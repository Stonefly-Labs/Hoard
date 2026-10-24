"""Bounded Linux SDK/logger diagnostics, never provider qualification.

Historical preparation is sealed and verified before any candidate compilation.
Only closed diagnostic codes, counts and hashes may reach the CI console.
Copied smoke-lock preparation rebinds only current local archive hashes; an
independent fresh cache then replays that unchanged graph in locked mode.
"""

import argparse
import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import time
import uuid
import zipfile
from xml.sax.saxutils import escape

import conformance_baselines as baselines
import conformance_evidence as evidence
from conformance_case_catalog import catalog_admission_witnesses
from conformance_execution import OwnedRun, capture_control, native_execution_supported, no_symlinks
from conformance_lock_preparation import prepare_project_lock, rebind_local_archives, verify_project_lock
from foundation_evidence import canonicalize_acceptance_archive


CONTRACTS = "tests/contracts"
SDK = f"{CONTRACTS}/Hoard.Testing.Conformance"
LOGGER = f"{CONTRACTS}/Hoard.Conformance.TestLogger"
TESTS = f"{CONTRACTS}/Hoard.Conformance.Tests"
MEMORY = "tests/fixtures/metadata/Memory/Memory.csproj"
MEMORY_BINDING = "tests/fixtures/conformance/Bindings/Memory/Memory.csproj"
SQLITE = "tests/fixtures/metadata/Sqlite/Sqlite.csproj"
SQLITE_BINDING = "tests/fixtures/conformance/Bindings/Sqlite/Sqlite.csproj"
LOCAL_PACKAGES = (
    "Hoard.Abstractions", "Hoard.Testing.Conformance", "Hoard.Conformance.TestLogger",
    "Hoard.Fixtures.Metadata.Memory", "Hoard.Fixtures.Conformance.Bindings.Memory",
    "Hoard.Fixtures.Metadata.Sqlite", "Hoard.Fixtures.Conformance.Bindings.Sqlite",
)
BINDING_TEST_PREFIX = "Hoard.Fixtures.Conformance.Consumer.MemoryBindingTests."
BINDING_OWNERSHIP_PREFIX = "Hoard.Fixtures.Conformance.Consumer.MemoryBindingOwnershipTests."
SQLITE_BINDING_PREFIX = "Hoard.Fixtures.Conformance.Consumer.SqliteBindingTests."
SQLITE_MECHANISM_PREFIX = "Hoard.Fixtures.Conformance.Consumer.SqliteMechanismTests."
BINDING_TEST_PREFIXES = (BINDING_TEST_PREFIX, BINDING_OWNERSHIP_PREFIX, SQLITE_BINDING_PREFIX, SQLITE_MECHANISM_PREFIX)
PACKAGE_TEST_OUTPUT = "bin/package-diagnostic"
PACKAGE_TEST_PREFIX = "Hoard.Conformance.Tests.MemoryMechanismTests."
PACKAGE_TEST_METHOD = (PACKAGE_TEST_PREFIX +
                       "Compiled_common_consumers_execute_against_the_independent_memory_store")
OWNED = "Hoard.Conformance.Tests.OwnedResourceTests."
OWNED_FACTS = (
    "Fresh_private_leases_reject_forged_foreign_and_second_writer_authority",
    "Same_path_and_copied_marker_do_not_replace_native_directory_identity",
    "Symlink_ancestors_parent_swaps_and_permissions_cannot_redirect_ownership",
    "Caller_timeout_and_cancellation_retain_live_work_and_retry_preserves_failure",
    "Provider_task_failure_is_sanitized_and_cannot_be_replaced_by_a_success_task",
    "Preexisting_store_is_not_adopted_even_when_parent_permissions_are_private",
)
SMOKE = "Hoard.Testing.Conformance.LoggerSmokeTests."
# Exact source-owned xUnit display identities; discovery/totals cannot substitute.
SCENARIOS = (
    ("owned", tuple(OWNED + fact for fact in OWNED_FACTS), "None", "Passed", 0, "None"),
    ("parameter", (SMOKE + "Parameter(value: 1)", SMOKE + "Parameter(value: 2)"),
     "None", "Passed", 0, "None"),
    ("assertion", (SMOKE + "Assertion",), "AssertionFailed", "Failed", 1, "Assertion"),
    ("unknown", (SMOKE + "Unknown",), "UnknownDiagnostic", "Failed", 1, "Unknown"),
    ("skipped", (SMOKE + "Skipped",), "EvidenceIncomplete", "Incomplete", 0, "SkippedOrUnknown"),
    ("stdout", (SMOKE + "PassingOutput",), "UnknownDiagnostic", "Passed", 0, "None"),
    ("ranges", tuple(
        "Hoard.Conformance.Tests.RuntimeLoggerTests.Finite_version_ranges_preserve_exact_parameter_identity"
        + f'(range: "{value}")' for value in ("[1.2.0,2.0.0)", "(2.0.0,1.0.0]", "[1.2.3]")),
     "None", "Passed", 0, "None"),
    ("catalog", catalog_admission_witnesses(), "None", "Passed", 0, "None"),
    ("declarations", tuple("Hoard.Conformance.Tests.BindingContractTests." + method for method in (
        "Binding_snapshots_capture_closed_actual_declarations_without_outcome_labels",
        "Binding_snapshots_reject_missing_faults_before_emitting_input_bytes")),
     "None", "Passed", 0, "None"),
    ("enums", tuple(
        "Hoard.Conformance.Tests.RuntimeLoggerTests.Finite_enum_parameters_preserve_exact_parent_expected_identity"
        + f"(category: {category})" for category in ("Metadata", "Artifacts")),
     "None", "Passed", 0, "None"),
    ("loaded", tuple("Hoard.Conformance.Tests.BindingContractTests." + method for method in (
        "Loaded_component_capture_observes_instance_bytes_and_type_not_interface_or_declaration_labels",
        "Loaded_component_projection_is_closed_and_never_renders_provider_objects_or_private_paths")),
     "None", "Passed", 0, "None"),
    ("discovery", (
        "Hoard.Conformance.Tests.RuntimeLoggerTests."
        "Discovery_preserves_exact_selected_parameters_without_fabricating_execution_witnesses",
        *(("Hoard.Conformance.Tests.RuntimeLoggerTests."
           "Discovery_rejects_selected_parameter_source_or_duplicate_changes_without_erasing_prior_records"
           + f'(mutation: "{mutation}", code: {code})') for mutation, code in (
               ("parameter", "WitnessMissing"), ("source", "ProofMismatch"), ("duplicate", "EvidenceIncomplete")))),
     "None", "Passed", 0, "None"),
    ("sessions", tuple("Hoard.Conformance.Tests.BindingContractTests." + method for method in (
        "Observed_legacy_factory_uses_explicit_setup_without_case_id_routing",
        "Observed_metadata_sessions_pin_factory_results_and_actual_component_instances",
        "Observed_metadata_origin_rejects_changed_declarations_and_missing_actual_fault_hooks",
        "Observed_artifact_sessions_pin_all_actual_roles_and_preserve_cleanup_ownership_on_capture_failure")),
     "None", "Passed", 0, "None"),
    ("origin-output", (SMOKE + "OriginOutput",), "None", "Passed", 0, "None"),
    ("origin-ingestion", (
        "Hoard.Conformance.Tests.RuntimeLoggerTests."
        "Origin_output_is_bound_to_the_actual_result_proof_without_private_component_labels",
        *(("Hoard.Conformance.Tests.RuntimeLoggerTests."
           "Invalid_origin_output_retains_prior_execution_without_accepting_replay_or_foreign_case"
           + f'(mutation: "{mutation}", code: {code})') for mutation, code in (
               ("missing", "EvidenceIncomplete"), ("digest", "ProofMismatch"),
               ("case", "ProofMismatch"), ("replay", "EvidenceIncomplete"),
               ("raw", "ProofMismatch"), ("instance", "ProofMismatch")))),
     "None", "Passed", 0, "None"),
    ("metadata-parity", (
        *(f'Hoard.Conformance.Tests.MetadataBindingTests.'
          f'Extraction_must_preserve_all_frozen_cases_parameters_controls_and_exclusions(binding: "{binding}")'
          for binding in ("sqlite", "memory")),
        *(f'Hoard.Conformance.Tests.MetadataBindingTests.Each_provider_requires_every_exact_corruption_parameter'
          f'(binding: "{binding}", mutation: "{mutation}", expected: {code})'
          for binding in ("sqlite", "memory")
          for mutation, code in (("complete", "None"), ("missing", "EvidenceIncomplete"), ("changed", "WitnessMissing"))),
        *(f'Hoard.Conformance.Tests.MetadataBindingTests.'
          f'Provider_cannot_replace_owned_expectations_with_a_shortened_passing_manifest(binding: "{binding}")'
          for binding in ("sqlite", "memory")),
        *(f'Hoard.Conformance.Tests.MetadataBindingTests.'
          f'Missing_logical_hook_rejects_instead_of_reducing_the_selected_agreement(binding: "{binding}")'
          for binding in ("sqlite", "memory")),
    ), "None", "Passed", 0, "None"),
    ("artifact-parity", (
        *(f'Hoard.Conformance.Tests.ArtifactBindingTests.'
          f'Extraction_must_preserve_all_frozen_streaming_authority_and_recovery_obligations(binding: "{binding}")'
          for binding in ("local", "object")),
        *(f'Hoard.Conformance.Tests.ArtifactBindingTests.'
          f'Both_streaming_handoff_rows_are_required_and_cannot_borrow_the_other_provider'
          f'(binding: "{binding}", mutation: "{mutation}", expected: {code})'
          for binding in ("local", "object")
          for mutation, code in (("complete", "None"), ("missing", "EvidenceIncomplete"), ("foreign", "WitnessMissing"))),
        *(f'Hoard.Conformance.Tests.ArtifactBindingTests.'
          f'Missing_authority_or_streaming_fault_hooks_cannot_reduce_the_agreement(binding: "{binding}")'
          for binding in ("local", "object")),
        "Hoard.Conformance.Tests.ArtifactBindingTests."
        "Simulation_cannot_take_local_restart_witnesses_or_remove_its_frozen_exclusions",
    ), "None", "Passed", 0, "None"),
    ("metadata-consumers", tuple("Hoard.Conformance.Tests.MetadataConsumerTests." + method for method in (
        "Precancelled_reservation_is_settled_before_the_next_operation",
        "Competing_create_consumer_rejects_successful_losers_instead_of_accepting_provider_results",
        "Common_consumer_propagates_cancellation_to_the_store_without_publishing_a_candidate"))
     + tuple("Hoard.Conformance.Tests.MetadataConsumerTests."
             + "Writer_contention_failure_releases_exclusion_and_joins_uncancelled_settlement"
             + f"(cancelCaller: {cancel})" for cancel in ("False", "True")),
     "None", "Passed", 0, "None"),
    ("memory-consumers", tuple(
        PACKAGE_TEST_METHOD + f'(consumer: "{consumer}")' for consumer in (
            "competing-creates", "revision-races", "exact-bounds", "scopes-and-intervals",
            "bounded-pages", "lease-fences")), "None", "Passed", 0, "None"),
    ("memory-publication-consumers", tuple(
        PACKAGE_TEST_PREFIX
        + "Compiled_publication_consumers_corroborate_actual_memory_records_and_references"
        + f'(consumer: "{consumer}")' for consumer in (
            "registry-isolation", "authorization-isolation", "entity-round-trips", "final-graph",
            "reference-replacement", "reference-aba", "telemetry-rollback", "all-page-queries",
            "oversized-pages")), "None", "Passed", 0, "None"),
    ("memory-mechanisms", tuple(PACKAGE_TEST_PREFIX + method for method in (
        "Noop_corruption_fails_the_common_assertion_and_real_memory_damage_passes_unchanged",
        "Compiled_receipt_corruption_consumer_preserves_all_shapes_and_original_ticket_classification",
        "Targeted_record_damage_fails_group_and_page_without_changing_the_damage",
        "Targeted_receipt_damage_preserves_original_ticket_and_independent_effects",
        "Partition_aliasing_fails_the_common_assertion_and_correct_memory_passes_unchanged")),
     "None", "Passed", 0, "None"),
    ("memory-record-consumers", tuple(PACKAGE_TEST_PREFIX + method for method in (
        "Compiled_page_corruption_consumer_preserves_complete_failures_and_restoration",
        "Compiled_absence_consumer_distinguishes_missing_records_from_corrupt_groups")),
     "None", "Passed", 0, "None"),
    ("memory-query-dimensions", tuple(
        PACKAGE_TEST_PREFIX + "Compiled_query_dimension_consumer_rejects_corruption_before_filtering"
        + f"(corruption: {corruption})" for corruption in (
            "CacheAuthorization", "AggregateAuthorization", "AggregateStart", "AggregateEnd", "LeaseResource")),
     "None", "Passed", 0, "None"),
    ("memory-time-consumers", tuple(
        PACKAGE_TEST_PREFIX + "Compiled_time_consumers_retain_exact_expiry_and_rollback_fences"
        + f'(consumer: "{consumer}")' for consumer in ("ticket-expiry", "lease-rollback")),
     "None", "Passed", 0, "None"),
    ("memory-cursor-consumer", (PACKAGE_TEST_PREFIX
        + "Compiled_cursor_consumer_checks_scope_size_foreign_epoch_and_live_resume",),
     "None", "Passed", 0, "None"),
    ("memory-identity-consumer", (PACKAGE_TEST_PREFIX
        + "Compiled_canonical_identity_consumer_preserves_text_and_rejects_forbidden_values",),
     "None", "Passed", 0, "None"),
    ("memory-observation-consumers", tuple(
        PACKAGE_TEST_PREFIX + "Compiled_observation_consumers_preserve_atomicity_and_uncertain_outcomes"
        + f'(consumer: "{consumer}")' for consumer in (
            "independent-candidate", "faulted-candidates", "grouped-root", "reconciliation-io",
            "lost-acknowledgment", "distinct-contributions"))
     + tuple(PACKAGE_TEST_PREFIX + "Grouped_read_failure_joins_the_started_writer_before_returning"
             + f"(cancelRead: {cancel})" for cancel in ("False", "True"))
     + (PACKAGE_TEST_PREFIX + "Compiled_writer_contention_consumer_never_classifies_an_unobserved_noncommit",),
     "None", "Passed", 0, "None"),
    ("memory-genuine-settlement", (PACKAGE_TEST_PREFIX
        + "Actual_work_settlement_task_remains_pending_after_the_public_deadline",),
     "None", "Passed", 0, "None"),
    ("memory-authority-consumers", tuple(
        PACKAGE_TEST_PREFIX + "Compiled_authority_consumers_preserve_evidence_protection_and_replay"
        + f'(consumer: "{consumer}")' for consumer in (
            "matching-evidence", "orphan-not-rollback", "protection-through-settlement", "replay-without-reacquisition")),
     "None", "Passed", 0, "None"),
    ("memory-lease-decision-consumers", (
        PACKAGE_TEST_PREFIX + "Compiled_lease_overflow_consumer_preserves_the_group_and_tombstone",
        *(PACKAGE_TEST_PREFIX + "Compiled_lease_expiry_consumer_rechecks_the_final_decision"
          + f"(action: {action})" for action in ("Renew", "Release", "Guard"))),
     "None", "Passed", 0, "None"),
    ("memory-deadline-consumers", tuple(
        PACKAGE_TEST_PREFIX + "Compiled_deadline_consumers_preserve_decision_and_work_ownership"
        + f'(consumer: "{consumer}")' for consumer in (
            "writer-budget", "cancellation-decision", "queue-capacity", "disposal-ownership", "known-exceptions")),
     "None", "Passed", 0, "None"),
    ("memory-failure-admission-consumers", tuple(
        PACKAGE_TEST_PREFIX + "Compiled_failure_and_admission_consumers_observe_actual_controls"
        + f'(consumer: "{consumer}")' for consumer in (
            "storage-capacity", "ledger-capacity", "explicit-admission", "invalid-budgets",
            "incomplete-cleanup", "safe-diagnostics"))
     + (PACKAGE_TEST_PREFIX + "Dropped_diagnostic_fails_the_common_assertion_and_observed_memory_passes_unchanged",),
     "None", "Passed", 0, "None"),
    ("memory-schema-consumers", tuple(
        PACKAGE_TEST_PREFIX + "Compiled_schema_consumers_preserve_explicit_upgrade_and_rejection"
        + f'(consumer: "{consumer}")' for consumer in (
            "unrecognized", "partial", "upgrade", "invalid-upgrade", "upgrade-contention", "future-corruption"))
     + (PACKAGE_TEST_PREFIX + "Logical_schema_fingerprint_tracks_raw_damage_without_decoding_or_repair",),
     "None", "Passed", 0, "None"),
    ("memory-continuation-corruption-consumers", tuple(
        PACKAGE_TEST_PREFIX + "Compiled_continuation_corruption_consumer_preserves_valid_resume"
        + f"(corruption: {corruption})" for corruption in (
            "Null", "Omitted", "WrongType", "Empty", "OddHex", "InvalidHex"))
     + (PACKAGE_TEST_PREFIX
        + "Noop_continuation_damage_fails_the_common_assertion_and_real_memory_damage_passes_unchanged",),
     "None", "Passed", 0, "None"),
    ("memory-binding-legacy", tuple(BINDING_TEST_PREFIX +
        'Explicit_legacy_factory_executes_unchanged_schema_consumers(consumer: "' + consumer + '")'
        for consumer in ("upgrade", "invalid-upgrade", "upgrade-contention")),
     "None", "Passed", 0, "None"),
    ("memory-binding-controls", (
        *(BINDING_TEST_PREFIX + 'Typed_adapter_controls_execute_unchanged_common_consumers(consumer: "' + consumer + '")'
          for consumer in ("receipts", "record-pages", "capacity", "ledger", "writer", "diagnostics", "publication", "cleanup")),
        *(BINDING_TEST_PREFIX + "Typed_adapter_continuation_damage_preserves_exact_valid_resume(corruption: " + corruption + ")"
          for corruption in ("Null", "Omitted", "WrongType", "Empty", "OddHex", "InvalidHex")),
        BINDING_TEST_PREFIX + "Disposal_registers_actual_pending_work_and_never_claims_physical_release",
        BINDING_TEST_PREFIX + "Independent_snapshot_observes_committed_state_while_a_read_is_held"),
     "None", "Passed", 0, "None"),
    ("memory-binding-owned-resource", (BINDING_OWNERSHIP_PREFIX
        + "Actual_allocator_retains_pending_memory_work_and_retry_preserves_the_failed_observation",),
     "None", "Passed", 0, "None"),
    ("sqlite-logical", tuple(SQLITE_BINDING_PREFIX
        + 'Compiled_logical_consumers_execute_through_the_independent_sqlite_binding(consumer: "' + consumer + '")'
        for consumer in (
            "competing-creates", "revision-races", "exact-bounds", "scopes-and-intervals", "bounded-pages",
            "lease-fences", "registry-isolation", "authorization-isolation", "final-graph", "reference-replacement",
            "reference-aba", "telemetry-rollback", "all-page-queries", "oversized-pages", "canonical-identity",
            "ticket-expiry", "lease-rollback", "independent-candidate", "faulted-candidates", "grouped-root",
            "reconciliation-io", "lost-acknowledgment", "distinct-contributions", "reconciliation-writer",
            "cancellation-decision", "queue-capacity", "disposal-ownership", "known-exceptions",
            "matching-evidence", "orphan-not-rollback", "replay-without-reacquisition", "lease-overflow",
            "absence-and-corruption")), "None", "Passed", 0, "None"),
    ("sqlite-admission", tuple(SQLITE_BINDING_PREFIX
        + 'Compiled_admission_consumers_execute_before_actual_schema_admission(consumer: "' + consumer + '")'
        for consumer in ("explicit-admission", "invalid-budgets")), "None", "Passed", 0, "None"),
    ("sqlite-query-dimensions", tuple(SQLITE_BINDING_PREFIX
        + "Compiled_query_dimension_consumers_check_raw_sqlite_damage_before_filtering(corruption: " + corruption + ")"
        for corruption in ("CacheAuthorization", "AggregateAuthorization", "AggregateStart", "AggregateEnd", "LeaseResource")),
     "None", "Passed", 0, "None"),
    ("sqlite-lease-expiry", tuple(SQLITE_BINDING_PREFIX
        + "Compiled_lease_expiry_consumer_rechecks_the_actual_sqlite_decision(action: " + action + ")"
        for action in ("Renew", "Release", "Guard")), "None", "Passed", 0, "None"),
    ("sqlite-cursor", (SQLITE_BINDING_PREFIX
        + "Compiled_cursor_consumer_checks_actual_sqlite_foreign_epoch_and_live_resume",), "None", "Passed", 0, "None"),
    ("sqlite-binding-controls", tuple(SQLITE_BINDING_PREFIX
        + 'Typed_adapter_controls_execute_unchanged_common_consumers(consumer: "' + consumer + '")'
        for consumer in ("receipts", "record-pages", "capacity", "ledger", "writer", "diagnostics", "publication", "cleanup")),
     "None", "Passed", 0, "None"),
    ("sqlite-continuations", tuple(SQLITE_BINDING_PREFIX
        + "Typed_continuation_damage_preserves_exact_valid_resume(corruption: " + corruption + ")"
        for corruption in ("Null", "Omitted", "WrongType", "Empty", "OddHex", "InvalidHex")), "None", "Passed", 0, "None"),
    ("sqlite-schema", (
        *(SQLITE_BINDING_PREFIX + "Unrecognized_layouts_reject_without_raw_state_repair(partial: " + partial + ")"
          for partial in ("False", "True")),
        *(SQLITE_BINDING_PREFIX
          + 'Explicit_legacy_factory_executes_unchanged_schema_consumers_on_the_same_database(consumer: "' + consumer + '")'
          for consumer in ("upgrade", "invalid-upgrade", "upgrade-contention")),
        SQLITE_BINDING_PREFIX
        + "Schema_exclusion_observation_retains_the_native_writer_after_candidate_creation"),
     "None", "Passed", 0, "None"),
    ("sqlite-ownership", tuple(SQLITE_BINDING_PREFIX + method for method in (
        "Cancelled_reopen_preserves_the_original_root_and_genuine_pending_worker_for_disposal",
        "Future_and_corrupt_schemas_reject_after_actual_same_database_reopen",
        "Reopen_transfers_one_directory_without_settling_it_under_an_old_worker")), "None", "Passed", 0, "None"),
    ("sqlite-raw-records", tuple(SQLITE_MECHANISM_PREFIX
        + "Raw_record_controls_preserve_damaged_bytes_and_restore_exact_committed_state(oversized: " + oversized + ")"
        for oversized in ("False", "True")), "None", "Passed", 0, "None"),
    ("sqlite-raw-operations", tuple(SQLITE_MECHANISM_PREFIX
        + 'Raw_operation_controls_preserve_native_storage_types_and_restore_exact_replay(damage: "' + damage + '")'
        for damage in ("short", "missing", "text", "fractional", "text-limit")), "None", "Passed", 0, "None"),
    ("sqlite-raw-layouts", tuple(SQLITE_MECHANISM_PREFIX
        + 'Raw_fingerprint_observes_rejected_layouts_without_admitting_or_repairing_them(layout: "' + layout + '")'
        for layout in ("empty", "unrecognized", "partial", "future")), "None", "Passed", 0, "None"),
    ("sqlite-native-lifetimes", tuple(SQLITE_MECHANISM_PREFIX + method for method in (
        "Raw_fingerprint_rejects_oversized_unindexed_native_rows_before_materialization",
        "Cancelled_writer_acquisition_keeps_late_native_handles_owned_until_they_close",
        "Cancelled_independent_read_does_not_release_the_underlying_work",
        "Independent_diagnostic_failure_is_surfaced_and_faults_the_actual_lifetime",
        "Independent_read_work_is_included_in_idle_and_actual_worker_termination",
        "Independent_writer_lease_is_not_ordinary_work_but_closes_before_lifetime_settlement",
        "Genuine_worker_termination_outlives_public_deadline_and_includes_native_handle_cleanup")),
     "None", "Passed", 0, "None"),
)
ASSERTION = "Hoard.Testing.Conformance.LoggerSmokeAssertion.Check"
BUDGETS = {
    "operationSeconds": 5, "barrierSeconds": 15, "childSeconds": 600,
    "transferSeconds": 2400, "recoverySeconds": 300, "terminationSeconds": 10,
    "cleanupSeconds": 30, "profileSeconds": 3600, "baselineSeconds": 28800,
    "maxChildren": 4, "maxTransferChildren": 1,
}


def write_new(path, data):
    with path.open("xb") as target:
        target.write(data)
    path.chmod(0o400)


def read_bounded(path, limit):
    no_symlinks(path)
    if not path.is_file() or not 0 <= path.stat().st_size <= limit:
        raise evidence.ConformanceError("OutputLimitExceeded")
    with path.open("rb") as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise evidence.ConformanceError("OutputLimitExceeded")
    return data


def snapshot(repository, run):
    target, hashes = evidence.snapshot_sources(repository, run)
    if "Hoard.slnx" not in hashes:
        raise evidence.ConformanceError("PrerequisiteMissing")
    return target, hashes


def build(run, project, config, cache_id, *, feed=None, lock=None, properties=(), package_id=None):
    common = ["-p:UseSharedCompilation=false", "-nodeReuse:false", "-v", "quiet", *properties]
    if lock is not None:
        common.append("-p:NuGetLockFilePath=" + str(lock))
    for args in (
        ["dotnet", "restore", str(project), "--locked-mode", "--configfile", str(config), *common],
        ["dotnet", "build", str(project), "-c", "Release", "--no-restore", *common],
    ):
        baselines._command(run, args, cwd=project.parent, cache_id=cache_id)
    if feed is not None:
        baselines._command(
            run, ["dotnet", "pack", str(project), "-c", "Release", "--no-build",
                  "--no-restore", "-o", str(feed), *common],
            cwd=project.parent, cache_id=cache_id)
        canonicalize_acceptance_archive(feed / f"{project.stem if package_id is None else package_id}.0.1.0.nupkg")


def prepare_smoke_lock(project, candidate, feed):
    _, packages, _ = rebind_local_archives(
        read_bounded(project.parent / "packages.lock.json", 2 * 1024 * 1024), feed)
    if set(packages) != {f"{name}.0.1.0.nupkg" for name in
                         ("Hoard.Abstractions", "Hoard.Testing.Conformance", "Hoard.Conformance.TestLogger")}:
        raise evidence.ConformanceError("InputChanged")
    return prepare_project_lock(project, candidate, feed, "candidate")


def prepare_package_consumer_lock(candidate, feed):
    original = candidate / TESTS / "PackageAcceptance/packages.lock.json"
    raw = read_bounded(original, 2 * 1024 * 1024)
    prepared, packages, _ = rebind_local_archives(raw, feed)
    expected = {f"{name}.0.1.0.nupkg" for name in LOCAL_PACKAGES}
    if set(packages) != expected:
        raise evidence.ConformanceError("InputChanged")
    alternate = candidate / TESTS / "obj/F07.consumer.packages.lock.json"
    no_symlinks(alternate)
    alternate.parent.mkdir(exist_ok=True, mode=0o700)
    write_new(alternate, prepared)
    return alternate, {
        "qualification": False, "mode": "preparation",
        "sourceLockSha256": hashlib.sha256(raw).hexdigest(),
        "preparedLockSha256": hashlib.sha256(prepared).hexdigest(), "packages": packages,
    }


def verify_package_consumer_lock(candidate, feed, alternate, receipt):
    raw = read_bounded(candidate / TESTS / "PackageAcceptance/packages.lock.json", 2 * 1024 * 1024)
    prepared, packages, _ = rebind_local_archives(raw, feed)
    if (set(receipt) != {"qualification", "mode", "sourceLockSha256", "preparedLockSha256", "packages"}
            or receipt["qualification"] is not False or receipt["mode"] != "preparation"
            or hashlib.sha256(raw).hexdigest() != receipt["sourceLockSha256"]
            or hashlib.sha256(prepared).hexdigest() != receipt["preparedLockSha256"]
            or packages != receipt["packages"]
            or read_bounded(alternate, 2 * 1024 * 1024) != prepared):
        raise evidence.ConformanceError("InputChanged")


def admit_sqlite_environment(observed, platform, runtime, package, locked):
    if (not isinstance(observed, dict)
            or set(observed) != {"schemaVersion", "runtime", "architecture", "nativeSqlite", "pragmas", "nativeLibrary"}
            or type(observed["schemaVersion"]) is not int or observed["schemaVersion"] != 1
            or observed["runtime"] != platform["runtime"]
            or not isinstance(observed["nativeSqlite"], str)
            or re.fullmatch(r"3\.[0-9]{1,6}\.[0-9]{1,6}", observed["nativeSqlite"]) is None
            or not isinstance(observed["pragmas"], dict)
            or observed["pragmas"] != {"journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0}
            or any(type(observed["pragmas"][key]) is not int for key in ("synchronous", "foreignKeys", "busyTimeout"))
            or not isinstance(observed["nativeLibrary"], dict)
            or set(observed["nativeLibrary"]) != {"path", "sha256"}):
        raise evidence.ConformanceError("ProofMismatch")
    architectures = {"x86_64": ("X64", "linux-x64"), "aarch64": ("Arm64", "linux-arm64")}
    expected_architecture, rid = architectures.get(platform["architecture"], (None, None))
    native_path = f"runtimes/{rid}/native/libe_sqlite3.so"
    if (expected_architecture is None or observed["architecture"] != expected_architecture
            or observed["nativeLibrary"]["path"] != native_path):
        raise evidence.ConformanceError("ProofMismatch")
    native = read_bounded(runtime / native_path, 32 * 1024 * 1024)
    native_sha = hashlib.sha256(native).hexdigest()
    archive = read_bounded(package, 64 * 1024 * 1024)
    archive_sha512 = hashlib.sha512(archive).digest()
    metadata_raw = read_bounded(package.parent / ".nupkg.metadata", 64 * 1024)
    metadata = evidence.load_json(metadata_raw)
    # NuGet records normalized signed-package content and downloaded archive
    # hashes separately. Both receipts come from the fresh locked restore.
    cached_sha512 = read_bounded(package.with_suffix(".nupkg.sha512"), 1024).decode("ascii").strip()
    if (observed["nativeLibrary"]["sha256"] != native_sha
            or not isinstance(metadata, dict)
            or type(metadata.get("version")) is not int or metadata["version"] != 2
            or metadata.get("source") != "https://api.nuget.org/v3/index.json"
            or metadata.get("contentHash") != locked["contentHash"]
            or base64.b64encode(archive_sha512).decode("ascii") != cached_sha512):
        raise evidence.ConformanceError("InputChanged")
    try:
        content_sha512 = base64.b64decode(locked["contentHash"], validate=True)
    except (ValueError, TypeError):
        raise evidence.ConformanceError("InputChanged") from None
    if len(content_sha512) != 64:
        raise evidence.ConformanceError("InputChanged")
    with zipfile.ZipFile(io.BytesIO(archive)) as packed:
        entries = packed.infolist()
        matching = [entry for entry in entries if entry.filename == native_path]
        if (len(entries) > 4096 or len(matching) != 1 or matching[0].file_size != len(native)
                or matching[0].flag_bits & 1 or packed.read(matching[0]) != native):
            raise evidence.ConformanceError("InputChanged")
    return {"qualification": False, "packageId": "SQLitePCLRaw.lib.e_sqlite3",
            "packageVersion": evidence.stable_id(locked["resolved"]),
            "packageSha256": hashlib.sha256(archive).hexdigest(),
            "archiveSha512": archive_sha512.hex(), "nugetSha512": content_sha512.hex(),
            "cacheMetadataSha256": hashlib.sha256(metadata_raw).hexdigest(), "sourceMapping": "nuget.org",
            "nativePath": native_path, "nativeSha256": native_sha}


def sqlite_environment(run, candidate, platform, *, phase):
    runtime = candidate / TESTS / PACKAGE_TEST_OUTPUT / "Release/net10.0"
    output = run.root / f"proofs/sqlite-environment-{phase}.json"
    parent = run.root / f"stores/sqlite-environment-{phase}"
    no_symlinks(parent)
    parent.mkdir(mode=0o700)
    provider_sha = evidence.package_identity(
        run.root / "feed/candidate", "Hoard.Fixtures.Metadata.Sqlite", "0.1.0")["sha256"]
    result = run.command(
        ["dotnet", str(runtime / "Hoard.Conformance.Tests.dll"), "sqlite-environment",
         str(output), str(parent), str(candidate), provider_sha],
        cwd=runtime, kind="build", timeout=60, cache_id=f"sqlite-environment-{phase}")
    if result.exit_code or result.events:
        code = result.events[0]["code"] if len(result.events) == 1 else "PrerequisiteMissing"
        if code not in ("PrerequisiteMissing", "ProofMismatch", "OutputLimitExceeded", "CleanupIncomplete", "OwnershipInvalid"):
            code = "PrerequisiteMissing"
        raise evidence.ConformanceError(code)
    observed = evidence.load_json(read_bounded(output, 64 * 1024))
    lock = evidence.load_json(read_bounded(
        candidate / TESTS / "PackageAcceptance/packages.lock.json", 2 * 1024 * 1024))
    locked = lock["dependencies"]["net10.0"]["SQLitePCLRaw.lib.e_sqlite3"]
    version = evidence.stable_id(locked["resolved"])
    package = run.root / "cache/consumer-locked-replay/sqlitepclraw.lib.e_sqlite3" / version / (
        f"sqlitepclraw.lib.e_sqlite3.{version}.nupkg")
    provenance = admit_sqlite_environment(observed, platform, runtime, package, locked)
    provenance_data = evidence.canonical_bytes(provenance)
    if phase == "completion" and read_bounded(
            run.root / "proofs/sqlite-native-provenance-admission.json", 64 * 1024) != provenance_data:
        raise evidence.ConformanceError("InputChanged")
    write_new(run.root / f"proofs/sqlite-native-provenance-{phase}.json", provenance_data)
    output.chmod(0o400)
    return {**platform, "nativeSqlite": observed["nativeSqlite"], "pragmas": observed["pragmas"]}


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


def require_sqlite_environment(inputs, assembly, root):
    observed = inputs.get("environment", {})
    rid = {"x86_64": "linux-x64", "aarch64": "linux-arm64"}.get(observed.get("architecture"))
    native = (assembly.parent / f"runtimes/{rid}/native/libe_sqlite3.so").relative_to(root).as_posix()
    if (observed.get("os") != "linux" or rid is None
            or not isinstance(observed.get("nativeSqlite"), str)
            or re.fullmatch(r"3\.[0-9]{1,6}\.[0-9]{1,6}", observed["nativeSqlite"]) is None
            or observed.get("pragmas") != {"journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0}
            or native not in inputs.get("runtimeAssemblies", {})):
        raise evidence.ConformanceError("EvidenceIncomplete")


def sqlite_noncooperation(run, inputs, candidate):
    runtime = candidate / TESTS / PACKAGE_TEST_OUTPUT / "Release/net10.0"
    assembly = runtime / "Hoard.Conformance.Tests.dll"
    require_sqlite_environment(inputs, assembly, run.root)
    parent = run.root / "stores/sqlite-native-noncooperation"
    no_symlinks(parent)
    parent.mkdir(mode=0o700)
    output = run.root / "proofs/sqlite-native-noncooperation.json"
    inputs_sha256 = evidence.digest(inputs)
    provider_sha = evidence.package_identity(
        run.root / "feed/candidate", "Hoard.Fixtures.Metadata.Sqlite", "0.1.0")["sha256"]
    sequence = run.command_sequence + 1
    try:
        run.command(
            ["dotnet", str(assembly), "sqlite-native-noncooperation", str(output),
             str(parent), str(candidate), provider_sha, inputs_sha256],
            cwd=runtime, scope="recovery", timeout=45, cache_id="sqlite-native-noncooperation")
    except evidence.ConformanceError as error:
        if str(error) != "DeadlineExceeded":
            raise
    else:
        raise evidence.ConformanceError("EvidenceIncomplete")
    if run.live_children():
        raise evidence.ConformanceError("CleanupIncomplete")
    command_raw = read_bounded(run.root / f"proofs/recovery-command-{sequence:04}.json", 64 * 1024)
    observed_raw = read_bounded(output, 64 * 1024)
    command = evidence.load_json(command_raw)
    observed = evidence.load_json(observed_raw)
    admit_sqlite_noncooperation(observed, command, inputs_sha256)
    if command["sequence"] != sequence:
        raise evidence.ConformanceError("ProofMismatch")
    output.chmod(0o400)
    return {
        "qualification": False, "mode": "native-noncooperation", "code": "None",
        "inputsSha256": inputs_sha256, "producerSha256": hashlib.sha256(observed_raw).hexdigest(),
        "controllerSha256": hashlib.sha256(command_raw).hexdigest(),
        "childStartSha256": command["childStartSha256"],
    }


def environment(run, *, phase="admission", candidate=None):
    # The probe is itself an owned child. Captured SDK text is bounded transient
    # input, validated before serialization, never sent to the console.
    if phase not in ("admission", "completion"):
        raise evidence.ConformanceError()
    path = run.root / f"proofs/environment-{phase}.json"
    image_os = os.environ.get("ImageOS", "")
    image_version = os.environ.get("ImageVersion", "")
    image = (f"{image_os}.{image_version}"
             if image_os in ("ubuntu24", "ubuntu22")
             and re.fullmatch(r"[0-9]{8}\.[0-9]+\.[0-9]+", image_version) else "none")
    result = run.command(
        [sys.executable, str(Path(__file__).resolve()), "--probe", str(path)],
        cwd=Path(__file__).resolve().parents[1], kind="build", timeout=30, cache_id=f"environment-{phase}",
        env={"HOARD_RUNNER_IMAGE": image})
    if result.exit_code or result.events:
        raise evidence.ConformanceError("PrerequisiteMissing")
    observed = evidence.admit_entity("Environment", evidence.load_json(read_bounded(path, 64 * 1024)))
    if candidate is not None:
        observed = sqlite_environment(run, candidate, observed, phase=phase)
    return evidence.admit_entity("Environment", observed)


def probe(path):
    if not native_execution_supported():
        raise evidence.ConformanceError("PrerequisiteMissing")
    code, sdk = capture_control(["dotnet", "--version"], limit=1024, timeout=5)
    code2, runtimes = capture_control(["dotnet", "--list-runtimes"], limit=16384, timeout=5)
    code3, filesystem = capture_control(
        ["stat", "-f", "--format=%T", str(path.parent)], limit=1024, timeout=5)
    sdk = sdk.decode("ascii").strip()
    filesystem = filesystem.decode("ascii").strip().replace("/", "-")
    versions = re.findall(rb"^Microsoft\.NETCore\.App (10\.\d+\.\d+) \[[^\r\n]+\]$",
                          runtimes, re.MULTILINE)
    if (code or code2 or code3 or not re.fullmatch(r"10\.\d+\.\d+", sdk) or not versions
            or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", filesystem)):
        raise evidence.ConformanceError("PrerequisiteMissing")
    image = os.environ.get("HOARD_RUNNER_IMAGE", "none")
    if image != "none" and re.fullmatch(r"ubuntu(?:22|24)\.[0-9]{8}\.[0-9]+\.[0-9]+", image) is None:
        raise evidence.ConformanceError("PrerequisiteMissing")
    value = {
        "os": "linux", "osVersion": os.uname().release, "architecture": os.uname().machine,
        "sdk": sdk, "runtime": versions[-1].decode("ascii"), "nativeSqlite": "not-used",
        "filesystem": filesystem, "runnerImage": image,
        "freeBytes": shutil.disk_usage(path.parent).free,
        "pragmas": {"journalMode": "none", "synchronous": 0, "foreignKeys": 0, "busyTimeout": 0},
    }
    evidence.admit_entity("Environment", value)
    write_new(path, evidence.canonical_bytes(value))


def make_inputs(run, repository, candidate, sources, observed_environment, identity, seal_sha,
                *, group_id=None, ci_revision=None, binding_sources=()):
    run._check_ledger()
    inventory = evidence.proof_manifest(candidate)
    prefix = candidate.relative_to(run.root).as_posix()
    locks = [f"{prefix}/{name}" for name in inventory if name.endswith("packages.lock.json")]
    runtime_folders = {f"{TESTS}/bin/Release/net10.0", f"{LOGGER}/Smoke/bin/Release/net10.0",
                       f"{TESTS}/{PACKAGE_TEST_OUTPUT}/Release/net10.0"}
    runtime = [f"{prefix}/{name}" for name in inventory if (
        name.endswith((".dll", ".deps.json", ".runtimeconfig.json", ".runtimeconfig.dev.json"))
        and Path(name).parent.as_posix() in runtime_folders) or (
        name.endswith((".so", ".dylib", ".dll"))
        and any(name.startswith(folder + "/runtimes/") for folder in runtime_folders))]
    if not runtime or not locks:
        raise evidence.ConformanceError("EvidenceIncomplete")
    inputs = evidence.capture_profile_inputs(
        run, repository, candidate, profile_id="harness", mode="diagnostic",
        invocation_group_id=str(uuid.uuid4()) if group_id is None else group_id,
        package_versions=[{"packageId": name, "version": "0.1.0"} for name in LOCAL_PACKAGES],
        feed="feed/candidate", configuration="stores/candidate.NuGet.Config",
        lock_paths=locks, runtime_paths=runtime, binding_sources=list(binding_sources),
        observed_environment=observed_environment, budgets=BUDGETS, invocation=["sdk-logger-diagnostic"],
        baseline_sha256=seal_sha, ci_revision=ci_revision)
    if (inputs["sourceManifest"] != sources
            or any(inputs[key] != value for key, value in identity.items())):
        raise evidence.ConformanceError("InputChanged")
    return inputs


def test_attempt(run, inputs, candidate, scenario):
    name, identities, expected_code, expected_status, expected_exit, failure_kind = scenario
    binding_tests = all(identity.startswith(BINDING_TEST_PREFIXES) for identity in identities)
    sqlite_tests = any(identity.startswith((SQLITE_BINDING_PREFIX, SQLITE_MECHANISM_PREFIX)) for identity in identities)
    source_tests = all(identity.startswith("Hoard.Conformance.Tests.") for identity in identities) or binding_tests
    smoke_tests = all(identity.startswith(SMOKE) for identity in identities)
    package_tests = binding_tests or any(identity.startswith(PACKAGE_TEST_PREFIX) for identity in identities)
    if (source_tests == smoke_tests
            or package_tests and not binding_tests
            and not all(identity.startswith(PACKAGE_TEST_PREFIX) for identity in identities)):
        raise evidence.ConformanceError("WitnessMissing")
    output = PACKAGE_TEST_OUTPUT if package_tests else "bin"
    assembly = candidate / (TESTS if source_tests else LOGGER + "/Smoke") / output / "Release/net10.0" / (
        "Hoard.Conformance.Tests.dll" if source_tests else "Smoke.dll")
    if sqlite_tests:
        require_sqlite_environment(inputs, assembly, run.root)
    assembly_path = assembly.relative_to(run.root).as_posix()
    package_id = "Hoard.Testing.Conformance" if source_tests or name == "origin-output" else "Hoard.Conformance.TestLogger"
    package = next(package for package in inputs["packages"] if package["packageId"] == package_id)
    attempt_id = str(uuid.uuid4())
    expected = {identity: ("origin-probe" if name == "origin-output" else "none", "none") for identity in identities}
    manifest = {
        "schemaVersion": 1, "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "attemptId": attempt_id, "attemptSequence": 1, "purpose": "execution",
        "inputSha256": evidence.digest(inputs),
        "runInputsPath": "proofs/run-inputs.json",
        "assemblies": [{"id": "test-assembly", "path": assembly_path,
                        "sha256": inputs["runtimeAssemblies"][assembly_path]}],
        "packages": [{"id": package_id, "path": f"feed/candidate/{package_id}.0.1.0.nupkg",
                      "sha256": package["sha256"]}],
        "expected": [{
            "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
            "assemblyId": "test-assembly", "packageId": package_id,
            "bindingId": binding, "matrixId": matrix,
            "assertionSymbol": ASSERTION if name == "assertion" else None,
            "caseId": "runtime",
        } for identity, (binding, matrix) in expected.items()],
    }
    discovery_manifest = {**manifest, "purpose": "discovery", "attemptId": str(uuid.uuid4())}
    discovery_result, discovery_output, discovery_transport = runtime_command(run, assembly, discovery_manifest)
    files = set()
    for path in discovery_output.iterdir():
        files.add(path.name)
        if len(files) > 2:
            raise evidence.ConformanceError("EvidenceIncomplete")
    if files != {"completion.json", "discovered.jsonl"}:
        raise evidence.ConformanceError("EvidenceIncomplete")
    discovery = evidence.ingest_runtime_discovery(
        inputs=inputs, expected_tests=expected,
        discoveries_data=read_bounded(discovery_output / "discovered.jsonl", 1024 * 1024),
        completion_data=read_bounded(discovery_output / "completion.json", 64 * 1024),
        **discovery_transport)
    if (discovery_result.exit_code or discovery["diagnosticCode"] != "None"
            or tuple(dict(event) for event in discovery_result.events) != (
                {"event": "control", "code": "None", "value": len(identities)},)
            or {record["testIdentity"] for record in discovery["discoveries"]} != set(identities)):
        raise evidence.ConformanceError("EvidenceIncomplete")
    result, output, transport = runtime_command(run, assembly, manifest)
    files = set()
    for path in output.iterdir():
        files.add(path.name)
        if len(files) > len(identities) + 2:
            raise evidence.ConformanceError("OutputLimitExceeded")
    if not {"completion.json", "witnesses.jsonl"} <= files or len(files) > len(identities) + 2:
        raise evidence.ConformanceError("EvidenceIncomplete")
    proof_data = {filename: read_bounded(output / filename, 64 * 1024)
                  for filename in files if filename.startswith("proof-") and filename.endswith(".json")}
    if files != {"completion.json", "witnesses.jsonl", *proof_data}:
        raise evidence.ConformanceError("EvidenceIncomplete")
    origin_inputs = None
    if name == "origin-output":
        origin_inputs = {"origin-probe": {role: (assembly_path, None) for role in (
            "factory", "session", "store", "schema", "authority", "faults")}}
    ingested = evidence.ingest_runtime_attempt(
        inputs=inputs, expected_tests=expected,
        witnesses_data=read_bounded(output / "witnesses.jsonl", 1024 * 1024), proofs=proof_data,
        completion_data=read_bounded(output / "completion.json", 64 * 1024),
        **({"origin_inputs": origin_inputs} if origin_inputs is not None else {}), **transport)
    validate_observation(ingested, result, identities, expected_code, expected_status, expected_exit,
                         proof_data, failure_kind)
    if name == "origin-output" and (
            len(ingested["sessionOrigins"]) != 1
            or any(len(origins) != 1 for origins in ingested["sessionOrigins"].values())):
        raise evidence.ConformanceError("WitnessMissing")
    return {"code": expected_code, "tests": len(identities),
            "discoverySha256": evidence.file_sha256(discovery_output / "completion.json"),
            "completionSha256": evidence.file_sha256(output / "completion.json")}


def runtime_command(run, assembly, manifest):
    attempt_id = manifest["attemptId"]
    identities = tuple(entry["testIdentity"] for entry in manifest["expected"])
    if manifest["purpose"] not in ("discovery", "execution"):
        raise evidence.ConformanceError()
    discovery = manifest["purpose"] == "discovery"
    origin_environment = ""
    if any(entry["fullyQualifiedName"] == SMOKE + "OriginOutput" for entry in manifest["expected"]):
        package = next((item for item in manifest["packages"] if item["id"] == "Hoard.Testing.Conformance"), None)
        if package is None:
            raise evidence.ConformanceError("PrerequisiteMissing")
        origin_environment = (
            "<EnvironmentVariables>"
            f'<HOARD_ORIGIN_RUN_ID>{escape(manifest["runId"])}</HOARD_ORIGIN_RUN_ID>'
            f'<HOARD_ORIGIN_PACKAGE_SHA256>{escape(package["sha256"])}</HOARD_ORIGIN_PACKAGE_SHA256>'
            "</EnvironmentVariables>")
    manifest_data = evidence.canonical_bytes(manifest)
    owner_data = read_bounded(run.root / "runtime-owner.json", 64 * 1024)
    manifest_sha = hashlib.sha256(manifest_data).hexdigest()
    owner_sha = hashlib.sha256(owner_data).hexdigest()
    write_new(run.root / f"runtime-input-{attempt_id}.json", manifest_data)
    settings = run.root / "stores" / f"settings-{attempt_id}.runsettings"
    write_new(settings, (
        '<RunSettings><RunConfiguration>'
        f'<TestAdaptersPaths>{escape(str(assembly.parent))}</TestAdaptersPaths>'
        '<MaxCpuCount>1</MaxCpuCount><TestSessionTimeout>120000</TestSessionTimeout>'
        + origin_environment +
        '</RunConfiguration><LoggerRunSettings><Loggers>'
        '<Logger friendlyName="console" enabled="False"/>'
        '<Logger friendlyName="HoardSafe" enabled="True"><Configuration>'
        f'<Root>{escape(str(run.root))}</Root><AttemptId>{attempt_id}</AttemptId>'
        f'<ManifestSha256>{manifest_sha}</ManifestSha256><OwnerSha256>{owner_sha}</OwnerSha256>'
        '</Configuration></Logger></Loggers></LoggerRunSettings></RunSettings>').encode())
    filter_text = "|".join("FullyQualifiedName=" + name
                           for name in dict.fromkeys(identity.split("(")[0] for identity in identities))
    started = time.monotonic() * 1000
    result = run.command(
        ["dotnet", "vstest", str(assembly), *(["--ListTests"] if discovery else []),
         f"--Settings:{settings}", f"--TestCaseFilter:{filter_text}"],
        cwd=assembly.parent, timeout=180, kind="discovery" if discovery else "tests", cache_id="runtime",
        **({"discovery_tests": frozenset(identities)} if discovery else {}))
    ended = time.monotonic() * 1000
    output = run.root / f'{"discovery" if discovery else "runtime"}-{attempt_id}'
    no_symlinks(output)
    return result, output, {
        "manifest_data": manifest_data, "owner_data": owner_data,
        "manifest_sha256": manifest_sha, "owner_sha256": owner_sha,
        "started_ms": started, "ended_ms": ended,
    }


def validate_observation(ingested, result, identities, code, status, exit_code, proofs, failure_kind):
    if (result.exit_code != exit_code or ingested["diagnosticCode"] != code
            or len(result.events) != 1 or dict(result.events[0]) !=
            {"event": "control", "code": code, "value": len(identities)}
            or len(ingested["witnesses"]) != len(identities)
            or {witness["testIdentity"] for witness in ingested["witnesses"]} != set(identities)
            or any(witness["status"] != status for witness in ingested["witnesses"])
            or len(proofs) != len(identities)
            or any(evidence.load_json(raw)["failureKind"] != failure_kind for raw in proofs.values())):
        raise evidence.ConformanceError("EvidenceIncomplete")


def execute(repository, destination):
    if not native_execution_supported() or not callable(getattr(evidence, "ingest_runtime_attempt", None)):
        raise evidence.ConformanceError("PrerequisiteMissing")
    run = OwnedRun.allocate(destination, repository, profile="baseline")
    run.deadline = min(run.deadline, time.monotonic() + 100 * 60)
    try:
        home = run.root / "cache"
        home.mkdir(exist_ok=True, mode=0o700)
        (home / ".local").mkdir(mode=0o700)
        (home / ".local/share").mkdir(mode=0o700)
        print(json.dumps({"qualification": False, "phase": "baseline-preparation"}), flush=True)
        seal = baselines.prepare(repository, run, prepare_local_archives=True)
        seal_sha = evidence.file_sha256(seal)
        baselines.verify_prepared_baselines(run.root, seal_sha)
        ci_revision = os.environ.get("GITHUB_SHA") if os.environ.get("GITHUB_ACTIONS") == "true" else None
        if os.environ.get("GITHUB_ACTIONS") == "true" and ci_revision is None:
            raise evidence.ConformanceError("InputChanged")
        identity = evidence.source_identity(repository, ci_revision=ci_revision)
        candidate, sources = snapshot(repository, run)
        config, feed = baselines._config(run, "candidate")
        print(json.dumps({"qualification": False, "phase": "candidate-build"}), flush=True)
        for folder, project_name in (
            ("src/Hoard.Abstractions", "Hoard.Abstractions"), (SDK, "Hoard.Testing.Conformance"),
            (LOGGER, "Hoard.Conformance.TestLogger"),
        ):
            build(run, candidate / folder / f"{project_name}.csproj", config, "candidate-build", feed=feed)
        build(run, candidate / TESTS / "Hoard.Conformance.Tests.csproj", config, "candidate-build")
        memory_lock, memory_record = prepare_project_lock(candidate / MEMORY, candidate, feed, "candidate")
        build(run, candidate / MEMORY, config, "memory-package", lock=memory_lock, feed=feed,
              package_id="Hoard.Fixtures.Metadata.Memory")
        if memory_record is not None:
            verify_project_lock(memory_record, candidate, feed)
            write_new(run.root / "proofs/memory-lock-derivation.json", evidence.canonical_bytes(memory_record))
        binding_lock, binding_record = prepare_project_lock(candidate / MEMORY_BINDING, candidate, feed, "candidate")
        build(run, candidate / MEMORY_BINDING, config, "memory-binding-package", lock=binding_lock, feed=feed,
              package_id="Hoard.Fixtures.Conformance.Bindings.Memory")
        if binding_record is not None:
            verify_project_lock(binding_record, candidate, feed)
            write_new(run.root / "proofs/memory-binding-lock-derivation.json", evidence.canonical_bytes(binding_record))
        sqlite_lock, sqlite_record = prepare_project_lock(candidate / SQLITE, candidate, feed, "candidate")
        build(run, candidate / SQLITE, config, "sqlite-package", lock=sqlite_lock, feed=feed,
              package_id="Hoard.Fixtures.Metadata.Sqlite")
        if sqlite_record is not None:
            verify_project_lock(sqlite_record, candidate, feed)
            write_new(run.root / "proofs/sqlite-lock-derivation.json", evidence.canonical_bytes(sqlite_record))
        sqlite_binding_lock, sqlite_binding_record = prepare_project_lock(candidate / SQLITE_BINDING, candidate, feed, "candidate")
        build(run, candidate / SQLITE_BINDING, config, "sqlite-binding-package", lock=sqlite_binding_lock, feed=feed,
              package_id="Hoard.Fixtures.Conformance.Bindings.Sqlite")
        if sqlite_binding_record is not None:
            verify_project_lock(sqlite_binding_record, candidate, feed)
            write_new(run.root / "proofs/sqlite-binding-lock-derivation.json", evidence.canonical_bytes(sqlite_binding_record))
        consumer_lock, consumer_receipt = prepare_package_consumer_lock(candidate, feed)
        verify_package_consumer_lock(candidate, feed, consumer_lock, consumer_receipt)
        write_new(run.root / "proofs/consumer-lock-derivation.json", evidence.canonical_bytes(consumer_receipt))
        build(run, candidate / TESTS / "Hoard.Conformance.Tests.csproj", config,
              "consumer-locked-replay", lock=consumer_lock, properties=(
                  "-p:ConformancePackageAcceptance=true", "-p:BaseOutputPath=" + PACKAGE_TEST_OUTPUT + "/"))
        smoke_lock = candidate / LOGGER / "Smoke/packages.lock.json"
        source_lock_sha = evidence.file_sha256(smoke_lock)
        smoke_project = candidate / LOGGER / "Smoke/Smoke.csproj"
        alternate, lock_record = prepare_smoke_lock(smoke_project, candidate, feed)
        replayed_lock = alternate if alternate is not None else smoke_lock
        if lock_record is not None:
            verify_project_lock(lock_record, candidate, feed)
            write_new(run.root / "proofs/smoke-lock-derivation.json", evidence.canonical_bytes(lock_record))
        lock_preparation = {
            "qualification": False, "mode": "preparation",
            "sourceLockSha256": source_lock_sha,
            "preparedLockSha256": evidence.file_sha256(replayed_lock),
        }
        write_new(run.root / "proofs/smoke-lock-preparation.json",
                  evidence.canonical_bytes(lock_preparation))
        print(json.dumps({"qualification": False, "phase": "locked-replay"}), flush=True)
        build(run, smoke_project, config, "smoke-locked-replay", lock=alternate)
        if evidence.source_identity(repository, ci_revision=ci_revision) != identity:
            raise evidence.ConformanceError("InputChanged")
        # This is an independently planned diagnostic declaration, not observed provider behavior.
        declaration = {
            "schemaVersion": 1, "bindingId": "origin-probe", "category": "metadata",
            "packageId": "Hoard.Testing.Conformance", "packageVersion": "0.1.0",
            "packageSha256": evidence.package_identity(feed, "Hoard.Testing.Conformance", "0.1.0")["sha256"],
            "capabilities": ["common-logical"], "faults": sorted(evidence._BINDING_REQUIRED_FAULTS["metadata"]),
        }
        write_new(run.root / "stores/origin-probe.json",
                  json.dumps(declaration, separators=(",", ":"), ensure_ascii=True).encode("ascii"))
        binding_sources = [{"path": "stores/origin-probe.json", "adapterId": "sdk-origin-probe"}]
        inputs = make_inputs(run, repository, candidate, sources, environment(run, candidate=candidate), identity, seal_sha,
                             ci_revision=ci_revision, binding_sources=binding_sources)
        for name in sources:
            (candidate / name).chmod(0o400)
        for name in inputs["runtimeAssemblies"]:
            (run.root / name).chmod(0o400)
        for package in feed.glob("*.nupkg"):
            package.chmod(0o400)
        write_new(run.root / "proofs/run-inputs.json", evidence.canonical_bytes(inputs))
        write_new(run.root / "runtime-owner.json", evidence.canonical_bytes({
            "schemaVersion": 1, "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
            "rootId": run.root_id, "rootPathSha256": hashlib.sha256(str(run.root).encode()).hexdigest(),
        }))
        observations = []
        for scenario in SCENARIOS:
            print(json.dumps({"qualification": False, "phase": "runtime-tests",
                              "completedScenarios": len(observations)}), flush=True)
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "native-noncooperation"}), flush=True)
        native_noncooperation = sqlite_noncooperation(run, inputs, candidate)
        post_environment = environment(run, phase="completion", candidate=candidate)
        post_sources = evidence.source_manifest(repository)
        post_identity = evidence.source_identity(repository, ci_revision=ci_revision)
        if post_sources != sources or post_identity != identity:
            raise evidence.ConformanceError("InputChanged")
        evidence.verify_snapshot(candidate, sources)
        if lock_record is not None:
            verify_project_lock(lock_record, candidate, feed)
        if memory_record is not None:
            verify_project_lock(memory_record, candidate, feed)
        if binding_record is not None:
            verify_project_lock(binding_record, candidate, feed)
        verify_package_consumer_lock(candidate, feed, consumer_lock, consumer_receipt)
        post_inputs = make_inputs(
            run, repository, candidate, post_sources, post_environment, post_identity, seal_sha,
            group_id=inputs["invocationGroupId"], ci_revision=ci_revision, binding_sources=binding_sources)
        evidence.verify_input_recomputation(inputs, post_inputs)
        native_provenance = evidence.load_json(read_bounded(
            run.root / "proofs/sqlite-native-provenance-completion.json", 64 * 1024))
        summary = {"qualification": False, "code": "None", "baselines": 6,
                   "baselineSha256": seal_sha, "inputsSha256": evidence.digest(inputs),
                   "lockPreparation": lock_preparation,
                   "nativeNonCooperation": native_noncooperation,
                   "sqliteEnvironment": {
                       "nativeVersion": inputs["environment"]["nativeSqlite"],
                       "pragmas": dict(inputs["environment"]["pragmas"]),
                       "nativeLibrarySha256": native_provenance["nativeSha256"],
                       "packageArchiveSha256": native_provenance["packageSha256"],
                       "archiveSha512": native_provenance["archiveSha512"],
                       "nugetContentSha512": native_provenance["nugetSha512"],
                   },
                   "observations": observations}
        write_new(run.root / "proofs/sdk-diagnostic-summary.json", evidence.canonical_bytes(summary))
        run.transition("Settling")
        if run.live_children():
            run.transition("Retained")
            raise evidence.ConformanceError("CleanupIncomplete")
        # Settled stores and caches remain private, separate from safe diagnostics.
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (evidence.ConformanceError, OSError, ValueError, zipfile.BadZipFile):
        if run.state in ("Active", "Allocated"):
            run.transition("Settling")
        if run.state == "Settling" and run.live_children():
            run.transition("Retained")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--probe", type=Path, help=argparse.SUPPRESS)
    options = parser.parse_args()
    try:
        if options.probe is not None:
            probe(options.probe)
            return 0
        if options.evidence is None:
            raise evidence.ConformanceError("PrerequisiteMissing")
        return execute(options.root.resolve(), options.evidence)
    except (evidence.ConformanceError, OSError, ValueError, zipfile.BadZipFile) as error:
        code = str(error) if isinstance(error, evidence.ConformanceError) else "PrerequisiteMissing"
        status = evidence.failure_status(code)
        print(json.dumps({"qualification": False, "status": status, "code": code}))
        return 2 if status == "Incomplete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
