"""Closed five-profile transport inspection, not qualification or CI attestation."""

from collections.abc import Mapping
import hashlib
from types import MappingProxyType

from conformance_case_catalog import expected_cases
from conformance_evidence import (
    ConformanceError, MAX_REPORT_BYTES, PROFILES, admit_entity, digest, load_json, sha256,
)


def _profile_map(value):
    if not isinstance(value, Mapping) or set(value) != set(PROFILES):
        raise ConformanceError("EvidenceIncomplete")
    return dict(value)


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
        statuses = jobs[profile]
        if not isinstance(statuses, Mapping) or set(statuses) != {"job", "upload", "download"}:
            raise ConformanceError("EvidenceSchemaInvalid")
        if any(statuses[phase] != "success" for phase in ("job", "upload", "download")):
            raise ConformanceError("EvidenceIncomplete")
        expected_hash = sha256(pins[profile])
        raw = reports[profile]
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_REPORT_BYTES:
            raise ConformanceError("EvidenceSchemaInvalid")
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ConformanceError("ProofMismatch")
        report = admit_entity("QualificationReport", load_json(raw))
        inputs = report["inputs"]
        expected = admit_entity("RunInputs", assignments[profile])
        if inputs["profileId"] != profile or digest(inputs) != digest(expected):
            raise ConformanceError("InputChanged")
        if inputs["mode"] != "qualification" or inputs["sourceState"] not in ("clean-local", "clean-ci"):
            raise ConformanceError("EvidenceIncomplete")
        selected = tuple(inputs[key] for key in (
            "invocationGroupId", "sourceRevision", "sourceState", "sourceManifestSha256",
            "catalogRevision", "catalogSha256", "sdkSha256"))
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
