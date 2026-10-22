import copy
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("metadata_evidence", SCRIPTS / "metadata_evidence.py")


class MetadataEvidenceTests(unittest.TestCase):
    def load(self):
        module = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(module)
        return module

    def cases(self, module, work):
        proof = work / "proof.json"
        proof.write_text('{"synthetic":"tooling-only"}')
        digest = hashlib.sha256(proof.read_bytes()).hexdigest()
        return [
            {"id": case, "provider": provider, "class": "D" if case in module.DURABLE_CASES else "L",
             "result": "NotApplicable" if provider == "memory" and case in module.DURABLE_CASES else "Passed",
             "reason": "non-durable fixture" if provider == "memory" and case in module.DURABLE_CASES else "",
             "runId": "current", "durationMs": 1, "tests": ["actual-test"],
             "positive": True, "negative": True,
             "proof": "proof.json", "sha256": digest}
            for provider in module.PROVIDERS for case in module.CASES
        ]

    def test_case_inventory_requires_every_applicable_case_exactly_once(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            cases = self.cases(module, work)
            module.verify_cases(cases, work, "current")
            for changed in (None, [], cases[:-1], cases + [cases[0]]):
                with self.subTest(changed=str(changed)[:30]), self.assertRaisesRegex(RuntimeError, "case"):
                    module.verify_cases(changed, work, "current")

    def test_stale_failed_unpaired_foreign_and_false_memory_durability_reject(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            original = self.cases(module, work)
            for field, value in (
                ("runId", "stale"), ("provider", "another-engine"), ("class", "D"),
                ("result", "Failed"), ("positive", False), ("negative", False),
                ("durationMs", -1), ("durationMs", True), ("tests", []), ("sha256", "a" * 64),
            ):
                changed = copy.deepcopy(original)
                changed[0][field] = value
                with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, "case"):
                    module.verify_cases(changed, work, "current")
            changed = copy.deepcopy(original)
            next(case for case in changed if case["provider"] == "memory" and case["class"] == "D")["result"] = "Passed"
            with self.assertRaisesRegex(RuntimeError, "durability"):
                module.verify_cases(changed, work, "current")

    def test_proof_cannot_escape_workspace_or_use_symlinks(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            work = parent / "work"
            work.mkdir()
            outside = parent / "outside"
            outside.write_bytes(b"private")
            (work / "link").symlink_to(outside)
            for path in ("../outside", str(outside), "link", "missing"):
                with self.subTest(path=path), self.assertRaisesRegex(RuntimeError, "proof"):
                    module.proof_file(work, path)

    def test_crash_proof_requires_named_barrier_confirmed_signal_exit_and_state(self):
        module = self.load()
        proof = {"barrier": "M0", "pid": 321, "exitCode": -9, "exitConfirmed": True,
                 "stateCompared": True, "receiptCompared": True, "baselineCompared": True}
        module.verify_crash(proof, "M0")
        for field, value in (("barrier", "M1"), ("pid", 0), ("exitCode", 0),
                             ("exitConfirmed", False), ("stateCompared", False),
                             ("receiptCompared", False), ("baselineCompared", False)):
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, "crash"):
                module.verify_crash({**proof, field: value}, "M0")

    def test_all_eight_distinct_crash_barriers_are_required(self):
        module = self.load()
        for evidence in (None, [], [{"barrier": "M0"}] * 8):
            with self.assertRaisesRegex(RuntimeError, "crash"):
                module.verify_crashes(evidence)

    def test_package_inventory_rejects_missing_duplicate_and_hash_drift(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            packages = []
            for name in module.PACKAGES:
                path = work / name
                path.write_bytes(name.encode())
                packages.append({"id": name, "proof": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            module.verify_packages(packages, work)
            for changed in (packages[:-1], packages + [packages[0]],
                            [{**entry, "sha256": "f" * 64} for entry in packages]):
                with self.assertRaisesRegex(RuntimeError, "package"):
                    module.verify_packages(changed, work)

    def test_runtime_red_requires_assertion_failure_then_same_passing_test(self):
        module = self.load()
        proof = {"id": "stale-revision", "test": "actual-test", "redExit": 1,
                 "redOutcome": "Failed", "redAssertion": True, "greenOutcome": "Passed",
                 "mutationSha256": "a" * 64, "baselineSha256": "b" * 64}
        module.verify_red_green([proof])
        for field, value in (("redExit", 0), ("redAssertion", False), ("redOutcome", "CompileFailed"),
                             ("greenOutcome", "Skipped"), ("mutationSha256", "b" * 64)):
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, "red/green"):
                module.verify_red_green([{**proof, field: value}])
        with self.assertRaisesRegex(RuntimeError, "red/green"):
            module.verify_red_green([])

    def test_subprocess_failure_and_timeout_are_sanitized_and_explicit(self):
        module = self.load()
        for result in (subprocess.CompletedProcess([], 7, "private-canary"),
                       subprocess.TimeoutExpired("fixture", 600)):
            with self.subTest(result=type(result).__name__):
                with patch.object(module.subprocess, "run",
                                  side_effect=result if isinstance(result, Exception) else None,
                                  return_value=result):
                    with self.assertRaisesRegex(RuntimeError, "command") as caught:
                        module.run("fixture")
                    self.assertNotIn("private-canary", str(caught.exception))

    def test_cleanup_rejects_unowned_broad_or_symlinked_targets(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            with self.assertRaisesRegex(RuntimeError, "cleanup"):
                module.cleanup_workspace(parent)
            work = module.create_workspace(parent=parent)
            module.cleanup_workspace(work)
            self.assertTrue(parent.is_dir())
            self.assertFalse(work.exists())

    def test_lock_replay_rejects_added_removed_and_changed_locks(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "packages.lock.json"
            lock.write_text("{}")
            expected = module.lock_hashes(root)
            module.verify_locks(root, expected)
            lock.write_text('{"drift":true}')
            with self.assertRaisesRegex(RuntimeError, "lock"):
                module.verify_locks(root, expected)
            lock.unlink()
            with self.assertRaisesRegex(RuntimeError, "lock"):
                module.verify_locks(root, expected)
            lock.write_text("{}")
            (root / "extra").mkdir()
            (root / "extra/packages.lock.json").write_text("{}")
            with self.assertRaisesRegex(RuntimeError, "lock"):
                module.verify_locks(root, expected)

    def test_focused_phases_reject_missing_stale_and_incomplete_prerequisites(self):
        module = self.load()
        for phase in ("logical", "recovery", "packages"):
            for evidence in (None, {}, {"sourceSha256": "stale", "prepared": True}):
                with self.subTest(phase=phase), self.assertRaisesRegex(RuntimeError, "prerequisite"):
                    module.verify_prerequisites(evidence, phase, "a" * 64)

    def test_empty_manifest_cannot_qualify(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            for value in (None, {}, {"production": True}, {"durable": True, "provider": "memory"}):
                with self.assertRaisesRegex(RuntimeError, "qualification"):
                    module.verify_manifest(value, Path(directory), "a" * 64)
