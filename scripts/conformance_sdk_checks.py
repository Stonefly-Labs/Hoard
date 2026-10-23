"""Bounded Linux SDK/logger diagnostics, never provider qualification.

Historical preparation is sealed and verified before any candidate compilation.
Only closed diagnostic codes, counts and hashes may reach the CI console.
Copied smoke-lock preparation rebinds only current local archive hashes; an
independent fresh cache then replays that unchanged graph in locked mode.
"""

import argparse
import hashlib
import json
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


def build(run, project, config, cache_id, *, feed=None, lock=None):
    common = ["-p:UseSharedCompilation=false", "-nodeReuse:false", "-v", "quiet"]
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
        canonicalize_acceptance_archive(feed / f"{project.stem}.0.1.0.nupkg")


def prepare_smoke_lock(project, candidate, feed):
    _, packages, _ = rebind_local_archives(
        read_bounded(project.parent / "packages.lock.json", 2 * 1024 * 1024), feed)
    if set(packages) != {f"{name}.0.1.0.nupkg" for name in
                         ("Hoard.Abstractions", "Hoard.Testing.Conformance", "Hoard.Conformance.TestLogger")}:
        raise evidence.ConformanceError("InputChanged")
    return prepare_project_lock(project, candidate, feed, "candidate")


def environment(run, *, phase="admission"):
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
    return evidence.load_json(read_bounded(path, 64 * 1024))


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
                *, group_id=None, ci_revision=None):
    run._check_ledger()
    inventory = evidence.proof_manifest(candidate)
    prefix = candidate.relative_to(run.root).as_posix()
    locks = [f"{prefix}/{name}" for name in inventory if name.endswith("packages.lock.json")]
    runtime_folders = {f"{TESTS}/bin/Release/net10.0", f"{LOGGER}/Smoke/bin/Release/net10.0"}
    runtime = [f"{prefix}/{name}" for name in inventory
               if name.endswith((".dll", ".deps.json", ".runtimeconfig.json", ".runtimeconfig.dev.json"))
               and Path(name).parent.as_posix() in runtime_folders]
    if not runtime or not locks:
        raise evidence.ConformanceError("EvidenceIncomplete")
    inputs = evidence.capture_profile_inputs(
        run, repository, candidate, profile_id="harness", mode="diagnostic",
        invocation_group_id=str(uuid.uuid4()) if group_id is None else group_id,
        package_versions=[{"packageId": name, "version": "0.1.0"} for name in
                          ("Hoard.Abstractions", "Hoard.Testing.Conformance", "Hoard.Conformance.TestLogger")],
        feed="feed/candidate", configuration="stores/candidate.NuGet.Config",
        lock_paths=locks, runtime_paths=runtime, binding_sources=[],
        observed_environment=observed_environment, budgets=BUDGETS, invocation=["sdk-logger-diagnostic"],
        baseline_sha256=seal_sha, ci_revision=ci_revision)
    if (inputs["sourceManifest"] != sources
            or any(inputs[key] != value for key, value in identity.items())):
        raise evidence.ConformanceError("InputChanged")
    return inputs


def test_attempt(run, inputs, candidate, scenario):
    name, identities, expected_code, expected_status, expected_exit, failure_kind = scenario
    source_tests = name in ("owned", "ranges", "catalog", "declarations", "enums", "loaded")
    assembly = candidate / (TESTS if source_tests else LOGGER + "/Smoke") / "bin/Release/net10.0" / (
        "Hoard.Conformance.Tests.dll" if source_tests else "Smoke.dll")
    assembly_path = assembly.relative_to(run.root).as_posix()
    package_id = "Hoard.Testing.Conformance" if source_tests else "Hoard.Conformance.TestLogger"
    package = next(package for package in inputs["packages"] if package["packageId"] == package_id)
    attempt_id = str(uuid.uuid4())
    expected = {identity: ("none", "none") for identity in identities}
    manifest = {
        "schemaVersion": 1, "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "attemptId": attempt_id, "attemptSequence": 1, "inputSha256": evidence.digest(inputs),
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
        } for identity, (binding, matrix) in expected.items()],
    }
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
        ["dotnet", "vstest", str(assembly), f"--Settings:{settings}",
         f"--TestCaseFilter:{filter_text}"],
        cwd=assembly.parent, timeout=180, kind="tests", cache_id="runtime")
    ended = time.monotonic() * 1000
    output = run.root / f"runtime-{attempt_id}"
    no_symlinks(output)
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
    ingested = evidence.ingest_runtime_attempt(
        inputs=inputs, manifest_data=manifest_data, owner_data=owner_data,
        witnesses_data=read_bounded(output / "witnesses.jsonl", 1024 * 1024), proofs=proof_data,
        completion_data=read_bounded(output / "completion.json", 64 * 1024), expected_tests=expected,
        manifest_sha256=manifest_sha, owner_sha256=owner_sha, started_ms=started, ended_ms=ended)
    validate_observation(ingested, result, identities, expected_code, expected_status, expected_exit,
                         proof_data, failure_kind)
    return {"code": expected_code, "tests": len(identities),
            "completionSha256": evidence.file_sha256(output / "completion.json")}


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
        inputs = make_inputs(run, repository, candidate, sources, environment(run), identity, seal_sha,
                             ci_revision=ci_revision)
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
        post_environment = environment(run, phase="completion")
        post_sources = evidence.source_manifest(repository)
        post_identity = evidence.source_identity(repository, ci_revision=ci_revision)
        if post_sources != sources or post_identity != identity:
            raise evidence.ConformanceError("InputChanged")
        evidence.verify_snapshot(candidate, sources)
        if lock_record is not None:
            verify_project_lock(lock_record, candidate, feed)
        post_inputs = make_inputs(
            run, repository, candidate, post_sources, post_environment, post_identity, seal_sha,
            group_id=inputs["invocationGroupId"], ci_revision=ci_revision)
        evidence.verify_input_recomputation(inputs, post_inputs)
        summary = {"qualification": False, "code": "None", "baselines": 6,
                   "baselineSha256": seal_sha, "inputsSha256": evidence.digest(inputs),
                   "lockPreparation": lock_preparation,
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
