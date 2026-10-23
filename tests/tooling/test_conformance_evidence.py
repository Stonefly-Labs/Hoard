import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_evidence as evidence


class ConformanceAdmissionTests(unittest.TestCase):
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


class ConformanceBaselineTests(unittest.TestCase):
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
