import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_cli
import conformance_evidence as evidence
import conformance_execution as execution


class ConformanceSanitationTests(unittest.TestCase):
    def setUp(self):
        token = uuid.uuid4().hex
        self.canaries = tuple((name + "-" + token).encode() for name in (
            "secret-canary", "payload-canary", "connection-canary", "exception-canary", "private-path-canary"))
        self.parent = Path(tempfile.mkdtemp(prefix=self.canaries[-1].decode() + "-")).resolve()
        self.parent.chmod(0o700)
        self.addCleanup(shutil.rmtree, self.parent)

    def assert_clean(self, root, *outputs):
        for output in outputs:
            for canary in self.canaries:
                self.assertNotIn(canary, output)
        for path in root.rglob("*"):
            for canary in self.canaries:
                self.assertNotIn(canary, os.fsencode(path.relative_to(root)))
            if path.is_file():
                contents = path.read_bytes()
                for canary in self.canaries:
                    self.assertNotIn(canary, contents)
        self.assertFalse(any(path.suffix in (".trx", ".log") for path in root.rglob("*")))

    def test_public_failure_projection_never_renders_provider_errors_or_private_paths(self):
        destination = self.parent / "evidence"
        message = b";".join((*self.canaries, os.fsencode(destination))).decode()
        for failure, code in ((OSError(message), "PrerequisiteMissing"),
                              (ValueError(message), "PrerequisiteMissing"),
                              (RuntimeError(message), "EvidenceIncomplete")):
            stdout, stderr = io.StringIO(), io.StringIO()
            with self.subTest(failure=type(failure).__name__), contextlib.redirect_stdout(stdout), (
                    contextlib.redirect_stderr(stderr)), mock.patch(
                    "conformance_sdk_checks.execute", side_effect=failure):
                status = conformance_cli.main([
                    "--profile", "compatibility", "--evidence", str(destination)])
            self.assertEqual(status, 2)
            self.assertEqual(stderr.getvalue(), "")
            observed = json.loads(stdout.getvalue())
            self.assertEqual(observed["code"], code)
            self.assertFalse(observed["qualification"])
            self.assertEqual(observed["status"], "Incomplete")
            self.assertFalse(destination.exists())
            self.assert_clean(self.parent, stdout.getvalue().encode(), stderr.getvalue().encode())

    @unittest.skipUnless(execution.native_execution_supported(), "All-output child inspection requires native Linux.")
    def test_unknown_provider_text_never_persists_in_any_owned_file_or_filename(self):
        run = execution.OwnedRun.allocate(self.parent / "evidence", ROOT, profile="harness")
        payload = b";".join((*self.canaries, os.fsencode(run.root))).decode()
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaisesRegex(evidence.ConformanceError, "^UnknownDiagnostic$"):
                run.command([sys.executable, "-c", "print(" + repr(payload) + ")"], record_execution=True)
            self.assertFalse(run.live_children())
            record = evidence.load_json(run.read_execution_record(1))
            self.assertEqual(record["diagnosticCode"], "UnknownDiagnostic")
            self.assertEqual(record["groupState"], "Exited")
            self.assert_clean(run.root, stdout.getvalue().encode(), stderr.getvalue().encode())
            run.transition("Settling")
            run.release()
        self.assertEqual(run.state, "Released")
        self.assert_clean(run.root, stdout.getvalue().encode(), stderr.getvalue().encode(),
                          evidence.canonical_bytes(run.resource_projection()))

    @unittest.skipUnless(execution.native_execution_supported(), "All-output flood inspection requires native Linux.")
    def test_output_flood_is_incomplete_without_spooling_or_truncating_into_success(self):
        run = execution.OwnedRun.allocate(self.parent / "evidence", ROOT, profile="harness")
        payload = b";".join(self.canaries).decode()
        repeats = execution.CHILD_DIAGNOSTIC_BYTES // len(payload) + 1
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            run.command([sys.executable, "-c", "print(" + repr(payload) + "*" + str(repeats) + ",flush=True)"],
                        record_execution=True)
        self.assertFalse(run.live_children())
        record = evidence.load_json(run.read_execution_record(1))
        self.assertEqual(record["diagnosticCode"], "OutputLimitExceeded")
        self.assertEqual(record["groupState"], "Exited")
        self.assert_clean(run.root)
        run.transition("Settling")
        run.release()
        self.assertEqual(run.state, "Released")
        self.assert_clean(run.root, evidence.canonical_bytes(run.resource_projection()))


if __name__ == "__main__":
    unittest.main()
