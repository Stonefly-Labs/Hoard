"""Run foundational regressions without retaining raw framework diagnostics."""

import argparse
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import time
import unittest


METADATA_INVENTORY_FAILURE = ("test_metadata_evidence.MetadataEvidenceTests."
                              "test_stale_failed_unpaired_foreign_and_false_memory_durability_reject")


class SafeResult(unittest.TestResult):
    def __init__(self, *, deadline=None):
        super().__init__()
        self.observed_tests = []
        self.deadline = deadline
        root = Path(__file__).resolve().parents[1]
        self.source_roles = {
            str(path): path.relative_to(root).as_posix()
            for folder, pattern in (("scripts", "*.py"), ("tests/tooling", "test_*.py"))
            for path in (root / folder).glob(pattern)}
        self.locations = {}

    def startTest(self, test):
        super().startTest(test)
        self.observed_tests.append(test.id())

    def stopTest(self, test):
        super().stopTest(test)
        if self.deadline is not None and time.monotonic() >= self.deadline:
            self.stop()

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


def metadata_inventory(root, mode, source):
    from conformance_evidence import ConformanceError, canonical_bytes
    from conformance_sources import read_bounded
    if mode not in ("baseline", "mutation", "repair"):
        raise ConformanceError("EvidenceSchemaInvalid")
    original = read_bounded(root / "scripts/metadata_evidence.py", 1024 * 1024)
    suite_path = root / "tests/tooling/test_metadata_evidence.py"
    suite_bytes = read_bounded(suite_path, 1024 * 1024)
    needle = b'\n        elif entry.get("result") != "Passed":\n'
    if original.count(needle) != 1:
        raise ConformanceError("ProofMismatch")
    mutation = original.replace(needle, b"\n        elif False:\n")
    expected = mutation if mode == "mutation" else original
    if mode == "baseline":
        with source.open("xb") as output:
            output.write(original)
        source.chmod(0o600)
    else:
        if read_bounded(source, 1024 * 1024) != (mutation if mode == "repair" else original):
            raise ConformanceError("ProofMismatch")
        source.write_bytes(expected)
    diagnostics = DiagnosticBoundary()
    previous = sys.dont_write_bytecode
    previous_path = sys.path[:]
    sys.dont_write_bytecode = True
    try:
        with contextlib.redirect_stdout(diagnostics), contextlib.redirect_stderr(diagnostics):
            spec = importlib.util.spec_from_file_location("test_metadata_evidence", suite_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.SPEC = importlib.util.spec_from_file_location("metadata_evidence", source)
            suite = unittest.TestLoader().loadTestsFromModule(module)

            def identities(selected):
                for test in selected:
                    if isinstance(test, unittest.TestSuite):
                        yield from identities(test)
                    else:
                        yield test.id()

            selected = sorted(identities(suite))
            if (not selected or len(selected) != len(set(selected))
                    or METADATA_INVENTORY_FAILURE not in selected
                    or any(re.fullmatch(r"test_metadata_evidence\.MetadataEvidenceTests\.test_[a-z_]+", identity)
                           is None for identity in selected)):
                raise ConformanceError("WitnessMissing")
            result = SafeResult()
            suite.run(result)
    finally:
        sys.dont_write_bytecode = previous
        sys.path[:] = previous_path
    failures = [row["test"] for row in failed_tests(result)]
    if (set(failures) - set(selected) or result.testsRun != len(selected)
            or read_bounded(source, 1024 * 1024) != expected
            or read_bounded(root / "scripts/metadata_evidence.py", 1024 * 1024) != original
            or read_bounded(suite_path, 1024 * 1024) != suite_bytes):
        raise ConformanceError("InputChanged")
    return {
        "schemaVersion": 1, "qualification": False, "mode": mode,
        "baselineSha256": hashlib.sha256(original).hexdigest(),
        "executedSha256": hashlib.sha256(expected).hexdigest(),
        "suiteSha256": hashlib.sha256(suite_bytes).hexdigest(),
        "testsSha256": hashlib.sha256(canonical_bytes(selected)).hexdigest(),
        "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "failedTests": failures, "diagnosticBytes": diagnostics.bytes,
        "exitCode": (1 if result.failures or result.errors else 2 if result.skipped or diagnostics.bytes else 0),
    }


def metadata_inventory_main(arguments):
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "scripts"))
    from conformance_evidence import ConformanceError, canonical_bytes
    from conformance_sources import read_bounded
    try:
        if len(arguments) != 4:
            raise ConformanceError("EvidenceSchemaInvalid")
        mode, source, proof, snapshot = arguments
        source = Path(source)
        packet = metadata_inventory(root, mode, source)
        raw = read_bounded(source, 1024 * 1024)
        if hashlib.sha256(raw).hexdigest() != packet["executedSha256"]:
            raise ConformanceError("InputChanged")
        for path, data in ((Path(snapshot), raw), (Path(proof), canonical_bytes(packet))):
            with path.open("xb") as output:
                output.write(data)
            path.chmod(0o400)
    except (ConformanceError, OSError) as error:
        print(json.dumps({"event": "control", "code": str(error) if isinstance(error, ConformanceError)
                          else "EvidenceIncomplete", "value": 0}))
        return 2
    print(json.dumps({"event": "test", "code": "None" if packet["exitCode"] == 0 else "AssertionFailed",
                      "value": packet["tests"]}))
    return packet["exitCode"]


def run_checks(*, all_tooling=False, deadline=None):
    root = Path(__file__).resolve().parents[1]
    diagnostics = DiagnosticBoundary()
    with contextlib.redirect_stdout(diagnostics), contextlib.redirect_stderr(diagnostics):
        suite = unittest.defaultTestLoader.discover(
            str(root / "tests/tooling"), pattern="test_*.py" if all_tooling else "test_conformance_*.py")

        def identities(selected):
            for test in selected:
                if isinstance(test, unittest.TestSuite):
                    yield from identities(test)
                else:
                    yield test.id()

        expected = list(identities(suite))
        result = SafeResult(deadline=deadline)
        suite.run(result)
    code = ("AssertionFailed" if result.failures or result.errors or result.unexpectedSuccesses else
            "EvidenceIncomplete" if result.skipped or result.expectedFailures or not result.testsRun
            or result.shouldStop or result.observed_tests != expected else
            "UnknownDiagnostic" if diagnostics.bytes else "None")
    return {"mode": "diagnostic", "qualification": False, "code": code,
            "scope": "tooling" if all_tooling else "conformance",
            "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
            "skipped": len(result.skipped), "failedTests": failed_tests(result),
            "expectedFailures": len(result.expectedFailures), "unexpectedSuccesses": len(result.unexpectedSuccesses),
            "expectedTests": expected, "observedTests": result.observed_tests,
            "unexpectedDiagnosticBytes": diagnostics.bytes, "freeScratchBytes": shutil.disk_usage(root).free}


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-tooling", action="store_true")
    args = parser.parse_args(arguments)
    packet = run_checks(all_tooling=args.all_tooling)
    print(json.dumps({key: value for key, value in packet.items() if key not in ("expectedTests", "observedTests")}))
    code = packet["code"]
    return 0 if code == "None" else 2 if code in ("EvidenceIncomplete", "UnknownDiagnostic") else 1


if __name__ == "__main__":
    sys.exit(metadata_inventory_main(sys.argv[2:]) if sys.argv[1:2] == ["--metadata-inventory"] else main())
