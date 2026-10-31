"""Original-controller admission of deliberately retained supplied-factory work."""

import hashlib
import os
from pathlib import Path
from types import MappingProxyType
import uuid

import conformance_evidence as evidence
import conformance_sources as sources
from conformance_contributors import artifact_process_context, _require_successful_capture, _write_owned_input
from conformance_execution import native_execution_supported


SCENARIOS = ("source", "destination", "native")
CASE_ID = "contributor-artifact-retention"


def _request(run, resource_id, scenario, repository):
    resource_id = evidence.stable_id(resource_id)
    if scenario not in SCENARIOS:
        raise evidence.ConformanceError("ProofMismatch")
    prefix = "proofs/contributor-noncooperation-" + resource_id
    return {
        "schemaVersion": 1, "qualification": False, "resourceId": resource_id,
        "runId": run.run_id, "caseId": CASE_ID, "repositoryRoot": str(Path(repository).absolute()),
        "originPath": prefix + "-origin.json", "readbackPrefix": prefix, "scenario": scenario}


def _outputs(request):
    return (request["originPath"], *(request["readbackPrefix"] + "-" + phase + ".json"
                                    for phase in ("contained", "inspected")))


def _arguments(run, inputs, assembly, request_path, request_data):
    return ["dotnet", "exec", "--fx-version", inputs["environment"]["runtime"], str(assembly),
            "artifact-noncooperative", str(run.root), request_path, hashlib.sha256(request_data).hexdigest()]


def admit_noncooperation(run, inputs, consumer, binding, *, repository, resource_id, scenario, sequence):
    inputs, assembly, selected, declaration = artifact_process_context(run, inputs, consumer, binding)
    if (type(sequence) is not int or not 0 < sequence <= run.command_sequence or run.live_children()
            or len(selected) + 4 > 16):
        raise evidence.ConformanceError("ProofMismatch")
    request = _request(run, resource_id, scenario, repository)
    request_path = f"stores/{resource_id}-control/request.json"
    request_data = sources._readonly(run.root / request_path, 16384)
    if request_data != evidence.canonical_bytes(request):
        raise evidence.ConformanceError("InputChanged")
    offset = SCENARIOS.index(scenario)
    control_raw = sources._readonly(run.root / f"proofs/recovery-command-{sequence:04}.json", 65536)
    command = evidence.load_json(control_raw)
    sources.admit_recovery_barrier(command, sequence, 70 + offset, inspection=60 + offset)
    binding_id = inputs["bindings"][0]["bindingId"]
    hashes = {}
    for phase in ("contained", "inspected"):
        raw = sources._readonly(run.root / (request["readbackPrefix"] + "-" + phase + ".json"), 8192)
        sources.admit_artifact_noncooperation(
            evidence.load_json(raw), binding_id, scenario, phase, command["childPid"], run.run_id)
        hashes[phase + "Sha256"] = hashlib.sha256(raw).hexdigest()
    origin_raw = sources._readonly(run.root / request["originPath"], 65536)
    origin, = evidence._ingest_runtime_origins(
        inputs, [evidence.load_json(origin_raw)], origin_inputs={binding_id: consumer["components"]},
        case_id=CASE_ID, prior_sessions={}, prior_instances={})
    if (origin["parentSessionId"] is not None
            or origin["descriptorSha256"] != hashlib.sha256(declaration).hexdigest()):
        raise evidence.ConformanceError("ProofMismatch")
    native_raw = sources.native_control_record(
        run, sequence, control_raw,
        arguments=_arguments(run, inputs, assembly, request_path, request_data), cwd=run.root,
        input_files=evidence.input_manifest(run.root, sorted({*selected, request_path})),
        output_files=evidence.input_manifest(run.root, _outputs(request)))
    return MappingProxyType({
        "scenario": scenario, "sessionId": origin["sessionId"],
        "childStartSha256": command["childStartSha256"],
        "nativeParentSha256": hashlib.sha256(native_raw).hexdigest(),
        "originSha256": hashlib.sha256(origin_raw).hexdigest(), **hashes})


def execute_noncooperation(run, inputs, consumer, binding, *, repository):
    if not native_execution_supported():
        raise evidence.ConformanceError("PrerequisiteMissing")
    _, _, selected, _ = artifact_process_context(run, inputs, consumer, binding)
    if len(selected) + 4 > 16:
        raise evidence.ConformanceError("EvidenceIncomplete")
    observations = []
    for offset, scenario in enumerate(SCENARIOS):
        inputs, assembly, selected, _ = artifact_process_context(run, inputs, consumer, binding)
        resource = "retention-" + uuid.uuid4().hex
        request = _request(run, resource, scenario, repository)
        request_path = f"stores/{resource}-control/request.json"
        descriptor = run._directory_descriptor("stores")
        try:
            os.mkdir(resource, mode=0o700, dir_fd=descriptor)
            os.mkdir(resource + "-control", mode=0o700, dir_fd=descriptor)
        finally:
            os.close(descriptor)
        request_data = evidence.canonical_bytes(request)
        _write_owned_input(run, run.root / request_path, request_data)
        result = run.command(
            _arguments(run, inputs, assembly, request_path, request_data),
            cwd=run.root, scope="recovery", record_execution=True,
            inspect_at_barrier=60 + offset, stop_at_barrier=70 + offset,
            execution_inputs=tuple(sorted({*selected, request_path})), execution_outputs=_outputs(request))
        if result.exit_code != -9:
            _require_successful_capture(result)
            raise evidence.ConformanceError("ProofMismatch")
        if (tuple(dict(row) for row in result.events) != (
                {"event": "barrier", "code": "None", "value": 60 + offset},
                {"event": "barrier", "code": "None", "value": 70 + offset})
                or result.execution_record_sha256 is None
                or hashlib.sha256(run.read_execution_record(run.command_sequence)).hexdigest()
                != result.execution_record_sha256):
            raise evidence.ConformanceError("ProofMismatch")
        observations.append(admit_noncooperation(
            run, inputs, consumer, binding, repository=repository, resource_id=resource,
            scenario=scenario, sequence=run.command_sequence))
    for field in ("sessionId", "childStartSha256"):
        if len({row[field] for row in observations}) != len(SCENARIOS):
            raise evidence.ConformanceError("ProofMismatch")
    return tuple(observations)
