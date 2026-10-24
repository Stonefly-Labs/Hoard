"""F-07 expectations expanded independently of any binding or result."""

from dataclasses import dataclass
import json
from pathlib import Path

from conformance_evidence import (
    CATALOG_REVISION, ConformanceError, MAX_RESULTS, MAX_WITNESSES, PROFILES,
    canonical_bytes, load_json, stable_id,
)


INVENTORY = Path(__file__).resolve().parents[1] / "tests/fixtures/conformance/baselines/inventory.json"


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
        ("CP-16", "late-initialization"): "CP16_noncooperative_initializer_returns_finitely_but_retains_owner_until_real_settlement",
        ("CP-18", "recovery-failed"): "CP18_real_local_recovery_rejects_corrupt_manifest_without_fallback_and_exact_repair_recovers",
        ("CP-20", "settled-restart"): "CP20_active_selection_is_immutable_and_only_fresh_settled_restart_changes_owner",
        ("CP-20", "active-config"): "CP20_active_configuration_is_fixed_until_a_fresh_explicit_restart",
    }
    if key in facts:
        return (prefix + facts[key],)
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
        ("CP-17", "stop-fault"): (
            'CP17_shutdown_fault_or_retention_never_claims_complete_cleanup(variant: "fault")',),
        ("CP-17", "late-stop"): (
            'CP17_shutdown_fault_or_retention_never_claims_complete_cleanup(variant: "noncooperative")',),
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
