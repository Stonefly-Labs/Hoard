import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import uuid
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_evidence as evidence


class ConformanceAdmissionTests(unittest.TestCase):
    def test_catalog_copies_witnesses_and_rejects_nonmatching_sdk_bounds(self):
        import conformance_case_catalog as catalog
        names = ["Tests.Check"]
        case = catalog.ExpectedCase("harness", "none", "none", "QC-01", names)
        names.append("changed")
        self.assertEqual(case.witnesses, ("Tests.Check",))
        for witnesses, controls, exclusion in (
                (["Tests.Check"] * 2, (), None), (["x" * 1025], (), None),
                (["control\ncanary"], (), None), (["caf\u00e9"], (), None),
                ([f"Tests.Check{number}" for number in range(129)], (), None),
                ((), ("control", "control"), None), ((), (), None),
                ((), (), "provider-selected"), ("Tests.Check", (), None)):
            with self.subTest(witnesses=witnesses, controls=controls), self.assertRaises(evidence.ConformanceError):
                catalog.ExpectedCase("harness", "none", "none", "QC-01", witnesses, controls, exclusion)

    def test_classification_catalog_preserves_every_source_parameter_and_policy_case(self):
        import conformance_case_catalog as catalog
        source = (ROOT / "tests/integration/Hoard.Composition.Tests/ConformanceVersionTests.cs").read_text()
        section = source.split("public static IEnumerable<object[]> Classifications()")[1].split("[Theory]")[0]
        rows = tuple(tuple(json.loads("[" + row + "]"))
                     for row in re.findall(r"yield return \[(.+)\];", section))
        self.assertEqual(catalog.CLASSIFICATION_RUNTIME_ROWS, rows)
        methods = set(re.findall(r"public void (\w+)\(", source))
        cases = [case for case in catalog.expected_cases("compatibility") if case.case_id.startswith("C-")]
        self.assertEqual({case.case_id for case in cases}, {f"C-{number:02}" for number in range(1, 24)})
        for case in cases:
            self.assertTrue(case.witnesses)
            for name in case.witnesses:
                self.assertIn(name.split("(")[0].rsplit(".", 1)[1], methods)
                if ".Inherited_runtime_classification(" not in name:
                    parameters = name.split("(", 1)[1].removesuffix(")")
                    values = re.sub(r"\w+: ", "", parameters).replace("True", "true").replace("False", "false")
                    self.assertIn("[InlineData(" + values + ")]", source)
        self.assertEqual(len(catalog.classification_witnesses("C-14")), 2)
        with self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
            catalog.classification_witnesses("C-99")

    def test_composition_catalog_maps_only_real_methods_and_declared_rejection_parameters(self):
        import conformance_case_catalog as catalog
        source = (ROOT / "tests/integration/Hoard.Composition.Tests/ConformanceMatrixTests.cs").read_text()
        methods = set(re.findall(r"public async Task (\w+)\(", source))
        declarations = set(re.findall(r'yield return \["([^"]+)", "([^"]+)", "([^"]+)"\]', source))
        for case in catalog.expected_cases("composition"):
            for name in case.witnesses:
                self.assertIn(name.split("(")[0].rsplit(".", 1)[1], methods)
                if ".Declaration_rejection_and_single_input_repair(" in name:
                    values = tuple(re.findall(r': "([^"]+)"', name))
                    self.assertIn(values, declarations)
        with self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
            catalog.composition_witnesses("CP-99", "missing")

    def test_version_catalog_names_real_methods_axes_and_each_source_owned_row(self):
        import conformance_case_catalog as catalog
        fixture = (ROOT / "tests/fixtures/conformance/Host/VersionFixtures.cs").read_text()
        rows = re.findall(r'new\("([^"]+)",', fixture.split("public static Row Repair")[0])
        self.assertEqual(set(catalog.VERSION_RUNTIME_ROWS), {row[0] for row in catalog.VERSION_ROWS})
        self.assertEqual(set(catalog.VERSION_RUNTIME_ROWS.values()), set(rows))
        source = (ROOT / "tests/integration/Hoard.Composition.Tests/ConformanceVersionTests.cs").read_text()
        methods = set(re.findall(r"public void (\w+)\(", source))
        witnesses = [name for case in catalog.expected_cases("compatibility")
                     if case.case_id in ("VERSION", "VERSION-INDEPENDENT") for name in case.witnesses]
        for name in witnesses:
            self.assertIn(name.split("(")[0].rsplit(".", 1)[1], methods)
            if ".Runtime_matrix(" in name:
                self.assertRegex(name, r'axis: "(?:host|abstractions|required|optional)", row: "[a-z0-9-]+"')
                self.assertIn(name.split('row: "')[1].rstrip('")'), rows)

    def test_architecture_catalog_preserves_all_existing_rule_and_inspection_parameters(self):
        import conformance_case_catalog as catalog
        source = (ROOT / "tests/architecture/Hoard.Architecture.Tests/ArchitectureRuleTests.cs").read_text()
        rows = re.findall(r'\[InlineData\("([^"]+)", "(ARCH-\d{3})"\)\]', source)
        expected = {
            "Hoard.Architecture.Tests.ArchitectureRuleTests."
            + f'Isolated_forbidden_input_is_rejected_by_its_intended_rule(name: "{name}", rule: "{rule}")'
            for name, rule in rows}
        expected.add("Hoard.Architecture.Tests.ArchitectureRuleTests.Both_project_and_package_cycles_are_rejected")
        cases = catalog.expected_cases("compatibility")
        rejects = [case for case in cases if case.case_id == "ARCHITECTURE" and case.matrix_id.endswith(".reject")]
        permits = [case for case in cases if case.case_id == "ARCHITECTURE" and case.matrix_id.endswith(".permit")]
        self.assertEqual({name for case in rejects for name in case.witnesses}, expected)
        self.assertTrue(all(case.witnesses and case.controls for case in rejects + permits))
        self.assertEqual({name for case in permits for name in case.witnesses}, {
            "Hoard.Architecture.Tests.ArchitectureRuleTests."
            "Actual_platform_provider_packages_and_both_hosts_are_permitted"})
        special = {case.matrix_id: case for case in cases if case.case_id == "COMPATIBILITY"}
        inspection = (ROOT / "tests/architecture/Hoard.Architecture.Tests/InspectionFailureTests.cs").read_text()
        expected_inspection = set()
        for method, parameter in (
                ("Omitting_any_required_real_scan_is_an_error", "identity"),
                ("Incomplete_inputs_are_inspection_errors_not_clean_scans", "failure")):
            attributes = inspection.split("public void " + method)[0].rsplit("[Theory]", 1)[1]
            expected_inspection.update(
                "Hoard.Architecture.Tests.InspectionFailureTests."
                + f'{method}({parameter}: "{value}")'
                for value in re.findall(r'\[InlineData\("([^"]+)"\)\]', attributes))
        self.assertEqual(set(special["inspection-failures"].witnesses), expected_inspection)
        self.assertIn(
            "Hoard.Architecture.Tests.ArchitectureRuleTests."
            "Approved_hosting_path_does_not_hide_an_alternate_forbidden_core_path(reverse: True)",
            special["identity-paths"].witnesses)
        self.assertIn(
            "Hoard.Architecture.Tests.ArchitectureRuleTests."
            "Approved_hosting_path_does_not_hide_an_alternate_forbidden_core_path(reverse: False)",
            special["identity-paths"].witnesses)
        for rule, mode in (("ARCH-009", "reject"), ("ARCH-001", "unknown")):
            with self.subTest(rule=rule, mode=mode), self.assertRaisesRegex(
                    evidence.ConformanceError, "WitnessMissing"):
                catalog.architecture_witnesses(rule, mode)
        with self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
            catalog.compatibility_witnesses("unknown")

    def test_proof_obligations_require_distinct_subproofs_not_one_aggregate_label(self):
        import conformance_case_catalog as catalog
        cases = [case for profile in evidence.PROFILES for case in catalog.expected_cases(profile)
                 if case.case_id.startswith("QC-")]
        self.assertEqual({case.case_id for case in cases}, {f"QC-{number:02}" for number in range(1, 49)})
        for case in cases:
            with self.subTest(case=case.key):
                self.assertGreater(len(case.controls), 1)
                self.assertNotIn("obligation:" + case.case_id, case.controls)
        watchdog = next(case for case in cases if case.case_id == "QC-34")
        for scope in ("operation", "barrier", "child", "transfer", "recovery", "termination",
                      "cleanup", "profile", "baseline"):
            self.assertIn(f"obligation:QC-34.{scope}-budget", watchdog.controls)
        capacity = next(case for case in cases if case.case_id == "QC-37")
        self.assertIn("obligation:QC-37.insufficient-scratch-incomplete", capacity.controls)
        with mock.patch.dict(catalog.QC_CONTROLS):
            del catalog.QC_CONTROLS[34]
            with self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
                catalog.expected_cases("harness")
        with mock.patch.dict(catalog.QC_CONTROLS, {49: ("unreviewed",)}):
            with self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
                catalog.expected_cases("harness")
        with mock.patch.object(catalog, "MAX_RESULTS", 1):
            with self.assertRaisesRegex(evidence.ConformanceError, "EvidenceIncomplete"):
                catalog.expected_cases("metadata")

    def case(self):
        return {
            "caseId": "MP-01", "contractRevision": "f07-v1", "category": "metadata",
            "claimClass": "common-logical", "requirementReferences": ["FR-001"],
            "expectedWitnessIds": ["metadata.roundtrip"],
            "applicabilityRule": "mandatory",
        }

    def test_strict_json_rejects_duplicate_keys_nonfinite_and_invalid_unicode(self):
        for raw in ('{"a":1,"a":2}', '{"value":NaN}', '{"value":Infinity}',
                    '{"value":1e999}', '{"value":"\\ud800"}', '{"\\ud800":0}',
                    '{"value":true} trailing'):
            with self.subTest(raw=raw), self.assertRaises(evidence.ConformanceError):
                evidence.load_json(raw.encode())
        self.assertEqual(evidence.load_json(b'{"a":[1,true,null]}'), {"a": [1, True, None]})

    def test_case_requires_every_field_and_copies_all_collections(self):
        case = self.case()
        admitted = evidence.admit_entity("ContractCase", case)
        case["expectedWitnessIds"].append("changed")
        self.assertEqual(admitted["expectedWitnessIds"], ("metadata.roundtrip",))
        with self.assertRaises(TypeError):
            admitted["caseId"] = "MP-02"
        for key in self.case():
            changed = self.case()
            del changed[key]
            with self.subTest(missing=key), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("ContractCase", changed)

    def test_each_evidence_entity_requires_all_fields_and_rejects_extensions(self):
        inputs = self.inputs()
        package = inputs["packages"][0]
        key = {"profileId": "metadata", "bindingId": "sqlite", "matrixId": "none", "caseId": "MP-01"}
        fixtures = {
            "ContractCase": self.case(),
            "QualificationProfile": {
                "profileId": "metadata", "revision": "f07-v1", "caseExpansion": [key],
                "bindingIds": ["sqlite"], "matrixIds": ["none"],
                "budgets": inputs["budgets"], "prerequisites": ["native"],
            },
            "ExpectedKey": key, "PackageIdentity": package, "ProviderBinding": inputs["bindings"][0],
            "MatrixEntry": {
                "matrixId": "baseline", "packageIds": ["Hoard.Fixture"], "hostVersion": "0.1.0",
                "abstractionsVersion": "0.1.0", "enabledIds": ["metadata", "artifacts"],
                "expectedRule": "None", "expectedReadiness": True, "expectedOwnership": "Released",
            },
            "CompatibilityBaseline": {
                "revision": "a" * 40, "sourceSha256": "b" * 64, "lockSha256": "c" * 64,
                "recipeSha256": "d" * 64, "binarySha256": "e" * 64,
                "dependencySha256": {"consumer.dll": "f" * 64}, "apiScope": "metadata",
            },
            "Budgets": inputs["budgets"], "Environment": inputs["environment"], "RunInputs": inputs,
            "ResourceOwnership": {
                "runId": inputs["runId"], "rootId": "root", "childPid": 0,
                "childStartSha256": "a" * 64, "state": "Allocated", "cleanupDurationMs": 0,
                "diagnosticCode": "None",
            },
            "Attempt": self.result()["attempts"][0], "CaseResult": self.result(),
            "RuntimeWitness": self.report()["witnesses"][0], "QualificationReport": self.report(),
            "SupportStatement": {
                "reportSha256": "a" * 64, "profiles": ["metadata"], "bindingIds": ["sqlite"],
                "versions": ["0.1.0"], "environmentSha256": ["b" * 64], "exclusions": [],
                "unsupportedScope": ["production"],
            },
        }
        for kind, fixture in fixtures.items():
            with self.subTest(kind=kind, control=True):
                evidence.admit_entity(kind, fixture)
            for field in fixture:
                incomplete = copy.deepcopy(fixture)
                del incomplete[field]
                with self.subTest(kind=kind, missing=field), self.assertRaises(evidence.ConformanceError):
                    evidence.admit_entity(kind, incomplete)
            with self.subTest(kind=kind, unknown=True), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity(kind, {**fixture, "unrecognized": "canary"})

    def test_unknown_fields_categories_revisions_and_unbounded_ids_reject(self):
        for key, value in (
                ("caseId", "../escape"), ("caseId", "x" * 129), ("caseId", "caf\u00e9"),
                ("category", "service"), ("contractRevision", "f07-v2"),
                ("claimClass", "production"), ("expectedWitnessIds", []),
                ("expectedWitnessIds", ["same", "same"]),
                ("expectedWitnessIds", ["x" + str(n) for n in range(129)]),
                ("applicabilityRule", "provider-selected"), ("unknown", "ignored")):
            changed = self.case()
            changed[key] = value
            with self.subTest(field=key, value=value), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("ContractCase", changed)

    def test_result_requires_exact_dimensions_status_attempts_and_provenance(self):
        result = self.result()
        admitted = evidence.admit_entity("CaseResult", result)
        self.assertEqual(admitted["matrixId"], "none")
        for key, value in (
                ("status", "Skipped"), ("status", "Unknown"), ("matrixId", ""),
                ("runId", "arbitrary-label"), ("proofSha256", ["A" * 64]),
                ("applicable", 1), ("attempts", []), ("extra", True)):
            changed = copy.deepcopy(result)
            changed[key] = value
            with self.subTest(field=key), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("CaseResult", changed)
        for key, value in (
                ("startedMs", -1), ("endedMs", float("nan")), ("endedMs", True),
                ("endedMs", float("inf")), ("sequence", 0),
                ("diagnosticCode", "synthetic-secret-canary"), ("witnessIds", [])):
            changed = copy.deepcopy(result)
            changed["attempts"][0][key] = value
            with self.subTest(attempt=key), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("CaseResult", changed)

    def result(self):
        return {
            "runId": "95b3bbc8-f009-4692-bca2-c2253fa2d967",
            "profileId": "metadata", "bindingId": "sqlite", "matrixId": "none",
            "caseId": "MP-01", "status": "Passed", "applicable": True,
            "exclusionRule": "none",
            "attempts": [{
                "sequence": 1, "startedMs": 0, "endedMs": 1, "status": "Passed",
                "witnessIds": ["25fffb6f-61c1-42b9-9c70-a0c2571cd212"], "proofSha256": ["a" * 64],
                "diagnosticCode": "None",
            }],
            "proofSha256": ["a" * 64],
        }

    def inputs(self):
        source = {"src/check.cs": "a" * 64}
        environment = {
            "os": "linux", "osVersion": "test", "architecture": "x86_64",
            "sdk": "10.0.203", "runtime": "10.0.7", "nativeSqlite": "none",
            "filesystem": "ext4", "runnerImage": "none", "freeBytes": 0,
            "pragmas": {"journalMode": "none", "synchronous": 0, "foreignKeys": 0, "busyTimeout": 0},
        }
        package = {
            "packageId": "Hoard.Fixture", "version": "0.1.0", "sha256": "b" * 64,
            "nugetSha512": "c" * 128, "sourceMapping": "local",
            "runtimeAssemblies": {"lib/net10.0/Hoard.Fixture.dll": "d" * 64},
        }
        return {
            "schemaVersion": 1, "runId": self.result()["runId"],
            "invocationGroupId": "95cc783d-a60b-4378-822e-8dcb854fa3fc",
            "profileId": "metadata", "mode": "diagnostic",
            "catalogRevision": "f07-v1", "catalogSha256": "a" * 64, "sdkSha256": "b" * 64,
            "sourceRevision": "c" * 40, "sourceState": "dirty-local",
            "sourceManifest": source, "sourceManifestSha256": evidence.digest(source),
            "packages": [package], "locks": {"packages.lock.json": "d" * 64},
            "bindings": [{
                "bindingId": "sqlite", "package": copy.deepcopy(package), "category": "metadata",
                "descriptorSha256": "a" * 64, "capabilitySha256": "b" * 64,
                "adapterId": "sqlite.adapter",
            }],
            "baselines": [], "runtimeAssemblies": {"consumer/Hoard.Tests.dll": "e" * 64},
            "configurationSha256": "e" * 64, "capabilitySha256": "f" * 64,
            "environment": environment, "environmentSha256": evidence.digest(environment),
            "budgets": {
                "operationSeconds": 5, "barrierSeconds": 15, "childSeconds": 600,
                "transferSeconds": 2400, "recoverySeconds": 300, "terminationSeconds": 10,
                "cleanupSeconds": 30, "profileSeconds": 5400, "baselineSeconds": 28800,
                "maxChildren": 4, "maxTransferChildren": 1,
            },
            "invocation": ["profile", "metadata"],
        }

    def report(self):
        inputs = self.inputs()
        result = self.result()
        witness = {
            "executionId": result["attempts"][0]["witnessIds"][0],
            "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
            "testIdentity": "Tests.Roundtrip", "bindingId": "sqlite", "matrixId": "none",
            "packageSha256": "b" * 64, "assemblySha256": "e" * 64,
            "inputSha256": evidence.digest(inputs), "startedMs": 0, "endedMs": 1,
            "status": "Passed", "proofSha256": "a" * 64,
        }
        return {
            "schemaVersion": 1, "catalogRevision": "f07-v1", "inputs": inputs,
            "postInputSha256": evidence.digest(inputs), "results": [result], "witnesses": [witness],
            "resources": [], "proofs": {"runtime/proof.json": "a" * 64},
            "state": "Complete", "qualification": False, "scope": ["common-logical"],
        }

    def test_exclusions_and_interruption_do_not_invent_runtime_executions(self):
        excluded = self.result()
        excluded.update(bindingId="memory", caseId="MP-36", status="NotApplicable",
                        applicable=False, exclusionRule="non-durable-fixture", attempts=[], proofSha256=[])
        evidence.admit_entity("CaseResult", excluded)
        for key, value in (("attempts", self.result()["attempts"]), ("proofSha256", ["a" * 64])):
            malformed = copy.deepcopy(excluded)
            malformed[key] = value
            with self.subTest(key=key), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("CaseResult", malformed)
        interrupted = self.result()
        interrupted.update(status="Incomplete", proofSha256=[])
        interrupted["attempts"][0].update(status="Incomplete", witnessIds=[], proofSha256=[],
                                         diagnosticCode="DeadlineExceeded")
        evidence.admit_entity("CaseResult", interrupted)
        with self.assertRaises(evidence.ConformanceError):
            evidence.admit_entity("Attempt", {
                **self.result()["attempts"][0], "status": "NotApplicable",
            })

    def test_input_hashes_bind_distinct_baselines_packages_bindings_and_runtime_assets(self):
        inputs = self.inputs()
        admitted = evidence.admit_entity("RunInputs", inputs)
        self.assertEqual(evidence.admit_entity("RunInputs", admitted), admitted)
        mutations = (
            ("sourceManifestSha256", "1" * 64), ("environmentSha256", "2" * 64),
            ("packages", inputs["packages"] * 2), ("bindings", inputs["bindings"] * 2),
        )
        for key, value in mutations:
            malformed = copy.deepcopy(inputs)
            malformed[key] = value
            with self.subTest(key=key), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("RunInputs", malformed)
        for dimension in ("packages", "bindings"):
            malformed = copy.deepcopy(inputs)
            if dimension == "packages":
                malformed["packages"][0]["sha256"] = "3" * 64
            else:
                malformed["bindings"][0]["package"]["sha256"] = "3" * 64
            with self.subTest(dimension=dimension), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("RunInputs", malformed)
        inputs["runtimeAssemblies"]["consumer/Hoard.Tests.dll"] = "4" * 64
        self.assertEqual(admitted["runtimeAssemblies"]["consumer/Hoard.Tests.dll"], "e" * 64)

    def test_profile_cannot_duplicate_or_change_its_frozen_dimensions(self):
        profile = {
            "profileId": "metadata", "revision": "f07-v1",
            "caseExpansion": [{"profileId": "metadata", "bindingId": "sqlite",
                               "matrixId": "none", "caseId": "MP-01"}],
            "bindingIds": ["sqlite"], "matrixIds": ["none"],
            "budgets": self.inputs()["budgets"], "prerequisites": ["owned-native-execution"],
        }
        evidence.admit_entity("QualificationProfile", profile)
        for key, value in (
                ("caseExpansion", profile["caseExpansion"] * 2),
                ("bindingIds", ["memory"]), ("matrixIds", ["invented"])):
            malformed = copy.deepcopy(profile)
            malformed[key] = value
            with self.subTest(field=key), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("QualificationProfile", malformed)
        profile["caseExpansion"][0]["profileId"] = "harness"
        with self.assertRaises(evidence.ConformanceError):
            evidence.admit_entity("QualificationProfile", profile)

    def test_report_rejects_cross_run_proof_borrowing_missing_and_duplicate_executions(self):
        report = self.report()
        evidence.admit_entity("QualificationReport", report)
        for field, value in (
                ("runId", str(uuid.uuid4())), ("invocationGroupId", str(uuid.uuid4())),
                ("inputSha256", "1" * 64), ("packageSha256", "2" * 64),
                ("assemblySha256", "3" * 64), ("proofSha256", "4" * 64)):
            malformed = copy.deepcopy(report)
            malformed["witnesses"][0][field] = value
            with self.subTest(field=field), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("QualificationReport", malformed)
        for field in ("results", "witnesses"):
            malformed = copy.deepcopy(report)
            malformed[field] *= 2
            with self.subTest(duplicate=field), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("QualificationReport", malformed)
        malformed = copy.deepcopy(report)
        malformed["results"][0]["attempts"][0]["witnessIds"] = [str(uuid.uuid4())]
        with self.assertRaises(evidence.ConformanceError):
            evidence.admit_entity("QualificationReport", malformed)
        malformed = copy.deepcopy(report)
        malformed["qualification"] = True
        with self.assertRaises(evidence.ConformanceError):
            evidence.admit_entity("QualificationReport", malformed)

    def test_retry_keeps_the_failed_execution_and_all_its_proofs(self):
        report = self.report()
        result = report["results"][0]
        first = result["attempts"][0]
        first.update(status="Failed", diagnosticCode="AssertionFailed")
        report["witnesses"][0]["status"] = "Failed"
        retry_id = str(uuid.uuid4())
        result["attempts"].append({
            "sequence": 2, "startedMs": 2, "endedMs": 3, "status": "Passed",
            "witnessIds": [retry_id], "proofSha256": ["f" * 64], "diagnosticCode": "None",
        })
        result["proofSha256"].append("f" * 64)
        report["witnesses"].append({
            **report["witnesses"][0], "executionId": retry_id, "startedMs": 2, "endedMs": 3,
            "status": "Passed", "proofSha256": "f" * 64,
        })
        report["proofs"]["runtime/retry.json"] = "f" * 64
        evidence.admit_entity("QualificationReport", report)
        result["attempts"] = result["attempts"][1:]
        result["attempts"][0]["sequence"] = 1
        result["proofSha256"] = ["f" * 64]
        with self.assertRaises(evidence.ConformanceError):
            evidence.admit_entity("QualificationReport", report)

    def test_an_attempt_cannot_borrow_other_dimensions_or_outside_execution_times(self):
        for dimension, value in (("bindingId", "memory"), ("matrixId", "other")):
            report = self.report()
            report["results"][0][dimension] = value
            with self.subTest(dimension=dimension), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("QualificationReport", report)
        for started, ended in ((0, 2), (2, 3)):
            report = self.report()
            report["witnesses"][0].update(startedMs=started, endedMs=ended)
            with self.subTest(interval=(started, ended)), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("QualificationReport", report)
        result = self.result()
        result["attempts"][0]["endedMs"] = 3
        result["attempts"].append({**result["attempts"][0], "sequence": 2, "startedMs": 2})
        with self.assertRaises(evidence.ConformanceError):
            evidence.admit_entity("CaseResult", result)

    def test_nil_execution_and_oversized_monotonic_values_fail_with_closed_codes(self):
        for field, value in (
                ("sequence", True), ("startedMs", 10**400), ("endedMs", 10**400),
                ("witnessIds", ["metadata.roundtrip"])):
            attempt = self.result()["attempts"][0]
            attempt[field] = value
            with self.subTest(field=field), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("Attempt", attempt)
        witness = self.report()["witnesses"][0]
        for field in ("executionId", "runId", "invocationGroupId"):
            malformed = {**witness, field: str(uuid.UUID(int=0))}
            with self.subTest(field=field), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("RuntimeWitness", malformed)

    def test_unknown_entity_and_oversized_json_fail_without_echoing_input(self):
        for data in (b" " * (16 * 1024 * 1024 + 1), b"\xff", b'{"canary":'):
            with self.assertRaises(evidence.ConformanceError) as raised:
                evidence.load_json(data)
            self.assertNotIn("canary", str(raised.exception))
        with self.assertRaises(evidence.ConformanceError):
            evidence.admit_entity("Unknown", {})

    def test_frozen_inventory_has_all_unique_keys_and_exact_durable_exclusions(self):
        import conformance_baselines as baselines
        inventory = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        entries = inventory["entries"]
        keys = {(x["profileId"], x["bindingId"], x["matrixId"], x["caseId"]) for x in entries}
        expected = {
            (profile, binding, "none", f"{prefix}-{number:02}")
            for profile, bindings, prefix in (
                ("metadata", ("sqlite", "memory"), "MP"),
                ("artifacts", ("local", "object"), "AS"))
            for binding in bindings for number in range(1, 49)
        }
        self.assertEqual(keys, expected)
        self.assertEqual(len(entries), len(keys))
        self.assertEqual(sum(x["exclusion"] is not None for x in entries), 13)
        self.assertFalse(inventory["qualification"])
        self.assertEqual(inventory["baselineRevision"], "9389016c0285c79f6f515f59805a5a41c69b0767")
        self.assertEqual(set(inventory["historicalBaselines"].values()),
                         {revision for _, revision, _, _ in baselines.BASELINES})


class ConformanceInputTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="hoard-conformance-input-test-")).resolve()
        self.parent.chmod(0o700)
        self.addCleanup(shutil.rmtree, self.parent)
        self.repo = self.parent / "repository"
        self.repo.mkdir()
        subprocess.run(["git", "init", "--quiet", str(self.repo)], check=True)
        (self.repo / "src").mkdir()
        (self.repo / "src/check.cs").write_text("immutable source")

    def package(self, *, package_id="Hoard.Fixture", version="0.1.0", assembly=b"assembly", extra=()):
        feed = self.parent / "feed"
        feed.mkdir(mode=0o700, exist_ok=True)
        path = feed / "Hoard.Fixture.0.1.0.nupkg"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("Hoard.Fixture.nuspec",
                            f"<package><metadata><id>{package_id}</id><version>{version}</version></metadata></package>")
            if assembly is not None:
                archive.writestr("lib/net10.0/Hoard.Fixture.dll", assembly)
            for name, data in extra:
                archive.writestr(name, data)
        return path

    def test_package_identity_binds_actual_metadata_archive_and_runtime_bytes(self):
        path = self.package()
        raw = path.read_bytes()
        admitted = evidence.package_identity(path.parent, "Hoard.Fixture", "0.1.0")
        self.assertEqual(admitted["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(admitted["nugetSha512"], hashlib.sha512(raw).hexdigest())
        self.assertEqual(dict(admitted["runtimeAssemblies"]),
                         {"lib/net10.0/Hoard.Fixture.dll": hashlib.sha256(b"assembly").hexdigest()})
        with self.assertRaises(TypeError):
            admitted["version"] = "0.2.0"
        for mutation in ({"package_id": "Hoard.Other"}, {"version": "0.2.0"}, {"assembly": None}):
            with self.subTest(mutation=mutation):
                self.package(**mutation)
                with self.assertRaises(evidence.ConformanceError):
                    evidence.package_identity(path.parent, "Hoard.Fixture", "0.1.0")

    def test_package_archive_and_runtime_hashes_cannot_describe_different_reads(self):
        path = self.package()
        original = path.read_bytes()
        self.package(assembly=b"replacement")
        replacement = path.read_bytes()
        path.write_bytes(original)
        constructor = zipfile.ZipFile
        changed = []
        def replaced_after_read(source, *args, **kwargs):
            path.write_bytes(replacement)
            changed.append(True)
            return constructor(source, *args, **kwargs)
        with mock.patch.object(zipfile, "ZipFile", side_effect=replaced_after_read):
            identity = evidence.package_identity(path.parent, "Hoard.Fixture", "0.1.0")
        self.assertEqual(changed, [True])
        self.assertEqual(identity["sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(identity["runtimeAssemblies"]["lib/net10.0/Hoard.Fixture.dll"],
                         hashlib.sha256(b"assembly").hexdigest())
        self.assertNotEqual(evidence.package_identity(path.parent, "Hoard.Fixture", "0.1.0"), identity)

    def test_package_inventory_rejects_escaping_members_and_bounded_expansion(self):
        path = self.package(extra=(("../outside.dll", b"not a runtime input"),))
        with self.assertRaises(evidence.ConformanceError):
            evidence.package_identity(path.parent, "Hoard.Fixture", "0.1.0")
        self.package()
        with mock.patch.object(evidence, "MAX_PACKAGE_BYTES", 1), \
                self.assertRaisesRegex(evidence.ConformanceError, "OutputLimitExceeded"):
            evidence.package_identity(path.parent, "Hoard.Fixture", "0.1.0")
        with mock.patch.object(evidence, "MAX_PACKAGE_EXPANDED_BYTES", 1), \
                self.assertRaisesRegex(evidence.ConformanceError, "OutputLimitExceeded"):
            evidence.package_identity(path.parent, "Hoard.Fixture", "0.1.0")

    def test_selected_inputs_are_pinned_bounded_and_recomputed_from_bytes(self):
        selected = ["src/check.cs"]
        before = evidence.input_manifest(self.repo, selected)
        self.assertEqual(dict(before), {"src/check.cs": hashlib.sha256(b"immutable source").hexdigest()})
        (self.repo / "src/check.cs").write_text("changed")
        self.assertNotEqual(evidence.input_manifest(self.repo, selected), before)
        with mock.patch.object(evidence, "MAX_PROOF_BYTES", 1), \
                self.assertRaisesRegex(evidence.ConformanceError, "OutputLimitExceeded"):
            evidence.input_manifest(self.repo, selected)
        (self.repo / "src/check.cs").unlink()
        (self.repo / "src/check.cs").symlink_to(self.package())
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.input_manifest(self.repo, selected)

    def test_recomputation_compares_all_input_roles_but_not_live_free_space(self):
        before = ConformanceAdmissionTests().inputs()
        after = copy.deepcopy(before)
        after["environment"]["freeBytes"] += 1
        after["environmentSha256"] = evidence.digest(after["environment"])
        self.assertEqual(evidence.verify_input_recomputation(before, after), evidence.digest(before))
        mutations = [
            lambda value: value.update(configurationSha256="1" * 64),
            lambda value: value.update(capabilitySha256="1" * 64),
            lambda value: value.update(sdkSha256="1" * 64),
            lambda value: value.update(catalogSha256="1" * 64),
            lambda value: value["locks"].update({"packages.lock.json": "1" * 64}),
            lambda value: value["runtimeAssemblies"].update({"consumer/Hoard.Tests.dll": "1" * 64}),
            lambda value: value["bindings"][0].update(descriptorSha256="1" * 64),
            lambda value: value["bindings"][0].update(capabilitySha256="1" * 64),
            lambda value: value["environment"].update(runtime="10.0.8"),
            lambda value: value.update(sourceState="clean-local"),
        ]
        for index, mutate in enumerate(mutations):
            changed = copy.deepcopy(after)
            mutate(changed)
            changed["environmentSha256"] = evidence.digest(changed["environment"])
            with self.subTest(role=index), self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
                evidence.verify_input_recomputation(before, changed)

    def test_source_mapping_is_verified_without_serializing_private_paths(self):
        self.package()
        feed = self.parent / 'feed&"synthetic'
        (self.parent / "feed").rename(feed)
        config = self.parent / "NuGet.Config"
        config.write_bytes(evidence.synthetic_nuget_configuration(feed))
        actual = ET.fromstring(config.read_bytes()).find("./packageSources/add")
        self.assertEqual(actual.attrib["value"], str(feed))
        policy = evidence.verify_synthetic_source_mapping(self.parent, "NuGet.Config", feed.name)
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(policy))
        config.write_text(config.read_text().replace("Hoard.*", "*"))
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.verify_synthetic_source_mapping(self.parent, "NuGet.Config", feed.name)

    def test_binding_capture_binds_actual_declarations_to_selected_package_bytes(self):
        path = self.package()
        package = evidence.package_identity(path.parent, "Hoard.Fixture", "0.1.0")
        declaration = {
            "schemaVersion": 1, "bindingId": "fixture", "category": "metadata",
            "packageId": "Hoard.Fixture", "packageVersion": "0.1.0", "packageSha256": package["sha256"],
            "capabilities": ["common-logical"],
            "faults": ["IndependentSnapshot", "WriterContention", "CommitAcknowledgement", "PersistedCorruption",
                       "Capacity", "SchemaState", "LeaseBoundary", "NativeNonCooperation", "CleanupFailure"],
        }
        source = self.parent / "declaration.json"
        source.write_bytes(evidence.canonical_bytes(declaration))
        def capture():
            return evidence.capture_binding(self.parent, source.name, packages=[package], adapter_id="fixture.adapter")
        admitted = capture()
        self.assertEqual(admitted["descriptorSha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(admitted["package"], package)
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(admitted))
        declaration["capabilities"].append("durable-local-process-crash")
        declaration["faults"].append("BackupRestore")
        source.write_bytes(evidence.canonical_bytes(declaration))
        changed = capture()
        self.assertNotEqual(changed["capabilitySha256"], admitted["capabilitySha256"])
        self.assertNotEqual(changed["descriptorSha256"], admitted["descriptorSha256"])
        self.assertEqual(admitted["package"], changed["package"])
        for field, value in (
                ("packageSha256", "1" * 64), ("packageId", "Hoard.Unselected"),
                ("packageVersion", "0.2.0"), ("faults", ["Capacity"]), ("qualified", True),
                ("capabilities", {"environment": "synthetic-secret-canary"}),
                ("capabilities", ["/private/synthetic-canary"]),
                ("connectionString", "synthetic-secret-canary")):
            modified = copy.deepcopy(declaration)
            modified[field] = value
            source.write_bytes(evidence.canonical_bytes(modified))
            with self.subTest(field=field), self.assertRaises(evidence.ConformanceError):
                capture()

    def test_binding_capture_rejects_aliases_and_duplicate_keys(self):
        path = self.package()
        package = evidence.package_identity(path.parent, "Hoard.Fixture", "0.1.0")
        source = self.parent / "declaration.json"
        source.write_bytes(b'{"schemaVersion":1,"schemaVersion":1}')
        with self.assertRaises(evidence.ConformanceError):
            evidence.capture_binding(self.parent, source.name, packages=[package], adapter_id="fixture.adapter")
        source.unlink()
        source.symlink_to(path)
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.capture_binding(self.parent, source.name, packages=[package], adapter_id="fixture.adapter")

    def test_profile_capture_derives_source_packages_bindings_and_materials_in_one_manifest(self):
        from conformance_execution import OwnedRun
        sdk = "tests/contracts/Hoard.Testing.Conformance"
        (self.repo / sdk / "Catalog").mkdir(parents=True)
        (self.repo / sdk / "Catalog/catalog.json").write_bytes(b"{}")
        (self.repo / sdk / "packages.lock.json").write_bytes(b"source lock")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run([
            "git", "-c", "user.name=Conformance fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
            "commit", "--quiet", "-m", "Create synthetic profile inputs",
        ], cwd=self.repo, check=True)
        run = OwnedRun.allocate(self.parent / "run", self.repo, profile="metadata")
        self.addCleanup(lambda: (run.transition("Settling"), run.release()))
        snapshot, _ = evidence.snapshot_sources(self.repo, run)
        feed = run.root / "feed/candidate"
        feed.mkdir(mode=0o700)
        shutil.copyfile(self.package(), feed / "Hoard.Fixture.0.1.0.nupkg")
        config = run.root / "stores/candidate.NuGet.Config"
        config.write_bytes(evidence.synthetic_nuget_configuration(feed))
        (run.root / "compiled").mkdir(mode=0o700)
        runtime = run.root / "compiled/Hoard.Fixture.dll"
        runtime.write_bytes(b"actual compiled fixture")
        package = evidence.package_identity(feed, "Hoard.Fixture", "0.1.0")
        declaration = {
            "schemaVersion": 1, "bindingId": "fixture", "category": "metadata",
            "packageId": "Hoard.Fixture", "packageVersion": "0.1.0", "packageSha256": package["sha256"],
            "capabilities": ["common-logical"],
            "faults": ["IndependentSnapshot", "WriterContention", "CommitAcknowledgement", "PersistedCorruption",
                       "Capacity", "SchemaState", "LeaseBoundary", "NativeNonCooperation", "CleanupFailure"],
        }
        binding = run.root / "binding.json"
        binding.write_bytes(evidence.canonical_bytes(declaration))
        fixture = ConformanceAdmissionTests().inputs()
        group_id = str(uuid.uuid4())
        def capture():
            return evidence.capture_profile_inputs(
                run, self.repo, snapshot, profile_id="metadata", mode="diagnostic",
                invocation_group_id=group_id,
                package_versions=[{"packageId": "Hoard.Fixture", "version": "0.1.0"}],
                feed="feed/candidate", configuration="stores/candidate.NuGet.Config",
                lock_paths=[f"snapshot/{sdk}/packages.lock.json"],
                runtime_paths=["compiled/Hoard.Fixture.dll"],
                binding_sources=[{"path": "binding.json", "adapterId": "fixture.adapter"}],
                observed_environment=fixture["environment"], budgets=fixture["budgets"],
                invocation=["profile", "metadata"])
        before = capture()
        self.assertEqual(before["catalogSha256"], hashlib.sha256(b"{}").hexdigest())
        self.assertEqual(before["runtimeAssemblies"]["compiled/Hoard.Fixture.dll"],
                         hashlib.sha256(b"actual compiled fixture").hexdigest())
        self.assertEqual(before["packages"][0], package)
        self.assertEqual(before["bindings"][0]["descriptorSha256"], hashlib.sha256(binding.read_bytes()).hexdigest())
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(before))
        self.assertEqual(evidence.verify_input_recomputation(before, capture()), evidence.digest(before))
        declaration["capabilities"].append("additional-fixture-capability")
        binding.write_bytes(evidence.canonical_bytes(declaration))
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.verify_input_recomputation(before, capture())
        (self.repo / "src/check.cs").write_text("source changed after selection")
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            capture()

    def test_source_admission_rejects_symlinked_roots_and_changed_ancestors(self):
        self.assertEqual(set(evidence.source_manifest(self.repo)), {"src/check.cs"})
        linked = self.parent / "linked"
        linked.symlink_to(self.repo, target_is_directory=True)
        with self.subTest(defect="root-link"), \
                self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.source_manifest(linked)
        outside = self.parent / "outside"
        outside.mkdir()
        (outside / "check.cs").write_text("outside canary")
        original = os.stat
        swapped = []
        def changed_ancestor(path, *args, **kwargs):
            observed = original(path, *args, **kwargs)
            if Path(path).name == "check.cs" and not swapped:
                (self.repo / "src").rename(self.repo / "original")
                (self.repo / "src").symlink_to(outside, target_is_directory=True)
                swapped.append(True)
            return observed
        with self.subTest(defect="changed-ancestor"), \
                mock.patch.object(os, "stat", side_effect=changed_ancestor), \
                self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.source_manifest(self.repo)
        self.assertEqual(swapped, [True])

    def test_snapshot_verification_rejects_borrowed_roots_and_unlisted_special_files(self):
        snapshot = self.parent / "snapshot"
        snapshot.mkdir()
        (snapshot / "check.cs").write_text("immutable source")
        manifest = {"check.cs": evidence.file_sha256(snapshot / "check.cs")}
        evidence.verify_snapshot(snapshot, manifest)
        linked = self.parent / "linked"
        linked.symlink_to(snapshot, target_is_directory=True)
        with self.subTest(defect="root-link"), \
                self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.verify_snapshot(linked, manifest)
        os.mkfifo(snapshot / "unlisted.cs")
        with self.subTest(defect="special-file"), \
                self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.verify_snapshot(snapshot, manifest)

    def test_snapshot_creation_cannot_follow_a_replaced_owned_root(self):
        from conformance_execution import OwnedRun
        run = OwnedRun.allocate(self.parent / "run", self.repo, profile="harness")
        outside = self.parent / "outside"
        outside.mkdir(mode=0o700)
        (outside / "snapshot").mkdir(mode=0o700)
        mkdir = os.mkdir
        swapped = []
        def substituted_root(path, *args, **kwargs):
            result = mkdir(path, *args, **kwargs)
            if Path(path).name == "snapshot" and not swapped:
                run.root.rename(self.parent / "moved")
                run.root.symlink_to(outside, target_is_directory=True)
                swapped.append(True)
            return result
        with mock.patch.object(os, "mkdir", side_effect=substituted_root), \
                self.assertRaises(evidence.ConformanceError):
            evidence.snapshot_sources(self.repo, run)
        self.assertEqual(swapped, [True])
        self.assertFalse(any((outside / "snapshot").iterdir()))

    def test_source_identity_labels_real_dirty_bytes_and_requires_the_exact_clean_ci_revision(self):
        subprocess.run(["git", "checkout", "--quiet", "-b", "test/conformance-inputs"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "add", "src/check.cs"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Conformance fixture", "-c", "user.email=fixture@example.invalid",
             "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
             "commit", "--quiet", "-m", "Create synthetic input fixture"],
            cwd=self.repo, check=True)
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo).decode().strip()
        clean = evidence.source_identity(self.repo)
        self.assertEqual(dict(clean), {"sourceRevision": revision, "sourceState": "clean-local"})
        self.assertEqual(evidence.source_identity(self.repo, ci_revision=revision)["sourceState"], "clean-ci")
        outside = self.parent / "ambient-git"
        outside.mkdir()
        with mock.patch.dict(os.environ, {"GIT_WORK_TREE": str(outside),
                                          "GIT_INDEX_FILE": str(outside / "foreign-index"),
                                          "GIT_DIR": str(outside / "foreign-git")}):
            self.assertEqual(dict(evidence.source_identity(self.repo)), dict(clean))
            self.assertEqual(set(evidence.source_manifest(self.repo)), {"src/check.cs"})
        self.assertFalse(any(outside.iterdir()))
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.source_identity(self.repo, ci_revision="f" * 40)
        with self.assertRaises(TypeError):
            clean["sourceState"] = "dirty-local"
        for name in ("src/check.cs", "src/extra.cs"):
            with self.subTest(input=name):
                path = self.repo / name
                original = path.read_bytes() if path.exists() else None
                path.write_bytes(b"changed source")
                self.assertEqual(evidence.source_identity(self.repo)["sourceState"], "dirty-local")
                with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
                    evidence.source_identity(self.repo, ci_revision=revision)
                if original is None:
                    path.unlink()
                else:
                    path.write_bytes(original)
        self.assertEqual(evidence.source_identity(self.repo)["sourceState"], "clean-local")
        for flag in ("assume-unchanged", "skip-worktree"):
            with self.subTest(indexFlag=flag):
                subprocess.run(["git", "update-index", "--" + flag, "src/check.cs"],
                               cwd=self.repo, check=True)
                try:
                    (self.repo / "src/check.cs").write_text("hidden dirty bytes")
                    self.assertEqual(evidence.source_identity(self.repo)["sourceState"], "dirty-local")
                    with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
                        evidence.source_identity(self.repo, ci_revision=revision)
                finally:
                    (self.repo / "src/check.cs").write_text("immutable source")
                    subprocess.run(["git", "update-index", "--no-" + flag, "src/check.cs"],
                                   cwd=self.repo, check=True)

    def test_source_limits_preserve_incomplete_codes_instead_of_relabelling_input_mutation(self):
        with mock.patch.object(evidence, "MAX_PROOF_BYTES", 1), \
                self.assertRaisesRegex(evidence.ConformanceError, "OutputLimitExceeded"):
            evidence.source_manifest(self.repo)
        with mock.patch("conformance_execution.capture_control",
                        side_effect=evidence.ConformanceError("DeadlineExceeded")), \
                self.assertRaisesRegex(evidence.ConformanceError, "DeadlineExceeded"):
            evidence.source_manifest(self.repo)

    def test_proof_roots_and_ancestors_cannot_borrow_a_symlinked_tree(self):
        actual = self.parent / "actual-proofs"
        actual.mkdir()
        (actual / "proof.json").write_text("{}")
        link = self.parent / "linked-proofs"
        link.symlink_to(actual, target_is_directory=True)
        with self.assertRaises(evidence.ConformanceError):
            evidence.proof_manifest(link)
        (actual / "nested").mkdir()
        (actual / "nested/proof.json").write_text("{}")
        with self.assertRaises(evidence.ConformanceError):
            evidence.proof_manifest(link / "nested")
        self.assertEqual((actual / "proof.json").read_text(), "{}")
        self.assertEqual(set(evidence.proof_manifest(actual)), {"proof.json", "nested/proof.json"})

    def test_proof_walk_rejects_overflow_and_special_files_without_opening_them(self):
        actual = self.parent / "proofs"
        actual.mkdir()
        (actual / "first.json").write_text("{}")
        (actual / "second.json").write_text("{}")
        with mock.patch.object(evidence, "MAX_PROOF_FILES", 1), self.assertRaises(evidence.ConformanceError):
            evidence.proof_manifest(actual)
        with mock.patch.object(evidence, "MAX_PROOF_BYTES", 3), self.assertRaises(evidence.ConformanceError):
            evidence.proof_manifest(actual)
        self.assertEqual(len(evidence.proof_manifest(actual)), 2)
        os.mkfifo(actual / "blocked-reader")
        with self.assertRaises(evidence.ConformanceError):
            evidence.proof_manifest(actual)

    def test_snapshot_binds_actual_source_bytes_and_rejects_changed_and_extra_inputs(self):
        from conformance_execution import OwnedRun
        run = OwnedRun.allocate(self.parent / "run", self.repo, profile="harness")
        snapshot, manifest = evidence.snapshot_sources(self.repo, run)
        self.assertEqual(set(manifest), {"src/check.cs"})
        evidence.verify_snapshot(snapshot, manifest)
        self.assertEqual(manifest["src/check.cs"], evidence.file_sha256(self.repo / "src/check.cs"))
        (self.repo / "src/check.cs").write_text("changed source")
        self.assertNotEqual(evidence.digest(evidence.source_manifest(self.repo)), evidence.digest(manifest))
        unexpected = snapshot / "src/extra.cs"
        unexpected.write_text("extra input")
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.verify_snapshot(snapshot, manifest)
        unexpected.unlink()
        original = snapshot / "src/check.cs"
        original.chmod(0o600)
        original.write_text("changed snapshot")
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.verify_snapshot(snapshot, manifest)
        run.transition("Settling")
        run.release()

    def test_exact_parameter_witnesses_cannot_borrow_counts_labels_or_input_hashes(self):
        run_id, group_id = str(uuid.uuid4()), str(uuid.uuid4())
        witness = {
            "executionId": str(uuid.uuid4()), "runId": run_id, "invocationGroupId": group_id,
            "testIdentity": 'Tests.Behavior(provider: "sqlite", shape: "null")',
            "bindingId": "sqlite", "matrixId": "none", "packageSha256": "a" * 64,
            "assemblySha256": "b" * 64, "inputSha256": "c" * 64, "proofSha256": "d" * 64,
            "startedMs": 0, "endedMs": 1, "status": "Passed",
        }
        def ingest(value):
            return evidence.ingest_witnesses(
                json.dumps(value).encode(), run_id=run_id, invocation_group_id=group_id,
                input_sha256="c" * 64, package_sha256="a" * 64, assembly_sha256="b" * 64,
                expected_tests={witness["testIdentity"]: ("sqlite", "none")})
        self.assertEqual(len(ingest([witness])), 1)
        for key, value in (
                ("executionId", "label"), ("runId", str(uuid.uuid4())),
                ("bindingId", "memory"), ("matrixId", "different-row"),
                ("testIdentity", 'Tests.Behavior(provider: "sqlite", shape: "omitted")'),
                ("packageSha256", "e" * 64), ("assemblySha256", "e" * 64),
                ("inputSha256", "e" * 64), ("status", "Incomplete")):
            changed = dict(witness, **{key: value})
            with self.subTest(field=key), self.assertRaises(evidence.ConformanceError):
                ingest([changed])
        for changed in ([], [witness, witness]):
            with self.assertRaises(evidence.ConformanceError):
                ingest(changed)


class ConformanceRuntimeIngestionTests(unittest.TestCase):
    def setUp(self):
        self.inputs = ConformanceAdmissionTests().inputs()
        self.attempt = str(uuid.uuid4())
        self.execution = str(uuid.uuid4())
        self.identity = "Hoard.Testing.Conformance.Runtime.Check(value: 1)"
        self.owner = {
            "schemaVersion": 1, "runId": self.inputs["runId"],
            "invocationGroupId": self.inputs["invocationGroupId"],
            "rootId": "synthetic-owned-root", "rootPathSha256": "f" * 64,
        }
        self.manifest = {
            "schemaVersion": 1, "runId": self.inputs["runId"],
            "invocationGroupId": self.inputs["invocationGroupId"],
            "attemptId": self.attempt, "attemptSequence": 1,
            "inputSha256": evidence.digest(self.inputs), "runInputsPath": "run-inputs.json",
            "assemblies": [{"id": "tests", "path": "consumer/Hoard.Tests.dll", "sha256": "e" * 64}],
            "packages": [{"id": "Hoard.Fixture", "path": "feed/Hoard.Fixture.nupkg", "sha256": "b" * 64}],
            "expected": [{
                "testIdentity": self.identity, "fullyQualifiedName": "Hoard.Testing.Conformance.Runtime.Check",
                "assemblyId": "tests", "packageId": "Hoard.Fixture",
                "bindingId": "sqlite", "matrixId": "none",
                "assertionSymbol": "Hoard.Testing.Conformance.Runtime.Check",
            }],
        }
        self.proof = {
            "schemaVersion": 1, "executionId": self.execution,
            "runId": self.inputs["runId"], "invocationGroupId": self.inputs["invocationGroupId"],
            "attemptId": self.attempt, "attemptSequence": 1, "testIdentity": self.identity,
            "bindingId": "sqlite", "matrixId": "none", "inputSha256": evidence.digest(self.inputs),
            "manifestSha256": evidence.digest(self.manifest), "ownerSha256": evidence.digest(self.owner),
            "assemblySha256": "e" * 64, "packageSha256": "b" * 64,
            "clock": "system-monotonic-ms", "durationMs": 1, "failureKind": "None",
            "assertionSymbol": None, "status": "Passed",
        }
        self.witness = {
            "executionId": self.execution, "runId": self.inputs["runId"],
            "invocationGroupId": self.inputs["invocationGroupId"], "testIdentity": self.identity,
            "bindingId": "sqlite", "matrixId": "none", "packageSha256": "b" * 64,
            "assemblySha256": "e" * 64, "inputSha256": evidence.digest(self.inputs),
            "startedMs": 10, "endedMs": 11, "status": "Passed",
            "proofSha256": evidence.digest(self.proof),
        }
        self.completion = {
            "schemaVersion": 1, "runId": self.inputs["runId"],
            "invocationGroupId": self.inputs["invocationGroupId"], "attemptId": self.attempt,
            "attemptSequence": 1, "manifestSha256": evidence.digest(self.manifest),
            "inputSha256": evidence.digest(self.inputs), "diagnosticCode": "None",
            "observedCount": 1, "expectedCount": 1, "complete": True,
        }

    def ingest(self, **overrides):
        options = {
            "inputs": self.inputs, "manifest_data": evidence.canonical_bytes(self.manifest),
            "owner_data": evidence.canonical_bytes(self.owner),
            "witnesses_data": evidence.canonical_bytes(self.witness) + b"\n",
            "proofs": {f"proof-{self.execution}.json": evidence.canonical_bytes(self.proof)},
            "completion_data": evidence.canonical_bytes(self.completion),
            "expected_tests": {self.identity: ("sqlite", "none")},
            "manifest_sha256": evidence.digest(self.manifest), "owner_sha256": evidence.digest(self.owner),
            "started_ms": 9, "ended_ms": 12,
        }
        options.update(overrides)
        return evidence.ingest_runtime_attempt(**options)

    def test_safe_logger_records_require_exact_manifest_proof_and_completion_links(self):
        admitted = self.ingest()
        self.assertEqual(admitted["attemptId"], self.attempt)
        self.assertEqual(admitted["witnesses"][0]["executionId"], self.execution)
        self.assertEqual(admitted["diagnosticCode"], "None")
        with self.assertRaises(TypeError):
            admitted["completion"]["complete"] = False
        with self.assertRaises(TypeError):
            admitted["proofs"]["invented"] = "a" * 64

    def test_finite_version_ranges_preserve_identity_without_allowing_paths_or_free_text(self):
        for value in ("[1.2.0,2.0.0)", "(2.0.0,1.0.0]", "[1.2.3]",
                      "/private/canary", "private canary", "canary\n", 'canary"'):
            self.setUp()
            self.identity = "Hoard.Testing.Conformance.Runtime.Check(range: " + json.dumps(value) + ")"
            self.manifest["expected"][0]["testIdentity"] = self.identity
            self.witness["testIdentity"] = self.proof["testIdentity"] = self.identity
            self.completion["manifestSha256"] = self.proof["manifestSha256"] = evidence.digest(self.manifest)
            self.witness["proofSha256"] = evidence.digest(self.proof)
            with self.subTest(value=value):
                if value.startswith(("[", "(")):
                    self.assertEqual(self.ingest()["witnesses"][0]["testIdentity"], self.identity)
                else:
                    with self.assertRaises(evidence.ConformanceError):
                        self.ingest()

    def test_rehashed_proof_cannot_borrow_another_attempt_dimension_or_input(self):
        for key, value in (
                ("attemptId", str(uuid.uuid4())), ("attemptSequence", 2),
                ("bindingId", "memory"), ("matrixId", "foreign"),
                ("inputSha256", "1" * 64), ("assemblySha256", "2" * 64),
                ("packageSha256", "3" * 64), ("manifestSha256", "4" * 64),
                ("ownerSha256", "5" * 64), ("clock", "wall-clock"),
                ("durationMs", 2), ("failureKind", "Assertion"), ("unknown", "canary")):
            proof = {**self.proof, key: value}
            witness = {**self.witness, "proofSha256": evidence.digest(proof)}
            with self.subTest(field=key), self.assertRaises(evidence.ConformanceError):
                self.ingest(proofs={f"proof-{self.execution}.json": evidence.canonical_bytes(proof)},
                            witnesses_data=evidence.canonical_bytes(witness) + b"\n")

    def test_count_or_complete_flag_cannot_replace_a_missing_or_skipped_result(self):
        for changed in (b"", evidence.canonical_bytes(self.witness) + b"\n" * 2,
                        evidence.canonical_bytes(self.witness) + b"\n" + evidence.canonical_bytes(self.witness) + b"\n"):
            with self.subTest(size=len(changed)), self.assertRaises(evidence.ConformanceError):
                self.ingest(witnesses_data=changed)
        self.proof.update(status="Incomplete", failureKind="SkippedOrUnknown")
        self.witness.update(status="Incomplete", proofSha256=evidence.digest(self.proof))
        with self.assertRaises(evidence.ConformanceError):
            self.ingest()
        self.completion.update(diagnosticCode="EvidenceIncomplete", complete=False)
        self.assertEqual(self.ingest()["diagnosticCode"], "EvidenceIncomplete")

    def test_real_assertion_failure_is_retained_without_turning_into_a_passing_attempt(self):
        self.proof.update(status="Failed", failureKind="Assertion",
                          assertionSymbol="Hoard.Testing.Conformance.Runtime.Check")
        self.witness.update(status="Failed", proofSha256=evidence.digest(self.proof))
        with self.assertRaises(evidence.ConformanceError):
            self.ingest()
        self.completion["diagnosticCode"] = "AssertionFailed"
        result = self.ingest()
        self.assertEqual(result["diagnosticCode"], "AssertionFailed")
        self.assertEqual(result["witnesses"][0]["status"], "Failed")
        self.proof.update(failureKind="Unknown", assertionSymbol=None)
        self.witness["proofSha256"] = evidence.digest(self.proof)
        with self.assertRaises(evidence.ConformanceError):
            self.ingest()
        self.completion.update(diagnosticCode="UnknownDiagnostic", complete=False)
        self.assertEqual(self.ingest()["diagnosticCode"], "UnknownDiagnostic")

    def test_unknown_or_missing_results_retain_only_safe_attributed_prefix(self):
        self.completion.update(diagnosticCode="WitnessMissing", complete=False, observedCount=2)
        result = self.ingest()
        self.assertEqual(result["diagnosticCode"], "WitnessMissing")
        self.completion.update(diagnosticCode="EvidenceIncomplete", complete=False, observedCount=0)
        result = self.ingest(witnesses_data=b"", proofs={})
        self.assertEqual(result["witnesses"], ())
        self.assertEqual(result["diagnosticCode"], "EvidenceIncomplete")

    def test_manifest_is_independent_of_runtime_and_bound_to_admitted_artifact_bytes(self):
        for dimension, value in (
                ("assemblies", [{"id": "tests", "path": "foreign.dll", "sha256": "e" * 64}]),
                ("packages", [{"id": "Hoard.Foreign", "path": "feed/foreign.nupkg", "sha256": "b" * 64}]),
                ("expected", []), ("unknown", True)):
            manifest = {**self.manifest, dimension: value}
            with self.subTest(field=dimension), self.assertRaises(evidence.ConformanceError):
                self.ingest(manifest_data=evidence.canonical_bytes(manifest),
                            manifest_sha256=evidence.digest(manifest))
        with self.assertRaises(evidence.ConformanceError):
            self.ingest(manifest_sha256="0" * 64)
        with self.assertRaises(evidence.ConformanceError):
            self.ingest(expected_tests={self.identity: ("memory", "none")})
        with self.assertRaises(evidence.ConformanceError):
            self.ingest(ended_ms=10)

    def test_proof_inventory_and_diagnostic_output_are_bounded_and_no_raw_fields_are_accepted(self):
        proofs = {f"proof-{self.execution}.json": evidence.canonical_bytes(self.proof), "raw.trx": b"canary"}
        with self.assertRaises(evidence.ConformanceError):
            self.ingest(proofs=proofs)
        with self.assertRaises(evidence.ConformanceError):
            self.ingest(witnesses_data=b"x" * (8 * 1024 * 1024 + 1))
        with self.assertRaises(evidence.ConformanceError):
            self.ingest(completion_data=b'{"schemaVersion":1,"schemaVersion":1}')


class ConformanceBaselineTests(unittest.TestCase):
    def test_explicit_local_archive_preparation_preserves_source_and_graph_then_verifies_actual_bytes(self):
        import conformance_lock_preparation as preparation
        source = self.root / "stores/registration"
        project = source / "retained/Consumer.csproj"
        lock = project.parent / "packages.lock.json"
        original = {"version": 1, "dependencies": {"net10.0": {
            "Hoard.Example": {"type": "Direct", "resolved": "0.1.0", "contentHash": "original",
                             "dependencies": {"External.Dependency": "1.0.0"}},
            "External.Dependency": {"type": "Transitive", "resolved": "1.0.0", "contentHash": "external"},
        }}}
        lock.write_bytes(evidence.canonical_bytes(original))
        before = lock.read_bytes()
        feed = self.root / "feed/registration"
        prepared, record = preparation.prepare_project_lock(project, source, feed, "registration")
        self.assertEqual(lock.read_bytes(), before)
        changed = json.loads(prepared.read_bytes())
        self.assertNotEqual(changed["dependencies"]["net10.0"]["Hoard.Example"]["contentHash"], "original")
        changed["dependencies"]["net10.0"]["Hoard.Example"]["contentHash"] = "original"
        self.assertEqual(changed, original)
        self.assertFalse(record["qualification"])
        preparation.verify_project_lock(record, source, feed)
        prepared.chmod(0o600)
        changed["dependencies"]["net10.0"]["External.Dependency"]["resolved"] = "2.0.0"
        prepared.write_bytes(evidence.canonical_bytes(changed) + b"\n")
        record["preparedSha256"] = evidence.file_sha256(prepared)
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            preparation.verify_project_lock(record, source, feed)

    def test_archive_preparation_never_resolves_missing_local_or_rebinds_external_packages(self):
        import conformance_lock_preparation as preparation
        source = self.root / "stores/registration"
        project = source / "retained/Consumer.csproj"
        lock = project.parent / "packages.lock.json"
        external = {"version": 2, "dependencies": {"net10.0": {
            "External.Dependency": {"resolved": "1.0.0", "contentHash": "untouched"}}}}
        lock.write_bytes(evidence.canonical_bytes(external))
        self.assertEqual(preparation.prepare_project_lock(
            project, source, self.root / "feed/registration", "registration"), (None, None))
        external["dependencies"]["net10.0"]["Hoard.Missing"] = {
            "resolved": "0.1.0", "contentHash": "missing"}
        lock.write_bytes(evidence.canonical_bytes(external))
        with self.assertRaisesRegex(evidence.ConformanceError, "PrerequisiteMissing"):
            preparation.prepare_project_lock(project, source, self.root / "feed/registration", "registration")
        self.assertEqual(json.loads(lock.read_bytes()), external)

    def test_sealed_alternate_locks_are_recipe_owned_and_cannot_be_downgraded_or_detached(self):
        import conformance_lock_preparation as preparation
        source = self.root / "stores/registration"
        project = source / "retained/Consumer.csproj"
        lock = project.parent / "packages.lock.json"
        lock.write_bytes(evidence.canonical_bytes({"version": 1, "dependencies": {"net10.0": {
            "Hoard.Example": {"resolved": "0.1.0", "contentHash": "original"}}}}))
        prepared, record = preparation.prepare_project_lock(
            project, source, self.root / "feed/registration", "registration")
        record_path = project.parent / "F07LockPreparation/0000.json"
        record_path.parent.mkdir()
        record_path.write_bytes(evidence.canonical_bytes(record))
        entry = self.manifest["entries"][0]
        entry["recipes"] = self.baselines._hash_tree(project.parent, exclude_outputs=True)
        entry["recipeSha256"] = evidence.digest(entry["recipes"])
        entry["locks"][record["preparedLock"]] = evidence.file_sha256(prepared)
        entry["lockSha256"] = evidence.digest(entry["locks"])
        self.manifest["schemaVersion"] = 2

        def verify():
            self.seal.write_bytes(evidence.canonical_bytes(self.manifest))
            return self.baselines.verify_prepared_baselines(self.root, evidence.file_sha256(self.seal))

        self.assertEqual(len(verify()["entries"]), 6)
        self.manifest["schemaVersion"] = 1
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            verify()
        self.manifest["schemaVersion"] = 2
        del entry["locks"][record["preparedLock"]]
        entry["lockSha256"] = evidence.digest(entry["locks"])
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            verify()

    def test_build_runtime_pin_overrides_ambient_roll_forward_only_for_owned_build_command(self):
        run = mock.Mock(command_sequence=1)
        run.command.return_value = mock.Mock(exit_code=0, events=())
        args = ["dotnet", "build", "fixture.csproj"]
        with mock.patch.dict(os.environ, {"DOTNET_ROLL_FORWARD": "LatestPatch"}):
            self.baselines._command(run, args, cwd=self.root, cache_id="diagnostic")
            self.assertEqual(os.environ["DOTNET_ROLL_FORWARD"], "LatestPatch")
        run.command.assert_called_once_with(
            args, cwd=self.root, kind="build", cache_id="diagnostic",
            env={"DOTNET_ROLL_FORWARD": "Disable"})

    def test_local_archive_diagnostics_project_only_fixed_identities_and_actual_hashes(self):
        import zipfile
        with tempfile.TemporaryDirectory() as directory:
            feed = Path(directory).resolve()
            package = feed / "Hoard.Abstractions.0.1.0.nupkg"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("lib/net10.0/Hoard.Abstractions.dll", b"actual assembly")
                archive.writestr("private-synthetic-canary.txt", b"unprojected contents")
            projected = self.baselines.local_archive_diagnostics(feed)
            self.assertEqual(projected, {"Hoard.Abstractions": {
                "archiveSha256": evidence.file_sha256(package),
                "assemblySha256": hashlib.sha256(b"actual assembly").hexdigest()}})
            package.write_bytes(b"broken archive")
            with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
                self.baselines.local_archive_diagnostics(feed)
            package.unlink()
            package.symlink_to(self.seal)
            with self.assertRaisesRegex(evidence.ConformanceError, "OwnershipInvalid"):
                self.baselines.local_archive_diagnostics(feed)

    def setUp(self):
        import conformance_baselines as baselines
        self.baselines = baselines
        self.root = Path(tempfile.mkdtemp(prefix="hoard-sealed-baseline-test-")).resolve()
        self.root.chmod(0o700)
        self.addCleanup(shutil.rmtree, self.root)
        entries = []
        for name, revision, _, _ in (*baselines.BASELINES, ("f06", baselines.BASELINE, None, None)):
            source = self.root / "stores" / name
            source.mkdir(parents=True)
            (source / "source.cs").write_text("frozen source")
            (source / "packages.lock.json").write_text("{}")
            recipe = source / ("tests/fixtures" if name == "f06" else "retained") / "Consumer.csproj"
            if name == "f06":
                recipe.parent.mkdir(parents=True)
                recipe.write_text("<Project />")
            sources = baselines._hash_tree(source, exclude_outputs=True)
            if name != "f06":
                recipe.parent.mkdir(parents=True)
                recipe.write_text("<Project />")
            recipes = {"Consumer.csproj": evidence.file_sha256(recipe)}
            binary = recipe.parent / "bin/Release/Consumer.dll"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"immutable compiled consumer")
            package = self.root / "feed" / name / "Hoard.Example.0.1.0.nupkg"
            package.parent.mkdir(parents=True)
            package.write_bytes(b"immutable package bytes")
            locks = {path: value for path, value in sources.items() if path.endswith("packages.lock.json")}
            entries.append({
                "id": name, "revision": revision, "sources": sources, "sourceSha256": evidence.digest(sources),
                "recipes": recipes, "recipeSha256": evidence.digest(recipes),
                "locks": locks, "lockSha256": evidence.digest(locks),
                "binaries": {binary.relative_to(source).as_posix(): evidence.file_sha256(binary)},
                "packages": {package.name: {"sha256": evidence.file_sha256(package),
                            "sha512": hashlib.sha512(package.read_bytes()).hexdigest()}},
            })
        self.manifest = {"schemaVersion": 1, "qualification": False, "mode": "preparation",
                         "baselineRevision": baselines.BASELINE, "entries": entries}
        self.seal = self.root / "proofs/baselines.json"
        self.seal.parent.mkdir()
        self.seal.write_bytes(evidence.canonical_bytes(self.manifest))
        self.expected_sha256 = evidence.file_sha256(self.seal)

    def test_sealed_sources_binaries_locks_recipes_and_packages_cannot_be_substituted(self):
        self.assertEqual(len(self.baselines.verify_prepared_baselines(self.root, self.expected_sha256)["entries"]), 6)
        paths = [
            self.root / "stores/registration/source.cs",
            self.root / "stores/registration/packages.lock.json",
            self.root / "stores/registration/retained/Consumer.csproj",
            self.root / "stores/registration/retained/bin/Release/Consumer.dll",
            self.root / "feed/registration/Hoard.Example.0.1.0.nupkg",
        ]
        for path in paths:
            original = path.read_bytes()
            path.write_bytes(b"same version but substituted bytes")
            with self.subTest(kind=path.suffix), self.assertRaises(evidence.ConformanceError):
                self.baselines.verify_prepared_baselines(self.root, self.expected_sha256)
            path.write_bytes(original)
        extra = self.root / "feed/registration/Hoard.Foreign.0.1.0.nupkg"
        extra.write_bytes(b"unsealed package")
        with self.assertRaises(evidence.ConformanceError):
            self.baselines.verify_prepared_baselines(self.root, self.expected_sha256)
        extra.unlink()
        self.baselines.verify_prepared_baselines(self.root, self.expected_sha256)

    def test_rehashed_labels_cannot_invent_a_historical_revision_or_qualification(self):
        self.manifest["entries"][0]["revision"] = "0" * 40
        self.seal.write_bytes(evidence.canonical_bytes(self.manifest))
        with self.assertRaises(evidence.ConformanceError):
            self.baselines.verify_prepared_baselines(self.root, evidence.file_sha256(self.seal))
        self.manifest["entries"][0]["revision"] = self.baselines.BASELINES[0][1]
        self.manifest["qualification"] = True
        self.seal.write_bytes(evidence.canonical_bytes(self.manifest))
        with self.assertRaises(evidence.ConformanceError):
            self.baselines.verify_prepared_baselines(self.root, evidence.file_sha256(self.seal))


if __name__ == "__main__":
    unittest.main()
