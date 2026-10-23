"""Delete only settled, identity-checked synthetic contents; preserve ownership."""

import os
import json
from pathlib import Path
import stat
import sys
import time


class CleanupFailure(Exception):
    pass


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CleanupFailure("OwnershipInvalid")
        result[key] = value
    return result


def clean(directory, deadline, *, root=False, depth=0, count=None):
    if depth > 32:
        raise CleanupFailure("CleanupIncomplete")
    count = [0] if count is None else count
    with os.scandir(directory) as entries:
        clean_entries(entries, directory, deadline, root, depth, count)


def clean_entries(entries, directory, deadline, root, depth, count):
    for entry in entries:
        if time.monotonic() >= deadline:
            raise CleanupFailure("DeadlineExceeded")
        count[0] += 1
        if count[0] > 1_000_000:
            raise CleanupFailure("CleanupIncomplete")
        name = entry.name
        if root and name == "ownership.json":
            continue
        info = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            raise CleanupFailure("OwnershipInvalid")
        if stat.S_ISDIR(info.st_mode):
            nested = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            try:
                clean(nested, deadline, depth=depth + 1, count=count)
            finally:
                os.close(nested)
            if not (root and name == "diagnostics"):
                os.rmdir(name, dir_fd=directory)
        else:
            os.unlink(name, dir_fd=directory)


def main():
    code = "None"
    try:
        path = Path(sys.argv[1])
        for ancestor in (path, *path.parents):
            if ancestor.is_symlink():
                raise CleanupFailure("OwnershipInvalid")
        directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(directory)
            if ((info.st_dev, info.st_ino) != (int(sys.argv[2]), int(sys.argv[3]))
                    or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
                raise CleanupFailure("OwnershipInvalid")
            ledger = os.open("ownership.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            with os.fdopen(ledger, "rb") as source:
                encoded = source.read(65537)
            if len(encoded) > 65536:
                raise CleanupFailure("OwnershipInvalid")
            owner = json.loads(encoded, object_pairs_hook=unique_fields)
            if (not isinstance(owner, dict) or set(owner) !=
                    {"schemaVersion", "runId", "rootId", "ownerPid", "ownerStartSha256",
                     "state", "children", "groups", "directories"}
                    or type(owner["schemaVersion"]) is not int or owner["schemaVersion"] != 1
                    or owner["rootId"] != sys.argv[4] or owner["ownerPid"] != int(sys.argv[5])
                    or owner["ownerPid"] != os.getppid() or owner["ownerStartSha256"] != sys.argv[6]
                    or owner["state"] != "Settling"):
                raise CleanupFailure("OwnershipInvalid")
            identities = owner["directories"]
            if (not isinstance(identities, dict) or set(identities) !=
                    {"stores", "feed", "cache", "diagnostics", "proofs"}):
                raise CleanupFailure("OwnershipInvalid")
            for name, identity in identities.items():
                if (not isinstance(identity, list) or len(identity) != 2
                        or any(type(part) is not int or part < 0 for part in identity)):
                    raise CleanupFailure("OwnershipInvalid")
                try:
                    child = os.stat(name, dir_fd=directory, follow_symlinks=False)
                except FileNotFoundError:
                    if name == "diagnostics":
                        raise CleanupFailure("OwnershipInvalid") from None
                    continue
                if (not stat.S_ISDIR(child.st_mode) or (child.st_dev, child.st_ino) != tuple(identity)
                        or child.st_uid != os.getuid() or stat.S_IMODE(child.st_mode) & 0o077):
                    raise CleanupFailure("OwnershipInvalid")
            clean(directory, time.monotonic() + 19, root=True)
        finally:
            os.close(directory)
    except CleanupFailure as error:
        code = str(error)
    except (OSError, ValueError, IndexError, RecursionError):
        code = "CleanupIncomplete"
    print('{"event":"cleanup","code":"' + code + '","value":0}')
    return 0 if code == "None" else 2


if __name__ == "__main__":
    sys.exit(main())
