import contextlib
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
    def test_hook_quality_requires_both_exact_native_binding_rows(self):
        import conformance_case_catalog as catalog
        for profile in ("metadata", "artifacts"):
            expected = catalog.hook_admission_tests(profile)
            case, = (case for case in catalog.expected_cases(profile) if case.case_id == "QC-05")
            with self.subTest(profile=profile):
                self.assertEqual(set(case.witnesses), set(expected))
                self.assertNotIn("hook-admission", catalog.category_execution_partitions(profile))
                scopes = catalog.category_execution_partitions(profile, mode="qualification")
                self.assertEqual(set(scopes["hook-admission"]), {
                    (binding, identity) for identity, (binding, _) in expected.items()})
                for identity, (binding, case_id) in expected.items():
                    self.assertEqual(catalog.category_runtime_cases(
                        profile, binding, mode="qualification")[identity], case_id)
                    self.assertNotIn(identity, catalog.category_runtime_cases(profile, binding))

    def test_qualified_mutation_scope_selects_only_complete_corrected_family_with_fresh_source_policy(self):
        import conformance_case_catalog as catalog
        prefix = "Hoard.Conformance.Tests.CategoryMutationTests."
        for profile, providers, method in (
                ("metadata", ("memory", "sqlite"), "Corrected_metadata_replay_passes"),
                ("artifacts", ("local", "object"), "Corrected_artifact_staging_passes")):
            expected = {prefix + method + f'(provider: "{provider}")' for provider in providers}
            quality, = (case for case in catalog.expected_cases(profile) if case.case_id == "QC-04")
            with self.subTest(profile=profile):
                self.assertEqual(set(quality.witnesses), expected)
                diagnostic = catalog.category_execution_partitions(profile)
                self.assertFalse(any(identity in expected for pairs in diagnostic.values() for _, identity in pairs))
                qualified = catalog.category_execution_partitions(profile, mode="qualification")
                self.assertEqual(set(qualified["mutation-repair"]), {
                    (provider, prefix + method + f'(provider: "{provider}")') for provider in providers})
                for provider in providers:
                    identity = prefix + method + f'(provider: "{provider}")'
                    self.assertEqual(catalog.category_runtime_cases(profile, provider, mode="qualification")[identity],
                                     "QC-04")
                    self.assertEqual(catalog.original_non_session_policy(identity), (profile, "mutation"))
                    self.assertIsNone(catalog.original_witness_policy(identity))

    def test_authority_quality_catalog_requires_all_actual_composition_parameters(self):
        import conformance_case_catalog as catalog
        method = "Hoard.Conformance.Tests.AuthorityIntegrationTests.Actual_compositions_preserve_shared_authority"
        expected = {
            f'{method}(provider: "{provider}", metadataProvider: "{metadata}", consumer: "{consumer}")'
            for provider in ("local", "object") for metadata in ("memory", "sqlite") for consumer in (
                "reference-admission", "failed-transaction", "live-references", "lost-acknowledgment",
                "incarnation", "reader", "foreign-authority", "shutdown")}
        case, = (case for case in catalog.expected_cases("artifacts") if case.case_id == "QC-12")
        self.assertEqual(set(case.witnesses), expected)
        self.assertEqual(len(case.witnesses), 32)
        source = (ROOT / "tests/contracts/Hoard.Conformance.Tests/AuthorityIntegrationTests.cs").read_text()
        rows = source.split("public static IEnumerable<object[]> Rows()")[1].split("[Theory]")[0]
        dimensions = {
            name: tuple(re.findall(r'"([^"]+)"', values))
            for name, values in re.findall(r"foreach \(var (\w+) in new\[\] \{([^}]+)\}", rows)}
        actual = tuple(
            f'{method}(provider: "{provider}", metadataProvider: "{metadata}", consumer: "{consumer}")'
            for provider in dimensions["provider"] for metadata in dimensions["metadata"]
            for consumer in dimensions["consumer"])
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(expected))
        self.assertEqual(catalog.category_runtime_cases("artifacts", "none", mode="qualification"), {})

    def test_authority_qualification_has_its_own_complete_observed_composition_scope(self):
        import conformance_case_catalog as catalog
        expected = set(catalog.authority_integration_witnesses())
        scopes = catalog.category_execution_partitions("artifacts", mode="qualification")
        self.assertTrue("original-integration" in scopes)
        rows = scopes["original-integration"]
        self.assertEqual({identity for _, identity in rows}, expected)
        self.assertEqual(len(rows), 32)
        for binding, identity in rows:
            self.assertEqual(catalog.original_witness_policy(identity),
                             ("artifacts", "loaded-contract", ("contract",)))
            self.assertEqual(catalog.original_witness_parents(identity), (None, None, None))
            self.assertEqual(catalog.category_runtime_cases(
                "artifacts", binding, mode="qualification")[identity], "QC-12")
        self.assertNotIn("original-integration", catalog.category_execution_partitions("artifacts"))
        for binding in ("local", "object"):
            self.assertFalse(expected & catalog.category_runtime_cases("artifacts", binding).keys())

    def test_category_qualification_selects_source_facts_only_for_actual_provider_bindings(self):
        import conformance_case_catalog as catalog
        for profile in ("metadata", "artifacts"):
            self.assertEqual({}, dict(catalog.category_runtime_cases(profile, "none", mode="qualification")))
        for binding, identity in catalog.METADATA_INVENTORY_SOURCE_WITNESSES.items():
            selected = catalog.category_runtime_cases("metadata", binding, mode="qualification")
            self.assertEqual("MP-48", selected[identity])
            self.assertEqual(binding == "sqlite", catalog.METADATA_RECOVERY_SOURCE_WITNESS in selected)

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
    def test_native_artifact_controller_joins_original_children_transfers_packets_and_explicit_execution(self):
        import conformance_sources as sources
        from conformance_case_catalog import ORIGINAL_ARTIFACT_PROOF_SOURCES
        self.assertTrue(callable(getattr(sources, "native_artifact_controller_source", None)),
                        "Artifact controller authority must reconstruct its original complete source graph independently.")
        inputs = evidence.admit_entity("RunInputs", {**self.inputs, "profileId": "artifacts", "mode": "qualification"})
        attempt = str(uuid.uuid4())
        manifest = {"attemptId": attempt, "runId": inputs["runId"],
                    "invocationGroupId": inputs["invocationGroupId"], "inputSha256": evidence.digest(inputs),
                    "expected": [{"testIdentity": identity, "bindingId": provider}
                                 for identity, (_, provider, _) in ORIGINAL_ARTIFACT_PROOF_SOURCES.items()]}
        witnesses = [{
            "testIdentity": identity, "bindingId": provider, "executionId": str(uuid.uuid4()),
            "proofSha256": hashlib.sha256(identity.encode()).hexdigest(), "status": "Passed"}
            for identity, (_, provider, _) in ORIGINAL_ARTIFACT_PROOF_SOURCES.items()]
        observed = {"attemptId": attempt, "diagnosticCode": "None", "witnesses": witnesses,
                    "proofs": {f'proof-{row["executionId"]}.json': row["proofSha256"] for row in witnesses}}
        captures = [{**{key: row[key] for key in ("testIdentity", "executionId")},
                     "runtimeProofSha256": row["proofSha256"], "sourceProofSha256": "a" * 64} for row in witnesses]
        packets = {f"proofs/source-artifact-{attempt}-{index}.json": f"original-packet-{index}".encode()
                   for index in range(16)}
        proofs, transfers, children = {}, [], {}
        for identity, (kind, provider, parameter) in ORIGINAL_ARTIFACT_PROOF_SOURCES.items():
            if kind != "transfer":
                children[identity] = {"producer": hashlib.sha256(identity.encode()).hexdigest()}
                if kind == "crash":
                    children[identity]["state"] = "b" * 64
                continue
            sequence = len(transfers) + 1
            prefix = f"proofs/qualification-artifact-transfers/transfer-{provider}-{parameter}"
            control = evidence.canonical_bytes({"childStartSha256": "c" * 64})
            producer, composite = f"original-producer-{sequence}".encode(), f"original-composite-{sequence}".encode()
            proofs.update({
                prefix + "/native-execution.json": evidence.canonical_bytes({"sequence": sequence}),
                prefix + "-native-inputs.json": evidence.canonical_bytes(inputs),
                f"proofs/transfer-command-{sequence:04}.json": control,
                f"proofs/execution-command-{sequence:04}.json": f"original-execution-{sequence}".encode(),
                prefix + "/producer.json": producer, prefix + "/proof.json": composite})
            transfers.append({
                "provider": provider, "size": parameter, "controllerSha256": hashlib.sha256(control).hexdigest(),
                "producerSha256": hashlib.sha256(producer).hexdigest(),
                "proofSha256": hashlib.sha256(composite).hexdigest(), "childStartSha256": "c" * 64})
        transfers.sort(key=lambda row: (row["provider"] != "local", row["size"]))
        summary = evidence.canonical_bytes({
            "qualification": False, "mode": "artifact-transfers", "code": "None",
            "inputsSha256": evidence.digest(inputs), "transfers": transfers})
        seal = b"original-held-output-index"
        consumption = evidence.canonical_bytes({
            "schemaVersion": 1, "qualification": False, "runId": inputs["runId"],
            "invocationGroupId": inputs["invocationGroupId"], "attemptId": attempt,
            "inputsSha256": evidence.digest(inputs), "observations": captures,
            "outputSealSha256": hashlib.sha256(seal).hexdigest()})
        by_identity = {row["testIdentity"]: row for row in witnesses}
        observations = []
        for identity, (kind, provider, parameter) in sorted(ORIGINAL_ARTIFACT_PROOF_SOURCES.items()):
            row = by_identity[identity]
            hashes = children[identity] if kind != "transfer" else {"producer": next(
                item["proofSha256"] for item in transfers if (item["provider"], item["size"]) == (provider, parameter))}
            observations.append({"testIdentity": identity, "executionId": row["executionId"],
                                 "runtimeProofSha256": row["proofSha256"], "sourceProofs": hashes})
        receipt = evidence.canonical_bytes({
            "schemaVersion": 1, "qualification": False, "mode": "original-artifact-proofs",
            "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"], "attemptId": attempt,
            "inputsSha256": evidence.digest(inputs), "transferParentSha256": hashlib.sha256(summary).hexdigest(),
            "observations": observations, "consumptionSha256": hashlib.sha256(consumption).hexdigest()})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "proofs").mkdir()
            run = object.__new__(sources.OwnedRun)
            run.root, run.run_id, run.command_sequence = root, inputs["runId"], 99
            for defect in (None, "summary", "consumption", "receipt", "runtime-proof", "late-controller",
                           "transfer-failure", "children-failure", "seal-failure"):
                originals = {
                    "proofs/qualification-artifact-transfers.json": summary,
                    f"proofs/artifact-source-capture-{attempt}.json": consumption,
                    f"proofs/original-artifact-external-{attempt}.json": receipt}
                for name, raw in originals.items():
                    path = root / name
                    if path.exists():
                        path.chmod(0o600)
                    path.write_bytes(raw + (b" " if defect == "summary" and name.endswith("transfers.json")
                                           or defect == "consumption" and "/artifact-source-capture-" in name
                                           or defect == "receipt" and "/original-artifact-external-" in name else b""))
                    path.chmod(0o400)
                changed = copy.deepcopy(observed)
                if defect == "runtime-proof":
                    changed["witnesses"][0]["proofSha256"] = "d" * 64

                def original_execution(sequence):
                    if sequence != 17:
                        raise evidence.ConformanceError("OwnershipInvalid")
                    return evidence.canonical_bytes({
                        "startedMs": 900, "endedMs": 1001 if defect == "late-controller" else 950})

                run.read_execution_record = original_execution
                with self.subTest(defect=defect), mock.patch.object(
                        sources, "native_artifact_transfer_controls",
                        side_effect=evidence.ConformanceError("ProofMismatch") if defect == "transfer-failure" else None,
                        return_value={"sourceProofs": proofs}) as transfer, mock.patch.object(
                        sources, "artifact_original_child_sources",
                        side_effect=evidence.ConformanceError("ProofMismatch") if defect == "children-failure" else None,
                        return_value={"observations": children}) as child, mock.patch.object(
                        sources, "artifact_source_observations", return_value=(captures, packets)), mock.patch.object(
                        sources, "artifact_source_output_seal",
                        side_effect=evidence.ConformanceError("ProofMismatch") if defect == "seal-failure" else None,
                        return_value=seal) as output:
                    if defect:
                        with self.assertRaises(evidence.ConformanceError):
                            sources.native_artifact_controller_source(
                                run, inputs, manifest, changed, sequence=17, started_ms=100, ended_ms=1000)
                    else:
                        admitted = sources.native_artifact_controller_source(
                            run, inputs, manifest, observed, sequence=17, started_ms=100, ended_ms=1000)
                        self.assertEqual(admitted["sourceReceipt"], receipt)
                        self.assertEqual(len(admitted["sourceProofs"]), 44)
                        transfer.assert_called_once_with(run, inputs, started_ms=100, ended_ms=900)
                        child.assert_called_once_with(
                            root, inputs, attempt, namespace="qualification-artifact-transfers")
                        self.assertEqual(output.call_args.kwargs["sequence"], 17)
                        with self.assertRaises(TypeError):
                            admitted["sourceProofs"]["replacement"] = b""

    def test_native_artifact_transfer_controls_require_fresh_complete_serial_joint_graphs(self):
        import conformance_sources as sources
        from conformance_execution import OwnedRun
        self.assertTrue(callable(getattr(sources, "native_artifact_transfer_controls", None)),
                        "Qualification transfers need all four original graphs inside the same serial joint window.")
        inputs = {**self.inputs, "profileId": "artifacts", "mode": "qualification"}
        run = object.__new__(OwnedRun)
        run.run_id = inputs["runId"]
        rows = [("local", 268435456), ("local", 4294967296), ("object", 268435456), ("object", 4294967296)]
        for defect in (None, "early", "late", "overlap", "sequence", "duplicate-proof", "missing"):
            graphs = []
            for index, (provider, size) in enumerate(rows, 1):
                sequence = 1 if defect == "sequence" and index == 2 else index
                started, ended = index * 100, index * 100 + 50
                if defect == "early" and index == 1:
                    started = 99
                elif defect == "late" and index == 4:
                    ended = 451
                elif defect == "overlap" and index == 2:
                    started = 149
                prefix = f"proofs/qualification-artifact-transfers/transfer-{provider}-{size}"
                graph = {"sequence": sequence, "sourceProofs": {
                    f"proofs/transfer-command-{sequence:04}.json": evidence.canonical_bytes({
                        "startedMs": started, "endedMs": ended}),
                    prefix + "/producer.json": f"original-{provider}-{size}".encode()}}
                if defect == "duplicate-proof":
                    graph["sourceProofs"]["proofs/shared-source.json"] = b"same bytes cannot hide path reuse"
                graphs.append(graph)
            if defect == "missing":
                graphs[-1] = evidence.ConformanceError("ProofMismatch")
            with self.subTest(defect=defect), mock.patch.object(
                    sources, "native_artifact_transfer_source", side_effect=graphs) as selected:
                if defect:
                    with self.assertRaises(evidence.ConformanceError):
                        sources.native_artifact_transfer_controls(run, inputs, started_ms=100, ended_ms=450)
                else:
                    admitted = sources.native_artifact_transfer_controls(run, inputs, started_ms=100, ended_ms=450)
                    self.assertEqual(len(admitted["controls"]), 7)
                    self.assertEqual(len(admitted["sourceProofs"]), 8)
                    hashes = {hashlib.sha256(raw).hexdigest() for raw in admitted["sourceProofs"].values()}
                    self.assertTrue(all(set(values) <= hashes for values in admitted["controls"].values()))
                    self.assertEqual([call.args[2:] for call in selected.call_args_list], rows)
                    self.assertTrue(all(call.kwargs == {"namespace": "qualification-artifact-transfers"}
                                        for call in selected.call_args_list))
                    with self.assertRaises(TypeError):
                        admitted["controls"]["local-256m-write-read"] = ()
        with mock.patch.object(sources, "native_artifact_transfer_source") as selected:
            for captured, started, ended in (
                    ({**inputs, "mode": "diagnostic"}, 100, 450),
                    ({**inputs, "profileId": "metadata"}, 100, 450),
                    ({**inputs, "runId": str(uuid.uuid4())}, 100, 450),
                    (inputs, 450, 100), (inputs, True, 450), (inputs, 100, float("nan"))):
                with self.subTest(captured=captured, started=started, ended=ended), self.assertRaises(evidence.ConformanceError):
                    sources.native_artifact_transfer_controls(run, captured, started_ms=started, ended_ms=ended)
            selected.assert_not_called()

    def test_artifact_source_capture_requires_exact_current_bytes_and_original_runtime_witnesses(self):
        import conformance_sources as sources
        from conformance_case_catalog import ORIGINAL_ARTIFACT_PROOF_SOURCES
        from types import SimpleNamespace
        self.assertTrue(callable(getattr(sources, "artifact_source_context", None)))
        self.assertTrue(callable(getattr(sources, "artifact_source_observations", None)))
        self.assertTrue(callable(getattr(sources, "artifact_source_output_seal", None)))
        inputs = {**self.inputs, "profileId": "artifacts"}
        manifest = {**self.manifest, "inputSha256": evidence.digest(inputs), "expected": [
            {"testIdentity": identity, "bindingId": provider}
            for identity, (_, provider, _) in ORIGINAL_ARTIFACT_PROOF_SOURCES.items()]}
        witnesses = [{
            "testIdentity": row["testIdentity"], "bindingId": row["bindingId"],
            "executionId": str(uuid.uuid4()), "status": "Passed",
            "proofSha256": hashlib.sha256(row["testIdentity"].encode()).hexdigest()}
            for row in manifest["expected"]]
        observed = {
            "attemptId": manifest["attemptId"], "diagnosticCode": "None", "witnesses": witnesses,
            "proofs": {f'proof-{row["executionId"]}.json': row["proofSha256"] for row in witnesses}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            run = SimpleNamespace(root=root, run_id=inputs["runId"], root_id=uuid.uuid4().hex)
            context = sources.artifact_source_context(run, inputs, manifest, namespace="category-artifact-transfers")
            self.assertEqual(set(context["cases"]), set(ORIGINAL_ARTIFACT_PROOF_SOURCES))
            self.assertEqual(16, len(context["cases"]))
            qualified_inputs = {**inputs, "mode": "qualification"}
            qualified_manifest = {
                **manifest, "attemptId": str(uuid.uuid4()), "inputSha256": evidence.digest(qualified_inputs)}
            qualified_context = sources.artifact_source_context(
                run, qualified_inputs, qualified_manifest, namespace="qualification-artifact-transfers")
            for identity, (kind, _, _) in ORIGINAL_ARTIFACT_PROOF_SOURCES.items():
                if kind == "transfer":
                    self.assertNotEqual(qualified_context["cases"][identity], context["cases"][identity])
                    self.assertIn("/proofs/qualification-artifact-transfers/", qualified_context["cases"][identity][0])
            for captured, selected, namespace in (
                    (inputs, manifest, "qualification-artifact-transfers"),
                    (qualified_inputs, qualified_manifest, "category-artifact-transfers"),
                    ({**qualified_inputs, "profileId": "metadata"}, qualified_manifest, "qualification-artifact-transfers")):
                with self.assertRaises(evidence.ConformanceError):
                    sources.artifact_source_context(run, captured, selected, namespace=namespace)
            capture = Path(context["outputDirectory"])
            capture.mkdir(parents=True)
            packet_paths, originals = {}, {}
            for identity, paths in context["cases"].items():
                files = {}
                for index, value in enumerate(paths):
                    path = Path(value)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    raw = b"" if index == 2 else ("synthetic-source-" + identity).encode()
                    path.write_bytes(raw)
                    files[hashlib.sha256(value.encode()).hexdigest()] = hashlib.sha256(raw).hexdigest()
                packet = {
                    "schemaVersion": 1, "qualification": False, "runId": inputs["runId"],
                    "attemptId": manifest["attemptId"], "inputsSha256": evidence.digest(inputs),
                    "testIdentity": identity, "files": files}
                packet_paths[identity] = capture / ("artifact-source-" + hashlib.sha256(identity.encode()).hexdigest() + ".json")
                originals[identity] = evidence.canonical_bytes(packet)
                packet_paths[identity].write_bytes(originals[identity])
            observations, retained = sources.artifact_source_observations(
                root, inputs, manifest, observed, namespace="category-artifact-transfers")
            self.assertEqual(16, len(observations))
            self.assertEqual(16, len(retained))
            for row in observations:
                witness = next(w for w in witnesses if w["testIdentity"] == row["testIdentity"])
                self.assertEqual(witness["executionId"], row["executionId"])
                self.assertEqual(witness["proofSha256"], row["runtimeProofSha256"])
                self.assertEqual(hashlib.sha256(originals[row["testIdentity"]]).hexdigest(), row["sourceProofSha256"])
            self.assertNotIn(str(root), b"".join(retained.values()).decode())
            self.assertNotIn("synthetic-source-", b"".join(retained.values()).decode())
            context_path = root / f'stores/artifact-source-context-{manifest["attemptId"]}.json'
            context_raw = evidence.canonical_bytes(context)
            context_path.write_bytes(context_raw)
            context_path.chmod(0o400)
            seal_path = root / f'proofs/artifact-source-seal-{manifest["attemptId"]}.json'
            seal = {
                "schemaVersion": 1, "qualification": False, "runId": run.run_id,
                "invocationGroupId": inputs["invocationGroupId"], "attemptId": manifest["attemptId"],
                "rootId": run.root_id, "inputsSha256": evidence.digest(inputs),
                "packets": {packet_paths[row["testIdentity"]].name: row["sourceProofSha256"] for row in observations}}
            seal_raw = json.dumps(seal, separators=(",", ":")).encode()
            seal_path.write_bytes(seal_raw)
            seal_path.chmod(0o400)
            record = {
                "runId": run.run_id, "rootId": run.root_id, "scope": "ordinary", "groupState": "Exited",
                "exitCode": 0, "diagnosticCode": "None",
                "inputFiles": {context_path.relative_to(root).as_posix(): hashlib.sha256(context_raw).hexdigest()},
                "outputFiles": {seal_path.relative_to(root).as_posix(): hashlib.sha256(seal_raw).hexdigest()}}
            native = object.__new__(sources.OwnedRun)
            native.root, native.run_id, native.root_id, native.command_sequence = root, run.run_id, run.root_id, 1
            native.read_execution_record = lambda sequence: evidence.canonical_bytes(record)
            self.assertEqual(sources.artifact_source_output_seal(
                native, inputs, manifest, observations, namespace="category-artifact-transfers"), seal_raw)
            native.command_sequence = 2
            reads = []

            def original_record(sequence):
                reads.append(sequence)
                return evidence.canonical_bytes(record if sequence == 1 else {**record, "outputFiles": {}})

            native.read_execution_record = original_record
            with self.assertRaises(evidence.ConformanceError):
                sources.artifact_source_output_seal(
                    native, inputs, manifest, observations, namespace="category-artifact-transfers")
            self.assertEqual(sources.artifact_source_output_seal(
                native, inputs, manifest, observations, namespace="category-artifact-transfers", sequence=1), seal_raw)
            self.assertEqual(reads, [2, 1])
            for sequence in (0, True, 3):
                with self.subTest(sequence=sequence), self.assertRaises(evidence.ConformanceError):
                    sources.artifact_source_output_seal(
                        native, inputs, manifest, observations, namespace="category-artifact-transfers", sequence=sequence)
            self.assertEqual(reads, [2, 1])
            native.command_sequence = 1
            native.read_execution_record = lambda sequence: evidence.canonical_bytes(record)
            for mutation in ("foreign-root", "foreign-run", "wrong-scope", "missing-output", "missing-context",
                             "mutable-output", "rehashed-replacement"):
                with self.subTest(seal=mutation):
                    changed_record = copy.deepcopy(record)
                    changed_observations = copy.deepcopy(observations)
                    if mutation == "foreign-root":
                        changed_record["rootId"] = uuid.uuid4().hex
                    elif mutation == "foreign-run":
                        changed_record["runId"] = str(uuid.uuid4())
                    elif mutation == "wrong-scope":
                        changed_record["scope"] = "recovery"
                    elif mutation == "missing-output":
                        changed_record["outputFiles"] = {}
                    elif mutation == "missing-context":
                        changed_record["inputFiles"] = {}
                    elif mutation == "mutable-output":
                        seal_path.chmod(0o600)
                    else:
                        changed_observations[0]["sourceProofSha256"] = "e" * 64
                        replacement = {**seal, "packets": {
                            packet_paths[row["testIdentity"]].name: row["sourceProofSha256"]
                            for row in changed_observations}}
                        seal_path.chmod(0o600)
                        seal_path.write_bytes(evidence.canonical_bytes(replacement))
                        seal_path.chmod(0o400)
                    native.read_execution_record = lambda sequence: evidence.canonical_bytes(changed_record)
                    with self.assertRaises(evidence.ConformanceError):
                        sources.artifact_source_output_seal(
                            native, inputs, manifest, changed_observations, namespace="category-artifact-transfers")
                    seal_path.chmod(0o600)
                    seal_path.write_bytes(seal_raw)
                    seal_path.chmod(0o400)
            identity = next(iter(packet_paths))
            for mutation in ("missing", "foreign-run", "foreign-inputs", "extra-field", "changed-bytes",
                             "missing-witness", "failed-witness", "wrong-binding", "extra-packet"):
                with self.subTest(mutation=mutation):
                    packet = evidence.load_json(originals[identity])
                    changed = copy.deepcopy(observed)
                    source = Path(context["cases"][identity][0])
                    previous = source.read_bytes()
                    extra = capture / "extra.json"
                    if mutation == "missing":
                        packet_paths[identity].unlink()
                    elif mutation == "foreign-run":
                        packet["runId"] = str(uuid.uuid4())
                    elif mutation == "foreign-inputs":
                        packet["inputsSha256"] = "f" * 64
                    elif mutation == "extra-field":
                        packet["unexpected"] = True
                    elif mutation == "changed-bytes":
                        source.write_bytes(b"changed")
                    elif mutation == "missing-witness":
                        changed["witnesses"].pop()
                    elif mutation == "failed-witness":
                        changed["witnesses"][0]["status"] = "Failed"
                    elif mutation == "wrong-binding":
                        changed["witnesses"][0]["bindingId"] = "foreign"
                    else:
                        extra.write_bytes(b"{}")
                    if mutation != "missing":
                        packet_paths[identity].write_bytes(evidence.canonical_bytes(packet))
                    with self.assertRaises(evidence.ConformanceError):
                        sources.artifact_source_observations(
                            root, inputs, manifest, changed, namespace="category-artifact-transfers")
                    packet_paths[identity].write_bytes(originals[identity])
                    source.write_bytes(previous)
                    if extra.exists():
                        extra.unlink()
            with self.assertRaises(evidence.ConformanceError):
                sources.artifact_source_context(run, inputs, manifest, namespace="foreign-transfers")
            with self.assertRaises(evidence.ConformanceError):
                sources.artifact_source_context(
                    run, inputs, {**manifest, "expected": manifest["expected"][:-1]},
                    namespace="category-artifact-transfers")

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

    def test_authority_observations_require_both_exact_loaded_provider_images(self):
        import conformance_case_catalog as catalog
        for mutation in (None, "missing", "reversed", "duplicate", "borrowed-image", "foreign-binding", "missing-package"):
            self.setUp()
            artifact, _ = self.original_transport(contract=True, case_id="QC-12")
            self.identity = catalog.authority_integration_witnesses()[0]
            metadata_path, metadata_package = "metadata/Hoard.Metadata.dll", "Hoard.Metadata"
            self.inputs["runtimeAssemblies"][metadata_path] = "b" * 64
            self.inputs["packages"].append({
                **self.inputs["packages"][0], "packageId": metadata_package, "sha256": "b" * 64,
                "runtimeAssemblies": {"lib/net10.0/Hoard.Metadata.dll": "b" * 64}})
            host_path, host_package = "host/Hoard.HostAdapter.dll", "Hoard.HostAdapter"
            self.inputs["runtimeAssemblies"][host_path] = "f" * 64
            self.inputs["packages"].append({
                **self.inputs["packages"][0], "packageId": host_package, "sha256": "f" * 64,
                "runtimeAssemblies": {"lib/net10.0/Hoard.HostAdapter.dll": "f" * 64}})
            artifact["testIdentity"] = self.identity
            metadata = copy.deepcopy(artifact)
            metadata["observationId"] = str(uuid.uuid4())
            metadata["components"]["contract"].update(
                instanceId=str(uuid.uuid4()), assemblySha256="b" * 64, typeSha256="b" * 64)
            host = copy.deepcopy(artifact)
            host["observationId"] = str(uuid.uuid4())
            host["components"]["contract"].update(
                instanceId=str(uuid.uuid4()), assemblySha256="f" * 64, typeSha256="f" * 64)
            nodes = [metadata, artifact, host]
            if mutation == "missing":
                nodes.pop()
            elif mutation == "reversed":
                nodes.reverse()
            elif mutation == "duplicate":
                nodes[1] = copy.deepcopy(metadata)
            elif mutation == "borrowed-image":
                metadata["components"]["contract"]["assemblySha256"] = "d" * 64
            elif mutation == "foreign-binding":
                metadata["bindingId"] = "object"
            elif mutation == "missing-package":
                self.inputs["packages"] = [package for package in self.inputs["packages"]
                                           if package["packageId"] != metadata_package]
            entry = self.manifest["expected"][0]
            entry.update(testIdentity=self.identity, fullyQualifiedName=self.identity.split("(")[0])
            self.manifest["inputSha256"] = evidence.digest(self.inputs)
            self.proof.update(testIdentity=self.identity, originalObservations=nodes,
                              inputSha256=evidence.digest(self.inputs), manifestSha256=evidence.digest(self.manifest))
            self.witness.update(testIdentity=self.identity, inputSha256=evidence.digest(self.inputs),
                                proofSha256=evidence.digest(self.proof))
            self.completion.update(inputSha256=evidence.digest(self.inputs), manifestSha256=evidence.digest(self.manifest))
            assignments = {"local": {self.identity: (
                {"contract": (metadata_path, metadata_package)},
                {"contract": ("provider/Hoard.Fixture.dll", "Hoard.Fixture")},
                {"contract": (host_path, host_package)})}}
            with self.subTest(mutation=mutation):
                if mutation is None:
                    observed = self.ingest(original_inputs=assignments, expected_tests={self.identity: ("local", "none")})
                    self.assertEqual(tuple(observed["originalObservations"][self.execution]), tuple(nodes))
                else:
                    with self.assertRaises(evidence.ConformanceError):
                        self.ingest(original_inputs=assignments, expected_tests={self.identity: ("local", "none")})

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

    def test_native_stall_graph_requires_original_owned_inputs_and_expected_deadline(self):
        import conformance_sources as sources
        from types import SimpleNamespace

        self.category_history(mode="qualification")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            def write(path, raw):
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    path.chmod(0o600)
                path.write_bytes(raw)
                path.chmod(0o400)

            assembly = ("candidate/tests/contracts/Hoard.Conformance.Tests/bin/package-diagnostic/"
                        "Release/net10.0/Hoard.Conformance.Tests.dll")
            write(root / assembly, b"explicit-stall-controller-model-not-native-execution")
            self.inputs["runtimeAssemblies"] = {assembly: evidence.file_sha256(root / assembly)}
            namespace = "qualification-sqlite-native-noncooperation"
            inputs_path = f"proofs/{namespace}-native-inputs.json"
            write(root / inputs_path, evidence.canonical_bytes(self.inputs))
            run = SimpleNamespace(
                root=root, run_id=self.inputs["runId"], root_id=str(uuid.uuid4()), live_children=lambda: ())
            command = {
                "schemaVersion": 1, "sequence": 7, "childPid": 200, "childStartSha256": "c" * 64,
                "startedMs": 10, "endedMs": 45010, "exitCode": -9,
                "diagnosticCode": "DeadlineExceeded", "groupState": "Exited", "scope": "recovery"}
            producer = {
                "schemaVersion": 1, "inputsSha256": evidence.digest(self.inputs), "childPid": 200,
                "boundaryObservations": 1, "guards": [1, 1, 1],
                "commitCode": "Uncertain", "commitPhase": "Commit", "commitRetry": "Reconcile",
                "ticketSha256": "d" * 64, "failureTicketSha256": "d" * 64,
                "disposeCode": "CleanupIncomplete", "incompleteCleanups": 1,
                "admissionCode": "Disposed", "settlementCompleted": False, "cleanupState": "Retained",
                "resourceIds": ["resource-a"], "ledgerStates": ["Allocated", "Active", "Settling", "Retained"]}
            provider = next(package for package in self.inputs["packages"]
                            if package["packageId"] == "Hoard.Fixtures.Metadata.Sqlite")
            args = ["dotnet", str(root / assembly), "sqlite-native-noncooperation",
                    str(root / f"proofs/{namespace}.json"), str(root / "stores" / namespace),
                    str(root / "candidate"), provider["sha256"], evidence.digest(self.inputs)]
            native = {
                **command, "runId": run.run_id, "rootId": run.root_id,
                "argvSha256": evidence.digest(args),
                "cwdSha256": hashlib.sha256(str((root / assembly).parent).encode()).hexdigest(),
                "controlRecordSha256": evidence.digest(command),
                "outputFiles": {f"proofs/{namespace}.json": evidence.digest(producer)},
                "inputFiles": {assembly: self.inputs["runtimeAssemblies"][assembly],
                               inputs_path: evidence.digest(self.inputs)}}
            original = evidence.canonical_bytes(native)
            run.read_execution_record = mock.Mock(return_value=original)
            control_path = root / "proofs/recovery-command-0007.json"
            native_path = root / "proofs/execution-command-0007.json"
            producer_path = root / f"proofs/{namespace}.json"
            graph_path = root / f"proofs/{namespace}-native-executions.json"
            write(control_path, evidence.canonical_bytes(command))
            write(native_path, original)
            write(producer_path, evidence.canonical_bytes(producer))
            graph = {
                "schemaVersion": 1, "qualification": False, "runId": run.run_id,
                "invocationGroupId": self.inputs["invocationGroupId"], "inputsSha256": evidence.digest(self.inputs),
                "assemblyPath": assembly, "inputsPath": inputs_path, "sequence": 7,
                "producerSha256": evidence.digest(producer), "controllerSha256": evidence.digest(command),
                "executionSha256": hashlib.sha256(original).hexdigest()}
            write(graph_path, evidence.canonical_bytes(graph))
            with mock.patch.object(sources, "OwnedRun", type(run)):
                admitted = sources.native_metadata_noncooperation_control(
                    run, self.inputs, started_ms=9, ended_ms=45011)
                self.assertEqual(set(admitted["controls"]), {"sqlite3-step-stall-and-incomplete-cleanup"})
                self.assertEqual(len(admitted["sourceProofs"]), 5)
                self.assertEqual(admitted["sourceProofs"][native_path.relative_to(root).as_posix()], original)
                for change in ({"mode": "diagnostic"}, {"runId": str(uuid.uuid4())},
                               {"invocationGroupId": str(uuid.uuid4())}):
                    with self.subTest(inputs=change), self.assertRaises(evidence.ConformanceError):
                        sources.native_metadata_noncooperation_control(
                            run, {**self.inputs, **change}, started_ms=9, ended_ms=45011)
                import conformance_case_catalog as catalog

                history = evidence.CategoryRuntimeHistory(self.inputs)
                with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
                    history.begin("sqlite", self.attempt)
                case = next(case for case in history._cases if case.binding_id == "sqlite" and case.case_id == "MP-37")
                witnesses = tuple({
                    "bindingId": "sqlite", "testIdentity": identity, "executionId": str(uuid.uuid4()),
                    "status": "Passed", "proofSha256": "e" * 64} for identity in case.witnesses)
                self.assertEqual(history._case_results(
                    "sqlite", "None", 45011, witnesses)[case.key]["status"], "Incomplete")
                unrelated_source = {
                    "bindingId": "sqlite", "testIdentity": catalog.METADATA_RECOVERY_SOURCE_WITNESS,
                    "executionId": str(uuid.uuid4()), "status": "Passed", "proofSha256": "f" * 64}
                result = history._case_results(
                    "sqlite", "None", 45011, (*witnesses, unrelated_source),
                    source_parents={unrelated_source["executionId"]: "d" * 64},
                    control_proofs=admitted["controls"])[case.key]
                self.assertEqual(result["status"], "Passed")
                self.assertEqual(set(result["attempts"][0]["witnessIds"]),
                                 {witness["executionId"] for witness in witnesses})
                self.assertTrue(set(admitted["controls"]["sqlite3-step-stall-and-incomplete-cleanup"])
                                <= set(result["attempts"][0]["proofSha256"]))
                self.assertEqual(history._case_results(
                    "sqlite", "None", 45011, (*witnesses[:-1], unrelated_source),
                    source_parents={unrelated_source["executionId"]: "d" * 64},
                    control_proofs=admitted["controls"])[case.key]["status"], "Incomplete")
                for change in (
                        {"argvSha256": "a" * 64}, {"cwdSha256": "a" * 64},
                        {"inputFiles": {}}, {"controlRecordSha256": "a" * 64},
                        {"diagnosticCode": "None"}, {"groupState": "Retained"}):
                    rewritten = evidence.canonical_bytes({**native, **change})
                    write(native_path, rewritten)
                    write(graph_path, evidence.canonical_bytes({
                        **graph, "executionSha256": hashlib.sha256(rewritten).hexdigest()}))
                    with self.subTest(change=change), self.assertRaises(evidence.ConformanceError):
                        sources.native_metadata_noncooperation_control(
                            run, self.inputs, started_ms=9, ended_ms=45011)
                write(native_path, original)
                write(graph_path, evidence.canonical_bytes(graph))
                for bounds in ((11, 45011), (9, 45009)):
                    with self.subTest(bounds=bounds), self.assertRaises(evidence.ConformanceError):
                        sources.native_metadata_noncooperation_control(
                            run, self.inputs, started_ms=bounds[0], ended_ms=bounds[1])
                rewritten_producer = {**producer, "ticketSha256": "e" * 64, "failureTicketSha256": "e" * 64}
                write(producer_path, evidence.canonical_bytes(rewritten_producer))
                write(graph_path, evidence.canonical_bytes({
                    **graph, "producerSha256": evidence.digest(rewritten_producer)}))
                with self.assertRaises(evidence.ConformanceError):
                    sources.native_metadata_noncooperation_control(
                        run, self.inputs, started_ms=9, ended_ms=45011)
                write(producer_path, evidence.canonical_bytes({**producer, "guards": [1, 1, 0]}))
                write(graph_path, evidence.canonical_bytes({
                    **graph, "producerSha256": evidence.digest({**producer, "guards": [1, 1, 0]})}))
                with self.assertRaises(evidence.ConformanceError):
                    sources.native_metadata_noncooperation_control(
                        run, self.inputs, started_ms=9, ended_ms=45011)

    def test_native_owner_probe_requires_distinct_process_original_output_and_crash_reopen(self):
        import conformance_sources as sources
        from types import SimpleNamespace

        self.category_history(mode="qualification")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            def write(path, raw):
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    path.chmod(0o600)
                path.write_bytes(raw)
                path.chmod(0o400)

            assembly = "candidate/tests/fixtures/metadata/CrashRunner/bin/Release/net10.0/Hoard.Fixtures.Metadata.CrashRunner.dll"
            write(root / assembly, b"explicit-ownership-controller-model-not-native-execution")
            self.inputs["runtimeAssemblies"] = {assembly: evidence.file_sha256(root / assembly)}
            namespace = "qualification-sqlite-ownership"
            inputs_path = f"proofs/{namespace}-native-inputs.json"
            probe_path = f"proofs/{namespace}-probe.json"
            write(root / inputs_path, evidence.canonical_bytes(self.inputs))
            probe = {"schemaVersion": 1, "ownerPid": 200, "probePid": 300,
                     "probeStartSha256": "c" * 64, "competingOwnerRejected": True}
            write(root / probe_path, evidence.canonical_bytes(probe))
            run = SimpleNamespace(root=root, run_id=self.inputs["runId"], root_id=str(uuid.uuid4()),
                                  live_children=lambda: ())
            records, commands = {}, []
            for offset, mode in enumerate(("hold-owner-probe", "reopen-owner")):
                sequence = offset + 7
                control = {
                    "schemaVersion": 1, "sequence": sequence, "childPid": 200 + offset,
                    "childStartSha256": "b" * 64, "startedMs": 10 + 3 * offset, "endedMs": 12 + 3 * offset,
                    "exitCode": -9 if offset == 0 else 0, "diagnosticCode": "None",
                    "groupState": "Exited", "scope": "recovery",
                    **({"barrier": {"value": 30, "observedMs": 10.5, "signalMs": 11}} if offset == 0 else {})}
                directory = root / "stores" / namespace
                arguments = ["dotnet", str(root / assembly), mode, str(directory / "metadata.db"), str(directory),
                             str(root / probe_path) if offset == 0 else "owner"]
                native = {
                    **{key: value for key, value in control.items() if key != "barrier"},
                    "runId": run.run_id, "rootId": run.root_id,
                    "argvSha256": evidence.digest(arguments),
                    "cwdSha256": hashlib.sha256(str((root / assembly).parent).encode()).hexdigest(),
                    "controlRecordSha256": evidence.digest(control),
                    "inputFiles": {assembly: self.inputs["runtimeAssemblies"][assembly], inputs_path: evidence.digest(self.inputs)},
                    **({"outputFiles": {probe_path: evidence.digest(probe)}} if offset == 0 else {})}
                records[sequence] = evidence.canonical_bytes(native)
                write(root / f"proofs/recovery-command-{sequence:04}.json", evidence.canonical_bytes(control))
                write(root / f"proofs/execution-command-{sequence:04}.json", records[sequence])
                commands.append({"mode": mode, "sequence": sequence,
                                 "controllerSha256": evidence.digest(control),
                                 "executionSha256": hashlib.sha256(records[sequence]).hexdigest()})
            run.read_execution_record = lambda sequence: records[sequence]
            graph = {
                "schemaVersion": 1, "qualification": False, "runId": run.run_id,
                "invocationGroupId": self.inputs["invocationGroupId"], "inputsSha256": evidence.digest(self.inputs),
                "assemblyPath": assembly, "inputsPath": inputs_path, "commands": commands,
                "probeSha256": evidence.digest(probe)}
            graph_path = root / f"proofs/{namespace}-native-executions.json"
            write(graph_path, evidence.canonical_bytes(graph))
            with mock.patch.object(sources, "OwnedRun", type(run)):
                admitted = sources.native_metadata_ownership_control(run, self.inputs, started_ms=9, ended_ms=16)
                self.assertEqual(set(admitted["controls"]), {"second-process-owner-and-crash-released-lock"})
                self.assertEqual(len(admitted["sourceProofs"]), 7)
                history = evidence.CategoryRuntimeHistory(self.inputs)
                with mock.patch.object(evidence.time, "monotonic", return_value=0.009):
                    history.begin("sqlite", self.attempt)
                case = next(case for case in history._cases if case.binding_id == "sqlite" and case.case_id == "MP-43")
                witnesses = tuple({
                    "bindingId": "sqlite", "testIdentity": identity, "executionId": str(uuid.uuid4()),
                    "status": "Passed", "proofSha256": "e" * 64} for identity in case.witnesses)
                result = history._case_results(
                    "sqlite", "None", 16, witnesses, control_proofs=admitted["controls"])[case.key]
                self.assertEqual(result["status"], "Passed")
                self.assertEqual(set(result["attempts"][0]["witnessIds"]),
                                 {witness["executionId"] for witness in witnesses})
                for changed in (probe | {"probePid": 200}, probe | {"probeStartSha256": "e" * 64}):
                    write(root / probe_path, evidence.canonical_bytes(changed))
                    write(graph_path, evidence.canonical_bytes(graph | {"probeSha256": evidence.digest(changed)}))
                    with self.subTest(probe=changed), self.assertRaises(evidence.ConformanceError):
                        sources.native_metadata_ownership_control(run, self.inputs, started_ms=9, ended_ms=16)
                write(root / probe_path, evidence.canonical_bytes(probe))
                write(graph_path, evidence.canonical_bytes(graph | {"commands": commands[:1]}))
                with self.assertRaises(evidence.ConformanceError):
                    sources.native_metadata_ownership_control(run, self.inputs, started_ms=9, ended_ms=16)

    def test_unchanged_metadata_consumer_requires_both_explicit_original_native_compositions(self):
        import conformance_sources as sources
        from types import SimpleNamespace

        self.category_history(mode="qualification")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            def write(path, value):
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    path.chmod(0o600)
                path.write_bytes(value)
                path.chmod(0o400)

            assembly = "candidate/tests/fixtures/metadata/Consumer/bin/Release/net10.0/Hoard.Fixtures.Metadata.Consumer.dll"
            write(root / assembly, b"explicit-unchanged-consumer-model-not-native-execution")
            self.inputs["runtimeAssemblies"] = {assembly: evidence.file_sha256(root / assembly)}
            namespace = "qualification-metadata-package-consumer"
            inputs_path = f"proofs/{namespace}-native-inputs.json"
            write(root / inputs_path, evidence.canonical_bytes(self.inputs))
            records, commands = {}, []
            run = SimpleNamespace(root=root, run_id=self.inputs["runId"], root_id=str(uuid.uuid4()), live_children=lambda: ())
            for sequence, binding in enumerate(("sqlite", "memory"), 1):
                control = {
                    "schemaVersion": 1, "sequence": sequence, "childPid": 200 + sequence,
                    "childStartSha256": "b" * 64, "startedMs": sequence * 1000, "endedMs": sequence * 1000 + 100,
                    "exitCode": 0, "diagnosticCode": "None", "groupState": "Exited", "scope": "recovery"}
                arguments = ["dotnet", str(root / assembly), binding,
                             str(root / "stores" / namespace / binding / "metadata.db")]
                native = {
                    **control, "runId": run.run_id, "rootId": run.root_id,
                    "argvSha256": evidence.digest(arguments),
                    "cwdSha256": hashlib.sha256(str((root / assembly).parent).encode()).hexdigest(),
                    "controlRecordSha256": evidence.digest(control),
                    "inputFiles": {assembly: self.inputs["runtimeAssemblies"][assembly], inputs_path: evidence.digest(self.inputs)}}
                records[sequence] = evidence.canonical_bytes(native)
                write(root / f"proofs/recovery-command-{sequence:04}.json", evidence.canonical_bytes(control))
                write(root / f"proofs/execution-command-{sequence:04}.json", records[sequence])
                commands.append({"bindingId": binding, "sequence": sequence, "controllerSha256": evidence.digest(control),
                                 "executionSha256": hashlib.sha256(records[sequence]).hexdigest()})
            run.read_execution_record = lambda sequence: records[sequence]
            graph = {
                "schemaVersion": 1, "qualification": False, "runId": run.run_id,
                "invocationGroupId": self.inputs["invocationGroupId"], "inputsSha256": evidence.digest(self.inputs),
                "assemblyPath": assembly, "inputsPath": inputs_path, "commands": commands}
            path = root / f"proofs/{namespace}-native-executions.json"
            write(path, evidence.canonical_bytes(graph))
            with mock.patch.object(sources, "OwnedRun", type(run)):
                admitted = sources.native_metadata_package_consumer_control(run, self.inputs, started_ms=999, ended_ms=2101)
                self.assertEqual(set(admitted["controls"]), {"unchanged-package-consumer"})
                self.assertEqual(len(admitted["sourceProofs"]), 6)
                for rows in (commands[:1], commands[::-1], [commands[0], commands[1] | {"bindingId": "sqlite"}]):
                    write(path, evidence.canonical_bytes(graph | {"commands": rows}))
                    with self.subTest(commands=rows), self.assertRaises(evidence.ConformanceError):
                        sources.native_metadata_package_consumer_control(run, self.inputs, started_ms=999, ended_ms=2101)
                write(path, evidence.canonical_bytes(graph))
                for bounds in ((1001, 2101), (999, 2099)):
                    with self.subTest(bounds=bounds), self.assertRaises(evidence.ConformanceError):
                        sources.native_metadata_package_consumer_control(
                            run, self.inputs, started_ms=bounds[0], ended_ms=bounds[1])

    def test_frozen_metadata_binary_requires_original_marker_current_platform_and_owned_execution(self):
        import conformance_sources as sources
        from types import SimpleNamespace

        self.category_history(mode="qualification")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            runtime = "candidate/tests/fixtures/metadata/RetainedMarker/bin/compatibility/net10.0/"
            current = "candidate/tests/fixtures/metadata/Consumer/bin/Release/net10.0/"
            old = "retained/bin/Release/net10.0/"
            files = {"RetainedMarker.dll": b"explicit-frozen-model-not-native",
                     "RetainedMarker.deps.json": b"{}", "RetainedMarker.runtimeconfig.json": b"{}"}
            binaries = {old + name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}
            for name in ("Hoard.Abstractions.dll", "Hoard.Core.dll", "Hoard.Hosting.dll"):
                binaries[old + name] = hashlib.sha256(b"old-" + name.encode()).hexdigest()
                files[name] = b"current-" + name.encode()
            self.inputs["baselines"] = [{
                "revision": "10ce78851b97b02bd83a8ef7da7ffdc2381d6519", "sourceSha256": "a" * 64,
                "lockSha256": "b" * 64, "recipeSha256": "c" * 64,
                "binarySha256": evidence.digest(binaries), "dependencySha256": binaries, "apiScope": "metadata-marker"}]
            self.inputs["runtimeAssemblies"] = {}
            for name, raw in files.items():
                for path in (runtime + name, *((current + name,) if name.startswith("Hoard.") else ())):
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
                    target.chmod(0o400)
                    self.inputs["runtimeAssemblies"][path] = hashlib.sha256(raw).hexdigest()
            namespace = "qualification-metadata-frozen-binary"
            inputs_path = f"proofs/{namespace}-native-inputs.json"
            assembly = runtime + "RetainedMarker.dll"
            control = {"schemaVersion": 1, "sequence": 1, "childPid": 200, "childStartSha256": "d" * 64,
                       "startedMs": 1000, "endedMs": 1100, "exitCode": 0, "diagnosticCode": "None",
                       "groupState": "Exited", "scope": "recovery"}
            native = {
                **control, "runId": self.inputs["runId"], "rootId": str(uuid.uuid4()),
                "argvSha256": evidence.digest(["dotnet", str(root / assembly)]),
                "cwdSha256": hashlib.sha256(str((root / assembly).parent).encode()).hexdigest(),
                "controlRecordSha256": evidence.digest(control),
                "inputFiles": {**{runtime + name: self.inputs["runtimeAssemblies"][runtime + name] for name in files},
                               inputs_path: evidence.digest(self.inputs)}}
            raw = evidence.canonical_bytes(native)
            run = SimpleNamespace(root=root, run_id=self.inputs["runId"], root_id=native["rootId"],
                                  live_children=lambda: (), read_execution_record=lambda _: raw)
            graph = {
                "schemaVersion": 1, "qualification": False, "runId": run.run_id,
                "invocationGroupId": self.inputs["invocationGroupId"], "inputsSha256": evidence.digest(self.inputs),
                "assemblyPath": assembly, "inputsPath": inputs_path, "sequence": 1,
                "baselineSha256": evidence.digest(self.inputs["baselines"][0]),
                "controllerSha256": evidence.digest(control), "executionSha256": hashlib.sha256(raw).hexdigest()}
            for path, value in (
                    (inputs_path, evidence.canonical_bytes(self.inputs)),
                    (f"proofs/{namespace}-native-executions.json", evidence.canonical_bytes(graph)),
                    ("proofs/recovery-command-0001.json", evidence.canonical_bytes(control)),
                    ("proofs/execution-command-0001.json", raw)):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(value)
                target.chmod(0o400)
            with mock.patch.object(sources, "OwnedRun", type(run)):
                admitted = sources.native_metadata_binary_control(run, self.inputs, started_ms=999, ended_ms=1101)
                self.assertEqual(set(admitted["controls"]), {"frozen-pre-F05-binary"})
                self.assertEqual(len(admitted["sourceProofs"]), 4)
                for name in ("RetainedMarker.dll", "Hoard.Hosting.dll"):
                    target = root / (runtime + name)
                    target.chmod(0o600)
                    target.write_bytes(b"substituted-image")
                    target.chmod(0o400)
                    with self.subTest(image=name), self.assertRaises(evidence.ConformanceError):
                        sources.native_metadata_binary_control(run, self.inputs, started_ms=999, ended_ms=1101)
                    target.chmod(0o600)
                    target.write_bytes(files[name])
                    target.chmod(0o400)

    def test_metadata_verifier_inventory_requires_original_native_red_and_same_source_repair(self):
        import conformance_sources as sources
        import conformance_unit_checks as checks
        import time
        from types import SimpleNamespace

        self.category_history(mode="qualification")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            original = Path(__file__).resolve().parents[2]
            self.inputs["sourceManifest"] = {}
            for path in sources.METADATA_INVENTORY_SOURCE_FILES:
                raw = (original / path).read_bytes()
                target = root / "snapshot" / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                target.chmod(0o400)
                self.inputs["sourceManifest"][path] = hashlib.sha256(raw).hexdigest()
            self.inputs["sourceManifestSha256"] = evidence.digest(self.inputs["sourceManifest"])
            namespace = "qualification-metadata-inventory"
            (root / "proofs").mkdir()
            work = root / "stores" / namespace
            work.mkdir(parents=True)
            inputs_path = f"proofs/{namespace}-native-inputs.json"
            source_files = {"snapshot/" + path: hashed for path, hashed in self.inputs["sourceManifest"].items()}
            records, commands = {}, []
            run = SimpleNamespace(root=root, run_id=self.inputs["runId"], root_id=str(uuid.uuid4()),
                                  live_children=lambda: (), read_execution_record=lambda sequence: records[sequence])
            for sequence, mode in enumerate(("baseline", "mutation", "repair"), 1):
                packet = checks.metadata_inventory(root / "snapshot", mode, work / "metadata_evidence.py")
                outputs = {
                    f"proofs/{namespace}-{mode}.json": evidence.canonical_bytes(packet),
                    f"proofs/{namespace}-{mode}.py": (work / "metadata_evidence.py").read_bytes()}
                for path, raw in outputs.items():
                    (root / path).write_bytes(raw)
                    (root / path).chmod(0o400)
                control = {
                    "schemaVersion": 1, "sequence": sequence, "childPid": 200 + sequence,
                    "childStartSha256": str(sequence) * 64, "startedMs": sequence * 1000,
                    "endedMs": sequence * 1000 + 100, "exitCode": packet["exitCode"],
                    "diagnosticCode": "None", "groupState": "Exited", "scope": "recovery"}
                arguments = [
                    sys.executable, "-I", "-B", "-S", str(root / "snapshot/scripts/conformance_unit_checks.py"),
                    "--metadata-inventory", mode, str(work / "metadata_evidence.py"),
                    str(root / f"proofs/{namespace}-{mode}.json"), str(root / f"proofs/{namespace}-{mode}.py")]
                native = {
                    **control, "runId": run.run_id, "rootId": run.root_id,
                    "argvSha256": evidence.digest(arguments),
                    "cwdSha256": hashlib.sha256(str(root / "snapshot").encode()).hexdigest(),
                    "controlRecordSha256": evidence.digest(control),
                    "inputFiles": {**source_files, inputs_path: evidence.digest(self.inputs)},
                    "outputFiles": {path: hashlib.sha256(raw).hexdigest() for path, raw in outputs.items()}}
                records[sequence] = evidence.canonical_bytes(native)
                for path, value in ((f"proofs/recovery-command-{sequence:04}.json", control),
                                    (f"proofs/execution-command-{sequence:04}.json", native)):
                    (root / path).write_bytes(evidence.canonical_bytes(value))
                    (root / path).chmod(0o400)
                commands.append({
                    "mode": mode, "sequence": sequence, "controllerSha256": evidence.digest(control),
                    "executionSha256": evidence.digest(native)})
            graph = {
                "schemaVersion": 1, "qualification": False, "runId": run.run_id,
                "invocationGroupId": self.inputs["invocationGroupId"], "inputsSha256": evidence.digest(self.inputs),
                "scriptPath": "snapshot/scripts/conformance_unit_checks.py", "inputsPath": inputs_path,
                "commands": commands}
            for path, value in ((inputs_path, self.inputs),
                                (f"proofs/{namespace}-native-executions.json", graph)):
                (root / path).write_bytes(evidence.canonical_bytes(value))
                (root / path).chmod(0o400)
            with mock.patch.object(sources, "OwnedRun", type(run)):
                admitted = sources.native_metadata_inventory_controls(run, self.inputs, started_ms=999, ended_ms=3101)
                self.assertEqual(set(admitted["controls"]), {
                    "MetadataEvidenceTests:positive-complete-and-negative-inventories",
                    "test_stale_failed_unpaired_foreign_and_false_memory_durability_reject"})
                self.assertEqual(14, len(admitted["sourceProofs"]))
                import conformance_case_catalog as catalog
                history = evidence.CategoryRuntimeHistory(self.inputs)
                history.begin("sqlite", self.attempt)
                unrelated = {
                    "bindingId": "sqlite", "testIdentity": catalog.METADATA_RECOVERY_SOURCE_WITNESS,
                    "executionId": str(uuid.uuid4()), "status": "Passed", "proofSha256": "f" * 64}
                case = next(case for case in history._cases
                            if case.binding_id == "sqlite" and case.case_id == "MP-48")
                result = history._case_results(
                    "sqlite", "None", time.monotonic() * 1000, (unrelated,),
                    source_parents={unrelated["executionId"]: "d" * 64},
                    control_proofs=admitted["controls"])[case.key]
                self.assertEqual("Incomplete", result["status"])
                self.assertEqual((), result["attempts"][0]["witnessIds"])
                witness = {**unrelated, "testIdentity": catalog.METADATA_INVENTORY_SOURCE_WITNESSES["sqlite"],
                           "executionId": str(uuid.uuid4())}
                result = history._case_results(
                    "sqlite", "None", time.monotonic() * 1000, (unrelated, witness),
                    source_parents={witness["executionId"]: "d" * 64, unrelated["executionId"]: "e" * 64},
                    control_proofs=admitted["controls"])[case.key]
                self.assertEqual("Passed", result["status"])
                self.assertEqual((witness["executionId"],), result["attempts"][0]["witnessIds"])
                packet_path = root / f"proofs/{namespace}-mutation.json"
                packet = evidence.load_json(packet_path.read_bytes())
                packet["errors"], packet["failures"] = 1, 0
                packet_path.chmod(0o600)
                packet_path.write_bytes(evidence.canonical_bytes(packet))
                packet_path.chmod(0o400)
                with self.assertRaisesRegex(evidence.ConformanceError, "ProofMismatch"):
                    sources.native_metadata_inventory_controls(run, self.inputs, started_ms=999, ended_ms=3101)

    def category_history(self, *, profile="metadata", mode="diagnostic", max_attempts=1, origin_inputs=None,
                         distinct_packages=False):
        self.inputs.update(mode=mode, profileId=profile, invocation=["profile", profile])
        self.inputs["budgets"]["profileSeconds"] = 5400 if profile == "metadata" else 10800
        original = self.inputs["bindings"][0]
        bindings = (("sqlite", "Sqlite"), ("memory", "Memory")) if profile == "metadata" else (
            ("local", "Local"), ("object", "ObjectSemantics"))
        family = "Metadata" if profile == "metadata" else "Artifacts"
        packages = [{**original["package"], "packageId": "Hoard.Fixtures." + family + "." + provider}
                    for _, provider in bindings]
        if distinct_packages:
            for package in packages:
                package["sha256"] = hashlib.sha256(package["packageId"].encode()).hexdigest()
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
        assignments = (dict(catalog.category_runtime_cases(self.inputs["profileId"], binding, mode=self.inputs["mode"]))
                       if binding is not None else {})
        if identities is not None:
            assignments = {identity: assignments[identity] for identity in identities}
        selected = ({identity: (binding, case_id) for identity, case_id in assignments.items()}
                    if selections is None else selections)
        packages = catalog.category_runtime_packages(self.inputs, {binding for binding, _ in selected.values()})
        manifest = {**self.manifest, "attemptId": self.attempt, "attemptSequence": sequence,
                    "inputSha256": evidence.digest(self.inputs),
                    "packages": [{"id": package["packageId"],
                                  "path": f'feed/candidate/{package["packageId"]}.{package["version"]}.nupkg',
                                  "sha256": package["sha256"]} for package in packages.values()], "expected": [
                        {**self.manifest["expected"][0], "testIdentity": identity,
                         "fullyQualifiedName": identity.split("(")[0], "bindingId": selected_binding,
                         "caseId": case_id, "packageId": packages[selected_binding]["packageId"]}
                        for identity, (selected_binding, case_id) in sorted(selected.items())]}
        proofs, witnesses = {}, []
        for entry in manifest["expected"]:
            binding = entry["bindingId"]
            execution = str(uuid.uuid4())
            proof = {**self.proof, "executionId": execution, "attemptId": self.attempt,
                     "attemptSequence": sequence, "inputSha256": evidence.digest(self.inputs),
                     "manifestSha256": evidence.digest(manifest), "testIdentity": entry["testIdentity"],
                     "bindingId": binding, "caseId": entry["caseId"], "durationMs": 0.5,
                     "packageSha256": packages[binding]["sha256"]}
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
                              "packageSha256": packages[binding]["sha256"],
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

    def category_quality_fixture(self, *, profile="metadata", mode="qualification", max_attempts=1,
                                 distinct_packages=False):
        import conformance_case_catalog as catalog
        history = self.category_history(profile=profile, mode=mode, max_attempts=max_attempts,
                                        distinct_packages=distinct_packages)

        def finish(sequence=1, *, failed=None, missing_control=None, missing_parent=None, proof_bytes=0,
                   missing_integration=None):
            start = 9 + (sequence - 1) * 4
            with mock.patch.object(evidence.time, "monotonic", return_value=start / 1000):
                history.begin_joint(str(uuid.uuid4()), partitions=catalog.category_execution_partitions(
                    profile, mode=mode))
            witnesses, proofs, parents = [], {}, {}
            for binding in (("sqlite", "memory") if profile == "metadata" else ("local", "object")):
                for identity in history.expected_runtime_tests(binding):
                    if identity == missing_integration:
                        continue
                    execution = str(uuid.uuid4())
                    hashed = hashlib.sha256(execution.encode()).hexdigest()
                    witnesses.append({
                        **self.witness, "executionId": execution, "bindingId": binding,
                        "packageSha256": next(row["package"]["sha256"] for row in history._inputs["bindings"]
                                              if row["bindingId"] == binding),
                        "inputSha256": evidence.digest(self.inputs), "testIdentity": identity,
                        "startedMs": start + 1, "endedMs": start + 2, "proofSha256": hashed,
                        "status": "Failed" if (binding, identity) == failed else "Passed"})
                    proofs["proof-" + execution + ".json"] = hashed
                    if (binding, identity) != missing_parent:
                        native_parent = profile == "artifacts" or identity in catalog.category_mutation_witnesses(
                            profile, corrected=True)
                        parents[execution] = (hashed if not native_parent else
                                              hashlib.sha256(("original-parent-" + str(sequence)).encode()).hexdigest())
                        if native_parent:
                            proofs["parent-" + execution + ".json"] = parents[execution]
            controls = {control: (hashlib.sha256(control.encode()).hexdigest(),)
                        for case in history._cases if case.binding_id != "none" and case.exclusion is None
                        for control in case.controls if control != missing_control}
            proofs.update({"control-" + hashlib.sha256(name.encode()).hexdigest() + ".json": hashes[0]
                           for name, hashes in controls.items()})
            imported = ("AssertionFailed" if failed else "None", tuple(witnesses), proofs, {}, {},
                        frozenset(), {}, parents, controls, history._proof_bytes + proof_bytes)
            with mock.patch.object(history, "_ingest_parts", return_value=imported), mock.patch.object(
                    evidence.time, "monotonic", return_value=(start + 3) / 1000):
                history.finish_joint(transports={})
            return {row["caseId"]: row for row in history.results() if row["bindingId"] == "none"}

        return history, finish

    def category_quality_report(self, history):
        return {
            "schemaVersion": 1, "catalogRevision": "f07-v1", "inputs": history._inputs,
            "postInputSha256": evidence.digest(history._inputs), "results": history.results(),
            "witnesses": history.witnesses, "resources": [], "proofs": history.proofs,
            "state": "Incomplete", "qualification": False, "scope": ["common-logical"],
        }

    def test_category_quality_reports_preserve_distinct_provider_package_provenance(self):
        for profile in ("metadata", "artifacts"):
            with self.subTest(profile=profile):
                self.setUp()
                history, finish = self.category_quality_fixture(profile=profile, distinct_packages=True)
                finish()
                report = self.category_quality_report(history)
                evidence.admit_entity("QualificationReport", report)
                changed = evidence.load_json(evidence.canonical_bytes(report))
                witness = changed["witnesses"][0]
                witness["packageSha256"] = next(
                    binding["package"]["sha256"] for binding in history._inputs["bindings"]
                    if binding["bindingId"] != witness["bindingId"])
                with self.assertRaises(evidence.ConformanceError):
                    evidence.admit_entity("QualificationReport", changed)

    def test_native_category_reports_recheck_original_history_inputs_and_proof_files(self):
        import conformance_sdk_checks as checks
        from types import SimpleNamespace

        publish = getattr(checks, "_category_report", None)
        self.assertTrue(callable(publish), "Native category evidence must pass real public report admission.")
        for profile in ("metadata", "artifacts"):
            for defect in (None, "free-space", "inputs", "history", "mutable-history", "proof", "shortened"):
                with self.subTest(profile=profile, defect=defect), tempfile.TemporaryDirectory() as temporary:
                    self.setUp()
                    history, finish = self.category_quality_fixture(profile=profile, distinct_packages=True)
                    finish()
                    root = Path(temporary).resolve()
                    (root / "proofs").mkdir()
                    originals = {hashlib.sha256(row["executionId"].encode()).hexdigest(): row["executionId"].encode()
                                 for row in history.witnesses}
                    originals[hashlib.sha256(b"original-parent-1").hexdigest()] = b"original-parent-1"
                    originals.update({hashlib.sha256(control.encode()).hexdigest(): control.encode()
                                      for case in history._cases for control in case.controls})
                    originals.update({hashlib.sha256(raw).hexdigest(): raw for raw in history.quality_proofs.values()})
                    for path, hashed in history.proofs.items():
                        checks.write_new(root / path, originals[hashed])
                    run = SimpleNamespace(root=root)
                    summary = checks._category_record(run, history._inputs, history, {}, "EvidenceIncomplete")
                    record_path = root / f"proofs/category-{profile}-qualification-history.json"
                    report_path = root / f"proofs/category-{profile}-qualification-report.json"
                    post = evidence.load_json(evidence.canonical_bytes(history._inputs))
                    if defect == "inputs":
                        post["runId"] = str(uuid.uuid4())
                    elif defect == "free-space":
                        post["environment"]["freeBytes"] += 1
                        post["environmentSha256"] = evidence.digest(post["environment"])
                    elif defect in ("history", "mutable-history", "shortened"):
                        record_path.chmod(0o600)
                        if defect == "history":
                            record_path.write_bytes(b"{}")
                            record_path.chmod(0o400)
                        elif defect == "shortened":
                            record = evidence.load_json(record_path.read_bytes())
                            record["results"].pop()
                            record["resultsSha256"] = evidence.digest(record["results"])
                            summary = {**summary, "resultsSha256": record["resultsSha256"]}
                            raw = evidence.canonical_bytes(record)
                            record_path.write_bytes(raw)
                            record_path.chmod(0o400)
                            summary["historySha256"] = hashlib.sha256(raw).hexdigest()
                    elif defect == "proof":
                        path = root / next(iter(history.proofs))
                        path.chmod(0o600)
                        path.write_bytes(b"replacement")
                    if defect not in (None, "free-space"):
                        with self.assertRaises(evidence.ConformanceError):
                            publish(run, history._inputs, post, summary)
                        self.assertFalse(report_path.exists())
                    else:
                        observed = publish(run, history._inputs, post, summary)
                        report = evidence.admit_entity("QualificationReport", evidence.load_json(report_path.read_bytes()))
                        self.assertEqual(observed["reportSha256"], evidence.file_sha256(report_path))
                        self.assertEqual(observed["reportState"], "Incomplete")
                        self.assertFalse(report["qualification"])
                        self.assertEqual(report["postInputSha256"], evidence.digest(post))
                        self.assertEqual(len(report["witnesses"]), len(history.witnesses))
                        self.assertEqual(dict(report["proofs"]), dict(history.proofs))

    def test_metadata_quality_reuses_complete_same_attempt_runtime_and_controller_provenance(self):
        history, finish = self.category_quality_fixture()
        qualities = finish()
        for identity in ("QC-06", "QC-07", "QC-08"):
            with self.subTest(identity=identity):
                result = qualities[identity]
                self.assertEqual("Passed", result["status"])
                attempt = result["attempts"][0]
                self.assertTrue(attempt["witnessIds"])
                selected = [row for row in history.witnesses if row["executionId"] in attempt["witnessIds"]]
                self.assertEqual(len(selected), len(attempt["witnessIds"]))
                self.assertEqual({"sqlite", "memory"}, {row["bindingId"] for row in selected})
                self.assertTrue({row["proofSha256"] for row in selected} <= set(attempt["proofSha256"]))
                self.assertLessEqual(len(attempt["proofSha256"]), evidence.MAX_WITNESSES)
        self.assertEqual("Incomplete", qualities["QC-02"]["status"])
        self.assertEqual("Passed", qualities["QC-04"]["status"])
        self.assertEqual("Incomplete", qualities["QC-05"]["status"])
        evidence.admit_entity("QualificationReport", self.category_quality_report(history))

    def test_metadata_quality_diagnostic_missing_control_and_failed_basis_do_not_become_passes(self):
        history, finish = self.category_quality_fixture(mode="diagnostic")
        self.assertTrue(all(row["status"] == "Incomplete" for row in finish().values()))
        self.setUp()
        history, finish = self.category_quality_fixture()
        self.assertEqual("Incomplete", finish(missing_control="parent-kill:U3")["QC-08"]["status"])
        self.setUp()
        history, finish = self.category_quality_fixture(max_attempts=2)
        failed = next(identity for identity in history.expected_runtime_tests("memory")
                      if ".MP15_Lost_acknowledgment_" in identity)
        first = finish(failed=("memory", failed))
        self.assertEqual("Failed", first["QC-07"]["status"])
        self.assertEqual("AssertionFailed", first["QC-07"]["attempts"][0]["diagnosticCode"])
        first_attempt = first["QC-07"]["attempts"][0]
        with self.assertRaisesRegex(evidence.ConformanceError, "OutputLimitExceeded"):
            finish(2)
        second = next(row for row in history.results() if row["caseId"] == "QC-07")
        self.assertEqual("Incomplete", second["status"])
        self.assertEqual("OutputLimitExceeded", second["attempts"][1]["diagnosticCode"])
        self.assertEqual(first_attempt, second["attempts"][0])
        evidence.admit_entity("QualificationReport", self.category_quality_report(history))

    def test_metadata_quality_report_rejects_shortened_foreign_and_borrowed_durability_provenance(self):
        history, finish = self.category_quality_fixture()
        self.assertEqual("Passed", finish()["QC-08"]["status"])
        original = evidence.load_json(evidence.canonical_bytes(self.category_quality_report(history)))
        for defect in ("missing-case", "missing-witness", "shortened-basis", "foreign-witness", "wrong-sequence",
                       "wrong-exclusion", "logical-exclusion", "unrelated-quality"):
            with self.subTest(defect=defect):
                report = copy.deepcopy(original)
                quality = next(row for row in report["results"] if row["caseId"] == "QC-08")
                basis = next(row for row in report["results"]
                             if row["bindingId"] == "sqlite" and row["caseId"] == "MP-38")
                if defect == "missing-case":
                    report["results"].remove(basis)
                elif defect == "missing-witness":
                    quality["attempts"][0]["witnessIds"].pop()
                elif defect == "shortened-basis":
                    basis["attempts"][0]["witnessIds"].clear()
                elif defect == "foreign-witness":
                    foreign = next(row for row in history.witnesses if ".MP02_" in row["testIdentity"])
                    quality["attempts"][0]["witnessIds"].append(foreign["executionId"])
                    quality["attempts"][0]["proofSha256"].append(foreign["proofSha256"])
                    quality["proofSha256"].append(foreign["proofSha256"])
                elif defect == "wrong-sequence":
                    basis["attempts"][0]["startedMs"] = 8
                elif defect == "wrong-exclusion":
                    excluded = next(row for row in report["results"]
                                    if row["bindingId"] == "memory" and row["caseId"] == "MP-38")
                    excluded["exclusionRule"] = "simulation-no-durable-restart"
                elif defect == "logical-exclusion":
                    basis.update(status="NotApplicable", applicable=False, exclusionRule="non-durable-fixture",
                                 attempts=[], proofSha256=[])
                else:
                    quality["caseId"] = "QC-99"
                with self.assertRaises(evidence.ConformanceError):
                    evidence.admit_entity("QualificationReport", report)

    def test_authority_quality_preserves_complete_current_rows_and_failed_retries(self):
        import conformance_case_catalog as catalog
        history, finish = self.category_quality_fixture(profile="artifacts", max_attempts=3)
        first = finish()["QC-12"]
        self.assertEqual(first["status"], "Passed")
        self.assertEqual(len(first["attempts"][0]["witnessIds"]), 32)
        selected = {row["testIdentity"] for row in history.witnesses
                    if row["executionId"] in first["attempts"][0]["witnessIds"]}
        self.assertEqual(selected, set(catalog.authority_integration_witnesses()))
        identity = catalog.authority_integration_witnesses()[0]
        binding = catalog.AUTHORITY_INTEGRATION_ROWS[identity][0]
        second = finish(2, failed=(binding, identity))
        self.assertEqual(second["QC-12"]["status"], "Failed")
        self.assertEqual(second["QC-12"]["attempts"][-1]["diagnosticCode"], "AssertionFailed")
        self.assertEqual(second["QC-09"]["status"], "Passed")
        third = finish(3)["QC-12"]
        self.assertEqual([attempt["status"] for attempt in third["attempts"]], ["Passed", "Failed", "Passed"])
        evidence.admit_entity("QualificationReport", self.category_quality_report(history))

    def test_mutation_quality_requires_current_complete_paired_source_and_retains_failed_repairs(self):
        import conformance_case_catalog as catalog
        for profile in ("metadata", "artifacts"):
            self.setUp()
            _, finish = self.category_quality_fixture(profile=profile)
            selected = catalog.category_mutation_witnesses(profile, corrected=True)
            identity = next(iter(selected))
            first = finish(missing_parent=(selected[identity], identity))["QC-04"]
            self.assertEqual(first["status"], "Incomplete")
            self.setUp()
            history, finish = self.category_quality_fixture(profile=profile)
            self.assertEqual(finish()["QC-04"]["status"], "Passed")
            evidence.admit_entity("QualificationReport", self.category_quality_report(history))
        self.setUp()
        history, finish = self.category_quality_fixture(profile="artifacts", max_attempts=2)
        identity, binding = next(iter(catalog.category_mutation_witnesses("artifacts", corrected=True).items()))
        self.assertEqual(finish(failed=(binding, identity))["QC-04"]["status"], "Failed")
        repaired = finish(2)["QC-04"]
        self.assertEqual([attempt["status"] for attempt in repaired["attempts"]], ["Failed", "Passed"])
        self.assertEqual(len(repaired["attempts"][-1]["witnessIds"]), 2)
        evidence.admit_entity("QualificationReport", self.category_quality_report(history))

    def test_authority_quality_rejects_missing_borrowed_or_retimed_integration_rows(self):
        import conformance_case_catalog as catalog
        missing = catalog.authority_integration_witnesses()[0]
        history, finish = self.category_quality_fixture(profile="artifacts", max_attempts=2, distinct_packages=True)
        self.assertEqual(finish(missing_integration=missing)["QC-12"]["status"], "Incomplete")
        self.assertEqual(finish(2)["QC-12"]["status"], "Passed")
        report = self.category_quality_report(history)
        evidence.admit_entity("QualificationReport", report)
        for mutation in ("shortened", "borrowed", "retimed"):
            changed = json.loads(evidence.canonical_bytes(report))
            quality = next(row for row in changed["results"] if row["caseId"] == "QC-12")
            attempt = quality["attempts"][-1]
            witness = next(row for row in changed["witnesses"] if row["executionId"] == attempt["witnessIds"][0])
            if mutation == "shortened":
                changed["witnesses"].remove(witness)
                attempt["witnessIds"].remove(witness["executionId"])
                attempt["proofSha256"].remove(witness["proofSha256"])
                quality["proofSha256"] = sorted({
                    hashed for retained in quality["attempts"] for hashed in retained["proofSha256"]})
            elif mutation == "borrowed":
                witness["bindingId"] = "object" if witness["bindingId"] == "local" else "local"
                witness["packageSha256"] = next(row["package"]["sha256"] for row in changed["inputs"]["bindings"]
                                                if row["bindingId"] == witness["bindingId"])
            else:
                witness["startedMs"] = attempt["startedMs"] - 1
                witness["endedMs"] = attempt["startedMs"] - 0.5
            with self.subTest(mutation=mutation), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("QualificationReport", changed)
        changed = json.loads(evidence.canonical_bytes(report))
        quality = next(row for row in changed["results"] if row["caseId"] == "QC-12")
        current = quality["attempts"][-1]
        current["witnessIds"] = quality["attempts"][0]["witnessIds"]
        executions = {row["executionId"]: row for row in changed["witnesses"]}
        for execution in current["witnessIds"]:
            executions[execution].update(startedMs=current["startedMs"], endedMs=current["startedMs"])
        results = {(row["profileId"], row["bindingId"], row["matrixId"], row["caseId"]): row
                   for row in changed["results"]}
        with self.assertRaisesRegex(evidence.ConformanceError, "ProofMismatch"):
            evidence._category_quality_composition(
                changed["inputs"], "QC-12", results, executions, sequence=current["sequence"],
                started_ms=current["startedMs"], ended_ms=current["endedMs"])
        self.setUp()
        _, complete = self.category_quality_fixture(profile="artifacts")
        binding = catalog.AUTHORITY_INTEGRATION_ROWS[missing][0]
        self.assertEqual(complete(missing_parent=(binding, missing))["QC-12"]["status"], "Incomplete")

    def test_artifact_transfer_and_durability_quality_require_exact_current_original_sources(self):
        import conformance_case_catalog as catalog
        history, finish = self.category_quality_fixture(profile="artifacts")
        qualities = finish()
        for identity, bindings in (("QC-10", {"local", "object"}), ("QC-11", {"local"})):
            with self.subTest(identity=identity):
                result = qualities[identity]
                self.assertEqual(result["status"], "Passed")
                attempt = result["attempts"][0]
                selected = [row for row in history.witnesses if row["executionId"] in attempt["witnessIds"]]
                self.assertEqual({row["bindingId"] for row in selected}, bindings)
                self.assertTrue({row["proofSha256"] for row in selected} < set(attempt["proofSha256"]))
                self.assertLessEqual(len(attempt["proofSha256"]), evidence.MAX_WITNESSES)
        for identity in ("QC-03", "QC-05"):
            self.assertEqual(qualities[identity]["status"], "Incomplete")
        excluded = [row for row in history.results() if row["bindingId"] == "object"
                    and row["caseId"] in ("AS-41", "AS-42", "AS-43", "AS-44")]
        self.assertEqual(len(excluded), 4)
        self.assertTrue(all(row["status"] == "NotApplicable" and row["attempts"] == ()
                            and row["exclusionRule"] == "simulation-no-durable-restart" for row in excluded))
        evidence.admit_entity("QualificationReport", self.category_quality_report(history))
        transfer = next(identity for identity, source in catalog.ORIGINAL_ARTIFACT_PROOF_SOURCES.items()
                        if source == ("transfer", "local", 268435456))
        for mode, missing in (("diagnostic", None), ("qualification", ("local", transfer))):
            self.setUp()
            history, finish = self.category_quality_fixture(profile="artifacts", mode=mode)
            observed = finish(missing_parent=missing)
            self.assertEqual(observed["QC-10"]["status"], "Incomplete")
            self.assertEqual(observed["QC-11"]["status"], "Passed" if missing else "Incomplete")

    def test_artifact_durability_quality_preserves_failed_attempts_and_rejects_borrowed_provenance(self):
        import conformance_case_catalog as catalog
        history, finish = self.category_quality_fixture(profile="artifacts", max_attempts=2)
        crash = next(identity for identity, source in catalog.ORIGINAL_ARTIFACT_PROOF_SOURCES.items()
                     if source[0] == "crash")
        first = finish(failed=("local", crash))["QC-11"]["attempts"][0]
        self.assertEqual(first["status"], "Failed")
        self.assertEqual(first["diagnosticCode"], "AssertionFailed")
        second = finish(2)["QC-11"]
        self.assertEqual(second["status"], "Passed")
        self.assertEqual(second["attempts"][0], first)
        self.assertEqual(len(second["attempts"]), 2)
        original = evidence.load_json(evidence.canonical_bytes(self.category_quality_report(history)))
        evidence.admit_entity("QualificationReport", original)
        for defect in ("missing-case", "missing-witness", "shortened-basis", "foreign-witness",
                       "wrong-sequence", "wrong-exclusion", "logical-exclusion", "missing-source-parent"):
            report = copy.deepcopy(original)
            quality = next(row for row in report["results"] if row["caseId"] == "QC-11")
            basis = next(row for row in report["results"] if row["bindingId"] == "local" and row["caseId"] == "AS-41")
            if defect == "missing-case":
                report["results"].remove(basis)
            elif defect == "missing-witness":
                quality["attempts"][1]["witnessIds"].pop()
            elif defect == "shortened-basis":
                basis["attempts"][1]["witnessIds"].clear()
            elif defect == "foreign-witness":
                foreign = next(row for row in history.witnesses if row["bindingId"] == "object")
                quality["attempts"][1]["witnessIds"].append(foreign["executionId"])
                quality["attempts"][1]["proofSha256"].append(foreign["proofSha256"])
                quality["proofSha256"].append(foreign["proofSha256"])
            elif defect == "wrong-sequence":
                basis["attempts"][1]["startedMs"] = 8
            elif defect == "wrong-exclusion":
                excluded = next(row for row in report["results"]
                                if row["bindingId"] == "object" and row["caseId"] == "AS-41")
                excluded["exclusionRule"] = "non-durable-fixture"
            elif defect == "missing-source-parent":
                own = {row["proofSha256"] for row in report["witnesses"]
                       if row["executionId"] in basis["attempts"][1]["witnessIds"]}
                basis["attempts"][1]["proofSha256"] = sorted(own)
            else:
                basis.update(status="NotApplicable", applicable=False, exclusionRule="simulation-no-durable-restart",
                             attempts=[], proofSha256=[])
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("QualificationReport", report)

    def test_artifact_logical_quality_retains_complete_basis_without_truncating_direct_witnesses(self):
        import conformance_case_catalog as catalog
        history, finish = self.category_quality_fixture(profile="artifacts", max_attempts=2)
        quality = finish()["QC-09"]
        self.assertEqual(quality["status"], "Passed", "Complete artifact logical closure must derive QC-09.")
        packets = dict(history.quality_proofs)
        self.assertEqual(len(packets), 1)
        path, raw = next(iter(packets.items()))
        packet = evidence.load_json(raw)
        required = {case.key for case in catalog.category_cases() if case.profile_id == "artifacts"
                    and int(case.case_id[3:]) not in (11, 12, 41, 42, 43, 44)}
        self.assertEqual({tuple(row["key"]) for row in packet["basis"]}, required)
        expected = {execution for row in packet["basis"] for execution in row["attempt"]["witnessIds"]}
        self.assertGreater(len(expected), evidence.MAX_WITNESSES)
        self.assertEqual({row["executionId"] for row in packet["witnesses"]}, expected)
        self.assertLessEqual(len(quality["attempts"][0]["witnessIds"]), evidence.MAX_WITNESSES)
        self.assertLessEqual(len(quality["attempts"][0]["proofSha256"]), evidence.MAX_WITNESSES)
        self.assertEqual(history.proofs[path], hashlib.sha256(raw).hexdigest())
        with self.assertRaises(TypeError):
            history.quality_proofs[path] = b"replacement"
        self.assertIn(history.proofs[path], quality["attempts"][0]["proofSha256"])
        evidence.admit_entity("QualificationReport", self.category_quality_report(history))
        self.assertEqual(finish(2)["QC-09"]["status"], "Passed")
        self.assertEqual(history.quality_proofs[path], raw)
        self.assertEqual(len(history.quality_proofs), 2)
        original = evidence.load_json(evidence.canonical_bytes(self.category_quality_report(history)))
        evidence.admit_entity("QualificationReport", original)
        for defect in ("missing-basis-packet", "changed-basis-packet", "missing-case", "shortened-case",
                       "foreign-anchor", "changed-original-attempt"):
            report = copy.deepcopy(original)
            result = next(row for row in report["results"] if row["caseId"] == "QC-09")
            basis = next(row for row in report["results"] if row["bindingId"] == "local" and row["caseId"] == "AS-01")
            if defect == "missing-basis-packet":
                del report["proofs"][path]
            elif defect == "changed-basis-packet":
                report["proofs"][path] = "0" * 64
            elif defect == "missing-case":
                report["results"].remove(basis)
            elif defect == "shortened-case":
                basis["attempts"][1]["witnessIds"].clear()
            elif defect == "foreign-anchor":
                foreign = next(row for row in report["witnesses"]
                               if row["executionId"] in basis["attempts"][1]["witnessIds"])
                result["attempts"][1]["witnessIds"].append(foreign["executionId"])
                result["attempts"][1]["proofSha256"].append(foreign["proofSha256"])
                result["proofSha256"].append(foreign["proofSha256"])
            else:
                basis["attempts"][0]["endedMs"] = 10.5
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                evidence.admit_entity("QualificationReport", report)

    def test_artifact_logical_quality_basis_budget_rejection_is_atomic_and_failed_history_survives(self):
        history, finish = self.category_quality_fixture(profile="artifacts", max_attempts=2)
        identity = next(identity for identity in history.expected_runtime_tests("local")
                        if ".Empty_content_and_true_absence_" in identity)
        first = finish(failed=("local", identity))["QC-09"]
        self.assertEqual(first["status"], "Failed", "QC-09 must preserve the actual failed logical basis.")
        packets = dict(history.quality_proofs)
        self.assertEqual(finish(2)["QC-09"]["attempts"][0], first["attempts"][0])
        evidence.admit_entity("QualificationReport", self.category_quality_report(history))
        self.assertTrue(all(history.quality_proofs[path] == raw for path, raw in packets.items()))
        self.setUp()
        history, finish = self.category_quality_fixture(profile="artifacts")
        with self.assertRaisesRegex(evidence.ConformanceError, "OutputLimitExceeded"):
            finish(proof_bytes=evidence.MAX_PROOF_BYTES)
        self.assertFalse(history.quality_proofs)
        self.assertFalse(history.proofs)
        self.assertTrue(all(row["status"] == "Incomplete" for row in history.results()
                            if row["applicable"]))

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
            actual.update({f'runtime-{scope["attemptId"]}/{name}': hashlib.sha256(raw).hexdigest()
                           for name, raw in transports[scope_id]["proofs"].items()})
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
            actual_proofs.update({f'runtime-{scope["attemptId"]}/{path}': hashlib.sha256(data).hexdigest()
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
        attempt = evidence.load_json(transports["failed"]["manifest_data"])["attemptId"]
        self.assertEqual(history.proofs[f'runtime-{attempt}/proof-{failed_witness["executionId"]}.json'],
                         failed_witness["proofSha256"])

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
                self.assertEqual(actual, set() if case.binding_id == "none" else set(case.witnesses))
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

    def test_native_artifact_controller_admission_binds_settings_inputs_output_and_original_command(self):
        import conformance_case_catalog as catalog
        import conformance_sources as sources
        from xml.sax.saxutils import escape

        self.category_history(profile="artifacts", mode="qualification")
        assembly_path = "candidate/Hoard.Artifacts.Tests.dll"
        crash_path = ("candidate/tests/fixtures/artifacts/CrashRunner/bin/Release/net10.0/"
                      "Hoard.Fixtures.Artifacts.CrashRunner.dll")
        self.inputs["runtimeAssemblies"] = {
            assembly_path: "e" * 64, crash_path: hashlib.sha256(b"original-crash-runner").hexdigest()}
        self.manifest["assemblies"][0]["path"] = assembly_path
        tests = {identity: (binding, catalog.category_runtime_cases("artifacts", binding)[identity])
                 for binding, identity in catalog.category_execution_partitions("artifacts")["controller"]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            def write(path, raw):
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    path.chmod(0o600)
                path.write_bytes(raw)
                path.chmod(0o400)

            write(root / crash_path, b"original-crash-runner")
            write(root / "stores/candidate.NuGet.Config", evidence.synthetic_nuget_configuration(root / "feed/candidate"))
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
            transport = self.category_transport(None, selections=tests)
            options = {**transport, "inputs": self.inputs,
                       "expected_tests": {identity: (binding, "none") for identity, (binding, _) in tests.items()},
                       "started_ms": 0, "ended_ms": 20}
            observed = evidence.inspect_runtime_attempt(**options)["observation"]
            manifest = evidence.load_json(transport["manifest_data"])
            run = object.__new__(sources.OwnedRun)
            run.root, run.run_id, run.root_id = root, self.inputs["runId"], self.owner["rootId"]
            run.command_sequence, run.live_children = 99, lambda: frozenset()
            write(root / "runtime-owner.json", transport["owner_data"])
            write(root / f"runtime-input-{self.attempt}.json", transport["manifest_data"])
            write(root / manifest["runInputsPath"], evidence.canonical_bytes(self.inputs))
            context = sources.artifact_source_context(
                run, self.inputs, manifest, namespace="qualification-artifact-transfers")
            context_path = f"stores/artifact-source-context-{self.attempt}.json"
            write(root / context_path, evidence.canonical_bytes(context))
            variables = {
                "HOARD_ARTIFACT_CRASH_RUNNER": str(root / crash_path),
                "HOARD_ARTIFACT_CRASH_PROOFS": str(root / "stores" / ("original-artifact-" + self.attempt)),
                "HOARD_ARTIFACT_TRANSFER_PROOFS": str(root / "proofs/qualification-artifact-transfers"),
                "HOARD_ARTIFACT_RUN_ID": run.run_id,
                "HOARD_ARTIFACT_SOURCE_CONTEXT": str(root / context_path)}
            environment = "<EnvironmentVariables>" + "".join(
                f"<{key}>{escape(value)}</{key}>" for key, value in variables.items()) + "</EnvironmentVariables>"
            settings = root / "stores" / f"settings-{self.attempt}.runsettings"
            settings_raw = sources.runtime_settings(
                root, root / assembly_path, self.attempt, evidence.digest(manifest), evidence.digest(self.owner), environment)
            write(settings, settings_raw)
            facts = [{
                "testIdentity": row["testIdentity"], "executionId": row["executionId"],
                "runtimeProofSha256": row["proofSha256"], "sourceProofs": {"producer": "a" * 64}}
                for row in observed["witnesses"]]
            source_raw = evidence.canonical_bytes({"observations": facts})
            source_path = f"proofs/original-artifact-external-{self.attempt}.json"
            seal_path = f"proofs/artifact-source-seal-{self.attempt}.json"
            graph = {
                "proofs/qualification-artifact-transfers.json": b"original-summary",
                **{f"proofs/qualification-artifact-transfers/transfer-{provider}-{size}/proof.json":
                   f"original-{provider}-{size}".encode()
                   for provider in ("local", "object") for size in (268435456, 4294967296)},
                source_path: source_raw, seal_path: b"original-source-index"}
            packets = {f"proofs/source-artifact-{self.attempt}-packet.json": b"original-capture"}
            for path, raw in graph.items():
                write(root / path, raw)
            record = {
                "schemaVersion": 1, "sequence": 17, "childPid": 123, "childStartSha256": "a" * 64,
                "startedMs": 9, "endedMs": 12, "exitCode": 0, "diagnosticCode": "None",
                "groupState": "Exited", "scope": "ordinary", "runId": run.run_id, "rootId": run.root_id,
                "argvSha256": evidence.digest(sources.runtime_arguments(root / assembly_path, settings, tuple(tests))),
                "cwdSha256": hashlib.sha256(str((root / assembly_path).parent).encode()).hexdigest(),
                "inputFiles": {
                    f"runtime-input-{self.attempt}.json": evidence.digest(manifest),
                    "runtime-owner.json": evidence.digest(self.owner),
                    manifest["runInputsPath"]: evidence.digest(self.inputs),
                    settings.relative_to(root).as_posix(): hashlib.sha256(settings_raw).hexdigest(),
                    assembly_path: "e" * 64, context_path: evidence.digest(context),
                    crash_path: self.inputs["runtimeAssemblies"][crash_path],
                    **{path: hashlib.sha256(raw).hexdigest() for path, raw in graph.items()
                       if path.startswith("proofs/qualification-artifact-transfers")}},
                "outputFiles": {seal_path: hashlib.sha256(graph[seal_path]).hexdigest()}}
            native = sources.NativeCategorySources(
                run, inspection_inputs=selected, inspection_configurations=configurations)
            for defect in (None, "argv", "cwd", "input", "output", "witness-window", "source-failure"):
                changed = copy.deepcopy(record)
                if defect in ("argv", "cwd"):
                    changed[defect + "Sha256"] = "0" * 64
                elif defect == "input":
                    changed["inputFiles"].pop(crash_path)
                elif defect == "output":
                    changed["outputFiles"][seal_path] = "0" * 64
                elif defect == "witness-window":
                    changed["endedMs"] = 9.5
                run.read_execution_record = mock.Mock(return_value=evidence.canonical_bytes(changed))
                execution = {
                    "schemaVersion": 1, "qualification": False, "nativeContainment": True,
                    "runId": run.run_id, "rootId": run.root_id, "invocationGroupId": self.inputs["invocationGroupId"],
                    "attemptId": self.attempt, "purpose": "execution", "commandSequence": 17,
                    "inputsSha256": evidence.digest(self.inputs), "executionRecordSha256": evidence.digest(changed),
                    "manifestSha256": evidence.digest(manifest), "settingsSha256": hashlib.sha256(settings_raw).hexdigest()}
                parent = {
                    "schemaVersion": 1, "qualification": False, "nativeContainment": True,
                    "profileId": "artifacts", "scopeId": "controller", "runId": run.run_id,
                    "invocationGroupId": self.inputs["invocationGroupId"], "attemptId": self.attempt,
                    "inputsSha256": evidence.digest(self.inputs), "manifestSha256": evidence.digest(manifest),
                    "commandSequence": 17, "executionParentSha256": evidence.digest(execution),
                    "sourceReceiptSha256": hashlib.sha256(source_raw).hexdigest(),
                    "observations": sorted(
                        ({**row, "bindingId": tests[row["testIdentity"]][0], "caseId": tests[row["testIdentity"]][1]}
                         for row in facts), key=lambda row: row["testIdentity"])}
                write(root / f"proofs/category-command-{self.attempt}-execution.json", evidence.canonical_bytes(execution))
                write(root / f"proofs/category-source-{self.attempt}.json", evidence.canonical_bytes(parent))
                with self.subTest(defect=defect), mock.patch.object(
                        sources, "native_artifact_controller_source",
                        side_effect=evidence.ConformanceError("ProofMismatch") if defect == "source-failure" else None,
                        return_value={"sourceReceipt": source_raw, "sourceProofs": graph, "sourcePackets": packets}) as authority, \
                        mock.patch.object(sources, "native_hook_admission_control", return_value={
                            "controls": {"hook-admission-sdk-consumer": ("c" * 64,)},
                            "sourceProofs": {"proofs/isolated-hook-control.json": b"isolated-hook-control"}}) as hooks:
                    if defect:
                        with self.assertRaises(evidence.ConformanceError):
                            native.ingest_attempt(category_scope=("artifacts", "controller"), **options)
                    else:
                        admitted = native.ingest_attempt(category_scope=("artifacts", "controller"), **options)
                        self.assertEqual(set(admitted["sourceParents"].values()), {evidence.digest(parent)})
                        self.assertEqual(len(record["inputFiles"]), 12)
                        for path, raw in packets.items():
                            self.assertEqual((root / path).read_bytes(), raw)
                        history = evidence.CategoryRuntimeHistory(self.inputs, native_sources=native)
                        result = history._ingest_parts(
                            {"controller": {"attemptId": self.attempt, "tests": tests}},
                            {"controller": transport}, 0, 20, 1)
                        self.assertEqual(set(result[7].values()), {evidence.digest(parent)})
                        self.assertIn(seal_path, result[2])
                        self.assertIn("proofs/isolated-hook-control.json", result[2])
                        self.assertEqual(result[8], {"hook-admission-sdk-consumer": ("c" * 64,)})
                        hooks.assert_called_once_with(run, history._inputs, started_ms=0, ended_ms=20)
                        self.assertEqual(authority.call_args.kwargs,
                                         {"sequence": 17, "started_ms": 0, "ended_ms": 20})
                        run.read_execution_record.assert_called_with(17)

    def test_native_authority_integration_rechecks_images_and_original_command_closure(self):
        import base64
        import conformance_case_catalog as catalog
        import conformance_sources as sources
        from types import SimpleNamespace

        self.category_history(profile="artifacts", mode="qualification", distinct_packages=True)
        assembly_path = ("candidate/tests/fixtures/conformance/Consumer/bin/package-diagnostic/Release/net10.0/"
                         "Hoard.Fixtures.Conformance.Consumer.dll")
        directory = Path(assembly_path).parent
        packages = {(category, binding): package for category, binding, _, package in catalog.CATEGORY_BINDING_SLOTS}
        image_packages = (*packages.values(), "Hoard.Fixtures.Artifacts.HostAdapters")
        images = {assembly_path: hashlib.sha256(b"consumer").hexdigest(),
                  **{(directory / (package + ".dll")).as_posix(): hashlib.sha256(package.encode()).hexdigest()
                     for package in image_packages}}
        self.inputs["runtimeAssemblies"] = images
        template = self.inputs["packages"][0]
        captured_packages = {package["packageId"]: package for package in self.inputs["packages"]}
        self.inputs["packages"] = [{**captured_packages.get(package, template), "packageId": package,
                                   "runtimeAssemblies": {"lib/net10.0/" + package + ".dll":
                                                        images[(directory / (package + ".dll")).as_posix()]}}
                                  for package in image_packages]
        for binding in self.inputs["bindings"]:
            binding["package"] = next(package for package in self.inputs["packages"]
                                      if package["packageId"] == binding["package"]["packageId"])
        self.manifest["assemblies"][0].update(path=assembly_path, sha256=images[assembly_path])
        self.manifest["assemblies"].extend(
            {"id": "component-" + str(index), "path": path, "sha256": hashed}
            for index, (path, hashed) in enumerate(images.items()) if path != assembly_path)
        tests = {identity: (binding, "QC-12") for identity, (binding, _, _) in catalog.AUTHORITY_INTEGRATION_ROWS.items()}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            def write(path, raw):
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    path.chmod(0o600)
                path.write_bytes(raw)
                path.chmod(0o400)

            for path in images:
                write(root / path, b"consumer" if path == assembly_path else Path(path).stem.encode())
            write(root / "stores/candidate.NuGet.Config", evidence.synthetic_nuget_configuration(root / "feed/candidate"))
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
            transport = self.category_transport(None, selections=tests)
            manifest = evidence.load_json(transport["manifest_data"])
            witnesses = [evidence.load_json(line) for line in transport["witnesses_data"].splitlines()]
            observed = {"diagnosticCode": "None", "attemptId": self.attempt, "witnesses": witnesses,
                        "proofs": {path: hashlib.sha256(raw).hexdigest() for path, raw in transport["proofs"].items()},
                        "sessionOrigins": {row["executionId"]: () for row in witnesses}, "originalObservations": {}}
            for row in witnesses:
                binding, metadata, _ = catalog.AUTHORITY_INTEGRATION_ROWS[row["testIdentity"]]
                selected_images = (packages["metadata", metadata], packages["artifacts", binding],
                                   "Hoard.Fixtures.Artifacts.HostAdapters")
                observed["originalObservations"][row["executionId"]] = tuple({
                    "kind": "loaded-contract", "operation": "contract", "parentObservationId": None,
                    "components": {"contract": {"assemblySha256": images[(directory / (package + ".dll")).as_posix()]}}}
                    for package in selected_images)
            run = SimpleNamespace(root=root, run_id=self.inputs["runId"], root_id=self.owner["rootId"],
                                  command_sequence=1, live_children=lambda: ())
            native = object.__new__(sources.NativeCategorySources)
            native._run, native._selected = run, selected
            facts = sources.authority_integration_observations(run, self.inputs, manifest, observed)
            receipt = {"schemaVersion": 1, "qualification": False, "mode": "category-artifacts-original-integration",
                       "runId": run.run_id, "invocationGroupId": self.inputs["invocationGroupId"],
                       "attemptId": self.attempt, "inputsSha256": evidence.digest(self.inputs), "observations": facts}
            write(root / f'proofs/{receipt["mode"]}-{self.attempt}.json', evidence.canonical_bytes(receipt))
            write(root / "runtime-owner.json", transport["owner_data"])
            write(root / f"runtime-input-{self.attempt}.json", transport["manifest_data"])
            write(root / manifest["runInputsPath"], evidence.canonical_bytes(self.inputs))
            context = {"schemaVersion": 1, "runId": run.run_id, "cases": {
                entry["testIdentity"]: {"caseId": entry["caseId"], "bindingId": entry["bindingId"]}
                for entry in manifest["expected"]}}
            environment = ("<EnvironmentVariables><HOARD_ORIGINAL_CONTEXT>"
                           + base64.b64encode(evidence.canonical_bytes(context)).decode()
                           + "</HOARD_ORIGINAL_CONTEXT></EnvironmentVariables>")
            assembly, settings = root / assembly_path, root / "stores" / f"settings-{self.attempt}.runsettings"
            settings_raw = sources.runtime_settings(
                root, assembly, self.attempt, evidence.digest(manifest), evidence.digest(self.owner), environment)
            write(settings, settings_raw)
            record = {
                "schemaVersion": 1, "sequence": 1, "childPid": 123, "childStartSha256": "a" * 64,
                "startedMs": 9, "endedMs": 12, "exitCode": 0, "diagnosticCode": "None",
                "groupState": "Exited", "scope": "ordinary", "runId": run.run_id, "rootId": run.root_id,
                "argvSha256": evidence.digest(sources.runtime_arguments(assembly, settings, tuple(tests))),
                "cwdSha256": hashlib.sha256(str(assembly.parent).encode()).hexdigest(),
                "inputFiles": {f"runtime-input-{self.attempt}.json": evidence.digest(manifest),
                               "runtime-owner.json": evidence.digest(self.owner),
                               manifest["runInputsPath"]: evidence.digest(self.inputs),
                               settings.relative_to(root).as_posix(): hashlib.sha256(settings_raw).hexdigest(), **images}}
            original = evidence.canonical_bytes(record)
            run.read_execution_record = mock.Mock(return_value=original)
            write(root / "proofs/execution-command-0001.json", original)
            execution = {
                "schemaVersion": 1, "qualification": False, "nativeContainment": True,
                "runId": run.run_id, "rootId": run.root_id, "invocationGroupId": self.inputs["invocationGroupId"],
                "attemptId": self.attempt, "purpose": "execution", "commandSequence": 1,
                "inputsSha256": evidence.digest(self.inputs), "executionRecordSha256": evidence.digest(record),
                "manifestSha256": evidence.digest(manifest), "settingsSha256": hashlib.sha256(settings_raw).hexdigest()}
            parent = {
                "schemaVersion": 1, "qualification": False, "nativeContainment": True, "profileId": "artifacts",
                "scopeId": "original-integration", "runId": run.run_id,
                "invocationGroupId": self.inputs["invocationGroupId"], "attemptId": self.attempt,
                "inputsSha256": evidence.digest(self.inputs), "manifestSha256": evidence.digest(manifest),
                "commandSequence": 1, "executionParentSha256": evidence.digest(execution),
                "sourceReceiptSha256": evidence.digest(receipt),
                "observations": [{**row, "bindingId": tests[row["testIdentity"]][0], "caseId": "QC-12"} for row in facts]}
            execution_path = root / f"proofs/category-command-{self.attempt}-execution.json"
            parent_path = root / f"proofs/category-source-{self.attempt}.json"

            def admit():
                return native._corroborate(
                    self.inputs, manifest, observed, category_scope=("artifacts", "original-integration"),
                    manifest_data=transport["manifest_data"], owner_data=transport["owner_data"],
                    started_ms=9, ended_ms=12)

            write(execution_path, evidence.canonical_bytes(execution))
            write(parent_path, evidence.canonical_bytes(parent))
            self.assertEqual(set(admit()["sourceParents"]), {row["executionId"] for row in witnesses})
            for mutation in ("argv", "inputs", "cwd", "exit", "time", "sequence", "replaced-record", "settings",
                             "missing-row", "missing-image", "borrowed-image"):
                changed = copy.deepcopy(record)
                if mutation in ("argv", "cwd"):
                    changed[mutation + "Sha256"] = "0" * 64
                elif mutation == "inputs":
                    changed["inputFiles"].pop(next(path for path in images if path != assembly_path))
                elif mutation == "exit":
                    changed["exitCode"] = 1
                elif mutation == "time":
                    changed["startedMs"] = 8
                elif mutation == "sequence":
                    changed["sequence"] = 2
                elif mutation == "settings":
                    write(settings, settings_raw + b" ")
                elif mutation == "missing-row":
                    observed["witnesses"] = witnesses[:-1]
                elif mutation in ("missing-image", "borrowed-image"):
                    first = witnesses[0]["executionId"]
                    nodes = observed["originalObservations"][first]
                    observed["originalObservations"][first] = nodes[:-1] if mutation == "missing-image" else (
                        nodes[1], nodes[0], nodes[2])
                raw = evidence.canonical_bytes(changed)
                run.read_execution_record.return_value = original if mutation == "replaced-record" else raw
                if mutation == "replaced-record":
                    raw = evidence.canonical_bytes({**record, "childPid": 456})
                    write(root / "proofs/execution-command-0001.json", raw)
                changed_execution = {**execution, "executionRecordSha256": hashlib.sha256(raw).hexdigest()}
                write(execution_path, evidence.canonical_bytes(changed_execution))
                write(parent_path, evidence.canonical_bytes({
                    **parent, "executionParentSha256": evidence.digest(changed_execution)}))
                with self.subTest(mutation=mutation), self.assertRaises(evidence.ConformanceError):
                    admit()
                run.read_execution_record.return_value = original
                observed["witnesses"] = witnesses
                if mutation in ("missing-image", "borrowed-image"):
                    observed["originalObservations"][first] = nodes
                write(settings, settings_raw)

    def test_original_metadata_sources_require_complete_forests_exact_roles_and_sdk_image(self):
        import conformance_case_catalog as catalog
        import conformance_sources as sources
        from types import SimpleNamespace

        self.assertTrue(callable(getattr(sources, "metadata_original_observations", None)))
        self.category_history(profile="metadata", mode="qualification", distinct_packages=True)
        assembly_path = ("candidate/tests/contracts/Hoard.Metadata.Tests/bin/wrapper-diagnostic/Release/net10.0/"
                         "Hoard.Metadata.Tests.dll")
        directory = Path(assembly_path).parent
        packages = ("Hoard.Fixtures.Metadata.Memory", "Hoard.Fixtures.Metadata.Sqlite",
                    "Hoard.Fixtures.Metadata.HostAdapters", "Hoard.Testing.Conformance")
        images = {assembly_path: hashlib.sha256(b"wrapper").hexdigest(), **{
            (directory / (package + ".dll")).as_posix(): hashlib.sha256(package.encode()).hexdigest()
            for package in packages}}
        self.inputs["runtimeAssemblies"] = images
        template = self.inputs["packages"][0]
        captured = {package["packageId"]: package for package in self.inputs["packages"]}
        self.inputs["packages"] = [
            {**captured.get(package, template), "packageId": package, "runtimeAssemblies": {
                "lib/net10.0/" + package + ".dll": images[(directory / (package + ".dll")).as_posix()]}}
            for package in packages]
        for binding in self.inputs["bindings"]:
            binding["package"] = next(package for package in self.inputs["packages"]
                                      if package["packageId"] == binding["package"]["packageId"])
        with tempfile.TemporaryDirectory() as temporary:
            run = SimpleNamespace(root=Path(temporary).resolve())
            for path in images:
                destination = run.root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(b"wrapper" if path == assembly_path else Path(path).stem.encode())
                destination.chmod(0o400)
            config = run.root / "stores/candidate.NuGet.Config"
            config.parent.mkdir(parents=True, exist_ok=True)
            (run.root / "feed/candidate").mkdir(parents=True)
            config.write_bytes(evidence.synthetic_nuget_configuration(run.root / "feed/candidate"))
            selected = {}
            for family in ("metadata", "artifacts"):
                path = run.root / "stores" / (family + ".json")
                path.write_bytes(b"{}")
                selected.update({
                    identity: {str(path): hashlib.sha256(b"{}").hexdigest()}
                    for identity, category in catalog.ORIGINAL_INSPECTION_WITNESSES.items()
                    if category == family and identity not in catalog.ORIGINAL_INSPECTION_LITERAL_WITNESSES})
            self.inputs["configurationSha256"] = evidence.configuration_fingerprint(
                evidence.verify_synthetic_source_mapping(run.root, "stores/candidate.NuGet.Config", "feed/candidate"),
                inspection_inputs=selected)
            self.owner["rootPathSha256"] = hashlib.sha256(str(run.root).encode()).hexdigest()
            for provider in ("memory", "sqlite"):
                scope = "original-" + provider
                tests = {identity: (provider, catalog.category_runtime_cases(
                    "metadata", provider, mode="qualification")[identity])
                    for identity in catalog.ORIGINAL_METADATA_WITNESSES}
                assignments = sources.metadata_original_inputs(run, self.inputs)[provider]
                manifest = {**self.manifest, "assemblies": [
                    {"id": "image-" + str(index), "path": path, "sha256": images[path]}
                    for index, path in enumerate(images) if Path(path).name != (
                        "Hoard.Fixtures.Metadata.Sqlite.dll" if provider == "memory"
                        else "Hoard.Fixtures.Metadata.Memory.dll")]}
                self.manifest["assemblies"] = manifest["assemblies"]
                self.manifest["expected"][0]["assemblyId"] = manifest["assemblies"][0]["id"]
                transport = self.category_transport(None, selections=tests)
                manifest = evidence.load_json(transport["manifest_data"])
                witnesses = [evidence.load_json(line) for line in transport["witnesses_data"].splitlines()]
                observed = {"diagnosticCode": "None", "attemptId": self.attempt, "witnesses": witnesses,
                            "proofs": {path: hashlib.sha256(raw).hexdigest()
                                       for path, raw in transport["proofs"].items()},
                            "sessionOrigins": {row["executionId"]: () for row in witnesses},
                            "originalObservations": {}}
                for witness in witnesses:
                    identity = witness["testIdentity"]
                    nodes = []
                    for parent in catalog.original_witness_parents(identity):
                        nodes.append({
                            "schemaVersion": 1, "runId": self.inputs["runId"], "caseId": tests[identity][1],
                            "testIdentity": identity, "bindingId": provider, "observationId": str(uuid.uuid4()),
                            "parentObservationId": None if parent is None else nodes[parent]["observationId"],
                            "kind": "original-instance", "operation": "create" if parent is None else "reopen",
                            "runtimeVersion": self.inputs["environment"]["runtime"], "processArchitecture": "x64",
                            "components": {role: {
                                "instanceId": str(uuid.uuid4()), "assemblySha256": images[path],
                                "moduleVersionId": str(uuid.uuid4()), "typeSha256": "a" * 64}
                                for role, (path, _) in assignments[identity].items()}})
                    observed["originalObservations"][witness["executionId"]] = nodes
                    path = f'proof-{witness["executionId"]}.json'
                    proof = evidence.load_json(transport["proofs"][path])
                    proof.update(schemaVersion=2, originalObservations=nodes, sessionOrigins=[],
                                 ownerSha256=evidence.digest(self.owner), assemblySha256=images[assembly_path])
                    raw = evidence.canonical_bytes(proof)
                    transport["proofs"][path] = raw
                    destination = run.root / f"runtime-{self.attempt}" / path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(raw)
                    destination.chmod(0o400)
                    witness["proofSha256"] = hashlib.sha256(raw).hexdigest()
                    witness["assemblySha256"] = images[assembly_path]
                    observed["proofs"][path] = witness["proofSha256"]
                transport["witnesses_data"] = b"".join(
                    evidence.canonical_bytes(row) + b"\n" for row in witnesses)
                completion = evidence.load_json(transport["completion_data"])
                completion["recordsSha256"] = hashlib.sha256(transport["witnesses_data"]).hexdigest()
                transport["completion_data"] = evidence.canonical_bytes(completion)
                for path, raw in (("witnesses.jsonl", transport["witnesses_data"]),
                                  ("completion.json", transport["completion_data"])):
                    destination = run.root / f"runtime-{self.attempt}" / path
                    if destination.exists():
                        destination.chmod(0o600)
                    destination.write_bytes(raw)
                    destination.chmod(0o400)

                def admit():
                    return sources.metadata_original_observations(
                        run, self.inputs, manifest, observed, scope_id=scope)

                self.assertEqual(len(admit()), 63)
                self.original_metadata_command_fixture(run, manifest, observed, transport, scope, selected)
                for mutation in ("missing-row", "parameter", "forest", "role", "context", "sdk", "image"):
                    changed_manifest, changed_observed = copy.deepcopy(manifest), copy.deepcopy(observed)
                    first = witnesses[0]["executionId"]
                    proof_path = run.root / f"runtime-{self.attempt}/proof-{first}.json"
                    proof_raw = proof_path.read_bytes()
                    if mutation == "missing-row":
                        observed["witnesses"] = witnesses[:-1]
                    elif mutation == "parameter":
                        manifest["expected"][0]["testIdentity"] += "(foreign)"
                    elif mutation == "forest":
                        observed["originalObservations"][first] = []
                    elif mutation == "role":
                        observed["originalObservations"][first][0]["components"]["store"]["assemblySha256"] = images[
                            (directory / "Hoard.Fixtures.Metadata.HostAdapters.dll").as_posix()]
                    elif mutation == "context":
                        observed["originalObservations"][first][0]["bindingId"] = (
                            "sqlite" if provider == "memory" else "memory")
                    elif mutation == "sdk":
                        manifest["assemblies"] = [row for row in manifest["assemblies"]
                                                  if not row["path"].endswith("/Hoard.Testing.Conformance.dll")]
                    else:
                        manifest["assemblies"][-1]["sha256"] = "0" * 64
                    if mutation in ("forest", "role", "context"):
                        changed_proof = evidence.load_json(proof_raw)
                        changed_proof["originalObservations"] = observed["originalObservations"][first]
                        raw = evidence.canonical_bytes(changed_proof)
                        proof_path.chmod(0o600)
                        proof_path.write_bytes(raw)
                        proof_path.chmod(0o400)
                        observed["witnesses"][0]["proofSha256"] = hashlib.sha256(raw).hexdigest()
                        observed["proofs"][proof_path.name] = hashlib.sha256(raw).hexdigest()
                    with self.subTest(provider=provider, mutation=mutation), self.assertRaises(evidence.ConformanceError):
                        admit()
                    proof_path.chmod(0o600)
                    proof_path.write_bytes(proof_raw)
                    proof_path.chmod(0o400)
                    manifest, observed = changed_manifest, changed_observed

    def original_metadata_command_fixture(self, run, manifest, observed, transport, scope, selected):
        import base64
        import conformance_sdk_checks as checks
        import conformance_sources as sources

        def write(path, raw):
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                path.chmod(0o600)
            path.write_bytes(raw)
            path.chmod(0o400)

        run.run_id, run.root_id = self.inputs["runId"], self.owner["rootId"]
        run.command_sequence, run.live_children = 1, lambda: ()
        native = object.__new__(sources.NativeCategorySources)
        native._run, native._selected = run, selected
        facts = sources.metadata_original_observations(run, self.inputs, manifest, observed, scope_id=scope)
        receipt = {"schemaVersion": 1, "qualification": False, "mode": "category-metadata-" + scope,
                   "runId": run.run_id, "invocationGroupId": self.inputs["invocationGroupId"],
                   "attemptId": self.attempt, "inputsSha256": evidence.digest(self.inputs), "observations": facts}
        write(run.root / f'proofs/{receipt["mode"]}-{self.attempt}.json', evidence.canonical_bytes(receipt))
        write(run.root / "runtime-owner.json", transport["owner_data"])
        write(run.root / f"runtime-input-{self.attempt}.json", transport["manifest_data"])
        write(run.root / manifest["runInputsPath"], evidence.canonical_bytes(self.inputs))
        context = {"schemaVersion": 1, "runId": run.run_id, "cases": {
            entry["testIdentity"]: {"caseId": entry["caseId"], "bindingId": entry["bindingId"]}
            for entry in manifest["expected"]}}
        provider = scope.removeprefix("original-")
        environment = ("<EnvironmentVariables><HOARD_METADATA_PROVIDER>" + provider
                       + "</HOARD_METADATA_PROVIDER><HOARD_ORIGINAL_CONTEXT>"
                       + base64.b64encode(evidence.canonical_bytes(context)).decode()
                       + "</HOARD_ORIGINAL_CONTEXT></EnvironmentVariables>")
        assembly = run.root / manifest["assemblies"][0]["path"]
        settings = run.root / "stores" / f"settings-{self.attempt}.runsettings"
        settings_raw = sources.runtime_settings(
            run.root, assembly, self.attempt, evidence.digest(manifest), evidence.digest(self.owner), environment)
        write(settings, settings_raw)
        record = {
            "schemaVersion": 1, "sequence": 1, "childPid": 123, "childStartSha256": "a" * 64,
            "startedMs": 9, "endedMs": 12, "exitCode": 0, "diagnosticCode": "None", "groupState": "Exited",
            "scope": "ordinary", "runId": run.run_id, "rootId": run.root_id,
            "argvSha256": evidence.digest(sources.runtime_arguments(
                assembly, settings, [entry["testIdentity"] for entry in manifest["expected"]])),
            "cwdSha256": hashlib.sha256(str(assembly.parent).encode()).hexdigest(),
            "inputFiles": {f"runtime-input-{self.attempt}.json": evidence.digest(manifest),
                           "runtime-owner.json": evidence.digest(self.owner),
                           manifest["runInputsPath"]: evidence.digest(self.inputs),
                           settings.relative_to(run.root).as_posix(): hashlib.sha256(settings_raw).hexdigest(),
                           **{row["path"]: row["sha256"] for row in manifest["assemblies"]}}}
        original = evidence.canonical_bytes(record)
        run.read_execution_record = mock.Mock(return_value=original)
        execution = {
            "schemaVersion": 1, "qualification": False, "nativeContainment": True,
            "runId": run.run_id, "rootId": run.root_id, "invocationGroupId": self.inputs["invocationGroupId"],
            "attemptId": self.attempt, "purpose": "execution", "commandSequence": 1,
            "inputsSha256": evidence.digest(self.inputs), "executionRecordSha256": evidence.digest(record),
            "manifestSha256": evidence.digest(manifest), "settingsSha256": hashlib.sha256(settings_raw).hexdigest()}
        parent = {
            "schemaVersion": 1, "qualification": False, "nativeContainment": True, "profileId": "metadata",
            "scopeId": scope, "runId": run.run_id, "invocationGroupId": self.inputs["invocationGroupId"],
            "attemptId": self.attempt, "inputsSha256": evidence.digest(self.inputs),
            "manifestSha256": evidence.digest(manifest), "commandSequence": 1,
            "executionParentSha256": evidence.digest(execution), "sourceReceiptSha256": evidence.digest(receipt),
            "observations": [{**row, "bindingId": provider,
                              "caseId": next(entry["caseId"] for entry in manifest["expected"]
                                             if entry["testIdentity"] == row["testIdentity"])} for row in facts]}
        execution_path = run.root / f"proofs/category-command-{self.attempt}-execution.json"
        parent_path = run.root / f"proofs/category-source-{self.attempt}.json"
        write(execution_path, evidence.canonical_bytes(execution))
        write(run.root / "proofs/execution-command-0001.json", original)
        if parent_path.exists():
            parent_path.unlink()
        with mock.patch.object(checks, "OwnedRun", type(run)):
            produced = checks.category_source_parent(
                run, self.inputs, manifest, observed,
                {"sourceExecutions": 63, "originalMetadataProofsSha256": evidence.digest(receipt)},
                category_scope=("metadata", scope),
                result=type(run)(exit_code=0, execution_record_sha256=hashlib.sha256(original).hexdigest()))
        self.assertEqual(produced, evidence.digest(parent))
        self.assertEqual(parent_path.read_bytes(), evidence.canonical_bytes(parent))

        def admit():
            return native._corroborate(
                self.inputs, manifest, observed, category_scope=("metadata", scope),
                manifest_data=transport["manifest_data"], owner_data=transport["owner_data"],
                started_ms=9, ended_ms=12)

        self.assertEqual(len(admit()["sourceParents"]), 63)
        def ingest(**overrides):
            return native.ingest_attempt(
                inputs=self.inputs, category_scope=("metadata", scope), **{**transport, **overrides},
                expected_tests={entry["testIdentity"]: (entry["bindingId"], "none") for entry in manifest["expected"]},
                started_ms=9, ended_ms=12)

        self.assertEqual(len(ingest()["sourceParents"]), 63)
        wrong_inputs = sources.metadata_original_inputs(run, self.inputs)
        identity = next(iter(wrong_inputs[provider]))
        wrong_inputs[provider][identity]["store"] = wrong_inputs[provider][identity]["controls"]
        with self.assertRaisesRegex(evidence.ConformanceError, "ProofMismatch"):
            ingest(original_inputs=wrong_inputs)
        for filename in ("witnesses.jsonl", "completion.json"):
            path = run.root / f"runtime-{self.attempt}" / filename
            path.chmod(0o600)
            with self.subTest(scope=scope, unsealed=filename), self.assertRaises(evidence.ConformanceError):
                ingest()
            path.chmod(0o400)
        for mutation in ("argv", "inputs", "cwd", "exit", "time", "sequence", "replaced-record", "settings",
                         "missing-parent", "borrowed-parent", "unsealed-proof", "changed-proof"):
            changed = copy.deepcopy(record)
            proof = run.root / f'runtime-{self.attempt}/proof-{observed["witnesses"][0]["executionId"]}.json'
            proof_raw = proof.read_bytes()
            if mutation in ("argv", "cwd"):
                changed[mutation + "Sha256"] = "0" * 64
            elif mutation == "inputs":
                changed["inputFiles"].pop(next(path for path in changed["inputFiles"]
                                               if path.endswith("/Hoard.Testing.Conformance.dll")))
            elif mutation == "exit":
                changed["exitCode"] = 1
            elif mutation == "time":
                changed["startedMs"] = 8
            elif mutation == "sequence":
                changed["sequence"] = 2
            elif mutation == "settings":
                write(settings, settings_raw.replace(provider.encode(), b"foreign"))
            elif mutation == "unsealed-proof":
                proof.chmod(0o600)
            elif mutation == "changed-proof":
                write(proof, proof_raw + b" ")
            raw = evidence.canonical_bytes(changed)
            run.read_execution_record.return_value = original if mutation == "replaced-record" else raw
            if mutation == "replaced-record":
                raw = evidence.canonical_bytes({**record, "childPid": 456})
            changed_execution = {**execution, "executionRecordSha256": hashlib.sha256(raw).hexdigest()}
            write(execution_path, evidence.canonical_bytes(changed_execution))
            changed_parent = {**parent, "executionParentSha256": evidence.digest(changed_execution)}
            if mutation == "borrowed-parent":
                changed_parent["attemptId"] = str(uuid.uuid4())
            write(parent_path, evidence.canonical_bytes(changed_parent))
            if mutation == "missing-parent":
                parent_path.unlink()
            with self.subTest(scope=scope, mutation=mutation), self.assertRaises((evidence.ConformanceError, OSError)):
                admit()
            run.read_execution_record.return_value = original
            write(settings, settings_raw)
            write(proof, proof_raw)
        write(execution_path, evidence.canonical_bytes(execution))
        write(parent_path, evidence.canonical_bytes(parent))

    def test_native_shared_metadata_consumer_reconstructs_all_rows_origins_and_original_command(self):
        self.native_consumer_source_fixture(profile="metadata", hooks=False)

    def test_native_hook_consumers_require_complete_actual_origins_and_original_command(self):
        import conformance_sources as sources
        self.assertTrue(callable(getattr(sources, "native_hook_admission_control", None)),
                        "Dedicated hook rows require independent native source reconstruction.")
        for profile in ("metadata", "artifacts"):
            self.setUp()
            with self.subTest(profile=profile):
                self.native_consumer_source_fixture(profile=profile, hooks=True)

    def native_consumer_source_fixture(self, *, profile, hooks):
        import conformance_case_catalog as catalog
        import conformance_sdk_checks as checks
        import conformance_sources as sources
        from types import SimpleNamespace
        from xml.sax.saxutils import escape

        self.category_history(profile=profile, mode="qualification", distinct_packages=True)
        directory = Path("snapshot/tests/fixtures/conformance/Consumer/bin/package-diagnostic/Release/net10.0")
        assembly_path = (directory / "Hoard.Fixtures.Conformance.Consumer.dll").as_posix()
        adapters = ("Memory", "Sqlite") if profile == "metadata" else ("Local", "ObjectSemantics")
        family = profile.title()
        packages = ("Hoard.Testing.Conformance", *("Hoard.Fixtures." + family + "." + adapter for adapter in adapters),
                    *("Hoard.Fixtures.Conformance.Bindings." + adapter for adapter in adapters))
        wrapper_sdk = (
            "snapshot/tests/contracts/Hoard.Metadata.Tests/bin/wrapper-diagnostic/Release/net10.0/"
            "Hoard.Testing.Conformance.dll")
        image_data = {assembly_path: b"consumer", **{
            (directory / (package + ".dll")).as_posix(): package.encode() for package in packages},
            **({wrapper_sdk: b"Hoard.Testing.Conformance"} if not hooks else {})}
        images = {path: hashlib.sha256(raw).hexdigest() for path, raw in image_data.items()}
        self.inputs["runtimeAssemblies"] = images
        captured = {row["packageId"]: row for row in self.inputs["packages"]}
        template = self.inputs["packages"][0]
        for package in packages:
            captured[package] = {
                **captured.get(package, template), "packageId": package,
                "runtimeAssemblies": {"lib/net10.0/" + package + ".dll":
                                     images[(directory / (package + ".dll")).as_posix()]}}
        self.inputs["packages"] = list(captured.values())
        for binding in self.inputs["bindings"]:
            binding["package"] = captured[binding["package"]["packageId"]]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            def write(path, raw):
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    path.chmod(0o600)
                path.write_bytes(raw)
                path.chmod(0o400)

            for path, raw in image_data.items():
                write(root / path, raw)
            run = SimpleNamespace(root=root, run_id=self.inputs["runId"], root_id=self.owner["rootId"],
                                  command_sequence=2, live_children=lambda: ())
            self.owner["rootPathSha256"] = hashlib.sha256(str(root).encode()).hexdigest()
            self.proof["ownerSha256"] = evidence.digest(self.owner)
            self.proof["assemblySha256"] = self.witness["assemblySha256"] = images[assembly_path]
            manifest_factory = sources.hook_admission_manifest if hooks else sources.metadata_common_consumer_manifest
            self.manifest = manifest_factory(run, self.inputs, self.attempt)
            consumer_images = {entry["path"]: entry["sha256"] for entry in self.manifest["assemblies"]}
            selected = catalog.hook_admission_tests(profile) if hooks else catalog.metadata_common_consumer_tests()
            counts = ({identity: 1 for identity in selected} if hooks else catalog.metadata_common_consumer_origin_counts())
            self.assertEqual(len(selected), 2 if hooks else 152)
            self.assertEqual({binding for binding, _ in selected.values()},
                             {"memory", "sqlite"} if profile == "metadata" else {"local", "object"})
            transport = self.category_transport(None, selections=selected)
            self.assertEqual(evidence.load_json(transport["manifest_data"]), self.manifest)
            origins = sources.category_consumer_origin_inputs(run, self.inputs)
            witnesses = []
            for line in transport["witnesses_data"].splitlines():
                row = evidence.load_json(line)
                filename = f'proof-{row["executionId"]}.json'
                proof = evidence.load_json(transport["proofs"][filename])
                captured_origins = []
                for index in range(counts[row["testIdentity"]]):
                    origin = {
                        "schemaVersion": 1, "runId": run.run_id, "caseId": "QC-05" if hooks else "full-metadata-binding",
                        "sessionId": str(uuid.uuid4()),
                        "parentSessionId": None if index == 0 else captured_origins[-1]["sessionId"],
                        "factoryOperation": "create" if index == 0 else "reopen",
                        "descriptorSha256": next(binding["descriptorSha256"] for binding in self.inputs["bindings"]
                                                 if binding["bindingId"] == row["bindingId"]),
                        "runtimeVersion": self.inputs["environment"]["runtime"], "processArchitecture": "x64",
                        "components": {
                            role: {"instanceId": str(uuid.uuid4()), "assemblySha256": images[path],
                                   "moduleVersionId": str(uuid.uuid4()), "typeSha256": "f" * 64}
                            for role, (path, _) in origins[row["bindingId"]].items()}}
                    if index:
                        origin["components"]["factory"] = copy.deepcopy(captured_origins[0]["components"]["factory"])
                    captured_origins.append(origin)
                proof["sessionOrigins"] = captured_origins
                transport["proofs"][filename] = evidence.canonical_bytes(proof)
                witnesses.append({**row, "proofSha256": evidence.digest(proof)})
            transport["witnesses_data"] = b"".join(evidence.canonical_bytes(row) + b"\n" for row in witnesses)
            completion = evidence.load_json(transport["completion_data"])
            completion["recordsSha256"] = hashlib.sha256(transport["witnesses_data"]).hexdigest()
            transport["completion_data"] = evidence.canonical_bytes(completion)
            expected = {identity: (binding, "none") for identity, (binding, _) in selected.items()}
            observed = evidence.inspect_runtime_attempt(
                inputs=self.inputs, **transport, expected_tests=expected, origin_inputs=origins,
                started_ms=9, ended_ms=12)["observation"]
            attempt = self.attempt
            assembly = root / assembly_path
            settings_path = f"stores/settings-{attempt}.runsettings"
            environment = "<EnvironmentVariables>" + "".join(
                f"<{key}>{escape(value)}</{key}>" for key, value in sources.category_consumer_environment(
                    self.inputs).items()) + "</EnvironmentVariables>"
            settings = sources.runtime_settings(
                root, assembly, attempt, evidence.digest(self.manifest), evidence.digest(self.owner), environment)
            record = {
                "schemaVersion": 1, "sequence": 2, "childPid": 123, "childStartSha256": "a" * 64,
                "startedMs": 9, "endedMs": 10, "exitCode": 0, "diagnosticCode": "None",
                "groupState": "Exited", "scope": "ordinary", "runId": run.run_id, "rootId": run.root_id,
                "argvSha256": evidence.digest(sources.runtime_arguments(
                    assembly, root / settings_path, [row["testIdentity"] for row in self.manifest["expected"]])),
                "cwdSha256": hashlib.sha256(str(assembly.parent).encode()).hexdigest(),
                "inputFiles": {f"runtime-input-{attempt}.json": evidence.digest(self.manifest),
                               "runtime-owner.json": evidence.digest(self.owner),
                               self.manifest["runInputsPath"]: evidence.digest(self.inputs),
                               settings_path: hashlib.sha256(settings).hexdigest(), **consumer_images,
                               **({wrapper_sdk: images[wrapper_sdk]} if not hooks else {})}}
            original_record = evidence.canonical_bytes(record)
            run.read_execution_record = lambda sequence: original_record
            namespace = (sources.HOOK_ADMISSION_NAMESPACES[profile] if hooks
                         else sources.METADATA_COMMON_CONSUMER_NAMESPACE)
            graph_path = f"proofs/{namespace}-native-executions.json"
            execution_path = f"proofs/category-command-{attempt}-execution.json"
            graph = {
                "schemaVersion": 1, "qualification": False, "runId": run.run_id,
                "invocationGroupId": self.inputs["invocationGroupId"], "inputsSha256": evidence.digest(self.inputs),
                "attemptId": attempt, "commandSequence": 2, "executionRecordSha256": evidence.digest(record)}
            execution = {
                "schemaVersion": 1, "qualification": False, "nativeContainment": True,
                "runId": run.run_id, "rootId": run.root_id, "invocationGroupId": self.inputs["invocationGroupId"],
                "attemptId": attempt, "purpose": "execution", "commandSequence": 2,
                "inputsSha256": evidence.digest(self.inputs), "executionRecordSha256": evidence.digest(record),
                "manifestSha256": evidence.digest(self.manifest), "settingsSha256": hashlib.sha256(settings).hexdigest()}
            originals = {
                graph_path: evidence.canonical_bytes(graph), execution_path: evidence.canonical_bytes(execution),
                "proofs/execution-command-0002.json": original_record,
                f"runtime-input-{attempt}.json": transport["manifest_data"],
                "runtime-owner.json": transport["owner_data"],
                self.manifest["runInputsPath"]: evidence.canonical_bytes(self.inputs), settings_path: settings,
                f"runtime-{attempt}/witnesses.jsonl": transport["witnesses_data"],
                f"runtime-{attempt}/completion.json": transport["completion_data"],
                **{f"runtime-{attempt}/{path}": raw for path, raw in transport["proofs"].items()}}
            for path, raw in originals.items():
                write(root / path, raw)

            def admit():
                with mock.patch.object(sources, "OwnedRun", SimpleNamespace):
                    return (sources.native_hook_admission_control if hooks
                            else sources.native_metadata_common_consumer_control)(
                        run, self.inputs, started_ms=9, ended_ms=12)

            admitted = admit()
            self.assertEqual(set(admitted["sourceProofs"]), set(originals))
            self.assertEqual(len(witnesses), 2 if hooks else 152)
            self.assertEqual(set(admitted["controls"]),
                             {"hook-admission-sdk-consumer", *catalog.obligation_controls(5)} if hooks
                             else {"shared-metadata-sdk-consumer"})
            if hooks:
                native = object.__new__(sources.NativeCategorySources)
                native._run = run
                with contextlib.ExitStack() as stack:
                    stack.enter_context(mock.patch.object(sources, "OwnedRun", SimpleNamespace))
                    for name in ("native_metadata_recovery_controls", "native_metadata_noncooperation_control",
                                 "native_metadata_ownership_control", "native_metadata_package_consumer_control",
                                 "native_metadata_binary_control", "native_metadata_inventory_controls",
                                 "native_metadata_common_consumer_control"):
                        stack.enter_context(mock.patch.object(
                            sources, name, return_value={"controls": {}, "sourceProofs": {
                                "runtime-owner.json": originals["runtime-owner.json"]}
                                if name == "native_metadata_common_consumer_control" else {}}))
                    history = evidence.CategoryRuntimeHistory(self.inputs, native_sources=native)
                    result = history._ingest_parts({}, {}, 9, 12, 1)
                    self.assertEqual(result[8], admitted["controls"])
                    self.assertEqual(result[2], {
                        path: hashlib.sha256(raw).hexdigest() for path, raw in originals.items()})
                    self.assertEqual(result[9], sum(len(raw) for raw in originals.values()))
                    if profile == "metadata":
                        for conflict in (
                                {"controls": {}, "sourceProofs": {"runtime-owner.json": b"foreign"}},
                                {"controls": {"hook-admission-sdk-consumer":
                                              admitted["controls"]["hook-admission-sdk-consumer"]},
                                 "sourceProofs": {}}):
                            with mock.patch.object(sources, "native_metadata_common_consumer_control",
                                                   return_value=conflict):
                                with self.assertRaisesRegex(evidence.ConformanceError, "ProofMismatch"):
                                    history._ingest_parts({}, {}, 9, 12, 1)
                    history._proof_bytes = evidence.MAX_PROOF_BYTES
                    with self.assertRaisesRegex(evidence.ConformanceError, "OutputLimitExceeded"):
                        history._ingest_parts({}, {}, 9, 12, 1)
                    history._proof_bytes = 0
                    plan = {"hook-admission": {"attemptId": attempt, "tests": selected}}
                    result = history._ingest_parts(plan, {"hook-admission": transport}, 9, 12, 1)
                    parent = hashlib.sha256(originals[graph_path]).hexdigest()
                    self.assertEqual(result[7], {row["executionId"]: parent for row in witnesses})
                    self.assertEqual({row["executionId"] for row in result[1]},
                                     {row["executionId"] for row in witnesses})
                    history._active = {binding: (attempt, 9) for binding in history._bindings}
                    cases = history._case_results("none", "None", 12, result[1], result[7], result[8])
                    key = (profile, "none", "none", "QC-05")
                    self.assertEqual(cases[key]["status"], "Passed")
                    indexed = {row["executionId"]: row for row in witnesses}
                    quality = evidence._category_quality_composition(
                        self.inputs, "QC-05", cases, indexed, sequence=1, started_ms=9, ended_ms=12)
                    self.assertEqual(quality["attempt"]["status"], "Passed")
                    self.assertEqual(set(quality["attempt"]["witnessIds"]), set(indexed))
                    for missing in catalog.obligation_controls(5):
                        incomplete = history._case_results(
                            "none", "None", 12, result[1], result[7],
                            {name: proofs for name, proofs in result[8].items() if name != missing})
                        rejected = evidence._category_quality_composition(
                            self.inputs, "QC-05", incomplete, indexed, sequence=1, started_ms=9, ended_ms=12)
                        self.assertEqual(rejected["attempt"]["status"], "Incomplete")
                        incomplete = history._case_results("none", "None", 12, result[1], {}, result[8])
                        rejected = evidence._category_quality_composition(
                            self.inputs, "QC-05", incomplete, indexed, sequence=1, started_ms=9, ended_ms=12)
                        self.assertEqual(rejected["attempt"]["status"], "Incomplete")
                        with self.assertRaisesRegex(evidence.ConformanceError, "ProofMismatch"):
                            evidence._category_quality_composition(
                                self.inputs, "QC-05", cases, indexed, sequence=1, started_ms=9, ended_ms=13)
                    incomplete = history._case_results(
                        "none", "None", 12, result[1][:-1], result[7], result[8])
                    rejected = evidence._category_quality_composition(
                        self.inputs, "QC-05", incomplete, indexed, sequence=1, started_ms=9, ended_ms=12)
                    self.assertEqual(rejected["attempt"]["status"], "Incomplete")
                    with self.assertRaises(evidence.ConformanceError):
                        native.ingest_attempt(
                            inputs=self.inputs, **transport, expected_tests=expected,
                            started_ms=9, ended_ms=12, category_scope=(profile, "hook-admission"),
                            origin_inputs={})
            (root / graph_path).unlink()
            (root / self.manifest["runInputsPath"]).unlink()
            if hooks:
                public_inputs = f"proofs/category-{profile}-qualification-run-inputs.json"
                write(root / public_inputs, evidence.canonical_bytes(self.inputs))
            with mock.patch.object(checks, "OwnedRun", SimpleNamespace), mock.patch.object(
                    sources, "OwnedRun", SimpleNamespace), mock.patch.object(
                    checks.uuid, "uuid4", return_value=uuid.UUID(attempt)), mock.patch.object(
                    checks, "require_sqlite_environment"), mock.patch.object(
                    checks.time, "monotonic", side_effect=lambda: 0.012 if launch.called else 0.009), mock.patch.object(
                    checks, "_execute_runtime_transport",
                    return_value=(SimpleNamespace(exit_code=0, execution_record_sha256=evidence.digest(record),
                                                  events=({"event": "control", "code": "None", "value": len(selected)},)),
                                  observed, transport, "b" * 64)) as launch:
                produced = (checks.category_attempt(
                    run, self.inputs, root / "snapshot", "hook-admission",
                    {"attemptId": attempt, "tests": selected},
                    run_inputs_path=public_inputs, native_sources=native)
                    if hooks else checks.metadata_common_consumer_diagnostics(run, self.inputs))
            if hooks:
                self.assertEqual(produced["transport"], transport)
                self.assertEqual(produced["summary"]["sourceParentSha256"],
                                 hashlib.sha256(originals[graph_path]).hexdigest())
                self.assertEqual(produced["summary"]["tests"], 2)
                self.assertEqual(admit(), admitted)
            else:
                self.assertEqual(produced, admitted)
            self.assertEqual(launch.call_args.args[4], expected)
            self.assertEqual(launch.call_args.kwargs["origin_inputs"], origins)
            self.assertEqual(launch.call_args.args[5]["category_scope"],
                             (profile, "hook-admission" if hooks else "shared-consumer"))
            for defect in ("missing-origins", "wrong-case", "borrowed-role", "foreign-descriptor", "duplicate-session",
                           "missing-row", "relabeled-manifest", "argv", "inputs", "replaced-record", "settings",
                           *(("wrapper-sdk", "unpinned-wrapper-sdk") if not hooks else ())):
                with self.subTest(defect=defect):
                    changed_record = copy.deepcopy(record)
                    first = witnesses[0]
                    filename = f'proof-{first["executionId"]}.json'
                    proof = evidence.load_json(transport["proofs"][filename])
                    if defect in ("missing-origins", "wrong-case", "borrowed-role", "foreign-descriptor",
                                  "duplicate-session"):
                        if defect == "missing-origins":
                            proof["sessionOrigins"] = []
                        elif defect == "wrong-case":
                            proof["sessionOrigins"][0]["caseId"] = "QC-02"
                        elif defect == "borrowed-role":
                            proof["sessionOrigins"][0]["components"]["store"]["assemblySha256"] = images[
                                (directory / ("Hoard.Fixtures." + family + "." + adapters[1] + ".dll")).as_posix()]
                        elif defect == "foreign-descriptor":
                            proof["sessionOrigins"][0]["descriptorSha256"] = next(
                                binding["descriptorSha256"] for binding in self.inputs["bindings"]
                                if binding["bindingId"] != first["bindingId"])
                        else:
                            proof["sessionOrigins"].append(copy.deepcopy(proof["sessionOrigins"][0]))
                        changed_witnesses = [{**first, "proofSha256": evidence.digest(proof)}, *witnesses[1:]]
                        write(root / f"runtime-{attempt}/{filename}", evidence.canonical_bytes(proof))
                    else:
                        changed_witnesses = witnesses
                    if defect == "missing-row":
                        changed_witnesses = witnesses[:-1]
                    lines = b"".join(evidence.canonical_bytes(row) + b"\n" for row in changed_witnesses)
                    write(root / f"runtime-{attempt}/witnesses.jsonl", lines)
                    write(root / f"runtime-{attempt}/completion.json", evidence.canonical_bytes({
                        **completion, "recordsSha256": hashlib.sha256(lines).hexdigest()}))
                    if defect == "relabeled-manifest":
                        manifest = copy.deepcopy(self.manifest)
                        manifest["expected"][0]["caseId"] = "QC-02"
                        write(root / f"runtime-input-{attempt}.json", evidence.canonical_bytes(manifest))
                    if defect in ("argv", "inputs", "replaced-record", "unpinned-wrapper-sdk"):
                        if defect == "argv":
                            changed_record["argvSha256"] = "b" * 64
                        elif defect == "unpinned-wrapper-sdk":
                            changed_record["inputFiles"].pop(wrapper_sdk)
                        else:
                            changed_record["inputFiles"].pop(next(iter(images)))
                        changed_raw = evidence.canonical_bytes(changed_record)
                        if defect != "replaced-record":
                            run.read_execution_record = lambda sequence: changed_raw
                        write(root / "proofs/execution-command-0002.json", changed_raw)
                        write(root / graph_path, evidence.canonical_bytes({
                            **graph, "executionRecordSha256": hashlib.sha256(changed_raw).hexdigest()}))
                        write(root / execution_path, evidence.canonical_bytes({
                            **execution, "executionRecordSha256": hashlib.sha256(changed_raw).hexdigest()}))
                    if defect == "settings":
                        write(root / settings_path, settings.replace(b"PACKAGE_SHA256", b"FOREIGN_SHA256"))
                    if defect == "wrapper-sdk":
                        write(root / wrapper_sdk, b"foreign-shared-assertions")
                    with self.assertRaises(evidence.ConformanceError):
                        admit()
                    run.read_execution_record = lambda sequence: original_record
                    for path, raw in originals.items():
                        write(root / path, raw)
                    if not hooks:
                        write(root / wrapper_sdk, image_data[wrapper_sdk])

    def test_native_mutation_pairs_require_exact_named_failures_and_same_current_images(self):
        import conformance_case_catalog as catalog
        import conformance_sdk_checks as checks
        import conformance_sources as sources
        from types import SimpleNamespace
        from xml.sax.saxutils import escape

        for profile in ("metadata", "artifacts"):
            self.setUp()
            self.category_history(profile=profile, mode="qualification", distinct_packages=True)
            corrected_id, faulty_id = str(uuid.uuid4()), str(uuid.uuid4())
            directory = Path("snapshot/tests/fixtures/conformance/Consumer/bin/package-diagnostic/Release/net10.0")
            assembly_path = (directory / "Hoard.Fixtures.Conformance.Consumer.dll").as_posix()
            providers = {row["bindingId"]: row["package"] for row in self.inputs["bindings"]}
            binding_names = {"memory": "Memory", "sqlite": "Sqlite", "local": "Local", "object": "ObjectSemantics"}
            image_packages = ("Hoard.Testing.Conformance", *(package["packageId"] for package in providers.values()),
                              *("Hoard.Fixtures.Conformance.Bindings." + binding_names[binding] for binding in providers))
            images = {assembly_path: hashlib.sha256(b"consumer").hexdigest(), **{
                (directory / (package + ".dll")).as_posix(): hashlib.sha256(package.encode()).hexdigest()
                for package in image_packages}}
            self.inputs["runtimeAssemblies"] = images
            captured = {package["packageId"]: package for package in self.inputs["packages"]}
            template = self.inputs["packages"][0]
            for package in image_packages:
                captured[package] = {**captured.get(package, template), "packageId": package,
                                     "runtimeAssemblies": {"lib/net10.0/" + package + ".dll":
                                                          images[(directory / (package + ".dll")).as_posix()]}}
            self.inputs["packages"] = list(captured.values())
            for binding in self.inputs["bindings"]:
                binding["package"] = captured[binding["package"]["packageId"]]
            self.manifest["assemblies"] = [
                {"id": "tests" if path == assembly_path else "component-" + str(index), "path": path, "sha256": hashed}
                for index, (path, hashed) in enumerate(images.items())]
            self.proof["assemblySha256"] = self.witness["assemblySha256"] = images[assembly_path]
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()

                def write(path, raw):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if path.exists():
                        path.chmod(0o600)
                    path.write_bytes(raw)
                    path.chmod(0o400)

                for path in images:
                    write(root / path, b"consumer" if path == assembly_path else Path(path).stem.encode())
                write(root / "stores/candidate.NuGet.Config",
                      evidence.synthetic_nuget_configuration(root / "feed/candidate"))
                (root / "feed/candidate").mkdir(parents=True)
                configurations = {family: root / "stores" / (family + ".json") for family in ("metadata", "artifacts")}
                for path in configurations.values():
                    write(path, b"{}")
                inspection = {
                    identity: {str(configurations[family]): hashlib.sha256(b"{}").hexdigest()}
                    for identity, family in catalog.ORIGINAL_INSPECTION_WITNESSES.items()
                    if identity not in catalog.ORIGINAL_INSPECTION_LITERAL_WITNESSES}
                self.inputs["configurationSha256"] = evidence.configuration_fingerprint(
                    evidence.verify_synthetic_source_mapping(root, "stores/candidate.NuGet.Config", "feed/candidate"),
                    inspection_inputs=inspection)
                self.owner["rootPathSha256"] = hashlib.sha256(str(root).encode()).hexdigest()
                self.proof["ownerSha256"] = evidence.digest(self.owner)
                self.attempt = faulty_id
                self.manifest["expected"][0]["assertionSymbol"] = catalog.CATEGORY_MUTATION_METHODS[profile][2]
                faulty = self.category_transport(None, selections={
                    identity: (binding, "QC-04") for identity, binding in catalog.category_mutation_witnesses(
                        profile, corrected=False).items()})
                failed = []
                for line in faulty["witnesses_data"].splitlines():
                    row = evidence.load_json(line)
                    path = f'proof-{row["executionId"]}.json'
                    proof = evidence.load_json(faulty["proofs"][path])
                    proof.update(status="Failed", failureKind="Assertion",
                                 assertionSymbol=catalog.CATEGORY_MUTATION_METHODS[profile][2])
                    faulty["proofs"][path] = evidence.canonical_bytes(proof)
                    failed.append({**row, "status": "Failed", "proofSha256": evidence.digest(proof)})
                faulty["witnesses_data"] = b"".join(evidence.canonical_bytes(row) + b"\n" for row in failed)
                completion = evidence.load_json(faulty["completion_data"])
                completion.update(diagnosticCode="AssertionFailed", recordsSha256=hashlib.sha256(
                    faulty["witnesses_data"]).hexdigest())
                faulty["completion_data"] = evidence.canonical_bytes(completion)
                faulty_manifest = evidence.load_json(faulty["manifest_data"])
                self.attempt = corrected_id
                self.manifest["expected"][0]["assertionSymbol"] = None
                corrected = catalog.category_mutation_witnesses(profile, corrected=True)
                transport = self.category_transport(
                    None, started=10, selections={identity: (binding, "QC-04") for identity, binding in corrected.items()})
                manifest = evidence.load_json(transport["manifest_data"])
                observed = evidence.inspect_runtime_attempt(
                    inputs=self.inputs, **transport,
                    expected_tests={identity: (binding, "none") for identity, binding in corrected.items()},
                    started_ms=9, ended_ms=12)["observation"]
                run = SimpleNamespace(root=root, run_id=self.inputs["runId"], root_id=self.owner["rootId"],
                                      command_sequence=2, live_children=lambda: ())
                write(root / "runtime-owner.json", transport["owner_data"])
                write(root / manifest["runInputsPath"], evidence.canonical_bytes(self.inputs))
                write(root / f"runtime-input-{faulty_id}.json", faulty["manifest_data"])
                for path, raw in {**faulty["proofs"], "witnesses.jsonl": faulty["witnesses_data"],
                                  "completion.json": faulty["completion_data"]}.items():
                    write(root / f"runtime-{faulty_id}" / path, raw)
                environment = "<EnvironmentVariables>" + "".join(
                    f"<{key}>{escape(value)}</{key}>" for key, value in sources.category_consumer_environment(
                        self.inputs).items()) + "</EnvironmentVariables>"
                assembly = root / assembly_path
                settings_path = f"stores/settings-{faulty_id}.runsettings"
                settings = root / settings_path
                settings_raw = sources.runtime_settings(
                    root, assembly, faulty_id, evidence.digest(faulty_manifest), evidence.digest(self.owner), environment)
                write(settings, settings_raw)
                record = {
                    "schemaVersion": 1, "sequence": 1, "childPid": 123, "childStartSha256": "a" * 64,
                    "startedMs": 9, "endedMs": 10, "exitCode": 1, "diagnosticCode": "None",
                    "groupState": "Exited", "scope": "ordinary", "runId": run.run_id, "rootId": run.root_id,
                    "argvSha256": evidence.digest(sources.runtime_arguments(
                        assembly, settings, tuple(catalog.category_mutation_witnesses(profile, corrected=False)))),
                    "cwdSha256": hashlib.sha256(str(assembly.parent).encode()).hexdigest(),
                    "inputFiles": {f"runtime-input-{faulty_id}.json": evidence.digest(faulty_manifest),
                                   "runtime-owner.json": evidence.digest(self.owner),
                                   manifest["runInputsPath"]: evidence.digest(self.inputs),
                                   settings_path: hashlib.sha256(settings_raw).hexdigest(), **images}}
                retained = {1: evidence.canonical_bytes(record), 2: evidence.canonical_bytes({"startedMs": 10})}
                run.read_execution_record = lambda sequence: retained[sequence]
                execution = {
                    "schemaVersion": 1, "qualification": False, "nativeContainment": True,
                    "runId": run.run_id, "rootId": run.root_id, "invocationGroupId": self.inputs["invocationGroupId"],
                    "attemptId": faulty_id, "purpose": "execution", "commandSequence": 1,
                    "inputsSha256": evidence.digest(self.inputs), "executionRecordSha256": evidence.digest(record),
                    "manifestSha256": evidence.digest(faulty_manifest),
                    "settingsSha256": hashlib.sha256(settings_raw).hexdigest()}
                execution_path = root / f"proofs/category-command-{faulty_id}-execution.json"
                native_path = root / "proofs/execution-command-0001.json"
                link = {"schemaVersion": 1, "qualification": False, "runId": run.run_id,
                        "invocationGroupId": self.inputs["invocationGroupId"], "attemptId": corrected_id,
                        "inputsSha256": evidence.digest(self.inputs), "profileId": profile,
                        "faultyAttemptId": faulty_id, "commandSequence": 1}
                link_path = root / f"proofs/category-mutation-{corrected_id}-fault.json"
                write(link_path, evidence.canonical_bytes(link))
                write(execution_path, evidence.canonical_bytes(execution))
                write(native_path, retained[1])

                def admit():
                    return sources.category_mutation_observations(
                        run, self.inputs, manifest, observed, sequence=2, started_ms=9, ended_ms=12)

                facts, packets = admit()
                self.assertEqual({row["testIdentity"] for row in facts}, corrected.keys())
                self.assertEqual({row["sourceProofSha256"] for row in facts}, {row["proofSha256"] for row in failed})
                self.assertIn(f"proofs/execution-command-0001.json", packets)
                write(root / f"runtime-input-{corrected_id}.json", transport["manifest_data"])
                current_settings = root / "stores" / f"settings-{corrected_id}.runsettings"
                current_settings_raw = sources.runtime_settings(
                    root, assembly, corrected_id, evidence.digest(manifest), evidence.digest(self.owner), environment)
                write(current_settings, current_settings_raw)
                current_record = {
                    **record, "sequence": 2, "startedMs": 10, "endedMs": 12, "exitCode": 0,
                    "argvSha256": evidence.digest(sources.runtime_arguments(assembly, current_settings, tuple(corrected))),
                    "inputFiles": {f"runtime-input-{corrected_id}.json": evidence.digest(manifest),
                                   "runtime-owner.json": evidence.digest(self.owner),
                                   manifest["runInputsPath"]: evidence.digest(self.inputs),
                                   current_settings.relative_to(root).as_posix(): hashlib.sha256(
                                       current_settings_raw).hexdigest(), **images}}
                retained[2] = evidence.canonical_bytes(current_record)
                write(root / "proofs/execution-command-0002.json", retained[2])
                write(root / f"proofs/category-command-{corrected_id}-execution.json", evidence.canonical_bytes({
                    **execution, "attemptId": corrected_id, "commandSequence": 2,
                    "executionRecordSha256": evidence.digest(current_record), "manifestSha256": evidence.digest(manifest),
                    "settingsSha256": hashlib.sha256(current_settings_raw).hexdigest()}))
                receipt = {
                    "schemaVersion": 1, "qualification": False, "mode": f"category-{profile}-mutation-repair",
                    "runId": run.run_id, "invocationGroupId": self.inputs["invocationGroupId"],
                    "attemptId": corrected_id, "inputsSha256": evidence.digest(self.inputs), "observations": facts}
                write(root / f'proofs/{receipt["mode"]}-{corrected_id}.json', evidence.canonical_bytes(receipt))
                with mock.patch.object(checks, "OwnedRun", SimpleNamespace):
                    parent = checks.category_source_parent(
                        run, self.inputs, manifest, observed,
                        {"sourceExecutions": 2, "mutationProofsSha256": evidence.digest(receipt)},
                        category_scope=(profile, "mutation-repair"),
                        result=SimpleNamespace(exit_code=0, execution_record_sha256=evidence.digest(current_record)))
                native = object.__new__(sources.NativeCategorySources)
                native._run, native._selected = run, inspection
                admitted = native._corroborate(
                    self.inputs, manifest, observed, category_scope=(profile, "mutation-repair"),
                    manifest_data=transport["manifest_data"], owner_data=transport["owner_data"],
                    started_ms=9, ended_ms=12)
                self.assertEqual(set(admitted["sourceParents"].values()), {parent})
                self.assertTrue(packets.keys() <= admitted["sourceProofs"].keys())
                for mutation in ("argv", "cwd", "inputs", "exit", "old-command", "overlap", "replaced-record", "setup-failure",
                                 "settings", "missing-row", "borrowed-image", "missing-negative", "old-attempt"):
                    changed = copy.deepcopy(record)
                    changed_execution = dict(execution)
                    if mutation in ("argv", "cwd"):
                        changed[mutation + "Sha256"] = "0" * 64
                    elif mutation == "inputs":
                        changed["inputFiles"].pop((directory / "Hoard.Testing.Conformance.dll").as_posix())
                    elif mutation == "exit":
                        changed["exitCode"] = 0
                    elif mutation == "old-command":
                        changed["startedMs"] = 8
                    elif mutation == "overlap":
                        changed["endedMs"] = 11
                    elif mutation == "settings":
                        write(settings, settings_raw + b" ")
                    elif mutation == "missing-row":
                        changed_observed = {**observed, "witnesses": observed["witnesses"][:-1]}
                    elif mutation == "borrowed-image":
                        changed_manifest = copy.deepcopy(manifest)
                        changed_manifest["assemblies"][1]["sha256"] = "0" * 64
                    elif mutation == "missing-negative":
                        write(root / f"runtime-{faulty_id}/witnesses.jsonl",
                              evidence.canonical_bytes(failed[0]) + b"\n")
                    elif mutation == "old-attempt":
                        write(link_path, evidence.canonical_bytes({**link, "faultyAttemptId": corrected_id}))
                    elif mutation == "setup-failure":
                        other = catalog.CATEGORY_MUTATION_METHODS["artifacts" if profile == "metadata" else "metadata"][2]
                        foreign_manifest = copy.deepcopy(faulty_manifest)
                        for entry in foreign_manifest["expected"]:
                            entry["assertionSymbol"] = other
                        foreign_manifest_raw = evidence.canonical_bytes(foreign_manifest)
                        write(root / f"runtime-input-{faulty_id}.json", foreign_manifest_raw)
                        foreign_rows = []
                        for row in failed:
                            proof_path = f'proof-{row["executionId"]}.json'
                            proof = evidence.load_json(faulty["proofs"][proof_path])
                            proof.update(assertionSymbol=other, manifestSha256=evidence.digest(foreign_manifest))
                            write(root / f"runtime-{faulty_id}" / proof_path, evidence.canonical_bytes(proof))
                            foreign_rows.append({**row, "proofSha256": evidence.digest(proof)})
                        foreign_lines = b"".join(evidence.canonical_bytes(row) + b"\n" for row in foreign_rows)
                        write(root / f"runtime-{faulty_id}/witnesses.jsonl", foreign_lines)
                        write(root / f"runtime-{faulty_id}/completion.json", evidence.canonical_bytes({
                            **completion, "manifestSha256": evidence.digest(foreign_manifest),
                            "recordsSha256": hashlib.sha256(foreign_lines).hexdigest()}))
                        foreign_settings = sources.runtime_settings(
                            root, assembly, faulty_id, evidence.digest(foreign_manifest),
                            evidence.digest(self.owner), environment)
                        write(settings, foreign_settings)
                        changed["inputFiles"].update({
                            f"runtime-input-{faulty_id}.json": evidence.digest(foreign_manifest),
                            settings_path: hashlib.sha256(foreign_settings).hexdigest()})
                        changed_execution.update(manifestSha256=evidence.digest(foreign_manifest),
                                                 settingsSha256=hashlib.sha256(foreign_settings).hexdigest())
                    raw = evidence.canonical_bytes(changed)
                    retained[1] = evidence.canonical_bytes(record) if mutation == "replaced-record" else raw
                    if mutation == "replaced-record":
                        raw = evidence.canonical_bytes({**record, "childPid": 456})
                    write(native_path, raw)
                    write(execution_path, evidence.canonical_bytes({
                        **changed_execution, "executionRecordSha256": hashlib.sha256(raw).hexdigest()}))
                    with self.subTest(mutation=mutation), self.assertRaises(evidence.ConformanceError):
                        sources.category_mutation_observations(
                            run, self.inputs, changed_manifest if mutation == "borrowed-image" else manifest,
                            changed_observed if mutation == "missing-row" else observed,
                            sequence=2, started_ms=9, ended_ms=12)
                    retained[1] = evidence.canonical_bytes(record)
                    write(settings, settings_raw)
                    write(root / f"runtime-{faulty_id}/witnesses.jsonl", faulty["witnesses_data"])
                    write(link_path, evidence.canonical_bytes(link))
                    write(root / f"runtime-input-{faulty_id}.json", faulty["manifest_data"])
                    for path, original in {**faulty["proofs"], "completion.json": faulty["completion_data"]}.items():
                        write(root / f"runtime-{faulty_id}" / path, original)

    def test_native_inspection_admission_rechecks_the_complete_source_and_command_graph(self):
        import conformance_case_catalog as catalog
        import conformance_sources as sources
        from types import SimpleNamespace
        from xml.sax.saxutils import escape

        self.category_history(mode="qualification")
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
