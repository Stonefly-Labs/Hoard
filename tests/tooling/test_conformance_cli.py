import contextlib
from dataclasses import replace
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_evidence as evidence
from conformance_case_catalog import expected_cases


class ConformanceCliTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="hoard-cli-test-")).resolve()
        self.parent.chmod(0o700)
        self.addCleanup(shutil.rmtree, self.parent)
        self.destination = self.parent / "fresh"

    def test_full_and_focused_admission_freeze_independent_case_selection(self):
        full = evidence.admit_invocation(
            ROOT, ["--evidence", str(self.destination)])
        expected = tuple(case.key for profile in evidence.PROFILES for case in expected_cases(profile))
        self.assertEqual(full.case_keys, expected)
        self.assertEqual(full.mode, "qualification")
        focused = evidence.admit_invocation(ROOT, [
            "--profile", "metadata", "--filter", "MP-01", "--evidence", str(self.destination)])
        self.assertEqual(focused.mode, "diagnostic")
        self.assertEqual(focused.case_keys, tuple(case.key for case in expected_cases("metadata")
                                                 if case.case_id == "MP-01"))
        self.assertFalse(self.destination.exists())

    def test_invalid_modes_and_paths_never_allocate_or_fall_back_to_a_profile(self):
        report = self.parent / "report.json"
        report.write_text("{}")
        invalid = (
            ["--profile", "private-service-canary", "--evidence", str(self.destination)],
            ["--profile", "metadata", "--profile", "artifacts", "--evidence", str(self.destination)],
            ["--profile", "composition", "--binding-project", str(report), "--evidence", str(self.destination)],
            ["--verify", str(report), "--aggregate", str(self.parent)],
            ["--verify", str(report), "--evidence", str(self.destination)],
            ["--update-locks", "--filter", "QC-01", "--evidence", str(self.destination)],
            ["--filter", "unknown-case", "--evidence", str(self.destination)],
            ["--profile", "metadata", "--filter", "MP-0", "--evidence", str(self.destination)],
            ["--prof", "metadata", "--evidence", str(self.destination)],
        )
        for arguments in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(evidence.ConformanceError):
                evidence.admit_invocation(ROOT, arguments)
        existing = self.parent / "existing"
        existing.mkdir()
        with self.assertRaisesRegex(evidence.ConformanceError, "OwnershipInvalid"):
            evidence.admit_invocation(ROOT, ["--evidence", str(existing)])
        linked = self.parent / "linked"
        linked.symlink_to(existing, target_is_directory=True)
        with self.assertRaisesRegex(evidence.ConformanceError, "OwnershipInvalid"):
            evidence.admit_invocation(ROOT, ["--evidence", str(linked / "fresh")])
        self.assertFalse(self.destination.exists())

    def test_preparation_and_offline_modes_route_only_their_admitted_inputs(self):
        preparation = evidence.admit_invocation(ROOT, ["--update-locks", "--evidence", str(self.destination)])
        with patch("conformance_prepare.execute", return_value=0) as execute:
            self.assertEqual(evidence.dispatch_invocation(preparation), 0)
        execute.assert_called_once_with(ROOT, self.destination)
        report = self.parent / "report.json"
        report.write_text("{}")
        for arguments, action in ((["--verify", str(report)], "verify"),
                                  (["--aggregate", str(self.parent)], "aggregate")):
            invocation = evidence.admit_invocation(ROOT, arguments)
            self.assertEqual(invocation.action, action)
            self.assertIsNone(invocation.evidence)
            with self.assertRaisesRegex(evidence.ConformanceError, "EvidenceIncomplete"):
                evidence.dispatch_invocation(invocation)

    def test_explicit_category_project_cannot_change_the_selected_common_agreement(self):
        project = ROOT / "tests/fixtures/conformance/Contributor/Contributor.csproj"
        invocation = evidence.admit_invocation(ROOT, [
            "--profile", "metadata", "--binding-project", str(project),
            "--filter", "MP-01", "--evidence", str(self.destination)])
        self.assertEqual(invocation.binding_project, project)
        self.assertEqual(invocation.case_keys, tuple(case.key for case in expected_cases("metadata")
                                                    if case.case_id == "MP-01"))
        self.parent.chmod(0o755)
        try:
            with self.assertRaisesRegex(evidence.ConformanceError, "OwnershipInvalid"):
                evidence.admit_invocation(ROOT, ["--evidence", str(self.destination)])
        finally:
            self.parent.chmod(0o700)
        self.assertFalse(self.destination.exists())

    def test_builtin_category_dispatch_executes_only_its_complete_native_batch(self):
        for profile in ("metadata", "artifacts"):
            invocation = evidence.admit_invocation(ROOT, [
                "--profile", profile, "--evidence", str(self.destination)])
            with self.subTest(profile=profile), patch(
                    "conformance_sdk_checks.execute", return_value=0) as execute:
                with self.assertRaisesRegex(evidence.ConformanceError, "EvidenceIncomplete"):
                    evidence.dispatch_invocation(invocation)
                execute.assert_called_once_with(ROOT, self.destination, category=profile)
            self.assertFalse(self.destination.exists())

    def test_category_dispatch_never_substitutes_a_builtin_or_reduced_agreement(self):
        invocation = evidence.admit_invocation(ROOT, [
            "--profile", "metadata", "--evidence", str(self.destination)])
        unsupported = (
            replace(invocation, case_keys=invocation.case_keys[:-1]),
            replace(invocation, case_keys=(*invocation.case_keys, invocation.case_keys[0])),
            replace(invocation, mode="diagnostic"),
            replace(invocation, binding_project=ROOT / "tests/fixtures/conformance/Contributor/Contributor.csproj"),
            replace(invocation, profiles=("metadata", "artifacts")),
            replace(invocation, profiles=("composition",)),
        )
        with patch("conformance_sdk_checks.execute") as execute:
            for changed in unsupported:
                with self.subTest(mode=changed.mode, profiles=changed.profiles):
                    with self.assertRaises(evidence.ConformanceError):
                        evidence.dispatch_invocation(changed)
            execute.assert_not_called()
        self.assertFalse(self.destination.exists())

    def test_category_dispatch_preserves_native_failures_and_never_qualifies_a_successful_batch(self):
        invocation = evidence.admit_invocation(ROOT, [
            "--profile", "metadata", "--evidence", str(self.destination)])
        for code in ("AssertionFailed", "InsufficientCapacity", "CleanupIncomplete"):
            with self.subTest(code=code), patch(
                    "conformance_sdk_checks.execute", side_effect=evidence.ConformanceError(code)) as execute:
                with self.assertRaisesRegex(evidence.ConformanceError, code):
                    evidence.dispatch_invocation(invocation)
                execute.assert_called_once_with(ROOT, self.destination, category="metadata")
        for result in (1, 2, None, False):
            with self.subTest(result=result), patch("conformance_sdk_checks.execute", return_value=result):
                with self.assertRaisesRegex(evidence.ConformanceError, "CommandFailed"):
                    evidence.dispatch_invocation(invocation)

    def test_cli_rejects_private_unknown_input_without_persistence_or_false_success(self):
        import conformance_cli
        for arguments, code in (
                (["--private-canary-value"], "EvidenceSchemaInvalid"),
                (["--profile", "private-canary-service", "--evidence", str(self.destination)], "UnsupportedProfile"),
                (["--profile", "metadata", "--filter", "MP-01",
                  "--evidence", str(self.destination)], "EvidenceIncomplete")):
            output = io.StringIO()
            with self.subTest(arguments=arguments), contextlib.redirect_stdout(output):
                status = conformance_cli.main(arguments)
            value = json.loads(output.getvalue())
            self.assertEqual(status, 2)
            self.assertEqual(value["code"], code)
            self.assertFalse(value["qualification"])
            self.assertNotIn("private-canary", output.getvalue())
            self.assertFalse(self.destination.exists())
        for code, expected in (("AssertionFailed", 1), ("CleanupIncomplete", 2)):
            output = io.StringIO()
            with contextlib.redirect_stdout(output), patch.object(
                    evidence, "dispatch_invocation", side_effect=evidence.ConformanceError(code)):
                status = conformance_cli.main([
                    "--profile", "metadata", "--filter", "MP-01",
                    "--evidence", str(self.destination)])
            self.assertEqual(status, expected)
            value = json.loads(output.getvalue())
            self.assertEqual(value["mode"], "diagnostic")
            self.assertFalse(value["qualification"])

    def test_shell_entry_rejects_unknown_profiles_without_private_stderr(self):
        result = subprocess.run([
            "bash", str(ROOT / "scripts/validate-conformance.sh"),
            "--profile", "private-canary-service", "--evidence", str(self.destination)],
            cwd=self.parent, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "")
        value = json.loads(result.stdout)
        self.assertEqual(value["code"], "UnsupportedProfile")
        self.assertFalse(value["qualification"])
        self.assertNotIn("private-canary", result.stdout)
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
