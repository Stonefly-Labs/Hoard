"""Prepare immutable historical sources/binaries before F-07 candidate builds.

Preparation never qualifies providers. Every build uses a private, revision-local
feed/cache and the historical locks; candidate execution may only verify/reuse
the resulting sealed bytes.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile

from foundation_evidence import canonicalize_acceptance_archive
from conformance_evidence import MAX_REPORT_BYTES, ConformanceError, canonical_bytes, digest, file_sha256, load_json, relative_path, sha256, synthetic_nuget_configuration, verify_snapshot
from conformance_execution import OwnedRun, capture_control, no_symlinks
from conformance_lock_preparation import prepare_project_lock, read_lock, rebind_local_archives, verify_project_lock


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
SOURCE_RECIPES_PATH = "tests/fixtures/conformance/baselines/source-consumers.json"
SOURCE_RECIPE_POLICY = (
    *((project, "historical-f06", "api-consumer") for project in (
        "tests/fixtures/lifecycle/registration/RegistrationConsumer/RegistrationConsumer.csproj",
        "tests/fixtures/configuration/LifecycleConsumer/LifecycleConsumer.csproj",
        "tests/fixtures/discovery/RetainedConfiguration/RetainedConfiguration.csproj")),
    *((f"tests/fixtures/{category}/RetainedMarker/RetainedMarker.csproj", "historical-f06", "marker-consumer")
      for category in ("metadata", "artifacts")),
    *((f"tests/fixtures/lifecycle/{name}/Hoard.Fixtures.Lifecycle.{name}.csproj",
       "historical-f06", "provider-implementer")
      for name in ("Protocol.One", "Protocol.Two", "Metadata", "Artifact.One", "Artifact.Two", "Identity")),
    ("tests/fixtures/configuration/LegacyOptions/LegacyOptions.csproj", "historical-f06", "provider-implementer"),
    *((f"tests/fixtures/{category}/{name}/{name}.csproj", "historical-f06",
       "operational-consumer" if name == "Consumer" else "provider-implementer")
      for category, names in (("metadata", ("Sqlite", "Memory", "HostAdapters", "Consumer")),
                              ("artifacts", ("Local", "ObjectSemantics", "HostAdapters", "Consumer")))
      for name in names),
    *((f"tests/fixtures/conformance/Bindings/{name}/{name}.csproj", "candidate-source-manifest",
       "sdk-binding-current") for name in ("Memory", "Sqlite", "Local", "ObjectSemantics")),
)


def validate_source_recipes(document):
    if (not isinstance(document, dict) or set(document) !=
            {"schemaVersion", "qualification", "baselineRevision", "recipes"}
            or type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1
            or document["qualification"] is not False or document["baselineRevision"] != BASELINE
            or not isinstance(document["recipes"], list)
            or any(not isinstance(row, dict) or set(row) != {"project", "sourceKind", "role"}
                   for row in document["recipes"])
            or tuple((row["project"], row["sourceKind"], row["role"]) for row in document["recipes"])
            != SOURCE_RECIPE_POLICY):
        raise ConformanceError("EvidenceIncomplete")
    return document


def source_recipes(repository):
    return validate_source_recipes(load_json(read_lock(Path(repository) / SOURCE_RECIPES_PATH)))


def _copy_recipe_sources(source, target, manifest):
    from conformance_sources import read_bounded
    target.mkdir(mode=0o700)
    for relative, expected in manifest.items():
        original = source / relative_path(relative)
        raw = read_bounded(original, 64 * 1024**2)
        if hashlib.sha256(raw).hexdigest() != sha256(expected):
            raise ConformanceError("InputChanged")
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with destination.open("xb") as output:
            output.write(raw)
        destination.chmod(0o400)
    verify_snapshot(target, manifest)


def _source_recipe_packages(project, feed, *, baseline=False):
    raw = read_lock(project.parent / ("Baseline/packages.lock.json" if baseline else "packages.lock.json"))
    _, packages, _ = rebind_local_archives(raw, feed)
    assets_raw = read_lock(project.parent / "obj/project.assets.json")
    assets = load_json(assets_raw)
    if not isinstance(assets, dict) or not isinstance(assets.get("libraries"), dict):
        raise ConformanceError("InputChanged")
    actual = {}
    for identity, library in assets["libraries"].items():
        if not identity.startswith("Hoard."):
            continue
        if (not isinstance(library, dict) or library.get("type") != "package"
                or not re.fullmatch(r"Hoard\.[A-Za-z0-9.]+/0\.1\.0", identity)):
            raise ConformanceError("InputChanged")
        filename = identity.replace("/", ".") + ".nupkg"
        if filename not in packages:
            raise ConformanceError("InputChanged")
        package = feed / filename
        content = base64.b64encode(hashlib.sha512(package.read_bytes()).digest()).decode("ascii")
        if library.get("sha512") != content:
            raise ConformanceError("InputChanged")
        actual[filename] = file_sha256(package)
    if not actual or actual != packages:
        raise ConformanceError("InputChanged")
    return packages, hashlib.sha256(assets_raw).hexdigest()


def execute_source_recipes(repository, run, candidate, candidate_sources, baseline_sha256):
    """Compile copied source inputs; never rebuild or modify sealed retained binaries."""
    candidate = Path(candidate)
    no_symlinks(candidate)
    if run.state != "Active" or candidate == run.root or not candidate.resolve(strict=True).is_relative_to(run.root):
        raise ConformanceError("OwnershipInvalid")
    verify_snapshot(candidate, candidate_sources)
    document = source_recipes(repository)
    baseline = verify_prepared_baselines(run.root, baseline_sha256)
    historical, = (entry for entry in baseline["entries"] if entry["id"] == "f06")
    roots = {
        "historical-f06": (run.root / "stores/f06", historical["sources"]),
        "candidate-source-manifest": (candidate, candidate_sources),
    }
    copies = {}
    for kind, (source, manifest) in roots.items():
        target = run.root / "stores" / ("source-compatibility-" + kind)
        _copy_recipe_sources(source, target, manifest)
        copies[kind] = target
    feed = run.root / "feed/candidate"
    no_symlinks(feed)
    feed_hashes = _hash_tree(feed)
    if not feed_hashes:
        raise ConformanceError("PrerequisiteMissing")
    verify_snapshot(feed, feed_hashes)
    config = run.root / "stores/source-compatibility.NuGet.Config"
    with config.open("xb") as output:
        output.write(synthetic_nuget_configuration(feed))
    records = []
    for recipe in document["recipes"]:
        kind = recipe["sourceKind"]
        _, manifest = roots[kind]
        copied = copies[kind]
        project = copied / recipe["project"]
        if recipe["project"] not in manifest:
            raise ConformanceError("InputChanged")
        verify_snapshot(copied, manifest)
        preparations = []
        project_xml = ET.parse(project)
        references = project_xml.findall(".//PackageReference")
        explicit = [reference for reference in references if reference.get("Version") is not None]
        if explicit and len(explicit) != len(references):
            raise ConformanceError("InputChanged")
        properties = ("-p:ManagePackageVersionsCentrally=false",) if explicit else ()
        baseline_lock = not (project.parent / "packages.lock.json").is_file()
        _build(run, project, config, "candidate", source_root=copied, preparations=preparations,
               properties=properties, baseline=baseline_lock)
        verify_snapshot(copied, manifest)
        verify_snapshot(feed, feed_hashes)
        for preparation in preparations:
            verify_project_lock(preparation, copied, feed)
        packages, assets_sha = _source_recipe_packages(project, feed, baseline=baseline_lock)
        assembly_name = project_xml.findtext(".//AssemblyName") or project.stem
        assembly = project.parent / "bin/Release/net10.0" / (assembly_name + ".dll")
        no_symlinks(assembly)
        if not assembly.is_file():
            raise ConformanceError("EvidenceIncomplete")
        records.append({
            **recipe, "sourceSha256": digest(manifest), "assemblySha256": file_sha256(assembly),
            "assetsSha256": assets_sha, "packages": packages, "lockPreparations": preparations,
            "properties": list(properties),
        })
    for kind, (_, manifest) in roots.items():
        verify_snapshot(copies[kind], manifest)
    verify_snapshot(candidate, candidate_sources)
    verify_prepared_baselines(run.root, baseline_sha256)
    return {"schemaVersion": 1, "qualification": False, "mode": "source-compatibility",
            "baselineSealSha256": baseline_sha256, "recipeSha256": digest(document),
            "candidatePackages": feed_hashes, "recipes": records}


def _command(run, args, *, cwd, cache_id):
    observed = run.command(args, cwd=cwd, kind="build", cache_id=cache_id,
                           env={"DOTNET_ROLL_FORWARD": "Disable"})
    if observed.exit_code or any(event["code"] != "None" for event in observed.events):
        codes = sorted({event["value"] for event in observed.events if event["code"] == "CommandFailed"})
        diagnostic = {"code": "CommandFailed", "compilerCodes": codes,
                      "commandSequence": run.command_sequence}
        if cache_id in {name for name, _, _, _ in BASELINES} | {"f06", "f06-artifacts"}:
            diagnostic["baselineId"] = cache_id
            if 1403 in codes:
                diagnostic["localArchives"] = local_archive_diagnostics(run.root / "feed" / cache_id)
        print(json.dumps(diagnostic), file=sys.stderr)
        raise ConformanceError("CommandFailed")


def local_archive_diagnostics(feed):
    result = {}
    for name in ("Hoard.Abstractions", "Hoard.Core", "Hoard.Hosting", "Hoard.Application"):
        path = feed / f"{name}.0.1.0.nupkg"
        no_symlinks(path)
        if not path.exists():
            continue
        if not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
            raise ConformanceError("OutputLimitExceeded")
        try:
            with zipfile.ZipFile(path) as archive:
                entry = archive.getinfo(f"lib/net10.0/{name}.dll")
                if entry.file_size > 16 * 1024 * 1024:
                    raise ConformanceError("OutputLimitExceeded")
                result[name] = {"archiveSha256": file_sha256(path),
                                "assemblySha256": hashlib.sha256(archive.read(entry)).hexdigest()}
        except (zipfile.BadZipFile, KeyError):
            raise ConformanceError("InputChanged") from None
    return result


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
    config.write_bytes(synthetic_nuget_configuration(feed))
    return config, feed


def _build(run, project, config, name, *, pack=False, feed=None, source_root=None, preparations=None,
           properties=(), baseline=False):
    lock_args = []
    if preparations is not None:
        alternate, record = prepare_project_lock(project, source_root, run.root / "feed" / name, name,
                                                 baseline=baseline)
        if alternate is not None:
            preparations.append(record)
            lock_args = [f"-p:NuGetLockFilePath={alternate}"]
        elif baseline:
            lock_args = [f"-p:NuGetLockFilePath={project.parent / 'Baseline/packages.lock.json'}"]
    _command(run, ["dotnet", "restore", str(project), "--locked-mode",
                   "--configfile", str(config), "-p:UseSharedCompilation=false", "-nodeReuse:false",
                   "-v", "quiet", *lock_args, *properties], cwd=project.parent, cache_id=name)
    _command(run, ["dotnet", "build", str(project), "-c", "Release",
                   "--no-restore", "-p:UseSharedCompilation=false", "-nodeReuse:false",
                   "-v", "quiet", *lock_args, *properties], cwd=project.parent, cache_id=name)
    if pack:
        _command(run, ["dotnet", "pack", str(project), "-c", "Release", "--no-build",
                       "--no-restore", "-p:UseSharedCompilation=false", "-nodeReuse:false",
                       "-o", str(feed), "-v", "quiet", *lock_args, *properties], cwd=project.parent, cache_id=name)
        for package in feed.glob("*.nupkg"):
            canonicalize_acceptance_archive(package)


def prepare(repository, run, *, prepare_local_archives=False):
    frozen = export_revision(repository, run, BASELINE, "f06")
    specs = (*BASELINES, ("f06", BASELINE, None, None))
    entries = []
    for name, revision, recipe, project_file in specs:
        source = frozen if name == "f06" else export_revision(repository, run, revision, name)
        source_hashes = _hash_tree(source, exclude_outputs=True)
        config, feed = _config(run, name)
        preparations = [] if prepare_local_archives else None

        def build(project, configuration, cache_id, *, pack=False, feed=None):
            _build(run, project, configuration, cache_id, pack=pack, feed=feed,
                   source_root=source, preparations=preparations)

        for package in ("Abstractions", "Core", "Hosting", "Application"):
            project = source / f"src/Hoard.{package}/Hoard.{package}.csproj"
            if project.is_file():
                build(project, config, name, pack=True, feed=feed)
        if name == "f06":
            metadata_projects = (
                "metadata/Sqlite/Sqlite.csproj", "metadata/Memory/Memory.csproj",
                "metadata/HostAdapters/HostAdapters.csproj",
            )
            for relative in metadata_projects:
                build(source / "tests/fixtures" / relative, config, name, pack=True, feed=feed)
            build(source / "tests/fixtures/metadata/Consumer/Consumer.csproj", config, name)
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
                build(source / "tests/fixtures" / relative, artifact_config, "f06-artifacts",
                      pack=True, feed=artifact_feed)
            build(source / "tests/fixtures/artifacts/Consumer/Consumer.csproj", artifact_config, "f06-artifacts")
            recipes = {relative: file_sha256(source / "tests/fixtures" / relative)
                       for relative in (*metadata_projects, *artifact_projects, "metadata/Consumer/Consumer.csproj",
                                        "artifacts/Consumer/Consumer.csproj")}
        else:
            if name == "artifact-marker":
                for relative in ("metadata/Sqlite/Sqlite.csproj", "metadata/Memory/Memory.csproj",
                                 "metadata/HostAdapters/HostAdapters.csproj"):
                    build(source / "tests/fixtures" / relative, config, name, pack=True, feed=feed)
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
            build(target / project_file, config, name)
        recipe_root = source / ("tests/fixtures" if name == "f06" else "retained")
        for sequence, record in enumerate(preparations or ()):
            record_path = recipe_root / "F07LockPreparation" / f"{sequence:04}.json"
            record_path.parent.mkdir(exist_ok=True, mode=0o700)
            with record_path.open("xb") as output:
                output.write(canonical_bytes(record) + b"\n")
            record_path.chmod(0o400)
            recipes[record_path.relative_to(recipe_root).as_posix()] = file_sha256(record_path)
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
        locks.update({record["preparedLock"]: record["preparedSha256"] for record in preparations or ()})
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
    evidence = {"schemaVersion": 2 if prepare_local_archives else 1, "qualification": False, "mode": "preparation",
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
            or type(evidence["schemaVersion"]) is not int or evidence["schemaVersion"] not in (1, 2)
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
        expected_sources = dict(entry["sources"])
        if entry["id"] != "f06":
            expected_sources.update({"retained/" + path: value for path, value in entry["recipes"].items()})
        elif evidence["schemaVersion"] == 2:
            for path, value in entry["recipes"].items():
                relative = "tests/fixtures/" + path
                if relative in expected_sources and expected_sources[relative] != value:
                    raise ConformanceError("InputChanged")
                expected_sources[relative] = value
        expected_locks = {path: value for path, value in entry["sources"].items()
                          if path.endswith("packages.lock.json")}
        recipe_root = source / ("tests/fixtures" if entry["id"] == "f06" else "retained")
        for path in entry["recipes"]:
            if not path.startswith("F07LockPreparation/"):
                continue
            if evidence["schemaVersion"] != 2 or not re.fullmatch(r"F07LockPreparation/[0-9]{4}\.json", path):
                raise ConformanceError("InputChanged")
            record = load_json(read_lock(recipe_root / relative_path(path)))
            if (not isinstance(record, dict) or not isinstance(record.get("feedId"), str) or record["feedId"] not in
                    ({entry["id"], "f06-artifacts"} if entry["id"] == "f06" else {entry["id"]})):
                raise ConformanceError("InputChanged")
            verify_project_lock(record, source, root / "feed" / record["feedId"])
            if (record["project"] not in expected_sources
                    or expected_sources.get(record["originalLock"]) != record["originalSha256"]
                    or record["preparedLock"] in expected_locks):
                raise ConformanceError("InputChanged")
            expected_locks[record["preparedLock"]] = record["preparedSha256"]
        if entry["locks"] != expected_locks:
            raise ConformanceError("InputChanged")
        if _hash_tree(source, exclude_outputs=True) != expected_sources:
            raise ConformanceError("InputChanged")
        for field in ("sources", "recipes", "locks", "binaries"):
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
    parser.add_argument("--prepare-local-archives", action="store_true")
    options = parser.parse_args()
    run = None
    try:
        if options.verify_sha256 is not None:
            if options.prepare_local_archives:
                raise ConformanceError("PrerequisiteMissing")
            verified = verify_prepared_baselines(options.evidence, options.verify_sha256)
            print(json.dumps({"mode": "verification", "qualification": False,
                              "baselines": len(verified["entries"]), "proofSha256": options.verify_sha256}))
            return 0
        run = OwnedRun.allocate(options.evidence, options.root, profile="baseline")
        sealed = prepare(options.root.resolve(), run, prepare_local_archives=options.prepare_local_archives)
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
