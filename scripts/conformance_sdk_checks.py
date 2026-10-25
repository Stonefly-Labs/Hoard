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
import artifact_evidence as artifacts
import conformance_evidence as evidence
from conformance_case_catalog import (
    CATEGORY_BINDING_SLOTS, ORIGINAL_METADATA_WITNESSES, catalog_admission_witnesses, category_cases, category_runtime_cases,
    original_witness_policy,
)
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
METADATA_RECOVERY = "tests/fixtures/metadata/CrashRunner"
ARTIFACT_RECOVERY = "tests/fixtures/artifacts/CrashRunner"
ARTIFACT_TRANSFER = "tests/fixtures/artifacts/TransferRunner"
METADATA_TESTS = f"{CONTRACTS}/Hoard.Metadata.Tests"
METADATA_TEST_OUTPUT = "bin/wrapper-diagnostic"
ARTIFACT_TESTS = f"{CONTRACTS}/Hoard.Artifacts.Tests"
ARTIFACT_TEST_OUTPUT = "bin/wrapper-diagnostic"
ARTIFACT_CONSUMER = "tests/fixtures/conformance/Consumer"
ARTIFACT_CONSUMER_PREFIX = "Hoard.Fixtures.Conformance.Consumer.LocalArtifactSessionTests."
OBJECT_ARTIFACT_CONSUMER_PREFIX = "Hoard.Fixtures.Conformance.Consumer.ObjectArtifactSessionTests."
CONFIGURED_ARTIFACT_CONSUMER_PREFIX = "Hoard.Fixtures.Conformance.Consumer.ArtifactConfiguredSessionTests."
PAYLOAD_ARTIFACT_CONSUMER_PREFIX = "Hoard.Fixtures.Conformance.Consumer.ArtifactPayloadSessionTests."
FULL_ARTIFACT_CONSUMER_PREFIX = "Hoard.Fixtures.Conformance.Consumer.ArtifactConformanceSessionTests."
FULL_METADATA_CONSUMER_PREFIX = "Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
AUTHORITY_INTEGRATION_PREFIX = "Hoard.Conformance.Tests.AuthorityIntegrationTests."
CATEGORY_MUTATION_PREFIX = "Hoard.Conformance.Tests.CategoryMutationTests."
ARTIFACT_CONSUMER_PREFIXES = (
    ARTIFACT_CONSUMER_PREFIX, OBJECT_ARTIFACT_CONSUMER_PREFIX, CONFIGURED_ARTIFACT_CONSUMER_PREFIX,
    PAYLOAD_ARTIFACT_CONSUMER_PREFIX, FULL_ARTIFACT_CONSUMER_PREFIX, AUTHORITY_INTEGRATION_PREFIX,
    CATEGORY_MUTATION_PREFIX)
ARTIFACT_CONSUMER_PACKAGES = (
    "Hoard.Abstractions", "Hoard.Testing.Conformance",
    "Hoard.Fixtures.Metadata.Memory", "Hoard.Fixtures.Metadata.Sqlite",
    "Hoard.Fixtures.Artifacts.Local", "Hoard.Fixtures.Artifacts.ObjectSemantics",
    "Hoard.Core", "Hoard.Hosting", "Hoard.Fixtures.Metadata.HostAdapters", "Hoard.Fixtures.Artifacts.HostAdapters",
    *(f"Hoard.Fixtures.Conformance.Bindings.{name}" for name in ("Memory", "Sqlite", "Local", "ObjectSemantics")),
)
LOCAL_PACKAGES = (
    "Hoard.Abstractions", "Hoard.Testing.Conformance", "Hoard.Conformance.TestLogger",
    "Hoard.Fixtures.Metadata.Memory", "Hoard.Fixtures.Conformance.Bindings.Memory",
    "Hoard.Fixtures.Metadata.Sqlite", "Hoard.Fixtures.Conformance.Bindings.Sqlite",
)
METADATA_PACKAGES = (
    "Hoard.Abstractions", "Hoard.Core", "Hoard.Hosting", "Hoard.Fixtures.Metadata.HostAdapters",
    "Hoard.Fixtures.Metadata.Memory", "Hoard.Fixtures.Metadata.Sqlite", "Hoard.Testing.Conformance",
)
METADATA_RECOVERY_PACKAGES = tuple(name for name in METADATA_PACKAGES if name != "Hoard.Testing.Conformance")
ARTIFACT_PACKAGES = (*METADATA_PACKAGES, "Hoard.Fixtures.Artifacts.Local",
                     "Hoard.Fixtures.Artifacts.ObjectSemantics", "Hoard.Fixtures.Artifacts.HostAdapters")
ARTIFACT_RECOVERY_PACKAGES = tuple(name for name in ARTIFACT_PACKAGES if name != "Hoard.Testing.Conformance")
INPUT_PACKAGES = tuple(dict.fromkeys((
    *LOCAL_PACKAGES, *METADATA_PACKAGES, *ARTIFACT_PACKAGES, *ARTIFACT_CONSUMER_PACKAGES)))
BINDING_TEST_PREFIX = "Hoard.Fixtures.Conformance.Consumer.MemoryBindingTests."
BINDING_OWNERSHIP_PREFIX = "Hoard.Fixtures.Conformance.Consumer.MemoryBindingOwnershipTests."
SQLITE_BINDING_PREFIX = "Hoard.Fixtures.Conformance.Consumer.SqliteBindingTests."
SQLITE_MECHANISM_PREFIX = "Hoard.Fixtures.Conformance.Consumer.SqliteMechanismTests."
BINDING_TEST_PREFIXES = (
    BINDING_TEST_PREFIX, BINDING_OWNERSHIP_PREFIX, SQLITE_BINDING_PREFIX, SQLITE_MECHANISM_PREFIX,
    FULL_METADATA_CONSUMER_PREFIX, *ARTIFACT_CONSUMER_PREFIXES)
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
        "Cancelled_physical_stream_settles_without_internal_failure",
        "Raw_fingerprint_rejects_oversized_unindexed_native_rows_before_materialization",
        "Cancelled_writer_acquisition_keeps_late_native_handles_owned_until_they_close",
        "Cancelled_independent_read_does_not_release_the_underlying_work",
        "Independent_diagnostic_failure_is_surfaced_and_faults_the_actual_lifetime",
        "Independent_read_work_is_included_in_idle_and_actual_worker_termination",
        "Independent_writer_lease_is_not_ordinary_work_but_closes_before_lifetime_settlement",
        "Genuine_worker_termination_outlives_public_deadline_and_includes_native_handle_cleanup"))
     + tuple(SQLITE_BINDING_PREFIX + method for method in (
        "Raw_corruption_observations_read_committed_rows_while_the_primary_candidate_is_held",
        "Physical_schema_fingerprints_detect_writes_and_preserve_rejected_reopen_state")),
     "None", "Passed", 0, "None"),
)
ASSERTION = "Hoard.Testing.Conformance.LoggerSmokeAssertion.Check"


def original_metadata_scenarios():
    frozen = category_cases()
    return tuple(
        ("original-metadata-" + provider, tuple(sorted({
            witness for case in frozen if case.profile_id == "metadata" and case.binding_id == provider
            for witness in case.witnesses if witness.startswith("Hoard.Metadata.Tests.")
        })), "None", "Passed", 0, "None")
        for provider in ("memory", "sqlite"))


def original_artifact_publication_scenarios():
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses
        if witness.startswith("Hoard.Artifacts.Tests.ArtifactPublicationTests.")
    }
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
        "Shared_duplicate_assertion_rejects_substituted_source_and_accepts_original_store"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-publication", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_read_delete_scenarios():
    methods = {
        "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
        "Destination_failure_and_second_copy_never_return_verified_completion_or_dispose_borrowed_streams",
        "Hoard.Artifacts.Tests.ArtifactDeletionTests."
        "Exact_delete_receipts_and_recreation_never_remove_the_new_incarnation",
        "Hoard.Artifacts.Tests.ArtifactDeletionTests."
        "A_held_reader_finishes_before_exclusive_deletion_and_later_opens_cannot_enter",
    }
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.split("(")[0] in methods
    }
    return (("original-artifact-read-delete", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_deletion_settlement_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactDeletionTests."
    methods = {prefix + name for name in (
        "Lost_delete_acknowledgment_preserves_pending_reclamation_until_actual_cleanup",
        "Live_reference_or_unavailable_reference_authority_denies_removal",
    )}
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.split("(")[0] in methods}
    return (("original-artifact-deletion-settlement", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_admission_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactAdmissionTests."
    methods = {prefix + name for name in (
        "Before_admission_and_with_mismatched_authority_no_source_or_directory_is_touched",
        "Symlinked_root_or_ancestor_is_rejected_without_touching_outside_sentinel",
    )}
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.split("(")[0] in methods}
    identities.update(
        prefix + name + f'(provider: "{provider}")'
        for name in (
            "Noncooperative_initialization_returns_with_owned_work_and_stop_does_not_release_it",
            "Create_is_explicit_exclusive_and_disabled_construction_touches_no_directory",
            "Reopen_refuses_missing_foreign_incompatible_or_corrupt_roots_without_reset",
        ) for provider in ("local", "object"))
    identities.add(prefix + "Local_reopen_preserves_identity_while_object_replacement_cannot_claim_durable_reopen")
    return (("original-artifact-admission", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_recovery_reopen_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactRecoveryTests."
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness == prefix +
        "Stop_retains_unselected_object_ownership_and_retries_only_its_private_payload"}
    identities.update(prefix + name for name in (
        "Local_reopen_preserves_committed_decisions_after_expired_ticket_retirement_and_clock_rollback",
        "Reopen_finishes_staging_release_after_a_durable_commit_receipt",
    ))
    return (("original-artifact-recovery-reopen", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_recovery_race_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactRecoveryTests."
    methods = {prefix + name for name in (
        "Expired_reclaimed_history_remains_owned_until_the_admitted_delete_physically_settles",
        "Late_cleanup_rechecks_the_exact_generation_after_replacement",
        "Progressing_commit_renews_owner_across_the_original_ttl",
    )}
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.split("(")[0] in methods}
    identities.update(
        prefix + name + f'(provider: "{provider}")'
        for name in (
            "Admitted_reconciliation_preserves_the_settled_receipt_after_delete_and_recreate",
            "Expired_history_is_not_retired_beneath_an_admitted_reconciliation",
        ) for provider in ("local", "object"))
    return (("original-artifact-recovery-races", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_recovery_pages_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactRecoveryTests."
    methods = {prefix + name for name in (
        "Sequential_recovery_retires_consumed_cursors_without_starving_independent_scans",
        "Changed_inventory_rejects_old_continuations_and_fresh_pages_cover_every_current_identity",
        "Expiry_cleanup_and_restage_fence_the_old_generation",
        "Recovery_pages_are_bounded_query_bound_and_not_deletion_authority",
    )}
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.split("(")[0] in methods}
    identities.update(
        prefix + name + f'(provider: "{provider}")'
        for name in (
            "Expired_ownerless_reservations_release_capacity_without_replaying_old_tickets",
            "Cleanup_cannot_reopen_a_finalized_noncommit",
        ) for provider in ("local", "object"))
    return (("original-artifact-recovery-pages", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_validation_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactEvidenceTests."
    methods = {prefix + name for name in (
        "Local_failed_quarantine_persistence_retains_ownership_until_stop_retry_and_reopen",
        "Validation_first_corruption_cannot_be_revived_by_external_restoration",
        "Validation_access_failure_does_not_quarantine_intact_content",
    )}
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.split("(")[0] in methods}
    return (("original-artifact-validation", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_quarantine_reopen_scenarios():
    methods = {
        "Hoard.Artifacts.Tests.ArtifactReadVerificationTests.Every_committed_detection_path_quarantines_restored_bytes",
        "Hoard.Artifacts.Tests.ArtifactReadVerificationTests.Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence",
        "Hoard.Artifacts.Tests.ArtifactPublicationRaceTests.Corrupt_existing_bytes_are_not_overwritten_or_reused",
    }
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses
        if witness.split("(")[0] in methods}
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactEvidenceConsumerTests."
        "Shared_quarantine_consumers_reject_lost_reopen_denial_and_accept_original_store"
        f'(consumer: "{consumer}")'
        for consumer in ("damaged-read", "committed-detection", "corrupt-existing"))
    return (("original-artifact-quarantine-reopen", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_detection_scenarios():
    method = ("Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
              "Every_committed_detection_path_quarantines_restored_bytes")
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith(method + "(")}
    return (("original-artifact-detection", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_read_race_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
    identities = {prefix + "Local_reconciliation_cannot_finalize_after_overlapping_read_quarantines_the_incarnation"}
    identities.update(prefix + f'Admitted_open_rechecks_quarantine_before_delivering_a_session(provider: "{provider}")'
                      for provider in ("local", "object"))
    return (("original-artifact-read-races", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_damaged_read_scenarios():
    method = ("Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
              "Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence")
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith(method + "(")}
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactEvidenceConsumerTests."
        "Shared_damaged_read_assertion_rejects_revived_evidence_and_accepts_original_validator"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-damaged-read", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_evidence_scenarios():
    read_methods = {
        "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
        "Every_committed_detection_path_quarantines_restored_bytes",
        "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
        "Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence",
    }
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith("Hoard.Artifacts.Tests.ArtifactEvidenceTests.")
        or witness.split("(")[0] in read_methods
    }
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactEvidenceConsumerTests."
        "Shared_receipt_assertion_rejects_wrong_receipt_acceptance_and_accepts_original_validator"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-evidence", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


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


def prepare_package_consumer_lock(candidate, feed, *, project=TESTS, local_packages=LOCAL_PACKAGES):
    original = candidate / project / "PackageAcceptance/packages.lock.json"
    raw = read_bounded(original, 2 * 1024 * 1024)
    prepared, packages, _ = rebind_local_archives(raw, feed)
    expected = {f"{name}.0.1.0.nupkg" for name in local_packages}
    if set(packages) != expected:
        raise evidence.ConformanceError("InputChanged")
    alternate = candidate / project / "obj/F07.consumer.packages.lock.json"
    no_symlinks(alternate)
    alternate.parent.mkdir(exist_ok=True, mode=0o700)
    write_new(alternate, prepared)
    return alternate, {
        "qualification": False, "mode": "preparation",
        "sourceLockSha256": hashlib.sha256(raw).hexdigest(),
        "preparedLockSha256": hashlib.sha256(prepared).hexdigest(), "packages": packages,
    }


def verify_package_consumer_lock(candidate, feed, alternate, receipt, *, project=TESTS):
    raw = read_bounded(candidate / project / "PackageAcceptance/packages.lock.json", 2 * 1024 * 1024)
    prepared, packages, _ = rebind_local_archives(raw, feed)
    if (set(receipt) != {"qualification", "mode", "sourceLockSha256", "preparedLockSha256", "packages"}
            or receipt["qualification"] is not False or receipt["mode"] != "preparation"
            or hashlib.sha256(raw).hexdigest() != receipt["sourceLockSha256"]
            or hashlib.sha256(prepared).hexdigest() != receipt["preparedLockSha256"]
            or packages != receipt["packages"]
            or read_bounded(alternate, 2 * 1024 * 1024) != prepared):
        raise evidence.ConformanceError("InputChanged")


def verify_runtime_packages(output, feed, packages):
    for package in packages:
        identity = evidence.package_identity(feed, package, "0.1.0")
        assembly = f"{package}.dll"
        if evidence.file_sha256(output / assembly) != identity["runtimeAssemblies"].get(
                f"lib/net10.0/{assembly}"):
            raise evidence.ConformanceError("InputChanged")


def _original_wrapper_runtime(candidate, feed, project, output_folder, packages):
    output = candidate / project / output_folder / "Release/net10.0"
    logger = "Hoard.Conformance.TestLogger"
    write_new(output / f"{logger}.dll", read_bounded(
        candidate / LOGGER / f"bin/Release/net10.0/{logger}.dll", 64 * 1024 * 1024))
    verify_runtime_packages(output, feed, (*packages, logger))


def metadata_wrapper_runtime(candidate, feed):
    _original_wrapper_runtime(candidate, feed, METADATA_TESTS, METADATA_TEST_OUTPUT, METADATA_PACKAGES)


def artifact_wrapper_runtime(candidate, feed):
    _original_wrapper_runtime(candidate, feed, ARTIFACT_TESTS, ARTIFACT_TEST_OUTPUT, ARTIFACT_PACKAGES)


def build_artifact_assertion_consumer(run, candidate, config, feed):
    for name in ("Local", "ObjectSemantics"):
        project = candidate / f"tests/fixtures/conformance/Bindings/{name}/{name}.csproj"
        lock, record = prepare_project_lock(project, candidate, feed, "candidate")
        build(run, project, config, "artifact-binding-package", lock=lock, feed=feed,
              package_id="Hoard.Fixtures.Conformance.Bindings." + name)
        if record is not None:
            verify_project_lock(record, candidate, feed)
            write_new(run.root / f"proofs/artifact-binding-{name}-lock-derivation.json",
                      evidence.canonical_bytes(record))
    project = candidate / ARTIFACT_CONSUMER / "Consumer.csproj"
    lock, record = prepare_project_lock(project, candidate, feed, "candidate")
    build(run, project, config, "artifact-consumer-locked-replay", lock=lock,
          properties=("-p:BaseOutputPath=" + PACKAGE_TEST_OUTPUT + "/", "-p:ConformanceCategoryMutations=true"))
    if record is not None:
        verify_project_lock(record, candidate, feed)
        write_new(run.root / "proofs/artifact-consumer-lock-derivation.json", evidence.canonical_bytes(record))
    _original_wrapper_runtime(candidate, feed, ARTIFACT_CONSUMER, PACKAGE_TEST_OUTPUT, ARTIFACT_CONSUMER_PACKAGES)


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


def admit_owned_command(command, sequence, *, scope, detail, exit_code, max_duration):
    fields = {
        "schemaVersion", "sequence", "childPid", "childStartSha256", "startedMs", "endedMs",
        "exitCode", "diagnosticCode", "groupState", "scope", detail,
    }
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


def admit_transfer_measurement(command, sequence, size):
    admit_owned_command(command, sequence, scope="transfer", detail="transfer", exit_code=0, max_duration=2400000)
    measured = command["transfer"]
    fields = {"bytes", "phase", "baselineRssBytes", "osPeakRssBytes", "sampledPeakRssBytes",
              "samples", "osPeakMethod", "baselineMs", "completedMs"}
    if (type(size) is not int or size not in (268435456, 4294967296)
            or not isinstance(measured, dict) or set(measured) != fields
            or any(type(measured[key]) is not int or not 0 < measured[key] <= 2**63 - 1
                   for key in ("bytes", "baselineRssBytes", "osPeakRssBytes", "sampledPeakRssBytes", "samples"))
            or measured["bytes"] != size or measured["phase"] != "complete"
            or measured["osPeakMethod"] != "proc-status" or measured["samples"] < 2
            or not measured["baselineRssBytes"] <= measured["sampledPeakRssBytes"] <= measured["osPeakRssBytes"]
            or measured["osPeakRssBytes"] - measured["baselineRssBytes"] > 67108864):
        raise evidence.ConformanceError("ProofMismatch")
    times = (command["startedMs"], measured["baselineMs"], measured["completedMs"], command["endedMs"])
    if (any(type(item) not in (int, float) or not 0 <= item <= 2**63 - 1 or not math.isfinite(item)
            for item in times) or tuple(sorted(times)) != times):
        raise evidence.ConformanceError("ProofMismatch")


def measured_artifact_transfer(run, inputs, assembly, provider, size, expected_hash):
    store = run.root / f"stores/artifact-transfers/transfer-{provider}-{size}"
    store.mkdir(mode=0o700)
    sequence = run.command_sequence + 1
    result = run.command(
        ["dotnet", str(assembly), provider, str(store), str(size), expected_hash, run.run_id],
        cwd=assembly.parent, scope="transfer", measure_transfer_bytes=size, cache_id="artifact-transfers",
        env={"HOARD_CONFORMANCE_SAFE_EVENTS": "1"})
    if run.live_children():
        raise evidence.ConformanceError("CleanupIncomplete")
    if result.exit_code or tuple(dict(item) for item in result.events) != (
            {"event": "control", "code": "None", "value": 0},
            {"event": "test", "code": "None", "value": size},
            {"event": "control", "code": "None", "value": 1}):
        raise evidence.ConformanceError("EvidenceIncomplete")
    raw = read_bounded(run.root / f"proofs/transfer-command-{sequence:04}.json", 64 * 1024)
    command = evidence.load_json(raw)
    admit_transfer_measurement(command, sequence, size)
    producer_path = store / "transfer-proof.json"
    producer_raw = read_bounded(producer_path, 8192)
    producer = evidence.load_json(producer_raw)
    fields = {
        "eventName", "provider", "runId", "pid", "size", "written", "read", "expectedSha256",
        "sourceSha256", "sinkSha256", "runtime", "sourcePaced", "sinkPaced", "nonSeekable",
        "generated", "independentExpectedHash", "warmupComplete", "bufferBytes", "providerBufferLimit", "slots",
    }
    if (not isinstance(producer, dict) or set(producer) != fields or producer["eventName"] != "complete"
            or producer["pid"] != command["childPid"] or producer["expectedSha256"] != expected_hash
            or producer["runtime"] != ".NET " + inputs["environment"]["runtime"]):
        raise evidence.ConformanceError("ProofMismatch")
    measured = command["transfer"]
    proof = {**producer, **{name: measured[name] for name in (
        "baselineRssBytes", "osPeakRssBytes", "sampledPeakRssBytes", "samples", "osPeakMethod")},
             "rssUnits": "bytes", "exitCode": command["exitCode"]}
    try:
        artifacts.verify_transfer(proof, provider, size, run.run_id, peak_methods=("proc-status",))
    except RuntimeError:
        raise evidence.ConformanceError("ProofMismatch") from None
    directory = run.root / f"proofs/artifact-transfers/transfer-{provider}-{size}"
    directory.mkdir(mode=0o700)
    proof_path = directory / "proof.json"
    write_new(proof_path, evidence.canonical_bytes(proof))
    producer_path.chmod(0o400)
    return {
        "provider": provider, "size": size, "controllerSha256": hashlib.sha256(raw).hexdigest(),
        "producerSha256": hashlib.sha256(producer_raw).hexdigest(),
        "proofSha256": evidence.file_sha256(proof_path), "childStartSha256": command["childStartSha256"],
    }


def artifact_transfer_diagnostics(run, inputs, candidate):
    runtime = candidate / ARTIFACT_TRANSFER / "bin/Release/net10.0"
    assembly = runtime / "Hoard.Fixtures.Artifacts.TransferRunner.dll"
    verify_runtime_packages(runtime, run.root / "feed/candidate", ARTIFACT_RECOVERY_PACKAGES)
    if inputs.get("runtimeAssemblies", {}).get(assembly.relative_to(run.root).as_posix()) != evidence.file_sha256(assembly):
        raise evidence.ConformanceError("InputChanged")
    for folder in ("stores", "proofs"):
        parent = run.root / folder / "artifact-transfers"
        no_symlinks(parent)
        parent.mkdir(mode=0o700)
    hashes = {size: artifacts.expected_transfer_hash(size) for size in (268435456, 4294967296)}
    observations = [
        measured_artifact_transfer(run, inputs, assembly, provider, size, hashes[size])
        for provider in ("local", "object") for size in hashes]
    result = {
        "qualification": False, "mode": "artifact-transfers", "code": "None",
        "inputsSha256": evidence.digest(inputs), "transfers": observations,
    }
    write_new(run.root / "proofs/artifact-transfers.json", evidence.canonical_bytes(result))
    return result


def recovery_command(run, assembly, arguments, *, cache_id, value=None):
    sequence = run.command_sequence + 1
    result = run.command(
        ["dotnet", str(assembly), *arguments], cwd=assembly.parent, scope="recovery",
        env={"HOARD_CONFORMANCE_SAFE_EVENTS": "1"}, stop_at_barrier=value, cache_id=cache_id)
    if run.live_children():
        raise evidence.ConformanceError("CleanupIncomplete")
    if value is None:
        if result.exit_code or tuple(dict(item) for item in result.events) != (
                {"event": "test", "code": "None", "value": 1},):
            raise evidence.ConformanceError("EvidenceIncomplete")
    elif result.exit_code != -9 or tuple(dict(item) for item in result.events) != (
            {"event": "barrier", "code": "None", "value": value},):
        raise evidence.ConformanceError("ProofMismatch")
    raw = read_bounded(run.root / f"proofs/recovery-command-{sequence:04}.json", 64 * 1024)
    command = evidence.load_json(raw)
    if value is not None:
        admit_recovery_barrier(command, sequence, value)
    return hashlib.sha256(raw).hexdigest(), command


def metadata_recovery_diagnostics(run, inputs, candidate):
    runtime = candidate / METADATA_RECOVERY / "bin/Release/net10.0"
    assembly = runtime / "Hoard.Fixtures.Metadata.CrashRunner.dll"
    require_sqlite_environment(inputs, assembly, run.root)
    verify_runtime_packages(runtime, run.root / "feed/candidate", METADATA_RECOVERY_PACKAGES)
    assembly_key = assembly.relative_to(run.root).as_posix()
    if inputs.get("runtimeAssemblies", {}).get(assembly_key) != evidence.file_sha256(assembly):
        raise evidence.ConformanceError("InputChanged")
    parent = run.root / "stores/sqlite-recovery"
    no_symlinks(parent)
    parent.mkdir(mode=0o700)

    def execute(mode, directory, barrier, value=None):
        return recovery_command(
            run, assembly, [mode, str(directory / "metadata.db"), str(directory), barrier],
            cache_id="sqlite-recovery", value=value)

    observations = []
    for kind, barriers in (
            ("mutation", (("M0", 0), ("M1", 1), ("M2", 2))),
            ("upgrade", tuple((f"U{index}", 10 + index) for index in range(5))),
            ("restore", (("R0", 20), ("R1", 21)))):
        for barrier, value in barriers:
            directory = parent / barrier
            directory.mkdir(mode=0o700)
            seed_sha, _ = execute("seed-" + kind, directory, barrier)
            controller_sha, command = execute("run-" + kind, directory, barrier, value)
            readback_sha, _ = execute("recover-" + kind, directory, barrier)
            observations.append({
                "barrierId": barrier, "value": value, "seedSha256": seed_sha,
                "controllerSha256": controller_sha, "readbackSha256": readback_sha,
                "childStartSha256": command["childStartSha256"],
            })
    walkthrough = parent / "walkthrough"
    walkthrough.mkdir(mode=0o700)
    walkthrough_sha, _ = execute("recovery-walkthrough", walkthrough, "none")
    result = {
        "qualification": False, "mode": "metadata-recovery", "code": "None",
        "inputsSha256": evidence.digest(inputs), "barriers": observations,
        "walkthroughSha256": walkthrough_sha,
    }
    write_new(run.root / "proofs/sqlite-recovery.json", evidence.canonical_bytes(result))
    return result


def artifact_recovery_diagnostics(run, inputs, candidate):
    runtime = candidate / ARTIFACT_RECOVERY / "bin/Release/net10.0"
    assembly = runtime / "Hoard.Fixtures.Artifacts.CrashRunner.dll"
    verify_runtime_packages(runtime, run.root / "feed/candidate", ARTIFACT_RECOVERY_PACKAGES)
    assembly_key = assembly.relative_to(run.root).as_posix()
    if inputs.get("runtimeAssemblies", {}).get(assembly_key) != evidence.file_sha256(assembly):
        raise evidence.ConformanceError("InputChanged")
    parent = run.root / "stores/local-recovery"
    no_symlinks(parent)
    parent.mkdir(mode=0o700)
    observations = []
    for value, barrier in enumerate(("B0", "B1", "B2", "B3", "D0", "D1"), 40):
        directory = parent / barrier
        directory.mkdir(mode=0o700)
        arguments = [str(directory / "store"), str(directory / "state.json"), barrier, str(uuid.uuid4())]
        controller_sha, command = recovery_command(
            run, assembly, ["crash", *arguments], cache_id="local-recovery", value=value)
        readback_sha, _ = recovery_command(
            run, assembly, ["recover", *arguments], cache_id="local-recovery")
        observations.append({
            "barrierId": barrier, "value": value, "controllerSha256": controller_sha,
            "readbackSha256": readback_sha, "childStartSha256": command["childStartSha256"],
        })
    result = {
        "qualification": False, "mode": "artifact-recovery", "code": "None",
        "inputsSha256": evidence.digest(inputs), "barriers": observations,
    }
    write_new(run.root / "proofs/local-recovery.json", evidence.canonical_bytes(result))
    return result


def admit_artifact_noncooperation(observed, provider, scenario, phase, pid, run_id):
    fields = {
        "eventName", "phase", "pid", "runId", "provider", "scenario", "durableCrashProof",
        "cleanup", "callerCode", "admissionCode", "shutdownCode", "enteredWorkers",
        "workerPending", "borrowedStreamsIntact", "rootStillOwned", "readinessBlocked", "protectionRetained",
    }
    if (provider not in ("local", "object") or scenario not in ("source", "destination", "native")
            or phase not in ("contained", "inspected") or not isinstance(observed, dict) or set(observed) != fields
            or observed["eventName"] != "noncooperative" or observed["phase"] != phase
            or type(observed["pid"]) is not int or observed["pid"] != pid
            or observed["runId"] != run_id or observed["provider"] != provider or observed["scenario"] != scenario
            or observed["durableCrashProof"] is not False or observed["cleanup"] != "RetainedLiveOwnership"
            or observed["callerCode"] not in (
                ("DeadlineExceeded", "Uncertain") if scenario == "native" else ("CancelledBeforeCommit",))
            or observed["admissionCode"] != "CleanupIncomplete" or observed["shutdownCode"] != "CleanupIncomplete"
            or type(observed["enteredWorkers"]) is not int or observed["enteredWorkers"] != 1
            or any(observed[key] is not True for key in (
                "workerPending", "borrowedStreamsIntact", "rootStillOwned", "readinessBlocked"))
            or observed["protectionRetained"] is not (scenario != "source")):
        raise evidence.ConformanceError("ProofMismatch")


def artifact_noncooperation(run, assembly, provider, scenario):
    directory = run.root / f"stores/artifact-noncooperation/{provider}-{scenario}"
    directory.mkdir(mode=0o700)
    run_id = str(uuid.uuid4())
    offset = ("source", "destination", "native").index(scenario)
    first, last = 60 + offset, 70 + offset
    sequence = run.command_sequence + 1
    result = run.command(
        ["dotnet", str(assembly), "noncooperative", str(directory), provider, scenario, run_id],
        cwd=assembly.parent, scope="recovery", inspect_at_barrier=first, stop_at_barrier=last,
        env={"HOARD_CONFORMANCE_SAFE_EVENTS": "1"}, cache_id="artifact-noncooperation")
    if run.live_children():
        raise evidence.ConformanceError("CleanupIncomplete")
    if result.exit_code != -9 or tuple(dict(item) for item in result.events) != (
            {"event": "barrier", "code": "None", "value": first},
            {"event": "barrier", "code": "None", "value": last}):
        raise evidence.ConformanceError("ProofMismatch")
    raw = read_bounded(run.root / f"proofs/recovery-command-{sequence:04}.json", 64 * 1024)
    command = evidence.load_json(raw)
    admit_recovery_barrier(command, sequence, last, inspection=first)
    hashes = {}
    for phase in ("contained", "inspected"):
        path = directory / f"noncooperative-{phase}.json"
        data = read_bounded(path, 8192)
        observed = evidence.load_json(data)
        admit_artifact_noncooperation(observed, provider, scenario, phase, command["childPid"], run_id)
        hashes[phase + "Sha256"] = hashlib.sha256(data).hexdigest()
        path.chmod(0o400)
    return {
        "provider": provider, "scenario": scenario, **hashes,
        "controllerSha256": hashlib.sha256(raw).hexdigest(), "childStartSha256": command["childStartSha256"],
    }


def artifact_noncooperation_diagnostics(run, inputs, candidate):
    runtime = candidate / ARTIFACT_RECOVERY / "bin/Release/net10.0"
    assembly = runtime / "Hoard.Fixtures.Artifacts.CrashRunner.dll"
    verify_runtime_packages(runtime, run.root / "feed/candidate", ARTIFACT_RECOVERY_PACKAGES)
    if inputs.get("runtimeAssemblies", {}).get(assembly.relative_to(run.root).as_posix()) != evidence.file_sha256(assembly):
        raise evidence.ConformanceError("InputChanged")
    parent = run.root / "stores/artifact-noncooperation"
    no_symlinks(parent)
    parent.mkdir(mode=0o700)
    observations = [artifact_noncooperation(run, assembly, provider, scenario)
                    for provider in ("local", "object") for scenario in ("source", "destination", "native")]
    result = {
        "qualification": False, "durableCrashProof": False, "mode": "artifact-noncooperation", "code": "None",
        "inputsSha256": evidence.digest(inputs), "observations": observations,
    }
    write_new(run.root / "proofs/artifact-noncooperation.json", evidence.canonical_bytes(result))
    return result


def local_artifact_session_scenarios():
    identities = {
        ARTIFACT_CONSUMER_PREFIX + f'Owned_local_projection_executes_unchanged_common_consumers(consumer: "{consumer}")'
        for consumer in ("publication", "expectations", "private-staging")}
    identities.update(ARTIFACT_CONSUMER_PREFIX + method for method in (
        "All_typed_observation_points_can_be_registered_together_and_removed_without_overwrite",
        "Scoped_observation_cannot_overwrite_a_live_registration_or_remove_its_replacement",
        "Local_reopen_keeps_identity_authority_content_and_allocation_without_stale_disposal",
        "Physical_store_stop_cannot_release_a_live_authority_guard_or_erase_retained_observation",
        "Concurrent_disposers_join_one_attempt_and_the_same_actual_settlement",
        "Failed_initialization_retains_allocator_ownership_and_joins_actual_shutdown"))
    identities.update(ARTIFACT_CONSUMER_PREFIX
        + "Released_boundary_stays_owned_through_actual_callback_and_reopen_or_disposal(reopen: " + value + ")"
        for value in ("False", "True"))
    for method, parameter in (
        ("Observer_failure_before_or_during_cleanup_remains_in_the_same_actual_settlement", "duringCleanup"),
        ("Concurrent_direct_stop_and_disposal_retry_reuse_the_pending_allocator_observation", "actualAllocator"),
    ):
        identities.update(ARTIFACT_CONSUMER_PREFIX + method + f"({parameter}: {value})"
                          for value in ("False", "True"))
    return (("local-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def artifact_authority_ownership_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactAuthorityOwnershipTests."
    identities = {prefix + name for name in (
        "Shutdown_fence_joins_recognized_retained_and_queued_guards_before_reopen",
        "Shutdown_fence_joins_actual_noncooperating_reference_query_before_reopen",
        "Shutdown_fence_observes_canceled_waiter_without_losing_the_current_guard")}
    identities.update(prefix + "Released_operation_callback_remains_real_owned_work_until_final_settlement"
                      + f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-authority-ownership", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def object_artifact_session_scenarios():
    prefix = OBJECT_ARTIFACT_CONSUMER_PREFIX
    identities = {
        prefix + f'Owned_object_projection_executes_unchanged_common_consumers(consumer: "{consumer}")'
        for consumer in ("publication", "expectations", "private-staging")}
    identities.update(prefix + method for method in (
        "All_typed_observations_register_together_and_stale_disposal_cannot_remove_a_replacement",
        "Object_restart_joins_old_authority_and_uses_fresh_epoch_authority_and_private_child",
        "Failed_replacement_keeps_the_original_as_cleanup_handle",
        "Failed_initialization_joins_actual_shutdown_without_erasing_foreign_content",
        "Cancellation_while_joining_old_authority_does_not_admit_a_replacement",
        "Cancellation_during_replacement_admission_retains_the_unpublished_generation",
        "Retained_authority_and_concurrent_disposers_retry_the_same_settlement"))
    for method, parameter in (
        ("Released_callback_stays_owned_until_restart_or_final_settlement", "restart"),
        ("Observer_failure_before_or_during_cleanup_faults_the_same_actual_settlement", "duringCleanup"),
        ("Direct_stop_and_disposal_retries_reuse_the_pending_allocator_observation", "actualAllocator"),
    ):
        identities.update(prefix + method + f"({parameter}: {value})" for value in ("False", "True"))
    return (("object-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def artifact_observation_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactObservationTests."
    identities = tuple(sorted(prefix + method + f'(provider: "{provider}")' for method in (
        "Persisted_receipt_boundary_exposes_the_same_actual_reconciled_receipt",
        "Failed_opened_read_callback_reclaims_real_stream_guard_and_single_transfer_slot",
        "Verified_reconciliation_callback_failure_keeps_actual_uncertain_publication_recoverable")
        for provider in ("local", "object")))
    return (("original-artifact-observations", identities, "None", "Passed", 0, "None"),)


def configured_artifact_session_scenarios():
    prefix = CONFIGURED_ARTIFACT_CONSUMER_PREFIX
    identities = {
        prefix + method + f'(provider: "{provider}")' for method in (
            "Actual_configured_limits_survive_compatible_or_logical_reopen",
            "Current_reference_queries_fence_deletion_on_each_actual_generation",
            "Unavailable_reference_query_cannot_become_an_optimistic_zero_reference_decision")
        for provider in ("local", "object")}
    identities.add(prefix + "Invalid_reference_observations_cannot_admit_negative_counts_or_missing_available_revisions")
    identities.update(prefix
        + f'Timed_out_reference_query_stays_owned_through_reopen_or_final_settlement(provider: "{provider}", reopen: {reopen})'
        for provider in ("local", "object") for reopen in ("False", "True"))
    return (("configured-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def full_artifact_binding_scenarios():
    prefix = FULL_ARTIFACT_CONSUMER_PREFIX
    identities = {
        prefix + "Full_binding_controls_reach_actual_work_and_preserve_borrowed_ownership"
        + f'(provider: "{provider}", fault: {fault})'
        for provider in ("local", "object") for fault in (
            "PublicationBoundary", "DirectVisibility", "PayloadDamage", "Capacity",
            "NativeNonCooperation", "CleanupFailure", "GenerationBoundary", "ReceiptBoundary",
            "SourceNonCooperation", "SinkNonCooperation")}
    identities.update(prefix + "Observed_full_binding_reopens_actual_components_and_fences_stale_controls"
                      + f'(provider: "{provider}", retainsPublication: {retained})'
                      for provider, retained in (("local", "True"), ("object", "False")))
    identities.update(prefix + "Releasing_native_work_does_not_block_an_independent_release_or_rearming"
                      + f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("full-artifact-binding", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def category_mutation_scenarios():
    result = []
    for category, providers, faulty_method, corrected_method in (
            ("metadata", ("memory", "sqlite"),
             "Stale_metadata_replay_is_rejected", "Corrected_metadata_replay_passes"),
            ("artifacts", ("local", "object"),
             "Premature_artifact_publication_is_rejected", "Corrected_artifact_staging_passes")):
        for corrected in (False, True):
            name = f"category-mutation-{category}-{'corrected' if corrected else 'faulty'}"
            selected = corrected_method if corrected else faulty_method
            identities = tuple(sorted(
                CATEGORY_MUTATION_PREFIX + selected + f'(provider: "{provider}")'
                for provider in providers))
            result.append((name, identities, "None" if corrected else "AssertionFailed",
                           "Passed" if corrected else "Failed", 0 if corrected else 1,
                           "None" if corrected else "Assertion"))
    return tuple(result)


def actual_authority_integration_scenarios():
    method = AUTHORITY_INTEGRATION_PREFIX + "Actual_compositions_preserve_shared_authority"
    identities = {
        f'{method}(provider: "{provider}", metadataProvider: "{metadata}", consumer: "{consumer}")'
        for provider in ("local", "object") for metadata in ("memory", "sqlite") for consumer in (
            "reference-admission", "failed-transaction", "live-references", "lost-acknowledgment",
            "incarnation", "reader", "foreign-authority", "shutdown")}
    return (("actual-authority-integration", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def full_metadata_binding_scenarios():
    return (("full-metadata-binding", tuple(sorted(full_metadata_binding_origin_counts())),
             "None", "Passed", 0, "None"),)


def full_metadata_binding_origin_counts():
    method = (FULL_METADATA_CONSUMER_PREFIX
              + "Observed_factories_execute_unchanged_common_consumers_with_actual_origins")
    identities = {
        f'{method}(provider: "{provider}", consumer: "{consumer}")': 1
        for provider in ("memory", "sqlite") for consumer in (
            "capacity", "writer", "publication", "entities", "graph", "independent",
            "atomic", "grouped", "lease-generation", "lease-fences",
            "lease-renew", "lease-release", "lease-guard",
            "text", "registry", "authorization", "references", "reference-aba", "telemetry",
            "create-race", "revision-race", "reconcile-writer", "reconcile-io",
            "reconcile-ack", "contributions", "receipts", "layout-empty", "layout-partial",
            "bounds", "scopes", "page-kinds", "page-size", "page-datasets",
            "time-ticket", "time-lease", "cancel", "queue", "exceptions", "ledger", "diagnostics",
            "evidence", "publication-replay", "publication-orphan", "corrupt-groups", "corrupt-pages",
            "admission", "invalid-budget", "incomplete-cleanup", "disposal")}
    reopen = FULL_METADATA_CONSUMER_PREFIX + "Observed_reopen_preserves_public_state_and_fences_stale_controls"
    identities.update({f'{reopen}(provider: "{provider}")': 2 for provider in ("memory", "sqlite")})
    schema = FULL_METADATA_CONSUMER_PREFIX + "Observed_schema_consumers_preserve_actual_reopen_lineage"
    identities.update({
        f'{schema}(provider: "{provider}", consumer: "{consumer}")': count
        for provider in ("memory", "sqlite") for consumer, count in (
            ("upgrade", 3), ("upgrade-invalid", 2), ("upgrade-exclusive", 2), ("future-corrupt", 4))})
    cursor = FULL_METADATA_CONSUMER_PREFIX + "Observed_continuation_corruption_preserves_actual_pages"
    identities.update({
        f'{cursor}(provider: "{provider}", corruption: {corruption})': 1
        for provider in ("memory", "sqlite") for corruption in (
            "Null", "Omitted", "WrongType", "Empty", "OddHex", "InvalidHex")})
    dimensions = FULL_METADATA_CONSUMER_PREFIX + "Observed_query_corruption_preserves_actual_dimensions"
    identities.update({
        f'{dimensions}(provider: "{provider}", corruption: {corruption})': 1
        for provider in ("memory", "sqlite") for corruption in (
            "CacheAuthorization", "AggregateAuthorization", "AggregateStart", "AggregateEnd", "LeaseResource")})
    epoch = FULL_METADATA_CONSUMER_PREFIX + "Observed_continuations_reject_foreign_actual_store_epochs"
    identities.update({f'{epoch}(provider: "{provider}")': 2 for provider in ("memory", "sqlite")})
    return identities


def validate_full_binding_origins(ingested, inputs, counts):
    bindings = {binding["bindingId"]: binding["descriptorSha256"] for binding in inputs["bindings"]}
    for witness in ingested["witnesses"]:
        origins = ingested["sessionOrigins"][witness["executionId"]]
        if (len(origins) != counts.get(witness["testIdentity"])
                or any(origin["descriptorSha256"] != bindings.get(witness["bindingId"]) for origin in origins)):
            raise evidence.ConformanceError("WitnessMissing")


def _binding_origin_inputs(candidate, root, category, providers, store_roles):
    runtime = candidate / ARTIFACT_CONSUMER / PACKAGE_TEST_OUTPUT / "Release/net10.0"
    result = {}
    for provider, adapter in providers:
        binding = "Hoard.Fixtures.Conformance.Bindings." + adapter
        store = "Hoard.Fixtures." + category.title() + "." + adapter
        try:
            result["fixture." + category.rstrip("s") + "." + provider] = {
                role: ((runtime / (package + ".dll")).relative_to(root).as_posix(), package)
                for role, package in (
                    ("factory", binding), ("session", binding), ("faults", binding), ("authority", binding),
                    *((role, store) for role in store_roles))}
        except ValueError as error:
            raise evidence.ConformanceError("InputChanged") from error
    return result


def artifact_origin_inputs(candidate, root):
    return _binding_origin_inputs(candidate, root, "artifacts",
                                  (("local", "Local"), ("object", "ObjectSemantics")),
                                  ("store", "validator", "maintenance", "lifetime"))


def metadata_origin_inputs(candidate, root):
    return _binding_origin_inputs(candidate, root, "metadata",
                                  (("memory", "Memory"), ("sqlite", "Sqlite")), ("store", "schema"))


def metadata_binding_declarations(feed):
    faults = [
        "IndependentSnapshot", "WriterContention", "CommitAcknowledgement", "PersistedCorruption",
        "Capacity", "SchemaState", "LeaseBoundary", "NativeNonCooperation", "CleanupFailure"]
    result = []
    for provider, adapter, capabilities in (
            ("memory", "Memory", ["metadata", "non-durable", "logical-schema-upgrade"]),
            ("sqlite", "Sqlite", ["metadata", "durable", "schema-upgrade", "backup-recovery"])):
        package = "Hoard.Fixtures.Metadata." + adapter
        result.append({
            "schemaVersion": 1, "bindingId": "fixture.metadata." + provider, "category": "metadata",
            "packageId": package, "packageVersion": "0.1.0",
            "packageSha256": evidence.package_identity(feed, package, "0.1.0")["sha256"],
            "capabilities": capabilities, "faults": list(faults)})
    return tuple(result)


def artifact_binding_declarations(feed):
    faults = [
        "PublicationBoundary", "DirectVisibility", "PayloadDamage", "Capacity", "NativeNonCooperation",
        "CleanupFailure", "GenerationBoundary", "ReceiptBoundary", "SourceNonCooperation", "SinkNonCooperation"]
    result = []
    for provider, adapter, capability in (
            ("local", "Local", "durable-local-process-crash"), ("object", "ObjectSemantics", "non-durable-simulation")):
        package = "Hoard.Fixtures.Artifacts." + adapter
        result.append({
            "schemaVersion": 1, "bindingId": "fixture.artifact." + provider, "category": "artifacts",
            "packageId": package, "packageVersion": "0.1.0",
            "packageSha256": evidence.package_identity(feed, package, "0.1.0")["sha256"],
            "capabilities": ["artifacts", capability], "faults": list(faults)})
    return tuple(result)


def artifact_synchronous_storage_scenarios():
    method = (PAYLOAD_ARTIFACT_CONSUMER_PREFIX
              + "Synchronous_storage_hold_retains_actual_worker_and_protection_until_release")
    identities = {method + f'(provider: "{provider}")' for provider in ("local", "object")}
    return (("artifact-synchronous-storage", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def artifact_unclaimed_cleanup_scenarios():
    method = (PAYLOAD_ARTIFACT_CONSUMER_PREFIX
              + "Scoped_unclaimed_cleanup_failure_retains_actual_work_until_repaired_settlement")
    identities = {
        method + f'(provider: "{provider}", readSession: {read_session})'
        for provider in ("local", "object") for read_session in ("False", "True")}
    return (("artifact-unclaimed-cleanup", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def artifact_capacity_injection_scenarios():
    identities = {
        PAYLOAD_ARTIFACT_CONSUMER_PREFIX + name + f'(provider: "{provider}")'
        for name in (
            "Scoped_capacity_failure_is_real_recoverable_and_does_not_poison_actual_settlement",
            "Ordinary_capacity_shaped_observer_error_still_faults_actual_settlement")
        for provider in ("local", "object")}
    return (("artifact-capacity-injection", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def artifact_direct_verification_scenarios():
    method = (PAYLOAD_ARTIFACT_CONSUMER_PREFIX
              + "Direct_verification_observation_holds_new_and_duplicate_publication_before_acknowledgement")
    identities = {
        method + f'(provider: "{provider}", duplicate: {duplicate})'
        for provider in ("local", "object") for duplicate in ("False", "True")}
    return (("artifact-direct-verification", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def payload_artifact_session_scenarios():
    prefix = PAYLOAD_ARTIFACT_CONSUMER_PREFIX
    identities = {
        prefix + f'Actual_payload_damage_invalidates_copy_and_later_open(provider: "{provider}", truncate: {truncate})'
        for provider in ("local", "object") for truncate in ("False", "True")}
    identities.update(prefix
        + f'Held_native_payload_handle_stays_owned_through_reopen_or_final_settlement(provider: "{provider}", reopen: {reopen})'
        for provider in ("local", "object") for reopen in ("False", "True"))
    identities.update(prefix + f'Foreign_incarnation_cannot_damage_current_payload(provider: "{provider}")'
                      for provider in ("local", "object"))
    identities.update(prefix + method + f'(provider: "{provider}")' for method in (
        "Failed_damage_observer_preserves_bytes_and_faults_final_settlement",
        "Removed_incarnation_cannot_damage_same_digest_replacement",
        "Stale_session_cannot_damage_reopened_payload",
        "Incompatible_open_read_handle_rejects_damage_without_changing_bytes")
        for provider in ("local", "object"))
    identities.update(prefix
        + f'Empty_payload_damage_is_explicit_and_never_false_success(provider: "{provider}", truncate: {truncate})'
        for provider in ("local", "object") for truncate in ("False", "True"))
    identities.add(prefix + "Object_old_epoch_cannot_damage_current_incarnation")
    return (("payload-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_configured_store_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactCompositionTests."
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith(prefix)}
    return (("original-artifact-configured-store", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_object_cleanup_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactFailureTests."
    methods = (
        "Reused_object_receipt_survives_failed_unselected_assembly_cleanup",
        "Unselected_object_cleanup_retains_exact_ownership_and_blocks_retry_until_reclaimed")
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if any(witness == prefix + method or witness.startswith(
            prefix + method + "(") for method in methods)}
    return (("original-artifact-object-cleanup", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_prefix_cleanup_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactFailureTests."
    methods = (
        "Committed_receipts_remain_reconcilable_while_exact_residual_staging_is_reclaimed",
        "Failed_prefix_reclamation_retains_ownership_until_exact_bounded_cleanup",
        "Stop_retains_failed_prefix_ownership_until_reclamation_can_settle")
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if any(witness.startswith(prefix + method + "(") for method in methods)}
    return (("original-artifact-prefix-cleanup", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_failure_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactFailureTests."
    methods = (
        "Storage_failures_remain_distinct_and_sanitized_and_do_not_publish_partial_content",
        "Unexpected_fault_after_visibility_requires_exact_ticket_reconciliation")
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if any(witness.startswith(prefix + method + "(") for method in methods)}
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
        + f'Shared_storage_failure_assertion_rejects_misclassified_denial_and_accepts_original_store(provider: "{provider}")'
        for provider in ("local", "object"))
    return (("original-artifact-failure", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_lifecycle_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactNonCooperationTests."
    methods = (
        "Concurrent_close_waits_for_the_same_physical_guard_release_and_fences_new_copy",
        "Deadline_and_stop_return_while_a_native_io_boundary_holds_provider_state")
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if any(witness.startswith(prefix + method + "(") for method in methods)}
    identities.update(prefix + "Composed_shutdown_cannot_release_store_while_authority_retains_a_reference_query"
                      + f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-lifecycle", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_metadata_bridge_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactMetadataAuthorityTests."
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith(prefix)}
    identities.update(prefix + name for name in (
        "Bridge_binds_exact_evidence_and_keeps_recognized_shared_protection_until_metadata_settlement",
        "Foreign_malformed_expired_and_unrecognized_evidence_cannot_publish_metadata_or_leak_a_guard"))
    return (("original-artifact-metadata-bridge", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_metadata_integration_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactMetadataIntegrationTests."
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith(prefix)}
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
        "Shared_metadata_reference_assertion_rejects_hidden_denial_and_accepts_original_stores"
        f'(provider: "{provider}", metadataProvider: "{metadata}")'
        for provider in ("local", "object") for metadata in ("sqlite", "memory"))
    return (("original-artifact-metadata-integration", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_capability_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactCapabilityTests."
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith(prefix)}
    identities.update(
        prefix + "Complete_capability_profile_accepts_configured_limits_and_keeps_ranges_optional"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-capability", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_authority_scenarios():
    prefix = "Hoard.Artifacts.Tests.ArtifactAuthorityTests."
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith(prefix)}
    identities.update(prefix + name for name in (
        "Shared_admission_retention_and_independent_disposal_use_one_recognized_handle",
        "Missing_reference_authority_denies_deletion_not_shared_reads",
        "Noncooperative_reference_query_retains_exclusion_blocks_admission_and_settles_before_release",
        "Shared_authority_assertion_rejects_repaired_copied_handle_and_accepts_original_authority"))
    return (("original-artifact-authority", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_budget_scenarios():
    methods = {
        "Hoard.Artifacts.Tests.ArtifactBudgetTests."
        "Failed_unclaimed_result_cleanup_blocks_admission_and_stop_until_exact_retry",
        "Hoard.Artifacts.Tests.ArtifactBudgetTests."
        "Cancelled_commit_before_decision_fences_the_ticket_and_cannot_publish_on_retry",
        "Hoard.Artifacts.Tests.ArtifactBudgetTests."
        "Full_transfer_queue_rejects_without_input_io_and_capacity_returns_after_release",
        "Hoard.Artifacts.Tests.ArtifactBudgetTests.Cap_crossing_rejects_excess_before_append_and_capacity_recovers",
        "Hoard.Artifacts.Tests.ArtifactBudgetTests.Total_deadline_includes_shared_authority_contention_before_publication",
        "Hoard.Artifacts.Tests.ArtifactBudgetTests.Cooperative_cancellation_stops_input_without_disposing_borrowed_stream"}
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.split("(", 1)[0] in methods}
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
        "Shared_cap_assertion_rejects_misclassified_limit_and_accepts_original_store"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-budget", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_handoff_scenarios():
    methods = {
        "Hoard.Artifacts.Tests.ArtifactBudgetTests."
        "Cancellation_after_resource_release_cannot_retain_an_already_settled_operation",
        "Hoard.Artifacts.Tests.ArtifactBudgetTests."
        "Cancellation_at_result_handoff_cannot_discard_a_reserved_ticket_or_live_read",
        "Hoard.Artifacts.Tests.ArtifactBudgetTests."
        "Cancellation_before_result_handoff_reclaims_the_unclaimed_ticket_or_read",
        "Hoard.Artifacts.Tests.ArtifactBudgetTests."
        "Undelivered_verified_staging_is_reclaimed_after_ownership_expiry"}
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.split("(", 1)[0] in methods}
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
        "Shared_result_handoff_assertion_rejects_discarded_reservation_and_accepts_original_store"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-handoff", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_cancellation_scenarios():
    method = ("Hoard.Artifacts.Tests.ArtifactBudgetTests."
              "Cancellation_of_an_admitted_commit_cannot_fence_an_externally_renewed_owner")
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.split("(", 1)[0] == method}
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactBudgetTests.Cancellation_after_progress_renewal_fences_the_same_admitted_owner"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactBudgetTests.Cancelled_invalid_or_stale_commit_cannot_fence_the_current_verified_handle"
        f'(provider: "{provider}", alteration: "{alteration}")'
        for provider in ("local", "object") for alteration in ("renewed", "completion", "handle"))
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
        "Shared_cancelled_descriptor_assertion_rejects_abandoned_current_owner_and_accepts_original_store"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-cancellation", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_ownership_scenarios():
    methods = {
        "Hoard.Artifacts.Tests.ArtifactBudgetTests."
        "Producer_and_consumer_inactivity_deadlines_release_cooperative_work_without_closing_borrowed_streams",
        *(f"Hoard.Artifacts.Tests.ArtifactNonCooperationTests.{name}" for name in (
            "Idle_read_expiry_fences_copy_without_touching_the_destination",
            "Noncooperative_source_retains_bounded_ownership_and_blocks_admission_until_real_settlement",
            "Noncooperative_destination_cannot_release_live_read_protection_via_close_or_dispose"))}
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.split("(", 1)[0] in methods}
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
        "Shared_source_ownership_assertion_rejects_optimistic_cleanup_and_accepts_original_store"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-ownership", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_history_scenarios():
    methods = {
        f"Hoard.Artifacts.Tests.ArtifactBudgetTests.{name}" for name in (
            "Local_reclaimed_incarnations_remain_budgeted_until_expiry_without_removing_the_recreated_blob",
            "Reclaimed_identity_history_has_a_finite_budget_and_expiry_restores_new_digest_admission",
            "History_maintenance_bounds_examined_candidates_even_when_none_can_be_retired",
            "History_candidate_pages_resume_past_ineligible_entries_and_preserve_a_faulted_candidate",
            "Expired_ticket_history_restores_write_and_delete_capacity_without_losing_committed_or_removed_identity")}
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.split("(", 1)[0] in methods}
    identities.add(
        "Hoard.Artifacts.Tests.ArtifactBudgetTests."
        "Local_reclaimed_incarnations_remain_budgeted_until_expiry_without_removing_the_recreated_blob")
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactBudgetTests."
        "History_maintenance_bounds_examined_candidates_even_when_none_can_be_retired"
        f'(provider: "{provider}", kind: "{kind}")'
        for provider, kind in (
            ("local", "tickets"), ("object", "tickets"), ("local", "dependencies"), ("object", "dependencies"),
            ("local", "decisions"), ("object", "decisions"), ("local", "reclamation")))
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
        "Shared_history_resume_assertion_rejects_hidden_candidate_failure_and_accepts_original_store"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-history", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_visibility_scenarios():
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith(
            "Hoard.Artifacts.Tests.ArtifactVisibilityTests.")}
    identities.add(
        "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
        "Shared_visibility_assertion_rejects_premature_acknowledgment_and_accepts_original_store")
    return (("original-artifact-visibility", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_reconciliation_scenarios():
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith(
            "Hoard.Artifacts.Tests.ArtifactReconciliationTests.")}
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
        "Shared_receipt_retry_assertion_rejects_foreign_receipt_and_accepts_original_store"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-reconciliation", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_race_scenarios():
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith(
            "Hoard.Artifacts.Tests.ArtifactPublicationRaceTests.")}
    identities.update(
        "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
        "Shared_conflicting_length_assertion_rejects_repaired_forgery_and_accepts_original_store"
        f'(provider: "{provider}")' for provider in ("local", "object"))
    return (("original-artifact-races", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def original_artifact_external_scenarios():
    prefixes = ("Hoard.Artifacts.Tests.ArtifactCrashTests.", "Hoard.Artifacts.Tests.ArtifactNonCooperativeChildTests.",
                "Hoard.Artifacts.Tests.ArtifactTransferProofTests.")
    admission = ("Hoard.Artifacts.Tests.ArtifactAdmissionTests."
                 "Local_root_is_exclusively_owned_across_real_processes_not_a_lock_filename")
    identities = {
        witness for case in category_cases() if case.profile_id == "artifacts"
        for witness in case.witnesses if witness.startswith(prefixes) or witness == admission}
    identities.add(admission)
    prefix = "Hoard.Artifacts.Tests.ArtifactChildOutputTests."
    identities.update((
        *(prefix + "Child_capture_accepts_the_exact_bound_and_rejects_overflow_before_return(line: " + value + ")"
          for value in ("False", "True")),
        prefix + "Line_capture_preserves_the_next_packet_and_distinguishes_empty_line_from_eof",
        prefix + "Capture_bounds_unterminated_packets_and_preserves_empty_completed_output",
    ))
    return (("original-artifact-external", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


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
    runtime_folders = {f"{TESTS}/bin/Release/net10.0", f"{LOGGER}/Smoke/bin/Release/net10.0",
                       f"{TESTS}/{PACKAGE_TEST_OUTPUT}/Release/net10.0",
                       f"{ARTIFACT_CONSUMER}/{PACKAGE_TEST_OUTPUT}/Release/net10.0",
                       f"{METADATA_TESTS}/{METADATA_TEST_OUTPUT}/Release/net10.0",
                       f"{ARTIFACT_TESTS}/{ARTIFACT_TEST_OUTPUT}/Release/net10.0"}
    runtime_folders.add(f"{METADATA_RECOVERY}/bin/Release/net10.0")
    runtime_folders.add(f"{ARTIFACT_RECOVERY}/bin/Release/net10.0")
    runtime_folders.add(f"{ARTIFACT_TRANSFER}/bin/Release/net10.0")
    native_rid = {"x86_64": "linux-x64", "aarch64": "linux-arm64"}.get(observed_environment.get("architecture"))
    if native_rid is None:
        raise evidence.ConformanceError("PrerequisiteMissing")
    def runtime_input(name):
        return (name.endswith((".dll", ".deps.json", ".runtimeconfig.json", ".runtimeconfig.dev.json"))
                and Path(name).parent.as_posix() in runtime_folders) or (
                    name.endswith((".so", ".dylib", ".dll"))
                    and any(name.startswith(folder + "/runtimes/" + native_rid + "/") for folder in runtime_folders))
    # Hash consumed inputs within existing budgets while retaining full-tree safety checks.
    inventory = evidence.proof_manifest(
        candidate, include_file=lambda name: name.endswith("packages.lock.json") or runtime_input(name))
    prefix = candidate.relative_to(run.root).as_posix()
    locks = [f"{prefix}/{name}" for name in inventory if name.endswith("packages.lock.json")]
    runtime = [f"{prefix}/{name}" for name in inventory if runtime_input(name)]
    if not runtime or not locks:
        raise evidence.ConformanceError("EvidenceIncomplete")
    inputs = evidence.capture_profile_inputs(
        run, repository, candidate, profile_id="harness", mode="diagnostic",
        invocation_group_id=str(uuid.uuid4()) if group_id is None else group_id,
        package_versions=[{"packageId": name, "version": "0.1.0"} for name in INPUT_PACKAGES],
        feed="feed/candidate", configuration="stores/candidate.NuGet.Config",
        lock_paths=locks, runtime_paths=runtime, binding_sources=list(binding_sources),
        observed_environment=observed_environment, budgets=BUDGETS, invocation=[
            "sdk-logger-diagnostic", "original-metadata-memory", "original-metadata-sqlite",
            "original-artifact-publication", "original-artifact-read-delete", "original-artifact-evidence",
            "sqlite-recovery-barriers", "local-recovery-barriers", "paced-artifact-transfers",
            "artifact-noncooperation", "original-artifact-external", "original-artifact-races",
            "original-artifact-reconciliation", "original-artifact-visibility", "original-artifact-history",
            "original-artifact-ownership", "original-artifact-cancellation", "original-artifact-handoff",
            "original-artifact-budget", "original-artifact-authority", "original-artifact-capability",
            "original-artifact-metadata-integration", "original-artifact-metadata-bridge",
            "original-artifact-lifecycle", "original-artifact-failure", "original-artifact-prefix-cleanup",
            "original-artifact-object-cleanup", "original-artifact-configured-store", "original-artifact-authority-ownership",
            "local-artifact-session", "object-artifact-session", "configured-artifact-session", "payload-artifact-session",
            "original-artifact-observations", "original-artifact-damaged-read", "original-artifact-read-races",
            "original-artifact-detection", "original-artifact-quarantine-reopen", "original-artifact-validation",
            "original-artifact-recovery-pages", "original-artifact-recovery-races",
            "original-artifact-recovery-reopen", "original-artifact-admission",
            "original-artifact-deletion-settlement", "artifact-direct-verification", "artifact-capacity-injection",
            "artifact-unclaimed-cleanup", "artifact-synchronous-storage", "full-artifact-binding", "full-metadata-binding",
            "actual-authority-integration", *(scenario[0] for scenario in category_mutation_scenarios()),
            *(scenario[0] for scenario in original_observation_scenarios())],
        baseline_sha256=seal_sha, ci_revision=ci_revision)
    if (inputs["sourceManifest"] != sources
            or any(inputs[key] != value for key, value in identity.items())):
        raise evidence.ConformanceError("InputChanged")
    return inputs


def original_observation_scenarios():
    artifacts = tuple('Hoard.Artifacts.Tests.ArtifactPublicationTests.'
                      f'Empty_content_and_true_absence_are_distinct(provider: "{provider}")'
                      for provider in ("local", "object"))
    contracts = tuple("Hoard.Artifacts.Tests.ArtifactValueTests." + method for method in (
        "Expectations_and_checksums_copy_input_and_reject_each_bound",
        "Public_diagnostic_formatting_is_redacted_and_contract_members_are_get_only"))
    return (
        *((f"observed-original-metadata-{provider}", ORIGINAL_METADATA_WITNESSES, "None", "Passed", 0, "None")
          for provider in ("memory", "sqlite")),
        ("observed-original-artifact-instances", artifacts, "None", "Passed", 0, "None"),
        *((f"observed-original-contract-{provider}", contracts, "None", "Passed", 0, "None")
          for provider in ("local", "object")),
    )


def original_observation_inputs(candidate, root):
    result = {}
    for category, provider, _, package in CATEGORY_BINDING_SLOTS:
        metadata = category == "metadata"
        folder, output = (METADATA_TESTS, METADATA_TEST_OUTPUT) if metadata else (ARTIFACT_TESTS, ARTIFACT_TEST_OUTPUT)
        runtime = candidate / folder / output / "Release/net10.0"
        assembly = "Hoard.Metadata.Tests" if metadata else "Hoard.Artifacts.Tests"
        host = "Hoard.Fixtures." + ("Metadata" if metadata else "Artifacts") + ".HostAdapters"
        roles = ({"owner": host, "store": package, "schema": package, "authority": None, "controls": host}
                 if metadata else
                 {"owner": None, "store": package, "validator": package, "maintenance": package,
                  "lifetime": package, "authority": host, "controls": package, "contract": "Hoard.Abstractions"})
        try:
            result[provider] = {
                role: ((runtime / ((package_id or assembly) + ".dll")).relative_to(root).as_posix(), package_id)
                for role, package_id in roles.items()}
        except ValueError as error:
            raise evidence.ConformanceError("InputChanged") from error
    return result


def validate_original_observations(ingested):
    for witness in ingested["witnesses"]:
        execution = witness["executionId"]
        policy = original_witness_policy(witness["testIdentity"])
        observations = ingested["originalObservations"].get(execution, ())
        if (policy is None or len(observations) != 1 or ingested["sessionOrigins"].get(execution)
                or observations[0]["kind"] != policy[1] or observations[0]["parentObservationId"] is not None
                or observations[0]["operation"] != ("contract" if policy[1] == "loaded-contract" else "create")):
            raise evidence.ConformanceError("WitnessMissing")


def test_attempt(run, inputs, candidate, scenario):
    name, identities, expected_code, expected_status, expected_exit, failure_kind = scenario
    original_observations = name.startswith("observed-original-")
    if original_observations and scenario not in original_observation_scenarios():
        raise evidence.ConformanceError("WitnessMissing")
    if (name == "full-metadata-binding"
            or any(identity.startswith(FULL_METADATA_CONSUMER_PREFIX) for identity in identities)):
        if scenario not in full_metadata_binding_scenarios():
            raise evidence.ConformanceError("WitnessMissing")
    if (name in ("local-artifact-session", "object-artifact-session", "configured-artifact-session",
                 "payload-artifact-session", "artifact-direct-verification", "artifact-capacity-injection",
                 "artifact-unclaimed-cleanup", "artifact-synchronous-storage", "full-artifact-binding",
                 "actual-authority-integration") or name.startswith("category-mutation-")
            or any(identity.startswith(ARTIFACT_CONSUMER_PREFIXES) for identity in identities)):
        if scenario not in (*local_artifact_session_scenarios(), *object_artifact_session_scenarios(),
                            *configured_artifact_session_scenarios(), *payload_artifact_session_scenarios(),
                            *artifact_direct_verification_scenarios(), *artifact_capacity_injection_scenarios(),
                            *artifact_unclaimed_cleanup_scenarios(), *artifact_synchronous_storage_scenarios(),
                            *full_artifact_binding_scenarios(), *actual_authority_integration_scenarios(),
                            *category_mutation_scenarios()):
            raise evidence.ConformanceError("WitnessMissing")
    original_metadata = name.startswith(("original-metadata-", "observed-original-metadata-"))
    original_artifacts = name.startswith(("original-artifact-", "observed-original-artifact-", "observed-original-contract-"))
    original_tests = original_metadata or original_artifacts
    metadata_provider = None
    if original_metadata:
        if not original_observations and scenario not in original_metadata_scenarios():
            raise evidence.ConformanceError("WitnessMissing")
        metadata_provider = name.rsplit("-", 1)[1]
    if original_artifacts and not original_observations and scenario not in (
            *original_artifact_publication_scenarios(), *original_artifact_read_delete_scenarios(),
            *original_artifact_evidence_scenarios(), *original_artifact_damaged_read_scenarios(),
            *original_artifact_read_race_scenarios(),
            *original_artifact_detection_scenarios(),
            *original_artifact_quarantine_reopen_scenarios(),
            *original_artifact_validation_scenarios(),
            *original_artifact_recovery_pages_scenarios(),
            *original_artifact_recovery_race_scenarios(),
            *original_artifact_recovery_reopen_scenarios(),
            *original_artifact_admission_scenarios(),
            *original_artifact_deletion_settlement_scenarios(),
            *original_artifact_external_scenarios(),
            *original_artifact_race_scenarios(), *original_artifact_reconciliation_scenarios(),
            *original_artifact_visibility_scenarios(), *original_artifact_history_scenarios(),
            *original_artifact_ownership_scenarios(), *original_artifact_cancellation_scenarios(),
            *original_artifact_handoff_scenarios(), *original_artifact_budget_scenarios(),
            *original_artifact_authority_scenarios(), *original_artifact_capability_scenarios(),
            *original_artifact_metadata_integration_scenarios(), *original_artifact_metadata_bridge_scenarios(),
            *original_artifact_lifecycle_scenarios(), *original_artifact_failure_scenarios(),
            *original_artifact_prefix_cleanup_scenarios(), *original_artifact_object_cleanup_scenarios(),
            *original_artifact_configured_store_scenarios(), *artifact_authority_ownership_scenarios(),
            *artifact_observation_scenarios()):
        raise evidence.ConformanceError("WitnessMissing")
    binding_tests = all(identity.startswith(BINDING_TEST_PREFIXES) for identity in identities)
    sqlite_tests = (
        name in ("full-metadata-binding", "actual-authority-integration")
        or name.startswith("category-mutation-metadata-") or metadata_provider == "sqlite"
        or any(identity.startswith((SQLITE_BINDING_PREFIX, SQLITE_MECHANISM_PREFIX)) for identity in identities))
    source_tests = original_tests or all(
        identity.startswith("Hoard.Conformance.Tests.") for identity in identities) or binding_tests
    smoke_tests = all(identity.startswith(SMOKE) for identity in identities)
    package_tests = binding_tests or any(identity.startswith(PACKAGE_TEST_PREFIX) for identity in identities)
    if (source_tests == smoke_tests
            or package_tests and not binding_tests
            and not all(identity.startswith(PACKAGE_TEST_PREFIX) for identity in identities)):
        raise evidence.ConformanceError("WitnessMissing")
    if original_artifacts:
        selected_methods = {identity.split("(")[0] for identity in identities}
        if any(witness.split("(")[0] in selected_methods and witness not in identities
               for case in category_cases() if case.profile_id == "artifacts"
               for witness in case.witnesses):
            raise evidence.ConformanceError("WitnessMissing")
        folder, output, assembly_name = ARTIFACT_TESTS, ARTIFACT_TEST_OUTPUT, "Hoard.Artifacts.Tests.dll"
    elif original_metadata:
        folder, output, assembly_name = METADATA_TESTS, METADATA_TEST_OUTPUT, "Hoard.Metadata.Tests.dll"
    elif all(identity.startswith((*ARTIFACT_CONSUMER_PREFIXES, FULL_METADATA_CONSUMER_PREFIX)) for identity in identities):
        folder, output, assembly_name = ARTIFACT_CONSUMER, PACKAGE_TEST_OUTPUT, "Hoard.Fixtures.Conformance.Consumer.dll"
    else:
        output = PACKAGE_TEST_OUTPUT if package_tests else "bin"
        folder = TESTS if source_tests else LOGGER + "/Smoke"
        assembly_name = "Hoard.Conformance.Tests.dll" if source_tests else "Smoke.dll"
    assembly = candidate / folder / output / "Release/net10.0" / assembly_name
    if sqlite_tests:
        require_sqlite_environment(inputs, assembly, run.root)
    assembly_path = assembly.relative_to(run.root).as_posix()
    package_id = "Hoard.Testing.Conformance" if source_tests or name == "origin-output" else "Hoard.Conformance.TestLogger"
    package = next(package for package in inputs["packages"] if package["packageId"] == package_id)
    attempt_id = str(uuid.uuid4())
    origin_inputs = None
    original_inputs = None
    original_cases = {}
    expected = {identity: ("origin-probe" if name == "origin-output" else "none", "none") for identity in identities}
    if original_observations:
        provider = name.rsplit("-", 1)[1] if original_metadata or "-contract-" in name else None
        expected = {
            identity: (provider if provider is not None else
                       "local" if '(provider: "local")' in identity else "object", "none")
            for identity in identities}
        original_inputs = original_observation_inputs(candidate, run.root)
        if not {binding for binding, _ in expected.values()} <= {item["bindingId"] for item in inputs["bindings"]}:
            raise evidence.ConformanceError("BindingInvalid")
        original_cases = {
            identity: category_runtime_cases(original_witness_policy(identity)[0], binding)[identity]
            for identity, (binding, _) in expected.items()}
    if name == "full-artifact-binding":
        expected = {
            identity: ("fixture.artifact." + provider, "none")
            for provider in ("local", "object") for identity in identities if f'(provider: "{provider}"' in identity}
        if set(expected) != set(identities):
            raise evidence.ConformanceError("WitnessMissing")
    if name == "full-metadata-binding":
        expected = {
            identity: ("fixture.metadata." + provider, "none")
            for provider in ("memory", "sqlite") for identity in identities if f'(provider: "{provider}"' in identity}
        if set(expected) != set(identities):
            raise evidence.ConformanceError("WitnessMissing")
    manifest = {
        "schemaVersion": 1, "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "attemptId": attempt_id, "attemptSequence": 1, "purpose": "execution",
        "inputSha256": evidence.digest(inputs),
        "runInputsPath": "proofs/original-run-inputs.json" if original_observations else "proofs/run-inputs.json",
        "assemblies": [{"id": "test-assembly", "path": assembly_path,
                        "sha256": inputs["runtimeAssemblies"][assembly_path]}],
        "packages": [{"id": package_id, "path": f"feed/candidate/{package_id}.0.1.0.nupkg",
                      "sha256": package["sha256"]}],
        "expected": [{
            "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
            "assemblyId": "test-assembly", "packageId": package_id,
            "bindingId": binding, "matrixId": matrix,
            "assertionSymbol": (
                "Hoard.Testing.Conformance.Metadata.MetadataTimeAssertions.TicketExpiryAndRollbackAsync"
                if name == "category-mutation-metadata-faulty" else
                "Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions.PrivateStagingAsync"
                if name == "category-mutation-artifacts-faulty" else ASSERTION if name == "assertion" else None),
            "caseId": original_cases[identity] if original_observations else
                name if original_tests or name in ("full-artifact-binding", "full-metadata-binding") else "runtime",
        } for identity, (binding, matrix) in expected.items()],
    }
    if original_observations or name in ("full-artifact-binding", "full-metadata-binding"):
        if original_observations:
            component_assignments = {binding: original_inputs[binding] for binding, _ in expected.values()}
        else:
            origin_inputs = (artifact_origin_inputs(candidate, run.root) if name == "full-artifact-binding"
                             else metadata_origin_inputs(candidate, run.root))
            component_assignments = origin_inputs
        component_paths = {path for roles in component_assignments.values() for path, _ in roles.values()}
        component_paths.discard(assembly_path)
        for index, path in enumerate(sorted(component_paths)):
            sha256 = inputs["runtimeAssemblies"].get(path)
            if sha256 is None:
                raise evidence.ConformanceError("InputChanged")
            manifest["assemblies"].append({"id": f"binding-component-{index}", "path": path, "sha256": sha256})
    discovery_manifest = {**manifest, "purpose": "discovery", "attemptId": str(uuid.uuid4())}
    runtime_options = {"metadata_provider": metadata_provider} if original_metadata else {}
    if original_observations:
        runtime_options["original_observations"] = True
    if name == "full-artifact-binding" or name.startswith("category-mutation-artifacts-"):
        packages = {item["packageId"]: item["sha256"] for item in inputs["packages"]}
        required = ("Hoard.Fixtures.Artifacts.Local", "Hoard.Fixtures.Artifacts.ObjectSemantics")
        if any(package not in packages for package in required):
            raise evidence.ConformanceError("PrerequisiteMissing")
        runtime_options["artifact_packages"] = {package: packages[package] for package in required}
    if name == "full-metadata-binding" or name.startswith("category-mutation-metadata-"):
        packages = {item["packageId"]: item["sha256"] for item in inputs["packages"]}
        required = ("Hoard.Fixtures.Metadata.Memory", "Hoard.Fixtures.Metadata.Sqlite")
        if any(package not in packages for package in required):
            raise evidence.ConformanceError("PrerequisiteMissing")
        runtime_options["metadata_packages"] = {package: packages[package] for package in required}
    if name == "original-artifact-external":
        runner = candidate / ARTIFACT_RECOVERY / "bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll"
        if inputs["runtimeAssemblies"].get(runner.relative_to(run.root).as_posix()) != evidence.file_sha256(runner):
            raise evidence.ConformanceError("InputChanged")
        runtime_options["artifact_runner"] = runner
    discovery_result, discovery_output, discovery_transport = runtime_command(
        run, assembly, discovery_manifest, **runtime_options)
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
    result, output, transport = runtime_command(run, assembly, manifest, **runtime_options)
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
    if name == "origin-output":
        origin_inputs = {"origin-probe": {role: (assembly_path, None) for role in (
            "factory", "session", "store", "schema", "authority", "faults")}}
    ingested = evidence.ingest_runtime_attempt(
        inputs=inputs, expected_tests=expected,
        witnesses_data=read_bounded(output / "witnesses.jsonl", 1024 * 1024), proofs=proof_data,
        completion_data=read_bounded(output / "completion.json", 64 * 1024),
        **({"origin_inputs": origin_inputs} if origin_inputs is not None else {}),
        **({"original_inputs": original_inputs} if original_inputs is not None else {}), **transport)
    validate_observation(ingested, result, identities, expected_code, expected_status, expected_exit,
                         proof_data, failure_kind)
    if name == "origin-output" and (
            len(ingested["sessionOrigins"]) != 1
            or any(len(origins) != 1 for origins in ingested["sessionOrigins"].values())):
        raise evidence.ConformanceError("WitnessMissing")
    if name in ("full-artifact-binding", "full-metadata-binding"):
        reopen = FULL_ARTIFACT_CONSUMER_PREFIX + "Observed_full_binding_reopens_actual_components_and_fences_stale_controls"
        counts = (full_metadata_binding_origin_counts() if name == "full-metadata-binding" else
                  {identity: 2 if identity.split("(")[0] == reopen else 1 for identity in identities})
        validate_full_binding_origins(ingested, inputs, counts)
    if original_observations:
        validate_original_observations(ingested)
    return {"code": expected_code, "tests": len(identities),
            "discoverySha256": evidence.file_sha256(discovery_output / "completion.json"),
            "completionSha256": evidence.file_sha256(output / "completion.json")}


def runtime_command(run, assembly, manifest, *, metadata_provider=None, artifact_runner=None,
                    artifact_packages=None, metadata_packages=None, original_observations=False):
    attempt_id = manifest["attemptId"]
    identities = tuple(entry["testIdentity"] for entry in manifest["expected"])
    if manifest["purpose"] not in ("discovery", "execution"):
        raise evidence.ConformanceError()
    discovery = manifest["purpose"] == "discovery"
    origin_environment = ""
    if artifact_packages is not None or metadata_packages is not None:
        if artifact_packages is not None and metadata_packages is not None:
            raise evidence.ConformanceError("WitnessMissing")
        required = {
            "Hoard.Fixtures.Artifacts.Local": "HOARD_ARTIFACT_LOCAL_PACKAGE_SHA256",
            "Hoard.Fixtures.Artifacts.ObjectSemantics": "HOARD_ARTIFACT_OBJECT_PACKAGE_SHA256",
        } if artifact_packages is not None else {
            "Hoard.Fixtures.Metadata.Memory": "HOARD_METADATA_MEMORY_PACKAGE_SHA256",
            "Hoard.Fixtures.Metadata.Sqlite": "HOARD_METADATA_SQLITE_PACKAGE_SHA256",
        }
        packages = artifact_packages if artifact_packages is not None else metadata_packages
        family = "artifacts" if artifact_packages is not None else "metadata"
        scenarios = (
            *(full_artifact_binding_scenarios() if artifact_packages is not None
              else full_metadata_binding_scenarios()),
            *(scenario for scenario in category_mutation_scenarios()
              if scenario[0].startswith(f"category-mutation-{family}-")),
        )
        if (metadata_provider is not None or artifact_runner is not None
                or assembly.name != "Hoard.Fixtures.Conformance.Consumer.dll"
                or not any(tuple(sorted(identities)) == scenario[1] for scenario in scenarios)
                or not isinstance(packages, dict) or set(packages) != set(required)):
            raise evidence.ConformanceError("WitnessMissing")
        variables = {}
        for package, variable in required.items():
            sha256 = packages[package]
            if not isinstance(sha256, str) or re.fullmatch("[0-9a-f]{64}", sha256) is None:
                raise evidence.ConformanceError("InputChanged")
            archive = run.root / "feed/candidate" / (package + ".0.1.0.nupkg")
            no_symlinks(archive)
            if not archive.is_file() or evidence.file_sha256(archive) != sha256:
                raise evidence.ConformanceError("InputChanged")
            variables[variable] = sha256
        variables["HOARD_ORIGIN_RUN_ID"] = manifest["runId"]
        origin_environment = ("<EnvironmentVariables>" + "".join(
            f"<{key}>{value}</{key}>" for key, value in variables.items()) + "</EnvironmentVariables>")
    if metadata_provider is not None:
        if metadata_provider not in ("memory", "sqlite") or assembly.name != "Hoard.Metadata.Tests.dll":
            raise evidence.ConformanceError("WitnessMissing")
        origin_environment = (
            "<EnvironmentVariables>"
            f"<HOARD_METADATA_PROVIDER>{metadata_provider}</HOARD_METADATA_PROVIDER>"
            "</EnvironmentVariables>")
    if artifact_runner is not None:
        allowed = set(original_artifact_external_scenarios()[0][1])
        if (metadata_provider is not None or assembly.name != "Hoard.Artifacts.Tests.dll"
                or set(identities) != allowed):
            raise evidence.ConformanceError("WitnessMissing")
        if (not isinstance(artifact_runner, Path) or not artifact_runner.is_relative_to(run.root)
                or ".." in artifact_runner.parts or artifact_runner.name != "Hoard.Fixtures.Artifacts.CrashRunner.dll"):
            raise evidence.ConformanceError("InputChanged")
        transfer_proofs = run.root / "proofs/artifact-transfers"
        no_symlinks(artifact_runner)
        no_symlinks(transfer_proofs)
        if not artifact_runner.is_file() or not transfer_proofs.is_dir():
            raise evidence.ConformanceError("EvidenceIncomplete")
        capture = run.root / "stores" / ("original-artifact-" + attempt_id)
        no_symlinks(capture)
        capture.mkdir(mode=0o700)
        variables = {
            "HOARD_ARTIFACT_CRASH_RUNNER": str(artifact_runner),
            "HOARD_ARTIFACT_CRASH_PROOFS": str(capture),
            "HOARD_ARTIFACT_TRANSFER_PROOFS": str(transfer_proofs),
            "HOARD_ARTIFACT_RUN_ID": manifest["runId"],
        }
        origin_environment = ("<EnvironmentVariables>" + "".join(
            f"<{key}>{escape(value)}</{key}>" for key, value in variables.items()) + "</EnvironmentVariables>")
    if any(entry["fullyQualifiedName"] == SMOKE + "OriginOutput" for entry in manifest["expected"]):
        package = next((item for item in manifest["packages"] if item["id"] == "Hoard.Testing.Conformance"), None)
        if package is None:
            raise evidence.ConformanceError("PrerequisiteMissing")
        origin_environment = (
            "<EnvironmentVariables>"
            f'<HOARD_ORIGIN_RUN_ID>{escape(manifest["runId"])}</HOARD_ORIGIN_RUN_ID>'
            f'<HOARD_ORIGIN_PACKAGE_SHA256>{escape(package["sha256"])}</HOARD_ORIGIN_PACKAGE_SHA256>'
            "</EnvironmentVariables>")
    if original_observations:
        policies = tuple(original_witness_policy(identity) for identity in identities)
        if (not identities or len(set(identities)) != len(identities) or any(policy is None for policy in policies)
                or metadata_packages is not None or artifact_packages is not None
                or any(assembly.name != ("Hoard.Metadata.Tests.dll" if policy[0] == "metadata"
                                        else "Hoard.Artifacts.Tests.dll") for policy in policies)):
            raise evidence.ConformanceError("WitnessMissing")
        if any(entry["bindingId"] not in (("sqlite", "memory") if policy[0] == "metadata" else ("local", "object"))
               for entry, policy in zip(manifest["expected"], policies)):
            raise evidence.ConformanceError("BindingInvalid")
        context = evidence.canonical_bytes({
            "schemaVersion": 1, "runId": manifest["runId"],
            "cases": {entry["testIdentity"]: {"caseId": entry["caseId"], "bindingId": entry["bindingId"]}
                      for entry in manifest["expected"]}})
        if len(context) > 64 * 1024:
            raise evidence.ConformanceError("OutputLimitExceeded")
        variable = "<HOARD_ORIGINAL_CONTEXT>" + base64.b64encode(context).decode() + "</HOARD_ORIGINAL_CONTEXT>"
        origin_environment = (origin_environment.removesuffix("</EnvironmentVariables>") + variable
                              + "</EnvironmentVariables>" if origin_environment
                              else "<EnvironmentVariables>" + variable + "</EnvironmentVariables>")
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
            ("src/Hoard.Core", "Hoard.Core"), ("src/Hoard.Hosting", "Hoard.Hosting"),
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
        adapter_project = candidate / "tests/fixtures/metadata/HostAdapters/HostAdapters.csproj"
        adapter_lock, adapter_record = prepare_project_lock(adapter_project, candidate, feed, "candidate")
        build(run, adapter_project, config, "metadata-host-package", lock=adapter_lock, feed=feed,
              package_id="Hoard.Fixtures.Metadata.HostAdapters")
        if adapter_record is not None:
            verify_project_lock(adapter_record, candidate, feed)
            write_new(run.root / "proofs/metadata-host-lock-derivation.json", evidence.canonical_bytes(adapter_record))
        recovery_project = candidate / METADATA_RECOVERY / "CrashRunner.csproj"
        recovery_lock, recovery_record = prepare_project_lock(recovery_project, candidate, feed, "candidate")
        build(run, recovery_project, config, "metadata-recovery", lock=recovery_lock)
        if recovery_record is not None:
            verify_project_lock(recovery_record, candidate, feed)
            write_new(run.root / "proofs/metadata-recovery-lock-derivation.json",
                      evidence.canonical_bytes(recovery_record))
        verify_runtime_packages(candidate / METADATA_RECOVERY / "bin/Release/net10.0",
                                feed, METADATA_RECOVERY_PACKAGES)
        artifact_records = []
        for name in ("Local", "ObjectSemantics", "HostAdapters"):
            project = candidate / f"tests/fixtures/artifacts/{name}/{name}.csproj"
            artifact_lock, artifact_record = prepare_project_lock(project, candidate, feed, "candidate")
            build(run, project, config, "artifact-package", lock=artifact_lock, feed=feed,
                  package_id="Hoard.Fixtures.Artifacts." + name)
            if artifact_record is not None:
                verify_project_lock(artifact_record, candidate, feed)
                artifact_records.append(artifact_record)
                write_new(run.root / f"proofs/artifact-{name}-lock-derivation.json",
                          evidence.canonical_bytes(artifact_record))
        artifact_recovery_project = candidate / ARTIFACT_RECOVERY / "CrashRunner.csproj"
        artifact_recovery_lock, artifact_recovery_record = prepare_project_lock(
            artifact_recovery_project, candidate, feed, "candidate")
        build(run, artifact_recovery_project, config, "artifact-recovery", lock=artifact_recovery_lock)
        if artifact_recovery_record is not None:
            verify_project_lock(artifact_recovery_record, candidate, feed)
            write_new(run.root / "proofs/artifact-recovery-lock-derivation.json",
                      evidence.canonical_bytes(artifact_recovery_record))
        verify_runtime_packages(candidate / ARTIFACT_RECOVERY / "bin/Release/net10.0",
                                feed, ARTIFACT_RECOVERY_PACKAGES)
        artifact_transfer_project = candidate / ARTIFACT_TRANSFER / "TransferRunner.csproj"
        artifact_transfer_lock, artifact_transfer_record = prepare_project_lock(
            artifact_transfer_project, candidate, feed, "candidate")
        build(run, artifact_transfer_project, config, "artifact-transfers", lock=artifact_transfer_lock)
        if artifact_transfer_record is not None:
            verify_project_lock(artifact_transfer_record, candidate, feed)
            write_new(run.root / "proofs/artifact-transfer-lock-derivation.json",
                      evidence.canonical_bytes(artifact_transfer_record))
        verify_runtime_packages(candidate / ARTIFACT_TRANSFER / "bin/Release/net10.0",
                                feed, ARTIFACT_RECOVERY_PACKAGES)
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
        wrapper_lock, wrapper_receipt = prepare_package_consumer_lock(
            candidate, feed, project=METADATA_TESTS, local_packages=METADATA_PACKAGES)
        verify_package_consumer_lock(candidate, feed, wrapper_lock, wrapper_receipt, project=METADATA_TESTS)
        write_new(run.root / "proofs/metadata-wrapper-lock-derivation.json", evidence.canonical_bytes(wrapper_receipt))
        build(run, candidate / METADATA_TESTS / "Hoard.Metadata.Tests.csproj", config,
              "metadata-wrapper-locked-replay", lock=wrapper_lock, properties=(
                  "-p:MetadataPackageAcceptance=true", "-p:BaseOutputPath=" + METADATA_TEST_OUTPUT + "/"))
        metadata_wrapper_runtime(candidate, feed)
        artifact_wrapper_lock, artifact_wrapper_receipt = prepare_package_consumer_lock(
            candidate, feed, project=ARTIFACT_TESTS, local_packages=ARTIFACT_PACKAGES)
        verify_package_consumer_lock(
            candidate, feed, artifact_wrapper_lock, artifact_wrapper_receipt, project=ARTIFACT_TESTS)
        write_new(run.root / "proofs/artifact-wrapper-lock-derivation.json",
                  evidence.canonical_bytes(artifact_wrapper_receipt))
        build(run, candidate / ARTIFACT_TESTS / "Hoard.Artifacts.Tests.csproj", config,
              "artifact-wrapper-locked-replay", lock=artifact_wrapper_lock, properties=(
                  "-p:ArtifactPackageAcceptance=true", "-p:BaseOutputPath=" + ARTIFACT_TEST_OUTPUT + "/"))
        artifact_wrapper_runtime(candidate, feed)
        build_artifact_assertion_consumer(run, candidate, config, feed)
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
        for declaration in (*artifact_binding_declarations(feed), *metadata_binding_declarations(feed)):
            path = "stores/" + declaration["bindingId"] + ".json"
            write_new(run.root / path, json.dumps(declaration, separators=(",", ":"), ensure_ascii=True).encode("ascii"))
            binding_sources.append({"path": path, "adapterId": declaration["bindingId"]})
        print(json.dumps({"qualification": False, "phase": "sqlite-environment-admission"}), flush=True)
        admitted_environment = environment(run, candidate=candidate)
        print(json.dumps({"qualification": False, "phase": "runtime-input-capture"}), flush=True)
        inputs = make_inputs(run, repository, candidate, sources, admitted_environment, identity, seal_sha,
                             ci_revision=ci_revision, binding_sources=binding_sources)
        catalog_bindings = {declaration: binding for _, binding, declaration, _ in CATEGORY_BINDING_SLOTS}
        original_binding_sources = [
            {**source, **({"catalogBindingId": catalog_bindings[source["adapterId"]]}
                         if source["adapterId"] in catalog_bindings else {})}
            for source in binding_sources]
        original_inputs = make_inputs(
            run, repository, candidate, sources, admitted_environment, identity, seal_sha,
            group_id=inputs["invocationGroupId"], ci_revision=ci_revision, binding_sources=original_binding_sources)
        for name in sources:
            (candidate / name).chmod(0o400)
        for name in inputs["runtimeAssemblies"]:
            (run.root / name).chmod(0o400)
        for package in feed.glob("*.nupkg"):
            package.chmod(0o400)
        write_new(run.root / "proofs/run-inputs.json", evidence.canonical_bytes(inputs))
        write_new(run.root / "proofs/original-run-inputs.json", evidence.canonical_bytes(original_inputs))
        write_new(run.root / "runtime-owner.json", evidence.canonical_bytes({
            "schemaVersion": 1, "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
            "rootId": run.root_id, "rootPathSha256": hashlib.sha256(str(run.root).encode()).hexdigest(),
        }))
        observations = []
        for scenario in (*SCENARIOS, *original_metadata_scenarios(), *original_artifact_publication_scenarios(),
                         *original_artifact_read_delete_scenarios(), *original_artifact_evidence_scenarios()):
            print(json.dumps({"qualification": False, "phase": "runtime-tests",
                              "completedScenarios": len(observations)}), flush=True)
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "native-noncooperation"}), flush=True)
        native_noncooperation = sqlite_noncooperation(run, inputs, candidate)
        print(json.dumps({"qualification": False, "phase": "metadata-recovery"}), flush=True)
        metadata_recovery = metadata_recovery_diagnostics(run, inputs, candidate)
        print(json.dumps({"qualification": False, "phase": "artifact-recovery"}), flush=True)
        artifact_recovery = artifact_recovery_diagnostics(run, inputs, candidate)
        print(json.dumps({"qualification": False, "phase": "artifact-transfers"}), flush=True)
        artifact_transfers = artifact_transfer_diagnostics(run, inputs, candidate)
        print(json.dumps({"qualification": False, "phase": "artifact-noncooperation"}), flush=True)
        artifact_noncooperative = artifact_noncooperation_diagnostics(run, inputs, candidate)
        print(json.dumps({"qualification": False, "phase": "original-artifact-external"}), flush=True)
        for scenario in original_artifact_external_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-races"}), flush=True)
        for scenario in original_artifact_race_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-reconciliation"}), flush=True)
        for scenario in original_artifact_reconciliation_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-visibility"}), flush=True)
        for scenario in original_artifact_visibility_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-history"}), flush=True)
        for scenario in original_artifact_history_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-ownership"}), flush=True)
        for scenario in original_artifact_ownership_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-cancellation"}), flush=True)
        for scenario in original_artifact_cancellation_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-handoff"}), flush=True)
        for scenario in original_artifact_handoff_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-budget"}), flush=True)
        for scenario in original_artifact_budget_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-authority"}), flush=True)
        for scenario in original_artifact_authority_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-capability"}), flush=True)
        for scenario in original_artifact_capability_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-metadata-integration"}), flush=True)
        for scenario in original_artifact_metadata_integration_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-metadata-bridge"}), flush=True)
        for scenario in original_artifact_metadata_bridge_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-lifecycle"}), flush=True)
        for scenario in original_artifact_lifecycle_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-failure"}), flush=True)
        for scenario in original_artifact_failure_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-prefix-cleanup"}), flush=True)
        for scenario in original_artifact_prefix_cleanup_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-object-cleanup"}), flush=True)
        for scenario in original_artifact_object_cleanup_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-configured-store"}), flush=True)
        for scenario in original_artifact_configured_store_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "artifact-authority-ownership"}), flush=True)
        for scenario in artifact_authority_ownership_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "local-artifact-session"}), flush=True)
        for scenario in local_artifact_session_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "object-artifact-session"}), flush=True)
        for scenario in object_artifact_session_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "configured-artifact-session"}), flush=True)
        for scenario in configured_artifact_session_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "payload-artifact-session"}), flush=True)
        for scenario in payload_artifact_session_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "artifact-observations"}), flush=True)
        for scenario in artifact_observation_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-damaged-read"}), flush=True)
        for scenario in original_artifact_damaged_read_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-read-races"}), flush=True)
        for scenario in original_artifact_read_race_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-detection"}), flush=True)
        for scenario in original_artifact_detection_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-quarantine-reopen"}), flush=True)
        for scenario in original_artifact_quarantine_reopen_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-validation"}), flush=True)
        for scenario in original_artifact_validation_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-recovery-pages"}), flush=True)
        for scenario in original_artifact_recovery_pages_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-recovery-races"}), flush=True)
        for scenario in original_artifact_recovery_race_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-recovery-reopen"}), flush=True)
        for scenario in original_artifact_recovery_reopen_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-admission"}), flush=True)
        for scenario in original_artifact_admission_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-artifact-deletion-settlement"}), flush=True)
        for scenario in original_artifact_deletion_settlement_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "artifact-direct-verification"}), flush=True)
        for scenario in artifact_direct_verification_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "artifact-capacity-injection"}), flush=True)
        for scenario in artifact_capacity_injection_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "artifact-unclaimed-cleanup"}), flush=True)
        for scenario in artifact_unclaimed_cleanup_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "artifact-synchronous-storage"}), flush=True)
        for scenario in artifact_synchronous_storage_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "full-artifact-binding"}), flush=True)
        for scenario in full_artifact_binding_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "full-metadata-binding"}), flush=True)
        for scenario in full_metadata_binding_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "actual-authority-integration"}), flush=True)
        for scenario in actual_authority_integration_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "category-mutations"}), flush=True)
        for scenario in category_mutation_scenarios():
            observations.append(test_attempt(run, inputs, candidate, scenario))
        print(json.dumps({"qualification": False, "phase": "original-wrapper-observations"}), flush=True)
        for scenario in original_observation_scenarios():
            observations.append(test_attempt(run, original_inputs, candidate, scenario))
        post_environment = environment(run, phase="completion", candidate=candidate)
        post_sources = evidence.source_manifest(repository)
        post_identity = evidence.source_identity(repository, ci_revision=ci_revision)
        if post_sources != sources or post_identity != identity:
            raise evidence.ConformanceError("InputChanged")
        evidence.verify_snapshot(candidate, sources)
        if lock_record is not None:
            verify_project_lock(lock_record, candidate, feed)
        if recovery_record is not None:
            verify_project_lock(recovery_record, candidate, feed)
        if artifact_recovery_record is not None:
            verify_project_lock(artifact_recovery_record, candidate, feed)
        if artifact_transfer_record is not None:
            verify_project_lock(artifact_transfer_record, candidate, feed)
        if memory_record is not None:
            verify_project_lock(memory_record, candidate, feed)
        if binding_record is not None:
            verify_project_lock(binding_record, candidate, feed)
        if adapter_record is not None:
            verify_project_lock(adapter_record, candidate, feed)
        for artifact_record in artifact_records:
            verify_project_lock(artifact_record, candidate, feed)
        verify_package_consumer_lock(
            candidate, feed, artifact_wrapper_lock, artifact_wrapper_receipt, project=ARTIFACT_TESTS)
        verify_package_consumer_lock(candidate, feed, wrapper_lock, wrapper_receipt, project=METADATA_TESTS)
        verify_package_consumer_lock(candidate, feed, consumer_lock, consumer_receipt)
        post_inputs = make_inputs(
            run, repository, candidate, post_sources, post_environment, post_identity, seal_sha,
            group_id=inputs["invocationGroupId"], ci_revision=ci_revision, binding_sources=binding_sources)
        evidence.verify_input_recomputation(inputs, post_inputs)
        original_post_inputs = make_inputs(
            run, repository, candidate, post_sources, post_environment, post_identity, seal_sha,
            group_id=inputs["invocationGroupId"], ci_revision=ci_revision, binding_sources=original_binding_sources)
        evidence.verify_input_recomputation(original_inputs, original_post_inputs)
        native_provenance = evidence.load_json(read_bounded(
            run.root / "proofs/sqlite-native-provenance-completion.json", 64 * 1024))
        summary = {"qualification": False, "code": "None", "baselines": 6,
                   "baselineSha256": seal_sha, "inputsSha256": evidence.digest(inputs),
                   "originalWrapperInputsSha256": evidence.digest(original_inputs),
                   "lockPreparation": lock_preparation,
                   "nativeNonCooperation": native_noncooperation,
                   "metadataRecovery": metadata_recovery,
                   "artifactRecovery": artifact_recovery,
                   "artifactTransfers": artifact_transfers,
                   "artifactNonCooperation": artifact_noncooperative,
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
