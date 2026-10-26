import copy
import hashlib
import json
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_legacy as legacy


class LegacyTransportTests(unittest.TestCase):
    def setUp(self):
        self.work = ROOT / ".foundation" / "legacy-tooling" / uuid.uuid4().hex
        self.work.mkdir(parents=True, mode=0o700)
        self.addCleanup(shutil.rmtree, self.work)

    def test_runtime_staging_refuses_diagnostics_before_copying_any_input(self):
        source = self.work / "source"
        source.mkdir()
        (source / "fixture.deps.json").write_text("{}")
        (source / "fixture.runtimeconfig.json").write_text("{}")
        for name in ("old.trx", "private.log", "crash.dmp", "foreign.json"):
            with self.subTest(name=name):
                path = source / name
                path.write_text("private-canary")
                target = self.work / "target"
                with self.assertRaisesRegex(RuntimeError, "runtime.*input"):
                    legacy._copy_runtime(source, target)
                self.assertFalse(target.exists())
                path.unlink()
        target = self.work / "target"
        legacy._copy_runtime(source, target)
        self.assertEqual({"fixture.deps.json", "fixture.runtimeconfig.json"},
                         {path.name for path in target.iterdir()})

    def test_unattributed_projection_is_rejected_by_default(self):
        import metadata_evidence as metadata
        path = self.work / "unattributed.trx"
        path.write_text("<TestRun/>")
        with self.assertRaisesRegex(RuntimeError, "safe projection is missing"):
            legacy.verify_projection(path)
        with self.assertRaisesRegex(RuntimeError, "safe projection is missing"):
            metadata.trx_results(path)

    def test_os_projection_rejects_diagnostic_text_even_with_a_valid_os_prefix(self):
        arguments = ("dotnet", "Hoard.Fixtures.Metadata.CrashRunner.dll")
        with self.assertRaises(ValueError):
            legacy.project_control(arguments, {"os": "Linux private-canary"})

    def test_barrier_child_output_is_drained_and_rejected_without_persistence(self):
        for count in (1, 1048577):
            with self.subTest(count=count), self.assertRaisesRegex(
                    RuntimeError, "UnknownDiagnostic|OutputLimitExceeded"):
                with legacy.silent_child([sys.executable, "-c",
                                          f"import sys;sys.stdout.buffer.write(b'x'*{count});sys.stdout.flush()"]) as child:
                    child.wait(timeout=10)
            self.assertIsNotNone(child.poll())
        self.assertEqual([], list(self.work.iterdir()))

    def test_post_handshake_output_is_drained_and_rejected(self):
        import artifact_evidence as artifact
        with self.assertRaisesRegex(RuntimeError, "UnknownDiagnostic"):
            with legacy.ErrorCapture() as trailing:
                child = subprocess.Popen(
                    [sys.executable, "-c", "print('{}',flush=True);print('private-canary',flush=True)"],
                    stdout=subprocess.PIPE, start_new_session=True)
                try:
                    self.assertEqual({}, artifact.read_child_line(child, 10))
                    trailing.start_from(child.stdout)
                    child.wait(timeout=10)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.wait(timeout=10)
                    child.stdout.close()
        self.assertEqual([], list(self.work.iterdir()))

    def packet(self, *, failed=False):
        identity = "Hoard.Metadata.Tests.MetadataDeadlineTests.MP18_Known_exception_types_after_commit_attempt_are_still_uncertain"
        image = self.work / "test.dll"
        image.write_bytes(b"synthetic-unit-test-image")
        package = self.work / "sdk.nupkg"
        package.write_bytes(b"synthetic-unit-test-archive")
        run, group, attempt, execution = (str(uuid.uuid4()) for _ in range(4))
        assertion = "Hoard.Testing.Conformance.Metadata.MetadataDeadlineAssertions.KnownExceptionsAsync"
        manifest = {
            "schemaVersion": 1, "runId": run, "invocationGroupId": group, "attemptId": attempt,
            "attemptSequence": 1, "inputSha256": "b" * 64, "purpose": "execution",
            "assemblies": [{"id": "test-assembly", "path": image.name, "sha256": legacy._hash(image)}],
            "packages": [{"id": "shared-sdk", "path": package.name, "sha256": legacy._hash(package)}],
            "expected": [{"testIdentity": identity, "bindingId": "legacy", "matrixId": "none", "caseId": "runtime"}]}
        legacy._write(self.work / f"runtime-input-{attempt}.json", manifest)
        legacy._write(self.work / "runtime-owner.json", {"schemaVersion": 1})
        output = self.work / f"runtime-{attempt}"
        output.mkdir()
        common = {key: manifest[key] for key in (
            "runId", "invocationGroupId", "attemptId", "attemptSequence", "inputSha256")}
        proof = {
            "schemaVersion": 1, **common, "testIdentity": identity, "executionId": execution,
            "bindingId": "legacy", "matrixId": "none", "caseId": "runtime",
            "manifestSha256": legacy._hash(self.work / f"runtime-input-{attempt}.json"),
            "ownerSha256": legacy._hash(self.work / "runtime-owner.json"),
            "assemblySha256": legacy._hash(image), "packageSha256": legacy._hash(package),
            "clock": "system-monotonic-ms", "durationMs": 1.0, "sessionOrigins": [],
            "failureKind": "Assertion" if failed else "None",
            "assertionSymbol": assertion if failed else None, "status": "Failed" if failed else "Passed"}
        proof_path = output / f"proof-{execution}.json"
        proof_path.write_bytes(legacy.canonical_bytes(proof))
        row = {key: proof[key] for key in (
            "executionId", "runId", "invocationGroupId", "testIdentity", "bindingId", "matrixId",
            "inputSha256", "assemblySha256", "packageSha256", "status")}
        row.update(startedMs=100, endedMs=101, proofSha256=legacy._hash(proof_path))
        raw = legacy.canonical_bytes(row) + b"\n"
        (output / "witnesses.jsonl").write_bytes(raw)
        diagnostic = "AssertionFailed" if failed else "None"
        completion = {
            "schemaVersion": 1, **common, "purpose": "execution", "manifestSha256": proof["manifestSha256"],
            "recordsSha256": hashlib.sha256(raw).hexdigest(), "diagnosticCode": diagnostic,
            "observedCount": 1, "expectedCount": 1, "complete": True}
        (output / "completion.json").write_bytes(legacy.canonical_bytes(completion))
        result = subprocess.CompletedProcess([], int(failed), legacy.canonical_bytes(
            {"event": "control", "code": diagnostic, "value": 1}))
        return manifest, result, proof_path, assertion

    def test_safe_transport_requires_original_exact_result_proof_and_completion(self):
        manifest, result, proof, _ = self.packet()
        observed, failures = legacy.validate_transport(self.work, manifest, result, started=99, ended=102)
        self.assertEqual([manifest["expected"][0]["testIdentity"]], [row["test"] for row in observed])
        self.assertEqual([], failures)
        original = proof.read_bytes()
        for key, value in (("testIdentity", "Hoard.Metadata.Tests.Foreign"), ("durationMs", -1),
                           ("status", "Incomplete"), ("failureKind", "Unknown"), ("diagnostic", "private-canary")):
            changed = json.loads(original)
            changed[key] = value
            proof.write_text(json.dumps(changed))
            with self.subTest(key=key), self.assertRaises((RuntimeError, ValueError)):
                legacy.validate_transport(self.work, manifest, result, started=99, ended=102)
        proof.write_bytes(original)
        result.stdout = b"private-canary"
        with self.assertRaisesRegex(RuntimeError, "UnknownDiagnostic") as caught:
            legacy.validate_transport(self.work, manifest, result, started=99, ended=102)
        self.assertNotIn("private-canary", str(caught.exception))

    def test_assertion_negative_requires_actual_matching_failed_witness_and_nonzero_exit(self):
        manifest, result, _, assertion = self.packet(failed=True)
        _, failures = legacy.validate_transport(self.work, manifest, result, started=99, ended=102, assertion=assertion)
        self.assertEqual([manifest["expected"][0]["testIdentity"]], failures)
        for wrong_assertion, wrong_exit in ((None, 1), (assertion + "Foreign", 1), (assertion, 0), (assertion, -9)):
            changed = copy.copy(result)
            changed.returncode = wrong_exit
            with self.subTest(assertion=wrong_assertion, exit=wrong_exit), self.assertRaises(RuntimeError):
                legacy.validate_transport(self.work, manifest, changed, started=99, ended=102, assertion=wrong_assertion)
        result.stdout = b"error CS1001: private-canary"
        with self.assertRaisesRegex(RuntimeError, "UnknownDiagnostic"):
            legacy.validate_transport(self.work, manifest, result, started=99, ended=102, assertion=assertion)

    def test_shared_sdk_loaded_image_must_match_the_actual_package_not_version_labels(self):
        package, image = self.work / "sdk.nupkg", self.work / "Hoard.Testing.Conformance.dll"
        with zipfile.ZipFile(package, "w") as contents:
            contents.writestr("lib/net10.0/Hoard.Testing.Conformance.dll", b"synthetic-original-image")
        legacy.stage_sdk(package, image)
        self.assertEqual(b"synthetic-original-image", image.read_bytes())
        legacy.stage_sdk(package, image)
        image.write_bytes(b"synthetic-same-version-different-image")
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            legacy.stage_sdk(package, image)

    def test_discovery_cannot_substitute_labels_for_frozen_required_runtime_names(self):
        assembly = self.work / "Hoard.Metadata.Tests.dll"
        identity = "Hoard.Metadata.Tests.MetadataDeadlineTests.MP18_Known_exception_types_after_commit_attempt_are_still_uncertain"
        selection = "FullyQualifiedName~MP18_Known_exception_types_after_commit_attempt_are_still_uncertain"
        for output, accepted in (
                (f"VSTest version 18.3.0 (arm64)\nThe following Tests are available:\n    {identity}\n", True),
                (f"The following Tests are available:\n    {identity}\n    {identity}\n", False),
                ("The following Tests are available:\nHoard.Metadata.Tests.MP18_label\n", False),
                ("private-canary\n", False)):
            with self.subTest(output=output), patch.object(
                    legacy, "capture", return_value=subprocess.CompletedProcess([], 0, output.encode())):
                if accepted:
                    self.assertEqual((identity,), legacy._discovery(assembly, selection, {}))
                else:
                    with self.assertRaises(RuntimeError):
                        legacy._discovery(assembly, selection, {})
        with patch.object(legacy, "capture", return_value=subprocess.CompletedProcess(
                [], 0, f"The following Tests are available:\n{identity}\n".encode())):
            self.assertEqual((identity,), legacy._discovery(assembly, "Name~Known_exception_types", {}))

    def test_unbounded_or_unknown_success_output_is_not_returned_to_evidence_writer(self):
        for command, expected in (
                ("import sys;sys.stdout.buffer.write(b'x'*1048577)", "OutputLimitExceeded"),
                ("print('private-canary')", "UnknownDiagnostic")):
            with self.subTest(command=command), self.assertRaisesRegex(RuntimeError, expected) as caught:
                legacy.command((sys.executable, "-c", command))
            self.assertNotIn("private-canary", str(caught.exception))
        self.assertEqual([], list(self.work.iterdir()))

    def test_interrupt_settles_real_owned_child_before_propagating(self):
        real_selector, real_popen = selectors.DefaultSelector, subprocess.Popen
        interrupted = False
        children = []

        class InterruptOnce(real_selector):
            def select(self, timeout=None):
                nonlocal interrupted
                if not interrupted:
                    interrupted = True
                    raise KeyboardInterrupt()
                return super().select(timeout)

        def start(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            if args[0][0] == sys.executable:
                children.append(child)
            return child

        with patch.object(legacy.selectors, "DefaultSelector", InterruptOnce), \
                patch.object(legacy.subprocess, "Popen", side_effect=start), self.assertRaises(KeyboardInterrupt):
            legacy.capture((sys.executable, "-c", "import time;time.sleep(60)"))
        self.assertEqual(1, len(children))
        self.assertIsNotNone(children[0].poll())
        self.assertEqual((), legacy.process_group(children[0].pid))

    def test_os_peak_is_numeric_projection_and_mixed_provider_stderr_is_refused(self):
        darwin = b" 0.01 real 0.00 user 0.00 sys\n123 maximum resident set size\n0 page faults\n"
        linux = b'\tCommand being timed: "dotnet transfer"\n\tMaximum resident set size (kbytes): 123\n'
        for data, is_darwin, wanted in ((darwin, True, 123), (linux, False, 123 * 1024)):
            self.assertEqual(wanted, legacy.peak_rss(data, darwin=is_darwin, arguments=["dotnet", "transfer"]))
            with self.assertRaisesRegex(RuntimeError, "UnknownDiagnostic"):
                legacy.peak_rss(data + b"42 private-canary\n", darwin=is_darwin, arguments=["dotnet", "transfer"])

    def test_interactive_stderr_is_bounded_in_memory_without_a_raw_spool_file(self):
        with self.assertRaisesRegex(RuntimeError, "OutputLimitExceeded"):
            with legacy.ErrorCapture() as errors:
                child = subprocess.Popen(
                    [sys.executable, "-c", "import sys;sys.stderr.buffer.write(b'x'*1048577)"],
                    stdout=subprocess.DEVNULL, stderr=errors, start_new_session=True)
                errors.start()
                try:
                    child.wait(timeout=10)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.wait(timeout=10)
        self.assertLessEqual(len(errors.data), 1048576)
        self.assertEqual([], list(self.work.iterdir()))

    def test_actual_python_verifier_assertion_is_named_without_raw_failure_message(self):
        tests = self.work / "tests/tooling"
        tests.mkdir(parents=True)
        source = tests / "test_negative.py"
        source.write_text("import unittest\nclass Negative(unittest.TestCase):\n"
                          " def test_actual(self):\n"
                          "  with self.subTest(field='private-canary'): self.assertEqual(1,2,'private-canary')\n")
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests/tooling", "-p", "test_negative.py", "-v"]
        code, observed = legacy.python_tests(command, cwd=self.work)
        self.assertEqual(1, code)
        self.assertEqual([{"test": "test_negative.Negative.test_actual", "kind": "Assertion"}], observed["failures"])
        self.assertNotIn("private-canary", json.dumps(observed))
        source.write_text("raise ImportError('private-canary')\n")
        _, observed = legacy.python_tests(command, cwd=self.work)
        self.assertTrue(all(record["kind"] == "Error" for record in observed["failures"]))
