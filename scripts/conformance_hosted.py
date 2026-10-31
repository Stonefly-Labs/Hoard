"""GitHub-only original-owner coordination and exact bounded evidence transport."""

import argparse
from contextlib import contextmanager
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
import time
import uuid

import conformance_ci as ci
import conformance_evidence as evidence
from conformance_execution import no_symlinks
from conformance_sources import read_bounded

MANIFEST = "__transport_manifest__.json"
MAX_FILES = evidence.MAX_PROOF_FILES + 8
MAX_BYTES = evidence.MAX_PROOF_BYTES + 8 * evidence.MAX_REPORT_BYTES
MAX_BUNDLE_BYTES = MAX_BYTES + MAX_FILES * 1024 + 10240
WORKFLOWS = (".github/workflows/conformance.yml", ".github/workflows/conformance-profile.yml")


def _sha_revision(value):
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{40}", value) is None:
        raise evidence.ConformanceError("InputChanged")
    return value


def _number(value):
    if not isinstance(value, str) or re.fullmatch("[1-9][0-9]{0,19}", value) is None:
        raise evidence.ConformanceError("InputChanged")
    return value


def _git(repository, arguments):
    return evidence._git_control(repository, arguments, time.monotonic() + 5)


def _host_identity(repository):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise evidence.ConformanceError("UnsupportedProfile")
    revision = _sha_revision(os.environ.get("GITHUB_SHA"))
    workflow = _sha_revision(os.environ.get("GITHUB_WORKFLOW_SHA"))
    event = os.environ.get("GITHUB_EVENT_NAME")
    if event not in ("pull_request", "push", "workflow_dispatch"):
        raise evidence.ConformanceError("InputChanged")
    if (event == "push" and os.environ.get("GITHUB_REF") != "refs/heads/main"
            or event == "workflow_dispatch" and not os.environ.get("GITHUB_REF", "").startswith("refs/heads/")):
        raise evidence.ConformanceError("InputChanged")
    head = _sha_revision(os.environ.get("HOARD_HEAD_SHA")) if event == "pull_request" else revision
    if event == "pull_request":
        parents = _git(repository, ["rev-list", "--parents", "-n", "1", revision]).decode("ascii").split()
        if len(parents) != 3 or parents[0] != revision or parents[2] != head:
            raise evidence.ConformanceError("InputChanged")
    if _git(repository, ["rev-parse", "--is-shallow-repository"]) != b"false\n":
        raise evidence.ConformanceError("InputChanged")
    for path in WORKFLOWS:
        if _git(repository, ["show", workflow + ":" + path]) != read_bounded(
                repository / path, evidence.MAX_REPORT_BYTES):
            raise evidence.ConformanceError("InputChanged")
    identity = evidence.source_identity(repository, ci_revision=revision)
    return {
        **identity, "workflowRevision": workflow, "headRevision": head, "event": event,
        "runId": _number(os.environ.get("GITHUB_RUN_ID")),
        "runAttempt": _number(os.environ.get("GITHUB_RUN_ATTEMPT")),
    }


def _common(repository, identity, group):
    sources = evidence.source_manifest(repository)
    try:
        group = str(uuid.UUID(group))
    except (ValueError, TypeError, AttributeError):
        raise evidence.ConformanceError("InputChanged") from None
    return {
        "invocationGroupId": group, "sourceRevision": identity["sourceRevision"],
        "sourceState": "clean-ci", "sourceManifestSha256": evidence.digest(sources),
        "catalogRevision": evidence.CATALOG_REVISION,
        "catalogSha256": sources["tests/contracts/Hoard.Testing.Conformance/Catalog/catalog.json"],
        "sdkSha256": evidence.digest({
            path: hashed for path, hashed in sources.items()
            if path.startswith("tests/contracts/Hoard.Testing.Conformance/")}),
    }


def assignment(repository):
    identity = _host_identity(repository)
    group = str(uuid.uuid4())
    return {"schemaVersion": 1, "github": identity, "common": _common(repository, identity, group)}


def admit_assignment(repository, value):
    identity = _host_identity(repository)
    if (not isinstance(value, dict) or set(value) != {"schemaVersion", "github", "common"}
            or value["schemaVersion"] != 1 or value["github"] != identity):
        raise evidence.ConformanceError("InputChanged")
    common = value["common"]
    if not isinstance(common, dict) or common != _common(repository, identity, common.get("invocationGroupId")):
        raise evidence.ConformanceError("InputChanged")
    return value


def roots(repository, context):
    # The workflow's checkout path is identical on each fresh hosted runner.
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", "")).absolute()
    if workspace != repository:
        raise evidence.ConformanceError("OwnershipInvalid")
    github = context["github"]
    return repository.parent / f'hoard-f07-{github["runId"]}-{github["runAttempt"]}' / "profiles"


def _private_directory(path):
    no_symlinks(path)
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat(follow_symlinks=False)
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise evidence.ConformanceError("OwnershipInvalid")


def _path(value):
    value = evidence.relative_path(value)
    if value == MANIFEST or PurePosixPath(value).suffix.lower() in (
            ".trx", ".log", ".db", ".sqlite", ".sqlite3"):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    return value


@contextmanager
def _reader_files(root, source_manifest):
    """Observe unchanged independent reader calls, never replace their validation."""
    import conformance_composition_checks as composition
    import conformance_sdk_checks as sdk
    import conformance_sources as sources

    original = evidence._readonly_report_proof
    files = {}
    repository = Path(__file__).resolve().parents[1]

    def observe(selected, hashed):
        selected = Path(selected).absolute()
        if not selected.is_relative_to(root):
            if (not selected.is_relative_to(repository)
                    or source_manifest.get(selected.relative_to(repository).as_posix()) != hashed):
                raise evidence.ConformanceError("InputChanged")
            # Source-owned catalogs are already in the exact checkout and pinned input manifest.
            return
        path = _path(selected.relative_to(root).as_posix())
        if path in files and files[path] != hashed:
            raise evidence.ConformanceError("InputChanged")
        files[path] = hashed

    def read(selected_root, relative):
        hashed, raw = original(selected_root, relative)
        observe(Path(selected_root) / evidence.relative_path(relative), hashed)
        return hashed, raw

    bounded = [(module, module.read_bounded) for module in (sources, sdk, composition)]

    def wrap(reader):
        def read(path, limit):
            raw = reader(path, limit)
            observe(path, hashlib.sha256(raw).hexdigest())
            return raw
        return read

    evidence._readonly_report_proof = read
    for module, reader in bounded:
        module.read_bounded = wrap(reader)
    try:
        yield files
    finally:
        evidence._readonly_report_proof = original
        for module, reader in bounded:
            module.read_bounded = reader


def _closure(root, entry):
    profile = entry["inputs"]["profileId"]
    input_path, report_path = ci.profile_paths(profile)
    if report_path != entry["reportPath"]:
        raise evidence.ConformanceError("InputChanged")
    origin = evidence.admit_qualification_origin(entry["qualificationOrigin"], profile=profile)
    report_raw = read_bounded(root / report_path, evidence.MAX_REPORT_BYTES)
    with _reader_files(root, entry["inputs"]["sourceManifest"]) as reader_files:
        inspected = ci.inspect_receipted_profile_qualification(
            root, report_raw, expected_inputs=entry["inputs"],
            expected_report_sha256=entry["reportSha256"], qualification_origin=origin)
    if inspected["qualification"] is not True or inspected["code"] != "None":
        raise evidence.ConformanceError("EvidenceIncomplete")
    report = evidence.admit_entity("QualificationReport", evidence.load_json(report_raw))
    original_raw = read_bounded(root / origin["originalReportPath"], evidence.MAX_REPORT_BYTES)
    original = evidence.admit_entity("QualificationReport", evidence.load_json(original_raw))
    if any(report["proofs"].get(path) != hashed for path, hashed in original["proofs"].items()):
        raise evidence.ConformanceError("ProofMismatch")
    outputs = evidence._render_verified_fixture_qualification(report_raw, {
        "reportSha256": inspected["reportSha256"],
        "caseStates": {state: sum(row["status"] == state for row in report["results"])
                       for state in evidence.STATUSES},
    })
    for name, data in outputs.items():
        if read_bounded(root / "diagnostics" / name, evidence.MAX_REPORT_BYTES) != data:
            raise evidence.ConformanceError("ProofMismatch")
    if profile == "compatibility":
        # This existing reader admits the baseline seal directly, not through the readonly helper.
        seal = "proofs/baselines.json"
        reader_files[seal] = hashlib.sha256(read_bounded(root / seal, evidence.MAX_REPORT_BYTES)).hexdigest()
    paths = set(report["proofs"]) | set(reader_files) | {
        input_path, report_path, origin["originalReportPath"], "ownership.json",
        *("diagnostics/" + name for name in outputs),
    }
    if profile == "compatibility":
        paths.add(origin["summaryPath"])
    return paths, reader_files


def _header(name, size):
    member = tarfile.TarInfo(name)
    member.size = size
    member.mode = 0o600
    return member.tobuf(format=tarfile.USTAR_FORMAT, encoding="ascii", errors="strict")


def _archive_name(path):
    return "files/" + hashlib.sha256(path.encode("ascii")).hexdigest()


def _write_member(output, name, raw):
    output.write(_header(name, len(raw)))
    output.write(raw)
    output.write(b"\0" * (-len(raw) % 512))


def _output_file(path):
    no_symlinks(path)
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb")


def pack_profile(root, entry, destination, *, deadline=None):
    """Only independently verified declared proofs, finite renders and fixed reader inputs."""
    deadline = time.monotonic() + 300 if deadline is None else deadline
    closure, reader_files = _closure(root, entry)
    paths = sorted(closure)
    if len(paths) > MAX_FILES:
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    files, total = {}, 0
    with evidence._input_root(root) as (_, descriptor):
        for path in paths:
            _path(path)
            hashed, size = evidence._source_file(
                descriptor, path, remaining=evidence.MAX_PROOF_BYTES, deadline=deadline)
            total += size
            files[path] = {"sha256": hashed, "size": size}
            if path in reader_files and hashed != reader_files[path]:
                raise evidence.ConformanceError("InputChanged")
        if total > MAX_BYTES:
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        manifest = {
            "schemaVersion": 1, "rootPathSha256": hashlib.sha256(str(root).encode()).hexdigest(),
            "inputsSha256": evidence.digest(entry["inputs"]), "reportPath": entry["reportPath"],
            "files": files, "readerFiles": reader_files,
        }
        manifest_raw = evidence.canonical_bytes(manifest)
        if len(manifest_raw) > evidence.MAX_REPORT_BYTES:
            raise evidence.ConformanceError("OutputLimitExceeded")
        with _output_file(destination) as output:
            _write_member(output, MANIFEST, manifest_raw)
            for path, expected in files.items():
                output.write(_header(_archive_name(path), expected["size"]))
                hashed, size = evidence._source_file(
                    descriptor, path, remaining=expected["size"], deadline=deadline, target=output)
                if hashed != expected["sha256"] or size != expected["size"]:
                    raise evidence.ConformanceError("ProofMismatch")
                output.write(b"\0" * (-size % 512))
            output.write(b"\0" * 1024)
    return {
        "schemaVersion": 1, "profileId": entry["inputs"]["profileId"],
        "inputsSha256": evidence.digest(entry["inputs"]), "reportSha256": entry["reportSha256"],
        "qualificationOrigin": entry["qualificationOrigin"],
        "qualificationOriginSha256": evidence.digest(entry["qualificationOrigin"]),
        "manifestSha256": hashlib.sha256(manifest_raw).hexdigest(),
        "transportSha256": _file_digest(destination, deadline),
        "rootPathSha256": manifest["rootPathSha256"],
    }


def _stream_digest(source, size, deadline, *, target=None):
    hashed = hashlib.sha256()
    remaining = size
    while remaining:
        if time.monotonic() >= deadline:
            raise evidence.ConformanceError("DeadlineExceeded")
        raw = source.read(min(1024 * 1024, remaining))
        if not raw:
            raise evidence.ConformanceError("ProofMismatch")
        remaining -= len(raw)
        hashed.update(raw)
        if target is not None:
            target.write(raw)
    if time.monotonic() >= deadline:
        raise evidence.ConformanceError("DeadlineExceeded")
    return hashed.hexdigest()


def _bundle_file(path):
    no_symlinks(path)
    source = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb")
    info = os.fstat(source.fileno())
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_BUNDLE_BYTES:
        source.close()
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    return source


def _file_digest(path, deadline):
    with _bundle_file(path) as source:
        return _stream_digest(source, os.fstat(source.fileno()).st_size, deadline)


def _manifest(raw, pin, root):
    if hashlib.sha256(raw).hexdigest() != pin["manifestSha256"]:
        raise evidence.ConformanceError("ProofMismatch")
    value = evidence.load_json(raw)
    if (not isinstance(value, dict) or set(value) != {
            "schemaVersion", "rootPathSha256", "inputsSha256", "reportPath", "files", "readerFiles"}
            or value["schemaVersion"] != 1 or value["inputsSha256"] != pin["inputsSha256"]
            or value["reportPath"] != ci.profile_paths(pin["profileId"])[1]
            or value["rootPathSha256"] != pin["rootPathSha256"]
            or value["rootPathSha256"] != hashlib.sha256(str(root).encode()).hexdigest()):
        raise evidence.ConformanceError("InputChanged")
    files = value["files"]
    if not isinstance(files, dict) or not 0 < len(files) <= MAX_FILES:
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    total, folded = 0, set()
    for path, row in files.items():
        _path(path)
        if (path.casefold() in folded or not isinstance(row, dict)
                or set(row) != {"sha256", "size"} or type(row["size"]) is not int or row["size"] < 0
                or row["size"] > evidence.MAX_PROOF_BYTES):
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        evidence.sha256(row["sha256"])
        folded.add(path.casefold())
        total += row["size"]
    if total > MAX_BYTES or any(
            "/".join(PurePosixPath(path).parts[:i]).casefold() in folded
            for path in files for i in range(1, len(PurePosixPath(path).parts))):
        raise evidence.ConformanceError("EvidenceSchemaInvalid")
    readers = value["readerFiles"]
    if (not isinstance(readers, dict) or len(readers) > MAX_FILES
            or any(path not in files or evidence.sha256(hashed) != files[path]["sha256"]
                   for path, hashed in readers.items())):
        raise evidence.ConformanceError("ProofMismatch")
    return value


def admit_pin(value, profile):
    if (not isinstance(value, dict) or set(value) != {
            "schemaVersion", "profileId", "inputsSha256", "reportSha256", "qualificationOrigin",
            "qualificationOriginSha256", "manifestSha256", "transportSha256", "rootPathSha256"}
            or value["schemaVersion"] != 1 or value["profileId"] != profile):
        raise evidence.ConformanceError("InputChanged")
    for key in ("inputsSha256", "reportSha256", "qualificationOriginSha256", "manifestSha256",
                "transportSha256", "rootPathSha256"):
        evidence.sha256(value[key])
    origin = evidence.admit_qualification_origin(value["qualificationOrigin"], profile=profile)
    if (evidence.digest(origin) != value["qualificationOriginSha256"]
            or origin["inputsSha256"] != value["inputsSha256"]
            or origin["reportSha256"] != value["reportSha256"]):
        raise evidence.ConformanceError("InputChanged")
    return value


def _walk(source, pin, root, deadline, *, extract=False):
    source.seek(0)
    manifest = None
    captured = {}
    expected_paths = [MANIFEST]
    index = 0
    input_path, report_path = ci.profile_paths(pin["profileId"])
    capture_paths = {input_path, report_path, pin["qualificationOrigin"]["originalReportPath"]}
    archive_paths = {}
    while True:
        if time.monotonic() >= deadline:
            raise evidence.ConformanceError("DeadlineExceeded")
        header = source.read(512)
        if header == b"\0" * 512:
            tail = source.read(10241)
            if len(tail) < 512 or len(tail) > 10240 or any(tail) or index != len(expected_paths):
                raise evidence.ConformanceError("ProofMismatch")
            break
        if len(header) != 512:
            raise evidence.ConformanceError("ProofMismatch")
        try:
            member = tarfile.TarInfo.frombuf(header, "ascii", "strict")
            canonical = _header(member.name, member.size)
        except (tarfile.TarError, ValueError, UnicodeError):
            raise evidence.ConformanceError("EvidenceSchemaInvalid") from None
        if (header != canonical or index >= len(expected_paths) or member.name != expected_paths[index]
                or member.size < 0):
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        if manifest is None:
            if member.size > evidence.MAX_REPORT_BYTES:
                raise evidence.ConformanceError("EvidenceSchemaInvalid")
            raw = source.read(member.size)
            manifest = _manifest(raw, pin, root)
            archive_paths = {_archive_name(path): path for path in sorted(manifest["files"])}
            if len(archive_paths) != len(manifest["files"]):
                raise evidence.ConformanceError("EvidenceSchemaInvalid")
            expected_paths.extend(archive_paths)
        else:
            path = archive_paths[member.name]
            expected = manifest["files"][path]
            if member.size != expected["size"]:
                raise evidence.ConformanceError("ProofMismatch")
            buffer = io.BytesIO() if path in capture_paths else None
            if buffer is not None and member.size > evidence.MAX_REPORT_BYTES:
                raise evidence.ConformanceError("EvidenceSchemaInvalid")
            if extract:
                target = root / path
                current = root
                for component in PurePosixPath(path).parts[:-1]:
                    current /= component
                    _private_directory(current)
                with _output_file(target) as output:
                    hashed = _stream_digest(source, member.size, deadline, target=output)
                target.chmod(0o400)
            else:
                hashed = _stream_digest(source, member.size, deadline, target=buffer)
            if hashed != expected["sha256"]:
                raise evidence.ConformanceError("ProofMismatch")
            if buffer is not None and not extract:
                captured[path] = buffer.getvalue()
        padding = source.read(-member.size % 512)
        if len(padding) != -member.size % 512 or any(padding):
            raise evidence.ConformanceError("ProofMismatch")
        index += 1
    if manifest is None:
        raise evidence.ConformanceError("EvidenceIncomplete")
    return manifest, captured


def unpack_profile(bundle, pin, root, *, common_context, deadline=None):
    """Validate bytes/closure before create-new extraction at the unchanged original root."""
    deadline = time.monotonic() + 600 if deadline is None else deadline
    pin = admit_pin(pin, pin["profileId"])
    with _bundle_file(bundle) as source:
        size = os.fstat(source.fileno()).st_size
        if _stream_digest(source, size, deadline) != pin["transportSha256"]:
            raise evidence.ConformanceError("ProofMismatch")
        manifest, captured = _walk(source, pin, root, deadline)
        input_path, report_path = ci.profile_paths(pin["profileId"])
        if not {input_path, report_path, pin["qualificationOrigin"]["originalReportPath"]} <= captured.keys():
            raise evidence.ConformanceError("EvidenceIncomplete")
        inputs = evidence.admit_entity("RunInputs", evidence.load_json(captured[input_path]))
        report = evidence.admit_entity("QualificationReport", evidence.load_json(captured[report_path]))
        origin = pin["qualificationOrigin"]
        original = evidence.admit_entity(
            "QualificationReport", evidence.load_json(captured[origin["originalReportPath"]]))
        if (evidence.digest(inputs) != pin["inputsSha256"] or report["inputs"] != inputs
                or inputs["profileId"] != pin["profileId"]
                or ci._common_context(inputs) != ci._common_context(common_context)
                or hashlib.sha256(captured[report_path]).hexdigest() != pin["reportSha256"]
                or hashlib.sha256(captured[origin["originalReportPath"]]).hexdigest()
                != origin["originalReportSha256"]
                or any(report["proofs"].get(path) != hashed for path, hashed in original["proofs"].items())):
            raise evidence.ConformanceError("InputChanged")
        inspected = {"reportSha256": pin["reportSha256"], "caseStates": {
            status: sum(row["status"] == status for row in report["results"])
            for status in ("Passed", "Failed", "NotApplicable", "Incomplete")}}
        presentations = evidence._render_verified_fixture_qualification(captured[report_path], inspected)
        paths = set(report["proofs"]) | set(manifest["readerFiles"]) | {
            input_path, report_path, origin["originalReportPath"], "ownership.json",
            *("diagnostics/" + name for name in presentations),
        }
        if inputs["profileId"] == "compatibility":
            paths.add(origin["summaryPath"])
        if set(manifest["files"]) != paths or any(
                manifest["files"][path]["sha256"] != hashed for path, hashed in report["proofs"].items()):
            raise evidence.ConformanceError("ProofMismatch")
        no_symlinks(root)
        if root.exists():
            raise evidence.ConformanceError("OwnershipInvalid")
        _private_directory(root.parent.parent)
        _private_directory(root.parent)
        root.mkdir(mode=0o700)
        _walk(source, pin, root, deadline, extract=True)
        source.seek(0)
        if (os.fstat(source.fileno()).st_size != size
                or _stream_digest(source, size, deadline) != pin["transportSha256"]):
            raise evidence.ConformanceError("ProofMismatch")
    entry = {
        "inputs": inputs, "reportSha256": pin["reportSha256"], "reportPath": report_path,
        "qualificationOrigin": origin,
    }
    # Replay source-specific independent readers and exact finite bytes after download.
    observed_paths, observed_readers = _closure(root, entry)
    if set(manifest["files"]) != observed_paths or manifest["readerFiles"] != observed_readers:
        raise evidence.ConformanceError("ProofMismatch")
    if time.monotonic() >= deadline:
        raise evidence.ConformanceError("DeadlineExceeded")
    return entry


def _json_environment(name):
    raw = os.environ.get(name, "").encode("utf-8")
    if not 0 < len(raw) <= 512 * 1024:
        raise evidence.ConformanceError("EvidenceIncomplete")
    return evidence.load_json(raw)


def _outputs(values):
    raw = "".join(key + "=" + evidence.canonical_bytes(value).decode("ascii") + "\n"
                  for key, value in values.items()).encode("ascii")
    if len(raw) > 64 * 1024:
        raise evidence.ConformanceError("OutputLimitExceeded")
    with open(os.environ["GITHUB_OUTPUT"], "ab") as output:
        output.write(raw)


def _summary(path, code, *, profile=None, preflight=None):
    value = {"schemaVersion": 1, "qualification": False, "state": "Incomplete", "code": code}
    if profile is not None:
        value["profileId"] = profile
    if preflight is not None:
        value["environment"] = preflight
    path.write_bytes(evidence.canonical_bytes(value))


def _failure_projection(path, code, *, profile=None, failure_phase="boundary"):
    """Retain the primary failure and separately expose diagnostic boundary failures."""
    preflight = None
    read_code = "None"
    try:
        retained = evidence.load_json(read_bounded(path, 65536))
        if not isinstance(retained, dict):
            raise evidence.ConformanceError("EvidenceSchemaInvalid")
        if retained.get("environment") is not None:
            preflight = evidence.admit_entity("Environment", retained["environment"])
    except evidence.ConformanceError as error:
        read_code = str(error)
    except OSError:
        read_code = "CommandFailed"
    value = {
        "schemaVersion": 1, "qualification": False, "state": "Incomplete", "code": code,
        "failurePhase": failure_phase,
        "diagnostics": {"preflightReadCode": read_code, "persistenceCode": "None"},
    }
    if profile is not None:
        value["profileId"] = profile
    if preflight is not None:
        value["environment"] = preflight
    try:
        no_symlinks(path)
        path.write_bytes(evidence.canonical_bytes(value))
    except evidence.ConformanceError as error:
        value["diagnostics"]["persistenceCode"] = str(error)
    except OSError:
        value["diagnostics"]["persistenceCode"] = "CommandFailed"
    return {key: selected for key, selected in value.items() if key != "environment"}


def _unexpected_driver_failure(exception_type, exception, traceback):
    """Unhandled programmer failures remain nonzero without a raw traceback or error text."""
    print(evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False, "state": "Incomplete",
        "code": "CommandFailed", "failurePhase": "driver",
    }).decode("ascii"), file=sys.stderr)


def produce(repository, profile, context, staging):
    import conformance_sdk_checks as sdk

    context = admit_assignment(repository, context)
    profiles = roots(repository, context)
    _private_directory(profiles.parent)
    _private_directory(profiles)
    image_os, version = os.environ.get("ImageOS"), os.environ.get("ImageVersion", "")
    if image_os != "ubuntu24" or re.fullmatch("[0-9]{8}\\.[0-9]+\\.[0-9]+", version) is None:
        raise evidence.ConformanceError("PrerequisiteMissing")
    probe_path = profiles.parent / (profile + "-preflight.json")
    os.environ["HOARD_RUNNER_IMAGE"] = image_os + "." + version
    sdk.probe(probe_path)
    preflight = evidence.admit_entity("Environment", evidence.load_json(read_bounded(probe_path, 65536)))
    _summary(staging / "summary.json", "EvidenceIncomplete", profile=profile, preflight=preflight)
    if preflight["freeBytes"] < 24 * 1024**3:
        _summary(staging / "summary.json", "InsufficientCapacity", profile=profile, preflight=preflight)
        raise evidence.ConformanceError("InsufficientCapacity")
    destination = profiles / profile
    entry = ci.execute_hosted_profile(repository, profile, destination, common_context=context["common"])
    pin = pack_profile(destination, entry, staging / "profile.tar.incomplete")
    if (staging / "profile.tar").exists():
        raise evidence.ConformanceError("OwnershipInvalid")
    (staging / "profile.tar.incomplete").rename(staging / "profile.tar")
    _outputs({"receipt": pin})
    # This says only that the producer finished; the aggregate must observe real transport statuses.
    _summary(staging / "summary.json", "None", profile=profile, preflight=preflight)


def aggregate(repository, context, needs, downloads, staging):
    context = admit_assignment(repository, context)
    if (not isinstance(needs, dict) or not isinstance(downloads, dict)
            or set(downloads) != set(evidence.PROFILES)):
        raise evidence.ConformanceError("EvidenceIncomplete")
    if needs.get("assignment", {}).get("result") != "success":
        raise evidence.ConformanceError("EvidenceIncomplete")
    pins = {}
    for profile in evidence.PROFILES:
        job = needs.get(profile)
        if (not isinstance(job, dict) or job.get("result") != "success"
                or job.get("outputs", {}).get("producer") != "success"
                or job.get("outputs", {}).get("upload") != "success"
                or downloads[profile] != "success"):
            raise evidence.ConformanceError("EvidenceIncomplete")
        pins[profile] = admit_pin(evidence.load_json(job["outputs"]["receipt"].encode("ascii")), profile)
    profiles = roots(repository, context)
    deadline = time.monotonic() + 600
    entries = {}
    for profile in evidence.PROFILES:
        entry = unpack_profile(
            staging / "downloads" / profile / "profile.tar", pins[profile], profiles / profile,
            common_context=context["common"], deadline=deadline)
        entries[profile] = {**entry, "jobResults": {
            "job": needs[profile]["result"], "upload": needs[profile]["outputs"]["upload"],
            "download": downloads[profile],
        }}
    coordinator = {
        "schemaVersion": 2, "configurationPolicy": evidence.configuration_policy(), "profiles": entries,
    }
    ci.admit_coordinator(coordinator, require_all=True)
    coordinator_path = staging / "coordinator.json"
    coordinator_raw = evidence.canonical_bytes(coordinator)
    if len(coordinator_raw) > evidence.MAX_REPORT_BYTES:
        raise evidence.ConformanceError("OutputLimitExceeded")
    with _output_file(coordinator_path) as output:
        output.write(coordinator_raw)
    # This public path replays all five original native receipts; it does not mint native tokens.
    output = io.StringIO()
    with ci.redirect_stdout(output):
        status = ci.inspect_offline(evidence.admit_invocation(repository, [
            "--aggregate", str(profiles), "--coordinator", str(coordinator_path)]))
    if status != 0:
        raise evidence.ConformanceError("EvidenceIncomplete")
    result = evidence.load_json(output.getvalue().encode("ascii"))
    if result.get("qualification") is not True or result.get("code") != "None":
        raise evidence.ConformanceError("EvidenceIncomplete")
    result_raw = evidence.canonical_bytes(result)
    if len(result_raw) > evidence.MAX_REPORT_BYTES or time.monotonic() >= deadline:
        raise evidence.ConformanceError("OutputLimitExceeded" if len(result_raw) > evidence.MAX_REPORT_BYTES
                                        else "DeadlineExceeded")
    (staging / "summary.json").write_bytes(result_raw)
    print(result_raw.decode("ascii"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("assignment", "produce", "aggregate"))
    parser.add_argument("--profile", choices=evidence.PROFILES)
    args = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[1]
    staging = repository / ".foundation" / "hosted" / (args.profile or args.action)
    completed = False
    handled = False
    try:
        staging.mkdir(parents=True, mode=0o700, exist_ok=True)
        _summary(staging / "summary.json", "EvidenceIncomplete", profile=args.profile)
        if args.action == "assignment":
            _outputs({"assignment": assignment(repository)})
        elif args.action == "produce":
            if args.profile is None:
                raise evidence.ConformanceError("UnsupportedProfile")
            produce(repository, args.profile, _json_environment("HOARD_ASSIGNMENT"), staging)
        else:
            aggregate(repository, _json_environment("HOARD_ASSIGNMENT"),
                      _json_environment("HOARD_NEEDS"), _json_environment("HOARD_DOWNLOADS"), staging)
        completed = True
        return 0
    except (evidence.ConformanceError, OSError) as error:
        handled = True
        code = ("CommandFailed" if isinstance(error, OSError) else
                str(error) if str(error) != "None" else "EvidenceIncomplete")
        # Partial bundles stay private and unuploaded; the closed failure remains retained.
        print(evidence.canonical_bytes(_failure_projection(
            staging / "summary.json", code, profile=args.profile)).decode("ascii"))
        return 2
    finally:
        if not completed and not handled:
            # Do not consume unexpected exceptions: callers still receive the original failure.
            _failure_projection(
                staging / "summary.json", "CommandFailed", profile=args.profile, failure_phase="driver")


if __name__ == "__main__":
    sys.excepthook = _unexpected_driver_failure
    raise SystemExit(main())
