import contextlib
import base64
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

ENVIRONMENT = {
    "os": "linux", "osVersion": "test", "architecture": "x86_64",
    "sdk": "10.0.203", "runtime": "10.0.7", "nativeSqlite": "not-used",
    "filesystem": "ext4", "runnerImage": "none", "freeBytes": 100,
    "pragmas": {"journalMode": "none", "synchronous": 0, "foreignKeys": 0, "busyTimeout": 0},
}


class SdkDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / ".foundation" / ("sdk-diagnostic-test-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True, mode=0o700)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_artifact_wrapper_scope_preserves_frozen_publication_parameters_and_actual_assembly(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_publication_scenarios", None)),
                        "Artifact publication needs exact source-owned wrapper transport.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"]
                    if name.startswith("Hoard.Artifacts.Tests.ArtifactPublicationTests.")}
        expected.update(
            'Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests.'
            'Shared_duplicate_assertion_rejects_substituted_source_and_accepts_original_store'
            f'(provider: "{provider}")' for provider in ("local", "object"))
        scenario, = checks.original_artifact_publication_scenarios()
        self.assertEqual(set(scenario[1]), expected)
        self.assertEqual(len(scenario[1]), 14)
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            launch.assert_called_once()
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertFalse(launch.call_args.kwargs)
            manifest = launch.call_args.args[2]
            self.assertEqual(manifest["purpose"], "discovery")
            self.assertEqual({item["testIdentity"] for item in manifest["expected"]}, expected)
            self.assertEqual({item["caseId"] for item in manifest["expected"]}, {scenario[0]})

    def test_artifact_wrapper_scope_cannot_drop_parameters_or_borrow_other_methods(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_publication_scenarios", None)),
                        "Artifact wrapper dispatch must reject shortened frozen scopes.")
        scenario, = checks.original_artifact_publication_scenarios()
        for changed in (
                (scenario[0], scenario[1][:-1], *scenario[2:]),
                ("original-artifact-provider-selected", *scenario[1:]),
                (scenario[0], (*scenario[1][:-1], "Hoard.Artifacts.Tests.Provider.Check"), *scenario[2:])):
            with self.subTest(scope=changed[0]), patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, self.directory, changed)
                launch.assert_not_called()

    def test_artifact_read_delete_scope_preserves_six_frozen_read_and_fencing_parameters(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_read_delete_scenarios", None)),
                        "Protected read and deletion wrappers need exact shared-consumer transport.")
        methods = {
            "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
            "Destination_failure_and_second_copy_never_return_verified_completion_or_dispose_borrowed_streams",
            "Hoard.Artifacts.Tests.ArtifactDeletionTests."
            "Exact_delete_receipts_and_recreation_never_remove_the_new_incarnation",
            "Hoard.Artifacts.Tests.ArtifactDeletionTests."
            "A_held_reader_finishes_before_exclusive_deletion_and_later_opens_cannot_enter",
        }
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(")[0] in methods}
        scenario, = checks.original_artifact_read_delete_scenarios()
        self.assertEqual(set(scenario[1]), expected)
        self.assertEqual(len(scenario[1]), 6)
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
        for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                        ("original-artifact-read-delete-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_original_wrapper_scopes_use_every_frozen_parameter_and_the_original_assembly(self):
        self.assertTrue(callable(getattr(checks, "original_metadata_scenarios", None)),
                        "Original wrappers need source-owned exact discovery scopes.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        scenarios = checks.original_metadata_scenarios()
        self.assertEqual(len(scenarios), 2)
        for scenario, provider in zip(scenarios, ("memory", "sqlite"), strict=True):
            expected = {name for entry in frozen["entries"]
                        if entry["profileId"] == "metadata" and entry["bindingId"] == provider
                        for name in entry["runtimeTests"] if name.startswith("Hoard.Metadata.Tests.")}
            self.assertEqual(set(scenario[1]), expected)
            self.assertEqual(len(scenario[1]), len(expected))
            candidate = self.directory / "candidate"
            assembly = candidate / checks.METADATA_TESTS / checks.METADATA_TEST_OUTPUT / (
                "Release/net10.0/Hoard.Metadata.Tests.dll")
            inputs = {
                "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                "runtimeAssemblies": {
                    assembly.relative_to(self.directory).as_posix(): "a" * 64,
                    (assembly.parent / "runtimes/linux-x64/native/libe_sqlite3.so"
                     ).relative_to(self.directory).as_posix(): "c" * 64},
                "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
                "environment": {**ENVIRONMENT, "nativeSqlite": "3.50.4", "pragmas": {
                    "journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0}},
            }
            with self.subTest(provider=provider), patch.object(
                    checks, "runtime_command", side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
                launch.assert_called_once()
                self.assertEqual(launch.call_args.args[1], assembly)
                self.assertEqual(launch.call_args.kwargs["metadata_provider"], provider)
                manifest = launch.call_args.args[2]
                self.assertEqual(manifest["purpose"], "discovery")
                self.assertEqual({item["testIdentity"] for item in manifest["expected"]}, expected)

    def test_shortened_or_renamed_original_wrapper_scope_never_launches(self):
        self.assertTrue(callable(getattr(checks, "original_metadata_scenarios", None)),
                        "Original wrapper dispatch must reject shortened frozen scopes.")
        scenario = checks.original_metadata_scenarios()[0]
        for changed in (
                (scenario[0], scenario[1][:-1], *scenario[2:]),
                ("original-metadata-provider-selected", *scenario[1:]),
                (scenario[0], (*scenario[1][:-1], "Hoard.Metadata.Tests.Provider.Check"), *scenario[2:])):
            with self.subTest(scope=changed[0]), patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, self.directory, changed)
                launch.assert_not_called()

    def test_original_wrapper_logger_and_shared_runtime_must_match_the_actual_archives(self):
        logger = "Hoard.Conformance.TestLogger"
        variants = (
            (checks.METADATA_TESTS, checks.METADATA_TEST_OUTPUT, checks.METADATA_PACKAGES,
             checks.metadata_wrapper_runtime),
            (checks.ARTIFACT_TESTS, checks.ARTIFACT_TEST_OUTPUT, checks.ARTIFACT_PACKAGES,
             checks.artifact_wrapper_runtime),
        )
        for project, folder, packages, admit in variants:
            for mutation in (None, *packages, logger):
                candidate = self.directory / (Path(project).name + "-" + str(mutation))
                output = candidate / project / folder / "Release/net10.0"
                output.mkdir(parents=True)
                source = candidate / checks.LOGGER / f"bin/Release/net10.0/{logger}.dll"
                source.parent.mkdir(parents=True)
                source.write_bytes(b"logger" if mutation != logger else b"replaced")
                for package in packages:
                    (output / f"{package}.dll").write_bytes(
                        b"shared" if mutation != package else b"replaced")

                def identity(feed, package, version):
                    digest = hashlib.sha256(b"logger" if package == logger else b"shared").hexdigest()
                    return {"runtimeAssemblies": {f"lib/net10.0/{package}.dll": digest}}

                with self.subTest(project=project, mutation=mutation), patch.object(
                        checks.evidence, "package_identity", side_effect=identity) as observed:
                    if mutation is None:
                        admit(candidate, self.directory)
                        self.assertEqual((output / f"{logger}.dll").read_bytes(), b"logger")
                        self.assertEqual({call.args[1] for call in observed.call_args_list},
                                         {*packages, logger})
                    else:
                        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                            admit(candidate, self.directory)

    def test_original_provider_selection_is_closed_and_reaches_the_actual_test_host_settings(self):
        (self.directory / "stores").mkdir()
        (self.directory / "runtime-owner.json").write_bytes(b"{}")
        received = []

        def command(args, **kwargs):
            received.append(args)
            return SimpleNamespace(exit_code=0, events=())

        run = SimpleNamespace(root=self.directory, command=command)
        assembly = self.directory / "Hoard.Metadata.Tests.dll"
        for provider in ("memory", "sqlite"):
            manifest = {
                "attemptId": str(uuid.uuid4()), "purpose": "discovery",
                "expected": [{"testIdentity": "Hoard.Metadata.Tests.Original.Check",
                              "fullyQualifiedName": "Hoard.Metadata.Tests.Original.Check"}],
            }
            checks.runtime_command(run, assembly, manifest, metadata_provider=provider)
            settings_path = Path(next(arg.removeprefix("--Settings:") for arg in received[-1]
                                      if arg.startswith("--Settings:")))
            settings = ET.fromstring(settings_path.read_bytes())
            self.assertEqual(settings.findtext("./RunConfiguration/EnvironmentVariables/HOARD_METADATA_PROVIDER"),
                             provider)
            self.assertEqual(settings.find("./LoggerRunSettings/Loggers/Logger[@friendlyName='console']")
                             .get("enabled"), "False")
            self.assertIn("--ListTests", received[-1])
        for provider, target in (("provider-selected", assembly), ("sqlite", self.directory / "Foreign.dll")):
            with self.subTest(provider=provider, target=target.name):
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.runtime_command(run, target, manifest, metadata_provider=provider)
        self.assertEqual(len(received), 2)

    def test_each_diagnostic_discovers_its_actual_selected_assembly_before_execution(self):
        candidate = self.directory / "candidate"
        for scenario in checks.SCENARIOS:
            name, identities = scenario[:2]
            source = not all(identity.startswith(checks.SMOKE) for identity in identities)
            folder = checks.TESTS if source else checks.LOGGER + "/Smoke"
            output = (checks.PACKAGE_TEST_OUTPUT
                      if all(identity.startswith((checks.PACKAGE_TEST_PREFIX, *checks.BINDING_TEST_PREFIXES))
                             for identity in identities) else "bin")
            assembly = candidate / folder / output / "Release/net10.0" / (
                "Hoard.Conformance.Tests.dll" if source else "Smoke.dll")
            package = "Hoard.Testing.Conformance" if source or name == "origin-output" else "Hoard.Conformance.TestLogger"
            inputs = {
                "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
                "packages": [{"packageId": package, "sha256": "b" * 64}],
                "environment": {**ENVIRONMENT, "nativeSqlite": "3.50.4", "pragmas": {
                    "journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0}},
            }
            inputs["runtimeAssemblies"][(assembly.parent / "runtimes/linux-x64/native/libe_sqlite3.so"
                                         ).relative_to(self.directory).as_posix()] = "c" * 64
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
                           (checks.SCENARIOS[0][1][0], checks.SMOKE + "Assertion"),
                           (checks.SCENARIOS[0][1][0],
                            "Hoard.Conformance.Tests.MemoryMechanismTests.Mixed")):
            scenario = ("unrecognized", identities, "None", "Passed", 0, "None")
            with self.subTest(identities=identities), patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, self.directory, scenario)
                launch.assert_not_called()

    def test_sqlite_diagnostics_require_actual_environment_and_fingerprinted_native_runtime(self):
        candidate = self.directory / "candidate"
        assembly = candidate / checks.TESTS / checks.PACKAGE_TEST_OUTPUT / "Release/net10.0/Hoard.Conformance.Tests.dll"
        native_path = (assembly.parent / "runtimes/linux-x64/native/libe_sqlite3.so").relative_to(self.directory).as_posix()
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64, native_path: "c" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
            "environment": {**ENVIRONMENT, "nativeSqlite": "3.50.4", "pragmas": {
                "journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0}},
        }
        identity = "Hoard.Fixtures.Conformance.Consumer.SqliteBindingTests.Reopen_transfers_one_directory_without_settling_it_under_an_old_worker"
        scenario = ("sqlite-ownership", (identity,), "None", "Passed", 0, "None")
        for mutation in ("missing-environment", "not-used", "wrong-pragmas", "missing-native"):
            changed = json.loads(json.dumps(inputs))
            if mutation == "missing-environment":
                changed.pop("environment")
            elif mutation == "not-used":
                changed["environment"]["nativeSqlite"] = "not-used"
            elif mutation == "wrong-pragmas":
                changed["environment"]["pragmas"]["synchronous"] = 1
            else:
                changed["runtimeAssemblies"].pop(native_path)
            with self.subTest(mutation=mutation), patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "EvidenceIncomplete"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), changed, candidate, scenario)
                launch.assert_not_called()
        with patch.object(checks, "runtime_command", side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual(launch.call_args.args[2]["purpose"], "discovery")

    def test_package_consumer_lock_preparation_is_exact_and_preserves_source_graph(self):
        candidate = self.directory / "candidate"
        original = candidate / checks.TESTS / "PackageAcceptance/packages.lock.json"
        original.parent.mkdir(parents=True)
        feed = self.directory / "feed"
        feed.mkdir()
        local = ("Hoard.Abstractions", "Hoard.Testing.Conformance",
                 "Hoard.Conformance.TestLogger", "Hoard.Fixtures.Metadata.Memory",
                 "Hoard.Fixtures.Conformance.Bindings.Memory", "Hoard.Fixtures.Metadata.Sqlite",
                 "Hoard.Fixtures.Conformance.Bindings.Sqlite")
        dependencies = {"xunit": {"resolved": "2.9.3", "contentHash": "unchanged"}}
        for package in local:
            (feed / (package + ".0.1.0.nupkg")).write_bytes(package.encode())
            dependencies[package] = {"resolved": "0.1.0", "contentHash": "old"}
        raw = json.dumps({"version": 2, "dependencies": {"net10.0": dependencies}}).encode()
        original.write_bytes(raw)
        lock, receipt = checks.prepare_package_consumer_lock(candidate, feed)
        self.assertEqual(original.read_bytes(), raw)
        self.assertEqual(json.loads(lock.read_bytes())["dependencies"]["net10.0"]["xunit"],
                         dependencies["xunit"])
        self.assertEqual(set(receipt["packages"]), {name + ".0.1.0.nupkg" for name in local})
        checks.verify_package_consumer_lock(candidate, feed, lock, receipt)
        (feed / "Hoard.Testing.Conformance.0.1.0.nupkg").write_bytes(b"changed")
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            checks.verify_package_consumer_lock(candidate, feed, lock, receipt)

    def test_package_consumer_lock_rejects_foreign_inventory_without_publishing(self):
        candidate = self.directory / "candidate"
        original = candidate / checks.TESTS / "PackageAcceptance/packages.lock.json"
        original.parent.mkdir(parents=True)
        raw = b'{"version":2,"dependencies":{"net10.0":{"xunit":{"resolved":"2.9.3"}}}}'
        original.write_bytes(raw)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            checks.prepare_package_consumer_lock(candidate, self.directory)
        self.assertEqual(original.read_bytes(), raw)
        self.assertFalse((original.parents[1] / "obj/F07.consumer.packages.lock.json").exists())

    def test_original_wrapper_preparation_preserves_each_existing_package_graph(self):
        feed = self.directory / "feed"
        feed.mkdir()
        for package in checks.INPUT_PACKAGES:
            (feed / f"{package}.0.1.0.nupkg").write_bytes(package.encode())
        for project, packages in (
                (checks.METADATA_TESTS, checks.METADATA_PACKAGES),
                (checks.ARTIFACT_TESTS, checks.ARTIFACT_PACKAGES)):
            with self.subTest(project=project):
                candidate = self.directory / Path(project).name
                original = candidate / project / "PackageAcceptance/packages.lock.json"
                original.parent.mkdir(parents=True)
                dependencies = {"xunit": {"resolved": "2.9.3", "contentHash": "unchanged"}}
                dependencies.update({package: {"resolved": "0.1.0", "contentHash": "old"} for package in packages})
                raw = json.dumps({"version": 2, "dependencies": {"net10.0": dependencies}}).encode()
                original.write_bytes(raw)
                alternate, receipt = checks.prepare_package_consumer_lock(
                    candidate, feed, project=project, local_packages=packages)
                self.assertEqual(original.read_bytes(), raw)
                self.assertEqual(alternate.parent, candidate / project / "obj")
                prepared = json.loads(alternate.read_bytes())["dependencies"]["net10.0"]
                self.assertEqual(set(prepared), set(dependencies))
                self.assertEqual(prepared["xunit"], dependencies["xunit"])
                self.assertEqual(set(receipt["packages"]), {f"{package}.0.1.0.nupkg" for package in packages})
                checks.verify_package_consumer_lock(candidate, feed, alternate, receipt, project=project)
                self.assertNotIn("Hoard.Conformance.TestLogger", prepared)

    def test_sqlite_environment_requires_actual_configuration_and_locked_native_archive_bytes(self):
        runtime = self.directory / "runtime"
        native = runtime / "runtimes/linux-x64/native/libe_sqlite3.so"
        native.parent.mkdir(parents=True)
        native.write_bytes(b"actual-native")
        package = self.directory / "sqlite.nupkg"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr(native.relative_to(runtime).as_posix(), native.read_bytes())
        locked = {"resolved": "2.1.13", "contentHash": base64.b64encode(
            hashlib.sha512(package.read_bytes()).digest()).decode()}
        metadata = package.parent / ".nupkg.metadata"
        metadata.write_text(json.dumps({"version": 2, "contentHash": locked["contentHash"],
                                       "source": "https://api.nuget.org/v3/index.json"}))
        package.with_suffix(".nupkg.sha512").write_text(locked["contentHash"])
        platform = {"architecture": "x86_64", "runtime": "10.0.7"}
        observation = {
            "schemaVersion": 1, "runtime": "10.0.7", "architecture": "X64",
            "nativeSqlite": "3.50.4", "pragmas": {
                "journalMode": "wal", "synchronous": 2, "foreignKeys": 1, "busyTimeout": 0},
            "nativeLibrary": {"path": native.relative_to(runtime).as_posix(),
                              "sha256": hashlib.sha256(native.read_bytes()).hexdigest()},
        }
        before = json.loads(json.dumps(observation))
        receipt = checks.admit_sqlite_environment(observation, platform, runtime, package, locked)
        self.assertEqual(observation, before)
        self.assertEqual(receipt["nativeSha256"], observation["nativeLibrary"]["sha256"])
        self.assertEqual(receipt["packageSha256"], hashlib.sha256(package.read_bytes()).hexdigest())
        normalized = base64.b64encode(b"n" * 64).decode()
        locked["contentHash"] = normalized
        metadata.write_text(json.dumps({"version": 2, "contentHash": normalized,
                                       "source": "https://api.nuget.org/v3/index.json"}))
        receipt = checks.admit_sqlite_environment(observation, platform, runtime, package, locked)
        self.assertEqual(receipt["nugetSha512"], (b"n" * 64).hex())
        self.assertEqual(receipt["archiveSha512"], hashlib.sha512(package.read_bytes()).hexdigest())
        restored_metadata = metadata.read_bytes()
        for field, invalid in (("contentHash", "foreign"), ("source", "https://example.invalid/v3/index.json")):
            changed = json.loads(restored_metadata)
            changed[field] = invalid
            metadata.write_text(json.dumps(changed))
            with self.subTest(cache_field=field), self.assertRaises(checks.evidence.ConformanceError):
                checks.admit_sqlite_environment(observation, platform, runtime, package, locked)
            metadata.write_bytes(restored_metadata)
        cached_hash = package.with_suffix(".nupkg.sha512")
        restored_hash = cached_hash.read_bytes()
        cached_hash.write_text(base64.b64encode(b"z" * 64).decode())
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.admit_sqlite_environment(observation, platform, runtime, package, locked)
        cached_hash.write_bytes(restored_hash)
        for mutate in (
                lambda value: value.update(nativeSqlite="not-used"),
                lambda value: value.update(runtime="10.0.8"),
                lambda value: value.update(architecture="Arm64"),
                lambda value: value["pragmas"].update(synchronous=1),
                lambda value: value["nativeLibrary"].update(path="../outside.so"),
                lambda value: value["nativeLibrary"].update(sha256="a" * 64),
                lambda value: value.update(extra=True)):
            with self.subTest(mutation=mutate):
                changed = json.loads(json.dumps(before))
                mutate(changed)
                with self.assertRaises(checks.evidence.ConformanceError):
                    checks.admit_sqlite_environment(changed, platform, runtime, package, locked)
        native.write_bytes(b"substituted-native")
        observation["nativeLibrary"]["sha256"] = hashlib.sha256(native.read_bytes()).hexdigest()
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.admit_sqlite_environment(observation, platform, runtime, package, locked)
        native.write_bytes(b"actual-native")
        locked["contentHash"] = base64.b64encode(b"x" * 64).decode()
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.admit_sqlite_environment(before, platform, runtime, package, locked)

    def test_native_noncooperation_requires_actual_retention_and_controller_confirmed_exit(self):
        observed = {
            "schemaVersion": 1, "inputsSha256": "a" * 64, "childPid": 123,
            "boundaryObservations": 1, "guards": [1, 1, 1],
            "commitCode": "Uncertain", "commitPhase": "Commit", "commitRetry": "Reconcile",
            "ticketSha256": "b" * 64, "failureTicketSha256": "b" * 64,
            "disposeCode": "CleanupIncomplete", "incompleteCleanups": 1,
            "admissionCode": "Disposed", "settlementCompleted": False, "cleanupState": "Retained",
            "resourceIds": ["resource-a"],
            "ledgerStates": ["Allocated", "Active", "Settling", "Retained"],
        }
        command = {
            "schemaVersion": 1, "sequence": 10, "childPid": 123, "childStartSha256": "c" * 64,
            "startedMs": 1000, "endedMs": 46000, "exitCode": -9,
            "diagnosticCode": "DeadlineExceeded", "groupState": "Exited", "scope": "recovery",
        }
        before = json.loads(json.dumps((observed, command)))
        checks.admit_sqlite_noncooperation(observed, command, "a" * 64)
        self.assertEqual(json.loads(json.dumps((observed, command))), before)
        for field, invalid in (
                ("schemaVersion", True), ("inputsSha256", "d" * 64), ("childPid", 124),
                ("boundaryObservations", 0), ("guards", [1, 1, 0]), ("guards", [True, 1, 1]),
                ("commitCode", "DeadlineExceeded"), ("commitPhase", "Read"), ("commitRetry", "Retry"),
                ("failureTicketSha256", "e" * 64), ("disposeCode", "None"), ("incompleteCleanups", 0),
                ("admissionCode", "Unavailable"), ("settlementCompleted", True),
                ("cleanupState", "Released"), ("resourceIds", []),
                ("resourceIds", ["../foreign"]), ("ledgerStates", ["Released"]), ("foreign", 1)):
            changed = {**observed, field: invalid}
            with self.subTest(producer=field, invalid=invalid), self.assertRaisesRegex(
                    checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_sqlite_noncooperation(changed, command, "a" * 64)
        for field, invalid in (
                ("schemaVersion", True), ("childPid", 124), ("childStartSha256", "0" * 64),
                ("sequence", 0), ("startedMs", True), ("endedMs", 999), ("exitCode", 0),
                ("diagnosticCode", "None"), ("groupState", "Retained"), ("scope", "ordinary"),
                ("foreign", 1)):
            changed = {**command, field: invalid}
            with self.subTest(controller=field), self.assertRaisesRegex(
                    checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_sqlite_noncooperation(observed, changed, "a" * 64)

    def test_native_noncooperation_cannot_turn_an_exit_setup_failure_or_live_child_into_success(self):
        for outcome, expected in (
                ("normal-exit", "EvidenceIncomplete"), ("CommandFailed", "CommandFailed"),
                ("missing-proof", "OutputLimitExceeded"), ("live-child", "CleanupIncomplete")):
            root = self.directory / outcome
            (root / "stores").mkdir(parents=True)
            command = unittest.mock.Mock(return_value=SimpleNamespace(exit_code=0))
            if outcome != "normal-exit":
                command.side_effect = checks.evidence.ConformanceError(
                    "CommandFailed" if outcome == "CommandFailed" else "DeadlineExceeded")
            run = SimpleNamespace(root=root, command_sequence=4, command=command,
                                  live_children=lambda: outcome == "live-child")
            with self.subTest(outcome=outcome), patch.object(
                    checks, "require_sqlite_environment") as admission, patch.object(
                    checks.evidence, "package_identity", return_value={"sha256": "f" * 64}):
                with self.assertRaisesRegex(checks.evidence.ConformanceError, expected):
                    checks.sqlite_noncooperation(run, {"bound": "input"}, root / "candidate")
                admission.assert_called_once()
                self.assertEqual(command.call_args.kwargs["scope"], "recovery")
                self.assertEqual(command.call_args.kwargs["timeout"], 45)
                self.assertEqual(command.call_args.args[0][-1], checks.evidence.digest({"bound": "input"}))

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

    def test_package_consumer_replay_is_locked_and_keeps_source_output_separate(self):
        received = []
        project = self.directory / "Tests.csproj"
        lock = self.directory / "obj/F07.consumer.packages.lock.json"
        with patch.object(checks.baselines, "_command",
                          side_effect=lambda run, args, **kwargs: received.append((args, kwargs))):
            checks.build(object(), project, self.directory / "NuGet.Config", "consumer-locked-replay",
                         lock=lock, properties=("-p:ConformancePackageAcceptance=true",
                                                "-p:BaseOutputPath=" + checks.PACKAGE_TEST_OUTPUT + "/"))
        self.assertEqual([args[1] for args, _ in received], ["restore", "build"])
        self.assertIn("--locked-mode", received[0][0])
        for args, kwargs in received:
            self.assertIn("-p:ConformancePackageAcceptance=true", args)
            self.assertIn("-p:BaseOutputPath=bin/package-diagnostic/", args)
            self.assertIn("-p:NuGetLockFilePath=" + str(lock), args)
            self.assertNotIn("--force-evaluate", args)
            self.assertEqual(kwargs["cache_id"], "consumer-locked-replay")

    def test_pack_uses_the_explicit_package_identity_not_the_fixture_project_filename(self):
        feed = self.directory / "feed"
        with patch.object(checks.baselines, "_command"), \
                patch.object(checks, "canonicalize_acceptance_archive") as canonicalize:
            checks.build(object(), self.directory / "Memory.csproj", self.directory / "NuGet.Config",
                         "memory-package", feed=feed, package_id="Hoard.Fixtures.Metadata.Memory")
        canonicalize.assert_called_once_with(feed / "Hoard.Fixtures.Metadata.Memory.0.1.0.nupkg")

    def test_capture_recomputes_added_runtime_and_locks_and_rejects_remapped_sources(self):
        (self.directory / "stores").mkdir()
        (self.directory / "feed").mkdir()
        run = SimpleNamespace(root=self.directory, run_id=str(uuid.uuid4()), _check_ledger=lambda: None)
        config, feed = checks.baselines._config(run, "candidate")
        for name in checks.INPUT_PACKAGES:
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
        native = candidate / checks.TESTS / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/runtimes/linux-x64/native/libe_sqlite3.so")
        native.parent.mkdir(parents=True)
        native.write_bytes(b"native")
        wrapped = candidate / checks.METADATA_TESTS / checks.METADATA_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Testing.Conformance.dll")
        wrapped.parent.mkdir(parents=True)
        wrapped.write_bytes(b"shared-sdk")
        artifact_wrapped = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Testing.Conformance.dll")
        artifact_wrapped.parent.mkdir(parents=True)
        artifact_wrapped.write_bytes(b"shared-sdk")
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
        self.assertEqual(len(before["packages"]), 13)
        self.assertNotIn(str(self.directory).encode(), checks.evidence.canonical_bytes(before))
        for path in (native, wrapped, artifact_wrapped, runtime / "Added.dll", runtime / "Tests.runtimeconfig.json",
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
            Path(args[-1]).write_text(json.dumps(ENVIRONMENT))
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
                target.write(json.dumps(ENVIRONMENT).encode())
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
