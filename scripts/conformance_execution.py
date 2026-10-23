"""Owned, bounded F-07 execution. Raw child diagnostics are never spooled."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import stat
import subprocess
import time
from types import MappingProxyType
import uuid

from conformance_evidence import ConformanceError, DIAGNOSTIC_CODES, canonical_bytes, load_json


READ_BYTES = 64 * 1024
TRANSIENT_BYTES = 1024 * 1024
CHILD_DIAGNOSTIC_BYTES = 8 * 1024 * 1024
PROFILE_DIAGNOSTIC_BYTES = 64 * 1024 * 1024
MAX_PROCESSES = 256


def capture_control(args, *, limit=TRANSIENT_BYTES, timeout=5, cwd=None):
    """Bounded transient data from fixed host tools; never diagnostic storage."""
    child = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    output = bytearray()
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise ConformanceError("DeadlineExceeded")
                for key, _ in selector.select(min(0.1, max(0.001, deadline - time.monotonic()))):
                    block = os.read(key.fileobj.fileno(), min(READ_BYTES, limit + 1))
                    if not block:
                        selector.unregister(key.fileobj)
                    else:
                        output.extend(block)
                        if len(output) > limit:
                            raise ConformanceError("OutputLimitExceeded")
        code = child.wait(timeout=max(0.001, deadline - time.monotonic()))
        return code, bytes(output)
    finally:
        if child.poll() is None:
            child.kill()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                raise ConformanceError("CleanupIncomplete") from None
        child.stdout.close()


def no_symlinks(path):
    for entry in (path, *path.parents):
        if entry.is_symlink():
            raise ConformanceError("OwnershipInvalid")


def profile_budget(profile):
    budgets = {"metadata": 5400, "artifacts": 10800, "composition": 3600,
               "compatibility": 3600, "harness": 3600, "baseline": 28800}
    if profile not in budgets:
        raise ConformanceError("UnsupportedProfile")
    return budgets[profile]


def check_capacity(profile, *, free_bytes):
    profile_budget(profile)
    if type(free_bytes) is not int or free_bytes < 0:
        raise ConformanceError("PrerequisiteMissing")
    if profile in ("artifacts", "baseline") and free_bytes < 24 * 1024**3:
        raise ConformanceError("InsufficientCapacity")


def process_identity(pid):
    if type(pid) is not int or pid <= 0:
        raise ConformanceError("OwnershipInvalid")
    code, output = capture_control(
        ["ps", "-p", str(pid), "-o", "pid=,uid=,pgid=,lstart=,stat="],
        limit=4096)
    if code == 1 and not output.strip():
        return None
    if code:
        raise ConformanceError("OwnershipInvalid")
    fields = output.decode("ascii", errors="strict").split()
    if len(fields) < 9 or int(fields[0]) != pid or int(fields[1]) != os.getuid():
        raise ConformanceError("OwnershipInvalid")
    if fields[-1].startswith("Z"):
        return None
    return hashlib.sha256(" ".join(fields[:-1]).encode("ascii")).hexdigest()


def process_group(group):
    code, output = capture_control(["ps", "-axo", "pid=,pgid=,uid=,stat="])
    if code:
        raise ConformanceError("OwnershipInvalid")
    owned = []
    for line in output.decode("ascii", errors="strict").splitlines():
        fields = line.split()
        if len(fields) != 4:
            raise ConformanceError("OwnershipInvalid")
        pid, pgid, uid = map(int, fields[:3])
        if pgid == group and not fields[3].startswith("Z"):
            if uid != os.getuid():
                raise ConformanceError("OwnershipInvalid")
            owned.append(pid)
    if len(owned) > MAX_PROCESSES:
        raise ConformanceError("OwnershipInvalid")
    return tuple(owned)


def project_event(line):
    value = load_json(line)
    if (not isinstance(value, dict) or set(value) != {"event", "code", "value"}
            or value["event"] not in ("control", "build", "test", "barrier", "cleanup")
            or value["code"] not in DIAGNOSTIC_CODES
            or type(value["value"]) is not int or not 0 <= value["value"] <= 2**63 - 1):
        raise ConformanceError("UnknownDiagnostic")
    return MappingProxyType(value)


def project_build_line(line):
    try:
        text = line.decode("utf-8", errors="strict").strip()
    except UnicodeError:
        raise ConformanceError("UnknownDiagnostic") from None
    if not text:
        return None
    codes = re.findall(r"\b(?:error|warning) ((?:CS|NU|MSB|NETSDK)\d{4,5})\b", text)
    if codes:
        return MappingProxyType({"event": "build", "code": "CommandFailed",
                                 "value": int(re.search(r"\d+", codes[0])[0])})
    if text == "Build FAILED.":
        return MappingProxyType({"event": "build", "code": "CommandFailed", "value": 0})
    if (text in ("Build succeeded.", "Pack succeeded.", "Determining projects to restore...",
                 "All projects are up-to-date for restore.")
            or re.fullmatch(r"\d+ Warning\(s\)", text) or re.fullmatch(r"\d+ Error\(s\)", text)
            or re.fullmatch(r"Time Elapsed \d{2}:\d{2}:\d{2}(?:\.\d+)?", text)
            or re.fullmatch(r"Restored .+ \([0-9.]+ (?:ms|sec|min)\)\.", text)
            or re.fullmatch(r".+ -> .+\.(?:dll|nupkg)", text)
            or re.fullmatch(r"Successfully created package '.+\.nupkg'\.", text)
            or text.startswith("The package ") and "is missing a readme." in text):
        return None
    raise ConformanceError("UnknownDiagnostic")


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    events: tuple
    duration_ms: float


class OwnedRun:
    @classmethod
    def allocate(cls, destination, repository, *, profile="baseline"):
        destination = Path(destination).absolute()
        repository = Path(repository).resolve()
        no_symlinks(destination)
        parent = destination.parent
        if (destination.exists() or not parent.is_dir() or parent.stat().st_uid != os.getuid()
                or stat.S_IMODE(parent.stat().st_mode) & 0o077
                or destination.is_relative_to(repository)):
            raise ConformanceError("OwnershipInvalid")
        check_capacity(profile, free_bytes=shutil.disk_usage(parent).free)
        destination.mkdir(mode=0o700)
        run = cls(destination.resolve())
        run.deadline = run.started + profile_budget(profile)
        for name in ("stores", "feed", "cache", "diagnostics", "proofs"):
            (run.root / name).mkdir(mode=0o700)
        run._persist(create=True)
        return run

    def __init__(self, root):
        self.root = root
        self.root_identity = (root.stat().st_dev, root.stat().st_ino)
        self.root_id = uuid.uuid4().hex
        self.run_id = str(uuid.uuid4())
        self.owner_pid = os.getpid()
        self.owner_start = process_identity(self.owner_pid)
        if self.owner_start is None:
            raise ConformanceError("OwnershipInvalid")
        self.state = "Allocated"
        self.children = {}
        self.groups = set()
        self.retained_bytes = 0
        self.command_sequence = 0
        self.started = time.monotonic()
        self.deadline = self.started + profile_budget("baseline")

    def _ledger(self):
        return {"schemaVersion": 1, "runId": self.run_id, "rootId": self.root_id,
                "ownerPid": self.owner_pid, "ownerStartSha256": self.owner_start,
                "state": self.state, "children": {str(pid): identity for pid, identity in self.children.items()}}

    def _persist(self, *, create=False):
        data = canonical_bytes(self._ledger())
        path = self.root / "ownership.json"
        if create:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            with os.fdopen(os.open(path, flags, 0o600), "wb") as output:
                output.write(data)
        else:
            self._check_ledger()
            temporary = self.root / "ownership.next"
            with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as output:
                output.write(data)
            temporary.replace(path)
        self._persisted = data

    def _check_ledger(self):
        no_symlinks(self.root)
        info = self.root.stat()
        path = self.root / "ownership.json"
        if ((info.st_dev, info.st_ino) != self.root_identity or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077 or path.is_symlink()
                or not path.is_file() or path.stat().st_size > TRANSIENT_BYTES
                or path.read_bytes() != self._persisted
                or self.owner_pid != os.getpid() or process_identity(self.owner_pid) != self.owner_start):
            raise ConformanceError("OwnershipInvalid")

    def transition(self, state):
        allowed = {"Allocated": ("Active", "Settling"), "Active": ("Settling",),
                   "Settling": ("Retained",), "Retained": ("Settling",)}
        if state not in allowed.get(self.state, ()):
            raise ConformanceError("OwnershipInvalid")
        self._check_ledger()
        self.state = state
        self._persist()

    def live_children(self):
        self._check_ledger()
        live = set()
        for pid, identity in self.children.items():
            observed = process_identity(pid)
            if observed is not None:
                if observed != identity:
                    raise ConformanceError("OwnershipInvalid")
                live.add(pid)
        for group in self.groups:
            live.update(process_group(group))
        return frozenset(live)

    def terminate(self, pid, *, deadline=None):
        self._check_ledger()
        if pid not in self.children or process_identity(pid) != self.children[pid]:
            raise ConformanceError("OwnershipInvalid")
        deadline = min(deadline or time.monotonic() + 10, time.monotonic() + 10)
        identities = {child: process_identity(child) for child in process_group(pid)}
        for child in sorted(identities, reverse=True):
            identity = identities[child]
            if identity is not None:
                if process_identity(child) != identity:
                    raise ConformanceError("OwnershipInvalid")
                try:
                    os.kill(child, signal.SIGKILL)
                except ProcessLookupError:
                    if process_identity(child) is not None:
                        raise ConformanceError("CleanupIncomplete") from None
        while process_group(pid):
            if time.monotonic() >= deadline:
                raise ConformanceError("CleanupIncomplete")
            time.sleep(0.01)

    def _contain(self, child):
        deadline = time.monotonic() + 10
        if child.poll() is None and process_identity(child.pid) is not None:
            self.terminate(child.pid, deadline=deadline)
        else:
            identities = {pid: process_identity(pid) for pid in process_group(child.pid)}
            for pid, identity in identities.items():
                if identity is not None:
                    if process_identity(pid) != identity:
                        raise ConformanceError("OwnershipInvalid")
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        if process_identity(pid) is not None:
                            raise ConformanceError("CleanupIncomplete") from None
        try:
            child.wait(timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise ConformanceError("CleanupIncomplete") from None
        while process_group(child.pid):
            if time.monotonic() >= deadline:
                raise ConformanceError("CleanupIncomplete")
            time.sleep(0.01)

    def command(self, args, *, cwd=None, timeout=None, kind="events", env=None, scope="ordinary", cache_id="default"):
        self._check_ledger()
        ceilings = {"ordinary": 600, "transfer": 2400, "recovery": 300}
        if scope not in ceilings:
            raise ConformanceError("OwnershipInvalid")
        if not isinstance(cache_id, str) or re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", cache_id) is None:
            raise ConformanceError("OwnershipInvalid")
        cache = self.root / "cache" / cache_id
        no_symlinks(cache)
        cache.mkdir(exist_ok=True, mode=0o700)
        timeout = ceilings[scope] if timeout is None else timeout
        if (self.state not in ("Allocated", "Active") or self.live_children()
                or not isinstance(args, (list, tuple)) or not args
                or any(not isinstance(arg, str) or "\x00" in arg for arg in args)
                or type(timeout) not in (int, float) or not 0 < timeout <= ceilings[scope]
                or kind not in ("events", "build")):
            raise ConformanceError("OwnershipInvalid")
        if self.state == "Allocated":
            self.transition("Active")
        started = time.monotonic()
        deadline = min(started + timeout, self.deadline)
        if deadline <= started:
            raise ConformanceError("DeadlineExceeded")
        child = subprocess.Popen(
            args, cwd=cwd, env={**os.environ, **(env or {}), "NUGET_PACKAGES": str(cache),
                               "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1",
                               "DOTNET_CLI_USE_MSBUILD_SERVER": "0", "MSBUILDDISABLENODEREUSE": "1"},
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        self.groups.add(child.pid)
        identity = process_identity(child.pid)
        if identity is not None:
            self.children[child.pid] = identity
        self._persist()
        self.command_sequence += 1
        destination = self.root / "diagnostics" / f"command-{self.command_sequence:04}.jsonl"
        events = []
        buffer = bytearray()
        retained = 0
        raw_total = 0
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ConformanceError("DeadlineExceeded")
                    for key, _ in selector.select(min(0.1, remaining)):
                        block = os.read(key.fileobj.fileno(), READ_BYTES)
                        if not block:
                            selector.unregister(key.fileobj)
                            continue
                        raw_total += len(block)
                        buffer.extend(block)
                        if len(buffer) > TRANSIENT_BYTES or raw_total > CHILD_DIAGNOSTIC_BYTES:
                            raise ConformanceError("OutputLimitExceeded")
                        while b"\n" in buffer:
                            line, _, tail = buffer.partition(b"\n")
                            buffer = bytearray(tail)
                            if len(line) > READ_BYTES:
                                raise ConformanceError("OutputLimitExceeded")
                            if not line.strip():
                                continue
                            try:
                                event = project_build_line(bytes(line)) if kind == "build" else project_event(bytes(line))
                            except ConformanceError:
                                raise ConformanceError("UnknownDiagnostic") from None
                            if event is not None:
                                safe = canonical_bytes(event) + b"\n"
                                retained += len(safe)
                                if retained > CHILD_DIAGNOSTIC_BYTES or self.retained_bytes + retained > PROFILE_DIAGNOSTIC_BYTES:
                                    raise ConformanceError("OutputLimitExceeded")
                                events.append(event)
                if buffer.strip():
                    if len(buffer) > READ_BYTES:
                        raise ConformanceError("OutputLimitExceeded")
                    try:
                        event = project_build_line(bytes(buffer)) if kind == "build" else project_event(bytes(buffer))
                    except ConformanceError:
                        raise ConformanceError("UnknownDiagnostic") from None
                    if event is not None:
                        events.append(event)
            code = child.wait(timeout=max(0.001, deadline - time.monotonic()))
            if process_group(child.pid):
                raise ConformanceError("CleanupIncomplete")
        except (ConformanceError, OSError, subprocess.SubprocessError, KeyboardInterrupt) as error:
            try:
                self._contain(child)
            except (ConformanceError, OSError, subprocess.SubprocessError):
                self.transition("Settling")
                self.transition("Retained")
                raise ConformanceError("CleanupIncomplete") from None
            if isinstance(error, ConformanceError):
                raise
            if isinstance(error, KeyboardInterrupt):
                raise
            raise ConformanceError("CommandFailed") from None
        finally:
            child.stdout.close()
            if child.poll() is not None and not process_group(child.pid):
                self.children.pop(child.pid, None)
                self.groups.discard(child.pid)
                self._persist()
        data = b"".join(canonical_bytes(event) + b"\n" for event in events)
        if len(data) > CHILD_DIAGNOSTIC_BYTES or self.retained_bytes + len(data) > PROFILE_DIAGNOSTIC_BYTES:
            raise ConformanceError("OutputLimitExceeded")
        with os.fdopen(os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as output:
            output.write(data)
        self.retained_bytes += len(data)
        return CommandResult(code, tuple(events), (time.monotonic() - started) * 1000)

    def release(self):
        self._check_ledger()
        if self.state != "Settling" or self.live_children():
            raise ConformanceError("CleanupIncomplete")
        for directory, directories, files in os.walk(self.root, followlinks=False):
            for name in (*directories, *files):
                if (Path(directory) / name).is_symlink():
                    raise ConformanceError("OwnershipInvalid")
        self.state = "Released"
        self._persist()
        shutil.rmtree(self.root)
