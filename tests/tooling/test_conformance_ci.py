"""Transport controls are modeled diagnostics, not runtime qualification."""

import copy
import contextlib
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_case_catalog as catalog
import conformance_evidence as evidence


class ConformanceProfileTransportTests(unittest.TestCase):
    def setUp(self):
        from test_conformance_evidence import ConformanceAdmissionTests

        self.reports = {}
        self.inputs = {}
        self.jobs = {}
        for index, profile in enumerate(evidence.PROFILES):
            report = ConformanceAdmissionTests().report()
            inputs = report["inputs"]
            inputs.update(profileId=profile, mode="qualification", sourceState="clean-ci",
                          runId=str(uuid.uuid4()), bindings=[], invocation=["profile", profile])
            inputs["budgets"]["profileSeconds"] = 3600
            inputs["environment"]["freeBytes"] = (24 + index) * 1024**3
            inputs["environment"]["runnerImage"] = "runner-" + profile
            inputs["environmentSha256"] = evidence.digest(inputs["environment"])
            inputs["configurationSha256"] = hashlib.sha256(("configuration-" + profile).encode()).hexdigest()
            inputs["packages"][0]["sha256"] = hashlib.sha256(profile.encode()).hexdigest()
            case = catalog.expected_cases(profile)[0]
            report.update(state="Incomplete", qualification=False, witnesses=[], results=[{
                "runId": inputs["runId"], "profileId": profile, "bindingId": case.binding_id,
                "matrixId": case.matrix_id, "caseId": case.case_id, "status": "Incomplete",
                "applicable": True, "exclusionRule": "none", "proofSha256": [],
                "attempts": [{"sequence": 1, "startedMs": 0, "endedMs": 1,
                              "status": "Incomplete", "witnessIds": [], "proofSha256": [],
                              "diagnosticCode": "EvidenceIncomplete"}],
            }])
            report["postInputSha256"] = evidence.digest(inputs)
            self.reports[profile] = report
            self.inputs[profile] = copy.deepcopy(inputs)
            self.jobs[profile] = {"job": "success", "upload": "success", "download": "success"}

    def inspect(self):
        inspector = importlib.import_module("conformance_ci").inspect_profile_transports
        packets = {profile: evidence.canonical_bytes(report) for profile, report in self.reports.items()}
        pins = {profile: hashlib.sha256(raw).hexdigest() for profile, raw in packets.items()}
        return inspector(packets, expected_inputs=self.inputs, expected_report_sha256=pins,
                         job_results=self.jobs)

    def test_all_five_distinct_assignments_are_inspectable_but_cannot_qualify(self):
        observed = self.inspect()
        self.assertFalse(observed["qualification"])
        self.assertEqual(observed["code"], "EvidenceIncomplete")
        self.assertEqual(observed["scope"], "profile-transport-consistency-diagnostic")
        self.assertEqual(set(observed["profiles"]), set(evidence.PROFILES))
        self.assertEqual(len({row["environmentSha256"] for row in self.inputs.values()}), 5)
        self.assertEqual(len({row["packages"][0]["sha256"] for row in self.inputs.values()}), 5)
        self.assertEqual(len({row["configurationSha256"] for row in self.inputs.values()}), 5)
        self.assertNotIn(b"runner-", evidence.canonical_bytes(observed))

    def test_local_and_ci_use_the_same_independent_profile_inventories(self):
        ci = self.inspect()
        for profile in evidence.PROFILES:
            self.reports[profile]["inputs"]["sourceState"] = "clean-local"
            self.inputs[profile]["sourceState"] = "clean-local"
            self.reports[profile]["postInputSha256"] = evidence.digest(self.inputs[profile])
        local = self.inspect()
        self.assertEqual(local["expectedCaseCounts"], ci["expectedCaseCounts"])
        self.assertEqual(dict(local["expectedCaseCounts"]), {
            profile: len(catalog.expected_cases(profile)) for profile in evidence.PROFILES})
        self.assertFalse(local["qualification"])

    def test_missing_extra_and_misassigned_profiles_reject(self):
        for defect in ("report", "inputs", "job", "extra", "assignment"):
            with self.subTest(defect=defect):
                reports, inputs, jobs = copy.deepcopy((self.reports, self.inputs, self.jobs))
                if defect == "report":
                    del self.reports["harness"]
                elif defect == "inputs":
                    del self.inputs["harness"]
                elif defect == "job":
                    del self.jobs["harness"]
                elif defect == "extra":
                    self.reports["foreign"] = self.reports["metadata"]
                else:
                    self.reports["metadata"], self.reports["artifacts"] = (
                        self.reports["artifacts"], self.reports["metadata"])
                with self.assertRaises(evidence.ConformanceError):
                    self.inspect()
                self.reports, self.inputs, self.jobs = reports, inputs, jobs

    def test_job_upload_download_failure_cancellation_and_missing_status_reject(self):
        for phase in ("job", "upload", "download"):
            for status in ("failure", "cancelled", "skipped", "timed_out", "neutral", "", None):
                with self.subTest(phase=phase, status=status):
                    self.jobs["artifacts"][phase] = status
                    with self.assertRaises(evidence.ConformanceError):
                        self.inspect()
            del self.jobs["artifacts"][phase]
            with self.assertRaises(evidence.ConformanceError):
                self.inspect()
            self.jobs["artifacts"][phase] = "success"
        self.jobs["artifacts"]["unknown"] = "success"
        with self.assertRaises(evidence.ConformanceError):
            self.inspect()

    def test_foreign_common_context_rejects_even_when_each_assignment_matches(self):
        for field, value in (("invocationGroupId", str(uuid.uuid4())),
                             ("sourceRevision", "f" * 40), ("catalogSha256", "f" * 64),
                             ("sdkSha256", "f" * 64), ("sourceState", "clean-local")):
            with self.subTest(field=field):
                original = self.inputs["harness"][field]
                self.inputs["harness"][field] = value
                self.reports["harness"]["inputs"][field] = value
                with self.assertRaises(evidence.ConformanceError):
                    self.inspect()
                self.inputs["harness"][field] = original
                self.reports["harness"]["inputs"][field] = original

    def test_focused_preparation_dirty_and_changed_original_inputs_reject(self):
        for field, value in (("mode", "diagnostic"), ("mode", "preparation"),
                             ("sourceState", "dirty-local"), ("configurationSha256", "f" * 64),
                             ("environmentSha256", "f" * 64)):
            with self.subTest(field=field, value=value):
                original = self.reports["metadata"]["inputs"][field]
                self.reports["metadata"]["inputs"][field] = value
                with self.assertRaises(evidence.ConformanceError):
                    self.inspect()
                self.reports["metadata"]["inputs"][field] = original

    def test_matching_nonqualifying_assignments_reject_before_cross_profile_mismatch(self):
        for field, value in (("mode", "diagnostic"), ("mode", "preparation"), ("sourceState", "dirty-local")):
            reports, inputs = copy.deepcopy((self.reports, self.inputs))
            for profile in evidence.PROFILES:
                self.reports[profile]["inputs"][field] = value
                self.inputs[profile][field] = value
                self.reports[profile]["postInputSha256"] = evidence.digest(self.inputs[profile])
            with self.subTest(field=field, value=value), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceIncomplete$"):
                self.inspect()
            self.reports, self.inputs = reports, inputs

    def test_foreign_evaluator_source_rejects_even_with_matching_revision_and_assignment(self):
        inputs = self.reports["harness"]["inputs"]
        inputs["sourceManifest"]["scripts/conformance_evidence.py"] = "f" * 64
        inputs["sourceManifestSha256"] = evidence.digest(inputs["sourceManifest"])
        self.inputs["harness"] = copy.deepcopy(inputs)
        self.reports["harness"]["postInputSha256"] = evidence.digest(inputs)
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.inspect()

    def test_external_report_pins_and_unique_run_identities_are_required(self):
        inspector = importlib.import_module("conformance_ci").inspect_profile_transports
        packets = {profile: evidence.canonical_bytes(report) for profile, report in self.reports.items()}
        pins = {profile: hashlib.sha256(raw).hexdigest() for profile, raw in packets.items()}
        for defect in ("missing", "different", "bytes"):
            with self.subTest(defect=defect):
                changed, supplied = dict(packets), dict(pins)
                if defect == "missing":
                    del supplied["metadata"]
                elif defect == "different":
                    supplied["metadata"] = "f" * 64
                else:
                    changed["metadata"] += b"\n"
                with self.assertRaises(evidence.ConformanceError):
                    inspector(changed, expected_inputs=self.inputs, expected_report_sha256=supplied,
                              job_results=self.jobs)
        run_id = self.inputs["metadata"]["runId"]
        self.inputs["harness"]["runId"] = run_id
        self.reports["harness"]["inputs"]["runId"] = run_id
        self.reports["harness"]["results"][0]["runId"] = run_id
        with self.assertRaises(evidence.ConformanceError):
            self.inspect()

    def coordinator(self):
        configuration = {
            "revision": evidence.CATALOG_REVISION, "stores": "fresh-owned-synthetic",
            "restore": "locked", "runtimeLogger": "HoardSafe", "consoleLogger": False,
            "sources": {"packageSources": {
                "local": "isolated-current-archives", "nuget.org": "https://api.nuget.org/v3/index.json"},
                "packageSourceMapping": {"local": ["Hoard.*"], "nuget.org": ["*"]}}}
        profiles = {}
        for profile in evidence.PROFILES:
            selected = copy.deepcopy(configuration)
            if profile == "harness":
                selected["sources"] = {
                    "packageSources": {"frozen": "isolated-frozen-archives"},
                    "archives": {"Example.1.0.0.nupkg": "a" * 64}}
            self.inputs[profile]["configurationSha256"] = evidence.digest(selected)
            self.reports[profile]["inputs"]["configurationSha256"] = evidence.digest(selected)
            self.reports[profile]["postInputSha256"] = evidence.digest(self.inputs[profile])
            profiles[profile] = {
                "inputs": copy.deepcopy(self.inputs[profile]),
                "reportSha256": evidence.digest(self.reports[profile]),
                "reportPath": f"proofs/category-{profile}-qualification-report.json",
                "configuration": selected, "jobResults": copy.deepcopy(self.jobs[profile])}
        return {"schemaVersion": 1, "profiles": profiles}

    def test_coordinator_binds_configuration_preimages_without_equal_profile_fingerprints(self):
        ci = importlib.import_module("conformance_ci")
        context = self.coordinator()
        admitted = ci.admit_coordinator(context)
        self.assertNotEqual(admitted["profiles"]["metadata"]["inputs"]["configurationSha256"],
                            admitted["profiles"]["harness"]["inputs"]["configurationSha256"])
        self.assertEqual(admitted["configurationPolicySha256"], evidence.digest({
            "revision": evidence.CATALOG_REVISION, "stores": "fresh-owned-synthetic",
            "restore": "locked", "runtimeLogger": "HoardSafe", "consoleLogger": False}))
        context["profiles"]["metadata"]["configuration"]["restore"] = "unlocked"
        self.assertEqual(admitted["profiles"]["metadata"]["configuration"]["restore"], "locked")
        with self.assertRaises(evidence.ConformanceError):
            ci.admit_coordinator(context)

    def test_coordinator_rejects_foreign_configuration_policy_and_changed_preimages(self):
        ci = importlib.import_module("conformance_ci")
        original = self.coordinator()
        for defect in ("hash", "policy", "source", "field", "extra-profile", "duplicate-run", "version"):
            context = copy.deepcopy(original)
            entry = context["profiles"]["metadata"]
            if defect == "hash":
                entry["inputs"]["configurationSha256"] = "f" * 64
            elif defect == "policy":
                entry["configuration"]["consoleLogger"] = True
                entry["inputs"]["configurationSha256"] = evidence.digest(entry["configuration"])
            elif defect == "source":
                entry["configuration"]["sources"]["packageSources"]["local"] = "/private/canary"
                entry["inputs"]["configurationSha256"] = evidence.digest(entry["configuration"])
            elif defect == "field":
                entry["qualification"] = True
            elif defect == "extra-profile":
                context["profiles"]["service"] = copy.deepcopy(entry)
            elif defect == "duplicate-run":
                context["profiles"]["harness"]["inputs"]["runId"] = entry["inputs"]["runId"]
            else:
                context["schemaVersion"] = True
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                ci.admit_coordinator(context)

    def test_coordinator_configuration_preimage_preserves_opaque_inspection_assignments(self):
        ci = importlib.import_module("conformance_ci")
        context = self.coordinator()
        entry = context["profiles"]["metadata"]
        private = "/private/connection-canary/inspection.json"
        identity = next(iter(set(catalog.ORIGINAL_INSPECTION_WITNESSES)
                             - set(catalog.ORIGINAL_INSPECTION_LITERAL_WITNESSES)))
        configuration = evidence.configuration_record(
            entry["configuration"]["sources"], inspection_inputs={identity: {private: "a" * 64}})
        entry["configuration"] = configuration
        entry["inputs"]["configurationSha256"] = evidence.digest(configuration)
        admitted = ci.admit_coordinator(context)
        self.assertNotIn(private.encode(), evidence.canonical_bytes(admitted))
        files = configuration["inspectionInputs"][identity]
        self.assertEqual(files, {hashlib.sha256(private.encode()).hexdigest(): "a" * 64})
        configuration["inspectionInputs"][identity] = {private: "a" * 64}
        entry["inputs"]["configurationSha256"] = evidence.digest(configuration)
        with self.assertRaises(evidence.ConformanceError):
            ci.admit_coordinator(context)

    def test_coordinator_does_not_infer_missing_jobs_or_profiles_from_green_reports(self):
        ci = importlib.import_module("conformance_ci")
        original = self.coordinator()
        for defect in ("missing-profile", "job", "upload", "download", "missing-status"):
            context = copy.deepcopy(original)
            if defect == "missing-profile":
                del context["profiles"]["harness"]
            elif defect == "missing-status":
                del context["profiles"]["artifacts"]["jobResults"]["download"]
            else:
                context["profiles"]["artifacts"]["jobResults"][defect] = "cancelled"
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                ci.admit_coordinator(context, require_all=True)

    def qualification_origin(self, profile, entry):
        category = profile in ("metadata", "artifacts")
        original = (f"proofs/category-{profile}-qualification-report.json" if category
                    else f"proofs/{profile}-runtime-released-report.json")
        origin = {
            "kind": "native-" + ("category" if category else profile) + "-fixture-qualification",
            "inputsSha256": evidence.digest(entry["inputs"]), "reportSha256": entry["reportSha256"],
            "originalReportPath": original, "originalReportSha256": "a" * 64,
            "resourcesSha256": "b" * 64}
        if profile == "compatibility":
            origin.update(summaryPath="proofs/compatibility-diagnostic-summary.json",
                          summarySha256="c" * 64)
        return origin

    def qualified_coordinator(self, context, profiles):
        entries = {}
        for profile in profiles:
            entry = {key: value for key, value in context["profiles"][profile].items()
                     if key != "configuration"}
            entry["qualificationOrigin"] = self.qualification_origin(profile, entry)
            entries[profile] = entry
        return {"schemaVersion": 2, "configurationPolicy": dict(evidence.configuration_policy()), "profiles": entries}

    def test_coordinator_pins_external_original_receipts_and_freezes_their_fields(self):
        ci = importlib.import_module("conformance_ci")
        for profile in ("metadata", "artifacts", "composition", "compatibility"):
            with self.subTest(profile=profile):
                context = self.qualified_coordinator(self.coordinator(), (profile,))
                entry = context["profiles"][profile]
                admitted = ci.admit_coordinator(context)
                origin = admitted["profiles"][profile]["qualificationOrigin"]
                entry["qualificationOrigin"]["resourcesSha256"] = "d" * 64
                self.assertEqual(origin["resourcesSha256"], "b" * 64)
                for defect in ("inputsSha256", "reportSha256", "kind", "extra"):
                    changed = copy.deepcopy(context)
                    candidate = changed["profiles"][profile]["qualificationOrigin"]
                    candidate[defect] = "f" * 64
                    with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                        ci.admit_coordinator(changed)

    def test_public_verify_uses_only_the_separately_trusted_receipt_and_exact_assignment(self):
        import conformance_cli

        with tempfile.TemporaryDirectory() as temporary:
            directory, coordinator, context = self.aggregate_fixture(Path(temporary).resolve())
            context = self.qualified_coordinator(context, ("composition",))
            entry = context["profiles"]["composition"]
            coordinator.write_bytes(evidence.canonical_bytes(context))
            report = directory / "composition" / entry["reportPath"]
            raw = report.read_bytes()
            output = io.StringIO()
            with mock.patch("conformance_ci.inspect_receipted_profile_qualification", return_value={
                    "qualification": True, "baselineQualification": False, "code": "None",
                    "profileId": "composition", "reportSha256": entry["reportSha256"]}) as reader:
                with contextlib.redirect_stdout(output):
                    result = conformance_cli.main([
                        "--verify", str(report), "--coordinator", str(coordinator)])
            self.assertEqual(result, 0)
            reader.assert_called_once_with(
                directory / "composition", raw, expected_inputs=evidence.admit_entity("RunInputs", entry["inputs"]),
                expected_report_sha256=entry["reportSha256"],
                qualification_origin=evidence.admit_qualification_origin(
                    entry["qualificationOrigin"], profile="composition"))
            packet = json.loads(output.getvalue())
            self.assertTrue(packet["qualification"])
            self.assertFalse(packet["baselineQualification"])
            self.assertNotIn(str(directory), output.getvalue())

    def test_native_local_assignments_do_not_invent_ci_transfer_status_or_allow_ci_omission(self):
        ci = importlib.import_module("conformance_ci")
        context = self.qualified_coordinator(self.coordinator(), ("metadata",))
        entry = context["profiles"]["metadata"]
        entry["jobResults"].update(upload="not-required", download="not-required")
        with self.assertRaises(evidence.ConformanceError):
            ci.admit_coordinator(context)
        entry["inputs"]["sourceState"] = "clean-local"
        entry["qualificationOrigin"]["inputsSha256"] = evidence.digest(entry["inputs"])
        admitted = ci.admit_coordinator(context)
        self.assertEqual(admitted["profiles"]["metadata"]["jobResults"]["upload"], "not-required")
        entry["jobResults"]["job"] = "cancelled"
        with self.assertRaises(evidence.ConformanceError):
            ci.admit_coordinator(context)

    def test_receipted_coordinator_requires_the_common_policy_and_clean_qualifying_inputs(self):
        ci = importlib.import_module("conformance_ci")
        original = self.qualified_coordinator(self.coordinator(), ("metadata",))
        for defect in ("policy", "diagnostic", "preparation", "dirty", "missing-receipt", "extra"):
            context = copy.deepcopy(original)
            entry = context["profiles"]["metadata"]
            if defect == "policy":
                context["configurationPolicy"]["restore"] = "unlocked"
            elif defect in ("diagnostic", "preparation"):
                entry["inputs"]["mode"] = defect
            elif defect == "dirty":
                entry["inputs"]["sourceState"] = "dirty-local"
            elif defect == "missing-receipt":
                del entry["qualificationOrigin"]
            else:
                context["qualification"] = True
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                ci.admit_coordinator(context)

    def test_receipted_dispatch_rejects_missing_authority_and_unimplemented_harness(self):
        context = self.coordinator()
        for profile in evidence.PROFILES:
            entry = context["profiles"][profile]
            with self.subTest(profile=profile), self.assertRaises(evidence.ConformanceError):
                evidence.inspect_receipted_profile_qualification(
                    Path("."), evidence.canonical_bytes(self.reports[profile]),
                    expected_inputs=entry["inputs"], expected_report_sha256=entry["reportSha256"],
                    qualification_origin=None)

    def test_receipted_aggregate_cannot_promote_four_profiles_without_harness_authority(self):
        import conformance_cli

        with tempfile.TemporaryDirectory() as temporary:
            directory, coordinator, context = self.aggregate_fixture(Path(temporary).resolve())
            context = self.qualified_coordinator(
                context, ("metadata", "artifacts", "composition", "compatibility"))
            coordinator.write_bytes(evidence.canonical_bytes(context))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = conformance_cli.main([
                    "--aggregate", str(directory), "--coordinator", str(coordinator)])
            packet = json.loads(output.getvalue())
            self.assertNotEqual(result, 0)
            self.assertFalse(packet["qualification"])
            self.assertEqual(packet["code"], "EvidenceIncomplete")

    def aggregate_fixture(self, parent):
        context = self.coordinator()
        directory = parent / "profiles"
        directory.mkdir()
        for profile in evidence.PROFILES:
            root = directory / profile
            (root / "proofs").mkdir(parents=True)
            entry = context["profiles"][profile]
            inputs = entry["inputs"]
            completion = f"proofs/category-{profile}-qualification-completion-inputs.json"
            (root / completion).write_bytes(evidence.canonical_bytes(inputs))
            (root / completion).chmod(0o400)
            attempt = {
                "sequence": 1, "startedMs": 0, "endedMs": 1, "status": "Incomplete",
                "witnessIds": [], "proofSha256": [], "diagnosticCode": "EvidenceIncomplete"}
            report = {
                **self.reports[profile], "inputs": inputs, "postInputSha256": evidence.digest(inputs),
                "proofs": {completion: evidence.digest(inputs)},
                "results": [evidence._catalog_case_result(
                    inputs, case, "NotApplicable" if case.exclusion else "Incomplete",
                    () if case.exclusion else (attempt,)) for case in catalog.expected_cases(profile)]}
            raw = evidence.canonical_bytes(report)
            (root / entry["reportPath"]).write_bytes(raw)
            entry["reportSha256"] = hashlib.sha256(raw).hexdigest()
        coordinator = parent / "trusted-coordinator.json"
        coordinator.write_bytes(evidence.canonical_bytes(context))
        return directory, coordinator, context

    def test_public_aggregate_checks_all_five_complete_inventories_but_never_qualifies_empty_models(self):
        import conformance_cli

        with tempfile.TemporaryDirectory() as temporary:
            directory, coordinator, context = self.aggregate_fixture(Path(temporary).resolve())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = conformance_cli.main([
                    "--aggregate", str(directory), "--coordinator", str(coordinator)])
            self.assertEqual(result, 2)
            packet, = (json.loads(row) for row in output.getvalue().splitlines())
            self.assertFalse(packet["qualification"])
            self.assertEqual(packet["scope"], "five-profile-structure-diagnostic")
            self.assertEqual(set(packet["profiles"]), set(evidence.PROFILES))
            for profile, observed in packet["profiles"].items():
                self.assertEqual(observed["caseCount"], len(catalog.expected_cases(profile)))
                self.assertEqual(observed["caseStates"]["Passed"], 0)
                self.assertEqual(observed["reportSha256"], context["profiles"][profile]["reportSha256"])
            self.assertNotIn(str(directory), output.getvalue())

    def test_aggregate_rejects_resealed_missing_cases_in_each_profile(self):
        import conformance_cli

        for profile in evidence.PROFILES:
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temporary:
                directory, coordinator, context = self.aggregate_fixture(Path(temporary).resolve())
                entry = context["profiles"][profile]
                path = directory / profile / entry["reportPath"]
                report = json.loads(path.read_bytes())
                report["results"].pop()
                path.write_bytes(evidence.canonical_bytes(report))
                entry["reportSha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                coordinator.write_bytes(evidence.canonical_bytes(context))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result = conformance_cli.main([
                        "--aggregate", str(directory), "--coordinator", str(coordinator)])
                self.assertEqual(result, 1)
                packet, = (json.loads(row) for row in output.getvalue().splitlines())
                self.assertEqual(packet["code"], "WitnessMissing")
                self.assertFalse(packet["qualification"])
                self.assertNotIn("profiles", packet)

    def test_aggregate_keeps_failed_attempt_after_passing_modeled_retry(self):
        import conformance_cli

        with tempfile.TemporaryDirectory() as temporary:
            directory, coordinator, context = self.aggregate_fixture(Path(temporary).resolve())
            entry = context["profiles"]["harness"]
            path = directory / "harness" / entry["reportPath"]
            report = json.loads(path.read_bytes())
            inputs = report["inputs"]
            result = next(row for row in report["results"] if row["caseId"] == "QC-38")
            result["attempts"][0].update(status="Failed", diagnosticCode="AssertionFailed")
            execution = str(uuid.uuid4())
            raw, relative = b"modeled-retry-proof", "proofs/modeled-retry.json"
            proof = directory / "harness" / relative
            proof.write_bytes(raw)
            proof.chmod(0o400)
            hashed = hashlib.sha256(raw).hexdigest()
            report["proofs"][relative] = hashed
            report["witnesses"] = [{
                "executionId": execution, "runId": inputs["runId"],
                "invocationGroupId": inputs["invocationGroupId"], "testIdentity": "Modeled.Retry",
                "bindingId": "none", "matrixId": "none", "packageSha256": inputs["packages"][0]["sha256"],
                "assemblySha256": next(iter(inputs["runtimeAssemblies"].values())),
                "inputSha256": evidence.digest(inputs), "startedMs": 2, "endedMs": 3,
                "status": "Passed", "proofSha256": hashed}]
            result.update(status="Passed", proofSha256=[hashed])
            result["attempts"].append({
                "sequence": 2, "startedMs": 2, "endedMs": 3, "status": "Passed",
                "witnessIds": [execution], "proofSha256": [hashed], "diagnosticCode": "None"})
            path.write_bytes(evidence.canonical_bytes(report))
            entry["reportSha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            coordinator.write_bytes(evidence.canonical_bytes(context))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = conformance_cli.main([
                    "--aggregate", str(directory), "--coordinator", str(coordinator)])
            self.assertEqual(result, 1)
            packet, = (json.loads(row) for row in output.getvalue().splitlines())
            self.assertEqual(packet["code"], "AssertionFailed")
            self.assertEqual(packet["profiles"]["harness"]["failedAttemptCount"], 1)
            self.assertFalse(packet["qualification"])


if __name__ == "__main__":
    unittest.main()
