import errno
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
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
        for destination in (sentinel, link, link / "child", ROOT / ".foundation/conformance-test"):
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
        with self.assertRaises(ConformanceError):
            execution.OwnedRun.allocate(run.root, ROOT)
        with self.assertRaises(ConformanceError):
            run.transition("Released")
        run.transition("Active")
        run.transition("Settling")
        run.release()
        self.assertFalse(run.root.exists())

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_bounded_safe_events_are_retained_without_raw_canary(self):
        run = self.workspace()
        result = run.command([sys.executable, "-c",
                              'print(\'{"event":"control","code":"None","value":3}\')'])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.events[0]["value"], 3)
        with self.assertRaisesRegex(ConformanceError, "UnknownDiagnostic"):
            run.command([sys.executable, "-c", 'print("synthetic-secret-canary/private/path")'])
        for path in (run.root / "diagnostics").rglob("*"):
            if path.is_file():
                self.assertNotIn(b"synthetic-secret-canary", path.read_bytes())
                self.assertNotIn(b"/private/path", path.read_bytes())
        self.assertFalse(any(path.suffix in (".trx", ".log") for path in run.root.rglob("*")))
        run.transition("Settling")
        run.release()

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
        run.transition("Settling")
        run.release()

    @unittest.skipUnless(NATIVE_CONTAINMENT, "Native process-group confinement requires Linux.")
    def test_watchdog_terminates_only_owned_process_tree_and_confirms_exit(self):
        run = self.workspace()
        code = ('import subprocess,sys,time; '
                'subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"]); time.sleep(60)')
        with self.assertRaisesRegex(ConformanceError, "DeadlineExceeded"):
            run.command([sys.executable, "-c", code], timeout=0.2)
        self.assertFalse(run.live_children())
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
        with mock.patch.dict(os.environ, {"UNRELATED_SECRET": "synthetic-canary", "LD_PRELOAD": "/private/canary"}):
            environment = execution.command_environment(run.root, run.root / "cache", {"HOARD_TEST": "synthetic"})
        self.assertNotIn("UNRELATED_SECRET", environment)
        self.assertNotIn("LD_PRELOAD", environment)
        self.assertEqual(environment["HOARD_TEST"], "synthetic")
        for supplied in ({"LD_PRELOAD": "/private/canary"}, {"HOARD_TEST": "x\x00"}, {"HOARD_TEST": "x" * 16385}):
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                execution.command_environment(run.root, run.root / "cache", supplied)
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
        def failing_persist(*, create=False):
            nonlocal failed
            if run.groups and not failed:
                failed = True
                raise OSError("synthetic ledger failure")
            return original(create=create)
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


if __name__ == "__main__":
    unittest.main()
