"""Freeze source-owned F-06 identities before extracting shared assertions.

This is a baseline preparation tool, not runtime qualification evidence.
"""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


REVISION = "9389016c0285c79f6f515f59805a5a41c69b0767"
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from artifact_case_catalog import required_runtime_tests  # noqa: E402


def baseline_file(path):
    return subprocess.run(
        ["git", "show", f"{REVISION}:{path}"], cwd=ROOT, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5).stdout


def freeze():
    paths = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", REVISION,
         "tests/contracts/Hoard.Metadata.Tests", "tests/contracts/Hoard.Artifacts.Tests",
         "scripts"], cwd=ROOT, check=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=5).stdout.decode().splitlines()
    sources = {path: baseline_file(path) for path in paths
               if path.endswith((".cs", ".py", ".sh", ".csproj", ".json"))}
    metadata = {}
    for path, content in sources.items():
        if not path.startswith("tests/contracts/Hoard.Metadata.Tests/") or not path.endswith(".cs"):
            continue
        source = content.decode()
        class_match = re.search(r"\bclass\s+(\w+)", source)
        if class_match is None:
            continue
        pattern = r"((?:\s*\[[^\n]+\]\s*)+)public (?:async )?(?:Task|void) (MP(\d{2})_\w+)\(([^)]*)\)"
        for match in re.finditer(pattern, source):
            attributes, method, number, parameters = match.groups()
            prefix = f"Hoard.Metadata.Tests.{class_match[1]}.{method}"
            arguments = re.findall(r"\[InlineData\(([^)]*)\)\]", attributes)
            names = [item.strip().split()[-1] for item in parameters.split(",") if item.strip()]
            witnesses = [prefix]
            if arguments:
                witnesses = [
                    prefix + "(" + ", ".join(f"{name}: {value.strip()}"
                                             for name, value in zip(names, argument.split(","), strict=True)) + ")"
                    for argument in arguments]
            elif names:
                raise ValueError("Baseline metadata parameters require an explicit expansion.")
            metadata.setdefault(f"MP-{number}", []).extend(witnesses)
    entries = []
    durable = {"MP-36", *(f"MP-{number:02}" for number in range(38, 46))}
    recovery = {
        "MP-36": ["verified-recovery-walkthrough", "parent-kill:R0", "parent-kill:R1"],
        "MP-38": ["parent-kill:M0"], "MP-39": ["parent-kill:M1"],
        "MP-40": ["parent-kill:M2"],
        "MP-41": ["parent-kill:U0", "parent-kill:U1", "parent-kill:U2"],
        "MP-42": ["parent-kill:U3", "parent-kill:U4"],
        "MP-43": ["second-process-owner-and-crash-released-lock"],
        "MP-44": ["verified-recovery-walkthrough", "parent-kill:R0", "parent-kill:R1"],
        "MP-45": ["verified-recovery-walkthrough", "parent-kill:R0", "parent-kill:R1"],
    }
    boundary_source = baseline_file("tests/architecture/Hoard.Architecture.Tests/MetadataBoundaryTests.cs")
    boundary_tests = sorted(
        "Hoard.Architecture.Tests.MetadataBoundaryTests." + name
        for name in re.findall(r"public (?:async )?(?:Task|void) (\w+)\(", boundary_source.decode()))
    for binding in ("sqlite", "memory"):
        for number in range(1, 49):
            case = f"MP-{number:02}"
            witnesses = list(metadata.get(case, ()))
            controls = []
            excluded = binding == "memory" and case in durable
            if binding == "sqlite":
                controls.extend(recovery.get(case, ()))
                if case == "MP-37":
                    controls.append("sqlite3-step-stall-and-incomplete-cleanup")
                if case == "MP-43":
                    witnesses.extend(metadata["MP-33"])
            if case == "MP-46":
                controls.append("unchanged-package-consumer")
            if case == "MP-47":
                witnesses.extend(boundary_tests)
                controls.append("frozen-pre-F05-binary")
            if case == "MP-48":
                controls.extend(("MetadataEvidenceTests:positive-complete-and-negative-inventories",
                                 "test_stale_failed_unpaired_foreign_and_false_memory_durability_reject"))
            if not excluded and not witnesses and not controls:
                raise ValueError("Missing baseline metadata witness.")
            entries.append({
                "profileId": "metadata", "bindingId": binding, "matrixId": "none",
                "caseId": case, "claimClass": "durable-local-process-crash" if case in durable else "common-logical",
                "exclusion": "non-durable fixture" if excluded else None,
                "runtimeTests": sorted(set(witnesses)), "orchestratorControls": sorted(set(controls)),
            })
    for binding in ("local", "object"):
        for number in range(1, 49):
            case = f"AS-{number:02}"
            entries.append({
                "profileId": "artifacts", "bindingId": binding, "matrixId": "none",
                "caseId": case,
                "claimClass": ("durable-local-process-crash" if 41 <= number <= 44
                               else "object-simulation" if binding == "object" else "common-logical"),
                "exclusion": "simulation: no durable restart" if binding == "object" and 41 <= number <= 44 else None,
                "runtimeTests": sorted(required_runtime_tests(binding, case)), "orchestratorControls": [],
            })
    artifact_catalog = sources["scripts/artifact_case_catalog.py"]
    if artifact_catalog != (ROOT / "scripts/artifact_case_catalog.py").read_bytes():
        raise ValueError("Artifact catalog changed before baseline freeze.")
    return {
        "schemaVersion": 1, "catalogRevision": "f07-v1", "baselineRevision": REVISION,
        "qualification": False, "identityOrigin": "baseline-source-not-observed-runtime",
        "historicalBaselines": {
            "configuration": "b80c69fc386541be4f56f6ef2edeca40f43a0e1c",
            "discovery": "7fd73267a5154583363c94e9e85b9bac7d4a16b3",
            "metadata": "10ce78851b97b02bd83a8ef7da7ffdc2381d6519",
            "artifacts": "830972f24795ffaaaa18cb35138db7da59022313",
        },
        "sourceFiles": {path: hashlib.sha256(content).hexdigest() for path, content in sorted(sources.items())},
        "metadataBoundarySourceSha256": hashlib.sha256(boundary_source).hexdigest(),
        "entries": entries,
    }


if __name__ == "__main__":
    destination = Path(__file__).with_name("inventory.json")
    value = json.dumps(freeze(), indent=2, ensure_ascii=True) + "\n"
    if "--check" in sys.argv:
        if destination.read_text() != value:
            raise SystemExit("Baseline inventory differs from immutable F-06 sources.")
    elif len(sys.argv) == 1:
        if destination.exists():
            raise SystemExit("Refusing to overwrite a frozen inventory; use --check.")
        destination.write_text(value)
    else:
        raise SystemExit("Usage: freeze_inventory.py [--check]")
