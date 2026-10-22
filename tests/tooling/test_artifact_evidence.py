import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import artifact_evidence as artifact


class ArtifactEvidenceTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / ".foundation" / "artifact-tooling"
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.work = parent / uuid.uuid4().hex
        self.work.mkdir(mode=0o700)
        self.addCleanup(shutil.rmtree, self.work)

    def proof(self, name, value):
        path = self.work / name
        path.write_text(json.dumps(value))
        return {"proof": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def cases(self):
        proof = self.proof("synthetic.json", {"synthetic": "verifier-only"})
        return [
            {"id": f"AS-{number:02}", "provider": provider,
             "class": "L" if number <= 40 else "D" if number <= 44 else "Q",
             "result": "NotApplicable" if provider == "object" and 41 <= number <= 44 else "Passed",
             "reason": "simulation: no durable restart" if provider == "object" and 41 <= number <= 44 else "",
             "runId": "current", "durationMs": 1, "positive": True, "negative": True,
             "tests": ["synthetic-verifier-only"], **proof}
            for provider in ("local", "object") for number in range(1, 49)]

    def test_exact_inventory_rejects_missing_duplicate_foreign_stale_and_failed(self):
        cases = self.cases()
        artifact.verify_cases(cases, self.work, "current")
        for changed in (None, [], cases[:-1], cases + [cases[0]]):
            with self.subTest(kind=type(changed).__name__), self.assertRaises(RuntimeError):
                artifact.verify_cases(changed, self.work, "current")
        for field, value in (
                ("id", "AS-99"), ("provider", "foreign"), ("runId", "stale"),
                ("result", "Skipped"), ("result", "Failed"), ("class", "D"),
                ("positive", False), ("negative", False), ("tests", []),
                ("durationMs", -1), ("durationMs", True), ("durationMs", float("nan")),
                ("sha256", "a" * 64)):
            changed = copy.deepcopy(cases)
            changed[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                artifact.verify_cases(changed, self.work, "current")

    def test_exactly_four_object_durable_exclusions_not_skips_or_passes(self):
        cases = self.cases()
        for result in ("Passed", "Skipped", "Failed"):
            changed = copy.deepcopy(cases)
            changed[88]["result"] = result
            with self.subTest(result=result), self.assertRaises(RuntimeError):
                artifact.verify_cases(changed, self.work, "current")
        changed = copy.deepcopy(cases)
        changed[88]["reason"] = "not tested"
        with self.assertRaises(RuntimeError):
            artifact.verify_cases(changed, self.work, "current")

    def transfer(self):
        return {
            "provider": "local", "runId": "current", "pid": 42, "runtime": ".NET 10",
            "size": 4294967296, "written": 4294967296, "read": 4294967296,
            "expectedSha256": "a" * 64, "sourceSha256": "a" * 64, "sinkSha256": "a" * 64,
            "baselineRssBytes": 40_000_000, "osPeakRssBytes": 80_000_000,
            "sampledPeakRssBytes": 70_000_000, "rssUnits": "bytes",
            "osPeakMethod": "getrusage", "samples": 20, "exitCode": 0,
            "bufferBytes": 262144, "providerBufferLimit": 2097152, "slots": 1,
            "sourcePaced": True, "sinkPaced": True, "nonSeekable": True,
            "generated": True, "independentExpectedHash": True, "warmupComplete": True}

    def test_transfer_proof_rejects_small_sparse_unmeasured_or_unbounded_runs(self):
        proof = self.transfer()
        artifact.verify_transfer(proof, "local", 4294967296, "current")
        for field, value in (
                ("size", 1024), ("written", 1024), ("read", 1024), ("pid", 0),
                ("runId", "old"), ("provider", "object"), ("sinkSha256", "b" * 64),
                ("sourceSha256", "b" * 64), ("expectedSha256", ""),
                ("osPeakRssBytes", 200_000_000), ("samples", 0), ("rssUnits", "unknown"),
                ("baselineRssBytes", 0), ("osPeakMethod", "managed allocations"),
                ("sourcePaced", False), ("sinkPaced", False), ("generated", False),
                ("nonSeekable", False), ("independentExpectedHash", False),
                ("warmupComplete", False), ("exitCode", 1), ("bufferBytes", 4194304),
                ("slots", 4)):
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                artifact.verify_transfer({**proof, field: value}, "local", 4294967296, "current")

    def crash(self):
        return {"barrier": "B2", "runId": "current", "provider": "local", "pid": 42,
                "reopenPid": 43, "signal": "SIGKILL", "exitCode": -9, "exitConfirmed": True,
                "handshake": True, "stateCompared": True, "receiptCompared": True,
                "controlReadback": True, "newReadback": True, "ownerFenced": True,
                "noDuplicateEffect": True, "stateSha256": "a" * 64}

    def test_crash_proof_rejects_exception_graceful_exit_foreign_or_missing_barrier(self):
        proof = self.crash()
        artifact.verify_crash(proof, "B2", "current")
        for field, value in (
                ("barrier", "B1"), ("runId", "old"), ("provider", "object"), ("pid", 0),
                ("reopenPid", 42), ("signal", "exception"), ("exitCode", 0),
                ("exitConfirmed", False), ("handshake", False), ("controlReadback", False),
                ("newReadback", False), ("receiptCompared", False), ("stateCompared", False),
                ("ownerFenced", False), ("noDuplicateEffect", False), ("stateSha256", "")):
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                artifact.verify_crash({**proof, field: value}, "B2", "current")

    def test_runtime_red_green_requires_assertion_not_compile_failure(self):
        proof = {"id": "bounded-input", "test": "actual-test", "redExit": 1,
                 "redOutcome": "Failed", "redAssertion": True, "greenOutcome": "Passed",
                 "mutationSha256": "a" * 64, "baselineSha256": "b" * 64}
        artifact.verify_red_green([proof])
        for field, value in (
                ("redExit", 0), ("redAssertion", False), ("redOutcome", "CompileFailed"),
                ("greenOutcome", "Skipped"), ("mutationSha256", "b" * 64)):
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                artifact.verify_red_green([{**proof, field: value}])
        with self.assertRaises(RuntimeError):
            artifact.verify_red_green([])

    def test_unfinished_full_manifest_never_qualifies(self):
        for manifest in (None, {}, {"qualification": True}, {
                "schemaVersion": 1, "qualification": True, "production": False,
                "sourceSha256": "a" * 64, "runId": "current", "cases": self.cases()}):
            with self.subTest(manifest=str(manifest)[:60]), self.assertRaises(RuntimeError):
                artifact.verify_manifest(manifest, self.work, "a" * 64)

    def test_proof_rejects_escape_symlink_missing_and_hash_tampering(self):
        artifact.proof_file(self.work, self.proof("valid.json", {})["proof"])
        (self.work / "link").symlink_to(self.work / "valid.json")
        for name in ("../valid.json", str(self.work / "valid.json"), "link", "absent"):
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                artifact.proof_file(self.work, name)
        cases = self.cases()
        (self.work / "synthetic.json").write_text('{"changed":true}')
        with self.assertRaises(RuntimeError):
            artifact.verify_cases(cases, self.work, "current")

    def test_source_lock_and_package_hash_drift_rejects(self):
        proof = self.proof("source.json", {})
        entries = [{"id": "source", **proof}]
        artifact.verify_files(entries, self.work, ("source",))
        for changed in ([], entries + entries, [{**entries[0], "sha256": "f" * 64}]):
            with self.assertRaises(RuntimeError):
                artifact.verify_files(changed, self.work, ("source",))
        locks = artifact.lock_hashes(ROOT)
        with self.assertRaises(RuntimeError):
            artifact.verify_locks(ROOT, {**locks, "foreign/packages.lock.json": "a" * 64})

    def test_cleanup_requires_owned_exact_root_and_settled_children(self):
        with self.assertRaises(RuntimeError):
            artifact.cleanup_workspace(self.work)
        owned = artifact.create_workspace(self.work / "owned", self.work / "repository")
        with self.assertRaises(RuntimeError):
            artifact.cleanup_workspace(self.work)
        artifact.cleanup_workspace(owned)
        self.assertTrue(self.work.is_dir())
        self.assertFalse(owned.exists())

    def test_destination_rejects_existing_inside_repository_and_symlinked_parent(self):
        (self.work / "link").symlink_to(self.work, target_is_directory=True)
        for target in (self.work, ROOT / ".foundation/unsafe", self.work / "link/child"):
            with self.subTest(target=str(target)), self.assertRaises(RuntimeError):
                artifact.create_workspace(target, ROOT)

    def test_failed_child_and_timeout_fail_without_exposing_output(self):
        for outcome in (subprocess.CompletedProcess([], 7, "synthetic-private-canary"),
                        subprocess.TimeoutExpired("child", 600)):
            with patch.object(artifact.subprocess, "run",
                              side_effect=outcome if isinstance(outcome, Exception) else None,
                              return_value=outcome), self.assertRaises(RuntimeError) as caught:
                artifact.run("fixture")
            self.assertNotIn("synthetic-private-canary", str(caught.exception))

    def test_focused_modes_never_qualify_even_with_complete_inventory(self):
        for phase in ("logical", "transfers", "recovery", "packages"):
            with self.subTest(phase=phase), self.assertRaises(RuntimeError):
                artifact.verify_manifest({"qualification": True, "phase": phase},
                                         self.work, "a" * 64)
