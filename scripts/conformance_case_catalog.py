"""F-07 expectations expanded independently of any binding or result."""

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType

from conformance_evidence import (
    CATALOG_REVISION, ConformanceError, MAX_RESULTS, MAX_WITNESSES, PROFILES,
    canonical_bytes, load_json, stable_id, _one_of, _record,
)


INVENTORY = Path(__file__).resolve().parents[1] / "tests/fixtures/conformance/baselines/inventory.json"
FULL_ARTIFACT_CONSUMER_PREFIX = "Hoard.Fixtures.Conformance.Consumer.ArtifactConformanceSessionTests."

INHERITED_GUARD_FAILURES = MappingProxyType({
    "inherited-discovery-guard-source-identity": (
        "Hoard.Composition.Tests.DiscoveryBoundsTests."
        "Cancellation_deadline_and_inconsistent_authority_never_become_successful_observations",
        "inherited.discovery.mutation", "none"),
    "inherited-discovery-guard-path-protection": (
        "Hoard.Composition.Tests.DiscoveryAuthorizationTests."
        "Both_literal_routes_require_the_same_policy_without_disclosure",
        "inherited.discovery.mutation", "none"),
})

CATEGORY_BINDING_SLOTS = (
    ("metadata", "sqlite", "fixture.metadata.sqlite", "Hoard.Fixtures.Metadata.Sqlite"),
    ("metadata", "memory", "fixture.metadata.memory", "Hoard.Fixtures.Metadata.Memory"),
    ("artifacts", "local", "fixture.artifact.local", "Hoard.Fixtures.Artifacts.Local"),
    ("artifacts", "object", "fixture.artifact.object", "Hoard.Fixtures.Artifacts.ObjectSemantics"),
)

AUTHORITY_INTEGRATION_ROWS = MappingProxyType({
    "Hoard.Conformance.Tests.AuthorityIntegrationTests."
    f'Actual_compositions_preserve_shared_authority(provider: "{provider}", metadataProvider: "{metadata}", consumer: "{consumer}")':
        (provider, metadata, consumer)
    for provider in ("local", "object") for metadata in ("memory", "sqlite") for consumer in (
        "reference-admission", "failed-transaction", "live-references", "lost-acknowledgment",
        "incarnation", "reader", "foreign-authority", "shutdown")})

CATEGORY_MUTATION_METHODS = MappingProxyType({
    "metadata": ("Stale_metadata_replay_is_rejected", "Corrected_metadata_replay_passes",
                 "Hoard.Testing.Conformance.Metadata.MetadataTimeAssertions.TicketExpiryAndRollbackAsync"),
    "artifacts": ("Premature_artifact_publication_is_rejected", "Corrected_artifact_staging_passes",
                  "Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions.PrivateStagingAsync"),
})


def category_mutation_witnesses(profile, *, corrected):
    if profile not in CATEGORY_MUTATION_METHODS or type(corrected) is not bool:
        raise ConformanceError("WitnessMissing")
    method = CATEGORY_MUTATION_METHODS[profile][int(corrected)]
    return MappingProxyType({
        "Hoard.Conformance.Tests.CategoryMutationTests." + method + f'(provider: "{binding}")': binding
        for category, binding, _, _ in CATEGORY_BINDING_SLOTS if category == profile})


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
    identities.update(prefix + "Observed_publication_consumers_preserve_actual_binding_guarantees"
                      + f'(provider: "{provider}", consumer: "{consumer}")'
                      for provider in ("local", "object") for consumer in (
                          "empty", "unknown-length", "expectations", "unsupported", "duplicates"))
    identities.update(prefix + "Observed_read_reconciliation_and_deletion_preserve_actual_binding_guarantees"
                      + f'(provider: "{provider}", consumer: "{consumer}")'
                      for provider in ("local", "object") for consumer in (
                          "destination-failure", "exact-retry", "staged-length", "recreation", "reader-exclusion"))
    identities.update(prefix + "Observed_boundary_consumers_preserve_actual_binding_guarantees"
                      + f'(provider: "{provider}", consumer: "{consumer}")'
                      for provider, consumers in (
                          ("local", ("private-staging", "concurrent-writers", "lost-acknowledgment", "visible-before-ack")),
                          ("object", ("private-staging", "concurrent-writers", "lost-acknowledgment", "direct-availability")))
                      for consumer in consumers)
    identities.update(prefix + "Ordinary_acknowledgment_shaped_observer_errors_still_fault_actual_settlement"
                      + f'(provider: "{provider}")' for provider in ("local", "object"))
    identities.update(prefix + "Observed_payload_and_progress_consumers_preserve_actual_binding_guarantees"
                      + f'(provider: "{provider}", consumer: "{consumer}")'
                      for provider in ("local", "object") for consumer in (
                          "read-bitflip", "read-truncate", "commit-progress", "exact-payload"))
    identities.update(prefix + "Observed_recovery_evidence_and_expiry_preserve_actual_binding_guarantees"
                      + f'(provider: "{provider}", consumer: "{consumer}")'
                      for provider in ("local", "object") for consumer in (
                          "receipts", "recovery-pages", "sequential-recovery", "changed-inventory",
                          "expiry-generation", "ownerless-expiry", "finalized-noncommit", "finalized-mutations",
                          "idle-read", "cooperative-inactivity", "noncooperative-source", "noncooperative-destination"))
    identities.update(prefix + "Observed_cancelled_descriptors_preserve_actual_current_ownership"
                      + f'(provider: "{provider}", alteration: "{alteration}")'
                      for provider in ("local", "object") for alteration in ("completion", "handle", "renewed"))
    identities.update(prefix + "Observed_budget_failures_and_references_preserve_actual_binding_guarantees"
                      + f'(provider: "{provider}", consumer: "{consumer}")'
                      for provider in ("local", "object") for consumer in (
                          "authority-deadline", "cancel-before", "cancel-waiting", "cap-crossing",
                          "cooperative-cancel", "storage-failures", "live-references", "reclaimed-identities"))
    identities.add(prefix + "Observed_budget_failures_and_references_preserve_actual_binding_guarantees"
                   + '(provider: "local", consumer: "reclaimed-incarnations")')
    identities.update(prefix + "Observed_clock_rollback_preserves_expiry_and_monotonic_ownership"
                      + f'(provider: "{provider}", consumer: "{consumer}")'
                      for provider in ("local", "object") for consumer in (
                          "history", "write-capacity", "delete-capacity"))
    identities.update(prefix + "Observed_handoff_and_progress_preserve_actual_result_ownership"
                      + f'(provider: "{provider}", consumer: "{consumer}")'
                      for provider in ("local", "object") for consumer in (
                          "released-cancellation", "successful-ticket", "successful-read",
                          "unclaimed-ticket", "unclaimed-read", "expired-staging", "progress-cancellation"))
    identities.update(prefix + "Observed_admitted_work_preserves_history_queue_and_shutdown_ownership"
                      + f'(provider: "{provider}", consumer: "{consumer}")'
                      for provider in ("local", "object") for consumer in (
                          "delete-history", "transfer-queue", "released-shutdown"))
    identities.update(prefix + "Observed_reconciliation_and_cleanup_preserve_admitted_generation_ownership"
                      + f'(provider: "{provider}", consumer: "{consumer}")'
                      for provider in ("local", "object") for consumer in (
                          "settled-replacement", "reconciliation-history", "cleanup-generation"))
    identities.update(prefix + "Observed_history_candidates_preserve_the_original_page_bounds"
                      + f'(provider: "{provider}", kind: "{kind}")'
                      for provider in ("local", "object") for kind in (
                          ("tickets", "dependencies", "decisions", "reclamation") if provider == "local"
                          else ("tickets", "dependencies", "decisions")))
    identities.update(prefix + method + f'(provider: "{provider}")'
                      for provider in ("local", "object") for method in (
                          "Observed_history_candidates_resume_after_an_owned_one_shot_failure",
                          "Ordinary_candidate_shaped_observer_errors_still_fault_actual_settlement"))
    identities.update(prefix + "Observed_receipts_and_failed_callbacks_preserve_actual_resource_ownership"
                      + f'(provider: "{provider}", consumer: "{consumer}")'
                      for provider in ("local", "object")
                      for consumer in ("receipt", "read-open", "verified-reconciliation", "pending-reclamation"))
    identities.update(prefix + "Ordinary_errors_inside_owned_failure_callbacks_still_fault_actual_settlement"
                      + f'(provider: "{provider}", point: {point})'
                      for provider in ("local", "object") for point in ("ReadOpened", "ReconciliationVerified", "DeleteRemoved"))
    identities.update(prefix + "Observed_admitted_open_rechecks_actual_quarantine_before_result_handoff"
                      + f'(provider: "{provider}")' for provider in ("local", "object"))
    identities.update(prefix + "Observed_validation_first_quarantine_survives_actual_restoration_and_reopen"
                      + f'(provider: "{provider}", missing: {missing})'
                      for provider in ("local", "object") for missing in ("False", "True"))
    identities.update(prefix + "Observed_initial_admission_preserves_actual_capabilities_and_no_io_rejection"
                      + f'(provider: "{provider}", probe: {probe})'
                      for provider in ("local", "object") for probe in (
                          "Complete", "Version", "Publication", "Deletion", "Recovery", "Fencing",
                          "Readers", "Streaming", "ForeignAuthority"))
    identities.add(prefix + 'Observed_local_reconciliation_cannot_finalize_after_actual_read_quarantine(provider: "local")')
    identities.update(prefix + "Observed_committed_detection_paths_quarantine_actual_restored_bytes"
                      + f'(provider: "{provider}", detection: "{detection}")'
                      for provider in ("local", "object") for detection in ("open", "publication", "reconciliation"))
    identities.update(prefix + "Observed_local_durable_reopen_preserves_retired_decisions_and_receipt_release"
                      + f'(provider: "local", consumer: "{consumer}")'
                      for consumer in ("committed-decision", "durable-receipt"))
    identities.add(prefix + 'Ordinary_record_write_callback_errors_still_fault_actual_settlement(provider: "local")')
    identities.add(prefix + 'Object_record_write_fault_rejects_without_borrowing_actual_deletion(provider: "object")')
    identities.add(prefix + 'Observed_failed_quarantine_persistence_retains_actual_ownership_through_retry_and_reopen(provider: "local")')
    identities.add(prefix + 'Object_record_permissions_reject_without_borrowing_payload_access(provider: "object")')
    identities.add(prefix + 'Observed_record_permission_application_joins_actual_shutdown_before_resource_settlement(provider: "local")')
    identities.update(prefix + "Observed_committed_residual_cleanup_preserves_actual_receipt_and_owned_capacity"
                      + f'(provider: "{provider}")' for provider in ("local", "object"))
    identities.update(prefix + "Observed_storage_inventory_bounds_all_actual_entries_and_rejects_nonfiles"
                      + f'(provider: "{provider}", shape: "{shape}")'
                      for provider in ("local", "object") for shape in ("overflow", "directory", "symlink"))
    identities.update(prefix + "Observed_failed_prefix_cleanup_and_stop_preserve_actual_ownership_and_fence_replay"
                      + f'(provider: "{provider}", stop: {stop})'
                      for provider in ("local", "object") for stop in ("False", "True"))
    identities.update(prefix + "Observed_object_cleanup_and_stop_preserve_actual_selected_payload"
                      + f'(provider: "object", stop: {stop})' for stop in ("False", "True"))
    identities.update(prefix + "Observed_unselected_object_cleanup_preserves_actual_residual_and_blocks_retry"
                      + f'(provider: "object", point: {point}, cancel: {cancel})'
                      for point in ("CommitProgress", "BeforePublicationDecision") for cancel in ("False", "True"))
    identities.update(prefix + "Ordinary_cleanup_boundary_errors_cannot_borrow_intentional_failure_ownership"
                      + f'(provider: "{provider}", point: {point})'
                      for provider in ("local", "object") for point in ("StagePrefix", "BeforePublicationDecision", "CommitProgress"))
    identities.update(prefix + "Ordinary_record_permission_release_errors_restore_actual_mode_before_faulted_settlement"
                      + f'(provider: "local", cancellation: {cancellation})' for cancellation in ("False", "True"))
    identities.update(prefix + "Observed_validation_access_failures_preserve_actual_intact_content"
                      + f'(provider: "{provider}", unavailable: {unavailable})'
                      for provider in ("local", "object") for unavailable in ("False", "True"))
    identities.update(prefix + "Observed_access_application_joins_actual_shutdown_before_releasing_owned_resources"
                      + f'(provider: "{provider}", unavailable: {unavailable})'
                      for provider in ("local", "object") for unavailable in ("False", "True"))
    identities.update(prefix + method + f'(provider: "{provider}", unavailable: {unavailable})'
                      for method in ("Observed_access_scope_protects_actual_incarnation_until_restoration",
                                     "Ordinary_access_release_errors_restore_actual_payload_before_faulted_settlement",
                                     "Ordinary_access_release_cancellation_restores_actual_payload_before_faulted_settlement")
                      for provider in ("local", "object") for unavailable in ("False", "True"))
    return (("full-artifact-binding", tuple(sorted(identities)), "None", "Passed", 0, "None"),)


def full_artifact_binding_origin_counts():
    reopen = FULL_ARTIFACT_CONSUMER_PREFIX + "Observed_full_binding_reopens_actual_components_and_fences_stale_controls"
    payload = FULL_ARTIFACT_CONSUMER_PREFIX + "Observed_payload_and_progress_consumers_preserve_actual_binding_guarantees"
    validation = FULL_ARTIFACT_CONSUMER_PREFIX + "Observed_validation_first_quarantine_survives_actual_restoration_and_reopen"
    detection = FULL_ARTIFACT_CONSUMER_PREFIX + "Observed_committed_detection_paths_quarantine_actual_restored_bytes"
    durable = FULL_ARTIFACT_CONSUMER_PREFIX + "Observed_local_durable_reopen_preserves_retired_decisions_and_receipt_release"
    persistence = FULL_ARTIFACT_CONSUMER_PREFIX + "Observed_failed_quarantine_persistence_retains_actual_ownership_through_retry_and_reopen"
    prefix_stop = FULL_ARTIFACT_CONSUMER_PREFIX + "Observed_failed_prefix_cleanup_and_stop_preserve_actual_ownership_and_fence_replay"
    return {identity: 2 if identity.split("(")[0] in (reopen, durable, persistence) or ('(provider: "local"' in identity and (
                (identity.split("(")[0] == prefix_stop and "stop: True" in identity) or
                identity.split("(")[0] == validation or (identity.split("(")[0] == detection and any(
                    f'detection: "{value}"' in identity for value in ("open", "publication")))
                or (identity.split("(")[0] == payload and any(
                    f'consumer: "{consumer}"' in identity for consumer in ("read-bitflip", "read-truncate")))))
            else 1 for identity in full_artifact_binding_scenarios()[0][1]}



def contributor_artifact_component_origin_counts(binding_id, *, profile):
    binding = stable_id(binding_id)
    profile = _record({
        "durability": _one_of("LocalProcessCrash", "SimulationOnly"),
        "enumeration": _one_of("Snapshot", "Incomplete"),
    })(profile)
    method = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
              "Observed_portable_consumers_preserve_actual_guarantees")
    identities = {
        f'{method}(provider: "{binding}", consumer: "{consumer}")': 1
        for consumer in (
            "empty", "unknown-length", "expectations", "unsupported", "duplicates",
            "destination-failure", "exact-retry", "staged-length", "recreation",
            "reader-exclusion", "cap-crossing", "storage-failures", "live-references",
            "private-staging", "concurrent-writers", "lost-acknowledgment", "visible-before-ack",
            "receipts", "recovery-pages", "changed-inventory", "expiry-generation", "ownerless-expiry",
            "finalized-noncommit", "finalized-mutations", "idle-read", "cooperative-inactivity",
            "noncooperative-source", "noncooperative-destination", "authority-deadline",
            "cancel-before", "cancel-waiting", "cooperative-cancel", "reclaimed-identities",
            "concurrent-release", "sequential-recovery", "released-cancellation", "successful-ticket",
            "successful-read", "unclaimed-ticket", "unclaimed-read", "expired-staging", "progress-cancellation",
            "rollback-history", "rollback-write-capacity", "rollback-delete-capacity",
            "descriptor-completion", "descriptor-handle", "descriptor-renewed",
            "candidate-tickets", "candidate-dependencies", "candidate-decisions", "candidate-resume",
            "receipt", "read-open", "verified-reconciliation", "pending-reclamation",
            "delete-history", "transfer-queue", "released-shutdown", "committed-residual",
            "settled-replacement", "reconciliation-history", "cleanup-generation")}
    if profile["enumeration"] == "Incomplete":
        identities[f'{method}(provider: "{binding}", consumer: "direct-availability")'] = 1
    control = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
               "Observed_controls_reach_actual_work")
    identities.update({
        f'{control}(provider: "{binding}", fault: {fault})': 1
        for fault in (
            "PublicationBoundary", "DirectVisibility", "PayloadDamage", "Capacity",
            "NativeNonCooperation", "CleanupFailure", "GenerationBoundary", "ReceiptBoundary",
            "SourceNonCooperation", "SinkNonCooperation")})
    reopen = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
              "Observed_reopen_preserves_actual_lineage_and_declared_state")
    identities[f'{reopen}(provider: "{binding}")'] = 2
    admission = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
                 "Observed_admission_preserves_actual_no_io_rejection")
    identities.update({
        f'{admission}(provider: "{binding}", probe: {probe})': 1
        for probe in ("Complete", "Version", "Publication", "Deletion", "Recovery", "Fencing",
                      "Readers", "Streaming", "ForeignAuthority")})
    payload = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
               "Observed_payload_controls_preserve_actual_quarantine_and_declared_state")
    identities.update({
        f'{payload}(provider: "{binding}", consumer: "{consumer}")':
            2 if profile["durability"] == "LocalProcessCrash" and consumer in ("read-bitflip", "read-truncate") else 1
        for consumer in ("read-bitflip", "read-truncate", "commit-progress", "exact-payload")})
    detection = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
                 "Observed_payload_detection_preserves_actual_quarantine_and_declared_state")
    identities.update({
        f'{detection}(provider: "{binding}", detection: "{value}")':
            2 if profile["durability"] == "LocalProcessCrash" and value in ("open", "publication") else 1
        for value in ("open", "publication", "reconciliation")})
    validation = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
                  "Observed_quarantine_validation_preserves_actual_restoration_and_declared_state")
    identities.update({
        f'{validation}(provider: "{binding}", missing: {missing})':
            2 if profile["durability"] == "LocalProcessCrash" else 1
        for missing in ("False", "True")})
    for method, points in (
            ("Observed_ordinary_cleanup_errors_preserve_actual_faulted_ownership",
             ("StagePrefix", "BeforePublicationDecision", "CommitProgress")),
            ("Observed_ordinary_failure_callbacks_preserve_actual_faulted_ownership",
             ("ReadOpened", "ReconciliationVerified", "DeleteRemoved"))):
        prefix = f"Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests.{method}"
        identities.update({f'{prefix}(provider: "{binding}", point: {point})': 1 for point in points})
    observer = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
                "Observed_ordinary_observer_errors_preserve_actual_faulted_ownership")
    identities.update({
        f'{observer}(provider: "{binding}", consumer: "{consumer}")': 1
        for consumer in ("candidate", "acknowledgment")})
    prefix = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
              "Observed_payload_prefix_cleanup_preserves_actual_ownership_and_declared_state")
    identities.update({
        f'{prefix}(provider: "{binding}", stop: {stop})':
            2 if stop == "True" and profile["durability"] == "LocalProcessCrash" else 1
        for stop in ("False", "True")})
    access = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
              "Observed_payload_access_preserves_actual_ownership_and_intact_content")
    identities.update({
        f'{access}(provider: "{binding}", consumer: "{consumer}", unavailable: {unavailable})': 1
        for consumer in ("scope", "validation") for unavailable in ("False", "True")})
    application = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
                   "Observed_payload_application_shutdown_preserves_actual_resource_ownership")
    identities.update({
        f'{application}(provider: "{binding}", unavailable: {unavailable})': 1
        for unavailable in ("False", "True")})
    release = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
               "Observed_payload_release_errors_preserve_actual_restoration_and_faulted_ownership")
    identities.update({
        f'{release}(provider: "{binding}", unavailable: {unavailable}, cancellation: {cancellation})': 1
        for unavailable in ("False", "True") for cancellation in ("False", "True")})
    admitted = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
                "Observed_payload_admission_rechecks_actual_quarantine_before_handoff")
    identities[f'{admitted}(provider: "{binding}")'] = 1
    if profile["durability"] == "LocalProcessCrash":
        portable = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
                    "Observed_portable_consumers_preserve_actual_guarantees")
        identities.update({
            f'{portable}(provider: "{binding}", consumer: "{consumer}")': 1
            for consumer in ("reclaimed-incarnations", "candidate-reclamation")})
        release = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
                   "Observed_durable_record_release_errors_preserve_actual_mode_and_faulted_ownership")
        identities.update({
            f'{release}(provider: "{binding}", cancellation: {cancellation})': 1
            for cancellation in ("False", "True")})
        durable = ("Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests."
                   "Observed_durable_reopen_preserves_actual_decisions_and_receipts")
        identities.update({
            f'{durable}(provider: "{binding}", consumer: "{consumer}")': 2
            for consumer in ("committed-decision", "durable-receipt")})
        identities.update({
            f'Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests.{method}(provider: "{binding}")': count
            for method, count in (
                ("Observed_durable_quarantine_persistence_preserves_actual_ownership_and_reopen", 2),
                ("Observed_durable_record_callback_errors_preserve_actual_faulted_ownership", 1),
                ("Observed_durable_reconciliation_preserves_actual_read_quarantine", 1),
                ("Observed_durable_record_application_shutdown_preserves_actual_resource_ownership", 1))})
    return identities


def metadata_common_consumer_origin_counts(*, binding_ids=("memory", "sqlite")):
    if not isinstance(binding_ids, (list, tuple)) or not 0 < len(binding_ids) <= 1024:
        raise ConformanceError("BindingInvalid")
    bindings = tuple(stable_id(value) for value in binding_ids)
    if len(set(bindings)) != len(bindings):
        raise ConformanceError("BindingInvalid")
    prefix = "Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
    method = prefix + "Observed_factories_execute_unchanged_common_consumers_with_actual_origins"
    identities = {
        f'{method}(provider: "{provider}", consumer: "{consumer}")': 1
        for provider in bindings for consumer in (
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
    reopen = prefix + "Observed_reopen_preserves_public_state_and_fences_stale_controls"
    identities.update({f'{reopen}(provider: "{provider}")': 2 for provider in bindings})
    schema = prefix + "Observed_schema_consumers_preserve_actual_reopen_lineage"
    identities.update({
        f'{schema}(provider: "{provider}", consumer: "{consumer}")': count
        for provider in bindings for consumer, count in (
            ("upgrade", 3), ("upgrade-invalid", 2), ("upgrade-exclusive", 2), ("future-corrupt", 4))})
    cursor = prefix + "Observed_continuation_corruption_preserves_actual_pages"
    identities.update({
        f'{cursor}(provider: "{provider}", corruption: {corruption})': 1
        for provider in bindings for corruption in (
            "Null", "Omitted", "WrongType", "Empty", "OddHex", "InvalidHex")})
    dimensions = prefix + "Observed_query_corruption_preserves_actual_dimensions"
    identities.update({
        f'{dimensions}(provider: "{provider}", corruption: {corruption})': 1
        for provider in bindings for corruption in (
            "CacheAuthorization", "AggregateAuthorization", "AggregateStart", "AggregateEnd", "LeaseResource")})
    epoch = prefix + "Observed_continuations_reject_foreign_actual_store_epochs"
    identities.update({f'{epoch}(provider: "{provider}")': 2 for provider in bindings})
    ownership = prefix + "Observed_corruption_scopes_preserve_actual_target_and_closure_ownership"
    identities.update({
        f'{ownership}(provider: "{provider}", operation: {operation})': 1
        for provider in bindings for operation in ("False", "True")})
    application = prefix + "Observed_corruption_application_preserves_actual_commits_and_recoverable_ownership"
    identities.update({
        f'{application}(provider: "{provider}", operation: {operation}, consumer: "{consumer}")': 1
        for provider in bindings for operation in ("False", "True")
        for consumer in ("capture", "cancel", "restore")})
    closure = prefix + "Observed_corruption_closure_fences_later_scopes_while_actual_work_is_held"
    identities.update({
        f'{closure}(provider: "{provider}", reopen: {reopen})': 2 if reopen == "True" else 1
        for provider in bindings for reopen in ("False", "True")})
    return MappingProxyType(identities)


def metadata_common_consumer_tests():
    return MappingProxyType({
        identity: (binding, "full-metadata-binding")
        for identity in metadata_common_consumer_origin_counts() for binding in ("memory", "sqlite")
        if f'(provider: "{binding}"' in identity})


def category_common_consumer_origin_counts(profile):
    if profile == "metadata":
        return metadata_common_consumer_origin_counts()
    if profile == "artifacts":
        return full_artifact_binding_origin_counts()
    raise ConformanceError("WitnessMissing")


def category_common_consumer_tests(profile):
    providers = {"metadata": ("memory", "sqlite"), "artifacts": ("local", "object")}
    if profile not in providers:
        raise ConformanceError("WitnessMissing")
    return MappingProxyType({
        identity: (binding, "full-" + ("artifact" if profile == "artifacts" else "metadata") + "-binding")
        for identity in category_common_consumer_origin_counts(profile) for binding in providers[profile]
        if f'(provider: "{binding}"' in identity})


def metadata_argument_expectations(*, original):
    """Frozen (source-node index, argument kind, argument value) assignments."""
    if type(original) is not bool:
        raise ConformanceError("WitnessMissing")
    identities = ORIGINAL_METADATA_WITNESSES if original else metadata_common_consumer_tests()
    expected = {identity: () for identity in identities}
    continuation = (("null", "Null"), ("omitted", "Omitted"), ("wrong-type", "WrongType"),
                    ("empty", "Empty"), ("odd-hex", "OddHex"), ("invalid-hex", "InvalidHex"))
    query = (("cache-auth", "CacheAuthorization"), ("aggregate-auth", "AggregateAuthorization"),
             ("aggregate-start", "AggregateStart"), ("aggregate-end", "AggregateEnd"),
             ("lease-resource", "LeaseResource"))
    if original:
        prefix = "Hoard.Metadata.Tests."
        for shape, value in continuation:
            identity = (prefix + "MetadataPagingTests."
                        "MP08_Malformed_continuation_fields_reject_input_and_preserve_valid_resume"
                        + f'(shape: "{shape}")')
            expected[identity] = ((0, "continuation-corruption", value),)
        for shape, value in query:
            identity = (prefix + "MetadataFailureTests."
                        "MP21_Corrupt_query_dimensions_cannot_disappear_behind_page_filters"
                        + f'(shape: "{shape}")')
            expected[identity] = ((0, "query-corruption", value),)
        expected[prefix + "MetadataLeaseTests."
                 "MP29_Expiry_is_rechecked_at_the_final_decision_for_renew_release_and_guards"] = tuple(
                     (index, "lease-expiry", value) for index, value in enumerate(("Renew", "Release", "Guard")))
        expected[prefix + "MetadataSchemaTests."
                 "MP33_Unrelated_and_partial_layouts_are_not_empty_or_permission_to_create"] = (
                     (0, "schema-layout", "unrelated"), (1, "schema-layout", "partial"))
    else:
        prefix = "Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
        for provider in ("memory", "sqlite"):
            for method, kind, values in (
                    ("Observed_continuation_corruption_preserves_actual_pages", "continuation-corruption",
                     tuple(value for _, value in continuation)),
                    ("Observed_query_corruption_preserves_actual_dimensions", "query-corruption",
                     tuple(value for _, value in query))):
                for value in values:
                    expected[prefix + method + f'(provider: "{provider}", corruption: {value})'] = ((0, kind, value),)
            method = prefix + "Observed_factories_execute_unchanged_common_consumers_with_actual_origins"
            for consumer, kind, value in (
                    ("lease-renew", "lease-expiry", "Renew"), ("lease-release", "lease-expiry", "Release"),
                    ("lease-guard", "lease-expiry", "Guard"), ("layout-empty", "schema-layout", "unrelated"),
                    ("layout-partial", "schema-layout", "partial")):
                expected[method + f'(provider: "{provider}", consumer: "{consumer}")'] = ((0, kind, value),)
    if expected.keys() != set(identities):
        raise ConformanceError("WitnessMissing")
    return MappingProxyType(expected)


def hook_admission_tests(profile):
    if profile not in ("metadata", "artifacts"):
        raise ConformanceError("WitnessMissing")
    fixture = "Metadata" if profile == "metadata" else "Artifact"
    providers = ("memory", "sqlite") if profile == "metadata" else ("local", "object")
    method = ("Hoard.Fixtures.Conformance.Consumer." + fixture
              + "ConformanceSessionTests.Missing_hooks_reject_before_dispatch_and_actual_binding_passes")
    return MappingProxyType({
        method + f'(provider: "{provider}")': (provider, "QC-05") for provider in providers})


ORIGINAL_INSPECTION_LITERAL_WITNESSES = tuple(sorted(
    "Hoard.Architecture.Tests.MetadataBoundaryTests." + method for method in (
        "Native_only_packages_cannot_hide_managed_assets",
        "Package_groups_follow_actual_resolved_assets_not_a_guessed_framework",
        "Pruned_dependency_needs_sdk_evidence_a_compatible_version_and_an_actual_framework_reference",
    )))
ORIGINAL_INSPECTION_WITNESSES = MappingProxyType({
    **{identity: "metadata" for identity in ORIGINAL_INSPECTION_LITERAL_WITNESSES},
    "Hoard.Architecture.Tests.MetadataBoundaryTests."
    "Prepared_metadata_packages_and_negative_contracts_preserve_boundaries_and_binary_surface": "metadata",
    **{"Hoard.Architecture.Tests.ArtifactBoundaryTests." + method: "artifacts" for method in (
        "Prepared_artifact_consumer_bodies_are_provider_neutral_and_object_mechanisms_do_not_rename",
        "Prepared_artifact_packages_preserve_independence_and_existing_public_members",
    )},
})
ORIGINAL_ARTIFACT_PROOF_SOURCES = MappingProxyType({
    **{"Hoard.Artifacts.Tests.ArtifactCrashTests."
       "Real_parent_kill_and_fresh_process_reopen_preserve_exact_receipts_and_control_bytes"
       + f'(barrier: "{barrier}")': ("crash", "local", barrier)
       for barrier in ("B0", "B1", "B2", "B3", "D0", "D1")},
    **{"Hoard.Artifacts.Tests.ArtifactNonCooperativeChildTests."
       "Owned_child_retains_noncooperative_work_until_parent_termination"
       + f'(provider: "{provider}", scenario: "{scenario}")': ("retention", provider, scenario)
       for provider in ("local", "object") for scenario in ("source", "destination", "native")},
    **{"Hoard.Artifacts.Tests.ArtifactTransferProofTests."
       "Measured_transfer_binds_actual_bytes_pacing_hashes_and_os_peak"
       + f'(provider: "{provider}", size: {size})': ("transfer", provider, size)
       for provider in ("local", "object") for size in (268435456, 4294967296)},
})

METADATA_RECOVERY_SOURCE_WITNESS = (
    "Hoard.Conformance.Tests.MetadataRecoveryRuntimeTests."
    "Complete_current_input_native_recovery_graph_preserves_all_barriers_and_readbacks")

METADATA_INVENTORY_SOURCE_WITNESSES = MappingProxyType({
    binding: "Hoard.Conformance.Tests.MetadataInventoryRuntimeTests."
    + binding.capitalize() + "_current_input_inventory_preserves_named_assertion_and_same_source_repair"
    for binding in ("sqlite", "memory")})

_ORIGINAL_METADATA_ROLES = ("owner", "store", "schema", "authority", "controls")
_ORIGINAL_ARTIFACT_ROLES = ("owner", "store", "validator", "maintenance", "lifetime", "authority", "controls")
ORIGINAL_METADATA_FORESTS = MappingProxyType({
    "Hoard.Metadata.Tests.MetadataHostIntegrationTests."
    "MP46_Configured_selection_uses_existing_lifecycle_and_has_no_routes_or_fallback": (None, None),
    "Hoard.Metadata.Tests.MetadataLeaseTests."
    "MP29_Expiry_is_rechecked_at_the_final_decision_for_renew_release_and_guards": (None, None, None),
    "Hoard.Metadata.Tests.MetadataPagingTests."
    "MP08_Continuation_is_bound_to_scope_size_and_epoch_and_is_not_a_snapshot": (None, None),
    "Hoard.Metadata.Tests.MetadataSchemaTests."
    "MP33_Unrelated_and_partial_layouts_are_not_empty_or_permission_to_create": (None, None),
    "Hoard.Metadata.Tests.MetadataSchemaTests."
    "MP32_Old_schema_requires_explicit_authorized_upgrade_and_preserves_records": (None, 0, 1),
    "Hoard.Metadata.Tests.MetadataSchemaTests."
    "MP33_Future_schema_and_recognized_corruption_are_never_created_over": (None, None, 0, 1),
    "Hoard.Metadata.Tests.MetadataSchemaTests."
    "MP34_Unsupported_and_foreign_upgrade_authorizations_leave_old_state_unchanged": (None, 0),
    "Hoard.Metadata.Tests.MetadataSchemaTests."
    "MP35_Upgrade_exclusion_prevents_partial_admission_and_has_one_winner": (None, 0),
})
ORIGINAL_METADATA_SCHEMA_WITNESSES = tuple(
    identity for identity in ORIGINAL_METADATA_FORESTS if ".MetadataSchemaTests." in identity)
ORIGINAL_METADATA_FACADE_WITNESSES = tuple(sorted(
    "Hoard.Metadata.Tests." + fixture + "." + method
    for fixture, methods in (
        ("MetadataRoundTripTests", ("MP01_Every_entity_round_trips_and_invalid_relationships_leave_no_changes",)),
        ("MetadataIdentityTests", ("MP02_Registry_identity_is_exact_and_isolated",
                                   "MP03_Anonymous_and_authenticated_request_partitions_remain_separate")),
        ("MetadataRelationshipTests", ("MP13_Explicit_final_graph_deletion_and_disabled_retention_are_atomic",)),
        ("MetadataPublicationTests", (
            "MP23_Publication_requires_committed_matching_authority_evidence",
            "MP24_Entry_edges_replace_remove_and_compete_without_double_counts",
            "MP25_Zero_reference_confirmation_is_invalidated_even_by_ABA",
            "MP26_Blob_commit_then_metadata_failure_is_an_orphan_not_a_blob_rollback",
            "MP27_Protection_survives_caller_timeout_through_owned_settlement",
            "MP31_Invalid_telemetry_rolls_back_its_declared_entry_and_reference_group")),
        ("MetadataReconciliationTests", ("MP14_Replay_returns_original_receipt_and_changed_payload_conflicts",)),
        ("MetadataPagingTests", (
            "MP07_All_seven_query_kinds_keep_scope_and_tuple_order",
            "MP07_Oversized_requests_and_results_fail_whole_instead_of_truncating")),
    ) for method in methods)) + tuple(
        "Hoard.Metadata.Tests.MetadataFailureTests."
        f'MP21_Corrupt_query_dimensions_cannot_disappear_behind_page_filters(shape: "{shape}")'
        for shape in ("cache-auth", "aggregate-auth", "aggregate-start", "aggregate-end", "lease-resource"))
ORIGINAL_METADATA_WITNESSES = tuple(sorted((
    *ORIGINAL_METADATA_FACADE_WITNESSES,
    *ORIGINAL_METADATA_FORESTS,
    *("Hoard.Metadata.Tests.MetadataPagingTests."
      f'MP08_Malformed_continuation_fields_reject_input_and_preserve_valid_resume(shape: "{shape}")'
      for shape in ("null", "omitted", "wrong-type", "empty", "odd-hex", "invalid-hex")),
    *("Hoard.Metadata.Tests." + fixture + "." + method
      for fixture, methods in (
          ("MetadataRoundTripTests", (
              "MP05_Exact_bounds_and_overflow_reject_the_entire_candidate",
              "MP06_Scopes_and_intervals_cannot_cross_registry_boundaries")),
          ("MetadataIdentityTests", (
              "MP04_Canonical_text_is_not_normalized_and_forbidden_credentials_are_rejected",)),
          ("MetadataAdmissionTests", (
              "MP32_Ordinary_use_requires_explicit_schema_admission",
              "MP19_Invalid_budgets_and_closed_instances_do_not_dispatch_work")),
          ("MetadataAtomicityTests", (
              "MP09_Independent_engine_reads_cannot_see_an_uncommitted_candidate",
              "MP09_Each_faulted_candidate_is_invisible_and_success_is_complete",
              "MP10_Grouped_reads_keep_one_root_while_independent_reads_can_straddle",
              "MP11_Competing_creates_have_one_winner",
              "MP12_Revision_races_and_delete_recreate_are_fenced")),
          ("MetadataDeadlineTests", (
              "MP19_Actual_writer_contention_consumes_the_original_budget_without_committing",
              "MP37_Incomplete_cleanup_reports_failure_and_keeps_activity_owned",
              "MP18_Cancellation_before_decision_is_definite_and_after_attempt_is_uncertain",
              "MP19_Queue_capacity_and_held_work_deadlines_have_finite_owned_results",
              "MP37_Disposal_owns_active_work_and_does_not_release_it_early",
              "MP18_Known_exception_types_after_commit_attempt_are_still_uncertain")),
          ("MetadataReconciliationTests", (
              "MP15_Corrupt_persisted_receipts_fail_reconciliation_and_replay_without_duplicate_effects",
              "MP15_Reconciliation_io_failure_preserves_the_unresolved_original_ticket",
              "MP15_Reconciliation_without_exclusion_is_uncertain_not_a_noncommit_result",
              "MP15_Lost_acknowledgment_reconciles_and_abandonment_fences_execution",
              "MP16_Distinct_contributions_sum_and_uncertain_retries_do_not_duplicate",
              "MP17_Exact_ticket_expiry_and_clock_rollback_cannot_revive_a_ticket")),
          ("MetadataFailureTests", (
              "MP20_Injected_storage_capacity_rolls_back_and_allows_same_ticket_retry",
              "MP20_Live_ledger_capacity_is_classified_without_evicting_a_receipt",
              "MP21_Absence_succeeds_but_corruption_fails_the_complete_group",
              "MP21_Stored_page_corruption_fails_whole_and_preserves_data",
              "MP22_Diagnostics_and_all_failure_shapes_are_sanitized")),
          ("MetadataPagingTests", ("MP07_Bounded_datasets_traverse_once_without_truncation",)),
          ("MetadataLeaseTests", (
              "MP28_Generation_overflow_rejects_the_whole_group_and_preserves_tombstone",
              "MP28_Lease_owners_generations_and_revisions_are_fenced",
              "MP30_Clock_rollback_does_not_undo_expiry_and_new_generation_is_retained")),
      ) for method in methods))))
ORIGINAL_ARTIFACT_CONTRACT_WITNESSES = tuple(sorted((
    *("Hoard.Artifacts.Tests.ArtifactValueTests." + method for method in (
        "Expectations_and_checksums_copy_input_and_reject_each_bound",
        "Public_diagnostic_formatting_is_redacted_and_contract_members_are_get_only")),
    *("Hoard.Artifacts.Tests.ArtifactContractTests." + method for method in (
        "Marker_and_historical_digest_remain_separate_from_operational_contracts",
        "Qualification_exclusions_cannot_exchange_simulated_and_durable_failure_models",
        "Flat_case_names_and_unattributed_hashes_cannot_claim_qualification",
        "Qualification_case_results_reject_missing_or_unbounded_attribution",
        "Qualification_records_keep_case_proofs_and_environment_attributable_and_immutable",
        "Qualification_environment_is_bounded_unambiguous_and_redacted")),
)))
ORIGINAL_ARTIFACT_SHARED_OWNER_WITNESSES = tuple(sorted((
    *("Hoard.Artifacts.Tests.ArtifactAuthorityTests." + method for method in (
        "Copied_foreign_changed_scope_and_disposed_handles_never_authorize_retention",
        "Held_same_operation_can_settle_after_expiry_without_reentrant_admission",
        "Queued_exclusive_admission_closes_new_shared_admission_and_retention_never_reenters")),
    "Hoard.Artifacts.Tests.ArtifactMetadataAuthorityTests.Mismatched_authority_composition_cannot_substitute_field_equivalent_protection",
)))
ORIGINAL_ARTIFACT_MODULE_OWNER_WITNESSES = tuple(
    'Hoard.Artifacts.Tests.ArtifactCompositionTests.Configured_selection_is_inert_until_start_and_missing_guarantees_block_readiness'
    f'(provider: "{provider}")' for provider in ("local", "object"))
ORIGINAL_ARTIFACT_FIXED_BINDINGS = MappingProxyType({
    **{f"Hoard.Artifacts.Tests.{fixture}.{method}": provider
       for fixture, method, provider in (
           ("ArtifactEvidenceTests", "Local_failed_quarantine_persistence_retains_ownership_until_stop_retry_and_reopen", "local"),
           ("ArtifactFailureTests", "Reused_object_receipt_survives_failed_unselected_assembly_cleanup", "object"),
           ("ArtifactReadVerificationTests", "Local_reconciliation_cannot_finalize_after_overlapping_read_quarantines_the_incarnation", "local"),
           ("ArtifactRecoveryTests", "Stop_retains_unselected_object_ownership_and_retries_only_its_private_payload", "object"),
           ("ArtifactVisibilityTests", "Local_publication_is_directly_visible_before_acknowledgment", "local"),
           ("ArtifactVisibilityTests", "Delayed_object_listing_does_not_block_direct_publication_or_establish_absence", "object"),
           ("ArtifactVisibilityTests", "Object_commit_waits_for_direct_availability_while_listing_is_independently_observable", "object"))},
    **{f'Hoard.Artifacts.Tests.ArtifactFailureTests.Unselected_object_cleanup_retains_exact_ownership_and_blocks_retry_until_reclaimed(boundary: "{boundary}", cancel: {cancel})': "object"
       for boundary in ("object.commit-progress", "pointer.compare") for cancel in ("False", "True")},
})
ORIGINAL_ARTIFACT_WITNESSES = tuple(sorted((
    *ORIGINAL_ARTIFACT_FIXED_BINDINGS,
    *ORIGINAL_ARTIFACT_MODULE_OWNER_WITNESSES,
    *(f'Hoard.Artifacts.Tests.{fixture}.{method}(provider: "{provider}")'
    for fixture, methods in (
        ("ArtifactPublicationTests", (
        "Empty_content_and_true_absence_are_distinct",
        "Empty_unknown_length_and_positive_short_reads_require_real_eof",
        "Every_expectation_is_checked_and_declared_length_does_not_replace_eof",
        "Unsupported_checksum_and_range_reject_before_storage_or_stream_io",
        "Staging_is_private_until_complete_verified_commit",
        "Submitted_duplicates_are_fully_verified_and_keep_one_immutable_incarnation")),
        ("ArtifactDeletionTests", (
            "Lost_delete_acknowledgment_preserves_pending_reclamation_until_actual_cleanup",
            "Exact_delete_receipts_and_recreation_never_remove_the_new_incarnation",
            "Live_reference_or_unavailable_reference_authority_denies_removal",
            "A_held_reader_finishes_before_exclusive_deletion_and_later_opens_cannot_enter")),
        ("ArtifactReconciliationTests", (
            "Finalized_mutation_retries_preserve_expiry_and_foreign_ticket_failures",
            "Acknowledged_commit_reconciles_and_retries_one_identical_receipt_without_new_source",
            "Lost_acknowledgment_never_becomes_rollback_or_another_publication",
            "Expired_history_cannot_be_revived_by_clock_rollback_or_foreign_epoch")),
        ("ArtifactReadVerificationTests", (
            "Admitted_open_rechecks_quarantine_before_delivering_a_session",
            "Destination_failure_and_second_copy_never_return_verified_completion_or_dispose_borrowed_streams")),
        ("ArtifactPublicationRaceTests", (
            "Equivalent_concurrent_writers_keep_one_stamp_and_distinct_receipts",
            "Conflicting_staged_length_cannot_replace_valid_content_or_its_stamp",
            "Corrupt_existing_bytes_are_not_overwritten_or_reused")),
        ("ArtifactFailureTests", (
            "Storage_failures_remain_distinct_and_sanitized_and_do_not_publish_partial_content",
            "Unexpected_fault_after_visibility_requires_exact_ticket_reconciliation",
            "Committed_receipts_remain_reconcilable_while_exact_residual_staging_is_reclaimed",
            "Failed_prefix_reclamation_retains_ownership_until_exact_bounded_cleanup",
            "Stop_retains_failed_prefix_ownership_until_reclamation_can_settle")),
        ("ArtifactEvidenceTests", (
            "Only_exact_current_receipts_with_opaque_same_operation_protection_validate",)),
        ("ArtifactAdmissionTests", (
            "Before_admission_and_with_mismatched_authority_no_source_or_directory_is_touched",
            "Symlinked_root_or_ancestor_is_rejected_without_touching_outside_sentinel")),
        ("ArtifactCompositionTests", (
            "Configured_singleton_selection_recovers_and_restarts_explicitly",)),
        ("ArtifactNonCooperationTests", (
            "Idle_read_expiry_fences_copy_without_touching_the_destination",
            "Concurrent_close_waits_for_the_same_physical_guard_release_and_fences_new_copy",
            "Deadline_and_stop_return_while_a_native_io_boundary_holds_provider_state",
            "Noncooperative_source_retains_bounded_ownership_and_blocks_admission_until_real_settlement",
            "Noncooperative_destination_cannot_release_live_read_protection_via_close_or_dispose")),
        ("ArtifactBudgetTests", (
            "Reclaimed_identity_history_has_a_finite_budget_and_expiry_restores_new_digest_admission",
            "History_candidate_pages_resume_past_ineligible_entries_and_preserve_a_faulted_candidate",
            "Producer_and_consumer_inactivity_deadlines_release_cooperative_work_without_closing_borrowed_streams",
            "Cancellation_of_an_admitted_commit_cannot_fence_an_externally_renewed_owner",
            "Cancellation_after_resource_release_cannot_retain_an_already_settled_operation",
            "Undelivered_verified_staging_is_reclaimed_after_ownership_expiry",
            "Full_transfer_queue_rejects_without_input_io_and_capacity_returns_after_release",
            "Cap_crossing_rejects_excess_before_append_and_capacity_recovers",
            "Total_deadline_includes_shared_authority_contention_before_publication",
            "Cooperative_cancellation_stops_input_without_disposing_borrowed_stream")),
        ("ArtifactRecoveryTests", (
            "Sequential_recovery_retires_consumed_cursors_without_starving_independent_scans",
            "Expired_reclaimed_history_remains_owned_until_the_admitted_delete_physically_settles",
            "Late_cleanup_rechecks_the_exact_generation_after_replacement",
            "Changed_inventory_rejects_old_continuations_and_fresh_pages_cover_every_current_identity",
            "Progressing_commit_renews_owner_across_the_original_ttl",
            "Expiry_cleanup_and_restage_fence_the_old_generation",
            "Recovery_pages_are_bounded_query_bound_and_not_deletion_authority")),
    ) for method in methods
    for provider in ("local", "object")),
    *(f'Hoard.Artifacts.Tests.ArtifactBudgetTests.{method}(provider: "{provider}", {parameter}: {value})'
      for method, parameter in (
          ("Expired_ticket_history_restores_write_and_delete_capacity_without_losing_committed_or_removed_identity",
           "reserveDelete"),
          ("Cancellation_at_result_handoff_cannot_discard_a_reserved_ticket_or_live_read", "readSession"),
          ("Cancellation_before_result_handoff_reclaims_the_unclaimed_ticket_or_read", "readSession"),
          ("Failed_unclaimed_result_cleanup_blocks_admission_and_stop_until_exact_retry", "readSession"),
          ("Cancelled_commit_before_decision_fences_the_ticket_and_cannot_publish_on_retry", "alreadyCancelled"))
      for provider in ("local", "object") for value in ("False", "True")),
    *(f'Hoard.Artifacts.Tests.{fixture}.{method}(provider: "{provider}", {parameter}: {value})'
      for fixture, method, parameter, values in (
          ("ArtifactReadVerificationTests",
           "Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence", "truncate", ("False", "True")),
          ("ArtifactReadVerificationTests", "Every_committed_detection_path_quarantines_restored_bytes",
           "detection", ('"open"', '"publication"', '"reconciliation"')),
          ("ArtifactEvidenceTests", "Validation_first_corruption_cannot_be_revived_by_external_restoration",
           "missing", ("False", "True")),
          ("ArtifactEvidenceTests", "Validation_access_failure_does_not_quarantine_intact_content",
           "unavailable", ("False", "True")),
          ("ArtifactCapabilityTests", "Missing_mandatory_guarantees_versions_or_authority_reject_before_io",
           "gap", tuple(f'"{gap}"' for gap in (
               "authority", "deletion", "fencing", "publication", "readers", "recovery", "streaming", "version"))))
      for provider in ("local", "object") for value in values),
    *(f'Hoard.Artifacts.Tests.ArtifactMetadataIntegrationTests.{method}(provider: "{provider}", metadataProvider: "{metadata}")'
      for method in (
          "New_reference_cannot_cross_an_admitted_zero_reference_deletion",
          "Failed_metadata_transaction_leaves_identifiable_committed_bytes_not_a_fabricated_entry",
          "Actual_metadata_references_deny_removal_until_the_reference_transaction_commits",
          "Lost_metadata_acknowledgment_keeps_real_reference_protection_until_physical_settlement")
      for provider in ("local", "object") for metadata in ("memory", "sqlite")),
)))
ORIGINAL_ARTIFACT_BINDINGS = MappingProxyType({
    **{identity: provider for identity in ORIGINAL_ARTIFACT_WITNESSES
       for provider in ("local", "object") if f'(provider: "{provider}"' in identity},
    **ORIGINAL_ARTIFACT_FIXED_BINDINGS,
})
ORIGINAL_ARTIFACT_REOPENS = MappingProxyType({
    identity: (None, 0) for identity in ORIGINAL_ARTIFACT_WITNESSES
    if ORIGINAL_ARTIFACT_BINDINGS[identity] == "local" and 'detection: "reconciliation"' not in identity
    and any(method in identity for method in (
        ".Local_failed_quarantine_persistence_retains_ownership_until_stop_retry_and_reopen",
        ".Stop_retains_failed_prefix_ownership_until_reclamation_can_settle(",
        ".Corrupt_existing_bytes_are_not_overwritten_or_reused(",
        ".Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence(",
        ".Every_committed_detection_path_quarantines_restored_bytes(",
        ".Validation_first_corruption_cannot_be_revived_by_external_restoration("))
})
ORIGINAL_ARTIFACT_FORESTS = MappingProxyType({
    **ORIGINAL_ARTIFACT_REOPENS,
    **{identity: (None, None) for identity in ORIGINAL_ARTIFACT_WITNESSES
       if ".Configured_singleton_selection_" in identity},
    "Hoard.Artifacts.Tests.ArtifactAuthorityTests.Copied_foreign_changed_scope_and_disposed_handles_never_authorize_retention": (None, None),
})


def original_witness_policy(identity):
    """Select original instance/contract attribution, distinct from non-session proofs."""
    if composition_snapshot_policy(identity) is not None:
        return "composition", "original-owner", ("owner",)
    contracts = (*ORIGINAL_ARTIFACT_CONTRACT_WITNESSES,
                 "Hoard.Artifacts.Tests.ArtifactValueTests.Identity_bounds_preserve_empty_and_reject_overflow_negative_or_null")
    if identity in ORIGINAL_METADATA_WITNESSES:
        return "metadata", "original-instance", _ORIGINAL_METADATA_ROLES
    if identity in contracts or identity in AUTHORITY_INTEGRATION_ROWS:
        return "artifacts", "loaded-contract", ("contract",)
    if identity in (*ORIGINAL_ARTIFACT_SHARED_OWNER_WITNESSES, *ORIGINAL_ARTIFACT_MODULE_OWNER_WITNESSES):
        return "artifacts", "original-owner", ("owner",)
    if identity in ORIGINAL_ARTIFACT_WITNESSES:
        return "artifacts", "original-instance", _ORIGINAL_ARTIFACT_ROLES
    return None


def original_non_session_policy(identity):
    """A provider session cannot stand in for an inspection or controller proof."""
    for profile in CATEGORY_MUTATION_METHODS:
        if identity in category_mutation_witnesses(profile, corrected=True):
            return profile, "mutation"
    if identity == METADATA_RECOVERY_SOURCE_WITNESS:
        return "metadata", "recovery"
    if identity in METADATA_INVENTORY_SOURCE_WITNESSES.values():
        return "metadata", "inventory"
    category = ORIGINAL_INSPECTION_WITNESSES.get(identity)
    if category is not None:
        return category, "inspection"
    source = ORIGINAL_ARTIFACT_PROOF_SOURCES.get(identity)
    return None if source is None else ("artifacts", source[0])


def original_witness_parents(identity):
    """The independently selected creation/reopen forest for one exact execution."""
    if original_witness_policy(identity) is None:
        return None
    owners = composition_snapshot_owner_indices(identity)
    if owners is not None:
        return (None,) * (max(owners) + 1)
    if identity in AUTHORITY_INTEGRATION_ROWS:
        return None, None, None
    return ORIGINAL_METADATA_FORESTS.get(identity, ORIGINAL_ARTIFACT_FORESTS.get(identity, (None,)))


def category_runtime_packages(inputs, selected_bindings):
    """Select provider archives independently from the executing SDK wrapper."""
    slots = {binding: package for profile, binding, _, package in CATEGORY_BINDING_SLOTS
             if profile == inputs["profileId"]}
    bindings = {binding["bindingId"]: binding for binding in inputs["bindings"]}
    packages = {package["packageId"].casefold(): package for package in inputs["packages"]}
    selected = frozenset(selected_bindings)
    if (not selected or not selected <= slots.keys() or not selected <= bindings.keys()
            or len(bindings) != len(inputs["bindings"]) or len(packages) != len(inputs["packages"])):
        raise ConformanceError("BindingInvalid")
    for binding_id in selected:
        binding = bindings[binding_id]
        if (binding["category"] != inputs["profileId"]
                or binding["package"]["packageId"].casefold() != slots[binding_id].casefold()
                or packages.get(slots[binding_id].casefold()) != binding["package"]):
            raise ConformanceError("BindingInvalid")
    return MappingProxyType({binding: bindings[binding]["package"] for binding in sorted(selected)})


def category_runtime_cases(profile, binding_id, *, mode="diagnostic"):
    """Select the same primary frozen case for manifest construction and admission."""
    if profile not in ("metadata", "artifacts"):
        raise ConformanceError("UnsupportedProfile")
    if mode not in ("diagnostic", "qualification"):
        raise ConformanceError("EvidenceSchemaInvalid")
    cases = tuple(case for case in expected_cases(profile) if case.binding_id == binding_id)
    if not cases:
        raise ConformanceError("BindingInvalid")
    applicable = tuple(case for case in cases if case.exclusion is None and case.binding_id != "none")
    selected = {
        identity: min(case.case_id for case in applicable if identity in case.witnesses)
        for identity in {identity for case in applicable for identity in case.witnesses}}
    if profile == "metadata" and binding_id == "sqlite" and mode == "qualification":
        selected[METADATA_RECOVERY_SOURCE_WITNESS] = min(
            case.case_id for case in applicable if "verified-recovery-walkthrough" in case.controls
            or any(control.startswith("parent-kill:") for control in case.controls))
    if profile == "metadata" and binding_id in METADATA_INVENTORY_SOURCE_WITNESSES and mode == "qualification":
        selected[METADATA_INVENTORY_SOURCE_WITNESSES[binding_id]] = "MP-48"
    if profile == "artifacts" and mode == "qualification":
        selected.update({identity: "QC-12" for identity, row in AUTHORITY_INTEGRATION_ROWS.items()
                         if row[0] == binding_id})
    if mode == "qualification":
        selected.update({identity: "QC-04" for identity, binding in category_mutation_witnesses(
            profile, corrected=True).items() if binding == binding_id})
        selected.update({identity: case_id for identity, (binding, case_id) in hook_admission_tests(profile).items()
                         if binding == binding_id})
    return MappingProxyType(selected)


def category_execution_partitions(profile, *, mode="diagnostic"):
    """Keep complete method families together without merging repeated binding contexts."""
    if profile not in ("metadata", "artifacts"):
        raise ConformanceError("UnsupportedProfile")
    rows = tuple(sorted((binding, identity) for category, binding, _, _ in CATEGORY_BINDING_SLOTS
                        if category == profile for identity in category_runtime_cases(profile, binding, mode=mode)))
    repeated = {identity for identity, count in Counter(identity for _, identity in rows).items() if count > 1}
    scopes = {}
    for binding, identity in rows:
        policy = original_witness_policy(identity)
        if identity == METADATA_RECOVERY_SOURCE_WITNESS:
            scope = "recovery-controller"
        elif identity in METADATA_INVENTORY_SOURCE_WITNESSES.values():
            scope = "inventory-controller"
        elif identity in AUTHORITY_INTEGRATION_ROWS:
            scope = "original-integration"
        elif identity in category_mutation_witnesses(profile, corrected=True):
            scope = "mutation-repair"
        elif identity in hook_admission_tests(profile):
            scope = "hook-admission"
        elif policy is not None and policy[0] == profile:
            scope = "original-" + binding if identity in repeated else "original"
        elif ORIGINAL_INSPECTION_WITNESSES.get(identity) == profile:
            scope = ("inspection-literals-" if identity in ORIGINAL_INSPECTION_LITERAL_WITNESSES
                     else "inspection-prepared-") + binding
        elif profile == "artifacts" and identity in ORIGINAL_ARTIFACT_PROOF_SOURCES:
            scope = "controller"
        else:
            raise ConformanceError("WitnessMissing")
        scopes.setdefault(scope, []).append((binding, identity))
    return MappingProxyType({scope: tuple(selected) for scope, selected in sorted(scopes.items())})


@dataclass(frozen=True)
class ExpectedCase:
    profile_id: str
    binding_id: str
    matrix_id: str
    case_id: str
    witnesses: tuple[str, ...]
    controls: tuple[str, ...] = ()
    exclusion: str | None = None

    def __post_init__(self):
        if self.profile_id not in PROFILES or self.exclusion not in (
                None, "non-durable fixture", "simulation: no durable restart"):
            raise ConformanceError()
        for dimension in self.key:
            stable_id(dimension)
        for field in ("witnesses", "controls"):
            names = getattr(self, field)
            if (not isinstance(names, (list, tuple)) or len(names) > MAX_WITNESSES
                    or any(not isinstance(name, str) or not 0 < len(name) <= 1024
                           or any(character < " " or character > "~" for character in name) for name in names)
                    or len(set(names)) != len(names)):
                raise ConformanceError()
            object.__setattr__(self, field, tuple(names))
        if not self.witnesses and not self.controls and self.exclusion is None:
            raise ConformanceError("WitnessMissing")
        if len(self.witnesses) + len(self.controls) > MAX_WITNESSES:
            raise ConformanceError("EvidenceIncomplete")

    @property
    def key(self):
        return self.profile_id, self.binding_id, self.matrix_id, self.case_id


COMPOSITIONS = (
    ("CP-01", ("baseline",)),
    ("CP-02", ("replacement",)),
    ("CP-03", ("multiple",)),
    ("CP-04", ("duplicate",)),
    ("CP-05", ("unknown",)),
    ("CP-06", ("missing-required",)),
    ("CP-07", ("cycle-forward", "cycle-reversed")),
    ("CP-08", ("missing-capability",)),
    ("CP-09", ("metadata-zero", "metadata-two")),
    ("CP-10", ("artifacts-zero", "artifacts-two")),
    ("CP-11", ("route-conflict",)),
    ("CP-12", ("optional-absent", "optional-disabled")),
    ("CP-13", ("optional-compatible", "optional-incompatible")),
    ("CP-14", ("initializer-failed",)),
    ("CP-15", ("cancel-initialization", "cancel-readiness")),
    ("CP-16", ("late-initialization",)),
    ("CP-17", ("stop-fault", "late-stop")),
    ("CP-18", ("recovery-failed",)),
    ("CP-19", ("authority-mismatch", "missing-guarantee")),
    ("CP-20", ("settled-restart", "active-config")),
)

# Each row is exercised through the existing Hosting version validator.
VERSION_ROWS = (
    ("inclusive-lower", "[0.1.0,0.2.0)", "0.1.0", False, True),
    ("exclusive-upper", "[0.1.0,0.2.0)", "0.2.0", False, False),
    ("exclusive-lower", "(0.1.0,0.2.0]", "0.1.0", False, False),
    ("inclusive-upper", "(0.1.0,0.2.0]", "0.2.0", False, True),
    ("build", "[0.1.0]", "0.1.0+build.7", False, True),
    ("prerelease-off", "[0.1.0,0.2.0)", "0.1.1-rc.1", False, False),
    ("prerelease-on", "[0.1.0,0.2.0)", "0.1.1-rc.1", True, True),
    ("below-stable", "[0.1.1,0.2.0)", "0.1.1-rc.1", True, False),
    ("prerelease-range-off", "[0.1.1-rc.1,0.1.1]", "0.1.1-rc.2", False, False),
    ("prerelease-range-on", "[0.1.1-rc.1,0.1.1]", "0.1.1-rc.2", True, True),
    ("upper-prerelease-off", "[0.1.0,0.2.0)", "0.2.0-rc.1", False, False),
    ("upper-prerelease-on", "[0.1.0,0.2.0)", "0.2.0-rc.1", True, True),
    ("case", "[0.1.1-RC.1]", "0.1.1-rc.1", True, True),
    ("empty", "", "0.1.1", False, False),
    ("floating", "1.*", "0.1.1", False, False),
    ("unbounded", "[0.1.0,)", "0.1.1", False, False),
    ("reversed", "[0.2.0,0.1.0]", "0.1.1", False, False),
    ("empty-open", "(0.1.0,0.1.0)", "0.1.1", False, False),
    ("unnormalized", "[0.1]", "0.1.1", False, False),
    ("four-part", "[0.1.0,0.2.0)", "0.1.0.0", False, False),
    ("malformed", "[0.1.0,0.2.0)", "malformed-canary", False, False),
)

VERSION_RUNTIME_ROWS = {
    "inclusive-lower": "inclusive-lower", "exclusive-upper": "exclusive-upper",
    "exclusive-lower": "exclusive-lower", "inclusive-upper": "inclusive-upper",
    "build": "exact-build", "prerelease-off": "rc-blocked", "prerelease-on": "rc-enabled",
    "below-stable": "below-stable-lower", "prerelease-range-off": "range-not-opt-in",
    "prerelease-range-on": "rc-range-enabled", "upper-prerelease-off": "upper-rc-blocked",
    "upper-prerelease-on": "upper-rc-enabled", "case": "case-precedence",
    "empty": "empty", "floating": "floating", "unbounded": "unbounded", "reversed": "reversed",
    "empty-open": "empty-open", "unnormalized": "short-range",
    "four-part": "four-part-candidate", "malformed": "unsafe-candidate",
}


def independent_version_witnesses(name):
    prefix = "Hoard.Composition.Tests.ConformanceVersionTests."
    flags = prefix + "Platform_prerelease_flags_are_independent"
    inherited = prefix + "Inherited_platform_flags_do_not_derive_from_module_version"
    optional = prefix + "Incompatible_optional_target_is_unavailable_not_an_active_edge_or_capability"
    return {
        "host-only-flag": (f"{flags}(host: True, abstractions: False)",
                           f'{inherited}(id: "C-11", host: True, abstractions: False)'),
        "abstractions-only-flag": (f"{flags}(host: False, abstractions: True)",),
        "module-no-platform-flag": (
            f"{flags}(host: False, abstractions: False)", f"{flags}(host: True, abstractions: True)",
            f'{inherited}(id: "C-18", host: False, abstractions: False)'),
        "optional-absent": (f'{optional}(selection: "absent")',),
        "optional-disabled": (f'{optional}(selection: "registered-disabled")',),
    }[name]


def version_observation_policy(identity):
    prefix = "Hoard.Composition.Tests.ConformanceVersionTests."
    if not identity.startswith(prefix):
        return None
    for axis in ("host", "abstractions", "required", "optional"):
        for name, _, _, _, accepted in VERSION_ROWS:
            if identity != prefix + f'Runtime_matrix(axis: "{axis}", row: "{VERSION_RUNTIME_ROWS[name]}")':
                continue
            primary = ("runtime", {"accepted": int(accepted), "constructors": 0,
                                   "diagnostics": 0 if accepted else (1, 128)})
            return (primary,) if accepted else (
                ("repair", {"accepted": 1, "constructors": 0, "diagnostics": 0,
                            "activeEdges": int(axis in ("required", "optional"))}), primary)
    for host in (False, True):
        for abstractions in (False, True):
            if identity == prefix + (
                    f"Platform_prerelease_flags_are_independent(host: {host}, abstractions: {abstractions})"):
                return (("platform-flags", {"accepted": int(host and abstractions), "constructors": 0}),)
    for selection in ("absent", "registered-disabled"):
        if identity == prefix + (
                f'Incompatible_optional_target_is_unavailable_not_an_active_edge_or_capability(selection: "{selection}")'):
            return (("optional", {"activeEdges": 0, "capabilities": 0, "capabilityRejections": 1}),)
    for case_id in dict.fromkeys("C-14" if row[0] == "C-14-outside" else row[0]
                                for row in CLASSIFICATION_RUNTIME_ROWS):
        if identity in classification_witnesses(case_id):
            matching = next(item for item in CLASSIFICATION_RUNTIME_ROWS
                            if f'(id: "{item[0]}",' in identity)
            accepted = matching[-1]
            return (("classification", {"accepted": int(accepted),
                                        "diagnostics": 0 if accepted else (1, 128)}),)
    for case_id in ("C-11", "C-18"):
        if identity in classification_witnesses(case_id):
            return (("platform-classification", {"accepted": 0, "unsupportedPlatform": (1, 128)}),)
    for case_id in ("C-05", "C-06", "C-16", "C-17"):
        if identity in classification_witnesses(case_id):
            return (("policy", {"policyInvalid": 1, "policyRepaired": 1, "runtimeClaims": 0}),)
    return None


def composition_snapshot_policy(identity):
    def matrix(stage, modules, *, ready=False, stopped=False, requests=0, edges=0, capabilities=0,
               rule_count=0, initialized=True, routes=None):
        return stage, MappingProxyType({
            "constructors": modules, "services": modules, "maps": modules, "requests": requests,
            "connections": modules if initialized else 0, "initializations": modules if initialized else 0,
            "assessments": modules if initialized else 0, "workers": modules if initialized else 0,
            "stops": modules if stopped else 0, "disposals": modules if stopped else 0,
            "disabledEffects": 0, "ready": int(ready), "admission": int(ready), "stopComplete": int(stopped),
            "rootDisposal": 0 if stopped else 6, "unsafeActivities": 0, "ruleCount": rule_count,
            "activeEdges": edges, "satisfiedCapabilities": capabilities,
            "publishedRoutes": modules if routes is None else routes,
        })

    endpoint_rows = composition_witnesses("CP-11", "route-conflict")[1:]
    if identity in endpoint_rows:
        modules = 3 if endpoint_rows.index(identity) % 2 == 0 else 2
        return (matrix("declaration-rejected", 0, rule_count=1),
                matrix("declaration-ready", modules, ready=True, requests=1),
                matrix("declaration-stopped", modules, stopped=True, requests=1))
    for case, variant, modules, edges, capabilities in (
            ("CP-04", "duplicate", 2, 0, 0), ("CP-05", "unknown", 2, 0, 0),
            ("CP-06", "missing-required", 3, 1, 0), ("CP-07", "cycle-forward", 2, 1, 0),
            ("CP-07", "cycle-reversed", 2, 1, 0), ("CP-08", "missing-capability", 2, 0, 1),
            ("CP-09", "metadata-zero", 2, 0, 0), ("CP-09", "metadata-two", 2, 0, 0),
            ("CP-10", "artifacts-zero", 2, 0, 0), ("CP-10", "artifacts-two", 2, 0, 0),
            ("CP-13", "optional-incompatible", 3, 1, 0)):
        if identity in composition_witnesses(case, variant):
            return (matrix("declaration-rejected", 0, rule_count=1),
                    matrix("declaration-ready", modules, ready=True, requests=1, edges=edges, capabilities=capabilities),
                    matrix("declaration-stopped", modules, stopped=True, requests=1, edges=edges, capabilities=capabilities))
    if identity in composition_witnesses("CP-03", "multiple"):
        return (matrix("multiple-ready", 6, ready=True, requests=6),
                matrix("multiple-stopped", 6, stopped=True, requests=6))
    if identity == composition_witnesses("CP-11", "route-conflict")[0]:
        rejected = matrix("mapping-rejected", 3, initialized=False, routes=0, rule_count=1)
        stopped = matrix("mapping-denial-stopped", 3, initialized=False, routes=0, rule_count=1, stopped=True)
        return ((rejected[0], MappingProxyType({**rejected[1], "stops": 3})),
                (stopped[0], MappingProxyType({**stopped[1], "disposals": 0})),
                matrix("mapping-ready", 3, ready=True, requests=2),
                matrix("mapping-stopped", 3, stopped=True, requests=2))
    if identity in (*composition_witnesses("CP-12", "optional-absent"),
                    *composition_witnesses("CP-12", "optional-disabled")):
        return (matrix("optional-unavailable", 2, ready=True),
                matrix("optional-unavailable-stopped", 2, stopped=True),
                matrix("optional-enabled", 3, ready=True, edges=1, capabilities=1),
                matrix("optional-enabled-stopped", 3, stopped=True, edges=1, capabilities=1))
    for variant, stages in (
            ("settled-restart", ("selection-fixed", "selection-stopped", "selection-restarted", "restart-stopped")),
            ("active-config", ("configuration-active", "configuration-draining", "configuration-stopped",
                               "configuration-restarted", "restart-draining", "restart-stopped"))):
        if identity not in composition_witnesses("CP-20", variant):
            continue
        configuration = variant == "active-config"
        rows = []
        for index, stage in enumerate(stages):
            restarted = index >= (3 if configuration else 2)
            stopped = stage.endswith("-stopped")
            ready = not stopped and not stage.endswith("-draining")
            rows.append((stage, MappingProxyType({
                "ready": int(ready), "admission": int(ready), "stopComplete": int(stopped),
                "rootDisposal": 0 if stopped else 6, "unsafeActivities": 0,
                "workers": 2 if configuration or not restarted else 3,
                "inactiveEffects": 0, "requests": 1 if configuration or not restarted else 3,
                "requestPending": int(configuration and not stopped),
                "requestSettled": int(configuration and stopped),
                "configurationFixed": 1, "identityChanged": int(restarted),
            })))
        return tuple(rows)
    stores = (*composition_witnesses("CP-19", "authority-mismatch"),
              *composition_witnesses("CP-19", "missing-guarantee"))
    if identity in stores:
        return tuple((stage, MappingProxyType({
            "ready": int(index == 2), "admission": int(index == 2),
            "phaseFailures": int(index < 2), "fallbackEffects": 0, "workers": 2 if index >= 2 else 0,
            "stopComplete": int(index % 2 == 1), "rootDisposal": 0 if index % 2 == 1 else 6,
            "unsafeActivities": 0, "storeBeforeRoot": int(index >= 2), "storeAdmitted": int(index >= 2),
            "storeReady": int(index == 2),
        })) for index, stage in enumerate(
            ("store-denied", "store-denial-stopped", "store-repair-admitted", "store-repair-stopped")))
    admission = (*composition_witnesses("CP-14", "initializer-failed")[1:],
                 *composition_witnesses("CP-18", "recovery-failed"))
    if identity in admission:
        return tuple((stage, MappingProxyType({
            "ready": int(index == 2), "admission": int(index == 2),
            "phaseFailures": int(index < 2), "fallbackRoots": 0, "workers": 2 if index >= 2 else 0,
            "stopComplete": int(index % 2 == 1), "rootDisposal": 0 if index % 2 == 1 else 6,
            "unsafeActivities": 0,
        })) for index, stage in enumerate(
            ("admission-denied", "denial-stopped", "repair-admitted", "repair-stopped")))
    baseline = (*composition_witnesses("CP-01", "baseline"), *composition_witnesses("CP-02", "replacement"))
    if identity in baseline:
        rows = []
        for stage in ("before-initialization", "ready", "stopped"):
            counters = {name: 0 for name in (
                "metadataSingletons", "artifactSingletons", "metadataReady", "artifactReady", "ready", "admission",
                "disabledRoots", "protocolRequests", "identityRequests", "stopComplete", "unsafeActivities")}
            counters.update(metadataSingletons=1, artifactSingletons=1)
            if stage == "ready":
                counters.update(metadataReady=1, artifactReady=1, ready=1, admission=1)
            if stage in ("ready", "stopped"):
                counters.update(protocolRequests=1, identityRequests=1)
            if stage == "stopped":
                counters["stopComplete"] = 1
            rows.append((stage, MappingProxyType(counters)))
        return tuple(rows)
    counters = {name: 0 for name in (
        "callbackSettled", "workCompleted", "workFaulted", "ready", "admission", "unsafeActivities",
        "rootDisposal", "stopComplete", "initializations", "assessments", "workers", "stops", "disposals")}
    counters["initializations"] = 1
    if identity == composition_witnesses("CP-14", "initializer-failed")[0]:
        counters.update(callbackSettled=1, workCompleted=1, workFaulted=1, rootDisposal=6, stops=1)
        stopped = {**counters, "rootDisposal": 0, "stopComplete": 1, "stops": 1, "disposals": 1}
        return (("initialization-denied", MappingProxyType(counters)),
                ("ownership-stopped", MappingProxyType(stopped)))
    for phase in ("initialization", "readiness"):
        if identity in composition_witnesses("CP-15", "cancel-" + phase):
            counters.update(rootDisposal=6, assessments=int(phase == "readiness"))
            stopped = {**counters, "callbackSettled": 1, "workCompleted": 1, "rootDisposal": 0,
                       "stopComplete": 1, "stops": 1, "disposals": 1}
            return (("caller-cancelled", MappingProxyType(counters)),
                    ("ownership-stopped", MappingProxyType(stopped)))
    for index, name in enumerate(composition_witnesses("CP-16", "late-initialization")):
        if identity == name:
            counters.update(unsafeActivities=1, rootDisposal=4)
            settled = {**counters, "callbackSettled": 1, "workCompleted": 1, "workFaulted": index}
            return (("ownership-retained", MappingProxyType(counters)),
                    ("ownership-settled", MappingProxyType(settled)))
    counters.update(assessments=1, workers=1, stops=1)
    if identity in composition_witnesses("CP-17", "stop-fault"):
        counters.update(callbackSettled=1, workCompleted=1, workFaulted=1, disposals=1)
        return (("ownership-settled", MappingProxyType(counters)),)
    for index, name in enumerate(composition_witnesses("CP-17", "late-stop")):
        if identity == name:
            counters.update(unsafeActivities=1, rootDisposal=4)
            settled = {**counters, "callbackSettled": 1, "workCompleted": 1, "workFaulted": index}
            return (("ownership-retained", MappingProxyType(counters)),
                    ("ownership-settled", MappingProxyType(settled)))
    return None


def composition_snapshot_owner_indices(identity):
    policy = composition_snapshot_policy(identity)
    if policy is None:
        return None
    if policy[0][0] == "declaration-rejected":
        return 0, 1, 1
    if policy[0][0] in ("mapping-rejected", "optional-unavailable"):
        return 0, 0, 1, 1
    if policy[0][0] == "selection-fixed":
        return 0, 0, 1, 1
    if policy[0][0] == "configuration-active":
        return 0, 0, 0, 1, 1, 1
    return (0, 0, 1, 1) if policy[0][0] in ("admission-denied", "store-denied") else (0,) * len(policy)


def composition_execution_cases():
    return MappingProxyType({
        identity: (case_id, variant + ".observe")
        for case_id, variants in COMPOSITIONS for variant in variants
        for identity in composition_witnesses(case_id, variant)})


def composition_witnesses(case_id, variant):
    prefix = "Hoard.Composition.Tests.ConformanceMatrixTests."
    declarations = {
        ("CP-04", "duplicate"): ("duplicate", "DuplicateModule"),
        ("CP-05", "unknown"): ("unknown", "UnknownSelection"),
        ("CP-06", "missing-required"): ("missing-required", "MissingDependency"),
        ("CP-07", "cycle-forward"): ("cycle-forward", "DependencyCycle"),
        ("CP-07", "cycle-reversed"): ("cycle-reordered", "DependencyCycle"),
        ("CP-08", "missing-capability"): ("missing-capability", "UnsupportedCapability"),
        ("CP-09", "metadata-zero"): ("metadata-zero", "InvalidCardinality"),
        ("CP-09", "metadata-two"): ("metadata-two", "InvalidCardinality"),
        ("CP-10", "artifacts-zero"): ("artifact-zero", "InvalidCardinality"),
        ("CP-10", "artifacts-two"): ("artifact-two", "InvalidCardinality"),
        ("CP-13", "optional-compatible"): ("optional-incompatible", "UnsupportedDependency"),
        ("CP-13", "optional-incompatible"): ("optional-incompatible", "UnsupportedDependency"),
    }
    key = case_id, variant
    if key in declarations:
        row, rule = declarations[key]
        return (prefix + "Declaration_rejection_and_single_input_repair"
                + f'(id: "{case_id}", variant: "{row}", rule: "{rule}")',)
    facts = {
        ("CP-03", "multiple"): "CP03_explicit_multiple_protocols_and_identity_schemes_start_and_stop",
        ("CP-11", "route-conflict"): "CP11_actual_route_ambiguity_rejects_before_publication_and_repair_starts",
        ("CP-18", "recovery-failed"): "CP18_real_local_recovery_rejects_corrupt_manifest_without_fallback_and_exact_repair_recovers",
        ("CP-20", "settled-restart"): "CP20_active_selection_is_immutable_and_only_fresh_settled_restart_changes_owner",
        ("CP-20", "active-config"): "CP20_active_configuration_is_fixed_until_a_fresh_explicit_restart",
    }
    if key in facts:
        witnesses = (prefix + facts[key],)
        if key == ("CP-11", "route-conflict"):
            witnesses += tuple(prefix + "Declaration_rejection_and_single_input_repair"
                + f'(id: "endpoint-declaration", variant: "{variant}", rule: "MalformedRegistry")'
                for variant in ("malformed-endpoint-enabled", "malformed-endpoint-disabled",
                                "duplicate-endpoint-enabled", "duplicate-endpoint-disabled"))
        return witnesses
    methods = {
        ("CP-01", "baseline"): (
            'Packaged_baseline_and_replacement_use_the_identical_consumer(id: "CP-01", metadata: "sqlite", '
            'artifact: "local", metadataAssembly: "Hoard.Fixtures.Metadata.Sqlite", artifactAssembly: "Hoard.Fixtures.Artifacts.Local")',),
        ("CP-02", "replacement"): (
            'Packaged_baseline_and_replacement_use_the_identical_consumer(id: "CP-02", metadata: "memory", '
            'artifact: "object", metadataAssembly: "Hoard.Fixtures.Metadata.Memory", artifactAssembly: "Hoard.Fixtures.Artifacts.ObjectSemantics")',),
        ("CP-12", "optional-absent"): (
            'CP12_disabled_effects_and_unavailable_optional_integration(target: "absent")',),
        ("CP-12", "optional-disabled"): (
            'CP12_disabled_effects_and_unavailable_optional_integration(target: "registered-disabled")',),
        ("CP-14", "initializer-failed"): (
            'Required_initialization_failure_has_no_readiness_or_fallback_and_cleans_owner(id: "CP-14", phase: "initialize")',
            'CP14_schema_admission_denies_empty_store_without_explicit_create_and_repair_succeeds(provider: "sqlite")',
            'CP14_schema_admission_denies_empty_store_without_explicit_create_and_repair_succeeds(provider: "memory")'),
        ("CP-15", "cancel-initialization"): (
            'CP15_cancelled_caller_does_not_admit_or_release_pending_shared_work(phase: "initialize")',),
        ("CP-15", "cancel-readiness"): (
            'CP15_cancelled_caller_does_not_admit_or_release_pending_shared_work(phase: "readiness")',),
        ("CP-16", "late-initialization"): (
            'CP16_noncooperative_initializer_returns_finitely_but_retains_owner_until_real_settlement(lateFault: False)',
            'CP16_noncooperative_initializer_returns_finitely_but_retains_owner_until_real_settlement(lateFault: True)'),
        ("CP-17", "stop-fault"): (
            'CP17_shutdown_fault_or_retention_never_claims_complete_cleanup(variant: "fault")',),
        ("CP-17", "late-stop"): (
            'CP17_shutdown_fault_or_retention_never_claims_complete_cleanup(variant: "noncooperative")',
            'CP17_shutdown_fault_or_retention_never_claims_complete_cleanup(variant: "noncooperative-fault")'),
        ("CP-19", "authority-mismatch"): (
            'CP19_actual_store_admission_rejects_before_io_and_paired_repair_admits(variant: "authority-identity")',),
        ("CP-19", "missing-guarantee"): (
            'CP19_actual_store_admission_rejects_before_io_and_paired_repair_admits(variant: "mandatory-guarantee")',),
    }
    if key not in methods:
        raise ConformanceError("WitnessMissing")
    return tuple(prefix + method for method in methods[key])


CLASSIFICATION_RUNTIME_ROWS = (
    ("C-01", "host", "[1.2.0,2.0.0)", "1.4.0", False, "enabled", True),
    ("C-02", "host", "[1.2.0,2.0.0)", "2.0.0", False, "enabled", False),
    ("C-03", "host", "", "1.0.0", False, "enabled", False),
    ("C-04", "host", "[0.1.0,0.2.0)", "0.2.0", False, "enabled", False),
    ("C-07", "host", "[1.0.0,2.0.0)", "1.5.0-rc.1", False, "enabled", False),
    ("C-08", "host", "[1.0.0,2.0.0)", "1.5.0-rc.1", True, "enabled", True),
    ("C-09", "host", "[1.5.0,2.0.0)", "1.5.0-rc.1", True, "enabled", False),
    ("C-10", "host", "[1.5.0-rc.1,1.5.0]", "1.5.0-rc.2", False, "enabled", False),
    ("C-12", "host", "[1.2.3]", "1.2.3+build.7", False, "enabled", True),
    ("C-13", "host", "(2.0.0,1.0.0]", "1.5.0", False, "enabled", False),
    ("C-14", "required", "[1.0.0,2.0.0)", "1.5.0", False, "absent", False),
    ("C-14-outside", "required", "[1.0.0,2.0.0)", "2.0.0", False, "enabled", False),
    ("C-15", "optional", "[1.0.0,2.0.0)", "1.5.0", False, "absent", True),
    ("C-19", "optional", "[1.0.0,2.0.0)", "1.5.0", False, "enabled", True),
    ("C-20", "optional", "[1.0.0,2.0.0)", "2.0.0", False, "enabled", False),
    ("C-21", "optional", "[1.0.0,2.0.0)", "1.5.0-rc.1", False, "enabled", False),
    ("C-22", "optional", "[1.0.0,2.0.0)", "1.5.0-rc.1", True, "enabled", True),
    ("C-23", "optional", "[1.0.0,2.0.0)", "2.0.0", False, "registered-disabled", True),
)


def classification_witnesses(case_id):
    prefix = "Hoard.Composition.Tests.ConformanceVersionTests."
    names = []
    for row in CLASSIFICATION_RUNTIME_ROWS:
        if row[0] != case_id and not (case_id == "C-14" and row[0] == "C-14-outside"):
            continue
        arguments = ", ".join(
            f"{key}: {str(value) if isinstance(value, bool) else json.dumps(value)}"
            for key, value in zip(("id", "axis", "range", "candidate", "prerelease", "selection", "accepted"),
                                  row, strict=True))
        names.append(prefix + f"Inherited_runtime_classification({arguments})")
    if names:
        return tuple(names)
    if case_id in ("C-11", "C-18"):
        host = case_id == "C-11"
        return (prefix + "Inherited_platform_flags_do_not_derive_from_module_version"
                + f'(id: "{case_id}", host: {host}, abstractions: False)',)
    policies = {"C-05": ("stable-major", "2.0.0"), "C-06": ("pre-1.0-minor", "0.2.0"),
                "C-16": ("stable-major", "2.0.0"), "C-17": ("stable-major", "2.0.0")}
    if case_id not in policies:
        raise ConformanceError("WitnessMissing")
    transition, version = policies[case_id]
    return (prefix + "Inherited_release_classifier_is_policy_not_runtime_evidence"
            + f'(id: "{case_id}", transition: "{transition}", repairedVersion: "{version}")',)


ARCHITECTURE_RUNTIME_ROWS = {
    "ARCH-001": ("abstractions-sdk", "abstractions-http", "abstractions-unused-http"),
    "ARCH-002": ("core-unused-http", "core-unused"),
    "ARCH-003": ("core-transitive", "core-packed"),
    "ARCH-004": ("leak-direct", "leak-recursive", "bcl-query", "bcl-nested-query", "bcl-connection"),
    "ARCH-005": ("provider-unrelated", "provider-same-family"),
    "ARCH-006": (),
    "ARCH-007": ("slice-same-assembly", "slice-async", "slice-external"),
    "ARCH-008": ("identity-direct-core", "identity-transitive-core", "slice-private"),
}


def architecture_witnesses(rule, mode):
    if rule not in ARCHITECTURE_RUNTIME_ROWS or mode not in ("reject", "permit"):
        raise ConformanceError("WitnessMissing")
    prefix = "Hoard.Architecture.Tests.ArchitectureRuleTests."
    if mode == "permit":
        return (prefix + "Actual_platform_provider_packages_and_both_hosts_are_permitted",)
    if rule == "ARCH-006":
        return (prefix + "Both_project_and_package_cycles_are_rejected",)
    return tuple(
        prefix + "Isolated_forbidden_input_is_rejected_by_its_intended_rule"
        + f'(name: "{name}", rule: "{rule}")' for name in ARCHITECTURE_RUNTIME_ROWS[rule])


def compatibility_witnesses(proof):
    prefix = "Hoard.Architecture.Tests."
    if proof == "identity-paths":
        return (
            prefix + "ArchitectureRuleTests.Identity_can_use_approved_hosting_with_its_transitive_core_dependency",
            *(prefix + "ArchitectureRuleTests.Approved_hosting_path_does_not_hide_an_alternate_forbidden_core_path"
              + f"(reverse: {reverse})" for reverse in (False, True)),
        )
    if proof == "inspection-failures":
        return tuple(
            prefix + "InspectionFailureTests.Omitting_any_required_real_scan_is_an_error"
            + f'(identity: "{identity}")' for identity in (
                "platform", "provider:Hoard.Fixtures.Protocol", "provider:Hoard.Fixtures.Metadata",
                "provider:Hoard.Fixtures.Artifact.One", "provider:Hoard.Fixtures.Artifact.Two",
                "provider:Hoard.Fixtures.Identity", "host:One", "host:Two")
        ) + tuple(
            prefix + "InspectionFailureTests.Incomplete_inputs_are_inspection_errors_not_clean_scans"
            + f'(failure: "{failure}")' for failure in (
                "assembly", "assets", "references", "ownership", "duplicate", "slices", "unresolved", "empty")
        )
    if proof not in ("source", "binary", "source-break", "binary-break", "predecessor-binaries"):
        raise ConformanceError("WitnessMissing")
    return ()


def version_runtime_tests():
    tests = {}
    for case in expected_cases("compatibility"):
        for identity in case.witnesses:
            if identity.startswith("Hoard.Composition.Tests.ConformanceVersionTests."):
                tests.setdefault(identity, ("none", case.case_id))
    return tests


def binary_runtime_tests():
    prefix = "Hoard.Conformance.Tests.CompatibilityBaselineTests."
    return {
        **{prefix + "Compiled_source_provenance_matches_actual_pe_pdb_and_frozen_historical_source"
           + f'(variant: "{variant}", name: "{name}", relative: "{relative}")': ("none", "COMPATIBILITY")
           for variant, name, relative in (
               ("baseline", "BinaryContract.dll", "Old/Contract.cs"),
               ("broken", "BinaryContract.dll", "New/Contract.cs"),
               ("compatible", "BinaryContract.dll", "Old/Contract.cs"),
               ("consumer", "RetainedConsumer.dll", "Consumer/Program.cs"))},
        **{prefix + "Unchanged_retained_consumer_observes_actual_candidate_not_an_accidental_old_contract"
           + f'(variant: "{variant}", compatible: {compatible})': ("none", "COMPATIBILITY")
           for variant, compatible in (("broken", False), ("compatible", True))},
        prefix + "Loaded_baseline_capture_rejects_replacement_with_actual_same_version_candidate_bytes":
            ("none", "COMPATIBILITY"),
    }


def architecture_runtime_tests():
    tests = {
        identity: ("none", case.case_id)
        for case in expected_cases("compatibility") for identity in case.witnesses
        if identity.startswith("Hoard.Architecture.Tests.")
    }
    prefix = "Hoard.Architecture.Tests.ConformanceArchitectureTests."
    owners = (
        ("Abstractions", "ARCH-001", "ARCH-001"), ("Core", "ARCH-002", "ARCH-003"),
        *((owner, "ARCH-008", "ARCH-008")
          for owner in ("Hosting", "Application", "Protocol", "Metadata", "Artifact", "Identity", "Host")),
    )
    extensions = (
        *(prefix + "Actual_declared_and_compiled_graph_paths_reject_test_sdk_but_permit_driver_sdk"
          + f"(transitive: {transitive}, compiled: {compiled})"
          for transitive in (False, True) for compiled in (False, True)),
        *(prefix + "Test_sdk_is_not_a_production_driver_sdk"
          + f'(source: "{source}", rule: "{direct}")' for source, direct, _ in owners),
        *(prefix + "Driver_sdk_permission_is_preserved_without_allowing_the_test_suite" + f'(source: "{source}")'
          for source in ("Metadata", "Artifact", "Identity")),
        *(prefix + "Explicit_test_owners_can_consume_the_test_suite" + f'(source: "{source}")'
          for source in ("Sdk", "Helper")),
        *(prefix + "Test_sdk_cannot_be_reclassified_to_bypass_the_boundary" + f'(ownership: "{ownership}")'
          for ownership in ("Bcl", "Abstractions", "Helper")),
        *(prefix + "Every_production_owner_rejects_actual_declared_and_compiled_test_sdk_paths"
          + f'(ownership: "{owner}", directRule: "{direct}", transitiveRule: "{transitive}")'
          for owner, direct, transitive in owners),
        *(prefix + "Explicit_test_owners_preserve_actual_test_sdk_graphs" + f'(ownership: "{owner}")'
          for owner in ("Sdk", "Helper")),
        *(prefix + "Permitted_hosting_never_hides_actual_direct_or_helper_core_paths"
          + f'(fixture: "{fixture}", identity: "{identity}", reverse: {reverse})'
          for fixture, identity in (("identity-direct-core", "DirectIdentityCore"),
                                    ("identity-transitive-core", "TransitiveIdentityCore"))
          for reverse in (False, True)),
        *(prefix + "Complete_scan_control_rejects_missing_foreign_and_uninspectable_graphs" + f'(defect: "{defect}")'
          for defect in ("missing", "duplicate", "foreign", "unidentified", "null", "array", "string", "number",
                         "missing-assembly", "missing-assets", "ambiguous-owner")),
    )
    tests.update({identity: ("none", "ARCH-BOUNDARY") for identity in extensions})
    return tests


QC_CONTROLS = {
    1: ("immutable-expansion", "fixed-category-keys", "unknown-revision-rejected", "altered-catalog-rejected"),
    2: ("sqlite-binding", "memory-binding", "unchanged-assertions", "exact-metadata-parameters"),
    3: ("local-binding", "object-binding", "unchanged-assertions", "exact-artifact-parameters"),
    4: ("faulty-binding-named-assertion", "corrected-binding", "unchanged-consumer-and-assertions"),
    5: ("missing-mandatory-hook", "missing-binding", "logical-exclusion-rejected", "durability-exclusions-only"),
    6: ("metadata-isolation", "metadata-atomicity", "bounded-pages", "leases", "references",
        "metadata-convergence-parity"),
    7: ("lost-ack-reconciliation", "late-native-protection", "incomplete-cleanup", "no-false-rollback"),
    8: ("sqlite-schema", "sqlite-backup-restore", "sqlite-crash-barriers", "owned-exit-readback",
        "nine-memory-exclusions", "no-borrowed-durability"),
    9: ("verification-visibility", "protected-reads", "shared-deletion-authority", "incarnation-fencing",
        "artifact-convergence-parity"),
    10: ("local-256m-write-read", "local-4g-write-read", "object-256m-write-read", "object-4g-write-read",
         "per-transfer-os-rss", "paced-nonseekable-streams", "stricter-inner-limits"),
    11: ("local-crash-barriers", "owned-exit-readback", "four-object-exclusions", "no-borrowed-durability"),
    12: ("sqlite-local", "sqlite-object", "memory-local", "memory-object",
         "live-references-and-readers", "aba-fencing", "uncertain-outcomes"),
    13: ("package-only-baseline", "package-only-replacement", "identical-consumer",
         "actual-start-readiness-stop", "selected-modules-only"),
    14: ("cp04", "cp05", "cp06", "cp07-forward", "cp07-reordered", "cp08", "cp09-zero", "cp09-two",
         "cp10-zero", "cp10-two", "cp11-route-conflict", "single-input-repairs",
         "preconstruction-declaration-rejection", "mapping-before-publication-and-admission"),
    15: ("multiple-protocols", "multiple-identities", "metadata-zero", "metadata-two",
         "artifacts-zero", "artifacts-two", "no-fallback"),
    16: ("zero-construction", "zero-routes", "zero-workers", "zero-connections",
         "optional-absent", "optional-disabled"),
    17: ("initializer-failure", "recovery-failure", "actual-not-ready", "no-replacement-activation"),
    18: ("initialization-cancellation", "readiness-cancellation", "late-initializer",
         "bounded-return", "retained-owner", "blocked-admission", "actual-settlement"),
    19: ("shutdown-fault", "noncooperative-shutdown", "retained-owner", "no-false-release",
         "actual-later-settlement"),
    20: ("optional-absent", "optional-disabled", "optional-compatible", "optional-incompatible",
         "no-unavailable-capability-or-edge", "no-auto-disable"),
    21: ("authority-mismatch", "store-version-admission", "mandatory-guarantee",
         "settled-restart", "active-selection-fixed", "active-configuration-fixed", "unsafe-errors-sanitized"),
    22: ("host-axis", "abstractions-axis", "required-dependency-axis", "optional-dependency-axis",
         "all-boundary-rows", "paired-repairs"),
    23: ("explicit-prerelease-gate", "exact-and-build-metadata", "case-precedence",
         "independent-platform-flags", "module-version-no-platform-opt-in"),
    24: ("required-dependency", "enabled-optional-dependency", "invalid-declarations-safe",
         "c01-through-c23", "policy-not-behavior"),
    25: ("unchanged-consumer-source", "unchanged-implementer-source", "four-category-bindings",
         "sealed-f06-binaries", "all-predecessor-binaries", "actual-candidate-assemblies", "no-baseline-rebuild"),
    26: ("source-break-intended-symbol", "source-compatible-repair", "binary-break-intended-incompatibility",
         "binary-compatible-repair", "unchanged-consumer-and-baseline"),
    27: ("arch001-pair", "arch002-pair", "arch003-pair", "arch004-pair",
         "arch005-pair", "arch006-pair", "arch007-pair", "arch008-pair",
         "graph-assets-nuspec", "public-surface-and-il", "complete-required-scans"),
    28: ("approved-hosting-core-path", "parallel-direct-core-forward", "parallel-direct-core-reverse",
         "parallel-helper-core-forward", "parallel-helper-core-reverse"),
    29: ("exact-input-scope", "finite-compositions-and-versions", "logical-durable-simulation-labels",
         "no-untested-cartesian-product"),
    30: ("separately-packed-adapter", "complete-common-suite", "explicit-category-admission",
         "unchanged-platform-provider-and-assertions"),
    31: ("faulty-stale-operation-assertion", "adapter-only-repair", "unchanged-consumer-and-assertions",
         "distinct-package-and-run-identities"),
    32: ("clean-source-reproduction", "documented-dependencies", "private-setup",
         "actual-package-resolution", "owned-cleanup", "no-undocumented-prerequisites"),
    33: ("overlapping-roots", "independent-feeds", "independent-caches", "independent-processes",
         "outside-sentinel-unchanged"),
    34: ("operation-budget", "barrier-budget", "child-budget", "transfer-budget", "recovery-budget",
         "termination-budget", "cleanup-budget", "profile-budget", "baseline-budget",
         "admission-included", "stricter-inner-limit", "child-and-transfer-ceilings",
         "bounded-raw-reads", "bounded-transient-and-retained-bytes", "output-flood-incomplete",
         "no-shortened-pass", "no-premature-release"),
    35: ("cleanup-failure-retained", "exact-live-identities", "explicit-settled-retry",
         "failure-history-preserved", "safe-guidance"),
    36: ("symlink-ancestor-rejected", "foreign-root-rejected", "preexisting-root-rejected",
         "pid-start-mismatch-rejected", "single-writer", "no-broad-deletion-or-termination"),
    37: ("service-free-baseline", "secret-free-baseline", "unsupported-service-no-fallback",
         "local-artifact-filesystem", "insufficient-scratch-incomplete"),
    38: ("source-mutation", "package-mutation", "lock-mutation", "configuration-mutation",
         "capability-mutation", "environment-mutation", "stale-report-substitution", "unaltered-control"),
    39: ("missing-case", "duplicate-case", "unknown-case", "missing-parameter",
         "duplicate-execution", "unknown-parameter", "unaltered-control"),
    40: ("altered-proof-bytes", "unattested-labels", "wrong-input-origin", "wrong-invocation-or-assembly",
         "wrong-execution-provenance", "unaltered-control"),
    41: ("post-selection-capability-change", "mandatory-logical-exclusion", "durability-reclassification",
         "unaltered-control"),
    42: ("mandatory-skip", "incomplete-child", "cancelled-child", "optimistic-aggregate",
         "unaltered-control"),
    43: ("failed-then-passing-attempt", "failed-history-preserved", "expected-negatives-isolated",
         "unaltered-control"),
    44: ("unknown-schema-field", "duplicate-schema-field", "malformed-unicode", "malformed-duration",
         "unsupported-status", "oversized-report", "escaping-proof", "oversized-proof",
         "proof-file-and-byte-ceilings", "unaltered-control"),
    45: ("local-ci-expansion-parity", "same-evaluator-bytes", "all-five-profiles", "every-mandatory-option"),
    46: ("required-job-failure", "required-job-cancellation", "upload-failure", "download-failure",
         "missing-report", "foreign-report", "partial-green-rejected", "unaltered-control"),
    47: ("recomputed-support", "exact-inputs-and-results", "exact-exclusions", "focused-not-baseline",
         "preparation-not-baseline", "stale-and-optimistic-summary-rejected"),
    48: ("secret-canary", "payload-canary", "private-path-canary", "connection-canary", "exception-canary",
         "all-private-diagnostics", "all-proof-files-and-filenames", "public-json-junit-markdown",
         "ci-summaries", "no-raw-spooling", "unknown-text-incomplete"),
}

METADATA_QUALITY_BASIS = MappingProxyType({
    "QC-02": tuple(range(1, 49)),
    "QC-04": (),
    "QC-05": (),
    "QC-06": (*range(1, 18), *range(20, 26), *range(28, 32)),
    "QC-07": (14, 15, 16, 17, 18, 19, 26, 27, 37),
    "QC-08": (*range(32, 37), *range(38, 46)),
})

CATEGORY_QUALITY_BASIS = MappingProxyType({
    "metadata": METADATA_QUALITY_BASIS,
    "artifacts": MappingProxyType({
        "QC-03": tuple(range(1, 49)),
        "QC-04": (),
        "QC-05": (),
        "QC-09": tuple(number for number in range(1, 49) if number not in (11, 12, 41, 42, 43, 44)),
        "QC-10": (11, 12),
        "QC-11": (41, 42, 43, 44),
        "QC-12": (),  # Its basis is the fresh integration scope, not inherited AS rows.
    }),
})


def obligation_controls(number):
    if set(QC_CONTROLS) != set(range(1, 49)) or number not in QC_CONTROLS or not QC_CONTROLS[number]:
        raise ConformanceError("WitnessMissing")
    return tuple(f"obligation:QC-{number:02}.{name}" for name in QC_CONTROLS[number])


def catalog_admission_witnesses():
    prefix = "Hoard.Conformance.Tests.CatalogAdmissionTests."
    return tuple(
        prefix + "Malformed_catalog_entries_fail_with_closed_diagnostics"
        + f'(defect: "{defect}")' for defect in (
            "unknown-profile", "duplicate-field", "unknown-field", "missing-field",
            "non-string-witness", "malformed-unicode", "malformed-key")
    ) + tuple(prefix + method for method in (
        "Oversized_catalogs_and_witness_collections_reject_without_partial_results",
        "Missing_profiles_and_duplicate_keys_cannot_return_a_shortened_catalog",
        "Per_profile_result_overflow_rejects_even_when_other_profiles_are_complete",
    ))


def authority_integration_witnesses():
    return tuple(sorted(AUTHORITY_INTEGRATION_ROWS))


def category_cases():
    inventory = load_json(INVENTORY.read_bytes())
    if inventory.get("catalogRevision") != CATALOG_REVISION:
        raise ConformanceError()
    cases = tuple(
        ExpectedCase(entry["profileId"], entry["bindingId"], entry["matrixId"], entry["caseId"],
                     tuple(entry["runtimeTests"]), tuple(entry["orchestratorControls"]), entry["exclusion"])
        for entry in inventory["entries"])
    expected = {
        (profile, binding, "none", f"{prefix}-{number:02}")
        for profile, bindings, prefix in (("metadata", ("sqlite", "memory"), "MP"),
                                          ("artifacts", ("local", "object"), "AS"))
        for binding in bindings for number in range(1, 49)}
    if len(cases) != len(expected) or {case.key for case in cases} != expected:
        raise ConformanceError("EvidenceIncomplete")
    return cases


def expected_cases(profile):
    cases = []
    if profile in ("metadata", "artifacts"):
        cases.extend(case for case in category_cases() if case.profile_id == profile)
    elif profile == "composition":
        for case_id, variants in COMPOSITIONS:
            for variant in variants:
                modes = ("reject", "repair") if 4 <= int(case_id[3:]) <= 11 or (
                    case_id == "CP-13" and variant == "optional-incompatible") else ("observe",)
                for mode in modes:
                    matrix = f"{variant}.{mode}"
                    cases.append(ExpectedCase(profile, "none", matrix, case_id,
                                              composition_witnesses(case_id, variant)))
    elif profile == "compatibility":
        for axis in ("host", "abstractions", "dependency-required", "dependency-optional"):
            runtime_axis = {"host": "host", "abstractions": "abstractions",
                            "dependency-required": "required", "dependency-optional": "optional"}[axis]
            for name, _, _, _, _ in VERSION_ROWS:
                matrix = f"{axis}.{name}"
                cases.append(ExpectedCase(profile, "none", matrix, "VERSION", (
                    f'Hoard.Composition.Tests.ConformanceVersionTests.Runtime_matrix(axis: "{runtime_axis}", row: "{VERSION_RUNTIME_ROWS[name]}")',)))
        for name in ("host-only-flag", "abstractions-only-flag", "module-no-platform-flag",
                     "optional-absent", "optional-disabled"):
            cases.append(ExpectedCase(profile, "none", name, "VERSION-INDEPENDENT",
                                      independent_version_witnesses(name)))
        for number in range(1, 24):
            case_id = f"C-{number:02}"
            cases.append(ExpectedCase(profile, "none", "none", case_id, classification_witnesses(case_id),
                                      (f"classification:{case_id}",)))
        for number in range(1, 9):
            for mode in ("reject", "permit"):
                rule = f"ARCH-{number:03}"
                matrix = f"{rule}.{mode}"
                cases.append(ExpectedCase(profile, "none", matrix, "ARCHITECTURE",
                                          architecture_witnesses(rule, mode),
                                          (f"architecture:{matrix}",)))
        for proof in ("source", "binary", "source-break", "binary-break", "identity-paths",
                      "inspection-failures", "predecessor-binaries"):
            cases.append(ExpectedCase(profile, "none", proof, "COMPATIBILITY", compatibility_witnesses(proof),
                                      (f"compatibility:{proof}",)))
    elif profile != "harness":
        raise ConformanceError("UnsupportedProfile")
    obligations = {
        "metadata": (2, 4, 5, 6, 7, 8),
        "artifacts": (3, 4, 5, 9, 10, 11, 12),
        "composition": tuple(range(13, 22)),
        "compatibility": tuple(range(22, 29)),
        "harness": (1, *range(29, 49)),
    }
    for number in obligations[profile]:
        witnesses = catalog_admission_witnesses() if number == 1 else ()
        if number == 12:
            witnesses = authority_integration_witnesses()
        elif number == 4:
            witnesses = tuple(sorted(category_mutation_witnesses(profile, corrected=True)))
        elif number == 5:
            witnesses = tuple(sorted(hook_admission_tests(profile)))
        cases.append(ExpectedCase(profile, "none", "none", f"QC-{number:02}", witnesses,
                                  obligation_controls(number)))
    if len(cases) > MAX_RESULTS or len({case.key for case in cases}) != len(cases):
        raise ConformanceError("EvidenceIncomplete")
    return tuple(cases)


def sdk_document():
    return {
        "schemaVersion": 1, "catalogRevision": CATALOG_REVISION,
        "entries": [
            {"profileId": case.profile_id, "bindingId": case.binding_id, "matrixId": case.matrix_id,
             "caseId": case.case_id, "witnesses": list(case.witnesses), "controls": list(case.controls),
             "exclusion": case.exclusion}
            for profile in PROFILES for case in expected_cases(profile)],
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Prepare/check the fixed SDK catalog, not runtime evidence.")
    parser.add_argument("--write-sdk", action="store_true")
    parser.add_argument("--check-sdk", action="store_true")
    options = parser.parse_args()
    target = Path(__file__).resolve().parents[1] / "tests/contracts/Hoard.Testing.Conformance/Catalog/catalog.json"
    content = canonical_bytes(sdk_document()) + b"\n"
    if options.write_sdk and not options.check_sdk:
        with target.open("xb") as output:
            output.write(content)
    elif options.check_sdk and not options.write_sdk:
        if target.read_bytes() != content:
            raise SystemExit("SDK catalog differs from independent expansion.")
    else:
        parser.error("Choose exactly one of --write-sdk/--check-sdk.")
