import base64
import copy
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock
import uuid
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_evidence as evidence
import conformance_contributors as contributors
import conformance_case_catalog as catalog
from conformance_execution import OwnedRun, capture_control, command_environment, native_execution_supported


class ContributorCrashAdmissionTests(unittest.TestCase):
    run_id = "e02917fa-6725-4ebe-9bfd-4703ea533479"
    source_id = "7eeb81e3-b717-4461-a313-5a3281e0f9fc"
    recovery_id = "b57bcff9-1992-49e3-8235-27996cd66482"
    receipt_id = "5ce8e7c7-8cb6-40da-a8d1-c01682fd8774"

    def readback(self, boundary):
        import conformance_contributor_crashes as crashes

        control = b"acknowledged independent control before crash"
        observed = {
            "schemaVersion": 1, "qualification": False, "runId": self.run_id,
            "caseId": crashes.CASE_ID, "boundary": boundary, "ownerFenced": True,
            "reconstructed": boundary in ("B0", "B1"),
            "reclamation": {"D0": "Pending", "D1": "Reclaimed"}.get(boundary, "NotApplicable"),
            "contentSha256": hashlib.sha256(
                bytes((index * 17 + 11) % 256 for index in range(256)) * 4096).hexdigest(),
            "contentLength": 1048576, "controlSha256": hashlib.sha256(control).hexdigest(),
            "controlLength": len(control), "outcome": "Removed" if boundary.startswith("D") else "Published",
            "receiptId": self.receipt_id}
        state = {
            "Run": self.run_id, "Barrier": boundary, "TargetDigest": observed["contentSha256"],
            "TargetLength": observed["contentLength"],
            "Control": {"Digest": observed["controlSha256"], "Length": observed["controlLength"]},
            "AcknowledgedReceipt": self.receipt_id if boundary == "B3" else None}
        return observed, state

    def test_six_readbacks_require_exact_shared_bytes_outcomes_and_original_acknowledgement(self):
        import conformance_contributor_crashes as crashes

        for boundary in crashes.BOUNDARIES:
            good, state = self.readback(boundary)
            arguments = {"boundary": boundary, "run_id": self.run_id, "case_id": crashes.CASE_ID}
            admitted = crashes.admit_readback(
                evidence.canonical_bytes(good), evidence.canonical_bytes(state), **arguments)
            self.assertEqual(admitted, good)
            for change in (
                    {"schemaVersion": True}, {"qualification": True}, {"extra": True},
                    {"runId": self.source_id}, {"caseId": "foreign"}, {"boundary": "unknown"},
                    {"ownerFenced": False}, {"reconstructed": not good["reconstructed"]},
                    {"reclamation": "Reclaimed" if boundary != "D1" else "Pending"},
                    {"contentSha256": "0" * 64}, {"controlSha256": "0" * 64},
                    {"contentLength": True}, {"contentLength": 1048575}, {"controlLength": 1},
                    {"outcome": "Removed" if good["outcome"] == "Published" else "Published"},
                    {"receiptId": "00000000-0000-0000-0000-000000000000"}):
                with self.subTest(boundary=boundary, change=change), self.assertRaises(evidence.ConformanceError):
                    crashes.admit_readback(
                        evidence.canonical_bytes(good | change), evidence.canonical_bytes(state), **arguments)
            for change in ({"Run": self.source_id}, {"Barrier": "foreign"}, {"TargetDigest": "0" * 64},
                           {"TargetLength": 1}, {"Control": {}},
                           *([{"AcknowledgedReceipt": self.recovery_id}] if boundary == "B3" else [])):
                with self.subTest(boundary=boundary, state=change), self.assertRaises(evidence.ConformanceError):
                    crashes.admit_readback(
                        evidence.canonical_bytes(good), evidence.canonical_bytes(state | change), **arguments)

    def test_native_pair_reader_rejects_borrowed_changed_and_non_original_receipts(self):
        import conformance_contributor_crashes as crashes
        import conformance_sources as sources

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            lease = SimpleNamespace(resource_id="resource-test", descriptor=17)
            seal = {"resourceId": lease.resource_id, "pathSha256": "a" * 64, "identitySha256": "b" * 64}
            records = {}
            run = SimpleNamespace(
                root=root, run_id=self.run_id, root_id="c" * 32, command_sequence=2,
                live_children=lambda: (), read_execution_record=lambda sequence: records[sequence],
                _directory_lease_snapshot=lambda candidate: seal if candidate is lease else {})
            inputs = {"environment": {"runtime": "10.0.7"}, "bindings": [{"bindingId": "acme.adapter"}]}
            assembly = root / "consumer.dll"
            selected = {"consumer.dll": hashlib.sha256(b"consumer").hexdigest()}
            consumer = {"components": {}}
            boundary = "B3"
            control, state_path, prefix = crashes._layout(lease, boundary)
            (root / control).mkdir(parents=True, mode=0o700)
            (root / "proofs").mkdir(mode=0o700)

            def write(path, data):
                target = root / path
                if target.exists():
                    target.chmod(0o600)
                target.write_bytes(data)
                target.chmod(0o400)

            write("consumer.dll", b"consumer")
            observed, state = self.readback(boundary)
            state_data = evidence.canonical_bytes(state)
            source_data = evidence.canonical_bytes({"sessionId": self.source_id})
            index = {
                "schemaVersion": 1, "qualification": False, "kind": "artifact-crash-source",
                "runId": self.run_id, "caseId": crashes.CASE_ID, "boundary": boundary,
                "sessionId": self.source_id, "stateSha256": hashlib.sha256(state_data).hexdigest(),
                "originSha256": hashlib.sha256(source_data).hexdigest()}
            write(state_path, state_data)
            write(f"{prefix}-source-origin.json", source_data)
            write(f"{prefix}-source-readback.json", evidence.canonical_bytes(index))
            write(f"{prefix}-recover-origin.json", b'{"recovery":"modeled-leaf"}')
            write(f"{prefix}-recover-readback.json", evidence.canonical_bytes(observed))
            requests, controls = [], []
            for sequence, action in enumerate(("source", "recover"), 1):
                path, request = crashes._request(
                    run, lease, boundary, ROOT, action,
                    source_data if action == "recover" else None, index if action == "recover" else None)
                raw = evidence.canonical_bytes(request)
                write(path, raw)
                requests.append(path)
                command = {
                    "schemaVersion": 1, "sequence": sequence, "childPid": 100 + sequence,
                    "childStartSha256": str(sequence) * 64, "startedMs": sequence * 1000,
                    "endedMs": sequence * 1000 + 300, "exitCode": -9 if sequence == 1 else 0,
                    "diagnosticCode": "None", "groupState": "Exited", "scope": "recovery",
                    **({"barrier": {"value": 43, "observedMs": 1100, "signalMs": 1200}} if sequence == 1 else {})}
                controls.append(command)
                control_raw = evidence.canonical_bytes(command)
                write(f"proofs/recovery-command-{sequence:04}.json", control_raw)
                paths = {*selected, path}
                if sequence == 2:
                    paths.update((state_path, f"{prefix}-source-origin.json", f"{prefix}-source-readback.json"))
                records[sequence] = evidence.canonical_bytes({
                    **{key: value for key, value in command.items() if key != "barrier"},
                    "runId": run.run_id, "rootId": run.root_id, "directoryLease": dict(seal),
                    "argvSha256": evidence.digest(crashes._arguments(run, inputs, assembly, path, raw)),
                    "cwdSha256": hashlib.sha256(str(root).encode()).hexdigest(),
                    "inputFiles": evidence.input_manifest(root, sorted(paths)),
                    "outputFiles": evidence.input_manifest(root, (request["originPath"], request["readbackPath"])),
                    "controlRecordSha256": hashlib.sha256(control_raw).hexdigest()})
            options = {
                "repository": ROOT, "lease": lease, "boundary": boundary,
                "source_sequence": 1, "recovery_sequence": 2}
            with mock.patch.object(crashes, "_context", return_value=(inputs, assembly, selected, b"declaration")), \
                    mock.patch.object(sources, "OwnedRun", type(run)), \
                    mock.patch.object(evidence, "ingest_artifact_recovery_origin",
                                      return_value={"sessionId": self.recovery_id}) as leaf:
                good = crashes.admit_crash(run, inputs, consumer, None, **options)
                self.assertEqual(good["sourceParentSha256"], hashlib.sha256(records[1]).hexdigest())
                self.assertEqual(good["recoveryParentSha256"], hashlib.sha256(records[2]).hexdigest())
                self.assertEqual(leaf.call_args.kwargs["source_data"], source_data)
                for path, replacement in (
                        (requests[0], (root / requests[0]).read_bytes() + b"\n"),
                        (requests[1], (root / requests[1]).read_bytes() + b"\n"),
                        (state_path, state_data + b" "),
                        (f"{prefix}-source-readback.json", evidence.canonical_bytes(index | {"stateSha256": "0" * 64})),
                        (f"{prefix}-source-origin.json", evidence.canonical_bytes({"sessionId": self.recovery_id})),
                        (f"{prefix}-recover-readback.json", evidence.canonical_bytes(observed | {"ownerFenced": False})),
                        ("consumer.dll", b"borrowed"),
                        ("proofs/recovery-command-0001.json", evidence.canonical_bytes(controls[0]) + b"\n"),
                        ("proofs/recovery-command-0002.json", evidence.canonical_bytes(controls[1] | {"exitCode": 2}))):
                    original = (root / path).read_bytes()
                    try:
                        write(path, replacement)
                        with self.subTest(path=path), self.assertRaises(evidence.ConformanceError):
                            crashes.admit_crash(run, inputs, consumer, None, **options)
                    finally:
                        write(path, original)
                for change in ({"source_sequence": 2}, {"recovery_sequence": 3},
                               {"boundary": "B2"}, {"lease": SimpleNamespace(resource_id="borrowed", descriptor=17)}):
                    with self.subTest(change=change), self.assertRaises((evidence.ConformanceError, OSError)):
                        crashes.admit_crash(run, inputs, consumer, None, **(options | change))
                for change in ({"runId": self.source_id}, {"rootId": "d" * 32}, {"argvSha256": "0" * 64},
                               {"directoryLease": seal | {"identitySha256": "e" * 64}},
                               {"childStartSha256": controls[0]["childStartSha256"]}):
                    original = records[2]
                    try:
                        records[2] = evidence.canonical_bytes(evidence.load_json(original) | change)
                        with self.subTest(record=change), self.assertRaises(evidence.ConformanceError):
                            crashes.admit_crash(run, inputs, consumer, None, **options)
                    finally:
                        records[2] = original
                run.live_children = lambda: (101,)
                with self.assertRaises(evidence.ConformanceError):
                    crashes.admit_crash(run, inputs, consumer, None, **options)

    def test_unsupported_crash_orchestration_rejects_before_allocating_or_writing(self):
        import conformance_contributor_crashes as crashes

        with mock.patch.object(crashes, "native_execution_supported", return_value=False), \
                self.assertRaisesRegex(evidence.ConformanceError, "^PrerequisiteMissing$"):
            crashes.execute_crashes(None, None, None, None, repository=ROOT)

    def test_failed_crash_child_preserves_closed_diagnostic_and_does_not_start_recovery(self):
        import conformance_contributor_crashes as crashes

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "stores").mkdir(mode=0o700)
            lease = SimpleNamespace(resource_id="failed-resource", descriptor=17)
            inputs = {"environment": {"runtime": "10.0.7"}}
            run = SimpleNamespace(
                root=root, run_id=self.run_id, command_sequence=1,
                lease_directory=mock.Mock(return_value=lease),
                _directory_descriptor=lambda name: os.open(root / name, os.O_RDONLY | os.O_DIRECTORY),
                _root_descriptor=lambda: os.open(root, os.O_RDONLY | os.O_DIRECTORY),
                command=mock.Mock(return_value=SimpleNamespace(
                    exit_code=2, events=({"event": "control", "code": "AssertionFailed", "value": 0},))))
            with mock.patch.object(crashes, "native_execution_supported", return_value=True), \
                    mock.patch.object(crashes, "_context",
                                      return_value=(inputs, root / "consumer.dll", {}, b"declaration")), \
                    self.assertRaisesRegex(evidence.ConformanceError, "^AssertionFailed$"):
                crashes.execute_crashes(run, inputs, None, None, repository=ROOT)
            run.command.assert_called_once()
            run.lease_directory.assert_called_once()
            request = run.command.call_args.args[0][-2]
            self.assertTrue(request.startswith("stores/"))
            self.assertFalse((root / "proofs").exists())


class ContributorTransferAdmissionTests(unittest.TestCase):
    def test_transfer_reader_binds_original_native_measurement_inputs_and_producer_bytes(self):
        import conformance_contributor_transfers as transfers
        import conformance_sources as sources

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "proofs").mkdir(mode=0o700)
            resource, size = "transfer-test", transfers.SIZES[0]
            request_path = f"stores/{resource}-control/request.json"
            (root / Path(request_path).parent).mkdir(parents=True, mode=0o700)
            records = {}
            run = SimpleNamespace(
                root=root, run_id=ContributorCrashAdmissionTests.run_id, root_id="a" * 32, command_sequence=1,
                live_children=lambda: (), read_execution_record=lambda sequence: records[sequence])
            inputs = {"environment": {"runtime": "10.0.7"}, "bindings": [{"bindingId": "acme.adapter"}]}
            assembly = root / "consumer.dll"
            selected = {"consumer.dll": hashlib.sha256(b"consumer").hexdigest()}
            consumer = {"components": {}}
            declaration = b"declaration"

            def write(path, data):
                target = root / path
                if target.exists():
                    target.chmod(0o600)
                target.write_bytes(data)
                target.chmod(0o400)

            with mock.patch.object(transfers.artifacts, "expected_transfer_hash", return_value="1" * 64):
                request = transfers._request(run, resource, size, ROOT)
                request_data = evidence.canonical_bytes(request)
                write(request_path, request_data)
                write("consumer.dll", b"consumer")
                write(transfers.ADMISSION_PATH, b'{"admission":"modeled-leaf"}')
                origin = {
                    "sessionId": ContributorCrashAdmissionTests.source_id, "parentSessionId": None,
                    "descriptorSha256": hashlib.sha256(declaration).hexdigest()}
                write(request["originPath"], evidence.canonical_bytes(origin))
                producer = {
                    "eventName": "complete", "provider": "acme.adapter", "runId": run.run_id, "pid": 101,
                    "size": size, "written": size, "read": size, "expectedSha256": "1" * 64,
                    "sourceSha256": "1" * 64, "sinkSha256": "1" * 64, "runtime": ".NET 10.0.7",
                    "sourcePaced": True, "sinkPaced": True, "nonSeekable": True, "generated": True,
                    "independentExpectedHash": True, "warmupComplete": True,
                    "bufferBytes": 262144, "providerBufferLimit": 2097152, "slots": 1}
                write(request["readbackPath"], evidence.canonical_bytes(producer))
                command = {
                    "schemaVersion": 1, "sequence": 1, "childPid": 101, "childStartSha256": "2" * 64,
                    "startedMs": 1000, "endedMs": 1300, "exitCode": 0, "diagnosticCode": "None",
                    "groupState": "Exited", "scope": "transfer", "transfer": {
                        "bytes": size, "phase": "complete", "baselineRssBytes": 10000000,
                        "osPeakRssBytes": 20000000, "sampledPeakRssBytes": 20000000, "samples": 3,
                        "osPeakMethod": "proc-status", "baselineMs": 1100, "completedMs": 1200}}
                control_raw = evidence.canonical_bytes(command)
                control_path = "proofs/transfer-command-0001.json"
                write(control_path, control_raw)
                records[1] = evidence.canonical_bytes({
                    **{key: value for key, value in command.items() if key != "transfer"},
                    "runId": run.run_id, "rootId": run.root_id,
                    "argvSha256": evidence.digest(transfers._arguments(run, inputs, assembly, request_path, request_data)),
                    "cwdSha256": hashlib.sha256(str(root).encode()).hexdigest(),
                    "inputFiles": evidence.input_manifest(root, sorted({*selected, transfers.ADMISSION_PATH, request_path})),
                    "outputFiles": evidence.input_manifest(root, (request["originPath"], request["readbackPath"])),
                    "controlRecordSha256": hashlib.sha256(control_raw).hexdigest()})
                options = {"repository": ROOT, "resource_id": resource, "size": size, "sequence": 1}
                with mock.patch.object(transfers, "artifact_process_context",
                                       return_value=(inputs, assembly, selected, declaration)), \
                        mock.patch.object(transfers, "_admission"), \
                        mock.patch.object(sources, "OwnedRun", type(run)), \
                        mock.patch.object(evidence, "_ingest_runtime_origins", return_value=(origin,)):
                    good = transfers.admit_transfer(run, inputs, consumer, None, **options)
                    self.assertEqual(good["nativeParentSha256"], hashlib.sha256(records[1]).hexdigest())
                    for path, replacement in (
                            (request_path, request_data + b"\n"), ("consumer.dll", b"borrowed"),
                            (transfers.ADMISSION_PATH, b'{"admission":"changed"}'),
                            (request["originPath"], evidence.canonical_bytes(origin) + b" "),
                            (request["readbackPath"], evidence.canonical_bytes(producer | {"read": size - 1})),
                            (control_path, control_raw + b"\n"),
                            (control_path, evidence.canonical_bytes(command | {
                                "transfer": command["transfer"] | {"osPeakRssBytes": 80000000}}))):
                        original = (root / path).read_bytes()
                        try:
                            write(path, replacement)
                            with self.subTest(path=path), self.assertRaises(evidence.ConformanceError):
                                transfers.admit_transfer(run, inputs, consumer, None, **options)
                        finally:
                            write(path, original)
                    for change in ({"runId": ContributorCrashAdmissionTests.source_id}, {"rootId": "b" * 32},
                                   {"argvSha256": "0" * 64}, {"controlRecordSha256": "0" * 64},
                                   {"inputFiles": {}}, {"outputFiles": {}}):
                        original = records[1]
                        try:
                            records[1] = evidence.canonical_bytes(evidence.load_json(original) | change)
                            with self.subTest(record=change), self.assertRaises(evidence.ConformanceError):
                                transfers.admit_transfer(run, inputs, consumer, None, **options)
                        finally:
                            records[1] = original
                    for change in ({"sequence": True}, {"sequence": 2}, {"size": True}, {"size": 1}):
                        with self.subTest(options=change), self.assertRaises(evidence.ConformanceError):
                            transfers.admit_transfer(run, inputs, consumer, None, **(options | change))
                    run.live_children = lambda: (101,)
                    with self.assertRaises(evidence.ConformanceError):
                        transfers.admit_transfer(run, inputs, consumer, None, **options)

    def test_failed_transfer_preserves_closed_diagnostic_and_does_not_start_second_size(self):
        import conformance_contributor_transfers as transfers

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "stores").mkdir(mode=0o700)
            inputs = {"environment": {"runtime": "10.0.7", "filesystem": "ext2-ext3"}}
            run = SimpleNamespace(
                root=root, run_id=ContributorCrashAdmissionTests.run_id, root_id="a" * 32,
                _directory_descriptor=lambda name: os.open(root / name, os.O_RDONLY | os.O_DIRECTORY),
                _root_descriptor=lambda: os.open(root, os.O_RDONLY | os.O_DIRECTORY),
                command=mock.Mock(return_value=SimpleNamespace(
                    exit_code=2, events=({"event": "control", "code": "AssertionFailed", "value": 0},))))
            with mock.patch.object(transfers, "native_execution_supported", return_value=True), \
                    mock.patch.object(transfers, "artifact_process_context",
                                      return_value=(inputs, root / "consumer.dll", {}, b"declaration")), \
                    mock.patch.object(transfers.shutil, "disk_usage", return_value=SimpleNamespace(free=24 * 1024**3)), \
                    mock.patch.object(transfers, "scratch_filesystem", return_value="ext2-ext3"), \
                    mock.patch.object(transfers.artifacts, "expected_transfer_hash", return_value="1" * 64), \
                    self.assertRaisesRegex(evidence.ConformanceError, "^AssertionFailed$"):
                transfers.execute_transfers(run, inputs, None, None, repository=ROOT)
            run.command.assert_called_once()
            self.assertTrue(run.command.call_args.args[0][-2].startswith("stores/"))
            self.assertEqual(run.command.call_args.kwargs["measure_transfer_bytes"], transfers.SIZES[0])

    def test_native_transfers_reject_missing_platform_and_foreign_controller_before_io(self):
        import conformance_contributor_transfers as transfers

        with mock.patch.object(transfers, "native_execution_supported", return_value=False), \
                self.assertRaisesRegex(evidence.ConformanceError, "^PrerequisiteMissing$"):
            transfers.execute_transfers(None, None, None, None, repository=ROOT)
        with mock.patch.object(transfers, "native_execution_supported", return_value=True), \
                self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
            transfers.execute_transfers(SimpleNamespace(), None, None, None, repository=ROOT)

    def test_measured_transfer_admission_rejects_relabelled_or_insufficient_environment(self):
        import conformance_contributor_transfers as transfers

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "proofs").mkdir(mode=0o700)
            path = root / transfers.ADMISSION_PATH
            inputs = {"environment": {"filesystem": "ext2-ext3"}}
            run = SimpleNamespace(
                root=root, run_id=ContributorCrashAdmissionTests.run_id, root_id="a" * 32,
                _root_descriptor=lambda: os.open(root, os.O_RDONLY | os.O_DIRECTORY))
            good = {
                "schemaVersion": 1, "qualification": False, "runId": run.run_id, "rootId": run.root_id,
                "inputsSha256": evidence.digest(inputs), "filesystem": "ext2-ext3", "freeBytes": 24 * 1024**3}

            def write(value):
                if path.exists():
                    path.chmod(0o600)
                path.write_bytes(evidence.canonical_bytes(value))
                path.chmod(0o400)

            write(good)
            with mock.patch.object(transfers, "scratch_filesystem", return_value="ext2-ext3"):
                self.assertEqual(transfers._admission(run, inputs), good)
                for change in (
                        {"qualification": True}, {"extra": True}, {"runId": ContributorCrashAdmissionTests.source_id},
                        {"rootId": "b" * 32}, {"inputsSha256": "0" * 64}, {"filesystem": "xfs"},
                        {"freeBytes": 24 * 1024**3 - 1}, {"freeBytes": True}):
                    write(good | change)
                    with self.subTest(change=change), self.assertRaises(evidence.ConformanceError):
                        transfers._admission(run, inputs)
                write(good)
            with mock.patch.object(transfers, "scratch_filesystem", return_value="xfs"), \
                    self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                transfers._admission(run, inputs)


class ContributorNonCooperationAdmissionTests(unittest.TestCase):
    def test_retained_reader_requires_both_original_inspections_and_native_output_receipt(self):
        import conformance_contributor_noncooperation as retention
        import conformance_sources as sources

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "proofs").mkdir(mode=0o700)
            records = {}
            run = SimpleNamespace(
                root=root, run_id=ContributorCrashAdmissionTests.run_id, root_id="a" * 32, command_sequence=1,
                live_children=lambda: (), read_execution_record=lambda sequence: records[sequence])
            inputs = {"environment": {"runtime": "10.0.7"}, "bindings": [{"bindingId": "acme.adapter"}]}
            assembly = root / "consumer.dll"
            selected = {"consumer.dll": hashlib.sha256(b"consumer").hexdigest()}
            consumer, declaration = {"components": {}}, b"declaration"
            origin = {
                "sessionId": ContributorCrashAdmissionTests.source_id, "parentSessionId": None,
                "descriptorSha256": hashlib.sha256(declaration).hexdigest()}

            def write(path, data):
                target = root / path
                if target.exists():
                    target.chmod(0o600)
                target.write_bytes(data)
                target.chmod(0o400)

            write("consumer.dll", b"consumer")
            for offset, scenario in enumerate(retention.SCENARIOS):
                resource = "retention-" + scenario
                request_path = f"stores/{resource}-control/request.json"
                (root / Path(request_path).parent).mkdir(parents=True, mode=0o700)
                request = retention._request(run, resource, scenario, ROOT)
                request_data = evidence.canonical_bytes(request)
                write(request_path, request_data)
                write(request["originPath"], evidence.canonical_bytes(origin))
                readbacks = {}
                for phase in ("contained", "inspected"):
                    readback = {
                        "eventName": "noncooperative", "phase": phase, "pid": 101, "runId": run.run_id,
                        "provider": "acme.adapter", "scenario": scenario, "durableCrashProof": False,
                        "cleanup": "RetainedLiveOwnership",
                        "callerCode": "Uncertain" if scenario == "native" else "CancelledBeforeCommit",
                        "admissionCode": "CleanupIncomplete", "shutdownCode": "CleanupIncomplete",
                        "enteredWorkers": 1, "workerPending": True, "borrowedStreamsIntact": True,
                        "rootStillOwned": True, "readinessBlocked": True, "protectionRetained": scenario != "source"}
                    path = request["readbackPrefix"] + "-" + phase + ".json"
                    readbacks[path] = readback
                    write(path, evidence.canonical_bytes(readback))
                command = {
                    "schemaVersion": 1, "sequence": 1, "childPid": 101, "childStartSha256": "2" * 64,
                    "startedMs": 1000, "endedMs": 1400, "exitCode": -9, "diagnosticCode": "None",
                    "groupState": "Exited", "scope": "recovery", "barrier": {
                        "value": 70 + offset, "observedMs": 1300, "signalMs": 1350,
                        "inspection": {"value": 60 + offset, "observedMs": 1100, "requestMs": 1200}}}
                control_raw = evidence.canonical_bytes(command)
                control_path = "proofs/recovery-command-0001.json"
                write(control_path, control_raw)
                records[1] = evidence.canonical_bytes({
                    **{key: value for key, value in command.items() if key != "barrier"},
                    "runId": run.run_id, "rootId": run.root_id,
                    "argvSha256": evidence.digest(retention._arguments(run, inputs, assembly, request_path, request_data)),
                    "cwdSha256": hashlib.sha256(str(root).encode()).hexdigest(),
                    "inputFiles": evidence.input_manifest(root, sorted({*selected, request_path})),
                    "outputFiles": evidence.input_manifest(root, retention._outputs(request)),
                    "controlRecordSha256": hashlib.sha256(control_raw).hexdigest()})
                options = {"repository": ROOT, "resource_id": resource, "scenario": scenario, "sequence": 1}
                with mock.patch.object(retention, "artifact_process_context",
                                       return_value=(inputs, assembly, selected, declaration)), \
                        mock.patch.object(sources, "OwnedRun", type(run)), \
                        mock.patch.object(evidence, "_ingest_runtime_origins", return_value=(origin,)):
                    good = retention.admit_noncooperation(run, inputs, consumer, None, **options)
                    self.assertEqual(good["nativeParentSha256"], hashlib.sha256(records[1]).hexdigest())
                    for path, replacement in (
                            (request_path, request_data + b"\n"), ("consumer.dll", b"borrowed"),
                            (request["originPath"], evidence.canonical_bytes(origin) + b" "),
                            (control_path, control_raw + b"\n"),
                            *((path, evidence.canonical_bytes(value | {"workerPending": False}))
                              for path, value in readbacks.items())):
                        original = (root / path).read_bytes()
                        try:
                            write(path, replacement)
                            with self.subTest(scenario=scenario, path=path), self.assertRaises(evidence.ConformanceError):
                                retention.admit_noncooperation(run, inputs, consumer, None, **options)
                        finally:
                            write(path, original)
                    for change in ({"runId": ContributorCrashAdmissionTests.source_id}, {"rootId": "b" * 32},
                                   {"argvSha256": "0" * 64}, {"outputFiles": {}}, {"controlRecordSha256": "0" * 64}):
                        original = records[1]
                        try:
                            records[1] = evidence.canonical_bytes(evidence.load_json(original) | change)
                            with self.subTest(record=change), self.assertRaises(evidence.ConformanceError):
                                retention.admit_noncooperation(run, inputs, consumer, None, **options)
                        finally:
                            records[1] = original

    def test_unsupported_foreign_or_oversized_retention_rejects_before_allocation(self):
        import conformance_contributor_noncooperation as retention

        with mock.patch.object(retention, "native_execution_supported", return_value=False), \
                self.assertRaisesRegex(evidence.ConformanceError, "^PrerequisiteMissing$"):
            retention.execute_noncooperation(None, None, None, None, repository=ROOT)
        with mock.patch.object(retention, "native_execution_supported", return_value=True):
            with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                retention.execute_noncooperation(SimpleNamespace(), None, None, None, repository=ROOT)
            with mock.patch.object(retention, "artifact_process_context",
                                   return_value=(None, None, dict.fromkeys(range(13)), None)), \
                    self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
                retention.execute_noncooperation(None, None, None, None, repository=ROOT)

    def test_failed_retention_child_keeps_closed_diagnostic_and_never_starts_next_scenario(self):
        import conformance_contributor_noncooperation as retention

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "stores").mkdir(mode=0o700)
            inputs = {"environment": {"runtime": "10.0.7"}}
            run = SimpleNamespace(
                root=root, run_id=ContributorCrashAdmissionTests.run_id,
                _directory_descriptor=lambda name: os.open(root / name, os.O_RDONLY | os.O_DIRECTORY),
                _root_descriptor=lambda: os.open(root, os.O_RDONLY | os.O_DIRECTORY),
                command=mock.Mock(return_value=SimpleNamespace(
                    exit_code=2, events=({"event": "control", "code": "AssertionFailed", "value": 0},))))
            with mock.patch.object(retention, "native_execution_supported", return_value=True), \
                    mock.patch.object(retention, "artifact_process_context",
                                      return_value=(inputs, root / "consumer.dll", {}, b"declaration")), \
                    self.assertRaisesRegex(evidence.ConformanceError, "^AssertionFailed$"):
                retention.execute_noncooperation(run, inputs, None, None, repository=ROOT)
            run.command.assert_called_once()
            self.assertTrue(run.command.call_args.args[0][-2].startswith("stores/"))
            self.assertEqual(run.command.call_args.kwargs["inspect_at_barrier"], 60)
            self.assertEqual(run.command.call_args.kwargs["stop_at_barrier"], 70)


class NuGetContentToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("dotnet") is None:
            raise unittest.SkipTest("Managed NuGet content tool requires the pinned .NET SDK")
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.parent = Path(cls.temporary.name).resolve()
        cls.owner = OwnedRun.allocate(cls.parent / "run", ROOT, profile="harness")
        source = cls.owner.root / "source"
        project = Path("tests/fixtures/conformance/BuildInputs/BuildInputs.csproj")
        for relative in (Path("global.json"), Path("Directory.Build.props"),
                         Path("Directory.Packages.props"), project, project.with_name("packages.lock.json"),
                         *(path.relative_to(ROOT) for path in (ROOT / project.parent).glob("*.cs"))):
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        cache = cls.owner.root / "cache/content"
        cache.mkdir()
        (cache / "tmp").mkdir()
        cls.environment = command_environment(cls.owner.root, cache, {"DOTNET_ROLL_FORWARD": "LatestPatch"})
        cls.generated = cls.owner.root / "tool-build/obj"
        cls.output = cls.owner.root / "tool-build/bin/Release/net10.0"
        cls.source = source
        config = cls.owner.root / "NuGet.Config"
        config.write_bytes(b"<configuration><packageSources><clear /></packageSources></configuration>")
        code, _ = capture_control(
            ["dotnet", "build", str(source / project), "-c", "Release", "-p:RestoreLockedMode=true",
             "-p:RestoreConfigFile=" + str(config), "-p:UseSharedCompilation=false", "-nodeReuse:false", "-v", "quiet",
             "-p:BaseIntermediateOutputPath=" + str(cls.generated) + "/",
             "-p:BaseOutputPath=" + str(cls.output.parents[1]) + "/", "-p:PathMap=",
             "-p:EmitCompilerGeneratedFiles=true", "-p:CompilerGeneratedFilesOutputPath=" + str(cls.generated / "generated")],
            cwd=source, env=cls.environment, limit=65536, timeout=120)
        if code:
            raise AssertionError("Managed NuGet content tool build failed")
        cls.tool = cls.output / "Hoard.Fixtures.Conformance.BuildInputs.dll"

    @classmethod
    def tearDownClass(cls):
        cls.owner.transition("Active")
        cls.owner.transition("Settling")
        cls.owner.release()

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(dir=self.owner.root))
        self.prefix = "acme.dependency/2.4.0-preview.1"
        self.cache = self.case / "packages"
        directory = self.cache / self.prefix
        directory.mkdir(parents=True)
        self.archive = directory / "acme.dependency.2.4.0-preview.1.nupkg"
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("Acme.Dependency.nuspec", (
                "<package><metadata><id>Acme.Dependency</id><version>2.4.0-preview.1</version></metadata></package>"))
            archive.writestr("build/Acme.Dependency.props", "<Project />")
        self.assets = self.case / "assets.json"
        self.graph = {"version": 3, "libraries": {"Acme.Dependency/2.4.0-preview.1": {
            "type": "package", "path": self.prefix}}}
        self.assets.write_bytes(evidence.canonical_bytes(self.graph))
        self.output = self.case / "content.json"
        self.request = self.case / "request.json"
        self.value = {
            "schemaVersion": 1, "qualification": False,
            "assets": {"path": self.relative(self.assets), "sha256": evidence.file_sha256(self.assets)},
            "cachePath": self.relative(self.cache), "outputPath": self.relative(self.output)}
        self.request.write_bytes(evidence.canonical_bytes(self.value))

    def relative(self, path):
        return path.relative_to(self.owner.root).as_posix()

    def test_managed_build_batch_preserves_cold_restore_imports_images_and_locked_failure(self):
        import conformance_sdk_checks as checks
        from conformance_execution import project_build_line

        self.evaluation_request()
        prefix = ("dotnet", "exec", "--fx-version", self.runtime_version, str(self.msbuild))
        dependency_feed = self.case / "dependencies"
        dependency_feed.mkdir()
        dependency = dependency_feed / "Acme.BuildInputs.1.0.0.nupkg"
        with zipfile.ZipFile(dependency, "w") as archive:
            archive.writestr("Acme.BuildInputs.nuspec", (
                "<package><metadata><id>Acme.BuildInputs</id><version>1.0.0</version>"
                "<authors>Fixture</authors><description>Cold import control</description></metadata></package>"))
            archive.writestr("build/Acme.BuildInputs.props", (
                "<Project><PropertyGroup><DefineConstants>$(DefineConstants);RESTORED_IMPORT"
                "</DefineConstants></PropertyGroup></Project>"))
        config = self.case / "NuGet.Config"
        configuration = ET.Element("configuration")
        sources = ET.SubElement(configuration, "packageSources")
        ET.SubElement(sources, "clear")
        ET.SubElement(sources, "add", key="local", value=str(dependency_feed))
        config.write_bytes(ET.tostring(configuration, encoding="utf-8"))
        locked = evidence.canonical_bytes({"version": 2, "dependencies": {"net10.0": {
            "Acme.BuildInputs": {
                "type": "Direct", "requested": "[1.0.0, 1.0.0]", "resolved": "1.0.0",
                "contentHash": base64.b64encode(hashlib.sha512(dependency.read_bytes()).digest()).decode()}}}})
        commands, archives, images = [], [], []

        def execute(run, arguments, *, cwd, cache_id):
            cache = self.case / cache_id / "packages"
            (cache / "tmp").mkdir(parents=True, exist_ok=True)
            environment = command_environment(self.owner.root, cache, {"DOTNET_ROLL_FORWARD": "Disable"})
            code, raw = capture_control(arguments, cwd=cwd, env=environment, limit=65536, timeout=120)
            commands.append(tuple(arguments))
            events = tuple(event for line in raw.splitlines() if line.strip()
                           if (event := project_build_line(line)) is not None)
            if code or events:
                raise evidence.ConformanceError("CommandFailed")

        with mock.patch.object(checks.baselines, "_command", side_effect=execute):
            for mode in ("separate", "batched", "invalid-lock"):
                directory = self.case / mode
                directory.mkdir()
                project, lock, feed = directory / "Fixture.csproj", directory / "packages.lock.json", directory / "feed"
                feed.mkdir()
                project.write_text(
                    '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework>'
                    '<PackageId>Acme.Batch</PackageId><AssemblyName>Acme.Batch</AssemblyName>'
                    '<Version>0.1.0</Version><RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>'
                    '</PropertyGroup><ItemGroup><PackageReference Include="Acme.BuildInputs" Version="[1.0.0]" />'
                    '</ItemGroup><Target Name="CheckRestoreProperties" BeforeTargets="Restore" '
                    'Condition="\'$(Configuration)\' != \'Debug\' Or \'$(ColdRestoreControl)\' != \'preserved\'">'
                    '<Error Text="Original restore properties were not preserved." /></Target></Project>')
                (directory / "Marker.cs").write_text(
                    "#if !RESTORED_IMPORT\n#error The freshly restored props must be imported.\n#endif\n"
                    "namespace Acme { public sealed class Marker { } }\n")
                lock.write_bytes(locked if mode != "invalid-lock" else evidence.canonical_bytes(
                    {"version": 2, "dependencies": {"net9.0": {}}}))
                lock.chmod(0o400)
                before, start = lock.read_bytes(), len(commands)
                properties = ("-p:PathMap=" + str(directory) + "=/_/", "-property:ColdRestoreControl=preserved")
                if mode == "separate":
                    for command in checks.baselines.project_build_commands(
                            project, config, feed=feed, lock=lock, properties=properties, msbuild=prefix):
                        checks.baselines._command(None, command, cwd=directory, cache_id=mode)
                    checks.canonicalize_acceptance_archive(feed / "Acme.Batch.0.1.0.nupkg",
                                                          expected_package_id="Acme.Batch")
                    self.assertEqual(len(commands) - start, 3)
                elif mode == "batched":
                    checks.build(None, project, config, mode, feed=feed, lock=lock,
                                 properties=properties, package_id="Acme.Batch", msbuild=prefix)
                    self.assertEqual(len(commands) - start, 1)
                else:
                    with self.assertRaisesRegex(evidence.ConformanceError, "CommandFailed"):
                        checks.build(None, project, config, mode, feed=feed, lock=lock,
                                     properties=properties, package_id="Acme.Batch", msbuild=prefix)
                    self.assertEqual(len(commands) - start, 1)
                    self.assertFalse((directory / "bin").exists())
                    self.assertEqual(list(feed.iterdir()), [])
                self.assertEqual(lock.read_bytes(), before)
                if mode != "invalid-lock":
                    archives.append((feed / "Acme.Batch.0.1.0.nupkg").read_bytes())
                    images.append(tuple((directory / "bin/Release/net10.0" / ("Acme.Batch" + suffix)).read_bytes()
                                        for suffix in (".dll", ".pdb")))
            self.assertEqual(archives[0], archives[1])
            self.assertEqual(images[0], images[1])

    def invoke(self, *, digest=None, operation="content-hashes"):
        code, raw = capture_control(
            ["dotnet", str(self.tool), operation, str(self.owner.root), self.relative(self.request),
             evidence.file_sha256(self.request) if digest is None else digest],
            cwd=self.owner.root, env=self.environment, limit=65536, timeout=30)
        try:
            value = evidence.load_json(raw)
        except evidence.ConformanceError:
            raise AssertionError("Managed content tool emitted non-schema diagnostics") from None
        return code, value

    def test_managed_content_tool_computes_actual_unsigned_archive_receipt_and_refuses_output_reuse(self):
        code, event = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(event, {"event": "control", "code": "None", "value": 1})
        receipt = evidence.load_json(self.output.read_bytes())
        self.assertEqual(receipt, {"schemaVersion": 1, "qualification": False, "packages": [{
            "cachePath": self.prefix, "archiveSha256": evidence.file_sha256(self.archive),
            "contentSha512": hashlib.sha512(self.archive.read_bytes()).hexdigest()}]})
        original = self.output.read_bytes()
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "OwnershipInvalid"))
        self.assertEqual(self.output.read_bytes(), original)

    def consumer_lock_request(self, *, dependency_version="3.2.1", cycle=False, pruned_baseline=False):
        archives = []

        def package(name, version, dependencies=""):
            path = self.case / f"{name}.{version}.nupkg"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(f"{name}.nuspec", (
                    f"<package><metadata><id>{name}</id><version>{version}</version>"
                    "<authors>Hoard fixture</authors><description>Consumer lock fixture</description>"
                    f"{dependencies}</metadata></package>"))
                if name == "Acme.Adapter":
                    archive.writestr("lib/net10.0/Acme.Adapter.dll", b"fixture adapter image")
            archives.append({"path": self.relative(path), "sha256": evidence.file_sha256(path)})
            return path

        baseline = package("Acme.Base", "0.1.0", (
            '<dependencies><group targetFramework="net10.0">'
            '<dependency id="System.Memory" version="4.5.3" />'
            '</group></dependencies>' if pruned_baseline else ""))
        package("Acme.Dependency", dependency_version, (
            '<dependencies><group targetFramework="net10.0">'
            '<dependency id="Acme.Adapter" version="[2.4.0-preview.1]" />'
            '</group></dependencies>' if cycle else ""))
        package("Acme.BuildOnly", "4.5.6")
        package("Acme.Adapter", "2.4.0-preview.1", (
            '<dependencies><group targetFramework="net10.0">'
            '<dependency id="Acme.Base" version="[0.1.0]" />'
            '<dependency id="Acme.Dependency" version="[3.2.1]" />'
            '</group></dependencies>'))
        self.lock = self.case / "consumer-source.lock.json"
        self.lock_value = {"version": 2, "dependencies": {"net10.0": {
            "Acme.Base": {
                "type": "Direct", "requested": "[0.1.0, 0.1.0]", "resolved": "0.1.0",
                "contentHash": base64.b64encode(hashlib.sha512(baseline.read_bytes()).digest()).decode()}}}}
        self.lock.write_bytes(evidence.canonical_bytes(self.lock_value))
        value = {
            "schemaVersion": 1, "qualification": False,
            "sourceLock": {"path": self.relative(self.lock), "sha256": evidence.file_sha256(self.lock)},
            "adapter": {"packageId": "Acme.Adapter", "version": "2.4.0-preview.1"},
            "archives": archives, "outputPath": self.relative(self.output)}
        self.request.write_bytes(evidence.canonical_bytes(value))
        return value

    def consumer_lock_round_trip(self, *, pruned_baseline=False):
        self.consumer_lock_request(pruned_baseline=pruned_baseline)
        code, event = self.invoke(operation="consumer-lock")
        self.assertEqual((code, event), (0, {"event": "control", "code": "None", "value": 3}))
        receipt = evidence.load_json(self.output.read_bytes())
        self.assertEqual(set(receipt), {
            "schemaVersion", "qualification", "sourceLockSha256", "packages", "lock"})
        self.assertFalse(receipt["qualification"])
        self.assertEqual(receipt["sourceLockSha256"], evidence.file_sha256(self.lock))
        rows = receipt["lock"]["dependencies"]["net10.0"]
        self.assertEqual(set(rows), {"Acme.Base", "Acme.Adapter", "Acme.Dependency"})
        self.assertEqual(rows["Acme.Base"], self.lock_value["dependencies"]["net10.0"]["Acme.Base"])
        self.assertEqual(rows["Acme.Adapter"]["type"], "Direct")
        self.assertEqual(rows["Acme.Adapter"]["requested"], "[2.4.0-preview.1, 2.4.0-preview.1]")
        self.assertEqual(rows["Acme.Dependency"]["type"], "Transitive")
        self.assertEqual(rows["Acme.Dependency"]["resolved"], "3.2.1")
        self.assertEqual({row["packageId"] for row in receipt["packages"]}, set(rows))
        for row in receipt["packages"]:
            archive = self.case / f'{row["packageId"]}.{row["version"]}.nupkg'
            self.assertEqual(row["archiveSha256"], evidence.file_sha256(archive))
            self.assertEqual(row["nugetContentSha512"], hashlib.sha512(archive.read_bytes()).hexdigest())
            self.assertEqual(rows[row["packageId"]]["contentHash"],
                             base64.b64encode(bytes.fromhex(row["nugetContentSha512"])).decode())
        consumer = self.case / "consumer"
        consumer.mkdir()
        project = consumer / "Consumer.csproj"
        project.write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
            '<TargetFramework>net10.0</TargetFramework>'
            '<RestoreEnablePackagePruning>true</RestoreEnablePackagePruning></PropertyGroup><ItemGroup>'
            '<PackageReference Include="Acme.Base" Version="[0.1.0]" />'
            '<PackageReference Include="Acme.Adapter" Version="[2.4.0-preview.1]" />'
            '</ItemGroup></Project>')
        lock = consumer / "packages.lock.json"
        lock_bytes = evidence.canonical_bytes(receipt["lock"])
        lock.write_bytes(lock_bytes)
        config = consumer / "NuGet.Config"
        configuration = ET.Element("configuration")
        sources = ET.SubElement(configuration, "packageSources")
        ET.SubElement(sources, "clear")
        ET.SubElement(sources, "add", key="fixture", value=str(self.case))
        config.write_bytes(ET.tostring(configuration, encoding="utf-8"))
        cache = self.case / "restore-cache"
        (cache / "tmp").mkdir(parents=True)
        environment = command_environment(self.owner.root, cache, {"DOTNET_ROLL_FORWARD": "LatestPatch"})
        code, raw = capture_control(
            ["dotnet", "restore", str(project), "--locked-mode", "--configfile", str(config),
             "-p:UseSharedCompilation=false", "-nodeReuse:false", "-v", "quiet"],
            cwd=consumer, env=environment, limit=65536, timeout=120)
        self.assertEqual(code, 0, "Composed lock did not support actual locked NuGet restore")
        self.assertEqual(raw, b"")
        self.assertEqual(lock.read_bytes(), lock_bytes)
        original = self.output.read_bytes()
        self.assertEqual(self.invoke(operation="consumer-lock")[1]["code"], "OwnershipInvalid")
        self.assertEqual(self.output.read_bytes(), original)

    def test_managed_consumer_lock_composition_uses_exact_archive_closure_without_resolving(self):
        self.consumer_lock_round_trip()

    def test_managed_consumer_lock_composition_preserves_framework_pruned_original_dependency_graph(self):
        self.consumer_lock_round_trip(pruned_baseline=True)

    def test_managed_consumer_lock_composition_does_not_repair_a_missing_original_dependency_row(self):
        value = self.consumer_lock_request(pruned_baseline=True)
        path = self.case / "System.Memory.4.5.3.nupkg"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("System.Memory.nuspec", (
                "<package><metadata><id>System.Memory</id><version>4.5.3</version></metadata></package>"))
        value["archives"].append({"path": self.relative(path), "sha256": evidence.file_sha256(path)})
        self.lock_value["dependencies"]["net10.0"]["Acme.Base"]["dependencies"] = {"System.Memory": "4.5.3"}
        self.lock.write_bytes(evidence.canonical_bytes(self.lock_value))
        value["sourceLock"]["sha256"] = evidence.file_sha256(self.lock)
        self.request.write_bytes(evidence.canonical_bytes(value))
        self.assertEqual(self.invoke(operation="consumer-lock"), (
            2, {"event": "control", "code": "ProofMismatch", "value": 0}))
        self.assertFalse(self.output.exists())

    def test_managed_consumer_lock_composition_rejects_unsatisfied_exact_archive_versions(self):
        self.consumer_lock_request(dependency_version="3.2.2")
        self.assertEqual(self.invoke(operation="consumer-lock"), (
            2, {"event": "control", "code": "ProofMismatch", "value": 0}))
        self.assertFalse(self.output.exists())

    def captured_consumer_lock(self, *, mutation=None, native=False):
        value = self.consumer_lock_request()
        owner = OwnedRun.allocate(self.case / ("consumer-lock-" + (mutation or "good")), ROOT, profile="harness")
        tools = owner.root / "tools"
        shutil.copytree(self.tool.parent, tools)
        source = owner.root / "source.lock.json"
        shutil.copyfile(self.lock, source)
        archives = []
        for row in value["archives"]:
            original = self.owner.root / row["path"]
            path = owner.root / "feed" / original.name
            shutil.copyfile(original, path)
            archives.append(path)
        adapter = evidence.package_identity(owner.root / "feed", "Acme.Adapter", "2.4.0-preview.1")
        commands = []
        native_command = owner.command

        def execute(arguments, *, cwd, cache_id, kind, timeout, env):
            if native:
                result = native_command(
                    arguments, cwd=cwd, cache_id=cache_id, kind=kind, timeout=timeout, env=env)
            else:
                cache = owner.root / "cache" / cache_id
                (cache / "tmp").mkdir(parents=True, exist_ok=True)
                environment = command_environment(owner.root, cache, env)
                code, raw = capture_control(
                    arguments, cwd=cwd, env=environment, limit=65536, timeout=timeout)
                result = mock.Mock(exit_code=code, events=(evidence.load_json(raw),))
            commands.append(tuple(arguments))
            receipt = owner.root / "stores/binding-consumer/lock-receipt.json"
            if mutation in ("unused", "baseline", "missing", "extra"):
                document = evidence.load_json(receipt.read_bytes())
                if mutation == "extra":
                    document["optimistic"] = True
                elif mutation == "baseline":
                    document["lock"]["dependencies"]["net10.0"]["Acme.Base"]["requested"] = "[0.1.0, )"
                elif mutation == "missing":
                    del document["lock"]["dependencies"]["net10.0"]["Acme.Dependency"]
                else:
                    path = owner.root / "feed/Acme.BuildOnly.4.5.6.nupkg"
                    content = hashlib.sha512(path.read_bytes()).digest()
                    document["packages"].append({
                        "packageId": "Acme.BuildOnly", "version": "4.5.6",
                        "archiveSha256": evidence.file_sha256(path), "nugetContentSha512": content.hex()})
                    document["lock"]["dependencies"]["net10.0"]["Acme.BuildOnly"] = {
                        "type": "Transitive", "resolved": "4.5.6",
                        "contentHash": base64.b64encode(content).decode()}
                    result.events = ({"event": "control", "code": "None", "value": len(document["packages"])},)
                receipt.write_bytes(evidence.canonical_bytes(document))
            elif mutation == "source":
                source.write_bytes(source.read_bytes() + b" ")
            elif mutation == "support":
                path = tools / "NuGet.Packaging.dll"
                path.write_bytes(path.read_bytes() + b"changed")
            return result

        try:
            with mock.patch.object(owner, "command", side_effect=execute):
                result = contributors.capture_binding_consumer_lock(
                    owner, tools / self.tool.name, self.runtime_version, source, adapter, archives)
            self.assertEqual(len(commands), 1)
            self.assertEqual(commands[0][5], "consumer-lock")
            self.assertFalse(result["qualification"])
            self.assertEqual(result["lockSha256"], evidence.file_sha256(result["lockPath"]))
            self.assertEqual(result["lockPath"].stat().st_mode & 0o777, 0o400)
            self.assertEqual(evidence.load_json(result["lockPath"].read_bytes()), result["lock"])
            self.assertEqual(source.read_bytes(), self.lock.read_bytes())
        finally:
            if owner.state == "Allocated":
                owner.transition("Active")
            owner.transition("Settling")
            owner.release()

    def test_managed_owned_consumer_lock_capture_freezes_inputs_and_publishes_readonly_derived_lock(self):
        self.evaluation_request()
        self.captured_consumer_lock()

    def test_managed_owned_consumer_lock_capture_rejects_receipt_forgery_and_late_input_changes(self):
        self.evaluation_request()
        for mutation, code in (
                ("unused", "ProofMismatch"), ("baseline", "ProofMismatch"), ("missing", "ProofMismatch"),
                ("extra", "EvidenceSchemaInvalid"), ("source", "InputChanged"), ("support", "InputChanged")):
            with self.subTest(mutation=mutation), self.assertRaisesRegex(evidence.ConformanceError, "^" + code + "$"):
                self.captured_consumer_lock(mutation=mutation)

    @unittest.skipUnless(native_execution_supported(), "Native consumer lock capture requires supported Linux containment")
    def test_native_owned_consumer_lock_capture_uses_actual_executor_and_settles_resources(self):
        self.evaluation_request()
        self.captured_consumer_lock(native=True)

    def test_managed_consumer_lock_composition_rejects_changed_lock_or_archive_bytes(self):
        value = self.consumer_lock_request()
        self.lock.write_bytes(self.lock.read_bytes() + b" ")
        self.assertEqual(self.invoke(operation="consumer-lock")[1]["code"], "InputChanged")
        self.assertFalse(self.output.exists())
        self.lock.write_bytes(evidence.canonical_bytes(self.lock_value))
        archive = self.owner.root / value["archives"][0]["path"]
        archive.write_bytes(archive.read_bytes() + b"changed")
        self.assertEqual(self.invoke(operation="consumer-lock")[1]["code"], "InputChanged")
        self.assertFalse(self.output.exists())

    def test_managed_consumer_lock_composition_rejects_incomplete_conflicting_and_foreign_policies(self):
        for defect, code in (
                ("unknown-field", "EvidenceSchemaInvalid"), ("archive-field", "EvidenceSchemaInvalid"),
                ("duplicate-archive", "ProofMismatch"), ("missing-dependency", "ProofMismatch"),
                ("adapter-version", "ProofMismatch"), ("baseline-hash", "ProofMismatch"),
                ("baseline-version", "ProofMismatch"), ("baseline-edges", "ProofMismatch"),
                ("cycle", "ProofMismatch"), ("foreign-archive", "OwnershipInvalid")):
            with self.subTest(defect=defect):
                value = self.consumer_lock_request(cycle=defect == "cycle")
                if defect == "unknown-field":
                    value["resolve"] = True
                elif defect == "archive-field":
                    value["archives"][0]["packageId"] = "Acme.Other"
                elif defect == "duplicate-archive":
                    value["archives"].append(dict(value["archives"][0]))
                elif defect == "missing-dependency":
                    del value["archives"][1]
                elif defect == "adapter-version":
                    value["adapter"]["version"] = "2.4.1"
                elif defect == "foreign-archive":
                    value["archives"][0]["path"] = "../outside.nupkg"
                elif defect.startswith("baseline-"):
                    row = self.lock_value["dependencies"]["net10.0"]["Acme.Base"]
                    if defect == "baseline-hash":
                        row["contentHash"] = base64.b64encode(b"\x00" * 64).decode()
                    elif defect == "baseline-version":
                        row["resolved"] = "0.2.0"
                    else:
                        row["dependencies"] = {"Acme.Dependency": "[3.2.1]"}
                    self.lock.write_bytes(evidence.canonical_bytes(self.lock_value))
                    value["sourceLock"]["sha256"] = evidence.file_sha256(self.lock)
                self.request.write_bytes(evidence.canonical_bytes(value))
                self.assertEqual(self.invoke(operation="consumer-lock"), (
                    2, {"event": "control", "code": code, "value": 0}))
                self.assertFalse(self.output.exists())

    def test_managed_content_tool_rejects_changed_request_and_asset_hashes(self):
        code, event = self.invoke(digest="a" * 64)
        self.assertEqual((code, event["code"]), (2, "InputChanged"))
        self.assets.write_bytes(self.assets.read_bytes() + b" ")
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "InputChanged"))
        self.assertFalse(self.output.exists())

    def test_managed_content_tool_accepts_version_four_library_layout_but_not_unknown_assets_versions(self):
        for version, expected in ((5, 2), (4, 0)):
            with self.subTest(version=version):
                self.graph["version"] = version
                self.assets.write_bytes(evidence.canonical_bytes(self.graph))
                self.value["assets"]["sha256"] = evidence.file_sha256(self.assets)
                self.request.write_bytes(evidence.canonical_bytes(self.value))
                code, event = self.invoke()
                self.assertEqual(code, expected)
                self.assertEqual(event["code"], "None" if expected == 0 else "EvidenceSchemaInvalid")
                self.assertEqual(self.output.exists(), expected == 0)

    def test_managed_content_tool_rejects_duplicate_request_fields_and_foreign_paths(self):
        original = self.request.read_bytes()
        self.request.write_bytes(original[:-1] + b',"schemaVersion":1}')
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "EvidenceSchemaInvalid"))
        self.value["assets"]["path"] = "../outside-canary"
        self.request.write_bytes(evidence.canonical_bytes(self.value))
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "OwnershipInvalid"))
        self.assertFalse(self.output.exists())

    def test_managed_content_tool_rejects_linked_archives_without_altering_outside_canary(self):
        outside = self.parent / "outside-private-canary"
        outside.write_bytes(b"private-canary")
        self.archive.unlink()
        self.archive.symlink_to(outside)
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "OwnershipInvalid"))
        self.assertEqual(outside.read_bytes(), b"private-canary")
        self.assertFalse(self.output.exists())

    def test_managed_content_tool_rejects_foreign_archive_metadata_and_oversized_assets(self):
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("Foreign.nuspec", (
                "<package><metadata><id>Foreign</id><version>2.4.0-preview.1</version></metadata></package>"))
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "InputChanged"))
        self.assets.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "OutputLimitExceeded"))
        self.assertFalse(self.output.exists())

    def pdb_request(self):
        image_directory = self.case / "image"
        image_directory.mkdir()
        name = "Hoard.Fixtures.Conformance.BuildInputs"
        image, pdb = image_directory / (name + ".dll"), image_directory / (name + ".pdb")
        for path in (image, pdb):
            shutil.copyfile(self.tool.parent / path.name, path)
        value = {
            "schemaVersion": 1, "qualification": False,
            "sourcePath": self.relative(self.source), "generatedPath": self.relative(self.generated),
            "outputRoot": self.relative(image_directory),
            "project": "tests/fixtures/conformance/BuildInputs/BuildInputs.csproj",
            "assembly": {"path": image.name, "sha256": evidence.file_sha256(image)},
            "pdb": {"path": pdb.name, "sha256": evidence.file_sha256(pdb)},
            "outputPath": self.relative(self.output_receipt)}
        self.request.write_bytes(evidence.canonical_bytes(value))
        return value, image, pdb

    @property
    def output_receipt(self):
        return self.case / "documents.json"

    def test_managed_pdb_tool_binds_actual_image_and_document_checksums_without_output_reuse(self):
        value, _, _ = self.pdb_request()
        code, event = self.invoke(operation="pdb-documents")
        self.assertEqual(code, 0)
        receipt = evidence.load_json(self.output_receipt.read_bytes())
        self.assertEqual(event, {"event": "control", "code": "None", "value": len(receipt["documents"])})
        self.assertEqual(receipt["assembly"], value["assembly"])
        self.assertEqual(receipt["pdb"], value["pdb"])
        self.assertEqual(receipt["project"], value["project"])
        self.assertIn("source/tests/fixtures/conformance/BuildInputs/Program.cs", receipt["documents"])
        self.assertTrue(any(path.startswith("generated/") for path in receipt["documents"]))
        for identity, hashed in receipt["documents"].items():
            namespace, relative = identity.split("/", 1)
            root = self.source if namespace == "source" else self.generated
            self.assertEqual(hashed, evidence.file_sha256(root / relative))
        original = self.output_receipt.read_bytes()
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "OwnershipInvalid")
        self.assertEqual(self.output_receipt.read_bytes(), original)

    def test_managed_pdb_tool_rejects_rehashed_checksum_tamper_and_changed_source(self):
        value, _, pdb = self.pdb_request()
        original = pdb.read_bytes()
        pdb.write_bytes(original + b"checksum-tamper")
        value["pdb"]["sha256"] = evidence.file_sha256(pdb)
        self.request.write_bytes(evidence.canonical_bytes(value))
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "ProofMismatch")
        self.assertFalse(self.output_receipt.exists())
        pdb.write_bytes(original)
        value["pdb"]["sha256"] = evidence.file_sha256(pdb)
        self.request.write_bytes(evidence.canonical_bytes(value))
        path = self.source / "tests/fixtures/conformance/BuildInputs/Program.cs"
        source = path.read_bytes()
        try:
            path.write_bytes(source + b"\n")
            self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "InputChanged")
            self.assertFalse(self.output_receipt.exists())
        finally:
            path.write_bytes(source)

    def test_managed_pdb_tool_rejects_foreign_paths_links_and_request_changes(self):
        value, _, pdb = self.pdb_request()
        self.assertEqual(self.invoke(operation="pdb-documents", digest="a" * 64)[1]["code"], "InputChanged")
        value["pdb"]["path"] = "../outside-private-canary"
        self.request.write_bytes(evidence.canonical_bytes(value))
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "OwnershipInvalid")
        outside = self.parent / "outside-private-pdb"
        shutil.copyfile(pdb, outside)
        pdb.unlink()
        pdb.symlink_to(outside)
        value["pdb"]["path"] = pdb.name
        self.request.write_bytes(evidence.canonical_bytes(value))
        before = evidence.file_sha256(outside)
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "OwnershipInvalid")
        self.assertEqual(evidence.file_sha256(outside), before)
        self.assertFalse(self.output_receipt.exists())

    def evaluation_request(self):
        source = self.case / "evaluation-source"
        (source / "Adapter").mkdir(parents=True)
        (source / "Shared").mkdir()
        inputs = {
            "Directory.Build.props": '<Project><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup>'
                '<Import Project="Release.props" Condition="\'$(Configuration)\' == \'Release\'" /></Project>',
            "Release.props": '<Project><ItemGroup><Compile Include="$(MSBuildThisFileDirectory)Injected.cs" /></ItemGroup></Project>',
            "Injected.cs": "public class Injected { }\n",
            "Adapter/Adapter.csproj": '<Project Sdk="Microsoft.NET.Sdk"><ItemGroup>'
                '<ProjectReference Include="../Shared/Shared.csproj" /></ItemGroup></Project>',
            "Adapter/Binding.cs": "public class Binding { }\n",
            "Adapter/Empty.txt": "",
            "Shared/Shared.csproj": '<Project Sdk="Microsoft.NET.Sdk" />',
            "Shared/Shared.cs": "public class Shared { }\n"}
        for relative, text in inputs.items():
            (source / relative).write_text(text)
        code, raw = capture_control(["dotnet", "--version"], cwd=self.source,
                                    env=self.environment, limit=128, timeout=30)
        self.assertEqual(code, 0)
        version = raw.decode("ascii").strip()
        self.assertRegex(version, r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
        code, raw = capture_control(["dotnet", "--list-sdks"], cwd=self.source,
                                    env=self.environment, limit=4096, timeout=30)
        self.assertEqual(code, 0)
        matches = [re.fullmatch(re.escape(version) + r" \[([^\r\n]+)\]", line)
                   for line in raw.decode("utf-8").splitlines()]
        selected = [match[1] for match in matches if match is not None]
        self.assertEqual(len(selected), 1)
        toolchain = Path(selected[0]).resolve().parent
        self.msbuild = Path(selected[0]).resolve() / version / "MSBuild.dll"
        code, raw = capture_control(["dotnet", "--list-runtimes"], cwd=self.source,
                                    env=self.environment, limit=4096, timeout=30)
        self.assertEqual(code, 0)
        runtimes = [re.fullmatch(r"Microsoft\.NETCore\.App (10\.0\.[0-9]+) \[[^\r\n]+\]", line)
                    for line in raw.decode("utf-8").splitlines()]
        installed = [match[1] for match in runtimes if match is not None]
        self.assertTrue(installed)
        self.runtime_version = max(installed, key=lambda version: tuple(map(int, version.split("."))))
        receipt = self.case / "evaluation.json"
        value = {"schemaVersion": 1, "qualification": False, "sourcePath": self.relative(source),
                 "project": "Adapter/Adapter.csproj", "toolchainRoot": str(toolchain),
                 "sources": dict(evidence.input_manifest(source, sorted(inputs))),
                 "outputPath": self.relative(receipt)}
        self.request.write_bytes(evidence.canonical_bytes(value))
        return value, source, receipt

    def evaluate(self, *, digest=None):
        driver = self.case / "evaluation.proj"
        document = ET.Element("Project")
        name = "Hoard.Fixtures.Conformance.BuildInputs.ReadBindingInputs"
        ET.SubElement(document, "UsingTask", TaskName=name, AssemblyFile=str(self.tool))
        target = ET.SubElement(document, "Target", Name="Capture")
        ET.SubElement(target, name, OwnedRootBase64=base64.b64encode(str(self.owner.root).encode()).decode(),
                      RequestPath=self.relative(self.request),
                      RequestSha256=evidence.file_sha256(self.request) if digest is None else digest)
        driver.write_bytes(ET.tostring(document, encoding="utf-8"))
        code, raw = capture_control(
            ["dotnet", "exec", "--fx-version", self.runtime_version, str(self.msbuild), str(driver),
             "-target:Capture", "-noconsolelogger", "-nologo",
             "-nodeReuse:false", "-verbosity:quiet"],
            cwd=self.source, env={**self.environment, "DOTNET_ROLL_FORWARD": "Disable"}, limit=4096, timeout=60)
        try:
            event = evidence.load_json(raw)
        except evidence.ConformanceError:
            raise AssertionError("Managed evaluation task emitted no safe control event") from None
        return code, event

    def test_managed_evaluation_task_observes_conditional_imports_and_referenced_project_sources(self):
        value, source, receipt = self.evaluation_request()
        code, event = self.evaluate()
        self.assertEqual(code, 0)
        captured = evidence.load_json(receipt.read_bytes())
        rows = captured["Items"]["_BindingInputs"]
        self.assertEqual(event, {"event": "control", "code": "None", "value": len(rows)})
        identities = {row["Identity"] for row in rows}
        self.assertTrue({"source/Release.props", "source/Injected.cs", "source/Shared/Shared.csproj",
                         "source/Shared/Shared.cs", "source/Adapter/Binding.cs", "source/Adapter/Empty.txt"} <= identities)
        self.assertTrue(any(path.startswith("toolchain/") for path in identities))
        self.assertTrue(all(set(row) == {"Identity", "Kind", "Sha256"} for row in rows))
        binding = contributors.BindingProject(source, value["project"], {}, value["sources"])
        admitted = contributors.binding_evaluation_inputs(binding, receipt.read_bytes(), Path(value["toolchainRoot"]))
        self.assertIn("Adapter/Empty.txt", admitted["sources"])
        rows[0]["Sha256"] = "a" * 64
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_evaluation_inputs(
                binding, evidence.canonical_bytes(captured), Path(value["toolchainRoot"]))
        self.assertEqual(self.evaluate()[1]["code"], "OwnershipInvalid")

    def test_managed_evaluation_task_rejects_changed_requests_sources_and_undeclared_ambient_inputs(self):
        value, source, receipt = self.evaluation_request()
        self.assertEqual(self.evaluate(digest="a" * 64)[1]["code"], "InputChanged")
        path = source / "Adapter/Binding.cs"
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        self.assertEqual(self.evaluate()[1]["code"], "InputChanged")
        path.write_bytes(original)
        (source / "Adapter/Ambient.cs").write_text("public class Ambient { }\n")
        self.assertEqual(self.evaluate()[1]["code"], "EvidenceIncomplete")
        self.assertFalse(receipt.exists())

    def compiler_request(self, *, change_after_compile=False):
        value, source, _ = self.evaluation_request()
        generated, packages = self.case / "compiler-build", self.case / "compiler-packages"
        generated.mkdir()
        packages.mkdir()
        (source / "Adapter/extra.txt").write_text("private-additional-file-canary")
        (source / "Adapter/resource.txt").write_text("private-resource-canary")
        project = source / "Adapter/Adapter.csproj"
        document = ET.parse(project)
        group = ET.SubElement(document.getroot(), "ItemGroup")
        ET.SubElement(group, "AdditionalFiles", Include="extra.txt")
        ET.SubElement(group, "EmbeddedResource", Include="resource.txt", LogicalName="Acme.Resource")
        document.write(project)
        targets = ET.Element("Project")
        target = ET.SubElement(targets, "Target", Name="GenerateInput", BeforeTargets="CoreCompile")
        ET.SubElement(target, "WriteLinesToFile", File="$(IntermediateOutputPath)Dynamic.cs",
                      Lines="public class Dynamic { }", Overwrite="true")
        ET.SubElement(ET.SubElement(target, "ItemGroup"), "Compile", Include="$(IntermediateOutputPath)Dynamic.cs")
        if change_after_compile:
            target = ET.SubElement(targets, "Target", Name="ChangeInput", AfterTargets="CoreCompile")
            ET.SubElement(target, "WriteLinesToFile", File="$(IntermediateOutputPath)Dynamic.cs",
                          Lines="private-postcompile-canary", Overwrite="true")
        ET.ElementTree(targets).write(source / "Directory.Build.targets")
        properties = generated / "compiler.props"
        props = ET.Element("Project")
        group = ET.SubElement(props, "PropertyGroup")
        for name, text in {
                "BaseIntermediateOutputPath": str(generated) + "/$(MSBuildProjectName)/obj/",
                "BaseOutputPath": str(generated) + "/$(MSBuildProjectName)/bin/",
                "EmitCompilerGeneratedFiles": "true",
                "CompilerGeneratedFilesOutputPath": str(generated) + "/$(MSBuildProjectName)/compiler-generated",
                "CscToolPath": "", "CscToolExe": "",
                "RestorePackagesPath": str(packages), "UseSharedCompilation": "false"}.items():
            ET.SubElement(group, name).text = text
        ET.ElementTree(props).write(properties)
        sources = evidence.proof_manifest(source)
        outputs = {kind: self.relative(self.case / (kind + ".json"))
                   for kind in ("sources", "inputs", "parameters")}
        request = {
            "schemaVersion": 1, "qualification": False, "sourcePath": self.relative(source),
            "generatedPath": self.relative(generated), "packagePath": self.relative(packages),
            "toolchainRoot": value["toolchainRoot"], "sourceHashes": sources, "outputs": outputs}
        self.request.write_bytes(evidence.canonical_bytes(request))
        code, _ = capture_control(
            ["dotnet", "restore", str(project), "--configfile", str(self.owner.root / "NuGet.Config"),
             "-p:CustomAfterDirectoryBuildProps=" + str(properties), "-p:UseSharedCompilation=false",
             "-nodeReuse:false", "-verbosity:quiet"],
            cwd=self.source, env=self.environment, limit=65536, timeout=60)
        self.assertEqual(code, 0)
        self.compiler_project, self.compiler_properties = project, properties
        return request, contributors.BindingProject(source, "Adapter/Adapter.csproj", {}, sources), generated, packages

    def compile(self, *, digest=None, typed_inputs=True):
        parameters = ";".join((
            base64.b64encode(str(self.owner.root).encode()).decode(), self.relative(self.request),
            evidence.file_sha256(self.request) if digest is None else digest))
        logger = ("-logger:Hoard.Fixtures.Conformance.BuildInputs.CompilerInputsLogger,"
                  + str(self.tool) + ";" + parameters)
        code, raw = capture_control(
            ["dotnet", "exec", "--fx-version", self.runtime_version, str(self.msbuild), str(self.compiler_project),
             "-target:Build", "-p:Configuration=Release", "-p:UseSharedCompilation=false",
             "-p:CustomAfterDirectoryBuildProps=" + str(self.compiler_properties),
             "-nodeReuse:false", "-maxCpuCount:1", "-noconsolelogger", "-nologo", "-verbosity:minimal", logger],
            cwd=self.source, env={**self.environment, "DOTNET_ROLL_FORWARD": "Disable",
                                  **({"MSBUILDLOGTASKINPUTS": "1", "MSBUILDLOGIMPORTS": "1"} if typed_inputs else {})},
            limit=4096, timeout=60)
        try:
            event = evidence.load_json(raw)
        except evidence.ConformanceError:
            raise AssertionError("Managed compiler observer emitted no safe control event") from None
        return code, event

    def test_managed_compiler_observer_captures_actual_sources_inputs_command_and_item_metadata(self):
        value, binding, generated, packages = self.compiler_request()
        code, event = self.compile()
        self.assertEqual(code, 0)
        self.assertEqual(event, {"event": "control", "code": "None", "value": 2})
        raw = {kind: (self.owner.root / path).read_bytes() for kind, path in value["outputs"].items()}
        sources = contributors.binding_compilation_sources(binding, raw["sources"], generated)
        self.assertEqual(len(sources["compilations"]), 2)
        for row in sources["compilations"]:
            compiled = row["compiledOutputs"]
            self.assertEqual(set(compiled), {"assembly", "pdb"})
            for kind, suffix in (("assembly", ".dll"), ("pdb", ".pdb")):
                self.assertTrue(compiled[kind]["path"].endswith(suffix))
                self.assertEqual(compiled[kind]["sha256"], evidence.file_sha256(
                    generated / compiled[kind]["path"].removeprefix("generated/")))
        self.assertTrue(any("Dynamic.cs" in path for row in sources["compilations"] for path in row["sources"]))
        inputs = contributors.binding_build_file_inputs(
            binding, raw["inputs"], generated, Path(value["toolchainRoot"]), packages, {})
        self.assertTrue(any(path.endswith("/Microsoft.Build.Tasks.CodeAnalysis.dll") for path in inputs["tools"]))
        self.assertTrue(all(path.startswith("toolchain/") for path in inputs["tools"]))
        self.assertTrue(any(path.endswith("/Roslyn/bincore/csc.deps.json") for path in inputs["supportFiles"]))
        self.assertTrue(any(path.endswith("/System.Text.RegularExpressions.Generator.dll")
                            for path in inputs["supportFiles"]))
        self.assertTrue(any("/shared/Microsoft.NETCore.App/" in path and path.endswith("/System.Net.Http.dll")
                            for path in inputs["supportFiles"]))
        self.assertTrue(any("/host/fxr/" in path for path in inputs["supportFiles"]))
        changed = evidence.load_json(raw["inputs"])
        first = next(iter(changed["tools"]))
        changed["tools"][first] = "a" * 64
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_build_file_inputs(
                binding, evidence.canonical_bytes(changed), generated, Path(value["toolchainRoot"]), packages, {})
        self.assertTrue(any(row["inputs"].get("AdditionalFiles") for row in inputs["compilations"]))
        self.assertTrue(any(row["inputs"].get("Resources") for row in inputs["compilations"]))
        parameters = contributors.binding_compiler_parameter_inputs(inputs["compilations"], raw["parameters"])
        self.assertEqual(len(parameters["compilations"]), 2)
        self.assertEqual(self.compile()[1]["code"], "OwnershipInvalid")
        self.assertEqual({kind: (self.owner.root / path).read_bytes() for kind, path in value["outputs"].items()}, raw)

    def test_managed_compiler_observer_rejects_postcompile_generated_source_changes(self):
        value, _, _, _ = self.compiler_request(change_after_compile=True)
        _, event = self.compile()
        self.assertEqual(event["code"], "InputChanged")
        self.assertFalse(any((self.owner.root / path).exists() for path in value["outputs"].values()))

    def test_managed_pdb_tool_maps_only_explicit_repository_prefix_to_owned_recorded_sources(self):
        value, binding, generated, _ = self.compiler_request()
        properties = ET.parse(self.compiler_properties)
        ET.SubElement(properties.find(".//PropertyGroup"), "PathMap").text = (
            str(binding.root) + "/=/_/," + str(generated) + "/=/_generated/")
        properties.write(self.compiler_properties)
        self.assertEqual(self.compile()[1]["code"], "None")
        rows = contributors.binding_compilation_sources(
            binding, (self.owner.root / value["outputs"]["sources"]).read_bytes(), generated)
        row = next(item for item in rows["compilations"] if item["project"] == binding.project)
        output = generated / "Adapter/bin/Release/net10.0"
        request = {
            "schemaVersion": 1, "qualification": False, "sourcePath": self.relative(binding.root),
            "generatedPath": self.relative(generated), "project": binding.project,
            "outputRoot": self.relative(output),
            "assembly": {"path": "Adapter.dll", "sha256": evidence.file_sha256(output / "Adapter.dll")},
            "pdb": {"path": "Adapter.pdb", "sha256": evidence.file_sha256(output / "Adapter.pdb")},
            "outputPath": self.relative(self.output_receipt)}
        self.request.write_bytes(evidence.canonical_bytes(request))
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "OwnershipInvalid")
        for prefix in ("/foreign/", "../", None, 1):
            self.request.write_bytes(evidence.canonical_bytes({**request, "sourceDocumentPrefix": prefix}))
            with self.subTest(prefix=prefix):
                self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "EvidenceSchemaInvalid")
                self.assertFalse(self.output_receipt.exists())
        self.request.write_bytes(evidence.canonical_bytes({**request, "sourceDocumentPrefix": "/_/"}))
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "OwnershipInvalid")
        for prefix in ("/foreign/", "../", None, 1):
            self.request.write_bytes(evidence.canonical_bytes({
                **request, "sourceDocumentPrefix": "/_/", "generatedDocumentPrefix": prefix}))
            with self.subTest(generatedPrefix=prefix):
                self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "EvidenceSchemaInvalid")
                self.assertFalse(self.output_receipt.exists())
        self.request.write_bytes(evidence.canonical_bytes({**request, "generatedDocumentPrefix": "/_generated/"}))
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "EvidenceSchemaInvalid")
        self.request.write_bytes(evidence.canonical_bytes({
            **request, "sourceDocumentPrefix": "/_/", "generatedDocumentPrefix": "/_generated/"}))
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "None")
        admitted = contributors.binding_compilation_documents(
            row, self.output_receipt.read_bytes(), output, "Adapter.dll")
        self.assertTrue(any(path.startswith("source/") for path in admitted["documents"]))
        generated_name = next(path for path in admitted["documents"] if path.startswith("generated/"))
        self.output_receipt.unlink()
        path = binding.root / "Adapter/Binding.cs"
        original = path.read_bytes()
        outside = self.parent / "mapped-pdb-outside-canary"
        outside.write_bytes(original)
        path.unlink()
        path.symlink_to(outside)
        try:
            self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "OwnershipInvalid")
            self.assertEqual(outside.read_bytes(), original)
            self.assertFalse(self.output_receipt.exists())
        finally:
            path.unlink()
            path.write_bytes(original)
            outside.unlink()
        path = generated / generated_name.removeprefix("generated/")
        original = path.read_bytes()
        outside = self.parent / "mapped-generated-pdb-outside-canary"
        outside.write_bytes(original)
        path.unlink()
        path.symlink_to(outside)
        try:
            self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "OwnershipInvalid")
            self.assertEqual(outside.read_bytes(), original)
            self.assertFalse(self.output_receipt.exists())
        finally:
            path.unlink()
            path.write_bytes(original)
            outside.unlink()

    def test_managed_compiler_observer_rejects_output_image_changes_after_csc_completion(self):
        value, binding, _, _ = self.compiler_request()
        targets = ET.parse(binding.root / "Directory.Build.targets")
        target = ET.SubElement(targets.getroot(), "Target", Name="ChangeCompiledImage", AfterTargets="CoreCompile",
                               Condition="'$(MSBuildProjectName)' == 'Adapter'")
        ET.SubElement(target, "WriteLinesToFile",
                      File="$(IntermediateOutputPath)$(TargetName)$(TargetExt)",
                      Lines="private-changed-compiled-image", Overwrite="true")
        targets.write(binding.root / "Directory.Build.targets")
        value["sourceHashes"] = evidence.proof_manifest(binding.root)
        self.request.write_bytes(evidence.canonical_bytes(value))
        _, event = self.compile()
        self.assertEqual(event["code"], "InputChanged")
        self.assertFalse(any((self.owner.root / path).exists() for path in value["outputs"].values()))

    def test_managed_compiler_observer_captures_roslyn_generator_outputs_separately(self):
        value, binding, generated, _ = self.compiler_request()
        (binding.root / "Adapter/Binding.cs").write_text(
            'using System.Text.RegularExpressions;\n'
            'public partial class Binding {\n'
            '    [GeneratedRegex("a+")] public static partial Regex Pattern();\n}\n')
        value["sourceHashes"] = evidence.proof_manifest(binding.root)
        binding = contributors.BindingProject(binding.root, binding.project, {}, value["sourceHashes"])
        self.request.write_bytes(evidence.canonical_bytes(value))
        code, event = self.compile()
        self.assertEqual(code, 0)
        self.assertEqual(event["code"], "None")
        raw = (self.owner.root / value["outputs"]["sources"]).read_bytes()
        result = contributors.binding_compilation_sources(binding, raw, generated)
        row = next(row for row in result["compilations"] if row["project"] == binding.project)
        self.assertEqual(len(row["generatedOutputs"]), 1)
        self.assertFalse(row["sources"].keys() & row["generatedOutputs"].keys())
        path = next(iter(row["generatedOutputs"]))
        self.assertIn("RegexGenerator", path)
        image_directory = generated / "Adapter/bin/Release/net10.0"
        image, pdb = image_directory / "Adapter.dll", image_directory / "Adapter.pdb"
        self.request.write_bytes(evidence.canonical_bytes({
            "schemaVersion": 1, "qualification": False, "sourcePath": self.relative(binding.root),
            "generatedPath": self.relative(generated), "project": binding.project,
            "outputRoot": self.relative(image_directory),
            "assembly": {"path": image.name, "sha256": evidence.file_sha256(image)},
            "pdb": {"path": pdb.name, "sha256": evidence.file_sha256(pdb)},
            "outputPath": self.relative(self.output_receipt)}))
        code, event = self.invoke(operation="pdb-documents")
        self.assertEqual(code, 0)
        receipt = contributors.binding_compilation_documents(
            row, self.output_receipt.read_bytes(), image_directory, image.name)
        self.assertIn(path, receipt["documents"])
        self.assertEqual(receipt["generatedOutputsSha256"], evidence.digest(row["generatedOutputs"]))
        self.assertEqual(receipt["assembly"]["sha256"], row["compiledOutputs"]["assembly"]["sha256"])
        self.assertEqual(receipt["pdb"]["sha256"], row["compiledOutputs"]["pdb"]["sha256"])
        changed = dict(row)
        changed["generatedOutputs"] = {}
        with self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
            contributors.binding_compilation_documents(
                changed, self.output_receipt.read_bytes(), image_directory, image.name)
        physical = generated / path.removeprefix("generated/")
        physical.write_bytes(physical.read_bytes() + b"\n")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_compilation_sources(binding, raw, generated)

    def test_managed_compiler_observer_rejects_reused_or_foreign_generator_output_directories(self):
        value, _, generated, _ = self.compiler_request()
        directory = generated / "Shared/compiler-generated"
        directory.mkdir(parents=True)
        (directory / "preexisting.cs").write_text("private-preexisting-canary")
        _, event = self.compile()
        self.assertEqual(event["code"], "OwnershipInvalid")
        self.assertFalse(any((self.owner.root / path).exists() for path in value["outputs"].values()))
        (directory / "preexisting.cs").unlink()
        properties = ET.parse(self.compiler_properties)
        properties.find(".//CompilerGeneratedFilesOutputPath").text = str(self.parent / "foreign-generator-output")
        properties.write(self.compiler_properties)
        _, event = self.compile()
        self.assertEqual(event["code"], "OwnershipInvalid")
        self.assertFalse(any((self.owner.root / path).exists() for path in value["outputs"].values()))

    def test_managed_compiler_observer_rejects_generator_tree_changes_after_compilation(self):
        value, binding, generated, _ = self.compiler_request()
        targets = ET.parse(binding.root / "Directory.Build.targets")
        target = ET.SubElement(targets.getroot(), "Target", Name="ChangeGeneratorOutput", AfterTargets="CoreCompile")
        ET.SubElement(target, "WriteLinesToFile",
                      File="$(CompilerGeneratedFilesOutputPath)/late.cs", Lines="private-late-canary", Overwrite="true")
        targets.write(binding.root / "Directory.Build.targets")
        value["sourceHashes"] = evidence.proof_manifest(binding.root)
        self.request.write_bytes(evidence.canonical_bytes(value))
        _, event = self.compile()
        self.assertEqual(event["code"], "InputChanged")
        self.assertFalse(any((self.owner.root / path).exists() for path in value["outputs"].values()))

    def test_managed_compiler_observer_rejects_changed_analyzer_support_files(self):
        value, binding, generated, _ = self.compiler_request()
        directory = generated / "analyzer-inputs"
        directory.mkdir()
        candidates = sorted((Path(value["toolchainRoot"]) / "packs").glob(
            "Microsoft.NETCore.App.Ref/*/analyzers/dotnet/cs/System.Text.RegularExpressions.Generator.dll"))
        self.assertTrue(candidates)
        analyzer = directory / "Acme.SupportProbe.dll"
        shutil.copyfile(candidates[-1], analyzer)
        dependency = directory / "dependency.json"
        dependency.write_text('{"value":"original"}')
        project = ET.parse(self.compiler_project)
        ET.SubElement(ET.SubElement(project.getroot(), "ItemGroup"), "Analyzer", Include=str(analyzer))
        project.write(self.compiler_project)
        targets = ET.parse(binding.root / "Directory.Build.targets")
        target = ET.SubElement(targets.getroot(), "Target", Name="ChangeAnalyzerSupport", AfterTargets="CoreCompile",
                               Condition="'$(MSBuildProjectName)' == 'Adapter'")
        ET.SubElement(target, "WriteLinesToFile", File=str(dependency), Lines="private-changed-support", Overwrite="true")
        targets.write(binding.root / "Directory.Build.targets")
        value["sourceHashes"] = evidence.proof_manifest(binding.root)
        self.request.write_bytes(evidence.canonical_bytes(value))
        _, event = self.compile()
        self.assertEqual(event["code"], "InputChanged")
        self.assertFalse(any((self.owner.root / path).exists() for path in value["outputs"].values()))

    def test_managed_compiler_observer_rejects_custom_compiler_selection(self):
        value, _, _, _ = self.compiler_request()
        properties = ET.parse(self.compiler_properties)
        properties.find(".//CscToolExe").text = "private-custom-compiler-canary"
        properties.write(self.compiler_properties)
        _, event = self.compile()
        self.assertEqual(event["code"], "OwnershipInvalid")
        self.assertFalse(any((self.owner.root / path).exists() for path in value["outputs"].values()))

    def test_managed_compiler_observer_rejects_changed_request_without_success_receipts(self):
        value, _, _, _ = self.compiler_request()
        _, event = self.compile(digest="a" * 64)
        self.assertEqual(event["code"], "InputChanged")
        _, event = self.compile(typed_inputs=False)
        self.assertEqual(event["code"], "PrerequisiteMissing")
        self.assertFalse(any((self.owner.root / path).exists() for path in value["outputs"].values()))

    def captured_build(self, *, change_after_pack=False, shared=False, change_dependency_after_pack=False,
                       ambient_sdk=False, native=False, nonpackable=False, package_mutation=None,
                       change_tool_after_restore=False):
        measured, _, _ = self.evaluation_request()
        if ambient_sdk:
            (self.case / "global.json").write_bytes(evidence.canonical_bytes({
                "sdk": {"version": "99.0.999", "rollForward": "disable"}}))
        source = self.case / "build-author"
        source.mkdir()
        (source / "Adapter.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
            '<TargetFramework>net10.0</TargetFramework><PackageId>Acme.Adapter</PackageId>'
            '<AssemblyName>Acme.Emitted</AssemblyName><Version>2.4.0-preview.1</Version>'
            '</PropertyGroup><ItemGroup>'
            '<PackageReference Include="Acme.BuildInputs" Version="3.2.1" PrivateAssets="all" />'
            + ('<Compile Remove="Shared/**/*.cs" /><ProjectReference Include="Shared/Shared.csproj" />' if shared else '')
            + '</ItemGroup></Project>')
        (source / "Binding.cs").write_text(
            "public class Binding { public int Value => "
            + ("new Shared.Dependency().Value" if shared else "7") + "; }\n")
        if shared:
            (source / "Shared").mkdir()
            (source / "Shared/Shared.csproj").write_text(
                '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
                '<TargetFramework>net10.0</TargetFramework><AssemblyName>Acme.Shared.Emitted</AssemblyName>'
                '<PackageId>Acme.Shared.Package</PackageId><Version>3.1.0</Version>'
                + ('<IsPackable>false</IsPackable>' if nonpackable else '')
                + '</PropertyGroup></Project>')
            (source / "Shared/Dependency.cs").write_text(
                "namespace Shared; public class Dependency { public int Value => 7; }\n")
            (source / "Shared/packages.lock.json").write_bytes(evidence.canonical_bytes({
                "version": 2, "dependencies": {"net10.0": {}}}))
        dependency = self.case / "Acme.BuildInputs.3.2.1.nupkg"
        package_members = {
            "build/Acme.BuildInputs.props": (
                b'<Project><ItemGroup><AdditionalFiles Include="$(MSBuildThisFileDirectory)info.txt" />'
                b'</ItemGroup></Project>'),
            "build/info.txt": b"private-compiler-input"}
        with zipfile.ZipFile(dependency, "w") as archive:
            archive.writestr("Acme.BuildInputs.nuspec", (
                '<package><metadata><id>Acme.BuildInputs</id><version>3.2.1</version>'
                '<authors>Hoard fixture</authors><description>Build-only fixture</description></metadata></package>'))
            for name, data in package_members.items():
                archive.writestr(name, data)
        dependencies = {"Acme.BuildInputs": {
                "type": "Direct", "requested": "[3.2.1, )", "resolved": "3.2.1",
                "contentHash": base64.b64encode(hashlib.sha512(dependency.read_bytes()).digest()).decode()}}
        if shared:
            dependencies["Acme.Shared.Package"] = {"type": "Project"}
        (source / "packages.lock.json").write_bytes(evidence.canonical_bytes({
            "version": 2, "dependencies": {"net10.0": dependencies}}))
        adapter = {"packageId": "Acme.Adapter", "version": "2.4.0-preview.1", "assemblyName": "Acme.Emitted"}
        registration = {
            "schemaVersion": 1, "project": "Adapter.csproj", "factoryType": "Acme.Binding",
            "adapterPackage": adapter,
            "declaration": {
                "schemaVersion": 1, "bindingId": "acme.metadata", "category": "metadata",
                "packageId": "Acme.Provider", "packageVersion": "0.1.0",
                "capabilities": ["metadata", "non-durable"],
                "faults": sorted(evidence._BINDING_REQUIRED_FAULTS["metadata"])},
            "components": {role: dict(adapter) for role in evidence._SESSION_ROLES["metadata"]},
            "sourceFiles": ["Adapter.csproj", "Adapter.conformance.json", "Binding.cs", "packages.lock.json"]}
        if shared:
            registration["sourceFiles"].extend(
                ["Shared/Shared.csproj", "Shared/Dependency.cs", "Shared/packages.lock.json"])
        (source / "Adapter.conformance.json").write_bytes(evidence.canonical_bytes(registration))
        admitted = contributors.admit_binding_project(source / "Adapter.csproj", "metadata")
        owner = OwnedRun.allocate(self.case / "captured-run", ROOT, profile="harness")
        binding = contributors.snapshot_binding_project(
            source / "Adapter.csproj", "metadata", admitted.inputs_sha256, owner)
        config, feed, tools = owner.root / "NuGet.Config", owner.root / "feed", owner.root / "tools"
        configuration = ET.Element("configuration")
        sources = ET.SubElement(configuration, "packageSources")
        ET.SubElement(sources, "clear")
        ET.SubElement(sources, "add", key="fixture", value=str(feed))
        config.write_bytes(ET.tostring(configuration, encoding="utf-8"))
        config.chmod(0o400)
        shutil.copyfile(dependency, feed / dependency.name)
        shutil.copytree(self.tool.parent, tools)
        tool = tools / self.tool.name
        commands = []
        native_command = owner.command

        def execute(arguments, *, cwd, cache_id, kind, timeout=600, env=None):
            if native:
                result = native_command(
                    arguments, cwd=cwd, cache_id=cache_id, kind=kind, timeout=timeout, env=env)
                code = result.exit_code
            else:
                cache = owner.root / "cache" / cache_id
                (cache / "tmp").mkdir(parents=True, exist_ok=True)
                environment = command_environment(owner.root, cache, env)
                if kind == "build":
                    # This managed component measures the installed runtime, not native confinement.
                    environment["DOTNET_ROLL_FORWARD"] = "LatestPatch"
                code, raw = capture_control(
                    arguments, cwd=cwd, env=environment, limit=65536, timeout=min(timeout, 120))
                if kind == "events":
                    events = (evidence.load_json(raw),)
                else:
                    from conformance_execution import project_build_line
                    events = tuple(project_build_line(line) for line in raw.splitlines() if line.strip())
                result = mock.Mock(exit_code=code, events=events)
            commands.append(tuple(arguments))
            if change_tool_after_restore and "-target:Restore" in arguments and code == 0:
                support = tool.with_name("NuGet.Versioning.dll")
                support.chmod(0o600)
                support.write_bytes(support.read_bytes() + b"changed-between-producer-phases")
            packing = arguments[1] == "pack" or "-target:Pack" in arguments
            if packing and code == 0 and change_after_pack:
                path = feed / "Acme.Adapter.2.4.0-preview.1.nupkg"
                with zipfile.ZipFile(path) as archive:
                    members = {member: archive.read(member) for member in archive.namelist()}
                members["lib/net10.0/Acme.Emitted.dll"] += b"changed-after-compile"
                with zipfile.ZipFile(path, "w") as archive:
                    for member, data in members.items():
                        archive.writestr(member, data)
            if packing and code == 0 and change_dependency_after_pack:
                project_hash = hashlib.sha256(b"Shared/Shared.csproj").hexdigest()
                path = (owner.root / "stores/binding-build" / project_hash
                        / "obj/Release/net10.0/Acme.Shared.Emitted.dll")
                path.write_bytes(path.read_bytes() + b"changed-dependency-after-pack")
            if packing and code == 0 and package_mutation:
                shared_archive = feed / "Acme.Shared.Package.3.1.0.nupkg"
                if shared_archive.exists():
                    if package_mutation == "image":
                        with zipfile.ZipFile(shared_archive) as archive:
                            members = {member: archive.read(member) for member in archive.namelist()}
                        members["lib/net10.0/Acme.Shared.Emitted.dll"] += b"not-the-observed-csc-image"
                        with zipfile.ZipFile(shared_archive, "w") as archive:
                            for member, data in members.items():
                                archive.writestr(member, data)
                    elif package_mutation == "feed":
                        path = feed / dependency.name
                        path.write_bytes(path.read_bytes() + b"changed-unrelated-archive")
            return result

        try:
            with mock.patch.object(owner, "command", side_effect=execute):
                result = contributors.build_captured_binding_project(
                    binding, owner, config, feed, tool, Path(measured["toolchainRoot"]),
                    self.msbuild.parent.name, self.runtime_version)
            self.assertEqual(len(commands), (8 if nonpackable else 9) if shared else 6)
            if ambient_sdk:
                for target in ("Restore", "Pack"):
                    selected = [command for command in commands if "-target:" + target in command]
                    self.assertEqual(len(selected), 1)
                    self.assertEqual(selected[0][:5], (
                        "dotnet", "exec", "--fx-version", self.runtime_version, str(self.msbuild)))
            self.assertEqual(result["package"]["packageId"], "Acme.Adapter")
            self.assertFalse(result["qualification"])
            projects = {binding.project, "Shared/Shared.csproj"} if shared else {binding.project}
            self.assertEqual(set(result["graphs"]), projects)
            self.assertEqual(set(result["documents"]), projects)
            self.assertEqual({row["project"] for row in result["compilation"]["sources"]["compilations"]}, projects)
            self.assertEqual(result["compilation"]["inputs"]["packageInputsSha256"], evidence.digest({
                "acme.buildinputs/3.2.1/" + path: hashlib.sha256(data).hexdigest()
                for path, data in package_members.items()}))
            receipt = result["documents"][binding.project]
            self.assertEqual(receipt["assembly"]["path"], "Acme.Emitted.dll")
            self.assertEqual(receipt["assembly"]["sha256"],
                             result["package"]["runtimeAssemblies"]["lib/net10.0/Acme.Emitted.dll"])
            if shared:
                dependency_receipt = result["documents"]["Shared/Shared.csproj"]
                self.assertEqual(dependency_receipt["assembly"]["path"], "Acme.Shared.Emitted.dll")
                self.assertNotEqual(dependency_receipt["assembly"]["sha256"], receipt["assembly"]["sha256"])
                if nonpackable:
                    self.assertNotIn("Shared/Shared.csproj", result["projectPackages"])
                    self.assertFalse((feed / "Acme.Shared.Package.3.1.0.nupkg").exists())
                else:
                    package = evidence.package_identity(feed, "Acme.Shared.Package", "3.1.0")
                    self.assertEqual(package, result["projectPackages"]["Shared/Shared.csproj"])
                    self.assertEqual(package["runtimeAssemblies"]["lib/net10.0/Acme.Shared.Emitted.dll"],
                                     dependency_receipt["assembly"]["sha256"])
            self.assertEqual(evidence.proof_manifest(source), admitted.sources)
        finally:
            if owner.state == "Allocated":
                owner.transition("Active")
            owner.transition("Settling")
            owner.release()

    def test_managed_captured_build_joins_evaluation_restore_csc_pdb_and_packed_image(self):
        self.captured_build()

    def test_managed_captured_build_rejects_packaged_image_not_emitted_by_observed_csc(self):
        with self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
            self.captured_build(change_after_pack=True)

    def test_managed_captured_build_joins_referenced_project_graphs_and_actual_images(self):
        self.captured_build(shared=True)

    def test_managed_captured_build_rechecks_referenced_project_image_after_pack(self):
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.captured_build(shared=True, change_dependency_after_pack=True)

    def test_managed_captured_build_preserves_explicitly_nonpackable_referenced_projects(self):
        self.captured_build(shared=True, nonpackable=True)

    def test_managed_captured_build_rejects_referenced_package_image_substitution(self):
        with self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
            self.captured_build(shared=True, package_mutation="image")

    def test_managed_captured_build_rejects_referenced_pack_overwriting_existing_feed_inputs(self):
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.captured_build(shared=True, package_mutation="feed")

    def test_managed_captured_build_rejects_tool_support_change_between_evaluation_and_compile(self):
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.captured_build(change_tool_after_restore=True)

    def test_managed_captured_build_uses_measured_sdk_for_restore_and_pack_not_ambient_sdk_selection(self):
        self.captured_build(ambient_sdk=True)

    @unittest.skipUnless(native_execution_supported(), "Native captured build requires supported Linux containment")
    def test_native_captured_build_joins_actual_owned_commands_and_releases_process_resources(self):
        self.captured_build(native=True)

    def package_consumer_build(self, *, native=False, runtime=False, captured=False, artifacts=False,
                               public_entrypoint=False):
        import conformance_sdk_checks as sdk
        import uuid
        from conformance_execution import project_build_line, project_discovery_line, project_test_line
        from conformance_lock_preparation import prepare_project_lock, verify_project_lock

        measured, _, _ = self.evaluation_request()
        parent = self.case
        if artifacts:
            temporary = tempfile.TemporaryDirectory(prefix="hoard-artifact-contributor-", dir=ROOT.parent)
            self.addCleanup(temporary.cleanup)
            parent = Path(temporary.name).resolve()
        owner = OwnedRun.allocate(parent / "package-consumer-run", ROOT, profile="harness")
        if artifacts:
            (owner.root / "cache/.local/share").mkdir(parents=True, mode=0o700)
            (owner.root / "cache/.local").chmod(0o700)
        candidate, sources = evidence.snapshot_sources(ROOT, owner, transient=True)
        category = "artifacts" if artifacts else "metadata"
        project = ROOT / "tests/fixtures/conformance/Contributor/Contributor.csproj"
        if artifacts:
            directory = self.case / "artifact-adapter"
            directory.mkdir()
            project = directory / "Adapter.csproj"
            project.write_text(
                '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
                '<TargetFramework>net10.0</TargetFramework><Nullable>enable</Nullable>'
                '<ImplicitUsings>enable</ImplicitUsings><PackageId>Acme.ArtifactAdapter</PackageId>'
                '<AssemblyName>Acme.ArtifactAdapter</AssemblyName><PackageVersion>0.1.0</PackageVersion>'
                '</PropertyGroup><ItemGroup>'
                '<PackageReference Include="Hoard.Fixtures.Conformance.Bindings.Local" Version="[0.1.0]" />'
                '</ItemGroup></Project>')
            (directory / "Binding.cs").write_text("""
using Hoard.Testing.Conformance.Bindings;
using Hoard.Fixtures.Conformance.Bindings.Local;
namespace Acme;
public sealed class ArtifactFactory : IArtifactRecoveryConformanceBinding
{
    private readonly LocalBinding inner;
    public ArtifactFactory(string sha) : this(sha, new ArtifactAssertionOptions()) { }
    public ArtifactFactory(string sha, ArtifactAssertionOptions options)
    {
        inner = new LocalBinding(sha, options: options);
        Declaration = new("acme.artifact.adapter", ConformanceCategory.Artifacts,
            "Hoard.Fixtures.Artifacts.Local", "0.1.0", sha,
            ["artifacts", "durable-local-process-crash", "enumeration-snapshot"],
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Artifacts)
                .OrderBy(fault => fault.ToString(), StringComparer.Ordinal));
    }
    public ConformanceBindingDeclaration Declaration { get; }
    public ValueTask<IArtifactConformanceSession> CreateSessionAsync(
        ConformanceRunContext context, CancellationToken token) => inner.CreateSessionAsync(context, token);
    public ValueTask<IArtifactConformanceSession> ReopenSessionAsync(
        ConformanceRunContext context, Hoard.Abstractions.Storage.ArtifactStoreIdentity identity,
        CancellationToken token) => inner.ReopenSessionAsync(context, identity, token);
}
""")
            adapter = {"packageId": "Acme.ArtifactAdapter", "version": "0.1.0",
                       "assemblyName": "Acme.ArtifactAdapter"}
            local = {"packageId": "Hoard.Fixtures.Conformance.Bindings.Local", "version": "0.1.0",
                     "assemblyName": "Hoard.Fixtures.Conformance.Bindings.Local"}
            provider = {"packageId": "Hoard.Fixtures.Artifacts.Local", "version": "0.1.0",
                        "assemblyName": "Hoard.Fixtures.Artifacts.Local"}
            registration = {
                "schemaVersion": 1, "project": "Adapter.csproj", "factoryType": "Acme.ArtifactFactory",
                "adapterPackage": adapter,
                "declaration": {
                    "schemaVersion": 1, "bindingId": "acme.artifact.adapter", "category": "artifacts",
                    "packageId": provider["packageId"], "packageVersion": "0.1.0",
                    "capabilities": ["artifacts", "durable-local-process-crash", "enumeration-snapshot"],
                    "faults": sorted(evidence._BINDING_REQUIRED_FAULTS["artifacts"])},
                "components": {"factory": adapter, **{role: local for role in ("session", "authority", "faults")},
                               **{role: provider for role in ("store", "validator", "maintenance", "lifetime")}},
                "sourceFiles": ["Adapter.csproj", "Adapter.conformance.json", "Binding.cs", "packages.lock.json"]}
            baseline = json.loads(
                (ROOT / "tests/fixtures/conformance/Consumer/packages.lock.json").read_text())["dependencies"]["net10.0"]
            dependencies, pending = {}, [local["packageId"]]
            while pending:
                package = pending.pop()
                if package in dependencies:
                    continue
                entry = copy.deepcopy(baseline[package])
                entry.pop("requested", None)
                entry["type"] = "Transitive"
                if package == local["packageId"]:
                    entry.update(type="Direct", requested="[0.1.0, 0.1.0]")
                dependencies[package] = entry
                pending.extend(entry.get("dependencies", {}))
            (directory / "packages.lock.json").write_bytes(evidence.canonical_bytes({
                "version": 1, "dependencies": {"net10.0": dependencies}}))
            project.with_suffix(".conformance.json").write_bytes(evidence.canonical_bytes(registration))
        admitted = contributors.admit_binding_project(project, category)
        if public_entrypoint:
            import conformance_cli

            self.assertTrue(native and runtime and captured and artifacts)
            owner.transition("Active")
            owner.transition("Settling")
            owner.release()
            destination = parent / "public-artifact-contributor"
            with contextlib.redirect_stdout(io.StringIO()) as output:
                status = conformance_cli.main([
                    "--profile", "artifacts", "--binding-project", str(project), "--evidence", str(destination)])
            records = tuple(evidence.load_json(line.encode("utf-8")) for line in output.getvalue().splitlines())
            self.assertEqual(status, 2)
            self.assertEqual(len(records), 2, records)
            summary, incomplete = records
            self.assertEqual(incomplete["code"], "EvidenceIncomplete")
            self.assertFalse(summary["qualification"])
            self.assertFalse(summary["profileComplete"])
            self.assertEqual(summary["scope"], "contributor-artifacts-runtime-diagnostic")
            self.assertEqual(summary["passedParameters"], 118)
            self.assertEqual(summary["sessionOrigins"], 128)
            self.assertEqual(len(summary["nativeArtifact"]["crashRecovery"]), 6)
            self.assertEqual(tuple(row["scenario"] for row in summary["nativeArtifact"]["retention"]),
                             ("source", "destination", "native"))
            self.assertEqual(tuple(row["size"] for row in summary["nativeArtifact"]["transfers"]),
                             (268435456, 4294967296))
            self.assertEqual(summary, evidence.load_json(
                (destination / "proofs/contributor-runtime-summary.json").read_bytes()))
            self.assertTrue(all(resource["state"] == "Released" for resource in summary["resources"]))
            self.assertFalse(any((destination / directory).exists() for directory in ("stores", "cache", "feed")))
            retained = destination / "proofs/contributor-runtime-inputs"
            inputs = evidence.load_json((destination / "proofs/contributor-inputs.json").read_bytes())
            self.assertEqual(evidence.input_manifest(retained, sorted(set(inputs["runtimeAssemblies"].values()))),
                             {hashed: hashed for hashed in inputs["runtimeAssemblies"].values()})
            print(evidence.canonical_bytes({"publicArtifact": summary}).decode("utf-8"), flush=True)
            return
        binding = contributors.snapshot_binding_project(project, category, admitted.inputs_sha256, owner)
        tools = owner.root / "tools"
        shutil.copytree(self.tool.parent, tools)
        config, feed = owner.root / "NuGet.Config", owner.root / "feed"
        config.write_bytes(evidence.synthetic_nuget_configuration(feed))
        config.chmod(0o400)
        native_command, commands, deadline = owner.command, [], time.monotonic() + 600

        def execute(arguments, *, cwd, cache_id, kind, timeout=600, env=None,
                    discovery_tests=frozenset(), **controls):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise evidence.ConformanceError("DeadlineExceeded")
            timeout = min(timeout, remaining)
            if native:
                result = native_command(
                    arguments, cwd=cwd, cache_id=cache_id, kind=kind, timeout=timeout, env=env,
                    **({"discovery_tests": discovery_tests} if kind == "discovery" else {}), **controls)
            else:
                cache = owner.root / "cache" / cache_id
                (cache / "tmp").mkdir(parents=True, exist_ok=True)
                environment = command_environment(owner.root, cache, env)
                code, raw = capture_control(
                    arguments, cwd=cwd, env=environment, limit=65536, timeout=min(timeout, 120))
                project = (lambda line: project_discovery_line(line, discovery_tests)) if kind == "discovery" else (
                    project_test_line if kind == "tests" else project_build_line)
                events = ((evidence.load_json(raw),) if kind == "events" else
                          tuple(event for line in raw.splitlines() if line.strip()
                                if (event := project(line)) is not None))
                result = mock.Mock(exit_code=code, events=events, execution_record_sha256=None)
            commands.append(tuple(arguments))
            return result

        try:
            with mock.patch.object(owner, "command", side_effect=execute):
                preparation = contributors.prepare_binding_project_consumer(
                    binding, owner, candidate, sources, config, feed, tools / self.tool.name,
                    Path(measured["toolchainRoot"]), self.msbuild.parent.name, self.runtime_version)
                supplied, result = preparation["captured"], preparation["consumer"]
                package_id = binding.registration["adapterPackage"]["packageId"]
                self.assertEqual(
                    supplied["package"]["runtimeAssemblies"]["lib/net10.0/" + package_id + ".dll"],
                    supplied["documents"][binding.project]["assembly"]["sha256"])
                selected = candidate / "tests/fixtures/conformance/Consumer/Consumer.csproj"
                self.assertTrue((selected.parent / "obj/Release/net10.0/Consumer.AssemblyInfo.cs").is_file())
            self.assertFalse(result["qualification"])
            self.assertEqual(set(result["components"]), set(evidence._SESSION_ROLES[category]))
            self.assertIn(result["assemblyPath"].relative_to(owner.root).as_posix(), result["runtimeAssemblies"])
            self.assertTrue(all(path.startswith("stores/binding-consumer/bin/Release/net10.0/")
                                for path in result["runtimeAssemblies"]))
            if artifacts:
                for entry in ("artifact-crash", "artifact-transfer", "artifact-noncooperative"):
                    code, raw = capture_control(
                        ["dotnet", "exec", "--fx-version", self.runtime_version,
                         str(result["assemblyPath"]), entry],
                        cwd=owner.root, env=command_environment(owner.root, owner.root / "cache/binding-consumer", None),
                        limit=65536, timeout=30)
                    self.assertEqual(code, 2)
                    self.assertEqual(evidence.load_json(raw), {
                        "event": "control",
                        "code": "EvidenceSchemaInvalid" if sys.platform == "linux" else "PrerequisiteMissing",
                        "value": 0})
            self.assertEqual(evidence.input_manifest(owner.root, sorted(result["controlInputs"])), result["controlInputs"])
            self.assertEqual(evidence.input_manifest(owner.root, sorted(result["cachedArchives"])), result["cachedArchives"])
            prepared_commands = (21 if runtime else 18) + (3 if captured else 0) + (1 if artifacts else 0)
            self.assertEqual(len(commands), prepared_commands)
            if runtime:
                prepared = contributors.prepare_binding_consumer_runtime(
                    binding, owner, ROOT, candidate, result, feed, {
                        "os": sys.platform, "osVersion": os.uname().release, "architecture": os.uname().machine,
                        "sdk": self.msbuild.parent.name, "runtime": self.runtime_version, "nativeSqlite": "not-used",
                        "filesystem": evidence.load_json((owner.root / "proofs/preflight.json").read_bytes())["filesystem"],
                        "runnerImage": "none", "freeBytes": shutil.disk_usage(owner.root).free,
                        "pragmas": {"journalMode": "none", "synchronous": 0, "foreignKeys": 0, "busyTimeout": 0}},
                    group_id=str(uuid.uuid4()), budgets=sdk.BUDGETS,
                    captured_build=supplied, toolchain_root=Path(measured["toolchainRoot"]))
                self.assertFalse(prepared["qualification"])
                inputs = prepared["inputs"]
                self.assertEqual(inputs, evidence.capture_profile_inputs(
                    owner, ROOT, candidate, **prepared["captureArguments"]))
                sdk.write_new(owner.root / "proofs/contributor-inputs.json", evidence.canonical_bytes(inputs))
                contributors.retain_binding_runtime_inputs(owner, inputs)
                sdk.write_new(owner.root / "runtime-owner.json", evidence.canonical_bytes({
                    "schemaVersion": 1, "runId": owner.run_id, "invocationGroupId": inputs["invocationGroupId"],
                    "rootId": owner.root_id, "rootPathSha256": hashlib.sha256(str(owner.root).encode()).hexdigest()}))
                manifest = contributors.binding_consumer_manifest(
                    binding, owner, inputs, attempt_id=str(uuid.uuid4()))
                binding_id = binding.registration["declaration"]["bindingId"]
                counts = (catalog.contributor_artifact_component_origin_counts(
                    binding_id, profile=contributors.artifact_binding_profile(binding.registration["declaration"]))
                    if artifacts else catalog.metadata_common_consumer_origin_counts(binding_ids=(binding_id,)))
                expected = {identity: (binding_id, "none") for identity in counts}
                runner = owner if native else SimpleNamespace(
                    root=owner.root, run_id=owner.run_id, root_id=owner.root_id, command=execute)
                for mutation in ("shortened", "duplicate", "foreign", "binding", "builtin-scope"):
                    bad = copy.deepcopy(manifest)
                    options = {"contributor_binding": binding}
                    if mutation == "shortened":
                        bad["expected"].pop()
                    elif mutation == "duplicate":
                        bad["expected"].append(dict(bad["expected"][0]))
                    elif mutation == "foreign":
                        bad["expected"][0]["testIdentity"] = "Foreign.Tests.Unrelated"
                    elif mutation == "binding":
                        bad["expected"][0]["bindingId"] = "foreign.binding"
                    else:
                        options["category_scope"] = ("metadata", "original-memory")
                    with self.subTest(runtime_manifest=mutation), self.assertRaisesRegex(
                            evidence.ConformanceError, "^WitnessMissing$"):
                        sdk.runtime_command(runner, result["assemblyPath"], bad, **options)
                for mutation in ("profileId", "mode"):
                    bad = {**inputs, mutation: ("metadata" if artifacts else "artifacts")
                           if mutation == "profileId" else "qualification"}
                    with self.subTest(runtime_inputs=mutation), self.assertRaisesRegex(
                            evidence.ConformanceError, "^BindingInvalid$"):
                        contributors.binding_consumer_manifest(
                            binding, owner, bad, attempt_id=str(uuid.uuid4()))
                altered_paths = (
                    "proofs/contributor-build-controls.json",
                    "proofs/contributor-vstest-inputs.json",
                    next(iter(result["components"].values()))[0],
                    "stores/binding-consumer/bin/Release/net10.0/Hoard.Fixtures.Conformance.Consumer.runtimeconfig.json",
                    "stores/binding-build/compiler-sources.json",
                    "stores/binding-evaluation/inputs.json",
                    "feed/" + package_id + ".0.1.0.nupkg",
                    next(iter(result["cachedArchives"])))
                for relative in altered_paths:
                    path = owner.root / relative
                    original, mode = path.read_bytes(), path.stat().st_mode & 0o777
                    try:
                        path.chmod(0o600)
                        path.write_bytes(original + b"\n")
                        with self.subTest(runtime_changed=relative), self.assertRaisesRegex(
                                evidence.ConformanceError, "^InputChanged$"):
                            contributors.binding_consumer_manifest(
                                binding, owner, inputs, attempt_id=str(uuid.uuid4()))
                    finally:
                        path.write_bytes(original)
                        path.chmod(mode)
                with mock.patch.object(owner, "command", side_effect=execute):
                    observed_result, observed, transport, discovery_sha = sdk._execute_runtime_transport(
                        runner, inputs, result["assemblyPath"], manifest, expected,
                        {"contributor_binding": binding}, origin_inputs={binding_id: result["components"]})
                sdk.validate_observation(
                    observed, observed_result, tuple(counts), "None", "Passed", 0, transport["proofs"], "None")
                sdk.validate_full_binding_origins(observed, inputs, counts)
                self.assertEqual(len(observed["witnesses"]), len(counts))
                self.assertEqual(sum(len(rows) for rows in observed["sessionOrigins"].values()), sum(counts.values()))
                self.assertRegex(discovery_sha, r"^[0-9a-f]{64}$")
                self.assertEqual(len(commands), prepared_commands + 2)
                for arguments in commands[-2:]:
                    self.assertEqual(arguments[:5], (
                        "dotnet", "exec", "--fx-version", self.runtime_version,
                        str(self.msbuild.parent / "vstest.console.dll")))
                self.assertEqual(evidence.input_manifest(
                    owner.root, sorted(prepared["controlInputs"])), prepared["controlInputs"])
                self.assertEqual(inputs, evidence.capture_profile_inputs(
                    owner, ROOT, candidate, **prepared["captureArguments"]))
                changed = owner.root / next(iter(result["cachedArchives"]))
                original, mode = changed.read_bytes(), changed.stat().st_mode & 0o777

                def late_change(arguments, **options):
                    observed = execute(arguments, **options)
                    changed.chmod(0o600)
                    changed.write_bytes(original + b"\n")
                    return observed

                late = {**manifest, "attemptId": str(uuid.uuid4()), "purpose": "discovery"}
                late_runner = owner if native else SimpleNamespace(
                    root=owner.root, run_id=owner.run_id, root_id=owner.root_id, command=late_change)
                try:
                    with mock.patch.object(owner, "command", side_effect=late_change), self.assertRaisesRegex(
                            evidence.ConformanceError, "^InputChanged$"):
                        sdk.runtime_command(late_runner, result["assemblyPath"], late, contributor_binding=binding)
                finally:
                    changed.write_bytes(original)
                    changed.chmod(mode)
                self.assertEqual(len(commands), prepared_commands + 3)
                if artifacts:
                    identity = (sdk.ARTIFACT_CONSUMER_PREFIX
                                + "Recovery_binding_reopens_exact_owned_state_with_fresh_factory_and_authority")
                    package = next(row for row in inputs["packages"]
                                   if row["packageId"] == "Hoard.Fixtures.Conformance.Bindings.Local")
                    recovery = {
                        **manifest, "attemptId": str(uuid.uuid4()),
                        "packages": [{
                            "id": package["packageId"], "sha256": package["sha256"],
                            "path": f'stores/binding-consumer/feed/{package["packageId"]}.{package["version"]}.nupkg'}],
                        "expected": [{
                            **manifest["expected"][0], "testIdentity": identity, "fullyQualifiedName": identity,
                            "packageId": package["packageId"], "bindingId": "local", "caseId": "local-artifact-session"}]}
                    checked, observed, transport, _ = sdk._execute_runtime_transport(
                        runner, inputs, result["assemblyPath"], recovery, {identity: ("local", "none")}, {})
                    sdk.validate_observation(
                        observed, checked, (identity,), "None", "Passed", 0, transport["proofs"], "None")
                    import conformance_contributor_crashes as crashes
                    crashes._context(owner, inputs, result, binding)
                    if native_execution_supported():
                        self.native_artifact_contributor_crashes(owner, inputs, result, binding)
                        self.native_artifact_contributor_noncooperation(owner, inputs, result, binding)
        finally:
            if owner.state == "Allocated":
                owner.transition("Active")
            owner.transition("Settling")
            owner.release()

    def native_artifact_contributor_crashes(self, owner, inputs, consumer, binding):
        import conformance_contributor_crashes as crashes

        observed = crashes.execute_crashes(owner, inputs, consumer, binding, repository=ROOT)
        self.assertEqual(tuple(row["boundary"] for row in observed), tuple(crashes.BOUNDARIES))
        self.assertEqual(len({row["directoryLease"]["resourceId"] for row in observed}), 6)
        self.assertEqual(len({row[key] for row in observed
                              for key in ("sourceSessionId", "recoverySessionId")}), 12)
        self.assertFalse(owner.live_children())

    def native_artifact_contributor_noncooperation(self, owner, inputs, consumer, binding):
        import conformance_contributor_noncooperation as retention

        observed = retention.execute_noncooperation(owner, inputs, consumer, binding, repository=ROOT)
        self.assertEqual(tuple(row["scenario"] for row in observed), retention.SCENARIOS)
        for field in ("sessionId", "childStartSha256"):
            self.assertEqual(len({row[field] for row in observed}), 3)
        self.assertFalse(owner.live_children())

    def test_managed_contributor_runtime_executes_every_common_metadata_row_with_exact_origins(self):
        self.package_consumer_build(runtime=True, captured=True)

    def test_managed_artifact_contributor_runtime_executes_component_rows_with_actual_package_origins(self):
        self.package_consumer_build(runtime=True, captured=True, artifacts=True)

    @unittest.skipUnless(native_execution_supported(), "Native contributor runtime requires supported Linux containment")
    def test_native_contributor_runtime_uses_owned_common_suite_and_actual_component_origins(self):
        project = ROOT / "tests/fixtures/conformance/Contributor/Contributor.csproj"
        binding = contributors.admit_binding_project(project, "metadata")
        destination = self.case / "public-contributor"
        with contextlib.redirect_stdout(io.StringIO()) as output:
            result = contributors.execute(
                ROOT, destination, project=project, category="metadata",
                binding_inputs_sha256=binding.inputs_sha256)
        self.assertEqual(result, 0)
        summary = evidence.load_json(output.getvalue().encode("utf-8"))
        self.assertFalse(summary["qualification"])
        self.assertFalse(summary["profileComplete"])
        self.assertEqual(summary["passedParameters"], 76)
        self.assertEqual(summary["sessionOrigins"], 86)
        self.assertRegex(summary["nativeParentSha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(summary, evidence.load_json(
            (destination / "proofs/contributor-runtime-summary.json").read_bytes()))
        self.assertTrue(all(resource["state"] == "Released" for resource in summary["resources"]))
        self.assertFalse(any((destination / directory).exists() for directory in ("stores", "cache", "feed")))
        inputs = evidence.admit_entity("RunInputs", evidence.load_json(
            (destination / "proofs/contributor-inputs.json").read_bytes()))
        replayed = contributors.inspect_metadata_binding_runtime(destination, expected_inputs=inputs)
        self.assertFalse(replayed["qualification"])
        self.assertEqual(len(replayed["witnesses"]), 76)
        self.assertEqual(replayed["sessionOrigins"], 86)
        self.assertEqual(replayed["failedTests"], ())
        with self.assertRaises(evidence.ConformanceError):
            contributors.inspect_metadata_binding_runtime(
                destination, expected_inputs=inputs, expected_fault="stale-replay")
        for defect in ("input-pin", "duplicate-attempt", "overlapping-attempts", "unknown-field",
                       "binding-source", "runtime-image", "completion-input", "optimistic-summary"):
            if defect == "input-pin":
                changed = evidence.load_json(evidence.canonical_bytes(inputs))
                changed["sourceSha256"] = "0" * 64
                with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                    contributors.inspect_metadata_binding_runtime(destination, expected_inputs=changed)
                continue
            relative = {
                "binding-source": "proofs/contributor-binding-inputs.json",
                "runtime-image": next(path for path in replayed["proofs"]
                                      if path.startswith("proofs/contributor-runtime-inputs/")),
                "completion-input": "proofs/contributor-completion-inputs.json",
                "optimistic-summary": "proofs/contributor-runtime-summary.json",
            }.get(defect, "proofs/contributor-runtime-transport.json")
            path = destination / relative
            original = path.read_bytes()
            if defect == "runtime-image":
                mutated = original + b"changed"
            else:
                changed = evidence.load_json(original)
                if defect == "duplicate-attempt":
                    changed["execution"]["attemptId"] = changed["discovery"]["attemptId"]
                elif defect == "overlapping-attempts":
                    changed["discovery"]["endedMs"] = changed["execution"]["endedMs"]
                elif defect == "unknown-field":
                    changed["extra"] = True
                elif defect == "binding-source":
                    changed["sources"].pop(next(iter(changed["sources"])))
                elif defect == "completion-input":
                    changed["runtimeAssemblies"][next(iter(changed["runtimeAssemblies"]))] = "0" * 64
                else:
                    changed["qualification"] = True
                mutated = evidence.canonical_bytes(changed)
            try:
                path.chmod(0o600)
                path.write_bytes(mutated)
                path.chmod(0o400)
                with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                    contributors.inspect_metadata_binding_runtime(destination, expected_inputs=inputs)
            finally:
                path.chmod(0o600)
                path.write_bytes(original)
                path.chmod(0o400)
            restored = contributors.inspect_metadata_binding_runtime(destination, expected_inputs=inputs)
            self.assertEqual(restored["proofs"], replayed["proofs"])
        from test_conformance_sanitation import ConformanceSanitationTests
        inspection = ConformanceSanitationTests()
        inspection.canaries = (os.fsencode(destination),)
        inspection.assert_clean(destination, output.getvalue().encode())

    @unittest.skipUnless(native_execution_supported(), "Native contributor runtime requires supported Linux containment")
    def test_native_faulty_contributor_retains_named_assertions_with_actual_session_origins(self):
        registration = evidence.load_json(
            (ROOT / "tests/fixtures/conformance/Contributor/Contributor.conformance.json").read_bytes())
        author = self.case / "faulty-adapter"
        for relative in registration["sourceFiles"]:
            target = author / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        project = author / registration["project"]
        source = project.parent / "ForwardingMetadataBinding.cs"
        raw = source.read_bytes()
        needle = b"inner = new(providerPackageSha256);\n        this.injectStaleReplay = injectStaleReplay;"
        self.assertEqual(raw.count(needle), 1)
        source.write_bytes(raw.replace(needle, needle.replace(b"= injectStaleReplay;", b"= true;")))
        binding = contributors.admit_binding_project(project, "metadata")
        destination = self.case / "faulty-contributor"
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            contributors.execute(
                ROOT, destination, project=project, category="metadata",
                binding_inputs_sha256=binding.inputs_sha256)
        inputs = evidence.admit_entity("RunInputs", evidence.load_json(
            (destination / "proofs/contributor-inputs.json").read_bytes()))
        replayed = contributors.inspect_metadata_binding_runtime(
            destination, expected_inputs=inputs, expected_fault="stale-replay")
        self.assertFalse(replayed["qualification"])
        self.assertEqual(len(replayed["witnesses"]), 76)
        self.assertEqual(len(replayed["failedTests"]), 3)
        self.assertEqual(replayed["sessionOrigins"], 86)
        frame = evidence.load_json((destination / "proofs/contributor-runtime-transport.json").read_bytes())
        failed_symbols = set()
        for witness in replayed["witnesses"]:
            if witness["status"] == "Failed":
                proof = evidence.load_json((destination / ("runtime-" + frame["execution"]["attemptId"])
                                           / f'proof-{witness["executionId"]}.json').read_bytes())
                self.assertEqual(proof["failureKind"], "Assertion")
                failed_symbols.add(proof["assertionSymbol"])
        self.assertEqual(len(failed_symbols), 3)
        self.assertTrue(any(symbol.endswith(".TicketExpiryAndRollbackAsync") for symbol in failed_symbols))
        with self.assertRaises(evidence.ConformanceError):
            contributors.inspect_metadata_binding_runtime(destination, expected_inputs=inputs)
        self.assertEqual(evidence.load_json((destination / "ownership.json").read_bytes())["state"], "Released")
        self.assertFalse((destination / "proofs/contributor-runtime-summary.json").exists())

    def test_managed_evaluation_task_rejects_links_foreign_toolchains_and_sanitizes_project_errors(self):
        value, source, receipt = self.evaluation_request()
        toolchain = value["toolchainRoot"]
        value["toolchainRoot"] = str(self.parent)
        self.request.write_bytes(evidence.canonical_bytes(value))
        self.assertEqual(self.evaluate()[1]["code"], "OwnershipInvalid")
        value["toolchainRoot"] = toolchain
        self.request.write_bytes(evidence.canonical_bytes(value))
        outside = self.parent / "outside-evaluation-canary"
        outside.write_bytes((source / "Adapter/Binding.cs").read_bytes())
        path = source / "Adapter/Binding.cs"
        path.unlink()
        path.symlink_to(outside)
        self.assertEqual(self.evaluate()[1]["code"], "OwnershipInvalid")
        self.assertEqual(outside.read_bytes(), b"public class Binding { }\n")
        path.unlink()
        path.write_bytes(outside.read_bytes())
        (source / "Adapter/Adapter.csproj").write_text("<Project>private-diagnostic-canary")
        value["sources"]["Adapter/Adapter.csproj"] = evidence.file_sha256(source / "Adapter/Adapter.csproj")
        self.request.write_bytes(evidence.canonical_bytes(value))
        self.assertEqual(self.evaluate()[1]["code"], "BindingInvalid")
        self.assertFalse(receipt.exists())


class ContributorAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="hoard-contributor-admission-")).resolve()
        self.parent.chmod(0o700)
        self.addCleanup(shutil.rmtree, self.parent)
        self.source = self.parent / "author"
        self.source.mkdir()
        self.project = self.source / "Adapter.csproj"
        self.project.write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        (self.source / "Binding.cs").write_text("namespace Acme; public sealed class Binding { }\n")
        (self.source / "packages.lock.json").write_text('{"version":2,"dependencies":{}}\n')
        self.sidecar = self.project.with_suffix(".conformance.json")
        adapter = {"packageId": "Acme.Adapter", "version": "0.1.0", "assemblyName": "Acme.Adapter"}
        self.registration = {
            "schemaVersion": 1, "project": "Adapter.csproj", "factoryType": "Acme.Binding",
            "adapterPackage": adapter,
            "declaration": {
                "schemaVersion": 1, "bindingId": "acme.metadata", "category": "metadata",
                "packageId": "Acme.Provider", "packageVersion": "0.1.0",
                "capabilities": ["metadata", "non-durable"],
                "faults": sorted(evidence._BINDING_REQUIRED_FAULTS["metadata"])},
            "components": {role: dict(adapter) for role in evidence._SESSION_ROLES["metadata"]},
            "sourceFiles": ["Adapter.csproj", "Adapter.conformance.json", "Binding.cs", "packages.lock.json"],
        }
        self.write(self.registration)

    def write(self, registration):
        self.sidecar.write_text(json.dumps(registration))

    def admit(self, profile="metadata"):
        return evidence.admit_invocation(ROOT, [
            "--profile", profile, "--binding-project", str(self.project),
            "--evidence", str(self.parent / "fresh")])

    def test_retained_binding_descriptor_replays_without_live_source_and_rejects_resealed_omissions(self):
        binding = contributors.admit_binding_project(self.project, "metadata")
        raw = evidence.canonical_bytes({"registration": binding.registration, "sources": binding.sources})
        retained = self.parent / "released"
        shutil.rmtree(self.source)
        replayed = contributors.admit_binding_snapshot(
            retained, raw, category="metadata", expected_inputs_sha256=binding.inputs_sha256)
        self.assertEqual(replayed.registration, binding.registration)
        self.assertEqual(replayed.sources, binding.sources)
        self.assertEqual(replayed.inputs_sha256, binding.inputs_sha256)
        self.assertFalse(replayed.root.exists())
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.admit_binding_snapshot(
                retained, raw, category="metadata", expected_inputs_sha256="0" * 64)
        for defect in ("omitted-source", "extra-source", "unknown-field", "foreign-category"):
            value = evidence.load_json(raw)
            if defect == "omitted-source":
                del value["sources"]["Binding.cs"]
            elif defect == "extra-source":
                value["sources"]["Foreign.cs"] = "0" * 64
            elif defect == "unknown-field":
                value["qualification"] = True
            else:
                value["registration"]["declaration"]["category"] = "artifacts"
            altered = evidence.canonical_bytes(value)
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                contributors.admit_binding_snapshot(
                    retained, altered, category="metadata",
                    expected_inputs_sha256=hashlib.sha256(altered).hexdigest())

    def test_retained_runtime_images_keep_original_bytes_without_private_workspaces(self):
        from test_conformance_evidence import ConformanceAdmissionTests

        for defect in ("none", "changed", "private", "encoded", "foreign-run"):
            with self.subTest(defect=defect):
                run = OwnedRun.allocate(self.parent / defect, ROOT, profile="harness")
                path = run.root / "stores/Consumer.dll"
                raw = b"original-runtime-image"
                if defect in ("private", "encoded"):
                    raw = os.fsencode(run.root)
                    if defect == "encoded":
                        raw = base64.b64encode(raw)
                path.write_bytes(raw)
                path.chmod(0o400)
                inputs = ConformanceAdmissionTests().inputs()
                inputs.update(runId=run.run_id, mode="diagnostic",
                              runtimeAssemblies={"stores/Consumer.dll": hashlib.sha256(raw).hexdigest()})
                if defect == "changed":
                    path.chmod(0o600)
                    path.write_bytes(b"changed")
                    path.chmod(0o400)
                elif defect == "foreign-run":
                    inputs["runId"] = str(uuid.uuid4())
                directory = run.root / "proofs/contributor-runtime-inputs"
                try:
                    if defect == "none":
                        contributors.retain_binding_runtime_inputs(run, inputs)
                        blob = directory / hashlib.sha256(raw).hexdigest()
                        self.assertEqual(blob.read_bytes(), raw)
                        self.assertEqual(blob.stat().st_mode & 0o777, 0o400)
                    else:
                        with self.assertRaises(evidence.ConformanceError):
                            contributors.retain_binding_runtime_inputs(run, inputs)
                        self.assertFalse(directory.exists())
                finally:
                    run.transition("Settling")
                    run.release()
                self.assertFalse(path.exists())
                if defect == "none":
                    self.assertEqual(blob.read_bytes(), raw)

    def test_runtime_controls_freeze_same_version_vstest_dependencies_extensions_and_resources(self):
        import conformance_sdk_checks as sdk

        toolchain = self.parent / "toolchain"
        directory = toolchain / "sdk/10.0.203"
        files = ("vstest.console.dll", "vstest.console.deps.json", "vstest.console.runtimeconfig.json",
                 "Newtonsoft.Json.dll", "Extensions/Logger.dll", "fr/vstest.console.resources.dll")
        for relative in files:
            path = directory / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(relative.encode())
        root = self.parent / "run"
        (root / "proofs").mkdir(parents=True)
        (root / "stores/snapshot").mkdir(parents=True)
        output = root / "stores/binding-consumer/bin/Release/net10.0"
        output.mkdir(parents=True)
        (output / "Consumer.dll").write_bytes(b"consumer")
        for path in self.source.iterdir():
            path.chmod(0o400)
        binding = SimpleNamespace(
            root=self.source, sources=evidence.proof_manifest(self.source), inputs_sha256="a" * 64)
        run = SimpleNamespace(root=root)
        images = contributors._binding_consumer_images(run)
        runner_path = root / "proofs/contributor-vstest-inputs.json"
        runner_path.write_bytes(evidence.canonical_bytes(contributors.vstest_runner_inputs(toolchain, "10.0.203")))
        controls = evidence.canonical_bytes({
            "schemaVersion": 1, "qualification": False, "bindingInputsSha256": binding.inputs_sha256,
            "inputs": evidence.input_manifest(root, ("proofs/contributor-vstest-inputs.json",)),
            "runtimeAssemblies": images})
        (root / "proofs/contributor-build-controls.json").write_bytes(controls)
        inputs = {
            "runtimeAssemblies": images, "sourceManifest": {},
            "environment": {"sdk": "10.0.203"},
            "invocation": ("binding-project", binding.inputs_sha256, hashlib.sha256(controls).hexdigest())}
        with mock.patch.object(sdk, "inspection_reference_roots", return_value={
                "Microsoft.NETCore.App": toolchain / "packs/Microsoft.NETCore.App.Ref"}), \
                mock.patch.object(evidence, "verify_snapshot"):
            self.assertEqual(contributors.read_binding_runtime_controls(run, binding, inputs), controls)
            for relative in files:
                path = directory / relative
                original = path.read_bytes()
                try:
                    path.write_bytes(original + b"changed")
                    with self.subTest(changed=relative), self.assertRaisesRegex(
                            evidence.ConformanceError, "^InputChanged$"):
                        contributors.read_binding_runtime_controls(run, binding, inputs)
                finally:
                    path.write_bytes(original)
            added = directory / "Extensions/Additional.dll"
            added.write_bytes(b"new extension")
            with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                contributors.read_binding_runtime_controls(run, binding, inputs)
            added.unlink()
            altered = evidence.load_json(controls)
            altered["inputs"] = {"proofs/contributor-vstest-inputs.json": "0" * 64}
            (root / "proofs/contributor-build-controls.json").write_bytes(evidence.canonical_bytes(altered))
            with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                contributors.read_binding_runtime_controls(run, binding, inputs)

    def test_native_pin_admission_uses_sealed_closure_for_eight_distinct_component_images(self):
        import conformance_contributor_crashes as crashes

        run = OwnedRun.allocate(self.parent / "component-run", ROOT, profile="harness")
        try:
            output = run.root / "stores/binding-consumer/bin/Release/net10.0"
            output.mkdir(parents=True)
            names = ("Consumer.dll", "Hoard.Testing.Conformance.dll", "Hoard.Abstractions.dll",
                     "Consumer.deps.json", "Consumer.runtimeconfig.json")
            roles = tuple(evidence._SESSION_ROLES["artifacts"])
            for name in (*names, *(role + ".dll" for role in roles)):
                (output / name).write_bytes(name.encode())
            images = contributors._binding_consumer_images(run)
            components = {role: ((output / (role + ".dll")).relative_to(run.root).as_posix(), "Acme.Adapter")
                          for role in roles}
            controls = evidence.canonical_bytes({"runtimeAssemblies": images})
            (run.root / "proofs/contributor-build-controls.json").write_bytes(controls)
            inputs = {
                "profileId": "artifacts", "mode": "diagnostic", "runId": run.run_id, "bindings": [{}],
                "runtimeAssemblies": images, "invocation": ("binding-project", "a" * 64,
                                                          hashlib.sha256(controls).hexdigest())}
            (run.root / "proofs/contributor-inputs.json").write_bytes(evidence.canonical_bytes(inputs))
            (run.root / "stores/binding-consumer/declaration.json").write_bytes(b"declaration")
            (run.root / "stores/binding-consumer/declaration.json").chmod(0o400)
            declaration = {
                **self.registration["declaration"], "category": "artifacts",
                "capabilities": ["artifacts", "durable-local-process-crash", "enumeration-snapshot"],
                "faults": sorted(evidence._BINDING_REQUIRED_FAULTS["artifacts"])}
            binding = SimpleNamespace(registration={"declaration": declaration})
            consumer = {"qualification": False, "assemblyPath": output / "Consumer.dll",
                        "runtimeAssemblies": images, "components": components}
            with mock.patch.object(evidence, "admit_entity", side_effect=lambda _, value: value), \
                    mock.patch.object(contributors, "read_binding_runtime_controls", return_value=controls):
                _, _, selected, _ = crashes._context(run, inputs, consumer, binding)
            self.assertLessEqual(len(selected) + 7, 16)
            self.assertIn("proofs/contributor-build-controls.json", selected)
            self.assertEqual(selected["proofs/contributor-build-controls.json"], inputs["invocation"][2])
            self.assertTrue(set(path for path, _ in components.values()) <=
                            evidence.load_json(controls)["runtimeAssemblies"].keys())
        finally:
            run.transition("Active")
            run.transition("Settling")
            run.release()

    def test_explicit_external_registration_freezes_declared_source_bytes_without_allocating_or_building(self):
        first = self.admit()
        self.assertEqual(first.binding_project, self.project)
        self.assertRegex(first.binding_inputs_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(first.binding_inputs_sha256, self.admit().binding_inputs_sha256)
        (self.source / "Binding.cs").write_text("namespace Acme; public sealed class Changed { }\n")
        self.assertNotEqual(first.binding_inputs_sha256, self.admit().binding_inputs_sha256)
        self.assertFalse((self.parent / "fresh").exists())
        self.assertEqual({path.name for path in self.source.iterdir()},
                         {"Adapter.csproj", "Adapter.conformance.json", "Binding.cs", "packages.lock.json"})
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            evidence.dispatch_invocation(first)

    def test_registration_rejects_foreign_categories_missing_hooks_and_provider_selected_omissions(self):
        for defect in ("category", "hook", "extra", "exclusions", "factory-injection", "factory-unicode",
                       "factory-package", "component-missing", "component-path", "duplicate-source",
                       "missing-project", "missing-registration", "escape", "unknown-source", "project-depth"):
            changed = copy.deepcopy(self.registration)
            if defect == "category":
                changed["declaration"]["category"] = "artifacts"
            elif defect == "hook":
                changed["declaration"]["faults"].pop()
            elif defect in ("extra", "exclusions"):
                changed[defect] = ["MP-21"]
            elif defect == "factory-injection":
                changed["factoryType"] = "Acme.Binding(); Bad()"
            elif defect == "factory-unicode":
                changed["factoryType"] = "Acme.B\u0131nding"
            elif defect == "factory-package":
                changed["components"]["factory"]["packageId"] = "Other.Adapter"
            elif defect == "component-missing":
                del changed["components"]["schema"]
            elif defect == "component-path":
                changed["components"]["store"]["assemblyName"] = "../Other"
            elif defect == "duplicate-source":
                changed["sourceFiles"].append("Binding.cs")
            elif defect == "missing-project":
                changed["sourceFiles"].remove("Adapter.csproj")
            elif defect == "missing-registration":
                changed["sourceFiles"].remove("Adapter.conformance.json")
            elif defect == "escape":
                changed["sourceFiles"].append("../outside.cs")
            elif defect == "project-depth":
                changed["project"] = "/".join(["nested"] * 33 + ["Adapter.csproj"])
            else:
                changed["sourceFiles"].append("Missing.cs")
            self.write(changed)
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                self.admit()
            self.assertFalse((self.parent / "fresh").exists())

    def test_registration_inventory_rejects_links_and_duplicate_json_keys(self):
        original = self.sidecar.read_bytes()
        self.sidecar.write_bytes(original.replace(b'"schemaVersion": 1', b'"schemaVersion": 1, "schemaVersion": 1', 1))
        with self.assertRaises(evidence.ConformanceError):
            self.admit()
        self.sidecar.write_bytes(original)
        source = self.source / "Binding.cs"
        target = self.parent / "outside.cs"
        target.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(target)
        with self.assertRaises(evidence.ConformanceError):
            self.admit()
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),
                         hashlib.sha256(b"namespace Acme; public sealed class Binding { }\n").hexdigest())
        self.assertFalse((self.parent / "fresh").exists())

    def test_owned_declared_snapshot_uses_admitted_bytes_without_building_or_modifying_author_sources(self):
        invocation = self.admit()
        original = {path.name: path.read_bytes() for path in self.source.iterdir()}
        run = OwnedRun.allocate(self.parent / "fresh", ROOT, profile="harness")
        captured = contributors.snapshot_binding_project(
            self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertEqual(captured.root, run.root / "stores/binding-source")
        self.assertEqual(captured.project, "Adapter.csproj")
        self.assertEqual(captured.inputs_sha256, invocation.binding_inputs_sha256)
        self.assertEqual({path.name: path.read_bytes() for path in self.source.iterdir()}, original)
        self.assertEqual({path.name: path.read_bytes() for path in captured.root.iterdir()}, original)
        self.assertTrue(all(path.stat().st_mode & 0o777 == 0o400 for path in captured.root.iterdir()))
        self.assertFalse((self.source / "obj").exists())
        self.assertFalse((captured.root / "obj").exists())
        run.transition("Settling")
        run.release()
        self.assertFalse(captured.root.exists())

    def test_owned_snapshot_rejects_changes_after_admission_before_copy_and_during_copy(self):
        invocation = self.admit()
        source = self.source / "Binding.cs"
        original = source.read_bytes()
        run = OwnedRun.allocate(self.parent / "fresh", ROOT, profile="harness")
        source.write_bytes(original + b"// changed after admission\n")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.snapshot_binding_project(
                self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertFalse((run.root / "stores/binding-source").exists())
        source.write_bytes(original)
        registration = self.sidecar.read_bytes()
        changed = copy.deepcopy(self.registration)
        changed["factoryType"] = "Acme.OtherBinding"
        self.write(changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.snapshot_binding_project(
                self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertFalse((run.root / "stores/binding-source").exists())
        self.sidecar.write_bytes(registration)
        actual = evidence._source_file

        def mutate_after_copy(directory, relative, **options):
            result = actual(directory, relative, **options)
            if relative == "Binding.cs" and options.get("target") is not None:
                source.write_bytes(original + b"// changed during copy\n")
            return result

        with mock.patch.object(evidence, "_source_file", side_effect=mutate_after_copy):
            with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                contributors.snapshot_binding_project(
                    self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertEqual((run.root / "stores/binding-source/Binding.cs").read_bytes(), original)
        self.assertFalse((self.source / "obj").exists())

    def test_owned_snapshot_rejects_output_inside_author_source_root(self):
        invocation = self.admit()
        original = (self.source / "Binding.cs").read_bytes()
        self.source.chmod(0o700)
        run = OwnedRun.allocate(self.source / "fresh", ROOT, profile="harness")
        with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
            contributors.snapshot_binding_project(
                self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertEqual((self.source / "Binding.cs").read_bytes(), original)
        self.assertFalse((run.root / "stores/binding-source").exists())

    def test_typed_factory_source_requires_selected_actual_adapter_image_and_provider_package(self):
        feed = self.parent / "feed"
        feed.mkdir()

        def package(name):
            with zipfile.ZipFile(feed / f"{name}.0.1.0.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                archive.writestr(f"lib/net10.0/{name}.dll", name.encode("ascii"))
            return evidence.package_identity(feed, name, "0.1.0")

        adapter, provider = package("Acme.Adapter"), package("Acme.Provider")
        for category in ("metadata", "artifacts"):
            with self.subTest(category=category):
                registration = copy.deepcopy(self.registration)
                registration["declaration"].update(
                    category=category, bindingId=f"acme.{category}",
                    capabilities=([category, "non-durable"] if category == "metadata"
                                  else [category, "non-durable-simulation", "enumeration-incomplete"]),
                    faults=sorted(evidence._BINDING_REQUIRED_FAULTS[category]))
                registration["components"] = {
                    role: dict(registration["adapterPackage"]) for role in evidence._SESSION_ROLES[category]}
                self.write(registration)
                project = contributors.admit_binding_project(self.project, category)
                source = contributors.binding_factory_source(project, adapter, provider)
                self.assertIn(b"new global::Acme.Binding(", source)
                self.assertIn(provider["sha256"].encode("ascii"), source)
                if category == "artifacts":
                    self.assertIn(b"ArtifactAssertionOptions options)", source)
                    self.assertIn(b"ArgumentNullException.ThrowIfNull(options)", source)
                    self.assertEqual(source.count(b"return Validate(new global::Acme.Binding("), 1)
                    self.assertEqual(source.count(b"Validate(new global::Acme.Binding("), 2)
                    self.assertEqual(source.count(b"ConformanceBindingAdmission.Validate(actual,"), 1)
                else:
                    self.assertNotIn(b"ArtifactAssertionOptions", source)
                for selected_adapter, selected_provider in (
                        (provider, provider), (adapter, adapter),
                        ({**adapter, "runtimeAssemblies": {"lib/net10.0/Other.dll": "a" * 64}}, provider),
                        ({**adapter, "version": "0.2.0"}, provider),
                        (adapter, {**provider, "version": "0.2.0"})):
                    with self.assertRaisesRegex(evidence.ConformanceError, "^BindingInvalid$"):
                        contributors.binding_factory_source(project, selected_adapter, selected_provider)
                with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                    contributors.binding_factory_source(project, {**adapter, "sourceMapping": "nuget.org"}, provider)

    def test_registered_metadata_common_parameters_use_the_actual_binding_id_without_builtin_aliases(self):
        counts = catalog.metadata_common_consumer_origin_counts(binding_ids=("acme.metadata",))
        default = catalog.metadata_common_consumer_origin_counts()
        self.assertEqual(len(counts) * 2, len(default))
        self.assertEqual({identity.split("(provider:")[0] for identity in counts},
                         {identity.split("(provider:")[0] for identity in default})
        self.assertTrue(all('(provider: "acme.metadata"' in identity for identity in counts))
        self.assertFalse(any('"memory"' in identity or '"sqlite"' in identity for identity in counts))
        for invalid in ((), ("acme.metadata",) * 2, "acme.metadata", None, ("../foreign",)):
            with self.subTest(invalid=invalid), self.assertRaises(evidence.ConformanceError):
                catalog.metadata_common_consumer_origin_counts(binding_ids=invalid)

    def test_artifact_component_inventory_uses_registered_identity_without_builtin_applicability(self):
        profile = {"durability": "SimulationOnly", "enumeration": "Incomplete"}
        actual = catalog.contributor_artifact_component_origin_counts("acme.artifacts", profile=profile)
        self.assertEqual(len(actual), 114)
        self.assertEqual(sum(actual.values()), 115)
        self.assertEqual(set(actual.values()), {1, 2})
        self.assertTrue(all('(provider: "acme.artifacts"' in identity for identity in actual))
        self.assertFalse(any('"local"' in identity or '"object"' in identity for identity in actual))
        with mock.patch.object(catalog, "full_artifact_binding_scenarios", side_effect=AssertionError):
            self.assertEqual(catalog.contributor_artifact_component_origin_counts("acme.artifacts", profile=profile), actual)
        snapshot = catalog.contributor_artifact_component_origin_counts(
            "acme.artifacts", profile={"durability": "LocalProcessCrash", "enumeration": "Snapshot"})
        self.assertEqual(len(snapshot), 118)
        self.assertEqual(sum(snapshot.values()), 128)
        self.assertEqual(set(actual) - set(snapshot), {
            'Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests.'
            'Observed_portable_consumers_preserve_actual_guarantees(provider: "acme.artifacts", consumer: "direct-availability")'})
        self.assertEqual(len(set(snapshot) - set(actual)), 5)
        self.assertTrue(all(".Observed_durable_" in identity or any(
            f'consumer: "{consumer}"' in identity for consumer in ("reclaimed-incarnations", "candidate-reclamation"))
                            for identity in set(snapshot) - set(actual)))
        release = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
                   "Observed_payload_release_errors_preserve_actual_restoration_and_faulted_ownership")
        self.assertEqual({identity for identity in actual if identity.startswith(release)}, {
            f'{release}(provider: "acme.artifacts", unavailable: {unavailable}, cancellation: {cancellation})'
            for unavailable in ("False", "True") for cancellation in ("False", "True")})
        for durability, enumeration, rows, origins in (
                ("LocalProcessCrash", "Incomplete", 119, 129), ("SimulationOnly", "Snapshot", 113, 114)):
            crossed = catalog.contributor_artifact_component_origin_counts(
                "acme.artifacts", profile={"durability": durability, "enumeration": enumeration})
            self.assertEqual(len(crossed), rows)
            self.assertEqual(sum(crossed.values()), origins)
        self.assertFalse(any("record_" in identity or 'consumer: "durable-receipt"' in identity
                             for identity in snapshot))
        for invalid in ("../foreign", "", None):
            with self.assertRaises(evidence.ConformanceError):
                catalog.contributor_artifact_component_origin_counts(invalid, profile=profile)
        for invalid in (None, {}, {**profile, "enumeration": "Unknown"}, {**profile, "extra": True}):
            with self.assertRaises(evidence.ConformanceError):
                catalog.contributor_artifact_component_origin_counts("acme.artifacts", profile=invalid)

    def test_artifact_profile_requires_unambiguous_input_bound_durability_and_enumeration(self):
        declaration = copy.deepcopy(self.registration["declaration"])
        declaration.update(
            category="artifacts", bindingId="acme.artifacts",
            capabilities=["artifacts", "non-durable-simulation", "enumeration-incomplete"],
            faults=sorted(evidence._BINDING_REQUIRED_FAULTS["artifacts"]))
        self.assertEqual(contributors.artifact_binding_profile(declaration),
                         {"durability": "SimulationOnly", "enumeration": "Incomplete"})
        durable = {**declaration, "capabilities": ["artifacts", "durable-local-process-crash", "enumeration-snapshot"]}
        self.assertEqual(contributors.artifact_binding_profile(durable),
                         {"durability": "LocalProcessCrash", "enumeration": "Snapshot"})
        for capabilities in (
                ["artifacts", "non-durable-simulation"],
                ["artifacts", "enumeration-incomplete"],
                ["artifacts", "non-durable-simulation", "enumeration-unknown"],
                [*declaration["capabilities"], "enumeration-unknown"],
                [*declaration["capabilities"], "durable-unknown"],
                [*declaration["capabilities"], "enumeration-snapshot"],
                [*declaration["capabilities"], "durable-local-process-crash"]):
            registration = copy.deepcopy(self.registration)
            registration["declaration"] = {**declaration, "capabilities": capabilities}
            registration["components"] = {
                role: dict(registration["adapterPackage"]) for role in evidence._SESSION_ROLES["artifacts"]}
            self.write(registration)
            with self.subTest(capabilities=capabilities), \
                    self.assertRaisesRegex(evidence.ConformanceError, "^BindingInvalid$"):
                contributors.admit_binding_project(self.project, "artifacts")

    def build_fixture(self, name="build"):
        (self.source / "packages.lock.json").write_text('{"version":2,"dependencies":{"net10.0":{}}}')
        self.write(self.registration)
        invocation = self.admit()
        run = OwnedRun.allocate(self.parent / name, ROOT, profile="harness")
        binding = contributors.snapshot_binding_project(
            self.project, "metadata", invocation.binding_inputs_sha256, run)
        configuration = run.root / "NuGet.Config"
        configuration.write_bytes(evidence.synthetic_nuget_configuration(run.root / "feed"))
        return binding, run, configuration

    def test_registered_build_isolates_each_declared_project_and_uses_exact_adapter_identity(self):
        nested = self.source / "shared"
        nested.mkdir()
        (nested / "Shared.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />')
        (nested / "packages.lock.json").write_text('{"version":2,"dependencies":{"net10.0":{}}}')
        self.registration["sourceFiles"].extend(["shared/Shared.csproj", "shared/packages.lock.json"])
        self.registration["adapterPackage"]["version"] = "2.4.0-preview.1"
        for component in self.registration["components"].values():
            component["version"] = "2.4.0-preview.1"
        binding, run, configuration = self.build_fixture()

        def pack(owner, project, config, cache, **options):
            self.assertIs(owner, run)
            self.assertEqual(project, binding.root / binding.project)
            self.assertEqual(config, configuration)
            self.assertEqual(options["package_id"], "Acme.Adapter")
            self.assertEqual(options["package_version"], "2.4.0-preview.1")
            properties = run.root / "stores/binding-build/binding.props"
            self.assertEqual(options["properties"], ("-p:CustomAfterDirectoryBuildProps=" + str(properties),))
            groups = ET.parse(properties).findall("./Choose/When/PropertyGroup")
            self.assertEqual(len(groups), 2)
            self.assertEqual(len({group.findtext("BaseIntermediateOutputPath") for group in groups}), 2)
            for group in groups:
                output = Path(group.findtext("BaseOutputPath"))
                self.assertTrue(output.is_relative_to(run.root / "stores/binding-build"))
                self.assertFalse(output.is_relative_to(binding.root))
            with zipfile.ZipFile(options["feed"] / "Acme.Adapter.2.4.0-preview.1.nupkg", "w") as archive:
                archive.writestr("Acme.Adapter.nuspec",
                                "<package><metadata><id>Acme.Adapter</id>"
                                "<version>2.4.0-preview.1</version></metadata></package>")
                archive.writestr("lib/net10.0/Acme.Adapter.dll", b"fixture image")

        with mock.patch("conformance_sdk_checks.build", side_effect=pack):
            result = contributors.build_binding_project(binding, run, configuration, run.root / "feed")
        self.assertEqual(result["package"]["version"], "2.4.0-preview.1")
        self.assertEqual(set(result["projects"]), {"Adapter.csproj", "shared/Shared.csproj"})
        self.assertFalse(result["qualification"])
        self.assertFalse((binding.root / "obj").exists())
        self.assertFalse((binding.root / "shared/obj").exists())
        self.assertEqual(evidence.input_manifest(binding.root, sorted(binding.sources)), binding.sources)

    def consumer_build_fixture(self, name="consumer-build"):
        binding, owner, configuration = self.build_fixture(name)
        candidate = owner.root / "stores/snapshot"
        project = candidate / "tests/fixtures/conformance/Consumer/Consumer.csproj"
        project.parent.mkdir(parents=True)
        project.write_text('<Project Sdk="Microsoft.NET.Sdk" />')
        project.chmod(0o400)
        sources = evidence.proof_manifest(candidate)
        tool = owner.root / "tools/BuildInputs.dll"
        tool.parent.mkdir()
        tool.write_bytes(b"modeled content tool")
        toolchain = self.parent / (name + "-toolchain")
        msbuild = toolchain / "sdk/10.0.203/MSBuild.dll"
        msbuild.parent.mkdir(parents=True)
        msbuild.write_bytes(b"modeled measured MSBuild")
        lock = owner.root / "consumer-source.lock.json"
        lock.write_bytes(evidence.canonical_bytes({"version": 2, "dependencies": {"net10.0": {}}}))
        packages, archives = [], []
        for name in ("Acme.Adapter", "Acme.Provider", "Hoard.Testing.Conformance", "Hoard.Abstractions"):
            archive = owner.root / "feed" / f"{name}.0.1.0.nupkg"
            with zipfile.ZipFile(archive, "w") as packed:
                packed.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                packed.writestr(f"lib/net10.0/{name}.dll", name.encode("ascii"))
            packages.append(evidence.package_identity(archive.parent, name, "0.1.0"))
            archives.append(archive)
        return binding, owner, candidate, sources, configuration, tool, toolchain, lock, packages, archives

    def run_consumer_build(self, fixture, *, defect=None):
        binding, owner, candidate, sources, configuration, tool, toolchain, lock, packages, archives = fixture

        def capture(run, selected_tool, version, selected_lock, adapter, selected_archives):
            self.assertIs(run, owner)
            self.assertEqual((selected_tool, version, selected_lock), (tool, "10.0.7", lock))
            self.assertEqual(selected_archives, archives)
            self.assertEqual(adapter, packages[0])
            derived = owner.root / "stores/binding-consumer/packages.lock.json"
            digest = contributors._write_owned_input(owner, derived, b"modeled derived lock")
            return {"qualification": False, "lockPath": derived, "lockSha256": digest,
                    "packages": [{"packageId": package["packageId"], "version": package["version"],
                                  "archiveSha256": package["sha256"]} for package in packages]}

        def build(run, project, config, cache, **options):
            self.assertIs(run, owner)
            self.assertEqual(project, candidate / "tests/fixtures/conformance/Consumer/Consumer.csproj")
            self.assertEqual((config, cache), (owner.root / "stores/binding-consumer/NuGet.Config", "binding-consumer"))
            configured = ET.parse(config).findall("./packageSources/add")
            self.assertEqual(len(configured), 1)
            self.assertEqual(configured[0].get("value"), str(owner.root / "stores/binding-consumer/feed"))
            self.assertEqual(config.stat().st_mode & 0o777, 0o400)
            self.assertEqual(options["lock"], owner.root / "stores/binding-consumer/packages.lock.json")
            self.assertNotIn("feed", options)
            self.assertEqual(options["msbuild"],
                             ("dotnet", "exec", "--fx-version", "10.0.7",
                              str(toolchain / "sdk/10.0.203/MSBuild.dll")))
            properties = dict(item[3:].split("=", 1) for item in options["properties"])
            self.assertEqual(properties["ConformanceContributorCategory"], "metadata")
            self.assertEqual(properties["ConformanceContributorPackageId"], "Acme.Adapter")
            factory = Path(properties["ConformanceContributorFactory"])
            self.assertIn(packages[1]["sha256"].encode("ascii"), factory.read_bytes())
            self.assertEqual(factory.stat().st_mode & 0o777, 0o400)
            self.assertEqual(options["lock"].stat().st_mode & 0o777, 0o400)
            output = owner.root / "stores/binding-consumer/bin/Release/net10.0"
            output.mkdir(parents=True)
            (output / "Hoard.Fixtures.Conformance.Consumer.dll").write_bytes(b"modeled compiled consumer")
            for package in packages:
                (output / (package["packageId"] + ".dll")).write_bytes(package["packageId"].encode("ascii"))
                filename = f'{package["packageId"]}.{package["version"]}.nupkg'
                cached = owner.root / "cache/binding-consumer" / package["packageId"].lower() / package["version"].lower()
                cached.mkdir(parents=True)
                shutil.copyfile(owner.root / "stores/binding-consumer/feed" / filename, cached / filename.lower())
            if defect == "sdk":
                (output / "Hoard.Testing.Conformance.dll").write_bytes(b"substituted SDK")
            elif defect == "cache-archive":
                (owner.root / "cache/binding-consumer/acme.adapter/0.1.0/acme.adapter.0.1.0.nupkg").write_bytes(b"changed")
            elif defect == "support-extra":
                (tool.parent / "unexpected.json").write_bytes(b"changed support inventory")
                raise evidence.ConformanceError("CommandFailed")
            elif defect == "build-failure":
                raise evidence.ConformanceError("CommandFailed")
            elif defect in ("factory", "lock", "configuration", "archive", "staged-archive", "tool", "source", "msbuild"):
                selected = {
                    "factory": factory, "lock": options["lock"], "configuration": config,
                    "archive": archives[0], "tool": tool, "source": project,
                    "staged-archive": owner.root / "stores/binding-consumer/feed/Acme.Adapter.0.1.0.nupkg",
                    "msbuild": toolchain / "sdk/10.0.203/MSBuild.dll"}[defect]
                selected.chmod(0o600)
                selected.write_bytes(b"changed")
                raise evidence.ConformanceError("CommandFailed")

        with mock.patch.object(contributors, "capture_binding_consumer_lock", side_effect=capture), \
                mock.patch("conformance_sdk_checks.build", side_effect=build):
            return contributors.build_binding_consumer(
                binding, owner, candidate, sources, tool, toolchain, "10.0.203", "10.0.7",
                source_lock=lock, packages=packages, archive_paths=archives)

    def test_registered_consumer_build_uses_frozen_package_only_controls_and_matches_output_component_bytes(self):
        fixture = self.consumer_build_fixture()
        result = self.run_consumer_build(fixture)
        self.assertFalse(result["qualification"])
        self.assertEqual(result["assemblyPath"],
                         fixture[1].root / "stores/binding-consumer/bin/Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
        self.assertEqual(set(result["components"]), set(evidence._SESSION_ROLES["metadata"]))
        self.assertTrue(all(path.startswith("stores/binding-consumer/bin/Release/net10.0/")
                            for path in result["runtimeAssemblies"]))

    def test_registered_consumer_build_rejects_substituted_common_sdk(self):
        for defect in ("sdk", "cache-archive"):
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                self.run_consumer_build(self.consumer_build_fixture(defect), defect=defect)

    def test_registered_consumer_build_rechecks_all_frozen_inputs_even_after_build_failure(self):
        for defect in ("factory", "lock", "configuration", "archive", "staged-archive",
                       "tool", "support-extra", "source", "msbuild"):
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                self.run_consumer_build(self.consumer_build_fixture(defect), defect=defect)

    def test_registered_consumer_build_preserves_failed_build_without_fallback(self):
        with self.assertRaisesRegex(evidence.ConformanceError, "^CommandFailed$"):
            self.run_consumer_build(self.consumer_build_fixture(), defect="build-failure")

    def test_shared_build_runs_observed_compile_between_restore_and_pack_without_a_fallback_build(self):
        from conformance_sdk_checks import build

        binding, owner, configuration = self.build_fixture()
        for prefix in (None, ("dotnet", "exec", "/selected/MSBuild.dll")):
            with self.subTest(msbuild=prefix):
                events = []

                def command(run, arguments, **options):
                    self.assertIs(run, owner)
                    events.append(arguments[1] if prefix is None else arguments[len(prefix) + 1])

                def compile_action():
                    events.append("observed-compile")

                with mock.patch("conformance_sdk_checks.baselines._command", side_effect=command), \
                        mock.patch("conformance_sdk_checks.canonicalize_acceptance_archive"):
                    build(owner, binding.root / binding.project, configuration, "binding-build", feed=owner.root / "feed",
                          compile_action=compile_action, msbuild=prefix)
                self.assertEqual(events, (["restore", "observed-compile", "pack"] if prefix is None else
                                          ["-target:Restore", "observed-compile", "-target:Pack"]))

    def test_shared_build_does_not_pack_or_fallback_after_observed_compile_failure(self):
        from conformance_sdk_checks import build

        binding, owner, configuration = self.build_fixture()
        for prefix in (None, ("dotnet", "exec", "/selected/MSBuild.dll")):
            with self.subTest(msbuild=prefix):
                compile_action = mock.Mock(side_effect=evidence.ConformanceError("InputChanged"))
                with mock.patch("conformance_sdk_checks.baselines._command") as command, \
                        mock.patch("conformance_sdk_checks.canonicalize_acceptance_archive") as canonicalize, \
                        self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                    build(owner, binding.root / binding.project, configuration, "binding-build", feed=owner.root / "feed",
                          compile_action=compile_action, msbuild=prefix)
                self.assertEqual(command.call_count, 1)
                arguments = command.call_args.args[1]
                self.assertEqual(arguments[1] if prefix is None else arguments[len(prefix) + 1],
                                 "restore" if prefix is None else "-target:Restore")
                compile_action.assert_called_once_with()
                canonicalize.assert_not_called()

    def test_registered_build_forwards_frozen_prepared_controls_to_its_observed_compile_stage(self):
        binding, owner, configuration = self.build_fixture()
        observed = []

        def capture(prepared):
            self.assertEqual(prepared["bindingInputsSha256"], binding.inputs_sha256)
            self.assertEqual(prepared["propertiesSha256"],
                             evidence.file_sha256(owner.root / "stores/binding-build/binding.props"))
            self.assertEqual(set(prepared["projects"]), {binding.project})
            self.assertNotIn("package", prepared)
            observed.append(prepared)

        def execute(run, project, config, cache_id, **options):
            options["compile_action"]()
            with zipfile.ZipFile(options["feed"] / "Acme.Adapter.0.1.0.nupkg", "w") as archive:
                archive.writestr("Acme.Adapter.nuspec",
                                "<package><metadata><id>Acme.Adapter</id><version>0.1.0</version></metadata></package>")
                archive.writestr("lib/net10.0/Acme.Adapter.dll", b"modeled observed compiler image")

        with mock.patch("conformance_sdk_checks.build", side_effect=execute):
            result = contributors.build_binding_project(
                binding, owner, configuration, owner.root / "feed", compile_action=capture)
        self.assertEqual(len(observed), 1)
        self.assertEqual(result["propertiesSha256"], observed[0]["propertiesSha256"])
        self.assertEqual(result["package"]["packageId"], "Acme.Adapter")

    def test_registered_build_rejects_foreign_contexts_and_undeclared_locks_before_commands(self):
        binding, run, configuration = self.build_fixture()
        foreign = contributors.admit_binding_project(self.project, "metadata")
        with mock.patch("conformance_sdk_checks.build") as build:
            for selected, config in ((foreign, configuration), (binding, self.parent / "foreign.config"),
                                      (binding, run.root / ".." / "foreign.config"),
                                      (binding, run.root / "unsupported;config")):
                with self.subTest(root=selected.root, config=config), \
                        self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                    contributors.build_binding_project(selected, run, config, run.root / "feed")
            build.assert_not_called()
        self.registration["sourceFiles"].remove("packages.lock.json")
        self.write(self.registration)
        binding, run, configuration = self.build_fixture("missing-lock")
        with mock.patch("conformance_sdk_checks.build") as build, \
                self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            contributors.build_binding_project(binding, run, configuration, run.root / "feed")
        build.assert_not_called()

    def test_registered_build_rechecks_frozen_source_and_generated_controls_even_after_failure(self):
        for index, defect in enumerate(("source", "mode", "properties", "lock", "configuration", "extra")):
            binding, run, configuration = self.build_fixture("changed-" + str(index))

            def mutate(*args, **kwargs):
                if defect in ("source", "mode"):
                    path = binding.root / "Binding.cs"
                elif defect == "properties":
                    path = run.root / "stores/binding-build/binding.props"
                elif defect == "configuration":
                    path = configuration
                elif defect == "extra":
                    path = binding.root / "undeclared.cs"
                    path.touch()
                else:
                    path = next((run.root / "stores/binding-build").glob("*/packages.lock.json"))
                path.chmod(0o600)
                if defect != "mode":
                    path.write_bytes(b"changed")
                raise evidence.ConformanceError("CommandFailed")

            with self.subTest(defect=defect), mock.patch("conformance_sdk_checks.build", side_effect=mutate), \
                    self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                contributors.build_binding_project(binding, run, configuration, run.root / "feed")

    def restore_graph_fixture(self):
        binding = contributors.admit_binding_project(self.project, "metadata")
        packages = self.parent / "packages"
        cache = packages / "acme.dependency/2.4.0-preview.1"
        cache.mkdir(parents=True)
        archive = cache / "acme.dependency.2.4.0-preview.1.nupkg"
        with zipfile.ZipFile(archive, "w") as packed:
            packed.writestr("Acme.Dependency.nuspec", (
                "<package><metadata><id>Acme.Dependency</id><version>2.4.0-preview.1</version></metadata></package>"))
            packed.writestr("build/Acme.Dependency.props", "<Project />")
        hashed = base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode("ascii")
        self.content_receipt = {"schemaVersion": 1, "qualification": False, "packages": [{
            "cachePath": "acme.dependency/2.4.0-preview.1",
            "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "contentSha512": hashlib.sha512(archive.read_bytes()).hexdigest()}]}
        assets = {
            "version": 3, "targets": {"net10.0": {
                "Acme.Dependency/2.4.0-preview.1": {"type": "package"}}},
            "libraries": {"Acme.Dependency/2.4.0-preview.1": {
                "type": "package", "path": "acme.dependency/2.4.0-preview.1", "sha512": hashed}},
            "packageFolders": {str(packages) + "/": {}},
            "project": {"restore": {
                "projectPath": str(self.project), "projectUniqueName": str(self.project),
                "packagesPath": str(packages)}}}
        lock = {"version": 2, "dependencies": {"net10.0": {
            "acme.dependency": {"type": "Direct", "resolved": "2.4.0-preview.1", "contentHash": hashed}}}}
        return binding, assets, lock, packages

    def restored_file_policy_fixture(self):
        binding, assets, lock, packages = self.restore_graph_fixture()
        graph = contributors.binding_restore_graph(
            binding, evidence.canonical_bytes(assets), evidence.canonical_bytes(lock), binding.project, packages,
            expected_lock_sha256=evidence.digest(lock),
            content_hashes_data=evidence.canonical_bytes(self.content_receipt))
        member = "acme.dependency/2.4.0-preview.1/build/Acme.Dependency.props"
        data = {
            "schemaVersion": 1, "qualification": False, "succeeded": True,
            "diagnosticCodes": [], "observerErrors": [],
            "imports": {"packages/" + member: hashlib.sha256(b"<Project />").hexdigest()},
            "compilations": [{
                "project": binding.project, "succeeded": True, "inputs": {
                    "Sources": {"source/Binding.cs": binding.sources["Binding.cs"]},
                    "References": {"toolchain/reference.dll": "a" * 64}}}]}
        return binding, {binding.project: graph}, data, packages, member

    def test_restored_file_policy_joins_observed_package_members_to_exact_restored_archives(self):
        binding, graphs, data, packages, member = self.restored_file_policy_fixture()
        policy = contributors.binding_restored_file_policy(
            binding, graphs, evidence.canonical_bytes(data), packages)
        self.assertEqual(policy, {member: hashlib.sha256(b"<Project />").hexdigest()})
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(policy))

    def test_restored_file_policy_rejects_foreign_or_conflicting_graphs_and_changed_archive_members(self):
        binding, graphs, data, packages, member = self.restored_file_policy_fixture()
        for defect in ("binding", "project", "missing", "foreign", "member", "hash", "archive"):
            changed, selected = copy.deepcopy(data), evidence.load_json(evidence.canonical_bytes(graphs))
            if defect == "binding":
                selected[binding.project]["bindingInputsSha256"] = "a" * 64
            elif defect == "project":
                selected["foreign.csproj"] = selected.pop(binding.project)
            elif defect == "missing":
                selected = {}
            elif defect == "foreign":
                changed["imports"] = {"packages/foreign/1.0.0/build/Acme.Dependency.props": "a" * 64}
            elif defect == "member":
                changed["imports"] = {"packages/" + member + ".absent": "a" * 64}
            elif defect == "hash":
                changed["imports"]["packages/" + member] = "a" * 64
            else:
                selected[binding.project]["packages"]["acme.dependency/2.4.0-preview.1"]["archiveSha256"] = "a" * 64
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                contributors.binding_restored_file_policy(
                    binding, selected, evidence.canonical_bytes(changed), packages)
        archive = packages / "acme.dependency/2.4.0-preview.1/acme.dependency.2.4.0-preview.1.nupkg"
        archive.write_bytes(archive.read_bytes() + b"changed")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_restored_file_policy(binding, graphs, evidence.canonical_bytes(data), packages)

    def test_restore_graph_binds_exact_package_versions_hashes_and_declared_project_references(self):
        shared = self.source / "shared"
        shared.mkdir()
        (shared / "Shared.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />')
        self.registration["sourceFiles"].append("shared/Shared.csproj")
        self.write(self.registration)
        binding, assets, lock, packages = self.restore_graph_fixture()
        key = "Acme.Shared/1.0.0"
        assets["libraries"][key] = {"type": "project", "msbuildProject": "shared/Shared.csproj"}
        assets["targets"]["net10.0"][key] = {"type": "project"}
        assets["targets"]["net10.0"]["Acme.Dependency/2.4.0-preview.1"]["dependencies"] = {"Acme.Shared": "1.0.0"}
        lock["dependencies"]["net10.0"]["acme.shared"] = {"type": "Project"}
        lock["dependencies"]["net10.0"]["acme.dependency"]["dependencies"] = {"Acme.Shared": "[1.0.0]"}
        raw = evidence.canonical_bytes(assets)
        result = contributors.binding_restore_graph(
            binding, raw, evidence.canonical_bytes(lock), binding.project, packages,
            expected_lock_sha256=evidence.digest(lock), content_hashes_data=evidence.canonical_bytes(self.content_receipt))
        archive = packages / "acme.dependency/2.4.0-preview.1/acme.dependency.2.4.0-preview.1.nupkg"
        self.assertEqual(result["packages"], {"acme.dependency/2.4.0-preview.1": {
            "packageId": "Acme.Dependency", "version": "2.4.0-preview.1",
            "nugetContentSha512": hashlib.sha512(archive.read_bytes()).hexdigest(),
            "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "archiveSha512": hashlib.sha512(archive.read_bytes()).hexdigest()}})
        self.assertEqual(result["projects"], {key: "shared/Shared.csproj"})
        self.assertEqual(result["assetsSha256"], hashlib.sha256(raw).hexdigest())
        self.assertFalse(result["qualification"])
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))
        assets["packageFolders"] = {str(packages): {}}
        self.assertEqual(contributors.binding_restore_graph(
            binding, evidence.canonical_bytes(assets), evidence.canonical_bytes(lock),
            binding.project, packages, expected_lock_sha256=evidence.digest(lock),
            content_hashes_data=evidence.canonical_bytes(self.content_receipt))["packages"], result["packages"])
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_restore_graph(binding, raw, evidence.canonical_bytes(lock),
                                               binding.project, packages, expected_lock_sha256="a" * 64,
                                               content_hashes_data=evidence.canonical_bytes(self.content_receipt))
        (self.source / "Binding.cs").write_bytes(b"changed")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_restore_graph(binding, raw, evidence.canonical_bytes(lock),
                                               binding.project, packages, expected_lock_sha256=evidence.digest(lock),
                                               content_hashes_data=evidence.canonical_bytes(self.content_receipt))

    def test_restore_graph_admits_version_four_only_with_exact_single_framework_alias_mapping(self):
        binding, assets, lock, packages = self.restore_graph_fixture()
        assets["version"] = 4
        framework = {"framework": "net10.0", "targetAlias": "net10.0"}
        assets["project"]["frameworks"] = {"net10.0": dict(framework)}
        assets["project"]["restore"]["frameworks"] = {"net10.0": dict(framework)}

        def admit(graph):
            return contributors.binding_restore_graph(
                binding, evidence.canonical_bytes(graph), evidence.canonical_bytes(lock), binding.project, packages,
                expected_lock_sha256=evidence.digest(lock),
                content_hashes_data=evidence.canonical_bytes(self.content_receipt))

        self.assertIn("acme.dependency/2.4.0-preview.1", admit(assets)["packages"])
        for location in ("project", "restore"):
            for defect in ("missing", "extra", "framework", "alias"):
                changed = copy.deepcopy(assets)
                selected = changed["project"] if location == "project" else changed["project"]["restore"]
                if defect == "missing":
                    del selected["frameworks"]
                elif defect == "extra":
                    selected["frameworks"]["net9.0"] = dict(framework)
                else:
                    selected["frameworks"]["net10.0"]["framework" if defect == "framework" else "targetAlias"] = "net9.0"
                with self.subTest(location=location, defect=defect), self.assertRaisesRegex(
                        evidence.ConformanceError, "^EvidenceIncomplete$"):
                    admit(changed)
        changed = copy.deepcopy(assets)
        changed["version"] = 5
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            admit(changed)

    def test_restore_graph_rejects_missing_foreign_duplicate_or_changed_package_and_edge_rows(self):
        binding, original, original_lock, packages = self.restore_graph_fixture()
        for defect in ("missing-library", "missing-lock", "foreign-target", "duplicate-id", "version",
                       "hash", "cache-owner", "edge", "type", "missing-type", "diagnostic", "framework"):
            assets, lock = copy.deepcopy(original), copy.deepcopy(original_lock)
            library = assets["libraries"]["Acme.Dependency/2.4.0-preview.1"]
            expected = "EvidenceIncomplete"
            if defect == "missing-library":
                assets["libraries"].clear()
            elif defect == "missing-lock":
                lock["dependencies"]["net10.0"].clear()
            elif defect == "foreign-target":
                assets["targets"]["net10.0"]["Foreign/1.0.0"] = {"type": "package"}
            elif defect == "duplicate-id":
                lock["dependencies"]["net10.0"]["Acme.Dependency"] = copy.deepcopy(
                    lock["dependencies"]["net10.0"]["acme.dependency"])
                expected = "EvidenceSchemaInvalid"
            elif defect == "version":
                lock["dependencies"]["net10.0"]["acme.dependency"]["resolved"] = "2.4.0"
                expected = "ProofMismatch"
            elif defect == "hash":
                library["sha512"] = base64.b64encode(b"q" * 64).decode("ascii")
                expected = "ProofMismatch"
            elif defect == "cache-owner":
                library["path"] = "foreign/2.4.0-preview.1"
                expected = "ProofMismatch"
            elif defect == "edge":
                assets["targets"]["net10.0"]["Acme.Dependency/2.4.0-preview.1"]["dependencies"] = {"Foreign": "1.0.0"}
            elif defect == "type":
                library["type"] = "project"
            elif defect == "missing-type":
                del library["type"]
                del assets["targets"]["net10.0"]["Acme.Dependency/2.4.0-preview.1"]["type"]
            elif defect == "diagnostic":
                assets["logs"] = [{"message": "private canary"}]
            else:
                assets["targets"]["net10.0/linux-x64"] = assets["targets"]["net10.0"]
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^" + expected + "$"):
                contributors.binding_restore_graph(binding, evidence.canonical_bytes(assets),
                                                   evidence.canonical_bytes(lock), binding.project, packages,
                                                   expected_lock_sha256=evidence.digest(lock),
                                                   content_hashes_data=evidence.canonical_bytes(self.content_receipt))

    def test_restore_graph_rejects_foreign_cache_project_paths_and_undeclared_project_references(self):
        binding, original, original_lock, packages = self.restore_graph_fixture()
        for defect in ("project", "unique-project", "cache", "fallback-cache", "outside-reference", "undeclared-reference"):
            assets, lock = copy.deepcopy(original), copy.deepcopy(original_lock)
            restore = assets["project"]["restore"]
            expected = "OwnershipInvalid"
            if defect == "project":
                restore["projectPath"] = str(self.parent / "foreign.csproj")
            elif defect == "unique-project":
                restore["projectUniqueName"] = str(self.parent / "foreign.csproj")
            elif defect == "cache":
                restore["packagesPath"] = str(self.parent)
            elif defect == "fallback-cache":
                assets["packageFolders"][str(self.parent) + "/"] = {}
            else:
                key = "Acme.Shared/1.0.0"
                assets["libraries"][key] = {
                    "type": "project", "msbuildProject": "../Outside.csproj" if defect == "outside-reference" else "Absent.csproj"}
                assets["targets"]["net10.0"][key] = {"type": "project"}
                lock["dependencies"]["net10.0"]["Acme.Shared"] = {"type": "Project"}
                if defect == "undeclared-reference":
                    expected = "EvidenceIncomplete"
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^" + expected + "$"):
                contributors.binding_restore_graph(binding, evidence.canonical_bytes(assets),
                                                   evidence.canonical_bytes(lock), binding.project, packages,
                                                   expected_lock_sha256=evidence.digest(lock),
                                                   content_hashes_data=evidence.canonical_bytes(self.content_receipt))

    def test_restore_graph_rejects_malformed_hashes_and_oversized_input(self):
        binding, assets, lock, packages = self.restore_graph_fixture()
        for hashed in ("not-base64", "!" * 88, base64.b64encode(b"x" * 63).decode("ascii")):
            assets["libraries"]["Acme.Dependency/2.4.0-preview.1"]["sha512"] = hashed
            with self.subTest(hashed=hashed), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                contributors.binding_restore_graph(binding, evidence.canonical_bytes(assets),
                                                   evidence.canonical_bytes(lock), binding.project, packages,
                                                   expected_lock_sha256=evidence.digest(lock),
                                                   content_hashes_data=evidence.canonical_bytes(self.content_receipt))
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            contributors.binding_restore_graph(binding, b"x" * (2 * 1024 * 1024 + 1), b"{}", binding.project, packages,
                                               expected_lock_sha256="a" * 64, content_hashes_data=b"{}")

    def test_restore_graph_checks_actual_cached_archives_and_aggregate_read_budget(self):
        binding, assets, lock, packages = self.restore_graph_fixture()
        archive = packages / "acme.dependency/2.4.0-preview.1/acme.dependency.2.4.0-preview.1.nupkg"
        original = archive.read_bytes()
        archive.write_bytes(original + b"changed")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_restore_graph(
                binding, evidence.canonical_bytes(assets), evidence.canonical_bytes(lock),
                binding.project, packages, expected_lock_sha256=evidence.digest(lock),
                content_hashes_data=evidence.canonical_bytes(self.content_receipt))
        archive.write_bytes(original)
        with mock.patch.object(evidence, "MAX_PROOF_BYTES", len(original) - 1), \
                self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            contributors.binding_restore_graph(
                binding, evidence.canonical_bytes(assets), evidence.canonical_bytes(lock),
                binding.project, packages, expected_lock_sha256=evidence.digest(lock),
                content_hashes_data=evidence.canonical_bytes(self.content_receipt))
        with zipfile.ZipFile(archive, "w") as packed:
            packed.writestr("Foreign.nuspec", (
                "<package><metadata><id>Foreign</id><version>2.4.0-preview.1</version></metadata></package>"))
            packed.writestr("build/Foreign.props", "<Project />")
        hashed = base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode("ascii")
        assets["libraries"]["Acme.Dependency/2.4.0-preview.1"]["sha512"] = hashed
        lock["dependencies"]["net10.0"]["acme.dependency"]["contentHash"] = hashed
        with self.assertRaises(evidence.ConformanceError):
            contributors.binding_restore_graph(
                binding, evidence.canonical_bytes(assets), evidence.canonical_bytes(lock),
                binding.project, packages, expected_lock_sha256=evidence.digest(lock),
                content_hashes_data=evidence.canonical_bytes(self.content_receipt))

    def test_restore_graph_requires_exact_closed_nuget_content_hash_receipt(self):
        binding, assets, lock, packages = self.restore_graph_fixture()
        for defect in ("missing", "foreign", "duplicate", "content", "archive", "unknown", "malformed"):
            receipt = copy.deepcopy(self.content_receipt)
            expected = "EvidenceSchemaInvalid"
            if defect == "missing":
                receipt["packages"].clear()
                expected = "ProofMismatch"
            elif defect == "foreign":
                receipt["packages"].append({**receipt["packages"][0], "cachePath": "foreign/1.0.0"})
                expected = "EvidenceIncomplete"
            elif defect == "duplicate":
                receipt["packages"].append(copy.deepcopy(receipt["packages"][0]))
            elif defect == "content":
                receipt["packages"][0]["contentSha512"] = "a" * 128
                expected = "ProofMismatch"
            elif defect == "archive":
                receipt["packages"][0]["archiveSha256"] = "a" * 64
                expected = "InputChanged"
            elif defect == "unknown":
                receipt["message"] = "private canary"
            else:
                receipt["packages"][0]["contentSha512"] = "not-a-hash"
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^" + expected + "$"):
                contributors.binding_restore_graph(
                    binding, evidence.canonical_bytes(assets), evidence.canonical_bytes(lock),
                    binding.project, packages, expected_lock_sha256=evidence.digest(lock),
                    content_hashes_data=evidence.canonical_bytes(receipt))

    def restore_capture_fixture(self):
        _, assets, lock, original_cache = self.restore_graph_fixture()
        binding, owner, _ = self.build_fixture()
        cache = owner.root / "cache/binding-build"
        shutil.copytree(original_cache, cache)
        assets["project"]["restore"].update({
            "projectPath": str(binding.root / binding.project),
            "projectUniqueName": str(binding.root / binding.project), "packagesPath": str(cache)})
        assets["packageFolders"] = {str(cache): {}}
        workspace = owner.root / "stores/binding-build" / hashlib.sha256(binding.project.encode()).hexdigest()
        (workspace / "obj").mkdir(parents=True)
        (workspace / "obj/project.assets.json").write_bytes(evidence.canonical_bytes(assets))
        (workspace / "packages.lock.json").write_bytes(evidence.canonical_bytes(lock))
        tool = owner.root / "content-tool.dll"
        tool.write_bytes(b"fixture tool image")
        built = {"bindingInputsSha256": binding.inputs_sha256, "projects": {
            binding.project: {"root": workspace, "preparedLockSha256": evidence.digest(lock)}}}
        return binding, owner, built, tool, cache, workspace

    def test_restore_capture_uses_owned_hash_bound_request_and_exact_runtime_without_relaxing_native_environment(self):
        binding, owner, built, tool, cache, workspace = self.restore_capture_fixture()

        def capture(arguments, **options):
            self.assertEqual(arguments[:5], ["dotnet", "exec", "--fx-version", "10.0.3", str(tool)])
            self.assertEqual(options["kind"], "events")
            self.assertEqual(options["env"], {"DOTNET_ROLL_FORWARD": "Disable"})
            request = owner.root / arguments[-2]
            self.assertEqual(evidence.file_sha256(request), arguments[-1])
            self.assertEqual(request.stat().st_mode & 0o777, 0o400)
            value = evidence.load_json(request.read_bytes())
            self.assertEqual(value["cachePath"], cache.relative_to(owner.root).as_posix())
            (owner.root / value["outputPath"]).write_bytes(evidence.canonical_bytes(self.content_receipt))
            return mock.Mock(exit_code=0, events=({"event": "control", "code": "None", "value": 1},))

        with mock.patch.object(owner, "command", side_effect=capture):
            graphs = contributors.capture_binding_restore_graphs(binding, owner, built, tool, "10.0.3", cache)
        self.assertEqual(set(graphs), {binding.project})
        self.assertEqual(len(graphs[binding.project]["packages"]), 1)

    def test_restore_capture_rechecks_inputs_after_failed_child_and_does_not_accept_missing_control_events(self):
        for defect in ("control", "request", "assets", "tool", "source", "mode"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=self.parent) as nested:
                original_parent = self.parent
                self.parent = Path(nested)
                try:
                    binding, owner, built, tool, cache, workspace = self.restore_capture_fixture()
                finally:
                    self.parent = original_parent

                def capture(arguments, **options):
                    if defect == "control":
                        (workspace / "nuget-content.json").write_bytes(evidence.canonical_bytes(self.content_receipt))
                        return mock.Mock(exit_code=0, events=())
                    path = {"request": workspace / "nuget-content-request.json",
                            "assets": workspace / "obj/project.assets.json",
                            "tool": tool, "source": binding.root / "Binding.cs",
                            "mode": binding.root / "Binding.cs"}[defect]
                    path.chmod(0o600)
                    if defect != "mode":
                        path.write_bytes(b"changed")
                    raise evidence.ConformanceError("CommandFailed")

                with mock.patch.object(owner, "command", side_effect=capture), self.assertRaisesRegex(
                        evidence.ConformanceError, "^" + ("ProofMismatch" if defect == "control" else "InputChanged") + "$"):
                    contributors.capture_binding_restore_graphs(binding, owner, built, tool, "10.0.3", cache)

    def test_restore_capture_preserves_closed_producer_failure_instead_of_masking_it(self):
        binding, owner, built, tool, cache, _ = self.restore_capture_fixture()
        observed = mock.Mock(exit_code=2, events=({
            "event": "control", "code": "PrerequisiteMissing", "value": 0},))
        with mock.patch.object(owner, "command", return_value=observed), self.assertRaisesRegex(
                evidence.ConformanceError, "^PrerequisiteMissing$"):
            contributors.capture_binding_restore_graphs(binding, owner, built, tool, "10.0.3", cache)

    def evaluation_capture_fixture(self):
        binding, owner, _ = self.build_fixture()
        tool = owner.root / "evaluation-tool.dll"
        tool.write_bytes(b"modeled evaluation tool")
        toolchain = self.parent / "toolchain"
        msbuild = toolchain / "sdk/10.0.203/MSBuild.dll"
        props = toolchain / "sdk/10.0.203/Sdks/Fixture.props"
        props.parent.mkdir(parents=True)
        msbuild.write_bytes(b"modeled msbuild host")
        props.write_bytes(b"<Project />")
        rows = [{"Identity": "source/" + path, "Kind": "source", "Sha256": binding.sources[path]}
                for path in (binding.project, "Binding.cs")]
        rows.append({"Identity": "toolchain/" + props.relative_to(toolchain).as_posix(), "Kind": "toolchain",
                     "Sha256": evidence.file_sha256(props)})
        return binding, owner, tool, toolchain, msbuild, props, rows

    def evaluation_receipt(self, binding, rows):
        adapter = binding.registration["adapterPackage"]
        return evidence.canonical_bytes({"Items": {
            "_BindingInputs": rows, "_BindingProjects": [{
                "Identity": binding.project, "PackageId": adapter["packageId"],
                "PackageVersion": adapter["version"], "IsPackable": "true"}]}})

    def test_evaluation_capture_uses_safe_driver_hash_bound_inputs_and_explicit_sdk_runtime(self):
        binding, owner, tool, toolchain, msbuild, _, rows = self.evaluation_capture_fixture()

        def capture(arguments, **options):
            self.assertEqual(arguments[:5], ["dotnet", "exec", "--fx-version", "10.0.3", str(msbuild)])
            self.assertIn("-noconsolelogger", arguments)
            self.assertEqual(options["env"], {"DOTNET_ROLL_FORWARD": "Disable"})
            self.assertEqual(options["kind"], "events")
            driver = Path(arguments[5])
            self.assertEqual(driver.stat().st_mode & 0o777, 0o400)
            task = ET.parse(driver).find("./Target/*")
            self.assertEqual(base64.b64decode(task.get("OwnedRootBase64")).decode(), str(owner.root))
            request = owner.root / task.get("RequestPath")
            self.assertEqual(evidence.file_sha256(request), task.get("RequestSha256"))
            self.assertEqual(request.stat().st_mode & 0o777, 0o400)
            value = evidence.load_json(request.read_bytes())
            self.assertEqual(value["sources"], binding.sources)
            (owner.root / value["outputPath"]).write_bytes(self.evaluation_receipt(binding, rows))
            return mock.Mock(exit_code=0, events=({"event": "control", "code": "None", "value": len(rows)},))

        with mock.patch.object(owner, "command", side_effect=capture):
            admitted = contributors.capture_binding_evaluation_inputs(
                binding, owner, tool, toolchain, "10.0.203", "10.0.3")
        self.assertIn("Binding.cs", admitted["sources"])
        self.assertIn("sdk/10.0.203/Sdks/Fixture.props", admitted["toolchain"])

    def test_evaluation_capture_rejects_missing_hashes_events_and_changed_inputs_after_failed_child(self):
        for defect in ("hash", "control", "request", "driver", "tool", "host", "source", "mode", "import"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=self.parent) as nested:
                original_parent = self.parent
                self.parent = Path(nested)
                try:
                    binding, owner, tool, toolchain, msbuild, props, rows = self.evaluation_capture_fixture()
                finally:
                    self.parent = original_parent

                def capture(arguments, **options):
                    driver = Path(arguments[5])
                    task = ET.parse(driver).find("./Target/*")
                    request = owner.root / task.get("RequestPath")
                    if defect in ("hash", "control", "import"):
                        if defect == "hash":
                            del rows[0]["Sha256"]
                        if defect == "import":
                            props.write_bytes(b"<Project changed='true' />")
                        value = evidence.load_json(request.read_bytes())
                        (owner.root / value["outputPath"]).write_bytes(
                            self.evaluation_receipt(binding, rows))
                        return mock.Mock(exit_code=0, events=() if defect == "control" else (
                            {"event": "control", "code": "None", "value": len(rows)},))
                    path = {"request": request, "driver": driver, "tool": tool, "host": msbuild,
                            "source": binding.root / "Binding.cs", "mode": binding.root / "Binding.cs"}[defect]
                    path.chmod(0o600)
                    if defect != "mode":
                        path.write_bytes(b"changed")
                    raise evidence.ConformanceError("CommandFailed")

                code = {"hash": "EvidenceIncomplete", "control": "ProofMismatch"}.get(defect, "InputChanged")
                with mock.patch.object(owner, "command", side_effect=capture), self.assertRaisesRegex(
                        evidence.ConformanceError, "^" + code + "$"):
                    contributors.capture_binding_evaluation_inputs(
                        binding, owner, tool, toolchain, "10.0.203", "10.0.3")

    def test_evaluation_capture_rejects_foreign_tool_and_overlapping_toolchain_before_execution(self):
        binding, owner, tool, toolchain, _, _, _ = self.evaluation_capture_fixture()
        for actual_tool, actual_toolchain in ((self.parent / "foreign.dll", toolchain), (tool, owner.root)):
            with self.subTest(foreign=actual_tool != tool), mock.patch.object(owner, "command") as command, \
                    self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                contributors.capture_binding_evaluation_inputs(
                    binding, owner, actual_tool, actual_toolchain, "10.0.203", "10.0.3")
            command.assert_not_called()

    def documents_capture_fixture(self):
        binding, owner, _ = self.build_fixture()
        workspace = owner.root / "stores/binding-build" / hashlib.sha256(binding.project.encode()).hexdigest()
        output = workspace / "bin/Release/net10.0"
        output.mkdir(parents=True)
        generated = workspace / "obj/Generated.cs"
        generated.parent.mkdir()
        generated.write_bytes(b"namespace Acme; public class Generated { }\n")
        for suffix in (".dll", ".pdb"):
            (output / ("Acme.Adapter" + suffix)).write_bytes(("modeled" + suffix).encode("ascii"))
        tool = owner.root / "documents-tool.dll"
        tool.write_bytes(b"modeled producer")
        built = {"bindingInputsSha256": binding.inputs_sha256,
                 "projects": {binding.project: {"root": workspace}}}
        compilation = {"schemaVersion": 1, "qualification": False, "succeeded": True,
                       "compilations": [{"project": binding.project, "succeeded": True, "sources": {
                           "source/Binding.cs": binding.sources["Binding.cs"],
                           "generated/" + generated.relative_to(owner.root / "stores/binding-build").as_posix():
                               evidence.file_sha256(generated)}}]}
        return binding, owner, built, tool, compilation, output, generated

    def test_documents_capture_binds_compiler_sources_owned_images_and_exact_runtime(self):
        binding, owner, built, tool, compilation, output, _ = self.documents_capture_fixture()

        def capture(arguments, **options):
            self.assertEqual(arguments[:6], ["dotnet", "exec", "--fx-version", "10.0.3", str(tool), "pdb-documents"])
            self.assertEqual(options["kind"], "events")
            self.assertEqual(options["env"], {"DOTNET_ROLL_FORWARD": "Disable"})
            request = owner.root / arguments[-2]
            self.assertEqual(evidence.file_sha256(request), arguments[-1])
            self.assertEqual(request.stat().st_mode & 0o777, 0o400)
            value = evidence.load_json(request.read_bytes())
            self.assertEqual(value["sourcePath"], "stores/binding-source")
            self.assertEqual(value["generatedPath"], "stores/binding-build")
            self.assertEqual(value["outputRoot"], output.relative_to(owner.root).as_posix())
            receipt = {"schemaVersion": 1, "qualification": False, "project": binding.project,
                       "assembly": value["assembly"], "pdb": value["pdb"],
                       "documents": compilation["compilations"][0]["sources"]}
            (owner.root / value["outputPath"]).write_bytes(evidence.canonical_bytes(receipt))
            return mock.Mock(exit_code=0, events=({"event": "control", "code": "None", "value": 2},))

        with mock.patch.object(owner, "command", side_effect=capture):
            receipts = contributors.capture_binding_compilation_documents(
                binding, owner, built, tool, "10.0.3", evidence.canonical_bytes(compilation),
                {binding.project: "Acme.Adapter.dll"})
        self.assertEqual(set(receipts), {binding.project})
        self.assertEqual(receipts[binding.project]["documents"], compilation["compilations"][0]["sources"])

    def test_documents_capture_rechecks_inputs_even_after_failed_child_and_rejects_missing_events(self):
        for defect in ("control", "request", "tool", "source", "mode", "generated", "image", "symbols"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=self.parent) as nested:
                original_parent = self.parent
                self.parent = Path(nested)
                try:
                    binding, owner, built, tool, compilation, output, generated = self.documents_capture_fixture()
                finally:
                    self.parent = original_parent

                def capture(arguments, **options):
                    request = owner.root / arguments[-2]
                    if defect == "control":
                        value = evidence.load_json(request.read_bytes())
                        receipt = {"schemaVersion": 1, "qualification": False, "project": binding.project,
                                   "assembly": value["assembly"], "pdb": value["pdb"],
                                   "documents": compilation["compilations"][0]["sources"]}
                        (owner.root / value["outputPath"]).write_bytes(evidence.canonical_bytes(receipt))
                        return mock.Mock(exit_code=0, events=())
                    path = {"request": request, "tool": tool, "source": binding.root / "Binding.cs",
                            "mode": binding.root / "Binding.cs", "generated": generated,
                            "image": output / "Acme.Adapter.dll", "symbols": output / "Acme.Adapter.pdb"}[defect]
                    path.chmod(0o600)
                    if defect != "mode":
                        path.write_bytes(b"changed")
                    raise evidence.ConformanceError("CommandFailed")

                with mock.patch.object(owner, "command", side_effect=capture), self.assertRaisesRegex(
                        evidence.ConformanceError, "^" + ("ProofMismatch" if defect == "control" else "InputChanged") + "$"):
                    contributors.capture_binding_compilation_documents(
                        binding, owner, built, tool, "10.0.3", evidence.canonical_bytes(compilation),
                        {binding.project: "Acme.Adapter.dll"})

    def test_documents_capture_rejects_missing_projects_and_foreign_workspace_or_images_before_execution(self):
        for defect in ("projects", "workspace", "image"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=self.parent) as nested:
                original_parent = self.parent
                self.parent = Path(nested)
                try:
                    binding, owner, built, tool, compilation, output, _ = self.documents_capture_fixture()
                finally:
                    self.parent = original_parent
                assemblies = {binding.project: "Acme.Adapter.dll"}
                if defect == "projects":
                    assemblies = {}
                elif defect == "workspace":
                    built["projects"][binding.project]["root"] = self.parent
                else:
                    assemblies[binding.project] = "../Acme.Adapter.dll"
                with mock.patch.object(owner, "command") as command, self.assertRaises(evidence.ConformanceError):
                    contributors.capture_binding_compilation_documents(
                        binding, owner, built, tool, "10.0.3", evidence.canonical_bytes(compilation), assemblies)
                command.assert_not_called()

    def compilation_capture_fixture(self):
        binding, owner, built, tool, compilation, _, generated = self.documents_capture_fixture()
        properties = owner.root / "stores/binding-build/binding.props"
        properties.write_bytes(b"<Project />")
        properties.chmod(0o400)
        built["propertiesSha256"] = evidence.file_sha256(properties)
        toolchain = self.parent / "compiler-toolchain"
        host, reference = toolchain / "sdk/10.0.203/MSBuild.dll", toolchain / "packs/Reference.dll"
        host.parent.mkdir(parents=True)
        reference.parent.mkdir()
        host.write_bytes(b"modeled compiler host")
        reference.write_bytes(b"modeled reference")
        packages = owner.root / "cache/binding-build"
        packages.mkdir()
        inputs = {"Sources": compilation["compilations"][0]["sources"],
                  "References": {"toolchain/packs/Reference.dll": evidence.file_sha256(reference)}}
        receipts = {
            "sources": compilation,
            "inputs": {"schemaVersion": 1, "qualification": False, "succeeded": True,
                       "compilations": [{"project": binding.project, "succeeded": True, "inputs": inputs}],
                       "imports": {"generated/binding.props": built["propertiesSha256"]},
                       "diagnosticCodes": [], "observerErrors": []},
            "parameters": {"schemaVersion": 1, "qualification": False, "compilations": [{
                "project": binding.project, "commandLineSha256": "a" * 64,
                "itemMetadata": {kind: {path: "b" * 64 for path in selected}
                                 for kind, selected in inputs.items()}}]}}
        return binding, owner, built, tool, toolchain, host, packages, generated, receipts

    def test_compilation_capture_uses_owned_fixed_event_mode_and_admits_all_three_receipts(self):
        binding, owner, built, tool, toolchain, host, packages, _, receipts = self.compilation_capture_fixture()

        def capture(arguments, **options):
            self.assertEqual(arguments[:5], ["dotnet", "exec", "--fx-version", "10.0.3", str(host)])
            self.assertIn("-noconsolelogger", arguments)
            self.assertIn("-verbosity:minimal", arguments)
            self.assertEqual(options["kind"], "events")
            self.assertEqual(options["env"], {
                "DOTNET_ROLL_FORWARD": "Disable", "MSBUILDLOGTASKINPUTS": "1", "MSBUILDLOGIMPORTS": "1"})
            logger = next(argument for argument in arguments if argument.startswith("-logger:"))
            _, root, relative, hashed = logger.split(";")
            self.assertEqual(base64.b64decode(root).decode(), str(owner.root))
            request = owner.root / relative
            self.assertEqual(evidence.file_sha256(request), hashed)
            self.assertEqual(request.stat().st_mode & 0o777, 0o400)
            value = evidence.load_json(request.read_bytes())
            self.assertEqual(value["sourceHashes"], binding.sources)
            for kind, path in value["outputs"].items():
                (owner.root / path).write_bytes(evidence.canonical_bytes(receipts[kind]))
            return mock.Mock(exit_code=0, events=({"event": "control", "code": "None", "value": 1},))

        with mock.patch.object(owner, "command", side_effect=capture):
            observed = contributors.capture_binding_compilation_inputs(
                binding, owner, built, tool, toolchain, "10.0.203", "10.0.3", packages, {})
        self.assertEqual(len(observed["sources"]["compilations"]), 1)
        self.assertEqual(len(observed["parameters"]["compilations"]), 1)

    def test_compilation_capture_rechecks_immutable_build_controls_even_after_child_failure(self):
        for defect in ("request", "properties", "tool", "host", "source", "mode"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=self.parent) as nested:
                original_parent = self.parent
                self.parent = Path(nested)
                try:
                    binding, owner, built, tool, toolchain, host, packages, _, _ = self.compilation_capture_fixture()
                finally:
                    self.parent = original_parent

                def capture(arguments, **options):
                    logger = next(argument for argument in arguments if argument.startswith("-logger:"))
                    path = {"request": owner.root / logger.split(";")[-2],
                            "properties": owner.root / "stores/binding-build/binding.props", "tool": tool, "host": host,
                            "source": binding.root / "Binding.cs", "mode": binding.root / "Binding.cs"}[defect]
                    path.chmod(0o600)
                    if defect != "mode":
                        path.write_bytes(b"changed")
                    raise evidence.ConformanceError("CommandFailed")

                with mock.patch.object(owner, "command", side_effect=capture), self.assertRaisesRegex(
                        evidence.ConformanceError, "^InputChanged$"):
                    contributors.capture_binding_compilation_inputs(
                        binding, owner, built, tool, toolchain, "10.0.203", "10.0.3", packages, {})

    def test_compilation_capture_rejects_missing_completion_or_changed_generated_inputs(self):
        for defect in ("control", "generated", "source-map"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=self.parent) as nested:
                original_parent = self.parent
                self.parent = Path(nested)
                try:
                    binding, owner, built, tool, toolchain, host, packages, generated, receipts = self.compilation_capture_fixture()
                finally:
                    self.parent = original_parent

                def capture(arguments, **options):
                    logger = next(argument for argument in arguments if argument.startswith("-logger:"))
                    value = evidence.load_json((owner.root / logger.split(";")[-2]).read_bytes())
                    if defect == "source-map":
                        receipts["sources"] = copy.deepcopy(receipts["sources"])
                        sources = receipts["sources"]["compilations"][0]["sources"]
                        del sources[next(path for path in sources if path.startswith("generated/"))]
                    for kind, path in value["outputs"].items():
                        (owner.root / path).write_bytes(evidence.canonical_bytes(receipts[kind]))
                    if defect == "generated":
                        generated.write_bytes(b"changed")
                    return mock.Mock(exit_code=0, events=() if defect == "control" else (
                        {"event": "control", "code": "None", "value": 1},))

                with mock.patch.object(owner, "command", side_effect=capture), self.assertRaisesRegex(
                        evidence.ConformanceError,
                        "^" + ("InputChanged" if defect == "generated" else "ProofMismatch") + "$"):
                    contributors.capture_binding_compilation_inputs(
                        binding, owner, built, tool, toolchain, "10.0.203", "10.0.3", packages, {})

    def test_registered_runtime_components_preserve_distinct_actual_archive_owners_and_image_names(self):
        feed, output = self.parent / "feed", self.parent / "consumer"
        feed.mkdir()
        output.mkdir()

        def package(name, assembly):
            image = (name + ":" + assembly).encode("ascii")
            with zipfile.ZipFile(feed / f"{name}.0.1.0.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                archive.writestr(f"lib/net10.0/{assembly}.dll", image)
            (output / f"{assembly}.dll").write_bytes(image)
            return evidence.package_identity(feed, name, "0.1.0")

        adapter = package("Acme.Adapter", "Acme.Adapter")
        provider = package("Acme.Provider", "Acme.Engine")
        controls = package("Acme.Helpers", "Acme.Control")
        packages = [adapter, provider, controls]
        self.registration["components"]["schema"] = {
            "packageId": "acme.provider", "version": "0.1.0", "assemblyName": "Acme.Engine"}
        for role in ("authority", "faults"):
            self.registration["components"][role] = {
                "packageId": "Acme.Helpers", "version": "0.1.0", "assemblyName": "Acme.Control"}
        self.write(self.registration)
        project = contributors.admit_binding_project(self.project, "metadata")

        def images():
            return evidence.input_manifest(self.parent, [
                f"consumer/{name}.dll" for name in ("Acme.Adapter", "Acme.Engine", "Acme.Control")])

        components = contributors.binding_runtime_components(project, packages, images(), "consumer")
        self.assertEqual(components["factory"], ("consumer/Acme.Adapter.dll", "Acme.Adapter"))
        self.assertEqual(components["store"], components["factory"])
        self.assertEqual(components["schema"], ("consumer/Acme.Engine.dll", "Acme.Provider"))
        self.assertEqual(components["faults"], ("consumer/Acme.Control.dll", "Acme.Helpers"))
        self.assertEqual(components["authority"], components["faults"])
        for defect, changed in (
                ("missing-provider", [adapter, controls]),
                ("missing-helper", [adapter, provider]),
                ("wrong-helper-version", [adapter, provider, {**controls, "version": "0.2.0"}]),
                ("wrong-helper-member", [adapter, provider, {
                    **controls, "runtimeAssemblies": {"lib/net10.0/Other.dll": next(iter(
                        controls["runtimeAssemblies"].values()))}}]),
                ("duplicate-casefolded-owner", [*packages, {**controls, "packageId": "acme.helpers"}])):
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^BindingInvalid$"):
                contributors.binding_runtime_components(project, changed, images(), "consumer")
        (output / "Acme.Control.dll").write_bytes(b"changed runtime image")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_runtime_components(project, packages, images(), "consumer")

        self.registration["declaration"].update({
            "category": "artifacts",
            "capabilities": ["artifacts", "non-durable-simulation", "enumeration-incomplete"],
            "faults": sorted(evidence._BINDING_REQUIRED_FAULTS["artifacts"])})
        del self.registration["components"]["schema"]
        for role in ("validator", "maintenance", "lifetime"):
            self.registration["components"][role] = {
                "packageId": "Acme.Provider", "version": "0.1.0", "assemblyName": "Acme.Engine"}
        self.write(self.registration)
        artifact = contributors.admit_binding_project(self.project, "artifacts")
        (output / "Acme.Control.dll").write_bytes(b"Acme.Helpers:Acme.Control")
        components = contributors.binding_runtime_components(artifact, packages, images(), "consumer")
        self.assertEqual(components["validator"], ("consumer/Acme.Engine.dll", "Acme.Provider"))
        self.assertEqual(components["maintenance"], components["validator"])
        self.assertEqual(components["lifetime"], components["validator"])
        self.assertEqual(components["faults"], ("consumer/Acme.Control.dll", "Acme.Helpers"))

    def test_registered_components_reject_conflicting_runtime_asset_owners_even_with_identical_bytes(self):
        feed = self.parent / "feed"
        feed.mkdir()
        packages = []
        for name in ("Acme.Adapter", "Acme.Provider"):
            with zipfile.ZipFile(feed / f"{name}.0.1.0.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                archive.writestr("lib/net10.0/Acme.Adapter.dll", b"identical but ambiguously owned")
            packages.append(evidence.package_identity(feed, name, "0.1.0"))
        self.registration["components"]["schema"]["packageId"] = "Acme.Provider"
        self.write(self.registration)
        project = contributors.admit_binding_project(self.project, "metadata")
        images = {"consumer/Acme.Adapter.dll": hashlib.sha256(b"identical but ambiguously owned").hexdigest()}
        with self.assertRaisesRegex(evidence.ConformanceError, "^BindingInvalid$"):
            contributors.binding_runtime_components(project, packages, images, "consumer")

    def test_explicit_archive_lock_policy_preserves_versions_graph_and_unselected_dependencies(self):
        import conformance_lock_preparation as preparation
        feed = self.parent / "feed"
        feed.mkdir()
        packages = []
        for name, version in (("Acme.Adapter", "1.2.3-preview.1"), ("Acme.Provider", "4.2.1")):
            with zipfile.ZipFile(feed / f"{name}.{version}.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>{version}</version></metadata></package>")
                archive.writestr(f"lib/net10.0/{name}.dll", (name + version).encode("ascii"))
            packages.append(evidence.package_identity(feed, name, version))
        dependencies = {
            "acme.adapter": {
                "type": "Direct", "requested": "[1.2.3-preview.1, 1.2.3-preview.1]",
                "resolved": "1.2.3-preview.1", "contentHash": "old-adapter",
                "dependencies": {"Acme.Provider": "4.2.1", "External.Other": "7.0.0"}},
            "Acme.Provider": {"type": "Transitive", "resolved": "4.2.1", "contentHash": "old-provider"},
            "External.Other": {"type": "Transitive", "resolved": "7.0.0", "contentHash": "unselected"}}
        original = {"version": 2, "dependencies": {
            "net10.0": dependencies, "net10.0/linux-x64": copy.deepcopy(dependencies)}}
        before = evidence.canonical_bytes(original)
        source = self.parent / "candidate"
        source.mkdir()
        project = source / "Consumer.csproj"
        project.write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        lock = source / "packages.lock.json"
        lock.write_bytes(before)
        alternate, record = preparation.prepare_project_lock(
            project, source, feed, "candidate", local_packages=packages)
        self.assertEqual(lock.read_bytes(), before)
        prepared = evidence.load_json(alternate.read_bytes())
        expected = copy.deepcopy(original)
        for framework in expected["dependencies"].values():
            for package in packages:
                name = "acme.adapter" if package["packageId"] == "Acme.Adapter" else "Acme.Provider"
                framework[name]["contentHash"] = base64.b64encode(
                    bytes.fromhex(package["nugetSha512"])).decode("ascii")
        self.assertEqual(prepared, expected)
        self.assertFalse(record["qualification"])
        preparation.verify_project_lock(record, source, feed, local_packages=packages)
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            preparation.verify_project_lock(record, source, feed)
        for defect in ("duplicate", "version", "archive-hash", "nuget-hash"):
            changed = list(packages)
            if defect == "duplicate":
                changed.append({**packages[0], "packageId": "acme.adapter"})
            else:
                field, value = {
                    "version": ("version", "1.2.4"),
                    "archive-hash": ("sha256", "a" * 64),
                    "nuget-hash": ("nugetSha512", "b" * 128)}[defect]
                changed[0] = {**packages[0], field: value}
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^InputChanged$"):
                preparation.rebind_local_archives(before, feed, local_packages=changed)
        for defect in ("duplicate-node", "missing-hash", "resolved-version"):
            changed = copy.deepcopy(original)
            framework = changed["dependencies"]["net10.0"]
            if defect == "duplicate-node":
                framework["Acme.Adapter"] = copy.deepcopy(framework["acme.adapter"])
            elif defect == "missing-hash":
                del framework["acme.adapter"]["contentHash"]
            else:
                framework["acme.adapter"]["resolved"] = "1.2.4"
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^InputChanged$"):
                preparation.rebind_local_archives(
                    evidence.canonical_bytes(changed), feed, local_packages=packages)
        archive = feed / "Acme.Provider.4.2.1.nupkg"
        archive.write_bytes(archive.read_bytes() + b"changed after capture")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            preparation.verify_project_lock(record, source, feed, local_packages=packages)

    def test_evaluated_inputs_require_declared_source_closure_and_hash_actual_toolchain_bytes(self):
        binding = contributors.admit_binding_project(self.project, "metadata")
        toolchain = self.parent / "toolchain"
        toolchain.mkdir()
        (toolchain / "Sdk.props").write_text("<Project />\n")
        rows = [{"Identity": "source/" + path, "Kind": "source"} for path in binding.sources]
        rows.append({"Identity": "toolchain/Sdk.props", "Kind": "toolchain",
                     "FullPath": str(self.parent / "discarded-private-vendor-metadata")})

        def capture(items):
            return contributors.binding_evaluation_inputs(
                binding, self.evaluation_receipt(binding, items), toolchain)

        captured = capture(rows)
        self.assertFalse(captured["qualification"])
        self.assertEqual(captured["sources"], binding.sources)
        self.assertEqual(captured["toolchain"], {"Sdk.props": evidence.file_sha256(toolchain / "Sdk.props")})
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(captured))
        missing_project = [row for row in rows if row["Identity"] != "source/Adapter.csproj"]
        missing_toolchain = [row for row in rows if row["Kind"] != "toolchain"]
        (self.source / "Ambient.cs").write_text("public class Ambient { }\n")
        for defect, changed in (
                ("undeclared-ambient-source", [*rows, {"Identity": "source/Ambient.cs", "Kind": "source"}]),
                ("missing-project", missing_project), ("missing-toolchain", missing_toolchain)):
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceIncomplete$"):
                capture(changed)
        for defect, changed in (
                ("duplicate", [*rows, rows[0]]),
                ("unknown-metadata", [{**rows[0], "providerMessage": "must not disappear"}, *rows[1:]]),
                ("wrong-kind", [{**rows[0], "Kind": "package"}, *rows[1:]]),
                ("prefix-mismatch", [{**rows[0], "Kind": "toolchain"}, *rows[1:]]),
                ("escaping-source", [{"Identity": "source/../outside", "Kind": "source"}, *rows[1:]])):
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                capture(changed)
        original = (self.source / "Binding.cs").read_bytes()
        (self.source / "Binding.cs").write_text("public class Changed { }\n")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            capture(rows)
        (self.source / "Binding.cs").write_bytes(original)
        self.sidecar.write_bytes(self.sidecar.read_bytes() + b"\n")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            capture([row for row in rows if row["Identity"] != "source/Adapter.conformance.json"])

    def compilation(self):
        self.generated = self.parent / "generated"
        self.generated.mkdir()
        (self.generated / "Dynamic.cs").write_text("public class Dynamic { }\n")
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        return {
            "schemaVersion": 1, "qualification": False, "succeeded": True,
            "compilations": [{
                "project": "Adapter.csproj", "succeeded": True,
                "sources": {"source/Binding.cs": self.binding.sources["Binding.cs"],
                            "generated/Dynamic.cs": evidence.file_sha256(self.generated / "Dynamic.cs")}}]}

    def compile_inputs(self, value):
        data = value if isinstance(value, bytes) else evidence.canonical_bytes(value)
        return contributors.binding_compilation_sources(self.binding, data, self.generated)

    def test_compiler_sources_bind_each_actual_project_to_frozen_and_generated_source_hashes(self):
        value = self.compilation()
        (self.source / "Helper.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        self.registration["sourceFiles"].append("Helper.csproj")
        self.write(self.registration)
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        value["compilations"].append({
            "project": "Helper.csproj", "succeeded": True,
            "sources": {"source/Binding.cs": self.binding.sources["Binding.cs"]}})
        result = self.compile_inputs(value)
        self.assertEqual(result["compilations"], tuple(value["compilations"]))
        self.assertEqual(result["bindingInputsSha256"], self.binding.inputs_sha256)
        self.assertFalse(result["qualification"])
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))

    def test_compiler_sources_reject_generated_output_namespace_and_input_ambiguity(self):
        value = self.compilation()
        row = value["compilations"][0]
        for path in ("source/Binding.cs", "generated/Dynamic.cs"):
            changed = copy.deepcopy(value)
            changed["compilations"][0]["generatedOutputs"] = {path: row["sources"][path]}
            with self.subTest(path=path), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceIncomplete$"):
                self.compile_inputs(changed)

    def test_compiler_sources_reject_failed_missing_duplicate_or_undeclared_projects(self):
        value = self.compilation()
        (self.source / "Other.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        self.registration["sourceFiles"].append("Other.csproj")
        self.write(self.registration)
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        for defect in ("build-failed", "compiler-failed", "missing-selected-project", "duplicate-project",
                       "undeclared-project", "not-a-project", "undeclared-source"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "build-failed":
                changed["succeeded"] = False
            elif defect == "compiler-failed":
                row["succeeded"] = False
            elif defect == "duplicate-project":
                changed["compilations"].append(copy.deepcopy(row))
            elif defect == "undeclared-source":
                row["sources"]["source/Ambient.cs"] = "a" * 64
            else:
                row["project"] = {
                    "missing-selected-project": "Other.csproj", "undeclared-project": "Unknown.csproj",
                    "not-a-project": "Binding.cs"}[defect]
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceIncomplete$"):
                self.compile_inputs(changed)

    def test_compiler_sources_reject_changed_generated_queried_and_unqueried_frozen_bytes(self):
        value = self.compilation()
        for path in (self.generated / "Dynamic.cs", self.source / "Binding.cs", self.sidecar):
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            with self.subTest(path=path.name), self.assertRaisesRegex(
                    evidence.ConformanceError, "^InputChanged$"):
                self.compile_inputs(value)
            path.write_bytes(original)
        changed = copy.deepcopy(value)
        changed["compilations"].append({
            "project": "Helper.csproj", "succeeded": True,
            "sources": {"generated/Dynamic.cs": "a" * 64}})
        (self.source / "Helper.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        self.registration["sourceFiles"].append("Helper.csproj")
        self.write(self.registration)
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.compile_inputs(changed)

    def test_compiler_sources_reject_open_schemas_unsafe_paths_and_unbounded_receipts(self):
        value = self.compilation()
        for defect in ("unknown-top", "unknown-row", "empty-rows", "empty-sources", "numeric-success",
                       "qualification", "namespace", "escape", "absolute", "hash"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "unknown-top":
                changed["message"] = "must not disappear"
            elif defect == "unknown-row":
                row["commandLine"] = "must not persist"
            elif defect == "empty-rows":
                changed["compilations"] = []
            elif defect == "empty-sources":
                row["sources"] = {}
            elif defect == "numeric-success":
                row["succeeded"] = 1
            elif defect == "qualification":
                changed["qualification"] = True
            elif defect == "hash":
                row["sources"]["source/Binding.cs"] = "invalid"
            else:
                path = {"namespace": "package/Other.cs", "escape": "generated/../outside.cs",
                        "absolute": "/private/outside.cs"}[defect]
                row["sources"][path] = "a" * 64
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                self.compile_inputs(changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            self.compile_inputs(b"x" * (2 * 1024 * 1024 + 1))
        raw = evidence.canonical_bytes(value).replace(b'"schemaVersion":1', b'"schemaVersion":1,"schemaVersion":1')
        with self.assertRaises(evidence.ConformanceError):
            self.compile_inputs(raw)

    def test_compiler_sources_reject_overlapping_generated_roots_and_linked_generated_inputs(self):
        value = self.compilation()
        for generated in (self.source, self.source / "obj", self.parent):
            with self.subTest(root=generated.name), self.assertRaisesRegex(
                    evidence.ConformanceError, "^OwnershipInvalid$"):
                contributors.binding_compilation_sources(
                    self.binding, evidence.canonical_bytes(value), generated)
        outside = self.parent / "outside.cs"
        outside.write_bytes((self.generated / "Dynamic.cs").read_bytes())
        (self.generated / "Dynamic.cs").unlink()
        (self.generated / "Dynamic.cs").symlink_to(outside)
        with self.assertRaises(evidence.ConformanceError):
            self.compile_inputs(value)
        self.assertEqual(outside.read_text(), "public class Dynamic { }\n")

    def documents(self):
        compilation = self.compile_inputs(self.compilation())["compilations"][0]
        self.output = self.parent / "output"
        self.output.mkdir()
        (self.output / "Adapter.dll").write_bytes(b"modeled compiler image")
        (self.output / "Adapter.pdb").write_bytes(b"modeled portable symbols")
        value = {
            "schemaVersion": 1, "qualification": False, "project": "Adapter.csproj",
            "assembly": {"path": "Adapter.dll", "sha256": evidence.file_sha256(self.output / "Adapter.dll")},
            "pdb": {"path": "Adapter.pdb", "sha256": evidence.file_sha256(self.output / "Adapter.pdb")},
            "documents": dict(compilation["sources"])}
        return compilation, value

    def document_inputs(self, compilation, value):
        return contributors.binding_compilation_documents(
            compilation, evidence.canonical_bytes(value), self.output, "Adapter.dll")

    def test_compiler_document_receipts_match_observed_source_subset_and_current_output_bytes(self):
        compilation, value = self.documents()
        del value["documents"]["generated/Dynamic.cs"]
        result = self.document_inputs(compilation, value)
        self.assertEqual(result["documents"], value["documents"])
        self.assertEqual(result["compilerSourcesSha256"], evidence.digest(compilation["sources"]))
        self.assertEqual(result["assembly"], value["assembly"])
        self.assertEqual(result["pdb"], value["pdb"])
        self.assertFalse(result["qualification"])
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))

    def test_compiler_documents_reject_foreign_project_source_hash_or_output_selection(self):
        compilation, value = self.documents()
        for defect in ("project", "document", "hash", "assembly", "pdb"):
            changed = copy.deepcopy(value)
            if defect == "project":
                changed["project"] = "Other.csproj"
            elif defect == "document":
                changed["documents"]["generated/Unobserved.cs"] = "a" * 64
            elif defect == "hash":
                changed["documents"]["source/Binding.cs"] = "a" * 64
            else:
                changed[defect]["path"] = "Other." + ("dll" if defect == "assembly" else "pdb")
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^ProofMismatch$"):
                self.document_inputs(compilation, changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            self.document_inputs({**compilation, "succeeded": False}, value)

    def test_compiler_documents_reject_output_byte_changes_and_linked_symbols(self):
        compilation, value = self.documents()
        for name in ("Adapter.dll", "Adapter.pdb"):
            path = self.output / name
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(name=name), self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                self.document_inputs(compilation, value)
            path.write_bytes(original)
        outside = self.parent / "outside.pdb"
        original = (self.output / "Adapter.pdb").read_bytes()
        outside.write_bytes(original)
        (self.output / "Adapter.pdb").unlink()
        (self.output / "Adapter.pdb").symlink_to(outside)
        with self.assertRaises(evidence.ConformanceError):
            self.document_inputs(compilation, value)
        self.assertEqual(outside.read_bytes(), original)

    def test_compiler_documents_reject_open_schemas_unsafe_paths_and_empty_document_sets(self):
        compilation, value = self.documents()
        for defect in ("field", "nested-field", "absolute", "escape", "qualification", "documents"):
            changed = copy.deepcopy(value)
            if defect == "field":
                changed["message"] = "must not disappear"
            elif defect == "nested-field":
                changed["assembly"]["message"] = "must not disappear"
            elif defect == "qualification":
                changed["qualification"] = True
            elif defect == "documents":
                changed["documents"] = {}
            else:
                changed["pdb"]["path"] = "/private/Adapter.pdb" if defect == "absolute" else "../Adapter.pdb"
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                self.document_inputs(compilation, changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            contributors.binding_compilation_documents(
                compilation, b"x" * (2 * 1024 * 1024 + 1), self.output, "Adapter.dll")

    def build_files(self):
        compilation = self.compile_inputs(self.compilation())["compilations"][0]
        self.toolchain, self.package_root = self.parent / "toolchain", self.parent / "packages"
        self.toolchain.mkdir()
        self.package_root.mkdir()
        for root, name, data in (
                (self.toolchain, "Reference.dll", b"fixed reference image"),
                (self.toolchain, "Analyzer.dll", b"fixed analyzer image"),
                (self.toolchain, "Sdk.props", b"<Project />"),
                (self.package_root, "acme.library/2.0.0/lib/net10.0/Library.dll", b"fixed package image")):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.package_inputs = evidence.input_manifest(
            self.package_root, ["acme.library/2.0.0/lib/net10.0/Library.dll"])
        return {
            "schemaVersion": 1, "qualification": False, "succeeded": True,
            "diagnosticCodes": [], "observerErrors": [],
            "imports": {"source/Adapter.csproj": self.binding.sources["Adapter.csproj"],
                        "toolchain/Sdk.props": evidence.file_sha256(self.toolchain / "Sdk.props")},
            "compilations": [{
                "project": "Adapter.csproj", "succeeded": True, "inputs": {
                    "Sources": dict(compilation["sources"]),
                    "References": {
                        "toolchain/Reference.dll": evidence.file_sha256(self.toolchain / "Reference.dll"),
                        **{"packages/" + path: hashed for path, hashed in self.package_inputs.items()}},
                    "Analyzers": {"toolchain/Analyzer.dll": evidence.file_sha256(self.toolchain / "Analyzer.dll")},
                    "AdditionalFiles": {}, "Resources": {}}}]}

    def build_file_inputs(self, value):
        return contributors.binding_build_file_inputs(
            self.binding, evidence.canonical_bytes(value), self.generated, self.toolchain,
            self.package_root, self.package_inputs)

    def test_build_file_receipts_rehash_imports_compiler_inputs_and_frozen_package_policy(self):
        value = self.build_files()
        value["tools"] = {"toolchain/Analyzer.dll": evidence.file_sha256(self.toolchain / "Analyzer.dll")}
        value["supportFiles"] = {"toolchain/Reference.dll": evidence.file_sha256(self.toolchain / "Reference.dll")}
        result = self.build_file_inputs(value)
        self.assertEqual(result["tools"], value["tools"])
        self.assertEqual(result["supportFiles"], value["supportFiles"])
        self.assertEqual(result["imports"], value["imports"])
        self.assertEqual(result["compilations"], tuple(value["compilations"]))
        self.assertEqual(result["bindingInputsSha256"], self.binding.inputs_sha256)
        self.assertEqual(result["packageInputsSha256"], evidence.digest(self.package_inputs))
        self.assertFalse(result["qualification"])
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))

    def test_build_file_receipts_apply_closed_namespace_and_archive_policy_to_tool_support(self):
        value = self.build_files()
        for field in ("tools", "supportFiles"):
            for path, code in (("external/Library.dll", "EvidenceSchemaInvalid"),
                               ("packages/foreign/1.0.0/Library.dll", "EvidenceIncomplete"),
                               ("source/Ambient.cs", "EvidenceIncomplete")):
                changed = copy.deepcopy(value)
                changed[field] = {path: "a" * 64}
                with self.subTest(field=field, path=path), self.assertRaisesRegex(
                        evidence.ConformanceError, "^" + code + "$"):
                    self.build_file_inputs(changed)

    def test_build_file_receipts_reject_missing_closure_failed_observation_and_unknown_parameters(self):
        value = self.build_files()
        for defect in ("diagnostics", "observer", "build-failed", "compiler-failed", "project", "duplicate-project",
                       "missing-sources", "empty-references", "unknown-parameter", "unknown-field",
                       "namespace", "undeclared-source", "package-policy", "empty-imports"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            expected = "EvidenceIncomplete"
            if defect in ("diagnostics", "observer"):
                changed["diagnosticCodes" if defect == "diagnostics" else "observerErrors"] = ["MSB4017"]
            elif defect == "build-failed":
                changed["succeeded"] = False
            elif defect == "compiler-failed":
                row["succeeded"] = False
            elif defect == "project":
                row["project"] = "Foreign.csproj"
            elif defect == "duplicate-project":
                changed["compilations"].append(copy.deepcopy(row))
            elif defect == "missing-sources":
                del row["inputs"]["Sources"]
                expected = "EvidenceSchemaInvalid"
            elif defect == "empty-references":
                row["inputs"]["References"] = {}
            elif defect == "unknown-parameter":
                row["inputs"]["UnobservedFiles"] = {}
                expected = "EvidenceSchemaInvalid"
            elif defect == "unknown-field":
                changed["message"] = "must not disappear"
                expected = "EvidenceSchemaInvalid"
            elif defect in ("namespace", "undeclared-source", "package-policy"):
                path = {"namespace": "external/Other.dll", "undeclared-source": "source/Ambient.cs",
                        "package-policy": "packages/foreign/1.0.0/Other.dll"}[defect]
                row["inputs"]["References"][path] = "a" * 64
                if defect == "namespace":
                    expected = "EvidenceSchemaInvalid"
            else:
                changed["imports"] = {}
                expected = "EvidenceSchemaInvalid"
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^" + expected + "$"):
                self.build_file_inputs(changed)

    def test_build_file_receipts_reject_changed_bytes_conflicting_hashes_and_package_policy_substitution(self):
        value = self.build_files()
        for path in (self.sidecar, self.generated / "Dynamic.cs", self.toolchain / "Reference.dll",
                     self.toolchain / "Analyzer.dll", self.toolchain / "Sdk.props",
                     self.package_root / "acme.library/2.0.0/lib/net10.0/Library.dll"):
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(path=path.name), self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                self.build_file_inputs(value)
            path.write_bytes(original)
        changed = copy.deepcopy(value)
        changed["imports"]["toolchain/Reference.dll"] = "a" * 64
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.build_file_inputs(changed)
        self.package_inputs = {path: "a" * 64 for path in self.package_inputs}
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.build_file_inputs(value)

    def test_build_file_receipts_reject_root_overlap_linked_inputs_and_aggregate_read_limit(self):
        value = self.build_files()
        with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
            contributors.binding_build_file_inputs(
                self.binding, evidence.canonical_bytes(value), self.generated, self.generated,
                self.package_root, self.package_inputs)
        outside = self.parent / "outside.dll"
        original = (self.toolchain / "Analyzer.dll").read_bytes()
        outside.write_bytes(original)
        (self.toolchain / "Analyzer.dll").unlink()
        (self.toolchain / "Analyzer.dll").symlink_to(outside)
        with self.assertRaises(evidence.ConformanceError):
            self.build_file_inputs(value)
        self.assertEqual(outside.read_bytes(), original)
        (self.toolchain / "Analyzer.dll").unlink()
        (self.toolchain / "Analyzer.dll").write_bytes(original)
        declared_bytes = sum((self.source / path).stat().st_size for path in self.binding.sources)
        with mock.patch.object(evidence, "MAX_PROOF_BYTES", declared_bytes):
            with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
                self.build_file_inputs(value)

    def package_file_selection(self):
        self.feed = self.parent / "feed"
        self.feed.mkdir()
        self.archive = self.feed / "Acme.Dependency.2.4.0-preview.1.nupkg"
        self.package_files = {
            "lib/net10.0/Acme.Dependency.dll": b"fixed runtime image",
            "ref/net10.0/Acme.Dependency.dll": b"fixed reference image",
            "build/Acme.Dependency.props": b"<Project />",
            "analyzers/dotnet/cs/Generator.dll": b"fixed analyzer image",
            "contentFiles/any/any/Additional.txt": b"private-resource-canary"}
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("Acme.Dependency.nuspec", (
                "<package><metadata><id>Acme.Dependency</id><version>2.4.0-preview.1</version></metadata></package>"))
            for name, data in self.package_files.items():
                archive.writestr(name, data)
        package = evidence.package_identity(self.feed, "Acme.Dependency", "2.4.0-preview.1")
        selection = {
            "packageId": "acme.dependency", "version": "2.4.0-preview.1",
            "cachePath": "acme.dependency/2.4.0-preview.1",
            "members": sorted(self.package_files)}
        return package, selection

    def test_registered_package_file_policy_binds_exact_nonruntime_archive_members_without_extracting(self):
        package, selection = self.package_file_selection()
        policy = contributors.binding_package_file_policy(self.feed, [package], [selection])
        self.assertEqual(policy, {
            selection["cachePath"] + "/" + name: hashlib.sha256(data).hexdigest()
            for name, data in self.package_files.items()})
        self.assertNotIn(b"private-resource-canary", evidence.canonical_bytes(policy))
        self.assertEqual(set(self.feed.iterdir()), {self.archive})
        self.assertEqual(contributors.binding_package_file_policy(self.feed, [], []), {})

    def test_registered_package_file_policy_rejects_missing_foreign_duplicate_or_ambiguous_selections(self):
        package, selection = self.package_file_selection()
        for defect in ("package", "version", "cache-owner", "cache-path", "cache-escape", "missing-member",
                       "member-escape", "duplicate-member", "duplicate-cache", "duplicate-package"):
            changed, packages = copy.deepcopy(selection), [package]
            expected = "BindingInvalid"
            if defect == "package":
                changed["packageId"] = "Foreign.Dependency"
            elif defect == "version":
                changed["version"] = "2.4.1"
            elif defect == "cache-owner":
                changed["cachePath"] = "other.dependency/2.4.0-preview.1"
            elif defect == "cache-path":
                changed["cachePath"] += "/nested"
            elif defect == "cache-escape":
                changed["cachePath"] = "../outside"
                expected = "EvidenceSchemaInvalid"
            elif defect == "missing-member":
                changed["members"].append("build/Absent.props")
                expected = "InputChanged"
            elif defect == "member-escape":
                changed["members"].append("../outside.props")
                expected = "EvidenceSchemaInvalid"
            elif defect == "duplicate-member":
                changed["members"].append(changed["members"][0])
                expected = "EvidenceSchemaInvalid"
            elif defect == "duplicate-package":
                packages.append({**package, "packageId": "acme.dependency"})
            selected = [changed, copy.deepcopy(changed)] if defect == "duplicate-cache" else [changed]
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^" + expected + "$"):
                contributors.binding_package_file_policy(self.feed, packages, selected)

    def test_registered_package_file_policy_rejects_changed_archive_bytes_and_hashes(self):
        package, selection = self.package_file_selection()
        for field in ("sha256", "nugetSha512"):
            changed = {**package, field: "a" * (64 if field == "sha256" else 128)}
            with self.subTest(field=field), self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                contributors.binding_package_file_policy(self.feed, [changed], [selection])
        self.archive.write_bytes(self.archive.read_bytes() + b"changed")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_package_file_policy(self.feed, [package], [selection])

    def test_registered_package_file_policy_checks_selected_nondll_crc_and_aggregate_byte_budget(self):
        package, selection = self.package_file_selection()
        with mock.patch.object(evidence, "MAX_PROOF_BYTES", self.archive.stat().st_size):
            with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
                contributors.binding_package_file_policy(self.feed, [package], [selection])
        with zipfile.ZipFile(self.archive) as archive:
            info = archive.getinfo("build/Acme.Dependency.props")
            offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
        raw = bytearray(self.archive.read_bytes())
        raw[offset] ^= 1
        self.archive.write_bytes(raw)
        corrupted = evidence.package_identity(self.feed, "Acme.Dependency", "2.4.0-preview.1")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_package_file_policy(self.feed, [corrupted], [selection])

    def test_build_only_archive_identity_does_not_weaken_runtime_package_admission(self):
        feed = self.parent / "feed"
        feed.mkdir()
        archive = feed / "Acme.BuildInputs.3.2.1.nupkg"
        with zipfile.ZipFile(archive, "w") as packed:
            packed.writestr("Acme.BuildInputs.nuspec",
                            "<package><metadata><id>Acme.BuildInputs</id><version>3.2.1</version></metadata></package>")
            packed.writestr("build/Acme.BuildInputs.props", "<Project />")
        captured = evidence.package_archive_identity(feed, "Acme.BuildInputs", "3.2.1")
        self.assertEqual(set(captured), {"packageId", "version", "sha256", "nugetSha512", "sourceMapping"})
        self.assertEqual(captured["sha256"], evidence.file_sha256(archive))
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            evidence.package_identity(feed, "Acme.BuildInputs", "3.2.1")
        selection = {
            "packageId": "Acme.BuildInputs", "version": "3.2.1", "cachePath": "acme.buildinputs/3.2.1",
            "members": ["build/Acme.BuildInputs.props"]}
        policy = contributors.binding_package_file_policy(feed, [captured], [selection])
        self.assertEqual(policy, {
            "acme.buildinputs/3.2.1/build/Acme.BuildInputs.props": hashlib.sha256(b"<Project />").hexdigest()})
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
            contributors.binding_package_file_policy(feed, [{**captured, "message": "must not disappear"}], [selection])
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_package_file_policy(feed, [{**captured, "sha256": "a" * 64}], [selection])

    def compiler_parameters(self):
        files = self.build_file_inputs(self.build_files())["compilations"]
        return files, {
            "schemaVersion": 1, "qualification": False, "compilations": [{
                "project": row["project"], "commandLineSha256": "a" * 64,
                "itemMetadata": {kind: {path: "b" * 64 for path in items}
                                 for kind, items in row["inputs"].items()}}
                for row in files]}

    def test_compiler_parameters_bind_each_project_and_metadata_key_to_actual_file_receipt(self):
        files, value = self.compiler_parameters()
        result = contributors.binding_compiler_parameter_inputs(files, evidence.canonical_bytes(value))
        self.assertEqual(result["compilations"], tuple(value["compilations"]))
        self.assertEqual(result["fileInputsSha256"], evidence.digest(files))
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))
        self.assertFalse(result["qualification"])

    def test_compiler_parameters_reject_missing_duplicate_foreign_or_mismatched_metadata_keys(self):
        files, value = self.compiler_parameters()
        for defect in ("project", "duplicate-project", "missing-kind", "unknown-input", "missing-input"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "project":
                row["project"] = "Other.csproj"
            elif defect == "duplicate-project":
                changed["compilations"].append(copy.deepcopy(row))
            elif defect == "missing-kind":
                del row["itemMetadata"]["Analyzers"]
            elif defect == "unknown-input":
                row["itemMetadata"]["References"]["source/Other.dll"] = "c" * 64
            else:
                del row["itemMetadata"]["References"]["toolchain/Reference.dll"]
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
                contributors.binding_compiler_parameter_inputs(files, evidence.canonical_bytes(changed))
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            contributors.binding_compiler_parameter_inputs(
                [{**files[0], "succeeded": False}], evidence.canonical_bytes(value))
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            contributors.binding_compiler_parameter_inputs([files[0], files[0]], evidence.canonical_bytes(value))

    def test_compiler_parameters_reject_open_schemas_malformed_hashes_and_unbounded_receipts(self):
        files, value = self.compiler_parameters()
        for defect in ("field", "row-field", "command-hash", "metadata-hash", "path", "unknown-parameter"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "field":
                changed["rawCommandLine"] = "must not disappear"
            elif defect == "row-field":
                row["message"] = "must not disappear"
            elif defect == "command-hash":
                row["commandLineSha256"] = ""
            elif defect == "metadata-hash":
                row["itemMetadata"]["Sources"]["source/Binding.cs"] = "invalid"
            elif defect == "path":
                row["project"] = "../Other.csproj"
            else:
                row["itemMetadata"]["UnknownParameter"] = {}
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                contributors.binding_compiler_parameter_inputs(files, evidence.canonical_bytes(changed))
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            contributors.binding_compiler_parameter_inputs(files, b"x" * (2 * 1024 * 1024 + 1))


if __name__ == "__main__":
    unittest.main()
