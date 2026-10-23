"""Explicit non-qualifying lock preparation and independent fresh locked replay."""

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
import zipfile

import conformance_baselines as baselines
import conformance_evidence as evidence
from conformance_execution import OwnedRun, native_execution_supported, no_symlinks
from conformance_lock_preparation import prepare_project_lock, read_lock, verify_project_lock
from foundation_evidence import canonicalize_acceptance_archive


@dataclass(frozen=True)
class Project:
    path: str
    package: str | None = None
    package_mode: bool = False

    @property
    def lock_path(self):
        return (Path(self.path).parent /
                ("PackageAcceptance/packages.lock.json" if self.package_mode else "packages.lock.json")).as_posix()


PREREQUISITES = (
    *(Project(f"src/Hoard.{name}/Hoard.{name}.csproj", f"Hoard.{name}")
      for name in ("Abstractions", "Core", "Hosting", "Application")),
    *(Project(f"tests/fixtures/metadata/{name}/{name}.csproj", f"Hoard.Fixtures.Metadata.{name}")
      for name in ("Sqlite", "Memory", "HostAdapters")),
    *(Project(f"tests/fixtures/artifacts/{name}/{name}.csproj", f"Hoard.Fixtures.Artifacts.{name}")
      for name in ("Local", "ObjectSemantics", "HostAdapters")),
)
TARGETS = (
    Project("tests/contracts/Hoard.Testing.Conformance/Hoard.Testing.Conformance.csproj",
            "Hoard.Testing.Conformance"),
    Project("tests/contracts/Hoard.Conformance.TestLogger/Hoard.Conformance.TestLogger.csproj",
            "Hoard.Conformance.TestLogger"),
    *(Project(f"tests/fixtures/conformance/Bindings/{name}/{name}.csproj",
              f"Hoard.Fixtures.Conformance.Bindings.{name}")
      for name in ("Sqlite", "Memory", "Local", "ObjectSemantics")),
    *(Project(f"tests/fixtures/conformance/{name}/{name}.csproj", f"Hoard.Fixtures.Conformance.{name}")
      for name in ("Contributor", "Host")),
    Project("tests/fixtures/conformance/Consumer/Consumer.csproj"),
    Project("tests/contracts/Hoard.Conformance.TestLogger/Smoke/Smoke.csproj"),
    Project("tests/contracts/Hoard.Conformance.Tests/Hoard.Conformance.Tests.csproj"),
    Project("tests/contracts/Hoard.Conformance.Tests/Hoard.Conformance.Tests.csproj", package_mode=True),
    Project("tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj", package_mode=True),
)


def build_project(run, source, project, config, feed, *, update, historical_lock=False):
    properties = ["-p:UseSharedCompilation=false", "-nodeReuse:false", "-v", "quiet"]
    if project.package_mode:
        properties.append("-p:ConformancePackageAcceptance=true")
    record = None
    if historical_lock:
        alternate, record = prepare_project_lock(source / project.path, source, feed, "candidate")
        if alternate is not None:
            properties.append("-p:NuGetLockFilePath=" + str(alternate))
    elif update and (source / project.lock_path).exists():
        no_symlinks(source / project.lock_path)
        (source / project.lock_path).chmod(0o600)
    cache = "candidate-lock-preparation" if update else "candidate-locked-replay"
    baselines._command(run, ["dotnet", "restore", str(source / project.path), "--configfile", str(config),
                            "--force-evaluate" if update else "--locked-mode", *properties],
                       cwd=source, cache_id=cache)
    baselines._command(run, ["dotnet", "build", str(source / project.path), "-c", "Release",
                            "--no-restore", *properties], cwd=source, cache_id=cache)
    if project.package is not None:
        baselines._command(run, ["dotnet", "pack", str(source / project.path), "-c", "Release",
                                "--no-build", "--no-restore", "-o", str(feed), *properties],
                           cwd=source, cache_id=cache)
        canonicalize_acceptance_archive(feed / f"{project.package}.0.1.0.nupkg")
    if record is not None:
        verify_project_lock(record, source, feed)
    return record


def _write_locks(source, locks):
    for relative, data in locks.items():
        target = source / relative
        no_symlinks(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.chmod(0o600)
        with target.open("wb") as output:
            output.write(data)
        target.chmod(0o400)


def _graph(run, source, sources, *, update):
    config, feed = baselines._config(run, "candidate")
    records = []
    for project in PREREQUISITES:
        record = build_project(run, source, project, config, feed, update=False, historical_lock=True)
        if record is not None:
            records.append(record)
    for project in TARGETS:
        build_project(run, source, project, config, feed, update=update)
    locks = {project.lock_path: read_lock(source / project.lock_path) for project in TARGETS}
    expected = {**sources, **{path: hashlib.sha256(data).hexdigest() for path, data in locks.items()}}
    evidence.verify_snapshot(source, expected)
    for record in records:
        verify_project_lock(record, source, feed)
    evidence.verify_synthetic_source_mapping(
        run.root, config.relative_to(run.root).as_posix(), feed.relative_to(run.root).as_posix())
    return locks, evidence.proof_manifest(feed), records


def publish_locks(repository, sources, locks):
    if set(locks) != {project.lock_path for project in TARGETS}:
        raise evidence.ConformanceError("EvidenceIncomplete")
    if dict(evidence.source_manifest(repository)) != dict(sources):
        raise evidence.ConformanceError("InputChanged")
    for relative, data in locks.items():
        document = evidence.load_json(data)
        if (len(data) > 2 * 1024 * 1024 or not isinstance(document, dict)
                or type(document.get("version")) is not int or document["version"] not in (1, 2)
                or not isinstance(document.get("dependencies"), dict)):
            raise evidence.ConformanceError("InputChanged")
    with evidence._input_root(repository) as (_, root):
        for relative, data in locks.items():
            with evidence._input_parent(root, relative) as (parent, name):
                if relative in sources:
                    actual, _ = evidence._source_file(
                        root, relative, remaining=2 * 1024 * 1024, deadline=time.monotonic() + 5)
                    if actual != sources[relative]:
                        raise evidence.ConformanceError("InputChanged")
                else:
                    try:
                        os.stat(name, dir_fd=parent, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        raise evidence.ConformanceError("InputChanged")
                temporary = f".conformance-lock-{uuid.uuid4().hex}.tmp"
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o644, dir_fd=parent)
                try:
                    with os.fdopen(descriptor, "wb") as output:
                        output.write(data)
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                finally:
                    try:
                        os.unlink(temporary, dir_fd=parent)
                    except FileNotFoundError:
                        pass


def _settle(run):
    if run.state in ("Active", "Allocated"):
        run.transition("Settling")
    if run.state == "Settling" and run.live_children():
        run.transition("Retained")
        raise evidence.ConformanceError("CleanupIncomplete")


def execute(repository, destination):
    if not native_execution_supported():
        raise evidence.ConformanceError("PrerequisiteMissing")
    run = OwnedRun.allocate(destination, repository, profile="baseline")
    replay = None
    try:
        (run.root / "cache/.local/share").mkdir(parents=True, mode=0o700)
        (run.root / "cache/.local").chmod(0o700)
        seal = baselines.prepare(repository, run, prepare_local_archives=True)
        seal_sha = evidence.file_sha256(seal)
        baselines.verify_prepared_baselines(run.root, seal_sha)
        source, sources = evidence.snapshot_sources(repository, run)
        locks, packages, records = _graph(run, source, sources, update=True)
        _settle(run)
        replay = OwnedRun.allocate(run.root / "stores/locked-replay", repository, profile="baseline")
        replay.deadline = min(replay.deadline, run.deadline)
        (replay.root / "cache/.local/share").mkdir(parents=True, mode=0o700)
        (replay.root / "cache/.local").chmod(0o700)
        fresh, fresh_sources = evidence.snapshot_sources(repository, replay)
        if dict(fresh_sources) != dict(sources):
            raise evidence.ConformanceError("InputChanged")
        _write_locks(fresh, locks)
        replayed, replay_packages, replay_records = _graph(replay, fresh, fresh_sources, update=False)
        if replayed != locks or dict(replay_packages) != dict(packages):
            raise evidence.ConformanceError("InputChanged")
        _settle(replay)
        baselines.verify_prepared_baselines(run.root, seal_sha)
        summary = {
            "schemaVersion": 1, "mode": "preparation", "qualification": False,
            "baselineSha256": seal_sha, "sourceSha256": evidence.digest(sources),
            "locks": {path: hashlib.sha256(data).hexdigest() for path, data in locks.items()},
            "packages": dict(packages), "lockedReplay": True,
            "prerequisiteLockDerivations": records, "replayPrerequisiteLockDerivations": replay_records,
        }
        with (run.root / "proofs/lock-preparation.json").open("xb") as output:
            output.write(evidence.canonical_bytes(summary) + b"\n")
        publish_locks(repository, sources, locks)
        print(json.dumps({"mode": "preparation", "qualification": False, "code": "None",
                          "locks": len(locks), "packages": len(packages), "lockedReplay": True,
                          "baselineSha256": seal_sha,
                          "proofSha256": evidence.file_sha256(run.root / "proofs/lock-preparation.json")}))
        return 0
    finally:
        for owned in (replay, run):
            if owned is not None:
                _settle(owned)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise evidence.ConformanceError()


def main(arguments=None):
    parser = Arguments(description=__doc__, add_help=False)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--update-locks", action="store_true")
    parser.add_argument("--help", action="store_true")
    try:
        options = parser.parse_args(arguments)
        if options.help:
            parser.print_help()
            return 0
        if not options.update_locks or options.evidence is None:
            raise evidence.ConformanceError()
    except evidence.ConformanceError:
        print(json.dumps({"mode": "preparation", "qualification": False,
                          "status": "Incomplete", "code": "EvidenceSchemaInvalid"}))
        return 2
    try:
        return execute(options.root.absolute(), options.evidence.absolute())
    except (evidence.ConformanceError, OSError, ValueError, zipfile.BadZipFile) as error:
        code = str(error) if isinstance(error, evidence.ConformanceError) else "PrerequisiteMissing"
        status = evidence.failure_status(code)
        print(json.dumps({"mode": "preparation", "qualification": False, "status": status, "code": code}))
        return 2 if status == "Incomplete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
