import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_sdk_checks as checks


class SdkDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / ".foundation" / ("sdk-diagnostic-test-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True, mode=0o700)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_each_diagnostic_discovers_its_actual_selected_assembly_before_execution(self):
        candidate = self.directory / "candidate"
        for scenario in checks.SCENARIOS:
            name, identities = scenario[:2]
            source = not all(identity.startswith(checks.SMOKE) for identity in identities)
            folder = checks.TESTS if source else checks.LOGGER + "/Smoke"
            assembly = candidate / folder / "bin/Release/net10.0" / (
                "Hoard.Conformance.Tests.dll" if source else "Smoke.dll")
            package = "Hoard.Testing.Conformance" if source or name == "origin-output" else "Hoard.Conformance.TestLogger"
            inputs = {
                "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
                "packages": [{"packageId": package, "sha256": "b" * 64}],
            }
            with self.subTest(scenario=name), patch.object(
                    checks, "runtime_command", side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
                launch.assert_called_once()
                self.assertEqual(launch.call_args.args[1], assembly)
                self.assertEqual(launch.call_args.args[2]["purpose"], "discovery")
                self.assertEqual(launch.call_args.args[2]["packages"][0]["id"], package)

    def test_unsupported_platform_never_allocates_or_prepares(self):
        with patch.object(checks, "native_execution_supported", return_value=False), \
                patch.object(checks.OwnedRun, "allocate") as allocate, \
                patch.object(checks.baselines, "prepare") as prepare:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
                checks.execute(ROOT, self.directory / "run")
        allocate.assert_not_called()
        prepare.assert_not_called()

    def test_unknown_mixed_or_empty_diagnostic_names_never_fall_back_to_an_assembly(self):
        for identities in ((), ("Foreign.Provider.Check",),
                           (checks.SCENARIOS[0][1][0], checks.SMOKE + "Assertion")):
            scenario = ("unrecognized", identities, "None", "Passed", 0, "None")
            with self.subTest(identities=identities), patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, self.directory, scenario)
                launch.assert_not_called()

    def test_preparation_and_seal_verification_precede_candidate_snapshot(self):
        calls = []
        seal = self.directory / "baselines.json"
        seal.write_bytes(b"sealed")
        run = SimpleNamespace(root=self.directory, deadline=float("inf"), state="Allocated",
                              live_children=lambda: False)
        run.transition = lambda state: setattr(run, "state", state)

        def prepare(*args, **kwargs):
            self.assertEqual(kwargs, {"prepare_local_archives": True})
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

        with contextlib.redirect_stdout(io.StringIO()) as output, \
                patch.object(checks, "native_execution_supported", return_value=True), \
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
        self.assertEqual(json.loads(output.getvalue()),
                         {"qualification": False, "phase": "baseline-preparation"})

    def test_invalid_baseline_seal_never_snapshots_or_compiles_candidate(self):
        seal = self.directory / "baselines.json"
        seal.write_bytes(b"sealed")
        run = SimpleNamespace(root=self.directory, deadline=float("inf"), state="Active",
                              live_children=lambda: True)
        run.transition = lambda state: setattr(run, "state", state)
        with contextlib.redirect_stdout(io.StringIO()) as output, \
                patch.object(checks, "native_execution_supported", return_value=True), \
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
        self.assertEqual(json.loads(output.getvalue()),
                         {"qualification": False, "phase": "baseline-preparation"})

    def test_snapshot_preserves_solution_ancestry_but_rejects_symlinks(self):
        with tempfile.TemporaryDirectory(prefix="hoard-sdk-snapshot-") as temporary:
            parent = Path(temporary).resolve()
            parent.chmod(0o700)
            repository = parent / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
            (repository / "Hoard.slnx").write_text("<Solution/>")
            (repository / "src").mkdir()
            (repository / "src/file.cs").write_text("source")
            contract = "specs/004-module-discovery/contracts/openapi.json"
            (repository / contract).parent.mkdir(parents=True)
            (repository / contract).write_text('{"openapi":"3.1.0"}')
            inventory = "tests/fixtures/conformance/baselines/inventory.json"
            (repository / inventory).parent.mkdir(parents=True)
            (repository / inventory).write_text('{"entries":[]}')
            run = checks.OwnedRun.allocate(parent / "run", repository, profile="harness")
            candidate, sources = checks.snapshot(repository, run)
            self.assertEqual((candidate / "Hoard.slnx").read_bytes(), (repository / "Hoard.slnx").read_bytes())
            self.assertIn(contract, sources)
            self.assertEqual((candidate / contract).read_bytes(), (repository / contract).read_bytes())
            self.assertEqual(sources[inventory], hashlib.sha256((repository / inventory).read_bytes()).hexdigest())
            self.assertEqual((candidate / inventory).read_bytes(), (repository / inventory).read_bytes())
            self.assertEqual(sources["src/file.cs"], hashlib.sha256(b"source").hexdigest())
            self.assertEqual((candidate / "src/file.cs").stat().st_mode & 0o222, 0)
            run.transition("Settling")
            run.release()
            (repository / "src/linked.cs").symlink_to(repository / "src/file.cs")
            second = checks.OwnedRun.allocate(parent / "second", repository, profile="harness")
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.snapshot(repository, second)
            second.transition("Settling")
            second.release()

    def test_package_lock_preparation_preserves_source_and_rebinds_only_three_local_archives(self):
        feed = self.directory / "feed"
        feed.mkdir()
        dependencies = {"xunit": {"resolved": "2.9.3", "contentHash": "unchanged"}}
        for name in ("Hoard.Abstractions", "Hoard.Testing.Conformance", "Hoard.Conformance.TestLogger"):
            dependencies[name] = {"resolved": "0.1.0", "contentHash": "old", "dependencies": {"xunit": "2.9.3"}}
            (feed / f"{name}.0.1.0.nupkg").write_bytes(name.encode())
        original = {"version": 2, "dependencies": {"net10.0": dependencies}}
        lock = self.directory / "packages.lock.json"
        lock.write_text(json.dumps(original))
        project = self.directory / "Smoke.csproj"
        project.write_text("<Project/>")
        alternate, record = checks.prepare_smoke_lock(project, self.directory, feed)
        self.assertEqual(json.loads(lock.read_bytes()), original)
        self.assertFalse(record["qualification"])
        checks.verify_project_lock(record, self.directory, feed)
        replayed = json.loads(alternate.read_bytes())
        for name, dependency in replayed["dependencies"]["net10.0"].items():
            if name.startswith("Hoard."):
                self.assertNotEqual(dependency["contentHash"], "old")
                dependency["contentHash"] = "old"
        self.assertEqual(replayed, original)
        (feed / "Hoard.Conformance.TestLogger.0.1.0.nupkg").unlink()
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
            checks.prepare_smoke_lock(project, self.directory, feed)

    def test_smoke_locked_replay_uses_the_explicit_prepared_lock_for_restore_and_build(self):
        received = []
        project = self.directory / "Smoke.csproj"
        lock = self.directory / "obj/F07.preparation.packages.lock.json"
        with patch.object(checks.baselines, "_command", side_effect=lambda run, args, **kwargs: received.append(args)):
            checks.build(object(), project, self.directory / "NuGet.Config", "locked-replay", lock=lock)
        self.assertEqual([args[1] for args in received], ["restore", "build"])
        self.assertTrue(all("-p:NuGetLockFilePath=" + str(lock) in args for args in received))
        self.assertIn("--locked-mode", received[0])
        self.assertIn("--no-restore", received[1])

    def test_capture_recomputes_added_runtime_and_locks_and_rejects_remapped_sources(self):
        (self.directory / "stores").mkdir()
        (self.directory / "feed").mkdir()
        run = SimpleNamespace(root=self.directory, run_id=str(uuid.uuid4()), _check_ledger=lambda: None)
        config, feed = checks.baselines._config(run, "candidate")
        for name in ("Hoard.Abstractions", "Hoard.Testing.Conformance", "Hoard.Conformance.TestLogger"):
            with zipfile.ZipFile(feed / f"{name}.0.1.0.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                archive.writestr(f"lib/net10.0/{name}.dll", b"fixture")
        repository = self.directory / "repository"
        (repository / checks.SDK / "Catalog").mkdir(parents=True)
        (repository / checks.SDK / "Catalog/catalog.json").write_bytes(b"{}")
        (repository / checks.SDK / "packages.lock.json").write_bytes(b"lock")
        subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
        subprocess.run(["git", "add", "."], cwd=repository, check=True)
        subprocess.run([
            "git", "-c", "user.name=Conformance fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
            "commit", "--quiet", "-m", "Create synthetic SDK inputs",
        ], cwd=repository, check=True)
        candidate = self.directory / "snapshot"
        shutil.copytree(repository / "tests", candidate / "tests")
        runtime = candidate / checks.TESTS / "bin/Release/net10.0"
        runtime.mkdir(parents=True)
        (runtime / "Tests.dll").write_bytes(b"runtime")
        (runtime / "Tests.runtimeconfig.json").write_bytes(b'{"runtimeOptions":{}}')
        sources = checks.evidence.source_manifest(repository)
        environment = {
            "os": "linux", "osVersion": "test", "architecture": "x86_64",
            "sdk": "10.0.203", "runtime": "10.0.7", "nativeSqlite": "not-used",
            "filesystem": "ext4", "runnerImage": "none", "freeBytes": 100,
            "pragmas": {"journalMode": "none", "synchronous": 0, "foreignKeys": 0, "busyTimeout": 0},
        }
        identity = checks.evidence.source_identity(repository)
        def capture(group_id=None):
            return checks.make_inputs(run, repository, candidate, sources,
                                      environment, identity, None, group_id=group_id)
        before = capture()
        self.assertNotIn(str(self.directory).encode(), checks.evidence.canonical_bytes(before))
        for path in (runtime / "Added.dll", runtime / "Tests.runtimeconfig.json",
                     candidate / "added.packages.lock.json"):
            with self.subTest(path=path.name):
                original = path.read_bytes() if path.exists() else None
                path.write_bytes(b"added after admission")
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                    checks.evidence.verify_input_recomputation(
                        before, capture(before["invocationGroupId"]))
                if original is None:
                    path.unlink()
                else:
                    path.write_bytes(original)
        config.write_text(config.read_text().replace("Hoard.*", "*"))
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            capture(before["invocationGroupId"])

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
        discoveries = {}

        def command(args, **kwargs):
            self.assertLessEqual(kwargs["timeout"], 600)
            self.assertEqual(args[-1], "--TestCaseFilter:FullyQualifiedName=" +
                             checks.SMOKE + "Parameter")
            settings = ET.parse(args[-2].removeprefix("--Settings:")).getroot()
            self.assertEqual(Path(args[-2].removeprefix("--Settings:")).parent, self.directory / "stores")
            loggers = settings.findall("./LoggerRunSettings/Loggers/Logger")
            self.assertEqual([(item.attrib["friendlyName"], item.attrib["enabled"]) for item in loggers],
                             [("console", "False"), ("HoardSafe", "True")])
            attempt_id = settings.findtext(".//AttemptId")
            manifest = json.loads((self.directory / f"runtime-input-{attempt_id}.json").read_bytes())
            discovery = manifest["purpose"] == "discovery"
            self.assertEqual(kwargs["kind"], "discovery" if discovery else "tests")
            self.assertEqual("--ListTests" in args, discovery)
            if discovery:
                self.assertEqual(kwargs["discovery_tests"], frozenset(identities))
            output = self.directory / (("discovery-" if discovery else "runtime-") + attempt_id)
            output.mkdir()
            (output / "completion.json").write_bytes(b"{}")
            if discovery:
                (output / "discovered.jsonl").write_bytes(b"actual-discovery\n")
            else:
                (output / "witnesses.jsonl").write_bytes(b"actual-lines\n")
                for number in range(2):
                    (output / f"proof-{number}.json").write_bytes(b'{"failureKind":"None"}')
            return result

        def ingest(**kwargs):
            received.update(kwargs)
            return {"diagnosticCode": "None", "witnesses": tuple(
                {"testIdentity": identity, "status": "Passed"} for identity in identities)}

        def discover(**kwargs):
            discoveries.update(kwargs)
            return {"diagnosticCode": "None", "discoveries": tuple(
                {"testIdentity": identity} for identity in identities)}

        run = SimpleNamespace(root=self.directory, command=command)
        with patch.object(checks.evidence, "ingest_runtime_attempt", side_effect=ingest), \
                patch.object(checks.evidence, "ingest_runtime_discovery", side_effect=discover):
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
        self.assertEqual(manifest["purpose"], "execution")
        discovery_manifest = json.loads(discoveries["manifest_data"])
        self.assertEqual(discovery_manifest["purpose"], "discovery")
        self.assertNotEqual(discovery_manifest["attemptId"], manifest["attemptId"])
        self.assertEqual(discoveries["discoveries_data"], b"actual-discovery\n")
        self.assertLessEqual(discoveries["ended_ms"], received["started_ms"])
        with patch.object(checks.evidence, "ingest_runtime_attempt") as execution, \
                patch.object(checks.evidence, "ingest_runtime_discovery", return_value={
                    "diagnosticCode": "None", "discoveries": [{"testIdentity": identities[0]}]}):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "EvidenceIncomplete"):
                checks.test_attempt(run, inputs, candidate, scenario)
            execution.assert_not_called()

    def test_environment_forwards_only_allowlisted_actual_runner_image(self):
        (self.directory / "proofs").mkdir()
        observed = []

        def command(args, **kwargs):
            observed.append(kwargs)
            Path(args[-1]).write_text("{}")
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

    def test_admission_and_completion_capture_distinct_environment_observations(self):
        (self.directory / "proofs").mkdir()
        observed = []
        def command(args, **kwargs):
            with Path(args[-1]).open("xb") as target:
                target.write(b"{}")
            observed.append((Path(args[-1]).name, kwargs["cache_id"]))
            return SimpleNamespace(exit_code=0, events=())
        run = SimpleNamespace(root=self.directory, command=command)
        checks.environment(run)
        checks.environment(run, phase="completion")
        self.assertEqual(observed, [
            ("environment-admission.json", "environment-admission"),
            ("environment-completion.json", "environment-completion"),
        ])

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

    def test_insufficient_scratch_is_reported_as_incomplete_before_any_workspace_is_created(self):
        parent = Path(tempfile.mkdtemp(prefix="hoard-preflight-test-")).resolve()
        self.addCleanup(shutil.rmtree, parent)
        destination = parent / "unallocated"
        sentinel = parent / "outside"
        sentinel.write_bytes(b"preserve")
        output = io.StringIO()
        with patch.object(sys, "argv", ["conformance_sdk_checks.py", "--evidence", str(destination)]), \
                patch.object(checks, "native_execution_supported", return_value=True), \
                patch("conformance_execution.shutil.disk_usage",
                      return_value=SimpleNamespace(free=24 * 1024**3 - 1)), \
                contextlib.redirect_stdout(output):
            code = checks.main()
        observed = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(observed["code"], "InsufficientCapacity")
        self.assertEqual(observed["status"], "Incomplete")
        self.assertFalse(observed["qualification"])
        self.assertFalse(destination.exists())
        self.assertEqual(sentinel.read_bytes(), b"preserve")

    def test_evidence_failure_is_not_relabelled_as_a_prerequisite_problem(self):
        output = io.StringIO()
        with patch.object(sys, "argv", ["conformance_sdk_checks.py", "--evidence", "unused"]), \
                patch.object(checks, "execute", side_effect=checks.evidence.ConformanceError("ProofMismatch")), \
                contextlib.redirect_stdout(output):
            code = checks.main()
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue()), {
            "qualification": False, "status": "Failed", "code": "ProofMismatch",
        })

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

    def test_lock_entry_rejects_unknown_arguments_without_echoing_private_input(self):
        import conformance_prepare as preparation
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(preparation.OwnedRun, "allocate") as allocate:
            code = preparation.main(["--private-canary-value"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue()), {
            "mode": "preparation", "qualification": False, "status": "Incomplete",
            "code": "EvidenceSchemaInvalid",
        })
        allocate.assert_not_called()

    def test_failed_locked_restore_never_switches_to_dependency_resolution_or_build(self):
        import conformance_prepare as preparation
        project = preparation.Project("tests/fixtures/conformance/Consumer/Consumer.csproj")
        calls = []
        def fail(run, args, **kwargs):
            calls.append(args)
            raise checks.evidence.ConformanceError("CommandFailed")
        with patch.object(preparation.baselines, "_command", side_effect=fail):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "CommandFailed"):
                preparation.build_project(
                    object(), self.directory, project, self.directory / "NuGet.Config",
                    self.directory / "feed", update=False)
        self.assertEqual(len(calls), 1)
        self.assertIn("--locked-mode", calls[0])
        self.assertNotIn("--force-evaluate", calls[0])

    def test_lock_publication_rejects_concurrent_source_changes_and_foreign_paths(self):
        import conformance_prepare as preparation
        target = preparation.TARGETS[0].lock_path
        prepared = {project.lock_path: b'{"version":2,"dependencies":{}}' for project in preparation.TARGETS}
        for locks, current, code in ((prepared, {"changed.cs": "a" * 64}, "InputChanged"),
                                    ({**prepared, "outside/packages.lock.json": b"{}"}, {}, "EvidenceIncomplete")):
            with self.subTest(locks=locks), patch.object(preparation.evidence, "source_manifest", return_value=current):
                with self.assertRaisesRegex(checks.evidence.ConformanceError, code):
                    preparation.publish_locks(self.directory, {}, locks)
                self.assertFalse((self.directory / target).exists())

    def test_lock_publication_changes_only_the_explicit_reviewable_inventory(self):
        import conformance_prepare as preparation
        locks = {project.lock_path: b'{"version":2,"dependencies":{"net10.0":{}}}' for project in preparation.TARGETS}
        for relative in locks:
            (self.directory / relative).parent.mkdir(parents=True, exist_ok=True)
        existing = self.directory / preparation.TARGETS[0].lock_path
        existing.write_bytes(b"original lock")
        foreign = self.directory / "predecessor.lock"
        foreign.write_bytes(b"untouched")
        sources = {existing.relative_to(self.directory).as_posix(): checks.evidence.file_sha256(existing)}
        with patch.object(preparation.evidence, "source_manifest", return_value=sources):
            preparation.publish_locks(self.directory, sources, locks)
        self.assertEqual({path: (self.directory / path).read_bytes() for path in locks}, locks)
        self.assertEqual(foreign.read_bytes(), b"untouched")
        self.assertFalse(tuple(self.directory.rglob(".conformance-lock-*.tmp")))


if __name__ == "__main__":
    unittest.main()
