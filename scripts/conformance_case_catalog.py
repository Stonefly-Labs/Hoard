"""F-07 expectations expanded independently of any binding or result."""

from dataclasses import dataclass
import json
from pathlib import Path

from conformance_evidence import CATALOG_REVISION, ConformanceError, MAX_RESULTS, PROFILES, canonical_bytes, stable_id


INVENTORY = Path(__file__).resolve().parents[1] / "tests/fixtures/conformance/baselines/inventory.json"


@dataclass(frozen=True)
class ExpectedCase:
    profile_id: str
    binding_id: str
    matrix_id: str
    case_id: str
    witnesses: tuple[str, ...]
    controls: tuple[str, ...] = ()
    exclusion: str | None = None

    @property
    def key(self):
        return self.profile_id, self.binding_id, self.matrix_id, self.case_id


COMPOSITIONS = (
    ("CP-01", ("baseline",)),
    ("CP-02", ("replacement",)),
    ("CP-03", ("multiple",)),
    ("CP-04", ("duplicate",)),
    ("CP-05", ("unknown",)),
    ("CP-06", ("missing-required",)),
    ("CP-07", ("cycle-forward", "cycle-reversed")),
    ("CP-08", ("missing-capability",)),
    ("CP-09", ("metadata-zero", "metadata-two")),
    ("CP-10", ("artifacts-zero", "artifacts-two")),
    ("CP-11", ("route-conflict",)),
    ("CP-12", ("optional-absent", "optional-disabled")),
    ("CP-13", ("optional-compatible", "optional-incompatible")),
    ("CP-14", ("initializer-failed",)),
    ("CP-15", ("cancel-initialization", "cancel-readiness")),
    ("CP-16", ("late-initialization",)),
    ("CP-17", ("stop-fault", "late-stop")),
    ("CP-18", ("recovery-failed",)),
    ("CP-19", ("authority-mismatch", "missing-guarantee")),
    ("CP-20", ("settled-restart", "active-config")),
)

# Each row is exercised through the existing Hosting version validator.
VERSION_ROWS = (
    ("inclusive-lower", "[0.1.0,0.2.0)", "0.1.0", False, True),
    ("exclusive-upper", "[0.1.0,0.2.0)", "0.2.0", False, False),
    ("exclusive-lower", "(0.1.0,0.2.0]", "0.1.0", False, False),
    ("inclusive-upper", "(0.1.0,0.2.0]", "0.2.0", False, True),
    ("build", "[0.1.0]", "0.1.0+build.7", False, True),
    ("prerelease-off", "[0.1.0,0.2.0)", "0.1.1-rc.1", False, False),
    ("prerelease-on", "[0.1.0,0.2.0)", "0.1.1-rc.1", True, True),
    ("below-stable", "[0.1.1,0.2.0)", "0.1.1-rc.1", True, False),
    ("prerelease-range-off", "[0.1.1-rc.1,0.1.1]", "0.1.1-rc.2", False, False),
    ("prerelease-range-on", "[0.1.1-rc.1,0.1.1]", "0.1.1-rc.2", True, True),
    ("upper-prerelease-off", "[0.1.0,0.2.0)", "0.2.0-rc.1", False, False),
    ("upper-prerelease-on", "[0.1.0,0.2.0)", "0.2.0-rc.1", True, True),
    ("case", "[0.1.1-RC.1]", "0.1.1-rc.1", True, True),
    ("empty", "", "0.1.1", False, False),
    ("floating", "1.*", "0.1.1", False, False),
    ("unbounded", "[0.1.0,)", "0.1.1", False, False),
    ("reversed", "[0.2.0,0.1.0]", "0.1.1", False, False),
    ("empty-open", "(0.1.0,0.1.0)", "0.1.1", False, False),
    ("unnormalized", "[0.1]", "0.1.1", False, False),
    ("four-part", "[0.1.0,0.2.0)", "0.1.0.0", False, False),
    ("malformed", "[0.1.0,0.2.0)", "malformed-canary", False, False),
)

VERSION_RUNTIME_ROWS = {
    "inclusive-lower": "inclusive-lower", "exclusive-upper": "exclusive-upper",
    "exclusive-lower": "exclusive-lower", "inclusive-upper": "inclusive-upper",
    "build": "exact-build", "prerelease-off": "rc-blocked", "prerelease-on": "rc-enabled",
    "below-stable": "below-stable-lower", "prerelease-range-off": "range-not-opt-in",
    "prerelease-range-on": "rc-range-enabled", "upper-prerelease-off": "upper-rc-blocked",
    "upper-prerelease-on": "upper-rc-enabled", "case": "case-precedence",
    "empty": "empty", "floating": "floating", "unbounded": "unbounded", "reversed": "reversed",
    "empty-open": "empty-open", "unnormalized": "short-range",
    "four-part": "four-part-candidate", "malformed": "unsafe-candidate",
}


def independent_version_witnesses(name):
    prefix = "Hoard.Composition.Tests.ConformanceVersionTests."
    flags = prefix + "Platform_prerelease_flags_are_independent"
    inherited = prefix + "Inherited_platform_flags_do_not_derive_from_module_version"
    optional = prefix + "Incompatible_optional_target_is_unavailable_not_an_active_edge_or_capability"
    return {
        "host-only-flag": (f"{flags}(host: True, abstractions: False)",
                           f'{inherited}(id: "C-11", host: True, abstractions: False)'),
        "abstractions-only-flag": (f"{flags}(host: False, abstractions: True)",),
        "module-no-platform-flag": (
            f"{flags}(host: False, abstractions: False)", f"{flags}(host: True, abstractions: True)",
            f'{inherited}(id: "C-18", host: False, abstractions: False)'),
        "optional-absent": (f'{optional}(selection: "absent")',),
        "optional-disabled": (f'{optional}(selection: "registered-disabled")',),
    }[name]


def category_cases():
    inventory = json.loads(INVENTORY.read_bytes())
    if inventory.get("catalogRevision") != CATALOG_REVISION:
        raise ConformanceError()
    cases = tuple(
        ExpectedCase(entry["profileId"], entry["bindingId"], entry["matrixId"], entry["caseId"],
                     tuple(entry["runtimeTests"]), tuple(entry["orchestratorControls"]), entry["exclusion"])
        for entry in inventory["entries"])
    expected = {
        (profile, binding, "none", f"{prefix}-{number:02}")
        for profile, bindings, prefix in (("metadata", ("sqlite", "memory"), "MP"),
                                          ("artifacts", ("local", "object"), "AS"))
        for binding in bindings for number in range(1, 49)}
    if len(cases) != len(expected) or {case.key for case in cases} != expected:
        raise ConformanceError("EvidenceIncomplete")
    return cases


def expected_cases(profile):
    cases = []
    if profile in ("metadata", "artifacts"):
        cases.extend(case for case in category_cases() if case.profile_id == profile)
    elif profile == "composition":
        for case_id, variants in COMPOSITIONS:
            for variant in variants:
                modes = ("reject", "repair") if 4 <= int(case_id[3:]) <= 11 or (
                    case_id == "CP-13" and variant == "optional-incompatible") else ("observe",)
                for mode in modes:
                    matrix = f"{variant}.{mode}"
                    cases.append(ExpectedCase(profile, "none", matrix, case_id, (
                        f'Hoard.Composition.Tests.ConformanceCompositionTests.Matrix(caseId: "{case_id}", variant: "{variant}", mode: "{mode}")',)))
    elif profile == "compatibility":
        for axis in ("host", "abstractions", "dependency-required", "dependency-optional"):
            runtime_axis = {"host": "host", "abstractions": "abstractions",
                            "dependency-required": "required", "dependency-optional": "optional"}[axis]
            for name, _, _, _, _ in VERSION_ROWS:
                matrix = f"{axis}.{name}"
                cases.append(ExpectedCase(profile, "none", matrix, "VERSION", (
                    f'Hoard.Composition.Tests.ConformanceVersionTests.Runtime_matrix(axis: "{runtime_axis}", row: "{VERSION_RUNTIME_ROWS[name]}")',)))
        for name in ("host-only-flag", "abstractions-only-flag", "module-no-platform-flag",
                     "optional-absent", "optional-disabled"):
            cases.append(ExpectedCase(profile, "none", name, "VERSION-INDEPENDENT",
                                      independent_version_witnesses(name)))
        for number in range(1, 24):
            cases.append(ExpectedCase(profile, "none", "none", f"C-{number:02}", (),
                                      (f"classification:C-{number:02}",)))
        for number in range(1, 9):
            for mode in ("reject", "permit"):
                matrix = f"ARCH-{number:03}.{mode}"
                cases.append(ExpectedCase(profile, "none", matrix, "ARCHITECTURE", (),
                                          (f"architecture:{matrix}",)))
        for proof in ("source", "binary", "source-break", "binary-break", "identity-paths",
                      "inspection-failures", "predecessor-binaries"):
            cases.append(ExpectedCase(profile, "none", proof, "COMPATIBILITY", (),
                                      (f"compatibility:{proof}",)))
    elif profile != "harness":
        raise ConformanceError("UnsupportedProfile")
    obligations = {
        "metadata": (2, 4, 5, 6, 7, 8),
        "artifacts": (3, 4, 5, 9, 10, 11, 12),
        "composition": tuple(range(13, 22)),
        "compatibility": tuple(range(22, 29)),
        "harness": (1, *range(29, 49)),
    }
    for number in obligations[profile]:
        cases.append(ExpectedCase(profile, "none", "none", f"QC-{number:02}", (),
                                  (f"obligation:QC-{number:02}",)))
    if len(cases) > MAX_RESULTS or len({case.key for case in cases}) != len(cases):
        raise ConformanceError("EvidenceIncomplete")
    for case in cases:
        for dimension in case.key:
            stable_id(dimension)
        if not case.witnesses and not case.controls and case.exclusion is None:
            raise ConformanceError("WitnessMissing")
        if len(case.witnesses) + len(case.controls) > 128:
            raise ConformanceError("EvidenceIncomplete")
    return tuple(cases)


def sdk_document():
    return {
        "schemaVersion": 1, "catalogRevision": CATALOG_REVISION,
        "entries": [
            {"profileId": case.profile_id, "bindingId": case.binding_id, "matrixId": case.matrix_id,
             "caseId": case.case_id, "witnesses": list(case.witnesses), "controls": list(case.controls),
             "exclusion": case.exclusion}
            for profile in PROFILES for case in expected_cases(profile)],
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Prepare/check the fixed SDK catalog, not runtime evidence.")
    parser.add_argument("--write-sdk", action="store_true")
    parser.add_argument("--check-sdk", action="store_true")
    options = parser.parse_args()
    target = Path(__file__).resolve().parents[1] / "tests/contracts/Hoard.Testing.Conformance/Catalog/catalog.json"
    content = canonical_bytes(sdk_document()) + b"\n"
    if options.write_sdk and not options.check_sdk:
        with target.open("xb") as output:
            output.write(content)
    elif options.check_sdk and not options.write_sdk:
        if target.read_bytes() != content:
            raise SystemExit("SDK catalog differs from independent expansion.")
    else:
        parser.error("Choose exactly one of --write-sdk/--check-sdk.")
