#!/usr/bin/env bash
set -euo pipefail

for prerequisite in python3 dotnet git; do
    command -v "$prerequisite" >/dev/null || {
        printf '{"mode":"preparation","qualification":false,"status":"Incomplete","code":"PrerequisiteMissing"}\n' >&2
        exit 2
    }
done

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
exec python3 "$root/scripts/conformance_prepare.py" --root "$root" "$@"
