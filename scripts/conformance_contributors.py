"""Explicit contributor inputs, typed factories and captured images, never qualification."""

from collections.abc import Mapping
from dataclasses import dataclass
import base64
import binascii
import hashlib
import io
import os
from pathlib import Path
import re
import time
from types import MappingProxyType
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


def build_binding_project(binding, owned_run, configuration, feed, *, local_packages=(), compile_action=None):
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
        if observed.exit_code or any(event["code"] != "None" for event in observed.events):
            raise evidence.ConformanceError("CommandFailed")
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
                                       sdk_version, runtime_version, package_root, package_inputs):
    from conformance_execution import no_symlinks
    from conformance_sdk_checks import read_bounded

    owned_run._check_ledger()
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
             "-p:UseSharedCompilation=false", "-p:CustomAfterDirectoryBuildProps=" + _msbuild_literal(properties),
             "-nodeReuse:false", "-maxCpuCount:1", "-noconsolelogger", "-nologo", "-verbosity:minimal", logger],
            cwd=tool.parent, kind="events", timeout=600, cache_id="binding-build",
            env={"DOTNET_ROLL_FORWARD": "Disable", "MSBUILDLOGTASKINPUTS": "1", "MSBUILDLOGIMPORTS": "1"})
        if observed.exit_code or any(event["code"] != "None" for event in observed.events):
            raise evidence.ConformanceError("CommandFailed")
        if tuple(observed.events) != ({"event": "control", "code": "None", "value": len(projects)},):
            raise evidence.ConformanceError("ProofMismatch")
        sources = binding_compilation_sources(
            binding, read_bounded(output_paths["sources"], 2 * 1024 * 1024), workspace)
        inputs = binding_build_file_inputs(
            binding, read_bounded(output_paths["inputs"], 2 * 1024 * 1024),
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
            if observed.exit_code or any(event["code"] != "None" for event in observed.events):
                raise evidence.ConformanceError("CommandFailed")
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
            if observed.exit_code or any(event["code"] != "None" for event in observed.events):
                raise evidence.ConformanceError("CommandFailed")
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
            or not isinstance(value["Items"], dict) or set(value["Items"]) != {"_BindingInputs"}):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
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
        "project": binding.project,
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
    if (not isinstance(assets, dict) or type(assets.get("version")) is not int or assets["version"] != 3
            or not isinstance(lock, dict) or type(lock.get("version")) is not int or lock["version"] not in (1, 2)
            or not isinstance(assets.get("targets"), dict) or set(assets["targets"]) != {"net10.0"}
            or not isinstance(lock.get("dependencies"), dict) or set(lock["dependencies"]) != {"net10.0"}
            or not isinstance(assets.get("libraries"), dict)
            or not isinstance(assets.get("project"), dict) or assets.get("logs")):
        raise evidence.ConformanceError("EvidenceIncomplete")
    restore = assets["project"].get("restore")
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


def binding_compilation_sources(binding, data, generated_root):
    if not isinstance(data, bytes):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    if len(data) > 2 * 1024 * 1024:
        raise evidence.ConformanceError("OutputLimitExceeded")
    compilation = evidence._record({
        "project": evidence.relative_path, "succeeded": evidence._boolean,
        "sources": evidence._hash_map})
    value = evidence._record({
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "succeeded": evidence._boolean,
        "compilations": evidence._list(compilation, 1024),
    })(evidence.load_json(data))
    generated_root = Path(generated_root).absolute()
    if (generated_root.is_relative_to(binding.root) or binding.root.is_relative_to(generated_root)):
        raise evidence.ConformanceError("OwnershipInvalid")
    projects, generated = set(), {}
    source_inputs = 0
    for row in value["compilations"]:
        project = row["project"]
        if (not row["succeeded"] or project in projects or project not in binding.sources
                or not project.endswith(".csproj")):
            raise evidence.ConformanceError("EvidenceIncomplete")
        projects.add(project)
        source_inputs += len(row["sources"])
        if source_inputs > evidence.MAX_PROOF_FILES:
            raise evidence.ConformanceError("OutputLimitExceeded")
        for path, hashed in row["sources"].items():
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
    compilation = evidence._record({
        "project": evidence.relative_path, "succeeded": evidence._boolean,
        "sources": evidence._hash_map})(compilation)
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
            or any(compilation["sources"].get(path) != hashed for path, hashed in value["documents"].items())):
        raise evidence.ConformanceError("ProofMismatch")
    outputs = {value[kind]["path"]: value[kind]["sha256"] for kind in ("assembly", "pdb")}
    if evidence.input_manifest(output_root, sorted(outputs)) != outputs:
        raise evidence.ConformanceError("InputChanged")
    return MappingProxyType({**value, "compilerSourcesSha256": evidence.digest(compilation["sources"])})


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


def binding_build_file_inputs(binding, data, generated_root, toolchain_root, package_root, package_inputs):
    if not isinstance(data, bytes):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    if len(data) > 2 * 1024 * 1024:
        raise evidence.ConformanceError("OutputLimitExceeded")
    row = evidence._record({
        "project": evidence.relative_path, "succeeded": evidence._boolean, "inputs": _compiler_file_parameters})
    errors = evidence._list(evidence.stable_id, 1024, minimum=0, unique=True)
    value = evidence._record({
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "succeeded": evidence._boolean, "compilations": evidence._list(row, 1024),
        "imports": evidence._hash_map, "diagnosticCodes": errors, "observerErrors": errors,
    })(evidence.load_json(data))
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
