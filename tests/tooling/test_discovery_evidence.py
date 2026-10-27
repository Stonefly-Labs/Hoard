import importlib.util
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("discovery_evidence", SCRIPTS / "discovery_evidence.py")


class DiscoveryEvidenceTests(unittest.TestCase):
    def load(self):
        module = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(module)
        return module

    def test_reference_consumer_reuses_actual_response_and_rejects_non_bcl_projects(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            project = root / "tests/fixtures/discovery/ReferenceConsumer/ReferenceConsumer.csproj"
            project.parent.mkdir(parents=True)
            work = root / "work"
            work.mkdir()
            image = project.parent / "bin/Release/net10.0/ReferenceConsumer.dll"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"reference-image")
            body = b'{"actual":"serialized-response"}'
            for kind in ("PackageReference", "ProjectReference", "bcl"):
                project.write_text("<Project>" + (
                    "" if kind == "bcl" else f'<ItemGroup><{kind} Include="unexpected"/></ItemGroup>') + "</Project>")
                with self.subTest(kind=kind), patch.object(module, "run", return_value='[{"Id":"fixture.protocol.one"}]') as run:
                    if kind != "bcl":
                        with self.assertRaisesRegex(RuntimeError, "BCL-only"):
                            module.reference_consumer(root, work, [base64.b64encode(body).decode()])
                        run.assert_not_called()
                    else:
                        receipt = module.reference_consumer(root, work, [base64.b64encode(body).decode()])
                        self.assertEqual(body.decode(), run.call_args.kwargs["input"])
                        self.assertEqual(hashlib.sha256(body).hexdigest(), receipt["responseSha256"])
                        self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), receipt["assemblySha256"])
                        self.assertEqual(["fixture.protocol.one"], receipt["moduleIds"])

    def test_mutation_workspace_preserves_current_project_and_contract_closure(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "source"
            work = Path(temporary).resolve() / "work"
            work.mkdir()
            files = {
                "src/Hoard.Hosting/Hosting.csproj": "<Project/>",
                "tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj":
                    '<Project><ItemGroup><ProjectReference Include="../../fixtures/conformance/Host/Host.csproj"/>'
                    '</ItemGroup></Project>',
                "tests/fixtures/conformance/Host/Host.csproj": "<Project/>",
                "tests/fixtures/discovery/ReferenceConsumer/ReferenceConsumer.csproj": "<Project/>",
                "tests/FoundationEvidence.cs": "class FoundationEvidence {}",
                "specs/004-module-discovery/contracts/openapi.json": "{}",
                "specs/007-provider-conformance/contracts/catalog.json": "{}",
                "examples/CustomHost/CustomHost.csproj": "<Project/>",
                "Directory.Build.props": "<Project/>", "Directory.Packages.props": "<Project/>",
                "global.json": "{}", "Hoard.slnx": "<Solution/>",
            }
            for name, text in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)

            def restore(*args, **kwargs):
                self.assertEqual(("dotnet", "restore"), args[:2])
                for name, text in files.items():
                    self.assertEqual(text, (work / "mutations" / name).read_text())

            with patch.object(module, "run", side_effect=restore) as run, patch.object(module, "MUTATIONS", ()):
                self.assertEqual([], module.mutations(root, work))
            run.assert_called_once()

    def test_missing_empty_duplicate_and_stale_cases_cannot_pass(self):
        module = self.load()
        for evidence in (None, [], [{"id": "D01", "passed": True, "tests": []}],
                         [{"id": "D01", "passed": True, "tests": ["test"]}] * 40):
            with self.subTest(evidence=evidence):
                with self.assertRaisesRegex(RuntimeError, "case inventory"):
                    module.verify_cases(evidence)

    def test_subprocess_failure_and_timeout_are_explicit(self):
        module = self.load()
        import subprocess
        for result in (subprocess.CompletedProcess([], 7, "invented-private-output"),
                       subprocess.TimeoutExpired("fixture", 600)):
            with self.subTest(result=type(result).__name__):
                with patch.object(module.subprocess, "run",
                                  side_effect=result if isinstance(result, Exception) else None,
                                  return_value=result):
                    with self.assertRaises(RuntimeError) as caught:
                        module.run("fixture")
                    self.assertNotIn("invented-private-output", str(caught.exception))

    def test_retained_binary_and_package_hash_drift_reject(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            binary = root / "fixture.dll"
            binary.write_bytes(b"original")
            with self.assertRaisesRegex(RuntimeError, "binary"):
                module.verify_binary(binary, "wrong")
            with self.assertRaisesRegex(RuntimeError, "package"):
                module.verify_package(binary, root / "another-feed", "wrong")

    def test_cleanup_requires_exact_owned_workspace(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            with self.assertRaisesRegex(RuntimeError, "cleanup"):
                module.cleanup_workspace(parent)
            work = module.create_workspace(parent=parent)
            module.cleanup_workspace(work)
            self.assertTrue(parent.is_dir())
            self.assertFalse(work.exists())

    def test_incomplete_performance_and_suite_evidence_reject(self):
        module = self.load()
        for evidence in ({}, {"samples": []}, {"samples": [0.1] * 99}):
            with self.assertRaisesRegex(RuntimeError, "performance"):
                module.verify_performance(evidence)
        for evidence in ([], [{"id": "inventory", "passed": True, "tests": 0}]):
            with self.assertRaisesRegex(RuntimeError, "suite inventory"):
                module.verify_suites(evidence)

    def test_case_closure_requires_each_real_mapped_scenario(self):
        module = self.load()
        entries = [{"id": case, "passed": True, "tests": [f"Hoard.Tests.Fixture.{name}" for name in names]}
                   for case, names in module.CASE_TESTS.items()]
        module.verify_cases(entries)
        for mutation in ("missing", "duplicate", "stale", "false", "wrong-scenario"):
            values = copy.deepcopy(entries)
            if mutation == "missing":
                values.pop()
            elif mutation == "duplicate":
                values[-1] = values[0]
            elif mutation == "stale":
                values[-1]["id"] = "D41"
            elif mutation == "false":
                values[-1]["passed"] = False
            else:
                values[-1]["tests"] = ["unrelated-passing-test"]
            with self.subTest(mutation=mutation), self.assertRaisesRegex(RuntimeError, "case inventory"):
                module.verify_cases(values)

    def test_suites_cannot_be_missing_empty_duplicate_or_stale(self):
        module = self.load()
        values = [{"id": suite, "passed": True, "tests": 1} for suite in module.SUITES]
        module.verify_suites(values)
        for changed in (values[:-1], values + [values[0]],
                        [{**entry, "tests": 0} for entry in values],
                        [{**entry, "id": "not-current"} for entry in values]):
            with self.assertRaisesRegex(RuntimeError, "suite inventory"):
                module.verify_suites(changed)

    def performance(self):
        return {"modules": 100, "contributionsPerModule": 10, "concurrency": 10, "completeBodies": 100,
                "samples": [0.1] * 100, "bytes": [512] * 100, "sdk": "synthetic-sdk", "os": "synthetic-os",
                "runId": "current", "resourceDeltas": {key: 0 for key in
                ("constructors", "probes", "secrets", "serviceCalls", "connections", "activeResources")}}

    def test_performance_rejects_hidden_slow_nonfinite_incomplete_and_stale_samples(self):
        module = self.load()
        module.verify_performance(self.performance(), "current")
        for field, value in (
                ("samples", [0.1] * 99), ("samples", [0.1] * 94 + [2.1] * 6),
                ("samples", [float("nan")] * 100), ("samples", [True] * 100),
                ("bytes", [0] * 100), ("bytes", [4 * 1024 * 1024 + 1] * 100), ("bytes", [512] * 99),
                ("sdk", ""), ("os", " "), ("completeBodies", 99), ("concurrency", 9),
                ("modules", 99), ("contributionsPerModule", 9), ("runId", "stale"),
                ("resourceDeltas", {}), ("resourceDeltas", {"probes": 0})):
            values = self.performance()
            values[field] = value
            with self.subTest(field=field, value=str(value)[:40]), self.assertRaisesRegex(RuntimeError, "performance"):
                module.verify_performance(values, "current")
        values = self.performance()
        values["resourceDeltas"]["secrets"] = 1
        with self.assertRaisesRegex(RuntimeError, "performance"):
            module.verify_performance(values)

    def journeys(self, module):
        return [{"id": name, "distribution": distribution, "passed": True,
                 "hostSha256": ("a" if distribution == "baseline" else "b") * 64,
                 **({"diagnostics": 1, "activityDelta": 0} if name == "invalid-replacement" else
                    {"lifecycleId": str(uuid.uuid4()), "routeCalls": 1, "serviceCalls": 1, "bytes": 512})}
                for distribution in ("baseline", "custom") for name in module.JOURNEYS
                if distribution == "custom" or name != "custom-rebuild"]

    def test_package_journeys_require_exact_closure_actual_counters_and_fresh_lifecycles(self):
        module = self.load()
        values = self.journeys(module)
        module.verify_journeys(values)
        for mutation in ("missing", "duplicate", "failed", "stale-host", "stale-lifecycle", "no-route", "no-service", "invalid-active"):
            changed = copy.deepcopy(values)
            if mutation == "missing":
                changed.pop()
            elif mutation == "duplicate":
                changed[-1] = changed[0]
            elif mutation == "failed":
                changed[0]["passed"] = False
            elif mutation == "stale-host":
                changed[1]["hostSha256"] = "c" * 64
            elif mutation == "stale-lifecycle":
                changed[1]["lifecycleId"] = changed[0]["lifecycleId"]
            elif mutation == "no-route":
                changed[0]["routeCalls"] = 0
            elif mutation == "no-service":
                changed[0]["serviceCalls"] = 0
            else:
                changed[2]["activityDelta"] = 1
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                module.verify_journeys(changed)

    def test_default_lock_replay_rejects_added_removed_or_mutated_locks(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "packages.lock.json"
            lock.write_text("{}")
            before = module.lock_hashes(root)
            module.verify_locks(root, before)
            for mutation in ("changed", "missing", "added"):
                lock.write_text("{}")
                if mutation == "changed":
                    lock.write_text('{"changed":true}')
                elif mutation == "missing":
                    lock.unlink()
                else:
                    (root / "extra").mkdir()
                    (root / "extra/packages.lock.json").write_text("{}")
                with self.subTest(mutation=mutation), self.assertRaisesRegex(RuntimeError, "lock"):
                    module.verify_locks(root, before)

    def test_trx_requires_actual_nonempty_unique_passes_without_skips(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.trx"
            path.write_text('<TestRun><UnitTestResult testName="actual" outcome="Passed"/></TestRun>')
            self.assertEqual(["actual"], module.results(path))
            for xml in ('<TestRun/>', '<TestRun><UnitTestResult testName="actual" outcome="NotExecuted"/></TestRun>',
                        '<TestRun><UnitTestResult testName="actual" outcome="Failed"/></TestRun>',
                        '<TestRun><UnitTestResult testName="actual" outcome="Passed"/><UnitTestResult testName="actual" outcome="Passed"/></TestRun>'):
                path.write_text(xml)
                with self.assertRaisesRegex(RuntimeError, "discovery test results"):
                    module.results(path)

    def test_full_acceptance_cannot_omit_runtime_red_json_or_provenance(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for evidence in (None, {}, {"toolingPassed": True, "referenceConsumerPassed": True, "mutations": []}):
                with self.assertRaisesRegex(RuntimeError, "acceptance evidence"):
                    module.verify_full_evidence(evidence, root, root)

    def wire(self, module):
        journeys = self.journeys(module)
        observations, bodies = [], []
        for journey in journeys:
            if journey["id"] == "invalid-replacement":
                continue
            observation = {"schemaVersion": 1, "observation": {
                "lifecycleId": journey["lifecycleId"], "readinessAssessedAt": "synthetic"},
                "host": {"phase": "running", "startupAdmission": True}}
            body = json.dumps(observation).encode()
            journey["bytes"] = len(body)
            observations.append(observation)
            bodies.append(base64.b64encode(body).decode())
        return journeys, observations, bodies

    def test_actual_wire_bodies_require_all_current_distinct_lifecycles_and_matching_bytes(self):
        module = self.load()
        journeys, observations, bodies = self.wire(module)
        module.verify_observations(journeys, observations, bodies)
        for mutation in ("missing", "duplicate", "invalid", "oversized", "mismatch", "wrong-bytes", "old-phase"):
            changed_journeys, changed, encoded = copy.deepcopy((journeys, observations, bodies))
            if mutation == "missing":
                encoded.pop()
            elif mutation == "duplicate":
                changed[-1], encoded[-1] = changed[0], encoded[0]
            elif mutation == "invalid":
                encoded[0] = "not base64"
            elif mutation == "oversized":
                encoded[0] = "a" * (4 * ((4 * 1024 * 1024 + 2) // 3) + 1)
            elif mutation == "mismatch":
                encoded[0] = base64.b64encode(b"{}").decode()
            elif mutation == "wrong-bytes":
                changed_journeys[0]["bytes"] += 1
            else:
                changed[0]["host"]["phase"] = "stopped"
                body = json.dumps(changed[0]).encode()
                encoded[0] = base64.b64encode(body).decode()
                changed_journeys[0]["bytes"] = len(body)
            with self.subTest(mutation=mutation), self.assertRaisesRegex(RuntimeError, "discovery body"):
                module.verify_observations(changed_journeys, changed, encoded)

    def test_runtime_red_requires_intended_assertions_not_compilation_empty_skipped_or_unrelated_failures(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "red.trx"
            with self.assertRaises(OSError):
                module.runtime_failures(result, "Expected")
            result.write_text('<TestRun><UnitTestResult testName="Fixture.Expected" outcome="Failed"/></TestRun>')
            self.assertEqual(["Fixture.Expected"], module.runtime_failures(result, "Expected"))
            for xml in ('<TestRun/>',
                        '<TestRun><UnitTestResult testName="Fixture.Expected" outcome="Passed"/></TestRun>',
                        '<TestRun><UnitTestResult testName="Fixture.Expected" outcome="NotExecuted"/></TestRun>',
                        '<TestRun><UnitTestResult testName="Fixture.Unrelated" outcome="Failed"/></TestRun>',
                        '<TestRun><UnitTestResult testName="Fixture.Expected" outcome="Failed"/><UnitTestResult testName="Fixture.Expected" outcome="Failed"/></TestRun>'):
                result.write_text(xml)
                with self.assertRaisesRegex(RuntimeError, "runtime assertion"):
                    module.runtime_failures(result, "Expected")

    def synthetic_full(self, module, root):
        methods = {name for names in module.CASE_TESTS.values() for name in names}
        names = sorted(f"Hoard.Tests.DiscoveryContractTests.{name}" for name in methods)
        names += [f"Hoard.Tests.{name}.Synthetic" for classes in module.SUITE_CLASSES.values() for name in classes]
        names += list(module.REQUIRED_ADAPTER_SCENARIOS)
        results = root / "results"
        results.mkdir()
        def trx(path, tests, outcome):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("<TestRun>" + "".join(
                f'<UnitTestResult testName="{name}" outcome="{outcome}"/>' for name in tests) + "</TestRun>")
        trx(results / "discovery.trx", names[:-1], "Passed")
        trx(results / "discovery-architecture.trx", names[-1:], "Passed")
        recipes = {}
        for _, relative, original, _, _ in module.MUTATIONS:
            recipes.setdefault(relative, []).append(original)
        for relative, anchors in recipes.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(anchors))
        mutations = []
        for identity, relative, original, replacement, method in module.MUTATIONS:
            source = (root / relative).read_text()
            failed = [f"Hoard.Tests.DiscoveryContractTests.{method}"]
            trx(root / "mutation-results" / identity / "red.trx", failed, "Failed")
            mutations.append({"id": identity, "passed": True, "failedTests": failed,
                              "originalSha256": hashlib.sha256(source.encode()).hexdigest(),
                              "mutantSha256": hashlib.sha256(source.replace(original, replacement).encode()).hexdigest()})
        binaries = []
        for name in ("RetainedLifecycle", "RetainedConfiguration", "LegacyOptions"):
            binary = root / f"{name}.dll"
            binary.write_bytes(b"synthetic")
            assets = root / f"{name}.assets.json"
            assets.write_text("{}")
            binaries.append({"name": name, "baseline": module.BASELINE, "assembly": str(binary),
                             "assets": str(assets), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                             "baselineAssetsSha256": hashlib.sha256(assets.read_bytes()).hexdigest(),
                             "baselineDependencyHashes": {binary.name: hashlib.sha256(binary.read_bytes()).hexdigest()},
                             "sourceHashes": {"Program.cs": "a" * 64}})
        feed = root / "feed"
        feed.mkdir()
        packages = []
        for name in module.FEED_PACKAGES:
            path = feed / name
            path.write_bytes(name.encode())
            packages.append({"id": name, "package": str(path), "sha512": hashlib.sha512(path.read_bytes()).hexdigest()})
        graphs = [{"scanId": name, "projects": ["synthetic"], "ownership": {"synthetic": "Host"}} for name in (
            "platform", "Protocol.One", "Protocol.Two", "Metadata", "Artifact.One", "Artifact.Two", "Identity",
            "baseline", "custom", "old-provider", "lifecycle-consumer", "configuration-consumer", "registration",
            "application-consumer", "nonweb-consumer", "permitted-application", "forbidden-provider", "cross-slice")]
        journeys, observations, bodies = self.wire(module)
        cases, suites = module.inventory(names)
        return {"runId": "current", "inputHashes": {"synthetic": "a" * 64}, "toolingPassed": True,
                "expectedTestNames": list(names),
                "referenceConsumerPassed": True, "mutations": mutations, "testNames": names,
                "cases": cases, "suites": suites, "journeys": journeys, "observations": observations,
                "responseBodies": bodies, "performance": self.performance(), "oldBinaries": binaries,
                "graphs": graphs, "feedPackages": packages}

    def test_materials_gate_rejects_incomplete_graph_feed_and_retained_binary_provenance(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            evidence = self.synthetic_full(module, root)
            module.verify_materials(evidence, root)
            for mutation in ("graph", "binary", "binary-hash", "package", "package-hash", "extra-package"):
                changed = copy.deepcopy(evidence)
                if mutation == "graph":
                    changed["graphs"].pop()
                elif mutation == "binary":
                    changed["oldBinaries"].pop()
                elif mutation == "binary-hash":
                    changed["oldBinaries"][0]["sha256"] = "0" * 64
                elif mutation == "package":
                    changed["feedPackages"].pop()
                elif mutation == "package-hash":
                    changed["feedPackages"][0]["sha512"] = "0" * 128
                else:
                    (root / "feed/Unexpected.0.1.0.nupkg").write_bytes(b"unexpected")
                with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                    module.verify_materials(changed, root)

    def test_controller_materials_require_bound_manifest_actual_bytes_and_current_performance(self):
        import conformance_inherited as inherited
        from conformance_evidence import ConformanceError, canonical_bytes, file_sha256

        module = self.load()
        for mutation in ("none", "manifest-path", "manifest-bytes", "reference", "binary-bytes",
                         "package-bytes", "performance-run", "performance-path", "malformed-binary"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                work = root / "stores/inherited-controller-discovery"
                work.mkdir(parents=True)
                document = self.synthetic_full(module, work)
                if mutation == "reference":
                    document["referenceConsumerPassed"] = False
                elif mutation == "malformed-binary":
                    del document["oldBinaries"][0]["sha256"]
                manifest = work / "discovery-evidence.json"
                manifest.write_bytes(canonical_bytes(document))
                preparation = {
                    "manifestPath": manifest.relative_to(root).as_posix(), "manifestSha256": file_sha256(manifest)}
                performance = root / "stores/inherited-runtime/performance/performance.json"
                performance.parent.mkdir(parents=True)
                observed = self.performance()
                if mutation == "performance-run":
                    observed["runId"] = "stale"
                performance.write_bytes(canonical_bytes(observed))
                if mutation == "manifest-path":
                    preparation["manifestPath"] = "../discovery-evidence.json"
                elif mutation == "manifest-bytes":
                    manifest.write_bytes(canonical_bytes({**document, "changed": True}))
                elif mutation == "binary-bytes":
                    Path(document["oldBinaries"][0]["assembly"]).write_bytes(b"changed")
                elif mutation == "package-bytes":
                    Path(document["feedPackages"][0]["package"]).write_bytes(b"changed")
                elif mutation == "performance-path":
                    performance = root / "foreign-performance.json"
                if mutation == "none":
                    result = inherited.verify_discovery_materials(root, preparation, performance, "current")
                    self.assertFalse(result["qualification"])
                    self.assertEqual((11, 3, 18), (
                        result["feedPackages"], result["retainedBinaries"], result["graphs"]))
                else:
                    with self.assertRaises(ConformanceError):
                        inherited.verify_discovery_materials(root, preparation, performance, "current")

    def test_full_evidence_rejects_missing_stale_unsafe_and_mismatched_mechanism_proof(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            evidence = self.synthetic_full(module, root)
            with patch.object(module, "input_hashes", return_value=evidence["inputHashes"]), patch.dict(
                    module.os.environ, {"HOARD_DISCOVERY_RUN_ID": "current"}):
                module.verify_full_evidence(evidence, root, root)
                for mutation in ("source", "run", "red", "green", "case", "suite", "graph",
                                 "binary", "binary-hash", "binary-path", "package", "package-hash", "package-id",
                                 "missing-scenario"):
                    changed = copy.deepcopy(evidence)
                    if mutation == "source":
                        changed["inputHashes"] = {"synthetic": "b" * 64}
                    elif mutation == "run":
                        changed["runId"] = "old"
                    elif mutation == "red":
                        changed["mutations"][0]["mutantSha256"] = "b" * 64
                    elif mutation == "green":
                        changed["testNames"] = ["unrelated-passing"]
                    elif mutation == "case":
                        changed["cases"][0]["tests"].append("unrelated-passing")
                    elif mutation == "suite":
                        changed["suites"][0]["tests"] += 1
                    elif mutation == "graph":
                        changed["graphs"].pop()
                    elif mutation == "binary":
                        changed["oldBinaries"].pop()
                    elif mutation == "binary-hash":
                        changed["oldBinaries"][0]["sha256"] = "b" * 64
                    elif mutation == "binary-path":
                        changed["oldBinaries"][0]["assets"] = str(root.parent / "not-owned.json")
                    elif mutation == "package":
                        changed["feedPackages"].pop()
                    elif mutation == "package-hash":
                        changed["feedPackages"][0]["sha512"] = "b" * 128
                    elif mutation == "missing-scenario":
                        changed["expectedTestNames"] = names = list(changed["testNames"])
                        names.pop()
                    else:
                        changed["feedPackages"][0]["package"] = changed["feedPackages"][1]["package"]
                        changed["feedPackages"][0]["sha512"] = changed["feedPackages"][1]["sha512"]
                    with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                        module.verify_full_evidence(changed, root, root)

    def test_retained_import_rejects_dependency_inventory_and_assets_drift_without_rebaselining(self):
        module = self.load()
        for mutation in ("dependency", "removed", "added", "assets", "missing-digests"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                saved, current = [], []
                for name in ("RetainedLifecycle", "RetainedConfiguration", "LegacyOptions"):
                    source, target = root / "retained" / name, root / "current" / name
                    source.mkdir(parents=True)
                    target.mkdir(parents=True)
                    binary, assets = source / f"{name}.dll", source / "baseline.assets.json"
                    binary.write_bytes(b"original")
                    assets.write_text("{}")
                    dependency = source / "Hoard.Abstractions.dll"
                    dependency.write_bytes(b"dependency")
                    saved.append({"name": name, "baseline": module.BASELINE, "assembly": str(binary),
                                  "assets": str(assets), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                                  "sourceHashes": {"Program.cs": "a" * 64},
                                  "baselineAssetsSha256": hashlib.sha256(assets.read_bytes()).hexdigest(),
                                  "baselineDependencyHashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                                               for path in source.glob("*.dll")}})
                    current.append({**saved[-1], "assembly": str(target / binary.name)})
                if mutation == "dependency":
                    (root / "retained/RetainedLifecycle/Hoard.Abstractions.dll").write_bytes(b"changed")
                elif mutation == "removed":
                    (root / "retained/RetainedLifecycle/Hoard.Abstractions.dll").unlink()
                elif mutation == "added":
                    (root / "retained/RetainedLifecycle/Added.dll").write_bytes(b"new")
                elif mutation == "assets":
                    Path(saved[0]["assets"]).write_text('{"changed":true}')
                else:
                    del saved[0]["baselineDependencyHashes"]
                (root / "retained/retained-binaries.json").write_text(json.dumps(saved))
                with self.assertRaisesRegex(RuntimeError, "retained|Retained"):
                    module.verify_retained_inputs(current, root / "retained")

    def test_scenario_closure_rejects_one_missing_theory_row_or_suite_class(self):
        module = self.load()
        names = list(module.REQUIRED_ADAPTER_SCENARIOS) + [
            f"Hoard.Tests.{name}.Scenario" for classes in module.SUITE_CLASSES.values() for name in classes]
        module.verify_scenarios(names, names)
        for missing in (module.REQUIRED_ADAPTER_SCENARIOS[-1], module.REQUIRED_ADAPTER_SCENARIOS[1],
                        "Hoard.Tests.DiscoveryExposureTests.Scenario"):
            changed = [name for name in names if name != missing]
            with self.subTest(missing=missing), self.assertRaisesRegex(RuntimeError, "scenario/class"):
                module.verify_scenarios(changed, names)
        with self.assertRaisesRegex(RuntimeError, "scenario/class"):
            module.verify_scenarios(names[:-1], names[:-1])


if __name__ == "__main__":
    unittest.main()
