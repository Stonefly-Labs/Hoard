"""Inherited composition inventory and safe exact-discovery controls."""

import importlib.util
import copy
import json
from pathlib import Path
import sys
import unittest

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
