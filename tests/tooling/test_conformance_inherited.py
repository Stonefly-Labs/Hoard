"""Inherited composition inventory and safe exact-discovery controls."""

import importlib.util
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "freeze_composition_inventory",
    ROOT / "tests/fixtures/conformance/baselines/freeze_composition_inventory.py")
FREEZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FREEZE)
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_inherited as inherited
from conformance_evidence import ConformanceError, canonical_bytes


class FrozenCompositionInventoryTests(unittest.TestCase):
    def test_controller_evidence_is_explicitly_forwarded_bound_and_owned(self):
        import lifecycle_evidence as lifecycle
        import conformance_legacy as legacy
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary).resolve()
            manifest = owner / "lifecycle-evidence.json"
            manifest.write_bytes(b'{"graphs":[]}')
            with inherited.controller_transport(ROOT, owner) as controls, patch.dict(
                    os.environ, {"HOARD_LIFECYCLE_EVIDENCE": str(manifest)}), patch.object(
                    legacy, "composition_controller_command",
                    return_value=subprocess.CompletedProcess([], 0, "")) as command:
                lifecycle.run("dotnet", "test", "Hoard.Architecture.Tests.csproj")
                self.assertEqual(str(manifest), command.call_args.kwargs["env"]["HOARD_LIFECYCLE_EVIDENCE"])
                self.assertEqual(legacy._hash(manifest), controls["inputFiles"][manifest.name])
            with tempfile.TemporaryDirectory() as outside, inherited.controller_transport(ROOT, owner), \
                    patch.dict(os.environ, {"HOARD_LIFECYCLE_EVIDENCE": str(Path(outside) / "manifest.json")}), \
                    patch.object(legacy, "composition_controller_command") as command, \
                    self.assertRaises(ConformanceError):
                lifecycle.run("dotnet", "test", "Hoard.Architecture.Tests.csproj")
            command.assert_not_called()
            with inherited.controller_transport(ROOT, owner), patch.dict(
                    os.environ, {"HOARD_LIFECYCLE_EVIDENCE": str(manifest)}), patch.object(
                    legacy, "composition_controller_command",
                    side_effect=lambda *args, **kwargs: manifest.write_bytes(b'{"graphs":[1]}')), \
                    self.assertRaisesRegex(ConformanceError, "InputChanged"):
                lifecycle.run("dotnet", "test", "Hoard.Architecture.Tests.csproj")

    def test_borrowed_controller_transport_rejects_raw_diagnostics_and_restores_entry_points(self):
        import configuration_evidence as configuration
        import discovery_evidence as discovery
        import foundation_evidence as foundation
        import lifecycle_evidence as lifecycle
        import conformance_legacy as legacy
        modules = (foundation, lifecycle, configuration, discovery)
        originals = [module.run for module in modules]
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary)
            os.chmod(owner, 0o700)
            with inherited.controller_transport(ROOT, owner), patch.object(
                    legacy, "capture", return_value=subprocess.CompletedProcess(
                        ["dotnet", "build", "Consumer.csproj"], 0, b"private-canary\n")):
                for module in modules:
                    with self.subTest(module=module.__name__), self.assertRaisesRegex(
                            RuntimeError, "^Legacy composition command UnknownDiagnostic.$"):
                        module.run("dotnet", "build", "Consumer.csproj")
            self.assertEqual(originals, [module.run for module in modules])

    def test_expands_parameters_without_copying_private_arguments(self):
        raw = b'''public sealed class OriginalTests
{
    [Theory]
    [InlineData("""{"value":"private-canary"}""")]
    [InlineData("second-canary")]
    public async Task Original(string input) { }
    [Fact]
    public void Separate() { }
    public async Task Helper() { }
}'''
        self.assertEqual({
            "Hoard.Composition.Tests.OriginalTests.Original": 2,
            "Hoard.Composition.Tests.OriginalTests.Separate": 1,
        }, FREEZE.methods_in_source(raw))

    def test_rejects_unexpanded_or_duplicate_assertions(self):
        for body in (
                "[Theory]\n[MemberData(nameof(Private))]\npublic Task Original(string input) { }",
                "[Theory]\npublic Task Original(string input) { }",
                "[Fact]\npublic Task Original(string input) { }",
                "[Fact]\npublic Task Original() { }\n[Fact]\npublic Task Original() { }",
                "[Fact]\npublic ValueTask Original() { }"):
            with self.subTest(body=body), self.assertRaises(ValueError):
                FREEZE.methods_in_source(("public sealed class OriginalTests\n{\n" + body + "\n}").encode())

    def test_frozen_inventory_is_derived_only_from_immutable_baseline(self):
        path = ROOT / "tests/fixtures/conformance/baselines/composition-inventory.json"
        self.assertEqual(json.loads(path.read_bytes()), FREEZE.freeze())

    def test_exact_discovery_rejects_missing_duplicate_foreign_and_misexpanded_parameters(self):
        value = json.loads((ROOT / inherited.INVENTORY_PATH).read_bytes())
        methods = inherited.inventory(canonical_bytes(value), value["sourceFiles"])
        rows = [{"fullyQualifiedName": name,
                 "testIdentity": name + '(testCaseSha256: "' + f"{index:064x}" + '")'}
                for name, entry in methods.items() if name.startswith("Hoard.Composition.Tests.")
                for index in range(entry["parameterCount"])]
        for mutation in ("none", "missing", "duplicate", "changed-method", "raw-display", "extra-key"):
            altered = copy.deepcopy(rows)
            if mutation == "missing":
                altered.pop()
            elif mutation == "duplicate":
                altered[-1] = altered[0]
            elif mutation == "changed-method":
                altered[-1]["fullyQualifiedName"] = "Hoard.Composition.Tests.Foreign.Test"
            elif mutation == "raw-display":
                altered[-1]["testIdentity"] = altered[-1]["fullyQualifiedName"] + '(value: "canary")'
            elif mutation == "extra-key":
                altered[-1]["privateDisplay"] = "canary"
            with self.subTest(mutation=mutation):
                if mutation == "none":
                    self.assertEqual(len(rows), len(inherited.admit_discovery(
                        canonical_bytes(altered), methods, assembly="Hoard.Composition.Tests")))
                else:
                    with self.assertRaises(ConformanceError):
                        inherited.admit_discovery(
                            canonical_bytes(altered), methods, assembly="Hoard.Composition.Tests")

    def test_inventory_rejects_source_drift_omitted_cases_and_falsified_parameter_totals(self):
        value = json.loads((ROOT / inherited.INVENTORY_PATH).read_bytes())
        for mutation in ("changed-source", "missing-case", "missing-method", "wrong-count", "resealed-count"):
            altered = copy.deepcopy(value)
            if mutation == "changed-source":
                altered["sourceFiles"][altered["entries"][0]["sourcePath"]] = "0" * 64
            elif mutation == "missing-case":
                altered["caseMethods"].pop("CFG-02")
            elif mutation == "missing-method":
                altered["entries"].pop()
            elif mutation == "wrong-count":
                altered["entries"][0]["parameterCount"] += 1
            elif mutation == "resealed-count":
                altered["entries"][0]["parameterCount"] += 1
                altered["groupParameters"][altered["entries"][0]["group"]] += 1
            with self.subTest(mutation=mutation), self.assertRaises(ConformanceError):
                inherited.inventory(canonical_bytes(altered), value["sourceFiles"])


if __name__ == "__main__":
    unittest.main()
