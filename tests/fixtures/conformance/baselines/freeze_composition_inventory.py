"""Freeze inherited F-06 composition assertions without persisting argument displays."""

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

REVISION = "9389016c0285c79f6f515f59805a5a41c69b0767"
ROOT = Path(__file__).resolve().parents[4]
PREFIX = "tests/integration/Hoard.Composition.Tests/"


def baseline_file(path):
    return subprocess.run(
        ["git", "show", f"{REVISION}:{path}"], cwd=ROOT, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5).stdout


def methods_in_source(raw):
    source = raw.decode("utf-8", errors="strict")
    namespace = re.search(r"^namespace ([A-Za-z0-9_.]+);", source, re.MULTILINE)
    owner = re.search(r"^public (?:sealed )?class ([A-Za-z0-9_]+)", source, re.MULTILINE)
    if owner is None:
        if re.search(r"^\s*\[(?:Fact|Theory)\]", source, re.MULTILINE):
            raise ValueError("Unrecognized inherited test owner.")
        return {}
    pattern = (r"((?:^[ \t]*\[[^\r\n]*\][ \t]*\r?\n)+)"
               r"[ \t]*public (?:async )?(?:Task|void) ([A-Za-z0-9_]+)\(([^)]*)\)")
    methods = {}
    for attributes, name, parameters in re.findall(pattern, source, re.MULTILINE):
        fact = len(re.findall(r"^\s*\[Fact\]", attributes, re.MULTILINE))
        theory = len(re.findall(r"^\s*\[Theory\]", attributes, re.MULTILINE))
        if fact + theory != 1:
            raise ValueError("Inherited test requires one recognized test attribute.")
        count = len(re.findall(r"^\s*\[InlineData\(", attributes, re.MULTILINE))
        if (fact and (count or parameters.strip())) or (theory and (not count or not parameters.strip())):
            raise ValueError("Inherited parameters require explicit source-owned expansion.")
        method = f"{namespace[1] if namespace else 'Hoard.Composition.Tests'}.{owner[1]}.{name}"
        if method in methods:
            raise ValueError("Duplicate inherited method.")
        methods[method] = count if theory else 1
    annotations = len(re.findall(r"^\s*\[(?:Fact|Theory)\]", source, re.MULTILINE))
    if len(methods) != annotations:
        raise ValueError("Missing inherited method expansion.")
    return methods


def literal_mapping(path, name):
    for node in ast.parse(baseline_file(path)).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name
                                               for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError("Missing inherited case mapping.")


def freeze():
    paths = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", REVISION, PREFIX], cwd=ROOT, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5).stdout.decode().splitlines()
    files = {path: baseline_file(path) for path in paths if path.endswith(".cs")}
    files.update({path: baseline_file(path) for path in (
        "tests/architecture/Hoard.Architecture.Tests/LifecycleBoundaryTests.cs",
        "tests/architecture/Hoard.Architecture.Tests/ConfigurationBoundaryTests.cs",
        "tests/architecture/Hoard.Architecture.Tests/DiscoveryBoundaryTests.cs")})
    entries = []
    for path, raw in sorted(files.items()):
        group = ("discovery" if Path(path).stem.startswith("Discovery")
                 else "configuration" if Path(path).stem.startswith(("Configuration", "Configured"))
                 else "lifecycle")
        for method, count in sorted(methods_in_source(raw).items()):
            entries.append({"fullyQualifiedName": method, "parameterCount": count,
                            "group": group, "sourcePath": path,
                            "sourceSha256": hashlib.sha256(raw).hexdigest()})
    methods = {entry["fullyQualifiedName"] for entry in entries}
    cases = {}
    for script, key, prefix in (
            ("scripts/configuration_evidence.py", "REQUIRED_TESTS", "CFG-"),
            ("scripts/discovery_evidence.py", "CASE_TESTS", "D")):
        mapping = literal_mapping(script, key)
        expected = {f"{prefix}{number:02}" for number in range(1, 37 if prefix == "CFG-" else 41)}
        if set(mapping) != expected:
            raise ValueError("Incomplete inherited case mapping.")
        for case, required in mapping.items():
            resolved = []
            for name in required:
                matches = sorted(method for method in methods if method.endswith("." + name))
                if not matches:
                    raise ValueError("Missing source-owned inherited case method.")
                resolved.extend(matches)
            cases[case] = sorted(set(resolved))
    controls = ("scripts/lifecycle_evidence.py", "scripts/configuration_evidence.py",
                "scripts/discovery_evidence.py", "scripts/validate-lifecycle.sh",
                "scripts/validate-configuration.sh", "scripts/validate-discovery.sh",
                "specs/002-module-lifecycle/contracts/acceptance.md")
    return {
        "schemaVersion": 1, "baselineRevision": REVISION, "qualification": False,
        "identityOrigin": "baseline-source-methods-and-exact-parameter-counts",
        "sourceFiles": {path: hashlib.sha256(raw).hexdigest() for path, raw in sorted(files.items())},
        "controllerSources": {path: hashlib.sha256(baseline_file(path)).hexdigest() for path in controls},
        "lifecycleCases": [f"LC-{number:02}" for number in range(1, 41)],
        "caseMethods": dict(sorted(cases.items())), "entries": entries,
        "groupParameters": {
            group: sum(entry["parameterCount"] for entry in entries if entry["group"] == group)
            for group in ("configuration", "discovery", "lifecycle")},
    }


if __name__ == "__main__":
    destination = Path(__file__).with_name("composition-inventory.json")
    value = json.dumps(freeze(), indent=2, ensure_ascii=True) + "\n"
    if sys.argv[1:] == ["--check"]:
        if destination.read_text() != value:
            raise SystemExit("Composition inventory differs from immutable F-06 sources.")
    elif not sys.argv[1:]:
        with destination.open("x") as output:
            output.write(value)
    else:
        raise SystemExit("Usage: freeze_composition_inventory.py [--check]")
