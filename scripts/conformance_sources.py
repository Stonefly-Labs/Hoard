"""Independent source corroboration; files or session claims alone cannot qualify."""

from collections.abc import Mapping
import ast
import base64
import hashlib
import math
from pathlib import Path
import re
import sys
import time
from types import MappingProxyType
import uuid
from xml.sax.saxutils import escape

import conformance_evidence as evidence
from conformance_case_catalog import (
    AUTHORITY_INTEGRATION_ROWS, CATEGORY_BINDING_SLOTS, CATEGORY_MUTATION_METHODS,
    METADATA_INVENTORY_SOURCE_WITNESSES, METADATA_RECOVERY_SOURCE_WITNESS,
    ORIGINAL_ARTIFACT_PROOF_SOURCES,
    ORIGINAL_INSPECTION_LITERAL_WITNESSES, ORIGINAL_INSPECTION_WITNESSES,
    category_execution_partitions, category_mutation_witnesses, category_runtime_cases, category_runtime_packages,
    metadata_common_consumer_origin_counts, metadata_common_consumer_tests, hook_admission_tests, obligation_controls,
)
from conformance_execution import OwnedRun, no_symlinks


METADATA_RECOVERY_SCENARIOS = (
    ("mutation", (("M0", 0), ("M1", 1), ("M2", 2))),
    ("upgrade", tuple((f"U{index}", 10 + index) for index in range(5))),
    ("restore", (("R0", 20), ("R1", 21))),
)

METADATA_INVENTORY_SOURCE_FILES = (
    "scripts/conformance_unit_checks.py", "scripts/conformance_sources.py",
    "scripts/conformance_case_catalog.py", "scripts/conformance_evidence.py",
    "scripts/conformance_execution.py", "scripts/conformance_lock_preparation.py",
    "scripts/metadata_evidence.py", "scripts/foundation_evidence.py", "scripts/lifecycle_evidence.py",
    "tests/tooling/test_metadata_evidence.py",
)

METADATA_COMMON_CONSUMER_NAMESPACE = "qualification-metadata-shared-consumer"
HOOK_ADMISSION_NAMESPACES = MappingProxyType({
    profile: "qualification-" + profile + "-hook-admission" for profile in ("metadata", "artifacts")})


def read_bounded(path, limit):
    no_symlinks(path)
    if not path.is_file() or not 0 <= path.stat().st_size <= limit:
        raise evidence.ConformanceError("OutputLimitExceeded")
    with path.open("rb") as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise evidence.ConformanceError("OutputLimitExceeded")
    return data


def _readonly(path, limit):
    raw = read_bounded(path, limit)
    if path.stat().st_mode & 0o777 != 0o400:
        raise evidence.ConformanceError("ProofMismatch")
    return raw


def source_witnesses(inputs, manifest, observed, identities):
    witnesses = observed["witnesses"]
    if (observed["diagnosticCode"] != "None" or observed["attemptId"] != manifest["attemptId"]
            or manifest["runId"] != inputs["runId"] or manifest["invocationGroupId"] != inputs["invocationGroupId"]
            or manifest["inputSha256"] != evidence.digest(inputs)
            or len(manifest["expected"]) != len(identities)
            or {entry["testIdentity"] for entry in manifest["expected"]} != set(identities)
            or len(witnesses) != len(identities) or {row["testIdentity"] for row in witnesses} != set(identities)
            or len({row["executionId"] for row in witnesses}) != len(witnesses)
            or any(row["status"] != "Passed" or observed["proofs"].get(
                f'proof-{row["executionId"]}.json') != row["proofSha256"] for row in witnesses)):
        raise evidence.ConformanceError("ProofMismatch")
    return {row["testIdentity"]: row for row in witnesses}


def authority_integration_observations(run, inputs, manifest, observed):
    if inputs["profileId"] != "artifacts" or inputs["mode"] != "qualification":
        raise evidence.ConformanceError("WitnessMissing")
    assembly_path, assembly = _control_assembly(
        run, inputs, "/tests/fixtures/conformance/Consumer/bin/package-diagnostic/Release/net10.0/"
        "Hoard.Fixtures.Conformance.Consumer.dll")
    witnesses = source_witnesses(inputs, manifest, observed, AUTHORITY_INTEGRATION_ROWS)
    packages = {(category, binding): package for category, binding, _, package in CATEGORY_BINDING_SLOTS}
    images = {assembly_path: inputs["runtimeAssemblies"][assembly_path]}
    observations = []
    for identity, (binding, metadata, _) in sorted(AUTHORITY_INTEGRATION_ROWS.items()):
        witness = witnesses[identity]
        origins = observed["originalObservations"].get(witness["executionId"], ())
        selected = (packages["metadata", metadata], packages["artifacts", binding],
                    "Hoard.Fixtures.Artifacts.HostAdapters")
        if (witness["bindingId"] != binding or len(origins) != len(selected)
                or observed["sessionOrigins"].get(witness["executionId"])):
            raise evidence.ConformanceError("ProofMismatch")
        for origin, package in zip(origins, selected):
            path = (assembly.parent / (package + ".dll")).relative_to(run.root).as_posix()
            captured = origin["components"]["contract"]
            evidence._runtime_bytes_correspondence(inputs, captured["assemblySha256"], path, package)
            if (origin["kind"] != "loaded-contract" or origin["operation"] != "contract"
                    or origin["parentObservationId"] is not None):
                raise evidence.ConformanceError("ProofMismatch")
            images[path] = captured["assemblySha256"]
        observations.append({
            "testIdentity": identity, "executionId": witness["executionId"],
            "runtimeProofSha256": witness["proofSha256"], "sourceProofSha256": evidence.digest(origins)})
    if (manifest["assemblies"][0]["path"] != assembly_path
            or len(manifest["assemblies"]) != len(images)
            or {row["path"]: row["sha256"] for row in manifest["assemblies"]} != images):
        raise evidence.ConformanceError("ProofMismatch")
    return observations


def category_consumer_images(run, inputs):
    assembly_path, assembly = _control_assembly(
        run, inputs, "/tests/fixtures/conformance/Consumer/bin/package-diagnostic/Release/net10.0/"
        "Hoard.Fixtures.Conformance.Consumer.dll")
    selected = category_runtime_packages(
        inputs, {binding for profile, binding, _, _ in CATEGORY_BINDING_SLOTS if profile == inputs["profileId"]})
    images = {assembly_path: inputs["runtimeAssemblies"][assembly_path]}
    packages = ("Hoard.Testing.Conformance",
                *(package["packageId"] for package in selected.values()),
                *("Hoard.Fixtures.Conformance.Bindings." + {
                    "memory": "Memory", "sqlite": "Sqlite", "local": "Local", "object": "ObjectSemantics"}[binding]
                  for binding in selected))
    for package in packages:
        path = (assembly.parent / (package + ".dll")).relative_to(run.root).as_posix()
        hashed = inputs["runtimeAssemblies"].get(path)
        if hashed is None:
            raise evidence.ConformanceError("InputChanged")
        evidence._runtime_bytes_correspondence(inputs, hashed, path, package)
        images[path] = hashed
    return images


def category_consumer_environment(inputs):
    packages = category_runtime_packages(
        inputs, {binding for profile, binding, _, _ in CATEGORY_BINDING_SLOTS if profile == inputs["profileId"]})
    family = "METADATA" if inputs["profileId"] == "metadata" else "ARTIFACT"
    names = {"memory": "MEMORY", "sqlite": "SQLITE", "local": "LOCAL", "object": "OBJECT"}
    return {**{f"HOARD_{family}_{names[binding]}_PACKAGE_SHA256": package["sha256"]
               for binding, package in sorted(packages.items(), key=lambda item: item[1]["packageId"])},
            "HOARD_ORIGIN_RUN_ID": inputs["runId"]}


def metadata_common_consumer_origin_inputs(run, inputs):
    if inputs["profileId"] != "metadata":
        raise evidence.ConformanceError("WitnessMissing")
    return category_consumer_origin_inputs(run, inputs)


def category_consumer_origin_inputs(run, inputs):
    profile = inputs["profileId"]
    if profile not in HOOK_ADMISSION_NAMESPACES:
        raise evidence.ConformanceError("WitnessMissing")
    images = category_consumer_images(run, inputs)
    directory = Path(next(iter(images))).parent
    providers = (("memory", "Memory"), ("sqlite", "Sqlite")) if profile == "metadata" else (
        ("local", "Local"), ("object", "ObjectSemantics"))
    roles = ("store", "schema") if profile == "metadata" else ("store", "validator", "maintenance", "lifetime")
    return {
        binding: {
            role: ((directory / (package + ".dll")).as_posix(), package)
            for role, package in (
                *((role, "Hoard.Fixtures.Conformance.Bindings." + adapter)
                  for role in ("factory", "session", "faults", "authority")),
                *((role, "Hoard.Fixtures." + profile.title() + "." + adapter) for role in roles))}
        for binding, adapter in providers}


def metadata_common_consumer_sdk_paths(consumer_path):
    path = evidence.relative_path(consumer_path)
    suffix = ("tests/fixtures/conformance/Consumer/bin/package-diagnostic/Release/net10.0/"
              "Hoard.Fixtures.Conformance.Consumer.dll")
    if not path.endswith("/" + suffix):
        raise evidence.ConformanceError("InputChanged")
    return ((Path(path).parent / "Hoard.Testing.Conformance.dll").as_posix(),
            path.removesuffix(suffix) + (
                "tests/contracts/Hoard.Metadata.Tests/bin/wrapper-diagnostic/Release/net10.0/"
                "Hoard.Testing.Conformance.dll"))


def metadata_common_consumer_sdk_images(run, inputs):
    images = category_consumer_images(run, inputs)
    paths = metadata_common_consumer_sdk_paths(next(iter(images)))
    expected = images[paths[0]]
    for path in paths:
        if (inputs["runtimeAssemblies"].get(path) != expected
                or hashlib.sha256(_readonly(run.root / path, 16 * 1024 * 1024)).hexdigest() != expected):
            raise evidence.ConformanceError("InputChanged")
        evidence._runtime_bytes_correspondence(inputs, expected, path, "Hoard.Testing.Conformance")
    return {path: expected for path in paths}


def metadata_common_consumer_manifest(run, inputs, attempt_id):
    return _category_consumer_manifest(run, inputs, attempt_id, hooks=False)


def hook_admission_manifest(run, inputs, attempt_id):
    return _category_consumer_manifest(run, inputs, attempt_id, hooks=True)


def _category_consumer_manifest(run, inputs, attempt_id, *, hooks):
    profile = inputs["profileId"]
    if (inputs["mode"] != "qualification" or profile not in HOOK_ADMISSION_NAMESPACES
            or not hooks and profile != "metadata"):
        raise evidence.ConformanceError("WitnessMissing")
    tests = hook_admission_tests(profile) if hooks else metadata_common_consumer_tests()
    namespace = HOOK_ADMISSION_NAMESPACES[profile] if hooks else METADATA_COMMON_CONSUMER_NAMESPACE
    images = category_consumer_images(run, inputs)
    packages = category_runtime_packages(inputs, {binding for binding, _ in tests.values()})
    return {
        "schemaVersion": 1, "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "attemptId": evidence._uuid(attempt_id), "attemptSequence": 1, "purpose": "execution",
        "inputSha256": evidence.digest(inputs),
        "runInputsPath": f"proofs/{namespace}-native-inputs.json",
        "assemblies": [
            {"id": f"consumer-component-{index}", "path": path, "sha256": hashed}
            for index, (path, hashed) in enumerate(images.items())],
        "packages": [{
            "id": package["packageId"],
            "path": f'feed/candidate/{package["packageId"]}.{package["version"]}.nupkg',
            "sha256": package["sha256"]} for package in packages.values()],
        "expected": [{
            "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
            "assemblyId": "consumer-component-0", "packageId": packages[binding]["packageId"],
            "bindingId": binding, "matrixId": "none", "assertionSymbol": None, "caseId": case_id}
            for identity, (binding, case_id) in sorted(tests.items())]}


def native_metadata_common_consumer_control(run, inputs, *, started_ms, ended_ms):
    return _native_category_consumer_control(run, inputs, started_ms=started_ms, ended_ms=ended_ms, hooks=False)


def native_hook_admission_control(run, inputs, *, started_ms, ended_ms):
    return _native_category_consumer_control(run, inputs, started_ms=started_ms, ended_ms=ended_ms, hooks=True)


def _native_category_consumer_control(run, inputs, *, started_ms, ended_ms, hooks):
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    inputs = evidence.admit_entity("RunInputs", inputs)
    started_ms, ended_ms = evidence._number(started_ms), evidence._number(ended_ms)
    profile = inputs["profileId"]
    if (profile not in HOOK_ADMISSION_NAMESPACES or not hooks and profile != "metadata"
            or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id or ended_ms < started_ms):
        raise evidence.ConformanceError("InputChanged")
    namespace = HOOK_ADMISSION_NAMESPACES[profile] if hooks else METADATA_COMMON_CONSUMER_NAMESPACE
    graph_path = f"proofs/{namespace}-native-executions.json"
    graph_raw = _readonly(run.root / graph_path, 64 * 1024)
    graph = evidence._runtime_json(graph_raw, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "runId": evidence._constant(run.run_id),
        "invocationGroupId": evidence._constant(inputs["invocationGroupId"]),
        "inputsSha256": evidence._constant(evidence.digest(inputs)),
        "attemptId": evidence._uuid, "commandSequence": evidence._integer,
        "executionRecordSha256": evidence.sha256,
    }, limit=64 * 1024)
    attempt, sequence = graph["attemptId"], graph["commandSequence"]
    if not 0 < sequence <= run.command_sequence:
        raise evidence.ConformanceError("OwnershipInvalid")
    manifest_path = f"runtime-input-{attempt}.json"
    manifest_raw = _readonly(run.root / manifest_path, 1024 * 1024)
    manifest = _category_consumer_manifest(run, inputs, attempt, hooks=hooks)
    owner_path = "runtime-owner.json"
    owner_raw = _readonly(run.root / owner_path, 64 * 1024)
    owner = {
        "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": inputs["invocationGroupId"],
        "rootId": run.root_id, "rootPathSha256": hashlib.sha256(str(run.root).encode()).hexdigest()}
    input_raw = _readonly(run.root / manifest["runInputsPath"], 16 * 1024 * 1024)
    if (manifest_raw != evidence.canonical_bytes(manifest) or owner_raw != evidence.canonical_bytes(owner)
            or input_raw != evidence.canonical_bytes(inputs)):
        raise evidence.ConformanceError("InputChanged")
    output = f"runtime-{attempt}"
    lines_path, completion_path = f"{output}/witnesses.jsonl", f"{output}/completion.json"
    lines_raw = _readonly(run.root / lines_path, 1024 * 1024)
    identities = hook_admission_tests(profile) if hooks else metadata_common_consumer_tests()
    if len(lines_raw.splitlines()) != len(identities):
        raise evidence.ConformanceError("ProofMismatch")
    proofs = {}
    for line in lines_raw.splitlines():
        witness = evidence.load_json(line)
        if not isinstance(witness, dict):
            raise evidence.ConformanceError("ProofMismatch")
        filename = f'proof-{evidence._uuid(witness.get("executionId"))}.json'
        if filename in proofs:
            raise evidence.ConformanceError("ProofMismatch")
        proofs[filename] = _readonly(run.root / output / filename, 64 * 1024)
    completion_raw = _readonly(run.root / completion_path, 64 * 1024)
    observed = evidence.inspect_runtime_attempt(
        inputs=inputs, manifest_data=manifest_raw, owner_data=owner_raw, witnesses_data=lines_raw,
        proofs=proofs, completion_data=completion_raw,
        expected_tests={identity: (binding, "none") for identity, (binding, _) in identities.items()},
        manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(), owner_sha256=hashlib.sha256(owner_raw).hexdigest(),
        started_ms=started_ms, ended_ms=ended_ms,
        origin_inputs=category_consumer_origin_inputs(run, inputs))["observation"]
    witnesses = source_witnesses(inputs, manifest, observed, identities)
    descriptors = {row["bindingId"]: row["descriptorSha256"] for row in inputs["bindings"]}
    counts = {identity: 1 for identity in identities} if hooks else metadata_common_consumer_origin_counts()
    for identity, row in witnesses.items():
        origins = observed["sessionOrigins"][row["executionId"]]
        if (row["bindingId"] != identities[identity][0] or len(origins) != counts[identity]
                or observed["originalObservations"][row["executionId"]]
                or any(origin["descriptorSha256"] != descriptors[row["bindingId"]] for origin in origins)):
            raise evidence.ConformanceError("ProofMismatch")
    record_raw = run.read_execution_record(sequence)
    record = evidence.load_json(record_raw)
    fields = {"schemaVersion", "sequence", "childPid", "childStartSha256", "startedMs", "endedMs",
              "exitCode", "diagnosticCode", "groupState", "scope"}
    if not isinstance(record, dict) or set(record) != fields | {
            "runId", "rootId", "argvSha256", "cwdSha256", "inputFiles"}:
        raise evidence.ConformanceError("OwnershipInvalid")
    admit_owned_command({key: record[key] for key in fields}, sequence,
                        scope="ordinary", detail=None, exit_code=0, max_duration=180000)
    assembly = run.root / manifest["assemblies"][0]["path"]
    settings_path = f"stores/settings-{attempt}.runsettings"
    settings_raw = _readonly(run.root / settings_path, 256 * 1024)
    environment = "<EnvironmentVariables>" + "".join(
        f"<{key}>{escape(value)}</{key}>" for key, value in category_consumer_environment(inputs).items()
    ) + "</EnvironmentVariables>"
    execution_path = f"proofs/category-command-{attempt}-execution.json"
    execution_raw = _readonly(run.root / execution_path, 64 * 1024)
    native_path = f"proofs/execution-command-{sequence:04}.json"
    images = {row["path"]: row["sha256"] for row in manifest["assemblies"]}
    shared_sdk_images = {} if hooks else metadata_common_consumer_sdk_images(run, inputs)
    if (run.live_children() or record["runId"] != run.run_id or record["rootId"] != run.root_id
            or not 1 < record["childPid"] <= 2**31 - 1
            or not started_ms <= record["startedMs"] <= record["endedMs"] <= ended_ms
            or any(not record["startedMs"] <= row["startedMs"] <= row["endedMs"] <= record["endedMs"]
                   for row in witnesses.values())
            or settings_raw != runtime_settings(run.root, assembly, attempt, evidence.digest(manifest),
                                                hashlib.sha256(owner_raw).hexdigest(), environment)
            or record["argvSha256"] != evidence.digest(runtime_arguments(
                assembly, run.root / settings_path, [row["testIdentity"] for row in manifest["expected"]]))
            or record["cwdSha256"] != hashlib.sha256(str(assembly.parent.absolute()).encode()).hexdigest()
            or record["inputFiles"] != {
                manifest_path: hashlib.sha256(manifest_raw).hexdigest(),
                owner_path: hashlib.sha256(owner_raw).hexdigest(),
                manifest["runInputsPath"]: evidence.digest(inputs),
                settings_path: hashlib.sha256(settings_raw).hexdigest(), **images, **shared_sdk_images}
            or any(hashlib.sha256(_readonly(run.root / path, 16 * 1024 * 1024)).hexdigest() != hashed
                   for path, hashed in images.items())
            or _readonly(run.root / native_path, 64 * 1024) != record_raw
            or hashlib.sha256(record_raw).hexdigest() != graph["executionRecordSha256"]
            or execution_raw != evidence.canonical_bytes({
                "schemaVersion": 1, "qualification": False, "nativeContainment": True,
                "runId": run.run_id, "rootId": run.root_id, "invocationGroupId": inputs["invocationGroupId"],
                "attemptId": attempt, "purpose": "execution", "commandSequence": sequence,
                "inputsSha256": evidence.digest(inputs), "executionRecordSha256": hashlib.sha256(record_raw).hexdigest(),
                "manifestSha256": evidence.digest(manifest),
                "settingsSha256": hashlib.sha256(settings_raw).hexdigest()})):
        raise evidence.ConformanceError("ProofMismatch")
    packets = {
        graph_path: graph_raw, manifest_path: manifest_raw, owner_path: owner_raw,
        manifest["runInputsPath"]: input_raw, lines_path: lines_raw, completion_path: completion_raw,
        settings_path: settings_raw, execution_path: execution_raw, native_path: record_raw,
        **{f"{output}/{path}": raw for path, raw in proofs.items()}}
    control = {
        "hook-admission-sdk-consumer" if hooks else "shared-metadata-sdk-consumer":
            tuple(hashlib.sha256(raw).hexdigest() for raw in packets.values())}
    if hooks:
        control.update({name: (hashlib.sha256(graph_raw).hexdigest(),) for name in obligation_controls(5)})
    return MappingProxyType({
        "controls": MappingProxyType(control), "sourceProofs": MappingProxyType(packets),
        **({"observation": observed} if hooks else {})})


def category_mutation_observations(run, inputs, manifest, observed, *, sequence, started_ms, ended_ms):
    profile = inputs["profileId"]
    corrected = category_mutation_witnesses(profile, corrected=True)
    witnesses = source_witnesses(inputs, manifest, observed, corrected)
    images = category_consumer_images(run, inputs)
    if (len(manifest["assemblies"]) != len(images)
            or {row["path"]: row["sha256"] for row in manifest["assemblies"]} != images
            or manifest["assemblies"][0]["path"] != next(iter(images))
            or any(row["bindingId"] != corrected[row["testIdentity"]] for row in witnesses.values())):
        raise evidence.ConformanceError("ProofMismatch")
    attempt = manifest["attemptId"]
    link_path = f"proofs/category-mutation-{attempt}-fault.json"
    link_raw = _readonly(run.root / link_path, 64 * 1024)
    link = evidence._runtime_json(link_raw, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "runId": evidence._constant(inputs["runId"]), "invocationGroupId": evidence._constant(inputs["invocationGroupId"]),
        "attemptId": evidence._constant(attempt), "inputsSha256": evidence._constant(evidence.digest(inputs)),
        "profileId": evidence._constant(profile), "faultyAttemptId": evidence._uuid,
        "commandSequence": evidence._integer,
    }, limit=64 * 1024)
    faulty_attempt, faulty_sequence = link["faultyAttemptId"], link["commandSequence"]
    if (not 0 < faulty_sequence < sequence or faulty_attempt == attempt
            or inputs["mode"] != "qualification" or inputs["runId"] != run.run_id):
        raise evidence.ConformanceError("OwnershipInvalid")
    manifest_path = f"runtime-input-{faulty_attempt}.json"
    faulty_manifest_raw = _readonly(run.root / manifest_path, 1024 * 1024)
    faulty_manifest = evidence.load_json(faulty_manifest_raw)
    output = f"runtime-{faulty_attempt}"
    lines_path, completion_path = f"{output}/witnesses.jsonl", f"{output}/completion.json"
    lines_raw = _readonly(run.root / lines_path, 1024 * 1024)
    lines = lines_raw.splitlines()
    if len(lines) != len(corrected):
        raise evidence.ConformanceError("ProofMismatch")
    proofs = {}
    for line in lines:
        row = evidence.load_json(line)
        if not isinstance(row, dict):
            raise evidence.ConformanceError("ProofMismatch")
        execution = evidence._uuid(row.get("executionId"))
        path = f"proof-{execution}.json"
        proofs[path] = _readonly(run.root / output / path, 64 * 1024)
    owner_raw = _readonly(run.root / "runtime-owner.json", 64 * 1024)
    completion_raw = _readonly(run.root / completion_path, 64 * 1024)
    expected = category_mutation_witnesses(profile, corrected=False)
    failure = evidence.inspect_runtime_attempt(
        inputs=inputs, manifest_data=faulty_manifest_raw, owner_data=owner_raw,
        witnesses_data=lines_raw, proofs=proofs, completion_data=completion_raw,
        expected_tests={identity: (binding, "none") for identity, binding in expected.items()},
        manifest_sha256=hashlib.sha256(faulty_manifest_raw).hexdigest(),
        owner_sha256=hashlib.sha256(owner_raw).hexdigest(), started_ms=started_ms, ended_ms=ended_ms)["observation"]
    assertion = CATEGORY_MUTATION_METHODS[profile][2]
    expected_manifest = {
        **manifest, "attemptId": faulty_attempt, "expected": [{
            **next(entry for entry in manifest["expected"] if entry["bindingId"] == binding),
            "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0], "assertionSymbol": assertion}
            for identity, binding in sorted(expected.items())]}
    if (faulty_manifest != expected_manifest
            or failure["diagnosticCode"] != "AssertionFailed"
            or len(failure["witnesses"]) != len(expected)
            or {row["testIdentity"] for row in failure["witnesses"]} != expected.keys()
            or {row["executionId"] for row in failure["witnesses"]} & {
                row["executionId"] for row in observed["witnesses"]}
            or any(row["status"] != "Failed" or row["bindingId"] != expected[row["testIdentity"]]
                   for row in failure["witnesses"])
            or any(entry["caseId"] != "QC-04" or entry["assertionSymbol"] != assertion
                   or entry["assemblyId"] != manifest["assemblies"][0]["id"]
                   for entry in faulty_manifest["expected"])
            or any(evidence.load_json(raw)["failureKind"] != "Assertion"
                   or evidence.load_json(raw)["assertionSymbol"] != assertion for raw in proofs.values())):
        raise evidence.ConformanceError("ProofMismatch")
    record_raw = run.read_execution_record(faulty_sequence)
    record = evidence.load_json(record_raw)
    fields = {"schemaVersion", "sequence", "childPid", "childStartSha256", "startedMs", "endedMs",
              "exitCode", "diagnosticCode", "groupState", "scope"}
    if not isinstance(record, dict) or set(record) != fields | {
            "runId", "rootId", "argvSha256", "cwdSha256", "inputFiles"}:
        raise evidence.ConformanceError("OwnershipInvalid")
    admit_owned_command({key: record[key] for key in fields}, faulty_sequence,
                        scope="ordinary", detail=None, exit_code=1, max_duration=180000)
    current = evidence.load_json(run.read_execution_record(sequence))
    if not isinstance(current, dict):
        raise evidence.ConformanceError("OwnershipInvalid")
    current_started = evidence._number(current.get("startedMs"))
    if (run.live_children() or not 1 < record["childPid"] <= 2**31 - 1
            or not started_ms <= record["startedMs"] <= record["endedMs"] <= current_started <= ended_ms
            or any(not record["startedMs"] <= row["startedMs"] <= row["endedMs"] <= record["endedMs"]
                   for row in failure["witnesses"])
            or record["runId"] != run.run_id or record["rootId"] != run.root_id):
        raise evidence.ConformanceError("OwnershipInvalid")
    assembly = run.root / next(iter(images))
    settings_path = f"stores/settings-{faulty_attempt}.runsettings"
    settings = run.root / settings_path
    environment = "<EnvironmentVariables>" + "".join(
        f"<{key}>{escape(value)}</{key}>" for key, value in category_consumer_environment(inputs).items()
    ) + "</EnvironmentVariables>"
    settings_raw = _readonly(settings, 256 * 1024)
    execution_path = f"proofs/category-command-{faulty_attempt}-execution.json"
    execution_raw = _readonly(run.root / execution_path, 64 * 1024)
    execution = {
        "schemaVersion": 1, "qualification": False, "nativeContainment": True,
        "runId": run.run_id, "rootId": run.root_id, "invocationGroupId": inputs["invocationGroupId"],
        "attemptId": faulty_attempt, "purpose": "execution", "commandSequence": faulty_sequence,
        "inputsSha256": evidence.digest(inputs), "executionRecordSha256": hashlib.sha256(record_raw).hexdigest(),
        "manifestSha256": hashlib.sha256(faulty_manifest_raw).hexdigest(),
        "settingsSha256": hashlib.sha256(settings_raw).hexdigest()}
    native_path = f"proofs/execution-command-{faulty_sequence:04}.json"
    if (settings_raw != runtime_settings(run.root, assembly, faulty_attempt,
                                        hashlib.sha256(faulty_manifest_raw).hexdigest(),
                                        hashlib.sha256(owner_raw).hexdigest(), environment)
            or execution_raw != evidence.canonical_bytes(execution)
            or _readonly(run.root / native_path, 64 * 1024) != record_raw
            or record["argvSha256"] != evidence.digest(runtime_arguments(assembly, settings, tuple(expected)))
            or record["cwdSha256"] != hashlib.sha256(str(assembly.parent.absolute()).encode()).hexdigest()
            or record["inputFiles"] != {
                manifest_path: hashlib.sha256(faulty_manifest_raw).hexdigest(),
                "runtime-owner.json": hashlib.sha256(owner_raw).hexdigest(),
                manifest["runInputsPath"]: evidence.digest(inputs),
                settings_path: hashlib.sha256(settings_raw).hexdigest(), **images}):
        raise evidence.ConformanceError("ProofMismatch")
    failed = {row["bindingId"]: row for row in failure["witnesses"]}
    observations = [{
        "testIdentity": identity, "executionId": row["executionId"], "runtimeProofSha256": row["proofSha256"],
        "sourceProofSha256": failed[corrected[identity]]["proofSha256"]}
        for identity, row in sorted(witnesses.items())]
    return observations, {
        link_path: link_raw, manifest_path: faulty_manifest_raw, lines_path: lines_raw,
        completion_path: completion_raw, settings_path: settings_raw, execution_path: execution_raw,
        native_path: record_raw, **{f"{output}/{path}": raw for path, raw in proofs.items()}}


def inspection_observations(root, inputs, manifest, observed, selected, bindings):
    return _consumption_observations(
        root, inputs, manifest, observed, selected, bindings,
        capture_prefix="original-inspection-", packet_prefix="inspection-", retained_prefix="source-inspection-")


def metadata_recovery_observations(root, inputs, manifest, observed, context):
    selected = {METADATA_RECOVERY_SOURCE_WITNESS: context["files"]}
    return _consumption_observations(
        root, inputs, manifest, observed, selected, {METADATA_RECOVERY_SOURCE_WITNESS: "sqlite"},
        capture_prefix="metadata-recovery-source-", packet_prefix="metadata-recovery-",
        retained_prefix="source-metadata-recovery-")


def metadata_inventory_observations(root, inputs, manifest, observed, context):
    selected = {identity: context["files"] for identity in METADATA_INVENTORY_SOURCE_WITNESSES.values()}
    return _consumption_observations(
        root, inputs, manifest, observed, selected,
        {identity: binding for binding, identity in METADATA_INVENTORY_SOURCE_WITNESSES.items()},
        capture_prefix="metadata-inventory-source-", packet_prefix="metadata-inventory-",
        retained_prefix="source-metadata-inventory-")


def _artifact_source_paths(root, attempt_id, namespace):
    evidence._uuid(attempt_id)
    if namespace not in ("artifact-transfers", "category-artifact-transfers", "qualification-artifact-transfers"):
        raise evidence.ConformanceError("WitnessMissing")
    no_symlinks(root)
    if not root.is_absolute() or root.resolve() != root or not root.is_dir():
        raise evidence.ConformanceError("OwnershipInvalid")
    capture = root / "stores" / ("original-artifact-" + attempt_id)
    selected = {}
    for identity, (kind, provider, parameter) in ORIGINAL_ARTIFACT_PROOF_SOURCES.items():
        paths = ((capture / (parameter + ".json"), capture / (parameter + "-state.json"),
                  capture / (parameter + "-recovery-errors.txt")) if kind == "crash" else
                 (capture / f"noncooperative-{provider}-{parameter}.json",) if kind == "retention" else
                 (root / f"proofs/{namespace}/transfer-{provider}-{parameter}/proof.json",))
        selected[identity] = tuple(str(path) for path in paths)
    return selected


def artifact_source_context(run, inputs, manifest, *, namespace):
    selected = _artifact_source_paths(run.root, manifest["attemptId"], namespace)
    admit_artifact_transfer_namespace(inputs, namespace)
    if (run.run_id != inputs["runId"] or manifest["runId"] != inputs["runId"]
            or manifest["invocationGroupId"] != inputs["invocationGroupId"]
            or manifest["inputSha256"] != evidence.digest(inputs)
            or len(manifest["expected"]) != len(selected)
            or {row["testIdentity"] for row in manifest["expected"]} != selected.keys()
            or any(row["bindingId"] != ORIGINAL_ARTIFACT_PROOF_SOURCES[row["testIdentity"]][1]
                   for row in manifest["expected"])):
        raise evidence.ConformanceError("ProofMismatch")
    return {
        "schemaVersion": 1, "runId": evidence._uuid(run.run_id),
        "invocationGroupId": evidence._uuid(inputs["invocationGroupId"]),
        "attemptId": manifest["attemptId"], "rootId": evidence.stable_id(run.root_id),
        "inputsSha256": evidence.digest(inputs), "rootPath": str(run.root),
        "outputDirectory": str(run.root / "stores" / ("artifact-source-capture-" + manifest["attemptId"])),
        "cases": selected}


def artifact_source_observations(root, inputs, manifest, observed, *, namespace):
    paths = _artifact_source_paths(root, manifest["attemptId"], namespace)
    admit_artifact_transfer_namespace(inputs, namespace)
    selected = {identity: {path: hashlib.sha256(read_bounded(Path(path), 16384)).hexdigest()
                           for path in files} for identity, files in paths.items()}
    return _consumption_observations(
        root, inputs, manifest, observed, selected,
        {identity: value[1] for identity, value in ORIGINAL_ARTIFACT_PROOF_SOURCES.items()},
        capture_prefix="artifact-source-capture-", packet_prefix="artifact-source-",
        retained_prefix="source-artifact-")


def artifact_source_output_seal(run, inputs, manifest, observations, *, namespace, sequence=None):
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    sequence = run.command_sequence if sequence is None else sequence
    if type(sequence) is not int or not 0 < sequence <= run.command_sequence:
        raise evidence.ConformanceError("OwnershipInvalid")
    context = artifact_source_context(run, inputs, manifest, namespace=namespace)
    attempt = manifest["attemptId"]
    context_path = f"stores/artifact-source-context-{attempt}.json"
    context_raw = _readonly(run.root / context_path, 1024 * 1024)
    if context_raw != evidence.canonical_bytes(context):
        raise evidence.ConformanceError("InputChanged")
    identities = set(context["cases"])
    if len(observations) != len(identities) or {row["testIdentity"] for row in observations} != identities:
        raise evidence.ConformanceError("ProofMismatch")
    seal_path = f"proofs/artifact-source-seal-{attempt}.json"
    raw = _readonly(run.root / seal_path, 64 * 1024)
    evidence._runtime_json(raw, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "runId": evidence._constant(inputs["runId"]),
        "invocationGroupId": evidence._constant(inputs["invocationGroupId"]),
        "attemptId": evidence._constant(attempt), "rootId": evidence._constant(run.root_id),
        "inputsSha256": evidence._constant(evidence.digest(inputs)),
        "packets": evidence._record({
            "artifact-source-" + hashlib.sha256(row["testIdentity"].encode()).hexdigest() + ".json":
                evidence._constant(row["sourceProofSha256"]) for row in observations})}, limit=64 * 1024)
    record = evidence.load_json(run.read_execution_record(sequence))
    if (not isinstance(record, dict) or record.get("runId") != run.run_id
            or record.get("rootId") != run.root_id or record.get("scope") != "ordinary"
            or record.get("groupState") != "Exited" or type(record.get("exitCode")) is not int
            or record["exitCode"] != 0 or record.get("diagnosticCode") != "None"
            or not isinstance(record.get("inputFiles"), dict)
            or record["inputFiles"].get(context_path) != hashlib.sha256(context_raw).hexdigest()
            or record.get("outputFiles") != {seal_path: hashlib.sha256(raw).hexdigest()}):
        raise evidence.ConformanceError("ProofMismatch")
    return raw


def _consumption_observations(root, inputs, manifest, observed, selected, bindings, *,
                              capture_prefix, packet_prefix, retained_prefix):
    witnesses = source_witnesses(inputs, manifest, observed, selected)
    if any(row["bindingId"] != bindings[identity] for identity, row in witnesses.items()):
        raise evidence.ConformanceError("ProofMismatch")
    capture = root / "stores" / (capture_prefix + manifest["attemptId"])
    no_symlinks(capture)
    if not capture.is_dir():
        raise evidence.ConformanceError("EvidenceIncomplete")
    expected = {packet_prefix + hashlib.sha256(identity.encode()).hexdigest() + ".json": identity
                for identity in selected}
    files = set()
    for path in capture.iterdir():
        files.add(path.name)
        if len(files) > len(expected):
            raise evidence.ConformanceError("EvidenceIncomplete")
    if files != set(expected):
        raise evidence.ConformanceError("EvidenceIncomplete")
    observations, packets = [], {}
    for name, identity in expected.items():
        raw = read_bounded(capture / name, 512 * 1024)
        evidence._runtime_json(raw, {
            "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
            "runId": evidence._constant(inputs["runId"]), "attemptId": evidence._constant(manifest["attemptId"]),
            "inputsSha256": evidence._constant(evidence.digest(inputs)),
            "testIdentity": evidence._constant(identity),
            "files": evidence._record({
                hashlib.sha256(path.encode()).hexdigest(): evidence._constant(hashed)
                for path, hashed in selected[identity].items()})}, limit=512 * 1024)
        witness = witnesses[identity]
        observations.append({
            "testIdentity": identity, "executionId": witness["executionId"],
            "runtimeProofSha256": witness["proofSha256"], "sourceProofSha256": hashlib.sha256(raw).hexdigest()})
        packets[f'proofs/{retained_prefix}{manifest["attemptId"]}-{hashlib.sha256(identity.encode()).hexdigest()}.json'] = raw
    return observations, MappingProxyType(packets)


def metadata_recovery_context(run, inputs, manifest, *, ended_ms):
    if (manifest["runId"] != inputs["runId"] or manifest["invocationGroupId"] != inputs["invocationGroupId"]
            or manifest["inputSha256"] != evidence.digest(inputs)
            or len(manifest["expected"]) != 1
            or manifest["expected"][0]["testIdentity"] != METADATA_RECOVERY_SOURCE_WITNESS
            or manifest["expected"][0]["bindingId"] != "sqlite"):
        raise evidence.ConformanceError("ProofMismatch")
    recovered = native_metadata_recovery_controls(run, inputs, started_ms=0, ended_ms=ended_ms)
    return {
        "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": inputs["invocationGroupId"],
        "attemptId": evidence._uuid(manifest["attemptId"]), "rootId": run.root_id,
        "inputsSha256": evidence.digest(inputs), "rootPath": str(run.root),
        "graphPath": "proofs/qualification-sqlite-recovery-native-executions.json",
        "sourcePath": "proofs/qualification-sqlite-recovery.json",
        "outputDirectory": str(run.root / "stores" / ("metadata-recovery-source-" + manifest["attemptId"])),
        "files": {str(run.root / path): hashlib.sha256(raw).hexdigest()
                  for path, raw in recovered["sourceProofs"].items()}}


def metadata_inventory_context(run, inputs, manifest, *, ended_ms):
    selected = {identity: binding for binding, identity in METADATA_INVENTORY_SOURCE_WITNESSES.items()}
    if (manifest["runId"] != inputs["runId"] or manifest["invocationGroupId"] != inputs["invocationGroupId"]
            or manifest["inputSha256"] != evidence.digest(inputs) or len(manifest["expected"]) != len(selected)
            or {row["testIdentity"] for row in manifest["expected"]} != selected.keys()
            or any(row["bindingId"] != selected[row["testIdentity"]] or row["caseId"] != "MP-48"
                   for row in manifest["expected"])):
        raise evidence.ConformanceError("ProofMismatch")
    recovered = native_metadata_inventory_controls(run, inputs, started_ms=0, ended_ms=ended_ms)
    return {
        "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": inputs["invocationGroupId"],
        "attemptId": evidence._uuid(manifest["attemptId"]), "rootId": run.root_id,
        "inputsSha256": evidence.digest(inputs), "rootPath": str(run.root),
        "graphPath": "proofs/qualification-metadata-inventory-native-executions.json",
        "outputDirectory": str(run.root / "stores" / ("metadata-inventory-source-" + manifest["attemptId"])),
        "files": {str(run.root / path): hashlib.sha256(raw).hexdigest()
                  for path, raw in recovered["sourceProofs"].items()}}


def runtime_settings(root, assembly, attempt, manifest_sha, owner_sha, environment):
    return (
        '<RunSettings><RunConfiguration>'
        f'<TestAdaptersPaths>{escape(str(assembly.parent))}</TestAdaptersPaths>'
        '<MaxCpuCount>1</MaxCpuCount><TestSessionTimeout>120000</TestSessionTimeout>'
        + environment +
        '</RunConfiguration><LoggerRunSettings><Loggers>'
        '<Logger friendlyName="console" enabled="False"/>'
        '<Logger friendlyName="HoardSafe" enabled="True"><Configuration>'
        f'<Root>{escape(str(root))}</Root><AttemptId>{attempt}</AttemptId>'
        f'<ManifestSha256>{manifest_sha}</ManifestSha256><OwnerSha256>{owner_sha}</OwnerSha256>'
        '</Configuration></Logger></Loggers></LoggerRunSettings></RunSettings>').encode()


def runtime_arguments(assembly, settings, identities, *, discovery=False):
    filter_text = "|".join("FullyQualifiedName=" + name
                           for name in dict.fromkeys(identity.split("(")[0] for identity in identities))
    return ["dotnet", "vstest", str(assembly), *(["--ListTests"] if discovery else []),
            f"--Settings:{settings}", f"--TestCaseFilter:{filter_text}"]


def native_control_record(run, sequence, control_raw, *, arguments, cwd, input_files, diagnostic_code="None",
                          output_files=None):
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    control = evidence.load_json(control_raw)
    fields = {"schemaVersion", "sequence", "childPid", "childStartSha256", "startedMs", "endedMs",
              "exitCode", "diagnosticCode", "groupState", "scope"}
    if (diagnostic_code not in ("None", "DeadlineExceeded")
            or not isinstance(control, dict) or not fields <= control.keys()
            or control["scope"] not in ("recovery", "transfer")
            or diagnostic_code == "DeadlineExceeded" and control["scope"] != "recovery"
            or set(control) - fields not in (
                (set(), {"barrier"}) if control["scope"] == "recovery" else ({"transfer"},))
            or control["sequence"] != sequence or control["diagnosticCode"] != diagnostic_code
            or control["groupState"] != "Exited" or run.live_children()):
        raise evidence.ConformanceError("ProofMismatch")
    raw = run.read_execution_record(sequence)
    expected = {
        **{key: control[key] for key in fields}, "runId": run.run_id, "rootId": run.root_id,
        "argvSha256": evidence.digest(arguments),
        "cwdSha256": hashlib.sha256(str(Path(cwd).absolute()).encode()).hexdigest(),
        "controlRecordSha256": hashlib.sha256(control_raw).hexdigest(),
        **({"inputFiles": input_files} if input_files else {}),
        **({"outputFiles": output_files} if output_files else {}),
    }
    if raw != evidence.canonical_bytes(expected):
        raise evidence.ConformanceError("ProofMismatch")
    return raw


def admit_owned_command(command, sequence, *, scope, detail, exit_code, max_duration):
    fields = {
        "schemaVersion", "sequence", "childPid", "childStartSha256", "startedMs", "endedMs",
        "exitCode", "diagnosticCode", "groupState", "scope",
    }
    if detail is not None:
        fields.add(detail)
    if (type(sequence) is not int or sequence <= 0
            or not isinstance(command, dict) or set(command) != fields
            or type(command["schemaVersion"]) is not int or command["schemaVersion"] != 1
            or type(command["sequence"]) is not int or command["sequence"] != sequence
            or type(command["childPid"]) is not int or command["childPid"] <= 0
            or not isinstance(command["childStartSha256"], str)
            or re.fullmatch("[0-9a-f]{64}", command["childStartSha256"]) is None
            or command["childStartSha256"] == "0" * 64
            or type(command["exitCode"]) is not int or command["exitCode"] != exit_code
            or command["diagnosticCode"] != "None" or command["groupState"] != "Exited"
            or command["scope"] != scope):
        raise evidence.ConformanceError("ProofMismatch")
    times = (command["startedMs"], command["endedMs"])
    if (any(type(item) not in (int, float) or not 0 <= item <= 2**63 - 1 or not math.isfinite(item)
            for item in times) or times[0] > times[1] or times[1] - times[0] > max_duration):
        raise evidence.ConformanceError("ProofMismatch")


def admit_transfer_measurement(command, sequence, size):
    admit_owned_command(command, sequence, scope="transfer", detail="transfer", exit_code=0, max_duration=2400000)
    measured = command["transfer"]
    fields = {"bytes", "phase", "baselineRssBytes", "osPeakRssBytes", "sampledPeakRssBytes",
              "samples", "osPeakMethod", "baselineMs", "completedMs"}
    if (type(size) is not int or size not in (268435456, 4294967296)
            or not isinstance(measured, dict) or set(measured) != fields
            or any(type(measured[key]) is not int or not 0 < measured[key] <= 2**63 - 1
                   for key in ("bytes", "baselineRssBytes", "osPeakRssBytes", "sampledPeakRssBytes", "samples"))
            or measured["bytes"] != size or measured["phase"] != "complete"
            or measured["osPeakMethod"] != "proc-status" or measured["samples"] < 2
            or not measured["baselineRssBytes"] <= measured["sampledPeakRssBytes"] <= measured["osPeakRssBytes"]
            or measured["osPeakRssBytes"] - measured["baselineRssBytes"] > 67108864):
        raise evidence.ConformanceError("ProofMismatch")
    times = (command["startedMs"], measured["baselineMs"], measured["completedMs"], command["endedMs"])
    if (any(type(item) not in (int, float) or not 0 <= item <= 2**63 - 1 or not math.isfinite(item)
            for item in times) or tuple(sorted(times)) != times):
        raise evidence.ConformanceError("ProofMismatch")


def admit_artifact_transfer_namespace(inputs, namespace):
    if (namespace not in ("artifact-transfers", "category-artifact-transfers", "qualification-artifact-transfers")
            or namespace != "artifact-transfers" and (
                inputs.get("profileId") != "artifacts" or inputs.get("mode") != (
                    "qualification" if namespace == "qualification-artifact-transfers" else "diagnostic"))):
        raise evidence.ConformanceError("ProofMismatch")


def artifact_category_transfer_namespace(inputs):
    namespace = ("qualification-artifact-transfers" if inputs.get("mode") == "qualification"
                 else "category-artifact-transfers")
    admit_artifact_transfer_namespace(inputs, namespace)
    return namespace


def admit_artifact_transfer_producer(producer, command, provider, size, expected_hash, run_id, runtime):
    import artifact_evidence as artifacts
    fields = {
        "eventName", "provider", "runId", "pid", "size", "written", "read", "expectedSha256",
        "sourceSha256", "sinkSha256", "runtime", "sourcePaced", "sinkPaced", "nonSeekable",
        "generated", "independentExpectedHash", "warmupComplete", "bufferBytes", "providerBufferLimit", "slots",
    }
    if (not isinstance(producer, dict) or set(producer) != fields or producer["eventName"] != "complete"
            or producer["pid"] != command["childPid"] or producer["expectedSha256"] != expected_hash
            or producer["runtime"] != ".NET " + runtime):
        raise evidence.ConformanceError("ProofMismatch")
    measured = command["transfer"]
    proof = {**producer, **{name: measured[name] for name in (
        "baselineRssBytes", "osPeakRssBytes", "sampledPeakRssBytes", "samples", "osPeakMethod")},
             "rssUnits": "bytes", "exitCode": command["exitCode"]}
    try:
        artifacts.verify_transfer(proof, provider, size, run_id, peak_methods=("proc-status",))
    except RuntimeError:
        raise evidence.ConformanceError("ProofMismatch") from None
    return proof


def native_artifact_transfer_source(run, inputs, provider, size, *, namespace):
    import artifact_evidence as artifacts
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    admit_artifact_transfer_namespace(inputs, namespace)
    if (inputs["runId"] != run.run_id or provider not in ("local", "object")
            or type(size) is not int or size not in (268435456, 4294967296)):
        raise evidence.ConformanceError("InputChanged")
    assembly_path, assembly = _control_assembly(
        run, inputs, "/tests/fixtures/artifacts/TransferRunner/bin/Release/net10.0/Hoard.Fixtures.Artifacts.TransferRunner.dll")
    prefix = f"proofs/{namespace}/transfer-{provider}-{size}"
    input_path = prefix + "-native-inputs.json"
    input_raw = _readonly(run.root / input_path, 16 * 1024 * 1024)
    if input_raw != evidence.canonical_bytes(inputs):
        raise evidence.ConformanceError("InputChanged")
    recipe_path = prefix + "/native-execution.json"
    recipe_raw = _readonly(run.root / recipe_path, 64 * 1024)
    recipe = evidence.load_json(recipe_raw)
    sequence = recipe.get("sequence") if isinstance(recipe, dict) else None
    if type(sequence) is not int or not 0 < sequence <= run.command_sequence:
        raise evidence.ConformanceError("ProofMismatch")
    control_path = f"proofs/transfer-command-{sequence:04}.json"
    control_raw = _readonly(run.root / control_path, 64 * 1024)
    command = evidence.load_json(control_raw)
    admit_transfer_measurement(command, sequence, size)
    producer_path = prefix + "/producer.json"
    producer_raw = _readonly(run.root / producer_path, 8192)
    expected = artifacts.expected_transfer_hash(size)
    proof = admit_artifact_transfer_producer(
        evidence.load_json(producer_raw), command, provider, size, expected, run.run_id, inputs["environment"]["runtime"])
    proof_path = prefix + "/proof.json"
    proof_raw = _readonly(run.root / proof_path, 16384)
    if proof_raw != evidence.canonical_bytes(proof):
        raise evidence.ConformanceError("ProofMismatch")
    store = run.root / f"stores/{namespace}/transfer-{provider}-{size}"
    native_raw = native_control_record(
        run, sequence, control_raw, arguments=[
            "dotnet", str(assembly), provider, str(store), str(size), expected, run.run_id, str(run.root / producer_path)],
        cwd=assembly.parent, input_files={assembly_path: inputs["runtimeAssemblies"][assembly_path],
                                         input_path: evidence.digest(inputs)},
        output_files={producer_path: hashlib.sha256(producer_raw).hexdigest()})
    expected_recipe = {
        "schemaVersion": 1, "qualification": False, "runId": run.run_id, "rootId": run.root_id,
        "invocationGroupId": inputs["invocationGroupId"], "inputsSha256": evidence.digest(inputs),
        "provider": provider, "size": size, "assemblyPath": assembly_path, "inputsPath": input_path,
        "sequence": sequence, "controllerSha256": hashlib.sha256(control_raw).hexdigest(),
        "producerSha256": hashlib.sha256(producer_raw).hexdigest(),
        "executionSha256": hashlib.sha256(native_raw).hexdigest()}
    if recipe_raw != evidence.canonical_bytes(expected_recipe):
        raise evidence.ConformanceError("ProofMismatch")
    return MappingProxyType({
        "sequence": sequence, "producerSha256": expected_recipe["producerSha256"],
        "sourceProofs": MappingProxyType({
            input_path: input_raw, recipe_path: recipe_raw, control_path: control_raw,
            producer_path: producer_raw, proof_path: proof_raw,
            f"proofs/execution-command-{sequence:04}.json": native_raw})})


def native_artifact_transfer_controls(run, inputs, *, started_ms, ended_ms):
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    inputs = evidence.admit_entity("RunInputs", inputs)
    started_ms, ended_ms = evidence._number(started_ms), evidence._number(ended_ms)
    if (inputs["profileId"] != "artifacts" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id or ended_ms < started_ms):
        raise evidence.ConformanceError("InputChanged")
    controls, proofs, previous_sequence, previous_end = {}, {}, 0, started_ms
    for provider in ("local", "object"):
        for size in (268435456, 4294967296):
            graph = native_artifact_transfer_source(
                run, inputs, provider, size, namespace="qualification-artifact-transfers")
            sequence = graph["sequence"]
            command = evidence.load_json(graph["sourceProofs"][f"proofs/transfer-command-{sequence:04}.json"])
            if (sequence <= previous_sequence
                    or not previous_end <= command["startedMs"] <= command["endedMs"] <= ended_ms
                    or set(proofs) & set(graph["sourceProofs"])):
                raise evidence.ConformanceError("ProofMismatch")
            controls[provider + ("-256m" if size == 268435456 else "-4g") + "-write-read"] = tuple(
                hashlib.sha256(raw).hexdigest() for raw in graph["sourceProofs"].values())
            proofs.update(graph["sourceProofs"])
            previous_sequence, previous_end = sequence, command["endedMs"]
    shared = tuple(hashlib.sha256(raw).hexdigest() for raw in proofs.values())
    controls.update({role: shared for role in (
        "per-transfer-os-rss", "paced-nonseekable-streams", "stricter-inner-limits")})
    return MappingProxyType({
        "controls": MappingProxyType(controls), "sourceProofs": MappingProxyType(proofs)})


def admit_artifact_noncooperation(observed, provider, scenario, phase, pid, run_id):
    fields = {
        "eventName", "phase", "pid", "runId", "provider", "scenario", "durableCrashProof",
        "cleanup", "callerCode", "admissionCode", "shutdownCode", "enteredWorkers",
        "workerPending", "borrowedStreamsIntact", "rootStillOwned", "readinessBlocked", "protectionRetained",
    }
    if (provider not in ("local", "object") or scenario not in ("source", "destination", "native")
            or phase not in ("contained", "inspected") or not isinstance(observed, dict) or set(observed) != fields
            or observed["eventName"] != "noncooperative" or observed["phase"] != phase
            or type(observed["pid"]) is not int or observed["pid"] != pid
            or observed["runId"] != run_id or observed["provider"] != provider or observed["scenario"] != scenario
            or observed["durableCrashProof"] is not False or observed["cleanup"] != "RetainedLiveOwnership"
            or observed["callerCode"] not in (
                ("DeadlineExceeded", "Uncertain") if scenario == "native" else ("CancelledBeforeCommit",))
            or observed["admissionCode"] != "CleanupIncomplete" or observed["shutdownCode"] != "CleanupIncomplete"
            or type(observed["enteredWorkers"]) is not int or observed["enteredWorkers"] != 1
            or any(observed[key] is not True for key in (
                "workerPending", "borrowedStreamsIntact", "rootStillOwned", "readinessBlocked"))
            or observed["protectionRetained"] is not (scenario != "source")):
        raise evidence.ConformanceError("ProofMismatch")


def _admit_original_artifact_uuid(value):
    if not isinstance(value, str) or len(value) != 36:
        raise evidence.ConformanceError("ProofMismatch")
    try:
        identity = uuid.UUID(value)
    except ValueError:
        raise evidence.ConformanceError("ProofMismatch") from None
    if identity.int == 0 or str(identity) != value:
        raise evidence.ConformanceError("ProofMismatch")


def _admit_original_artifact_child(proof, fields):
    if (not isinstance(proof, dict) or set(proof) != fields or proof["qualification"] is not False
            or any(type(proof[key]) is not int or not 0 < proof[key] <= 2147483647 for key in ("parentPid", "killedPid"))
            or proof["parentPid"] == proof["killedPid"]
            or type(proof["killedExitCode"]) is not int or proof["killedExitCode"] != 137):
        raise evidence.ConformanceError("ProofMismatch")
    _admit_original_artifact_uuid(proof["runId"])


def admit_original_artifact_crash(proof, state_data, barrier):
    import artifact_evidence as artifacts
    _admit_original_artifact_child(proof, {
        "provider", "qualification", "runId", "barrier", "signal", "parentPid", "killedPid",
        "killedExitCode", "recoveredPid", "reopenedExitCode", "barrierProof", "recovery"})
    handshake, recovered = proof["barrierProof"], proof["recovery"]
    if (barrier not in ("B0", "B1", "B2", "B3", "D0", "D1")
            or proof["provider"] != "local" or proof["barrier"] != barrier
            or type(proof["signal"]) is not int or proof["signal"] != 9
            or type(proof["recoveredPid"]) is not int or not 0 < proof["recoveredPid"] <= 2147483647
            or proof["recoveredPid"] in (proof["parentPid"], proof["killedPid"])
            or type(proof["reopenedExitCode"]) is not int or proof["reopenedExitCode"] != 0
            or not isinstance(state_data, bytes) or not 0 < len(state_data) <= 16384
            or not isinstance(handshake, dict) or set(handshake) != {
                "eventName", "pid", "runId", "barrier", "stateSha256", "acknowledged"}
            or handshake["eventName"] != "barrier" or type(handshake["pid"]) is not int
            or handshake["pid"] != proof["killedPid"] or handshake["runId"] != proof["runId"]
            or handshake["barrier"] != barrier or handshake["acknowledged"] is not (barrier == "B3")
            or handshake["stateSha256"] != hashlib.sha256(state_data).hexdigest()
            or not isinstance(recovered, dict) or set(recovered) != {
                "eventName", "provider", "qualification", "pid", "runId", "barrier",
                "controlReadback", "controlReceipt", "exactReceipt", "contentReadback", "ownerFenced",
                "reconstructed", "reclamation", "noDuplicateEffect", "contentSha256", "contentLength",
                "controlSha256", "controlLength", "outcome", "receiptId"}
            or type(recovered["pid"]) is not int):
        raise evidence.ConformanceError("ProofMismatch")
    _admit_original_artifact_uuid(recovered["receiptId"])
    state = evidence.load_json(state_data)
    if barrier == "B3" and (not isinstance(state, dict) or state.get("AcknowledgedReceipt") != recovered["receiptId"]):
        raise evidence.ConformanceError("ProofMismatch")
    try:
        artifacts.validate_recovery_readback(
            recovered, state, barrier, proof["runId"], proof["recoveredPid"])
    except RuntimeError:
        raise evidence.ConformanceError("ProofMismatch") from None


def admit_original_artifact_retention(proof, provider, scenario):
    _admit_original_artifact_child(proof, {
        "qualification", "durableCrashProof", "provider", "scenario", "runId",
        "parentPid", "killedPid", "killedExitCode", "observations"})
    if (proof["durableCrashProof"] is not False or proof["provider"] != provider or proof["scenario"] != scenario
            or not isinstance(proof["observations"], list) or len(proof["observations"]) != 2):
        raise evidence.ConformanceError("ProofMismatch")
    for phase, observation in zip(("contained", "inspected"), proof["observations"]):
        admit_artifact_noncooperation(observation, provider, scenario, phase, proof["killedPid"], proof["runId"])


def artifact_original_child_sources(root, inputs, attempt_id, *, namespace):
    selected = _artifact_source_paths(root, attempt_id, namespace)
    admit_artifact_transfer_namespace(inputs, namespace)
    children = {identity: tuple(Path(path) for path in selected[identity])
                for identity, (kind, _, _) in ORIGINAL_ARTIFACT_PROOF_SOURCES.items() if kind != "transfer"}
    capture = root / "stores" / ("original-artifact-" + attempt_id)
    no_symlinks(capture)
    if not capture.is_dir():
        raise evidence.ConformanceError("EvidenceIncomplete")
    expected = {path.name for paths in children.values() for path in paths}
    found = set()
    for path in capture.iterdir():
        found.add(path.name)
        if len(found) > len(expected):
            raise evidence.ConformanceError("EvidenceIncomplete")
    if found != expected:
        raise evidence.ConformanceError("EvidenceIncomplete")
    observations, proofs, child_runs = {}, {}, set()
    for identity, paths in children.items():
        kind, provider, parameter = ORIGINAL_ARTIFACT_PROOF_SOURCES[identity]
        raw = tuple(read_bounded(path, 16384) for path in paths)
        producer = evidence.load_json(raw[0])
        hashes = {"producer": hashlib.sha256(raw[0]).hexdigest()}
        if kind == "crash":
            admit_original_artifact_crash(producer, raw[1], parameter)
            if raw[2]:
                raise evidence.ConformanceError("ProofMismatch")
            hashes["state"] = hashlib.sha256(raw[1]).hexdigest()
        else:
            admit_original_artifact_retention(producer, provider, parameter)
        if producer["runId"] == inputs["runId"] or producer["runId"] in child_runs:
            raise evidence.ConformanceError("ProofMismatch")
        child_runs.add(producer["runId"])
        observations[identity] = MappingProxyType(hashes)
        proofs.update({path.relative_to(root).as_posix(): data for path, data in zip(paths, raw, strict=True)})
    return MappingProxyType({
        "observations": MappingProxyType(observations), "sourceProofs": MappingProxyType(proofs)})


def native_artifact_controller_source(run, inputs, manifest, observed, *, sequence, started_ms, ended_ms):
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    inputs = evidence.admit_entity("RunInputs", inputs)
    started_ms, ended_ms = evidence._number(started_ms), evidence._number(ended_ms)
    if (inputs["profileId"] != "artifacts" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id or type(sequence) is not int
            or not 0 < sequence <= run.command_sequence or ended_ms < started_ms):
        raise evidence.ConformanceError("InputChanged")
    witnesses = source_witnesses(inputs, manifest, observed, ORIGINAL_ARTIFACT_PROOF_SOURCES)
    if any(row["bindingId"] != ORIGINAL_ARTIFACT_PROOF_SOURCES[identity][1]
           for identity, row in witnesses.items()):
        raise evidence.ConformanceError("ProofMismatch")
    record = evidence.load_json(run.read_execution_record(sequence))
    if not started_ms <= record["startedMs"] <= record["endedMs"] <= ended_ms:
        raise evidence.ConformanceError("ProofMismatch")
    namespace = "qualification-artifact-transfers"
    transfer_sources = native_artifact_transfer_controls(
        run, inputs, started_ms=started_ms, ended_ms=record["startedMs"])
    proofs = dict(transfer_sources["sourceProofs"])
    children = artifact_original_child_sources(run.root, inputs, manifest["attemptId"], namespace=namespace)
    rows, by_transfer = [], {}
    for provider in ("local", "object"):
        for size in (268435456, 4294967296):
            prefix = f"proofs/{namespace}/transfer-{provider}-{size}"
            recipe = evidence.load_json(proofs[prefix + "/native-execution.json"])
            controller = proofs[f'proofs/transfer-command-{recipe["sequence"]:04}.json']
            row = {
                "provider": provider, "size": size, "controllerSha256": hashlib.sha256(controller).hexdigest(),
                "producerSha256": hashlib.sha256(proofs[prefix + "/producer.json"]).hexdigest(),
                "proofSha256": hashlib.sha256(proofs[prefix + "/proof.json"]).hexdigest(),
                "childStartSha256": evidence.load_json(controller)["childStartSha256"]}
            rows.append(row)
            by_transfer[provider, size] = row
    summary_path = f"proofs/{namespace}.json"
    summary = _readonly(run.root / summary_path, 64 * 1024)
    if summary != evidence.canonical_bytes({
            "qualification": False, "mode": "artifact-transfers", "code": "None",
            "inputsSha256": evidence.digest(inputs), "transfers": rows}):
        raise evidence.ConformanceError("ProofMismatch")
    captured, packets = artifact_source_observations(run.root, inputs, manifest, observed, namespace=namespace)
    seal = artifact_source_output_seal(run, inputs, manifest, captured, namespace=namespace, sequence=sequence)
    consumption_path = f'proofs/artifact-source-capture-{manifest["attemptId"]}.json'
    consumption = _readonly(run.root / consumption_path, 512 * 1024)
    if consumption != evidence.canonical_bytes({
            "schemaVersion": 1, "qualification": False, "runId": inputs["runId"],
            "invocationGroupId": inputs["invocationGroupId"], "attemptId": manifest["attemptId"],
            "inputsSha256": evidence.digest(inputs), "observations": captured,
            "outputSealSha256": hashlib.sha256(seal).hexdigest()}):
        raise evidence.ConformanceError("ProofMismatch")
    observations = []
    for identity, (kind, provider, parameter) in sorted(ORIGINAL_ARTIFACT_PROOF_SOURCES.items()):
        witness = witnesses[identity]
        hashes = ({"producer": by_transfer[provider, parameter]["proofSha256"]} if kind == "transfer" else
                  dict(children["observations"][identity]))
        observations.append({
            "testIdentity": identity, "executionId": witness["executionId"],
            "runtimeProofSha256": witness["proofSha256"], "sourceProofs": hashes})
    source_path = f'proofs/original-artifact-external-{manifest["attemptId"]}.json'
    source = _readonly(run.root / source_path, 512 * 1024)
    if source != evidence.canonical_bytes({
            "schemaVersion": 1, "qualification": False, "mode": "original-artifact-proofs",
            "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
            "attemptId": manifest["attemptId"], "inputsSha256": evidence.digest(inputs),
            "transferParentSha256": hashlib.sha256(summary).hexdigest(),
            "observations": observations, "consumptionSha256": hashlib.sha256(consumption).hexdigest()}):
        raise evidence.ConformanceError("ProofMismatch")
    return MappingProxyType({
        "sourceReceipt": source, "sourcePackets": MappingProxyType(dict(packets)),
        "sourceProofs": MappingProxyType({
            **proofs, **packets, summary_path: summary, consumption_path: consumption, source_path: source,
            f'proofs/artifact-source-seal-{manifest["attemptId"]}.json': seal})})


def admit_recovery_barrier(command, sequence, value, *, inspection=None):
    admit_owned_command(command, sequence, scope="recovery", detail="barrier", exit_code=-9, max_duration=15000)
    fields = {"value", "observedMs", "signalMs"} | ({"inspection"} if inspection is not None else set())
    if (type(value) is not int or not 0 <= value <= 65535 or not isinstance(command["barrier"], dict)
            or set(command["barrier"]) != fields
            or type(command["barrier"]["value"]) is not int or command["barrier"]["value"] != value):
        raise evidence.ConformanceError("ProofMismatch")
    barrier = command["barrier"]
    times = (command["startedMs"], barrier["observedMs"], barrier["signalMs"], command["endedMs"])
    if inspection is not None:
        observed = barrier["inspection"]
        if (type(inspection) is not int or not 0 <= inspection <= 65535 or inspection == value
                or not isinstance(observed, dict) or set(observed) != {"value", "observedMs", "requestMs"}
                or type(observed["value"]) is not int or observed["value"] != inspection):
            raise evidence.ConformanceError("ProofMismatch")
        times = (times[0], observed["observedMs"], observed["requestMs"], *times[1:])
    if (any(type(item) not in (int, float) or not 0 <= item <= 2**63 - 1 or not math.isfinite(item)
            for item in times) or tuple(sorted(times)) != times or times[-1] - times[0] > 15000):
        raise evidence.ConformanceError("ProofMismatch")


def admit_sqlite_noncooperation(observed, command, inputs_sha256):
    producer_fields = {
        "schemaVersion", "inputsSha256", "childPid", "boundaryObservations", "guards",
        "commitCode", "commitPhase", "commitRetry", "ticketSha256", "failureTicketSha256",
        "disposeCode", "incompleteCleanups", "admissionCode", "settlementCompleted",
        "cleanupState", "resourceIds", "ledgerStates",
    }
    command_fields = {
        "schemaVersion", "sequence", "childPid", "childStartSha256", "startedMs", "endedMs",
        "exitCode", "diagnosticCode", "groupState", "scope",
    }
    if (not isinstance(observed, dict) or set(observed) != producer_fields
            or not isinstance(command, dict) or set(command) != command_fields
            or type(observed["schemaVersion"]) is not int or observed["schemaVersion"] != 1
            or type(command["schemaVersion"]) is not int or command["schemaVersion"] != 1
            or observed["inputsSha256"] != inputs_sha256
            or type(observed["childPid"]) is not int or observed["childPid"] <= 0
            or type(command["childPid"]) is not int or command["childPid"] != observed["childPid"]
            or type(command["sequence"]) is not int or command["sequence"] <= 0
            or not isinstance(command["childStartSha256"], str)
            or re.fullmatch("[0-9a-f]{64}", command["childStartSha256"]) is None
            or command["childStartSha256"] == "0" * 64
            or any(type(command[key]) not in (int, float) or not math.isfinite(command[key])
                   or not 0 <= command[key] <= 2**63 - 1 for key in ("startedMs", "endedMs"))
            or command["endedMs"] - command["startedMs"] < 45000
            or type(command["exitCode"]) is not int or command["exitCode"] != -9
            or command["diagnosticCode"] != "DeadlineExceeded"
            or command["groupState"] != "Exited" or command["scope"] != "recovery"
            or type(observed["boundaryObservations"]) is not int or observed["boundaryObservations"] != 1
            or not isinstance(observed["guards"], list) or observed["guards"] != [1, 1, 1]
            or any(type(value) is not int for value in observed["guards"])
            or observed["commitCode"] != "Uncertain" or observed["commitPhase"] != "Commit"
            or observed["commitRetry"] != "Reconcile"
            or not isinstance(observed["ticketSha256"], str)
            or re.fullmatch("[0-9a-f]{64}", observed["ticketSha256"]) is None
            or observed["failureTicketSha256"] != observed["ticketSha256"]
            or observed["disposeCode"] != "CleanupIncomplete"
            or type(observed["incompleteCleanups"]) is not int or observed["incompleteCleanups"] != 1
            or observed["admissionCode"] != "Disposed" or observed["settlementCompleted"] is not False
            or observed["cleanupState"] != "Retained"
            or not isinstance(observed["resourceIds"], list) or len(observed["resourceIds"]) != 1
            or not isinstance(observed["resourceIds"][0], str)
            or re.fullmatch("[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}", observed["resourceIds"][0]) is None
            or observed["ledgerStates"] != ["Allocated", "Active", "Settling", "Retained"]):
        raise evidence.ConformanceError("ProofMismatch")


def _control_assembly(run, inputs, suffix):
    assemblies = [path for path in inputs["runtimeAssemblies"] if path.endswith(suffix)]
    if len(assemblies) != 1:
        raise evidence.ConformanceError("InputChanged")
    assembly_path = assemblies[0]
    assembly = run.root / assembly_path
    no_symlinks(assembly)
    if assembly.stat().st_mode & 0o777 != 0o400:
        raise evidence.ConformanceError("InputChanged")
    with evidence._input_root(run.root) as (_, descriptor):
        hashed, _ = evidence._source_file(
            descriptor, assembly_path, remaining=evidence.MAX_PROOF_BYTES, deadline=time.monotonic() + 5)
    if hashed != inputs["runtimeAssemblies"][assembly_path]:
        raise evidence.ConformanceError("InputChanged")
    return assembly_path, assembly


def native_metadata_noncooperation_control(run, inputs, *, started_ms, ended_ms):
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    inputs = evidence.admit_entity("RunInputs", inputs)
    started_ms, ended_ms = evidence._number(started_ms), evidence._number(ended_ms)
    if (inputs["profileId"] != "metadata" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id or ended_ms < started_ms):
        raise evidence.ConformanceError("InputChanged")
    packages = [package for package in inputs["packages"]
                if package["packageId"] == "Hoard.Fixtures.Metadata.Sqlite" and package["version"] == "0.1.0"]
    if len(packages) != 1:
        raise evidence.ConformanceError("InputChanged")
    suffix = ("/tests/contracts/Hoard.Conformance.Tests/bin/package-diagnostic/"
              "Release/net10.0/Hoard.Conformance.Tests.dll")
    assembly_path, assembly = _control_assembly(run, inputs, suffix)
    namespace = "qualification-sqlite-native-noncooperation"
    inputs_path = f"proofs/{namespace}-native-inputs.json"
    input_raw = _readonly(run.root / inputs_path, 16 * 1024 * 1024)
    if input_raw != evidence.canonical_bytes(inputs):
        raise evidence.ConformanceError("InputChanged")
    graph_path = f"proofs/{namespace}-native-executions.json"
    graph_raw = _readonly(run.root / graph_path, 64 * 1024)
    graph = evidence.load_json(graph_raw)
    sequence = graph.get("sequence") if isinstance(graph, dict) else None
    if type(sequence) is not int or sequence <= 0:
        raise evidence.ConformanceError("ProofMismatch")
    control_path = f"proofs/recovery-command-{sequence:04}.json"
    native_path = f"proofs/execution-command-{sequence:04}.json"
    producer_path = f"proofs/{namespace}.json"
    control_raw = _readonly(run.root / control_path, 64 * 1024)
    producer_raw = _readonly(run.root / producer_path, 64 * 1024)
    command = evidence.load_json(control_raw)
    admit_sqlite_noncooperation(evidence.load_json(producer_raw), command, evidence.digest(inputs))
    if (command["sequence"] != sequence
            or not started_ms <= command["startedMs"] <= command["endedMs"] <= ended_ms
            or command["endedMs"] - command["startedMs"] > 300000):
        raise evidence.ConformanceError("ProofMismatch")
    arguments = [
        "dotnet", str(assembly), "sqlite-native-noncooperation", str(run.root / producer_path),
        str(run.root / "stores" / namespace), str(run.root / assembly_path.removesuffix(suffix)),
        packages[0]["sha256"], evidence.digest(inputs)]
    native_raw = native_control_record(
        run, sequence, control_raw, arguments=arguments, cwd=assembly.parent,
        input_files={assembly_path: inputs["runtimeAssemblies"][assembly_path], inputs_path: evidence.digest(inputs)},
        diagnostic_code="DeadlineExceeded", output_files={producer_path: hashlib.sha256(producer_raw).hexdigest()})
    expected_graph = {
        "schemaVersion": 1, "qualification": False, "runId": run.run_id,
        "invocationGroupId": inputs["invocationGroupId"], "inputsSha256": evidence.digest(inputs),
        "assemblyPath": assembly_path, "inputsPath": inputs_path, "sequence": sequence,
        "producerSha256": hashlib.sha256(producer_raw).hexdigest(),
        "controllerSha256": hashlib.sha256(control_raw).hexdigest(),
        "executionSha256": hashlib.sha256(native_raw).hexdigest()}
    if (graph_raw != evidence.canonical_bytes(expected_graph)
            or _readonly(run.root / native_path, 64 * 1024) != native_raw):
        raise evidence.ConformanceError("ProofMismatch")
    proofs = {graph_path: graph_raw, inputs_path: input_raw, producer_path: producer_raw,
              control_path: control_raw, native_path: native_raw}
    return MappingProxyType({
        "controls": MappingProxyType({
            "sqlite3-step-stall-and-incomplete-cleanup": tuple(hashlib.sha256(raw).hexdigest()
                                                            for raw in proofs.values())}),
        "sourceProofs": MappingProxyType(proofs)})


def native_metadata_recovery_controls(run, inputs, *, started_ms, ended_ms):
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    inputs = evidence.admit_entity("RunInputs", inputs)
    started_ms, ended_ms = evidence._number(started_ms), evidence._number(ended_ms)
    if (inputs["profileId"] != "metadata" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id or ended_ms < started_ms):
        raise evidence.ConformanceError("InputChanged")
    namespace = "qualification-sqlite-recovery"
    suffix = "/tests/fixtures/metadata/CrashRunner/bin/Release/net10.0/Hoard.Fixtures.Metadata.CrashRunner.dll"
    assembly_path, assembly = _control_assembly(run, inputs, suffix)
    inputs_path = f"proofs/{namespace}-native-inputs.json"
    input_raw = _readonly(run.root / inputs_path, 16 * 1024 * 1024)
    if input_raw != evidence.canonical_bytes(inputs):
        raise evidence.ConformanceError("InputChanged")
    input_files = {assembly_path: inputs["runtimeAssemblies"][assembly_path], inputs_path: evidence.digest(inputs)}
    graph_path = f"proofs/{namespace}-native-executions.json"
    graph_raw = _readonly(run.root / graph_path, 256 * 1024)
    graph = evidence.load_json(graph_raw)
    if (not isinstance(graph, dict) or not isinstance(graph.get("commands"), list)
            or len(graph["commands"]) != 31):
        raise evidence.ConformanceError("EvidenceIncomplete")
    source_path = f"proofs/{namespace}.json"
    source_raw = _readonly(run.root / source_path, 64 * 1024)
    expected_graph = {
        "schemaVersion": 1, "qualification": False, "runId": run.run_id,
        "invocationGroupId": inputs["invocationGroupId"], "inputsSha256": evidence.digest(inputs),
        "assemblyPath": assembly_path, "inputsPath": inputs_path, "commands": graph["commands"],
        "sourceReceiptSha256": hashlib.sha256(source_raw).hexdigest()}
    if graph_raw != evidence.canonical_bytes(expected_graph):
        raise evidence.ConformanceError("ProofMismatch")
    proof_data = {graph_path: graph_raw, source_path: source_raw, inputs_path: input_raw}
    steps = [(kind, barrier, value) for kind, rows in METADATA_RECOVERY_SCENARIOS for barrier, value in rows]
    expected = [(mode + "-" + kind, barrier, value if mode == "run" else None)
                for kind, barrier, value in steps for mode in ("seed", "run", "recover")]
    expected.append(("recovery-walkthrough", "none", None))
    commands, links, previous_sequence, previous_end = {}, {}, 0, started_ms
    for row, (mode, barrier, value) in zip(graph["commands"], expected, strict=True):
        if (not isinstance(row, dict) or set(row) != {
                "mode", "barrierId", "sequence", "controllerSha256", "executionSha256"}
                or row["mode"] != mode or row["barrierId"] != barrier
                or type(row["sequence"]) is not int or row["sequence"] <= previous_sequence):
            raise evidence.ConformanceError("ProofMismatch")
        sequence = row["sequence"]
        control_path = f"proofs/recovery-command-{sequence:04}.json"
        control_raw = _readonly(run.root / control_path, 64 * 1024)
        command = evidence.load_json(control_raw)
        if value is None:
            admit_owned_command(command, sequence, scope="recovery", detail=None, exit_code=0, max_duration=300000)
        else:
            admit_recovery_barrier(command, sequence, value)
        if not previous_end <= command["startedMs"] <= command["endedMs"] <= ended_ms:
            raise evidence.ConformanceError("ProofMismatch")
        directory = run.root / "stores" / namespace / ("walkthrough" if barrier == "none" else barrier)
        arguments = ["dotnet", str(assembly), mode, str(directory / "metadata.db"), str(directory), barrier]
        native_raw = native_control_record(
            run, sequence, control_raw, arguments=arguments, cwd=assembly.parent, input_files=input_files)
        native_path = f"proofs/execution-command-{sequence:04}.json"
        if (_readonly(run.root / native_path, 64 * 1024) != native_raw
                or hashlib.sha256(control_raw).hexdigest() != row["controllerSha256"]
                or hashlib.sha256(native_raw).hexdigest() != row["executionSha256"]):
            raise evidence.ConformanceError("ProofMismatch")
        proof_data[control_path], proof_data[native_path] = control_raw, native_raw
        commands[mode, barrier] = row["controllerSha256"], command
        links[mode, barrier] = row["controllerSha256"], row["executionSha256"]
        previous_sequence, previous_end = sequence, command["endedMs"]
    observations = [{
        "barrierId": barrier, "value": value, "seedSha256": commands["seed-" + kind, barrier][0],
        "controllerSha256": commands["run-" + kind, barrier][0],
        "readbackSha256": commands["recover-" + kind, barrier][0],
        "childStartSha256": commands["run-" + kind, barrier][1]["childStartSha256"]}
        for kind, barrier, value in steps]
    source = {
        "qualification": False, "mode": "metadata-recovery", "code": "None",
        "inputsSha256": evidence.digest(inputs), "barriers": observations,
        "walkthroughSha256": commands["recovery-walkthrough", "none"][0]}
    if source_raw != evidence.canonical_bytes(source):
        raise evidence.ConformanceError("ProofMismatch")
    shared = (hashlib.sha256(graph_raw).hexdigest(), hashlib.sha256(source_raw).hexdigest(), evidence.digest(inputs))
    controls = {
        "parent-kill:" + barrier: (*shared, *(hashed for mode in ("seed", "run", "recover")
                                           for hashed in links[mode + "-" + kind, barrier]))
        for kind, barrier, _ in steps}
    controls["verified-recovery-walkthrough"] = (*shared, *links["recovery-walkthrough", "none"])
    return MappingProxyType({
        "controls": MappingProxyType(controls), "sourceProofs": MappingProxyType(proof_data)})


def native_metadata_ownership_control(run, inputs, *, started_ms, ended_ms):
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    inputs = evidence.admit_entity("RunInputs", inputs)
    started_ms, ended_ms = evidence._number(started_ms), evidence._number(ended_ms)
    if (inputs["profileId"] != "metadata" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id or ended_ms < started_ms):
        raise evidence.ConformanceError("InputChanged")
    assembly_path, assembly = _control_assembly(
        run, inputs, "/tests/fixtures/metadata/CrashRunner/bin/Release/net10.0/Hoard.Fixtures.Metadata.CrashRunner.dll")
    namespace = "qualification-sqlite-ownership"
    inputs_path = f"proofs/{namespace}-native-inputs.json"
    input_raw = _readonly(run.root / inputs_path, 16 * 1024 * 1024)
    if input_raw != evidence.canonical_bytes(inputs):
        raise evidence.ConformanceError("InputChanged")
    graph_path = f"proofs/{namespace}-native-executions.json"
    graph_raw = _readonly(run.root / graph_path, 64 * 1024)
    graph = evidence.load_json(graph_raw)
    if not isinstance(graph, dict) or not isinstance(graph.get("commands"), list) or len(graph["commands"]) != 2:
        raise evidence.ConformanceError("ProofMismatch")
    probe_path = f"proofs/{namespace}-probe.json"
    probe_raw = _readonly(run.root / probe_path, 4096)
    probe = evidence._runtime_json(probe_raw, {
        "schemaVersion": evidence._constant(1), "ownerPid": evidence._integer, "probePid": evidence._integer,
        "probeStartSha256": evidence.sha256, "competingOwnerRejected": evidence._constant(True)}, limit=4096)
    if (not 1 < probe["ownerPid"] <= 2**31 - 1 or not 1 < probe["probePid"] <= 2**31 - 1
            or probe["ownerPid"] == probe["probePid"] or probe["probeStartSha256"] == "0" * 64):
        raise evidence.ConformanceError("ProofMismatch")
    expected = {
        "schemaVersion": 1, "qualification": False, "runId": run.run_id,
        "invocationGroupId": inputs["invocationGroupId"], "inputsSha256": evidence.digest(inputs),
        "assemblyPath": assembly_path, "inputsPath": inputs_path, "commands": graph["commands"],
        "probeSha256": hashlib.sha256(probe_raw).hexdigest()}
    if graph_raw != evidence.canonical_bytes(expected):
        raise evidence.ConformanceError("ProofMismatch")
    proof_data = {graph_path: graph_raw, inputs_path: input_raw, probe_path: probe_raw}
    previous_sequence, previous_end = 0, started_ms
    directory = run.root / "stores" / namespace
    for row, mode in zip(graph["commands"], ("hold-owner-probe", "reopen-owner"), strict=True):
        if (not isinstance(row, dict) or set(row) != {
                "mode", "sequence", "controllerSha256", "executionSha256"}
                or row["mode"] != mode or type(row["sequence"]) is not int
                or row["sequence"] <= previous_sequence):
            raise evidence.ConformanceError("ProofMismatch")
        sequence = row["sequence"]
        control_path = f"proofs/recovery-command-{sequence:04}.json"
        native_path = f"proofs/execution-command-{sequence:04}.json"
        control_raw = _readonly(run.root / control_path, 64 * 1024)
        command = evidence.load_json(control_raw)
        holding = mode == "hold-owner-probe"
        if holding:
            admit_recovery_barrier(command, sequence, 30)
            if command["childPid"] != probe["ownerPid"]:
                raise evidence.ConformanceError("ProofMismatch")
        else:
            admit_owned_command(command, sequence, scope="recovery", detail=None, exit_code=0, max_duration=300000)
        if not previous_end <= command["startedMs"] <= command["endedMs"] <= ended_ms:
            raise evidence.ConformanceError("ProofMismatch")
        arguments = ["dotnet", str(assembly), mode, str(directory / "metadata.db"), str(directory),
                     str(run.root / probe_path) if holding else "owner"]
        native_raw = native_control_record(
            run, sequence, control_raw, arguments=arguments, cwd=assembly.parent,
            input_files={assembly_path: inputs["runtimeAssemblies"][assembly_path], inputs_path: evidence.digest(inputs)},
            output_files={probe_path: hashlib.sha256(probe_raw).hexdigest()} if holding else None)
        if (_readonly(run.root / native_path, 64 * 1024) != native_raw
                or row["controllerSha256"] != hashlib.sha256(control_raw).hexdigest()
                or row["executionSha256"] != hashlib.sha256(native_raw).hexdigest()):
            raise evidence.ConformanceError("ProofMismatch")
        proof_data[control_path], proof_data[native_path] = control_raw, native_raw
        previous_sequence, previous_end = sequence, command["endedMs"]
    return MappingProxyType({
        "controls": MappingProxyType({
            "second-process-owner-and-crash-released-lock": tuple(hashlib.sha256(raw).hexdigest()
                                                                for raw in proof_data.values())}),
        "sourceProofs": MappingProxyType(proof_data)})


def native_metadata_package_consumer_control(run, inputs, *, started_ms, ended_ms):
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    inputs = evidence.admit_entity("RunInputs", inputs)
    started_ms, ended_ms = evidence._number(started_ms), evidence._number(ended_ms)
    if (inputs["profileId"] != "metadata" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id or ended_ms < started_ms):
        raise evidence.ConformanceError("InputChanged")
    assembly_path, assembly = _control_assembly(
        run, inputs, "/tests/fixtures/metadata/Consumer/bin/Release/net10.0/Hoard.Fixtures.Metadata.Consumer.dll")
    namespace = "qualification-metadata-package-consumer"
    inputs_path = f"proofs/{namespace}-native-inputs.json"
    input_raw = _readonly(run.root / inputs_path, 16 * 1024 * 1024)
    if input_raw != evidence.canonical_bytes(inputs):
        raise evidence.ConformanceError("InputChanged")
    graph_path = f"proofs/{namespace}-native-executions.json"
    graph_raw = _readonly(run.root / graph_path, 64 * 1024)
    graph = evidence.load_json(graph_raw)
    if not isinstance(graph, dict) or not isinstance(graph.get("commands"), list) or len(graph["commands"]) != 2:
        raise evidence.ConformanceError("ProofMismatch")
    expected = {
        "schemaVersion": 1, "qualification": False, "runId": run.run_id,
        "invocationGroupId": inputs["invocationGroupId"], "inputsSha256": evidence.digest(inputs),
        "assemblyPath": assembly_path, "inputsPath": inputs_path, "commands": graph["commands"]}
    if graph_raw != evidence.canonical_bytes(expected):
        raise evidence.ConformanceError("ProofMismatch")
    proof_data = {graph_path: graph_raw, inputs_path: input_raw}
    previous_sequence, previous_end = 0, started_ms
    for row, binding in zip(graph["commands"], ("sqlite", "memory"), strict=True):
        if (not isinstance(row, dict) or set(row) != {
                "bindingId", "sequence", "controllerSha256", "executionSha256"}
                or row["bindingId"] != binding or type(row["sequence"]) is not int
                or row["sequence"] <= previous_sequence):
            raise evidence.ConformanceError("ProofMismatch")
        sequence = row["sequence"]
        control_path = f"proofs/recovery-command-{sequence:04}.json"
        native_path = f"proofs/execution-command-{sequence:04}.json"
        control_raw = _readonly(run.root / control_path, 64 * 1024)
        command = evidence.load_json(control_raw)
        admit_owned_command(command, sequence, scope="recovery", detail=None, exit_code=0, max_duration=300000)
        if not previous_end <= command["startedMs"] <= command["endedMs"] <= ended_ms:
            raise evidence.ConformanceError("ProofMismatch")
        arguments = ["dotnet", str(assembly), binding, str(run.root / "stores" / namespace / binding / "metadata.db")]
        native_raw = native_control_record(
            run, sequence, control_raw, arguments=arguments, cwd=assembly.parent,
            input_files={assembly_path: inputs["runtimeAssemblies"][assembly_path], inputs_path: evidence.digest(inputs)})
        if (_readonly(run.root / native_path, 64 * 1024) != native_raw
                or row["controllerSha256"] != hashlib.sha256(control_raw).hexdigest()
                or row["executionSha256"] != hashlib.sha256(native_raw).hexdigest()):
            raise evidence.ConformanceError("ProofMismatch")
        proof_data[control_path], proof_data[native_path] = control_raw, native_raw
        previous_sequence, previous_end = sequence, command["endedMs"]
    return MappingProxyType({
        "controls": MappingProxyType({
            "unchanged-package-consumer": tuple(hashlib.sha256(raw).hexdigest() for raw in proof_data.values())}),
        "sourceProofs": MappingProxyType(proof_data)})


def native_metadata_binary_control(run, inputs, *, started_ms, ended_ms):
    from conformance_baselines import BASELINES

    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    inputs = evidence.admit_entity("RunInputs", inputs)
    started_ms, ended_ms = evidence._number(started_ms), evidence._number(ended_ms)
    if (inputs["profileId"] != "metadata" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id or ended_ms < started_ms):
        raise evidence.ConformanceError("InputChanged")
    suffix = "tests/fixtures/metadata/RetainedMarker/bin/compatibility/net10.0/RetainedMarker.dll"
    assembly_path, assembly = _control_assembly(run, inputs, "/" + suffix)
    prefix = assembly_path.removesuffix("RetainedMarker.dll")
    candidate_prefix = assembly_path.removesuffix(suffix)
    baselines = [row for row in inputs["baselines"] if row["apiScope"] == "metadata-marker"]
    revision = next(row[1] for row in BASELINES if row[0] == "metadata-marker")
    if (len(baselines) != 1 or baselines[0]["revision"] != revision
            or evidence.digest(baselines[0]["dependencySha256"]) != baselines[0]["binarySha256"]):
        raise evidence.ConformanceError("InputChanged")
    baseline = baselines[0]
    old = "retained/bin/Release/net10.0/"
    images = {prefix + path.removeprefix(old): hashed
              for path, hashed in baseline["dependencySha256"].items() if path.startswith(old)}
    platform = ("Hoard.Abstractions.dll", "Hoard.Core.dll", "Hoard.Hosting.dll")
    required = ("RetainedMarker.dll", "RetainedMarker.deps.json", "RetainedMarker.runtimeconfig.json", *platform)
    if not {prefix + name for name in required} <= images.keys() or len(images) > 15:
        raise evidence.ConformanceError("ProofMismatch")
    for name in platform:
        current = candidate_prefix + "tests/fixtures/metadata/Consumer/bin/Release/net10.0/" + name
        hashed = inputs["runtimeAssemblies"].get(current)
        if hashed is None or hashlib.sha256(_readonly(run.root / current, 16 * 1024 * 1024)).hexdigest() != hashed:
            raise evidence.ConformanceError("InputChanged")
        images[prefix + name] = hashed
    if {path: hashed for path, hashed in inputs["runtimeAssemblies"].items() if path.startswith(prefix)} != images:
        raise evidence.ConformanceError("InputChanged")
    for path, hashed in images.items():
        if hashlib.sha256(_readonly(run.root / path, 16 * 1024 * 1024)).hexdigest() != hashed:
            raise evidence.ConformanceError("InputChanged")
    namespace = "qualification-metadata-frozen-binary"
    inputs_path = f"proofs/{namespace}-native-inputs.json"
    input_raw = _readonly(run.root / inputs_path, 16 * 1024 * 1024)
    if input_raw != evidence.canonical_bytes(inputs):
        raise evidence.ConformanceError("InputChanged")
    graph_path = f"proofs/{namespace}-native-executions.json"
    graph_raw = _readonly(run.root / graph_path, 64 * 1024)
    graph = evidence.load_json(graph_raw)
    if not isinstance(graph, dict) or type(graph.get("sequence")) is not int or graph["sequence"] <= 0:
        raise evidence.ConformanceError("ProofMismatch")
    sequence = graph["sequence"]
    control_path = f"proofs/recovery-command-{sequence:04}.json"
    native_path = f"proofs/execution-command-{sequence:04}.json"
    control_raw = _readonly(run.root / control_path, 64 * 1024)
    command = evidence.load_json(control_raw)
    admit_owned_command(command, sequence, scope="recovery", detail=None, exit_code=0, max_duration=300000)
    if not started_ms <= command["startedMs"] <= command["endedMs"] <= ended_ms:
        raise evidence.ConformanceError("ProofMismatch")
    native_raw = native_control_record(
        run, sequence, control_raw, arguments=["dotnet", str(assembly)], cwd=assembly.parent,
        input_files={**images, inputs_path: evidence.digest(inputs)})
    expected = {
        "schemaVersion": 1, "qualification": False, "runId": run.run_id,
        "invocationGroupId": inputs["invocationGroupId"], "inputsSha256": evidence.digest(inputs),
        "assemblyPath": assembly_path, "inputsPath": inputs_path, "sequence": sequence,
        "baselineSha256": evidence.digest(baseline), "controllerSha256": hashlib.sha256(control_raw).hexdigest(),
        "executionSha256": hashlib.sha256(native_raw).hexdigest()}
    if graph_raw != evidence.canonical_bytes(expected) or _readonly(run.root / native_path, 64 * 1024) != native_raw:
        raise evidence.ConformanceError("ProofMismatch")
    proof_data = {graph_path: graph_raw, inputs_path: input_raw, control_path: control_raw, native_path: native_raw}
    return MappingProxyType({
        "controls": MappingProxyType({
            "frozen-pre-F05-binary": tuple(hashlib.sha256(raw).hexdigest() for raw in proof_data.values())}),
        "sourceProofs": MappingProxyType(proof_data)})


def metadata_inventory_source_inputs(run, inputs):
    material = {}
    for path in METADATA_INVENTORY_SOURCE_FILES:
        raw = _readonly(run.root / "snapshot" / path, 1024 * 1024)
        hashed = hashlib.sha256(raw).hexdigest()
        if inputs["sourceManifest"].get(path) != hashed:
            raise evidence.ConformanceError("InputChanged")
        material["snapshot/" + path] = hashed
    return material


def metadata_inventory_arguments(root, mode):
    namespace = "qualification-metadata-inventory"
    return [
        sys.executable, "-I", "-B", "-S", str(root / "snapshot/scripts/conformance_unit_checks.py"),
        "--metadata-inventory", mode, str(root / "stores" / namespace / "metadata_evidence.py"),
        str(root / f"proofs/{namespace}-{mode}.json"), str(root / f"proofs/{namespace}-{mode}.py")]


def native_metadata_inventory_controls(run, inputs, *, started_ms, ended_ms):
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    inputs = evidence.admit_entity("RunInputs", inputs)
    started_ms, ended_ms = evidence._number(started_ms), evidence._number(ended_ms)
    if (inputs["profileId"] != "metadata" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id or ended_ms < started_ms):
        raise evidence.ConformanceError("InputChanged")
    material = metadata_inventory_source_inputs(run, inputs)
    original = _readonly(run.root / "snapshot/scripts/metadata_evidence.py", 1024 * 1024)
    suite_raw = _readonly(run.root / "snapshot/tests/tooling/test_metadata_evidence.py", 1024 * 1024)
    try:
        syntax = ast.parse(suite_raw)
    except SyntaxError:
        raise evidence.ConformanceError("ProofMismatch") from None
    classes = [node for node in syntax.body if isinstance(node, ast.ClassDef)]
    if len(classes) != 1 or classes[0].name != "MetadataEvidenceTests":
        raise evidence.ConformanceError("WitnessMissing")
    identities = sorted("test_metadata_evidence.MetadataEvidenceTests." + node.name
                        for node in classes[0].body
                        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
    failure = ("test_metadata_evidence.MetadataEvidenceTests."
               "test_stale_failed_unpaired_foreign_and_false_memory_durability_reject")
    needle = b'\n        elif entry.get("result") != "Passed":\n'
    if failure not in identities or original.count(needle) != 1:
        raise evidence.ConformanceError("ProofMismatch")
    mutation = original.replace(needle, b"\n        elif False:\n")
    namespace = "qualification-metadata-inventory"
    inputs_path = f"proofs/{namespace}-native-inputs.json"
    input_raw = _readonly(run.root / inputs_path, 16 * 1024 * 1024)
    if input_raw != evidence.canonical_bytes(inputs):
        raise evidence.ConformanceError("InputChanged")
    graph_path = f"proofs/{namespace}-native-executions.json"
    graph_raw = _readonly(run.root / graph_path, 64 * 1024)
    graph = evidence.load_json(graph_raw)
    if (not isinstance(graph, dict) or not isinstance(graph.get("commands"), list)
            or len(graph["commands"]) != 3):
        raise evidence.ConformanceError("ProofMismatch")
    proof_data = {inputs_path: input_raw, graph_path: graph_raw}
    commands, previous_sequence, previous_end = [], 0, started_ms
    for mode, row in zip(("baseline", "mutation", "repair"), graph["commands"], strict=True):
        if (not isinstance(row, dict) or type(row.get("sequence")) is not int
                or row["sequence"] <= previous_sequence):
            raise evidence.ConformanceError("ProofMismatch")
        sequence = row["sequence"]
        control_path = f"proofs/recovery-command-{sequence:04}.json"
        native_path = f"proofs/execution-command-{sequence:04}.json"
        packet_path = f"proofs/{namespace}-{mode}.json"
        snapshot_path = f"proofs/{namespace}-{mode}.py"
        expected_source = mutation if mode == "mutation" else original
        exit_code = 1 if mode == "mutation" else 0
        packet = {
            "schemaVersion": 1, "qualification": False, "mode": mode,
            "baselineSha256": hashlib.sha256(original).hexdigest(),
            "executedSha256": hashlib.sha256(expected_source).hexdigest(),
            "suiteSha256": hashlib.sha256(suite_raw).hexdigest(), "testsSha256": evidence.digest(identities),
            "tests": len(identities), "failures": exit_code, "errors": 0, "skipped": 0,
            "failedTests": [failure] if exit_code else [], "diagnosticBytes": 0, "exitCode": exit_code}
        packet_raw = _readonly(run.root / packet_path, 64 * 1024)
        snapshot_raw = _readonly(run.root / snapshot_path, 1024 * 1024)
        if packet_raw != evidence.canonical_bytes(packet) or snapshot_raw != expected_source:
            raise evidence.ConformanceError("ProofMismatch")
        control_raw = _readonly(run.root / control_path, 64 * 1024)
        command = evidence.load_json(control_raw)
        admit_owned_command(
            command, sequence, scope="recovery", detail=None, exit_code=exit_code, max_duration=300000)
        if not previous_end <= command["startedMs"] <= command["endedMs"] <= ended_ms:
            raise evidence.ConformanceError("ProofMismatch")
        native_raw = native_control_record(
            run, sequence, control_raw, arguments=metadata_inventory_arguments(run.root, mode),
            cwd=run.root / "snapshot", input_files={**material, inputs_path: evidence.digest(inputs)},
            output_files={packet_path: hashlib.sha256(packet_raw).hexdigest(),
                          snapshot_path: hashlib.sha256(snapshot_raw).hexdigest()})
        if _readonly(run.root / native_path, 64 * 1024) != native_raw:
            raise evidence.ConformanceError("ProofMismatch")
        commands.append({
            "mode": mode, "sequence": sequence, "controllerSha256": hashlib.sha256(control_raw).hexdigest(),
            "executionSha256": hashlib.sha256(native_raw).hexdigest()})
        proof_data.update({control_path: control_raw, native_path: native_raw,
                           packet_path: packet_raw, snapshot_path: snapshot_raw})
        previous_sequence, previous_end = sequence, command["endedMs"]
    expected_graph = {
        "schemaVersion": 1, "qualification": False, "runId": run.run_id,
        "invocationGroupId": inputs["invocationGroupId"], "inputsSha256": evidence.digest(inputs),
        "scriptPath": "snapshot/scripts/conformance_unit_checks.py", "inputsPath": inputs_path, "commands": commands}
    if (graph_raw != evidence.canonical_bytes(expected_graph)
            or read_bounded(run.root / "stores" / namespace / "metadata_evidence.py", 1024 * 1024) != original):
        raise evidence.ConformanceError("ProofMismatch")
    hashes = tuple(hashlib.sha256(raw).hexdigest() for raw in proof_data.values())
    return MappingProxyType({
        "controls": MappingProxyType({
            "MetadataEvidenceTests:positive-complete-and-negative-inventories": hashes,
            "test_stale_failed_unpaired_foreign_and_false_memory_durability_reject": hashes}),
        "sourceProofs": MappingProxyType(proof_data)})


class NativeCategorySources:
    def __init__(self, run, *, inspection_inputs, inspection_configurations):
        if type(run) is not OwnedRun:
            raise evidence.ConformanceError("OwnershipInvalid")
        expected = set(ORIGINAL_INSPECTION_WITNESSES) - set(ORIGINAL_INSPECTION_LITERAL_WITNESSES)
        if (not isinstance(inspection_inputs, Mapping) or set(inspection_inputs) != expected
                or not isinstance(inspection_configurations, Mapping)
                or set(inspection_configurations) != {"metadata", "artifacts"}):
            raise evidence.ConformanceError("WitnessMissing")
        evidence.configuration_fingerprint({}, inspection_inputs=inspection_inputs)
        self._run = run
        self._selected = MappingProxyType({
            identity: MappingProxyType(dict(files)) for identity, files in inspection_inputs.items()})
        configurations = {}
        for family, value in inspection_configurations.items():
            if not isinstance(value, (str, Path)):
                raise evidence.ConformanceError("OwnershipInvalid")
            path = Path(value)
            no_symlinks(path)
            if not path.is_absolute() or not path.is_relative_to(run.root):
                raise evidence.ConformanceError("OwnershipInvalid")
            configurations[family] = path
        self._configurations = MappingProxyType(configurations)

    def ingest_attempt(self, *, category_scope, **transport):
        if category_scope == (transport["inputs"]["profileId"], "hook-admission"):
            expected_origins = category_consumer_origin_inputs(self._run, transport["inputs"])
            if transport.get("origin_inputs") is not None and transport["origin_inputs"] != expected_origins:
                raise evidence.ConformanceError("ProofMismatch")
            transport["origin_inputs"] = expected_origins
        inspected = evidence.inspect_runtime_attempt(**transport)
        graph = self._corroborate(inspected["inputs"], evidence.load_json(transport["manifest_data"]),
                                  inspected["observation"], category_scope=category_scope,
                                  manifest_data=transport["manifest_data"], owner_data=transport["owner_data"],
                                  started_ms=transport["started_ms"], ended_ms=transport["ended_ms"])
        return MappingProxyType({**inspected["observation"], **graph})

    def metadata_controls(self, inputs, *, started_ms, ended_ms):
        collected = {"controls": {}, "sourceProofs": {}}
        for authority in (native_metadata_recovery_controls, native_metadata_noncooperation_control,
                          native_metadata_ownership_control, native_metadata_package_consumer_control,
                          native_metadata_binary_control, native_metadata_inventory_controls,
                          native_metadata_common_consumer_control, native_hook_admission_control):
            observed = authority(self._run, inputs, started_ms=started_ms, ended_ms=ended_ms)
            for key, target in collected.items():
                overlap = set(target) & set(observed[key])
                if overlap and (key != "sourceProofs" or any(target[path] != observed[key][path] for path in overlap)):
                    raise evidence.ConformanceError("ProofMismatch")
                target.update(observed[key])
        return MappingProxyType({
            key: MappingProxyType(value) for key, value in collected.items()})

    def artifact_controls(self, inputs, *, started_ms, ended_ms):
        if inputs["profileId"] != "artifacts":
            raise evidence.ConformanceError("WitnessMissing")
        return native_hook_admission_control(self._run, inputs, started_ms=started_ms, ended_ms=ended_ms)

    def _corroborate(self, inputs, manifest, observed, *, category_scope, manifest_data, owner_data,
                     started_ms, ended_ms):
        run = self._run
        if not isinstance(category_scope, (tuple, list)) or len(category_scope) != 2:
            raise evidence.ConformanceError("WitnessMissing")
        profile, scope_id = category_scope
        partitions = category_execution_partitions(profile, mode=inputs["mode"])
        inventory = profile == "metadata" and scope_id == "inventory-controller"
        metadata = profile == "metadata" and scope_id in ("recovery-controller", "inventory-controller")
        artifact = profile == "artifacts" and scope_id == "controller"
        integration = (profile, scope_id) == ("artifacts", "original-integration")
        mutation = scope_id == "mutation-repair"
        hooks = scope_id == "hook-admission"
        if (inputs["mode"] != "qualification" or inputs["profileId"] != profile
                or inputs["runId"] != run.run_id or not isinstance(scope_id, str)
                or not (scope_id.startswith("inspection-") or metadata or artifact or integration or mutation or hooks)
                or scope_id not in partitions):
            raise evidence.ConformanceError("WitnessMissing")
        if hooks:
            admitted = native_hook_admission_control(run, inputs, started_ms=started_ms, ended_ms=ended_ms)
            if (admitted["observation"] != observed
                    or admitted["sourceProofs"].get(f'runtime-input-{manifest["attemptId"]}.json') != manifest_data
                    or admitted["sourceProofs"].get("runtime-owner.json") != owner_data):
                raise evidence.ConformanceError("ProofMismatch")
            parent = hashlib.sha256(admitted["sourceProofs"][
                f"proofs/{HOOK_ADMISSION_NAMESPACES[profile]}-native-executions.json"]).hexdigest()
            return MappingProxyType({
                "sourceParents": MappingProxyType({row["executionId"]: parent for row in observed["witnesses"]}),
                "sourceProofs": admitted["sourceProofs"]})
        tests = {identity: (binding, category_runtime_cases(profile, binding, mode=inputs["mode"])[identity])
                 for binding, identity in partitions[scope_id]}
        if (len(manifest["expected"]) != len(tests)
                or {entry["testIdentity"] for entry in manifest["expected"]} != set(tests)
                or any((entry["bindingId"], entry["caseId"]) != tests[entry["testIdentity"]]
                       or entry["fullyQualifiedName"] != entry["testIdentity"].split("(")[0]
                       for entry in manifest["expected"])
                or any(observed[name][row["executionId"]]
                       for name in (("sessionOrigins",) if integration else ("sessionOrigins", "originalObservations"))
                       for row in observed["witnesses"])):
            raise evidence.ConformanceError("ProofMismatch")
        mapping = evidence.verify_synthetic_source_mapping(
            run.root, "stores/candidate.NuGet.Config", "feed/candidate")
        if inputs["configurationSha256"] != evidence.configuration_fingerprint(
                mapping, inspection_inputs=self._selected):
            raise evidence.ConformanceError("InputChanged")
        attempt = evidence._uuid(manifest["attemptId"])
        parent_raw = _readonly(run.root / f"proofs/category-source-{attempt}.json", 512 * 1024)
        parent = evidence.load_json(parent_raw)
        sequence = parent.get("commandSequence") if isinstance(parent, dict) else None
        if type(sequence) is not int or not 0 < sequence <= run.command_sequence:
            raise evidence.ConformanceError("OwnershipInvalid")
        record_raw = run.read_execution_record(sequence)
        record = evidence.load_json(record_raw)
        material = {}
        if artifact:
            material = native_artifact_controller_source(
                run, inputs, manifest, observed, sequence=sequence, started_ms=started_ms, ended_ms=ended_ms)
            source_raw = material["sourceReceipt"]
            source = evidence.load_json(source_raw)
            source_path = f"proofs/original-artifact-external-{attempt}.json"
            observations, packets = source["observations"], material["sourcePackets"]
        elif mutation:
            observations, packets = category_mutation_observations(
                run, inputs, manifest, observed, sequence=sequence, started_ms=started_ms, ended_ms=ended_ms)
        elif integration:
            observations = authority_integration_observations(run, inputs, manifest, observed)
            packets = {}
        elif metadata:
            metadata_context = (metadata_inventory_context if inventory else metadata_recovery_context)(
                run, inputs, manifest, ended_ms=time.monotonic() * 1000)
            selected = {identity: metadata_context["files"] for identity in tests}
            observations, packets = (metadata_inventory_observations if inventory else metadata_recovery_observations)(
                run.root, inputs, manifest, observed, metadata_context)
        else:
            selected = ({identity: self._selected[identity] for identity in tests}
                        if scope_id.startswith("inspection-prepared-") else {identity: {} for identity in tests})
            observations, packets = inspection_observations(
                run.root, inputs, manifest, observed, selected, {identity: pair[0] for identity, pair in tests.items()})
        if not artifact:
            source = {
                "schemaVersion": 1, "qualification": False, "mode": f"category-{profile}-{scope_id}",
                "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
                "attemptId": attempt, "inputsSha256": evidence.digest(inputs), "observations": observations}
            source_path = f'proofs/{source["mode"]}-{attempt}.json'
            source_raw = _readonly(run.root / source_path, 512 * 1024)
            if source_raw != evidence.canonical_bytes(source):
                raise evidence.ConformanceError("ProofMismatch")
        execution_raw = _readonly(run.root / f"proofs/category-command-{attempt}-execution.json", 64 * 1024)
        expected_parent = {
            "schemaVersion": 1, "qualification": False, "nativeContainment": True,
            "profileId": profile, "scopeId": scope_id, "runId": inputs["runId"],
            "invocationGroupId": inputs["invocationGroupId"], "attemptId": attempt,
            "inputsSha256": evidence.digest(inputs), "manifestSha256": evidence.digest(manifest),
            "commandSequence": sequence, "executionParentSha256": hashlib.sha256(execution_raw).hexdigest(),
            "sourceReceiptSha256": hashlib.sha256(source_raw).hexdigest(),
            "observations": sorted(
                ({**row, "bindingId": tests[row["testIdentity"]][0], "caseId": tests[row["testIdentity"]][1]}
                 for row in observations), key=lambda row: row["testIdentity"])}
        if parent_raw != evidence.canonical_bytes(expected_parent):
            raise evidence.ConformanceError("ProofMismatch")
        owner = {
            "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": inputs["invocationGroupId"],
            "rootId": run.root_id, "rootPathSha256": hashlib.sha256(str(run.root).encode()).hexdigest()}
        provider_packages = category_runtime_packages(inputs, {binding for binding, _ in tests.values()})
        expected_packages = {package["packageId"]: package["sha256"] for package in provider_packages.values()}
        if (owner_data != evidence.canonical_bytes(owner)
                or _readonly(run.root / "runtime-owner.json", 64 * 1024) != owner_data
                or _readonly(run.root / f"runtime-input-{attempt}.json", 1024 * 1024) != manifest_data
                or _readonly(run.root / manifest["runInputsPath"], 16 * 1024 * 1024) != evidence.canonical_bytes(inputs)
                or len(manifest["assemblies"]) != (6 if integration or mutation else 1)
                or {entry["assemblyId"] for entry in manifest["expected"]} != {manifest["assemblies"][0]["id"]}
                or len(manifest["packages"]) != len(expected_packages)
                or {package["id"]: package["sha256"] for package in manifest["packages"]} != expected_packages
                or any(entry["packageId"] != provider_packages[entry["bindingId"]]["packageId"]
                       for entry in manifest["expected"])):
            raise evidence.ConformanceError("ProofMismatch")
        assembly = run.root / manifest["assemblies"][0]["path"]
        if assembly.name != ("Hoard.Fixtures.Conformance.Consumer.dll" if integration or mutation else
                             "Hoard.Conformance.Tests.dll" if metadata else
                             "Hoard.Artifacts.Tests.dll" if artifact else "Hoard.Architecture.Tests.dll"):
            raise evidence.ConformanceError("ProofMismatch")
        metadata_prefix = "metadata-inventory" if inventory else "metadata-recovery"
        context_prefix = metadata_prefix if metadata else "artifact-source" if artifact else "inspection"
        context = run.root / "stores" / f"{context_prefix}-context-{attempt}.json"
        expected_context = {} if mutation else {
            "schemaVersion": 1, "runId": manifest["runId"],
            "cases": {entry["testIdentity"]: {"caseId": entry["caseId"], "bindingId": entry["bindingId"]}
                      for entry in manifest["expected"]}} if integration else artifact_source_context(
            run, inputs, manifest, namespace="qualification-artifact-transfers") if artifact else (
            metadata_inventory_context if inventory else metadata_recovery_context)(
            run, inputs, manifest, ended_ms=record["startedMs"]) if metadata else {
            "schemaVersion": 1, "runId": run.run_id, "attemptId": attempt,
            "inputsSha256": evidence.digest(inputs),
            "outputDirectory": str(run.root / "stores" / ("original-inspection-" + attempt)), "cases": selected}
        if not (integration or mutation) and _readonly(context, 1024 * 1024) != evidence.canonical_bytes(expected_context):
            raise evidence.ConformanceError("ProofMismatch")
        variables = {}
        configuration_hashes = {}
        if artifact:
            crash_path, crash_assembly = _control_assembly(
                run, inputs, "/tests/fixtures/artifacts/CrashRunner/bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll")
            variables.update({
                "HOARD_ARTIFACT_CRASH_RUNNER": str(crash_assembly),
                "HOARD_ARTIFACT_CRASH_PROOFS": str(run.root / "stores" / ("original-artifact-" + attempt)),
                "HOARD_ARTIFACT_TRANSFER_PROOFS": str(run.root / "proofs/qualification-artifact-transfers"),
                "HOARD_ARTIFACT_RUN_ID": run.run_id})
        if scope_id.startswith("inspection-prepared-"):
            for family, variable in (("metadata", "HOARD_METADATA_BOUNDARIES"), ("artifacts", "HOARD_ARTIFACT_BOUNDARIES")):
                path = self._configurations[family]
                hashed = hashlib.sha256(read_bounded(path, 1024 * 1024)).hexdigest()
                if any(files.get(str(path)) != hashed for identity, files in self._selected.items()
                       if (".MetadataBoundaryTests." in identity) == (family == "metadata")):
                    raise evidence.ConformanceError("InputChanged")
                variables[variable] = str(path)
                configuration_hashes[path.relative_to(run.root).as_posix()] = hashed
        if mutation:
            variables = category_consumer_environment(inputs)
        elif integration:
            variables["HOARD_ORIGINAL_CONTEXT"] = base64.b64encode(evidence.canonical_bytes(expected_context)).decode()
        else:
            variables["HOARD_ARTIFACT_SOURCE_CONTEXT" if artifact else (
                      "HOARD_METADATA_INVENTORY_CONTEXT" if inventory else "HOARD_METADATA_RECOVERY_CONTEXT")
                      if metadata else "HOARD_INSPECTION_CONTEXT"] = str(context)
        environment = "<EnvironmentVariables>" + "".join(
            f"<{key}>{escape(value)}</{key}>" for key, value in variables.items()) + "</EnvironmentVariables>"
        settings = run.root / "stores" / f"settings-{attempt}.runsettings"
        settings_raw = _readonly(settings, 256 * 1024)
        if settings_raw != runtime_settings(
                run.root, assembly, attempt, evidence.digest(manifest), hashlib.sha256(owner_data).hexdigest(), environment):
            raise evidence.ConformanceError("ProofMismatch")
        expected_execution = {
            "schemaVersion": 1, "qualification": False, "nativeContainment": True,
            "runId": run.run_id, "rootId": run.root_id,
            "invocationGroupId": inputs["invocationGroupId"], "attemptId": attempt, "purpose": "execution",
            "commandSequence": sequence, "inputsSha256": evidence.digest(inputs),
            "executionRecordSha256": hashlib.sha256(record_raw).hexdigest(),
            "manifestSha256": evidence.digest(manifest), "settingsSha256": hashlib.sha256(settings_raw).hexdigest()}
        if execution_raw != evidence.canonical_bytes(expected_execution):
            raise evidence.ConformanceError("ProofMismatch")
        fields = {"schemaVersion", "sequence", "childPid", "childStartSha256", "startedMs", "endedMs",
                  "exitCode", "diagnosticCode", "groupState", "scope", "runId", "rootId",
                  "argvSha256", "cwdSha256", "inputFiles"}
        if artifact:
            fields.add("outputFiles")
        input_files = {
            f"runtime-input-{attempt}.json": hashlib.sha256(manifest_data).hexdigest(),
            "runtime-owner.json": hashlib.sha256(owner_data).hexdigest(),
            manifest["runInputsPath"]: evidence.digest(inputs),
            settings.relative_to(run.root).as_posix(): hashlib.sha256(settings_raw).hexdigest(),
            **{entry["path"]: inputs["runtimeAssemblies"][entry["path"]] for entry in manifest["assemblies"]},
            **configuration_hashes}
        if not (integration or mutation):
            input_files[context.relative_to(run.root).as_posix()] = evidence.digest(expected_context)
        if metadata:
            for path in (expected_context["graphPath"],
                         expected_context["graphPath"].removesuffix("-native-executions.json") + "-native-inputs.json"):
                input_files[path] = hashlib.sha256(_readonly(run.root / path, 16 * 1024 * 1024)).hexdigest()
        if artifact:
            input_files[crash_path] = inputs["runtimeAssemblies"][crash_path]
            for path in ("proofs/qualification-artifact-transfers.json", *(
                    f"proofs/qualification-artifact-transfers/transfer-{provider}-{size}/proof.json"
                    for provider in ("local", "object") for size in (268435456, 4294967296))):
                input_files[path] = hashlib.sha256(material["sourceProofs"][path]).hexdigest()
            seal_path = f"proofs/artifact-source-seal-{attempt}.json"
            if record.get("outputFiles") != {
                    seal_path: hashlib.sha256(material["sourceProofs"][seal_path]).hexdigest()}:
                raise evidence.ConformanceError("ProofMismatch")
        if (not isinstance(record, dict) or set(record) != fields
                or type(record["schemaVersion"]) is not int or record["schemaVersion"] != 1
                or type(record["sequence"]) is not int or record["sequence"] != sequence
                or record["runId"] != run.run_id or record["rootId"] != run.root_id
                or type(record["childPid"]) is not int or not 1 < record["childPid"] <= 2**31 - 1
                or evidence.sha256(record["childStartSha256"]) == "0" * 64
                or type(record["exitCode"]) is not int or record["exitCode"] != 0
                or record["diagnosticCode"] != "None" or record["groupState"] != "Exited"
                or record["scope"] != "ordinary" or run.live_children()
                or record["inputFiles"] != input_files
                or record["argvSha256"] != evidence.digest(runtime_arguments(
                    assembly, settings, [entry["testIdentity"] for entry in manifest["expected"]]))
                or record["cwdSha256"] != hashlib.sha256(str(assembly.parent.absolute()).encode()).hexdigest()):
            raise evidence.ConformanceError("OwnershipInvalid")
        times = (record["startedMs"], record["endedMs"])
        if (any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 2**63 - 1
                for value in times) or times[1] < times[0]
                or (integration or mutation) and not started_ms <= times[0] <= times[1] <= ended_ms
                or any(not times[0] <= row["startedMs"] <= row["endedMs"] <= times[1]
                       for row in observed["witnesses"])):
            raise evidence.ConformanceError("ProofMismatch")
        for path, raw in packets.items():
            destination = run.root / path
            try:
                with destination.open("xb") as output:
                    output.write(raw)
                destination.chmod(0o400)
            except FileExistsError:
                if _readonly(destination, 512 * 1024) != raw:
                    raise evidence.ConformanceError("ProofMismatch") from None
        return MappingProxyType({
            "sourceParents": MappingProxyType({
                row["executionId"]: hashlib.sha256(parent_raw).hexdigest() for row in observations}),
            "sourceProofs": MappingProxyType({
                f"proofs/category-source-{attempt}.json": parent_raw,
                source_path: source_raw,
                f"proofs/category-command-{attempt}-execution.json": execution_raw,
                f"proofs/execution-command-{sequence:04}.json": record_raw,
                **material.get("sourceProofs", {}), **packets}),
        })
