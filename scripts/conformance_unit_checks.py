"""Run foundational regressions without retaining raw framework diagnostics."""

import contextlib
import json
from pathlib import Path
import re
import shutil
import sys
import unittest


class SafeResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        root = Path(__file__).resolve().parents[1]
        self.source_roles = {
            str(path): path.relative_to(root).as_posix()
            for folder, pattern in (("scripts", "conformance_*.py"), ("tests/tooling", "test_conformance_*.py"))
            for path in (root / folder).glob(pattern)}
        self.locations = {}

    def _exc_info_to_string(self, error, test):
        from conformance_evidence import ConformanceError
        trace, locations, count = error[2], [], 0
        while trace is not None and count < 1024:
            source = self.source_roles.get(trace.tb_frame.f_code.co_filename)
            if source is not None and type(trace.tb_lineno) is int and 0 < trace.tb_lineno <= 2**31 - 1:
                locations = [*locations[-3:], {"source": source, "line": trace.tb_lineno}]
            trace, count = trace.tb_next, count + 1
        self.locations[id(test)] = locations
        return str(error[1]) if isinstance(error[1], ConformanceError) else "AssertionFailed"


def failed_tests(result):
    failures = []
    for test, code in (*result.failures, *result.errors):
        identity = getattr(test, "test_case", test).id()
        if len(identity) > 512 or not re.fullmatch(r"[a-zA-Z0-9_.]+", identity):
            identity = "UnknownDiagnostic"
        failures.append({"test": identity, "code": code, "locations": result.locations.get(id(test), [])})
    return failures


class DiagnosticBoundary:
    def __init__(self):
        self.bytes = 0

    def write(self, text):
        self.bytes += len(text.encode("utf-8"))
        if self.bytes > 1024 * 1024:
            raise ValueError("OutputLimitExceeded")
        return len(text)

    def flush(self):
        pass


def main():
    root = Path(__file__).resolve().parents[1]
    diagnostics = DiagnosticBoundary()
    with contextlib.redirect_stdout(diagnostics), contextlib.redirect_stderr(diagnostics):
        suite = unittest.defaultTestLoader.discover(str(root / "tests/tooling"), pattern="test_conformance_*.py")
        result = SafeResult()
        suite.run(result)
    code = ("AssertionFailed" if result.failures or result.errors else
            "EvidenceIncomplete" if result.skipped or not result.testsRun else
            "UnknownDiagnostic" if diagnostics.bytes else "None")
    print(json.dumps({"mode": "diagnostic", "qualification": False, "code": code,
                      "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                      "skipped": len(result.skipped), "failedTests": failed_tests(result),
                      "freeScratchBytes": shutil.disk_usage(root).free}))
    return 0 if code == "None" else 2 if code in ("EvidenceIncomplete", "UnknownDiagnostic") else 1


if __name__ == "__main__":
    sys.exit(main())
