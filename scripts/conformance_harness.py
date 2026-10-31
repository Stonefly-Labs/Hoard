"""Source-bound harness controls and original live-to-released qualification."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import time
from types import MappingProxyType
import uuid

import conformance_evidence as evidence
from conformance_case_catalog import catalog_admission_witnesses
from conformance_execution import OwnedRun
from conformance_sources import runtime_arguments, runtime_runner, runtime_settings


CATALOG_FRAME = "proofs/harness-catalog.json"
CATALOG_INPUTS = "proofs/harness-inputs.json"
FROZEN_INPUTS = "proofs/harness-frozen-inputs/"
CONTRIBUTOR_FRAME = "proofs/harness-contributors.json"
CATEGORY_CONTROL_FRAME = "proofs/harness-category-controls.json"
OBSERVATION = "proofs/harness-observation.json"
TOOLING_SUMMARY = "proofs/harness-tooling-summary.json"
COMPLETION_INPUTS = "proofs/category-harness-qualification-completion-inputs.json"
ORIGINAL_REPORT = "proofs/harness-runtime-released-report.json"
QUALIFIED_REPORT = "proofs/harness-fixture-qualification-report.json"

_EXECUTION = "test_conformance_execution.ConformanceExecutionTests."
_CI = "test_conformance_ci.ConformanceProfileTransportTests."
_CLI = "test_conformance_cli.ConformanceCliTests."
_SANITATION = "test_conformance_sanitation.ConformanceSanitationTests."
_INGESTION = "test_conformance_evidence.ConformanceRuntimeIngestionTests."

TOOLING_BASIS = MappingProxyType({
    "QC-29": (
        _INGESTION + "test_compatibility_presentations_reconstruct_the_candidate_and_bound_support_to_exact_inputs",
        _CI + "test_public_aggregate_checks_all_five_complete_inventories_but_never_qualifies_empty_models"),
    "QC-32": (
        _CLI + "test_explicit_category_project_cannot_change_the_selected_common_agreement",
        _EXECUTION + "test_child_environment_is_explicit_and_cannot_inject_a_native_loader"),
    "QC-33": (
        _EXECUTION + "test_private_roots_and_subresources_are_run_owned_and_single_writer",
        _EXECUTION + "test_concurrent_runs_isolate_cache_inputs_and_containment_does_not_end_the_other_child",
        _EXECUTION + "test_preflight_parent_swap_cannot_create_a_workspace_under_an_outside_sentinel"),
    "QC-34": (
        _EXECUTION + "test_insufficient_artifact_capacity_and_invalid_budgets_fail_explicitly",
        _EXECUTION + "test_profile_reserves_termination_and_cleanup_before_admitting_another_child",
        _EXECUTION + "test_child_deadline_includes_admission_work_instead_of_restarting_after_it",
        _EXECUTION + "test_control_barrier_and_caller_limits_cannot_expand_or_bypass_command_budgets",
        _EXECUTION + "test_output_flood_is_failure_not_truncated_success_and_child_exits",
        _EXECUTION + "test_safe_event_size_is_bounded_before_json_expansion_without_truncation",
        _EXECUTION + "test_expired_cleanup_records_retention_without_deleting_synthetic_resources",
        _EXECUTION + "test_transfer_peak_and_protocol_failures_cannot_become_measured_success",
        _EXECUTION + "test_observed_barrier_precedes_owned_signal_and_confirmed_process_tree_exit"),
    "QC-35": (
        _EXECUTION + "test_live_work_is_retained_then_retry_records_exit_without_erasing_the_failure",
        _EXECUTION + "test_failed_release_publication_cannot_claim_release_and_retry_keeps_evidence",
        _EXECUTION + "test_partial_directory_cleanup_retries_only_unlinked_pins_and_preserves_retained_history"),
    "QC-36": (
        _EXECUTION + "test_rejects_existing_foreign_symlink_and_nonprivate_roots",
        _EXECUTION + "test_foreign_process_identity_cannot_be_terminated_or_cleaned",
        _EXECUTION + "test_ledger_tampering_and_symlink_swap_prevent_cleanup",
        _EXECUTION + "test_replacing_a_top_level_directory_does_not_recreate_its_ownership",
        _EXECUTION + "test_one_owned_writer_rejects_overlapping_commands_and_cleanup_before_admission"),
    "QC-37": (
        _CLI + "test_invalid_modes_and_paths_never_allocate_or_fall_back_to_a_profile",
        _EXECUTION + "test_child_environment_is_explicit_and_cannot_inject_a_native_loader",
        _EXECUTION + "test_remote_or_unknown_artifact_scratch_rejects_before_workspace_creation",
        _EXECUTION + "test_artifact_and_baseline_capacity_preflight_prevents_root_creation",
        _EXECUTION + "test_local_scratch_observation_is_bounded_and_rejects_failed_or_malformed_controls"),
    "QC-45": (
        _CI + "test_local_and_ci_use_the_same_independent_profile_inventories",
        _CI + "test_foreign_evaluator_source_rejects_even_with_matching_revision_and_assignment",
        _CI + "test_public_aggregate_checks_all_five_complete_inventories_but_never_qualifies_empty_models",
        _CI + "test_aggregate_rejects_resealed_missing_cases_in_each_profile"),
    "QC-46": (
        _CI + "test_job_upload_download_failure_cancellation_and_missing_status_reject",
        _CI + "test_missing_extra_and_misassigned_profiles_reject",
        _CI + "test_foreign_common_context_rejects_even_when_each_assignment_matches",
        _CI + "test_coordinator_does_not_infer_missing_jobs_or_profiles_from_green_reports",
        _CI + "test_receipted_aggregate_cannot_promote_four_profiles_without_harness_authority"),
    "QC-47": (
        _CI + "test_focused_preparation_dirty_and_changed_original_inputs_reject",
        _CI + "test_external_report_pins_and_unique_run_identities_are_required",
        _CI + "test_coordinator_rejects_foreign_configuration_policy_and_changed_preimages",
        _CI + "test_aggregate_keeps_failed_attempt_after_passing_modeled_retry",
        _INGESTION + "test_compatibility_presentations_reconstruct_the_candidate_and_bound_support_to_exact_inputs"),
    "QC-48": tuple(_SANITATION + name for name in (
        "test_diagnostic_json_junit_markdown_and_ci_surfaces_do_not_repeat_private_inputs",
        "test_unknown_diagnostic_report_fields_reject_instead_of_disappearing_into_public_success",
        "test_public_failure_projection_never_renders_provider_errors_or_private_paths",
        "test_unknown_provider_text_never_persists_in_any_owned_file_or_filename",
        "test_private_executable_settings_remain_bound_until_real_settlement_and_do_not_persist",
        "test_build_snapshot_private_metadata_is_transient_without_weakening_source_binding",
        "test_output_flood_is_incomplete_without_spooling_or_truncating_into_success")),
})

NATIVE_CONTROL_BASIS = MappingProxyType({
    "QC-38": (
        ("retainedReportTests", "test_every_admission_field_is_required_and_independently_bound"),
        ("liveOriginTests", "test_predeclared_partitions_and_original_scope_identities")),
    "QC-39": (
        ("retainedReportTests", "test_exact_case_and_parameter_sets_reject_missing_duplicate_and_unknown_rows"),
        ("liveOriginTests", "test_predeclared_partitions_and_original_scope_identities")),
    "QC-40": (
        ("retainedReportTests", "test_runtime_provenance_and_unsupported_outcomes_cannot_be_substituted"),
        ("liveOriginTests", "test_original_transports_cannot_be_substituted"),
        ("liveOriginTests", "test_rehashed_command_and_parent_cannot_replace_executor_held_bytes")),
    "QC-41": (
        ("retainedReportTests", "test_exclusion_reclassification_retry_reuse_and_optimistic_flags_reject"),
        ("retainedReportTests", "test_every_admission_field_is_required_and_independently_bound")),
    "QC-42": (
        ("retainedReportTests", "test_runtime_provenance_and_unsupported_outcomes_cannot_be_substituted"),
        ("retainedReportTests", "test_exclusion_reclassification_retry_reuse_and_optimistic_flags_reject"),
        ("liveOriginTests", "test_optimistic_history_and_retimed_parent_cannot_replace_observation")),
    "QC-43": (
        ("retainedReportTests", "test_failed_attempt_cannot_disappear_behind_a_passing_retry"),
        ("retainedReportTests", "test_exclusion_reclassification_retry_reuse_and_optimistic_flags_reject")),
    "QC-44": (
        ("retainedReportTests", "test_nested_schema_unicode_duration_path_and_size_limits_reject_safely"),
        ("retainedReportTests", "test_real_proof_bytes_presence_links_completion_sealing_and_byte_budget")),
})


def _tooling_case_sources(case_id, packet):
    selected = TOOLING_BASIS.get(case_id, ())
    if (packet["code"] != "None" or packet["expectedTests"] != packet["observedTests"]
            or not set(selected) <= set(packet["observedTests"])):
        raise evidence.ConformanceError("WitnessMissing")
    return selected


def _frozen_inputs(inputs):
    return {
        **inputs["runtimeAssemblies"], **inputs["locks"],
        **{f'feed/candidate/{row["packageId"]}.{row["version"]}.nupkg': row["sha256"]
           for row in inputs["packages"]},
    }


def _catalog_manifest(inputs, assembly, attempt):
    identities = catalog_admission_witnesses()
    package = next((row for row in inputs["packages"]
                    if row["packageId"] == "Hoard.Testing.Conformance"), None)
    if package is None or assembly not in inputs["runtimeAssemblies"]:
        raise evidence.ConformanceError("InputChanged")
    return {
        "schemaVersion": 1, "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "attemptId": evidence._uuid(attempt), "attemptSequence": 1, "purpose": "execution",
        "inputSha256": evidence.digest(inputs), "runInputsPath": CATALOG_INPUTS,
        "assemblies": [{"id": "test-assembly", "path": assembly,
                        "sha256": inputs["runtimeAssemblies"][assembly]}],
        "packages": [{"id": package["packageId"],
                      "path": f'feed/candidate/{package["packageId"]}.{package["version"]}.nupkg',
                      "sha256": package["sha256"]}],
        "expected": [{
            "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
            "assemblyId": "test-assembly", "packageId": package["packageId"],
            "bindingId": "none", "matrixId": "none", "assertionSymbol": None, "caseId": "QC-01",
        } for identity in identities],
    }


def prepare_catalog(repository, run, *, group_id):
    import conformance_baselines as baselines
    import conformance_sdk_checks as sdk
    from conformance_prepare import Project, build_project
    from conformance_sources import read_bounded

    if type(run) is not OwnedRun or run.state != "Active":
        raise evidence.ConformanceError("OwnershipInvalid")
    group_id = evidence._uuid(group_id)
    (run.root / "cache/.local/share").mkdir(parents=True, mode=0o700)
    (run.root / "cache/.local").chmod(0o700)
    source, sources = evidence.snapshot_sources(repository, run, transient=True)
    observed = sdk.environment(run, scope="build")
    msbuild = sdk.selected_msbuild(observed)
    configuration, feed = baselines._config(run, "candidate")
    projects = (
        Project("src/Hoard.Abstractions/Hoard.Abstractions.csproj", "Hoard.Abstractions"),
        Project(sdk.SDK + "/Hoard.Testing.Conformance.csproj", "Hoard.Testing.Conformance"),
        Project(sdk.LOGGER + "/Hoard.Conformance.TestLogger.csproj", "Hoard.Conformance.TestLogger"),
        Project(sdk.TESTS + "/Hoard.Conformance.Tests.csproj"),
    )
    for project in projects:
        build_project(run, source, project, configuration, feed,
                      update=False, historical_lock=True, msbuild=msbuild)
    _, runner_material = sdk.runtime_runner_material(observed)
    sdk.write_new(run.root / "proofs/sdk-vstest-inputs.json", runner_material)
    runtime = {}
    for folder in (sdk.TESTS, sdk.LOGGER):
        prefix = (source / folder / "bin/Release/net10.0").relative_to(run.root).as_posix()
        runtime.update({
            prefix + "/" + path: hashed
            for path, hashed in evidence.proof_manifest(run.root / prefix).items()
            if path.endswith((".dll", ".deps.json", ".runtimeconfig.json", ".so", ".dylib"))
        })
    runtime["proofs/sdk-vstest-inputs.json"] = hashlib.sha256(runner_material).hexdigest()
    source_prefix = source.relative_to(run.root).as_posix()
    locks = [source_prefix + "/" + path for path in evidence.proof_manifest(
        source, include_file=lambda path: path.endswith("packages.lock.json"))]
    capture = {
        "profile_id": "harness", "mode": "qualification", "invocation_group_id": group_id,
        "package_versions": [{"packageId": row.package, "version": "0.1.0"}
                             for row in projects if row.package is not None],
        "feed": feed.relative_to(run.root).as_posix(),
        "configuration": configuration.relative_to(run.root).as_posix(),
        "lock_paths": locks, "runtime_paths": list(runtime), "binding_sources": [],
        "observed_environment": observed, "budgets": {**sdk.BUDGETS, "profileSeconds": 3600},
        "invocation": ["profile", "harness", "native-source-admission"],
        "ci_revision": os.environ.get("GITHUB_SHA") if os.environ.get("GITHUB_ACTIONS") == "true" else None,
    }
    if os.environ.get("GITHUB_ACTIONS") == "true" and capture["ci_revision"] is None:
        raise evidence.ConformanceError("InputChanged")
    inputs = evidence.capture_profile_inputs(run, repository, source, **capture)
    if inputs["sourceManifest"] != sources or inputs["runtimeAssemblies"] != runtime:
        raise evidence.ConformanceError("InputChanged")
    sdk.write_new(run.root / CATALOG_INPUTS, evidence.canonical_bytes(inputs))
    (run.root / FROZEN_INPUTS).mkdir(mode=0o700)
    for relative, hashed in _frozen_inputs(inputs).items():
        (run.root / relative).chmod(0o400)
        target = run.root / (FROZEN_INPUTS + hashed)
        if not target.exists():
            sdk.write_new(target, read_bounded(run.root / relative, evidence.MAX_PROOF_BYTES))
    # Configuration identity hashes normalized policy, not the XML bytes.
    sdk.write_new(run.root / (FROZEN_INPUTS + inputs["configurationSha256"]),
                  read_bounded(configuration, 64 * 1024))
    sdk.write_new(run.root / "runtime-owner.json", evidence.canonical_bytes({
        "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": group_id,
        "rootId": run.root_id, "rootPathSha256": hashlib.sha256(str(run.root).encode()).hexdigest(),
    }))
    assembly = source_prefix + "/" + sdk.TESTS + "/bin/Release/net10.0/Hoard.Conformance.Tests.dll"
    return inputs, assembly, source, capture


def execute_catalog(run, inputs, assembly):
    import conformance_sdk_checks as sdk

    inputs = evidence.admit_entity("RunInputs", inputs)
    if (type(run) is not OwnedRun or run.state != "Active"
            or inputs["profileId"] != "harness" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id):
        raise evidence.ConformanceError("OwnershipInvalid")
    manifest = _catalog_manifest(inputs, evidence.relative_path(assembly), str(uuid.uuid4()))
    expected = {identity: ("none", "none") for identity in catalog_admission_witnesses()}
    result, observed, transport, _ = sdk._execute_runtime_transport(
        run, inputs, run.root / assembly, manifest, expected, {"category_scope": ("harness", "catalog")})
    sdk.validate_observation(
        observed, result, tuple(expected), "None", "Passed", 0, transport["proofs"], "None")
    if result.execution_record_sha256 is None:
        raise evidence.ConformanceError("OwnershipInvalid")
    for purpose, bounds in transport["nativeTransports"].items():
        folder = run.root / (("discovery-" if purpose == "discovery" else "runtime-") + bounds["attemptId"])
        names = ({"completion.json", "discovered.jsonl"} if purpose == "discovery" else
                 {"completion.json", "witnesses.jsonl", *transport["proofs"]})
        for name in names:
            (folder / name).chmod(0o400)
    sdk.write_new(run.root / CATALOG_FRAME, evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False, "scope": "harness-native-catalog",
        "inputsSha256": evidence.digest(inputs), "assemblyPath": assembly, **transport["nativeTransports"],
    }))
    inspected = inspect_catalog(run.root, inputs)
    if tuple(inspected["witnesses"]) != tuple(observed["witnesses"]):
        raise evidence.ConformanceError("ProofMismatch")
    return inspected


def inspect_catalog(root, inputs):
    import conformance_sdk_checks as sdk

    root = Path(root)
    inputs = evidence.admit_entity("RunInputs", inputs)
    if inputs["profileId"] != "harness" or inputs["mode"] != "qualification":
        raise evidence.ConformanceError("UnsupportedProfile")
    hashes = {}

    def read(path, limit=evidence.MAX_REPORT_BYTES):
        hashed, raw = evidence._readonly_report_proof(root, path)
        if len(raw) > limit:
            raise evidence.ConformanceError("OutputLimitExceeded")
        hashes[path] = hashed
        return raw

    phase = evidence._record({
        "attemptId": evidence._uuid, "startedMs": evidence._number, "endedMs": evidence._number})
    frame = evidence._runtime_json(read(CATALOG_FRAME), {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "scope": evidence._constant("harness-native-catalog"),
        "inputsSha256": evidence._constant(evidence.digest(inputs)),
        "assemblyPath": evidence.relative_path, "discovery": phase, "execution": phase,
    })
    if (frame["discovery"]["attemptId"] == frame["execution"]["attemptId"]
            or frame["discovery"]["endedMs"] > frame["execution"]["startedMs"]
            or any(not 0 <= bounds["endedMs"] - bounds["startedMs"]
                   <= min(180, inputs["budgets"]["childSeconds"]) * 1000
                   for bounds in (frame["discovery"], frame["execution"]))):
        raise evidence.ConformanceError("ProofMismatch")
    if evidence.canonical_bytes(inputs) != read(CATALOG_INPUTS):
        raise evidence.ConformanceError("InputChanged")
    for hashed in set(_frozen_inputs(inputs).values()):
        if hashlib.sha256(read(FROZEN_INPUTS + hashed, evidence.MAX_PROOF_BYTES)).hexdigest() != hashed:
            raise evidence.ConformanceError("InputChanged")
    configuration = read(FROZEN_INPUTS + inputs["configurationSha256"], 64 * 1024)
    if (configuration != evidence.synthetic_nuget_configuration(root / "feed/candidate")
            or inputs["configurationSha256"] != evidence.configuration_fingerprint(evidence.synthetic_source_mapping())):
        raise evidence.ConformanceError("InputChanged")
    owner_data = read("runtime-owner.json", 64 * 1024)
    owner = evidence._runtime_json(owner_data, {
        "schemaVersion": evidence._constant(1), "runId": evidence._constant(inputs["runId"]),
        "invocationGroupId": evidence._constant(inputs["invocationGroupId"]),
        "rootId": evidence.stable_id,
        "rootPathSha256": evidence._constant(hashlib.sha256(str(root).encode()).hexdigest()),
    })
    runner = runtime_runner(root, inputs)
    read("proofs/sdk-vstest-inputs.json")
    expected = {identity: ("none", "none") for identity in catalog_admission_witnesses()}
    discovered, witnesses = None, None
    sequences = []
    for purpose in ("discovery", "execution"):
        bounds = frame[purpose]
        attempt = bounds["attemptId"]
        manifest_data = read(f"runtime-input-{attempt}.json")
        manifest = {**_catalog_manifest(inputs, frame["assemblyPath"], attempt), "purpose": purpose}
        if evidence.canonical_bytes(manifest) != manifest_data:
            raise evidence.ConformanceError("ProofMismatch")
        assembly = root / frame["assemblyPath"]
        settings = runtime_settings(
            root, assembly, attempt, hashlib.sha256(manifest_data).hexdigest(),
            hashlib.sha256(owner_data).hexdigest(), "")
        arguments = runtime_arguments(
            assembly, root / f"stores/settings-{attempt}.runsettings", tuple(expected),
            discovery=purpose == "discovery", runner_prefix=runner["prefix"])
        receipt, record = sdk.verify_category_command_proof(
            root, run_id=inputs["runId"], root_id=owner["rootId"], arguments=arguments,
            cwd=assembly.parent, manifest=manifest, settings_data=settings,
            started_ms=bounds["startedMs"], ended_ms=bounds["endedMs"], settings_directory="stores")
        sequence = receipt["commandSequence"]
        sequences.append(sequence)
        read(f"proofs/category-command-{attempt}-{purpose}.json", 64 * 1024)
        read(f"proofs/execution-command-{sequence:04}.json", 64 * 1024)
        frozen = {**sdk.harness_catalog_runtime_inputs(inputs, frame["assemblyPath"]),
                  CATALOG_INPUTS: evidence.digest(inputs), "runtime-owner.json": hashlib.sha256(owner_data).hexdigest(),
                  f"runtime-input-{attempt}.json": hashlib.sha256(manifest_data).hexdigest()}
        if any(record.get("inputFiles", {}).get(path) != hashed for path, hashed in frozen.items()):
            raise evidence.ConformanceError("ProofMismatch")
        folder = ("discovery-" if purpose == "discovery" else "runtime-") + attempt
        transport = {
            "inputs": inputs, "expected_tests": expected, "manifest_data": manifest_data, "owner_data": owner_data,
            "manifest_sha256": hashlib.sha256(manifest_data).hexdigest(),
            "owner_sha256": hashlib.sha256(owner_data).hexdigest(),
            "completion_data": read(folder + "/completion.json", 64 * 1024),
            "started_ms": bounds["startedMs"], "ended_ms": bounds["endedMs"],
        }
        if purpose == "discovery":
            discovered = evidence.ingest_runtime_discovery(
                **transport, discoveries_data=read(folder + "/discovered.jsonl", 1024 * 1024))
            if (discovered["diagnosticCode"] != "None"
                    or {row["testIdentity"] for row in discovered["discoveries"]} != set(expected)):
                raise evidence.ConformanceError("WitnessMissing")
        else:
            witness_data = read(folder + "/witnesses.jsonl", 1024 * 1024)
            rows = [evidence.load_json(line) for line in witness_data.splitlines()]
            if len(rows) != len(expected):
                raise evidence.ConformanceError("WitnessMissing")
            proofs = {f'proof-{evidence._uuid(row["executionId"])}.json': read(
                folder + f'/proof-{row["executionId"]}.json', 64 * 1024) for row in rows}
            observed = evidence.ingest_runtime_attempt(**transport, witnesses_data=witness_data, proofs=proofs)
            witnesses = observed["witnesses"]
            if (observed["diagnosticCode"] != "None" or len(witnesses) != len(expected)
                    or {row["testIdentity"] for row in witnesses} != set(expected)
                    or any(row["status"] != "Passed" for row in witnesses)):
                raise evidence.ConformanceError("EvidenceIncomplete")
    if sequences != sorted(set(sequences)) or discovered is None or witnesses is None:
        raise evidence.ConformanceError("ProofMismatch")
    return MappingProxyType({
        "qualification": False, "scope": "harness-native-catalog", "code": "None",
        "witnesses": tuple(witnesses), "proofs": MappingProxyType(hashes),
        "startedMs": frame["discovery"]["startedMs"], "endedMs": frame["execution"]["endedMs"],
    })


def execute_contributor_journey(repository, run, inputs, source):
    import conformance_contributors as contributors
    import conformance_sdk_checks as sdk
    from conformance_sources import read_bounded

    inputs = evidence.admit_entity("RunInputs", inputs)
    if (type(run) is not OwnedRun or run.state != "Active" or run.live_children()
            or inputs["profileId"] != "harness" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id
            or Path(source) != run.root / "stores/snapshot"
            or evidence.source_manifest(repository) != inputs["sourceManifest"]):
        raise evidence.ConformanceError("OwnershipInvalid")
    evidence.verify_snapshot(source, inputs["sourceManifest"])
    registration_path = "tests/fixtures/conformance/Contributor/Contributor.conformance.json"
    original = contributors.admit_binding_project(
        Path(source) / registration_path.replace(".conformance.json", ".csproj"), "metadata")
    adapter = run.root / "stores/contributor-source"
    adapter.mkdir(mode=0o700)
    for relative, hashed in original.sources.items():
        target = adapter / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        raw = read_bounded(Path(source) / relative, evidence.MAX_PROOF_BYTES)
        if hashlib.sha256(raw).hexdigest() != hashed:
            raise evidence.ConformanceError("InputChanged")
        sdk.write_new(target, raw)
        target.chmod(0o600)
    project = adapter / original.project
    forwarding = project.parent / "ForwardingMetadataBinding.cs"
    good = read_bounded(forwarding, 64 * 1024)
    needle = b"inner = new(providerPackageSha256);\n        this.injectStaleReplay = injectStaleReplay;"
    if good.count(needle) != 1:
        raise evidence.ConformanceError("InputChanged")
    destination = run.root / "proofs/contributors"
    destination.mkdir(mode=0o700)
    owners, rows = [], []
    for label in ("good", "faulty", "corrected"):
        if evidence.source_manifest(repository) != inputs["sourceManifest"]:
            raise evidence.ConformanceError("InputChanged")
        forwarding.write_bytes(good.replace(needle, needle.replace(b"= injectStaleReplay;", b"= true;"))
                               if label == "faulty" else good)
        binding = contributors.admit_binding_project(project, "metadata")
        child = OwnedRun.allocate(destination / label, repository, profile="metadata")
        child.deadline = min(child.deadline, run.deadline)
        owners.append(child)
        try:
            contributors.execute_owned(
                repository, child, project=project, category="metadata",
                binding_inputs_sha256=binding.inputs_sha256, group_id=inputs["invocationGroupId"])
        except sdk._RuntimeObservationError:
            if label != "faulty":
                raise
        else:
            if label == "faulty":
                raise evidence.ConformanceError("EvidenceIncomplete")
        resources = child.resource_projection()
        if (child.state != "Released" or child.live_children()
                or any(row["state"] != "Released" for row in resources)):
            raise evidence.ConformanceError("CleanupIncomplete")
        child_inputs = evidence.admit_entity("RunInputs", evidence.load_json(
            read_bounded(child.root / "proofs/contributor-inputs.json", evidence.MAX_REPORT_BYTES)))
        observed = contributors.inspect_metadata_binding_runtime(
            child.root, expected_inputs=child_inputs, expected_fault="stale-replay" if label == "faulty" else "none")
        for path in evidence.proof_manifest(child.root):
            (child.root / path).chmod(0o400)
        rows.append({
            "label": label, "path": child.root.relative_to(run.root).as_posix(), "inputs": child_inputs,
            "proofsSha256": evidence.digest(observed["proofs"]), "resources": resources,
        })
    if (evidence.source_manifest(repository) != inputs["sourceManifest"]
            or contributors.admit_binding_project(project, "metadata").inputs_sha256 != original.inputs_sha256):
        raise evidence.ConformanceError("InputChanged")
    sdk.write_new(run.root / CONTRIBUTOR_FRAME, evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False, "scope": "harness-contributor-journey",
        "inputsSha256": evidence.digest(inputs), "runs": rows,
    }))
    inspect_contributor_journey(run.root, expected_inputs=inputs)
    return tuple(owners)


def inspect_contributor_journey(root, *, expected_inputs):
    import conformance_contributors as contributors

    root = Path(root)
    inputs = evidence.admit_entity("RunInputs", expected_inputs)
    if inputs["profileId"] != "harness" or inputs["mode"] != "qualification":
        raise evidence.ConformanceError("UnsupportedProfile")
    hashed, raw = evidence._readonly_report_proof(root, CONTRIBUTOR_FRAME)
    frame = evidence._runtime_json(raw, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "scope": evidence._constant("harness-contributor-journey"),
        "inputsSha256": evidence._constant(evidence.digest(inputs)),
        "runs": evidence._list(evidence._record({
            "label": evidence._one_of("good", "faulty", "corrected"), "path": evidence.relative_path,
            "inputs": lambda row: evidence.admit_entity("RunInputs", row),
            "proofsSha256": evidence.sha256,
            "resources": evidence._list(lambda row: evidence.admit_entity("ResourceOwnership", row), 1, minimum=1),
        }), 3, minimum=3),
    }, limit=evidence.MAX_REPORT_BYTES)
    proofs, results, invariants, bindings, packages, run_ids, root_ids = (
        {CONTRIBUTOR_FRAME: hashed}, [], [], [], [], set(), set())
    for row, label in zip(frame["runs"], ("good", "faulty", "corrected")):
        child = row["inputs"]
        if (row["label"] != label or row["path"] != "proofs/contributors/" + label
                or child["profileId"] != "metadata" or child["mode"] != "diagnostic"
                or child["invocationGroupId"] != inputs["invocationGroupId"]
                or child["sourceManifest"] != inputs["sourceManifest"]
                or child["sourceRevision"] != inputs["sourceRevision"]
                or child["sourceState"] != inputs["sourceState"]
                or child["catalogSha256"] != inputs["catalogSha256"]
                or child["sdkSha256"] != inputs["sdkSha256"]
                or child["runId"] in run_ids or child["runId"] == inputs["runId"]):
            raise evidence.ConformanceError("InputChanged")
        run_ids.add(child["runId"])
        observed = contributors.inspect_metadata_binding_runtime(
            root / row["path"], expected_inputs=child, expected_fault="stale-replay" if label == "faulty" else "none")
        owner_hash, owner_raw = evidence._readonly_report_proof(root / row["path"], "runtime-owner.json")
        owner = evidence.load_json(owner_raw)
        if (evidence.digest(observed["proofs"]) != row["proofsSha256"]
                or owner["rootId"] in root_ids
                or any(resource["runId"] != child["runId"] or resource["rootId"] != owner["rootId"]
                       or resource["state"] != "Released" or resource["childPid"] != 0
                       or resource["childStartSha256"] != "0" * 64
                       or resource["diagnosticCode"] != "None" for resource in row["resources"])):
            raise evidence.ConformanceError("ProofMismatch")
        root_ids.add(owner["rootId"])
        proofs.update({row["path"] + "/" + path: value for path, value in observed["proofs"].items()})
        proofs[row["path"] + "/runtime-owner.json"] = owner_hash
        adapter = child["bindings"][0]["adapterId"]
        common_packages = tuple(sorted(
            (package for package in child["packages"] if package["packageId"] != adapter),
            key=lambda package: package["packageId"]))
        selected = [package["sha256"] for package in child["packages"] if package["packageId"] == adapter]
        if len(selected) != 1 or observed["sessionOrigins"] != 86 or len(observed["witnesses"]) != 76:
            raise evidence.ConformanceError("WitnessMissing")
        invariants.append(evidence.digest(common_packages))
        bindings.append(child["invocation"][1])
        packages.append(selected[0])
        results.append(observed)
    if (len(set(invariants)) != 1 or bindings[0] != bindings[2] or bindings[0] == bindings[1]
            or packages[0] == packages[1] or packages[1] == packages[2]):
        raise evidence.ConformanceError("InputChanged")
    return MappingProxyType({
        "qualification": False, "scope": "harness-contributor-journey", "code": "None",
        "runs": tuple(results), "proofs": MappingProxyType(proofs),
    })


def execute_category_controls(repository, run, inputs):
    import importlib.util
    import conformance_sdk_checks as sdk
    from conformance_sources import NativeCategoryEvaluation, read_bounded

    inputs = evidence.admit_entity("RunInputs", inputs)
    if (type(run) is not OwnedRun or run.state != "Active" or run.live_children()
            or inputs["profileId"] != "harness" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id
            or evidence.source_manifest(repository) != inputs["sourceManifest"]):
        raise evidence.ConformanceError("OwnershipInvalid")
    if inputs["sourceState"] not in ("clean-local", "clean-ci"):
        raise evidence.ConformanceError("InputChanged")
    source_path = "tests/tooling/test_conformance_evidence.py"
    source = Path(repository) / source_path
    if hashlib.sha256(read_bounded(source, 1024 * 1024)).hexdigest() != inputs["sourceManifest"][source_path]:
        raise evidence.ConformanceError("InputChanged")
    spec = importlib.util.spec_from_file_location("test_conformance_evidence", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    destination = run.root / "proofs/category-controls"
    destination.mkdir(mode=0o700)
    evaluations, rows = [], []
    for profile in ("metadata", "artifacts"):
        child, child_root = None, destination / profile

        def execute(invocation):
            nonlocal child
            if invocation.profiles != (profile,) or invocation.evidence != child_root or child is not None:
                raise evidence.ConformanceError("InputChanged")
            child = OwnedRun.allocate(child_root, repository, profile=profile)
            child.deadline = min(child.deadline, run.deadline)
            native = sdk.execute_owned(
                repository, child, category=profile, qualify=True, group_id=inputs["invocationGroupId"])
            if type(native) is not NativeCategoryEvaluation or native._source._run is not child:
                raise evidence.ConformanceError("OwnershipInvalid")
            evaluations.append(native)
            return evidence.complete_native_category_invocation(invocation, native)

        try:
            status = module.run_native_category_controls(
                ["--profile", profile, "--evidence", str(child_root)], executor=execute)
            if (type(status) is not int or status != 0 or child is None
                    or len(evaluations) != len(rows) + 1):
                raise evidence.ConformanceError("EvidenceIncomplete")
        finally:
            if child is not None and child.state in ("Allocated", "Active"):
                child.transition("Settling")
            if child is not None and child.state == "Settling":
                child.release()
        child_inputs = evidence.admit_entity("RunInputs", evidence.load_json(read_bounded(
            child.root / f"proofs/category-{profile}-qualification-run-inputs.json", evidence.MAX_REPORT_BYTES)))
        original_path = f"proofs/category-{profile}-qualification-report.json"
        report_path = f"proofs/category-{profile}-fixture-qualification-report.json"
        _, original = evidence._readonly_report_proof(child.root, original_path)
        report_sha, report = evidence._readonly_report_proof(child.root, report_path)
        origin = evidence.native_category_qualification_receipt(
            child, report, original_report_data=original, expected_inputs=child_inputs,
            native_evaluation=evaluations[-1])
        control_path = f"proofs/category-{profile}-native-controls.json"
        control_sha, _ = evidence._readonly_report_proof(child.root, control_path)
        rows.append({
            "profileId": profile, "path": child.root.relative_to(run.root).as_posix(), "inputs": child_inputs,
            "reportPath": report_path, "qualificationOrigin": origin,
            "controlOrigin": {
                "kind": "native-category-control-observation", "inputsSha256": evidence.digest(child_inputs),
                "reportSha256": report_sha, "proofPath": control_path, "proofSha256": control_sha,
            },
        })
    sdk.write_new(run.root / CATEGORY_CONTROL_FRAME, evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False, "scope": "harness-native-category-controls",
        "inputsSha256": evidence.digest(inputs), "runs": rows,
    }))
    inspect_category_controls(run.root, expected_inputs=inputs)
    return tuple(evaluations)


def inspect_category_controls(root, *, expected_inputs):
    root = Path(root)
    inputs = evidence.admit_entity("RunInputs", expected_inputs)
    if inputs["profileId"] != "harness" or inputs["mode"] != "qualification":
        raise evidence.ConformanceError("UnsupportedProfile")
    if inputs["sourceState"] not in ("clean-local", "clean-ci"):
        raise evidence.ConformanceError("InputChanged")
    hashed, raw = evidence._readonly_report_proof(root, CATEGORY_CONTROL_FRAME)
    frame = evidence._runtime_json(raw, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "scope": evidence._constant("harness-native-category-controls"),
        "inputsSha256": evidence._constant(evidence.digest(inputs)),
        "runs": evidence._list(evidence._record({
            "profileId": evidence._one_of("metadata", "artifacts"), "path": evidence.relative_path,
            "inputs": lambda row: evidence.admit_entity("RunInputs", row),
            "reportPath": evidence.relative_path,
            "qualificationOrigin": evidence.admit_qualification_origin,
            "controlOrigin": evidence._record({
                "kind": evidence._constant("native-category-control-observation"),
                "inputsSha256": evidence.sha256, "reportSha256": evidence.sha256,
                "proofPath": evidence.relative_path, "proofSha256": evidence.sha256,
            }),
        }), 2, minimum=2),
    }, limit=evidence.MAX_REPORT_BYTES)
    results, proofs, identities = [], {CATEGORY_CONTROL_FRAME: hashed}, {inputs["runId"]}
    for row, profile in zip(frame["runs"], ("metadata", "artifacts")):
        child = row["inputs"]
        if (row["profileId"] != child["profileId"] or row["profileId"] != profile
                or row["path"] != "proofs/category-controls/" + profile
                or child["mode"] != "qualification" or child["runId"] in identities
                or any(child[key] != inputs[key] for key in (
                    "invocationGroupId", "sourceRevision", "sourceState", "sourceManifest",
                    "catalogSha256", "sdkSha256"))
                or row["reportPath"] != f"proofs/category-{profile}-fixture-qualification-report.json"):
            raise evidence.ConformanceError("InputChanged")
        identities.add(child["runId"])
        child_root = root / row["path"]
        _, report = evidence._readonly_report_proof(child_root, row["reportPath"])
        inspected = evidence.inspect_receipted_native_category_controls(
            child_root, report, expected_inputs=child,
            expected_report_sha256=row["qualificationOrigin"]["reportSha256"],
            qualification_origin=row["qualificationOrigin"], control_origin=row["controlOrigin"])
        original_path = row["qualificationOrigin"]["originalReportPath"]
        original_sha, original = evidence._readonly_report_proof(child_root, original_path)
        original = evidence.admit_entity("QualificationReport", evidence.load_json(original))
        child_proofs = {
            **original["proofs"], original_path: original_sha,
            row["reportPath"]: row["qualificationOrigin"]["reportSha256"],
            row["controlOrigin"]["proofPath"]: row["controlOrigin"]["proofSha256"],
        }
        source_path = f"proofs/category-{profile}-native-controls-source.py"
        source_sha, _ = evidence._readonly_report_proof(child_root, source_path)
        child_proofs[source_path] = source_sha
        proofs.update({row["path"] + "/" + path: value for path, value in child_proofs.items()})
        results.append(inspected)
    return MappingProxyType({
        "qualification": False, "scope": "harness-native-category-controls", "code": "None",
        "runs": tuple(results), "proofs": MappingProxyType(proofs),
    })


def _read_frame(root, path):
    _, raw = evidence._readonly_report_proof(root, path)
    return evidence.load_json(raw)


def _report_material(root, inputs):
    import conformance_inherited as inherited
    from conformance_case_catalog import expected_cases

    root = Path(root)
    inputs = evidence.admit_entity("RunInputs", inputs)
    catalog = inspect_catalog(root, inputs)
    contributors = inspect_contributor_journey(root, expected_inputs=inputs)
    categories = inspect_category_controls(root, expected_inputs=inputs)
    owner = _read_frame(root, "runtime-owner.json")
    observation_sha, observation_data = evidence._readonly_report_proof(root, OBSERVATION)
    observation = evidence._runtime_json(observation_data, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "scope": evidence._constant("harness-control-observation"),
        "runId": evidence._constant(inputs["runId"]), "rootId": evidence._constant(owner["rootId"]),
        "inputsSha256": evidence._constant(evidence.digest(inputs)),
        "startedMs": evidence._number, "endedMs": evidence._number,
    })
    started, ended = observation["startedMs"], observation["endedMs"]
    if not 0 <= ended - started < inputs["budgets"]["profileSeconds"] * 1000:
        raise evidence.ConformanceError("DeadlineExceeded")
    tooling = _read_frame(root, TOOLING_SUMMARY)
    inherited.verify_controller_tooling(root, tooling, inputs, owner)
    _, tooling_document = inherited._read_controller_tooling(root, inputs, owner)
    if not started <= tooling_document["startedMs"] <= tooling_document["endedMs"] <= ended:
        raise evidence.ConformanceError("ProofMismatch")
    contributor_frame = _read_frame(root, CONTRIBUTOR_FRAME)
    category_frame = _read_frame(root, CATEGORY_CONTROL_FRAME)
    controls, child_resources = {}, []
    all_witnesses = [*catalog["witnesses"]]
    for row, observed in zip(contributor_frame["runs"], contributors["runs"]):
        all_witnesses.extend(observed["witnesses"])
        child_resources.extend(row["resources"])
    for row in category_frame["runs"]:
        child_root = root / row["path"]
        report = _read_frame(child_root, row["qualificationOrigin"]["originalReportPath"])
        all_witnesses.extend(report["witnesses"])
        child_resources.extend(report["resources"])
        controls[row["profileId"]] = _read_frame(child_root, row["controlOrigin"]["proofPath"])
    if (any(row["startedMs"] < started or row["endedMs"] > ended for row in all_witnesses)
            or len({row["rootId"] for row in child_resources}) != 5
            or any(row["rootId"] == owner["rootId"] or row["state"] != "Released"
                   or row["childPid"] != 0 for row in child_resources)):
        raise evidence.ConformanceError("CleanupIncomplete")
    proofs = {**catalog["proofs"], **contributors["proofs"], **categories["proofs"],
              OBSERVATION: observation_sha}
    for path in (TOOLING_SUMMARY, "proofs/inherited-controller-tooling.json", COMPLETION_INPUTS):
        proofs[path] = evidence._readonly_report_proof(root, path)[0]
    results, source_proofs = [], {}
    anchors = catalog["witnesses"]
    anchor_hashes = {row["proofSha256"] for row in anchors}
    for case in expected_cases("harness"):
        sources = {}
        if case.case_id == "QC-01":
            sources["catalog"] = proofs[CATALOG_FRAME]
        if case.case_id in ("QC-30", "QC-31", "QC-32"):
            sources["contributorJourney"] = proofs[CONTRIBUTOR_FRAME]
        if case.case_id in TOOLING_BASIS:
            sources["tooling"] = {
                "proofPath": "proofs/inherited-controller-tooling.json",
                "proofSha256": proofs["proofs/inherited-controller-tooling.json"],
                "tests": _tooling_case_sources(case.case_id, tooling_document["result"]),
            }
        if case.case_id in NATIVE_CONTROL_BASIS:
            selected = NATIVE_CONTROL_BASIS[case.case_id]
            for profile, document in controls.items():
                if any(method not in document["phases"][phase]["observedTests"]
                       for phase, method in selected):
                    raise evidence.ConformanceError("WitnessMissing")
                row = next(row for row in category_frame["runs"] if row["profileId"] == profile)
                sources[profile] = {
                    "proofPath": row["path"] + "/" + row["controlOrigin"]["proofPath"],
                    "proofSha256": row["controlOrigin"]["proofSha256"],
                    "methods": [{"phase": phase, "method": method} for phase, method in selected],
                }
        if not sources:
            raise evidence.ConformanceError("WitnessMissing")
        path = f"proofs/harness-{case.case_id}-sources.json"
        raw = evidence.canonical_bytes({
            "schemaVersion": 1, "qualification": False, "scope": "harness-control-derivation",
            "inputsSha256": evidence.digest(inputs), "caseId": case.case_id,
            "controls": case.controls, "sources": sources,
            "catalogAnchorExecutions": [row["executionId"] for row in anchors],
            "startedMs": started, "endedMs": ended,
        })
        hashed = hashlib.sha256(raw).hexdigest()
        source_proofs[path], proofs[path] = raw, hashed
        attempt = evidence.admit_entity("Attempt", {
            "sequence": 1, "startedMs": started, "endedMs": ended, "status": "Passed",
            "witnessIds": [row["executionId"] for row in anchors],
            "proofSha256": sorted({hashed, *anchor_hashes}), "diagnosticCode": "None",
        })
        results.append(evidence._catalog_case_result(inputs, case, "Passed", (attempt,)))
    return {
        "results": results, "witnesses": anchors, "proofs": proofs, "sourceProofs": source_proofs,
        "postInputSha256": proofs[COMPLETION_INPUTS], "childResources": child_resources,
    }


def inspect_harness_report(root, report_data, *, expected_inputs):
    report = evidence.admit_entity("QualificationReport", evidence.load_json(report_data))
    inputs = evidence.admit_entity("RunInputs", expected_inputs)
    if (inputs["profileId"] != "harness" or inputs["mode"] != "qualification"
            or report["inputs"] != inputs or report["qualification"]
            or report["state"] != "Incomplete" or report["scope"] != ("harness-runtime-diagnostic",)):
        raise evidence.ConformanceError("EvidenceIncomplete")
    material = _report_material(root, inputs)
    if any(evidence.digest(report[key]) != evidence.digest(material[key])
           for key in ("results", "witnesses", "proofs", "postInputSha256")):
        raise evidence.ConformanceError("ProofMismatch")
    for path, raw in material["sourceProofs"].items():
        if evidence._readonly_report_proof(root, path)[1] != raw:
            raise evidence.ConformanceError("ProofMismatch")
    return evidence.inspect_profile_report(
        root, report_data, expected_inputs=inputs,
        expected_report_sha256=hashlib.sha256(report_data).hexdigest())


@dataclass(frozen=True, repr=False)
class NativeHarnessEvaluation:
    _source: "NativeHarnessSources"
    report_data: bytes
    commands: tuple

    def verify_report_origin(self, run, inputs, report):
        if (type(run) is not OwnedRun or type(self._source) is not NativeHarnessSources
                or self._source._run is not run or self._source._evaluation is not self
                or run.state != "Released"):
            raise evidence.ConformanceError("OwnershipInvalid")
        if (not report.get("resources")
                or evidence.canonical_bytes(report["resources"])
                != evidence.canonical_bytes(run.resource_projection())
                or any(row["state"] != "Released" for row in report["resources"])):
            raise evidence.ConformanceError("CleanupIncomplete")
        original = evidence.load_json(self.report_data)
        if (evidence.digest(inputs) != evidence.digest(original["inputs"])
                or evidence.digest({key: value for key, value in report.items() if key != "resources"})
                != evidence.digest({key: value for key, value in original.items() if key != "resources"})):
            raise evidence.ConformanceError("ProofMismatch")
        for path, hashed in self.commands:
            if evidence._readonly_report_proof(run.root, path)[0] != hashed or report["proofs"].get(path) != hashed:
                raise evidence.ConformanceError("ProofMismatch")
        self._source._verify_children(inputs)


class NativeHarnessSources:
    def __init__(self, run):
        if (type(run) is not OwnedRun or run.state != "Active"
                or run.command_sequence != 0 or run.live_children()):
            raise evidence.ConformanceError("OwnershipInvalid")
        self._run = run
        self._evaluation = None
        self._contributors = ()
        self._categories = ()

    def _verify_children(self, inputs):
        run = self._run
        contributor_frame = _read_frame(run.root, CONTRIBUTOR_FRAME)
        category_frame = _read_frame(run.root, CATEGORY_CONTROL_FRAME)
        if len(self._contributors) != 3 or len(self._categories) != 2:
            raise evidence.ConformanceError("OwnershipInvalid")
        for owner, row in zip(self._contributors, contributor_frame["runs"]):
            if (type(owner) is not OwnedRun or owner.root != run.root / row["path"]
                    or owner.run_id != row["inputs"]["runId"] or owner.state != "Released"
                    or owner.live_children()
                    or evidence.digest(owner.resource_projection()) != evidence.digest(row["resources"])):
                raise evidence.ConformanceError("CleanupIncomplete")
        for native, row in zip(self._categories, category_frame["runs"]):
            owner = native._source._run
            if owner.root != run.root / row["path"] or row["inputs"]["invocationGroupId"] != inputs["invocationGroupId"]:
                raise evidence.ConformanceError("OwnershipInvalid")
            _, original = evidence._readonly_report_proof(owner.root, row["qualificationOrigin"]["originalReportPath"])
            _, qualified = evidence._readonly_report_proof(owner.root, row["reportPath"])
            observed = evidence.native_category_qualification_receipt(
                owner, qualified, original_report_data=original, expected_inputs=row["inputs"],
                native_evaluation=native)
            if observed != row["qualificationOrigin"]:
                raise evidence.ConformanceError("ProofMismatch")

    def execute(self, repository, *, group_id):
        import conformance_inherited as inherited
        import conformance_sdk_checks as sdk

        run = self._run
        if run.state != "Active" or run.command_sequence != 0 or self._evaluation is not None:
            raise evidence.ConformanceError("OwnershipInvalid")
        inputs, assembly, source, capture = prepare_catalog(repository, run, group_id=group_id)
        execute_catalog(run, inputs, assembly)
        self._contributors = execute_contributor_journey(repository, run, inputs, source)
        self._categories = execute_category_controls(repository, run, inputs)
        tooling = inherited.run_controller_tooling(repository, run, inputs["sourceManifest"])
        sdk.write_new(run.root / TOOLING_SUMMARY, evidence.canonical_bytes(tooling))
        post = evidence.capture_profile_inputs(run, repository, source, **{
            **capture, "observed_environment": sdk.environment(run, phase="completion")})
        evidence.verify_input_recomputation(inputs, post)
        sdk.write_new(run.root / COMPLETION_INPUTS, evidence.canonical_bytes(post))
        self._verify_children(inputs)
        ended = time.monotonic()
        if ended >= run.deadline or run.live_children():
            raise evidence.ConformanceError("DeadlineExceeded")
        sdk.write_new(run.root / OBSERVATION, evidence.canonical_bytes({
            "schemaVersion": 1, "qualification": False, "scope": "harness-control-observation",
            "runId": run.run_id, "rootId": run.root_id, "inputsSha256": evidence.digest(inputs),
            "startedMs": run.started * 1000, "endedMs": ended * 1000,
        }))
        material = _report_material(run.root, inputs)
        for path, raw in material["sourceProofs"].items():
            sdk.write_new(run.root / path, raw)
        report = evidence.admit_entity("QualificationReport", {
            "schemaVersion": 1, "catalogRevision": inputs["catalogRevision"], "inputs": inputs,
            **{key: material[key] for key in ("results", "witnesses", "proofs", "postInputSha256")},
            "resources": run.resource_projection(), "state": "Incomplete", "qualification": False,
            "scope": ["harness-runtime-diagnostic"],
        })
        raw = evidence.canonical_bytes(report)
        sdk.write_new(run.root / "proofs/harness-runtime-report.json", raw)
        inspect_harness_report(run.root, raw, expected_inputs=inputs)
        commands = []
        for path, hashed in report["proofs"].items():
            if path.startswith("proofs/execution-command-") and path.endswith(".json"):
                sequence = int(Path(path).stem.rsplit("-", 1)[1])
                if hashlib.sha256(run.read_execution_record(sequence)).hexdigest() != hashed:
                    raise evidence.ConformanceError("ProofMismatch")
                commands.append((path, hashed))
        if len(commands) != 2:
            raise evidence.ConformanceError("OwnershipInvalid")
        self._evaluation = NativeHarnessEvaluation(self, raw, tuple(commands))
        return self._evaluation


def execute(repository, destination, *, group_id=None):
    import conformance_sdk_checks as sdk
    from conformance_execution import native_execution_supported

    if not native_execution_supported():
        raise evidence.ConformanceError("PrerequisiteMissing")
    group_id = str(uuid.uuid4()) if group_id is None else evidence._uuid(group_id)
    ci_revision = os.environ.get("GITHUB_SHA") if os.environ.get("GITHUB_ACTIONS") == "true" else None
    if (os.environ.get("GITHUB_ACTIONS") == "true" and ci_revision is None
            or evidence.source_identity(repository, ci_revision=ci_revision)["sourceState"]
            not in ("clean-local", "clean-ci")):
        raise evidence.ConformanceError("InputChanged")
    run = OwnedRun.allocate(destination, repository, profile="harness")
    try:
        run.transition("Active")
        native = NativeHarnessSources(run).execute(repository, group_id=group_id)
    finally:
        if run.state in ("Allocated", "Active"):
            run.transition("Settling")
        if run.state == "Settling":
            run.release()
    original = evidence.admit_entity("QualificationReport", {
        **evidence.load_json(native.report_data), "resources": run.resource_projection()})
    raw = evidence.canonical_bytes(original)
    sdk.write_new(run.root / ORIGINAL_REPORT, raw)
    qualified = derive_native_qualification(
        run, raw, expected_inputs=original["inputs"], native_evaluation=native)
    sdk.write_new(run.root / QUALIFIED_REPORT, evidence.canonical_bytes(qualified))
    return native


def derive_native_qualification(run, original_report_data, *, expected_inputs, native_evaluation):
    if type(native_evaluation) is not NativeHarnessEvaluation:
        raise evidence.ConformanceError("OwnershipInvalid")
    original = evidence.admit_entity("QualificationReport", evidence.load_json(original_report_data))
    native_evaluation.verify_report_origin(run, expected_inputs, original)
    inspect_harness_report(run.root, original_report_data, expected_inputs=expected_inputs)
    evidence._require_qualifying_outcomes(original)
    return evidence.admit_entity("QualificationReport", {
        **original, "state": "Complete", "qualification": True, "scope": ["harness-fixture-qualification"]})


def inspect_native_qualification(
        run, report_data, *, original_report_data, expected_inputs, native_evaluation):
    expected = derive_native_qualification(
        run, original_report_data, expected_inputs=expected_inputs, native_evaluation=native_evaluation)
    report = evidence.admit_entity("QualificationReport", evidence.load_json(report_data))
    if report != expected:
        raise evidence.ConformanceError("ProofMismatch")
    return _qualification_summary(report_data, report, scope="native-harness-fixture-qualification")


def _qualification_summary(report_data, report, *, scope):
    return MappingProxyType({
        "qualification": True, "baselineQualification": False, "code": "None", "scope": scope,
        "profileId": "harness", "reportSha256": hashlib.sha256(report_data).hexdigest(),
        "caseCount": len(report["results"]), "witnessCount": len(report["witnesses"]),
        "caseStates": MappingProxyType({
            state: sum(row["status"] == state for row in report["results"]) for state in evidence.STATUSES}),
    })


def qualification_receipt(
        run, report_data, *, original_report_data, expected_inputs, native_evaluation):
    inspected = inspect_native_qualification(
        run, report_data, original_report_data=original_report_data,
        expected_inputs=expected_inputs, native_evaluation=native_evaluation)
    original_sha, original = evidence._readonly_report_proof(run.root, ORIGINAL_REPORT)
    if original != original_report_data:
        raise evidence.ConformanceError("ProofMismatch")
    return MappingProxyType({
        "kind": "native-harness-fixture-qualification", "inputsSha256": evidence.digest(expected_inputs),
        "reportSha256": inspected["reportSha256"], "originalReportPath": ORIGINAL_REPORT,
        "originalReportSha256": original_sha, "resourcesSha256": evidence.digest(run.resource_projection()),
    })


def inspect_receipted_qualification(
        root, report_data, *, expected_inputs, expected_report_sha256, qualification_origin):
    if qualification_origin is None:
        raise evidence.ConformanceError("OwnershipInvalid")
    inputs = evidence.admit_entity("RunInputs", expected_inputs)
    origin = evidence.admit_qualification_origin(qualification_origin, profile="harness")
    if (inputs["profileId"] != "harness" or origin["inputsSha256"] != evidence.digest(inputs)
            or origin["reportSha256"] != evidence.sha256(expected_report_sha256)
            or origin["originalReportPath"] != ORIGINAL_REPORT):
        raise evidence.ConformanceError("InputChanged")
    if (not isinstance(report_data, bytes) or len(report_data) > evidence.MAX_REPORT_BYTES
            or hashlib.sha256(report_data).hexdigest() != origin["reportSha256"]):
        raise evidence.ConformanceError("ProofMismatch")
    original_sha, original_data = evidence._readonly_report_proof(root, ORIGINAL_REPORT)
    if original_sha != origin["originalReportSha256"]:
        raise evidence.ConformanceError("ProofMismatch")
    original = evidence.admit_entity("QualificationReport", evidence.load_json(original_data))
    inspect_harness_report(root, original_data, expected_inputs=inputs)
    evidence._require_qualifying_outcomes(original)
    if (not original["resources"] or any(row["state"] != "Released" for row in original["resources"])
            or evidence.digest(original["resources"]) != origin["resourcesSha256"]):
        raise evidence.ConformanceError("CleanupIncomplete")
    report = evidence.admit_entity("QualificationReport", evidence.load_json(report_data))
    expected = evidence.admit_entity("QualificationReport", {
        **original, "state": "Complete", "qualification": True, "scope": ["harness-fixture-qualification"]})
    if report != expected:
        raise evidence.ConformanceError("ProofMismatch")
    return _qualification_summary(report_data, report, scope="trusted-native-harness-fixture-qualification")
