import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_execution as execution
from conformance_evidence import ConformanceError


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

    def test_output_flood_is_failure_not_truncated_success_and_child_exits(self):
        run = self.workspace()
        with self.assertRaisesRegex(ConformanceError, "OutputLimitExceeded"):
            run.command([sys.executable, "-c", 'import os; os.write(1,b"x"*131072)'], timeout=5)
        self.assertFalse(run.live_children())
        run.transition("Settling")
        run.release()

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
