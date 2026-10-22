import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid
from unittest.mock import MagicMock, patch

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

    def test_actual_recovery_readback_requires_exact_run_hashes_outcomes_and_all_observations(self):
        content = hashlib.sha256(bytes((index * 17 + 11) % 256 for index in range(1048576))).hexdigest()
        control = b"acknowledged independent control before crash"
        control_hash = hashlib.sha256(control).hexdigest()
        state = {"Run": "current", "Barrier": "D1", "TargetDigest": content, "TargetLength": 1048576,
                 "Control": {"Digest": control_hash, "Length": len(control)}}
        observed = {"eventName": "recovered", "provider": "local", "qualification": False,
                    "pid": 43, "runId": "current", "barrier": "D1", "outcome": "Removed",
                    "reconstructed": False, "reclamation": "Reclaimed",
                    "contentSha256": content, "contentLength": 1048576,
                    "controlSha256": control_hash, "controlLength": len(control),
                    **{key: True for key in ("controlReadback", "controlReceipt", "exactReceipt",
                                            "contentReadback", "ownerFenced", "noDuplicateEffect")}}
        artifact.validate_recovery_readback(observed, state, "D1", "current", 43)
        for field, value in (("runId", "foreign"), ("pid", 42), ("provider", "object"),
                             ("qualification", True), ("contentSha256", "c" * 64),
                             ("controlLength", 0), ("outcome", "AlreadyAbsent"),
                             ("reconstructed", True), ("reclamation", "Pending"),
                             ("ownerFenced", False), ("exactReceipt", False), ("noDuplicateEffect", False)):
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                artifact.validate_recovery_readback({**observed, field: value}, state, "D1", "current", 43)

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

    def test_metadata_inputs_allow_only_local_package_hash_refresh(self):
        old = self.work / "baseline/packages.lock.json"
        new = self.work / "current/packages.lock.json"
        old.parent.mkdir()
        new.parent.mkdir()
        lock = {"version": 1, "dependencies": {"net10.0": {
            "Hoard.Abstractions": {
                "type": "Direct", "requested": "[0.1.0, 0.1.0]", "resolved": "0.1.0",
                "contentHash": base64.b64encode(b"a" * 64).decode()},
            "External.Package": {
                "type": "Transitive", "resolved": "1.0.0",
                "contentHash": base64.b64encode(b"b" * 64).decode()}}}}
        old.write_text(json.dumps(lock))
        new.write_text(json.dumps(lock))
        artifact.verify_metadata_input(old, new)
        changed = copy.deepcopy(lock)
        changed["dependencies"]["net10.0"]["Hoard.Abstractions"]["contentHash"] = base64.b64encode(b"c" * 64).decode()
        new.write_text(json.dumps(changed))
        artifact.verify_metadata_input(old, new)

        for package, field, value in (
                ("Hoard.Abstractions", "resolved", "0.1.1"),
                ("Hoard.Abstractions", "requested", "[0.1.0, 0.2.0]"),
                ("Hoard.Abstractions", "dependencies", {"New.Dependency": "1.0.0"}),
                ("Hoard.Abstractions", "contentHash", "invalid"),
                ("Hoard.Abstractions", "contentHash", base64.b64encode(b"short").decode()),
                ("External.Package", "contentHash", "c" * 88)):
            changed = copy.deepcopy(lock)
            changed["dependencies"]["net10.0"][package][field] = value
            new.write_text(json.dumps(changed))
            with self.subTest(package=package, field=field), self.assertRaises(RuntimeError):
                artifact.verify_metadata_input(old, new)
        for name in ("Fixture.cs", "Fixture.csproj"):
            prior = old.with_name(name)
            current = new.with_name(name)
            prior.write_text("original")
            current.write_text("changed")
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                artifact.verify_metadata_input(prior, current)

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
        for timed_out in (False, True):
            child = MagicMock(pid=42, returncode=7)
            child.__enter__.return_value = child
            child.communicate.side_effect = (
                [subprocess.TimeoutExpired("child", 600), ("synthetic-private-canary", None)]
                if timed_out else [("synthetic-private-canary", None)])
            with self.subTest(timed_out=timed_out), \
                    patch.object(artifact.subprocess, "Popen", return_value=child) as start, \
                    patch.object(artifact, "command_processes", create=True,
                                 side_effect=[{42, 43}, set()]) as processes, \
                    patch.object(artifact.os, "kill") as kill, \
                    self.assertRaises(RuntimeError) as caught:
                artifact.run("fixture")
            self.assertNotIn("synthetic-private-canary", str(caught.exception))
            self.assertIs(True, start.call_args.kwargs.get("start_new_session"))
            if timed_out:
                self.assertEqual({42, 43}, {call.args[0] for call in kill.call_args_list})
                self.assertTrue(all(call.args[1] == artifact.signal.SIGKILL for call in kill.call_args_list))
                self.assertLessEqual(child.communicate.call_args.kwargs["timeout"], 10)
            else:
                kill.assert_not_called()
                processes.assert_not_called()

    def test_timeout_with_unsettled_pipe_reports_cleanup_incomplete_not_success(self):
        child = MagicMock(pid=42, returncode=None)
        child.__enter__.return_value = child
        child.communicate.side_effect = subprocess.TimeoutExpired("child", 600)
        with patch.object(artifact.subprocess, "Popen", return_value=child), \
                patch.object(artifact, "command_processes", create=True, return_value={42}), \
                patch.object(artifact.os, "kill") as kill, \
                self.assertRaisesRegex(RuntimeError, "cleanup incomplete"):
            artifact.run("fixture")
        kill.assert_called_once_with(child.pid, artifact.signal.SIGKILL)

    def test_actual_timeout_stops_owned_descendant_and_preserves_unrelated_child(self):
        marker = self.work / "descendant.json"
        descendant = (
            "import json,os,time; from pathlib import Path; "
            f"Path({str(marker)!r}).write_text(json.dumps([os.getpid(),os.getpgrp()])); "
            "time.sleep(60)"
        )
        command = (
            "import subprocess,sys,time; "
            f"subprocess.Popen([sys.executable,'-c',{descendant!r}]); "
            "time.sleep(60)"
        )
        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
        try:
            with patch.object(artifact, "COMMAND_TIMEOUT_SECONDS", 2), \
                    self.assertRaisesRegex(RuntimeError, "finite deadline"):
                artifact.run(sys.executable, "-c", command)
            self.assertTrue(marker.is_file(), "The real descendant must exist before timeout.")
            descendant_pid, group = json.loads(marker.read_text())
            self.assertNotEqual(descendant_pid, group)
            self.assertEqual(set(), artifact.command_processes(group))
            self.assertIsNone(unrelated.poll())
        finally:
            if marker.is_file():
                _, group = json.loads(marker.read_text())
                for pid in artifact.command_processes(group):
                    os.kill(pid, artifact.signal.SIGKILL)
            if unrelated.poll() is None:
                unrelated.kill()
            unrelated.wait(timeout=10)

    def test_interrupted_command_settles_owned_children_before_propagating(self):
        child = MagicMock(pid=42, returncode=-9)
        child.communicate.side_effect = [KeyboardInterrupt(), ("private-canary", None)]
        with patch.object(artifact.subprocess, "Popen", return_value=child), \
                patch.object(artifact, "command_processes", side_effect=[{42, 43}, set()]), \
                patch.object(artifact.os, "kill") as kill, \
                self.assertRaises(KeyboardInterrupt):
            artifact.run("fixture")
        self.assertEqual({42, 43}, {call.args[0] for call in kill.call_args_list})

    def test_command_processes_selects_only_live_members_of_its_owned_session(self):
        output = "42 42 S\n43 42 R\n44 42 Z\n99 99 S\n"
        with patch.object(artifact.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0, output, "")):
            self.assertEqual({42, 43}, artifact.command_processes(42))

    def test_focused_modes_never_qualify_even_with_complete_inventory(self):
        for phase in ("logical", "transfers", "recovery", "packages"):
            with self.subTest(phase=phase), self.assertRaises(RuntimeError):
                artifact.verify_manifest({"qualification": True, "phase": phase},
                                         self.work, "a" * 64)

    def test_package_phase_runs_real_compatibility_and_never_qualifies(self):
        destination = self.work / "package-phase"
        destination.mkdir()
        with patch.object(artifact, "create_workspace", return_value=destination), \
                patch.object(artifact, "prepare_baseline"), patch.object(artifact, "prepare_packages"), \
                patch.object(artifact, "package_checks", create=True, return_value={"testsPassed": 1}) as checks, \
                patch.object(artifact, "source_hash", return_value="a" * 64), \
                patch.object(sys, "argv", ["artifact_evidence", str(ROOT), "--phase", "packages",
                                          "--evidence", str(destination)]):
            self.assertEqual(0, artifact.main())
        checks.assert_called_once_with(ROOT, destination)
        manifest = json.loads((destination / "manifest.json").read_text())
        self.assertIs(False, manifest["qualification"])
        self.assertEqual("packages", manifest["phase"])
