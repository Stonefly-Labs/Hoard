"""Transport controls are modeled diagnostics, not runtime qualification."""

import copy
import hashlib
import importlib
from pathlib import Path
import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()
