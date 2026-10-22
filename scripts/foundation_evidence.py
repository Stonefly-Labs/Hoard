"""Prepare bounded local compilation evidence; never load or run providers."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from xml.sax.saxutils import escape


def run(*args, cwd=None, expected=None, env=None):
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False,
                            env=None if env is None else {**os.environ, **env}, timeout=600)
    if expected is not None:
        if result.returncode == 0 or expected not in result.stdout:
            raise RuntimeError(f"Expected diagnostic {expected}: {' '.join(args)}\n{result.stdout}")
    elif result.returncode:
        raise RuntimeError(f"Foundation command failed: {' '.join(args)}\n{result.stdout}")
    return result


def declarations(root, work):
    project = root / "src/Hoard.Abstractions/Hoard.Abstractions.csproj"
    run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet")
    assembly = root / "src/Hoard.Abstractions/bin/Release/net10.0/Hoard.Abstractions.dll"
    results = {}
    for name, error in [("Valid", None), ("Unsupported", None),
                        ("MissingRequired", "CS9035"), ("InitOnly", "CS8852"),
                        ("MutableCollection", "CS0029")]:
        target = work / "declarations" / name
        target.mkdir(parents=True)
        sources = [name] if name in ("Valid", "MissingRequired") else ["Valid", name]
        for source in sources:
            shutil.copy2(root / f"tests/fixtures/declarations/{source}.cs", target)
        (target / "Consumer.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework>'
            '<Nullable>enable</Nullable></PropertyGroup><ItemGroup>'
            f'<Reference Include="Hoard.Abstractions"><HintPath>{escape(str(assembly))}</HintPath></Reference>'
            '</ItemGroup></Project>\n')
        result = run("dotnet", "build", str(target / "Consumer.csproj"), "-v", "quiet", expected=error)
        results[name] = {"success": result.returncode == 0, "output": result.stdout}
    return results


def copy_source(source, target):
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("bin", "obj", "*.nupkg"))


def restore(project, config, update=False, source=None):
    run("dotnet", "restore", str(project), "--configfile", str(config),
        "--force-evaluate" if update else "--locked-mode", "-v", "quiet")
    if update:
        if source is not None:
            shutil.copy2(project.parent / "packages.lock.json", source / "packages.lock.json")
        # Replay in an empty cache so the initial restore is not its own proof.
        shutil.rmtree(project.parent / "obj")
        run("dotnet", "restore", str(project), "--configfile", str(config), "--locked-mode",
            "--packages", str(project.parent / ".replay-cache"), "-v", "quiet")


def build(project):
    run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet")
    return project.parent / f"bin/Release/net10.0/{project.stem}.dll"


def canonicalize_acceptance_archive(path):
    """Stabilize only the unsigned local SDK pack envelope, never package payloads."""
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    nuspecs = [name for name in entries if name.endswith(".nuspec")]
    if len(nuspecs) != 1 or ".signature.p7s" in entries:
        raise RuntimeError("Canonical packing requires an unsigned local Hoard acceptance archive.")
    package_id = next((node.text for node in ET.fromstring(entries[nuspecs[0]]).iter()
                       if node.tag.split("}")[-1] == "id"), "")
    if not package_id.startswith("Hoard."):
        raise RuntimeError("Canonical packing requires an unsigned local Hoard acceptance archive.")
    metadata = [name for name in entries
                if name.startswith("package/services/metadata/core-properties/") and name.endswith(".psmdcp")]
    if len(metadata) != 1 or "_rels/.rels" not in entries:
        raise RuntimeError("Missing or ambiguous SDK OPC envelope inputs.")
    old = metadata[0]
    stable = "package/services/metadata/core-properties/properties.psmdcp"
    entries[stable] = entries.pop(old)
    relationships = ET.fromstring(entries["_rels/.rels"])
    for relationship in relationships:
        target = relationship.attrib["Target"]
        if target.lstrip("/") == old:
            relationship.attrib["Target"] = ("/" if target.startswith("/") else "") + stable
        elif target.lstrip("/") != nuspecs[0]:
            raise RuntimeError("Unexpected SDK OPC relationship target.")
    relationships[:] = sorted(relationships, key=lambda item: (item.attrib["Type"], item.attrib["Target"]))
    for index, relationship in enumerate(relationships):
        relationship.attrib["Id"] = f"R{index}"
    entries["_rels/.rels"] = ET.tostring(relationships, encoding="utf-8", xml_declaration=True)
    temporary = path.with_suffix(".canonical.nupkg")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content, compresslevel=9)
    temporary.replace(path)


def packages(root, work, update):
    feed = work / "feed"
    feed.mkdir()
    config = work / "NuGet.Config"
    config.write_text(
        '<configuration><packageSources><clear />'
        f'<add key="local" value="{escape(str(feed))}" />'
        '<add key="nuget.org" value="https://api.nuget.org/v3/index.json" />'
        '</packageSources><packageSourceMapping><packageSource key="local">'
        '<package pattern="Hoard.*" /></packageSource><packageSource key="nuget.org">'
        '<package pattern="*" /></packageSource></packageSourceMapping></configuration>\n')
    os.environ["NUGET_PACKAGES"] = str(work / "cache")
    core = work / "core"
    for name in ("Hoard.Abstractions", "Hoard.Core"):
        copy_source(root / "src" / name, core / "src" / name)
    for name in ("global.json", "Directory.Build.props", "Directory.Packages.props"):
        shutil.copy2(root / name, core / name)
    core_project = core / "src/Hoard.Core/Hoard.Core.csproj"
    restore(core_project, config)
    core_assembly = build(core_project)
    core_proof = {"directory": str(core), "assembly": str(core_assembly),
                  "assets": str(core_project.parent / "obj/project.assets.json")}
    for name in ("Abstractions", "Core", "Hosting", "Application"):
        run("dotnet", "pack", str(root / f"src/Hoard.{name}/Hoard.{name}.csproj"),
            "-c", "Release", "--no-build", "--no-restore", "-o", str(feed), "-v", "quiet")
        canonicalize_acceptance_archive(feed / f"Hoard.{name}.0.1.0.nupkg")
    proofs = []
    for name in ("Protocol", "Metadata", "Artifact.One", "Artifact.Two", "Identity"):
        source = root / "tests/fixtures/providers" / name
        target = work / "providers" / name
        copy_source(source, target)
        project = next(target.glob("*.csproj"))
        restore(project, config, update, source)
        assembly = build(project)
        run("dotnet", "pack", str(project), "-c", "Release", "--no-build", "--no-restore",
            "-o", str(feed), "-v", "quiet")
        canonicalize_acceptance_archive(feed / f"{project.stem}.0.1.0.nupkg")
        family = name.split(".")[0]
        implementation = f"Artifact{name.split('.')[1]}Provider" if family == "Artifact" else f"{name}Provider"
        consumer = work / "consumers" / name
        consumer.mkdir(parents=True)
        (consumer / "Consumer.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework>'
            '<Nullable>enable</Nullable><RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>'
            '</PropertyGroup><ItemGroup>'
            f'<PackageReference Include="{project.stem}" Version="[0.1.0]" />'
            '</ItemGroup></Project>\n')
        (consumer / "Consumer.cs").write_text(
            f'public class Consumer {{ public Hoard.Abstractions.Providers.I{family}Provider '
            f'Create() => new Hoard.Fixtures.{name}.{implementation}(); }}\n')
        restore(consumer / "Consumer.csproj", config, update=True)
        consumer_assembly = build(consumer / "Consumer.csproj")
        proofs.append({"id": project.stem, "family": family, "directory": str(target),
                       "assembly": str(assembly), "consumerAssembly": str(consumer_assembly),
                       "consumerAssets": str(consumer / "obj/project.assets.json"),
                       "package": str(feed / f"{project.stem}.0.1.0.nupkg")})
    return core_proof, proofs, config


def inspection_graph(projects, ownership):
    pending = list(projects)
    result = {}
    while pending:
        project = pending.pop().resolve()
        if str(project) in result:
            continue
        resolved = json.loads(run(
            "dotnet", "msbuild", str(project), "-target:ResolveReferences", "-property:Configuration=Release",
            "-getItem:ReferencePath,Compile", "-verbosity:quiet").stdout)["Items"]
        result[str(project)] = {
            "id": project.stem, "project": str(project),
            "assembly": str(project.parent / f"bin/Release/net10.0/{project.stem}.dll"),
            "assets": str(project.parent / "obj/project.assets.json"),
            "references": resolved["ReferencePath"],
            "sources": [str((project.parent / p["Identity"]).resolve())
                        for p in resolved["Compile"] if "/obj/" not in p["FullPath"]]}
        for reference in ET.parse(project).findall(".//ProjectReference"):
            pending.append(project.parent / reference.attrib["Include"])
    return {"projects": list(result.values()), "ownership": ownership}


def architecture(root, work, config, update):
    source = root / "tests/fixtures/architecture"
    target = work / "architecture"
    copy_source(source, target)
    ownership = json.loads((source / "ownership.json").read_text())
    for name in ("Sdk", "Helper"):
        project = target / name / f"{name}.csproj"
        restore(project, config, update, source / name)
        build(project)
        run("dotnet", "pack", str(project), "-c", "Release", "--no-build", "--no-restore",
            "-o", str(work / "feed"), "-v", "quiet")
        canonicalize_acceptance_archive(work / "feed" / f"Hoard.Fixtures.Arch.{name}.0.1.0.nupkg")
    cases = {
        "permitted": "Permitted/Permitted",
        "identity-hosting": "Permitted/Identity/PermittedIdentity",
        "identity-direct-core": "ForbiddenIdentity/DirectCore/DirectIdentityCore",
        "identity-transitive-core": "ForbiddenIdentity/TransitiveCore/TransitiveIdentityCore",
        "abstractions-sdk": "ForbiddenAbstractions/ForbiddenAbstractions",
        "abstractions-http": "ForbiddenAbstractions/Http/ForbiddenHttp",
        "abstractions-unused-http": "ForbiddenAbstractions/UnusedHttp/UnusedHttp",
        "core-unused-http": "ForbiddenCore/UnusedHttp/UnusedCoreHttp",
        "core-unused": "ForbiddenCore/ForbiddenCore",
        "core-transitive": "TransitiveCore/TransitiveCore",
        "core-packed": "TransitiveCore/Packed/PackedCore",
        "leak-direct": "PublicTypeLeaks/Direct/DirectLeak",
        "leak-recursive": "PublicTypeLeaks/Recursive/RecursiveLeak",
        "bcl-query": "PublicTypeLeaks/BclQuery/BclQuery",
        "bcl-nested-query": "PublicTypeLeaks/BclNested/BclNested",
        "bcl-connection": "PublicTypeLeaks/BclConnection/BclConnection",
        "provider-unrelated": "ProviderCoupling/ProviderCoupling",
        "provider-same-family": "ProviderCoupling/SameFamily/SameFamily",
        "slice-private": "ApplicationInternals/ApplicationInternals",
        "slice-same-assembly": "CrossSlice/SameAssembly/CrossSlice",
        "slice-async": "CrossSlice/Async/AsyncSlice",
        "slice-external": "CrossSlice/External/One/ExternalSlice"
    }
    # Generate locks for every reachable project before replaying each root.
    for project in sorted(target.glob("**/*.csproj")):
        restore(project, config, update, source / project.parent.relative_to(target))
    graphs = {}
    for name, relative in cases.items():
        project = target / f"{relative}.csproj"
        build(project)
        graphs[name] = inspection_graph([project], ownership)
    return graphs, json.loads((source / "Cycles/graph.json").read_text())


def source_hashes(root):
    result = {}
    for base in ("src", "tests/fixtures/providers"):
        for path in sorted((root / base).rglob("*")):
            if path.suffix in (".cs", ".csproj", ".props") and not {"bin", "obj"}.intersection(path.parts):
                result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def hosts(root, work, config, update):
    source = root / "examples/CustomHost"
    proofs = []
    for name in ("One", "Two"):
        target = work / "hosts" / name
        copy_source(source, target)
        project = target / "CustomHost.csproj"
        if name == "Two":
            project.write_text(project.read_text().replace("Artifact.One", "Artifact.Two"))
            program = target / "Program.cs"
            program.write_text(program.read_text().replace("Artifact.One", "Artifact.Two")
                               .replace("ArtifactOneProvider", "ArtifactTwoProvider"))
        restore(project, config, update or name == "Two", source if name == "One" else None)
        if name == "Two":
            restore(project, config)
        proofs.append({"directory": str(target), "assembly": str(build(project)), "artifact": name})
    return proofs


def real_architecture(root, work, evidence):
    ownership = {
        "Hoard.Abstractions": "Abstractions", "Hoard.Core": "Core", "Hoard.Hosting": "Hosting",
        "Hoard.Application": "Application", "Microsoft.Extensions.DependencyInjection.Abstractions": "Di",
        "NuGet.Versioning": "Versioning",
        "Hoard.Fixtures.Protocol": "Protocol", "Hoard.Fixtures.Metadata": "Metadata",
        "Hoard.Fixtures.Artifact.One": "Artifact", "Hoard.Fixtures.Artifact.Two": "Artifact",
        "Hoard.Fixtures.Identity": "Identity", "CustomHost": "Host"
    }
    graphs = [inspection_graph([root / f"src/Hoard.{name}/Hoard.{name}.csproj"
                                for name in ("Abstractions", "Core", "Hosting", "Application")], ownership)]
    graphs[0]["scanId"] = "platform"
    for provider in evidence["providers"]:
        graph = inspection_graph(list(Path(provider["directory"]).glob("*.csproj")), ownership)
        graph["scanId"] = f"provider:{provider['id']}"
        graphs.append(graph)
    for host in evidence["hosts"]:
        graph = inspection_graph([Path(host["directory"]) / "CustomHost.csproj"], ownership)
        graph["scanId"] = f"host:{host['artifact']}"
        graphs.append(graph)
    return graphs


def breaking(root, work, config, update):
    source = root / "tests/fixtures/compatibility"
    target = work / "compatibility"
    copy_source(source, target)
    for project in sorted(target.glob("**/*.csproj")):
        restore(project, config, update, source / project.parent.relative_to(target))
    results = {}
    for name, contract, consumer in (("RequiredMember", "RequiredContract", "RequiredConsumer"),
                                     ("BinaryMemberRemoval", "BinaryContract", "BinaryConsumer")):
        base = target / name
        old = build(base / "Old" / f"{contract}.csproj")
        new = build(base / "New" / f"{contract}.csproj")
        project = base / "Consumer" / f"{consumer}.csproj"
        run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet",
            f"-p:ContractAssembly={old}")
        if name == "RequiredMember":
            result = run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet",
                         f"-p:ContractAssembly={new}", expected="CS0535")
            results["required"] = {"oldSuccess": True, "newSuccess": False, "output": result.stdout}
        else:
            output = project.parent / "bin/Release/net10.0"
            run("dotnet", str(output / f"{consumer}.dll"))
            shutil.copy2(new, output / "BinaryContract.dll")
            result = run("dotnet", str(output / f"{consumer}.dll"), expected="MissingMethodException")
            results["binary"] = {"oldSuccess": True, "newSuccess": False, "output": result.stdout}
            original = (project.parent / "Program.cs").read_text()
            (project.parent / "Program.cs").write_text('Console.WriteLine("Migrated consumer no longer calls the removed API.");\n')
            run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet",
                f"-p:ContractAssembly={new}")
            results["binary"]["migratedSourceSuccess"] = True
            (project.parent / "Program.cs").write_text(original)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("--phase", choices=["declarations", "packages", "architecture", "hosts", "all"], default="all")
    parser.add_argument("--update-locks", action="store_true")
    args = parser.parse_args()
    os.environ["NUGET_PACKAGES"] = str(args.work / "source-cache")
    run("dotnet", "restore", str(args.root / "Hoard.slnx"),
        "--force-evaluate" if args.update_locks else "--locked-mode",
        "--source", "https://api.nuget.org/v3/index.json", "-v", "quiet")
    run("dotnet", "build", str(args.root / "Hoard.slnx"), "-c", "Release", "--no-restore", "-v", "quiet")
    evidence = {"declarations": declarations(args.root, args.work)}
    if args.phase == "declarations":
        print("Declaration consumer proof passed (partial foundation check).")
        return
    evidence["core"], evidence["providers"], config = packages(args.root, args.work, args.update_locks)
    evidence["localFeed"] = str(args.work / "feed")
    manifest = args.work / "evidence.json"
    manifest.write_text(json.dumps(evidence, indent=2))
    os.environ["HOARD_FOUNDATION_EVIDENCE"] = str(manifest)
    if args.phase == "packages":
        run("dotnet", "test", str(args.root / "tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj"),
            "-c", "Release", "--no-build", "--no-restore", "--filter",
            "FullyQualifiedName~ProviderPackageTests|FullyQualifiedName~CoreIndependenceTests", "-v", "normal")
        print("Five provider packages/family consumers and isolated Core passed (partial foundation check).")
        return
    evidence["architecture"], evidence["cycles"] = architecture(args.root, args.work, config, args.update_locks)
    evidence["realArchitecture"] = []
    manifest.write_text(json.dumps(evidence, indent=2))
    if args.phase == "architecture":
        run("dotnet", "test", str(args.root / "tests/architecture/Hoard.Architecture.Tests/Hoard.Architecture.Tests.csproj"),
            "-c", "Release", "--no-build", "--no-restore", "--filter",
            "FullyQualifiedName!~Actual_platform_provider_packages_and_both_hosts&FullyQualifiedName!~Omitting_any_required_real_scan&FullyQualifiedName!~Prepared_lifecycle_graphs&FullyQualifiedName!~Prepared_configuration&FullyQualifiedName!~Prepared_discovery&FullyQualifiedName!~Prepared_metadata",
            "-v", "minimal")
        print("Isolated architecture rejection/permitted pairs passed (partial foundation check).")
        return
    evidence["sourceHashesBefore"] = source_hashes(args.root)
    evidence["hosts"] = hosts(args.root, args.work, config, args.update_locks)
    evidence["sourceHashesAfter"] = source_hashes(args.root)
    evidence["realArchitecture"] = real_architecture(args.root, args.work, evidence)
    manifest.write_text(json.dumps(evidence, indent=2))
    if args.phase == "hosts":
        for project in ("unit/Hoard.Foundation.Tests", "architecture/Hoard.Architecture.Tests",
                        "integration/Hoard.Composition.Tests"):
            selection = ["--filter", "FullyQualifiedName~ModuleRegistrationTests|FullyQualifiedName~DeclarationContractTests"] if project.startswith("unit/") else ["--filter", "FullyQualifiedName!~Prepared_lifecycle_graphs&FullyQualifiedName!~Prepared_configuration&FullyQualifiedName!~Prepared_discovery&FullyQualifiedName!~Prepared_metadata"]
            run("dotnet", "test", str(args.root / f"tests/{project}/{project.split('/')[-1]}.csproj"),
                "-c", "Release", "--no-build", "--no-restore", *selection, "-v", "minimal")
        print("Registration, package-only host swap and real boundary scans passed (partial foundation check).")
        return
    evidence["breaking"] = breaking(args.root, args.work, config, args.update_locks)
    manifest.write_text(json.dumps(evidence, indent=2))
    run("dotnet", "format", str(args.root / "Hoard.slnx"), "--verify-no-changes", "--no-restore", "-v", "quiet")
    for base in ("providers", "architecture", "hosts", "compatibility"):
        for project in sorted((args.work / base).glob("**/*.csproj")):
            environment = None
            if project.stem in ("RequiredConsumer", "BinaryConsumer"):
                contract = "RequiredContract" if project.stem == "RequiredConsumer" else "BinaryContract"
                environment = {"ContractAssembly": str(project.parent.parent / f"Old/bin/Release/net10.0/{contract}.dll")}
            run("dotnet", "format", str(project), "--verify-no-changes", "--no-restore", "-v", "quiet", env=environment)
    result = run("dotnet", "test", str(args.root / "Hoard.slnx"), "-c", "Release", "--no-build", "--no-restore",
                 "--filter", "FullyQualifiedName!~Prepared_lifecycle_graphs&FullyQualifiedName!~Prepared_configuration&FullyQualifiedName!~Prepared_discovery&FullyQualifiedName!~Prepared_metadata", "-v", "minimal")
    print(result.stdout)
    print("Foundation acceptance passed: isolated Core, five independent providers, both hosts, "
          "ARCH-001..008 rejection/permitted pairs, C-01..23, declaration and registration proofs. "
          "Compile-only; no operational provider or runtime support claim.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ET.ParseError, zipfile.BadZipFile) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
