"""Owned, bounded F-07 execution. Raw child diagnostics are never spooled."""

from dataclasses import dataclass
from functools import wraps
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
from types import MappingProxyType
import uuid

from conformance_evidence import ConformanceError, DIAGNOSTIC_CODES, admit_entity, canonical_bytes, load_json


READ_BYTES = 64 * 1024
SAFE_EVENT_BYTES = 1024
TRANSIENT_BYTES = 1024 * 1024
CHILD_DIAGNOSTIC_BYTES = 8 * 1024 * 1024
PROFILE_DIAGNOSTIC_BYTES = 64 * 1024 * 1024
MAX_PROCESSES = 256
PIDFD_SIGNAL_PROCESS_GROUP = 4


def single_writer(operation):
    @wraps(operation)
    def execute(self, *args, **kwargs):
        if not self._writer.acquire(blocking=False):
            raise ConformanceError("OwnershipInvalid")
        try:
            return operation(self, *args, **kwargs)
        finally:
            self._writer.release()
    return execute


def control_timeout(deadline):
    remaining = 5 if deadline is None else min(5, deadline - time.monotonic())
    if remaining <= 0:
        raise ConformanceError("CleanupIncomplete")
    return remaining


def capture_control(args, *, limit=TRANSIENT_BYTES, timeout=5, cwd=None):
    """Bounded transient data from fixed host tools; never diagnostic storage."""
    child = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    output = bytearray()
    deadline = time.monotonic() + timeout
    work_deadline = deadline - min(1, timeout / 5)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            while selector.get_map():
                if time.monotonic() >= work_deadline:
                    raise ConformanceError("DeadlineExceeded")
                for key, _ in selector.select(min(0.1, max(0.001, work_deadline - time.monotonic()))):
                    block = os.read(key.fileobj.fileno(), min(READ_BYTES, limit + 1))
                    if not block:
                        selector.unregister(key.fileobj)
                    else:
                        output.extend(block)
                        if len(output) > limit:
                            raise ConformanceError("OutputLimitExceeded")
        try:
            code = child.wait(timeout=max(0.001, work_deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise ConformanceError("DeadlineExceeded") from None
        return code, bytes(output)
    finally:
        if child.poll() is None:
            child.kill()
            try:
                child.wait(timeout=max(0.001, deadline - time.monotonic()))
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


def native_execution_supported():
    return sys.platform == "linux" and os.uname().machine in ("x86_64", "aarch64")


def scratch_filesystem(parent, profile):
    if not native_execution_supported():
        return "unobserved"
    target = f"/proc/{os.getpid()}/fd/{parent}" if type(parent) is int else str(parent)
    code, output = capture_control(["stat", "-L", "-f", "--format=%T", target], limit=1024, timeout=5)
    if code or re.fullmatch(rb"[a-zA-Z0-9][a-zA-Z0-9._/-]{0,63}\n?", output) is None:
        raise ConformanceError("PrerequisiteMissing")
    filesystem = output.decode("ascii").strip()
    if profile in ("artifacts", "baseline") and filesystem not in (
            "ext2/ext3", "xfs", "btrfs", "zfs", "f2fs", "bcachefs"):
        raise ConformanceError("PrerequisiteMissing")
    return filesystem.replace("/", "-")


def command_environment(root, cache, supplied):
    if supplied is not None and (not isinstance(supplied, dict) or len(supplied) > 128):
        raise ConformanceError("OwnershipInvalid")
    environment = {key: os.environ[key] for key in
                   ("PATH", "LANG", "LC_ALL", "DOTNET_ROOT", "DOTNET_ROOT_X64", "DOTNET_ROOT_ARM64")
                   if key in os.environ}
    for key, value in (supplied or {}).items():
        if (not isinstance(key, str) or not key.startswith(("HOARD_", "DOTNET_", "ASPNETCORE_", "COMPlus_"))
                or re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,127}", key) is None
                or not isinstance(value, str) or "\x00" in value or len(value.encode("utf-8")) > 16384):
            raise ConformanceError("OwnershipInvalid")
        environment[key] = value
    if sum(len(key.encode("utf-8")) + len(value.encode("utf-8")) for key, value in environment.items()) > READ_BYTES:
        raise ConformanceError("OwnershipInvalid")
    environment.update({
        "NUGET_PACKAGES": str(cache), "HOME": str(root / "cache"), "DOTNET_CLI_HOME": str(cache),
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1",
        "DOTNET_CLI_USE_MSBUILD_SERVER": "0", "MSBUILDDISABLENODEREUSE": "1",
    })
    return environment


def process_identity(pid, *, deadline=None):
    if type(pid) is not int or pid <= 0:
        raise ConformanceError("OwnershipInvalid")
    if sys.platform == "linux":
        control_timeout(deadline)
        try:
            descriptor = os.open(f"/proc/{pid}/stat", os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        with os.fdopen(descriptor, "rb") as source:
            if os.fstat(source.fileno()).st_uid != os.getuid():
                raise ConformanceError("OwnershipInvalid")
            encoded = source.read(4097)
        return linux_process_identity(pid, encoded)
    code, output = capture_control(
        ["ps", "-p", str(pid), "-o", "pid=,uid=,pgid=,lstart=,stat="],
        limit=4096, timeout=control_timeout(deadline))
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


def linux_process_identity(pid, encoded):
    prefix, separator, remainder = encoded.rpartition(b") ")
    fields = remainder.split()
    if (len(encoded) > 4096 or not separator or not prefix.startswith(str(pid).encode("ascii") + b" (")
            or len(fields) < 20 or fields[0] not in (b"R", b"S", b"D", b"Z", b"T", b"t", b"X", b"x", b"K", b"W", b"P", b"I")
            or any(not fields[index].isdigit() for index in (1, 2, 3, 19))):
        raise ConformanceError("OwnershipInvalid")
    if fields[0] in (b"Z", b"X", b"x"):
        return None
    identity = b":".join((str(pid).encode("ascii"), str(os.getuid()).encode("ascii"),
                          fields[2], fields[3], fields[19]))
    return hashlib.sha256(identity).hexdigest()


def process_group(group, *, deadline=None):
    code, output = capture_control(["ps", "-axo", "pid=,pgid=,uid=,stat="],
                                   timeout=control_timeout(deadline))
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
    if len(line) > SAFE_EVENT_BYTES:
        raise ConformanceError("OutputLimitExceeded")
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
    code = re.search(r"\b(?:error|warning) ((?:CS|NU|MSB|NETSDK)\d{4,5})\b", text)
    if code:
        return MappingProxyType({"event": "build", "code": "CommandFailed",
                                 "value": int(re.search(r"\d+", code[1])[0])})
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


def project_test_line(line):
    try:
        text = line.decode("utf-8", errors="strict").strip()
    except UnicodeError:
        raise ConformanceError("UnknownDiagnostic") from None
    if (not text or text == "Starting test execution, please wait..."
            or re.fullmatch(r"VSTest version [0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4} \((?:x64|x86|arm64)\)", text)):
        return None
    try:
        return project_event(line)
    except ConformanceError as error:
        if str(error) == "OutputLimitExceeded":
            raise
        raise ConformanceError("UnknownDiagnostic") from None


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    events: tuple
    duration_ms: float


class OwnedRun:
    @classmethod
    def allocate(cls, destination, repository, *, profile="baseline"):
        started = time.monotonic()
        destination = Path(destination).absolute()
        repository = Path(repository).resolve()
        no_symlinks(destination)
        parent = destination.parent
        if (".." in destination.parts or destination.exists() or not parent.is_dir()
                or destination.is_relative_to(repository)):
            raise ConformanceError("OwnershipInvalid")
        parent_info = parent.stat()
        if parent_info.st_uid != os.getuid() or stat.S_IMODE(parent_info.st_mode) & 0o077:
            raise ConformanceError("OwnershipInvalid")
        parent_descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            pinned = os.fstat(parent_descriptor)
            identity = (parent_info.st_dev, parent_info.st_ino)
            if (pinned.st_dev, pinned.st_ino) != identity:
                raise ConformanceError("OwnershipInvalid")
            free_bytes = shutil.disk_usage(parent_descriptor).free
            check_capacity(profile, free_bytes=free_bytes)
            filesystem = scratch_filesystem(parent_descriptor, profile)
            no_symlinks(destination)
            current = parent.stat(follow_symlinks=False)
            if (current.st_dev, current.st_ino) != identity:
                raise ConformanceError("OwnershipInvalid")
            os.mkdir(destination.name, mode=0o700, dir_fd=parent_descriptor)
            root = os.open(destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                           dir_fd=parent_descriptor)
            try:
                info = os.fstat(root)
                run = cls(destination, root_identity=(info.st_dev, info.st_ino))
                run.started = started
                run.deadline = started + profile_budget(profile)
                for name in ("stores", "feed", "cache", "diagnostics", "proofs"):
                    os.mkdir(name, mode=0o700, dir_fd=root)
                    info = os.stat(name, dir_fd=root, follow_symlinks=False)
                    run.directory_identities[name] = (info.st_dev, info.st_ino)
                run._persist(create=True)
                directory = run._directory_descriptor("proofs")
                try:
                    with os.fdopen(os.open(
                            "preflight.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                            0o600, dir_fd=directory), "wb") as output:
                        output.write(canonical_bytes({
                            "schemaVersion": 1, "qualification": False, "profileId": profile,
                            "filesystem": filesystem, "freeBytes": free_bytes,
                            "durationMs": (time.monotonic() - started) * 1000,
                        }))
                finally:
                    os.close(directory)
                return run
            finally:
                os.close(root)
        finally:
            os.close(parent_descriptor)

    def __init__(self, root, *, root_identity):
        self.root = root
        self.root_identity = root_identity
        self.root_id = uuid.uuid4().hex
        self.run_id = str(uuid.uuid4())
        self.owner_pid = os.getpid()
        self.owner_start = process_identity(self.owner_pid)
        if self.owner_start is None:
            raise ConformanceError("OwnershipInvalid")
        self.state = "Allocated"
        self.children = {}
        self.groups = set()
        self._group_handles = {}
        self.directory_identities = {}
        self.retained_bytes = 0
        self.command_sequence = 0
        self.cleanup_attempts = []
        self._writer = threading.RLock()
        self.started = time.monotonic()
        self.deadline = self.started + profile_budget("baseline")

    def _ledger(self):
        return {"schemaVersion": 2, "runId": self.run_id, "rootId": self.root_id,
                "ownerPid": self.owner_pid, "ownerStartSha256": self.owner_start,
                "state": self.state, "groups": sorted(self.groups),
                "directories": self.directory_identities,
                "cleanupAttempts": self.cleanup_attempts,
                "children": {str(pid): identity for pid, identity in self.children.items()}}

    def _root_descriptor(self):
        no_symlinks(self.root)
        try:
            descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            raise ConformanceError("OwnershipInvalid") from None
        info = os.fstat(descriptor)
        if ((info.st_dev, info.st_ino) != self.root_identity or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077):
            os.close(descriptor)
            raise ConformanceError("OwnershipInvalid")
        return descriptor

    def _directory_descriptor(self, name):
        if name not in self.directory_identities:
            raise ConformanceError("OwnershipInvalid")
        root = self._root_descriptor()
        descriptor = None
        try:
            descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
            info = os.fstat(descriptor)
            if ((info.st_dev, info.st_ino) != self.directory_identities[name]
                    or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
                raise ConformanceError("OwnershipInvalid")
            return descriptor
        except (ConformanceError, OSError):
            if descriptor is not None:
                os.close(descriptor)
            raise ConformanceError("OwnershipInvalid") from None
        finally:
            os.close(root)

    def _persist(self, *, create=False, state=None, cleanup_attempt=None, deadline=None):
        ledger = self._ledger()
        if state is not None:
            ledger["state"] = state
        if cleanup_attempt is not None:
            ledger["cleanupAttempts"] = [*self.cleanup_attempts, cleanup_attempt]
        data = canonical_bytes(ledger)
        if not create:
            self._check_ledger(deadline=deadline)
        directory = self._root_descriptor()
        partial = None
        try:
            name = "ownership.json" if create else "ownership.next"
            with os.fdopen(os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                   0o600, dir_fd=directory), "wb") as output:
                info = os.fstat(output.fileno())
                partial = (info.st_dev, info.st_ino)
                output.write(data)
            if not create:
                os.rename("ownership.next", "ownership.json", src_dir_fd=directory, dst_dir_fd=directory)
        except OSError:
            if not create and partial is not None:
                try:
                    info = os.stat(name, dir_fd=directory, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != partial:
                        raise ConformanceError("OwnershipInvalid") from None
                    os.unlink(name, dir_fd=directory)
            raise
        finally:
            os.close(directory)
        self._persisted = data
        if state is not None:
            self.state = state
        if cleanup_attempt is not None:
            self.cleanup_attempts.append(cleanup_attempt)

    def _check_ledger(self, *, deadline=None):
        directory = self._root_descriptor()
        try:
            descriptor = os.open("ownership.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            with os.fdopen(descriptor, "rb") as source:
                info = os.fstat(source.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > TRANSIENT_BYTES
                        or source.read(TRANSIENT_BYTES + 1) != self._persisted):
                    raise ConformanceError("OwnershipInvalid")
        except OSError:
            raise ConformanceError("OwnershipInvalid") from None
        finally:
            os.close(directory)
        if (self.owner_pid != os.getpid()
                or process_identity(self.owner_pid, deadline=deadline) != self.owner_start):
            raise ConformanceError("OwnershipInvalid")

    @single_writer
    def transition(self, state, *, deadline=None):
        allowed = {"Allocated": ("Active", "Settling"), "Active": ("Settling",),
                   "Settling": ("Retained",), "Retained": ("Settling",)}
        if state not in allowed.get(self.state, ()):
            raise ConformanceError("OwnershipInvalid")
        self._check_ledger(deadline=deadline)
        self._persist(state=state, deadline=deadline)

    def live_children(self, *, deadline=None):
        self._check_ledger(deadline=deadline)
        live = set()
        for pid, identity in self.children.items():
            observed = process_identity(pid, deadline=deadline)
            if observed is not None:
                if observed != identity:
                    raise ConformanceError("OwnershipInvalid")
                live.add(pid)
        for group in self.groups:
            live.update(self._group_members(group, deadline=deadline))
        return frozenset(live)

    def _admit_group_handle(self, group):
        try:
            handle = os.pidfd_open(group, 0)
        except (AttributeError, OSError):
            raise ConformanceError("PrerequisiteMissing") from None
        try:
            signal.pidfd_send_signal(handle, 0, None, PIDFD_SIGNAL_PROCESS_GROUP)
        except (AttributeError, OSError):
            os.close(handle)
            raise ConformanceError("PrerequisiteMissing") from None
        self._group_handles[group] = handle

    def _group_members(self, group, *, deadline=None):
        if group in self._group_handles:
            try:
                signal.pidfd_send_signal(self._group_handles[group], 0, None, PIDFD_SIGNAL_PROCESS_GROUP)
            except ProcessLookupError:
                return ()
            except OSError:
                raise ConformanceError("OwnershipInvalid") from None
        return process_group(group, deadline=deadline)

    def terminate(self, pid, *, deadline=None):
        deadline = min(time.monotonic() + 10, self.deadline,
                       deadline if deadline is not None else self.deadline)
        self._check_ledger(deadline=deadline)
        if pid not in self.children or process_identity(pid, deadline=deadline) != self.children[pid]:
            raise ConformanceError("OwnershipInvalid")
        self._terminate_group(pid, deadline)

    def _terminate_group(self, group, deadline):
        if group not in self._group_handles:
            raise ConformanceError("OwnershipInvalid")
        try:
            signal.pidfd_send_signal(self._group_handles[group], signal.SIGKILL, None, PIDFD_SIGNAL_PROCESS_GROUP)
        except ProcessLookupError:
            return
        except OSError:
            raise ConformanceError("CleanupIncomplete") from None
        while self._group_members(group, deadline=deadline):
            time.sleep(0.01)

    def _contain(self, child):
        deadline = min(time.monotonic() + 10, self.deadline)
        if child.pid in self._group_handles:
            self._terminate_group(child.pid, deadline)
        elif child.poll() is None:
            child.kill()
        try:
            child.wait(timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise ConformanceError("CleanupIncomplete") from None
        if self._group_members(child.pid, deadline=deadline):
            raise ConformanceError("CleanupIncomplete")

    @single_writer
    def command(self, args, *, cwd=None, timeout=None, kind="events", env=None,
                scope="ordinary", cache_id="default", deadline=None):
        started = time.monotonic()
        ceilings = {"control": 5, "barrier": 15, "ordinary": 600,
                    "transfer": 2400, "recovery": 300, "cleanup": 20}
        if scope not in ceilings:
            raise ConformanceError("OwnershipInvalid")
        timeout = ceilings[scope] if timeout is None else timeout
        if (type(timeout) not in (int, float) or not 0 < timeout <= ceilings[scope]
                or deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline))):
            raise ConformanceError("OwnershipInvalid")
        reserve = 0 if scope == "cleanup" else 40
        deadline = min(started + timeout, self.deadline - reserve,
                       deadline if deadline is not None else self.deadline)
        if time.monotonic() >= deadline:
            raise ConformanceError("DeadlineExceeded")
        self._check_ledger(deadline=deadline)
        if time.monotonic() >= deadline:
            raise ConformanceError("DeadlineExceeded")
        if scope == "cleanup" and (not isinstance(args, (list, tuple)) or list(args) != [
                sys.executable, "-I", "-S", str(Path(__file__).with_name("conformance_cleanup.py")),
                str(self.root), str(self.root_identity[0]), str(self.root_identity[1]),
                self.root_id, str(self.owner_pid), self.owner_start]
                or env is not None or cwd is not None):
            raise ConformanceError("OwnershipInvalid")
        for name in (("diagnostics",) if scope == "cleanup" else self.directory_identities):
            os.close(self._directory_descriptor(name))
        if not isinstance(cache_id, str) or re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", cache_id) is None:
            raise ConformanceError("OwnershipInvalid")
        cache = self.root / "cache" / cache_id
        no_symlinks(cache)
        if scope != "cleanup":
            cache.mkdir(exist_ok=True, mode=0o700)
        if (self.state not in ("Allocated", "Active") and not (scope == "cleanup" and self.state == "Settling")
                or self.live_children(deadline=deadline)
                or not isinstance(args, (list, tuple)) or not args
                or any(not isinstance(arg, str) or "\x00" in arg for arg in args)
                or kind not in ("events", "build", "tests")):
            raise ConformanceError("OwnershipInvalid")
        if self.retained_bytes + SAFE_EVENT_BYTES > PROFILE_DIAGNOSTIC_BYTES:
            raise ConformanceError("OutputLimitExceeded")
        if self.state == "Allocated":
            self.transition("Active", deadline=deadline)
        if time.monotonic() >= deadline:
            raise ConformanceError("DeadlineExceeded")
        if scope != "cleanup" and not native_execution_supported():
            raise ConformanceError("PrerequisiteMissing")
        environment = command_environment(self.root, cache, env)
        acknowledgement, writer = socket.socketpair()
        launch = (list(args) if scope == "cleanup" else
                  [sys.executable, "-I", "-S", str(Path(__file__).with_name("conformance_process.py")),
                   str(writer.fileno()), *args])
        try:
            child = subprocess.Popen(
                launch, cwd=cwd, env=environment,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True,
                pass_fds=(() if scope == "cleanup" else (writer.fileno(),)))
        except OSError:
            acknowledgement.close()
            raise ConformanceError("CommandFailed") from None
        finally:
            writer.close()
        self.command_sequence += 1
        destination = self.root / "diagnostics" / f"command-{self.command_sequence:04}.jsonl"
        events = []
        buffer = bytearray()
        retained = 0
        raw_total = 0
        failure = None

        def observe(line):
            nonlocal retained
            try:
                event = {"build": project_build_line, "tests": project_test_line,
                         "events": project_event}[kind](line)
            except ConformanceError as error:
                if str(error) == "OutputLimitExceeded":
                    raise
                raise ConformanceError("UnknownDiagnostic") from None
            if event is not None:
                size = len(canonical_bytes(event)) + 1
                if (retained + size + SAFE_EVENT_BYTES > CHILD_DIAGNOSTIC_BYTES
                        or self.retained_bytes + retained + size + SAFE_EVENT_BYTES > PROFILE_DIAGNOSTIC_BYTES):
                    raise ConformanceError("OutputLimitExceeded")
                events.append(event)
                retained += size

        try:
            self.groups.add(child.pid)
            if scope != "cleanup":
                self._admit_group_handle(child.pid)
            self._persist(deadline=deadline)
            identity = process_identity(child.pid, deadline=deadline)
            if identity is not None:
                self.children[child.pid] = identity
            self._persist(deadline=deadline)
            if scope != "cleanup":
                if time.monotonic() >= deadline:
                    raise ConformanceError("DeadlineExceeded")
                with selectors.DefaultSelector() as startup:
                    startup.register(acknowledgement, selectors.EVENT_READ)
                    if not startup.select(control_timeout(deadline)):
                        raise ConformanceError("DeadlineExceeded")
                    if acknowledgement.recv(2) != b"1":
                        raise ConformanceError("PrerequisiteMissing")
                acknowledgement.sendall(b"1")
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
                        if len(buffer) + len(block) > 2 * READ_BYTES or raw_total > CHILD_DIAGNOSTIC_BYTES:
                            raise ConformanceError("OutputLimitExceeded")
                        buffer.extend(block)
                        while b"\n" in buffer:
                            line, _, tail = buffer.partition(b"\n")
                            buffer = bytearray(tail)
                            if len(line) > READ_BYTES:
                                raise ConformanceError("OutputLimitExceeded")
                            if not line.strip():
                                continue
                            observe(bytes(line))
                        if len(buffer) > READ_BYTES:
                            raise ConformanceError("OutputLimitExceeded")
                if buffer.strip():
                    if len(buffer) > READ_BYTES:
                        raise ConformanceError("OutputLimitExceeded")
                    observe(bytes(buffer))
            code = child.wait(timeout=max(0.001, deadline - time.monotonic()))
            if self._group_members(child.pid, deadline=deadline):
                raise ConformanceError("CleanupIncomplete")
        except (ConformanceError, OSError, subprocess.SubprocessError, KeyboardInterrupt) as error:
            observed = (error if isinstance(error, (ConformanceError, KeyboardInterrupt)) else
                        ConformanceError("DeadlineExceeded" if isinstance(error, subprocess.TimeoutExpired)
                                         else "CommandFailed"))
            try:
                self._contain(child)
            except (ConformanceError, OSError, subprocess.SubprocessError):
                if self.state in ("Allocated", "Active"):
                    self.transition("Settling")
                if self.state == "Settling":
                    self.transition("Retained")
                events.append(MappingProxyType({
                    "event": "control", "code": str(observed) if isinstance(observed, ConformanceError)
                    else "EvidenceIncomplete", "value": 0,
                }))
                failure = ConformanceError("CleanupIncomplete")
            else:
                failure = observed
        finally:
            acknowledgement.close()
            child.stdout.close()
            if child.poll() is not None and not self._group_members(child.pid):
                self.children.pop(child.pid, None)
                self.groups.discard(child.pid)
                handle = self._group_handles.pop(child.pid, None)
                if handle is not None:
                    os.close(handle)
                self._persist()
        if failure is None and time.monotonic() >= deadline:
            failure = ConformanceError("DeadlineExceeded")
        if failure is not None:
            events.append(MappingProxyType({
                "event": "control", "code": str(failure) if isinstance(failure, ConformanceError)
                else "EvidenceIncomplete", "value": 0,
            }))
        self._retain_diagnostics(destination.name, events)
        if failure is not None:
            raise failure
        return CommandResult(code, tuple(events), (time.monotonic() - started) * 1000)

    def _retain_diagnostics(self, name, events):
        data = b"".join(canonical_bytes(event) + b"\n" for event in events)
        if len(data) > CHILD_DIAGNOSTIC_BYTES or self.retained_bytes + len(data) > PROFILE_DIAGNOSTIC_BYTES:
            raise ConformanceError("OutputLimitExceeded")
        try:
            directory = self._directory_descriptor("diagnostics")
            try:
                with os.fdopen(os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                       0o600, dir_fd=directory), "wb") as output:
                    output.write(data)
            finally:
                os.close(directory)
        except (ConformanceError, OSError):
            if self.state in ("Allocated", "Active"):
                self.transition("Settling")
            if self.state == "Settling":
                self.transition("Retained")
            raise ConformanceError("OwnershipInvalid") from None
        self.retained_bytes += len(data)

    @single_writer
    def release(self):
        started = time.monotonic() * 1000
        deadline = min(started / 1000 + 30, self.deadline)
        if self.state != "Settling":
            self._check_ledger(deadline=deadline)
            raise ConformanceError("CleanupIncomplete")
        if len(self.cleanup_attempts) >= 128:
            self._persist(state="Retained")
            raise ConformanceError("OutputLimitExceeded")
        try:
            self._check_ledger(deadline=deadline)
            if self.live_children(deadline=deadline):
                raise ConformanceError("CleanupIncomplete")
            self.children.clear()
            self.groups.clear()
            for handle in self._group_handles.values():
                os.close(handle)
            self._group_handles.clear()
            self._persist(deadline=deadline)
            result = self.command(
                [sys.executable, "-I", "-S", str(Path(__file__).with_name("conformance_cleanup.py")),
                 str(self.root), str(self.root_identity[0]), str(self.root_identity[1]),
                 self.root_id, str(self.owner_pid), self.owner_start],
                scope="cleanup", timeout=min(20, control_timeout(deadline) + 15), deadline=deadline - 10)
            if (result.exit_code or len(result.events) != 1
                    or dict(result.events[0]) != {"event": "cleanup", "code": "None", "value": 0}):
                code = next((event["code"] for event in result.events if event["code"] != "None"), "CleanupIncomplete")
                raise ConformanceError(code)
            self._check_ledger(deadline=deadline)
            if self.live_children(deadline=deadline) or any(
                    os.path.lexists(self.root / name) for name in ("stores", "feed", "cache")):
                raise ConformanceError("CleanupIncomplete")
            self._persist(state="Released", cleanup_attempt={
                "sequence": len(self.cleanup_attempts) + 1, "startedMs": started,
                "endedMs": time.monotonic() * 1000, "diagnosticCode": "None",
            }, deadline=deadline)
        except (ConformanceError, OSError) as error:
            self._persist(state="Retained", cleanup_attempt={
                "sequence": len(self.cleanup_attempts) + 1, "startedMs": started,
                "endedMs": time.monotonic() * 1000,
                "diagnosticCode": str(error) if isinstance(error, ConformanceError) else "CleanupIncomplete",
            })
            if not isinstance(error, ConformanceError):
                raise ConformanceError("CleanupIncomplete") from None
            raise

    def resource_projection(self):
        self._check_ledger()
        live = self.live_children()
        if self.state == "Released" and (
                live or any(os.path.lexists(self.root / name) for name in ("stores", "feed", "cache"))):
            raise ConformanceError("OwnershipInvalid")
        for name in ("diagnostics", "proofs"):
            os.close(self._directory_descriptor(name))
        duration = sum(attempt["endedMs"] - attempt["startedMs"] for attempt in self.cleanup_attempts)
        code = self.cleanup_attempts[-1]["diagnosticCode"] if self.cleanup_attempts else "None"
        return tuple(admit_entity("ResourceOwnership", {
            "runId": self.run_id, "rootId": self.root_id, "childPid": pid,
            "childStartSha256": process_identity(pid) if pid else "0" * 64,
            "state": self.state, "cleanupDurationMs": duration, "diagnosticCode": code,
        }) for pid in sorted(live) or [0])
