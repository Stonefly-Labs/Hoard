"""Owned original controller preparation and exact inherited runtime inventories."""

from collections import Counter
from contextlib import contextmanager, redirect_stdout
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import uuid

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance_evidence import ConformanceError, DIAGNOSTIC_CODES, digest, load_json

INVENTORY_PATH = "tests/fixtures/conformance/baselines/composition-inventory.json"
BASELINE = "9389016c0285c79f6f515f59805a5a41c69b0767"
INVENTORY_SHA256 = "9b45196787d57b0437c14e73345b1a0ba4b1544a41d95f7fca3ea32b7635de50"
# Keep the frozen assertions; admit only the exact worker-entry setup correction.
EXECUTION_SOURCE_VARIANTS = {
    "tests/integration/Hoard.Composition.Tests/DiscoveryBoundsTests.cs":
        "ef516b44d066f1f5a9667a9eb65aea8960d84ea8c889bd66be1535ffbbe5d4a4",
}
FOUNDATION_INVENTORY_PATH = "tests/fixtures/conformance/baselines/foundation-inventory.json"
FOUNDATION_INVENTORY_SHA256 = "c8ba6c4d6ebe82c043ce22bb28dd65a6c1b0258d7490be74dbbc36499753bb5e"
GROUPS = frozenset(("lifecycle", "configuration", "discovery"))
ASSEMBLIES = frozenset(("Hoard.Composition.Tests", "Hoard.Architecture.Tests"))
FOUNDATION_ASSEMBLIES = ASSEMBLIES | {"Hoard.Foundation.Tests"}
TOOLING_SUITE_SECONDS = 30 * 60
CONTROLLER_ERROR_SOURCES = (
    "conformance_inherited.py", "conformance_legacy.py", "conformance_lock_preparation.py",
    "conformance_evidence.py", "conformance_sources.py", "foundation_evidence.py",
    "lifecycle_evidence.py", "configuration_evidence.py", "discovery_evidence.py", "conformance_execution.py",
)


def _controller_incomplete(phase, code, lines):
    from conformance_execution import project_event

    events = [project_event(line) for line in lines]
    locations = []
    for event in events:
        source, line = divmod(event["value"], 100000)
        if (event["event"] == "control" and event["code"] != "None"
                and 1 <= source <= len(CONTROLLER_ERROR_SOURCES) and line):
            locations.append({"source": CONTROLLER_ERROR_SOURCES[source - 1], "line": line})
    print(json.dumps({"qualification": False, "phase": "inherited-preparation-incomplete",
                      "scope": phase, "code": code, "locations": locations,
                      "events": [dict(event) for event in events if event["event"] == "control"]}), flush=True)


def controller_phase(run, repository, source, phase, *, baseline_seal=None, sdk_package=None, logger_path=None,
                     reference=None):
    import conformance_evidence as evidence
    import conformance_legacy as legacy
    from conformance_sdk_checks import write_new
    from conformance_sources import read_bounded

    if phase not in ("historical", "controllers", "mutations", "reference", "architecture"):
        raise ConformanceError("EvidenceSchemaInvalid")
    if (phase == "reference") != (reference is not None):
        raise ConformanceError("EvidenceSchemaInvalid")
    if phase == "architecture" and any(value is not None for value in (baseline_seal, sdk_package, logger_path)):
        raise ConformanceError("EvidenceSchemaInvalid")
    if phase == "historical" and (run.command_sequence != 0 or (run.root / "feed/candidate").exists()):
        raise ConformanceError("InputChanged")
    request_path = run.root / f"stores/inherited-{phase}-request.json"
    output_path = run.root / f"proofs/inherited-{phase}-result.json"
    script = source / "scripts/conformance_inherited.py"
    request = {
        "schemaVersion": 1, "phase": phase, "owner": str(run.root), "repository": str(repository),
        "runId": run.run_id, "rootId": run.root_id, "source": source.relative_to(run.root).as_posix(),
        "baselineSeal": baseline_seal,
        "sdkPackage": None if sdk_package is None else sdk_package.relative_to(run.root).as_posix(),
        "loggerPath": None if logger_path is None else logger_path.relative_to(run.root).as_posix(),
    }
    if reference is not None:
        request["reference"] = reference
    write_new(request_path, evidence.canonical_bytes(request))
    paths = [request_path, script]
    if baseline_seal is not None:
        paths.append(run.root / baseline_seal["path"])
    paths.extend(path for path in (sdk_package, logger_path) if path is not None)
    if reference is not None:
        paths.extend(run.root / evidence.relative_path(reference[key]) for key in ("manifestPath", "inputMapPath"))
    if phase == "mutations":
        paths.append(run.root / "proofs/composition-inputs.json")
    for path in paths:
        path.chmod(0o400)
    inputs = {path.relative_to(run.root).as_posix(): evidence.file_sha256(path) for path in paths}
    arguments = [sys.executable, "-I", "-S", str(script), "--request", str(request_path), "--output", str(output_path)]
    try:
        result = run.command(
            arguments, cwd=source, kind="events", cache_id="inherited-" + phase, timeout=600,
            record_execution=True, execution_inputs=tuple(inputs),
            execution_outputs=(output_path.relative_to(run.root).as_posix(),))
    except ConformanceError as error:
        diagnostic = run.root / f"diagnostics/command-{run.command_sequence:04}.jsonl"
        lines = read_bounded(diagnostic, 65536).splitlines() if diagnostic.is_file() else ()
        _controller_incomplete(phase, str(error), lines)
        raise
    record = load_json(run.read_execution_record(run.command_sequence))
    failures = [event["code"] for event in result.events if event["code"] != "None"]
    if failures:
        _controller_incomplete(phase, failures[-1], [evidence.canonical_bytes(dict(event)) for event in result.events])
        raise ConformanceError(failures[-1])
    ordinals = ((0,) if phase == "reference" else (1, 0) if phase == "architecture" else
                (2, 3, 4, 0) if phase == "historical" else
                (*range(1, 25), 0) if phase == "mutations" else (1, 2, 3, 4, 0))
    expected_events = [{"event": "control", "code": "None", "value": number} for number in ordinals]
    if (result.exit_code or list(result.events) != expected_events
            or record["runId"] != run.run_id or record["rootId"] != run.root_id
            or record["argvSha256"] != digest(arguments)
            or record["cwdSha256"] != hashlib.sha256(str(source).encode("utf-8")).hexdigest()
            or record["inputFiles"] != inputs or record["groupState"] != "Exited"
            or record["exitCode"] != 0 or record["diagnosticCode"] != "None"):
        raise ConformanceError("ProofMismatch")
    raw = read_bounded(output_path, 16 * 1024**2)
    if (record.get("outputFiles") != {
            output_path.relative_to(run.root).as_posix(): hashlib.sha256(raw).hexdigest()}
            or result.execution_record_sha256 != digest(record)):
        raise ConformanceError("ProofMismatch")
    value = load_json(raw)
    if (not isinstance(value, dict) or set(value) != {
            "schemaVersion", "qualification", "phase", "runId", "rootId", "result", "invocations", "inputSnapshots"}
            or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 3
            or value["qualification"] is not False or value["phase"] != phase
            or value["runId"] != run.run_id or value["rootId"] != run.root_id
            or not isinstance(value["result"], dict)):
        raise ConformanceError("ProofMismatch")
    legacy.verify_borrowed_invocations(
        value["invocations"], group_pid=record["childPid"], group_start_sha256=record["childStartSha256"])
    legacy.verify_borrowed_input_snapshots(value["inputSnapshots"], len(value["invocations"]))
    if phase == "reference" and value["invocations"] != [value["result"].get("invocation")]:
        raise ConformanceError("ProofMismatch")
    return value["result"], result.execution_record_sha256, {
        "qualification": False, "nativeContainment": True, "inputClosureComplete": False,
        "scope": "borrowed-launch-observations", "count": len(value["invocations"]),
        "sha256": digest(value["invocations"]), "sequence": run.command_sequence,
        "parentSha256": result.execution_record_sha256,
        "inputSnapshotsSha256": digest(value["inputSnapshots"])}


@contextmanager
def controller_transport(repository, owner, *, sdk_package=None, logger_path=None):
    import configuration_evidence as configuration
    import discovery_evidence as discovery
    import foundation_evidence as foundation
    import lifecycle_evidence as lifecycle
    import conformance_legacy as legacy
    from conformance_lock_preparation import prepare_project_lock, verify_project_lock

    repository, owner = Path(repository).resolve(strict=True), Path(owner).resolve(strict=True)
    if owner == repository or owner.is_relative_to(repository):
        raise ConformanceError("OwnershipInvalid")
    modules = (foundation, lifecycle, configuration, discovery)
    originals = {module: module.run for module in modules}
    original_graph = foundation.inspection_graph
    original_copy = foundation.copy_source
    original_processes, original_selectors = configuration.subprocess, configuration.selectors
    environment = {key: value for key, value in os.environ.items()
                   if key.startswith("HOARD_") or key == "NUGET_PACKAGES"}
    preparations = {}
    state = {"lockDerivations": [], "inputFiles": {}, "phase": "preparation", "commandSequence": 0,
             "independentRestores": frozenset(), "independentlyRestored": set()}
    runtime_inputs = {}
    if sdk_package is not None or logger_path is not None:
        if sdk_package is None or logger_path is None:
            raise ConformanceError("PrerequisiteMissing")
        for path in (sdk_package, logger_path):
            path = Path(path)
            legacy.no_symlinks(path)
            if (not path.is_absolute() or not path.is_file()
                    or not path.resolve(strict=True).is_relative_to(owner)
                    or not 0 < path.stat().st_size <= 64 * 1024**2):
                raise ConformanceError("OwnershipInvalid")
            runtime_inputs[path] = legacy._hash(path)

    def command(*arguments, cwd=None, env=None, expected=None, input=None):
        if not arguments or any(not isinstance(argument, str) for argument in arguments):
            raise ConformanceError("OwnershipInvalid")
        state["commandSequence"] += 1
        arguments = list(arguments)
        effective = dict(env or {})
        bound = {}
        runtime = {}
        independent_project = None
        if arguments[:2] == ["dotnet", "test"] and runtime_inputs:
            bound.update(runtime_inputs)
            runtime = {"sdk_package": sdk_package, "logger_path": logger_path}
            for path, hashed in runtime_inputs.items():
                if legacy._hash(path) != hashed:
                    raise ConformanceError("InputChanged")
                state["inputFiles"][path.relative_to(owner).as_posix()] = hashed
        for key in ("HOARD_FOUNDATION_EVIDENCE", "HOARD_LIFECYCLE_EVIDENCE",
                    "HOARD_CONFIGURATION_EVIDENCE", "HOARD_DISCOVERY_EVIDENCE"):
            if key not in effective and key in os.environ:
                effective[key] = os.environ[key]
            if key in effective:
                path = Path(effective[key])
                legacy.no_symlinks(path)
                if (not path.is_absolute() or not path.is_file()
                        or not path.resolve(strict=True).is_relative_to(owner)
                        or not 0 < path.stat().st_size <= 16 * 1024**2):
                    raise ConformanceError("OwnershipInvalid")
                path = path.resolve(strict=True)
                bound[path] = legacy._hash(path)
                state["inputFiles"][path.relative_to(owner).as_posix()] = bound[path]
        if arguments[:2] == ["dotnet", "restore"] and "--configfile" in arguments:
            project = Path(arguments[2]).resolve(strict=True)
            configuration_file = Path(arguments[arguments.index("--configfile") + 1]).resolve(strict=True)
            if not project.is_relative_to(owner) or not configuration_file.is_relative_to(owner):
                raise ConformanceError("OwnershipInvalid")
            if project in state["independentRestores"]:
                if "--locked-mode" not in arguments or expected is not None:
                    raise ConformanceError("InputChanged")
                arguments.append("--no-dependencies")
                independent_project = project
            feeds = ET.parse(configuration_file).findall("./packageSources/add[@key='local']")
            if len(feeds) != 1:
                raise ConformanceError("InputChanged")
            feed = Path(feeds[0].get("value", "")).resolve(strict=True)
            if not feed.is_relative_to(owner):
                raise ConformanceError("OwnershipInvalid")
            if "--locked-mode" in arguments and (project.parent / "packages.lock.json").is_file():
                key = (project, feed)
                if key not in preparations:
                    alternate, record = prepare_project_lock(project, owner, feed, "inherited-controller")
                    preparations[key] = alternate, record
                    if record is not None:
                        state["lockDerivations"].append(record)
                alternate, record = preparations[key]
                if record is not None:
                    verify_project_lock(record, owner, feed)
                    arguments.append("-p:NuGetLockFilePath=" + str(alternate))
        try:
            result = legacy.composition_controller_command(
                arguments, cwd=repository if arguments[0] == "git" else cwd,
                env=effective, expected=expected, input=input, **runtime)
            if independent_project is not None:
                state["independentlyRestored"].add(independent_project)
            return result
        except (RuntimeError, ConformanceError) as error:
            codes = ("CommandFailed", "UnknownDiagnostic", "PrerequisiteMissing", "OutputLimitExceeded")
            code = (str(error) if isinstance(error, ConformanceError) else
                    next((code for code in codes
                          if str(error) == "Legacy composition command " + code + "."), "EvidenceIncomplete"))
            print(json.dumps({
                "qualification": False, "phase": "inherited-controller-failure",
                "controller": state["phase"] if state["phase"] in (
                    "foundation", "lifecycle", "configuration", "discovery") else "preparation",
                "commandSequence": state["commandSequence"],
                "operation": arguments[1] if len(arguments) >= 2 and arguments[0] == "dotnet" and arguments[1] in (
                    "restore", "build", "pack", "format", "test", "--version") else "control",
                "code": code,
            }), flush=True)
            raise
        finally:
            if any(legacy._hash(path) != hashed for path, hashed in bound.items()):
                raise ConformanceError("InputChanged")

    def text_command(*arguments, **kwargs):
        return command(*arguments, **kwargs).stdout

    def graph(projects, ownership, *, resolve=None):
        return original_graph(projects, ownership, resolve=resolve or legacy.resolve_project)

    def copy_source(source, target, *, include_outputs=False):
        source, target = Path(source), Path(target)
        for path in (source, target):
            legacy.no_symlinks(path)
            if not path.is_absolute() or not path.resolve().is_relative_to(owner):
                raise ConformanceError("OwnershipInvalid")
        if source == owner or target.resolve().is_relative_to(source.resolve()):
            raise ConformanceError("OwnershipInvalid")
        count, size = 0, 0
        ignored = shutil.ignore_patterns(*(() if include_outputs else ("bin", "obj", "*.nupkg")))
        for directory, directories, filenames in os.walk(source, followlinks=False):
            omitted = ignored(directory, directories + filenames)
            directories[:] = [name for name in directories if name not in omitted]
            for name in (*directories, *(name for name in filenames if name not in omitted)):
                path = Path(directory) / name
                legacy.no_symlinks(path)
                count += 1
                if path.is_file():
                    size += path.stat().st_size
                elif not path.is_dir():
                    raise ConformanceError("OwnershipInvalid")
                if count > 50000 or size > 256 * 1024**2:
                    raise ConformanceError("OutputLimitExceeded")
        result = shutil.copytree(source, target) if include_outputs else original_copy(source, target)
        for path in (target, *target.rglob("*")):
            path.chmod(0o700 if path.is_dir() else 0o600 | (path.stat().st_mode & 0o111))
        return result

    try:
        foundation.run = command
        foundation.inspection_graph = graph
        foundation.copy_source = copy_source
        for module in (lifecycle, configuration, discovery):
            module.run = text_command
        configuration.subprocess = SimpleNamespace(
            Popen=lambda args, **kwargs: legacy.PublicationChild(args, owner=owner, **kwargs),
            PIPE=legacy.subprocess.PIPE, STDOUT=legacy.subprocess.STDOUT)
        configuration.selectors = SimpleNamespace(
            DefaultSelector=legacy.PublicationSelector, EVENT_READ=legacy.selectors.EVENT_READ)
        yield state
        for (project, feed), (_, record) in preparations.items():
            if record is not None:
                verify_project_lock(record, owner, feed)
    finally:
        configuration.subprocess, configuration.selectors = original_processes, original_selectors
        foundation.inspection_graph = original_graph
        foundation.copy_source = original_copy
        for module, original in originals.items():
            module.run = original
        for key in list(os.environ):
            if key.startswith("HOARD_") or key == "NUGET_PACKAGES":
                del os.environ[key]
        os.environ.update(environment)


def foundation_inventory(data, sources):
    from conformance_evidence import (
        _constant, _hash_map, _integer, _list, _one_of, _record, _runtime_identity, relative_path, sha256)

    value = load_json(data)
    if digest(value) != FOUNDATION_INVENTORY_SHA256:
        raise ConformanceError("ProofMismatch")
    assemblies = ("Hoard.Architecture.Tests", "Hoard.Composition.Tests", "Hoard.Foundation.Tests")
    value = _record({
        "schemaVersion": _constant(1),
        "originalRevision": _constant("837fdf3edf51c3df34710184d018479683c194c2"),
        "executionRevision": _constant("69aac6578c7222493832125a7bc91b4950583db9"),
        "baselineRevision": _constant(BASELINE), "qualification": _constant(False),
        "identityOrigin": _constant("original-foundation-methods-with-complete-inherited-parameters"),
        "sourceFiles": _hash_map, "executionSourceFiles": _hash_map, "controllerSources": _hash_map,
        "entries": _list(_record({
            "fullyQualifiedName": _runtime_identity,
            "parameterCount": _integer, "assembly": _one_of(*assemblies),
            "sourcePath": relative_path, "sourceSha256": sha256,
            "executionSourceSha256": sha256,
        }), 10000),
        "assemblyParameters": _record({assembly: _integer for assembly in assemblies}),
        "formatting": _constant({
            "solution": "Hoard.slnx", "fixtureRoots": ["providers", "architecture", "hosts", "compatibility"]}),
    })(value)
    if (not value["sourceFiles"] or value["sourceFiles"].keys() != value["executionSourceFiles"].keys()
            or set(value["controllerSources"]) != {
            "scripts/foundation_evidence.py", "scripts/validate-foundation.sh"}):
        raise ConformanceError("WitnessMissing")
    for path, hashed in value["executionSourceFiles"].items():
        if sources.get(path) != hashed:
            raise ConformanceError("InputChanged")
    methods, totals = {}, Counter()
    for entry in value["entries"]:
        name = entry["fullyQualifiedName"]
        if (re.fullmatch(r"Hoard\.(?:Foundation|Composition|Architecture)\.Tests\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+",
                         name) is None or name in methods or not name.startswith(entry["assembly"] + ".")
                or not 1 <= entry["parameterCount"] <= 10000
                or value["sourceFiles"].get(entry["sourcePath"]) != entry["sourceSha256"]
                or value["executionSourceFiles"].get(entry["sourcePath"]) != entry["executionSourceSha256"]):
            raise ConformanceError("WitnessMissing")
        methods[name] = entry
        totals[entry["assembly"]] += entry["parameterCount"]
    if dict(totals) != value["assemblyParameters"]:
        raise ConformanceError("WitnessMissing")
    return methods


def inventory(data, sources):
    value = load_json(data)
    if digest(value) != INVENTORY_SHA256:
        raise ConformanceError("ProofMismatch")
    if (not isinstance(value, dict) or set(value) != {
            "schemaVersion", "baselineRevision", "qualification", "identityOrigin", "sourceFiles",
            "controllerSources", "lifecycleCases", "caseMethods", "entries", "groupParameters"}
            or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1
            or value["baselineRevision"] != BASELINE or value["qualification"] is not False
            or value["identityOrigin"] != "baseline-source-methods-and-exact-parameter-counts"
            or value["lifecycleCases"] != [f"LC-{number:02}" for number in range(1, 41)]
            or not isinstance(value["sourceFiles"], dict) or not value["sourceFiles"]
            or not isinstance(value["controllerSources"], dict) or len(value["controllerSources"]) != 7
            or not isinstance(value["caseMethods"], dict)
            or set(value["caseMethods"]) != {*(f"CFG-{number:02}" for number in range(1, 37)),
                                            *(f"D{number:02}" for number in range(1, 41))}
            or not isinstance(value["entries"], list) or not 1 <= len(value["entries"]) <= 10000
            or not isinstance(value["groupParameters"], dict) or value["groupParameters"].keys() != GROUPS):
        raise ConformanceError("EvidenceSchemaInvalid")
    for path, hashed in value["sourceFiles"].items():
        if (not isinstance(path, str) or not isinstance(hashed, str)
                or re.fullmatch(r"[0-9a-f]{64}", hashed) is None
                or sources.get(path) not in (hashed, EXECUTION_SOURCE_VARIANTS.get(path, hashed))):
            raise ConformanceError("InputChanged")
    for path, hashed in value["controllerSources"].items():
        if (not isinstance(path, str) or not isinstance(hashed, str)
                or re.fullmatch(r"[0-9a-f]{64}", hashed) is None):
            raise ConformanceError("EvidenceSchemaInvalid")
    methods = {}
    totals = Counter()
    for entry in value["entries"]:
        if (not isinstance(entry, dict) or set(entry) != {
                "fullyQualifiedName", "parameterCount", "group", "sourcePath", "sourceSha256"}
                or not isinstance(entry["fullyQualifiedName"], str)
                or re.fullmatch(r"Hoard\.(?:Composition|Architecture)\.Tests\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+",
                                entry["fullyQualifiedName"]) is None
                or entry["fullyQualifiedName"] in methods
                or not isinstance(entry["group"], str) or entry["group"] not in GROUPS
                or type(entry["parameterCount"]) is not int or not 1 <= entry["parameterCount"] <= 10000
                or not isinstance(entry["sourcePath"], str)
                or value["sourceFiles"].get(entry["sourcePath"]) != entry["sourceSha256"]):
            raise ConformanceError("WitnessMissing")
        methods[entry["fullyQualifiedName"]] = entry
        totals[entry["group"]] += entry["parameterCount"]
    if dict(totals) != value["groupParameters"]:
        raise ConformanceError("WitnessMissing")
    for required in value["caseMethods"].values():
        if (not isinstance(required, list) or not required
                or any(not isinstance(method, str) or method not in methods for method in required)
                or len(set(required)) != len(required)):
            raise ConformanceError("WitnessMissing")
    return methods


def admit_discovery(data, methods, *, assembly):
    return _admit_discovery(data, methods, assembly=assembly, assemblies=ASSEMBLIES)


def admit_foundation_discovery(data, methods, *, assembly):
    return _admit_discovery(
        data, methods, assembly=assembly,
        assemblies=FOUNDATION_ASSEMBLIES,
        group="foundation")


def _admit_discovery(data, methods, *, assembly, assemblies, group=None):
    from conformance_evidence import _uuid

    if assembly not in assemblies:
        raise ConformanceError("WitnessMissing")
    expected = {name: entry for name, entry in methods.items() if name.startswith(assembly + ".")}
    rows = load_json(data)
    if not expected or not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
        raise ConformanceError("WitnessMissing")
    seen = set()
    case_ids = set()
    counts = Counter()
    admitted = []
    for row in rows:
        if (not isinstance(row, dict) or set(row) not in (
                {"testIdentity", "fullyQualifiedName"}, {"testIdentity", "fullyQualifiedName", "testCaseId"})
                or not isinstance(row["fullyQualifiedName"], str) or row["fullyQualifiedName"] not in expected
                or not isinstance(row["testIdentity"], str)
                or re.fullmatch(re.escape(row["fullyQualifiedName"])
                                + r'\(testCaseSha256: "[0-9a-f]{64}"\)', row["testIdentity"]) is None
                or row["testIdentity"] in seen):
            raise ConformanceError("WitnessMissing")
        if "testCaseId" in row:
            case_id = _uuid(row["testCaseId"])
            if case_id in case_ids:
                raise ConformanceError("WitnessMissing")
            case_ids.add(case_id)
        seen.add(row["testIdentity"])
        counts[row["fullyQualifiedName"]] += 1
        entry = expected[row["fullyQualifiedName"]]
        selected_group = entry["group"] if group is None else group
        admitted.append({
            **{key: row[key] for key in ("testIdentity", "fullyQualifiedName")},
            "assemblyId": "test-assembly", "packageId": "Hoard.Testing.Conformance",
            "bindingId": "none", "matrixId": "inherited." + selected_group,
            "caseId": "inherited-" + selected_group, "assertionSymbol": None,
        })
    if dict(counts) != {name: entry["parameterCount"] for name, entry in expected.items()}:
        raise ConformanceError("WitnessMissing")
    return sorted(admitted, key=lambda row: row["testIdentity"])


def discover_inherited_method(assembly, entry, driver_source, sdk, environment):
    import conformance_legacy as legacy
    from conformance_evidence import canonical_bytes, input_manifest
    from conformance_execution import capture_control
    from conformance_sources import read_bounded

    assembly = Path(assembly)
    root = assembly.parents[2]
    legacy.no_symlinks(root)
    method = entry["fullyQualifiedName"]
    if (assembly.name != "Hoard.Composition.Tests.dll"
            or assembly.parent != root / "resources/assembly"
            or not method.startswith("Hoard.Composition.Tests.")):
        raise ConformanceError("OwnershipInvalid")
    code, installed = capture_control(["dotnet", "--list-sdks"], limit=16384, timeout=5)
    matches = re.findall(r"^" + re.escape(sdk) + r" \[([^\r\n]+)\]$",
                         installed.decode("utf-8", errors="strict"), re.MULTILINE)
    if code or len(matches) != 1:
        raise ConformanceError("PrerequisiteMissing")
    vstest = Path(matches[0]) / sdk / "vstest.console.dll"
    legacy.no_symlinks(vstest)
    if not vstest.is_file():
        raise ConformanceError("PrerequisiteMissing")
    driver = root / "resources/discovery"
    legacy._copy_runtime(driver_source, driver)
    images = [path for folder in (assembly.parent, driver) for path in folder.rglob("*")
              if path.is_file() and (path.suffix in (".dll", ".so", ".dylib")
                                     or path.name.endswith((".deps.json", ".runtimeconfig.json")))]
    files = dict(input_manifest(root, [path.relative_to(root).as_posix() for path in images]))
    request = {
        "methods": [method],
        "assemblies": [{"id": "test-assembly" if path == assembly else f"image-{index}",
                        "path": path.relative_to(root).as_posix(),
                        "sha256": files[path.relative_to(root).as_posix()]}
                       for index, path in enumerate(images)]}
    request_path = root / "discovery-request.json"
    legacy._write(request_path, request)
    result = legacy.capture(
        ["dotnet", str(driver / "Hoard.Fixtures.Conformance.Discovery.dll"), str(root), str(vstest),
         request_path.name, digest(request), "discovered.json"],
        cwd=assembly.parent, env=environment, timeout=120)
    if result.returncode:
        raise ConformanceError("CommandFailed")
    rows = admit_discovery(read_bounded(root / "discovered.json", 2 * 1024**2),
                           {method: entry}, assembly="Hoard.Composition.Tests")
    event = load_json(result.stdout)
    if (event != {"event": "control", "code": "None", "value": len(rows)}
            or type(event["value"]) is not int
            or dict(input_manifest(root, list(files))) != files
            or read_bounded(request_path, 65536) != canonical_bytes(request)):
        raise ConformanceError("InputChanged")
    return tuple(row["testIdentity"] for row in rows)


def run_discovery_mutations(repository, owner, source, sources, sdk, *, sdk_package, logger_path):
    import conformance_legacy as legacy
    import discovery_evidence as discovery
    from conformance_case_catalog import INHERITED_GUARD_FAILURES
    from conformance_evidence import canonical_bytes, input_manifest
    from conformance_sources import read_bounded

    owner, source = Path(owner), Path(source)
    methods = inventory(read_bounded(source / INVENTORY_PATH, 2 * 1024**2), sources)
    original_files = {(source / name).relative_to(owner).as_posix(): hashed for name, hashed in sources.items()}
    if dict(input_manifest(owner, list(original_files))) != original_files:
        raise ConformanceError("InputChanged")
    work = owner / "stores/inherited-discovery-mutations"
    work.mkdir(mode=0o700)
    recipes, selected = {}, {}
    for identity, relative, original, replacement, method in discovery.MUTATIONS:
        matches = [row for name, row in methods.items()
                   if name.endswith("." + method) and row["group"] == "discovery"]
        raw = read_bounded(source / relative, 1024**2)
        if (identity in recipes or len(matches) != 1
                or raw.decode("utf-8").count(original) != 1):
            raise ConformanceError("WitnessMissing")
        recipes[identity] = relative, raw, raw.decode("utf-8").replace(original, replacement).encode("utf-8")
        selected[identity] = matches[0]
    root_files = ("Directory.Build.props", "Directory.Packages.props", "global.json", "Hoard.slnx")
    cloned = {name: hashed for name, hashed in sources.items()
              if name.startswith(("src/", "tests/", "specs/", "examples/")) or name in root_files}
    project = work / "mutations/tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj"
    driver = source / "tests/fixtures/conformance/Discovery/bin/Release/net10.0"
    observations = {}
    with controller_transport(repository, owner, sdk_package=sdk_package, logger_path=logger_path) as controls:
        controls["phase"] = "discovery"
        original_run = discovery.run

        def command(*arguments, cwd=None, env=None, input=None):
            if arguments[:2] != ("dotnet", "test"):
                return original_run(*arguments, cwd=cwd, env=env, input=input)
            if "--results-directory" not in arguments or "--logger" not in arguments:
                raise ConformanceError("OwnershipInvalid")
            directory = Path(arguments[arguments.index("--results-directory") + 1])
            identity = directory.name
            phase = {"mutation-results": "red", "repair-results": "repair"}.get(directory.parent.name)
            if identity not in recipes or phase is None:
                raise ConformanceError("OwnershipInvalid")
            method = selected[identity]["fullyQualifiedName"]
            expected_arguments = (
                "dotnet", "test", str(project), "-c", "Release", "--no-restore",
                "--filter", "FullyQualifiedName~" + method.rsplit(".", 1)[-1],
                "--logger", "trx;LogFileName=" + phase + ".trx",
                "--results-directory", str(work / directory.parent.name / identity), "-v", "minimal")
            if (arguments != expected_arguments or cwd is not None or input is not None
                    or env != {"HOARD_DISCOVERY_MUTATION": "active"} or (identity, phase) in observations):
                raise ConformanceError("ProofMismatch")
            relative, original, mutant = recipes[identity]
            files = {(work / "mutations" / name).relative_to(owner).as_posix(): hashed
                     for name, hashed in cloned.items()}
            files[(work / "mutations" / relative).relative_to(owner).as_posix()] = hashlib.sha256(
                mutant if phase == "red" else original).hexdigest()
            if dict(input_manifest(owner, list(files))) != files:
                raise ConformanceError("InputChanged")
            mutant_path = owner / f"proofs/inherited-mutation-{identity}-source.cs"
            if phase == "red":
                with mutant_path.open("xb") as output:
                    output.write(mutant)
                mutant_path.chmod(0o400)
            guard = "inherited-discovery-guard-" + identity
            guard = guard if guard in INHERITED_GUARD_FAILURES else None
            captured = {}

            def discover(assembly, selection, environment):
                if selection != expected_arguments[7]:
                    raise ConformanceError("ProofMismatch")
                identities = discover_inherited_method(assembly, selected[identity], driver, sdk, environment)
                captured.update(controller_read_inputs(owner, {}, extra=(
                    project, sdk_package, logger_path, assembly.parents[2] / "discovery-request.json")))
                captured.update(input_manifest(owner, [
                    path.relative_to(owner).as_posix() for folder in (assembly.parent, assembly.parents[1] / "discovery")
                    for path in folder.rglob("*")
                    if path.is_file()]))
                return identities

            print(json.dumps({"qualification": False, "phase": "inherited-discovery-mutation",
                              "ordinal": len(observations) + 1}), flush=True)
            result = legacy.test_command(
                arguments, env=env, assertion=None if guard else method, guard_case=guard,
                allow_failure=True, sdk_package=sdk_package, logger_path=logger_path, discover=discover)
            frozen = {**files, **captured}
            if dict(input_manifest(owner, list(frozen))) != frozen:
                raise ConformanceError("InputChanged")
            projection = directory / (phase + ".trx")
            legacy.verify_projection(projection, expected_binding="none" if guard else "legacy",
                                     expected_environment=env)
            summary = load_json(result.stdout)
            if (summary["tests"] != selected[identity]["parameterCount"]
                    or (phase == "red" and (result.returncode <= 0 or summary["failed"] <= 0))
                    or (phase == "repair" and (result.returncode != 0 or summary["failed"] != 0))):
                raise ConformanceError("WitnessMissing")
            descriptor = owner / f"proofs/inherited-mutation-{identity}-{phase}-inputs.json"
            retained = {**original_files, **captured,
                        mutant_path.relative_to(owner).as_posix(): hashlib.sha256(mutant).hexdigest()}
            document = {
                "schemaVersion": 1, "qualification": False, "mutation": identity, "phase": phase,
                "sourcePath": relative, "originalSha256": hashlib.sha256(original).hexdigest(),
                "mutantSha256": hashlib.sha256(mutant).hexdigest(),
                "readInputs": frozen, "retainedInputs": retained,
            }
            legacy._write(descriptor, document)
            observations[identity, phase] = {
                "projection": projection.relative_to(owner).as_posix(), "projectionSha256": legacy._hash(projection),
                "inputDescriptor": descriptor.relative_to(owner).as_posix(), "inputSha256": digest(document),
                "parameters": summary["tests"], "failedParameters": summary["failed"],
                "failureKind": "None" if phase == "repair" else "Guard" if guard else "Assertion",
            }
            if phase == "red":
                raise RuntimeError("Intended discovery negative observed.")
            return result.stdout.decode("utf-8")

        discovery.run = command
        try:
            negatives = discovery.mutations(source, work)
            for negative in negatives:
                identity = negative["id"]
                command(
                    "dotnet", "test", str(project), "-c", "Release", "--no-restore",
                    "--filter", "FullyQualifiedName~" + selected[identity]["fullyQualifiedName"].rsplit(".", 1)[-1],
                    "--logger", "trx;LogFileName=repair.trx",
                    "--results-directory", str(work / "repair-results" / identity), "-v", "minimal",
                    env={"HOARD_DISCOVERY_MUTATION": "active"})
        finally:
            discovery.run = original_run
    if (set(observations) != {(identity, phase) for identity in recipes for phase in ("red", "repair")}
            or dict(input_manifest(owner, list(original_files))) != original_files):
        raise ConformanceError("InputChanged")
    for observation in observations.values():
        document = load_json(read_bounded(owner / observation["inputDescriptor"], 2 * 1024**2))
        projection = owner / observation["projection"]
        guard = "inherited-discovery-guard-" + document["mutation"] in INHERITED_GUARD_FAILURES
        legacy.verify_projection(projection, expected_binding="none" if guard else "legacy",
                                 expected_environment={"HOARD_DISCOVERY_MUTATION": "active"})
        if (digest(document) != observation["inputSha256"]
                or legacy._hash(projection) != observation["projectionSha256"]
                or dict(input_manifest(owner, list(document["retainedInputs"]))) != document["retainedInputs"]):
            raise ConformanceError("InputChanged")
    return {"qualification": False, "mutations": [
        {**row, "negative": observations[row["id"], "red"], "repair": observations[row["id"], "repair"]}
        for row in negatives]}


def verify_discovery_mutation_membership(owner, mutations, scenarios):
    import conformance_legacy as legacy
    import discovery_evidence as discovery
    from conformance_case_catalog import INHERITED_GUARD_FAILURES
    from conformance_sources import read_bounded

    recipes = {row[0]: row[4] for row in discovery.MUTATIONS}
    if not isinstance(mutations, dict):
        raise ConformanceError("WitnessMissing")
    rows = mutations.get("mutations")
    if (mutations.get("qualification") is not False or not isinstance(rows, list) or len(rows) != len(recipes)
            or any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in rows)
            or {row["id"] for row in rows} != set(recipes)
            or not isinstance(scenarios, (tuple, list, set, frozenset))
            or any(not isinstance(name, str) for name in scenarios)
            or len(scenarios) != len(set(scenarios))):
        raise ConformanceError("WitnessMissing")
    owner = Path(owner).resolve(strict=True)
    for row in rows:
        identity = row["id"]
        expected = {name for name in scenarios if name.split("(")[0].rsplit(".", 1)[-1] == recipes[identity]}
        if (row.get("passed") is not True or not expected
                or len({name.split("(")[0] for name in expected}) != 1):
            raise ConformanceError("WitnessMissing")
        guard = "inherited-discovery-guard-" + identity in INHERITED_GUARD_FAILURES
        for phase, directory, filename in (
                ("negative", "mutation-results", "red.trx"), ("repair", "repair-results", "repair.trx")):
            observed = row.get(phase)
            if (not isinstance(observed, dict) or not isinstance(observed.get("projection"), str)
                    or type(observed.get("parameters")) is not int
                    or type(observed.get("failedParameters")) is not int):
                raise ConformanceError("WitnessMissing")
            path = owner / "stores/inherited-discovery-mutations" / directory / identity / filename
            if observed["projection"] != path.relative_to(owner).as_posix():
                raise ConformanceError("OwnershipInvalid")
            raw = read_bounded(path, 2 * 1024**2)
            if hashlib.sha256(raw).hexdigest() != observed.get("projectionSha256"):
                raise ConformanceError("InputChanged")
            legacy.verify_projection(path, expected_binding="none" if guard else "legacy",
                                     expected_environment={"HOARD_DISCOVERY_MUTATION": "active"})
            if read_bounded(path, 2 * 1024**2) != raw:
                raise ConformanceError("InputChanged")
            entries = [node for node in ET.fromstring(raw).iter()
                       if node.tag.rsplit("}", 1)[-1] == "UnitTestResult"]
            failed = [node.get("testName") for node in entries if node.get("outcome") == "Failed"]
            if (len(entries) != len(expected) or {node.get("testName") for node in entries} != expected
                    or any(node.get("outcome") not in ("Passed", "Failed") for node in entries)
                    or observed["parameters"] != len(expected) or observed["failedParameters"] != len(failed)
                    or (phase == "negative" and (not failed or row.get("failedTests") != failed
                        or observed.get("failureKind") != ("Guard" if guard else "Assertion")))
                    or (phase == "repair" and (failed or observed.get("failureKind") != "None"))):
                raise ConformanceError("WitnessMissing")


def execution_scopes(discoveries, methods):
    return _execution_scopes(discoveries, methods, ASSEMBLIES, admit_discovery)


def foundation_execution_scopes(discoveries, methods):
    return _execution_scopes(discoveries, methods, FOUNDATION_ASSEMBLIES, admit_foundation_discovery)


def _execution_scopes(discoveries, methods, assemblies, admit):
    if not isinstance(discoveries, dict) or set(discoveries) != assemblies:
        raise ConformanceError("WitnessMissing")
    scopes = {}
    for assembly in sorted(assemblies):
        for row in admit(discoveries[assembly], methods, assembly=assembly):
            key = (assembly, row["fullyQualifiedName"].rsplit(".", 1)[0])
            scopes.setdefault(key, []).append(row)
    return {key: tuple(rows) for key, rows in sorted(scopes.items())}


def execute_inventory_scope(run, source, feed, prior, files, closure_path, inventory_path, owner_raw, variables,
                            discovered_runtime, expected, *, assembly_name, scope, retain_settings=False):
    import time
    import conformance_evidence as evidence
    from conformance_sdk_checks import category_command_proof, write_new
    from conformance_sources import read_bounded, runtime_arguments, runtime_runner, runtime_settings
    from xml.sax.saxutils import escape

    runtime, request_path, discovery_path = discovered_runtime
    request = load_json(read_bounded(request_path, 2 * 1024**2))
    owner = load_json(owner_raw)
    images = [row for row in request["assemblies"] if (run.root / row["path"]).is_relative_to(runtime)]
    assembly = runtime / (assembly_name + ".dll")
    attempt = str(uuid.uuid4())
    inputs = evidence.admit_entity("RunInputs", {
        **prior, "runtimeAssemblies": {row["path"]: row["sha256"] for row in images},
        "configurationSha256": digest({
            "configuration": prior["configurationSha256"], "controllerReadInputs": files,
            "environmentSha256": digest(variables), "discoveryRequestSha256": digest(request)}),
        "invocation": ["component", "inherited", assembly_name, scope],
    })
    inputs_path = run.root / f"proofs/inherited-inputs-{attempt}.json"
    write_new(inputs_path, evidence.canonical_bytes(inputs))
    manifest = {
        "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": inputs["invocationGroupId"],
        "attemptId": attempt, "attemptSequence": 1, "purpose": "execution",
        "inputSha256": digest(inputs), "runInputsPath": inputs_path.relative_to(run.root).as_posix(),
        "assemblies": images, "packages": [{
            "id": package["packageId"],
            "path": (feed / (package["packageId"] + ".0.1.0.nupkg")).relative_to(run.root).as_posix(),
            "sha256": package["sha256"]} for package in inputs["packages"]], "expected": expected,
    }
    manifest_raw = evidence.canonical_bytes(manifest)
    manifest_path = run.root / f"runtime-input-{attempt}.json"
    write_new(manifest_path, manifest_raw)
    environment_xml = "<EnvironmentVariables>" + "".join(
        "<" + key + ">" + escape(value) + "</" + key + ">" for key, value in variables.items()
    ) + "</EnvironmentVariables>"
    settings_data = runtime_settings(
        run.root, assembly, attempt, digest(manifest), digest(owner), environment_xml)
    settings_directory = "proofs" if retain_settings else "stores"
    settings_path = run.root / settings_directory / f"settings-{attempt}.runsettings"
    write_new(settings_path, settings_data)
    runner = runtime_runner(run.root, prior)
    bound_paths = (
        manifest_path, inputs_path, run.root / "runtime-owner.json", settings_path, closure_path,
        source / inventory_path, request_path, discovery_path, assembly,
        runtime / (assembly_name + ".deps.json"), runtime / (assembly_name + ".runtimeconfig.json"),
        runtime / "Hoard.Conformance.TestLogger.dll", runtime / "Hoard.Testing.Conformance.dll",
    )
    for path in (*bound_paths, *(run.root / name for name in files)):
        path.chmod(0o400)
    bound = {path.relative_to(run.root).as_posix(): evidence.file_sha256(path) for path in bound_paths}
    bound.update(runner["inputFiles"])
    if any(evidence.file_sha256(run.root / name) != hashed for name, hashed in files.items()):
        raise ConformanceError("InputChanged")
    arguments = runtime_arguments(
        assembly, settings_path, [row["testIdentity"] for row in expected],
        runner_prefix=runner["prefix"])
    started = time.monotonic() * 1000
    result = run.command(
        arguments, cwd=runtime, env=variables, kind="tests", cache_id="inherited-runtime", timeout=180,
        record_execution=True, execution_inputs=tuple(bound))
    ended = time.monotonic() * 1000
    parent_sha = category_command_proof(
        run, result, arguments=arguments, cwd=runtime, manifest=manifest,
        settings_data=settings_data, started_ms=started, ended_ms=ended, settings_directory=settings_directory)
    record = load_json(run.read_execution_record(run.command_sequence))
    if parent_sha is None or record.get("inputFiles") != bound:
        raise ConformanceError("ProofMismatch")
    output = run.root / ("runtime-" + attempt)
    for path in output.iterdir():
        path.chmod(0o400)
    transport = {
        "inputs": inputs, "manifest_data": manifest_raw, "owner_data": owner_raw,
        "witnesses_data": read_bounded(output / "witnesses.jsonl", 2 * 1024**2),
        "completion_data": read_bounded(output / "completion.json", 65536),
        "proofs": {path.name: read_bounded(path, 65536) for path in output.glob("proof-*.json")},
        "expected_tests": {row["testIdentity"]: ("none", row["matrixId"]) for row in expected},
        "manifest_sha256": digest(manifest), "owner_sha256": digest(owner),
        "started_ms": started, "ended_ms": ended,
    }
    observed = evidence.ingest_runtime_attempt(**transport)
    if any(evidence.file_sha256(run.root / name) != hashed for name, hashed in {
            **files, **bound, **inputs["runtimeAssemblies"],
    }.items()):
        raise ConformanceError("InputChanged")
    if (result.exit_code or observed["diagnosticCode"] != "None"
            or any(row["status"] != "Passed" for row in observed["witnesses"])):
        raise ConformanceError("WitnessMissing")
    print(json.dumps({"qualification": False, "phase": "inherited-runtime", "scope": scope,
                      "passedParameters": len(observed["witnesses"])}), flush=True)
    return (
        {"assembly": assembly_name, "testClass": scope, "transport": transport},
        {"attemptId": attempt, "parentSha256": parent_sha},
    )


def replay_reference_consumer(owner, descriptor):
    import conformance_legacy as legacy
    from conformance_evidence import input_manifest, relative_path, sha256
    from conformance_sources import read_bounded

    owner = Path(owner).resolve(strict=True)
    if not isinstance(descriptor, dict) or set(descriptor) != {
            "manifestPath", "manifestSha256", "inputMapPath", "inputMapSha256"}:
        raise ConformanceError("EvidenceSchemaInvalid")
    manifest = owner / relative_path(descriptor["manifestPath"])
    inputs_path = owner / relative_path(descriptor["inputMapPath"])
    raw = read_bounded(inputs_path, 2 * 1024**2)
    files = load_json(raw)
    if hashlib.sha256(raw).hexdigest() != sha256(descriptor["inputMapSha256"]):
        raise ConformanceError("InputChanged")
    if (not isinstance(files, dict) or not files
            or dict(input_manifest(owner, list(files))) != files):
        raise ConformanceError("InputChanged")
    raw = read_bounded(manifest, 16 * 1024**2)
    if (hashlib.sha256(raw).hexdigest() != sha256(descriptor["manifestSha256"])
            or files.get(manifest.relative_to(owner).as_posix()) != descriptor["manifestSha256"]):
        raise ConformanceError("InputChanged")
    document = load_json(raw)
    reference = document.get("referenceConsumer") if isinstance(document, dict) else None
    if not isinstance(reference, dict) or set(reference) != {
            "source", "assembly", "assemblySha256", "assets", "runtimeConfig", "dependencies",
            "response", "responseSha256", "moduleIds"}:
        raise ConformanceError("EvidenceSchemaInvalid")
    if (any(not isinstance(reference[key], str) for key in
            ("source", "assembly", "assemblySha256", "assets", "runtimeConfig", "dependencies",
             "response", "responseSha256"))
            or not isinstance(reference["moduleIds"], list)
            or any(not isinstance(value, str) for value in reference["moduleIds"])):
        raise ConformanceError("EvidenceSchemaInvalid")
    source = Path(reference["source"])
    legacy.no_symlinks(source)
    if (not source.is_absolute() or not source.is_relative_to(owner)
            or not source.resolve(strict=True).is_relative_to(owner)):
        raise ConformanceError("OwnershipInvalid")
    paths = {key: Path(reference[key]) for key in
             ("assembly", "assets", "runtimeConfig", "dependencies", "response")}
    project = source / "ReferenceConsumer.csproj"
    code = [path for path in source.rglob("*.cs")
            if not {"bin", "obj"}.intersection(path.relative_to(source).parts)]
    if not code:
        raise ConformanceError("EvidenceIncomplete")
    for path in (project, *code, *paths.values()):
        legacy.no_symlinks(path)
        if (not path.is_absolute() or not path.is_relative_to(owner)
                or not path.resolve(strict=True).is_relative_to(owner)
                or path.relative_to(owner).as_posix() not in files):
            raise ConformanceError("OwnershipInvalid")
    try:
        declaration = ET.fromstring(read_bounded(project, 65536))
    except ET.ParseError:
        raise ConformanceError("EvidenceSchemaInvalid") from None
    if (declaration.findall(".//PackageReference") or declaration.findall(".//ProjectReference")
            or paths["assembly"].name != "ReferenceConsumer.dll"
            or files[paths["assembly"].relative_to(owner).as_posix()] != reference["assemblySha256"]
            or files[paths["response"].relative_to(owner).as_posix()] != reference["responseSha256"]):
        raise ConformanceError("InputChanged")
    arguments = ["dotnet", str(paths["assembly"])]
    observed = legacy.composition_controller_command(arguments, input=read_bounded(paths["response"], 1024**2))
    modules = load_json(observed.stdout.encode("utf-8", errors="strict"))
    if (observed.returncode or not isinstance(modules, list) or not modules
            or any(not isinstance(module, dict) or set(module) != {"Id"}
                   or module["Id"] not in legacy.DISCOVERY_MODULES for module in modules)
            or [module["Id"] for module in modules] != reference["moduleIds"]
            or dict(input_manifest(owner, list(files))) != files):
        raise ConformanceError("ProofMismatch")
    invocation = getattr(observed, "native_invocation", None)
    argv_sha256 = digest(arguments)
    cwd_sha256 = hashlib.sha256(os.getcwd().encode("utf-8")).hexdigest()
    legacy.verify_borrowed_invocation(
        invocation, argv_sha256=argv_sha256, cwd_sha256=cwd_sha256,
        stdin_sha256=reference["responseSha256"], group_pid=os.getpid())
    return {"qualification": False, "moduleCount": len(modules),
            "moduleIdsSha256": digest(reference["moduleIds"]), "inputMapSha256": descriptor["inputMapSha256"],
            "argvSha256": argv_sha256, "cwdSha256": cwd_sha256, "invocation": invocation,
            "assemblySha256": reference["assemblySha256"], "responseSha256": reference["responseSha256"]}


def verify_discovery_materials(owner, preparation, performance, run_id):
    import conformance_legacy as legacy
    import discovery_evidence as discovery
    from conformance_sources import read_bounded

    owner = Path(owner).resolve(strict=True)
    work = owner / "stores/inherited-controller-discovery"
    manifest = work / "discovery-evidence.json"
    legacy.no_symlinks(manifest)
    raw = read_bounded(manifest, 16 * 1024**2)
    if (not isinstance(preparation, dict)
            or preparation.get("manifestPath") != manifest.relative_to(owner).as_posix()
            or hashlib.sha256(raw).hexdigest() != preparation.get("manifestSha256")):
        raise ConformanceError("InputChanged")
    document = load_json(raw)
    if (not isinstance(document, dict) or document.get("referenceConsumerPassed") is not True):
        raise ConformanceError("WitnessMissing")
    performance_path = owner / "stores/inherited-runtime/performance/performance.json"
    legacy.no_symlinks(performance_path)
    if Path(performance) != performance_path:
        raise ConformanceError("OwnershipInvalid")
    observed = load_json(read_bounded(performance_path, 65536))
    try:
        discovery.verify_materials({**document, "runId": run_id, "performance": observed}, work)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        raise ConformanceError("WitnessMissing") from None
    return {
        "qualification": False, "manifestSha256": preparation["manifestSha256"],
        "performanceSha256": digest(observed), "feedPackages": len(document["feedPackages"]),
        "retainedBinaries": len(document["oldBinaries"]), "graphs": len(document["graphs"]),
        "journeys": len(document["journeys"]),
    }


def _admit_tooling_result(packet, sources):
    fields = {"mode", "scope", "qualification", "code", "tests", "failures", "errors", "skipped", "failedTests",
              "expectedFailures", "unexpectedSuccesses", "unexpectedDiagnosticBytes", "freeScratchBytes",
              "expectedTests", "observedTests"}
    if not isinstance(packet, dict) or set(packet) != fields:
        raise ConformanceError("WitnessMissing")
    modules = {Path(path).stem for path in sources
               if Path(path).parent.as_posix() == "tests/tooling"
               and Path(path).name.startswith("test_") and Path(path).suffix == ".py"}
    expected, observed = packet["expectedTests"], packet["observedTests"]
    counts = ("failures", "errors", "skipped", "expectedFailures", "unexpectedSuccesses", "unexpectedDiagnosticBytes")
    if (packet["mode"] != "diagnostic" or packet["scope"] != "tooling" or packet["qualification"] is not False
            or not isinstance(packet["code"], str) or packet["code"] not in DIAGNOSTIC_CODES
            or not isinstance(expected, list) or not 1 <= len(expected) <= 10000
            or any(not isinstance(identity, str) or len(identity) > 512
                   or re.fullmatch(r"[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+", identity) is None
                   for identity in expected)
            or len(expected) != len(set(expected)) or {identity.split(".")[0] for identity in expected} != modules
            or not isinstance(observed, list) or any(identity not in expected for identity in observed)
            or len(observed) != len(set(observed))
            or type(packet["tests"]) is not int or packet["tests"] != len(observed)
            or any(type(packet[key]) is not int or not 0 <= packet[key] <= 2**63 - 1
                   for key in (*counts, "freeScratchBytes"))):
        raise ConformanceError("WitnessMissing")
    if packet["code"] == "None" and (
            expected != observed or packet["failedTests"] != [] or any(packet[key] != 0 for key in counts)):
        raise ConformanceError("EvidenceIncomplete")
    if type(packet["failedTests"]) is not list or len(packet["failedTests"]) > 10000:
        raise ConformanceError("WitnessMissing")
    from conformance_sdk_checks import bounded_runtime_diagnostic
    for row in packet["failedTests"]:
        if (type(row) is not dict or set(row) not in (
                {"test", "code", "locations"}, {"test", "code", "locations", "runtimeDiagnostic"})
                or type(row["test"]) is not str or row["test"] not in observed
                or type(row["code"]) is not str or row["code"] not in DIAGNOSTIC_CODES
                or type(row["locations"]) is not list or len(row["locations"]) > 4
                or any(type(location) is not dict or set(location) != {"source", "line"}
                       or type(location["source"]) is not str or location["source"] not in sources
                       or type(location["line"]) is not int or not 1 <= location["line"] <= 2**31 - 1
                       for location in row["locations"])):
            raise ConformanceError("WitnessMissing")
        if "runtimeDiagnostic" in row:
            bounded_runtime_diagnostic(row["runtimeDiagnostic"])


def _read_controller_tooling(root, inputs, owner):
    import conformance_legacy as legacy
    from conformance_evidence import _number
    from conformance_sources import read_bounded

    path = Path(root) / "proofs/inherited-controller-tooling.json"
    legacy.no_symlinks(path)
    raw = read_bounded(path, 2 * 1024**2)
    document = load_json(raw)
    if (not isinstance(document, dict) or set(document) != {
                "schemaVersion", "qualification", "nativeContainment", "role", "runId", "rootId",
                "sourceManifestSha256", "startedMs", "endedMs", "result"}
            or type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1
            or not isinstance(document["result"], dict)
            or document["qualification"] is not False or document["nativeContainment"] is not False
            or document["role"] != "trusted-tooling-supervisor"
            or document["runId"] != inputs["runId"] or document["rootId"] != owner["rootId"]
            or document["sourceManifestSha256"] != inputs["sourceManifestSha256"]
            or inputs["sourceManifestSha256"] != digest(inputs["sourceManifest"])
            or not 0 <= _number(document["endedMs"]) - _number(document["startedMs"]) <= 2**63 - 1):
        raise ConformanceError("ProofMismatch")
    _admit_tooling_result(document["result"], inputs["sourceManifest"])
    return raw, document


def controller_tooling_observation(root, inputs, owner):
    """Project only validated finite diagnostics, including an incomplete supervisor run."""
    _, document = _read_controller_tooling(root, inputs, owner)
    packet = document["result"]
    runtime = [{
        "toolingTestSha256": hashlib.sha256(row["test"].encode("utf-8")).hexdigest(),
        **row["runtimeDiagnostic"],
    } for row in packet["failedTests"] if "runtimeDiagnostic" in row]
    return {
        "qualification": False, "nativeContainment": False, "scope": "trusted-tooling-supervisor",
        "code": packet["code"], "elapsedMs": document["endedMs"] - document["startedMs"],
        "expectedTests": len(packet["expectedTests"]), "observedTests": packet["tests"],
        **{key: packet[key] for key in (
            "failures", "errors", "skipped", "expectedFailures", "unexpectedSuccesses", "unexpectedDiagnosticBytes")},
        **({"runtimeFailureCount": len(runtime), "runtimeFailures": runtime[:4]} if runtime else {}),
    }


def verify_controller_tooling(root, summary, inputs, owner):
    raw, document = _read_controller_tooling(root, inputs, owner)
    if (not isinstance(summary, dict) or set(summary) != {
            "qualification", "nativeContainment", "role", "sha256", "tests", "sourceManifestSha256"}
            or summary["qualification"] is not False or summary["nativeContainment"] is not False
            or summary["role"] != "trusted-tooling-supervisor"
            or summary["sha256"] != hashlib.sha256(raw).hexdigest()
            or summary["sourceManifestSha256"] != inputs["sourceManifestSha256"]
            or type(summary["tests"]) is not int
            or document["endedMs"] - document["startedMs"] >= TOOLING_SUITE_SECONDS * 1000):
        raise ConformanceError("ProofMismatch")
    if document["result"]["code"] != "None" or summary["tests"] != document["result"]["tests"]:
        raise ConformanceError("EvidenceIncomplete")


def run_controller_tooling(repository, run, sources):
    """Run trusted harness regressions in their owning supervisor, not a provider child."""
    import time
    import conformance_legacy as legacy
    import conformance_unit_checks as checks
    from conformance_evidence import source_manifest

    if (Path(checks.__file__).resolve().parents[1] != Path(repository).resolve()
            or run.state != "Active" or legacy._borrowed_group() is not None or run.live_children()):
        raise ConformanceError("OwnershipInvalid")
    if dict(source_manifest(repository)) != dict(sources):
        raise ConformanceError("InputChanged")
    started = time.monotonic()
    deadline = min(run.deadline, started + TOOLING_SUITE_SECONDS)
    if started >= deadline:
        raise ConformanceError("DeadlineExceeded")
    packet = checks.run_checks(all_tooling=True, deadline=deadline)
    ended = time.monotonic()
    if dict(source_manifest(repository)) != dict(sources):
        raise ConformanceError("InputChanged")
    if run.live_children():
        raise ConformanceError("CleanupIncomplete")
    _admit_tooling_result(packet, sources)
    if packet["code"] == "None" and ended >= deadline:
        raise ConformanceError("EvidenceIncomplete")
    document = {
        "schemaVersion": 1, "qualification": False, "nativeContainment": False,
        "role": "trusted-tooling-supervisor", "runId": run.run_id, "rootId": run.root_id,
        "sourceManifestSha256": digest(sources), "startedMs": started * 1000, "endedMs": ended * 1000,
        "result": packet,
    }
    path = run.root / "proofs/inherited-controller-tooling.json"
    legacy._write(path, document)
    path.chmod(0o400)
    if packet["code"] != "None":
        raise ConformanceError(packet["code"])
    return {"qualification": False, "nativeContainment": False, "role": "trusted-tooling-supervisor",
            "sha256": legacy._hash(path), "tests": packet["tests"], "sourceManifestSha256": digest(sources)}


CONTROLLER_BASELINES = "proofs/inherited-controller-baselines.json"


def _controller_baseline_entries(registration, retained, path):
    import configuration_evidence as configuration
    import discovery_evidence as discovery
    from conformance_evidence import _constant, _one_of, _record, relative_path, sha256

    def hashes(value):
        if not isinstance(value, dict) or len(value) > 50000:
            raise ConformanceError("EvidenceSchemaInvalid")
        return {relative_path(key): sha256(hashed) for key, hashed in value.items()}

    registration = dict(_record({"assembly": path, "sha256": sha256})(registration))
    if not isinstance(retained, dict) or set(retained) != {"configuration", "discovery"}:
        raise ConformanceError("EvidenceSchemaInvalid")
    result = {}
    for phase, revision, names in (
            ("configuration", configuration.BASELINE, ("LegacyOptions", "LifecycleConsumer")),
            ("discovery", discovery.BASELINE, ("RetainedLifecycle", "RetainedConfiguration", "LegacyOptions"))):
        fields = {"name": _one_of(*names), "baseline": _constant(revision),
                  "assembly": path, "sha256": sha256, "assets": path}
        if phase == "discovery":
            fields.update(baselineAssetsSha256=sha256, baselineDependencyHashes=hashes,
                          linkedSourceHashes=hashes, sourceHashes=hashes)
        entries = retained[phase]
        if not isinstance(entries, list) or len(entries) != len(names):
            raise ConformanceError("EvidenceSchemaInvalid")
        result[phase] = [dict(_record(fields)(entry)) for entry in entries]
        if {entry["name"] for entry in result[phase]} != set(names):
            raise ConformanceError("EvidenceSchemaInvalid")
    return registration, result


def _controller_baseline_files(owner, roots):
    import conformance_legacy as legacy
    from conformance_evidence import file_sha256

    files, size = {}, 0
    for root in roots:
        legacy.no_symlinks(root)
        if not root.is_dir() or not root.resolve(strict=True).is_relative_to(owner):
            raise ConformanceError("OwnershipInvalid")
        for directory, directories, filenames in os.walk(root, followlinks=False):
            if Path(directory) == root:
                directories[:] = [name for name in directories if name not in (
                    "cache", "old-cache", "old-platform-cache", "baseline-cache", "baseline-replay-cache")]
            for name in (*directories, *filenames):
                path = Path(directory) / name
                legacy.no_symlinks(path)
                if path.is_file():
                    size += path.stat().st_size
                    if len(files) >= 50000 or size > 256 * 1024**2:
                        raise ConformanceError("OutputLimitExceeded")
                    files[path.relative_to(owner).as_posix()] = file_sha256(path)
                elif not path.is_dir():
                    raise ConformanceError("OwnershipInvalid")
    return dict(sorted(files.items()))


def prepare_controller_baselines(repository, run):
    """Seal historical controller inputs before any candidate command or feed exists."""
    import configuration_evidence as configuration
    import discovery_evidence as discovery
    import lifecycle_evidence as lifecycle
    import conformance_baselines as baselines
    import conformance_legacy as legacy
    from conformance_evidence import synthetic_nuget_configuration

    if run.command_sequence != 0 or (run.root / "feed/candidate").exists():
        raise ConformanceError("InputChanged")
    historical = run.root / "stores/inherited-historical"
    if historical.exists() or (run.root / CONTROLLER_BASELINES).exists():
        raise ConformanceError("InputChanged")
    frozen = baselines.export_revision(repository, run, BASELINE, "inherited-f06-recipes")
    recipes = baselines._hash_tree(frozen, exclude_outputs=True)
    historical.mkdir(mode=0o700)
    roots, retained = [frozen], {}
    with controller_transport(repository, run.root) as controls:
        controls["phase"] = "lifecycle"
        print(json.dumps({"qualification": False, "phase": "inherited-historical-preparation",
                          "controller": "lifecycle"}), flush=True)
        registration_root = historical / "registration"
        registration_root.mkdir(mode=0o700)
        feed = registration_root / "feed"
        feed.mkdir(mode=0o700)
        config = registration_root / "NuGet.Config"
        config.write_bytes(synthetic_nuget_configuration(feed))
        registration = lifecycle.prepare_registration_baseline(frozen, registration_root, config, False)
        feed.rmdir()
        roots.append(registration_root)
        for phase, module in (("configuration", configuration), ("discovery", discovery)):
            controls["phase"] = phase
            print(json.dumps({"qualification": False, "phase": "inherited-historical-preparation",
                              "controller": phase}), flush=True)
            target = historical / phase
            target.mkdir(mode=0o700)
            retained[phase] = module.prepare_baseline(frozen, target, False)
            roots.append(target)
    if baselines._hash_tree(frozen, exclude_outputs=True) != recipes:
        raise ConformanceError("InputChanged")
    files = _controller_baseline_files(run.root, roots)

    def relative(value):
        from conformance_evidence import relative_path
        if not isinstance(value, str):
            raise ConformanceError("EvidenceSchemaInvalid")
        path = Path(value)
        legacy.no_symlinks(path)
        if not path.is_absolute() or not path.is_file() or not path.is_relative_to(run.root):
            raise ConformanceError("OwnershipInvalid")
        return relative_path(path.relative_to(run.root).as_posix())

    registration, retained = _controller_baseline_entries(registration, retained, relative)
    document = {
        "schemaVersion": 2, "qualification": False, "nativeContainment": False, "mode": "preparation",
        "runId": run.run_id, "rootId": run.root_id, "baselineRevision": BASELINE,
        "recipeSourceSha256": digest(recipes), "registration": registration, "retained": retained,
        "files": files,
    }
    path = run.root / CONTROLLER_BASELINES
    legacy._write(path, document)
    for relative in (*files, CONTROLLER_BASELINES):
        (run.root / relative).chmod(0o400)
    seal = {"path": CONTROLLER_BASELINES, "sha256": legacy._hash(path)}
    verify_controller_baselines(run, seal)
    return seal


def verify_controller_baselines(run, seal):
    import conformance_legacy as legacy
    from conformance_evidence import file_sha256, relative_path
    from conformance_sources import read_bounded

    if (not isinstance(seal, dict) or set(seal) != {"path", "sha256"}
            or seal["path"] != CONTROLLER_BASELINES or not isinstance(seal["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", seal["sha256"]) is None):
        raise ConformanceError("ProofMismatch")
    path = run.root / CONTROLLER_BASELINES
    legacy.no_symlinks(path)
    raw = read_bounded(path, 16 * 1024**2)
    if hashlib.sha256(raw).hexdigest() != seal["sha256"]:
        raise ConformanceError("InputChanged")
    value = load_json(raw)
    if (not isinstance(value, dict) or set(value) != {
            "schemaVersion", "qualification", "nativeContainment", "mode", "runId", "rootId",
            "baselineRevision", "recipeSourceSha256", "registration", "retained", "files"}
            or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 2
            or value["qualification"] is not False or value["nativeContainment"] is not False
            or value["mode"] != "preparation" or value["runId"] != run.run_id or value["rootId"] != run.root_id
            or value["baselineRevision"] != BASELINE or not isinstance(value["recipeSourceSha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", value["recipeSourceSha256"]) is None
            or not isinstance(value["registration"], dict)
            or set(value["registration"]) != {"assembly", "sha256"}
            or not isinstance(value["retained"], dict) or set(value["retained"]) != {"configuration", "discovery"}
            or not isinstance(value["files"], dict) or not 1 <= len(value["files"]) <= 50000):
        raise ConformanceError("EvidenceSchemaInvalid")
    size = 0
    for relative, hashed in value["files"].items():
        path = run.root / relative_path(relative)
        legacy.no_symlinks(path)
        if not path.is_file():
            raise ConformanceError("InputChanged")
        if not isinstance(hashed, str) or re.fullmatch(r"[0-9a-f]{64}", hashed) is None:
            raise ConformanceError("EvidenceSchemaInvalid")
        size += path.stat().st_size
        if size > 256 * 1024**2:
            raise ConformanceError("OutputLimitExceeded")
        if file_sha256(path) != hashed:
            raise ConformanceError("InputChanged")
    registration, retained = _controller_baseline_entries(value["registration"], value["retained"], relative_path)
    entries = [registration]
    for phase_entries in retained.values():
        for entry in phase_entries:
            if entry["assets"] not in value["files"]:
                raise ConformanceError("ProofMismatch")
        entries.extend(phase_entries)
    for entry in entries:
        if value["files"].get(entry["assembly"]) != entry["sha256"]:
            raise ConformanceError("ProofMismatch")
    return {
        **value, "registration": {**registration, "assembly": str(run.root / registration["assembly"])},
        "retained": {phase: [{**entry, "assembly": str(run.root / entry["assembly"]),
                             "assets": str(run.root / entry["assets"])} for entry in entries]
                     for phase, entries in retained.items()},
    }


def replay_controller_baseline(owner, baseline, phase, target):
    """Copy the prebuilt project tree; candidate dependency replacement stays in the replay."""
    import foundation_evidence as foundation
    from conformance_evidence import file_sha256

    source = owner / "stores/inherited-historical" / phase / "retained"
    destination = target / "retained"
    foundation.copy_source(source, destination, include_outputs=True)
    retained = []
    for entry in baseline["retained"][phase]:
        replay = dict(entry)
        for key in ("assembly", "assets"):
            replay[key] = str(destination / Path(entry[key]).relative_to(source))
        if file_sha256(Path(replay["assembly"])) != replay["sha256"]:
            raise ConformanceError("InputChanged")
        retained.append(replay)
    return retained


def admit_architecture_preparation(root, prepared):
    from conformance_evidence import _constant, _hash_map, _integer, _record, input_manifest, sha256
    from conformance_sources import read_bounded

    prepared = _record({
        "qualification": _constant(False), "profileComplete": _constant(False),
        "manifestPath": _constant("stores/compatibility-architecture/manifest.json"),
        "manifestSha256": sha256, "inputMapPath": _constant("proofs/compatibility-architecture-inputs.json"),
        "inputMapSha256": sha256, "inputCount": _integer,
        "fixtureGraphs": _constant(22), "requiredRealScans": _constant(8), "lockDerivationsSha256": sha256,
    })(prepared)
    raw = read_bounded(root / prepared["inputMapPath"], 2 * 1024**2)
    selected = _hash_map(load_json(raw))
    if (hashlib.sha256(raw).hexdigest() != prepared["inputMapSha256"]
            or len(selected) != prepared["inputCount"]
            or selected.get(prepared["manifestPath"]) != prepared["manifestSha256"]
            or dict(input_manifest(root, list(selected))) != selected):
        raise ConformanceError("InputChanged")
    return prepared, selected


def prepare_architecture_evidence(repository, owner, source):
    import foundation_evidence as foundation
    import conformance_legacy as legacy
    from conformance_case_catalog import ARCHITECTURE_RUNTIME_ROWS
    from conformance_evidence import input_manifest
    from conformance_sources import read_bounded

    owner, source = Path(owner), Path(source)
    for path in (owner, source):
        legacy.no_symlinks(path)
    owner, source = owner.resolve(strict=True), source.resolve(strict=True)
    if source == owner or not source.is_relative_to(owner):
        raise ConformanceError("OwnershipInvalid")
    foundation_path = source / FOUNDATION_INVENTORY_PATH
    legacy.no_symlinks(foundation_path)
    foundation_raw = read_bounded(foundation_path, 2 * 1024**2)
    foundation_sources = load_json(foundation_raw)
    if digest(foundation_sources) != FOUNDATION_INVENTORY_SHA256:
        raise ConformanceError("ProofMismatch")
    foundation_sources = foundation_sources["executionSourceFiles"]
    prefix = source.relative_to(owner).as_posix() + "/"
    captured_sources = input_manifest(owner, [prefix + path for path in foundation_sources])
    foundation_methods = foundation_inventory(
        foundation_raw, {path: captured_sources[prefix + path] for path in foundation_sources})
    target = owner / "stores/compatibility-architecture"
    target.mkdir(mode=0o700)
    with controller_transport(repository, owner) as controls:
        architecture_source = source / "tests/fixtures/architecture"
        projects = frozenset(architecture_source.rglob("*.csproj"))
        if not 1 <= len(projects) <= 128:
            raise ConformanceError("WitnessMissing")
        for project in projects:
            try:
                document = ET.fromstring(read_bounded(project, 65536))
            except ET.ParseError:
                raise ConformanceError("InputChanged") from None
            for reference in document.findall(".//ProjectReference"):
                include = reference.get("Include")
                if not include or (project.parent / include).resolve() not in projects:
                    raise ConformanceError("WitnessMissing")
        controls["independentRestores"] = frozenset(
            target / "architecture" / project.relative_to(architecture_source) for project in projects)
        controls["phase"] = "foundation"
        print(json.dumps({"qualification": False, "phase": "inherited-controller-preparation",
                          "controller": "foundation"}), flush=True)
        before = foundation.source_hashes(source)
        core, providers, config = foundation.packages(source, target, False)
        document = {
            "core": core, "providers": providers, "localFeed": str(target / "feed"),
            "declarations": foundation.declarations(source, target),
            "sourceHashesBefore": before,
            "foundationInventory": {
                "path": str(foundation_path), "sha256": hashlib.sha256(foundation_raw).hexdigest(),
                "canonicalSha256": FOUNDATION_INVENTORY_SHA256,
                "methods": len(foundation_methods),
                "parameters": sum(row["parameterCount"] for row in foundation_methods.values()),
            },
        }
        document["hosts"] = foundation.hosts(source, target, config, False)
        document["breaking"] = foundation.breaking(source, target, config, False)
        document["architecture"], document["cycles"] = foundation.architecture(source, target, config, False)
        if controls["independentlyRestored"] != controls["independentRestores"]:
            raise ConformanceError("WitnessMissing")
        document["realArchitecture"] = foundation.real_architecture(source, target, document)
        document["sourceHashesAfter"] = foundation.source_hashes(source)
        if (document["sourceHashesAfter"] != before
                or read_bounded(foundation_path, 2 * 1024**2) != foundation_raw):
            raise ConformanceError("InputChanged")
        expected = {"permitted", "identity-hosting", *(name for rows in ARCHITECTURE_RUNTIME_ROWS.values()
                                                      for name in rows)}
        scans = {
            "platform", "provider:Hoard.Fixtures.Protocol", "provider:Hoard.Fixtures.Metadata",
            "provider:Hoard.Fixtures.Artifact.One", "provider:Hoard.Fixtures.Artifact.Two",
            "provider:Hoard.Fixtures.Identity", "host:One", "host:Two"}
        if (document["architecture"].keys() != expected or len(document["realArchitecture"]) != len(scans)
                or {graph["scanId"] for graph in document["realArchitecture"]} != scans):
            raise ConformanceError("WitnessMissing")
        manifest_path = target / "manifest.json"
        legacy._write(manifest_path, document)
        manifest_path.chmod(0o400)
        files = controller_read_inputs(owner, {"foundation": manifest_path}, extra=(
            source / "tests/fixtures/architecture/ownership.json",
            source / "tests/fixtures/architecture/Cycles/graph.json"))
    inputs_path = owner / "proofs/compatibility-architecture-inputs.json"
    legacy._write(inputs_path, files)
    inputs_path.chmod(0o400)
    return {
        "qualification": False, "profileComplete": False,
        "manifestPath": manifest_path.relative_to(owner).as_posix(), "manifestSha256": legacy._hash(manifest_path),
        "inputMapPath": inputs_path.relative_to(owner).as_posix(), "inputMapSha256": legacy._hash(inputs_path),
        "inputCount": len(files), "fixtureGraphs": len(expected), "requiredRealScans": len(scans),
        "lockDerivationsSha256": digest(controls["lockDerivations"]),
    }


def prepare_controller_evidence(repository, owner, source, *, sdk_package=None, logger_path=None,
                                prepared_baselines=None):
    """Prepare fresh borrowed evidence, without claiming full controller acceptance."""
    import configuration_evidence as configuration
    import discovery_evidence as discovery
    import foundation_evidence as foundation
    import lifecycle_evidence as lifecycle
    import conformance_legacy as legacy
    from conformance_sources import read_bounded

    owner, source = Path(owner), Path(source)
    legacy.no_symlinks(owner)
    legacy.no_symlinks(source)
    owner, source = Path(owner).resolve(strict=True), Path(source).resolve(strict=True)
    if source == owner or not source.is_relative_to(owner):
        raise ConformanceError("OwnershipInvalid")
    manifests, phases, format_projects = {}, {}, {}
    with controller_transport(repository, owner, sdk_package=sdk_package, logger_path=logger_path) as controls:
        for phase in ("foundation", "lifecycle", "configuration", "discovery"):
            controls["phase"] = phase
            print(json.dumps({"qualification": False, "phase": "inherited-controller-preparation",
                              "controller": phase}), flush=True)
            target = owner / "stores" / ("inherited-controller-" + phase)
            target.mkdir(mode=0o700)
            if phase == "foundation":
                core, providers, config = foundation.packages(source, target, False)
                document = {
                    "core": core, "providers": providers, "localFeed": str(target / "feed"),
                    "sourceHashesBefore": foundation.source_hashes(source),
                }
                document["hosts"] = foundation.hosts(source, target, config, False)
                document["sourceHashesAfter"] = foundation.source_hashes(source)
                summary = {"providerPackages": len(providers), "customHosts": len(document["hosts"])}
                projects = [project for base in ("providers", "architecture", "hosts", "compatibility")
                            for project in sorted((target / base).glob("**/*.csproj"))]
            elif phase == "lifecycle":
                config, providers = lifecycle.prepare_packages(source, target, False)
                registration = lifecycle.registration_compatibility(
                    source, target, config, False,
                    prepared=None if prepared_baselines is None else prepared_baselines["registration"])
                journeys, hosts = lifecycle.host_journeys(source, target, config, False)
                graphs = lifecycle.prepare_lifecycle_graphs(source, target, providers, hosts, registration)
                manifest = Path(os.environ["HOARD_LIFECYCLE_EVIDENCE"])
                document = load_json(read_bounded(manifest, 16 * 1024**2))
                summary = {"providerPackages": len(providers), "journeys": journeys, "graphs": len(graphs)}
                projects = [*(Path(proof["project"]) for proof in providers), *hosts, registration]
            else:
                module = configuration if phase == "configuration" else discovery
                retained = (module.prepare_baseline(source, target, False) if prepared_baselines is None
                            else replay_controller_baseline(owner, prepared_baselines, phase, target))
                config, providers = lifecycle.prepare_packages(source, target, False)
                if phase == "configuration":
                    provider, consumer = configuration.compatibility(source, target, config, retained, False)
                    registration = lifecycle.registration_compatibility(
                        source, target, config, False, "registration-baseline",
                        prepared=None if prepared_baselines is None else prepared_baselines["registration"])
                    hosts, journeys = configuration.configured_journeys(source, target, config, retained, False)
                    conversion, publication = configuration.interrupted_publication(source, target, config, False)
                    graphs = configuration.configuration_graphs(
                        source, target, providers, hosts, provider, consumer, registration, conversion)
                    document = {"graphs": graphs, "journeys": journeys, "oldBinaries": retained,
                                "publication": publication, "packages": providers}
                    summary = {"retainedBinaries": len(retained), "journeys": len(journeys),
                               "graphs": len(graphs), "publicationBarriers": len(publication["barriers"])}
                    projects = [*(Path(proof["project"]) for proof in providers), *hosts,
                                provider, consumer, registration, conversion]
                else:
                    old = next(entry for entry in retained if entry["name"] == "LegacyOptions")
                    old_provider = Path(old["assembly"]).parents[3] / "LegacyOptions.csproj"
                    discovery.run("dotnet", "pack", str(old_provider), "-c", "Release", "--no-build",
                                  "--no-restore", "-o", str(target / "feed"), "-v", "quiet")
                    foundation.canonicalize_acceptance_archive(
                        target / "feed/Hoard.Fixtures.Configuration.LegacyOptions.0.1.0.nupkg")
                    consumers = discovery.compatibility(source, target, config, retained, False)
                    hosts, journeys, observations, bodies = discovery.package_journeys(
                        source, target, config, retained, False)
                    registration = lifecycle.registration_compatibility(
                        source, target, config, False, "registration-baseline",
                        prepared=None if prepared_baselines is None else prepared_baselines["registration"])
                    graphs = discovery.graphs(
                        source, target, config, providers, hosts, consumers, old_provider, registration, False)
                    reference = discovery.reference_consumer(source, target, bodies)
                    feed_packages = [
                        {"id": package.name, "package": str(package),
                         "sha512": hashlib.sha512(read_bounded(package, 64 * 1024**2)).hexdigest()}
                        for package in sorted((target / "feed").glob("*.nupkg"))]
                    document = {"graphs": graphs, "journeys": journeys, "observations": observations,
                                "responseBodies": bodies, "oldBinaries": retained, "packages": providers,
                                "referenceConsumer": reference, "referenceConsumerPassed": True,
                                "feedPackages": feed_packages}
                    summary = {"retainedBinaries": len(retained), "journeys": len(journeys),
                               "observations": len(observations), "graphs": len(graphs),
                               "referenceConsumerPassed": True}
                    projects = [*hosts, *consumers.values(), *(Path(proof["project"]) for proof in providers)]
            format_projects[phase] = [Path(project).relative_to(owner).as_posix() for project in projects]
            if phase != "lifecycle":
                manifest = target / (phase + "-evidence.json")
                legacy._write(manifest, document)
            variable = "HOARD_" + phase.upper() + "_EVIDENCE"
            manifests[variable] = manifest.relative_to(owner).as_posix()
            phases[phase] = {
                **summary, "manifestPath": manifest.relative_to(owner).as_posix(),
                "manifestSha256": legacy._hash(manifest),
            }
        legacy._write(owner / "proofs/inherited-controller-lock-derivations.json", controls["lockDerivations"])
        legacy._write(owner / "proofs/inherited-controller-command-inputs.json", controls["inputFiles"])
        formatting = owner / "proofs/inherited-controller-format-projects.json"
        legacy._write(formatting, format_projects)
    return {"qualification": False, "fullControllerAcceptance": False, "nativeContainment": False,
            "manifests": manifests, "phases": phases,
            "formatting": {"path": formatting.relative_to(owner).as_posix(), "sha256": legacy._hash(formatting)}}


def controller_runtime_read_inputs(owner, settings, *, cwd):
    from conformance_evidence import _uuid, relative_path, sha256
    from conformance_sources import read_bounded
    import conformance_legacy as legacy

    try:
        configuration = ET.fromstring(read_bounded(settings, 256 * 1024)).findall(
            "./LoggerRunSettings/Loggers/Logger[@friendlyName='HoardSafe']/Configuration")
    except ET.ParseError:
        raise ConformanceError("EvidenceSchemaInvalid") from None
    fields = {"Root", "AttemptId", "ManifestSha256", "OwnerSha256"}
    if (len(configuration) != 1 or len(configuration[0]) != len(fields)
            or {child.tag for child in configuration[0]} != fields
            or any(child.attrib or len(child) or not isinstance(child.text, str) or not child.text
                   for child in configuration[0])):
        raise ConformanceError("EvidenceSchemaInvalid")
    values = {child.tag: child.text for child in configuration[0]}
    root = Path(values["Root"])
    if not root.is_absolute():
        root = Path(cwd) / root
    legacy.no_symlinks(root)
    root = root.resolve(strict=True)
    if not root.is_relative_to(owner) or not root.is_dir():
        raise ConformanceError("OwnershipInvalid")
    attempt = _uuid(values["AttemptId"])
    manifest_path = root / f"runtime-input-{attempt}.json"
    raw = read_bounded(manifest_path, 2 * 1024**2)
    if hashlib.sha256(raw).hexdigest() != sha256(values["ManifestSha256"]):
        raise ConformanceError("InputChanged")
    manifest = load_json(raw)
    if (not isinstance(manifest, dict) or type(manifest.get("schemaVersion")) is not int
            or manifest["schemaVersion"] != 1 or manifest.get("attemptId") != attempt
            or not {"runInputsPath", "inputSha256", "assemblies", "packages"} <= manifest.keys()):
        raise ConformanceError("ProofMismatch")
    files = {
        manifest_path: values["ManifestSha256"], root / "runtime-owner.json": sha256(values["OwnerSha256"]),
        root / relative_path(manifest["runInputsPath"]): sha256(manifest["inputSha256"]),
    }
    for kind, maximum in (("assemblies", 128), ("packages", 1024)):
        rows = manifest.get(kind)
        if not isinstance(rows, list) or not 1 <= len(rows) <= maximum:
            raise ConformanceError("EvidenceSchemaInvalid")
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"id", "path", "sha256"}:
                raise ConformanceError("EvidenceSchemaInvalid")
            path, hashed = root / relative_path(row["path"]), sha256(row["sha256"])
            if path in files and files[path] != hashed:
                raise ConformanceError("ProofMismatch")
            files[path] = hashed
    return files


def controller_command_read_inputs(owner, arguments, *, cwd=None, env=None):
    """Capture selected declared inputs, not a complete native I/O trace."""
    import conformance_legacy as legacy
    from conformance_sources import read_bounded

    owner = Path(owner).resolve(strict=True)
    if (not isinstance(arguments, (list, tuple)) or not arguments
            or any(not isinstance(argument, str) for argument in arguments)):
        raise ConformanceError("OwnershipInvalid")
    extra, mutable, declared = set(), set(), {}
    dotnet = Path(arguments[0]).name == "dotnet"
    restoring = (dotnet and len(arguments) > 1 and (arguments[1] == "restore"
                 or arguments[1] in ("build", "pack", "format") and "--no-restore" not in arguments))
    directory = Path(cwd or os.getcwd()).resolve(strict=True)

    def project_files(project):
        pending, visited = [project], set()
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            if len(visited) > 2048:
                raise ConformanceError("OutputLimitExceeded")
            extra.add(current)
            extra.update(item for item in current.parent.rglob("*.cs")
                         if not {"bin", "obj"}.intersection(item.relative_to(current.parent).parts))
            if restoring:
                mutable.update(current.parent / name for name in (
                    "obj/project.assets.json", f"obj/{current.name}.nuget.g.props",
                    f"obj/{current.name}.nuget.g.targets"))
                if "--locked-mode" not in arguments:
                    mutable.add(current.parent / "packages.lock.json")
            try:
                document = ET.fromstring(read_bounded(current, 1024 * 1024))
            except ET.ParseError:
                raise ConformanceError("EvidenceSchemaInvalid") from None
            for node in document.iter():
                tag = node.tag.split("}")[-1]
                if tag not in ("Compile", "ProjectReference", "Import", "HintPath"):
                    continue
                value = node.text if tag == "HintPath" else node.get("Project" if tag == "Import" else "Include")
                if not isinstance(value, str):
                    continue
                for expression in value.split(";"):
                    if not expression or any(token in expression for token in ("$(", "@(", "%(", "*", "?")):
                        continue
                    item = current.parent / expression.replace("\\", "/")
                    legacy.no_symlinks(item)
                    item = item.resolve()
                    if not item.is_relative_to(owner):
                        raise ConformanceError("OwnershipInvalid")
                    if item.is_file():
                        extra.add(item)
                        if tag == "ProjectReference":
                            pending.append(item)

    for index, argument in enumerate(arguments[1:], 1):
        contract_reference = argument.startswith("-p:ContractAssembly=")
        for prefix in ("--Settings:", "-p:NuGetLockFilePath=", "-p:ContractAssembly="):
            if argument.startswith(prefix):
                argument = argument[len(prefix):]
                break
        path = Path(argument)
        if not path.is_absolute():
            if path.suffix not in (".dll", ".csproj", ".slnx", ".json", ".runsettings", ".config"):
                continue
            path = directory / path
        legacy.no_symlinks(path)
        path = path.resolve()
        if not path.is_relative_to(owner):
            if contract_reference:
                raise ConformanceError("OwnershipInvalid")
            target = index == 1 or index == 2 and arguments[1] in (
                "build", "restore", "pack", "publish", "test", "vstest", "msbuild", "exec", "format")
            if dotnet and (path.suffix in (".csproj", ".slnx") or path.suffix == ".dll" and target):
                raise ConformanceError("OwnershipInvalid")
            continue
        if not path.is_file():
            if contract_reference:
                raise ConformanceError("InputChanged")
            continue
        extra.add(path)
        if path.suffix == ".csproj":
            project_files(path)
        elif path.suffix == ".slnx":
            extra.update(item for item in path.parent.rglob("*.cs")
                         if not {"bin", "obj"}.intersection(item.relative_to(path.parent).parts))
        elif path.suffix == ".dll":
            extra.update(item for item in path.parent.iterdir() if item.is_file())
        elif path.suffix == ".runsettings":
            for item, hashed in controller_runtime_read_inputs(owner, path, cwd=directory).items():
                if item in declared and declared[item] != hashed:
                    raise ConformanceError("ProofMismatch")
                declared[item] = hashed
                extra.add(item)
        elif path.name == "NuGet.Config":
            try:
                configuration = ET.fromstring(read_bounded(path, 65536))
            except ET.ParseError:
                raise ConformanceError("EvidenceSchemaInvalid") from None
            for entry in configuration.findall("./packageSources/add"):
                feed = Path(entry.get("value", ""))
                if feed.is_absolute():
                    legacy.no_symlinks(feed)
                    if not feed.resolve(strict=True).is_relative_to(owner):
                        raise ConformanceError("OwnershipInvalid")
                    extra.update(feed.glob("*.nupkg"))
    for key in ("HOARD_FOUNDATION_EVIDENCE", "HOARD_LIFECYCLE_EVIDENCE",
                "HOARD_CONFIGURATION_EVIDENCE", "HOARD_DISCOVERY_EVIDENCE"):
        environment = os.environ if env is None else env
        if key in environment:
            extra.add(Path(environment[key]))
    files = controller_read_inputs(owner, {}, extra=sorted(extra))
    if any(files[path.relative_to(owner).as_posix()] != hashed for path, hashed in declared.items()):
        raise ConformanceError("InputChanged")
    for path in mutable:
        files.pop(path.relative_to(owner).as_posix(), None)
    return files


def verify_controller_invocations(owner, summary, phase, run_id, root_id):
    import conformance_legacy as legacy
    from conformance_sources import read_bounded

    fields = {"qualification", "nativeContainment", "inputClosureComplete", "scope",
              "count", "sha256", "parentSha256", "sequence", "inputSnapshotsSha256"}
    if (phase not in ("historical", "controllers", "mutations", "reference", "architecture")
            or not isinstance(summary, dict) or set(summary) != fields
            or summary["qualification"] is not False or summary["nativeContainment"] is not True
            or summary["inputClosureComplete"] is not False or summary["scope"] != "borrowed-launch-observations"
            or type(summary["sequence"]) is not int or not 1 <= summary["sequence"] <= 10000
            or type(summary["count"]) is not int or not 1 <= summary["count"] <= 10000):
        raise ConformanceError("ProofMismatch")
    owner = Path(owner)
    legacy.no_symlinks(owner / "proofs")
    parent_raw = read_bounded(owner / f"proofs/execution-command-{summary['sequence']:04}.json", 65536)
    output_name = f"proofs/inherited-{phase}-result.json"
    output_raw = read_bounded(owner / output_name, 16 * 1024**2)
    parent, output = load_json(parent_raw), load_json(output_raw)
    if (not isinstance(parent, dict) or not isinstance(output, dict)
            or set(output) != {"schemaVersion", "qualification", "phase", "runId", "rootId", "result",
                               "invocations", "inputSnapshots"}
            or type(output["schemaVersion"]) is not int or output["schemaVersion"] != 3
            or output["qualification"] is not False or output["phase"] != phase
            or output["runId"] != run_id or output["rootId"] != root_id or not isinstance(output["result"], dict)
            or parent.get("runId") != run_id or parent.get("rootId") != root_id
            or type(parent.get("sequence")) is not int or parent["sequence"] != summary["sequence"]
            or parent.get("groupState") != "Exited" or type(parent.get("exitCode")) is not int or parent["exitCode"] != 0
            or parent.get("diagnosticCode") != "None"
            or parent.get("outputFiles") != {output_name: hashlib.sha256(output_raw).hexdigest()}
            or hashlib.sha256(parent_raw).hexdigest() != summary["parentSha256"]
            or not isinstance(output["invocations"], list)
            or len(output["invocations"]) != summary["count"] or digest(output["invocations"]) != summary["sha256"]
            or digest(output["inputSnapshots"]) != summary["inputSnapshotsSha256"]):
        raise ConformanceError("ProofMismatch")
    legacy.verify_borrowed_invocations(
        output["invocations"], group_pid=parent.get("childPid"), group_start_sha256=parent.get("childStartSha256"))
    legacy.verify_borrowed_input_snapshots(output["inputSnapshots"], len(output["invocations"]))
    if phase == "reference" and output["invocations"] != [output["result"].get("invocation")]:
        raise ConformanceError("ProofMismatch")


def controller_read_inputs(owner, manifests, *, extra=()):
    """Bind private fixture inputs; this is not a native controller I/O trace."""
    import conformance_legacy as legacy
    from conformance_evidence import file_sha256
    from conformance_sources import read_bounded

    owner = Path(owner).resolve(strict=True)
    files, size = {}, 0

    def bind(path):
        nonlocal size
        path = Path(path)
        legacy.no_symlinks(path)
        if not path.is_file() or not path.resolve(strict=True).is_relative_to(owner):
            raise ConformanceError("OwnershipInvalid")
        path = path.resolve(strict=True)
        relative = path.relative_to(owner).as_posix()
        if relative in files:
            return
        size += path.stat().st_size
        if len(files) >= 50000 or size > 256 * 1024**2:
            raise ConformanceError("OutputLimitExceeded")
        files[relative] = file_sha256(path)
        if path.name == "project.assets.json":
            assets = load_json(read_bounded(path, 16 * 1024**2))
            for identity, entry in assets["libraries"].items():
                if identity.startswith("Hoard.") and entry["type"] == "package":
                    for cache in assets["packageFolders"]:
                        for item in (Path(cache) / entry["path"]).rglob("*"):
                            if item.is_file():
                                bind(item)
        if path.suffix in (".csproj", ".slnx"):
            for directory in path.parents:
                if not directory.is_relative_to(owner):
                    break
                names = ["Directory.Build.props", "Directory.Build.targets", "Directory.Packages.props", "global.json"]
                if directory == path.parent and path.suffix == ".csproj":
                    names.extend(("packages.lock.json", "PackageAcceptance/packages.lock.json",
                                  "obj/F07.preparation.packages.lock.json",
                                  "obj/F07.preparation.acceptance.packages.lock.json",
                                  "obj/project.assets.json", f"obj/{path.name}.nuget.g.props",
                                  f"obj/{path.name}.nuget.g.targets"))
                for name in names:
                    context = directory / name
                    legacy.no_symlinks(context)
                    if context.exists():
                        bind(context)

    def collect(value):
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str) and value.startswith("/"):
            path = Path(value)
            # Manifests also contain route literals and SDK paths, not private fixture inputs.
            if not path.is_relative_to(owner):
                return
            legacy.no_symlinks(path)
            if not path.resolve().is_relative_to(owner):
                raise ConformanceError("OwnershipInvalid")
            if path.is_file():
                bind(path)
            elif path.is_dir():
                for item in path.rglob("*"):
                    if (item.is_file() and item.suffix in (".cs", ".csproj")
                            and not {"bin", "obj"}.intersection(item.relative_to(path).parts)):
                        bind(item)

    for path in (*manifests.values(), *extra):
        bind(path)
    for path in manifests.values():
        collect(load_json(read_bounded(Path(path), 16 * 1024**2)))
    return dict(sorted(files.items()))


class ControllerProgress(io.TextIOBase):
    """Translate only fixed controller progress into native safe events."""

    def __init__(self, stream):
        self.stream, self.pending = stream, ""

    def write(self, text):
        if len(self.pending) + len(text) > 4096:
            raise ConformanceError("OutputLimitExceeded")
        self.pending += text
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            try:
                value = load_json(line.encode("utf-8", errors="strict"))
                controllers = ("foundation", "lifecycle", "configuration", "discovery")
                if not isinstance(value, dict) or value.get("qualification") is not False:
                    raise ConformanceError("UnknownDiagnostic")
                if value.get("phase") == "inherited-discovery-mutation":
                    if (set(value) != {"qualification", "phase", "ordinal"}
                            or type(value["ordinal"]) is not int or not 1 <= value["ordinal"] <= 24):
                        raise ConformanceError("UnknownDiagnostic")
                    event = {"event": "control", "code": "None", "value": value["ordinal"]}
                elif value.get("phase") == "inherited-controller-failure":
                    if (set(value) != {"qualification", "phase", "controller", "commandSequence", "operation", "code"}
                            or value["controller"] not in (*controllers, "preparation")
                            or type(value["commandSequence"]) is not int
                            or not 1 <= value["commandSequence"] <= 65535
                            or value["operation"] not in ("restore", "build", "pack", "format", "test",
                                                          "--version", "control")
                            or value["code"] not in DIAGNOSTIC_CODES or value["code"] == "None"):
                        raise ConformanceError("UnknownDiagnostic")
                    event = {"event": "control", "code": value["code"], "value": value["commandSequence"]}
                else:
                    if (value.get("phase") not in (
                            "inherited-controller-preparation", "inherited-historical-preparation")
                            or set(value) != {"qualification", "phase", "controller"}
                            or value.get("controller") not in controllers):
                        raise ConformanceError("UnknownDiagnostic")
                    event = {"event": "control", "code": "None", "value": controllers.index(value["controller"]) + 1}
            except (ConformanceError, UnicodeError):
                raise ConformanceError("UnknownDiagnostic") from None
            self.stream.write(json.dumps(event) + "\n")
            self.stream.flush()
        return len(text)


def controller_child_main(argv=None):
    parser = argparse.ArgumentParser(description="Owned nonqualifying inherited controller child.")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    stream = sys.stdout
    authorized_output = False
    try:
        import conformance_legacy as legacy
        from conformance_evidence import relative_path, stable_id
        from conformance_sources import read_bounded

        request = load_json(read_bounded(args.request, 65536))
        fields = {
                "schemaVersion", "phase", "owner", "repository", "runId", "rootId", "source",
                "baselineSeal", "sdkPackage", "loggerPath"}
        if isinstance(request, dict) and request.get("phase") == "reference":
            fields.add("reference")
        if (not isinstance(request, dict) or set(request) != fields
                or type(request["schemaVersion"]) is not int or request["schemaVersion"] != 1
                or request["phase"] not in ("historical", "controllers", "mutations", "reference", "architecture")
                or not isinstance(request["runId"], str)
                or str(uuid.UUID(request["runId"])) != request["runId"]):
            raise ConformanceError("EvidenceSchemaInvalid")
        stable_id(request["rootId"])
        owner, repository = Path(request["owner"]), Path(request["repository"])
        for path in (owner, repository, args.request, args.output):
            legacy.no_symlinks(path)
            if not path.is_absolute():
                raise ConformanceError("OwnershipInvalid")
        if (args.request.parent != owner / "stores" or args.output.parent != owner / "proofs"
                or args.output.exists() or owner == repository or owner.is_relative_to(repository)):
            raise ConformanceError("OwnershipInvalid")
        header = load_json(read_bounded(owner / "ownership.json", 65536))
        preflight = load_json(read_bounded(owner / "proofs/preflight.json", 65536))
        if (header["schemaVersion"] != 2 or header["state"] != "Active"
                or header["runId"] != request["runId"] or header["rootId"] != request["rootId"]
                or preflight["schemaVersion"] != 1 or preflight["qualification"] is not False
                or preflight["profileId"] != ("compatibility" if request["phase"] == "architecture" else "composition")):
            raise ConformanceError("OwnershipInvalid")
        authorized_output = True
        run = SimpleNamespace(root=owner, run_id=request["runId"], root_id=request["rootId"], command_sequence=0)
        progress = ControllerProgress(stream)
        def read_inputs(arguments, **kwargs):
            return controller_command_read_inputs(owner, arguments, **kwargs)

        with legacy.native_preparation_group(
                header, input_owner=owner, input_reader=read_inputs) as observations, redirect_stdout(progress):
            if request["phase"] == "architecture":
                if any(request[key] is not None for key in ("baselineSeal", "sdkPackage", "loggerPath")):
                    raise ConformanceError("EvidenceSchemaInvalid")
                result = prepare_architecture_evidence(
                    repository, owner, owner / relative_path(request["source"]))
            elif request["phase"] == "historical":
                if any(request[key] is not None for key in ("baselineSeal", "sdkPackage", "loggerPath")):
                    raise ConformanceError("EvidenceSchemaInvalid")
                result = prepare_controller_baselines(repository, run)
            elif request["phase"] == "controllers":
                prepared = verify_controller_baselines(run, request["baselineSeal"])
                result = prepare_controller_evidence(
                    repository, owner, owner / relative_path(request["source"]),
                    sdk_package=owner / relative_path(request["sdkPackage"]),
                    logger_path=owner / relative_path(request["loggerPath"]), prepared_baselines=prepared)
                verify_controller_baselines(run, request["baselineSeal"])
            elif request["phase"] == "reference":
                if request["sdkPackage"] is not None or request["loggerPath"] is not None:
                    raise ConformanceError("EvidenceSchemaInvalid")
                verify_controller_baselines(run, request["baselineSeal"])
                result = replay_reference_consumer(owner, request["reference"])
                verify_controller_baselines(run, request["baselineSeal"])
            else:
                from conformance_evidence import admit_entity
                verify_controller_baselines(run, request["baselineSeal"])
                inputs = admit_entity("RunInputs", load_json(read_bounded(
                    owner / "proofs/composition-inputs.json", 2 * 1024**2)))
                if inputs["runId"] != run.run_id or inputs["profileId"] != "composition":
                    raise ConformanceError("ProofMismatch")
                result = run_discovery_mutations(
                    repository, owner, owner / relative_path(request["source"]),
                    inputs["sourceManifest"], inputs["environment"]["sdk"],
                    sdk_package=owner / relative_path(request["sdkPackage"]),
                    logger_path=owner / relative_path(request["loggerPath"]))
                verify_controller_baselines(run, request["baselineSeal"])
        if progress.pending:
            raise ConformanceError("UnknownDiagnostic")
        legacy._write(args.output, {
            "schemaVersion": 3, "qualification": False, "phase": request["phase"],
            "runId": run.run_id, "rootId": run.root_id, "result": result,
            "invocations": observations["invocations"], "inputSnapshots": observations["inputSnapshots"],
        })
        stream.write('{"event":"control","code":"None","value":0}\n')
        return 0
    except (ConformanceError, OSError, RuntimeError, ValueError, TypeError, KeyError) as error:
        code = str(error) if isinstance(error, ConformanceError) else "EvidenceIncomplete"
        sources = {str(Path(__file__).resolve().with_name(name)): index * 100000
                   for index, name in enumerate(CONTROLLER_ERROR_SOURCES, 1)}
        frame, location = error.__traceback__, None
        while frame is not None:
            if frame.tb_frame.f_code.co_filename in sources and 0 < frame.tb_lineno < 100000:
                location = sources[frame.tb_frame.f_code.co_filename] + frame.tb_lineno
            frame = frame.tb_next
        if authorized_output and location is not None:
            stream.write(json.dumps({"event": "control", "code": code, "value": location}) + "\n")
        if authorized_output and not args.output.exists():
            legacy._write(args.output, {
                "schemaVersion": 1, "qualification": False, "phase": request["phase"],
                "runId": request["runId"], "rootId": request["rootId"],
                "status": "Incomplete", "diagnosticCode": code,
            })
        stream.write(json.dumps({"event": "control", "code": code, "value": 0}) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(controller_child_main())
