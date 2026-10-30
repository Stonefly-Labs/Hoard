import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
from types import MappingProxyType, SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


class CompositionDiagnosticTests(unittest.TestCase):
    def test_native_report_inspection_rejects_modeled_ownership_before_reading_proofs(self):
        import conformance_composition_checks as composition
        import conformance_evidence as evidence

        with mock.patch.object(composition, "verify_composition_case_report") as verify:
            with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                evidence.inspect_native_composition_report(
                    SimpleNamespace(state="Released"), b"{}", expected_inputs={},
                    native_evaluation=SimpleNamespace(report_data=b"{}"))
        verify.assert_not_called()

    def test_native_origin_controls_require_the_actual_runtime_callback_and_preserve_failures(self):
        import conformance_composition_checks as composition
        import conformance_evidence as evidence

        for failure in (None, evidence.ConformanceError("InputChanged")):
            with self.subTest(failure=failure), mock.patch.object(
                    composition, "native_execution_supported", return_value=True), \
                    mock.patch.object(composition, "execute", side_effect=failure):
                with self.assertRaisesRegex(
                        evidence.ConformanceError, "^WitnessMissing$" if failure is None else "^InputChanged$"):
                    run_native_composition_controls(["--evidence", "/unallocated/test-only"])

    def test_inherited_runtime_hydrates_relative_manifest_paths_only_for_live_consumers(self):
        import conformance_composition_checks as composition

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "stores/source"
            source.mkdir(parents=True)
            logger = source / f"tests/contracts/{composition.LOGGER}/bin/Release/net10.0/{composition.LOGGER}.dll"
            logger.parent.mkdir(parents=True)
            logger.write_bytes(b"logger")
            normative = source / "specs/004-module-discovery/contracts/openapi.json"
            normative.parent.mkdir(parents=True)
            normative.write_bytes(b"{}")
            (root / "proofs").mkdir()
            controllers = {
                "manifests": {"HOARD_" + phase.upper() + "_EVIDENCE":
                              f"stores/inherited-controller-{phase}/{phase}-evidence.json"
                              for phase in ("foundation", "lifecycle", "configuration", "discovery")},
                "formatting": {"path": "proofs/formatting.json"},
            }
            run = SimpleNamespace(root=root)

            def read_inputs(owner, manifests, **kwargs):
                self.assertEqual(manifests, {key: str(root / path)
                                            for key, path in controllers["manifests"].items()})
                self.assertEqual(owner, root)
                raise RuntimeError("live-input-boundary")

            with mock.patch.object(composition.baselines, "_command"), \
                    mock.patch.object(composition, "verify_controller_baselines", return_value={"files": {}}), \
                    mock.patch.object(composition, "_controller_phase", return_value=(controllers, None, None)), \
                    mock.patch.object(composition, "_prepare_solution_formatting"), \
                    mock.patch.object(composition, "_native_reference_consumer"), \
                    mock.patch.object(composition, "controller_read_inputs", side_effect=read_inputs), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "^live-input-boundary$"):
                    composition._inherited_runtime(
                        run, ROOT, source, {}, root / "config", root / "feed",
                        {"path": "proofs/inherited-controller-baselines.json"})

    def test_compatibility_runtime_seals_compiler_outputs_for_the_real_executor_input_guard(self):
        import conformance_execution as execution
        import conformance_evidence as evidence
        import conformance_sdk_checks as sdk

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            runtime = root / "stores/runtime"
            runtime.mkdir(parents=True)
            for name in ("Hoard.Architecture.Tests.dll", "Hoard.Testing.Conformance.dll",
                         "Hoard.Architecture.Tests.deps.json", "Hoard.Architecture.Tests.runtimeconfig.json",
                         "compatibility-fixture.pdb"):
                image = runtime / name
                image.write_bytes(b"compiled-original")
                image.chmod(0o644)
            run = SimpleNamespace(
                root=root, _root_descriptor=lambda: os.open(root, os.O_RDONLY | os.O_DIRECTORY))
            assembly = (runtime / "Hoard.Architecture.Tests.dll").relative_to(root).as_posix()
            with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
                execution.OwnedRun._capture_execution_inputs(run, (assembly,), time.monotonic() + 5)
            paths = sdk.compatibility_runtime_paths(run, runtime)
            captured = execution.OwnedRun._capture_execution_inputs(run, paths, time.monotonic() + 5)
            self.assertEqual(set(captured), set(paths))
            for path in paths:
                self.assertEqual((root / path).read_bytes(), b"compiled-original")
                self.assertEqual((root / path).stat().st_mode & 0o777, 0o400)

    def test_version_environment_probes_never_overwrite_an_architecture_observation(self):
        import conformance_evidence as evidence
        import conformance_sdk_checks as sdk

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "proofs").mkdir()
            paths = []
            def probe(arguments, **kwargs):
                path = Path(arguments[-1])
                sdk.write_new(path, b'{"probe":true}')
                paths.append(path.name)
                return SimpleNamespace(exit_code=0, events=())

            run = SimpleNamespace(root=root, command=probe)
            with mock.patch.object(evidence, "admit_entity", side_effect=lambda _, value: value):
                for phase in ("admission", "completion"):
                    sdk.environment(run, phase=phase)
                    sdk.environment(run, phase=phase, scope="compatibility-version")
            self.assertEqual(len(set(paths)), 4)
            self.assertTrue(all((root / "proofs" / path).read_bytes() == b'{"probe":true}' for path in paths))

    def test_version_runtime_scope_preserves_all_axes_and_rejects_reduced_or_relabelled_manifests(self):
        import conformance_case_catalog as catalog
        import conformance_evidence as evidence
        import conformance_sdk_checks as sdk

        tests = catalog.version_runtime_tests()
        manifest = {"expected": [
            {"testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
             "bindingId": binding, "caseId": case}
            for identity, (binding, case) in tests.items()]}
        self.assertEqual(sdk._category_manifest_tests(("compatibility", "version"), manifest), tests)
        for selector in ('axis: "host"', 'axis: "abstractions"', 'axis: "required"', 'axis: "optional"',
                         "Platform_prerelease_flags_are_independent",
                         "Inherited_release_classifier_is_policy_not_runtime_evidence"):
            changed = evidence.load_json(evidence.canonical_bytes(manifest))
            matching = next(index for index, row in enumerate(changed["expected"])
                            if selector in row["testIdentity"])
            changed["expected"].pop(matching)
            with self.subTest(selector=selector), self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
                sdk._category_manifest_tests(("compatibility", "version"), changed)
        for defect in ("duplicate", "foreign", "binding", "case"):
            changed = evidence.load_json(evidence.canonical_bytes(manifest))
            if defect == "duplicate":
                changed["expected"].append(changed["expected"][0])
            elif defect == "foreign":
                changed["expected"][0]["testIdentity"] = "Hoard.Composition.Tests.Foreign"
            else:
                changed["expected"][0]["bindingId" if defect == "binding" else "caseId"] = "foreign"
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
                sdk._category_manifest_tests(("compatibility", "version"), changed)

    def test_binary_scope_requires_each_pdb_source_and_retained_break_repair_control(self):
        import conformance_case_catalog as catalog
        import conformance_evidence as evidence
        import conformance_sdk_checks as sdk

        tests = catalog.binary_runtime_tests()
        manifest = {"expected": [
            {"testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
             "bindingId": binding, "caseId": case}
            for identity, (binding, case) in tests.items()]}
        self.assertEqual(sdk._category_manifest_tests(("compatibility", "binary"), manifest), tests)
        for index in range(len(manifest["expected"])):
            changed = evidence.load_json(evidence.canonical_bytes(manifest))
            changed["expected"].pop(index)
            with self.subTest(omitted=index), self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
                sdk._category_manifest_tests(("compatibility", "binary"), changed)
        changed = evidence.load_json(evidence.canonical_bytes(manifest))
        changed["expected"][0]["testIdentity"] = "Hoard.Conformance.Tests.Foreign"
        with self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
            sdk._category_manifest_tests(("compatibility", "binary"), changed)

    def test_architecture_execution_admits_existing_prepared_images_without_reinstalling_them(self):
        import conformance_evidence as evidence
        import conformance_inherited as inherited
        import conformance_sdk_checks as sdk

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            candidate, feed = root / "stores/candidate", root / "feed/candidate"
            runtime = candidate / sdk.ARCHITECTURE_TESTS / "bin/Release/net10.0"
            runtime.mkdir(parents=True)
            installed = runtime / "Hoard.Conformance.TestLogger.dll"
            installed.write_bytes(b"already-prepared-image")
            installed.chmod(0o400)
            with contextlib.redirect_stdout(io.StringIO()), \
                    mock.patch.object(inherited, "admit_architecture_preparation", return_value=({}, {})), \
                    mock.patch.object(sdk, "build_inspection_runtime",
                                      side_effect=AssertionError("Prepared images must not be reinstalled")), \
                    mock.patch.object(sdk, "verify_runtime_packages",
                                      side_effect=evidence.ConformanceError("InputChanged")) as verify:
                with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
                    sdk.execute_architecture_runtime(
                        SimpleNamespace(root=root), ROOT, candidate, {}, root / "NuGet.Config", feed, {}, "a" * 64)
            verify.assert_called_once_with(
                runtime, feed, ("Hoard.Conformance.TestLogger", "Hoard.Testing.Conformance", "Hoard.Abstractions"))
            self.assertEqual(installed.read_bytes(), b"already-prepared-image")
            self.assertEqual(installed.stat().st_mode & 0o777, 0o400)

    def test_scoped_graph_restores_replay_each_project_without_reusing_a_parent_lock_for_children(self):
        import subprocess
        import conformance_evidence as evidence
        import conformance_inherited as inherited
        import conformance_legacy as legacy
        import foundation_evidence as foundation

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            feed = root / "feed"
            feed.mkdir()
            config = root / "NuGet.Config"
            config.write_text('<configuration><packageSources><add key="local" value="'
                              + str(feed) + '"/></packageSources></configuration>')
            projects = []
            for name in ("Parent", "Child", "Other"):
                project = root / "stores" / name / (name + ".csproj")
                project.parent.mkdir(parents=True)
                project.write_text("<Project/>")
                (project.parent / "packages.lock.json").write_text(
                    '{"version":1,"dependencies":{"net10.0":{}}}')
                projects.append(project)
            calls = []

            def replay(arguments, **kwargs):
                calls.append(arguments)
                return subprocess.CompletedProcess(arguments, 0, "")

            with inherited.controller_transport(ROOT, root) as controls, \
                    mock.patch.object(legacy, "composition_controller_command", side_effect=replay):
                controls["independentRestores"] = frozenset(projects[:2])
                for project in projects:
                    foundation.run("dotnet", "restore", str(project), "--locked-mode",
                                   "--configfile", str(config))
                self.assertEqual(["--no-dependencies" in arguments for arguments in calls], [True, True, False])
                self.assertEqual(controls["independentlyRestored"], set(projects[:2]))
                with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
                    foundation.run("dotnet", "restore", str(projects[0]), "--force-evaluate",
                                   "--configfile", str(config))
                self.assertEqual(len(calls), 3)

    def test_modeled_architecture_command_binds_original_graphs_and_rejects_context_substitution(self):
        import hashlib
        import uuid
        import conformance_case_catalog as catalog
        import conformance_evidence as evidence
        import conformance_sdk_checks as sdk
        import xml.etree.ElementTree as ET

        for defect in ("none", "missing-context", "foreign-scope", "changed-input", "changed-after", "changed-runner"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                manifest_path = "stores/compatibility-architecture/manifest.json"
                files = {}
                for path, data in (
                        (manifest_path, b"{}"), ("stores/graph.input", b"original"),
                        *((f"stores/graph-{index}.input", b"original") for index in range(32))):
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    sdk.write_new(target, data)
                    files[path] = hashlib.sha256(data).hexdigest()
                map_path = "proofs/compatibility-architecture-inputs.json"
                map_raw = evidence.canonical_bytes(files)
                sdk.write_new(root / map_path, map_raw)
                prepared = {
                    "qualification": False, "profileComplete": False, "fixtureGraphs": 22, "requiredRealScans": 8,
                    "manifestPath": manifest_path, "manifestSha256": files[manifest_path],
                    "inputMapPath": map_path, "inputMapSha256": hashlib.sha256(map_raw).hexdigest(),
                    "inputCount": len(files), "lockDerivationsSha256": "a" * 64}
                assembly = root / "stores/runtime/Hoard.Architecture.Tests.dll"
                assembly.parent.mkdir()
                sdk.write_new(assembly, b"modeled-image")
                sdk.write_new(root / "runtime-owner.json", b"{}")
                manifest = {
                    "attemptId": str(uuid.uuid4()), "purpose": "execution",
                    "runInputsPath": "proofs/modeled-inputs.json",
                    "assemblies": [{"path": assembly.relative_to(root).as_posix()}],
                    "expected": [
                        {"testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
                         "bindingId": binding, "caseId": case}
                        for identity, (binding, case) in catalog.architecture_runtime_tests().items()]}
                if defect == "changed-input":
                    (root / "stores/graph.input").chmod(0o600)
                    (root / "stores/graph.input").write_bytes(b"changed")
                def execute(*args, **kwargs):
                    self.assertLessEqual(len(kwargs["execution_inputs"]), 16)
                    if defect == "changed-after":
                        changed = root / "stores/graph.input"
                        changed.chmod(0o600)
                        changed.write_bytes(b"changed")
                    return SimpleNamespace(exit_code=0)

                command = mock.Mock(side_effect=execute)
                run = SimpleNamespace(root=root, command=command)
                scope = None if defect == "foreign-scope" else ("compatibility", "architecture")
                runner = {
                    "prefix": ("dotnet", "exec", "--fx-version", "10.0.100",
                               "/modeled/toolchain/sdk/10.0.100/vstest.console.dll"),
                    "inputFiles": {"proofs/sdk-vstest-inputs.json": "b" * 64}}
                with mock.patch.object(sdk, "category_command_proof"), \
                        mock.patch.object(
                            sdk, "runtime_runner", return_value=runner,
                            side_effect=[runner, {**runner, "inputFiles": {"proofs/sdk-vstest-inputs.json": "c" * 64}}]
                            if defect == "changed-runner" else None) as frozen_runner:
                    if defect not in ("none", "changed-after", "changed-runner"):
                        with self.assertRaisesRegex(evidence.ConformanceError,
                                                    "InputChanged" if defect == "changed-input" else "WitnessMissing"):
                            sdk.runtime_command(
                                run, assembly, manifest, category_scope=scope,
                                architecture_preparation=None if defect == "missing-context" else prepared)
                        command.assert_not_called()
                        continue
                    if defect in ("changed-after", "changed-runner"):
                        with self.assertRaisesRegex(evidence.ConformanceError, "InputChanged"):
                            sdk.runtime_command(
                                run, assembly, manifest, category_scope=scope, architecture_preparation=prepared)
                        self.assertEqual(1, command.call_count)
                        continue
                    sdk.runtime_command(run, assembly, manifest, category_scope=scope, architecture_preparation=prepared)
                selected = command.call_args.kwargs["execution_inputs"]
                self.assertTrue({manifest_path, map_path} <= set(selected))
                self.assertIn("proofs/sdk-vstest-inputs.json", selected)
                self.assertEqual(tuple(command.call_args.args[0][:len(runner["prefix"])]), runner["prefix"])
                self.assertEqual(frozen_runner.call_count, 2)
                self.assertEqual(len(selected), len(set(selected)))
                settings = ET.fromstring((root / f'proofs/settings-{manifest["attemptId"]}.runsettings').read_bytes())
                self.assertEqual(settings.findtext("./RunConfiguration/EnvironmentVariables/HOARD_FOUNDATION_EVIDENCE"),
                                 str(root / manifest_path))

    def test_architecture_runtime_manifest_rejects_missing_parameters_and_foreign_tests(self):
        import conformance_case_catalog as catalog
        import conformance_evidence as evidence
        import conformance_sdk_checks as sdk

        tests = catalog.architecture_runtime_tests()
        self.assertTrue(all(binding == "none" for binding, _ in tests.values()))
        required = {identity for case in catalog.expected_cases("compatibility")
                    for identity in case.witnesses if identity.startswith("Hoard.Architecture.Tests.")}
        self.assertTrue(required <= tests.keys())
        manifest = {"expected": [
            {"testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
             "bindingId": binding, "caseId": case}
            for identity, (binding, case) in tests.items()]}
        self.assertEqual(sdk._category_manifest_tests(("compatibility", "architecture"), manifest), tests)
        for defect in ("omitted-parameter", "foreign", "binding", "case"):
            changed = evidence.load_json(evidence.canonical_bytes(manifest))
            if defect == "omitted-parameter":
                index = next(index for index, row in enumerate(changed["expected"])
                             if "Every_production_owner_rejects_actual" in row["testIdentity"])
                changed["expected"].pop(index)
            elif defect == "foreign":
                changed["expected"][0]["testIdentity"] = "Hoard.Architecture.Tests.Foreign"
            else:
                changed["expected"][0]["bindingId" if defect == "binding" else "caseId"] = "foreign"
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "WitnessMissing"):
                sdk._category_manifest_tests(("compatibility", "architecture"), changed)

    def test_modeled_architecture_preparation_requires_every_paired_fixture_and_real_scan(self):
        import conformance_case_catalog as catalog
        import conformance_evidence as evidence
        import conformance_inherited as inherited
        import foundation_evidence as foundation

        for defect in ("none", "missing-fixture", "missing-scan", "duplicate-scan", "changed-source",
                       "missing-restored-project", "foreign-reference"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                source = root / "stores/source"
                fixture = source / "tests/fixtures/architecture"
                (fixture / "Cycles").mkdir(parents=True)
                (fixture / "ownership.json").write_bytes(b"{}")
                (fixture / "Cycles/graph.json").write_bytes(b"{}")
                (fixture / "Helper.csproj").write_text("<Project/>")
                (fixture / "Parent.csproj").write_text(
                    '<Project><ItemGroup><ProjectReference Include="'
                    + ("../Foreign.csproj" if defect == "foreign-reference" else "Helper.csproj")
                    + '"/></ItemGroup></Project>')
                graphs = {name: {"projects": []} for name in (
                    "permitted", "identity-hosting", *(name for rows in catalog.ARCHITECTURE_RUNTIME_ROWS.values()
                                                      for name in rows))}
                scans = [{"scanId": name} for name in (
                    "platform", "provider:Hoard.Fixtures.Protocol", "provider:Hoard.Fixtures.Metadata",
                    "provider:Hoard.Fixtures.Artifact.One", "provider:Hoard.Fixtures.Artifact.Two",
                    "provider:Hoard.Fixtures.Identity", "host:One", "host:Two")]
                if defect == "missing-fixture":
                    del graphs["identity-hosting"]
                elif defect == "missing-scan":
                    scans.pop()
                elif defect == "duplicate-scan":
                    scans[-1] = scans[0]
                target = root / "stores/compatibility-architecture"
                state = {"lockDerivations": []}

                def prepare_graphs(*args):
                    restored = set(state.get("independentRestores", ()))
                    if defect == "missing-restored-project" and restored:
                        restored.pop()
                    state["independentlyRestored"] = restored
                    return graphs, {}

                with mock.patch.object(inherited, "controller_transport", return_value=contextlib.nullcontext(state)), \
                        mock.patch.object(foundation, "source_hashes", side_effect=[
                            {"source": "a"}, {"source": "b" if defect == "changed-source" else "a"}]), \
                        mock.patch.object(foundation, "packages", return_value=(
                            {}, [], target / "NuGet.Config")), \
                        mock.patch.object(foundation, "hosts", return_value=[]), \
                        mock.patch.object(foundation, "architecture", side_effect=prepare_graphs) as architecture, \
                        mock.patch.object(foundation, "real_architecture", return_value=scans) as real_scans, \
                        contextlib.redirect_stdout(io.StringIO()):
                    if defect != "none":
                        with self.assertRaisesRegex(evidence.ConformanceError,
                                                    "InputChanged" if defect == "changed-source" else "WitnessMissing"):
                            inherited.prepare_architecture_evidence(ROOT, root, source)
                        continue
                    result = inherited.prepare_architecture_evidence(ROOT, root, source)
                architecture.assert_called_once_with(source, target, target / "NuGet.Config", False)
                real_scans.assert_called_once()
                self.assertFalse(result["qualification"])
                self.assertFalse(result["profileComplete"])
                selected = evidence.load_json((root / result["inputMapPath"]).read_bytes())
                self.assertEqual(len(selected), result["inputCount"])
                self.assertEqual(dict(evidence.input_manifest(root, list(selected))), selected)
                self.assertEqual(inherited.admit_architecture_preparation(root, result)[1], selected)
                self.assertEqual(selected[result["manifestPath"]], result["manifestSha256"])
                document = evidence.load_json((root / result["manifestPath"]).read_bytes())
                self.assertEqual(document["architecture"], graphs)
                self.assertEqual(document["realArchitecture"], scans)

    def test_architecture_child_requires_explicit_compatibility_profile_before_preparation(self):
        import uuid
        import conformance_evidence as evidence
        import conformance_inherited as inherited
        import conformance_legacy as legacy

        for profile in ("compatibility", "composition", "baseline"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                (root / "stores").mkdir()
                run_id = str(uuid.uuid4())
                request = {
                    "schemaVersion": 1, "phase": "architecture", "owner": str(root), "repository": str(ROOT),
                    "runId": run_id, "rootId": "modeled-root", "source": "stores/source",
                    "baselineSeal": None, "sdkPackage": None, "loggerPath": None}
                for path, value in (
                        ("stores/request.json", request),
                        ("ownership.json", {"schemaVersion": 2, "state": "Active", "runId": run_id,
                                            "rootId": "modeled-root"}),
                        ("proofs/preflight.json", {"schemaVersion": 1, "qualification": False, "profileId": profile})):
                    (root / path).write_bytes(evidence.canonical_bytes(value))
                output = root / "proofs/result.json"
                with mock.patch.object(legacy, "native_preparation_group", return_value=contextlib.nullcontext(
                        {"invocations": [], "inputSnapshots": []})) as group, \
                        mock.patch.object(inherited, "prepare_architecture_evidence",
                                          return_value={"qualification": False}) as prepare, \
                        contextlib.redirect_stdout(io.StringIO()):
                    status = inherited.controller_child_main([
                        "--request", str(root / "stores/request.json"), "--output", str(output)])
                if profile == "compatibility":
                    self.assertEqual(status, 0)
                    prepare.assert_called_once_with(ROOT, root, root / "stores/source")
                    group.assert_called_once()
                    self.assertEqual(evidence.load_json(output.read_bytes())["phase"], "architecture")
                else:
                    self.assertEqual(status, 2)
                    prepare.assert_not_called()
                    group.assert_not_called()
                    self.assertFalse(output.exists())

    def test_architecture_workflow_requires_released_owner_and_retained_manifest_identity(self):
        import hashlib
        import conformance_evidence as evidence
        import conformance_inherited as inherited

        workflow = (ROOT / ".github/workflows/conformance.yml").read_text()
        script = workflow.split('--profile compatibility --evidence "$private_parent/run"', 1)[1].split(
            "<<'PY'\n", 1)[1].split("\n          PY", 1)[0]
        code = compile(textwrap.dedent(script), "<architecture-workflow>", "exec")
        for defect in ("none", "live", "profile", "path", "manifest", "inputs", "qualification",
                       "missing-version", "missing-axis", "missing-observation", "runtime-receipt", "missing-binary"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                manifest = "stores/compatibility-architecture/manifest.json"
                raw = evidence.canonical_bytes({manifest: "a" * 64})
                architecture = {
                    "qualification": False, "profileComplete": False, "fixtureGraphs": 22, "requiredRealScans": 8,
                    "manifestPath": manifest, "manifestSha256": "b" * 64 if defect == "manifest" else "a" * 64,
                    "inputMapPath": "../outside" if defect == "path" else "proofs/compatibility-architecture-inputs.json",
                    "inputMapSha256": "b" * 64 if defect == "inputs" else hashlib.sha256(raw).hexdigest(),
                    "inputCount": 1, "parentSha256": "c" * 64, "nativeInvocations": {"parentSha256": "c" * 64}}
                summary = {
                    "qualification": defect == "qualification", "profileComplete": False,
                    "processResourcesReleased": True, "architecturePreparation": architecture}
                for key, scope, count in (("architectureRuntime", "architecture", 88),
                                          ("versionRuntime", "version", 114), ("binaryRuntime", "binary", 7)):
                    observed = {
                        "qualification": False, "profileComplete": False, "scope": f"{scope}-runtime-diagnostic",
                        "passedParameters": count, **{field: "d" * 64 for field in (
                            "inputsSha256", "postInputsSha256", "discoverySha256", "completionSha256",
                            "runtimeProofsSha256", "nativeParentSha256")}}
                    if scope == "version":
                        observed["admittedObservations"] = 169 if defect == "missing-observation" else 170
                        if defect == "missing-axis":
                            observed["passedParameters"] -= 1
                    (root / f"proofs/compatibility-{scope}-runtime-summary.json").write_bytes(
                        evidence.canonical_bytes(observed))
                    summary[key] = dict(observed)
                if defect == "missing-version":
                    del summary["versionRuntime"]
                if defect == "runtime-receipt":
                    summary["versionRuntime"]["nativeParentSha256"] = "e" * 64
                if defect == "missing-binary":
                    del summary["binaryRuntime"]
                owner = {"state": "Active" if defect == "live" else "Released", "runId": "modeled", "rootId": "modeled"}
                preflight = {"profileId": "baseline" if defect == "profile" else "compatibility"}
                for path, data in (
                        ("proofs/compatibility-diagnostic-summary.json", evidence.canonical_bytes(summary)),
                        ("proofs/compatibility-architecture-inputs.json", raw),
                        ("ownership.json", evidence.canonical_bytes(owner)),
                        ("proofs/preflight.json", evidence.canonical_bytes(preflight))):
                    (root / path).write_bytes(data)
                output = io.StringIO()
                with mock.patch.object(sys, "argv", ["workflow", str(root)]), \
                        mock.patch.object(inherited, "verify_controller_invocations") as verify, \
                        contextlib.redirect_stdout(output):
                    if defect == "none":
                        exec(code, {"__name__": "__main__"})
                        verify.assert_called_once_with(root, architecture["nativeInvocations"], "architecture",
                                                       owner["runId"], owner["rootId"])
                        self.assertFalse(evidence.load_json(output.getvalue().encode())["qualification"])
                    else:
                        with self.assertRaisesRegex(SystemExit, "WitnessMissing"):
                            exec(code, {"__name__": "__main__"})
                        verify.assert_not_called()

    def test_selected_runtime_input_bytes_survive_store_release_and_reject_changed_or_escaping_sources(self):
        import hashlib
        import shutil
        import uuid
        import conformance_composition_checks as checks
        import conformance_evidence as evidence

        for defect in ("none", "changed", "conflict", "symlink", "configuration", "hardlink"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                contents = {
                    "stores/runtime.dll": b"modeled-image", "stores/duplicate.dll": b"modeled-image",
                    "stores/packages.lock.json": b"{}", "stores/candidate.NuGet.Config":
                    evidence.synthetic_nuget_configuration(root / "feed/candidate"),
                    "feed/candidate/Modeled.Package.0.1.0.nupkg": b"modeled-package",
                    "runtime-owner.json": b"modeled-owner"}
                for path, data in contents.items():
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                hashes = {path: hashlib.sha256(data).hexdigest() for path, data in contents.items()}
                inputs = {
                    "runId": str(uuid.uuid4()), "invocationGroupId": str(uuid.uuid4()),
                    "runtimeAssemblies": {path: hashed for path, hashed in hashes.items() if path.endswith(".dll")},
                    "locks": {"stores/packages.lock.json": hashes["stores/packages.lock.json"]},
                    "packages": [{"packageId": "Modeled.Package", "version": "0.1.0",
                                  "sha256": hashes["feed/candidate/Modeled.Package.0.1.0.nupkg"]}]}
                record = {"inputFiles": {path: hashes[path] for path in (
                    "runtime-owner.json", "stores/candidate.NuGet.Config", "stores/runtime.dll")}}
                image = root / "stores/runtime.dll"
                if defect == "changed":
                    image.write_bytes(b"changed")
                elif defect == "conflict":
                    record["inputFiles"]["stores/runtime.dll"] = "0" * 64
                elif defect == "symlink":
                    image.unlink()
                    image.symlink_to(root / "runtime-owner.json")
                elif defect == "configuration":
                    path = root / "stores/candidate.NuGet.Config"
                    path.write_bytes(b"<configuration/>")
                    record["inputFiles"]["stores/candidate.NuGet.Config"] = evidence.file_sha256(path)
                elif defect == "hardlink":
                    alias = root / "unselected-owner"
                    alias.write_bytes(contents["runtime-owner.json"])
                    alias.chmod(0o644)
                    (root / "runtime-owner.json").unlink()
                    (root / "runtime-owner.json").hardlink_to(alias)
                if defect != "none":
                    with self.assertRaises(evidence.ConformanceError):
                        checks._retain_composition_inputs(SimpleNamespace(root=root), inputs, record)
                    self.assertEqual((root / "runtime-owner.json").read_bytes(), b"modeled-owner")
                    if defect == "hardlink":
                        self.assertEqual(alias.stat().st_mode & 0o777, 0o644)
                    continue
                paths = checks._retain_composition_inputs(SimpleNamespace(root=root), inputs, record)
                snapshot = evidence.load_json((root / paths[0]).read_bytes())
                self.assertFalse(snapshot["qualification"])
                self.assertEqual(snapshot["inputSha256"], evidence.digest(inputs))
                self.assertEqual(snapshot["files"], {
                    path: hashed for path, hashed in hashes.items() if path != "runtime-owner.json"})
                self.assertEqual(len(paths), 5)
                self.assertIn("runtime-owner.json", paths)
                shutil.rmtree(root / "stores")
                shutil.rmtree(root / "feed")
                for path, hashed in snapshot["files"].items():
                    if path == "stores/candidate.NuGet.Config":
                        self.assertEqual(hashlib.sha256(evidence.synthetic_nuget_configuration(
                            root / "feed/candidate")).hexdigest(), hashed)
                        continue
                    retained = root / f"proofs/composition-runtime-inputs/{hashed}"
                    self.assertEqual(retained.read_bytes(), contents[path])
                    self.assertEqual(retained.stat().st_mode & 0o777, 0o400)
                self.assertTrue(all(str(root).encode() not in (root / path).read_bytes() for path in paths))

    def test_prepared_formatting_requires_exact_native_receipts_and_unchanged_closure(self):
        import hashlib
        import time
        import conformance_composition_checks as checks
        import conformance_evidence as evidence
        for mutation in ("none", "solution", "unbound-solution", "foreign-root", "argv", "cwd", "inputs", "sequence", "hash",
                         "retained", "live-child", "failed", "changed-source", "changed-closure", "symlink",
                         "duplicate", "missing-phase", "missing-assets"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                projects, files = {}, {}
                for phase in ("foundation", "lifecycle", "configuration", "discovery"):
                    directory = root / "stores" / ("inherited-controller-" + phase)
                    (directory / "obj").mkdir(parents=True)
                    project = directory / "Example.csproj"
                    project.write_bytes(b"<Project/>")
                    assets = directory / "obj/project.assets.json"
                    assets.write_bytes(b"{}")
                    projects[phase] = [project.relative_to(root).as_posix()]
                    files.update({path.relative_to(root).as_posix(): evidence.file_sha256(path)
                                  for path in (project, assets)})
                source = root / "independent.cs"
                source.write_bytes(b"class Original {}")
                outside = root / "not-bound.cs"
                outside.write_bytes(source.read_bytes())
                files[source.name] = evidence.file_sha256(source)
                solution = None
                if mutation in ("solution", "unbound-solution"):
                    solution = root / "source/Hoard.slnx"
                    solution.parent.mkdir()
                    solution.write_bytes(b"<Solution/>")
                    if mutation == "solution":
                        files[solution.relative_to(root).as_posix()] = evidence.file_sha256(solution)
                if mutation == "duplicate":
                    projects["foundation"] *= 2
                elif mutation == "missing-phase":
                    del projects["foundation"]
                elif mutation == "missing-assets":
                    del files["stores/inherited-controller-foundation/obj/project.assets.json"]
                descriptor = root / "proofs/format-projects.json"
                descriptor.write_bytes(evidence.canonical_bytes(projects))
                closure = root / "proofs/closure.json"
                closure.write_bytes(evidence.canonical_bytes(files))
                controllers = {"formatting": {"path": descriptor.relative_to(root).as_posix(),
                                             "sha256": evidence.file_sha256(descriptor)}}
                run = SimpleNamespace(root=root, run_id="run", root_id="root", command_sequence=0)
                record = {}

                def command(arguments, **kwargs):
                    self.assertTrue(kwargs["record_execution"])
                    self.assertEqual("build", kwargs["kind"])
                    self.assertEqual(["dotnet", "format"], arguments[:2])
                    self.assertEqual(["--verify-no-changes", "--no-restore", "-v", "quiet"], arguments[3:])
                    self.assertEqual(Path(arguments[2]).parent, kwargs["cwd"])
                    self.assertEqual(3 if arguments[2].endswith(".slnx") else 4, len(kwargs["execution_inputs"]))
                    run.command_sequence += 1
                    now = time.monotonic() * 1000
                    record.update(
                        sequence=run.command_sequence, runId="run", rootId="root", scope="ordinary",
                        argvSha256=evidence.digest(arguments),
                        cwdSha256=hashlib.sha256(str(kwargs["cwd"]).encode()).hexdigest(),
                        inputFiles={path: evidence.file_sha256(root / path) for path in kwargs["execution_inputs"]},
                        groupState="Exited", exitCode=0, diagnosticCode="None", startedMs=now, endedMs=now)
                    if mutation in ("foreign-root", "argv", "cwd", "inputs", "sequence", "retained"):
                        field, value = {
                            "foreign-root": ("rootId", "foreign"), "argv": ("argvSha256", "0" * 64),
                            "cwd": ("cwdSha256", "0" * 64), "inputs": ("inputFiles", {}),
                            "sequence": ("sequence", 99), "retained": ("groupState", "Retained"),
                        }[mutation]
                        record[field] = value
                    if mutation in ("changed-source", "changed-closure"):
                        changed = source if mutation == "changed-source" else closure
                        changed.chmod(0o600)
                        changed.write_bytes(b"changed")
                    elif mutation == "symlink":
                        source.unlink()
                        source.symlink_to(outside)
                    return SimpleNamespace(
                        exit_code=1 if mutation == "failed" else 0, events=(),
                        execution_record_sha256="0" * 64 if mutation == "hash" else evidence.digest(record))

                run.command = mock.Mock(side_effect=command)
                run.read_execution_record = mock.Mock(side_effect=lambda sequence: evidence.canonical_bytes(record))
                run.live_children = mock.Mock(return_value=[1] if mutation == "live-child" else [])
                if mutation in ("none", "solution"):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        observed = checks._format_prepared_controllers(
                            run, controllers, files, closure, solution=solution)
                    self.assertFalse(observed["qualification"])
                    self.assertEqual(solution is not None, observed["solutionFormatting"])
                    scopes = [*projects, *(("solution",) if solution else ())]
                    self.assertEqual(scopes, [row["controller"] for row in observed["commands"]])
                    self.assertEqual(len(scopes), run.command.call_count)
                    self.assertEqual([
                        {"qualification": False, "phase": "inherited-prepared-formatting",
                         "controller": phase, "command": number}
                        for number, phase in enumerate(scopes, 1)
                    ], [evidence.load_json(line.encode()) for line in output.getvalue().splitlines()])
                else:
                    code = ("InputChanged" if mutation.startswith("changed-") or mutation == "symlink" else
                            "CommandFailed" if mutation == "failed" else
                            "EvidenceSchemaInvalid" if mutation == "missing-phase" else "ProofMismatch")
                    with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(
                            evidence.ConformanceError, code):
                        checks._format_prepared_controllers(run, controllers, files, closure, solution=solution)
                    if mutation in ("duplicate", "missing-phase", "missing-assets", "unbound-solution"):
                        run.command.assert_not_called()

    def test_solution_formatter_preparation_restores_missing_projects_with_locked_inputs(self):
        import conformance_composition_checks as checks
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "source"
            source.mkdir()
            (root / "proofs").mkdir()
            (source / "Hoard.slnx").write_text(
                '<Solution><Project Path="One/One.csproj"/><Project Path="Two/Two.csproj">'
                '<Build Project="false"/></Project></Solution>')
            original = b'{"version":1,"dependencies":{"net10.0":{}}}'
            for name in ("One", "Two"):
                directory = source / name
                directory.mkdir()
                (directory / (name + ".csproj")).write_bytes(b"<Project/>")
                (directory / "packages.lock.json").write_bytes(original)
            (source / "One/obj").mkdir()
            (source / "One/obj/project.assets.json").write_bytes(b"existing")
            run = SimpleNamespace(root=root)
            config, feed = root / "NuGet.Config", root / "feed"
            feed.mkdir()

            def restore(owner, arguments, **kwargs):
                self.assertIs(run, owner)
                self.assertEqual(["dotnet", "restore", str(source / "Two/Two.csproj"),
                                  "--locked-mode", "--configfile", str(config)], arguments[:6])
                self.assertNotIn("--force-evaluate", arguments)
                directory = source / "Two/obj"
                directory.mkdir()
                (directory / "project.assets.json").write_bytes(b"fresh")

            output = io.StringIO()
            with contextlib.redirect_stdout(output), mock.patch.object(
                    checks.baselines, "_command", side_effect=restore) as command:
                checks._prepare_solution_formatting(run, source, config, feed)
            self.assertEqual(1, command.call_count)
            self.assertEqual({"qualification": False, "phase": "inherited-solution-assets", "project": 2},
                             json.loads(output.getvalue()))
            for name in ("One", "Two"):
                self.assertEqual(original, (source / name / "packages.lock.json").read_bytes())

    def test_controller_failure_exposes_only_revalidated_closed_progress(self):
        import conformance_composition_checks as checks
        import conformance_evidence as evidence
        for private in (False, True):
            with self.subTest(private=private), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                for directory in ("proofs", "stores", "diagnostics", "source/scripts"):
                    (root / directory).mkdir(parents=True, exist_ok=True)
                (root / "source/scripts/conformance_inherited.py").write_bytes(b"controller")
                run = SimpleNamespace(root=root, run_id="run", root_id="root", command_sequence=0)

                def fail(*args, **kwargs):
                    run.command_sequence = 1
                    (root / "diagnostics/command-0001.jsonl").write_bytes(
                        b'{"event":"control","code":"None","value":2}\n'
                        + (b"private-canary\n" if private else
                           b'{"event":"control","code":"OutputLimitExceeded","value":0}\n'))
                    raise evidence.ConformanceError("OutputLimitExceeded")

                run.command = mock.Mock(side_effect=fail)
                output = io.StringIO()
                with contextlib.redirect_stdout(output), self.assertRaises(evidence.ConformanceError):
                    checks._controller_phase(run, ROOT, root / "source", "historical")
                if private:
                    self.assertEqual("", output.getvalue())
                else:
                    value = evidence.load_json(output.getvalue().encode())
                    self.assertEqual("historical", value["scope"])
                    self.assertEqual([2, 0], [event["value"] for event in value["events"]])
                    self.assertEqual([], value["locations"])
                self.assertNotIn("private-canary", output.getvalue())

    def test_controller_failure_location_decodes_only_known_script_numbers(self):
        import conformance_composition_checks as checks
        import conformance_evidence as evidence
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            checks._controller_incomplete("controllers", "OutputLimitExceeded", [
                evidence.canonical_bytes({"event": "control", "code": "OutputLimitExceeded", "value": value})
                for value in (300018, 9900001, 200000)])
        self.assertEqual([{"source": "conformance_lock_preparation.py", "line": 18}],
                         evidence.load_json(output.getvalue().encode())["locations"])

    def test_controller_phase_requires_native_parent_output_and_complete_progress(self):
        import hashlib
        import conformance_composition_checks as checks
        import conformance_evidence as evidence
        from conformance_execution import CommandResult
        for phase, mutation in ((phase, mutation) for phase in ("historical", "mutations", "reference", "architecture")
                                for mutation in ("none", "changed-output", "missing-phase", "retained-process",
                                                 "child-failed", "missing-invocation", "foreign-invocation",
                                                 "duplicate-invocation", "missing-input-snapshot",
                                                 "changed-input-snapshot")):
            with self.subTest(phase=phase, mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                (root / "proofs/composition-inputs.json").write_bytes(b"{}")
                reference = None
                if phase == "reference":
                    reference = {}
                    for role in ("manifest", "inputMap"):
                        path = root / "proofs" / (role + ".json")
                        path.write_bytes(b"{}")
                        reference[role + "Path"] = path.relative_to(root).as_posix()
                        reference[role + "Sha256"] = evidence.file_sha256(path)
                source = root / "stores/source"
                (source / "scripts").mkdir(parents=True)
                (source / "scripts/conformance_inherited.py").write_bytes(b"frozen controller")
                run = SimpleNamespace(root=root, run_id="run", root_id="root", command_sequence=0)
                record = {}

                def command(arguments, **kwargs):
                    request = Path(arguments[arguments.index("--request") + 1])
                    output = Path(arguments[arguments.index("--output") + 1])
                    invocation = {
                        "schemaVersion": 1, "qualification": False, "groupState": "Borrowed",
                        "groupPid": 101 if mutation == "foreign-invocation" else 100,
                        "groupStartSha256": "a" * 64, "childPid": 102, "childStartSha256": "b" * 64,
                        "childState": "Exited", "exitCode": 0, "argvSha256": "c" * 64,
                        "cwdSha256": "d" * 64, "stdinSha256": None}
                    invocations = ([] if mutation == "missing-invocation" else
                                   [invocation] * (2 if mutation == "duplicate-invocation" else 1))
                    child_result = {"seal": "bound", **({"invocation": invocation} if phase == "reference" else {})}
                    snapshot = {
                        "qualification": False, "inputClosureComplete": False, "scope": "selected-declared-inputs",
                        "files": {"stores/input": "e" * 64}, "sha256": evidence.digest({"stores/input": "e" * 64})}
                    if mutation == "changed-input-snapshot":
                        snapshot["sha256"] = "0" * 64
                    raw = evidence.canonical_bytes({
                        "schemaVersion": 3, "qualification": False, "phase": phase,
                        "runId": "run", "rootId": "root", "result": child_result,
                        "invocations": invocations,
                        "inputSnapshots": [] if mutation == "missing-input-snapshot" else
                        [snapshot for _ in invocations],
                    })
                    output.write_bytes(raw + b"\n" if mutation == "changed-output" else raw)
                    record.update(
                        runId="run", rootId="root", argvSha256=evidence.digest(arguments),
                        cwdSha256=hashlib.sha256(str(source).encode()).hexdigest(),
                        inputFiles={path: evidence.file_sha256(root / path) for path in kwargs["execution_inputs"]},
                        outputFiles={output.relative_to(root).as_posix(): hashlib.sha256(raw).hexdigest()},
                        childPid=100, childStartSha256="a" * 64,
                        groupState="Retained" if mutation == "retained-process" else "Exited",
                        exitCode=0, diagnosticCode="None",
                    )
                    self.assertIn(request.relative_to(root).as_posix(), kwargs["execution_inputs"])
                    self.assertEqual((output.relative_to(root).as_posix(),), kwargs["execution_outputs"])
                    if phase == "mutations":
                        self.assertIn("proofs/composition-inputs.json", kwargs["execution_inputs"])
                    if phase == "reference":
                        self.assertEqual(evidence.load_json(request.read_bytes())["reference"], reference)
                        self.assertTrue({reference["manifestPath"], reference["inputMapPath"]}
                                        <= set(kwargs["execution_inputs"]))
                    run.command_sequence = 1
                    ordinals = ((0,) if phase == "reference" else (1, 0) if phase == "architecture"
                                else (2, 3, 4, 0) if phase == "historical"
                                else (*range(1, 25), 0))
                    if mutation == "missing-phase":
                        ordinals = ordinals[:-1]
                    events = tuple({"event": "control", "code": "None", "value": number}
                                   for number in ordinals)
                    if mutation == "child-failed":
                        events = (*events[:2], MappingProxyType({
                            "event": "control", "code": "OutputLimitExceeded", "value": 0}))
                    return CommandResult(0, events, 1, evidence.digest(record))

                run.command = mock.Mock(side_effect=command)
                run.read_execution_record = mock.Mock(side_effect=lambda sequence: evidence.canonical_bytes(record))
                if mutation == "none":
                    result, parent, invocations = checks._controller_phase(
                        run, ROOT, source, phase, reference=reference)
                    self.assertEqual("bound", result["seal"])
                    self.assertEqual(evidence.digest(record), parent)
                    self.assertEqual(1, invocations["count"])
                else:
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output), self.assertRaisesRegex(
                            evidence.ConformanceError, "OutputLimitExceeded" if mutation == "child-failed"
                            else "ProofMismatch"):
                        checks._controller_phase(run, ROOT, source, phase, reference=reference)
                    if mutation == "child-failed":
                        expected = ([0, 0] if phase == "reference" else [1, 0, 0] if phase == "architecture"
                                    else [2, 3, 0] if phase == "historical" else [1, 2, 0])
                        self.assertEqual(expected, [event["value"] for event in
                                                   evidence.load_json(output.getvalue().encode())["events"]])

    def test_workflow_observes_failed_controller_before_enforcing_diagnostic_exit(self):
        workflow = (ROOT / ".github/workflows/conformance-composition.yml").read_text()
        script = textwrap.dedent(workflow.split("        run: |\n", 1)[1])
        for status in (0, 1, 2):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temporary:
                environment = {
                    **os.environ, "GITHUB_WORKSPACE": str(Path(temporary) / "workspace"),
                    "GITHUB_RUN_ID": "control", "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": "a" * 40}
                controls = (f"bash() {{ return {status}; }}\n"
                            "python3() { printf 'projection-reached\\n'; return 0; }\n")
                result = subprocess.run(
                    ["/bin/bash", "-c", controls + script], cwd=ROOT, env=environment,
                    capture_output=True, timeout=10)
                self.assertEqual(result.stdout, b"projection-reached\n")
                self.assertEqual(result.stderr, b"")
                self.assertEqual(result.returncode == 0, status == 2)

    def test_workflow_checks_retained_historical_seal_after_stores_are_released(self):
        import hashlib
        import conformance_composition_checks as composition
        import conformance_evidence as evidence
        import conformance_inherited as inherited
        workflow = (ROOT / ".github/workflows/conformance-composition.yml").read_text()
        script = workflow.split("<<'PY'\n", 1)[1].split("\n          PY", 1)[0]
        code = compile(textwrap.dedent(script), "<composition-workflow>", "exec")
        for mutation in ("none", "changed-bytes", "resealed-foreign-root", "false-qualification",
                         "missing-mutation", "missing-repair", "mutation-qualification",
                         "missing-adapter", "missing-discovery-suite", "tooling-skip",
                         "missing-tooling-test", "stale-tooling-source", "tooling-native-claim",
                         "missing-feed-package", "missing-retained-binary", "missing-material-graph",
                         "missing-material-journey", "materials-qualification", "materials-foreign-manifest",
                         "reference-modules", "reference-native", "reference-inputs",
                         "reference-parent", "reference-output", "reference-child-owner",
                         "reference-child-start", "reference-child-live", "reference-child-input",
                         "native-invocation-omitted", "native-invocation-output",
                         "native-invocation-count", "native-invocation-closure", "native-input-digest",
                         "native-input-closure", "native-input-path",
                         "missing-report-control", "missing-semantic-control", "missing-summary",
                         "missing-summary-incomplete-tooling", "missing-summary-foreign-tooling",
                         "missing-summary-unsafe-tooling", "missing-summary-missing-tooling",
                         "missing-summary-foreign-source"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                inputs = {"runId": "run", "sourceRevision": "a" * 40, "sourceState": "clean-ci",
                          "mode": "diagnostic", "profileId": "composition"}
                inputs["sourceManifest"] = {"tests/tooling/test_control.py": "a" * 64}
                inputs["sourceManifestSha256"] = evidence.digest(inputs["sourceManifest"])
                tooling = {
                    "schemaVersion": 1, "qualification": False, "nativeContainment": False,
                    "role": "trusted-tooling-supervisor", "runId": "run", "rootId": "root",
                    "startedMs": 1, "endedMs": 2,
                    "sourceManifestSha256": "b" * 64 if mutation == "stale-tooling-source"
                    else inputs["sourceManifestSha256"],
                    "result": {
                        "mode": "diagnostic", "qualification": False, "scope": "tooling", "code": "None",
                        "tests": 1, "failures": 0, "errors": 0,
                        "skipped": 1 if mutation == "tooling-skip" else 0,
                        "expectedFailures": 0, "unexpectedSuccesses": 0, "unexpectedDiagnosticBytes": 0,
                        "freeScratchBytes": 123,
                        "failedTests": [], "expectedTests": ["test_control.Case.test_assertion"],
                        "observedTests": [] if mutation == "missing-tooling-test"
                        else ["test_control.Case.test_assertion"],
                    },
                }
                if mutation == "missing-summary-incomplete-tooling":
                    tooling["endedMs"] = 600002
                    tooling["result"].update(code="EvidenceIncomplete", tests=0, observedTests=[])
                elif mutation == "missing-summary-foreign-tooling":
                    tooling["rootId"] = "foreign-root"
                elif mutation == "missing-summary-unsafe-tooling":
                    tooling["result"]["code"] = "private-tooling-canary"
                elif mutation == "missing-summary-foreign-source":
                    inputs["sourceRevision"] = "b" * 40
                baseline = {"runId": "run", "rootId": "root", "qualification": False,
                            "nativeContainment": False, "mode": "preparation",
                            "schemaVersion": 2, "baselineRevision": inherited.BASELINE,
                            "recipeSourceSha256": "b" * 64, "files": {}, "retained": {},
                            "registration": {"assembly": "stores/old/RegistrationConsumer.dll",
                                             "sha256": "c" * 64}}
                for phase, revision, names in (
                        ("configuration", "b80c69fc386541be4f56f6ef2edeca40f43a0e1c",
                         ("LegacyOptions", "LifecycleConsumer")),
                        ("discovery", "7fd73267a5154583363c94e9e85b9bac7d4a16b3",
                         ("RetainedLifecycle", "RetainedConfiguration", "LegacyOptions"))):
                    baseline["retained"][phase] = [{
                        "name": name, "baseline": revision, "assembly": f"stores/{phase}/{name}.dll",
                        "assets": f"stores/{phase}/{name}.assets.json", "sha256": "c" * 64,
                    } for name in names]
                for entry in (baseline["registration"], *baseline["retained"]["configuration"],
                              *baseline["retained"]["discovery"]):
                    for field in ("assembly", "assets"):
                        if field in entry:
                            baseline["files"][entry[field]] = "c" * 64
                if mutation == "resealed-foreign-root":
                    baseline["rootId"] = "foreign-root"
                elif mutation == "false-qualification":
                    baseline["qualification"] = True
                raw = evidence.canonical_bytes(baseline)
                reference_inputs = evidence.canonical_bytes({f"stores/input-{number}": "c" * 64 for number in range(9)})
                reference = {
                    "qualification": False, "moduleCount": 6, "moduleIdsSha256": "a" * 64,
                    "inputMapSha256": hashlib.sha256(reference_inputs).hexdigest(),
                    "argvSha256": "d" * 64, "cwdSha256": "e" * 64,
                    "assemblySha256": "b" * 64, "responseSha256": "c" * 64}
                reference["invocation"] = {
                    "schemaVersion": 1, "qualification": False, "groupState": "Borrowed",
                    "groupPid": 101 if mutation == "reference-child-owner" else 100,
                    "groupStartSha256": "0" * 64 if mutation == "reference-child-start" else "f" * 64,
                    "childPid": 102, "childStartSha256": "1" * 64,
                    "childState": "Running" if mutation == "reference-child-live" else "Exited",
                    "exitCode": 0, "argvSha256": reference["argvSha256"], "cwdSha256": reference["cwdSha256"],
                    "stdinSha256": "0" * 64 if mutation == "reference-child-input" else reference["responseSha256"]}
                reference_output = evidence.canonical_bytes({
                    "schemaVersion": 3, "qualification": False, "phase": "reference",
                    "runId": "run", "rootId": "root", "result": dict(reference),
                    "invocations": [reference["invocation"]], "inputSnapshots": [{
                        "qualification": False, "inputClosureComplete": False, "scope": "selected-declared-inputs",
                        "files": {}, "sha256": evidence.digest({})}]})
                reference_parent = {
                    "runId": "foreign" if mutation == "reference-parent" else "run",
                    "rootId": "root", "sequence": 1, "groupState": "Exited",
                    "childPid": 100, "childStartSha256": "f" * 64,
                    "exitCode": 0, "diagnosticCode": "None",
                    "inputFiles": {"proofs/inherited-reference-inputs.json": reference["inputMapSha256"]},
                    "outputFiles": {"proofs/inherited-reference-result.json":
                                    "0" * 64 if mutation == "reference-output"
                                    else hashlib.sha256(reference_output).hexdigest()}}
                parent_raw = evidence.canonical_bytes(reference_parent)
                (root / "proofs/execution-command-0001.json").write_bytes(parent_raw)
                (root / "proofs/inherited-reference-result.json").write_bytes(reference_output)
                (root / "proofs/inherited-reference-inputs.json").write_bytes(reference_inputs)
                observation_summaries = {}
                snapshots = [{"qualification": False, "inputClosureComplete": False,
                              "scope": "selected-declared-inputs", "files": {}, "sha256": evidence.digest({})}]
                for phase, sequence in (("reference", 1), ("historical", 2), ("controllers", 3), ("mutations", 4)):
                    invocation = {**reference["invocation"], "groupPid": 100, "groupStartSha256": "f" * 64}
                    rows = [] if phase == "controllers" and mutation == "native-invocation-omitted" else [invocation]
                    packet_snapshots = json.loads(json.dumps(snapshots))
                    if phase == "controllers" and mutation == "native-input-closure":
                        packet_snapshots[0]["inputClosureComplete"] = True
                    if phase == "controllers" and mutation == "native-input-path":
                        packet_snapshots[0]["files"] = {"../escape": "e" * 64}
                        packet_snapshots[0]["sha256"] = evidence.digest(packet_snapshots[0]["files"])
                    if phase != "reference":
                        packet = evidence.canonical_bytes({
                            "schemaVersion": 3, "qualification": False, "phase": phase,
                            "runId": "run", "rootId": "root", "result": {}, "invocations": rows,
                            "inputSnapshots": packet_snapshots})
                        command = {**reference_parent, "runId": "run", "sequence": sequence, "outputFiles": {
                            f"proofs/inherited-{phase}-result.json": hashlib.sha256(packet).hexdigest()}}
                        if phase == "controllers" and mutation == "native-invocation-output":
                            command["outputFiles"][f"proofs/inherited-{phase}-result.json"] = "0" * 64
                        parent_bytes = evidence.canonical_bytes(command)
                        (root / f"proofs/inherited-{phase}-result.json").write_bytes(packet)
                        (root / f"proofs/execution-command-{sequence:04}.json").write_bytes(parent_bytes)
                    else:
                        parent_bytes = parent_raw
                        rows = [reference["invocation"]]
                    observation_summaries[phase] = {
                        "qualification": False, "nativeContainment": True, "inputClosureComplete":
                        phase == "controllers" and mutation == "native-invocation-closure",
                        "scope": "borrowed-launch-observations",
                        "count": 0 if phase == "controllers" and mutation == "native-invocation-count" else 1,
                        "sha256": evidence.digest(rows), "sequence": sequence,
                        "inputSnapshotsSha256": ("0" * 64 if phase == "controllers" and
                                                 mutation == "native-input-digest" else
                                                 evidence.digest(packet_snapshots)),
                        "parentSha256": hashlib.sha256(parent_bytes).hexdigest()}
                reference.update(nativeContainment=mutation != "reference-native",
                                 sequence=1, parentSha256=hashlib.sha256(parent_raw).hexdigest(),
                                 inputCount=8 if mutation == "reference-inputs" else 9,
                                 nativeInvocations=observation_summaries["reference"])
                if mutation == "reference-modules":
                    reference["moduleCount"] = 5
                summary = {
                    "qualification": False, "profileComplete": False, "passedComponents": 36,
                    "caseReport": {"qualification": False, "reportState": "Incomplete"},
                    "admittedSnapshots": 110, "processResourcesReleased": True,
                    "inputSha256": evidence.digest(inputs),
                    "historicalNativeInvocations": observation_summaries["historical"],
                    "inheritedRuntime": {
                        "qualification": False, "profileComplete": False, "executionComplete": True,
                        "nativeContainment": True, "controllerNativeContainment": False,
                        "fullControllerAcceptance": False, "historicalBinariesPreparedBeforeCandidate": True,
                        "historicalBaselineSealSha256": hashlib.sha256(raw).hexdigest(),
                        "passedParameters": 525, "scopes": 58, "commands": [{}] * 58,
                        "controllerPreparation": {"discovery": {"manifestSha256": "d" * 64}},
                        "referenceConsumer": reference,
                        "nativeInvocations": {phase: observation_summaries[phase]
                                              for phase in ("controllers", "mutations")},
                        "discoveryMutations": {
                            "qualification": mutation == "mutation-qualification",
                            "mutations": 11 if mutation == "missing-mutation" else 12,
                            "negativeParameters": 29,
                            "repairedParameters": 28 if mutation == "missing-repair" else 29,
                        },
                        "discoveryScenarios": {
                            "qualification": False, "parameters": 137,
                            "adapterScenarios": 3 if mutation == "missing-adapter" else 4,
                            "suites": 9 if mutation == "missing-discovery-suite" else 10,
                        },
                        "discoveryMaterials": {
                            "qualification": mutation == "materials-qualification",
                            "manifestSha256": "f" * 64 if mutation == "materials-foreign-manifest" else "d" * 64,
                            "performanceSha256": "e" * 64,
                            "feedPackages": 10 if mutation == "missing-feed-package" else 11,
                            "retainedBinaries": 2 if mutation == "missing-retained-binary" else 3,
                            "graphs": 17 if mutation == "missing-material-graph" else 18,
                            "journeys": 8 if mutation == "missing-material-journey" else 9,
                        },
                        "tooling": {
                            "qualification": False, "nativeContainment": mutation == "tooling-native-claim",
                            "role": "trusted-tooling-supervisor", "tests": 1,
                            "sourceManifestSha256": inputs["sourceManifestSha256"],
                            "sha256": evidence.digest(tooling),
                        },
                    },
                }
                (root / inherited.CONTROLLER_BASELINES).write_bytes(
                    raw + b"\n" if mutation == "changed-bytes" else raw)
                for path, value in (("proofs/composition-diagnostic-summary.json", summary),
                                    ("proofs/composition-inputs.json", inputs),
                                    ("proofs/inherited-controller-tooling.json", tooling),
                                    ("runtime-owner.json", {"runId": "run", "rootId": "root"})):
                    (root / path).write_bytes(evidence.canonical_bytes(value))
                if mutation.startswith("missing-summary"):
                    (root / "proofs/composition-diagnostic-summary.json").unlink()
                    if mutation == "missing-summary-missing-tooling":
                        (root / "proofs/inherited-controller-tooling.json").unlink()
                output = io.StringIO()
                with mock.patch.object(sys, "argv", ["workflow", str(root), "a" * 40]), mock.patch.object(
                        evidence, "admit_entity", side_effect=lambda kind, value: value), \
                        mock.patch.object(composition, "verify_composition_report_controls", return_value={
                            "qualification": False,
                            "reportMutations": 28 if mutation == "missing-report-control" else 29,
                            "semanticMutations": 1 if mutation == "missing-semantic-control" else 2}) as report_controls, \
                        contextlib.redirect_stdout(output):
                    if mutation == "none":
                        exec(code, {"__name__": "__main__"})
                        self.assertEqual({"qualification": False, "status": "Incomplete",
                                          "code": "EvidenceIncomplete"},
                                         evidence.load_json(output.getvalue().encode()))
                        report_controls.assert_called_once_with(
                            root, inputs, {"runId": "run", "rootId": "root"}, summary["caseReport"])
                    else:
                        with self.assertRaisesRegex(SystemExit, "WitnessMissing"):
                            exec(code, {"__name__": "__main__"})
                        if mutation.startswith("missing-summary"):
                            failure = evidence.load_json(output.getvalue().encode())
                            self.assertEqual("WitnessMissing", failure["code"])
                            self.assertFalse(failure["qualification"])
                            self.assertNotIn("private-tooling-canary", output.getvalue())
                            if mutation in ("missing-summary", "missing-summary-incomplete-tooling"):
                                self.assertEqual("OutputLimitExceeded", failure["summaryCode"])
                                observed = failure["tooling"]
                                self.assertFalse(observed["nativeContainment"])
                                self.assertEqual(1, observed["expectedTests"])
                                self.assertEqual(
                                    ("EvidenceIncomplete", 0, 600001) if mutation.endswith("incomplete-tooling")
                                    else ("None", 1, 1),
                                    tuple(observed[key] for key in ("code", "observedTests", "elapsedMs")))
                            else:
                                self.assertNotIn("tooling", failure)
                                self.assertIn("toolingCode", failure)
                self.assertFalse((root / "stores").exists())

    def test_unsupported_native_host_rejects_before_allocating_or_building(self):
        import conformance_composition_checks as checks
        import conformance_evidence as evidence
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "must-not-exist"
            with mock.patch.object(checks, "native_execution_supported", return_value=False), \
                    mock.patch.object(checks.OwnedRun, "allocate") as allocate, \
                    self.assertRaisesRegex(evidence.ConformanceError, "PrerequisiteMissing"):
                checks.execute(ROOT, destination)
            allocate.assert_not_called()
            self.assertFalse(destination.exists())

    def test_cli_reports_incomplete_without_qualifying_a_failed_native_run(self):
        import conformance_composition_checks as checks
        import conformance_evidence as evidence
        output = io.StringIO()
        with mock.patch.object(checks, "execute", side_effect=evidence.ConformanceError("CleanupIncomplete")), \
                contextlib.redirect_stdout(output):
            code = checks.main(["--root", str(ROOT), "--evidence", "/unallocated/test-only"])
        self.assertEqual(code, 2)
        report = evidence.load_json(output.getvalue().encode())
        self.assertEqual(report, {
            "qualification": False, "status": "Incomplete", "code": "CleanupIncomplete"})

    def test_selected_manifest_keeps_every_ownership_parameter(self):
        import conformance_composition_checks as checks
        rows = checks.expected_rows()
        self.assertEqual(len(rows), 36)
        self.assertEqual(len({row["testIdentity"] for row in rows}), 36)
        self.assertEqual(sum(row["caseId"] == "CP-11" for row in rows), 5)
        self.assertEqual({row["caseId"] for row in rows}, {f"CP-{index:02}" for index in range(1, 21)})
        self.assertEqual(sum(row["caseId"] == "CP-19" for row in rows), 2)
        self.assertEqual(sum(row["caseId"] == "CP-20" for row in rows), 2)
        self.assertEqual(sum(row["caseId"] == "CP-14" for row in rows), 3)
        self.assertEqual(sum(row["caseId"] == "CP-18" for row in rows), 1)
        self.assertEqual(sum(row["caseId"] == "CP-16" for row in rows), 2)
        self.assertEqual(sum(row["caseId"] == "CP-17" for row in rows), 3)
        self.assertTrue(all(row["bindingId"] == "none" for row in rows))


def native_composition_origin_tests(evaluation, *, released):
    from dataclasses import replace
    import conformance_evidence as evidence
    from conformance_sources import NativeCompositionEvaluation

    if type(evaluation) is not NativeCompositionEvaluation:
        raise evidence.ConformanceError("OwnershipInvalid")
    owner = evaluation._source._run
    original = evidence.load_json(evaluation.report_data)

    def inspect(report, token=evaluation, run=owner):
        return evidence.inspect_native_composition_report(
            run, evidence.canonical_bytes(report), expected_inputs=original["inputs"], native_evaluation=token)

    if not released:
        class LiveNativeCompositionOriginTests(unittest.TestCase):
            __qualname__ = "LiveNativeCompositionOriginTests"

            def test_unsettled_original_owner_cannot_publish_released_authority(self):
                self.assertEqual(owner.state, "Active")
                with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                    inspect(original)

            def test_capture_is_single_use_even_with_the_original_inputs(self):
                with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                    evaluation._source.capture_evaluation(original["inputs"], {}, {}, evaluation.command_sequence)

            def test_rehashed_execution_cannot_replace_the_actual_executor_record(self):
                path = owner.root / f"proofs/execution-command-{evaluation.command_sequence:04}.json"
                raw = owner.read_execution_record(evaluation.command_sequence)
                try:
                    path.chmod(0o600)
                    path.write_bytes(raw + b"\n")
                    path.chmod(0o400)
                    with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                        owner.read_execution_record(evaluation.command_sequence)
                finally:
                    path.chmod(0o600)
                    path.write_bytes(raw)
                    path.chmod(0o400)
                self.assertEqual(owner.read_execution_record(evaluation.command_sequence), raw)

        return unittest.TestLoader().loadTestsFromTestCase(LiveNativeCompositionOriginTests)

    report = evidence.load_json(evaluation.report_data)
    report["resources"] = owner.resource_projection()

    class ReleasedNativeCompositionOriginTests(unittest.TestCase):
        __qualname__ = "ReleasedNativeCompositionOriginTests"

        def setUp(self):
            self.assertTrue(inspect(report)["runtimeOriginVerified"])

        def test_original_runtime_is_independently_replayed_after_actual_release(self):
            inspected = inspect(report)
            self.assertEqual(owner.state, "Released")
            self.assertFalse(inspected["qualification"])
            self.assertEqual(inspected["reportState"], "Incomplete")
            self.assertGreater(inspected["passedCases"], 0)
            self.assertEqual(inspected["incompleteCases"], 0)

        def test_equal_token_copy_cannot_replace_the_original_held_identity(self):
            with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                inspect(report, token=replace(evaluation))

        def test_modeled_owner_cannot_borrow_the_original_token(self):
            with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                inspect(report, run=SimpleNamespace(state="Released", root=owner.root))

        def test_captured_active_and_missing_resources_cannot_claim_actual_settlement(self):
            for resources in (original["resources"], []):
                with self.subTest(resources=bool(resources)):
                    changed = evidence.load_json(evidence.canonical_bytes(report))
                    changed["resources"] = resources
                    with self.assertRaisesRegex(evidence.ConformanceError, "^CleanupIncomplete$"):
                        inspect(changed)

        def test_changed_observations_cannot_borrow_the_original_runtime_authority(self):
            for collection in ("results", "witnesses"):
                changed = evidence.load_json(evidence.canonical_bytes(report))
                changed[collection].pop()
                with self.subTest(collection=collection), self.assertRaises(evidence.ConformanceError):
                    inspect(changed)

        def test_correctly_hashed_extra_proof_was_not_observed_by_the_original_runtime(self):
            changed = evidence.load_json(evidence.canonical_bytes(report))
            path = "proofs/composition-runtime-report.json"
            changed["proofs"][path] = evidence.file_sha256(owner.root / path)
            with self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
                inspect(changed)

        def test_resealed_execution_bytes_cannot_replace_the_held_command_hash(self):
            path = owner.root / f"proofs/execution-command-{evaluation.command_sequence:04}.json"
            raw = path.read_bytes()
            try:
                path.chmod(0o600)
                path.write_bytes(raw + b"\n")
                path.chmod(0o400)
                with self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
                    inspect(report)
            finally:
                path.chmod(0o600)
                path.write_bytes(raw)
                path.chmod(0o400)
            self.assertTrue(inspect(report)["runtimeOriginVerified"])

        def test_changed_quality_derivation_bytes_cannot_borrow_the_original_report(self):
            path = owner.root / "proofs/composition-QC-18-attempt-1.json"
            raw = path.read_bytes()
            try:
                path.chmod(0o600)
                path.write_bytes(raw + b"\n")
                path.chmod(0o400)
                with self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
                    inspect(report)
            finally:
                path.chmod(0o600)
                path.write_bytes(raw)
                path.chmod(0o400)
            self.assertTrue(inspect(report)["runtimeOriginVerified"])

        def test_changed_selected_sdk_closure_cannot_borrow_the_original_execution(self):
            path = owner.root / "proofs/sdk-vstest-inputs.json"
            raw = path.read_bytes()
            try:
                path.chmod(0o600)
                path.write_bytes(raw + b"\n")
                path.chmod(0o400)
                with self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
                    inspect(report)
            finally:
                path.chmod(0o600)
                path.write_bytes(raw)
                path.chmod(0o400)
            self.assertTrue(inspect(report)["runtimeOriginVerified"])

    return unittest.TestLoader().loadTestsFromTestCase(ReleasedNativeCompositionOriginTests)


def run_native_composition_controls(arguments):
    import conformance_composition_checks as composition
    import conformance_evidence as evidence
    from test_conformance_evidence import _run_native_control_suite

    if len(arguments) != 2 or arguments[0] != "--evidence":
        raise evidence.ConformanceError("UnsupportedProfile")
    if not composition.native_execution_supported():
        raise evidence.ConformanceError("PrerequisiteMissing")
    captured = []
    counts = {"liveOriginTests": 0, "settlementOriginTests": 0}
    original_runtime = composition._runtime

    class RuntimeControlBoundary(Exception):
        pass

    def runtime(*args, **kwargs):
        if captured:
            raise evidence.ConformanceError("ProofMismatch")
        original_runtime(*args, **kwargs)
        evaluation = kwargs["native_sources"]._evaluation
        counts["liveOriginTests"] = _run_native_control_suite(
            lambda: native_composition_origin_tests(evaluation, released=False))
        captured.append(evaluation)
        raise RuntimeControlBoundary

    with mock.patch.object(composition, "_runtime", runtime):
        try:
            composition.execute(ROOT, Path(arguments[1]).resolve())
        except RuntimeControlBoundary:
            pass
        else:
            raise evidence.ConformanceError("WitnessMissing")
    if len(captured) != 1 or not counts["liveOriginTests"]:
        raise evidence.ConformanceError("WitnessMissing")
    evaluation, = captured
    owner = evaluation._source._run
    released = composition._released_composition_report(owner, evaluation)
    paths = [path.relative_to(owner.root).as_posix()
             for path in owner.root.rglob("*") if path.is_file()]
    before = evidence.input_manifest(owner.root, paths)
    counts["settlementOriginTests"] = _run_native_control_suite(
        lambda: native_composition_origin_tests(evaluation, released=True))
    if before != evidence.input_manifest(owner.root, paths):
        raise evidence.ConformanceError("InputChanged")
    print(evidence.canonical_bytes({
        "qualification": False, "scope": "native-composition-origin-control-diagnostic",
        "profileComplete": False, "inheritedRuntimeExecuted": False, **counts,
        "runtimeOriginVerified": released["runtimeOriginVerified"]}).decode("ascii"))
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["--native-origin-controls"]:
        import conformance_evidence as evidence
        try:
            raise SystemExit(run_native_composition_controls(sys.argv[2:]))
        except (evidence.ConformanceError, OSError) as error:
            code = str(error) if isinstance(error, evidence.ConformanceError) else "EvidenceIncomplete"
            print(evidence.canonical_bytes({
                "qualification": False, "scope": "native-composition-origin-control-diagnostic",
                "code": code}).decode("ascii"))
            raise SystemExit(1) from None
    unittest.main()
