import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

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


if __name__ == "__main__":
    unittest.main()
