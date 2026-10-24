"""Fail-closed orchestration for test-only F-06 qualification."""

import argparse
import base64
import binascii
import copy
import functools
import hashlib
import json
import math
import os
import platform
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
import uuid
from xml.etree import ElementTree

from artifact_case_catalog import required_runtime_tests

import foundation_evidence as foundation
import lifecycle_evidence as lifecycle
import metadata_evidence as metadata
from conformance_lock_preparation import prepare_project_lock, verify_project_lock

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
    "Fixtures.Artifacts.Local", "Fixtures.Artifacts.ObjectSemantics", "Fixtures.Artifacts.HostAdapters",
    "Testing.Conformance"))
CASE_BINDINGS = ("sourceSha256", "lockSha256", "configurationSha256",
                 "capabilitiesSha256", "environmentSha256", "packageSha256")
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
    runtime_proofs = {}
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
                or any(not isinstance(test, str) or not test.strip() for test in entry["tests"])
                or len(set(entry["tests"])) != len(entry["tests"])
                or any(not is_hash(entry.get(key)) for key in CASE_BINDINGS)):
            raise RuntimeError("Stale, unpaired or incomplete artifact case proof.")
        if not required_runtime_tests(entry["provider"], entry["id"]).issubset(entry["tests"]):
            raise RuntimeError("Artifact case is missing its required runtime witnesses.")
        path = proof_file(work, entry.get("proof"))
        if path.stat().st_size > 1048576:
            raise RuntimeError("Artifact case proof exceeds its finite report bound.")
        if sha256(path) != entry.get("sha256"):
            raise RuntimeError("Artifact case proof hash mismatch.")
        try:
            payload = json.loads(path.read_text())
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise RuntimeError("Malformed artifact case proof.") from None
        if (not isinstance(payload, dict) or type(payload.get("schemaVersion")) is not int or payload["schemaVersion"] != 1
                or any(payload.get(key) != entry.get(key) for key in (
                    "id", "provider", "class", "runId", "result", *CASE_BINDINGS))
                or not isinstance(payload.get("subproofs"), list) or len(payload["subproofs"]) != 2
                or any(not isinstance(value, dict) or not isinstance(value.get("id"), str)
                       for value in payload["subproofs"])
                or {value["id"] for value in payload["subproofs"]} != {"positive", "negative"}):
            raise RuntimeError("Foreign, stale or unattributed artifact case proof.")
        witnessed = {}
        for subproof in payload["subproofs"]:
            names = subproof.get("tests")
            if (subproof.get("result") != "Passed" or not isinstance(names, list) or not names
                    or any(not isinstance(name, str) for name in names) or len(set(names)) != len(names)
                    or not set(names).issubset(entry["tests"])):
                raise RuntimeError("Missing or failed artifact runtime subproof.")
            witness = proof_file(work, subproof.get("proof"))
            if witness.stat().st_size > 16777216:
                raise RuntimeError("Artifact runtime witness exceeds its finite report bound.")
            digest = sha256(witness)
            if digest != subproof.get("sha256"):
                raise RuntimeError("Artifact runtime subproof hash mismatch.")
            cache_key = (witness, digest)
            if cache_key not in runtime_proofs:
                try:
                    results = metadata.trx_results(witness)
                except (OSError, UnicodeError, ElementTree.ParseError, ValueError, RuntimeError):
                    raise RuntimeError("Missing, malformed, failed or skipped artifact runtime witness.") from None
                if (len({result["test"] for result in results}) != len(results)
                        or any(not math.isfinite(result["durationMs"]) or result["durationMs"] < 0 for result in results)):
                    raise RuntimeError("Duplicate or invalid-duration artifact runtime witness.")
                runtime_proofs[cache_key] = {result["test"]: result["durationMs"] for result in results}
            for name in names:
                if name not in runtime_proofs[cache_key]:
                    raise RuntimeError("Artifact case names an unexecuted runtime witness.")
                witnessed[(witness, name)] = runtime_proofs[cache_key][name]
        if ({name for _, name in witnessed} != set(entry["tests"])
                or not math.isclose(sum(witnessed.values()), entry["durationMs"], rel_tol=1e-9, abs_tol=0.01)):
            raise RuntimeError("Artifact case runtime inventory or duration is unattributed.")


def is_hash(value):
    return isinstance(value, str) and re.fullmatch("[a-f0-9]{64}", value) is not None


def verify_transfer(proof, provider, size, run_id, *, peak_methods=("getrusage", "time-l", "time-v")):
    numeric = ("pid", "size", "written", "read", "baselineRssBytes", "osPeakRssBytes",
               "sampledPeakRssBytes", "samples", "bufferBytes", "providerBufferLimit", "slots", "exitCode")
    if (not isinstance(proof, dict) or any(type(proof.get(key)) is not int for key in numeric)
            or proof.get("provider") != provider or proof.get("runId") != run_id
            or proof["pid"] <= 0 or proof["exitCode"] != 0
            or size not in (268435456, 4294967296)
            or any(proof[key] != size for key in ("size", "written", "read"))
            or not is_hash(proof.get("expectedSha256"))
            or any(proof.get(key) != proof["expectedSha256"] for key in ("sourceSha256", "sinkSha256"))
            or proof.get("rssUnits") != "bytes" or proof.get("osPeakMethod") not in peak_methods
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


def write_proof(work, name, value):
    path = work / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")
    return {"proof": name, "sha256": sha256(path)}


def read_proof(work, reference, maximum=1048576):
    if not isinstance(reference, dict):
        raise RuntimeError("Artifact input attribution is missing.")
    path = proof_file(work, reference.get("proof"))
    if path.stat().st_size > maximum or sha256(path) != reference.get("sha256"):
        raise RuntimeError("Artifact input proof is oversized or hash-altered.")
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise RuntimeError("Artifact input proof is malformed.") from None


def verify_input_bindings(evidence, work, source_digest):
    inputs = evidence.get("inputs")
    if not isinstance(inputs, dict):
        raise RuntimeError("Artifact qualification is missing its actual input bindings.")
    locks = read_proof(work, inputs.get("locks"))
    environment = read_proof(work, inputs.get("environment"))
    if (not isinstance(locks, dict) or not locks or not isinstance(environment, dict)
            or any(not isinstance(name, str) or not is_hash(digest) for name, digest in locks.items())
            or environment != evidence.get("environment")
            or any(not isinstance(environment.get(key), str) or not 0 < len(environment[key]) <= 256
                   or not environment[key].strip() or any(not 32 <= ord(char) <= 126 for char in environment[key])
                   for key in ("os", "runtime", "filesystem", "flushConfiguration"))):
        raise RuntimeError("Artifact lock/environment input is invalid.")
    contexts = inputs.get("contexts")
    if (not isinstance(contexts, list) or len(contexts) != 2
            or any(not isinstance(value, dict) for value in contexts)
            or {value.get("id") for value in contexts} != set(PROVIDERS)):
        raise RuntimeError("Artifact qualification requires both actual admission contexts.")
    environment_hash = hashlib.sha256("\n".join(environment[key] for key in (
        "os", "runtime", "filesystem", "flushConfiguration")).encode()).hexdigest()
    bindings = {}
    for reference in contexts:
        provider = reference["id"]
        context = read_proof(work, reference)
        capabilities = read_proof(work, reference.get("capabilities"))
        configuration = read_proof(work, reference.get("configuration"))
        if (not isinstance(context, dict) or not isinstance(capabilities, dict) or not isinstance(configuration, dict)
                or context.get("capabilities") != capabilities or context.get("configuration") != configuration
                or context.get("implementationId") != f"fixture.artifact.{provider}"
                or context.get("runtime") != environment["runtime"]
                or capabilities.get("Version") != 1 or capabilities.get("MeetsBaseline") is not True
                or capabilities.get("Durability") != (0 if provider == "local" else 1)
                or capabilities.get("Enumeration") != (0 if provider == "local" else 1)
                or capabilities.get("RangeReads") is not False or capabilities.get("Sha512") is not True
                or any(capabilities.get(key) is not True for key in (
                    "ConditionalPublication", "ConditionalDeletion", "StagingRecovery", "OwnerFencing",
                    "ReaderProtection", "BoundedStreaming"))
                or not isinstance(capabilities.get("Limits"), dict)
                or configuration.get("limits") != capabilities["Limits"]):
            raise RuntimeError("Artifact admission/capability inputs are inconsistent or unsupported.")
        package = f"Hoard.Fixtures.Artifacts.{'Local' if provider == 'local' else 'ObjectSemantics'}.0.1.0.nupkg"
        matching = [value for value in evidence["packages"] if value["id"] == package]
        if len(matching) != 1:
            raise RuntimeError("Artifact selected implementation package is missing.")
        bindings[provider] = {
            "sourceSha256": source_digest, "lockSha256": inputs["locks"]["sha256"],
            "environmentSha256": environment_hash, "packageSha256": matching[0]["sha256"],
            "configurationSha256": reference["configuration"]["sha256"],
            "capabilitiesSha256": reference["capabilities"]["sha256"]}
    for entry in evidence["cases"]:
        if any(entry.get(key) != digest for key, digest in bindings[entry["provider"]].items()):
            raise RuntimeError("Artifact case does not bind its actual qualification inputs.")
    return bindings


def verify_execution_proofs(evidence, work):
    if (evidence.get("lockMode") != "locked" or not isinstance(evidence.get("command"), list)
            or evidence["command"][:2] != ["bash", "scripts/validate-artifacts.sh"]):
        raise RuntimeError("Artifact qualification requires its exact locked command.")
    for proof in evidence["transfers"]:
        stored = read_proof(work, proof)
        if stored != {key: value for key, value in proof.items() if key not in ("proof", "sha256", "measurement")}:
            raise RuntimeError("Artifact transfer is not bound to its actual measured child output.")
        measurement = proof.get("measurement")
        if not isinstance(measurement, dict):
            raise RuntimeError("Artifact transfer has no OS measurement capture.")
        path = proof_file(work, measurement.get("proof"))
        if path.stat().st_size > 16384 or sha256(path) != measurement.get("sha256"):
            raise RuntimeError("Artifact OS measurement capture is missing or altered.")
        pattern = (r"^\s*(\d+)\s+maximum resident set size\s*$" if proof["osPeakMethod"] == "time-l"
                   else r"Maximum resident set size \(kbytes\):\s*(\d+)")
        matched = re.search(pattern, path.read_text(), re.MULTILINE)
        if (not matched or int(matched[1]) * (1 if proof["osPeakMethod"] == "time-l" else 1024) != proof["osPeakRssBytes"]
                or proof["expectedSha256"] != expected_transfer_hash(proof["size"])
                or proof["runtime"] != evidence["environment"]["runtime"]):
            raise RuntimeError("Artifact transfer peak, digest or runtime disagrees with its actual inputs.")
    for proof in evidence["crashes"]:
        stored = read_proof(work, proof)
        if stored != {key: value for key, value in proof.items() if key not in ("proof", "sha256")}:
            raise RuntimeError("Artifact crash is not bound to its actual parent observation.")
        state = read_proof(work, {"proof": f"crash-{proof['barrier']}/state.json", "sha256": proof["stateSha256"]})
        validate_recovery_readback(proof["observed"], state, proof["barrier"], evidence["runId"], proof["reopenPid"])
    for pair in evidence["redGreen"]:
        if pair.get("kind") not in ("runtime", "verifier"):
            raise RuntimeError("Artifact qualification requires actually executed mutation pairs.")
        for state, digest in (("baseline", pair["baselineSha256"]), ("mutation", pair["mutationSha256"])):
            if sha256(proof_file(work, pair.get(state))) != digest:
                raise RuntimeError("Artifact mutation input is missing or hash-altered.")
        if pair["kind"] == "runtime":
            red = proof_file(work, pair.get("redProof"))
            green = proof_file(work, pair.get("greenProof"))
            if sha256(red) != pair.get("redProofSha256") or sha256(green) != pair.get("greenProofSha256"):
                raise RuntimeError("Artifact mutation execution proof was altered.")
            results = ElementTree.parse(red).findall(".//{*}UnitTestResult")
            result = next((result for result in results if result.get("testName") == pair["test"]), None)
            if (result is None or result.get("outcome") != "Failed"
                    or "Assert." not in result.findtext(".//{*}Message", "")
                    or pair["test"] not in {result["test"] for result in metadata.trx_results(green)}):
                raise RuntimeError("Artifact mutation pair lacks its exact failed assertion and green execution.")
        else:
            capture = read_proof(work, pair.get("execution"))
            if (capture.get("redExit") != pair["redExit"] or capture.get("greenExit") != 0
                    or f"FAIL: {pair['test']}" not in capture.get("redOutput", "")
                    or "AssertionError" not in capture["redOutput"]):
                raise RuntimeError("Artifact verifier mutation did not execute its intended assertion.")
    if {pair["id"] for pair in evidence["redGreen"]} != {
            "local-capability-admission", "object-capability-admission", "case-context-binding"}:
        raise RuntimeError("Artifact mutation execution inventory is incomplete.")
    records = evidence.get("qualificationRecords")
    if (not isinstance(records, list) or len(records) != 2
            or {record.get("id") for record in records} != set(PROVIDERS)):
        raise RuntimeError("Both materialized public qualification records are required.")
    for reference in records:
        record = read_proof(work, reference)
        cases = [case for case in evidence["cases"] if case["provider"] == reference["id"]]
        context = next(value for value in evidence["inputs"]["contexts"] if value["id"] == reference["id"])
        environment = {key: evidence["environment"][name] for key, name in (
            ("OperatingSystem", "os"), ("Runtime", "runtime"), ("FileSystem", "filesystem"),
            ("FlushConfiguration", "flushConfiguration"))}
        environment["Sha256"] = cases[0]["environmentSha256"]
        if (record.get("ImplementationId") != f"fixture.artifact.{reference['id']}"
                or record.get("PackageVersion") != "0.1.0"
                or record.get("Capabilities") != read_proof(work, context["capabilities"])
                or record.get("Environment") != environment
                or record.get("CaseIds") != [case["id"] for case in cases]
                or set(record.get("ProofHashes", [])) != {case["sha256"] for case in cases}
                or any(record.get(field) != cases[0][field[0].lower() + field[1:]]
                       for field in ("SourceSha256", "LockSha256", "ConfigurationSha256", "PackageSha256", "EnvironmentSha256"))
                or record.get("Exclusions") != (["AS-41", "AS-42", "AS-43", "AS-44"] if reference["id"] == "object" else [])
                or not isinstance(record.get("CaseResults"), list) or len(record["CaseResults"]) != 48):
            raise RuntimeError("Materialized public qualification record is incomplete or foreign.")
        expected = {case["id"]: case for case in cases}
        for result in record["CaseResults"]:
            case = expected.pop(result.get("CaseId"), None)
            duration = result.get("Duration", "").split(":")
            milliseconds = ((int(duration[0]) * 3600 + int(duration[1]) * 60 + float(duration[2])) * 1000
                            if len(duration) == 3 else -1)
            if (case is None or result.get("Status") != (1 if case["result"] == "NotApplicable" else 0)
                    or result.get("ProofHashes") != [case["sha256"]]
                    or not math.isclose(milliseconds, case["durationMs"], rel_tol=1e-9, abs_tol=0.01)):
                raise RuntimeError("Materialized qualification case is unexecuted or unattributed.")


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
    if any(entry["sourceSha256"] != source_digest for entry in evidence["cases"]):
        raise RuntimeError("Artifact case source attribution is stale.")
    verify_files(evidence.get("packages"), work, PACKAGES)
    verify_input_bindings(evidence, work, source_digest)
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
    verify_execution_proofs(evidence, work)


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
    metadata_work = work / "metadata-packages"
    metadata_work.mkdir()
    metadata.prepare_packages(root, metadata_work, update)
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
    sdk = "Hoard.Testing.Conformance.0.1.0.nupkg"
    shutil.copy2(metadata_work / "feed" / sdk, feed / sdk)
    from xml.sax.saxutils import escape
    config.write_text(
        '<configuration><packageSources><clear/>'
        f'<add key="local" value="{escape(str(feed))}"/>'
        '<add key="nuget.org" value="https://api.nuget.org/v3/index.json"/>'
        '</packageSources><packageSourceMapping><packageSource key="local">'
        '<package pattern="Hoard.*"/></packageSource><packageSource key="nuget.org">'
        '<package pattern="*"/></packageSource></packageSourceMapping></configuration>')
    derivations = []

    def build(relative, pack=False, properties=()):
        project = current / relative
        record = None
        if not update:
            lock, record = prepare_project_lock(
                project, current, feed, "artifacts-current",
                acceptance="-p:ArtifactPackageAcceptance=true" in properties)
            if lock is not None:
                properties = (*properties, "-p:NuGetLockFilePath=" + str(lock))
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
        if record is not None:
            verify_project_lock(record, current, feed)
            derivations.append(record)

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
              "baseline": True, "packages": packages, "locks": lock_hashes(root),
              "lockDerivations": derivations}
    (work / "prerequisites.json").write_text(json.dumps(inputs, indent=2) + "\n")
    return inputs


def focused_tests(work, selection, *, name="artifacts", environment=None):
    project = work / "current/tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj"
    results = work / "results"
    arguments = ["dotnet", "test", str(project), "-c", "Release", "--no-build", "--no-restore",
                 "-p:ArtifactPackageAcceptance=true", "--logger", f"trx;LogFileName={name}.trx",
                 "--results-directory", str(results), "-v", "quiet"]
    if selection:
        arguments += ["--filter", selection]
    output = run(*arguments, env={
        "HOARD_ARTIFACT_TEST_ROOT": str(work / "case-roots"),
        "HOARD_METADATA_WORKSPACE": str(work / "metadata-roots"),
        "HOARD_ARTIFACT_CRASH_PROOFS": str(work / "crashes"),
        "HOARD_ARTIFACT_CRASH_RUNNER": str(work / "current/tests/fixtures/artifacts/CrashRunner/bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll"),
        **(environment or {})})
    (work / f"{name}-tests.txt").write_text(output)
    return lifecycle.test_count(results / f"{name}.trx")


def consumer_journeys(work):
    binary = work / "current/tests/fixtures/artifacts/Consumer/bin/Release/net10.0/Hoard.Fixtures.Artifacts.Consumer.dll"
    journeys = []
    for provider in PROVIDERS:
        result = json.loads(run("dotnet", str(binary), provider, str(work / f"consumer-{provider}"),
                                env={"HOARD_ARTIFACT_CONTEXT_PATH": str(work / f"context-{provider}.json")}))
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


@functools.lru_cache(maxsize=2)
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


def mutation_pairs(root, work):
    pairs = []
    tests = work / "current/tests/contracts/Hoard.Artifacts.Tests/bin/Release/net10.0"
    for provider, module in (("local", "Local"), ("object", "ObjectSemantics")):
        directory = work / f"mutation-{provider}"
        source = directory / "current"
        source.mkdir(parents=True)
        for name in ("Directory.Build.props", "Directory.Packages.props", "global.json"):
            shutil.copy2(work / "current" / name, source / name)
        relative = Path(f"tests/fixtures/artifacts/{module}")
        foundation.copy_source(work / "current" / relative, source / relative)
        shutil.copy2(work / "current/tests/fixtures/artifacts/Directory.Packages.props", source / relative.parent)
        implementation = source / relative / f"{module if provider == 'local' else 'Object'}ArtifactStore.cs"
        original = implementation.read_text()
        needle = "if (!Capabilities.MeetsBaseline || Capabilities.Limits != request.Limits"
        if original.count(needle) != 1:
            raise RuntimeError("Artifact admission mutation target changed.")
        baseline = directory / "baseline.cs"
        baseline.write_text(original)
        implementation.write_text(original.replace(needle, "if (Capabilities.Version < 0 || Capabilities.Limits != request.Limits"))
        mutation = directory / "mutation.cs"
        shutil.copy2(implementation, mutation)
        project = source / relative / f"{module}.csproj"
        environment = {"NUGET_PACKAGES": str(work / "cache"), "HOARD_ARTIFACT_TEST_ROOT": str(directory / "roots")}
        run("dotnet", "restore", str(project), "--locked-mode", "--configfile", str(work / "NuGet.Config"),
            "-v", "quiet", env=environment)
        run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet", env=environment)
        output = directory / "tests"
        shutil.copytree(tests, output)
        assembly = f"Hoard.Fixtures.Artifacts.{module}.dll"
        shutil.copy2(project.parent / "bin/Release/net10.0" / assembly, output)
        method = "Missing_mandatory_guarantees_versions_or_authority_reject_before_io"
        command = ["dotnet", "vstest", str(output / "Hoard.Artifacts.Tests.dll"),
                   f"/TestCaseFilter:FullyQualifiedName~{method}", f"/ResultsDirectory:{directory}"]
        red = subprocess.run([*command, "/Logger:trx;LogFileName=red.trx"], text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600,
                             env={**os.environ, **environment})
        (directory / "red.txt").write_text(red.stdout)
        test = next(name for name in required_runtime_tests(provider, "AS-38") if 'gap: "streaming"' in name)
        document = ElementTree.parse(directory / "red.trx")
        result = next((result for result in document.findall(".//{*}UnitTestResult")
                       if result.get("testName") == test), None)
        if (red.returncode <= 0 or result is None or result.get("outcome") != "Failed"
                or "Assert.IsType" not in result.findtext(".//{*}Message", "")):
            raise RuntimeError("Artifact runtime mutation missed its intended assertion.")
        shutil.copy2(tests / assembly, output)
        run(*command, "/Logger:trx;LogFileName=green.trx", env=environment)
        if test not in {result["test"] for result in metadata.trx_results(directory / "green.trx")}:
            raise RuntimeError("Artifact runtime mutation has no matching green.")
        pairs.append({
            "id": f"{provider}-capability-admission", "kind": "runtime", "test": test,
            "redExit": red.returncode, "redOutcome": "Failed", "redAssertion": True, "greenOutcome": "Passed",
            "baseline": baseline.relative_to(work).as_posix(), "baselineSha256": sha256(baseline),
            "mutation": mutation.relative_to(work).as_posix(), "mutationSha256": sha256(mutation),
            "redProof": (directory / "red.trx").relative_to(work).as_posix(),
            "redProofSha256": sha256(directory / "red.trx"),
            "greenProof": (directory / "green.trx").relative_to(work).as_posix(),
            "greenProofSha256": sha256(directory / "green.trx")})
    directory = work / "mutation-verifier"
    (directory / "scripts").mkdir(parents=True)
    (directory / "tests/tooling").mkdir(parents=True)
    for path in (root / "scripts").glob("*.py"):
        shutil.copy2(path, directory / "scripts")
    shutil.copy2(root / "tests/tooling/test_artifact_evidence.py", directory / "tests/tooling")
    implementation = directory / "scripts/artifact_evidence.py"
    original = implementation.read_text()
    needle = '\n        if any(entry.get(key) != digest for key, digest in bindings[entry["provider"]].items()):\n'
    if original.count(needle) != 1:
        raise RuntimeError("Artifact context-binding mutation target changed.")
    baseline = directory / "baseline.py"
    baseline.write_text(original)
    implementation.write_text(original.replace(needle, '\n        if any(False for key, digest in bindings[entry["provider"]].items()):\n'))
    mutation = directory / "mutation.py"
    shutil.copy2(implementation, mutation)
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests/tooling", "-p", "test_artifact_evidence.py", "-v"]
    red = subprocess.run(command, cwd=directory, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    test = "test_matching_outer_and_inner_bindings_cannot_replace_actual_inputs"
    if (red.returncode <= 0 or f"FAIL: {test}" not in red.stdout or "AssertionError" not in red.stdout
            or "ImportError" in red.stdout or "SyntaxError" in red.stdout):
        raise RuntimeError("Artifact verifier mutation missed its intended assertion.")
    implementation.write_text(original)
    green = run(*command, cwd=directory)
    pairs.append({
        "id": "case-context-binding", "kind": "verifier", "test": test, "redExit": red.returncode,
        "redOutcome": "Failed", "redAssertion": True, "greenOutcome": "Passed",
        "baseline": baseline.relative_to(work).as_posix(), "baselineSha256": sha256(baseline),
        "mutation": mutation.relative_to(work).as_posix(), "mutationSha256": sha256(mutation),
        "execution": write_proof(work, "mutation-verifier/execution.json", {
            "command": command, "redExit": red.returncode, "greenExit": 0, "redOutput": red.stdout, "greenOutput": green})})
    verify_red_green(pairs)
    return pairs


def qualification_inputs(root, work, packages):
    contexts = []
    runtimes = set()
    for provider in PROVIDERS:
        path = work / f"context-{provider}.json"
        context = json.loads(path.read_text())
        runtimes.add(context["runtime"])
        contexts.append({
            "id": provider, "proof": path.name, "sha256": sha256(path),
            "capabilities": write_proof(work, f"capabilities-{provider}.json", context["capabilities"]),
            "configuration": write_proof(work, f"configuration-{provider}.json", context["configuration"])})
    if len(runtimes) != 1:
        raise RuntimeError("Artifact consumers did not execute the same runtime.")
    environment = {
        "os": platform.platform(), "runtime": next(iter(runtimes)), "filesystem": metadata.filesystem_type(work),
        "flushConfiguration": "Local payload/decision Flush(true), no directory fsync; object process-local simulation"}
    inputs = {"locks": write_proof(work, "locks.json", lock_hashes(root)), "contexts": contexts,
              "environment": write_proof(work, "environment.json", environment)}
    bindings = verify_input_bindings({
        "inputs": inputs, "environment": environment, "packages": packages, "cases": []}, work, source_hash(root))
    return inputs, environment, bindings


def qualification_cases(work, run_id, bindings):
    executions = {}
    for name in ("artifacts", "transfer-proofs", "artifact-boundaries"):
        reference = f"results/{name}.trx"
        for result in metadata.trx_results(work / reference):
            if result["test"] in executions:
                raise RuntimeError("Artifact qualification has ambiguous duplicate runtime witnesses.")
            executions[result["test"]] = {**result, "proof": reference}
    cases = []
    for provider in PROVIDERS:
        for case in CASES:
            number = int(case[3:])
            excluded = provider == "object" and 41 <= number <= 44
            names = sorted(required_runtime_tests(provider, case))
            if not set(names).issubset(executions):
                raise RuntimeError(f"Artifact {provider}/{case} has an unexecuted required runtime witness.")
            grouped = {}
            for name in names:
                grouped.setdefault(executions[name]["proof"], []).append(name)
            if len(grouped) > 2:
                raise RuntimeError("Artifact runtime case exceeds its paired witness inventory.")
            groups = list(grouped.items())
            if len(groups) == 1:
                groups *= 2
            subproofs = [{"id": role, "result": "Passed", "tests": tests, "proof": path, "sha256": sha256(work / path)}
                         for role, (path, tests) in zip(("positive", "negative"), groups)]
            entry = {
                "id": case, "provider": provider, "class": "L" if number <= 40 else "D" if number <= 44 else "Q",
                "runId": run_id, "result": "NotApplicable" if excluded else "Passed",
                "reason": "simulation: no durable restart" if excluded else "",
                "positive": True, "negative": True, "tests": names,
                "durationMs": sum(executions[name]["durationMs"] for name in names), **bindings[provider]}
            entry.update(write_proof(work, f"cases/{provider}-{case}.json", {
                "schemaVersion": 1, **{key: entry[key] for key in (
                    "id", "provider", "class", "runId", "result", *CASE_BINDINGS)}, "subproofs": subproofs}))
            cases.append(entry)
    verify_cases(cases, work, run_id)
    return cases


def negative_manifests(evidence, work):
    mutations = []
    for field, value in (("production", True), ("phase", "logical"), ("lockMode", "update"),
                         ("sourceSha256", "0" * 64), ("runId", "foreign")):
        changed = copy.deepcopy(evidence)
        changed[field] = value
        mutations.append((field, changed))
    for name, cases in (("missing-case", evidence["cases"][:-1]),
                        ("duplicate-case", [*evidence["cases"][:-1], evidence["cases"][0]])):
        changed = copy.deepcopy(evidence)
        changed["cases"] = cases
        mutations.append((name, changed))
    for field, value in (("provider", "foreign"), ("result", "Failed"), ("result", "Skipped"),
                         ("durationMs", -1), ("packageSha256", "0" * 64),
                         ("configurationSha256", "0" * 64), ("capabilitiesSha256", "0" * 64),
                         ("environmentSha256", "0" * 64), ("lockSha256", "0" * 64)):
        changed = copy.deepcopy(evidence)
        changed["cases"][0][field] = value
        mutations.append((f"case-{field}-{value}", changed))
    for section, field, value in (
            ("transfers", "written", 0), ("transfers", "osPeakRssBytes", 2 ** 60),
            ("transfers", "sha256", "0" * 64), ("crashes", "exitCode", 0),
            ("crashes", "reopenPid", evidence["crashes"][0]["pid"]),
            ("crashes", "sha256", "0" * 64), ("packages", "sha256", "0" * 64)):
        changed = copy.deepcopy(evidence)
        changed[section][0][field] = value
        mutations.append((f"{section}-{field}", changed))
    for index, field, value in (
            (0, "Capabilities", {}), (0, "Environment", {}), (0, "CaseIds", []),
            (1, "Exclusions", []), (0, "SourceSha256", "0" * 64)):
        changed = copy.deepcopy(evidence)
        reference = changed["qualificationRecords"][index]
        record = read_proof(work, reference)
        record[field] = value
        reference.update(write_proof(work, f"negative-records/{index}-{field}.json", record))
        mutations.append((f"record-{index}-{field}", changed))
    changed = copy.deepcopy(evidence)
    reference = changed["qualificationRecords"][0]
    record = read_proof(work, reference)
    record["CaseResults"][0]["Duration"] = "00:00:00"
    reference.update(write_proof(work, "negative-records/duration.json", record))
    mutations.append(("record-duration", changed))
    for name, changed in mutations:
        try:
            verify_manifest(changed, work, evidence["sourceSha256"])
        except RuntimeError:
            continue
        raise RuntimeError(f"Artifact verifier accepted the actual {name} mutation.")
    return write_proof(work, "negative-manifests.json", {
        "schemaVersion": 1, "sourceSha256": evidence["sourceSha256"], "runId": evidence["runId"],
        "tests": [{"id": name, "result": "Passed"} for name, _ in mutations]})


def qualify(root, work, prerequisites):
    fingerprint = source_hash(root)
    locks = lock_hashes(root)
    if prerequisites["sourceSha256"] != fingerprint:
        raise RuntimeError("Artifact prepared source fingerprint drifted.")
    run_id = str(uuid.uuid4())
    focused_tests(work, "FullyQualifiedName~Artifact&FullyQualifiedName!~ArtifactTransferProofTests")
    transfers = measured_transfers(work, run_id)
    focused_tests(work, "FullyQualifiedName~ArtifactTransferProofTests", name="transfer-proofs",
                  environment={"HOARD_ARTIFACT_TRANSFER_PROOFS": str(work), "HOARD_ARTIFACT_RUN_ID": run_id})
    crashes = [crash_recovery(work, barrier, run_id) for barrier in BARRIERS]
    package_checks(root, work)
    inputs, environment, bindings = qualification_inputs(root, work, prerequisites["packages"])
    cases = qualification_cases(work, run_id, bindings)
    pairs = mutation_pairs(root, work)
    records = []
    binary = work / "current/tests/fixtures/artifacts/Consumer/bin/Release/net10.0/Hoard.Fixtures.Artifacts.Consumer.dll"
    for provider in PROVIDERS:
        request = {
            "implementationId": f"fixture.artifact.{provider}", **bindings[provider], "environment": environment,
            "capabilities": json.loads((work / f"capabilities-{provider}.json").read_text()),
            "cases": [case for case in cases if case["provider"] == provider]}
        reference = write_proof(work, f"qualification-request-{provider}.json", request)
        output = run("dotnet", str(binary), "qualification", str(work / reference["proof"]))
        records.append({"id": provider, **write_proof(work, f"qualification-record-{provider}.json", json.loads(output))})
    for path in ("src", "tests/contracts/Hoard.Artifacts.Tests", "tests/fixtures/artifacts"):
        run("dotnet", "format", "whitespace", str(root / path), "--folder", "--verify-no-changes", "--verbosity", "quiet")
    project = work / "current/tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj"
    run("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-p:ArtifactPackageAcceptance=true",
        "-p:RunAnalyzersDuringBuild=true", "-v", "quiet", env={"NUGET_PACKAGES": str(work / "cache")})
    if fingerprint != source_hash(root) or locks != lock_hashes(root):
        raise RuntimeError("Artifact qualification inputs changed during execution.")
    evidence = {
        "schemaVersion": 1, "qualification": True, "production": False, "phase": "full", "lockMode": "locked",
        "command": ["bash", "scripts/validate-artifacts.sh", "--evidence", str(work)],
        "runId": run_id, "sourceSha256": fingerprint, "baselineRevision": BASELINE,
        "environment": environment, "inputs": inputs, "packages": prerequisites["packages"],
        "cases": cases, "redGreen": pairs, "qualificationRecords": records,
        "limitations": ["Test-only independent fixtures, not a production cache/provider or F-07 certification.",
                        "Only the recorded local process-crash environment; no power-loss/remote-service/HA claim.",
                        "Object simulation has no durable restart; AS-41..44 are explicitly not applicable.",
                        "Measured transfers run one at a time with one slot and fixed 256 KiB/2 MiB buffers."],
        "transfers": [{**proof, "proof": f"transfer-{proof['provider']}-{proof['size']}/proof.json",
                       "sha256": sha256(work / f"transfer-{proof['provider']}-{proof['size']}/proof.json"),
                       "measurement": {"proof": f"transfer-{proof['provider']}-{proof['size']}/time.txt",
                                       "sha256": sha256(work / f"transfer-{proof['provider']}-{proof['size']}/time.txt")}}
                      for proof in transfers],
        "crashes": [{**proof, "proof": f"crash-{proof['barrier']}/proof.json",
                     "sha256": sha256(work / f"crash-{proof['barrier']}/proof.json")} for proof in crashes]}
    verify_manifest(evidence, work, fingerprint)
    evidence["negativeValidation"] = negative_manifests(evidence, work)
    return evidence


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
        prerequisites = prepare_packages(root, work, args.update_locks)
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
            count = focused_tests(work, "FullyQualifiedName~ArtifactTransferProofTests", name="transfer-proofs",
                                  environment={"HOARD_ARTIFACT_TRANSFER_PROOFS": str(work), "HOARD_ARTIFACT_RUN_ID": run_id})
            evidence = {"schemaVersion": 1, "qualification": False, "phase": args.phase,
                        "runId": run_id, "sourceSha256": source_hash(root), "transfers": transfers, "testsPassed": count}
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
            selection = ("FullyQualifiedName~Artifact&FullyQualifiedName!~ArtifactCrashTests&FullyQualifiedName!~ArtifactTransferProofTests" if args.phase == "logical"
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
        if args.update_locks:
            raise RuntimeError("Full artifact qualification requires a separate default locked replay.")
        evidence = qualify(root, work, prerequisites)
        (work / "manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps({"schemaVersion": 1, "qualification": True, "phase": "full",
                          "sourceSha256": evidence["sourceSha256"], "runId": evidence["runId"],
                          "passed": sum(case["result"] == "Passed" for case in evidence["cases"]),
                          "notApplicable": sum(case["result"] == "NotApplicable" for case in evidence["cases"])}))
        return 0
    except Exception as error:
        (work / "failure.json").write_text(json.dumps({
            "schemaVersion": 1, "qualification": False, "phase": args.phase or "full",
            "error": str(error) if isinstance(error, RuntimeError) else "Artifact preparation failed.",
        }, indent=2) + "\n")
        print("Artifact acceptance failed; private failure evidence retained.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
