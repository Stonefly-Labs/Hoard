"""Strict test-only F-07 evidence admission; no production certification."""

from collections.abc import Mapping
import hashlib
import json
import math
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import stat
import subprocess
import time
from types import MappingProxyType
import uuid


MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_RESULTS = 10_000
MAX_WITNESSES = 128
MAX_PROOF_FILES = 50_000
MAX_PROOF_BYTES = 256 * 1024 * 1024
CATALOG_REVISION = "f07-v1"
PROFILES = ("metadata", "artifacts", "composition", "compatibility", "harness")
STATUSES = ("Passed", "Failed", "NotApplicable", "Incomplete")
DIAGNOSTIC_CODES = (
    "None", "AssertionFailed", "EvidenceSchemaInvalid", "EvidenceIncomplete",
    "InputChanged", "WitnessMissing", "ProofMismatch", "BindingInvalid",
    "UnsupportedProfile", "PrerequisiteMissing", "InsufficientCapacity",
    "DeadlineExceeded", "OutputLimitExceeded", "UnknownDiagnostic",
    "CleanupIncomplete", "OwnershipInvalid", "CommandFailed",
)


class ConformanceError(ValueError):
    """A closed safe evidence error, without private input interpolation."""

    def __init__(self, code="EvidenceSchemaInvalid"):
        super().__init__(code if code in DIAGNOSTIC_CODES else "EvidenceSchemaInvalid")


def _invalid():
    raise ConformanceError()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _unicode(value, depth=0):
    if depth > 64:
        _invalid()
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
    elif isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                _invalid()
            _unicode(key, depth + 1)
            _unicode(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _unicode(child, depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        _invalid()


def load_json(data):
    try:
        if not isinstance(data, bytes) or len(data) > MAX_REPORT_BYTES:
            _invalid()
        result = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_constant=lambda _: _invalid())
        _unicode(result)
        return result
    except (UnicodeError, ValueError, RecursionError):
        raise ConformanceError() from None


def canonical_bytes(value):
    def plain(item):
        if isinstance(item, (dict, MappingProxyType)):
            return {key: plain(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [plain(child) for child in item]
        return item
    try:
        _unicode(plain(value))
        return json.dumps(plain(value), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise ConformanceError() from None


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def stable_id(value):
    if not isinstance(value, str) or re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}", value, re.ASCII) is None:
        _invalid()
    return value


def sha256(value):
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{64}", value, re.ASCII) is None:
        _invalid()
    return value


def _sha512(value):
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{128}", value, re.ASCII) is None:
        _invalid()
    return value


def relative_path(value):
    if (not isinstance(value, str) or not value or len(value) > 512
            or "\\" in value or ":" in value or "\x00" in value
            or any(ord(char) < 32 or ord(char) > 126 for char in value)):
        _invalid()
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        _invalid()
    return value


def _uuid(value):
    if not isinstance(value, str):
        _invalid()
    try:
        parsed = uuid.UUID(value)
        if parsed.int == 0 or str(parsed) != value:
            _invalid()
    except ValueError:
        raise ConformanceError() from None
    return value


def _number(value):
    if type(value) not in (int, float) or not 0 <= value <= 2**63 - 1 or not math.isfinite(value):
        _invalid()
    return value


def _integer(value):
    if type(value) is not int or value < 0 or value > 2**63 - 1:
        _invalid()
    return value


def _boolean(value):
    if type(value) is not bool:
        _invalid()
    return value


def _one_of(*values):
    def validate(value):
        if not isinstance(value, str) or value not in values:
            _invalid()
        return value
    return validate


def _constant(expected):
    def validate(value):
        if type(value) is not type(expected) or value != expected:
            _invalid()
        return value
    return validate


def _list(validate, limit, *, minimum=1, unique=False):
    def admit(value):
        if not isinstance(value, (tuple, list)) or not minimum <= len(value) <= limit:
            _invalid()
        admitted = tuple(validate(item) for item in value)
        if unique and len({canonical_bytes(item) for item in admitted}) != len(admitted):
            _invalid()
        return admitted
    return admit


def _hash_map(value):
    if not isinstance(value, (dict, MappingProxyType)) or not value or len(value) > MAX_PROOF_FILES:
        _invalid()
    return MappingProxyType({relative_path(key): sha256(child) for key, child in value.items()})


def _record(fields):
    def validate(value):
        if not isinstance(value, (dict, MappingProxyType)) or set(value) != set(fields):
            _invalid()
        return MappingProxyType({key: validator(value[key]) for key, validator in fields.items()})
    return validate


def _entity(kind):
    return lambda value: admit_entity(kind, value)


_ids = _list(stable_id, MAX_WITNESSES, unique=True)
_hashes = _list(sha256, MAX_WITNESSES, unique=True)
_optional_hashes = _list(sha256, MAX_WITNESSES, minimum=0, unique=True)
_executions = _list(_uuid, MAX_WITNESSES, minimum=0, unique=True)
_category = _one_of("metadata", "artifacts", "declaration-lifecycle", "harness", "compatibility")
_state = _one_of(*STATUSES)
_executed_state = _one_of("Passed", "Failed", "Incomplete")
_schemas = {
    "ContractCase": {
        "caseId": stable_id, "contractRevision": _constant(CATALOG_REVISION),
        "category": _category,
        "claimClass": _one_of("common-logical", "durable-local-process-crash", "object-simulation",
                             "declaration-lifecycle", "unqualified-service"),
        "requirementReferences": _ids, "expectedWitnessIds": _ids,
        "applicabilityRule": _one_of("mandatory", "metadata-durable", "artifact-durable"),
    },
    "QualificationProfile": {
        "profileId": _one_of(*PROFILES), "revision": _constant(CATALOG_REVISION),
        "caseExpansion": _list(_entity("ExpectedKey"), MAX_RESULTS),
        "bindingIds": _ids, "matrixIds": _list(stable_id, MAX_RESULTS, unique=True),
        "budgets": _entity("Budgets"), "prerequisites": _ids,
    },
    "ExpectedKey": {
        "profileId": _one_of(*PROFILES), "bindingId": stable_id,
        "matrixId": stable_id, "caseId": stable_id,
    },
    "PackageIdentity": {
        "packageId": stable_id, "version": stable_id, "sha256": sha256,
        "nugetSha512": _sha512, "sourceMapping": _constant("local"),
        "runtimeAssemblies": _hash_map,
    },
    "ProviderBinding": {
        "bindingId": stable_id, "package": _entity("PackageIdentity"),
        "category": _one_of("metadata", "artifacts"),
        "descriptorSha256": sha256, "capabilitySha256": sha256, "adapterId": stable_id,
    },
    "MatrixEntry": {
        "matrixId": stable_id, "packageIds": _ids, "hostVersion": stable_id,
        "abstractionsVersion": stable_id, "enabledIds": _ids,
        "expectedRule": stable_id, "expectedReadiness": _boolean,
        "expectedOwnership": _one_of("Released", "Retained"),
    },
    "CompatibilityBaseline": {
        "revision": lambda x: x if isinstance(x, str) and re.fullmatch("[0-9a-f]{40}", x) else _invalid(),
        "sourceSha256": sha256, "lockSha256": sha256, "recipeSha256": sha256,
        "binarySha256": sha256, "dependencySha256": _hash_map, "apiScope": stable_id,
    },
    "Budgets": {
        "operationSeconds": _integer, "barrierSeconds": _integer, "childSeconds": _integer,
        "transferSeconds": _integer, "recoverySeconds": _integer, "terminationSeconds": _integer,
        "cleanupSeconds": _integer, "profileSeconds": _integer, "baselineSeconds": _integer,
        "maxChildren": _integer, "maxTransferChildren": _integer,
    },
    "Environment": {
        "os": stable_id, "osVersion": stable_id, "architecture": stable_id,
        "sdk": stable_id, "runtime": stable_id, "nativeSqlite": stable_id,
        "filesystem": stable_id, "runnerImage": stable_id, "freeBytes": _integer,
        "pragmas": _record({"journalMode": _one_of("wal", "none"), "synchronous": _integer,
                            "foreignKeys": _integer, "busyTimeout": _integer}),
    },
    "RunInputs": {
        "schemaVersion": _constant(1), "runId": _uuid, "invocationGroupId": _uuid,
        "profileId": _one_of(*PROFILES), "mode": _one_of("qualification", "diagnostic", "preparation"),
        "catalogRevision": _constant(CATALOG_REVISION), "catalogSha256": sha256, "sdkSha256": sha256,
        "sourceRevision": lambda x: x if isinstance(x, str) and re.fullmatch("[0-9a-f]{40}", x) else _invalid(),
        "sourceState": _one_of("clean-ci", "clean-local", "dirty-local"),
        "sourceManifest": _hash_map, "sourceManifestSha256": sha256,
        "packages": _list(_entity("PackageIdentity"), 1024),
        "locks": _hash_map, "configurationSha256": sha256, "capabilitySha256": sha256,
        "bindings": _list(_entity("ProviderBinding"), 128, minimum=0),
        "baselines": _list(_entity("CompatibilityBaseline"), 6, minimum=0),
        "runtimeAssemblies": _hash_map,
        "environment": _entity("Environment"), "environmentSha256": sha256,
        "budgets": _entity("Budgets"), "invocation": _ids,
    },
    "ResourceOwnership": {
        "runId": _uuid, "rootId": stable_id, "childPid": _integer,
        "childStartSha256": sha256,
        "state": _one_of("Allocated", "Active", "Settling", "Released", "Retained"),
        "cleanupDurationMs": _number, "diagnosticCode": _one_of(*DIAGNOSTIC_CODES),
    },
    "Attempt": {
        "sequence": _integer, "startedMs": _number, "endedMs": _number, "status": _executed_state,
        "witnessIds": _executions, "proofSha256": _optional_hashes,
        "diagnosticCode": _one_of(*DIAGNOSTIC_CODES),
    },
    "CaseResult": {
        "runId": _uuid, "profileId": _one_of(*PROFILES), "bindingId": stable_id,
        "matrixId": stable_id, "caseId": stable_id, "status": _state,
        "applicable": _boolean,
        "exclusionRule": _one_of("none", "non-durable-fixture", "simulation-no-durable-restart"),
        "attempts": _list(_entity("Attempt"), 3, minimum=0), "proofSha256": _optional_hashes,
    },
    "RuntimeWitness": {
        "executionId": _uuid, "runId": _uuid, "invocationGroupId": _uuid,
        "testIdentity": lambda x: x if isinstance(x, str) and 0 < len(x.encode("utf-8")) <= 1024
        and all(32 <= ord(c) <= 126 for c in x) else _invalid(),
        "bindingId": stable_id, "matrixId": stable_id, "packageSha256": sha256,
        "assemblySha256": sha256, "inputSha256": sha256,
        "startedMs": _number, "endedMs": _number, "status": _executed_state, "proofSha256": sha256,
    },
    "QualificationReport": {
        "schemaVersion": _constant(1), "catalogRevision": _constant(CATALOG_REVISION),
        "inputs": _entity("RunInputs"), "postInputSha256": sha256,
        "results": _list(_entity("CaseResult"), MAX_RESULTS),
        "witnesses": _list(_entity("RuntimeWitness"), MAX_RESULTS * MAX_WITNESSES, minimum=0),
        "resources": _list(_entity("ResourceOwnership"), 1024, minimum=0),
        "proofs": _hash_map,
        "state": _one_of("Created", "Admitted", "Running", "Evaluating", "Complete", "Failed", "Incomplete"),
        "qualification": _boolean, "scope": _ids,
    },
    "SupportStatement": {
        "reportSha256": sha256, "profiles": _list(_one_of(*PROFILES), 5, unique=True),
        "bindingIds": _ids, "versions": _ids, "environmentSha256": _hashes,
        "exclusions": _list(stable_id, MAX_RESULTS, minimum=0, unique=True),
        "unsupportedScope": _ids,
    },
}


def admit_entity(kind, value):
    if not isinstance(kind, str) or kind not in _schemas:
        _invalid()
    result = _record(_schemas[kind])(value)
    if kind in ("Attempt", "RuntimeWitness"):
        if result["endedMs"] < result["startedMs"]:
            _invalid()
    if kind == "Attempt":
        if (not 1 <= result["sequence"] <= 3
                or (result["status"] == "Passed"
                    and (not result["witnessIds"] or not result["proofSha256"]
                         or result["diagnosticCode"] != "None"))
                or (result["status"] != "Passed" and result["diagnosticCode"] == "None")):
            _invalid()
    if kind == "CaseResult":
        if tuple(attempt["sequence"] for attempt in result["attempts"]) != tuple(range(1, len(result["attempts"]) + 1)):
            _invalid()
        if any(earlier["endedMs"] > later["startedMs"]
               for earlier, later in zip(result["attempts"], result["attempts"][1:])):
            _invalid()
        if result["applicable"] and (not result["attempts"] or result["status"] != result["attempts"][-1]["status"]):
            _invalid()
        if result["applicable"] != (result["exclusionRule"] == "none"):
            _invalid()
        if (result["status"] == "NotApplicable") == result["applicable"]:
            _invalid()
        if not result["applicable"] and (result["attempts"] or result["proofSha256"]):
            _invalid()
        if set(result["proofSha256"]) != {proof for attempt in result["attempts"] for proof in attempt["proofSha256"]}:
            _invalid()
    if kind == "Budgets":
        ceilings = {
            "operationSeconds": 5, "barrierSeconds": 15, "childSeconds": 600,
            "transferSeconds": 2400, "recoverySeconds": 300, "terminationSeconds": 10,
            "cleanupSeconds": 30, "profileSeconds": 10800, "baselineSeconds": 28800,
            "maxChildren": 4, "maxTransferChildren": 1,
        }
        if any(not 0 < result[key] <= limit for key, limit in ceilings.items()):
            _invalid()
    if kind == "QualificationProfile":
        keys = result["caseExpansion"]
        if (len({tuple(key.values()) for key in keys}) != len(keys)
                or any(key["profileId"] != result["profileId"] for key in keys)
                or {key["bindingId"] for key in keys} != set(result["bindingIds"])
                or {key["matrixId"] for key in keys} != set(result["matrixIds"])):
            _invalid()
    if kind == "RunInputs":
        _validate_input_links(result)
    if kind == "QualificationReport":
        _validate_report_links(result)
    return result


def _package_key(package):
    return package["sourceMapping"], package["packageId"].casefold(), package["version"].casefold()


def _validate_input_links(inputs):
    packages = {_package_key(package): package for package in inputs["packages"]}
    bindings = {binding["bindingId"]: binding for binding in inputs["bindings"]}
    baselines = {(baseline["revision"], baseline["apiScope"]) for baseline in inputs["baselines"]}
    if (inputs["sourceManifestSha256"] != digest(inputs["sourceManifest"])
            or inputs["environmentSha256"] != digest(inputs["environment"])
            or len(packages) != len(inputs["packages"])
            or len(bindings) != len(inputs["bindings"])
            or len(baselines) != len(inputs["baselines"])
            or any(packages.get(_package_key(binding["package"])) != binding["package"]
                   for binding in bindings.values())):
        _invalid()
    ceiling = {"metadata": 5400, "artifacts": 10800, "composition": 3600,
               "compatibility": 3600, "harness": 3600}[inputs["profileId"]]
    if inputs["budgets"]["profileSeconds"] > ceiling:
        _invalid()


def _validate_report_links(report):
    inputs = report["inputs"]
    input_sha = digest(inputs)
    executions = {witness["executionId"]: witness for witness in report["witnesses"]}
    packages = {package["sha256"] for package in inputs["packages"]}
    bindings = {binding["bindingId"]: binding for binding in inputs["bindings"]}
    assemblies = set(inputs["runtimeAssemblies"].values())
    assemblies.update(assembly for package in inputs["packages"] for assembly in package["runtimeAssemblies"].values())
    proofs = set(report["proofs"].values())
    result_keys = {(result["profileId"], result["bindingId"], result["matrixId"], result["caseId"])
                   for result in report["results"]}
    if len(result_keys) != len(report["results"]) or len(executions) != len(report["witnesses"]):
        _invalid()
    for witness in executions.values():
        binding = bindings.get(witness["bindingId"])
        if (witness["runId"] != inputs["runId"]
                or witness["invocationGroupId"] != inputs["invocationGroupId"]
                or witness["inputSha256"] != input_sha
                or witness["packageSha256"] not in packages
                or witness["assemblySha256"] not in assemblies
                or witness["proofSha256"] not in proofs
                or (witness["bindingId"] != "none"
                    and (binding is None or binding["package"]["sha256"] != witness["packageSha256"]))):
            _invalid()
    referenced = set()
    for result in report["results"]:
        if (result["runId"] != inputs["runId"] or result["profileId"] != inputs["profileId"]
                or not set(result["proofSha256"]).issubset(proofs)):
            _invalid()
        for attempt in result["attempts"]:
            for execution_id in attempt["witnessIds"]:
                witness = executions.get(execution_id)
                if (witness is None or witness["proofSha256"] not in attempt["proofSha256"]
                        or witness["bindingId"] != result["bindingId"] or witness["matrixId"] != result["matrixId"]
                        or witness["startedMs"] < attempt["startedMs"] or witness["endedMs"] > attempt["endedMs"]
                        or (attempt["status"] == "Passed" and witness["status"] != "Passed")):
                    _invalid()
                referenced.add(execution_id)
    if referenced != set(executions) or any(resource["runId"] != inputs["runId"] for resource in report["resources"]):
        _invalid()
    if report["qualification"] and (
            inputs["mode"] != "qualification" or report["state"] != "Complete"
            or report["postInputSha256"] != input_sha
            or any(result["status"] not in ("Passed", "NotApplicable") for result in report["results"])
            or any(attempt["status"] != "Passed" for result in report["results"] for attempt in result["attempts"])
            or any(resource["state"] != "Released" for resource in report["resources"])):
        _invalid()
    if len(canonical_bytes(report)) > MAX_REPORT_BYTES:
        _invalid()


def file_sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(64 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def source_manifest(root):
    from conformance_execution import capture_control
    root = Path(root).resolve()
    code, output = capture_control(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--",
         "src", "tests", "scripts", ".github/workflows", "global.json", "Hoard.slnx",
         "Directory.Build.props", "Directory.Build.targets", "Directory.Packages.props",
         "NuGet.Config", "nuget.config", ".editorconfig"], cwd=root,
    )
    if code:
        raise ConformanceError("InputChanged")
    paths = sorted(set(output.decode("utf-8", errors="strict").rstrip("\0").split("\0")))
    if not paths or len(paths) > MAX_PROOF_FILES:
        raise ConformanceError("InputChanged")
    manifest = {}
    total = 0
    for relative in paths:
        relative_path(relative)
        candidate = root / relative
        if {"bin", "obj", "__pycache__"}.intersection(PurePosixPath(relative).parts):
            raise ConformanceError("InputChanged")
        current = candidate
        while current != root:
            if current.is_symlink():
                raise ConformanceError("InputChanged")
            current = current.parent
        if not candidate.is_file():
            raise ConformanceError("InputChanged")
        total += candidate.stat().st_size
        if total > MAX_PROOF_BYTES:
            raise ConformanceError("InputChanged")
        manifest[relative] = file_sha256(candidate)
    return MappingProxyType(manifest)


def snapshot_sources(root, owned_run):
    root = Path(root).resolve()
    before = source_manifest(root)
    owned_run._check_ledger()
    snapshot = owned_run.root / "snapshot"
    snapshot.mkdir(mode=0o700)
    for relative, expected in before.items():
        destination = snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (root / relative).open("rb") as source, destination.open("xb") as target:
            while block := source.read(64 * 1024):
                target.write(block)
        if file_sha256(destination) != expected:
            raise ConformanceError("InputChanged")
        destination.chmod(0o400)
    if dict(source_manifest(root)) != dict(before):
        raise ConformanceError("InputChanged")
    return snapshot, before


def verify_snapshot(snapshot, manifest):
    snapshot = Path(snapshot)
    for relative, expected in manifest.items():
        relative_path(relative)
        candidate = snapshot / relative
        current = candidate
        while current != snapshot:
            if current.is_symlink():
                raise ConformanceError("InputChanged")
            current = current.parent
        if not candidate.is_file() or file_sha256(candidate) != expected:
            raise ConformanceError("InputChanged")
    files = {path.relative_to(snapshot).as_posix() for path in snapshot.rglob("*") if path.is_file()
             and not {"bin", "obj", "__pycache__"}.intersection(path.relative_to(snapshot).parts)}
    if files != set(manifest):
        raise ConformanceError("InputChanged")


def proof_manifest(directory):
    from conformance_execution import no_symlinks
    directory = Path(directory).absolute()
    files = {}
    total = 0
    entries_seen = 0
    deadline = time.monotonic() + 5

    def visit(descriptor, prefix="", depth=0):
        nonlocal total, entries_seen
        if depth > 32 or time.monotonic() >= deadline:
            raise ConformanceError("ProofMismatch")
        with os.scandir(descriptor) as entries:
            for entry in entries:
                entries_seen += 1
                if entries_seen > MAX_PROOF_FILES * 2 or time.monotonic() >= deadline:
                    raise ConformanceError("ProofMismatch")
                relative = relative_path(prefix + entry.name)
                before = os.stat(entry.name, dir_fd=descriptor, follow_symlinks=False)
                if stat.S_ISDIR(before.st_mode):
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                    try:
                        opened = os.fstat(child)
                        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                            raise ConformanceError("ProofMismatch")
                        visit(child, relative + "/", depth + 1)
                    finally:
                        os.close(child)
                elif stat.S_ISREG(before.st_mode):
                    if len(files) >= MAX_PROOF_FILES or total + before.st_size > MAX_PROOF_BYTES:
                        raise ConformanceError("ProofMismatch")
                    child = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
                    with os.fdopen(child, "rb") as source:
                        opened = os.fstat(source.fileno())
                        if (not stat.S_ISREG(opened.st_mode)
                                or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)):
                            raise ConformanceError("ProofMismatch")
                        hashed = hashlib.sha256()
                        observed = 0
                        while block := source.read(64 * 1024):
                            observed += len(block)
                            if total + observed > MAX_PROOF_BYTES or time.monotonic() >= deadline:
                                raise ConformanceError("ProofMismatch")
                            hashed.update(block)
                        if observed != before.st_size:
                            raise ConformanceError("ProofMismatch")
                        files[relative] = hashed.hexdigest()
                        total += observed
                else:
                    raise ConformanceError("ProofMismatch")
                after = os.stat(entry.name, dir_fd=descriptor, follow_symlinks=False)
                if ((after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns)
                        != (before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns)):
                    raise ConformanceError("ProofMismatch")
    try:
        no_symlinks(directory)
        root = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            original = os.fstat(root)
            visit(root)
            no_symlinks(directory)
            final = directory.stat()
            if (final.st_dev, final.st_ino) != (original.st_dev, original.st_ino):
                raise ConformanceError("ProofMismatch")
        finally:
            os.close(root)
    except (OSError, ConformanceError):
        raise ConformanceError("ProofMismatch") from None
    if not files:
        raise ConformanceError("ProofMismatch")
    return MappingProxyType(files)


def ingest_witnesses(data, *, run_id, invocation_group_id, input_sha256,
                     package_sha256, assembly_sha256, expected_tests):
    if (not isinstance(expected_tests, Mapping) or not expected_tests
            or len(expected_tests) > MAX_RESULTS * MAX_WITNESSES):
        raise ConformanceError("EvidenceIncomplete")
    expected_tests = dict(expected_tests)
    for identity, dimensions in expected_tests.items():
        if (not isinstance(identity, str) or not identity or len(identity) > 2048
                or not isinstance(dimensions, tuple) or len(dimensions) != 2):
            raise ConformanceError("EvidenceIncomplete")
        for dimension in dimensions:
            stable_id(dimension)
    value = load_json(data)
    if not isinstance(value, list) or len(value) > MAX_RESULTS * MAX_WITNESSES:
        raise ConformanceError("EvidenceIncomplete")
    witnesses = tuple(admit_entity("RuntimeWitness", item) for item in value)
    identities = [item["testIdentity"] for item in witnesses]
    if (len(set(identities)) != len(identities) or set(identities) != set(expected_tests)
            or len({item["executionId"] for item in witnesses}) != len(witnesses)):
        raise ConformanceError("WitnessMissing")
    for witness in witnesses:
        if (witness["runId"] != run_id or witness["invocationGroupId"] != invocation_group_id
                or witness["inputSha256"] != input_sha256 or witness["packageSha256"] != package_sha256
                or witness["assemblySha256"] != assembly_sha256 or witness["status"] != "Passed"):
            raise ConformanceError("ProofMismatch")
        if (witness["bindingId"], witness["matrixId"]) != expected_tests[witness["testIdentity"]]:
            raise ConformanceError("ProofMismatch")
    return witnesses


def _runtime_identity(value):
    if (not isinstance(value, str) or not 0 < len(value) <= 1024
            or re.fullmatch(r'[a-zA-Z0-9_.():, "+-]+', value, re.ASCII) is None):
        _invalid()
    return value


def _assertion_symbol(value):
    if value is None:
        return None
    if (not isinstance(value, str) or len(value) > 256
            or re.fullmatch(r"Hoard\.Testing\.Conformance\.[a-zA-Z0-9_.]+", value, re.ASCII) is None):
        _invalid()
    return value


def _runtime_json(data, fields, *, limit=2 * 1024 * 1024):
    if not isinstance(data, bytes) or not 0 < len(data) <= limit:
        raise ConformanceError("OutputLimitExceeded")
    return _record(fields)(load_json(data))


def ingest_runtime_attempt(*, inputs, manifest_data, owner_data, witnesses_data, proofs,
                           completion_data, expected_tests, manifest_sha256, owner_sha256,
                           started_ms, ended_ms):
    """Validate actual safe-logger records; a valid failed attempt remains failed."""
    inputs = admit_entity("RunInputs", inputs)
    input_sha = digest(inputs)
    _number(started_ms)
    _number(ended_ms)
    if ended_ms < started_ms:
        _invalid()
    sha256(manifest_sha256)
    sha256(owner_sha256)
    file_fields = {"id": stable_id, "path": relative_path, "sha256": sha256}
    expected_fields = {
        "testIdentity": _runtime_identity, "fullyQualifiedName": _runtime_identity,
        "assemblyId": stable_id, "packageId": stable_id, "bindingId": stable_id,
        "matrixId": stable_id, "assertionSymbol": _assertion_symbol,
    }
    owner = _runtime_json(owner_data, {
        "schemaVersion": _constant(1), "runId": _uuid, "invocationGroupId": _uuid,
        "rootId": stable_id, "rootPathSha256": sha256,
    })
    manifest = _runtime_json(manifest_data, {
        "schemaVersion": _constant(1), "runId": _uuid, "invocationGroupId": _uuid,
        "attemptId": _uuid, "attemptSequence": _integer, "inputSha256": sha256,
        "runInputsPath": relative_path,
        "assemblies": _list(_record(file_fields), 128),
        "packages": _list(_record(file_fields), 128),
        "expected": _list(_record(expected_fields), MAX_RESULTS),
    })
    if (hashlib.sha256(manifest_data).hexdigest() != manifest_sha256
            or hashlib.sha256(owner_data).hexdigest() != owner_sha256
            or owner["runId"] != inputs["runId"] or manifest["runId"] != inputs["runId"]
            or owner["invocationGroupId"] != inputs["invocationGroupId"]
            or manifest["invocationGroupId"] != inputs["invocationGroupId"]
            or manifest["inputSha256"] != input_sha
            or not 1 <= manifest["attemptSequence"] <= 3):
        raise ConformanceError("InputChanged")
    if (not isinstance(expected_tests, Mapping) or not 0 < len(expected_tests) <= MAX_RESULTS
            or any(not isinstance(dimensions, tuple) or len(dimensions) != 2
                   for dimensions in expected_tests.values())):
        raise ConformanceError("EvidenceIncomplete")
    expected_tests = {_runtime_identity(identity): tuple(stable_id(part) for part in dimensions)
                      for identity, dimensions in expected_tests.items()}
    expected = {entry["testIdentity"]: entry for entry in manifest["expected"]}
    files = (*manifest["assemblies"], *manifest["packages"])
    if (len({item["id"] for item in files}) != len(files)
            or len({item["path"] for item in files} | {manifest["runInputsPath"]}) != len(files) + 1
            or len(expected) != len(manifest["expected"])
            or {identity: (item["bindingId"], item["matrixId"]) for identity, item in expected.items()}
            != expected_tests):
        raise ConformanceError("ProofMismatch")
    assemblies = {item["id"]: item for item in manifest["assemblies"]}
    packages = {item["id"]: item for item in manifest["packages"]}
    admitted_packages = {(item["packageId"], item["sha256"]) for item in inputs["packages"]}
    if (any(inputs["runtimeAssemblies"].get(item["path"]) != item["sha256"]
            for item in assemblies.values())
            or any((item["id"], item["sha256"]) not in admitted_packages
                   for item in packages.values())):
        raise ConformanceError("ProofMismatch")
    for entry in expected.values():
        name = entry["fullyQualifiedName"]
        suffix = entry["testIdentity"][len(name):]
        parameter = r'(?:\"[a-zA-Z0-9._:+-]{0,128}\"|[-+]?[0-9]+(?:\.[0-9]+)?|True|False|null)'
        if (re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_.+]*", name, re.ASCII) is None
                or not entry["testIdentity"].startswith(name)
                or (suffix and re.fullmatch(
                    rf"\([a-zA-Z_][a-zA-Z0-9_]*: {parameter}(?:, [a-zA-Z_][a-zA-Z0-9_]*: {parameter})*\)",
                    suffix, re.ASCII) is None)
                or entry["assemblyId"] not in assemblies or entry["packageId"] not in packages):
            raise ConformanceError("WitnessMissing")
    if (not isinstance(witnesses_data, bytes) or not isinstance(completion_data, bytes)
            or len(witnesses_data) > 8 * 1024 * 1024
            or not isinstance(proofs, Mapping) or len(proofs) > MAX_RESULTS
            or any(not isinstance(data, bytes) for data in proofs.values())
            or sum(map(len, proofs.values())) + len(witnesses_data) + len(completion_data) > 8 * 1024 * 1024):
        raise ConformanceError("OutputLimitExceeded")
    if witnesses_data and not witnesses_data.endswith(b"\n"):
        raise ConformanceError("EvidenceIncomplete")
    lines = witnesses_data.splitlines()
    if len(lines) > MAX_RESULTS or any(not line or len(line) > 64 * 1024 for line in lines):
        raise ConformanceError("EvidenceIncomplete")
    witnesses = tuple(admit_entity("RuntimeWitness", load_json(line)) for line in lines)
    if (len({item["executionId"] for item in witnesses}) != len(witnesses)
            or len({item["testIdentity"] for item in witnesses}) != len(witnesses)
            or set(proofs) != {f'proof-{item["executionId"]}.json' for item in witnesses}):
        raise ConformanceError("ProofMismatch")
    proof_fields = {
        "schemaVersion": _constant(1), "executionId": _uuid, "runId": _uuid,
        "invocationGroupId": _uuid, "attemptId": _uuid, "attemptSequence": _integer,
        "testIdentity": _runtime_identity, "bindingId": stable_id, "matrixId": stable_id,
        "inputSha256": sha256, "manifestSha256": sha256, "ownerSha256": sha256,
        "assemblySha256": sha256, "packageSha256": sha256,
        "clock": _constant("system-monotonic-ms"), "durationMs": _number,
        "failureKind": _one_of("None", "Assertion", "Unknown", "SkippedOrUnknown"),
        "assertionSymbol": _assertion_symbol, "status": _executed_state,
    }
    proof_hashes = {}
    unknown_failure = False
    for witness in witnesses:
        entry = expected.get(witness["testIdentity"])
        if entry is None:
            raise ConformanceError("WitnessMissing")
        path = f'proof-{witness["executionId"]}.json'
        proof_data = proofs[path]
        proof = _runtime_json(proof_data, proof_fields, limit=64 * 1024)
        proof_hashes[path] = hashlib.sha256(proof_data).hexdigest()
        if (proof_hashes[path] != witness["proofSha256"]
                or any(proof[key] != witness[key] for key in (
                    "executionId", "runId", "invocationGroupId", "testIdentity", "bindingId", "matrixId",
                    "inputSha256", "assemblySha256", "packageSha256", "status"))
                or proof["runId"] != inputs["runId"]
                or proof["invocationGroupId"] != inputs["invocationGroupId"]
                or proof["inputSha256"] != input_sha or proof["manifestSha256"] != manifest_sha256
                or proof["ownerSha256"] != owner_sha256
                or proof["attemptId"] != manifest["attemptId"]
                or proof["attemptSequence"] != manifest["attemptSequence"]
                or (witness["bindingId"], witness["matrixId"]) != expected_tests[witness["testIdentity"]]
                or witness["packageSha256"] != packages[entry["packageId"]]["sha256"]
                or witness["assemblySha256"] != assemblies[entry["assemblyId"]]["sha256"]
                or witness["startedMs"] < started_ms - 0.001 or witness["endedMs"] > ended_ms + 0.001
                or proof["durationMs"] > 8 * 60 * 60 * 1000
                or abs(proof["durationMs"] - (witness["endedMs"] - witness["startedMs"])) > 0.001):
            raise ConformanceError("ProofMismatch")
        if ((witness["status"] == "Passed" and (proof["failureKind"] != "None" or proof["assertionSymbol"] is not None))
                or (witness["status"] == "Incomplete"
                    and (proof["failureKind"] != "SkippedOrUnknown" or proof["assertionSymbol"] is not None))
                or (witness["status"] == "Failed" and (
                    proof["failureKind"] not in ("Assertion", "Unknown")
                    or (proof["failureKind"] == "Assertion" and (
                        entry["assertionSymbol"] is None or proof["assertionSymbol"] != entry["assertionSymbol"]))
                    or (proof["failureKind"] == "Unknown" and proof["assertionSymbol"] is not None)))):
            raise ConformanceError("ProofMismatch")
        unknown_failure |= proof["failureKind"] == "Unknown"
    completion = _runtime_json(completion_data, {
        "schemaVersion": _constant(1), "runId": _uuid, "invocationGroupId": _uuid,
        "attemptId": _uuid, "attemptSequence": _integer, "manifestSha256": sha256,
        "inputSha256": sha256, "diagnosticCode": _one_of(*DIAGNOSTIC_CODES),
        "observedCount": _integer, "expectedCount": _integer, "complete": _boolean,
    }, limit=64 * 1024)
    code = completion["diagnosticCode"]
    inventory_complete = {item["testIdentity"] for item in witnesses} == set(expected)
    failed = any(item["status"] == "Failed" for item in witnesses)
    if (any(completion[key] != manifest[key] for key in (
            "runId", "invocationGroupId", "attemptId", "attemptSequence", "inputSha256"))
            or completion["manifestSha256"] != manifest_sha256
            or completion["expectedCount"] != len(expected)
            or not len(witnesses) <= completion["observedCount"] <= MAX_RESULTS + 1
            or completion["complete"] != (inventory_complete and code in ("None", "AssertionFailed"))
            or (completion["complete"] and completion["observedCount"] != len(witnesses))
            or (code == "None" and (not inventory_complete or any(item["status"] != "Passed" for item in witnesses)))
            or (code == "AssertionFailed" and (not inventory_complete or not failed or unknown_failure
                or any(item["status"] == "Incomplete" for item in witnesses)))):
        raise ConformanceError("EvidenceIncomplete")
    return MappingProxyType({
        "witnesses": witnesses, "proofs": MappingProxyType(proof_hashes), "completion": completion,
        "attemptId": manifest["attemptId"], "diagnosticCode": code,
    })
