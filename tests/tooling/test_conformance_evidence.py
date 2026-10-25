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
    def test_category_execution_partitions_preserve_complete_method_families_and_both_binding_inventories(self):
        import conformance_case_catalog as catalog
        for profile, bindings in (("metadata", ("sqlite", "memory")), ("artifacts", ("local", "object"))):
            with self.subTest(profile=profile):
                expected = {(binding, identity) for binding in bindings
                            for identity in catalog.category_runtime_cases(profile, binding)}
                scopes = catalog.category_execution_partitions(profile)
                actual = [row for rows in scopes.values() for row in rows]
                self.assertEqual(set(actual), expected)
                self.assertEqual(len(actual), len(expected))
                for rows in scopes.values():
                    identities = {identity for _, identity in rows}
                    self.assertEqual(len(identities), len(rows))
                    for method in {identity.split("(")[0] for identity in identities}:
                        self.assertEqual({identity for identity in identities if identity.split("(")[0] == method},
                                         {identity for _, identity in expected if identity.split("(")[0] == method})
                if profile == "artifacts":
                    self.assertTrue(any({binding for binding, _ in rows} == set(bindings)
                                        for rows in scopes.values()))
                with self.assertRaises(TypeError):
                    scopes["foreign"] = ()
        with self.assertRaisesRegex(evidence.ConformanceError, "UnsupportedProfile"):
            catalog.category_execution_partitions("composition")

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

    def test_category_binding_capture_projects_only_its_frozen_slot_without_rewriting_declarations(self):
        import conformance_sdk_checks as checks
        feed = self.parent / "feed"
        feed.mkdir(mode=0o700)
        for package_id in (
                "Hoard.Fixtures.Metadata.Memory", "Hoard.Fixtures.Metadata.Sqlite",
                "Hoard.Fixtures.Artifacts.Local", "Hoard.Fixtures.Artifacts.ObjectSemantics"):
            with zipfile.ZipFile(feed / (package_id + ".0.1.0.nupkg"), "w") as archive:
                archive.writestr(package_id + ".nuspec", (
                    f"<package><metadata><id>{package_id}</id><version>0.1.0</version></metadata></package>"))
                archive.writestr("lib/net10.0/" + package_id + ".dll", b"fixture assembly")
        declarations = (*checks.metadata_binding_declarations(feed), *checks.artifact_binding_declarations(feed))
        packages = [evidence.package_identity(feed, declaration["packageId"], "0.1.0")
                    for declaration in declarations]
        source = self.parent / "declaration.json"
        for declaration in declarations:
            source.write_bytes(evidence.canonical_bytes(declaration))
            original = source.read_bytes()
            slot = declaration["bindingId"].rsplit(".", 1)[1]
            options = {"packages": packages, "adapter_id": "fixture.adapter"}
            captured = evidence.capture_binding(self.parent, source.name, **options)
            projected = evidence.capture_binding(
                self.parent, source.name, catalog_binding_id=slot, **options)
            self.assertEqual(projected["bindingId"], slot)
            self.assertEqual({key: value for key, value in projected.items() if key != "bindingId"},
                             {key: value for key, value in captured.items() if key != "bindingId"})
            self.assertEqual(projected["descriptorSha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(source.read_bytes(), original)
            for invalid in ("unknown", *(other["bindingId"].rsplit(".", 1)[1]
                                       for other in declarations if other is not declaration)):
                with self.subTest(slot=slot, foreign=invalid), self.assertRaisesRegex(
                        evidence.ConformanceError, "BindingInvalid"):
                    evidence.capture_binding(self.parent, source.name, catalog_binding_id=invalid, **options)
            for field, value in (("bindingId", "fixture.foreign"), ("category", "metadata"
                                 if declaration["category"] == "artifacts" else "artifacts")):
                source.write_bytes(evidence.canonical_bytes({**declaration, field: value}))
                with self.subTest(slot=slot, field=field), self.assertRaisesRegex(
                        evidence.ConformanceError, "BindingInvalid"):
                    evidence.capture_binding(self.parent, source.name, catalog_binding_id=slot, **options)
            foreign = next(other for other in declarations
                           if other is not declaration and other["category"] == declaration["category"])
            source.write_bytes(evidence.canonical_bytes({
                **declaration, "packageId": foreign["packageId"], "packageSha256": foreign["packageSha256"]}))
            with self.subTest(slot=slot, field="package"), self.assertRaisesRegex(
                    evidence.ConformanceError, "BindingInvalid"):
                evidence.capture_binding(self.parent, source.name, catalog_binding_id=slot, **options)

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
        package_versions = [{"packageId": "Hoard.Fixture", "version": "0.1.0"}]
        binding_sources = [{"path": "binding.json", "adapterId": "fixture.adapter"}]
        def capture(**options):
            return evidence.capture_profile_inputs(
                run, self.repo, snapshot, profile_id="metadata", mode="diagnostic",
                invocation_group_id=group_id,
                package_versions=package_versions,
                feed="feed/candidate", configuration="stores/candidate.NuGet.Config",
                lock_paths=[f"snapshot/{sdk}/packages.lock.json"],
                runtime_paths=["compiled/Hoard.Fixture.dll"],
                binding_sources=binding_sources,
                observed_environment=fixture["environment"], budgets=fixture["budgets"],
                invocation=["profile", "metadata"], **options)
        before = capture()
        self.assertEqual(before["catalogSha256"], hashlib.sha256(b"{}").hexdigest())
        self.assertEqual(before["runtimeAssemblies"]["compiled/Hoard.Fixture.dll"],
                         hashlib.sha256(b"actual compiled fixture").hexdigest())
        self.assertEqual(before["packages"][0], package)
        self.assertEqual(before["bindings"][0]["descriptorSha256"], hashlib.sha256(binding.read_bytes()).hexdigest())
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(before))
        self.assertEqual(evidence.verify_input_recomputation(before, capture()), evidence.digest(before))
        identity = ("Hoard.Architecture.Tests.MetadataBoundaryTests."
                    "Prepared_metadata_packages_and_negative_contracts_preserve_boundaries_and_binary_surface")
        selected = {identity: {"/private/inspection/project.csproj": "a" * 64}}
        with_inspection = capture(inspection_inputs=selected)
        self.assertNotEqual(before["configurationSha256"], with_inspection["configurationSha256"])
        self.assertEqual(before["runtimeAssemblies"], with_inspection["runtimeAssemblies"])
        self.assertEqual(before["sourceManifest"], with_inspection["sourceManifest"])
        self.assertNotIn(b"/private/inspection", evidence.canonical_bytes(with_inspection))
        self.assertEqual(evidence.verify_input_recomputation(
            with_inspection, capture(inspection_inputs=selected)), evidence.digest(with_inspection))
        for changed in (
                {identity: {"/private/inspection/project.csproj": "b" * 64}},
                {identity: {"/private/inspection/other.csproj": "a" * 64}}):
            with self.subTest(changed=changed), self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
                evidence.verify_input_recomputation(with_inspection, capture(inspection_inputs=changed))
        for invalid in ({}, {"foreign": selected[identity]}, {identity: {}},
                        {identity: {"../foreign": "a" * 64}}):
            with self.subTest(invalid=invalid), self.assertRaises(evidence.ConformanceError):
                capture(inspection_inputs=invalid)
        package_id = "Hoard.Fixtures.Metadata.Memory"
        with zipfile.ZipFile(feed / (package_id + ".0.1.0.nupkg"), "w") as archive:
            archive.writestr(package_id + ".nuspec", (
                f"<package><metadata><id>{package_id}</id><version>0.1.0</version></metadata></package>"))
            archive.writestr("lib/net10.0/" + package_id + ".dll", b"fixture metadata assembly")
        package_versions.append({"packageId": package_id, "version": "0.1.0"})
        package = evidence.package_identity(feed, package_id, "0.1.0")
        declaration.update(bindingId="fixture.metadata.memory", packageId=package_id, packageSha256=package["sha256"])
        binding.write_bytes(evidence.canonical_bytes(declaration))
        binding_sources[0]["catalogBindingId"] = "memory"
        before = capture()
        self.assertEqual(before["bindings"][0]["bindingId"], "memory")
        self.assertEqual(before["bindings"][0]["descriptorSha256"], hashlib.sha256(binding.read_bytes()).hexdigest())
        self.assertEqual(evidence.verify_input_recomputation(before, capture()), evidence.digest(before))
        binding_sources.append({"path": "binding.json", "adapterId": "same.factory"})
        with self.assertRaisesRegex(evidence.ConformanceError, "BindingInvalid"):
            capture()
        binding_sources.pop()
        alternate = run.root / "alternate-binding.json"
        alternate.write_text(json.dumps(declaration, indent=2))
        binding_sources.append({"path": alternate.name, "adapterId": "same.factory"})
        with self.assertRaisesRegex(evidence.ConformanceError, "BindingInvalid"):
            capture()
        binding_sources.pop()
        del binding_sources[0]["catalogBindingId"]
        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
            evidence.verify_input_recomputation(before, capture())
        binding_sources[0]["catalogBindingId"] = "memory"
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
        self.inputs["mode"] = "diagnostic"
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
            "attemptId": self.attempt, "attemptSequence": 1, "purpose": "execution",
            "inputSha256": evidence.digest(self.inputs), "runInputsPath": "run-inputs.json",
            "assemblies": [{"id": "tests", "path": "consumer/Hoard.Tests.dll", "sha256": "e" * 64}],
            "packages": [{"id": "Hoard.Fixture", "path": "feed/Hoard.Fixture.nupkg", "sha256": "b" * 64}],
            "expected": [{
                "testIdentity": self.identity, "fullyQualifiedName": "Hoard.Testing.Conformance.Runtime.Check",
                "assemblyId": "tests", "packageId": "Hoard.Fixture",
                "bindingId": "sqlite", "matrixId": "none",
                "assertionSymbol": "Hoard.Testing.Conformance.Runtime.Check",
                "caseId": "runtime",
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
            "caseId": "runtime", "sessionOrigins": [],
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
            "attemptSequence": 1, "purpose": "execution", "manifestSha256": evidence.digest(self.manifest),
            "inputSha256": evidence.digest(self.inputs), "diagnosticCode": "None",
            "observedCount": 1, "expectedCount": 1, "complete": True,
        }

    def transport(self, **overrides):
        options = {
            "inputs": self.inputs, "manifest_data": evidence.canonical_bytes(self.manifest),
            "owner_data": evidence.canonical_bytes(self.owner),
            "witnesses_data": evidence.canonical_bytes(self.witness) + b"\n",
            "proofs": {f"proof-{self.execution}.json": evidence.canonical_bytes(self.proof)},
            "completion_data": evidence.canonical_bytes({
                **self.completion, "recordsSha256": hashlib.sha256(
                    evidence.canonical_bytes(self.witness) + b"\n").hexdigest()}),
            "expected_tests": {self.identity: ("sqlite", "none")},
            "manifest_sha256": evidence.digest(self.manifest), "owner_sha256": evidence.digest(self.owner),
            "started_ms": 9, "ended_ms": 12,
        }
        options.update(overrides)
        return options

    def ingest(self, **overrides):
        return evidence.ingest_runtime_attempt(**self.transport(**overrides))

    def original_transport(self, *, contract=False, case_id="runtime"):
        self.identity = ("Hoard.Artifacts.Tests.ArtifactValueTests."
                         "Identity_bounds_preserve_empty_and_reject_overflow_negative_or_null" if contract else
                         "Hoard.Metadata.Tests.MetadataRoundTripTests."
                         "MP01_Every_entity_round_trips_and_invalid_relationships_leave_no_changes")
        entry = self.manifest["expected"][0]
        entry.update(testIdentity=self.identity, fullyQualifiedName=self.identity, caseId=case_id)
        self.inputs["mode"] = "qualification"
        self.inputs["runtimeAssemblies"]["provider/Hoard.Fixture.dll"] = "d" * 64
        binding = "local" if contract else "sqlite"
        self.inputs["bindings"][0].update(bindingId=binding, category="artifacts" if contract else "metadata")
        entry["bindingId"] = binding
        self.manifest["inputSha256"] = evidence.digest(self.inputs)
        roles = ("contract",) if contract else ("owner", "store", "schema", "authority", "controls")
        observation = {
            "schemaVersion": 1, "runId": self.inputs["runId"], "caseId": case_id,
            "testIdentity": self.identity, "bindingId": binding, "observationId": str(uuid.uuid4()),
            "parentObservationId": None, "kind": "loaded-contract" if contract else "original-instance",
            "operation": "contract" if contract else "create",
            "runtimeVersion": self.inputs["environment"]["runtime"], "processArchitecture": "x64",
            "components": {role: {"instanceId": str(uuid.uuid4()), "assemblySha256": ("e" if role == "owner" else "d") * 64,
                                  "moduleVersionId": str(uuid.uuid4()), "typeSha256": "d" * 64} for role in roles},
        }
        self.proof.update(schemaVersion=2, testIdentity=self.identity, bindingId=binding, caseId=case_id,
                          inputSha256=evidence.digest(self.inputs),
                          manifestSha256=evidence.digest(self.manifest), originalObservations=[observation])
        self.witness.update(testIdentity=self.identity, bindingId=binding, inputSha256=evidence.digest(self.inputs),
                            proofSha256=evidence.digest(self.proof))
        self.completion.update(inputSha256=evidence.digest(self.inputs), manifestSha256=evidence.digest(self.manifest))
        assignments = {role: ("consumer/Hoard.Tests.dll", None) if role == "owner"
                       else ("provider/Hoard.Fixture.dll", "Hoard.Fixture") for role in roles}
        return observation, {binding: {self.identity: assignments}}

    def test_original_observation_assignments_are_witness_specific_and_frozen_before_execution(self):
        self.inputs.update(profileId="metadata", invocation=["profile", "metadata"])
        self.inputs["budgets"]["profileSeconds"] = 5400
        original, assignments = self.original_transport(case_id="MP-01")
        history = evidence.RuntimeCaseHistory(
            self.inputs, binding_id="sqlite", matrix_id="none", case_id="MP-01",
            original_inputs=assignments)
        roles = assignments["sqlite"][self.identity]
        original_roles = dict(roles)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin(self.attempt)
        roles["store"] = ("consumer/Hoard.Tests.dll", "Foreign.Package")
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            self.assertEqual(self.finish_history(history)["status"], "Passed")
        self.assertEqual(history.original_observations[self.execution][0], original)
        for selected in (
                {"sqlite": original_roles},
                {"sqlite": {self.identity + "Foreign": original_roles}},
                {"memory": {self.identity: original_roles}}):
            with self.subTest(selected=tuple(selected)), self.assertRaises(evidence.ConformanceError):
                self.ingest(original_inputs=selected)

    def test_original_observation_qualification_uses_independent_witness_kind_and_role_assignments(self):
        for contract in (False, True):
            with self.subTest(contract=contract):
                self.setUp()
                observation, assignments = self.original_transport(contract=contract)
                result = self.ingest(original_inputs=assignments,
                                     expected_tests={self.identity: (self.witness["bindingId"], "none")})
                self.assertEqual(result["originalObservations"][self.execution][0], observation)
                self.assertFalse(result["sessionOrigins"][self.execution])

    def test_original_observation_rejects_foreign_kind_context_roles_or_package(self):
        for mutation in ("kind", "identity", "binding", "run", "roles", "package", "assignment-role", "missing", "typed-only",
                         "replay", "extra-root", "parent"):
            with self.subTest(mutation=mutation):
                self.setUp()
                observation, assignments = self.original_transport()
                origin_inputs = None
                if mutation == "kind":
                    observation["kind"] = "loaded-contract"
                elif mutation == "identity":
                    observation["testIdentity"] += "Foreign"
                elif mutation == "binding":
                    observation["bindingId"] = "memory"
                elif mutation == "run":
                    observation["runId"] = str(uuid.uuid4())
                elif mutation == "roles":
                    del observation["components"]["owner"]
                elif mutation == "package":
                    assignments["sqlite"][self.identity]["store"] = ("consumer/Hoard.Tests.dll", "Foreign.Package")
                elif mutation == "assignment-role":
                    assignments["sqlite"][self.identity]["unused"] = assignments["sqlite"][self.identity]["store"]
                elif mutation == "missing":
                    self.proof["originalObservations"] = []
                elif mutation == "replay":
                    self.proof["originalObservations"].append(copy.deepcopy(observation))
                elif mutation == "extra-root":
                    extra = copy.deepcopy(observation)
                    extra["observationId"] = str(uuid.uuid4())
                    self.proof["originalObservations"].append(extra)
                elif mutation == "parent":
                    observation.update(parentObservationId=str(uuid.uuid4()), operation="reopen")
                else:
                    origin, selected = self.runtime_origin("runtime")
                    origin_inputs = {"sqlite": selected}
                    self.proof["sessionOrigins"] = [origin]
                    self.proof["originalObservations"] = []
                self.witness["proofSha256"] = evidence.digest(self.proof)
                with self.assertRaises(evidence.ConformanceError):
                    self.ingest(original_inputs=assignments, origin_inputs=origin_inputs)

    def test_original_observation_history_retains_evidence_and_rejects_replay_in_a_fresh_execution(self):
        self.inputs.update(profileId="metadata", invocation=["profile", "metadata"])
        self.inputs["budgets"]["profileSeconds"] = 5400
        original, assignments = self.original_transport(case_id="MP-01")
        history = evidence.RuntimeCaseHistory(
            self.inputs, binding_id="sqlite", matrix_id="none", case_id="MP-01",
            max_attempts=2, original_inputs=assignments)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin(self.attempt)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            self.assertEqual(self.finish_history(history)["status"], "Passed")
        retained = dict(history.proofs)
        self.assertEqual(history.original_observations[self.execution][0], original)
        self.attempt, self.execution = str(uuid.uuid4()), str(uuid.uuid4())
        self.manifest.update(attemptId=self.attempt, attemptSequence=2)
        self.proof.update(executionId=self.execution, attemptId=self.attempt, attemptSequence=2,
                          manifestSha256=evidence.digest(self.manifest))
        self.witness.update(executionId=self.execution, proofSha256=evidence.digest(self.proof), startedMs=20, endedMs=21)
        self.completion.update(attemptId=self.attempt, attemptSequence=2, manifestSha256=evidence.digest(self.manifest))
        with mock.patch.object(evidence.time, "monotonic", return_value=0.019):
            history.begin(self.attempt)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.022), self.assertRaisesRegex(
                evidence.ConformanceError, "ProofMismatch"):
            self.finish_history(history)
        self.assertEqual(dict(history.proofs), retained)
        self.assertEqual(len(history.witnesses), 1)

    def test_original_observation_forests_require_exact_current_execution_lineage_and_distinct_owners(self):
        prefix = "Hoard.Metadata.Tests."
        shapes = (
            (prefix + "MetadataHostIntegrationTests."
             "MP46_Configured_selection_uses_existing_lifecycle_and_has_no_routes_or_fallback",
             (None, None)),
            (prefix + "MetadataSchemaTests.MP32_Old_schema_requires_explicit_authorized_upgrade_and_preserves_records",
             (None, 0, 1)),
            (prefix + "MetadataSchemaTests.MP33_Future_schema_and_recognized_corruption_are_never_created_over",
             (None, None, 0, 1)),
            (prefix + "MetadataLeaseTests.MP29_Expiry_is_rechecked_at_the_final_decision_for_renew_release_and_guards",
             (None, None, None)),
            (prefix + "MetadataPagingTests.MP08_Continuation_is_bound_to_scope_size_and_epoch_and_is_not_a_snapshot",
             (None, None)),
        )
        for identity, parents in shapes:
            for mutation in ("valid", "missing", "extra", "parent", "wrong-parent", "owner", "store"):
                with self.subTest(identity=identity, mutation=mutation):
                    self.setUp()
                    original, assignments = self.original_transport(case_id="MP-32")
                    roles = assignments["sqlite"].pop(self.identity)
                    self.identity = identity
                    assignments["sqlite"][identity] = roles
                    self.manifest["expected"][0].update(testIdentity=identity, fullyQualifiedName=identity)
                    observations = []
                    for parent in parents:
                        observed = copy.deepcopy(original)
                        observed.update(testIdentity=identity, observationId=str(uuid.uuid4()),
                                        parentObservationId=None if parent is None else observations[parent]["observationId"],
                                        operation="create" if parent is None else "reopen")
                        for component in observed["components"].values():
                            component["instanceId"] = str(uuid.uuid4())
                        observations.append(observed)
                    if mutation == "missing":
                        observations.pop()
                    elif mutation == "extra":
                        extra = copy.deepcopy(observations[0])
                        extra["observationId"] = str(uuid.uuid4())
                        observations.append(extra)
                    elif mutation == "parent":
                        observations[-1].update(parentObservationId=str(uuid.uuid4()), operation="reopen")
                    elif mutation == "wrong-parent":
                        wrong = 1 if parents[-1] == 0 else 0
                        observations[-1].update(parentObservationId=observations[wrong]["observationId"], operation="reopen")
                    elif mutation in ("owner", "store"):
                        observations[-1]["components"][mutation] = copy.deepcopy(observations[0]["components"][mutation])
                    self.proof.update(testIdentity=identity, originalObservations=observations,
                                      manifestSha256=evidence.digest(self.manifest))
                    self.witness.update(testIdentity=identity, proofSha256=evidence.digest(self.proof))
                    self.completion["manifestSha256"] = evidence.digest(self.manifest)
                    if mutation == "valid":
                        result = self.ingest(original_inputs=assignments)
                        self.assertEqual(tuple(result["originalObservations"][self.execution]), tuple(observations))
                    else:
                        with self.assertRaises(evidence.ConformanceError):
                            self.ingest(original_inputs=assignments)

    def test_original_observation_node_images_are_exact_and_deeply_frozen(self):
        self.inputs.update(profileId="metadata", invocation=["profile", "metadata"])
        self.inputs["budgets"]["profileSeconds"] = 5400
        original, assignments = self.original_transport(case_id="MP-32")
        roles = assignments["sqlite"].pop(self.identity)
        self.identity = ("Hoard.Metadata.Tests.MetadataSchemaTests."
                         "MP32_Old_schema_requires_explicit_authorized_upgrade_and_preserves_records")
        self.manifest["expected"][0].update(testIdentity=self.identity, fullyQualifiedName=self.identity)
        nodes, images = [], []
        for index in range(3):
            node = copy.deepcopy(original)
            node.update(testIdentity=self.identity, observationId=str(uuid.uuid4()),
                        parentObservationId=None if not index else nodes[-1]["observationId"],
                        operation="create" if not index else "reopen")
            selected = dict(roles)
            for component in node["components"].values():
                component["instanceId"] = str(uuid.uuid4())
            if index:
                node["components"]["owner"]["assemblySha256"] = "d" * 64
                selected["owner"] = ("provider/Hoard.Fixture.dll", "Hoard.Fixture")
            nodes.append(node)
            images.append(selected)
        unmodified = copy.deepcopy(images)
        self.proof.update(testIdentity=self.identity, originalObservations=nodes,
                          manifestSha256=evidence.digest(self.manifest))
        self.witness.update(testIdentity=self.identity, proofSha256=evidence.digest(self.proof))
        self.completion["manifestSha256"] = evidence.digest(self.manifest)
        frozen = evidence.original_node_assignments(self.identity, images)
        images[1]["owner"] = roles["owner"]
        result = self.ingest(original_inputs={"sqlite": {self.identity: frozen}})
        self.assertEqual(tuple(result["originalObservations"][self.execution]), tuple(nodes))
        for selected in (images, [unmodified[0]], [unmodified[1], unmodified[0], unmodified[2]]):
            with self.subTest(nodes=len(selected)), self.assertRaises(evidence.ConformanceError):
                self.ingest(original_inputs={"sqlite": {self.identity: selected}})

    def test_original_observation_owner_only_admission_cannot_replace_real_session_roles(self):
        observation, _ = self.original_transport(contract=True)
        self.identity = ("Hoard.Artifacts.Tests.ArtifactCompositionTests."
                         'Configured_selection_is_inert_until_start_and_missing_guarantees_block_readiness(provider: "local")')
        self.manifest["expected"][0].update(testIdentity=self.identity, fullyQualifiedName=self.identity.split("(")[0])
        owner = {**observation["components"]["contract"], "assemblySha256": "e" * 64}
        observation.update(testIdentity=self.identity, kind="original-owner", operation="create", components={"owner": owner})
        self.proof.update(testIdentity=self.identity, originalObservations=[observation],
                          manifestSha256=evidence.digest(self.manifest))
        self.witness.update(testIdentity=self.identity, proofSha256=evidence.digest(self.proof))
        self.completion["manifestSha256"] = evidence.digest(self.manifest)
        assignments = {"local": {self.identity: {"owner": ("consumer/Hoard.Tests.dll", None)}}}
        self.assertEqual(self.ingest(original_inputs=assignments, expected_tests={self.identity: ("local", "none")})[
            "originalObservations"][self.execution][0], observation)
        original = copy.deepcopy(observation)
        for mutation in ("kind", "extra-role", "parent", "operation", "provider-session"):
            with self.subTest(mutation=mutation):
                observation = copy.deepcopy(original)
                if mutation == "kind":
                    observation["kind"] = "original-instance"
                elif mutation == "extra-role":
                    observation["components"]["store"] = copy.deepcopy(owner)
                elif mutation == "parent":
                    observation["parentObservationId"] = str(uuid.uuid4())
                    observation["operation"] = "reopen"
                elif mutation == "operation":
                    observation["operation"] = "contract"
                else:
                    observation["testIdentity"] = (
                        'Hoard.Artifacts.Tests.ArtifactPublicationTests.Empty_content_and_true_absence_are_distinct(provider: "local")')
                    self.manifest["expected"][0].update(testIdentity=observation["testIdentity"],
                                                       fullyQualifiedName=observation["testIdentity"].split("(")[0])
                    self.proof.update(testIdentity=observation["testIdentity"],
                                      manifestSha256=evidence.digest(self.manifest))
                    self.witness["testIdentity"] = observation["testIdentity"]
                    self.completion["manifestSha256"] = evidence.digest(self.manifest)
                    assignments = {"local": {observation["testIdentity"]: assignments["local"][self.identity]}}
                    self.identity = observation["testIdentity"]
                self.proof["originalObservations"] = [observation]
                self.witness["proofSha256"] = evidence.digest(self.proof)
                with self.assertRaises(evidence.ConformanceError):
                    self.ingest(original_inputs=assignments, expected_tests={self.identity: ("local", "none")})
        self.setUp()
        observation, _ = self.original_transport(contract=True)
        self.identity = ("Hoard.Artifacts.Tests.ArtifactAuthorityTests."
                         "Copied_foreign_changed_scope_and_disposed_handles_never_authorize_retention")
        self.manifest["expected"][0].update(testIdentity=self.identity, fullyQualifiedName=self.identity)
        observation.update(testIdentity=self.identity, kind="original-owner", operation="create", components={"owner": owner})
        second = copy.deepcopy(observation)
        second["observationId"] = str(uuid.uuid4())
        second["components"]["owner"]["instanceId"] = str(uuid.uuid4())
        self.proof.update(testIdentity=self.identity, originalObservations=[observation, second],
                          manifestSha256=evidence.digest(self.manifest))
        self.witness.update(testIdentity=self.identity, proofSha256=evidence.digest(self.proof))
        self.completion["manifestSha256"] = evidence.digest(self.manifest)
        assignments = {"local": {self.identity: {"owner": ("consumer/Hoard.Tests.dll", None)}}}
        result = self.ingest(original_inputs=assignments, expected_tests={self.identity: ("local", "none")})
        self.assertEqual(tuple(result["originalObservations"][self.execution]), (observation, second))
        second["components"]["owner"]["instanceId"] = observation["components"]["owner"]["instanceId"]
        self.witness["proofSha256"] = evidence.digest(self.proof)
        with self.assertRaisesRegex(evidence.ConformanceError, "ProofMismatch"):
            self.ingest(original_inputs=assignments, expected_tests={self.identity: ("local", "none")})

    def history(self, *, max_attempts=1, origin_inputs=None):
        import conformance_case_catalog as catalog
        case = next(case for case in catalog.expected_cases("composition") if case.case_id == "CP-01")
        self.inputs.update(profileId="composition", invocation=["profile", "composition"])
        self.inputs["budgets"]["profileSeconds"] = 3600
        self.identity = case.witnesses[0]
        entry = self.manifest["expected"][0]
        entry.update(testIdentity=self.identity, fullyQualifiedName=self.identity.split("(")[0],
                     bindingId=case.binding_id, matrixId=case.matrix_id, caseId=case.case_id)
        self.manifest["inputSha256"] = evidence.digest(self.inputs)
        self.proof.update(testIdentity=self.identity, bindingId=case.binding_id, matrixId=case.matrix_id,
                          inputSha256=evidence.digest(self.inputs), manifestSha256=evidence.digest(self.manifest),
                          caseId=case.case_id)
        self.witness.update(testIdentity=self.identity, bindingId=case.binding_id, matrixId=case.matrix_id,
                            inputSha256=evidence.digest(self.inputs), proofSha256=evidence.digest(self.proof))
        self.completion.update(inputSha256=evidence.digest(self.inputs), manifestSha256=evidence.digest(self.manifest))
        return evidence.RuntimeCaseHistory(self.inputs, binding_id=case.binding_id,
                                           matrix_id=case.matrix_id, case_id=case.case_id,
                                           max_attempts=max_attempts, origin_inputs=origin_inputs)

    def finish_history(self, history):
        options = self.transport()
        for key in ("inputs", "expected_tests", "started_ms", "ended_ms"):
            del options[key]
        return history.finish(**options)

    def category_history(self, *, profile="metadata", mode="diagnostic", max_attempts=1, origin_inputs=None):
        self.inputs.update(mode=mode, profileId=profile, invocation=["profile", profile])
        self.inputs["budgets"]["profileSeconds"] = 5400 if profile == "metadata" else 10800
        original = self.inputs["bindings"][0]
        bindings = (("sqlite", "Sqlite"), ("memory", "Memory")) if profile == "metadata" else (
            ("local", "Local"), ("object", "ObjectSemantics"))
        family = "Metadata" if profile == "metadata" else "Artifacts"
        packages = [{**original["package"], "packageId": "Hoard.Fixtures." + family + "." + provider}
                    for _, provider in bindings]
        self.inputs["packages"].extend(packages)
        self.inputs["bindings"] = [
            {**original, "bindingId": binding, "package": package, "category": profile,
             "descriptorSha256": hashlib.sha256(binding.encode()).hexdigest()}
            for (binding, _), package in zip(bindings, packages)]
        original_inputs = None if origin_inputs is None else {
            binding: {role: assignments[source] for role, source in
                      (("owner", "session"), ("store", "store"), ("schema", "schema"),
                       ("authority", "authority"), ("controls", "faults"))}
            for binding, assignments in origin_inputs.items()}
        if original_inputs is not None:
            import conformance_case_catalog as catalog
            selected_packages = {item["bindingId"]: item["package"]["packageId"] for item in self.inputs["bindings"]}
            for binding, assignments in original_inputs.items():
                for role in ("store", "schema"):
                    assignments[role] = (assignments[role][0], selected_packages[binding])
            original_inputs = {
                binding: {identity: dict(assignments) for identity in catalog.category_runtime_cases(profile, binding)
                          if catalog.original_witness_policy(identity) is not None}
                for binding, assignments in original_inputs.items()}
        return evidence.CategoryRuntimeHistory(
            self.inputs, max_attempts=max_attempts, origin_inputs=origin_inputs, original_inputs=original_inputs)

    def category_transport(self, binding, *, sequence=1, started=9, origin=None, identities=None,
                           failed_identity=None, selections=None):
        import conformance_case_catalog as catalog
        cases = [case for case in catalog.expected_cases(self.inputs["profileId"])
                 if case.binding_id == binding and case.exclusion is None]
        assignments = {identity: min(case.case_id for case in cases if identity in case.witnesses)
                       for identity in {identity for case in cases for identity in case.witnesses}}
        if self.inputs["mode"] == "qualification" and self.inputs["profileId"] == "metadata" and binding == "sqlite":
            assignments[catalog.METADATA_RECOVERY_SOURCE_WITNESS] = "MP-36"
        if identities is not None:
            assignments = {identity: assignments[identity] for identity in identities}
        selected = ({identity: (binding, case_id) for identity, case_id in assignments.items()}
                    if selections is None else selections)
        manifest = {**self.manifest, "attemptId": self.attempt, "attemptSequence": sequence,
                    "inputSha256": evidence.digest(self.inputs), "expected": [
                        {**self.manifest["expected"][0], "testIdentity": identity,
                         "fullyQualifiedName": identity.split("(")[0], "bindingId": selected_binding,
                         "caseId": case_id}
                        for identity, (selected_binding, case_id) in sorted(selected.items())]}
        proofs, witnesses = {}, []
        for entry in manifest["expected"]:
            binding = entry["bindingId"]
            execution = str(uuid.uuid4())
            proof = {**self.proof, "executionId": execution, "attemptId": self.attempt,
                     "attemptSequence": sequence, "inputSha256": evidence.digest(self.inputs),
                     "manifestSha256": evidence.digest(manifest), "testIdentity": entry["testIdentity"],
                     "bindingId": binding, "caseId": entry["caseId"], "durationMs": 0.5}
            if entry["testIdentity"] == failed_identity:
                proof.update(status="Failed", failureKind="Assertion", assertionSymbol=entry["assertionSymbol"])
            if origin is not None:
                captured = copy.deepcopy(origin)
                captured.update(caseId=entry["caseId"], sessionId=str(uuid.uuid4()),
                                descriptorSha256=next(item["descriptorSha256"] for item in self.inputs["bindings"]
                                                      if item["bindingId"] == binding))
                for component in captured["components"].values():
                    component["instanceId"] = str(uuid.uuid4())
                proof["sessionOrigins"] = [captured]
                policy = catalog.original_witness_policy(entry["testIdentity"])
                if policy is not None:
                    aliases = {"owner": "session", "controls": "faults"}
                    proof["schemaVersion"] = 2
                    observations = []
                    for parent in catalog.original_witness_parents(entry["testIdentity"]):
                        components = {role: copy.deepcopy(captured["components"][aliases.get(role, role)])
                                      for role in policy[2]}
                        for component in components.values():
                            component["instanceId"] = str(uuid.uuid4())
                        observations.append({
                            "schemaVersion": 1, "runId": self.inputs["runId"], "caseId": entry["caseId"],
                            "testIdentity": entry["testIdentity"], "bindingId": binding,
                            "observationId": str(uuid.uuid4()),
                            "parentObservationId": None if parent is None else observations[parent]["observationId"],
                            "kind": policy[1], "operation": "create" if parent is None else "reopen",
                            "runtimeVersion": captured["runtimeVersion"], "processArchitecture": "x64",
                            "components": components})
                    proof["originalObservations"] = observations
            proofs[f"proof-{execution}.json"] = evidence.canonical_bytes(proof)
            witnesses.append({**self.witness, "executionId": execution, "testIdentity": entry["testIdentity"],
                              "bindingId": binding, "inputSha256": evidence.digest(self.inputs),
                              "startedMs": started + 0.25, "endedMs": started + 0.75,
                              "status": proof["status"], "proofSha256": evidence.digest(proof)})
        lines = b"".join(evidence.canonical_bytes(witness) + b"\n" for witness in witnesses)
        completion = {**self.completion, "attemptId": self.attempt, "attemptSequence": sequence,
                      "inputSha256": evidence.digest(self.inputs), "manifestSha256": evidence.digest(manifest),
                      "expectedCount": len(witnesses), "observedCount": len(witnesses),
                      "recordsSha256": hashlib.sha256(lines).hexdigest(),
                      "diagnosticCode": "AssertionFailed" if failed_identity in selected else "None"}
        return {
            "manifest_data": evidence.canonical_bytes(manifest), "owner_data": evidence.canonical_bytes(self.owner),
            "witnesses_data": lines, "proofs": proofs, "completion_data": evidence.canonical_bytes(completion),
            "manifest_sha256": evidence.digest(manifest), "owner_sha256": evidence.digest(self.owner)}

    def joint_category_partitions(self, history):
        partitions, selected = {"mixed": [], "repeated": []}, set()
        for binding in ("local", "object"):
            for identity in history.expected_runtime_tests(binding):
                partitions["repeated" if identity in selected else "mixed"].append((binding, identity))
                selected.add(identity)
        return partitions

    def test_joint_category_import_freezes_both_bindings_and_retains_unmodified_mixed_scope_proofs(self):
        import conformance_case_catalog as catalog
        history = self.category_history(profile="artifacts")
        partitions = {scope: list(rows) for scope, rows in catalog.category_execution_partitions("artifacts").items()}
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            self.assertEqual(history.begin_joint(self.attempt, partitions=partitions), 1)
        plan = history.joint_partitions()
        self.assertEqual({binding for binding, _ in plan["original"]["tests"].values()}, {"local", "object"})
        expected = {(binding, identity) for binding in ("local", "object")
                    for identity in history.expected_runtime_tests(binding)}
        self.assertEqual({(binding, identity) for scope in plan.values()
                          for identity, (binding, _) in scope["tests"].items()}, expected)
        partitions["original"].clear()
        with self.assertRaises(TypeError):
            plan["original"]["tests"]["foreign"] = ("local", "AS-01")
        transports, actual = {}, {}
        for scope_id, scope in plan.items():
            self.attempt = scope["attemptId"]
            transports[scope_id] = self.category_transport(None, selections=scope["tests"])
            actual.update({name: hashlib.sha256(raw).hexdigest() for name, raw in transports[scope_id]["proofs"].items()})
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            results = history.finish_joint(transports=transports)
        self.assertEqual(dict(history.proofs), actual)
        self.assertEqual({(row["bindingId"], row["testIdentity"]) for row in history.witnesses}, expected)
        owned = {row["executionId"]: row["bindingId"] for row in history.witnesses}
        self.assertEqual({(row["profileId"], row["bindingId"], row["matrixId"], row["caseId"]) for row in results},
                         {case.key for case in catalog.expected_cases("artifacts")})
        for row in results:
            for attempt in row["attempts"]:
                self.assertTrue(all(owned[identity] == row["bindingId"] for identity in attempt["witnessIds"]))
        with self.assertRaisesRegex(evidence.ConformanceError, "OwnershipInvalid"):
            history.joint_partitions()

    def test_joint_category_import_rejects_incomplete_overlapping_or_ambiguous_plans_before_start(self):
        original = copy.deepcopy(self.inputs)
        for mutation in ("missing", "overlap", "ambiguous", "foreign", "empty"):
            with self.subTest(mutation=mutation):
                self.inputs = copy.deepcopy(original)
                history = self.category_history(profile="artifacts")
                partitions = self.joint_category_partitions(history)
                if mutation == "missing":
                    partitions["mixed"].pop()
                elif mutation == "overlap":
                    partitions["repeated"].append(partitions["mixed"][0])
                elif mutation == "ambiguous":
                    binding, identity = partitions["repeated"].pop()
                    partitions["mixed"].append((binding, identity))
                elif mutation == "foreign":
                    partitions["mixed"][0] = ("local", "Foreign.Unselected.Fact")
                else:
                    partitions["empty"] = []
                with self.assertRaises(evidence.ConformanceError):
                    history.begin_joint(self.attempt, partitions=partitions)
                with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
                    history.begin_joint(self.attempt, partitions=self.joint_category_partitions(history))
                with self.assertRaisesRegex(evidence.ConformanceError, "OwnershipInvalid"):
                    history.interrupt("local", "EvidenceIncomplete")
                with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
                    history.interrupt_joint("EvidenceIncomplete")
                self.assertEqual(history.witnesses, ())

    def test_joint_category_import_is_atomic_and_a_fresh_retry_preserves_both_bindings_failed_attempts(self):
        original = copy.deepcopy(self.inputs)
        for mutation, code in (("missing", "EvidenceIncomplete"), ("attempt", "ProofMismatch")):
            with self.subTest(mutation=mutation):
                self.inputs = copy.deepcopy(original)
                history = self.category_history(profile="artifacts", max_attempts=2)
                with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
                    history.begin_joint(self.attempt, partitions=self.joint_category_partitions(history))
                plan, transports = history.joint_partitions(), {}
                for scope_id, scope in plan.items():
                    self.attempt = plan["mixed"]["attemptId"] if mutation == "attempt" else scope["attemptId"]
                    transports[scope_id] = self.category_transport(None, selections=scope["tests"])
                if mutation == "missing":
                    del transports["repeated"]
                with mock.patch.object(evidence.time, "monotonic", return_value=0.012), self.assertRaisesRegex(
                        evidence.ConformanceError, code):
                    history.finish_joint(transports=transports)
                self.assertEqual(history.witnesses, ())
                self.assertEqual(dict(history.proofs), {})
                self.assertEqual(dict(history.session_origins), {})
                self.assertEqual(dict(history.original_observations), {})
                with mock.patch.object(evidence.time, "monotonic", return_value=0.020):
                    self.assertEqual(history.begin_joint(
                        str(uuid.uuid4()), partitions=self.joint_category_partitions(history)), 2)
                transports = {}
                for scope_id, scope in history.joint_partitions().items():
                    self.attempt = scope["attemptId"]
                    transports[scope_id] = self.category_transport(
                        None, selections=scope["tests"], sequence=2, started=20)
                with mock.patch.object(evidence.time, "monotonic", return_value=0.023):
                    results = history.finish_joint(transports=transports)
                self.assertTrue(any(row["status"] == "Passed" for row in results))
                self.assertTrue(all(len(row["attempts"]) == 2 for row in results if row["applicable"]))

    def test_joint_category_failure_is_attributed_only_to_the_actual_binding_and_mapped_cases(self):
        import conformance_case_catalog as catalog
        history = self.category_history(profile="artifacts")
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin_joint(self.attempt, partitions=self.joint_category_partitions(history))
        plan, transports = history.joint_partitions(), {}
        identity = next(iter(plan["repeated"]["tests"]))
        binding, _ = plan["repeated"]["tests"][identity]
        for scope_id, scope in plan.items():
            self.attempt = scope["attemptId"]
            transports[scope_id] = self.category_transport(
                None, selections=scope["tests"], failed_identity=identity if scope_id == "repeated" else None)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            results = history.finish_joint(transports=transports)
        self.assertEqual({(row["profileId"], row["bindingId"], row["matrixId"], row["caseId"])
                          for row in results if row["status"] == "Failed"},
                         {case.key for case in catalog.expected_cases("artifacts")
                          if case.binding_id == binding and case.exclusion is None and identity in case.witnesses})
        actual = [row for row in history.witnesses if row["testIdentity"] == identity]
        self.assertEqual({row["bindingId"]: row["status"] for row in actual},
                         {binding: "Failed", "local" if binding == "object" else "object": "Passed"})

    def test_category_partitioned_import_freezes_the_complete_inventory_and_preserves_actual_scope_proofs(self):
        import conformance_case_catalog as catalog
        history = self.category_history()
        identities = tuple(history.expected_runtime_tests("sqlite"))
        partitions = {"first": list(identities[::2]), "second": list(identities[1::2])}
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            sequence = history.begin("sqlite", self.attempt, partitions=partitions)
        plan = history.runtime_partitions("sqlite")
        self.assertEqual(sequence, 1)
        self.assertEqual(set(plan), set(partitions))
        self.assertEqual({identity for scope in plan.values() for identity in scope["tests"]}, set(identities))
        self.assertEqual(len({scope["attemptId"] for scope in plan.values()} | {self.attempt}), 3)
        partitions["first"].clear()
        with self.assertRaises(TypeError):
            plan["first"]["tests"][identities[0]] = "foreign"
        transports, actual_proofs = {}, {}
        for scope_id, scope in plan.items():
            self.attempt = scope["attemptId"]
            transports[scope_id] = self.category_transport("sqlite", identities=scope["tests"])
            actual_proofs.update({path: hashlib.sha256(data).hexdigest()
                                  for path, data in transports[scope_id]["proofs"].items()})
        self.assertEqual(history.witnesses, ())
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            results = history.finish_parts("sqlite", transports=transports)
        self.assertEqual({row["testIdentity"] for row in history.witnesses}, set(identities))
        self.assertEqual(dict(history.proofs), actual_proofs)
        cases = {case.key: case for case in catalog.expected_cases("metadata") if case.binding_id == "sqlite"}
        for result in results:
            case = cases[result["profileId"], result["bindingId"], result["matrixId"], result["caseId"]]
            self.assertEqual(result["status"], "Incomplete" if case.controls else "Passed")
        with self.assertRaisesRegex(evidence.ConformanceError, "OwnershipInvalid"):
            history.runtime_partitions("sqlite")

    def test_category_partitioned_import_rejects_reduced_overlapping_or_foreign_plans_before_start(self):
        original_inputs = copy.deepcopy(self.inputs)
        for mutation in ("missing", "overlap", "foreign", "empty", "duplicate"):
            with self.subTest(mutation=mutation):
                self.inputs = copy.deepcopy(original_inputs)
                history = self.category_history()
                identities = tuple(history.expected_runtime_tests("sqlite"))
                partitions = {"first": list(identities[::2]), "second": list(identities[1::2])}
                if mutation == "missing":
                    partitions["first"].pop()
                elif mutation == "overlap":
                    partitions["second"].append(partitions["first"][0])
                elif mutation == "foreign":
                    partitions["first"][0] = "Foreign.Unselected.Fact"
                elif mutation == "empty":
                    partitions["empty"] = []
                else:
                    partitions["first"].append(partitions["first"][0])
                with self.assertRaises(evidence.ConformanceError):
                    history.begin("sqlite", self.attempt, partitions=partitions)
                with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
                    self.assertEqual(history.begin("sqlite", self.attempt), 1)
                with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
                    history.interrupt("sqlite", "EvidenceIncomplete")
                self.assertEqual(history.witnesses, ())

    def test_category_partitioned_import_is_atomic_for_missing_scopes_wrong_attempts_and_replayed_origins(self):
        original_inputs = copy.deepcopy(self.inputs)
        for mutation in ("missing", "attempt", "session", "execution"):
            with self.subTest(mutation=mutation):
                self.inputs = copy.deepcopy(original_inputs)
                origin, assignments = self.runtime_origin("runtime")
                history = self.category_history(
                    max_attempts=2, origin_inputs={"sqlite": assignments, "memory": assignments})
                identities = tuple(history.expected_runtime_tests("sqlite"))
                partitions = {"first": identities[::2], "second": identities[1::2]}
                with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
                    history.begin("sqlite", self.attempt, partitions=partitions)
                plan = history.runtime_partitions("sqlite")
                transports = {}
                for scope_id, scope in plan.items():
                    self.attempt = plan["first"]["attemptId"] if mutation == "attempt" else scope["attemptId"]
                    transports[scope_id] = self.category_transport(
                        "sqlite", identities=scope["tests"], origin=origin)
                if mutation == "missing":
                    del transports["second"]
                elif mutation in ("session", "execution"):
                    first = evidence.load_json(next(iter(transports["first"]["proofs"].values())))
                    transport = transports["second"]
                    witnesses = [evidence.load_json(line) for line in transport["witnesses_data"].splitlines()]
                    witness = witnesses[0]
                    path = f'proof-{witness["executionId"]}.json'
                    proof = evidence.load_json(transport["proofs"].pop(path))
                    if mutation == "session":
                        proof["sessionOrigins"][0]["sessionId"] = first["sessionOrigins"][0]["sessionId"]
                    else:
                        proof["executionId"] = witness["executionId"] = first["executionId"]
                    transport["proofs"][f'proof-{proof["executionId"]}.json'] = evidence.canonical_bytes(proof)
                    witness["proofSha256"] = evidence.digest(proof)
                    transport["witnesses_data"] = b"".join(
                        evidence.canonical_bytes(row) + b"\n" for row in witnesses)
                    completion = evidence.load_json(transport["completion_data"])
                    completion["recordsSha256"] = hashlib.sha256(transport["witnesses_data"]).hexdigest()
                    transport["completion_data"] = evidence.canonical_bytes(completion)
                with mock.patch.object(evidence.time, "monotonic", return_value=0.012), self.assertRaisesRegex(
                        evidence.ConformanceError, "EvidenceIncomplete" if mutation == "missing" else "ProofMismatch"):
                    history.finish_parts("sqlite", transports=transports)
                self.assertEqual(history.witnesses, ())
                self.assertEqual(dict(history.proofs), {})
                self.assertEqual(dict(history.session_origins), {})
                self.assertEqual(dict(history.original_observations), {})
                with mock.patch.object(evidence.time, "monotonic", return_value=0.020):
                    self.assertEqual(history.begin("sqlite", str(uuid.uuid4()), partitions=partitions), 2)
                retry = history.runtime_partitions("sqlite")
                transports = {}
                for scope_id, scope in retry.items():
                    self.attempt = scope["attemptId"]
                    transports[scope_id] = self.category_transport(
                        "sqlite", sequence=2, started=20, identities=scope["tests"], origin=origin)
                with mock.patch.object(evidence.time, "monotonic", return_value=0.023):
                    results = history.finish_parts("sqlite", transports=transports)
                self.assertTrue(any(result["status"] == "Passed" for result in results))
                self.assertTrue(all(len(result["attempts"]) == 2 for result in results))

    def test_category_partitioned_import_preserves_a_failed_scope_without_failing_unrelated_cases(self):
        import conformance_case_catalog as catalog
        history = self.category_history()
        identities = tuple(history.expected_runtime_tests("sqlite"))
        failed = next(identity for identity in identities if ".MP01_" in identity)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin("sqlite", self.attempt, partitions={
                "failed": [failed], "unchanged": [identity for identity in identities if identity != failed]})
        transports = {}
        for scope_id, scope in history.runtime_partitions("sqlite").items():
            self.attempt = scope["attemptId"]
            transports[scope_id] = self.category_transport(
                "sqlite", identities=scope["tests"], failed_identity=failed)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            results = history.finish_parts("sqlite", transports=transports)
        cases = {case.case_id: case for case in catalog.expected_cases("metadata") if case.binding_id == "sqlite"}
        self.assertTrue(any(result["status"] == "Failed" for result in results))
        self.assertTrue(any(result["status"] == "Passed" for result in results))
        for result in results:
            case = cases[result["caseId"]]
            expected = "Failed" if failed in case.witnesses else "Incomplete" if case.controls else "Passed"
            self.assertEqual(result["status"], expected)
        failed_witness = next(row for row in history.witnesses if row["testIdentity"] == failed)
        self.assertEqual(failed_witness["status"], "Failed")
        self.assertEqual(history.proofs[f'proof-{failed_witness["executionId"]}.json'], failed_witness["proofSha256"])

    def test_category_import_expands_all_frozen_keys_without_inventing_controls_or_excluded_executions(self):
        import conformance_case_catalog as catalog
        history = self.category_history()
        for binding in ("sqlite", "memory"):
            self.attempt = str(uuid.uuid4())
            with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
                self.assertEqual(history.begin(binding, self.attempt), 1)
            with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
                history.finish(binding, **self.category_transport(binding))
            if binding == "sqlite":
                with self.assertRaisesRegex(evidence.ConformanceError, "EvidenceIncomplete"):
                    history.results()
        with self.assertRaisesRegex(evidence.ConformanceError, "EvidenceIncomplete"):
            history.results()
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin("none", str(uuid.uuid4()))
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            history.interrupt("none", "EvidenceIncomplete")
        results = history.results()
        cases = catalog.expected_cases("metadata")
        self.assertEqual({(result["profileId"], result["bindingId"], result["matrixId"], result["caseId"])
                          for result in results}, {case.key for case in cases})
        self.assertEqual(sum(result["bindingId"] != "none" for result in results), 96)
        self.assertEqual(sum(result["status"] == "NotApplicable" for result in results), 9)
        for case, result in zip(cases, results):
            self.assertEqual(result["status"], "NotApplicable" if case.exclusion else
                             "Incomplete" if case.controls else "Passed")
            if case.exclusion:
                self.assertEqual(result["attempts"], ())
                self.assertEqual(result["proofSha256"], ())
            else:
                actual = {witness["testIdentity"] for witness in history.witnesses
                          if witness["executionId"] in result["attempts"][0]["witnessIds"]}
                self.assertEqual(actual, set(case.witnesses))
        uses = [execution for result in results for attempt in result["attempts"]
                for execution in attempt["witnessIds"]]
        self.assertGreater(len(uses), len(set(uses)))
        self.assertEqual(len(history.proofs), len(history.witnesses))

    def test_category_import_rejects_reduced_manifests_and_retains_failure_before_an_exact_retry(self):
        history = self.category_history(max_attempts=2)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin("sqlite", self.attempt)
        transport = self.category_transport("sqlite")
        manifest = evidence.load_json(transport["manifest_data"])
        manifest["expected"].pop()
        transport.update(manifest_data=evidence.canonical_bytes(manifest),
                         manifest_sha256=evidence.digest(manifest))
        with mock.patch.object(evidence.time, "monotonic", return_value=0.010), self.assertRaisesRegex(
                evidence.ConformanceError, "ProofMismatch"):
            history.finish("sqlite", **transport)
        self.attempt = str(uuid.uuid4())
        with mock.patch.object(evidence.time, "monotonic", return_value=0.011):
            self.assertEqual(history.begin("sqlite", self.attempt), 2)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            results = history.finish("sqlite", **self.category_transport("sqlite", sequence=2, started=11))
        self.assertEqual(len(results), 48)
        self.assertTrue(all(len(result["attempts"]) == 2 for result in results))
        self.assertTrue(all(result["attempts"][0]["diagnosticCode"] == "ProofMismatch" for result in results))
        self.assertTrue(any(result["status"] == "Passed" for result in results))
        self.assertTrue(all(not result["attempts"][0]["witnessIds"] for result in results))

    def test_category_import_never_promotes_diagnostic_packets_without_actual_qualification_origins(self):
        history = self.category_history(mode="qualification")
        with self.assertRaisesRegex(evidence.ConformanceError, "OwnershipInvalid"):
            evidence.CategoryRuntimeHistory(self.inputs, native_sources=object())
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin("sqlite", self.attempt)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012), self.assertRaisesRegex(
                evidence.ConformanceError, "WitnessMissing"):
            history.finish("sqlite", **self.category_transport("sqlite"))
        self.assertEqual(history.witnesses, ())
        self.assertEqual(dict(history.proofs), {})

    def test_known_inspection_and_controller_witnesses_cannot_qualify_with_unrelated_valid_sessions(self):
        import conformance_case_catalog as catalog
        self.assertTrue(callable(getattr(evidence, "inspect_runtime_attempt", None)))
        baseline = copy.deepcopy((self.inputs, self.manifest, self.proof, self.witness, self.completion))
        fixtures = (".MetadataBoundaryTests.", ".ArtifactBoundaryTests.", ".ArtifactCrashTests.",
                    ".ArtifactNonCooperativeChildTests.", ".ArtifactTransferProofTests.",
                    ".MetadataRecoveryRuntimeTests.")
        for profile, binding in (("metadata", "sqlite"), ("artifacts", "local"), ("artifacts", "object")):
            identities = tuple(catalog.category_runtime_cases(profile, binding))
            if (profile, binding) == ("metadata", "sqlite"):
                identities += (catalog.METADATA_RECOVERY_SOURCE_WITNESS,)
            for identity in identities:
                if not any(fixture in identity for fixture in fixtures):
                    continue
                with self.subTest(binding=binding, identity=identity):
                    self.inputs, self.manifest, self.proof, self.witness, self.completion = copy.deepcopy(baseline)
                    origin, assignments = self.runtime_origin("runtime")
                    if profile == "artifacts":
                        del origin["components"]["schema"], assignments["schema"]
                        for role in ("validator", "maintenance", "lifetime"):
                            origin["components"][role] = {
                                **origin["components"]["store"], "instanceId": str(uuid.uuid4())}
                            assignments[role] = assignments["store"]
                    self.inputs["bindings"][0].update(bindingId=binding, category=profile)
                    self.identity = identity
                    self.manifest["expected"][0].update(
                        testIdentity=identity, fullyQualifiedName=identity.split("(")[0], bindingId=binding)
                    self.proof.update(testIdentity=identity, bindingId=binding, sessionOrigins=[origin])
                    self.witness.update(testIdentity=identity, bindingId=binding)
                    for mode in ("diagnostic", "qualification"):
                        self.inputs["mode"] = mode
                        input_sha = evidence.digest(self.inputs)
                        self.manifest["inputSha256"] = input_sha
                        manifest_sha = evidence.digest(self.manifest)
                        self.proof.update(inputSha256=input_sha, manifestSha256=manifest_sha)
                        self.witness.update(inputSha256=input_sha, proofSha256=evidence.digest(self.proof))
                        self.completion.update(inputSha256=input_sha, manifestSha256=manifest_sha)
                        options = {"origin_inputs": {binding: assignments},
                                   "expected_tests": {identity: (binding, "none")}}
                        if mode == "diagnostic":
                            self.assertEqual(self.ingest(**options)["diagnosticCode"], "None")
                        else:
                            inspected = evidence.inspect_runtime_attempt(**self.transport(**options))
                            self.assertFalse(inspected["qualification"])
                            self.assertEqual(inspected["inputs"]["mode"], "qualification")
                            self.assertEqual(
                                inspected["observation"]["witnesses"][0]["testIdentity"], identity)
                            with self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
                                self.ingest(**options)

    def test_runtime_inspection_freezes_unqualified_transport_without_skipping_validation(self):
        self.inputs["mode"] = "qualification"
        input_sha = evidence.digest(self.inputs)
        self.manifest["inputSha256"] = input_sha
        manifest_sha = evidence.digest(self.manifest)
        self.proof.update(inputSha256=input_sha, manifestSha256=manifest_sha)
        self.witness.update(inputSha256=input_sha, proofSha256=evidence.digest(self.proof))
        self.completion.update(inputSha256=input_sha, manifestSha256=manifest_sha)
        transport = self.transport()
        inspected = evidence.inspect_runtime_attempt(**transport)
        self.assertFalse(inspected["qualification"])
        self.assertEqual(inspected["inputsSha256"], input_sha)
        self.assertEqual(inspected["observation"]["diagnosticCode"], "None")
        with self.assertRaises(TypeError):
            inspected["qualification"] = True
        with self.assertRaises(TypeError):
            inspected["inputs"]["mode"] = "diagnostic"
        with self.assertRaises(TypeError):
            inspected["observation"]["proofs"]["foreign"] = "a" * 64
        with self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
            evidence.ingest_runtime_attempt(**transport)
        for changed in (
            {"proofs": {f"proof-{self.execution}.json": b"{}"}},
            {"witnesses_data": transport["witnesses_data"][:-1]},
            {"completion_data": evidence.canonical_bytes({
                **evidence.load_json(transport["completion_data"]), "complete": False})},
        ):
            with self.subTest(changed=changed), self.assertRaises(evidence.ConformanceError):
                evidence.inspect_runtime_attempt(**{**transport, **changed})
        self.inputs["mode"] = "diagnostic"
        self.assertEqual(inspected["inputs"]["mode"], "qualification")

    def test_category_import_requires_inspection_evidence_even_when_all_provider_origins_are_valid(self):
        origin, assignments = self.runtime_origin("runtime")
        history = self.category_history(
            mode="qualification", origin_inputs={"sqlite": assignments, "memory": assignments})
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin("sqlite", self.attempt)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012), self.assertRaisesRegex(
                evidence.ConformanceError, "WitnessMissing"):
            history.finish("sqlite", **self.category_transport("sqlite", origin=origin))
        self.assertEqual(history.witnesses, ())
        self.assertEqual(dict(history.session_origins), {})
        self.assertEqual(dict(history.original_observations), {})

    def test_native_metadata_recovery_requires_every_actual_input_bound_seed_kill_and_readback(self):
        import conformance_case_catalog as catalog
        import conformance_sources as sources
        from types import SimpleNamespace

        history = self.category_history(mode="qualification")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            def write(path, raw):
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    path.chmod(0o600)
                path.write_bytes(raw)
                path.chmod(0o400)

            assembly = "candidate/tests/fixtures/metadata/CrashRunner/bin/Release/net10.0/Hoard.Fixtures.Metadata.CrashRunner.dll"
            write(root / assembly, b"explicit-controller-model-not-native-execution")
            self.inputs["runtimeAssemblies"] = {assembly: evidence.file_sha256(root / assembly)}
            namespace = "qualification-sqlite-recovery"
            inputs_path = f"proofs/{namespace}-native-inputs.json"
            write(root / inputs_path, evidence.canonical_bytes(self.inputs))
            input_files = {assembly: self.inputs["runtimeAssemblies"][assembly], inputs_path: evidence.digest(self.inputs)}
            run = SimpleNamespace(root=root, run_id=self.inputs["runId"], root_id=str(uuid.uuid4()),
                                  live_children=lambda: ())
            retained, commands, observations, proof_hashes = {}, [], [], {}
            steps = [(kind, barrier, value) for kind, rows in (
                ("mutation", (("M0", 0), ("M1", 1), ("M2", 2))),
                ("upgrade", tuple((f"U{index}", 10 + index) for index in range(5))),
                ("restore", (("R0", 20), ("R1", 21)))) for barrier, value in rows]
            executions = [(mode + "-" + kind, barrier, value if mode == "run" else None)
                          for kind, barrier, value in steps for mode in ("seed", "run", "recover")]
            executions.append(("recovery-walkthrough", "none", None))
            for sequence, (mode, barrier, value) in enumerate(executions, 1):
                directory = root / "stores" / namespace / ("walkthrough" if barrier == "none" else barrier)
                args = ["dotnet", str(root / assembly), mode, str(directory / "metadata.db"), str(directory), barrier]
                control = {
                    "schemaVersion": 1, "sequence": sequence, "childPid": 200 + sequence,
                    "childStartSha256": hashlib.sha256(str(sequence).encode()).hexdigest(),
                    "startedMs": sequence * 3 + 10, "endedMs": sequence * 3 + 12,
                    "exitCode": 0 if value is None else -9, "diagnosticCode": "None",
                    "groupState": "Exited", "scope": "recovery",
                    **({"barrier": {"value": value, "observedMs": sequence * 3 + 10.5,
                                   "signalMs": sequence * 3 + 11}} if value is not None else {})}
                raw = evidence.canonical_bytes(control)
                control_sha = hashlib.sha256(raw).hexdigest()
                native = {
                    **{key: val for key, val in control.items() if key != "barrier"},
                    "runId": run.run_id, "rootId": run.root_id, "inputFiles": input_files,
                    "argvSha256": evidence.digest(args),
                    "cwdSha256": hashlib.sha256(str((root / assembly).parent).encode()).hexdigest(),
                    "controlRecordSha256": control_sha}
                retained[sequence] = evidence.canonical_bytes(native)
                write(root / f"proofs/recovery-command-{sequence:04}.json", raw)
                write(root / f"proofs/execution-command-{sequence:04}.json", retained[sequence])
                commands.append({"mode": mode, "barrierId": barrier, "sequence": sequence,
                                 "controllerSha256": control_sha,
                                 "executionSha256": hashlib.sha256(retained[sequence]).hexdigest()})
                proof_hashes[mode, barrier] = control_sha, control
            for kind, barrier, value in steps:
                observations.append({
                    "barrierId": barrier, "value": value, "seedSha256": proof_hashes["seed-" + kind, barrier][0],
                    "controllerSha256": proof_hashes["run-" + kind, barrier][0],
                    "readbackSha256": proof_hashes["recover-" + kind, barrier][0],
                    "childStartSha256": proof_hashes["run-" + kind, barrier][1]["childStartSha256"]})
            producer = {
                "qualification": False, "mode": "metadata-recovery", "code": "None",
                "inputsSha256": evidence.digest(self.inputs), "barriers": observations,
                "walkthroughSha256": proof_hashes["recovery-walkthrough", "none"][0]}
            write(root / f"proofs/{namespace}.json", evidence.canonical_bytes(producer))
            graph = {
                "schemaVersion": 1, "qualification": False, "runId": run.run_id,
                "invocationGroupId": self.inputs["invocationGroupId"], "inputsSha256": evidence.digest(self.inputs),
                "assemblyPath": assembly, "inputsPath": inputs_path, "commands": commands,
                "sourceReceiptSha256": evidence.digest(producer)}
            graph_path = root / f"proofs/{namespace}-native-executions.json"
            write(graph_path, evidence.canonical_bytes(graph))

            def read(sequence):
                if sequence not in retained:
                    raise evidence.ConformanceError("OwnershipInvalid")
                return retained[sequence]

            run.read_execution_record = read
            with mock.patch.object(sources, "OwnedRun", type(run)):
                admitted = sources.native_metadata_recovery_controls(
                    run, self.inputs, started_ms=9, ended_ms=110)
                self.assertEqual(set(admitted["controls"]),
                                 {"parent-kill:" + barrier for _, barrier, _ in steps} | {"verified-recovery-walkthrough"})
                self.assertTrue(admitted["sourceProofs"])
                with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
                    history.begin("sqlite", self.attempt)
                case = next(case for case in history._cases if case.binding_id == "sqlite" and case.case_id == "MP-38")
                witnesses = tuple({
                    "bindingId": "sqlite", "testIdentity": identity, "executionId": str(uuid.uuid4()),
                    "status": "Passed", "proofSha256": "e" * 64} for identity in case.witnesses)
                before = history._case_results("sqlite", "None", 110, witnesses)[case.key]
                after = history._case_results(
                    "sqlite", "None", 110, witnesses, control_proofs=admitted["controls"])[case.key]
                self.assertEqual(before["status"], "Incomplete")
                self.assertEqual(after["status"], "Incomplete")
                self.assertEqual(after["attempts"][0]["witnessIds"], ())
                self.assertTrue(set(admitted["controls"]["parent-kill:M0"]) <= set(after["attempts"][0]["proofSha256"]))
                runtime_source = {
                    "bindingId": "sqlite", "testIdentity": catalog.METADATA_RECOVERY_SOURCE_WITNESS,
                    "executionId": str(uuid.uuid4()), "status": "Passed", "proofSha256": "f" * 64}
                attributed = history._case_results(
                    "sqlite", "None", 110, (*witnesses, runtime_source),
                    source_parents={runtime_source["executionId"]: "d" * 64},
                    control_proofs=admitted["controls"])[case.key]
                self.assertEqual(attributed["status"], "Passed")
                self.assertEqual(attributed["attempts"][0]["witnessIds"], (runtime_source["executionId"],))
                recovered_cases = [
                    item for item in catalog.expected_cases("metadata")
                    if item.binding_id == "sqlite" and item.exclusion is None and item.controls
                    and set(item.controls) <= admitted["controls"].keys()]
                self.assertEqual({item.case_id for item in recovered_cases},
                                 {"MP-36", "MP-38", "MP-39", "MP-40", "MP-41", "MP-42", "MP-44", "MP-45"})
                source_results = history._case_results(
                    "sqlite", "None", 110, (runtime_source,),
                    source_parents={runtime_source["executionId"]: "d" * 64},
                    control_proofs=admitted["controls"])
                for item in recovered_cases:
                    self.assertEqual(source_results[item.key]["status"], "Passed")
                    self.assertEqual(source_results[item.key]["attempts"][0]["witnessIds"],
                                     (runtime_source["executionId"],))
                self.assertEqual(history._case_results(
                    "sqlite", "None", 110, (*witnesses, runtime_source),
                    source_parents={}, control_proofs=admitted["controls"])[case.key]["status"], "Incomplete")
                source_manifest = {
                    **self.manifest, "inputSha256": evidence.digest(self.inputs),
                    "expected": [{**self.manifest["expected"][0], "bindingId": "sqlite", "caseId": "MP-36",
                                  "testIdentity": catalog.METADATA_RECOVERY_SOURCE_WITNESS}]}
                context = sources.metadata_recovery_context(run, self.inputs, source_manifest, ended_ms=110)
                self.assertEqual(len(context["files"]), 65)
                packet = {
                    "schemaVersion": 1, "qualification": False, "runId": run.run_id,
                    "attemptId": source_manifest["attemptId"], "inputsSha256": evidence.digest(self.inputs),
                    "testIdentity": catalog.METADATA_RECOVERY_SOURCE_WITNESS,
                    "files": {hashlib.sha256(path.encode()).hexdigest(): value
                              for path, value in context["files"].items()}}
                packet_path = Path(context["outputDirectory"]) / (
                    "metadata-recovery-" + hashlib.sha256(catalog.METADATA_RECOVERY_SOURCE_WITNESS.encode()).hexdigest()
                    + ".json")
                write(packet_path, evidence.canonical_bytes(packet))
                observed_source = {
                    "diagnosticCode": "None", "attemptId": source_manifest["attemptId"],
                    "witnesses": (runtime_source,), "proofs": {
                        f'proof-{runtime_source["executionId"]}.json': runtime_source["proofSha256"]}}
                source_observations, source_packets = sources.metadata_recovery_observations(
                    root, self.inputs, source_manifest, observed_source, context)
                self.assertEqual(source_observations[0]["executionId"], runtime_source["executionId"])
                self.assertEqual(len(source_packets), 1)
                changed = {**packet, "files": dict(packet["files"])}
                changed["files"][next(iter(changed["files"]))] = "0" * 64
                write(packet_path, evidence.canonical_bytes(changed))
                with self.assertRaises(evidence.ConformanceError):
                    sources.metadata_recovery_observations(
                        root, self.inputs, source_manifest, observed_source, context)
                missing = dict(admitted["controls"])
                del missing["parent-kill:M0"]
                self.assertEqual(history._case_results(
                    "sqlite", "None", 110, witnesses, control_proofs=missing)[case.key]["status"], "Incomplete")
                for change in (
                        {"commands": commands[:-1]},
                        {"commands": [commands[0] | {"sequence": 99}, *commands[1:]]},
                        {"inputsSha256": "a" * 64}):
                    write(graph_path, evidence.canonical_bytes(graph | change))
                    with self.subTest(change=list(change)), self.assertRaises(evidence.ConformanceError):
                        sources.native_metadata_recovery_controls(run, self.inputs, started_ms=9, ended_ms=110)
                write(graph_path, evidence.canonical_bytes(graph))
                for start, end in ((14, 110), (9, 100)):
                    with self.subTest(start=start, end=end), self.assertRaises(evidence.ConformanceError):
                        sources.native_metadata_recovery_controls(run, self.inputs, started_ms=start, ended_ms=end)
                altered = evidence.load_json(retained[2])
                retained[2] = evidence.canonical_bytes(altered | {"inputFiles": {assembly: input_files[assembly]}})
                commands[1]["executionSha256"] = hashlib.sha256(retained[2]).hexdigest()
                write(graph_path, evidence.canonical_bytes(graph))
                with self.assertRaises(evidence.ConformanceError):
                    sources.native_metadata_recovery_controls(run, self.inputs, started_ms=9, ended_ms=110)

    def test_native_inspection_admission_rechecks_the_complete_source_and_command_graph(self):
        import conformance_case_catalog as catalog
        import conformance_sources as sources
        from types import SimpleNamespace
        from xml.sax.saxutils import escape

        self.category_history(mode="qualification")
        self.inputs["packages"][0]["packageId"] = "Hoard.Testing.Conformance"
        self.manifest["packages"][0]["id"] = "Hoard.Testing.Conformance"
        self.manifest["expected"][0]["packageId"] = "Hoard.Testing.Conformance"
        assembly_path = "candidate/Hoard.Architecture.Tests.dll"
        self.inputs["runtimeAssemblies"] = {assembly_path: "e" * 64}
        self.manifest["assemblies"][0]["path"] = assembly_path
        scope = "inspection-literals-sqlite"
        pairs = catalog.category_execution_partitions("metadata")[scope]
        expected = {identity: (binding, "none") for binding, identity in pairs}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            def write(path, data):
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    path.chmod(0o600)
                path.write_bytes(data)
                path.chmod(0o400)

            configuration = root / "stores/candidate.NuGet.Config"
            write(configuration, evidence.synthetic_nuget_configuration(root / "feed/candidate"))
            (root / "feed/candidate").mkdir(parents=True)
            configurations = {family: root / "stores" / (family + ".json") for family in ("metadata", "artifacts")}
            for path in configurations.values():
                write(path, b"{}")
            selected = {
                identity: {str(configurations[family]): hashlib.sha256(b"{}").hexdigest()}
                for identity, family in catalog.ORIGINAL_INSPECTION_WITNESSES.items()
                if identity not in catalog.ORIGINAL_INSPECTION_LITERAL_WITNESSES}
            self.inputs["configurationSha256"] = evidence.configuration_fingerprint(
                evidence.verify_synthetic_source_mapping(root, "stores/candidate.NuGet.Config", "feed/candidate"),
                inspection_inputs=selected)
            self.owner["rootPathSha256"] = hashlib.sha256(str(root).encode()).hexdigest()
            self.proof["ownerSha256"] = evidence.digest(self.owner)
            transport = self.category_transport("sqlite", identities=tuple(expected))
            options = {**transport, "inputs": self.inputs, "expected_tests": expected, "started_ms": 9, "ended_ms": 12}
            observed = evidence.inspect_runtime_attempt(**options)["observation"]
            with self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
                evidence.ingest_runtime_attempt(**options)
            manifest = evidence.load_json(transport["manifest_data"])
            write(root / "runtime-owner.json", transport["owner_data"])
            write(root / f"runtime-input-{self.attempt}.json", transport["manifest_data"])
            write(root / manifest["runInputsPath"], evidence.canonical_bytes(self.inputs))
            capture = root / "stores" / ("original-inspection-" + self.attempt)
            for identity in expected:
                write(capture / ("inspection-" + hashlib.sha256(identity.encode()).hexdigest() + ".json"),
                      evidence.canonical_bytes({
                          "schemaVersion": 1, "qualification": False, "runId": self.inputs["runId"],
                          "attemptId": self.attempt, "inputsSha256": evidence.digest(self.inputs),
                          "testIdentity": identity, "files": {}}))
            facts, _ = sources.inspection_observations(
                root, self.inputs, manifest, observed, {identity: {} for identity in expected},
                {identity: binding for binding, identity in pairs})
            receipt = {
                "schemaVersion": 1, "qualification": False, "mode": "category-metadata-" + scope,
                "runId": self.inputs["runId"], "invocationGroupId": self.inputs["invocationGroupId"],
                "attemptId": self.attempt, "inputsSha256": evidence.digest(self.inputs), "observations": facts}
            receipt_data = evidence.canonical_bytes(receipt)
            write(root / f'proofs/{receipt["mode"]}-{self.attempt}.json', receipt_data)
            context = root / "stores" / f"inspection-context-{self.attempt}.json"
            write(context, evidence.canonical_bytes({
                "schemaVersion": 1, "runId": self.inputs["runId"], "attemptId": self.attempt,
                "inputsSha256": evidence.digest(self.inputs), "outputDirectory": str(capture),
                "cases": {identity: {} for identity in expected}}))
            assembly = root / assembly_path
            settings = root / "stores" / f"settings-{self.attempt}.runsettings"
            environment = "<EnvironmentVariables><HOARD_INSPECTION_CONTEXT>" + escape(str(context)) + (
                "</HOARD_INSPECTION_CONTEXT></EnvironmentVariables>")
            settings_data = sources.runtime_settings(
                root, assembly, self.attempt, evidence.digest(manifest), evidence.digest(self.owner), environment)
            write(settings, settings_data)
            record = {
                "schemaVersion": 1, "sequence": 1, "childPid": 123, "childStartSha256": "a" * 64,
                "startedMs": 9, "endedMs": 12, "exitCode": 0, "diagnosticCode": "None",
                "groupState": "Exited", "scope": "ordinary", "runId": self.inputs["runId"],
                "rootId": self.owner["rootId"],
                "argvSha256": evidence.digest(sources.runtime_arguments(assembly, settings, tuple(expected))),
                "cwdSha256": hashlib.sha256(str(assembly.parent).encode()).hexdigest(),
                "inputFiles": {
                    f"runtime-input-{self.attempt}.json": evidence.digest(manifest),
                    "runtime-owner.json": evidence.digest(self.owner),
                    manifest["runInputsPath"]: evidence.digest(self.inputs),
                    settings.relative_to(root).as_posix(): hashlib.sha256(settings_data).hexdigest(),
                    assembly_path: "e" * 64,
                    context.relative_to(root).as_posix(): hashlib.sha256(context.read_bytes()).hexdigest()}}
            native_record = mock.Mock(return_value=evidence.canonical_bytes(record))
            write(root / "proofs/execution-command-0001.json", evidence.canonical_bytes(record))
            run = SimpleNamespace(
                root=root, run_id=self.inputs["runId"], root_id=self.owner["rootId"],
                command_sequence=7, read_execution_record=native_record, live_children=lambda: ())
            execution = {
                "schemaVersion": 1, "qualification": False, "nativeContainment": True,
                "runId": run.run_id, "rootId": run.root_id, "invocationGroupId": self.inputs["invocationGroupId"],
                "attemptId": self.attempt, "purpose": "execution", "commandSequence": 1,
                "inputsSha256": evidence.digest(self.inputs), "executionRecordSha256": evidence.digest(record),
                "manifestSha256": evidence.digest(manifest), "settingsSha256": hashlib.sha256(settings_data).hexdigest()}
            execution_path = root / f"proofs/category-command-{self.attempt}-execution.json"
            write(execution_path, evidence.canonical_bytes(execution))
            parent = {
                "schemaVersion": 1, "qualification": False, "nativeContainment": True,
                "profileId": "metadata", "scopeId": scope, "runId": run.run_id,
                "invocationGroupId": self.inputs["invocationGroupId"], "attemptId": self.attempt,
                "inputsSha256": evidence.digest(self.inputs), "manifestSha256": evidence.digest(manifest),
                "commandSequence": 1, "executionParentSha256": evidence.digest(execution),
                "sourceReceiptSha256": hashlib.sha256(receipt_data).hexdigest(),
                "observations": sorted(
                    ({**row, "bindingId": "sqlite", "caseId": catalog.category_runtime_cases(
                        "metadata", "sqlite")[row["testIdentity"]]} for row in facts),
                    key=lambda row: row["testIdentity"])}
            parent_path = root / f"proofs/category-source-{self.attempt}.json"
            write(parent_path, evidence.canonical_bytes(parent))
            with self.assertRaisesRegex(evidence.ConformanceError, "OwnershipInvalid"):
                sources.NativeCategorySources(run, inspection_inputs=selected, inspection_configurations=configurations)
            with mock.patch.object(sources, "OwnedRun", SimpleNamespace):
                native = sources.NativeCategorySources(
                    run, inspection_inputs=selected, inspection_configurations=configurations)
            selected.clear()
            configurations.clear()
            admitted = native.ingest_attempt(category_scope=("metadata", scope), **options)
            self.assertEqual(admitted["witnesses"], observed["witnesses"])
            self.assertEqual(set(admitted["sourceParents"].values()), {evidence.digest(parent)})
            for path, raw in admitted["sourceProofs"].items():
                self.assertEqual((root / path).read_bytes(), raw)
                self.assertEqual((root / path).stat().st_mode & 0o777, 0o400)
            history = evidence.CategoryRuntimeHistory(self.inputs, native_sources=native)
            with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
                history.begin("sqlite", self.attempt)
            results = history._case_results(
                "sqlite", "None", 12, admitted["witnesses"], admitted["sourceParents"])
            associated = [result for result in results.values() if result["attempts"][-1]["witnessIds"]]
            self.assertTrue(associated)
            self.assertTrue(all(evidence.digest(parent) in result["attempts"][-1]["proofSha256"]
                                for result in associated))
            native_record.assert_called_with(1)
            for change in ({"schemaVersion": True}, {"nativeContainment": False}, {"scopeId": "foreign"},
                           {"inputsSha256": "0" * 64}, {"commandSequence": 2}):
                write(parent_path, evidence.canonical_bytes({**parent, **change}))
                with self.subTest(change=change), self.assertRaises(evidence.ConformanceError):
                    native.ingest_attempt(category_scope=("metadata", scope), **options)
            changed_settings = settings_data.replace(b'enabled="False"', b'enabled="True"')
            write(settings, changed_settings)
            changed_execution = {**execution, "settingsSha256": hashlib.sha256(changed_settings).hexdigest()}
            write(execution_path, evidence.canonical_bytes(changed_execution))
            write(parent_path, evidence.canonical_bytes({**parent, "executionParentSha256": evidence.digest(changed_execution)}))
            with self.assertRaisesRegex(evidence.ConformanceError, "ProofMismatch"):
                native.ingest_attempt(category_scope=("metadata", scope), **options)
            write(settings, settings_data)
            for unrelated in ({"argvSha256": "0" * 64}, {"inputFiles": {
                    **record["inputFiles"], manifest["runInputsPath"]: "0" * 64}}):
                unrelated_record = {**record, **unrelated}
                native_record.return_value = evidence.canonical_bytes(unrelated_record)
                changed_execution = {**execution, "executionRecordSha256": evidence.digest(unrelated_record)}
                write(execution_path, evidence.canonical_bytes(changed_execution))
                write(parent_path, evidence.canonical_bytes({
                    **parent, "executionParentSha256": evidence.digest(changed_execution)}))
                with self.subTest(unrelated=unrelated), self.assertRaisesRegex(
                        evidence.ConformanceError, "OwnershipInvalid"):
                    native.ingest_attempt(category_scope=("metadata", scope), **options)

    def test_known_original_evidence_cannot_be_bypassed_by_selecting_no_provider_binding(self):
        baseline = copy.deepcopy((self.inputs, self.manifest, self.proof, self.witness, self.completion))
        identities = (
            "Hoard.Metadata.Tests.MetadataRoundTripTests."
            "MP01_Every_entity_round_trips_and_invalid_relationships_leave_no_changes",
            "Hoard.Architecture.Tests.MetadataBoundaryTests.Native_only_packages_cannot_hide_managed_assets",
            "Hoard.Artifacts.Tests.ArtifactCrashTests."
            'Real_parent_kill_and_fresh_process_reopen_preserve_exact_receipts_and_control_bytes(barrier: "B0")',
        )
        for identity in identities:
            with self.subTest(identity=identity):
                self.inputs, self.manifest, self.proof, self.witness, self.completion = copy.deepcopy(baseline)
                self.identity = identity
                self.manifest["expected"][0].update(
                    testIdentity=identity, fullyQualifiedName=identity.split("(")[0], bindingId="none")
                self.proof.update(testIdentity=identity, bindingId="none")
                self.witness.update(testIdentity=identity, bindingId="none")
                for mode in ("diagnostic", "qualification"):
                    self.inputs["mode"] = mode
                    input_sha = evidence.digest(self.inputs)
                    self.manifest["inputSha256"] = input_sha
                    manifest_sha = evidence.digest(self.manifest)
                    self.proof.update(inputSha256=input_sha, manifestSha256=manifest_sha)
                    self.witness.update(inputSha256=input_sha, proofSha256=evidence.digest(self.proof))
                    self.completion.update(inputSha256=input_sha, manifestSha256=manifest_sha)
                    options = {"expected_tests": {identity: ("none", "none")}}
                    if mode == "diagnostic":
                        self.assertEqual(self.ingest(**options)["diagnosticCode"], "None")
                    else:
                        with self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
                            self.ingest(**options)

    def test_category_import_requires_both_artifact_options_and_keeps_all_seven_qc_controls_incomplete(self):
        import conformance_case_catalog as catalog
        history = self.category_history(profile="artifacts")
        for binding in ("local", "object"):
            self.attempt = str(uuid.uuid4())
            with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
                history.begin(binding, self.attempt)
            with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
                history.finish(binding, **self.category_transport(binding))
        with self.assertRaisesRegex(evidence.ConformanceError, "EvidenceIncomplete"):
            history.results()
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin("none", str(uuid.uuid4()))
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            history.interrupt("none", "EvidenceIncomplete")
        results = history.results()
        self.assertEqual(len(results), len(catalog.expected_cases("artifacts")))
        self.assertEqual(sum(result["bindingId"] != "none" for result in results), 96)
        self.assertEqual(sum(result["status"] == "NotApplicable" for result in results), 4)
        self.assertEqual(sum(result["status"] == "Incomplete" for result in results), 7)
        self.assertTrue(all(result["status"] == "Passed" for result in results if result["bindingId"] == "local"))

    def test_category_import_checks_admitted_origins_and_rejects_reused_execution_ids_across_bindings(self):
        origin, assignments = self.runtime_origin("runtime")
        history = self.category_history(
            mode="diagnostic", origin_inputs={"sqlite": assignments, "memory": assignments})
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin("sqlite", self.attempt)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            results = history.finish("sqlite", **self.category_transport("sqlite", origin=origin))
        self.assertTrue(any(result["status"] == "Passed" for result in results))
        executions = {witness["executionId"] for witness in history.witnesses}
        self.assertEqual(set(history.session_origins), executions)
        self.assertTrue(all(len(origins) == 1 for origins in history.session_origins.values()))
        previous_proofs = dict(history.proofs)
        self.attempt = str(uuid.uuid4())
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin("memory", self.attempt)
        transport = self.category_transport("memory", origin=origin)
        witnesses = [evidence.load_json(line) for line in transport["witnesses_data"].splitlines()]
        first = witnesses[0]
        proof = evidence.load_json(transport["proofs"].pop(f'proof-{first["executionId"]}.json'))
        duplicate = next(iter(executions))
        proof["executionId"] = first["executionId"] = duplicate
        transport["proofs"][f"proof-{duplicate}.json"] = evidence.canonical_bytes(proof)
        first["proofSha256"] = evidence.digest(proof)
        transport["witnesses_data"] = b"".join(evidence.canonical_bytes(witness) + b"\n" for witness in witnesses)
        completion = evidence.load_json(transport["completion_data"])
        completion["recordsSha256"] = hashlib.sha256(transport["witnesses_data"]).hexdigest()
        transport["completion_data"] = evidence.canonical_bytes(completion)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012), self.assertRaisesRegex(
                evidence.ConformanceError, "ProofMismatch"):
            history.finish("memory", **transport)
        self.assertEqual({witness["executionId"] for witness in history.witnesses}, executions)
        self.assertEqual(dict(history.proofs), previous_proofs)

    def test_case_execution_preserves_failed_attempt_and_proofs_after_a_passing_retry(self):
        history = self.history(max_attempts=2)
        self.assertEqual(history.state, "Expected")
        self.proof.update(status="Failed", failureKind="Assertion",
                          assertionSymbol=self.manifest["expected"][0]["assertionSymbol"])
        self.witness.update(status="Failed", proofSha256=evidence.digest(self.proof))
        self.completion["diagnosticCode"] = "AssertionFailed"
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin(self.attempt)
        self.assertEqual(history.state, "Running")
        with self.assertRaises(evidence.ConformanceError):
            history.result()
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            self.finish_history(history)
        first = history.result()
        self.assertEqual(history.state, "Failed")
        self.attempt, self.execution = str(uuid.uuid4()), str(uuid.uuid4())
        self.manifest.update(attemptId=self.attempt, attemptSequence=2)
        self.proof.update(attemptId=self.attempt, attemptSequence=2, executionId=self.execution,
                          status="Passed", failureKind="None", assertionSymbol=None,
                          manifestSha256=evidence.digest(self.manifest))
        self.witness.update(executionId=self.execution, status="Passed", startedMs=21, endedMs=22,
                            proofSha256=evidence.digest(self.proof))
        self.completion.update(attemptId=self.attempt, attemptSequence=2,
                               diagnosticCode="None", manifestSha256=evidence.digest(self.manifest))
        with mock.patch.object(evidence.time, "monotonic", return_value=0.020):
            history.begin(self.attempt)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.023):
            self.finish_history(history)
        result = history.result()
        self.assertEqual(history.state, "Passed")
        self.assertEqual(tuple(attempt["status"] for attempt in result["attempts"]), ("Failed", "Passed"))
        self.assertTrue(set(first["proofSha256"]) < set(result["proofSha256"]))
        self.assertEqual(result["attempts"][0], first["attempts"][0])
        self.assertEqual(len(history.witnesses), 2)
        self.assertEqual({witness["executionId"] for witness in history.witnesses},
                         {execution for attempt in result["attempts"] for execution in attempt["witnessIds"]})
        self.assertEqual(set(history.proofs.values()), set(result["proofSha256"]))
        with self.assertRaises(TypeError):
            result["attempts"][0]["status"] = "Passed"
        with self.assertRaises(TypeError):
            history.proofs["invented"] = "a" * 64
        with self.assertRaises(evidence.ConformanceError):
            history.begin(str(uuid.uuid4()))

    def test_case_execution_rejects_overlap_and_closes_invalid_provenance_without_inventing_witnesses(self):
        history = self.history()
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin(self.attempt)
            with self.assertRaises(evidence.ConformanceError):
                history.begin(str(uuid.uuid4()))
        self.proof["attemptId"] = str(uuid.uuid4())
        self.witness["proofSha256"] = evidence.digest(self.proof)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012), \
                self.assertRaises(evidence.ConformanceError):
            self.finish_history(history)
        result = history.result()
        self.assertEqual(history.state, "Failed")
        self.assertEqual(result["attempts"][0]["witnessIds"], ())
        self.assertEqual(result["attempts"][0]["proofSha256"], ())
        self.assertEqual(result["attempts"][0]["diagnosticCode"], "ProofMismatch")
        with self.assertRaises(evidence.ConformanceError):
            history.begin(str(uuid.uuid4()))

    def test_case_execution_cannot_replay_a_session_origin_under_a_fresh_attempt_and_execution(self):
        origin, assignments = self.runtime_origin("CP-01")
        self.proof["sessionOrigins"] = [origin]
        history = self.history(max_attempts=3, origin_inputs={"sqlite": assignments})
        assignments["store"] = ("missing.dll", None)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin(self.attempt)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            self.finish_history(history)
        first_execution = self.execution
        self.attempt, self.execution = str(uuid.uuid4()), str(uuid.uuid4())
        self.manifest.update(attemptId=self.attempt, attemptSequence=2)
        self.proof.update(attemptId=self.attempt, attemptSequence=2, executionId=self.execution,
                          manifestSha256=evidence.digest(self.manifest))
        self.witness.update(executionId=self.execution, startedMs=21, endedMs=22,
                            proofSha256=evidence.digest(self.proof))
        self.completion.update(attemptId=self.attempt, attemptSequence=2, manifestSha256=evidence.digest(self.manifest))
        with mock.patch.object(evidence.time, "monotonic", return_value=0.020):
            history.begin(self.attempt)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.023), \
                self.assertRaisesRegex(evidence.ConformanceError, "ProofMismatch"):
            self.finish_history(history)
        self.assertEqual(history.state, "Failed")
        self.assertEqual(set(history.session_origins), {first_execution})
        self.assertEqual(history.session_origins[first_execution][0]["sessionId"], origin["sessionId"])
        self.assertEqual(history.result()["attempts"][1]["witnessIds"], ())
        self.attempt, self.execution = str(uuid.uuid4()), str(uuid.uuid4())
        self.manifest.update(attemptId=self.attempt, attemptSequence=3)
        self.proof["sessionOrigins"][0]["sessionId"] = str(uuid.uuid4())
        self.proof["sessionOrigins"][0]["components"]["store"]["typeSha256"] = "0" * 64
        self.proof.update(attemptId=self.attempt, attemptSequence=3, executionId=self.execution,
                          manifestSha256=evidence.digest(self.manifest))
        self.witness.update(executionId=self.execution, startedMs=31, endedMs=32,
                            proofSha256=evidence.digest(self.proof))
        self.completion.update(attemptId=self.attempt, attemptSequence=3, manifestSha256=evidence.digest(self.manifest))
        with mock.patch.object(evidence.time, "monotonic", return_value=0.030):
            history.begin(self.attempt)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.033), \
                self.assertRaisesRegex(evidence.ConformanceError, "ProofMismatch"):
            self.finish_history(history)
        self.assertEqual(history.result()["attempts"][2]["witnessIds"], ())

    def test_case_execution_interruption_and_catalog_exclusion_never_invent_runtime_proofs(self):
        history = self.history()
        with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
            history.begin(self.attempt)
        with mock.patch.object(evidence.time, "monotonic", return_value=0.012):
            result = history.interrupt("DeadlineExceeded")
        self.assertEqual(history.state, "Incomplete")
        self.assertEqual(result["attempts"][0]["witnessIds"], ())
        self.assertEqual(result["proofSha256"], ())
        with self.assertRaises(evidence.ConformanceError):
            history.begin(str(uuid.uuid4()))
        inputs = ConformanceAdmissionTests().inputs()
        inputs["bindings"].append({**inputs["bindings"][0], "bindingId": "memory"})
        excluded = evidence.RuntimeCaseHistory(inputs, binding_id="memory", matrix_id="none", case_id="MP-36")
        self.assertEqual(excluded.state, "NotApplicable")
        self.assertEqual(excluded.result()["attempts"], ())
        self.assertEqual(excluded.result()["exclusionRule"], "non-durable-fixture")
        with self.assertRaises(evidence.ConformanceError):
            excluded.begin(str(uuid.uuid4()))
        for matrix, case in (("unknown", "MP-36"), ("none", "MP-99")):
            with self.subTest(matrix=matrix, case=case), self.assertRaises(evidence.ConformanceError):
                evidence.RuntimeCaseHistory(inputs, binding_id="memory", matrix_id=matrix, case_id=case)

    def test_safe_logger_records_require_exact_manifest_proof_and_completion_links(self):
        admitted = self.ingest()
        self.assertEqual(admitted["attemptId"], self.attempt)
        self.assertEqual(admitted["witnesses"][0]["executionId"], self.execution)
        self.assertEqual(admitted["diagnosticCode"], "None")
        with self.assertRaises(TypeError):
            admitted["completion"]["complete"] = False
        with self.assertRaises(TypeError):
            admitted["proofs"]["invented"] = "a" * 64

    def discovery(self, **overrides):
        self.manifest["purpose"] = "discovery"
        self.completion.update(purpose="discovery", manifestSha256=evidence.digest(self.manifest))
        record = {
            "schemaVersion": 1, "runId": self.inputs["runId"],
            "invocationGroupId": self.inputs["invocationGroupId"],
            "attemptId": self.attempt, "attemptSequence": 1, "inputSha256": evidence.digest(self.inputs),
            "manifestSha256": evidence.digest(self.manifest), "ownerSha256": evidence.digest(self.owner),
            "testIdentity": self.identity, "fullyQualifiedName": self.manifest["expected"][0]["fullyQualifiedName"],
            "assemblySha256": "e" * 64, "discoveredMs": 10,
        }
        options = {
            "inputs": self.inputs, "manifest_data": evidence.canonical_bytes(self.manifest),
            "owner_data": evidence.canonical_bytes(self.owner),
            "discoveries_data": evidence.canonical_bytes(record) + b"\n",
            "completion_data": evidence.canonical_bytes({
                **self.completion, "recordsSha256": hashlib.sha256(
                    evidence.canonical_bytes(record) + b"\n").hexdigest()}),
            "expected_tests": {self.identity: ("sqlite", "none")},
            "manifest_sha256": evidence.digest(self.manifest), "owner_sha256": evidence.digest(self.owner),
            "started_ms": 9, "ended_ms": 12,
        }
        options.update(overrides)
        return evidence.ingest_runtime_discovery(**options)

    def test_actual_discovery_is_exact_immutable_and_not_an_execution_witness(self):
        captured = self.discovery()
        self.assertEqual(captured["discoveries"][0]["testIdentity"], self.identity)
        self.assertNotIn("witnesses", captured)
        self.assertNotIn("executionId", captured["discoveries"][0])
        with self.assertRaises(TypeError):
            captured["discoveries"][0]["testIdentity"] = "changed"
        with self.assertRaises(evidence.ConformanceError):
            self.ingest()

    def test_discovery_cannot_borrow_totals_parameter_source_or_other_invocation_provenance(self):
        captured = self.discovery()
        record = dict(captured["discoveries"][0])
        for key, value in (("testIdentity", self.identity.replace("1)", "2)")),
                           ("fullyQualifiedName", "Foreign.Check"), ("assemblySha256", "1" * 64),
                           ("attemptId", str(uuid.uuid4())), ("inputSha256", "1" * 64),
                           ("ownerSha256", "1" * 64), ("manifestSha256", "1" * 64),
                           ("discoveredMs", 11), ("discoveredMs", 13),
                           ("executionId", str(uuid.uuid4()))):
            with self.subTest(field=key), self.assertRaises(evidence.ConformanceError):
                self.discovery(discoveries_data=evidence.canonical_bytes({**record, key: value}) + b"\n")
        for records in (b"", evidence.canonical_bytes(record) + b"\n" + evidence.canonical_bytes(record) + b"\n"):
            with self.subTest(records=len(records)), self.assertRaises(evidence.ConformanceError):
                self.discovery(discoveries_data=records)

    def test_loaded_assembly_requires_exact_admitted_runtime_and_selected_package_bytes(self):
        self.inputs["runtimeAssemblies"]["provider/Hoard.Fixture.dll"] = "d" * 64
        observed = {
            "assemblyName": "Hoard.Fixture", "assemblyVersion": "0.1.0.0",
            "moduleVersionId": str(uuid.uuid4()), "assemblySha256": "d" * 64,
            "typeSha256": "f" * 64,
        }
        captured = evidence.ingest_loaded_assembly(
            self.inputs, evidence.canonical_bytes(observed),
            runtime_path="provider/Hoard.Fixture.dll", package_id="Hoard.Fixture")
        self.assertEqual(captured["assemblySha256"], "d" * 64)
        with self.assertRaises(TypeError):
            captured["assemblySha256"] = "e" * 64
        for key, value in (("assemblySha256", "e" * 64), ("moduleVersionId", str(uuid.UUID(int=0))),
                           ("assemblyVersion", "0.1.0"), ("assemblyVersion", "0.1.0.65536"),
                           ("assemblyName", "/private/canary"), ("path", "/private/canary")):
            with self.subTest(field=key), self.assertRaises(evidence.ConformanceError):
                evidence.ingest_loaded_assembly(
                    self.inputs, evidence.canonical_bytes({**observed, key: value}),
                    runtime_path="provider/Hoard.Fixture.dll", package_id="Hoard.Fixture")

    def test_loaded_assembly_cannot_borrow_a_package_label_for_an_unpacked_runtime_artifact(self):
        observed = {
            "assemblyName": "Hoard.Tests", "assemblyVersion": "0.1.0.0",
            "moduleVersionId": str(uuid.uuid4()), "assemblySha256": "e" * 64,
            "typeSha256": "f" * 64,
        }
        data = evidence.canonical_bytes(observed)
        self.assertEqual(evidence.ingest_loaded_assembly(
            self.inputs, data, runtime_path="consumer/Hoard.Tests.dll",
            package_id=None)["assemblySha256"], "e" * 64)
        for package_id, runtime_path in (
                ("Hoard.Fixture", "consumer/Hoard.Tests.dll"), ("Hoard.Missing", "consumer/Hoard.Tests.dll"),
                (None, "consumer/Missing.dll"), (None, "../Hoard.Tests.dll")):
            with self.subTest(package=package_id, path=runtime_path), self.assertRaises(evidence.ConformanceError):
                evidence.ingest_loaded_assembly(self.inputs, data, runtime_path=runtime_path, package_id=package_id)

    def session_origin(self):
        self.inputs["runtimeAssemblies"]["provider/Hoard.Fixture.dll"] = "d" * 64
        roles = ("authority", "factory", "faults", "schema", "session", "store")
        assembly = {
            "assemblyName": "Hoard.Fixture", "assemblyVersion": "0.1.0.0",
            "moduleVersionId": str(uuid.uuid4()), "assemblySha256": "d" * 64, "typeSha256": "f" * 64,
        }
        origin = {
            "schemaVersion": 1, "runId": self.inputs["runId"], "caseId": "MT-01",
            "sessionId": str(uuid.uuid4()), "parentSessionId": None, "factoryOperation": "create",
            "descriptorSha256": "a" * 64, "runtimeVersion": self.inputs["environment"]["runtime"],
            "processArchitecture": "x64",
            "components": {role: {"instanceId": str(uuid.uuid4()), "assembly": dict(assembly)} for role in roles},
        }
        assignments = {role: ("provider/Hoard.Fixture.dll", "Hoard.Fixture") for role in roles}
        origin["components"]["factory"]["assembly"].update(assemblyName="Hoard.Tests", assemblySha256="e" * 64)
        assignments["factory"] = ("consumer/Hoard.Tests.dll", None)
        return origin, assignments

    def ingest_origin(self, origin, assignments, **overrides):
        options = dict(binding_id="sqlite", case_id="MT-01", component_inputs=assignments, parent_session_id=None)
        options.update(overrides)
        return evidence.ingest_session_origin(self.inputs, evidence.canonical_bytes(origin), **options)

    def runtime_origin(self, case_id):
        origin, assignments = self.session_origin()
        origin["caseId"] = case_id
        origin["components"] = {role: {
            "instanceId": component["instanceId"], "assemblySha256": component["assembly"]["assemblySha256"],
            "moduleVersionId": component["assembly"]["moduleVersionId"], "typeSha256": component["assembly"]["typeSha256"],
        } for role, component in origin["components"].items()}
        return origin, assignments

    def test_runtime_origin_proof_requires_independent_role_assignments_and_exact_execution_case(self):
        self.inputs["mode"] = "qualification"
        origin, assignments = self.runtime_origin("runtime")
        self.proof.update(sessionOrigins=[origin], inputSha256=evidence.digest(self.inputs))
        self.manifest["inputSha256"] = self.completion["inputSha256"] = evidence.digest(self.inputs)
        self.proof["manifestSha256"] = self.completion["manifestSha256"] = evidence.digest(self.manifest)
        self.witness.update(inputSha256=evidence.digest(self.inputs), proofSha256=evidence.digest(self.proof))
        with self.assertRaisesRegex(evidence.ConformanceError, "EvidenceIncomplete"):
            self.ingest()
        admitted = self.ingest(origin_inputs={"sqlite": assignments})
        self.assertEqual(admitted["sessionOrigins"][self.execution][0]["sessionId"], origin["sessionId"])
        def admit_changed(proof):
            data = evidence.canonical_bytes(proof)
            witness = {**self.witness, "proofSha256": hashlib.sha256(data).hexdigest()}
            lines = evidence.canonical_bytes(witness) + b"\n"
            return self.ingest(origin_inputs={"sqlite": assignments},
                               proofs={f"proof-{self.execution}.json": data}, witnesses_data=lines,
                               completion_data=evidence.canonical_bytes({
                                   **self.completion, "recordsSha256": hashlib.sha256(lines).hexdigest()}))
        lineage = json.loads(evidence.canonical_bytes(self.proof))
        reopened = json.loads(evidence.canonical_bytes(origin))
        reopened.update(sessionId=str(uuid.uuid4()), parentSessionId=origin["sessionId"], factoryOperation="reopen")
        lineage["sessionOrigins"].append(reopened)
        self.assertEqual(len(admit_changed(lineage)["sessionOrigins"][self.execution]), 2)
        for mutation in ("case", "runtime", "type", "descriptor", "missing", "replay", "absent",
                         "parent", "factory", "instance"):
            changed = json.loads(evidence.canonical_bytes(self.proof))
            captured = changed["sessionOrigins"][0]
            if mutation == "case":
                captured["caseId"] = "foreign"
            elif mutation == "runtime":
                captured["runtimeVersion"] = "10.0.8"
            elif mutation == "type":
                captured["components"]["factory"]["instanceId"] = captured["components"]["store"]["instanceId"]
            elif mutation == "descriptor":
                captured["descriptorSha256"] = "b" * 64
            elif mutation == "missing":
                del captured["components"]["store"]
            elif mutation == "absent":
                changed["sessionOrigins"] = []
            elif mutation in ("parent", "factory", "instance"):
                child = json.loads(evidence.canonical_bytes(reopened))
                if mutation == "parent":
                    child["parentSessionId"] = str(uuid.uuid4())
                elif mutation == "factory":
                    child["components"]["factory"]["instanceId"] = str(uuid.uuid4())
                else:
                    child["components"]["store"]["typeSha256"] = "0" * 64
                changed["sessionOrigins"].append(child)
            else:
                changed["sessionOrigins"].append(captured)
            with self.subTest(mutation=mutation), self.assertRaises(evidence.ConformanceError):
                admit_changed(changed)

    def test_session_origin_matches_independent_role_bytes_environment_and_reopen_lineage(self):
        origin, assignments = self.session_origin()
        admitted = self.ingest_origin(origin, assignments)
        self.assertEqual(admitted["components"]["store"]["assembly"]["assemblySha256"], "d" * 64)
        with self.assertRaises(TypeError):
            admitted["components"]["store"]["instanceId"] = str(uuid.uuid4())
        parent = origin["sessionId"]
        origin.update(sessionId=str(uuid.uuid4()), parentSessionId=parent, factoryOperation="reopen")
        self.assertEqual(self.ingest_origin(origin, assignments, parent_session_id=parent)["parentSessionId"], parent)
        with self.assertRaises(evidence.ConformanceError):
            self.ingest_origin(origin, assignments)
        origin, assignments = self.session_origin()
        self.inputs["bindings"][0]["category"] = "artifacts"
        del origin["components"]["schema"]
        del assignments["schema"]
        for role in ("validator", "maintenance", "lifetime"):
            origin["components"][role] = origin["components"]["store"]
            assignments[role] = assignments["store"]
        self.assertEqual(len(self.ingest_origin(origin, assignments)["components"]), 8)

    def test_session_origin_cannot_borrow_factory_package_labels_or_changed_runtime_or_component_identity(self):
        for mutation in ("descriptor", "run", "case", "runtime", "architecture", "package", "missing",
                         "extra", "instance", "parent", "raw"):
            origin, assignments = self.session_origin()
            if mutation == "descriptor":
                origin["descriptorSha256"] = "b" * 64
            elif mutation == "run":
                origin["runId"] = str(uuid.uuid4())
            elif mutation == "case":
                origin["caseId"] = "MT-02"
            elif mutation == "runtime":
                origin["runtimeVersion"] = "10.0.8"
            elif mutation == "architecture":
                origin["processArchitecture"] = "arm64"
            elif mutation == "package":
                assignments["factory"] = ("consumer/Hoard.Tests.dll", "Hoard.Fixture")
            elif mutation == "missing":
                del origin["components"]["store"]
            elif mutation == "extra":
                origin["components"]["private-canary"] = origin["components"]["store"]
            elif mutation == "instance":
                origin["components"]["factory"]["instanceId"] = origin["components"]["store"]["instanceId"]
            elif mutation == "parent":
                origin.update(parentSessionId=origin["sessionId"], factoryOperation="reopen")
            else:
                origin["privatePath"] = "/private/canary"
            with self.subTest(mutation=mutation), self.assertRaises(evidence.ConformanceError):
                self.ingest_origin(origin, assignments)

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

    def test_enum_parameters_are_bounded_identifiers_and_still_require_exact_parent_expectations(self):
        for parameter in ("Metadata", "Artifacts", "A" * 128, "A" * 129,
                          "Metadata Artifacts", "../Metadata", "Metadata-Artifact"):
            self.setUp()
            self.identity = f"Hoard.Testing.Conformance.Runtime.Check(category: {parameter})"
            self.manifest["expected"][0]["testIdentity"] = self.identity
            self.witness["testIdentity"] = self.proof["testIdentity"] = self.identity
            self.completion["manifestSha256"] = self.proof["manifestSha256"] = evidence.digest(self.manifest)
            self.witness["proofSha256"] = evidence.digest(self.proof)
            with self.subTest(parameter=parameter):
                if parameter in ("Metadata", "Artifacts", "A" * 128):
                    self.assertEqual(self.ingest()["witnesses"][0]["testIdentity"], self.identity)
                    unexpected = self.identity.replace(parameter, "Unselected")
                    self.witness["testIdentity"] = self.proof["testIdentity"] = unexpected
                    self.witness["proofSha256"] = evidence.digest(self.proof)
                    with self.assertRaises(evidence.ConformanceError):
                        self.ingest()
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
        result = self.ingest(witnesses_data=b"", proofs={}, completion_data=evidence.canonical_bytes({
            **self.completion, "recordsSha256": hashlib.sha256(b"").hexdigest()}))
        self.assertEqual(result["witnesses"], ())
        self.assertEqual(result["diagnosticCode"], "EvidenceIncomplete")

    def test_manifest_is_independent_of_runtime_and_bound_to_admitted_artifact_bytes(self):
        for dimension, value in (
                ("assemblies", [{"id": "tests", "path": "foreign.dll", "sha256": "e" * 64}]),
                ("packages", [{"id": "Hoard.Foreign", "path": "feed/foreign.nupkg", "sha256": "b" * 64}]),
                ("expected", []), ("purpose", "unknown"), ("purpose", None), ("unknown", True)):
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
    def test_package_acceptance_lock_derivation_preserves_ordinary_lock_and_closed_paths(self):
        import conformance_lock_preparation as preparation
        source = self.root / "stores/registration"
        project = source / "retained/Consumer.csproj"
        ordinary = project.parent / "packages.lock.json"
        ordinary.write_bytes(b"ordinary-lock-sentinel")
        before = ordinary.read_bytes()
        original = project.parent / "PackageAcceptance/packages.lock.json"
        original.parent.mkdir()
        original.write_bytes(evidence.canonical_bytes({"version": 1, "dependencies": {"net10.0": {
            "Hoard.Example": {"resolved": "0.1.0", "contentHash": "original"},
            "External.Dependency": {"resolved": "1.0.0", "contentHash": "untouched"}}}}))
        acceptance_before = original.read_bytes()
        prepared, record = preparation.prepare_project_lock(
            project, source, self.root / "feed/registration", "registration", acceptance=True)
        self.assertEqual(ordinary.read_bytes(), before)
        self.assertEqual(original.read_bytes(), acceptance_before)
        self.assertEqual(record["originalLock"], "retained/PackageAcceptance/packages.lock.json")
        self.assertEqual(prepared.name, "F07.preparation.acceptance.packages.lock.json")
        preparation.verify_project_lock(record, source, self.root / "feed/registration")
        for changed in (record | {"originalLock": "retained/packages.lock.json"},
                        record | {"preparedLock": "retained/obj/F07.preparation.packages.lock.json"}):
            with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
                preparation.verify_project_lock(changed, source, self.root / "feed/registration")

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
