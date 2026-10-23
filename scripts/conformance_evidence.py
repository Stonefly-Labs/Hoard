"""Strict test-only F-07 evidence admission; no production certification."""

import hashlib
import json
import math
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import subprocess
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
    except (UnicodeError, json.JSONDecodeError, RecursionError):
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
        if str(uuid.UUID(value)) != value:
            _invalid()
    except ValueError:
        raise ConformanceError() from None
    return value


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
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
    if not isinstance(value, dict) or not value or len(value) > MAX_PROOF_FILES:
        _invalid()
    return MappingProxyType({relative_path(key): sha256(child) for key, child in value.items()})


def _record(fields):
    def validate(value):
        if not isinstance(value, dict) or set(value) != set(fields):
            _invalid()
        return MappingProxyType({key: validator(value[key]) for key, validator in fields.items()})
    return validate


def _entity(kind):
    return lambda value: admit_entity(kind, value)


_ids = _list(stable_id, MAX_WITNESSES, unique=True)
_hashes = _list(sha256, MAX_WITNESSES, unique=True)
_category = _one_of("metadata", "artifacts", "declaration-lifecycle", "harness", "compatibility")
_state = _one_of(*STATUSES)
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
        "bindingId": stable_id, "package": _entity("PackageIdentity"), "category": _category,
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
        "sequence": _integer, "startedMs": _number, "endedMs": _number, "status": _state,
        "witnessIds": _ids, "proofSha256": _hashes, "diagnosticCode": _one_of(*DIAGNOSTIC_CODES),
    },
    "CaseResult": {
        "runId": _uuid, "profileId": _one_of(*PROFILES), "bindingId": stable_id,
        "matrixId": stable_id, "caseId": stable_id, "status": _state,
        "applicable": _boolean,
        "exclusionRule": _one_of("none", "non-durable-fixture", "simulation-no-durable-restart"),
        "attempts": _list(_entity("Attempt"), 3), "proofSha256": _hashes,
    },
    "RuntimeWitness": {
        "executionId": _uuid, "runId": _uuid, "invocationGroupId": _uuid,
        "testIdentity": lambda x: x if isinstance(x, str) and 0 < len(x.encode("utf-8")) <= 1024
        and all(32 <= ord(c) <= 126 for c in x) else _invalid(),
        "bindingId": stable_id, "matrixId": stable_id, "packageSha256": sha256,
        "assemblySha256": sha256, "inputSha256": sha256,
        "startedMs": _number, "endedMs": _number, "status": _state, "proofSha256": sha256,
    },
    "QualificationReport": {
        "schemaVersion": _constant(1), "catalogRevision": _constant(CATALOG_REVISION),
        "inputs": _entity("RunInputs"), "postInputSha256": sha256,
        "results": _list(_entity("CaseResult"), MAX_RESULTS),
        "witnesses": _list(_entity("RuntimeWitness"), MAX_RESULTS * MAX_WITNESSES),
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
    if kind not in _schemas:
        _invalid()
    result = _record(_schemas[kind])(value)
    if kind in ("Attempt", "RuntimeWitness"):
        if result["endedMs"] < result["startedMs"]:
            _invalid()
    if kind == "Attempt" and not 1 <= result["sequence"] <= 3:
        _invalid()
    if kind == "CaseResult":
        if tuple(attempt["sequence"] for attempt in result["attempts"]) != tuple(range(1, len(result["attempts"]) + 1)):
            _invalid()
        if result["status"] != result["attempts"][-1]["status"]:
            _invalid()
        if result["applicable"] != (result["exclusionRule"] == "none"):
            _invalid()
        if (result["status"] == "NotApplicable") == result["applicable"]:
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
    return result


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
    directory = Path(directory).resolve()
    files = {}
    total = 0
    for candidate in sorted(directory.rglob("*")):
        if candidate.is_symlink():
            raise ConformanceError("ProofMismatch")
        if candidate.is_file():
            total += candidate.stat().st_size
            if len(files) >= MAX_PROOF_FILES or total > MAX_PROOF_BYTES:
                raise ConformanceError("ProofMismatch")
            relative = relative_path(candidate.relative_to(directory).as_posix())
            files[relative] = file_sha256(candidate)
    if not files:
        raise ConformanceError("ProofMismatch")
    return MappingProxyType(files)


def ingest_witnesses(data, *, run_id, invocation_group_id, input_sha256,
                     package_sha256, assembly_sha256, expected_tests):
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
    return witnesses
