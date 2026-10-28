import base64
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_evidence as evidence
import conformance_contributors as contributors
from conformance_execution import OwnedRun


class ContributorAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="hoard-contributor-admission-")).resolve()
        self.parent.chmod(0o700)
        self.addCleanup(shutil.rmtree, self.parent)
        self.source = self.parent / "author"
        self.source.mkdir()
        self.project = self.source / "Adapter.csproj"
        self.project.write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        (self.source / "Binding.cs").write_text("namespace Acme; public sealed class Binding { }\n")
        (self.source / "packages.lock.json").write_text('{"version":2,"dependencies":{}}\n')
        self.sidecar = self.project.with_suffix(".conformance.json")
        adapter = {"packageId": "Acme.Adapter", "version": "0.1.0", "assemblyName": "Acme.Adapter"}
        self.registration = {
            "schemaVersion": 1, "project": "Adapter.csproj", "factoryType": "Acme.Binding",
            "adapterPackage": adapter,
            "declaration": {
                "schemaVersion": 1, "bindingId": "acme.metadata", "category": "metadata",
                "packageId": "Acme.Provider", "packageVersion": "0.1.0",
                "capabilities": ["metadata", "non-durable"],
                "faults": sorted(evidence._BINDING_REQUIRED_FAULTS["metadata"])},
            "components": {role: dict(adapter) for role in evidence._SESSION_ROLES["metadata"]},
            "sourceFiles": ["Adapter.csproj", "Adapter.conformance.json", "Binding.cs", "packages.lock.json"],
        }
        self.write(self.registration)

    def write(self, registration):
        self.sidecar.write_text(json.dumps(registration))

    def admit(self, profile="metadata"):
        return evidence.admit_invocation(ROOT, [
            "--profile", profile, "--binding-project", str(self.project),
            "--evidence", str(self.parent / "fresh")])

    def test_explicit_external_registration_freezes_declared_source_bytes_without_allocating_or_building(self):
        first = self.admit()
        self.assertEqual(first.binding_project, self.project)
        self.assertRegex(first.binding_inputs_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(first.binding_inputs_sha256, self.admit().binding_inputs_sha256)
        (self.source / "Binding.cs").write_text("namespace Acme; public sealed class Changed { }\n")
        self.assertNotEqual(first.binding_inputs_sha256, self.admit().binding_inputs_sha256)
        self.assertFalse((self.parent / "fresh").exists())
        self.assertEqual({path.name for path in self.source.iterdir()},
                         {"Adapter.csproj", "Adapter.conformance.json", "Binding.cs", "packages.lock.json"})
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            evidence.dispatch_invocation(first)

    def test_registration_rejects_foreign_categories_missing_hooks_and_provider_selected_omissions(self):
        for defect in ("category", "hook", "extra", "exclusions", "factory-injection", "factory-unicode",
                       "factory-package", "component-missing", "component-path", "duplicate-source",
                       "missing-project", "missing-registration", "escape", "unknown-source", "project-depth"):
            changed = copy.deepcopy(self.registration)
            if defect == "category":
                changed["declaration"]["category"] = "artifacts"
            elif defect == "hook":
                changed["declaration"]["faults"].pop()
            elif defect in ("extra", "exclusions"):
                changed[defect] = ["MP-21"]
            elif defect == "factory-injection":
                changed["factoryType"] = "Acme.Binding(); Bad()"
            elif defect == "factory-unicode":
                changed["factoryType"] = "Acme.B\u0131nding"
            elif defect == "factory-package":
                changed["components"]["factory"]["packageId"] = "Other.Adapter"
            elif defect == "component-missing":
                del changed["components"]["schema"]
            elif defect == "component-path":
                changed["components"]["store"]["assemblyName"] = "../Other"
            elif defect == "duplicate-source":
                changed["sourceFiles"].append("Binding.cs")
            elif defect == "missing-project":
                changed["sourceFiles"].remove("Adapter.csproj")
            elif defect == "missing-registration":
                changed["sourceFiles"].remove("Adapter.conformance.json")
            elif defect == "escape":
                changed["sourceFiles"].append("../outside.cs")
            elif defect == "project-depth":
                changed["project"] = "/".join(["nested"] * 33 + ["Adapter.csproj"])
            else:
                changed["sourceFiles"].append("Missing.cs")
            self.write(changed)
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                self.admit()
            self.assertFalse((self.parent / "fresh").exists())

    def test_registration_inventory_rejects_links_and_duplicate_json_keys(self):
        original = self.sidecar.read_bytes()
        self.sidecar.write_bytes(original.replace(b'"schemaVersion": 1', b'"schemaVersion": 1, "schemaVersion": 1', 1))
        with self.assertRaises(evidence.ConformanceError):
            self.admit()
        self.sidecar.write_bytes(original)
        source = self.source / "Binding.cs"
        target = self.parent / "outside.cs"
        target.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(target)
        with self.assertRaises(evidence.ConformanceError):
            self.admit()
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),
                         hashlib.sha256(b"namespace Acme; public sealed class Binding { }\n").hexdigest())
        self.assertFalse((self.parent / "fresh").exists())

    def test_owned_declared_snapshot_uses_admitted_bytes_without_building_or_modifying_author_sources(self):
        invocation = self.admit()
        original = {path.name: path.read_bytes() for path in self.source.iterdir()}
        run = OwnedRun.allocate(self.parent / "fresh", ROOT, profile="harness")
        captured = contributors.snapshot_binding_project(
            self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertEqual(captured.root, run.root / "binding-source")
        self.assertEqual(captured.project, "Adapter.csproj")
        self.assertEqual(captured.inputs_sha256, invocation.binding_inputs_sha256)
        self.assertEqual({path.name: path.read_bytes() for path in self.source.iterdir()}, original)
        self.assertEqual({path.name: path.read_bytes() for path in captured.root.iterdir()}, original)
        self.assertTrue(all(path.stat().st_mode & 0o777 == 0o400 for path in captured.root.iterdir()))
        self.assertFalse((self.source / "obj").exists())
        self.assertFalse((captured.root / "obj").exists())

    def test_owned_snapshot_rejects_changes_after_admission_before_copy_and_during_copy(self):
        invocation = self.admit()
        source = self.source / "Binding.cs"
        original = source.read_bytes()
        run = OwnedRun.allocate(self.parent / "fresh", ROOT, profile="harness")
        source.write_bytes(original + b"// changed after admission\n")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.snapshot_binding_project(
                self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertFalse((run.root / "binding-source").exists())
        source.write_bytes(original)
        registration = self.sidecar.read_bytes()
        changed = copy.deepcopy(self.registration)
        changed["factoryType"] = "Acme.OtherBinding"
        self.write(changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.snapshot_binding_project(
                self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertFalse((run.root / "binding-source").exists())
        self.sidecar.write_bytes(registration)
        actual = evidence._source_file

        def mutate_after_copy(directory, relative, **options):
            result = actual(directory, relative, **options)
            if relative == "Binding.cs" and options.get("target") is not None:
                source.write_bytes(original + b"// changed during copy\n")
            return result

        with mock.patch.object(evidence, "_source_file", side_effect=mutate_after_copy):
            with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                contributors.snapshot_binding_project(
                    self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertEqual((run.root / "binding-source/Binding.cs").read_bytes(), original)
        self.assertFalse((self.source / "obj").exists())

    def test_owned_snapshot_rejects_output_inside_author_source_root(self):
        invocation = self.admit()
        original = (self.source / "Binding.cs").read_bytes()
        self.source.chmod(0o700)
        run = OwnedRun.allocate(self.source / "fresh", ROOT, profile="harness")
        with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
            contributors.snapshot_binding_project(
                self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertEqual((self.source / "Binding.cs").read_bytes(), original)
        self.assertFalse((run.root / "binding-source").exists())

    def test_typed_factory_source_requires_selected_actual_adapter_image_and_provider_package(self):
        project = contributors.admit_binding_project(self.project, "metadata")
        feed = self.parent / "feed"
        feed.mkdir()

        def package(name):
            with zipfile.ZipFile(feed / f"{name}.0.1.0.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                archive.writestr(f"lib/net10.0/{name}.dll", name.encode("ascii"))
            return evidence.package_identity(feed, name, "0.1.0")

        adapter, provider = package("Acme.Adapter"), package("Acme.Provider")
        source = contributors.binding_factory_source(project, adapter, provider)
        self.assertIn(b"new global::Acme.Binding(", source)
        self.assertIn(provider["sha256"].encode("ascii"), source)
        for selected_adapter, selected_provider in (
                (provider, provider), (adapter, adapter),
                ({**adapter, "runtimeAssemblies": {"lib/net10.0/Other.dll": "a" * 64}}, provider),
                ({**adapter, "version": "0.2.0"}, provider),
                (adapter, {**provider, "version": "0.2.0"})):
            with self.assertRaisesRegex(evidence.ConformanceError, "^BindingInvalid$"):
                contributors.binding_factory_source(project, selected_adapter, selected_provider)
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
            contributors.binding_factory_source(project, {**adapter, "sourceMapping": "nuget.org"}, provider)

    def test_registered_runtime_components_preserve_distinct_actual_archive_owners_and_image_names(self):
        feed, output = self.parent / "feed", self.parent / "consumer"
        feed.mkdir()
        output.mkdir()

        def package(name, assembly):
            image = (name + ":" + assembly).encode("ascii")
            with zipfile.ZipFile(feed / f"{name}.0.1.0.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                archive.writestr(f"lib/net10.0/{assembly}.dll", image)
            (output / f"{assembly}.dll").write_bytes(image)
            return evidence.package_identity(feed, name, "0.1.0")

        adapter = package("Acme.Adapter", "Acme.Adapter")
        provider = package("Acme.Provider", "Acme.Engine")
        controls = package("Acme.Helpers", "Acme.Control")
        packages = [adapter, provider, controls]
        self.registration["components"]["schema"] = {
            "packageId": "acme.provider", "version": "0.1.0", "assemblyName": "Acme.Engine"}
        for role in ("authority", "faults"):
            self.registration["components"][role] = {
                "packageId": "Acme.Helpers", "version": "0.1.0", "assemblyName": "Acme.Control"}
        self.write(self.registration)
        project = contributors.admit_binding_project(self.project, "metadata")

        def images():
            return evidence.input_manifest(self.parent, [
                f"consumer/{name}.dll" for name in ("Acme.Adapter", "Acme.Engine", "Acme.Control")])

        components = contributors.binding_runtime_components(project, packages, images(), "consumer")
        self.assertEqual(components["factory"], ("consumer/Acme.Adapter.dll", "Acme.Adapter"))
        self.assertEqual(components["store"], components["factory"])
        self.assertEqual(components["schema"], ("consumer/Acme.Engine.dll", "Acme.Provider"))
        self.assertEqual(components["faults"], ("consumer/Acme.Control.dll", "Acme.Helpers"))
        self.assertEqual(components["authority"], components["faults"])
        for defect, changed in (
                ("missing-provider", [adapter, controls]),
                ("missing-helper", [adapter, provider]),
                ("wrong-helper-version", [adapter, provider, {**controls, "version": "0.2.0"}]),
                ("wrong-helper-member", [adapter, provider, {
                    **controls, "runtimeAssemblies": {"lib/net10.0/Other.dll": next(iter(
                        controls["runtimeAssemblies"].values()))}}]),
                ("duplicate-casefolded-owner", [*packages, {**controls, "packageId": "acme.helpers"}])):
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^BindingInvalid$"):
                contributors.binding_runtime_components(project, changed, images(), "consumer")
        (output / "Acme.Control.dll").write_bytes(b"changed runtime image")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_runtime_components(project, packages, images(), "consumer")

        self.registration["declaration"].update({
            "category": "artifacts", "capabilities": ["artifacts", "non-durable"],
            "faults": sorted(evidence._BINDING_REQUIRED_FAULTS["artifacts"])})
        del self.registration["components"]["schema"]
        for role in ("validator", "maintenance", "lifetime"):
            self.registration["components"][role] = {
                "packageId": "Acme.Provider", "version": "0.1.0", "assemblyName": "Acme.Engine"}
        self.write(self.registration)
        artifact = contributors.admit_binding_project(self.project, "artifacts")
        (output / "Acme.Control.dll").write_bytes(b"Acme.Helpers:Acme.Control")
        components = contributors.binding_runtime_components(artifact, packages, images(), "consumer")
        self.assertEqual(components["validator"], ("consumer/Acme.Engine.dll", "Acme.Provider"))
        self.assertEqual(components["maintenance"], components["validator"])
        self.assertEqual(components["lifetime"], components["validator"])
        self.assertEqual(components["faults"], ("consumer/Acme.Control.dll", "Acme.Helpers"))

    def test_registered_components_reject_conflicting_runtime_asset_owners_even_with_identical_bytes(self):
        feed = self.parent / "feed"
        feed.mkdir()
        packages = []
        for name in ("Acme.Adapter", "Acme.Provider"):
            with zipfile.ZipFile(feed / f"{name}.0.1.0.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                archive.writestr("lib/net10.0/Acme.Adapter.dll", b"identical but ambiguously owned")
            packages.append(evidence.package_identity(feed, name, "0.1.0"))
        self.registration["components"]["schema"]["packageId"] = "Acme.Provider"
        self.write(self.registration)
        project = contributors.admit_binding_project(self.project, "metadata")
        images = {"consumer/Acme.Adapter.dll": hashlib.sha256(b"identical but ambiguously owned").hexdigest()}
        with self.assertRaisesRegex(evidence.ConformanceError, "^BindingInvalid$"):
            contributors.binding_runtime_components(project, packages, images, "consumer")

    def test_explicit_archive_lock_policy_preserves_versions_graph_and_unselected_dependencies(self):
        import conformance_lock_preparation as preparation
        feed = self.parent / "feed"
        feed.mkdir()
        packages = []
        for name, version in (("Acme.Adapter", "1.2.3-preview.1"), ("Acme.Provider", "4.2.1")):
            with zipfile.ZipFile(feed / f"{name}.{version}.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>{version}</version></metadata></package>")
                archive.writestr(f"lib/net10.0/{name}.dll", (name + version).encode("ascii"))
            packages.append(evidence.package_identity(feed, name, version))
        dependencies = {
            "acme.adapter": {
                "type": "Direct", "requested": "[1.2.3-preview.1, 1.2.3-preview.1]",
                "resolved": "1.2.3-preview.1", "contentHash": "old-adapter",
                "dependencies": {"Acme.Provider": "4.2.1", "External.Other": "7.0.0"}},
            "Acme.Provider": {"type": "Transitive", "resolved": "4.2.1", "contentHash": "old-provider"},
            "External.Other": {"type": "Transitive", "resolved": "7.0.0", "contentHash": "unselected"}}
        original = {"version": 2, "dependencies": {
            "net10.0": dependencies, "net10.0/linux-x64": copy.deepcopy(dependencies)}}
        before = evidence.canonical_bytes(original)
        source = self.parent / "candidate"
        source.mkdir()
        project = source / "Consumer.csproj"
        project.write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        lock = source / "packages.lock.json"
        lock.write_bytes(before)
        alternate, record = preparation.prepare_project_lock(
            project, source, feed, "candidate", local_packages=packages)
        self.assertEqual(lock.read_bytes(), before)
        prepared = evidence.load_json(alternate.read_bytes())
        expected = copy.deepcopy(original)
        for framework in expected["dependencies"].values():
            for package in packages:
                name = "acme.adapter" if package["packageId"] == "Acme.Adapter" else "Acme.Provider"
                framework[name]["contentHash"] = base64.b64encode(
                    bytes.fromhex(package["nugetSha512"])).decode("ascii")
        self.assertEqual(prepared, expected)
        self.assertFalse(record["qualification"])
        preparation.verify_project_lock(record, source, feed, local_packages=packages)
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            preparation.verify_project_lock(record, source, feed)
        for defect in ("duplicate", "version", "archive-hash", "nuget-hash"):
            changed = list(packages)
            if defect == "duplicate":
                changed.append({**packages[0], "packageId": "acme.adapter"})
            else:
                field, value = {
                    "version": ("version", "1.2.4"),
                    "archive-hash": ("sha256", "a" * 64),
                    "nuget-hash": ("nugetSha512", "b" * 128)}[defect]
                changed[0] = {**packages[0], field: value}
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^InputChanged$"):
                preparation.rebind_local_archives(before, feed, local_packages=changed)
        for defect in ("duplicate-node", "missing-hash", "resolved-version"):
            changed = copy.deepcopy(original)
            framework = changed["dependencies"]["net10.0"]
            if defect == "duplicate-node":
                framework["Acme.Adapter"] = copy.deepcopy(framework["acme.adapter"])
            elif defect == "missing-hash":
                del framework["acme.adapter"]["contentHash"]
            else:
                framework["acme.adapter"]["resolved"] = "1.2.4"
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^InputChanged$"):
                preparation.rebind_local_archives(
                    evidence.canonical_bytes(changed), feed, local_packages=packages)
        archive = feed / "Acme.Provider.4.2.1.nupkg"
        archive.write_bytes(archive.read_bytes() + b"changed after capture")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            preparation.verify_project_lock(record, source, feed, local_packages=packages)

    def test_evaluated_inputs_require_declared_source_closure_and_hash_actual_toolchain_bytes(self):
        binding = contributors.admit_binding_project(self.project, "metadata")
        toolchain = self.parent / "toolchain"
        toolchain.mkdir()
        (toolchain / "Sdk.props").write_text("<Project />\n")
        rows = [{"Identity": "source/" + path, "Kind": "source"} for path in binding.sources]
        rows.append({"Identity": "toolchain/Sdk.props", "Kind": "toolchain",
                     "FullPath": str(self.parent / "discarded-private-vendor-metadata")})

        def capture(items):
            return contributors.binding_evaluation_inputs(
                binding, evidence.canonical_bytes({"Items": {"_BindingInputs": items}}), toolchain)

        captured = capture(rows)
        self.assertFalse(captured["qualification"])
        self.assertEqual(captured["sources"], binding.sources)
        self.assertEqual(captured["toolchain"], {"Sdk.props": evidence.file_sha256(toolchain / "Sdk.props")})
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(captured))
        missing_project = [row for row in rows if row["Identity"] != "source/Adapter.csproj"]
        missing_toolchain = [row for row in rows if row["Kind"] != "toolchain"]
        (self.source / "Ambient.cs").write_text("public class Ambient { }\n")
        for defect, changed in (
                ("undeclared-ambient-source", [*rows, {"Identity": "source/Ambient.cs", "Kind": "source"}]),
                ("missing-project", missing_project), ("missing-toolchain", missing_toolchain)):
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceIncomplete$"):
                capture(changed)
        for defect, changed in (
                ("duplicate", [*rows, rows[0]]),
                ("unknown-metadata", [{**rows[0], "providerMessage": "must not disappear"}, *rows[1:]]),
                ("wrong-kind", [{**rows[0], "Kind": "package"}, *rows[1:]]),
                ("prefix-mismatch", [{**rows[0], "Kind": "toolchain"}, *rows[1:]]),
                ("escaping-source", [{"Identity": "source/../outside", "Kind": "source"}, *rows[1:]])):
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                capture(changed)
        original = (self.source / "Binding.cs").read_bytes()
        (self.source / "Binding.cs").write_text("public class Changed { }\n")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            capture(rows)
        (self.source / "Binding.cs").write_bytes(original)
        self.sidecar.write_bytes(self.sidecar.read_bytes() + b"\n")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            capture([row for row in rows if row["Identity"] != "source/Adapter.conformance.json"])


if __name__ == "__main__":
    unittest.main()
