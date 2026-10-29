"""Explicit contributor inputs, typed factories and captured images, never qualification."""

from collections.abc import Mapping
from dataclasses import dataclass
import base64
import binascii
import hashlib
import io
import json
import os
from pathlib import Path
import re
import time
from types import MappingProxyType
import uuid
import zipfile
import zlib
import xml.etree.ElementTree as ET

import conformance_evidence as evidence


@dataclass(frozen=True)
class BindingProject:
    root: Path
    project: str
    registration: Mapping
    sources: Mapping

    @property
    def inputs_sha256(self):
        return evidence.digest({"registration": self.registration, "sources": self.sources})


def _factory_type(value):
    if (not isinstance(value, str) or not 0 < len(value) <= 1024
            or re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*", value,
                            re.ASCII) is None):
        raise evidence.ConformanceError("BindingInvalid")
    return value


def artifact_binding_profile(declaration):
    declaration = evidence.admit_binding_declaration(declaration, require_archive_hash=False)
    if declaration["category"] != "artifacts":
        raise evidence.ConformanceError("BindingInvalid")
    capabilities = set(declaration["capabilities"])
    profile = {}
    for field, choices, prefixes in (
            ("durability", {"durable-local-process-crash": "LocalProcessCrash",
                            "non-durable-simulation": "SimulationOnly"}, ("durable-", "non-durable-")),
            ("enumeration", {"enumeration-snapshot": "Snapshot", "enumeration-incomplete": "Incomplete"},
             ("enumeration-",))):
        selected = [capability for capability in capabilities if capability.startswith(prefixes)]
        if len(selected) != 1 or selected[0] not in choices:
            raise evidence.ConformanceError("BindingInvalid")
        profile[field] = choices[selected[0]]
    return profile


def admit_binding_project(project, category):
    if category not in ("metadata", "artifacts"):
        raise evidence.ConformanceError("UnsupportedProfile")
    project = Path(project).absolute()
    if project.suffix != ".csproj":
        raise evidence.ConformanceError("BindingInvalid")
    sidecar = project.with_suffix(".conformance.json")
    deadline = time.monotonic() + 5
    captured = io.BytesIO()
    with evidence._input_root(project.parent) as (_, directory):
        evidence._source_file(
            directory, sidecar.name, remaining=2 * 1024 * 1024, deadline=deadline, target=captured)
    raw = captured.getvalue()
    value = evidence.load_json(raw)
    if not isinstance(value, dict) or not isinstance(value.get("components"), dict):
        raise evidence.ConformanceError("BindingInvalid")
    image = evidence._record({
        "packageId": evidence.stable_id, "version": evidence.stable_id, "assemblyName": evidence.stable_id})
    registration = evidence._record({
        "schemaVersion": evidence._constant(1), "project": evidence.relative_path,
        "factoryType": _factory_type, "adapterPackage": image,
        "declaration": lambda item: evidence.admit_binding_declaration(item, require_archive_hash=False),
        "components": evidence._record({role: image for role in evidence._SESSION_ROLES[category]}),
        "sourceFiles": evidence._list(evidence.relative_path, evidence.MAX_PROOF_FILES, unique=True),
    })(value)
    if category == "artifacts":
        artifact_binding_profile(registration["declaration"])
    relative = Path(registration["project"])
    if (relative.suffix != ".csproj" or relative.name != project.name
            or len(relative.parts) > min(32, len(project.parents))
            or registration["declaration"]["category"] != category
            or registration["components"]["factory"] != registration["adapterPackage"]):
        raise evidence.ConformanceError("BindingInvalid")
    root = project.parents[len(relative.parts) - 1]
    if root / relative != project:
        raise evidence.ConformanceError("BindingInvalid")
    registration_path = relative.with_suffix(".conformance.json").as_posix()
    if not {relative.as_posix(), registration_path}.issubset(registration["sourceFiles"]):
        raise evidence.ConformanceError("BindingInvalid")
    sources, total = {}, 0
    with evidence._input_root(root) as (_, directory):
        for path in sorted(registration["sourceFiles"]):
            hashed, size = evidence._source_file(
                directory, path, remaining=evidence.MAX_PROOF_BYTES - total, deadline=deadline)
            sources[path] = hashed
            total += size
    if sources[registration_path] != hashlib.sha256(raw).hexdigest():
        raise evidence.ConformanceError("InputChanged")
    return BindingProject(root, relative.as_posix(), registration, MappingProxyType(sources))


def snapshot_binding_project(project, category, expected_inputs_sha256, owned_run):
    expected = evidence.sha256(expected_inputs_sha256)
    admitted = admit_binding_project(project, category)
    if admitted.inputs_sha256 != expected:
        raise evidence.ConformanceError("InputChanged")
    if (owned_run.root.is_relative_to(admitted.root)
            or admitted.root.is_relative_to(owned_run.root)):
        raise evidence.ConformanceError("OwnershipInvalid")
    snapshot, sources = evidence.snapshot_sources(
        admitted.root, owned_run, name="binding-source", manifest=admitted.sources)
    if admit_binding_project(project, category).inputs_sha256 != expected:
        raise evidence.ConformanceError("InputChanged")
    return BindingProject(snapshot, admitted.project, admitted.registration, sources)


def _binding_writable(binding):
    try:
        return any((binding.root / path).stat(follow_symlinks=False).st_mode & 0o222 for path in binding.sources)
    except OSError:
        raise evidence.ConformanceError("InputChanged") from None


def _write_owned_input(owned_run, path, data):
    relative = path.relative_to(owned_run.root).as_posix()
    owner = owned_run._root_descriptor()
    try:
        with evidence._input_parent(owner, relative, create=True) as (directory, filename):
            descriptor = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o400, dir_fd=directory)
            with os.fdopen(descriptor, "wb") as output:
                output.write(data)
    except OSError:
        raise evidence.ConformanceError("OwnershipInvalid") from None
    finally:
        os.close(owner)
    return hashlib.sha256(data).hexdigest()


def _msbuild_literal(value):
    return "".join(f"%{ord(character):02X}" if character in "%$@;,?*()'" else character
                   for character in str(value))


def _require_successful_capture(observed):
    codes = {event["code"] for event in observed.events if event["code"] != "None"}
    if observed.exit_code or codes:
        raise evidence.ConformanceError(next(iter(codes)) if len(codes) == 1 else "CommandFailed")


def build_binding_project(binding, owned_run, configuration, feed, *, local_packages=(), compile_action=None,
                          msbuild=None):
    from conformance_execution import no_symlinks
    from conformance_lock_preparation import rebind_local_archives
    from conformance_sdk_checks import build

    if compile_action is not None and not callable(compile_action):
        raise evidence.ConformanceError("OwnershipInvalid")
    owned_run._check_ledger()
    if binding.root != owned_run.root / "binding-source":
        raise evidence.ConformanceError("OwnershipInvalid")
    category = binding.registration["declaration"]["category"]
    if (admit_binding_project(binding.root / binding.project, category).inputs_sha256 != binding.inputs_sha256
            or evidence.proof_manifest(binding.root) != binding.sources):
        raise evidence.ConformanceError("InputChanged")
    if _binding_writable(binding):
        raise evidence.ConformanceError("OwnershipInvalid")
    for path in (configuration, feed):
        if (".." in Path(path).parts or ";" in str(path)
                or not Path(path).is_absolute() or not Path(path).is_relative_to(owned_run.root)):
            raise evidence.ConformanceError("OwnershipInvalid")
        no_symlinks(path)
    workspace = owned_run.root / "binding-build"
    owner = owned_run._root_descriptor()
    try:
        os.mkdir("binding-build", mode=0o700, dir_fd=owner)
    except OSError:
        raise evidence.ConformanceError("OwnershipInvalid") from None
    finally:
        os.close(owner)

    configuration_relative = Path(configuration).relative_to(owned_run.root).as_posix()
    frozen = dict(evidence.input_manifest(owned_run.root, [configuration_relative]))

    def write(path, data):
        relative = path.relative_to(owned_run.root).as_posix()
        frozen[relative] = _write_owned_input(owned_run, path, data)

    document = ET.Element("Project")
    choices = ET.SubElement(document, "Choose")
    projects = {}
    deadline = time.monotonic() + 5
    total = 0
    for project in sorted(path for path in binding.sources if path.endswith(".csproj")):
        lock_path = (Path(project).parent / "packages.lock.json").as_posix()
        if lock_path not in binding.sources:
            raise evidence.ConformanceError("EvidenceIncomplete")
        captured = io.BytesIO()
        with evidence._input_root(binding.root) as (_, directory):
            hashed, size = evidence._source_file(
                directory, lock_path, remaining=min(2 * 1024 * 1024, evidence.MAX_PROOF_BYTES - total),
                deadline=deadline, target=captured)
        if hashed != binding.sources[lock_path]:
            raise evidence.ConformanceError("InputChanged")
        total += size
        prepared, _, _ = rebind_local_archives(captured.getvalue(), feed, local_packages=local_packages)
        if time.monotonic() >= deadline:
            raise evidence.ConformanceError("OutputLimitExceeded")
        target = workspace / hashlib.sha256(project.encode("utf-8")).hexdigest()
        lock = target / "packages.lock.json"
        write(lock, prepared)
        group = ET.SubElement(ET.SubElement(
            choices, "When", Condition=f"'$(MSBuildProjectFullPath)' == '{_msbuild_literal(binding.root / project)}'"),
            "PropertyGroup")
        values = {
            "BaseIntermediateOutputPath": str(target / "obj") + "/",
            "MSBuildProjectExtensionsPath": str(target / "obj") + "/",
            "BaseOutputPath": str(target / "bin") + "/",
            "NuGetLockFilePath": str(lock),
            "EmitCompilerGeneratedFiles": "true",
            "CompilerGeneratedFilesOutputPath": str(target / "compiler-generated"),
        }
        for name, value in values.items():
            ET.SubElement(group, name).text = _msbuild_literal(value)
        projects[project] = MappingProxyType({
            "root": target, "preparedLockSha256": hashlib.sha256(prepared).hexdigest(),
            "sourceLockSha256": hashed})
    properties = workspace / "binding.props"
    write(properties, ET.tostring(document, encoding="utf-8"))
    prepared = MappingProxyType({
        "qualification": False, "bindingInputsSha256": binding.inputs_sha256,
        "projects": MappingProxyType(projects),
        "propertiesSha256": frozen[properties.relative_to(owned_run.root).as_posix()]})
    observation = {} if compile_action is None else {"compile_action": lambda: compile_action(prepared)}
    if msbuild is not None:
        observation["msbuild"] = msbuild
    identity = binding.registration["adapterPackage"]
    try:
        build(owned_run, binding.root / binding.project, configuration, "binding-build", feed=feed,
              properties=("-p:CustomAfterDirectoryBuildProps=" + _msbuild_literal(properties),),
              package_id=identity["packageId"], package_version=identity["version"], **observation)
    finally:
        owned_run._check_ledger()
        if evidence.input_manifest(owned_run.root, sorted(frozen)) != frozen:
            raise evidence.ConformanceError("InputChanged")
        if (admit_binding_project(binding.root / binding.project, category).inputs_sha256 != binding.inputs_sha256
                or evidence.proof_manifest(binding.root) != binding.sources):
            raise evidence.ConformanceError("InputChanged")
        if _binding_writable(binding):
            raise evidence.ConformanceError("InputChanged")
    package = evidence.package_identity(feed, identity["packageId"], identity["version"])
    return MappingProxyType({**prepared, "package": package})


def capture_binding_evaluation_inputs(binding, owned_run, tool, toolchain_root, sdk_version, runtime_version):
    from conformance_execution import no_symlinks
    from conformance_sdk_checks import read_bounded

    owned_run._check_ledger()
    tool, toolchain_root = Path(tool), Path(toolchain_root)
    if (binding.root != owned_run.root / "binding-source"
            or not tool.is_absolute() or not tool.is_relative_to(owned_run.root) or ".." in tool.parts
            or tool.suffix != ".dll" or not toolchain_root.is_absolute() or ".." in toolchain_root.parts
            or toolchain_root.is_relative_to(owned_run.root) or owned_run.root.is_relative_to(toolchain_root)):
        raise evidence.ConformanceError("OwnershipInvalid")
    for path in (tool, toolchain_root):
        no_symlinks(path)
    sdk_version = evidence.stable_id(sdk_version)
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", sdk_version, re.ASCII) is None:
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    runtime_version = evidence.stable_id(runtime_version)
    if evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding):
        raise evidence.ConformanceError("InputChanged")
    workspace = owned_run.root / "binding-evaluation"
    request, driver, output = (workspace / name for name in ("request.json", "capture.proj", "inputs.json"))
    request_sha = _write_owned_input(owned_run, request, evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False, "sourcePath": "binding-source",
        "project": binding.project, "toolchainRoot": str(toolchain_root), "sources": binding.sources,
        "outputPath": output.relative_to(owned_run.root).as_posix()}))
    name = "Hoard.Fixtures.Conformance.BuildInputs.ReadBindingInputs"
    document = ET.Element("Project")
    ET.SubElement(document, "UsingTask", TaskName=name, AssemblyFile=_msbuild_literal(tool))
    ET.SubElement(ET.SubElement(document, "Target", Name="Capture"), name,
                  OwnedRootBase64=base64.b64encode(str(owned_run.root).encode("utf-8")).decode("ascii"),
                  RequestPath=request.relative_to(owned_run.root).as_posix(), RequestSha256=request_sha)
    driver_sha = _write_owned_input(owned_run, driver, ET.tostring(document, encoding="utf-8"))
    msbuild = toolchain_root / "sdk" / sdk_version / "MSBuild.dll"
    frozen = dict(evidence.input_manifest(
        owned_run.root, [tool.relative_to(owned_run.root).as_posix()]))
    frozen.update({request.relative_to(owned_run.root).as_posix(): request_sha,
                   driver.relative_to(owned_run.root).as_posix(): driver_sha})
    msbuild_relative = msbuild.relative_to(toolchain_root).as_posix()
    host = evidence.input_manifest(toolchain_root, [msbuild_relative])
    try:
        observed = owned_run.command(
            ["dotnet", "exec", "--fx-version", runtime_version, str(msbuild), str(driver), "-target:Capture",
             "-noconsolelogger", "-nologo", "-nodeReuse:false", "-verbosity:quiet"],
            cwd=tool.parent, kind="events", timeout=60, cache_id="binding-build",
            env={"DOTNET_ROLL_FORWARD": "Disable"})
        _require_successful_capture(observed)
        raw = read_bounded(output, 2 * 1024 * 1024)
        admitted = binding_evaluation_inputs(binding, raw, toolchain_root)
        rows = evidence.load_json(raw)["Items"]["_BindingInputs"]
        if any(set(row) != {"Identity", "Kind", "Sha256"} for row in rows):
            raise evidence.ConformanceError("EvidenceIncomplete")
        if tuple(observed.events) != ({"event": "control", "code": "None", "value": len(rows)},):
            raise evidence.ConformanceError("ProofMismatch")
        return admitted
    finally:
        owned_run._check_ledger()
        if (evidence.input_manifest(owned_run.root, sorted(frozen)) != frozen
                or evidence.input_manifest(toolchain_root, [msbuild_relative]) != host
                or request.stat().st_mode & 0o777 != 0o400 or driver.stat().st_mode & 0o777 != 0o400
                or evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding)):
            raise evidence.ConformanceError("InputChanged")


def capture_binding_compilation_inputs(binding, owned_run, built, tool, toolchain_root,
                                       sdk_version, runtime_version, package_root, package_inputs, *, restore_graphs=None):
    from conformance_execution import no_symlinks
    from conformance_sdk_checks import read_bounded

    owned_run._check_ledger()
    if (package_inputs is None) != (restore_graphs is not None):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    tool, toolchain_root, package_root = Path(tool), Path(toolchain_root), Path(package_root)
    for path in (tool, toolchain_root, package_root):
        if not path.is_absolute() or ".." in path.parts:
            raise evidence.ConformanceError("OwnershipInvalid")
        no_symlinks(path)
    if (binding.root != owned_run.root / "binding-source" or tool.suffix != ".dll"
            or not tool.is_relative_to(owned_run.root) or not package_root.is_relative_to(owned_run.root)
            or toolchain_root.is_relative_to(owned_run.root) or owned_run.root.is_relative_to(toolchain_root)):
        raise evidence.ConformanceError("OwnershipInvalid")
    sdk_version, runtime_version = evidence.stable_id(sdk_version), evidence.stable_id(runtime_version)
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", sdk_version, re.ASCII) is None:
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    projects = {path for path in binding.sources if path.endswith(".csproj")}
    if (built["bindingInputsSha256"] != binding.inputs_sha256 or set(built["projects"]) != projects
            or evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding)):
        raise evidence.ConformanceError("InputChanged")
    workspace = owned_run.root / "binding-build"
    for project in projects:
        expected = workspace / hashlib.sha256(project.encode("utf-8")).hexdigest()
        if built["projects"][project]["root"] != expected:
            raise evidence.ConformanceError("OwnershipInvalid")
    if (package_root.is_relative_to(workspace) or workspace.is_relative_to(package_root)
            or package_root.is_relative_to(binding.root) or binding.root.is_relative_to(package_root)):
        raise evidence.ConformanceError("OwnershipInvalid")
    properties = workspace / "binding.props"
    frozen = dict(evidence.input_manifest(
        owned_run.root, [path.relative_to(owned_run.root).as_posix() for path in (tool, properties)]))
    if (frozen[properties.relative_to(owned_run.root).as_posix()] != built["propertiesSha256"]
            or properties.stat().st_mode & 0o222):
        raise evidence.ConformanceError("InputChanged")
    output_paths = {kind: workspace / ("compiler-" + kind + ".json") for kind in ("sources", "inputs", "parameters")}
    request = workspace / "compiler-request.json"
    request_sha = _write_owned_input(owned_run, request, evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False, "sourcePath": "binding-source", "generatedPath": "binding-build",
        "packagePath": package_root.relative_to(owned_run.root).as_posix(), "toolchainRoot": str(toolchain_root),
        "sourceHashes": binding.sources,
        "outputs": {kind: path.relative_to(owned_run.root).as_posix() for kind, path in output_paths.items()}}))
    frozen[request.relative_to(owned_run.root).as_posix()] = request_sha
    msbuild_relative = "sdk/" + sdk_version + "/MSBuild.dll"
    host = evidence.input_manifest(toolchain_root, [msbuild_relative])
    logger = ("-logger:Hoard.Fixtures.Conformance.BuildInputs.CompilerInputsLogger," + _msbuild_literal(tool)
              + ";" + base64.b64encode(str(owned_run.root).encode("utf-8")).decode("ascii")
              + ";" + request.relative_to(owned_run.root).as_posix() + ";" + request_sha)
    try:
        observed = owned_run.command(
            ["dotnet", "exec", "--fx-version", runtime_version, str(toolchain_root / msbuild_relative),
             str(binding.root / binding.project), "-target:Build", "-p:Configuration=Release",
             "-p:CscToolPath=",
             "-p:CscToolExe=",
             "-p:UseSharedCompilation=false", "-p:CustomAfterDirectoryBuildProps=" + _msbuild_literal(properties),
             "-nodeReuse:false", "-maxCpuCount:1", "-noconsolelogger", "-nologo", "-verbosity:minimal", logger],
            cwd=tool.parent, kind="events", timeout=600, cache_id="binding-build",
            env={"DOTNET_ROLL_FORWARD": "Disable", "MSBUILDLOGTASKINPUTS": "1", "MSBUILDLOGIMPORTS": "1"})
        _require_successful_capture(observed)
        if tuple(observed.events) != ({"event": "control", "code": "None", "value": len(projects)},):
            raise evidence.ConformanceError("ProofMismatch")
        sources = binding_compilation_sources(
            binding, read_bounded(output_paths["sources"], 2 * 1024 * 1024), workspace)
        file_data = read_bounded(output_paths["inputs"], 2 * 1024 * 1024)
        if restore_graphs is not None:
            package_inputs = binding_restored_file_policy(binding, restore_graphs, file_data, package_root)
        inputs = binding_build_file_inputs(
            binding, file_data,
            workspace, toolchain_root, package_root, package_inputs)
        parameters = binding_compiler_parameter_inputs(
            inputs["compilations"], read_bounded(output_paths["parameters"], 2 * 1024 * 1024))
        if ({row["project"] for row in sources["compilations"]} != projects
                or {row["project"] for row in inputs["compilations"]} != projects
                or any(row["sources"] != next(item["inputs"]["Sources"] for item in inputs["compilations"]
                                              if item["project"] == row["project"])
                       for row in sources["compilations"])):
            raise evidence.ConformanceError("ProofMismatch")
        return MappingProxyType({"qualification": False, "sources": sources, "inputs": inputs, "parameters": parameters})
    finally:
        owned_run._check_ledger()
        if (evidence.input_manifest(owned_run.root, sorted(frozen)) != frozen
                or evidence.input_manifest(toolchain_root, [msbuild_relative]) != host
                or request.stat().st_mode & 0o777 != 0o400 or properties.stat().st_mode & 0o222
                or evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding)):
            raise evidence.ConformanceError("InputChanged")


def build_captured_binding_project(binding, owned_run, configuration, feed, tool, toolchain_root,
                                   sdk_version, runtime_version, *, local_packages=()):
    from conformance_sdk_checks import read_bounded
    from foundation_evidence import canonicalize_acceptance_archive

    tool = Path(tool)
    if ".." in tool.parts or not tool.is_absolute() or not tool.is_relative_to(owned_run.root):
        raise evidence.ConformanceError("OwnershipInvalid")
    support = evidence.proof_manifest(tool.parent)

    def verify_tool():
        if evidence.proof_manifest(tool.parent) != support:
            raise evidence.ConformanceError("InputChanged")

    try:
        evaluation = capture_binding_evaluation_inputs(
            binding, owned_run, tool, toolchain_root, sdk_version, runtime_version)
    finally:
        verify_tool()
    feed = Path(feed)
    if ".." in feed.parts or not feed.is_absolute() or not feed.is_relative_to(owned_run.root):
        raise evidence.ConformanceError("OwnershipInvalid")
    original_feed = evidence.proof_manifest(feed)
    package_root = owned_run.root / "cache/binding-build"
    captured = {}

    def compile_action(prepared):
        verify_tool()
        graphs = capture_binding_restore_graphs(
            binding, owned_run, prepared, tool, runtime_version, package_root)
        compilation = capture_binding_compilation_inputs(
            binding, owned_run, prepared, tool, toolchain_root, sdk_version, runtime_version,
            package_root, None, restore_graphs=graphs)
        assemblies = {}
        for row in compilation["sources"]["compilations"]:
            if "compiledOutputs" not in row:
                raise evidence.ConformanceError("EvidenceIncomplete")
            assemblies[row["project"]] = Path(row["compiledOutputs"]["assembly"]["path"]).name
        raw = read_bounded(owned_run.root / "binding-build/compiler-sources.json", 2 * 1024 * 1024)
        documents = capture_binding_compilation_documents(
            binding, owned_run, prepared, tool, runtime_version, raw, assemblies)
        captured.update(graphs=graphs, compilation=compilation, documents=documents)

    try:
        built = build_binding_project(
            binding, owned_run, configuration, feed, local_packages=local_packages, compile_action=compile_action,
            msbuild=("dotnet", "exec", "--fx-version", runtime_version,
                     str(Path(toolchain_root) / "sdk" / sdk_version / "MSBuild.dll")))
    finally:
        verify_tool()
    if set(captured) != {"graphs", "compilation", "documents"}:
        raise evidence.ConformanceError("EvidenceIncomplete")
    project_packages = {binding.project: built["package"]}
    for project in sorted(set(built["projects"]) - {binding.project}):
        packaging = evaluation["packaging"][project]
        if not packaging["packable"]:
            continue
        identities = {identity for graph in captured["graphs"].values()
                      for identity, path in graph["projects"].items() if path == project}
        identity = packaging["packageId"] + "/" + packaging["version"]
        if identities != {identity}:
            raise evidence.ConformanceError("ProofMismatch")
        package_id, version = packaging["packageId"], packaging["version"]
        archive = feed / f"{package_id}.{version}.nupkg"
        if archive.exists():
            raise evidence.ConformanceError("OwnershipInvalid")
        protected_feed = evidence.proof_manifest(feed)
        try:
            observed = owned_run.command([
                "dotnet", "exec", "--fx-version", runtime_version,
                str(Path(toolchain_root) / "sdk" / sdk_version / "MSBuild.dll"), str(binding.root / project),
                "-target:Pack", "-p:Configuration=Release", "-p:NoBuild=true", "-p:UseSharedCompilation=false",
                "-p:PackageOutputPath=" + _msbuild_literal(feed),
                "-p:CustomAfterDirectoryBuildProps=" + _msbuild_literal(owned_run.root / "binding-build/binding.props"),
                "-nodeReuse:false", "-nologo", "-verbosity:quiet"],
                cwd=binding.root / Path(project).parent, kind="build", timeout=600, cache_id="binding-build",
                env={"DOTNET_ROLL_FORWARD": "Disable"})
            _require_successful_capture(observed)
        finally:
            verify_tool()
            if (evidence.input_manifest(feed, sorted(protected_feed)) != protected_feed
                    or evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding)):
                raise evidence.ConformanceError("InputChanged")
        evidence.package_identity(feed, package_id, version)
        canonicalize_acceptance_archive(archive, expected_package_id=package_id)
        project_packages[project] = evidence.package_identity(feed, package_id, version)
    result = MappingProxyType({
        **built, "evaluation": evaluation, **captured, "projectPackages": MappingProxyType(project_packages),
        "feedInputs": original_feed, "toolPath": tool.relative_to(owned_run.root).as_posix(),
        "toolSupport": support})
    verify_captured_binding_project(binding, owned_run, result, toolchain_root, feed)
    return result


def verify_captured_binding_project(binding, owned_run, captured, toolchain_root, feed):
    from conformance_sdk_checks import read_bounded

    owned_run._check_ledger()
    feed = Path(feed)
    if ".." in feed.parts or not feed.is_absolute() or not feed.is_relative_to(owned_run.root):
        raise evidence.ConformanceError("OwnershipInvalid")
    tool = owned_run.root / evidence.relative_path(captured["toolPath"])
    if evidence.proof_manifest(tool.parent) != captured["toolSupport"]:
        raise evidence.ConformanceError("InputChanged")
    projects = {path for path in binding.sources if path.endswith(".csproj")}
    if (binding.root != owned_run.root / "binding-source" or captured["qualification"] is not False
            or captured["bindingInputsSha256"] != binding.inputs_sha256
            or any(set(captured[field]) != projects for field in (
                "projects", "documents", "graphs"))
            or set(captured["evaluation"]["packaging"]) != projects):
        raise evidence.ConformanceError("InputChanged")
    packaging = captured["evaluation"]["packaging"]
    if (not packaging[binding.project]["packable"]
            or set(captured["projectPackages"]) != {
                project for project, row in packaging.items() if row["packable"]}):
        raise evidence.ConformanceError("ProofMismatch")
    for project in projects:
        expected = owned_run.root / "binding-build" / hashlib.sha256(project.encode("utf-8")).hexdigest()
        if captured["projects"][project]["root"] != expected:
            raise evidence.ConformanceError("OwnershipInvalid")
    package_root = owned_run.root / "cache/binding-build"
    registered = binding.registration["adapterPackage"]
    documents = captured["documents"][binding.project]
    member = "lib/net10.0/" + registered["assemblyName"] + ".dll"
    if (documents["assembly"]["path"] != registered["assemblyName"] + ".dll"
            or captured["package"]["runtimeAssemblies"].get(member) != documents["assembly"]["sha256"]):
        raise evidence.ConformanceError("ProofMismatch")
    if evidence.package_identity(feed, registered["packageId"], registered["version"]) != captured["package"]:
        raise evidence.ConformanceError("InputChanged")
    for project, package in captured["projectPackages"].items():
        package = evidence.admit_entity("PackageIdentity", package)
        if (package["packageId"] != packaging[project]["packageId"]
                or package["version"] != packaging[project]["version"]):
            raise evidence.ConformanceError("ProofMismatch")
        actual = evidence.package_identity(feed, package["packageId"], package["version"])
        image = captured["documents"][project]["assembly"]
        if package["runtimeAssemblies"].get("lib/net10.0/" + image["path"]) != image["sha256"]:
            raise evidence.ConformanceError("ProofMismatch")
        if actual != package:
            raise evidence.ConformanceError("InputChanged")
    expected_feed = {
        **captured["feedInputs"],
        **{f'{package["packageId"]}.{package["version"]}.nupkg': package["sha256"]
           for package in captured["projectPackages"].values()}}
    if evidence.proof_manifest(feed) != expected_feed:
        raise evidence.ConformanceError("InputChanged")
    workspace = owned_run.root / "binding-build"
    if binding_evaluation_inputs(
            binding, read_bounded(owned_run.root / "binding-evaluation/inputs.json", 2 * 1024 * 1024),
            toolchain_root) != captured["evaluation"]:
        raise evidence.ConformanceError("InputChanged")
    sources_data = read_bounded(workspace / "compiler-sources.json", 2 * 1024 * 1024)
    if binding_compilation_sources(binding, sources_data, workspace) != captured["compilation"]["sources"]:
        raise evidence.ConformanceError("InputChanged")
    file_data = read_bounded(workspace / "compiler-inputs.json", 2 * 1024 * 1024)
    policy = binding_restored_file_policy(binding, captured["graphs"], file_data, package_root)
    files = binding_build_file_inputs(binding, file_data, workspace, toolchain_root, package_root, policy)
    parameters = binding_compiler_parameter_inputs(
        files["compilations"], read_bounded(workspace / "compiler-parameters.json", 2 * 1024 * 1024))
    if files != captured["compilation"]["inputs"] or parameters != captured["compilation"]["parameters"]:
        raise evidence.ConformanceError("InputChanged")
    for project, receipt in captured["documents"].items():
        root = captured["projects"][project]["root"]
        row = next(item for item in captured["compilation"]["sources"]["compilations"] if item["project"] == project)
        if binding_compilation_documents(
                row, read_bounded(root / "pdb-documents.json", 2 * 1024 * 1024),
                root / "bin/Release/net10.0", receipt["assembly"]["path"]) != receipt:
            raise evidence.ConformanceError("InputChanged")
        graph = binding_restore_graph(
            binding, read_bounded(root / "obj/project.assets.json", 2 * 1024 * 1024),
            read_bounded(root / "packages.lock.json", 2 * 1024 * 1024), project, package_root,
            expected_lock_sha256=captured["projects"][project]["preparedLockSha256"],
            content_hashes_data=read_bounded(root / "nuget-content.json", 2 * 1024 * 1024))
        if graph != captured["graphs"][project]:
            raise evidence.ConformanceError("InputChanged")
    toolchain = captured["evaluation"]["toolchain"]
    if toolchain != evidence.input_manifest(toolchain_root, sorted(toolchain)):
        raise evidence.ConformanceError("InputChanged")


def prepare_binding_project_consumer(binding, owned_run, candidate, candidate_sources, configuration, feed,
                                     tool, toolchain_root, sdk_version, runtime_version):
    from conformance_lock_preparation import prepare_project_lock, verify_project_lock
    from conformance_prepare import PREREQUISITES, TARGETS
    from conformance_sdk_checks import build, read_bounded

    owned_run._check_ledger()
    if binding.root != owned_run.root / "binding-source" or candidate != owned_run.root / "snapshot":
        raise evidence.ConformanceError("OwnershipInvalid")
    evidence.verify_snapshot(candidate, candidate_sources)
    adapter = binding.registration["adapterPackage"]
    projects = tuple(project for project in (*PREREQUISITES, *TARGETS)
                     if project.package is not None
                     and project.package not in ("Hoard.Application", "Hoard.Fixtures.Conformance.Host"))
    reserved = {project.package.casefold() for project in projects
                if project.package != "Hoard.Fixtures.Conformance.Contributor"}
    if adapter["packageId"].casefold() in reserved:
        raise evidence.ConformanceError("BindingInvalid")
    msbuild = ("dotnet", "exec", "--fx-version", runtime_version,
               str(Path(toolchain_root) / "sdk" / sdk_version / "MSBuild.dll"))
    records = []
    for project in projects:
        if project.package.casefold() == adapter["packageId"].casefold() and adapter["version"] == "0.1.0":
            continue
        selected = candidate / project.path
        lock, receipt = prepare_project_lock(selected, candidate, feed, "candidate")
        build(owned_run, selected, configuration, "contributor-prerequisites", feed=feed,
              lock=lock, package_id=project.package, msbuild=msbuild)
        if receipt is not None:
            verify_project_lock(receipt, candidate, feed)
            records.append(receipt)
    captured = build_captured_binding_project(
        binding, owned_run, configuration, feed, tool, toolchain_root, sdk_version, runtime_version)
    project = candidate / "tests/fixtures/conformance/Consumer/Consumer.csproj"
    lock, receipt = prepare_project_lock(project, candidate, feed, "candidate")
    build(owned_run, project, configuration, "contributor-prerequisites", lock=lock, msbuild=msbuild,
          properties=("-p:BaseOutputPath=bin/baseline-consumer/",))
    if receipt is not None:
        verify_project_lock(receipt, candidate, feed)
        records.append(receipt)
    source_lock = lock if lock is not None else project.with_name("packages.lock.json")
    baseline = evidence.load_json(read_bounded(source_lock, 2 * 1024 * 1024))
    archives = {}
    total, deadline = 0, time.monotonic() + 5

    def stage(package_id, version, path, *, expected=None):
        nonlocal total
        package_id, version = evidence.stable_id(package_id), evidence.stable_id(version)
        if time.monotonic() >= deadline:
            raise evidence.ConformanceError("DeadlineExceeded")
        data = read_bounded(path, min(evidence.MAX_PACKAGE_BYTES, evidence.MAX_PROOF_BYTES - total))
        total += len(data)
        hashed = hashlib.sha256(data).hexdigest()
        if expected is not None and hashed != expected:
            raise evidence.ConformanceError("InputChanged")
        key = (package_id.casefold(), version.casefold())
        if key in archives:
            if evidence.file_sha256(archives[key][2]) != hashed:
                raise evidence.ConformanceError("InputChanged")
            return
        if len(archives) >= 1024:
            raise evidence.ConformanceError("OutputLimitExceeded")
        target = owned_run.root / "binding-archives" / f"{package_id}.{version}.nupkg"
        _write_owned_input(owned_run, target, data)
        evidence.package_archive_identity(target.parent, package_id, version)
        archives[key] = (package_id, version, target)

    for package_id, row in baseline["dependencies"]["net10.0"].items():
        version = evidence.stable_id(row["resolved"])
        filename = f"{package_id}.{version}.nupkg"
        local = feed / filename
        path = (local if local.exists() else owned_run.root / "cache/contributor-prerequisites"
                / package_id.lower() / version.lower() / filename.lower())
        stage(package_id, version, path)
    for graph in captured["graphs"].values():
        for prefix, row in graph["packages"].items():
            path = (owned_run.root / "cache/binding-build" / prefix
                    / f'{row["packageId"].lower()}.{row["version"].lower()}.nupkg')
            stage(row["packageId"], row["version"], path, expected=row["archiveSha256"])
    for package in captured["projectPackages"].values():
        stage(package["packageId"], package["version"],
              feed / f'{package["packageId"]}.{package["version"]}.nupkg', expected=package["sha256"])
    required = {**{role: image for role, image in binding.registration["components"].items()},
                "provider": {"packageId": binding.registration["declaration"]["packageId"],
                             "version": binding.registration["declaration"]["packageVersion"]},
                "sdk": {"packageId": "Hoard.Testing.Conformance", "version": "0.1.0"},
                "abstractions": {"packageId": "Hoard.Abstractions", "version": "0.1.0"}}
    packages = {}
    for image in required.values():
        key = (image["packageId"].casefold(), image["version"].casefold())
        if key not in archives:
            raise evidence.ConformanceError("PrerequisiteMissing")
        package_id, version, path = archives[key]
        package = evidence.package_identity(path.parent, package_id, version)
        packages[key] = package
    consumer = build_binding_consumer(
        binding, owned_run, candidate, candidate_sources, tool, toolchain_root, sdk_version, runtime_version,
        source_lock=source_lock, packages=list(packages.values()),
        archive_paths=[path for _, _, path in archives.values()])
    for receipt in records:
        verify_project_lock(receipt, candidate, feed)
    verify_captured_binding_project(binding, owned_run, captured, toolchain_root, feed)
    evidence.verify_snapshot(candidate, candidate_sources)
    return MappingProxyType({"qualification": False, "captured": captured, "consumer": consumer})


def execute(repository, destination, *, project, category, binding_inputs_sha256):
    import conformance_sdk_checks as sdk
    from conformance_case_catalog import contributor_artifact_component_origin_counts, metadata_common_consumer_origin_counts
    from conformance_execution import OwnedRun, native_execution_supported, profile_budget

    if category not in ("metadata", "artifacts"):
        raise evidence.ConformanceError("BindingInvalid")
    expected = evidence.sha256(binding_inputs_sha256)
    if admit_binding_project(project, category).inputs_sha256 != expected:
        raise evidence.ConformanceError("InputChanged")
    if not native_execution_supported():
        raise evidence.ConformanceError("PrerequisiteMissing")
    run = OwnedRun.allocate(destination, repository, profile=category)
    seconds = profile_budget("artifacts") if category == "artifacts" else 60 * 60
    run.deadline = min(run.deadline, time.monotonic() + seconds)
    captured, binding, feed, toolchain_root = None, None, None, None
    try:
        (run.root / "cache/.local/share").mkdir(parents=True, mode=0o700)
        (run.root / "cache/.local").chmod(0o700)
        candidate, sources = evidence.snapshot_sources(repository, run)
        binding = snapshot_binding_project(project, category, expected, run)
        config, feed = run.root / "NuGet.Config", run.root / "feed/contributor"
        feed.mkdir(mode=0o700)
        _write_owned_input(run, config, evidence.synthetic_nuget_configuration(feed))
        observed_environment = sdk.environment(run)
        toolchain_root = sdk.inspection_reference_roots()["Microsoft.NETCore.App"].parents[1]
        sdk_version, runtime_version = observed_environment["sdk"], observed_environment["runtime"]
        tool_project = candidate / "tests/fixtures/conformance/BuildInputs/BuildInputs.csproj"
        sdk.build(run, tool_project, config, "contributor-tool", msbuild=(
            "dotnet", "exec", "--fx-version", runtime_version,
            str(toolchain_root / "sdk" / sdk_version / "MSBuild.dll")))
        tool = tool_project.parent / "bin/Release/net10.0/Hoard.Fixtures.Conformance.BuildInputs.dll"
        preparation = prepare_binding_project_consumer(
            binding, run, candidate, sources, config, feed, tool, toolchain_root, sdk_version, runtime_version)
        captured, consumer = preparation["captured"], preparation["consumer"]
        ci_revision = os.environ.get("GITHUB_SHA") if os.environ.get("GITHUB_ACTIONS") == "true" else None
        if os.environ.get("GITHUB_ACTIONS") == "true" and ci_revision is None:
            raise evidence.ConformanceError("InputChanged")
        prepared = prepare_binding_consumer_runtime(
            binding, run, repository, candidate, consumer, feed, observed_environment,
            group_id=str(uuid.uuid4()), budgets={**sdk.BUDGETS, "profileSeconds": seconds}, ci_revision=ci_revision,
            captured_build=captured, toolchain_root=toolchain_root)
        inputs = prepared["inputs"]
        _write_owned_input(run, run.root / "proofs/contributor-inputs.json", evidence.canonical_bytes(inputs))
        _write_owned_input(run, run.root / "runtime-owner.json", evidence.canonical_bytes({
            "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": inputs["invocationGroupId"],
            "rootId": run.root_id, "rootPathSha256": hashlib.sha256(str(run.root).encode()).hexdigest()}))
        manifest = binding_consumer_manifest(binding, run, inputs, attempt_id=str(uuid.uuid4()))
        binding_id = binding.registration["declaration"]["bindingId"]
        profile = artifact_binding_profile(binding.registration["declaration"]) if category == "artifacts" else None
        counts = (contributor_artifact_component_origin_counts(binding_id, profile=profile) if profile is not None
                  else metadata_common_consumer_origin_counts(binding_ids=(binding_id,)))
        result, observed, transport, discovery_sha = sdk._execute_runtime_transport(
            run, inputs, consumer["assemblyPath"], manifest,
            {identity: (binding_id, "none") for identity in counts}, {"contributor_binding": binding},
            origin_inputs={binding_id: consumer["components"]})
        sdk.validate_observation(
            observed, result, tuple(counts), "None", "Passed", 0, transport["proofs"], "None")
        sdk.validate_full_binding_origins(observed, inputs, counts)
        if result.execution_record_sha256 is None:
            raise evidence.ConformanceError("ProofMismatch")
        native = None
        if profile is not None:
            from conformance_contributor_crashes import execute_crashes
            from conformance_contributor_noncooperation import execute_noncooperation
            from conformance_contributor_transfers import execute_transfers

            native = {
                "crashRecovery": [dict(row) for row in execute_crashes(
                    run, inputs, consumer, binding, repository=repository)]
                if profile["durability"] == "LocalProcessCrash" else [],
                "retention": [dict(row) for row in execute_noncooperation(
                    run, inputs, consumer, binding, repository=repository)],
                "transfers": [dict(row) for row in execute_transfers(
                    run, inputs, consumer, binding, repository=repository)]}
        post = evidence.capture_profile_inputs(run, repository, candidate, **{
            **prepared["captureArguments"], "observed_environment": sdk.environment(run, phase="completion")})
        evidence.verify_input_recomputation(inputs, post)
        read_binding_runtime_controls(run, binding, inputs)
        verify_captured_binding_project(binding, run, captured, toolchain_root, feed)
        _write_owned_input(
            run, run.root / "proofs/contributor-completion-inputs.json", evidence.canonical_bytes(post))
        summary = {
            "qualification": False, "profileComplete": False, "scope": f"contributor-{category}-runtime-diagnostic",
            "bindingId": binding_id, "bindingInputsSha256": expected,
            "inputsSha256": evidence.digest(inputs), "postInputsSha256": evidence.digest(post),
            "passedParameters": len(counts), "sessionOrigins": sum(
                len(rows) for rows in observed["sessionOrigins"].values()),
            "discoverySha256": discovery_sha,
            "completionSha256": hashlib.sha256(transport["completion_data"]).hexdigest(),
            "runtimeProofsSha256": evidence.digest(observed["proofs"]),
            "nativeParentSha256": result.execution_record_sha256}
        if native is not None:
            summary["nativeArtifact"] = native
    except RuntimeError:
        raise evidence.ConformanceError("EvidenceIncomplete") from None
    finally:
        try:
            if captured is not None:
                verify_captured_binding_project(binding, run, captured, toolchain_root, feed)
        finally:
            if run.state in ("Allocated", "Active"):
                run.transition("Settling")
            if run.state == "Settling":
                if run.live_children():
                    run.transition("Retained")
                    raise evidence.ConformanceError("CleanupIncomplete")
                run.release()
    summary["resources"] = run.resource_projection()
    _write_owned_input(run, run.root / "proofs/contributor-runtime-summary.json", evidence.canonical_bytes(summary))
    print(evidence.canonical_bytes(summary).decode("utf-8"))
    return 0


def capture_binding_restore_graphs(binding, owned_run, built, tool, runtime_version, package_root):
    from conformance_execution import no_symlinks
    from conformance_sdk_checks import read_bounded

    owned_run._check_ledger()
    for path in (tool, package_root):
        if (".." in Path(path).parts or not Path(path).is_absolute()
                or not Path(path).is_relative_to(owned_run.root)):
            raise evidence.ConformanceError("OwnershipInvalid")
        no_symlinks(path)
    tool, package_root = Path(tool), Path(package_root)
    runtime_version = evidence.stable_id(runtime_version)
    projects = {path for path in binding.sources if path.endswith(".csproj")}
    if (binding.root != owned_run.root / "binding-source" or tool.suffix != ".dll"
            or built["bindingInputsSha256"] != binding.inputs_sha256 or set(built["projects"]) != projects):
        raise evidence.ConformanceError("InputChanged")
    graphs = {}
    for project in sorted(projects):
        workspace = owned_run.root / "binding-build" / hashlib.sha256(project.encode("utf-8")).hexdigest()
        record = built["projects"][project]
        if record["root"] != workspace:
            raise evidence.ConformanceError("OwnershipInvalid")
        assets, lock = workspace / "obj/project.assets.json", workspace / "packages.lock.json"
        request, output = workspace / "nuget-content-request.json", workspace / "nuget-content.json"
        assets_data = read_bounded(assets, 2 * 1024 * 1024)
        lock_data = read_bounded(lock, 2 * 1024 * 1024)
        if hashlib.sha256(lock_data).hexdigest() != record["preparedLockSha256"]:
            raise evidence.ConformanceError("InputChanged")
        payload = evidence.canonical_bytes({
            "schemaVersion": 1, "qualification": False,
            "assets": {"path": assets.relative_to(owned_run.root).as_posix(),
                       "sha256": hashlib.sha256(assets_data).hexdigest()},
            "cachePath": package_root.relative_to(owned_run.root).as_posix(),
            "outputPath": output.relative_to(owned_run.root).as_posix()})
        request_sha = _write_owned_input(owned_run, request, payload)
        frozen = {request.relative_to(owned_run.root).as_posix(): request_sha,
                  assets.relative_to(owned_run.root).as_posix(): hashlib.sha256(assets_data).hexdigest(),
                  lock.relative_to(owned_run.root).as_posix(): record["preparedLockSha256"]}
        frozen.update(evidence.input_manifest(
            owned_run.root, [tool.relative_to(owned_run.root).as_posix()]))
        try:
            observed = owned_run.command(
                ["dotnet", "exec", "--fx-version", runtime_version, str(tool), "content-hashes",
                 str(owned_run.root), request.relative_to(owned_run.root).as_posix(), request_sha],
                cwd=tool.parent, kind="events", timeout=60, cache_id="binding-build",
                env={"DOTNET_ROLL_FORWARD": "Disable"})
            _require_successful_capture(observed)
            graphs[project] = binding_restore_graph(
                binding, assets_data, lock_data, project, package_root,
                expected_lock_sha256=record["preparedLockSha256"],
                content_hashes_data=read_bounded(output, 2 * 1024 * 1024))
            if tuple(observed.events) != ({
                    "event": "control", "code": "None", "value": len(graphs[project]["packages"])},):
                raise evidence.ConformanceError("ProofMismatch")
        finally:
            owned_run._check_ledger()
            if evidence.input_manifest(owned_run.root, sorted(frozen)) != frozen:
                raise evidence.ConformanceError("InputChanged")
            if (evidence.input_manifest(binding.root, sorted(binding.sources)) != binding.sources
                    or evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding)):
                raise evidence.ConformanceError("InputChanged")
    return MappingProxyType(graphs)


def capture_binding_compilation_documents(binding, owned_run, built, tool, runtime_version,
                                          compilation_data, assemblies):
    from conformance_execution import no_symlinks
    from conformance_sdk_checks import read_bounded

    owned_run._check_ledger()
    tool = Path(tool)
    if (".." in tool.parts or not tool.is_absolute() or not tool.is_relative_to(owned_run.root)
            or tool.suffix != ".dll" or binding.root != owned_run.root / "binding-source"):
        raise evidence.ConformanceError("OwnershipInvalid")
    no_symlinks(tool)
    runtime_version = evidence.stable_id(runtime_version)
    projects = {path for path in binding.sources if path.endswith(".csproj")}
    if (built["bindingInputsSha256"] != binding.inputs_sha256 or set(built["projects"]) != projects
            or not isinstance(assemblies, (dict, MappingProxyType)) or set(assemblies) != projects):
        raise evidence.ConformanceError("InputChanged")
    generated = owned_run.root / "binding-build"
    compilations = binding_compilation_sources(binding, compilation_data, generated)
    rows = {row["project"]: row for row in compilations["compilations"]}
    if set(rows) != projects or evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding):
        raise evidence.ConformanceError("InputChanged")
    receipts = {}
    for project in sorted(projects):
        workspace = generated / hashlib.sha256(project.encode("utf-8")).hexdigest()
        if built["projects"][project]["root"] != workspace:
            raise evidence.ConformanceError("OwnershipInvalid")
        no_symlinks(workspace)
        output_root = workspace / "bin/Release/net10.0"
        assembly = evidence.relative_path(assemblies[project])
        if not assembly.endswith(".dll"):
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        image_paths = [output_root / assembly, output_root / (assembly[:-4] + ".pdb")]
        frozen = dict(evidence.input_manifest(
            owned_run.root, [path.relative_to(owned_run.root).as_posix() for path in [tool, *image_paths]]))
        request, output = workspace / "pdb-documents-request.json", workspace / "pdb-documents.json"
        payload = evidence.canonical_bytes({
            "schemaVersion": 1, "qualification": False, "sourcePath": "binding-source",
            "generatedPath": "binding-build", "project": project,
            "sourceDocumentPrefix": "/_/",
            "outputRoot": output_root.relative_to(owned_run.root).as_posix(),
            "assembly": {"path": assembly, "sha256": frozen[image_paths[0].relative_to(owned_run.root).as_posix()]},
            "pdb": {"path": assembly[:-4] + ".pdb",
                    "sha256": frozen[image_paths[1].relative_to(owned_run.root).as_posix()]},
            "outputPath": output.relative_to(owned_run.root).as_posix()})
        request_sha = _write_owned_input(owned_run, request, payload)
        frozen[request.relative_to(owned_run.root).as_posix()] = request_sha
        try:
            observed = owned_run.command(
                ["dotnet", "exec", "--fx-version", runtime_version, str(tool), "pdb-documents",
                 str(owned_run.root), request.relative_to(owned_run.root).as_posix(), request_sha],
                cwd=tool.parent, kind="events", timeout=60, cache_id="binding-build",
                env={"DOTNET_ROLL_FORWARD": "Disable"})
            _require_successful_capture(observed)
            receipts[project] = binding_compilation_documents(
                rows[project], read_bounded(output, 2 * 1024 * 1024), output_root, assembly)
            if tuple(observed.events) != ({
                    "event": "control", "code": "None", "value": len(receipts[project]["documents"])},):
                raise evidence.ConformanceError("ProofMismatch")
        finally:
            owned_run._check_ledger()
            if (evidence.input_manifest(owned_run.root, sorted(frozen)) != frozen
                    or request.stat().st_mode & 0o777 != 0o400
                    or evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding)):
                raise evidence.ConformanceError("InputChanged")
            binding_compilation_sources(binding, compilation_data, generated)
    return MappingProxyType(receipts)


def binding_factory_source(binding, adapter_package, provider_package):
    registration = binding.registration
    declaration = evidence.admit_binding_declaration(
        registration["declaration"], require_archive_hash=False)
    adapter = evidence.admit_entity("PackageIdentity", adapter_package)
    provider = evidence.admit_entity("PackageIdentity", provider_package)
    for package, package_id, version in (
            (adapter, registration["adapterPackage"]["packageId"], registration["adapterPackage"]["version"]),
            (provider, declaration["packageId"], declaration["packageVersion"])):
        if (package["packageId"].casefold() != package_id.casefold()
                or package["version"].casefold() != version.casefold()):
            raise evidence.ConformanceError("BindingInvalid")
    image = f'lib/net10.0/{registration["adapterPackage"]["assemblyName"]}.dll'
    if image not in adapter["runtimeAssemblies"]:
        raise evidence.ConformanceError("BindingInvalid")
    category = evidence._one_of("metadata", "artifacts")(declaration["category"])
    interface = "IMetadataConformanceBinding" if category == "metadata" else "IArtifactConformanceBinding"
    factory = _factory_type(registration["factoryType"])
    bindings = "global::Hoard.Testing.Conformance.Bindings"
    expected_category = "Metadata" if category == "metadata" else "Artifacts"
    capabilities = ", ".join(f'"{item}"' for item in declaration["capabilities"])
    faults = ", ".join(f"{bindings}.ConformanceFault.{item}" for item in declaration["faults"])
    profile_constants = ""
    construction = (
        f"    internal static {bindings}.{interface} Create()\n"
        "    {\n"
        f'        {bindings}.{interface} binding = new global::{factory}("{provider["sha256"]}");\n')
    if category == "artifacts":
        profile = artifact_binding_profile(declaration)
        storage = "global::Hoard.Abstractions.Storage"
        profile_constants = (
            f"    internal const {storage}.ArtifactDurability ExpectedDurability = "
            f'{storage}.ArtifactDurability.{profile["durability"]};\n'
            f"    internal const {storage}.ArtifactEnumerationConsistency ExpectedEnumeration = "
            f'{storage}.ArtifactEnumerationConsistency.{profile["enumeration"]};\n\n')
        construction = (
            f"    internal static {bindings}.{interface} Create() => "
            f'Validate(new global::{factory}("{provider["sha256"]}"));\n\n'
            f"    internal static {bindings}.{interface} Create({bindings}.ArtifactAssertionOptions options)\n"
            "    {\n"
            "        global::System.ArgumentNullException.ThrowIfNull(options);\n"
            f'        return Validate(new global::{factory}("{provider["sha256"]}", options));\n'
            "    }\n\n"
            f"    private static {bindings}.{interface} Validate({bindings}.{interface} binding)\n"
            "    {\n")
    return (
        "namespace Hoard.Fixtures.Conformance.Consumer;\n\n"
        "internal static class ContributorBindingFactory\n"
        "{\n"
        f'    internal const string BindingId = "{declaration["bindingId"]}";\n\n'
        + profile_constants + construction +
        "        var actual = binding.Declaration;\n"
        f"        {bindings}.ConformanceBindingAdmission.Validate(actual, "
        f"{bindings}.ConformanceCategory.{expected_category});\n"
        f'        if (actual.BindingId != "{declaration["bindingId"]}"\n'
        f'            || !global::System.StringComparer.OrdinalIgnoreCase.Equals(actual.PackageId, "{declaration["packageId"]}")\n'
        f'            || !global::System.StringComparer.OrdinalIgnoreCase.Equals(actual.PackageVersion, "{declaration["packageVersion"]}")\n'
        f'            || actual.PackageSha256 != "{provider["sha256"]}"\n'
        "            || !new global::System.Collections.Generic.HashSet<string>(actual.Capabilities, "
        f"global::System.StringComparer.Ordinal).SetEquals([{capabilities}])\n"
        f"            || !new global::System.Collections.Generic.HashSet<{bindings}.ConformanceFault>"
        f"(actual.Faults).SetEquals([{faults}]))\n"
        '        { throw new global::System.InvalidOperationException("BindingInvalid"); }\n'
        "        return binding;\n"
        "    }\n"
        "}\n"
    ).encode("ascii")


def capture_binding_consumer_lock(owned_run, tool, runtime_version, source_lock, adapter_package, archive_paths):
    from conformance_execution import no_symlinks
    from conformance_sdk_checks import read_bounded

    owned_run._check_ledger()
    adapter = evidence.admit_entity("PackageIdentity", adapter_package)
    runtime_version = evidence.stable_id(runtime_version)
    tool, source_lock = Path(tool), Path(source_lock)
    if not isinstance(archive_paths, (list, tuple)) or not 0 < len(archive_paths) <= 1024:
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    paths = [tool, source_lock, *(Path(path) for path in archive_paths)]
    if not 2 < len(paths) <= 1026 or tool.suffix != ".dll":
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    for path in paths:
        if not path.is_absolute() or ".." in path.parts or not path.is_relative_to(owned_run.root):
            raise evidence.ConformanceError("OwnershipInvalid")
        no_symlinks(path)
    archives = [path.relative_to(owned_run.root).as_posix() for path in paths[2:]]
    frozen = dict(evidence.input_manifest(
        owned_run.root, [source_lock.relative_to(owned_run.root).as_posix(), *archives]))
    support = evidence.proof_manifest(tool.parent)
    frozen.update({
        (tool.parent / path).relative_to(owned_run.root).as_posix(): hashed
        for path, hashed in support.items()})
    if tool.name not in support:
        raise evidence.ConformanceError("EvidenceIncomplete")
    expected_archive = f'{adapter["packageId"]}.{adapter["version"]}.nupkg'.casefold()
    selected = [path for path in archives if Path(path).name.casefold() == expected_archive]
    if len(selected) != 1 or frozen[selected[0]] != adapter["sha256"]:
        raise evidence.ConformanceError("InputChanged")
    source_hash = frozen[source_lock.relative_to(owned_run.root).as_posix()]
    source = evidence.load_json(read_bounded(source_lock, 2 * 1024 * 1024))
    workspace = owned_run.root / "binding-consumer"
    request, output, lock = (workspace / name for name in ("lock-request.json", "lock-receipt.json", "packages.lock.json"))
    request_hash = _write_owned_input(owned_run, request, evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False,
        "sourceLock": {"path": source_lock.relative_to(owned_run.root).as_posix(), "sha256": source_hash},
        "adapter": {"packageId": adapter["packageId"], "version": adapter["version"]},
        "archives": [{"path": path, "sha256": frozen[path]} for path in sorted(archives)],
        "outputPath": output.relative_to(owned_run.root).as_posix()}))
    frozen[request.relative_to(owned_run.root).as_posix()] = request_hash
    try:
        observed = owned_run.command(
            ["dotnet", "exec", "--fx-version", runtime_version, str(tool), "consumer-lock",
             str(owned_run.root), request.relative_to(owned_run.root).as_posix(), request_hash],
            cwd=tool.parent, kind="events", timeout=60, cache_id="binding-consumer",
            env={"DOTNET_ROLL_FORWARD": "Disable"})
        _require_successful_capture(observed)
        row = evidence._record({
            "packageId": evidence.stable_id, "version": evidence.stable_id,
            "archiveSha256": evidence.sha256, "nugetContentSha512": evidence._sha512})
        raw = read_bounded(output, 2 * 1024 * 1024)
        receipt_hash = hashlib.sha256(raw).hexdigest()
        frozen[output.relative_to(owned_run.root).as_posix()] = receipt_hash
        receipt = evidence._record({
            "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
            "sourceLockSha256": evidence._constant(source_hash),
            "packages": evidence._list(row, 1024), "lock": lambda value: value,
        })(evidence.load_json(raw))
        if tuple(observed.events) != ({
                "event": "control", "code": "None", "value": len(receipt["packages"])},):
            raise evidence.ConformanceError("ProofMismatch")
        packages = {}
        for package in receipt["packages"]:
            key = package["packageId"].casefold()
            name = f'{package["packageId"]}.{package["version"]}.nupkg'.casefold()
            selected = [path for path in archives if Path(path).name.casefold() == name]
            if (key in packages or len(selected) != 1
                    or frozen[selected[0]] != package["archiveSha256"]):
                raise evidence.ConformanceError("ProofMismatch")
            packages[key] = package
        derived = receipt["lock"]
        if (not isinstance(source, dict) or set(source) != {"version", "dependencies"}
                or not isinstance(derived, dict) or set(derived) != set(source)
                or type(derived["version"]) is not int or derived["version"] not in (1, 2)
                or derived["version"] != source["version"]
                or not isinstance(source["dependencies"], dict) or set(source["dependencies"]) != {"net10.0"}
                or not isinstance(derived["dependencies"], dict) or set(derived["dependencies"]) != {"net10.0"}):
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        original, entries = source["dependencies"]["net10.0"], derived["dependencies"]["net10.0"]
        if not isinstance(original, dict) or not isinstance(entries, dict) or len(entries) > 1024:
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        indexed = {}
        for name, entry in entries.items():
            key = evidence.stable_id(name).casefold()
            package = packages.get(key)
            if (key in indexed or package is None or not isinstance(entry, dict)
                    or not {"type", "resolved", "contentHash"} <= set(entry)
                    or not set(entry) <= {"type", "resolved", "contentHash", "requested", "dependencies"}
                    or entry["type"] not in ("Direct", "Transitive", "CentralTransitive")
                    or entry["resolved"] != package["version"]
                    or entry["contentHash"] != base64.b64encode(
                        bytes.fromhex(package["nugetContentSha512"])).decode("ascii")):
                raise evidence.ConformanceError("ProofMismatch")
            edges = entry.get("dependencies", {})
            if (not isinstance(edges, dict) or len(edges) > 1024
                    or len({evidence.stable_id(edge).casefold() for edge in edges}) != len(edges)
                    or any(not isinstance(value, str) or not 0 < len(value) <= 1024
                           or not value.isascii() for value in edges.values())):
                raise evidence.ConformanceError("EvidenceSchemaInvalid")
            indexed[key] = entry
        adapter_id = adapter["packageId"].casefold()
        if (set(indexed) != set(packages) or adapter_id not in indexed
                or indexed[adapter_id]["type"] != "Direct"
                or indexed[adapter_id]["resolved"].casefold() != adapter["version"].casefold()
                or indexed[adapter_id].get("requested") != f'[{adapter["version"]}, {adapter["version"]}]'):
            raise evidence.ConformanceError("ProofMismatch")
        roots, original_ids = {adapter_id}, set()
        for name, entry in original.items():
            key = evidence.stable_id(name).casefold()
            expected = ({**entry, "type": "Direct",
                         "requested": f'[{adapter["version"]}, {adapter["version"]}]'}
                        if key == adapter_id and isinstance(entry, dict) else entry)
            if key in original_ids or indexed.get(key) != expected:
                raise evidence.ConformanceError("ProofMismatch")
            original_ids.add(key)
            roots.add(key)
        if any(entry["type"] != "Transitive" or "requested" in entry
               for key, entry in indexed.items() if key not in roots):
            raise evidence.ConformanceError("ProofMismatch")
        reached, pending = set(), list(roots)
        while pending:
            key = pending.pop()
            if key in reached:
                continue
            if key not in indexed:
                raise evidence.ConformanceError("ProofMismatch")
            reached.add(key)
            pending.extend(name.casefold() for name in indexed[key].get("dependencies", {}))
        if reached != set(indexed):
            raise evidence.ConformanceError("ProofMismatch")
        lock_hash = _write_owned_input(owned_run, lock, evidence.canonical_bytes(derived))
        return MappingProxyType({**receipt, "lockPath": lock, "lockSha256": lock_hash,
                                 "receiptSha256": receipt_hash})
    finally:
        owned_run._check_ledger()
        if (evidence.input_manifest(owned_run.root, sorted(frozen)) != frozen
                or evidence.proof_manifest(tool.parent) != support
                or request.stat().st_mode & 0o777 != 0o400):
            raise evidence.ConformanceError("InputChanged")


def build_binding_consumer(binding, owned_run, candidate, candidate_sources, tool,
                           toolchain_root, sdk_version, runtime_version, *, source_lock, packages, archive_paths):
    from conformance_execution import no_symlinks
    from conformance_sdk_checks import build, read_bounded

    owned_run._check_ledger()
    candidate, tool, source_lock = map(Path, (candidate, tool, source_lock))
    toolchain_root = Path(toolchain_root)
    sdk_version, runtime_version = evidence.stable_id(sdk_version), evidence.stable_id(runtime_version)
    if (candidate != owned_run.root / "snapshot" or binding.root != owned_run.root / "binding-source"
            or not toolchain_root.is_absolute() or ".." in toolchain_root.parts
            or toolchain_root.is_relative_to(owned_run.root) or owned_run.root.is_relative_to(toolchain_root)
            or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", sdk_version, re.ASCII) is None):
        raise evidence.ConformanceError("OwnershipInvalid")
    if not isinstance(archive_paths, (list, tuple)) or not 0 < len(archive_paths) <= 1024:
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    paths = [tool, source_lock, *(Path(path) for path in archive_paths)]
    for path in [*paths, toolchain_root]:
        if ".." in path.parts or ";" in str(path) or not path.is_absolute():
            raise evidence.ConformanceError("OwnershipInvalid")
        no_symlinks(path)
    if any(not path.is_relative_to(owned_run.root) for path in paths):
        raise evidence.ConformanceError("OwnershipInvalid")
    evidence.verify_snapshot(candidate, candidate_sources)
    if evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding):
        raise evidence.ConformanceError("InputChanged")
    project = candidate / "tests/fixtures/conformance/Consumer/Consumer.csproj"
    if project.relative_to(candidate).as_posix() not in candidate_sources:
        raise evidence.ConformanceError("EvidenceIncomplete")
    msbuild_relative = f"sdk/{sdk_version}/MSBuild.dll"
    host = evidence.input_manifest(toolchain_root, [msbuild_relative])
    support = evidence.proof_manifest(tool.parent)
    frozen = dict(evidence.input_manifest(
        owned_run.root, [path.relative_to(owned_run.root).as_posix() for path in paths]))
    frozen.update({(tool.parent / path).relative_to(owned_run.root).as_posix(): hashed
                   for path, hashed in support.items()})
    packages = evidence._list(evidence._entity("PackageIdentity"), 1024)(packages)
    indexed = {package["packageId"].casefold(): package for package in packages}
    if len(indexed) != len(packages):
        raise evidence.ConformanceError("BindingInvalid")
    required = {binding.registration["adapterPackage"]["packageId"].casefold(),
                binding.registration["declaration"]["packageId"].casefold(),
                "hoard.testing.conformance", "hoard.abstractions"}
    required.update(identity["packageId"].casefold() for identity in binding.registration["components"].values())
    if not required <= set(indexed):
        raise evidence.ConformanceError("PrerequisiteMissing")
    for package in packages:
        filename = f'{package["packageId"]}.{package["version"]}.nupkg'
        selected = [Path(path) for path in archive_paths if Path(path).name == filename]
        if (len(selected) != 1 or frozen[selected[0].relative_to(owned_run.root).as_posix()] != package["sha256"]
                or evidence.package_identity(
                    selected[0].parent, package["packageId"], package["version"]) != package):
            raise evidence.ConformanceError("InputChanged")
    adapter = indexed[binding.registration["adapterPackage"]["packageId"].casefold()]
    provider = indexed[binding.registration["declaration"]["packageId"].casefold()]
    factory_data = binding_factory_source(binding, adapter, provider)
    workspace = owned_run.root / "binding-consumer"
    if any((workspace / name).exists() for name in ("bin", "obj")):
        raise evidence.ConformanceError("OwnershipInvalid")
    try:
        derived = capture_binding_consumer_lock(
            owned_run, tool, runtime_version, source_lock, adapter, archive_paths)
        feed = workspace / "feed"
        cached = {}
        for package in derived["packages"]:
            filename = f'{package["packageId"]}.{package["version"]}.nupkg'
            selected = [Path(path) for path in archive_paths if Path(path).name.casefold() == filename.casefold()]
            if len(selected) != 1:
                raise evidence.ConformanceError("ProofMismatch")
            if _write_owned_input(owned_run, feed / filename, read_bounded(
                    selected[0], evidence.MAX_PACKAGE_BYTES)) != package["archiveSha256"]:
                raise evidence.ConformanceError("InputChanged")
            prefix = f'{package["packageId"].lower()}/{package["version"].lower()}'
            cached[f'cache/binding-consumer/{prefix}/{filename.lower()}'] = package["archiveSha256"]
        configuration = workspace / "NuGet.Config"
        _write_owned_input(owned_run, configuration, evidence.frozen_nuget_configuration(feed))
        factory = workspace / "ContributorBindingFactory.cs"
        _write_owned_input(owned_run, factory, factory_data)
        frozen.update({(workspace / path).relative_to(owned_run.root).as_posix(): hashed
                       for path, hashed in evidence.proof_manifest(workspace).items()})
        properties = {
            "BaseIntermediateOutputPath": str(workspace / "obj") + "/",
            "MSBuildProjectExtensionsPath": str(workspace / "obj") + "/",
            "BaseOutputPath": str(workspace / "bin") + "/",
            "ConformanceContributorCategory": binding.registration["declaration"]["category"],
            "ConformanceContributorFactory": str(factory),
            "ConformanceContributorPackageId": adapter["packageId"],
            "ConformanceContributorPackageVersion": adapter["version"],
        }
        build(owned_run, project, configuration, "binding-consumer", lock=derived["lockPath"],
              properties=tuple(f"-p:{name}={_msbuild_literal(value)}" for name, value in properties.items()),
              msbuild=("dotnet", "exec", "--fx-version", runtime_version, str(toolchain_root / msbuild_relative)))
        if evidence.input_manifest(owned_run.root, sorted(cached)) != cached:
            raise evidence.ConformanceError("InputChanged")
        output = workspace / "bin/Release/net10.0"
        directory = output.relative_to(owned_run.root).as_posix()
        runtime = _binding_consumer_images(owned_run)
        assembly = output / "Hoard.Fixtures.Conformance.Consumer.dll"
        if assembly.relative_to(owned_run.root).as_posix() not in runtime:
            raise evidence.ConformanceError("EvidenceIncomplete")
        for name in ("Hoard.Testing.Conformance", "Hoard.Abstractions"):
            package = indexed[name.casefold()]
            expected = package["runtimeAssemblies"].get(f"lib/net10.0/{name}.dll")
            if expected is None or runtime.get(f"{directory}/{name}.dll") != expected:
                raise evidence.ConformanceError("InputChanged")
        components = binding_runtime_components(binding, packages, runtime, directory)
        return MappingProxyType({
            "qualification": False, "assemblyPath": assembly, "runtimeAssemblies": MappingProxyType(runtime),
            "components": components, "lock": derived,
            "packages": packages,
            "configurationPath": configuration, "controlInputs": MappingProxyType(frozen),
            "cachedArchives": MappingProxyType(cached),
            "factorySha256": frozen[factory.relative_to(owned_run.root).as_posix()]})
    finally:
        owned_run._check_ledger()
        if (evidence.input_manifest(owned_run.root, sorted(frozen)) != frozen
                or evidence.input_manifest(toolchain_root, [msbuild_relative]) != host
                or evidence.proof_manifest(tool.parent) != support
                or evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding)):
            raise evidence.ConformanceError("InputChanged")
        evidence.verify_snapshot(candidate, candidate_sources)


def _binding_consumer_images(owned_run):
    directory = "binding-consumer/bin/Release/net10.0"
    return {f"{directory}/{path}": hashed for path, hashed in evidence.proof_manifest(
        owned_run.root / directory, include_file=lambda path: path.endswith(
            (".dll", ".so", ".dylib", ".deps.json", ".runtimeconfig.json", ".runtimeconfig.dev.json"))).items()}


def vstest_runner_inputs(toolchain_root, sdk_version):
    from conformance_execution import no_symlinks

    directory = Path(toolchain_root) / "sdk" / evidence.stable_id(sdk_version)
    no_symlinks(directory)
    files = evidence.proof_manifest(
        directory, include_file=lambda path: "/" not in path or path.startswith("Extensions/")
        or path.count("/") == 1 and path.endswith(".resources.dll")
        and Path(path).name.startswith(("Microsoft.TestPlatform.", "Microsoft.VisualStudio.TestPlatform.",
                                        "vstest.console.")))
    if not {"vstest.console.dll", "vstest.console.deps.json", "vstest.console.runtimeconfig.json"} <= files.keys():
        raise evidence.ConformanceError("PrerequisiteMissing")
    return {"schemaVersion": 1, "qualification": False, "sdkVersion": sdk_version, "files": files}


def prepare_binding_consumer_runtime(binding, owned_run, repository, candidate, consumer, source_feed,
                                     observed_environment, *, group_id, budgets, ci_revision=None,
                                     captured_build=None, toolchain_root=None):
    from conformance_execution import no_symlinks
    from conformance_sdk_checks import LOGGER, inspection_reference_roots, read_bounded

    owned_run._check_ledger()
    candidate, source_feed = Path(candidate), Path(source_feed)
    if (consumer["qualification"] is not False or candidate != owned_run.root / "snapshot"
            or binding.root != owned_run.root / "binding-source"
            or not source_feed.is_absolute() or ".." in source_feed.parts
            or not source_feed.is_relative_to(owned_run.root)):
        raise evidence.ConformanceError("OwnershipInvalid")
    no_symlinks(source_feed)
    if (evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding)
            or _binding_consumer_images(owned_run) != consumer["runtimeAssemblies"]):
        raise evidence.ConformanceError("InputChanged")
    frozen = dict(evidence._hash_map(consumer["controlInputs"]))
    frozen.update(evidence._hash_map(consumer["cachedArchives"]))
    frozen.update(consumer["runtimeAssemblies"])
    frozen.update({f"binding-source/{path}": hashed for path, hashed in binding.sources.items()})
    if (captured_build is None) != (toolchain_root is None):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    if captured_build is not None:
        verify_captured_binding_project(binding, owned_run, captured_build, toolchain_root, source_feed)
        for directory in ("binding-evaluation", "binding-build"):
            frozen.update({f"{directory}/{path}": hashed
                           for path, hashed in evidence.proof_manifest(owned_run.root / directory).items()})
        files = captured_build["compilation"]["inputs"]
        consumed = [files["imports"], files.get("tools", {}), files.get("supportFiles", {})]
        consumed.extend(items for row in files["compilations"] for items in row["inputs"].values())
        frozen.update({"cache/binding-build/" + path[len("packages/"):]: hashed
                       for items in consumed for path, hashed in items.items() if path.startswith("packages/")})
        for graph in captured_build["graphs"].values():
            frozen.update({
                f'cache/binding-build/{prefix}/{row["packageId"].lower()}.{row["version"].lower()}.nupkg':
                row["archiveSha256"] for prefix, row in graph["packages"].items()})
        frozen.update({(source_feed / path).relative_to(owned_run.root).as_posix(): hashed
                       for path, hashed in evidence.proof_manifest(source_feed).items()})
    if evidence.input_manifest(owned_run.root, sorted(frozen)) != frozen:
        raise evidence.ConformanceError("InputChanged")
    packages = list(evidence._list(evidence._entity("PackageIdentity"), 1024)(consumer["packages"]))
    logger = evidence.package_identity(source_feed, "Hoard.Conformance.TestLogger", "0.1.0")
    logger_archive = source_feed / "Hoard.Conformance.TestLogger.0.1.0.nupkg"
    logger_source = candidate / LOGGER / "bin/Release/net10.0/Hoard.Conformance.TestLogger.dll"
    frozen.update(evidence.input_manifest(
        owned_run.root, [path.relative_to(owned_run.root).as_posix() for path in (logger_archive, logger_source)]))
    workspace = owned_run.root / "binding-consumer"
    output = workspace / "bin/Release/net10.0"

    def stage(path, source, expected):
        data = read_bounded(source, evidence.MAX_PACKAGE_BYTES)
        if expected is None or hashlib.sha256(data).hexdigest() != expected:
            raise evidence.ConformanceError("InputChanged")
        relative = path.relative_to(owned_run.root).as_posix()
        if relative in frozen:
            if frozen[relative] != expected:
                raise evidence.ConformanceError("InputChanged")
        else:
            frozen[relative] = _write_owned_input(owned_run, path, data)

    try:
        stage(workspace / "feed" / logger_archive.name, logger_archive, logger["sha256"])
        stage(output / logger_source.name, logger_source, logger["runtimeAssemblies"].get(
            "lib/net10.0/Hoard.Conformance.TestLogger.dll"))
        selected = [package for package in packages if package["packageId"].casefold() == logger["packageId"].casefold()]
        if selected:
            if len(selected) != 1 or selected[0] != logger:
                raise evidence.ConformanceError("InputChanged")
        else:
            packages.append(logger)
        indexed = {package["packageId"].casefold(): package for package in packages}
        if len(indexed) != len(packages):
            raise evidence.ConformanceError("BindingInvalid")
        declaration = dict(binding.registration["declaration"])
        provider = indexed.get(declaration["packageId"].casefold())
        if provider is None or provider["version"].casefold() != declaration["packageVersion"].casefold():
            raise evidence.ConformanceError("BindingInvalid")
        declaration["packageSha256"] = provider["sha256"]
        declaration = evidence.admit_binding_declaration(declaration)
        ordered = {key: declaration[key] for key in (
            "schemaVersion", "bindingId", "category", "packageId", "packageVersion",
            "packageSha256", "capabilities", "faults")}
        path = workspace / "declaration.json"
        frozen[path.relative_to(owned_run.root).as_posix()] = _write_owned_input(
            owned_run, path, json.dumps(ordered, separators=(",", ":"), ensure_ascii=True).encode("ascii"))
        runtime = _binding_consumer_images(owned_run)
        for path in runtime:
            (owned_run.root / path).chmod(0o400)
        frozen.update(runtime)
        runner_path = "proofs/contributor-vstest-inputs.json"
        frozen[runner_path] = _write_owned_input(owned_run, owned_run.root / runner_path, evidence.canonical_bytes(
            vstest_runner_inputs(
                inspection_reference_roots()["Microsoft.NETCore.App"].parents[1], observed_environment["sdk"])))
        controls_path = "proofs/contributor-build-controls.json"
        controls_hash = _write_owned_input(owned_run, owned_run.root / controls_path, evidence.canonical_bytes({
            "schemaVersion": 1, "qualification": False, "bindingInputsSha256": binding.inputs_sha256,
            "inputs": frozen, "runtimeAssemblies": runtime}))
        frozen[controls_path] = controls_hash
        arguments = {
            "profile_id": declaration["category"], "mode": "diagnostic", "invocation_group_id": group_id,
            "package_versions": tuple({"packageId": package["packageId"], "version": package["version"]}
                                      for package in packages),
            "feed": "binding-consumer/feed", "configuration": "binding-consumer/NuGet.Config",
            "lock_paths": tuple(sorted(path for path in frozen if path.endswith(".lock.json"))),
            "runtime_paths": tuple(sorted(runtime)),
            "binding_sources": ({"path": "binding-consumer/declaration.json",
                                 "adapterId": binding.registration["adapterPackage"]["packageId"]},),
            "observed_environment": observed_environment, "budgets": budgets,
            "invocation": ("binding-project", binding.inputs_sha256, controls_hash),
            "ci_revision": ci_revision,
            "frozen_archives": MappingProxyType({f"binding-consumer/feed/{path}": hashed
                                                for path, hashed in evidence.proof_manifest(workspace / "feed").items()}),
        }
        inputs = evidence.capture_profile_inputs(owned_run, repository, candidate, **arguments)
        return MappingProxyType({
            "qualification": False, "inputs": inputs, "captureArguments": MappingProxyType(arguments),
            "controlInputs": MappingProxyType(frozen)})
    finally:
        owned_run._check_ledger()
        if (evidence.input_manifest(owned_run.root, sorted(frozen)) != frozen
                or evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding)):
            raise evidence.ConformanceError("InputChanged")


def binding_consumer_manifest(binding, owned_run, inputs, *, attempt_id):
    from conformance_case_catalog import contributor_artifact_component_origin_counts, metadata_common_consumer_origin_counts

    inputs = evidence.admit_entity("RunInputs", inputs)
    declaration = binding.registration["declaration"]
    category, binding_id = declaration["category"], declaration["bindingId"]
    if (inputs["profileId"] != category or inputs["mode"] != "diagnostic" or inputs["runId"] != owned_run.run_id
            or len(inputs["bindings"]) != 1 or inputs["bindings"][0]["bindingId"] != binding_id
            or tuple(inputs["invocation"][:2]) != ("binding-project", binding.inputs_sha256)
            or len(inputs["invocation"]) != 3):
        raise evidence.ConformanceError("BindingInvalid")
    raw = read_binding_runtime_controls(owned_run, binding, inputs)
    if hashlib.sha256(raw).hexdigest() != inputs["invocation"][2]:
        raise evidence.ConformanceError("InputChanged")
    captured = evidence.capture_binding(
        owned_run.root, "binding-consumer/declaration.json", packages=inputs["packages"],
        adapter_id=binding.registration["adapterPackage"]["packageId"])
    if inputs["bindings"] != (captured,):
        raise evidence.ConformanceError("BindingInvalid")
    runtime = _binding_consumer_images(owned_run)
    if runtime != inputs["runtimeAssemblies"]:
        raise evidence.ConformanceError("InputChanged")
    directory = "binding-consumer/bin/Release/net10.0"
    components = binding_runtime_components(binding, inputs["packages"], runtime, directory)
    for package in inputs["packages"]:
        for member, hashed in package["runtimeAssemblies"].items():
            if member.startswith("lib/net10.0/") and runtime.get(f"{directory}/{Path(member).name}") != hashed:
                raise evidence.ConformanceError("InputChanged")
    required = {path for path, _ in components.values()}
    for name in ("Hoard.Testing.Conformance", "Hoard.Abstractions", "Hoard.Conformance.TestLogger"):
        path = f"{directory}/{name}.dll"
        hashed = runtime.get(path)
        if hashed is None:
            raise evidence.ConformanceError("EvidenceIncomplete")
        evidence._runtime_bytes_correspondence(inputs, hashed, path, name)
        required.add(path)
    assembly = f"{directory}/Hoard.Fixtures.Conformance.Consumer.dll"
    if assembly not in runtime:
        raise evidence.ConformanceError("EvidenceIncomplete")
    required.discard(assembly)
    paths = (assembly, *sorted(required))
    counts = (metadata_common_consumer_origin_counts(binding_ids=(binding_id,)) if category == "metadata"
              else contributor_artifact_component_origin_counts(
                  binding_id, profile=artifact_binding_profile(declaration)))
    provider = inputs["bindings"][0]["package"]
    return {
        "schemaVersion": 1, "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "attemptId": evidence._uuid(attempt_id), "attemptSequence": 1, "purpose": "execution",
        "inputSha256": evidence.digest(inputs), "runInputsPath": "proofs/contributor-inputs.json",
        "assemblies": [{"id": f"contributor-component-{index}", "path": path, "sha256": runtime[path]}
                       for index, path in enumerate(paths)],
        "packages": [{"id": provider["packageId"],
                      "path": f'binding-consumer/feed/{provider["packageId"]}.{provider["version"]}.nupkg',
                      "sha256": provider["sha256"]}],
        "expected": [{
            "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
            "assemblyId": "contributor-component-0", "packageId": provider["packageId"],
            "bindingId": binding_id, "matrixId": "none", "assertionSymbol": None,
            "caseId": "full-metadata-binding" if category == "metadata" else "contributor-artifact-component",
        } for identity in sorted(counts)],
    }


def read_binding_runtime_controls(owned_run, binding, inputs):
    from conformance_sdk_checks import inspection_reference_roots, read_bounded

    raw = read_bounded(owned_run.root / "proofs/contributor-build-controls.json", 16 * 1024 * 1024)
    controls = evidence._record({
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "bindingInputsSha256": evidence.sha256, "inputs": evidence._hash_map,
        "runtimeAssemblies": evidence._hash_map})(evidence.load_json(raw))
    if (hashlib.sha256(raw).hexdigest() != inputs["invocation"][2]
            or controls["bindingInputsSha256"] != binding.inputs_sha256
            or controls["runtimeAssemblies"] != inputs["runtimeAssemblies"]
            or evidence.input_manifest(owned_run.root, sorted(controls["inputs"])) != controls["inputs"]
            or _binding_consumer_images(owned_run) != inputs["runtimeAssemblies"]
            or evidence.proof_manifest(binding.root) != binding.sources or _binding_writable(binding)):
        raise evidence.ConformanceError("InputChanged")
    runner = read_bounded(owned_run.root / "proofs/contributor-vstest-inputs.json", 16 * 1024 * 1024)
    if (controls["inputs"].get("proofs/contributor-vstest-inputs.json") != hashlib.sha256(runner).hexdigest()
            or runner != evidence.canonical_bytes(vstest_runner_inputs(
                inspection_reference_roots()["Microsoft.NETCore.App"].parents[1], inputs["environment"]["sdk"]))):
        raise evidence.ConformanceError("InputChanged")
    evidence.verify_snapshot(owned_run.root / "snapshot", inputs["sourceManifest"])
    return raw


def artifact_process_context(run, inputs, consumer, binding):
    from conformance_execution import OwnedRun
    from conformance_sources import _readonly

    if type(run) is not OwnedRun:
        raise evidence.ConformanceError("OwnershipInvalid")
    inputs = evidence.admit_entity("RunInputs", inputs)
    if (inputs["profileId"] != "artifacts" or inputs["mode"] != "diagnostic"
            or inputs["runId"] != run.run_id or len(inputs["bindings"]) != 1
            or consumer["qualification"] is not False):
        raise evidence.ConformanceError("BindingInvalid")
    artifact_binding_profile(binding.registration["declaration"])
    read_binding_runtime_controls(run, binding, inputs)
    images = inputs["runtimeAssemblies"]
    if any(images.get(path) != hashed for path, hashed in consumer["runtimeAssemblies"].items()):
        raise evidence.ConformanceError("InputChanged")
    assembly = Path(consumer["assemblyPath"])
    if not assembly.is_relative_to(run.root):
        raise evidence.ConformanceError("OwnershipInvalid")
    relative = evidence.relative_path(assembly.relative_to(run.root).as_posix())
    directory = assembly.parent.relative_to(run.root).as_posix()
    selected = {
        relative,
        f"{directory}/Hoard.Testing.Conformance.dll", f"{directory}/Hoard.Abstractions.dll",
        assembly.with_suffix(".deps.json").relative_to(run.root).as_posix(),
        assembly.with_suffix(".runtimeconfig.json").relative_to(run.root).as_posix(),
        "proofs/contributor-inputs.json", "proofs/contributor-build-controls.json"}
    if (set(consumer["components"]) != set(evidence._SESSION_ROLES["artifacts"])
            or not selected - {"proofs/contributor-inputs.json", "proofs/contributor-build-controls.json"}
            <= images.keys()):
        raise evidence.ConformanceError("EvidenceIncomplete")
    selected = evidence.input_manifest(run.root, sorted(selected))
    if (any(selected[path] != images[path] for path in selected if path in images)
            or selected["proofs/contributor-inputs.json"] != evidence.digest(inputs)
            or selected["proofs/contributor-build-controls.json"] != inputs["invocation"][2]):
        raise evidence.ConformanceError("InputChanged")
    declaration = _readonly(run.root / "binding-consumer/declaration.json", 65536)
    return inputs, assembly, selected, declaration


def binding_runtime_components(binding, packages, runtime_assemblies, consumer_directory):
    packages = evidence._list(evidence._entity("PackageIdentity"), 1024)(packages)
    images = evidence._hash_map(runtime_assemblies)
    directory = evidence.relative_path(consumer_directory)
    indexed = {}
    for package in packages:
        key = package["packageId"].casefold()
        if key in indexed:
            raise evidence.ConformanceError("BindingInvalid")
        indexed[key] = package

    def selected(identity):
        package = indexed.get(identity["packageId"].casefold())
        if package is None or package["version"].casefold() != identity["version"].casefold():
            raise evidence.ConformanceError("BindingInvalid")
        return package

    registration = binding.registration
    selected(registration["adapterPackage"])
    declaration = registration["declaration"]
    selected({"packageId": declaration["packageId"], "version": declaration["packageVersion"]})
    components, owners = {}, {}
    for role, identity in registration["components"].items():
        package = selected(identity)
        member = f'lib/net10.0/{identity["assemblyName"]}.dll'
        hashed = package["runtimeAssemblies"].get(member)
        if hashed is None:
            raise evidence.ConformanceError("BindingInvalid")
        path = f'{directory}/{identity["assemblyName"]}.dll'
        owner = (package["packageId"].casefold(), package["version"].casefold(), hashed)
        if owners.setdefault(path.casefold(), owner) != owner:
            raise evidence.ConformanceError("BindingInvalid")
        if images.get(path) != hashed:
            raise evidence.ConformanceError("InputChanged")
        components[role] = (path, package["packageId"])
    return MappingProxyType(components)


def binding_evaluation_inputs(binding, data, toolchain_root):
    if not isinstance(data, bytes):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    if len(data) > 2 * 1024 * 1024:
        raise evidence.ConformanceError("OutputLimitExceeded")
    value = evidence.load_json(data)
    if (not isinstance(value, dict) or set(value) != {"Items"}
            or not isinstance(value["Items"], dict)
            or set(value["Items"]) != {"_BindingInputs", "_BindingProjects"}):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    project_rows = evidence._list(evidence._record({
        "Identity": evidence.relative_path, "PackageId": evidence.stable_id,
        "PackageVersion": evidence.stable_id, "IsPackable": evidence._one_of("true", "false"),
    }), 128)(value["Items"]["_BindingProjects"])
    packaging = {row["Identity"]: MappingProxyType({
        "packageId": row["PackageId"], "version": row["PackageVersion"],
        "packable": row["IsPackable"] == "true"}) for row in project_rows}
    if (len(packaging) != len(project_rows)
            or set(packaging) != {path for path in binding.sources if path.endswith(".csproj")}):
        raise evidence.ConformanceError("EvidenceIncomplete")
    rows = value["Items"]["_BindingInputs"]
    if not isinstance(rows, list) or not 0 < len(rows) <= evidence.MAX_PROOF_FILES:
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    metadata = {
        "Identity", "Kind", "Sha256", "FullPath", "RootDir", "Filename", "Extension", "RelativeDir",
        "Directory", "RecursiveDir", "ModifiedTime", "CreatedTime", "AccessedTime",
        "DefiningProjectFullPath", "DefiningProjectDirectory", "DefiningProjectName", "DefiningProjectExtension"}
    paths = {"source": set(), "toolchain": set()}
    hashes = {"source": {}, "toolchain": {}}
    for row in rows:
        if (not isinstance(row, dict) or not {"Identity", "Kind"} <= row.keys()
                or not row.keys() <= metadata
                or any(not isinstance(item, str) or len(item) > 4096 for item in row.values())):
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        kind = evidence._one_of("source", "toolchain")(row["Kind"])
        identity = evidence.relative_path(row["Identity"])
        prefix = kind + "/"
        if not identity.startswith(prefix):
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        relative = evidence.relative_path(identity[len(prefix):])
        if relative in paths[kind]:
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        paths[kind].add(relative)
        if "Sha256" in row:
            hashes[kind][relative] = evidence.sha256(row["Sha256"])
    if (binding.project not in paths["source"] or not paths["toolchain"]
            or not paths["source"].issubset(binding.sources)):
        raise evidence.ConformanceError("EvidenceIncomplete")
    sources = evidence.input_manifest(binding.root, sorted(binding.sources))
    if sources != binding.sources:
        raise evidence.ConformanceError("InputChanged")
    toolchain = evidence.input_manifest(toolchain_root, sorted(paths["toolchain"]))
    for kind, observed in (("source", sources), ("toolchain", toolchain)):
        if any(observed[path] != hashed for path, hashed in hashes[kind].items()):
            raise evidence.ConformanceError("InputChanged")
    return MappingProxyType({
        "schemaVersion": 1, "qualification": False, "bindingInputsSha256": binding.inputs_sha256,
        "project": binding.project, "packaging": MappingProxyType(packaging),
        "sources": MappingProxyType({path: sources[path] for path in sorted(paths["source"])}),
        "toolchain": toolchain})


def binding_restore_graph(binding, assets_data, lock_data, project, package_root, *,
                          expected_lock_sha256, content_hashes_data):
    if any(not isinstance(data, bytes) for data in (assets_data, lock_data, content_hashes_data)):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    if max(map(len, (assets_data, lock_data, content_hashes_data))) > 2 * 1024 * 1024:
        raise evidence.ConformanceError("OutputLimitExceeded")
    if hashlib.sha256(lock_data).hexdigest() != evidence.sha256(expected_lock_sha256):
        raise evidence.ConformanceError("InputChanged")
    content_row = evidence._record({
        "cachePath": evidence.relative_path, "archiveSha256": evidence.sha256,
        "contentSha512": evidence._sha512})
    content = evidence._record({
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "packages": evidence._list(content_row, 1024, minimum=0),
    })(evidence.load_json(content_hashes_data))
    content_rows = {row["cachePath"]: row for row in content["packages"]}
    if len(content_rows) != len(content["packages"]):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    project = evidence.relative_path(project)
    if project not in binding.sources or not project.endswith(".csproj"):
        raise evidence.ConformanceError("BindingInvalid")
    assets, lock = evidence.load_json(assets_data), evidence.load_json(lock_data)
    if (not isinstance(assets, dict) or type(assets.get("version")) is not int or assets["version"] not in (3, 4)
            or not isinstance(lock, dict) or type(lock.get("version")) is not int or lock["version"] not in (1, 2)
            or not isinstance(assets.get("targets"), dict) or set(assets["targets"]) != {"net10.0"}
            or not isinstance(lock.get("dependencies"), dict) or set(lock["dependencies"]) != {"net10.0"}
            or not isinstance(assets.get("libraries"), dict)
            or not isinstance(assets.get("project"), dict) or assets.get("logs")):
        raise evidence.ConformanceError("EvidenceIncomplete")
    restore = assets["project"].get("restore")
    if assets["version"] == 4:
        for owner in (assets["project"], restore):
            frameworks = owner.get("frameworks") if isinstance(owner, dict) else None
            if (not isinstance(frameworks, dict) or set(frameworks) != {"net10.0"}
                    or not isinstance(frameworks["net10.0"], dict)
                    or frameworks["net10.0"].get("framework") != "net10.0"
                    or frameworks["net10.0"].get("targetAlias") != "net10.0"):
                raise evidence.ConformanceError("EvidenceIncomplete")
    folders = assets.get("packageFolders")
    package_root = Path(package_root).absolute()
    if (not isinstance(restore, dict) or restore.get("projectPath") != str(binding.root / project)
            or restore.get("projectUniqueName") != str(binding.root / project)
            or restore.get("packagesPath") != str(package_root)
            or not isinstance(folders, dict) or len(folders) != 1
            or next(iter(folders)) not in (str(package_root), str(package_root) + os.sep)):
        raise evidence.ConformanceError("OwnershipInvalid")
    target, dependencies = assets["targets"]["net10.0"], lock["dependencies"]["net10.0"]
    libraries = assets["libraries"]
    if (not isinstance(target, dict) or not isinstance(dependencies, dict)
            or len(libraries) > 1024 or len(dependencies) > 1024 or set(target) != set(libraries)):
        raise evidence.ConformanceError("EvidenceIncomplete")

    def named(rows):
        if not isinstance(rows, dict) or len(rows) > 1024:
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        result = {}
        for name, value in rows.items():
            name = evidence.stable_id(name).casefold()
            if name in result:
                raise evidence.ConformanceError("EvidenceSchemaInvalid")
            result[name] = value
        return result

    def content_hash(value):
        if not isinstance(value, str) or len(value) != 88:
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        try:
            raw = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error):
            raise evidence.ConformanceError("EvidenceSchemaInvalid") from None
        if len(raw) != 64 or base64.b64encode(raw).decode("ascii") != value:
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        return raw.hex()

    locked = named(dependencies)
    observed, packages, projects = set(), {}, {}
    total, deadline = 0, time.monotonic() + 5
    for key, library in libraries.items():
        if not isinstance(key, str) or key.count("/") != 1:
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        package_id, version = (evidence.stable_id(part) for part in key.split("/"))
        name = package_id.casefold()
        dependency, resolved = locked.get(name), target[key]
        if (name in observed or not isinstance(dependency, dict) or not isinstance(library, dict)
                or not isinstance(resolved, dict) or library.get("type") != resolved.get("type")):
            raise evidence.ConformanceError("EvidenceIncomplete")
        lock_edges = named(dependency.get("dependencies", {}))
        target_edges = named(resolved.get("dependencies", {}))
        if any(not isinstance(value, str) or not 0 < len(value) <= 1024
               for edges in (lock_edges, target_edges) for value in edges.values()):
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        if lock_edges.keys() != target_edges.keys() or not target_edges.keys() <= locked.keys():
            raise evidence.ConformanceError("EvidenceIncomplete")
        observed.add(name)
        if library.get("type") == "package":
            prefix = evidence.relative_path(library.get("path"))
            if (dependency.get("type") not in ("Direct", "Transitive", "CentralTransitive")
                    or not isinstance(dependency.get("resolved"), str)
                    or dependency["resolved"].casefold() != version.casefold()
                    or prefix != name + "/" + version.lower()):
                raise evidence.ConformanceError("ProofMismatch")
            hashed = content_hash(library.get("sha512"))
            if hashed != content_hash(dependency.get("contentHash")):
                raise evidence.ConformanceError("ProofMismatch")
            receipt = content_rows.get(prefix)
            if receipt is None or receipt["contentSha512"] != hashed:
                raise evidence.ConformanceError("ProofMismatch")
            captured = io.BytesIO()
            filename = prefix + "/" + name + "." + version.lower() + ".nupkg"
            with evidence._input_root(package_root) as (_, directory):
                archive_hash, size = evidence._source_file(
                    directory, filename, remaining=min(evidence.MAX_PACKAGE_BYTES, evidence.MAX_PROOF_BYTES - total),
                    deadline=deadline, target=captured)
            total += size
            actual = evidence.package_archive_identity(package_root / prefix, name, version.lower())
            if (receipt["archiveSha256"] != archive_hash or actual["sha256"] != archive_hash
                    or actual["nugetSha512"] != hashlib.sha512(captured.getvalue()).hexdigest()):
                raise evidence.ConformanceError("InputChanged")
            packages[prefix] = MappingProxyType({
                "packageId": package_id, "version": version, "nugetContentSha512": hashed,
                "archiveSha256": archive_hash, "archiveSha512": actual["nugetSha512"]})
        elif library.get("type") == "project":
            path = library.get("msbuildProject")
            if (dependency.get("type") != "Project" or not isinstance(path, str) or len(path) > 512
                    or Path(path).is_absolute() or "\\" in path or "\x00" in path):
                raise evidence.ConformanceError("EvidenceIncomplete")
            path = Path(os.path.normpath(binding.root / Path(project).parent / path))
            if not path.is_relative_to(binding.root):
                raise evidence.ConformanceError("OwnershipInvalid")
            relative = evidence.relative_path(path.relative_to(binding.root).as_posix())
            if relative not in binding.sources or not relative.endswith(".csproj"):
                raise evidence.ConformanceError("EvidenceIncomplete")
            projects[key] = relative
        else:
            raise evidence.ConformanceError("EvidenceIncomplete")
    if observed != locked.keys():
        raise evidence.ConformanceError("EvidenceIncomplete")
    if set(packages) != set(content_rows):
        raise evidence.ConformanceError("EvidenceIncomplete")
    if evidence.input_manifest(binding.root, sorted(binding.sources)) != binding.sources:
        raise evidence.ConformanceError("InputChanged")
    if time.monotonic() >= deadline:
        raise evidence.ConformanceError("DeadlineExceeded")
    return MappingProxyType({
        "schemaVersion": 1, "qualification": False, "bindingInputsSha256": binding.inputs_sha256,
        "project": project, "assetsSha256": hashlib.sha256(assets_data).hexdigest(),
        "lockSha256": hashlib.sha256(lock_data).hexdigest(),
        "contentHashesSha256": hashlib.sha256(content_hashes_data).hexdigest(),
        "packages": MappingProxyType(packages), "projects": MappingProxyType(projects)})


def _compilation_sources(value):
    fields = {
        "project": evidence.relative_path, "succeeded": evidence._boolean,
        "sources": evidence._hash_map}
    if isinstance(value, (dict, MappingProxyType)) and "generatedOutputs" in value:
        fields["generatedOutputs"] = lambda items: (
            evidence._record({})(items) if items == {} else evidence._hash_map(items))
    if isinstance(value, Mapping) and "compiledOutputs" in value:
        artifact = evidence._record({"path": evidence.relative_path, "sha256": evidence.sha256})
        fields["compiledOutputs"] = evidence._record({"assembly": artifact, "pdb": artifact})
    return evidence._record(fields)(value)


def binding_compilation_sources(binding, data, generated_root):
    if not isinstance(data, bytes):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    if len(data) > 2 * 1024 * 1024:
        raise evidence.ConformanceError("OutputLimitExceeded")
    value = evidence._record({
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "succeeded": evidence._boolean,
        "compilations": evidence._list(_compilation_sources, 1024),
    })(evidence.load_json(data))
    generated_root = Path(generated_root).absolute()
    if (generated_root.is_relative_to(binding.root) or binding.root.is_relative_to(generated_root)):
        raise evidence.ConformanceError("OwnershipInvalid")
    projects, generated, generator_outputs, compiler_sources, compiled_outputs = set(), {}, set(), set(), set()
    source_inputs = 0
    for row in value["compilations"]:
        project = row["project"]
        if (not row["succeeded"] or project in projects or project not in binding.sources
                or not project.endswith(".csproj")):
            raise evidence.ConformanceError("EvidenceIncomplete")
        projects.add(project)
        outputs = row.get("generatedOutputs", {})
        compiled = row.get("compiledOutputs", {})
        for kind, artifact in compiled.items():
            path = artifact["path"]
            if not path.startswith("generated/") or not path.endswith(".dll" if kind == "assembly" else ".pdb"):
                raise evidence.ConformanceError("EvidenceSchemaInvalid")
            if path in compiled_outputs:
                raise evidence.ConformanceError("EvidenceIncomplete")
            compiled_outputs.add(path)
            relative = path[len("generated/"):]
            if generated.setdefault(relative, artifact["sha256"]) != artifact["sha256"]:
                raise evidence.ConformanceError("InputChanged")
        if (any(not path.startswith("generated/") or path in compiler_sources or path in generator_outputs
                or path in row["sources"] for path in outputs)
                or generator_outputs & row["sources"].keys()):
            raise evidence.ConformanceError("EvidenceIncomplete")
        generator_outputs.update(outputs)
        compiler_sources.update(row["sources"])
        source_inputs += len(row["sources"]) + len(outputs) + len(compiled)
        if source_inputs > evidence.MAX_PROOF_FILES:
            raise evidence.ConformanceError("OutputLimitExceeded")
        for path, hashed in {**row["sources"], **outputs}.items():
            namespace, separator, relative = path.partition("/")
            if not separator or namespace not in ("source", "generated"):
                raise evidence.ConformanceError("EvidenceSchemaInvalid")
            relative = evidence.relative_path(relative)
            if namespace == "source":
                if relative not in binding.sources:
                    raise evidence.ConformanceError("EvidenceIncomplete")
                if binding.sources[relative] != hashed:
                    raise evidence.ConformanceError("InputChanged")
            elif generated.setdefault(relative, hashed) != hashed:
                raise evidence.ConformanceError("InputChanged")
    if not value["succeeded"] or binding.project not in projects:
        raise evidence.ConformanceError("EvidenceIncomplete")
    if evidence.input_manifest(binding.root, sorted(binding.sources)) != binding.sources:
        raise evidence.ConformanceError("InputChanged")
    if generated and evidence.input_manifest(generated_root, sorted(generated)) != generated:
        raise evidence.ConformanceError("InputChanged")
    return MappingProxyType({**value, "bindingInputsSha256": binding.inputs_sha256})


def binding_compilation_documents(compilation, data, output_root, assembly_path):
    if not isinstance(data, bytes):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    if len(data) > 2 * 1024 * 1024:
        raise evidence.ConformanceError("OutputLimitExceeded")
    compilation = _compilation_sources(compilation)
    artifact = evidence._record({"path": evidence.relative_path, "sha256": evidence.sha256})
    value = evidence._record({
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "project": evidence.relative_path, "assembly": artifact, "pdb": artifact,
        "documents": evidence._hash_map,
    })(evidence.load_json(data))
    assembly = evidence.relative_path(assembly_path)
    if not assembly.endswith(".dll"):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    if not compilation["succeeded"]:
        raise evidence.ConformanceError("EvidenceIncomplete")
    if (value["project"] != compilation["project"] or value["assembly"]["path"] != assembly
            or value["pdb"]["path"] != assembly[:-4] + ".pdb"
            or any({**compilation["sources"], **compilation.get("generatedOutputs", {})}.get(path) != hashed
                   for path, hashed in value["documents"].items())):
        raise evidence.ConformanceError("ProofMismatch")
    if "compiledOutputs" in compilation and any(
            value[kind]["sha256"] != compilation["compiledOutputs"][kind]["sha256"] for kind in ("assembly", "pdb")):
        raise evidence.ConformanceError("ProofMismatch")
    outputs = {value[kind]["path"]: value[kind]["sha256"] for kind in ("assembly", "pdb")}
    if evidence.input_manifest(output_root, sorted(outputs)) != outputs:
        raise evidence.ConformanceError("InputChanged")
    generators = ({"generatedOutputsSha256": evidence.digest(compilation["generatedOutputs"])}
                  if "generatedOutputs" in compilation else {})
    return MappingProxyType({**value, "compilerSourcesSha256": evidence.digest(compilation["sources"]), **generators})


def _compiler_file_parameters(value):
    kinds = {
        "Sources", "References", "Analyzers", "AdditionalFiles", "AnalyzerConfigFiles",
        "EmbeddedFiles", "Resources", "LinkResources", "ResponseFiles", "Win32Resource",
        "Win32Manifest", "ApplicationConfiguration", "KeyFile", "SourceLink"}

    if (not isinstance(value, (dict, MappingProxyType)) or not {"Sources", "References"} <= value.keys()
            or not value.keys() <= kinds):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    return MappingProxyType({
        kind: evidence._record({})(items) if items == {} else evidence._hash_map(items)
        for kind, items in value.items()})


def _binding_build_file_document(data):
    if not isinstance(data, bytes):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    if len(data) > 2 * 1024 * 1024:
        raise evidence.ConformanceError("OutputLimitExceeded")
    row = evidence._record({
        "project": evidence.relative_path, "succeeded": evidence._boolean, "inputs": _compiler_file_parameters})
    errors = evidence._list(evidence.stable_id, 1024, minimum=0, unique=True)
    fields = {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "succeeded": evidence._boolean, "compilations": evidence._list(row, 1024),
        "imports": evidence._hash_map, "diagnosticCodes": errors, "observerErrors": errors,
    }
    document = evidence.load_json(data)
    if isinstance(document, dict) and "tools" in document:
        fields["tools"] = evidence._hash_map
    if isinstance(document, dict) and "supportFiles" in document:
        fields["supportFiles"] = evidence._hash_map
    return evidence._record(fields)(document)


def binding_build_file_inputs(binding, data, generated_root, toolchain_root, package_root, package_inputs):
    value = _binding_build_file_document(data)
    policy = evidence._record({})(package_inputs) if package_inputs == {} else evidence._hash_map(package_inputs)
    roots = {"source": binding.root, "generated": Path(generated_root).absolute(),
             "toolchain": Path(toolchain_root).absolute(), "packages": Path(package_root).absolute()}
    if any(left != right and root.is_relative_to(other)
           for left, root in roots.items() for right, other in roots.items()):
        raise evidence.ConformanceError("OwnershipInvalid")
    if not value["succeeded"] or value["diagnosticCodes"] or value["observerErrors"]:
        raise evidence.ConformanceError("EvidenceIncomplete")
    projects, inputs = set(), {kind: {} for kind in roots}

    def observe(items):
        for path, hashed in items.items():
            namespace, separator, relative = path.partition("/")
            if not separator or namespace not in roots:
                raise evidence.ConformanceError("EvidenceSchemaInvalid")
            relative = evidence.relative_path(relative)
            if inputs[namespace].setdefault(relative, hashed) != hashed:
                raise evidence.ConformanceError("InputChanged")
            expected = binding.sources if namespace == "source" else policy if namespace == "packages" else None
            if expected is not None:
                if relative not in expected:
                    raise evidence.ConformanceError("EvidenceIncomplete")
                if expected[relative] != hashed:
                    raise evidence.ConformanceError("InputChanged")

    observe(value["imports"])
    observe(value.get("tools", {}))
    observe(value.get("supportFiles", {}))
    for compilation in value["compilations"]:
        project = compilation["project"]
        if (not compilation["succeeded"] or project in projects or project not in binding.sources
                or not project.endswith(".csproj") or not compilation["inputs"]["Sources"]
                or not compilation["inputs"]["References"]):
            raise evidence.ConformanceError("EvidenceIncomplete")
        projects.add(project)
        for items in compilation["inputs"].values():
            observe(items)
    if binding.project not in projects:
        raise evidence.ConformanceError("EvidenceIncomplete")
    inputs["source"] = dict(binding.sources)
    if sum(map(len, inputs.values())) > evidence.MAX_PROOF_FILES:
        raise evidence.ConformanceError("OutputLimitExceeded")
    total, deadline = 0, time.monotonic() + 5
    for namespace, selected in inputs.items():
        if not selected:
            continue
        with evidence._input_root(roots[namespace]) as (_, descriptor):
            for path, expected in sorted(selected.items()):
                hashed, size = evidence._source_file(
                    descriptor, path, remaining=evidence.MAX_PROOF_BYTES - total, deadline=deadline)
                total += size
                if hashed != expected:
                    raise evidence.ConformanceError("InputChanged")
    if time.monotonic() >= deadline:
        raise evidence.ConformanceError("DeadlineExceeded")
    return MappingProxyType({
        **value, "bindingInputsSha256": binding.inputs_sha256, "packageInputsSha256": evidence.digest(policy)})


def binding_restored_file_policy(binding, graphs, data, package_root):
    value = _binding_build_file_document(data)
    projects = {path for path in binding.sources if path.endswith(".csproj")}
    if not isinstance(graphs, Mapping) or set(graphs) != projects:
        raise evidence.ConformanceError("EvidenceIncomplete")
    package_row = evidence._record({
        "packageId": evidence.stable_id, "version": evidence.stable_id,
        "nugetContentSha512": evidence._sha512, "archiveSha256": evidence.sha256,
        "archiveSha512": evidence._sha512})
    packages = {}
    for project, graph in graphs.items():
        if (not isinstance(graph, Mapping) or graph.get("project") != project
                or graph.get("bindingInputsSha256") != binding.inputs_sha256
                or not isinstance(graph.get("packages"), Mapping) or len(graph["packages"]) > 1024):
            raise evidence.ConformanceError("ProofMismatch")
        for prefix, row in graph["packages"].items():
            prefix, row = evidence.relative_path(prefix), package_row(row)
            if prefix != row["packageId"].lower() + "/" + row["version"].lower():
                raise evidence.ConformanceError("ProofMismatch")
            if prefix in packages and packages[prefix] != row:
                raise evidence.ConformanceError("InputChanged")
            packages[prefix] = row
            if len(packages) > 1024:
                raise evidence.ConformanceError("OutputLimitExceeded")
    observed = {}
    groups = [value["imports"], value.get("tools", {}), value.get("supportFiles", {})]
    groups.extend(items for row in value["compilations"] for items in row["inputs"].values())
    for items in groups:
        for path, hashed in items.items():
            if path.startswith("packages/"):
                relative = path[len("packages/"):]
                if observed.setdefault(relative, hashed) != hashed:
                    raise evidence.ConformanceError("InputChanged")
                if len(observed) > evidence.MAX_PROOF_FILES:
                    raise evidence.ConformanceError("OutputLimitExceeded")
    selections = {}
    for relative in observed:
        parts = relative.split("/", 2)
        if len(parts) != 3 or "/".join(parts[:2]) not in packages:
            raise evidence.ConformanceError("EvidenceIncomplete")
        selections.setdefault("/".join(parts[:2]), []).append(parts[2])
    total, deadline, policy = 0, time.monotonic() + 5, {}
    for prefix, members in sorted(selections.items()):
        row = packages[prefix]
        name, version = prefix.split("/")
        archive = prefix + "/" + name + "." + version + ".nupkg"
        captured = io.BytesIO()
        with evidence._input_root(package_root) as (_, directory):
            hashed, size = evidence._source_file(
                directory, archive, remaining=min(evidence.MAX_PACKAGE_BYTES, evidence.MAX_PROOF_BYTES - total),
                deadline=deadline, target=captured)
        total += size
        if hashed != row["archiveSha256"] or hashlib.sha512(captured.getvalue()).hexdigest() != row["archiveSha512"]:
            raise evidence.ConformanceError("InputChanged")
        try:
            with zipfile.ZipFile(captured) as packed:
                for member in members:
                    total += packed.getinfo(member).file_size
                    if total > evidence.MAX_PROOF_BYTES:
                        raise evidence.ConformanceError("OutputLimitExceeded")
        except (KeyError, zipfile.BadZipFile):
            raise evidence.ConformanceError("InputChanged") from None
        identity = {
            "packageId": name, "version": version, "sha256": row["archiveSha256"],
            "nugetSha512": row["archiveSha512"], "sourceMapping": "local"}
        policy.update(binding_package_file_policy(
            Path(package_root) / prefix, [identity],
            [{"packageId": name, "version": version, "cachePath": prefix, "members": sorted(members)}]))
        if time.monotonic() >= deadline:
            raise evidence.ConformanceError("DeadlineExceeded")
    if policy != observed:
        raise evidence.ConformanceError("InputChanged")
    return MappingProxyType(policy)


def binding_package_file_policy(feed, packages, selections):
    def archive_identity(value):
        if isinstance(value, (dict, MappingProxyType)) and "runtimeAssemblies" in value:
            return evidence.admit_entity("PackageIdentity", value)
        return evidence._record({
            "packageId": evidence.stable_id, "version": evidence.stable_id,
            "sha256": evidence.sha256, "nugetSha512": evidence._sha512,
            "sourceMapping": evidence._constant("local")})(value)

    packages = evidence._list(archive_identity, 1024, minimum=0)(packages)
    selected = evidence._record({
        "packageId": evidence.stable_id, "version": evidence.stable_id, "cachePath": evidence.relative_path,
        "members": evidence._list(evidence.relative_path, evidence.MAX_PROOF_FILES, unique=True)})
    selections = evidence._list(selected, 1024, minimum=0)(selections)
    indexed, owners = {}, set()
    for package in packages:
        key = (package["packageId"].casefold(), package["version"].casefold())
        if key in indexed:
            raise evidence.ConformanceError("BindingInvalid")
        indexed[key] = package
    result, total, deadline = {}, 0, time.monotonic() + 5
    for selection in selections:
        key = (selection["packageId"].casefold(), selection["version"].casefold())
        package = indexed.get(key)
        prefix = selection["cachePath"]
        if (package is None or len(prefix.split("/")) != 2 or prefix.split("/")[0].casefold() != key[0]
                or prefix.casefold() in owners):
            raise evidence.ConformanceError("BindingInvalid")
        owners.add(prefix.casefold())
        captured = io.BytesIO()
        filename = evidence.relative_path(f'{package["packageId"]}.{package["version"]}.nupkg')
        with evidence._input_root(feed) as (_, descriptor):
            hashed, size = evidence._source_file(
                descriptor, filename, remaining=min(evidence.MAX_PACKAGE_BYTES, evidence.MAX_PROOF_BYTES - total),
                deadline=deadline, target=captured)
        raw = captured.getvalue()
        total += size
        actual = (evidence.package_identity if "runtimeAssemblies" in package
                  else evidence.package_archive_identity)(feed, package["packageId"], package["version"])
        if (hashed != package["sha256"] or hashlib.sha512(raw).hexdigest() != package["nugetSha512"]
                or actual != package):
            raise evidence.ConformanceError("InputChanged")
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for member in selection["members"]:
                    if len(result) >= evidence.MAX_PROOF_FILES:
                        raise evidence.ConformanceError("OutputLimitExceeded")
                    try:
                        info = archive.getinfo(member)
                    except KeyError:
                        raise evidence.ConformanceError("InputChanged") from None
                    if info.is_dir():
                        raise evidence.ConformanceError("InputChanged")
                    digest, observed = hashlib.sha256(), 0
                    with archive.open(info) as source:
                        while block := source.read(64 * 1024):
                            observed += len(block)
                            total += len(block)
                            if observed > info.file_size or total > evidence.MAX_PROOF_BYTES:
                                raise evidence.ConformanceError("OutputLimitExceeded")
                            if time.monotonic() >= deadline:
                                raise evidence.ConformanceError("DeadlineExceeded")
                            digest.update(block)
                    if observed != info.file_size:
                        raise evidence.ConformanceError("InputChanged")
                    result[evidence.relative_path(prefix + "/" + member)] = digest.hexdigest()
        except (zipfile.BadZipFile, EOFError, RuntimeError, zlib.error):
            raise evidence.ConformanceError("InputChanged") from None
    if time.monotonic() >= deadline:
        raise evidence.ConformanceError("DeadlineExceeded")
    return MappingProxyType(result)


def binding_compiler_parameter_inputs(file_compilations, data):
    if not isinstance(data, bytes):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    if len(data) > 2 * 1024 * 1024:
        raise evidence.ConformanceError("OutputLimitExceeded")
    files = evidence._list(evidence._record({
        "project": evidence.relative_path, "succeeded": evidence._boolean,
        "inputs": _compiler_file_parameters}), 1024)(file_compilations)
    row = evidence._record({
        "project": evidence.relative_path, "commandLineSha256": evidence.sha256,
        "itemMetadata": _compiler_file_parameters})
    value = evidence._record({
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "compilations": evidence._list(row, 1024),
    })(evidence.load_json(data))
    expected = {}
    for compilation in files:
        project = compilation["project"]
        if (not compilation["succeeded"] or project in expected or not project.endswith(".csproj")
                or not compilation["inputs"]["Sources"] or not compilation["inputs"]["References"]):
            raise evidence.ConformanceError("EvidenceIncomplete")
        expected[project] = compilation["inputs"]
    seen = set()
    for compilation in value["compilations"]:
        project, metadata = compilation["project"], compilation["itemMetadata"]
        if (project not in expected or project in seen or set(metadata) != set(expected[project])
                or any(set(metadata[kind]) != set(items) for kind, items in expected[project].items())):
            raise evidence.ConformanceError("ProofMismatch")
        seen.add(project)
    if seen != set(expected):
        raise evidence.ConformanceError("ProofMismatch")
    return MappingProxyType({**value, "fileInputsSha256": evidence.digest(files)})
