import contextlib
import copy
import hashlib
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
import xml.etree.ElementTree as ET

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

    def diagnostic_presentation_fixture(self):
        from test_conformance_evidence import ConformanceAdmissionTests
        report = ConformanceAdmissionTests().report()
        report.update(state="Incomplete", scope=["category-runtime-diagnostic"])
        inputs = report["inputs"]
        inputs["packages"][0]["packageId"] = self.canaries[0].decode()
        inputs["bindings"][0]["package"] = copy.deepcopy(inputs["packages"][0])
        inputs["environment"]["osVersion"] = self.canaries[2].decode()
        inputs["environmentSha256"] = evidence.digest(inputs["environment"])
        inputs["sourceManifest"] = {"src/" + self.canaries[4].decode() + ".cs": "a" * 64}
        inputs["sourceManifestSha256"] = evidence.digest(inputs["sourceManifest"])
        inputs["packages"][0]["runtimeAssemblies"] = {
            "lib/net10.0/" + self.canaries[3].decode() + ".dll": "d" * 64}
        inputs["bindings"][0]["package"] = copy.deepcopy(inputs["packages"][0])
        report["proofs"] = {"runtime/" + self.canaries[1].decode() + ".json": "a" * 64}
        report["witnesses"][0]["inputSha256"] = evidence.digest(inputs)
        report["postInputSha256"] = evidence.digest(inputs)
        return report

    def test_diagnostic_json_junit_markdown_and_ci_surfaces_do_not_repeat_private_inputs(self):
        render = getattr(evidence, "render_category_diagnostics", None)
        self.assertTrue(callable(render), "Diagnostic output needs a closed safe public projection.")
        report = self.diagnostic_presentation_fixture()
        raw = evidence.canonical_bytes(report)
        expected = hashlib.sha256(raw).hexdigest()
        # Isolate presentation; real native packet verification has separate integration controls.
        with mock.patch.object(evidence, "verify_retained_category_report", return_value={
                "qualification": False, "reportSha256": expected}) as verify:
            outputs = render(self.parent, raw, expected_inputs=report["inputs"],
                             expected_report_sha256=expected)
        verify.assert_called_once_with(
            self.parent, raw, expected_inputs=report["inputs"], expected_report_sha256=expected)
        self.assertEqual(set(outputs), {
            "category-metadata-diagnostic.json", "category-metadata-diagnostic.junit.xml",
            "category-metadata-diagnostic.md", "category-metadata-ci-summary.md"})
        for name, contents in outputs.items():
            path = self.parent / name
            path.write_bytes(contents)
            self.assert_clean(self.parent, contents)
        summary = json.loads(outputs["category-metadata-diagnostic.json"])
        self.assertFalse(summary["qualification"])
        self.assertEqual(summary["state"], "Incomplete")
        self.assertEqual(summary["reportSha256"], expected)
        self.assertEqual(summary["caseStates"]["Passed"], 1)
        self.assertEqual(summary["support"]["status"], "NotQualified")
        xml = ET.fromstring(outputs["category-metadata-diagnostic.junit.xml"])
        self.assertGreaterEqual(int(xml.attrib["errors"]), 1)
        self.assertIsNotNone(xml.find("./testcase/error[@type='EvidenceIncomplete']"))
        for name in ("category-metadata-diagnostic.md", "category-metadata-ci-summary.md"):
            self.assertIn(b"not qualification", outputs[name])

    def test_unknown_diagnostic_report_fields_reject_instead_of_disappearing_into_public_success(self):
        render = getattr(evidence, "render_category_diagnostics", None)
        self.assertTrue(callable(render), "Unknown report text must reject before rendering.")
        report = self.diagnostic_presentation_fixture()
        report["providerError"] = b";".join(self.canaries).decode()
        raw = evidence.canonical_bytes(report)
        expected = hashlib.sha256(raw).hexdigest()
        with mock.patch.object(evidence, "verify_retained_category_report", return_value={
                "qualification": False, "reportSha256": expected}):
            with self.assertRaises(evidence.ConformanceError):
                render(self.parent, raw, expected_inputs=report["inputs"],
                       expected_report_sha256=expected)
        self.assertEqual(list(self.parent.iterdir()), [])

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
