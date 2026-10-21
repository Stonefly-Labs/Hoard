"""Bounded, fail-closed fixture-only configuration evidence."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import foundation_evidence as foundation
import lifecycle_evidence as lifecycle


BASELINE = "b80c69fc386541be4f56f6ef2edeca40f43a0e1c"
CASES = tuple(f"CFG-{number:02}" for number in range(1, 37))
PUBLICATION_BARRIERS = ("staged", "write", "flush", "pre-publish", "post-publish")
_workspaces = set()


def create_workspace(parent=None):
    import tempfile
    path = Path(tempfile.mkdtemp(prefix="hoard-configuration-", dir=parent)).resolve()
    path.chmod(0o700)
    _workspaces.add(path)
    return path


def cleanup_workspace(path):
    path = Path(path)
    if path != path.resolve() or path not in _workspaces:
        raise RuntimeError("Refusing cleanup outside owned configuration workspace.")
    shutil.rmtree(path)
    _workspaces.remove(path)


def run(*args, cwd=None, env=None):
    try:
        result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=False, timeout=600,
                                env={**os.environ, **(env or {})})
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Configuration command timed out: {Path(args[0]).name}") from None
    if result.returncode:
        codes = re.findall(r"(?:error (?:CS|NU|MSB)\d+|error WHITESPACE|\bFailed [A-Za-z0-9._]+)", result.stdout)
        context = " [" + ", ".join(codes[:10]) + "]" if codes else ""
        raise RuntimeError(f"Configuration command failed: {Path(args[0]).name}{context}")
    return result.stdout


def verify_cases(cases):
    if not isinstance(cases, list) or len(cases) != len(CASES) or \
            any(not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or
                not isinstance(entry.get("tests"), list) for entry in cases) or \
            sorted(entry.get("id", "") for entry in cases) != sorted(CASES) or \
            any(entry.get("passed") is not True or not entry.get("tests") or
                any(not isinstance(test, str) or not test.strip() for test in entry["tests"])
                for entry in cases):
        raise RuntimeError("Missing, duplicate, failed or incomplete configuration case inventory.")


def verify_binary(path, digest):
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Retained configuration binary changed or missing.")


def verify_package(package, feed, digest):
    if feed != feed.resolve() or package.resolve().parent != feed or not package.is_file() or \
            hashlib.sha512(package.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Invalid configuration package provenance.")


def verify_publication(evidence):
    if not isinstance(evidence, dict) or evidence.get("os") not in ("Darwin", "Linux") or \
            not isinstance(evidence.get("filesystem"), str) or not evidence["filesystem"].strip() or \
            not isinstance(evidence.get("barriers"), list) or \
            any(not isinstance(barrier, str) for barrier in evidence["barriers"]) or \
            evidence.get("passed") is not True or \
            sorted(evidence.get("barriers", [])) != sorted(PUBLICATION_BARRIERS):
        raise RuntimeError("Missing local-platform configuration publication proof.")


lock_hashes = lifecycle.lock_hashes
verify_locks = lifecycle.verify_locks


def test_count(path):
    try:
        return lifecycle.test_count(path)
    except (OSError, ValueError, ET.ParseError):
        raise RuntimeError("Invalid configuration test result counters.") from None


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
        run("dotnet", "pack", str(project), "-c", "Release", "--no-restore",
            "-o", str(feed), "-v", "quiet")
        foundation.canonicalize_acceptance_archive(feed / f"Hoard.{name}.0.1.0.nupkg")
    retained = []
    for name in ("LegacyOptions", "LifecycleConsumer"):
        source = root / "tests/fixtures/configuration" / name
        target = work / "retained" / name
        foundation.copy_source(source, target)
        lock_source = source / "Baseline"
        lock_source.mkdir(exist_ok=True)
        project = target / f"{name}.csproj"
        if not update:
            lock = lock_source / "packages.lock.json"
            if not lock.is_file():
                raise RuntimeError("Missing retained configuration baseline lock.")
            shutil.copy2(lock, target / lock.name)
        run("dotnet", "restore", str(project), "--configfile", str(config),
            "--force-evaluate" if update else "--locked-mode",
            "--packages", str(cache), "-v", "quiet")
        if update:
            shutil.copy2(target / "packages.lock.json", lock_source / "packages.lock.json")
            run("dotnet", "restore", str(project), "--configfile", str(config), "--locked-mode",
                "--packages", str(work / "baseline-replay-cache"), "-v", "quiet")
        run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet")
        binary = target / f"bin/Release/net10.0/{name}.dll"
        if name == "LifecycleConsumer" and run("dotnet", str(binary)).strip() != "lifecycle-compatible":
            raise RuntimeError("Retained lifecycle baseline did not execute.")
        retained.append({"name": name, "baseline": BASELINE, "assembly": str(binary),
                         "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                         "assets": str(target / "obj/project.assets.json")})
    for entry in retained:
        verify_binary(Path(entry["assembly"]), entry["sha256"])
    (work / "retained-binaries.json").write_text(json.dumps(retained, indent=2))
    return retained


def retain_baseline(retained, destination):
    destination = destination.absolute()
    if destination.exists() or not destination.parent.is_dir():
        raise RuntimeError("Retained baseline requires a fresh explicit private destination.")
    if any(destination.is_relative_to(Path(entry["assembly"]).resolve().parent) for entry in retained):
        raise RuntimeError("Retained baseline destination overlaps inputs.")
    destination.mkdir(mode=0o700)
    result = []
    for entry in retained:
        binary = Path(entry["assembly"])
        verify_binary(binary, entry["sha256"])
        target = destination / entry["name"]
        shutil.copytree(binary.parent, target)
        shutil.copy2(entry["assets"], target / "baseline.assets.json")
        saved = {**entry, "assembly": str(target / binary.name), "assets": str(target / "baseline.assets.json")}
        verify_binary(Path(saved["assembly"]), saved["sha256"])
        result.append(saved)
    (destination / "retained-binaries.json").write_text(json.dumps(result, indent=2))
    return result


def retain_evidence(work, destination, kind, passed):
    if kind not in ("source-tests", "baseline") or not isinstance(passed, bool):
        raise RuntimeError("Invalid configuration evidence category.")
    destination = destination.absolute()
    if destination.exists() or not destination.parent.is_dir() or destination.is_relative_to(work):
        raise RuntimeError("Configuration evidence requires a fresh explicit private destination.")
    destination.mkdir(mode=0o700)
    results = []
    for name in ("configuration.trx",):
        source = work / "results" / name
        if source.is_file():
            shutil.copy2(source, destination / name)
            results.append(name)
    (destination / "result.json").write_text(json.dumps({
        "kind": kind, "scope": "partial", "status": "passed" if passed else "failed",
        "testResults": results, "fullAcceptance": False
    }, indent=2))


def complete_acceptance(root, work, update):
    raise RuntimeError("Incomplete configuration acceptance: runtime, package and publication proofs not implemented.")


def focused_tests(root, work, selection):
    if not selection.strip():
        raise RuntimeError("Empty configuration test selection.")
    project = root / "tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj"
    run("dotnet", "restore", str(project), "--locked-mode", "-v", "quiet")
    run("dotnet", "test", str(project), "-c", "Release", "--no-restore", "--filter", selection,
        "--logger", "trx;LogFileName=configuration.trx", "--results-directory", str(work / "results"), "-v", "minimal")
    return test_count(work / "results/configuration.trx")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--update-locks", action="store_true")
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--retain-baseline", type=Path)
    parser.add_argument("--evidence-directory", type=Path)
    parser.add_argument("--filter")
    args = parser.parse_args()
    if args.retain_baseline is not None and not args.baseline_only:
        parser.error("--retain-baseline requires --baseline-only")
    if args.evidence_directory is not None and not (args.baseline_only or args.filter is not None):
        parser.error("--evidence-directory requires an explicitly partial selector")
    root = args.root.resolve()
    before = lock_hashes(root)
    work = create_workspace()
    passed = False
    try:
        if args.baseline_only:
            retained = prepare_baseline(root, work, args.update_locks)
            if args.retain_baseline is not None:
                retain_baseline(retained, args.retain_baseline)
            print(f"Partial configuration baseline proof: {len(retained)} retained binaries; not full acceptance.")
        elif args.filter is not None:
            count = focused_tests(root, work, args.filter)
            print(f"Partial configuration proof: {count} tests; not full CFG-01..36 acceptance.")
        else:
            complete_acceptance(root, work, args.update_locks)
        if not args.update_locks:
            verify_locks(root, before)
        passed = True
    finally:
        try:
            if args.evidence_directory is not None:
                retain_evidence(work, args.evidence_directory, "baseline" if args.baseline_only else "source-tests", passed)
        finally:
            cleanup_workspace(work)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
    except (OSError, ValueError, ET.ParseError):
        raise SystemExit("Configuration evidence preparation failed; inspect local inputs privately.") from None
