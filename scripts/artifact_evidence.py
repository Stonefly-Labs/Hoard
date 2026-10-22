"""Fail-closed orchestration for test-only F-06 qualification."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

import foundation_evidence as foundation
import lifecycle_evidence as lifecycle
import metadata_evidence as metadata

BASELINE = "830972f24795ffaaaa18cb35138db7da59022313"
PROVIDERS = ("local", "object")
CASES = tuple(f"AS-{number:02}" for number in range(1, 49))
BARRIERS = ("B0", "B1", "B2", "B3", "D0", "D1")
PHASES = ("logical", "transfers", "recovery", "packages")
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
    try:
        result = subprocess.run(
            args, cwd=cwd, env={**os.environ, **(env or {})}, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=600)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Artifact command exceeded its finite deadline.") from None
    if result.returncode:
        codes = sorted(set(re.findall(r"error (?:CS|NU|MSB)\d+|error WHITESPACE", result.stdout)))
        suffix = " [" + ", ".join(codes[:10]) + "]" if codes else ""
        raise RuntimeError(f"Artifact command failed: {Path(args[0]).name}{suffix}.")
    return result.stdout


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


def prepare_packages(root, work, update):
    metadata.prepare_packages(root, work, update)
    current = work / "current"
    foundation.copy_source(root / "tests/fixtures/artifacts", current / "tests/fixtures/artifacts")
    foundation.copy_source(root / "tests/contracts/Hoard.Artifacts.Tests",
                           current / "tests/contracts/Hoard.Artifacts.Tests")
    environment = {"NUGET_PACKAGES": str(work / "cache")}
    config = work / "NuGet.Config"

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
            foundation.canonicalize_acceptance_archive(
                work / "feed" / f"Hoard.Fixtures.Artifacts.{project.stem}.0.1.0.nupkg")

    for name in ("Local", "ObjectSemantics", "HostAdapters", "Consumer", "CrashRunner", "TransferRunner"):
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--phase", choices=PHASES)
    parser.add_argument("--update-locks", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    work = create_workspace(args.evidence, root)
    try:
        before = lock_hashes(root)
        prepare_baseline(root, work, args.update_locks)
        prepare_packages(root, work, args.update_locks)
        if not args.update_locks:
            verify_locks(root, before)
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
