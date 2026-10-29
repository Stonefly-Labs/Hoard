import base64
import binascii
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
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
        def inspect(output):
            for canary in self.canaries:
                self.assertFalse(canary in output, "A synthetic private canary reached retained output.")
            for candidate in re.findall(rb"[A-Za-z0-9+/]{16,}={0,2}", output):
                try:
                    decoded = base64.b64decode(candidate, validate=True)
                except binascii.Error:
                    continue
                for canary in self.canaries:
                    self.assertFalse(canary in decoded, "An encoded private canary reached retained output.")

        for output in outputs:
            inspect(output)
        for path in root.rglob("*"):
            inspect(os.fsencode(path.relative_to(root)))
            if path.is_file():
                inspect(path.read_bytes())
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

    def test_diagnostic_and_qualification_mode_outputs_publish_without_overwriting_either_attempt(self):
        from conformance_sdk_checks import write_new

        published = {}
        for mode in ("diagnostic", "qualification"):
            report = self.diagnostic_presentation_fixture()
            report["inputs"]["mode"] = mode
            hashed_inputs = evidence.digest(report["inputs"])
            report["witnesses"][0]["inputSha256"] = hashed_inputs
            report["postInputSha256"] = hashed_inputs
            raw = evidence.canonical_bytes(report)
            expected = hashlib.sha256(raw).hexdigest()
            with mock.patch.object(evidence, "verify_retained_category_report", return_value={
                    "qualification": False, "reportSha256": expected}):
                outputs = evidence.render_category_diagnostics(
                    self.parent, raw, expected_inputs=report["inputs"], expected_report_sha256=expected)
            for name, contents in outputs.items():
                write_new(self.parent / name, contents)
                published[name] = contents
            self.assertEqual(evidence.proof_manifest(self.parent), {
                name: hashlib.sha256(contents).hexdigest() for name, contents in published.items()})
            self.assert_clean(self.parent, *outputs.values())
        self.assertEqual(len(published), 8)

    def test_retained_composition_settings_keep_private_paths_only_in_held_command_arguments(self):
        import conformance_composition_checks as composition
        from conformance_sources import runtime_arguments

        root = self.parent / "evidence"
        for directory in ("stores/runtime", "snapshot/tests/Consumer/bin/Release/net10.0"):
            with self.subTest(directory=directory):
                assembly = root / directory / "Consumer.dll"
                attempt = str(uuid.uuid4())
                raw = composition._composition_settings(
                    root, assembly, attempt, {"runId": str(uuid.uuid4())},
                    {"rootPathSha256": hashlib.sha256(os.fsencode(root)).hexdigest()})
                self.assert_clean(self.parent, raw)
                relative = ET.fromstring(raw).findtext(".//Logger/Configuration/Root")
                self.assertFalse(Path(relative).is_absolute())
                self.assertEqual((assembly.parent / relative).resolve(), root)
                arguments = runtime_arguments(assembly, root / "proofs/settings.runsettings", ("Tests.Case",))
                self.assertIn("--TestAdapterPath:" + str(assembly.parent), arguments)

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

    @unittest.skipUnless(execution.native_execution_supported(), "Configuration settlement requires native Linux.")
    def test_private_executable_settings_remain_bound_until_real_settlement_and_do_not_persist(self):
        import conformance_sdk_checks as checks
        from conformance_sources import runtime_settings

        run = execution.OwnedRun.allocate(self.parent / "evidence", ROOT, profile="harness")
        attempt = str(uuid.uuid4())
        settings = run.root / "stores" / ("settings-" + attempt + ".runsettings")
        payload = b";".join((*self.canaries, os.fsencode(run.root)))
        environment = ("<EnvironmentVariables><HOARD_CONFIGURATION_CANARY>"
                       + base64.b64encode(payload).decode()
                       + "</HOARD_CONFIGURATION_CANARY></EnvironmentVariables>")
        raw = runtime_settings(run.root, run.root / "stores/Consumer.dll", attempt, "a" * 64, "b" * 64, environment)
        checks.write_new(settings, raw)
        relative = settings.relative_to(run.root).as_posix()
        command = (
            "import json,sys,xml.etree.ElementTree as ET;"
            "ET.parse(sys.argv[1]);"
            "print(json.dumps({'event':'control','code':'None','value':0}))")
        observed = run.command(
            [sys.executable, "-I", "-S", "-c", command, relative], cwd=run.root,
            record_execution=True, execution_inputs=(relative,))
        self.assertEqual(observed.exit_code, 0)
        record = evidence.load_json(run.read_execution_record(run.command_sequence))
        self.assertEqual(record["inputFiles"], {relative: hashlib.sha256(raw).hexdigest()})
        self.assertEqual(settings.read_bytes(), raw)
        with self.assertRaises(AssertionError):
            self.assert_clean(run.root, raw)
        run.transition("Settling")
        run.release()
        self.assertEqual(run.state, "Released")
        self.assertFalse(settings.exists())
        self.assert_clean(run.root, evidence.canonical_bytes(run.resource_projection()))

    @unittest.skipUnless(execution.native_execution_supported(), "Build snapshot settlement requires native Linux.")
    def test_build_snapshot_private_metadata_is_transient_without_weakening_source_binding(self):
        run = execution.OwnedRun.allocate(self.parent / "evidence", ROOT, profile="harness")
        author = self.parent / "author"
        author.mkdir(mode=0o700)
        project = author / "Fixture.csproj"
        project.write_bytes(b"<Project/>")
        original = {"Fixture.csproj": evidence.file_sha256(project)}
        snapshot, files = evidence.snapshot_sources(
            author, run, name="composition-source", manifest=original, transient=True)
        self.assertEqual(snapshot.parent, run.root / "stores")
        self.assertEqual(dict(files), original)
        evidence.verify_snapshot(snapshot, original)
        metadata = snapshot / "obj/project.assets.json"
        metadata.parent.mkdir(mode=0o700)
        payload = b";".join((*self.canaries, os.fsencode(run.root)))
        raw = evidence.canonical_bytes({"path": payload.decode(), "encoded": base64.b64encode(payload).decode()})
        metadata.write_bytes(raw)
        metadata.chmod(0o400)
        relative = metadata.relative_to(run.root).as_posix()
        observed = run.command(
            [sys.executable, "-I", "-S", "-c",
             "import pathlib,sys;pathlib.Path(sys.argv[1]).read_bytes()", relative],
            cwd=run.root, record_execution=True, execution_inputs=(relative,))
        self.assertEqual(observed.exit_code, 0)
        record = evidence.load_json(run.read_execution_record(run.command_sequence))
        self.assertEqual(record["inputFiles"], {relative: hashlib.sha256(raw).hexdigest()})
        self.assertEqual(metadata.read_bytes(), raw)
        run.transition("Settling")
        run.release()
        self.assertEqual(run.state, "Released")
        self.assertFalse(snapshot.exists())
        self.assert_clean(run.root, evidence.canonical_bytes(run.resource_projection()))

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
