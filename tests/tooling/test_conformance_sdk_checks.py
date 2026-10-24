import contextlib
import base64
import hashlib
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
import uuid
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_sdk_checks as checks

ENVIRONMENT = {
    "os": "linux", "osVersion": "test", "architecture": "x86_64",
    "sdk": "10.0.203", "runtime": "10.0.7", "nativeSqlite": "not-used",
    "filesystem": "ext4", "runnerImage": "none", "freeBytes": 100,
    "pragmas": {"journalMode": "none", "synchronous": 0, "foreignKeys": 0, "busyTimeout": 0},
}


class SdkDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / ".foundation" / ("sdk-diagnostic-test-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True, mode=0o700)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_transfer_measurement_admits_only_exact_parent_memory_and_settlement_proof(self):
        self.assertTrue(callable(getattr(checks, "admit_transfer_measurement", None)),
                        "Actual large transfers need parent kernel memory and settlement admission.")
        command = {
            "schemaVersion": 1, "sequence": 3, "childPid": 200, "childStartSha256": "a" * 64,
            "startedMs": 1000, "endedMs": 1200, "exitCode": 0, "diagnosticCode": "None",
            "groupState": "Exited", "scope": "transfer", "transfer": {
                "bytes": 268435456, "phase": "complete", "baselineRssBytes": 1048576,
                "osPeakRssBytes": 2097152, "sampledPeakRssBytes": 2097152, "samples": 2,
                "osPeakMethod": "proc-status", "baselineMs": 1050, "completedMs": 1150,
            },
        }
        checks.admit_transfer_measurement(command, 3, 268435456)
        for change in (
                {"sequence": True}, {"childPid": True}, {"childStartSha256": "0" * 64},
                {"scope": "ordinary"}, {"exitCode": True}, {"groupState": "Retained"},
                {"diagnosticCode": "DeadlineExceeded"}, {"startedMs": float("nan")}, {"startedMs": 10**400},
                {"endedMs": 2401001}, {"extra": "ignored"}, {"transfer": None},
                *({"transfer": command["transfer"] | item} for item in (
                    {"bytes": 4294967296}, {"bytes": True}, {"phase": "transferring"},
                    {"osPeakMethod": "declared"}, {"baselineRssBytes": 0},
                    {"osPeakRssBytes": 1048576 + 67108865}, {"sampledPeakRssBytes": 2097153},
                    {"sampledPeakRssBytes": 1}, {"samples": 1}, {"samples": True}, {"extra": "ignored"},
                    {"baselineMs": 999}, {"completedMs": 1201}, {"completedMs": 1049},
                    {"baselineMs": False}, {"completedMs": float("nan")}, {"baselineMs": 10**400}))):
            with self.subTest(change=change), self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_transfer_measurement(command | change, 3, 268435456)

    def test_measured_transfer_binds_actual_producer_pid_hash_runtime_and_unchanged_memory_receipt(self):
        for mutation in (None, "pid", "hash", "runtime", "pacing", "extra", "memory", "event"):
            root = self.directory / str(mutation)
            (root / "stores/artifact-transfers").mkdir(parents=True)
            (root / "proofs/artifact-transfers").mkdir(parents=True)
            run = SimpleNamespace(root=root, run_id=str(uuid.uuid4()), command_sequence=0, live_children=lambda: ())
            expected_hash = "a" * 64
            captured = []

            def command(args, **options):
                run.command_sequence += 1
                captured.append((args, options))
                measured = {
                    "bytes": 268435456, "phase": "complete", "baselineRssBytes": 1048576,
                    "osPeakRssBytes": 2097152, "sampledPeakRssBytes": 2097152, "samples": 2,
                    "osPeakMethod": "proc-status", "baselineMs": 1050, "completedMs": 1150,
                }
                if mutation == "memory":
                    measured["osPeakRssBytes"] = 2**40
                receipt = {
                    "schemaVersion": 1, "sequence": 1, "childPid": 200, "childStartSha256": "b" * 64,
                    "startedMs": 1000, "endedMs": 1200, "exitCode": 0, "diagnosticCode": "None",
                    "groupState": "Exited", "scope": "transfer", "transfer": measured,
                }
                (root / "proofs/transfer-command-0001.json").write_text(json.dumps(receipt))
                producer = {
                    "eventName": "complete", "provider": "local", "runId": run.run_id, "pid": 200,
                    "size": 268435456, "written": 268435456, "read": 268435456,
                    "expectedSha256": expected_hash, "sourceSha256": expected_hash, "sinkSha256": expected_hash,
                    "runtime": ".NET 10.0.7", "sourcePaced": True, "sinkPaced": True, "nonSeekable": True,
                    "generated": True, "independentExpectedHash": True, "warmupComplete": True,
                    "bufferBytes": 262144, "providerBufferLimit": 2097152, "slots": 1,
                }
                changes = {
                    "pid": {"pid": 201}, "hash": {"expectedSha256": "0" * 64},
                    "runtime": {"runtime": "foreign"}, "pacing": {"sinkPaced": False}, "extra": {"extra": True},
                }
                producer.update(changes.get(mutation, {}))
                (Path(args[3]) / "transfer-proof.json").write_text(json.dumps(producer))
                events = ({"event": "control", "code": "None", "value": 0},
                          {"event": "test", "code": "None", "value": 268435456},
                          {"event": "control", "code": "None", "value": 1})
                return SimpleNamespace(exit_code=0, events=events if mutation != "event" else events[:1])

            run.command = command
            with self.subTest(mutation=mutation):
                if mutation is not None:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError,
                                                "EvidenceIncomplete" if mutation == "event" else "ProofMismatch"):
                        checks.measured_artifact_transfer(
                            run, {"environment": ENVIRONMENT}, root / "runner.dll", "local", 268435456, expected_hash)
                    self.assertFalse((root / "proofs/artifact-transfers/transfer-local-268435456/proof.json").exists())
                    continue
                result = checks.measured_artifact_transfer(
                    run, {"environment": ENVIRONMENT}, root / "runner.dll", "local", 268435456, expected_hash)
                self.assertEqual(result["childStartSha256"], "b" * 64)
                self.assertEqual(captured[0][1]["measure_transfer_bytes"], 268435456)
                self.assertEqual(captured[0][1]["env"], {"HOARD_CONFORMANCE_SAFE_EVENTS": "1"})
                proof = json.loads((root / "proofs/artifact-transfers/transfer-local-268435456/proof.json").read_bytes())
                self.assertEqual(proof["osPeakRssBytes"], 2097152)
                self.assertEqual(proof["osPeakMethod"], "proc-status")
                self.assertEqual(proof["runId"], run.run_id)

    def test_actual_transfer_controller_requests_both_qualified_sizes_and_providers(self):
        self.assertTrue(callable(getattr(checks, "artifact_transfer_diagnostics", None)),
                        "Large transfer proof requires actual owned runner invocations for every frozen row.")
        root = self.directory
        candidate = root / "candidate"
        assembly = candidate / checks.ARTIFACT_TRANSFER / (
            "bin/Release/net10.0/Hoard.Fixtures.Artifacts.TransferRunner.dll")
        assembly.parent.mkdir(parents=True)
        assembly.write_bytes(b"transfer-controller-unit-double")
        (root / "stores").mkdir()
        (root / "proofs").mkdir()
        run = SimpleNamespace(root=root, run_id=str(uuid.uuid4()))
        inputs = {"runtimeAssemblies": {
            assembly.relative_to(root).as_posix(): hashlib.sha256(assembly.read_bytes()).hexdigest()}}
        with patch.object(checks, "verify_runtime_packages") as images, patch.object(
                checks, "measured_artifact_transfer", return_value={"proofSha256": "a" * 64}) as execute:
            result = checks.artifact_transfer_diagnostics(run, inputs, candidate)
            self.assertFalse(result["qualification"])
            self.assertEqual(result["inputsSha256"], checks.evidence.digest(inputs))
            self.assertEqual([call.args[3:5] for call in execute.call_args_list],
                             [("local", 268435456), ("local", 4294967296),
                              ("object", 268435456), ("object", 4294967296)])
            images.assert_called_once_with(assembly.parent, root / "feed/candidate",
                                           checks.ARTIFACT_RECOVERY_PACKAGES)
        with patch.object(checks, "verify_runtime_packages"), patch.object(checks, "measured_artifact_transfer") as execute:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.artifact_transfer_diagnostics(
                    run, {"runtimeAssemblies": {assembly.relative_to(root).as_posix(): "0" * 64}}, candidate)
            execute.assert_not_called()

    def test_noncooperative_observations_require_real_retention_and_matching_live_child(self):
        self.assertTrue(callable(getattr(checks, "admit_artifact_noncooperation", None)),
                        "Retained-work observations must be checked before their numeric barriers qualify.")
        run_id = str(uuid.uuid4())
        observation = {
            "eventName": "noncooperative", "phase": "contained", "pid": 200, "runId": run_id,
            "provider": "local", "scenario": "source", "durableCrashProof": False,
            "cleanup": "RetainedLiveOwnership", "callerCode": "CancelledBeforeCommit",
            "admissionCode": "CleanupIncomplete", "shutdownCode": "CleanupIncomplete",
            "enteredWorkers": 1, "workerPending": True, "borrowedStreamsIntact": True,
            "rootStillOwned": True, "readinessBlocked": True, "protectionRetained": False,
        }
        checks.admit_artifact_noncooperation(observation, "local", "source", "contained", 200, run_id)
        for change in (
                {"pid": 201}, {"pid": True}, {"runId": str(uuid.uuid4())}, {"provider": "object"},
                {"scenario": "native"}, {"phase": "inspected"}, {"durableCrashProof": True},
                {"cleanup": "Released"}, {"callerCode": "None"}, {"admissionCode": "None"},
                {"shutdownCode": "None"}, {"enteredWorkers": 2}, {"enteredWorkers": True},
                {"workerPending": False}, {"borrowedStreamsIntact": False}, {"rootStillOwned": False},
                {"readinessBlocked": False}, {"protectionRetained": True}, {"extra": True}):
            with self.subTest(change=change), self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_artifact_noncooperation(
                    observation | change, "local", "source", "contained", 200, run_id)
        for code in ("Uncertain", "DeadlineExceeded"):
            changed = observation | {"scenario": "native", "callerCode": code, "protectionRetained": True}
            checks.admit_artifact_noncooperation(changed, "local", "native", "contained", 200, run_id)
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_artifact_noncooperation(
                    changed | {"protectionRetained": False}, "local", "native", "contained", 200, run_id)

    def test_inspection_receipts_reject_missing_reordered_and_foreign_handshakes(self):
        command = {
            "schemaVersion": 1, "sequence": 1, "childPid": 200, "childStartSha256": "a" * 64,
            "startedMs": 1000, "endedMs": 1500, "exitCode": -9, "diagnosticCode": "None",
            "groupState": "Exited", "scope": "recovery", "barrier": {
                "value": 70, "observedMs": 1300, "signalMs": 1400,
                "inspection": {"value": 60, "observedMs": 1100, "requestMs": 1200},
            },
        }
        checks.admit_recovery_barrier(command, 1, 70, inspection=60)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
            checks.admit_recovery_barrier(command, 1, 70)
        for change in (
                {"value": 61}, {"value": True}, {"observedMs": 999}, {"requestMs": 1099},
                {"requestMs": 1301}, {"requestMs": None}, {"requestMs": float("nan")}, {"extra": True}):
            changed = command | {"barrier": command["barrier"] | {
                "inspection": command["barrier"]["inspection"] | change}}
            with self.subTest(change=change), self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_recovery_barrier(changed, 1, 70, inspection=60)

    def test_noncooperative_controller_requires_both_matching_producers_and_exact_parent_inspection(self):
        for mutation in (None, "foreign", "wrong-second", "handoff", "event"):
            root = self.directory / str(mutation)
            (root / "stores/artifact-noncooperation").mkdir(parents=True)
            (root / "proofs").mkdir()
            run = SimpleNamespace(root=root, command_sequence=0, live_children=lambda: ())
            invocations = []

            def command(args, **options):
                run.command_sequence += 1
                invocations.append((args, options))
                receipt = {
                    "schemaVersion": 1, "sequence": 1, "childPid": 200, "childStartSha256": "a" * 64,
                    "startedMs": 1000, "endedMs": 1500, "exitCode": -9, "diagnosticCode": "None",
                    "groupState": "Exited", "scope": "recovery", "barrier": {
                        "value": 70, "observedMs": 1300, "signalMs": 1400,
                        "inspection": {"value": 60, "observedMs": 1100, "requestMs": 1200},
                    },
                }
                if mutation == "handoff":
                    receipt["barrier"]["inspection"]["requestMs"] = None
                (root / "proofs/recovery-command-0001.json").write_text(json.dumps(receipt))
                for phase in ("contained", "inspected"):
                    producer = {
                        "eventName": "noncooperative", "phase": phase, "pid": 200, "runId": args[6],
                        "provider": "local", "scenario": "source", "durableCrashProof": False,
                        "cleanup": "RetainedLiveOwnership", "callerCode": "CancelledBeforeCommit",
                        "admissionCode": "CleanupIncomplete", "shutdownCode": "CleanupIncomplete",
                        "enteredWorkers": 1, "workerPending": True, "borrowedStreamsIntact": True,
                        "rootStillOwned": True, "readinessBlocked": True, "protectionRetained": False,
                    }
                    if mutation == "foreign":
                        producer["pid"] = 201
                    if mutation == "wrong-second" and phase == "inspected":
                        producer["runId"] = str(uuid.uuid4())
                    (Path(args[3]) / f"noncooperative-{phase}.json").write_text(json.dumps(producer))
                events = ({"event": "barrier", "code": "None", "value": 60},
                          {"event": "barrier", "code": "None", "value": 70})
                return SimpleNamespace(exit_code=-9, events=events if mutation != "event" else events[:1])

            run.command = command
            with self.subTest(mutation=mutation):
                if mutation is not None:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                        checks.artifact_noncooperation(run, root / "runner.dll", "local", "source")
                    continue
                observed = checks.artifact_noncooperation(run, root / "runner.dll", "local", "source")
                self.assertEqual(observed["childStartSha256"], "a" * 64)
                self.assertNotEqual(observed["containedSha256"], observed["inspectedSha256"])
                self.assertEqual(invocations[0][1]["inspect_at_barrier"], 60)
                self.assertEqual(invocations[0][1]["stop_at_barrier"], 70)
                self.assertEqual(invocations[0][1]["env"], {"HOARD_CONFORMANCE_SAFE_EVENTS": "1"})

    def test_noncooperative_controller_requests_source_sink_and_native_inspection_on_both_actual_providers(self):
        self.assertTrue(callable(getattr(checks, "artifact_noncooperation_diagnostics", None)),
                        "Artifact retained work requires actual owned inspection/termination on both providers.")
        root = self.directory
        candidate = root / "candidate"
        assembly = candidate / checks.ARTIFACT_RECOVERY / (
            "bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll")
        assembly.parent.mkdir(parents=True)
        assembly.write_bytes(b"noncooperative-controller-unit-double")
        (root / "stores").mkdir()
        (root / "proofs").mkdir()
        run = SimpleNamespace(root=root)
        inputs = {"runtimeAssemblies": {
            assembly.relative_to(root).as_posix(): hashlib.sha256(assembly.read_bytes()).hexdigest()}}
        with patch.object(checks, "verify_runtime_packages"), patch.object(
                checks, "artifact_noncooperation", return_value={"controllerSha256": "a" * 64}) as execute:
            result = checks.artifact_noncooperation_diagnostics(run, inputs, candidate)
            self.assertFalse(result["qualification"])
            self.assertEqual(result["inputsSha256"], checks.evidence.digest(inputs))
            self.assertEqual([call.args[2:4] for call in execute.call_args_list], [
                (provider, scenario) for provider in ("local", "object") for scenario in ("source", "destination", "native")])
        with patch.object(checks, "verify_runtime_packages"), patch.object(checks, "artifact_noncooperation") as execute:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.artifact_noncooperation_diagnostics(
                    run, {"runtimeAssemblies": {assembly.relative_to(root).as_posix(): "0" * 64}}, candidate)
            execute.assert_not_called()

    def test_metadata_recovery_barrier_requires_exact_observe_signal_exit_chain(self):
        self.assertTrue(callable(getattr(checks, "admit_recovery_barrier", None)),
                        "Real recovery needs an admitted parent-owned observation/signal/exit chain.")
        command = {
            "schemaVersion": 1, "sequence": 3, "childPid": 200,
            "childStartSha256": "a" * 64, "startedMs": 1000, "endedMs": 1200,
            "exitCode": -9, "diagnosticCode": "None", "groupState": "Exited", "scope": "recovery",
            "barrier": {"value": 10, "observedMs": 1050, "signalMs": 1100},
        }
        checks.admit_recovery_barrier(command, 3, 10)
        changes = (
            {"sequence": 4}, {"sequence": True}, {"schemaVersion": True},
            {"childPid": 0}, {"childPid": True}, {"childStartSha256": "0" * 64},
            {"exitCode": 0}, {"exitCode": True}, {"diagnosticCode": "DeadlineExceeded"},
            {"groupState": "Retained"}, {"scope": "ordinary"}, {"extra": "ignored"},
            {"startedMs": float("nan")}, {"endedMs": float("inf")}, {"endedMs": True},
            {"endedMs": 17001},
            *({"barrier": command["barrier"] | change} for change in (
                {"value": 11}, {"value": True}, {"extra": "ignored"},
                {"observedMs": None}, {"signalMs": None}, {"observedMs": 999},
                {"signalMs": 1049}, {"signalMs": 1201}, {"signalMs": float("nan")},
                {"observedMs": False})),
            {"barrier": None},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaisesRegex(
                    checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_recovery_barrier(command | change, 3, 10)

    def test_metadata_recovery_controller_drives_each_real_runner_mode_and_rejects_missing_proof(self):
        for mutation in (None, "normal-exit", "missing-event", "wrong-receipt"):
            root = self.directory / str(mutation)
            candidate = root / "candidate"
            assembly = candidate / checks.METADATA_RECOVERY / (
                "bin/Release/net10.0/Hoard.Fixtures.Metadata.CrashRunner.dll")
            assembly.parent.mkdir(parents=True)
            assembly.write_bytes(b"controller-unit-double")
            (root / "stores").mkdir()
            (root / "proofs").mkdir()
            invocations = []
            run = SimpleNamespace(root=root, command_sequence=0, live_children=lambda: ())

            def command(args, **options):
                run.command_sequence += 1
                invocations.append((args, options))
                value = options["stop_at_barrier"]
                receipt = {
                    "schemaVersion": 1, "sequence": run.command_sequence, "childPid": 200,
                    "childStartSha256": "a" * 64, "startedMs": 1000, "endedMs": 1200,
                    "exitCode": 0 if value is None or mutation == "normal-exit" else -9,
                    "diagnosticCode": "None", "groupState": "Exited", "scope": "recovery",
                }
                if value is not None:
                    receipt["barrier"] = {
                        "value": value + (mutation == "wrong-receipt"),
                        "observedMs": 1050, "signalMs": 1100,
                    }
                (root / f"proofs/recovery-command-{run.command_sequence:04}.json").write_text(json.dumps(receipt))
                events = () if mutation == "missing-event" else ({
                    "event": "test" if value is None else "barrier", "code": "None",
                    "value": 1 if value is None else value,
                },)
                return SimpleNamespace(exit_code=receipt["exitCode"], events=events)

            run.command = command
            inputs = {"runtimeAssemblies": {
                assembly.relative_to(root).as_posix(): hashlib.sha256(assembly.read_bytes()).hexdigest()}}
            with self.subTest(mutation=mutation), patch.object(
                    checks, "require_sqlite_environment"), patch.object(checks, "verify_runtime_packages"):
                if mutation is not None:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError,
                                                "EvidenceIncomplete" if mutation == "missing-event" else "ProofMismatch"):
                        checks.metadata_recovery_diagnostics(run, inputs, candidate)
                    self.assertFalse((root / "proofs/sqlite-recovery.json").exists())
                    continue
                result = checks.metadata_recovery_diagnostics(run, inputs, candidate)
                self.assertFalse(result["qualification"])
                self.assertEqual(result["inputsSha256"], checks.evidence.digest(inputs))
                self.assertEqual([item["barrierId"] for item in result["barriers"]],
                                 ["M0", "M1", "M2", "U0", "U1", "U2", "U3", "U4", "R0", "R1"])
                self.assertEqual(len(invocations), 31)
                self.assertEqual([options["stop_at_barrier"] for _, options in invocations
                                  if options["stop_at_barrier"] is not None],
                                 [0, 1, 2, 10, 11, 12, 13, 14, 20, 21])
                self.assertEqual(invocations[-1][0][2], "recovery-walkthrough")
                for args, options in invocations:
                    self.assertEqual(args[:2], ["dotnet", str(assembly)])
                    self.assertEqual(options["scope"], "recovery")
                    self.assertEqual(options["env"], {"HOARD_CONFORMANCE_SAFE_EVENTS": "1"})
                    self.assertEqual(Path(args[3]).parent, Path(args[4]))

    def test_local_recovery_uses_each_real_crash_boundary_without_borrowing_simulation_proof(self):
        self.assertTrue(callable(getattr(checks, "artifact_recovery_diagnostics", None)),
                        "Local needs actual owned crash/readback scopes, not metadata or simulation receipts.")
        root = self.directory
        candidate = root / "candidate"
        assembly = candidate / checks.ARTIFACT_RECOVERY / (
            "bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll")
        assembly.parent.mkdir(parents=True)
        assembly.write_bytes(b"local-controller-unit-double")
        (root / "stores").mkdir()
        (root / "proofs").mkdir()
        inputs = {"runtimeAssemblies": {
            assembly.relative_to(root).as_posix(): hashlib.sha256(assembly.read_bytes()).hexdigest()}}
        run = SimpleNamespace(root=root)
        with patch.object(checks, "verify_runtime_packages") as images, patch.object(
                checks, "recovery_command", return_value=("a" * 64, {"childStartSha256": "b" * 64})) as execute:
            result = checks.artifact_recovery_diagnostics(run, inputs, candidate)
            self.assertFalse(result["qualification"])
            self.assertEqual(result["inputsSha256"], checks.evidence.digest(inputs))
            self.assertEqual([item["barrierId"] for item in result["barriers"]],
                             ["B0", "B1", "B2", "B3", "D0", "D1"])
            self.assertEqual([item["value"] for item in result["barriers"]], list(range(40, 46)))
            self.assertEqual(execute.call_count, 12)
            for index, barrier in enumerate(("B0", "B1", "B2", "B3", "D0", "D1")):
                crash, recover = execute.call_args_list[index * 2:index * 2 + 2]
                self.assertEqual(crash.args[:2], (run, assembly))
                self.assertEqual(crash.args[2][0], "crash")
                self.assertEqual(recover.args[2][0], "recover")
                self.assertEqual(crash.args[2][1:], recover.args[2][1:])
                self.assertEqual(crash.args[2][3], barrier)
                self.assertEqual(str(uuid.UUID(crash.args[2][4])), crash.args[2][4])
                self.assertEqual(crash.kwargs["value"], 40 + index)
                self.assertNotIn("value", recover.kwargs)
            images.assert_called_once_with(
                assembly.parent, root / "feed/candidate", checks.ARTIFACT_RECOVERY_PACKAGES)
        with patch.object(checks, "verify_runtime_packages"), patch.object(checks, "recovery_command") as execute:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.artifact_recovery_diagnostics(
                    run, {"runtimeAssemblies": {assembly.relative_to(root).as_posix(): "0" * 64}}, candidate)
            execute.assert_not_called()

    def test_external_artifact_scope_preserves_frozen_rows_and_original_cross_process_ownership(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_external_scenarios", None)),
                        "All seventeen original external-proof wrappers need exact owned transport.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        prefixes = ("Hoard.Artifacts.Tests.ArtifactCrashTests.",
                    "Hoard.Artifacts.Tests.ArtifactNonCooperativeChildTests.",
                    "Hoard.Artifacts.Tests.ArtifactTransferProofTests.")
        admission = "Hoard.Artifacts.Tests.ArtifactAdmissionTests.Local_root_is_exclusively_owned_across_real_processes_not_a_lock_filename"
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefixes) or name == admission}
        scenario, = checks.original_artifact_external_scenarios()
        self.assertEqual(len(original), 16)
        self.assertEqual({name for name in scenario[1] if not name.startswith(
            "Hoard.Artifacts.Tests.ArtifactChildOutputTests.")}, original | {admission})
        self.assertEqual(len(scenario[1]), 21)
        candidate = self.directory / "candidate"
        runner = candidate / checks.ARTIFACT_RECOVERY / (
            "bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll")
        runner.parent.mkdir(parents=True)
        runner.write_bytes(b"external-wrapper-unit-double")
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {
                assembly.relative_to(self.directory).as_posix(): "a" * 64,
                runner.relative_to(self.directory).as_posix(): hashlib.sha256(runner.read_bytes()).hexdigest()},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.kwargs["artifact_runner"], runner)
            manifest = launch.call_args.args[2]
            self.assertEqual({item["testIdentity"] for item in manifest["expected"]}, set(scenario[1]))
        runner.write_bytes(b"changed")
        with patch.object(checks, "runtime_command") as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            launch.assert_not_called()

    def test_artifact_race_scope_preserves_all_frozen_parameters_and_named_length_mutations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_race_scenarios", None)),
                        "Shared artifact publication races need exact owned wrapper transport.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(
                        "Hoard.Artifacts.Tests.ArtifactPublicationRaceTests.")}
        self.assertEqual(len(original), 6)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_conflicting_length_assertion_rejects_repaired_forgery_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_race_scenarios()
        self.assertEqual(scenario, ("original-artifact-races", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_reconciliation_scope_preserves_frozen_parameters_and_foreign_receipt_mutations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_reconciliation_scenarios", None)),
                        "Shared artifact reconciliation needs exact owned wrapper transport.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(
                        "Hoard.Artifacts.Tests.ArtifactReconciliationTests.")}
        self.assertEqual(len(original), 8)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_receipt_retry_assertion_rejects_foreign_receipt_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_reconciliation_scenarios()
        self.assertEqual(scenario, ("original-artifact-reconciliation", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_visibility_scope_preserves_frozen_rows_and_premature_acknowledgment_mutation(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_visibility_scenarios", None)),
                        "Shared direct/listing visibility needs exact owned wrapper transport.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(
                        "Hoard.Artifacts.Tests.ArtifactVisibilityTests.")}
        self.assertEqual(len(original), 3)
        mutation = ("Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
                    "Shared_visibility_assertion_rejects_premature_acknowledgment_and_accepts_original_store")
        scenario, = checks.original_artifact_visibility_scenarios()
        self.assertEqual(scenario, ("original-artifact-visibility", tuple(sorted(original | {mutation})),
                                    "None", "Passed", 0, "None"))

    def test_artifact_history_scope_preserves_frozen_parameters_and_hidden_failure_mutations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_history_scenarios", None)),
                        "Shared history and budget checks need exact owned wrapper transport.")
        methods = {
            "Local_reclaimed_incarnations_remain_budgeted_until_expiry_without_removing_the_recreated_blob",
            "Reclaimed_identity_history_has_a_finite_budget_and_expiry_restores_new_digest_admission",
            "History_maintenance_bounds_examined_candidates_even_when_none_can_be_retired",
            "History_candidate_pages_resume_past_ineligible_entries_and_preserve_a_faulted_candidate",
            "Expired_ticket_history_restores_write_and_delete_capacity_without_losing_committed_or_removed_identity",
        }
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(", 1)[0] in {
                        f"Hoard.Artifacts.Tests.ArtifactBudgetTests.{method}" for method in methods}}
        self.assertEqual(len(original), 8)
        additional = {
            "Hoard.Artifacts.Tests.ArtifactBudgetTests."
            "Local_reclaimed_incarnations_remain_budgeted_until_expiry_without_removing_the_recreated_blob",
            *(
                "Hoard.Artifacts.Tests.ArtifactBudgetTests."
                "History_maintenance_bounds_examined_candidates_even_when_none_can_be_retired"
                f'(provider: "{provider}", kind: "{kind}")'
                for provider, kind in (
                    ("local", "tickets"), ("object", "tickets"), ("local", "dependencies"), ("object", "dependencies"),
                    ("local", "decisions"), ("object", "decisions"), ("local", "reclamation"))),
        }
        self.assertEqual(len(additional), 8)
        self.assertTrue(original.isdisjoint(additional))
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_history_resume_assertion_rejects_hidden_candidate_failure_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_history_scenarios()
        self.assertEqual(scenario, ("original-artifact-history", tuple(sorted(original | additional | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_ownership_scope_preserves_frozen_parameters_and_optimistic_cleanup_mutations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_ownership_scenarios", None)),
                        "Shared stream ownership needs exact owned wrapper transport.")
        methods = {
            "Hoard.Artifacts.Tests.ArtifactBudgetTests."
            "Producer_and_consumer_inactivity_deadlines_release_cooperative_work_without_closing_borrowed_streams",
            *(
                f"Hoard.Artifacts.Tests.ArtifactNonCooperationTests.{method}" for method in (
                    "Idle_read_expiry_fences_copy_without_touching_the_destination",
                    "Noncooperative_source_retains_bounded_ownership_and_blocks_admission_until_real_settlement",
                    "Noncooperative_destination_cannot_release_live_read_protection_via_close_or_dispose")),
        }
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(", 1)[0] in methods}
        self.assertEqual(len(original), 8)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_source_ownership_assertion_rejects_optimistic_cleanup_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_ownership_scenarios()
        self.assertEqual(scenario, ("original-artifact-ownership", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_local_artifact_session_scope_requires_unchanged_consumers_and_actual_ownership(self):
        factory = getattr(checks, "local_artifact_session_scenarios", None)
        self.assertTrue(callable(factory), "Owned Local sessions need exact package-only transport.")
        prefix = "Hoard.Fixtures.Conformance.Consumer.LocalArtifactSessionTests."
        identities = {
            prefix + f'Owned_local_projection_executes_unchanged_common_consumers(consumer: "{consumer}")'
            for consumer in ("publication", "expectations", "private-staging")}
        identities.update(prefix + method for method in (
            "All_typed_observation_points_can_be_registered_together_and_removed_without_overwrite",
            "Scoped_observation_cannot_overwrite_a_live_registration_or_remove_its_replacement",
            "Local_reopen_keeps_identity_authority_content_and_allocation_without_stale_disposal",
            "Physical_store_stop_cannot_release_a_live_authority_guard_or_erase_retained_observation",
            "Concurrent_disposers_join_one_attempt_and_the_same_actual_settlement",
            "Failed_initialization_retains_allocator_ownership_and_joins_actual_shutdown"))
        identities.update(prefix
            + "Released_boundary_stays_owned_through_actual_callback_and_reopen_or_disposal(reopen: " + value + ")"
            for value in ("False", "True"))
        for method, parameter in (
            ("Observer_failure_before_or_during_cleanup_remains_in_the_same_actual_settlement", "duringCleanup"),
            ("Concurrent_direct_stop_and_disposal_retry_reuse_the_pending_allocator_observation", "actualAllocator"),
        ):
            identities.update(prefix + method + f"({parameter}: {value})" for value in ("False", "True"))
        scenario, = factory()
        self.assertEqual(scenario, ("local-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"))

    def test_artifact_authority_ownership_scope_requires_all_live_settlement_cases(self):
        factory = getattr(checks, "artifact_authority_ownership_scenarios", None)
        self.assertTrue(callable(factory), "Owned artifact adapters need actual authority-quiescence transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactAuthorityOwnershipTests."
        identities = {
            prefix + "Shutdown_fence_joins_recognized_retained_and_queued_guards_before_reopen",
            prefix + "Shutdown_fence_joins_actual_noncooperating_reference_query_before_reopen",
            prefix + "Shutdown_fence_observes_canceled_waiter_without_losing_the_current_guard"}
        identities.update(prefix + "Released_operation_callback_remains_real_owned_work_until_final_settlement"
                          + f'(provider: "{provider}")' for provider in ("local", "object"))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-authority-ownership", tuple(sorted(identities)),
                                    "None", "Passed", 0, "None"))

    def test_object_artifact_session_scope_requires_fresh_epochs_and_actual_ownership(self):
        factory = getattr(checks, "object_artifact_session_scenarios", None)
        self.assertTrue(callable(factory), "Owned Object sessions need exact package-only transport.")
        prefix = "Hoard.Fixtures.Conformance.Consumer.ObjectArtifactSessionTests."
        identities = {
            prefix + f'Owned_object_projection_executes_unchanged_common_consumers(consumer: "{consumer}")'
            for consumer in ("publication", "expectations", "private-staging")}
        identities.update(prefix + method for method in (
            "All_typed_observations_register_together_and_stale_disposal_cannot_remove_a_replacement",
            "Object_restart_joins_old_authority_and_uses_fresh_epoch_authority_and_private_child",
            "Failed_replacement_keeps_the_original_as_cleanup_handle",
            "Failed_initialization_joins_actual_shutdown_without_erasing_foreign_content",
            "Cancellation_while_joining_old_authority_does_not_admit_a_replacement",
            "Cancellation_during_replacement_admission_retains_the_unpublished_generation",
            "Retained_authority_and_concurrent_disposers_retry_the_same_settlement"))
        for method, parameter in (
            ("Released_callback_stays_owned_until_restart_or_final_settlement", "restart"),
            ("Observer_failure_before_or_during_cleanup_faults_the_same_actual_settlement", "duringCleanup"),
            ("Direct_stop_and_disposal_retries_reuse_the_pending_allocator_observation", "actualAllocator"),
        ):
            identities.update(prefix + method + f"({parameter}: {value})" for value in ("False", "True"))
        scenario, = factory()
        self.assertEqual(scenario, ("object-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"))

    def test_artifact_observation_scope_requires_actual_independent_transition_cases(self):
        prefix = "Hoard.Artifacts.Tests.ArtifactObservationTests."
        identities = tuple(sorted(prefix + method + f'(provider: "{provider}")' for method in (
            "Persisted_receipt_boundary_exposes_the_same_actual_reconciled_receipt",
            "Failed_opened_read_callback_reclaims_real_stream_guard_and_single_transfer_slot",
            "Verified_reconciliation_callback_failure_keeps_actual_uncertain_publication_recoverable")
            for provider in ("local", "object")))
        scenario, = checks.artifact_observation_scenarios()
        self.assertEqual(scenario, ("original-artifact-observations", identities, "None", "Passed", 0, "None"))

    def test_configured_artifact_session_scope_requires_actual_limits_and_reference_queries(self):
        factory = getattr(checks, "configured_artifact_session_scenarios", None)
        self.assertTrue(callable(factory), "Configured artifact sessions need exact package-only transport.")
        prefix = "Hoard.Fixtures.Conformance.Consumer.ArtifactConfiguredSessionTests."
        identities = {
            prefix + method + f'(provider: "{provider}")' for method in (
                "Actual_configured_limits_survive_compatible_or_logical_reopen",
                "Current_reference_queries_fence_deletion_on_each_actual_generation",
                "Unavailable_reference_query_cannot_become_an_optimistic_zero_reference_decision")
            for provider in ("local", "object")}
        identities.add(prefix + "Invalid_reference_observations_cannot_admit_negative_counts_or_missing_available_revisions")
        identities.update(prefix
            + f'Timed_out_reference_query_stays_owned_through_reopen_or_final_settlement(provider: "{provider}", reopen: {reopen})'
            for provider in ("local", "object") for reopen in ("False", "True"))
        scenario, = factory()
        self.assertEqual(scenario, ("configured-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"))

    def test_payload_artifact_scope_requires_real_corruption_and_native_handle_ownership(self):
        factory = getattr(checks, "payload_artifact_session_scenarios", None)
        self.assertTrue(callable(factory), "Payload controls need exact owned native-work transport.")
        prefix = "Hoard.Fixtures.Conformance.Consumer.ArtifactPayloadSessionTests."
        identities = {
            prefix + f'Actual_payload_damage_invalidates_copy_and_later_open(provider: "{provider}", truncate: {truncate})'
            for provider in ("local", "object") for truncate in ("False", "True")}
        identities.update(prefix
            + f'Held_native_payload_handle_stays_owned_through_reopen_or_final_settlement(provider: "{provider}", reopen: {reopen})'
            for provider in ("local", "object") for reopen in ("False", "True"))
        identities.update(prefix + f'Foreign_incarnation_cannot_damage_current_payload(provider: "{provider}")'
                          for provider in ("local", "object"))
        identities.update(prefix + method + f'(provider: "{provider}")' for method in (
            "Failed_damage_observer_preserves_bytes_and_faults_final_settlement",
            "Removed_incarnation_cannot_damage_same_digest_replacement",
            "Stale_session_cannot_damage_reopened_payload",
            "Incompatible_open_read_handle_rejects_damage_without_changing_bytes")
            for provider in ("local", "object"))
        identities.update(prefix
            + f'Empty_payload_damage_is_explicit_and_never_false_success(provider: "{provider}", truncate: {truncate})'
            for provider in ("local", "object") for truncate in ("False", "True"))
        identities.add(prefix + "Object_old_epoch_cannot_damage_current_incarnation")
        scenario, = factory()
        self.assertEqual(scenario, ("payload-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"))

    def test_owned_artifact_scopes_discover_their_actual_distinct_assemblies(self):
        candidate = self.directory / "candidate"
        for scenario, folder, assembly_name in (
                (checks.artifact_authority_ownership_scenarios()[0], checks.ARTIFACT_TESTS, "Hoard.Artifacts.Tests.dll"),
                (checks.local_artifact_session_scenarios()[0], checks.ARTIFACT_CONSUMER,
                 "Hoard.Fixtures.Conformance.Consumer.dll"),
                (checks.object_artifact_session_scenarios()[0], checks.ARTIFACT_CONSUMER,
                 "Hoard.Fixtures.Conformance.Consumer.dll"),
                (checks.configured_artifact_session_scenarios()[0], checks.ARTIFACT_CONSUMER,
                 "Hoard.Fixtures.Conformance.Consumer.dll"),
                (checks.payload_artifact_session_scenarios()[0], checks.ARTIFACT_CONSUMER,
                 "Hoard.Fixtures.Conformance.Consumer.dll")):
            output = checks.ARTIFACT_TEST_OUTPUT if folder == checks.ARTIFACT_TESTS else checks.PACKAGE_TEST_OUTPUT
            assembly = candidate / folder / output / "Release/net10.0" / assembly_name
            inputs = {
                "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
                "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
            }
            with self.subTest(scope=scenario[0]), patch.object(
                    checks, "runtime_command", side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
                launch.assert_called_once()
                self.assertEqual(launch.call_args.args[1], assembly)
                self.assertEqual(launch.call_args.args[2]["purpose"], "discovery")
                self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, set(scenario[1]))

    def test_owned_artifact_consumer_builds_real_bindings_before_its_isolated_locked_runtime(self):
        run = SimpleNamespace(root=self.directory)
        candidate = self.directory / "candidate"
        config = self.directory / "NuGet.Config"
        feed = self.directory / "feed"
        with patch.object(checks, "prepare_project_lock", return_value=(None, None)) as prepare, \
                patch.object(checks, "build") as build, \
                patch.object(checks, "_original_wrapper_runtime") as runtime:
            checks.build_artifact_assertion_consumer(run, candidate, config, feed)
        projects = [
            candidate / f"tests/fixtures/conformance/Bindings/{name}/{name}.csproj"
            for name in ("Local", "ObjectSemantics")]
        projects.append(candidate / checks.ARTIFACT_CONSUMER / "Consumer.csproj")
        self.assertEqual([call.args[0] for call in prepare.call_args_list], projects)
        self.assertEqual([call.args[1] for call in build.call_args_list], projects)
        for call, name in zip(build.call_args_list[:2], ("Local", "ObjectSemantics")):
            self.assertEqual(call.kwargs["feed"], feed)
            self.assertEqual(call.kwargs["package_id"], "Hoard.Fixtures.Conformance.Bindings." + name)
        consumer = build.call_args_list[-1]
        self.assertEqual(consumer.args[3], "artifact-consumer-locked-replay")
        self.assertEqual(consumer.kwargs["properties"], ("-p:BaseOutputPath=bin/package-diagnostic/",))
        self.assertNotIn("feed", consumer.kwargs)
        runtime.assert_called_once_with(candidate, feed, checks.ARTIFACT_CONSUMER,
                                        checks.PACKAGE_TEST_OUTPUT, checks.ARTIFACT_CONSUMER_PACKAGES)

    def test_incomplete_or_foreign_owned_local_vectors_never_launch(self):
        for scenario in (*checks.local_artifact_session_scenarios(), *checks.object_artifact_session_scenarios(),
                         *checks.configured_artifact_session_scenarios(), *checks.payload_artifact_session_scenarios()):
            name, identities, *outcome = scenario
            for invalid in (identities[:-1], identities + ("Foreign.Test",),
                            ("Foreign.Test", *identities[1:])):
                with self.subTest(scope=name, vector=invalid), patch.object(checks, "runtime_command") as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                        checks.test_attempt(SimpleNamespace(root=self.directory), {}, self.directory / "candidate",
                                            (name, invalid, *outcome))
                    launch.assert_not_called()

    def test_artifact_configured_store_scope_preserves_all_frozen_host_selection_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_configured_store_scenarios", None)),
                        "Shared configured-store checks need exact owned host wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactCompositionTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefix)}
        self.assertEqual(len(original), 4)
        scenario, = checks.original_artifact_configured_store_scenarios()
        self.assertEqual(scenario, ("original-artifact-configured-store", tuple(sorted(original)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_object_cleanup_scope_preserves_all_frozen_residual_ownership_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_object_cleanup_scenarios", None)),
                        "Shared object cleanup checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactFailureTests."
        methods = (
            "Reused_object_receipt_survives_failed_unselected_assembly_cleanup",
            "Unselected_object_cleanup_retains_exact_ownership_and_blocks_retry_until_reclaimed")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if any(name == prefix + method or name.startswith(
                        prefix + method + "(") for method in methods)}
        self.assertEqual(len(original), 5)
        scenario, = checks.original_artifact_object_cleanup_scenarios()
        self.assertEqual(scenario, ("original-artifact-object-cleanup", tuple(sorted(original)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_prefix_cleanup_scope_preserves_all_frozen_reclamation_and_stop_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_prefix_cleanup_scenarios", None)),
                        "Shared prefix cleanup checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactFailureTests."
        methods = (
            "Committed_receipts_remain_reconcilable_while_exact_residual_staging_is_reclaimed",
            "Failed_prefix_reclamation_retains_ownership_until_exact_bounded_cleanup",
            "Stop_retains_failed_prefix_ownership_until_reclamation_can_settle")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if any(name.startswith(prefix + method + "(") for method in methods)}
        self.assertEqual(len(original), 6)
        scenario, = checks.original_artifact_prefix_cleanup_scenarios()
        self.assertEqual(scenario, ("original-artifact-prefix-cleanup", tuple(sorted(original)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_failure_scope_preserves_frozen_classification_and_reconciliation_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_failure_scenarios", None)),
                        "Shared failure checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactFailureTests."
        methods = (
            "Storage_failures_remain_distinct_and_sanitized_and_do_not_publish_partial_content",
            "Unexpected_fault_after_visibility_requires_exact_ticket_reconciliation")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if any(name.startswith(prefix + method + "(") for method in methods)}
        self.assertEqual(len(original), 4)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            + f'Shared_storage_failure_assertion_rejects_misclassified_denial_and_accepts_original_store(provider: "{provider}")'
            for provider in ("local", "object")}
        scenario, = checks.original_artifact_failure_scenarios()
        self.assertEqual(scenario, ("original-artifact-failure", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_lifecycle_scope_preserves_frozen_and_additional_shutdown_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_lifecycle_scenarios", None)),
                        "Shared lifecycle checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactNonCooperationTests."
        methods = (
            "Concurrent_close_waits_for_the_same_physical_guard_release_and_fences_new_copy",
            "Deadline_and_stop_return_while_a_native_io_boundary_holds_provider_state")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if any(name.startswith(prefix + method + "(") for method in methods)}
        self.assertEqual(len(original), 4)
        additional = {prefix + "Composed_shutdown_cannot_release_store_while_authority_retains_a_reference_query"
                      + f'(provider: "{provider}")' for provider in ("local", "object")}
        self.assertTrue(original.isdisjoint(additional))
        scenario, = checks.original_artifact_lifecycle_scenarios()
        self.assertEqual(scenario, ("original-artifact-lifecycle", tuple(sorted(original | additional)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_metadata_bridge_scope_preserves_frozen_and_additional_evidence_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_metadata_bridge_scenarios", None)),
                        "Shared metadata bridge checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactMetadataAuthorityTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefix)}
        self.assertEqual(len(original), 1)
        additional = {prefix + name for name in (
            "Bridge_binds_exact_evidence_and_keeps_recognized_shared_protection_until_metadata_settlement",
            "Foreign_malformed_expired_and_unrecognized_evidence_cannot_publish_metadata_or_leak_a_guard")}
        self.assertTrue(original.isdisjoint(additional))
        scenario, = checks.original_artifact_metadata_bridge_scenarios()
        self.assertEqual(scenario, ("original-artifact-metadata-bridge", tuple(sorted(original | additional)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_metadata_integration_scope_preserves_all_four_actual_combinations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_metadata_integration_scenarios", None)),
                        "Shared metadata/artifact integration checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactMetadataIntegrationTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefix)}
        self.assertEqual(len(original), 16)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_metadata_reference_assertion_rejects_hidden_denial_and_accepts_original_stores"
            f'(provider: "{provider}", metadataProvider: "{metadata}")'
            for provider in ("local", "object") for metadata in ("sqlite", "memory")}
        scenario, = checks.original_artifact_metadata_integration_scenarios()
        self.assertEqual(scenario, ("original-artifact-metadata-integration", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_capability_scope_preserves_frozen_gaps_and_existing_complete_profiles(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_capability_scenarios", None)),
                        "Shared capability checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactCapabilityTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefix)}
        self.assertEqual(len(original), 16)
        additional = {
            prefix + "Complete_capability_profile_accepts_configured_limits_and_keeps_ranges_optional"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        self.assertTrue(original.isdisjoint(additional))
        scenario, = checks.original_artifact_capability_scenarios()
        self.assertEqual(scenario, ("original-artifact-capability", tuple(sorted(original | additional)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_authority_scope_preserves_frozen_and_additional_recognized_handle_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_authority_scenarios", None)),
                        "Shared authority checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactAuthorityTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefix)}
        self.assertEqual(len(original), 3)
        additional = {prefix + name for name in (
            "Shared_admission_retention_and_independent_disposal_use_one_recognized_handle",
            "Missing_reference_authority_denies_deletion_not_shared_reads",
            "Noncooperative_reference_query_retains_exclusion_blocks_admission_and_settles_before_release")}
        self.assertTrue(original.isdisjoint(additional))
        mutation = prefix + "Shared_authority_assertion_rejects_repaired_copied_handle_and_accepts_original_authority"
        scenario, = checks.original_artifact_authority_scenarios()
        self.assertEqual(scenario, ("original-artifact-authority", tuple(sorted(original | additional | {mutation})),
                                    "None", "Passed", 0, "None"))

    def test_artifact_budget_scope_preserves_frozen_admission_cleanup_and_authority_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_budget_scenarios", None)),
                        "Shared finite-budget checks need exact owned wrapper transport.")
        methods = {
            "Failed_unclaimed_result_cleanup_blocks_admission_and_stop_until_exact_retry",
            "Cancelled_commit_before_decision_fences_the_ticket_and_cannot_publish_on_retry",
            "Full_transfer_queue_rejects_without_input_io_and_capacity_returns_after_release",
            "Cap_crossing_rejects_excess_before_append_and_capacity_recovers",
            "Total_deadline_includes_shared_authority_contention_before_publication",
            "Cooperative_cancellation_stops_input_without_disposing_borrowed_stream"}
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(", 1)[0].split(".")[-1] in methods}
        self.assertEqual(len(original), 16)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_cap_assertion_rejects_misclassified_limit_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_budget_scenarios()
        self.assertEqual(scenario, ("original-artifact-budget", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_handoff_scope_preserves_all_frozen_results_and_actual_discard_mutations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_handoff_scenarios", None)),
                        "Shared result-handoff checks need exact owned wrapper transport.")
        methods = {
            "Cancellation_after_resource_release_cannot_retain_an_already_settled_operation",
            "Cancellation_at_result_handoff_cannot_discard_a_reserved_ticket_or_live_read",
            "Cancellation_before_result_handoff_reclaims_the_unclaimed_ticket_or_read",
            "Undelivered_verified_staging_is_reclaimed_after_ownership_expiry"}
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(", 1)[0].split(".")[-1] in methods}
        self.assertEqual(len(original), 12)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_result_handoff_assertion_rejects_discarded_reservation_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_handoff_scenarios()
        self.assertEqual(scenario, ("original-artifact-handoff", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_cancellation_scope_preserves_frozen_and_additional_current_owner_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_cancellation_scenarios", None)),
                        "Shared cancellation/current-owner checks need exact owned wrapper transport.")
        method = ("Hoard.Artifacts.Tests.ArtifactBudgetTests."
                  "Cancellation_of_an_admitted_commit_cannot_fence_an_externally_renewed_owner")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(", 1)[0] == method}
        self.assertEqual(len(original), 2)
        additional = {
            "Hoard.Artifacts.Tests.ArtifactBudgetTests.Cancellation_after_progress_renewal_fences_the_same_admitted_owner"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        additional.update(
            "Hoard.Artifacts.Tests.ArtifactBudgetTests.Cancelled_invalid_or_stale_commit_cannot_fence_the_current_verified_handle"
            f'(provider: "{provider}", alteration: "{alteration}")'
            for provider in ("local", "object") for alteration in ("renewed", "completion", "handle"))
        self.assertEqual(len(additional), 8)
        self.assertTrue(original.isdisjoint(additional))
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_cancelled_descriptor_assertion_rejects_abandoned_current_owner_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_cancellation_scenarios()
        self.assertEqual(scenario, ("original-artifact-cancellation", tuple(sorted(original | additional | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_wrapper_scope_preserves_frozen_publication_parameters_and_actual_assembly(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_publication_scenarios", None)),
                        "Artifact publication needs exact source-owned wrapper transport.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"]
                    if name.startswith("Hoard.Artifacts.Tests.ArtifactPublicationTests.")}
        expected.update(
            'Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests.'
            'Shared_duplicate_assertion_rejects_substituted_source_and_accepts_original_store'
            f'(provider: "{provider}")' for provider in ("local", "object"))
        scenario, = checks.original_artifact_publication_scenarios()
        self.assertEqual(set(scenario[1]), expected)
        self.assertEqual(len(scenario[1]), 14)
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            launch.assert_called_once()
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertFalse(launch.call_args.kwargs)
            manifest = launch.call_args.args[2]
            self.assertEqual(manifest["purpose"], "discovery")
            self.assertEqual({item["testIdentity"] for item in manifest["expected"]}, expected)
            self.assertEqual({item["caseId"] for item in manifest["expected"]}, {scenario[0]})

    def test_artifact_wrapper_scope_cannot_drop_parameters_or_borrow_other_methods(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_publication_scenarios", None)),
                        "Artifact wrapper dispatch must reject shortened frozen scopes.")
        scenario, = checks.original_artifact_publication_scenarios()
        for changed in (
                (scenario[0], scenario[1][:-1], *scenario[2:]),
                ("original-artifact-provider-selected", *scenario[1:]),
                (scenario[0], (*scenario[1][:-1], "Hoard.Artifacts.Tests.Provider.Check"), *scenario[2:])):
            with self.subTest(scope=changed[0]), patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, self.directory, changed)
                launch.assert_not_called()

    def test_artifact_read_delete_scope_preserves_six_frozen_read_and_fencing_parameters(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_read_delete_scenarios", None)),
                        "Protected read and deletion wrappers need exact shared-consumer transport.")
        methods = {
            "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
            "Destination_failure_and_second_copy_never_return_verified_completion_or_dispose_borrowed_streams",
            "Hoard.Artifacts.Tests.ArtifactDeletionTests."
            "Exact_delete_receipts_and_recreation_never_remove_the_new_incarnation",
            "Hoard.Artifacts.Tests.ArtifactDeletionTests."
            "A_held_reader_finishes_before_exclusive_deletion_and_later_opens_cannot_enter",
        }
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(")[0] in methods}
        scenario, = checks.original_artifact_read_delete_scenarios()
        self.assertEqual(set(scenario[1]), expected)
        self.assertEqual(len(scenario[1]), 6)
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
        for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                        ("original-artifact-read-delete-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_quarantine_extraction_preserves_transitive_original_assertions_and_wrapper_ownership(self):
        sdk = ROOT / "tests/contracts/Hoard.Testing.Conformance/Artifacts/ArtifactEvidenceAssertions.cs"
        text = sdk.read_text()
        start = text.index("{", text.index("public static async Task QuarantineIsPermanentAsync("))
        body = text[start:text.index("\n    }", start) + 6]
        # Preserve the entire d7ef7cc^ helper after explicit interface/factory/token forwarding.
        self.assertEqual(hashlib.sha256("".join(body.split()).encode()).hexdigest(),
                         "9b54ea0c474c6d0aad0fb3616b338244e6e25add2c6c4f28ebf9d9bcd47677e2")
        for filename, method in (
            ("ArtifactEvidenceAssertions.cs", "QuarantineIsPermanentAsync"),
            ("ArtifactReadAssertions.cs", "DamagedReadAsync"),
            ("ArtifactReadAssertions.cs", "CommittedDetectionQuarantineAsync"),
            ("ArtifactPublicationAssertions.cs", "CorruptExistingContentAsync"),
        ):
            with self.subTest(method=method):
                text = (sdk.parent / filename).read_text()
                start = text.index("public static async Task " + method + "(")
                self.assertNotIn("reopen = null", text[start:text.index("{", start)])
        cases = ROOT / "tests/contracts/Hoard.Artifacts.Tests/Cases"
        for filename, method in (
            ("ArtifactReadVerificationTests.cs", "Every_committed_detection_path_quarantines_restored_bytes"),
            ("ArtifactReadVerificationTests.cs", "Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence"),
            ("ArtifactPublicationRaceTests.cs", "Corrupt_existing_bytes_are_not_overwritten_or_reused"),
        ):
            with self.subTest(method=method):
                text = (cases / filename).read_text()
                start = text.index("public async Task " + method + "(")
                body = text[start:text.index("\n    }", start)]
                self.assertIn("ArtifactEvidenceTests.QuarantineReopen(driver)", body)
        text = (cases / "ArtifactEvidenceTests.cs").read_text()
        for method in (
            "Local_failed_quarantine_persistence_retains_ownership_until_stop_retry_and_reopen",
            "Validation_first_corruption_cannot_be_revived_by_external_restoration",
        ):
            with self.subTest(method=method):
                start = text.index("public async Task " + method + "(")
                self.assertIn("QuarantineReopen(driver)", text[start:text.index("\n    }", start)])
        text = sdk.read_text()
        for method in ("FailedQuarantinePersistenceAsync", "ValidationFirstCorruptionAsync"):
            with self.subTest(method=method):
                start = text.index("public static async Task " + method + "(")
                body = "".join(text[start:text.index("\n    }", start)].split())
                self.assertIn("awaitQuarantineIsPermanentAsync(store,receipt,bytes,cancellationToken,reopen);", body)

    def test_recovery_pages_scope_requires_both_original_providers_and_every_cursor_and_generation_witness(self):
        factory = getattr(checks, "original_artifact_recovery_pages_scenarios", None)
        self.assertTrue(callable(factory), "Recovery extraction must retain both original providers.")
        prefix = "Hoard.Artifacts.Tests.ArtifactRecoveryTests."
        methods = {prefix + name for name in (
            "Sequential_recovery_retires_consumed_cursors_without_starving_independent_scans",
            "Changed_inventory_rejects_old_continuations_and_fresh_pages_cover_every_current_identity",
            "Expired_ownerless_reservations_release_capacity_without_replaying_old_tickets",
            "Cleanup_cannot_reopen_a_finalized_noncommit",
            "Expiry_cleanup_and_restage_fence_the_old_generation",
            "Recovery_pages_are_bounded_query_bound_and_not_deletion_authority",
        )}
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(")[0] in methods}
        expected.update(
            prefix + name + f'(provider: "{provider}")'
            for name in (
                "Expired_ownerless_reservations_release_capacity_without_replaying_old_tickets",
                "Cleanup_cannot_reopen_a_finalized_noncommit",
            ) for provider in ("local", "object"))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-recovery-pages", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
        for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-recovery-pages-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_validation_scope_requires_every_frozen_persistence_corruption_and_access_variant(self):
        factory = getattr(checks, "original_artifact_validation_scenarios", None)
        self.assertTrue(callable(factory), "Validation extraction must retain all original evidence fault variants.")
        prefix = "Hoard.Artifacts.Tests.ArtifactEvidenceTests."
        methods = {prefix + name for name in (
            "Local_failed_quarantine_persistence_retains_ownership_until_stop_retry_and_reopen",
            "Validation_first_corruption_cannot_be_revived_by_external_restoration",
            "Validation_access_failure_does_not_quarantine_intact_content",
        )}
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(")[0] in methods}
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-validation", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
        for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-validation-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_quarantine_reopen_scope_retains_every_frozen_variant_and_all_three_lost_denial_mutations(self):
        factory = getattr(checks, "original_artifact_quarantine_reopen_scenarios", None)
        self.assertTrue(callable(factory), "Quarantine extraction must retain transitive Local reopen assertions.")
        methods = {
            "Hoard.Artifacts.Tests.ArtifactReadVerificationTests.Every_committed_detection_path_quarantines_restored_bytes",
            "Hoard.Artifacts.Tests.ArtifactReadVerificationTests.Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence",
            "Hoard.Artifacts.Tests.ArtifactPublicationRaceTests.Corrupt_existing_bytes_are_not_overwritten_or_reused",
        }
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"]
                    if name.split("(")[0] in methods}
        expected.update(
            "Hoard.Artifacts.Tests.ArtifactEvidenceConsumerTests."
            "Shared_quarantine_consumers_reject_lost_reopen_denial_and_accept_original_store"
            f'(consumer: "{consumer}")'
            for consumer in ("damaged-read", "committed-detection", "corrupt-existing"))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-quarantine-reopen", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
        local_only = (scenario[0], tuple(name for name in scenario[1] if '(provider: "object"' not in name), *scenario[2:])
        with patch.object(checks, "original_artifact_quarantine_reopen_scenarios", return_value=(local_only,)):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, local_only)
                launch.assert_not_called()
        for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-quarantine-reopen-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_detection_scope_preserves_every_frozen_open_publication_and_reconciliation_variant(self):
        factory = getattr(checks, "original_artifact_detection_scenarios", None)
        self.assertTrue(callable(factory), "Committed-detection extraction needs all fixed inherited variants.")
        method = ("Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
                  "Every_committed_detection_path_quarantines_restored_bytes")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(method + "(")}
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-detection", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
        for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-detection-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_read_race_scope_requires_original_quarantine_revalidation_and_reconciliation(self):
        factory = getattr(checks, "original_artifact_read_race_scenarios", None)
        self.assertTrue(callable(factory), "Read-race extraction needs exact original observer/barrier transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
        expected = {prefix + "Local_reconciliation_cannot_finalize_after_overlapping_read_quarantines_the_incarnation"}
        expected.update(prefix + f'Admitted_open_rechecks_quarantine_before_delivering_a_session(provider: "{provider}")'
                        for provider in ("local", "object"))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-read-races", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
        for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-read-races-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_damaged_read_scope_preserves_frozen_parameters_and_revived_evidence_mutations(self):
        factory = getattr(checks, "original_artifact_damaged_read_scenarios", None)
        self.assertTrue(callable(factory), "Damaged-read extraction needs exact frozen and actual-validator mutation transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
        method = prefix + "Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence"
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(method + "(")}
        expected.update(
            "Hoard.Artifacts.Tests.ArtifactEvidenceConsumerTests."
            "Shared_damaged_read_assertion_rejects_revived_evidence_and_accepts_original_validator"
            f'(provider: "{provider}")' for provider in ("local", "object"))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-damaged-read", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
        for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-damaged-read-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_artifact_evidence_scope_preserves_quarantine_and_receipt_parameters_and_mutation_pair(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_evidence_scenarios", None)),
                        "Exact receipt and permanent quarantine consumers need actual wrapper transport.")
        read_methods = {
            "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
            "Every_committed_detection_path_quarantines_restored_bytes",
            "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
            "Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence",
        }
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(
                        "Hoard.Artifacts.Tests.ArtifactEvidenceTests.") or name.split("(")[0] in read_methods}
        expected.update(
            "Hoard.Artifacts.Tests.ArtifactEvidenceConsumerTests."
            "Shared_receipt_assertion_rejects_wrong_receipt_acceptance_and_accepts_original_validator"
            f'(provider: "{provider}")' for provider in ("local", "object"))
        scenario, = checks.original_artifact_evidence_scenarios()
        self.assertEqual(set(scenario[1]), expected)
        self.assertEqual(len(scenario[1]), 23)
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
        for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                        ("original-artifact-evidence-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_original_wrapper_scopes_use_every_frozen_parameter_and_the_original_assembly(self):
        self.assertTrue(callable(getattr(checks, "original_metadata_scenarios", None)),
                        "Original wrappers need source-owned exact discovery scopes.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        scenarios = checks.original_metadata_scenarios()
        self.assertEqual(len(scenarios), 2)
        for scenario, provider in zip(scenarios, ("memory", "sqlite"), strict=True):
            expected = {name for entry in frozen["entries"]
                        if entry["profileId"] == "metadata" and entry["bindingId"] == provider
                        for name in entry["runtimeTests"] if name.startswith("Hoard.Metadata.Tests.")}
            self.assertEqual(set(scenario[1]), expected)
            self.assertEqual(len(scenario[1]), len(expected))
            candidate = self.directory / "candidate"
            assembly = candidate / checks.METADATA_TESTS / checks.METADATA_TEST_OUTPUT / (
                "Release/net10.0/Hoard.Metadata.Tests.dll")
            inputs = {
                "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                "runtimeAssemblies": {
                    assembly.relative_to(self.directory).as_posix(): "a" * 64,
                    (assembly.parent / "runtimes/linux-x64/native/libe_sqlite3.so"
                     ).relative_to(self.directory).as_posix(): "c" * 64},
                "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
                "environment": {**ENVIRONMENT, "nativeSqlite": "3.50.4", "pragmas": {
                    "journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0}},
            }
            with self.subTest(provider=provider), patch.object(
                    checks, "runtime_command", side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
                launch.assert_called_once()
                self.assertEqual(launch.call_args.args[1], assembly)
                self.assertEqual(launch.call_args.kwargs["metadata_provider"], provider)
                manifest = launch.call_args.args[2]
                self.assertEqual(manifest["purpose"], "discovery")
                self.assertEqual({item["testIdentity"] for item in manifest["expected"]}, expected)

    def test_shortened_or_renamed_original_wrapper_scope_never_launches(self):
        self.assertTrue(callable(getattr(checks, "original_metadata_scenarios", None)),
                        "Original wrapper dispatch must reject shortened frozen scopes.")
        scenario = checks.original_metadata_scenarios()[0]
        for changed in (
                (scenario[0], scenario[1][:-1], *scenario[2:]),
                ("original-metadata-provider-selected", *scenario[1:]),
                (scenario[0], (*scenario[1][:-1], "Hoard.Metadata.Tests.Provider.Check"), *scenario[2:])):
            with self.subTest(scope=changed[0]), patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, self.directory, changed)
                launch.assert_not_called()

    def test_original_wrapper_logger_and_shared_runtime_must_match_the_actual_archives(self):
        logger = "Hoard.Conformance.TestLogger"
        variants = (
            (checks.METADATA_TESTS, checks.METADATA_TEST_OUTPUT, checks.METADATA_PACKAGES,
             checks.metadata_wrapper_runtime),
            (checks.ARTIFACT_TESTS, checks.ARTIFACT_TEST_OUTPUT, checks.ARTIFACT_PACKAGES,
             checks.artifact_wrapper_runtime),
        )
        for project, folder, packages, admit in variants:
            for mutation in (None, *packages, logger):
                candidate = self.directory / (Path(project).name + "-" + str(mutation))
                output = candidate / project / folder / "Release/net10.0"
                output.mkdir(parents=True)
                source = candidate / checks.LOGGER / f"bin/Release/net10.0/{logger}.dll"
                source.parent.mkdir(parents=True)
                source.write_bytes(b"logger" if mutation != logger else b"replaced")
                for package in packages:
                    (output / f"{package}.dll").write_bytes(
                        b"shared" if mutation != package else b"replaced")

                def identity(feed, package, version):
                    digest = hashlib.sha256(b"logger" if package == logger else b"shared").hexdigest()
                    return {"runtimeAssemblies": {f"lib/net10.0/{package}.dll": digest}}

                with self.subTest(project=project, mutation=mutation), patch.object(
                        checks.evidence, "package_identity", side_effect=identity) as observed:
                    if mutation is None:
                        admit(candidate, self.directory)
                        self.assertEqual((output / f"{logger}.dll").read_bytes(), b"logger")
                        self.assertEqual({call.args[1] for call in observed.call_args_list},
                                         {*packages, logger})
                    else:
                        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                            admit(candidate, self.directory)

    def test_external_artifact_settings_bind_the_actual_runner_current_run_and_parent_transfer_proofs(self):
        (self.directory / "stores").mkdir()
        (self.directory / "proofs/artifact-transfers").mkdir(parents=True)
        (self.directory / "runtime-owner.json").write_bytes(b"{}")
        runner = self.directory / "Hoard.Fixtures.Artifacts.CrashRunner.dll"
        runner.write_bytes(b"runner-unit-double")
        assembly = self.directory / "Hoard.Artifacts.Tests.dll"
        received = []
        run = SimpleNamespace(root=self.directory, command=lambda args, **options: (
            received.append(args) or SimpleNamespace(exit_code=0, events=())))
        scenario, = checks.original_artifact_external_scenarios()
        manifest = {
            "attemptId": str(uuid.uuid4()), "runId": str(uuid.uuid4()), "purpose": "discovery",
            "expected": [{"testIdentity": name, "fullyQualifiedName": name.split("(")[0]} for name in scenario[1]],
        }
        checks.runtime_command(run, assembly, manifest, artifact_runner=runner)
        settings = ET.fromstring(Path(next(arg.removeprefix("--Settings:") for arg in received[0]
                                          if arg.startswith("--Settings:"))).read_bytes())
        variables = {item.tag: item.text for item in settings.findall("./RunConfiguration/EnvironmentVariables/*")}
        self.assertEqual(variables["HOARD_ARTIFACT_CRASH_RUNNER"], str(runner))
        self.assertEqual(variables["HOARD_ARTIFACT_TRANSFER_PROOFS"], str(self.directory / "proofs/artifact-transfers"))
        self.assertEqual(variables["HOARD_ARTIFACT_RUN_ID"], manifest["runId"])
        self.assertEqual(Path(variables["HOARD_ARTIFACT_CRASH_PROOFS"]).parent, self.directory / "stores")
        self.assertNotIn("HOARD_CONFORMANCE_SAFE_EVENTS", variables)
        for target, expected in ((self.directory / "Foreign.dll", manifest["expected"]),
                                 (assembly, [{"testIdentity": "foreign", "fullyQualifiedName": "foreign"}])):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                checks.runtime_command(run, target, manifest | {"expected": expected}, artifact_runner=runner)
        self.assertEqual(len(received), 1)

    def test_original_provider_selection_is_closed_and_reaches_the_actual_test_host_settings(self):
        (self.directory / "stores").mkdir()
        (self.directory / "runtime-owner.json").write_bytes(b"{}")
        received = []

        def command(args, **kwargs):
            received.append(args)
            return SimpleNamespace(exit_code=0, events=())

        run = SimpleNamespace(root=self.directory, command=command)
        assembly = self.directory / "Hoard.Metadata.Tests.dll"
        for provider in ("memory", "sqlite"):
            manifest = {
                "attemptId": str(uuid.uuid4()), "purpose": "discovery",
                "expected": [{"testIdentity": "Hoard.Metadata.Tests.Original.Check",
                              "fullyQualifiedName": "Hoard.Metadata.Tests.Original.Check"}],
            }
            checks.runtime_command(run, assembly, manifest, metadata_provider=provider)
            settings_path = Path(next(arg.removeprefix("--Settings:") for arg in received[-1]
                                      if arg.startswith("--Settings:")))
            settings = ET.fromstring(settings_path.read_bytes())
            self.assertEqual(settings.findtext("./RunConfiguration/EnvironmentVariables/HOARD_METADATA_PROVIDER"),
                             provider)
            self.assertEqual(settings.find("./LoggerRunSettings/Loggers/Logger[@friendlyName='console']")
                             .get("enabled"), "False")
            self.assertIn("--ListTests", received[-1])
        for provider, target in (("provider-selected", assembly), ("sqlite", self.directory / "Foreign.dll")):
            with self.subTest(provider=provider, target=target.name):
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.runtime_command(run, target, manifest, metadata_provider=provider)
        self.assertEqual(len(received), 2)

    def test_each_diagnostic_discovers_its_actual_selected_assembly_before_execution(self):
        candidate = self.directory / "candidate"
        for scenario in checks.SCENARIOS:
            name, identities = scenario[:2]
            source = not all(identity.startswith(checks.SMOKE) for identity in identities)
            folder = checks.TESTS if source else checks.LOGGER + "/Smoke"
            output = (checks.PACKAGE_TEST_OUTPUT
                      if all(identity.startswith((checks.PACKAGE_TEST_PREFIX, *checks.BINDING_TEST_PREFIXES))
                             for identity in identities) else "bin")
            assembly = candidate / folder / output / "Release/net10.0" / (
                "Hoard.Conformance.Tests.dll" if source else "Smoke.dll")
            package = "Hoard.Testing.Conformance" if source or name == "origin-output" else "Hoard.Conformance.TestLogger"
            inputs = {
                "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
                "packages": [{"packageId": package, "sha256": "b" * 64}],
                "environment": {**ENVIRONMENT, "nativeSqlite": "3.50.4", "pragmas": {
                    "journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0}},
            }
            inputs["runtimeAssemblies"][(assembly.parent / "runtimes/linux-x64/native/libe_sqlite3.so"
                                         ).relative_to(self.directory).as_posix()] = "c" * 64
            with self.subTest(scenario=name), patch.object(
                    checks, "runtime_command", side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
                launch.assert_called_once()
                self.assertEqual(launch.call_args.args[1], assembly)
                self.assertEqual(launch.call_args.args[2]["purpose"], "discovery")
                self.assertEqual(launch.call_args.args[2]["packages"][0]["id"], package)

    def test_unsupported_platform_never_allocates_or_prepares(self):
        with patch.object(checks, "native_execution_supported", return_value=False), \
                patch.object(checks.OwnedRun, "allocate") as allocate, \
                patch.object(checks.baselines, "prepare") as prepare:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
                checks.execute(ROOT, self.directory / "run")
        allocate.assert_not_called()
        prepare.assert_not_called()

    def test_unknown_mixed_or_empty_diagnostic_names_never_fall_back_to_an_assembly(self):
        for identities in ((), ("Foreign.Provider.Check",),
                           (checks.SCENARIOS[0][1][0], checks.SMOKE + "Assertion"),
                           (checks.SCENARIOS[0][1][0],
                            "Hoard.Conformance.Tests.MemoryMechanismTests.Mixed")):
            scenario = ("unrecognized", identities, "None", "Passed", 0, "None")
            with self.subTest(identities=identities), patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, self.directory, scenario)
                launch.assert_not_called()

    def test_sqlite_diagnostics_require_actual_environment_and_fingerprinted_native_runtime(self):
        candidate = self.directory / "candidate"
        assembly = candidate / checks.TESTS / checks.PACKAGE_TEST_OUTPUT / "Release/net10.0/Hoard.Conformance.Tests.dll"
        native_path = (assembly.parent / "runtimes/linux-x64/native/libe_sqlite3.so").relative_to(self.directory).as_posix()
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64, native_path: "c" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
            "environment": {**ENVIRONMENT, "nativeSqlite": "3.50.4", "pragmas": {
                "journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0}},
        }
        identity = "Hoard.Fixtures.Conformance.Consumer.SqliteBindingTests.Reopen_transfers_one_directory_without_settling_it_under_an_old_worker"
        scenario = ("sqlite-ownership", (identity,), "None", "Passed", 0, "None")
        for mutation in ("missing-environment", "not-used", "wrong-pragmas", "missing-native"):
            changed = json.loads(json.dumps(inputs))
            if mutation == "missing-environment":
                changed.pop("environment")
            elif mutation == "not-used":
                changed["environment"]["nativeSqlite"] = "not-used"
            elif mutation == "wrong-pragmas":
                changed["environment"]["pragmas"]["synchronous"] = 1
            else:
                changed["runtimeAssemblies"].pop(native_path)
            with self.subTest(mutation=mutation), patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "EvidenceIncomplete"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), changed, candidate, scenario)
                launch.assert_not_called()
        with patch.object(checks, "runtime_command", side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual(launch.call_args.args[2]["purpose"], "discovery")

    def test_package_consumer_lock_preparation_is_exact_and_preserves_source_graph(self):
        candidate = self.directory / "candidate"
        original = candidate / checks.TESTS / "PackageAcceptance/packages.lock.json"
        original.parent.mkdir(parents=True)
        feed = self.directory / "feed"
        feed.mkdir()
        local = ("Hoard.Abstractions", "Hoard.Testing.Conformance",
                 "Hoard.Conformance.TestLogger", "Hoard.Fixtures.Metadata.Memory",
                 "Hoard.Fixtures.Conformance.Bindings.Memory", "Hoard.Fixtures.Metadata.Sqlite",
                 "Hoard.Fixtures.Conformance.Bindings.Sqlite")
        dependencies = {"xunit": {"resolved": "2.9.3", "contentHash": "unchanged"}}
        for package in local:
            (feed / (package + ".0.1.0.nupkg")).write_bytes(package.encode())
            dependencies[package] = {"resolved": "0.1.0", "contentHash": "old"}
        raw = json.dumps({"version": 2, "dependencies": {"net10.0": dependencies}}).encode()
        original.write_bytes(raw)
        lock, receipt = checks.prepare_package_consumer_lock(candidate, feed)
        self.assertEqual(original.read_bytes(), raw)
        self.assertEqual(json.loads(lock.read_bytes())["dependencies"]["net10.0"]["xunit"],
                         dependencies["xunit"])
        self.assertEqual(set(receipt["packages"]), {name + ".0.1.0.nupkg" for name in local})
        checks.verify_package_consumer_lock(candidate, feed, lock, receipt)
        (feed / "Hoard.Testing.Conformance.0.1.0.nupkg").write_bytes(b"changed")
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            checks.verify_package_consumer_lock(candidate, feed, lock, receipt)

    def test_package_consumer_lock_rejects_foreign_inventory_without_publishing(self):
        candidate = self.directory / "candidate"
        original = candidate / checks.TESTS / "PackageAcceptance/packages.lock.json"
        original.parent.mkdir(parents=True)
        raw = b'{"version":2,"dependencies":{"net10.0":{"xunit":{"resolved":"2.9.3"}}}}'
        original.write_bytes(raw)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            checks.prepare_package_consumer_lock(candidate, self.directory)
        self.assertEqual(original.read_bytes(), raw)
        self.assertFalse((original.parents[1] / "obj/F07.consumer.packages.lock.json").exists())

    def test_original_wrapper_preparation_preserves_each_existing_package_graph(self):
        feed = self.directory / "feed"
        feed.mkdir()
        for package in checks.INPUT_PACKAGES:
            (feed / f"{package}.0.1.0.nupkg").write_bytes(package.encode())
        for project, packages in (
                (checks.METADATA_TESTS, checks.METADATA_PACKAGES),
                (checks.ARTIFACT_TESTS, checks.ARTIFACT_PACKAGES)):
            with self.subTest(project=project):
                candidate = self.directory / Path(project).name
                original = candidate / project / "PackageAcceptance/packages.lock.json"
                original.parent.mkdir(parents=True)
                dependencies = {"xunit": {"resolved": "2.9.3", "contentHash": "unchanged"}}
                dependencies.update({package: {"resolved": "0.1.0", "contentHash": "old"} for package in packages})
                raw = json.dumps({"version": 2, "dependencies": {"net10.0": dependencies}}).encode()
                original.write_bytes(raw)
                alternate, receipt = checks.prepare_package_consumer_lock(
                    candidate, feed, project=project, local_packages=packages)
                self.assertEqual(original.read_bytes(), raw)
                self.assertEqual(alternate.parent, candidate / project / "obj")
                prepared = json.loads(alternate.read_bytes())["dependencies"]["net10.0"]
                self.assertEqual(set(prepared), set(dependencies))
                self.assertEqual(prepared["xunit"], dependencies["xunit"])
                self.assertEqual(set(receipt["packages"]), {f"{package}.0.1.0.nupkg" for package in packages})
                checks.verify_package_consumer_lock(candidate, feed, alternate, receipt, project=project)
                self.assertNotIn("Hoard.Conformance.TestLogger", prepared)

    def test_sqlite_environment_requires_actual_configuration_and_locked_native_archive_bytes(self):
        runtime = self.directory / "runtime"
        native = runtime / "runtimes/linux-x64/native/libe_sqlite3.so"
        native.parent.mkdir(parents=True)
        native.write_bytes(b"actual-native")
        package = self.directory / "sqlite.nupkg"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr(native.relative_to(runtime).as_posix(), native.read_bytes())
        locked = {"resolved": "2.1.13", "contentHash": base64.b64encode(
            hashlib.sha512(package.read_bytes()).digest()).decode()}
        metadata = package.parent / ".nupkg.metadata"
        metadata.write_text(json.dumps({"version": 2, "contentHash": locked["contentHash"],
                                       "source": "https://api.nuget.org/v3/index.json"}))
        package.with_suffix(".nupkg.sha512").write_text(locked["contentHash"])
        platform = {"architecture": "x86_64", "runtime": "10.0.7"}
        observation = {
            "schemaVersion": 1, "runtime": "10.0.7", "architecture": "X64",
            "nativeSqlite": "3.50.4", "pragmas": {
                "journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0},
            "nativeLibrary": {"path": native.relative_to(runtime).as_posix(),
                              "sha256": hashlib.sha256(native.read_bytes()).hexdigest()},
        }
        before = json.loads(json.dumps(observation))
        receipt = checks.admit_sqlite_environment(observation, platform, runtime, package, locked)
        self.assertEqual(observation, before)
        self.assertEqual(receipt["nativeSha256"], observation["nativeLibrary"]["sha256"])
        self.assertEqual(receipt["packageSha256"], hashlib.sha256(package.read_bytes()).hexdigest())
        normalized = base64.b64encode(b"n" * 64).decode()
        locked["contentHash"] = normalized
        metadata.write_text(json.dumps({"version": 2, "contentHash": normalized,
                                       "source": "https://api.nuget.org/v3/index.json"}))
        receipt = checks.admit_sqlite_environment(observation, platform, runtime, package, locked)
        self.assertEqual(receipt["nugetSha512"], (b"n" * 64).hex())
        self.assertEqual(receipt["archiveSha512"], hashlib.sha512(package.read_bytes()).hexdigest())
        restored_metadata = metadata.read_bytes()
        for field, invalid in (("contentHash", "foreign"), ("source", "https://example.invalid/v3/index.json")):
            changed = json.loads(restored_metadata)
            changed[field] = invalid
            metadata.write_text(json.dumps(changed))
            with self.subTest(cache_field=field), self.assertRaises(checks.evidence.ConformanceError):
                checks.admit_sqlite_environment(observation, platform, runtime, package, locked)
            metadata.write_bytes(restored_metadata)
        cached_hash = package.with_suffix(".nupkg.sha512")
        restored_hash = cached_hash.read_bytes()
        cached_hash.write_text(base64.b64encode(b"z" * 64).decode())
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.admit_sqlite_environment(observation, platform, runtime, package, locked)
        cached_hash.write_bytes(restored_hash)
        for mutate in (
                lambda value: value.update(nativeSqlite="not-used"),
                lambda value: value.update(runtime="10.0.8"),
                lambda value: value.update(architecture="Arm64"),
                lambda value: value["pragmas"].update(synchronous=1),
                lambda value: value["nativeLibrary"].update(path="../outside.so"),
                lambda value: value["nativeLibrary"].update(sha256="a" * 64),
                lambda value: value.update(extra=True)):
            with self.subTest(mutation=mutate):
                changed = json.loads(json.dumps(before))
                mutate(changed)
                with self.assertRaises(checks.evidence.ConformanceError):
                    checks.admit_sqlite_environment(changed, platform, runtime, package, locked)
        native.write_bytes(b"substituted-native")
        observation["nativeLibrary"]["sha256"] = hashlib.sha256(native.read_bytes()).hexdigest()
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.admit_sqlite_environment(observation, platform, runtime, package, locked)
        native.write_bytes(b"actual-native")
        locked["contentHash"] = base64.b64encode(b"x" * 64).decode()
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.admit_sqlite_environment(before, platform, runtime, package, locked)

    def test_native_noncooperation_requires_actual_retention_and_controller_confirmed_exit(self):
        observed = {
            "schemaVersion": 1, "inputsSha256": "a" * 64, "childPid": 123,
            "boundaryObservations": 1, "guards": [1, 1, 1],
            "commitCode": "Uncertain", "commitPhase": "Commit", "commitRetry": "Reconcile",
            "ticketSha256": "b" * 64, "failureTicketSha256": "b" * 64,
            "disposeCode": "CleanupIncomplete", "incompleteCleanups": 1,
            "admissionCode": "Disposed", "settlementCompleted": False, "cleanupState": "Retained",
            "resourceIds": ["resource-a"],
            "ledgerStates": ["Allocated", "Active", "Settling", "Retained"],
        }
        command = {
            "schemaVersion": 1, "sequence": 10, "childPid": 123, "childStartSha256": "c" * 64,
            "startedMs": 1000, "endedMs": 46000, "exitCode": -9,
            "diagnosticCode": "DeadlineExceeded", "groupState": "Exited", "scope": "recovery",
        }
        before = json.loads(json.dumps((observed, command)))
        checks.admit_sqlite_noncooperation(observed, command, "a" * 64)
        self.assertEqual(json.loads(json.dumps((observed, command))), before)
        for field, invalid in (
                ("schemaVersion", True), ("inputsSha256", "d" * 64), ("childPid", 124),
                ("boundaryObservations", 0), ("guards", [1, 1, 0]), ("guards", [True, 1, 1]),
                ("commitCode", "DeadlineExceeded"), ("commitPhase", "Read"), ("commitRetry", "Retry"),
                ("failureTicketSha256", "e" * 64), ("disposeCode", "None"), ("incompleteCleanups", 0),
                ("admissionCode", "Unavailable"), ("settlementCompleted", True),
                ("cleanupState", "Released"), ("resourceIds", []),
                ("resourceIds", ["../foreign"]), ("ledgerStates", ["Released"]), ("foreign", 1)):
            changed = {**observed, field: invalid}
            with self.subTest(producer=field, invalid=invalid), self.assertRaisesRegex(
                    checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_sqlite_noncooperation(changed, command, "a" * 64)
        for field, invalid in (
                ("schemaVersion", True), ("childPid", 124), ("childStartSha256", "0" * 64),
                ("sequence", 0), ("startedMs", True), ("endedMs", 999), ("exitCode", 0),
                ("diagnosticCode", "None"), ("groupState", "Retained"), ("scope", "ordinary"),
                ("foreign", 1)):
            changed = {**command, field: invalid}
            with self.subTest(controller=field), self.assertRaisesRegex(
                    checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_sqlite_noncooperation(observed, changed, "a" * 64)

    def test_native_noncooperation_cannot_turn_an_exit_setup_failure_or_live_child_into_success(self):
        for outcome, expected in (
                ("normal-exit", "EvidenceIncomplete"), ("CommandFailed", "CommandFailed"),
                ("missing-proof", "OutputLimitExceeded"), ("live-child", "CleanupIncomplete")):
            root = self.directory / outcome
            (root / "stores").mkdir(parents=True)
            command = unittest.mock.Mock(return_value=SimpleNamespace(exit_code=0))
            if outcome != "normal-exit":
                command.side_effect = checks.evidence.ConformanceError(
                    "CommandFailed" if outcome == "CommandFailed" else "DeadlineExceeded")
            run = SimpleNamespace(root=root, command_sequence=4, command=command,
                                  live_children=lambda: outcome == "live-child")
            with self.subTest(outcome=outcome), patch.object(
                    checks, "require_sqlite_environment") as admission, patch.object(
                    checks.evidence, "package_identity", return_value={"sha256": "f" * 64}):
                with self.assertRaisesRegex(checks.evidence.ConformanceError, expected):
                    checks.sqlite_noncooperation(run, {"bound": "input"}, root / "candidate")
                admission.assert_called_once()
                self.assertEqual(command.call_args.kwargs["scope"], "recovery")
                self.assertEqual(command.call_args.kwargs["timeout"], 45)
                self.assertEqual(command.call_args.args[0][-1], checks.evidence.digest({"bound": "input"}))

    def test_preparation_and_seal_verification_precede_candidate_snapshot(self):
        calls = []
        seal = self.directory / "baselines.json"
        seal.write_bytes(b"sealed")
        run = SimpleNamespace(root=self.directory, deadline=float("inf"), state="Allocated",
                              live_children=lambda: False)
        run.transition = lambda state: setattr(run, "state", state)

        def prepare(*args, **kwargs):
            self.assertEqual(kwargs, {"prepare_local_archives": True})
            self.assertTrue((run.root / "cache/.local/share").is_dir())
            self.assertEqual((run.root / "cache/.local").stat().st_mode & 0o777, 0o700)
            calls.append("prepare")
            return seal

        def verify(*args):
            calls.append("verify")
            return {}

        def snapshot(*args):
            calls.append("snapshot")
            raise checks.evidence.ConformanceError("InputChanged")

        with contextlib.redirect_stdout(io.StringIO()) as output, \
                patch.object(checks, "native_execution_supported", return_value=True), \
                patch.object(checks.OwnedRun, "allocate", return_value=run), \
                patch.object(checks.baselines, "prepare", side_effect=prepare), \
                patch.object(checks.baselines, "verify_prepared_baselines", side_effect=verify), \
                patch.object(checks, "snapshot", side_effect=snapshot), \
                patch.object(checks, "build") as build:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.execute(ROOT, self.directory / "run")
        self.assertEqual(calls, ["prepare", "verify", "snapshot"])
        build.assert_not_called()
        self.assertEqual(run.state, "Settling")
        self.assertEqual(json.loads(output.getvalue()),
                         {"qualification": False, "phase": "baseline-preparation"})

    def test_invalid_baseline_seal_never_snapshots_or_compiles_candidate(self):
        seal = self.directory / "baselines.json"
        seal.write_bytes(b"sealed")
        run = SimpleNamespace(root=self.directory, deadline=float("inf"), state="Active",
                              live_children=lambda: True)
        run.transition = lambda state: setattr(run, "state", state)
        with contextlib.redirect_stdout(io.StringIO()) as output, \
                patch.object(checks, "native_execution_supported", return_value=True), \
                patch.object(checks.OwnedRun, "allocate", return_value=run), \
                patch.object(checks.baselines, "prepare", return_value=seal), \
                patch.object(checks.baselines, "verify_prepared_baselines",
                             side_effect=checks.evidence.ConformanceError("InputChanged")), \
                patch.object(checks, "snapshot") as snapshot, patch.object(checks, "build") as build:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.execute(ROOT, self.directory / "run")
        snapshot.assert_not_called()
        build.assert_not_called()
        self.assertEqual(run.state, "Retained")
        self.assertTrue(seal.exists())
        self.assertEqual(json.loads(output.getvalue()),
                         {"qualification": False, "phase": "baseline-preparation"})

    def test_snapshot_preserves_solution_ancestry_but_rejects_symlinks(self):
        with tempfile.TemporaryDirectory(prefix="hoard-sdk-snapshot-") as temporary:
            parent = Path(temporary).resolve()
            parent.chmod(0o700)
            repository = parent / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
            (repository / "Hoard.slnx").write_text("<Solution/>")
            (repository / "src").mkdir()
            (repository / "src/file.cs").write_text("source")
            contract = "specs/004-module-discovery/contracts/openapi.json"
            (repository / contract).parent.mkdir(parents=True)
            (repository / contract).write_text('{"openapi":"3.1.0"}')
            inventory = "tests/fixtures/conformance/baselines/inventory.json"
            (repository / inventory).parent.mkdir(parents=True)
            (repository / inventory).write_text('{"entries":[]}')
            run = checks.OwnedRun.allocate(parent / "run", repository, profile="harness")
            candidate, sources = checks.snapshot(repository, run)
            self.assertEqual((candidate / "Hoard.slnx").read_bytes(), (repository / "Hoard.slnx").read_bytes())
            self.assertIn(contract, sources)
            self.assertEqual((candidate / contract).read_bytes(), (repository / contract).read_bytes())
            self.assertEqual(sources[inventory], hashlib.sha256((repository / inventory).read_bytes()).hexdigest())
            self.assertEqual((candidate / inventory).read_bytes(), (repository / inventory).read_bytes())
            self.assertEqual(sources["src/file.cs"], hashlib.sha256(b"source").hexdigest())
            self.assertEqual((candidate / "src/file.cs").stat().st_mode & 0o222, 0)
            run.transition("Settling")
            run.release()
            (repository / "src/linked.cs").symlink_to(repository / "src/file.cs")
            second = checks.OwnedRun.allocate(parent / "second", repository, profile="harness")
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.snapshot(repository, second)
            second.transition("Settling")
            second.release()

    def test_package_lock_preparation_preserves_source_and_rebinds_only_three_local_archives(self):
        feed = self.directory / "feed"
        feed.mkdir()
        dependencies = {"xunit": {"resolved": "2.9.3", "contentHash": "unchanged"}}
        for name in ("Hoard.Abstractions", "Hoard.Testing.Conformance", "Hoard.Conformance.TestLogger"):
            dependencies[name] = {"resolved": "0.1.0", "contentHash": "old", "dependencies": {"xunit": "2.9.3"}}
            (feed / f"{name}.0.1.0.nupkg").write_bytes(name.encode())
        original = {"version": 2, "dependencies": {"net10.0": dependencies}}
        lock = self.directory / "packages.lock.json"
        lock.write_text(json.dumps(original))
        project = self.directory / "Smoke.csproj"
        project.write_text("<Project/>")
        alternate, record = checks.prepare_smoke_lock(project, self.directory, feed)
        self.assertEqual(json.loads(lock.read_bytes()), original)
        self.assertFalse(record["qualification"])
        checks.verify_project_lock(record, self.directory, feed)
        replayed = json.loads(alternate.read_bytes())
        for name, dependency in replayed["dependencies"]["net10.0"].items():
            if name.startswith("Hoard."):
                self.assertNotEqual(dependency["contentHash"], "old")
                dependency["contentHash"] = "old"
        self.assertEqual(replayed, original)
        (feed / "Hoard.Conformance.TestLogger.0.1.0.nupkg").unlink()
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
            checks.prepare_smoke_lock(project, self.directory, feed)

    def test_smoke_locked_replay_uses_the_explicit_prepared_lock_for_restore_and_build(self):
        received = []
        project = self.directory / "Smoke.csproj"
        lock = self.directory / "obj/F07.preparation.packages.lock.json"
        with patch.object(checks.baselines, "_command", side_effect=lambda run, args, **kwargs: received.append(args)):
            checks.build(object(), project, self.directory / "NuGet.Config", "locked-replay", lock=lock)
        self.assertEqual([args[1] for args in received], ["restore", "build"])
        self.assertTrue(all("-p:NuGetLockFilePath=" + str(lock) in args for args in received))
        self.assertIn("--locked-mode", received[0])
        self.assertIn("--no-restore", received[1])

    def test_package_consumer_replay_is_locked_and_keeps_source_output_separate(self):
        received = []
        project = self.directory / "Tests.csproj"
        lock = self.directory / "obj/F07.consumer.packages.lock.json"
        with patch.object(checks.baselines, "_command",
                          side_effect=lambda run, args, **kwargs: received.append((args, kwargs))):
            checks.build(object(), project, self.directory / "NuGet.Config", "consumer-locked-replay",
                         lock=lock, properties=("-p:ConformancePackageAcceptance=true",
                                                "-p:BaseOutputPath=" + checks.PACKAGE_TEST_OUTPUT + "/"))
        self.assertEqual([args[1] for args, _ in received], ["restore", "build"])
        self.assertIn("--locked-mode", received[0][0])
        for args, kwargs in received:
            self.assertIn("-p:ConformancePackageAcceptance=true", args)
            self.assertIn("-p:BaseOutputPath=bin/package-diagnostic/", args)
            self.assertIn("-p:NuGetLockFilePath=" + str(lock), args)
            self.assertNotIn("--force-evaluate", args)
            self.assertEqual(kwargs["cache_id"], "consumer-locked-replay")

    def test_pack_uses_the_explicit_package_identity_not_the_fixture_project_filename(self):
        feed = self.directory / "feed"
        with patch.object(checks.baselines, "_command"), \
                patch.object(checks, "canonicalize_acceptance_archive") as canonicalize:
            checks.build(object(), self.directory / "Memory.csproj", self.directory / "NuGet.Config",
                         "memory-package", feed=feed, package_id="Hoard.Fixtures.Metadata.Memory")
        canonicalize.assert_called_once_with(feed / "Hoard.Fixtures.Metadata.Memory.0.1.0.nupkg")

    def test_capture_recomputes_added_runtime_and_locks_and_rejects_remapped_sources(self):
        (self.directory / "stores").mkdir()
        (self.directory / "feed").mkdir()
        run = SimpleNamespace(root=self.directory, run_id=str(uuid.uuid4()), _check_ledger=lambda: None)
        config, feed = checks.baselines._config(run, "candidate")
        for name in checks.INPUT_PACKAGES:
            with zipfile.ZipFile(feed / f"{name}.0.1.0.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                archive.writestr(f"lib/net10.0/{name}.dll", b"fixture")
        repository = self.directory / "repository"
        (repository / checks.SDK / "Catalog").mkdir(parents=True)
        (repository / checks.SDK / "Catalog/catalog.json").write_bytes(b"{}")
        (repository / checks.SDK / "packages.lock.json").write_bytes(b"lock")
        subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
        subprocess.run(["git", "add", "."], cwd=repository, check=True)
        subprocess.run([
            "git", "-c", "user.name=Conformance fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
            "commit", "--quiet", "-m", "Create synthetic SDK inputs",
        ], cwd=repository, check=True)
        candidate = self.directory / "snapshot"
        shutil.copytree(repository / "tests", candidate / "tests")
        runtime = candidate / checks.TESTS / "bin/Release/net10.0"
        runtime.mkdir(parents=True)
        (runtime / "Tests.dll").write_bytes(b"runtime")
        (runtime / "Tests.runtimeconfig.json").write_bytes(b'{"runtimeOptions":{}}')
        native = candidate / checks.TESTS / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/runtimes/linux-x64/native/libe_sqlite3.so")
        native.parent.mkdir(parents=True)
        native.write_bytes(b"native")
        wrapped = candidate / checks.METADATA_TESTS / checks.METADATA_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Testing.Conformance.dll")
        wrapped.parent.mkdir(parents=True)
        wrapped.write_bytes(b"shared-sdk")
        artifact_wrapped = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Testing.Conformance.dll")
        artifact_wrapped.parent.mkdir(parents=True)
        artifact_wrapped.write_bytes(b"shared-sdk")
        artifact_consumer = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
        artifact_consumer.parent.mkdir(parents=True)
        artifact_consumer.write_bytes(b"owned-artifact-session")
        sources = checks.evidence.source_manifest(repository)
        environment = {
            "os": "linux", "osVersion": "test", "architecture": "x86_64",
            "sdk": "10.0.203", "runtime": "10.0.7", "nativeSqlite": "not-used",
            "filesystem": "ext4", "runnerImage": "none", "freeBytes": 100,
            "pragmas": {"journalMode": "none", "synchronous": 0, "foreignKeys": 0, "busyTimeout": 0},
        }
        identity = checks.evidence.source_identity(repository)
        def capture(group_id=None):
            return checks.make_inputs(run, repository, candidate, sources,
                                      environment, identity, None, group_id=group_id)
        unconsumed = runtime / "unused-native-build.a"
        with unconsumed.open("wb") as output:
            output.truncate(checks.evidence.MAX_PROOF_BYTES + 1)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
            checks.evidence.proof_manifest(candidate)
        before = capture()
        selected_large = runtime / "Oversized.dll"
        with selected_large.open("wb") as output:
            output.truncate(checks.evidence.MAX_PROOF_BYTES + 1)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
            capture(before["invocationGroupId"])
        selected_large.unlink()
        foreign_native = native.parent.parent.parent / "linux-arm64/native/libe_sqlite3.so"
        foreign_native.parent.mkdir(parents=True)
        foreign_native.write_bytes(b"unexecuted architecture")
        self.assertEqual(dict(before["runtimeAssemblies"]), dict(capture(before["invocationGroupId"])["runtimeAssemblies"]))
        foreign_native.unlink()
        foreign_native.symlink_to(native)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
            capture(before["invocationGroupId"])
        foreign_native.unlink()
        self.assertEqual(len(before["packages"]), 15)
        self.assertNotIn(str(self.directory).encode(), checks.evidence.canonical_bytes(before))
        for path in (native, wrapped, artifact_wrapped, artifact_consumer,
                     runtime / "Added.dll", runtime / "Tests.runtimeconfig.json",
                     candidate / "added.packages.lock.json"):
            with self.subTest(path=path.name):
                original = path.read_bytes() if path.exists() else None
                path.write_bytes(b"added after admission")
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                    checks.evidence.verify_input_recomputation(
                        before, capture(before["invocationGroupId"]))
                if original is None:
                    path.unlink()
                else:
                    path.write_bytes(original)
        config.write_text(config.read_text().replace("Hoard.*", "*"))
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            capture(before["invocationGroupId"])

    def test_attempt_uses_exact_identities_disabled_console_and_ingestion(self):
        (self.directory / "proofs").mkdir()
        (self.directory / "stores").mkdir()
        owner = self.directory / "runtime-owner.json"
        owner.write_bytes(b"owner")
        candidate = self.directory / "stores/candidate"
        scenario = checks.SCENARIOS[1]
        identities = scenario[1]
        assembly_path = f"stores/candidate/{checks.LOGGER}/Smoke/bin/Release/net10.0/Smoke.dll"
        inputs = {"runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                  "runtimeAssemblies": {assembly_path: "a" * 64},
                  "packages": [{"packageId": "Hoard.Conformance.TestLogger", "sha256": "b" * 64}]}
        result = SimpleNamespace(exit_code=0, events=(
            {"event": "control", "code": "None", "value": 2},))
        received = {}
        discoveries = {}

        def command(args, **kwargs):
            self.assertLessEqual(kwargs["timeout"], 600)
            self.assertEqual(args[-1], "--TestCaseFilter:FullyQualifiedName=" +
                             checks.SMOKE + "Parameter")
            settings = ET.parse(args[-2].removeprefix("--Settings:")).getroot()
            self.assertEqual(Path(args[-2].removeprefix("--Settings:")).parent, self.directory / "stores")
            loggers = settings.findall("./LoggerRunSettings/Loggers/Logger")
            self.assertEqual([(item.attrib["friendlyName"], item.attrib["enabled"]) for item in loggers],
                             [("console", "False"), ("HoardSafe", "True")])
            attempt_id = settings.findtext(".//AttemptId")
            manifest = json.loads((self.directory / f"runtime-input-{attempt_id}.json").read_bytes())
            discovery = manifest["purpose"] == "discovery"
            self.assertEqual(kwargs["kind"], "discovery" if discovery else "tests")
            self.assertEqual("--ListTests" in args, discovery)
            if discovery:
                self.assertEqual(kwargs["discovery_tests"], frozenset(identities))
            output = self.directory / (("discovery-" if discovery else "runtime-") + attempt_id)
            output.mkdir()
            (output / "completion.json").write_bytes(b"{}")
            if discovery:
                (output / "discovered.jsonl").write_bytes(b"actual-discovery\n")
            else:
                (output / "witnesses.jsonl").write_bytes(b"actual-lines\n")
                for number in range(2):
                    (output / f"proof-{number}.json").write_bytes(b'{"failureKind":"None"}')
            return result

        def ingest(**kwargs):
            received.update(kwargs)
            return {"diagnosticCode": "None", "witnesses": tuple(
                {"testIdentity": identity, "status": "Passed"} for identity in identities)}

        def discover(**kwargs):
            discoveries.update(kwargs)
            return {"diagnosticCode": "None", "discoveries": tuple(
                {"testIdentity": identity} for identity in identities)}

        run = SimpleNamespace(root=self.directory, command=command)
        with patch.object(checks.evidence, "ingest_runtime_attempt", side_effect=ingest), \
                patch.object(checks.evidence, "ingest_runtime_discovery", side_effect=discover):
            observation = checks.test_attempt(run, inputs, candidate, scenario)
        self.assertEqual(observation["tests"], 2)
        self.assertEqual(received["expected_tests"],
                         {identity: ("none", "none") for identity in identities})
        self.assertEqual(received["witnesses_data"], b"actual-lines\n")
        self.assertLessEqual(received["started_ms"], received["ended_ms"])
        self.assertEqual(received["manifest_sha256"], hashlib.sha256(received["manifest_data"]).hexdigest())
        manifest = json.loads(received["manifest_data"])
        self.assertEqual(manifest["packages"][0]["id"], "Hoard.Conformance.TestLogger")
        self.assertEqual(manifest["assemblies"][0]["path"], assembly_path)
        self.assertEqual(manifest["purpose"], "execution")
        discovery_manifest = json.loads(discoveries["manifest_data"])
        self.assertEqual(discovery_manifest["purpose"], "discovery")
        self.assertNotEqual(discovery_manifest["attemptId"], manifest["attemptId"])
        self.assertEqual(discoveries["discoveries_data"], b"actual-discovery\n")
        self.assertLessEqual(discoveries["ended_ms"], received["started_ms"])
        with patch.object(checks.evidence, "ingest_runtime_attempt") as execution, \
                patch.object(checks.evidence, "ingest_runtime_discovery", return_value={
                    "diagnosticCode": "None", "discoveries": [{"testIdentity": identities[0]}]}):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "EvidenceIncomplete"):
                checks.test_attempt(run, inputs, candidate, scenario)
            execution.assert_not_called()

    def test_environment_forwards_only_allowlisted_actual_runner_image(self):
        (self.directory / "proofs").mkdir()
        observed = []

        def command(args, **kwargs):
            observed.append(kwargs)
            Path(args[-1]).write_text(json.dumps(ENVIRONMENT))
            return SimpleNamespace(exit_code=0, events=())

        run = SimpleNamespace(root=self.directory, command=command)
        for image_os, image_version, expected in (
            ("ubuntu24", "20261020.57.1", "ubuntu24.20261020.57.1"),
            ("", "", "none"),
            ("ubuntu24", "private-canary-image", "none"),
            ("unknown-image", "20261020.57.1", "none"),
        ):
            with self.subTest(image_os=image_os, image_version=image_version), \
                    patch.dict(checks.os.environ, {"ImageOS": image_os, "ImageVersion": image_version}):
                checks.environment(run)
                self.assertEqual(observed[-1]["env"], {"HOARD_RUNNER_IMAGE": expected})
                self.assertEqual(observed[-1]["kind"], "build")
                self.assertLessEqual(observed[-1]["timeout"], 30)

    def test_admission_and_completion_capture_distinct_environment_observations(self):
        (self.directory / "proofs").mkdir()
        observed = []
        def command(args, **kwargs):
            with Path(args[-1]).open("xb") as target:
                target.write(json.dumps(ENVIRONMENT).encode())
            observed.append((Path(args[-1]).name, kwargs["cache_id"]))
            return SimpleNamespace(exit_code=0, events=())
        run = SimpleNamespace(root=self.directory, command=command)
        checks.environment(run)
        checks.environment(run, phase="completion")
        self.assertEqual(observed, [
            ("environment-admission.json", "environment-admission"),
            ("environment-completion.json", "environment-completion"),
        ])

    def test_probe_observes_filesystem_and_explicit_runner_metadata(self):
        output = self.directory / "environment.json"
        calls = []

        def capture(args, **kwargs):
            calls.append((args, kwargs))
            return {
                "--version": (0, b"10.0.203\n"),
                "--list-runtimes": (0, b"Microsoft.NETCore.App 10.0.7 [/sdk/shared/Microsoft.NETCore.App]\n"),
                "-f": (0, b"ext2/ext3\n"),
            }[args[1]]

        with patch.object(checks, "native_execution_supported", return_value=True), \
                patch.object(checks, "capture_control", side_effect=capture), \
                patch.dict(checks.os.environ, {"HOARD_RUNNER_IMAGE": "ubuntu24.20261020.57.1"}):
            checks.probe(output)
        observed = json.loads(output.read_bytes())
        self.assertEqual(observed["filesystem"], "ext2-ext3")
        self.assertEqual(observed["runnerImage"], "ubuntu24.20261020.57.1")
        self.assertEqual(calls[-1][0], ["stat", "-f", "--format=%T", str(output.parent)])
        self.assertEqual(calls[-1][1], {"limit": 1024, "timeout": 5})

    def test_insufficient_scratch_is_reported_as_incomplete_before_any_workspace_is_created(self):
        parent = Path(tempfile.mkdtemp(prefix="hoard-preflight-test-")).resolve()
        self.addCleanup(shutil.rmtree, parent)
        destination = parent / "unallocated"
        sentinel = parent / "outside"
        sentinel.write_bytes(b"preserve")
        output = io.StringIO()
        with patch.object(sys, "argv", ["conformance_sdk_checks.py", "--evidence", str(destination)]), \
                patch.object(checks, "native_execution_supported", return_value=True), \
                patch("conformance_execution.shutil.disk_usage",
                      return_value=SimpleNamespace(free=24 * 1024**3 - 1)), \
                contextlib.redirect_stdout(output):
            code = checks.main()
        observed = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(observed["code"], "InsufficientCapacity")
        self.assertEqual(observed["status"], "Incomplete")
        self.assertFalse(observed["qualification"])
        self.assertFalse(destination.exists())
        self.assertEqual(sentinel.read_bytes(), b"preserve")

    def test_evidence_failure_is_not_relabelled_as_a_prerequisite_problem(self):
        output = io.StringIO()
        with patch.object(sys, "argv", ["conformance_sdk_checks.py", "--evidence", "unused"]), \
                patch.object(checks, "execute", side_effect=checks.evidence.ConformanceError("ProofMismatch")), \
                contextlib.redirect_stdout(output):
            code = checks.main()
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue()), {
            "qualification": False, "status": "Failed", "code": "ProofMismatch",
        })

    def test_negative_observations_require_matching_exit_event_inventory_and_failure_kind(self):
        scenario = checks.SCENARIOS[2]
        _, identities, code, status, exit_code, kind = scenario
        result = SimpleNamespace(exit_code=exit_code, events=(
            {"event": "control", "code": code, "value": 1},))
        ingested = {"diagnosticCode": code, "witnesses": (
            {"testIdentity": identities[0], "status": status},)}
        proofs = {"proof.json": b'{"failureKind":"Assertion"}'}
        checks.validate_observation(ingested, result, identities, code, status, exit_code, proofs, kind)
        mutations = (
            ({"diagnosticCode": "UnknownDiagnostic", "witnesses": ingested["witnesses"]}, result, proofs),
            ({"diagnosticCode": code, "witnesses": ()}, result, proofs),
            (ingested, SimpleNamespace(exit_code=0, events=result.events), proofs),
            (ingested, SimpleNamespace(exit_code=1, events=()), proofs),
            (ingested, result, {"proof.json": b'{"failureKind":"Unknown"}'}),
        )
        for changed, command_result, proof_data in mutations:
            with self.subTest(changed=changed, result=command_result):
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "EvidenceIncomplete"):
                    checks.validate_observation(changed, command_result, identities, code, status,
                                                exit_code, proof_data, kind)

    def test_safe_reads_reject_oversized_and_linked_diagnostics(self):
        path = self.directory / "proof.json"
        path.write_bytes(b"12345")
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "OutputLimitExceeded"):
            checks.read_bounded(path, 4)
        linked = self.directory / "linked.json"
        linked.symlink_to(path)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "OwnershipInvalid"):
            checks.read_bounded(linked, 100)

    def test_lock_entry_rejects_unknown_arguments_without_echoing_private_input(self):
        import conformance_prepare as preparation
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(preparation.OwnedRun, "allocate") as allocate:
            code = preparation.main(["--private-canary-value"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue()), {
            "mode": "preparation", "qualification": False, "status": "Incomplete",
            "code": "EvidenceSchemaInvalid",
        })
        allocate.assert_not_called()

    def test_failed_locked_restore_never_switches_to_dependency_resolution_or_build(self):
        import conformance_prepare as preparation
        project = preparation.Project("tests/fixtures/conformance/Consumer/Consumer.csproj")
        calls = []
        def fail(run, args, **kwargs):
            calls.append(args)
            raise checks.evidence.ConformanceError("CommandFailed")
        with patch.object(preparation.baselines, "_command", side_effect=fail):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "CommandFailed"):
                preparation.build_project(
                    object(), self.directory, project, self.directory / "NuGet.Config",
                    self.directory / "feed", update=False)
        self.assertEqual(len(calls), 1)
        self.assertIn("--locked-mode", calls[0])
        self.assertNotIn("--force-evaluate", calls[0])

    def test_lock_publication_rejects_concurrent_source_changes_and_foreign_paths(self):
        import conformance_prepare as preparation
        target = preparation.TARGETS[0].lock_path
        prepared = {project.lock_path: b'{"version":2,"dependencies":{}}' for project in preparation.TARGETS}
        for locks, current, code in ((prepared, {"changed.cs": "a" * 64}, "InputChanged"),
                                    ({**prepared, "outside/packages.lock.json": b"{}"}, {}, "EvidenceIncomplete")):
            with self.subTest(locks=locks), patch.object(preparation.evidence, "source_manifest", return_value=current):
                with self.assertRaisesRegex(checks.evidence.ConformanceError, code):
                    preparation.publish_locks(self.directory, {}, locks)
                self.assertFalse((self.directory / target).exists())

    def test_lock_publication_changes_only_the_explicit_reviewable_inventory(self):
        import conformance_prepare as preparation
        locks = {project.lock_path: b'{"version":2,"dependencies":{"net10.0":{}}}' for project in preparation.TARGETS}
        for relative in locks:
            (self.directory / relative).parent.mkdir(parents=True, exist_ok=True)
        existing = self.directory / preparation.TARGETS[0].lock_path
        existing.write_bytes(b"original lock")
        foreign = self.directory / "predecessor.lock"
        foreign.write_bytes(b"untouched")
        sources = {existing.relative_to(self.directory).as_posix(): checks.evidence.file_sha256(existing)}
        with patch.object(preparation.evidence, "source_manifest", return_value=sources):
            preparation.publish_locks(self.directory, sources, locks)
        self.assertEqual({path: (self.directory / path).read_bytes() for path in locks}, locks)
        self.assertEqual(foreign.read_bytes(), b"untouched")
        self.assertFalse(tuple(self.directory.rglob(".conformance-lock-*.tmp")))


if __name__ == "__main__":
    unittest.main()
