import copy
import base64
import hashlib
import json
import os
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

    @unittest.skipUnless(sys.platform == "linux", "Requires actual Linux process-group guard.")
    def test_native_preparation_borrows_guarded_group_without_attempting_a_new_session(self):
        program = """
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import conformance_legacy as legacy
from conformance_process import install_group_guard
install_group_guard()
try:
    legacy.capture([sys.executable, "-c", "print('closed')"])
except RuntimeError as error:
    assert str(error) == "Legacy command CommandFailed."
else:
    raise AssertionError("unguarded legacy launch unexpectedly succeeded")
pid = os.getpid()
header = {"groups": [pid], "children": {str(pid): legacy.process_identity(pid)}}
owner = Path(sys.argv[2])
tracked = owner / "tracked-input"
tracked.write_bytes(b"unchanged")
expected = legacy._hash(tracked)
def read_inputs(args, **kwargs):
    return {"tracked-input": expected}
with legacy.native_preparation_group(header, input_owner=owner, input_reader=read_inputs) as journal:
    invocations = journal["invocations"]
    result = legacy.capture([sys.executable, "-c", "print('closed')"])
    assert result.returncode == 0 and result.stdout == b"closed\\n"
    observed = result.native_invocation
    assert observed["groupPid"] == pid and observed["groupStartSha256"] == header["children"][str(pid)]
    assert observed["childPid"] != pid and observed["childPid"] > 0
    assert len(observed["childStartSha256"]) == 64
    assert observed["childState"] == "Exited" and observed["groupState"] == "Borrowed"
    assert observed["exitCode"] == 0 and observed["stdinSha256"] is None
    assert observed["argvSha256"] == legacy.hashlib.sha256(
        legacy.canonical_bytes([sys.executable, "-c", "print('closed')"])).hexdigest()
    fast = legacy.capture(["/bin/true"])
    assert fast.native_invocation["childState"] == "Exited"
    assert fast.native_invocation["childStartSha256"] != observed["childStartSha256"]
    assert invocations == [observed, fast.native_invocation]
    with legacy.OwnedChild(
            [sys.executable, "-c", "import time;print('barrier',flush=True);time.sleep(60)"],
            stdout=legacy.subprocess.PIPE, stderr=legacy.subprocess.STDOUT) as owned:
        with owned.stdout:
            assert owned.stdout.readline() == b"barrier\\n"
            owned.kill()
            assert owned.wait(timeout=5) == -legacy.signal.SIGKILL
    assert len(invocations) == 3 and invocations[-1] == owned.native_invocation
    assert invocations[-1]["exitCode"] == -legacy.signal.SIGKILL
    legacy.verify_borrowed_invocations(invocations, group_pid=pid, group_start_sha256=header["children"][str(pid)])
    legacy.verify_borrowed_input_snapshots(journal["inputSnapshots"], 3)
    assert all(snapshot["files"] == {"tracked-input": legacy._hash(tracked)}
               for snapshot in journal["inputSnapshots"])
    try:
        legacy.capture([sys.executable, "-c", "from pathlib import Path;Path(" + repr(str(tracked)) +
                        ").write_bytes(b'changed')"])
    except legacy.ConformanceError as error:
        assert str(error) == "InputChanged"
    else:
        raise AssertionError("changed native input was admitted")
    sentinel = owner / "must-not-launch"
    try:
        legacy.capture([sys.executable, "-c", "from pathlib import Path;Path(" + repr(str(sentinel)) +
                        ").touch()"])
    except legacy.ConformanceError as error:
        assert str(error) == "InputChanged"
    else:
        raise AssertionError("changed input was admitted before launch")
    assert not sentinel.exists()
    assert len(invocations) == len(journal["inputSnapshots"]) == 3
assert legacy._borrowed_group() is None
"""
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-c", program, str(ROOT / "scripts"), str(self.work)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, timeout=20, check=False)
        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8", errors="replace"))
        self.assertEqual(b"", result.stdout)

    def test_native_preparation_rejects_an_unadmitted_group(self):
        with self.assertRaisesRegex(legacy.ConformanceError, "OwnershipInvalid"):
            with legacy.native_preparation_group({"groups": [], "children": {}}):
                self.fail("Foreign process must not borrow a native group.")

    def test_reference_consumer_requires_exact_closed_presentation_without_execution_authority(self):
        body = {"modules": [{
            "id": "fixture.protocol.one", "category": "protocol", "inclusion": "included",
            "registered": True, "enabled": True, "readiness": "ready", "lifecyclePhase": "running",
            "selectedRoles": [], "provenance": {"classification": "fixture"}, "reasons": [],
            "capabilities": [{"operationId": "inspect", "support": "supported", "evidenceScope": "fixture",
                              "availability": "usable", "reasons": []}],
        }], "observation": {key: "2026-10-21T15:00:00.1234567Z"
                           for key in ("capturedAt", "publishedAt", "readinessAssessedAt")}}
        pairs = [
            ("inclusion", "Included"), ("registration", "Registered"), ("enablement", "Enabled selection"),
            ("observed readiness", "ready"), ("authority phase", "running"),
            *[(label, "2026-10-21T15:00:00.1234567+00:00") for label in ("captured", "published", "assessed")],
            ("inspect support", "supported"),
            ("inspect evidence scope", "Fixture-tested only; not production, native-client or conformance qualification."),
            ("inspect availability", "usable"),
        ]
        value = [{"Id": "fixture.protocol.one", "ReadingOrder": [
            {"Order": index, "Label": "fixture.protocol.one: " + label, "Text": text}
            for index, (label, text) in enumerate(pairs, 1)],
                  "Actions": [{"OperationId": "inspect", "AccessibleName": "fixture.protocol.one: inspect",
                               "Hidden": True, "Enabled": False,
                               "Explanation": "Observation is not current; refresh before acting."}]}]
        args = ("dotnet", "ReferenceConsumer.dll")
        for mutation in ("none", "private-text", "missing-line", "extra-field", "foreign-module",
                         "execution-authority", "boolean-order"):
            altered = copy.deepcopy(value)
            if mutation == "private-text":
                altered[0]["ReadingOrder"][0]["Text"] = "private-canary"
            elif mutation == "missing-line":
                altered[0]["ReadingOrder"].pop()
            elif mutation == "extra-field":
                altered[0]["private"] = "private-canary"
            elif mutation == "foreign-module":
                altered[0]["Id"] = "private-canary"
            elif mutation == "execution-authority":
                altered[0]["Actions"][0]["Enabled"] = True
            elif mutation == "boolean-order":
                altered[0]["ReadingOrder"][0]["Order"] = True
            with self.subTest(mutation=mutation), patch.object(
                    legacy, "discovery_fixture_wire", return_value=body), patch.object(
                    legacy, "capture", return_value=subprocess.CompletedProcess(args, 0, json.dumps(altered).encode())):
                if mutation == "none":
                    projected = legacy.composition_controller_command(args, input=json.dumps(body))
                    self.assertEqual([{"Id": "fixture.protocol.one"}], json.loads(projected.stdout))
                else:
                    with self.assertRaisesRegex(RuntimeError, "UnknownDiagnostic"):
                        legacy.composition_controller_command(args, input=json.dumps(body))
        for source in (None, '{"private":"private-canary"}'):
            with self.subTest(source=source), patch.object(legacy, "capture") as capture, \
                    self.assertRaises(RuntimeError):
                legacy.composition_controller_command(args, input=source)
            capture.assert_not_called()

    def test_control_input_is_bounded_transient_and_does_not_block_output_drain(self):
        body = "private-canary" * 10000
        result = legacy.capture(
            [sys.executable, "-c", "import sys;sys.stdout.buffer.write(b'v'*131072);sys.stdout.flush();"
             "value=sys.stdin.buffer.read();print(len(value))"],
            input=body, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"v" * 131072 + (str(len(body.encode())) + "\n").encode())
        self.assertEqual([], list(self.work.iterdir()))
        with patch.object(legacy.subprocess, "Popen") as start, \
                self.assertRaisesRegex(RuntimeError, "OutputLimitExceeded"):
            legacy.capture([sys.executable, "-c", "pass"], input="x" * 1048577)
        start.assert_not_called()

    def test_inherited_compiler_controls_keep_only_the_intended_closed_code(self):
        args = ("dotnet", "build", "Consumer.csproj", "-v", "quiet")
        raw = b"/private/canary.cs(1,1): error CS0535: secret-canary missing contract [Consumer.csproj]\nBuild FAILED.\n"
        with patch.object(legacy, "capture", return_value=subprocess.CompletedProcess(args, 1, raw)):
            result = legacy.composition_controller_command(args, expected="CS0535")
            self.assertEqual(result.stdout, "CS0535")
            with self.assertRaisesRegex(RuntimeError, "CommandFailed"):
                legacy.composition_controller_command(args, expected="CS9035")
            with self.assertRaisesRegex(RuntimeError, "CommandFailed"):
                legacy.composition_controller_command(args)

    def test_unadapted_controller_commands_reject_before_launch_or_diagnostic_persistence(self):
        for args in (("dotnet", "test", "Hoard.Composition.Tests.csproj"),
                     ("dotnet", "UnknownHost.dll"), ("python3", "-m", "unittest")):
            with self.subTest(args=args), patch.object(legacy, "capture") as capture, \
                    self.assertRaisesRegex(RuntimeError, "PrerequisiteMissing"):
                legacy.composition_controller_command(args)
            capture.assert_not_called()

    def test_publication_barrier_output_rejects_private_or_unterminated_diagnostics(self):
        for raw, accepted in ((b"barrier:Flush\n", True), (b"private-canary\n", False),
                              (b"barrier:Flush\nprivate-canary", False), (b"barrier:Flush", False)):
            reader, writer = os.pipe()
            with os.fdopen(reader, "rb") as stream:
                os.write(writer, raw)
                os.close(writer)
                output = legacy.PublicationOutput(stream, "Flush")
                if accepted:
                    self.assertEqual("barrier:Flush\n", output.readline())
                else:
                    with self.assertRaisesRegex(RuntimeError, "UnknownDiagnostic|CommandFailed"):
                        output.readline()

    def test_publication_child_rejects_unowned_inputs_before_launch(self):
        with patch.object(legacy.subprocess, "Popen") as start:
            owner = self.work.resolve()
            for arguments in (("dotnet", "/outside/ConversionProcess.dll", "/outside/old", "/outside/new", "Flush"),
                              ("dotnet", str(owner / "Unknown.dll"), str(owner / "old"), str(owner / "new"), "Flush")):
                with self.subTest(arguments=arguments), self.assertRaises(legacy.ConformanceError):
                    legacy.PublicationChild(arguments, owner=owner, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True)
            start.assert_not_called()

    def test_discovery_controller_requires_matching_closed_bodies_and_complete_host_journeys(self):
        module_ids = ("fixture.protocol.one", "fixture.protocol.two", "fixture.legacy-options",
                      "fixture.artifact.one", "fixture.identity", "fixture.unregistered")
        value = {"journeys": [], "observations": [], "responseBodies": []}
        for index, name in enumerate(("baseline", "bundled-restart", "recovery"), 1):
            observation = {
                "schemaVersion": 1,
                "distribution": {"id": "package-discovery-fixture", "version": "0.1.0", "inventoryCompleteness": "partial"},
                "host": {"phase": "running", "ready": True, "startupAdmission": True},
                "observation": {"lifecycleId": str(uuid.UUID(int=index)), "revision": "1",
                                "capturedAt": "2026-10-21T15:00:01Z", "publishedAt": "2026-10-21T15:00:00Z",
                                "readinessAssessedAt": "2026-10-21T15:00:00Z"},
                "modules": [{
                    "id": name, "category": "protocol", "version": "0.1.0", "inclusion": "included",
                    "registered": True, "enabled": False, "lifecyclePhase": "registered", "readiness": "disabled",
                    "compatibility": {"hostRange": "[0.1.0,0.2.0)", "abstractionsRange": "[0.1.0,0.2.0)",
                                      "allowHostPrerelease": False, "allowAbstractionsPrerelease": False},
                    "provenance": {"classification": "fixture"}, "selectedRoles": [], "options": [],
                    "capabilities": [], "reasons": [], "omittedReasonCount": 0,
                } for name in module_ids], "reasons": [], "omittedReasonCount": 0}
            raw = json.dumps(observation).encode()
            value["journeys"].append({"id": name, "passed": True, "lifecycleId": str(uuid.UUID(int=index)),
                                      "routeCalls": 1, "serviceCalls": 1, "bytes": len(raw)})
            value["observations"].append(observation)
            value["responseBodies"].append(base64.b64encode(raw).decode("ascii"))
        value["journeys"].append({"id": "invalid-replacement", "passed": True, "diagnostics": 1, "activityDelta": 0})
        args = ("dotnet", "LifecycleHost.Discovery.dll")
        self.assertEqual(value, legacy.composition_control(args, copy.deepcopy(value)))
        for mutation in ("private-wire-text", "private-key", "changed-body", "boolean-alias",
                         "duplicate-lifecycle", "missing-journey"):
            altered = copy.deepcopy(value)
            if mutation == "private-wire-text":
                altered["observations"][0]["modules"][0]["id"] = "private-canary"
            elif mutation == "private-key":
                altered["observations"][0]["private-canary"] = True
            elif mutation == "changed-body":
                altered["responseBodies"][0] = altered["responseBodies"][1]
            elif mutation == "boolean-alias":
                body = copy.deepcopy(altered["observations"][0])
                body["schemaVersion"] = True
                raw = json.dumps(body).encode()
                altered["journeys"][0]["bytes"] = len(raw)
                altered["responseBodies"][0] = base64.b64encode(raw).decode("ascii")
            elif mutation == "duplicate-lifecycle":
                altered["journeys"][1]["lifecycleId"] = altered["journeys"][0]["lifecycleId"]
            else:
                altered["journeys"].pop()
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, legacy.ConformanceError)):
                legacy.composition_control(args, altered)

    def test_inherited_journey_controls_reject_unexpected_fields_names_and_failure_labels(self):
        args = ("dotnet", "LifecycleHost.dll")
        good = {"journeys": [{"name": "bundled-one", "passed": True, "events": 4}]}
        self.assertEqual(good, legacy.composition_control(args, good))
        for mutation in ("field", "name", "status", "zero", "boolean-count"):
            altered = copy.deepcopy(good)
            if mutation == "field":
                altered["private"] = "canary"
            elif mutation == "name":
                altered["journeys"][0]["name"] = "private-canary"
            elif mutation == "status":
                altered["journeys"][0]["passed"] = False
            elif mutation == "zero":
                altered["journeys"][0]["events"] = 0
            else:
                altered["journeys"][0]["events"] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                legacy.composition_control(args, altered)

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

    def test_runtime_staging_accepts_a_dotted_apphost_only_with_its_execution_inputs(self):
        source = self.work / "source"
        source.mkdir()
        for name in ("Fixture.Tests", "Fixture.Tests.dll", "Fixture.Tests.runtimeconfig.json"):
            (source / name).write_bytes(b"synthetic-unit-test-input")
        mapping = source / ".msCoverageSourceRootsMapping_Fixture.Tests"
        mapping.write_bytes(b"private-source-path-canary")
        target = self.work / "target"
        legacy._copy_runtime(source, target)
        self.assertEqual({path.name for path in source.iterdir() if path != mapping},
                         {path.name for path in target.iterdir()})
        (source / "Fixture.Tests.runtimeconfig.json").unlink()
        with self.assertRaisesRegex(RuntimeError, "runtime.*input"):
            legacy._copy_runtime(source, self.work / "rejected")

    def test_os_projection_rejects_diagnostic_text_even_with_a_valid_os_prefix(self):
        arguments = ("dotnet", "Hoard.Fixtures.Metadata.CrashRunner.dll")
        with self.assertRaises(ValueError):
            legacy.project_control(arguments, {"os": "Linux private-canary"})
        with patch.object(legacy.sys, "platform", "darwin"):
            self.assertEqual({"os": "macos"}, legacy.project_control(arguments, {"os": "macOS 15.6.1"}))
            with self.assertRaises(ValueError):
                legacy.project_control(arguments, {"os": "macOS 15.6.1 private-canary"})

    def test_barrier_child_output_is_drained_and_rejected_without_persistence(self):
        for count in (1, 1048577):
            with self.subTest(count=count), self.assertRaisesRegex(
                    RuntimeError, "UnknownDiagnostic|OutputLimitExceeded"):
                with legacy.silent_child([sys.executable, "-c",
                                          f"import sys;sys.stdout.buffer.write(b'x'*{count});sys.stdout.flush()"]) as child:
                    child.wait(timeout=10)
            self.assertIsNotNone(child.poll())
        self.assertEqual([], list(self.work.iterdir()))

    def test_interactive_exit_settles_descendants_with_closed_or_inherited_output(self):
        unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"],
                                     start_new_session=True)
        try:
            for inherited in (False, True):
                output = "" if inherited else ",stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL"
                code = ("import subprocess,sys;subprocess.Popen([sys.executable,'-c',"
                        "'import time;time.sleep(60)']" + output + ")")
                with self.subTest(inherited=inherited):
                    with legacy.silent_child([sys.executable, "-c", code]) as child:
                        self.assertEqual(0, child.wait(timeout=10))
                        self.assertEqual(len(legacy.process_group(child.pid)), 1)
                        self.assertIsNone(child._process.returncode)
                    self.assertEqual((), legacy.process_group(child.pid))
                    self.assertIsNone(unrelated.poll())
        finally:
            unrelated.kill()
            unrelated.wait(timeout=10)

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

    def packet(self, *, failed=False, binding="legacy", environment=None):
        identity = "Hoard.Metadata.Tests.MetadataDeadlineTests.MP18_Known_exception_types_after_commit_attempt_are_still_uncertain"
        image = self.work / "test.dll"
        image.write_bytes(b"synthetic-unit-test-image")
        package = self.work / "sdk.nupkg"
        package.write_bytes(b"synthetic-unit-test-archive")
        run, group, attempt, execution = (str(uuid.uuid4()) for _ in range(4))
        assertion = "Hoard.Testing.Conformance.Metadata.MetadataDeadlineAssertions.KnownExceptionsAsync"
        images = [{"id": "test-assembly", "path": image.name, "sha256": legacy._hash(image)}]
        legacy._write(self.work / "legacy-inputs.json", {
            "schemaVersion": 1, "runId": run, "invocationGroupId": group,
            "assemblies": images, "packageSha256": legacy._hash(package),
            "configuration": {"bindingId": binding, "environmentSha256": legacy._environment_sha256(environment)}})
        manifest = {
            "schemaVersion": 1, "runId": run, "invocationGroupId": group, "attemptId": attempt,
            "attemptSequence": 1, "inputSha256": legacy._hash(self.work / "legacy-inputs.json"),
            "purpose": "execution", "runInputsPath": "legacy-inputs.json",
            "assemblies": images,
            "packages": [{"id": "shared-sdk", "path": package.name, "sha256": legacy._hash(package)}],
            "expected": [{"testIdentity": identity, "bindingId": binding, "matrixId": "none", "caseId": "runtime"}]}
        legacy._write(self.work / f"runtime-input-{attempt}.json", manifest)
        legacy._write(self.work / "runtime-owner.json", {"schemaVersion": 1})
        output = self.work / f"runtime-{attempt}"
        output.mkdir()
        common = {key: manifest[key] for key in (
            "runId", "invocationGroupId", "attemptId", "attemptSequence", "inputSha256")}
        proof = {
            "schemaVersion": 1, **common, "testIdentity": identity, "executionId": execution,
            "bindingId": binding, "matrixId": "none", "caseId": "runtime",
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

    def test_projection_replay_requires_the_independently_selected_provider_and_configuration(self):
        parent = self.work
        self.work = parent / ("safe-" + uuid.uuid4().hex)
        self.work.mkdir()
        environment = {"HOARD_METADATA_PROVIDER": "memory", "HOARD_METADATA_WORKSPACE": str(parent)}
        manifest, result, _, _ = self.packet(binding="memory", environment=environment)
        projection = parent / "memory.trx"
        projection.write_text("<TestRun/>")
        legacy._write(projection.with_suffix(".runtime.json"), {
            "schemaVersion": 1, "projectionSha256": legacy._hash(projection), "transport": self.work.name,
            "attemptId": manifest["attemptId"],
            "manifestSha256": legacy._hash(self.work / f'runtime-input-{manifest["attemptId"]}.json'),
            "startedMs": 99, "endedMs": 102, "exitCode": 0, "assertionSymbol": None,
            "events": [json.loads(result.stdout)]})
        legacy.verify_projection(projection, expected_binding="memory", expected_environment=environment)
        for provider, expected in (("sqlite", environment), ("legacy", environment),
                                   ("memory", {**environment, "HOARD_METADATA_WORKSPACE": str(parent / "foreign")})):
            with self.subTest(provider=provider), self.assertRaisesRegex(RuntimeError, "configured provider"):
                legacy.verify_projection(projection, expected_binding=provider, expected_environment=expected)

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

    def test_logger_admission_failure_preserves_its_closed_code_without_completion(self):
        manifest, result, _, _ = self.packet()
        completion = self.work / f'runtime-{manifest["attemptId"]}' / "completion.json"
        completion.unlink()
        for code in ("OwnershipInvalid", "EvidenceSchemaInvalid", "InputChanged", "ProofMismatch"):
            result.stdout = legacy.canonical_bytes({"event": "control", "code": code, "value": 0})
            result.returncode = 1
            with self.subTest(code=code), self.assertRaises(legacy.ConformanceError) as caught:
                legacy.validate_transport(self.work, manifest, result, started=99, ended=102)
            self.assertEqual(code, str(caught.exception))
        result.stdout = b"private-canary"
        with self.assertRaisesRegex(RuntimeError, "^Legacy runtime UnknownDiagnostic.$"):
            legacy.validate_transport(self.work, manifest, result, started=99, ended=102)

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

    def test_original_guard_projection_cannot_be_borrowed_as_an_assertion_or_unknown_failure(self):
        manifest, result, path, _ = self.packet(failed=True, binding="none")
        method = ("Hoard.Composition.Tests.DiscoveryBoundsTests."
                  "Cancellation_deadline_and_inconsistent_authority_never_become_successful_observations")
        manifest["expected"][0].update(
            testIdentity=method, fullyQualifiedName=method, assertionSymbol=method,
            matrixId="inherited.discovery.mutation", caseId="inherited-discovery-guard-source-identity")
        manifest_path = self.work / f'runtime-input-{manifest["attemptId"]}.json'
        manifest_path.chmod(0o600)
        manifest_path.write_bytes(legacy.canonical_bytes(manifest))
        proof = json.loads(path.read_bytes())
        proof.update(testIdentity=method, matrixId="inherited.discovery.mutation",
                     caseId="inherited-discovery-guard-source-identity",
                     manifestSha256=legacy._hash(manifest_path), failureKind="Guard", assertionSymbol=None)
        path.write_bytes(legacy.canonical_bytes(proof))
        witnesses = path.parent / "witnesses.jsonl"
        row = json.loads(witnesses.read_bytes())
        row.update(testIdentity=method, matrixId=proof["matrixId"], proofSha256=legacy._hash(path))
        witnesses.write_bytes(legacy.canonical_bytes(row) + b"\n")
        completion_path = path.parent / "completion.json"
        completion = json.loads(completion_path.read_bytes())
        completion.update(manifestSha256=legacy._hash(manifest_path),
                          recordsSha256=hashlib.sha256(witnesses.read_bytes()).hexdigest(),
                          diagnosticCode="EvidenceIncomplete", complete=False)
        completion_path.write_bytes(legacy.canonical_bytes(completion))
        result.stdout = legacy.canonical_bytes({"event": "control", "code": "EvidenceIncomplete", "value": 1})
        _, failures = legacy.validate_transport(self.work, manifest, result, started=99, ended=102)
        self.assertEqual([method], failures)
        with self.assertRaises(RuntimeError):
            legacy.validate_transport(self.work, manifest, result, started=99, ended=102, assertion=method)
        for kind in ("Unknown", "Assertion"):
            proof["failureKind"] = kind
            path.write_bytes(legacy.canonical_bytes(proof))
            row["proofSha256"] = legacy._hash(path)
            witnesses.write_bytes(legacy.canonical_bytes(row) + b"\n")
            completion["recordsSha256"] = hashlib.sha256(witnesses.read_bytes()).hexdigest()
            completion_path.write_bytes(legacy.canonical_bytes(completion))
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                legacy.validate_transport(self.work, manifest, result, started=99, ended=102)

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

    def test_owned_commands_disable_build_servers_and_unused_framework_watchers(self):
        result = legacy.capture(
            (sys.executable, "-c", "import os,json;print(json.dumps({name:os.environ[name] for name in "
             "('MSBUILDDISABLENODEREUSE','DOTNET_CLI_USE_MSBUILD_SERVER','UseSharedCompilation',"
             "'DOTNET_HOSTBUILDER__RELOADCONFIGONCHANGE')}))"),
            env={"MSBUILDDISABLENODEREUSE": "0", "DOTNET_CLI_USE_MSBUILD_SERVER": "1",
                 "UseSharedCompilation": "true", "DOTNET_HOSTBUILDER__RELOADCONFIGONCHANGE": "true"})
        self.assertEqual({"MSBUILDDISABLENODEREUSE": "1", "DOTNET_CLI_USE_MSBUILD_SERVER": "0",
                          "UseSharedCompilation": "false",
                          "DOTNET_HOSTBUILDER__RELOADCONFIGONCHANGE": "false"}, json.loads(result.stdout))

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
