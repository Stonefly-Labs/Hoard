"""Bounded, isolated fixture-only lifecycle acceptance."""

import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import tarfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import foundation_evidence as foundation


_workspaces = set()


def create_workspace(parent=None):
    path = Path(tempfile.mkdtemp(prefix="hoard-lifecycle-", dir=parent)).resolve()
    _workspaces.add(path)
    return path


def cleanup_workspace(path):
    path = Path(path)
    if path != path.resolve() or path not in _workspaces:
        raise RuntimeError("Refusing cleanup outside owned lifecycle workspace.")
    shutil.rmtree(path)
    _workspaces.remove(path)


def run(*args, cwd=None, env=None):
    try:
        result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=False, timeout=600,
                                env={**os.environ, **(env or {})})
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Lifecycle command timed out: {Path(args[0]).name}") from None
    if result.returncode:
        context = ""
        if Path(args[0]).name == "dotnet":
            context = f" {args[1]}"
            failures = re.findall(r"(?:error (?:CS|NU|MSB)\d+|error WHITESPACE|\bFailed [A-Za-z0-9._]+)", result.stdout)
            if failures:
                context += " [" + ", ".join(failures[:10]) + "]"
        raise RuntimeError(f"Lifecycle command failed: {Path(args[0]).name}{context}")
    return result.stdout


def require_file(path):
    if not path.is_file():
        raise RuntimeError("Missing lifecycle evidence input.")
    return path


def test_count(path):
    root = ET.parse(require_file(path)).getroot()
    counters = next((node for node in root.iter() if node.tag.split("}")[-1] == "Counters"), None)
    if counters is None:
        raise RuntimeError("Missing test counters.")
    total = int(counters.get("total", "0"))
    if total <= 0 or int(counters.get("passed", "0")) != total:
        raise RuntimeError("Empty, failed, or skipped lifecycle proof.")
    return total


def journey_count(text):
    journeys = json.loads(text).get("journeys", [])
    if not journeys or any(not entry.get("passed") or entry.get("events", 0) <= 0 for entry in journeys):
        raise RuntimeError("Missing or failed lifecycle journey.")
    return len(journeys)


def verify_package(package, feed, digest):
    if package.resolve().parent != feed.resolve() or not package.is_file() or \
            hashlib.sha512(package.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Invalid local package provenance.")


def lock_hashes(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("packages.lock.json") if "obj" not in path.parts and "bin" not in path.parts}


def verify_locks(root, before):
    if lock_hashes(root) != before:
        raise RuntimeError("Default lifecycle acceptance mutated tracked lock inputs.")


def focused_tests(root, work, selection):
    if not selection.strip():
        raise RuntimeError("Empty lifecycle test selection.")
    project = root / "tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj"
    run("dotnet", "restore", str(project), "--locked-mode", "-v", "quiet")
    run("dotnet", "test", str(project), "-c", "Release", "--no-restore",
        "--filter", selection, "--logger", "trx;LogFileName=lifecycle.trx",
        "--results-directory", str(work / "results"), "-v", "minimal")
    return test_count(work / "results/lifecycle.trx")


def prepare_packages(root, work, update):
    feed = work / "feed"
    feed.mkdir()
    config = work / "NuGet.Config"
    config.write_text(
        '<configuration><packageSources><clear/>'
        f'<add key="local" value="{escape(str(feed))}"/>'
        '<add key="nuget.org" value="https://api.nuget.org/v3/index.json"/>'
        '</packageSources><packageSourceMapping><packageSource key="local">'
        '<package pattern="Hoard.*"/></packageSource><packageSource key="nuget.org">'
        '<package pattern="*"/></packageSource></packageSourceMapping></configuration>')
    run("dotnet", "restore", str(root / "Hoard.slnx"), "--locked-mode", "-v", "quiet")
    run("dotnet", "build", str(root / "Hoard.slnx"), "-c", "Release", "--no-restore", "-v", "quiet")
    proofs = []
    for name in ("Abstractions", "Core", "Hosting", "Application"):
        run("dotnet", "pack", str(root / f"src/Hoard.{name}/Hoard.{name}.csproj"),
            "-c", "Release", "--no-build", "--no-restore", "-o", str(feed), "-v", "quiet")
        foundation.canonicalize_acceptance_archive(feed / f"Hoard.{name}.0.1.0.nupkg")
    os.environ["NUGET_PACKAGES"] = str(work / "cache")
    for name in ("Protocol.One", "Protocol.Two", "Metadata", "Artifact.One", "Artifact.Two", "Identity"):
        source = root / "tests/fixtures/lifecycle" / name
        target = work / "fixtures" / name
        foundation.copy_source(source, target)
        project = next(target.glob("*.csproj"))
        references = ET.parse(project).findall(".//PackageReference")
        allowed = {"Hoard.Hosting"} if name.startswith("Protocol") or name == "Identity" else {"Hoard.Abstractions"}
        if {node.get("Include") for node in references} != allowed or ET.parse(project).findall(".//ProjectReference"):
            raise RuntimeError("Invalid independent fixture dependency graph.")
        foundation.restore(project, config, update, source)
        assembly = foundation.build(project)
        run("dotnet", "pack", str(project), "-c", "Release", "--no-build", "--no-restore",
            "-o", str(feed), "-v", "quiet")
        package = feed / f"{project.stem}.0.1.0.nupkg"
        foundation.canonicalize_acceptance_archive(package)
        digest = hashlib.sha512(package.read_bytes()).hexdigest()
        verify_package(package, feed, digest)
        assets = json.loads((project.parent / "obj/project.assets.json").read_text())
        for identity, details in assets["libraries"].items():
            if identity.startswith("Hoard."):
                local = feed / f"{identity.split('/')[0]}.{identity.split('/')[1]}.nupkg"
                require_file(local)
                if details["sha512"] != base64.b64encode(hashlib.sha512(local.read_bytes()).digest()).decode():
                    raise RuntimeError("Stale local package provenance.")
        proofs.append({"id": project.stem, "project": str(project), "assembly": str(assembly),
                       "assets": str(project.parent / "obj/project.assets.json"), "package": str(package),
                       "sha512": digest, "sourceHashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                                        for p in source.glob("*.cs")}})
    (work / "packages.json").write_text(json.dumps(proofs, indent=2))
    return config, proofs


def host_journeys(root, work, config, update):
    source = root / "examples/LifecycleHost"
    projects = []
    total = 0
    before = foundation.source_hashes(root)
    for variant, relative in (("baseline", "LifecycleHost.csproj"), ("custom", "Custom/LifecycleHost.Custom.csproj")):
        target = work / "hosts" / variant
        foundation.copy_source(source, target)
        project = target / relative
        foundation.restore(project, config, update, source / Path(relative).parent)
        assembly = foundation.build(project)
        digest = hashlib.sha256(assembly.read_bytes()).hexdigest()
        output = run("dotnet", str(assembly), cwd=target)
        count = journey_count(output)
        if count != (3 if variant == "baseline" else 4):
            raise RuntimeError("Missing lifecycle distribution journey.")
        assets = json.loads((project.parent / "obj/project.assets.json").read_text())
        if variant == "baseline" and any(identity.startswith("Hoard.Fixtures.Lifecycle.Artifact.Two/") for identity in assets["libraries"]):
            raise RuntimeError("Custom artifact unexpectedly included in baseline.")
        if hashlib.sha256(assembly.read_bytes()).hexdigest() != digest:
            raise RuntimeError("Bundled journey rebuilt its host.")
        total += count
        projects.append(project)
    if foundation.source_hashes(root) != before:
        raise RuntimeError("Distribution journey modified platform or unrelated provider sources.")
    return total, projects


def prepare_registration_baseline(root, work, config, update, baseline_directory="baseline"):
    os.environ["NUGET_PACKAGES"] = str(work / "old-platform-cache")
    baseline = work / baseline_directory
    baseline.mkdir()
    commit = "837fdf3edf51c3df34710184d018479683c194c2"
    run("git", "merge-base", "--is-ancestor", commit, "origin/main", cwd=root)
    archive = work / f"{baseline_directory}.tar"
    run("git", "archive", "--format=tar", f"--output={archive}", commit,
        "Directory.Build.props", "Directory.Packages.props", "global.json", "src", cwd=root)
    with tarfile.open(archive) as contents:
        contents.extractall(baseline, filter="data")
    old_feed = work / "old-feed"
    old_feed.mkdir()
    for name in ("Abstractions", "Core", "Hosting"):
        project = baseline / f"src/Hoard.{name}/Hoard.{name}.csproj"
        foundation.restore(project, config)
        foundation.build(project)
        run("dotnet", "pack", str(project), "-c", "Release", "--no-build", "--no-restore",
            "-o", str(old_feed), "-v", "quiet")
        foundation.canonicalize_acceptance_archive(old_feed / f"Hoard.{name}.0.1.0.nupkg")
    old_config = work / "Old.NuGet.Config"
    old_config.write_text(config.read_text().replace(str(work / "feed"), str(old_feed)))
    source = root / "tests/fixtures/lifecycle/registration/RegistrationConsumer"
    old_source = work / "registration-old"
    foundation.copy_source(source, old_source)
    old_project = old_source / "RegistrationConsumer.csproj"
    old_lock_source = source / "Baseline"
    if not update:
        shutil.copy2(require_file(old_lock_source / "packages.lock.json"), old_source / "packages.lock.json")
    os.environ["NUGET_PACKAGES"] = str(work / "old-cache")
    foundation.restore(old_project, old_config, update, old_lock_source if update else None)
    old_binary = foundation.build(old_project)
    digest = hashlib.sha256(old_binary.read_bytes()).hexdigest()
    if run("dotnet", str(old_binary)).strip() != "registration-compatible":
        raise RuntimeError("Baseline registration consumer did not run.")
    os.environ["NUGET_PACKAGES"] = str(work / "cache")
    return {"assembly": str(old_binary), "sha256": digest}


def registration_compatibility(root, work, config, update, baseline_directory="baseline", *, prepared=None):
    if prepared is None:
        retained = prepare_registration_baseline(root, work, config, update, baseline_directory)
        old_binary = Path(retained["assembly"])
    else:
        if (not isinstance(prepared, dict) or set(prepared) != {"assembly", "sha256"}
                or not isinstance(prepared["assembly"], str) or not isinstance(prepared["sha256"], str)
                or hashlib.sha256(Path(prepared["assembly"]).read_bytes()).hexdigest() != prepared["sha256"]):
            raise RuntimeError("Retained registration baseline changed.")
        retained = prepared
        replay = work / "registration-old"
        foundation.copy_source(Path(prepared["assembly"]).parent, replay)
        old_binary = replay / Path(prepared["assembly"]).name
    digest = retained["sha256"]
    source = root / "tests/fixtures/lifecycle/registration/RegistrationConsumer"
    os.environ["NUGET_PACKAGES"] = str(work / "new-registration-cache")
    target = work / "registration-new"
    foundation.copy_source(source, target)
    project = target / "RegistrationConsumer.csproj"
    foundation.restore(project, config, update, source)
    new_binary = foundation.build(project)
    if run("dotnet", str(new_binary)).strip() != "registration-compatible":
        raise RuntimeError("New source registration consumer did not run.")
    runtime = json.loads(new_binary.with_suffix(".runtimeconfig.json").read_text())
    frameworks = runtime["runtimeOptions"].get("frameworks", [])
    if not any(framework["name"] == "Microsoft.AspNetCore.App" for framework in frameworks):
        raise RuntimeError("Packed non-web shared-framework propagation missing.")
    for path in new_binary.parent.iterdir():
        if path.is_file() and path.name not in ("RegistrationConsumer.dll", "RegistrationConsumer.pdb"):
            shutil.copy2(path, old_binary.parent / path.name)
    if hashlib.sha256(old_binary.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Old registration binary was recompiled or overwritten.")
    if run("dotnet", str(old_binary)).strip() != "registration-compatible":
        raise RuntimeError("Retained old binary failed against new runtime.")
    os.environ["NUGET_PACKAGES"] = str(work / "cache")
    return project


def prepare_lifecycle_graphs(root, work, proofs, hosts, registration):
    ownership = {
        "Hoard.Abstractions": "Abstractions", "Hoard.Core": "Core", "Hoard.Hosting": "Hosting",
        "Hoard.Application": "Application", "NuGet.Versioning": "Versioning",
        "Microsoft.Extensions.DependencyInjection.Abstractions": "Di",
        "Microsoft.AspNetCore.TestHost": "Sdk", "LifecycleHost": "Host",
        "LifecycleHost.Custom": "Host", "RegistrationConsumer": "Host"
    }
    for proof in proofs:
        family = proof["id"].removeprefix("Hoard.Fixtures.Lifecycle.").split(".")[0]
        ownership[proof["id"]] = family
    graphs = []
    projects = [("platform", [root / f"src/Hoard.{name}/Hoard.{name}.csproj"
                             for name in ("Abstractions", "Core", "Hosting", "Application")])]
    projects += [(proof["id"].removeprefix("Hoard.Fixtures.Lifecycle."), [Path(proof["project"])]) for proof in proofs]
    projects += [(name, [project]) for name, project in zip(("baseline", "custom"), hosts)]
    projects += [("registration", [registration])]
    for name, inputs in projects:
        graph = foundation.inspection_graph(inputs, ownership)
        graph["scanId"] = name
        graphs.append(graph)
    manifest = work / "lifecycle-evidence.json"
    manifest.write_text(json.dumps({"graphs": graphs}, indent=2))
    os.environ["HOARD_LIFECYCLE_EVIDENCE"] = str(manifest)
    return graphs


def lifecycle_graphs(root, work, proofs, hosts, registration):
    prepare_lifecycle_graphs(root, work, proofs, hosts, registration)
    architecture = root / "tests/architecture/Hoard.Architecture.Tests/Hoard.Architecture.Tests.csproj"
    run("dotnet", "test", str(architecture), "-c", "Release", "--no-build", "--no-restore",
        "--filter", "FullyQualifiedName~LifecycleBoundaryTests", "--logger", "trx;LogFileName=architecture.trx",
        "--results-directory", str(work / "results"), "-v", "minimal")
    return test_count(work / "results/architecture.trx")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--update-locks", action="store_true")
    parser.add_argument("--filter")
    parser.add_argument("--packages-only", action="store_true")
    parser.add_argument("--journeys-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    before = lock_hashes(root)
    work = create_workspace()
    try:
        if args.journeys_only:
            config, _ = prepare_packages(root, work, args.update_locks)
            (root / "tests/fixtures/lifecycle/registration/RegistrationConsumer/Baseline").mkdir(exist_ok=True)
            registration_compatibility(root, work, config, args.update_locks)
            count, _ = host_journeys(root, work, config, args.update_locks)
            print(f"Partial distribution proof: {count} journeys and old-binary/new-source/framework compatibility passed.")
        elif args.packages_only:
            _, proofs = prepare_packages(root, work, args.update_locks)
            print(f"Partial lifecycle package proof: {len(proofs)} independent fixtures; not full acceptance.")
        elif args.filter is not None:
            count = focused_tests(root, work, args.filter)
            print(f"Partial lifecycle proof: {count} tests passed; not full LC-01..40 acceptance.")
        else:
            config, proofs = prepare_packages(root, work, args.update_locks)
            (root / "tests/fixtures/lifecycle/registration/RegistrationConsumer/Baseline").mkdir(exist_ok=True)
            registration = registration_compatibility(root, work, config, args.update_locks)
            journeys, hosts = host_journeys(root, work, config, args.update_locks)
            # Source assets belong to the repository cache; copied consumers use isolated caches.
            os.environ.pop("NUGET_PACKAGES", None)
            for project in [root / "Hoard.slnx", *(Path(proof["project"]) for proof in proofs), *hosts, registration]:
                run("dotnet", "format", str(project), "--verify-no-changes", "--no-restore", "-v", "quiet")
            architecture = lifecycle_graphs(root, work, proofs, hosts, registration)
            count = focused_tests(root, work,
                "FullyQualifiedName!~ProviderPackageTests&FullyQualifiedName!~CoreIndependenceTests&FullyQualifiedName!~CustomHostTests&FullyQualifiedName!~Prepared_configuration&FullyQualifiedName!~Prepared_discovery&FullyQualifiedName!~Prepared_metadata&FullyQualifiedName!~Prepared_artifact")
            print(f"Lifecycle acceptance: {count} tests, {architecture} boundary proofs, {journeys} package-only journeys passed; six independent packages and retained old binary verified.")
        if not args.update_locks:
            verify_locks(root, before)
    finally:
        cleanup_workspace(work)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, ET.ParseError) as error:
        raise SystemExit(str(error)) from None
