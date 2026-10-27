"""Non-qualifying native execution of packaged composition observations."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import uuid

import conformance_baselines as baselines
import conformance_evidence as evidence
import conformance_legacy as legacy
from conformance_case_catalog import composition_snapshot_policy, composition_witnesses
from conformance_execution import OwnedRun, native_execution_supported
from conformance_lock_preparation import verify_project_lock
from conformance_prepare import PREREQUISITES, Project, build_project
from conformance_sdk_checks import BUDGETS, category_command_proof, environment, write_new
from conformance_sources import read_bounded, runtime_arguments, runtime_settings


PROJECT = "tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj"
HOST = "Hoard.Fixtures.Conformance.Host"
SDK = "Hoard.Testing.Conformance"
LOGGER = "Hoard.Conformance.TestLogger"


def expected_rows():
    return [{
        "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
        "assemblyId": "test-assembly", "packageId": SDK, "bindingId": "none",
        "matrixId": matrix + ".observe", "caseId": case, "assertionSymbol": None,
    } for case, matrix in (
        ("CP-01", "baseline"), ("CP-02", "replacement"),
        ("CP-14", "initializer-failed"),
        ("CP-15", "cancel-initialization"), ("CP-15", "cancel-readiness"),
        ("CP-16", "late-initialization"), ("CP-17", "stop-fault"), ("CP-17", "late-stop"),
        ("CP-18", "recovery-failed"),
    ) for identity in composition_witnesses(case, matrix)]


def _runtime(run, repository, source, sources, config, feed, records, replay):
    print(json.dumps({"qualification": False, "phase": "runtime-staging"}), flush=True)
    project = replay / PROJECT
    runtime = project.parent / "bin/Release/net10.0"
    legacy.stage_sdk(feed / f"{SDK}.0.1.0.nupkg", runtime / f"{SDK}.dll")
    shutil.copy2(source / f"tests/contracts/{LOGGER}/bin/Release/net10.0/{LOGGER}.dll",
                 runtime / f"{LOGGER}.dll")
    staged = run.root / "stores/composition-runtime"
    legacy._copy_runtime(runtime, staged)
    assembly = staged / "Hoard.Composition.Tests.dll"
    images = [{
        "id": "test-assembly" if path == assembly else f"component-{index}",
        "path": path.relative_to(run.root).as_posix(), "sha256": evidence.file_sha256(path),
    } for index, path in enumerate(sorted(staged.rglob("*.dll")))]
    packages = [evidence.package_identity(feed, archive.name.removesuffix(".0.1.0.nupkg"), "0.1.0")
                for archive in sorted(feed.glob("*.nupkg"))]
    for name in (HOST, SDK, LOGGER):
        package = next(row for row in packages if row["packageId"] == name)
        if evidence.file_sha256(staged / f"{name}.dll") not in package["runtimeAssemblies"].values():
            raise evidence.ConformanceError("PackageMismatch")
    print(json.dumps({"qualification": False, "phase": "runtime-environment"}), flush=True)
    observed_environment = evidence.admit_entity("Environment", {
        **environment(run), "nativeSqlite": "unobserved",
    })
    write_new(run.root / "proofs/composition-environment-admission.json",
              evidence.canonical_bytes(observed_environment))
    ci_revision = os.environ.get("GITHUB_SHA") if os.environ.get("GITHUB_ACTIONS") == "true" else None
    if os.environ.get("GITHUB_ACTIONS") == "true" and ci_revision is None:
        raise evidence.ConformanceError("InputChanged")
    group, attempt = str(uuid.uuid4()), str(uuid.uuid4())
    print(json.dumps({"qualification": False, "phase": "runtime-inputs"}), flush=True)
    inputs = evidence.admit_entity("RunInputs", {
        "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": group,
        "profileId": "composition", "mode": "diagnostic",
        "catalogRevision": evidence.CATALOG_REVISION,
        "catalogSha256": sources["tests/contracts/Hoard.Testing.Conformance/Catalog/catalog.json"],
        "sdkSha256": evidence.digest({name: hashed for name, hashed in sources.items()
                                     if name.startswith("tests/contracts/Hoard.Testing.Conformance/")}),
        **evidence.source_identity(repository, ci_revision=ci_revision),
        "sourceManifest": sources, "sourceManifestSha256": evidence.digest(sources),
        "packages": packages, "locks": {
            **{path.relative_to(run.root).as_posix(): evidence.file_sha256(path)
               for root in (source, replay) for path in root.rglob("packages.lock.json")},
            **{(source / record["preparedLock"]).relative_to(run.root).as_posix(): record["preparedSha256"]
               for record in records}},
        "runtimeAssemblies": {row["path"]: row["sha256"] for row in images},
        "bindings": [], "baselines": [], "configurationSha256": evidence.file_sha256(config),
        "capabilitySha256": evidence.digest({}), "environment": observed_environment,
        "environmentSha256": evidence.digest(observed_environment), "budgets": BUDGETS,
        "invocation": ["component", "composition", "native-snapshot-transport"],
    })
    inputs_path = run.root / "proofs/composition-inputs.json"
    write_new(inputs_path, evidence.canonical_bytes(inputs))
    owner = {
        "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": group,
        "rootId": run.root_id, "rootPathSha256": hashlib.sha256(str(run.root).encode()).hexdigest(),
    }
    write_new(run.root / "runtime-owner.json", evidence.canonical_bytes(owner))
    expected = expected_rows()
    manifest = {
        "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": group, "attemptId": attempt,
        "attemptSequence": 1, "purpose": "execution", "inputSha256": evidence.digest(inputs),
        "runInputsPath": inputs_path.relative_to(run.root).as_posix(), "assemblies": images,
        "packages": [{"id": row["packageId"],
                      "path": (feed / f'{row["packageId"]}.0.1.0.nupkg').relative_to(run.root).as_posix(),
                      "sha256": row["sha256"]} for row in packages],
        "expected": expected,
    }
    manifest_path = run.root / f"runtime-input-{attempt}.json"
    write_new(manifest_path, evidence.canonical_bytes(manifest))
    context = base64.b64encode(evidence.canonical_bytes({
        "schemaVersion": 1, "runId": run.run_id,
        "cases": {row["testIdentity"]: {"bindingId": "none", "caseId": row["caseId"]} for row in expected},
    })).decode("ascii")
    settings_data = runtime_settings(
        run.root, assembly, attempt, evidence.digest(manifest), evidence.digest(owner),
        "<EnvironmentVariables><HOARD_ORIGINAL_CONTEXT>" + context
        + "</HOARD_ORIGINAL_CONTEXT></EnvironmentVariables>")
    settings_path = run.root / f"proofs/settings-{attempt}.runsettings"
    write_new(settings_path, settings_data)
    bound_paths = (
        manifest_path, inputs_path, run.root / "runtime-owner.json", settings_path,
        run.root / "proofs/environment-admission.json", run.root / "proofs/composition-environment-admission.json",
        config, assembly, staged / f"{HOST}.dll", staged / f"{SDK}.dll", staged / f"{LOGGER}.dll",
        staged / "Hoard.Composition.Tests.deps.json", staged / "Hoard.Composition.Tests.runtimeconfig.json",
    )
    for path in bound_paths:
        path.chmod(0o400)
    for image in images:
        (run.root / image["path"]).chmod(0o400)
    command_inputs = {path.relative_to(run.root).as_posix(): evidence.file_sha256(path)
                      for path in bound_paths}
    arguments = runtime_arguments(assembly, settings_path, [row["testIdentity"] for row in expected])
    print(json.dumps({"qualification": False, "phase": "runtime-command"}), flush=True)
    started = time.monotonic() * 1000
    result = run.command(
        arguments, cwd=staged, kind="tests", cache_id="composition-runtime", timeout=180,
        record_execution=True, execution_inputs=tuple(command_inputs))
    ended = time.monotonic() * 1000
    parent_sha = category_command_proof(
        run, result, arguments=arguments, cwd=staged, manifest=manifest,
        settings_data=settings_data, started_ms=started, ended_ms=ended)
    record = evidence.load_json(run.read_execution_record(run.command_sequence))
    if parent_sha is None or record.get("inputFiles") != command_inputs:
        raise evidence.ConformanceError("ProofMismatch")
    output = run.root / f"runtime-{attempt}"
    print(json.dumps({"qualification": False, "phase": "runtime-ingestion"}), flush=True)
    admitted = evidence.ingest_runtime_attempt(
        inputs=inputs, manifest_data=evidence.canonical_bytes(manifest), owner_data=evidence.canonical_bytes(owner),
        witnesses_data=read_bounded(output / "witnesses.jsonl", 1024 * 1024),
        completion_data=read_bounded(output / "completion.json", 64 * 1024),
        proofs={path.name: read_bounded(path, 64 * 1024) for path in output.glob("proof-*.json")},
        expected_tests={row["testIdentity"]: ("none", row["matrixId"]) for row in expected},
        manifest_sha256=evidence.digest(manifest), owner_sha256=evidence.digest(owner),
        started_ms=started, ended_ms=ended,
        original_inputs={"none": {row["testIdentity"]: {
            "owner": ((staged / f"{HOST}.dll").relative_to(run.root).as_posix(), HOST)}
            for row in expected}},
    )
    if result.exit_code or admitted["diagnosticCode"] != "None":
        raise evidence.ConformanceError("ProofMismatch")
    if (len(admitted["witnesses"]) != len(expected)
            or any(row["status"] != "Passed" for row in admitted["witnesses"])
            or len(admitted["compositionObservations"]) != len(expected)
            or any(len(admitted["compositionObservations"][row["executionId"]])
                   != len(composition_snapshot_policy(row["testIdentity"]))
                   for row in admitted["witnesses"])):
        raise evidence.ConformanceError("WitnessMissing")
    print(json.dumps({"qualification": False, "phase": "completion-inputs"}), flush=True)
    if (dict(evidence.source_manifest(repository)) != dict(sources)
            or any(evidence.file_sha256(run.root / path) != hashed
                   for path, hashed in {**inputs["runtimeAssemblies"], **inputs["locks"], **command_inputs}.items())):
        raise evidence.ConformanceError("InputChanged")
    return {
        "schemaVersion": 1, "qualification": False, "nativeContainment": True, "profileComplete": False,
        "safeRuntimeAdmission": True, "runId": run.run_id, "attemptId": attempt,
        "sourceSha256": evidence.digest(sources), "consumerSha256": evidence.file_sha256(assembly),
        "inputSha256": evidence.digest(inputs), "manifestSha256": evidence.digest(manifest),
        "commandParentSha256": parent_sha, "runtimeProofs": dict(admitted["proofs"]),
        "passedComponents": len(expected),
        "admittedSnapshots": sum(map(len, admitted["compositionObservations"].values())),
        "lockDerivationsSha256": evidence.digest(records),
        "lockedFreshCacheReplay": True, "moduleOwnershipQualification": False,
        "environment": evidence.load_json(evidence.canonical_bytes(observed_environment)),
    }


def execute(repository, destination):
    if not native_execution_supported():
        raise evidence.ConformanceError("PrerequisiteMissing")
    run = OwnedRun.allocate(destination, repository, profile="composition")
    try:
        (run.root / "cache/.local/share").mkdir(parents=True, mode=0o700)
        (run.root / "cache/.local").chmod(0o700)
        source, sources = evidence.snapshot_sources(repository, run)
        config, feed = baselines._config(run, "candidate")
        projects = (
            *PREREQUISITES,
            Project(f"tests/contracts/{SDK}/{SDK}.csproj", SDK),
            Project(f"tests/contracts/{LOGGER}/{LOGGER}.csproj", LOGGER),
            *(Project(f"tests/fixtures/conformance/Bindings/{name}/{name}.csproj",
                      f"Hoard.Fixtures.Conformance.Bindings.{name}")
              for name in ("Sqlite", "Memory", "Local", "ObjectSemantics")),
            Project("tests/fixtures/conformance/Host/Host.csproj", HOST),
        )
        records = []
        for project in projects:
            print(json.dumps({"qualification": False, "phase": "package", "id": project.package}), flush=True)
            record = build_project(run, source, project, config, feed, update=False, historical_lock=True)
            if record is not None:
                records.append(record)
        print(json.dumps({"qualification": False, "phase": "consumer-build"}), flush=True)
        build_project(run, source, Project(PROJECT, package_mode=True), config, feed, update=True)
        consumer_lock = Path(PROJECT).parent / "PackageAcceptance/packages.lock.json"
        prepared_sources = {**sources, consumer_lock.as_posix(): evidence.file_sha256(source / consumer_lock)}
        print(json.dumps({"qualification": False, "phase": "source-recomputation"}), flush=True)
        evidence.verify_snapshot(source, prepared_sources)
        replay = run.root / "stores/composition-locked-replay"
        for relative in prepared_sources:
            target = replay / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copy2(source / relative, target)
        properties = ["-p:UseSharedCompilation=false", "-nodeReuse:false", "-v", "quiet",
                      "-p:ConformancePackageAcceptance=true"]
        print(json.dumps({"qualification": False, "phase": "locked-replay"}), flush=True)
        for arguments in (
            ["dotnet", "restore", str(replay / PROJECT), "--locked-mode", "--configfile", str(config)],
            ["dotnet", "build", str(replay / PROJECT), "-c", "Release", "--no-restore"],
        ):
            baselines._command(run, [*arguments, *properties], cwd=replay, cache_id="composition-fresh-replay")
        evidence.verify_snapshot(replay, prepared_sources)
        write_new(run.root / "proofs/composition-lock-derivations.json", evidence.canonical_bytes(records))
        summary = _runtime(run, repository, source, sources, config, feed, records, replay)
        evidence.verify_snapshot(source, prepared_sources)
        evidence.verify_snapshot(replay, prepared_sources)
        for record in records:
            verify_project_lock(record, source, feed)
        print(json.dumps({"qualification": False, "phase": "process-release"}), flush=True)
        run.transition("Settling")
        run.release()
        resources = run.resource_projection()
        if not resources or any(row["state"] != "Released" for row in resources):
            raise evidence.ConformanceError("CleanupIncomplete")
        summary["processResourcesReleased"] = True
        write_new(run.root / "proofs/composition-diagnostic-summary.json", evidence.canonical_bytes(summary))
        print(json.dumps(summary, sort_keys=True), flush=True)
        return 0
    finally:
        if run.state in ("Active", "Allocated"):
            run.transition("Settling")
        if run.state == "Settling":
            if run.live_children():
                run.transition("Retained")
                raise evidence.ConformanceError("CleanupIncomplete")
            run.release()


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args(arguments)
    try:
        return execute(args.root, args.evidence)
    except (evidence.ConformanceError, OSError, ValueError) as error:
        code = str(error) if isinstance(error, evidence.ConformanceError) else "EvidenceIncomplete"
        print(json.dumps({"qualification": False, "status": "Incomplete", "code": code}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
