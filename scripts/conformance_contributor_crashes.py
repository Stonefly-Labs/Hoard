"""Supplied-factory crash orchestration and independent original-controller admission."""

import hashlib
import os
from pathlib import Path
import time
from types import MappingProxyType

import conformance_evidence as evidence
import conformance_sources as sources
from conformance_execution import native_execution_supported


BOUNDARIES = MappingProxyType(dict(zip(("B0", "B1", "B2", "B3", "D0", "D1"), range(40, 46), strict=True)))
CASE_ID = "contributor-artifact-component"


def admit_readback(data, state_data, *, boundary, run_id, case_id):
    if boundary not in BOUNDARIES:
        raise evidence.ConformanceError("ProofMismatch")
    observed = evidence._runtime_json(data, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "runId": evidence._uuid, "caseId": evidence.stable_id,
        "boundary": evidence._one_of(*BOUNDARIES),
        "ownerFenced": evidence._boolean, "reconstructed": evidence._boolean,
        "reclamation": evidence._one_of("NotApplicable", "Pending", "Reclaimed"),
        "contentSha256": evidence.sha256, "contentLength": evidence._integer,
        "controlSha256": evidence.sha256, "controlLength": evidence._integer,
        "outcome": evidence._one_of("Published", "Removed"), "receiptId": evidence._uuid,
    }, limit=16384)
    if not isinstance(state_data, bytes) or not 0 < len(state_data) <= 16384:
        raise evidence.ConformanceError("OutputLimitExceeded")
    state = evidence.load_json(state_data)
    pattern = bytes((index * 17 + 11) % 256 for index in range(256))
    control = b"acknowledged independent control before crash"
    if (not isinstance(state, dict) or not isinstance(state.get("Control"), dict)
            or observed["runId"] != run_id or observed["caseId"] != case_id
            or observed["boundary"] != boundary or state.get("Run") != run_id or state.get("Barrier") != boundary
            or observed["ownerFenced"] is not True
            or observed["reconstructed"] is not (boundary in ("B0", "B1"))
            or observed["reclamation"] != {"D0": "Pending", "D1": "Reclaimed"}.get(boundary, "NotApplicable")
            or observed["outcome"] != ("Removed" if boundary.startswith("D") else "Published")
            or observed["contentLength"] != 1048576
            or observed["contentSha256"] != hashlib.sha256(pattern * 4096).hexdigest()
            or observed["controlLength"] != len(control)
            or observed["controlSha256"] != hashlib.sha256(control).hexdigest()
            or observed["contentSha256"] != state.get("TargetDigest")
            or observed["contentLength"] != state.get("TargetLength")
            or observed["controlSha256"] != state["Control"].get("Digest")
            or observed["controlLength"] != state["Control"].get("Length")
            or boundary == "B3" and observed["receiptId"] != state.get("AcknowledgedReceipt")):
        raise evidence.ConformanceError("ProofMismatch")
    return observed


def _layout(lease, boundary):
    resource = evidence.stable_id(lease.resource_id)
    if boundary not in BOUNDARIES:
        raise evidence.ConformanceError("ProofMismatch")
    name = f"contributor-crash-{resource}-{boundary}"
    control = f"stores/{name}"
    return control, f"{control}/state.json", f"proofs/{name}"


def _context(run, inputs, consumer, binding):
    from conformance_contributors import artifact_binding_profile, artifact_process_context

    context = artifact_process_context(run, inputs, consumer, binding)
    if artifact_binding_profile(binding.registration["declaration"])["durability"] != "LocalProcessCrash":
        raise evidence.ConformanceError("BindingInvalid")
    if len(context[2]) + 7 > 16:
        raise evidence.ConformanceError("EvidenceIncomplete")
    return context


def _request(run, lease, boundary, repository, action, source_origin=None, source_index=None):
    control, state, prefix = _layout(lease, boundary)
    return f"{control}/{action}-request.json", {
        "schemaVersion": 1, "qualification": False, "action": action, "boundary": boundary,
        "runId": run.run_id, "caseId": CASE_ID, "resourceId": lease.resource_id,
        "descriptor": lease.descriptor, "repositoryRoot": str(Path(repository).absolute()),
        "statePath": state, "originPath": f"{prefix}-{action}-origin.json",
        "readbackPath": f"{prefix}-{action}-readback.json",
        "sourceSessionId": None if source_origin is None else evidence.load_json(source_origin)["sessionId"],
        "stateSha256": None if source_index is None else source_index["stateSha256"]}


def _arguments(run, inputs, assembly, request_path, request_data):
    return ["dotnet", "exec", "--fx-version", inputs["environment"]["runtime"], str(assembly),
            "artifact-crash", str(run.root), request_path, hashlib.sha256(request_data).hexdigest()]


def _source_index(data, source_data, state_data, run_id, boundary):
    value = evidence._runtime_json(data, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "kind": evidence._constant("artifact-crash-source"), "runId": evidence._uuid,
        "caseId": evidence.stable_id, "boundary": evidence._one_of(*BOUNDARIES),
        "sessionId": evidence._uuid, "stateSha256": evidence.sha256, "originSha256": evidence.sha256,
    }, limit=16384)
    if (value["runId"] != run_id or value["caseId"] != CASE_ID or value["boundary"] != boundary
            or value["sessionId"] != evidence.load_json(source_data).get("sessionId")
            or value["stateSha256"] != hashlib.sha256(state_data).hexdigest()
            or value["originSha256"] != hashlib.sha256(source_data).hexdigest()):
        raise evidence.ConformanceError("ProofMismatch")
    return value


def admit_crash(run, inputs, consumer, binding, *, repository, lease, boundary,
                source_sequence, recovery_sequence):
    inputs, assembly, selected, declaration = _context(run, inputs, consumer, binding)
    if (type(source_sequence) is not int or type(recovery_sequence) is not int
            or not 0 < source_sequence < recovery_sequence <= run.command_sequence or run.live_children()):
        raise evidence.ConformanceError("ProofMismatch")
    _, state_path, prefix = _layout(lease, boundary)
    state_data = sources._readonly(run.root / state_path, 16384)
    source_path, index_path = f"{prefix}-source-origin.json", f"{prefix}-source-readback.json"
    source_data = sources._readonly(run.root / source_path, 65536)
    index = _source_index(sources._readonly(run.root / index_path, 16384),
                          source_data, state_data, run.run_id, boundary)
    receipts, controls = [], []
    for action, sequence in (("source", source_sequence), ("recover", recovery_sequence)):
        path, request = _request(run, lease, boundary, repository, action, source_data, index)
        if action == "source":
            path, request = _request(run, lease, boundary, repository, action)
        raw_request = sources._readonly(run.root / path, 16384)
        if raw_request != evidence.canonical_bytes(request):
            raise evidence.ConformanceError("InputChanged")
        input_paths = {*selected, path}
        if action == "recover":
            input_paths.update((state_path, source_path, index_path))
        captured = evidence.input_manifest(run.root, sorted(input_paths))
        outputs = evidence.input_manifest(run.root, (request["originPath"], request["readbackPath"]))
        control_raw = sources._readonly(run.root / f"proofs/recovery-command-{sequence:04}.json", 65536)
        control = evidence.load_json(control_raw)
        if action == "source":
            sources.admit_recovery_barrier(control, sequence, BOUNDARIES[boundary])
        else:
            sources.admit_owned_command(
                control, sequence, scope="recovery", detail=None, exit_code=0, max_duration=300000)
        raw = sources.native_control_record(
            run, sequence, control_raw,
            arguments=_arguments(run, inputs, assembly, path, raw_request), cwd=run.root,
            input_files=captured, output_files=outputs, directory_lease=lease)
        receipts.append(hashlib.sha256(raw).hexdigest())
        controls.append(control)
    if (controls[0]["endedMs"] > controls[1]["startedMs"]
            or controls[0]["childStartSha256"] == controls[1]["childStartSha256"]):
        raise evidence.ConformanceError("ProofMismatch")
    recovery_data = sources._readonly(run.root / f"{prefix}-recover-origin.json", 65536)
    recovery_path = _request(run, lease, boundary, repository, "recover", source_data, index)[0]
    recovery_hash = hashlib.sha256(sources._readonly(run.root / recovery_path, 16384)).hexdigest()
    recovery = evidence.ingest_artifact_recovery_origin(
        inputs, recovery_data, binding_id=inputs["bindings"][0]["bindingId"], case_id=CASE_ID,
        component_inputs=consumer["components"], declaration_data=declaration, source_data=source_data,
        recovery_input_sha256=recovery_hash)
    readback_data = sources._readonly(run.root / f"{prefix}-recover-readback.json", 16384)
    admit_readback(readback_data, state_data, boundary=boundary, run_id=run.run_id, case_id=CASE_ID)
    return MappingProxyType({
        "boundary": boundary, "sourceParentSha256": receipts[0], "recoveryParentSha256": receipts[1],
        "sourceOriginSha256": index["originSha256"], "stateSha256": index["stateSha256"],
        "recoveryOriginSha256": hashlib.sha256(recovery_data).hexdigest(),
        "recoveryInputSha256": recovery_hash, "readbackSha256": hashlib.sha256(readback_data).hexdigest(),
        "sourceSessionId": index["sessionId"], "recoverySessionId": recovery["sessionId"],
        "directoryLease": MappingProxyType(run._directory_lease_snapshot(lease))})


def execute_crashes(run, inputs, consumer, binding, *, repository):
    from conformance_contributors import _require_successful_capture, _write_owned_input

    if not native_execution_supported():
        raise evidence.ConformanceError("PrerequisiteMissing")
    inputs, assembly, _, _ = _context(run, inputs, consumer, binding)
    observations = []
    for boundary in BOUNDARIES:
        lease = run.lease_directory()
        control, state_path, prefix = _layout(lease, boundary)
        descriptor = run._directory_descriptor("stores")
        try:
            os.mkdir(Path(control).name, mode=0o700, dir_fd=descriptor)
        finally:
            os.close(descriptor)
        source_data = index = None
        sequences = []
        for action in ("source", "recover"):
            inputs, assembly, selected, _ = _context(run, inputs, consumer, binding)
            path, request = _request(run, lease, boundary, repository, action, source_data, index)
            raw_request = evidence.canonical_bytes(request)
            _write_owned_input(run, run.root / path, raw_request)
            paths = {*selected, path}
            if action == "recover":
                paths.update((state_path, f"{prefix}-source-origin.json", f"{prefix}-source-readback.json"))
            observed = run.command(
                _arguments(run, inputs, assembly, path, raw_request), cwd=run.root, scope="recovery",
                record_execution=True, directory_lease=lease, execution_inputs=tuple(sorted(paths)),
                execution_outputs=(request["originPath"], request["readbackPath"]),
                **({"stop_at_barrier": BOUNDARIES[boundary]} if action == "source" else {}))
            if action == "recover" or any(row["code"] != "None" for row in observed.events):
                _require_successful_capture(observed)
            sequences.append(run.command_sequence)
            expected = ({"event": "barrier", "code": "None", "value": BOUNDARIES[boundary]}
                        if action == "source" else {"event": "test", "code": "None", "value": 1})
            if (observed.exit_code != (-9 if action == "source" else 0)
                    or tuple(dict(row) for row in observed.events) != (expected,)
                    or observed.execution_record_sha256 is None or run.live_children()
                    or hashlib.sha256(run.read_execution_record(run.command_sequence)).hexdigest()
                    != observed.execution_record_sha256):
                raise evidence.ConformanceError("ProofMismatch")
            _context(run, inputs, consumer, binding)
            if action == "source":
                source_data = sources._readonly(run.root / request["originPath"], 65536)
                state_data = sources._readonly(run.root / state_path, 16384)
                index = _source_index(sources._readonly(run.root / request["readbackPath"], 16384),
                                      source_data, state_data, run.run_id, boundary)
                run._capture_execution_inputs((state_path,), time.monotonic() + 5)
        observations.append(admit_crash(
            run, inputs, consumer, binding, repository=repository, lease=lease, boundary=boundary,
            source_sequence=sequences[0], recovery_sequence=sequences[1]))
    return tuple(observations)
