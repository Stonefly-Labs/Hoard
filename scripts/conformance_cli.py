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
        failure = {"mode": mode, "qualification": False, "status": status, "code": code}
        if admitted:
            from conformance_sdk_checks import (
                _RuntimeObservationError, _category_failure_locations, bounded_runtime_diagnostic)

            failure["locations"] = _category_failure_locations(error)
            if isinstance(error, _RuntimeObservationError):
                try:
                    failure.update(bounded_runtime_diagnostic(error.runtime_diagnostic))
                except evidence.ConformanceError as diagnostic_error:
                    failure.update(code=str(diagnostic_error),
                                   status=evidence.failure_status(str(diagnostic_error)))
        print(json.dumps(failure))
        return 2 if failure["status"] == "Incomplete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
