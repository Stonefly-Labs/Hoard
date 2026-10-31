#!/usr/bin/env bash
set -euo pipefail

command -v python3 >/dev/null || {
    printf '{"mode":"diagnostic","qualification":false,"status":"Incomplete","code":"PrerequisiteMissing"}\n' >&2
    exit 2
}

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
exec python3 "$root/scripts/conformance_cli.py" "$@"
