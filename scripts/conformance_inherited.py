"""Exact source-owned inherited composition inventories and opaque discovery admission."""

from collections import Counter
import re

from conformance_evidence import ConformanceError, digest, load_json

INVENTORY_PATH = "tests/fixtures/conformance/baselines/composition-inventory.json"
BASELINE = "9389016c0285c79f6f515f59805a5a41c69b0767"
INVENTORY_SHA256 = "9b45196787d57b0437c14e73345b1a0ba4b1544a41d95f7fca3ea32b7635de50"
GROUPS = frozenset(("lifecycle", "configuration", "discovery"))
ASSEMBLIES = frozenset(("Hoard.Composition.Tests", "Hoard.Architecture.Tests"))


def inventory(data, sources):
    value = load_json(data)
    if digest(value) != INVENTORY_SHA256:
        raise ConformanceError("ProofMismatch")
    if (not isinstance(value, dict) or set(value) != {
            "schemaVersion", "baselineRevision", "qualification", "identityOrigin", "sourceFiles",
            "controllerSources", "lifecycleCases", "caseMethods", "entries", "groupParameters"}
            or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1
            or value["baselineRevision"] != BASELINE or value["qualification"] is not False
            or value["identityOrigin"] != "baseline-source-methods-and-exact-parameter-counts"
            or value["lifecycleCases"] != [f"LC-{number:02}" for number in range(1, 41)]
            or not isinstance(value["sourceFiles"], dict) or not value["sourceFiles"]
            or not isinstance(value["controllerSources"], dict) or len(value["controllerSources"]) != 7
            or not isinstance(value["caseMethods"], dict)
            or set(value["caseMethods"]) != {*(f"CFG-{number:02}" for number in range(1, 37)),
                                            *(f"D{number:02}" for number in range(1, 41))}
            or not isinstance(value["entries"], list) or not 1 <= len(value["entries"]) <= 10000
            or not isinstance(value["groupParameters"], dict) or value["groupParameters"].keys() != GROUPS):
        raise ConformanceError("EvidenceSchemaInvalid")
    for path, hashed in value["sourceFiles"].items():
        if (not isinstance(path, str) or not isinstance(hashed, str)
                or re.fullmatch(r"[0-9a-f]{64}", hashed) is None or sources.get(path) != hashed):
            raise ConformanceError("InputChanged")
    for path, hashed in value["controllerSources"].items():
        if (not isinstance(path, str) or not isinstance(hashed, str)
                or re.fullmatch(r"[0-9a-f]{64}", hashed) is None):
            raise ConformanceError("EvidenceSchemaInvalid")
    methods = {}
    totals = Counter()
    for entry in value["entries"]:
        if (not isinstance(entry, dict) or set(entry) != {
                "fullyQualifiedName", "parameterCount", "group", "sourcePath", "sourceSha256"}
                or not isinstance(entry["fullyQualifiedName"], str)
                or re.fullmatch(r"Hoard\.(?:Composition|Architecture)\.Tests\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+",
                                entry["fullyQualifiedName"]) is None
                or entry["fullyQualifiedName"] in methods
                or not isinstance(entry["group"], str) or entry["group"] not in GROUPS
                or type(entry["parameterCount"]) is not int or not 1 <= entry["parameterCount"] <= 10000
                or not isinstance(entry["sourcePath"], str)
                or value["sourceFiles"].get(entry["sourcePath"]) != entry["sourceSha256"]):
            raise ConformanceError("WitnessMissing")
        methods[entry["fullyQualifiedName"]] = entry
        totals[entry["group"]] += entry["parameterCount"]
    if dict(totals) != value["groupParameters"]:
        raise ConformanceError("WitnessMissing")
    for required in value["caseMethods"].values():
        if (not isinstance(required, list) or not required
                or any(not isinstance(method, str) or method not in methods for method in required)
                or len(set(required)) != len(required)):
            raise ConformanceError("WitnessMissing")
    return methods


def admit_discovery(data, methods, *, assembly):
    if assembly not in ASSEMBLIES:
        raise ConformanceError("WitnessMissing")
    expected = {name: entry for name, entry in methods.items() if name.startswith(assembly + ".")}
    rows = load_json(data)
    if not expected or not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
        raise ConformanceError("WitnessMissing")
    seen = set()
    counts = Counter()
    admitted = []
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"testIdentity", "fullyQualifiedName"}
                or not isinstance(row["fullyQualifiedName"], str) or row["fullyQualifiedName"] not in expected
                or not isinstance(row["testIdentity"], str)
                or re.fullmatch(re.escape(row["fullyQualifiedName"])
                                + r'\(testCaseSha256: "[0-9a-f]{64}"\)', row["testIdentity"]) is None
                or row["testIdentity"] in seen):
            raise ConformanceError("WitnessMissing")
        seen.add(row["testIdentity"])
        counts[row["fullyQualifiedName"]] += 1
        entry = expected[row["fullyQualifiedName"]]
        admitted.append({
            **row, "assemblyId": "test-assembly", "packageId": "Hoard.Testing.Conformance",
            "bindingId": "none", "matrixId": "inherited." + entry["group"],
            "caseId": "inherited-" + entry["group"], "assertionSymbol": None,
        })
    if dict(counts) != {name: entry["parameterCount"] for name, entry in expected.items()}:
        raise ConformanceError("WitnessMissing")
    return sorted(admitted, key=lambda row: row["testIdentity"])
