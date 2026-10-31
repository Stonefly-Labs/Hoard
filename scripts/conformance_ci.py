"""Trusted finite-profile verification and closed five-profile correspondence."""

from collections.abc import Mapping
import hashlib
import io
from pathlib import Path
from pathlib import PurePosixPath
from types import MappingProxyType
import time

from conformance_case_catalog import expected_cases
from conformance_evidence import (
    ConformanceError, MAX_REPORT_BYTES, PROFILES, _constant, _hash_map, _list,
    _local_package_patterns, _record, admit_entity, configuration_policy, digest, load_json,
    admit_qualification_origin, canonical_bytes, inspect_profile_report,
    inspect_receipted_profile_qualification, relative_path, sha256, stable_id, _input_root, _source_file,
)


def _profile_map(value):
    if not isinstance(value, Mapping) or set(value) != set(PROFILES):
        raise ConformanceError("EvidenceIncomplete")
    return dict(value)


def _common_context(inputs):
    return tuple(inputs[key] for key in (
        "invocationGroupId", "sourceRevision", "sourceState", "sourceManifestSha256",
        "catalogRevision", "catalogSha256", "sdkSha256"))


def _job_results(value, *, local=False):
    if not isinstance(value, Mapping) or set(value) != {"job", "upload", "download"}:
        raise ConformanceError("EvidenceSchemaInvalid")
    success = {phase: "success" for phase in ("job", "upload", "download")}
    local_results = {"job": "success", "upload": "not-required", "download": "not-required"}
    if dict(value) != success and not (local and dict(value) == local_results):
        raise ConformanceError("EvidenceIncomplete")
    return MappingProxyType(dict(value))


def _configuration_sources(value):
    if not isinstance(value, Mapping):
        raise ConformanceError("EvidenceSchemaInvalid")
    if set(value) == {"packageSources", "packageSourceMapping"}:
        sources = _record({
            "local": _constant("isolated-current-archives"),
            "nuget.org": _constant("https://api.nuget.org/v3/index.json")})(value["packageSources"])
        mapping = _record({
            "local": lambda rows: _list(lambda row: row if row == "Hoard.*" else stable_id(row), 1025)(rows),
            "nuget.org": lambda rows: _list(_constant("*"), 1)(rows),
        })(value["packageSourceMapping"])
        if tuple(mapping["local"]) != _local_package_patterns(
                tuple(pattern for pattern in mapping["local"] if pattern != "Hoard.*")):
            raise ConformanceError("InputChanged")
        return MappingProxyType({"packageSources": sources, "packageSourceMapping": mapping})
    if set(value) == {"packageSources", "archives"}:
        sources = _record({"frozen": _constant("isolated-frozen-archives")})(value["packageSources"])
        archives = _hash_map(value["archives"])
        if (not 0 < len(archives) <= 1024
                or any(PurePosixPath(path).name != path or not path.endswith(".nupkg") for path in archives)
                or len({path.casefold() for path in archives}) != len(archives)):
            raise ConformanceError("EvidenceSchemaInvalid")
        return MappingProxyType({"packageSources": sources, "archives": archives})
    raise ConformanceError("EvidenceSchemaInvalid")


def _configuration(value):
    from conformance_case_catalog import ORIGINAL_INSPECTION_LITERAL_WITNESSES, ORIGINAL_INSPECTION_WITNESSES

    fields = {key: _constant(selected) for key, selected in configuration_policy().items()}
    fields["sources"] = _configuration_sources
    if isinstance(value, Mapping) and "inspectionInputs" in value:
        def inspection(selected):
            expected = set(ORIGINAL_INSPECTION_WITNESSES) - set(ORIGINAL_INSPECTION_LITERAL_WITNESSES)
            if not isinstance(selected, Mapping) or not selected or set(selected) - expected:
                raise ConformanceError("EvidenceSchemaInvalid")
            result = {}
            for identity, files in selected.items():
                files = _hash_map(files)
                if not 0 < len(files) <= 2048:
                    raise ConformanceError("EvidenceSchemaInvalid")
                for key in files:
                    sha256(key)
                result[identity] = files
            return MappingProxyType(result)
        fields["inspectionInputs"] = inspection
    return _record(fields)(value)


def admit_coordinator(value, *, require_all=False):
    """Admit separately trusted assignments; never infer authority from a report."""
    qualified = isinstance(value, Mapping) and value.get("schemaVersion") == 2
    header_fields = {"schemaVersion": _constant(2 if qualified else 1), "profiles": lambda rows: rows}
    if qualified:
        header_fields["configurationPolicy"] = _record({
            key: _constant(selected) for key, selected in configuration_policy().items()})
    header = _record(header_fields)(value)
    selected = header["profiles"]
    if (not isinstance(selected, Mapping) or not selected or set(selected) - set(PROFILES)
            or require_all and set(selected) != set(PROFILES)):
        raise ConformanceError("EvidenceIncomplete")
    profiles, run_ids, common = {}, set(), None
    for profile in PROFILES:
        if profile not in selected:
            continue
        fields = {
            "inputs": lambda inputs: admit_entity("RunInputs", inputs),
            "reportSha256": sha256, "reportPath": relative_path,
            "jobResults": lambda results: results,
        }
        if qualified:
            fields["qualificationOrigin"] = lambda origin: admit_qualification_origin(origin, profile=profile)
        else:
            fields["configuration"] = _configuration
        entry = _record(fields)(selected[profile])
        inputs = entry["inputs"]
        entry = MappingProxyType({
            **entry, "jobResults": _job_results(
                entry["jobResults"], local=qualified and inputs["sourceState"] == "clean-local")})
        if (inputs["profileId"] != profile
                or not qualified and digest(entry["configuration"]) != inputs["configurationSha256"]
                or (qualified or require_all) and (
                    inputs["mode"] != "qualification" or inputs["sourceState"] not in ("clean-local", "clean-ci"))):
            raise ConformanceError("InputChanged")
        origin = entry.get("qualificationOrigin")
        if origin is not None and (
                origin["inputsSha256"] != digest(inputs)
                or origin["reportSha256"] != entry["reportSha256"]):
            raise ConformanceError("InputChanged")
        context = _common_context(inputs)
        if common is not None and context != common or inputs["runId"] in run_ids:
            raise ConformanceError("InputChanged")
        common = context
        run_ids.add(inputs["runId"])
        profiles[profile] = entry
    return MappingProxyType({
        "schemaVersion": header["schemaVersion"], "configurationPolicySha256": digest(configuration_policy()),
        "profiles": MappingProxyType(profiles)})


def _read_packet(root, relative):
    contents = io.BytesIO()
    with _input_root(root) as (_, descriptor):
        _source_file(descriptor, relative, remaining=MAX_REPORT_BYTES,
                     deadline=time.monotonic() + 5, target=contents)
    return contents.getvalue()


def inspect_offline(invocation):
    """Replay trusted assignments; receipt-free inspection cannot qualify."""
    if invocation.coordinator_path is None:
        raise ConformanceError("EvidenceIncomplete")
    context_path = Path(invocation.coordinator_path)
    context = admit_coordinator(
        load_json(_read_packet(context_path.parent, context_path.name)),
        require_all=invocation.action == "aggregate")
    if invocation.action == "verify":
        path = Path(invocation.input_path)
        raw = _read_packet(path.parent, path.name)
        report = admit_entity("QualificationReport", load_json(raw))
        profile = report["inputs"]["profileId"]
        entry = context["profiles"].get(profile)
        if entry is None:
            raise ConformanceError("InputChanged")
        root = path
        for component in reversed(PurePosixPath(entry["reportPath"]).parts):
            if root.name != component:
                raise ConformanceError("InputChanged")
            root = root.parent
        if context_path.is_relative_to(root):
            raise ConformanceError("OwnershipInvalid")
        if "qualificationOrigin" in entry:
            inspected = inspect_receipted_profile_qualification(
                root, raw, expected_inputs=entry["inputs"], expected_report_sha256=entry["reportSha256"],
                qualification_origin=entry["qualificationOrigin"])
        else:
            inspected = inspect_profile_report(
                root, raw, expected_inputs=entry["inputs"], expected_report_sha256=entry["reportSha256"])
    elif invocation.action == "aggregate":
        root = Path(invocation.input_path)
        if context_path.is_relative_to(root):
            raise ConformanceError("OwnershipInvalid")
        reports = {profile: _read_packet(root / profile, entry["reportPath"])
                   for profile, entry in context["profiles"].items()}
        transport = inspect_profile_transports(
            reports, expected_inputs={profile: entry["inputs"] for profile, entry in context["profiles"].items()},
            expected_report_sha256={profile: entry["reportSha256"] for profile, entry in context["profiles"].items()},
            job_results={profile: entry["jobResults"] for profile, entry in context["profiles"].items()})
        if all("qualificationOrigin" in entry for entry in context["profiles"].values()):
            profiles = {
                profile: inspect_receipted_profile_qualification(
                    root / profile, reports[profile], expected_inputs=entry["inputs"],
                    expected_report_sha256=entry["reportSha256"],
                    qualification_origin=entry["qualificationOrigin"])
                for profile, entry in context["profiles"].items()}
            if any(row["qualification"] is not True or row["code"] != "None" for row in profiles.values()):
                raise ConformanceError("EvidenceIncomplete")
            inspected = MappingProxyType({
                "qualification": True, "baselineQualification": True, "code": "None",
                "scope": "five-profile-fixture-qualification", "profiles": MappingProxyType(profiles),
                "configurationPolicySha256": context["configurationPolicySha256"],
                "reportSha256": transport["reportSha256"]})
        else:
            profiles = {
                profile: inspect_profile_report(
                    root / profile, reports[profile], expected_inputs=entry["inputs"],
                    expected_report_sha256=entry["reportSha256"])
                for profile, entry in context["profiles"].items()}
            inspected = MappingProxyType({
                "qualification": False, "scope": "five-profile-structure-diagnostic",
                "code": "AssertionFailed" if any(row["failedAttemptCount"] for row in profiles.values())
                else "EvidenceIncomplete", "profiles": MappingProxyType(profiles),
                "configurationPolicySha256": context["configurationPolicySha256"],
                "reportSha256": transport["reportSha256"]})
    else:
        raise ConformanceError("EvidenceSchemaInvalid")
    print(canonical_bytes(inspected).decode("ascii"))
    if inspected["qualification"] is True and inspected["code"] == "None":
        return 0
    return 1 if inspected["code"] == "AssertionFailed" else 2


def inspect_profile_transports(reports, *, expected_inputs, expected_report_sha256, job_results):
    """Use externally supplied assignments, pins and job/upload/download outcomes.

    A matching transport does not establish runtime origin, settlement, complete
    inventories or qualification. Never derive these expected values from the
    same downloaded artifact as a substitute for trusted coordinator observations.
    """
    reports = _profile_map(reports)
    assignments = _profile_map(expected_inputs)
    pins = _profile_map(expected_report_sha256)
    jobs = _profile_map(job_results)
    common = None
    run_ids = set()
    hashes = {}
    input_hashes = {}
    counts = {}
    for profile in PROFILES:
        expected_hash = sha256(pins[profile])
        raw = reports[profile]
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_REPORT_BYTES:
            raise ConformanceError("EvidenceSchemaInvalid")
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ConformanceError("ProofMismatch")
        report = admit_entity("QualificationReport", load_json(raw))
        inputs = report["inputs"]
        expected = admit_entity("RunInputs", assignments[profile])
        _job_results(jobs[profile], local=expected["sourceState"] == "clean-local")
        if inputs["profileId"] != profile or digest(inputs) != digest(expected):
            raise ConformanceError("InputChanged")
        if inputs["mode"] != "qualification" or inputs["sourceState"] not in ("clean-local", "clean-ci"):
            raise ConformanceError("EvidenceIncomplete")
        selected = _common_context(inputs)
        if common is not None and selected != common or inputs["runId"] in run_ids:
            raise ConformanceError("InputChanged")
        common = selected
        run_ids.add(inputs["runId"])
        hashes[profile] = expected_hash
        input_hashes[profile] = digest(inputs)
        counts[profile] = len(expected_cases(profile))
    return MappingProxyType({
        "qualification": False, "code": "EvidenceIncomplete",
        "scope": "profile-transport-consistency-diagnostic",
        "profiles": PROFILES, "reportSha256": MappingProxyType(hashes),
        "inputSha256": MappingProxyType(input_hashes),
        "expectedCaseCounts": MappingProxyType(counts),
    })
