import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_evidence as evidence
import conformance_contributors as contributors
import conformance_case_catalog as catalog
from conformance_execution import OwnedRun, capture_control, command_environment


class NuGetContentToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("dotnet") is None:
            raise unittest.SkipTest("Managed NuGet content tool requires the pinned .NET SDK")
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.parent = Path(cls.temporary.name).resolve()
        cls.owner = OwnedRun.allocate(cls.parent / "run", ROOT, profile="harness")
        source = cls.owner.root / "source"
        project = Path("tests/fixtures/conformance/BuildInputs/BuildInputs.csproj")
        for relative in (Path("global.json"), Path("Directory.Build.props"),
                         Path("Directory.Packages.props"), project, project.with_name("packages.lock.json"),
                         *(path.relative_to(ROOT) for path in (ROOT / project.parent).glob("*.cs"))):
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        cache = cls.owner.root / "cache/content"
        cache.mkdir()
        (cache / "tmp").mkdir()
        cls.environment = command_environment(cls.owner.root, cache, {"DOTNET_ROLL_FORWARD": "LatestPatch"})
        cls.generated = cls.owner.root / "tool-build/obj"
        cls.output = cls.owner.root / "tool-build/bin/Release/net10.0"
        cls.source = source
        config = cls.owner.root / "NuGet.Config"
        config.write_bytes(b"<configuration><packageSources><clear /></packageSources></configuration>")
        code, _ = capture_control(
            ["dotnet", "build", str(source / project), "-c", "Release", "-p:RestoreLockedMode=true",
             "-p:RestoreConfigFile=" + str(config), "-p:UseSharedCompilation=false", "-nodeReuse:false", "-v", "quiet",
             "-p:BaseIntermediateOutputPath=" + str(cls.generated) + "/",
             "-p:BaseOutputPath=" + str(cls.output.parents[1]) + "/", "-p:PathMap=",
             "-p:EmitCompilerGeneratedFiles=true", "-p:CompilerGeneratedFilesOutputPath=" + str(cls.generated / "generated")],
            cwd=source, env=cls.environment, limit=65536, timeout=120)
        if code:
            raise AssertionError("Managed NuGet content tool build failed")
        cls.tool = cls.output / "Hoard.Fixtures.Conformance.BuildInputs.dll"

    @classmethod
    def tearDownClass(cls):
        cls.owner.transition("Active")
        cls.owner.transition("Settling")
        cls.owner.release()

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(dir=self.owner.root))
        self.prefix = "acme.dependency/2.4.0-preview.1"
        self.cache = self.case / "packages"
        directory = self.cache / self.prefix
        directory.mkdir(parents=True)
        self.archive = directory / "acme.dependency.2.4.0-preview.1.nupkg"
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("Acme.Dependency.nuspec", (
                "<package><metadata><id>Acme.Dependency</id><version>2.4.0-preview.1</version></metadata></package>"))
            archive.writestr("build/Acme.Dependency.props", "<Project />")
        self.assets = self.case / "assets.json"
        self.graph = {"version": 3, "libraries": {"Acme.Dependency/2.4.0-preview.1": {
            "type": "package", "path": self.prefix}}}
        self.assets.write_bytes(evidence.canonical_bytes(self.graph))
        self.output = self.case / "content.json"
        self.request = self.case / "request.json"
        self.value = {
            "schemaVersion": 1, "qualification": False,
            "assets": {"path": self.relative(self.assets), "sha256": evidence.file_sha256(self.assets)},
            "cachePath": self.relative(self.cache), "outputPath": self.relative(self.output)}
        self.request.write_bytes(evidence.canonical_bytes(self.value))

    def relative(self, path):
        return path.relative_to(self.owner.root).as_posix()

    def invoke(self, *, digest=None, operation="content-hashes"):
        code, raw = capture_control(
            ["dotnet", str(self.tool), operation, str(self.owner.root), self.relative(self.request),
             evidence.file_sha256(self.request) if digest is None else digest],
            cwd=self.owner.root, env=self.environment, limit=65536, timeout=30)
        try:
            value = evidence.load_json(raw)
        except evidence.ConformanceError:
            raise AssertionError("Managed content tool emitted non-schema diagnostics") from None
        return code, value

    def test_managed_content_tool_computes_actual_unsigned_archive_receipt_and_refuses_output_reuse(self):
        code, event = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(event, {"event": "control", "code": "None", "value": 1})
        receipt = evidence.load_json(self.output.read_bytes())
        self.assertEqual(receipt, {"schemaVersion": 1, "qualification": False, "packages": [{
            "cachePath": self.prefix, "archiveSha256": evidence.file_sha256(self.archive),
            "contentSha512": hashlib.sha512(self.archive.read_bytes()).hexdigest()}]})
        original = self.output.read_bytes()
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "OwnershipInvalid"))
        self.assertEqual(self.output.read_bytes(), original)

    def test_managed_content_tool_rejects_changed_request_and_asset_hashes(self):
        code, event = self.invoke(digest="a" * 64)
        self.assertEqual((code, event["code"]), (2, "InputChanged"))
        self.assets.write_bytes(self.assets.read_bytes() + b" ")
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "InputChanged"))
        self.assertFalse(self.output.exists())

    def test_managed_content_tool_rejects_duplicate_request_fields_and_foreign_paths(self):
        original = self.request.read_bytes()
        self.request.write_bytes(original[:-1] + b',"schemaVersion":1}')
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "EvidenceSchemaInvalid"))
        self.value["assets"]["path"] = "../outside-canary"
        self.request.write_bytes(evidence.canonical_bytes(self.value))
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "OwnershipInvalid"))
        self.assertFalse(self.output.exists())

    def test_managed_content_tool_rejects_linked_archives_without_altering_outside_canary(self):
        outside = self.parent / "outside-private-canary"
        outside.write_bytes(b"private-canary")
        self.archive.unlink()
        self.archive.symlink_to(outside)
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "OwnershipInvalid"))
        self.assertEqual(outside.read_bytes(), b"private-canary")
        self.assertFalse(self.output.exists())

    def test_managed_content_tool_rejects_foreign_archive_metadata_and_oversized_assets(self):
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("Foreign.nuspec", (
                "<package><metadata><id>Foreign</id><version>2.4.0-preview.1</version></metadata></package>"))
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "InputChanged"))
        self.assets.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        code, event = self.invoke()
        self.assertEqual((code, event["code"]), (2, "OutputLimitExceeded"))
        self.assertFalse(self.output.exists())

    def pdb_request(self):
        image_directory = self.case / "image"
        image_directory.mkdir()
        name = "Hoard.Fixtures.Conformance.BuildInputs"
        image, pdb = image_directory / (name + ".dll"), image_directory / (name + ".pdb")
        for path in (image, pdb):
            shutil.copyfile(self.tool.parent / path.name, path)
        value = {
            "schemaVersion": 1, "qualification": False,
            "sourcePath": self.relative(self.source), "generatedPath": self.relative(self.generated),
            "outputRoot": self.relative(image_directory),
            "project": "tests/fixtures/conformance/BuildInputs/BuildInputs.csproj",
            "assembly": {"path": image.name, "sha256": evidence.file_sha256(image)},
            "pdb": {"path": pdb.name, "sha256": evidence.file_sha256(pdb)},
            "outputPath": self.relative(self.output_receipt)}
        self.request.write_bytes(evidence.canonical_bytes(value))
        return value, image, pdb

    @property
    def output_receipt(self):
        return self.case / "documents.json"

    def test_managed_pdb_tool_binds_actual_image_and_document_checksums_without_output_reuse(self):
        value, _, _ = self.pdb_request()
        code, event = self.invoke(operation="pdb-documents")
        self.assertEqual(code, 0)
        receipt = evidence.load_json(self.output_receipt.read_bytes())
        self.assertEqual(event, {"event": "control", "code": "None", "value": len(receipt["documents"])})
        self.assertEqual(receipt["assembly"], value["assembly"])
        self.assertEqual(receipt["pdb"], value["pdb"])
        self.assertEqual(receipt["project"], value["project"])
        self.assertIn("source/tests/fixtures/conformance/BuildInputs/Program.cs", receipt["documents"])
        self.assertTrue(any(path.startswith("generated/") for path in receipt["documents"]))
        for identity, hashed in receipt["documents"].items():
            namespace, relative = identity.split("/", 1)
            root = self.source if namespace == "source" else self.generated
            self.assertEqual(hashed, evidence.file_sha256(root / relative))
        original = self.output_receipt.read_bytes()
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "OwnershipInvalid")
        self.assertEqual(self.output_receipt.read_bytes(), original)

    def test_managed_pdb_tool_rejects_rehashed_checksum_tamper_and_changed_source(self):
        value, _, pdb = self.pdb_request()
        original = pdb.read_bytes()
        pdb.write_bytes(original + b"checksum-tamper")
        value["pdb"]["sha256"] = evidence.file_sha256(pdb)
        self.request.write_bytes(evidence.canonical_bytes(value))
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "ProofMismatch")
        self.assertFalse(self.output_receipt.exists())
        pdb.write_bytes(original)
        value["pdb"]["sha256"] = evidence.file_sha256(pdb)
        self.request.write_bytes(evidence.canonical_bytes(value))
        path = self.source / "tests/fixtures/conformance/BuildInputs/Program.cs"
        source = path.read_bytes()
        try:
            path.write_bytes(source + b"\n")
            self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "InputChanged")
            self.assertFalse(self.output_receipt.exists())
        finally:
            path.write_bytes(source)

    def test_managed_pdb_tool_rejects_foreign_paths_links_and_request_changes(self):
        value, _, pdb = self.pdb_request()
        self.assertEqual(self.invoke(operation="pdb-documents", digest="a" * 64)[1]["code"], "InputChanged")
        value["pdb"]["path"] = "../outside-private-canary"
        self.request.write_bytes(evidence.canonical_bytes(value))
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "OwnershipInvalid")
        outside = self.parent / "outside-private-pdb"
        shutil.copyfile(pdb, outside)
        pdb.unlink()
        pdb.symlink_to(outside)
        value["pdb"]["path"] = pdb.name
        self.request.write_bytes(evidence.canonical_bytes(value))
        before = evidence.file_sha256(outside)
        self.assertEqual(self.invoke(operation="pdb-documents")[1]["code"], "OwnershipInvalid")
        self.assertEqual(evidence.file_sha256(outside), before)
        self.assertFalse(self.output_receipt.exists())

    def evaluation_request(self):
        source = self.case / "evaluation-source"
        (source / "Adapter").mkdir(parents=True)
        (source / "Shared").mkdir()
        inputs = {
            "Directory.Build.props": '<Project><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup>'
                '<Import Project="Release.props" Condition="\'$(Configuration)\' == \'Release\'" /></Project>',
            "Release.props": '<Project><ItemGroup><Compile Include="$(MSBuildThisFileDirectory)Injected.cs" /></ItemGroup></Project>',
            "Injected.cs": "public class Injected { }\n",
            "Adapter/Adapter.csproj": '<Project Sdk="Microsoft.NET.Sdk"><ItemGroup>'
                '<ProjectReference Include="../Shared/Shared.csproj" /></ItemGroup></Project>',
            "Adapter/Binding.cs": "public class Binding { }\n",
            "Adapter/Empty.txt": "",
            "Shared/Shared.csproj": '<Project Sdk="Microsoft.NET.Sdk" />',
            "Shared/Shared.cs": "public class Shared { }\n"}
        for relative, text in inputs.items():
            (source / relative).write_text(text)
        code, raw = capture_control(["dotnet", "--version"], cwd=self.source,
                                    env=self.environment, limit=128, timeout=30)
        self.assertEqual(code, 0)
        version = raw.decode("ascii").strip()
        self.assertRegex(version, r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
        code, raw = capture_control(["dotnet", "--list-sdks"], cwd=self.source,
                                    env=self.environment, limit=4096, timeout=30)
        self.assertEqual(code, 0)
        matches = [re.fullmatch(re.escape(version) + r" \[([^\r\n]+)\]", line)
                   for line in raw.decode("utf-8").splitlines()]
        selected = [match[1] for match in matches if match is not None]
        self.assertEqual(len(selected), 1)
        toolchain = Path(selected[0]).resolve().parent
        self.msbuild = Path(selected[0]).resolve() / version / "MSBuild.dll"
        code, raw = capture_control(["dotnet", "--list-runtimes"], cwd=self.source,
                                    env=self.environment, limit=4096, timeout=30)
        self.assertEqual(code, 0)
        runtimes = [re.fullmatch(r"Microsoft\.NETCore\.App (10\.0\.[0-9]+) \[[^\r\n]+\]", line)
                    for line in raw.decode("utf-8").splitlines()]
        installed = [match[1] for match in runtimes if match is not None]
        self.assertTrue(installed)
        self.runtime_version = max(installed, key=lambda version: tuple(map(int, version.split("."))))
        receipt = self.case / "evaluation.json"
        value = {"schemaVersion": 1, "qualification": False, "sourcePath": self.relative(source),
                 "project": "Adapter/Adapter.csproj", "toolchainRoot": str(toolchain),
                 "sources": dict(evidence.input_manifest(source, sorted(inputs))),
                 "outputPath": self.relative(receipt)}
        self.request.write_bytes(evidence.canonical_bytes(value))
        return value, source, receipt

    def evaluate(self, *, digest=None):
        driver = self.case / "evaluation.proj"
        document = ET.Element("Project")
        name = "Hoard.Fixtures.Conformance.BuildInputs.ReadBindingInputs"
        ET.SubElement(document, "UsingTask", TaskName=name, AssemblyFile=str(self.tool))
        target = ET.SubElement(document, "Target", Name="Capture")
        ET.SubElement(target, name, OwnedRootBase64=base64.b64encode(str(self.owner.root).encode()).decode(),
                      RequestPath=self.relative(self.request),
                      RequestSha256=evidence.file_sha256(self.request) if digest is None else digest)
        driver.write_bytes(ET.tostring(document, encoding="utf-8"))
        code, raw = capture_control(
            ["dotnet", "exec", "--fx-version", self.runtime_version, str(self.msbuild), str(driver),
             "-target:Capture", "-noconsolelogger", "-nologo",
             "-nodeReuse:false", "-verbosity:quiet"],
            cwd=self.source, env={**self.environment, "DOTNET_ROLL_FORWARD": "Disable"}, limit=4096, timeout=60)
        try:
            event = evidence.load_json(raw)
        except evidence.ConformanceError:
            raise AssertionError("Managed evaluation task emitted no safe control event") from None
        return code, event

    def test_managed_evaluation_task_observes_conditional_imports_and_referenced_project_sources(self):
        value, source, receipt = self.evaluation_request()
        code, event = self.evaluate()
        self.assertEqual(code, 0)
        rows = evidence.load_json(receipt.read_bytes())["Items"]["_BindingInputs"]
        self.assertEqual(event, {"event": "control", "code": "None", "value": len(rows)})
        identities = {row["Identity"] for row in rows}
        self.assertTrue({"source/Release.props", "source/Injected.cs", "source/Shared/Shared.csproj",
                         "source/Shared/Shared.cs", "source/Adapter/Binding.cs", "source/Adapter/Empty.txt"} <= identities)
        self.assertTrue(any(path.startswith("toolchain/") for path in identities))
        self.assertTrue(all(set(row) == {"Identity", "Kind", "Sha256"} for row in rows))
        binding = contributors.BindingProject(source, value["project"], {}, value["sources"])
        admitted = contributors.binding_evaluation_inputs(binding, receipt.read_bytes(), Path(value["toolchainRoot"]))
        self.assertIn("Adapter/Empty.txt", admitted["sources"])
        rows[0]["Sha256"] = "a" * 64
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_evaluation_inputs(
                binding, evidence.canonical_bytes({"Items": {"_BindingInputs": rows}}), Path(value["toolchainRoot"]))
        self.assertEqual(self.evaluate()[1]["code"], "OwnershipInvalid")

    def test_managed_evaluation_task_rejects_changed_requests_sources_and_undeclared_ambient_inputs(self):
        value, source, receipt = self.evaluation_request()
        self.assertEqual(self.evaluate(digest="a" * 64)[1]["code"], "InputChanged")
        path = source / "Adapter/Binding.cs"
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        self.assertEqual(self.evaluate()[1]["code"], "InputChanged")
        path.write_bytes(original)
        (source / "Adapter/Ambient.cs").write_text("public class Ambient { }\n")
        self.assertEqual(self.evaluate()[1]["code"], "EvidenceIncomplete")
        self.assertFalse(receipt.exists())

    def test_managed_evaluation_task_rejects_links_foreign_toolchains_and_sanitizes_project_errors(self):
        value, source, receipt = self.evaluation_request()
        toolchain = value["toolchainRoot"]
        value["toolchainRoot"] = str(self.parent)
        self.request.write_bytes(evidence.canonical_bytes(value))
        self.assertEqual(self.evaluate()[1]["code"], "OwnershipInvalid")
        value["toolchainRoot"] = toolchain
        self.request.write_bytes(evidence.canonical_bytes(value))
        outside = self.parent / "outside-evaluation-canary"
        outside.write_bytes((source / "Adapter/Binding.cs").read_bytes())
        path = source / "Adapter/Binding.cs"
        path.unlink()
        path.symlink_to(outside)
        self.assertEqual(self.evaluate()[1]["code"], "OwnershipInvalid")
        self.assertEqual(outside.read_bytes(), b"public class Binding { }\n")
        path.unlink()
        path.write_bytes(outside.read_bytes())
        (source / "Adapter/Adapter.csproj").write_text("<Project>private-diagnostic-canary")
        value["sources"]["Adapter/Adapter.csproj"] = evidence.file_sha256(source / "Adapter/Adapter.csproj")
        self.request.write_bytes(evidence.canonical_bytes(value))
        self.assertEqual(self.evaluate()[1]["code"], "BindingInvalid")
        self.assertFalse(receipt.exists())


class ContributorAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="hoard-contributor-admission-")).resolve()
        self.parent.chmod(0o700)
        self.addCleanup(shutil.rmtree, self.parent)
        self.source = self.parent / "author"
        self.source.mkdir()
        self.project = self.source / "Adapter.csproj"
        self.project.write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        (self.source / "Binding.cs").write_text("namespace Acme; public sealed class Binding { }\n")
        (self.source / "packages.lock.json").write_text('{"version":2,"dependencies":{}}\n')
        self.sidecar = self.project.with_suffix(".conformance.json")
        adapter = {"packageId": "Acme.Adapter", "version": "0.1.0", "assemblyName": "Acme.Adapter"}
        self.registration = {
            "schemaVersion": 1, "project": "Adapter.csproj", "factoryType": "Acme.Binding",
            "adapterPackage": adapter,
            "declaration": {
                "schemaVersion": 1, "bindingId": "acme.metadata", "category": "metadata",
                "packageId": "Acme.Provider", "packageVersion": "0.1.0",
                "capabilities": ["metadata", "non-durable"],
                "faults": sorted(evidence._BINDING_REQUIRED_FAULTS["metadata"])},
            "components": {role: dict(adapter) for role in evidence._SESSION_ROLES["metadata"]},
            "sourceFiles": ["Adapter.csproj", "Adapter.conformance.json", "Binding.cs", "packages.lock.json"],
        }
        self.write(self.registration)

    def write(self, registration):
        self.sidecar.write_text(json.dumps(registration))

    def admit(self, profile="metadata"):
        return evidence.admit_invocation(ROOT, [
            "--profile", profile, "--binding-project", str(self.project),
            "--evidence", str(self.parent / "fresh")])

    def test_explicit_external_registration_freezes_declared_source_bytes_without_allocating_or_building(self):
        first = self.admit()
        self.assertEqual(first.binding_project, self.project)
        self.assertRegex(first.binding_inputs_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(first.binding_inputs_sha256, self.admit().binding_inputs_sha256)
        (self.source / "Binding.cs").write_text("namespace Acme; public sealed class Changed { }\n")
        self.assertNotEqual(first.binding_inputs_sha256, self.admit().binding_inputs_sha256)
        self.assertFalse((self.parent / "fresh").exists())
        self.assertEqual({path.name for path in self.source.iterdir()},
                         {"Adapter.csproj", "Adapter.conformance.json", "Binding.cs", "packages.lock.json"})
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            evidence.dispatch_invocation(first)

    def test_registration_rejects_foreign_categories_missing_hooks_and_provider_selected_omissions(self):
        for defect in ("category", "hook", "extra", "exclusions", "factory-injection", "factory-unicode",
                       "factory-package", "component-missing", "component-path", "duplicate-source",
                       "missing-project", "missing-registration", "escape", "unknown-source", "project-depth"):
            changed = copy.deepcopy(self.registration)
            if defect == "category":
                changed["declaration"]["category"] = "artifacts"
            elif defect == "hook":
                changed["declaration"]["faults"].pop()
            elif defect in ("extra", "exclusions"):
                changed[defect] = ["MP-21"]
            elif defect == "factory-injection":
                changed["factoryType"] = "Acme.Binding(); Bad()"
            elif defect == "factory-unicode":
                changed["factoryType"] = "Acme.B\u0131nding"
            elif defect == "factory-package":
                changed["components"]["factory"]["packageId"] = "Other.Adapter"
            elif defect == "component-missing":
                del changed["components"]["schema"]
            elif defect == "component-path":
                changed["components"]["store"]["assemblyName"] = "../Other"
            elif defect == "duplicate-source":
                changed["sourceFiles"].append("Binding.cs")
            elif defect == "missing-project":
                changed["sourceFiles"].remove("Adapter.csproj")
            elif defect == "missing-registration":
                changed["sourceFiles"].remove("Adapter.conformance.json")
            elif defect == "escape":
                changed["sourceFiles"].append("../outside.cs")
            elif defect == "project-depth":
                changed["project"] = "/".join(["nested"] * 33 + ["Adapter.csproj"])
            else:
                changed["sourceFiles"].append("Missing.cs")
            self.write(changed)
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                self.admit()
            self.assertFalse((self.parent / "fresh").exists())

    def test_registration_inventory_rejects_links_and_duplicate_json_keys(self):
        original = self.sidecar.read_bytes()
        self.sidecar.write_bytes(original.replace(b'"schemaVersion": 1', b'"schemaVersion": 1, "schemaVersion": 1', 1))
        with self.assertRaises(evidence.ConformanceError):
            self.admit()
        self.sidecar.write_bytes(original)
        source = self.source / "Binding.cs"
        target = self.parent / "outside.cs"
        target.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(target)
        with self.assertRaises(evidence.ConformanceError):
            self.admit()
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),
                         hashlib.sha256(b"namespace Acme; public sealed class Binding { }\n").hexdigest())
        self.assertFalse((self.parent / "fresh").exists())

    def test_owned_declared_snapshot_uses_admitted_bytes_without_building_or_modifying_author_sources(self):
        invocation = self.admit()
        original = {path.name: path.read_bytes() for path in self.source.iterdir()}
        run = OwnedRun.allocate(self.parent / "fresh", ROOT, profile="harness")
        captured = contributors.snapshot_binding_project(
            self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertEqual(captured.root, run.root / "binding-source")
        self.assertEqual(captured.project, "Adapter.csproj")
        self.assertEqual(captured.inputs_sha256, invocation.binding_inputs_sha256)
        self.assertEqual({path.name: path.read_bytes() for path in self.source.iterdir()}, original)
        self.assertEqual({path.name: path.read_bytes() for path in captured.root.iterdir()}, original)
        self.assertTrue(all(path.stat().st_mode & 0o777 == 0o400 for path in captured.root.iterdir()))
        self.assertFalse((self.source / "obj").exists())
        self.assertFalse((captured.root / "obj").exists())

    def test_owned_snapshot_rejects_changes_after_admission_before_copy_and_during_copy(self):
        invocation = self.admit()
        source = self.source / "Binding.cs"
        original = source.read_bytes()
        run = OwnedRun.allocate(self.parent / "fresh", ROOT, profile="harness")
        source.write_bytes(original + b"// changed after admission\n")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.snapshot_binding_project(
                self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertFalse((run.root / "binding-source").exists())
        source.write_bytes(original)
        registration = self.sidecar.read_bytes()
        changed = copy.deepcopy(self.registration)
        changed["factoryType"] = "Acme.OtherBinding"
        self.write(changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.snapshot_binding_project(
                self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertFalse((run.root / "binding-source").exists())
        self.sidecar.write_bytes(registration)
        actual = evidence._source_file

        def mutate_after_copy(directory, relative, **options):
            result = actual(directory, relative, **options)
            if relative == "Binding.cs" and options.get("target") is not None:
                source.write_bytes(original + b"// changed during copy\n")
            return result

        with mock.patch.object(evidence, "_source_file", side_effect=mutate_after_copy):
            with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                contributors.snapshot_binding_project(
                    self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertEqual((run.root / "binding-source/Binding.cs").read_bytes(), original)
        self.assertFalse((self.source / "obj").exists())

    def test_owned_snapshot_rejects_output_inside_author_source_root(self):
        invocation = self.admit()
        original = (self.source / "Binding.cs").read_bytes()
        self.source.chmod(0o700)
        run = OwnedRun.allocate(self.source / "fresh", ROOT, profile="harness")
        with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
            contributors.snapshot_binding_project(
                self.project, "metadata", invocation.binding_inputs_sha256, run)
        self.assertEqual((self.source / "Binding.cs").read_bytes(), original)
        self.assertFalse((run.root / "binding-source").exists())

    def test_typed_factory_source_requires_selected_actual_adapter_image_and_provider_package(self):
        feed = self.parent / "feed"
        feed.mkdir()

        def package(name):
            with zipfile.ZipFile(feed / f"{name}.0.1.0.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                archive.writestr(f"lib/net10.0/{name}.dll", name.encode("ascii"))
            return evidence.package_identity(feed, name, "0.1.0")

        adapter, provider = package("Acme.Adapter"), package("Acme.Provider")
        for category in ("metadata", "artifacts"):
            with self.subTest(category=category):
                registration = copy.deepcopy(self.registration)
                registration["declaration"].update(
                    category=category, bindingId=f"acme.{category}",
                    capabilities=([category, "non-durable"] if category == "metadata"
                                  else [category, "non-durable-simulation", "enumeration-incomplete"]),
                    faults=sorted(evidence._BINDING_REQUIRED_FAULTS[category]))
                registration["components"] = {
                    role: dict(registration["adapterPackage"]) for role in evidence._SESSION_ROLES[category]}
                self.write(registration)
                project = contributors.admit_binding_project(self.project, category)
                source = contributors.binding_factory_source(project, adapter, provider)
                self.assertIn(b"new global::Acme.Binding(", source)
                self.assertIn(provider["sha256"].encode("ascii"), source)
                if category == "artifacts":
                    self.assertIn(b"ArtifactAssertionOptions options)", source)
                    self.assertIn(b"ArgumentNullException.ThrowIfNull(options)", source)
                    self.assertEqual(source.count(b"return Validate(new global::Acme.Binding("), 1)
                    self.assertEqual(source.count(b"Validate(new global::Acme.Binding("), 2)
                    self.assertEqual(source.count(b"ConformanceBindingAdmission.Validate(actual,"), 1)
                else:
                    self.assertNotIn(b"ArtifactAssertionOptions", source)
                for selected_adapter, selected_provider in (
                        (provider, provider), (adapter, adapter),
                        ({**adapter, "runtimeAssemblies": {"lib/net10.0/Other.dll": "a" * 64}}, provider),
                        ({**adapter, "version": "0.2.0"}, provider),
                        (adapter, {**provider, "version": "0.2.0"})):
                    with self.assertRaisesRegex(evidence.ConformanceError, "^BindingInvalid$"):
                        contributors.binding_factory_source(project, selected_adapter, selected_provider)
                with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                    contributors.binding_factory_source(project, {**adapter, "sourceMapping": "nuget.org"}, provider)

    def test_registered_metadata_common_parameters_use_the_actual_binding_id_without_builtin_aliases(self):
        counts = catalog.metadata_common_consumer_origin_counts(binding_ids=("acme.metadata",))
        default = catalog.metadata_common_consumer_origin_counts()
        self.assertEqual(len(counts) * 2, len(default))
        self.assertEqual({identity.split("(provider:")[0] for identity in counts},
                         {identity.split("(provider:")[0] for identity in default})
        self.assertTrue(all('(provider: "acme.metadata"' in identity for identity in counts))
        self.assertFalse(any('"memory"' in identity or '"sqlite"' in identity for identity in counts))
        for invalid in ((), ("acme.metadata",) * 2, "acme.metadata", None, ("../foreign",)):
            with self.subTest(invalid=invalid), self.assertRaises(evidence.ConformanceError):
                catalog.metadata_common_consumer_origin_counts(binding_ids=invalid)

    def test_artifact_component_inventory_uses_registered_identity_without_builtin_applicability(self):
        profile = {"durability": "SimulationOnly", "enumeration": "Incomplete"}
        actual = catalog.contributor_artifact_component_origin_counts("acme.artifacts", profile=profile)
        self.assertEqual(len(actual), 110)
        self.assertEqual(sum(actual.values()), 111)
        self.assertEqual(set(actual.values()), {1, 2})
        self.assertTrue(all('(provider: "acme.artifacts"' in identity for identity in actual))
        self.assertFalse(any('"local"' in identity or '"object"' in identity for identity in actual))
        with mock.patch.object(catalog, "full_artifact_binding_scenarios", side_effect=AssertionError):
            self.assertEqual(catalog.contributor_artifact_component_origin_counts("acme.artifacts", profile=profile), actual)
        snapshot = catalog.contributor_artifact_component_origin_counts(
            "acme.artifacts", profile={"durability": "LocalProcessCrash", "enumeration": "Snapshot"})
        self.assertEqual(len(snapshot), 109)
        self.assertEqual(sum(snapshot.values()), 117)
        self.assertEqual(set(actual) - set(snapshot), {
            'Hoard.Fixtures.Conformance.Consumer.ContributorArtifactSessionTests.'
            'Observed_portable_consumers_preserve_actual_guarantees(provider: "acme.artifacts", consumer: "direct-availability")'})
        for durability, enumeration, rows, origins in (
                ("LocalProcessCrash", "Incomplete", 110, 118), ("SimulationOnly", "Snapshot", 109, 110)):
            crossed = catalog.contributor_artifact_component_origin_counts(
                "acme.artifacts", profile={"durability": durability, "enumeration": enumeration})
            self.assertEqual(len(crossed), rows)
            self.assertEqual(sum(crossed.values()), origins)
        for invalid in ("../foreign", "", None):
            with self.assertRaises(evidence.ConformanceError):
                catalog.contributor_artifact_component_origin_counts(invalid, profile=profile)
        for invalid in (None, {}, {**profile, "enumeration": "Unknown"}, {**profile, "extra": True}):
            with self.assertRaises(evidence.ConformanceError):
                catalog.contributor_artifact_component_origin_counts("acme.artifacts", profile=invalid)

    def test_artifact_profile_requires_unambiguous_input_bound_durability_and_enumeration(self):
        declaration = copy.deepcopy(self.registration["declaration"])
        declaration.update(
            category="artifacts", bindingId="acme.artifacts",
            capabilities=["artifacts", "non-durable-simulation", "enumeration-incomplete"],
            faults=sorted(evidence._BINDING_REQUIRED_FAULTS["artifacts"]))
        self.assertEqual(contributors.artifact_binding_profile(declaration),
                         {"durability": "SimulationOnly", "enumeration": "Incomplete"})
        durable = {**declaration, "capabilities": ["artifacts", "durable-local-process-crash", "enumeration-snapshot"]}
        self.assertEqual(contributors.artifact_binding_profile(durable),
                         {"durability": "LocalProcessCrash", "enumeration": "Snapshot"})
        for capabilities in (
                ["artifacts", "non-durable-simulation"],
                ["artifacts", "enumeration-incomplete"],
                ["artifacts", "non-durable-simulation", "enumeration-unknown"],
                [*declaration["capabilities"], "enumeration-unknown"],
                [*declaration["capabilities"], "durable-unknown"],
                [*declaration["capabilities"], "enumeration-snapshot"],
                [*declaration["capabilities"], "durable-local-process-crash"]):
            registration = copy.deepcopy(self.registration)
            registration["declaration"] = {**declaration, "capabilities": capabilities}
            registration["components"] = {
                role: dict(registration["adapterPackage"]) for role in evidence._SESSION_ROLES["artifacts"]}
            self.write(registration)
            with self.subTest(capabilities=capabilities), \
                    self.assertRaisesRegex(evidence.ConformanceError, "^BindingInvalid$"):
                contributors.admit_binding_project(self.project, "artifacts")

    def build_fixture(self, name="build"):
        (self.source / "packages.lock.json").write_text('{"version":2,"dependencies":{"net10.0":{}}}')
        self.write(self.registration)
        invocation = self.admit()
        run = OwnedRun.allocate(self.parent / name, ROOT, profile="harness")
        binding = contributors.snapshot_binding_project(
            self.project, "metadata", invocation.binding_inputs_sha256, run)
        configuration = run.root / "NuGet.Config"
        configuration.write_bytes(evidence.synthetic_nuget_configuration(run.root / "feed"))
        return binding, run, configuration

    def test_registered_build_isolates_each_declared_project_and_uses_exact_adapter_identity(self):
        nested = self.source / "shared"
        nested.mkdir()
        (nested / "Shared.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />')
        (nested / "packages.lock.json").write_text('{"version":2,"dependencies":{"net10.0":{}}}')
        self.registration["sourceFiles"].extend(["shared/Shared.csproj", "shared/packages.lock.json"])
        self.registration["adapterPackage"]["version"] = "2.4.0-preview.1"
        for component in self.registration["components"].values():
            component["version"] = "2.4.0-preview.1"
        binding, run, configuration = self.build_fixture()

        def pack(owner, project, config, cache, **options):
            self.assertIs(owner, run)
            self.assertEqual(project, binding.root / binding.project)
            self.assertEqual(config, configuration)
            self.assertEqual(options["package_id"], "Acme.Adapter")
            self.assertEqual(options["package_version"], "2.4.0-preview.1")
            properties = run.root / "binding-build/binding.props"
            self.assertEqual(options["properties"], ("-p:CustomAfterDirectoryBuildProps=" + str(properties),))
            groups = ET.parse(properties).findall("./Choose/When/PropertyGroup")
            self.assertEqual(len(groups), 2)
            self.assertEqual(len({group.findtext("BaseIntermediateOutputPath") for group in groups}), 2)
            for group in groups:
                output = Path(group.findtext("BaseOutputPath"))
                self.assertTrue(output.is_relative_to(run.root / "binding-build"))
                self.assertFalse(output.is_relative_to(binding.root))
            with zipfile.ZipFile(options["feed"] / "Acme.Adapter.2.4.0-preview.1.nupkg", "w") as archive:
                archive.writestr("Acme.Adapter.nuspec",
                                "<package><metadata><id>Acme.Adapter</id>"
                                "<version>2.4.0-preview.1</version></metadata></package>")
                archive.writestr("lib/net10.0/Acme.Adapter.dll", b"fixture image")

        with mock.patch("conformance_sdk_checks.build", side_effect=pack):
            result = contributors.build_binding_project(binding, run, configuration, run.root / "feed")
        self.assertEqual(result["package"]["version"], "2.4.0-preview.1")
        self.assertEqual(set(result["projects"]), {"Adapter.csproj", "shared/Shared.csproj"})
        self.assertFalse(result["qualification"])
        self.assertFalse((binding.root / "obj").exists())
        self.assertFalse((binding.root / "shared/obj").exists())
        self.assertEqual(evidence.input_manifest(binding.root, sorted(binding.sources)), binding.sources)

    def test_registered_build_rejects_foreign_contexts_and_undeclared_locks_before_commands(self):
        binding, run, configuration = self.build_fixture()
        foreign = contributors.admit_binding_project(self.project, "metadata")
        with mock.patch("conformance_sdk_checks.build") as build:
            for selected, config in ((foreign, configuration), (binding, self.parent / "foreign.config"),
                                      (binding, run.root / ".." / "foreign.config"),
                                      (binding, run.root / "unsupported;config")):
                with self.subTest(root=selected.root, config=config), \
                        self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                    contributors.build_binding_project(selected, run, config, run.root / "feed")
            build.assert_not_called()
        self.registration["sourceFiles"].remove("packages.lock.json")
        self.write(self.registration)
        binding, run, configuration = self.build_fixture("missing-lock")
        with mock.patch("conformance_sdk_checks.build") as build, \
                self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            contributors.build_binding_project(binding, run, configuration, run.root / "feed")
        build.assert_not_called()

    def test_registered_build_rechecks_frozen_source_and_generated_controls_even_after_failure(self):
        for index, defect in enumerate(("source", "mode", "properties", "lock", "configuration", "extra")):
            binding, run, configuration = self.build_fixture("changed-" + str(index))

            def mutate(*args, **kwargs):
                if defect in ("source", "mode"):
                    path = binding.root / "Binding.cs"
                elif defect == "properties":
                    path = run.root / "binding-build/binding.props"
                elif defect == "configuration":
                    path = configuration
                elif defect == "extra":
                    path = binding.root / "undeclared.cs"
                    path.touch()
                else:
                    path = next((run.root / "binding-build").glob("*/packages.lock.json"))
                path.chmod(0o600)
                if defect != "mode":
                    path.write_bytes(b"changed")
                raise evidence.ConformanceError("CommandFailed")

            with self.subTest(defect=defect), mock.patch("conformance_sdk_checks.build", side_effect=mutate), \
                    self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                contributors.build_binding_project(binding, run, configuration, run.root / "feed")

    def restore_graph_fixture(self):
        binding = contributors.admit_binding_project(self.project, "metadata")
        packages = self.parent / "packages"
        cache = packages / "acme.dependency/2.4.0-preview.1"
        cache.mkdir(parents=True)
        archive = cache / "acme.dependency.2.4.0-preview.1.nupkg"
        with zipfile.ZipFile(archive, "w") as packed:
            packed.writestr("Acme.Dependency.nuspec", (
                "<package><metadata><id>Acme.Dependency</id><version>2.4.0-preview.1</version></metadata></package>"))
            packed.writestr("build/Acme.Dependency.props", "<Project />")
        hashed = base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode("ascii")
        self.content_receipt = {"schemaVersion": 1, "qualification": False, "packages": [{
            "cachePath": "acme.dependency/2.4.0-preview.1",
            "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "contentSha512": hashlib.sha512(archive.read_bytes()).hexdigest()}]}
        assets = {
            "version": 3, "targets": {"net10.0": {
                "Acme.Dependency/2.4.0-preview.1": {"type": "package"}}},
            "libraries": {"Acme.Dependency/2.4.0-preview.1": {
                "type": "package", "path": "acme.dependency/2.4.0-preview.1", "sha512": hashed}},
            "packageFolders": {str(packages) + "/": {}},
            "project": {"restore": {
                "projectPath": str(self.project), "projectUniqueName": str(self.project),
                "packagesPath": str(packages)}}}
        lock = {"version": 2, "dependencies": {"net10.0": {
            "acme.dependency": {"type": "Direct", "resolved": "2.4.0-preview.1", "contentHash": hashed}}}}
        return binding, assets, lock, packages

    def test_restore_graph_binds_exact_package_versions_hashes_and_declared_project_references(self):
        shared = self.source / "shared"
        shared.mkdir()
        (shared / "Shared.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />')
        self.registration["sourceFiles"].append("shared/Shared.csproj")
        self.write(self.registration)
        binding, assets, lock, packages = self.restore_graph_fixture()
        key = "Acme.Shared/1.0.0"
        assets["libraries"][key] = {"type": "project", "msbuildProject": "shared/Shared.csproj"}
        assets["targets"]["net10.0"][key] = {"type": "project"}
        assets["targets"]["net10.0"]["Acme.Dependency/2.4.0-preview.1"]["dependencies"] = {"Acme.Shared": "1.0.0"}
        lock["dependencies"]["net10.0"]["acme.shared"] = {"type": "Project"}
        lock["dependencies"]["net10.0"]["acme.dependency"]["dependencies"] = {"Acme.Shared": "[1.0.0]"}
        raw = evidence.canonical_bytes(assets)
        result = contributors.binding_restore_graph(
            binding, raw, evidence.canonical_bytes(lock), binding.project, packages,
            expected_lock_sha256=evidence.digest(lock), content_hashes_data=evidence.canonical_bytes(self.content_receipt))
        archive = packages / "acme.dependency/2.4.0-preview.1/acme.dependency.2.4.0-preview.1.nupkg"
        self.assertEqual(result["packages"], {"acme.dependency/2.4.0-preview.1": {
            "packageId": "Acme.Dependency", "version": "2.4.0-preview.1",
            "nugetContentSha512": hashlib.sha512(archive.read_bytes()).hexdigest(),
            "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "archiveSha512": hashlib.sha512(archive.read_bytes()).hexdigest()}})
        self.assertEqual(result["projects"], {key: "shared/Shared.csproj"})
        self.assertEqual(result["assetsSha256"], hashlib.sha256(raw).hexdigest())
        self.assertFalse(result["qualification"])
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))
        assets["packageFolders"] = {str(packages): {}}
        self.assertEqual(contributors.binding_restore_graph(
            binding, evidence.canonical_bytes(assets), evidence.canonical_bytes(lock),
            binding.project, packages, expected_lock_sha256=evidence.digest(lock),
            content_hashes_data=evidence.canonical_bytes(self.content_receipt))["packages"], result["packages"])
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_restore_graph(binding, raw, evidence.canonical_bytes(lock),
                                               binding.project, packages, expected_lock_sha256="a" * 64,
                                               content_hashes_data=evidence.canonical_bytes(self.content_receipt))
        (self.source / "Binding.cs").write_bytes(b"changed")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_restore_graph(binding, raw, evidence.canonical_bytes(lock),
                                               binding.project, packages, expected_lock_sha256=evidence.digest(lock),
                                               content_hashes_data=evidence.canonical_bytes(self.content_receipt))

    def test_restore_graph_rejects_missing_foreign_duplicate_or_changed_package_and_edge_rows(self):
        binding, original, original_lock, packages = self.restore_graph_fixture()
        for defect in ("missing-library", "missing-lock", "foreign-target", "duplicate-id", "version",
                       "hash", "cache-owner", "edge", "type", "missing-type", "diagnostic", "framework"):
            assets, lock = copy.deepcopy(original), copy.deepcopy(original_lock)
            library = assets["libraries"]["Acme.Dependency/2.4.0-preview.1"]
            expected = "EvidenceIncomplete"
            if defect == "missing-library":
                assets["libraries"].clear()
            elif defect == "missing-lock":
                lock["dependencies"]["net10.0"].clear()
            elif defect == "foreign-target":
                assets["targets"]["net10.0"]["Foreign/1.0.0"] = {"type": "package"}
            elif defect == "duplicate-id":
                lock["dependencies"]["net10.0"]["Acme.Dependency"] = copy.deepcopy(
                    lock["dependencies"]["net10.0"]["acme.dependency"])
                expected = "EvidenceSchemaInvalid"
            elif defect == "version":
                lock["dependencies"]["net10.0"]["acme.dependency"]["resolved"] = "2.4.0"
                expected = "ProofMismatch"
            elif defect == "hash":
                library["sha512"] = base64.b64encode(b"q" * 64).decode("ascii")
                expected = "ProofMismatch"
            elif defect == "cache-owner":
                library["path"] = "foreign/2.4.0-preview.1"
                expected = "ProofMismatch"
            elif defect == "edge":
                assets["targets"]["net10.0"]["Acme.Dependency/2.4.0-preview.1"]["dependencies"] = {"Foreign": "1.0.0"}
            elif defect == "type":
                library["type"] = "project"
            elif defect == "missing-type":
                del library["type"]
                del assets["targets"]["net10.0"]["Acme.Dependency/2.4.0-preview.1"]["type"]
            elif defect == "diagnostic":
                assets["logs"] = [{"message": "private canary"}]
            else:
                assets["targets"]["net10.0/linux-x64"] = assets["targets"]["net10.0"]
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^" + expected + "$"):
                contributors.binding_restore_graph(binding, evidence.canonical_bytes(assets),
                                                   evidence.canonical_bytes(lock), binding.project, packages,
                                                   expected_lock_sha256=evidence.digest(lock),
                                                   content_hashes_data=evidence.canonical_bytes(self.content_receipt))

    def test_restore_graph_rejects_foreign_cache_project_paths_and_undeclared_project_references(self):
        binding, original, original_lock, packages = self.restore_graph_fixture()
        for defect in ("project", "unique-project", "cache", "fallback-cache", "outside-reference", "undeclared-reference"):
            assets, lock = copy.deepcopy(original), copy.deepcopy(original_lock)
            restore = assets["project"]["restore"]
            expected = "OwnershipInvalid"
            if defect == "project":
                restore["projectPath"] = str(self.parent / "foreign.csproj")
            elif defect == "unique-project":
                restore["projectUniqueName"] = str(self.parent / "foreign.csproj")
            elif defect == "cache":
                restore["packagesPath"] = str(self.parent)
            elif defect == "fallback-cache":
                assets["packageFolders"][str(self.parent) + "/"] = {}
            else:
                key = "Acme.Shared/1.0.0"
                assets["libraries"][key] = {
                    "type": "project", "msbuildProject": "../Outside.csproj" if defect == "outside-reference" else "Absent.csproj"}
                assets["targets"]["net10.0"][key] = {"type": "project"}
                lock["dependencies"]["net10.0"]["Acme.Shared"] = {"type": "Project"}
                if defect == "undeclared-reference":
                    expected = "EvidenceIncomplete"
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^" + expected + "$"):
                contributors.binding_restore_graph(binding, evidence.canonical_bytes(assets),
                                                   evidence.canonical_bytes(lock), binding.project, packages,
                                                   expected_lock_sha256=evidence.digest(lock),
                                                   content_hashes_data=evidence.canonical_bytes(self.content_receipt))

    def test_restore_graph_rejects_malformed_hashes_and_oversized_input(self):
        binding, assets, lock, packages = self.restore_graph_fixture()
        for hashed in ("not-base64", "!" * 88, base64.b64encode(b"x" * 63).decode("ascii")):
            assets["libraries"]["Acme.Dependency/2.4.0-preview.1"]["sha512"] = hashed
            with self.subTest(hashed=hashed), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                contributors.binding_restore_graph(binding, evidence.canonical_bytes(assets),
                                                   evidence.canonical_bytes(lock), binding.project, packages,
                                                   expected_lock_sha256=evidence.digest(lock),
                                                   content_hashes_data=evidence.canonical_bytes(self.content_receipt))
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            contributors.binding_restore_graph(binding, b"x" * (2 * 1024 * 1024 + 1), b"{}", binding.project, packages,
                                               expected_lock_sha256="a" * 64, content_hashes_data=b"{}")

    def test_restore_graph_checks_actual_cached_archives_and_aggregate_read_budget(self):
        binding, assets, lock, packages = self.restore_graph_fixture()
        archive = packages / "acme.dependency/2.4.0-preview.1/acme.dependency.2.4.0-preview.1.nupkg"
        original = archive.read_bytes()
        archive.write_bytes(original + b"changed")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_restore_graph(
                binding, evidence.canonical_bytes(assets), evidence.canonical_bytes(lock),
                binding.project, packages, expected_lock_sha256=evidence.digest(lock),
                content_hashes_data=evidence.canonical_bytes(self.content_receipt))
        archive.write_bytes(original)
        with mock.patch.object(evidence, "MAX_PROOF_BYTES", len(original) - 1), \
                self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            contributors.binding_restore_graph(
                binding, evidence.canonical_bytes(assets), evidence.canonical_bytes(lock),
                binding.project, packages, expected_lock_sha256=evidence.digest(lock),
                content_hashes_data=evidence.canonical_bytes(self.content_receipt))
        with zipfile.ZipFile(archive, "w") as packed:
            packed.writestr("Foreign.nuspec", (
                "<package><metadata><id>Foreign</id><version>2.4.0-preview.1</version></metadata></package>"))
            packed.writestr("build/Foreign.props", "<Project />")
        hashed = base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode("ascii")
        assets["libraries"]["Acme.Dependency/2.4.0-preview.1"]["sha512"] = hashed
        lock["dependencies"]["net10.0"]["acme.dependency"]["contentHash"] = hashed
        with self.assertRaises(evidence.ConformanceError):
            contributors.binding_restore_graph(
                binding, evidence.canonical_bytes(assets), evidence.canonical_bytes(lock),
                binding.project, packages, expected_lock_sha256=evidence.digest(lock),
                content_hashes_data=evidence.canonical_bytes(self.content_receipt))

    def test_restore_graph_requires_exact_closed_nuget_content_hash_receipt(self):
        binding, assets, lock, packages = self.restore_graph_fixture()
        for defect in ("missing", "foreign", "duplicate", "content", "archive", "unknown", "malformed"):
            receipt = copy.deepcopy(self.content_receipt)
            expected = "EvidenceSchemaInvalid"
            if defect == "missing":
                receipt["packages"].clear()
                expected = "ProofMismatch"
            elif defect == "foreign":
                receipt["packages"].append({**receipt["packages"][0], "cachePath": "foreign/1.0.0"})
                expected = "EvidenceIncomplete"
            elif defect == "duplicate":
                receipt["packages"].append(copy.deepcopy(receipt["packages"][0]))
            elif defect == "content":
                receipt["packages"][0]["contentSha512"] = "a" * 128
                expected = "ProofMismatch"
            elif defect == "archive":
                receipt["packages"][0]["archiveSha256"] = "a" * 64
                expected = "InputChanged"
            elif defect == "unknown":
                receipt["message"] = "private canary"
            else:
                receipt["packages"][0]["contentSha512"] = "not-a-hash"
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^" + expected + "$"):
                contributors.binding_restore_graph(
                    binding, evidence.canonical_bytes(assets), evidence.canonical_bytes(lock),
                    binding.project, packages, expected_lock_sha256=evidence.digest(lock),
                    content_hashes_data=evidence.canonical_bytes(receipt))

    def restore_capture_fixture(self):
        _, assets, lock, original_cache = self.restore_graph_fixture()
        binding, owner, _ = self.build_fixture()
        cache = owner.root / "cache/binding-build"
        shutil.copytree(original_cache, cache)
        assets["project"]["restore"].update({
            "projectPath": str(binding.root / binding.project),
            "projectUniqueName": str(binding.root / binding.project), "packagesPath": str(cache)})
        assets["packageFolders"] = {str(cache): {}}
        workspace = owner.root / "binding-build" / hashlib.sha256(binding.project.encode()).hexdigest()
        (workspace / "obj").mkdir(parents=True)
        (workspace / "obj/project.assets.json").write_bytes(evidence.canonical_bytes(assets))
        (workspace / "packages.lock.json").write_bytes(evidence.canonical_bytes(lock))
        tool = owner.root / "content-tool.dll"
        tool.write_bytes(b"fixture tool image")
        built = {"bindingInputsSha256": binding.inputs_sha256, "projects": {
            binding.project: {"root": workspace, "preparedLockSha256": evidence.digest(lock)}}}
        return binding, owner, built, tool, cache, workspace

    def test_restore_capture_uses_owned_hash_bound_request_and_exact_runtime_without_relaxing_native_environment(self):
        binding, owner, built, tool, cache, workspace = self.restore_capture_fixture()

        def capture(arguments, **options):
            self.assertEqual(arguments[:5], ["dotnet", "exec", "--fx-version", "10.0.3", str(tool)])
            self.assertEqual(options["kind"], "events")
            self.assertEqual(options["env"], {"DOTNET_ROLL_FORWARD": "Disable"})
            request = owner.root / arguments[-2]
            self.assertEqual(evidence.file_sha256(request), arguments[-1])
            self.assertEqual(request.stat().st_mode & 0o777, 0o400)
            value = evidence.load_json(request.read_bytes())
            self.assertEqual(value["cachePath"], cache.relative_to(owner.root).as_posix())
            (owner.root / value["outputPath"]).write_bytes(evidence.canonical_bytes(self.content_receipt))
            return mock.Mock(exit_code=0, events=({"event": "control", "code": "None", "value": 1},))

        with mock.patch.object(owner, "command", side_effect=capture):
            graphs = contributors.capture_binding_restore_graphs(binding, owner, built, tool, "10.0.3", cache)
        self.assertEqual(set(graphs), {binding.project})
        self.assertEqual(len(graphs[binding.project]["packages"]), 1)

    def test_restore_capture_rechecks_inputs_after_failed_child_and_does_not_accept_missing_control_events(self):
        for defect in ("control", "request", "assets", "tool", "source", "mode"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=self.parent) as nested:
                original_parent = self.parent
                self.parent = Path(nested)
                try:
                    binding, owner, built, tool, cache, workspace = self.restore_capture_fixture()
                finally:
                    self.parent = original_parent

                def capture(arguments, **options):
                    if defect == "control":
                        (workspace / "nuget-content.json").write_bytes(evidence.canonical_bytes(self.content_receipt))
                        return mock.Mock(exit_code=0, events=())
                    path = {"request": workspace / "nuget-content-request.json",
                            "assets": workspace / "obj/project.assets.json",
                            "tool": tool, "source": binding.root / "Binding.cs",
                            "mode": binding.root / "Binding.cs"}[defect]
                    path.chmod(0o600)
                    if defect != "mode":
                        path.write_bytes(b"changed")
                    raise evidence.ConformanceError("CommandFailed")

                with mock.patch.object(owner, "command", side_effect=capture), self.assertRaisesRegex(
                        evidence.ConformanceError, "^" + ("ProofMismatch" if defect == "control" else "InputChanged") + "$"):
                    contributors.capture_binding_restore_graphs(binding, owner, built, tool, "10.0.3", cache)

    def evaluation_capture_fixture(self):
        binding, owner, _ = self.build_fixture()
        tool = owner.root / "evaluation-tool.dll"
        tool.write_bytes(b"modeled evaluation tool")
        toolchain = self.parent / "toolchain"
        msbuild = toolchain / "sdk/10.0.203/MSBuild.dll"
        props = toolchain / "sdk/10.0.203/Sdks/Fixture.props"
        props.parent.mkdir(parents=True)
        msbuild.write_bytes(b"modeled msbuild host")
        props.write_bytes(b"<Project />")
        rows = [{"Identity": "source/" + path, "Kind": "source", "Sha256": binding.sources[path]}
                for path in (binding.project, "Binding.cs")]
        rows.append({"Identity": "toolchain/" + props.relative_to(toolchain).as_posix(), "Kind": "toolchain",
                     "Sha256": evidence.file_sha256(props)})
        return binding, owner, tool, toolchain, msbuild, props, rows

    def test_evaluation_capture_uses_safe_driver_hash_bound_inputs_and_explicit_sdk_runtime(self):
        binding, owner, tool, toolchain, msbuild, _, rows = self.evaluation_capture_fixture()

        def capture(arguments, **options):
            self.assertEqual(arguments[:5], ["dotnet", "exec", "--fx-version", "10.0.3", str(msbuild)])
            self.assertIn("-noconsolelogger", arguments)
            self.assertEqual(options["env"], {"DOTNET_ROLL_FORWARD": "Disable"})
            self.assertEqual(options["kind"], "events")
            driver = Path(arguments[5])
            self.assertEqual(driver.stat().st_mode & 0o777, 0o400)
            task = ET.parse(driver).find("./Target/*")
            self.assertEqual(base64.b64decode(task.get("OwnedRootBase64")).decode(), str(owner.root))
            request = owner.root / task.get("RequestPath")
            self.assertEqual(evidence.file_sha256(request), task.get("RequestSha256"))
            self.assertEqual(request.stat().st_mode & 0o777, 0o400)
            value = evidence.load_json(request.read_bytes())
            self.assertEqual(value["sources"], binding.sources)
            (owner.root / value["outputPath"]).write_bytes(evidence.canonical_bytes({"Items": {"_BindingInputs": rows}}))
            return mock.Mock(exit_code=0, events=({"event": "control", "code": "None", "value": len(rows)},))

        with mock.patch.object(owner, "command", side_effect=capture):
            admitted = contributors.capture_binding_evaluation_inputs(
                binding, owner, tool, toolchain, "10.0.203", "10.0.3")
        self.assertIn("Binding.cs", admitted["sources"])
        self.assertIn("sdk/10.0.203/Sdks/Fixture.props", admitted["toolchain"])

    def test_evaluation_capture_rejects_missing_hashes_events_and_changed_inputs_after_failed_child(self):
        for defect in ("hash", "control", "request", "driver", "tool", "host", "source", "mode", "import"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=self.parent) as nested:
                original_parent = self.parent
                self.parent = Path(nested)
                try:
                    binding, owner, tool, toolchain, msbuild, props, rows = self.evaluation_capture_fixture()
                finally:
                    self.parent = original_parent

                def capture(arguments, **options):
                    driver = Path(arguments[5])
                    task = ET.parse(driver).find("./Target/*")
                    request = owner.root / task.get("RequestPath")
                    if defect in ("hash", "control", "import"):
                        if defect == "hash":
                            del rows[0]["Sha256"]
                        if defect == "import":
                            props.write_bytes(b"<Project changed='true' />")
                        value = evidence.load_json(request.read_bytes())
                        (owner.root / value["outputPath"]).write_bytes(
                            evidence.canonical_bytes({"Items": {"_BindingInputs": rows}}))
                        return mock.Mock(exit_code=0, events=() if defect == "control" else (
                            {"event": "control", "code": "None", "value": len(rows)},))
                    path = {"request": request, "driver": driver, "tool": tool, "host": msbuild,
                            "source": binding.root / "Binding.cs", "mode": binding.root / "Binding.cs"}[defect]
                    path.chmod(0o600)
                    if defect != "mode":
                        path.write_bytes(b"changed")
                    raise evidence.ConformanceError("CommandFailed")

                code = {"hash": "EvidenceIncomplete", "control": "ProofMismatch"}.get(defect, "InputChanged")
                with mock.patch.object(owner, "command", side_effect=capture), self.assertRaisesRegex(
                        evidence.ConformanceError, "^" + code + "$"):
                    contributors.capture_binding_evaluation_inputs(
                        binding, owner, tool, toolchain, "10.0.203", "10.0.3")

    def test_evaluation_capture_rejects_foreign_tool_and_overlapping_toolchain_before_execution(self):
        binding, owner, tool, toolchain, _, _, _ = self.evaluation_capture_fixture()
        for actual_tool, actual_toolchain in ((self.parent / "foreign.dll", toolchain), (tool, owner.root)):
            with self.subTest(foreign=actual_tool != tool), mock.patch.object(owner, "command") as command, \
                    self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                contributors.capture_binding_evaluation_inputs(
                    binding, owner, actual_tool, actual_toolchain, "10.0.203", "10.0.3")
            command.assert_not_called()

    def documents_capture_fixture(self):
        binding, owner, _ = self.build_fixture()
        workspace = owner.root / "binding-build" / hashlib.sha256(binding.project.encode()).hexdigest()
        output = workspace / "bin/Release/net10.0"
        output.mkdir(parents=True)
        generated = workspace / "obj/Generated.cs"
        generated.parent.mkdir()
        generated.write_bytes(b"namespace Acme; public class Generated { }\n")
        for suffix in (".dll", ".pdb"):
            (output / ("Acme.Adapter" + suffix)).write_bytes(("modeled" + suffix).encode("ascii"))
        tool = owner.root / "documents-tool.dll"
        tool.write_bytes(b"modeled producer")
        built = {"bindingInputsSha256": binding.inputs_sha256,
                 "projects": {binding.project: {"root": workspace}}}
        compilation = {"schemaVersion": 1, "qualification": False, "succeeded": True,
                       "compilations": [{"project": binding.project, "succeeded": True, "sources": {
                           "source/Binding.cs": binding.sources["Binding.cs"],
                           "generated/" + generated.relative_to(owner.root / "binding-build").as_posix():
                               evidence.file_sha256(generated)}}]}
        return binding, owner, built, tool, compilation, output, generated

    def test_documents_capture_binds_compiler_sources_owned_images_and_exact_runtime(self):
        binding, owner, built, tool, compilation, output, _ = self.documents_capture_fixture()

        def capture(arguments, **options):
            self.assertEqual(arguments[:6], ["dotnet", "exec", "--fx-version", "10.0.3", str(tool), "pdb-documents"])
            self.assertEqual(options["kind"], "events")
            self.assertEqual(options["env"], {"DOTNET_ROLL_FORWARD": "Disable"})
            request = owner.root / arguments[-2]
            self.assertEqual(evidence.file_sha256(request), arguments[-1])
            self.assertEqual(request.stat().st_mode & 0o777, 0o400)
            value = evidence.load_json(request.read_bytes())
            self.assertEqual(value["sourcePath"], "binding-source")
            self.assertEqual(value["generatedPath"], "binding-build")
            self.assertEqual(value["outputRoot"], output.relative_to(owner.root).as_posix())
            receipt = {"schemaVersion": 1, "qualification": False, "project": binding.project,
                       "assembly": value["assembly"], "pdb": value["pdb"],
                       "documents": compilation["compilations"][0]["sources"]}
            (owner.root / value["outputPath"]).write_bytes(evidence.canonical_bytes(receipt))
            return mock.Mock(exit_code=0, events=({"event": "control", "code": "None", "value": 2},))

        with mock.patch.object(owner, "command", side_effect=capture):
            receipts = contributors.capture_binding_compilation_documents(
                binding, owner, built, tool, "10.0.3", evidence.canonical_bytes(compilation),
                {binding.project: "Acme.Adapter.dll"})
        self.assertEqual(set(receipts), {binding.project})
        self.assertEqual(receipts[binding.project]["documents"], compilation["compilations"][0]["sources"])

    def test_documents_capture_rechecks_inputs_even_after_failed_child_and_rejects_missing_events(self):
        for defect in ("control", "request", "tool", "source", "mode", "generated", "image", "symbols"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=self.parent) as nested:
                original_parent = self.parent
                self.parent = Path(nested)
                try:
                    binding, owner, built, tool, compilation, output, generated = self.documents_capture_fixture()
                finally:
                    self.parent = original_parent

                def capture(arguments, **options):
                    request = owner.root / arguments[-2]
                    if defect == "control":
                        value = evidence.load_json(request.read_bytes())
                        receipt = {"schemaVersion": 1, "qualification": False, "project": binding.project,
                                   "assembly": value["assembly"], "pdb": value["pdb"],
                                   "documents": compilation["compilations"][0]["sources"]}
                        (owner.root / value["outputPath"]).write_bytes(evidence.canonical_bytes(receipt))
                        return mock.Mock(exit_code=0, events=())
                    path = {"request": request, "tool": tool, "source": binding.root / "Binding.cs",
                            "mode": binding.root / "Binding.cs", "generated": generated,
                            "image": output / "Acme.Adapter.dll", "symbols": output / "Acme.Adapter.pdb"}[defect]
                    path.chmod(0o600)
                    if defect != "mode":
                        path.write_bytes(b"changed")
                    raise evidence.ConformanceError("CommandFailed")

                with mock.patch.object(owner, "command", side_effect=capture), self.assertRaisesRegex(
                        evidence.ConformanceError, "^" + ("ProofMismatch" if defect == "control" else "InputChanged") + "$"):
                    contributors.capture_binding_compilation_documents(
                        binding, owner, built, tool, "10.0.3", evidence.canonical_bytes(compilation),
                        {binding.project: "Acme.Adapter.dll"})

    def test_documents_capture_rejects_missing_projects_and_foreign_workspace_or_images_before_execution(self):
        for defect in ("projects", "workspace", "image"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=self.parent) as nested:
                original_parent = self.parent
                self.parent = Path(nested)
                try:
                    binding, owner, built, tool, compilation, output, _ = self.documents_capture_fixture()
                finally:
                    self.parent = original_parent
                assemblies = {binding.project: "Acme.Adapter.dll"}
                if defect == "projects":
                    assemblies = {}
                elif defect == "workspace":
                    built["projects"][binding.project]["root"] = self.parent
                else:
                    assemblies[binding.project] = "../Acme.Adapter.dll"
                with mock.patch.object(owner, "command") as command, self.assertRaises(evidence.ConformanceError):
                    contributors.capture_binding_compilation_documents(
                        binding, owner, built, tool, "10.0.3", evidence.canonical_bytes(compilation), assemblies)
                command.assert_not_called()

    def test_registered_runtime_components_preserve_distinct_actual_archive_owners_and_image_names(self):
        feed, output = self.parent / "feed", self.parent / "consumer"
        feed.mkdir()
        output.mkdir()

        def package(name, assembly):
            image = (name + ":" + assembly).encode("ascii")
            with zipfile.ZipFile(feed / f"{name}.0.1.0.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                archive.writestr(f"lib/net10.0/{assembly}.dll", image)
            (output / f"{assembly}.dll").write_bytes(image)
            return evidence.package_identity(feed, name, "0.1.0")

        adapter = package("Acme.Adapter", "Acme.Adapter")
        provider = package("Acme.Provider", "Acme.Engine")
        controls = package("Acme.Helpers", "Acme.Control")
        packages = [adapter, provider, controls]
        self.registration["components"]["schema"] = {
            "packageId": "acme.provider", "version": "0.1.0", "assemblyName": "Acme.Engine"}
        for role in ("authority", "faults"):
            self.registration["components"][role] = {
                "packageId": "Acme.Helpers", "version": "0.1.0", "assemblyName": "Acme.Control"}
        self.write(self.registration)
        project = contributors.admit_binding_project(self.project, "metadata")

        def images():
            return evidence.input_manifest(self.parent, [
                f"consumer/{name}.dll" for name in ("Acme.Adapter", "Acme.Engine", "Acme.Control")])

        components = contributors.binding_runtime_components(project, packages, images(), "consumer")
        self.assertEqual(components["factory"], ("consumer/Acme.Adapter.dll", "Acme.Adapter"))
        self.assertEqual(components["store"], components["factory"])
        self.assertEqual(components["schema"], ("consumer/Acme.Engine.dll", "Acme.Provider"))
        self.assertEqual(components["faults"], ("consumer/Acme.Control.dll", "Acme.Helpers"))
        self.assertEqual(components["authority"], components["faults"])
        for defect, changed in (
                ("missing-provider", [adapter, controls]),
                ("missing-helper", [adapter, provider]),
                ("wrong-helper-version", [adapter, provider, {**controls, "version": "0.2.0"}]),
                ("wrong-helper-member", [adapter, provider, {
                    **controls, "runtimeAssemblies": {"lib/net10.0/Other.dll": next(iter(
                        controls["runtimeAssemblies"].values()))}}]),
                ("duplicate-casefolded-owner", [*packages, {**controls, "packageId": "acme.helpers"}])):
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^BindingInvalid$"):
                contributors.binding_runtime_components(project, changed, images(), "consumer")
        (output / "Acme.Control.dll").write_bytes(b"changed runtime image")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_runtime_components(project, packages, images(), "consumer")

        self.registration["declaration"].update({
            "category": "artifacts",
            "capabilities": ["artifacts", "non-durable-simulation", "enumeration-incomplete"],
            "faults": sorted(evidence._BINDING_REQUIRED_FAULTS["artifacts"])})
        del self.registration["components"]["schema"]
        for role in ("validator", "maintenance", "lifetime"):
            self.registration["components"][role] = {
                "packageId": "Acme.Provider", "version": "0.1.0", "assemblyName": "Acme.Engine"}
        self.write(self.registration)
        artifact = contributors.admit_binding_project(self.project, "artifacts")
        (output / "Acme.Control.dll").write_bytes(b"Acme.Helpers:Acme.Control")
        components = contributors.binding_runtime_components(artifact, packages, images(), "consumer")
        self.assertEqual(components["validator"], ("consumer/Acme.Engine.dll", "Acme.Provider"))
        self.assertEqual(components["maintenance"], components["validator"])
        self.assertEqual(components["lifetime"], components["validator"])
        self.assertEqual(components["faults"], ("consumer/Acme.Control.dll", "Acme.Helpers"))

    def test_registered_components_reject_conflicting_runtime_asset_owners_even_with_identical_bytes(self):
        feed = self.parent / "feed"
        feed.mkdir()
        packages = []
        for name in ("Acme.Adapter", "Acme.Provider"):
            with zipfile.ZipFile(feed / f"{name}.0.1.0.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>0.1.0</version></metadata></package>")
                archive.writestr("lib/net10.0/Acme.Adapter.dll", b"identical but ambiguously owned")
            packages.append(evidence.package_identity(feed, name, "0.1.0"))
        self.registration["components"]["schema"]["packageId"] = "Acme.Provider"
        self.write(self.registration)
        project = contributors.admit_binding_project(self.project, "metadata")
        images = {"consumer/Acme.Adapter.dll": hashlib.sha256(b"identical but ambiguously owned").hexdigest()}
        with self.assertRaisesRegex(evidence.ConformanceError, "^BindingInvalid$"):
            contributors.binding_runtime_components(project, packages, images, "consumer")

    def test_explicit_archive_lock_policy_preserves_versions_graph_and_unselected_dependencies(self):
        import conformance_lock_preparation as preparation
        feed = self.parent / "feed"
        feed.mkdir()
        packages = []
        for name, version in (("Acme.Adapter", "1.2.3-preview.1"), ("Acme.Provider", "4.2.1")):
            with zipfile.ZipFile(feed / f"{name}.{version}.nupkg", "w") as archive:
                archive.writestr(f"{name}.nuspec",
                                f"<package><metadata><id>{name}</id><version>{version}</version></metadata></package>")
                archive.writestr(f"lib/net10.0/{name}.dll", (name + version).encode("ascii"))
            packages.append(evidence.package_identity(feed, name, version))
        dependencies = {
            "acme.adapter": {
                "type": "Direct", "requested": "[1.2.3-preview.1, 1.2.3-preview.1]",
                "resolved": "1.2.3-preview.1", "contentHash": "old-adapter",
                "dependencies": {"Acme.Provider": "4.2.1", "External.Other": "7.0.0"}},
            "Acme.Provider": {"type": "Transitive", "resolved": "4.2.1", "contentHash": "old-provider"},
            "External.Other": {"type": "Transitive", "resolved": "7.0.0", "contentHash": "unselected"}}
        original = {"version": 2, "dependencies": {
            "net10.0": dependencies, "net10.0/linux-x64": copy.deepcopy(dependencies)}}
        before = evidence.canonical_bytes(original)
        source = self.parent / "candidate"
        source.mkdir()
        project = source / "Consumer.csproj"
        project.write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        lock = source / "packages.lock.json"
        lock.write_bytes(before)
        alternate, record = preparation.prepare_project_lock(
            project, source, feed, "candidate", local_packages=packages)
        self.assertEqual(lock.read_bytes(), before)
        prepared = evidence.load_json(alternate.read_bytes())
        expected = copy.deepcopy(original)
        for framework in expected["dependencies"].values():
            for package in packages:
                name = "acme.adapter" if package["packageId"] == "Acme.Adapter" else "Acme.Provider"
                framework[name]["contentHash"] = base64.b64encode(
                    bytes.fromhex(package["nugetSha512"])).decode("ascii")
        self.assertEqual(prepared, expected)
        self.assertFalse(record["qualification"])
        preparation.verify_project_lock(record, source, feed, local_packages=packages)
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            preparation.verify_project_lock(record, source, feed)
        for defect in ("duplicate", "version", "archive-hash", "nuget-hash"):
            changed = list(packages)
            if defect == "duplicate":
                changed.append({**packages[0], "packageId": "acme.adapter"})
            else:
                field, value = {
                    "version": ("version", "1.2.4"),
                    "archive-hash": ("sha256", "a" * 64),
                    "nuget-hash": ("nugetSha512", "b" * 128)}[defect]
                changed[0] = {**packages[0], field: value}
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^InputChanged$"):
                preparation.rebind_local_archives(before, feed, local_packages=changed)
        for defect in ("duplicate-node", "missing-hash", "resolved-version"):
            changed = copy.deepcopy(original)
            framework = changed["dependencies"]["net10.0"]
            if defect == "duplicate-node":
                framework["Acme.Adapter"] = copy.deepcopy(framework["acme.adapter"])
            elif defect == "missing-hash":
                del framework["acme.adapter"]["contentHash"]
            else:
                framework["acme.adapter"]["resolved"] = "1.2.4"
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^InputChanged$"):
                preparation.rebind_local_archives(
                    evidence.canonical_bytes(changed), feed, local_packages=packages)
        archive = feed / "Acme.Provider.4.2.1.nupkg"
        archive.write_bytes(archive.read_bytes() + b"changed after capture")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            preparation.verify_project_lock(record, source, feed, local_packages=packages)

    def test_evaluated_inputs_require_declared_source_closure_and_hash_actual_toolchain_bytes(self):
        binding = contributors.admit_binding_project(self.project, "metadata")
        toolchain = self.parent / "toolchain"
        toolchain.mkdir()
        (toolchain / "Sdk.props").write_text("<Project />\n")
        rows = [{"Identity": "source/" + path, "Kind": "source"} for path in binding.sources]
        rows.append({"Identity": "toolchain/Sdk.props", "Kind": "toolchain",
                     "FullPath": str(self.parent / "discarded-private-vendor-metadata")})

        def capture(items):
            return contributors.binding_evaluation_inputs(
                binding, evidence.canonical_bytes({"Items": {"_BindingInputs": items}}), toolchain)

        captured = capture(rows)
        self.assertFalse(captured["qualification"])
        self.assertEqual(captured["sources"], binding.sources)
        self.assertEqual(captured["toolchain"], {"Sdk.props": evidence.file_sha256(toolchain / "Sdk.props")})
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(captured))
        missing_project = [row for row in rows if row["Identity"] != "source/Adapter.csproj"]
        missing_toolchain = [row for row in rows if row["Kind"] != "toolchain"]
        (self.source / "Ambient.cs").write_text("public class Ambient { }\n")
        for defect, changed in (
                ("undeclared-ambient-source", [*rows, {"Identity": "source/Ambient.cs", "Kind": "source"}]),
                ("missing-project", missing_project), ("missing-toolchain", missing_toolchain)):
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceIncomplete$"):
                capture(changed)
        for defect, changed in (
                ("duplicate", [*rows, rows[0]]),
                ("unknown-metadata", [{**rows[0], "providerMessage": "must not disappear"}, *rows[1:]]),
                ("wrong-kind", [{**rows[0], "Kind": "package"}, *rows[1:]]),
                ("prefix-mismatch", [{**rows[0], "Kind": "toolchain"}, *rows[1:]]),
                ("escaping-source", [{"Identity": "source/../outside", "Kind": "source"}, *rows[1:]])):
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                capture(changed)
        original = (self.source / "Binding.cs").read_bytes()
        (self.source / "Binding.cs").write_text("public class Changed { }\n")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            capture(rows)
        (self.source / "Binding.cs").write_bytes(original)
        self.sidecar.write_bytes(self.sidecar.read_bytes() + b"\n")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            capture([row for row in rows if row["Identity"] != "source/Adapter.conformance.json"])

    def compilation(self):
        self.generated = self.parent / "generated"
        self.generated.mkdir()
        (self.generated / "Dynamic.cs").write_text("public class Dynamic { }\n")
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        return {
            "schemaVersion": 1, "qualification": False, "succeeded": True,
            "compilations": [{
                "project": "Adapter.csproj", "succeeded": True,
                "sources": {"source/Binding.cs": self.binding.sources["Binding.cs"],
                            "generated/Dynamic.cs": evidence.file_sha256(self.generated / "Dynamic.cs")}}]}

    def compile_inputs(self, value):
        data = value if isinstance(value, bytes) else evidence.canonical_bytes(value)
        return contributors.binding_compilation_sources(self.binding, data, self.generated)

    def test_compiler_sources_bind_each_actual_project_to_frozen_and_generated_source_hashes(self):
        value = self.compilation()
        (self.source / "Helper.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        self.registration["sourceFiles"].append("Helper.csproj")
        self.write(self.registration)
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        value["compilations"].append({
            "project": "Helper.csproj", "succeeded": True,
            "sources": {"source/Binding.cs": self.binding.sources["Binding.cs"]}})
        result = self.compile_inputs(value)
        self.assertEqual(result["compilations"], tuple(value["compilations"]))
        self.assertEqual(result["bindingInputsSha256"], self.binding.inputs_sha256)
        self.assertFalse(result["qualification"])
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))

    def test_compiler_sources_reject_failed_missing_duplicate_or_undeclared_projects(self):
        value = self.compilation()
        (self.source / "Other.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        self.registration["sourceFiles"].append("Other.csproj")
        self.write(self.registration)
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        for defect in ("build-failed", "compiler-failed", "missing-selected-project", "duplicate-project",
                       "undeclared-project", "not-a-project", "undeclared-source"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "build-failed":
                changed["succeeded"] = False
            elif defect == "compiler-failed":
                row["succeeded"] = False
            elif defect == "duplicate-project":
                changed["compilations"].append(copy.deepcopy(row))
            elif defect == "undeclared-source":
                row["sources"]["source/Ambient.cs"] = "a" * 64
            else:
                row["project"] = {
                    "missing-selected-project": "Other.csproj", "undeclared-project": "Unknown.csproj",
                    "not-a-project": "Binding.cs"}[defect]
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceIncomplete$"):
                self.compile_inputs(changed)

    def test_compiler_sources_reject_changed_generated_queried_and_unqueried_frozen_bytes(self):
        value = self.compilation()
        for path in (self.generated / "Dynamic.cs", self.source / "Binding.cs", self.sidecar):
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            with self.subTest(path=path.name), self.assertRaisesRegex(
                    evidence.ConformanceError, "^InputChanged$"):
                self.compile_inputs(value)
            path.write_bytes(original)
        changed = copy.deepcopy(value)
        changed["compilations"].append({
            "project": "Helper.csproj", "succeeded": True,
            "sources": {"generated/Dynamic.cs": "a" * 64}})
        (self.source / "Helper.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk" />\n')
        self.registration["sourceFiles"].append("Helper.csproj")
        self.write(self.registration)
        self.binding = contributors.admit_binding_project(self.project, "metadata")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.compile_inputs(changed)

    def test_compiler_sources_reject_open_schemas_unsafe_paths_and_unbounded_receipts(self):
        value = self.compilation()
        for defect in ("unknown-top", "unknown-row", "empty-rows", "empty-sources", "numeric-success",
                       "qualification", "namespace", "escape", "absolute", "hash"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "unknown-top":
                changed["message"] = "must not disappear"
            elif defect == "unknown-row":
                row["commandLine"] = "must not persist"
            elif defect == "empty-rows":
                changed["compilations"] = []
            elif defect == "empty-sources":
                row["sources"] = {}
            elif defect == "numeric-success":
                row["succeeded"] = 1
            elif defect == "qualification":
                changed["qualification"] = True
            elif defect == "hash":
                row["sources"]["source/Binding.cs"] = "invalid"
            else:
                path = {"namespace": "package/Other.cs", "escape": "generated/../outside.cs",
                        "absolute": "/private/outside.cs"}[defect]
                row["sources"][path] = "a" * 64
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                self.compile_inputs(changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            self.compile_inputs(b"x" * (2 * 1024 * 1024 + 1))
        raw = evidence.canonical_bytes(value).replace(b'"schemaVersion":1', b'"schemaVersion":1,"schemaVersion":1')
        with self.assertRaises(evidence.ConformanceError):
            self.compile_inputs(raw)

    def test_compiler_sources_reject_overlapping_generated_roots_and_linked_generated_inputs(self):
        value = self.compilation()
        for generated in (self.source, self.source / "obj", self.parent):
            with self.subTest(root=generated.name), self.assertRaisesRegex(
                    evidence.ConformanceError, "^OwnershipInvalid$"):
                contributors.binding_compilation_sources(
                    self.binding, evidence.canonical_bytes(value), generated)
        outside = self.parent / "outside.cs"
        outside.write_bytes((self.generated / "Dynamic.cs").read_bytes())
        (self.generated / "Dynamic.cs").unlink()
        (self.generated / "Dynamic.cs").symlink_to(outside)
        with self.assertRaises(evidence.ConformanceError):
            self.compile_inputs(value)
        self.assertEqual(outside.read_text(), "public class Dynamic { }\n")

    def documents(self):
        compilation = self.compile_inputs(self.compilation())["compilations"][0]
        self.output = self.parent / "output"
        self.output.mkdir()
        (self.output / "Adapter.dll").write_bytes(b"modeled compiler image")
        (self.output / "Adapter.pdb").write_bytes(b"modeled portable symbols")
        value = {
            "schemaVersion": 1, "qualification": False, "project": "Adapter.csproj",
            "assembly": {"path": "Adapter.dll", "sha256": evidence.file_sha256(self.output / "Adapter.dll")},
            "pdb": {"path": "Adapter.pdb", "sha256": evidence.file_sha256(self.output / "Adapter.pdb")},
            "documents": dict(compilation["sources"])}
        return compilation, value

    def document_inputs(self, compilation, value):
        return contributors.binding_compilation_documents(
            compilation, evidence.canonical_bytes(value), self.output, "Adapter.dll")

    def test_compiler_document_receipts_match_observed_source_subset_and_current_output_bytes(self):
        compilation, value = self.documents()
        del value["documents"]["generated/Dynamic.cs"]
        result = self.document_inputs(compilation, value)
        self.assertEqual(result["documents"], value["documents"])
        self.assertEqual(result["compilerSourcesSha256"], evidence.digest(compilation["sources"]))
        self.assertEqual(result["assembly"], value["assembly"])
        self.assertEqual(result["pdb"], value["pdb"])
        self.assertFalse(result["qualification"])
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))

    def test_compiler_documents_reject_foreign_project_source_hash_or_output_selection(self):
        compilation, value = self.documents()
        for defect in ("project", "document", "hash", "assembly", "pdb"):
            changed = copy.deepcopy(value)
            if defect == "project":
                changed["project"] = "Other.csproj"
            elif defect == "document":
                changed["documents"]["generated/Unobserved.cs"] = "a" * 64
            elif defect == "hash":
                changed["documents"]["source/Binding.cs"] = "a" * 64
            else:
                changed[defect]["path"] = "Other." + ("dll" if defect == "assembly" else "pdb")
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^ProofMismatch$"):
                self.document_inputs(compilation, changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            self.document_inputs({**compilation, "succeeded": False}, value)

    def test_compiler_documents_reject_output_byte_changes_and_linked_symbols(self):
        compilation, value = self.documents()
        for name in ("Adapter.dll", "Adapter.pdb"):
            path = self.output / name
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(name=name), self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                self.document_inputs(compilation, value)
            path.write_bytes(original)
        outside = self.parent / "outside.pdb"
        original = (self.output / "Adapter.pdb").read_bytes()
        outside.write_bytes(original)
        (self.output / "Adapter.pdb").unlink()
        (self.output / "Adapter.pdb").symlink_to(outside)
        with self.assertRaises(evidence.ConformanceError):
            self.document_inputs(compilation, value)
        self.assertEqual(outside.read_bytes(), original)

    def test_compiler_documents_reject_open_schemas_unsafe_paths_and_empty_document_sets(self):
        compilation, value = self.documents()
        for defect in ("field", "nested-field", "absolute", "escape", "qualification", "documents"):
            changed = copy.deepcopy(value)
            if defect == "field":
                changed["message"] = "must not disappear"
            elif defect == "nested-field":
                changed["assembly"]["message"] = "must not disappear"
            elif defect == "qualification":
                changed["qualification"] = True
            elif defect == "documents":
                changed["documents"] = {}
            else:
                changed["pdb"]["path"] = "/private/Adapter.pdb" if defect == "absolute" else "../Adapter.pdb"
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                self.document_inputs(compilation, changed)
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            contributors.binding_compilation_documents(
                compilation, b"x" * (2 * 1024 * 1024 + 1), self.output, "Adapter.dll")

    def build_files(self):
        compilation = self.compile_inputs(self.compilation())["compilations"][0]
        self.toolchain, self.package_root = self.parent / "toolchain", self.parent / "packages"
        self.toolchain.mkdir()
        self.package_root.mkdir()
        for root, name, data in (
                (self.toolchain, "Reference.dll", b"fixed reference image"),
                (self.toolchain, "Analyzer.dll", b"fixed analyzer image"),
                (self.toolchain, "Sdk.props", b"<Project />"),
                (self.package_root, "acme.library/2.0.0/lib/net10.0/Library.dll", b"fixed package image")):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.package_inputs = evidence.input_manifest(
            self.package_root, ["acme.library/2.0.0/lib/net10.0/Library.dll"])
        return {
            "schemaVersion": 1, "qualification": False, "succeeded": True,
            "diagnosticCodes": [], "observerErrors": [],
            "imports": {"source/Adapter.csproj": self.binding.sources["Adapter.csproj"],
                        "toolchain/Sdk.props": evidence.file_sha256(self.toolchain / "Sdk.props")},
            "compilations": [{
                "project": "Adapter.csproj", "succeeded": True, "inputs": {
                    "Sources": dict(compilation["sources"]),
                    "References": {
                        "toolchain/Reference.dll": evidence.file_sha256(self.toolchain / "Reference.dll"),
                        **{"packages/" + path: hashed for path, hashed in self.package_inputs.items()}},
                    "Analyzers": {"toolchain/Analyzer.dll": evidence.file_sha256(self.toolchain / "Analyzer.dll")},
                    "AdditionalFiles": {}, "Resources": {}}}]}

    def build_file_inputs(self, value):
        return contributors.binding_build_file_inputs(
            self.binding, evidence.canonical_bytes(value), self.generated, self.toolchain,
            self.package_root, self.package_inputs)

    def test_build_file_receipts_rehash_imports_compiler_inputs_and_frozen_package_policy(self):
        value = self.build_files()
        result = self.build_file_inputs(value)
        self.assertEqual(result["imports"], value["imports"])
        self.assertEqual(result["compilations"], tuple(value["compilations"]))
        self.assertEqual(result["bindingInputsSha256"], self.binding.inputs_sha256)
        self.assertEqual(result["packageInputsSha256"], evidence.digest(self.package_inputs))
        self.assertFalse(result["qualification"])
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))

    def test_build_file_receipts_reject_missing_closure_failed_observation_and_unknown_parameters(self):
        value = self.build_files()
        for defect in ("diagnostics", "observer", "build-failed", "compiler-failed", "project", "duplicate-project",
                       "missing-sources", "empty-references", "unknown-parameter", "unknown-field",
                       "namespace", "undeclared-source", "package-policy", "empty-imports"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            expected = "EvidenceIncomplete"
            if defect in ("diagnostics", "observer"):
                changed["diagnosticCodes" if defect == "diagnostics" else "observerErrors"] = ["MSB4017"]
            elif defect == "build-failed":
                changed["succeeded"] = False
            elif defect == "compiler-failed":
                row["succeeded"] = False
            elif defect == "project":
                row["project"] = "Foreign.csproj"
            elif defect == "duplicate-project":
                changed["compilations"].append(copy.deepcopy(row))
            elif defect == "missing-sources":
                del row["inputs"]["Sources"]
                expected = "EvidenceSchemaInvalid"
            elif defect == "empty-references":
                row["inputs"]["References"] = {}
            elif defect == "unknown-parameter":
                row["inputs"]["UnobservedFiles"] = {}
                expected = "EvidenceSchemaInvalid"
            elif defect == "unknown-field":
                changed["message"] = "must not disappear"
                expected = "EvidenceSchemaInvalid"
            elif defect in ("namespace", "undeclared-source", "package-policy"):
                path = {"namespace": "external/Other.dll", "undeclared-source": "source/Ambient.cs",
                        "package-policy": "packages/foreign/1.0.0/Other.dll"}[defect]
                row["inputs"]["References"][path] = "a" * 64
                if defect == "namespace":
                    expected = "EvidenceSchemaInvalid"
            else:
                changed["imports"] = {}
                expected = "EvidenceSchemaInvalid"
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^" + expected + "$"):
                self.build_file_inputs(changed)

    def test_build_file_receipts_reject_changed_bytes_conflicting_hashes_and_package_policy_substitution(self):
        value = self.build_files()
        for path in (self.sidecar, self.generated / "Dynamic.cs", self.toolchain / "Reference.dll",
                     self.toolchain / "Analyzer.dll", self.toolchain / "Sdk.props",
                     self.package_root / "acme.library/2.0.0/lib/net10.0/Library.dll"):
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(path=path.name), self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                self.build_file_inputs(value)
            path.write_bytes(original)
        changed = copy.deepcopy(value)
        changed["imports"]["toolchain/Reference.dll"] = "a" * 64
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.build_file_inputs(changed)
        self.package_inputs = {path: "a" * 64 for path in self.package_inputs}
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.build_file_inputs(value)

    def test_build_file_receipts_reject_root_overlap_linked_inputs_and_aggregate_read_limit(self):
        value = self.build_files()
        with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
            contributors.binding_build_file_inputs(
                self.binding, evidence.canonical_bytes(value), self.generated, self.generated,
                self.package_root, self.package_inputs)
        outside = self.parent / "outside.dll"
        original = (self.toolchain / "Analyzer.dll").read_bytes()
        outside.write_bytes(original)
        (self.toolchain / "Analyzer.dll").unlink()
        (self.toolchain / "Analyzer.dll").symlink_to(outside)
        with self.assertRaises(evidence.ConformanceError):
            self.build_file_inputs(value)
        self.assertEqual(outside.read_bytes(), original)
        (self.toolchain / "Analyzer.dll").unlink()
        (self.toolchain / "Analyzer.dll").write_bytes(original)
        declared_bytes = sum((self.source / path).stat().st_size for path in self.binding.sources)
        with mock.patch.object(evidence, "MAX_PROOF_BYTES", declared_bytes):
            with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
                self.build_file_inputs(value)

    def package_file_selection(self):
        self.feed = self.parent / "feed"
        self.feed.mkdir()
        self.archive = self.feed / "Acme.Dependency.2.4.0-preview.1.nupkg"
        self.package_files = {
            "lib/net10.0/Acme.Dependency.dll": b"fixed runtime image",
            "ref/net10.0/Acme.Dependency.dll": b"fixed reference image",
            "build/Acme.Dependency.props": b"<Project />",
            "analyzers/dotnet/cs/Generator.dll": b"fixed analyzer image",
            "contentFiles/any/any/Additional.txt": b"private-resource-canary"}
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("Acme.Dependency.nuspec", (
                "<package><metadata><id>Acme.Dependency</id><version>2.4.0-preview.1</version></metadata></package>"))
            for name, data in self.package_files.items():
                archive.writestr(name, data)
        package = evidence.package_identity(self.feed, "Acme.Dependency", "2.4.0-preview.1")
        selection = {
            "packageId": "acme.dependency", "version": "2.4.0-preview.1",
            "cachePath": "acme.dependency/2.4.0-preview.1",
            "members": sorted(self.package_files)}
        return package, selection

    def test_registered_package_file_policy_binds_exact_nonruntime_archive_members_without_extracting(self):
        package, selection = self.package_file_selection()
        policy = contributors.binding_package_file_policy(self.feed, [package], [selection])
        self.assertEqual(policy, {
            selection["cachePath"] + "/" + name: hashlib.sha256(data).hexdigest()
            for name, data in self.package_files.items()})
        self.assertNotIn(b"private-resource-canary", evidence.canonical_bytes(policy))
        self.assertEqual(set(self.feed.iterdir()), {self.archive})
        self.assertEqual(contributors.binding_package_file_policy(self.feed, [], []), {})

    def test_registered_package_file_policy_rejects_missing_foreign_duplicate_or_ambiguous_selections(self):
        package, selection = self.package_file_selection()
        for defect in ("package", "version", "cache-owner", "cache-path", "cache-escape", "missing-member",
                       "member-escape", "duplicate-member", "duplicate-cache", "duplicate-package"):
            changed, packages = copy.deepcopy(selection), [package]
            expected = "BindingInvalid"
            if defect == "package":
                changed["packageId"] = "Foreign.Dependency"
            elif defect == "version":
                changed["version"] = "2.4.1"
            elif defect == "cache-owner":
                changed["cachePath"] = "other.dependency/2.4.0-preview.1"
            elif defect == "cache-path":
                changed["cachePath"] += "/nested"
            elif defect == "cache-escape":
                changed["cachePath"] = "../outside"
                expected = "EvidenceSchemaInvalid"
            elif defect == "missing-member":
                changed["members"].append("build/Absent.props")
                expected = "InputChanged"
            elif defect == "member-escape":
                changed["members"].append("../outside.props")
                expected = "EvidenceSchemaInvalid"
            elif defect == "duplicate-member":
                changed["members"].append(changed["members"][0])
                expected = "EvidenceSchemaInvalid"
            elif defect == "duplicate-package":
                packages.append({**package, "packageId": "acme.dependency"})
            selected = [changed, copy.deepcopy(changed)] if defect == "duplicate-cache" else [changed]
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^" + expected + "$"):
                contributors.binding_package_file_policy(self.feed, packages, selected)

    def test_registered_package_file_policy_rejects_changed_archive_bytes_and_hashes(self):
        package, selection = self.package_file_selection()
        for field in ("sha256", "nugetSha512"):
            changed = {**package, field: "a" * (64 if field == "sha256" else 128)}
            with self.subTest(field=field), self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                contributors.binding_package_file_policy(self.feed, [changed], [selection])
        self.archive.write_bytes(self.archive.read_bytes() + b"changed")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_package_file_policy(self.feed, [package], [selection])

    def test_registered_package_file_policy_checks_selected_nondll_crc_and_aggregate_byte_budget(self):
        package, selection = self.package_file_selection()
        with mock.patch.object(evidence, "MAX_PROOF_BYTES", self.archive.stat().st_size):
            with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
                contributors.binding_package_file_policy(self.feed, [package], [selection])
        with zipfile.ZipFile(self.archive) as archive:
            info = archive.getinfo("build/Acme.Dependency.props")
            offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
        raw = bytearray(self.archive.read_bytes())
        raw[offset] ^= 1
        self.archive.write_bytes(raw)
        corrupted = evidence.package_identity(self.feed, "Acme.Dependency", "2.4.0-preview.1")
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_package_file_policy(self.feed, [corrupted], [selection])

    def test_build_only_archive_identity_does_not_weaken_runtime_package_admission(self):
        feed = self.parent / "feed"
        feed.mkdir()
        archive = feed / "Acme.BuildInputs.3.2.1.nupkg"
        with zipfile.ZipFile(archive, "w") as packed:
            packed.writestr("Acme.BuildInputs.nuspec",
                            "<package><metadata><id>Acme.BuildInputs</id><version>3.2.1</version></metadata></package>")
            packed.writestr("build/Acme.BuildInputs.props", "<Project />")
        captured = evidence.package_archive_identity(feed, "Acme.BuildInputs", "3.2.1")
        self.assertEqual(set(captured), {"packageId", "version", "sha256", "nugetSha512", "sourceMapping"})
        self.assertEqual(captured["sha256"], evidence.file_sha256(archive))
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            evidence.package_identity(feed, "Acme.BuildInputs", "3.2.1")
        selection = {
            "packageId": "Acme.BuildInputs", "version": "3.2.1", "cachePath": "acme.buildinputs/3.2.1",
            "members": ["build/Acme.BuildInputs.props"]}
        policy = contributors.binding_package_file_policy(feed, [captured], [selection])
        self.assertEqual(policy, {
            "acme.buildinputs/3.2.1/build/Acme.BuildInputs.props": hashlib.sha256(b"<Project />").hexdigest()})
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
            contributors.binding_package_file_policy(feed, [{**captured, "message": "must not disappear"}], [selection])
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            contributors.binding_package_file_policy(feed, [{**captured, "sha256": "a" * 64}], [selection])

    def compiler_parameters(self):
        files = self.build_file_inputs(self.build_files())["compilations"]
        return files, {
            "schemaVersion": 1, "qualification": False, "compilations": [{
                "project": row["project"], "commandLineSha256": "a" * 64,
                "itemMetadata": {kind: {path: "b" * 64 for path in items}
                                 for kind, items in row["inputs"].items()}}
                for row in files]}

    def test_compiler_parameters_bind_each_project_and_metadata_key_to_actual_file_receipt(self):
        files, value = self.compiler_parameters()
        result = contributors.binding_compiler_parameter_inputs(files, evidence.canonical_bytes(value))
        self.assertEqual(result["compilations"], tuple(value["compilations"]))
        self.assertEqual(result["fileInputsSha256"], evidence.digest(files))
        self.assertNotIn(str(self.parent).encode(), evidence.canonical_bytes(result))
        self.assertFalse(result["qualification"])

    def test_compiler_parameters_reject_missing_duplicate_foreign_or_mismatched_metadata_keys(self):
        files, value = self.compiler_parameters()
        for defect in ("project", "duplicate-project", "missing-kind", "unknown-input", "missing-input"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "project":
                row["project"] = "Other.csproj"
            elif defect == "duplicate-project":
                changed["compilations"].append(copy.deepcopy(row))
            elif defect == "missing-kind":
                del row["itemMetadata"]["Analyzers"]
            elif defect == "unknown-input":
                row["itemMetadata"]["References"]["source/Other.dll"] = "c" * 64
            else:
                del row["itemMetadata"]["References"]["toolchain/Reference.dll"]
            with self.subTest(defect=defect), self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
                contributors.binding_compiler_parameter_inputs(files, evidence.canonical_bytes(changed))
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            contributors.binding_compiler_parameter_inputs(
                [{**files[0], "succeeded": False}], evidence.canonical_bytes(value))
        with self.assertRaisesRegex(evidence.ConformanceError, "^EvidenceIncomplete$"):
            contributors.binding_compiler_parameter_inputs([files[0], files[0]], evidence.canonical_bytes(value))

    def test_compiler_parameters_reject_open_schemas_malformed_hashes_and_unbounded_receipts(self):
        files, value = self.compiler_parameters()
        for defect in ("field", "row-field", "command-hash", "metadata-hash", "path", "unknown-parameter"):
            changed = copy.deepcopy(value)
            row = changed["compilations"][0]
            if defect == "field":
                changed["rawCommandLine"] = "must not disappear"
            elif defect == "row-field":
                row["message"] = "must not disappear"
            elif defect == "command-hash":
                row["commandLineSha256"] = ""
            elif defect == "metadata-hash":
                row["itemMetadata"]["Sources"]["source/Binding.cs"] = "invalid"
            elif defect == "path":
                row["project"] = "../Other.csproj"
            else:
                row["itemMetadata"]["UnknownParameter"] = {}
            with self.subTest(defect=defect), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceSchemaInvalid$"):
                contributors.binding_compiler_parameter_inputs(files, evidence.canonical_bytes(changed))
        with self.assertRaisesRegex(evidence.ConformanceError, "^OutputLimitExceeded$"):
            contributors.binding_compiler_parameter_inputs(files, b"x" * (2 * 1024 * 1024 + 1))


if __name__ == "__main__":
    unittest.main()
