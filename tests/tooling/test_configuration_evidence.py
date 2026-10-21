import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import configuration_evidence as configuration


class ConfigurationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def test_exact_case_inventory_rejects_missing_empty_duplicate_and_partial(self):
        cases = [{"id": case, "tests": list(configuration.REQUIRED_TESTS[case]), "passed": True}
                 for case in configuration.CASES]
        configuration.verify_cases(cases)
        for invalid in ([], cases[:-1], cases + [cases[0]],
                        [{**entry, "tests": []} for entry in cases],
                        [{**entry, "passed": False} for entry in cases],
                        ["untrusted-record"] * 36, [{**entry, "id": None} for entry in cases],
                        [{**entry, "tests": "not-a-test-list"} for entry in cases]):
            with self.assertRaisesRegex(RuntimeError, "configuration case"):
                configuration.verify_cases(invalid)

    def test_unrelated_passing_method_per_class_cannot_certify_configuration_scenarios(self):
        names = [f"Hoard.Composition.Tests.{name}.Unrelated_scenario" for name in (
            "ConfigurationSourceTests", "ConfigurationStructureTests", "ConfigurationMergeTests",
            "ConfiguredCompositionTests", "ConfigurationContractTests", "ConfigurationSecretTests",
            "ConfigurationCoordinationTests", "ConfigurationRestartTests", "ConfigurationDistributionTests",
            "ConfigurationVersionTests", "ConfigurationConversionTests", "ConfigurationBoundaryTests")]
        with self.assertRaisesRegex(RuntimeError, "configuration case"):
            configuration.case_inventory(names)

    def test_removing_required_race_pipe_or_commit_scenario_fails_despite_other_class_passes(self):
        names = sorted({name for required in configuration.REQUIRED_TESTS.values() for name in required})
        configuration.case_inventory(names)
        for missing in (
                "ConfigurationSecretTests.Actual_local_pipe_is_rejected_without_waiting_for_secret_bytes",
                "ConfigurationSecretTests.Concurrent_consume_dispose_mutation_and_legacy_attempts_have_one_secret_release_authority",
                "ConfigurationSecretTests.Blocked_configured_delivery_keeps_transferred_secrets_and_prerequisites_without_late_services",
                "ConfigurationSecretTests.Pending_F02_notification_or_cancellation_retains_secrets_and_root_without_deferred_cleanup",
                "ConfigurationSecretTests.Known_secret_failures_keep_the_exact_field_owner_and_winning_source",
                "ConfigurationCoordinationTests.Pending_secret_diagnostics_keep_origin_through_timeout_cancellation_and_late_fault",
                "ConfiguredCompositionTests.Declared_option_rules_keep_effective_field_source_and_safe_action",
                "ConfiguredCompositionTests.Unsupported_active_option_version_keeps_its_explicit_setting_source",
                "ConfigurationSecretTests.Secret_option_rules_keep_effective_source_and_reject_undeclared_results",
                "ConfigurationConversionTests.Committed_publication_remains_published_while_post_commit_work_times_out"):
            with self.subTest(scenario=missing):
                with self.assertRaisesRegex(RuntimeError, "configuration case"):
                    configuration.case_inventory([name for name in names if name != missing])

    def test_subprocess_errors_are_closed_and_bounded(self):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "private-payload")):
            with self.assertRaisesRegex(RuntimeError, "^Configuration command failed: probe$"):
                configuration.run("probe")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("probe", 1, output="private-payload")):
            with self.assertRaisesRegex(RuntimeError, "^Configuration command timed out: probe$"):
                configuration.run("probe")

    def test_local_package_and_retained_binary_provenance(self):
        package = self.root / "Hoard.Fixture.nupkg"
        package.write_bytes(b"original")
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        configuration.verify_binary(package, digest)
        configuration.verify_package(package, self.root, hashlib.sha512(package.read_bytes()).hexdigest())
        for directory in (self.root / "elsewhere", self.root / ".."):
            with self.assertRaisesRegex(RuntimeError, "provenance"):
                configuration.verify_package(package, directory, "stale")
        package.write_bytes(b"changed")
        with self.assertRaisesRegex(RuntimeError, "binary"):
            configuration.verify_binary(package, digest)
        with self.assertRaisesRegex(RuntimeError, "binary"):
            configuration.verify_binary(self.root / "absent", digest)

    def test_platform_acceptance_is_required_and_not_inferred(self):
        for evidence in (None, {}, {"os": "Darwin", "filesystem": "local", "barriers": []},
                         {"os": "Darwin", "filesystem": "local", "barriers": ["staged"]}):
            with self.assertRaisesRegex(RuntimeError, "publication proof"):
                configuration.verify_publication(evidence)
        configuration.verify_publication({
            "os": "Darwin", "filesystem": "local",
            "barriers": list(configuration.PUBLICATION_BARRIERS), "passed": True})

    def test_malformed_test_counters_do_not_reflect_result_payloads(self):
        result = self.root / "result.trx"
        for text in ('<TestRun><Counters total="private-payload" passed="1"/></TestRun>', "private-payload"):
            result.write_text(text)
            with self.assertRaisesRegex(RuntimeError, "^Invalid configuration test result counters.$"):
                configuration.test_count(result)

    def test_default_locks_are_immutable(self):
        lock = self.root / "packages.lock.json"
        lock.write_text("{}")
        before = configuration.lock_hashes(self.root)
        configuration.verify_locks(self.root, before)
        lock.write_text(json.dumps({"changed": True}))
        with self.assertRaisesRegex(RuntimeError, "lock"):
            configuration.verify_locks(self.root, before)

    def test_cleanup_only_accepts_its_own_resolved_workspace(self):
        owned = configuration.create_workspace(self.root)
        sibling = self.root / "unrelated"
        sibling.mkdir()
        for path in (self.root, sibling, owned / ".."):
            with self.assertRaisesRegex(RuntimeError, "workspace"):
                configuration.cleanup_workspace(path)
        configuration.cleanup_workspace(owned)
        self.assertFalse(owned.exists())
        self.assertTrue(sibling.exists())

    def test_full_acceptance_refuses_missing_actual_proof_without_running_suites(self):
        for evidence in ({}, {"graphs": [], "journeys": [], "oldBinaries": []}):
            with self.assertRaisesRegex(RuntimeError, "Missing actual configuration acceptance"):
                configuration.verify_full_evidence(evidence)

    def full_evidence(self):
        feed = self.root / "feed"
        feed.mkdir()
        scans = ("platform", "Protocol.One", "Protocol.Two", "Metadata", "Artifact.One",
                 "Artifact.Two", "Identity", "configured-baseline", "configured-custom",
                 "old-provider", "lifecycle-consumer", "registration", "conversion-process")
        project = self.root / "fixture.csproj"
        project.write_text("<Project/>")
        assets = self.root / "project.assets.json"
        assets.write_text("{}")
        packages = []
        for name in scans[1:7]:
            package = feed / f"{name}.nupkg"
            package.write_bytes(b"synthetic-unit-test-package")
            packages.append({"id": f"Hoard.Fixtures.Lifecycle.{name}", "package": str(package),
                             "sha512": hashlib.sha512(package.read_bytes()).hexdigest(),
                             "project": str(project), "assets": str(assets),
                             "sourceHashes": {"fixture.cs": "a" * 64}})
        binaries = []
        for name in ("LegacyOptions", "LifecycleConsumer"):
            binary = self.root / f"{name}.dll"
            binary.write_bytes(b"synthetic-unit-test-binary")
            binaries.append({"name": name, "baseline": configuration.BASELINE, "assembly": str(binary),
                             "assets": str(assets), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()})
        journeys = [{"name": name, "distribution": distribution, "passed": True, "events": 1,
                     "hostSha256": "b" * 64, "providerAssembly": binaries[0]["assembly"],
                     "providerSha256": binaries[0]["sha256"]}
                    for distribution in ("baseline", "custom")
                    for name in ("configured-one", "configured-two-same-binary", "invalid-replacement",
                                 "explicit-recovery", *(() if distribution == "baseline" else ("configured-custom-artifact",)))]
        return {"graphs": [{"scanId": name, "projects": [{"projectFile": str(project)}],
                            "ownership": {"Fixture": "Metadata"}} for name in scans],
                "packages": packages, "journeys": journeys, "oldBinaries": binaries, "toolingPassed": True,
                "cases": [{"id": case, "passed": True, "tests": list(configuration.REQUIRED_TESTS[case])}
                          for case in configuration.CASES],
                "publication": {"os": "Darwin", "filesystem": "synthetic-local-volume",
                                "barriers": list(configuration.PUBLICATION_BARRIERS), "passed": True}}

    def test_full_inventory_rejects_duplicate_graphs_journeys_binaries_and_missing_packages(self):
        evidence = self.full_evidence()
        configuration.verify_full_evidence(evidence)
        variants = []
        for key in ("graphs", "journeys", "oldBinaries", "packages"):
            duplicate = copy.deepcopy(evidence)
            duplicate[key][-1] = duplicate[key][0]
            variants.append(duplicate)
            missing = copy.deepcopy(evidence)
            missing[key] = missing[key][:-1]
            variants.append(missing)
        for key in ("graphs", "journeys", "oldBinaries", "packages"):
            malformed = copy.deepcopy(evidence)
            malformed[key][0] = "private-payload"
            variants.append(malformed)
        failed = copy.deepcopy(evidence)
        failed["journeys"][0]["passed"] = False
        variants.append(failed)
        empty = copy.deepcopy(evidence)
        empty["graphs"][0]["projects"] = []
        variants.append(empty)
        for invalid in variants:
            with self.subTest(inventory=next((key for key in evidence if evidence[key] != invalid[key]), None)):
                with self.assertRaisesRegex(RuntimeError, "configuration acceptance"):
                    configuration.verify_full_evidence(invalid)

    def test_full_evidence_rechecks_actual_retained_bytes_and_local_package_hashes(self):
        evidence = self.full_evidence()
        configuration.verify_full_evidence(evidence)
        for key, path in (("oldBinaries", "assembly"), ("packages", "package")):
            binary = Path(evidence[key][0][path])
            original = binary.read_bytes()
            binary.write_bytes(b"changed-after-collection")
            with self.assertRaisesRegex(RuntimeError, "binary|provenance|configuration acceptance"):
                configuration.verify_full_evidence(evidence)
            binary.write_bytes(original)

    def test_journeys_require_actual_retained_provider_bytes_not_only_host_hash(self):
        evidence = self.full_evidence()
        configuration.verify_full_evidence(evidence)
        for key in ("providerAssembly", "providerSha256"):
            missing = copy.deepcopy(evidence)
            del missing["journeys"][0][key]
            with self.assertRaisesRegex(RuntimeError, "journey|binary"):
                configuration.verify_full_evidence(missing)
        changed = self.root / "different-runtime-provider.dll"
        changed.write_bytes(b"different-from-retained-provider")
        evidence["journeys"][0]["providerAssembly"] = str(changed)
        with self.assertRaisesRegex(RuntimeError, "journey|binary"):
            configuration.verify_full_evidence(evidence)

    def test_retained_input_manifest_is_closed_and_does_not_copy_unrelated_files(self):
        saved = self.full_evidence()["oldBinaries"]
        directory = self.root / "input"
        directory.mkdir()
        current = []
        for entry in saved:
            owner = directory / entry["name"]
            owner.mkdir()
            source = Path(entry["assembly"])
            destination = owner / source.name
            destination.write_bytes(source.read_bytes())
            entry["assembly"] = str(destination)
            assets = owner / "baseline.assets.json"
            assets.write_text("{}")
            entry["assets"] = str(assets)
            (owner / "private-note.txt").write_text("must-not-copy")
            target = self.root / "target" / entry["name"] / source.name
            target.parent.mkdir(parents=True)
            target.write_bytes(source.read_bytes())
            current.append({**entry, "assembly": str(target)})
        manifest = directory / "retained-binaries.json"
        for invalid in ([None, None], [{**entry, "assembly": 7} for entry in saved],
                        [{**entry, "assets": str(self.root / "project.assets.json")} for entry in saved]):
            manifest.write_text(json.dumps(invalid))
            with self.assertRaisesRegex(RuntimeError, "retained pre-F-03"):
                configuration.retained_inputs(current, directory)
        manifest.write_text(json.dumps(saved))
        configuration.retained_inputs(current, directory)
        for entry in current:
            self.assertFalse((Path(entry["assembly"]).parent / "private-note.txt").exists())

    def test_retained_baseline_is_copied_once_without_overwriting_existing_inputs(self):
        source = self.root / "source"
        source.mkdir()
        binary = source / "LifecycleConsumer.dll"
        binary.write_bytes(b"unchanged-retained-binary")
        assets = source / "project.assets.json"
        assets.write_text("{}")
        entry = {"name": "LifecycleConsumer", "assembly": str(binary), "assets": str(assets),
                 "baseline": configuration.BASELINE, "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
        output = self.root / "retained"
        retained = configuration.retain_baseline([entry], output)
        configuration.verify_binary(Path(retained[0]["assembly"]), entry["sha256"])
        with self.assertRaisesRegex(RuntimeError, "fresh explicit"):
            configuration.retain_baseline([entry], output)

    def test_red_and_green_capture_preserves_real_result_without_claiming_full_acceptance(self):
        work = self.root / "work"
        (work / "results").mkdir(parents=True)
        (work / "results/configuration.trx").write_text("<actual-test-result/>")
        for passed in (False, True):
            output = self.root / ("green" if passed else "red")
            configuration.retain_evidence(work, output, "source-tests", passed)
            report = json.loads((output / "result.json").read_text())
            self.assertEqual("passed" if passed else "failed", report["status"])
            self.assertFalse(report["fullAcceptance"])
            self.assertEqual("<actual-test-result/>", (output / "configuration.trx").read_text())
            with self.assertRaisesRegex(RuntimeError, "fresh explicit"):
                configuration.retain_evidence(work, output, "source-tests", passed)
