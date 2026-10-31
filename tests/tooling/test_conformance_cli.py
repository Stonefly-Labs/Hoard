import contextlib
from dataclasses import replace
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
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
            ["--coordinator", str(report), "--profile", "metadata", "--evidence", str(self.destination)],
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

    def offline_fixture(self):
        from test_conformance_evidence import ConformanceRuntimeIngestionTests

        model = ConformanceRuntimeIngestionTests()
        model.setUp()
        self.addCleanup(model.doCleanups)
        sources = {
            "packageSources": {
                "local": "isolated-current-archives", "nuget.org": "https://api.nuget.org/v3/index.json"},
            "packageSourceMapping": {"local": ["Hoard.*"], "nuget.org": ["*"]}}
        configuration = {**evidence.configuration_policy(), "sources": sources}
        model.inputs["configurationSha256"] = evidence.digest(configuration)
        root = self.parent / "original"
        root.mkdir()
        report = model.generated_category_report(root, "metadata")
        path = root / "proofs/category-metadata-qualification-report.json"
        context = self.parent / "coordinator.json"
        context.write_bytes(evidence.canonical_bytes({"schemaVersion": 1, "profiles": {"metadata": {
            "inputs": report["inputs"], "reportSha256": evidence.digest(report),
            "reportPath": path.relative_to(root).as_posix(), "configuration": configuration,
            "jobResults": {"job": "success", "upload": "success", "download": "success"}}}}))
        return root, path, context

    def test_explicit_coordinator_verifies_original_generated_packet_without_qualifying_model_origin(self):
        import conformance_cli

        root, report, coordinator = self.offline_fixture()
        before = evidence.proof_manifest(root)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = conformance_cli.main(["--verify", str(report), "--coordinator", str(coordinator)])
        self.assertEqual(code, 2)
        packet, = (json.loads(row) for row in output.getvalue().splitlines())
        self.assertFalse(packet["qualification"])
        self.assertEqual(packet["scope"], "profile-report-structure-diagnostic")
        self.assertEqual(packet["code"], "EvidenceIncomplete")
        self.assertEqual(packet["profileId"], "metadata")
        self.assertGreater(packet["caseCount"], 96)
        self.assertNotIn(str(self.parent), output.getvalue())
        self.assertEqual(evidence.proof_manifest(root), before)
        child = subprocess.run([
            "bash", str(ROOT / "scripts/validate-conformance.sh"),
            "--verify", str(report), "--coordinator", str(coordinator)],
            cwd=self.parent, capture_output=True, timeout=15, check=False)
        self.assertEqual(child.returncode, 2)
        self.assertEqual(child.stderr, b"")
        self.assertEqual(json.loads(child.stdout), packet)

    def test_offline_verification_rejects_report_self_pins_changed_proofs_and_unknown_context(self):
        import conformance_cli

        for defect in ("self-context", "context-field", "changed-report", "changed-proof", "context-link"):
            with self.subTest(defect=defect):
                root, report, coordinator = self.offline_fixture()
                if defect == "self-context":
                    target = root / "coordinator.json"
                    coordinator.rename(target)
                    coordinator = target
                elif defect == "context-field":
                    value = json.loads(coordinator.read_bytes())
                    value["providerError"] = "private-canary"
                    coordinator.write_bytes(evidence.canonical_bytes(value))
                elif defect == "changed-report":
                    report.chmod(0o600)
                    report.write_bytes(report.read_bytes() + b"\n")
                elif defect == "changed-proof":
                    value = json.loads(report.read_bytes())
                    proof = root / next(iter(value["proofs"]))
                    proof.chmod(0o600)
                    proof.write_bytes(b"private-canary")
                else:
                    linked = self.parent / "linked-coordinator.json"
                    linked.symlink_to(coordinator)
                    coordinator = linked
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = conformance_cli.main(["--verify", str(report), "--coordinator", str(coordinator)])
                self.assertIn(code, (1, 2))
                packet, = (json.loads(row) for row in output.getvalue().splitlines())
                self.assertNotIn("scope", packet)
                self.assertFalse(packet["qualification"])
                self.assertNotIn("private-canary", output.getvalue())
                self.assertNotIn(str(self.parent), output.getvalue())
                shutil.rmtree(root)
                if coordinator.is_symlink():
                    coordinator.unlink()

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
                execute.assert_called_once_with(ROOT, self.destination, category=profile, qualify=True)
            self.assertFalse(self.destination.exists())

    def test_composition_dispatch_runs_complete_native_observations_without_qualification(self):
        invocation = evidence.admit_invocation(ROOT, [
            "--profile", "composition", "--evidence", str(self.destination)])
        with patch("conformance_composition_checks.execute", return_value=0) as execute:
            with self.assertRaisesRegex(evidence.ConformanceError, "EvidenceIncomplete"):
                evidence.dispatch_invocation(invocation)
            execute.assert_called_once_with(ROOT, self.destination, qualify=True)
        self.assertFalse(self.destination.exists())

    def test_complete_composition_dispatch_requires_original_qualification_completion(self):
        invocation = evidence.admit_invocation(ROOT, [
            "--profile", "composition", "--evidence", str(self.destination)])
        token = object()
        with patch("conformance_composition_checks.execute", return_value=token) as execute, patch.object(
                evidence, "complete_native_composition_invocation", return_value=0) as complete:
            self.assertEqual(evidence.dispatch_invocation(invocation), 0)
            execute.assert_called_once_with(ROOT, self.destination, qualify=True)
            complete.assert_called_once_with(invocation, token)

    def test_complete_compatibility_dispatch_requires_original_qualification_completion(self):
        invocation = evidence.admit_invocation(ROOT, [
            "--profile", "compatibility", "--evidence", str(self.destination)])
        token = object()
        with patch("conformance_sdk_checks.execute", return_value=token) as execute, patch.object(
                evidence, "complete_native_compatibility_invocation", return_value=0) as complete:
            self.assertEqual(evidence.dispatch_invocation(invocation), 0)
            execute.assert_called_once_with(ROOT, self.destination, compatibility_only=True, qualify=True)
            complete.assert_called_once_with(invocation, token)
        for forged in (0, 1, None, token):
            with self.subTest(forged=forged), self.assertRaises(evidence.ConformanceError):
                evidence.complete_native_compatibility_invocation(invocation, forged)

    def test_harness_dispatch_requires_complete_controls_and_original_native_completion(self):
        invocation = evidence.admit_invocation(ROOT, [
            "--profile", "harness", "--evidence", str(self.destination)])
        token = object()
        with patch("conformance_harness.execute", return_value=token) as execute, patch.object(
                evidence, "complete_native_harness_invocation", return_value=0) as complete:
            self.assertEqual(evidence.dispatch_invocation(invocation), 0)
            execute.assert_called_once_with(ROOT, self.destination)
            complete.assert_called_once_with(invocation, token)
        for forged in (0, 1, None, False, token):
            with self.subTest(forged=forged), self.assertRaises(evidence.ConformanceError):
                evidence.complete_native_harness_invocation(invocation, forged)
        for changed in (
                replace(invocation, case_keys=invocation.case_keys[:-1]),
                replace(invocation, case_keys=(*invocation.case_keys, invocation.case_keys[0])),
                replace(invocation, mode="diagnostic"),
                replace(invocation, profiles=("harness", "composition"))):
            with self.subTest(invocation=changed), patch("conformance_harness.execute") as execute:
                with self.assertRaises(evidence.ConformanceError):
                    evidence.dispatch_invocation(changed)
                execute.assert_not_called()
        with patch("conformance_harness.execute", return_value=0):
            with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
                evidence.dispatch_invocation(invocation)

    def test_compatibility_dispatch_requires_the_complete_agreement_and_never_qualifies_diagnostics(self):
        invocation = evidence.admit_invocation(ROOT, [
            "--profile", "compatibility", "--evidence", str(self.destination)])
        with patch("conformance_sdk_checks.execute", return_value=0) as execute:
            with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
                evidence.dispatch_invocation(invocation)
            execute.assert_called_once_with(ROOT, self.destination, compatibility_only=True, qualify=True)
        unsupported = (
            replace(invocation, case_keys=invocation.case_keys[:-1]),
            replace(invocation, case_keys=(*invocation.case_keys, invocation.case_keys[0])),
            replace(invocation, mode="diagnostic"),
            replace(invocation, profiles=("compatibility", "composition")),
            replace(invocation, binding_project=ROOT / "tests/fixtures/conformance/Contributor/Contributor.csproj"))
        with patch("conformance_sdk_checks.execute") as execute:
            for changed in unsupported:
                with self.subTest(invocation=changed), self.assertRaises(evidence.ConformanceError):
                    evidence.dispatch_invocation(changed)
            execute.assert_not_called()
        for error, code in (
                (evidence.ConformanceError("CleanupIncomplete"), "CleanupIncomplete"),
                (RuntimeError("private-canary"), "EvidenceIncomplete")):
            with patch("conformance_sdk_checks.execute", side_effect=error):
                with self.assertRaisesRegex(evidence.ConformanceError, "^" + code + "$"):
                    evidence.dispatch_invocation(invocation)
        for result in (1, 2, None, False):
            with patch("conformance_sdk_checks.execute", return_value=result):
                with self.assertRaisesRegex(evidence.ConformanceError, "^CommandFailed$"):
                    evidence.dispatch_invocation(invocation)

    def test_composition_dispatch_rejects_reduced_focused_and_mixed_agreements_before_execution(self):
        invocation = evidence.admit_invocation(ROOT, [
            "--profile", "composition", "--evidence", str(self.destination)])
        unsupported = (
            replace(invocation, case_keys=invocation.case_keys[:-1]),
            replace(invocation, case_keys=(*invocation.case_keys, invocation.case_keys[0])),
            replace(invocation, mode="diagnostic"),
            replace(invocation, profiles=("composition", "metadata")),
            replace(invocation, binding_project=ROOT / "tests/fixtures/conformance/Contributor/Contributor.csproj"),
        )
        with patch("conformance_composition_checks.execute") as execute:
            for changed in unsupported:
                with self.subTest(invocation=changed), self.assertRaises(evidence.ConformanceError):
                    evidence.dispatch_invocation(changed)
            execute.assert_not_called()

    def test_composition_dispatch_preserves_failures_and_sanitizes_borrowed_controller_errors(self):
        invocation = evidence.admit_invocation(ROOT, [
            "--profile", "composition", "--evidence", str(self.destination)])
        for error, code in (
                (evidence.ConformanceError("WitnessMissing"), "WitnessMissing"),
                (evidence.ConformanceError("CleanupIncomplete"), "CleanupIncomplete"),
                (RuntimeError("private-canary"), "EvidenceIncomplete")):
            with self.subTest(code=code), patch("conformance_composition_checks.execute", side_effect=error):
                with self.assertRaisesRegex(evidence.ConformanceError, "^" + code + "$"):
                    evidence.dispatch_invocation(invocation)
        for result in (1, 2, None, False):
            with self.subTest(result=result), patch("conformance_composition_checks.execute", return_value=result):
                with self.assertRaisesRegex(evidence.ConformanceError, "CommandFailed"):
                    evidence.dispatch_invocation(invocation)

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
                execute.assert_called_once_with(ROOT, self.destination, category="metadata", qualify=True)
        for result in (1, 2, None, False, {"qualification": True}, SimpleNamespace(qualification=True)):
            with self.subTest(result=result), patch("conformance_sdk_checks.execute", return_value=result):
                with self.assertRaisesRegex(evidence.ConformanceError, "CommandFailed"):
                    evidence.dispatch_invocation(invocation)
        from conformance_sources import NativeCategoryEvaluation

        modeled = NativeCategoryEvaluation(object(), "a" * 64, "b" * 64, {})
        with patch("conformance_sdk_checks.execute", return_value=modeled):
            with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                evidence.dispatch_invocation(invocation)

    def test_explicit_metadata_dispatch_runs_only_the_admitted_contributor_and_never_qualifies(self):
        project = ROOT / "tests/fixtures/conformance/Contributor/Contributor.csproj"
        invocation = evidence.admit_invocation(ROOT, [
            "--profile", "metadata", "--binding-project", str(project), "--evidence", str(self.destination)])
        with patch("conformance_contributors.execute", return_value=0) as execute, patch(
                "conformance_sdk_checks.execute") as builtin:
            with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
                evidence.dispatch_invocation(invocation)
            execute.assert_called_once_with(
                ROOT, self.destination, project=project, category="metadata",
                binding_inputs_sha256=invocation.binding_inputs_sha256)
            builtin.assert_not_called()
        for changed in (
                replace(invocation, case_keys=invocation.case_keys[:-1]),
                replace(invocation, case_keys=(*invocation.case_keys, invocation.case_keys[0])),
                replace(invocation, mode="diagnostic"), replace(invocation, profiles=("artifacts",))):
            with self.subTest(profiles=changed.profiles, mode=changed.mode), patch(
                    "conformance_contributors.execute") as execute, self.assertRaises(evidence.ConformanceError):
                evidence.dispatch_invocation(changed)
            execute.assert_not_called()
        for code in ("AssertionFailed", "InputChanged", "CleanupIncomplete"):
            with self.subTest(code=code), patch(
                    "conformance_contributors.execute", side_effect=evidence.ConformanceError(code)), (
                    self.assertRaisesRegex(evidence.ConformanceError, "^" + code + "$")):
                evidence.dispatch_invocation(invocation)
        for result in (1, 2, None, False):
            with self.subTest(result=result), patch(
                    "conformance_contributors.execute", return_value=result), self.assertRaisesRegex(
                    evidence.ConformanceError, "^CommandFailed$"):
                evidence.dispatch_invocation(invocation)
        self.assertFalse(self.destination.exists())

    def test_explicit_artifact_dispatch_uses_only_the_complete_contributor_agreement(self):
        project = ROOT / "tests/fixtures/conformance/Contributor/Contributor.csproj"
        admitted = evidence.admit_invocation(ROOT, [
            "--profile", "metadata", "--binding-project", str(project), "--evidence", str(self.destination)])
        invocation = replace(admitted, profiles=("artifacts",),
                             case_keys=tuple(case.key for case in expected_cases("artifacts")))
        with patch("conformance_contributors.execute", return_value=0) as execute, patch(
                "conformance_sdk_checks.execute") as builtin:
            with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
                evidence.dispatch_invocation(invocation)
            execute.assert_called_once_with(
                ROOT, self.destination, project=project, category="artifacts",
                binding_inputs_sha256=invocation.binding_inputs_sha256)
            builtin.assert_not_called()
        for changed in (
                replace(invocation, case_keys=invocation.case_keys[:-1]),
                replace(invocation, case_keys=(*invocation.case_keys, invocation.case_keys[0])),
                replace(invocation, mode="diagnostic"), replace(invocation, profiles=("artifacts", "metadata"))):
            with self.subTest(profiles=changed.profiles, mode=changed.mode), patch(
                    "conformance_contributors.execute") as execute, self.assertRaises(evidence.ConformanceError):
                evidence.dispatch_invocation(changed)
            execute.assert_not_called()
        for code in ("AssertionFailed", "InputChanged", "InsufficientCapacity", "CleanupIncomplete"):
            with self.subTest(code=code), patch(
                    "conformance_contributors.execute", side_effect=evidence.ConformanceError(code)), (
                    self.assertRaisesRegex(evidence.ConformanceError, "^" + code + "$")):
                evidence.dispatch_invocation(invocation)
        self.assertFalse(self.destination.exists())

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

    def test_public_native_failure_retains_closed_runtime_observations_without_private_text(self):
        import conformance_cli
        import conformance_sdk_checks as sdk

        error = sdk._RuntimeObservationError({
            "diagnosticCode": "UnknownDiagnostic", "witnesses": (
                {"testIdentity": "private-canary-test", "status": "Failed"},)},
            SimpleNamespace(exit_code=1, events=(
                {"event": "test", "code": "UnknownDiagnostic", "value": 42},)), "Passed")
        observed = error.runtime_diagnostic
        for defect in ("none", "unsafe-code", "unknown-field"):
            error.runtime_diagnostic = dict(observed)
            if defect == "unsafe-code":
                error.runtime_diagnostic["observedCode"] = "private-canary-value"
            elif defect == "unknown-field":
                error.runtime_diagnostic["providerError"] = "private-canary-value"
            output = io.StringIO()
            with self.subTest(defect=defect), contextlib.redirect_stdout(output), patch(
                    "conformance_composition_checks.execute", side_effect=error):
                code = conformance_cli.main([
                    "--profile", "composition", "--evidence", str(self.destination)])
            packet = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertFalse(packet["qualification"])
            self.assertEqual(packet["status"], "Incomplete")
            locations = packet.pop("locations")
            self.assertTrue(0 < len(locations) <= 4)
            self.assertTrue(all(location["source"].startswith("scripts/")
                                and location["line"] > 0 for location in locations))
            if defect == "none":
                self.assertEqual({key: packet[key] for key in observed}, observed)
                self.assertEqual(packet["code"], "EvidenceIncomplete")
            else:
                self.assertEqual(packet["code"], "UnknownDiagnostic")
                self.assertTrue(set(observed).isdisjoint(packet))
            self.assertNotIn("private-canary", output.getvalue())
            self.assertNotIn(str(self.parent), output.getvalue())

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
