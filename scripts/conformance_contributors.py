"""Explicit contributor inputs, typed factories and captured images, never qualification."""

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import io
from pathlib import Path
import re
import time
from types import MappingProxyType
import zipfile
import zlib

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
    return (
        "namespace Hoard.Fixtures.Conformance.Consumer;\n\n"
        "internal static class ContributorBindingFactory\n"
        "{\n"
        f"    internal static {bindings}.{interface} Create()\n"
        "    {\n"
        f'        {bindings}.{interface} binding = new global::{factory}("{provider["sha256"]}");\n'
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
        "Identity", "Kind", "FullPath", "RootDir", "Filename", "Extension", "RelativeDir",
        "Directory", "RecursiveDir", "ModifiedTime", "CreatedTime", "AccessedTime",
        "DefiningProjectFullPath", "DefiningProjectDirectory", "DefiningProjectName", "DefiningProjectExtension"}
    paths = {"source": set(), "toolchain": set()}
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
    if (binding.project not in paths["source"] or not paths["toolchain"]
            or not paths["source"].issubset(binding.sources)):
        raise evidence.ConformanceError("EvidenceIncomplete")
    sources = evidence.input_manifest(binding.root, sorted(binding.sources))
    if sources != binding.sources:
        raise evidence.ConformanceError("InputChanged")
    toolchain = evidence.input_manifest(toolchain_root, sorted(paths["toolchain"]))
    return MappingProxyType({
        "schemaVersion": 1, "qualification": False, "bindingInputsSha256": binding.inputs_sha256,
        "project": binding.project,
        "sources": MappingProxyType({path: sources[path] for path in sorted(paths["source"])}),
        "toolchain": toolchain})


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


def binding_build_file_inputs(binding, data, generated_root, toolchain_root, package_root, package_inputs):
    if not isinstance(data, bytes):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    if len(data) > 2 * 1024 * 1024:
        raise evidence.ConformanceError("OutputLimitExceeded")
    kinds = {
        "Sources", "References", "Analyzers", "AdditionalFiles", "AnalyzerConfigFiles",
        "EmbeddedFiles", "Resources", "LinkResources", "ResponseFiles", "Win32Resource",
        "Win32Manifest", "ApplicationConfiguration", "KeyFile", "SourceLink"}

    def parameters(value):
        if (not isinstance(value, (dict, MappingProxyType)) or not {"Sources", "References"} <= value.keys()
                or not value.keys() <= kinds):
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        return MappingProxyType({
            kind: evidence._record({})(items) if items == {} else evidence._hash_map(items)
            for kind, items in value.items()})

    row = evidence._record({
        "project": evidence.relative_path, "succeeded": evidence._boolean, "inputs": parameters})
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
    packages = evidence._list(evidence._entity("PackageIdentity"), 1024, minimum=0)(packages)
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
        if (hashed != package["sha256"] or hashlib.sha512(raw).hexdigest() != package["nugetSha512"]
                or evidence.package_identity(feed, package["packageId"], package["version"]) != package):
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
