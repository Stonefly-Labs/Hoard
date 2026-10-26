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
    def test_hook_admission_scopes_select_complete_dedicated_families_and_pin_sdk(self):
        factory = getattr(checks, "hook_admission_scenarios", None)
        self.assertTrue(callable(factory), "Hook admission needs independently selectable complete method families.")
        self.assertEqual(len(factory()), 2)
        for scenario, family, providers, fixture in zip(
                factory(), ("metadata", "artifacts"), (("memory", "sqlite"), ("local", "object")),
                ("Metadata", "Artifact")):
            with self.subTest(family=family):
                method = ("Hoard.Fixtures.Conformance.Consumer." + fixture
                          + "ConformanceSessionTests.Missing_hooks_reject_before_dispatch_and_actual_binding_passes")
                identities = {method + f'(provider: "{provider}")' for provider in providers}
                self.assertEqual(scenario, ("hook-admission-" + family, tuple(sorted(identities)),
                                            "None", "Passed", 0, "None"))
                candidate = self.directory / "candidate"
                assembly = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
                    "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
                origin_inputs = (checks.metadata_origin_inputs if family == "metadata"
                                 else checks.artifact_origin_inputs)(candidate, self.directory)
                sdk_path = (assembly.parent / "Hoard.Testing.Conformance.dll").relative_to(
                    self.directory).as_posix()
                provider_packages = ("Hoard.Fixtures." + family.title() + "." + provider
                                     for provider in (("Memory", "Sqlite") if family == "metadata"
                                                      else ("Local", "ObjectSemantics")))
                inputs = {
                    "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                    "runtimeAssemblies": {
                        assembly.relative_to(self.directory).as_posix(): "a" * 64, sdk_path: "b" * 64,
                        **{path: "c" * 64 for roles in origin_inputs.values() for path, _ in roles.values()}},
                    "packages": [{"packageId": package, "sha256": "d" * 64}
                                 for package in ("Hoard.Testing.Conformance", *provider_packages)]}
                run = SimpleNamespace(root=self.directory)
                with patch.object(checks, "require_sqlite_environment") as sqlite, patch.object(
                        checks, "runtime_command",
                        side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                        checks.test_attempt(run, inputs, candidate, scenario)
                self.assertEqual(sqlite.call_count, int(family == "metadata"))
                manifest = launch.call_args.args[2]
                self.assertEqual({row["testIdentity"] for row in manifest["expected"]}, identities)
                self.assertEqual({row["caseId"] for row in manifest["expected"]}, {"QC-05"})
                self.assertEqual(len(manifest["assemblies"]), 6)
                self.assertEqual({row["path"] for row in manifest["assemblies"]}, set(inputs["runtimeAssemblies"]))
                inputs["bindings"] = [
                    {"bindingId": row["bindingId"], "descriptorSha256": hashlib.sha256(
                        row["bindingId"].encode()).hexdigest()} for row in manifest["expected"]]
                for defect in (None, "missing", "duplicate", "foreign"):
                    witnesses, origins = [], {}
                    for row, binding in zip(manifest["expected"], inputs["bindings"]):
                        execution = str(uuid.uuid4())
                        witnesses.append({
                            "testIdentity": row["testIdentity"], "bindingId": row["bindingId"],
                            "executionId": execution})
                        captured = {"descriptorSha256": binding["descriptorSha256"]}
                        origins[execution] = ([] if defect == "missing" else
                                              [captured, captured] if defect == "duplicate" else
                                              [{"descriptorSha256": "0" * 64}] if defect == "foreign" else [captured])
                    with patch.object(checks, "require_sqlite_environment"), patch.object(
                            checks, "validate_observation"), patch.object(
                            checks, "_execute_runtime_transport", return_value=(
                                SimpleNamespace(exit_code=0), {"witnesses": witnesses, "sessionOrigins": origins},
                                {"proofs": {}, "completion_data": b"{}"}, "e" * 64)) as transport:
                        if defect is None:
                            self.assertEqual(checks.test_attempt(run, inputs, candidate, scenario)["tests"], 2)
                        else:
                            with self.subTest(defect=defect), self.assertRaisesRegex(
                                    checks.evidence.ConformanceError, "WitnessMissing"):
                                checks.test_attempt(run, inputs, candidate, scenario)
                    self.assertEqual(transport.call_args.kwargs["origin_inputs"], origin_inputs)
                for changed, code in (
                        ({**inputs, "runtimeAssemblies": {
                            path: hashed for path, hashed in inputs["runtimeAssemblies"].items() if path != sdk_path}},
                         "InputChanged"),
                        ({**inputs, "packages": inputs["packages"][:1]}, "PrerequisiteMissing")):
                    with patch.object(checks, "require_sqlite_environment"), patch.object(
                            checks, "runtime_command") as launch:
                        with self.assertRaisesRegex(checks.evidence.ConformanceError, code):
                            checks.test_attempt(run, changed, candidate, scenario)
                        launch.assert_not_called()
                for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                                (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                                (scenario[0] + "-foreign", *scenario[1:])):
                    with patch.object(checks, "runtime_command") as launch:
                        with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                            checks.test_attempt(run, {}, candidate, changed)
                        launch.assert_not_called()
                scope = (family, "hook-admission")
                native = {**manifest, "attemptId": str(uuid.uuid4()), "purpose": "execution",
                          "runInputsPath": "proofs/hook-inputs.json", "inputSha256": "f" * 64,
                          "expected": [{**row, "bindingId": row["bindingId"].rsplit(".", 1)[1]}
                                       for row in manifest["expected"]]}
                self.assertEqual(checks._category_scope_tests(scope), {
                    row["testIdentity"]: (row["bindingId"], "QC-05") for row in native["expected"]})
                with self.assertRaises(checks.evidence.ConformanceError):
                    checks._category_scope_tests(("harness", "hook-admission"))
                feed = self.directory / "feed/candidate"
                feed.mkdir(parents=True, exist_ok=True)
                packages = {}
                for package in inputs["packages"][1:]:
                    name = package["packageId"]
                    archive = feed / (name + ".0.1.0.nupkg")
                    archive.write_bytes(name.encode())
                    packages[name] = checks.evidence.file_sha256(archive)
                (self.directory / "stores").mkdir(exist_ok=True)
                owner = self.directory / "runtime-owner.json"
                if not owner.exists():
                    checks.write_new(owner, b"owner")
                options = {"metadata_packages" if family == "metadata" else "artifact_packages": packages}
                with patch.object(run, "command", create=True,
                                  side_effect=checks.evidence.ConformanceError("PrerequisiteMissing")) as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
                        checks.runtime_command(run, assembly, native, category_scope=scope, **options)
                self.assertTrue(launch.call_args.kwargs["record_execution"])
                self.assertTrue(set(inputs["runtimeAssemblies"]) <=
                                set(launch.call_args.kwargs["execution_inputs"]))
                for defect in ("missing", "foreign", "context"):
                    changed = {**native, "expected": [dict(row) for row in native["expected"]]}
                    if defect == "missing":
                        changed["expected"].pop()
                    elif defect == "foreign":
                        changed["expected"][0]["testIdentity"] += ".foreign"
                    else:
                        changed["expected"][0]["caseId"] = "full-metadata-binding"
                    with self.subTest(defect=defect), self.assertRaises(checks.evidence.ConformanceError):
                        checks.runtime_command(run, assembly, changed, category_scope=scope, **options)

    def test_shared_metadata_scope_requires_complete_actual_consumer_families_and_all_images(self):
        tests = checks._category_scope_tests(("metadata", "shared-consumer"))
        self.assertEqual(set(tests), set(checks.full_metadata_binding_origin_counts()))
        self.assertEqual({binding for binding, _ in tests.values()}, {"memory", "sqlite"})
        with self.assertRaises(checks.evidence.ConformanceError):
            checks._category_scope_tests(("artifacts", "shared-consumer"))
        assembly = self.directory / "candidate" / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
        manifest = {
            "purpose": "execution", "attemptId": str(uuid.uuid4()), "runId": str(uuid.uuid4()),
            "runInputsPath": "proofs/shared-consumer-inputs.json",
            "inputSha256": "a" * 64, "expected": [{
                "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
                "bindingId": binding, "caseId": case_id, "assertionSymbol": None}
                for identity, (binding, case_id) in tests.items()],
            "assemblies": [{"path": "candidate/Consumer.dll"}, {"path": "candidate/SDK.dll"}]}
        packages = {}
        feed = self.directory / "feed/candidate"
        feed.mkdir(parents=True)
        for provider in ("Memory", "Sqlite"):
            name = "Hoard.Fixtures.Metadata." + provider
            archive = feed / (name + ".0.1.0.nupkg")
            archive.write_bytes(name.encode())
            packages[name] = checks.evidence.file_sha256(archive)
        (self.directory / "stores").mkdir()
        checks.write_new(self.directory / "runtime-owner.json", b"owner")
        run = SimpleNamespace(root=self.directory)
        with patch.object(run, "command", create=True, side_effect=checks.evidence.ConformanceError(
                "PrerequisiteMissing")) as command:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
                checks.runtime_command(run, assembly, manifest, metadata_packages=packages,
                                       category_scope=("metadata", "shared-consumer"))
        self.assertTrue(command.call_args.kwargs["record_execution"])
        self.assertTrue({"candidate/Consumer.dll", "candidate/SDK.dll"} <=
                        set(command.call_args.kwargs["execution_inputs"]))
        self.assertIn(checks.metadata_common_consumer_sdk_paths(assembly.relative_to(self.directory).as_posix())[1],
                      command.call_args.kwargs["execution_inputs"])
        for defect in ("missing", "foreign", "category"):
            changed = {**manifest, "attemptId": str(uuid.uuid4()),
                       "expected": [dict(entry) for entry in manifest["expected"]]}
            if defect == "missing":
                changed["expected"].pop()
            elif defect == "foreign":
                changed["expected"][0]["testIdentity"] += ".foreign"
            else:
                changed["expected"][0]["caseId"] = "QC-02"
            with self.subTest(defect=defect), self.assertRaises(checks.evidence.ConformanceError):
                checks.runtime_command(run, assembly, changed, metadata_packages=packages,
                                       category_scope=("metadata", "shared-consumer"))

    def test_qualified_mutation_launches_named_failure_before_unchanged_repair_and_records_all_images(self):
        for profile in ("metadata", "artifacts"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory(dir=self.directory) as temporary:
                root = Path(temporary)
                candidate = root / "snapshot"
                run = SimpleNamespace(root=root, command_sequence=7)

                class Sources:
                    def __init__(self):
                        self._run = run

                assembly = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
                    "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
                images = {assembly.relative_to(root).as_posix(): "a" * 64, **{
                    (assembly.parent / ("Image" + str(index) + ".dll")).relative_to(root).as_posix(): "b" * 64
                    for index in range(5)}}
                packages = [{"packageId": package, "version": "0.1.0",
                             "sha256": hashlib.sha256(package.encode()).hexdigest()}
                            for category, _, _, package in checks.CATEGORY_BINDING_SLOTS if category == profile]
                inputs = {
                    "profileId": profile, "mode": "qualification", "runId": str(uuid.uuid4()),
                    "invocationGroupId": str(uuid.uuid4()), "runtimeAssemblies": images, "packages": packages,
                    "bindings": [{"bindingId": binding, "category": category,
                                  "package": next(item for item in packages if item["packageId"] == package)}
                                 for category, binding, _, package in checks.CATEGORY_BINDING_SLOTS if category == profile]}
                path = f"proofs/category-{profile}-qualification-run-inputs.json"
                (root / "proofs").mkdir()
                checks.write_new(root / path, checks.evidence.canonical_bytes(inputs))
                checks.write_new(root / "runtime-owner.json", b"owner")
                (root / "stores").mkdir()
                feed = root / "feed/candidate"
                feed.mkdir(parents=True)
                for package in packages:
                    checks.write_new(feed / (package["packageId"] + ".0.1.0.nupkg"), package["packageId"].encode())
                tests = checks._category_scope_tests((profile, "mutation-repair"))
                plan = {"attemptId": str(uuid.uuid4()), "tests": tests}
                result = SimpleNamespace(exit_code=0)
                failed = SimpleNamespace(exit_code=1)
                with patch.object(checks, "NativeCategorySources", Sources), patch.object(
                        checks, "category_consumer_images", return_value=images), patch.object(
                        checks, "require_sqlite_environment") as sqlite, patch.object(
                        checks, "_execute_runtime_transport", side_effect=(
                            (failed, {}, {"proofs": {}, "completion_data": b"{}"}, "a" * 64),
                            (result, {}, {"proofs": {}, "completion_data": b"{}"}, "b" * 64))) as launch, patch.object(
                        checks, "validate_observation") as validate, patch.object(
                        checks, "category_mutation_observations", return_value=([], {})), patch.object(
                        checks, "category_source_parent", return_value="c" * 64):
                    checks.category_attempt(
                        run, inputs, candidate, "mutation-repair", plan,
                        run_inputs_path=path, native_sources=Sources())
                self.assertEqual(sqlite.call_count, int(profile == "metadata"))
                self.assertEqual(launch.call_count, 2)
                for call, corrected in zip(launch.call_args_list, (False, True)):
                    self.assertEqual(call.args[2], assembly)
                    manifest = call.args[3]
                    self.assertEqual({entry["testIdentity"] for entry in manifest["expected"]},
                                     checks.category_mutation_witnesses(profile, corrected=corrected).keys())
                    self.assertEqual({entry["assertionSymbol"] for entry in manifest["expected"]}, {
                        None if corrected else checks.CATEGORY_MUTATION_METHODS[profile][2]})
                    self.assertEqual({row["path"] for row in manifest["assemblies"]}, images.keys())
                    with patch.object(run, "command", create=True, side_effect=checks.evidence.ConformanceError(
                            "PrerequisiteMissing")) as command:
                        with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
                            checks.runtime_command(run, assembly, manifest, **call.args[5])
                    self.assertEqual(set(command.call_args.kwargs["execution_inputs"]), {
                        f'runtime-input-{manifest["attemptId"]}.json', "runtime-owner.json", path,
                        f'stores/settings-{manifest["attemptId"]}.runsettings', *images})
                    settings = ET.parse(root / f'stores/settings-{manifest["attemptId"]}.runsettings')
                    variables = settings.find(".//EnvironmentVariables")
                    expected = {
                        **{variable: package["sha256"] for package, variable in zip(
                            packages, ("HOARD_METADATA_SQLITE_PACKAGE_SHA256", "HOARD_METADATA_MEMORY_PACKAGE_SHA256")
                            if profile == "metadata" else (
                                "HOARD_ARTIFACT_LOCAL_PACKAGE_SHA256", "HOARD_ARTIFACT_OBJECT_PACKAGE_SHA256"))},
                        "HOARD_ORIGIN_RUN_ID": inputs["runId"]}
                    self.assertEqual({node.tag: node.text for node in variables}, expected)
                self.assertEqual(validate.call_args_list[0].args[3:6], ("AssertionFailed", "Failed", 1))
                self.assertEqual(validate.call_args_list[1].args[3:6], ("None", "Passed", 0))

    def test_fresh_authority_scope_uses_consumer_and_both_exact_loaded_provider_images(self):
        candidate = self.directory / "current"
        run = SimpleNamespace(root=self.directory)

        class Sources:
            def __init__(self):
                self._run = run

        originals = checks.original_observation_inputs(candidate, run.root, include_integrations=True)
        tests = checks._category_scope_tests(("artifacts", "original-integration"))
        self.assertEqual(len(tests), 32)
        packages = {(category, binding): package for category, binding, _, package in checks.CATEGORY_BINDING_SLOTS}
        assembly = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
        images = {assembly.relative_to(run.root).as_posix(): "a" * 64}
        for identity, (binding, metadata, _) in checks.AUTHORITY_INTEGRATION_ROWS.items():
            nodes = checks.evidence.original_node_assignments(identity, originals[binding][identity])
            self.assertEqual(tuple(node["contract"][1] for node in nodes),
                             (packages["metadata", metadata], packages["artifacts", binding],
                              "Hoard.Fixtures.Artifacts.HostAdapters"))
            images.update({path: hashlib.sha256(path.encode()).hexdigest() for node in nodes for path, _ in node.values()})
        inputs = {
            "profileId": "artifacts", "mode": "qualification", "runId": str(uuid.uuid4()),
            "invocationGroupId": str(uuid.uuid4()), "runtimeAssemblies": images,
            "bindings": [{"bindingId": binding, "category": category, "package": {
                "packageId": package, "version": "0.1.0", "sha256": hashlib.sha256(package.encode()).hexdigest()}}
                for category, binding, _, package in checks.CATEGORY_BINDING_SLOTS],
        }
        inputs["packages"] = [binding["package"] for binding in inputs["bindings"]]
        inputs["packages"].append({
            "packageId": "Hoard.Fixtures.Artifacts.HostAdapters", "version": "0.1.0", "sha256": "f" * 64})
        path = "proofs/authority-inputs.json"
        (run.root / "proofs").mkdir()
        (run.root / path).write_bytes(checks.evidence.canonical_bytes(inputs))
        plan = {"attemptId": str(uuid.uuid4()), "tests": tests}
        with patch.object(checks, "NativeCategorySources", Sources), patch.object(
                checks, "require_sqlite_environment") as sqlite, patch.object(
                checks, "_execute_runtime_transport", side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.category_attempt(run, inputs, candidate, "original-integration", plan,
                                        run_inputs_path=path, native_sources=Sources())
            sqlite.assert_called_once_with(inputs, assembly, run.root)
        self.assertEqual(launch.call_args.args[2], assembly)
        manifest = launch.call_args.args[3]
        self.assertEqual({row["caseId"] for row in manifest["expected"]}, {"QC-12"})
        self.assertEqual({row["path"] for row in manifest["assemblies"]}, set(images))
        self.assertTrue(launch.call_args.args[5]["original_observations"])
        self.assertEqual(launch.call_args.kwargs["original_inputs"], originals)
        checks.write_new(run.root / "runtime-owner.json", b"owner")
        (run.root / "stores").mkdir()
        with patch.object(run, "command", create=True, side_effect=checks.evidence.ConformanceError(
                "PrerequisiteMissing")) as command:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
                checks.runtime_command(run, assembly, manifest, category_scope=("artifacts", "original-integration"),
                                       original_observations=True)
        self.assertEqual(set(command.call_args.kwargs["execution_inputs"]), {
            f'runtime-input-{manifest["attemptId"]}.json', "runtime-owner.json", path,
            f'stores/settings-{manifest["attemptId"]}.runsettings', *images})
        settings = ET.parse(run.root / f'stores/settings-{manifest["attemptId"]}.runsettings')
        context = settings.findtext(".//EnvironmentVariables/HOARD_ORIGINAL_CONTEXT")
        self.assertEqual(checks.evidence.load_json(base64.b64decode(context)), {
            "schemaVersion": 1, "runId": inputs["runId"],
            "cases": {identity: {"caseId": "QC-12", "bindingId": binding}
                      for identity, (binding, _) in tests.items()}})

    def test_qualification_artifact_controller_inspects_before_independent_source_admission(self):
        discovery, execution = self.directory / "discovery", self.directory / "execution"
        for folder, records in ((discovery, "discovered.jsonl"), (execution, "witnesses.jsonl")):
            folder.mkdir()
            (folder / records).write_bytes(b"")
            (folder / "completion.json").write_bytes(b"{}")
        (execution / f"proof-{uuid.uuid4()}.json").write_bytes(b"{}")
        run = SimpleNamespace(live_children=lambda: ())
        result = SimpleNamespace(exit_code=0, events=({"event": "control", "code": "None", "value": 1},))
        transport = {
            "manifest_data": b"manifest", "owner_data": b"owner",
            "manifest_sha256": "a" * 64, "owner_sha256": "b" * 64,
            "started_ms": 1, "ended_ms": 2}
        observation = {"diagnosticCode": "None"}
        for profile, mode, scope, source in (
                ("artifacts", "qualification", "controller", True),
                ("artifacts", "qualification", "original-integration", True),
                ("metadata", "qualification", "mutation-faulty", True),
                ("metadata", "qualification", "shared-consumer", True),
                ("artifacts", "diagnostic", "controller", False),
                ("artifacts", "qualification", "original", False)):
            for path in execution.iterdir():
                path.chmod(0o600)
            with self.subTest(mode=mode, scope=scope), patch.object(checks, "runtime_command", side_effect=(
                    (result, discovery, transport), (result, execution, transport))), patch.object(
                    checks.evidence, "ingest_runtime_discovery", return_value={
                        "diagnosticCode": "None", "discoveries": ({"testIdentity": "Test.Source"},)}), patch.object(
                    checks.evidence, "ingest_runtime_attempt", return_value=observation,
                    side_effect=checks.evidence.ConformanceError("WitnessMissing") if source else None
                    ) as ordinary, patch.object(
                    checks.evidence, "inspect_runtime_attempt", return_value={"observation": observation},
                    side_effect=None if source else checks.evidence.ConformanceError("ProofMismatch")) as inspect:
                observed = checks._execute_runtime_transport(
                    run, {"mode": mode}, None, {}, {"Test.Source": ("local", "none")},
                    {"category_scope": (profile, scope)})
            self.assertIs(observed[1], observation)
            if source:
                ordinary.assert_not_called()
                inspect.assert_called_once()
                self.assertTrue(all(path.stat().st_mode & 0o777 == 0o400 for path in execution.iterdir()),
                                "Validated settled source transport must be sealed before independent re-ingestion.")
            else:
                ordinary.assert_called_once()
                inspect.assert_not_called()
        for defect in ("live-child", "changed-output"):
            for path in execution.iterdir():
                path.chmod(0o600)
            run.live_children = lambda: (123,) if defect == "live-child" else ()

            def inspect_changed(**options):
                if defect == "changed-output":
                    (execution / "witnesses.jsonl").write_bytes(b"foreign")
                return {"observation": observation}

            with self.subTest(defect=defect), patch.object(checks, "runtime_command", side_effect=(
                    (result, discovery, transport), (result, execution, transport))), patch.object(
                    checks.evidence, "ingest_runtime_discovery", return_value={
                        "diagnosticCode": "None", "discoveries": ({"testIdentity": "Test.Source"},)}), patch.object(
                    checks.evidence, "inspect_runtime_attempt", side_effect=inspect_changed):
                with self.assertRaises(checks.evidence.ConformanceError):
                    checks._execute_runtime_transport(
                        run, {"mode": "qualification"}, None, {}, {"Test.Source": ("memory", "none")},
                        {"category_scope": ("metadata", "shared-consumer")})
                self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in execution.iterdir()))

    def test_category_failure_locations_are_bounded_static_source_roles_only(self):
        trace = None
        for source, line in (
                ("conformance_sdk_checks.py", 1), ("conformance_evidence.py", 2),
                ("conformance_sources.py", 3), ("conformance_case_catalog.py", 4),
                ("conformance_sdk_checks.py", 5), ("conformance_sources.py", 6),
                ("secret/credentials.py", 7), ("conformance_evidence.py", 0),
                ("conformance_evidence.py", 2**31)):
            trace = SimpleNamespace(
                tb_frame=SimpleNamespace(f_code=SimpleNamespace(co_filename=str(ROOT / "scripts" / source))),
                tb_lineno=line, tb_next=trace)
        error = SimpleNamespace(__traceback__=trace, message="secret-value")
        self.assertEqual(checks._category_failure_locations(error), [
            {"source": "scripts/conformance_case_catalog.py", "line": 4},
            {"source": "scripts/conformance_sources.py", "line": 3},
            {"source": "scripts/conformance_evidence.py", "line": 2},
            {"source": "scripts/conformance_sdk_checks.py", "line": 1}])
        self.assertEqual(checks._category_failure_locations(SimpleNamespace(__traceback__=None)), [])

    def test_qualification_selects_independent_metadata_recovery_and_inventory_source_scopes(self):
        import conformance_case_catalog as catalog

        diagnostic = catalog.category_execution_partitions("metadata")
        qualification = catalog.category_execution_partitions("metadata", mode="qualification")
        self.assertEqual({key: value for key, value in qualification.items()
                          if key not in ("recovery-controller", "inventory-controller", "mutation-repair", "hook-admission")},
                         dict(diagnostic))
        self.assertEqual(qualification["recovery-controller"],
                         (("sqlite", catalog.METADATA_RECOVERY_SOURCE_WITNESS),))
        self.assertNotIn(catalog.METADATA_RECOVERY_SOURCE_WITNESS,
                         catalog.category_runtime_cases("metadata", "memory", mode="qualification"))
        self.assertEqual(checks._category_scope_tests(("metadata", "recovery-controller")),
                         {catalog.METADATA_RECOVERY_SOURCE_WITNESS: ("sqlite", "MP-36")})
        self.assertEqual(checks._category_scope_tests(("metadata", "inventory-controller")), {
            identity: (binding, "MP-48") for binding, identity in catalog.METADATA_INVENTORY_SOURCE_WITNESSES.items()})
        self.assertEqual(2, len(qualification["inventory-controller"]))

    def setUp(self):
        self.directory = ROOT / ".foundation" / ("sdk-diagnostic-test-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True, mode=0o700)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_category_command_parent_joins_exact_owned_invocation_without_raw_arguments(self):
        (self.directory / "proofs").mkdir()
        run = SimpleNamespace(
            root=self.directory, run_id=str(uuid.uuid4()), root_id=str(uuid.uuid4()),
            command_sequence=7, live_children=lambda: ())
        manifest = {
            "runId": run.run_id, "invocationGroupId": str(uuid.uuid4()),
            "attemptId": str(uuid.uuid4()), "purpose": "execution", "inputSha256": "a" * 64}
        arguments = ["dotnet", "vstest", "synthetic-private-path-canary"]
        settings = b"<RunSettings/>"
        (self.directory / "stores").mkdir()
        (self.directory / f'stores/settings-{manifest["attemptId"]}.runsettings').write_bytes(settings)
        record = {
            "schemaVersion": 1, "sequence": 7, "childPid": 123,
            "childStartSha256": "b" * 64, "startedMs": 2, "endedMs": 3,
            "exitCode": 0, "diagnosticCode": "None", "groupState": "Exited", "scope": "ordinary",
            "runId": run.run_id, "rootId": run.root_id,
            "argvSha256": checks.evidence.digest(arguments),
            "cwdSha256": hashlib.sha256(str(self.directory.absolute()).encode()).hexdigest(),
            "inputFiles": {"stores/source-context.json": "d" * 64},
            "outputFiles": {"proofs/source-index.json": "e" * 64}}
        path = self.directory / "proofs/execution-command-0007.json"
        parent = self.directory / f'proofs/category-command-{manifest["attemptId"]}-execution.json'
        changes = (
            {"schemaVersion": True}, {"sequence": True}, {"sequence": 8},
            {"childPid": True}, {"childPid": 0}, {"childStartSha256": "0" * 64},
            {"childStartSha256": "not-a-hash"}, {"startedMs": True}, {"startedMs": 0},
            {"startedMs": 4}, {"endedMs": 1}, {"endedMs": 5},
            {"exitCode": True}, {"exitCode": 1}, {"diagnosticCode": "AssertionFailed"},
            {"groupState": "Retained"}, {"scope": "recovery"},
            {"runId": str(uuid.uuid4())}, {"rootId": str(uuid.uuid4())},
            {"argvSha256": "c" * 64}, {"cwdSha256": "c" * 64}, {"extra": "forbidden"},
            {"outputFiles": []}, {"outputFiles": {}},
            {"outputFiles": {"../source-index.json": "e" * 64}},
            {"outputFiles": {"stores/source-index.json": "e" * 64}},
            {"outputFiles": {"proofs/source-index.json": "invalid"}},
            {"inputFiles": {"proofs/source-index.json": "d" * 64}},
            {"outputFiles": {f"proofs/source-{index}.json": "e" * 64 for index in range(16)}})
        def persist(value):
            if path.exists():
                path.chmod(0o600)
            raw = checks.evidence.canonical_bytes(value)
            path.write_bytes(raw)
            path.chmod(0o400)
            return SimpleNamespace(exit_code=0, execution_record_sha256=hashlib.sha256(raw).hexdigest())
        options = {
            "arguments": arguments, "cwd": self.directory, "manifest": manifest,
            "settings_data": settings, "started_ms": 1, "ended_ms": 4}
        for changed in (*({**record, **change} for change in changes),
                        {key: value for key, value in record.items() if key != "rootId"}):
            with self.subTest(changed=changed):
                result = persist(changed)
                with self.assertRaises(checks.evidence.ConformanceError):
                    checks.category_command_proof(run, result, **options)
                self.assertFalse(parent.exists())
        result = persist(record)
        for invalid_result in (SimpleNamespace(exit_code=0, execution_record_sha256="c" * 64),
                               SimpleNamespace(exit_code=0, execution_record_sha256=True),
                               SimpleNamespace(exit_code=False, execution_record_sha256=result.execution_record_sha256)):
            with self.assertRaises(checks.evidence.ConformanceError):
                checks.category_command_proof(run, invalid_result, **options)
        path.chmod(0o600)
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.category_command_proof(run, result, **options)
        path.chmod(0o400)
        settings_path = self.directory / f'stores/settings-{manifest["attemptId"]}.runsettings'
        settings_path.write_bytes(b"<Changed/>")
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.category_command_proof(run, result, **options)
        settings_path.write_bytes(settings)
        with patch.object(run, "live_children", return_value=(123,)):
            with self.assertRaises(checks.evidence.ConformanceError):
                checks.category_command_proof(run, result, **options)
        checks.category_command_proof(run, result, **options)
        admitted = json.loads(parent.read_bytes())
        self.assertFalse(admitted["qualification"])
        self.assertFalse(admitted["nativeContainment"])
        self.assertEqual(admitted["executionRecordSha256"], result.execution_record_sha256)
        self.assertEqual(admitted["manifestSha256"], checks.evidence.digest(manifest))
        self.assertEqual(admitted["settingsSha256"], hashlib.sha256(settings).hexdigest())
        self.assertNotIn(b"synthetic-private-path-canary", parent.read_bytes())
        with self.assertRaises(FileExistsError):
            checks.category_command_proof(run, result, **options)
        self.assertIsNone(checks.category_command_proof(
            run, SimpleNamespace(exit_code=0), **options))
        with patch.object(checks, "OwnedRun", SimpleNamespace):
            with self.assertRaises(checks.evidence.ConformanceError):
                checks.category_command_proof(run, SimpleNamespace(exit_code=0), **options)

    def test_metadata_category_batch_keeps_predeclared_transports_and_failure_history(self):
        self._assert_category_batch("metadata", 134)

    def test_artifact_category_batch_keeps_predeclared_transports_and_failure_history(self):
        self._assert_category_batch("artifacts", 227)

    def test_qualification_stall_and_recovery_are_fresh_inside_joint_attempt_before_scopes(self):
        for failed in (None, "stall", "recovery", "ownership", "consumer", "shared-consumer", "binary", "inventory", "hooks"):
            root = self.directory / str(failed)
            (root / "proofs").mkdir(parents=True)
            run = SimpleNamespace(root=root)
            sources = checks.NativeCategorySources.__new__(checks.NativeCategorySources)
            sources._run = run
            inputs = {"profileId": "metadata", "mode": "qualification"}
            candidate = root / "candidate"
            calls = []
            history = unittest.mock.Mock()
            history.begin_joint.side_effect = lambda *args, **options: calls.append("begin")
            history.joint_partitions.return_value = {"hook-admission": {}, "scope": {}}
            history.finish_joint.side_effect = lambda **options: calls.append("finish")

            def controls(name, namespace):
                def execute(actual_run, actual_inputs, actual_candidate=None, **options):
                    self.assertIs(actual_run, run)
                    self.assertIs(actual_inputs, inputs)
                    self.assertEqual(actual_candidate, None if name in ("shared-consumer", "hooks") else candidate)
                    self.assertEqual(options, {} if namespace is None else {"namespace": namespace})
                    calls.append(name)
                    if failed == name:
                        raise checks.evidence.ConformanceError("ProofMismatch")
                return execute

            def scope(*args, **options):
                name = "hooks" if args[3] == "hook-admission" else "scope"
                calls.append(name)
                if failed == name:
                    raise checks.evidence.ConformanceError("ProofMismatch")
                return {"transport": {}, "summary": {}}

            with self.subTest(failed=failed), patch.object(
                    checks.evidence, "CategoryRuntimeHistory", return_value=history), patch.object(
                    checks, "original_observation_inputs", return_value={}), patch.object(
                    checks, "sqlite_noncooperation", side_effect=controls(
                        "stall", "qualification-sqlite-native-noncooperation")), patch.object(
                    checks, "metadata_recovery_diagnostics", side_effect=controls(
                        "recovery", "qualification-sqlite-recovery")), patch.object(
                    checks, "metadata_ownership_diagnostics", side_effect=controls("ownership", None)), patch.object(
                    checks, "metadata_package_consumer_diagnostics", side_effect=controls("consumer", None)), patch.object(
                    checks, "metadata_common_consumer_diagnostics", side_effect=controls("shared-consumer", None)), patch.object(
                    checks, "metadata_binary_diagnostics", side_effect=controls("binary", None)), patch.object(
                    checks, "metadata_inventory_diagnostics", side_effect=controls("inventory", None)), patch.object(
                    checks, "category_attempt", side_effect=scope), patch.object(
                    checks, "_category_record", return_value={"qualification": False}), contextlib.redirect_stdout(io.StringIO()):
                options = {"inspection_cases": {}, "inspection_configurations": {}, "native_sources": sources}
                if failed is None:
                    self.assertFalse(checks.category_diagnostics(run, inputs, candidate, **options)["qualification"])
                    self.assertEqual(calls, [
                        "begin", "stall", "recovery", "ownership", "consumer", "shared-consumer",
                        "binary", "inventory", "hooks", "scope", "finish"])
                    history.interrupt_joint.assert_not_called()
                else:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                        checks.category_diagnostics(run, inputs, candidate, **options)
                    expected = ["begin", "stall", "recovery", "ownership", "consumer", "shared-consumer",
                                "binary", "inventory", "hooks"]
                    self.assertEqual(calls, expected[:expected.index(failed) + 1])
                    history.interrupt_joint.assert_called_once_with("ProofMismatch")
                    history.finish_joint.assert_not_called()

    def test_qualification_artifact_transfers_are_fresh_before_scopes_and_fail_closed(self):
        for failed in (None, "transfers", "hooks", "scope"):
            root = self.directory / str(failed)
            (root / "proofs").mkdir(parents=True)
            run = SimpleNamespace(root=root)
            sources = object.__new__(checks.NativeCategorySources)
            sources._run = run
            inputs = {"profileId": "artifacts", "mode": "qualification"}
            candidate, calls = root / "candidate", []
            history = unittest.mock.Mock()
            history.begin_joint.side_effect = lambda *args, **options: calls.append("begin")
            history.joint_partitions.return_value = {"hook-admission": {}, "controller": {}}
            history.finish_joint.side_effect = lambda **options: calls.append("finish")

            def transfers(actual_run, actual_inputs, actual_candidate, **options):
                self.assertIs(actual_run, run)
                self.assertIs(actual_inputs, inputs)
                self.assertEqual(actual_candidate, candidate)
                self.assertEqual(options, {"namespace": "qualification-artifact-transfers"})
                calls.append("transfers")
                if failed == "transfers":
                    raise checks.evidence.ConformanceError("ProofMismatch")

            def scope(*args, **options):
                self.assertIs(options["native_sources"], sources)
                self.assertEqual(options["run_inputs_path"], "proofs/category-artifacts-qualification-run-inputs.json")
                name = "hooks" if args[3] == "hook-admission" else "scope"
                calls.append(name)
                if failed == name:
                    raise checks.evidence.ConformanceError("ProofMismatch")
                return {"transport": {}, "summary": {}}

            with self.subTest(failed=failed), patch.object(
                    checks.evidence, "CategoryRuntimeHistory", return_value=history), patch.object(
                    checks, "original_observation_inputs", return_value={}), patch.object(
                    checks, "artifact_transfer_diagnostics", side_effect=transfers), patch.object(
                    checks, "category_attempt", side_effect=scope), patch.object(
                    checks, "_category_record", return_value={"qualification": False}) as record, contextlib.redirect_stdout(io.StringIO()):
                options = {"inspection_cases": {}, "inspection_configurations": {}, "native_sources": sources}
                if failed is None:
                    self.assertFalse(checks.category_diagnostics(run, inputs, candidate, **options)["qualification"])
                    self.assertEqual(calls, ["begin", "transfers", "hooks", "scope", "finish"])
                    history.interrupt_joint.assert_not_called()
                else:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                        checks.category_diagnostics(run, inputs, candidate, **options)
                    expected = ["begin", "transfers", "hooks", "scope"]
                    self.assertEqual(calls, expected[:expected.index(failed) + 1])
                    history.interrupt_joint.assert_called_once_with("ProofMismatch")
                    history.finish_joint.assert_not_called()
                    self.assertEqual(record.call_args.args[-1], "ProofMismatch")

    def test_category_record_persists_original_quality_basis_and_rejects_replacement(self):
        path, raw = "proofs/category-artifacts-QC-09-basis-0001.json", b'{"original":"complete-basis"}'
        for defect in (None, "existing", "changed", "mutable", "hash"):
            root = self.directory / str(defect)
            destination = root / path
            destination.parent.mkdir(parents=True)
            if defect in ("existing", "changed", "mutable"):
                destination.write_bytes(b"replacement" if defect == "changed" else raw)
                destination.chmod(0o600 if defect == "mutable" else 0o400)
            history = SimpleNamespace(
                quality_proofs={path: raw},
                witnesses=(),
                proofs={path: "0" * 64 if defect == "hash" else hashlib.sha256(raw).hexdigest()},
                results=lambda: [{"status": "Incomplete"}])
            with self.subTest(defect=defect):
                if defect in ("changed", "mutable", "hash"):
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                        checks._category_record(
                            SimpleNamespace(root=root), {"profileId": "artifacts", "mode": "qualification"}, history, {})
                    self.assertFalse((root / "proofs/category-artifacts-qualification-history.json").exists())
                else:
                    summary = checks._category_record(
                        SimpleNamespace(root=root), {"profileId": "artifacts", "mode": "qualification"}, history, {})
                    self.assertEqual(destination.read_bytes(), raw)
                    self.assertEqual(destination.stat().st_mode & 0o777, 0o400)
                    self.assertEqual(summary["qualitySourceCount"], 1)
                    self.assertEqual(summary["qualitySourcesSha256"], checks.evidence.digest(history.proofs))
                    self.assertFalse(summary["qualification"])

    def _assert_category_batch(self, profile, witness_count):
        from conformance_case_catalog import category_execution_partitions, category_runtime_cases, expected_cases
        partitions = category_execution_partitions(profile)
        case_count = len(expected_cases(profile))
        plans = {scope_id: {
            "attemptId": str(uuid.uuid4()),
            "tests": {identity: (binding, category_runtime_cases(profile, binding)[identity])
                      for binding, identity in rows}} for scope_id, rows in partitions.items()}
        for failure in (None, "execution", "admission"):
            root = self.directory / str(failure)
            (root / "proofs").mkdir(parents=True)
            inputs = {
                "profileId": profile, "mode": "diagnostic",
                "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4())}
            transports = {scope: object() for scope in plans}
            history = unittest.mock.Mock()
            history.joint_partitions.return_value = plans
            history.results.return_value = [{"status": "Incomplete"} for _ in range(case_count)]
            history.quality_proofs = {}
            history.witnesses, history.proofs = (), {}
            if failure == "admission":
                history.finish_joint.side_effect = checks.evidence.ConformanceError("ProofMismatch")
            captured = []
            def execute(run, captured_inputs, candidate, scope_id, plan, **options):
                self.assertIs(captured_inputs, inputs)
                self.assertIs(plan, plans[scope_id])
                self.assertEqual(options["run_inputs_path"], f"proofs/category-{profile}-run-inputs.json")
                if "prepared" in scope_id:
                    self.assertEqual(options["inspection_cases"], {"selected": "inputs"})
                captured.append(scope_id)
                if failure == "execution" and len(captured) == 3:
                    raise checks.evidence.ConformanceError("ProofMismatch")
                source = ({"sourceParentSha256": hashlib.sha256(scope_id.encode()).hexdigest()}
                          if scope_id.startswith("inspection-") or scope_id == "controller" else {})
                return {"transport": transports[scope_id],
                        "summary": {"tests": len(plan["tests"]), "qualification": False, "code": "None", **source}}
            diagnostics = io.StringIO()
            with self.subTest(failure=failure), contextlib.redirect_stdout(diagnostics), patch.object(
                    checks, "OwnedRun", SimpleNamespace), patch.object(
                    checks.evidence, "CategoryRuntimeHistory", return_value=history), patch.object(
                        checks, "category_attempt", side_effect=execute):
                arguments = (
                    SimpleNamespace(root=root), inputs, root / "candidate")
                options = {"inspection_cases": {"selected": "inputs"}, "inspection_configurations": {}}
                if failure is not None:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                        checks.category_diagnostics(*arguments, **options)
                    if failure == "execution":
                        history.interrupt_joint.assert_called_once_with("ProofMismatch")
                        history.finish_joint.assert_not_called()
                    else:
                        history.interrupt_joint.assert_not_called()
                        history.finish_joint.assert_called_once()
                else:
                    summary = checks.category_diagnostics(*arguments, **options)
                    history.finish_joint.assert_called_once()
                    received = history.finish_joint.call_args.kwargs["transports"]
                    self.assertEqual(set(received), set(plans))
                    self.assertTrue(all(received[key] is value for key, value in transports.items()))
                    self.assertEqual(summary["tests"], witness_count)
                    self.assertEqual(summary["caseCount"], case_count)
                    parents = {scope: hashlib.sha256(scope.encode()).hexdigest()
                               for scope in plans if scope.startswith("inspection-") or scope == "controller"}
                    self.assertEqual(summary["sourceParentCount"], len(parents))
                    self.assertEqual(summary["sourceParentsSha256"], checks.evidence.digest(parents))
                    self.assertFalse(summary["qualification"])
                    self.assertEqual(
                        json.loads(json.dumps({"category": summary}))["category"], summary)
                    history.interrupt_joint.assert_not_called()
                self.assertEqual(history.begin_joint.call_args.kwargs["partitions"], partitions)
                record = json.loads((root / f"proofs/category-{profile}-diagnostic-history.json").read_bytes())
                self.assertFalse(record["qualification"])
                self.assertEqual(record["code"], "ProofMismatch" if failure else "EvidenceIncomplete")
                self.assertEqual(len(record["results"]), case_count)
                if failure:
                    diagnostic = json.loads(diagnostics.getvalue())
                    locations = diagnostic.pop("locations")
                    self.assertTrue(0 < len(locations) <= 4)
                    self.assertTrue(all(location["source"] == "scripts/conformance_sdk_checks.py"
                                        and type(location["line"]) is int and location["line"] > 0
                                        for location in locations))
                if failure == "execution":
                    self.assertEqual(diagnostic, {
                        "qualification": False, "phase": "category-scope-failure",
                        "profileId": profile, "scopeId": captured[-1], "code": "ProofMismatch"})
                elif failure == "admission":
                    self.assertEqual(diagnostic, {
                        "qualification": False, "phase": "category-admission-failure",
                        "profileId": profile, "scopeCount": len(plans), "code": "ProofMismatch"})
                else:
                    self.assertEqual(diagnostics.getvalue(), "")

    def test_category_runtime_scopes_preserve_exact_catalog_binding_and_case_assignments(self):
        from conformance_case_catalog import category_execution_partitions, category_runtime_cases
        (self.directory / "stores").mkdir()
        (self.directory / "runtime-owner.json").write_bytes(b"{}")
        runner = self.directory / "Hoard.Fixtures.Artifacts.CrashRunner.dll"
        runner.write_bytes(b"runner")
        (self.directory / "proofs/artifact-transfers").mkdir(parents=True)
        (self.directory / "proofs/category-artifact-transfers").mkdir()
        configurations = {family: self.directory / (family + ".json") for family in ("metadata", "artifacts")}
        for path in configurations.values():
            path.write_bytes(b"{}")
        selected = {
            identity: {str(configurations[family]): checks.evidence.file_sha256(configurations[family])}
            for identity, family in checks.ORIGINAL_INSPECTION_WITNESSES.items()
            if identity not in checks.ORIGINAL_INSPECTION_LITERAL_WITNESSES}
        launches = []
        run = SimpleNamespace(
            root=self.directory, run_id=str(uuid.uuid4()), root_id=str(uuid.uuid4()),
            command_sequence=0, live_children=lambda: ())
        def launch(arguments, **kwargs):
            launches.append((arguments, kwargs))
            run.command_sequence += 1
            instant = checks.time.monotonic() * 1000
            path = self.directory / f"proofs/execution-command-{run.command_sequence:04}.json"
            record = {
                "schemaVersion": 1, "sequence": run.command_sequence, "childPid": 123,
                "childStartSha256": "b" * 64, "startedMs": instant, "endedMs": instant,
                "exitCode": 0, "diagnosticCode": "None", "groupState": "Exited", "scope": "ordinary",
                "runId": run.run_id, "rootId": run.root_id, "argvSha256": checks.evidence.digest(arguments),
                "cwdSha256": hashlib.sha256(str(kwargs["cwd"].absolute()).encode()).hexdigest()}
            checks.write_new(path, checks.evidence.canonical_bytes(record))
            return SimpleNamespace(exit_code=0, execution_record_sha256=checks.evidence.file_sha256(path))
        run.command = launch
        for profile in ("metadata", "artifacts"):
            for scope_id, pairs in category_execution_partitions(profile).items():
                inspection = scope_id.startswith("inspection-")
                assembly = self.directory / ("Hoard.Architecture.Tests.dll" if inspection else
                                              "Hoard.Metadata.Tests.dll" if profile == "metadata" else
                                              "Hoard.Artifacts.Tests.dll")
                options = {"category_scope": (profile, scope_id)}
                if scope_id.startswith("inspection-literals-"):
                    options["inspection_literals"] = True
                elif scope_id.startswith("inspection-prepared-"):
                    options.update(inspection_cases=selected, inspection_configurations=configurations)
                elif scope_id == "controller":
                    options["artifact_runner"] = runner
                else:
                    options["original_observations"] = True
                    if profile == "metadata":
                        options["metadata_provider"] = pairs[0][0]
                expected = [{
                    "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
                    "bindingId": binding, "caseId": category_runtime_cases(profile, binding)[identity],
                } for binding, identity in pairs]
                manifest = {
                    "runId": run.run_id, "invocationGroupId": str(uuid.uuid4()),
                    "attemptId": str(uuid.uuid4()), "purpose": "execution",
                    "assemblies": [{"path": assembly.relative_to(self.directory).as_posix()}],
                    "inputSha256": "a" * 64, "runInputsPath": "proofs/category-inputs.json", "expected": expected}
                if profile == "metadata" and scope_id.startswith("original-"):
                    manifest["assemblies"].extend(
                        {"path": "images/" + name + ".dll"}
                        for name in ("Hoard.Testing.Conformance", "Hoard.Fixtures.Metadata.HostAdapters",
                                     "Hoard.Fixtures.Metadata." + ("Memory" if pairs[0][0] == "memory" else "Sqlite")))
                with self.subTest(profile=profile, scope=scope_id):
                    checks.runtime_command(run, assembly, manifest, **options)
                    if profile == "metadata" and scope_id.startswith("original-"):
                        self.assertTrue({entry["path"] for entry in manifest["assemblies"]} <= set(
                            launches[-1][1]["execution_inputs"]))
                    if scope_id == "controller":
                        settings = ET.fromstring((self.directory / "stores" / (
                            "settings-" + manifest["attemptId"] + ".runsettings")).read_bytes())
                        self.assertEqual(
                            settings.findtext("./RunConfiguration/EnvironmentVariables/HOARD_ARTIFACT_TRANSFER_PROOFS"),
                            str(self.directory / "proofs/category-artifact-transfers"))
                    if inspection:
                        context = self.directory / "stores" / ("inspection-context-" + manifest["attemptId"] + ".json")
                        observed = json.loads(context.read_bytes())["cases"]
                        self.assertEqual(set(observed), {identity for _, identity in pairs})
                        self.assertEqual(observed, {identity: selected[identity] if "prepared" in scope_id else {}
                                                    for _, identity in pairs})
                        discovery = {**manifest, "attemptId": str(uuid.uuid4()), "purpose": "discovery"}
                        checks.runtime_command(run, assembly, discovery, **options)
                        self.assertFalse((self.directory / "stores" / (
                            "inspection-context-" + discovery["attemptId"] + ".json")).exists())
                    count = len(launches)
                    for changed in (
                        expected[:-1],
                        [{**expected[0], "bindingId": "foreign"}, *expected[1:]],
                        [{**expected[0], "caseId": "foreign"}, *expected[1:]],
                        [*expected, expected[0]],
                    ):
                        with self.assertRaises(checks.evidence.ConformanceError):
                            checks.runtime_command(
                                run, assembly, {**manifest, "attemptId": str(uuid.uuid4()), "expected": changed}, **options)
                    with self.assertRaises(checks.evidence.ConformanceError):
                        checks.runtime_command(
                            run, assembly, {**manifest, "attemptId": str(uuid.uuid4())},
                            **{**options, "category_scope": (profile, "foreign")})
                    self.assertEqual(len(launches), count)
        self.assertEqual(len(launches), 18)
        self.assertTrue(all(options["record_execution"] is True for _, options in launches))
        self.assertEqual(len(tuple((self.directory / "proofs").glob("category-command-*.json"))), 18)

    def test_category_inspection_receipts_join_only_the_exact_catalog_binding_scope(self):
        from conformance_case_catalog import category_execution_partitions, category_runtime_cases
        for name in ("stores", "proofs", "feed/candidate"):
            (self.directory / name).mkdir(parents=True, exist_ok=True)
        (self.directory / "stores/candidate.NuGet.Config").write_bytes(
            checks.evidence.synthetic_nuget_configuration(self.directory / "feed/candidate"))
        selected = {identity: {str(self.directory / "input.xml"): "a" * 64}
                    for identity in checks.original_inspection_prepared_scenarios()[0][1]}
        for profile in ("metadata", "artifacts"):
            for scope_id, pairs in category_execution_partitions(profile).items():
                if not scope_id.startswith("inspection-"):
                    continue
                inputs = {
                    "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                    "mode": "diagnostic", "profileId": profile,
                    "configurationSha256": checks.evidence.configuration_fingerprint(
                        checks.evidence.verify_synthetic_source_mapping(
                            self.directory, "stores/candidate.NuGet.Config", "feed/candidate"),
                        inspection_inputs=selected)}
                manifest = {
                    "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
                    "inputSha256": checks.evidence.digest(inputs), "attemptId": str(uuid.uuid4()), "purpose": "execution",
                    "expected": [{
                        "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
                        "bindingId": binding, "caseId": category_runtime_cases(profile, binding)[identity],
                    } for binding, identity in pairs]}
                witnesses = [{
                    "testIdentity": identity, "executionId": str(uuid.uuid4()), "proofSha256": str(index + 1) * 64,
                    "status": "Passed", "bindingId": binding} for index, (binding, identity) in enumerate(pairs)]
                ingested = {
                    "diagnosticCode": "None", "attemptId": manifest["attemptId"], "witnesses": witnesses,
                    "proofs": {f'proof-{row["executionId"]}.json': row["proofSha256"] for row in witnesses}}
                capture = self.directory / "stores" / ("original-inspection-" + manifest["attemptId"])
                capture.mkdir()
                for _, identity in pairs:
                    files = selected[identity] if "prepared" in scope_id else {}
                    (capture / ("inspection-" + hashlib.sha256(identity.encode()).hexdigest() + ".json")).write_bytes(
                        checks.evidence.canonical_bytes({
                            "schemaVersion": 1, "qualification": False, "runId": inputs["runId"],
                            "attemptId": manifest["attemptId"], "inputsSha256": checks.evidence.digest(inputs),
                            "testIdentity": identity,
                            "files": {hashlib.sha256(path.encode()).hexdigest(): hashed for path, hashed in files.items()}}))
                options = {"category_scope": (profile, scope_id), "selected": selected}
                run = SimpleNamespace(root=self.directory)
                receipt = self.directory / f'proofs/category-{profile}-{scope_id}-{manifest["attemptId"]}.json'
                with self.subTest(profile=profile, scope=scope_id):
                    changed = {**ingested, "witnesses": [
                        {**witnesses[0], "bindingId": "foreign"}, *witnesses[1:]]}
                    with self.assertRaises(checks.evidence.ConformanceError):
                        checks.category_inspection_proofs(run, inputs, manifest, changed, **options)
                    self.assertFalse(receipt.exists())
                    with self.assertRaises(checks.evidence.ConformanceError):
                        checks.category_inspection_proofs(
                            run, {**inputs, "profileId": "harness"}, manifest, ingested, **options)
                    self.assertFalse(receipt.exists())
                    if "prepared" in scope_id:
                        with self.assertRaises(checks.evidence.ConformanceError):
                            checks.category_inspection_proofs(
                                run, {**inputs, "configurationSha256": "f" * 64}, manifest, ingested, **options)
                        self.assertFalse(receipt.exists())
                    result = checks.category_inspection_proofs(run, inputs, manifest, ingested, **options)
                    self.assertEqual(result["sourceExecutions"], len(pairs))
                    self.assertEqual(result["inspectionProofsSha256"], checks.evidence.file_sha256(receipt))
                    self.assertFalse(json.loads(receipt.read_bytes())["qualification"])
                    parent = self.directory / f'proofs/category-source-{manifest["attemptId"]}.json'
                    source_options = {
                        "category_scope": (profile, scope_id), "result": SimpleNamespace(exit_code=0)}
                    changed_sources = {**result, "inspectionProofsSha256": "0" * 64}
                    for sources in (changed_sources, {**result, "sourceExecutions": len(pairs) + 1}):
                        with self.assertRaises(checks.evidence.ConformanceError):
                            checks.category_source_parent(
                                run, inputs, manifest, ingested, sources, **source_options)
                        self.assertFalse(parent.exists())
                    with patch.object(checks, "OwnedRun", SimpleNamespace):
                        with self.assertRaises(checks.evidence.ConformanceError):
                            checks.category_source_parent(
                                run, inputs, manifest, ingested, result, **source_options)
                    self.assertFalse(parent.exists())
                    source_hash = checks.category_source_parent(
                        run, inputs, manifest, ingested, result, **source_options)
                    linked = json.loads(parent.read_bytes())
                    self.assertEqual(source_hash, checks.evidence.file_sha256(parent))
                    self.assertFalse(linked["qualification"])
                    self.assertFalse(linked["nativeContainment"])
                    self.assertIsNone(linked["executionParentSha256"])
                    self.assertEqual(linked["sourceReceiptSha256"], result["inspectionProofsSha256"])
                    self.assertEqual(
                        {(row["bindingId"], row["caseId"], row["executionId"], row["runtimeProofSha256"])
                         for row in linked["observations"]},
                        {(binding, category_runtime_cases(profile, binding)[identity],
                          next(row["executionId"] for row in witnesses if row["testIdentity"] == identity),
                          next(row["proofSha256"] for row in witnesses if row["testIdentity"] == identity))
                         for binding, identity in pairs})
                    parent.unlink()
                    run.run_id, run.root_id = inputs["runId"], str(uuid.uuid4())
                    run.command_sequence, run.live_children = 1, lambda: ()
                    arguments, settings = ["dotnet", "vstest", "synthetic-source-command-canary"], b"<RunSettings/>"
                    settings_path = self.directory / f'stores/settings-{manifest["attemptId"]}.runsettings'
                    settings_path.write_bytes(settings)
                    record = {
                        "schemaVersion": 1, "sequence": 1, "childPid": 123, "childStartSha256": "b" * 64,
                        "startedMs": 2, "endedMs": 3, "exitCode": 0, "diagnosticCode": "None",
                        "groupState": "Exited", "scope": "ordinary", "runId": run.run_id, "rootId": run.root_id,
                        "argvSha256": checks.evidence.digest(arguments),
                        "cwdSha256": hashlib.sha256(str(self.directory.absolute()).encode()).hexdigest()}
                    record_path = self.directory / "proofs/execution-command-0001.json"
                    checks.write_new(record_path, checks.evidence.canonical_bytes(record))
                    execution = SimpleNamespace(exit_code=0, execution_record_sha256=checks.evidence.file_sha256(record_path))
                    command_parent = self.directory / f'proofs/category-command-{manifest["attemptId"]}-execution.json'
                    source_options["result"] = execution
                    with patch.object(checks, "OwnedRun", SimpleNamespace), patch.object(
                            run, "read_execution_record", return_value=record_path.read_bytes(), create=True) as native_record:
                        checks.category_command_proof(
                             run, execution, arguments=arguments, cwd=self.directory, manifest=manifest,
                             settings_data=settings, started_ms=1, ended_ms=4)
                        command_raw = command_parent.read_bytes()
                        command_value = json.loads(command_raw)
                        for change in (
                                 {"runId": str(uuid.uuid4())}, {"rootId": str(uuid.uuid4())},
                                 {"attemptId": str(uuid.uuid4())}, {"invocationGroupId": str(uuid.uuid4())},
                                 {"commandSequence": 2},
                                 {"inputsSha256": "0" * 64}, {"manifestSha256": "0" * 64},
                                 {"executionRecordSha256": "0" * 64}, {"settingsSha256": "0" * 64},
                                 {"nativeContainment": False}, {"purpose": "discovery"}, {"extra": True}):
                             command_parent.chmod(0o600)
                             command_parent.write_bytes(checks.evidence.canonical_bytes({**command_value, **change}))
                             command_parent.chmod(0o400)
                             with self.assertRaises(checks.evidence.ConformanceError):
                                 checks.category_source_parent(run, inputs, manifest, ingested, result, **source_options)
                             self.assertFalse(parent.exists())
                        command_parent.chmod(0o600)
                        command_parent.write_bytes(command_raw)
                        with self.assertRaises(checks.evidence.ConformanceError):
                             checks.category_source_parent(run, inputs, manifest, ingested, result, **source_options)
                        command_parent.chmod(0o400)
                        settings_path.write_bytes(b"<Changed/>")
                        with self.assertRaises(checks.evidence.ConformanceError):
                             checks.category_source_parent(run, inputs, manifest, ingested, result, **source_options)
                        settings_path.write_bytes(settings)
                        with patch.object(run, "live_children", return_value=(123,)):
                             with self.assertRaises(checks.evidence.ConformanceError):
                                 checks.category_source_parent(run, inputs, manifest, ingested, result, **source_options)
                        record_path.chmod(0o600)
                        with self.assertRaises(checks.evidence.ConformanceError):
                             checks.category_source_parent(run, inputs, manifest, ingested, result, **source_options)
                        record_path.chmod(0o400)
                        with patch.object(run, "read_execution_record",
                                          side_effect=checks.evidence.ConformanceError("OwnershipInvalid")):
                             with self.assertRaisesRegex(checks.evidence.ConformanceError, "OwnershipInvalid"):
                                  checks.category_source_parent(run, inputs, manifest, ingested, result, **source_options)
                        self.assertFalse(parent.exists())
                        checks.category_source_parent(run, inputs, manifest, ingested, result, **source_options)
                        native_record.assert_called_with(1)
                    linked = json.loads(parent.read_bytes())
                    self.assertTrue(linked["nativeContainment"])
                    self.assertFalse(linked["qualification"])
                    self.assertEqual(linked["commandSequence"], 1)
                    self.assertEqual(linked["executionParentSha256"], hashlib.sha256(command_raw).hexdigest())
                    self.assertNotIn(b"synthetic-source-command-canary", parent.read_bytes())
                    record_path.unlink()
                    receipt.unlink()
                    changed_manifest = {**manifest, "expected": [
                        {**manifest["expected"][0], "caseId": "foreign"}, *manifest["expected"][1:]]}
                    with self.assertRaises(checks.evidence.ConformanceError):
                        checks.category_inspection_proofs(run, inputs, changed_manifest, ingested, **options)
                    self.assertFalse(receipt.exists())

    def test_category_attempt_uses_the_predeclared_scope_without_relabelling_runtime_inputs(self):
        from conformance_case_catalog import CATEGORY_BINDING_SLOTS, category_execution_partitions, category_runtime_cases
        candidate = self.directory / "current"
        runner = candidate / checks.ARTIFACT_RECOVERY / "bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll"
        runner.parent.mkdir(parents=True)
        runner.write_bytes(b"runner")
        for name in ("stores", "proofs", "feed/candidate"):
            (self.directory / name).mkdir(parents=True, exist_ok=True)
        (self.directory / "stores/candidate.NuGet.Config").write_bytes(
            checks.evidence.synthetic_nuget_configuration(self.directory / "feed/candidate"))
        selected = {identity: {str(self.directory / "input.xml"): "a" * 64}
                    for identity in checks.original_inspection_prepared_scenarios()[0][1]}
        configurations = {category: self.directory / (category + ".json") for category in ("metadata", "artifacts")}
        originals = checks.original_observation_inputs(candidate, self.directory)
        assemblies = {runner.relative_to(self.directory).as_posix(): checks.evidence.file_sha256(runner)}
        for binding in originals.values():
            for identity, assignments in binding.items():
                for node in checks.evidence.original_node_assignments(identity, assignments):
                    assemblies.update({path: "b" * 64 for path, _ in node.values()})
        for profile in ("metadata", "artifacts"):
            for scope_id, pairs in category_execution_partitions(profile).items():
                inspection = scope_id.startswith("inspection-")
                folder, output, name = (
                    (checks.ARCHITECTURE_TESTS, "bin", "Hoard.Architecture.Tests.dll") if inspection else
                    (checks.METADATA_TESTS, checks.METADATA_TEST_OUTPUT, "Hoard.Metadata.Tests.dll") if profile == "metadata"
                    else (checks.ARTIFACT_TESTS, checks.ARTIFACT_TEST_OUTPUT, "Hoard.Artifacts.Tests.dll"))
                assembly = candidate / folder / output / "Release/net10.0" / name
                assemblies[assembly.relative_to(self.directory).as_posix()] = "b" * 64
                inputs = {
                    "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                    "profileId": profile, "mode": "diagnostic",
                    "runtimeAssemblies": assemblies,
                    "bindings": [{"bindingId": binding, "category": category, "package": {
                        "packageId": package, "version": "0.1.0",
                        "sha256": hashlib.sha256(package.encode()).hexdigest()}}
                        for category, binding, _, package in CATEGORY_BINDING_SLOTS],
                    "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "c" * 64},
                                 *({"packageId": package, "version": "0.1.0",
                                    "sha256": hashlib.sha256(package.encode()).hexdigest()}
                                   for _, _, _, package in CATEGORY_BINDING_SLOTS)],
                    "configurationSha256": checks.evidence.configuration_fingerprint(
                        checks.evidence.verify_synthetic_source_mapping(
                            self.directory, "stores/candidate.NuGet.Config", "feed/candidate"),
                        inspection_inputs=selected)}
                path = "proofs/category-inputs.json"
                (self.directory / path).write_bytes(checks.evidence.canonical_bytes(inputs))
                plan = {
                    "attemptId": str(uuid.uuid4()),
                    "tests": {identity: (binding, category_runtime_cases(profile, binding)[identity])
                              for binding, identity in pairs}}
                options = {"run_inputs_path": path}
                if "prepared" in scope_id:
                    options.update(inspection_cases=selected, inspection_configurations=configurations)
                with self.subTest(profile=profile, scope=scope_id), patch.object(
                        checks, "_execute_runtime_transport",
                        side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch, patch.object(
                            checks, "require_sqlite_environment"):
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                        checks.category_attempt(run=SimpleNamespace(root=self.directory), inputs=inputs,
                                                candidate=candidate, scope_id=scope_id, plan=plan, **options)
                    launch.assert_called_once()
                    self.assertEqual(launch.call_args.args[2], assembly)
                    manifest = launch.call_args.args[3]
                    self.assertEqual(manifest["attemptId"], plan["attemptId"])
                    self.assertEqual(manifest["inputSha256"], checks.evidence.digest(inputs))
                    self.assertEqual(manifest["runInputsPath"], path)
                    self.assertEqual({item["testIdentity"]: (item["bindingId"], item["caseId"])
                                      for item in manifest["expected"]}, plan["tests"])
                    packages = {binding["bindingId"]: binding["package"] for binding in inputs["bindings"]}
                    self.assertEqual({entry["packageId"] for entry in manifest["expected"]},
                                     {packages[binding]["packageId"] for binding, _ in pairs})
                    self.assertTrue(all(entry["packageId"] == packages[entry["bindingId"]]["packageId"]
                                        for entry in manifest["expected"]))
                    self.assertEqual({row["id"]: row["sha256"] for row in manifest["packages"]},
                                     {packages[binding]["packageId"]: packages[binding]["sha256"]
                                      for binding, _ in pairs})
                    self.assertEqual(launch.call_args.args[5]["category_scope"], (profile, scope_id))
                    if inspection or scope_id == "controller":
                        source_function = "category_inspection_proofs" if inspection else "original_artifact_external_proofs"
                        source_key = "inspectionProofsSha256" if inspection else "externalProofsSha256"
                        with patch.object(
                                checks, "_execute_runtime_transport",
                                return_value=(SimpleNamespace(exit_code=0), {},
                                              {"proofs": {}, "completion_data": b""}, "c" * 64)), patch.object(
                                    checks, "validate_observation"), patch.object(
                                        checks, source_function, return_value={
                                            "sourceExecutions": len(pairs), source_key: "d" * 64}), patch.object(
                                                checks, "category_source_parent",
                                                side_effect=checks.evidence.ConformanceError("OwnershipInvalid")):
                            with self.assertRaisesRegex(checks.evidence.ConformanceError, "OwnershipInvalid"):
                                checks.category_attempt(
                                    run=SimpleNamespace(root=self.directory), inputs=inputs,
                                    candidate=candidate, scope_id=scope_id, plan=plan, **options)
                    launch.reset_mock()
                    binding_id = pairs[0][0]
                    foreign_package = next(binding["package"] for binding in inputs["bindings"]
                                           if binding["bindingId"] != binding_id)
                    changed_inputs = {**inputs, "bindings": [
                        {**binding, "package": foreign_package} if binding["bindingId"] == binding_id else binding
                        for binding in inputs["bindings"]]}
                    (self.directory / path).write_bytes(checks.evidence.canonical_bytes(changed_inputs))
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "BindingInvalid"):
                        checks.category_attempt(
                            run=SimpleNamespace(root=self.directory), inputs=changed_inputs,
                            candidate=candidate, scope_id=scope_id, plan=plan, **options)
                    launch.assert_not_called()
                    (self.directory / path).write_bytes(checks.evidence.canonical_bytes(inputs))
                    changed = {**plan, "tests": {**plan["tests"], "Foreign.Check": ("foreign", "MP-01")}}
                    with self.assertRaises(checks.evidence.ConformanceError):
                        checks.category_attempt(run=SimpleNamespace(root=self.directory), inputs=inputs,
                                                candidate=candidate, scope_id=scope_id, plan=changed, **options)
                    launch.assert_not_called()
                    (self.directory / path).write_bytes(b"{}")
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                        checks.category_attempt(run=SimpleNamespace(root=self.directory), inputs=inputs,
                                                candidate=candidate, scope_id=scope_id, plan=plan, **options)
                    launch.assert_not_called()

    def test_original_literal_inspections_select_the_actual_architecture_assembly_before_launch(self):
        factory = getattr(checks, "original_inspection_literal_scenarios", None)
        self.assertTrue(callable(factory), "Literal inspection witnesses need their own real architecture execution scope.")
        scenario, = factory()
        prefix = "Hoard.Architecture.Tests.MetadataBoundaryTests."
        expected = {prefix + method for method in (
            "Native_only_packages_cannot_hide_managed_assets",
            "Package_groups_follow_actual_resolved_assets_not_a_guessed_framework",
            "Pruned_dependency_needs_sdk_evidence_a_compatible_version_and_an_actual_framework_reference")}
        self.assertEqual(scenario, ("original-inspection-literals", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / "tests/architecture/Hoard.Architecture.Tests/bin/Release/net10.0/Hoard.Architecture.Tests.dll"
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}]}
        with patch.object(checks, "runtime_command", side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[1], assembly)
        self.assertEqual(launch.call_args.kwargs, {"inspection_literals": True})
        self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
        self.assertEqual({item["bindingId"] for item in launch.call_args.args[2]["expected"]}, {"none"})

    def test_original_literal_inspection_receipts_require_exact_current_packets_and_runtime_proofs(self):
        self.assertTrue(callable(getattr(checks, "original_inspection_literal_proofs", None)),
                        "A source-created inspection packet must independently join its admitted runtime proof.")
        scenario, = checks.original_inspection_literal_scenarios()
        inputs = {"runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()), "mode": "diagnostic"}
        manifest = {
            **inputs, "inputSha256": checks.evidence.digest(inputs), "attemptId": str(uuid.uuid4()),
            "expected": [{"testIdentity": identity} for identity in scenario[1]]}
        witnesses = [{
            "testIdentity": identity, "executionId": str(uuid.uuid4()), "proofSha256": str(index + 1) * 64,
            "status": "Passed", "bindingId": "none"} for index, identity in enumerate(scenario[1])]
        ingested = {
            "diagnosticCode": "None", "attemptId": manifest["attemptId"], "witnesses": witnesses,
            "proofs": {f'proof-{row["executionId"]}.json': row["proofSha256"] for row in witnesses}}
        capture = self.directory / "stores" / ("original-inspection-" + manifest["attemptId"])
        capture.mkdir(parents=True)
        (self.directory / "proofs").mkdir()
        packets = {}
        for identity in scenario[1]:
            path = capture / ("inspection-" + hashlib.sha256(identity.encode()).hexdigest() + ".json")
            packets[path] = checks.evidence.canonical_bytes({
                "schemaVersion": 1, "qualification": False, "runId": inputs["runId"],
                "attemptId": manifest["attemptId"], "inputsSha256": checks.evidence.digest(inputs),
                "testIdentity": identity, "files": {}})
        def restore():
            for path in capture.iterdir():
                path.unlink()
            for path, raw in packets.items():
                path.write_bytes(raw)
        restore()
        run = SimpleNamespace(root=self.directory)
        result = checks.original_inspection_literal_proofs(run, inputs, manifest, ingested)
        receipt_path = self.directory / ("proofs/original-inspection-literals-" + manifest["attemptId"] + ".json")
        receipt = checks.evidence.load_json(receipt_path.read_bytes())
        self.assertEqual(result, {"sourceExecutions": 3, "inspectionProofsSha256": checks.evidence.digest(receipt)})
        self.assertEqual({row["testIdentity"] for row in receipt["observations"]}, set(scenario[1]))
        receipt_path.unlink()
        selected = next(iter(packets))
        for change in (
                {"schemaVersion": True}, {"qualification": True}, {"runId": str(uuid.uuid4())},
                {"attemptId": str(uuid.uuid4())}, {"inputsSha256": "f" * 64}, {"extra": True},
                {"testIdentity": scenario[1][1]}, {"files": {"a" * 64: "b" * 64}}):
            restore()
            selected.write_bytes(checks.evidence.canonical_bytes(checks.evidence.load_json(packets[selected]) | change))
            with self.subTest(change=change), self.assertRaises(checks.evidence.ConformanceError):
                checks.original_inspection_literal_proofs(run, inputs, manifest, ingested)
            self.assertFalse(receipt_path.exists())
        for mutation in ("missing", "extra", "duplicate"):
            restore()
            if mutation == "missing":
                selected.unlink()
            elif mutation == "extra":
                (capture / "foreign.json").write_bytes(b"{}")
            else:
                selected.write_bytes(b'{"schemaVersion":1,' + packets[selected][1:])
            with self.subTest(mutation=mutation), self.assertRaises(checks.evidence.ConformanceError):
                checks.original_inspection_literal_proofs(run, inputs, manifest, ingested)
            self.assertFalse(receipt_path.exists())
        restore()
        wrong = {**ingested, "proofs": dict(ingested["proofs"])}
        wrong["proofs"][next(iter(wrong["proofs"]))] = "f" * 64
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
            checks.original_inspection_literal_proofs(run, inputs, manifest, wrong)
        self.assertFalse(receipt_path.exists())

    def test_original_literal_inspection_context_is_exact_and_never_created_for_discovery(self):
        factory = getattr(checks, "original_inspection_literal_scenarios", None)
        self.assertTrue(callable(factory), "Inspection context must be independently allocated per execution.")
        scenario, = factory()
        (self.directory / "stores").mkdir()
        (self.directory / "runtime-owner.json").write_bytes(b"{}")
        commands = []
        def execute(args, **options):
            commands.append(args)
            return SimpleNamespace(exit_code=0)
        run = SimpleNamespace(root=self.directory, command=execute)
        assembly = self.directory / "Hoard.Architecture.Tests.dll"
        for purpose in ("discovery", "execution"):
            attempt = str(uuid.uuid4())
            manifest = {
                "runId": str(uuid.uuid4()), "attemptId": attempt, "purpose": purpose, "inputSha256": "a" * 64,
                "expected": [{"testIdentity": identity, "fullyQualifiedName": identity} for identity in scenario[1]]}
            checks.runtime_command(run, assembly, manifest, inspection_literals=True)
            context = self.directory / "stores" / ("inspection-context-" + attempt + ".json")
            if purpose == "discovery":
                self.assertFalse(context.exists())
            else:
                actual = json.loads(context.read_bytes())
                self.assertEqual(actual["runId"], manifest["runId"])
                self.assertEqual(actual["attemptId"], attempt)
                self.assertEqual(actual["inputsSha256"], manifest["inputSha256"])
                self.assertEqual(actual["cases"], {identity: {} for identity in scenario[1]})
                self.assertEqual(Path(actual["outputDirectory"]),
                                 self.directory / "stores" / ("original-inspection-" + attempt))
                settings = ET.parse(self.directory / "stores" / ("settings-" + attempt + ".runsettings"))
                self.assertEqual(settings.findtext("./RunConfiguration/EnvironmentVariables/HOARD_INSPECTION_CONTEXT"),
                                 str(context))
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
            checks.runtime_command(run, assembly, {**manifest, "attemptId": str(uuid.uuid4()),
                                                   "expected": manifest["expected"][:-1]}, inspection_literals=True)
        self.assertEqual(len(commands), 2)

    def test_prepared_inspection_receipts_bind_exact_file_assignments_to_current_configuration_and_runtime(self):
        self.assertTrue(callable(getattr(checks, "original_inspection_prepared_proofs", None)),
                        "Actual prepared source packets need configuration-bound independent parent admission.")
        identities = tuple(identity for identity in checks.ORIGINAL_INSPECTION_WITNESSES
                           if identity not in checks.ORIGINAL_INSPECTION_LITERAL_WITNESSES)
        for name in ("stores", "proofs", "feed", "feed/candidate"):
            (self.directory / name).mkdir()
        config = self.directory / "stores/candidate.NuGet.Config"
        config.write_bytes(checks.evidence.synthetic_nuget_configuration(self.directory / "feed/candidate"))
        selected = {identity: {str(self.directory / ("input-" + str(index) + ".xml")): str(index + 1) * 64}
                    for index, identity in enumerate(identities)}
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()), "mode": "diagnostic",
            "configurationSha256": checks.evidence.configuration_fingerprint(
                checks.evidence.verify_synthetic_source_mapping(
                    self.directory, "stores/candidate.NuGet.Config", "feed/candidate"),
                inspection_inputs=selected)}
        manifest = {**inputs, "attemptId": str(uuid.uuid4()), "inputSha256": checks.evidence.digest(inputs),
                    "expected": [{"testIdentity": identity} for identity in identities]}
        witnesses = [{
            "testIdentity": identity, "executionId": str(uuid.uuid4()), "proofSha256": str(index + 1) * 64,
            "status": "Passed", "bindingId": "none"} for index, identity in enumerate(identities)]
        ingested = {"diagnosticCode": "None", "attemptId": manifest["attemptId"], "witnesses": witnesses,
                    "proofs": {f'proof-{row["executionId"]}.json': row["proofSha256"] for row in witnesses}}
        capture = self.directory / "stores" / ("original-inspection-" + manifest["attemptId"])
        capture.mkdir()
        packets = {}
        for identity in identities:
            path = capture / ("inspection-" + hashlib.sha256(identity.encode()).hexdigest() + ".json")
            packets[path] = checks.evidence.canonical_bytes({
                "schemaVersion": 1, "qualification": False, "runId": inputs["runId"], "attemptId": manifest["attemptId"],
                "testIdentity": identity, "inputsSha256": checks.evidence.digest(inputs),
                "files": {hashlib.sha256(name.encode()).hexdigest(): hashed for name, hashed in selected[identity].items()}})
            path.write_bytes(packets[path])
        run = SimpleNamespace(root=self.directory)
        result = checks.original_inspection_prepared_proofs(run, inputs, manifest, ingested, selected)
        receipt = self.directory / ("proofs/original-inspection-prepared-" + manifest["attemptId"] + ".json")
        self.assertEqual(result["sourceExecutions"], 3)
        self.assertEqual(result["inspectionProofsSha256"], checks.evidence.file_sha256(receipt))
        receipt.unlink()
        selected_packet = next(iter(packets))
        for files in ({}, {"f" * 64: "e" * 64},
                      {next(iter(json.loads(packets[selected_packet])["files"])): "f" * 64}):
            selected_packet.write_bytes(checks.evidence.canonical_bytes(
                checks.evidence.load_json(packets[selected_packet]) | {"files": files}))
            with self.subTest(files=files), self.assertRaises(checks.evidence.ConformanceError):
                checks.original_inspection_prepared_proofs(run, inputs, manifest, ingested, selected)
            self.assertFalse(receipt.exists())
        selected_packet.write_bytes(packets[selected_packet])
        changed = {identity: dict(files) for identity, files in selected.items()}
        changed[identities[0]][next(iter(changed[identities[0]]))] = "f" * 64
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            checks.original_inspection_prepared_proofs(run, inputs, manifest, ingested, changed)
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.original_inspection_prepared_proofs(run, inputs, manifest, ingested, {})
        self.assertFalse(receipt.exists())

    def test_prepared_inspection_runtime_allocates_exact_execution_context_without_discovery_capture(self):
        (self.directory / "stores").mkdir()
        (self.directory / "runtime-owner.json").write_bytes(b"{}")
        identities = tuple(identity for identity in checks.ORIGINAL_INSPECTION_WITNESSES
                           if identity not in checks.ORIGINAL_INSPECTION_LITERAL_WITNESSES)
        configurations = {family: self.directory / (family + ".json") for family in ("metadata", "artifacts")}
        for path in configurations.values():
            path.write_bytes(b"{}")
        cases = {}
        for identity in identities:
            path = configurations["metadata" if ".MetadataBoundaryTests." in identity else "artifacts"]
            cases[identity] = {str(path): checks.evidence.file_sha256(path)}
        commands = []
        def execute(arguments, **options):
            commands.append(arguments)
            return SimpleNamespace(exit_code=0)
        run = SimpleNamespace(root=self.directory, command=execute)
        assembly = self.directory / "Hoard.Architecture.Tests.dll"
        for purpose in ("discovery", "execution"):
            manifest = {
                "runId": str(uuid.uuid4()), "attemptId": str(uuid.uuid4()), "purpose": purpose,
                "inputSha256": "a" * 64,
                "expected": [{"testIdentity": identity, "fullyQualifiedName": identity} for identity in identities]}
            checks.runtime_command(run, assembly, manifest,
                                   inspection_cases=cases, inspection_configurations=configurations)
            context = self.directory / "stores" / ("inspection-context-" + manifest["attemptId"] + ".json")
            settings = ET.parse(self.directory / "stores" / ("settings-" + manifest["attemptId"] + ".runsettings"))
            if purpose == "discovery":
                self.assertFalse(context.exists())
                self.assertIsNone(settings.find("./RunConfiguration/EnvironmentVariables"))
            else:
                self.assertEqual(json.loads(context.read_bytes())["cases"], cases)
                for family, variable in (("metadata", "HOARD_METADATA_BOUNDARIES"), ("artifacts", "HOARD_ARTIFACT_BOUNDARIES")):
                    self.assertEqual(settings.findtext("./RunConfiguration/EnvironmentVariables/" + variable),
                                     str(configurations[family]))
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.runtime_command(run, assembly, {**manifest, "attemptId": str(uuid.uuid4())},
                                   inspection_cases=cases, inspection_configurations=configurations, inspection_literals=True)
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.runtime_command(run, assembly, {**manifest, "attemptId": str(uuid.uuid4())},
                                   inspection_cases=cases, inspection_configurations={"metadata": configurations["metadata"]})
        self.assertEqual(len(commands), 2)

    def test_prepared_inspection_dispatch_checks_input_fingerprint_before_selecting_the_real_assembly(self):
        scenario, = checks.original_inspection_prepared_scenarios()
        candidate = self.directory / "current"
        assembly = candidate / checks.ARCHITECTURE_TESTS / "bin/Release/net10.0/Hoard.Architecture.Tests.dll"
        (self.directory / "stores").mkdir()
        (self.directory / "feed/candidate").mkdir(parents=True)
        (self.directory / "stores/candidate.NuGet.Config").write_bytes(
            checks.evidence.synthetic_nuget_configuration(self.directory / "feed/candidate"))
        selected = {identity: {str(self.directory / "input.xml"): "a" * 64} for identity in scenario[1]}
        configurations = {category: self.directory / (category + ".json") for category in ("metadata", "artifacts")}
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()), "mode": "diagnostic",
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "b" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "c" * 64}],
            "configurationSha256": checks.evidence.configuration_fingerprint(
                checks.evidence.verify_synthetic_source_mapping(
                    self.directory, "stores/candidate.NuGet.Config", "feed/candidate"), inspection_inputs=selected)}
        run = SimpleNamespace(root=self.directory)
        options = {"inspection_cases": selected, "inspection_configurations": configurations}
        with patch.object(checks, "runtime_command", side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(run, inputs, candidate, scenario, **options)
        self.assertEqual(launch.call_args.args[1], assembly)
        self.assertEqual(launch.call_args.kwargs, options)
        with patch.object(checks, "runtime_command") as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.test_attempt(run, {**inputs, "configurationSha256": "d" * 64}, candidate, scenario, **options)
        launch.assert_not_called()

    def test_frozen_metadata_runtime_keeps_marker_and_replaces_only_current_platform_images(self):
        candidate = self.directory / "candidate"
        prefix = "retained/bin/Release/net10.0/"
        images = {
            "RetainedMarker.dll": b"explicit-old-marker-model",
            "RetainedMarker.deps.json": b"{}", "RetainedMarker.runtimeconfig.json": b"{}",
            **{name: b"old-" + name.encode() for name in (
                "Hoard.Abstractions.dll", "Hoard.Core.dll", "Hoard.Hosting.dll")}}
        for name, raw in images.items():
            target = self.directory / "stores/metadata-marker" / prefix / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            if name.startswith("Hoard."):
                current = candidate / checks.METADATA_PACKAGE_CONSUMER / "bin/Release/net10.0" / name
                current.parent.mkdir(parents=True, exist_ok=True)
                current.write_bytes(b"current-" + name.encode())
        sealed = {"entries": [{"id": "metadata-marker", "binaries": {
            prefix + name: hashlib.sha256(raw).hexdigest() for name, raw in images.items()}}]}
        with patch.object(checks.baselines, "verify_prepared_baselines", return_value=sealed):
            runtime = checks.stage_metadata_binary_runtime(SimpleNamespace(root=self.directory), candidate, "a" * 64)
        for name, raw in images.items():
            self.assertEqual((runtime / name).read_bytes(), b"current-" + name.encode() if name.startswith("Hoard.") else raw)
            self.assertEqual((runtime / name).stat().st_mode & 0o777, 0o400)
            self.assertEqual((self.directory / "stores/metadata-marker" / prefix / name).read_bytes(), raw)

    def test_prepared_inspection_configuration_uses_the_sealed_family_image_and_rejects_changed_bytes(self):
        candidate = self.directory / "current"
        relative = "src/Hoard.Abstractions/bin/Release/net10.0/Hoard.Abstractions.dll"
        current = candidate / relative
        current.parent.mkdir(parents=True)
        current.write_bytes(b"current")
        entries = []
        for family in ("metadata", "artifact"):
            image = self.directory / "stores" / (family + "-marker") / relative
            image.parent.mkdir(parents=True)
            image.write_bytes(family.encode())
            entries.append({"id": family + "-marker", "binaries": {relative: checks.evidence.file_sha256(image)}})
        run = SimpleNamespace(root=self.directory)
        with patch.object(checks.baselines, "verify_prepared_baselines", return_value={"entries": entries}) as verify, \
                patch.object(checks, "prepared_inspection_graphs", return_value=[]) as graphs:
            configurations = checks.prepare_inspection_configurations(run, candidate, "a" * 64)
        verify.assert_called_once_with(self.directory, "a" * 64)
        self.assertEqual(graphs.call_count, 2)
        for category, marker in (("metadata", "metadata"), ("artifacts", "artifact")):
            value = checks.evidence.load_json(configurations[category].read_bytes())
            self.assertEqual(value["baselineAbstractions"],
                             str(self.directory / "stores" / (marker + "-marker") / relative))
            self.assertEqual(value["currentAbstractions"], str(current))
        (self.directory / "stores/metadata-marker" / relative).write_bytes(b"changed")
        with patch.object(checks.baselines, "verify_prepared_baselines", return_value={"entries": entries}), \
                patch.object(checks, "prepared_inspection_graphs"):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.prepare_inspection_configurations(run, candidate, "a" * 64)

    def test_inspection_reference_roots_come_from_the_resolved_tool_not_graph_supplied_labels(self):
        installed = self.directory / "dotnet"
        installed.mkdir()
        binary = installed / "dotnet"
        binary.touch()
        expected = {name: installed / "packs" / (name + ".Ref")
                    for name in ("Microsoft.NETCore.App", "Microsoft.AspNetCore.App")}
        for root in expected.values():
            root.mkdir(parents=True)
        with patch.object(checks.shutil, "which", return_value=str(binary)):
            self.assertEqual(checks.inspection_reference_roots(), expected)
            next(iter(expected.values())).rmdir()
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
                checks.inspection_reference_roots()
        with patch.object(checks.shutil, "which", return_value=None):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
                checks.inspection_reference_roots()

    def test_missing_inspection_projects_use_locked_builds_without_extending_the_package_feed(self):
        (self.directory / "proofs").mkdir()
        candidate = self.directory / "current"
        feed, config = self.directory / "feed", self.directory / "candidate.NuGet.Config"
        receipts = []
        def prepare(project, selected, archives, feed_id):
            self.assertEqual((selected, archives, feed_id), (candidate, feed, "candidate"))
            receipt = {"project": project.relative_to(candidate).as_posix()}
            receipts.append(receipt)
            return project.parent / "obj/selected.packages.lock.json", receipt
        with patch.object(checks, "prepare_project_lock", side_effect=prepare), \
                patch.object(checks, "build") as build, patch.object(checks, "verify_project_lock") as verify:
            observed = checks.build_inspection_projects(SimpleNamespace(root=self.directory), candidate, config, feed)
        self.assertEqual(observed, tuple(receipts))
        self.assertEqual({row["project"] for row in observed}, {
            "src/Hoard.Application/Hoard.Application.csproj",
            *(f"tests/fixtures/{family}/{name}/{name}.csproj"
              for family in ("metadata", "artifacts") for name in ("Consumer", "BoundaryLeak"))})
        for call in build.call_args_list:
            self.assertEqual(call.kwargs, {"lock": call.args[1].parent / "obj/selected.packages.lock.json"})
            self.assertEqual(call.args[2], config)
        self.assertEqual(verify.call_count, len(observed))
        self.assertEqual({json.loads(path.read_bytes())["project"] for path in
                          (self.directory / "proofs").glob("inspection-*-lock-derivation.json")},
                         {row["project"] for row in observed})

    def test_inspection_graph_uses_explicit_resolved_outputs_without_legacy_raw_execution(self):
        import foundation_evidence as foundation
        parent = self.directory / "Parent.csproj"
        child = self.directory / "Child.csproj"
        parent.write_text('<Project><ItemGroup><ProjectReference Include="Child.csproj"/></ItemGroup></Project>')
        child.write_text("<Project/>")
        calls = []
        def resolve(project):
            calls.append(project)
            return {
                "Properties": {"TargetPath": str(self.directory / (project.stem + ".Actual.dll")),
                               "ProjectAssetsFile": str(self.directory / (project.stem + ".assets.json"))},
                "Items": {"ReferencePath": [{"Identity": str(self.directory / "Reference.dll")}],
                          "Compile": [{"Identity": "Feature.cs", "FullPath": str(self.directory / "Feature.cs")}]}}
        with patch.object(foundation, "run", side_effect=AssertionError("Legacy raw execution must not run.")):
            graph = foundation.inspection_graph([parent], {"Parent": "Core", "Child": "Abstractions"}, resolve=resolve)
        self.assertEqual(calls, [parent, child])
        for row in graph["projects"]:
            self.assertEqual(row["assembly"], str(self.directory / (row["id"] + ".Actual.dll")))
            self.assertEqual(row["assets"], str(self.directory / (row["id"] + ".assets.json")))
            self.assertEqual(row["sources"], [str(self.directory / "Feature.cs")])

    def test_owned_inspection_resolution_uses_a_bounded_projecting_child_and_actual_outputs(self):
        self.assertTrue(callable(getattr(checks, "resolve_inspection_project", None)),
                        "Prepared graphs must not invoke the predecessor raw-output runner.")
        project = self.directory / "Actual.csproj"
        project.write_text("<Project/>")
        (self.directory / "stores").mkdir()
        calls = []
        selected = {
            "Properties": {"TargetPath": str(self.directory / "Actual.Output.dll"),
                           "ProjectAssetsFile": str(self.directory / "actual.assets.json")},
            "Items": {"ReferencePath": [{"Identity": str(self.directory / "Reference.dll"),
                                         "NuGetPackageId": "Example.Package"}],
                      "Compile": [{"Identity": "Feature.cs", "FullPath": str(self.directory / "Feature.cs")}]}}
        def command(arguments, **options):
            calls.append((arguments, options))
            output = Path(arguments[arguments.index("--inspection-output") + 1])
            output.write_bytes(checks.evidence.canonical_bytes({
                "schemaVersion": 1, "project": str(project),
                "projectSha256": checks.evidence.file_sha256(project), **selected}))
            return SimpleNamespace(exit_code=0, events=())
        run = SimpleNamespace(root=self.directory, command=command)
        self.assertEqual(checks.resolve_inspection_project(run, project), selected)
        arguments, options = calls[0]
        self.assertEqual(arguments[arguments.index("--inspection-project") + 1], str(project))
        self.assertEqual(options["timeout"], 120)
        self.assertEqual(options["kind"], "build")
        self.assertTrue(Path(arguments[arguments.index("--inspection-output") + 1]).is_relative_to(self.directory / "stores"))
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.resolve_inspection_project(run, ROOT / "src/Hoard.Core/Hoard.Core.csproj")
        linked = self.directory / "Linked.csproj"
        linked.symlink_to(project)
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.resolve_inspection_project(run, linked)
        self.assertEqual(len(calls), 1)
        for mutation in (
                {"schemaVersion": True}, {"projectSha256": "f" * 64}, {"project": str(linked)},
                {"unknown": "private-canary"},
                {"Properties": {**selected["Properties"], "TargetPath": str(ROOT / "foreign.dll")}},
                {"Items": {**selected["Items"], "ReferencePath": [
                    {**selected["Items"]["ReferencePath"][0], "UnusedMetadata": "private-canary"}]}}):
            def invalid(arguments, **options):
                command(arguments, **options)
                output = Path(arguments[arguments.index("--inspection-output") + 1])
                output.write_bytes(checks.evidence.canonical_bytes(
                    checks.evidence.load_json(output.read_bytes()) | mutation))
                return SimpleNamespace(exit_code=0, events=())
            with self.subTest(mutation=mutation), self.assertRaises(checks.evidence.ConformanceError):
                checks.resolve_inspection_project(SimpleNamespace(root=self.directory, command=invalid), project)
        def changed(arguments, **options):
            result = command(arguments, **options)
            project.write_text("<Project changed='true'/>")
            return result
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            checks.resolve_inspection_project(SimpleNamespace(root=self.directory, command=changed), project)

    def test_inspection_probe_projects_only_read_metadata_and_rejects_changed_or_malformed_inputs(self):
        self.assertTrue(callable(getattr(checks, "probe_inspection_project", None)),
                        "MSBuild metadata must be bounded transient input, never retained raw output.")
        project = self.directory / "Actual.csproj"
        project.write_text("<Project/>")
        output = self.directory / "resolution.json"
        raw = {
            "Properties": {"TargetPath": str(self.directory / "Actual.Output.dll"),
                           "ProjectAssetsFile": str(self.directory / "actual.assets.json")},
            "Items": {"ReferencePath": [{"Identity": str(self.directory / "Reference.dll"),
                                        "NuGetPackageId": "Example.Package", "UnusedMetadata": "private-canary"}],
                      "Compile": [{"Identity": "Feature.cs", "FullPath": str(self.directory / "Feature.cs"),
                                   "UnusedMetadata": "private-canary"}]}}
        with patch.object(checks, "capture_control", return_value=(0, checks.evidence.canonical_bytes(raw))) as capture:
            checks.probe_inspection_project(project, output)
        self.assertNotIn(b"private-canary", output.read_bytes())
        selected = checks.evidence.load_json(output.read_bytes())
        self.assertEqual(selected["Properties"], raw["Properties"])
        self.assertEqual(selected["Items"]["ReferencePath"], [{
            "Identity": str(self.directory / "Reference.dll"), "NuGetPackageId": "Example.Package"}])
        self.assertEqual(selected["projectSha256"], checks.evidence.file_sha256(project))
        arguments = capture.call_args.args[0]
        self.assertIn("-getProperty:TargetPath,ProjectAssetsFile", arguments)
        self.assertIn("-getItem:ReferencePath,Compile", arguments)
        self.assertEqual(capture.call_args.kwargs["limit"], 1024 * 1024)
        self.assertEqual(capture.call_args.kwargs["timeout"], 110)
        output.unlink()
        malformed = [
            b'{"Properties":{},"Properties":{},"Items":{}}',
            checks.evidence.canonical_bytes({**raw, "Properties": {**raw["Properties"], "TargetPath": "../guessed.dll"}}),
            checks.evidence.canonical_bytes({**raw, "Items": {**raw["Items"], "ReferencePath": []}}),
            checks.evidence.canonical_bytes({**raw, "Items": {**raw["Items"], "Compile": [{
                "Identity": "Feature.cs", "FullPath": str(self.directory / "Different.cs")}]}})]
        for data in malformed:
            with self.subTest(data=data), patch.object(checks, "capture_control", return_value=(0, data)):
                with self.assertRaises(checks.evidence.ConformanceError):
                    checks.probe_inspection_project(project, output)
            self.assertFalse(output.exists())
        with patch.object(checks, "capture_control", return_value=(1, b"private-canary")):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "CommandFailed"):
                checks.probe_inspection_project(project, output)
        self.assertFalse(output.exists())
        def changed(*arguments, **options):
            project.write_text("<Project changed='true'/>")
            return 0, checks.evidence.canonical_bytes(raw)
        with patch.object(checks, "capture_control", side_effect=changed):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.probe_inspection_project(project, output)
        self.assertFalse(output.exists())

    def test_prepared_graphs_reuse_original_recipes_and_resolve_each_actual_project_once(self):
        self.assertTrue(callable(getattr(checks, "prepared_inspection_graphs", None)),
                        "Prepared metadata/artifact graphs need the original recipes without raw orchestration.")
        import artifact_evidence as artifacts
        import foundation_evidence as foundation
        import metadata_evidence as metadata
        candidate = self.directory / "current"
        for name, dependency in (("Abstractions", None), ("Core", "Abstractions"),
                                 ("Hosting", "Core"), ("Application", "Hosting")):
            project = candidate / f"src/Hoard.{name}/Hoard.{name}.csproj"
            project.parent.mkdir(parents=True)
            project.write_text("<Project/>" if dependency is None else
                               f'<Project><ItemGroup><ProjectReference Include="../Hoard.{dependency}/Hoard.{dependency}.csproj"/>'
                               "</ItemGroup></Project>")
        for family, names in (
                ("metadata", ("Sqlite", "Memory", "HostAdapters", "Consumer", "CrashRunner", "BoundaryLeak")),
                ("artifacts", ("Local", "ObjectSemantics", "HostAdapters", "Consumer", "CrashRunner",
                               "TransferRunner", "BoundaryLeak"))):
            for name in names:
                project = candidate / f"tests/fixtures/{family}/{name}/{name}.csproj"
                project.parent.mkdir(parents=True)
                project.write_text("<Project/>")
        calls = []
        def resolve(run, project):
            calls.append(project)
            return {"Properties": {
                "TargetPath": str(project.parent / (project.stem + ".Actual.dll")),
                "ProjectAssetsFile": str(project.parent / "obj/actual.assets.json")},
                "Items": {"ReferencePath": [{"Identity": str(self.directory / "Reference.dll")}], "Compile": []}}
        with (patch.object(checks, "resolve_inspection_project", side_effect=resolve),
              patch.object(foundation, "run", side_effect=AssertionError("Raw predecessor runner must not execute.")),
              patch.object(metadata, "compatibility_cases", side_effect=AssertionError("Full legacy orchestration must not execute.")),
              patch.object(artifacts, "package_checks", side_effect=AssertionError("Full legacy orchestration must not execute."))):
            for family, expected in (
                    ("metadata", {"platform", "sqlite", "memory", "host-adapters", "consumer", "crash-runner", "boundary-leak"}),
                    ("artifacts", {"platform", "local", "object", "host-adapters", "consumer", "crash-runner",
                                   "transfer-runner", "boundary-leak"})):
                calls.clear()
                graphs = checks.prepared_inspection_graphs(SimpleNamespace(root=self.directory), candidate, family)
                self.assertEqual({graph["scanId"] for graph in graphs}, expected)
                projects = {Path(row["project"]) for graph in graphs for row in graph["projects"]}
                self.assertEqual(set(calls), projects)
                self.assertEqual(len(calls), len(projects))
                for graph in graphs:
                    for row in graph["projects"]:
                        self.assertEqual(row["assembly"], str(Path(row["project"]).parent / (row["id"] + ".Actual.dll")))
                        self.assertEqual(row["assets"], str(Path(row["project"]).parent / "obj/actual.assets.json"))
                self.assertEqual({row["id"] for row in next(graph for graph in graphs
                                                          if graph["scanId"] == "platform")["projects"]},
                                 {"Hoard.Abstractions", "Hoard.Core", "Hoard.Hosting", "Hoard.Application"})
            with self.assertRaises(checks.evidence.ConformanceError):
                checks.prepared_inspection_graphs(SimpleNamespace(root=self.directory), candidate, "unknown")

    def test_prepared_file_selection_matches_full_and_consumer_only_actual_read_sets(self):
        self.assertTrue(callable(getattr(checks, "inspection_file_inputs", None)),
                        "Source contexts require an independent exact input selection, not all graph files.")
        projects = {}
        graphs = []
        for scan in ("platform", "local", "object", "host-adapters", "consumer", "crash-runner",
                     "transfer-runner", "boundary-leak"):
            folder = self.directory / scan
            folder.mkdir()
            files = {}
            for name in ("project.csproj", "assembly.dll", "Reference.dll", "Features/Read/Feature.cs", "Ignored.cs"):
                path = folder / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
                files[name] = path
            cache = self.directory / "packages" / scan
            cache.mkdir(parents=True)
            nuspec = cache / "package.nuspec"
            nuspec.write_text("<package/>")
            assets = folder / "assets.json"
            assets.write_bytes(checks.evidence.canonical_bytes({
                "targets": {"net10.0": {scan + "/1.0.0": {}}},
                "libraries": {scan + "/1.0.0": {"type": "package", "path": scan}},
                "packageFolders": {str(self.directory / "packages") + "/": {}}}))
            row = {"id": scan, "project": str(files["project.csproj"]), "assembly": str(files["assembly.dll"]),
                   "assets": str(assets), "references": [{"Identity": str(files["Reference.dll"])}],
                   "sources": [str(files["Features/Read/Feature.cs"]), str(files["Ignored.cs"])]}
            graphs.append({"scanId": scan, "projects": [row], "ownership": {}})
            projects[scan] = {**files, "assets.json": assets, "nuspec": nuspec}
        baseline, current = self.directory / "old.dll", self.directory / "new.dll"
        baseline.write_bytes(b"old")
        current.write_bytes(b"new")
        configuration = self.directory / "artifacts.json"
        configuration.write_bytes(checks.evidence.canonical_bytes({
            "graphs": graphs, "baselineAbstractions": str(baseline), "currentAbstractions": str(current)}))
        prefix = "Hoard.Architecture.Tests.ArtifactBoundaryTests."
        full = prefix + "Prepared_artifact_packages_preserve_independence_and_existing_public_members"
        consumer = prefix + "Prepared_artifact_consumer_bodies_are_provider_neutral_and_object_mechanisms_do_not_rename"
        all_files = checks.inspection_file_inputs(self.directory, configuration, full, reference_roots={})
        expected = {str(configuration), str(baseline), str(current)}
        expected.update(str(path) for files in projects.values() for name, path in files.items() if name != "Ignored.cs")
        self.assertEqual(set(all_files), expected)
        for path, hashed in all_files.items():
            self.assertEqual(hashed, checks.evidence.file_sha256(Path(path)))
        selected = checks.inspection_file_inputs(self.directory, configuration, consumer, reference_roots={})
        expected = {str(configuration)}
        for scan in ("consumer", "boundary-leak", "local", "object"):
            expected.update(str(path) for name, path in projects[scan].items()
                            if name != "Ignored.cs" and (scan == "boundary-leak" or name not in ("project.csproj", "nuspec")))
        self.assertEqual(set(selected), expected)
        with self.assertRaises(TypeError):
            selected["foreign"] = "f" * 64
        projects["consumer"]["project.csproj"].unlink()
        self.assertEqual(checks.inspection_file_inputs(
            self.directory, configuration, consumer, reference_roots={}), selected)
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.inspection_file_inputs(self.directory, configuration, full, reference_roots={})
        with self.assertRaises(checks.evidence.ConformanceError):
            checks.inspection_file_inputs(self.directory, configuration, "foreign", reference_roots={})

    def test_prepared_file_selection_accepts_only_explicit_matching_sdk_reference_roots_and_bounds(self):
        self.assertTrue(callable(getattr(checks, "inspection_file_inputs", None)),
                        "External PE inputs require an independently trusted framework root, not arbitrary paths.")
        for name, data in (("project.csproj", b"<Project/>"), ("assembly.dll", b"assembly"),
                           ("assets.json", b'{"targets":{"net10.0":{}}}')):
            (self.directory / name).write_bytes(data)
        configuration = self.directory / "artifacts.json"
        identity = ("Hoard.Architecture.Tests.ArtifactBoundaryTests."
                    "Prepared_artifact_consumer_bodies_are_provider_neutral_and_object_mechanisms_do_not_rename")
        with tempfile.TemporaryDirectory(dir=ROOT / ".foundation", prefix="sdk-reference-") as temporary:
            framework = "Microsoft.NETCore.App"
            trusted = Path(temporary) / (framework + ".Ref")
            reference = trusted / "10.0.7/ref/net10.0/Reference.dll"
            reference.parent.mkdir(parents=True)
            reference.write_bytes(b"reference")
            row = {
                "id": "source", "project": str(self.directory / "project.csproj"),
                "assembly": str(self.directory / "assembly.dll"), "assets": str(self.directory / "assets.json"),
                "sources": [], "references": [{"Identity": str(reference),
                    "FrameworkReferenceName": framework, "NuGetPackageId": framework + ".Ref"}]}
            def configure(selected=row):
                configuration.write_bytes(checks.evidence.canonical_bytes({
                    "graphs": [{"scanId": scan, "projects": [selected], "ownership": {}}
                               for scan in ("platform", "local", "object", "host-adapters", "consumer",
                                            "crash-runner", "transfer-runner", "boundary-leak")],
                    "baselineAbstractions": "unused", "currentAbstractions": "unused"}))
            configure()
            files = checks.inspection_file_inputs(
                self.directory, configuration, identity, reference_roots={framework: trusted})
            self.assertEqual(files[str(reference)], hashlib.sha256(b"reference").hexdigest())
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "OwnershipInvalid"):
                checks.inspection_file_inputs(self.directory, configuration, identity, reference_roots={})
            for mutation in (
                    {"NuGetPackageId": "Provider.Pretending.Framework"},
                    {"FrameworkReferenceName": "Microsoft.AspNetCore.App"},
                    {"Identity": str(Path(temporary) / "foreign.dll")}):
                configure({**row, "references": [{**row["references"][0], **mutation}]})
                with self.subTest(mutation=mutation), self.assertRaisesRegex(
                        checks.evidence.ConformanceError, "OwnershipInvalid"):
                    checks.inspection_file_inputs(
                        self.directory, configuration, identity, reference_roots={framework: trusted})
            configure()
            with reference.open("wb") as destination:
                destination.truncate(65 * 1024 * 1024)
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "OutputLimitExceeded"):
                checks.inspection_file_inputs(
                    self.directory, configuration, identity, reference_roots={framework: trusted})

    @staticmethod
    def original_crash_fixture(barrier):
        run_id = str(uuid.uuid4())
        receipt_id = str(uuid.uuid4())
        content = hashlib.sha256(bytes((index * 17 + 11) % 256 for index in range(256)) * 4096).hexdigest()
        control = b"acknowledged independent control before crash"
        state = checks.evidence.canonical_bytes({
            "Run": run_id, "Barrier": barrier, "TargetDigest": content, "TargetLength": 1048576,
            "Control": {"Digest": hashlib.sha256(control).hexdigest(), "Length": len(control)},
            "AcknowledgedReceipt": receipt_id if barrier == "B3" else None})
        recovered = {
            "eventName": "recovered", "provider": "local", "qualification": False,
            "pid": 43, "runId": run_id, "barrier": barrier,
            **{key: True for key in ("controlReadback", "controlReceipt", "exactReceipt",
                                     "contentReadback", "ownerFenced", "noDuplicateEffect")},
            "reconstructed": barrier in ("B0", "B1"),
            "reclamation": {"D0": "Pending", "D1": "Reclaimed"}.get(barrier, "NotApplicable"),
            "contentSha256": content, "contentLength": 1048576,
            "controlSha256": hashlib.sha256(control).hexdigest(), "controlLength": len(control),
            "outcome": "Removed" if barrier.startswith("D") else "Published", "receiptId": receipt_id}
        return {
            "provider": "local", "qualification": False, "runId": run_id, "barrier": barrier, "signal": 9,
            "parentPid": 41, "killedPid": 42, "killedExitCode": 137, "recoveredPid": 43, "reopenedExitCode": 0,
            "barrierProof": {"eventName": "barrier", "pid": 42, "runId": run_id, "barrier": barrier,
                             "stateSha256": hashlib.sha256(state).hexdigest(), "acknowledged": barrier == "B3"},
            "recovery": recovered}, state

    def test_original_crash_packets_require_actual_state_exit_and_fresh_readback_correspondence(self):
        import conformance_sources as sources
        self.assertTrue(callable(getattr(sources, "admit_original_artifact_crash", None)),
                        "Original process wrappers need independently admitted producer/state packets, not only green VSTest.")
        self.assertIs(checks.admit_original_artifact_crash, sources.admit_original_artifact_crash)
        for barrier in ("B0", "B1", "B2", "B3", "D0", "D1"):
            original, state = self.original_crash_fixture(barrier)
            checks.admit_original_artifact_crash(original, state, barrier)
            for change in (
                    {"provider": "object"}, {"qualification": True}, {"runId": str(uuid.uuid4())},
                    {"runId": "not-a-uuid"}, {"signal": True}, {"parentPid": True}, {"killedPid": True}, {"recoveredPid": True},
                    {"killedExitCode": 1}, {"reopenedExitCode": True}, {"recoveredPid": 42},
                    {"parentPid": 42}, {"parentPid": 2147483648}, {"recoveredPid": 2147483648}, {"extra": True},
                    *({"barrierProof": original["barrierProof"] | item} for item in (
                        {"stateSha256": "0" * 64}, {"pid": 43}, {"runId": str(uuid.uuid4())},
                        {"acknowledged": barrier != "B3"}, {"extra": True})),
                    *({"recovery": original["recovery"] | item} for item in (
                        {"contentReadback": False}, {"noDuplicateEffect": False}, {"ownerFenced": False},
                        {"contentSha256": "0" * 64}, {"controlLength": 0}, {"pid": True},
                        {"runId": str(uuid.uuid4())}, {"receiptId": ""}, {"extra": True}))):
                with self.subTest(barrier=barrier, change=change), self.assertRaisesRegex(
                        checks.evidence.ConformanceError, "ProofMismatch"):
                    checks.admit_original_artifact_crash(original | change, state, barrier)
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_original_artifact_crash(original, state + b" ", barrier)
            if barrier == "B3":
                altered = checks.evidence.canonical_bytes(
                    checks.evidence.load_json(state) | {"AcknowledgedReceipt": str(uuid.uuid4())})
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                    checks.admit_original_artifact_crash(original | {
                        "barrierProof": original["barrierProof"] | {"stateSha256": hashlib.sha256(altered).hexdigest()}},
                        altered, barrier)

    @staticmethod
    def original_retention_fixture(provider, scenario):
        run_id = str(uuid.uuid4())
        return {
            "qualification": False, "durableCrashProof": False, "provider": provider, "scenario": scenario,
            "runId": run_id, "parentPid": 41, "killedPid": 42, "killedExitCode": 137,
            "observations": [{
                "eventName": "noncooperative", "phase": phase, "pid": 42, "runId": run_id,
                "provider": provider, "scenario": scenario, "durableCrashProof": False,
                "cleanup": "RetainedLiveOwnership",
                "callerCode": "Uncertain" if scenario == "native" else "CancelledBeforeCommit",
                "admissionCode": "CleanupIncomplete", "shutdownCode": "CleanupIncomplete",
                "enteredWorkers": 1, "workerPending": True, "borrowedStreamsIntact": True,
                "rootStillOwned": True, "readinessBlocked": True, "protectionRetained": scenario != "source",
            } for phase in ("contained", "inspected")]}

    def test_original_retained_child_packets_require_both_live_phases_and_actual_signal_exit(self):
        import conformance_sources as sources
        self.assertTrue(callable(getattr(sources, "admit_original_artifact_retention", None)),
                        "Original retained-child packets must not borrow unrelated controller diagnostics.")
        self.assertIs(checks.admit_original_artifact_retention, sources.admit_original_artifact_retention)
        for provider in ("local", "object"):
            for scenario in ("source", "destination", "native"):
                original = self.original_retention_fixture(provider, scenario)
                checks.admit_original_artifact_retention(original, provider, scenario)
                for change in (
                        {"provider": "foreign"}, {"scenario": "foreign"}, {"runId": str(uuid.uuid4())},
                        {"qualification": True}, {"durableCrashProof": True}, {"parentPid": True},
                        {"parentPid": 42}, {"killedPid": True}, {"killedExitCode": 1}, {"extra": True},
                        {"observations": original["observations"][:1]},
                        {"observations": original["observations"][::-1]},
                        {"observations": [original["observations"][0], original["observations"][1] | {
                            "workerPending": False}]}):
                    with self.subTest(provider=provider, scenario=scenario, change=change), self.assertRaisesRegex(
                            checks.evidence.ConformanceError, "ProofMismatch"):
                        checks.admit_original_artifact_retention(original | change, provider, scenario)

    def test_original_external_packets_are_linked_to_exact_runtime_executions_without_session_claims(self):
        import conformance_sources as native_sources
        self.assertTrue(callable(getattr(checks, "original_artifact_external_proofs", None)),
                        "Original controller producer packets must join the actual source execution before admission.")
        self.assertTrue(callable(getattr(native_sources, "artifact_original_child_sources", None)),
                        "Independent source admission must reconstruct every original crash and retained-child graph.")
        sources = checks.original_artifact_proof_sources()
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_bytes())
        expected = {name for case in frozen["entries"] if case["profileId"] == "artifacts"
                    for name in case["runtimeTests"] if name.startswith((
                        "Hoard.Artifacts.Tests.ArtifactCrashTests.",
                        "Hoard.Artifacts.Tests.ArtifactNonCooperativeChildTests.",
                        "Hoard.Artifacts.Tests.ArtifactTransferProofTests."))}
        self.assertEqual(set(sources), expected)
        run_id, group, attempt = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        inputs = {"runId": run_id, "invocationGroupId": group, "environment": {"runtime": "10.0.7"}}
        capture = self.directory / "stores" / ("original-artifact-" + attempt)
        capture.mkdir(parents=True)
        (self.directory / "proofs").mkdir()
        paths = {}
        for identity, (kind, provider, parameter) in sources.items():
            if kind == "crash":
                proof, state = self.original_crash_fixture(parameter)
                (capture / (parameter + "-state.json")).write_bytes(state)
                (capture / (parameter + "-recovery-errors.txt")).write_bytes(b"")
                path = capture / (parameter + ".json")
            elif kind == "retention":
                proof = self.original_retention_fixture(provider, parameter)
                path = capture / f"noncooperative-{provider}-{parameter}.json"
            else:
                proof = {"runId": run_id, "runtime": ".NET 10.0.7", "expectedSha256": "a" * 64}
                path = self.directory / f"proofs/artifact-transfers/transfer-{provider}-{parameter}/proof.json"
                path.parent.mkdir(parents=True)
            path.write_bytes(checks.evidence.canonical_bytes(proof))
            paths[identity] = path
        children = native_sources.artifact_original_child_sources(
            self.directory, inputs, attempt, namespace="artifact-transfers")
        self.assertEqual(len(children["observations"]), 12)
        self.assertEqual(len(children["sourceProofs"]), 24)
        for identity, hashes in children["observations"].items():
            self.assertEqual(hashes["producer"], checks.evidence.file_sha256(paths[identity]))
        with self.assertRaises(TypeError):
            children["observations"][next(iter(children["observations"]))]["producer"] = "0" * 64
        transfer_receipt = {
            "qualification": False, "mode": "artifact-transfers", "code": "None",
            "inputsSha256": checks.evidence.digest(inputs),
            "transfers": [{"provider": provider, "size": parameter, "controllerSha256": "c" * 64,
                           "producerSha256": "d" * 64, "childStartSha256": "e" * 64,
                           "proofSha256": checks.evidence.file_sha256(paths[identity])}
                          for identity, (kind, provider, parameter) in sources.items() if kind == "transfer"]}
        transfer_receipt_path = self.directory / "proofs/artifact-transfers.json"
        transfer_receipt_path.write_bytes(checks.evidence.canonical_bytes(transfer_receipt))
        identities = checks.original_artifact_external_scenarios()[0][1]
        witnesses = [{"testIdentity": identity, "executionId": str(uuid.uuid4()), "status": "Passed",
                      "proofSha256": hashlib.sha256(identity.encode()).hexdigest()} for identity in identities]
        observed = {"attemptId": attempt, "diagnosticCode": "None", "witnesses": witnesses,
                    "proofs": {f'proof-{row["executionId"]}.json': row["proofSha256"] for row in witnesses}}
        manifest = {"attemptId": attempt, "runId": run_id, "invocationGroupId": group,
                    "inputSha256": checks.evidence.digest(inputs),
                    "expected": [{"testIdentity": identity} for identity in identities]}
        with patch.object(checks.artifacts, "verify_transfer"), patch.object(
                checks.artifacts, "expected_transfer_hash", return_value="a" * 64):
            receipt = checks.original_artifact_external_proofs(SimpleNamespace(root=self.directory), inputs, manifest, observed)
            self.assertEqual(receipt["sourceExecutions"], 16)
            retained = checks.evidence.load_json((
                self.directory / f"proofs/original-artifact-external-{attempt}.json").read_bytes())
            self.assertEqual(receipt["externalProofsSha256"], checks.evidence.digest(retained))
            self.assertFalse(retained["qualification"])
            self.assertEqual(retained["inputsSha256"], checks.evidence.digest(inputs))
            self.assertEqual({row["testIdentity"] for row in retained["observations"]}, expected)
            for row in retained["observations"]:
                witness = next(witness for witness in witnesses if witness["testIdentity"] == row["testIdentity"])
                self.assertEqual((row["executionId"], row["runtimeProofSha256"]),
                                 (witness["executionId"], witness["proofSha256"]))
                self.assertEqual(row["sourceProofs"]["producer"], checks.evidence.file_sha256(paths[row["testIdentity"]]))
                self.assertNotIn("sessionOrigins", row)
            for mutation in ("execution", "runtime-proof", "status", "missing-file", "extra-file",
                             "transfer-run", "transfer-parent", "child-run", "child-alias", "recovery-errors"):
                with self.subTest(mutation=mutation), contextlib.ExitStack() as cleanup:
                    changed = [dict(row) for row in witnesses]
                    if mutation == "execution":
                        changed[0]["executionId"] = changed[1]["executionId"]
                    elif mutation == "runtime-proof":
                        changed[0]["proofSha256"] = "b" * 64
                    elif mutation == "status":
                        changed[0]["status"] = "Incomplete"
                    elif mutation == "missing-file":
                        path = paths[next(iter(sources))]
                        before = path.read_bytes()
                        path.unlink()
                        cleanup.callback(path.write_bytes, before)
                    elif mutation == "extra-file":
                        path = capture / "foreign.json"
                        path.write_bytes(b"{}")
                        cleanup.callback(path.unlink)
                    elif mutation == "transfer-run":
                        path = next(path for identity, path in paths.items() if "TransferProofTests" in identity)
                        before = path.read_bytes()
                        path.write_bytes(checks.evidence.canonical_bytes({"runId": str(uuid.uuid4())}))
                        cleanup.callback(path.write_bytes, before)
                    elif mutation in ("child-run", "child-alias"):
                        retained = [paths[identity] for identity, (kind, _, _) in sources.items() if kind == "retention"]
                        path = retained[0]
                        before = path.read_bytes()
                        body = checks.evidence.load_json(before)
                        identity = (run_id if mutation == "child-run" else
                                    checks.evidence.load_json(retained[1].read_bytes())["runId"])
                        body["runId"] = identity
                        for observation in body["observations"]:
                            observation["runId"] = identity
                        path.write_bytes(checks.evidence.canonical_bytes(body))
                        cleanup.callback(path.write_bytes, before)
                    elif mutation == "recovery-errors":
                        path = capture / "B0-recovery-errors.txt"
                        path.write_bytes(b"raw child diagnostics must not enter source proof retention")
                        cleanup.callback(path.write_bytes, b"")
                    else:
                        before = transfer_receipt_path.read_bytes()
                        transfer_receipt_path.write_bytes(checks.evidence.canonical_bytes(
                            transfer_receipt | {"inputsSha256": "0" * 64}))
                        cleanup.callback(transfer_receipt_path.write_bytes, before)
                    with self.assertRaises(checks.evidence.ConformanceError):
                        checks.original_artifact_external_proofs(
                            SimpleNamespace(root=self.directory), inputs, manifest, observed | {"witnesses": changed})
            from conformance_case_catalog import category_execution_partitions, category_runtime_cases
            pairs = category_execution_partitions("artifacts")["controller"]
            category_inputs = {**inputs, "profileId": "artifacts", "mode": "diagnostic"}
            category_attempt = str(uuid.uuid4())
            shutil.copytree(capture, capture.parent / ("original-artifact-" + category_attempt))
            transfer_receipt_path.write_bytes(checks.evidence.canonical_bytes({
                **transfer_receipt, "inputsSha256": checks.evidence.digest(category_inputs)}))
            category_manifest = {
                **manifest, "attemptId": category_attempt, "inputSha256": checks.evidence.digest(category_inputs),
                "expected": [{"testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
                              "bindingId": binding, "caseId": category_runtime_cases("artifacts", binding)[identity]}
                             for binding, identity in pairs]}
            by_identity = {row["testIdentity"]: row for row in witnesses}
            category_witnesses = [{**by_identity[identity], "bindingId": binding} for binding, identity in pairs]
            category_observed = {**observed, "attemptId": category_attempt, "witnesses": category_witnesses}
            options = {"category_scope": ("artifacts", "controller")}
            category_receipt = self.directory / f"proofs/original-artifact-external-{category_attempt}.json"
            for changed in (
                [{**category_witnesses[0], "bindingId": "foreign"}, *category_witnesses[1:]],
                category_witnesses[:-1],
            ):
                with self.assertRaises(checks.evidence.ConformanceError):
                    checks.original_artifact_external_proofs(
                        SimpleNamespace(root=self.directory), category_inputs, category_manifest,
                        {**category_observed, "witnesses": changed}, **options)
                self.assertFalse(category_receipt.exists())
            with self.assertRaises(checks.evidence.ConformanceError):
                checks.original_artifact_external_proofs(
                    SimpleNamespace(root=self.directory), category_inputs, category_manifest, category_observed, **options)
            shutil.copytree(self.directory / "proofs/artifact-transfers",
                            self.directory / "proofs/category-artifact-transfers")
            (self.directory / "proofs/category-artifact-transfers.json").write_bytes(
                checks.evidence.canonical_bytes({
                    **transfer_receipt, "inputsSha256": checks.evidence.digest(category_inputs)}))
            result = checks.original_artifact_external_proofs(
                SimpleNamespace(root=self.directory), category_inputs, category_manifest, category_observed, **options)
            self.assertEqual(result["sourceExecutions"], 16)
            self.assertEqual(result["externalProofsSha256"], checks.evidence.file_sha256(category_receipt))
            run = SimpleNamespace(root=self.directory)
            source_options = {**options, "result": SimpleNamespace(exit_code=0)}
            parent = self.directory / f"proofs/category-source-{category_attempt}.json"
            source_raw = category_receipt.read_bytes()
            source = json.loads(source_raw)
            for change in (
                    {"attemptId": str(uuid.uuid4())}, {"runId": str(uuid.uuid4())},
                    {"inputsSha256": "0" * 64}, {"qualification": True},
                    {"observations": [
                        {**source["observations"][0], "executionId": str(uuid.uuid4())},
                        *source["observations"][1:]]},
                    {"observations": [
                        {**source["observations"][0], "runtimeProofSha256": "0" * 64},
                        *source["observations"][1:]]},
                    {"observations": [
                        {**source["observations"][0], "sourceProofs": {"foreign": "a" * 64}},
                        *source["observations"][1:]]},
                    {"observations": source["observations"][:-1]}):
                category_receipt.chmod(0o600)
                category_receipt.write_bytes(checks.evidence.canonical_bytes({**source, **change}))
                category_receipt.chmod(0o400)
                changed = {**result, "externalProofsSha256": checks.evidence.file_sha256(category_receipt)}
                with self.assertRaises(checks.evidence.ConformanceError):
                    checks.category_source_parent(
                        run, category_inputs, category_manifest, category_observed, changed, **source_options)
                self.assertFalse(parent.exists())
            category_receipt.chmod(0o600)
            category_receipt.write_bytes(source_raw)
            with self.assertRaises(checks.evidence.ConformanceError):
                checks.category_source_parent(
                    run, category_inputs, category_manifest, category_observed, result, **source_options)
            category_receipt.chmod(0o400)
            checks.category_source_parent(
                run, category_inputs, category_manifest, category_observed, result, **source_options)
            linked = json.loads(parent.read_bytes())
            self.assertFalse(linked["qualification"])
            self.assertFalse(linked["nativeContainment"])
            self.assertEqual(linked["sourceReceiptSha256"], result["externalProofsSha256"])
            self.assertEqual(len(linked["observations"]), 16)

    def test_transfer_measurement_admits_only_exact_parent_memory_and_settlement_proof(self):
        self.assertTrue(callable(getattr(checks, "admit_transfer_measurement", None)),
                        "Actual large transfers need parent kernel memory and settlement admission.")
        command = {
            "schemaVersion": 1, "sequence": 3, "childPid": 200, "childStartSha256": "a" * 64,
            "startedMs": 1000, "endedMs": 1200, "exitCode": 0, "diagnosticCode": "None",
            "groupState": "Exited", "scope": "transfer", "transfer": {
                "bytes": 268435456, "phase": "complete", "baselineRssBytes": 1048576,
                "osPeakRssBytes": 2097152, "sampledPeakRssBytes": 2097152, "samples": 2,
                "osPeakMethod": "proc-status", "baselineMs": 1050, "completedMs": 1150,
            },
        }
        checks.admit_transfer_measurement(command, 3, 268435456)
        for change in (
                {"sequence": True}, {"childPid": True}, {"childStartSha256": "0" * 64},
                {"scope": "ordinary"}, {"exitCode": True}, {"groupState": "Retained"},
                {"diagnosticCode": "DeadlineExceeded"}, {"startedMs": float("nan")}, {"startedMs": 10**400},
                {"endedMs": 2401001}, {"extra": "ignored"}, {"transfer": None},
                *({"transfer": command["transfer"] | item} for item in (
                    {"bytes": 4294967296}, {"bytes": True}, {"phase": "transferring"},
                    {"osPeakMethod": "declared"}, {"baselineRssBytes": 0},
                    {"osPeakRssBytes": 1048576 + 67108865}, {"sampledPeakRssBytes": 2097153},
                    {"sampledPeakRssBytes": 1}, {"samples": 1}, {"samples": True}, {"extra": "ignored"},
                    {"baselineMs": 999}, {"completedMs": 1201}, {"completedMs": 1049},
                    {"baselineMs": False}, {"completedMs": float("nan")}, {"baselineMs": 10**400}))):
            with self.subTest(change=change), self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_transfer_measurement(command | change, 3, 268435456)

    def test_measured_transfer_binds_actual_producer_pid_hash_runtime_and_unchanged_memory_receipt(self):
        for namespace, mutation in (
                (namespace, mutation) for namespace in (
                    "artifact-transfers", "category-artifact-transfers", "qualification-artifact-transfers")
                for mutation in (None, "pid", "hash", "runtime", "pacing", "extra", "memory", "event")):
            root = self.directory / (namespace + "-" + str(mutation))
            (root / "stores" / namespace).mkdir(parents=True)
            (root / "proofs" / namespace).mkdir(parents=True)
            inputs = {"environment": ENVIRONMENT, "profileId": "artifacts",
                      "mode": "qualification" if namespace == "qualification-artifact-transfers" else "diagnostic"}
            run = SimpleNamespace(root=root, run_id=str(uuid.uuid4()), command_sequence=0, live_children=lambda: ())
            expected_hash = "a" * 64
            captured = []

            def command(args, **options):
                run.command_sequence += 1
                captured.append((args, options))
                measured = {
                    "bytes": 268435456, "phase": "complete", "baselineRssBytes": 1048576,
                    "osPeakRssBytes": 2097152, "sampledPeakRssBytes": 2097152, "samples": 2,
                    "osPeakMethod": "proc-status", "baselineMs": 1050, "completedMs": 1150,
                }
                if mutation == "memory":
                    measured["osPeakRssBytes"] = 2**40
                receipt = {
                    "schemaVersion": 1, "sequence": 1, "childPid": 200, "childStartSha256": "b" * 64,
                    "startedMs": 1000, "endedMs": 1200, "exitCode": 0, "diagnosticCode": "None",
                    "groupState": "Exited", "scope": "transfer", "transfer": measured,
                }
                (root / "proofs/transfer-command-0001.json").write_text(json.dumps(receipt))
                producer = {
                    "eventName": "complete", "provider": "local", "runId": run.run_id, "pid": 200,
                    "size": 268435456, "written": 268435456, "read": 268435456,
                    "expectedSha256": expected_hash, "sourceSha256": expected_hash, "sinkSha256": expected_hash,
                    "runtime": ".NET 10.0.7", "sourcePaced": True, "sinkPaced": True, "nonSeekable": True,
                    "generated": True, "independentExpectedHash": True, "warmupComplete": True,
                    "bufferBytes": 262144, "providerBufferLimit": 2097152, "slots": 1,
                }
                changes = {
                    "pid": {"pid": 201}, "hash": {"expectedSha256": "0" * 64},
                    "runtime": {"runtime": "foreign"}, "pacing": {"sinkPaced": False}, "extra": {"extra": True},
                }
                producer.update(changes.get(mutation, {}))
                (Path(args[3]) / "transfer-proof.json").write_text(json.dumps(producer))
                events = ({"event": "control", "code": "None", "value": 0},
                          {"event": "test", "code": "None", "value": 268435456},
                          {"event": "control", "code": "None", "value": 1})
                return SimpleNamespace(exit_code=0, events=events if mutation != "event" else events[:1])

            run.command = command
            with self.subTest(namespace=namespace, mutation=mutation):
                if mutation is not None:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError,
                                                "EvidenceIncomplete" if mutation == "event" else "ProofMismatch"):
                        checks.measured_artifact_transfer(
                            run, inputs, root / "runner.dll", "local", 268435456, expected_hash, namespace=namespace)
                    self.assertFalse((root / f"proofs/{namespace}/transfer-local-268435456/proof.json").exists())
                    continue
                result = checks.measured_artifact_transfer(
                    run, inputs, root / "runner.dll", "local", 268435456, expected_hash, namespace=namespace)
                self.assertEqual(result["childStartSha256"], "b" * 64)
                self.assertEqual(captured[0][1]["measure_transfer_bytes"], 268435456)
                self.assertEqual(captured[0][1]["env"], {"HOARD_CONFORMANCE_SAFE_EVENTS": "1"})
                self.assertEqual(captured[0][1]["cache_id"], namespace)
                self.assertEqual(Path(captured[0][0][3]).parent, root / "stores" / namespace)
                proof = json.loads((root / f"proofs/{namespace}/transfer-local-268435456/proof.json").read_bytes())
                self.assertEqual(proof["osPeakRssBytes"], 2097152)
                self.assertEqual(proof["osPeakMethod"], "proc-status")
                self.assertEqual(proof["runId"], run.run_id)

    def test_actual_transfer_controller_requests_both_qualified_sizes_and_providers(self):
        self.assertTrue(callable(getattr(checks, "artifact_transfer_diagnostics", None)),
                        "Large transfer proof requires actual owned runner invocations for every frozen row.")
        root = self.directory
        candidate = root / "candidate"
        assembly = candidate / checks.ARTIFACT_TRANSFER / (
            "bin/Release/net10.0/Hoard.Fixtures.Artifacts.TransferRunner.dll")
        assembly.parent.mkdir(parents=True)
        assembly.write_bytes(b"transfer-controller-unit-double")
        (root / "stores").mkdir()
        (root / "proofs").mkdir()
        run = SimpleNamespace(root=root, run_id=str(uuid.uuid4()))
        inputs = {"runtimeAssemblies": {
            assembly.relative_to(root).as_posix(): hashlib.sha256(assembly.read_bytes()).hexdigest()}}
        with patch.object(checks, "verify_runtime_packages") as images, patch.object(
                checks, "measured_artifact_transfer", return_value={"proofSha256": "a" * 64}) as execute:
            result = checks.artifact_transfer_diagnostics(run, inputs, candidate)
            self.assertFalse(result["qualification"])
            self.assertEqual(result["inputsSha256"], checks.evidence.digest(inputs))
            self.assertEqual([call.args[3:5] for call in execute.call_args_list],
                             [("local", 268435456), ("local", 4294967296),
                              ("object", 268435456), ("object", 4294967296)])
            images.assert_called_once_with(assembly.parent, root / "feed/candidate",
                                           checks.ARTIFACT_RECOVERY_PACKAGES)
        category_inputs = {**inputs, "profileId": "artifacts", "mode": "diagnostic"}
        with patch.object(checks, "verify_runtime_packages"), patch.object(
                checks, "measured_artifact_transfer", return_value={"proofSha256": "b" * 64}) as execute:
            category = checks.artifact_transfer_diagnostics(
                run, category_inputs, candidate, namespace="category-artifact-transfers")
            self.assertEqual(category["inputsSha256"], checks.evidence.digest(category_inputs))
            self.assertNotEqual(category["inputsSha256"], result["inputsSha256"])
            self.assertEqual(execute.call_count, 4)
            self.assertTrue(all(call.kwargs["namespace"] == "category-artifact-transfers"
                                for call in execute.call_args_list))
            self.assertTrue((root / "proofs/artifact-transfers.json").exists())
            self.assertTrue((root / "proofs/category-artifact-transfers.json").exists())
            for namespace, captured in (("../foreign", category_inputs),
                                        ("category-artifact-transfers", inputs),
                                        ("category-artifact-transfers", {**category_inputs, "mode": "qualification"})):
                with self.assertRaises(checks.evidence.ConformanceError):
                    checks.artifact_transfer_diagnostics(run, captured, candidate, namespace=namespace)
            self.assertEqual(execute.call_count, 4)
        qualified_inputs = {**category_inputs, "mode": "qualification"}
        native_run = object.__new__(checks.OwnedRun)
        native_run.root, native_run.run_id = root, run.run_id
        with patch.object(checks, "verify_runtime_packages"), patch.object(
                checks, "measured_artifact_transfer", return_value={"proofSha256": "f" * 64}) as execute, patch.object(
                checks, "native_artifact_transfer_controls") as admit:
            qualified = checks.artifact_transfer_diagnostics(
                native_run, qualified_inputs, candidate, namespace="qualification-artifact-transfers")
            self.assertEqual(qualified["inputsSha256"], checks.evidence.digest(qualified_inputs))
            self.assertFalse(qualified["qualification"])
            self.assertTrue(all(call.kwargs["namespace"] == "qualification-artifact-transfers"
                                for call in execute.call_args_list))
            self.assertEqual(
                [call.args[3:5] for call in execute.call_args_list],
                [("local", 268435456), ("local", 4294967296), ("object", 268435456), ("object", 4294967296)])
            self.assertTrue((root / "proofs/qualification-artifact-transfers.json").exists())
            admit.assert_called_once()
            self.assertEqual(admit.call_args.args, (native_run, qualified_inputs))
            self.assertLessEqual(admit.call_args.kwargs["started_ms"], admit.call_args.kwargs["ended_ms"])
            for captured in (inputs, category_inputs, {**qualified_inputs, "profileId": "metadata"}):
                with self.assertRaises(checks.evidence.ConformanceError):
                    checks.artifact_transfer_diagnostics(
                        run, captured, candidate, namespace="qualification-artifact-transfers")
            self.assertEqual(execute.call_count, 4)
            admit.assert_called_once()
        with patch.object(checks, "verify_runtime_packages"), patch.object(checks, "measured_artifact_transfer") as execute:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.artifact_transfer_diagnostics(
                    run, {"runtimeAssemblies": {assembly.relative_to(root).as_posix(): "0" * 64}}, candidate)
            execute.assert_not_called()

    def test_qualification_transfer_controller_does_not_publish_a_summary_after_joint_source_rejection(self):
        root = self.directory
        assembly = root / "candidate" / checks.ARTIFACT_TRANSFER / (
            "bin/Release/net10.0/Hoard.Fixtures.Artifacts.TransferRunner.dll")
        assembly.parent.mkdir(parents=True)
        assembly.write_bytes(b"transfer-controller-unit-double")
        (root / "stores").mkdir()
        (root / "proofs").mkdir()
        run = object.__new__(checks.OwnedRun)
        run.root, run.run_id = root, str(uuid.uuid4())
        inputs = {"profileId": "artifacts", "mode": "qualification", "runtimeAssemblies": {
            assembly.relative_to(root).as_posix(): hashlib.sha256(assembly.read_bytes()).hexdigest()}}
        with patch.object(checks, "verify_runtime_packages"), patch.object(
                checks, "measured_artifact_transfer", return_value={"proofSha256": "f" * 64}) as execute, patch.object(
                checks, "native_artifact_transfer_controls",
                side_effect=checks.evidence.ConformanceError("ProofMismatch")) as admit:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.artifact_transfer_diagnostics(
                    run, inputs, root / "candidate", namespace="qualification-artifact-transfers")
            self.assertEqual(execute.call_count, 4)
            admit.assert_called_once()
            self.assertFalse((root / "proofs/qualification-artifact-transfers.json").exists())

    def test_artifact_source_consumption_rechecks_all_four_original_transfer_graphs_and_propagates_failure(self):
        run, inputs, manifest, ingested = (
            SimpleNamespace(root=self.directory), {}, {"attemptId": str(uuid.uuid4())}, {})
        for failed in (None, "transfer", "children"):
            with self.subTest(failed=failed), patch.object(
                    checks, "native_artifact_transfer_source",
                    side_effect=checks.evidence.ConformanceError("ProofMismatch") if failed == "transfer" else None
                    ) as transfer, patch.object(
                    checks, "artifact_original_child_sources",
                    side_effect=checks.evidence.ConformanceError("ProofMismatch") if failed == "children" else None
                    ) as children, patch.object(
                    checks, "artifact_source_observations", return_value=([], {})) as capture, patch.object(
                    checks, "artifact_source_output_seal", return_value=b"original-index") as seal:
                if failed:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                        checks._artifact_source_consumption(run, inputs, manifest, ingested, "category-artifact-transfers")
                    capture.assert_not_called()
                    seal.assert_not_called()
                    self.assertEqual(children.call_count, int(failed == "children"))
                else:
                    complete_inputs = {"runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4())}
                    complete_manifest = {"attemptId": str(uuid.uuid4())}
                    checks._artifact_source_consumption(
                        run, complete_inputs, complete_manifest, ingested, "category-artifact-transfers")
                    self.assertEqual(
                        [call.args[2:] for call in transfer.call_args_list],
                        [("local", 268435456), ("local", 4294967296), ("object", 268435456), ("object", 4294967296)])
                    self.assertTrue(all(call.kwargs == {"namespace": "category-artifact-transfers"}
                                        for call in transfer.call_args_list))
                    capture.assert_called_once()
                    seal.assert_called_once()
                    children.assert_called_once_with(
                        run.root, complete_inputs, complete_manifest["attemptId"], namespace="category-artifact-transfers")

    def test_native_transfer_measurement_pins_original_inputs_controller_and_command_result(self):
        import conformance_sources as sources
        self.assertTrue(callable(getattr(sources, "native_artifact_transfer_source", None)))
        for namespace, changed in (
                (namespace, changed) for namespace in (
                    "artifact-transfers", "category-artifact-transfers", "qualification-artifact-transfers")
                for changed in (None, "result", "controller", "producer", "assembly", "run", "provider", "size")):
            root = self.directory / namespace / str(changed)
            (root / "stores" / namespace).mkdir(parents=True)
            (root / "proofs" / namespace).mkdir(parents=True)
            assembly_path = ("candidate/tests/fixtures/artifacts/TransferRunner/"
                             "bin/Release/net10.0/Hoard.Fixtures.Artifacts.TransferRunner.dll")
            assembly = root / assembly_path
            assembly.parent.mkdir(parents=True)
            assembly.write_bytes(b"modeled-transfer-assembly")
            assembly.chmod(0o400)
            run = object.__new__(checks.OwnedRun)
            run.root, run.run_id, run.root_id = root, str(uuid.uuid4()), uuid.uuid4().hex
            run.command_sequence = 0
            run.live_children = lambda: ()
            inputs = {
                "runId": run.run_id, "invocationGroupId": str(uuid.uuid4()),
                "environment": ENVIRONMENT, "profileId": "artifacts",
                "mode": "qualification" if namespace == "qualification-artifact-transfers" else "diagnostic",
                "runtimeAssemblies": {assembly_path: checks.evidence.file_sha256(assembly)}}
            if changed == "assembly":
                inputs["runtimeAssemblies"][assembly_path] = "c" * 64
            elif changed == "run":
                inputs["runId"] = str(uuid.uuid4())
            expected_hash = checks.artifacts.expected_transfer_hash(268435456)
            held = {}

            def command(arguments, **options):
                self.assertTrue(options.get("record_execution"))
                input_path = f"proofs/{namespace}/transfer-local-268435456-native-inputs.json"
                self.assertEqual(options["execution_inputs"], (assembly_path, input_path))
                producer_path = f"proofs/{namespace}/transfer-local-268435456/producer.json"
                self.assertEqual(options.get("execution_outputs"), (producer_path,))
                self.assertEqual(arguments[-1], str(root / producer_path))
                self.assertEqual((root / input_path).read_bytes(), checks.evidence.canonical_bytes(inputs))
                self.assertEqual((root / input_path).stat().st_mode & 0o777, 0o400)
                run.command_sequence += 1
                control = {
                    "schemaVersion": 1, "sequence": 1, "childPid": 200, "childStartSha256": "b" * 64,
                    "startedMs": 1000, "endedMs": 1200, "exitCode": 0, "diagnosticCode": "None",
                    "groupState": "Exited", "scope": "transfer", "transfer": {
                        "bytes": 268435456, "phase": "complete", "baselineRssBytes": 1048576,
                        "osPeakRssBytes": 2097152, "sampledPeakRssBytes": 2097152, "samples": 2,
                        "osPeakMethod": "proc-status", "baselineMs": 1050, "completedMs": 1150}}
                raw = checks.evidence.canonical_bytes(control)
                (root / "proofs/transfer-command-0001.json").write_bytes(raw)
                producer = {
                    "eventName": "complete", "provider": "local", "runId": run.run_id, "pid": 200,
                    "size": 268435456, "written": 268435456, "read": 268435456,
                    "expectedSha256": expected_hash, "sourceSha256": expected_hash, "sinkSha256": expected_hash,
                    "runtime": ".NET 10.0.7", "sourcePaced": True, "sinkPaced": True, "nonSeekable": True,
                    "generated": True, "independentExpectedHash": True, "warmupComplete": True,
                    "bufferBytes": 262144, "providerBufferLimit": 2097152, "slots": 1}
                (Path(arguments[3]) / "transfer-proof.json").write_bytes(checks.evidence.canonical_bytes(producer))
                (root / producer_path).write_bytes(checks.evidence.canonical_bytes(producer))
                (root / producer_path).chmod(0o400)
                held[1] = checks.evidence.canonical_bytes({
                    **{key: value for key, value in control.items() if key != "transfer"},
                    "runId": run.run_id, "rootId": run.root_id,
                    "argvSha256": checks.evidence.digest(arguments),
                    "cwdSha256": hashlib.sha256(str(assembly.parent).encode()).hexdigest(),
                    "controlRecordSha256": hashlib.sha256(raw).hexdigest(),
                    "inputFiles": {assembly_path: checks.evidence.file_sha256(assembly),
                                   input_path: checks.evidence.digest(inputs)},
                    "outputFiles": {producer_path: checks.evidence.digest(producer)}})
                if changed == "controller":
                    control["transfer"]["osPeakRssBytes"] += 1024
                    (root / "proofs/transfer-command-0001.json").write_bytes(checks.evidence.canonical_bytes(control))
                elif changed == "producer":
                    (root / producer_path).chmod(0o600)
                    (root / producer_path).write_bytes(json.dumps(producer, separators=(",", ":")).encode())
                    (root / producer_path).chmod(0o400)
                return SimpleNamespace(
                    exit_code=0, events=(
                        {"event": "control", "code": "None", "value": 0},
                        {"event": "test", "code": "None", "value": 268435456},
                        {"event": "control", "code": "None", "value": 1}),
                    execution_record_sha256="c" * 64 if changed == "result" else hashlib.sha256(held[1]).hexdigest())

            run.command = command
            run.read_execution_record = lambda sequence: held[sequence]
            with self.subTest(namespace=namespace, changed=changed):
                receipt = root / f"proofs/{namespace}/transfer-local-268435456/native-execution.json"
                if changed:
                    with self.assertRaisesRegex(
                            checks.evidence.ConformanceError,
                            "InputChanged" if changed in ("assembly", "run") else "ProofMismatch"):
                        checks.measured_artifact_transfer(
                            run, inputs, assembly, "../foreign" if changed == "provider" else "local",
                            True if changed == "size" else 268435456, expected_hash,
                            namespace=namespace)
                    self.assertFalse(receipt.exists())
                else:
                    checks.measured_artifact_transfer(
                        run, inputs, assembly, "local", 268435456, expected_hash, namespace=namespace)
                    observed = checks.evidence.load_json(receipt.read_bytes())
                    self.assertEqual(observed["executionSha256"], hashlib.sha256(held[1]).hexdigest())
                    self.assertEqual(observed["inputsSha256"], checks.evidence.digest(inputs))
                    self.assertEqual(observed["sequence"], 1)
                    self.assertEqual(observed["rootId"], run.root_id)
                    self.assertEqual(receipt.stat().st_mode & 0o777, 0o400)
                    control_path = root / "proofs/transfer-command-0001.json"
                    control_path.chmod(0o400)
                    run.command_sequence += 1
                    admitted = sources.native_artifact_transfer_source(
                        run, inputs, "local", 268435456, namespace=namespace)
                    self.assertEqual(admitted["sequence"], 1)
                    self.assertEqual(admitted["producerSha256"], observed["producerSha256"])
                    original = receipt.read_bytes()
                    for defect in ("recipe", "control", "producer", "inputs", "combined"):
                        with self.subTest(source=defect):
                            target = {
                                "recipe": receipt, "control": control_path,
                                "producer": receipt.parent / "producer.json",
                                "inputs": root / f"proofs/{namespace}/transfer-local-268435456-native-inputs.json",
                                "combined": receipt.parent / "proof.json"}[defect]
                            before = target.read_bytes()
                            target.chmod(0o600)
                            body = checks.evidence.load_json(before)
                            if defect == "recipe":
                                body["sequence"] = 2
                            elif defect == "control":
                                body["transfer"]["osPeakRssBytes"] += 1024
                            elif defect == "inputs":
                                body["runId"] = str(uuid.uuid4())
                            elif defect == "combined":
                                body["samples"] += 1
                            replacement = (json.dumps(dict(reversed(tuple(body.items()))), separators=(",", ":")).encode()
                                           if defect == "producer" else checks.evidence.canonical_bytes(body))
                            self.assertNotEqual(replacement, before)
                            target.write_bytes(replacement)
                            target.chmod(0o400)
                            if defect in ("control", "producer"):
                                rewired = checks.evidence.load_json(original)
                                rewired["controllerSha256" if defect == "control" else "producerSha256"] = (
                                    hashlib.sha256(replacement).hexdigest())
                                receipt.chmod(0o600)
                                receipt.write_bytes(checks.evidence.canonical_bytes(rewired))
                                receipt.chmod(0o400)
                            with self.assertRaises(checks.evidence.ConformanceError):
                                sources.native_artifact_transfer_source(
                                    run, inputs, "local", 268435456, namespace=namespace)
                            target.chmod(0o600)
                            target.write_bytes(before)
                            target.chmod(0o400)
                            if defect in ("control", "producer"):
                                receipt.chmod(0o600)
                                receipt.write_bytes(original)
                                receipt.chmod(0o400)
                    self.assertEqual(receipt.read_bytes(), original)

    def test_noncooperative_observations_require_real_retention_and_matching_live_child(self):
        import conformance_sources as sources
        self.assertTrue(callable(getattr(sources, "admit_artifact_noncooperation", None)),
                        "Retained-work observations must be checked before their numeric barriers qualify.")
        self.assertIs(checks.admit_artifact_noncooperation, sources.admit_artifact_noncooperation)
        run_id = str(uuid.uuid4())
        observation = {
            "eventName": "noncooperative", "phase": "contained", "pid": 200, "runId": run_id,
            "provider": "local", "scenario": "source", "durableCrashProof": False,
            "cleanup": "RetainedLiveOwnership", "callerCode": "CancelledBeforeCommit",
            "admissionCode": "CleanupIncomplete", "shutdownCode": "CleanupIncomplete",
            "enteredWorkers": 1, "workerPending": True, "borrowedStreamsIntact": True,
            "rootStillOwned": True, "readinessBlocked": True, "protectionRetained": False,
        }
        checks.admit_artifact_noncooperation(observation, "local", "source", "contained", 200, run_id)
        for change in (
                {"pid": 201}, {"pid": True}, {"runId": str(uuid.uuid4())}, {"provider": "object"},
                {"scenario": "native"}, {"phase": "inspected"}, {"durableCrashProof": True},
                {"cleanup": "Released"}, {"callerCode": "None"}, {"admissionCode": "None"},
                {"shutdownCode": "None"}, {"enteredWorkers": 2}, {"enteredWorkers": True},
                {"workerPending": False}, {"borrowedStreamsIntact": False}, {"rootStillOwned": False},
                {"readinessBlocked": False}, {"protectionRetained": True}, {"extra": True}):
            with self.subTest(change=change), self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_artifact_noncooperation(
                    observation | change, "local", "source", "contained", 200, run_id)
        for code in ("Uncertain", "DeadlineExceeded"):
            changed = observation | {"scenario": "native", "callerCode": code, "protectionRetained": True}
            checks.admit_artifact_noncooperation(changed, "local", "native", "contained", 200, run_id)
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_artifact_noncooperation(
                    changed | {"protectionRetained": False}, "local", "native", "contained", 200, run_id)

    def test_inspection_receipts_reject_missing_reordered_and_foreign_handshakes(self):
        command = {
            "schemaVersion": 1, "sequence": 1, "childPid": 200, "childStartSha256": "a" * 64,
            "startedMs": 1000, "endedMs": 1500, "exitCode": -9, "diagnosticCode": "None",
            "groupState": "Exited", "scope": "recovery", "barrier": {
                "value": 70, "observedMs": 1300, "signalMs": 1400,
                "inspection": {"value": 60, "observedMs": 1100, "requestMs": 1200},
            },
        }
        checks.admit_recovery_barrier(command, 1, 70, inspection=60)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
            checks.admit_recovery_barrier(command, 1, 70)
        for change in (
                {"value": 61}, {"value": True}, {"observedMs": 999}, {"requestMs": 1099},
                {"requestMs": 1301}, {"requestMs": None}, {"requestMs": float("nan")}, {"extra": True}):
            changed = command | {"barrier": command["barrier"] | {
                "inspection": command["barrier"]["inspection"] | change}}
            with self.subTest(change=change), self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_recovery_barrier(changed, 1, 70, inspection=60)

    def test_noncooperative_controller_requires_both_matching_producers_and_exact_parent_inspection(self):
        for mutation in (None, "foreign", "wrong-second", "handoff", "event"):
            root = self.directory / str(mutation)
            (root / "stores/artifact-noncooperation").mkdir(parents=True)
            (root / "proofs").mkdir()
            run = SimpleNamespace(root=root, command_sequence=0, live_children=lambda: ())
            invocations = []

            def command(args, **options):
                run.command_sequence += 1
                invocations.append((args, options))
                receipt = {
                    "schemaVersion": 1, "sequence": 1, "childPid": 200, "childStartSha256": "a" * 64,
                    "startedMs": 1000, "endedMs": 1500, "exitCode": -9, "diagnosticCode": "None",
                    "groupState": "Exited", "scope": "recovery", "barrier": {
                        "value": 70, "observedMs": 1300, "signalMs": 1400,
                        "inspection": {"value": 60, "observedMs": 1100, "requestMs": 1200},
                    },
                }
                if mutation == "handoff":
                    receipt["barrier"]["inspection"]["requestMs"] = None
                (root / "proofs/recovery-command-0001.json").write_text(json.dumps(receipt))
                for phase in ("contained", "inspected"):
                    producer = {
                        "eventName": "noncooperative", "phase": phase, "pid": 200, "runId": args[6],
                        "provider": "local", "scenario": "source", "durableCrashProof": False,
                        "cleanup": "RetainedLiveOwnership", "callerCode": "CancelledBeforeCommit",
                        "admissionCode": "CleanupIncomplete", "shutdownCode": "CleanupIncomplete",
                        "enteredWorkers": 1, "workerPending": True, "borrowedStreamsIntact": True,
                        "rootStillOwned": True, "readinessBlocked": True, "protectionRetained": False,
                    }
                    if mutation == "foreign":
                        producer["pid"] = 201
                    if mutation == "wrong-second" and phase == "inspected":
                        producer["runId"] = str(uuid.uuid4())
                    (Path(args[3]) / f"noncooperative-{phase}.json").write_text(json.dumps(producer))
                events = ({"event": "barrier", "code": "None", "value": 60},
                          {"event": "barrier", "code": "None", "value": 70})
                return SimpleNamespace(exit_code=-9, events=events if mutation != "event" else events[:1])

            run.command = command
            with self.subTest(mutation=mutation):
                if mutation is not None:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                        checks.artifact_noncooperation(run, root / "runner.dll", "local", "source")
                    continue
                observed = checks.artifact_noncooperation(run, root / "runner.dll", "local", "source")
                self.assertEqual(observed["childStartSha256"], "a" * 64)
                self.assertNotEqual(observed["containedSha256"], observed["inspectedSha256"])
                self.assertEqual(invocations[0][1]["inspect_at_barrier"], 60)
                self.assertEqual(invocations[0][1]["stop_at_barrier"], 70)
                self.assertEqual(invocations[0][1]["env"], {"HOARD_CONFORMANCE_SAFE_EVENTS": "1"})

    def test_noncooperative_controller_requests_source_sink_and_native_inspection_on_both_actual_providers(self):
        self.assertTrue(callable(getattr(checks, "artifact_noncooperation_diagnostics", None)),
                        "Artifact retained work requires actual owned inspection/termination on both providers.")
        root = self.directory
        candidate = root / "candidate"
        assembly = candidate / checks.ARTIFACT_RECOVERY / (
            "bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll")
        assembly.parent.mkdir(parents=True)
        assembly.write_bytes(b"noncooperative-controller-unit-double")
        (root / "stores").mkdir()
        (root / "proofs").mkdir()
        run = SimpleNamespace(root=root)
        inputs = {"runtimeAssemblies": {
            assembly.relative_to(root).as_posix(): hashlib.sha256(assembly.read_bytes()).hexdigest()}}
        with patch.object(checks, "verify_runtime_packages"), patch.object(
                checks, "artifact_noncooperation", return_value={"controllerSha256": "a" * 64}) as execute:
            result = checks.artifact_noncooperation_diagnostics(run, inputs, candidate)
            self.assertFalse(result["qualification"])
            self.assertEqual(result["inputsSha256"], checks.evidence.digest(inputs))
            self.assertEqual([call.args[2:4] for call in execute.call_args_list], [
                (provider, scenario) for provider in ("local", "object") for scenario in ("source", "destination", "native")])
        with patch.object(checks, "verify_runtime_packages"), patch.object(checks, "artifact_noncooperation") as execute:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.artifact_noncooperation_diagnostics(
                    run, {"runtimeAssemblies": {assembly.relative_to(root).as_posix(): "0" * 64}}, candidate)
            execute.assert_not_called()

    def test_metadata_recovery_barrier_requires_exact_observe_signal_exit_chain(self):
        self.assertTrue(callable(getattr(checks, "admit_recovery_barrier", None)),
                        "Real recovery needs an admitted parent-owned observation/signal/exit chain.")
        command = {
            "schemaVersion": 1, "sequence": 3, "childPid": 200,
            "childStartSha256": "a" * 64, "startedMs": 1000, "endedMs": 1200,
            "exitCode": -9, "diagnosticCode": "None", "groupState": "Exited", "scope": "recovery",
            "barrier": {"value": 10, "observedMs": 1050, "signalMs": 1100},
        }
        checks.admit_recovery_barrier(command, 3, 10)
        changes = (
            {"sequence": 4}, {"sequence": True}, {"schemaVersion": True},
            {"childPid": 0}, {"childPid": True}, {"childStartSha256": "0" * 64},
            {"exitCode": 0}, {"exitCode": True}, {"diagnosticCode": "DeadlineExceeded"},
            {"groupState": "Retained"}, {"scope": "ordinary"}, {"extra": "ignored"},
            {"startedMs": float("nan")}, {"endedMs": float("inf")}, {"endedMs": True},
            {"endedMs": 17001},
            *({"barrier": command["barrier"] | change} for change in (
                {"value": 11}, {"value": True}, {"extra": "ignored"},
                {"observedMs": None}, {"signalMs": None}, {"observedMs": 999},
                {"signalMs": 1049}, {"signalMs": 1201}, {"signalMs": float("nan")},
                {"observedMs": False})),
            {"barrier": None},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaisesRegex(
                    checks.evidence.ConformanceError, "ProofMismatch"):
                checks.admit_recovery_barrier(command | change, 3, 10)

    def test_native_control_receipts_bind_actual_controller_bytes_not_only_exit_and_pid(self):
        import conformance_sources as sources

        run = SimpleNamespace(
            run_id=str(uuid.uuid4()), root_id=str(uuid.uuid4()), live_children=lambda: ())
        control = {
            "schemaVersion": 1, "sequence": 3, "childPid": 200,
            "childStartSha256": "a" * 64, "startedMs": 1000, "endedMs": 1200,
            "exitCode": -9, "diagnosticCode": "None", "groupState": "Exited", "scope": "recovery",
            "barrier": {"value": 10, "observedMs": 1050, "signalMs": 1100},
        }
        arguments, cwd = ["dotnet", "owned-runner.dll", "run-upgrade"], self.directory
        input_files = {"proofs/current-inputs.json": "b" * 64}
        raw = checks.evidence.canonical_bytes(control)
        record = {
            **{key: value for key, value in control.items() if key != "barrier"},
            "runId": run.run_id, "rootId": run.root_id,
            "argvSha256": checks.evidence.digest(arguments),
            "cwdSha256": hashlib.sha256(str(cwd.absolute()).encode()).hexdigest(),
            "inputFiles": input_files, "controlRecordSha256": hashlib.sha256(raw).hexdigest(),
        }
        native_raw = checks.evidence.canonical_bytes(record)
        run.read_execution_record = unittest.mock.Mock(return_value=native_raw)
        with patch.object(sources, "OwnedRun", type(run)):
            self.assertEqual(sources.native_control_record(
                run, 3, raw, arguments=arguments, cwd=cwd, input_files=input_files), native_raw)
            run.read_execution_record.assert_called_once_with(3)
            for changed in (
                    control | {"barrier": control["barrier"] | {"value": 11}},
                    control | {"barrier": control["barrier"] | {"observedMs": 1060}},
                    control | {"childStartSha256": "c" * 64}):
                with self.subTest(changed=changed), self.assertRaises(checks.evidence.ConformanceError):
                    sources.native_control_record(
                        run, 3, checks.evidence.canonical_bytes(changed),
                        arguments=arguments, cwd=cwd, input_files=input_files)
            for change in (
                    {"sequence": 4}, {"arguments": ["dotnet", "unrelated.dll"]},
                    {"cwd": cwd / "foreign"}, {"input_files": input_files | {"foreign.json": "d" * 64}}):
                options = {"sequence": 3, "arguments": arguments, "cwd": cwd, "input_files": input_files} | change
                with self.subTest(change=change), self.assertRaises(checks.evidence.ConformanceError):
                    sources.native_control_record(run, control_raw=raw, **options)
            run.read_execution_record.side_effect = checks.evidence.ConformanceError("OwnershipInvalid")
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "OwnershipInvalid"):
                sources.native_control_record(
                    run, 3, raw, arguments=arguments, cwd=cwd, input_files=input_files)
            run.read_execution_record.side_effect = None
            timed_out = {key: value for key, value in control.items() if key != "barrier"}
            timed_out["diagnosticCode"] = "DeadlineExceeded"
            timeout_raw = checks.evidence.canonical_bytes(timed_out)
            timeout_native = checks.evidence.canonical_bytes({
                **record, "diagnosticCode": "DeadlineExceeded",
                "controlRecordSha256": hashlib.sha256(timeout_raw).hexdigest()})
            run.read_execution_record.return_value = timeout_native
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                sources.native_control_record(
                    run, 3, timeout_raw, arguments=arguments, cwd=cwd, input_files=input_files)
            self.assertEqual(sources.native_control_record(
                run, 3, timeout_raw, arguments=arguments, cwd=cwd, input_files=input_files,
                diagnostic_code="DeadlineExceeded"), timeout_native)
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                sources.native_control_record(
                    run, 3, raw, arguments=arguments, cwd=cwd, input_files=input_files,
                    diagnostic_code="DeadlineExceeded")
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "OwnershipInvalid"):
            sources.native_control_record(run, 3, raw, arguments=arguments, cwd=cwd, input_files=input_files)

    def test_native_recovery_command_checks_the_actual_command_result_record_digest(self):
        from conformance_execution import CommandResult

        (self.directory / "proofs").mkdir()
        command = {
            "schemaVersion": 1, "sequence": 1, "childPid": 200,
            "childStartSha256": "a" * 64, "startedMs": 1000, "endedMs": 1200,
            "exitCode": 0, "diagnosticCode": "None", "groupState": "Exited", "scope": "recovery",
        }
        raw = checks.evidence.canonical_bytes(command)
        (self.directory / "proofs/recovery-command-0001.json").write_bytes(raw)
        recorded = b"executor-retained-record"
        result = CommandResult(
            0, ({"event": "test", "code": "None", "value": 1},), 200,
            hashlib.sha256(recorded).hexdigest())
        run = SimpleNamespace(
            root=self.directory, command_sequence=0, live_children=lambda: (),
            command=unittest.mock.Mock(return_value=result))
        with patch.object(checks, "OwnedRun", type(run)), patch.object(
                checks, "native_control_record", return_value=recorded):
            self.assertEqual(checks.recovery_command(
                run, self.directory / "runner.dll", ["recover-mutation"], cache_id="recovery"),
                (hashlib.sha256(raw).hexdigest(), command))
            self.assertTrue(run.command.call_args.kwargs["record_execution"])
            for digest in (None, "0" * 64):
                run.command.return_value = CommandResult(0, result.events, 200, digest)
                with self.subTest(digest=digest), self.assertRaisesRegex(
                        checks.evidence.ConformanceError, "ProofMismatch"):
                    checks.recovery_command(
                        run, self.directory / "runner.dll", ["recover-mutation"], cache_id="recovery")

    def test_native_ownership_producer_seals_probe_then_reopens_same_database(self):
        from conformance_execution import CommandResult

        root = self.directory
        candidate = root / "candidate"
        assembly = candidate / checks.METADATA_RECOVERY / "bin/Release/net10.0/Hoard.Fixtures.Metadata.CrashRunner.dll"
        assembly.parent.mkdir(parents=True)
        assembly.write_bytes(b"explicit-modeled-owner-controller-not-native")
        (root / "stores").mkdir()
        (root / "proofs").mkdir()
        namespace = "qualification-sqlite-ownership"
        probe_path = f"proofs/{namespace}-probe.json"
        inputs = {"profileId": "metadata", "mode": "qualification", "invocationGroupId": str(uuid.uuid4()),
                  "runtimeAssemblies": {assembly.relative_to(root).as_posix(): checks.evidence.file_sha256(assembly)}}
        records, calls = {}, []
        run = SimpleNamespace(root=root, run_id=str(uuid.uuid4()), command_sequence=0, live_children=lambda: ())

        def command(arguments, **options):
            run.command_sequence += 1
            sequence = run.command_sequence
            calls.append((arguments, options))
            holding = arguments[2] == "hold-owner-probe"
            control = {
                "schemaVersion": 1, "sequence": sequence, "childPid": 200,
                "childStartSha256": "a" * 64, "startedMs": sequence * 1000, "endedMs": sequence * 1000 + 200,
                "exitCode": -9 if holding else 0, "diagnosticCode": "None", "groupState": "Exited", "scope": "recovery",
                **({"barrier": {"value": 30, "observedMs": 1050, "signalMs": 1100}} if holding else {})}
            (root / f"proofs/recovery-command-{sequence:04}.json").write_bytes(checks.evidence.canonical_bytes(control))
            records[sequence] = b"explicit-native-record-model-" + str(sequence).encode()
            if holding:
                (root / probe_path).write_bytes(b"explicit-probe-model")
            return CommandResult(control["exitCode"], ({
                "event": "barrier" if holding else "test", "code": "None", "value": 30 if holding else 1},),
                200, hashlib.sha256(records[sequence]).hexdigest())

        run.command = command
        run.read_execution_record = lambda sequence: records[sequence]
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "OwnershipInvalid"):
            checks.recovery_command(run, assembly, ["hold-owner-probe"], cache_id=namespace,
                                    execution_outputs=(probe_path,))
        self.assertEqual(calls, [])
        with patch.object(checks, "OwnedRun", type(run)), patch.object(
                checks, "require_sqlite_environment"), patch.object(checks, "verify_runtime_packages"), patch.object(
                checks, "native_control_record", side_effect=lambda _, sequence, *args, **kwargs: records[sequence]) as native, patch.object(
                checks, "native_metadata_ownership_control") as admission:
            result = checks.metadata_ownership_diagnostics(run, inputs, candidate)
        graph = checks.evidence.load_json((root / f"proofs/{namespace}-native-executions.json").read_bytes())
        self.assertEqual(result, checks.evidence.digest(graph))
        self.assertEqual([row["mode"] for row in graph["commands"]], ["hold-owner-probe", "reopen-owner"])
        self.assertEqual(calls[0][0][3:5], calls[1][0][3:5])
        self.assertEqual(calls[0][0][-1], str(root / probe_path))
        self.assertEqual(calls[0][1]["execution_outputs"], (probe_path,))
        self.assertNotIn("execution_outputs", calls[1][1])
        self.assertEqual(native.call_args_list[0].kwargs["output_files"],
                         {probe_path: checks.evidence.file_sha256(root / probe_path)})
        admission.assert_called_once()
        self.assertEqual((root / f"proofs/{namespace}-native-inputs.json").read_bytes(),
                         checks.evidence.canonical_bytes(inputs))

    def test_native_package_consumer_runs_same_assembly_with_explicit_binding_and_owned_store(self):
        root = self.directory
        candidate = root / "candidate"
        assembly = candidate / checks.METADATA_PACKAGE_CONSUMER / "bin/Release/net10.0/Hoard.Fixtures.Metadata.Consumer.dll"
        assembly.parent.mkdir(parents=True)
        assembly.write_bytes(b"explicit-common-consumer-model-not-native")
        (root / "stores").mkdir()
        (root / "proofs").mkdir()
        namespace = "qualification-metadata-package-consumer"
        inputs = {"profileId": "metadata", "mode": "qualification", "invocationGroupId": str(uuid.uuid4()),
                  "runtimeAssemblies": {assembly.relative_to(root).as_posix(): checks.evidence.file_sha256(assembly)}}
        run = SimpleNamespace(root=root, run_id=str(uuid.uuid4()), command_sequence=0,
                              read_execution_record=lambda sequence: b"explicit-native-model-" + str(sequence).encode())
        calls = []

        def execute(owner, selected, arguments, **options):
            self.assertIs(owner, run)
            self.assertEqual(selected, assembly)
            run.command_sequence += 1
            calls.append((arguments, options))
            return "a" * 64, {"sequence": run.command_sequence}

        with patch.object(checks, "OwnedRun", type(run)), patch.object(
                checks, "require_sqlite_environment"), patch.object(checks, "verify_runtime_packages"), patch.object(
                checks, "recovery_command", side_effect=execute), patch.object(
                checks, "native_metadata_package_consumer_control") as admission:
            result = checks.metadata_package_consumer_diagnostics(run, inputs, candidate)
        graph = checks.evidence.load_json((root / f"proofs/{namespace}-native-executions.json").read_bytes())
        self.assertEqual(result, checks.evidence.digest(graph))
        self.assertEqual([row["bindingId"] for row in graph["commands"]], ["sqlite", "memory"])
        for (arguments, options), binding in zip(calls, ("sqlite", "memory"), strict=True):
            self.assertEqual(arguments, [binding, str(root / "stores" / namespace / binding / "metadata.db")])
            self.assertEqual(options["execution_inputs"],
                             (assembly.relative_to(root).as_posix(), f"proofs/{namespace}-native-inputs.json"))
            self.assertEqual(options["cache_id"], namespace)
        admission.assert_called_once()
        self.assertEqual((root / f"proofs/{namespace}-native-inputs.json").read_bytes(),
                         checks.evidence.canonical_bytes(inputs))

    def test_metadata_recovery_controller_drives_each_real_runner_mode_and_rejects_missing_proof(self):
        for namespace, mutation in (
                ("sqlite-recovery", None), ("category-sqlite-recovery", None),
                *(("sqlite-recovery", mutation) for mutation in (
                    "normal-exit", "missing-event", "wrong-receipt", "wrong-seed-record", "wrong-readback-record"))):
            root = self.directory / f"{namespace}-{mutation}"
            candidate = root / "candidate"
            assembly = candidate / checks.METADATA_RECOVERY / (
                "bin/Release/net10.0/Hoard.Fixtures.Metadata.CrashRunner.dll")
            assembly.parent.mkdir(parents=True)
            assembly.write_bytes(b"controller-unit-double")
            (root / "stores").mkdir()
            (root / "proofs").mkdir()
            invocations = []
            run = SimpleNamespace(root=root, command_sequence=0, live_children=lambda: ())

            def command(args, **options):
                run.command_sequence += 1
                invocations.append((args, options))
                value = options["stop_at_barrier"]
                receipt = {
                    "schemaVersion": 1, "sequence": run.command_sequence, "childPid": 200,
                    "childStartSha256": "a" * 64, "startedMs": 1000, "endedMs": 1200,
                    "exitCode": 0 if value is None or mutation == "normal-exit" else -9,
                    "diagnosticCode": "None", "groupState": "Exited", "scope": "recovery",
                }
                if ((mutation == "wrong-seed-record" and args[2].startswith("seed-"))
                        or (mutation == "wrong-readback-record" and args[2].startswith("recover-"))):
                    receipt["sequence"] += 1
                if value is not None:
                    receipt["barrier"] = {
                        "value": value + (mutation == "wrong-receipt"),
                        "observedMs": 1050, "signalMs": 1100,
                    }
                (root / f"proofs/recovery-command-{run.command_sequence:04}.json").write_text(json.dumps(receipt))
                events = () if mutation == "missing-event" else ({
                    "event": "test" if value is None else "barrier", "code": "None",
                    "value": 1 if value is None else value,
                },)
                return SimpleNamespace(exit_code=receipt["exitCode"], events=events)

            run.command = command
            inputs = {"profileId": "metadata", "mode": "diagnostic", "runtimeAssemblies": {
                assembly.relative_to(root).as_posix(): hashlib.sha256(assembly.read_bytes()).hexdigest()}}
            with self.subTest(mutation=mutation), patch.object(
                    checks, "require_sqlite_environment"), patch.object(checks, "verify_runtime_packages"):
                if mutation is not None:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError,
                                                "EvidenceIncomplete" if mutation == "missing-event" else "ProofMismatch"):
                        checks.metadata_recovery_diagnostics(run, inputs, candidate, namespace=namespace)
                    self.assertFalse((root / f"proofs/{namespace}.json").exists())
                    continue
                result = checks.metadata_recovery_diagnostics(run, inputs, candidate, namespace=namespace)
                self.assertFalse(result["qualification"])
                self.assertEqual(result["inputsSha256"], checks.evidence.digest(inputs))
                self.assertEqual([item["barrierId"] for item in result["barriers"]],
                                 ["M0", "M1", "M2", "U0", "U1", "U2", "U3", "U4", "R0", "R1"])
                self.assertEqual(len(invocations), 31)
                self.assertEqual([options["stop_at_barrier"] for _, options in invocations
                                  if options["stop_at_barrier"] is not None],
                                 [0, 1, 2, 10, 11, 12, 13, 14, 20, 21])
                self.assertEqual(invocations[-1][0][2], "recovery-walkthrough")
                for args, options in invocations:
                    self.assertEqual(args[:2], ["dotnet", str(assembly)])
                    self.assertEqual(options["scope"], "recovery")
                    self.assertEqual(options["env"], {"HOARD_CONFORMANCE_SAFE_EVENTS": "1"})
                    self.assertEqual(Path(args[3]).parent, Path(args[4]))
                    self.assertTrue(Path(args[4]).is_relative_to(root / f"stores/{namespace}"))
                    self.assertEqual(options["cache_id"], namespace)
                self.assertEqual(
                    json.loads((root / f"proofs/{namespace}.json").read_bytes()), result)

    def test_category_metadata_controls_reject_foreign_scope_before_executing(self):
        run = SimpleNamespace(root=self.directory, command=unittest.mock.Mock())
        for method, namespace in (
                (checks.metadata_recovery_diagnostics, "category-sqlite-recovery"),
                (checks.sqlite_noncooperation, "category-sqlite-native-noncooperation")):
            for inputs, selected in (
                    ({"profileId": "artifacts", "mode": "diagnostic"}, namespace),
                    ({"profileId": "metadata", "mode": "qualification"}, namespace),
                    ({"profileId": "metadata", "mode": "diagnostic"}, "../foreign"),
                    ({"profileId": "metadata", "mode": "diagnostic"}, "foreign")):
                with self.subTest(method=method.__name__, inputs=inputs, namespace=selected):
                    with self.assertRaises(checks.evidence.ConformanceError):
                        method(run, inputs, self.directory / "candidate", namespace=selected)
        run.command.assert_not_called()

    def test_local_recovery_uses_each_real_crash_boundary_without_borrowing_simulation_proof(self):
        self.assertTrue(callable(getattr(checks, "artifact_recovery_diagnostics", None)),
                        "Local needs actual owned crash/readback scopes, not metadata or simulation receipts.")
        root = self.directory
        candidate = root / "candidate"
        assembly = candidate / checks.ARTIFACT_RECOVERY / (
            "bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll")
        assembly.parent.mkdir(parents=True)
        assembly.write_bytes(b"local-controller-unit-double")
        (root / "stores").mkdir()
        (root / "proofs").mkdir()
        inputs = {"runtimeAssemblies": {
            assembly.relative_to(root).as_posix(): hashlib.sha256(assembly.read_bytes()).hexdigest()}}
        run = SimpleNamespace(root=root)
        with patch.object(checks, "verify_runtime_packages") as images, patch.object(
                checks, "recovery_command", return_value=("a" * 64, {"childStartSha256": "b" * 64})) as execute:
            result = checks.artifact_recovery_diagnostics(run, inputs, candidate)
            self.assertFalse(result["qualification"])
            self.assertEqual(result["inputsSha256"], checks.evidence.digest(inputs))
            self.assertEqual([item["barrierId"] for item in result["barriers"]],
                             ["B0", "B1", "B2", "B3", "D0", "D1"])
            self.assertEqual([item["value"] for item in result["barriers"]], list(range(40, 46)))
            self.assertEqual(execute.call_count, 12)
            for index, barrier in enumerate(("B0", "B1", "B2", "B3", "D0", "D1")):
                crash, recover = execute.call_args_list[index * 2:index * 2 + 2]
                self.assertEqual(crash.args[:2], (run, assembly))
                self.assertEqual(crash.args[2][0], "crash")
                self.assertEqual(recover.args[2][0], "recover")
                self.assertEqual(crash.args[2][1:], recover.args[2][1:])
                self.assertEqual(crash.args[2][3], barrier)
                self.assertEqual(str(uuid.UUID(crash.args[2][4])), crash.args[2][4])
                self.assertEqual(crash.kwargs["value"], 40 + index)
                self.assertNotIn("value", recover.kwargs)
            images.assert_called_once_with(
                assembly.parent, root / "feed/candidate", checks.ARTIFACT_RECOVERY_PACKAGES)
        with patch.object(checks, "verify_runtime_packages"), patch.object(checks, "recovery_command") as execute:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.artifact_recovery_diagnostics(
                    run, {"runtimeAssemblies": {assembly.relative_to(root).as_posix(): "0" * 64}}, candidate)
            execute.assert_not_called()

    def test_external_artifact_scope_preserves_frozen_rows_and_original_cross_process_ownership(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_external_scenarios", None)),
                        "All seventeen original external-proof wrappers need exact owned transport.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        prefixes = ("Hoard.Artifacts.Tests.ArtifactCrashTests.",
                    "Hoard.Artifacts.Tests.ArtifactNonCooperativeChildTests.",
                    "Hoard.Artifacts.Tests.ArtifactTransferProofTests.")
        admission = "Hoard.Artifacts.Tests.ArtifactAdmissionTests.Local_root_is_exclusively_owned_across_real_processes_not_a_lock_filename"
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefixes) or name == admission}
        scenario, = checks.original_artifact_external_scenarios()
        self.assertEqual(len(original), 16)
        self.assertEqual({name for name in scenario[1] if not name.startswith(
            "Hoard.Artifacts.Tests.ArtifactChildOutputTests.")}, original | {admission})
        self.assertEqual(len(scenario[1]), 21)
        candidate = self.directory / "candidate"
        runner = candidate / checks.ARTIFACT_RECOVERY / (
            "bin/Release/net10.0/Hoard.Fixtures.Artifacts.CrashRunner.dll")
        runner.parent.mkdir(parents=True)
        runner.write_bytes(b"external-wrapper-unit-double")
        assembly = candidate / checks.ARTIFACT_TESTS / checks.ARTIFACT_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Artifacts.Tests.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {
                assembly.relative_to(self.directory).as_posix(): "a" * 64,
                runner.relative_to(self.directory).as_posix(): hashlib.sha256(runner.read_bytes()).hexdigest()},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.kwargs["artifact_runner"], runner)
            manifest = launch.call_args.args[2]
            self.assertEqual({item["testIdentity"] for item in manifest["expected"]}, set(scenario[1]))
        runner.write_bytes(b"changed")
        with patch.object(checks, "runtime_command") as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            launch.assert_not_called()

    def test_artifact_race_scope_preserves_all_frozen_parameters_and_named_length_mutations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_race_scenarios", None)),
                        "Shared artifact publication races need exact owned wrapper transport.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(
                        "Hoard.Artifacts.Tests.ArtifactPublicationRaceTests.")}
        self.assertEqual(len(original), 6)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_conflicting_length_assertion_rejects_repaired_forgery_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_race_scenarios()
        self.assertEqual(scenario, ("original-artifact-races", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_reconciliation_scope_preserves_frozen_parameters_and_foreign_receipt_mutations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_reconciliation_scenarios", None)),
                        "Shared artifact reconciliation needs exact owned wrapper transport.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(
                        "Hoard.Artifacts.Tests.ArtifactReconciliationTests.")}
        self.assertEqual(len(original), 8)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_receipt_retry_assertion_rejects_foreign_receipt_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_reconciliation_scenarios()
        self.assertEqual(scenario, ("original-artifact-reconciliation", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_visibility_scope_preserves_frozen_rows_and_premature_acknowledgment_mutation(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_visibility_scenarios", None)),
                        "Shared direct/listing visibility needs exact owned wrapper transport.")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(
                        "Hoard.Artifacts.Tests.ArtifactVisibilityTests.")}
        self.assertEqual(len(original), 3)
        mutation = ("Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
                    "Shared_visibility_assertion_rejects_premature_acknowledgment_and_accepts_original_store")
        scenario, = checks.original_artifact_visibility_scenarios()
        self.assertEqual(scenario, ("original-artifact-visibility", tuple(sorted(original | {mutation})),
                                    "None", "Passed", 0, "None"))

    def test_artifact_history_scope_preserves_frozen_parameters_and_hidden_failure_mutations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_history_scenarios", None)),
                        "Shared history and budget checks need exact owned wrapper transport.")
        methods = {
            "Local_reclaimed_incarnations_remain_budgeted_until_expiry_without_removing_the_recreated_blob",
            "Reclaimed_identity_history_has_a_finite_budget_and_expiry_restores_new_digest_admission",
            "History_maintenance_bounds_examined_candidates_even_when_none_can_be_retired",
            "History_candidate_pages_resume_past_ineligible_entries_and_preserve_a_faulted_candidate",
            "Expired_ticket_history_restores_write_and_delete_capacity_without_losing_committed_or_removed_identity",
        }
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(", 1)[0] in {
                        f"Hoard.Artifacts.Tests.ArtifactBudgetTests.{method}" for method in methods}}
        self.assertEqual(len(original), 8)
        additional = {
            "Hoard.Artifacts.Tests.ArtifactBudgetTests."
            "Local_reclaimed_incarnations_remain_budgeted_until_expiry_without_removing_the_recreated_blob",
            *(
                "Hoard.Artifacts.Tests.ArtifactBudgetTests."
                "History_maintenance_bounds_examined_candidates_even_when_none_can_be_retired"
                f'(provider: "{provider}", kind: "{kind}")'
                for provider, kind in (
                    ("local", "tickets"), ("object", "tickets"), ("local", "dependencies"), ("object", "dependencies"),
                    ("local", "decisions"), ("object", "decisions"), ("local", "reclamation"))),
        }
        self.assertEqual(len(additional), 8)
        self.assertTrue(original.isdisjoint(additional))
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_history_resume_assertion_rejects_hidden_candidate_failure_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_history_scenarios()
        self.assertEqual(scenario, ("original-artifact-history", tuple(sorted(original | additional | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_ownership_scope_preserves_frozen_parameters_and_optimistic_cleanup_mutations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_ownership_scenarios", None)),
                        "Shared stream ownership needs exact owned wrapper transport.")
        methods = {
            "Hoard.Artifacts.Tests.ArtifactBudgetTests."
            "Producer_and_consumer_inactivity_deadlines_release_cooperative_work_without_closing_borrowed_streams",
            *(
                f"Hoard.Artifacts.Tests.ArtifactNonCooperationTests.{method}" for method in (
                    "Idle_read_expiry_fences_copy_without_touching_the_destination",
                    "Noncooperative_source_retains_bounded_ownership_and_blocks_admission_until_real_settlement",
                    "Noncooperative_destination_cannot_release_live_read_protection_via_close_or_dispose")),
        }
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(", 1)[0] in methods}
        self.assertEqual(len(original), 8)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_source_ownership_assertion_rejects_optimistic_cleanup_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_ownership_scenarios()
        self.assertEqual(scenario, ("original-artifact-ownership", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_local_artifact_session_scope_requires_unchanged_consumers_and_actual_ownership(self):
        factory = getattr(checks, "local_artifact_session_scenarios", None)
        self.assertTrue(callable(factory), "Owned Local sessions need exact package-only transport.")
        prefix = "Hoard.Fixtures.Conformance.Consumer.LocalArtifactSessionTests."
        identities = {
            prefix + f'Owned_local_projection_executes_unchanged_common_consumers(consumer: "{consumer}")'
            for consumer in ("publication", "expectations", "private-staging")}
        identities.update(prefix + method for method in (
            "All_typed_observation_points_can_be_registered_together_and_removed_without_overwrite",
            "Scoped_observation_cannot_overwrite_a_live_registration_or_remove_its_replacement",
            "Local_reopen_keeps_identity_authority_content_and_allocation_without_stale_disposal",
            "Physical_store_stop_cannot_release_a_live_authority_guard_or_erase_retained_observation",
            "Concurrent_disposers_join_one_attempt_and_the_same_actual_settlement",
            "Failed_initialization_retains_allocator_ownership_and_joins_actual_shutdown"))
        identities.update(prefix
            + "Released_boundary_stays_owned_through_actual_callback_and_reopen_or_disposal(reopen: " + value + ")"
            for value in ("False", "True"))
        for method, parameter in (
            ("Observer_failure_before_or_during_cleanup_remains_in_the_same_actual_settlement", "duringCleanup"),
            ("Concurrent_direct_stop_and_disposal_retry_reuse_the_pending_allocator_observation", "actualAllocator"),
        ):
            identities.update(prefix + method + f"({parameter}: {value})" for value in ("False", "True"))
        scenario, = factory()
        self.assertEqual(scenario, ("local-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"))

    def test_artifact_authority_ownership_scope_requires_all_live_settlement_cases(self):
        factory = getattr(checks, "artifact_authority_ownership_scenarios", None)
        self.assertTrue(callable(factory), "Owned artifact adapters need actual authority-quiescence transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactAuthorityOwnershipTests."
        identities = {
            prefix + "Shutdown_fence_joins_recognized_retained_and_queued_guards_before_reopen",
            prefix + "Shutdown_fence_joins_actual_noncooperating_reference_query_before_reopen",
            prefix + "Shutdown_fence_observes_canceled_waiter_without_losing_the_current_guard"}
        identities.update(prefix + "Released_operation_callback_remains_real_owned_work_until_final_settlement"
                          + f'(provider: "{provider}")' for provider in ("local", "object"))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-authority-ownership", tuple(sorted(identities)),
                                    "None", "Passed", 0, "None"))

    def test_object_artifact_session_scope_requires_fresh_epochs_and_actual_ownership(self):
        factory = getattr(checks, "object_artifact_session_scenarios", None)
        self.assertTrue(callable(factory), "Owned Object sessions need exact package-only transport.")
        prefix = "Hoard.Fixtures.Conformance.Consumer.ObjectArtifactSessionTests."
        identities = {
            prefix + f'Owned_object_projection_executes_unchanged_common_consumers(consumer: "{consumer}")'
            for consumer in ("publication", "expectations", "private-staging")}
        identities.update(prefix + method for method in (
            "All_typed_observations_register_together_and_stale_disposal_cannot_remove_a_replacement",
            "Object_restart_joins_old_authority_and_uses_fresh_epoch_authority_and_private_child",
            "Failed_replacement_keeps_the_original_as_cleanup_handle",
            "Failed_initialization_joins_actual_shutdown_without_erasing_foreign_content",
            "Cancellation_while_joining_old_authority_does_not_admit_a_replacement",
            "Cancellation_during_replacement_admission_retains_the_unpublished_generation",
            "Retained_authority_and_concurrent_disposers_retry_the_same_settlement"))
        for method, parameter in (
            ("Released_callback_stays_owned_until_restart_or_final_settlement", "restart"),
            ("Observer_failure_before_or_during_cleanup_faults_the_same_actual_settlement", "duringCleanup"),
            ("Direct_stop_and_disposal_retries_reuse_the_pending_allocator_observation", "actualAllocator"),
        ):
            identities.update(prefix + method + f"({parameter}: {value})" for value in ("False", "True"))
        scenario, = factory()
        self.assertEqual(scenario, ("object-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"))

    def test_artifact_observation_scope_requires_actual_independent_transition_cases(self):
        prefix = "Hoard.Artifacts.Tests.ArtifactObservationTests."
        identities = tuple(sorted(prefix + method + f'(provider: "{provider}")' for method in (
            "Persisted_receipt_boundary_exposes_the_same_actual_reconciled_receipt",
            "Failed_opened_read_callback_reclaims_real_stream_guard_and_single_transfer_slot",
            "Verified_reconciliation_callback_failure_keeps_actual_uncertain_publication_recoverable")
            for provider in ("local", "object")))
        scenario, = checks.artifact_observation_scenarios()
        self.assertEqual(scenario, ("original-artifact-observations", identities, "None", "Passed", 0, "None"))

    def test_configured_artifact_session_scope_requires_actual_limits_and_reference_queries(self):
        factory = getattr(checks, "configured_artifact_session_scenarios", None)
        self.assertTrue(callable(factory), "Configured artifact sessions need exact package-only transport.")
        prefix = "Hoard.Fixtures.Conformance.Consumer.ArtifactConfiguredSessionTests."
        identities = {
            prefix + method + f'(provider: "{provider}")' for method in (
                "Actual_configured_limits_survive_compatible_or_logical_reopen",
                "Current_reference_queries_fence_deletion_on_each_actual_generation",
                "Unavailable_reference_query_cannot_become_an_optimistic_zero_reference_decision")
            for provider in ("local", "object")}
        identities.add(prefix + "Invalid_reference_observations_cannot_admit_negative_counts_or_missing_available_revisions")
        identities.update(prefix
            + f'Timed_out_reference_query_stays_owned_through_reopen_or_final_settlement(provider: "{provider}", reopen: {reopen})'
            for provider in ("local", "object") for reopen in ("False", "True"))
        scenario, = factory()
        self.assertEqual(scenario, ("configured-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"))

    def test_payload_artifact_scope_requires_real_corruption_and_native_handle_ownership(self):
        factory = getattr(checks, "payload_artifact_session_scenarios", None)
        self.assertTrue(callable(factory), "Payload controls need exact owned native-work transport.")
        prefix = "Hoard.Fixtures.Conformance.Consumer.ArtifactPayloadSessionTests."
        identities = {
            prefix + f'Actual_payload_damage_invalidates_copy_and_later_open(provider: "{provider}", truncate: {truncate})'
            for provider in ("local", "object") for truncate in ("False", "True")}
        identities.update(prefix
            + f'Held_native_payload_handle_stays_owned_through_reopen_or_final_settlement(provider: "{provider}", reopen: {reopen})'
            for provider in ("local", "object") for reopen in ("False", "True"))
        identities.update(prefix + f'Foreign_incarnation_cannot_damage_current_payload(provider: "{provider}")'
                          for provider in ("local", "object"))
        identities.update(prefix + method + f'(provider: "{provider}")' for method in (
            "Failed_damage_observer_preserves_bytes_and_faults_final_settlement",
            "Removed_incarnation_cannot_damage_same_digest_replacement",
            "Stale_session_cannot_damage_reopened_payload",
            "Incompatible_open_read_handle_rejects_damage_without_changing_bytes")
            for provider in ("local", "object"))
        identities.update(prefix
            + f'Empty_payload_damage_is_explicit_and_never_false_success(provider: "{provider}", truncate: {truncate})'
            for provider in ("local", "object") for truncate in ("False", "True"))
        identities.add(prefix + "Object_old_epoch_cannot_damage_current_incarnation")
        scenario, = factory()
        self.assertEqual(scenario, ("payload-artifact-session", tuple(sorted(identities)), "None", "Passed", 0, "None"))

    def test_owned_artifact_scopes_discover_their_actual_distinct_assemblies(self):
        candidate = self.directory / "candidate"
        for scenario, folder, assembly_name in (
                (checks.artifact_authority_ownership_scenarios()[0], checks.ARTIFACT_TESTS, "Hoard.Artifacts.Tests.dll"),
                (checks.local_artifact_session_scenarios()[0], checks.ARTIFACT_CONSUMER,
                 "Hoard.Fixtures.Conformance.Consumer.dll"),
                (checks.object_artifact_session_scenarios()[0], checks.ARTIFACT_CONSUMER,
                 "Hoard.Fixtures.Conformance.Consumer.dll"),
                (checks.configured_artifact_session_scenarios()[0], checks.ARTIFACT_CONSUMER,
                 "Hoard.Fixtures.Conformance.Consumer.dll"),
                (checks.payload_artifact_session_scenarios()[0], checks.ARTIFACT_CONSUMER,
                 "Hoard.Fixtures.Conformance.Consumer.dll")):
            output = checks.ARTIFACT_TEST_OUTPUT if folder == checks.ARTIFACT_TESTS else checks.PACKAGE_TEST_OUTPUT
            assembly = candidate / folder / output / "Release/net10.0" / assembly_name
            inputs = {
                "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
                "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
            }
            with self.subTest(scope=scenario[0]), patch.object(
                    checks, "runtime_command", side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
                launch.assert_called_once()
                self.assertEqual(launch.call_args.args[1], assembly)
                self.assertEqual(launch.call_args.args[2]["purpose"], "discovery")
                self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, set(scenario[1]))

    def test_owned_artifact_consumer_builds_real_bindings_before_its_isolated_locked_runtime(self):
        run = SimpleNamespace(root=self.directory)
        candidate = self.directory / "candidate"
        config = self.directory / "NuGet.Config"
        feed = self.directory / "feed"
        with patch.object(checks, "prepare_project_lock", return_value=(None, None)) as prepare, \
                patch.object(checks, "build") as build, \
                patch.object(checks, "_original_wrapper_runtime") as runtime:
            checks.build_artifact_assertion_consumer(run, candidate, config, feed)
        projects = [
            candidate / f"tests/fixtures/conformance/Bindings/{name}/{name}.csproj"
            for name in ("Local", "ObjectSemantics")]
        projects.append(candidate / checks.ARTIFACT_CONSUMER / "Consumer.csproj")
        self.assertEqual([call.args[0] for call in prepare.call_args_list], projects)
        self.assertEqual([call.args[1] for call in build.call_args_list], projects)
        for call, name in zip(build.call_args_list[:2], ("Local", "ObjectSemantics")):
            self.assertEqual(call.kwargs["feed"], feed)
            self.assertEqual(call.kwargs["package_id"], "Hoard.Fixtures.Conformance.Bindings." + name)
        consumer = build.call_args_list[-1]
        self.assertEqual(consumer.args[3], "artifact-consumer-locked-replay")
        self.assertEqual(consumer.kwargs["properties"], (
            "-p:BaseOutputPath=bin/package-diagnostic/", "-p:ConformanceCategoryMutations=true"))
        self.assertNotIn("feed", consumer.kwargs)
        runtime.assert_called_once_with(candidate, feed, checks.ARTIFACT_CONSUMER,
                                        checks.PACKAGE_TEST_OUTPUT, checks.ARTIFACT_CONSUMER_PACKAGES)

    def test_incomplete_or_foreign_owned_local_vectors_never_launch(self):
        for scenario in (*checks.local_artifact_session_scenarios(), *checks.object_artifact_session_scenarios(),
                         *checks.configured_artifact_session_scenarios(), *checks.payload_artifact_session_scenarios()):
            name, identities, *outcome = scenario
            for invalid in (identities[:-1], identities + ("Foreign.Test",),
                            ("Foreign.Test", *identities[1:])):
                with self.subTest(scope=name, vector=invalid), patch.object(checks, "runtime_command") as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                        checks.test_attempt(SimpleNamespace(root=self.directory), {}, self.directory / "candidate",
                                            (name, invalid, *outcome))
                    launch.assert_not_called()

    def test_artifact_configured_store_scope_preserves_all_frozen_host_selection_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_configured_store_scenarios", None)),
                        "Shared configured-store checks need exact owned host wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactCompositionTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefix)}
        self.assertEqual(len(original), 4)
        scenario, = checks.original_artifact_configured_store_scenarios()
        self.assertEqual(scenario, ("original-artifact-configured-store", tuple(sorted(original)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_object_cleanup_scope_preserves_all_frozen_residual_ownership_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_object_cleanup_scenarios", None)),
                        "Shared object cleanup checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactFailureTests."
        methods = (
            "Reused_object_receipt_survives_failed_unselected_assembly_cleanup",
            "Unselected_object_cleanup_retains_exact_ownership_and_blocks_retry_until_reclaimed")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if any(name == prefix + method or name.startswith(
                        prefix + method + "(") for method in methods)}
        self.assertEqual(len(original), 5)
        scenario, = checks.original_artifact_object_cleanup_scenarios()
        self.assertEqual(scenario, ("original-artifact-object-cleanup", tuple(sorted(original)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_prefix_cleanup_scope_preserves_all_frozen_reclamation_and_stop_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_prefix_cleanup_scenarios", None)),
                        "Shared prefix cleanup checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactFailureTests."
        methods = (
            "Committed_receipts_remain_reconcilable_while_exact_residual_staging_is_reclaimed",
            "Failed_prefix_reclamation_retains_ownership_until_exact_bounded_cleanup",
            "Stop_retains_failed_prefix_ownership_until_reclamation_can_settle")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if any(name.startswith(prefix + method + "(") for method in methods)}
        self.assertEqual(len(original), 6)
        scenario, = checks.original_artifact_prefix_cleanup_scenarios()
        self.assertEqual(scenario, ("original-artifact-prefix-cleanup", tuple(sorted(original)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_failure_scope_preserves_frozen_classification_and_reconciliation_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_failure_scenarios", None)),
                        "Shared failure checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactFailureTests."
        methods = (
            "Storage_failures_remain_distinct_and_sanitized_and_do_not_publish_partial_content",
            "Unexpected_fault_after_visibility_requires_exact_ticket_reconciliation")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if any(name.startswith(prefix + method + "(") for method in methods)}
        self.assertEqual(len(original), 4)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            + f'Shared_storage_failure_assertion_rejects_misclassified_denial_and_accepts_original_store(provider: "{provider}")'
            for provider in ("local", "object")}
        scenario, = checks.original_artifact_failure_scenarios()
        self.assertEqual(scenario, ("original-artifact-failure", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_lifecycle_scope_preserves_frozen_and_additional_shutdown_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_lifecycle_scenarios", None)),
                        "Shared lifecycle checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactNonCooperationTests."
        methods = (
            "Concurrent_close_waits_for_the_same_physical_guard_release_and_fences_new_copy",
            "Deadline_and_stop_return_while_a_native_io_boundary_holds_provider_state")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if any(name.startswith(prefix + method + "(") for method in methods)}
        self.assertEqual(len(original), 4)
        additional = {prefix + "Composed_shutdown_cannot_release_store_while_authority_retains_a_reference_query"
                      + f'(provider: "{provider}")' for provider in ("local", "object")}
        self.assertTrue(original.isdisjoint(additional))
        scenario, = checks.original_artifact_lifecycle_scenarios()
        self.assertEqual(scenario, ("original-artifact-lifecycle", tuple(sorted(original | additional)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_metadata_bridge_scope_preserves_frozen_and_additional_evidence_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_metadata_bridge_scenarios", None)),
                        "Shared metadata bridge checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactMetadataAuthorityTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefix)}
        self.assertEqual(len(original), 1)
        additional = {prefix + name for name in (
            "Bridge_binds_exact_evidence_and_keeps_recognized_shared_protection_until_metadata_settlement",
            "Foreign_malformed_expired_and_unrecognized_evidence_cannot_publish_metadata_or_leak_a_guard")}
        self.assertTrue(original.isdisjoint(additional))
        scenario, = checks.original_artifact_metadata_bridge_scenarios()
        self.assertEqual(scenario, ("original-artifact-metadata-bridge", tuple(sorted(original | additional)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_metadata_integration_scope_preserves_all_four_actual_combinations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_metadata_integration_scenarios", None)),
                        "Shared metadata/artifact integration checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactMetadataIntegrationTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefix)}
        self.assertEqual(len(original), 16)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_metadata_reference_assertion_rejects_hidden_denial_and_accepts_original_stores"
            f'(provider: "{provider}", metadataProvider: "{metadata}")'
            for provider in ("local", "object") for metadata in ("sqlite", "memory")}
        scenario, = checks.original_artifact_metadata_integration_scenarios()
        self.assertEqual(scenario, ("original-artifact-metadata-integration", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_capability_scope_preserves_frozen_gaps_and_existing_complete_profiles(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_capability_scenarios", None)),
                        "Shared capability checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactCapabilityTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefix)}
        self.assertEqual(len(original), 16)
        additional = {
            prefix + "Complete_capability_profile_accepts_configured_limits_and_keeps_ranges_optional"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        self.assertTrue(original.isdisjoint(additional))
        scenario, = checks.original_artifact_capability_scenarios()
        self.assertEqual(scenario, ("original-artifact-capability", tuple(sorted(original | additional)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_authority_scope_preserves_frozen_and_additional_recognized_handle_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_authority_scenarios", None)),
                        "Shared authority checks need exact owned wrapper transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactAuthorityTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(prefix)}
        self.assertEqual(len(original), 3)
        additional = {prefix + name for name in (
            "Shared_admission_retention_and_independent_disposal_use_one_recognized_handle",
            "Missing_reference_authority_denies_deletion_not_shared_reads",
            "Noncooperative_reference_query_retains_exclusion_blocks_admission_and_settles_before_release")}
        self.assertTrue(original.isdisjoint(additional))
        mutation = prefix + "Shared_authority_assertion_rejects_repaired_copied_handle_and_accepts_original_authority"
        scenario, = checks.original_artifact_authority_scenarios()
        self.assertEqual(scenario, ("original-artifact-authority", tuple(sorted(original | additional | {mutation})),
                                    "None", "Passed", 0, "None"))

    def test_artifact_budget_scope_preserves_frozen_admission_cleanup_and_authority_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_budget_scenarios", None)),
                        "Shared finite-budget checks need exact owned wrapper transport.")
        methods = {
            "Failed_unclaimed_result_cleanup_blocks_admission_and_stop_until_exact_retry",
            "Cancelled_commit_before_decision_fences_the_ticket_and_cannot_publish_on_retry",
            "Full_transfer_queue_rejects_without_input_io_and_capacity_returns_after_release",
            "Cap_crossing_rejects_excess_before_append_and_capacity_recovers",
            "Total_deadline_includes_shared_authority_contention_before_publication",
            "Cooperative_cancellation_stops_input_without_disposing_borrowed_stream"}
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(", 1)[0].split(".")[-1] in methods}
        self.assertEqual(len(original), 16)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_cap_assertion_rejects_misclassified_limit_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_budget_scenarios()
        self.assertEqual(scenario, ("original-artifact-budget", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_handoff_scope_preserves_all_frozen_results_and_actual_discard_mutations(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_handoff_scenarios", None)),
                        "Shared result-handoff checks need exact owned wrapper transport.")
        methods = {
            "Cancellation_after_resource_release_cannot_retain_an_already_settled_operation",
            "Cancellation_at_result_handoff_cannot_discard_a_reserved_ticket_or_live_read",
            "Cancellation_before_result_handoff_reclaims_the_unclaimed_ticket_or_read",
            "Undelivered_verified_staging_is_reclaimed_after_ownership_expiry"}
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(", 1)[0].split(".")[-1] in methods}
        self.assertEqual(len(original), 12)
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_result_handoff_assertion_rejects_discarded_reservation_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_handoff_scenarios()
        self.assertEqual(scenario, ("original-artifact-handoff", tuple(sorted(original | mutations)),
                                    "None", "Passed", 0, "None"))

    def test_artifact_cancellation_scope_preserves_frozen_and_additional_current_owner_cases(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_cancellation_scenarios", None)),
                        "Shared cancellation/current-owner checks need exact owned wrapper transport.")
        method = ("Hoard.Artifacts.Tests.ArtifactBudgetTests."
                  "Cancellation_of_an_admitted_commit_cannot_fence_an_externally_renewed_owner")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        original = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(", 1)[0] == method}
        self.assertEqual(len(original), 2)
        additional = {
            "Hoard.Artifacts.Tests.ArtifactBudgetTests.Cancellation_after_progress_renewal_fences_the_same_admitted_owner"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        additional.update(
            "Hoard.Artifacts.Tests.ArtifactBudgetTests.Cancelled_invalid_or_stale_commit_cannot_fence_the_current_verified_handle"
            f'(provider: "{provider}", alteration: "{alteration}")'
            for provider in ("local", "object") for alteration in ("renewed", "completion", "handle"))
        self.assertEqual(len(additional), 8)
        self.assertTrue(original.isdisjoint(additional))
        mutations = {
            "Hoard.Artifacts.Tests.ArtifactPublicationConsumerTests."
            "Shared_cancelled_descriptor_assertion_rejects_abandoned_current_owner_and_accepts_original_store"
            f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = checks.original_artifact_cancellation_scenarios()
        self.assertEqual(scenario, ("original-artifact-cancellation", tuple(sorted(original | additional | mutations)),
                                    "None", "Passed", 0, "None"))

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

    def test_original_observation_scopes_select_frozen_bindings_images_and_context_before_launch(self):
        self.assertTrue(callable(getattr(checks, "original_observation_scenarios", None)),
                        "Actual original observations must join captured native inputs, not minimal diagnostic labels.")
        candidate = self.directory / "candidate"
        assignments = checks.original_observation_inputs(candidate, self.directory)
        runtime = {path: "a" * 64 for witnesses in assignments.values()
                   for identity, selected in witnesses.items()
                   for roles in checks.evidence.original_node_assignments(identity, selected)
                   for path, _ in roles.values()}
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": runtime,
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
            "bindings": [{"bindingId": binding} for binding in assignments],
        }
        (self.directory / "stores").mkdir()
        (self.directory / "runtime-owner.json").write_bytes(b"{}")
        run = SimpleNamespace(root=self.directory)
        scenarios = checks.original_observation_scenarios()
        self.assertEqual(len(scenarios), 7)
        self.assertEqual(sum(len(scenario[1]) for scenario in scenarios), 333)
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_bytes())
        expected_metadata = {name for entry in frozen["entries"] if entry["profileId"] == "metadata"
                             for name in entry["runtimeTests"] if name.startswith((
                                 "Hoard.Metadata.Tests.MetadataPublicationTests.",
                                 "Hoard.Metadata.Tests.MetadataRelationshipTests.",
                                 "Hoard.Metadata.Tests.MetadataIdentityTests.",
                                 "Hoard.Metadata.Tests.MetadataRoundTripTests.",
                                 "Hoard.Metadata.Tests.MetadataAtomicityTests.",
                                 "Hoard.Metadata.Tests.MetadataDeadlineTests.",
                                 "Hoard.Metadata.Tests.MetadataAdmissionTests.",
                                 "Hoard.Metadata.Tests.MetadataHostIntegrationTests.",
                                 "Hoard.Metadata.Tests.MetadataSchemaTests.",
                                 "Hoard.Metadata.Tests.MetadataReconciliationTests.",
                                 "Hoard.Metadata.Tests.MetadataFailureTests.MP20_",
                                 "Hoard.Metadata.Tests.MetadataFailureTests.MP21_",
                                 "Hoard.Metadata.Tests.MetadataFailureTests.MP22_",
                                 "Hoard.Metadata.Tests.MetadataPagingTests.MP07_",
                                 "Hoard.Metadata.Tests.MetadataPagingTests.MP08_Malformed_",
                                 "Hoard.Metadata.Tests.MetadataPagingTests.MP08_Continuation_",
                                 "Hoard.Metadata.Tests.MetadataLeaseTests.MP28_",
                                 "Hoard.Metadata.Tests.MetadataLeaseTests.MP29_",
                                 "Hoard.Metadata.Tests.MetadataLeaseTests.MP30_"))}
        self.assertEqual(set(scenarios[0][1]), expected_metadata)
        self.assertEqual(set(scenarios[1][1]), expected_metadata)
        expected_artifacts = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                              for name in entry["runtimeTests"]
                              if name.startswith(tuple("Hoard.Artifacts.Tests." + prefix for prefix in (
                                  "ArtifactPublicationTests.", "ArtifactDeletionTests.", "ArtifactReconciliationTests.",
                                  "ArtifactReadVerificationTests.",
                                  "ArtifactPublicationRaceTests.",
                                  "ArtifactEvidenceTests.",
                                  "ArtifactVisibilityTests.",
                                  "ArtifactCapabilityTests.",
                                  "ArtifactAdmissionTests.",
                                  "ArtifactMetadataIntegrationTests.",
                                  "ArtifactCompositionTests.",
                                  "ArtifactNonCooperationTests.",
                                  "ArtifactFailureTests.",
                                  "ArtifactBudgetTests.",
                                  "ArtifactRecoveryTests."))) and (
                                      not any(part in name for part in (
                                          ".ArtifactRecoveryTests.",))
                                      or '(provider: "' in name
                                      or ".Stop_retains_unselected_object_" in name)}
        self.assertEqual(set(scenarios[2][1]), expected_artifacts)
        expected_contracts = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                              for name in entry["runtimeTests"] if name.startswith((
                                  "Hoard.Artifacts.Tests.ArtifactValueTests.",
                                  "Hoard.Artifacts.Tests.ArtifactContractTests."))}
        self.assertEqual(set(scenarios[3][1]), expected_contracts)
        self.assertEqual(set(scenarios[4][1]), expected_contracts)
        expected_shared = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                           for name in entry["runtimeTests"] if name.startswith((
                               "Hoard.Artifacts.Tests.ArtifactAuthorityTests.",
                               "Hoard.Artifacts.Tests.ArtifactMetadataAuthorityTests."))}
        self.assertEqual(set(scenarios[5][1]), expected_shared)
        self.assertEqual(set(scenarios[6][1]), expected_shared)
        for scenario in scenarios:
            metadata = "-metadata-" in scenario[0]
            provider = scenario[0].rsplit("-", 1)[1] if metadata or any(
                marker in scenario[0] for marker in ("-contract-", "-shared-")) else None
            with self.subTest(scope=scenario[0]), patch.object(checks, "require_sqlite_environment") as admission:
                with patch.object(checks, "runtime_command",
                                  side_effect=checks.evidence.ConformanceError("DeadlineExceeded")) as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "DeadlineExceeded"):
                        checks.test_attempt(run, inputs, candidate, scenario)
                    manifest = launch.call_args.args[2]
                    assembly = launch.call_args.args[1]
                    self.assertEqual(manifest["runInputsPath"], "proofs/original-run-inputs.json")
                    self.assertEqual(manifest["inputSha256"], checks.evidence.digest(inputs))
                    self.assertEqual({entry["testIdentity"] for entry in manifest["expected"]}, set(scenario[1]))
                    self.assertEqual(launch.call_args.kwargs, {
                        "original_observations": True, **({"metadata_provider": provider} if metadata else {})})
                    for entry in manifest["expected"]:
                        matches = {case.binding_id for case in checks.category_cases()
                                   if case.profile_id == ("metadata" if metadata else "artifacts")
                                   and entry["testIdentity"] in case.witnesses}
                        if provider is None:
                            self.assertEqual(len(matches), 1)
                        binding = provider if provider is not None else matches.pop()
                        self.assertEqual(entry["bindingId"], binding)
                        cases = [case.case_id for case in checks.category_cases()
                                 if case.binding_id == binding and case.exclusion is None
                                 and entry["testIdentity"] in case.witnesses]
                        self.assertEqual(entry["caseId"], min(cases))
                        nodes = checks.evidence.original_node_assignments(
                            entry["testIdentity"], assignments[binding][entry["testIdentity"]])
                        kind = checks.original_witness_policy(entry["testIdentity"])[1]
                        self.assertIn(nodes[0][
                            "contract" if kind == "loaded-contract" else "owner" if kind == "original-owner" else "store"][0],
                                      {item["path"] for item in manifest["assemblies"]})
                        roles = nodes[0]
                        self.assertEqual(set(roles), set(checks.original_witness_policy(entry["testIdentity"])[2]))
                        self.assertTrue({path for path, _ in roles.values()} <= {
                            item["path"] for item in manifest["assemblies"]})
                        for node in nodes:
                            self.assertTrue({path for path, _ in node.values()} <= {
                                item["path"] for item in manifest["assemblies"]})
                        if not metadata and any(parent is not None for parent in checks.original_witness_parents(
                                entry["testIdentity"])):
                            self.assertIsNone(nodes[0]["owner"][1])
                            self.assertEqual(nodes[1]["owner"][1], "Hoard.Fixtures.Artifacts.Local")
                            with self.assertRaisesRegex(checks.evidence.ConformanceError, "EvidenceIncomplete"):
                                checks.evidence.original_node_assignments(entry["testIdentity"], nodes[0])
                        if any(f".{fixture}." in entry["testIdentity"] for fixture in (
                                "ArtifactCapabilityTests", "ArtifactAdmissionTests")):
                            self.assertEqual(roles["owner"], roles["store"])
                            self.assertEqual(roles["owner"][1], "Hoard.Fixtures.Artifacts." + (
                                "Local" if binding == "local" else "ObjectSemantics"))
                        if ".Concurrent_close_waits_" in entry["testIdentity"]:
                            self.assertIsNone(roles["authority"][1])
                            self.assertTrue(roles["authority"][0].endswith("/Hoard.Artifacts.Tests.dll"))
                        if any(f".{fixture}." in entry["testIdentity"] for fixture in (
                                "ArtifactMetadataIntegrationTests", "ArtifactCompositionTests")):
                            self.assertEqual(roles["owner"][1], "Hoard.Fixtures.Artifacts.HostAdapters")
                            if kind == "original-instance":
                                self.assertEqual(roles["controls"][1], "Hoard.Fixtures.Artifacts." + (
                                    "Local" if binding == "local" else "ObjectSemantics"))
                            if ".ArtifactCompositionTests." in entry["testIdentity"]:
                                self.assertEqual(checks.original_witness_parents(entry["testIdentity"]),
                                                 (None,) if kind == "original-owner" else (None, None))
                        if kind == "original-owner":
                            self.assertEqual(set(roles), {"owner"})
                            self.assertEqual(roles["owner"][1], "Hoard.Fixtures.Artifacts.HostAdapters")
                        if metadata:
                            facade = any(part in entry["testIdentity"] for part in (
                                "MetadataPublicationTests.", "MetadataRelationshipTests.",
                                "MetadataIdentityTests.MP02_", "MetadataIdentityTests.MP03_",
                                "MetadataRoundTripTests.MP01_", "MetadataReconciliationTests.MP14_",
                                "MetadataFailureTests.MP21_Corrupt_query_",
                                "MetadataPagingTests.MP07_All_seven_", "MetadataPagingTests.MP07_Oversized_"))
                            authority = roles["authority"]
                            self.assertEqual(authority[1], None if facade else "Hoard.Fixtures.Metadata.HostAdapters")
                            self.assertTrue(authority[0].endswith(
                                "/Hoard.Metadata.Tests.dll" if facade else "/Hoard.Fixtures.Metadata.HostAdapters.dll"))
                            self.assertEqual(roles["owner"][1], None if ".MetadataSchemaTests." in entry["testIdentity"]
                                             else "Hoard.Fixtures.Metadata.HostAdapters")
                    self.assertEqual(assembly.name, "Hoard.Metadata.Tests.dll" if metadata else "Hoard.Artifacts.Tests.dll")
                    if provider == "sqlite" or any('metadataProvider: "sqlite"' in name for name in scenario[1]):
                        admission.assert_called_once_with(inputs, assembly, self.directory)
                with patch.object(run, "command", create=True,
                                  side_effect=checks.evidence.ConformanceError("DeadlineExceeded")) as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "DeadlineExceeded"):
                        checks.runtime_command(run, assembly, manifest, **{
                            "original_observations": True, **({"metadata_provider": provider} if metadata else {})})
                    settings = ET.fromstring((
                        self.directory / "stores" / f"settings-{manifest['attemptId']}.runsettings").read_bytes())
                    encoded = settings.find("./RunConfiguration/EnvironmentVariables/HOARD_ORIGINAL_CONTEXT").text
                    context = checks.evidence.load_json(base64.b64decode(encoded))
                    self.assertEqual(context, {"schemaVersion": 1, "runId": inputs["runId"], "cases": {
                        entry["testIdentity"]: {"bindingId": entry["bindingId"], "caseId": entry["caseId"]}
                        for entry in manifest["expected"]}})
            for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                            ("observed-original-provider-selected", *scenario[1:])):
                with patch.object(checks, "runtime_command") as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                        checks.test_attempt(run, {}, candidate, changed)
                    launch.assert_not_called()

    def test_original_observation_scope_cannot_pass_without_each_original_execution_proof(self):
        self.assertTrue(callable(getattr(checks, "validate_original_observations", None)),
                        "Successful diagnostics cannot substitute for observed original execution proofs.")
        identity = ("Hoard.Metadata.Tests.MetadataRoundTripTests."
                    "MP01_Every_entity_round_trips_and_invalid_relationships_leave_no_changes")
        execution = str(uuid.uuid4())
        observation = {"kind": "original-instance", "operation": "create", "parentObservationId": None}
        ingested = {
            "witnesses": [{"testIdentity": identity, "executionId": execution}],
            "sessionOrigins": {execution: ()}, "originalObservations": {execution: (observation,)},
        }
        checks.validate_original_observations(ingested)
        for changes in (
                {"originalObservations": {}},
                {"originalObservations": {execution: ()}},
                {"originalObservations": {execution: (observation, observation)}},
                {"originalObservations": {execution: (observation | {"kind": "loaded-contract"},)}},
                {"originalObservations": {execution: (observation | {"parentObservationId": str(uuid.uuid4())},)}},
                {"sessionOrigins": {execution: ({"unrelated": "typed-origin"},)}}):
            with self.subTest(changes=changes), self.assertRaisesRegex(
                    checks.evidence.ConformanceError, "WitnessMissing"):
                checks.validate_original_observations(ingested | changes)

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

    def test_quarantine_extraction_preserves_transitive_original_assertions_and_wrapper_ownership(self):
        sdk = ROOT / "tests/contracts/Hoard.Testing.Conformance/Artifacts/ArtifactEvidenceAssertions.cs"
        text = sdk.read_text()
        start = text.index("{", text.index("public static async Task QuarantineIsPermanentAsync("))
        body = text[start:text.index("\n    }", start) + 6]
        # Preserve the entire d7ef7cc^ helper after explicit interface/factory/token forwarding.
        self.assertEqual(hashlib.sha256("".join(body.split()).encode()).hexdigest(),
                         "9b54ea0c474c6d0aad0fb3616b338244e6e25add2c6c4f28ebf9d9bcd47677e2")
        for filename, method in (
            ("ArtifactEvidenceAssertions.cs", "QuarantineIsPermanentAsync"),
            ("ArtifactReadAssertions.cs", "DamagedReadAsync"),
            ("ArtifactReadAssertions.cs", "CommittedDetectionQuarantineAsync"),
            ("ArtifactPublicationAssertions.cs", "CorruptExistingContentAsync"),
        ):
            with self.subTest(method=method):
                text = (sdk.parent / filename).read_text()
                start = text.index("public static async Task " + method + "(")
                self.assertNotIn("reopen = null", text[start:text.index("{", start)])
        cases = ROOT / "tests/contracts/Hoard.Artifacts.Tests/Cases"
        for filename, method in (
            ("ArtifactReadVerificationTests.cs", "Every_committed_detection_path_quarantines_restored_bytes"),
            ("ArtifactReadVerificationTests.cs", "Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence"),
            ("ArtifactPublicationRaceTests.cs", "Corrupt_existing_bytes_are_not_overwritten_or_reused"),
        ):
            with self.subTest(method=method):
                text = (cases / filename).read_text()
                start = text.index("public async Task " + method + "(")
                body = text[start:text.index("\n    }", start)]
                self.assertIn("ArtifactEvidenceTests.QuarantineReopen(driver, observations)", body)
        text = (cases / "ArtifactEvidenceTests.cs").read_text()
        for method in (
            "Local_failed_quarantine_persistence_retains_ownership_until_stop_retry_and_reopen",
            "Validation_first_corruption_cannot_be_revived_by_external_restoration",
        ):
            with self.subTest(method=method):
                start = text.index("public async Task " + method + "(")
                self.assertIn("QuarantineReopen(driver, observations)", text[start:text.index("\n    }", start)])
        text = sdk.read_text()
        for method in ("FailedQuarantinePersistenceAsync", "ValidationFirstCorruptionAsync"):
            with self.subTest(method=method):
                start = text.index("public static async Task " + method + "(")
                body = "".join(text[start:text.index("\n    }", start)].split())
                self.assertIn("awaitQuarantineIsPermanentAsync(store,receipt,bytes,cancellationToken,reopen);", body)

    def test_full_artifact_origins_pin_every_actual_role_to_its_independent_archive(self):
        factory = getattr(checks, "artifact_origin_inputs", None)
        self.assertTrue(callable(factory), "Full artifact origins must bind actual component roles, not labels.")
        candidate = self.directory / "candidate"
        runtime = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / "Release/net10.0"
        expected = {}
        for provider, adapter in (("local", "Local"), ("object", "ObjectSemantics")):
            binding = "Hoard.Fixtures.Conformance.Bindings." + adapter
            store = "Hoard.Fixtures.Artifacts." + adapter
            expected["fixture.artifact." + provider] = {
                role: ((runtime / (package + ".dll")).relative_to(self.directory).as_posix(), package)
                for role, package in (
                    ("factory", binding), ("session", binding), ("faults", binding), ("authority", binding),
                    ("store", store), ("validator", store), ("maintenance", store), ("lifetime", store))}
        self.assertEqual(factory(candidate, self.directory), expected)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            factory(candidate, candidate / "foreign")

    def test_full_metadata_origins_require_both_independent_factories_and_actual_role_images(self):
        factory = getattr(checks, "metadata_origin_inputs", None)
        self.assertTrue(callable(factory), "Metadata origins require actual factory and provider image assignments.")
        candidate = self.directory / "candidate"
        runtime = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / "Release/net10.0"
        expected = {}
        for provider, adapter in (("memory", "Memory"), ("sqlite", "Sqlite")):
            binding = "Hoard.Fixtures.Conformance.Bindings." + adapter
            store = "Hoard.Fixtures.Metadata." + adapter
            expected["fixture.metadata." + provider] = {
                role: ((runtime / (package + ".dll")).relative_to(self.directory).as_posix(), package)
                for role, package in (
                    ("factory", binding), ("session", binding), ("faults", binding), ("authority", binding),
                    ("store", store), ("schema", store))}
        self.assertEqual(factory(candidate, self.directory), expected)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            factory(candidate, candidate / "foreign")

    def test_full_metadata_scope_admits_exact_common_work_and_rejects_missing_images_or_packages(self):
        method = ("Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
                  "Observed_factories_execute_unchanged_common_consumers_with_actual_origins")
        expected = {f'{method}(provider: "{provider}", consumer: "{consumer}")'
                    for provider in ("memory", "sqlite") for consumer in (
                        "capacity", "writer", "publication", "entities", "graph", "independent",
                        "atomic", "grouped", "lease-generation", "lease-fences",
                        "lease-renew", "lease-release", "lease-guard",
                        "text", "registry", "authorization", "references", "reference-aba", "telemetry",
                        "create-race", "revision-race", "reconcile-writer", "reconcile-io",
                        "reconcile-ack", "contributions", "receipts", "layout-empty", "layout-partial",
                        "bounds", "scopes", "page-kinds", "page-size", "page-datasets",
                        "time-ticket", "time-lease", "cancel", "queue", "exceptions", "ledger", "diagnostics",
                        "evidence", "publication-replay", "publication-orphan", "corrupt-groups", "corrupt-pages",
                        "admission", "invalid-budget", "incomplete-cleanup", "disposal")}
        reopen = ("Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
                  "Observed_reopen_preserves_public_state_and_fences_stale_controls")
        expected.update(f'{reopen}(provider: "{provider}")' for provider in ("memory", "sqlite"))
        schema = ("Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
                  "Observed_schema_consumers_preserve_actual_reopen_lineage")
        expected.update(f'{schema}(provider: "{provider}", consumer: "{consumer}")'
                        for provider in ("memory", "sqlite") for consumer in (
                            "upgrade", "upgrade-invalid", "upgrade-exclusive", "future-corrupt"))
        cursor = ("Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
                  "Observed_continuation_corruption_preserves_actual_pages")
        expected.update(f'{cursor}(provider: "{provider}", corruption: {corruption})'
                        for provider in ("memory", "sqlite") for corruption in (
                            "Null", "Omitted", "WrongType", "Empty", "OddHex", "InvalidHex"))
        dimensions = ("Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
                      "Observed_query_corruption_preserves_actual_dimensions")
        expected.update(f'{dimensions}(provider: "{provider}", corruption: {corruption})'
                        for provider in ("memory", "sqlite") for corruption in (
                            "CacheAuthorization", "AggregateAuthorization", "AggregateStart", "AggregateEnd", "LeaseResource"))
        epoch = ("Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
                 "Observed_continuations_reject_foreign_actual_store_epochs")
        expected.update(f'{epoch}(provider: "{provider}")' for provider in ("memory", "sqlite"))
        ownership = ("Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
                     "Observed_corruption_scopes_preserve_actual_target_and_closure_ownership")
        expected.update(f'{ownership}(provider: "{provider}", operation: {operation})'
                        for provider in ("memory", "sqlite") for operation in ("False", "True"))
        application = ("Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
                       "Observed_corruption_application_preserves_actual_commits_and_recoverable_ownership")
        expected.update(f'{application}(provider: "{provider}", operation: {operation}, consumer: "{consumer}")'
                        for provider in ("memory", "sqlite") for operation in ("False", "True")
                        for consumer in ("capture", "cancel", "restore"))
        closure = ("Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
                   "Observed_corruption_closure_fences_later_scopes_while_actual_work_is_held")
        expected.update(f'{closure}(provider: "{provider}", reopen: {reopen})'
                        for provider in ("memory", "sqlite") for reopen in ("False", "True"))
        scenario, = checks.full_metadata_binding_scenarios()
        self.assertEqual(scenario, ("full-metadata-binding", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [
                {"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64},
                {"packageId": "Hoard.Fixtures.Metadata.Memory", "sha256": "c" * 64},
                {"packageId": "Hoard.Fixtures.Metadata.Sqlite", "sha256": "d" * 64}],
        }
        for roles in checks.metadata_origin_inputs(candidate, self.directory).values():
            for path, _ in roles.values():
                inputs["runtimeAssemblies"][path] = "e" * 64
        run = SimpleNamespace(root=self.directory)
        with patch.object(checks, "require_sqlite_environment") as admission:
            with patch.object(checks, "runtime_command",
                              side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                    checks.test_attempt(run, inputs, candidate, scenario)
                admission.assert_called_once_with(inputs, assembly, self.directory)
                manifest = launch.call_args.args[2]
                packages = launch.call_args.kwargs["metadata_packages"]
                self.assertEqual(packages, {
                    "Hoard.Fixtures.Metadata.Memory": "c" * 64, "Hoard.Fixtures.Metadata.Sqlite": "d" * 64})
                self.assertEqual({item["path"] for item in manifest["assemblies"]}, set(inputs["runtimeAssemblies"]))
                self.assertEqual({item["caseId"] for item in manifest["expected"]}, {"full-metadata-binding"})
                self.assertEqual({item["bindingId"] for item in manifest["expected"]},
                                 {"fixture.metadata.memory", "fixture.metadata.sqlite"})
            for changed, code in (
                    ({**inputs, "packages": inputs["packages"][:1]}, "PrerequisiteMissing"),
                    ({**inputs, "runtimeAssemblies": {
                        assembly.relative_to(self.directory).as_posix(): "a" * 64}}, "InputChanged")):
                with patch.object(checks, "runtime_command") as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, code):
                        checks.test_attempt(run, changed, candidate, scenario)
                    launch.assert_not_called()
        for artifact_packages, metadata_packages, code in (
                (None, {**packages, "foreign": "e" * 64}, "WitnessMissing"),
                (packages, packages, "WitnessMissing"), (None, packages, "InputChanged")):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, code):
                checks.runtime_command(run, assembly, manifest,
                                       artifact_packages=artifact_packages, metadata_packages=metadata_packages)
        for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("full-metadata-binding-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(run, {}, candidate, changed)
                launch.assert_not_called()

    def test_actual_authority_matrix_requires_every_composition_and_rejects_reduced_scope(self):
        factory = getattr(checks, "actual_authority_integration_scenarios", None)
        self.assertTrue(callable(factory), "Actual authority integration requires its own exact observed scope.")
        method = "Hoard.Conformance.Tests.AuthorityIntegrationTests.Actual_compositions_preserve_shared_authority"
        expected = {
            f'{method}(provider: "{provider}", metadataProvider: "{metadata}", consumer: "{consumer}")'
            for provider in ("local", "object") for metadata in ("memory", "sqlite") for consumer in (
                "reference-admission", "failed-transaction", "live-references", "lost-acknowledgment",
                "incarnation", "reader", "foreign-authority", "shutdown")}
        scenario, = factory()
        self.assertEqual(scenario, ("actual-authority-integration", tuple(sorted(expected)),
                                    "None", "Passed", 0, "None"))
        case, = (case for case in checks.expected_cases("artifacts") if case.case_id == "QC-12")
        self.assertEqual(scenario[1], case.witnesses)
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64}],
        }
        run = SimpleNamespace(root=self.directory)
        with patch.object(checks, "require_sqlite_environment") as admission:
            with patch.object(checks, "runtime_command",
                              side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                    checks.test_attempt(run, inputs, candidate, scenario)
                admission.assert_called_once_with(inputs, assembly, self.directory)
                self.assertEqual(launch.call_args.args[1], assembly)
                self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
        shortened = tuple(
            (scenario[0], tuple(identity for identity in scenario[1] if parameter not in identity), *scenario[2:])
            for parameter in (
                *(f'provider: "{provider}", metadataProvider: "{metadata}"'
                  for provider in ("local", "object") for metadata in ("memory", "sqlite")),
                *(f'consumer: "{consumer}"' for consumer in (
                    "reference-admission", "failed-transaction", "live-references", "lost-acknowledgment",
                    "incarnation", "reader", "foreign-authority", "shutdown"))))
        for changed in (*shortened, (scenario[0], scenario[1][:-1], *scenario[2:]),
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("actual-authority-integration-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, self.directory, changed)
                launch.assert_not_called()

    def test_category_mutations_require_faulty_and_corrected_provider_pairs(self):
        factory = getattr(checks, "category_mutation_scenarios", None)
        self.assertTrue(callable(factory), "Category mutations require named assertion failures and corrected passes.")
        actual = factory()
        self.assertEqual(len(actual), 4)
        for category, providers in (("metadata", ("memory", "sqlite")), ("artifacts", ("local", "object"))):
            for corrected in (False, True):
                name = f"category-mutation-{category}-{'corrected' if corrected else 'faulty'}"
                scenario = next(row for row in actual if row[0] == name)
                selected = (("Corrected_metadata_replay_passes" if corrected else "Stale_metadata_replay_is_rejected")
                            if category == "metadata" else
                            ("Corrected_artifact_staging_passes" if corrected else "Premature_artifact_publication_is_rejected"))
                method = "Hoard.Conformance.Tests.CategoryMutationTests." + selected
                expected = tuple(sorted(
                    f'{method}(provider: "{provider}")' for provider in providers))
                self.assertEqual(scenario, (name, expected, "None" if corrected else "AssertionFailed",
                                           "Passed" if corrected else "Failed", 0 if corrected else 1,
                                           "None" if corrected else "Assertion"))
                changed = (name, expected[:-1], *scenario[2:])
                with patch.object(checks, "runtime_command") as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                        checks.test_attempt(SimpleNamespace(root=self.directory), {}, self.directory, changed)
                    launch.assert_not_called()

    def test_category_mutation_runtime_owns_named_assertions_and_actual_package_hashes(self):
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
        packages = {
            "Hoard.Fixtures.Metadata.Memory": "c" * 64,
            "Hoard.Fixtures.Metadata.Sqlite": "d" * 64,
            "Hoard.Fixtures.Artifacts.Local": "e" * 64,
            "Hoard.Fixtures.Artifacts.ObjectSemantics": "f" * 64,
        }
        feed = self.directory / "feed/candidate"
        feed.mkdir(parents=True)
        for package in packages:
            archive = feed / (package + ".0.1.0.nupkg")
            archive.write_bytes(package.encode())
            packages[package] = checks.evidence.file_sha256(archive)
        (self.directory / "stores").mkdir()
        (self.directory / "runtime-owner.json").write_bytes(b"{}")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [{"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64},
                         *({"packageId": package, "sha256": digest} for package, digest in packages.items())],
        }
        run = SimpleNamespace(root=self.directory)
        for scenario in checks.category_mutation_scenarios():
            metadata = "-metadata-" in scenario[0]
            family = "Metadata" if metadata else "Artifacts"
            required = {package: digest for package, digest in packages.items() if f".{family}." in package}
            symbol = ("Hoard.Testing.Conformance.Metadata.MetadataTimeAssertions.TicketExpiryAndRollbackAsync"
                      if metadata else
                      "Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions.PrivateStagingAsync")
            with self.subTest(scope=scenario[0]), patch.object(checks, "require_sqlite_environment") as admission:
                with patch.object(checks, "runtime_command",
                                  side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                        checks.test_attempt(run, inputs, candidate, scenario)
                    self.assertEqual(launch.call_args.args[1], assembly)
                    manifest = launch.call_args.args[2]
                    self.assertEqual({item["testIdentity"] for item in manifest["expected"]}, set(scenario[1]))
                    self.assertEqual({item["assertionSymbol"] for item in manifest["expected"]},
                                     {symbol if scenario[5] == "Assertion" else None})
                    self.assertEqual(launch.call_args.kwargs,
                                     {"metadata_packages" if metadata else "artifact_packages": required})
                    if metadata:
                        admission.assert_called_once_with(inputs, assembly, self.directory)
                    else:
                        admission.assert_not_called()
                options = {"metadata_packages" if metadata else "artifact_packages": required}
                with patch.object(run, "command", create=True,
                                  side_effect=checks.evidence.ConformanceError("DeadlineExceeded")) as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "DeadlineExceeded"):
                        checks.runtime_command(run, assembly, manifest, **options)
                    arguments = launch.call_args.args[0]
                    self.assertEqual(arguments[:3], ["dotnet", "vstest", str(assembly)])
                    self.assertIn("--ListTests", arguments)
                    self.assertIn("--TestCaseFilter:FullyQualifiedName=" + scenario[1][0].split("(")[0], arguments)
                    settings = ET.fromstring((
                        self.directory / "stores" / f"settings-{manifest['attemptId']}.runsettings").read_bytes())
                    variables = settings.find("./RunConfiguration/EnvironmentVariables")
                    self.assertEqual({item.tag: item.text for item in variables}, {
                        "HOARD_ORIGIN_RUN_ID": inputs["runId"],
                        **{("HOARD_METADATA_" if metadata else "HOARD_ARTIFACT_")
                           + ("OBJECT" if package.endswith(".ObjectSemantics") else package.rsplit(".", 1)[1].upper())
                           + "_PACKAGE_SHA256": digest for package, digest in required.items()},
                    })
                foreign = {package: digest for package, digest in packages.items() if package not in required}
                for changed_manifest, changed_options in (
                        ({**manifest, "expected": manifest["expected"][:-1]}, options),
                        ({**manifest, "expected": [manifest["expected"][0]] * 2}, options),
                        (manifest, {"artifact_packages" if metadata else "metadata_packages": foreign})):
                    with patch.object(run, "command", create=True) as launch:
                        with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                            checks.runtime_command(run, assembly, changed_manifest, **changed_options)
                        launch.assert_not_called()
                changed = {**inputs, "packages": [
                    item for item in inputs["packages"] if item["packageId"] != next(iter(required))]}
                with patch.object(checks, "runtime_command") as launch:
                    with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
                        checks.test_attempt(run, changed, candidate, scenario)
                    launch.assert_not_called()

    def test_full_schema_origin_admission_rejects_missing_extra_and_foreign_lineages(self):
        witness = (
            "Hoard.Fixtures.Conformance.Consumer.MetadataConformanceSessionTests."
            'Observed_schema_consumers_preserve_actual_reopen_lineage(provider: "memory", consumer: "future-corrupt")')
        inputs = {"bindings": [{"bindingId": "fixture.metadata.memory", "descriptorSha256": "a" * 64}]}
        observed = {"testIdentity": witness, "executionId": "actual-case", "bindingId": "fixture.metadata.memory"}
        counts = checks.full_metadata_binding_origin_counts()
        for size, descriptor, accepted in ((4, "a" * 64, True), (3, "a" * 64, False),
                                           (5, "a" * 64, False), (4, "b" * 64, False)):
            ingested = {"witnesses": [observed], "sessionOrigins": {
                "actual-case": [{"descriptorSha256": descriptor} for _ in range(size)]}}
            if accepted:
                checks.validate_full_binding_origins(ingested, inputs, counts)
            else:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.validate_full_binding_origins(ingested, inputs, counts)

    def test_full_artifact_binding_origins_require_validation_reopen_without_object_restart(self):
        counts = checks.full_artifact_binding_origin_counts()
        for provider in ("local", "object"):
            for missing in ("False", "True"):
                identity = (checks.FULL_ARTIFACT_CONSUMER_PREFIX
                            + "Observed_validation_first_quarantine_survives_actual_restoration_and_reopen"
                            + f'(provider: "{provider}", missing: {missing})')
                binding = "fixture.artifact." + provider
                execution = str(uuid.uuid4())
                inputs = {"bindings": [{"bindingId": binding, "descriptorSha256": "a" * 64}]}
                witness = {"testIdentity": identity, "bindingId": binding, "executionId": execution}
                origins = tuple({"descriptorSha256": "a" * 64}
                                for _ in range(2 if provider == "local" else 1))
                observed = {"witnesses": [witness], "sessionOrigins": {execution: origins}}
                checks.validate_full_binding_origins(observed, inputs, counts)
                for altered in (origins[:-1], (*origins, origins[0]),
                                (*origins[:-1], {"descriptorSha256": "b" * 64})):
                    with self.subTest(provider=provider, missing=missing, count=len(altered)):
                        with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                            checks.validate_full_binding_origins(
                                {**observed, "sessionOrigins": {execution: altered}}, inputs, counts)

    def test_full_artifact_binding_scope_requires_all_real_controls_and_observed_reopen(self):
        factory = getattr(checks, "full_artifact_binding_scenarios", None)
        self.assertTrue(callable(factory), "Full bindings require actual controls, not declarations alone.")
        prefix = "Hoard.Fixtures.Conformance.Consumer.ArtifactConformanceSessionTests."
        expected = {
            prefix + "Full_binding_controls_reach_actual_work_and_preserve_borrowed_ownership"
            + f'(provider: "{provider}", fault: {fault})'
            for provider in ("local", "object") for fault in (
                "PublicationBoundary", "DirectVisibility", "PayloadDamage", "Capacity",
                "NativeNonCooperation", "CleanupFailure", "GenerationBoundary", "ReceiptBoundary",
                "SourceNonCooperation", "SinkNonCooperation")}
        expected.update(prefix + "Observed_full_binding_reopens_actual_components_and_fences_stale_controls"
                        + f'(provider: "{provider}", retainsPublication: {retained})'
                        for provider, retained in (("local", "True"), ("object", "False")))
        expected.update(prefix + "Releasing_native_work_does_not_block_an_independent_release_or_rearming"
                        + f'(provider: "{provider}")' for provider in ("local", "object"))
        expected.update(prefix + "Observed_publication_consumers_preserve_actual_binding_guarantees"
                        + f'(provider: "{provider}", consumer: "{consumer}")'
                        for provider in ("local", "object") for consumer in (
                            "empty", "unknown-length", "expectations", "unsupported", "duplicates"))
        expected.update(prefix + "Observed_read_reconciliation_and_deletion_preserve_actual_binding_guarantees"
                        + f'(provider: "{provider}", consumer: "{consumer}")'
                        for provider in ("local", "object") for consumer in (
                            "destination-failure", "exact-retry", "staged-length", "recreation", "reader-exclusion"))
        expected.update(prefix + "Observed_boundary_consumers_preserve_actual_binding_guarantees"
                        + f'(provider: "{provider}", consumer: "{consumer}")'
                        for provider, consumers in (
                            ("local", ("private-staging", "concurrent-writers", "lost-acknowledgment", "visible-before-ack")),
                            ("object", ("private-staging", "concurrent-writers", "lost-acknowledgment", "direct-availability")))
                        for consumer in consumers)
        expected.update(prefix + "Ordinary_acknowledgment_shaped_observer_errors_still_fault_actual_settlement"
                        + f'(provider: "{provider}")' for provider in ("local", "object"))
        expected.update(prefix + "Observed_payload_and_progress_consumers_preserve_actual_binding_guarantees"
                        + f'(provider: "{provider}", consumer: "{consumer}")'
                        for provider in ("local", "object") for consumer in (
                            "read-bitflip", "read-truncate", "commit-progress", "exact-payload"))
        expected.update(prefix + "Observed_recovery_evidence_and_expiry_preserve_actual_binding_guarantees"
                        + f'(provider: "{provider}", consumer: "{consumer}")'
                        for provider in ("local", "object") for consumer in (
                            "receipts", "recovery-pages", "sequential-recovery", "changed-inventory",
                            "expiry-generation", "ownerless-expiry", "finalized-noncommit", "finalized-mutations",
                            "idle-read", "cooperative-inactivity", "noncooperative-source", "noncooperative-destination"))
        expected.update(prefix + "Observed_cancelled_descriptors_preserve_actual_current_ownership"
                        + f'(provider: "{provider}", alteration: "{alteration}")'
                        for provider in ("local", "object") for alteration in ("completion", "handle", "renewed"))
        expected.update(prefix + "Observed_budget_failures_and_references_preserve_actual_binding_guarantees"
                        + f'(provider: "{provider}", consumer: "{consumer}")'
                        for provider in ("local", "object") for consumer in (
                            "authority-deadline", "cancel-before", "cancel-waiting", "cap-crossing",
                            "cooperative-cancel", "storage-failures", "live-references", "reclaimed-identities"))
        expected.add(prefix + "Observed_budget_failures_and_references_preserve_actual_binding_guarantees"
                     + '(provider: "local", consumer: "reclaimed-incarnations")')
        expected.update(prefix + "Observed_clock_rollback_preserves_expiry_and_monotonic_ownership"
                        + f'(provider: "{provider}", consumer: "{consumer}")'
                        for provider in ("local", "object") for consumer in (
                            "history", "write-capacity", "delete-capacity"))
        expected.update(prefix + "Observed_handoff_and_progress_preserve_actual_result_ownership"
                        + f'(provider: "{provider}", consumer: "{consumer}")'
                        for provider in ("local", "object") for consumer in (
                            "released-cancellation", "successful-ticket", "successful-read",
                            "unclaimed-ticket", "unclaimed-read", "expired-staging", "progress-cancellation"))
        expected.update(prefix + "Observed_admitted_work_preserves_history_queue_and_shutdown_ownership"
                        + f'(provider: "{provider}", consumer: "{consumer}")'
                        for provider in ("local", "object") for consumer in (
                            "delete-history", "transfer-queue", "released-shutdown"))
        expected.update(prefix + "Observed_reconciliation_and_cleanup_preserve_admitted_generation_ownership"
                        + f'(provider: "{provider}", consumer: "{consumer}")'
                        for provider in ("local", "object") for consumer in (
                            "settled-replacement", "reconciliation-history", "cleanup-generation"))
        expected.update(prefix + "Observed_history_candidates_preserve_the_original_page_bounds"
                        + f'(provider: "{provider}", kind: "{kind}")'
                        for provider, kinds in (
                            ("local", ("tickets", "dependencies", "decisions", "reclamation")),
                            ("object", ("tickets", "dependencies", "decisions"))) for kind in kinds)
        expected.update(prefix + method + f'(provider: "{provider}")'
                        for provider in ("local", "object") for method in (
                            "Observed_history_candidates_resume_after_an_owned_one_shot_failure",
                            "Ordinary_candidate_shaped_observer_errors_still_fault_actual_settlement"))
        expected.update(prefix + "Observed_receipts_and_failed_callbacks_preserve_actual_resource_ownership"
                        + f'(provider: "{provider}", consumer: "{consumer}")'
                        for provider in ("local", "object")
                        for consumer in ("receipt", "read-open", "verified-reconciliation", "pending-reclamation"))
        expected.update(prefix + "Ordinary_errors_inside_owned_failure_callbacks_still_fault_actual_settlement"
                        + f'(provider: "{provider}", point: {point})'
                        for provider in ("local", "object")
                        for point in ("ReadOpened", "ReconciliationVerified", "DeleteRemoved"))
        expected.update(prefix + "Observed_admitted_open_rechecks_actual_quarantine_before_result_handoff"
                        + f'(provider: "{provider}")' for provider in ("local", "object"))
        expected.update(prefix + "Observed_validation_first_quarantine_survives_actual_restoration_and_reopen"
                        + f'(provider: "{provider}", missing: {missing})'
                        for provider in ("local", "object") for missing in ("False", "True"))
        expected.update(prefix + "Observed_initial_admission_preserves_actual_capabilities_and_no_io_rejection"
                        + f'(provider: "{provider}", probe: {probe})'
                        for provider in ("local", "object") for probe in (
                            "Complete", "Version", "Publication", "Deletion", "Recovery", "Fencing",
                            "Readers", "Streaming", "ForeignAuthority"))
        scenario, = factory()
        self.assertEqual(scenario, ("full-artifact-binding", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
        inputs = {
            "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
            "runtimeAssemblies": {assembly.relative_to(self.directory).as_posix(): "a" * 64},
            "packages": [
                {"packageId": "Hoard.Testing.Conformance", "sha256": "b" * 64},
                {"packageId": "Hoard.Fixtures.Artifacts.Local", "sha256": "c" * 64},
                {"packageId": "Hoard.Fixtures.Artifacts.ObjectSemantics", "sha256": "d" * 64}],
        }
        components = checks.artifact_origin_inputs(candidate, self.directory)
        for roles in components.values():
            for path, _ in roles.values():
                inputs["runtimeAssemblies"][path] = "e" * 64
        sdk_path = (assembly.parent / "Hoard.Testing.Conformance.dll").relative_to(self.directory).as_posix()
        inputs["runtimeAssemblies"][sdk_path] = "f" * 64
        with patch.object(checks, "runtime_command",
                          side_effect=checks.evidence.ConformanceError("ProofMismatch")) as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
                checks.test_attempt(SimpleNamespace(root=self.directory), inputs, candidate, scenario)
            self.assertEqual(launch.call_args.args[1], assembly)
            self.assertEqual({item["testIdentity"] for item in launch.call_args.args[2]["expected"]}, expected)
            packages = launch.call_args.kwargs["artifact_packages"]
            self.assertEqual(packages, {
                "Hoard.Fixtures.Artifacts.Local": "c" * 64,
                "Hoard.Fixtures.Artifacts.ObjectSemantics": "d" * 64})
            manifest = launch.call_args.args[2]
            self.assertEqual(len(manifest["assemblies"]), 6)
            self.assertEqual({item["path"] for item in manifest["assemblies"]}, set(inputs["runtimeAssemblies"]))
            self.assertEqual({item["caseId"] for item in manifest["expected"]}, {"full-artifact-binding"})
            self.assertEqual({item["bindingId"] for item in manifest["expected"]},
                             {"fixture.artifact.local", "fixture.artifact.object"})
        with patch.object(checks, "runtime_command") as launch:
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "PrerequisiteMissing"):
                checks.test_attempt(SimpleNamespace(root=self.directory),
                                    {**inputs, "packages": inputs["packages"][:1]}, candidate, scenario)
            launch.assert_not_called()
        for images in (
                {assembly.relative_to(self.directory).as_posix(): "a" * 64},
                {path: hashed for path, hashed in inputs["runtimeAssemblies"].items() if path != sdk_path}):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
                    checks.test_attempt(SimpleNamespace(root=self.directory),
                                        {**inputs, "runtimeAssemblies": images}, candidate, scenario)
                launch.assert_not_called()
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
            checks.runtime_command(SimpleNamespace(root=self.directory), assembly, manifest,
                                   artifact_packages={**packages, "foreign": "e" * 64})
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            checks.runtime_command(SimpleNamespace(root=self.directory), assembly, manifest, artifact_packages=packages)
        for changed in (*((
                scenario[0], tuple(identity for identity in scenario[1] if f'consumer: "{consumer}"' not in identity),
                *scenario[2:]) for consumer in (
                    "empty", "unknown-length", "expectations", "unsupported", "duplicates",
                    "destination-failure", "exact-retry", "staged-length", "recreation", "reader-exclusion",
                    "private-staging", "concurrent-writers", "lost-acknowledgment", "visible-before-ack", "direct-availability")),
                        (scenario[0], scenario[1][:-1], *scenario[2:]),
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("full-artifact-binding-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_synchronous_storage_scope_requires_actual_owned_worker_and_authority_protection(self):
        factory = getattr(checks, "artifact_synchronous_storage_scenarios", None)
        self.assertTrue(callable(factory), "Synchronous native-boundary work must remain genuinely owned.")
        method = ("Hoard.Fixtures.Conformance.Consumer.ArtifactPayloadSessionTests."
                  "Synchronous_storage_hold_retains_actual_worker_and_protection_until_release")
        expected = {method + f'(provider: "{provider}")' for provider in ("local", "object")}
        scenario, = factory()
        self.assertEqual(scenario, ("artifact-synchronous-storage", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("artifact-synchronous-storage-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_unclaimed_cleanup_scope_requires_real_reservation_and_read_handoff_ownership_until_repair(self):
        factory = getattr(checks, "artifact_unclaimed_cleanup_scenarios", None)
        self.assertTrue(callable(factory), "Unclaimed cleanup must retain actual provider work until repair.")
        method = ("Hoard.Fixtures.Conformance.Consumer.ArtifactPayloadSessionTests."
                  "Scoped_unclaimed_cleanup_failure_retains_actual_work_until_repaired_settlement")
        expected = {
            method + f'(provider: "{provider}", readSession: {read_session})'
            for provider in ("local", "object") for read_session in ("False", "True")}
        scenario, = factory()
        self.assertEqual(scenario, ("artifact-unclaimed-cleanup", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("artifact-unclaimed-cleanup-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_capacity_injection_scope_requires_real_failure_repair_and_unsuppressed_ordinary_observer_errors(self):
        factory = getattr(checks, "artifact_capacity_injection_scenarios", None)
        self.assertTrue(callable(factory), "Expected capacity injection must not hide unexpected observer errors.")
        prefix = "Hoard.Fixtures.Conformance.Consumer.ArtifactPayloadSessionTests."
        expected = {
            prefix + name + f'(provider: "{provider}")'
            for name in (
                "Scoped_capacity_failure_is_real_recoverable_and_does_not_poison_actual_settlement",
                "Ordinary_capacity_shaped_observer_error_still_faults_actual_settlement",
            ) for provider in ("local", "object")}
        scenario, = factory()
        self.assertEqual(scenario, ("artifact-capacity-injection", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("artifact-capacity-injection-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_direct_verification_scope_requires_actual_new_and_duplicate_publications_on_both_providers(self):
        factory = getattr(checks, "artifact_direct_verification_scenarios", None)
        self.assertTrue(callable(factory), "Direct verification must not borrow the publication-selection witness.")
        method = ("Hoard.Fixtures.Conformance.Consumer.ArtifactPayloadSessionTests."
                  "Direct_verification_observation_holds_new_and_duplicate_publication_before_acknowledgement")
        expected = {method + f'(provider: "{provider}", duplicate: {duplicate})'
                    for provider in ("local", "object") for duplicate in ("False", "True")}
        scenario, = factory()
        self.assertEqual(scenario, ("artifact-direct-verification", tuple(sorted(expected)), "None", "Passed", 0, "None"))
        candidate = self.directory / "candidate"
        assembly = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("artifact-direct-verification-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_deletion_settlement_scope_requires_both_original_providers_and_all_four_parameters(self):
        factory = getattr(checks, "original_artifact_deletion_settlement_scenarios", None)
        self.assertTrue(callable(factory), "Deletion extraction must retain both original physical and reference cases.")
        prefix = "Hoard.Artifacts.Tests.ArtifactDeletionTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        methods = {prefix + name for name in (
            "Lost_delete_acknowledgment_preserves_pending_reclamation_until_actual_cleanup",
            "Live_reference_or_unavailable_reference_authority_denies_removal",
        )}
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(")[0] in methods}
        self.assertEqual(len(expected), 4)
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-deletion-settlement", tuple(sorted(expected)), "None", "Passed", 0, "None"))
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-deletion-settlement-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_admission_scope_requires_original_logical_and_physical_variants_without_native_fact_substitution(self):
        factory = getattr(checks, "original_artifact_admission_scenarios", None)
        self.assertTrue(callable(factory), "Admission extraction must retain every original logical variant.")
        prefix = "Hoard.Artifacts.Tests.ArtifactAdmissionTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        methods = {prefix + name for name in (
            "Before_admission_and_with_mismatched_authority_no_source_or_directory_is_touched",
            "Symlinked_root_or_ancestor_is_rejected_without_touching_outside_sentinel",
        )}
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(")[0] in methods}
        expected.update(
            prefix + name + f'(provider: "{provider}")'
            for name in (
                "Noncooperative_initialization_returns_with_owned_work_and_stop_does_not_release_it",
                "Create_is_explicit_exclusive_and_disabled_construction_touches_no_directory",
                "Reopen_refuses_missing_foreign_incompatible_or_corrupt_roots_without_reset",
            ) for provider in ("local", "object"))
        expected.add(prefix + "Local_reopen_preserves_identity_while_object_replacement_cannot_claim_durable_reopen")
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-admission", tuple(sorted(expected)), "None", "Passed", 0, "None"))
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-admission-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_recovery_reopen_scope_requires_original_object_stop_and_both_existing_local_reopens(self):
        factory = getattr(checks, "original_artifact_recovery_reopen_scenarios", None)
        self.assertTrue(callable(factory), "Remaining recovery must retain actual object stop and Local reopen.")
        prefix = "Hoard.Artifacts.Tests.ArtifactRecoveryTests."
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name == prefix +
                    "Stop_retains_unselected_object_ownership_and_retries_only_its_private_payload"}
        expected.update(prefix + name for name in (
            "Local_reopen_preserves_committed_decisions_after_expired_ticket_retirement_and_clock_rollback",
            "Reopen_finishes_staging_release_after_a_durable_commit_receipt",
        ))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-recovery-reopen", tuple(sorted(expected)), "None", "Passed", 0, "None"))
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-recovery-reopen-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_recovery_barrier_retains_complete_original_entry_hold_release_and_settlement_body(self):
        path = ROOT / "tests/contracts/Hoard.Testing.Conformance/Artifacts/ArtifactConformanceBarrier.cs"
        self.assertTrue(path.is_file(), "Common race checks must own the original managed barrier.")
        text = path.read_text()
        body = text[text.index("{"):text.rindex("}") + 1]
        self.assertEqual(hashlib.sha256("".join(body.split()).encode()).hexdigest(),
                         "88372cf64d9e1c68b791e66c87393b107397e5b29c383dd1b3b2c3659659242a")
        original = (ROOT / "tests/contracts/Hoard.Artifacts.Tests/Cases/ArtifactTestBarrier.cs").read_text()
        self.assertIn("Hoard.Testing.Conformance.Artifacts.ArtifactConformanceBarrier(name);", original)

    def test_recovery_races_scope_requires_every_original_provider_and_admitted_history_witness(self):
        factory = getattr(checks, "original_artifact_recovery_race_scenarios", None)
        self.assertTrue(callable(factory), "Recovery races must retain both providers and admitted history.")
        prefix = "Hoard.Artifacts.Tests.ArtifactRecoveryTests."
        methods = {prefix + name for name in (
            "Expired_reclaimed_history_remains_owned_until_the_admitted_delete_physically_settles",
            "Late_cleanup_rechecks_the_exact_generation_after_replacement",
            "Progressing_commit_renews_owner_across_the_original_ttl",
        )}
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(")[0] in methods}
        expected.update(
            prefix + name + f'(provider: "{provider}")'
            for name in (
                "Admitted_reconciliation_preserves_the_settled_receipt_after_delete_and_recreate",
                "Expired_history_is_not_retired_beneath_an_admitted_reconciliation",
            ) for provider in ("local", "object"))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-recovery-races", tuple(sorted(expected)), "None", "Passed", 0, "None"))
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-recovery-races-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_recovery_pages_scope_requires_both_original_providers_and_every_cursor_and_generation_witness(self):
        factory = getattr(checks, "original_artifact_recovery_pages_scenarios", None)
        self.assertTrue(callable(factory), "Recovery extraction must retain both original providers.")
        prefix = "Hoard.Artifacts.Tests.ArtifactRecoveryTests."
        methods = {prefix + name for name in (
            "Sequential_recovery_retires_consumed_cursors_without_starving_independent_scans",
            "Changed_inventory_rejects_old_continuations_and_fresh_pages_cover_every_current_identity",
            "Expired_ownerless_reservations_release_capacity_without_replaying_old_tickets",
            "Cleanup_cannot_reopen_a_finalized_noncommit",
            "Expiry_cleanup_and_restage_fence_the_old_generation",
            "Recovery_pages_are_bounded_query_bound_and_not_deletion_authority",
        )}
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(")[0] in methods}
        expected.update(
            prefix + name + f'(provider: "{provider}")'
            for name in (
                "Expired_ownerless_reservations_release_capacity_without_replaying_old_tickets",
                "Cleanup_cannot_reopen_a_finalized_noncommit",
            ) for provider in ("local", "object"))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-recovery-pages", tuple(sorted(expected)), "None", "Passed", 0, "None"))
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-recovery-pages-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_validation_scope_requires_every_frozen_persistence_corruption_and_access_variant(self):
        factory = getattr(checks, "original_artifact_validation_scenarios", None)
        self.assertTrue(callable(factory), "Validation extraction must retain all original evidence fault variants.")
        prefix = "Hoard.Artifacts.Tests.ArtifactEvidenceTests."
        methods = {prefix + name for name in (
            "Local_failed_quarantine_persistence_retains_ownership_until_stop_retry_and_reopen",
            "Validation_first_corruption_cannot_be_revived_by_external_restoration",
            "Validation_access_failure_does_not_quarantine_intact_content",
        )}
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.split("(")[0] in methods}
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-validation", tuple(sorted(expected)), "None", "Passed", 0, "None"))
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-validation-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_quarantine_reopen_scope_retains_every_frozen_variant_and_all_three_lost_denial_mutations(self):
        factory = getattr(checks, "original_artifact_quarantine_reopen_scenarios", None)
        self.assertTrue(callable(factory), "Quarantine extraction must retain transitive Local reopen assertions.")
        methods = {
            "Hoard.Artifacts.Tests.ArtifactReadVerificationTests.Every_committed_detection_path_quarantines_restored_bytes",
            "Hoard.Artifacts.Tests.ArtifactReadVerificationTests.Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence",
            "Hoard.Artifacts.Tests.ArtifactPublicationRaceTests.Corrupt_existing_bytes_are_not_overwritten_or_reused",
        }
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"]
                    if name.split("(")[0] in methods}
        expected.update(
            "Hoard.Artifacts.Tests.ArtifactEvidenceConsumerTests."
            "Shared_quarantine_consumers_reject_lost_reopen_denial_and_accept_original_store"
            f'(consumer: "{consumer}")'
            for consumer in ("damaged-read", "committed-detection", "corrupt-existing"))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-quarantine-reopen", tuple(sorted(expected)), "None", "Passed", 0, "None"))
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
        local_only = (scenario[0], tuple(name for name in scenario[1] if '(provider: "object"' not in name), *scenario[2:])
        with patch.object(checks, "original_artifact_quarantine_reopen_scenarios", return_value=(local_only,)):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, local_only)
                launch.assert_not_called()
        for changed in ((scenario[0], scenario[1][:-1], *scenario[2:]),
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-quarantine-reopen-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_detection_scope_preserves_every_frozen_open_publication_and_reconciliation_variant(self):
        factory = getattr(checks, "original_artifact_detection_scenarios", None)
        self.assertTrue(callable(factory), "Committed-detection extraction needs all fixed inherited variants.")
        method = ("Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
                  "Every_committed_detection_path_quarantines_restored_bytes")
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(method + "(")}
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-detection", tuple(sorted(expected)), "None", "Passed", 0, "None"))
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-detection-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_read_race_scope_requires_original_quarantine_revalidation_and_reconciliation(self):
        factory = getattr(checks, "original_artifact_read_race_scenarios", None)
        self.assertTrue(callable(factory), "Read-race extraction needs exact original observer/barrier transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
        expected = {prefix + "Local_reconciliation_cannot_finalize_after_overlapping_read_quarantines_the_incarnation"}
        expected.update(prefix + f'Admitted_open_rechecks_quarantine_before_delivering_a_session(provider: "{provider}")'
                        for provider in ("local", "object"))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-read-races", tuple(sorted(expected)), "None", "Passed", 0, "None"))
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-read-races-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_damaged_read_scope_preserves_frozen_parameters_and_revived_evidence_mutations(self):
        factory = getattr(checks, "original_artifact_damaged_read_scenarios", None)
        self.assertTrue(callable(factory), "Damaged-read extraction needs exact frozen and actual-validator mutation transport.")
        prefix = "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
        method = prefix + "Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence"
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(method + "(")}
        expected.update(
            "Hoard.Artifacts.Tests.ArtifactEvidenceConsumerTests."
            "Shared_damaged_read_assertion_rejects_revived_evidence_and_accepts_original_validator"
            f'(provider: "{provider}")' for provider in ("local", "object"))
        scenario, = factory()
        self.assertEqual(scenario, ("original-artifact-damaged-read", tuple(sorted(expected)), "None", "Passed", 0, "None"))
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
                        (scenario[0], (*scenario[1], "Foreign.Test"), *scenario[2:]),
                        ("original-artifact-damaged-read-foreign", *scenario[1:])):
            with patch.object(checks, "runtime_command") as launch:
                with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                    checks.test_attempt(SimpleNamespace(root=self.directory), {}, candidate, changed)
                launch.assert_not_called()

    def test_artifact_evidence_scope_preserves_quarantine_and_receipt_parameters_and_mutation_pair(self):
        self.assertTrue(callable(getattr(checks, "original_artifact_evidence_scenarios", None)),
                        "Exact receipt and permanent quarantine consumers need actual wrapper transport.")
        read_methods = {
            "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
            "Every_committed_detection_path_quarantines_restored_bytes",
            "Hoard.Artifacts.Tests.ArtifactReadVerificationTests."
            "Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence",
        }
        frozen = json.loads((ROOT / "tests/fixtures/conformance/baselines/inventory.json").read_text())
        expected = {name for entry in frozen["entries"] if entry["profileId"] == "artifacts"
                    for name in entry["runtimeTests"] if name.startswith(
                        "Hoard.Artifacts.Tests.ArtifactEvidenceTests.") or name.split("(")[0] in read_methods}
        expected.update(
            "Hoard.Artifacts.Tests.ArtifactEvidenceConsumerTests."
            "Shared_receipt_assertion_rejects_wrong_receipt_acceptance_and_accepts_original_validator"
            f'(provider: "{provider}")' for provider in ("local", "object"))
        scenario, = checks.original_artifact_evidence_scenarios()
        self.assertEqual(set(scenario[1]), expected)
        self.assertEqual(len(scenario[1]), 23)
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
                        ("original-artifact-evidence-foreign", *scenario[1:])):
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

    def test_native_artifact_capture_context_is_bound_to_category_inputs_but_not_legacy_or_discovery(self):
        from test_conformance_evidence import ConformanceAdmissionTests
        inputs = {**ConformanceAdmissionTests().inputs(), "profileId": "artifacts", "mode": "diagnostic"}
        (self.directory / "stores").mkdir()
        (self.directory / "proofs/category-artifact-transfers").mkdir(parents=True)
        (self.directory / "proofs/qualification-artifact-transfers").mkdir()
        (self.directory / "proofs/artifact-transfers").mkdir()
        (self.directory / "runtime-owner.json").write_bytes(b"{}")
        (self.directory / "proofs/category-inputs.json").write_bytes(checks.evidence.canonical_bytes(inputs))
        runner = self.directory / "Hoard.Fixtures.Artifacts.CrashRunner.dll"
        runner.write_bytes(b"runner-unit-double")
        assembly = self.directory / "Hoard.Artifacts.Tests.dll"
        tests = checks._category_scope_tests(("artifacts", "controller"))
        manifest = {
            "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
            "attemptId": str(uuid.uuid4()), "purpose": "execution", "inputSha256": checks.evidence.digest(inputs),
            "runInputsPath": "proofs/category-inputs.json", "expected": [{
                "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
                "bindingId": binding, "caseId": case} for identity, (binding, case) in tests.items()]}
        run = object.__new__(checks.OwnedRun)
        run.root, run.run_id, run.root_id = self.directory, inputs["runId"], uuid.uuid4().hex
        launches = []
        run.command = lambda arguments, **options: launches.append(options) or SimpleNamespace(exit_code=0)
        for kind in ("category", "qualification", "discovery", "qualification-discovery", "legacy"):
            selected_inputs = {**inputs, "mode": "qualification" if kind.startswith("qualification") else "diagnostic"}
            (self.directory / "proofs/category-inputs.json").write_bytes(checks.evidence.canonical_bytes(selected_inputs))
            selected = {**manifest, "attemptId": str(uuid.uuid4()),
                        "purpose": "discovery" if kind.endswith("discovery") else "execution",
                        "inputSha256": checks.evidence.digest(selected_inputs)}
            if kind == "legacy":
                selected["expected"] = [{
                    "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
                    "bindingId": "none", "caseId": "original-artifact-external"}
                    for identity in checks.original_artifact_external_scenarios()[0][1]]
            with self.subTest(kind=kind), patch.object(checks, "category_command_proof"):
                checks.runtime_command(run, assembly, selected, artifact_runner=runner, **(
                    {} if kind == "legacy" else {"category_scope": ("artifacts", "controller")}))
                settings = ET.fromstring((self.directory / f'stores/settings-{selected["attemptId"]}.runsettings').read_bytes())
                context_path = settings.findtext("./RunConfiguration/EnvironmentVariables/HOARD_ARTIFACT_SOURCE_CONTEXT")
                namespace = ("qualification-artifact-transfers" if kind.startswith("qualification")
                             else "category-artifact-transfers")
                self.assertEqual(
                    settings.findtext("./RunConfiguration/EnvironmentVariables/HOARD_ARTIFACT_TRANSFER_PROOFS"),
                    str(self.directory / "proofs" / ("artifact-transfers" if kind == "legacy" else namespace)))
                if kind in ("category", "qualification"):
                    context = checks.evidence.load_json(Path(context_path).read_bytes())
                    self.assertEqual(context["rootId"], run.root_id)
                    self.assertEqual(context["inputsSha256"], checks.evidence.digest(selected_inputs))
                    self.assertEqual(set(context["cases"]), set(tests))
                    self.assertEqual(context["outputDirectory"], str(
                        self.directory / f'stores/artifact-source-capture-{selected["attemptId"]}'))
                    expected = {
                        f'runtime-input-{selected["attemptId"]}.json', "runtime-owner.json",
                        "proofs/category-inputs.json", f'stores/settings-{selected["attemptId"]}.runsettings',
                        "Hoard.Artifacts.Tests.dll", f'stores/artifact-source-context-{selected["attemptId"]}.json',
                        runner.name, f"proofs/{namespace}.json",
                        *(f"proofs/{namespace}/transfer-{provider}-{size}/proof.json"
                          for provider in ("local", "object") for size in (268435456, 4294967296))}
                    self.assertEqual(set(launches[-1]["execution_inputs"]), expected)
                    self.assertTrue(launches[-1]["record_execution"])
                    self.assertEqual(launches[-1]["execution_outputs"],
                                     (f'proofs/artifact-source-seal-{selected["attemptId"]}.json',))
                else:
                    self.assertIsNone(context_path)
                    self.assertNotIn("execution_outputs", launches[-1])
                    self.assertFalse((self.directory / f'stores/artifact-source-context-{selected["attemptId"]}.json').exists())

    def test_external_artifact_settings_bind_the_actual_runner_current_run_and_parent_transfer_proofs(self):
        (self.directory / "stores").mkdir()
        (self.directory / "proofs/artifact-transfers").mkdir(parents=True)
        (self.directory / "runtime-owner.json").write_bytes(b"{}")
        runner = self.directory / "Hoard.Fixtures.Artifacts.CrashRunner.dll"
        runner.write_bytes(b"runner-unit-double")
        assembly = self.directory / "Hoard.Artifacts.Tests.dll"
        received = []
        run = SimpleNamespace(root=self.directory, command=lambda args, **options: (
            received.append(args) or SimpleNamespace(exit_code=0, events=())))
        scenario, = checks.original_artifact_external_scenarios()
        manifest = {
            "attemptId": str(uuid.uuid4()), "runId": str(uuid.uuid4()), "purpose": "discovery",
            "expected": [{"testIdentity": name, "fullyQualifiedName": name.split("(")[0]} for name in scenario[1]],
        }
        checks.runtime_command(run, assembly, manifest, artifact_runner=runner)
        settings = ET.fromstring(Path(next(arg.removeprefix("--Settings:") for arg in received[0]
                                          if arg.startswith("--Settings:"))).read_bytes())
        variables = {item.tag: item.text for item in settings.findall("./RunConfiguration/EnvironmentVariables/*")}
        self.assertEqual(variables["HOARD_ARTIFACT_CRASH_RUNNER"], str(runner))
        self.assertEqual(variables["HOARD_ARTIFACT_TRANSFER_PROOFS"], str(self.directory / "proofs/artifact-transfers"))
        self.assertEqual(variables["HOARD_ARTIFACT_RUN_ID"], manifest["runId"])
        self.assertEqual(Path(variables["HOARD_ARTIFACT_CRASH_PROOFS"]).parent, self.directory / "stores")
        self.assertNotIn("HOARD_CONFORMANCE_SAFE_EVENTS", variables)
        for target, expected in ((self.directory / "Foreign.dll", manifest["expected"]),
                                 (assembly, [{"testIdentity": "foreign", "fullyQualifiedName": "foreign"}])):
            with self.assertRaisesRegex(checks.evidence.ConformanceError, "WitnessMissing"):
                checks.runtime_command(run, target, manifest | {"expected": expected}, artifact_runner=runner)
        self.assertEqual(len(received), 1)

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
        import conformance_sources as sources

        for namespace in ("sqlite-native-noncooperation", "category-sqlite-native-noncooperation",
                          "qualification-sqlite-native-noncooperation"):
            root = self.directory / namespace
            (root / "stores").mkdir(parents=True)
            (root / "proofs").mkdir()
            assembly_path = (Path("candidate") / checks.TESTS / checks.PACKAGE_TEST_OUTPUT
                             / "Release/net10.0/Hoard.Conformance.Tests.dll").as_posix()
            inputs = {
                "profileId": "metadata", "mode": "qualification" if namespace.startswith("qualification-") else "diagnostic",
                "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                "runtimeAssemblies": {assembly_path: "a" * 64}}
            producer = {**observed, "inputsSha256": checks.evidence.digest(inputs)}
            record = {**command, "sequence": 5}
            invocations = []
            original_records = {}

            def execute(arguments, **options):
                invocations.append((arguments, options))
                self.assertEqual(Path(arguments[3]), root / f"proofs/{namespace}.json")
                self.assertEqual(Path(arguments[4]), root / f"stores/{namespace}")
                self.assertEqual(arguments[-1], checks.evidence.digest(inputs))
                self.assertEqual(options["cache_id"], namespace)
                self.assertIs(options.get("record_execution"), True)
                input_path = f"proofs/{namespace}-native-inputs.json"
                self.assertEqual(options["execution_inputs"], (
                    Path(arguments[1]).relative_to(root).as_posix(), input_path))
                self.assertEqual(options["execution_outputs"], (f"proofs/{namespace}.json",))
                self.assertEqual((root / input_path).read_bytes(), checks.evidence.canonical_bytes(inputs))
                self.assertEqual((root / input_path).stat().st_mode & 0o777, 0o400)
                Path(arguments[3]).write_bytes(checks.evidence.canonical_bytes(producer))
                (root / "proofs/recovery-command-0005.json").write_bytes(
                    checks.evidence.canonical_bytes(record))
                original_records[5] = checks.evidence.canonical_bytes({
                    **record, "runId": run.run_id, "rootId": run.root_id,
                    "argvSha256": checks.evidence.digest(arguments),
                    "cwdSha256": hashlib.sha256(str(options["cwd"].absolute()).encode()).hexdigest(),
                    "controlRecordSha256": checks.evidence.digest(record),
                    "outputFiles": {f"proofs/{namespace}.json": checks.evidence.digest(producer)},
                    "inputFiles": {assembly_path: "a" * 64, input_path: checks.evidence.digest(inputs)}})
                raise checks.evidence.ConformanceError("DeadlineExceeded")

            run = SimpleNamespace(
                root=root, run_id=inputs["runId"], root_id=str(uuid.uuid4()),
                command_sequence=4, command=execute, live_children=lambda: (),
                read_execution_record=lambda sequence: original_records[sequence])
            with self.subTest(namespace=namespace), patch.object(
                    checks, "require_sqlite_environment"), patch.object(
                    checks.evidence, "package_identity", return_value={"sha256": "f" * 64}), patch.object(
                    checks, "OwnedRun", type(run)), patch.object(sources, "OwnedRun", type(run)):
                result = checks.sqlite_noncooperation(
                    run, inputs, root / "candidate", namespace=namespace)
                self.assertFalse(result["qualification"])
                self.assertEqual(result["inputsSha256"], checks.evidence.digest(inputs))
                self.assertEqual(result["producerSha256"], checks.evidence.digest(producer))
                self.assertEqual(result["controllerSha256"], checks.evidence.digest(record))
                self.assertEqual(len(invocations), 1)
                graph_path = root / f"proofs/{namespace}-native-executions.json"
                graph = checks.evidence.load_json(graph_path.read_bytes())
                self.assertFalse(graph["qualification"])
                self.assertEqual(graph["sequence"], 5)
                self.assertEqual(graph["executionSha256"], hashlib.sha256(original_records[5]).hexdigest())
                self.assertEqual(graph["producerSha256"], checks.evidence.digest(producer))
                self.assertEqual(graph["inputsPath"], f"proofs/{namespace}-native-inputs.json")
                self.assertEqual(graph_path.stat().st_mode & 0o777, 0o400)

    def test_native_noncooperation_cannot_turn_an_exit_setup_failure_or_live_child_into_success(self):
        for outcome, expected in (
                ("normal-exit", "EvidenceIncomplete"), ("CommandFailed", "CommandFailed"),
                ("missing-proof", "OutputLimitExceeded"), ("live-child", "CleanupIncomplete")):
            root = self.directory / outcome
            (root / "stores").mkdir(parents=True)
            (root / "proofs").mkdir()
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
        artifact_consumer = candidate / checks.ARTIFACT_CONSUMER / checks.PACKAGE_TEST_OUTPUT / (
            "Release/net10.0/Hoard.Fixtures.Conformance.Consumer.dll")
        artifact_consumer.parent.mkdir(parents=True)
        artifact_consumer.write_bytes(b"owned-artifact-session")
        sources = checks.evidence.source_manifest(repository)
        environment = {
            "os": "linux", "osVersion": "test", "architecture": "x86_64",
            "sdk": "10.0.203", "runtime": "10.0.7", "nativeSqlite": "not-used",
            "filesystem": "ext4", "runnerImage": "none", "freeBytes": 100,
            "pragmas": {"journalMode": "none", "synchronous": 0, "foreignKeys": 0, "busyTimeout": 0},
        }
        identity = checks.evidence.source_identity(repository)
        def capture(group_id=None, inspection_inputs=None, profile_id="harness", mode="diagnostic"):
            return checks.make_inputs(run, repository, candidate, sources,
                                      environment, identity, None, group_id=group_id, inspection_inputs=inspection_inputs,
                                      profile_id=profile_id, mode=mode)
        unconsumed = runtime / "unused-native-build.a"
        with unconsumed.open("wb") as output:
            output.truncate(checks.evidence.MAX_PROOF_BYTES + 1)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
            checks.evidence.proof_manifest(candidate)
        before = capture()
        for profile in ("metadata", "artifacts"):
            category_inputs = capture(profile_id=profile)
            self.assertEqual(category_inputs["profileId"], profile)
            self.assertEqual(category_inputs["mode"], "diagnostic")
            self.assertNotEqual(checks.evidence.digest(category_inputs), checks.evidence.digest(before))
            checks.evidence.verify_input_recomputation(
                category_inputs, capture(category_inputs["invocationGroupId"], profile_id=profile))
        qualification_inputs = capture(before["invocationGroupId"], profile_id="metadata", mode="qualification")
        self.assertEqual(qualification_inputs["mode"], "qualification")
        self.assertNotEqual(checks.evidence.digest(qualification_inputs), checks.evidence.digest(before))
        checks.evidence.verify_input_recomputation(
            qualification_inputs,
            capture(before["invocationGroupId"], profile_id="metadata", mode="qualification"))
        selected_large = runtime / "Oversized.dll"
        with selected_large.open("wb") as output:
            output.truncate(checks.evidence.MAX_PROOF_BYTES + 1)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
            capture(before["invocationGroupId"])
        selected_large.unlink()
        foreign_native = native.parent.parent.parent / "linux-arm64/native/libe_sqlite3.so"
        foreign_native.parent.mkdir(parents=True)
        foreign_native.write_bytes(b"unexecuted architecture")
        self.assertEqual(dict(before["runtimeAssemblies"]), dict(capture(before["invocationGroupId"])["runtimeAssemblies"]))
        foreign_native.unlink()
        foreign_native.symlink_to(native)
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "ProofMismatch"):
            capture(before["invocationGroupId"])
        foreign_native.unlink()
        self.assertEqual(len(before["packages"]), 15)
        self.assertNotIn(str(self.directory).encode(), checks.evidence.canonical_bytes(before))
        inspection = self.directory / "stores/inspection.xml"
        inspection.write_bytes(b"selected before execution")
        def selected():
            return {checks.original_inspection_prepared_scenarios()[0][1][0]:
                    {str(inspection): checks.evidence.file_sha256(inspection)}}
        inspected = capture(before["invocationGroupId"], selected())
        self.assertEqual(inspected["sourceManifest"], before["sourceManifest"])
        self.assertEqual(inspected["runtimeAssemblies"], before["runtimeAssemblies"])
        self.assertNotEqual(inspected["configurationSha256"], before["configurationSha256"])
        self.assertNotIn(str(inspection).encode(), checks.evidence.canonical_bytes(inspected))
        inspection.write_bytes(b"changed after execution")
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "InputChanged"):
            checks.evidence.verify_input_recomputation(
                inspected, capture(before["invocationGroupId"], selected()))
        for path in (native, wrapped, artifact_wrapped, artifact_consumer,
                     runtime / "Added.dll", runtime / "Tests.runtimeconfig.json",
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
        inputs = {"runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()), "mode": "diagnostic",
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
        diagnostic = json.loads(output.getvalue())
        locations = diagnostic.pop("locations")
        self.assertTrue(0 < len(locations) <= 4)
        self.assertTrue(all(location["source"] == "scripts/conformance_sdk_checks.py"
                            and location["line"] > 0 for location in locations))
        self.assertEqual(diagnostic, {
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

    def test_unexpected_runtime_failure_retains_only_bounded_closed_observations(self):
        identities = tuple(f"PrivateCanary.Case{index}" for index in range(9))
        ingested = {"diagnosticCode": "AssertionFailed", "witnesses": tuple(
            {"testIdentity": identity, "status": "Failed"} for identity in identities)}
        result = SimpleNamespace(exit_code=1, events=(
            {"event": "control", "code": "AssertionFailed", "value": len(identities)},))
        with self.assertRaisesRegex(checks.evidence.ConformanceError, "EvidenceIncomplete") as raised:
            checks.validate_observation(
                ingested, result, identities, "None", "Passed", 0, {}, "None")
        observed = raised.exception.runtime_diagnostic
        self.assertEqual(observed["observedCode"], "AssertionFailed")
        self.assertEqual(observed["observedExit"], 1)
        self.assertEqual(observed["witnessStates"], {"Passed": 0, "Failed": 9, "Incomplete": 0})
        self.assertEqual(observed["mismatchCount"], 9)
        self.assertEqual(observed["mismatchedTestsSha256"], sorted(
            hashlib.sha256(identity.encode()).hexdigest() for identity in identities)[:4])
        raw = json.dumps(observed).encode()
        self.assertLessEqual(len(raw), 1024)
        self.assertNotIn(b"PrivateCanary", raw)
        output = io.StringIO()
        with patch.object(sys, "argv", ["conformance_sdk_checks.py", "--evidence", "unused"]), \
                patch.object(checks, "execute", side_effect=raised.exception), contextlib.redirect_stdout(output):
            exit_code = checks.main()
        self.assertEqual(exit_code, 2)
        diagnostic = json.loads(output.getvalue())
        locations = diagnostic.pop("locations")
        self.assertTrue(0 < len(locations) <= 4)
        self.assertTrue(all(location["source"] == "scripts/conformance_sdk_checks.py"
                            and location["line"] > 0 for location in locations))
        self.assertEqual(diagnostic, {
            "qualification": False, "status": "Incomplete", "code": "EvidenceIncomplete", **observed})
        self.assertNotIn("PrivateCanary", output.getvalue())
        self.assertLessEqual(len(output.getvalue().encode()), 1024)

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
