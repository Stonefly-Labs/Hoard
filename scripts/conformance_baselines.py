"""Prepare immutable historical sources/binaries before F-07 candidate builds.

Preparation never qualifies providers. Every build uses a private, revision-local
feed/cache and the historical locks; candidate execution may only verify/reuse
the resulting sealed bytes.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tarfile
from xml.sax.saxutils import escape

from foundation_evidence import canonicalize_acceptance_archive
from conformance_evidence import MAX_REPORT_BYTES, ConformanceError, canonical_bytes, digest, file_sha256, load_json, relative_path, sha256
from conformance_execution import OwnedRun, capture_control, no_symlinks


BASELINE = "9389016c0285c79f6f515f59805a5a41c69b0767"
BASELINES = (
    ("registration", "837fdf3edf51c3df34710184d018479683c194c2",
     "tests/fixtures/lifecycle/registration/RegistrationConsumer", "RegistrationConsumer.csproj"),
    ("lifecycle", "b80c69fc386541be4f56f6ef2edeca40f43a0e1c",
     "tests/fixtures/configuration/LifecycleConsumer", "LifecycleConsumer.csproj"),
    ("configuration", "7fd73267a5154583363c94e9e85b9bac7d4a16b3",
     "tests/fixtures/discovery/RetainedConfiguration", "RetainedConfiguration.csproj"),
    ("metadata-marker", "10ce78851b97b02bd83a8ef7da7ffdc2381d6519",
     "tests/fixtures/metadata/RetainedMarker", "RetainedMarker.csproj"),
    ("artifact-marker", "830972f24795ffaaaa18cb35138db7da59022313",
     "tests/fixtures/artifacts/RetainedMarker", "RetainedMarker.csproj"),
)


def _command(run, args, *, cwd, cache_id):
    observed = run.command(args, cwd=cwd, kind="build", cache_id=cache_id)
    if observed.exit_code or any(event["code"] != "None" for event in observed.events):
        codes = sorted({event["value"] for event in observed.events if event["code"] == "CommandFailed"})
        print(json.dumps({"code": "CommandFailed", "compilerCodes": codes}), file=sys.stderr)
        raise ConformanceError("CommandFailed")


def export_revision(repository, run, revision, name):
    code, _ = capture_control(
        ["git", "merge-base", "--is-ancestor", revision, "origin/main"], cwd=repository)
    if code:
        raise ConformanceError("InputChanged")
    destination = run.root / "stores" / name
    destination.mkdir(mode=0o700)
    archive = run.root / "stores" / f"{name}.tar"
    code, _ = capture_control(
        ["git", "archive", "--format=tar", f"--output={archive}", revision,
         "Directory.Build.props", "Directory.Packages.props", "global.json", "src", "tests", "specs"],
        cwd=repository)
    if code:
        raise ConformanceError("InputChanged")
    if archive.stat().st_size > 256 * 1024 * 1024:
        raise ConformanceError("InputChanged")
    with tarfile.open(archive) as source:
        members = source.getmembers()
        if (len(members) > 50_000 or sum(member.size for member in members) > 256 * 1024 * 1024
                or any(not (member.isfile() or member.isdir()) for member in members)):
            raise ConformanceError("InputChanged")
        source.extractall(destination, filter="data")
    return destination


def _hash_tree(root, *, exclude_outputs=False):
    return {
        path.relative_to(root).as_posix(): file_sha256(path)
        for path in sorted(root.rglob("*")) if path.is_file()
        and (not exclude_outputs or not {"bin", "obj"}.intersection(path.relative_to(root).parts))
    }


def _config(run, name):
    feed = run.root / "feed" / name
    feed.mkdir(mode=0o700)
    config = run.root / "stores" / f"{name}.NuGet.Config"
    config.write_text(
        '<configuration><packageSources><clear/>'
        f'<add key="local" value="{escape(str(feed))}"/>'
        '<add key="nuget.org" value="https://api.nuget.org/v3/index.json"/>'
        '</packageSources><packageSourceMapping><packageSource key="local">'
        '<package pattern="Hoard.*"/></packageSource><packageSource key="nuget.org">'
        '<package pattern="*"/></packageSource></packageSourceMapping></configuration>')
    return config, feed


def _build(run, project, config, name, *, pack=False, feed=None):
    _command(run, ["dotnet", "restore", str(project), "--locked-mode",
                   "--configfile", str(config), "-p:UseSharedCompilation=false", "-nodeReuse:false",
                   "-v", "quiet"], cwd=project.parent, cache_id=name)
    _command(run, ["dotnet", "build", str(project), "-c", "Release",
                   "--no-restore", "-p:UseSharedCompilation=false", "-nodeReuse:false",
                   "-v", "quiet"], cwd=project.parent, cache_id=name)
    if pack:
        _command(run, ["dotnet", "pack", str(project), "-c", "Release", "--no-build",
                       "--no-restore", "-p:UseSharedCompilation=false", "-nodeReuse:false",
                       "-o", str(feed), "-v", "quiet"], cwd=project.parent, cache_id=name)
        for package in feed.glob("*.nupkg"):
            canonicalize_acceptance_archive(package)


def prepare(repository, run):
    frozen = export_revision(repository, run, BASELINE, "f06")
    specs = (*BASELINES, ("f06", BASELINE, None, None))
    entries = []
    for name, revision, recipe, project_file in specs:
        source = frozen if name == "f06" else export_revision(repository, run, revision, name)
        source_hashes = _hash_tree(source, exclude_outputs=True)
        config, feed = _config(run, name)
        for package in ("Abstractions", "Core", "Hosting", "Application"):
            project = source / f"src/Hoard.{package}/Hoard.{package}.csproj"
            if project.is_file():
                _build(run, project, config, name, pack=True, feed=feed)
        if name == "f06":
            metadata_projects = (
                "metadata/Sqlite/Sqlite.csproj", "metadata/Memory/Memory.csproj",
                "metadata/HostAdapters/HostAdapters.csproj",
            )
            for relative in metadata_projects:
                _build(run, source / "tests/fixtures" / relative, config, name, pack=True, feed=feed)
            _build(run, source / "tests/fixtures/metadata/Consumer/Consumer.csproj", config, name)
            # F-06's artifact recipe deliberately consumes pre-F-06 metadata
            # binaries, not same-version recompilations against new abstractions.
            artifact_config, artifact_feed = _config(run, "f06-artifacts")
            for package in ("Abstractions", "Core", "Hosting", "Application"):
                filename = f"Hoard.{package}.0.1.0.nupkg"
                shutil.copy2(feed / filename, artifact_feed / filename)
            for package in ("Sqlite", "Memory", "HostAdapters"):
                filename = f"Hoard.Fixtures.Metadata.{package}.0.1.0.nupkg"
                shutil.copy2(run.root / "feed/artifact-marker" / filename, artifact_feed / filename)
            artifact_projects = (
                "artifacts/Local/Local.csproj", "artifacts/ObjectSemantics/ObjectSemantics.csproj",
                "artifacts/HostAdapters/HostAdapters.csproj",
            )
            for relative in artifact_projects:
                _build(run, source / "tests/fixtures" / relative, artifact_config, "f06-artifacts",
                       pack=True, feed=artifact_feed)
            _build(run, source / "tests/fixtures/artifacts/Consumer/Consumer.csproj",
                   artifact_config, "f06-artifacts")
            recipes = {relative: file_sha256(source / "tests/fixtures" / relative)
                       for relative in (*metadata_projects, *artifact_projects, "metadata/Consumer/Consumer.csproj",
                                        "artifacts/Consumer/Consumer.csproj")}
        else:
            if name == "artifact-marker":
                for relative in ("metadata/Sqlite/Sqlite.csproj", "metadata/Memory/Memory.csproj",
                                 "metadata/HostAdapters/HostAdapters.csproj"):
                    _build(run, source / "tests/fixtures" / relative, config, name, pack=True, feed=feed)
            target = source / "retained"
            shutil.copytree(frozen / recipe, target, ignore=shutil.ignore_patterns("bin", "obj"))
            baseline_lock = target / "Baseline/packages.lock.json"
            if baseline_lock.is_file():
                shutil.copy2(baseline_lock, target / "packages.lock.json")
            versions = source / "retained/Directory.Packages.props"
            versions.write_text(
                '<Project><PropertyGroup><ManagePackageVersionsCentrally>false</ManagePackageVersionsCentrally>'
                '</PropertyGroup></Project>')
            recipes = _hash_tree(target, exclude_outputs=True)
            _build(run, target / project_file, config, name)
        binaries = {
            path.relative_to(source).as_posix(): file_sha256(path)
            for path in sorted(source.rglob("*")) if path.is_file()
            and "bin" in path.relative_to(source).parts
            and path.suffix in (".dll", ".json", ".so", ".dylib")
        }
        if not binaries:
            raise ConformanceError("EvidenceIncomplete")
        if any(file_sha256(source / path) != expected for path, expected in source_hashes.items()):
            raise ConformanceError("InputChanged")
        locks = {path: value for path, value in source_hashes.items() if path.endswith("packages.lock.json")}
        package_hashes = {
            path.name: {"sha256": file_sha256(path), "sha512": hashlib.sha512(path.read_bytes()).hexdigest()}
            for path in sorted(feed.glob("*.nupkg"))
        }
        if name == "f06":
            package_hashes.update({
                "artifacts/" + path.name: {
                    "sha256": file_sha256(path), "sha512": hashlib.sha512(path.read_bytes()).hexdigest()}
                for path in sorted(artifact_feed.glob("*.nupkg"))
            })
        entries.append({
            "id": name, "revision": revision, "sourceSha256": digest(source_hashes),
            "sources": source_hashes, "recipeSha256": digest(recipes), "recipes": recipes,
            "lockSha256": digest(locks), "locks": locks, "binaries": binaries, "packages": package_hashes,
        })
    evidence = {"schemaVersion": 1, "qualification": False, "mode": "preparation",
                "baselineRevision": BASELINE, "entries": entries}
    sealed = run.root / "proofs" / "baselines.json"
    with sealed.open("xb") as destination:
        destination.write(canonical_bytes(evidence) + b"\n")
    sealed.chmod(0o400)
    return sealed


def verify_prepared_baselines(root, expected_sha256):
    root = Path(root).absolute()
    no_symlinks(root)
    if (not root.is_dir() or root.stat().st_uid != os.getuid()
            or stat.S_IMODE(root.stat().st_mode) & 0o077):
        raise ConformanceError("OwnershipInvalid")
    seal = root / "proofs/baselines.json"
    no_symlinks(seal)
    if not seal.is_file() or seal.stat().st_size > MAX_REPORT_BYTES or file_sha256(seal) != sha256(expected_sha256):
        raise ConformanceError("InputChanged")
    evidence = load_json(seal.read_bytes())
    if (not isinstance(evidence, dict) or set(evidence) !=
            {"schemaVersion", "qualification", "mode", "baselineRevision", "entries"}
            or type(evidence["schemaVersion"]) is not int or evidence["schemaVersion"] != 1
            or evidence["qualification"] is not False or evidence["mode"] != "preparation"
            or evidence["baselineRevision"] != BASELINE or not isinstance(evidence["entries"], list)):
        raise ConformanceError("EvidenceIncomplete")
    revisions = {name: revision for name, revision, _, _ in (*BASELINES, ("f06", BASELINE, None, None))}
    if (len(evidence["entries"]) != len(revisions)
            or any(not isinstance(entry, dict) or not isinstance(entry.get("id"), str) for entry in evidence["entries"])
            or {entry.get("id") for entry in evidence["entries"] if isinstance(entry, dict)} != set(revisions)):
        raise ConformanceError("EvidenceIncomplete")
    fields = {"id", "revision", "sourceSha256", "sources", "recipeSha256", "recipes",
              "lockSha256", "locks", "binaries", "packages"}
    for entry in evidence["entries"]:
        if not isinstance(entry, dict) or set(entry) != fields or entry["revision"] != revisions[entry["id"]]:
            raise ConformanceError("EvidenceIncomplete")
        source = root / "stores" / entry["id"]
        no_symlinks(source)
        count = 0
        for path in source.rglob("*"):
            count += 1
            if count > 50_000 or path.is_symlink():
                raise ConformanceError("InputChanged")
        for field in ("sources", "recipes", "locks", "binaries", "packages"):
            if not isinstance(entry[field], dict) or not entry[field] or len(entry[field]) > 50_000:
                raise ConformanceError("EvidenceIncomplete")
        for field, hash_field in (("sources", "sourceSha256"), ("recipes", "recipeSha256"), ("locks", "lockSha256")):
            if digest(entry[field]) != sha256(entry[hash_field]):
                raise ConformanceError("InputChanged")
        if entry["locks"] != {path: value for path, value in entry["sources"].items() if path.endswith("packages.lock.json")}:
            raise ConformanceError("InputChanged")
        expected_sources = dict(entry["sources"])
        if entry["id"] != "f06":
            expected_sources.update({"retained/" + path: value for path, value in entry["recipes"].items()})
        if _hash_tree(source, exclude_outputs=True) != expected_sources:
            raise ConformanceError("InputChanged")
        for field in ("sources", "recipes", "binaries"):
            base = source if field != "recipes" else source / ("tests/fixtures" if entry["id"] == "f06" else "retained")
            for relative, expected in entry[field].items():
                path = base / relative_path(relative)
                no_symlinks(path)
                if not path.is_file() or file_sha256(path) != sha256(expected):
                    raise ConformanceError("InputChanged")
        actual_binaries = {
            path.relative_to(source).as_posix(): file_sha256(path)
            for path in source.rglob("*") if path.is_file()
            and "bin" in path.relative_to(source).parts
            and path.suffix in (".dll", ".json", ".so", ".dylib")
        }
        if actual_binaries != entry["binaries"]:
            raise ConformanceError("InputChanged")
        feeds = {entry["id"]: set()}
        for relative, expected in entry["packages"].items():
            relative_path(relative)
            artifact = relative.startswith("artifacts/")
            filename = relative.removeprefix("artifacts/") if artifact else relative
            if "/" in filename or not filename.endswith(".nupkg") or artifact and entry["id"] != "f06":
                raise ConformanceError("EvidenceIncomplete")
            feed = "f06-artifacts" if artifact else entry["id"]
            feeds.setdefault(feed, set()).add(filename)
            package = root / "feed" / feed / filename
            no_symlinks(package)
            if (not isinstance(expected, dict) or set(expected) != {"sha256", "sha512"}
                    or not package.is_file() or file_sha256(package) != sha256(expected["sha256"])
                    or hashlib.sha512(package.read_bytes()).hexdigest() != expected["sha512"]):
                raise ConformanceError("InputChanged")
        for feed, expected in feeds.items():
            if {path.name for path in (root / "feed" / feed).glob("*.nupkg")} != expected:
                raise ConformanceError("InputChanged")
    if file_sha256(seal) != expected_sha256:
        raise ConformanceError("InputChanged")
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--verify-sha256")
    options = parser.parse_args()
    run = None
    try:
        if options.verify_sha256 is not None:
            verified = verify_prepared_baselines(options.evidence, options.verify_sha256)
            print(json.dumps({"mode": "verification", "qualification": False,
                              "baselines": len(verified["entries"]), "proofSha256": options.verify_sha256}))
            return 0
        run = OwnedRun.allocate(options.evidence, options.root, profile="baseline")
        sealed = prepare(options.root.resolve(), run)
        print(json.dumps({"mode": "preparation", "qualification": False,
                          "proofSha256": file_sha256(sealed)}))
        run.transition("Settling")
        return 0
    except (ConformanceError, OSError, tarfile.TarError) as error:
        code = str(error) if isinstance(error, ConformanceError) else "PrerequisiteMissing"
        print(json.dumps({"mode": "preparation", "qualification": False, "code": code}), file=sys.stderr)
        if run is not None and run.state in ("Active", "Allocated"):
            run.transition("Settling")
            if run.live_children():
                run.transition("Retained")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
