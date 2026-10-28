"""Explicit contributor registration/staging and typed source, never qualification."""

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import io
from pathlib import Path
import re
import time
from types import MappingProxyType

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
    declaration = registration["declaration"]
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
    return (
        "namespace Hoard.Fixtures.Conformance.Consumer;\n\n"
        "internal static class ContributorBindingFactory\n"
        "{\n"
        f"    internal static global::Hoard.Testing.Conformance.Bindings.{interface} Create() =>\n"
        f'        new global::{factory}("{provider["sha256"]}");\n'
        "}\n"
    ).encode("ascii")
