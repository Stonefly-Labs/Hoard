"""Bounded, fail-closed fixture-only discovery evidence."""

import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import uuid
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import configuration_evidence as configuration
import foundation_evidence as foundation
import lifecycle_evidence as lifecycle


BASELINE = "7fd73267a5154583363c94e9e85b9bac7d4a16b3"
CASES = tuple(f"D{number:02}" for number in range(1, 41))
SUITES = ("contracts", "publication", "inventory", "capabilities", "http",
          "adapters", "consumer", "bounds", "performance", "compatibility")
JOURNEYS = ("baseline", "bundled-restart", "invalid-replacement", "recovery", "custom-rebuild")
FEED_PACKAGES = tuple(f"Hoard.{name}.0.1.0.nupkg" for name in ("Abstractions", "Core", "Hosting", "Application")) + tuple(
    f"Hoard.Fixtures.Lifecycle.{name}.0.1.0.nupkg" for name in
    ("Protocol.One", "Protocol.Two", "Metadata", "Artifact.One", "Artifact.Two", "Identity")) + (
    "Hoard.Fixtures.Configuration.LegacyOptions.0.1.0.nupkg",)
CASE_TESTS = {
    "D01": ("Inclusion_registration_selection_and_roles_are_independent",),
    "D02": ("Inclusion_registration_selection_and_roles_are_independent", "Unsupported_actions_hide_and_usable_operations_still_require_separate_permission"),
    "D03": ("Only_approved_literals_survive_and_owned_failures_keep_closed_safe_guidance",),
    "D04": ("All_families_and_multiple_protocol_identity_selections_are_preserved_without_settings",),
    "D05": ("Disabled_operational_failures_do_not_validate_resolve_construct_or_probe", "Enabled_counterparts_preserve_active_validation_and_secret_gates"),
    "D06": ("Invalid_static_associations_reject_before_construction", "Module_limit_checks_the_union_before_activation"),
    "D07": ("Exact_fixture_support_and_real_owned_route_are_required",),
    "D08": ("Exact_fixture_support_and_real_owned_route_are_required",),
    "D09": ("Only_the_actual_owned_method_satisfies_the_binding",),
    "D10": ("Effective_service_proof_requires_the_single_unkeyed_owner_added_descriptor",),
    "D11": ("Version_operation_and_multi_owner_scopes_remain_independent_of_unrelated_readiness",),
    "D12": ("Version_operation_and_multi_owner_scopes_remain_independent_of_unrelated_readiness",),
    "D13": ("Optional_absence_removes_only_the_integration_and_enabled_incompatibility_still_rejects",),
    "D14": ("Initial_publication_and_terminal_revisions_are_coherent_without_probes", "Distinct_textual_states_and_safe_actions_are_projected_from_actual_JSON"),
    "D15": ("Explicit_reassessment_updates_one_observation_without_refresh_probes_or_runtime_drain",),
    "D16": ("Failed_start_and_late_unknown_diagnostics_preserve_only_safe_terminal_reports",
            "Terminal_owner_or_dependency_phases_override_ready_usable_action_claims"),
    "D17": ("Failed_start_and_late_unknown_diagnostics_preserve_only_safe_terminal_reports",),
    "D18": ("Both_literal_routes_require_the_same_policy_without_disclosure",),
    "D19": ("Both_literal_routes_require_the_same_policy_without_disclosure",),
    "D20": ("Actual_loopback_binding_and_pinned_TLS_are_verified_without_a_public_listener", "Local_posture_policy_uses_the_raw_peer_not_rewritten_connection_state"),
    "D21": ("Raw_peer_precedes_existing_forwarding_filters_regardless_of_opt_in_order", "Trusted_proxy_requires_known_immediate_peer_single_protocol_and_actual_forwarding_result"),
    "D22": ("Only_approved_literals_survive_and_owned_failures_keep_closed_safe_guidance", "Raw_option_metadata_and_disabled_secret_locations_are_not_public_defaults"),
    "D23": ("Invalid_static_associations_reject_before_construction",),
    "D24": ("Serialized_data_description_problems_and_method_rules_match_the_normative_contract",),
    "D25": ("Distinct_textual_states_and_safe_actions_are_projected_from_actual_JSON",
            "Support_state_and_fixture_scope_have_separate_contextual_semantic_lines"),
    "D26": ("Unsupported_actions_hide_and_usable_operations_still_require_separate_permission",
            "Terminal_owner_or_dependency_phases_override_ready_usable_action_claims",
            "Unknown_owner_or_dependency_phases_preserve_inventory_but_never_enable_actions"),
    "D27": ("Generations_denial_failure_and_monotonic_age_never_revive_retained_actions",),
    "D28": ("Distinct_textual_states_and_safe_actions_are_projected_from_actual_JSON",
            "Support_state_and_fixture_scope_have_separate_contextual_semantic_lines"),
    "D29": ("Distinct_textual_states_and_safe_actions_are_projected_from_actual_JSON",),
    "D30": ("Incompatible_required_shapes_are_explicit_failures_not_empty_success", "A_known_operation_name_does_not_authorize_unknown_capability_semantics",
            "Unknown_owner_or_dependency_phases_preserve_inventory_but_never_enable_actions"),
    "D31": ("A_captured_revision_stays_coherent_while_the_authority_changes_without_waiting_for_the_reader",),
    "D32": ("Prepared_discovery_restart_journeys_have_distinct_lifecycles_and_actual_operations", "Generations_denial_failure_and_monotonic_age_never_revive_retained_actions"),
    "D33": ("Cancellation_deadline_and_inconsistent_authority_never_become_successful_observations",),
    "D34": ("Cancellation_during_encoding_releases_owned_buffers_without_disposing_provider_resources",
            "Cancellation_and_deadline_during_HTTP_projection_leave_live_modules_untouched",
            "Deadline_during_actual_encoding_cannot_commit_a_partial_success",
            "Cancellation_deadline_and_inconsistent_authority_never_become_successful_observations"),
    "D35": ("Exact_encoded_byte_bound_is_checked_before_success_headers", "Escaped_UTF8_expansion_cannot_produce_a_partial_success", "Encoding_rejects_oversized_tokens_before_uncapped_writer_allocation"),
    "D36": ("One_hundred_complete_authorized_reads_of_one_thousand_contributions_have_bounded_local_cost",),
    "D37": ("Both_literal_routes_require_the_same_policy_without_disclosure",),
    "D38": ("Binding_requires_the_exact_retained_app_and_owned_source", "Prepared_discovery_graphs_preserve_approved_and_forbidden_directions", "Prepared_discovery_restart_journeys_have_distinct_lifecycles_and_actual_operations"),
    "D39": ("Serialized_data_description_problems_and_method_rules_match_the_normative_contract",),
    "D40": ("Only_approved_literals_survive_and_owned_failures_keep_closed_safe_guidance", "Failed_start_and_late_unknown_diagnostics_preserve_only_safe_terminal_reports"),
}
SUITE_CLASSES = {
    "contracts": ("DiscoveryContractTests", "DiscoveryCatalogTests"),
    "publication": ("DiscoveryPublicationTests", "DiscoveryRaceTests", "DiscoveryLifecycleTests"),
    "inventory": ("DiscoveryInventoryTests", "DiscoveryDisabledTests"),
    "capabilities": ("DiscoveryCapabilityTests", "DiscoveryRouteBindingTests", "DiscoveryServiceBindingTests"),
    "http": ("DiscoveryAuthorizationTests", "DiscoveryDisclosureTests", "DiscoveryWireContractTests", "DiscoveryOwnershipTests"),
    "adapters": ("DiscoveryKestrelAdapterTests", "DiscoveryExposureTests"),
    "consumer": ("DiscoveryPresentationTests", "DiscoveryConsumerRefreshTests", "DiscoveryConsumerCompatibilityTests"),
    "bounds": ("DiscoveryBoundsTests",),
    "performance": ("DiscoveryPerformanceTests",),
    "compatibility": ("DiscoveryRestartTests", "DiscoveryBoundaryTests"),
}
REQUIRED_ADAPTER_SCENARIOS = tuple(
    f"Hoard.Composition.Tests.DiscoveryKestrelAdapterTests.{method}({parameter}: {value})"
    for method, parameter in (
        ("Actual_loopback_binding_and_pinned_TLS_are_verified_without_a_public_listener", "tls"),
        ("Raw_peer_precedes_existing_forwarding_filters_regardless_of_opt_in_order", "registerFirst"))
    for value in ("False", "True"))
MUTATIONS = (
    ("catalog-bound", "src/Hoard.Hosting/Discovery/HoardDiscoveryExtensions.cs",
     "if (!valid) { throw new HoardDiscoverySetupException(); }",
     'if (!valid && Environment.GetEnvironmentVariable("HOARD_DISCOVERY_MUTATION") != "active") { throw new HoardDiscoverySetupException(); }',
     "Invalid_static_associations_reject_before_construction"),
    ("source-identity", "src/Hoard.Hosting/Discovery/HoardDiscoverySource.cs",
     "state.LifecycleId != Lease.Composition.Identity || ", "",
     "Cancellation_deadline_and_inconsistent_authority_never_become_successful_observations"),
    ("source-no-probes", "src/Hoard.Hosting/Discovery/HoardDiscoverySource.cs",
     "var budget = new DiscoveryReadBudget", "Lease.Lifecycle.AssessReadinessAsync().GetAwaiter().GetResult();\n        var budget = new DiscoveryReadBudget",
     "Explicit_reassessment_updates_one_observation_without_refresh_probes_or_runtime_drain"),
    ("single-publication", "src/Hoard.Hosting/Discovery/HoardDiscoverySource.cs",
     "DiscoveryCapabilityEvaluator.Project(modules, catalog, Lease.Composition, state,",
     "DiscoveryCapabilityEvaluator.Project(modules, catalog, Lease.Composition, Lease.Publication!.Capture()!,",
     "A_captured_revision_stays_coherent_while_the_authority_changes_without_waiting_for_the_reader"),
    ("capture-cancellation", "src/Hoard.Hosting/Discovery/DiscoveryReadBudget.cs",
     "cancellationToken.ThrowIfCancellationRequested();", "_ = cancellationToken.IsCancellationRequested;",
     "Cancellation_deadline_and_inconsistent_authority_never_become_successful_observations"),
    ("service-owner", "src/Hoard.Hosting/Discovery/DiscoveryBindingLedger.cs",
     " && owner == binding.OwnerId", "", "Effective_service_proof_requires_the_single_unkeyed_owner_added_descriptor"),
    ("actual-route", "src/Hoard.Hosting/Discovery/DiscoveryCapabilityEvaluator.cs",
     "|| contribution.Routes.Any(route => !bindings.Routes.Contains(route))", "",
     "Only_the_actual_owned_method_satisfies_the_binding"),
    ("tested-support", "src/Hoard.Hosting/Discovery/DiscoveryCapabilityEvaluator.cs",
     'if (contribution.Support != "supported")', 'if (contribution.Support == "mutation-disabled")',
     "Exact_fixture_support_and_real_owned_route_are_required"),
    ("path-protection", "src/Hoard.Hosting/Discovery/DiscoveryRawPeerStartupFilter.cs",
     "context.Request.Path.Value?.TrimEnd('/')", "context.Request.Path.Value",
     "Both_literal_routes_require_the_same_policy_without_disclosure"),
    ("encoder-allocation", "src/Hoard.Application/Discovery/DiscoveryResponseWriter.cs",
     "if (sizeHint > 16384) { throw new ResponseLimitException(); }", "",
     "Encoding_rejects_oversized_tokens_before_uncapped_writer_allocation"),
    ("encoding-deadline", "src/Hoard.Application/Discovery/DiscoveryResponseWriter.cs",
     "options.TimeProvider.GetElapsedTime(started) >= options.Deadline",
     "options.TimeProvider.GetElapsedTime(started) >= TimeSpan.MaxValue",
     "Deadline_during_actual_encoding_cannot_commit_a_partial_success"),
    ("action-semantics", "tests/fixtures/discovery/ReferenceConsumer/PresentationProjector.cs",
     'var known = module.Id == "protocol" && capability is { Id: "inspect", Version: "0.1.0", OperationId: "inspect" }\n'
     '                    && capability.Owners.SequenceEqual(["protocol"]) && capability.Understood && module.Understood;',
     'var known = capability.OperationId == "inspect" && capability.Understood && module.Understood;',
     "A_known_operation_name_does_not_authorize_unknown_capability_semantics"),
)
create_workspace = configuration.create_workspace
cleanup_workspace = configuration.cleanup_workspace
verify_binary = configuration.verify_binary
verify_package = configuration.verify_package
lock_hashes = lifecycle.lock_hashes
verify_locks = lifecycle.verify_locks
_log = None


def run(*args, cwd=None, env=None, input=None):
    try:
        result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=False, timeout=600,
                                env={**os.environ, **(env or {})}, input=input)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Discovery command timed out: {Path(args[0]).name}") from None
    if _log is not None:
        with _log.open("a") as log:
            log.write(result.stdout)
    if result.returncode:
        codes = re.findall(r"error (?:CS|NU|MSB)\d+|error WHITESPACE|Failed [A-Za-z0-9._]+", result.stdout)
        detail = " [" + ", ".join(codes[:10]) + "]" if codes else ""
        raise RuntimeError(f"Discovery command failed: {Path(args[0]).name}{detail}")
    return result.stdout


def exact_inventory(entries, identities):
    return (isinstance(entries, list) and len(entries) == len(identities)
            and all(isinstance(entry, dict) and isinstance(entry.get("id"), str) for entry in entries)
            and sorted(entry["id"] for entry in entries) == sorted(identities))


def verify_cases(entries):
    if not exact_inventory(entries, CASES) or any(
            entry.get("passed") is not True or not isinstance(entry.get("tests"), list)
            or not entry["tests"] or any(not isinstance(test, str) or not test.strip()
                                       for test in entry["tests"]) for entry in entries):
        raise RuntimeError("Missing, duplicate, failed or incomplete discovery case inventory.")
    for entry in entries:
        methods = {configuration.scenario_name(name).rsplit(".", 1)[-1] for name in entry["tests"]}
        if not set(CASE_TESTS[entry["id"]]).issubset(methods):
            raise RuntimeError("Stale or mismatched discovery case inventory.")


def verify_suites(entries):
    if not exact_inventory(entries, SUITES) or any(
            entry.get("passed") is not True or type(entry.get("tests")) is not int
            or entry["tests"] <= 0 for entry in entries):
        raise RuntimeError("Missing, duplicate, failed or empty discovery suite inventory.")


def verify_performance(evidence, run_id=None):
    if not isinstance(evidence, dict):
        raise RuntimeError("Invalid discovery performance evidence.")
    samples = evidence.get("samples")
    if (not isinstance(samples, list) or len(samples) != 100
            or any(type(value) not in (float, int) or not math.isfinite(value) or value < 0 for value in samples)
            or evidence.get("modules") != 100 or evidence.get("contributionsPerModule") != 10
            or evidence.get("concurrency") != 10 or evidence.get("completeBodies") != 100
            or not isinstance(evidence.get("bytes"), list) or len(evidence["bytes"]) != 100
            or any(type(value) is not int or not 0 < value <= 4 * 1024 * 1024 for value in evidence["bytes"])
            or not all(isinstance(evidence.get(key), str) and evidence[key].strip() for key in ("sdk", "os"))
            or not isinstance(evidence.get("resourceDeltas"), dict) or not evidence["resourceDeltas"]
            or set(evidence["resourceDeltas"]) != {"constructors", "probes", "secrets", "serviceCalls", "connections", "activeResources"}
            or any(type(value) is not int or value != 0 for value in evidence["resourceDeltas"].values())
            or run_id is not None and evidence.get("runId") != run_id
            or sorted(samples)[94] > 2):
        raise RuntimeError("Missing, incomplete or failed discovery performance evidence.")
    return sorted(samples)[94]


def verify_journeys(entries):
    expected = {(distribution, name) for distribution in ("baseline", "custom")
                for name in JOURNEYS if distribution == "custom" or name != "custom-rebuild"}
    if (not isinstance(entries, list) or len(entries) != len(expected)
            or any(not isinstance(entry, dict) or entry.get("passed") is not True
                   or (entry.get("distribution"), entry.get("id")) not in expected
                   or not re.fullmatch("[0-9a-f]{64}", entry.get("hostSha256", ""))
                   for entry in entries)
            or {(entry["distribution"], entry["id"]) for entry in entries} != expected):
        raise RuntimeError("Missing, duplicate, stale or failed discovery journey inventory.")
    successful = [entry for entry in entries if entry["id"] != "invalid-replacement"]
    try:
        for entry in successful:
            if str(uuid.UUID(entry["lifecycleId"])) != entry["lifecycleId"]:
                raise ValueError()
    except (KeyError, TypeError, ValueError, AttributeError):
        raise RuntimeError("Missing actual discovery journey lifecycle identity.") from None
    if (len({entry.get("lifecycleId") for entry in successful}) != len(successful)
            or any(not isinstance(entry.get("lifecycleId"), str) or entry.get("routeCalls") != 1
                   or entry.get("serviceCalls") != 1 or type(entry.get("bytes")) is not int
                   or not 0 < entry["bytes"] <= 4 * 1024 * 1024 for entry in successful)
            or any(len({entry["hostSha256"] for entry in entries if entry["distribution"] == distribution}) != 1
                   for distribution in ("baseline", "custom"))):
        raise RuntimeError("Missing actual discovery journey operation/lifecycle evidence.")
    if any(type(entry.get("diagnostics")) is not int or entry["diagnostics"] <= 0 or entry.get("activityDelta") != 0
           for entry in entries if entry["id"] == "invalid-replacement"):
        raise RuntimeError("Missing rejected-replacement isolation evidence.")


def results(path):
    tree = ET.parse(path).getroot()
    nodes = [node for node in tree.iter() if node.tag.split("}")[-1] == "UnitTestResult"]
    if not nodes or any(node.get("outcome") != "Passed" or not node.get("testName") for node in nodes):
        raise RuntimeError("Missing, skipped or failed discovery test results.")
    names = [node.get("testName") for node in nodes]
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate discovery test results.")
    return names


def verify_scenarios(names, expected):
    if (not isinstance(expected, list) or not expected
            or any(not isinstance(name, str) or not name.strip() for name in expected)
            or len(expected) != len(set(expected)) or sorted(names) != sorted(expected)
            or not set(REQUIRED_ADAPTER_SCENARIOS).issubset(names)
            or any(not any(f".{name}." in result for result in names)
                   for classes in SUITE_CLASSES.values() for name in classes)):
        raise RuntimeError("Missing or mismatched mandatory discovery scenario/class inventory.")


def listed_scenarios(project, selection):
    output = run("dotnet", "test", str(project), "-c", "Release", "--no-build", "--no-restore",
                 "--filter", selection, "--list-tests", "-v", "quiet")
    names = [line.strip() for line in output.splitlines()
             if re.match(r"\s+Hoard\.(Composition|Architecture)\.Tests\.", line)]
    if not names or len(names) != len(set(names)):
        raise RuntimeError("Missing or duplicate declared discovery scenario inventory.")
    return names


def inventory(names):
    cases = [{"id": case, "passed": True, "tests": sorted(name for name in names
              if configuration.scenario_name(name).rsplit(".", 1)[-1] in CASE_TESTS[case])} for case in CASES]
    suites = [{"id": suite, "passed": True, "tests": sum(any(
        f".{name}." in result for name in SUITE_CLASSES[suite]) for result in names)} for suite in SUITES]
    verify_cases(cases)
    verify_suites(suites)
    return cases, suites


def verify_retained_inputs(retained, directory):
    directory = directory.resolve()
    try:
        saved = json.loads((directory / "retained-binaries.json").read_text())
    except (OSError, ValueError):
        raise RuntimeError("Invalid retained pre-F-04 input manifest.") from None
    if not configuration.exact_inventory(saved, "name", ("RetainedLifecycle", "RetainedConfiguration", "LegacyOptions")):
        raise RuntimeError("Missing retained pre-F-04 binary inventory.")
    for entry in saved:
        if entry.get("baseline") != BASELINE or any(
                not isinstance(entry.get(key), str) or not entry[key] for key in ("assembly", "assets", "sha256")):
            raise RuntimeError("Invalid retained pre-F-04 identity.")
        binary, assets = Path(entry["assembly"]), Path(entry["assets"])
        if binary.name != entry["name"] + ".dll" or any(
                not path.resolve().is_relative_to(directory) or not path.is_file() for path in (binary, assets)):
            raise RuntimeError("Invalid retained pre-F-04 location.")
        verify_binary(binary, entry["sha256"])
        current = next(value for value in retained if value["name"] == entry["name"])
        if entry.get("sourceHashes") != current["sourceHashes"]:
            raise RuntimeError("Retained pre-F-04 source recipe changed.")
        dependencies = {
            source.name: hashlib.sha256(source.read_bytes()).hexdigest()
            for source in binary.parent.glob("*.dll")}
        if (not isinstance(entry.get("baselineDependencyHashes"), dict)
                or dependencies != entry["baselineDependencyHashes"]
                or hashlib.sha256(assets.read_bytes()).hexdigest() != entry.get("baselineAssetsSha256")):
            raise RuntimeError("Retained pre-F-04 dependency inventory or assets hash changed.")
        current["baselineDependencyHashes"] = entry["baselineDependencyHashes"]
        current["baselineAssetsSha256"] = entry["baselineAssetsSha256"]
        target = Path(current["assembly"]).parent
        for source in binary.parent.iterdir():
            if source.is_file() and source.suffix in (".dll", ".pdb", ".json"):
                if not source.resolve().is_relative_to(directory):
                    raise RuntimeError("Unsafe retained dependency location.")
                shutil.copy2(source, target / source.name)
        current["sha256"] = entry["sha256"]
        verify_binary(Path(current["assembly"]), current["sha256"])


def compatibility(root, work, config, retained, update):
    projects = {}
    for name in ("RetainedLifecycle", "RetainedConfiguration", "ApplicationConsumer", "NonWebConsumer"):
        source = root / f"tests/fixtures/discovery/{name}"
        target = work / f"new-consumers/discovery/{name}"
        foundation.copy_source(source, target)
        if name == "RetainedLifecycle":
            foundation.copy_source(root / "tests/fixtures/configuration/LifecycleConsumer", work / "new-consumers/configuration/LifecycleConsumer")
        if name == "NonWebConsumer" and not (target.parent / "ApplicationConsumer").exists():
            foundation.copy_source(root / "tests/fixtures/discovery/ApplicationConsumer", target.parent / "ApplicationConsumer")
        project = target / f"{name}.csproj"
        foundation.restore(project, config, update, source)
        binary = foundation.build(project)
        expected = {"RetainedLifecycle": "lifecycle-compatible", "RetainedConfiguration": "configuration-compatible"}.get(
            name, "application-discovery-compatible")
        if run("dotnet", str(binary)).strip() != expected:
            raise RuntimeError("New source discovery consumer failed.")
        runtime = json.loads(binary.with_suffix(".runtimeconfig.json").read_text())
        if not any(framework["name"] == "Microsoft.AspNetCore.App"
                   for framework in runtime["runtimeOptions"].get("frameworks", [])):
            raise RuntimeError("Missing packed shared-framework propagation.")
        if name.startswith("Retained"):
            old = next(entry for entry in retained if entry["name"] == name)
            for dependency in binary.parent.iterdir():
                if dependency.is_file() and dependency.name not in (f"{name}.dll", f"{name}.pdb"):
                    shutil.copy2(dependency, Path(old["assembly"]).parent / dependency.name)
            verify_binary(Path(old["assembly"]), old["sha256"])
            if run("dotnet", old["assembly"]).strip() != expected:
                raise RuntimeError("Unchanged retained binary failed against new platform.")
        projects[name] = project
    return projects


def package_journeys(root, work, config, retained, update):
    source = root / "examples/LifecycleHost"
    projects, journeys, observations, bodies = [], [], [], []
    before = foundation.source_hashes(root)
    legacy = next(entry for entry in retained if entry["name"] == "LegacyOptions")
    provider_hashes = None
    for distribution, relative in (("baseline", "Discovery/LifecycleHost.Discovery.csproj"),
                                   ("custom", "Discovery/Custom/LifecycleHost.Discovery.Custom.csproj")):
        target = work / "discovery-hosts" / distribution
        foundation.copy_source(source, target)
        project = target / relative
        if ET.parse(project).findall(".//ProjectReference"):
            raise RuntimeError("Discovery distribution must use packages only.")
        foundation.restore(project, config, update, source / Path(relative).parent)
        binary = foundation.build(project)
        provider = binary.parent / "LegacyOptions.dll"
        shutil.copy2(legacy["assembly"], provider)
        verify_binary(provider, legacy["sha256"])
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        output = json.loads(run("dotnet", str(binary), cwd=project.parent))
        actual = output.get("journeys")
        if not isinstance(actual, list) or not isinstance(output.get("observations"), list) or not output["observations"]:
            raise RuntimeError("Missing actual discovery package JSON.")
        journeys.extend({**entry, "distribution": distribution, "hostSha256": digest} for entry in actual)
        observations.extend(output["observations"])
        if not isinstance(output.get("responseBodies"), list):
            raise RuntimeError("Missing actual serialized discovery bodies.")
        bodies.extend(output["responseBodies"])
        verify_binary(binary, digest)
        verify_binary(provider, legacy["sha256"])
        stable = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in binary.parent.glob("*.dll") if path.name.startswith("Hoard.Fixtures.Lifecycle.")}
        if not stable:
            raise RuntimeError("Missing independent provider runtime hashes.")
        if provider_hashes is not None and any(stable.get(name) != value for name, value in provider_hashes.items()):
            raise RuntimeError("Custom rebuild changed unrelated provider binaries.")
        provider_hashes = stable
        assets = json.loads((project.parent / "obj/project.assets.json").read_text())
        present = any(identity.startswith("Hoard.Fixtures.Lifecycle.Artifact.Two/") for identity in assets["libraries"])
        if present != (distribution == "custom"):
            raise RuntimeError("Discovery distribution package selection mismatch.")
        projects.append(project)
    if foundation.source_hashes(root) != before:
        raise RuntimeError("Discovery journeys changed unrelated platform/provider sources.")
    verify_journeys(journeys)
    verify_observations(journeys, observations, bodies)
    return projects, journeys, observations, bodies


def verify_observations(journeys, observations, bodies):
    successful = {entry["lifecycleId"]: entry for entry in journeys if entry["id"] != "invalid-replacement"}
    if not isinstance(observations, list) or not isinstance(bodies, list) or len(observations) != 7 or len(bodies) != 7:
        raise RuntimeError("Missing actual serialized discovery body inventory.")
    seen = set()
    for observation, encoded in zip(observations, bodies, strict=True):
        try:
            if not isinstance(encoded, str) or len(encoded) > 4 * ((4 * 1024 * 1024 + 2) // 3):
                raise ValueError()
            body = base64.b64decode(encoded, validate=True)
            identity = observation["observation"]["lifecycleId"]
            entry = successful[identity]
            if (identity in seen or json.loads(body) != observation or len(body) != entry["bytes"]
                    or observation["schemaVersion"] != 1 or observation["host"]["phase"] != "running"
                    or observation["host"]["startupAdmission"] is not True
                    or observation["observation"]["readinessAssessedAt"] is None):
                raise ValueError()
            seen.add(identity)
        except (ValueError, KeyError, TypeError):
            raise RuntimeError("Invalid or stale actual serialized discovery body.") from None
    if seen != set(successful):
        raise RuntimeError("Incomplete actual serialized discovery lifecycle inventory.")


def input_hashes(root):
    paths = set()
    for relative in ("src", "tests/fixtures/discovery", "tests/fixtures/lifecycle", "tests/fixtures/configuration",
                     "tests/fixtures/architecture", "tests/integration/Hoard.Composition.Tests", "tests/tooling",
                     "tests/architecture/Hoard.Architecture.Tests", "examples/LifecycleHost", "scripts"):
        paths.update(path for path in (root / relative).rglob("*")
                     if path.suffix in (".cs", ".csproj", ".py", ".json") and path.name != "packages.lock.json"
                     and not {"bin", "obj"}.intersection(path.parts))
    paths.add(root / "specs/004-module-discovery/contracts/openapi.json")
    paths.update(root / relative for relative in ("Directory.Build.props", "Directory.Packages.props", "global.json"))
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def verify_full_evidence(evidence, root, work):
    if (not isinstance(evidence, dict) or not isinstance(evidence.get("runId"), str)
            or evidence.get("runId") != os.environ.get("HOARD_DISCOVERY_RUN_ID")
            or evidence.get("toolingPassed") is not True or evidence.get("referenceConsumerPassed") is not True
            or not isinstance(evidence.get("inputHashes"), dict) or not evidence["inputHashes"]
            or evidence.get("inputHashes") != input_hashes(root)
            or not isinstance(evidence.get("mutations"), list) or not evidence["mutations"]):
        raise RuntimeError("Missing, stale or incomplete discovery acceptance evidence.")
    if not configuration.exact_inventory(evidence["mutations"], "id", [entry[0] for entry in MUTATIONS]) or any(
            entry.get("passed") is not True or not entry.get("failedTests")
            or entry.get("originalSha256") == entry.get("mutantSha256")
            or any(name not in evidence.get("testNames", []) for name in entry["failedTests"])
            for entry in evidence["mutations"]):
        raise RuntimeError("Missing actual runtime red/green mutation evidence.")
    actual = results(work / "results/discovery.trx") + results(work / "results/discovery-architecture.trx")
    verify_scenarios(actual, evidence.get("expectedTestNames"))
    cases, suites = inventory(actual)
    if evidence.get("testNames") != actual or evidence.get("cases") != cases or evidence.get("suites") != suites:
        raise RuntimeError("Mismatched actual discovery red/green result inventory.")
    for identity, relative, original, replacement, method in MUTATIONS:
        entry = next(value for value in evidence["mutations"] if value["id"] == identity)
        source = (root / relative).read_text()
        if (source.count(original) != 1
                or entry.get("originalSha256") != hashlib.sha256(source.encode()).hexdigest()
                or entry.get("mutantSha256") != hashlib.sha256(source.replace(original, replacement).encode()).hexdigest()
                or entry.get("failedTests") != runtime_failures(work / "mutation-results" / identity / "red.trx", method)):
            raise RuntimeError("Stale or mismatched actual runtime mutation evidence.")
    verify_journeys(evidence.get("journeys"))
    verify_observations(evidence["journeys"], evidence.get("observations"), evidence.get("responseBodies"))
    verify_performance(evidence.get("performance"), evidence["runId"])
    if not configuration.exact_inventory(evidence.get("oldBinaries"), "name",
                                         ("RetainedLifecycle", "RetainedConfiguration", "LegacyOptions")):
        raise RuntimeError("Missing discovery binary compatibility evidence.")
    for entry in evidence["oldBinaries"]:
        if (entry.get("baseline") != BASELINE or not isinstance(entry.get("sourceHashes"), dict)
                or not entry["sourceHashes"] or any(
                    not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value)
                    for value in entry["sourceHashes"].values())
                or not isinstance(entry.get("baselineDependencyHashes"), dict) or not entry["baselineDependencyHashes"]
                or any(not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value)
                       for value in entry["baselineDependencyHashes"].values())
                or not re.fullmatch("[0-9a-f]{64}", entry.get("baselineAssetsSha256", ""))
                or any(not isinstance(entry.get(key), str) or not Path(entry[key]).resolve().is_relative_to(work.resolve())
                       or not Path(entry[key]).is_file() for key in ("assembly", "assets"))):
            raise RuntimeError("Invalid discovery binary provenance.")
        verify_binary(Path(entry["assembly"]), entry["sha256"])
    expected_graphs = ("platform", "Protocol.One", "Protocol.Two", "Metadata", "Artifact.One", "Artifact.Two", "Identity",
                       "baseline", "custom", "old-provider", "lifecycle-consumer", "configuration-consumer", "registration",
                       "application-consumer", "nonweb-consumer", "permitted-application", "forbidden-provider", "cross-slice")
    if not configuration.exact_inventory(evidence.get("graphs"), "scanId", expected_graphs) or any(
            not entry.get("projects") or not entry.get("ownership") for entry in evidence["graphs"]):
        raise RuntimeError("Missing discovery graph evidence.")
    if not configuration.exact_inventory(evidence.get("feedPackages"), "id", FEED_PACKAGES):
        raise RuntimeError("Missing immutable discovery package provenance.")
    expected_packages = sorted(path.name for path in (work / "feed").glob("*.nupkg"))
    if sorted(entry.get("id", "") for entry in evidence["feedPackages"]) != expected_packages:
        raise RuntimeError("Incomplete discovery package inventory.")
    for entry in evidence["feedPackages"]:
        if Path(entry["package"]).name != entry["id"]:
            raise RuntimeError("Mismatched discovery package identity.")
        verify_package(Path(entry["package"]), work / "feed", entry["sha512"])


def runtime_failures(path, method):
    tree = ET.parse(path).getroot()
    entries = [node for node in tree.iter() if node.tag.split("}")[-1] == "UnitTestResult"]
    failed = [node.get("testName", "") for node in entries if node.get("outcome") == "Failed"]
    if (not failed or len(failed) != len(set(failed))
            or any(node.get("outcome") not in ("Passed", "Failed") for node in entries)
            or any(configuration.scenario_name(name).rsplit(".", 1)[-1] != method for name in failed)):
        raise RuntimeError("Missing intended discovery runtime assertion failure.")
    return failed


def mutations(root, work):
    target = work / "mutations"
    for relative in ("src", "tests/integration/Hoard.Composition.Tests", "tests/fixtures/discovery/ReferenceConsumer"):
        foundation.copy_source(root / relative, target / relative)
    for relative in ("Directory.Build.props", "Directory.Packages.props", "global.json"):
        shutil.copy2(root / relative, target / relative)
    shutil.copy2(root / "tests/FoundationEvidence.cs", target / "tests/FoundationEvidence.cs")
    contract = target / "specs/004-module-discovery/contracts"
    contract.mkdir(parents=True)
    shutil.copy2(root / "specs/004-module-discovery/contracts/openapi.json", contract / "openapi.json")
    project = target / "tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj"
    run("dotnet", "restore", str(project), "--locked-mode", "-v", "quiet")
    detected = []
    for identity, relative, original, replacement, method in MUTATIONS:
        path = target / relative
        source = path.read_text()
        if source.count(original) != 1:
            raise RuntimeError(f"Stale discovery mutation recipe: {identity}.")
        mutant = source.replace(original, replacement)
        path.write_text(mutant)
        directory = work / "mutation-results" / identity
        try:
            try:
                run("dotnet", "test", str(project), "-c", "Release", "--no-restore",
                    "--filter", f"FullyQualifiedName~{method}", "--logger", "trx;LogFileName=red.trx",
                    "--results-directory", str(directory), "-v", "minimal", env={"HOARD_DISCOVERY_MUTATION": "active"})
            except RuntimeError:
                result = directory / "red.trx"
                if not result.is_file():
                    raise RuntimeError(f"Discovery mutation did not reach its runtime assertion: {identity}.") from None
                failed = runtime_failures(result, method)
                detected.append({"id": identity, "passed": True, "failedTests": failed,
                                 "originalSha256": hashlib.sha256(source.encode()).hexdigest(),
                                 "mutantSha256": hashlib.sha256(mutant.encode()).hexdigest()})
            else:
                raise RuntimeError(f"Discovery runtime guard was not independently detected: {identity}.")
        finally:
            path.write_text(source)
    return detected


def graphs(root, work, config, packages, hosts, consumers, old_provider, registration, update):
    ownership = {
        "Hoard.Abstractions": "Abstractions", "Hoard.Core": "Core", "Hoard.Hosting": "Hosting",
        "Hoard.Application": "Application", "NuGet.Versioning": "Versioning",
        "Microsoft.Extensions.DependencyInjection.Abstractions": "Di", "Microsoft.AspNetCore.TestHost": "Sdk",
        "LegacyOptions": "Metadata", "Hoard.Fixtures.Configuration.LegacyOptions": "Metadata",
        "LifecycleHost.Discovery": "Host", "LifecycleHost.Discovery.Custom": "Host",
        "RetainedLifecycle": "Host", "RetainedConfiguration": "Host", "ApplicationConsumer": "Host",
        "NonWebConsumer": "Host", "RegistrationConsumer": "Host",
        "PermittedApplication": "Host", "ForbiddenProvider": "Metadata", "CrossSlice": "Application"
    }
    for package in packages:
        ownership[package["id"]] = package["id"].removeprefix("Hoard.Fixtures.Lifecycle.").split(".")[0]
    inputs = [("platform", [root / f"src/Hoard.{name}/Hoard.{name}.csproj"
                             for name in ("Abstractions", "Core", "Hosting", "Application")])]
    inputs += [(package["id"].removeprefix("Hoard.Fixtures.Lifecycle."), [Path(package["project"])]) for package in packages]
    inputs += list(zip(("baseline", "custom"), ([host] for host in hosts)))
    inputs += [("old-provider", [old_provider]), ("lifecycle-consumer", [consumers["RetainedLifecycle"]]),
               ("configuration-consumer", [consumers["RetainedConfiguration"]]), ("registration", [registration]),
               ("application-consumer", [consumers["ApplicationConsumer"]]), ("nonweb-consumer", [consumers["NonWebConsumer"]])]
    architecture = root / "tests/fixtures/architecture"
    target = work / "discovery-architecture"
    foundation.copy_source(architecture, target)
    for name, scan in (("PermittedApplication", "permitted-application"),
                       ("ForbiddenProvider", "forbidden-provider"), ("CrossSlice", "cross-slice")):
        project = target / f"Discovery/{name}/{name}.csproj"
        foundation.restore(project, config, update, architecture / f"Discovery/{name}")
        foundation.build(project)
        inputs.append((scan, [project]))
    result = []
    for scan, projects in inputs:
        graph = foundation.inspection_graph(projects, ownership)
        graph["scanId"] = scan
        result.append(graph)
    return result


def reference_consumer(root, work, bodies):
    """Run the unchanged BCL-only consumer against an actual serialized host response."""
    reference = root / "tests/fixtures/discovery/ReferenceConsumer/ReferenceConsumer.csproj"
    project = ET.parse(reference)
    if project.findall(".//PackageReference") or project.findall(".//ProjectReference"):
        raise RuntimeError("Reference consumer is not JSON-only/BCL-only.")
    run("dotnet", "restore", str(reference), "--locked-mode", "-v", "quiet")
    run("dotnet", "build", str(reference), "-c", "Release", "--no-restore", "-v", "quiet")
    body = work / "observation.json"
    body.write_bytes(base64.b64decode(bodies[0], validate=True))
    runtime = reference.parent / "bin/Release/net10.0"
    assembly = runtime / "ReferenceConsumer.dll"
    output = json.loads(run("dotnet", str(assembly), input=body.read_text()))
    if not isinstance(output, list) or not output:
        raise RuntimeError("Missing standalone JSON consumer output.")
    return {
        "source": str(reference.parent), "assembly": str(assembly),
        "assemblySha256": hashlib.sha256(assembly.read_bytes()).hexdigest(),
        "assets": str(reference.parent / "obj/project.assets.json"),
        "runtimeConfig": str(runtime / "ReferenceConsumer.runtimeconfig.json"),
        "dependencies": str(runtime / "ReferenceConsumer.deps.json"),
        "response": str(body), "responseSha256": hashlib.sha256(body.read_bytes()).hexdigest(),
        "moduleIds": [module["Id"] for module in output],
    }


def complete(root, work, update, retained_directory):
    inputs = input_hashes(root)
    run_id = str(uuid.uuid4())
    os.environ["HOARD_DISCOVERY_RUN_ID"] = run_id
    retained = prepare_baseline(root, work, update)
    if retained_directory is not None:
        verify_retained_inputs(retained, retained_directory)
    config, packages = lifecycle.prepare_packages(root, work, update)
    legacy = next(entry for entry in retained if entry["name"] == "LegacyOptions")
    old_provider = Path(legacy["assembly"]).parents[3] / "LegacyOptions.csproj"
    run("dotnet", "pack", str(old_provider), "-c", "Release", "--no-build", "--no-restore",
        "-o", str(work / "feed"), "-v", "quiet")
    foundation.canonicalize_acceptance_archive(work / "feed/Hoard.Fixtures.Configuration.LegacyOptions.0.1.0.nupkg")
    consumers = compatibility(root, work, config, retained, update)
    hosts, journeys, observations, bodies = package_journeys(root, work, config, retained, update)
    registration = lifecycle.registration_compatibility(root, work, config, update, "registration-baseline")
    actual_graphs = graphs(root, work, config, packages, hosts, consumers, old_provider, registration, update)
    evidence = {"runId": run_id, "inputHashes": inputs, "graphs": actual_graphs, "journeys": journeys,
                "observations": observations, "responseBodies": bodies, "oldBinaries": retained, "packages": packages}
    manifest = work / "discovery-evidence.json"
    manifest.write_text(json.dumps(evidence, indent=2))
    os.environ["HOARD_DISCOVERY_EVIDENCE"] = str(manifest)
    os.environ["HOARD_DISCOVERY_OUTPUT"] = str(work)
    os.environ["HOARD_DISCOVERY_SDK"] = run("dotnet", "--version").strip()
    os.environ.pop("NUGET_PACKAGES", None)
    project = root / "tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj"
    run("dotnet", "test", str(project), "-c", "Release", "--no-build", "--no-restore", "--filter",
        "FullyQualifiedName~Discovery", "--logger", "trx;LogFileName=discovery.trx",
        "--results-directory", str(work / "results"), "-v", "minimal")
    architecture = root / "tests/architecture/Hoard.Architecture.Tests/Hoard.Architecture.Tests.csproj"
    run("dotnet", "test", str(architecture), "-c", "Release", "--no-build", "--no-restore",
        "--filter", "FullyQualifiedName~DiscoveryBoundaryTests", "--logger", "trx;LogFileName=discovery-architecture.trx",
        "--results-directory", str(work / "results"), "-v", "minimal")
    names = results(work / "results/discovery.trx") + results(work / "results/discovery-architecture.trx")
    evidence["expectedTestNames"] = listed_scenarios(project, "FullyQualifiedName~Discovery") + listed_scenarios(
        architecture, "FullyQualifiedName~DiscoveryBoundaryTests")
    verify_scenarios(names, evidence["expectedTestNames"])
    evidence["testNames"] = names
    evidence["cases"], evidence["suites"] = inventory(names)
    evidence["performance"] = json.loads((work / "performance.json").read_text())
    p95 = verify_performance(evidence["performance"], run_id)
    evidence["referenceConsumer"] = reference_consumer(root, work, bodies)
    evidence["referenceConsumerPassed"] = True
    for value in retained:
        verify_binary(Path(value["assembly"]), value["sha256"])
    for value in packages:
        verify_package(Path(value["package"]), work / "feed", value["sha512"])
    for project in [root / "Hoard.slnx", *hosts, *consumers.values(),
                    *(Path(package["project"]) for package in packages)]:
        run("dotnet", "format", str(project), "--verify-no-changes", "--no-restore", "-v", "quiet")
    run("python3", "-m", "unittest", "discover", "-s", str(root / "tests/tooling"), "-v")
    evidence["toolingPassed"] = True
    evidence["feedPackages"] = [{"id": package.name, "package": str(package),
                                "sha512": hashlib.sha512(package.read_bytes()).hexdigest()}
                               for package in sorted((work / "feed").glob("*.nupkg"))]
    evidence["mutations"] = mutations(root, work)
    verify_full_evidence(evidence, root, work)
    manifest.write_text(json.dumps(evidence, indent=2))
    print(f"Discovery acceptance: {len(names)} tests, D01..D40, {len(journeys)} package journeys, "
          f"{len(actual_graphs)} actual graph scans, retained binaries and JSON consumer passed; local fixture p95 {p95:.3f}s.")


def prepare_baseline(root, work, update):
    run("git", "merge-base", "--is-ancestor", BASELINE, "origin/main", cwd=root)
    linked = "tests/fixtures/configuration/LifecycleConsumer/Program.cs"
    if run("git", "rev-parse", f"{BASELINE}:{linked}", cwd=root).strip() != run(
            "git", "hash-object", str(root / linked), cwd=root).strip():
        raise RuntimeError("Retained linked lifecycle source differs from the merged baseline.")
    baseline = work / "baseline"
    baseline.mkdir()
    archive = work / "baseline.tar"
    run("git", "archive", "--format=tar", f"--output={archive}", BASELINE,
        "Directory.Build.props", "Directory.Packages.props", "global.json", "src", cwd=root)
    with tarfile.open(archive) as contents:
        contents.extractall(baseline, filter="data")
    feed = work / "baseline-feed"
    feed.mkdir()
    config = work / "Baseline.NuGet.Config"
    config.write_text(
        '<configuration><packageSources><clear/>'
        f'<add key="local" value="{escape(str(feed))}"/>'
        '<add key="nuget.org" value="https://api.nuget.org/v3/index.json"/>'
        '</packageSources><packageSourceMapping><packageSource key="local">'
        '<package pattern="Hoard.*"/></packageSource><packageSource key="nuget.org">'
        '<package pattern="*"/></packageSource></packageSourceMapping></configuration>')
    cache = work / "baseline-cache"
    for name in ("Abstractions", "Core", "Hosting"):
        project = baseline / f"src/Hoard.{name}/Hoard.{name}.csproj"
        run("dotnet", "restore", str(project), "--locked-mode", "--configfile", str(config),
            "--packages", str(cache), "-v", "quiet")
        run("dotnet", "pack", str(project), "-c", "Release", "--no-restore",
            "-o", str(feed), "-v", "quiet")
        foundation.canonicalize_acceptance_archive(feed / f"Hoard.{name}.0.1.0.nupkg")
    retained = []
    foundation.copy_source(root / "tests/fixtures/configuration/LifecycleConsumer",
                           work / "retained/configuration/LifecycleConsumer")
    for name in ("RetainedLifecycle", "RetainedConfiguration", "LegacyOptions"):
        source = root / ("tests/fixtures/configuration/LegacyOptions" if name == "LegacyOptions"
                         else f"tests/fixtures/discovery/{name}")
        target = work / f"retained/discovery/{name}"
        foundation.copy_source(source, target)
        lock_source = root / f"tests/fixtures/discovery/{name}/Baseline"
        lock_source.mkdir(parents=True, exist_ok=True)
        project = target / f"{name}.csproj"
        if not update:
            lock = lock_source / "packages.lock.json"
            if not lock.is_file():
                raise RuntimeError("Missing retained pre-F-04 baseline lock.")
            shutil.copy2(lock, target / lock.name)
        run("dotnet", "restore", str(project), "--configfile", str(config),
            "--force-evaluate" if update else "--locked-mode", "--packages", str(cache), "-v", "quiet")
        if update:
            shutil.copy2(target / "packages.lock.json", lock_source / "packages.lock.json")
            run("dotnet", "restore", str(project), "--configfile", str(config), "--locked-mode",
                "--packages", str(work / "baseline-replay-cache"), "-v", "quiet")
        run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet")
        binary = target / f"bin/Release/net10.0/{name}.dll"
        if name != "LegacyOptions":
            expected = "lifecycle-compatible" if name == "RetainedLifecycle" else "configuration-compatible"
            if run("dotnet", str(binary)).strip() != expected:
                raise RuntimeError("Retained pre-F-04 consumer did not execute.")
        retained.append({"name": name, "baseline": BASELINE, "assembly": str(binary),
                         "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                         "assets": str(target / "obj/project.assets.json"),
                         "baselineAssetsSha256": hashlib.sha256((target / "obj/project.assets.json").read_bytes()).hexdigest(),
                         "baselineDependencyHashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                                      for path in binary.parent.glob("*.dll")},
                         "linkedSourceHashes": {linked: hashlib.sha256((root / linked).read_bytes()).hexdigest()}
                                               if name == "RetainedLifecycle" else {},
                         "sourceHashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                          for path in source.iterdir() if path.suffix in (".cs", ".csproj")}})
    for entry in retained:
        verify_binary(Path(entry["assembly"]), entry["sha256"])
    return retained


def main():
    global _log
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--update-locks", action="store_true")
    parser.add_argument("--phase", choices=("baseline", "all"), default="all")
    parser.add_argument("--retain-baseline", type=Path)
    parser.add_argument("--retained-baseline", type=Path)
    parser.add_argument("--evidence-directory", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.retain_baseline is not None and args.phase != "baseline":
        parser.error("--retain-baseline requires --phase baseline")
    if args.retained_baseline is not None and args.phase != "all":
        parser.error("--retained-baseline requires full acceptance")
    if any(path is not None and path.resolve().is_relative_to(root)
           for path in (args.evidence_directory, args.retain_baseline)):
        parser.error("Retained proof workspaces must be outside the repository")
    before = lock_hashes(root)
    work = create_workspace(destination=args.evidence_directory)
    _log = work / "commands.log"
    passed = False
    try:
        if args.phase == "baseline":
            retained = prepare_baseline(root, work, args.update_locks)
            if args.retain_baseline:
                saved = configuration.retain_baseline(retained, args.retain_baseline)
                for current, output in zip(retained, saved, strict=True):
                    for key in ("sourceHashes", "baselineDependencyHashes", "baselineAssetsSha256", "linkedSourceHashes"):
                        output[key] = current[key]
                (args.retain_baseline / "retained-binaries.json").write_text(json.dumps(saved, indent=2))
            print("Pre-F-04 baseline: three retained binaries compiled, executed where applicable, and hash-verified.")
        else:
            complete(root, work, args.update_locks, args.retained_baseline)
        if not args.update_locks:
            verify_locks(root, before)
        passed = True
    finally:
        if args.evidence_directory is None:
            cleanup_workspace(work)
        else:
            (work / "result.json").write_text(json.dumps({"passed": passed, "fullAcceptance": passed and args.phase == "all"}))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
    except (OSError, ValueError, ET.ParseError):
        raise SystemExit("Discovery evidence preparation failed; inspect local inputs privately.") from None
