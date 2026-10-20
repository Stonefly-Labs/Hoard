#!/usr/bin/env bash
set -euo pipefail

for prerequisite in dotnet python3 git; do
    command -v "$prerequisite" >/dev/null || {
        printf 'Lifecycle prerequisite missing: %s\n' "$prerequisite" >&2
        exit 1
    }
done

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
python3 "$root/scripts/lifecycle_evidence.py" "$root" "$@"
