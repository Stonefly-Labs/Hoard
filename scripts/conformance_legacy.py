"""Bounded legacy command transport; raw child diagnostics never reach evidence."""

import hashlib
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
import threading
import uuid
import xml.etree.ElementTree as ET
import zipfile

from conformance_evidence import ConformanceError, admit_entity, canonical_bytes, load_json
from conformance_execution import (
    READ_BYTES, TRANSIENT_BYTES, no_symlinks, process_group, project_build_line, project_test_line,
)
from conformance_sources import read_bounded, runtime_arguments, runtime_settings

FQN_TERM = re.compile(r"FullyQualifiedName(!~|~|=)([a-zA-Z0-9_.]+)")
_retained_children = {}


def _settle_group(child):
    deadline = time.monotonic() + 10
    try:
        while process_group(child.pid, deadline=deadline):
            if time.monotonic() >= deadline:
                raise RuntimeError("Legacy command cleanup incomplete.")
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            time.sleep(0.01)
        child.wait(timeout=max(0.001, deadline - time.monotonic()))
    except (OSError, RuntimeError, ConformanceError, subprocess.SubprocessError):
        _retained_children[child.pid] = child
        raise RuntimeError("Legacy command cleanup incomplete; private stores retained.") from None
    _retained_children.pop(child.pid, None)


class OwnedChild:
    """Observe interactive exit without releasing the leader's process-group identity."""

    def __init__(self, args, **kwargs):
        if not all(hasattr(os, name) for name in ("waitid", "WNOWAIT", "WEXITED", "WNOHANG", "P_PID")):
            raise RuntimeError("Legacy command PrerequisiteMissing.")
        kwargs["start_new_session"] = True
        self._process = subprocess.Popen(args, **kwargs)
        self.returncode = None
        self._settled = False

    def __getattr__(self, name):
        return getattr(self._process, name)

    def poll(self):
        if self.returncode is None:
            result = os.waitid(os.P_PID, self.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            if result is not None:
                self.returncode = result.si_status if result.si_code == os.CLD_EXITED else -result.si_status
        return self.returncode

    def wait(self, timeout):
        deadline = time.monotonic() + timeout
        while self.poll() is None:
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(self.args, timeout)
            time.sleep(0.01)
        return self.returncode

    def kill(self):
        os.kill(self.pid, signal.SIGKILL)

    def settle(self):
        if not self._settled:
            _settle_group(self._process)
            self.returncode = self._process.returncode
            self._settled = True

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.settle()


def capture(args, *, cwd=None, env=None, timeout=600):
    """Capture at most 1 MiB, settle the complete owned process group on all exits."""
    if not all(hasattr(os, name) for name in ("waitid", "WNOWAIT", "WEXITED", "WNOHANG", "P_PID")):
        raise RuntimeError("Legacy command PrerequisiteMissing.")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("HOARD_")}
    environment.update(env or {})
    environment.update(MSBUILDDISABLENODEREUSE="1", DOTNET_CLI_USE_MSBUILD_SERVER="0",
                       UseSharedCompilation="false")
    try:
        child = subprocess.Popen(
            args, cwd=cwd, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, start_new_session=True)
    except OSError:
        raise RuntimeError("Legacy command CommandFailed.") from None
    data = bytearray()
    deadline = time.monotonic() + timeout
    error = None
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError("Legacy command exceeded its finite deadline.")
                for key, _ in selector.select(min(0.1, remaining)):
                    block = os.read(key.fileobj.fileno(), READ_BYTES)
                    if not block:
                        selector.unregister(key.fileobj)
                    elif len(data) + len(block) > TRANSIENT_BYTES:
                        raise RuntimeError("Legacy command OutputLimitExceeded.")
                    else:
                        data.extend(block)
        while os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
            if time.monotonic() >= deadline:
                raise RuntimeError("Legacy command exceeded its finite deadline.")
            time.sleep(0.01)
        if process_group(child.pid):
            raise RuntimeError("Legacy command left an unsettled descendant.")
    except (OSError, subprocess.SubprocessError, RuntimeError, ConformanceError, KeyboardInterrupt) as caught:
        error = caught
    finally:
        child.stdout.close()
        _settle_group(child)
    if error is not None:
        if isinstance(error, KeyboardInterrupt):
            raise error
        if isinstance(error, RuntimeError) and not isinstance(error, ConformanceError):
            raise error
        raise RuntimeError("Legacy command failed within its finite deadline.") from None
    result = subprocess.CompletedProcess(args, child.returncode, bytes(data))
    result.child_pid = child.pid
    return result


class ErrorCapture:
    """Concurrent finite stderr capture for legacy interactive transfer/barrier producers."""

    def __init__(self, *, allow_output=False):
        self.allow_output = allow_output

    def __enter__(self):
        self.reader, self.writer = os.pipe()
        self.data = bytearray()
        self.overflow = False
        self.failed = False
        self.started = False
        return self

    def fileno(self):
        return self.writer

    def start(self):
        os.close(self.writer)
        self.writer = None
        self.thread = threading.Thread(target=self._drain, daemon=True)
        self.thread.start()
        self.started = True

    def start_from(self, stream):
        os.close(self.reader)
        self.reader = os.dup(stream.fileno())
        self.start()

    def _drain(self):
        try:
            while block := os.read(self.reader, READ_BYTES):
                if len(self.data) + len(block) > TRANSIENT_BYTES:
                    self.overflow = True
                elif not self.overflow:
                    self.data.extend(block)
        except OSError:
            self.failed = True
        finally:
            os.close(self.reader)

    def check(self):
        if self.overflow:
            raise RuntimeError("Legacy command OutputLimitExceeded.")
        if self.failed:
            raise RuntimeError("Legacy command UnknownDiagnostic.")
        if self.data and not self.allow_output:
            raise RuntimeError("Legacy command UnknownDiagnostic.")

    def __exit__(self, *unused):
        if self.writer is not None:
            os.close(self.writer)
        if self.started:
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                raise RuntimeError("Legacy command cleanup incomplete.")
        else:
            os.close(self.reader)
        self.check()


@contextmanager
def silent_child(args):
    """Drain barrier-only child output concurrently and reject unexpected diagnostics."""
    with ErrorCapture() as output:
        with OwnedChild(args, stdout=output, stderr=subprocess.STDOUT) as child:
            output.start()
            try:
                yield child
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=10)


def peak_rss(data, *, darwin, arguments):
    """Admit only the fixed OS profiler grammar, never its quoted private argv."""
    text = data.decode("utf-8", errors="strict")
    if darwin:
        patterns = (
            r"\s*[0-9.]+ real\s+[0-9.]+ user\s+[0-9.]+ sys",
            r"\s*\d+\s+(?:maximum resident set size|average shared memory size|average unshared data size|"
            r"average unshared stack size|page reclaims|page faults|swaps|block input operations|"
            r"block output operations|messages sent|messages received|signals received|voluntary context switches|"
            r"involuntary context switches|instructions retired|cycles elapsed|peak memory footprint)")
        peak = re.findall(r"^\s*(\d+)\s+maximum resident set size\s*$", text, re.MULTILINE)
    else:
        patterns = (
            r'\s*Command being timed: "' + re.escape(" ".join(arguments)) + '"',
            r"\s*(?:User time \(seconds\)|System time \(seconds\)|Percent of CPU this job got|"
            r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\)|Average shared text size \(kbytes\)|"
            r"Average unshared data size \(kbytes\)|Average stack size \(kbytes\)|Average total size \(kbytes\)|"
            r"Maximum resident set size \(kbytes\)|Average resident set size \(kbytes\)|"
            r"Major \(requiring I/O\) page faults|Minor \(reclaiming a frame\) page faults|"
            r"Voluntary context switches|Involuntary context switches|Swaps|File system inputs|File system outputs|"
            r"Socket messages sent|Socket messages received|Signals delivered|Page size \(bytes\)|Exit status):"
            r"\s*[0-9.:%]+")
        peak = re.findall(r"^\s*Maximum resident set size \(kbytes\):\s*(\d+)\s*$", text, re.MULTILINE)
    if len(peak) != 1 or any(not any(re.fullmatch(pattern, line) for pattern in patterns)
                             for line in text.splitlines() if line.strip()):
        raise RuntimeError("Legacy OS memory profiler UnknownDiagnostic.")
    return int(peak[0]) * (1 if darwin else 1024)


def command(args, *, cwd=None, env=None, timeout=600):
    result = capture(args, cwd=cwd, env=env, timeout=timeout)
    if result.returncode:
        raise RuntimeError("Legacy command CommandFailed.")
    raw = result.stdout
    try:
        text = raw.decode("utf-8", errors="strict")
        if args[0] == "dotnet" and args[1] in ("restore", "build", "pack", "format"):
            for line in raw.splitlines():
                project_build_line(line)
            return ""
        if args[0] == "git":
            if args[1:3] == ("rev-parse", "HEAD") and re.fullmatch(r"[0-9a-f]{40,64}\n?", text):
                return text
            if not text:
                return ""
        if text.strip() in (
                "metadata-marker-compatible", "artifact-marker-compatible",
                "metadata-package-consumer-compatible",
                "ext2/ext3", "ext4", "xfs", "btrfs", "tmpfs", "overlayfs"):
            return text
        # These host observations are transient control inputs, never retained logs.
        if args[0] in ("df", "diskutil", "stat"):
            return text
        if args[0] == "dotnet" and str(args[1]).endswith(".dll"):
            return json.dumps(project_control(args, load_json(raw)), allow_nan=False)
    except (ValueError, TypeError, KeyError, UnicodeError, ConformanceError):
        pass
    raise RuntimeError("Legacy command UnknownDiagnostic.")


def project_control(args, value):
    if not isinstance(value, dict):
        raise ValueError()
    if Path(args[1]).name == "Hoard.Fixtures.Metadata.CrashRunner.dll":
        booleans = {
            "seeded", "baselineCompared", "stateCompared", "receiptCompared", "independentOldLayout",
            "admissionRejected", "competingOwnerRejected", "crashReleasedOwner", "uninstalledTargetAbsent",
            "retryRestoredBaseline", "historicalTicketRejected", "positive", "negative", "walCaptured",
            "isolatedRestoreCompared", "artifactSetRequired"}
        if set(value) - booleans - {"barrier", "settings", "runtime", "os", "cases"}:
            raise ValueError()
        if any(type(entry) is not bool for key, entry in value.items() if key in booleans):
            raise ValueError()
        if "barrier" in value and value["barrier"] not in ("M0", "M1", "M2", "U0", "U1", "U2", "U3", "U4"):
            raise ValueError()
        if "cases" in value and value["cases"] != ["MP-36", "MP-44", "MP-45"]:
            raise ValueError()
        if "runtime" in value and re.fullmatch(r"\.NET [0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,4}", value["runtime"]) is None:
            raise ValueError()
        if "os" in value:
            if sys.platform == "darwin":
                native = os.uname()
                description = f"{native.sysname} {native.release} {native.version}"
            elif sys.platform == "linux":
                description = platform.freedesktop_os_release()["PRETTY_NAME"]
            else:
                raise ValueError()
            if (value["os"] != description
                    and not (sys.platform == "darwin" and isinstance(value["os"], str)
                             and re.fullmatch(r"macOS [0-9]{1,2}\.[0-9]{1,2}(?:\.[0-9]{1,2})?", value["os"]))):
                raise ValueError()
            value = {**value, "os": {"darwin": "macos", "linux": "linux"}.get(sys.platform, "unsupported")}
        if "settings" in value:
            settings = value["settings"]
            if (not isinstance(settings, dict) or set(settings) != {
                    "JournalMode", "Synchronous", "ForeignKeys", "BusyTimeout", "NativeVersion", "Driver"}
                    or settings["JournalMode"] != "wal"
                    or any(type(settings[key]) is not int for key in ("Synchronous", "ForeignKeys", "BusyTimeout"))
                    or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", settings["NativeVersion"]) is None
                    or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?", settings["Driver"]) is None):
                raise ValueError()
        return value
    if Path(args[1]).name == "Hoard.Fixtures.Artifacts.Consumer.dll" and args[2] in ("local", "object"):
        operations = ("ReserveWriteAsync", "StageAsync", "RenewAsync", "CommitAsync", "OpenReadAsync", "ValidateAsync",
                      "ReconcileAsync", "AbandonAsync", "ReserveDeleteAsync", "DeleteAsync", "ObserveAsync", "CleanupAsync",
                      "CopyToAsync", "CloseAsync", "AcquireAsync", "RetainAsync")
        if value != {"qualification": False, "provider": args[2], "roundTrip": True, "operations": list(operations)}:
            raise ValueError()
        return value
    if Path(args[1]).name == "Hoard.Fixtures.Artifacts.Consumer.dll" and args[2] == "qualification":
        request = load_json(read_bounded(Path(args[3]), 1024 * 1024))
        fields = {
            "ImplementationId": request["implementationId"], "PackageVersion": "0.1.0",
            **{key[0].upper() + key[1:]: request[key] for key in (
                "packageSha256", "configurationSha256", "sourceSha256", "lockSha256")},
            "Capabilities": request["capabilities"],
            "Environment": {
                key: request["environment"][name] for key, name in (
                    ("OperatingSystem", "os"), ("Runtime", "runtime"), ("FileSystem", "filesystem"),
                    ("FlushConfiguration", "flushConfiguration"))},
            "EnvironmentSha256": request["cases"][0]["environmentSha256"],
            "ProofHashes": list(dict.fromkeys(case["sha256"] for case in request["cases"])),
        }
        fields["Environment"]["Sha256"] = fields["EnvironmentSha256"]
        if (set(value) != {*fields, "CaseIds", "Exclusions", "CaseResults"}
                or any(value[key] != entry for key, entry in fields.items())
                or value["CaseIds"] != [case["id"] for case in request["cases"]]
                or not isinstance(value["Exclusions"], list)
                or any(not isinstance(entry, str) or not re.fullmatch(r"AS-[0-9]{2}", entry)
                       for entry in value["Exclusions"])
                or not isinstance(value["CaseResults"], list) or len(value["CaseResults"]) != 48):
            raise ValueError()
        for case, observed in zip(request["cases"], value["CaseResults"]):
            if (not isinstance(observed, dict) or set(observed) != {"CaseId", "Status", "Duration", "ProofHashes"}
                    or observed["CaseId"] != case["id"]
                    or observed["Status"] != (0 if case["result"] == "Passed" else 1)
                    or re.fullmatch(r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,7})?", observed["Duration"]) is None
                    or observed["ProofHashes"] != [case["sha256"]]):
                raise ValueError()
        return value
    raise ValueError()


def _selected(identity, selection):
    if not selection:
        return True
    for disjunction in selection.split("|"):
        accepted = True
        for term in disjunction.split("&"):
            match = FQN_TERM.fullmatch(term)
            if match is None:
                return None
            method = identity.split("(")[0]
            accepted &= (match[2] not in method if match[1] == "!~" else
                         match[2] in method if match[1] == "~" else match[2] == method)
        if accepted:
            return True
    return False


def _required(assembly):
    from artifact_case_catalog import required_runtime_tests
    from conformance_case_catalog import ORIGINAL_INSPECTION_WITNESSES, ORIGINAL_METADATA_WITNESSES
    if assembly.name == "Hoard.Metadata.Tests.dll":
        return frozenset(ORIGINAL_METADATA_WITNESSES)
    if assembly.name == "Hoard.Artifacts.Tests.dll":
        return frozenset(name for provider in ("local", "object") for number in range(1, 49)
                         for name in required_runtime_tests(provider, f"AS-{number:02}"))
    if assembly.name == "Hoard.Architecture.Tests.dll":
        return frozenset(ORIGINAL_INSPECTION_WITNESSES)
    raise RuntimeError("Foreign legacy test assembly.")


def _discovery(assembly, selection, environment):
    arguments = ["dotnet", "vstest", str(assembly), "--ListTests"]
    if selection:
        arguments.append("--TestCaseFilter:" + selection)
    result = capture(arguments, env=environment, timeout=120)
    if result.returncode:
        raise RuntimeError("Legacy discovery CommandFailed.")
    names = []
    catalog_filter = not selection or all(FQN_TERM.fullmatch(term)
                                         for part in selection.split("|") for term in part.split("&"))
    try:
        for line in result.stdout.decode("utf-8", errors="strict").splitlines():
            text = line.strip()
            if text.startswith("Hoard."):
                if (len(text) > 1024 or re.fullmatch(r'[a-zA-Z0-9_.():, "\[\]+-]+', text) is None
                        or not text.startswith(assembly.stem + ".")):
                    raise RuntimeError("Legacy discovery WitnessMissing.")
                if not catalog_filter or _selected(text, selection):
                    names.append(text)
            elif text and text != "The following Tests are available:":
                project_test_line(line.encode())
    except (UnicodeError, ConformanceError):
        raise RuntimeError("Legacy discovery UnknownDiagnostic.") from None
    # Other valid VSTest properties remain usable for focused, non-qualifying runs.
    # Full qualification independently requires every frozen per-case witness.
    required = ({name for name in _required(assembly)
                 if name.startswith(assembly.stem + ".") and _selected(name, selection)}
                if catalog_filter else set())
    if (not required.issubset(names) or not names
            or len(names) > 10000 or len(set(names)) != len(names)):
        raise RuntimeError("Legacy discovery has missing or duplicate required runtime witnesses.")
    return tuple(sorted(names))


def _copy_runtime(source, target):
    no_symlinks(source)
    total, count = 0, 0
    inputs = []
    for path in source.rglob("*"):
        no_symlinks(path)
        if path.is_file():
            count += 1
            total += path.stat().st_size
            if count > 2048 or path.stat().st_size > 64 * 1024**2 or total > 512 * 1024**2:
                raise RuntimeError("Legacy runtime OutputLimitExceeded.")
            coverage_prefix = ".msCoverageSourceRootsMapping_"
            if (path.name.startswith(coverage_prefix)
                    and path.with_name(path.name.removeprefix(coverage_prefix) + ".dll").is_file()):
                continue
            if (path.suffix.lower() not in (".dll", ".exe", ".so", ".dylib", ".pdb")
                    and not (path.suffix == ".a" and path.relative_to(source).parts[0] == "runtimes")
                    and not path.name.endswith((".deps.json", ".runtimeconfig.json", ".runtimeconfig.dev.json"))
                    and not (path.suffix == ".xml" and path.with_suffix(".dll").is_file())
                    and not (path.with_name(path.name + ".dll").is_file()
                             and path.with_name(path.name + ".runtimeconfig.json").is_file())):
                raise RuntimeError("Legacy runtime contains an unexpected execution input.")
            inputs.append(path)
        elif not path.is_dir():
            raise RuntimeError("Legacy runtime contains an unexpected execution input.")
    target.mkdir(mode=0o700)
    for path in inputs:
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(path, destination)


def _write(path, value):
    with path.open("xb") as output:
        output.write(canonical_bytes(value))
    path.chmod(0o400)


def _hash(path):
    no_symlinks(path)
    if not path.is_file() or path.stat().st_size > 512 * 1024**2:
        raise RuntimeError("Legacy runtime OutputLimitExceeded.")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(READ_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def _environment_sha256(environment):
    controls = {"HOARD_ORIGINAL_CONTEXT", "HOARD_CONFORMANCE_BINDING_CONTEXT",
                "HOARD_CONFORMANCE_RUNTIME_CONTEXT"}
    return hashlib.sha256(canonical_bytes({
        name: value for name, value in (environment or {}).items()
        if name.startswith("HOARD_") and name not in controls})).hexdigest()


def _runtime_configuration(assembly, environment):
    provider = (environment or {}).get("HOARD_METADATA_PROVIDER")
    if (provider not in (None, "sqlite", "memory")
            or assembly.stem == "Hoard.Metadata.Tests" and provider is None):
        raise RuntimeError("Legacy runtime requires an explicit supported metadata provider.")
    return {"bindingId": provider or "legacy", "environmentSha256": _environment_sha256(environment)}


def resolve_project(project):
    result = capture((
        "dotnet", "msbuild", str(project), "-target:ResolveReferences", "-property:Configuration=Release",
        "-getItem:ReferencePath,Compile", "-getProperty:TargetPath,ProjectAssetsFile", "-verbosity:quiet"))
    if result.returncode:
        raise RuntimeError("Legacy inspection CommandFailed.")
    try:
        value = load_json(result.stdout)
        if (not isinstance(value, dict) or set(value) != {"Items", "Properties"}
                or set(value["Items"]) != {"ReferencePath", "Compile"}
                or set(value["Properties"]) != {"TargetPath", "ProjectAssetsFile"}
                or any(not isinstance(value["Items"][key], list) for key in ("ReferencePath", "Compile"))
                or any(not isinstance(path, str) or not Path(path).is_absolute()
                       for path in value["Properties"].values())):
            raise ValueError()
        return value
    except (ValueError, TypeError, KeyError):
        raise RuntimeError("Legacy inspection UnknownDiagnostic.") from None


def stage_sdk(package, sdk):
    try:
        with zipfile.ZipFile(package) as contents:
            members = [item for item in contents.infolist()
                       if item.filename == "lib/net10.0/Hoard.Testing.Conformance.dll"]
            if len(members) != 1 or not 0 < members[0].file_size <= 64 * 1024**2:
                raise RuntimeError("Legacy runtime shared SDK package is invalid or unbounded.")
            packaged_sdk = contents.read(members[0])
    except (zipfile.BadZipFile, OSError):
        raise RuntimeError("Legacy runtime shared SDK package is invalid.") from None
    if sdk.exists():
        if _hash(sdk) != hashlib.sha256(packaged_sdk).hexdigest():
            raise RuntimeError("Legacy runtime SDK image does not match its actual archive.")
    else:
        sdk.write_bytes(packaged_sdk)


def validate_transport(root, manifest, result, *, started, ended, assertion=None):
    """Independently correlate logger completion, exact results and individual proofs."""
    attempt = manifest["attemptId"]
    output = root / f"runtime-{attempt}"
    completion = load_json(read_bounded(output / "completion.json", 64 * 1024))
    raw = read_bounded(output / "witnesses.jsonl", 1024 * 1024)
    expected = {entry["testIdentity"]: entry for entry in manifest["expected"]}
    if (not raw.endswith(b"\n") or len(raw.splitlines()) != len(expected)
            or len(raw.splitlines()) > 10000):
        raise RuntimeError("Legacy runtime EvidenceIncomplete.")
    rows = [admit_entity("RuntimeWitness", load_json(line)) for line in raw.splitlines()]
    if (len({row["executionId"] for row in rows}) != len(rows)
            or {row["testIdentity"] for row in rows} != expected.keys()):
        raise RuntimeError("Legacy runtime WitnessMissing.")
    manifest_sha = _hash(root / f"runtime-input-{attempt}.json")
    owner_sha = _hash(root / "runtime-owner.json")
    common = {key: manifest[key] for key in (
        "runId", "invocationGroupId", "attemptId", "attemptSequence", "inputSha256")}
    files = {"completion.json", "witnesses.jsonl"}
    observed = []
    failures = []
    for row in rows:
        entry = expected[row["testIdentity"]]
        name = f'proof-{row["executionId"]}.json'
        files.add(name)
        proof_raw = read_bounded(output / name, 64 * 1024)
        proof = load_json(proof_raw)
        fixed = {
            "schemaVersion": 1, **common, "testIdentity": row["testIdentity"],
            "executionId": row["executionId"], "bindingId": entry["bindingId"],
            "matrixId": entry["matrixId"], "caseId": entry["caseId"],
            "manifestSha256": manifest_sha, "ownerSha256": owner_sha,
            "assemblySha256": manifest["assemblies"][0]["sha256"],
            "packageSha256": manifest["packages"][0]["sha256"],
            "clock": "system-monotonic-ms", "sessionOrigins": [],
        }
        if (not isinstance(proof, dict) or set(proof) != {*fixed, "durationMs", "failureKind", "assertionSymbol", "status"}
                or any(type(proof.get(key)) is not type(value) or proof.get(key) != value
                       for key, value in fixed.items())
                or any(proof.get(key) != row[key] for key in (
                    "runId", "invocationGroupId", "inputSha256", "assemblySha256", "packageSha256",
                    "status", "testIdentity", "bindingId", "matrixId"))
                or hashlib.sha256(proof_raw).hexdigest() != row["proofSha256"]
                or not started - 1000 <= row["startedMs"] <= row["endedMs"] <= ended + 1000
                or type(proof["durationMs"]) not in (int, float)
                or not math.isfinite(proof["durationMs"]) or proof["durationMs"] < 0
                or abs(row["endedMs"] - row["startedMs"] - proof["durationMs"]) > 1):
            raise RuntimeError("Legacy runtime ProofMismatch.")
        if row["status"] == "Failed":
            if assertion is None or proof["failureKind"] != "Assertion" or proof["assertionSymbol"] != assertion:
                raise RuntimeError("Legacy runtime did not produce its named assertion failure.")
            failures.append(row["testIdentity"])
        elif (row["status"] != "Passed" or proof["failureKind"] != "None" or proof["assertionSymbol"] is not None):
            raise RuntimeError("Legacy runtime has a skipped or unknown witness.")
        observed.append({"test": row["testIdentity"], "durationMs": proof["durationMs"], "outcome": row["status"]})
    diagnostic = "AssertionFailed" if failures else "None"
    wanted = {
        "schemaVersion": 1, **common, "purpose": "execution",
        "manifestSha256": manifest_sha, "recordsSha256": hashlib.sha256(raw).hexdigest(),
        "diagnosticCode": diagnostic, "observedCount": len(expected), "expectedCount": len(expected), "complete": True}
    if (completion != wanted or any(type(completion.get(key)) is not type(value) for key, value in wanted.items())
            or {path.name for path in output.iterdir()} != files
            or (result.returncode > 0) != bool(failures) or result.returncode < 0):
        raise RuntimeError("Legacy runtime EvidenceIncomplete.")
    events = []
    try:
        for line in result.stdout.splitlines():
            if event := project_test_line(line):
                events.append(dict(event))
    except ConformanceError:
        raise RuntimeError("Legacy runtime UnknownDiagnostic.") from None
    if events != [{"event": "control", "code": diagnostic, "value": len(expected)}]:
        raise RuntimeError("Legacy runtime completion was not observed.")
    for entry in (*manifest["assemblies"], *manifest["packages"]):
        path = root / entry["path"]
        if not path.resolve().is_relative_to(root.resolve()) or _hash(path) != entry["sha256"]:
            raise RuntimeError("Legacy runtime InputChanged.")
    return observed, failures


def test_command(args, *, cwd=None, env=None, assertion=None, allow_failure=False):
    """Replace a legacy TRX invocation with the existing pre-persistence safe logger."""
    args = tuple(map(str, args))
    options = {}
    assembly = None
    selection = None
    for index, value in enumerate(args):
        if value in ("--filter", "--logger", "--results-directory"):
            options[value] = args[index + 1]
        for prefix, key in (("/Logger:", "--logger"), ("/ResultsDirectory:", "--results-directory"),
                            ("/TestCaseFilter:", "--filter")):
            if value.startswith(prefix):
                options[key] = value[len(prefix):]
    selection = options.get("--filter")
    if args[1] == "vstest":
        assembly = Path(args[2]).absolute()
    elif args[1] == "test":
        project = Path(args[2]).absolute()
        assembly = project.parent / f"bin/Release/net10.0/{project.stem}.dll"
        if "--no-build" not in args:
            properties = tuple(value for value in args if value.startswith("-p:"))
            command(("dotnet", "build", str(project), "-c", "Release", "--no-restore", *properties, "-v", "quiet"),
                    cwd=cwd, env=env)
    if assembly is None or "--results-directory" not in options:
        raise RuntimeError("Legacy runtime requires an explicit assembly and results directory.")
    match = re.fullmatch(r"trx;LogFileName=([a-zA-Z0-9._-]+\.trx)", options.get("--logger", ""))
    if match is None:
        raise RuntimeError("Legacy runtime requires a fixed safe projection name.")
    destination = Path(options["--results-directory"]).absolute()
    no_symlinks(destination)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = destination / ("safe-" + uuid.uuid4().hex)
    root.mkdir(mode=0o700)
    resources = root / "resources"
    resources.mkdir(mode=0o700)
    runtime = resources / "assembly"
    _copy_runtime(assembly.parent, runtime)
    logger_output = Path(__file__).resolve().parents[1] / "tests/contracts/Hoard.Conformance.TestLogger/bin/Release/net10.0"
    logger = logger_output / "Hoard.Conformance.TestLogger.dll"
    if not logger.is_file():
        project = logger_output.parents[2] / "Hoard.Conformance.TestLogger.csproj"
        if not (project.parent / "obj/project.assets.json").is_file():
            command(("dotnet", "restore", str(project), "--locked-mode", "-v", "quiet"))
        command(("dotnet", "build", str(project), "-c", "Release", "--no-restore", "-v", "quiet"))
    if not logger.is_file():
        raise RuntimeError("Legacy runtime safe logger prerequisite is missing.")
    shutil.copy2(logger, runtime / logger.name)
    sdk = runtime / "Hoard.Testing.Conformance.dll"
    feed = next((parent / "feed" for parent in (destination.parent, *assembly.parents)
                 if (parent / "feed/Hoard.Testing.Conformance.0.1.0.nupkg").is_file()), None)
    if feed is None:
        raise RuntimeError("Legacy runtime requires its actual shared SDK package.")
    archive = feed / "Hoard.Testing.Conformance.0.1.0.nupkg"
    no_symlinks(archive)
    if archive.stat().st_size > 64 * 1024**2:
        raise RuntimeError("Legacy runtime OutputLimitExceeded.")
    package = resources / "sdk.nupkg"
    shutil.copy2(archive, package)
    stage_sdk(package, sdk)
    staged = runtime / assembly.name
    identities = _discovery(staged, selection, env)
    configuration = _runtime_configuration(assembly, env)
    run_id, group, attempt = (str(uuid.uuid4()) for _ in range(3))
    images = [{"id": "test-assembly" if path == staged else f"component-{index}",
               "path": path.relative_to(root).as_posix(), "sha256": _hash(path)}
              for index, path in enumerate(sorted(runtime.rglob("*")))
              if path.is_file() and (path.suffix in (".dll", ".so", ".dylib")
                                     or path.name.endswith((".deps.json", ".runtimeconfig.json", ".runtimeconfig.dev.json")))]
    images.sort(key=lambda entry: entry["id"] != "test-assembly")
    if len(images) > 128:
        raise RuntimeError("Legacy runtime OutputLimitExceeded.")
    for entry in images:
        (root / entry["path"]).chmod(0o400)
    package.chmod(0o400)
    inputs = {"schemaVersion": 1, "runId": run_id, "invocationGroupId": group,
              "assemblies": images, "packageSha256": _hash(package), "configuration": configuration}
    _write(root / "legacy-inputs.json", inputs)
    _write(root / "runtime-owner.json", {
        "schemaVersion": 1, "runId": run_id, "invocationGroupId": group, "rootId": uuid.uuid4().hex,
        "rootPathSha256": hashlib.sha256(str(root).encode()).hexdigest()})
    manifest = {
        "schemaVersion": 1, "runId": run_id, "invocationGroupId": group, "attemptId": attempt,
        "attemptSequence": 1, "purpose": "execution", "inputSha256": _hash(root / "legacy-inputs.json"),
        "runInputsPath": "legacy-inputs.json", "assemblies": images,
        "packages": [{"id": "shared-sdk", "path": package.relative_to(root).as_posix(), "sha256": _hash(package)}],
        "expected": [{"testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
                      "assemblyId": "test-assembly", "packageId": "shared-sdk", "bindingId": configuration["bindingId"],
                      "matrixId": "none", "assertionSymbol": assertion, "caseId": "runtime"}
                     for identity in identities]}
    _write(root / f"runtime-input-{attempt}.json", manifest)
    environment = dict(env or {})
    for name in ("HOARD_ORIGINAL_CONTEXT", "HOARD_CONFORMANCE_BINDING_CONTEXT", "HOARD_CONFORMANCE_RUNTIME_CONTEXT"):
        environment.pop(name, None)
    from xml.sax.saxutils import escape
    variables = ("<EnvironmentVariables>" + "".join(
        f"<{key}>{escape(value)}</{key}>" for key, value in environment.items()) + "</EnvironmentVariables>")
    settings = resources / "settings.runsettings"
    with settings.open("xb") as output:
        output.write(runtime_settings(root, staged, attempt, _hash(root / f"runtime-input-{attempt}.json"),
                                      _hash(root / "runtime-owner.json"), variables))
    started = time.monotonic() * 1000
    arguments = runtime_arguments(staged, settings, identities)
    if selection:
        arguments[-1] = "--TestCaseFilter:" + selection
    result = capture(arguments, cwd=runtime, env=environment, timeout=180)
    ended = time.monotonic() * 1000
    observed, failures = validate_transport(root, manifest, result, started=started, ended=ended, assertion=assertion)
    if failures and not allow_failure:
        raise RuntimeError("Legacy runtime has failed applicable tests.")
    document = ET.Element("TestRun", xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010")
    results = ET.SubElement(document, "Results")
    for entry in observed:
        seconds = entry["durationMs"] / 1000
        ET.SubElement(results, "UnitTestResult", testName=entry["test"], outcome=entry["outcome"],
                      duration=f"{int(seconds // 3600):02}:{int(seconds // 60 % 60):02}:{seconds % 60:012.9f}")
    counters = ET.SubElement(ET.SubElement(document, "ResultSummary"), "Counters")
    counters.attrib.update(total=str(len(observed)), executed=str(len(observed)), passed=str(len(observed) - len(failures)),
                           failed=str(len(failures)), error="0", timeout="0", aborted="0", inconclusive="0",
                           passedButRunAborted="0", notRunnable="0", notExecuted="0", disconnected="0")
    projection = destination / match[1]
    with projection.open("xb") as output:
        output.write(ET.tostring(document, encoding="utf-8", xml_declaration=True))
    _write(projection.with_suffix(".runtime.json"), {
        "schemaVersion": 1, "projectionSha256": _hash(projection), "transport": root.name,
        "attemptId": attempt, "manifestSha256": _hash(root / f"runtime-input-{attempt}.json"),
        "startedMs": started, "endedMs": ended, "exitCode": result.returncode,
        "assertionSymbol": assertion, "events": [{"event": "control", "code": "AssertionFailed" if failures else "None",
                                                "value": len(observed)}]})
    return subprocess.CompletedProcess(args, result.returncode, canonical_bytes({"tests": len(observed), "failed": len(failures)}),
                                       failures)


def verify_projection(path, *, required=True, expected_binding="legacy", expected_environment=None):
    sidecar = path.with_suffix(".runtime.json")
    if not sidecar.exists():
        if required:
            raise RuntimeError("Legacy runtime safe projection is missing.")
        return
    receipt = load_json(read_bounded(sidecar, 64 * 1024))
    if (not isinstance(receipt, dict) or receipt.get("schemaVersion") != 1
            or set(receipt) != {"schemaVersion", "projectionSha256", "transport", "attemptId",
                                "manifestSha256", "startedMs", "endedMs", "exitCode", "assertionSymbol", "events"}
            or not re.fullmatch(r"safe-[0-9a-f]{32}", receipt.get("transport", ""))
            or _hash(path) != receipt.get("projectionSha256")):
        raise RuntimeError("Legacy runtime projection ProofMismatch.")
    root = path.parent / receipt["transport"]
    manifest_path = root / f'runtime-input-{receipt["attemptId"]}.json'
    if _hash(manifest_path) != receipt["manifestSha256"]:
        raise RuntimeError("Legacy runtime manifest InputChanged.")
    manifest = load_json(read_bounded(manifest_path, 2 * 1024**2))
    inputs_path = root / "legacy-inputs.json"
    if manifest["runInputsPath"] != "legacy-inputs.json" or _hash(inputs_path) != manifest["inputSha256"]:
        raise RuntimeError("Legacy runtime input InputChanged.")
    inputs = load_json(read_bounded(inputs_path, 2 * 1024**2))
    configuration = inputs.get("configuration") if isinstance(inputs, dict) else None
    if (not isinstance(inputs, dict) or set(inputs) != {
                "schemaVersion", "runId", "invocationGroupId", "assemblies", "packageSha256", "configuration"}
            or not isinstance(configuration, dict)
            or set(configuration) != {"bindingId", "environmentSha256"}
            or expected_binding not in ("legacy", "memory", "sqlite")
            or configuration["bindingId"] != expected_binding
            or not isinstance(configuration["environmentSha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", configuration["environmentSha256"]) is None
            or expected_environment is not None
               and configuration["environmentSha256"] != _environment_sha256(expected_environment)
            or inputs["runId"] != manifest["runId"]
            or inputs["invocationGroupId"] != manifest["invocationGroupId"]
            or inputs["assemblies"] != manifest["assemblies"]
            or inputs["packageSha256"] != manifest["packages"][0]["sha256"]
            or any(entry["bindingId"] != expected_binding for entry in manifest["expected"])):
        raise RuntimeError("Legacy runtime configured provider InputChanged.")
    result = subprocess.CompletedProcess([], receipt["exitCode"],
        b"\n".join(canonical_bytes(event) for event in receipt["events"]))
    validate_transport(root, manifest, result, started=receipt["startedMs"], ended=receipt["endedMs"],
                       assertion=receipt["assertionSymbol"])


def python_tests(args, *, cwd):
    """Run real unittest assertions without its traceback/source-line diagnostic writer."""
    pattern = args[args.index("-p") + 1]
    code = (
        "import json,unittest\n"
        f"suite=unittest.defaultTestLoader.discover('tests/tooling',pattern={pattern!r})\n"
        "class SafeResult(unittest.TestResult):\n"
        " def __init__(self): super().__init__(); self.records=[]\n"
        " def addFailure(self,test,error): self.records.append({'test':test.id(),'kind':'Assertion' if "
        "issubclass(error[0],AssertionError) else 'Unknown'}); self.failures.append((test,''))\n"
        " def addError(self,test,error): self.records.append({'test':test.id(),'kind':'Error'}); self.errors.append((test,''))\n"
        " def addSubTest(self,test,subtest,error):\n"
        "  if error is not None:\n"
        "   if issubclass(error[0],AssertionError): self.addFailure(test,error)\n"
        "   else: self.addError(test,error)\n"
        "result=SafeResult(); suite.run(result)\n"
        "print(json.dumps({'run':result.testsRun,'failures':result.records,'skipped':len(result.skipped)}))\n"
        "raise SystemExit(0 if result.wasSuccessful() else 1)\n")
    result = capture((sys.executable, "-c", code), cwd=cwd)
    try:
        value = load_json(result.stdout)
        if (set(value) != {"run", "failures", "skipped"} or type(value["run"]) is not int or value["run"] <= 0
                or value["skipped"] != 0 or not isinstance(value["failures"], list)
                or any(set(item) != {"test", "kind"} or item["kind"] not in ("Assertion", "Error", "Unknown")
                       or re.fullmatch(r"[a-zA-Z0-9_.]+", item["test"]) is None for item in value["failures"])
                or bool(result.returncode) != bool(value["failures"])):
            raise ValueError()
    except (ValueError, TypeError, KeyError, ConformanceError):
        raise RuntimeError("Legacy verifier UnknownDiagnostic.") from None
    return result.returncode, value
