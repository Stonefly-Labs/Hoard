"""Inherited composition inventory and safe exact-discovery controls."""

import importlib.util
import copy
from contextlib import nullcontext, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "freeze_composition_inventory",
    ROOT / "tests/fixtures/conformance/baselines/freeze_composition_inventory.py")
FREEZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FREEZE)
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_inherited as inherited
from conformance_evidence import ConformanceError, canonical_bytes, file_sha256


class FrozenCompositionInventoryTests(unittest.TestCase):
    def test_controller_runtime_inputs_bind_original_logger_descriptors_images_and_archives(self):
        from conformance_sources import runtime_arguments, runtime_settings

        for defect in (None, "manifest", "owner", "inputs", "image", "package", "foreign-root", "escaping-root",
                       "foreign-image", "unknown-setting"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                runtime = root / "stores/runtime"
                assembly = runtime / "assemblies/Fixture.dll"
                assembly.parent.mkdir(parents=True)
                assembly.write_bytes(b"fixture image")
                package = runtime / "resources/sdk.nupkg"
                package.parent.mkdir()
                package.write_bytes(b"fixture package")
                attempt = str(uuid.uuid4())
                owner = runtime / "runtime-owner.json"
                owner.write_bytes(canonical_bytes({"schemaVersion": 1, "rootId": "fixture"}))
                inputs = runtime / "legacy-inputs.json"
                inputs.write_bytes(canonical_bytes({"schemaVersion": 1, "configuration": {}}))
                manifest = runtime / f"runtime-input-{attempt}.json"
                images = [{"id": "test-assembly", "path": assembly.relative_to(runtime).as_posix(),
                           "sha256": file_sha256(assembly)}]
                if defect == "foreign-image":
                    images[0]["path"] = "../outside.dll"
                manifest.write_bytes(canonical_bytes({
                    "schemaVersion": 1, "attemptId": attempt, "inputSha256": file_sha256(inputs),
                    "runInputsPath": inputs.relative_to(runtime).as_posix(), "assemblies": images,
                    "packages": [{"id": "shared-sdk", "path": package.relative_to(runtime).as_posix(),
                                  "sha256": file_sha256(package)}]}))
                settings = runtime / "resources/settings.runsettings"
                logger_root = (root.parent if defect == "foreign-root" else
                               runtime / "../../.." if defect == "escaping-root" else runtime)
                settings.write_bytes(runtime_settings(
                    logger_root, assembly, attempt,
                    file_sha256(manifest), file_sha256(owner), ""))
                if defect == "unknown-setting":
                    settings.write_bytes(settings.read_bytes().replace(
                        b"</OwnerSha256>", b"</OwnerSha256><Unexpected>value</Unexpected>"))
                elif defect in ("manifest", "owner", "inputs", "image", "package"):
                    {"manifest": manifest, "owner": owner, "inputs": inputs,
                     "image": assembly, "package": package}[defect].write_bytes(b"changed")
                arguments = runtime_arguments(assembly, settings, ["Fixture.Case"])
                if defect in ("foreign-root", "escaping-root"):
                    with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                        inherited.controller_command_read_inputs(root, arguments, env={})
                elif defect is not None:
                    with self.assertRaises(ConformanceError):
                        inherited.controller_command_read_inputs(root, arguments, env={})
                else:
                    files = inherited.controller_command_read_inputs(root, arguments, env={})
                    for path in (manifest, owner, inputs, assembly, package, settings):
                        self.assertEqual(file_sha256(path), files[path.relative_to(root).as_posix()])

    def test_controller_command_read_inputs_bind_selected_sources_imports_runtime_and_configuration(self):
        for operation in ("build", "implicit-build", "restore", "runtime", "relative", "environment",
                          "project-links", "package", "foreign", "foreign-link", "sdk-argument", "foreign-vstest"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                project = root / "stores/project/Fixture.csproj"
                project.parent.mkdir(parents=True)
                project.write_bytes(b"<Project />")
                code = project.parent / "Program.cs"
                code.write_bytes(b"fixture source")
                properties = root / "stores/Directory.Build.props"
                properties.write_bytes(b"<Project />")
                assets = project.parent / "obj/project.assets.json"
                assets.parent.mkdir()
                assets.write_bytes(b'{"libraries":{}}')
                assembly = project.parent / "bin/Release/net10.0/Fixture.dll"
                assembly.parent.mkdir(parents=True)
                assembly.write_bytes(b"fixture image")
                sidecar = assembly.with_suffix(".deps.json")
                sidecar.write_bytes(b"{}")
                original = root / "stores/original.json"
                original.write_bytes(b"unchanged original")
                linked = root / "stores/Linked.cs"
                imported = root / "stores/Imported.props"
                dependency = root / "stores/dependency/Dependency.csproj"
                dependency_code = dependency.parent / "Dependency.cs"
                package_image = root / "cache/hoard.fixture/0.1.0/lib/net10.0/Hoard.Fixture.dll"
                if operation == "project-links":
                    linked.write_bytes(b"linked source")
                    imported.write_bytes(b"<Project />")
                    dependency.parent.mkdir()
                    dependency.write_bytes(
                        b'<Project><ItemGroup><ProjectReference Include="../project/Fixture.csproj" />'
                        b'</ItemGroup></Project>')
                    dependency_code.write_bytes(b"dependency source")
                    project.write_bytes(
                        b'<Project><Import Project="../Imported.props" /><ItemGroup>'
                        b'<Compile Include="../Linked.cs" />'
                        b'<ProjectReference Include="../dependency/Dependency.csproj" /></ItemGroup></Project>')
                elif operation == "package":
                    package_image.parent.mkdir(parents=True)
                    package_image.write_bytes(b"actual cached assembly")
                    assets.write_bytes(canonical_bytes({
                        "libraries": {"Hoard.Fixture/0.1.0": {"type": "package", "path": "hoard.fixture/0.1.0"}},
                        "packageFolders": {str(root / "cache"): {}}}))
                arguments = (["dotnet", str(assembly), str(original)] if operation in ("runtime", "sdk-argument")
                             else ["dotnet", operation, str(project)])
                if operation == "sdk-argument":
                    arguments.append("/opt/dotnet/sdk/10.0.203/vstest.console.dll")
                if operation == "build":
                    arguments.append("--no-restore")
                elif operation == "implicit-build":
                    arguments[1] = "build"
                elif operation == "relative":
                    arguments = ["dotnet", "build", project.name, "--no-restore"]
                elif operation == "environment":
                    arguments = ["dotnet", "build", str(project), "--no-restore"]
                elif operation in ("project-links", "package", "foreign-link"):
                    arguments = ["dotnet", "build", str(project), "--no-restore"]
                if operation == "foreign-link":
                    project.write_bytes(b'<Project><ItemGroup><Compile Include="../../../Outside.cs" />'
                                        b'</ItemGroup></Project>')
                    with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                        inherited.controller_command_read_inputs(root, arguments, env={})
                    continue
                if operation in ("foreign", "foreign-vstest"):
                    arguments = ["dotnet", *(["vstest"] if operation == "foreign-vstest" else []),
                                 str(root.parent / "Foreign.dll")]
                    with self.assertRaises(ConformanceError):
                        inherited.controller_command_read_inputs(root, arguments)
                    continue
                environment = {"HOARD_DISCOVERY_EVIDENCE": str(original)} if operation == "environment" else {}
                observed = inherited.controller_command_read_inputs(
                    root, arguments, cwd=project.parent, env=environment)
                if operation == "environment":
                    self.assertIn(original.relative_to(root).as_posix(), observed)
                elif operation == "project-links":
                    self.assertTrue({path.relative_to(root).as_posix()
                                     for path in (linked, imported, dependency, dependency_code)} <= set(observed))
                elif operation == "package":
                    self.assertEqual(file_sha256(package_image),
                                     observed[package_image.relative_to(root).as_posix()])
                self.assertEqual(observed, {
                    path: file_sha256(root / path) for path in observed})
                if operation in ("runtime", "sdk-argument"):
                    self.assertTrue({path.relative_to(root).as_posix() for path in (assembly, sidecar, original)}
                                    <= set(observed))
                else:
                    self.assertTrue({path.relative_to(root).as_posix() for path in (project, code, properties)}
                                    <= set(observed))
                    self.assertEqual(operation not in ("restore", "implicit-build"),
                                     assets.relative_to(root).as_posix() in observed)

    def test_native_reference_replay_requires_unchanged_complete_inputs_and_actual_original_consumer(self):
        import hashlib
        import conformance_legacy as legacy
        from conformance_evidence import digest

        for defect in (None, "changed", "omitted", "foreign", "output", "during", "source-omitted",
                       "dependency", "unknown-field", "missing-native", "foreign-group", "native-input"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                source = root / "stores/reference"
                source.mkdir(parents=True)
                files = {
                    "project": source / "ReferenceConsumer.csproj",
                    "assembly": source / "ReferenceConsumer.dll",
                    "assets": source / "obj/project.assets.json",
                    "runtimeConfig": source / "ReferenceConsumer.runtimeconfig.json",
                    "dependencies": source / "ReferenceConsumer.deps.json",
                    "response": source / "observation.json",
                    "code": source / "Program.cs",
                }
                for path in files.values():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"<Project />" if path.suffix == ".csproj" else b"{}")
                if defect == "dependency":
                    files["project"].write_bytes(b'<Project><PackageReference Include="Unexpected" /></Project>')
                reference = {key: str(path) for key, path in files.items() if key not in ("project", "code")}
                reference.update(source=str(source), assemblySha256=file_sha256(files["assembly"]),
                                 responseSha256=file_sha256(files["response"]), moduleIds=["fixture.protocol.one"])
                if defect == "unknown-field":
                    reference["private"] = "synthetic-canary"
                manifest = root / "stores/discovery-evidence.json"
                manifest.write_bytes(canonical_bytes({"referenceConsumer": reference}))
                inputs = {path.relative_to(root).as_posix(): file_sha256(path)
                          for path in (*files.values(), manifest)}
                if defect == "omitted":
                    inputs.pop(files["response"].relative_to(root).as_posix())
                if defect == "source-omitted":
                    inputs.pop(files["code"].relative_to(root).as_posix())
                if defect == "foreign":
                    reference["assembly"] = str(root.parent / "ReferenceConsumer.dll")
                    manifest.write_bytes(canonical_bytes({"referenceConsumer": reference}))
                    inputs[manifest.relative_to(root).as_posix()] = file_sha256(manifest)
                packet = root / "proofs/reference-inputs.json"
                packet.write_bytes(canonical_bytes(inputs))
                descriptor = {
                    "manifestPath": manifest.relative_to(root).as_posix(), "manifestSha256": file_sha256(manifest),
                    "inputMapPath": packet.relative_to(root).as_posix(), "inputMapSha256": file_sha256(packet)}
                if defect == "changed":
                    files["response"].write_bytes(b"changed")
                native = {
                    "schemaVersion": 1, "qualification": False, "groupState": "Borrowed",
                    "groupPid": os.getpid(), "groupStartSha256": "a" * 64,
                    "childPid": os.getpid() + 1, "childStartSha256": "b" * 64,
                    "childState": "Exited", "exitCode": 0,
                    "argvSha256": digest(["dotnet", str(files["assembly"])]),
                    "cwdSha256": hashlib.sha256(os.getcwd().encode()).hexdigest(),
                    "stdinSha256": reference["responseSha256"],
                }
                if defect == "foreign-group":
                    native["groupPid"] += 1
                elif defect == "native-input":
                    native["stdinSha256"] = "0" * 64
                result = SimpleNamespace(returncode=0, stdout=json.dumps(
                    [{"Id": "fixture.protocol.two" if defect == "output" else "fixture.protocol.one"}]),
                    **({} if defect == "missing-native" else {"native_invocation": native}))
                def command(*args, **kwargs):
                    if defect == "during":
                        files["response"].write_bytes(b"changed while executing")
                    return result
                with patch.object(legacy, "composition_controller_command", side_effect=command) as invoke:
                    if defect:
                        with self.assertRaises(ConformanceError):
                            inherited.replay_reference_consumer(root, descriptor)
                    else:
                        observed = inherited.replay_reference_consumer(root, descriptor)
                        self.assertEqual(observed["moduleCount"], 1)
                        self.assertEqual(observed["moduleIdsSha256"], digest(reference["moduleIds"]))
                        self.assertEqual(observed["invocation"], native)
                        invoke.assert_called_once_with(
                            ["dotnet", str(files["assembly"])], input=b"{}")
                    if defect in ("changed", "omitted", "foreign", "source-omitted", "dependency", "unknown-field"):
                        invoke.assert_not_called()

    def test_compatibility_fixture_source_baseline_is_derived_from_immutable_git_bytes(self):
        import hashlib

        data = json.loads((ROOT / "tests/fixtures/conformance/Compatibility/source-baseline.json").read_bytes())
        paths = ["tests/fixtures/compatibility/BinaryMemberRemoval/" + name for name in (
            "Consumer/Program.cs", "Old/Contract.cs", "New/Contract.cs")]
        expected = {path: hashlib.sha256(subprocess.check_output(
            ["git", "show", inherited.BASELINE + ":" + path], cwd=ROOT)).hexdigest() for path in paths}
        self.assertEqual({
            "schemaVersion": 1, "baselineRevision": inherited.BASELINE,
            "scope": "controlled-binary-member-removal-fixture-sources", "sources": expected}, data)

    def test_mutation_scopes_require_exact_positive_parameters_and_actual_negative_and_repair_results(self):
        import xml.etree.ElementTree as ET
        import conformance_legacy as legacy
        import discovery_evidence as discovery
        from conformance_case_catalog import INHERITED_GUARD_FAILURES

        for mutation in ("none", "foreign-parameter", "omitted-repair", "false-negative",
                         "false-count", "changed-projection", "foreign-path", "omitted-mutation",
                         "malformed-row", "boolean-count"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                scenarios, rows = set(), []
                for identity, _, _, _, method in discovery.MUTATIONS:
                    name = "Hoard.Composition.Tests.DiscoveryTests." + method
                    scenario = name + '(testCaseSha256: "' + "a" * 64 + '")'
                    scenarios.add(scenario)
                    row = {"id": identity, "passed": True, "failedTests": [scenario]}
                    for phase, directory, outcome in (
                            ("negative", "mutation-results", "Failed"), ("repair", "repair-results", "Passed")):
                        path = root / "stores/inherited-discovery-mutations" / directory / identity / (
                            "red.trx" if phase == "negative" else "repair.trx")
                        path.parent.mkdir(parents=True)
                        element = ET.Element("TestRun")
                        ET.SubElement(element, "UnitTestResult", testName=scenario, outcome=outcome)
                        path.write_bytes(ET.tostring(element))
                        guard = "inherited-discovery-guard-" + identity in INHERITED_GUARD_FAILURES
                        row[phase] = {
                            "projection": str(path), "projectionSha256": file_sha256(path), "parameters": 1,
                            "failedParameters": int(phase == "negative"),
                            "failureKind": "None" if phase == "repair" else "Guard" if guard else "Assertion",
                        }
                    rows.append(row)
                if mutation in ("foreign-parameter", "omitted-repair", "false-negative"):
                    phase = "repair" if mutation == "omitted-repair" else "negative"
                    entry = rows[0][phase]
                    tree = ET.Element("TestRun")
                    if mutation != "omitted-repair":
                        ET.SubElement(tree, "UnitTestResult",
                            testName=rows[0]["failedTests"][0].replace("a" * 64, "b" * 64)
                            if mutation == "foreign-parameter" else rows[0]["failedTests"][0],
                            outcome="Passed" if mutation == "false-negative" else "Failed")
                    Path(entry["projection"]).write_bytes(ET.tostring(tree))
                    entry["projectionSha256"] = file_sha256(Path(entry["projection"]))
                elif mutation == "false-count":
                    rows[0]["negative"]["parameters"] = 2
                elif mutation == "changed-projection":
                    rows[0]["negative"]["projectionSha256"] = "0" * 64
                elif mutation == "foreign-path":
                    rows[0]["negative"]["projection"] = str(root / "foreign.trx")
                elif mutation == "omitted-mutation":
                    rows.pop()
                elif mutation == "malformed-row":
                    del rows[0]["id"]
                elif mutation == "boolean-count":
                    rows[0]["negative"]["parameters"] = True
                with patch.object(legacy, "verify_projection") as verify:
                    if mutation == "none":
                        inherited.verify_discovery_mutation_membership(
                            root, {"qualification": False, "mutations": rows}, scenarios)
                        self.assertEqual(24, verify.call_count)
                    else:
                        with self.assertRaises(ConformanceError):
                            inherited.verify_discovery_mutation_membership(
                                root, {"qualification": False, "mutations": rows}, scenarios)

    def test_controller_tooling_binds_full_source_and_actual_complete_supervisor_execution(self):
        import time
        import conformance_evidence as evidence
        import conformance_unit_checks as checks

        identity = "test_control.Case.test_assertion"
        sources = {"tests/tooling/test_control.py": "a" * 64}
        for mutation in ("none", "changed-source", "missing-observation", "foreign-module", "skipped",
                         "borrowed-provider-group", "live-child"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                run = SimpleNamespace(root=root, state="Active", run_id="run", root_id="root",
                                      deadline=time.monotonic() + 600,
                                      live_children=lambda: {123} if mutation == "live-child" else set())
                packet = {
                    "mode": "diagnostic", "scope": "tooling", "qualification": False, "code": "None",
                    "tests": 1, "failures": 0, "errors": 0, "skipped": 0, "failedTests": [],
                    "expectedFailures": 0, "unexpectedSuccesses": 0, "unexpectedDiagnosticBytes": 0,
                    "freeScratchBytes": 123,
                    "expectedTests": [identity], "observedTests": [identity],
                }
                if mutation == "missing-observation":
                    packet.update(tests=0, observedTests=[])
                elif mutation == "foreign-module":
                    packet.update(expectedTests=["foreign.Case.test_assertion"],
                                  observedTests=["foreign.Case.test_assertion"])
                elif mutation == "skipped":
                    packet.update(skipped=1, code="EvidenceIncomplete")
                with patch.object(evidence, "source_manifest", side_effect=[
                        sources, {} if mutation == "changed-source" else sources]), \
                        patch.object(checks, "run_checks", return_value=packet) as execute, \
                        patch("conformance_legacy._borrowed_group",
                              return_value=123 if mutation == "borrowed-provider-group" else None):
                    if mutation == "none":
                        result = inherited.run_controller_tooling(ROOT, run, sources)
                        self.assertFalse(result["qualification"])
                        self.assertFalse(result["nativeContainment"])
                        self.assertEqual(1, result["tests"])
                        self.assertEqual(file_sha256(root / "proofs/inherited-controller-tooling.json"), result["sha256"])
                        self.assertTrue(execute.call_args.kwargs["all_tooling"])
                        self.assertLessEqual(execute.call_args.kwargs["deadline"], run.deadline)
                    else:
                        with self.assertRaises(ConformanceError):
                            inherited.run_controller_tooling(ROOT, run, sources)
                        if mutation in ("borrowed-provider-group", "live-child"):
                            execute.assert_not_called()

    def test_selected_mutation_discovery_requires_actual_complete_unchanged_images(self):
        import conformance_legacy as legacy
        method = "Hoard.Composition.Tests.DiscoveryBoundsTests.Check"
        entry = {"fullyQualifiedName": method, "parameterCount": 2, "group": "discovery"}
        for mutation in ("none", "missing-parameter", "changed-image", "failed", "unknown-output"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                assembly = root / "resources/assembly/Hoard.Composition.Tests.dll"
                assembly.parent.mkdir(parents=True)
                assembly.write_bytes(b"synthetic-image")
                driver_source = root / "prepared-driver"
                driver_source.mkdir()
                (driver_source / "Hoard.Fixtures.Conformance.Discovery.dll").write_bytes(b"synthetic-driver")
                sdk = root / "sdk"
                (sdk / "10.0.203").mkdir(parents=True)
                (sdk / "10.0.203/vstest.console.dll").write_bytes(b"vstest")

                def execute(arguments, **kwargs):
                    request = json.loads((root / "discovery-request.json").read_bytes())
                    self.assertEqual([method], request["methods"])
                    count = 1 if mutation == "missing-parameter" else 2
                    (root / "discovered.json").write_bytes(canonical_bytes([
                        {"testIdentity": method + '(testCaseSha256: "' + str(index) * 64 + '")',
                         "fullyQualifiedName": method} for index in range(count)]))
                    if mutation == "changed-image":
                        assembly.write_bytes(b"changed")
                    return subprocess.CompletedProcess(arguments, int(mutation == "failed"),
                        b"private-canary" if mutation == "unknown-output" else canonical_bytes(
                            {"event": "control", "code": "None", "value": count}))

                with patch("conformance_execution.capture_control", return_value=(
                        0, f"10.0.203 [{sdk}]\n".encode())), patch.object(legacy, "capture", side_effect=execute):
                    if mutation == "none":
                        rows = inherited.discover_inherited_method(
                            assembly, entry, driver_source, "10.0.203", {})
                        self.assertEqual(2, len(rows))
                    else:
                        with self.assertRaises(ConformanceError):
                            inherited.discover_inherited_method(assembly, entry, driver_source, "10.0.203", {})

    def test_isolated_controller_entry_rejects_bad_request_without_import_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary).resolve()
            request = owner / "request.json"
            request.write_bytes(b"private-canary")
            output = owner / "must-not-exist.json"
            result = subprocess.run(
                [sys.executable, "-I", "-S", str(ROOT / "scripts/conformance_inherited.py"),
                 "--request", str(request), "--output", str(output)],
                capture_output=True, timeout=15, check=False)
            self.assertEqual(2, result.returncode)
            self.assertEqual(b"", result.stderr)
            self.assertEqual({"event": "control", "code": "EvidenceSchemaInvalid", "value": 0},
                             json.loads(result.stdout))
            self.assertFalse(output.exists())

    def test_controller_child_projects_progress_and_unknown_failures_before_persistence(self):
        run_id = "11111111-1111-4111-8111-111111111111"
        for failure in (False, True):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                owner = Path(temporary).resolve()
                (owner / "proofs").mkdir()
                (owner / "source").mkdir()
                (owner / "ownership.json").write_bytes(canonical_bytes({
                    "schemaVersion": 2, "runId": run_id, "rootId": "root", "state": "Active"}))
                (owner / "proofs/preflight.json").write_bytes(canonical_bytes({
                    "schemaVersion": 1, "qualification": False, "profileId": "composition"}))
                request = owner / "proofs/request.json"
                request.write_bytes(canonical_bytes({
                    "schemaVersion": 1, "phase": "historical", "owner": str(owner), "repository": str(ROOT),
                    "runId": run_id, "rootId": "root", "source": "source", "baselineSeal": None,
                    "sdkPackage": None, "loggerPath": None,
                }))
                result = owner / "proofs/result.json"

                def prepare(repository, run):
                    self.assertEqual((ROOT, owner, run_id, "root", 0),
                                     (repository, run.root, run.run_id, run.root_id, run.command_sequence))
                    print(json.dumps({"qualification": False, "phase": "inherited-historical-preparation",
                                      "controller": "lifecycle"}))
                    if failure:
                        raise RuntimeError("private-canary")
                    return {"path": inherited.CONTROLLER_BASELINES, "sha256": "a" * 64}

                output = io.StringIO()
                with redirect_stdout(output), patch("conformance_legacy.native_preparation_group",
                                                     return_value=nullcontext({
                                                         "invocations": [], "inputSnapshots": []})), patch.object(
                        inherited, "prepare_controller_baselines", side_effect=prepare):
                    code = inherited.controller_child_main(["--request", str(request), "--output", str(result)])
                self.assertEqual(2 if failure else 0, code)
                self.assertNotIn("private-canary", output.getvalue())
                lines = [json.loads(line) for line in output.getvalue().splitlines()]
                self.assertEqual({"event": "control", "code": "None", "value": 2}, lines[0])
                self.assertEqual({"event": "control", "code": "EvidenceIncomplete" if failure else "None",
                                  "value": 0}, lines[-1])
                if failure:
                    self.assertTrue(any(event["code"] == "EvidenceIncomplete"
                                        and 100000 < event["value"] < 200000 for event in lines))
                self.assertTrue(result.exists())
                self.assertNotIn("private-canary", result.read_text())
                if failure:
                    self.assertEqual({"schemaVersion": 1, "qualification": False, "phase": "historical",
                                      "runId": run_id, "rootId": "root", "status": "Incomplete",
                                      "diagnosticCode": "EvidenceIncomplete"}, json.loads(result.read_bytes()))

    def test_controller_child_progress_rejects_raw_text_without_echo(self):
        output = io.StringIO()
        progress = inherited.ControllerProgress(output)
        with self.assertRaisesRegex(ConformanceError, "UnknownDiagnostic"):
            progress.write("private-canary\n")
        self.assertEqual("", output.getvalue())
        with self.assertRaisesRegex(ConformanceError, "OutputLimitExceeded"):
            progress.write("x" * 4097)

    def test_controller_progress_preserves_closed_conformance_errors_without_masking_their_codes(self):
        output = io.StringIO()
        progress = inherited.ControllerProgress(output)
        progress.write(json.dumps({
            "qualification": False, "phase": "inherited-controller-failure", "controller": "lifecycle",
            "commandSequence": 3, "operation": "test", "code": "InputChanged",
        }) + "\n")
        self.assertEqual({"event": "control", "code": "InputChanged", "value": 3},
                         json.loads(output.getvalue()))
    def test_controller_baselines_are_prepared_before_candidate_and_replayed_without_rebuild(self):
        import configuration_evidence as configuration
        import discovery_evidence as discovery
        import foundation_evidence as foundation
        import lifecycle_evidence as lifecycle
        import conformance_baselines as baselines
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary).resolve()
            for name in ("stores", "proofs", "feed"):
                (owner / name).mkdir()
            recipe = owner / "stores/f06-recipes"
            recipe.mkdir()
            (recipe / "recipe.cs").write_bytes(b"frozen recipe")
            run = SimpleNamespace(root=owner, run_id="run", root_id="root", command_sequence=0)

            def retained(root, work, update):
                result = []
                names = (("RetainedLifecycle", "RetainedConfiguration", "LegacyOptions")
                         if work.name == "discovery" else ("LegacyOptions", "LifecycleConsumer"))
                for name in names:
                    project = work / "retained" / name
                    binary = project / "bin/Release/net10.0" / (name + ".dll")
                    binary.parent.mkdir(parents=True)
                    binary.write_bytes(name.encode())
                    (binary.parent / "Hoard.Core.dll").write_bytes(b"old dependency")
                    assets = project / "obj/project.assets.json"
                    assets.parent.mkdir()
                    assets.write_bytes(b"{}")
                    (project / (name + ".csproj")).write_bytes(b"<Project/>")
                    result.append({"name": name, "baseline": (discovery if work.name == "discovery"
                                                              else configuration).BASELINE,
                                   "assembly": str(binary),
                                   "sha256": file_sha256(binary), "assets": str(assets)})
                return result

            def registration(root, work, config, update):
                binary = work / "registration-old/bin/Release/net10.0/RegistrationConsumer.dll"
                binary.parent.mkdir(parents=True)
                binary.write_bytes(b"old registration")
                return {"assembly": str(binary), "sha256": file_sha256(binary)}

            with patch.object(baselines, "export_revision", return_value=recipe), patch.object(
                    lifecycle, "prepare_registration_baseline", side_effect=registration) as old_registration, \
                    patch.object(configuration, "prepare_baseline", side_effect=retained) as old_configuration, \
                    patch.object(discovery, "prepare_baseline", side_effect=retained) as old_discovery, \
                    redirect_stdout(io.StringIO()) as progress:
                seal = inherited.prepare_controller_baselines(ROOT, run)
                self.assertEqual((1, 1, 1), (old_registration.call_count, old_configuration.call_count,
                                            old_discovery.call_count))
            self.assertEqual([
                {"qualification": False, "phase": "inherited-historical-preparation", "controller": name}
                for name in ("lifecycle", "configuration", "discovery")
            ], [json.loads(line) for line in progress.getvalue().splitlines()])
            verified = inherited.verify_controller_baselines(run, seal)
            self.assertFalse(verified["qualification"])
            self.assertFalse(verified["nativeContainment"])
            original = Path(verified["retained"]["configuration"][0]["assembly"])
            target = owner / "stores/replay"
            target.mkdir()
            with inherited.controller_transport(ROOT, owner), patch.object(
                    configuration, "prepare_baseline") as rebuild:
                replay = inherited.replay_controller_baseline(owner, verified, "configuration", target)
            rebuild.assert_not_called()
            copied = Path(replay[0]["assembly"])
            self.assertEqual(original.read_bytes(), copied.read_bytes())
            self.assertTrue(Path(replay[0]["assets"]).is_file())
            self.assertTrue((copied.parents[3] / "LegacyOptions.csproj").is_file())
            (copied.parent / "Hoard.Core.dll").write_bytes(b"candidate dependency")
            self.assertEqual(b"old dependency", (original.parent / "Hoard.Core.dll").read_bytes())
            inherited.verify_controller_baselines(run, seal)
            run.root_id = "foreign-root"
            with self.assertRaises(ConformanceError):
                inherited.verify_controller_baselines(run, seal)
            run.root_id = "root"
            original.chmod(0o600)
            original.write_bytes(b"changed")
            with self.assertRaisesRegex(ConformanceError, "InputChanged"):
                inherited.verify_controller_baselines(run, seal)
            with self.assertRaisesRegex(ConformanceError, "InputChanged"):
                inherited.prepare_controller_baselines(ROOT, run)

    def test_controller_baselines_reject_late_preparation_foreign_seals_and_changed_identity(self):
        import conformance_baselines as baselines
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary).resolve()
            (owner / "feed").mkdir()
            run = SimpleNamespace(root=owner, run_id="run", root_id="root", command_sequence=1)
            with patch.object(baselines, "export_revision") as export:
                with self.assertRaisesRegex(ConformanceError, "InputChanged"):
                    inherited.prepare_controller_baselines(ROOT, run)
                run.command_sequence = 0
                (owner / "feed/candidate").mkdir()
                with self.assertRaisesRegex(ConformanceError, "InputChanged"):
                    inherited.prepare_controller_baselines(ROOT, run)
                export.assert_not_called()
            with self.assertRaises(ConformanceError):
                inherited.verify_controller_baselines(
                    run, {"path": str(ROOT / "global.json"), "sha256": file_sha256(ROOT / "global.json")})

    def test_registration_replay_preserves_sealed_binary_and_dependency_inputs(self):
        import foundation_evidence as foundation
        import lifecycle_evidence as lifecycle
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary).resolve()
            source = owner / "snapshot"
            recipe = source / "tests/fixtures/lifecycle/registration/RegistrationConsumer"
            recipe.mkdir(parents=True)
            (recipe / "RegistrationConsumer.csproj").write_bytes(b"<Project/>")
            old = owner / "sealed/RegistrationConsumer.dll"
            old.parent.mkdir()
            old.write_bytes(b"old consumer")
            dependency = old.parent / "Hoard.Core.dll"
            dependency.write_bytes(b"old core")
            for path in (old, dependency):
                path.chmod(0o400)
            work = owner / "replay"
            work.mkdir()

            def build(project):
                binary = project.parent / "bin/Release/net10.0/RegistrationConsumer.dll"
                binary.parent.mkdir(parents=True)
                binary.write_bytes(b"new consumer")
                (binary.parent / "Hoard.Core.dll").write_bytes(b"candidate core")
                binary.with_suffix(".runtimeconfig.json").write_text(json.dumps({
                    "runtimeOptions": {"frameworks": [{"name": "Microsoft.AspNetCore.App"}]}}))
                return binary

            prepared = {"assembly": str(old), "sha256": file_sha256(old)}
            with inherited.controller_transport(ROOT, owner), patch.object(
                    lifecycle, "prepare_registration_baseline") as rebuild, patch.object(
                    foundation, "restore"), patch.object(foundation, "build", side_effect=build), patch.object(
                    lifecycle, "run", return_value="registration-compatible"):
                lifecycle.registration_compatibility(source, work, owner / "NuGet.Config", False, prepared=prepared)
            rebuild.assert_not_called()
            self.assertEqual(b"old consumer", (work / "registration-old/RegistrationConsumer.dll").read_bytes())
            self.assertEqual(b"candidate core", (work / "registration-old/Hoard.Core.dll").read_bytes())
            self.assertEqual(b"old core", dependency.read_bytes())
            self.assertEqual(prepared["sha256"], file_sha256(old))
            self.assertEqual(0o400, old.stat().st_mode & 0o777)

    def test_controller_runtime_inputs_are_explicit_owned_and_immutable(self):
        import lifecycle_evidence as lifecycle
        import conformance_legacy as legacy
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary).resolve()
            package, logger = owner / "sdk.nupkg", owner / "logger.dll"
            package.write_bytes(b"package")
            logger.write_bytes(b"logger")
            with inherited.controller_transport(
                    ROOT, owner, sdk_package=package, logger_path=logger) as controls, patch.object(
                    legacy, "composition_controller_command",
                    return_value=subprocess.CompletedProcess([], 0, "")) as command:
                lifecycle.run("dotnet", "test", "Hoard.Architecture.Tests.csproj")
                self.assertEqual(package, command.call_args.kwargs["sdk_package"])
                self.assertEqual(logger, command.call_args.kwargs["logger_path"])
                self.assertEqual({package.name: file_sha256(package), logger.name: file_sha256(logger)},
                                 controls["inputFiles"])
                package.write_bytes(b"changed")
                with self.assertRaisesRegex(ConformanceError, "InputChanged"):
                    lifecycle.run("dotnet", "test", "Hoard.Architecture.Tests.csproj")
                self.assertEqual(1, command.call_count)
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                with inherited.controller_transport(
                        ROOT, owner, sdk_package=package, logger_path=ROOT / "global.json"):
                    self.fail("Foreign runtime input was admitted")

    def test_native_preparation_failure_location_cannot_persist_exception_text_or_paths(self):
        import conformance_composition_checks as checks
        for error in (RuntimeError("private-canary"), PermissionError(13, "private-canary", "/private-canary")):
            output = io.StringIO()
            with self.subTest(error=type(error).__name__), redirect_stdout(output), patch.object(
                    checks, "execute", side_effect=error):
                self.assertEqual(2, checks.main(["--evidence", "/unused"]))
            self.assertNotIn("private-canary", output.getvalue())
            observed = json.loads(output.getvalue())
            self.assertEqual({
                "qualification": False, "status": "Incomplete", "code": "EvidenceIncomplete",
                "source": "conformance_composition_checks.py", "line": observed["line"],
            }, observed)
            self.assertIs(type(observed["line"]), int)
            self.assertGreater(observed["line"], 0)

    def test_controller_copies_are_writable_without_unsealing_source_snapshot(self):
        import foundation_evidence as foundation
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary).resolve()
            source = owner / "snapshot"
            source.mkdir()
            project = source / "CustomHost.csproj"
            project.write_bytes(b"<Project>Artifact.One</Project>")
            project.chmod(0o400)
            target = owner / "custom-host"
            original = foundation.copy_source
            with inherited.controller_transport(ROOT, owner):
                foundation.copy_source(source, target)
                self.assertEqual(0o600, (target / project.name).stat().st_mode & 0o777)
                (target / project.name).write_bytes(b"<Project>Artifact.Two</Project>")
                with tempfile.TemporaryDirectory() as outside:
                    sentinel = Path(outside) / "sentinel.cs"
                    sentinel.write_bytes(b"outside")
                    (source / "alias.cs").symlink_to(sentinel)
                    with self.assertRaises(ConformanceError):
                        foundation.copy_source(source, owner / "unsafe")
                    self.assertFalse((owner / "unsafe").exists())
                    self.assertEqual(b"outside", sentinel.read_bytes())
            self.assertIs(original, foundation.copy_source)
            self.assertEqual(0o400, project.stat().st_mode & 0o777)
            self.assertEqual(b"<Project>Artifact.One</Project>", project.read_bytes())

    def test_controller_input_closure_binds_private_sources_assets_and_package_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary).resolve()
            project = owner / "project"
            project.mkdir()
            cache = owner / "cache/hoard.example/0.1.0"
            cache.mkdir(parents=True)
            inputs = {
                project / "Example.cs": b"class Example {}",
                project / "Example.csproj": b"<Project/>",
                project / "packages.lock.json": b"{}",
                owner / "Directory.Build.props": b"<Project/>",
                owner / "Directory.Build.targets": b"<Project/>",
                owner / "Directory.Packages.props": b"<Project/>",
                owner / "global.json": b"{}",
                owner / "Example.dll": b"assembly",
                cache / "hoard.example.0.1.0.nupkg": b"archive",
                cache / ".nupkg.metadata": b"metadata",
            }
            for path, raw in inputs.items():
                path.write_bytes(raw)
            (project / "obj").mkdir()
            (project / "obj/Generated.cs").write_bytes(b"not a source input")
            for name in ("F07.preparation.packages.lock.json", "F07.preparation.acceptance.packages.lock.json"):
                path = project / "obj" / name
                inputs[path] = b"{}"
                path.write_bytes(inputs[path])
            assets = project / "obj/project.assets.json"
            assets.write_bytes(canonical_bytes({
                "libraries": {"Hoard.Example/0.1.0": {"type": "package", "path": "hoard.example/0.1.0"}},
                "packageFolders": {str(owner / "cache"): {}},
            }))
            manifest = owner / "manifest.json"
            manifest.write_bytes(canonical_bytes({
                "source": str(project), "assembly": str(owner / "Example.dll"),
                "assets": str(assets), "route": "/health",
            }))
            extra = owner / "openapi.json"
            extra.write_bytes(b"{}")
            expected = {path.relative_to(owner).as_posix(): file_sha256(path)
                        for path in (*inputs, assets, manifest, extra)}
            observed = inherited.controller_read_inputs(
                owner, {"HOARD_FOUNDATION_EVIDENCE": str(manifest)}, extra=(extra,))
            self.assertEqual(expected, observed)
            for path in (project / "packages.lock.json", project / "obj/F07.preparation.packages.lock.json",
                         project / "obj/F07.preparation.acceptance.packages.lock.json", owner / "Directory.Build.props",
                         owner / "Directory.Build.targets", owner / "Directory.Packages.props", owner / "global.json"):
                with self.subTest(path=path.name):
                    path.write_bytes(b"changed")
                    self.assertNotEqual(observed, inherited.controller_read_inputs(
                        owner, {"HOARD_FOUNDATION_EVIDENCE": str(manifest)}, extra=(extra,)))
                    path.write_bytes(inputs[path])
            (cache / ".nupkg.metadata").write_bytes(b"changed")
            self.assertNotEqual(observed, inherited.controller_read_inputs(
                owner, {"HOARD_FOUNDATION_EVIDENCE": str(manifest)}, extra=(extra,)))

    def test_controller_input_closure_rejects_foreign_manifests_and_private_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            owner = Path(temporary).resolve()
            foreign = Path(outside) / "manifest.json"
            foreign.write_bytes(b"{}")
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                inherited.controller_read_inputs(owner, {"HOARD_FOUNDATION_EVIDENCE": str(foreign)})
            original = owner / "image.dll"
            original.write_bytes(b"image")
            alias = owner / "alias.dll"
            alias.symlink_to(original)
            manifest = owner / "manifest.json"
            manifest.write_bytes(canonical_bytes({"assembly": str(alias)}))
            with self.assertRaises(ConformanceError):
                inherited.controller_read_inputs(owner, {"HOARD_FOUNDATION_EVIDENCE": str(manifest)})
            project = owner / "Owned.csproj"
            project.write_bytes(b"<Project/>")
            manifest.write_bytes(canonical_bytes({"project": str(project)}))
            (owner / "Directory.Build.props").symlink_to(foreign)
            with self.assertRaises(ConformanceError):
                inherited.controller_read_inputs(owner, {"HOARD_FOUNDATION_EVIDENCE": str(manifest)})
            self.assertEqual(b"{}", foreign.read_bytes())

    def test_project_only_input_binds_formatter_imports_assets_and_actual_archive_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary).resolve()
            project = owner / "Example.csproj"
            project.write_bytes(b"<Project/>")
            (owner / "obj").mkdir()
            imports = [owner / "obj" / ("Example.csproj.nuget.g." + suffix) for suffix in ("props", "targets")]
            for path in imports:
                path.write_bytes(b"<Project/>")
            cache = owner / "cache/hoard.example/0.1.0"
            cache.mkdir(parents=True)
            archive = cache / "hoard.example.0.1.0.nupkg"
            archive.write_bytes(b"actual archive")
            assets = owner / "obj/project.assets.json"
            assets.write_bytes(canonical_bytes({
                "libraries": {"Hoard.Example/0.1.0": {"type": "package", "path": "hoard.example/0.1.0"}},
                "packageFolders": {str(owner / "cache"): {}},
            }))
            manifest = owner / "manifest.json"
            manifest.write_bytes(canonical_bytes({"project": str(project)}))
            observed = inherited.controller_read_inputs(owner, {"evidence": str(manifest)})
            self.assertEqual({path.relative_to(owner).as_posix(): file_sha256(path)
                              for path in (project, manifest, assets, archive, *imports)}, observed)
            for path in (archive, *imports):
                with self.subTest(path=path.name):
                    original = path.read_bytes()
                    path.write_bytes(b"changed")
                    self.assertNotEqual(observed, inherited.controller_read_inputs(owner, {"evidence": str(manifest)}))
                    path.write_bytes(original)

    def test_controller_preparation_rejects_foreign_source_before_running_borrowed_code(self):
        import foundation_evidence as foundation
        with tempfile.TemporaryDirectory() as temporary, patch.object(foundation, "packages") as prepare:
            with self.assertRaisesRegex(ConformanceError, "OwnershipInvalid"):
                inherited.prepare_controller_evidence(ROOT, temporary, ROOT)
            prepare.assert_not_called()

    def test_controller_evidence_is_explicitly_forwarded_bound_and_owned(self):
        import lifecycle_evidence as lifecycle
        import conformance_legacy as legacy
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary).resolve()
            manifest = owner / "lifecycle-evidence.json"
            manifest.write_bytes(b'{"graphs":[]}')
            with inherited.controller_transport(ROOT, owner) as controls, patch.dict(
                    os.environ, {"HOARD_LIFECYCLE_EVIDENCE": str(manifest)}), patch.object(
                    legacy, "composition_controller_command",
                    return_value=subprocess.CompletedProcess([], 0, "")) as command:
                lifecycle.run("dotnet", "test", "Hoard.Architecture.Tests.csproj")
                self.assertEqual(str(manifest), command.call_args.kwargs["env"]["HOARD_LIFECYCLE_EVIDENCE"])
                self.assertEqual(legacy._hash(manifest), controls["inputFiles"][manifest.name])
            with tempfile.TemporaryDirectory() as outside, inherited.controller_transport(ROOT, owner), \
                    patch.dict(os.environ, {"HOARD_LIFECYCLE_EVIDENCE": str(Path(outside) / "manifest.json")}), \
                    patch.object(legacy, "composition_controller_command") as command, \
                    self.assertRaises(ConformanceError):
                lifecycle.run("dotnet", "test", "Hoard.Architecture.Tests.csproj")
            command.assert_not_called()
            with inherited.controller_transport(ROOT, owner), patch.dict(
                    os.environ, {"HOARD_LIFECYCLE_EVIDENCE": str(manifest)}), patch.object(
                    legacy, "composition_controller_command",
                    side_effect=lambda *args, **kwargs: manifest.write_bytes(b'{"graphs":[1]}')), \
                    self.assertRaisesRegex(ConformanceError, "InputChanged"):
                lifecycle.run("dotnet", "test", "Hoard.Architecture.Tests.csproj")

    def test_borrowed_controller_transport_rejects_raw_diagnostics_and_restores_entry_points(self):
        import configuration_evidence as configuration
        import discovery_evidence as discovery
        import foundation_evidence as foundation
        import lifecycle_evidence as lifecycle
        import conformance_legacy as legacy
        modules = (foundation, lifecycle, configuration, discovery)
        originals = [module.run for module in modules]
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary)
            os.chmod(owner, 0o700)
            diagnostics = io.StringIO()
            with inherited.controller_transport(ROOT, owner), redirect_stdout(diagnostics), patch.object(
                    legacy, "capture", return_value=subprocess.CompletedProcess(
                        ["dotnet", "build", "Consumer.csproj"], 0, b"private-canary\n")):
                for module in modules:
                    with self.subTest(module=module.__name__), self.assertRaisesRegex(
                            RuntimeError, "^Legacy composition command UnknownDiagnostic.$"):
                        module.run("dotnet", "build", "Consumer.csproj")
            self.assertEqual(originals, [module.run for module in modules])
            self.assertNotIn("private-canary", diagnostics.getvalue())
            self.assertEqual([{
                "qualification": False, "phase": "inherited-controller-failure",
                "controller": "preparation", "commandSequence": index, "operation": "build",
                "code": "UnknownDiagnostic",
            } for index in range(1, 5)], [json.loads(line) for line in diagnostics.getvalue().splitlines()])

    def test_expands_parameters_without_copying_private_arguments(self):
        raw = b'''public sealed class OriginalTests
{
    [Theory]
    [InlineData("""{"value":"private-canary"}""")]
    [InlineData("second-canary")]
    public async Task Original(string input) { }
    [Fact]
    public void Separate() { }
    public async Task Helper() { }
}'''
        self.assertEqual({
            "Hoard.Composition.Tests.OriginalTests.Original": 2,
            "Hoard.Composition.Tests.OriginalTests.Separate": 1,
        }, FREEZE.methods_in_source(raw))

    def test_rejects_unexpanded_or_duplicate_assertions(self):
        for body in (
                "[Theory]\n[MemberData(nameof(Private))]\npublic Task Original(string input) { }",
                "[Theory]\npublic Task Original(string input) { }",
                "[Fact]\npublic Task Original(string input) { }",
                "[Fact]\npublic Task Original() { }\n[Fact]\npublic Task Original() { }",
                "[Fact]\npublic ValueTask Original() { }"):
            with self.subTest(body=body), self.assertRaises(ValueError):
                FREEZE.methods_in_source(("public sealed class OriginalTests\n{\n" + body + "\n}").encode())

    def test_frozen_inventory_is_derived_only_from_immutable_baseline(self):
        path = ROOT / "tests/fixtures/conformance/baselines/composition-inventory.json"
        self.assertEqual(json.loads(path.read_bytes()), FREEZE.freeze())

    def test_exact_discovery_rejects_missing_duplicate_foreign_and_misexpanded_parameters(self):
        value = json.loads((ROOT / inherited.INVENTORY_PATH).read_bytes())
        methods = inherited.inventory(canonical_bytes(value), value["sourceFiles"])
        rows = [{"fullyQualifiedName": name,
                 "testIdentity": name + '(testCaseSha256: "' + f"{index:064x}" + '")'}
                for name, entry in methods.items() if name.startswith("Hoard.Composition.Tests.")
                for index in range(entry["parameterCount"])]
        for mutation in ("none", "missing", "duplicate", "changed-method", "raw-display", "extra-key",
                         "case-id", "invalid-case-id", "duplicate-case-id"):
            altered = copy.deepcopy(rows)
            if mutation == "missing":
                altered.pop()
            elif mutation == "duplicate":
                altered[-1] = altered[0]
            elif mutation == "changed-method":
                altered[-1]["fullyQualifiedName"] = "Hoard.Composition.Tests.Foreign.Test"
            elif mutation == "raw-display":
                altered[-1]["testIdentity"] = altered[-1]["fullyQualifiedName"] + '(value: "canary")'
            elif mutation == "extra-key":
                altered[-1]["privateDisplay"] = "canary"
            elif mutation in ("case-id", "invalid-case-id", "duplicate-case-id"):
                altered[-1]["testCaseId"] = "10000000-0000-0000-0000-000000000001"
                if mutation == "invalid-case-id":
                    altered[-1]["testCaseId"] = "private-canary"
                elif mutation == "duplicate-case-id":
                    altered[0]["testCaseId"] = altered[-1]["testCaseId"]
            with self.subTest(mutation=mutation):
                if mutation in ("none", "case-id"):
                    self.assertEqual(len(rows), len(inherited.admit_discovery(
                        canonical_bytes(altered), methods, assembly="Hoard.Composition.Tests")))
                else:
                    with self.assertRaises(ConformanceError):
                        inherited.admit_discovery(
                            canonical_bytes(altered), methods, assembly="Hoard.Composition.Tests")

    def test_inventory_rejects_source_drift_omitted_cases_and_falsified_parameter_totals(self):
        value = json.loads((ROOT / inherited.INVENTORY_PATH).read_bytes())
        for mutation in ("changed-source", "missing-case", "missing-method", "wrong-count", "resealed-count"):
            altered = copy.deepcopy(value)
            if mutation == "changed-source":
                altered["sourceFiles"][altered["entries"][0]["sourcePath"]] = "0" * 64
            elif mutation == "missing-case":
                altered["caseMethods"].pop("CFG-02")
            elif mutation == "missing-method":
                altered["entries"].pop()
            elif mutation == "wrong-count":
                altered["entries"][0]["parameterCount"] += 1
            elif mutation == "resealed-count":
                altered["entries"][0]["parameterCount"] += 1
                altered["groupParameters"][altered["entries"][0]["group"]] += 1
            with self.subTest(mutation=mutation), self.assertRaises(ConformanceError):
                inherited.inventory(canonical_bytes(altered), value["sourceFiles"])


if __name__ == "__main__":
    unittest.main()
