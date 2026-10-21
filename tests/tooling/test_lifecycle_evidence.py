import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import lifecycle_evidence as lifecycle


class LifecycleEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def test_missing_and_empty_proof_fail(self):
        with self.assertRaisesRegex(RuntimeError, "Missing"):
            lifecycle.require_file(self.root / "absent")
        for content in ('<TestRun/>', '<TestRun><Counters total="0" passed="0"/></TestRun>',
                        '<TestRun><Counters total="2" passed="1" failed="0" notExecuted="1"/></TestRun>'):
            result = self.root / "result.trx"
            result.write_text(content)
            with self.assertRaises(RuntimeError):
                lifecycle.test_count(result)
        with self.assertRaisesRegex(RuntimeError, "journey"):
            lifecycle.journey_count('{"journeys":[]}')
        for entry in ({"passed": False, "events": 2}, {"passed": True, "events": 0}):
            with self.assertRaisesRegex(RuntimeError, "journey"):
                lifecycle.journey_count(json.dumps({"journeys": [entry]}))
        with self.assertRaisesRegex(RuntimeError, "Empty"):
            lifecycle.focused_tests(self.root, self.root, " ")

    def test_subprocess_error_and_timeout_are_explicit_without_payloads(self):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "secret")):
            with self.assertRaisesRegex(RuntimeError, "^Lifecycle command failed: probe$"):
                lifecycle.run("probe")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("probe", 1, output="secret")):
            with self.assertRaisesRegex(RuntimeError, "^Lifecycle command timed out: probe$"):
                lifecycle.run("probe")

    def test_provenance_rejects_missing_stale_or_external_package(self):
        package = self.root / "Hoard.Test.nupkg"
        package.write_bytes(b"fresh")
        digest = hashlib.sha512(package.read_bytes()).hexdigest()
        lifecycle.verify_package(package, self.root, digest)
        for directory, expected in ((self.root / "other", digest), (self.root, "stale")):
            with self.assertRaisesRegex(RuntimeError, "provenance"):
                lifecycle.verify_package(package, directory, expected)

    def test_default_execution_cannot_rewrite_locks(self):
        lock = self.root / "packages.lock.json"
        lock.write_text("{}")
        before = lifecycle.lock_hashes(self.root)
        lock.write_text('{"changed":true}')
        with self.assertRaisesRegex(RuntimeError, "lock"):
            lifecycle.verify_locks(self.root, before)

    def test_cleanup_requires_owned_resolved_temporary_directory(self):
        owned = lifecycle.create_workspace(self.root)
        unrelated = self.root / "unrelated"
        unrelated.mkdir()
        for path in (self.root, unrelated, owned / ".."):
            with self.assertRaisesRegex(RuntimeError, "workspace"):
                lifecycle.cleanup_workspace(path)
        lifecycle.cleanup_workspace(owned)
        self.assertFalse(owned.exists())
        self.assertTrue(unrelated.exists())
