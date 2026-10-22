"""Bounded, fail-closed evidence for the test-only F-05 metadata contract."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tarfile
import time
import uuid
import xml.etree.ElementTree as ET
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


def retain_private_evidence(work, destination, root):
    destination = destination.absolute()
    if (destination.exists() or destination.is_symlink() or not destination.parent.is_dir()
            or destination.resolve().is_relative_to(root.resolve())):
        raise RuntimeError("Metadata evidence requires a fresh destination outside the repository.")
    destination.mkdir(mode=0o700)
    shutil.copytree(work, destination, dirs_exist_ok=True)
    destination.chmod(0o700)


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
            or evidence.get("providers") != provider_inventory()
            or not isinstance(evidence.get("limitations"), list) or not evidence["limitations"]):
        raise RuntimeError("Incomplete or overclaimed metadata qualification manifest.")
    verify_cases(evidence.get("cases"), work, evidence["runId"])
    verify_crashes(evidence.get("crashes"))
    verify_packages(evidence.get("packages"), work)
    verify_red_green(evidence.get("redGreen"))


def provider_inventory():
    return [
        {"id": provider, "package": f"Hoard.Fixtures.Metadata.{name}", "version": "0.1.0",
         "moduleId": "fixture.metadata", "moduleVersion": "0.1.0", "configurationVersion": 1, "optionsVersion": 1,
         "schema": f"fixture-{provider}-v2", "durable": provider == "sqlite"}
        for provider, name in (("sqlite", "Sqlite"), ("memory", "Memory"))]


def source_hash(root):
    inputs = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (path.is_file() and not {".git", "bin", "obj", "__pycache__"}.intersection(relative.parts)
                and (relative.parts[0] in ("src", "tests", "scripts")
                     or str(relative) in ("Directory.Build.props", "Directory.Packages.props", "global.json", "Hoard.slnx",
                                          "specs/004-module-discovery/contracts/openapi.json"))
                and path.suffix in (".cs", ".csproj", ".props", ".json", ".py", ".sh", ".slnx", ".sql")):
            inputs.append((relative.as_posix(), sha256(path)))
    return hashlib.sha256(json.dumps(inputs, separators=(",", ":")).encode()).hexdigest()


def prepare_baseline(root, work, update, *, revision=BASELINE, recipe=None,
                     expected_output="metadata-marker-compatible"):
    run("git", "merge-base", "--is-ancestor", revision, "origin/main", cwd=root)
    baseline = work / "baseline"
    baseline.mkdir()
    archive = work / "baseline.tar"
    run("git", "archive", "--format=tar", f"--output={archive}", revision,
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
    source = recipe or root / "tests/fixtures/metadata/RetainedMarker"
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
    if run("dotnet", str(binary)).strip() != expected_output:
        raise RuntimeError("Retained metadata marker baseline did not execute.")
    frozen = {path.relative_to(work).as_posix(): sha256(path)
              for base in (target, feed) for path in sorted(base.rglob("*"))
              if path.is_file() and not {"obj", "Baseline"}.intersection(path.relative_to(base).parts)}
    evidence = {"baseline": revision, "binarySha256": sha256(binary),
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
    for name in ("Sqlite", "Memory", "HostAdapters", "Consumer", "CrashRunner", "BoundaryLeak"):
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


def write_proof(work, name, value):
    target = work / "proofs" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2) + "\n")
    return target.relative_to(work).as_posix()


def runtime_json(binary, mode, database, directory, barrier):
    value = json.loads(run("dotnet", str(binary), mode, str(database), str(directory), barrier))
    if not isinstance(value, dict):
        raise RuntimeError("Invalid metadata recovery result.")
    return value


def await_barrier(child, directory, barrier, timeout=15):
    deadline = time.monotonic() + timeout
    acknowledgement = directory / "barrier.json"
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError("Metadata child exited before its named barrier.")
        if acknowledgement.is_file():
            try:
                value = json.loads(acknowledgement.read_text())
            except json.JSONDecodeError:
                time.sleep(0.01)
                continue
            if value != {"barrier": barrier, "pid": child.pid}:
                raise RuntimeError("Foreign or stale metadata crash barrier.")
            return
        time.sleep(0.01)
    raise RuntimeError("Metadata crash barrier timed out.")


def kill_owned_child(child):
    if child.poll() is not None:
        raise RuntimeError("Metadata crash child was not alive at termination.")
    child.kill()
    try:
        code = child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Metadata child exit was not confirmed.") from None
    if code >= 0:
        raise RuntimeError("Metadata child did not exit by signal.")
    return code


def recovery_cases(work):
    binary = work / "current/tests/fixtures/metadata/CrashRunner/bin/Release/net10.0/Hoard.Fixtures.Metadata.CrashRunner.dll"
    crashes = []
    proofs = {}
    environment = None
    for barrier in BARRIERS:
        directory = work / "recovery" / barrier
        directory.mkdir(parents=True)
        database = directory / "metadata.db"
        mutation = barrier.startswith("M")
        family = "mutation" if mutation else "upgrade"
        if runtime_json(binary, "seed-" + family, database, directory, barrier) != {"seeded": True}:
            raise RuntimeError("Metadata recovery baseline was not seeded.")
        started = time.monotonic()
        with subprocess.Popen(["dotnet", str(binary), "run-" + family, str(database), str(directory), barrier],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as child:
            try:
                await_barrier(child, directory, barrier)
                if barrier in ("U1", "U2"):
                    probe = runtime_json(binary, "probe-upgrade", database, directory, barrier)
                    if probe != {"independentOldLayout": True, "admissionRejected": True}:
                        raise RuntimeError("Partial metadata upgrade became admissible.")
                code = kill_owned_child(child)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=10)
        observed = runtime_json(binary, "recover-" + family, database, directory, barrier)
        entry = {"barrier": barrier, "pid": child.pid, "exitCode": code, "exitConfirmed": True,
                 **{key: observed.get(key) for key in ("stateCompared", "receiptCompared", "baselineCompared")}}
        verify_crash(entry, barrier)
        proof = write_proof(work, f"crash-{barrier}.json", {**entry, "observations": observed})
        crashes.append(entry)
        proofs[barrier] = {"proof": proof, "tests": [f"parent-kill:{barrier}"], "durationMs": (time.monotonic() - started) * 1000}
        if mutation:
            settings = observed.get("settings", {})
            if {key: settings.get(key) for key in ("JournalMode", "Synchronous", "ForeignKeys", "BusyTimeout")} != {
                "JournalMode": "wal", "Synchronous": 2, "ForeignKeys": 1, "BusyTimeout": 0
            }:
                raise RuntimeError("Durable metadata configuration was not effective.")
            environment = {"os": observed.get("os"), "runtime": observed.get("runtime"),
                           "driver": settings.get("Driver"), "nativeSqlite": settings.get("NativeVersion")}
    verify_crashes(crashes)
    directory = work / "recovery" / "walkthrough"
    directory.mkdir()
    started = time.monotonic()
    result = runtime_json(binary, "recovery-walkthrough", directory / "metadata.db", directory, "walkthrough")
    if (result.get("cases") != ["MP-36", "MP-44", "MP-45"]
            or any(result.get(key) is not True for key in ("positive", "negative", "walCaptured", "isolatedRestoreCompared", "artifactSetRequired"))):
        raise RuntimeError("Incomplete metadata backup/restore proof.")
    walkthrough = {"proof": write_proof(work, "recovery-walkthrough.json", result),
                   "tests": ["verified-backup-and-compatible-rollback"], "durationMs": (time.monotonic() - started) * 1000}
    directory = work / "recovery" / "ownership"
    directory.mkdir()
    database = directory / "metadata.db"
    with subprocess.Popen(["dotnet", str(binary), "hold-owner", str(database), str(directory), "owner"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as child:
        try:
            await_barrier(child, directory, "owner")
            if runtime_json(binary, "try-owner", database, directory, "owner") != {"competingOwnerRejected": True}:
                raise RuntimeError("Competing process acquired metadata ownership.")
            owner_exit = kill_owned_child(child)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
    if runtime_json(binary, "reopen-owner", database, directory, "owner") != {"crashReleasedOwner": True}:
        raise RuntimeError("Process termination did not release metadata ownership.")
    owner = {"proof": write_proof(work, "ownership.json", {"competingOwnerRejected": True, "crashReleasedOwner": True,
             "pid": child.pid, "exitCode": owner_exit}), "tests": ["second-process-owner-and-crash-release"], "durationMs": 0}
    directory = work / "recovery" / "native-ownership"
    directory.mkdir()
    database = directory / "metadata.db"
    started = time.monotonic()
    with subprocess.Popen(["dotnet", str(binary), "stuck-native", str(database), str(directory), "native-step"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as child:
        try:
            await_barrier(child, directory, "native-step")
            deadline = time.monotonic() + 45
            while not (directory / "cleanup.json").is_file():
                if child.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("Incomplete native metadata cleanup was not reported.")
                time.sleep(0.01)
            cleanup = json.loads((directory / "cleanup.json").read_text())
            if (cleanup != {"cleanupIncomplete": True, "guardRetained": True, "admissionRejected": True}
                    or runtime_json(binary, "try-owner", database, directory, "owner") != {"competingOwnerRejected": True}):
                raise RuntimeError("Native metadata work lost ownership or publication protection.")
            native_exit = kill_owned_child(child)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
    if runtime_json(binary, "reopen-owner", database, directory, "owner") != {"crashReleasedOwner": True}:
        raise RuntimeError("Terminated native metadata work did not release process ownership.")
    native = {"proof": write_proof(work, "native-ownership.json", {**cleanup, "nativeStepEntered": True,
              "pid": child.pid, "exitCode": native_exit, "crashReleasedOwner": True}),
              "tests": ["sqlite3-step-stall-and-incomplete-cleanup"], "durationMs": (time.monotonic() - started) * 1000}
    restore_crashes = []
    for barrier in ("R0", "R1"):
        directory = work / "recovery" / barrier
        directory.mkdir()
        database = directory / "metadata.db"
        if runtime_json(binary, "seed-restore", database, directory, barrier) != {"seeded": True}:
            raise RuntimeError("Interrupted restore baseline was not seeded.")
        with subprocess.Popen(["dotnet", str(binary), "run-restore", str(database), str(directory), barrier],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as child:
            try:
                await_barrier(child, directory, barrier)
                code = kill_owned_child(child)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=10)
        observed = runtime_json(binary, "recover-restore", database, directory, barrier)
        if observed != {"uninstalledTargetAbsent": True, "retryRestoredBaseline": True, "historicalTicketRejected": True}:
            raise RuntimeError("Interrupted restore exposed an unverified or historical-epoch target.")
        restore_crashes.append({"barrier": barrier, "pid": child.pid, "exitCode": code, "exitConfirmed": True, **observed})
    walkthrough["proof"] = write_proof(work, "verified-recovery-and-installation.json", {
        "walkthrough": json.loads(proof_file(work, walkthrough["proof"]).read_text()), "restoreCrashes": restore_crashes})
    walkthrough["tests"] += ["parent-kill:R0", "parent-kill:R1"]
    cases = {"MP-38": proofs["M0"], "MP-39": proofs["M1"], "MP-40": proofs["M2"], "MP-43": owner,
             "MP-37": native,
             **{case: walkthrough for case in ("MP-36", "MP-44", "MP-45")}}
    for case, barriers in (("MP-41", ("U0", "U1", "U2")), ("MP-42", ("U3", "U4"))):
        cases[case] = {"proof": write_proof(work, f"{case}.json", [json.loads(proof_file(work, proofs[barrier]["proof"]).read_text()) for barrier in barriers]),
                       "tests": [f"parent-kill:{barrier}" for barrier in barriers],
                       "durationMs": sum(proofs[barrier]["durationMs"] for barrier in barriers)}
    return cases, crashes, environment


def trx_results(path):
    namespace = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
    document = ET.parse(path)
    results = document.findall(".//t:UnitTestResult", namespace)
    if not results or any(result.get("outcome") != "Passed" for result in results):
        raise RuntimeError("Missing, failed or skipped metadata runtime tests.")
    observed = []
    for result in results:
        duration = result.get("duration", "").split(":")
        if len(duration) != 3:
            raise RuntimeError("Missing metadata test duration.")
        milliseconds = (int(duration[0]) * 3600 + int(duration[1]) * 60 + float(duration[2])) * 1000
        observed.append({"test": result.get("testName", ""), "durationMs": milliseconds})
    return observed


def logical_cases(work):
    output = work / "current/tests/contracts/Hoard.Metadata.Tests/bin/Release/net10.0"
    binary = output / "Hoard.Metadata.Tests.dll"
    consumer = work / "current/tests/fixtures/metadata/Consumer/bin/Release/net10.0/Hoard.Fixtures.Metadata.Consumer.dll"
    frozen = {str(path): sha256(path) for path in (binary, consumer)}
    inventories = {}
    required = set(CASES) - DURABLE_CASES - {"MP-47", "MP-48"}
    for provider in PROVIDERS:
        environment = {"HOARD_METADATA_PROVIDER": provider, "HOARD_METADATA_WORKSPACE": str(work)}
        run("dotnet", "vstest", str(binary), f"/Logger:trx;LogFileName={provider}.trx",
            f"/ResultsDirectory:{work / 'results'}", env=environment)
        proof = f"results/{provider}.trx"
        tests = trx_results(work / proof)
        cases = {}
        for test in tests:
            match = re.search(r"\bMP(\d{2})_", test["test"])
            if match:
                case = "MP-" + match[1]
                if case not in required:
                    raise RuntimeError("Foreign logical metadata case.")
                entry = cases.setdefault(case, {"proof": proof, "tests": [], "durationMs": 0})
                entry["tests"].append(test["test"])
                entry["durationMs"] += test["durationMs"]
        if set(cases) != required:
            raise RuntimeError("Incomplete logical metadata case attribution.")
        if run("dotnet", str(consumer), env=environment).strip() != "metadata-package-consumer-compatible":
            raise RuntimeError("Unchanged metadata consumer did not execute.")
        cases["MP-46"]["tests"].append("unchanged-package-consumer")
        inventories[provider] = cases
    if frozen != {str(path): sha256(path) for path in (binary, consumer)}:
        raise RuntimeError("Metadata common suite or consumer binary changed between compositions.")
    write_proof(work, "unchanged-consumers.json", {
        "testAssemblySha256": frozen[str(binary)], "consumerSha256": frozen[str(consumer)],
        "providers": list(PROVIDERS), "unchanged": True})
    return inventories


def compatibility_cases(root, work):
    retained = json.loads((work / "retained-binaries.json").read_text())
    runtime = work / "compatible-runtime"
    shutil.copytree(work / "retained/bin/Release/net10.0", runtime)
    for name in ("Abstractions", "Core", "Hosting", "Application"):
        shutil.copy2(work / f"current/src/Hoard.{name}/bin/Release/net10.0/Hoard.{name}.dll", runtime)
    if (sha256(runtime / "RetainedMarker.dll") != retained["binarySha256"]
            or run("dotnet", str(runtime / "RetainedMarker.dll")).strip() != "metadata-marker-compatible"
            or any(sha256(proof_file(work, path)) != digest for path, digest in retained["files"].items())):
        raise RuntimeError("Frozen pre-F-05 metadata binary compatibility failed.")
    ownership = {
        "Hoard.Abstractions": "Abstractions", "Hoard.Core": "Core", "Hoard.Hosting": "Hosting",
        "Hoard.Application": "Application", "NuGet.Versioning": "Versioning",
        "Microsoft.Extensions.DependencyInjection.Abstractions": "Di",
        **{name: "Metadata" for name in ("Sqlite", "Memory", "BoundaryLeak")},
        **{name: "Host" for name in ("HostAdapters", "Consumer", "CrashRunner")},
        **{"Hoard.Fixtures.Metadata." + name: "Metadata" for name in ("Sqlite", "Memory")},
        "Hoard.Fixtures.Metadata.HostAdapters": "Host",
        **{name: "Sdk" for name in ("Microsoft.Data.Sqlite", "Microsoft.Data.Sqlite.Core",
            "SQLitePCLRaw.bundle_e_sqlite3", "SQLitePCLRaw.core", "SQLitePCLRaw.provider.e_sqlite3",
            "SQLitePCLRaw.lib.e_sqlite3", "System.Memory")}
    }
    graphs = []
    current = work / "current"
    projects = [("platform", [current / f"src/Hoard.{name}/Hoard.{name}.csproj"
                             for name in ("Abstractions", "Core", "Hosting", "Application")])]
    projects += [(scan, [current / f"tests/fixtures/metadata/{name}/{name}.csproj"])
                 for scan, name in (("sqlite", "Sqlite"), ("memory", "Memory"), ("host-adapters", "HostAdapters"),
                                    ("consumer", "Consumer"), ("crash-runner", "CrashRunner"), ("boundary-leak", "BoundaryLeak"))]
    previous = os.environ.get("NUGET_PACKAGES")
    os.environ["NUGET_PACKAGES"] = str(work / "cache")
    try:
        for scan, inputs in projects:
            graph = foundation.inspection_graph(inputs, ownership)
            graph["scanId"] = scan
            for project in graph["projects"]:
                if project["id"] in ("Sqlite", "Memory", "HostAdapters", "Consumer", "CrashRunner", "BoundaryLeak"):
                    project["assembly"] = str(Path(project["project"]).parent
                        / f"bin/Release/net10.0/Hoard.Fixtures.Metadata.{project['id']}.dll")
            graphs.append(graph)
    finally:
        if previous is None:
            os.environ.pop("NUGET_PACKAGES", None)
        else:
            os.environ["NUGET_PACKAGES"] = previous
    manifest = work / "metadata-boundaries.json"
    manifest.write_text(json.dumps({
        "graphs": graphs,
        "baselineAbstractions": str(work / "baseline/src/Hoard.Abstractions/bin/Release/net10.0/Hoard.Abstractions.dll"),
        "currentAbstractions": str(current / "src/Hoard.Abstractions/bin/Release/net10.0/Hoard.Abstractions.dll")}, indent=2))
    project = root / "tests/architecture/Hoard.Architecture.Tests/Hoard.Architecture.Tests.csproj"
    run("dotnet", "test", str(project), "-c", "Release", "--no-restore",
        "--filter", "FullyQualifiedName~MetadataBoundaryTests", "--logger", "trx;LogFileName=boundaries.trx",
        "--results-directory", str(work / "results"), "-v", "quiet",
        env={"HOARD_METADATA_BOUNDARIES": str(manifest)})
    tests = trx_results(work / "results/boundaries.trx")
    proof = write_proof(work, "compatibility.json", {
        "retainedBinarySha256": retained["binarySha256"], "baseline": BASELINE,
        "unchangedRetainedBinaryExecuted": True, "scans": [graph["scanId"] for graph in graphs], "tests": tests})
    return {"proof": proof, "tests": [test["test"] for test in tests] + ["frozen-pre-F05-binary"],
            "durationMs": sum(test["durationMs"] for test in tests)}


def verifier_cases(root, work):
    directory = work / "verifier-mutation"
    (directory / "scripts").mkdir(parents=True)
    (directory / "tests/tooling").mkdir(parents=True)
    for name in ("metadata_evidence.py", "foundation_evidence.py", "lifecycle_evidence.py"):
        shutil.copy2(root / "scripts" / name, directory / "scripts" / name)
    shutil.copy2(root / "tests/tooling/test_metadata_evidence.py", directory / "tests/tooling")
    source = directory / "scripts/metadata_evidence.py"
    baseline = sha256(source)
    original = source.read_text()
    needle = '\n        elif entry.get("result") != "Passed":\n'
    if original.count(needle) != 1:
        raise RuntimeError("Metadata verifier mutation target changed.")
    source.write_text(original.replace(needle, "\n        elif False:\n"))
    mutation = sha256(source)
    command = ["python3", "-m", "unittest", "discover", "-s", "tests/tooling", "-p", "test_metadata_evidence.py", "-v"]
    red = subprocess.run(command, cwd=directory, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    test = "test_stale_failed_unpaired_foreign_and_false_memory_durability_reject"
    if (red.returncode <= 0 or f"FAIL: {test}" not in red.stdout or "AssertionError" not in red.stdout
            or "ImportError" in red.stdout or "SyntaxError" in red.stdout):
        raise RuntimeError("Metadata verifier mutation did not produce its intended assertion failure.")
    source.write_text(original)
    run(*command, cwd=directory)
    red_green = {"id": "failed-case-refusal", "test": test, "redExit": red.returncode, "redOutcome": "Failed",
                 "redAssertion": True, "greenOutcome": "Passed", "mutationSha256": mutation, "baselineSha256": baseline}
    proof = write_proof(work, "qualification-verifier.json", {
        "positive": True, "negative": True, "redGreen": red_green,
        "suite": "test_metadata_evidence.py", "command": "python3 -m unittest discover -s tests/tooling -p test_metadata_evidence.py -v"})
    return {"proof": proof, "tests": ["MetadataEvidenceTests:positive-complete-and-negative-inventories", test],
            "durationMs": 0}, [red_green]


def runtime_red_green(work):
    directory = work / "runtime-mutation"
    source = directory / "current"
    source.mkdir(parents=True)
    current = work / "current"
    for name in ("Directory.Build.props", "Directory.Packages.props", "global.json"):
        shutil.copy2(current / name, source / name)
    relative = Path("tests/fixtures/metadata/Sqlite")
    foundation.copy_source(current / relative, source / relative)
    shutil.copy2(current / relative.parent / "Directory.Packages.props", source / relative.parent)
    worker = source / relative / "SqliteWorker.cs"
    original = worker.read_text()
    needle = """            if (Budget.Attempted && result is MetadataResult<T>.Failure)
            { result = Failure<T>(MetadataFailureCode.Uncertain, Phase, Ticket); }
"""
    if original.count(needle) != 1:
        raise RuntimeError("Metadata runtime mutation target changed.")
    baseline = sha256(worker)
    worker.write_text(original.replace(needle, ""))
    mutation = sha256(worker)
    project = source / relative / "Sqlite.csproj"
    environment = {"NUGET_PACKAGES": str(work / "cache")}
    run("dotnet", "restore", str(project), "--locked-mode", "--configfile", str(work / "NuGet.Config"),
        "-v", "quiet", env=environment)
    run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet", env=environment)
    output = directory / "tests"
    shutil.copytree(current / "tests/contracts/Hoard.Metadata.Tests/bin/Release/net10.0", output)
    sqlite = "Hoard.Fixtures.Metadata.Sqlite.dll"
    shutil.copy2(source / relative / "bin/Release/net10.0" / sqlite, output)
    test = "MP18_Known_exception_types_after_commit_attempt_are_still_uncertain"
    command = ["dotnet", "vstest", str(output / "Hoard.Metadata.Tests.dll"), f"/TestCaseFilter:FullyQualifiedName~{test}",
               f"/ResultsDirectory:{directory}", "/Logger:trx;LogFileName=red.trx"]
    environment.update({"HOARD_METADATA_PROVIDER": "sqlite", "HOARD_METADATA_WORKSPACE": str(work)})
    red = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600,
                         env={**os.environ, **environment})
    document = ET.parse(directory / "red.trx")
    results = document.findall(".//{*}UnitTestResult")
    message = document.findtext(".//{*}ErrorInfo/{*}Message", "")
    if (red.returncode <= 0 or len(results) != 1 or results[0].get("outcome") != "Failed"
            or test not in results[0].get("testName", "") or "Assert.Equal" not in message or "Uncertain" not in message):
        raise RuntimeError("Metadata runtime mutation did not produce its intended assertion failure.")
    shutil.copy2(current / "tests/contracts/Hoard.Metadata.Tests/bin/Release/net10.0" / sqlite, output)
    run(*command[:-1], "/Logger:trx;LogFileName=green.trx", env=environment)
    if len(trx_results(directory / "green.trx")) != 1:
        raise RuntimeError("Metadata runtime mutation green pair was incomplete.")
    evidence = {"id": "post-commit-classification", "test": test, "redExit": red.returncode,
                "redOutcome": "Failed", "redAssertion": True, "greenOutcome": "Passed",
                "mutationSha256": mutation, "baselineSha256": baseline}
    write_proof(work, "runtime-red-green.json", evidence)
    return evidence


def filesystem_type(work):
    if sys.platform == "darwin":
        rows = run("df", "-P", str(work)).splitlines()
        device = rows[-1].split()[0] if len(rows) >= 2 else ""
        if not device.startswith("/dev/"):
            raise RuntimeError("Metadata recovery requires a local block-device filesystem.")
        information = plistlib.loads(run("diskutil", "info", "-plist", device).encode())
        value = information.get("FilesystemType")
    elif sys.platform.startswith("linux"):
        value = run("stat", "-f", "-c", "%T", str(work)).strip()
    else:
        raise RuntimeError("Metadata filesystem qualification is not implemented for this operating system.")
    if not isinstance(value, str) or not value:
        raise RuntimeError("Metadata filesystem type could not be established.")
    if value.lower() not in ("apfs", "hfs", "ext2/ext3", "ext4", "xfs", "btrfs", "tmpfs", "overlayfs"):
        raise RuntimeError("Metadata recovery requires a recognized local filesystem.")
    return value


def qualify(root, work, prerequisites, phase):
    fingerprint = source_hash(root)
    verify_prerequisites(prerequisites, "logical", fingerprint)
    logical = logical_cases(work)
    prerequisites["logical"] = True
    if phase == "logical":
        return {"schemaVersion": 1, "sourceSha256": fingerprint, "qualification": False, "phase": phase,
                "logical": True, "providers": list(PROVIDERS)}
    verify_prerequisites(prerequisites, "recovery", fingerprint)
    durable, crashes, environment = recovery_cases(work)
    prerequisites["recovery"] = True
    if phase == "recovery":
        return {"schemaVersion": 1, "sourceSha256": fingerprint, "qualification": False, "phase": phase,
                "logical": True, "recovery": True}
    verify_prerequisites(prerequisites, "packages", fingerprint)
    compatibility = compatibility_cases(root, work)
    verifier, red_green = verifier_cases(root, work)
    red_green.append(runtime_red_green(work))
    run_id = uuid.uuid4().hex
    cases = []
    for provider in PROVIDERS:
        inventory = {**logical[provider], "MP-47": compatibility, "MP-48": verifier}
        if provider == "sqlite":
            inventory["MP-37"] = {
                "proof": write_proof(work, "MP-37.json", {"logical": logical[provider]["MP-37"], "native": durable["MP-37"]}),
                "tests": logical[provider]["MP-37"]["tests"] + durable["MP-37"]["tests"],
                "durationMs": logical[provider]["MP-37"]["durationMs"] + durable["MP-37"]["durationMs"]}
            inventory["MP-43"] = {
                "proof": write_proof(work, "MP-43.json", {"processOwnership": durable["MP-43"], "unchangedFutureLayout": logical[provider]["MP-33"]}),
                "tests": durable["MP-43"]["tests"] + logical[provider]["MP-33"]["tests"],
                "durationMs": durable["MP-43"]["durationMs"] + logical[provider]["MP-33"]["durationMs"]}
        for case in CASES:
            excluded = provider == "memory" and case in DURABLE_CASES
            proof = ({"proof": verifier["proof"], "tests": ["memory-durability-nonapplicability-and-overclaim-refusal"], "durationMs": 0}
                     if excluded else inventory.get(case) or durable[case])
            cases.append({**proof, "id": case, "provider": provider, "runId": run_id,
                "class": "D" if case in DURABLE_CASES else "L",
                "result": "NotApplicable" if excluded else "Passed",
                "reason": "non-durable fixture" if excluded else "",
                "positive": True, "negative": True, "sha256": sha256(proof_file(work, proof["proof"]))})
    evidence = {
        "schemaVersion": 1, "sourceSha256": fingerprint, "sourceCommit": run("git", "rev-parse", "HEAD", cwd=root).strip(),
        "runId": run_id, "production": False, "qualification": phase is None,
        "phase": phase or "all", "environment": {**environment, "filesystem": filesystem_type(work)},
        "configuration": {"journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0},
        "providers": provider_inventory(),
        "cases": cases, "crashes": crashes, "packages": prerequisites["packageInventory"], "redGreen": red_green,
        "limitations": ["Test fixtures only; not production providers or F-07 certification.",
            "SQLite process-stop recovery on the recorded local filesystem only, not device or power loss.",
            "Memory has no durable recovery; no other engine, filesystem or multi-node claim.",
            "Synthetic publication authority does not verify artifact bytes or authorize physical deletion."]}
    verify_manifest(evidence, work, fingerprint)
    if source_hash(root) != fingerprint:
        raise RuntimeError("Metadata source or lock inputs changed during qualification.")
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--update-locks", action="store_true")
    parser.add_argument("--phase", choices=("logical", "recovery", "packages"))
    parser.add_argument("--evidence", type=Path, help="Retain private proof in a fresh destination outside the repository.")
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
            if args.prepare_baseline is not None and args.prepare_only is not None or args.phase is not None or args.evidence is not None:
                raise RuntimeError("Metadata preparation selectors cannot be combined.")
            destination = (args.prepare_baseline or args.prepare_only).absolute()
            if (destination.exists() or destination.is_symlink() or not destination.parent.is_dir()
                    or destination.resolve().is_relative_to(root)):
                raise RuntimeError("Retained metadata baseline requires a fresh destination.")
            evidence = prepare_baseline(root, work, args.update_locks)
            if args.prepare_only is not None:
                prepare_packages(root, work, args.update_locks)
            retain_private_evidence(work, destination, root)
            print(json.dumps({"baseline": evidence["baseline"], "binarySha256": evidence["binarySha256"],
                              "qualification": False}))
        else:
            prepare_baseline(root, work, args.update_locks)
            prerequisites = prepare_packages(root, work, args.update_locks)
            verify_prerequisites(prerequisites, "logical", source_hash(root))
            run("dotnet", "restore", str(root / "Hoard.slnx"), "--locked-mode", "-v", "quiet")
            run("dotnet", "build", str(root / "Hoard.slnx"), "-c", "Release", "--no-restore", "-v", "quiet")
            if args.phase is None:
                run("dotnet", "format", str(root / "Hoard.slnx"), "--no-restore", "--verify-no-changes", "-v", "quiet")
                for project in sorted((work / "current/tests/fixtures/metadata").glob("*/*.csproj")):
                    if project.parent.name != "RetainedMarker":
                        run("dotnet", "format", str(project), "--no-restore", "--verify-no-changes", "-v", "quiet",
                            env={"NUGET_PACKAGES": str(work / "cache")})
            evidence = qualify(root, work, prerequisites, args.phase)
            if not args.update_locks:
                verify_locks(root, before)
            (work / "qualification.json").write_text(json.dumps(evidence, indent=2) + "\n")
            destination = (args.evidence.absolute() if args.evidence else work.with_name(work.name + "-evidence"))
            retain_private_evidence(work, destination, root)
            print(json.dumps({"qualification": evidence["qualification"], "phase": args.phase or "all",
                              "cases": len(evidence.get("cases", [])), "evidence": str(destination)}))
        if not args.update_locks:
            verify_locks(root, before)
    except (RuntimeError, OSError, ValueError):
        if args.evidence is not None:
            destination = args.evidence.absolute()
            if (not destination.exists() and not destination.is_symlink() and destination.parent.is_dir()
                    and not destination.resolve().is_relative_to(root)):
                retain_private_evidence(work, destination, root)
                print("Failed metadata run retained private diagnostics at " + str(destination), file=sys.stderr)
        raise
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
