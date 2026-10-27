"""Exact source-owned inherited composition inventories and opaque discovery admission."""

from collections import Counter
from contextlib import contextmanager
import os
from pathlib import Path
import re
from types import SimpleNamespace
import xml.etree.ElementTree as ET

from conformance_evidence import ConformanceError, digest, load_json

INVENTORY_PATH = "tests/fixtures/conformance/baselines/composition-inventory.json"
BASELINE = "9389016c0285c79f6f515f59805a5a41c69b0767"
INVENTORY_SHA256 = "9b45196787d57b0437c14e73345b1a0ba4b1544a41d95f7fca3ea32b7635de50"
GROUPS = frozenset(("lifecycle", "configuration", "discovery"))
ASSEMBLIES = frozenset(("Hoard.Composition.Tests", "Hoard.Architecture.Tests"))


@contextmanager
def controller_transport(repository, owner):
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
    original_processes, original_selectors = configuration.subprocess, configuration.selectors
    environment = {key: value for key, value in os.environ.items()
                   if key.startswith("HOARD_") or key == "NUGET_PACKAGES"}
    preparations = {}
    state = {"lockDerivations": [], "inputFiles": {}}

    def command(*arguments, cwd=None, env=None, expected=None, input=None):
        arguments = list(arguments)
        effective = dict(env or {})
        bound = {}
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
            return legacy.composition_controller_command(
                arguments, cwd=repository if arguments[0] == "git" else cwd,
                env=effective, expected=expected, input=input)
        finally:
            if any(legacy._hash(path) != hashed for path, hashed in bound.items()):
                raise ConformanceError("InputChanged")

    def text_command(*arguments, **kwargs):
        return command(*arguments, **kwargs).stdout

    def graph(projects, ownership, *, resolve=None):
        return original_graph(projects, ownership, resolve=resolve or legacy.resolve_project)

    try:
        foundation.run = command
        foundation.inspection_graph = graph
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
        for module, original in originals.items():
            module.run = original
        for key in list(os.environ):
            if key.startswith("HOARD_") or key == "NUGET_PACKAGES":
                del os.environ[key]
        os.environ.update(environment)


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
                or re.fullmatch(r"[0-9a-f]{64}", hashed) is None or sources.get(path) != hashed):
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
    if assembly not in ASSEMBLIES:
        raise ConformanceError("WitnessMissing")
    expected = {name: entry for name, entry in methods.items() if name.startswith(assembly + ".")}
    rows = load_json(data)
    if not expected or not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
        raise ConformanceError("WitnessMissing")
    seen = set()
    counts = Counter()
    admitted = []
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"testIdentity", "fullyQualifiedName"}
                or not isinstance(row["fullyQualifiedName"], str) or row["fullyQualifiedName"] not in expected
                or not isinstance(row["testIdentity"], str)
                or re.fullmatch(re.escape(row["fullyQualifiedName"])
                                + r'\(testCaseSha256: "[0-9a-f]{64}"\)', row["testIdentity"]) is None
                or row["testIdentity"] in seen):
            raise ConformanceError("WitnessMissing")
        seen.add(row["testIdentity"])
        counts[row["fullyQualifiedName"]] += 1
        entry = expected[row["fullyQualifiedName"]]
        admitted.append({
            **row, "assemblyId": "test-assembly", "packageId": "Hoard.Testing.Conformance",
            "bindingId": "none", "matrixId": "inherited." + entry["group"],
            "caseId": "inherited-" + entry["group"], "assertionSymbol": None,
        })
    if dict(counts) != {name: entry["parameterCount"] for name, entry in expected.items()}:
        raise ConformanceError("WitnessMissing")
    return sorted(admitted, key=lambda row: row["testIdentity"])
