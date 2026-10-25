import errno
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_execution as execution
from conformance_evidence import ConformanceError
NATIVE_CONTAINMENT = sys.platform == "linux" and os.uname().machine in ("x86_64", "aarch64")


class ConformanceExecutionTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="hoard-conformance-test-")).resolve()
        self.parent.chmod(0o700)
        self.addCleanup(shutil.rmtree, self.parent)

    def workspace(self):
        return execution.OwnedRun.allocate(self.parent / "run", ROOT)

    def test_rejects_existing_foreign_symlink_and_nonprivate_roots(self):
        sentinel = self.parent / "sentinel"
        sentinel.mkdir()
        (sentinel / "outside").write_text("untouched")
        link = self.parent / "linked"
        link.symlink_to(sentinel, target_is_directory=True)
        for destination in (sentinel, link, link / "child", sentinel / "../escaped",
                            ROOT / ".foundation/conformance-test"):
            with self.subTest(destination=destination), self.assertRaises(ConformanceError):
                execution.OwnedRun.allocate(destination, ROOT)
        self.parent.chmod(0o755)
        with self.assertRaises(ConformanceError):
            execution.OwnedRun.allocate(self.parent / "public", ROOT)
        self.parent.chmod(0o700)
        self.assertEqual((sentinel / "outside").read_text(), "untouched")
        self.assertFalse((sentinel / "child").exists())

    def test_private_roots_and_subresources_are_run_owned_and_single_writer(self):
        run = self.workspace()
        self.assertEqual(stat.S_IMODE(run.root.stat().st_mode), 0o700)
        self.assertEqual({path.name for path in run.root.iterdir()},
                         {"ownership.json", "stores", "feed", "cache", "diagnostics", "proofs"})
        preflight = json.loads((run.root / "proofs/preflight.json").read_bytes())
        self.assertFalse(preflight["qualification"])
        self.assertGreaterEqual(preflight["freeBytes"], 24 * 1024**3)
        self.assertGreaterEqual(preflight["durationMs"], 0)
        if NATIVE_CONTAINMENT:
            self.assertNotEqual(preflight["filesystem"], "unobserved")
        with self.assertRaises(ConformanceError):
            execution.OwnedRun.allocate(run.root, ROOT)
        with self.assertRaises(ConformanceError):
            run.transition("Released")
        run.transition("Active")
        run.transition("Settling")
        run.release()
        self.assertEqual(json.loads((run.root / "ownership.json").read_bytes())["state"], "Released")
        self.assertFalse(any((run.root / name).exists() for name in ("stores", "feed", "cache")))

    def test_release_preserves_evidence_and_persists_authoritative_resource_projection(self):
        run = self.workspace()
        proof = run.root / "proofs" / "result.json"
        diagnostic = run.root / "diagnostics" / "prior.jsonl"
        proof.write_bytes(b'{"caseId":"MP-01"}')
        diagnostic.write_bytes(b'{"event":"control","code":"None","value":1}\n')
        (run.root / "stores" / "synthetic.db").write_bytes(b"synthetic-test-data")
        run.transition("Settling")
        run.release()
        self.assertEqual(proof.read_bytes(), b'{"caseId":"MP-01"}')
        self.assertEqual(diagnostic.read_bytes(), b'{"event":"control","code":"None","value":1}\n')
        ledger = json.loads((run.root / "ownership.json").read_bytes())
        self.assertEqual(ledger["state"], "Released")
        self.assertEqual(ledger["cleanupAttempts"][0]["diagnosticCode"], "None")
        projection, = run.resource_projection()
        self.assertEqual(projection["state"], "Released")
        self.assertEqual(projection["childPid"], 0)
        self.assertEqual(projection["childStartSha256"], "0" * 64)
        self.assertGreaterEqual(projection["cleanupDurationMs"], 0)
        self.assertEqual(projection["diagnosticCode"], "None")
        with self.assertRaises(TypeError):
            projection["state"] = "Retained"
        with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
            run.command([sys.executable, "-c", "raise AssertionError('must not execute')"])

    def test_live_work_is_retained_then_retry_records_exit_without_erasing_the_failure(self):
        run = self.workspace()
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            run.children[child.pid] = execution.process_identity(child.pid)
            run.transition("Settling")
            with self.assertRaisesRegex(ConformanceError, "CleanupIncomplete"):
                run.release()
            self.assertEqual(run.state, "Retained")
            projection, = run.resource_projection()
            self.assertEqual(projection["childPid"], child.pid)
            self.assertEqual(projection["childStartSha256"], run.children[child.pid])
            self.assertEqual(projection["diagnosticCode"], "CleanupIncomplete")
            self.assertTrue((run.root / "stores").is_dir())
        finally:
            child.kill()
            child.wait(timeout=5)
        run.transition("Settling")
        run.release()
        ledger = json.loads((run.root / "ownership.json").read_bytes())
        self.assertEqual([attempt["diagnosticCode"] for attempt in ledger["cleanupAttempts"]],
                         ["CleanupIncomplete", "None"])
        self.assertEqual(ledger["state"], "Released")

    def test_failed_release_publication_cannot_claim_release_and_retry_keeps_evidence(self):
        run = self.workspace()
        proof = run.root / "proofs" / "result.json"
        proof.write_bytes(b'{"caseId":"MP-01"}')
        run.transition("Settling")
        original = execution.os.rename
        def failing_publication(*args, **kwargs):
            if json.loads((run.root / "ownership.next").read_bytes())["state"] == "Released":
                raise OSError("synthetic ledger failure")
            return original(*args, **kwargs)
        with mock.patch.object(execution.os, "rename", side_effect=failing_publication):
            with self.assertRaisesRegex(ConformanceError, "CleanupIncomplete"):
                run.release()
        self.assertEqual(run.state, "Retained")
        self.assertEqual(json.loads((run.root / "ownership.json").read_bytes())["state"], "Retained")
        self.assertEqual(proof.read_bytes(), b'{"caseId":"MP-01"}')
        run.transition("Settling")
        run.release()
        self.assertEqual([attempt["diagnosticCode"] for attempt in run.cleanup_attempts],
                         ["CleanupIncomplete", "None"])
        self.assertEqual(run.resource_projection()[0]["state"], "Released")

    def test_foreign_staging_marker_is_not_overwritten_or_removed_on_publication_failure(self):
        run = self.workspace()
        marker = run.root / "ownership.next"
        marker.write_bytes(b"foreign-staging-sentinel")
        with self.assertRaises(OSError):
            run.transition("Active")
        self.assertEqual(marker.read_bytes(), b"foreign-staging-sentinel")
        self.assertEqual(run.state, "Allocated")
        marker.unlink()
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_concurrent_runs_isolate_cache_inputs_and_containment_does_not_end_the_other_child(self):
        first = self.workspace()
        second = execution.OwnedRun.allocate(self.parent / "second", ROOT)
        code = (
            "import json,os,time\nfrom pathlib import Path\n"
            "root=Path(os.environ['HOME']).parent\ncache=Path(os.environ['NUGET_PACKAGES'])\n"
            "(cache/'same-key').write_text(os.environ['HOARD_VALUE'])\n"
            "(root/'stores/entered').write_text('entered')\n"
            "deadline=time.monotonic()+12\n"
            "while not (root/'stores/release').exists():\n"
            " if time.monotonic()>deadline: raise RuntimeError('deadline')\n"
            " time.sleep(0.01)\n"
            "print(json.dumps({'event':'control','code':'None','value':int((cache/'same-key').read_text())}))"
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            interrupted = executor.submit(
                first.command, [sys.executable, "-c", code], timeout=5, env={"HOARD_VALUE": "1"})
            surviving = executor.submit(
                second.command, [sys.executable, "-c", code], timeout=15, env={"HOARD_VALUE": "2"})
            try:
                deadline = time.monotonic() + 3
                while not all((run.root / "stores/entered").exists() for run in (first, second)):
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.01)
                self.assertEqual((first.root / "cache/default/same-key").read_text(), "1")
                self.assertEqual((second.root / "cache/default/same-key").read_text(), "2")
                with self.assertRaisesRegex(ConformanceError, "DeadlineExceeded"):
                    interrupted.result(timeout=10)
                self.assertFalse(first.live_children())
                self.assertTrue(second.live_children())
            finally:
                (second.root / "stores/release").write_text("release")
            observed = surviving.result(timeout=10)
        self.assertEqual(observed.exit_code, 0)
        self.assertEqual(observed.events[0]["value"], 2)
        for run in (first, second):
            run.transition("Settling")
            run.release()
            self.assertFalse(any((run.root / name).exists() for name in ("stores", "feed", "cache")))
            self.assertEqual(run.state, "Released")

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_bounded_safe_events_are_retained_without_raw_canary(self):
        run = self.workspace()
        input_file = run.root / "stores/command-input.json"
        input_file.write_bytes(b"one")
        input_file.chmod(0o400)
        arguments = [sys.executable, "-c",
                     'from pathlib import Path; assert Path("stores/command-input.json").read_bytes() == b"one"; '
                     'print(\'{"event":"control","code":"None","value":3}\')']
        result = run.command(arguments, cwd=run.root, record_execution=True,
                             execution_inputs=("stores/command-input.json",))
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.events[0]["value"], 3)
        path = run.root / "proofs/execution-command-0001.json"
        receipt = json.loads(path.read_bytes())
        self.assertEqual(result.execution_record_sha256, execution.hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(run.read_execution_record(1), path.read_bytes())
        original = path.read_bytes()
        path.chmod(0o600)
        path.write_bytes(execution.canonical_bytes({**receipt, "argvSha256": "0" * 64}))
        path.chmod(0o400)
        with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
            run.read_execution_record(1)
        path.chmod(0o600)
        path.write_bytes(original)
        path.chmod(0o400)
        unowned = run.root / "proofs/execution-command-0002.json"
        unowned.write_bytes(execution.canonical_bytes({**receipt, "sequence": 2}))
        unowned.chmod(0o400)
        with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
            run.read_execution_record(2)
        unowned.unlink()
        self.assertEqual(receipt["argvSha256"], execution.hashlib.sha256(execution.canonical_bytes(arguments)).hexdigest())
        self.assertEqual(receipt["runId"], run.run_id)
        self.assertEqual(receipt["exitCode"], 0)
        self.assertEqual(receipt["groupState"], "Exited")
        self.assertEqual(receipt["inputFiles"], {"stores/command-input.json": execution.hashlib.sha256(b"one").hexdigest()})
        self.assertNotEqual(receipt["childStartSha256"], "0" * 64)
        self.assertGreater(receipt["childPid"], 1)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)
        with self.assertRaisesRegex(ConformanceError, "UnknownDiagnostic"):
            run.command([sys.executable, "-c",
                         'print(\'{"event":"control","code":"None","value":4}\'); '
                         'print("synthetic-secret-canary/private/path")'], record_execution=True)
        failure = json.loads((run.root / "proofs/execution-command-0002.json").read_bytes())
        self.assertEqual(failure["diagnosticCode"], "UnknownDiagnostic")
        self.assertEqual(run.read_execution_record(1), original)
        self.assertEqual(json.loads(run.read_execution_record(2)), failure)
        with self.assertRaisesRegex(ConformanceError, "InputChanged"):
            run.command([
                sys.executable, "-c",
                'from pathlib import Path; p = Path("stores/command-input.json"); p.chmod(0o600); '
                'p.write_bytes(b"two"); p.write_bytes(b"one"); p.chmod(0o400); '
                'print(\'{"event":"control","code":"None","value":1}\')',
            ], cwd=run.root, record_execution=True, execution_inputs=("stores/command-input.json",))
        self.assertEqual(json.loads(run.read_execution_record(3))["diagnosticCode"], "InputChanged")
        self.assertEqual([json.loads(line) for line in
                          (run.root / "diagnostics/command-0002.jsonl").read_bytes().splitlines()], [
                              {"event": "control", "code": "None", "value": 4},
                              {"event": "control", "code": "UnknownDiagnostic", "value": 0},
                          ])
        for path in (run.root / "diagnostics").rglob("*"):
            if path.is_file():
                self.assertNotIn(b"synthetic-secret-canary", path.read_bytes())
                self.assertNotIn(b"/private/path", path.read_bytes())
        for path in (run.root / "proofs").glob("execution-command-*.json"):
            self.assertNotIn(b"synthetic-secret-canary", path.read_bytes())
            self.assertNotIn(b"/private/path", path.read_bytes())
        self.assertFalse(any(path.suffix in (".trx", ".log") for path in run.root.rglob("*")))
        run.transition("Settling")
        run.release()

    def test_execution_receipt_requests_are_boolean_and_reject_before_launch(self):
        run = self.workspace()
        with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
            run.read_execution_record(1)
        with mock.patch.object(execution.subprocess, "Popen") as launch:
            for paths in (None, {}, ["../outside"], ["same", "same"], ["input"] * 17):
                with self.subTest(paths=paths), self.assertRaises(ConformanceError):
                    run.command([sys.executable], record_execution=True, execution_inputs=paths)
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                run.command([sys.executable], execution_inputs=["input"])
            with mock.patch.object(execution, "MAX_PROOF_FILES", 0):
                with self.assertRaisesRegex(ConformanceError, "OutputLimitExceeded"):
                    run.command([sys.executable], record_execution=True)
            with mock.patch.object(execution, "MAX_PROOF_BYTES", 0):
                with self.assertRaisesRegex(ConformanceError, "OutputLimitExceeded"):
                    run.command([sys.executable], record_execution=True)
            for value in (None, 0, 1, "true", {}):
                with self.subTest(value=value), self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                    run.command([sys.executable, "-c", "raise AssertionError()"], record_execution=value)
            for arguments in ([sys.executable, "a" * 65537], [sys.executable, "\u00e9" * 40000],
                              ["argument"] * 1025):
                with self.subTest(size=len(arguments)), self.assertRaisesRegex(ConformanceError, "OutputLimitExceeded"):
                    run.command(arguments, record_execution=True)
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                run.command([sys.executable], scope="cleanup", record_execution=True)
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                run.command([sys.executable, "\ud800"], record_execution=True)
            launch.assert_not_called()
        self.assertEqual(run.command_sequence, 0)
        self.assertFalse(tuple((run.root / "proofs").glob("execution-command-*.json")))
        run.transition("Settling")
        run.release()

    def test_execution_input_snapshots_detect_rewrites_even_when_bytes_are_restored(self):
        run = self.workspace()
        path = run.root / "stores/command-input.json"
        path.write_bytes(b"one")
        path.chmod(0o400)
        original = run._capture_execution_inputs(("stores/command-input.json",), time.monotonic() + 5)
        self.assertEqual(original["stores/command-input.json"][0], execution.hashlib.sha256(b"one").hexdigest())
        self.assertEqual(
            run._capture_execution_inputs(("stores/command-input.json",), time.monotonic() + 5), original)
        path.chmod(0o600)
        with self.assertRaisesRegex(ConformanceError, "InputChanged"):
            run._capture_execution_inputs(("stores/command-input.json",), time.monotonic() + 5)
        path.write_bytes(b"two")
        path.write_bytes(b"one")
        path.chmod(0o400)
        changed = run._capture_execution_inputs(("stores/command-input.json",), time.monotonic() + 5)
        self.assertEqual(changed["stores/command-input.json"][0], original["stores/command-input.json"][0])
        self.assertNotEqual(changed, original)
        run.transition("Settling")
        run.release()

    def test_safe_event_size_is_bounded_before_json_expansion_without_truncation(self):
        event = b'{"event":"control","code":"None","value":1}'
        self.assertEqual(execution.project_event(event.ljust(1024))["value"], 1)
        for value in (event.ljust(1025), b'{"extra":[' + b"0," * 32768 + b"0]}"):
            with self.subTest(size=len(value)), self.assertRaisesRegex(ConformanceError, "OutputLimitExceeded"):
                execution.project_event(value)

    def test_test_projection_accepts_only_finite_vstest_scaffolding_and_closed_events(self):
        for line in (b"", b"Starting test execution, please wait...",
                     b"VSTest version 18.3.0 (arm64)", b"VSTest version 18.3.0 (x64)"):
            self.assertIsNone(execution.project_test_line(line))
        self.assertEqual(execution.project_test_line(
            b'{"event":"control","code":"None","value":3}')["value"], 3)
        for line in (b"Starting test execution, please wait... /private/canary",
                     b"VSTest version private-canary (x64)", b"Test run for /private/canary.dll",
                     b"Passed!  - Failed: 0, Passed: 100", b"\xff"):
            with self.subTest(line=line), self.assertRaisesRegex(ConformanceError, "UnknownDiagnostic"):
                execution.project_test_line(line)

    def test_discovery_projection_requires_exact_frozen_names_and_never_accepts_substrings(self):
        names = frozenset({"Hoard.Tests.Check(value: 1)", "Hoard.Tests.Check(value: 2)"})
        for line in (b"The following Tests are available:", b"    Hoard.Tests.Check(value: 1)"):
            self.assertIsNone(execution.project_discovery_line(line, names))
        for line in (b"Hoard.Tests.Check(value: 3)", b"Hoard.Tests", b"/private/canary",
                     b"    Hoard.Tests.Check(value: 1) private-canary", b"\xff"):
            with self.subTest(line=line), self.assertRaisesRegex(ConformanceError, "UnknownDiagnostic"):
                execution.project_discovery_line(line, names)
        with self.assertRaises(ConformanceError):
            execution.project_discovery_line(b"Hoard.Tests", "Hoard.Tests.Check")

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_diagnostic_parent_swap_cannot_redirect_a_safe_write_outside_its_owned_directory(self):
        run = self.workspace()
        outside = self.parent / "outside-diagnostics"
        outside.mkdir()
        (outside / "sentinel").write_text("untouched")
        program = """
from pathlib import Path
import sys
root, outside = map(Path, sys.argv[1:])
(root / "diagnostics").rename(root / "stores" / "original-diagnostics")
(root / "diagnostics").symlink_to(outside, target_is_directory=True)
print('{"event":"control","code":"None","value":1}')
"""
        try:
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                run.command([sys.executable, "-c", program, str(run.root), str(outside)])
            self.assertEqual({entry.name for entry in outside.iterdir()}, {"sentinel"})
            self.assertEqual((outside / "sentinel").read_text(), "untouched")
            self.assertFalse(run.live_children())
        finally:
            if (run.root / "diagnostics").is_symlink():
                (run.root / "diagnostics").unlink()
                (run.root / "stores" / "original-diagnostics").rename(run.root / "diagnostics")
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_output_flood_is_failure_not_truncated_success_and_child_exits(self):
        run = self.workspace()
        with self.assertRaisesRegex(ConformanceError, "OutputLimitExceeded"):
            run.command([sys.executable, "-c", 'import os; os.write(1,b"x"*131072)'], timeout=5)
        self.assertFalse(run.live_children())
        self.assertEqual(json.loads((run.root / "diagnostics/command-0001.jsonl").read_bytes())["code"],
                         "OutputLimitExceeded")
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_watchdog_terminates_only_owned_process_tree_and_confirms_exit(self):
        run = self.workspace()
        for code in (
                'import subprocess,sys,time; '
                'subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"]); time.sleep(60)',
                "import os,time; os.close(1); os.close(2); time.sleep(60)"):
            with self.subTest(code=code), self.assertRaisesRegex(ConformanceError, "DeadlineExceeded"):
                run.command([sys.executable, "-c", code], scope="recovery", timeout=0.2)
        self.assertFalse(run.live_children())
        for sequence in (1, 2):
            self.assertEqual(json.loads((run.root / "diagnostics" / f"command-{sequence:04}.jsonl").read_bytes())["code"],
                             "DeadlineExceeded")
            receipt = json.loads((run.root / "proofs" / f"recovery-command-{sequence:04}.json").read_bytes())
            self.assertEqual(receipt["sequence"], sequence)
            self.assertGreater(receipt["childPid"], 0)
            self.assertNotEqual(receipt["childPid"], os.getpid())
            self.assertRegex(receipt["childStartSha256"], "^[0-9a-f]{64}$")
            self.assertNotEqual(receipt["childStartSha256"], "0" * 64)
            self.assertEqual(receipt["exitCode"], -9)
            self.assertEqual(receipt["diagnosticCode"], "DeadlineExceeded")
            self.assertEqual(receipt["groupState"], "Exited")
            self.assertGreaterEqual(receipt["endedMs"] - receipt["startedMs"], 200)
        self.assertEqual(run.command([sys.executable, "-c", "pass"], scope="recovery", timeout=5).exit_code, 0)
        normal = json.loads((run.root / "proofs/recovery-command-0003.json").read_bytes())
        self.assertEqual((normal["exitCode"], normal["diagnosticCode"], normal["groupState"]),
                         (0, "None", "Exited"))
        run.transition("Settling")
        run.release()

    def test_barrier_stop_requires_recovery_events_scope_and_a_bounded_target(self):
        run = self.workspace()
        for options in (
                {"stop_at_barrier": True}, {"stop_at_barrier": -1},
                {"stop_at_barrier": 65536}, {"stop_at_barrier": 1.0},
                {"stop_at_barrier": "M0"}, {"stop_at_barrier": 7, "scope": "ordinary"},
                {"stop_at_barrier": 7, "kind": "build"},
                {"stop_at_barrier": 7, "timeout": 15.1}):
            with self.subTest(options=options), mock.patch.object(execution.subprocess, "Popen") as launch:
                with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                    run.command([sys.executable, "-c", "pass"],
                                **({"scope": "recovery"} | options))
                launch.assert_not_called()
        self.assertEqual(run.command_sequence, 0)
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_observed_barrier_precedes_owned_signal_and_confirmed_process_tree_exit(self):
        run = self.workspace()
        program = (
            "import subprocess,sys,time; "
            "subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
            "print('{\"event\":\"barrier\",\"code\":\"None\",\"value\":7}',flush=True); time.sleep(60)")
        result = run.command(
            [sys.executable, "-c", program], scope="recovery", stop_at_barrier=7, record_execution=True)
        self.assertEqual(result.exit_code, -9)
        self.assertEqual([dict(event) for event in result.events],
                         [{"event": "barrier", "code": "None", "value": 7}])
        self.assertFalse(run.live_children())
        receipt = json.loads((run.root / "proofs/recovery-command-0001.json").read_bytes())
        self.assertEqual((receipt["exitCode"], receipt["diagnosticCode"], receipt["groupState"]),
                         (-9, "None", "Exited"))
        self.assertNotEqual(receipt["childStartSha256"], "0" * 64)
        barrier = receipt["barrier"]
        self.assertEqual(set(barrier), {"value", "observedMs", "signalMs"})
        self.assertEqual(barrier["value"], 7)
        self.assertLessEqual(receipt["startedMs"], barrier["observedMs"])
        self.assertLessEqual(barrier["observedMs"], barrier["signalMs"])
        self.assertLessEqual(barrier["signalMs"], receipt["endedMs"])
        control_raw = (run.root / "proofs/recovery-command-0001.json").read_bytes()
        native_raw = run.read_execution_record(1)
        self.assertEqual(hashlib.sha256(native_raw).hexdigest(), result.execution_sha256)
        self.assertEqual(json.loads(native_raw)["controlRecordSha256"], hashlib.sha256(control_raw).hexdigest())
        with mock.patch.object(run, "terminate", return_value=False):
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                run.command([sys.executable, "-c", program], scope="recovery", stop_at_barrier=7)
        self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_normal_exit_without_the_requested_barrier_is_not_a_crash_proof(self):
        run = self.workspace()
        with self.assertRaisesRegex(ConformanceError, "EvidenceIncomplete"):
            run.command([sys.executable, "-c", "pass"], scope="recovery", stop_at_barrier=7)
        receipt = json.loads((run.root / "proofs/recovery-command-0001.json").read_bytes())
        self.assertEqual(receipt["exitCode"], 0)
        self.assertEqual(receipt["diagnosticCode"], "EvidenceIncomplete")
        self.assertEqual(receipt["barrier"], {"value": 7, "observedMs": None, "signalMs": None})
        self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_wrong_repeated_or_unobserved_barriers_cannot_turn_containment_into_success(self):
        run = self.workspace()
        barrier = {"event": "barrier", "code": "None", "value": 7}
        for events, expected in (
                ([barrier | {"value": 8}], "ProofMismatch"),
                ([barrier | {"code": "EvidenceIncomplete"}], "ProofMismatch"),
                ([{"event": "control", "code": "AssertionFailed", "value": 0}, barrier], "ProofMismatch"),
                ([barrier, barrier], "ProofMismatch"),
                ([], "DeadlineExceeded")):
            payload = b"".join(execution.canonical_bytes(event) + b"\n" for event in events)
            program = f"import os,time; os.write(1,{payload!r}); time.sleep(60)"
            with self.subTest(events=events), self.assertRaisesRegex(ConformanceError, expected):
                run.command([sys.executable, "-c", program], scope="recovery",
                            stop_at_barrier=7, timeout=0.5)
            self.assertFalse(run.live_children())
            receipt = json.loads((run.root / "proofs" /
                                  f"recovery-command-{run.command_sequence:04}.json").read_bytes())
            self.assertEqual(receipt["diagnosticCode"], expected)
            self.assertEqual(receipt["groupState"], "Exited")
        run.transition("Settling")
        run.release()

    def test_foreign_process_identity_cannot_be_terminated_or_cleaned(self):
        run = self.workspace()
        run.children[os.getpid()] = "0" * 64
        run.transition("Active")
        run.transition("Settling")
        with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
            run.terminate(os.getpid())
        with self.assertRaises(ConformanceError):
            run.release()
        self.assertTrue(run.root.is_dir())
        del run.children[os.getpid()]
        run.transition("Settling")
        run.release()

    def test_barrier_inspection_requires_a_distinct_owned_recovery_stop_target(self):
        run = self.workspace()
        for options in (
                {"inspect_at_barrier": 60}, {"inspect_at_barrier": True, "stop_at_barrier": 70},
                {"inspect_at_barrier": 60.0, "stop_at_barrier": 70},
                {"inspect_at_barrier": -1, "stop_at_barrier": 70},
                {"inspect_at_barrier": 60, "stop_at_barrier": 60},
                {"inspect_at_barrier": 60, "stop_at_barrier": 70, "kind": "build"}):
            with self.subTest(options=options), mock.patch.object(execution.subprocess, "Popen") as launch:
                with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                    run.command([sys.executable, "-c", "pass"], **({"scope": "recovery"} | options))
                launch.assert_not_called()
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_owned_inspection_observes_both_live_boundaries_before_terminating_the_exact_child(self):
        run = self.workspace()
        program = """
import json,sys,time
print(json.dumps({"event":"barrier","code":"None","value":60}),flush=True)
assert sys.stdin.readline()=="inspect\\n"
print(json.dumps({"event":"barrier","code":"None","value":70}),flush=True)
time.sleep(60)
"""
        result = run.command([sys.executable, "-c", program], scope="recovery",
                             inspect_at_barrier=60, stop_at_barrier=70)
        self.assertEqual(result.exit_code, -9)
        receipt = json.loads((run.root / "proofs/recovery-command-0001.json").read_bytes())
        barrier = receipt["barrier"]
        self.assertEqual(barrier["inspection"]["value"], 60)
        self.assertLessEqual(barrier["inspection"]["observedMs"], barrier["inspection"]["requestMs"])
        self.assertLessEqual(barrier["inspection"]["requestMs"], barrier["observedMs"])
        self.assertLessEqual(barrier["observedMs"], barrier["signalMs"])
        self.assertEqual((receipt["diagnosticCode"], receipt["groupState"]), ("None", "Exited"))
        self.assertFalse(run.live_children())
        for program in (
                'print(\'{"event":"barrier","code":"None","value":70}\',flush=True)',
                'import sys,time; print(\'{"event":"barrier","code":"None","value":60}\',flush=True); '
                'sys.stdin.readline(); print(\'{"event":"barrier","code":"None","value":60}\',flush=True); time.sleep(60)'):
            with self.subTest(program=program), self.assertRaisesRegex(ConformanceError, "ProofMismatch"):
                run.command([sys.executable, "-c", program], scope="recovery",
                            inspect_at_barrier=60, stop_at_barrier=70)
            self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    def test_transfer_measurement_requires_qualified_bytes_and_the_owned_transfer_event_scope(self):
        run = self.workspace()
        for options in (
                {"measure_transfer_bytes": True}, {"measure_transfer_bytes": 1},
                {"measure_transfer_bytes": 268435456.0}, {"measure_transfer_bytes": "268435456"},
                {"measure_transfer_bytes": 268435456, "scope": "ordinary"},
                {"measure_transfer_bytes": 268435456, "kind": "build"},
                {"measure_transfer_bytes": 268435456, "stop_at_barrier": 7}):
            with self.subTest(options=options), mock.patch.object(execution.subprocess, "Popen") as launch:
                with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                    run.command([sys.executable, "-c", "pass"], **({"scope": "transfer"} | options))
                launch.assert_not_called()
        run.transition("Settling")
        run.release()

    def test_linux_memory_projection_requires_exact_bounded_kernel_rss_and_high_water_fields(self):
        self.assertTrue(callable(getattr(execution, "linux_process_memory", None)),
                        "Measured transfers need bounded independent kernel RSS observations.")
        observed = b"Name:\tsynthetic\nVmHWM:\t2048 kB\nVmRSS:\t1024 kB\n"
        self.assertEqual(execution.linux_process_memory(observed), (1048576, 2097152))
        for changed in (
                observed.replace(b"1024", b"0"), observed.replace(b"2048", b"1"),
                observed.replace(b"1024", b"-1"), observed.replace(b" kB", b" bytes"),
                observed + b"VmRSS:\t1024 kB\n", b"x" * 8193,
                observed.replace(b"1024", b"99999999999999999999"), b"VmRSS:\t1024 kB\n"):
            with self.subTest(changed=changed), self.assertRaisesRegex(ConformanceError, "ProofMismatch"):
                execution.linux_process_memory(changed)

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_owned_transfer_measures_kernel_peak_between_exact_start_and_settlement_handshakes(self):
        run = self.workspace()
        program = """
import json,sys
print(json.dumps({"event":"control","code":"None","value":0}),flush=True)
assert sys.stdin.readline()=="transfer\\n"
buffer=bytearray(4*1024**2)
print(json.dumps({"event":"test","code":"None","value":268435456}),flush=True)
assert sys.stdin.readline()=="settle\\n"
print(json.dumps({"event":"control","code":"None","value":1}),flush=True)
"""
        result = run.command([sys.executable, "-c", program], scope="transfer", measure_transfer_bytes=268435456)
        self.assertEqual(result.exit_code, 0)
        receipt = json.loads((run.root / "proofs/transfer-command-0001.json").read_bytes())
        self.assertEqual((receipt["exitCode"], receipt["diagnosticCode"], receipt["groupState"]), (0, "None", "Exited"))
        measured = receipt["transfer"]
        self.assertEqual(measured["bytes"], 268435456)
        self.assertEqual(measured["phase"], "complete")
        self.assertEqual(measured["osPeakMethod"], "proc-status")
        self.assertGreater(measured["baselineRssBytes"], 0)
        self.assertGreaterEqual(measured["samples"], 2)
        self.assertLessEqual(measured["baselineRssBytes"], measured["sampledPeakRssBytes"])
        self.assertLessEqual(measured["sampledPeakRssBytes"], measured["osPeakRssBytes"])
        self.assertLessEqual(measured["osPeakRssBytes"] - measured["baselineRssBytes"], 67108864)
        self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_transfer_peak_and_protocol_failures_cannot_become_measured_success(self):
        run = self.workspace()
        for program, expected in (
                ("pass", "EvidenceIncomplete"),
                ('print(\'{"event":"test","code":"None","value":268435456}\',flush=True)', "ProofMismatch"),
                ('print(\'{"event":"control","code":"None","value":1}\',flush=True)', "ProofMismatch"),
                ('import sys; print(\'{"event":"control","code":"None","value":0}\',flush=True); '
                 'sys.stdin.readline(); print(\'{"event":"test","code":"None","value":268435456}\',flush=True); '
                 'sys.stdin.readline()', "EvidenceIncomplete"),
                ('import sys,time; print(\'{"event":"control","code":"None","value":0}\',flush=True); '
                 'sys.stdin.readline(); buffer=bytearray(70*1024**2); '
                 'print(\'{"event":"test","code":"None","value":268435456}\',flush=True); time.sleep(60)',
                 "ProofMismatch")):
            with self.subTest(expected=expected), self.assertRaisesRegex(ConformanceError, expected):
                run.command([sys.executable, "-c", program], scope="transfer",
                            measure_transfer_bytes=268435456, timeout=5)
            self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    def test_linux_identity_distinguishes_kernel_start_ticks_and_ignores_process_names(self):
        def image(name, ticks):
            fields = [b"S", b"1", b"7", b"7"] + [b"0"] * 15 + [str(ticks).encode("ascii")]
            return b"42 (" + name + b") " + b" ".join(fields)
        original = execution.linux_process_identity(42, image(b"test) internal name", 100))
        renamed = execution.linux_process_identity(42, image(b"changed", 100))
        reused = execution.linux_process_identity(42, image(b"test) internal name", 101))
        self.assertEqual(original, renamed)
        self.assertNotEqual(original, reused)
        for malformed in (b"42 (bad) S", b"43 (different) S", b"x" * 4097):
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                execution.linux_process_identity(42, malformed)

    def test_ledger_tampering_and_symlink_swap_prevent_cleanup(self):
        run = self.workspace()
        run.transition("Active")
        run.transition("Settling")
        ledger = run.root / "ownership.json"
        original = ledger.read_bytes()
        value = json.loads(original)
        value["rootId"] = "foreign"
        ledger.write_text(json.dumps(value))
        with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
            run.release()
        with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
            run.transition("Settling")
        ledger.write_bytes(original)
        outside = self.parent / "outside"
        outside.mkdir()
        (outside / "sentinel").write_text("untouched")
        (run.root / "stores/link").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
            run.release()
        self.assertEqual((outside / "sentinel").read_text(), "untouched")
        (run.root / "stores/link").unlink()
        self.assertEqual(run.state, "Retained")
        run.transition("Settling")
        run.release()

    def test_replacing_a_top_level_directory_does_not_recreate_its_ownership(self):
        run = self.workspace()
        original = self.parent / "original-cache"
        (run.root / "cache").rename(original)
        (run.root / "cache").mkdir(mode=0o700)
        try:
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                run.command([sys.executable, "-c", "raise AssertionError('must not execute')"])
            self.assertEqual(list((run.root / "cache").iterdir()), [])
            self.assertFalse(run.live_children())
        finally:
            (run.root / "cache").rmdir()
            original.rename(run.root / "cache")
        run.transition("Settling")
        run.release()

    def test_unsupported_containment_fails_before_starting_a_provider(self):
        run = self.workspace()
        with mock.patch.object(execution, "native_execution_supported", return_value=False):
            with self.assertRaisesRegex(ConformanceError, "PrerequisiteMissing"):
                run.command([sys.executable, "-c", "raise AssertionError('must not execute')"])
        self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    def test_child_environment_is_explicit_and_cannot_inject_a_native_loader(self):
        run = self.workspace()
        with mock.patch.dict(os.environ, {"UNRELATED_SECRET": "synthetic-canary", "LD_PRELOAD": "/private/canary",
                                         "TMPDIR": "/private/canary"}):
            environment = execution.command_environment(run.root, run.root / "cache", {"HOARD_TEST": "synthetic"})
        self.assertNotIn("UNRELATED_SECRET", environment)
        self.assertNotIn("LD_PRELOAD", environment)
        self.assertEqual(environment["HOARD_TEST"], "synthetic")
        self.assertEqual(environment["TMPDIR"], str(run.root / "cache/tmp"))
        for supplied in ({"LD_PRELOAD": "/private/canary"}, {"HOARD_TEST": "x\x00"}, {"HOARD_TEST": "x" * 16385}):
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                execution.command_environment(run.root, run.root / "cache", supplied)
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "requires native Linux containment")
    def test_actual_child_temporary_files_stay_beneath_its_private_owned_cache(self):
        run = self.workspace()
        code = (
            "import json,os,tempfile\nfrom pathlib import Path\n"
            "expected=Path(os.environ['NUGET_PACKAGES'])/'tmp'\n"
            "assert expected.stat().st_mode & 0o777 == 0o700\n"
            "with tempfile.NamedTemporaryFile() as value:\n"
            " assert Path(value.name).parent == expected\n"
            "print(json.dumps({'event':'control','code':'None','value':1}))\n"
        )
        result = run.command([sys.executable, "-c", code], cache_id="temporary-probe", timeout=5)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual([dict(event) for event in result.events],
                         [{"event": "control", "code": "None", "value": 1}])
        self.assertTrue((run.root / "cache/temporary-probe/tmp").is_dir())
        self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_descendants_cannot_detach_into_an_unobserved_session_or_group(self):
        run = self.workspace()
        program = """
import subprocess, sys
try:
    child = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
except PermissionError:
    print('{"event":"control","code":"None","value":1}')
else:
    child.wait()
    print('{"event":"control","code":"None","value":0}')
subprocess.run([sys.executable, "-c", '''
import os
try:
    os.setpgid(0, 0)
except PermissionError:
    print('{"event":"control","code":"None","value":1}')
else:
    print('{"event":"control","code":"None","value":0}')
'''], check=True)
"""
        result = run.command([sys.executable, "-c", program])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual([event["value"] for event in result.events], [1, 1])
        self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_identity_failure_after_spawn_contains_the_provisional_child(self):
        run = self.workspace()
        original = execution.process_identity
        def failing_identity(pid, **kwargs):
            if pid != os.getpid():
                raise ConformanceError("OwnershipInvalid")
            return original(pid, **kwargs)
        with mock.patch.object(execution, "process_identity", side_effect=failing_identity):
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                run.command([sys.executable, "-c", "import time; time.sleep(60)"])
        self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_ledger_failure_after_spawn_contains_the_provisional_child(self):
        run = self.workspace()
        original = run._persist
        failed = False
        def failing_persist(**kwargs):
            nonlocal failed
            if run.groups and not failed:
                failed = True
                raise OSError("synthetic ledger failure")
            return original(**kwargs)
        with mock.patch.object(run, "_persist", side_effect=failing_persist):
            with self.assertRaisesRegex(ConformanceError, "CommandFailed"):
                run.command([sys.executable, "-c", "import time; time.sleep(60)"])
        self.assertTrue(failed)
        self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_unavailable_process_handle_prevents_target_execution(self):
        run = self.workspace()
        marker = run.root / "stores" / "target-started"
        program = (
            "from pathlib import Path; Path('target-started').write_text('unsafe'); "
            "print('{\"event\":\"control\",\"code\":\"None\",\"value\":1}')"
        )
        with mock.patch.object(execution.os, "pidfd_open",
                               side_effect=OSError(errno.EMFILE, "synthetic"), create=True):
            with self.assertRaisesRegex(ConformanceError, "PrerequisiteMissing"):
                run.command([sys.executable, "-c", program], cwd=marker.parent)
        self.assertFalse(marker.exists())
        self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_unavailable_kernel_group_signalling_prevents_target_execution(self):
        run = self.workspace()
        marker = run.root / "stores" / "target-started"
        program = (
            "from pathlib import Path; Path('target-started').write_text('unsafe'); "
            "print('{\"event\":\"control\",\"code\":\"None\",\"value\":1}')"
        )
        with mock.patch.object(execution.signal, "pidfd_send_signal",
                               side_effect=OSError(errno.EINVAL, "synthetic"), create=True):
            with self.assertRaisesRegex(ConformanceError, "PrerequisiteMissing"):
                run.command([sys.executable, "-c", program], cwd=marker.parent)
        self.assertFalse(marker.exists())
        self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

    def test_insufficient_artifact_capacity_and_invalid_budgets_fail_explicitly(self):
        with self.assertRaisesRegex(ConformanceError, "InsufficientCapacity"):
            execution.check_capacity("artifacts", free_bytes=24 * 1024**3 - 1)
        execution.check_capacity("artifacts", free_bytes=24 * 1024**3)
        with self.assertRaises(ConformanceError):
            execution.profile_budget("service")
        self.assertEqual(execution.profile_budget("metadata"), 90 * 60)
        self.assertEqual(execution.profile_budget("artifacts"), 180 * 60)
        self.assertEqual(execution.profile_budget("baseline"), 480 * 60)

    def test_profile_reserves_termination_and_cleanup_before_admitting_another_child(self):
        run = self.workspace()
        run.deadline = time.monotonic() + 30
        original = execution.subprocess.Popen
        def launch(args, *values, **kwargs):
            if args[0] == "ps":
                return original(args, *values, **kwargs)
            raise AssertionError("Child admitted without settlement budget")
        with mock.patch.object(execution, "native_execution_supported", return_value=True), \
                mock.patch.object(execution.subprocess, "Popen", side_effect=launch):
            with self.assertRaisesRegex(ConformanceError, "DeadlineExceeded"):
                run.command([sys.executable, "-c", "pass"], timeout=1)
        run.transition("Settling")
        run.release()

    def test_child_deadline_includes_admission_work_instead_of_restarting_after_it(self):
        run = self.workspace()
        now = [time.monotonic()]
        def delayed_admission(**kwargs):
            now[0] += 2
        with mock.patch.object(execution.time, "monotonic", side_effect=lambda: now[0]), \
                mock.patch.object(run, "_check_ledger", side_effect=delayed_admission), \
                mock.patch.object(execution, "native_execution_supported", return_value=True), \
                mock.patch.object(execution.subprocess, "Popen",
                                  side_effect=AssertionError("Child admitted after its deadline")):
            with self.assertRaisesRegex(ConformanceError, "DeadlineExceeded"):
                run.command([sys.executable, "-c", "pass"], timeout=1)
        run.transition("Settling")
        run.release()

    def test_remote_or_unknown_artifact_scratch_rejects_before_workspace_creation(self):
        for filesystem in (b"nfs\n", b"cifs\n", b"unknown\n"):
            with self.subTest(filesystem=filesystem), \
                    mock.patch.object(execution, "native_execution_supported", return_value=True), \
                    mock.patch.object(execution, "capture_control", return_value=(0, filesystem)), \
                    self.assertRaisesRegex(ConformanceError, "PrerequisiteMissing"):
                execution.OwnedRun.allocate(self.parent / "rejected", ROOT, profile="artifacts")
            self.assertFalse((self.parent / "rejected").exists())

    def test_preflight_parent_swap_cannot_create_a_workspace_under_an_outside_sentinel(self):
        disk_usage = execution.shutil.disk_usage
        mkdir = execution.os.mkdir
        for stage in ("preflight", "root-created"):
            with self.subTest(stage=stage):
                scope = self.parent / stage
                scope.mkdir(mode=0o700)
                private = scope / "private"
                outside = scope / "outside"
                private.mkdir(mode=0o700)
                outside.mkdir(mode=0o700)
                if stage == "root-created":
                    (outside / "run").mkdir(mode=0o700)
                (outside / "sentinel").write_bytes(b"preserve")
                def swap():
                    private.rename(scope / "moved")
                    private.symlink_to(outside, target_is_directory=True)
                def swapped_parent(parent):
                    capacity = disk_usage(parent)
                    if stage == "preflight":
                        swap()
                    return capacity
                def swapped_creation(path, *args, **kwargs):
                    result = mkdir(path, *args, **kwargs)
                    if stage == "root-created" and path == "run":
                        swap()
                    return result
                with mock.patch.object(execution.shutil, "disk_usage", side_effect=swapped_parent), \
                        mock.patch.object(execution.os, "mkdir", side_effect=swapped_creation), \
                        mock.patch.object(execution, "native_execution_supported", return_value=False), \
                        self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                    execution.OwnedRun.allocate(private / "run", ROOT, profile="artifacts")
                self.assertEqual({path.name for path in outside.iterdir()},
                                 {"sentinel", "run"} if stage == "root-created" else {"sentinel"})
                self.assertEqual((outside / "sentinel").read_bytes(), b"preserve")
                if stage == "root-created":
                    self.assertFalse(any((outside / "run").iterdir()))

    def test_state_publication_does_not_restart_expired_admission_controls(self):
        run = self.workspace()
        started = time.monotonic()
        now = [started]
        def inspect(*, deadline=None):
            now[0] += 5 if deadline is None else min(0.1, max(0, deadline - now[0]))
            if deadline is not None and now[0] >= deadline:
                raise ConformanceError("DeadlineExceeded")
        with mock.patch.object(execution.time, "monotonic", side_effect=lambda: now[0]), \
                mock.patch.object(run, "_check_ledger", side_effect=inspect), \
                mock.patch.object(execution, "native_execution_supported", return_value=True), \
                mock.patch.object(execution.subprocess, "Popen",
                                  side_effect=AssertionError("Expired admission spawned a child")):
            with self.assertRaisesRegex(ConformanceError, "DeadlineExceeded"):
                run.command([sys.executable, "-c", "pass"], scope="control", timeout=0.3)
        self.assertLessEqual(now[0] - started, 0.301)
        run.transition("Settling")
        run.release()

    def test_expired_cleanup_records_retention_without_deleting_synthetic_resources(self):
        run = self.workspace()
        sentinel = run.root / "stores" / "still-owned"
        sentinel.write_bytes(b"preserve")
        run.transition("Settling")
        original_deadline = run.deadline
        run.deadline = time.monotonic() - 1
        with self.assertRaisesRegex(ConformanceError, "CleanupIncomplete"):
            run.release()
        self.assertEqual(run.state, "Retained")
        self.assertEqual(run.cleanup_attempts[-1]["diagnosticCode"], "CleanupIncomplete")
        self.assertEqual(sentinel.read_bytes(), b"preserve")
        run.deadline = original_deadline
        run.transition("Settling")
        run.release()

    def test_local_scratch_observation_is_bounded_and_rejects_failed_or_malformed_controls(self):
        with mock.patch.object(execution, "native_execution_supported", return_value=True):
            with mock.patch.object(execution, "capture_control", return_value=(0, b"ext2/ext3\n")) as capture:
                self.assertEqual(execution.scratch_filesystem(self.parent, "artifacts"), "ext2-ext3")
                self.assertEqual(capture.call_args.kwargs, {"limit": 1024, "timeout": 5})
            for response in ((1, b"ext2/ext3\n"), (0, b"ext2/ext3\nnfs\n"), (0, b"\xff\n")):
                with self.subTest(response=response), \
                        mock.patch.object(execution, "capture_control", return_value=response), \
                        self.assertRaisesRegex(ConformanceError, "PrerequisiteMissing"):
                    execution.scratch_filesystem(self.parent, "artifacts")

    def test_control_barrier_and_caller_limits_cannot_expand_or_bypass_command_budgets(self):
        run = self.workspace()
        for scope, timeout in (("control", 6), ("barrier", 16), ("ordinary", 601),
                               ("transfer", 2401), ("recovery", 301)):
            with self.subTest(scope=scope), self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                run.command([sys.executable, "-c", "pass"], scope=scope, timeout=timeout)
        for deadline in (True, float("nan"), float("inf")):
            with self.subTest(deadline=deadline), self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                run.command([sys.executable, "-c", "pass"], deadline=deadline)
        with self.assertRaisesRegex(ConformanceError, "DeadlineExceeded"):
            run.command([sys.executable, "-c", "pass"], deadline=time.monotonic() - 1)
        run.transition("Settling")
        run.release()

    def test_one_owned_writer_rejects_overlapping_commands_and_cleanup_before_admission(self):
        run = self.workspace()
        entered = threading.Event()
        settle = threading.Event()
        def held_admission(**kwargs):
            if not entered.is_set():
                entered.set()
                if not settle.wait(5):
                    raise AssertionError("Admission barrier did not settle")
            raise ConformanceError("EvidenceIncomplete")
        with mock.patch.object(run, "_check_ledger", side_effect=held_admission):
            with ThreadPoolExecutor(max_workers=1) as executor:
                pending = executor.submit(run.command, [sys.executable, "-c", "pass"])
                try:
                    self.assertTrue(entered.wait(5))
                    with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                        run.command([sys.executable, "-c", "pass"])
                    with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                        run.release()
                finally:
                    settle.set()
                with self.assertRaisesRegex(ConformanceError, "EvidenceIncomplete"):
                    pending.result(timeout=5)
        run.transition("Settling")
        run.release()


if __name__ == "__main__":
    unittest.main()
from concurrent.futures import ThreadPoolExecutor
