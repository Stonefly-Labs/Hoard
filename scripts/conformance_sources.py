"""Independent source corroboration; files or session claims alone cannot qualify."""

from collections.abc import Mapping
import hashlib
import math
from pathlib import Path
import re
import time
from types import MappingProxyType
from xml.sax.saxutils import escape

import conformance_evidence as evidence
from conformance_case_catalog import (
    ORIGINAL_INSPECTION_LITERAL_WITNESSES, ORIGINAL_INSPECTION_WITNESSES,
    category_execution_partitions, category_runtime_cases,
)
from conformance_execution import OwnedRun, no_symlinks


METADATA_RECOVERY_SCENARIOS = (
    ("mutation", (("M0", 0), ("M1", 1), ("M2", 2))),
    ("upgrade", tuple((f"U{index}", 10 + index) for index in range(5))),
    ("restore", (("R0", 20), ("R1", 21))),
)


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


def inspection_observations(root, inputs, manifest, observed, selected, bindings):
    witnesses = source_witnesses(inputs, manifest, observed, selected)
    if any(row["bindingId"] != bindings[identity] for identity, row in witnesses.items()):
        raise evidence.ConformanceError("ProofMismatch")
    capture = root / "stores" / ("original-inspection-" + manifest["attemptId"])
    no_symlinks(capture)
    if not capture.is_dir():
        raise evidence.ConformanceError("EvidenceIncomplete")
    expected = {"inspection-" + hashlib.sha256(identity.encode()).hexdigest() + ".json": identity
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
        packets[f'proofs/source-inspection-{manifest["attemptId"]}-{hashlib.sha256(identity.encode()).hexdigest()}.json'] = raw
    return observations, MappingProxyType(packets)


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


def native_control_record(run, sequence, control_raw, *, arguments, cwd, input_files):
    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    control = evidence.load_json(control_raw)
    fields = {"schemaVersion", "sequence", "childPid", "childStartSha256", "startedMs", "endedMs",
              "exitCode", "diagnosticCode", "groupState", "scope"}
    if (not isinstance(control, dict) or not fields <= control.keys()
            or control["scope"] not in ("recovery", "transfer")
            or set(control) - fields not in (
                (set(), {"barrier"}) if control["scope"] == "recovery" else ({"transfer"},))
            or control["sequence"] != sequence or control["diagnosticCode"] != "None"
            or control["groupState"] != "Exited" or run.live_children()):
        raise evidence.ConformanceError("ProofMismatch")
    raw = run.read_execution_record(sequence)
    expected = {
        **{key: control[key] for key in fields}, "runId": run.run_id, "rootId": run.root_id,
        "argvSha256": evidence.digest(arguments),
        "cwdSha256": hashlib.sha256(str(Path(cwd).absolute()).encode()).hexdigest(),
        "controlRecordSha256": hashlib.sha256(control_raw).hexdigest(),
        **({"inputFiles": input_files} if input_files else {}),
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
        inspected = evidence.inspect_runtime_attempt(**transport)
        graph = self._corroborate(inspected["inputs"], evidence.load_json(transport["manifest_data"]),
                                  inspected["observation"], category_scope=category_scope,
                                  manifest_data=transport["manifest_data"], owner_data=transport["owner_data"])
        return MappingProxyType({**inspected["observation"], **graph})

    def metadata_controls(self, inputs, *, started_ms, ended_ms):
        return native_metadata_recovery_controls(self._run, inputs, started_ms=started_ms, ended_ms=ended_ms)

    def _corroborate(self, inputs, manifest, observed, *, category_scope, manifest_data, owner_data):
        run = self._run
        if not isinstance(category_scope, (tuple, list)) or len(category_scope) != 2:
            raise evidence.ConformanceError("WitnessMissing")
        profile, scope_id = category_scope
        partitions = category_execution_partitions(profile)
        if (inputs["mode"] != "qualification" or inputs["profileId"] != profile
                or inputs["runId"] != run.run_id or not isinstance(scope_id, str)
                or not scope_id.startswith("inspection-") or scope_id not in partitions):
            raise evidence.ConformanceError("WitnessMissing")
        tests = {identity: (binding, category_runtime_cases(profile, binding)[identity])
                 for binding, identity in partitions[scope_id]}
        if (len(manifest["expected"]) != len(tests)
                or {entry["testIdentity"] for entry in manifest["expected"]} != set(tests)
                or any((entry["bindingId"], entry["caseId"]) != tests[entry["testIdentity"]]
                       or entry["fullyQualifiedName"] != entry["testIdentity"].split("(")[0]
                       for entry in manifest["expected"])
                or any(observed[name][row["executionId"]] for name in ("sessionOrigins", "originalObservations")
                       for row in observed["witnesses"])):
            raise evidence.ConformanceError("ProofMismatch")
        mapping = evidence.verify_synthetic_source_mapping(
            run.root, "stores/candidate.NuGet.Config", "feed/candidate")
        if inputs["configurationSha256"] != evidence.configuration_fingerprint(
                mapping, inspection_inputs=self._selected):
            raise evidence.ConformanceError("InputChanged")
        attempt = evidence._uuid(manifest["attemptId"])
        selected = ({identity: self._selected[identity] for identity in tests}
                    if scope_id.startswith("inspection-prepared-") else {identity: {} for identity in tests})
        observations, packets = inspection_observations(
            run.root, inputs, manifest, observed, selected, {identity: pair[0] for identity, pair in tests.items()})
        source = {
            "schemaVersion": 1, "qualification": False, "mode": f"category-{profile}-{scope_id}",
            "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
            "attemptId": attempt, "inputsSha256": evidence.digest(inputs), "observations": observations}
        source_raw = _readonly(run.root / f'proofs/{source["mode"]}-{attempt}.json', 512 * 1024)
        if source_raw != evidence.canonical_bytes(source):
            raise evidence.ConformanceError("ProofMismatch")
        parent_raw = _readonly(run.root / f"proofs/category-source-{attempt}.json", 512 * 1024)
        parent = evidence.load_json(parent_raw)
        sequence = parent.get("commandSequence") if isinstance(parent, dict) else None
        if type(sequence) is not int or not 0 < sequence <= run.command_sequence:
            raise evidence.ConformanceError("OwnershipInvalid")
        record_raw = run.read_execution_record(sequence)
        record = evidence.load_json(record_raw)
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
        if (owner_data != evidence.canonical_bytes(owner)
                or _readonly(run.root / "runtime-owner.json", 64 * 1024) != owner_data
                or _readonly(run.root / f"runtime-input-{attempt}.json", 1024 * 1024) != manifest_data
                or _readonly(run.root / manifest["runInputsPath"], 16 * 1024 * 1024) != evidence.canonical_bytes(inputs)
                or len(manifest["assemblies"]) != 1
                or {entry["assemblyId"] for entry in manifest["expected"]} != {manifest["assemblies"][0]["id"]}
                or len(manifest["packages"]) != 1 or manifest["packages"][0]["id"] != "Hoard.Testing.Conformance"
                or {entry["packageId"] for entry in manifest["expected"]} != {"Hoard.Testing.Conformance"}):
            raise evidence.ConformanceError("ProofMismatch")
        assembly = run.root / manifest["assemblies"][0]["path"]
        if assembly.name != "Hoard.Architecture.Tests.dll":
            raise evidence.ConformanceError("ProofMismatch")
        context = run.root / "stores" / f"inspection-context-{attempt}.json"
        expected_context = {
            "schemaVersion": 1, "runId": run.run_id, "attemptId": attempt,
            "inputsSha256": evidence.digest(inputs),
            "outputDirectory": str(run.root / "stores" / ("original-inspection-" + attempt)), "cases": selected}
        if _readonly(context, 1024 * 1024) != evidence.canonical_bytes(expected_context):
            raise evidence.ConformanceError("ProofMismatch")
        variables = {}
        configuration_hashes = {}
        if scope_id.startswith("inspection-prepared-"):
            for family, variable in (("metadata", "HOARD_METADATA_BOUNDARIES"), ("artifacts", "HOARD_ARTIFACT_BOUNDARIES")):
                path = self._configurations[family]
                hashed = hashlib.sha256(read_bounded(path, 1024 * 1024)).hexdigest()
                if any(files.get(str(path)) != hashed for identity, files in self._selected.items()
                       if (".MetadataBoundaryTests." in identity) == (family == "metadata")):
                    raise evidence.ConformanceError("InputChanged")
                variables[variable] = str(path)
                configuration_hashes[path.relative_to(run.root).as_posix()] = hashed
        variables["HOARD_INSPECTION_CONTEXT"] = str(context)
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
        input_files = {
            f"runtime-input-{attempt}.json": hashlib.sha256(manifest_data).hexdigest(),
            "runtime-owner.json": hashlib.sha256(owner_data).hexdigest(),
            manifest["runInputsPath"]: evidence.digest(inputs),
            settings.relative_to(run.root).as_posix(): hashlib.sha256(settings_raw).hexdigest(),
            manifest["assemblies"][0]["path"]: inputs["runtimeAssemblies"][manifest["assemblies"][0]["path"]],
            context.relative_to(run.root).as_posix(): evidence.digest(expected_context), **configuration_hashes}
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
                f'proofs/{source["mode"]}-{attempt}.json': source_raw,
                f"proofs/category-command-{attempt}-execution.json": execution_raw,
                f"proofs/execution-command-{sequence:04}.json": record_raw, **packets}),
        })
