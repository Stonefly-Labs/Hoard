"""Actual supplied-factory measured transfers, never built-in provider aliases."""

import hashlib
import os
from pathlib import Path
import shutil
from types import MappingProxyType
import uuid

import artifact_evidence as artifacts
import conformance_evidence as evidence
import conformance_sources as sources
from conformance_contributors import artifact_process_context, _require_successful_capture, _write_owned_input
from conformance_execution import check_capacity, native_execution_supported, scratch_filesystem


SIZES = (268435456, 4294967296)
CASE_ID = "contributor-artifact-transfer"
ADMISSION_PATH = "proofs/contributor-transfer-admission.json"


def _request(run, resource_id, size, repository):
    resource_id = evidence.stable_id(resource_id)
    if type(size) is not int or size not in SIZES:
        raise evidence.ConformanceError("ProofMismatch")
    prefix = "proofs/contributor-transfer-" + resource_id
    return {
        "schemaVersion": 1, "qualification": False, "resourceId": resource_id,
        "runId": run.run_id, "caseId": CASE_ID, "repositoryRoot": str(Path(repository).absolute()),
        "originPath": prefix + "-origin.json", "readbackPath": prefix + "-readback.json",
        "size": size, "expectedSha256": artifacts.expected_transfer_hash(size)}


def _arguments(run, inputs, assembly, request_path, request_data):
    return ["dotnet", "exec", "--fx-version", inputs["environment"]["runtime"], str(assembly),
            "artifact-transfer", str(run.root), request_path, hashlib.sha256(request_data).hexdigest()]


def _admission(run, inputs):
    value = evidence._runtime_json(sources._readonly(run.root / ADMISSION_PATH, 16384), {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "runId": evidence._uuid, "rootId": evidence.stable_id, "inputsSha256": evidence.sha256,
        "filesystem": evidence.stable_id, "freeBytes": evidence._integer,
    }, limit=16384)
    if (value["runId"] != run.run_id or value["rootId"] != run.root_id
            or value["inputsSha256"] != evidence.digest(inputs)
            or value["filesystem"] != inputs["environment"]["filesystem"]):
        raise evidence.ConformanceError("InputChanged")
    check_capacity("artifacts", free_bytes=value["freeBytes"])
    descriptor = run._root_descriptor()
    try:
        if scratch_filesystem(descriptor, "artifacts") != value["filesystem"]:
            raise evidence.ConformanceError("InputChanged")
    finally:
        os.close(descriptor)
    return value


def admit_transfer(run, inputs, consumer, binding, *, repository, resource_id, size, sequence):
    inputs, assembly, selected, declaration = artifact_process_context(run, inputs, consumer, binding)
    _admission(run, inputs)
    if (type(sequence) is not int or not 0 < sequence <= run.command_sequence or run.live_children()
            or len(selected) + 4 > 16):
        raise evidence.ConformanceError("ProofMismatch")
    request = _request(run, resource_id, size, repository)
    request_path = f"stores/{resource_id}-control/request.json"
    raw_request = sources._readonly(run.root / request_path, 16384)
    if raw_request != evidence.canonical_bytes(request):
        raise evidence.ConformanceError("InputChanged")
    control_raw = sources._readonly(run.root / f"proofs/transfer-command-{sequence:04}.json", 65536)
    command = evidence.load_json(control_raw)
    sources.admit_transfer_measurement(command, sequence, size)
    producer_raw = sources._readonly(run.root / request["readbackPath"], 8192)
    binding_id = inputs["bindings"][0]["bindingId"]
    sources.admit_artifact_transfer_producer(
        evidence.load_json(producer_raw), command, binding_id, size, request["expectedSha256"],
        run.run_id, inputs["environment"]["runtime"])
    origin_raw = sources._readonly(run.root / request["originPath"], 65536)
    origin, = evidence._ingest_runtime_origins(
        inputs, [evidence.load_json(origin_raw)], origin_inputs={binding_id: consumer["components"]},
        case_id=CASE_ID, prior_sessions={}, prior_instances={})
    if (origin["parentSessionId"] is not None
            or origin["descriptorSha256"] != hashlib.sha256(declaration).hexdigest()):
        raise evidence.ConformanceError("ProofMismatch")
    native_raw = sources.native_control_record(
        run, sequence, control_raw, arguments=_arguments(run, inputs, assembly, request_path, raw_request), cwd=run.root,
        input_files=evidence.input_manifest(run.root, sorted({*selected, ADMISSION_PATH, request_path})),
        output_files=evidence.input_manifest(run.root, (request["originPath"], request["readbackPath"])))
    return MappingProxyType({
        "size": size, "sessionId": origin["sessionId"], "expectedSha256": request["expectedSha256"],
        "nativeParentSha256": hashlib.sha256(native_raw).hexdigest(),
        "producerSha256": hashlib.sha256(producer_raw).hexdigest(),
        "originSha256": hashlib.sha256(origin_raw).hexdigest()})


def execute_transfers(run, inputs, consumer, binding, *, repository):
    if not native_execution_supported():
        raise evidence.ConformanceError("PrerequisiteMissing")
    inputs, assembly, selected, _ = artifact_process_context(run, inputs, consumer, binding)
    if len(selected) + 4 > 16:
        raise evidence.ConformanceError("EvidenceIncomplete")
    descriptor = run._root_descriptor()
    try:
        free = shutil.disk_usage(descriptor).free
        check_capacity("artifacts", free_bytes=free)
        filesystem = scratch_filesystem(descriptor, "artifacts")
    finally:
        os.close(descriptor)
    _write_owned_input(run, run.root / ADMISSION_PATH, evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False, "runId": run.run_id, "rootId": run.root_id,
        "inputsSha256": evidence.digest(inputs), "filesystem": filesystem, "freeBytes": free}))
    _admission(run, inputs)
    observations = []
    for size in SIZES:
        inputs, assembly, selected, _ = artifact_process_context(run, inputs, consumer, binding)
        resource = "transfer-" + uuid.uuid4().hex
        request = _request(run, resource, size, repository)
        request_path = f"stores/{resource}-control/request.json"
        descriptor = run._directory_descriptor("stores")
        try:
            os.mkdir(resource, mode=0o700, dir_fd=descriptor)
            os.mkdir(resource + "-control", mode=0o700, dir_fd=descriptor)
        finally:
            os.close(descriptor)
        raw_request = evidence.canonical_bytes(request)
        _write_owned_input(run, run.root / request_path, raw_request)
        result = run.command(
            _arguments(run, inputs, assembly, request_path, raw_request),
            cwd=run.root, scope="transfer", record_execution=True, measure_transfer_bytes=size,
            execution_inputs=tuple(sorted({*selected, ADMISSION_PATH, request_path})),
            execution_outputs=(request["originPath"], request["readbackPath"]))
        _require_successful_capture(result)
        if (tuple(dict(row) for row in result.events) != (
                {"event": "control", "code": "None", "value": 0},
                {"event": "test", "code": "None", "value": size},
                {"event": "control", "code": "None", "value": 1})
                or result.execution_record_sha256 is None
                or hashlib.sha256(run.read_execution_record(run.command_sequence)).hexdigest()
                != result.execution_record_sha256):
            raise evidence.ConformanceError("ProofMismatch")
        observations.append(admit_transfer(
            run, inputs, consumer, binding, repository=repository, resource_id=resource,
            size=size, sequence=run.command_sequence))
    if len({row["sessionId"] for row in observations}) != len(SIZES):
        raise evidence.ConformanceError("ProofMismatch")
    return tuple(observations)
