import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import artifact_evidence as artifact


class ArtifactEvidenceTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / ".foundation" / "artifact-tooling"
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.work = parent / uuid.uuid4().hex
        self.work.mkdir(mode=0o700)
        self.addCleanup(shutil.rmtree, self.work)

    def proof(self, name, value):
        path = self.work / name
        path.write_text(json.dumps(value))
        return {"proof": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def test_current_preparation_uses_current_metadata_and_sdk_not_a_rebuilt_historical_recipe(self):
        root = self.work / "source"
        work = self.work / "prepared"
        root.mkdir()
        work.mkdir()
        for relative in (
                "Directory.Build.props", "Directory.Packages.props", "global.json",
                "specs/004-module-discovery/contracts/openapi.json",
                *(f"src/Hoard.{name}/Hoard.{name}.csproj"
                  for name in ("Abstractions", "Core", "Hosting", "Application")),
                *(f"tests/fixtures/artifacts/{name}/{name}.csproj" for name in (
                    "Local", "ObjectSemantics", "HostAdapters", "Consumer",
                    "CrashRunner", "TransferRunner", "BoundaryLeak")),
                "tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj",
                "tests/contracts/Hoard.Testing.Conformance/Artifacts/ArtifactCrashAssertions.cs"):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("tooling-only-current-source")
            if relative.endswith(".csproj"):
                for lock in (target.parent / "packages.lock.json",
                             target.parent / "PackageAcceptance/packages.lock.json"):
                    lock.parent.mkdir(parents=True, exist_ok=True)
                    lock.write_text('{"version":2,"dependencies":{"net10.0":{}}}')
                    if target.stem == "Hoard.Artifacts.Tests" and lock.parent.name == "PackageAcceptance":
                        lock.write_text('{"version":2,"dependencies":{"net10.0":{'
                            '"Hoard.Testing.Conformance":{"resolved":"0.1.0","contentHash":"original"}}}}')
        commands = []

        def metadata_packages(source, destination, update):
            self.assertEqual(source, root)
            self.assertFalse(update)
            (destination / "feed").mkdir()
            for name in ("Sqlite", "Memory", "HostAdapters"):
                (destination / "feed" / f"Hoard.Fixtures.Metadata.{name}.0.1.0.nupkg").write_bytes(
                    b"tooling-only-current-metadata")
            (destination / "feed/Hoard.Testing.Conformance.0.1.0.nupkg").write_bytes(
                b"tooling-only-current-sdk")

        def command(*args, **kwargs):
            self.assertEqual(args[0], "dotnet",
                             "Current source preparation must not rebuild a historical metadata recipe.")
            commands.append(args)
            project = Path(args[2])
            self.assertTrue(project.is_file())
            if project.stem == "CrashRunner":
                shared = Path("tests/contracts/Hoard.Testing.Conformance/Artifacts/ArtifactCrashAssertions.cs")
                self.assertEqual((work / "current" / shared).read_bytes(), (root / shared).read_bytes())
            if project.stem == "Hoard.Artifacts.Tests":
                self.assertEqual((work / "feed/Hoard.Testing.Conformance.0.1.0.nupkg").read_bytes(),
                                 b"tooling-only-current-sdk")
                if "-p:ArtifactPackageAcceptance=true" in args:
                    self.assertTrue(any(arg.startswith("-p:NuGetLockFilePath=") for arg in args))
            if args[1] == "pack":
                name = ("Hoard.Fixtures.Artifacts." + project.stem
                        if "fixtures" in project.parts else project.stem)
                (work / "feed" / f"{name}.0.1.0.nupkg").write_bytes(b"tooling-only-current-package")
            return ""

        with (patch.object(artifact.metadata, "prepare_packages", side_effect=metadata_packages) as metadata,
              patch.object(artifact, "run", side_effect=command),
              patch.object(artifact.foundation, "canonicalize_acceptance_archive"),
              patch.object(artifact, "source_hash", return_value="a" * 64),
              patch.object(artifact, "lock_hashes", return_value={})):
            inputs = artifact.prepare_packages(root, work, False)
        metadata.assert_called_once_with(root, work / "metadata-packages", False)
        self.assertFalse(inputs["qualification"])
        self.assertEqual({item["id"] for item in inputs["packages"]}, set(artifact.PACKAGES))
        self.assertEqual(len(inputs["lockDerivations"]), 1)
        self.assertIn('"contentHash":"original"',
                      (root / "tests/contracts/Hoard.Artifacts.Tests/PackageAcceptance/packages.lock.json").read_text())
        self.assertTrue(any("-p:ArtifactPackageAcceptance=true" in args for args in commands))

    def cases(self):
        # Synthetic parser fixtures are not runtime-attribution or qualification evidence.
        projection = patch.object(artifact.legacy, "verify_projection")
        projection.start()
        self.addCleanup(projection.stop)
        witness = self.work / "synthetic.trx"
        bindings = {key: "a" * 64 for key in artifact.CASE_BINDINGS}
        entries = [
            {"id": f"AS-{number:02}", "provider": provider,
             "class": "L" if number <= 40 else "D" if number <= 44 else "Q",
             "result": "NotApplicable" if provider == "object" and 41 <= number <= 44 else "Passed",
             "reason": "simulation: no durable restart" if provider == "object" and 41 <= number <= 44 else "",
             "runId": "current", "positive": True, "negative": True,
             "tests": sorted(artifact.required_runtime_tests(provider, f"AS-{number:02}")), **bindings}
            for provider in ("local", "object") for number in range(1, 49)]
        from xml.sax.saxutils import quoteattr
        names = sorted({name for entry in entries for name in entry["tests"]})
        witness.write_text(
            '<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><Results>'
            + "".join(f'<UnitTestResult testName={quoteattr(name)} outcome="Passed" duration="00:00:00.001" />'
                      for name in names) + '</Results></TestRun>')
        proof = {"proof": "synthetic.trx", "sha256": artifact.sha256(witness)}
        for entry in entries:
            entry["durationMs"] = len(entry["tests"])
            entry.update(self.proof(f"synthetic-{entry['provider']}-{entry['id']}.json", {
                "schemaVersion": 1,
                **{key: entry[key] for key in ("id", "provider", "class", "result", "runId", *artifact.CASE_BINDINGS)},
                "subproofs": [{"id": role, "result": "Passed", "tests": entry["tests"], **proof}
                              for role in ("positive", "negative")]}))
        return entries

    def test_exact_inventory_rejects_missing_duplicate_foreign_stale_and_failed(self):
        cases = self.cases()
        artifact.verify_cases(cases, self.work, "current")
        for changed in (None, [], cases[:-1], cases + [cases[0]]):
            with self.subTest(kind=type(changed).__name__), self.assertRaises(RuntimeError):
                artifact.verify_cases(changed, self.work, "current")
        for field, value in (
                ("id", "AS-99"), ("provider", "foreign"), ("runId", "stale"),
                ("result", "Skipped"), ("result", "Failed"), ("class", "D"),
                ("positive", False), ("negative", False), ("tests", []),
                ("durationMs", -1), ("durationMs", True), ("durationMs", float("nan")),
                ("sha256", "a" * 64), ("sourceSha256", "b" * 64), ("lockSha256", "b" * 64),
                ("configurationSha256", "b" * 64), ("capabilitiesSha256", "b" * 64),
                ("environmentSha256", "b" * 64), ("packageSha256", "b" * 64)):
            changed = copy.deepcopy(cases)
            changed[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                artifact.verify_cases(changed, self.work, "current")

    def test_exactly_four_object_durable_exclusions_not_skips_or_passes(self):
        cases = self.cases()
        for result in ("Passed", "Skipped", "Failed"):
            changed = copy.deepcopy(cases)
            changed[88]["result"] = result
            with self.subTest(result=result), self.assertRaises(RuntimeError):
                artifact.verify_cases(changed, self.work, "current")
        changed = copy.deepcopy(cases)
        changed[88]["reason"] = "not tested"
        with self.assertRaises(RuntimeError):
            artifact.verify_cases(changed, self.work, "current")

    def test_case_hash_cannot_substitute_foreign_failed_or_unattributed_proof_contents(self):
        cases = self.cases()
        for payload in (
                {"synthetic": "no case attribution"},
                {"id": "AS-02", "provider": "object", "runId": "stale", "result": "Failed"},
                {"id": "AS-01", "provider": "local", "runId": "current", "result": "Passed", "subproofs": []}):
            changed = copy.deepcopy(cases)
            changed[0].update(self.proof("unattributed.json", payload))
            with self.subTest(payload=payload), self.assertRaises(RuntimeError):
                artifact.verify_cases(changed, self.work, "current")

    def test_case_cannot_borrow_an_unrelated_passed_runtime_method(self):
        cases = self.cases()
        payload = json.loads(artifact.proof_file(self.work, cases[0]["proof"]).read_text())
        cases[0]["tests"] = cases[1]["tests"]
        cases[0]["durationMs"] = len(cases[0]["tests"])
        for subproof in payload["subproofs"]:
            subproof["tests"] = cases[0]["tests"]
        cases[0].update(self.proof("borrowed-runtime-case.json", payload))
        with self.assertRaisesRegex(RuntimeError, "required runtime"):
            artifact.verify_cases(cases, self.work, "current")

    def test_case_requires_every_parameter_variant_and_its_own_provider(self):
        for provider, case in (("local", "AS-10"), ("object", "AS-28"), ("local", "AS-39")):
            cases = self.cases()
            entry = next(entry for entry in cases if entry["provider"] == provider and entry["id"] == case)
            payload = json.loads(artifact.proof_file(self.work, entry["proof"]).read_text())
            entry["tests"] = entry["tests"][1:]
            for subproof in payload["subproofs"]:
                subproof["tests"] = entry["tests"]
            entry.update(self.proof("missing-variant.json", payload))
            with self.subTest(provider=provider, case=case), self.assertRaisesRegex(RuntimeError, "required runtime"):
                artifact.verify_cases(cases, self.work, "current")
        cases = self.cases()
        payload = json.loads(artifact.proof_file(self.work, cases[0]["proof"]).read_text())
        cases[0]["tests"] = sorted(artifact.required_runtime_tests("object", "AS-01"))
        for subproof in payload["subproofs"]:
            subproof["tests"] = cases[0]["tests"]
        cases[0].update(self.proof("foreign-provider.json", payload))
        with self.assertRaisesRegex(RuntimeError, "required runtime"):
            artifact.verify_cases(cases, self.work, "current")

    def test_required_name_in_inventory_is_not_proof_of_execution(self):
        cases = self.cases()
        witness = self.work / "synthetic.trx"
        from xml.etree import ElementTree
        document = ElementTree.parse(witness)
        results = document.getroot().find("{*}Results")
        for result in list(results):
            if result.get("testName") in cases[0]["tests"]:
                results.remove(result)
        document.write(witness)
        payload = json.loads(artifact.proof_file(self.work, cases[0]["proof"]).read_text())
        for subproof in payload["subproofs"]:
            subproof["sha256"] = artifact.sha256(witness)
        cases[0].update(self.proof("unexecuted-required-name.json", payload))
        with self.assertRaisesRegex(RuntimeError, "unexecuted runtime"):
            artifact.verify_cases(cases, self.work, "current")

    def test_case_payload_rejects_altered_binding_and_missing_or_failed_runtime_pairs(self):
        cases = self.cases()
        original = json.loads(artifact.proof_file(self.work, cases[0]["proof"]).read_text())
        mutations = [("schemaVersion", True), ("provider", "object"), ("id", "AS-02"),
                     ("result", "Failed"), ("class", "D"), ("runId", "stale"),
                     ("subproofs", []), ("subproofs", original["subproofs"][:1]),
                     ("subproofs", [original["subproofs"][0]] * 2),
                     *((key, "b" * 64) for key in artifact.CASE_BINDINGS)]
        for field, value in mutations:
            changed = copy.deepcopy(cases)
            payload = {**original, field: value}
            changed[0].update(self.proof("mutated-case.json", payload))
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                artifact.verify_cases(changed, self.work, "current")
        for field, value in (("result", "Skipped"), ("tests", []),
                             ("tests", ["foreign-test"]), ("sha256", "b" * 64)):
            changed = copy.deepcopy(cases)
            payload = copy.deepcopy(original)
            payload["subproofs"][0][field] = value
            changed[0].update(self.proof("mutated-subproof.json", payload))
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                artifact.verify_cases(changed, self.work, "current")

    def test_runtime_witness_cannot_invent_test_execution_or_duration(self):
        cases = self.cases()
        payload = json.loads(artifact.proof_file(self.work, cases[0]["proof"]).read_text())
        cases[0]["tests"] = ["never-executed"]
        for subproof in payload["subproofs"]:
            subproof["tests"] = cases[0]["tests"]
        cases[0].update(self.proof("invented-test.json", payload))
        with self.assertRaisesRegex(RuntimeError, "required runtime"):
            artifact.verify_cases(cases, self.work, "current")
        cases = self.cases()
        cases[0]["durationMs"] = 100
        with self.assertRaisesRegex(RuntimeError, "duration"):
            artifact.verify_cases(cases, self.work, "current")
        for outcome in ("Failed", "NotExecuted"):
            cases = self.cases()
            witness = self.work / "synthetic.trx"
            witness.write_text(witness.read_text().replace('outcome="Passed"', f'outcome="{outcome}"'))
            for entry in cases:
                payload = json.loads(artifact.proof_file(self.work, entry["proof"]).read_text())
                for subproof in payload["subproofs"]:
                    subproof["sha256"] = artifact.sha256(witness)
                entry.update(self.proof(entry["proof"], payload))
            with self.subTest(outcome=outcome), self.assertRaisesRegex(RuntimeError, "runtime witness"):
                artifact.verify_cases(cases, self.work, "current")

    def test_runtime_witness_rejects_malformed_duplicate_and_negative_duration_results(self):
        self.cases()
        original = (self.work / "synthetic.trx").read_text()
        from xml.sax.saxutils import quoteattr
        name = sorted(artifact.required_runtime_tests("local", "AS-01"))[0]
        duplicate = f'<UnitTestResult testName={quoteattr(name)} outcome="Passed" duration="00:00:00.001" />'
        for content in ("not XML", original.replace("</Results>", duplicate + "</Results>"),
                        original.replace('duration="00:00:00.001"', 'duration="00:00:-0.001"')):
            cases = self.cases()
            witness = self.work / "synthetic.trx"
            witness.write_text(content)
            payload = json.loads(artifact.proof_file(self.work, cases[0]["proof"]).read_text())
            for subproof in payload["subproofs"]:
                subproof["sha256"] = artifact.sha256(witness)
            cases[0].update(self.proof("invalid-runtime-witness.json", payload))
            with self.subTest(content=content), self.assertRaisesRegex(RuntimeError, "runtime witness"):
                artifact.verify_cases(cases, self.work, "current")

    def transfer(self):
        return {
            "provider": "local", "runId": "current", "pid": 42, "runtime": ".NET 10",
            "size": 4294967296, "written": 4294967296, "read": 4294967296,
            "expectedSha256": "a" * 64, "sourceSha256": "a" * 64, "sinkSha256": "a" * 64,
            "baselineRssBytes": 40_000_000, "osPeakRssBytes": 80_000_000,
            "sampledPeakRssBytes": 70_000_000, "rssUnits": "bytes",
            "osPeakMethod": "getrusage", "samples": 20, "exitCode": 0,
            "bufferBytes": 262144, "providerBufferLimit": 2097152, "slots": 1,
            "sourcePaced": True, "sinkPaced": True, "nonSeekable": True,
            "generated": True, "independentExpectedHash": True, "warmupComplete": True}

    def test_transfer_proof_rejects_small_sparse_unmeasured_or_unbounded_runs(self):
        proof = self.transfer()
        artifact.verify_transfer(proof, "local", 4294967296, "current")
        for field, value in (
                ("size", 1024), ("written", 1024), ("read", 1024), ("pid", 0),
                ("runId", "old"), ("provider", "object"), ("sinkSha256", "b" * 64),
                ("sourceSha256", "b" * 64), ("expectedSha256", ""),
                ("osPeakRssBytes", 200_000_000), ("samples", 0), ("rssUnits", "unknown"),
                ("baselineRssBytes", 0), ("osPeakMethod", "managed allocations"),
                ("sourcePaced", False), ("sinkPaced", False), ("generated", False),
                ("nonSeekable", False), ("independentExpectedHash", False),
                ("warmupComplete", False), ("exitCode", 1), ("bufferBytes", 4194304),
                ("slots", 4)):
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                artifact.verify_transfer({**proof, field: value}, "local", 4294967296, "current")

    def crash(self):
        return {"barrier": "B2", "runId": "current", "provider": "local", "pid": 42,
                "reopenPid": 43, "signal": "SIGKILL", "exitCode": -9, "exitConfirmed": True,
                "handshake": True, "stateCompared": True, "receiptCompared": True,
                "controlReadback": True, "newReadback": True, "ownerFenced": True,
                "noDuplicateEffect": True, "stateSha256": "a" * 64}

    def test_crash_proof_rejects_exception_graceful_exit_foreign_or_missing_barrier(self):
        proof = self.crash()
        artifact.verify_crash(proof, "B2", "current")
        for field, value in (
                ("barrier", "B1"), ("runId", "old"), ("provider", "object"), ("pid", 0),
                ("reopenPid", 42), ("signal", "exception"), ("exitCode", 0),
                ("exitConfirmed", False), ("handshake", False), ("controlReadback", False),
                ("newReadback", False), ("receiptCompared", False), ("stateCompared", False),
                ("ownerFenced", False), ("noDuplicateEffect", False), ("stateSha256", "")):
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                artifact.verify_crash({**proof, field: value}, "B2", "current")

    def test_runtime_red_green_requires_assertion_not_compile_failure(self):
        proof = {"id": "bounded-input", "test": "actual-test", "redExit": 1,
                 "redOutcome": "Failed", "redAssertion": True, "greenOutcome": "Passed",
                 "mutationSha256": "a" * 64, "baselineSha256": "b" * 64}
        artifact.verify_red_green([proof])
        for field, value in (
                ("redExit", 0), ("redAssertion", False), ("redOutcome", "CompileFailed"),
                ("greenOutcome", "Skipped"), ("mutationSha256", "b" * 64)):
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                artifact.verify_red_green([{**proof, field: value}])
        with self.assertRaises(RuntimeError):
            artifact.verify_red_green([])

    def test_actual_recovery_readback_requires_exact_run_hashes_outcomes_and_all_observations(self):
        content = hashlib.sha256(bytes((index * 17 + 11) % 256 for index in range(1048576))).hexdigest()
        control = b"acknowledged independent control before crash"
        control_hash = hashlib.sha256(control).hexdigest()
        state = {"Run": "current", "Barrier": "D1", "TargetDigest": content, "TargetLength": 1048576,
                 "Control": {"Digest": control_hash, "Length": len(control)}}
        observed = {"eventName": "recovered", "provider": "local", "qualification": False,
                    "pid": 43, "runId": "current", "barrier": "D1", "outcome": "Removed",
                    "reconstructed": False, "reclamation": "Reclaimed",
                    "contentSha256": content, "contentLength": 1048576,
                    "controlSha256": control_hash, "controlLength": len(control),
                    **{key: True for key in ("controlReadback", "controlReceipt", "exactReceipt",
                                            "contentReadback", "ownerFenced", "noDuplicateEffect")}}
        artifact.validate_recovery_readback(observed, state, "D1", "current", 43)
        for field, value in (("runId", "foreign"), ("pid", 42), ("provider", "object"),
                             ("qualification", True), ("contentSha256", "c" * 64),
                             ("controlLength", 0), ("outcome", "AlreadyAbsent"),
                             ("reconstructed", True), ("reclamation", "Pending"),
                             ("ownerFenced", False), ("exactReceipt", False), ("noDuplicateEffect", False)):
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                artifact.validate_recovery_readback({**observed, field: value}, state, "D1", "current", 43)

    def test_unfinished_full_manifest_never_qualifies(self):
        for manifest in (None, {}, {"qualification": True}, {
                "schemaVersion": 1, "qualification": True, "production": False,
                "sourceSha256": "a" * 64, "runId": "current", "cases": self.cases()}):
            with self.subTest(manifest=str(manifest)[:60]), self.assertRaises(RuntimeError):
                artifact.verify_manifest(manifest, self.work, "a" * 64)

    def complete_manifest(self):
        packages = [{"id": name, **self.proof(name, {})} for name in artifact.PACKAGES]
        transfers = [{**self.transfer(), "provider": provider, "size": size, "written": size, "read": size}
                     for provider in artifact.PROVIDERS for size in (268435456, 4294967296)]
        manifest = {
            "schemaVersion": 1, "qualification": True, "production": False, "phase": "full",
            "sourceSha256": "a" * 64, "runId": "current", "baselineRevision": artifact.BASELINE,
            "environment": {"os": "test", "runtime": ".NET 10", "filesystem": "test", "flushConfiguration": "test"},
            "limitations": ["synthetic unit fixture, never runtime qualification"],
            "cases": self.cases(), "packages": packages, "transfers": transfers,
            "crashes": [{**self.crash(), "barrier": barrier} for barrier in artifact.BARRIERS],
            "redGreen": [{"id": "test", "test": "test", "redExit": 1, "redOutcome": "Failed",
                          "redAssertion": True, "greenOutcome": "Passed",
                          "mutationSha256": "a" * 64, "baselineSha256": "b" * 64}]}
        inputs = {"locks": self.proof("locks.json", {"example/packages.lock.json": "a" * 64}),
                  "environment": self.proof("environment.json", manifest["environment"]), "contexts": []}
        package_hash = packages[0]["sha256"]
        for provider in artifact.PROVIDERS:
            capabilities = {
                "Version": 1, "Durability": 0 if provider == "local" else 1,
                "Enumeration": 0 if provider == "local" else 1, "MeetsBaseline": True,
                "Limits": {"TransferSlots": 4}, "RangeReads": False, "Sha512": True,
                **{key: True for key in ("ConditionalPublication", "ConditionalDeletion", "StagingRecovery",
                                        "OwnerFencing", "ReaderProtection", "BoundedStreaming")}}
            configuration = {"limits": capabilities["Limits"]}
            context = {"implementationId": f"fixture.artifact.{provider}", "runtime": ".NET 10",
                       "capabilities": capabilities, "configuration": configuration}
            reference = {"id": provider, **self.proof(f"context-{provider}.json", context),
                         "capabilities": self.proof(f"capabilities-{provider}.json", capabilities),
                         "configuration": self.proof(f"configuration-{provider}.json", configuration)}
            inputs["contexts"].append(reference)
            bindings = {
                "sourceSha256": "a" * 64, "lockSha256": inputs["locks"]["sha256"],
                "environmentSha256": hashlib.sha256(b"test\n.NET 10\ntest\ntest").hexdigest(),
                "packageSha256": package_hash,
                "capabilitiesSha256": reference["capabilities"]["sha256"],
                "configurationSha256": reference["configuration"]["sha256"]}
            for entry in manifest["cases"]:
                if entry["provider"] == provider:
                    entry.update(bindings)
                    payload = json.loads(artifact.proof_file(self.work, entry["proof"]).read_text())
                    payload.update(bindings)
                    entry.update(self.proof(entry["proof"], payload))
        manifest["inputs"] = inputs
        return manifest

    def test_matching_outer_and_inner_bindings_cannot_replace_actual_inputs(self):
        for field in artifact.CASE_BINDINGS[1:]:
            manifest = self.complete_manifest()
            artifact.verify_input_bindings(manifest, self.work, "a" * 64)
            for entry in manifest["cases"]:
                entry[field] = "b" * 64
                payload = json.loads(artifact.proof_file(self.work, entry["proof"]).read_text())
                payload[field] = "b" * 64
                entry.update(self.proof(entry["proof"], payload))
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                artifact.verify_input_bindings(manifest, self.work, "a" * 64)

    def test_proof_rejects_escape_symlink_missing_and_hash_tampering(self):
        artifact.proof_file(self.work, self.proof("valid.json", {})["proof"])
        (self.work / "link").symlink_to(self.work / "valid.json")
        for name in ("../valid.json", str(self.work / "valid.json"), "link", "absent"):
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                artifact.proof_file(self.work, name)
        cases = self.cases()
        artifact.proof_file(self.work, cases[0]["proof"]).write_text('{"changed":true}')
        with self.assertRaises(RuntimeError):
            artifact.verify_cases(cases, self.work, "current")

    def test_source_lock_and_package_hash_drift_rejects(self):
        proof = self.proof("source.json", {})
        entries = [{"id": "source", **proof}]
        artifact.verify_files(entries, self.work, ("source",))
        for changed in ([], entries + entries, [{**entries[0], "sha256": "f" * 64}]):
            with self.assertRaises(RuntimeError):
                artifact.verify_files(changed, self.work, ("source",))
        locks = artifact.lock_hashes(ROOT)
        with self.assertRaises(RuntimeError):
            artifact.verify_locks(ROOT, {**locks, "foreign/packages.lock.json": "a" * 64})

    def test_metadata_inputs_allow_only_local_package_hash_refresh(self):
        old = self.work / "baseline/packages.lock.json"
        new = self.work / "current/packages.lock.json"
        old.parent.mkdir()
        new.parent.mkdir()
        lock = {"version": 1, "dependencies": {"net10.0": {
            "Hoard.Abstractions": {
                "type": "Direct", "requested": "[0.1.0, 0.1.0]", "resolved": "0.1.0",
                "contentHash": base64.b64encode(b"a" * 64).decode()},
            "External.Package": {
                "type": "Transitive", "resolved": "1.0.0",
                "contentHash": base64.b64encode(b"b" * 64).decode()}}}}
        old.write_text(json.dumps(lock))
        new.write_text(json.dumps(lock))
        artifact.verify_metadata_input(old, new)
        changed = copy.deepcopy(lock)
        changed["dependencies"]["net10.0"]["Hoard.Abstractions"]["contentHash"] = base64.b64encode(b"c" * 64).decode()
        new.write_text(json.dumps(changed))
        artifact.verify_metadata_input(old, new)

        for package, field, value in (
                ("Hoard.Abstractions", "resolved", "0.1.1"),
                ("Hoard.Abstractions", "requested", "[0.1.0, 0.2.0]"),
                ("Hoard.Abstractions", "dependencies", {"New.Dependency": "1.0.0"}),
                ("Hoard.Abstractions", "contentHash", "invalid"),
                ("Hoard.Abstractions", "contentHash", base64.b64encode(b"short").decode()),
                ("External.Package", "contentHash", "c" * 88)):
            changed = copy.deepcopy(lock)
            changed["dependencies"]["net10.0"][package][field] = value
            new.write_text(json.dumps(changed))
            with self.subTest(package=package, field=field), self.assertRaises(RuntimeError):
                artifact.verify_metadata_input(old, new)
        for name in ("Fixture.cs", "Fixture.csproj"):
            prior = old.with_name(name)
            current = new.with_name(name)
            prior.write_text("original")
            current.write_text("changed")
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                artifact.verify_metadata_input(prior, current)

    def test_cleanup_requires_owned_exact_root_and_settled_children(self):
        with self.assertRaises(RuntimeError):
            artifact.cleanup_workspace(self.work)
        owned = artifact.create_workspace(self.work / "owned", self.work / "repository")
        with self.assertRaises(RuntimeError):
            artifact.cleanup_workspace(self.work)
        artifact.cleanup_workspace(owned)
        self.assertTrue(self.work.is_dir())
        self.assertFalse(owned.exists())

    def test_destination_rejects_existing_inside_repository_and_symlinked_parent(self):
        (self.work / "link").symlink_to(self.work, target_is_directory=True)
        for target in (self.work, ROOT / ".foundation/unsafe", self.work / "link/child"):
            with self.subTest(target=str(target)), self.assertRaises(RuntimeError):
                artifact.create_workspace(target, ROOT)

    def test_failed_child_and_timeout_fail_without_exposing_output(self):
        for timed_out in (False, True):
            command = "print('synthetic-private-canary',flush=True); " + (
                "import time; time.sleep(60)" if timed_out else "raise SystemExit(7)")
            with self.subTest(timed_out=timed_out), \
                    patch.object(artifact, "COMMAND_TIMEOUT_SECONDS", 0.2), \
                    self.assertRaises(RuntimeError) as caught:
                artifact.run(sys.executable, "-c", command)
            self.assertNotIn("synthetic-private-canary", str(caught.exception))
            self.assertIn("finite deadline" if timed_out else "CommandFailed", str(caught.exception))

    def test_timeout_with_unsettled_pipe_reports_cleanup_incomplete_not_success(self):
        with patch.object(artifact.legacy, "capture",
                          side_effect=RuntimeError("Legacy command cleanup incomplete; private stores retained.")), \
                self.assertRaisesRegex(RuntimeError, "cleanup incomplete"):
            artifact.run("fixture")

    def test_actual_timeout_stops_owned_descendant_and_preserves_unrelated_child(self):
        marker = self.work / "descendant.json"
        descendant = (
            "import json,os,time; from pathlib import Path; "
            f"Path({str(marker)!r}).write_text(json.dumps([os.getpid(),os.getpgrp()])); "
            "time.sleep(60)"
        )
        command = (
            "import subprocess,sys,time; "
            f"subprocess.Popen([sys.executable,'-c',{descendant!r}]); "
            "time.sleep(60)"
        )
        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
        try:
            with patch.object(artifact, "COMMAND_TIMEOUT_SECONDS", 2), \
                    self.assertRaisesRegex(RuntimeError, "finite deadline"):
                artifact.run(sys.executable, "-c", command)
            self.assertTrue(marker.is_file(), "The real descendant must exist before timeout.")
            descendant_pid, group = json.loads(marker.read_text())
            self.assertNotEqual(descendant_pid, group)
            self.assertEqual(set(), artifact.command_processes(group))
            self.assertIsNone(unrelated.poll())
        finally:
            if marker.is_file():
                _, group = json.loads(marker.read_text())
                for pid in artifact.command_processes(group):
                    os.kill(pid, artifact.signal.SIGKILL)
            if unrelated.poll() is None:
                unrelated.kill()
            unrelated.wait(timeout=10)

    def test_interrupted_command_propagates_after_transport_cleanup(self):
        with patch.object(artifact.legacy, "capture", side_effect=KeyboardInterrupt()), \
                self.assertRaises(KeyboardInterrupt):
            artifact.run("fixture")

    def test_command_processes_selects_only_live_members_of_its_owned_session(self):
        output = "42 42 S\n43 42 R\n44 42 Z\n99 99 S\n"
        with patch.object(artifact.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0, output, "")):
            self.assertEqual({42, 43}, artifact.command_processes(42))

    def test_focused_modes_never_qualify_even_with_complete_inventory(self):
        for phase in ("logical", "transfers", "recovery", "packages"):
            with self.subTest(phase=phase), self.assertRaises(RuntimeError):
                artifact.verify_manifest({"qualification": True, "phase": phase},
                                         self.work, "a" * 64)

    def test_roundtrip_only_report_cannot_claim_complete_consumer_operations(self):
        old = {"qualification": False, "provider": "local", "roundTrip": True}
        reports = [json.dumps({**old, "provider": provider}) for provider in artifact.PROVIDERS]
        with patch.object(artifact, "run", side_effect=reports), \
                self.assertRaisesRegex(RuntimeError, "consumer"):
            artifact.consumer_journeys(self.work)

    def test_consumer_report_requires_each_operation_once_for_both_choices(self):
        reports = [{"qualification": False, "provider": provider, "roundTrip": True,
                    "operations": list(artifact.CONSUMER_OPERATIONS)} for provider in artifact.PROVIDERS]
        with patch.object(artifact, "run", side_effect=[json.dumps(value) for value in reports]):
            self.assertEqual(reports, artifact.consumer_journeys(self.work))
        for operations in ([], list(artifact.CONSUMER_OPERATIONS[:-1]),
                           [*artifact.CONSUMER_OPERATIONS, artifact.CONSUMER_OPERATIONS[0]],
                           [*artifact.CONSUMER_OPERATIONS[:-1], "ForeignAsync"]):
            changed = [{**reports[0], "operations": operations}, reports[1]]
            with self.subTest(operations=operations), \
                    patch.object(artifact, "run", side_effect=[json.dumps(value) for value in changed]), \
                    self.assertRaisesRegex(RuntimeError, "consumer"):
                artifact.consumer_journeys(self.work)

    def test_package_phase_runs_real_compatibility_and_never_qualifies(self):
        destination = self.work / "package-phase"
        destination.mkdir()
        with patch.object(artifact, "create_workspace", return_value=destination), \
                patch.object(artifact, "prepare_baseline"), patch.object(artifact, "prepare_packages"), \
                patch.object(artifact, "package_checks", create=True, return_value={"testsPassed": 1}) as checks, \
                patch.object(artifact, "source_hash", return_value="a" * 64), \
                patch("builtins.print"), \
                patch.object(sys, "argv", ["artifact_evidence", str(ROOT), "--phase", "packages",
                                          "--evidence", str(destination)]):
            self.assertEqual(0, artifact.main())
        checks.assert_called_once_with(ROOT, destination)
        manifest = json.loads((destination / "manifest.json").read_text())
        self.assertIs(False, manifest["qualification"])
        self.assertEqual("packages", manifest["phase"])
