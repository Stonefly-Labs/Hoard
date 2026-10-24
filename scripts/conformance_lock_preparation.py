"""Explicit, non-qualifying local archive preparation without graph resolution."""

import base64
import hashlib
from pathlib import Path

from conformance_evidence import ConformanceError, canonical_bytes, load_json, relative_path, stable_id
from conformance_execution import no_symlinks


def read_lock(path):
    no_symlinks(path)
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise ConformanceError("InputChanged")
    with path.open("rb") as source:
        raw = source.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ConformanceError("OutputLimitExceeded")
    return raw


def rebind_local_archives(raw, feed):
    document = load_json(raw)
    if (not isinstance(document, dict) or type(document.get("version")) is not int
            or document["version"] not in (1, 2)
            or not isinstance(document.get("dependencies"), dict) or not document["dependencies"]):
        raise ConformanceError("InputChanged")
    original = canonical_bytes(document)
    packages = {}
    archive_bytes = 0
    for dependencies in document["dependencies"].values():
        if not isinstance(dependencies, dict):
            raise ConformanceError("InputChanged")
        for package_id, dependency in dependencies.items():
            stable_id(package_id)
            if not isinstance(dependency, dict):
                raise ConformanceError("InputChanged")
            if not package_id.startswith("Hoard.") or "contentHash" not in dependency:
                continue
            version = dependency.get("resolved")
            if version != "0.1.0":
                raise ConformanceError("InputChanged")
            filename = f"{package_id}.{version}.nupkg"
            package = feed / filename
            no_symlinks(package)
            if not package.is_file():
                raise ConformanceError("PrerequisiteMissing")
            if package.stat().st_size > 64 * 1024 * 1024:
                raise ConformanceError("OutputLimitExceeded")
            archive_sha = hashlib.sha256()
            content_sha = hashlib.sha512()
            total = 0
            with package.open("rb") as archive:
                while block := archive.read(64 * 1024):
                    total += len(block)
                    archive_bytes += len(block)
                    if total > 64 * 1024 * 1024 or archive_bytes > 256 * 1024 * 1024:
                        raise ConformanceError("OutputLimitExceeded")
                    archive_sha.update(block)
                    content_sha.update(block)
            dependency["contentHash"] = base64.b64encode(content_sha.digest()).decode("ascii")
            packages[filename] = archive_sha.hexdigest()
            if len(packages) > 1024:
                raise ConformanceError("OutputLimitExceeded")
    prepared = canonical_bytes(document)
    return prepared + b"\n", packages, prepared != original


def prepare_project_lock(project, source, feed, feed_id):
    original = project.parent / "packages.lock.json"
    raw = read_lock(original)
    prepared, packages, changed = rebind_local_archives(raw, feed)
    if not changed:
        return None, None
    alternate = project.parent / "obj/F07.preparation.packages.lock.json"
    no_symlinks(alternate)
    alternate.parent.mkdir(exist_ok=True, mode=0o700)
    with alternate.open("xb") as output:
        output.write(prepared)
    alternate.chmod(0o400)
    record = {
        "schemaVersion": 1, "mode": "preparation", "qualification": False,
        "project": relative_path(project.relative_to(source).as_posix()),
        "originalLock": relative_path(original.relative_to(source).as_posix()),
        "originalSha256": hashlib.sha256(raw).hexdigest(),
        "preparedLock": relative_path(alternate.relative_to(source).as_posix()),
        "preparedSha256": hashlib.sha256(prepared).hexdigest(),
        "feedId": stable_id(feed_id), "packages": packages,
    }
    return alternate, record


def verify_project_lock(record, source, feed):
    fields = {"schemaVersion", "mode", "qualification", "project", "originalLock", "originalSha256",
              "preparedLock", "preparedSha256", "feedId", "packages"}
    if (not isinstance(record, dict) or set(record) != fields
            or type(record["schemaVersion"]) is not int or record["schemaVersion"] != 1
            or record["mode"] != "preparation" or record["qualification"] is not False):
        raise ConformanceError("InputChanged")
    project = Path(relative_path(record["project"]))
    if (record["originalLock"] != (project.parent / "packages.lock.json").as_posix()
            or record["preparedLock"] != (project.parent / "obj/F07.preparation.packages.lock.json").as_posix()):
        raise ConformanceError("InputChanged")
    raw = read_lock(source / relative_path(record["originalLock"]))
    actual = read_lock(source / relative_path(record["preparedLock"]))
    prepared, packages, changed = rebind_local_archives(raw, feed)
    if (not changed or hashlib.sha256(raw).hexdigest() != record["originalSha256"]
            or hashlib.sha256(actual).hexdigest() != record["preparedSha256"]
            or actual != prepared or record["packages"] != packages):
        raise ConformanceError("InputChanged")
