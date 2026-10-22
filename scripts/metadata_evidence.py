"""Bounded, fail-closed evidence for the test-only F-05 metadata contract."""

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
import tarfile
from xml.sax.saxutils import escape

import foundation_evidence as foundation
import lifecycle_evidence as lifecycle


BASELINE = "10ce78851b97b02bd83a8ef7da7ffdc2381d6519"
CASES = tuple(f"MP-{number:02}" for number in range(1, 49))
DURABLE_CASES = frozenset(("MP-36", *(f"MP-{number:02}" for number in range(38, 46))))
PROVIDERS = ("sqlite", "memory")
BARRIERS = ("M0", "M1", "M2", "U0", "U1", "U2", "U3", "U4")
PACKAGES = tuple(f"Hoard.{name}.0.1.0.nupkg" for name in (
    "Abstractions", "Core", "Hosting", "Application",
    "Fixtures.Metadata.Sqlite", "Fixtures.Metadata.Memory", "Fixtures.Metadata.HostAdapters"))
create_workspace = lifecycle.create_workspace
cleanup_workspace = lifecycle.cleanup_workspace
lock_hashes = lifecycle.lock_hashes
verify_locks = lifecycle.verify_locks


def run(*args, cwd=None, env=None):
    try:
        result = subprocess.run(
            args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            check=False, timeout=600, env={**os.environ, **(env or {})})
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Metadata command timed out: {Path(args[0]).name}.") from None
    if result.returncode:
        codes = re.findall(r"error (?:CS|NU|MSB)\d+|error WHITESPACE", result.stdout)
        detail = " [" + ", ".join(sorted(set(codes))[:10]) + "]" if codes else ""
        raise RuntimeError(f"Metadata command failed: {Path(args[0]).name}{detail}.")
    return result.stdout


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proof_file(work, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise RuntimeError("Invalid metadata proof path.")
    relative = Path(value)
    if ".." in relative.parts:
        raise RuntimeError("Invalid metadata proof traversal.")
    candidate = work / relative
    current = work
    for component in relative.parts:
        current /= component
        if current.is_symlink():
            raise RuntimeError("Invalid symlinked metadata proof.")
    if not candidate.is_file() or not candidate.resolve().is_relative_to(work.resolve()):
        raise RuntimeError("Missing or foreign metadata proof.")
    return candidate


def exact_inventory(entries, identities):
    return (isinstance(entries, list) and len(entries) == len(identities)
            and all(isinstance(entry, dict) and isinstance(entry.get("id"), str) for entry in entries)
            and sorted(entry["id"] for entry in entries) == sorted(identities))


def verify_cases(entries, work, run_id):
    expected = {(provider, case) for provider in PROVIDERS for case in CASES}
    if (not isinstance(entries, list) or len(entries) != len(expected)
            or any(not isinstance(entry, dict) or not isinstance(entry.get("provider"), str)
                   or not isinstance(entry.get("id"), str) for entry in entries)
            or {(entry["provider"], entry["id"]) for entry in entries} != expected):
        raise RuntimeError("Missing, duplicate or foreign metadata case inventory.")
    for entry in entries:
        durable = entry["id"] in DURABLE_CASES
        excluded = durable and entry["provider"] == "memory"
        if excluded:
            if entry.get("result") != "NotApplicable" or entry.get("reason") != "non-durable fixture":
                raise RuntimeError("Memory metadata durability overclaim.")
        elif entry.get("result") != "Passed":
            raise RuntimeError("Failed applicable metadata case.")
        if (entry.get("class") != ("D" if durable else "L") or entry.get("runId") != run_id
                or type(entry.get("durationMs")) not in (int, float)
                or not math.isfinite(entry["durationMs"]) or entry["durationMs"] < 0
                or entry.get("positive") is not True or entry.get("negative") is not True
                or not isinstance(entry.get("tests"), list) or not entry["tests"]
                or any(not isinstance(test, str) or not test.strip() for test in entry["tests"])):
            raise RuntimeError("Stale, unpaired or incomplete metadata case proof.")
        if sha256(proof_file(work, entry.get("proof"))) != entry.get("sha256"):
            raise RuntimeError("Metadata case proof hash mismatch.")


def verify_crash(entry, barrier):
    if (not isinstance(entry, dict) or entry.get("barrier") != barrier
            or type(entry.get("pid")) is not int or entry["pid"] <= 0
            or type(entry.get("exitCode")) is not int or entry["exitCode"] >= 0
            or any(entry.get(key) is not True for key in (
                "exitConfirmed", "stateCompared", "receiptCompared", "baselineCompared"))):
        raise RuntimeError("Missing or incomplete metadata crash evidence.")


def verify_crashes(entries):
    if (not isinstance(entries, list) or len(entries) != len(BARRIERS)
            or any(not isinstance(entry, dict) or not isinstance(entry.get("barrier"), str) for entry in entries)
            or {entry["barrier"] for entry in entries} != set(BARRIERS)):
        raise RuntimeError("Missing or duplicate metadata crash barrier inventory.")
    for entry in entries:
        verify_crash(entry, entry["barrier"])


def verify_packages(entries, work):
    if not exact_inventory(entries, PACKAGES):
        raise RuntimeError("Missing or duplicate metadata package inventory.")
    for entry in entries:
        if sha256(proof_file(work, entry.get("proof"))) != entry.get("sha256"):
            raise RuntimeError("Metadata package hash mismatch.")


def verify_red_green(entries):
    if (not isinstance(entries, list) or not entries
            or any(not isinstance(entry, dict) or not isinstance(entry.get("id"), str) for entry in entries)
            or len({entry["id"] for entry in entries}) != len(entries)):
        raise RuntimeError("Missing or duplicate metadata red/green proof.")
    for entry in entries:
        if (not isinstance(entry.get("test"), str) or not entry["test"]
                or type(entry.get("redExit")) is not int or entry["redExit"] <= 0
                or entry.get("redOutcome") != "Failed" or entry.get("redAssertion") is not True
                or entry.get("greenOutcome") != "Passed"
                or not re.fullmatch("[0-9a-f]{64}", entry.get("mutationSha256", ""))
                or not re.fullmatch("[0-9a-f]{64}", entry.get("baselineSha256", ""))
                or entry["mutationSha256"] == entry["baselineSha256"]):
            raise RuntimeError("Invalid metadata runtime red/green proof.")


def verify_prerequisites(evidence, phase, source_hash):
    required = {"logical": ("packages", "baseline"),
                "recovery": ("packages", "baseline", "logical"),
                "packages": ("packages", "baseline", "logical", "recovery")}
    if (phase not in required or not isinstance(evidence, dict)
            or evidence.get("schemaVersion") != 1 or evidence.get("sourceSha256") != source_hash
            or any(evidence.get(key) is not True for key in required[phase])):
        raise RuntimeError("Missing, stale or incomplete metadata phase prerequisites.")


def verify_manifest(evidence, work, source_hash):
    if (not isinstance(evidence, dict) or evidence.get("schemaVersion") != 1
            or evidence.get("sourceSha256") != source_hash or evidence.get("production") is not False
            or not isinstance(evidence.get("runId"), str) or not evidence["runId"]
            or not isinstance(evidence.get("environment"), dict)
            or not all(isinstance(evidence["environment"].get(key), str) and evidence["environment"][key]
                       for key in ("os", "runtime", "driver", "nativeSqlite", "filesystem"))
            or evidence.get("configuration") != {
                "journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0}
            or not isinstance(evidence.get("limitations"), list) or not evidence["limitations"]):
        raise RuntimeError("Incomplete or overclaimed metadata qualification manifest.")
    verify_cases(evidence.get("cases"), work, evidence["runId"])
    verify_crashes(evidence.get("crashes"))
    verify_packages(evidence.get("packages"), work)
    verify_red_green(evidence.get("redGreen"))


def source_hash(root):
    inputs = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (path.is_file() and not {".git", "bin", "obj", "__pycache__"}.intersection(relative.parts)
                and (relative.parts[0] in ("src", "tests", "scripts")
                     or str(relative) in ("Directory.Build.props", "Directory.Packages.props", "global.json", "Hoard.slnx",
                                          "specs/004-module-discovery/contracts/openapi.json"))
                and path.suffix in (".cs", ".csproj", ".props", ".json", ".py", ".sh", ".slnx")):
            inputs.append((relative.as_posix(), sha256(path)))
    return hashlib.sha256(json.dumps(inputs, separators=(",", ":")).encode()).hexdigest()


def prepare_baseline(root, work, update):
    run("git", "merge-base", "--is-ancestor", BASELINE, "origin/main", cwd=root)
    baseline = work / "baseline"
    baseline.mkdir()
    archive = work / "baseline.tar"
    run("git", "archive", "--format=tar", f"--output={archive}", BASELINE,
        "Directory.Build.props", "Directory.Packages.props", "global.json", "src", cwd=root)
    with tarfile.open(archive) as contents:
        contents.extractall(baseline, filter="data")
    feed = work / "baseline-feed"
    feed.mkdir()
    cache = work / "baseline-cache"
    config = work / "Baseline.NuGet.Config"
    config.write_text(
        '<configuration><packageSources><clear/>'
        f'<add key="local" value="{escape(str(feed))}"/>'
        '<add key="nuget.org" value="https://api.nuget.org/v3/index.json"/>'
        '</packageSources><packageSourceMapping><packageSource key="local">'
        '<package pattern="Hoard.*"/></packageSource><packageSource key="nuget.org">'
        '<package pattern="*"/></packageSource></packageSourceMapping></configuration>')
    for name in ("Abstractions", "Core", "Hosting"):
        project = baseline / f"src/Hoard.{name}/Hoard.{name}.csproj"
        run("dotnet", "restore", str(project), "--locked-mode", "--configfile", str(config),
            "--packages", str(cache), "-v", "quiet")
        run("dotnet", "pack", str(project), "-c", "Release", "--no-restore", "-o", str(feed), "-v", "quiet")
        foundation.canonicalize_acceptance_archive(feed / f"Hoard.{name}.0.1.0.nupkg")
    source = root / "tests/fixtures/metadata/RetainedMarker"
    target = work / "retained"
    foundation.copy_source(source, target)
    lock = source / "Baseline/packages.lock.json"
    if lock.is_file():
        shutil.copy2(lock, target / "packages.lock.json")
    elif not update:
        raise RuntimeError("Missing retained metadata baseline lock.")
    project = target / "RetainedMarker.csproj"
    run("dotnet", "restore", str(project), "--configfile", str(config),
        "--force-evaluate" if update else "--locked-mode", "--packages", str(cache), "-v", "quiet")
    if update:
        lock.parent.mkdir(exist_ok=True)
        shutil.copy2(target / "packages.lock.json", lock)
        run("dotnet", "restore", str(project), "--configfile", str(config), "--locked-mode",
            "--packages", str(work / "baseline-replay-cache"), "-v", "quiet")
    run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet")
    binary = target / "bin/Release/net10.0/RetainedMarker.dll"
    if run("dotnet", str(binary)).strip() != "metadata-marker-compatible":
        raise RuntimeError("Retained metadata marker baseline did not execute.")
    frozen = {path.relative_to(work).as_posix(): sha256(path)
              for base in (target, feed) for path in sorted(base.rglob("*"))
              if path.is_file() and not {"obj", "Baseline"}.intersection(path.relative_to(base).parts)}
    evidence = {"baseline": BASELINE, "binarySha256": sha256(binary),
                "sourceSha256": sha256(source / "Program.cs"),
                "lockSha256": sha256(lock), "files": frozen}
    (work / "retained-binaries.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


def prepare_packages(root, work, update):
    current = work / "current"
    current.mkdir()
    for name in ("Directory.Build.props", "Directory.Packages.props", "global.json", "Hoard.slnx"):
        shutil.copy2(root / name, current / name)
    foundation.copy_source(root / "src", current / "src")
    resource = Path("specs/004-module-discovery/contracts/openapi.json")
    (current / resource.parent).mkdir(parents=True)
    shutil.copy2(root / resource, current / resource)
    foundation.copy_source(root / "tests/fixtures/metadata", current / "tests/fixtures/metadata")
    foundation.copy_source(root / "tests/contracts/Hoard.Metadata.Tests",
                           current / "tests/contracts/Hoard.Metadata.Tests")
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
    environment = {"NUGET_PACKAGES": str(work / "cache")}

    def build(relative, pack=False, properties=()):
        project = current / relative
        run("dotnet", "restore", str(project), "--configfile", str(config),
            "--force-evaluate" if update else "--locked-mode", *properties, "-v", "quiet", env=environment)
        if update:
            for lock in current.rglob("packages.lock.json"):
                source = root / lock.relative_to(current)
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(lock, source)
        run("dotnet", "restore", str(project), "--configfile", str(config),
            "--locked-mode", *properties, "-v", "quiet", env=environment)
        run("dotnet", "build", str(project), "-c", "Release", "--no-restore", *properties,
            "-v", "quiet", env=environment)
        if pack:
            run("dotnet", "pack", str(project), "-c", "Release", "--no-build",
                "--no-restore", "-o", str(feed), "-v", "quiet", env=environment)
            name = ("Hoard.Fixtures.Metadata." + project.stem if "fixtures" in project.parts else project.stem)
            foundation.canonicalize_acceptance_archive(feed / f"{name}.0.1.0.nupkg")

    for name in ("Abstractions", "Core", "Hosting", "Application"):
        build(f"src/Hoard.{name}/Hoard.{name}.csproj", pack=True)
    for name in ("Sqlite", "Memory", "HostAdapters", "Consumer", "CrashRunner"):
        build(f"tests/fixtures/metadata/{name}/{name}.csproj", pack=name in ("Sqlite", "Memory", "HostAdapters"))
    build("tests/contracts/Hoard.Metadata.Tests/Hoard.Metadata.Tests.csproj",
          properties=("-p:MetadataPackageAcceptance=true",))
    packages = [{"id": path.name, "proof": path.relative_to(work).as_posix(), "sha256": sha256(path)}
                for path in sorted(feed.glob("*.nupkg"))]
    verify_packages(packages, work)
    inputs = {"sourceSha256": source_hash(root), "baseline": True, "packages": True,
              "schemaVersion": 1, "qualification": False, "packageInventory": packages,
              "locks": lock_hashes(root)}
    (work / "prerequisites.json").write_text(json.dumps(inputs, indent=2) + "\n")
    return inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--update-locks", action="store_true")
    parser.add_argument("--phase", choices=("logical", "recovery", "packages"))
    parser.add_argument("--prepare-baseline", type=Path,
                        help="Freeze only pre-F-05 binary evidence in a fresh private directory; does not qualify metadata.")
    parser.add_argument("--prepare-only", type=Path,
                        help="Retain only baseline/build/package prerequisites; does not qualify metadata.")
    args = parser.parse_args()
    root = args.root.resolve()
    before = lock_hashes(root)
    work = create_workspace()
    try:
        if args.prepare_baseline is not None or args.prepare_only is not None:
            if args.prepare_baseline is not None and args.prepare_only is not None or args.phase is not None:
                raise RuntimeError("Metadata preparation selectors cannot be combined.")
            destination = (args.prepare_baseline or args.prepare_only).absolute()
            if destination.exists() or not destination.parent.is_dir():
                raise RuntimeError("Retained metadata baseline requires a fresh destination.")
            evidence = prepare_baseline(root, work, args.update_locks)
            if args.prepare_only is not None:
                prepare_packages(root, work, args.update_locks)
            shutil.copytree(work, destination)
            destination.chmod(0o700)
            print(json.dumps({"baseline": evidence["baseline"], "binarySha256": evidence["binarySha256"],
                              "qualification": False}))
        else:
            prepare_baseline(root, work, args.update_locks)
            prerequisites = prepare_packages(root, work, args.update_locks)
            verify_prerequisites(prerequisites, args.phase or "logical", source_hash(root))
            raise RuntimeError("Metadata qualification incomplete: runtime logical/recovery/package proof is required.")
        if not args.update_locks:
            verify_locks(root, before)
    finally:
        cleanup_workspace(work)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError) as error:
        if isinstance(error, RuntimeError):
            print(str(error), file=sys.stderr)
        else:
            print("Metadata evidence I/O or input failure; preserve private diagnostic evidence.", file=sys.stderr)
        raise SystemExit(1)
