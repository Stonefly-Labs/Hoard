import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_evidence as evidence


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


if __name__ == "__main__":
    unittest.main()
