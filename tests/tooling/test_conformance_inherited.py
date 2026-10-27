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
                                                     return_value=nullcontext()), patch.object(
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
                owner / "Example.dll": b"assembly",
                cache / "hoard.example.0.1.0.nupkg": b"archive",
                cache / ".nupkg.metadata": b"metadata",
            }
            for path, raw in inputs.items():
                path.write_bytes(raw)
            (project / "obj").mkdir()
            (project / "obj/Generated.cs").write_bytes(b"not a source input")
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
        for mutation in ("none", "missing", "duplicate", "changed-method", "raw-display", "extra-key"):
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
            with self.subTest(mutation=mutation):
                if mutation == "none":
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
