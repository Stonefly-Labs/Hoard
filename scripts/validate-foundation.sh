#!/usr/bin/env bash
set -euo pipefail

for prerequisite in dotnet python3 mktemp; do
    command -v "$prerequisite" >/dev/null || {
        printf 'Foundation prerequisite missing: %s\n' "$prerequisite" >&2
        exit 1
    }
done

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
work="$(mktemp -d "${TMPDIR:-/tmp}/hoard-foundation.XXXXXXXX")"
work="$(cd "$work" && pwd -P)"
trap 'python3 -c "import shutil,sys; shutil.rmtree(sys.argv[1])" "$work"' EXIT
python3 "$root/scripts/foundation_evidence.py" "$root" "$work" "$@"
