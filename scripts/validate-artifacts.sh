#!/usr/bin/env bash
set -euo pipefail

for prerequisite in dotnet python3 git; do
    command -v "$prerequisite" >/dev/null || {
        printf 'Artifact prerequisite missing: %s\n' "$prerequisite" >&2
        exit 1
    }
done

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
exec python3 -B "$root/scripts/artifact_evidence.py" "$root" "$@"
