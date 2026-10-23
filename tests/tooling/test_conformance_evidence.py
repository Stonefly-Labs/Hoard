import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_evidence as evidence


class ConformanceAdmissionTests(unittest.TestCase):
    def case(self):
        return {
            "caseId": "MP-01", "contractRevision": "f07-v1", "category": "metadata",
            "claimClass": "common-logical", "requirementReferences": ["FR-001"],
            "expectedWitnessIds": ["metadata.roundtrip"],
            "applicabilityRule": "mandatory",
        }

    def test_strict_json_rejects_duplicate_keys_nonfinite_and_invalid_unicode(self):
        for raw in ('{"a":1,"a":2}', '{"value":NaN}', '{"value":Infinity}',
                    '{"value":1e999}', '{"value":"\\ud800"}', '{"\\ud800":0}',
                    '{"value":true} trailing'):
            with self.subTest(raw=raw), self.assertRaises(evidence.ConformanceError):
                evidence.load_json(raw.encode())
        self.assertEqual(evidence.load_json(b'{"a":[1,true,null]}'), {"a": [1, True, None]})

    def test_case_requires_every_field_and_copies_all_collections(self):
        case = self.case()
        admitted = evidence.admit_entity("ContractCase", case)
        case["expectedWitnessIds"].append("changed")
        self.assertEqual(admitted["expectedWitnessIds"], ("metadata.roundtrip",))
        with self.assertRaises(TypeError):
            admitted["caseId"] = "MP-02"
        for key in self.case():
            changed = self.case()
            del changed[key]
            with self.subTest(missing=key), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("ContractCase", changed)

    def test_unknown_fields_categories_revisions_and_unbounded_ids_reject(self):
        for key, value in (
                ("caseId", "../escape"), ("caseId", "x" * 129), ("caseId", "caf\u00e9"),
                ("category", "service"), ("contractRevision", "f07-v2"),
                ("claimClass", "production"), ("expectedWitnessIds", []),
                ("expectedWitnessIds", ["same", "same"]),
                ("expectedWitnessIds", ["x" + str(n) for n in range(129)]),
                ("applicabilityRule", "provider-selected"), ("unknown", "ignored")):
            changed = self.case()
            changed[key] = value
            with self.subTest(field=key, value=value), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("ContractCase", changed)

    def test_result_requires_exact_dimensions_status_attempts_and_provenance(self):
        result = {
            "runId": "95b3bbc8-f009-4692-bca2-c2253fa2d967",
            "profileId": "metadata", "bindingId": "sqlite", "matrixId": "none",
            "caseId": "MP-01", "status": "Passed", "applicable": True,
            "exclusionRule": "none",
            "attempts": [{
                "sequence": 1, "startedMs": 0, "endedMs": 1, "status": "Passed",
                "witnessIds": ["metadata.roundtrip"], "proofSha256": ["a" * 64],
                "diagnosticCode": "None",
            }],
            "proofSha256": ["a" * 64],
        }
        admitted = evidence.admit_entity("CaseResult", result)
        self.assertEqual(admitted["matrixId"], "none")
        for key, value in (
                ("status", "Skipped"), ("status", "Unknown"), ("matrixId", ""),
                ("runId", "arbitrary-label"), ("proofSha256", ["A" * 64]),
                ("applicable", 1), ("attempts", []), ("extra", True)):
            changed = copy.deepcopy(result)
            changed[key] = value
            with self.subTest(field=key), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("CaseResult", changed)
        for key, value in (
                ("startedMs", -1), ("endedMs", float("nan")), ("endedMs", True),
                ("endedMs", float("inf")), ("sequence", 0),
                ("diagnosticCode", "synthetic-secret-canary"), ("witnessIds", [])):
            changed = copy.deepcopy(result)
            changed["attempts"][0][key] = value
            with self.subTest(attempt=key), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("CaseResult", changed)

    def test_unknown_entity_and_oversized_json_fail_without_echoing_input(self):
        for data in (b" " * (16 * 1024 * 1024 + 1), b"\xff", b'{"canary":'):
            with self.assertRaises(evidence.ConformanceError) as raised:
                evidence.load_json(data)
            self.assertNotIn("canary", str(raised.exception))
        with self.assertRaises(evidence.ConformanceError):
            evidence.admit_entity("Unknown", {})

    def test_frozen_inventory_has_all_unique_keys_and_exact_durable_exclusions(self):
        inventory = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        entries = inventory["entries"]
        keys = {(x["profileId"], x["bindingId"], x["matrixId"], x["caseId"]) for x in entries}
        expected = {
            (profile, binding, "none", f"{prefix}-{number:02}")
            for profile, bindings, prefix in (
                ("metadata", ("sqlite", "memory"), "MP"),
                ("artifacts", ("local", "object"), "AS"))
            for binding in bindings for number in range(1, 49)
        }
        self.assertEqual(keys, expected)
        self.assertEqual(len(entries), len(keys))
        self.assertEqual(sum(x["exclusion"] is not None for x in entries), 13)
        self.assertFalse(inventory["qualification"])
        self.assertEqual(inventory["baselineRevision"], "9389016c0285c79f6f515f59805a5a41c69b0767")


class ConformanceInputTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="hoard-conformance-input-test-")).resolve()
        self.parent.chmod(0o700)
        self.addCleanup(shutil.rmtree, self.parent)
        self.repo = self.parent / "repository"
        self.repo.mkdir()
        subprocess.run(["git", "init", "--quiet", str(self.repo)], check=True)
        (self.repo / "src").mkdir()
        (self.repo / "src/check.cs").write_text("immutable source")

    def test_snapshot_binds_actual_source_bytes_and_rejects_changed_and_extra_inputs(self):
        from conformance_execution import OwnedRun
        run = OwnedRun.allocate(self.parent / "run", self.repo, profile="harness")
        snapshot, manifest = evidence.snapshot_sources(self.repo, run)
        self.assertEqual(set(manifest), {"src/check.cs"})
        evidence.verify_snapshot(snapshot, manifest)
        self.assertEqual(manifest["src/check.cs"], evidence.file_sha256(self.repo / "src/check.cs"))
        (self.repo / "src/check.cs").write_text("changed source")
        self.assertNotEqual(evidence.digest(evidence.source_manifest(self.repo)), evidence.digest(manifest))
        unexpected = snapshot / "src/extra.cs"
        unexpected.write_text("extra input")
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.verify_snapshot(snapshot, manifest)
        unexpected.unlink()
        original = snapshot / "src/check.cs"
        original.chmod(0o600)
        original.write_text("changed snapshot")
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.verify_snapshot(snapshot, manifest)
        run.transition("Settling")
        run.release()

    def test_exact_parameter_witnesses_cannot_borrow_counts_labels_or_input_hashes(self):
        run_id, group_id = str(uuid.uuid4()), str(uuid.uuid4())
        witness = {
            "executionId": str(uuid.uuid4()), "runId": run_id, "invocationGroupId": group_id,
            "testIdentity": 'Tests.Behavior(provider: "sqlite", shape: "null")',
            "bindingId": "sqlite", "matrixId": "none", "packageSha256": "a" * 64,
            "assemblySha256": "b" * 64, "inputSha256": "c" * 64, "proofSha256": "d" * 64,
            "startedMs": 0, "endedMs": 1, "status": "Passed",
        }
        def ingest(value):
            return evidence.ingest_witnesses(
                json.dumps(value).encode(), run_id=run_id, invocation_group_id=group_id,
                input_sha256="c" * 64, package_sha256="a" * 64, assembly_sha256="b" * 64,
                expected_tests={witness["testIdentity"]})
        self.assertEqual(len(ingest([witness])), 1)
        for key, value in (
                ("executionId", "label"), ("runId", str(uuid.uuid4())),
                ("testIdentity", 'Tests.Behavior(provider: "sqlite", shape: "omitted")'),
                ("packageSha256", "e" * 64), ("assemblySha256", "e" * 64),
                ("inputSha256", "e" * 64), ("status", "Incomplete")):
            changed = dict(witness, **{key: value})
            with self.subTest(field=key), self.assertRaises(evidence.ConformanceError):
                ingest([changed])
        for changed in ([], [witness, witness]):
            with self.assertRaises(evidence.ConformanceError):
                ingest(changed)


if __name__ == "__main__":
    unittest.main()
