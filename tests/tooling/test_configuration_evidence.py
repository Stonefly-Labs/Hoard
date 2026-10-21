import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import configuration_evidence as configuration


class ConfigurationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def test_exact_case_inventory_rejects_missing_empty_duplicate_and_partial(self):
        cases = [{"id": f"CFG-{number:02}", "tests": ["actual-proof"], "passed": True}
                 for number in range(1, 37)]
        configuration.verify_cases(cases)
        for invalid in ([], cases[:-1], cases + [cases[0]],
                        [{**entry, "tests": []} for entry in cases],
                        [{**entry, "passed": False} for entry in cases],
                        ["untrusted-record"] * 36, [{**entry, "id": None} for entry in cases],
                        [{**entry, "tests": "not-a-test-list"} for entry in cases]):
            with self.assertRaisesRegex(RuntimeError, "configuration case"):
                configuration.verify_cases(invalid)

    def test_subprocess_errors_are_closed_and_bounded(self):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "private-payload")):
            with self.assertRaisesRegex(RuntimeError, "^Configuration command failed: probe$"):
                configuration.run("probe")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("probe", 1, output="private-payload")):
            with self.assertRaisesRegex(RuntimeError, "^Configuration command timed out: probe$"):
                configuration.run("probe")

    def test_local_package_and_retained_binary_provenance(self):
        package = self.root / "Hoard.Fixture.nupkg"
        package.write_bytes(b"original")
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        configuration.verify_binary(package, digest)
        configuration.verify_package(package, self.root, hashlib.sha512(package.read_bytes()).hexdigest())
        for directory in (self.root / "elsewhere", self.root / ".."):
            with self.assertRaisesRegex(RuntimeError, "provenance"):
                configuration.verify_package(package, directory, "stale")
        package.write_bytes(b"changed")
        with self.assertRaisesRegex(RuntimeError, "binary"):
            configuration.verify_binary(package, digest)
        with self.assertRaisesRegex(RuntimeError, "binary"):
            configuration.verify_binary(self.root / "absent", digest)

    def test_platform_acceptance_is_required_and_not_inferred(self):
        for evidence in (None, {}, {"os": "Darwin", "filesystem": "local", "barriers": []},
                         {"os": "Darwin", "filesystem": "local", "barriers": ["staged"]}):
            with self.assertRaisesRegex(RuntimeError, "publication proof"):
                configuration.verify_publication(evidence)
        configuration.verify_publication({
            "os": "Darwin", "filesystem": "local",
            "barriers": list(configuration.PUBLICATION_BARRIERS), "passed": True})

    def test_malformed_test_counters_do_not_reflect_result_payloads(self):
        result = self.root / "result.trx"
        for text in ('<TestRun><Counters total="private-payload" passed="1"/></TestRun>', "private-payload"):
            result.write_text(text)
            with self.assertRaisesRegex(RuntimeError, "^Invalid configuration test result counters.$"):
                configuration.test_count(result)

    def test_default_locks_are_immutable(self):
        lock = self.root / "packages.lock.json"
        lock.write_text("{}")
        before = configuration.lock_hashes(self.root)
        configuration.verify_locks(self.root, before)
        lock.write_text(json.dumps({"changed": True}))
        with self.assertRaisesRegex(RuntimeError, "lock"):
            configuration.verify_locks(self.root, before)

    def test_cleanup_only_accepts_its_own_resolved_workspace(self):
        owned = configuration.create_workspace(self.root)
        sibling = self.root / "unrelated"
        sibling.mkdir()
        for path in (self.root, sibling, owned / ".."):
            with self.assertRaisesRegex(RuntimeError, "workspace"):
                configuration.cleanup_workspace(path)
        configuration.cleanup_workspace(owned)
        self.assertFalse(owned.exists())
        self.assertTrue(sibling.exists())

    def test_full_acceptance_refuses_incomplete_implementation(self):
        with self.assertRaisesRegex(RuntimeError, "Incomplete configuration acceptance"):
            configuration.complete_acceptance(self.root, self.root, False)

    def test_retained_baseline_is_copied_once_without_overwriting_existing_inputs(self):
        source = self.root / "source"
        source.mkdir()
        binary = source / "LifecycleConsumer.dll"
        binary.write_bytes(b"unchanged-retained-binary")
        assets = source / "project.assets.json"
        assets.write_text("{}")
        entry = {"name": "LifecycleConsumer", "assembly": str(binary), "assets": str(assets),
                 "baseline": configuration.BASELINE, "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
        output = self.root / "retained"
        retained = configuration.retain_baseline([entry], output)
        configuration.verify_binary(Path(retained[0]["assembly"]), entry["sha256"])
        with self.assertRaisesRegex(RuntimeError, "fresh explicit"):
            configuration.retain_baseline([entry], output)

    def test_red_and_green_capture_preserves_real_result_without_claiming_full_acceptance(self):
        work = self.root / "work"
        (work / "results").mkdir(parents=True)
        (work / "results/configuration.trx").write_text("<actual-test-result/>")
        for passed in (False, True):
            output = self.root / ("green" if passed else "red")
            configuration.retain_evidence(work, output, "source-tests", passed)
            report = json.loads((output / "result.json").read_text())
            self.assertEqual("passed" if passed else "failed", report["status"])
            self.assertFalse(report["fullAcceptance"])
            self.assertEqual("<actual-test-result/>", (output / "configuration.trx").read_text())
            with self.assertRaisesRegex(RuntimeError, "fresh explicit"):
                configuration.retain_evidence(work, output, "source-tests", passed)
