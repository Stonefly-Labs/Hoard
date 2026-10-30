"""Strict test-only F-07 evidence admission; no production certification."""

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import argparse
import hashlib
import io
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
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile
import zlib


MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_RESULTS = 10_000
MAX_WITNESSES = 128
MAX_PROOF_FILES = 50_000
MAX_PROOF_BYTES = 256 * 1024 * 1024
MAX_PACKAGE_BYTES = 64 * 1024 * 1024
MAX_PACKAGE_EXPANDED_BYTES = 128 * 1024 * 1024
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
        self._proof_read: "_ProofReadObservation | None" = None


def failure_status(code):
    if code not in DIAGNOSTIC_CODES or code == "None":
        raise ConformanceError()
    return "Incomplete" if code in (
        "EvidenceIncomplete", "UnsupportedProfile", "PrerequisiteMissing", "InsufficientCapacity",
        "DeadlineExceeded", "OutputLimitExceeded", "UnknownDiagnostic", "CleanupIncomplete",
        "OwnershipInvalid", "CommandFailed",
    ) else "Failed"


@dataclass(frozen=True)
class ConformanceInvocation:
    action: str
    repository: Path
    mode: str
    profiles: tuple[str, ...] = ()
    case_keys: tuple[tuple[str, str, str, str], ...] = ()
    evidence: Path | None = None
    binding_project: Path | None = None
    input_path: Path | None = None
    binding_inputs_sha256: str | None = None
    coordinator_path: Path | None = None


class _Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise ConformanceError()


def invocation_parser():
    parser = _Arguments(
        description="Conformance admission and native metadata/artifact/composition execution. "
                    "Reports remain non-qualifying; independent evaluation, full controller acceptance, "
                    "focused/custom bindings, compatibility/harness and qualifying verify/aggregate remain incomplete. "
                    "Offline --verify/--aggregate with --coordinator inspect correspondence only.",
        add_help=False, allow_abbrev=False)
    parser.add_argument("--profile", metavar="PROFILE",
                        help="baseline (default), metadata, artifacts, composition, compatibility, harness")
    parser.add_argument("--evidence", type=Path, metavar="FRESH_PRIVATE_PATH")
    parser.add_argument("--binding-project", type=Path, metavar="PROJECT")
    parser.add_argument("--filter", metavar="EXACT_CATALOG_CASE_ID")
    parser.add_argument("--update-locks", action="store_true", help="non-qualifying preparation")
    parser.add_argument("--verify", type=Path, metavar="PUBLIC_REPORT")
    parser.add_argument("--aggregate", type=Path, metavar="REPORT_DIRECTORY")
    parser.add_argument("--coordinator", type=Path, metavar="TRUSTED_MANIFEST",
                        help="separate trusted input/report/configuration assignments for offline inspection")
    parser.add_argument("--help", action="store_true")
    return parser


def _invocation_path(path):
    from conformance_execution import no_symlinks
    path = path.absolute()
    if ".." in path.parts:
        raise ConformanceError("OwnershipInvalid")
    no_symlinks(path)
    return path


def admit_invocation(repository, arguments):
    from conformance_case_catalog import expected_cases
    if (not isinstance(arguments, (list, tuple)) or len(arguments) > 32
            or any(not isinstance(value, str) or len(value) > 8192 for value in arguments)):
        raise ConformanceError()
    seen = set()
    for argument in arguments:
        option = argument.partition("=")[0]
        if argument.startswith("--"):
            if option in seen:
                raise ConformanceError()
            seen.add(option)
    options = invocation_parser().parse_args(arguments)
    repository = Path(repository).resolve()
    if options.help:
        if len(arguments) != 1:
            raise ConformanceError()
        return ConformanceInvocation("help", repository, "diagnostic")
    offline = options.verify is not None or options.aggregate is not None
    if sum((options.verify is not None, options.aggregate is not None, options.update_locks)) > 1:
        raise ConformanceError()
    if offline:
        if any(value is not None for value in (
                options.profile, options.evidence, options.binding_project, options.filter)):
            raise ConformanceError()
        action = "verify" if options.verify is not None else "aggregate"
        path = _invocation_path(options.verify if action == "verify" else options.aggregate)
        if action == "verify":
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_REPORT_BYTES:
                raise ConformanceError()
        elif not path.is_dir():
            raise ConformanceError("PrerequisiteMissing")
        coordinator = None
        if options.coordinator is not None:
            coordinator = _invocation_path(options.coordinator)
            info = coordinator.stat()
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_REPORT_BYTES:
                raise ConformanceError()
        return ConformanceInvocation(action, repository, "diagnostic", input_path=path,
                                     coordinator_path=coordinator)
    if options.coordinator is not None:
        raise ConformanceError()
    profile = options.profile if options.profile is not None else "baseline"
    if profile not in ("baseline", *PROFILES):
        raise ConformanceError("UnsupportedProfile")
    if options.update_locks and any(value is not None for value in (
            options.profile, options.binding_project, options.filter)):
        raise ConformanceError()
    if options.evidence is None:
        raise ConformanceError()
    destination = _invocation_path(options.evidence)
    if (destination.exists() or not destination.parent.is_dir()
            or destination.is_relative_to(repository)):
        raise ConformanceError("OwnershipInvalid")
    info = destination.parent.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ConformanceError("OwnershipInvalid")
    if options.update_locks:
        return ConformanceInvocation("preparation", repository, "preparation", evidence=destination)
    project, binding_inputs_sha256 = None, None
    if options.binding_project is not None:
        if profile not in ("metadata", "artifacts"):
            raise ConformanceError()
        project = _invocation_path(options.binding_project)
        if project.suffix != ".csproj" or not project.is_file():
            raise ConformanceError("BindingInvalid")
        from conformance_contributors import admit_binding_project
        binding_inputs_sha256 = admit_binding_project(project, profile).inputs_sha256
    profiles = PROFILES if profile == "baseline" else (profile,)
    cases = tuple(case for selected in profiles for case in expected_cases(selected))
    mode = "qualification"
    if options.filter is not None:
        case_id = stable_id(options.filter)
        cases = tuple(case for case in cases if case.case_id == case_id)
        if not cases:
            raise ConformanceError("WitnessMissing")
        profiles = tuple(selected for selected in profiles
                         if any(case.profile_id == selected for case in cases))
        mode = "diagnostic"
    return ConformanceInvocation("run", repository, mode, profiles,
                                 tuple(case.key for case in cases), destination, project,
                                 binding_inputs_sha256=binding_inputs_sha256)


def dispatch_invocation(invocation):
    if invocation.action == "help":
        invocation_parser().print_help()
        return 0
    if invocation.action == "preparation":
        from conformance_prepare import execute
        return execute(invocation.repository, invocation.evidence)
    if (invocation.action == "run" and invocation.profiles in (("metadata",), ("artifacts",))
            and invocation.mode == "qualification" and invocation.binding_project is not None):
        from conformance_case_catalog import expected_cases
        from conformance_contributors import execute
        profile = invocation.profiles[0]
        if invocation.case_keys != tuple(case.key for case in expected_cases(profile)):
            raise ConformanceError("WitnessMissing")
        result = execute(
            invocation.repository, invocation.evidence, project=invocation.binding_project,
            category=profile, binding_inputs_sha256=invocation.binding_inputs_sha256)
        if type(result) is not int or result != 0:
            raise ConformanceError("CommandFailed")
        raise ConformanceError("EvidenceIncomplete")
    if (invocation.action == "run" and invocation.profiles in (
            ("metadata",), ("artifacts",), ("composition",), ("compatibility",))
            and invocation.mode == "qualification" and invocation.binding_project is None):
        from conformance_case_catalog import expected_cases
        profile = invocation.profiles[0]
        if invocation.case_keys != tuple(case.key for case in expected_cases(profile)):
            raise ConformanceError("WitnessMissing")
        if profile == "composition":
            from conformance_composition_checks import execute
            try:
                result = execute(invocation.repository, invocation.evidence)
            except RuntimeError:
                raise ConformanceError("EvidenceIncomplete") from None
        elif profile == "compatibility":
            from conformance_sdk_checks import execute
            try:
                result = execute(invocation.repository, invocation.evidence, compatibility_only=True)
            except RuntimeError:
                raise ConformanceError("EvidenceIncomplete") from None
        else:
            from conformance_sdk_checks import execute
            result = execute(invocation.repository, invocation.evidence, category=profile)
        if type(result) is not int or result != 0:
            raise ConformanceError("CommandFailed")
        # Native history admission is not the independent qualification evaluator.
        raise ConformanceError("EvidenceIncomplete")
    if invocation.action in ("verify", "aggregate"):
        from conformance_ci import inspect_offline
        return inspect_offline(invocation)
    if invocation.action == "run":
        raise ConformanceError("EvidenceIncomplete")
    raise ConformanceError()


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
    if kind == "ResourceOwnership":
        if ((result["childPid"] == 0) != (result["childStartSha256"] == "0" * 64)
                or result["state"] == "Released"
                and (result["childPid"] != 0 or result["diagnosticCode"] != "None")):
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
    from conformance_case_catalog import (
        CATEGORY_QUALITY_BASIS, COMPATIBILITY_RUNTIME_QUALITY_SCOPES, COMPOSITION_QUALITY_BASIS, expected_cases,
    )

    inputs = report["inputs"]
    quality_basis = CATEGORY_QUALITY_BASIS.get(inputs["profileId"], {})
    composition_cases = ({case.key: case for case in expected_cases("composition")}
                         if inputs["profileId"] == "composition" else None)
    compatibility_cases = ({case.key: case for case in expected_cases("compatibility")}
                           if inputs["profileId"] == "compatibility" else None)
    compatibility_physical = {}
    if compatibility_cases is not None:
        from conformance_case_catalog import architecture_runtime_tests, binary_runtime_tests, version_runtime_tests
        compatibility_physical = {
            identity: (scope, binding)
            for scope, rows in (("architecture", architecture_runtime_tests()),
                                ("version", version_runtime_tests()), ("binary", binary_runtime_tests()))
            for identity, (binding, _) in rows.items()}
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
    results = {(row["profileId"], row["bindingId"], row["matrixId"], row["caseId"]): row
               for row in report["results"]}
    for result in report["results"]:
        if (result["runId"] != inputs["runId"] or result["profileId"] != inputs["profileId"]
                or not set(result["proofSha256"]).issubset(proofs)):
            _invalid()
        composition_case = None
        if composition_cases is not None:
            composition_case = composition_cases.get((
                result["profileId"], result["bindingId"], result["matrixId"], result["caseId"]))
            if composition_case is None or not result["applicable"]:
                _invalid()
        compatibility_case = None
        if compatibility_cases is not None:
            compatibility_case = compatibility_cases.get((
                result["profileId"], result["bindingId"], result["matrixId"], result["caseId"]))
            if compatibility_case is None or not result["applicable"]:
                _invalid()
        for attempt in result["attempts"]:
            quality_link = False
            if (result["bindingId"] == result["matrixId"] == "none"
                    and result["caseId"] in quality_basis and attempt["witnessIds"]):
                material = _category_quality_composition(
                        inputs, result["caseId"], results, executions, sequence=attempt["sequence"],
                        started_ms=attempt["startedMs"], ended_ms=attempt["endedMs"], proof_registry=report["proofs"])
                if (inputs["mode"] != "qualification" or attempt != material["attempt"]
                        or any(report["proofs"].get(path) != hashlib.sha256(raw).hexdigest()
                               for path, raw in material["sourceProofs"].items())):
                    _invalid()
                quality_link = True
            composition_link = False
            if (composition_case is not None and result["caseId"] in COMPOSITION_QUALITY_BASIS
                    and attempt["status"] == "Passed"):
                material = composition_quality_case_material(
                    inputs, case_id=result["caseId"], results=report["results"], witnesses=report["witnesses"],
                    sequence=attempt["sequence"], started_ms=attempt["startedMs"], ended_ms=attempt["endedMs"])
                if (attempt != material["attempt"]
                        or any(report["proofs"].get(path) != hashlib.sha256(raw).hexdigest()
                               for path, raw in material["sourceProofs"].items())):
                    _invalid()
                composition_link = True
            compatibility_link = False
            if (compatibility_case is not None and result["caseId"] in COMPATIBILITY_RUNTIME_QUALITY_SCOPES
                    and attempt["status"] == "Passed"):
                material = compatibility_quality_case_material(
                    inputs, case_id=result["caseId"], results=report["results"], witnesses=report["witnesses"],
                    sequence=attempt["sequence"], started_ms=attempt["startedMs"], ended_ms=attempt["endedMs"])
                if (attempt != material["attempt"]
                        or any(report["proofs"].get(path) != hashlib.sha256(raw).hexdigest()
                               for path, raw in material["sourceProofs"].items())):
                    _invalid()
                compatibility_link = True
            if (compatibility_case is not None and compatibility_case.witnesses
                    and attempt["status"] == "Passed"):
                if any(identity not in executions for identity in attempt["witnessIds"]):
                    _invalid()
                material = _compatibility_case_material(
                    inputs, compatibility_case, compatibility_physical,
                    [executions[identity] for identity in attempt["witnessIds"]], input_sha=input_sha,
                    sequence=attempt["sequence"], started_ms=attempt["startedMs"], ended_ms=attempt["endedMs"])
                if (attempt != material["attempt"]
                        or any(report["proofs"].get(path) != hashlib.sha256(raw).hexdigest()
                               for path, raw in material["sourceProofs"].items())):
                    _invalid()
                compatibility_link = True
            if (composition_case is not None and composition_case.witnesses
                    and attempt["status"] == "Passed"
                    and any(executions.get(identity, {}).get("matrixId") != result["matrixId"]
                            for identity in attempt["witnessIds"])):
                if any(identity not in executions for identity in attempt["witnessIds"]):
                    _invalid()
                material = composition_case_material(
                    inputs, case_id=result["caseId"], matrix_id=result["matrixId"],
                    witnesses=[executions[identity] for identity in attempt["witnessIds"]],
                    sequence=attempt["sequence"], started_ms=attempt["startedMs"], ended_ms=attempt["endedMs"])
                if (attempt != material["attempt"]
                        or any(report["proofs"].get(path) != hashlib.sha256(raw).hexdigest()
                               for path, raw in material["sourceProofs"].items())):
                    _invalid()
                composition_link = True
            for execution_id in attempt["witnessIds"]:
                witness = executions.get(execution_id)
                if (witness is None or witness["proofSha256"] not in attempt["proofSha256"]
                        or (not quality_link and witness["bindingId"] != result["bindingId"])
                        or (not composition_link and not compatibility_link
                            and witness["matrixId"] != result["matrixId"])
                        or witness["startedMs"] < attempt["startedMs"] or witness["endedMs"] > attempt["endedMs"]
                        or (attempt["status"] == "Passed" and witness["status"] != "Passed")):
                    _invalid()
                referenced.add(execution_id)
            if composition_case is not None and composition_case.witnesses:
                identities = tuple(executions[identity]["testIdentity"] for identity in attempt["witnessIds"])
                expected = set(composition_case.witnesses)
                if (len(identities) != len(set(identities)) or not set(identities) <= expected
                        or attempt["status"] == "Passed" and set(identities) != expected):
                    _invalid()
    if referenced != set(executions) or any(resource["runId"] != inputs["runId"] for resource in report["resources"]):
        _invalid()
    resources = {}
    resource_keys = set()
    for resource in report["resources"]:
        key = resource["rootId"], resource["childPid"]
        if key in resource_keys:
            _invalid()
        resource_keys.add(key)
        resources.setdefault(resource["rootId"], []).append(resource)
    for rows in resources.values():
        if (len(rows) > 1 and any(row["childPid"] == 0 for row in rows)
                or len({(row["state"], row["cleanupDurationMs"], row["diagnosticCode"]) for row in rows}) != 1):
            _invalid()
    if report["qualification"] and (
            inputs["mode"] != "qualification" or report["state"] != "Complete"
            or not report["resources"]
            or report["postInputSha256"] != report["proofs"].get(
                f'proofs/category-{inputs["profileId"]}-{inputs["mode"]}-completion-inputs.json')
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


@contextmanager
def _input_root(root):
    from conformance_execution import no_symlinks
    descriptor = None
    try:
        root = Path(root).absolute()
        if ".." in root.parts:
            raise ConformanceError("InputChanged")
        no_symlinks(root)
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        before = os.fstat(descriptor)
        yield root, descriptor
        no_symlinks(root)
        after = root.stat(follow_symlinks=False)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ConformanceError("InputChanged")
    except ConformanceError as error:
        if str(error) != "OwnershipInvalid":
            raise
        raise ConformanceError("InputChanged") from None
    except OSError:
        raise ConformanceError("InputChanged") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


@contextmanager
def _input_parent(root, relative, *, create=False):
    parts = PurePosixPath(relative_path(relative)).parts
    if len(parts) > 32:
        raise ConformanceError("OutputLimitExceeded")
    descriptor = os.dup(root)
    try:
        for part in parts[:-1]:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor, parts[-1]
    finally:
        os.close(descriptor)


def _source_file(root, relative, *, remaining, deadline, target=None):
    def identity(info):
        return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns
    with _input_parent(root, relative) as (parent, name):
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            raise ConformanceError("InputChanged")
        if before.st_size > remaining:
            raise ConformanceError("OutputLimitExceeded")
        if time.monotonic() >= deadline:
            raise ConformanceError("DeadlineExceeded")
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as source:
            if identity(os.fstat(source.fileno())) != identity(before):
                raise ConformanceError("InputChanged")
            hashed = hashlib.sha256()
            observed = 0
            while block := source.read(64 * 1024):
                observed += len(block)
                if observed > remaining:
                    raise ConformanceError("OutputLimitExceeded")
                if time.monotonic() >= deadline:
                    raise ConformanceError("DeadlineExceeded")
                hashed.update(block)
                if target is not None:
                    target.write(block)
            if observed != before.st_size or identity(os.fstat(source.fileno())) != identity(before):
                raise ConformanceError("InputChanged")
        with _input_parent(root, relative) as (current_parent, current_name):
            if identity(os.stat(current_name, dir_fd=current_parent, follow_symlinks=False)) != identity(before):
                raise ConformanceError("InputChanged")
        if time.monotonic() >= deadline:
            raise ConformanceError("DeadlineExceeded")
        return hashed.hexdigest(), observed


def input_manifest(root, paths):
    deadline = time.monotonic() + 5
    if isinstance(paths, (list, tuple)) and len(paths) > MAX_PROOF_FILES:
        raise ConformanceError("OutputLimitExceeded")
    paths = _list(relative_path, MAX_PROOF_FILES, unique=True)(paths)
    total = 0
    result = {}
    with _input_root(root) as (_, descriptor):
        for relative in sorted(paths):
            hashed, size = _source_file(descriptor, relative, remaining=MAX_PROOF_BYTES - total,
                                         deadline=deadline)
            result[relative] = hashed
            total += size
    if time.monotonic() >= deadline:
        raise ConformanceError("DeadlineExceeded")
    return MappingProxyType(result)


def _local_package_patterns(local_package_ids):
    packages = _list(stable_id, 1024, minimum=0, unique=True)(local_package_ids)
    folded = tuple(package.casefold() for package in packages)
    if len(set(folded)) != len(folded):
        _invalid()
    return ("Hoard.*", *sorted(package for package in folded if not package.startswith("hoard.")))


def synthetic_nuget_configuration(feed, *, local_package_ids=()):
    local = escape(str(feed), {'"': "&quot;"})
    patterns = "".join(f'<package pattern="{package}"/>' for package in _local_package_patterns(local_package_ids))
    result = (
        '<configuration><packageSources><clear/>'
        f'<add key="local" value="{local}"/>'
        '<add key="nuget.org" value="https://api.nuget.org/v3/index.json"/>'
        '</packageSources><packageSourceMapping><packageSource key="local">'
        f'{patterns}</packageSource><packageSource key="nuget.org">'
        '<package pattern="*"/></packageSource></packageSourceMapping></configuration>'
    ).encode("utf-8")
    if len(result) > 64 * 1024:
        raise ConformanceError("OutputLimitExceeded")
    return result


def verify_synthetic_source_mapping(root, configuration, feed, *, local_package_ids=()):
    configuration, feed = relative_path(configuration), relative_path(feed)
    captured = io.BytesIO()
    with _input_root(root) as (root, descriptor):
        with _input_root(root / feed):
            _source_file(descriptor, configuration, remaining=64 * 1024,
                         deadline=time.monotonic() + 5, target=captured)
            if captured.getvalue() != synthetic_nuget_configuration(
                    root / feed, local_package_ids=local_package_ids):
                raise ConformanceError("InputChanged")
    return synthetic_source_mapping(local_package_ids=local_package_ids)


def synthetic_source_mapping(*, local_package_ids=()):
    return MappingProxyType({
        "packageSources": MappingProxyType({
            "local": "isolated-current-archives", "nuget.org": "https://api.nuget.org/v3/index.json"}),
        "packageSourceMapping": MappingProxyType({
            "local": _local_package_patterns(local_package_ids), "nuget.org": ("*",)}),
    })


def frozen_nuget_configuration(feed):
    local = escape(str(feed), {'"': "&quot;"})
    result = ('<configuration><packageSources><clear />'
              f'<add key="frozen" value="{local}" />'
              '</packageSources></configuration>').encode("utf-8")
    if len(result) > 64 * 1024:
        raise ConformanceError("OutputLimitExceeded")
    return result


def verify_frozen_source_mapping(root, configuration, feed, *, archives):
    configuration, feed = relative_path(configuration), relative_path(feed)
    archives = _hash_map(archives)
    if (len(archives) > 1024
            or any(Path(path).parent.as_posix() != feed or not path.endswith(".nupkg") for path in archives)
            or len({Path(path).name.casefold() for path in archives}) != len(archives)):
        raise ConformanceError("EvidenceSchemaInvalid")
    selected = {Path(path).name: hashed for path, hashed in archives.items()}
    captured = io.BytesIO()
    with _input_root(root) as (root, descriptor):
        _source_file(descriptor, configuration, remaining=64 * 1024,
                     deadline=time.monotonic() + 5, target=captured)
        if (captured.getvalue() != frozen_nuget_configuration(root / feed)
                or proof_manifest(root / feed) != selected):
            raise ConformanceError("InputChanged")
    return MappingProxyType({
        "packageSources": MappingProxyType({"frozen": "isolated-frozen-archives"}),
        "archives": MappingProxyType(selected),
    })


def verify_input_recomputation(before, after):
    before, after = admit_entity("RunInputs", before), admit_entity("RunInputs", after)
    environment = dict(after["environment"])
    # Free space is an admission measurement, not an immutable machine identity.
    environment["freeBytes"] = before["environment"]["freeBytes"]
    compared = dict(after)
    compared.update(environment=environment, environmentSha256=digest(environment))
    if digest(before) != digest(compared):
        raise ConformanceError("InputChanged")
    return digest(before)


def _readonly_report_proof(root, path):
    contents = io.BytesIO()
    with _input_root(root) as (_, descriptor):
        with _input_parent(descriptor, path) as (parent, name):
            if stat.S_IMODE(os.stat(name, dir_fd=parent, follow_symlinks=False).st_mode) != 0o400:
                raise ConformanceError("ProofMismatch")
        hashed, _ = _source_file(descriptor, path, remaining=MAX_REPORT_BYTES,
                                 deadline=time.monotonic() + 5, target=contents)
    return hashed, contents.getvalue()


def verify_completion_inputs(root, report):
    """Verify retained actual completion measurements without rewriting free space."""
    report = admit_entity("QualificationReport", report)
    inputs = report["inputs"]
    path = f'proofs/category-{inputs["profileId"]}-{inputs["mode"]}-completion-inputs.json'
    if report["proofs"].get(path) != report["postInputSha256"]:
        raise ConformanceError("ProofMismatch")
    hashed, raw = _readonly_report_proof(root, path)
    if hashed != report["postInputSha256"]:
        raise ConformanceError("ProofMismatch")
    completion = admit_entity("RunInputs", load_json(raw))
    verify_input_recomputation(inputs, completion)
    return completion


def verify_retained_category_report(root, report_data, *, expected_inputs, expected_report_sha256=None):
    """Verify a caller-pinned diagnostic; its digest must come from outside the artifact."""
    if expected_report_sha256 is None:
        raise ConformanceError("EvidenceIncomplete")
    expected_report_sha256 = sha256(expected_report_sha256)
    if not isinstance(report_data, bytes) or len(report_data) > MAX_REPORT_BYTES:
        raise ConformanceError("EvidenceSchemaInvalid")
    if hashlib.sha256(report_data).hexdigest() != expected_report_sha256:
        raise ConformanceError("ProofMismatch")
    return inspect_category_report(root, report_data, expected_inputs=expected_inputs)


def inspect_category_report(root, report_data, *, expected_inputs):
    """Inspect a complete category ledger without attesting runtime origin."""
    report = admit_entity("QualificationReport", load_json(report_data))
    expected_inputs = admit_entity("RunInputs", expected_inputs)
    inputs = report["inputs"]
    if digest(inputs) != digest(expected_inputs):
        raise ConformanceError("InputChanged")
    if (inputs["profileId"] not in ("metadata", "artifacts")
            or inputs["mode"] not in ("qualification", "diagnostic")):
        raise ConformanceError("UnsupportedProfile")
    if (report["qualification"] or report["state"] != "Incomplete"
            or report["scope"] != ("category-runtime-diagnostic",)):
        raise ConformanceError("EvidenceIncomplete")
    inspected = inspect_profile_report(root, report_data, expected_inputs=expected_inputs,
                                       expected_report_sha256=hashlib.sha256(report_data).hexdigest())
    return MappingProxyType({
        "qualification": False, "scope": "category-report-structure-diagnostic",
        "code": inspected["code"], "reportSha256": inspected["reportSha256"],
        "caseCount": inspected["caseCount"], "witnessCount": inspected["witnessCount"],
    })


def inspect_native_category_report(run, report_data, *, expected_inputs, native_evaluation):
    """Bind independent report inspection to the original live-to-released authority."""
    from conformance_execution import OwnedRun
    from conformance_sources import NativeCategoryEvaluation

    if type(run) is not OwnedRun or type(native_evaluation) is not NativeCategoryEvaluation:
        raise ConformanceError("OwnershipInvalid")
    inputs = admit_entity("RunInputs", expected_inputs)
    if inputs["mode"] != "qualification" or inputs["profileId"] not in ("metadata", "artifacts"):
        raise ConformanceError("UnsupportedProfile")
    if not isinstance(report_data, bytes) or len(report_data) > MAX_REPORT_BYTES:
        raise ConformanceError("EvidenceSchemaInvalid")
    report = admit_entity("QualificationReport", load_json(report_data))
    prefix = f'proofs/category-{inputs["profileId"]}-qualification'
    hashed, raw = _readonly_report_proof(run.root, prefix + "-history.json")
    if hashed != native_evaluation.history_sha256:
        raise ConformanceError("ProofMismatch")
    record = load_json(raw)
    native_evaluation.verify_report_origin(
        run, inputs, record, {"historySha256": hashed}, report["resources"])
    if (digest(report["results"]) != digest(record["results"])
            or digest(report["witnesses"]) != digest(record["witnesses"])
            or report["proofs"] != {
                **record["proofs"], prefix + "-completion-inputs.json": report["postInputSha256"]}):
        raise ConformanceError("ProofMismatch")
    inspected = inspect_category_report(run.root, report_data, expected_inputs=inputs)
    return MappingProxyType({
        **inspected, "scope": "native-category-runtime-origin-diagnostic", "runtimeOriginVerified": True})


def inspect_native_compatibility_report(run, report_data, *, expected_inputs, native_evaluation):
    """Replay compatibility runtimes only with their original released executor."""
    from conformance_execution import OwnedRun
    from conformance_sdk_checks import inspect_compatibility_runtime_scope, verify_compatibility_case_report
    from conformance_sources import NativeCompatibilityEvaluation

    if type(run) is not OwnedRun or type(native_evaluation) is not NativeCompatibilityEvaluation:
        raise ConformanceError("OwnershipInvalid")
    if not isinstance(report_data, bytes) or len(report_data) > MAX_REPORT_BYTES:
        raise ConformanceError("EvidenceSchemaInvalid")
    inputs = admit_entity("RunInputs", expected_inputs)
    summary = load_json(report_data)
    if not isinstance(summary, dict):
        raise ConformanceError("EvidenceSchemaInvalid")
    native_evaluation.verify_report_origin(run, inputs, summary)
    commands = []
    counts = {}
    for scope, key in (("architecture", "architectureRuntime"), ("version", "versionRuntime"),
                       ("binary", "binaryRuntime")):
        _, retained = _readonly_report_proof(run.root, f"proofs/compatibility-{scope}-runtime-summary.json")
        observed, records, _ = inspect_compatibility_runtime_scope(
            run.root, inputs, scope, summary[key], summary["architecturePreparation"])
        if canonical_bytes(observed) != retained or retained != canonical_bytes(summary[key]):
            raise ConformanceError("ProofMismatch")
        commands.extend(records)
        counts[scope] = observed["passedParameters"]
    if tuple(commands) != native_evaluation.command_hashes:
        raise ConformanceError("ProofMismatch")
    _, active_data = _readonly_report_proof(run.root, "proofs/compatibility-runtime-report.json")
    active = admit_entity("QualificationReport", load_json(active_data))
    if summary.get("runtimeCases") != verify_compatibility_case_report(
            run.root, inputs, summary, report_data=active_data):
        raise ConformanceError("ProofMismatch")
    _, released_data = _readonly_report_proof(run.root, "proofs/compatibility-runtime-released-report.json")
    released = admit_entity("QualificationReport", load_json(released_data))
    expected = admit_entity("QualificationReport", {**active, "resources": run.resource_projection()})
    if released != expected:
        raise ConformanceError("ProofMismatch")
    cases = verify_compatibility_case_report(run.root, inputs, summary, report_data=released_data)
    return MappingProxyType({
        "qualification": False, "profileComplete": False, "runtimeOriginVerified": True,
        "scope": "native-compatibility-runtime-origin-diagnostic",
        "reportSha256": hashlib.sha256(report_data).hexdigest(),
        "architectureParameters": counts["architecture"], "versionParameters": counts["version"],
        "binaryParameters": counts["binary"],
        "passedCases": cases["passedCases"], "incompleteCases": cases["incompleteCases"],
        "runtimeCaseReportSha256": cases["reportSha256"],
    })


def inspect_native_composition_report(run, report_data, *, expected_inputs, native_evaluation):
    """Inspect original composition transport only after its actual owner releases."""
    from conformance_composition_checks import verify_composition_case_report
    from conformance_execution import OwnedRun
    from conformance_sources import NativeCompositionEvaluation

    if type(run) is not OwnedRun or type(native_evaluation) is not NativeCompositionEvaluation:
        raise ConformanceError("OwnershipInvalid")
    if not isinstance(report_data, bytes) or len(report_data) > MAX_REPORT_BYTES:
        raise ConformanceError("EvidenceSchemaInvalid")
    inputs = admit_entity("RunInputs", expected_inputs)
    report = admit_entity("QualificationReport", load_json(report_data))
    native_evaluation.verify_report_origin(run, inputs, report)
    _, owner_data = _readonly_report_proof(run.root, "runtime-owner.json")
    inspected = verify_composition_case_report(
        run.root, inputs, load_json(owner_data), report_data=report_data)
    return MappingProxyType({
        **inspected, "scope": "native-composition-runtime-origin-diagnostic", "runtimeOriginVerified": True})


def inspect_profile_report(root, report_data, *, expected_inputs, expected_report_sha256):
    """Recompute catalog/file correspondence, never runtime-origin qualification."""
    from conformance_case_catalog import CATEGORY_QUALITY_BASIS, expected_cases

    if not isinstance(report_data, bytes) or len(report_data) > MAX_REPORT_BYTES:
        raise ConformanceError("EvidenceSchemaInvalid")
    if hashlib.sha256(report_data).hexdigest() != sha256(expected_report_sha256):
        raise ConformanceError("ProofMismatch")
    report = admit_entity("QualificationReport", load_json(report_data))
    inputs = report["inputs"]
    if digest(inputs) != digest(admit_entity("RunInputs", expected_inputs)):
        raise ConformanceError("InputChanged")
    cases = {case.key: case for case in expected_cases(inputs["profileId"])}
    results = {(row["profileId"], row["bindingId"], row["matrixId"], row["caseId"]): row
               for row in report["results"]}
    if results.keys() != cases.keys():
        raise ConformanceError("WitnessMissing")
    witnesses = {row["executionId"]: row for row in report["witnesses"]}
    for key, result in results.items():
        case = cases[key]
        if result != _catalog_case_result(inputs, case, result["status"], result["attempts"]):
            raise ConformanceError("ProofMismatch")
        used = set()
        for attempt in result["attempts"]:
            if used.intersection(attempt["witnessIds"]):
                raise ConformanceError("ProofMismatch")
            used.update(attempt["witnessIds"])
            composed_quality = case.binding_id == case.matrix_id == "none" and (
                case.case_id in CATEGORY_QUALITY_BASIS.get(inputs["profileId"], {}))
            if case.witnesses and attempt["status"] == "Passed" and not composed_quality:
                identities = tuple(witnesses[identity]["testIdentity"] for identity in attempt["witnessIds"])
                if len(identities) != len(set(identities)) or set(identities) != set(case.witnesses):
                    raise ConformanceError("WitnessMissing")
    if input_manifest(root, list(report["proofs"])) != report["proofs"]:
        raise ConformanceError("ProofMismatch")
    verify_completion_inputs(root, report)
    failed_attempts = sum(attempt["status"] == "Failed" for result in report["results"]
                          for attempt in result["attempts"])
    if report["qualification"]:
        raise ConformanceError("EvidenceIncomplete")
    return MappingProxyType({
        "qualification": False, "scope": "profile-report-structure-diagnostic",
        "code": "AssertionFailed" if failed_attempts else "EvidenceIncomplete",
        "profileId": inputs["profileId"], "reportSha256": hashlib.sha256(report_data).hexdigest(),
        "caseCount": len(results), "witnessCount": len(witnesses),
        "caseStates": MappingProxyType({
            state: sum(result["status"] == state for result in results.values()) for state in STATUSES}),
        "failedAttemptCount": failed_attempts,
    })


def render_category_diagnostics(root, report_data, *, expected_inputs, expected_report_sha256):
    """Render bounded public diagnostics, never qualification or private proof contents."""
    inspected = verify_retained_category_report(
        root, report_data, expected_inputs=expected_inputs, expected_report_sha256=expected_report_sha256)
    report = admit_entity("QualificationReport", load_json(report_data))
    if (inspected["qualification"] or report["qualification"] or report["state"] != "Incomplete"
            or report["scope"] != ("category-runtime-diagnostic",)):
        raise ConformanceError("EvidenceIncomplete")
    inputs = report["inputs"]
    profile = inputs["profileId"]
    states = {state: sum(row["status"] == state for row in report["results"]) for state in STATUSES}
    summary = {
        "schemaVersion": 1, "kind": "category-diagnostic-summary",
        "qualification": False, "state": "Incomplete", "code": inspected["code"],
        "scope": "category-report-structure-diagnostic", "profileId": profile,
        "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "sourceRevision": inputs["sourceRevision"], "inputsSha256": digest(inputs),
        "reportSha256": inspected["reportSha256"], "caseStates": states,
        "witnessCount": len(report["witnesses"]), "proofCount": len(report["proofs"]),
        "support": {
            "status": "NotQualified",
            "bindingSlots": sorted({row["bindingId"] for row in report["results"] if row["bindingId"] != "none"}),
            "exclusions": [{key: row[key] for key in ("bindingId", "matrixId", "caseId", "exclusionRule")}
                           for row in report["results"] if row["status"] == "NotApplicable"]}}
    suite = ET.Element("testsuite", {
        "name": "conformance-" + profile + "-diagnostic", "tests": str(len(report["results"]) + 1),
        "failures": str(states["Failed"]), "errors": str(states["Incomplete"] + 1),
        "skipped": str(states["NotApplicable"])})
    for row in report["results"]:
        case = ET.SubElement(suite, "testcase", {
            "classname": ".".join((profile, row["bindingId"], row["matrixId"])), "name": row["caseId"]})
        if row["status"] == "NotApplicable":
            ET.SubElement(case, "skipped", {"type": "NotApplicable", "message": row["exclusionRule"]})
        elif row["status"] in ("Failed", "Incomplete"):
            codes = [attempt["diagnosticCode"] for attempt in row["attempts"]
                     if attempt["diagnosticCode"] != "None"]
            code = codes[-1] if codes else "EvidenceIncomplete"
            ET.SubElement(case, "failure" if row["status"] == "Failed" else "error", {"type": code})
    ET.SubElement(ET.SubElement(suite, "testcase", {"classname": "conformance", "name": "qualification"}),
                  "error", {"type": "EvidenceIncomplete", "message": "Diagnostic evidence is not qualification."})
    markdown = (
        f"## {profile} conformance diagnostics\n\n"
        "**Incomplete: diagnostic evidence is not qualification.**\n\n"
        "| Case state | Count |\n| --- | ---: |\n"
        + "".join(f"| {state} | {count} |\n" for state, count in states.items())
        + f"\nSource: `{inputs['sourceRevision']}`\n\nReport SHA-256: `{inspected['reportSha256']}`\n\n"
        "Only the catalogued fixture slots and frozen exclusions are described. "
        "No production, external-service, protocol, identity or HA support is inferred.\n").encode("utf-8")
    prefix = "category-" + profile
    if inputs["mode"] == "qualification":
        prefix += "-qualification"
    outputs = {
        prefix + "-diagnostic.json": canonical_bytes(summary),
        prefix + "-diagnostic.junit.xml": ET.tostring(suite, encoding="utf-8", xml_declaration=True),
        prefix + "-diagnostic.md": markdown, prefix + "-ci-summary.md": markdown}
    if any(len(raw) > MAX_REPORT_BYTES for raw in outputs.values()):
        raise ConformanceError("OutputLimitExceeded")
    return MappingProxyType(outputs)


_BINDING_REQUIRED_FAULTS = {
    "metadata": frozenset((
        "IndependentSnapshot", "WriterContention", "CommitAcknowledgement", "PersistedCorruption",
        "Capacity", "SchemaState", "LeaseBoundary", "NativeNonCooperation", "CleanupFailure")),
    "artifacts": frozenset((
        "PublicationBoundary", "DirectVisibility", "PayloadDamage", "Capacity", "NativeNonCooperation",
        "CleanupFailure", "GenerationBoundary", "ReceiptBoundary", "SourceNonCooperation", "SinkNonCooperation")),
}


def admit_binding_declaration(value, *, require_archive_hash=True):
    faults = frozenset().union(*_BINDING_REQUIRED_FAULTS.values(), ("BackupRestore",))
    fields = {
        "schemaVersion": _constant(1), "bindingId": stable_id,
        "category": _one_of("metadata", "artifacts"), "packageId": stable_id,
        "packageVersion": stable_id,
        "capabilities": _ids, "faults": _list(_one_of(*sorted(faults)), 128, unique=True),
    }
    if require_archive_hash:
        fields["packageSha256"] = sha256
    declaration = _record(fields)(value)
    required = _BINDING_REQUIRED_FAULTS[declaration["category"]]
    if (not required.issubset(declaration["faults"])
            or (declaration["category"] == "metadata"
                and "durable-local-process-crash" in declaration["capabilities"]
                and "BackupRestore" not in declaration["faults"])):
        raise ConformanceError("BindingInvalid")
    return declaration


def capture_binding(root, declaration_path, *, packages, adapter_id, catalog_binding_id=None):
    deadline = time.monotonic() + 5
    declaration_path, adapter_id = relative_path(declaration_path), stable_id(adapter_id)
    packages = _list(_entity("PackageIdentity"), 1024)(packages)
    captured = io.BytesIO()
    with _input_root(root) as (_, descriptor):
        _source_file(descriptor, declaration_path, remaining=64 * 1024,
                     deadline=deadline, target=captured)
    raw = captured.getvalue()
    declaration = admit_binding_declaration(load_json(raw))
    matching = [package for package in packages
                if package["packageId"].casefold() == declaration["packageId"].casefold()
                and package["version"].casefold() == declaration["packageVersion"].casefold()]
    if len(matching) != 1 or matching[0]["sha256"] != declaration["packageSha256"]:
        raise ConformanceError("BindingInvalid")
    binding_id = declaration["bindingId"]
    if catalog_binding_id is not None:
        from conformance_case_catalog import CATEGORY_BINDING_SLOTS
        catalog_binding_id = stable_id(catalog_binding_id)
        selected = [slot for slot in CATEGORY_BINDING_SLOTS if slot[1] == catalog_binding_id]
        if (len(selected) != 1 or selected[0][0] != declaration["category"]
                or selected[0][2] != binding_id
                or selected[0][3].casefold() != matching[0]["packageId"].casefold()):
            raise ConformanceError("BindingInvalid")
        binding_id = catalog_binding_id
    admitted = admit_entity("ProviderBinding", {
        "bindingId": binding_id, "package": matching[0], "category": declaration["category"],
        "descriptorSha256": hashlib.sha256(raw).hexdigest(),
        "capabilitySha256": digest({field: declaration[field] for field in ("category", "capabilities", "faults")}),
        "adapterId": adapter_id,
    })
    if time.monotonic() >= deadline:
        raise ConformanceError("DeadlineExceeded")
    return admitted


def _binding_source(value):
    fields = {"path": relative_path, "adapterId": stable_id}
    if isinstance(value, (dict, MappingProxyType)) and "catalogBindingId" in value:
        fields["catalogBindingId"] = stable_id
    return _record(fields)(value)


def configuration_policy():
    return MappingProxyType({
        "revision": CATALOG_REVISION, "stores": "fresh-owned-synthetic",
        "restore": "locked", "runtimeLogger": "HoardSafe", "consoleLogger": False})


def configuration_record(source_mapping, *, inspection_inputs=None):
    policy = {**configuration_policy(), "sources": source_mapping}
    if inspection_inputs is not None:
        from conformance_case_catalog import ORIGINAL_INSPECTION_LITERAL_WITNESSES, ORIGINAL_INSPECTION_WITNESSES
        expected = set(ORIGINAL_INSPECTION_WITNESSES) - set(ORIGINAL_INSPECTION_LITERAL_WITNESSES)
        if (not isinstance(inspection_inputs, (dict, MappingProxyType)) or not inspection_inputs
                or set(inspection_inputs) - expected):
            _invalid()
        selected = {}
        for identity, files in inspection_inputs.items():
            if not isinstance(files, (dict, MappingProxyType)) or not 0 < len(files) <= 2048:
                _invalid()
            assignments = {}
            for path, hashed in files.items():
                if (not isinstance(path, str) or not 0 < len(path.encode("utf-8")) <= 4096
                        or not Path(path).is_absolute() or os.path.normpath(path) != path
                        or any(ord(character) < 32 or ord(character) == 127 for character in path)):
                    _invalid()
                assignments[hashlib.sha256(path.encode("utf-8")).hexdigest()] = sha256(hashed)
            selected[identity] = assignments
        policy["inspectionInputs"] = selected
    return load_json(canonical_bytes(policy))


def configuration_fingerprint(source_mapping, *, inspection_inputs=None):
    return digest(configuration_record(source_mapping, inspection_inputs=inspection_inputs))


def capture_profile_inputs(run, repository, snapshot, *, profile_id, mode, invocation_group_id,
                           package_versions, feed, configuration, lock_paths, runtime_paths,
                           binding_sources, observed_environment, budgets, invocation,
                           baseline_sha256=None, ci_revision=None, inspection_inputs=None, frozen_archives=None):
    from conformance_case_catalog import CATEGORY_BINDING_SLOTS
    run._check_ledger()
    profile_id, mode = _one_of(*PROFILES)(profile_id), _one_of(
        "qualification", "diagnostic", "preparation")(mode)
    invocation_group_id = _uuid(invocation_group_id)
    feed, configuration = relative_path(feed), relative_path(configuration)
    package_versions = _list(_record({"packageId": stable_id, "version": stable_id}),
                             1024, unique=True)(package_versions)
    binding_sources = _list(_binding_source, 128, minimum=0, unique=True)(binding_sources)
    if frozen_archives is not None:
        frozen_archives = _hash_map(frozen_archives)
    try:
        snapshot_relative = relative_path(Path(snapshot).relative_to(run.root).as_posix())
    except ValueError:
        raise ConformanceError("OwnershipInvalid") from None
    identity = source_identity(repository, ci_revision=ci_revision)
    sources = source_manifest(repository)
    verify_snapshot(run.root / snapshot_relative, sources)
    sdk = "tests/contracts/Hoard.Testing.Conformance/"
    catalog = sdk + "Catalog/catalog.json"
    if catalog not in sources:
        raise ConformanceError("EvidenceIncomplete")
    source_mapping = (verify_synthetic_source_mapping(run.root, configuration, feed) if frozen_archives is None
                      else verify_frozen_source_mapping(run.root, configuration, feed, archives=frozen_archives))
    packages = [package_identity(run.root / feed, item["packageId"], item["version"])
                for item in package_versions]
    bindings = [capture_binding(run.root, item["path"], packages=packages, adapter_id=item["adapterId"],
                                catalog_binding_id=item.get("catalogBindingId"))
                for item in binding_sources]
    original_ids = {slot[1]: slot[2] for slot in CATEGORY_BINDING_SLOTS}
    declaration_ids = {
        original_ids[source["catalogBindingId"]] if "catalogBindingId" in source else binding["bindingId"]
        for source, binding in zip(binding_sources, bindings)}
    if len(declaration_ids) != len(bindings):
        raise ConformanceError("BindingInvalid")
    baseline_inputs = []
    if baseline_sha256 is not None:
        from conformance_baselines import verify_prepared_baselines
        prepared = verify_prepared_baselines(run.root, sha256(baseline_sha256))
        baseline_inputs = [{
            "revision": entry["revision"], "sourceSha256": entry["sourceSha256"],
            "lockSha256": entry["lockSha256"], "recipeSha256": entry["recipeSha256"],
            "binarySha256": digest(entry["binaries"]), "dependencySha256": entry["binaries"],
            "apiScope": entry["id"],
        } for entry in prepared["entries"]]
    inputs = admit_entity("RunInputs", {
        "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": invocation_group_id,
        "profileId": profile_id, "mode": mode, "catalogRevision": CATALOG_REVISION,
        "catalogSha256": sources[catalog],
        "sdkSha256": digest({path: hashed for path, hashed in sources.items() if path.startswith(sdk)}),
        "sourceRevision": identity["sourceRevision"], "sourceState": identity["sourceState"],
        "sourceManifest": sources, "sourceManifestSha256": digest(sources),
        "packages": packages, "locks": input_manifest(run.root, lock_paths),
        "runtimeAssemblies": input_manifest(run.root, runtime_paths),
        "configurationSha256": configuration_fingerprint(source_mapping, inspection_inputs=inspection_inputs),
        "capabilitySha256": digest({binding["bindingId"]: binding["capabilitySha256"] for binding in bindings}),
        "bindings": bindings, "baselines": baseline_inputs,
        "environment": observed_environment, "environmentSha256": digest(observed_environment),
        "budgets": budgets, "invocation": invocation,
    })
    if (source_manifest(repository) != sources
            or source_identity(repository, ci_revision=ci_revision) != identity):
        raise ConformanceError("InputChanged")
    if frozen_archives is not None:
        verify_frozen_source_mapping(run.root, configuration, feed, archives=frozen_archives)
    run._check_ledger()
    return inputs


def _git_control(root, arguments, deadline):
    from conformance_execution import capture_control
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ConformanceError("DeadlineExceeded")
    environment = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ}
    environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0"})
    code, output = capture_control(["git", "--work-tree=" + str(root), *arguments],
                                   cwd=root, env=environment, timeout=min(5, remaining))
    if code:
        raise ConformanceError("InputChanged")
    return output


def _package_identity_data(feed, package_id, version):
    package_id, version = stable_id(package_id), stable_id(version)
    filename = relative_path(f"{package_id}.{version}.nupkg")
    deadline = time.monotonic() + 5
    captured = io.BytesIO()
    with _input_root(feed) as (_, descriptor):
        sha256, _ = _source_file(descriptor, filename, remaining=MAX_PACKAGE_BYTES,
                                 deadline=deadline, target=captured)
    raw = captured.getvalue()
    # Bound central-directory materialization before ZipFile allocates entries.
    end = raw.rfind(b"PK\x05\x06", max(0, len(raw) - 65557))
    if (end < 0 or end + 22 > len(raw)
            or end + 22 + int.from_bytes(raw[end + 20:end + 22], "little") != len(raw)):
        raise ConformanceError("InputChanged")
    if (int.from_bytes(raw[end + 10:end + 12], "little") > 1024
            or int.from_bytes(raw[end + 12:end + 16], "little") > 1024 * 1024):
        raise ConformanceError("OutputLimitExceeded")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > 1024 or sum(item.file_size for item in entries) > MAX_PACKAGE_EXPANDED_BYTES:
                raise ConformanceError("OutputLimitExceeded")
            names = set()
            for item in entries:
                name = relative_path(item.filename[:-1] if item.is_dir() else item.filename)
                kind = stat.S_IFMT(item.external_attr >> 16)
                if (name in names or item.flag_bits & 1
                        or kind not in (0, stat.S_IFREG, stat.S_IFDIR)
                        or (kind == stat.S_IFDIR and not item.is_dir())
                        or (kind == stat.S_IFREG and item.is_dir())
                        or item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                    raise ConformanceError("InputChanged")
                names.add(name)
            manifests = [item for item in entries if item.filename.lower().endswith(".nuspec")]
            if (len(manifests) != 1 or manifests[0].filename.lower() != f"{package_id}.nuspec".lower()
                    or manifests[0].file_size > 64 * 1024):
                raise ConformanceError("InputChanged")
            document = archive.read(manifests[0]).decode("utf-8-sig", errors="strict")
            if "<!DOCTYPE" in document.upper() or "<!ENTITY" in document.upper():
                raise ConformanceError("InputChanged")
            root = ET.fromstring(document)
            if sum(1 for _ in root.iter()) > 1024 or root.tag.rsplit("}", 1)[-1] != "package":
                raise ConformanceError("InputChanged")
            metadata = [node for node in root if node.tag.rsplit("}", 1)[-1] == "metadata"]
            if len(metadata) != 1:
                raise ConformanceError("InputChanged")
            for field, expected in (("id", package_id), ("version", version)):
                values = [node.text for node in metadata[0] if node.tag.rsplit("}", 1)[-1] == field]
                if len(values) != 1 or values[0] is None or values[0].casefold() != expected.casefold():
                    raise ConformanceError("InputChanged")
            assemblies = {}
            for item in entries:
                if time.monotonic() >= deadline:
                    raise ConformanceError("DeadlineExceeded")
                if (item.is_dir() or not item.filename.startswith(("lib/", "runtimes/"))
                        or not item.filename.endswith((".dll", ".so", ".dylib"))):
                    continue
                hashed = hashlib.sha256()
                observed = 0
                with archive.open(item) as source:
                    while block := source.read(64 * 1024):
                        observed += len(block)
                        if observed > item.file_size or observed > MAX_PACKAGE_EXPANDED_BYTES:
                            raise ConformanceError("OutputLimitExceeded")
                        if time.monotonic() >= deadline:
                            raise ConformanceError("DeadlineExceeded")
                        hashed.update(block)
                if observed != item.file_size:
                    raise ConformanceError("InputChanged")
                assemblies[item.filename] = hashed.hexdigest()
    except (zipfile.BadZipFile, ET.ParseError, UnicodeError, EOFError, RuntimeError, zlib.error):
        raise ConformanceError("InputChanged") from None
    admitted = MappingProxyType({
        "packageId": package_id, "version": version, "sha256": sha256,
        "nugetSha512": hashlib.sha512(raw).hexdigest(),
        "sourceMapping": "local", "runtimeAssemblies": MappingProxyType(assemblies),
    })
    if time.monotonic() >= deadline:
        raise ConformanceError("DeadlineExceeded")
    return admitted


def package_identity(feed, package_id, version):
    value = _package_identity_data(feed, package_id, version)
    if not value["runtimeAssemblies"]:
        raise ConformanceError("EvidenceIncomplete")
    return admit_entity("PackageIdentity", value)


def package_archive_identity(feed, package_id, version):
    value = _package_identity_data(feed, package_id, version)
    return MappingProxyType({key: item for key, item in value.items() if key != "runtimeAssemblies"})


def source_manifest(root):
    deadline = time.monotonic() + 5
    with _input_root(root) as (root, descriptor):
        output = _git_control(root,
            ["ls-files", "-z", "--cached", "--others", "--exclude-standard", "--",
             "src", "tests", "scripts", "examples", ".github/workflows", "global.json", "Hoard.slnx",
             "Directory.Build.props", "Directory.Build.targets", "Directory.Packages.props",
             "NuGet.Config", "nuget.config", ".editorconfig", ".gitignore", ".gitattributes",
             "specs/004-module-discovery/contracts/openapi.json"], deadline,
        )
        try:
            paths = sorted(set(output.decode("utf-8", errors="strict").rstrip("\0").split("\0")))
        except UnicodeError:
            raise ConformanceError("InputChanged") from None
        if not paths:
            raise ConformanceError("InputChanged")
        if len(paths) > MAX_PROOF_FILES:
            raise ConformanceError("OutputLimitExceeded")
        manifest = {}
        total = 0
        for relative in paths:
            if {"bin", "obj", "__pycache__"}.intersection(PurePosixPath(relative).parts):
                raise ConformanceError("InputChanged")
            hashed, size = _source_file(
                descriptor, relative, remaining=MAX_PROOF_BYTES - total, deadline=deadline)
            manifest[relative] = hashed
            total += size
    if time.monotonic() >= deadline:
        raise ConformanceError("DeadlineExceeded")
    return MappingProxyType(manifest)


def source_identity(root, *, ci_revision=None):
    if ci_revision is not None and (
            not isinstance(ci_revision, str) or re.fullmatch("[0-9a-f]{40}", ci_revision) is None):
        raise ConformanceError("InputChanged")
    deadline = time.monotonic() + 5
    with _input_root(root) as (root, _):
        observations = []
        for arguments in (["rev-parse", "HEAD"], ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
                          ["ls-files", "-v", "-z"]):
            observations.append(_git_control(root, arguments, deadline))
        revision, changes, entries = observations
        if re.fullmatch(rb"[0-9a-f]{40}\n", revision) is None:
            raise ConformanceError("InputChanged")
        revision = revision.decode("ascii").strip()
        dirty = bool(changes) or any(entry[:2] != b"H " for entry in entries.split(b"\0") if entry)
        if ci_revision is not None and (dirty or revision != ci_revision):
            raise ConformanceError("InputChanged")
        state = "clean-ci" if ci_revision is not None else "dirty-local" if dirty else "clean-local"
    if time.monotonic() >= deadline:
        raise ConformanceError("DeadlineExceeded")
    return MappingProxyType({"sourceRevision": revision, "sourceState": state})


def snapshot_sources(root, owned_run, *, name="snapshot", manifest=None, transient=False):
    name = stable_id(name)
    if type(transient) is not bool:
        raise ConformanceError("EvidenceSchemaInvalid")
    before = source_manifest(root) if manifest is None else _hash_map(manifest)
    if manifest is not None and dict(input_manifest(root, list(before))) != dict(before):
        raise ConformanceError("InputChanged")
    owned_run._check_ledger()
    snapshot = owned_run.root / "stores" / name if transient else owned_run.root / name
    owner = owned_run._directory_descriptor("stores") if transient else owned_run._root_descriptor()
    try:
        os.mkdir(name, mode=0o700, dir_fd=owner)
        directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=owner)
        try:
            total = 0
            deadline = time.monotonic() + 5
            with _input_root(root) as (_, source):
                for relative, expected in before.items():
                    with _input_parent(directory, relative, create=True) as (parent, filename):
                        target = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                         0o400, dir_fd=parent)
                        with os.fdopen(target, "wb") as output:
                            hashed, size = _source_file(
                                source, relative, remaining=MAX_PROOF_BYTES - total,
                                deadline=deadline, target=output)
                        if hashed != expected:
                            raise ConformanceError("InputChanged")
                        total += size
        finally:
            os.close(directory)
    finally:
        os.close(owner)
    owned_run._check_ledger()
    verify_snapshot(snapshot, before)
    after = source_manifest(root) if manifest is None else input_manifest(root, list(before))
    if dict(after) != dict(before):
        raise ConformanceError("InputChanged")
    return snapshot, before


def verify_snapshot(snapshot, manifest):
    try:
        admitted = _hash_map(manifest)
        if proof_manifest(snapshot, exclude_outputs=True) != admitted:
            raise ConformanceError("InputChanged")
    except ConformanceError:
        raise ConformanceError("InputChanged") from None


@dataclass(frozen=True)
class _ProofReadObservation:
    files_hashed: int
    bytes_read: int
    entries_seen: int
    elapsed_ms: float
    cpu_elapsed_ms: float

    def __post_init__(self):
        for value in (self.files_hashed, self.bytes_read, self.entries_seen):
            _integer(value)
        _number(self.elapsed_ms)
        _number(self.cpu_elapsed_ms)

    def diagnostic(self):
        return {
            "filesHashed": self.files_hashed, "bytesRead": self.bytes_read,
            "entriesSeen": self.entries_seen, "elapsedMs": self.elapsed_ms,
            "cpuElapsedMs": self.cpu_elapsed_ms}


def proof_read_diagnostic(error):
    observed = getattr(error, "_proof_read", None)
    return {"proofRead": observed.diagnostic()} if type(observed) is _ProofReadObservation else {}


def proof_manifest(directory, *, exclude_outputs=False, include_file=None, include_directory=None):
    from conformance_execution import no_symlinks
    if (include_file is not None and not callable(include_file)
            or include_directory is not None and not callable(include_directory)):
        raise ConformanceError("ProofMismatch")
    directory = Path(directory).absolute()
    files = {}
    total = 0
    partial = 0
    entries_seen = 0
    started = time.monotonic()
    cpu_started = time.process_time()
    deadline = started + 5

    def visit(descriptor, prefix="", depth=0):
        nonlocal total, partial, entries_seen
        if depth > 32 or time.monotonic() >= deadline:
            raise ConformanceError("ProofMismatch")
        with os.scandir(descriptor) as entries:
            for entry in entries:
                entries_seen += 1
                if entries_seen > MAX_PROOF_FILES * 2 or time.monotonic() >= deadline:
                    raise ConformanceError("ProofMismatch")
                if exclude_outputs and entry.name in ("bin", "obj", "__pycache__"):
                    continue
                relative = relative_path(prefix + entry.name)
                before = os.stat(entry.name, dir_fd=descriptor, follow_symlinks=False)
                if stat.S_ISDIR(before.st_mode):
                    if include_directory is None or include_directory(relative):
                        child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                        try:
                            opened = os.fstat(child)
                            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                                raise ConformanceError("ProofMismatch")
                            visit(child, relative + "/", depth + 1)
                        finally:
                            os.close(child)
                elif stat.S_ISREG(before.st_mode) and (include_file is None or include_file(relative)):
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
                            partial = observed
                            if total + observed > MAX_PROOF_BYTES:
                                raise ConformanceError("ProofMismatch")
                            if time.monotonic() >= deadline:
                                raise ConformanceError("ProofMismatch")
                            hashed.update(block)
                        if observed != before.st_size:
                            raise ConformanceError("ProofMismatch")
                        files[relative] = hashed.hexdigest()
                        total += observed
                        partial = 0
                elif not stat.S_ISREG(before.st_mode):
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
    except ConformanceError as error:
        if str(error) == "ProofMismatch":
            error._proof_read = _ProofReadObservation(
                len(files), total + partial, entries_seen, (time.monotonic() - started) * 1000,
                (time.process_time() - cpu_started) * 1000)
            raise
        rejected = ConformanceError("ProofMismatch")
        rejected._proof_read = _ProofReadObservation(
            len(files), total + partial, entries_seen, (time.monotonic() - started) * 1000,
            (time.process_time() - cpu_started) * 1000)
        raise rejected from None
    except OSError:
        rejected = ConformanceError("ProofMismatch")
        rejected._proof_read = _ProofReadObservation(
            len(files), total + partial, entries_seen, (time.monotonic() - started) * 1000,
            (time.process_time() - cpu_started) * 1000)
        raise rejected from None
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
            or re.fullmatch(r'[a-zA-Z0-9_./():, "\[\]+-]+', value, re.ASCII) is None):
        _invalid()
    if "/" in value:
        from conformance_case_catalog import binary_runtime_tests
        if value not in binary_runtime_tests():
            _invalid()
    return value


def _assertion_symbol(value):
    if value is None:
        return None
    if (not isinstance(value, str) or len(value) > 256
            or re.fullmatch(r"Hoard\.(?:Testing\.Conformance|Composition\.Tests)\.[a-zA-Z0-9_.]+",
                            value, re.ASCII) is None):
        _invalid()
    return value


def _inherited_guard_entry(entry):
    from conformance_case_catalog import INHERITED_GUARD_FAILURES
    policy = INHERITED_GUARD_FAILURES.get(entry["caseId"])
    return (policy is not None
            and policy == (entry["fullyQualifiedName"], entry["matrixId"], entry["bindingId"])
            and entry["assertionSymbol"] == entry["fullyQualifiedName"])


def _runtime_json(data, fields, *, limit=2 * 1024 * 1024):
    if not isinstance(data, bytes) or not 0 < len(data) <= limit:
        raise ConformanceError("OutputLimitExceeded")
    return _record(fields)(load_json(data))


_LOADED_ASSEMBLY_FIELDS = {
    "assemblyName": stable_id, "assemblyVersion": stable_id, "moduleVersionId": _uuid,
    "assemblySha256": sha256, "typeSha256": sha256,
}
_SESSION_ROLES = {
    "metadata": ("factory", "session", "store", "schema", "authority", "faults"),
    "artifacts": ("factory", "session", "store", "validator", "maintenance", "lifetime", "authority", "faults"),
}


def _loaded_assembly_correspondence(inputs, observed, runtime_path, package_id):
    parts = observed["assemblyVersion"].split(".")
    if (len(parts) != 4
            or any(not part.isascii() or not part.isdecimal()
                   or str(int(part)) != part or int(part) > 65535 for part in parts)):
        raise ConformanceError()
    _runtime_bytes_correspondence(inputs, observed["assemblySha256"], runtime_path, package_id)
    return observed


def _runtime_bytes_correspondence(inputs, assembly_sha256, runtime_path, package_id):
    runtime_path = relative_path(runtime_path)
    if inputs["runtimeAssemblies"].get(runtime_path) != assembly_sha256:
        raise ConformanceError("InputChanged")
    if package_id is not None:
        stable_id(package_id)
        package = next((item for item in inputs["packages"] if item["packageId"] == package_id), None)
        if package is None or assembly_sha256 not in package["runtimeAssemblies"].values():
            raise ConformanceError("ProofMismatch")


def ingest_loaded_assembly(inputs, data, *, runtime_path, package_id):
    """Check a trusted actual-instance producer against independently selected input bytes."""
    return _loaded_assembly_correspondence(
        admit_entity("RunInputs", inputs),
        _runtime_json(data, _LOADED_ASSEMBLY_FIELDS, limit=64 * 1024), runtime_path, package_id)


def ingest_session_origin(inputs, data, *, binding_id, case_id, component_inputs, parent_session_id=None):
    """Admit a leaf session observation; this is not an execution witness or qualification."""
    inputs = admit_entity("RunInputs", inputs)
    binding_id, case_id = stable_id(binding_id), stable_id(case_id)
    if parent_session_id is not None:
        _uuid(parent_session_id)
    binding = next((item for item in inputs["bindings"] if item["bindingId"] == binding_id), None)
    if binding is None or binding["category"] not in ("metadata", "artifacts"):
        raise ConformanceError("BindingInvalid")
    roles = _SESSION_ROLES[binding["category"]]
    if (not isinstance(component_inputs, Mapping) or set(component_inputs) != set(roles)
            or any(not isinstance(value, tuple) or len(value) != 2 for value in component_inputs.values())):
        raise ConformanceError("EvidenceIncomplete")
    component = _record({"instanceId": _uuid, "assembly": _record(_LOADED_ASSEMBLY_FIELDS)})
    observed = _runtime_json(data, {
        "schemaVersion": _constant(1), "runId": _uuid, "caseId": stable_id, "sessionId": _uuid,
        "parentSessionId": lambda value: None if value is None else _uuid(value),
        "factoryOperation": _one_of("create", "reopen"), "descriptorSha256": sha256,
        "runtimeVersion": stable_id, "processArchitecture": _one_of("x64", "arm64"),
        "components": _record({role: component for role in roles}),
    }, limit=64 * 1024)
    architecture = {"x64": ("x86_64", "x64"), "arm64": ("aarch64", "arm64")}
    if (observed["runId"] != inputs["runId"] or observed["caseId"] != case_id
            or observed["descriptorSha256"] != binding["descriptorSha256"]
            or observed["runtimeVersion"] != inputs["environment"]["runtime"]
            or inputs["environment"]["architecture"] not in architecture[observed["processArchitecture"]]
            or observed["parentSessionId"] != parent_session_id
            or observed["sessionId"] == parent_session_id
            or observed["factoryOperation"] != ("create" if parent_session_id is None else "reopen")):
        raise ConformanceError("ProofMismatch")
    instances = {}
    for role, captured in observed["components"].items():
        runtime_path, package_id = component_inputs[role]
        assembly = _loaded_assembly_correspondence(inputs, captured["assembly"], runtime_path, package_id)
        prior = instances.setdefault(captured["instanceId"], assembly)
        if prior != assembly:
            raise ConformanceError("ProofMismatch")
    return observed


def _observe_component_instance(instances, captured):
    identity = tuple(captured[key] for key in ("assemblySha256", "moduleVersionId", "typeSha256"))
    if instances.setdefault(captured["instanceId"], identity) != identity:
        raise ConformanceError("ProofMismatch")


def _ingest_runtime_origins(inputs, origins, *, origin_inputs, case_id, prior_sessions, prior_instances):
    observed = []
    component = _record({
        "instanceId": _uuid, "assemblySha256": sha256, "moduleVersionId": _uuid, "typeSha256": sha256,
    })
    for raw in origins:
        if not isinstance(raw, Mapping):
            raise ConformanceError()
        descriptor = sha256(raw.get("descriptorSha256"))
        bindings = [item for item in inputs["bindings"] if item["descriptorSha256"] == descriptor]
        if len(bindings) != 1 or bindings[0]["category"] not in _SESSION_ROLES:
            raise ConformanceError("BindingInvalid")
        binding = bindings[0]
        roles = _SESSION_ROLES[binding["category"]]
        if not isinstance(origin_inputs, Mapping):
            raise ConformanceError("EvidenceIncomplete")
        assignments = origin_inputs.get(binding["bindingId"])
        if (not isinstance(assignments, Mapping) or set(assignments) != set(roles)
                or any(not isinstance(value, tuple) or len(value) != 2 for value in assignments.values())):
            raise ConformanceError("EvidenceIncomplete")
        origin = _record({
            "schemaVersion": _constant(1), "runId": _uuid, "caseId": stable_id, "sessionId": _uuid,
            "parentSessionId": lambda value: None if value is None else _uuid(value),
            "factoryOperation": _one_of("create", "reopen"), "descriptorSha256": sha256,
            "runtimeVersion": stable_id, "processArchitecture": _one_of("x64", "arm64"),
            "components": _record({role: component for role in roles}),
        })(raw)
        architecture = {"x64": ("x86_64", "x64"), "arm64": ("aarch64", "arm64")}
        parent_id = origin["parentSessionId"]
        if (origin["runId"] != inputs["runId"] or origin["caseId"] != case_id
                or origin["runtimeVersion"] != inputs["environment"]["runtime"]
                or inputs["environment"]["architecture"] not in architecture[origin["processArchitecture"]]
                or origin["factoryOperation"] != ("create" if parent_id is None else "reopen")
                or origin["sessionId"] in prior_sessions or origin["sessionId"] == parent_id):
            raise ConformanceError("ProofMismatch")
        if parent_id is not None:
            parent = prior_sessions.get(parent_id)
            if (parent is None or parent["descriptorSha256"] != descriptor or parent["caseId"] != case_id
                    or parent["components"]["factory"] != origin["components"]["factory"]):
                raise ConformanceError("ProofMismatch")
        for role, captured in origin["components"].items():
            _runtime_bytes_correspondence(inputs, captured["assemblySha256"], *assignments[role])
            _observe_component_instance(prior_instances, captured)
        prior_sessions[origin["sessionId"]] = origin
        observed.append(origin)
    return tuple(observed)


def ingest_artifact_recovery_origin(inputs, data, *, binding_id, case_id, component_inputs,
                                    declaration_data, source_data, recovery_input_sha256):
    """Admit a separate setup observation, not an execution witness or process/crash proof."""
    inputs = admit_entity("RunInputs", inputs)
    binding_id, case_id = stable_id(binding_id), stable_id(case_id)
    recovery_input_sha256 = sha256(recovery_input_sha256)
    binding = next((item for item in inputs["bindings"] if item["bindingId"] == binding_id), None)
    if binding is None or binding["category"] != "artifacts":
        raise ConformanceError("BindingInvalid")
    if (not isinstance(declaration_data, bytes) or not 0 < len(declaration_data) <= 64 * 1024
            or not isinstance(source_data, bytes) or not 0 < len(source_data) <= 64 * 1024):
        raise ConformanceError("OutputLimitExceeded")
    declaration = admit_binding_declaration(load_json(declaration_data))
    if (hashlib.sha256(declaration_data).hexdigest() != binding["descriptorSha256"]
            or declaration["category"] != "artifacts"
            or "durable-local-process-crash" not in declaration["capabilities"]
            or declaration["packageId"].casefold() != binding["package"]["packageId"].casefold()
            or declaration["packageVersion"].casefold() != binding["package"]["version"].casefold()
            or declaration["packageSha256"] != binding["package"]["sha256"]
            or digest({field: declaration[field] for field in ("category", "capabilities", "faults")})
            != binding["capabilitySha256"]):
        raise ConformanceError("BindingInvalid")
    prior_sessions, instances = {}, {}
    source, = _ingest_runtime_origins(
        inputs, [load_json(source_data)], origin_inputs={binding_id: component_inputs}, case_id=case_id,
        prior_sessions=prior_sessions, prior_instances=instances)
    if source["parentSessionId"] is not None or source["descriptorSha256"] != binding["descriptorSha256"]:
        raise ConformanceError("ProofMismatch")
    component = _record({
        "instanceId": _uuid, "assemblySha256": sha256, "moduleVersionId": _uuid, "typeSha256": sha256,
    })
    observed = _runtime_json(data, {
        "schemaVersion": _constant(1), "kind": _constant("artifact-recovery"),
        "runId": _uuid, "caseId": stable_id, "sessionId": _uuid, "sourceSessionId": _uuid,
        "recoveryInputSha256": sha256, "factoryOperation": _constant("recover"),
        "descriptorSha256": sha256, "runtimeVersion": stable_id,
        "processArchitecture": _one_of("x64", "arm64"),
        "components": _record({role: component for role in _SESSION_ROLES["artifacts"]}),
    }, limit=64 * 1024)
    if (observed["runId"] != source["runId"] or observed["caseId"] != case_id
            or observed["sourceSessionId"] != source["sessionId"]
            or observed["sessionId"] == source["sessionId"]
            or observed["recoveryInputSha256"] != recovery_input_sha256
            or observed["descriptorSha256"] != source["descriptorSha256"]
            or observed["runtimeVersion"] != source["runtimeVersion"]
            or observed["processArchitecture"] != source["processArchitecture"]):
        raise ConformanceError("ProofMismatch")
    for role, captured in observed["components"].items():
        if captured["instanceId"] in instances:
            raise ConformanceError("ProofMismatch")
        _runtime_bytes_correspondence(inputs, captured["assemblySha256"], *component_inputs[role])
    for captured in observed["components"].values():
        _observe_component_instance(instances, captured)
    return observed


def _runtime_manifest(inputs, manifest_data, owner_data, expected_tests,
                      manifest_sha256, owner_sha256, purpose):
    inputs = admit_entity("RunInputs", inputs)
    input_sha = digest(inputs)
    sha256(manifest_sha256)
    sha256(owner_sha256)
    file_fields = {"id": stable_id, "path": relative_path, "sha256": sha256}
    expected_fields = {
        "testIdentity": _runtime_identity, "fullyQualifiedName": _runtime_identity,
        "assemblyId": stable_id, "packageId": stable_id, "bindingId": stable_id,
        "matrixId": stable_id, "assertionSymbol": _assertion_symbol,
        "caseId": stable_id,
    }
    owner = _runtime_json(owner_data, {
        "schemaVersion": _constant(1), "runId": _uuid, "invocationGroupId": _uuid,
        "rootId": stable_id, "rootPathSha256": sha256,
    })
    manifest = _runtime_json(manifest_data, {
        "schemaVersion": _constant(1), "runId": _uuid, "invocationGroupId": _uuid,
        "attemptId": _uuid, "attemptSequence": _integer, "inputSha256": sha256,
        "purpose": _constant(purpose),
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
        parameter = r'(?:\"[a-zA-Z0-9._:/+,()\[\]-]{0,128}\"|[-+]?[0-9]+(?:\.[0-9]+)?|[a-zA-Z_][a-zA-Z0-9_]{0,127})'
        if (re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_.+]*", name, re.ASCII) is None
                or not entry["testIdentity"].startswith(name)
                or (suffix and re.fullmatch(
                    rf"\([a-zA-Z_][a-zA-Z0-9_]*: {parameter}(?:, [a-zA-Z_][a-zA-Z0-9_]*: {parameter})*\)",
                    suffix, re.ASCII) is None)
                or entry["assemblyId"] not in assemblies or entry["packageId"] not in packages):
            raise ConformanceError("WitnessMissing")
        if (entry["assertionSymbol"] is not None
                and entry["assertionSymbol"].startswith("Hoard.Composition.Tests.")
                and entry["assertionSymbol"] != name):
            raise ConformanceError("WitnessMissing")
    return inputs, manifest, expected, assemblies, packages, expected_tests


def _runtime_completion(data, purpose, records_data):
    completion = _runtime_json(data, {
        "schemaVersion": _constant(1), "runId": _uuid, "invocationGroupId": _uuid,
        "attemptId": _uuid, "attemptSequence": _integer, "manifestSha256": sha256,
        "inputSha256": sha256, "purpose": _constant(purpose), "recordsSha256": sha256,
        "diagnosticCode": _one_of(*DIAGNOSTIC_CODES),
        "observedCount": _integer, "expectedCount": _integer, "complete": _boolean,
    }, limit=64 * 1024)
    if completion["recordsSha256"] != hashlib.sha256(records_data).hexdigest():
        raise ConformanceError("ProofMismatch")
    return completion


def ingest_runtime_discovery(*, inputs, manifest_data, owner_data, discoveries_data,
                             completion_data, expected_tests, manifest_sha256, owner_sha256,
                             started_ms, ended_ms):
    """Admit exact selected discovery records, never execution witnesses."""
    inputs, manifest, expected, assemblies, _, _ = _runtime_manifest(
        inputs, manifest_data, owner_data, expected_tests, manifest_sha256, owner_sha256, "discovery")
    _number(started_ms)
    _number(ended_ms)
    if ended_ms < started_ms:
        _invalid()
    if (not isinstance(discoveries_data, bytes) or not isinstance(completion_data, bytes)
            or len(discoveries_data) + len(completion_data) > 8 * 1024 * 1024):
        raise ConformanceError("OutputLimitExceeded")
    if discoveries_data and not discoveries_data.endswith(b"\n"):
        raise ConformanceError("EvidenceIncomplete")
    lines = discoveries_data.splitlines()
    if len(lines) > MAX_RESULTS or any(not line or len(line) > 64 * 1024 for line in lines):
        raise ConformanceError("EvidenceIncomplete")
    fields = {
        "schemaVersion": _constant(1), "runId": _uuid, "invocationGroupId": _uuid,
        "attemptId": _uuid, "attemptSequence": _integer, "inputSha256": sha256,
        "manifestSha256": sha256, "ownerSha256": sha256,
        "testIdentity": _runtime_identity, "fullyQualifiedName": _runtime_identity,
        "assemblySha256": sha256, "discoveredMs": _number,
    }
    records = tuple(_runtime_json(line, fields, limit=64 * 1024) for line in lines)
    if len({record["testIdentity"] for record in records}) != len(records):
        raise ConformanceError("EvidenceIncomplete")
    for record in records:
        entry = expected.get(record["testIdentity"])
        if (entry is None or record["fullyQualifiedName"] != entry["fullyQualifiedName"]
                or record["assemblySha256"] != assemblies[entry["assemblyId"]]["sha256"]
                or any(record[key] != manifest[key] for key in (
                    "runId", "invocationGroupId", "attemptId", "attemptSequence", "inputSha256"))
                or record["manifestSha256"] != manifest_sha256 or record["ownerSha256"] != owner_sha256
                or not started_ms - 0.001 <= record["discoveredMs"] <= ended_ms + 0.001):
            raise ConformanceError("ProofMismatch")
    completion = _runtime_completion(completion_data, "discovery", discoveries_data)
    code = completion["diagnosticCode"]
    inventory_complete = {record["testIdentity"] for record in records} == set(expected)
    if (any(completion[key] != manifest[key] for key in (
            "runId", "invocationGroupId", "attemptId", "attemptSequence", "inputSha256"))
            or completion["manifestSha256"] != manifest_sha256
            or completion["expectedCount"] != len(expected)
            or not len(records) <= completion["observedCount"] <= MAX_RESULTS + 1
            or completion["complete"] != (inventory_complete and code == "None")
            or code == "AssertionFailed"
            or (code == "None" and (not inventory_complete or completion["observedCount"] != len(records)))):
        raise ConformanceError("EvidenceIncomplete")
    return MappingProxyType({
        "discoveries": records, "completion": completion,
        "attemptId": manifest["attemptId"], "diagnosticCode": code,
    })


def _ingest_original_observations(inputs, observations, *, original_inputs, entry, prior_observations, prior_instances,
                                  require_success=True):
    from conformance_case_catalog import CATEGORY_BINDING_SLOTS, original_witness_parents, original_witness_policy
    if not observations:
        return ()
    policy = original_witness_policy(entry["testIdentity"])
    parents = original_witness_parents(entry["testIdentity"])
    if policy is None or parents is None:
        raise ConformanceError("WitnessMissing")
    category, kind, roles = policy
    if len(observations) != len(parents) and not (
            category == "composition" and not require_success and len(observations) < len(parents)):
        raise ConformanceError("WitnessMissing")
    binding_id = entry["bindingId"]
    binding = next((item for item in inputs["bindings"] if item["bindingId"] == binding_id), None)
    if category == "composition":
        if inputs["profileId"] != "composition" or binding_id != "none":
            raise ConformanceError("BindingInvalid")
    elif (binding is None or binding["category"] != category
          or binding_id not in {slot[1] for slot in CATEGORY_BINDING_SLOTS if slot[0] == category}):
        raise ConformanceError("BindingInvalid")
    witnesses = original_inputs.get(binding_id) if isinstance(original_inputs, Mapping) else None
    assignments = witnesses.get(entry["testIdentity"]) if isinstance(witnesses, Mapping) else None
    assignments = original_node_assignments(entry["testIdentity"], assignments)
    component = _record({
        "instanceId": _uuid, "assemblySha256": sha256, "moduleVersionId": _uuid, "typeSha256": sha256,
    })
    observed = []
    for raw in observations:
        observation = _record({
            "schemaVersion": _constant(1), "runId": _uuid, "caseId": stable_id,
            "testIdentity": _runtime_identity, "bindingId": stable_id, "observationId": _uuid,
            "parentObservationId": lambda value: None if value is None else _uuid(value),
            "kind": _one_of("original-instance", "loaded-contract", "original-owner"),
            "operation": _one_of("create", "reopen", "contract"),
            "runtimeVersion": stable_id, "processArchitecture": _one_of("x64", "arm64"),
            "components": _record({role: component for role in roles}),
        })(raw)
        parent_id = observation["parentObservationId"]
        parent_index = parents[len(observed)]
        if parent_id != (None if parent_index is None else observed[parent_index]["observationId"]):
            raise ConformanceError("ProofMismatch")
        architecture = {"x64": ("x86_64", "x64"), "arm64": ("aarch64", "arm64")}
        if (observation["runId"] != inputs["runId"] or observation["caseId"] != entry["caseId"]
                or observation["testIdentity"] != entry["testIdentity"] or observation["bindingId"] != binding_id
                or observation["kind"] != kind
                or observation["runtimeVersion"] != inputs["environment"]["runtime"]
                or inputs["environment"]["architecture"] not in architecture[observation["processArchitecture"]]
                or observation["observationId"] in prior_observations or observation["observationId"] == parent_id
                or observation["operation"] != ("contract" if kind == "loaded-contract"
                                                else "reopen" if parent_id is not None else "create")):
            raise ConformanceError("ProofMismatch")
        if kind in ("loaded-contract", "original-owner") and parent_id is not None:
            raise ConformanceError("ProofMismatch")
        if kind in ("original-instance", "original-owner") and any(
                observation["components"][role]["instanceId"] == prior["components"][role]["instanceId"]
                for prior in observed for role in (("owner", "store") if kind == "original-instance" else ("owner",))):
            raise ConformanceError("ProofMismatch")
        if parent_id is not None:
            parent = prior_observations.get(parent_id)
            if (parent is None or any(parent[key] != observation[key] for key in
                                     ("runId", "caseId", "testIdentity", "bindingId", "kind"))
                    or parent["components"]["owner"]["instanceId"] == observation["components"]["owner"]["instanceId"]):
                raise ConformanceError("ProofMismatch")
        for role, captured in observation["components"].items():
            assignment = assignments[len(observed)][role]
            if not isinstance(assignment, tuple) or len(assignment) != 2:
                raise ConformanceError("EvidenceIncomplete")
            if category == "composition" and assignment[1] != "Hoard.Fixtures.Conformance.Host":
                raise ConformanceError("ProofMismatch")
            if (kind == "original-instance" and role in ("store", "schema", "validator", "maintenance", "lifetime")
                    and (assignment[1] is None
                         or assignment[1].casefold() != binding["package"]["packageId"].casefold())):
                raise ConformanceError("ProofMismatch")
            _runtime_bytes_correspondence(inputs, captured["assemblySha256"], *assignment)
            _observe_component_instance(prior_instances, captured)
        prior_observations[observation["observationId"]] = observation
        observed.append(observation)
    return tuple(observed)


def ingest_runtime_attempt(*, inputs, manifest_data, owner_data, witnesses_data, proofs,
                           completion_data, expected_tests, manifest_sha256, owner_sha256,
                           started_ms, ended_ms, origin_inputs=None, original_inputs=None):
    """Validate actual safe-logger records; a valid failed attempt remains failed."""
    inspected = inspect_runtime_attempt(
        inputs=inputs, manifest_data=manifest_data, owner_data=owner_data, witnesses_data=witnesses_data,
        proofs=proofs, completion_data=completion_data, expected_tests=expected_tests,
        manifest_sha256=manifest_sha256, owner_sha256=owner_sha256, started_ms=started_ms, ended_ms=ended_ms,
        origin_inputs=origin_inputs, original_inputs=original_inputs)
    inputs, observed = inspected["inputs"], inspected["observation"]
    if inputs["mode"] == "qualification":
        from conformance_case_catalog import original_non_session_policy, original_witness_policy
        for witness in observed["witnesses"]:
            if witness["status"] != "Passed":
                continue
            originals = observed["originalObservations"][witness["executionId"]]
            origins = observed["sessionOrigins"][witness["executionId"]]
            selected_binding = next((binding for binding in inputs["bindings"]
                                     if binding["bindingId"] == witness["bindingId"]), None)
            if original_witness_policy(witness["testIdentity"]) is not None:
                if not originals:
                    raise ConformanceError("WitnessMissing")
            elif original_non_session_policy(witness["testIdentity"]) is not None:
                raise ConformanceError("WitnessMissing")
            elif (selected_binding is not None and selected_binding["category"] in _SESSION_ROLES
                  and not any(origin["descriptorSha256"] == selected_binding["descriptorSha256"] for origin in origins)):
                raise ConformanceError("WitnessMissing")
    return observed


def inspect_runtime_attempt(*, inputs, manifest_data, owner_data, witnesses_data, proofs,
                            completion_data, expected_tests, manifest_sha256, owner_sha256,
                            started_ms, ended_ms, origin_inputs=None, original_inputs=None):
    """Inspect validated transport for parent corroboration without qualifying it."""
    captured, observed = _read_runtime_attempt(
        inputs=inputs, manifest_data=manifest_data, owner_data=owner_data, witnesses_data=witnesses_data,
        proofs=proofs, completion_data=completion_data, expected_tests=expected_tests,
        manifest_sha256=manifest_sha256, owner_sha256=owner_sha256, started_ms=started_ms, ended_ms=ended_ms,
        origin_inputs=origin_inputs, original_inputs=original_inputs)
    return MappingProxyType({
        "qualification": False, "inputs": captured, "inputsSha256": digest(captured), "observation": observed})


def inspect_inherited_runtime_attempts(*, inventory_data, sources, discoveries, attempts):
    """Re-admit the complete frozen inventories across disjoint class scopes."""
    from conformance_inherited import execution_scopes, inventory

    sources = _hash_map(sources)
    methods = inventory(inventory_data, sources)
    scopes = execution_scopes(discoveries, methods)
    inventory_sha = hashlib.sha256(inventory_data).hexdigest()
    discovery_hashes = MappingProxyType({
        assembly: hashlib.sha256(raw).hexdigest() for assembly, raw in discoveries.items()})
    admitted = []
    seen_scopes, seen_attempts, seen_executions = set(), set(), set()
    common_inputs = owner_sha = None
    assembly_inputs = {}
    observed_count = passed_count = 0
    for attempt in attempts:
        if (len(admitted) >= len(scopes) or not isinstance(attempt, dict)
                or set(attempt) != {"assembly", "testClass", "transport"}
                or not isinstance(attempt["assembly"], str) or not isinstance(attempt["testClass"], str)
                or not isinstance(attempt["transport"], dict)):
            raise ConformanceError("EvidenceSchemaInvalid")
        key = (attempt["assembly"], attempt["testClass"])
        if key not in scopes or key in seen_scopes:
            raise ConformanceError("WitnessMissing")
        expected = {row["testIdentity"]: row for row in scopes[key]}
        transport = attempt["transport"]
        allowed = {
            "inputs", "manifest_data", "owner_data", "witnesses_data", "proofs", "completion_data",
            "expected_tests", "manifest_sha256", "owner_sha256", "started_ms", "ended_ms",
            "origin_inputs", "original_inputs",
        }
        required = allowed - {"expected_tests", "origin_inputs", "original_inputs"}
        if not required <= transport.keys() or transport.keys() - allowed:
            raise ConformanceError("EvidenceSchemaInvalid")
        inspected = inspect_runtime_attempt(**{
            **transport, "expected_tests": {
                identity: (row["bindingId"], row["matrixId"]) for identity, row in expected.items()},
        })
        inputs, observation = inspected["inputs"], inspected["observation"]
        manifest = load_json(transport["manifest_data"])
        if (inputs["profileId"] != "composition" or inputs["sourceManifest"] != sources
                or inputs["sourceManifestSha256"] != digest(sources)
                or {row["testIdentity"]: row for row in manifest["expected"]} != expected
                or manifest["attemptId"] in seen_attempts):
            raise ConformanceError("InputChanged")
        shared = digest({name: value for name, value in inputs.items()
                         if name not in ("runtimeAssemblies", "configurationSha256", "invocation")})
        per_assembly = digest({
            "runtimeAssemblies": inputs["runtimeAssemblies"],
            "configurationSha256": inputs["configurationSha256"],
        })
        if (common_inputs is not None and shared != common_inputs
                or owner_sha is not None and transport["owner_sha256"] != owner_sha
                or key[0] in assembly_inputs and assembly_inputs[key[0]] != per_assembly):
            raise ConformanceError("InputChanged")
        executions = {row["executionId"] for row in observation["witnesses"]}
        if executions & seen_executions:
            raise ConformanceError("ProofMismatch")
        seen_scopes.add(key)
        seen_attempts.add(manifest["attemptId"])
        seen_executions.update(executions)
        common_inputs, owner_sha = shared, transport["owner_sha256"]
        assembly_inputs[key[0]] = per_assembly
        observed_count += len(observation["witnesses"])
        passed_count += sum(row["status"] == "Passed" for row in observation["witnesses"])
        admitted.append(MappingProxyType({
            "assembly": key[0], "testClass": key[1], "attemptId": manifest["attemptId"],
            "inputSha256": inspected["inputsSha256"], "manifestSha256": transport["manifest_sha256"],
            "ownerSha256": owner_sha, "observation": observation,
        }))
    if seen_scopes != scopes.keys():
        raise ConformanceError("WitnessMissing")
    expected_count = sum(map(len, scopes.values()))
    witnesses = {row["testIdentity"]: (row["status"], scope["observation"]["diagnosticCode"])
                 for scope in admitted for row in scope["observation"]["witnesses"]}
    coverage = {}
    for case, required_methods in load_json(inventory_data)["caseMethods"].items():
        identities = tuple(sorted(identity for identity in witnesses if identity.split("(")[0] in required_methods))
        if not identities:
            raise ConformanceError("WitnessMissing")
        coverage[case] = MappingProxyType({
            "tests": identities, "passed": all(witnesses[identity] == ("Passed", "None") for identity in identities)})
    import discovery_evidence as discovery
    discovery_methods = {name for name, row in methods.items() if row["group"] == "discovery"}
    discovery_rows = [row for raw in discoveries.values() for row in load_json(raw)
                      if row["fullyQualifiedName"] in discovery_methods]
    scenarios = tuple(sorted(row["testIdentity"] for row in discovery_rows))
    adapters = []
    for display in discovery.REQUIRED_ADAPTER_SCENARIOS:
        method = display.split("(")[0]
        matched = [row["testIdentity"] for row in discovery_rows
                   if row["fullyQualifiedName"] == method and "testCaseId" in row
                   and row["testIdentity"] == method + '(testCaseSha256: "' + hashlib.sha256(
                       (row["testCaseId"] + "\n" + display).encode("utf-8")).hexdigest() + '")']
        if len(matched) != 1:
            raise ConformanceError("WitnessMissing")
        adapters.extend(matched)
    suites = []
    for suite, classes in discovery.SUITE_CLASSES.items():
        selected = tuple(identity for identity in scenarios if identity.split("(")[0].rsplit(".", 2)[1] in classes)
        if {identity.split("(")[0].rsplit(".", 2)[1] for identity in selected} != set(classes):
            raise ConformanceError("WitnessMissing")
        suites.append(MappingProxyType({
            "id": suite, "tests": len(selected),
            "passed": all(witnesses[identity] == ("Passed", "None") for identity in selected)}))
    if all(row["passed"] for row in suites):
        try:
            discovery.verify_suites([dict(row) for row in suites])
            discovery.verify_cases([{"id": case, "passed": row["passed"], "tests": list(row["tests"])}
                                    for case, row in coverage.items() if case.startswith("D")])
        except RuntimeError:
            raise ConformanceError("WitnessMissing") from None
    return MappingProxyType({
        "qualification": False, "profileComplete": False,
        "executionComplete": observed_count == passed_count == expected_count
        and all(row["observation"]["diagnosticCode"] == "None" for row in admitted),
        "expectedParameters": expected_count, "observedParameters": observed_count,
        "passedParameters": passed_count, "scopes": tuple(admitted),
        "caseCoverage": MappingProxyType(coverage),
        "discoveryCoverage": MappingProxyType({
            "scenarios": scenarios, "adapterScenarios": tuple(adapters), "suites": tuple(suites)}),
        "inventorySha256": inventory_sha, "discoverySha256": discovery_hashes,
    })


def _ingest_metadata_arguments(inputs, raw, origins, originals, prior_ids, binding_id):
    if raw and not any(binding["bindingId"] == binding_id and binding["category"] == "metadata"
                       for binding in inputs["bindings"]):
        raise ConformanceError("ProofMismatch")
    sources = {
        **{("session-origin", source["sessionId"]): source for source in origins},
        **{("original-observation", source["observationId"]): source for source in originals},
    }
    result = []
    choices = {
        "continuation-corruption": ("store", ("Null", "Omitted", "WrongType", "Empty", "OddHex", "InvalidHex")),
        "query-corruption": ("store", ("CacheAuthorization", "AggregateAuthorization", "AggregateStart",
                                     "AggregateEnd", "LeaseResource")),
        "lease-expiry": ("store", ("Renew", "Release", "Guard")),
        "schema-layout": ("schema", ("unrelated", "partial")),
    }
    for value in raw:
        argument = _record({
            "schemaVersion": _constant(1), "runId": _uuid, "caseId": stable_id, "callId": _uuid,
            "sourceKind": _one_of("session-origin", "original-observation"), "sourceId": _uuid,
            "componentRole": _one_of("store", "schema"), "componentInstanceId": _uuid,
            "argumentKind": _one_of(*choices),
            "argumentValue": _one_of(*(value for _, values in choices.values() for value in values)),
        })(value)
        source = sources.get((argument["sourceKind"], argument["sourceId"]))
        role, values = choices[argument["argumentKind"]]
        if (source is None or argument["callId"] in prior_ids or argument["runId"] != inputs["runId"]
                or argument["caseId"] != source["caseId"] or argument["argumentValue"] not in values
                or argument["componentRole"] != role or "schema" not in source["components"]
                or argument["componentInstanceId"] != source["components"][role]["instanceId"]
                or (argument["sourceKind"] == "original-observation"
                    and (source["kind"] != "original-instance" or source["bindingId"] not in ("memory", "sqlite")))):
            raise ConformanceError("ProofMismatch")
        prior_ids.add(argument["callId"])
        result.append(argument)
    return tuple(result)


def _ingest_composition_observations(raw, originals, prior_ids, *, require_success, test_identity):
    from conformance_case_catalog import composition_snapshot_owner_indices, composition_snapshot_policy
    policy = composition_snapshot_policy(test_identity)
    if not raw:
        return ()
    if policy is None:
        raise ConformanceError("WitnessMissing")
    def counter(value):
        value = _integer(value)
        if value > 1_000_000:
            raise ConformanceError("OutputLimitExceeded")
        return value

    fields = _record({
        "schemaVersion": _constant(1), "observationId": _uuid, "sourceId": _uuid,
        "stage": _one_of(*(stage for stage, _ in policy)),
        "counters": _record({name: counter for name in policy[0][1]}),
    })
    owners = tuple(origin["observationId"] for origin in originals if origin["kind"] == "original-owner")
    owner_indices = composition_snapshot_owner_indices(test_identity)
    stages = set()
    admitted = []
    for value in raw:
        observation = fields(value)
        identity, source = observation["observationId"], observation["sourceId"]
        key = source, observation["stage"]
        index = len(admitted)
        if (index >= len(policy) or owner_indices[index] >= len(owners)
                or source != owners[owner_indices[index]] or observation["stage"] != policy[index][0]
                or identity in prior_ids or identity == source or key in stages):
            raise ConformanceError("ProofMismatch")
        prior_ids.add(identity)
        stages.add(key)
        expected = dict(policy)[observation["stage"]]
        if require_success and observation["counters"] != expected:
            raise ConformanceError("ProofMismatch")
        admitted.append(observation)
    if not admitted:
        return ()
    if require_success and len(admitted) != len(policy):
        raise ConformanceError("WitnessMissing")
    return tuple(admitted)


def _ingest_version_observations(raw, *, profile, require_success, test_identity):
    from conformance_case_catalog import version_observation_policy
    policy = version_observation_policy(test_identity)
    if raw and (profile != "compatibility" or policy is None):
        raise ConformanceError("ProofMismatch")
    if policy is None:
        return ()
    if require_success and (profile != "compatibility" or len(raw) != len(policy)):
        raise ConformanceError("WitnessMissing")
    if len(raw) > len(policy):
        raise ConformanceError("ProofMismatch")
    result = []
    for value, (kind, counters) in zip(raw, policy):
        row = _record({"kind": _constant(kind),
                       "counters": _record({name: _integer for name in counters})})(value)
        if any(value > 1_000_000 for value in row["counters"].values()):
            raise ConformanceError("OutputLimitExceeded")
        if require_success and any(
                not expected[0] <= row["counters"][name] <= expected[1] if isinstance(expected, tuple)
                else row["counters"][name] != expected for name, expected in counters.items()):
            raise ConformanceError("ProofMismatch")
        result.append(row)
    return tuple(result)


def _read_runtime_attempt(*, inputs, manifest_data, owner_data, witnesses_data, proofs,
                          completion_data, expected_tests, manifest_sha256, owner_sha256,
                          started_ms, ended_ms, origin_inputs=None, original_inputs=None):
    inputs, manifest, expected, assemblies, packages, expected_tests = _runtime_manifest(
        inputs, manifest_data, owner_data, expected_tests, manifest_sha256, owner_sha256, "execution")
    input_sha = digest(inputs)
    _number(started_ms)
    _number(ended_ms)
    if ended_ms < started_ms:
        _invalid()
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
        "failureKind": _one_of("None", "Assertion", "Guard", "Unknown", "SkippedOrUnknown"),
        "assertionSymbol": _assertion_symbol, "status": _executed_state,
        "caseId": stable_id, "sessionOrigins": _list(lambda value: value, 128, minimum=0),
    }
    proof_hashes = {}
    session_origins = {}
    original_observations = {}
    metadata_arguments = {}
    composition_observations = {}
    version_observations = {}
    prior_arguments = set()
    prior_compositions = set()
    prior_sessions = {}
    prior_observations = {}
    prior_instances = {}
    unknown_failure = False
    guard_failure = False
    for witness in witnesses:
        entry = expected.get(witness["testIdentity"])
        if entry is None:
            raise ConformanceError("WitnessMissing")
        path = f'proof-{witness["executionId"]}.json'
        proof_data = proofs[path]
        if not 0 < len(proof_data) <= 64 * 1024:
            raise ConformanceError("OutputLimitExceeded")
        raw = load_json(proof_data)
        version = raw.get("schemaVersion") if isinstance(raw, Mapping) else None
        fields = proof_fields
        if version in (2, 3, 4):
            fields = {**proof_fields, "schemaVersion": _constant(version),
                      "originalObservations": _list(lambda value: value, 128, minimum=0)}
            if version == 3:
                fields["metadataArguments"] = _list(lambda value: value, 128, minimum=1)
            elif version == 4:
                fields["compositionObservations"] = _list(lambda value: value, 128, minimum=1)
        elif version == 5:
            fields = {**proof_fields, "schemaVersion": _constant(5),
                      "versionObservations": _list(lambda value: value, 2, minimum=1)}
        proof = _record(fields)(raw)
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
                or proof["caseId"] != entry["caseId"]
                or (witness["bindingId"], witness["matrixId"]) != expected_tests[witness["testIdentity"]]
                or witness["packageSha256"] != packages[entry["packageId"]]["sha256"]
                or witness["assemblySha256"] != assemblies[entry["assemblyId"]]["sha256"]
                or witness["startedMs"] < started_ms - 0.001 or witness["endedMs"] > ended_ms + 0.001
                or proof["durationMs"] > 8 * 60 * 60 * 1000
                or abs(proof["durationMs"] - (witness["endedMs"] - witness["startedMs"])) > 0.001):
            raise ConformanceError("ProofMismatch")
        origins = _ingest_runtime_origins(
            inputs, proof["sessionOrigins"], origin_inputs=origin_inputs,
            case_id=entry["caseId"], prior_sessions=prior_sessions, prior_instances=prior_instances)
        originals = _ingest_original_observations(
            inputs, proof.get("originalObservations", ()), original_inputs=original_inputs, entry=entry,
            prior_observations=prior_observations, prior_instances=prior_instances,
            require_success=witness["status"] == "Passed")
        if (set(prior_sessions) & set(prior_observations)
                or prior_arguments & (set(prior_sessions) | set(prior_observations))):
            raise ConformanceError("ProofMismatch")
        arguments = _ingest_metadata_arguments(
            inputs, proof.get("metadataArguments", ()), origins, originals, prior_arguments, entry["bindingId"])
        compositions = _ingest_composition_observations(
            proof.get("compositionObservations", ()), originals, prior_compositions,
            require_success=witness["status"] == "Passed", test_identity=entry["testIdentity"])
        versions = _ingest_version_observations(
            proof.get("versionObservations", ()), profile=inputs["profileId"],
            require_success=witness["status"] == "Passed", test_identity=entry["testIdentity"])
        if compositions and inputs["profileId"] != "composition":
            raise ConformanceError("ProofMismatch")
        if inputs["profileId"] == "composition":
            from conformance_case_catalog import composition_snapshot_policy, original_witness_parents, original_witness_policy
            policy = original_witness_policy(entry["testIdentity"])
            if (witness["status"] == "Passed" and policy is not None and policy[0] == "composition"
                    and (len(originals) != len(original_witness_parents(entry["testIdentity"]))
                         or len(compositions) != len(composition_snapshot_policy(entry["testIdentity"])))):
                raise ConformanceError("WitnessMissing")
        if len(origins) + len(originals) + len(arguments) + len(compositions) > 128:
            raise ConformanceError("OutputLimitExceeded")
        if (prior_arguments & (set(prior_sessions) | set(prior_observations))
                or prior_compositions & (set(prior_sessions) | set(prior_observations) | prior_arguments)):
            raise ConformanceError("ProofMismatch")
        session_origins[witness["executionId"]] = origins
        original_observations[witness["executionId"]] = originals
        metadata_arguments[witness["executionId"]] = arguments
        composition_observations[witness["executionId"]] = compositions
        version_observations[witness["executionId"]] = versions
        if ((witness["status"] == "Passed" and (proof["failureKind"] != "None" or proof["assertionSymbol"] is not None))
                or (witness["status"] == "Incomplete"
                    and (proof["failureKind"] != "SkippedOrUnknown" or proof["assertionSymbol"] is not None))
                or (witness["status"] == "Failed" and (
                    proof["failureKind"] not in ("Assertion", "Guard", "Unknown")
                    or (proof["failureKind"] == "Assertion" and (
                        entry["assertionSymbol"] is None or proof["assertionSymbol"] != entry["assertionSymbol"]))
                    or (proof["failureKind"] == "Guard" and (
                        not _inherited_guard_entry(entry) or proof["assertionSymbol"] is not None))
                    or (proof["failureKind"] == "Unknown" and proof["assertionSymbol"] is not None)))):
            raise ConformanceError("ProofMismatch")
        unknown_failure |= proof["failureKind"] == "Unknown"
        guard_failure |= proof["failureKind"] == "Guard"
    completion = _runtime_completion(completion_data, "execution", witnesses_data)
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
            or (guard_failure and code not in ("EvidenceIncomplete", "UnknownDiagnostic"))
            or (code == "AssertionFailed" and (not inventory_complete or not failed or unknown_failure
                or any(item["status"] == "Incomplete" for item in witnesses)))):
        raise ConformanceError("EvidenceIncomplete")
    return inputs, MappingProxyType({
        "witnesses": witnesses, "proofs": MappingProxyType(proof_hashes), "completion": completion,
        "attemptId": manifest["attemptId"], "diagnosticCode": code,
        "sessionOrigins": MappingProxyType(session_origins),
        "originalObservations": MappingProxyType(original_observations),
        "metadataArguments": MappingProxyType(metadata_arguments),
        "compositionObservations": MappingProxyType(composition_observations),
        "versionObservations": MappingProxyType(version_observations),
        "caseIds": tuple(sorted({entry["caseId"] for entry in expected.values()})),
    })


def _catalog_case_result(inputs, case, status, attempts):
    proofs = {proof for attempt in attempts for proof in attempt["proofSha256"]}
    if len(proofs) > MAX_WITNESSES:
        raise ConformanceError("OutputLimitExceeded")
    return admit_entity("CaseResult", {
        "runId": inputs["runId"], "profileId": case.profile_id,
        "bindingId": case.binding_id, "matrixId": case.matrix_id,
        "caseId": case.case_id, "status": status, "attempts": attempts,
        "applicable": case.exclusion is None,
        "exclusionRule": {None: "none", "non-durable fixture": "non-durable-fixture",
                          "simulation: no durable restart": "simulation-no-durable-restart"}[case.exclusion],
        "proofSha256": sorted(proofs),
    })


def composition_case_material(inputs, *, case_id, matrix_id, witnesses, sequence, started_ms, ended_ms):
    from conformance_case_catalog import composition_execution_cases, composition_snapshot_policy, expected_cases

    inputs = admit_entity("RunInputs", inputs)
    if inputs["profileId"] != "composition":
        raise ConformanceError("UnsupportedProfile")
    sequence, started_ms, ended_ms = _integer(sequence), _number(started_ms), _number(ended_ms)
    cases = {case.key: case for case in expected_cases("composition")}
    case = cases.get(("composition", "none", stable_id(matrix_id), stable_id(case_id)))
    if case is None or not case.witnesses:
        raise ConformanceError("WitnessMissing")
    witnesses = _list(_entity("RuntimeWitness"), MAX_WITNESSES)(witnesses)
    selected = {row["testIdentity"]: row for row in witnesses}
    if len(selected) != len(witnesses) or selected.keys() != set(case.witnesses):
        raise ConformanceError("WitnessMissing")
    physical = composition_execution_cases()
    ordered = tuple(selected[identity] for identity in case.witnesses)
    input_sha = digest(inputs)
    if any(
            (case_id, row["matrixId"]) != physical[row["testIdentity"]]
            or row["bindingId"] != "none" or row["status"] != "Passed"
            or row["runId"] != inputs["runId"] or row["invocationGroupId"] != inputs["invocationGroupId"]
            or row["inputSha256"] != input_sha
            or row["startedMs"] < started_ms or row["endedMs"] > ended_ms
            for row in ordered):
        raise ConformanceError("ProofMismatch")
    path = f"proofs/composition-{case_id}-{matrix_id}-attempt-{sequence}.json"
    raw = canonical_bytes({
        "schemaVersion": 1, "qualification": False, "scope": "composition-case-derivation",
        "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "inputSha256": input_sha, "caseId": case_id, "matrixId": matrix_id,
        "sequence": sequence, "startedMs": started_ms, "endedMs": ended_ms,
        "witnesses": ordered,
        "policiesSha256": digest({
            identity: composition_snapshot_policy(identity) for identity in case.witnesses}),
    })
    attempt = admit_entity("Attempt", {
        "sequence": sequence, "startedMs": started_ms, "endedMs": ended_ms, "status": "Passed",
        "witnessIds": [row["executionId"] for row in ordered],
        "proofSha256": sorted({hashlib.sha256(raw).hexdigest(), *(row["proofSha256"] for row in ordered)}),
        "diagnosticCode": "None",
    })
    return MappingProxyType({"attempt": attempt, "sourceProofs": MappingProxyType({path: raw})})


def compatibility_case_material(inputs, *, case_id, matrix_id, witnesses, sequence, started_ms, ended_ms):
    from conformance_case_catalog import (
        architecture_runtime_tests, binary_runtime_tests, expected_cases, version_runtime_tests,
    )

    inputs = admit_entity("RunInputs", inputs)
    if inputs["profileId"] != "compatibility":
        raise ConformanceError("UnsupportedProfile")
    sequence, started_ms, ended_ms = _integer(sequence), _number(started_ms), _number(ended_ms)
    cases = {case.key: case for case in expected_cases("compatibility")}
    case = cases.get(("compatibility", "none", stable_id(matrix_id), stable_id(case_id)))
    if case is None or not case.witnesses:
        raise ConformanceError("WitnessMissing")
    physical = {
        identity: (scope, binding)
        for scope, rows in (("architecture", architecture_runtime_tests()),
                            ("version", version_runtime_tests()), ("binary", binary_runtime_tests()))
        for identity, (binding, _) in rows.items()}
    return _compatibility_case_material(
        inputs, case, physical, witnesses, input_sha=digest(inputs),
        sequence=sequence, started_ms=started_ms, ended_ms=ended_ms)


def _compatibility_baseline(inputs):
    from conformance_baselines import BASELINE

    historical = [row for row in inputs["baselines"] if row["apiScope"] == "f06"]
    if len(historical) != 1:
        raise ConformanceError("EvidenceIncomplete")
    baseline = historical[0]
    binaries = baseline["dependencySha256"]
    if baseline["revision"] != BASELINE or baseline["binarySha256"] != digest(binaries):
        raise ConformanceError("ProofMismatch")
    return baseline


def _compatibility_binary_binding(inputs):
    from conformance_baselines import BASELINE, HISTORICAL_BINARY_IMAGES

    baseline = _compatibility_baseline(inputs)
    binaries = baseline["dependencySha256"]
    if not set(HISTORICAL_BINARY_IMAGES.values()) <= binaries.keys():
        raise ConformanceError("ProofMismatch")
    images = []
    for folder in ("bin/Release/net10.0", "bin/package-diagnostic/Release/net10.0"):
        prefix = "stores/snapshot/tests/contracts/Hoard.Conformance.Tests/" + folder + "/compatibility-fixtures/"
        for target, original in HISTORICAL_BINARY_IMAGES.items():
            runtime = prefix + target
            if inputs["runtimeAssemblies"].get(runtime) != binaries[original]:
                raise ConformanceError("ProofMismatch")
            images.append({"originalPath": original, "runtimePath": runtime, "sha256": binaries[original]})
    return {
        "revision": BASELINE, "sourceSha256": baseline["sourceSha256"],
        "lockSha256": baseline["lockSha256"], "recipeSha256": baseline["recipeSha256"],
        "binarySha256": baseline["binarySha256"], "images": images}


def _compatibility_source_break_binding(inputs):
    from conformance_baselines import SOURCE_BREAK_RUNTIME, SOURCE_BREAK_RUNTIME_FILES

    baseline = _compatibility_baseline(inputs)
    prefixes = tuple(
        "stores/snapshot/tests/contracts/Hoard.Conformance.Tests/" + folder + "/" + SOURCE_BREAK_RUNTIME + "/"
        for folder in ("bin/Release/net10.0", "bin/package-diagnostic/Release/net10.0"))
    scopes = [{path.removeprefix(prefix): hashed for path, hashed in inputs["runtimeAssemblies"].items()
               if path.startswith(prefix)} for prefix in prefixes]
    if (any(scope.keys() != set(SOURCE_BREAK_RUNTIME_FILES) for scope in scopes)
            or scopes[0] != scopes[1]):
        raise ConformanceError("ProofMismatch")
    return {
        "revision": baseline["revision"], "sourceSha256": baseline["sourceSha256"],
        "lockSha256": baseline["lockSha256"], "recipeSha256": baseline["recipeSha256"],
        "runtimeRoots": prefixes, "files": scopes[0]}


def _compatibility_case_material(inputs, case, physical, witnesses, *, input_sha, sequence, started_ms, ended_ms):
    from conformance_case_catalog import version_observation_policy

    witnesses = _list(_entity("RuntimeWitness"), MAX_WITNESSES)(witnesses)
    selected = {row["testIdentity"]: row for row in witnesses}
    if len(selected) != len(witnesses) or selected.keys() != set(case.witnesses):
        raise ConformanceError("WitnessMissing")
    ordered = tuple(selected[identity] for identity in case.witnesses)
    for row in ordered:
        expected = physical.get(row["testIdentity"])
        if (expected is None or row["bindingId"] != expected[1] or row["matrixId"] != expected[0] + "-runtime"
                or row["status"] != "Passed" or row["runId"] != inputs["runId"]
                or row["invocationGroupId"] != inputs["invocationGroupId"] or row["inputSha256"] != input_sha
                or row["startedMs"] < started_ms or row["endedMs"] > ended_ms):
            raise ConformanceError("ProofMismatch")
    path = f"proofs/compatibility-{case.case_id}-{case.matrix_id}-attempt-{sequence}.json"
    historical_binary = (_compatibility_binary_binding(inputs)
                         if (case.case_id, case.matrix_id) == ("COMPATIBILITY", "binary-break") else None)
    source_break = (_compatibility_source_break_binding(inputs)
                    if (case.case_id, case.matrix_id) == ("COMPATIBILITY", "source-break") else None)
    raw = canonical_bytes({
        "schemaVersion": 1, "qualification": False, "scope": "compatibility-case-derivation",
        "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "inputSha256": input_sha, "caseId": case.case_id, "matrixId": case.matrix_id,
        "sequence": sequence, "startedMs": started_ms, "endedMs": ended_ms,
        "witnesses": ordered, "controls": case.controls,
        **({"historicalBinary": historical_binary} if historical_binary is not None else {}),
        **({"sourceBreak": source_break} if source_break is not None else {}),
        "policiesSha256": digest({
            identity: {"runtimeScope": physical[identity][0], "bindingId": physical[identity][1],
                       "versionObservations": version_observation_policy(identity)}
            for identity in case.witnesses}),
    })
    attempt = admit_entity("Attempt", {
        "sequence": sequence, "startedMs": started_ms, "endedMs": ended_ms, "status": "Passed",
        "witnessIds": [row["executionId"] for row in ordered],
        "proofSha256": sorted({hashlib.sha256(raw).hexdigest(), *(row["proofSha256"] for row in ordered)}),
        "diagnosticCode": "None",
    })
    return MappingProxyType({"attempt": attempt, "sourceProofs": MappingProxyType({path: raw})})


def compatibility_quality_case_material(inputs, *, case_id, results, witnesses, sequence, started_ms, ended_ms):
    from conformance_case_catalog import (
        COMPATIBILITY_RUNTIME_QUALITY_SCOPES, architecture_runtime_tests, binary_runtime_tests,
        expected_cases, obligation_controls, version_runtime_tests,
    )

    inputs = admit_entity("RunInputs", inputs)
    if inputs["profileId"] != "compatibility" or case_id not in COMPATIBILITY_RUNTIME_QUALITY_SCOPES:
        raise ConformanceError("UnsupportedProfile")
    sequence, started_ms, ended_ms = _integer(sequence), _number(started_ms), _number(ended_ms)
    scope = COMPATIBILITY_RUNTIME_QUALITY_SCOPES[case_id]
    tests = {"version": version_runtime_tests, "architecture": architecture_runtime_tests,
             "binary": binary_runtime_tests}[scope]()
    cases = tuple(case for case in expected_cases("compatibility")
                  if case.witnesses and set(case.witnesses) <= tests.keys())
    selected = {(row["profileId"], row["bindingId"], row["matrixId"], row["caseId"]): row
                for row in (admit_entity("CaseResult", result) for result in results)}
    executions = {row["testIdentity"]: admit_entity("RuntimeWitness", row) for row in witnesses}
    if (len(selected) != len(results) or len(executions) != len(witnesses)
            or not tests.keys() <= executions.keys()):
        raise ConformanceError("WitnessMissing")
    ordered = tuple(executions[identity] for identity in sorted(tests))
    input_sha = digest(inputs)
    for row in ordered:
        if (row["status"] != "Passed" or row["bindingId"] != tests[row["testIdentity"]][0]
                or row["matrixId"] != scope + "-runtime" or row["runId"] != inputs["runId"]
                or row["invocationGroupId"] != inputs["invocationGroupId"] or row["inputSha256"] != input_sha
                or not started_ms <= row["startedMs"] <= row["endedMs"] <= ended_ms):
            raise ConformanceError("ProofMismatch")
    basis = []
    physical = {identity: (scope, binding) for identity, (binding, _) in tests.items()}
    for case in cases:
        if case.key not in selected:
            raise ConformanceError("WitnessMissing")
        material = _compatibility_case_material(
            inputs, case, physical, [executions[identity] for identity in case.witnesses], input_sha=input_sha,
            sequence=sequence, started_ms=started_ms, ended_ms=ended_ms)
        expected = _catalog_case_result(inputs, case, "Passed", [material["attempt"]])
        if selected[case.key] != expected:
            raise ConformanceError("ProofMismatch")
        basis.append(expected)
    path = f"proofs/compatibility-{case_id}-attempt-{sequence}.json"
    raw = canonical_bytes({
        "schemaVersion": 1, "qualification": False, "scope": "compatibility-quality-derivation",
        "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "inputSha256": input_sha, "caseId": case_id, "sequence": sequence,
        "startedMs": started_ms, "endedMs": ended_ms, "runtimeScope": scope,
        "basis": basis, "witnesses": ordered, "controls": obligation_controls(int(case_id[3:])),
    })
    attempt = admit_entity("Attempt", {
        "sequence": sequence, "startedMs": started_ms, "endedMs": ended_ms, "status": "Passed",
        "witnessIds": [row["executionId"] for row in ordered],
        "proofSha256": sorted({hashlib.sha256(raw).hexdigest(), *(row["proofSha256"] for row in ordered)}),
        "diagnosticCode": "None",
    })
    return MappingProxyType({"attempt": attempt, "sourceProofs": MappingProxyType({path: raw})})


def composition_quality_case_material(inputs, *, case_id, results, witnesses, sequence, started_ms, ended_ms):
    from conformance_case_catalog import COMPOSITION_QUALITY_BASIS, expected_cases, obligation_controls

    inputs = admit_entity("RunInputs", inputs)
    if inputs["profileId"] != "composition" or case_id not in COMPOSITION_QUALITY_BASIS:
        raise ConformanceError("UnsupportedProfile")
    sequence, started_ms, ended_ms = _integer(sequence), _number(started_ms), _number(ended_ms)
    basis_ids = {f"CP-{number:02}" for number in COMPOSITION_QUALITY_BASIS[case_id]}
    cases = tuple(case for case in expected_cases("composition") if case.case_id in basis_ids)
    selected = {(row["profileId"], row["bindingId"], row["matrixId"], row["caseId"]): row for row in results}
    executions = {row["testIdentity"]: row for row in witnesses}
    if len(selected) != len(results) or len(executions) != len(witnesses) or not cases:
        raise ConformanceError("WitnessMissing")
    basis, proofs, identities = [], set(), set()
    for case in cases:
        if case.key not in selected or not set(case.witnesses) <= executions.keys():
            raise ConformanceError("WitnessMissing")
        material = composition_case_material(
            inputs, case_id=case.case_id, matrix_id=case.matrix_id,
            witnesses=[executions[identity] for identity in case.witnesses],
            sequence=sequence, started_ms=started_ms, ended_ms=ended_ms)
        expected = _catalog_case_result(inputs, case, "Passed", [material["attempt"]])
        if selected[case.key] != expected:
            raise ConformanceError("ProofMismatch")
        basis.append(expected)
        proofs.update(material["attempt"]["proofSha256"])
        identities.update(case.witnesses)
    ordered = tuple(executions[identity] for identity in sorted(identities))
    path = f"proofs/composition-{case_id}-attempt-{sequence}.json"
    raw = canonical_bytes({
        "schemaVersion": 1, "qualification": False, "scope": "composition-quality-derivation",
        "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "inputSha256": digest(inputs), "caseId": case_id, "sequence": sequence,
        "startedMs": started_ms, "endedMs": ended_ms, "basis": basis,
        "controls": obligation_controls(int(case_id[3:])),
    })
    attempt = admit_entity("Attempt", {
        "sequence": sequence, "startedMs": started_ms, "endedMs": ended_ms, "status": "Passed",
        "witnessIds": [row["executionId"] for row in ordered],
        "proofSha256": sorted({hashlib.sha256(raw).hexdigest(), *proofs}), "diagnosticCode": "None",
    })
    return MappingProxyType({"attempt": attempt, "sourceProofs": MappingProxyType({path: raw})})


def _direct_category_quality_composition(inputs, results, witnesses, *, case_id, expected,
                                         sequence, started_ms, ended_ms):
    result = results.get((inputs["profileId"], "none", "none", case_id))
    attempts = () if result is None else result["attempts"]
    current = None if len(attempts) < sequence else attempts[sequence - 1]
    if current is not None and (
            result["runId"] != inputs["runId"] or current["sequence"] != sequence
            or current["startedMs"] != started_ms or current["endedMs"] != ended_ms):
        raise ConformanceError("ProofMismatch")
    selected_ids = () if current is None else current["witnessIds"]
    prior_ids = {execution for attempt in attempts[:sequence - 1] for execution in attempt["witnessIds"]}
    if set(selected_ids) & prior_ids or not set(selected_ids) <= witnesses.keys():
        raise ConformanceError("ProofMismatch")
    selected = tuple(sorted((witnesses[execution] for execution in selected_ids), key=lambda row: row["executionId"]))
    identities = {row["testIdentity"] for row in selected}
    if (len(identities) != len(selected)
            or any(row["testIdentity"] not in expected
                   or row["bindingId"] != expected[row["testIdentity"]]
                   or row["matrixId"] != "none"
                   or not started_ms <= row["startedMs"] <= row["endedMs"] <= ended_ms for row in selected)):
        raise ConformanceError("ProofMismatch")
    complete = identities == expected.keys() and all(row["status"] == "Passed" for row in selected)
    if case_id == "QC-05":
        complete &= current is not None and current["status"] == "Passed"
    runtime_proofs = {row["proofSha256"] for row in selected}
    parents = set() if current is None else set(current["proofSha256"]) - runtime_proofs
    complete &= len(parents) == 1
    failed = any(row["status"] == "Failed" for row in selected)
    status = "Failed" if failed else "Passed" if complete else "Incomplete"
    return MappingProxyType({
        "attempt": admit_entity("Attempt", {
            "sequence": sequence, "startedMs": started_ms, "endedMs": ended_ms, "status": status,
            "diagnosticCode": "AssertionFailed" if failed else "None" if complete else "EvidenceIncomplete",
            "witnessIds": tuple(row["executionId"] for row in selected),
            "proofSha256": sorted(runtime_proofs | parents),
        }),
        "sourceProofs": MappingProxyType({}),
    })


def _parameter_pairing_scope(witnesses, proofs, expected, receipt_prefix, *, started_ms, ended_ms):
    selected = sorted((row for row in witnesses
                       if (row["bindingId"], row["testIdentity"]) in expected
                       and started_ms <= row["startedMs"] <= row["endedMs"] <= ended_ms),
                      key=lambda row: (row["bindingId"], row["testIdentity"]))
    if (len(selected) != len(expected)
            or {(row["bindingId"], row["testIdentity"]) for row in selected} != expected
            or len({row["executionId"] for row in selected}) != len(selected)
            or any(row["status"] != "Passed" for row in selected)):
        raise ConformanceError("WitnessMissing")
    attempts = set()
    for row in selected:
        paths = [path for path, hashed in proofs.items()
                 if path.endswith(f'/proof-{row["executionId"]}.json') and hashed == row["proofSha256"]]
        if len(paths) != 1 or not re.fullmatch(r"runtime-[0-9a-f-]{36}/proof-[0-9a-f-]{36}\.json", paths[0]):
            raise ConformanceError("ProofMismatch")
        attempts.add(_uuid(paths[0].split("/")[0].removeprefix("runtime-")))
    if len(attempts) != 1:
        raise ConformanceError("ProofMismatch")
    attempt = next(iter(attempts))
    parent = f"proofs/category-source-{attempt}.json"
    receipt = f"proofs/category-{receipt_prefix}-{attempt}.json"
    if parent not in proofs or receipt not in proofs:
        raise ConformanceError("WitnessMissing")
    return {
        "attemptId": attempt, "sourceParentSha256": proofs[parent],
        "sourceReceiptSha256": proofs[receipt], "witnessesSha256": digest(selected)}


def metadata_parameter_pairing_material(inputs, witnesses, proofs, *, sequence, started_ms, ended_ms):
    from conformance_case_catalog import ORIGINAL_METADATA_WITNESSES

    started_ms, ended_ms = float(_number(started_ms)), float(_number(ended_ms))
    if inputs["profileId"] != "metadata" or inputs["mode"] != "qualification":
        raise ConformanceError("ProofMismatch")
    shared = "proofs/qualification-metadata-shared-consumer-native-executions.json"
    if shared not in proofs:
        raise ConformanceError("WitnessMissing")
    witnesses = tuple(witnesses)
    bindings = [{
        "bindingId": binding,
        **_parameter_pairing_scope(
            witnesses, proofs, {(binding, identity) for identity in ORIGINAL_METADATA_WITNESSES},
            "metadata-original-" + binding, started_ms=started_ms, ended_ms=ended_ms)}
        for binding in ("memory", "sqlite")]
    if (len({row["attemptId"] for row in bindings}) != 2
            or len({row["sourceParentSha256"] for row in bindings}) != 2):
        raise ConformanceError("ProofMismatch")
    return canonical_bytes({
        "schemaVersion": 1, "qualification": False, "mode": "metadata-parameter-pairing",
        "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "inputsSha256": digest(inputs), "sequence": sequence, "startedMs": started_ms, "endedMs": ended_ms,
        "sharedConsumerSourceSha256": proofs[shared], "bindings": bindings})


def artifact_parameter_pairing_material(inputs, witnesses, proofs, *, sequence, started_ms, ended_ms):
    from conformance_case_catalog import category_execution_partitions

    started_ms, ended_ms = float(_number(started_ms)), float(_number(ended_ms))
    if inputs["profileId"] != "artifacts" or inputs["mode"] != "qualification":
        raise ConformanceError("ProofMismatch")
    shared = "proofs/qualification-artifacts-shared-consumer-native-executions.json"
    if shared not in proofs:
        raise ConformanceError("WitnessMissing")
    witnesses = tuple(witnesses)
    partitions = category_execution_partitions("artifacts", mode="qualification")
    scopes = [{
        "scopeId": scope,
        **_parameter_pairing_scope(
            witnesses, proofs, set(partitions[scope]), "artifacts-" + scope,
            started_ms=started_ms, ended_ms=ended_ms)}
        for scope in ("original", "original-local", "original-object")]
    if (len({row["attemptId"] for row in scopes}) != 3
            or len({row["sourceParentSha256"] for row in scopes}) != 3):
        raise ConformanceError("ProofMismatch")
    return canonical_bytes({
        "schemaVersion": 1, "qualification": False, "mode": "artifacts-parameter-pairing",
        "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "inputsSha256": digest(inputs), "sequence": sequence, "startedMs": started_ms, "endedMs": ended_ms,
        "sharedConsumerSourceSha256": proofs[shared], "scopes": scopes})


def _category_quality_composition(inputs, case_id, results, witnesses, *, sequence, started_ms, ended_ms,
                                  proof_registry=MappingProxyType({})):
    """Compose only the exact current-attempt basis; never relabel its executions."""
    from conformance_case_catalog import (
        AUTHORITY_INTEGRATION_ROWS, CATEGORY_QUALITY_BASIS, METADATA_INVENTORY_SOURCE_WITNESSES,
        METADATA_RECOVERY_SOURCE_WITNESS,
        ORIGINAL_ARTIFACT_PROOF_SOURCES, ORIGINAL_INSPECTION_WITNESSES, ORIGINAL_METADATA_WITNESSES,
        category_cases, category_execution_partitions, category_mutation_witnesses,
        hook_admission_tests,
    )

    profile = inputs["profileId"]
    quality_basis = CATEGORY_QUALITY_BASIS.get(profile, {})
    if inputs["mode"] != "qualification" or case_id not in quality_basis:
        raise ConformanceError("ProofMismatch")
    if case_id in ("QC-04", "QC-05") or profile == "artifacts" and case_id == "QC-12":
        expected = (category_mutation_witnesses(profile, corrected=True) if case_id == "QC-04" else
                    {identity: binding for identity, (binding, _) in hook_admission_tests(profile).items()}
                    if case_id == "QC-05" else
                    {identity: row[0] for identity, row in AUTHORITY_INTEGRATION_ROWS.items()})
        return _direct_category_quality_composition(
            inputs, results, witnesses, case_id=case_id, expected=expected,
            sequence=sequence, started_ms=started_ms, ended_ms=ended_ms)
    required = tuple(case for case in category_cases()
                     if case.profile_id == profile and int(case.case_id[3:]) in quality_basis[case_id])
    complete, failure, executions, proofs = True, None, set(), set()
    basis, packets = [], {}
    authorities = set(ORIGINAL_ARTIFACT_PROOF_SOURCES) | set(ORIGINAL_INSPECTION_WITNESSES)
    pairing_parents = {}
    if (profile, case_id) in (("metadata", "QC-02"), ("artifacts", "QC-03")):
        pair_path = f"proofs/category-{profile}-parameters-{sequence:04}.json"
        if pair_path not in proof_registry:
            complete = False
        else:
            raw = (metadata_parameter_pairing_material if profile == "metadata" else artifact_parameter_pairing_material)(
                inputs, witnesses.values(), proof_registry, sequence=sequence, started_ms=started_ms, ended_ms=ended_ms)
            hashed = hashlib.sha256(raw).hexdigest()
            if proof_registry[pair_path] != hashed:
                raise ConformanceError("ProofMismatch")
            proofs.add(hashed)
            paired = load_json(raw)
            if profile == "metadata":
                pairing_parents = {(row["bindingId"], identity): row["sourceParentSha256"]
                                   for row in paired["bindings"] for identity in ORIGINAL_METADATA_WITNESSES}
            else:
                partitions = category_execution_partitions("artifacts", mode="qualification")
                pairing_parents = {key: row["sourceParentSha256"] for row in paired["scopes"]
                                   for key in partitions[row["scopeId"]]}
        if profile == "metadata":
            authorities = {identity for identity in ORIGINAL_METADATA_WITNESSES if ".MP46_" in identity}
    for case in required:
        row = {"key": case.key, "exclusion": case.exclusion, "attempt": None}
        basis.append(row)
        result = results.get(case.key)
        if result is None:
            complete = False
            continue
        if (result["runId"] != inputs["runId"] or (
                result["profileId"], result["bindingId"], result["matrixId"], result["caseId"]) != case.key):
            raise ConformanceError("ProofMismatch")
        if case.exclusion is not None:
            if result != _catalog_case_result(inputs, case, "NotApplicable", ()):
                raise ConformanceError("ProofMismatch")
            continue
        if not result["applicable"] or result["exclusionRule"] != "none":
            raise ConformanceError("ProofMismatch")
        if len(result["attempts"]) < sequence:
            complete = False
            continue
        attempt = result["attempts"][sequence - 1]
        row["attempt"] = attempt
        if (attempt["sequence"] != sequence
                or not started_ms <= attempt["startedMs"] <= attempt["endedMs"] <= ended_ms):
            raise ConformanceError("ProofMismatch")
        observed = tuple(witnesses.get(execution) for execution in attempt["witnessIds"])
        if any(witness is None or witness["bindingId"] != case.binding_id
               or witness["matrixId"] != case.matrix_id or witness["proofSha256"] not in attempt["proofSha256"]
               or not attempt["startedMs"] <= witness["startedMs"] <= witness["endedMs"] <= attempt["endedMs"]
               for witness in observed):
            raise ConformanceError("ProofMismatch")
        expected = set(case.witnesses)
        if not expected and profile == "metadata" and case.case_id == "MP-48":
            expected.add(METADATA_INVENTORY_SOURCE_WITNESSES[case.binding_id])
        if not expected and case.binding_id == "sqlite" and (
                "verified-recovery-walkthrough" in case.controls
                or any(control.startswith("parent-kill:") for control in case.controls)):
            expected.add(METADATA_RECOVERY_SOURCE_WITNESS)
        if attempt["status"] == "Passed" and (
                len(observed) != len(expected) or {row["testIdentity"] for row in observed} != expected
                or any(row["status"] != "Passed" for row in observed)):
            raise ConformanceError("WitnessMissing")
        if (profile == "artifacts" and expected & authorities and attempt["status"] == "Passed"
                and not set(attempt["proofSha256"]) - {row["proofSha256"] for row in observed}):
            raise ConformanceError("ProofMismatch")
        if (pairing_parents and attempt["status"] == "Passed"
                and not {pairing_parents[case.binding_id, identity] for identity in expected
                         if (case.binding_id, identity) in pairing_parents} <= set(attempt["proofSha256"])):
            raise ConformanceError("ProofMismatch")
        complete &= attempt["status"] == "Passed"
        if attempt["status"] == "Failed" and failure is None:
            failure = attempt["diagnosticCode"]
        executions.update(attempt["witnessIds"])
        proofs.update(attempt["proofSha256"])
    code = failure or ("None" if complete and executions and proofs else "EvidenceIncomplete")
    if (profile, case_id) in (("artifacts", "QC-03"), ("artifacts", "QC-09"), ("metadata", "QC-02")):
        raw = canonical_bytes({
            "schemaVersion": 1, "qualification": False, "mode": "category-quality-basis",
            "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
            "profileId": profile, "caseId": case_id, "inputsSha256": digest(inputs),
            "sequence": sequence, "startedMs": started_ms, "endedMs": ended_ms,
            "basis": basis, "witnesses": [witnesses[execution] for execution in sorted(executions)]})
        if len(raw) > MAX_REPORT_BYTES:
            raise ConformanceError("OutputLimitExceeded")
        packets[f"proofs/category-{profile}-{case_id}-basis-{sequence:04}.json"] = raw
        runtime_hashes = {witnesses[execution]["proofSha256"] for execution in executions}
        executions = {execution for execution in executions if witnesses[execution]["testIdentity"] in authorities}
        proofs = ((proofs - runtime_hashes) | {witnesses[execution]["proofSha256"] for execution in executions}
                  | {hashlib.sha256(raw).hexdigest()})
    attempt = admit_entity("Attempt", {
        "sequence": sequence, "startedMs": started_ms, "endedMs": ended_ms,
        "status": "Passed" if code == "None" else failure_status(code), "diagnosticCode": code,
        "witnessIds": sorted(executions), "proofSha256": sorted(proofs),
    })
    return MappingProxyType({"attempt": attempt, "sourceProofs": MappingProxyType(packets)})


def _origin_input_assignments(origin_inputs):
    if origin_inputs is None:
        return None
    if not isinstance(origin_inputs, Mapping) or len(origin_inputs) > 128:
        raise ConformanceError("EvidenceIncomplete")
    frozen = {}
    for origin_binding, assignments in origin_inputs.items():
        stable_id(origin_binding)
        if not isinstance(assignments, Mapping) or len(assignments) > 8:
            raise ConformanceError("EvidenceIncomplete")
        captured = {}
        for role, assignment in assignments.items():
            stable_id(role)
            if not isinstance(assignment, tuple) or len(assignment) != 2:
                raise ConformanceError("EvidenceIncomplete")
            path, package = assignment
            relative_path(path)
            if package is not None:
                stable_id(package)
            captured[role] = assignment
        frozen[origin_binding] = MappingProxyType(captured)
    return MappingProxyType(frozen)


def original_node_assignments(identity, assignments):
    """Freeze exact component images for each independently selected forest node."""
    from conformance_case_catalog import ORIGINAL_ARTIFACT_REOPENS, original_witness_parents, original_witness_policy
    parents = original_witness_parents(identity)
    if parents is None or identity in ORIGINAL_ARTIFACT_REOPENS and isinstance(assignments, Mapping):
        raise ConformanceError("EvidenceIncomplete")
    nodes = (assignments,) * len(parents) if isinstance(assignments, Mapping) else assignments
    if not isinstance(nodes, (tuple, list)) or len(nodes) != len(parents):
        raise ConformanceError("EvidenceIncomplete")
    roles = original_witness_policy(identity)[2]
    if any(not isinstance(node, Mapping) or set(node) != set(roles) for node in nodes):
        raise ConformanceError("EvidenceIncomplete")
    return tuple(_origin_input_assignments({"original": node})["original"] for node in nodes)


def _original_input_assignments(original_inputs):
    if original_inputs is None:
        return None
    if not isinstance(original_inputs, Mapping) or len(original_inputs) > 128:
        raise ConformanceError("EvidenceIncomplete")
    frozen = {}
    count = 0
    for binding, witnesses in original_inputs.items():
        stable_id(binding)
        if not isinstance(witnesses, Mapping):
            raise ConformanceError("EvidenceIncomplete")
        count += len(witnesses)
        if count > MAX_RESULTS:
            raise ConformanceError("EvidenceIncomplete")
        frozen[binding] = MappingProxyType({
            _runtime_identity(identity): original_node_assignments(identity, roles)
            for identity, roles in witnesses.items()})
    return MappingProxyType(frozen)


def _runtime_provenance_state(observed, used, prior_instances):
    observations = [*(
        (origin["sessionId"], origin) for origins in observed["sessionOrigins"].values() for origin in origins), *(
        (origin["observationId"], origin) for origins in observed["originalObservations"].values() for origin in origins)]
    calls = tuple(argument["callId"] for arguments in observed.get("metadataArguments", {}).values()
                  for argument in arguments)
    compositions = tuple(row["observationId"] for rows in observed.get("compositionObservations", {}).values()
                         for row in rows)
    ids = frozenset((*[identity for identity, _ in observations], *calls, *compositions))
    if len(ids) != len(observations) + len(calls) + len(compositions) or ids & used:
        raise ConformanceError("ProofMismatch")
    instances = dict(prior_instances)
    for _, origin in observations:
        for captured in origin["components"].values():
            _observe_component_instance(instances, captured)
    return ids, instances


class RuntimeCaseHistory:
    """Append-only runtime-bearing case state selected from the independent catalog."""

    def __init__(self, inputs, *, binding_id, matrix_id, case_id, max_attempts=1, origin_inputs=None,
                 original_inputs=None):
        from conformance_case_catalog import expected_cases
        self._inputs = admit_entity("RunInputs", inputs)
        self._session_origins = MappingProxyType({})
        self._original_observations = MappingProxyType({})
        self._metadata_arguments = MappingProxyType({})
        self._composition_observations = MappingProxyType({})
        self._used_sessions = frozenset()
        self._instances = {}
        self._origin_inputs = _origin_input_assignments(origin_inputs)
        self._original_inputs = _original_input_assignments(original_inputs)
        key = (self._inputs["profileId"], stable_id(binding_id), stable_id(matrix_id), stable_id(case_id))
        matches = tuple(case for case in expected_cases(key[0]) if case.key == key)
        if len(matches) != 1:
            raise ConformanceError("WitnessMissing")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
            raise ConformanceError()
        if binding_id != "none" and not any(
                binding["bindingId"] == binding_id for binding in self._inputs["bindings"]):
            raise ConformanceError("InputChanged")
        self._case = matches[0]
        self._max_attempts = max_attempts
        self._attempts = ()
        self._witnesses = ()
        self._proofs = MappingProxyType({})
        self._active = None
        self._used_attempts = frozenset()
        self._used_executions = frozenset()
        self._state = "NotApplicable" if self._case.exclusion is not None else "Expected"
        self._result = self._make_result("NotApplicable", ()) if self._case.exclusion is not None else None

    @property
    def state(self):
        return self._state

    @property
    def witnesses(self):
        return self._witnesses

    @property
    def proofs(self):
        return self._proofs

    @property
    def session_origins(self):
        return self._session_origins

    @property
    def original_observations(self):
        return self._original_observations

    @property
    def metadata_arguments(self):
        return self._metadata_arguments

    @property
    def composition_observations(self):
        return self._composition_observations

    def begin(self, attempt_id):
        attempt_id = _uuid(attempt_id)
        if (self._state in ("Running", "NotApplicable") or len(self._attempts) >= self._max_attempts
                or attempt_id in self._used_attempts or not self._case.witnesses):
            raise ConformanceError("EvidenceIncomplete")
        started = _number(time.monotonic() * 1000)
        if self._attempts and started < self._attempts[-1]["endedMs"]:
            raise ConformanceError("EvidenceIncomplete")
        self._used_attempts = self._used_attempts | {attempt_id}
        self._active = attempt_id, started
        self._state = "Running"
        return len(self._attempts) + 1

    def _make_result(self, status, attempts):
        return _catalog_case_result(self._inputs, self._case, status, attempts)

    def _append(self, code, ended, witnesses=(), proofs=MappingProxyType({})):
        status = "Passed" if code == "None" else failure_status(code)
        attempt = admit_entity("Attempt", {
            "sequence": len(self._attempts) + 1, "startedMs": self._active[1], "endedMs": ended,
            "status": status, "diagnosticCode": code,
            "witnessIds": tuple(witness["executionId"] for witness in witnesses),
            "proofSha256": sorted(set(proofs.values())),
        })
        result = self._make_result(status, (*self._attempts, attempt))
        self._attempts = result["attempts"]
        self._witnesses = (*self._witnesses, *witnesses)
        self._proofs = MappingProxyType({**self._proofs, **proofs})
        self._used_executions = self._used_executions | set(attempt["witnessIds"])
        self._result = result
        self._state = status
        self._active = None

    def finish(self, *, manifest_data, owner_data, witnesses_data, proofs, completion_data,
               manifest_sha256, owner_sha256):
        if self._active is None:
            raise ConformanceError("OwnershipInvalid")
        ended = _number(time.monotonic() * 1000)
        try:
            observed = ingest_runtime_attempt(
                inputs=self._inputs, manifest_data=manifest_data, owner_data=owner_data,
                witnesses_data=witnesses_data, proofs=proofs, completion_data=completion_data,
                manifest_sha256=manifest_sha256, owner_sha256=owner_sha256,
                expected_tests={identity: (self._case.binding_id, self._case.matrix_id)
                                for identity in self._case.witnesses},
                started_ms=self._active[1], ended_ms=ended, origin_inputs=self._origin_inputs,
                original_inputs=self._original_inputs)
            if (observed["attemptId"] != self._active[0]
                    or observed["completion"]["attemptSequence"] != len(self._attempts) + 1
                    or observed["caseIds"] != (self._case.case_id,)
                    or any(witness["executionId"] in self._used_executions for witness in observed["witnesses"])):
                raise ConformanceError("ProofMismatch")
            sessions, instances = _runtime_provenance_state(observed, self._used_sessions, self._instances)
            code = observed["diagnosticCode"]
            if code == "None" and self._case.controls:
                code = "EvidenceIncomplete"
            self._append(code, ended, observed["witnesses"], observed["proofs"])
            self._session_origins = MappingProxyType({**self._session_origins, **observed["sessionOrigins"]})
            self._original_observations = MappingProxyType({
                **self._original_observations, **observed["originalObservations"]})
            self._metadata_arguments = MappingProxyType({
                **self._metadata_arguments, **observed["metadataArguments"]})
            self._composition_observations = MappingProxyType({
                **self._composition_observations, **observed["compositionObservations"]})
            self._used_sessions = self._used_sessions | sessions
            self._instances = instances
        except ConformanceError as error:
            if self._active is not None:
                self._append(str(error), ended)
            raise
        return self.result()

    def interrupt(self, code):
        if self._active is None:
            raise ConformanceError("OwnershipInvalid")
        if code not in DIAGNOSTIC_CODES or code == "None":
            raise ConformanceError()
        self._append(code, _number(time.monotonic() * 1000))
        return self.result()

    def result(self):
        if self._state in ("Expected", "Running") or self._result is None:
            raise ConformanceError("EvidenceIncomplete")
        return self._result


class CategoryRuntimeHistory:
    """Import complete frozen binding batches without inventing controller proofs."""

    def __init__(self, inputs, *, max_attempts=1, origin_inputs=None, original_inputs=None, native_sources=None):
        from conformance_case_catalog import CATEGORY_BINDING_SLOTS, expected_cases
        self._inputs = admit_entity("RunInputs", inputs)
        if native_sources is not None:
            from conformance_sources import NativeCategorySources
            if type(native_sources) is not NativeCategorySources or self._inputs["mode"] != "qualification":
                raise ConformanceError("OwnershipInvalid")
        self._native_sources = native_sources
        profile = self._inputs["profileId"]
        if profile not in ("metadata", "artifacts"):
            raise ConformanceError("UnsupportedProfile")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
            raise ConformanceError()
        self._cases = expected_cases(profile)
        self._bindings = {case.binding_id for case in self._cases}
        selected = {binding["bindingId"]: binding for binding in self._inputs["bindings"]
                    if binding["category"] == profile}
        packages = {slot[1]: slot[3] for slot in CATEGORY_BINDING_SLOTS if slot[0] == profile}
        if (set(selected) != self._bindings - {"none"} or any(
                binding["package"]["packageId"].casefold() != packages[binding_id].casefold()
                for binding_id, binding in selected.items())):
            raise ConformanceError("BindingInvalid")
        self._origin_inputs = _origin_input_assignments(origin_inputs)
        self._original_inputs = _original_input_assignments(original_inputs)
        self._max_attempts = max_attempts
        self._active = {}
        self._partitions = {}
        self._joint_plan = None
        self._joint_origin = None
        self._sequences = {binding: 0 for binding in self._bindings}
        self._used_attempts = frozenset()
        self._used_executions = frozenset()
        self._used_sessions = frozenset()
        self._instances = {}
        self._witnesses = ()
        self._proofs = MappingProxyType({})
        self._proof_bytes = 0
        self._quality_proofs = MappingProxyType({})
        self._session_origins = MappingProxyType({})
        self._original_observations = MappingProxyType({})
        self._metadata_arguments = MappingProxyType({})
        self._results = {case.key: _catalog_case_result(self._inputs, case, "NotApplicable", ())
                         for case in self._cases if case.exclusion is not None}

    @property
    def witnesses(self):
        return self._witnesses

    @property
    def proofs(self):
        return self._proofs

    @property
    def session_origins(self):
        return self._session_origins

    @property
    def original_observations(self):
        return self._original_observations

    @property
    def metadata_arguments(self):
        return self._metadata_arguments

    @property
    def quality_proofs(self):
        return self._quality_proofs

    def expected_runtime_tests(self, binding_id):
        """Select primary owned cases before building the runtime manifest."""
        from conformance_case_catalog import category_runtime_cases
        binding_id = stable_id(binding_id)
        if binding_id not in self._bindings:
            raise ConformanceError("BindingInvalid")
        return category_runtime_cases(self._inputs["profileId"], binding_id, mode=self._inputs["mode"])

    def runtime_partitions(self, binding_id):
        binding_id = stable_id(binding_id)
        if binding_id not in self._active or self._joint_plan is not None:
            raise ConformanceError("OwnershipInvalid")
        return self._partitions[binding_id]

    def begin(self, binding_id, attempt_id, *, partitions=None):
        binding_id, attempt_id = stable_id(binding_id), _uuid(attempt_id)
        if self._joint_plan is not None:
            raise ConformanceError("OwnershipInvalid")
        if (binding_id not in self._bindings or binding_id in self._active
                or self._sequences[binding_id] >= self._max_attempts or attempt_id in self._used_attempts):
            raise ConformanceError("EvidenceIncomplete")
        identities = self.expected_runtime_tests(binding_id)
        if partitions is None:
            plan = {"all": MappingProxyType({"attemptId": attempt_id, "tests": identities})}
        else:
            if not isinstance(partitions, Mapping) or not 0 < len(partitions) <= 128:
                raise ConformanceError("EvidenceIncomplete")
            plan, selected = {}, set()
            for scope_id, tests in partitions.items():
                scope_id = stable_id(scope_id)
                if not isinstance(tests, (tuple, list)) or not 0 < len(tests) <= MAX_RESULTS:
                    raise ConformanceError("EvidenceIncomplete")
                tests = tuple(_runtime_identity(identity) for identity in tests)
                if len(set(tests)) != len(tests) or selected.intersection(tests) or not set(tests) <= identities.keys():
                    raise ConformanceError("WitnessMissing")
                selected.update(tests)
                plan[scope_id] = MappingProxyType({
                    "attemptId": str(uuid.uuid4()),
                    "tests": MappingProxyType({identity: identities[identity] for identity in tests}),
                })
            if selected != identities.keys():
                raise ConformanceError("WitnessMissing")
        attempts = {scope["attemptId"] for scope in plan.values()}
        if (len(attempts) != len(plan) or attempts & self._used_attempts
                or (partitions is not None and attempt_id in attempts)):
            raise ConformanceError("ProofMismatch")
        started = _number(time.monotonic() * 1000)
        prior = [attempt["endedMs"] for case in self._cases if case.binding_id == binding_id
                 for attempt in self._results.get(case.key, {}).get("attempts", ())]
        if prior and started < max(prior):
            raise ConformanceError("EvidenceIncomplete")
        self._active[binding_id] = attempt_id, started
        self._partitions[binding_id] = MappingProxyType(plan)
        self._used_attempts = self._used_attempts | attempts | {attempt_id}
        return self._sequences[binding_id] + 1

    def begin_joint(self, attempt_id, *, partitions):
        attempt_id = _uuid(attempt_id)
        if (self._active or self._joint_plan is not None or attempt_id in self._used_attempts
                or len(set(self._sequences.values())) != 1
                or any(sequence >= self._max_attempts for sequence in self._sequences.values())):
            raise ConformanceError("EvidenceIncomplete")
        if not isinstance(partitions, Mapping) or not 0 < len(partitions) <= 128:
            raise ConformanceError("EvidenceIncomplete")
        expected = {(binding, identity): case_id for binding in self._bindings
                    for identity, case_id in self.expected_runtime_tests(binding).items()}
        selected, plan = set(), {}
        for scope_id, rows in partitions.items():
            scope_id = stable_id(scope_id)
            if not isinstance(rows, (tuple, list)) or not 0 < len(rows) <= MAX_RESULTS:
                raise ConformanceError("EvidenceIncomplete")
            tests = {}
            for row in rows:
                if not isinstance(row, (tuple, list)) or len(row) != 2:
                    raise ConformanceError()
                binding, identity = stable_id(row[0]), _runtime_identity(row[1])
                pair = binding, identity
                if pair not in expected or pair in selected or identity in tests:
                    raise ConformanceError("WitnessMissing")
                tests[identity] = binding, expected[pair]
                selected.add(pair)
            plan[scope_id] = MappingProxyType({
                "attemptId": str(uuid.uuid4()), "tests": MappingProxyType(tests)})
        if selected != expected.keys():
            raise ConformanceError("WitnessMissing")
        attempts = {scope["attemptId"] for scope in plan.values()}
        if len(attempts) != len(plan) or attempts & self._used_attempts or attempt_id in attempts:
            raise ConformanceError("ProofMismatch")
        started = _number(time.monotonic() * 1000)
        prior = [attempt["endedMs"] for result in self._results.values() for attempt in result["attempts"]]
        if prior and started < max(prior):
            raise ConformanceError("EvidenceIncomplete")
        self._joint_plan = MappingProxyType(plan)
        self._active = {binding: (attempt_id, started) for binding in self._bindings}
        self._partitions = {binding: MappingProxyType({}) for binding in self._bindings}
        self._used_attempts = self._used_attempts | attempts | {attempt_id}
        return next(iter(self._sequences.values())) + 1

    def joint_partitions(self):
        if self._joint_plan is None:
            raise ConformanceError("OwnershipInvalid")
        return self._joint_plan

    def _case_results(self, binding_id, code, ended, witnesses, source_parents=None, control_proofs=None):
        from conformance_case_catalog import (
            METADATA_INVENTORY_SOURCE_WITNESSES, METADATA_RECOVERY_SOURCE_WITNESS, ORIGINAL_ARTIFACT_PROOF_SOURCES,
        )

        results = {}
        for case in self._cases:
            if case.binding_id != binding_id or case.exclusion is not None:
                continue
            selected = tuple(witness for witness in witnesses
                             if witness["bindingId"] == binding_id and witness["testIdentity"] in case.witnesses)
            if binding_id == "none" and (case.case_id in ("QC-04", "QC-05")
                                        or self._inputs["profileId"] == "artifacts" and case.case_id == "QC-12"):
                selected = tuple(witness for witness in witnesses if witness["testIdentity"] in case.witnesses
                                 and (witness["status"] != "Passed"
                                      or source_parents is not None and witness["executionId"] in source_parents))
            expected = set(case.witnesses)
            source_identity = (
                METADATA_INVENTORY_SOURCE_WITNESSES[binding_id] if case.case_id == "MP-48" else
                METADATA_RECOVERY_SOURCE_WITNESS if binding_id == "sqlite" and (
                    "verified-recovery-walkthrough" in case.controls
                    or any(control.startswith("parent-kill:") for control in case.controls)) else None
            ) if self._inputs["profileId"] == "metadata" else None
            if (self._inputs["mode"] == "qualification" and self._inputs["profileId"] == "metadata"
                    and source_identity is not None and case.controls and not case.witnesses
                    and control_proofs is not None and set(case.controls) <= control_proofs.keys()
                    and source_parents is not None):
                source = tuple(witness for witness in witnesses
                               if witness["bindingId"] == binding_id
                               and witness["testIdentity"] == source_identity
                               and witness["executionId"] in source_parents)
                selected = (*selected, *source)
                if source:
                    expected.add(source_identity)
            case_code = code
            if code in ("None", "AssertionFailed"):
                if any(witness["status"] == "Failed" for witness in selected):
                    case_code = "AssertionFailed"
                elif (not selected
                      or any(control_proofs is None or control not in control_proofs for control in case.controls)
                      or self._inputs["profileId"] == "artifacts" and self._inputs["mode"] == "qualification" and any(
                          witness["testIdentity"] in ORIGINAL_ARTIFACT_PROOF_SOURCES
                          and (source_parents is None or witness["executionId"] not in source_parents)
                          for witness in selected)
                      or {witness["testIdentity"] for witness in selected} != expected
                      or any(witness["status"] != "Passed" for witness in selected)):
                    case_code = "EvidenceIncomplete"
                else:
                    case_code = "None"
            status = "Passed" if case_code == "None" else failure_status(case_code)
            proof_hashes = {witness["proofSha256"] for witness in selected}
            if source_parents is not None:
                proof_hashes.update(source_parents[witness["executionId"]] for witness in selected
                                    if witness["executionId"] in source_parents)
            if control_proofs is not None:
                proof_hashes.update(hashed for control in case.controls if control in control_proofs
                                    for hashed in control_proofs[control])
            attempt = admit_entity("Attempt", {
                "sequence": self._sequences[binding_id] + 1,
                "startedMs": self._active[binding_id][1], "endedMs": ended,
                "status": status, "diagnosticCode": case_code,
                "witnessIds": tuple(witness["executionId"] for witness in selected),
                "proofSha256": sorted(proof_hashes),
            })
            previous = self._results.get(case.key, {}).get("attempts", ())
            results[case.key] = _catalog_case_result(self._inputs, case, status, (*previous, attempt))
        return results

    def _commit(self, bindings, results, witnesses, proofs, *, proof_bytes=None):
        self._results.update(results)
        for binding_id in bindings:
            self._sequences[binding_id] += 1
            del self._active[binding_id]
            del self._partitions[binding_id]
        self._witnesses = (*self._witnesses, *witnesses)
        self._proofs = MappingProxyType({**self._proofs, **proofs})
        if proof_bytes is not None:
            self._proof_bytes = proof_bytes
        self._used_executions = self._used_executions | {witness["executionId"] for witness in witnesses}
        return tuple(self._results[case.key] for case in self._cases if case.binding_id in bindings)

    def _append(self, binding_id, code, ended, witnesses=(), proofs=MappingProxyType({}),
                source_parents=None, control_proofs=None, *, proof_bytes=None):
        return self._commit(
            (binding_id,), self._case_results(binding_id, code, ended, witnesses, source_parents, control_proofs),
            witnesses, proofs, proof_bytes=proof_bytes)

    def finish(self, binding_id, *, manifest_data, owner_data, witnesses_data, proofs, completion_data,
               manifest_sha256, owner_sha256):
        return self.finish_parts(binding_id, transports={"all": {
            "manifest_data": manifest_data, "owner_data": owner_data, "witnesses_data": witnesses_data,
            "proofs": proofs, "completion_data": completion_data,
            "manifest_sha256": manifest_sha256, "owner_sha256": owner_sha256,
        }})

    def finish_parts(self, binding_id, *, transports):
        binding_id = stable_id(binding_id)
        if binding_id not in self._active or self._joint_plan is not None:
            raise ConformanceError("OwnershipInvalid")
        ended = _number(time.monotonic() * 1000)
        try:
            plan = {scope_id: {**scope, "tests": {
                identity: (binding_id, case_id) for identity, case_id in scope["tests"].items()}}
                for scope_id, scope in self._partitions[binding_id].items()}
            code, witnesses, proofs, origins, originals, used_sessions, instances, source_parents, controls, proof_bytes, arguments = self._ingest_parts(
                plan, transports, self._active[binding_id][1], ended, self._sequences[binding_id] + 1)
            results = self._append(
                binding_id, code, ended, witnesses, proofs, source_parents, controls, proof_bytes=proof_bytes)
            self._session_origins = MappingProxyType({**self._session_origins, **origins})
            self._original_observations = MappingProxyType({
                **self._original_observations, **originals})
            self._metadata_arguments = MappingProxyType({**self._metadata_arguments, **arguments})
            self._used_sessions = used_sessions
            self._instances = instances
            return results
        except ConformanceError as error:
            if binding_id in self._active:
                self._append(binding_id, str(error), ended)
            raise

    def _ingest_parts(self, plan, transports, started, ended, sequence):
        if not isinstance(transports, Mapping) or set(transports) != set(plan):
            raise ConformanceError("EvidenceIncomplete")
        fields = {"manifest_data", "owner_data", "witnesses_data", "proofs", "completion_data",
                  "manifest_sha256", "owner_sha256"}
        witnesses, proofs, origins, originals, codes, source_parents = (), {}, {}, {}, [], {}
        arguments = {}
        used_executions, used_sessions, instances = self._used_executions, self._used_sessions, self._instances
        proof_bytes = self._proof_bytes
        for scope_id, scope in sorted(plan.items()):
            transport = transports[scope_id]
            if not isinstance(transport, Mapping) or set(transport) != fields:
                raise ConformanceError()
            admit_attempt = ingest_runtime_attempt
            source_options = {}
            if self._native_sources is not None and (
                    scope_id.startswith("inspection-")
                    or scope_id in ("recovery-controller", "inventory-controller", "mutation-repair", "hook-admission")
                    or self._inputs["profileId"] == "metadata" and scope_id in ("original-memory", "original-sqlite")
                    or self._inputs["profileId"] == "artifacts" and scope_id in (
                        "controller", "original-integration", "original", "original-local", "original-object")):
                admit_attempt = self._native_sources.ingest_attempt
                source_options["category_scope"] = self._inputs["profileId"], scope_id
            observed = admit_attempt(
                inputs=self._inputs, **transport,
                expected_tests={identity: (binding, "none") for identity, (binding, _) in scope["tests"].items()},
                started_ms=started, ended_ms=ended, origin_inputs=self._origin_inputs,
                original_inputs=self._original_inputs, **source_options)
            if (observed["attemptId"] != scope["attemptId"]
                    or observed["completion"]["attemptSequence"] != sequence
                    or any((entry["bindingId"], entry["caseId"]) != scope["tests"][entry["testIdentity"]]
                           for entry in load_json(transport["manifest_data"])["expected"])
                    or any(witness["executionId"] in used_executions for witness in observed["witnesses"])):
                raise ConformanceError("ProofMismatch")
            sessions, instances = _runtime_provenance_state(observed, used_sessions, instances)
            used_sessions = used_sessions | sessions
            used_executions = used_executions | {row["executionId"] for row in observed["witnesses"]}
            witnesses = (*witnesses, *observed["witnesses"])
            proofs.update({f'runtime-{scope["attemptId"]}/{path}': hashed
                           for path, hashed in observed["proofs"].items()})
            proof_bytes += sum(len(data) for data in transport["proofs"].values())
            if source_options:
                source_parents.update(observed["sourceParents"])
                proofs.update({path: hashlib.sha256(raw).hexdigest() for path, raw in observed["sourceProofs"].items()})
                proof_bytes += sum(len(raw) for raw in observed["sourceProofs"].values())
            if len({**self._proofs, **proofs}) > MAX_PROOF_FILES or proof_bytes > MAX_PROOF_BYTES:
                raise ConformanceError("OutputLimitExceeded")
            origins.update(observed["sessionOrigins"])
            originals.update(observed["originalObservations"])
            arguments.update(observed.get("metadataArguments", {}))
            codes.append(observed["diagnosticCode"])
        controls = {}
        if self._native_sources is not None:
            authority = (self._native_sources.metadata_controls if self._inputs["profileId"] == "metadata"
                         else self._native_sources.artifact_controls)
            options = ({"metadata_scopes": {scope: transport for scope, transport in transports.items()
                                            if scope in ("original-memory", "original-sqlite")},
                        "sequence": sequence} if self._inputs["profileId"] == "metadata" else {
                            "artifact_scopes": {scope: transport for scope, transport in transports.items()
                                                if scope in ("original", "original-local", "original-object")},
                            "sequence": sequence})
            recovered = authority(self._inputs, started_ms=started, ended_ms=ended, **options)
            controls = recovered["controls"]
            proofs.update({path: hashlib.sha256(raw).hexdigest() for path, raw in recovered["sourceProofs"].items()})
            proof_bytes += sum(len(raw) for raw in recovered["sourceProofs"].values())
            if len({**self._proofs, **proofs}) > MAX_PROOF_FILES or proof_bytes > MAX_PROOF_BYTES:
                raise ConformanceError("OutputLimitExceeded")
        code = next((code for code in codes if code not in ("None", "AssertionFailed")),
                    "AssertionFailed" if "AssertionFailed" in codes else "None")
        return code, witnesses, proofs, origins, originals, used_sessions, instances, source_parents, controls, proof_bytes, arguments

    def finish_joint(self, *, transports):
        self.joint_partitions()
        attempt_id, started = self._active[next(iter(self._bindings))]
        ended = _number(time.monotonic() * 1000)
        committed = self._finish_joint(transports=transports, ended=ended)
        self._joint_origin = (attempt_id, started, ended)
        return committed

    def replay_joint(self, *, plan, transports):
        """Reconstruct the first joint ledger against the original live native source."""
        if self._native_sources is None:
            raise ConformanceError("OwnershipInvalid")
        if (self._active or self._joint_plan is not None or self._joint_origin is None
                or set(self._sequences.values()) != {1}):
            raise ConformanceError("EvidenceIncomplete")
        results = self.results()
        attempts = [row["attempts"] for row in results if row["status"] != "NotApplicable"]
        if not attempts or any(len(rows) != 1 for rows in attempts):
            raise ConformanceError("EvidenceIncomplete")
        attempt_id, started, ended = self._joint_origin
        windows = {(rows[0]["startedMs"], rows[0]["endedMs"]) for rows in attempts}
        if windows != {(started, ended)}:
            raise ConformanceError("ProofMismatch")
        from conformance_case_catalog import category_execution_partitions
        replay = CategoryRuntimeHistory(
            self._inputs, origin_inputs=self._origin_inputs, original_inputs=self._original_inputs,
            native_sources=self._native_sources)
        replay.begin_joint(attempt_id, partitions=category_execution_partitions(
            self._inputs["profileId"], mode="qualification"))
        expected = replay.joint_partitions()
        if not isinstance(plan, Mapping) or set(plan) != set(expected):
            raise ConformanceError("WitnessMissing")
        observed = {}
        for scope_id, scope in plan.items():
            if (not isinstance(scope, Mapping) or set(scope) != {"attemptId", "tests"}
                    or scope["tests"] != expected[scope_id]["tests"]):
                raise ConformanceError("WitnessMissing")
            observed[scope_id] = MappingProxyType({
                "attemptId": _uuid(scope["attemptId"]), "tests": expected[scope_id]["tests"]})
        identities = {scope["attemptId"] for scope in observed.values()}
        if len(identities) != len(observed) or attempt_id in identities:
            raise ConformanceError("ProofMismatch")
        # Replay the captured parent window and scope identities, not new executions.
        replay._joint_plan = MappingProxyType(observed)
        replay._active = {binding: (attempt_id, started) for binding in replay._bindings}
        replay._used_attempts = frozenset({attempt_id, *identities})
        replay._finish_joint(transports=transports, ended=ended)
        for original, reconstructed in (
                (results, replay.results()), (self.witnesses, replay.witnesses),
                (self.proofs, replay.proofs), (self.quality_proofs, replay.quality_proofs)):
            if original != reconstructed:
                raise ConformanceError("ProofMismatch")
        projection = MappingProxyType({
            "inputsSha256": digest(self._inputs), "planSha256": digest(plan),
            "resultsSha256": digest(replay.results()), "witnessesSha256": digest(replay.witnesses),
            "proofsSha256": digest(replay.proofs)})
        self._native_sources.retain_category_replay(self, projection)
        return projection

    def _finish_joint(self, *, transports, ended):
        plan = self.joint_partitions()
        try:
            binding = next(iter(self._bindings))
            code, witnesses, proofs, origins, originals, used_sessions, instances, source_parents, controls, proof_bytes, arguments = self._ingest_parts(
                plan, transports, self._active[binding][1], ended, self._sequences[binding] + 1)
            results = {key: value for binding in self._bindings
                       for key, value in self._case_results(
                           binding, code, ended, witnesses, source_parents, controls).items()}
            packets = {}
            if (self._inputs["mode"] == "qualification"
                    and code in ("None", "AssertionFailed")):
                from conformance_case_catalog import CATEGORY_QUALITY_BASIS

                quality_basis = CATEGORY_QUALITY_BASIS[self._inputs["profileId"]]
                basis = {**self._results, **results}
                executions = {row["executionId"]: row for row in (*self._witnesses, *witnesses)}
                for case in self._cases:
                    if case.binding_id != "none" or case.case_id not in quality_basis:
                        continue
                    material = _category_quality_composition(
                        self._inputs, case.case_id, basis, executions, sequence=self._sequences["none"] + 1,
                        started_ms=self._active["none"][1], ended_ms=ended,
                        proof_registry={**self._proofs, **proofs})
                    attempt = material["attempt"]
                    packets.update(material["sourceProofs"])
                    for path, raw in material["sourceProofs"].items():
                        if path in proofs or path in self._proofs:
                            raise ConformanceError("ProofMismatch")
                        proofs[path] = hashlib.sha256(raw).hexdigest()
                        proof_bytes += len(raw)
                    if len({**self._proofs, **proofs}) > MAX_PROOF_FILES or proof_bytes > MAX_PROOF_BYTES:
                        raise ConformanceError("OutputLimitExceeded")
                    previous = self._results.get(case.key, {}).get("attempts", ())
                    results[case.key] = _catalog_case_result(
                        self._inputs, case, attempt["status"], (*previous, attempt))
            committed = self._commit(self._bindings, results, witnesses, proofs, proof_bytes=proof_bytes)
            self._quality_proofs = MappingProxyType({**self._quality_proofs, **packets})
            self._session_origins = MappingProxyType({**self._session_origins, **origins})
            self._original_observations = MappingProxyType({**self._original_observations, **originals})
            self._metadata_arguments = MappingProxyType({**self._metadata_arguments, **arguments})
            self._used_sessions, self._instances = used_sessions, instances
            self._joint_plan = None
            return committed
        except ConformanceError as error:
            self._end_joint(str(error), ended)
            raise

    def interrupt_joint(self, code):
        return self._end_joint(code, _number(time.monotonic() * 1000))

    def _end_joint(self, code, ended):
        self.joint_partitions()
        if code not in DIAGNOSTIC_CODES or code == "None":
            raise ConformanceError()
        results = {key: value for binding in self._bindings
                   for key, value in self._case_results(binding, code, ended, ()).items()}
        committed = self._commit(self._bindings, results, (), {})
        self._joint_plan = None
        return committed

    def interrupt(self, binding_id, code):
        binding_id = stable_id(binding_id)
        if binding_id not in self._active or self._joint_plan is not None:
            raise ConformanceError("OwnershipInvalid")
        if code not in DIAGNOSTIC_CODES or code == "None":
            raise ConformanceError()
        return self._append(binding_id, code, _number(time.monotonic() * 1000))

    def results(self):
        if self._active or set(self._results) != {case.key for case in self._cases}:
            raise ConformanceError("EvidenceIncomplete")
        return tuple(self._results[case.key] for case in self._cases)
