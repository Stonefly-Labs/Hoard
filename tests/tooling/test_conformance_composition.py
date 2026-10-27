import contextlib
import io
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


class CompositionDiagnosticTests(unittest.TestCase):
    def test_workflow_checks_retained_historical_seal_after_stores_are_released(self):
        import hashlib
        import conformance_evidence as evidence
        import conformance_inherited as inherited
        workflow = (ROOT / ".github/workflows/conformance-composition.yml").read_text()
        script = workflow.split("<<'PY'\n", 1)[1].split("\n          PY", 1)[0]
        code = compile(textwrap.dedent(script), "<composition-workflow>", "exec")
        for mutation in ("none", "changed-bytes", "resealed-foreign-root", "false-qualification"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                inputs = {"runId": "run", "sourceRevision": "a" * 40, "sourceState": "clean-ci",
                          "mode": "diagnostic", "profileId": "composition"}
                baseline = {"runId": "run", "rootId": "root", "qualification": False,
                            "nativeContainment": False, "mode": "preparation",
                            "schemaVersion": 1, "baselineRevision": inherited.BASELINE,
                            "recipeSourceSha256": "b" * 64, "files": {}, "retained": {},
                            "registration": {"assembly": str(root / "stores/old/RegistrationConsumer.dll"),
                                             "sha256": "c" * 64}}
                for phase, revision, names in (
                        ("configuration", "b80c69fc386541be4f56f6ef2edeca40f43a0e1c",
                         ("LegacyOptions", "LifecycleConsumer")),
                        ("discovery", "7fd73267a5154583363c94e9e85b9bac7d4a16b3",
                         ("RetainedLifecycle", "RetainedConfiguration", "LegacyOptions"))):
                    baseline["retained"][phase] = [{
                        "name": name, "baseline": revision, "assembly": str(root / f"stores/{phase}/{name}.dll"),
                        "assets": str(root / f"stores/{phase}/{name}.assets.json"), "sha256": "c" * 64,
                    } for name in names]
                for entry in (baseline["registration"], *baseline["retained"]["configuration"],
                              *baseline["retained"]["discovery"]):
                    for field in ("assembly", "assets"):
                        if field in entry:
                            baseline["files"][Path(entry[field]).relative_to(root).as_posix()] = "c" * 64
                if mutation == "resealed-foreign-root":
                    baseline["rootId"] = "foreign-root"
                elif mutation == "false-qualification":
                    baseline["qualification"] = True
                raw = evidence.canonical_bytes(baseline)
                summary = {
                    "qualification": False, "profileComplete": False, "passedComponents": 36,
                    "admittedSnapshots": 110, "processResourcesReleased": True,
                    "inputSha256": evidence.digest(inputs),
                    "inheritedRuntime": {
                        "qualification": False, "profileComplete": False, "executionComplete": True,
                        "nativeContainment": True, "controllerNativeContainment": False,
                        "fullControllerAcceptance": False, "historicalBinariesPreparedBeforeCandidate": True,
                        "historicalBaselineSealSha256": hashlib.sha256(raw).hexdigest(),
                        "passedParameters": 525, "scopes": 58, "commands": [{}] * 58,
                    },
                }
                (root / inherited.CONTROLLER_BASELINES).write_bytes(
                    raw + b"\n" if mutation == "changed-bytes" else raw)
                for path, value in (("proofs/composition-diagnostic-summary.json", summary),
                                    ("proofs/composition-inputs.json", inputs),
                                    ("runtime-owner.json", {"runId": "run", "rootId": "root"})):
                    (root / path).write_bytes(evidence.canonical_bytes(value))
                output = io.StringIO()
                with mock.patch.object(sys, "argv", ["workflow", str(root), "a" * 40]), mock.patch.object(
                        evidence, "admit_entity", side_effect=lambda kind, value: value), \
                        contextlib.redirect_stdout(output):
                    if mutation == "none":
                        exec(code, {"__name__": "__main__"})
                        self.assertEqual({"qualification": False, "status": "Incomplete",
                                          "code": "EvidenceIncomplete"},
                                         evidence.load_json(output.getvalue().encode()))
                    else:
                        with self.assertRaisesRegex(SystemExit, "WitnessMissing"):
                            exec(code, {"__name__": "__main__"})
                self.assertFalse((root / "stores").exists())

    def test_unsupported_native_host_rejects_before_allocating_or_building(self):
        import conformance_composition_checks as checks
        import conformance_evidence as evidence
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "must-not-exist"
            with mock.patch.object(checks, "native_execution_supported", return_value=False), \
                    mock.patch.object(checks.OwnedRun, "allocate") as allocate, \
                    self.assertRaisesRegex(evidence.ConformanceError, "PrerequisiteMissing"):
                checks.execute(ROOT, destination)
            allocate.assert_not_called()
            self.assertFalse(destination.exists())

    def test_cli_reports_incomplete_without_qualifying_a_failed_native_run(self):
        import conformance_composition_checks as checks
        import conformance_evidence as evidence
        output = io.StringIO()
        with mock.patch.object(checks, "execute", side_effect=evidence.ConformanceError("CleanupIncomplete")), \
                contextlib.redirect_stdout(output):
            code = checks.main(["--root", str(ROOT), "--evidence", "/unallocated/test-only"])
        self.assertEqual(code, 2)
        report = evidence.load_json(output.getvalue().encode())
        self.assertEqual(report, {
            "qualification": False, "status": "Incomplete", "code": "CleanupIncomplete"})

    def test_selected_manifest_keeps_every_ownership_parameter(self):
        import conformance_composition_checks as checks
        rows = checks.expected_rows()
        self.assertEqual(len(rows), 36)
        self.assertEqual(len({row["testIdentity"] for row in rows}), 36)
        self.assertEqual(sum(row["caseId"] == "CP-11" for row in rows), 5)
        self.assertEqual({row["caseId"] for row in rows}, {f"CP-{index:02}" for index in range(1, 21)})
        self.assertEqual(sum(row["caseId"] == "CP-19" for row in rows), 2)
        self.assertEqual(sum(row["caseId"] == "CP-20" for row in rows), 2)
        self.assertEqual(sum(row["caseId"] == "CP-14" for row in rows), 3)
        self.assertEqual(sum(row["caseId"] == "CP-18" for row in rows), 1)
        self.assertEqual(sum(row["caseId"] == "CP-16" for row in rows), 2)
        self.assertEqual(sum(row["caseId"] == "CP-17" for row in rows), 3)
        self.assertTrue(all(row["bindingId"] == "none" for row in rows))


if __name__ == "__main__":
    unittest.main()
