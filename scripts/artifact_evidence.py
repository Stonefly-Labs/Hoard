"""Fail-closed orchestration for test-only F-06 qualification."""

import argparse
import base64
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import uuid

import foundation_evidence as foundation
import lifecycle_evidence as lifecycle
import metadata_evidence as metadata

BASELINE = "830972f24795ffaaaa18cb35138db7da59022313"
PROVIDERS = ("local", "object")
CASES = tuple(f"AS-{number:02}" for number in range(1, 49))
BARRIERS = ("B0", "B1", "B2", "B3", "D0", "D1")
PHASES = ("logical", "transfers", "recovery", "packages")
COMMAND_TIMEOUT_SECONDS = 600
CONSUMER_OPERATIONS = (
    "ReserveWriteAsync", "StageAsync", "RenewAsync", "CommitAsync", "OpenReadAsync", "ValidateAsync",
    "ReconcileAsync", "AbandonAsync", "ReserveDeleteAsync", "DeleteAsync", "ObserveAsync", "CleanupAsync",
    "CopyToAsync", "CloseAsync", "AcquireAsync", "RetainAsync")
PACKAGES = tuple(f"Hoard.{name}.0.1.0.nupkg" for name in (
    "Abstractions", "Core", "Hosting", "Application",
    "Fixtures.Metadata.Sqlite", "Fixtures.Metadata.Memory", "Fixtures.Metadata.HostAdapters",
    "Fixtures.Artifacts.Local", "Fixtures.Artifacts.ObjectSemantics", "Fixtures.Artifacts.HostAdapters"))
lock_hashes = lifecycle.lock_hashes
verify_locks = lifecycle.verify_locks
_workspaces = {}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(262144), b""):
            digest.update(block)
    return digest.hexdigest()


def run(*args, cwd=None, env=None):
    child = subprocess.Popen(
        args, cwd=cwd, env={**os.environ, **(env or {})}, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        output, _ = child.communicate(timeout=COMMAND_TIMEOUT_SECONDS)
    except (subprocess.SubprocessError, OSError, UnicodeError, KeyboardInterrupt) as error:
        deadline = time.monotonic() + 10
        try:
            for pid in sorted(command_processes(child.pid, deadline=deadline), reverse=True):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            child.communicate(timeout=max(0.001, deadline - time.monotonic()))
            while command_processes(child.pid, deadline=deadline):
                if time.monotonic() >= deadline:
                    raise subprocess.TimeoutExpired("owned artifact command", 10)
                time.sleep(0.01)
        except (OSError, subprocess.SubprocessError):
            raise RuntimeError("Artifact command cleanup incomplete; private evidence retained.") from None
        if isinstance(error, KeyboardInterrupt):
            raise
        if isinstance(error, subprocess.TimeoutExpired):
            raise RuntimeError("Artifact command exceeded its finite deadline.") from None
        raise RuntimeError("Artifact command output capture failed; private evidence retained.") from None
    if child.returncode:
        codes = sorted(set(re.findall(r"error (?:CS|NU|MSB)\d+|error WHITESPACE", output)))
        suffix = " [" + ", ".join(codes[:10]) + "]" if codes else ""
        raise RuntimeError(f"Artifact command failed: {Path(args[0]).name}{suffix}.")
    return output


def command_processes(session, deadline=None):
    timeout = 5 if deadline is None else min(5, deadline - time.monotonic())
    if timeout <= 0:
        raise subprocess.TimeoutExpired("owned artifact process observation", 0)
    result = subprocess.run(["ps", "-axo", "pid=,pgid=,stat="], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=True)
    return {int(pid) for line in result.stdout.splitlines()
            for pid, group, state in [line.split()]
            if int(group) == session and not state.startswith("Z")}


def no_symlinks(path):
    for entry in (path, *path.parents):
        if entry.is_symlink():
            raise RuntimeError("Artifact destination/proof has a symlinked ancestor.")


def create_workspace(destination, root):
    destination = Path(destination).absolute()
    no_symlinks(destination)
    if (destination.exists() or not destination.parent.is_dir()
            or destination.resolve().is_relative_to(root.resolve())
            or destination.parent.stat().st_uid != os.getuid()
            or destination.parent.stat().st_mode & 0o077):
        raise RuntimeError("Artifact destination requires a fresh child of an owner-private parent outside Git.")
    destination.mkdir(mode=0o700)
    destination = destination.resolve()
    _workspaces[destination] = set()
    return destination


def cleanup_workspace(path):
    path = Path(path)
    if (path != path.resolve() or path not in _workspaces
            or _workspaces[path] or path.is_symlink()):
        raise RuntimeError("Refusing artifact cleanup of an unowned root or live child.")
    shutil.rmtree(path)
    del _workspaces[path]


def proof_file(work, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
        raise RuntimeError("Invalid artifact proof path.")
    candidate = work / value
    no_symlinks(candidate)
    if not candidate.is_file() or not candidate.resolve().is_relative_to(work.resolve()):
        raise RuntimeError("Missing or foreign artifact proof.")
    return candidate


def verify_files(entries, work, identities):
    if (not isinstance(entries, list) or len(entries) != len(identities)
            or any(not isinstance(entry, dict) or not isinstance(entry.get("id"), str) for entry in entries)
            or sorted(entry["id"] for entry in entries) != sorted(identities)):
        raise RuntimeError("Missing, duplicate or foreign artifact file inventory.")
    for entry in entries:
        if sha256(proof_file(work, entry.get("proof"))) != entry.get("sha256"):
            raise RuntimeError("Artifact file hash mismatch.")


def verify_cases(entries, work, run_id):
    expected = {(provider, case) for provider in PROVIDERS for case in CASES}
    if (not isinstance(entries, list) or len(entries) != len(expected)
            or any(not isinstance(entry, dict) or not isinstance(entry.get("provider"), str)
                   or not isinstance(entry.get("id"), str) for entry in entries)
            or {(entry["provider"], entry["id"]) for entry in entries} != expected):
        raise RuntimeError("Missing, duplicate or foreign artifact case inventory.")
    for entry in entries:
        number = int(entry["id"][3:])
        category = "L" if number <= 40 else "D" if number <= 44 else "Q"
        excluded = entry["provider"] == "object" and category == "D"
        if excluded:
            if entry.get("result") != "NotApplicable" or entry.get("reason") != "simulation: no durable restart":
                raise RuntimeError("Artifact object durability exclusion is invalid.")
        elif entry.get("result") != "Passed":
            raise RuntimeError("Failed or skipped applicable artifact case.")
        if (entry.get("class") != category or entry.get("runId") != run_id
                or type(entry.get("durationMs")) not in (int, float)
                or not math.isfinite(entry["durationMs"]) or entry["durationMs"] < 0
                or entry.get("positive") is not True or entry.get("negative") is not True
                or not isinstance(entry.get("tests"), list) or not entry["tests"]
                or any(not isinstance(test, str) or not test.strip() for test in entry["tests"])):
            raise RuntimeError("Stale, unpaired or incomplete artifact case proof.")
        if sha256(proof_file(work, entry.get("proof"))) != entry.get("sha256"):
            raise RuntimeError("Artifact case proof hash mismatch.")


def is_hash(value):
    return isinstance(value, str) and re.fullmatch("[a-f0-9]{64}", value) is not None


def verify_transfer(proof, provider, size, run_id):
    numeric = ("pid", "size", "written", "read", "baselineRssBytes", "osPeakRssBytes",
               "sampledPeakRssBytes", "samples", "bufferBytes", "providerBufferLimit", "slots", "exitCode")
    if (not isinstance(proof, dict) or any(type(proof.get(key)) is not int for key in numeric)
            or proof.get("provider") != provider or proof.get("runId") != run_id
            or proof["pid"] <= 0 or proof["exitCode"] != 0
            or size not in (268435456, 4294967296)
            or any(proof[key] != size for key in ("size", "written", "read"))
            or not is_hash(proof.get("expectedSha256"))
            or any(proof.get(key) != proof["expectedSha256"] for key in ("sourceSha256", "sinkSha256"))
            or proof.get("rssUnits") != "bytes" or proof.get("osPeakMethod") not in ("getrusage", "time-l", "time-v")
            or not 0 < proof["baselineRssBytes"] <= proof["osPeakRssBytes"]
            or proof["osPeakRssBytes"] - proof["baselineRssBytes"] > 67108864
            or proof["sampledPeakRssBytes"] < proof["baselineRssBytes"]
            or proof["sampledPeakRssBytes"] > proof["osPeakRssBytes"]
            or proof["samples"] < 2 or proof["bufferBytes"] != 262144
            or proof["providerBufferLimit"] != 2097152 or proof["slots"] != 1
            or not isinstance(proof.get("runtime"), str) or not proof["runtime"]
            or any(proof.get(key) is not True for key in (
                "sourcePaced", "sinkPaced", "nonSeekable", "generated",
                "independentExpectedHash", "warmupComplete"))):
        raise RuntimeError("Missing, false or unbounded artifact transfer proof.")


def verify_crash(proof, barrier, run_id):
    if (not isinstance(proof, dict) or proof.get("barrier") != barrier
            or barrier not in BARRIERS or proof.get("runId") != run_id
            or proof.get("provider") != "local" or proof.get("signal") != "SIGKILL"
            or type(proof.get("pid")) is not int or proof["pid"] <= 0
            or type(proof.get("reopenPid")) is not int or proof["reopenPid"] <= 0
            or proof["pid"] == proof["reopenPid"] or proof.get("exitCode") != -9
            or not is_hash(proof.get("stateSha256"))
            or any(proof.get(key) is not True for key in (
                "exitConfirmed", "handshake", "stateCompared", "receiptCompared",
                "controlReadback", "newReadback", "ownerFenced", "noDuplicateEffect"))):
        raise RuntimeError("Missing or false artifact crash proof.")


def verify_red_green(entries):
    metadata.verify_red_green(entries)


def source_hash(root):
    return metadata.source_hash(root)


def verify_manifest(evidence, work, source_digest):
    if (not isinstance(evidence, dict) or evidence.get("schemaVersion") != 1
            or evidence.get("sourceSha256") != source_digest
            or evidence.get("phase") != "full" or evidence.get("qualification") is not True
            or evidence.get("production") is not False or not isinstance(evidence.get("runId"), str)
            or not evidence["runId"] or not isinstance(evidence.get("environment"), dict)
            or not all(isinstance(evidence["environment"].get(key), str) and evidence["environment"][key]
                       for key in ("os", "runtime", "filesystem", "flushConfiguration"))
            or evidence.get("baselineRevision") != BASELINE
            or not isinstance(evidence.get("limitations"), list) or not evidence["limitations"]):
        raise RuntimeError("Incomplete or overclaimed artifact qualification manifest.")
    verify_cases(evidence.get("cases"), work, evidence["runId"])
    verify_files(evidence.get("packages"), work, PACKAGES)
    verify_red_green(evidence.get("redGreen"))
    transfers = evidence.get("transfers")
    expected = {(provider, size) for provider in PROVIDERS for size in (268435456, 4294967296)}
    if (not isinstance(transfers, list) or len(transfers) != 4
            or any(not isinstance(value, dict) for value in transfers)
            or {(value.get("provider"), value.get("size")) for value in transfers} != expected):
        raise RuntimeError("Incomplete artifact transfer inventory.")
    for proof in transfers:
        verify_transfer(proof, proof["provider"], proof["size"], evidence["runId"])
    crashes = evidence.get("crashes")
    if (not isinstance(crashes, list) or len(crashes) != 6
            or any(not isinstance(value, dict) for value in crashes)
            or {value.get("barrier") for value in crashes} != set(BARRIERS)):
        raise RuntimeError("Incomplete artifact crash inventory.")
    for proof in crashes:
        verify_crash(proof, proof["barrier"], evidence["runId"])


def prepare_baseline(root, work, update):
    retained = os.environ.get("HOARD_ARTIFACT_RETAINED_BASELINE")
    if retained:
        original = Path(retained).resolve()
        no_symlinks(Path(retained).absolute())
        record = json.loads((original / "retained-binaries.json").read_text())
        if record.get("baseline") != BASELINE:
            raise RuntimeError("Foreign artifact retained baseline revision.")
        for key in ("files", "baselineDependencies"):
            files = record.get(key)
            if not isinstance(files, dict) or not files:
                raise RuntimeError("Missing artifact retained binary/dependency hashes.")
            for name, digest in files.items():
                if sha256(proof_file(original, name)) != digest:
                    raise RuntimeError("Artifact retained binary/dependency hash drift.")
        if sha256(proof_file(original, "baseline.tar")) != record.get("baselineArchiveSha256"):
            raise RuntimeError("Artifact retained source archive hash drift.")
        for name, digest in record.get("baselineSources", {}).items():
            if sha256(proof_file(original / "baseline", name)) != digest:
                raise RuntimeError("Artifact retained source hash drift.")
        if (not record.get("baselineSources")
                or sha256(original / "retained/bin/Release/net10.0/RetainedMarker.dll") != record.get("binarySha256")
                or sha256(root / "tests/fixtures/artifacts/RetainedMarker/Program.cs") != record.get("sourceSha256")
                or sha256(root / "tests/fixtures/artifacts/RetainedMarker/Baseline/packages.lock.json") != record.get("lockSha256")):
            raise RuntimeError("Artifact retained recipe or binary hash drift.")
        for name in ("baseline", "baseline-feed"):
            shutil.copytree(original / name, work / name)
        shutil.copytree(original / "retained", work / "retained",
                        ignore=shutil.ignore_patterns("obj"))
        shutil.copy2(original / "baseline.tar", work / "baseline.tar")
        shutil.copy2(original / "retained-binaries.json", work / "retained-binaries.json")
        return record
    if (root / "src/Hoard.Abstractions/Storage/IArtifactStore.cs").exists():
        raise RuntimeError("Use HOARD_ARTIFACT_RETAINED_BASELINE: baseline must be frozen before public contracts.")
    evidence = metadata.prepare_baseline(
        root, work, update, revision=BASELINE,
        recipe=root / "tests/fixtures/artifacts/RetainedMarker",
        expected_output="artifact-marker-compatible")
    evidence["baselineArchiveSha256"] = sha256(work / "baseline.tar")
    evidence["baselineSources"] = {
        path.relative_to(work / "baseline").as_posix(): sha256(path)
        for path in sorted((work / "baseline").rglob("*"))
        if path.is_file() and not {"obj", "bin"}.intersection(path.parts)}
    evidence["baselineDependencies"] = {
        path.relative_to(work).as_posix(): sha256(path)
        for path in sorted((work / "retained/bin").rglob("*")) if path.is_file()}
    (work / "retained-binaries.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


def verify_metadata_input(previous, current):
    if sha256(previous) == sha256(current):
        return
    if previous.name == current.name == "packages.lock.json":
        documents = [json.loads(path.read_text()) for path in (previous, current)]
        for document in documents:
            for packages in document["dependencies"].values():
                for name, dependency in packages.items():
                    if name.startswith("Hoard.") and "contentHash" in dependency:
                        try:
                            digest = base64.b64decode(dependency["contentHash"], validate=True)
                        except (binascii.Error, ValueError, TypeError):
                            raise RuntimeError("Invalid local metadata package hash.") from None
                        if len(digest) != 64:
                            raise RuntimeError("Invalid local metadata package hash.")
                        dependency["contentHash"] = None
        if documents[0] == documents[1]:
            return
    raise RuntimeError("F-06 must consume unchanged existing metadata fixture sources and lock graphs.")


def prepare_packages(root, work, update):
    historical = work / "metadata-input"
    historical.mkdir()
    archive = work / "metadata-input.tar"
    run("git", "archive", "--format=tar", f"--output={archive}", BASELINE,
        "Directory.Build.props", "Directory.Packages.props", "global.json", "Hoard.slnx", "src",
        "tests/fixtures/metadata", "tests/contracts/Hoard.Metadata.Tests",
        "specs/004-module-discovery/contracts/openapi.json", cwd=root)
    with tarfile.open(archive) as entries:
        entries.extractall(historical, filter="data")
    for base in ("tests/fixtures/metadata", "tests/contracts/Hoard.Metadata.Tests"):
        for old in (historical / base).rglob("*"):
            if old.is_file() and old.suffix in (".cs", ".csproj", ".props", ".sql", ".json"):
                verify_metadata_input(old, root / old.relative_to(historical))
    metadata_work = work / "metadata-packages"
    metadata_work.mkdir()
    metadata.prepare_packages(historical, metadata_work, False)
    current = work / "current"
    current.mkdir()
    for name in ("Directory.Build.props", "Directory.Packages.props", "global.json"):
        shutil.copy2(root / name, current / name)
    foundation.copy_source(root / "src", current / "src")
    resource = Path("specs/004-module-discovery/contracts/openapi.json")
    (current / resource.parent).mkdir(parents=True)
    shutil.copy2(root / resource, current / resource)
    foundation.copy_source(root / "tests/fixtures/artifacts", current / "tests/fixtures/artifacts")
    foundation.copy_source(root / "tests/contracts/Hoard.Artifacts.Tests",
                           current / "tests/contracts/Hoard.Artifacts.Tests")
    environment = {"NUGET_PACKAGES": str(work / "cache")}
    config = work / "NuGet.Config"
    feed = work / "feed"
    feed.mkdir()
    for name in ("Sqlite", "Memory", "HostAdapters"):
        package = f"Hoard.Fixtures.Metadata.{name}.0.1.0.nupkg"
        shutil.copy2(metadata_work / "feed" / package, feed / package)
    from xml.sax.saxutils import escape
    config.write_text(
        '<configuration><packageSources><clear/>'
        f'<add key="local" value="{escape(str(feed))}"/>'
        '<add key="nuget.org" value="https://api.nuget.org/v3/index.json"/>'
        '</packageSources><packageSourceMapping><packageSource key="local">'
        '<package pattern="Hoard.*"/></packageSource><packageSource key="nuget.org">'
        '<package pattern="*"/></packageSource></packageSourceMapping></configuration>')

    def build(relative, pack=False, properties=()):
        project = current / relative
        run("dotnet", "restore", str(project), "--configfile", str(config),
            "--force-evaluate" if update else "--locked-mode", *properties, "-v", "quiet", env=environment)
        if update:
            for lock in project.parent.glob("**/packages.lock.json"):
                if not {"bin", "obj"}.intersection(lock.parts):
                    target = root / lock.relative_to(current)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(lock, target)
        run("dotnet", "restore", str(project), "--configfile", str(config),
            "--locked-mode", *properties, "-v", "quiet", env=environment)
        run("dotnet", "build", str(project), "-c", "Release", "--no-restore",
            *properties, "-v", "quiet", env=environment)
        if pack:
            run("dotnet", "pack", str(project), "-c", "Release", "--no-build",
                "--no-restore", "-o", str(work / "feed"), "-v", "quiet", env=environment)
            package_id = project.stem if project.stem.startswith("Hoard.") else f"Hoard.Fixtures.Artifacts.{project.stem}"
            foundation.canonicalize_acceptance_archive(work / "feed" / f"{package_id}.0.1.0.nupkg")

    for name in ("Abstractions", "Core", "Hosting", "Application"):
        build(f"src/Hoard.{name}/Hoard.{name}.csproj", pack=True)
    for name in ("Local", "ObjectSemantics", "HostAdapters", "Consumer", "CrashRunner", "TransferRunner", "BoundaryLeak"):
        build(f"tests/fixtures/artifacts/{name}/{name}.csproj",
              pack=name in ("Local", "ObjectSemantics", "HostAdapters"))
    build("tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj")
    build("tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj",
          properties=("-p:ArtifactPackageAcceptance=true",))
    packages = [{"id": path.name, "proof": path.relative_to(work).as_posix(), "sha256": sha256(path)}
                for path in sorted((work / "feed").glob("*.nupkg"))]
    verify_files(packages, work, PACKAGES)
    inputs = {"schemaVersion": 1, "qualification": False, "sourceSha256": source_hash(root),
              "baseline": True, "packages": packages, "locks": lock_hashes(root)}
    (work / "prerequisites.json").write_text(json.dumps(inputs, indent=2) + "\n")
    return inputs


def focused_tests(work, selection):
    project = work / "current/tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj"
    results = work / "results"
    arguments = ["dotnet", "test", str(project), "-c", "Release", "--no-build", "--no-restore",
                 "-p:ArtifactPackageAcceptance=true", "--logger", "trx;LogFileName=artifacts.trx",
                 "--results-directory", str(results), "-v", "quiet"]
    if selection:
        arguments += ["--filter", selection]
    output = run(*arguments, env={
        "HOARD_ARTIFACT_TEST_ROOT": str(work / "case-roots"),
        "HOARD_METADATA_WORKSPACE": str(work / "metadata-roots"),
        "HOARD_ARTIFACT_CRASH_PROOFS": str(work / "crashes"),
        "HOARD_ARTIFACT_CRASH_RUNNER": str(work / "current/tests/fixtures/artifacts/CrashRunner/bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll")})
    (work / "tests.txt").write_text(output)
    return lifecycle.test_count(results / "artifacts.trx")


def consumer_journeys(work):
    binary = work / "current/tests/fixtures/artifacts/Consumer/bin/Release/net10.0/Hoard.Fixtures.Artifacts.Consumer.dll"
    journeys = []
    for provider in PROVIDERS:
        result = json.loads(run("dotnet", str(binary), provider, str(work / f"consumer-{provider}")))
        if result != {"qualification": False, "provider": provider, "roundTrip": True,
                      "operations": list(CONSUMER_OPERATIONS)}:
            raise RuntimeError("Artifact unchanged-consumer journey did not pass.")
        journeys.append(result)
    (work / "consumer-journeys.json").write_text(json.dumps(journeys, indent=2) + "\n")
    return journeys


def package_checks(root, work):
    retained = json.loads((work / "retained-binaries.json").read_text())
    runtime = work / "compatible-runtime"
    shutil.copytree(work / "retained/bin/Release/net10.0", runtime)
    current = work / "current"
    for name in ("Abstractions", "Core", "Hosting", "Application"):
        shutil.copy2(current / f"src/Hoard.{name}/bin/Release/net10.0/Hoard.{name}.dll", runtime)
    if (sha256(runtime / "RetainedMarker.dll") != retained["binarySha256"]
            or run("dotnet", str(runtime / "RetainedMarker.dll")).strip() != "artifact-marker-compatible"
            or any(sha256(proof_file(work, path)) != digest for path, digest in retained["files"].items())):
        raise RuntimeError("Frozen pre-F-06 artifact binary compatibility failed.")
    ownership = {
        **{f"Hoard.{name}": name for name in ("Abstractions", "Core", "Hosting", "Application")},
        "NuGet.Versioning": "Versioning", "Microsoft.Extensions.DependencyInjection.Abstractions": "Di",
        **{name: "Artifact" for name in ("Local", "ObjectSemantics", "BoundaryLeak")},
        **{f"Hoard.Fixtures.Artifacts.{name}": "Artifact" for name in ("Local", "ObjectSemantics")},
        **{name: "Host" for name in ("HostAdapters", "Consumer", "CrashRunner", "TransferRunner")},
        "Hoard.Fixtures.Artifacts.HostAdapters": "Host",
        **{f"Hoard.Fixtures.Metadata.{name}": "Metadata" for name in ("Sqlite", "Memory")},
        "Hoard.Fixtures.Metadata.HostAdapters": "Host",
        **{name: "Sdk" for name in ("Microsoft.Data.Sqlite", "Microsoft.Data.Sqlite.Core",
            "SQLitePCLRaw.bundle_e_sqlite3", "SQLitePCLRaw.core", "SQLitePCLRaw.provider.e_sqlite3",
            "SQLitePCLRaw.lib.e_sqlite3", "System.Memory")}
    }
    projects = [("platform", [current / f"src/Hoard.{name}/Hoard.{name}.csproj"
                             for name in ("Abstractions", "Core", "Hosting", "Application")])]
    projects += [(scan, [current / f"tests/fixtures/artifacts/{name}/{name}.csproj"])
                 for scan, name in (("local", "Local"), ("object", "ObjectSemantics"),
                                    ("host-adapters", "HostAdapters"), ("consumer", "Consumer"),
                                    ("crash-runner", "CrashRunner"), ("transfer-runner", "TransferRunner"),
                                    ("boundary-leak", "BoundaryLeak"))]
    graphs = []
    previous = os.environ.get("NUGET_PACKAGES")
    os.environ["NUGET_PACKAGES"] = str(work / "cache")
    try:
        for scan, inputs in projects:
            graph = foundation.inspection_graph(inputs, ownership)
            graph["scanId"] = scan
            for project in graph["projects"]:
                if project["id"] in ("Local", "ObjectSemantics", "HostAdapters", "Consumer",
                                     "CrashRunner", "TransferRunner", "BoundaryLeak"):
                    project["assembly"] = str(Path(project["project"]).parent
                        / f"bin/Release/net10.0/Hoard.Fixtures.Artifacts.{project['id']}.dll")
            graphs.append(graph)
    finally:
        if previous is None:
            os.environ.pop("NUGET_PACKAGES", None)
        else:
            os.environ["NUGET_PACKAGES"] = previous
    manifest = work / "artifact-boundaries.json"
    manifest.write_text(json.dumps({
        "graphs": graphs,
        "baselineAbstractions": str(work / "baseline/src/Hoard.Abstractions/bin/Release/net10.0/Hoard.Abstractions.dll"),
        "currentAbstractions": str(current / "src/Hoard.Abstractions/bin/Release/net10.0/Hoard.Abstractions.dll")
    }, indent=2) + "\n")
    project = root / "tests/architecture/Hoard.Architecture.Tests/Hoard.Architecture.Tests.csproj"
    output = run("dotnet", "test", str(project), "-c", "Release", "--no-restore",
                 "--filter", "FullyQualifiedName~ArtifactBoundaryTests",
                 "--logger", "trx;LogFileName=artifact-boundaries.trx",
                 "--results-directory", str(work / "results"), "-v", "quiet",
                 env={"HOARD_ARTIFACT_BOUNDARIES": str(manifest)})
    (work / "boundaries.txt").write_text(output)
    count = lifecycle.test_count(work / "results/artifact-boundaries.trx")
    journeys = consumer_journeys(work)
    proof = {"testsPassed": count, "retainedBinarySha256": retained["binarySha256"],
             "unchangedRetainedBinaryExecuted": True, "consumerJourneys": len(journeys),
             "scans": [graph["scanId"] for graph in graphs]}
    (work / "package-checks.json").write_text(json.dumps(proof, indent=2) + "\n")
    return proof


def process_rss(pid):
    result = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, check=False)
    if result.returncode or not result.stdout.strip().isdigit():
        raise RuntimeError("Artifact child OS RSS measurement is unavailable.")
    return int(result.stdout.strip()) * 1024


def child_processes(parent):
    result = subprocess.run(["ps", "-axo", "pid=,ppid="], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, check=True)
    pairs = [tuple(map(int, line.split())) for line in result.stdout.splitlines() if len(line.split()) == 2]
    descendants = {parent}
    for _ in range(16):
        found = {pid for pid, ppid in pairs if ppid in descendants}
        if found.issubset(descendants):
            break
        descendants.update(found)
    return descendants - {parent}


def stop_measured_child(child):
    if child.poll() is not None:
        return
    for pid in sorted(child_processes(child.pid), reverse=True):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=10)


def read_child_line(child, timeout):
    with selectors.DefaultSelector() as selection:
        selection.register(child.stdout, selectors.EVENT_READ)
        if not selection.select(timeout):
            raise RuntimeError("Artifact measured child missed its bounded handshake.")
        line = child.stdout.readline(16385)
    if not line or len(line) > 16384:
        raise RuntimeError("Artifact measured child emitted no bounded proof.")
    return json.loads(line)


def expected_transfer_hash(size):
    block = bytes((index * 31 + 7) % 251 for index in range(262144))
    digest = hashlib.sha256()
    remaining = size
    while remaining:
        count = min(len(block), remaining)
        digest.update(block[:count])
        remaining -= count
    return digest.hexdigest()


def measured_transfer(work, provider, size, run_id, expected):
    if sys.platform not in ("darwin", "linux") or not Path("/usr/bin/time").is_file():
        raise RuntimeError("Artifact qualification requires supported OS peak-RSS measurement.")
    if shutil.disk_usage(work).free < 16 * 1024 ** 3:
        raise RuntimeError("Artifact measured transfer requires at least 16 GiB free scratch space.")
    capture = work / f"transfer-{provider}-{size}"
    capture.mkdir(mode=0o700)
    binary = work / "current/tests/fixtures/artifacts/TransferRunner/bin/Release/net10.0/Hoard.Fixtures.Artifacts.TransferRunner.dll"
    flag = "-l" if sys.platform == "darwin" else "-v"
    command = ["/usr/bin/time", flag, "dotnet", str(binary), provider,
               str(capture / "store"), str(size), expected, run_id]
    with (capture / "time.txt").open("w") as errors:
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=errors, text=True, bufsize=1, start_new_session=True)
        _workspaces[work].add(child.pid)
        actual_pid = None
        try:
            idle = read_child_line(child, 120)
            actual_pid = idle.get("pid")
            if (idle.get("eventName") != "idle" or type(actual_pid) is not int
                    or actual_pid not in child_processes(child.pid)):
                raise RuntimeError("Artifact measured handshake is not from the owned transfer child.")
            _workspaces[work].add(actual_pid)
            baseline = process_rss(actual_pid)
            samples = [baseline]
            child.stdin.write("transfer\n")
            child.stdin.flush()
            deadline = time.monotonic() + 2400
            with selectors.DefaultSelector() as selection:
                selection.register(child.stdout, selectors.EVENT_READ)
                while True:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Artifact transfer child exceeded its 40-minute deadline.")
                    if selection.select(0.05):
                        complete = json.loads(child.stdout.readline(16385))
                        break
                    samples.append(process_rss(actual_pid))
            child.wait(timeout=max(0.001, deadline - time.monotonic()))
            if child.stdout.read(1) or child.returncode != 0:
                raise RuntimeError("Artifact transfer child failed or emitted unexpected proof.")
        finally:
            stop_measured_child(child)
            child.stdin.close()
            child.stdout.close()
            _workspaces[work].discard(child.pid)
            if actual_pid is not None:
                _workspaces[work].discard(actual_pid)
    raw = (capture / "time.txt").read_text()
    pattern = r"^\s*(\d+)\s+maximum resident set size\s*$" if sys.platform == "darwin" else r"Maximum resident set size \(kbytes\):\s*(\d+)"
    matched = re.search(pattern, raw, re.MULTILINE)
    if not matched:
        raise RuntimeError("Artifact OS peak resident-memory capture is missing.")
    proof = {**complete, "baselineRssBytes": baseline, "osPeakRssBytes": int(matched[1]) * (1 if sys.platform == "darwin" else 1024),
             "sampledPeakRssBytes": max(samples), "samples": len(samples), "rssUnits": "bytes",
             "osPeakMethod": "time-l" if sys.platform == "darwin" else "time-v", "exitCode": child.returncode}
    (capture / "proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    verify_transfer(proof, provider, size, run_id)
    return proof


def measured_transfers(work, run_id):
    hashes = {size: expected_transfer_hash(size) for size in (268435456, 4294967296)}
    proofs = [measured_transfer(work, provider, size, run_id, hashes[size])
              for provider in PROVIDERS for size in hashes]
    (work / "transfers.json").write_text(json.dumps(proofs, indent=2) + "\n")
    return proofs


def validate_recovery_readback(observed, state, barrier, run_id, pid):
    if not isinstance(state, dict) or not isinstance(state.get("Control"), dict):
        raise RuntimeError("Artifact original crash state is invalid.")
    pattern = bytes((index * 17 + 11) % 256 for index in range(256))
    control = b"acknowledged independent control before crash"
    if (not isinstance(observed, dict) or observed.get("eventName") != "recovered"
            or observed.get("provider") != "local" or observed.get("qualification") is not False
            or observed.get("pid") != pid or observed.get("runId") != run_id or observed.get("barrier") != barrier
            or any(observed.get(key) is not True for key in (
                "controlReadback", "controlReceipt", "exactReceipt", "contentReadback", "ownerFenced", "noDuplicateEffect"))
            or state.get("Run") != run_id or state.get("Barrier") != barrier
            or observed.get("contentSha256") != state.get("TargetDigest")
            or observed.get("contentLength") != state.get("TargetLength")
            or observed.get("controlSha256") != state.get("Control", {}).get("Digest")
            or observed.get("controlLength") != state.get("Control", {}).get("Length")
            or not is_hash(observed.get("contentSha256")) or not is_hash(observed.get("controlSha256"))
            or type(observed.get("contentLength")) is not int or observed["contentLength"] != 1048576
            or observed["contentSha256"] != hashlib.sha256(pattern * 4096).hexdigest()
            or type(observed.get("controlLength")) is not int or observed["controlLength"] != len(control)
            or observed["controlSha256"] != hashlib.sha256(control).hexdigest()
            or observed.get("outcome") != ("Removed" if barrier.startswith("D") else "Published")
            or observed.get("reconstructed") is not (barrier in ("B0", "B1"))
            or observed.get("reclamation") != {"D0": "Pending", "D1": "Reclaimed"}.get(barrier, "NotApplicable")):
        raise RuntimeError("Artifact fresh-process recovery readback is incomplete or foreign.")


def crash_recovery(work, barrier, run_id):
    capture = work / f"crash-{barrier}"
    capture.mkdir(mode=0o700)
    binary = work / "current/tests/fixtures/artifacts/CrashRunner/bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll"
    state_path = capture / "state.json"
    arguments = [str(capture / "store"), str(state_path), barrier, run_id]
    started = time.monotonic()
    with (capture / "crash-errors.txt").open("w") as errors:
        child = subprocess.Popen(["dotnet", str(binary), "crash", *arguments],
                                 stdout=subprocess.PIPE, stderr=errors, text=True, start_new_session=True)
        _workspaces[work].add(child.pid)
        try:
            handshake = read_child_line(child, 120)
            if (handshake.get("eventName") != "barrier" or handshake.get("pid") != child.pid
                    or handshake.get("runId") != run_id or handshake.get("barrier") != barrier
                    or handshake.get("acknowledged") is not (barrier == "B3")
                    or handshake.get("stateSha256") != sha256(state_path) or child.poll() is not None):
                raise RuntimeError("Artifact crash child missed its exact owned barrier.")
            before = sha256(state_path)
            os.kill(child.pid, signal.SIGKILL)
            child.wait(timeout=10)
            if child.returncode != -signal.SIGKILL:
                raise RuntimeError("Artifact crash child did not exit from its parent's SIGKILL.")
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
            child.stdout.close()
            _workspaces[work].discard(child.pid)
    with (capture / "reopen-errors.txt").open("w") as errors:
        reopened = subprocess.Popen(["dotnet", str(binary), "recover", *arguments],
                                    stdout=subprocess.PIPE, stderr=errors, text=True, start_new_session=True)
        _workspaces[work].add(reopened.pid)
        try:
            output, _ = reopened.communicate(timeout=120)
            (capture / "reopen-output.txt").write_text(output)
            if reopened.returncode or len(output) > 16384 or sha256(state_path) != before:
                raise RuntimeError("Artifact fresh-process reopen failed or changed its original ticket proof.")
            observed = json.loads(output)
            state = json.loads(state_path.read_text())
            validate_recovery_readback(observed, state, barrier, run_id, reopened.pid)
        finally:
            if reopened.poll() is None:
                reopened.kill()
                reopened.wait(timeout=10)
            reopened.stdout.close()
            _workspaces[work].discard(reopened.pid)
    proof = {
        "provider": "local", "barrier": barrier, "runId": run_id, "signal": "SIGKILL",
        "pid": child.pid, "reopenPid": reopened.pid, "exitCode": child.returncode,
        "exitConfirmed": True, "handshake": True, "stateCompared": before == sha256(state_path),
        "receiptCompared": observed["exactReceipt"] and observed["controlReceipt"],
        "controlReadback": observed["controlReadback"], "newReadback": observed["contentReadback"],
        "ownerFenced": observed["ownerFenced"], "noDuplicateEffect": observed["noDuplicateEffect"],
        "stateSha256": before, "durationMs": (time.monotonic() - started) * 1000,
        "observed": observed, "parentObserved": handshake,
    }
    verify_crash(proof, barrier, run_id)
    (capture / "proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--phase", choices=PHASES)
    parser.add_argument("--update-locks", action="store_true")
    parser.add_argument("--filter", help="Focused runtime checks only; never full qualification.")
    args = parser.parse_args()
    root = args.root.resolve()
    work = create_workspace(args.evidence, root)
    try:
        before = lock_hashes(root)
        prepare_baseline(root, work, args.update_locks)
        prepare_packages(root, work, args.update_locks)
        if not args.update_locks:
            verify_locks(root, before)
        if args.filter:
            count = focused_tests(work, args.filter)
            journeys = consumer_journeys(work)
            evidence = {"schemaVersion": 1, "qualification": False, "phase": "focused",
                        "testsPassed": count, "sourceSha256": source_hash(root),
                        "baselineRevision": BASELINE, "consumerJourneys": len(journeys)}
            (work / "manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
            print(json.dumps(evidence))
            return 0
        if args.phase == "transfers":
            run_id = str(uuid.uuid4())
            transfers = measured_transfers(work, run_id)
            evidence = {"schemaVersion": 1, "qualification": False, "phase": args.phase,
                        "runId": run_id, "sourceSha256": source_hash(root), "transfers": transfers}
            (work / "manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
            print(json.dumps(evidence))
            return 0
        if args.phase == "packages":
            checks = package_checks(root, work)
            evidence = {"schemaVersion": 1, "qualification": False, "phase": args.phase,
                        "sourceSha256": source_hash(root), "baselineRevision": BASELINE,
                        "packageChecks": checks}
            (work / "manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
            print(json.dumps(evidence))
            return 0
        if args.phase in ("logical", "recovery"):
            run_id = str(uuid.uuid4())
            selection = ("FullyQualifiedName~Artifact&FullyQualifiedName!~ArtifactCrashTests" if args.phase == "logical"
                         else "FullyQualifiedName~ArtifactRecoveryTests|FullyQualifiedName~ArtifactReconciliationTests")
            count = focused_tests(work, selection)
            journeys = consumer_journeys(work) if args.phase == "logical" else []
            crashes = [crash_recovery(work, barrier, run_id) for barrier in BARRIERS] if args.phase == "recovery" else []
            evidence = {"schemaVersion": 1, "qualification": False, "phase": args.phase, "runId": run_id,
                        "sourceSha256": source_hash(root), "testsPassed": count,
                        "consumerJourneys": len(journeys), "crashes": crashes}
            (work / "manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
            print(json.dumps(evidence))
            return 0
        # No case is inferred from compilation, an old run or the verifier's own tests.
        raise RuntimeError("Artifact qualification is incomplete: current provider/case execution is not implemented.")
    except Exception as error:
        (work / "failure.json").write_text(json.dumps({
            "schemaVersion": 1, "qualification": False, "phase": args.phase or "full",
            "error": str(error) if isinstance(error, RuntimeError) else "Artifact preparation failed.",
        }, indent=2) + "\n")
        print("Artifact acceptance failed; private failure evidence retained.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
