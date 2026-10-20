#!/usr/bin/env python3
"""Validate Hoard source-release tags and optionally their main-branch ancestry."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = re.compile(
    r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?",
    re.ASCII,
)


def metadata(tag):
    match = TAG.fullmatch(tag)
    if not match:
        raise ValueError("Use vMAJOR.MINOR.PATCH or vMAJOR.MINOR.PATCH-prerelease (no build metadata).")
    prerelease = match[4]
    if prerelease and any(
        part.isdigit() and len(part) > 1 and part.startswith("0")
        for part in prerelease.split(".")
    ):
        raise ValueError("Numeric prerelease identifiers must not have leading zeroes.")
    return {"tag": tag, "prerelease": "true" if prerelease else "false"}


def check_main(root, tag):
    metadata(tag)
    commit = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "origin/main"],
        cwd=root, check=True, capture_output=True, text=True,
    )
    return commit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--check-main", action="store_true")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    try:
        result = metadata(args.tag)
        if args.check_main:
            result["commit"] = check_main(ROOT, args.tag)
        if args.github_output:
            with args.github_output.open("a") as output:
                output.write(f"prerelease={result['prerelease']}\n")
        print(json.dumps(result))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            detail = error.stderr.strip() or "Tag is missing or its commit is not reachable from origin/main."
        else:
            detail = str(error)
        print(f"Release blocked: {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
