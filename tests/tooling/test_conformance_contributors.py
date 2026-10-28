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
import conformance_case_catalog as catalog
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

    def test_registered_metadata_common_parameters_use_the_actual_binding_id_without_builtin_aliases(self):
        counts = catalog.metadata_common_consumer_origin_counts(binding_ids=("acme.metadata",))
        default = catalog.metadata_common_consumer_origin_counts()
        self.assertEqual(len(counts) * 2, len(default))
        self.assertEqual({identity.split("(provider:")[0] for identity in counts},
                         {identity.split("(provider:")[0] for identity in default})
        self.assertTrue(all('(provider: "acme.metadata"' in identity for identity in counts))
        self.assertFalse(any('"memory"' in identity or '"sqlite"' in identity for identity in counts))
        for invalid in ((), ("acme.metadata",) * 2, "acme.metadata", None, ("../foreign",)):
            with self.subTest(invalid=invalid), self.assertRaises(evidence.ConformanceError):
                catalog.metadata_common_consumer_origin_counts(binding_ids=invalid)

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

    def compilation(self):
        self.generated = self.parent / "generated"
        self.generated.mkdir()
        (self.generated / "Dynamic.cs").write_text("public class Dynamic { }\n")
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        return {
            "schemaVersion": 1, "qualification": False, "succeeded": True,
            "compilations": [{
                "project": "Adapter.csproj", "succeeded": True,
                "sources": {"source/Binding.cs": self.binding.sources["Binding.cs"],
                            "generated/Dynamic.cs": evidence.file_sha256(self.generated / "Dynamic.cs")}}]}

    def compile_inputs(self, value):
        data = value if isinstance(value, bytes) else evidence.canonical_bytes(value)
        return contributors.binding_compilation_sources(self.binding, data, self.generated)

    def test_compiler_sources_bind_each_actual_project_to_frozen_and_generated_source_hashes(self):
        value = self.compilation()
        (self.source / "Helper.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        self.registration["sourceFiles"].append("Helper.csproj")
        self.write(self.registration)
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        value["compilations"].append({
            "project": "Helper.csproj", "succeeded": True,
            "sources": {"source/Binding.cs": self.binding.sources["Binding.cs"]}})
        result = self.compile_inputs(value)
        self.assertEqual(result["compilations"], tuple(value["compilations"]))
        self.assertEqual(result["bindingInputsSha256"], self.binding.inputs_sha256)
        self.assertFalse(result["qualification"])
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))

    def test_compiler_sources_reject_failed_missing_duplicate_or_undeclared_projects(self):
        value = self.compilation()
        (self.source / "Other.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        self.registration["sourceFiles"].append("Other.csproj")
        self.write(self.registration)
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        for defect in ("build-failed", "compiler-failed", "missing-selected-project", "duplicate-project",
                       "undeclared-project", "not-a-project", "undeclared-source"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "build-failed":
                changed["succeeded"] = False
            elif defect == "compiler-failed":
                row["succeeded"] = False
            elif defect == "duplicate-project":
                changed["compilations"].append(copy.deepcopy(row))
            elif defect == "undeclared-source":
                row["sources"]["source/Ambient.cs"] = "a" * 64
            else:
                row["project"] = {
                    "missing-selected-project": "Other.csproj", "undeclared-project": "Unknown.csproj",
                    "not-a-project": "Binding.cs"}[defect]
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceIncomplete$"):
                self.compile_inputs(changed)

    def test_compiler_sources_reject_changed_generated_queried_and_unqueried_frozen_bytes(self):
        value = self.compilation()
        for path in (self.generated / "Dynamic.cs", self.source / "Binding.cs", self.sidecar):
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            with self.subTest(path=path.name), self.assertRaisesRegex(
                    evidence.ConformanceError, "^InputChanged$"):
                self.compile_inputs(value)
            path.write_bytes(original)
        changed = copy.deepcopy(value)
        changed["compilations"].append({
            "project": "Helper.csproj", "succeeded": True,
            "sources": {"generated/Dynamic.cs": "a" * 64}})
        (self.source / "Helper.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        self.registration["sourceFiles"].append("Helper.csproj")
        self.write(self.registration)
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.compile_inputs(changed)

    def test_compiler_sources_reject_open_schemas_unsafe_paths_and_unbounded_receipts(self):
        value = self.compilation()
        for defect in ("unknown-top", "unknown-row", "empty-rows", "empty-sources", "numeric-success",
                       "qualification", "namespace", "escape", "absolute", "hash"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "unknown-top":
                changed["message"] = "must not disappear"
            elif defect == "unknown-row":
                row["commandLine"] = "must not persist"
            elif defect == "empty-rows":
                changed["compilations"] = []
            elif defect == "empty-sources":
                row["sources"] = {}
            elif defect == "numeric-success":
                row["succeeded"] = 1
            elif defect == "qualification":
                changed["qualification"] = True
            elif defect == "hash":
                row["sources"]["source/Binding.cs"] = "invalid"
            else:
                path = {"namespace": "package/Other.cs", "escape": "generated/../outside.cs",
                        "absolute": "/private/outside.cs"}[defect]
                row["sources"][path] = "a" * 64
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                self.compile_inputs(changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            self.compile_inputs(b"x" * (2 * 1024 * 1024 + 1))
        raw = evidence.canonical_bytes(value).replace(b'"schemaVersion":1', b'"schemaVersion":1,"schemaVersion":1')
        with self.assertRaises(evidence.ConformanceError):
            self.compile_inputs(raw)

    def test_compiler_sources_reject_overlapping_generated_roots_and_linked_generated_inputs(self):
        value = self.compilation()
        for generated in (self.source, self.source / "obj", self.parent):
            with self.subTest(root=generated.name), self.assertRaisesRegex(
                    evidence.ConformanceError, "^OwnershipInvalid$"):
                contributors.binding_compilation_sources(
                    self.binding, evidence.canonical_bytes(value), generated)
        outside = self.parent / "outside.cs"
        outside.write_bytes((self.generated / "Dynamic.cs").read_bytes())
        (self.generated / "Dynamic.cs").unlink()
        (self.generated / "Dynamic.cs").symlink_to(outside)
        with self.assertRaises(evidence.ConformanceError):
            self.compile_inputs(value)
        self.assertEqual(outside.read_text(), "public class Dynamic { }\n")

    def documents(self):
        compilation = self.compile_inputs(self.compilation())["compilations"][0]
        self.output = self.parent / "output"
        self.output.mkdir()
        (self.output / "Adapter.dll").write_bytes(b"modeled compiler image")
        (self.output / "Adapter.pdb").write_bytes(b"modeled portable symbols")
        value = {
            "schemaVersion": 1, "qualification": False, "project": "Adapter.csproj",
            "assembly": {"path": "Adapter.dll", "sha256": evidence.file_sha256(self.output / "Adapter.dll")},
            "pdb": {"path": "Adapter.pdb", "sha256": evidence.file_sha256(self.output / "Adapter.pdb")},
            "documents": dict(compilation["sources"])}
        return compilation, value

    def document_inputs(self, compilation, value):
        return contributors.binding_compilation_documents(
            compilation, evidence.canonical_bytes(value), self.output, "Adapter.dll")

    def test_compiler_document_receipts_match_observed_source_subset_and_current_output_bytes(self):
        compilation, value = self.documents()
        del value["documents"]["generated/Dynamic.cs"]
        result = self.document_inputs(compilation, value)
        self.assertEqual(result["documents"], value["documents"])
        self.assertEqual(result["compilerSourcesSha256"], evidence.digest(compilation["sources"]))
        self.assertEqual(result["assembly"], value["assembly"])
        self.assertEqual(result["pdb"], value["pdb"])
        self.assertFalse(result["qualification"])
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))

    def test_compiler_documents_reject_foreign_project_source_hash_or_output_selection(self):
        compilation, value = self.documents()
        for defect in ("project", "document", "hash", "assembly", "pdb"):
            changed = copy.deepcopy(value)
            if defect == "project":
                changed["project"] = "Other.csproj"
            elif defect == "document":
                changed["documents"]["generated/Unobserved.cs"] = "a" * 64
            elif defect == "hash":
                changed["documents"]["source/Binding.cs"] = "a" * 64
            else:
                changed[defect]["path"] = "Other." + ("dll" if defect == "assembly" else "pdb")
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^ProofMismatch$"):
                self.document_inputs(compilation, changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            self.document_inputs({**compilation, "succeeded": False}, value)

    def test_compiler_documents_reject_output_byte_changes_and_linked_symbols(self):
        compilation, value = self.documents()
        for name in ("Adapter.dll", "Adapter.pdb"):
            path = self.output / name
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(name=name), self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                self.document_inputs(compilation, value)
            path.write_bytes(original)
        outside = self.parent / "outside.pdb"
        original = (self.output / "Adapter.pdb").read_bytes()
        outside.write_bytes(original)
        (self.output / "Adapter.pdb").unlink()
        (self.output / "Adapter.pdb").symlink_to(outside)
        with self.assertRaises(evidence.ConformanceError):
            self.document_inputs(compilation, value)
        self.assertEqual(outside.read_bytes(), original)

    def test_compiler_documents_reject_open_schemas_unsafe_paths_and_empty_document_sets(self):
        compilation, value = self.documents()
        for defect in ("field", "nested-field", "absolute", "escape", "qualification", "documents"):
            changed = copy.deepcopy(value)
            if defect == "field":
                changed["message"] = "must not disappear"
            elif defect == "nested-field":
                changed["assembly"]["message"] = "must not disappear"
            elif defect == "qualification":
                changed["qualification"] = True
            elif defect == "documents":
                changed["documents"] = {}
            else:
                changed["pdb"]["path"] = "/private/Adapter.pdb" if defect == "absolute" else "../Adapter.pdb"
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                self.document_inputs(compilation, changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            contributors.binding_compilation_documents(
                compilation, b"x" * (2 * 1024 * 1024 + 1), self.output, "Adapter.dll")

    def build_files(self):
        compilation = self.compile_inputs(self.compilation())["compilations"][0]
        self.toolchain, self.package_root = self.parent / "toolchain", self.parent / "packages"
        self.toolchain.mkdir()
        self.package_root.mkdir()
        for root, name, data in (
                (self.toolchain, "Reference.dll", b"fixed reference image"),
                (self.toolchain, "Analyzer.dll", b"fixed analyzer image"),
                (self.toolchain, "Sdk.props", b"<Project />"),
                (self.package_root, "acme.library/2.0.0/lib/net10.0/Library.dll", b"fixed package image")):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.package_inputs = evidence.input_manifest(
            self.package_root, ["acme.library/2.0.0/lib/net10.0/Library.dll"])
        return {
            "schemaVersion": 1, "qualification": False, "succeeded": True,
            "diagnosticCodes": [], "observerErrors": [],
            "imports": {"source/Adapter.csproj": self.binding.sources["Adapter.csproj"],
                        "toolchain/Sdk.props": evidence.file_sha256(self.toolchain / "Sdk.props")},
            "compilations": [{
                "project": "Adapter.csproj", "succeeded": True, "inputs": {
                    "Sources": dict(compilation["sources"]),
                    "References": {
                        "toolchain/Reference.dll": evidence.file_sha256(self.toolchain / "Reference.dll"),
                        **{"packages/" + path: hashed for path, hashed in self.package_inputs.items()}},
                    "Analyzers": {"toolchain/Analyzer.dll": evidence.file_sha256(self.toolchain / "Analyzer.dll")},
                    "AdditionalFiles": {}, "Resources": {}}}]}

    def build_file_inputs(self, value):
        return contributors.binding_build_file_inputs(
            self.binding, evidence.canonical_bytes(value), self.generated, self.toolchain,
            self.package_root, self.package_inputs)

    def test_build_file_receipts_rehash_imports_compiler_inputs_and_frozen_package_policy(self):
        value = self.build_files()
        result = self.build_file_inputs(value)
        self.assertEqual(result["imports"], value["imports"])
        self.assertEqual(result["compilations"], tuple(value["compilations"]))
        self.assertEqual(result["bindingInputsSha256"], self.binding.inputs_sha256)
        self.assertEqual(result["packageInputsSha256"], evidence.digest(self.package_inputs))
        self.assertFalse(result["qualification"])
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))

    def test_build_file_receipts_reject_missing_closure_failed_observation_and_unknown_parameters(self):
        value = self.build_files()
        for defect in ("diagnostics", "observer", "build-failed", "compiler-failed", "project", "duplicate-project",
                       "missing-sources", "empty-references", "unknown-parameter", "unknown-field",
                       "namespace", "undeclared-source", "package-policy", "empty-imports"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            expected = "EvidenceIncomplete"
            if defect in ("diagnostics", "observer"):
                changed["diagnosticCodes" if defect == "diagnostics" else "observerErrors"] = ["MSB4017"]
            elif defect == "build-failed":
                changed["succeeded"] = False
            elif defect == "compiler-failed":
                row["succeeded"] = False
            elif defect == "project":
                row["project"] = "Foreign.csproj"
            elif defect == "duplicate-project":
                changed["compilations"].append(copy.deepcopy(row))
            elif defect == "missing-sources":
                del row["inputs"]["Sources"]
                expected = "EvidenceSchemaInvalid"
            elif defect == "empty-references":
                row["inputs"]["References"] = {}
            elif defect == "unknown-parameter":
                row["inputs"]["UnobservedFiles"] = {}
                expected = "EvidenceSchemaInvalid"
            elif defect == "unknown-field":
                changed["message"] = "must not disappear"
                expected = "EvidenceSchemaInvalid"
            elif defect in ("namespace", "undeclared-source", "package-policy"):
                path = {"namespace": "external/Other.dll", "undeclared-source": "source/Ambient.cs",
                        "package-policy": "packages/foreign/1.0.0/Other.dll"}[defect]
                row["inputs"]["References"][path] = "a" * 64
                if defect == "namespace":
                    expected = "EvidenceSchemaInvalid"
            else:
                changed["imports"] = {}
                expected = "EvidenceSchemaInvalid"
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^" + expected + "$"):
                self.build_file_inputs(changed)

    def test_build_file_receipts_reject_changed_bytes_conflicting_hashes_and_package_policy_substitution(self):
        value = self.build_files()
        for path in (self.sidecar, self.generated / "Dynamic.cs", self.toolchain / "Reference.dll",
                     self.toolchain / "Analyzer.dll", self.toolchain / "Sdk.props",
                     self.package_root / "acme.library/2.0.0/lib/net10.0/Library.dll"):
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(path=path.name), self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                self.build_file_inputs(value)
            path.write_bytes(original)
        changed = copy.deepcopy(value)
        changed["imports"]["toolchain/Reference.dll"] = "a" * 64
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.build_file_inputs(changed)
        self.package_inputs = {path: "a" * 64 for path in self.package_inputs}
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.build_file_inputs(value)

    def test_build_file_receipts_reject_root_overlap_linked_inputs_and_aggregate_read_limit(self):
        value = self.build_files()
        with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
            contributors.binding_build_file_inputs(
                self.binding, evidence.canonical_bytes(value), self.generated, self.generated,
                self.package_root, self.package_inputs)
        outside = self.parent / "outside.dll"
        original = (self.toolchain / "Analyzer.dll").read_bytes()
        outside.write_bytes(original)
        (self.toolchain / "Analyzer.dll").unlink()
        (self.toolchain / "Analyzer.dll").symlink_to(outside)
        with self.assertRaises(evidence.ConformanceError):
            self.build_file_inputs(value)
        self.assertEqual(outside.read_bytes(), original)
        (self.toolchain / "Analyzer.dll").unlink()
        (self.toolchain / "Analyzer.dll").write_bytes(original)
        declared_bytes = sum((self.source / path).stat().st_size for path in self.binding.sources)
        with mock.patch.object(evidence, "MAX_PROOF_BYTES", declared_bytes):
            with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
                self.build_file_inputs(value)

    def package_file_selection(self):
        self.feed = self.parent / "feed"
        self.feed.mkdir()
        self.archive = self.feed / "Acme.Dependency.2.4.0-preview.1.nupkg"
        self.package_files = {
            "lib/net10.0/Acme.Dependency.dll": b"fixed runtime image",
            "ref/net10.0/Acme.Dependency.dll": b"fixed reference image",
            "build/Acme.Dependency.props": b"<Project />",
            "analyzers/dotnet/cs/Generator.dll": b"fixed analyzer image",
            "contentFiles/any/any/Additional.txt": b"private-resource-canary"}
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("Acme.Dependency.nuspec", (
                "<package><metadata><id>Acme.Dependency</id><version>2.4.0-preview.1</version></metadata></package>"))
            for name, data in self.package_files.items():
                archive.writestr(name, data)
        package = evidence.package_identity(self.feed, "Acme.Dependency", "2.4.0-preview.1")
        selection = {
            "packageId": "acme.dependency", "version": "2.4.0-preview.1",
            "cachePath": "acme.dependency/2.4.0-preview.1",
            "members": sorted(self.package_files)}
        return package, selection

    def test_registered_package_file_policy_binds_exact_nonruntime_archive_members_without_extracting(self):
        package, selection = self.package_file_selection()
        policy = contributors.binding_package_file_policy(self.feed, [package], [selection])
        self.assertEqual(policy, {
            selection["cachePath"] + "/" + name: hashlib.sha256(data).hexdigest()
            for name, data in self.package_files.items()})
        self.assertNotIn(b"private-resource-canary", evidence.canonical_bytes(policy))
        self.assertEqual(set(self.feed.iterdir()), {self.archive})
        self.assertEqual(contributors.binding_package_file_policy(self.feed, [], []), {})

    def test_registered_package_file_policy_rejects_missing_foreign_duplicate_or_ambiguous_selections(self):
        package, selection = self.package_file_selection()
        for defect in ("package", "version", "cache-owner", "cache-path", "cache-escape", "missing-member",
                       "member-escape", "duplicate-member", "duplicate-cache", "duplicate-package"):
            changed, packages = copy.deepcopy(selection), [package]
            expected = "BindingInvalid"
            if defect == "package":
                changed["packageId"] = "Foreign.Dependency"
            elif defect == "version":
                changed["version"] = "2.4.1"
            elif defect == "cache-owner":
                changed["cachePath"] = "other.dependency/2.4.0-preview.1"
            elif defect == "cache-path":
                changed["cachePath"] += "/nested"
            elif defect == "cache-escape":
                changed["cachePath"] = "../outside"
                expected = "EvidenceSchemaInvalid"
            elif defect == "missing-member":
                changed["members"].append("build/Absent.props")
                expected = "InputChanged"
            elif defect == "member-escape":
                changed["members"].append("../outside.props")
                expected = "EvidenceSchemaInvalid"
            elif defect == "duplicate-member":
                changed["members"].append(changed["members"][0])
                expected = "EvidenceSchemaInvalid"
            elif defect == "duplicate-package":
                packages.append({**package, "packageId": "acme.dependency"})
            selected = [changed, copy.deepcopy(changed)] if defect == "duplicate-cache" else [changed]
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^" + expected + "$"):
                contributors.binding_package_file_policy(self.feed, packages, selected)

    def test_registered_package_file_policy_rejects_changed_archive_bytes_and_hashes(self):
        package, selection = self.package_file_selection()
        for field in ("sha256", "nugetSha512"):
            changed = {**package, field: "a" * (64 if field == "sha256" else 128)}
            with self.subTest(field=field), self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                contributors.binding_package_file_policy(self.feed, [changed], [selection])
        self.archive.write_bytes(self.archive.read_bytes() + b"changed")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_package_file_policy(self.feed, [package], [selection])

    def test_registered_package_file_policy_checks_selected_nondll_crc_and_aggregate_byte_budget(self):
        package, selection = self.package_file_selection()
        with mock.patch.object(evidence, "MAX_PROOF_BYTES", self.archive.stat().st_size):
            with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
                contributors.binding_package_file_policy(self.feed, [package], [selection])
        with zipfile.ZipFile(self.archive) as archive:
            info = archive.getinfo("build/Acme.Dependency.props")
            offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
        raw = bytearray(self.archive.read_bytes())
        raw[offset] ^= 1
        self.archive.write_bytes(raw)
        corrupted = evidence.package_identity(self.feed, "Acme.Dependency", "2.4.0-preview.1")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_package_file_policy(self.feed, [corrupted], [selection])

    def test_build_only_archive_identity_does_not_weaken_runtime_package_admission(self):
        feed = self.parent / "feed"
        feed.mkdir()
        archive = feed / "Acme.BuildInputs.3.2.1.nupkg"
        with zipfile.ZipFile(archive, "w") as packed:
            packed.writestr("Acme.BuildInputs.nuspec",
                            "<package><metadata><id>Acme.BuildInputs</id><version>3.2.1</version></metadata></package>")
            packed.writestr("build/Acme.BuildInputs.props", "<Project />")
        captured = evidence.package_archive_identity(feed, "Acme.BuildInputs", "3.2.1")
        self.assertEqual(set(captured), {"packageId", "version", "sha256", "nugetSha512", "sourceMapping"})
        self.assertEqual(captured["sha256"], evidence.file_sha256(archive))
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            evidence.package_identity(feed, "Acme.BuildInputs", "3.2.1")
        selection = {
            "packageId": "Acme.BuildInputs", "version": "3.2.1", "cachePath": "acme.buildinputs/3.2.1",
            "members": ["build/Acme.BuildInputs.props"]}
        policy = contributors.binding_package_file_policy(feed, [captured], [selection])
        self.assertEqual(policy, {
            "acme.buildinputs/3.2.1/build/Acme.BuildInputs.props": hashlib.sha256(b"<Project />").hexdigest()})
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
            contributors.binding_package_file_policy(feed, [{**captured, "message": "must not disappear"}], [selection])
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_package_file_policy(feed, [{**captured, "sha256": "a" * 64}], [selection])

    def compiler_parameters(self):
        files = self.build_file_inputs(self.build_files())["compilations"]
        return files, {
            "schemaVersion": 1, "qualification": False, "compilations": [{
                "project": row["project"], "commandLineSha256": "a" * 64,
                "itemMetadata": {kind: {path: "b" * 64 for path in items}
                                 for kind, items in row["inputs"].items()}}
                for row in files]}

    def test_compiler_parameters_bind_each_project_and_metadata_key_to_actual_file_receipt(self):
        files, value = self.compiler_parameters()
        result = contributors.binding_compiler_parameter_inputs(files, evidence.canonical_bytes(value))
        self.assertEqual(result["compilations"], tuple(value["compilations"]))
        self.assertEqual(result["fileInputsSha256"], evidence.digest(files))
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))
        self.assertFalse(result["qualification"])

    def test_compiler_parameters_reject_missing_duplicate_foreign_or_mismatched_metadata_keys(self):
        files, value = self.compiler_parameters()
        for defect in ("project", "duplicate-project", "missing-kind", "unknown-input", "missing-input"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "project":
                row["project"] = "Other.csproj"
            elif defect == "duplicate-project":
                changed["compilations"].append(copy.deepcopy(row))
            elif defect == "missing-kind":
                del row["itemMetadata"]["Analyzers"]
            elif defect == "unknown-input":
                row["itemMetadata"]["References"]["source/Other.dll"] = "c" * 64
            else:
                del row["itemMetadata"]["References"]["toolchain/Reference.dll"]
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
                contributors.binding_compiler_parameter_inputs(files, evidence.canonical_bytes(changed))
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            contributors.binding_compiler_parameter_inputs(
                [{**files[0], "succeeded": False}], evidence.canonical_bytes(value))
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            contributors.binding_compiler_parameter_inputs([files[0], files[0]], evidence.canonical_bytes(value))

    def test_compiler_parameters_reject_open_schemas_malformed_hashes_and_unbounded_receipts(self):
        files, value = self.compiler_parameters()
        for defect in ("field", "row-field", "command-hash", "metadata-hash", "path", "unknown-parameter"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "field":
                changed["rawCommandLine"] = "must not disappear"
            elif defect == "row-field":
                row["message"] = "must not disappear"
            elif defect == "command-hash":
                row["commandLineSha256"] = ""
            elif defect == "metadata-hash":
                row["itemMetadata"]["Sources"]["source/Binding.cs"] = "invalid"
            elif defect == "path":
                row["project"] = "../Other.csproj"
            else:
                row["itemMetadata"]["UnknownParameter"] = {}
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                contributors.binding_compiler_parameter_inputs(files, evidence.canonical_bytes(changed))
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            contributors.binding_compiler_parameter_inputs(files, b"x" * (2 * 1024 * 1024 + 1))


if __name__ == "__main__":
    unittest.main()
