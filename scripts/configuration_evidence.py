"""Bounded, fail-closed fixture-only configuration evidence."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import subprocess
import tarfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import foundation_evidence as foundation
import lifecycle_evidence as lifecycle


BASELINE = "b80c69fc386541be4f56f6ef2edeca40f43a0e1c"
CASES = tuple(f"CFG-{number:02}" for number in range(1, 37))
PUBLICATION_BARRIERS = ("staged", "write", "flush", "pre-publish", "post-publish")
GRAPH_IDS = ("platform", "Protocol.One", "Protocol.Two", "Metadata", "Artifact.One", "Artifact.Two",
             "Identity", "configured-baseline", "configured-custom", "old-provider",
             "lifecycle-consumer", "registration", "conversion-process")
JOURNEYS = ("configured-one", "configured-two-same-binary", "invalid-replacement", "explicit-recovery")
REQUIRED_TESTS = {
    "CFG-01": ("ConfigurationSourceTests.Four_sources_are_explicit_deterministic_and_keep_winning_provenance",
               "ConfigurationSourceTests.Requested_files_empty_overlays_and_case_equivalent_overlay_names_are_not_absence"),
    "CFG-02": ("ConfigurationStructureTests.Canonical_keys_decode_before_duplicates_and_values_are_not_normalized",
               "ConfigurationStructureTests.Every_supplied_occurrence_is_structurally_checked_even_when_disabled_and_overridden",
               "ConfigurationSourceTests.Malformed_reserved_arguments_fail_without_payloads"),
    "CFG-03": ("ConfigurationMergeTests.Arrays_replace_options_merge_and_secret_references_replace_atomically",),
    "CFG-04": ("ConfigurationMergeTests.Explicit_emptiness_is_not_a_missing_value_or_an_informative_default",
               "ConfiguredCompositionTests.Real_composition_gate_rejects_before_public_checks_without_reflecting_unknown_ids"),
    "CFG-05": ("ConfigurationSourceTests.Requested_files_empty_overlays_and_case_equivalent_overlay_names_are_not_absence",
               "ConfigurationStructureTests.Document_depth_assignment_and_selection_limits_have_exact_permitted_counterparts",
               "ConfigurationStructureTests.Utf8_string_and_private_locator_limits_apply_to_bytes_not_character_count",
               "ConfigurationContractTests.Input_snapshots_stop_at_hard_bounds_before_exhausting_supplied_collections",
               "ConfigurationContractTests.Oversized_snapshot_argument_does_not_enumerate_following_inputs"),
    "CFG-06": ("ConfiguredCompositionTests.Real_composition_gate_rejects_before_public_checks_without_reflecting_unknown_ids",
               "ConfiguredCompositionTests.Multiple_protocols_and_identities_use_the_real_gate_activation_order",
               "ConfiguredCompositionTests.Composition_diagnostics_preserve_closed_reason_known_owner_source_and_remap_dependency_paths"),
    "CFG-07": ("ConfiguredCompositionTests.Real_composition_gate_rejects_before_public_checks_without_reflecting_unknown_ids",
               "ConfiguredCompositionTests.Configured_gate_preserves_actual_optional_dependency_cycle_prerelease_and_declaration_outcomes",
               "ConfiguredCompositionTests.Composition_diagnostics_preserve_closed_reason_known_owner_source_and_remap_dependency_paths"),
    "CFG-08": ("ConfiguredCompositionTests.Disabled_semantic_failures_and_unavailable_references_do_no_work",
               "ConfiguredCompositionTests.Configured_gate_preserves_actual_optional_dependency_cycle_prerelease_and_declaration_outcomes",
               "ConfiguredCompositionTests.Real_composition_gate_rejects_before_public_checks_without_reflecting_unknown_ids"),
    "CFG-09": ("ConfigurationContractTests.Registration_is_inert_and_metadata_is_defensively_copied",
               "ConfigurationContractTests.Invalid_associations_fail_without_callbacks_or_construction",
               "ConfiguredCompositionTests.Active_option_failures_precede_every_secret_read_and_construction"),
    "CFG-10": ("ConfiguredCompositionTests.Active_option_failures_precede_every_secret_read_and_construction",
               "ConfiguredCompositionTests.Declared_option_rules_keep_effective_field_source_and_safe_action",
               "ConfiguredCompositionTests.Unsupported_active_option_version_keeps_its_explicit_setting_source",
               "ConfiguredCompositionTests.Effective_allowed_values_and_ranges_reject_without_overrides_but_ignore_discarded_semantic_errors",
               "ConfigurationStructureTests.Every_supplied_occurrence_is_structurally_checked_even_when_disabled_and_overridden"),
    "CFG-11": ("ConfiguredCompositionTests.Disabled_semantic_failures_and_unavailable_references_do_no_work",
               "ConfigurationStructureTests.Every_supplied_occurrence_is_structurally_checked_even_when_disabled_and_overridden"),
    "CFG-12": ("ConfiguredCompositionTests.Real_composition_gate_rejects_before_public_checks_without_reflecting_unknown_ids",
               "ConfiguredCompositionTests.Declared_option_rules_keep_effective_field_source_and_safe_action",
               "ConfigurationSecretTests.Secret_option_rules_keep_effective_source_and_reject_undeclared_results",
               "ConfiguredCompositionTests.Active_option_failures_precede_every_secret_read_and_construction",
               "ConfigurationSecretTests.Timed_out_secret_check_retains_input_until_late_fault_and_freezes_result"),
    "CFG-13": ("ConfigurationSecretTests.Secret_is_fixed_owner_only_and_transferred_once_to_existing_lifecycle",
               "ConfigurationSecretTests.Known_secret_failures_keep_the_exact_field_owner_and_winning_source",
               "ConfigurationSecretTests.Unavailable_environment_secret_has_no_fallback_or_activation",
               "ConfigurationSecretTests.Environment_preserves_exact_text_and_accepts_exact_byte_limit",
               "ConfigurationSecretTests.Environment_target_lookup_uses_platform_case_rules_without_an_alternate_lookup"),
    "CFG-14": ("ConfigurationSecretTests.Actual_local_file_and_deployment_symlink_preserve_documented_newline_policy",
               "ConfigurationSecretTests.Known_secret_failures_keep_the_exact_field_owner_and_winning_source",
               "ConfigurationSecretTests.Invalid_actual_or_denied_mounted_file_is_safe_and_never_constructs",
               "ConfigurationSecretTests.Actual_local_pipe_is_rejected_without_waiting_for_secret_bytes"),
    "CFG-15": ("ConfigurationStructureTests.Every_supplied_occurrence_is_structurally_checked_even_when_disabled_and_overridden",
               "ConfiguredCompositionTests.Active_option_failures_precede_every_secret_read_and_construction"),
    "CFG-16": ("ConfigurationSecretTests.Secret_is_fixed_owner_only_and_transferred_once_to_existing_lifecycle",
               "ConfigurationSecretTests.Shared_reference_resolves_each_owner_independently_without_cross_owner_options"),
    "CFG-17": ("ConfigurationContractTests.Safe_diagnostics_cap_unknown_identities_without_reflecting_regex_valid_payloads",
               "ConfigurationSecretTests.Known_secret_failures_keep_the_exact_field_owner_and_winning_source",
               "ConfigurationCoordinationTests.Pending_secret_diagnostics_keep_origin_through_timeout_cancellation_and_late_fault",
               "ConfiguredCompositionTests.Declared_option_rules_keep_effective_field_source_and_safe_action",
               "ConfigurationSecretTests.Secret_option_rules_keep_effective_source_and_reject_undeclared_results",
               "ConfigurationStructureTests.Known_field_failures_keep_safe_identity_but_unknown_names_are_not_reflected",
               "ConfiguredCompositionTests.Composition_diagnostics_preserve_closed_reason_known_owner_source_and_remap_dependency_paths",
               "ConfigurationConversionTests.Preview_is_secret_free_and_approved_apply_preserves_original_references_without_activation"),
    "CFG-18": ("ConfigurationCoordinationTests.Entire_synchronous_callback_is_supervised_and_late_fault_is_observed",
               "ConfigurationCoordinationTests.Pending_secret_diagnostics_keep_origin_through_timeout_cancellation_and_late_fault",
               "ConfigurationCoordinationTests.Absolute_deadline_caps_the_next_dispatch_and_prevents_later_work",
               "ConfigurationCoordinationTests.Elapsed_dispatch_cap_wins_even_when_timeout_notification_is_delayed"),
    "CFG-19": ("ConfigurationCoordinationTests.Already_cancelled_input_dispatches_nothing",
               "ConfigurationCoordinationTests.Pending_secret_diagnostics_keep_origin_through_timeout_cancellation_and_late_fault",
               "ConfigurationCoordinationTests.Caller_cancellation_does_not_run_collaborator_notification_inline",
               "ConfigurationCoordinationTests.Cancellation_at_success_boundary_prevents_completion_and_notification_retains_inputs"),
    "CFG-20": ("ConfigurationCoordinationTests.Pending_work_keeps_sensitive_inputs_alive_after_bounded_disposal",
               "ConfigurationCoordinationTests.Pending_secret_diagnostics_keep_origin_through_timeout_cancellation_and_late_fault",
               "ConfigurationSecretTests.Timed_out_secret_check_retains_input_until_late_fault_and_freezes_result",
               "ConfigurationSecretTests.Pending_F02_notification_or_cancellation_retains_secrets_and_root_without_deferred_cleanup"),
    "CFG-21": ("ConfiguredCompositionTests.Proof_rejects_foreign_changed_disposed_and_duplicate_consumption_before_construction",
               "ConfiguredCompositionTests.Legacy_compose_cannot_bypass_opt_in_and_cancelled_consume_constructs_nothing",
               "ConfigurationSecretTests.Concurrent_consume_dispose_mutation_and_legacy_attempts_have_one_secret_release_authority",
               "ConfigurationSecretTests.Blocked_configured_delivery_keeps_transferred_secrets_and_prerequisites_without_late_services",
               "ConfigurationSecretTests.Pending_F02_notification_or_cancellation_retains_secrets_and_root_without_deferred_cleanup"),
    "CFG-22": ("ConfiguredCompositionTests.Accepted_owner_values_enter_the_existing_lease_before_services",
               "ConfiguredCompositionTests.Thrown_configured_delivery_uses_existing_safe_lifecycle_failure",
               "ConfigurationSecretTests.Blocked_configured_delivery_keeps_transferred_secrets_and_prerequisites_without_late_services",
               "ConfigurationSecretTests.Pending_F02_notification_or_cancellation_retains_secrets_and_root_without_deferred_cleanup"),
    "CFG-23": ("ConfigurationRestartTests.Running_TestServer_keeps_fixed_inputs_and_fresh_restart_rereads_explicit_sources",),
    "CFG-24": ("ConfigurationDistributionTests.Prepared_configuration_distributions_and_old_binaries_are_complete",),
    "CFG-25": ("ConfigurationRestartTests.Invalid_restart_has_no_previous_value_reuse_and_explicit_fresh_recovery_is_required",
               "ConfigurationDistributionTests.Prepared_configuration_distributions_and_old_binaries_are_complete"),
    "CFG-26": ("ConfigurationVersionTests.Each_document_requires_its_own_current_integer_version",
               "ConfiguredCompositionTests.Unsupported_active_option_version_keeps_its_explicit_setting_source",
               "ConfigurationVersionTests.Overlays_cannot_override_or_repair_document_versions",
               "ConfiguredCompositionTests.Disabled_semantic_failures_and_unavailable_references_do_no_work"),
    "CFG-27": ("ConfigurationConversionTests.Preview_is_secret_free_and_approved_apply_preserves_original_references_without_activation",
               "ConfigurationConversionTests.Unsupported_or_incomplete_synthetic_input_is_not_guessed",
               "ConfigurationConversionTests.Conversion_rejects_unsupported_disabled_option_versions_without_disabled_work"),
    "CFG-28": ("ConfigurationConversionTests.Approval_pins_exact_context_and_full_validation_precedes_publication",
               "ConfigurationConversionTests.Context_changed_after_validation_is_rechecked_before_atomic_publication",
               "ConfigurationConversionTests.Conversion_rejects_unsupported_disabled_option_versions_without_disabled_work"),
    "CFG-29": ("ConfigurationConversionTests.Preview_is_secret_free_and_approved_apply_preserves_original_references_without_activation",
               "ConfigurationConversionTests.Actual_source_aliases_are_rejected_without_changing_either_file",
               "ConfigurationConversionTests.Publication_rejects_nonprivate_or_direct_symlink_parent_without_creating_output",
               "ConfigurationConversionTests.Racing_existing_destination_is_never_clobbered",
               "ConfigurationConversionTests.Real_publication_faults_preserve_original_and_report_actual_commit"),
    "CFG-30": ("ConfigurationConversionTests.Real_publication_faults_preserve_original_and_report_actual_commit",
               "ConfigurationConversionTests.Cancelled_apply_before_dispatch_reads_no_secret_and_publishes_nothing",
               "ConfigurationConversionTests.Timed_out_dispatched_publication_is_pending_until_actual_nonpublication_is_observed",
               "ConfigurationConversionTests.Committed_publication_remains_published_while_post_commit_work_times_out"),
    "CFG-31": ("ConfigurationRestartTests.Invalid_restart_has_no_previous_value_reuse_and_explicit_fresh_recovery_is_required",
               "ConfigurationConversionTests.Unsupported_or_incomplete_synthetic_input_is_not_guessed"),
    "CFG-32": ("ConfigurationBoundaryTests.Configuration_does_not_expand_provider_dependency_directions",
               "ConfigurationBoundaryTests.Prepared_configuration_graphs_are_complete_and_permitted"),
    "CFG-33": ("ConfigurationDistributionTests.Prepared_configuration_distributions_and_old_binaries_are_complete",),
    "CFG-34": ("ConfigurationContractTests.Private_inputs_and_options_do_not_serialize_values",
               "ConfigurationDistributionTests.Prepared_configuration_distributions_and_old_binaries_are_complete"),
    "CFG-35": ("ConfigurationStructureTests.Every_supplied_occurrence_is_structurally_checked_even_when_disabled_and_overridden",
               "ConfigurationRestartTests.Invalid_restart_has_no_previous_value_reuse_and_explicit_fresh_recovery_is_required",
               "ConfigurationBoundaryTests.Prepared_configuration_graphs_are_complete_and_permitted"),
    "CFG-36": ("ConfigurationDistributionTests.Missing_distribution_inputs_cannot_pass_as_empty_package_proof",
               "ConfigurationDistributionTests.Prepared_configuration_distributions_and_old_binaries_are_complete",
               "ConfigurationBoundaryTests.Prepared_configuration_graphs_are_complete_and_permitted")
}
_workspaces = set()


def create_workspace(parent=None, destination=None):
    import tempfile
    if destination is None:
        path = Path(tempfile.mkdtemp(prefix="hoard-configuration-", dir=parent)).resolve()
    else:
        destination = Path(destination).absolute()
        if destination.exists() or not destination.parent.is_dir():
            raise RuntimeError("Configuration evidence requires a fresh explicit private destination.")
        destination.mkdir(mode=0o700)
        path = destination.resolve()
    path.chmod(0o700)
    _workspaces.add(path)
    return path


def cleanup_workspace(path):
    path = Path(path)
    if path != path.resolve() or path not in _workspaces:
        raise RuntimeError("Refusing cleanup outside owned configuration workspace.")
    shutil.rmtree(path)
    _workspaces.remove(path)


def run(*args, cwd=None, env=None):
    try:
        result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=False, timeout=600,
                                env={**os.environ, **(env or {})})
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Configuration command timed out: {Path(args[0]).name}") from None
    if result.returncode:
        codes = re.findall(r"(?:error (?:CS|NU|MSB)\d+|error WHITESPACE|\bFailed [A-Za-z0-9._]+)", result.stdout)
        context = " [" + ", ".join(codes[:10]) + "]" if codes else ""
        raise RuntimeError(f"Configuration command failed: {Path(args[0]).name}{context}")
    return result.stdout


def scenario_name(name):
    return ".".join(name.partition("(")[0].split(".")[-2:])


def verify_cases(cases):
    if not isinstance(cases, list) or len(cases) != len(CASES) or \
            any(not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or
                not isinstance(entry.get("tests"), list) for entry in cases) or \
            sorted(entry.get("id", "") for entry in cases) != sorted(CASES) or \
            any(entry.get("passed") is not True or not entry.get("tests") or
                any(not isinstance(test, str) or not test.strip() for test in entry["tests"]) or
                not set(REQUIRED_TESTS[entry["id"]]).issubset({scenario_name(test) for test in entry["tests"]})
                for entry in cases):
        raise RuntimeError("Missing, duplicate, failed or incomplete configuration case inventory.")


def verify_binary(path, digest):
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Retained configuration binary changed or missing.")


def verify_package(package, feed, digest):
    if feed != feed.resolve() or package.resolve().parent != feed or not package.is_file() or \
            hashlib.sha512(package.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Invalid configuration package provenance.")


def verify_publication(evidence):
    if not isinstance(evidence, dict) or evidence.get("os") not in ("Darwin", "Linux") or \
            not isinstance(evidence.get("filesystem"), str) or not evidence["filesystem"].strip() or \
            not isinstance(evidence.get("barriers"), list) or \
            any(not isinstance(barrier, str) for barrier in evidence["barriers"]) or \
            evidence.get("passed") is not True or \
            sorted(evidence.get("barriers", [])) != sorted(PUBLICATION_BARRIERS):
        raise RuntimeError("Missing local-platform configuration publication proof.")


lock_hashes = lifecycle.lock_hashes
verify_locks = lifecycle.verify_locks


def test_count(path):
    try:
        return lifecycle.test_count(path)
    except (OSError, ValueError, ET.ParseError):
        raise RuntimeError("Invalid configuration test result counters.") from None


def prepare_baseline(root, work, update):
    run("git", "merge-base", "--is-ancestor", BASELINE, "origin/main", cwd=root)
    baseline = work / "baseline"
    baseline.mkdir()
    archive = work / "baseline.tar"
    run("git", "archive", "--format=tar", f"--output={archive}", BASELINE,
        "Directory.Build.props", "Directory.Packages.props", "global.json", "src", cwd=root)
    with tarfile.open(archive) as contents:
        contents.extractall(baseline, filter="data")
    feed = work / "baseline-feed"
    feed.mkdir()
    cache = work / "baseline-cache"
    config = work / "Baseline.NuGet.Config"
    config.write_text(
        '<configuration><packageSources><clear/>'
        f'<add key="local" value="{escape(str(feed))}"/>'
        '<add key="nuget.org" value="https://api.nuget.org/v3/index.json"/>'
        '</packageSources><packageSourceMapping><packageSource key="local">'
        '<package pattern="Hoard.*"/></packageSource><packageSource key="nuget.org">'
        '<package pattern="*"/></packageSource></packageSourceMapping></configuration>')
    for name in ("Abstractions", "Core", "Hosting"):
        project = baseline / f"src/Hoard.{name}/Hoard.{name}.csproj"
        run("dotnet", "restore", str(project), "--locked-mode", "--configfile", str(config),
            "--packages", str(cache), "-v", "quiet")
        run("dotnet", "pack", str(project), "-c", "Release", "--no-restore",
            "-o", str(feed), "-v", "quiet")
        foundation.canonicalize_acceptance_archive(feed / f"Hoard.{name}.0.1.0.nupkg")
    retained = []
    for name in ("LegacyOptions", "LifecycleConsumer"):
        source = root / "tests/fixtures/configuration" / name
        target = work / "retained" / name
        foundation.copy_source(source, target)
        lock_source = source / "Baseline"
        lock_source.mkdir(exist_ok=True)
        project = target / f"{name}.csproj"
        if not update:
            lock = lock_source / "packages.lock.json"
            if not lock.is_file():
                raise RuntimeError("Missing retained configuration baseline lock.")
            shutil.copy2(lock, target / lock.name)
        run("dotnet", "restore", str(project), "--configfile", str(config),
            "--force-evaluate" if update else "--locked-mode",
            "--packages", str(cache), "-v", "quiet")
        if update:
            shutil.copy2(target / "packages.lock.json", lock_source / "packages.lock.json")
            run("dotnet", "restore", str(project), "--configfile", str(config), "--locked-mode",
                "--packages", str(work / "baseline-replay-cache"), "-v", "quiet")
        run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet")
        binary = target / f"bin/Release/net10.0/{name}.dll"
        if name == "LifecycleConsumer" and run("dotnet", str(binary)).strip() != "lifecycle-compatible":
            raise RuntimeError("Retained lifecycle baseline did not execute.")
        retained.append({"name": name, "baseline": BASELINE, "assembly": str(binary),
                         "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                         "assets": str(target / "obj/project.assets.json")})
    for entry in retained:
        verify_binary(Path(entry["assembly"]), entry["sha256"])
    (work / "retained-binaries.json").write_text(json.dumps(retained, indent=2))
    return retained


def retain_baseline(retained, destination):
    destination = destination.absolute()
    if destination.exists() or not destination.parent.is_dir():
        raise RuntimeError("Retained baseline requires a fresh explicit private destination.")
    if any(destination.is_relative_to(Path(entry["assembly"]).resolve().parent) for entry in retained):
        raise RuntimeError("Retained baseline destination overlaps inputs.")
    destination.mkdir(mode=0o700)
    result = []
    for entry in retained:
        binary = Path(entry["assembly"])
        verify_binary(binary, entry["sha256"])
        target = destination / entry["name"]
        shutil.copytree(binary.parent, target)
        shutil.copy2(entry["assets"], target / "baseline.assets.json")
        saved = {**entry, "assembly": str(target / binary.name), "assets": str(target / "baseline.assets.json")}
        verify_binary(Path(saved["assembly"]), saved["sha256"])
        result.append(saved)
    (destination / "retained-binaries.json").write_text(json.dumps(result, indent=2))
    return result


def retain_evidence(work, destination, kind, passed):
    if kind not in ("source-tests", "baseline") or not isinstance(passed, bool):
        raise RuntimeError("Invalid configuration evidence category.")
    destination = destination.absolute()
    if destination.exists() or not destination.parent.is_dir() or destination.is_relative_to(work):
        raise RuntimeError("Configuration evidence requires a fresh explicit private destination.")
    destination.mkdir(mode=0o700)
    results = []
    for name in ("configuration.trx",):
        source = work / "results" / name
        if source.is_file():
            shutil.copy2(source, destination / name)
            results.append(name)
    (destination / "result.json").write_text(json.dumps({
        "kind": kind, "scope": "partial", "status": "passed" if passed else "failed",
        "testResults": results, "fullAcceptance": False
    }, indent=2))


def phase(name, callback, *args):
    try:
        return callback(*args)
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        codes = re.findall(r"error (?:CS|NU|MSB)\d+|error WHITESPACE|Failed [A-Za-z0-9._]+", str(error))
        detail = " [" + ", ".join(codes[:10]) + "]" if codes else ""
        raise RuntimeError(f"Configuration evidence phase failed: {name}{detail}") from None


def prepared_restore(project, config, source, update):
    phase("locked consumer restore", foundation.restore, project, config, update, source)
    return phase("consumer build", foundation.build, project)


def retained_inputs(retained, directory):
    directory = directory.resolve()
    try:
        entries = json.loads((directory / "retained-binaries.json").read_text())
    except (OSError, ValueError):
        raise RuntimeError("Invalid retained pre-F-03 input manifest.") from None
    if not exact_inventory(entries, "name", ("LegacyOptions", "LifecycleConsumer")):
        raise RuntimeError("Missing retained pre-F-03 input inventory.")
    for saved in entries:
        if saved.get("baseline") != BASELINE or any(
                not isinstance(saved.get(key), str) or not saved[key] for key in ("assembly", "assets", "sha256")):
            raise RuntimeError("Invalid retained pre-F-03 baseline identity.")
        binary, assets = Path(saved["assembly"]), Path(saved["assets"])
        if binary.name != saved["name"] + ".dll" or not all(
                path.resolve().is_relative_to(directory) and path.is_file() for path in (binary, assets)):
            raise RuntimeError("Invalid retained pre-F-03 input location.")
        verify_binary(binary, saved["sha256"])
    for current in retained:
        saved = next(entry for entry in entries if entry["name"] == current["name"])
        binary = Path(saved["assembly"])
        target = Path(current["assembly"])
        for source in binary.parent.iterdir():
            if source.is_file() and (source.suffix in (".dll", ".pdb") or
                                     source.name.endswith((".deps.json", ".runtimeconfig.json"))):
                if not source.resolve().is_relative_to(directory):
                    raise RuntimeError("Invalid retained pre-F-03 dependency location.")
                shutil.copy2(source, target.parent / source.name)
        current["sha256"] = saved["sha256"]
        verify_binary(target, saved["sha256"])


def compatibility(root, work, config, retained, update, retained_directory=None):
    legacy = next(entry for entry in retained if entry["name"] == "LegacyOptions")
    project = Path(legacy["assembly"]).parents[3] / "LegacyOptions.csproj"
    run("dotnet", "pack", str(project), "-c", "Release", "--no-build", "--no-restore",
        "-o", str(work / "feed"), "-v", "quiet")
    package = work / "feed/Hoard.Fixtures.Configuration.LegacyOptions.0.1.0.nupkg"
    phase("old provider packing", foundation.canonicalize_acceptance_archive, package)
    verify_binary(Path(legacy["assembly"]), legacy["sha256"])
    if retained_directory is not None:
        phase("retained pre-F-03 input validation", retained_inputs, retained, retained_directory)
    source = root / "tests/fixtures/configuration/LifecycleConsumer"
    target = work / "lifecycle-consumer"
    foundation.copy_source(source, target)
    new_project = target / "LifecycleConsumer.csproj"
    binary = prepared_restore(new_project, config, source, update)
    if run("dotnet", str(binary)).strip() != "lifecycle-compatible":
        raise RuntimeError("New-source lifecycle consumer failed.")
    old = next(entry for entry in retained if entry["name"] == "LifecycleConsumer")
    for path in binary.parent.iterdir():
        if path.is_file() and path.name not in ("LifecycleConsumer.dll", "LifecycleConsumer.pdb"):
            shutil.copy2(path, Path(old["assembly"]).parent / path.name)
    verify_binary(Path(old["assembly"]), old["sha256"])
    if run("dotnet", old["assembly"]).strip() != "lifecycle-compatible":
        raise RuntimeError("Unchanged pre-F-03 lifecycle binary failed with new runtime.")
    runtime = json.loads(binary.with_suffix(".runtimeconfig.json").read_text())
    if not any(item["name"] == "Microsoft.AspNetCore.App" for item in runtime["runtimeOptions"].get("frameworks", [])):
        raise RuntimeError("Configuration shared-framework propagation is missing.")
    return project, new_project


def configured_journeys(root, work, config, retained, update):
    source = root / "examples/LifecycleHost"
    projects, journeys = [], []
    legacy = next(entry for entry in retained if entry["name"] == "LegacyOptions")
    before = foundation.source_hashes(root)
    for name, relative, expected in (
            ("baseline", "Configuration/LifecycleHost.Configuration.csproj",
             {"configured-one", "configured-two-same-binary", "invalid-replacement", "explicit-recovery"}),
            ("custom", "Configuration/Custom/LifecycleHost.Configuration.Custom.csproj",
             {"configured-one", "configured-two-same-binary", "invalid-replacement", "explicit-recovery", "configured-custom-artifact"})):
        target = work / "configured-hosts" / name
        foundation.copy_source(source, target)
        project = target / relative
        binary = prepared_restore(project, config, source / Path(relative).parent, update)
        provider = binary.parent / "LegacyOptions.dll"
        if not provider.is_file():
            raise RuntimeError("Missing configured runtime provider.")
        verify_binary(Path(legacy["assembly"]), legacy["sha256"])
        shutil.copy2(legacy["assembly"], provider)
        verify_binary(provider, legacy["sha256"])
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        output = json.loads(run("dotnet", str(binary), "--configuration-fixtures", cwd=target))
        actual = output.get("journeys", [])
        if len(actual) != len(expected) or {entry.get("name") for entry in actual} != expected or \
                any(entry.get("passed") is not True or entry.get("events", 0) <= 0 for entry in actual):
            raise RuntimeError("Missing, duplicate or failed configured package-only journey.")
        assets = json.loads((project.parent / "obj/project.assets.json").read_text())
        present = any(key.startswith("Hoard.Fixtures.Lifecycle.Artifact.Two/") for key in assets["libraries"])
        if present != (name == "custom") or ET.parse(project).findall(".//ProjectReference"):
            raise RuntimeError("Configured distribution has an invalid package graph.")
        if hashlib.sha256(binary.read_bytes()).hexdigest() != digest:
            raise RuntimeError("Configured bundled journey rebuilt its host.")
        verify_binary(provider, legacy["sha256"])
        journeys.extend({**entry, "distribution": name, "hostSha256": digest,
                         "providerAssembly": str(provider), "providerSha256": legacy["sha256"]} for entry in actual)
        projects.append(project)
    if foundation.source_hashes(root) != before:
        raise RuntimeError("Configured journeys modified platform/provider source.")
    return projects, journeys


def interrupted_publication(root, work, config, update):
    if platform.system() not in ("Darwin", "Linux"):
        raise RuntimeError("Local publication platform is not supported by this acceptance run.")
    source = root / "tests/fixtures/configuration/ConversionProcess"
    target = work / "conversion-process"
    foundation.copy_source(source, target)
    project = target / "ConversionProcess.csproj"
    binary = prepared_restore(project, config, source, update)
    original = json.dumps({
        "configurationversion": "fixture-v0", "enabled": ["metadata", "artifact"],
        "metadata": "metadata", "artifact": "artifact", "identities": [], "capabilities": [], "providers": {}
    }).encode()
    stages = {"staged": "Staged", "write": "Write", "flush": "Flush", "pre-publish": "PrePublish", "post-publish": "Published"}
    results = []
    for barrier, category in stages.items():
        directory = work / f"publication-{barrier}"
        directory.mkdir(mode=0o700)
        old, destination = directory / "original.json", directory / "converted.json"
        old.write_bytes(original)
        old.chmod(0o600)
        child = subprocess.Popen(["dotnet", str(binary), str(old), str(destination), category],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ)
                if not selector.select(timeout=30) or child.stdout.readline().strip() != f"barrier:{category}":
                    raise RuntimeError("Conversion child did not reach its exact publication barrier.")
            staged = list(directory.glob(".hoard-configuration-*.tmp"))
            if barrier != "post-publish" and len(staged) != 1:
                raise RuntimeError("Missing exclusive conversion staging proof.")
            for path in staged:
                if path.is_symlink() or path.stat().st_mode & 0o077:
                    raise RuntimeError("Conversion staging is not owner-private.")
            child.kill()
            child.communicate(timeout=10)
            if old.read_bytes() != original or destination.exists() != (barrier == "post-publish"):
                raise RuntimeError("Interrupted conversion changed its original or exposed a partial destination.")
            if destination.exists():
                current = json.loads(destination.read_text())
                if current.get("configurationversion") != 1 or current.get("enabledmodules") != ["metadata", "artifact"]:
                    raise RuntimeError("Interrupted publication produced incomplete current configuration.")
                if destination.stat().st_mode & 0o077:
                    raise RuntimeError("Published conversion is not owner-private.")
            for path in staged:
                if path.exists():
                    path.unlink()
            results.append({"barrier": barrier, "passed": True})
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)
    evidence = {"os": platform.system(), "filesystem": f"tested-local-device-{work.stat().st_dev}",
                "barriers": [item["barrier"] for item in results], "passed": len(results) == len(PUBLICATION_BARRIERS)}
    verify_publication(evidence)
    return project, evidence


def configuration_graphs(root, work, proofs, hosts, old_provider, consumer, registration, conversion):
    ownership = {
        "Hoard.Abstractions": "Abstractions", "Hoard.Core": "Core", "Hoard.Hosting": "Hosting",
        "Hoard.Application": "Application", "NuGet.Versioning": "Versioning",
        "Microsoft.Extensions.DependencyInjection.Abstractions": "Di", "Microsoft.AspNetCore.TestHost": "Sdk",
        "LifecycleHost.Configuration": "Host", "LifecycleHost.Configuration.Custom": "Host",
        "LegacyOptions": "Metadata", "Hoard.Fixtures.Configuration.LegacyOptions": "Metadata",
        "LifecycleConsumer": "Host", "RegistrationConsumer": "Host", "ConversionProcess": "Host"
    }
    for proof in proofs:
        ownership[proof["id"]] = proof["id"].removeprefix("Hoard.Fixtures.Lifecycle.").split(".")[0]
    projects = [("platform", [root / f"src/Hoard.{name}/Hoard.{name}.csproj"
                              for name in ("Abstractions", "Core", "Hosting", "Application")])]
    projects += [(proof["id"].removeprefix("Hoard.Fixtures.Lifecycle."), [Path(proof["project"])]) for proof in proofs]
    projects += list(zip(("configured-baseline", "configured-custom"), ([host] for host in hosts)))
    projects += [("old-provider", [old_provider]), ("lifecycle-consumer", [consumer]),
                 ("registration", [registration]), ("conversion-process", [conversion])]
    graphs = []
    for name, inputs in projects:
        graph = phase("actual packed graph inspection", foundation.inspection_graph, inputs, ownership)
        graph["scanId"] = name
        graphs.append(graph)
    return graphs


def result_names(path):
    root = ET.parse(path).getroot()
    return [node.get("testName", "") for node in root.iter()
            if node.tag.split("}")[-1] == "UnitTestResult" and node.get("outcome") == "Passed"]


def case_inventory(names):
    if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
        raise RuntimeError("Missing actual configuration case scenarios.")
    cases = [{"id": case, "tests": sorted({name for name in names if scenario_name(name) in REQUIRED_TESTS[case]}), "passed": True}
             for case in CASES]
    verify_cases(cases)
    return cases


def exact_inventory(entries, key, expected):
    return isinstance(entries, list) and all(
        isinstance(entry, dict) and isinstance(entry.get(key), str) for entry in entries) and \
        sorted(entry[key] for entry in entries) == sorted(expected)


def verify_full_evidence(evidence):
    if not isinstance(evidence, dict) or evidence.get("toolingPassed") is not True or \
            not exact_inventory(evidence.get("graphs"), "scanId", GRAPH_IDS) or \
            not exact_inventory(evidence.get("oldBinaries"), "name", ("LegacyOptions", "LifecycleConsumer")) or \
            not exact_inventory(evidence.get("packages"), "id", ("Hoard.Fixtures.Lifecycle." + name for name in GRAPH_IDS[1:7])):
        raise RuntimeError("Missing actual configuration acceptance evidence.")
    if any(not isinstance(graph.get("projects"), list) or not graph["projects"] or
           not isinstance(graph.get("ownership"), dict) or not graph["ownership"] for graph in evidence["graphs"]):
        raise RuntimeError("Missing actual configuration acceptance graph evidence.")
    journeys = evidence.get("journeys")
    legacy = next(entry for entry in evidence["oldBinaries"] if entry["name"] == "LegacyOptions")
    expected = {(distribution, name) for distribution in ("baseline", "custom")
                for name in (*JOURNEYS, *(() if distribution == "baseline" else ("configured-custom-artifact",)))}
    if not isinstance(journeys, list) or len(journeys) != len(expected) or any(
            not isinstance(entry, dict) or entry.get("passed") is not True or
            type(entry.get("events")) is not int or entry["events"] <= 0 or
            not isinstance(entry.get("name"), str) or not isinstance(entry.get("distribution"), str) or
            not isinstance(entry.get("providerAssembly"), str) or not entry["providerAssembly"] or
            not isinstance(entry.get("providerSha256"), str) or entry["providerSha256"] != legacy.get("sha256") or
            not isinstance(entry.get("hostSha256"), str) or not re.fullmatch("[0-9a-f]{64}", entry["hostSha256"])
            for entry in journeys) or {(entry["distribution"], entry["name"]) for entry in journeys} != expected or any(
                len({entry["hostSha256"] for entry in journeys if entry["distribution"] == distribution}) != 1
                for distribution in ("baseline", "custom")):
        raise RuntimeError("Missing actual configuration acceptance journey evidence.")
    for entry in journeys:
        verify_binary(Path(entry["providerAssembly"]), entry["providerSha256"])
    for entry in evidence["oldBinaries"]:
        if entry.get("baseline") != BASELINE or any(not isinstance(entry.get(key), str) or not entry[key]
                                                  for key in ("assembly", "assets", "sha256")) or \
                not Path(entry["assets"]).is_file():
            raise RuntimeError("Missing actual configuration acceptance binary provenance.")
        verify_binary(Path(entry["assembly"]), entry["sha256"])
    feeds = set()
    for entry in evidence["packages"]:
        if any(not isinstance(entry.get(key), str) or not entry[key] for key in ("package", "sha512", "project", "assets")) or \
                not isinstance(entry.get("sourceHashes"), dict) or not entry["sourceHashes"] or \
                not all(Path(entry[key]).is_file() for key in ("project", "assets")):
            raise RuntimeError("Missing actual configuration acceptance package provenance.")
        package = Path(entry["package"])
        feeds.add(package.parent)
        verify_package(package, package.parent, entry["sha512"])
    if len(feeds) != 1:
        raise RuntimeError("Invalid configuration acceptance package feed provenance.")
    verify_cases(evidence.get("cases"))
    verify_publication(evidence.get("publication"))


def complete_acceptance(root, work, update, retained_directory=None):
    retained = prepare_baseline(root, work, update)
    config, proofs = phase("independent local package preparation", lifecycle.prepare_packages, root, work, update)
    old_provider, consumer = compatibility(root, work, config, retained, update, retained_directory)
    registration = phase("retained F-01 registration compatibility", lifecycle.registration_compatibility,
                         root, work, config, update, "registration-baseline")
    hosts, journeys = configured_journeys(root, work, config, retained, update)
    conversion, publication = interrupted_publication(root, work, config, update)
    graphs = configuration_graphs(root, work, proofs, hosts, old_provider, consumer, registration, conversion)
    evidence = {"graphs": graphs, "journeys": journeys, "oldBinaries": retained, "publication": publication,
                "packages": proofs}
    manifest = work / "configuration-evidence.json"
    manifest.write_text(json.dumps(evidence, indent=2))
    os.environ["HOARD_CONFIGURATION_EVIDENCE"] = str(manifest)
    os.environ.pop("NUGET_PACKAGES", None)
    architecture = root / "tests/architecture/Hoard.Architecture.Tests/Hoard.Architecture.Tests.csproj"
    run("dotnet", "test", str(architecture), "-c", "Release", "--no-build", "--no-restore",
        "--filter", "FullyQualifiedName~ConfigurationBoundaryTests", "--logger", "trx;LogFileName=configuration-architecture.trx",
        "--results-directory", str(work / "results"), "-v", "minimal")
    boundary_count = test_count(work / "results/configuration-architecture.trx")
    count = focused_tests(root, work, "FullyQualifiedName~Configuration|FullyQualifiedName~ConfiguredComposition")
    for project in [root / "Hoard.slnx", *(Path(proof["project"]) for proof in proofs), *hosts,
                    old_provider, consumer, registration, conversion]:
        phase("format/analyzers", run, "dotnet", "format", str(project), "--verify-no-changes", "--no-restore", "-v", "quiet")
    run("python3", "-m", "unittest", "discover", "-s", str(root / "tests/tooling"), "-v")
    evidence["toolingPassed"] = True
    evidence["cases"] = case_inventory(result_names(work / "results/configuration.trx")
                                       + result_names(work / "results/configuration-architecture.trx"))
    for entry in retained:
        verify_binary(Path(entry["assembly"]), entry["sha256"])
    verify_full_evidence(evidence)
    manifest.write_text(json.dumps(evidence, indent=2))
    print(f"Configuration acceptance: {count} tests, {boundary_count} boundary proofs, {len(journeys)} package-only journeys "
          f"and {len(publication['barriers'])} real interrupted-publication barriers passed on {publication['os']}; CFG-01..36 complete.")


def focused_tests(root, work, selection):
    if not selection.strip():
        raise RuntimeError("Empty configuration test selection.")
    project = root / "tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj"
    run("dotnet", "restore", str(project), "--locked-mode", "-v", "quiet")
    run("dotnet", "test", str(project), "-c", "Release", "--no-restore", "--filter", selection,
        "--logger", "trx;LogFileName=configuration.trx", "--results-directory", str(work / "results"), "-v", "minimal")
    return test_count(work / "results/configuration.trx")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--update-locks", action="store_true")
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--retain-baseline", type=Path)
    parser.add_argument("--evidence-directory", type=Path)
    parser.add_argument("--retained-baseline", type=Path)
    parser.add_argument("--filter")
    args = parser.parse_args()
    if args.retain_baseline is not None and not args.baseline_only:
        parser.error("--retain-baseline requires --baseline-only")
    partial = args.baseline_only or args.filter is not None
    if args.retained_baseline is not None and partial:
        parser.error("--retained-baseline requires full acceptance")
    root = args.root.resolve()
    before = lock_hashes(root)
    retained_work = args.evidence_directory is not None and not partial
    work = create_workspace(destination=args.evidence_directory if retained_work else None)
    passed = False
    try:
        if args.baseline_only:
            retained = prepare_baseline(root, work, args.update_locks)
            if args.retain_baseline is not None:
                retain_baseline(retained, args.retain_baseline)
            print(f"Partial configuration baseline proof: {len(retained)} retained binaries; not full acceptance.")
        elif args.filter is not None:
            count = focused_tests(root, work, args.filter)
            print(f"Partial configuration proof: {count} tests; not full CFG-01..36 acceptance.")
        else:
            complete_acceptance(root, work, args.update_locks, args.retained_baseline)
        if not args.update_locks:
            verify_locks(root, before)
        passed = True
    finally:
        try:
            if retained_work:
                (work / "result.json").write_text(json.dumps({
                    "kind": "acceptance", "scope": "full", "status": "passed" if passed else "failed", "fullAcceptance": passed
                }, indent=2))
            elif args.evidence_directory is not None:
                retain_evidence(work, args.evidence_directory, "baseline" if args.baseline_only else "source-tests", passed)
        finally:
            if not retained_work:
                cleanup_workspace(work)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
    except (OSError, ValueError, ET.ParseError):
        raise SystemExit("Configuration evidence preparation failed; inspect local inputs privately.") from None
