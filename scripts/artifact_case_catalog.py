"""Exact runtime witnesses required by the F-06 case matrix, not pass counts."""

import json


_LOGICAL = {
    "AS-01": ("ArtifactPublicationTests.Empty_content_and_true_absence_are_distinct",),
    "AS-02": ("ArtifactPublicationTests.Staging_is_private_until_complete_verified_commit",),
    "AS-03": ("ArtifactPublicationTests.Empty_unknown_length_and_positive_short_reads_require_real_eof",),
    "AS-04": ("ArtifactPublicationTests.Every_expectation_is_checked_and_declared_length_does_not_replace_eof",),
    "AS-05": ("ArtifactPublicationTests.Unsupported_checksum_and_range_reject_before_storage_or_stream_io",),
    "AS-06": ("ArtifactPublicationTests.Submitted_duplicates_are_fully_verified_and_keep_one_immutable_incarnation",),
    "AS-07": ("ArtifactPublicationRaceTests.Equivalent_concurrent_writers_keep_one_stamp_and_distinct_receipts",),
    "AS-08": ("ArtifactPublicationRaceTests.Conflicting_staged_length_cannot_replace_valid_content_or_its_stamp",),
    "AS-09": ("ArtifactPublicationRaceTests.Corrupt_existing_bytes_are_not_overwritten_or_reused",),
    "AS-10": ("ArtifactFailureTests.Storage_failures_remain_distinct_and_sanitized_and_do_not_publish_partial_content",),
    "AS-13": ("ArtifactBudgetTests.Cap_crossing_rejects_excess_before_append_and_capacity_recovers",
              "ArtifactPublicationTests.Every_expectation_is_checked_and_declared_length_does_not_replace_eof"),
    "AS-14": ("ArtifactBudgetTests.Full_transfer_queue_rejects_without_input_io_and_capacity_returns_after_release",
              "ArtifactBudgetTests.Reclaimed_identity_history_has_a_finite_budget_and_expiry_restores_new_digest_admission"),
    "AS-15": ("ArtifactBudgetTests.Cooperative_cancellation_stops_input_without_disposing_borrowed_stream",),
    "AS-16": ("ArtifactBudgetTests.Producer_and_consumer_inactivity_deadlines_release_cooperative_work_without_closing_borrowed_streams",
              "ArtifactBudgetTests.Total_deadline_includes_shared_authority_contention_before_publication"),
    "AS-17": ("ArtifactFailureTests.Storage_failures_remain_distinct_and_sanitized_and_do_not_publish_partial_content",
              "ArtifactFailureTests.Failed_prefix_reclamation_retains_ownership_until_exact_bounded_cleanup"),
    "AS-18": ("ArtifactReadVerificationTests.Destination_failure_and_second_copy_never_return_verified_completion_or_dispose_borrowed_streams",
              "ArtifactNonCooperationTests.Concurrent_close_waits_for_the_same_physical_guard_release_and_fences_new_copy",
              "ArtifactNonCooperationTests.Idle_read_expiry_fences_copy_without_touching_the_destination"),
    "AS-19": ("ArtifactFailureTests.Storage_failures_remain_distinct_and_sanitized_and_do_not_publish_partial_content",),
    "AS-20": ("ArtifactFailureTests.Storage_failures_remain_distinct_and_sanitized_and_do_not_publish_partial_content",
              "ArtifactFailureTests.Unexpected_fault_after_visibility_requires_exact_ticket_reconciliation"),
    "AS-21": ("ArtifactReconciliationTests.Acknowledged_commit_reconciles_and_retries_one_identical_receipt_without_new_source",
              "ArtifactFailureTests.Committed_receipts_remain_reconcilable_while_exact_residual_staging_is_reclaimed",
              "ArtifactReconciliationTests.Lost_acknowledgment_never_becomes_rollback_or_another_publication"),
    "AS-22": ("ArtifactReconciliationTests.Finalized_mutation_retries_preserve_expiry_and_foreign_ticket_failures",
              "ArtifactReconciliationTests.Expired_history_cannot_be_revived_by_clock_rollback_or_foreign_epoch"),
    "AS-23": ("ArtifactRecoveryTests.Expiry_cleanup_and_restage_fence_the_old_generation",
              "ArtifactRecoveryTests.Progressing_commit_renews_owner_across_the_original_ttl",
              "ArtifactBudgetTests.Cancellation_of_an_admitted_commit_cannot_fence_an_externally_renewed_owner"),
    "AS-24": ("ArtifactRecoveryTests.Recovery_pages_are_bounded_query_bound_and_not_deletion_authority",
              "ArtifactRecoveryTests.Changed_inventory_rejects_old_continuations_and_fresh_pages_cover_every_current_identity",
              "ArtifactRecoveryTests.Sequential_recovery_retires_consumed_cursors_without_starving_independent_scans",
              "ArtifactBudgetTests.History_candidate_pages_resume_past_ineligible_entries_and_preserve_a_faulted_candidate"),
    "AS-25": ("ArtifactRecoveryTests.Recovery_pages_are_bounded_query_bound_and_not_deletion_authority",),
    "AS-27": ("ArtifactRecoveryTests.Late_cleanup_rechecks_the_exact_generation_after_replacement",
              "ArtifactFailureTests.Failed_prefix_reclamation_retains_ownership_until_exact_bounded_cleanup",
              "ArtifactRecoveryTests.Expired_reclaimed_history_remains_owned_until_the_admitted_delete_physically_settles",
              "ArtifactNonCooperationTests.Deadline_and_stop_return_while_a_native_io_boundary_holds_provider_state"),
    "AS-28": ("ArtifactDeletionTests.Live_reference_or_unavailable_reference_authority_denies_removal",),
    "AS-29": ("ArtifactDeletionTests.A_held_reader_finishes_before_exclusive_deletion_and_later_opens_cannot_enter",),
    "AS-31": ("ArtifactDeletionTests.Exact_delete_receipts_and_recreation_never_remove_the_new_incarnation",),
    "AS-32": ("ArtifactDeletionTests.Exact_delete_receipts_and_recreation_never_remove_the_new_incarnation",),
    "AS-33": ("ArtifactDeletionTests.Lost_delete_acknowledgment_preserves_pending_reclamation_until_actual_cleanup",),
    "AS-34": ("ArtifactAdmissionTests.Symlinked_root_or_ancestor_is_rejected_without_touching_outside_sentinel",
              "ArtifactAdmissionTests.Before_admission_and_with_mismatched_authority_no_source_or_directory_is_touched",
              "ArtifactEvidenceTests.Only_exact_current_receipts_with_opaque_same_operation_protection_validate"),
    "AS-35": ("ArtifactDeletionTests.Live_reference_or_unavailable_reference_authority_denies_removal",
              "ArtifactEvidenceTests.Only_exact_current_receipts_with_opaque_same_operation_protection_validate"),
    "AS-36": ("ArtifactCompositionTests.Configured_singleton_selection_recovers_and_restarts_explicitly",),
    "AS-39": ("ArtifactNonCooperationTests.Noncooperative_source_retains_bounded_ownership_and_blocks_admission_until_real_settlement",
              "ArtifactNonCooperationTests.Noncooperative_destination_cannot_release_live_read_protection_via_close_or_dispose",
              "ArtifactNonCooperationTests.Deadline_and_stop_return_while_a_native_io_boundary_holds_provider_state"),
    "AS-40": ("ArtifactCompositionTests.Configured_selection_is_inert_until_start_and_missing_guarantees_block_readiness",
              "ArtifactFailureTests.Stop_retains_failed_prefix_ownership_until_reclamation_can_settle",
              "ArtifactCompositionTests.Configured_singleton_selection_recovers_and_restarts_explicitly"),
}

_QUALIFICATION = (
    "ArtifactContractTests.Qualification_exclusions_cannot_exchange_simulated_and_durable_failure_models",
    "ArtifactContractTests.Flat_case_names_and_unattributed_hashes_cannot_claim_qualification",
    "ArtifactContractTests.Qualification_case_results_reject_missing_or_unbounded_attribution",
    "ArtifactContractTests.Qualification_records_keep_case_proofs_and_environment_attributable_and_immutable",
    "ArtifactContractTests.Qualification_environment_is_bounded_unambiguous_and_redacted",
)


def runtime_test(method, provider=None, **parameters):
    name = method if method.startswith("Hoard.") else "Hoard.Artifacts.Tests." + method
    if provider is not None:
        parameters = {"provider": provider, **parameters}
    if parameters:
        arguments = ", ".join(f"{key}: {str(value) if isinstance(value, bool) else json.dumps(value)}"
                              for key, value in parameters.items())
        name += f"({arguments})"
    return name


def required_runtime_tests(provider, case):
    if provider not in ("local", "object") or case not in {f"AS-{number:02}" for number in range(1, 49)}:
        raise RuntimeError("Foreign artifact runtime case catalog lookup.")
    tests = {runtime_test(method, provider) for method in _LOGICAL.get(case, ())}
    if case == "AS-10":
        tests.update(runtime_test(
            "ArtifactReadVerificationTests.Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence",
            provider, truncate=value) for value in (False, True))
    if case in ("AS-11", "AS-12"):
        tests.add(runtime_test("ArtifactTransferProofTests.Measured_transfer_binds_actual_bytes_pacing_hashes_and_os_peak",
                               provider, size=268435456 if case == "AS-11" else 4294967296))
    if case == "AS-13":
        tests.add(runtime_test("ArtifactValueTests.Expectations_and_checksums_copy_input_and_reject_each_bound"))
    if case == "AS-14":
        tests.update(runtime_test(
            "ArtifactBudgetTests.Expired_ticket_history_restores_write_and_delete_capacity_without_losing_committed_or_removed_identity",
            provider, reserveDelete=value) for value in (False, True))
    if case == "AS-15":
        tests.update(runtime_test(
            "ArtifactBudgetTests.Cancelled_commit_before_decision_fences_the_ticket_and_cannot_publish_on_retry",
            provider, alreadyCancelled=value) for value in (False, True))
        tests.add(runtime_test(
            "ArtifactBudgetTests.Cancellation_after_resource_release_cannot_retain_an_already_settled_operation", provider))
        tests.update(runtime_test("ArtifactBudgetTests." + method, provider, readSession=value)
                     for method in ("Cancellation_at_result_handoff_cannot_discard_a_reserved_ticket_or_live_read",
                                    "Cancellation_before_result_handoff_reclaims_the_unclaimed_ticket_or_read",
                                    "Failed_unclaimed_result_cleanup_blocks_admission_and_stop_until_exact_retry")
                     for value in (False, True))
        tests.add(runtime_test("ArtifactBudgetTests.Undelivered_verified_staging_is_reclaimed_after_ownership_expiry", provider))
    if case == "AS-19":
        tests.add(runtime_test("ArtifactValueTests.Public_diagnostic_formatting_is_redacted_and_contract_members_are_get_only"))
    if provider == "object" and case in ("AS-15", "AS-17", "AS-27"):
        tests.update(runtime_test(
            "ArtifactFailureTests.Unselected_object_cleanup_retains_exact_ownership_and_blocks_retry_until_reclaimed",
            boundary=boundary, cancel=cancel)
            for boundary in ("object.commit-progress", "pointer.compare") for cancel in (False, True))
    if provider == "object" and case == "AS-40":
        tests.add(runtime_test(
            "ArtifactRecoveryTests.Stop_retains_unselected_object_ownership_and_retries_only_its_private_payload"))
    if provider == "object" and case == "AS-21":
        tests.add(runtime_test(
            "ArtifactFailureTests.Reused_object_receipt_survives_failed_unselected_assembly_cleanup"))
    if case == "AS-25" and provider == "object":
        tests.add(runtime_test("ArtifactVisibilityTests.Delayed_object_listing_does_not_block_direct_publication_or_establish_absence"))
    if case in ("AS-26", "AS-28", "AS-30"):
        methods = {
            "AS-26": ("Failed_metadata_transaction_leaves_identifiable_committed_bytes_not_a_fabricated_entry",),
            "AS-28": ("Actual_metadata_references_deny_removal_until_the_reference_transaction_commits",),
            "AS-30": ("Lost_metadata_acknowledgment_keeps_real_reference_protection_until_physical_settlement",
                      "New_reference_cannot_cross_an_admitted_zero_reference_deletion"),
        }[case]
        tests.update(runtime_test("ArtifactMetadataIntegrationTests." + method, provider, metadataProvider=metadata)
                     for method in methods for metadata in ("sqlite", "memory"))
    if case == "AS-35":
        tests.update(runtime_test("ArtifactAuthorityTests." + method) for method in (
            "Copied_foreign_changed_scope_and_disposed_handles_never_authorize_retention",
            "Held_same_operation_can_settle_after_expiry_without_reentrant_admission",
            "Queued_exclusive_admission_closes_new_shared_admission_and_retention_never_reenters"))
        tests.add(runtime_test("ArtifactMetadataAuthorityTests.Mismatched_authority_composition_cannot_substitute_field_equivalent_protection"))
    if case == "AS-37":
        methods = ("Delayed_object_listing_does_not_block_direct_publication_or_establish_absence",
                   "Object_commit_waits_for_direct_availability_while_listing_is_independently_observable") if provider == "object" else (
                       "Local_publication_is_directly_visible_before_acknowledgment",)
        tests.update(runtime_test("ArtifactVisibilityTests." + method) for method in methods)
    if case == "AS-38":
        tests.update(runtime_test(
            "ArtifactCapabilityTests.Missing_mandatory_guarantees_versions_or_authority_reject_before_io",
            provider, gap=gap) for gap in ("version", "publication", "deletion", "recovery", "fencing", "readers", "streaming", "authority"))
    if case == "AS-39":
        tests.update(runtime_test(
            "ArtifactNonCooperativeChildTests.Owned_child_retains_noncooperative_work_until_parent_termination",
            provider, scenario=scenario) for scenario in ("source", "destination", "native"))
    if case in ("AS-41", "AS-42", "AS-43", "AS-44"):
        if provider == "object":
            tests.add(runtime_test(_QUALIFICATION[0]))
        else:
            barriers = {"AS-41": ("B0", "B1"), "AS-42": ("B2",), "AS-43": ("B3",), "AS-44": ("D0", "D1")}[case]
            tests.update(runtime_test(
                "ArtifactCrashTests.Real_parent_kill_and_fresh_process_reopen_preserve_exact_receipts_and_control_bytes",
                barrier=barrier) for barrier in barriers)
    if case in ("AS-45", "AS-46"):
        tests.add(runtime_test("Hoard.Architecture.Tests.ArtifactBoundaryTests.Prepared_artifact_packages_preserve_independence_and_existing_public_members"))
        if case == "AS-45":
            tests.add(runtime_test("Hoard.Architecture.Tests.ArtifactBoundaryTests.Prepared_artifact_consumer_bodies_are_provider_neutral_and_object_mechanisms_do_not_rename"))
        else:
            tests.add(runtime_test("ArtifactContractTests.Marker_and_historical_digest_remain_separate_from_operational_contracts"))
    if case in ("AS-47", "AS-48"):
        tests.update(runtime_test(method) for method in _QUALIFICATION)
    if not tests:
        raise RuntimeError("Artifact case has no required runtime witnesses.")
    return frozenset(tests)
