import hashlib
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_sdk_checks as checks


class SdkDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / ".foundation" / ("sdk-diagnostic-test-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True, mode=0o700)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_unsupported_platform_never_allocates_or_prepares(self):
        with patch.object(checks, "native_execution_supported", return_value=False), \
                patch.object(checks.OwnedRun, "allocate") as allocate, \
                patch.object(checks.baselines, "prepare") as prepare:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
                checks.execute(ROOT, self.directory / "run")
        allocate.assert_not_called()
        prepare.assert_not_called()

    def test_preparation_and_seal_verification_precede_candidate_snapshot(self):
        calls = []
        seal = self.directory / "baselines.json"
        seal.write_bytes(b"sealed")
        run = SimpleNamespace(root=self.directory, deadline=float("inf"), state="Allocated",
                              live_children=lambda: False)
        run.transition = lambda state: setattr(run, "state", state)

        def prepare(*args):
            self.assertTrue((run.root / "cache/.local/share").is_dir())
            self.assertEqual((run.root / "cache/.local").stat().st_mode & 0o777, 0o700)
            calls.append("prepare")
            return seal

        def verify(*args):
            calls.append("verify")
            return {}

        def snapshot(*args):
            calls.append("snapshot")
            raise checks.evidence.ConformanceError("InputChanged")

        with patch.object(checks, "native_execution_supported", return_value=True), \
                patch.object(checks.OwnedRun, "allocate", return_value=run), \
                patch.object(checks.baselines, "prepare", side_effect=prepare), \
                patch.object(checks.baselines, "verify_prepared_baselines", side_effect=verify), \
                patch.object(checks, "snapshot", side_effect=snapshot), \
                patch.object(checks, "build") as build:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.execute(ROOT, self.directory / "run")
        self.assertEqual(calls, ["prepare", "verify", "snapshot"])
        build.assert_not_called()
        self.assertEqual(run.state, "Settling")

    def test_invalid_baseline_seal_never_snapshots_or_compiles_candidate(self):
        seal = self.directory / "baselines.json"
        seal.write_bytes(b"sealed")
        run = SimpleNamespace(root=self.directory, deadline=float("inf"), state="Active",
                              live_children=lambda: True)
        run.transition = lambda state: setattr(run, "state", state)
        with patch.object(checks, "native_execution_supported", return_value=True), \
                patch.object(checks.OwnedRun, "allocate", return_value=run), \
                patch.object(checks.baselines, "prepare", return_value=seal), \
                patch.object(checks.baselines, "verify_prepared_baselines",
                             side_effect=checks.evidence.ConformanceError("InputChanged")), \
                patch.object(checks, "snapshot") as snapshot, patch.object(checks, "build") as build:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.execute(ROOT, self.directory / "run")
        snapshot.assert_not_called()
        build.assert_not_called()
        self.assertEqual(run.state, "Retained")
        self.assertTrue(seal.exists())

    def test_snapshot_preserves_solution_ancestry_but_rejects_symlinks(self):
        repository = self.directory / "repository"
        repository.mkdir()
        (repository / "Hoard.slnx").write_text("<Solution/>")
        (repository / "file.cs").write_text("source")
        run = SimpleNamespace(root=self.directory / "run")
        (run.root / "stores").mkdir(parents=True)
        with patch.object(checks, "capture_control", return_value=(0, b"Hoard.slnx\0file.cs\0")):
            candidate, sources = checks.snapshot(repository, run)
        self.assertEqual((candidate / "Hoard.slnx").read_bytes(), (repository / "Hoard.slnx").read_bytes())
        self.assertEqual(sources["file.cs"], hashlib.sha256(b"source").hexdigest())
        (repository / "linked.cs").symlink_to(repository / "file.cs")
        second = SimpleNamespace(root=self.directory / "second")
        (second.root / "stores").mkdir(parents=True)
        with patch.object(checks, "capture_control", return_value=(0, b"Hoard.slnx\0linked.cs\0")):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "OwnershipInvalid"):
                checks.snapshot(repository, second)

    def test_package_lock_replay_changes_only_three_local_archive_hashes(self):
        feed = self.directory / "feed"
        feed.mkdir()
        dependencies = {"xunit": {"resolved": "2.9.3", "contentHash": "unchanged"}}
        for name in ("Hoard.Abstractions", "Hoard.Testing.Conformance", "Hoard.Conformance.TestLogger"):
            dependencies[name] = {"resolved": "0.1.0", "contentHash": "old", "dependencies": {"xunit": "2.9.3"}}
            (feed / f"{name}.0.1.0.nupkg").write_bytes(name.encode())
        original = {"version": 2, "dependencies": {"net10.0": dependencies}}
        lock = self.directory / "packages.lock.json"
        lock.write_text(json.dumps(original))
        checks.replay_lock(lock, feed)
        replayed = json.loads(lock.read_bytes())
        for name, dependency in replayed["dependencies"]["net10.0"].items():
            if name.startswith("Hoard."):
                self.assertNotEqual(dependency["contentHash"], "old")
                dependency["contentHash"] = "old"
        self.assertEqual(replayed, original)
        (feed / "Hoard.Conformance.TestLogger.0.1.0.nupkg").unlink()
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
            checks.replay_lock(lock, feed)

    def test_attempt_uses_exact_identities_disabled_console_and_ingestion(self):
        (self.directory / "proofs").mkdir()
        (self.directory / "stores").mkdir()
        owner = self.directory / "runtime-owner.json"
        owner.write_bytes(b"owner")
        candidate = self.directory / "stores/candidate"
        scenario = checks.SCENARIOS[1]
        identities = scenario[1]
        assembly_path = f"stores/candidate/{checks.LOGGER}/Smoke/bin/Release/net10.0/Smoke.dll"
        inputs = {"runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                  "runtimeAssemblies": {assembly_path: "a" * 64},
                  "packages": [{"packageId": "Hoard.Conformance.TestLogger", "sha256": "b" * 64}]}
        result = SimpleNamespace(exit_code=0, events=(
            {"event": "control", "code": "None", "value": 2},))
        received = {}

        def command(args, **kwargs):
            self.assertEqual(kwargs["kind"], "tests")
            self.assertLessEqual(kwargs["timeout"], 600)
            self.assertEqual(args[-1], "--TestCaseFilter:FullyQualifiedName=" +
                             checks.SMOKE + "Parameter")
            settings = ET.parse(args[-2].removeprefix("--Settings:")).getroot()
            self.assertEqual(Path(args[-2].removeprefix("--Settings:")).parent, self.directory / "stores")
            loggers = settings.findall("./LoggerRunSettings/Loggers/Logger")
            self.assertEqual([(item.attrib["friendlyName"], item.attrib["enabled"]) for item in loggers],
                             [("console", "False"), ("HoardSafe", "True")])
            attempt_id = settings.findtext(".//AttemptId")
            output = self.directory / ("runtime-" + attempt_id)
            output.mkdir()
            (output / "completion.json").write_bytes(b"{}")
            (output / "witnesses.jsonl").write_bytes(b"actual-lines\n")
            for number in range(2):
                (output / f"proof-{number}.json").write_bytes(b'{"failureKind":"None"}')
            return result

        def ingest(**kwargs):
            received.update(kwargs)
            return {"diagnosticCode": "None", "witnesses": tuple(
                {"testIdentity": identity, "status": "Passed"} for identity in identities)}

        run = SimpleNamespace(root=self.directory, command=command)
        with patch.object(checks.evidence, "ingest_runtime_attempt", side_effect=ingest):
            observation = checks.test_attempt(run, inputs, candidate, scenario)
        self.assertEqual(observation["tests"], 2)
        self.assertEqual(received["expected_tests"],
                         {identity: ("none", "none") for identity in identities})
        self.assertEqual(received["witnesses_data"], b"actual-lines\n")
        self.assertLessEqual(received["started_ms"], received["ended_ms"])
        self.assertEqual(received["manifest_sha256"], hashlib.sha256(received["manifest_data"]).hexdigest())
        manifest = json.loads(received["manifest_data"])
        self.assertEqual(manifest["packages"][0]["id"], "Hoard.Conformance.TestLogger")
        self.assertEqual(manifest["assemblies"][0]["path"], assembly_path)

    def test_environment_forwards_only_allowlisted_actual_runner_image(self):
        (self.directory / "proofs").mkdir()
        observed = []

        def command(args, **kwargs):
            observed.append(kwargs)
            (self.directory / "proofs/environment.json").write_text("{}")
            return SimpleNamespace(exit_code=0, events=())

        run = SimpleNamespace(root=self.directory, command=command)
        for image_os, image_version, expected in (
            ("ubuntu24", "20261020.57.1", "ubuntu24.20261020.57.1"),
            ("", "", "none"),
            ("ubuntu24", "private-canary-image", "none"),
            ("unknown-image", "20261020.57.1", "none"),
        ):
            with self.subTest(image_os=image_os, image_version=image_version), \
                    patch.dict(checks.os.environ, {"ImageOS": image_os, "ImageVersion": image_version}):
                checks.environment(run)
                self.assertEqual(observed[-1]["env"], {"HOARD_RUNNER_IMAGE": expected})
                self.assertEqual(observed[-1]["kind"], "build")
                self.assertLessEqual(observed[-1]["timeout"], 30)

    def test_probe_observes_filesystem_and_explicit_runner_metadata(self):
        output = self.directory / "environment.json"
        calls = []

        def capture(args, **kwargs):
            calls.append((args, kwargs))
            return {
                "--version": (0, b"10.0.203\n"),
                "--list-runtimes": (0, b"Microsoft.NETCore.App 10.0.7 [/sdk/shared/Microsoft.NETCore.App]\n"),
                "-f": (0, b"ext2/ext3\n"),
            }[args[1]]

        with patch.object(checks, "native_execution_supported", return_value=True), \
                patch.object(checks, "capture_control", side_effect=capture), \
                patch.dict(checks.os.environ, {"HOARD_RUNNER_IMAGE": "ubuntu24.20261020.57.1"}):
            checks.probe(output)
        observed = json.loads(output.read_bytes())
        self.assertEqual(observed["filesystem"], "ext2-ext3")
        self.assertEqual(observed["runnerImage"], "ubuntu24.20261020.57.1")
        self.assertEqual(calls[-1][0], ["stat", "-f", "--format=%T", str(output.parent)])
        self.assertEqual(calls[-1][1], {"limit": 1024, "timeout": 5})
        self.assertNotIn(str(self.directory), json.dumps(checks.CONFIGURATION_POLICY))

    def test_negative_observations_require_matching_exit_event_inventory_and_failure_kind(self):
        scenario = checks.SCENARIOS[2]
        _, identities, code, status, exit_code, kind = scenario
        result = SimpleNamespace(exit_code=exit_code, events=(
            {"event": "control", "code": code, "value": 1},))
        ingested = {"diagnosticCode": code, "witnesses": (
            {"testIdentity": identities[0], "status": status},)}
        proofs = {"proof.json": b'{"failureKind":"Assertion"}'}
        checks.validate_observation(ingested, result, identities, code, status, exit_code, proofs, kind)
        mutations = (
            ({"diagnosticCode": "UnknownDiagnostic", "witnesses": ingested["witnesses"]}, result, proofs),
            ({"diagnosticCode": code, "witnesses": ()}, result, proofs),
            (ingested, SimpleNamespace(exit_code=0, events=result.events), proofs),
            (ingested, SimpleNamespace(exit_code=1, events=()), proofs),
            (ingested, result, {"proof.json": b'{"failureKind":"Unknown"}'}),
        )
        for changed, command_result, proof_data in mutations:
            with self.subTest(changed=changed, result=command_result):
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "EvidenceIncomplete"):
                    checks.validate_observation(changed, command_result, identities, code, status,
                                                exit_code, proof_data, kind)

    def test_safe_reads_reject_oversized_and_linked_diagnostics(self):
        path = self.directory / "proof.json"
        path.write_bytes(b"12345")
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "OutputLimitExceeded"):
            checks.read_bounded(path, 4)
        linked = self.directory / "linked.json"
        linked.symlink_to(path)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "OwnershipInvalid"):
            checks.read_bounded(linked, 100)


if __name__ == "__main__":
    unittest.main()
