"""Safe public entry point; keep the evidence library's module identity stable."""

import json
from pathlib import Path
import sys
import zipfile

import conformance_evidence as evidence


def main(arguments=None):
    mode = "diagnostic"
    admitted = False
    try:
        invocation = evidence.admit_invocation(
            Path(__file__).resolve().parents[1],
            sys.argv[1:] if arguments is None else arguments)
        mode = invocation.mode
        admitted = True
        return evidence.dispatch_invocation(invocation)
    except (evidence.ConformanceError, OSError, ValueError, zipfile.BadZipFile) as error:
        code = str(error) if isinstance(error, evidence.ConformanceError) else "PrerequisiteMissing"
        status = evidence.failure_status(code) if admitted else "Incomplete"
        print(json.dumps({"mode": mode, "qualification": False, "status": status, "code": code}))
        return 2 if status == "Incomplete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
