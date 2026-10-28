"""Non-qualifying native execution of packaged composition observations."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import conformance_baselines as baselines
import conformance_evidence as evidence
import conformance_legacy as legacy
from conformance_case_catalog import composition_execution_cases, composition_snapshot_policy, expected_cases
from conformance_execution import OwnedRun, capture_control, native_execution_supported
from conformance_inherited import (
    INVENTORY_PATH, _controller_incomplete, admit_discovery, controller_phase as _controller_phase,
    controller_read_inputs, execution_scopes, inventory,
    verify_controller_baselines,
)
from conformance_lock_preparation import prepare_project_lock, verify_project_lock
from conformance_prepare import PREREQUISITES, Project, build_project
from conformance_sdk_checks import (
    BUDGETS, category_command_proof, environment, verify_category_command_proof, write_new,
)
from conformance_sources import read_bounded, runtime_arguments, runtime_settings


PROJECT = "tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj"
ARCHITECTURE_PROJECT = "tests/architecture/Hoard.Architecture.Tests/Hoard.Architecture.Tests.csproj"
HOST = "Hoard.Fixtures.Conformance.Host"
SDK = "Hoard.Testing.Conformance"
LOGGER = "Hoard.Conformance.TestLogger"
DISCOVERY_PROJECT = "tests/fixtures/conformance/Discovery/Discovery.csproj"


def _native_reference_consumer(run, repository, source, controllers, baseline_seal):
    preparation = controllers["phases"]["discovery"]
    manifest = run.root / evidence.relative_path(preparation["manifestPath"])
    raw = read_bounded(manifest, 16 * 1024**2)
    if hashlib.sha256(raw).hexdigest() != preparation["manifestSha256"]:
        raise evidence.ConformanceError("InputChanged")
    reference = evidence.load_json(raw)["referenceConsumer"]
    source_directory = Path(reference["source"])
    legacy.no_symlinks(source_directory)
    if (not source_directory.is_absolute() or source_directory == run.root
            or not source_directory.is_relative_to(run.root)
            or not source_directory.resolve(strict=True).is_relative_to(run.root)):
        raise evidence.ConformanceError("OwnershipInvalid")
    project = source_directory / "ReferenceConsumer.csproj"
    code = [path for path in source_directory.rglob("*.cs")
            if not {"bin", "obj"}.intersection(path.relative_to(source_directory).parts)]
    files = controller_read_inputs(run.root, {}, extra=(
        manifest, project, *code, *(Path(reference[key]) for key in
                                  ("assembly", "assets", "runtimeConfig", "dependencies", "response"))))
    closure = run.root / "proofs/inherited-reference-inputs.json"
    write_new(closure, evidence.canonical_bytes(files))
    for relative in files:
        (run.root / relative).chmod(0o400)
    descriptor = {
        "manifestPath": preparation["manifestPath"], "manifestSha256": preparation["manifestSha256"],
        "inputMapPath": closure.relative_to(run.root).as_posix(), "inputMapSha256": evidence.digest(files)}
    if dict(evidence.input_manifest(run.root, list(files))) != files:
        raise evidence.ConformanceError("InputChanged")
    observed, parent, invocations = _controller_phase(
        run, repository, source, "reference", baseline_seal=baseline_seal, reference=descriptor)
    expected = {
        "qualification": False, "moduleCount": len(reference["moduleIds"]),
        "moduleIdsSha256": evidence.digest(reference["moduleIds"]), "inputMapSha256": evidence.digest(files),
        "argvSha256": evidence.digest(["dotnet", reference["assembly"]]),
        "cwdSha256": hashlib.sha256(str(source).encode("utf-8")).hexdigest(),
        "assemblySha256": reference["assemblySha256"], "responseSha256": reference["responseSha256"]}
    invocation = observed.get("invocation")
    record = evidence.load_json(run.read_execution_record(run.command_sequence))
    legacy.verify_borrowed_invocation(
        invocation, argv_sha256=expected["argvSha256"], cwd_sha256=expected["cwdSha256"],
        stdin_sha256=expected["responseSha256"], group_pid=record["childPid"],
        group_start_sha256=record["childStartSha256"])
    if (observed != {**expected, "invocation": invocation}
            or dict(evidence.input_manifest(run.root, list(files))) != files):
        raise evidence.ConformanceError("ProofMismatch")
    return {**observed, "nativeContainment": True, "parentSha256": parent,
            "sequence": run.command_sequence, "inputCount": len(files), "nativeInvocations": invocations}


def _prepare_solution_formatting(run, source, config, feed):
    try:
        solution = ET.fromstring(read_bounded(source / "Hoard.slnx", 65536))
    except ET.ParseError:
        raise evidence.ConformanceError("EvidenceSchemaInvalid") from None
    projects = [evidence.relative_path(node.get("Path")) for node in solution.findall(".//Project")]
    if solution.tag != "Solution" or not 1 <= len(projects) <= 128 or len(set(projects)) != len(projects):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    records = []
    for ordinal, relative in enumerate(projects, 1):
        project = source / relative
        legacy.no_symlinks(project)
        if project.suffix != ".csproj" or not project.is_file():
            raise evidence.ConformanceError("InputChanged")
        assets = project.parent / "obj/project.assets.json"
        legacy.no_symlinks(assets)
        if assets.is_file():
            continue
        print(json.dumps({"qualification": False, "phase": "inherited-solution-assets",
                          "project": ordinal}), flush=True)
        alternate, record = prepare_project_lock(project, source, feed, "candidate")
        properties = ["-p:UseSharedCompilation=false", "-nodeReuse:false", "-v", "quiet"]
        if alternate is not None:
            properties.append("-p:NuGetLockFilePath=" + str(alternate))
        baselines._command(
            run, ["dotnet", "restore", str(project), "--locked-mode", "--configfile", str(config), *properties],
            cwd=source, cache_id="inherited-discovery")
        if not assets.is_file():
            raise evidence.ConformanceError("EvidenceIncomplete")
        if record is not None:
            verify_project_lock(record, source, feed)
            records.append(record)
    write_new(run.root / "proofs/inherited-solution-lock-derivations.json", evidence.canonical_bytes(records))


def _format_prepared_controllers(run, controllers, files, closure_path, *, solution=None):
    descriptor = controllers["formatting"]
    path = run.root / evidence.relative_path(descriptor["path"])
    raw = read_bounded(path, 1024**2)
    if hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
        raise evidence.ConformanceError("InputChanged")
    projects = evidence.load_json(raw)
    phases = ("foundation", "lifecycle", "configuration", "discovery")
    if (not isinstance(projects, dict) or set(projects) != set(phases)
            or any(not isinstance(projects[phase], list) or not 1 <= len(projects[phase]) <= 200
                   for phase in phases)):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    selected = []
    for phase in phases:
        seen = set()
        for relative in projects[phase]:
            project = run.root / evidence.relative_path(relative)
            legacy.no_symlinks(project)
            assets = project.parent / "obj/project.assets.json"
            if (not project.is_relative_to(run.root / "stores" / ("inherited-controller-" + phase))
                    or project.suffix != ".csproj" or relative in seen
                    or relative not in files or assets.relative_to(run.root).as_posix() not in files):
                raise evidence.ConformanceError("ProofMismatch")
            seen.add(relative)
            selected.append((phase, project, assets))
    if solution is not None:
        legacy.no_symlinks(solution)
        if (not solution.is_absolute() or not solution.is_relative_to(run.root)
                or solution.name != "Hoard.slnx" or solution.relative_to(run.root).as_posix() not in files):
            raise evidence.ConformanceError("ProofMismatch")
        selected.append(("solution", solution, None))
    frozen = {**files, path.relative_to(run.root).as_posix(): descriptor["sha256"],
              closure_path.relative_to(run.root).as_posix(): evidence.digest(files)}
    if read_bounded(closure_path, 2 * 1024**2) != evidence.canonical_bytes(files):
        raise evidence.ConformanceError("InputChanged")

    def verify_inputs():
        if dict(evidence.input_manifest(run.root, list(frozen))) != frozen:
            raise evidence.ConformanceError("InputChanged")

    verify_inputs()
    for name in frozen:
        (run.root / name).chmod(0o400)
    commands = []
    for phase, project, assets in selected:
        verify_inputs()
        print(json.dumps({"qualification": False, "phase": "inherited-prepared-formatting",
                          "controller": phase, "command": len(commands) + 1}), flush=True)
        bound = dict(evidence.input_manifest(run.root, [
            item.relative_to(run.root).as_posix()
            for item in (path, closure_path, project, *((assets,) if assets is not None else ()))]))
        arguments = ["dotnet", "format", str(project), "--verify-no-changes", "--no-restore", "-v", "quiet"]
        sequence = run.command_sequence + 1
        started = time.monotonic() * 1000
        result = run.command(
            arguments, cwd=project.parent, kind="build", cache_id="inherited-format", timeout=180,
            record_execution=True, execution_inputs=tuple(bound))
        ended = time.monotonic() * 1000
        verify_inputs()
        if result.exit_code or any(event["code"] != "None" for event in result.events):
            raise evidence.ConformanceError("CommandFailed")
        record_raw = run.read_execution_record(run.command_sequence)
        record = evidence.load_json(record_raw)
        if (result.execution_record_sha256 != hashlib.sha256(record_raw).hexdigest()
                or run.command_sequence != sequence or record["sequence"] != sequence
                or record["runId"] != run.run_id or record["rootId"] != run.root_id
                or record["scope"] != "ordinary" or record["groupState"] != "Exited"
                or record["exitCode"] != 0 or record["diagnosticCode"] != "None"
                or record["argvSha256"] != evidence.digest(arguments)
                or record["cwdSha256"] != hashlib.sha256(str(project.parent).encode("utf-8")).hexdigest()
                or record.get("inputFiles") != bound
                or not started <= record["startedMs"] <= record["endedMs"] <= ended
                or run.live_children()):
            raise evidence.ConformanceError("ProofMismatch")
        commands.append({"controller": phase, "projectSha256": files[project.relative_to(run.root).as_posix()],
                         "parentSha256": result.execution_record_sha256})
    return {"qualification": False, "solutionFormatting": solution is not None, "commands": commands}


def expected_rows():
    rows = [{
        "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
        "assemblyId": "test-assembly", "packageId": SDK, "bindingId": "none",
        "matrixId": matrix, "caseId": case, "assertionSymbol": None,
    } for identity, (case, matrix) in composition_execution_cases().items()]
    return rows


def _inherited_discovery(run, source, sources, feed, observed_environment, *, assembly_name, runtime, driver):
    methods = inventory(read_bounded(source / INVENTORY_PATH, 2 * 1024 * 1024), sources)
    for name in ("Hoard.Abstractions", "Hoard.Core", "Hoard.Hosting", "Hoard.Application"):
        package = evidence.package_identity(feed, name, "0.1.0")
        image = runtime / f"{name}.dll"
        if image.is_file() and evidence.file_sha256(image) not in package["runtimeAssemblies"].values():
            raise evidence.ConformanceError("PackageMismatch")
    code, installed = capture_control(["dotnet", "--list-sdks"], limit=16384, timeout=5)
    if code:
        raise evidence.ConformanceError("PrerequisiteMissing")
    sdks = re.findall(r"^" + re.escape(observed_environment["sdk"]) + r" \[([^\r\n]+)\]$",
                      installed.decode("utf-8", errors="strict"), re.MULTILINE)
    if len(sdks) != 1:
        raise evidence.ConformanceError("PrerequisiteMissing")
    vstest = Path(sdks[0]) / observed_environment["sdk"] / "vstest.console.dll"
    if not vstest.is_file():
        raise evidence.ConformanceError("PrerequisiteMissing")
    selected = sorted(name for name in methods if name.startswith(assembly_name + "."))
    prefix = "proofs/inherited-" + assembly_name
    methods_path = run.root / (prefix + "-methods.json")
    output_path = run.root / (prefix + "-cases.json")
    write_new(methods_path, evidence.canonical_bytes(selected))
    images = []
    for folder in (runtime, driver):
        images.extend(path for path in folder.rglob("*") if path.is_file()
                      and (path.suffix in (".dll", ".so", ".dylib")
                           or path.name.endswith((".deps.json", ".runtimeconfig.json"))))
    request_path = run.root / (prefix + "-request.json")
    assembly = runtime / (assembly_name + ".dll")
    request = {
        "methods": selected, "assemblies": [{
            "id": "test-assembly" if path == assembly else f"discovery-image-{index}",
            "path": path.relative_to(run.root).as_posix(), "sha256": evidence.file_sha256(path),
        } for index, path in enumerate(images)],
    }
    write_new(request_path, evidence.canonical_bytes(request))
    inputs = [source / INVENTORY_PATH, methods_path, request_path, assembly,
              *(driver / name for name in (
                  "Hoard.Fixtures.Conformance.Discovery.dll", "Hoard.Fixtures.Conformance.Discovery.deps.json",
                  "Hoard.Fixtures.Conformance.Discovery.runtimeconfig.json",
                  "Hoard.Conformance.TestLogger.dll", "Microsoft.TestPlatform.VsTestConsole.TranslationLayer.dll",
                  "Microsoft.VisualStudio.TestPlatform.ObjectModel.dll"))]
    for path in {*inputs, *images}:
        path.chmod(0o400)
    bound = {path.relative_to(run.root).as_posix(): evidence.file_sha256(path) for path in inputs}
    print(json.dumps({"qualification": False, "phase": "inherited-exact-discovery"}), flush=True)
    result = run.command(
        ["dotnet", str(driver / "Hoard.Fixtures.Conformance.Discovery.dll"), str(run.root), str(vstest),
         request_path.relative_to(run.root).as_posix(), evidence.digest(request),
         output_path.relative_to(run.root).as_posix()],
        cwd=runtime, cache_id="inherited-discovery", timeout=180, record_execution=True,
        execution_inputs=tuple(bound), execution_outputs=(output_path.relative_to(run.root).as_posix(),))
    if result.exit_code:
        raise evidence.ConformanceError("WitnessMissing")
    record = evidence.load_json(run.read_execution_record(run.command_sequence))
    raw = read_bounded(output_path, 2 * 1024 * 1024)
    rows = admit_discovery(raw, methods, assembly=assembly_name)
    if (record.get("inputFiles") != bound
            or record.get("outputFiles") != {
                output_path.relative_to(run.root).as_posix(): hashlib.sha256(raw).hexdigest()}
            or any(evidence.file_sha256(run.root / path) != hashed for path, hashed in bound.items())):
        raise evidence.ConformanceError("InputChanged")
    if any(evidence.file_sha256(run.root / row["path"]) != row["sha256"] for row in request["assemblies"]):
        raise evidence.ConformanceError("InputChanged")
    summary = {
        "qualification": False, "profileComplete": False, "executionComplete": False,
        "methods": len(selected), "exactParameters": len(rows),
        "groups": {group: sum(row["matrixId"] == "inherited." + group for row in rows)
                   for group in ("lifecycle", "configuration", "discovery")},
        "inventorySha256": evidence.file_sha256(source / INVENTORY_PATH),
        "discoverySha256": evidence.file_sha256(output_path),
        "commandSha256": evidence.digest(record),
        "boundarySuitesExecuted": False, "controllersExecuted": False,
    }
    return summary, raw, request_path, output_path, vstest


def _inherited_runtime(run, repository, source, sources, config, feed, baseline_seal):
    print(json.dumps({"qualification": False, "phase": "inherited-source-build"}), flush=True)
    properties = ["-p:UseSharedCompilation=false", "-nodeReuse:false", "-v", "quiet"]
    for relative in (PROJECT, ARCHITECTURE_PROJECT, DISCOVERY_PROJECT):
        for arguments in (
                ["dotnet", "restore", str(source / relative), "--locked-mode", "--configfile", str(config)],
                ["dotnet", "build", str(source / relative), "-c", "Release", "--no-restore"]):
            baselines._command(run, [*arguments, *properties], cwd=source, cache_id="inherited-discovery")
    print(json.dumps({"qualification": False, "phase": "inherited-controller-preparation"}), flush=True)
    logger = run.root / "proofs/inherited-controller-logger.dll"
    shutil.copy2(source / f"tests/contracts/{LOGGER}/bin/Release/net10.0/{LOGGER}.dll", logger)
    verify_controller_baselines(run, baseline_seal)
    controllers, controller_parent, controller_invocations = _controller_phase(
        run, repository, source, "controllers", baseline_seal=baseline_seal,
        sdk_package=feed / f"{SDK}.0.1.0.nupkg", logger_path=logger)
    _prepare_solution_formatting(run, source, config, feed)
    reference_consumer = _native_reference_consumer(run, repository, source, controllers, baseline_seal)
    historical = verify_controller_baselines(run, baseline_seal)
    root = run.root / "stores/inherited-runtime"
    root.mkdir(mode=0o700)
    normative = root / "specs/004-module-discovery/contracts/openapi.json"
    normative.parent.mkdir(parents=True, mode=0o700)
    shutil.copy2(source / "specs/004-module-discovery/contracts/openapi.json", normative)
    driver = root / "driver"
    legacy._copy_runtime((source / DISCOVERY_PROJECT).parent / "bin/Release/net10.0", driver)
    files = controller_read_inputs(
        run.root, controllers["manifests"],
        extra=(normative, run.root / controllers["formatting"]["path"], run.root / baseline_seal["path"],
               run.root / "proofs/inherited-solution-lock-derivations.json",
               *(source / name for name in sources),
               *(run.root / name for name in historical["files"])))
    closure_path = run.root / "proofs/inherited-controller-read-inputs.json"
    write_new(closure_path, evidence.canonical_bytes(files))
    formatting = _format_prepared_controllers(run, controllers, files, closure_path, solution=source / "Hoard.slnx")
    prior = evidence.load_json(read_bounded(run.root / "proofs/composition-inputs.json", 2 * 1024**2))
    owner_raw = read_bounded(run.root / "runtime-owner.json", 65536)
    owner = evidence.load_json(owner_raw)
    variables = {
        **controllers["manifests"], "HOARD_DISCOVERY_RUN_ID": run.run_id,
        "HOARD_DISCOVERY_SDK": prior["environment"]["sdk"],
        "HOARD_DISCOVERY_OUTPUT": str(root / "performance"),
    }
    (root / "performance").mkdir(mode=0o700)
    environment_xml = "<EnvironmentVariables>" + "".join(
        "<" + key + ">" + escape(value) + "</" + key + ">" for key, value in variables.items()
    ) + "</EnvironmentVariables>"
    methods = inventory(read_bounded(source / INVENTORY_PATH, 2 * 1024**2), sources)
    discoveries, discovered, runtimes = {}, {}, {}
    for relative in (PROJECT, ARCHITECTURE_PROJECT):
        assembly_name = Path(relative).stem
        runtime = root / Path(relative).parent / "bin/Release/net10.0"
        runtime.parent.mkdir(parents=True, mode=0o700)
        legacy._copy_runtime((source / relative).parent / "bin/Release/net10.0", runtime)
        legacy.stage_sdk(feed / f"{SDK}.0.1.0.nupkg", runtime / f"{SDK}.dll")
        shutil.copy2(source / f"tests/contracts/{LOGGER}/bin/Release/net10.0/{LOGGER}.dll",
                     runtime / f"{LOGGER}.dll")
        for package_id in (SDK, LOGGER):
            package = next(row for row in prior["packages"] if row["packageId"] == package_id)
            if evidence.file_sha256(runtime / f"{package_id}.dll") not in package["runtimeAssemblies"].values():
                raise evidence.ConformanceError("PackageMismatch")
        summary, raw, request, output, _ = _inherited_discovery(
            run, source, sources, feed, prior["environment"], assembly_name=assembly_name,
            runtime=runtime, driver=driver)
        discoveries[assembly_name] = raw
        discovered[assembly_name] = summary
        runtimes[assembly_name] = runtime, request, output
    attempts, commands = [], []
    for (assembly_name, scope), expected in execution_scopes(discoveries, methods).items():
        runtime, request_path, discovery_path = runtimes[assembly_name]
        request = evidence.load_json(read_bounded(request_path, 2 * 1024**2))
        images = [row for row in request["assemblies"]
                  if (run.root / row["path"]).is_relative_to(runtime)]
        assembly = runtime / (assembly_name + ".dll")
        attempt = str(uuid.uuid4())
        inputs = evidence.admit_entity("RunInputs", {
            **prior, "runtimeAssemblies": {row["path"]: row["sha256"] for row in images},
            "configurationSha256": evidence.digest({
                "configuration": prior["configurationSha256"], "controllerReadInputs": files,
                "environmentSha256": evidence.digest(variables), "discoveryRequestSha256": evidence.digest(request)}),
            "invocation": ["component", "inherited", assembly_name, scope],
        })
        inputs_path = run.root / f"proofs/inherited-inputs-{attempt}.json"
        write_new(inputs_path, evidence.canonical_bytes(inputs))
        manifest = {
            "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": inputs["invocationGroupId"],
            "attemptId": attempt, "attemptSequence": 1, "purpose": "execution",
            "inputSha256": evidence.digest(inputs), "runInputsPath": inputs_path.relative_to(run.root).as_posix(),
            "assemblies": images, "packages": [{
                "id": package["packageId"],
                "path": (feed / (package["packageId"] + ".0.1.0.nupkg")).relative_to(run.root).as_posix(),
                "sha256": package["sha256"]} for package in inputs["packages"]], "expected": expected,
        }
        manifest_raw = evidence.canonical_bytes(manifest)
        manifest_path = run.root / f"runtime-input-{attempt}.json"
        write_new(manifest_path, manifest_raw)
        settings_data = runtime_settings(
            run.root, assembly, attempt, evidence.digest(manifest), evidence.digest(owner), environment_xml)
        settings_path = run.root / f"proofs/settings-{attempt}.runsettings"
        write_new(settings_path, settings_data)
        bound_paths = (
            manifest_path, inputs_path, run.root / "runtime-owner.json", settings_path, closure_path,
            source / INVENTORY_PATH, request_path, discovery_path, assembly,
            runtime / (assembly_name + ".deps.json"), runtime / (assembly_name + ".runtimeconfig.json"),
            runtime / (LOGGER + ".dll"), runtime / (SDK + ".dll"),
        )
        for path in (*bound_paths, *(run.root / name for name in files)):
            path.chmod(0o400)
        bound = {path.relative_to(run.root).as_posix(): evidence.file_sha256(path) for path in bound_paths}
        if any(evidence.file_sha256(run.root / name) != hashed for name, hashed in files.items()):
            raise evidence.ConformanceError("InputChanged")
        arguments = runtime_arguments(assembly, settings_path, [row["testIdentity"] for row in expected])
        started = time.monotonic() * 1000
        result = run.command(
            arguments, cwd=runtime, env=variables, kind="tests", cache_id="inherited-runtime", timeout=180,
            record_execution=True, execution_inputs=tuple(bound))
        ended = time.monotonic() * 1000
        parent_sha = category_command_proof(
            run, result, arguments=arguments, cwd=runtime, manifest=manifest,
            settings_data=settings_data, started_ms=started, ended_ms=ended)
        record = evidence.load_json(run.read_execution_record(run.command_sequence))
        if parent_sha is None or record.get("inputFiles") != bound:
            raise evidence.ConformanceError("ProofMismatch")
        output = run.root / ("runtime-" + attempt)
        transport = {
            "inputs": inputs, "manifest_data": manifest_raw, "owner_data": owner_raw,
            "witnesses_data": read_bounded(output / "witnesses.jsonl", 2 * 1024**2),
            "completion_data": read_bounded(output / "completion.json", 65536),
            "proofs": {path.name: read_bounded(path, 65536) for path in output.glob("proof-*.json")},
            "expected_tests": {row["testIdentity"]: ("none", row["matrixId"]) for row in expected},
            "manifest_sha256": evidence.digest(manifest), "owner_sha256": evidence.digest(owner),
            "started_ms": started, "ended_ms": ended,
        }
        observed = evidence.ingest_runtime_attempt(**transport)
        attempts.append({"assembly": assembly_name, "testClass": scope, "transport": transport})
        commands.append({"attemptId": attempt, "parentSha256": parent_sha})
        if any(evidence.file_sha256(run.root / name) != hashed for name, hashed in {
                **files, **bound, **inputs["runtimeAssemblies"],
        }.items()):
            raise evidence.ConformanceError("InputChanged")
        if (result.exit_code or observed["diagnosticCode"] != "None"
                or any(row["status"] != "Passed" for row in observed["witnesses"])):
            raise evidence.ConformanceError("WitnessMissing")
        print(json.dumps({"qualification": False, "phase": "inherited-runtime", "scope": scope,
                          "passedParameters": len(observed["witnesses"])}), flush=True)
    admitted = evidence.inspect_inherited_runtime_attempts(
        inventory_data=read_bounded(source / INVENTORY_PATH, 2 * 1024**2), sources=sources,
        discoveries=discoveries, attempts=attempts)
    if not admitted["executionComplete"]:
        raise evidence.ConformanceError("WitnessMissing")
    write_new(run.root / "proofs/inherited-scope-admission.json", evidence.canonical_bytes(admitted))
    from conformance_inherited import verify_discovery_materials, verify_discovery_mutation_membership
    materials = verify_discovery_materials(
        run.root, controllers["phases"]["discovery"], root / "performance/performance.json", run.run_id)
    mutation_source, mutation_sources = evidence.snapshot_sources(repository, run, name="inherited-mutation-source")
    if dict(mutation_sources) != dict(sources):
        raise evidence.ConformanceError("InputChanged")
    mutation_driver = mutation_source / Path(DISCOVERY_PROJECT).parent / "bin/Release/net10.0"
    mutation_driver.parent.mkdir(parents=True, mode=0o700)
    legacy._copy_runtime((source / DISCOVERY_PROJECT).parent / "bin/Release/net10.0", mutation_driver)
    mutations, mutation_parent, mutation_invocations = _controller_phase(
        run, repository, mutation_source, "mutations", baseline_seal=baseline_seal,
        sdk_package=feed / f"{SDK}.0.1.0.nupkg", logger_path=logger)
    verify_discovery_mutation_membership(run.root, mutations, admitted["discoveryCoverage"]["scenarios"])
    if dict(evidence.source_manifest(repository)) != dict(sources):
        raise evidence.ConformanceError("InputChanged")
    verify_controller_baselines(run, baseline_seal)
    return {
        "qualification": False, "profileComplete": False, "executionComplete": True,
        "nativeContainment": True, "controllerNativeContainment": False, "fullControllerAcceptance": False,
        "passedParameters": admitted["passedParameters"], "scopes": len(attempts),
        "scopeAdmissionSha256": evidence.digest(admitted), "controllerReadInputCount": len(files),
        "historicalBaselineSealSha256": baseline_seal["sha256"],
        "historicalBinariesPreparedBeforeCandidate": True,
        "controllerPreparationParentSha256": controller_parent,
        "commands": commands, "discoveries": discovered, "controllerPreparation": controllers["phases"],
        "preparedFormatting": formatting,
        "discoveryMaterials": materials,
        "nativeInvocations": {"controllers": controller_invocations, "mutations": mutation_invocations},
        "referenceConsumer": reference_consumer,
        "discoveryScenarios": {
            "qualification": False, "sha256": evidence.digest(admitted["discoveryCoverage"]),
            "parameters": len(admitted["discoveryCoverage"]["scenarios"]),
            "adapterScenarios": len(admitted["discoveryCoverage"]["adapterScenarios"]),
            "suites": len(admitted["discoveryCoverage"]["suites"]),
        },
        "discoveryMutations": {
            "qualification": False, "parentSha256": mutation_parent, "resultSha256": evidence.digest(mutations),
            "mutations": len(mutations["mutations"]),
            "negativeParameters": sum(row["negative"]["parameters"] for row in mutations["mutations"]),
            "repairedParameters": sum(row["repair"]["parameters"] for row in mutations["mutations"]),
        },
    }


def _composition_settings(root, assembly, attempt, manifest, owner):
    context = base64.b64encode(evidence.canonical_bytes({
        "schemaVersion": 1, "runId": manifest["runId"],
        "cases": {row["testIdentity"]: {"bindingId": "none", "caseId": row["caseId"]}
                  for row in expected_rows()},
    })).decode("ascii")
    return runtime_settings(
        root, assembly, attempt, evidence.digest(manifest), evidence.digest(owner),
        "<EnvironmentVariables><HOARD_ORIGINAL_CONTEXT>" + context
        + "</HOARD_ORIGINAL_CONTEXT></EnvironmentVariables>")


def _composition_input_files(inputs, record):
    files = {}
    for selected in (
            inputs["runtimeAssemblies"], inputs["locks"], record["inputFiles"],
            {f"feed/candidate/{row['packageId']}.{row['version']}.nupkg": row["sha256"]
             for row in inputs["packages"]}):
        for path, hashed in selected.items():
            path, hashed = evidence.relative_path(path), evidence.sha256(hashed)
            if path in files and files[path] != hashed:
                raise evidence.ConformanceError("InputChanged")
            files[path] = hashed
    return files


def _retain_composition_inputs(run, inputs, record):
    files = _composition_input_files(inputs, record)
    if dict(evidence.input_manifest(run.root, list(files))) != files:
        raise evidence.ConformanceError("InputChanged")
    selected = {path: hashed for path, hashed in files.items() if path.startswith(("stores/", "feed/", "cache/"))}
    config = "stores/candidate.NuGet.Config"
    configuration = evidence.synthetic_nuget_configuration(run.root / "feed/candidate")
    if selected.get(config) != hashlib.sha256(configuration).hexdigest():
        raise evidence.ConformanceError("ProofMismatch")
    directory = run.root / "proofs/composition-runtime-inputs"
    directory.mkdir(mode=0o700)
    paths = [path for path in files if path not in selected]
    for path in paths:
        target = run.root / path
        legacy.no_symlinks(target)
        if target.stat().st_nlink != 1:
            raise evidence.ConformanceError("OwnershipInvalid")
        target.chmod(0o400)
    for hashed, path in {hashed: path for path, hashed in selected.items() if path != config}.items():
        target = directory / hashed
        data = read_bounded(run.root / path, 32 * 1024**2)
        if hashlib.sha256(data).hexdigest() != hashed:
            raise evidence.ConformanceError("InputChanged")
        write_new(target, data)
        paths.append(target.relative_to(run.root).as_posix())
    snapshot = "proofs/composition-runtime-input-snapshot.json"
    write_new(run.root / snapshot, evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False, "scope": "composition-runtime-selected-inputs",
        "configurationPolicy": "synthetic-nuget-v1",
        "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "inputSha256": evidence.digest(inputs), "files": selected}))
    return (snapshot, *paths)


def verify_composition_case_report(root, inputs, owner, *, report_data=None):
    report_path = root / "proofs/composition-runtime-report.json"
    raw = read_bounded(report_path, 16 * 1024**2) if report_data is None else report_data
    report = evidence.admit_entity("QualificationReport", evidence.load_json(raw))
    inputs = evidence.admit_entity("RunInputs", inputs)
    if (report["inputs"] != inputs or inputs["profileId"] != "composition" or inputs["mode"] != "diagnostic"
            or report["state"] != "Incomplete" or report["qualification"] is not False
            or tuple(report["scope"]) != ("composition-runtime-diagnostic",)
            or owner["runId"] != inputs["runId"] or owner["invocationGroupId"] != inputs["invocationGroupId"]
            or owner["rootPathSha256"] != hashlib.sha256(str(root).encode()).hexdigest()):
        raise evidence.ConformanceError("ProofMismatch")
    if dict(evidence.input_manifest(root, list(report["proofs"]))) != report["proofs"]:
        raise evidence.ConformanceError("ProofMismatch")
    manifests = [path for path in report["proofs"] if re.fullmatch(r"runtime-input-[0-9a-f-]{36}\.json", path)]
    if len(manifests) != 1:
        raise evidence.ConformanceError("WitnessMissing")
    manifest_path, = manifests
    manifest_data = read_bounded(root / manifest_path, 2 * 1024**2)
    manifest = evidence.load_json(manifest_data)
    attempt = evidence._uuid(manifest["attemptId"])
    runtime_directory = f"runtime-{attempt}"
    settings_path = f"proofs/settings-{attempt}.runsettings"
    command_path = f"proofs/category-command-{attempt}-execution.json"
    owner_data = read_bounded(root / "runtime-owner.json", 65536)
    if (evidence.load_json(owner_data) != owner or manifest_path != f"runtime-input-{attempt}.json"
            or manifest["runInputsPath"] != "proofs/composition-inputs.json"
            or manifest["attemptSequence"] != 1 or manifest["purpose"] != "execution"
            or manifest["expected"] != expected_rows()):
        raise evidence.ConformanceError("ProofMismatch")
    cases = expected_cases("composition")
    results = {row["caseId"] + "/" + row["matrixId"]: row for row in report["results"]}
    if (len(results) != len(cases) or set(results) != {case.case_id + "/" + case.matrix_id for case in cases}
            or any(len(row["attempts"]) != 1 for row in results.values())):
        raise evidence.ConformanceError("WitnessMissing")
    first = report["results"][0]["attempts"][0]
    started_ms, ended_ms = first["startedMs"], first["endedMs"]
    staged = root / "stores/composition-runtime"
    assembly = staged / "Hoard.Composition.Tests.dll"
    settings = _composition_settings(root, assembly, attempt, manifest, owner)
    receipt, record = verify_category_command_proof(
        root, run_id=inputs["runId"], root_id=owner["rootId"], manifest=manifest,
        arguments=runtime_arguments(assembly, root / settings_path,
                                    [row["testIdentity"] for row in expected_rows()]),
        cwd=staged, settings_data=settings, started_ms=started_ms, ended_ms=ended_ms)
    required = {
        manifest_path, "runtime-owner.json", "proofs/composition-inputs.json", settings_path, command_path,
        f"proofs/execution-command-{receipt['commandSequence']:04}.json",
        runtime_directory + "/witnesses.jsonl", runtime_directory + "/completion.json",
        "proofs/category-composition-diagnostic-completion-inputs.json",
    }
    if not required <= report["proofs"].keys() or not isinstance(record.get("inputFiles"), dict):
        raise evidence.ConformanceError("WitnessMissing")
    config = "stores/candidate.NuGet.Config"
    bound_paths = {
        manifest_path, "proofs/composition-inputs.json", "runtime-owner.json", settings_path,
        "proofs/environment-admission.json", "proofs/composition-environment-admission.json", config,
        *(path.relative_to(root).as_posix() for path in (
            assembly, staged / f"{HOST}.dll", staged / f"{SDK}.dll", staged / f"{LOGGER}.dll",
            staged / "Hoard.Composition.Tests.deps.json", staged / "Hoard.Composition.Tests.runtimeconfig.json")),
    }
    if (set(record["inputFiles"]) != bound_paths
            or evidence.admit_entity("RunInputs", evidence.load_json(read_bounded(
                root / "proofs/composition-inputs.json", 2 * 1024**2))) != inputs):
        raise evidence.ConformanceError("ProofMismatch")
    files = _composition_input_files(inputs, record)
    selected = {path: hashed for path, hashed in files.items() if path.startswith(("stores/", "feed/", "cache/"))}
    snapshot_path = "proofs/composition-runtime-input-snapshot.json"
    snapshot = evidence._runtime_json(read_bounded(root / snapshot_path, 2 * 1024**2), {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "scope": evidence._constant("composition-runtime-selected-inputs"),
        "configurationPolicy": evidence._constant("synthetic-nuget-v1"),
        "runId": evidence._constant(inputs["runId"]),
        "invocationGroupId": evidence._constant(inputs["invocationGroupId"]),
        "inputSha256": evidence._constant(evidence.digest(inputs)), "files": evidence._hash_map,
    }, limit=2 * 1024**2)
    retained = {path: hashed for path, hashed in files.items() if path not in selected}
    retained.update({f"proofs/composition-runtime-inputs/{hashed}": hashed
                     for path, hashed in selected.items() if path != config})
    if snapshot["files"] != selected or snapshot_path not in report["proofs"]:
        raise evidence.ConformanceError("ProofMismatch")
    if any(report["proofs"].get(path) != hashed for path, hashed in retained.items()):
        raise evidence.ConformanceError("ProofMismatch")
    if any((root / path).stat().st_mode & 0o777 != 0o400 for path in retained):
        raise evidence.ConformanceError("ProofMismatch")
    if selected.get(config) != inputs["configurationSha256"]:
        raise evidence.ConformanceError("ProofMismatch")
    if selected.get(config) != hashlib.sha256(
            evidence.synthetic_nuget_configuration(root / "feed/candidate")).hexdigest():
        raise evidence.ConformanceError("ProofMismatch")
    observed = evidence.ingest_runtime_attempt(
        inputs=inputs, manifest_data=manifest_data, owner_data=owner_data,
        witnesses_data=read_bounded(root / runtime_directory / "witnesses.jsonl", 1024 * 1024),
        completion_data=read_bounded(root / runtime_directory / "completion.json", 64 * 1024),
        proofs={path.name: read_bounded(path, 64 * 1024)
                for path in (root / runtime_directory).glob("proof-*.json")},
        expected_tests={row["testIdentity"]: ("none", row["matrixId"]) for row in expected_rows()},
        manifest_sha256=hashlib.sha256(manifest_data).hexdigest(),
        owner_sha256=hashlib.sha256(owner_data).hexdigest(),
        started_ms=record["startedMs"], ended_ms=record["endedMs"],
        original_inputs={"none": {row["testIdentity"]: {
            "owner": ((staged / f"{HOST}.dll").relative_to(root).as_posix(), HOST)}
            for row in expected_rows()}},
    )
    if (observed["diagnosticCode"] != "None" or tuple(report["witnesses"]) != observed["witnesses"]
            or any(report["proofs"].get(runtime_directory + "/" + path) != hashed
                   for path, hashed in observed["proofs"].items())):
        raise evidence.ConformanceError("ProofMismatch")
    registered = set(retained) | required | {snapshot_path}
    registered.update(runtime_directory + "/" + path for path in observed["proofs"])
    selected = {row["testIdentity"]: row for row in observed["witnesses"]}
    for case in cases:
        if case.witnesses:
            material = evidence.composition_case_material(
                inputs, case_id=case.case_id, matrix_id=case.matrix_id,
                witnesses=[selected[identity] for identity in case.witnesses],
                sequence=1, started_ms=started_ms, ended_ms=ended_ms)
            expected = evidence._catalog_case_result(inputs, case, "Passed", [material["attempt"]])
            if any(report["proofs"].get(path) != hashlib.sha256(data).hexdigest()
                   or read_bounded(root / path, 512 * 1024) != data
                   for path, data in material["sourceProofs"].items()):
                raise evidence.ConformanceError("ProofMismatch")
            registered.update(material["sourceProofs"])
        else:
            expected = evidence._catalog_case_result(inputs, case, "Incomplete", [{
                "sequence": 1, "startedMs": started_ms, "endedMs": ended_ms, "status": "Incomplete",
                "witnessIds": [], "proofSha256": [], "diagnosticCode": "EvidenceIncomplete"}])
        if results[case.case_id + "/" + case.matrix_id] != expected:
            raise evidence.ConformanceError("ProofMismatch")
    if report["proofs"].keys() != registered:
        raise evidence.ConformanceError("ProofMismatch")
    evidence.verify_completion_inputs(root, report)
    return {
        "qualification": False, "reportState": "Incomplete", "reportSha256": hashlib.sha256(raw).hexdigest(),
        "passedCases": sum(bool(case.witnesses) for case in cases),
        "incompleteCases": sum(not case.witnesses for case in cases),
    }


def _verify_composition_observation_controls(proofs):
    targets = {"false-readiness": ("before-initialization", "ready"),
               "optimistic-cleanup": ("ownership-retained", "stopComplete")}
    rejected = set()
    for proof in proofs:
        rows = proof["compositionObservations"]
        originals = proof["originalObservations"]
        options = {"require_success": True, "test_identity": proof["testIdentity"]}
        evidence._ingest_composition_observations(rows, originals, set(), **options)
        for name, (stage, counter) in targets.items():
            if name in rejected:
                continue
            matches = [index for index, row in enumerate(rows) if row["stage"] == stage]
            if not matches:
                continue
            index = matches[0]
            if rows[index]["counters"][counter] != 0:
                raise evidence.ConformanceError("ProofMismatch")
            changed = evidence.load_json(evidence.canonical_bytes(rows))
            changed[index]["counters"][counter] = 1
            try:
                evidence._ingest_composition_observations(changed, originals, set(), **options)
            except evidence.ConformanceError as error:
                if str(error) != "ProofMismatch":
                    raise
            else:
                raise evidence.ConformanceError("ProofMismatch")
            rejected.add(name)
    if rejected != targets.keys():
        raise evidence.ConformanceError("WitnessMissing")
    return len(rejected)


def verify_composition_report_controls(root, inputs, owner, summary):
    if verify_composition_case_report(root, inputs, owner) != summary:
        raise evidence.ConformanceError("ProofMismatch")
    report = evidence.load_json(read_bounded(root / "proofs/composition-runtime-report.json", 16 * 1024**2))
    mutations = []
    for field, value in (("qualification", True), ("state", "Complete")):
        changed = evidence.load_json(evidence.canonical_bytes(report))
        changed[field] = value
        mutations.append(changed)
    for collection in ("results", "witnesses"):
        changed = evidence.load_json(evidence.canonical_bytes(report))
        changed[collection].pop(0)
        mutations.append(changed)
    for prefix in ("runtime-input-", "runtime-owner.json", "proofs/settings-",
                   "proofs/category-command-", "proofs/execution-command-",
                   "proofs/composition-runtime-input-snapshot.json"):
        changed = evidence.load_json(evidence.canonical_bytes(report))
        key, = (key for key in changed["proofs"] if key.startswith(prefix))
        del changed["proofs"][key]
        mutations.append(changed)
    changed = evidence.load_json(evidence.canonical_bytes(report))
    derivation = next(key for key in changed["proofs"] if re.fullmatch(r"proofs/composition-CP-.*", key))
    changed["proofs"][derivation] = "0" * 64
    mutations.append(changed)
    changed = evidence.load_json(evidence.canonical_bytes(report))
    changed["results"][0]["matrixId"] = "foreign"
    mutations.append(changed)
    changed = evidence.load_json(evidence.canonical_bytes(report))
    changed["witnesses"][0]["proofSha256"] = "0" * 64
    mutations.append(changed)
    changed = evidence.load_json(evidence.canonical_bytes(report))
    changed["proofs"]["proofs/composition-runtime-report.json"] = evidence.file_sha256(
        root / "proofs/composition-runtime-report.json")
    mutations.append(changed)
    for field in ("catalogSha256", "sdkSha256", "sourceManifestSha256", "configurationSha256",
                  "capabilitySha256", "environmentSha256"):
        changed = evidence.load_json(evidence.canonical_bytes(report))
        changed["inputs"][field] = "0" * 64
        mutations.append(changed)
    for collection in ("sourceManifest", "locks", "runtimeAssemblies"):
        changed = evidence.load_json(evidence.canonical_bytes(report))
        path = next(iter(changed["inputs"][collection]))
        changed["inputs"][collection][path] = "0" * 64
        mutations.append(changed)
    changed = evidence.load_json(evidence.canonical_bytes(report))
    changed["inputs"]["packages"][0]["sha256"] = "0" * 64
    mutations.append(changed)
    changed = evidence.load_json(evidence.canonical_bytes(report))
    changed["inputs"]["environment"]["sdk"] = "10.0.999"
    mutations.append(changed)
    changed = evidence.load_json(evidence.canonical_bytes(report))
    changed["unknownSchemaField"] = False
    mutations.append(changed)
    changed = evidence.load_json(evidence.canonical_bytes(report))
    changed["results"].append(changed["results"][0])
    mutations.append(changed)
    changed = evidence.load_json(evidence.canonical_bytes(report))
    changed["witnesses"].append(changed["witnesses"][0])
    mutations.append(changed)
    changed = evidence.load_json(evidence.canonical_bytes(report))
    changed["results"][0]["attempts"][0]["endedMs"] = -1
    mutations.append(changed)
    for changed in mutations:
        try:
            verify_composition_case_report(root, inputs, owner, report_data=evidence.canonical_bytes(changed))
        except evidence.ConformanceError:
            continue
        raise evidence.ConformanceError("ProofMismatch")
    if len(mutations) != 29:
        raise evidence.ConformanceError("WitnessMissing")
    manifest_path, = (path for path in report["proofs"]
                      if re.fullmatch(r"runtime-input-[0-9a-f-]{36}\.json", path))
    attempt = manifest_path.removeprefix("runtime-input-").removesuffix(".json")
    proofs = []
    for witness in report["witnesses"]:
        path = f'runtime-{attempt}/proof-{witness["executionId"]}.json'
        raw = read_bounded(root / path, 64 * 1024)
        if hashlib.sha256(raw).hexdigest() != witness["proofSha256"]:
            raise evidence.ConformanceError("ProofMismatch")
        proofs.append(evidence.load_json(raw))
    return {"qualification": False, "reportMutations": len(mutations),
            "semanticMutations": _verify_composition_observation_controls(proofs)}


def _composition_case_report(run, inputs, post_inputs, observed, *, runtime_directory, started_ms, ended_ms,
                             resources=(), transport_paths=()):
    inputs = evidence.admit_entity("RunInputs", inputs)
    post_inputs = evidence.admit_entity("RunInputs", post_inputs)
    evidence.verify_input_recomputation(inputs, post_inputs)
    if inputs["profileId"] != "composition" or inputs["mode"] != "diagnostic":
        raise evidence.ConformanceError("UnsupportedProfile")
    runtime_directory = evidence.relative_path(runtime_directory)
    witnesses = tuple(evidence.admit_entity("RuntimeWitness", row) for row in observed["witnesses"])
    selected = {row["testIdentity"]: row for row in witnesses}
    if (len(selected) != len(witnesses) or selected.keys() != composition_execution_cases().keys()
            or any(row["status"] != "Passed" for row in witnesses)
            or set(observed["proofs"]) != {f'proof-{row["executionId"]}.json' for row in witnesses}):
        raise evidence.ConformanceError("WitnessMissing")
    proofs = {runtime_directory + "/" + evidence.relative_path(path): evidence.sha256(hashed)
              for path, hashed in observed["proofs"].items()}
    if transport_paths:
        proofs.update(evidence.input_manifest(run.root, list(transport_paths)))
    if dict(evidence.input_manifest(run.root, list(proofs))) != proofs:
        raise evidence.ConformanceError("ProofMismatch")
    results = []
    for case in expected_cases("composition"):
        if case.witnesses:
            material = evidence.composition_case_material(
                inputs, case_id=case.case_id, matrix_id=case.matrix_id,
                witnesses=[selected[identity] for identity in case.witnesses],
                sequence=1, started_ms=started_ms, ended_ms=ended_ms)
            for path, raw in material["sourceProofs"].items():
                write_new(run.root / path, raw)
                proofs[path] = hashlib.sha256(raw).hexdigest()
            results.append(evidence._catalog_case_result(inputs, case, "Passed", [material["attempt"]]))
        else:
            results.append(evidence._catalog_case_result(inputs, case, "Incomplete", [{
                "sequence": 1, "startedMs": started_ms, "endedMs": ended_ms, "status": "Incomplete",
                "witnessIds": [], "proofSha256": [], "diagnosticCode": "EvidenceIncomplete"}]))
    completion = "proofs/category-composition-diagnostic-completion-inputs.json"
    raw = evidence.canonical_bytes(post_inputs)
    write_new(run.root / completion, raw)
    proofs[completion] = hashlib.sha256(raw).hexdigest()
    report = evidence.admit_entity("QualificationReport", {
        "schemaVersion": 1, "catalogRevision": evidence.CATALOG_REVISION, "inputs": inputs,
        "postInputSha256": evidence.digest(post_inputs), "results": results, "witnesses": witnesses,
        "resources": resources, "proofs": proofs, "state": "Incomplete", "qualification": False,
        "scope": ["composition-runtime-diagnostic"]})
    evidence.verify_completion_inputs(run.root, report)
    raw = evidence.canonical_bytes(report)
    write_new(run.root / "proofs/composition-runtime-report.json", raw)
    return {
        "qualification": False, "reportState": "Incomplete", "reportSha256": hashlib.sha256(raw).hexdigest(),
        "passedCases": sum(row["status"] == "Passed" for row in results),
        "incompleteCases": sum(row["status"] == "Incomplete" for row in results),
    }


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
    settings_data = _composition_settings(run.root, assembly, attempt, manifest, owner)
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
    post_sources = evidence.source_manifest(repository)
    post_environment = evidence.admit_entity("Environment", {
        **environment(run, phase="completion"), "nativeSqlite": "unobserved"})
    post_inputs = evidence.admit_entity("RunInputs", {
        **inputs, **evidence.source_identity(repository, ci_revision=ci_revision),
        "sourceManifest": post_sources, "sourceManifestSha256": evidence.digest(post_sources),
        "packages": [evidence.package_identity(feed, row["packageId"], row["version"])
                     for row in inputs["packages"]],
        "locks": {path: evidence.file_sha256(run.root / path) for path in inputs["locks"]},
        "runtimeAssemblies": {path: evidence.file_sha256(run.root / path) for path in inputs["runtimeAssemblies"]},
        "configurationSha256": evidence.file_sha256(config),
        "environment": post_environment, "environmentSha256": evidence.digest(post_environment),
    })
    try:
        retained_inputs = _retain_composition_inputs(run, inputs, record)
        case_report = _composition_case_report(
            run, inputs, post_inputs, admitted, runtime_directory=output.relative_to(run.root).as_posix(),
            started_ms=started, ended_ms=ended, resources=run.resource_projection(),
            transport_paths=(
                *retained_inputs,
                f"proofs/category-command-{attempt}-execution.json",
                f"proofs/execution-command-{record['sequence']:04}.json",
                output.relative_to(run.root).as_posix() + "/witnesses.jsonl",
                output.relative_to(run.root).as_posix() + "/completion.json"))
        if verify_composition_case_report(run.root, inputs, owner) != case_report:
            raise evidence.ConformanceError("ProofMismatch")
    except evidence.ConformanceError as error:
        sources = {str(Path(__file__).with_name(name)): name for name in (
            "conformance_composition_checks.py", "conformance_sdk_checks.py", "conformance_evidence.py")}
        locations = []
        frame = error.__traceback__
        while frame is not None:
            source_name = sources.get(frame.tb_frame.f_code.co_filename)
            if source_name is not None and 0 < frame.tb_lineno < 100000:
                locations.append({"source": source_name, "line": frame.tb_lineno})
            frame = frame.tb_next
        print(json.dumps({
            "qualification": False, "phase": "composition-report-replay-incomplete",
            "code": str(error), "locations": locations}), flush=True)
        raise
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
        "caseReport": case_report,
    }


def execute(repository, destination):
    if not native_execution_supported():
        raise evidence.ConformanceError("PrerequisiteMissing")
    run = OwnedRun.allocate(destination, repository, profile="composition")
    try:
        (run.root / "cache/.local/share").mkdir(parents=True, mode=0o700)
        (run.root / "cache/.local").chmod(0o700)
        source, sources = evidence.snapshot_sources(repository, run)
        print(json.dumps({"qualification": False, "phase": "inherited-historical-preparation"}), flush=True)
        baseline_seal, historical_parent, historical_invocations = _controller_phase(
            run, repository, source, "historical")
        verify_controller_baselines(run, baseline_seal)
        config, feed = baselines._config(run, "candidate")
        projects = (
            *PREREQUISITES,
            Project(f"tests/contracts/{SDK}/{SDK}.csproj", SDK),
            Project(f"tests/contracts/{LOGGER}/{LOGGER}.csproj", LOGGER),
            *(Project(f"tests/fixtures/conformance/Bindings/{name}/{name}.csproj",
                      f"Hoard.Fixtures.Conformance.Bindings.{name}")
              for name in ("Sqlite", "Memory", "Local", "ObjectSemantics")),
            Project("tests/fixtures/conformance/Contributor/Contributor.csproj",
                    "Hoard.Fixtures.Conformance.Contributor"),
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
        summary["historicalPreparationParentSha256"] = historical_parent
        summary["historicalNativeInvocations"] = historical_invocations
        summary["inheritedRuntime"] = _inherited_runtime(
            run, repository, source, sources, config, feed, baseline_seal)
        from conformance_inherited import run_controller_tooling
        summary["inheritedRuntime"]["tooling"] = run_controller_tooling(repository, run, sources)
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
    except (evidence.ConformanceError, OSError, ValueError, RuntimeError) as error:
        code = str(error) if isinstance(error, evidence.ConformanceError) else "EvidenceIncomplete"
        failure = {"qualification": False, "status": "Incomplete", "code": code}
        known_sources = {str(Path(__file__).with_name(name)): name for name in (
            "conformance_composition_checks.py", "conformance_inherited.py", "conformance_legacy.py",
            "foundation_evidence.py", "lifecycle_evidence.py", "configuration_evidence.py", "discovery_evidence.py")}
        frame = None if isinstance(error, evidence.ConformanceError) else error.__traceback__
        while frame is not None:
            name = known_sources.get(frame.tb_frame.f_code.co_filename)
            if name is not None:
                failure.update(source=name, line=frame.tb_lineno)
            frame = frame.tb_next
        print(json.dumps(failure))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
