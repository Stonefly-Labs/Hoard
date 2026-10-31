"""Transport controls are modeled diagnostics, not runtime qualification."""

import copy
import contextlib
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import tarfile
import unittest
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import conformance_case_catalog as catalog
import conformance_evidence as evidence


class ConformanceHostedTests(unittest.TestCase):
    """Modeled trust/transport controls; these never claim hosted/native acceptance."""

    def fixture(self, parent):
        import conformance_ci as ci
        import conformance_hosted as hosted
        from test_conformance_evidence import ConformanceAdmissionTests

        root = parent / "private" / "profiles" / "harness"
        root.parent.parent.mkdir(mode=0o700)
        root.parent.mkdir(mode=0o700)
        root.mkdir(mode=0o700)
        report = ConformanceAdmissionTests().report()
        inputs = report["inputs"]
        inputs.update(profileId="harness", mode="qualification", sourceState="clean-ci", bindings=[])
        inputs["budgets"]["profileSeconds"] = 3600
        case = catalog.expected_cases("harness")[0]
        result = report["results"][0]
        result.update(profileId="harness", bindingId=case.binding_id,
                      matrixId=case.matrix_id, caseId=case.case_id)
        resources = [{
            "runId": inputs["runId"], "rootId": "modeled-root", "childPid": 0,
            "childStartSha256": "0" * 64, "state": "Released", "cleanupDurationMs": 1,
            "diagnosticCode": "None",
        }]
        report.update(results=[result], resources=resources, state="Complete",
                      qualification=True, scope=["harness-fixture-qualification"],
                      postInputSha256=evidence.digest(inputs))
        # Real proof names include extensionless binaries, claims/Python and runtime/discovery trees.
        contents = {
            "runtime-" + str(uuid.uuid4()) + "/witnesses.jsonl": b'{"safe":true}\n',
            "discovery-" + str(uuid.uuid4()) + "/completion.json": b'{"safe":true}',
            "proofs/" + "a" * 64: b"bounded-binary",
            "proofs/control.claim": b'{"safe":true}',
            "proofs/control.py": b"pass\n",
            "proofs/original.runsettings": b"<RunSettings />",
            "proofs/" + "selected-" * 16 + ".json": b'{"safe":true}',
            "proofs/category-harness-qualification-completion-inputs.json": evidence.canonical_bytes(inputs),
        }
        report["proofs"] = {path: hashlib.sha256(raw).hexdigest() for path, raw in contents.items()}
        result["proofSha256"] = [next(iter(report["proofs"].values()))]
        result["attempts"][0].update(proofSha256=result["proofSha256"])
        report["witnesses"][0].update(
            bindingId=case.binding_id, matrixId=case.matrix_id,
            inputSha256=evidence.digest(inputs), proofSha256=result["proofSha256"][0])
        input_path, report_path = ci.profile_paths("harness")
        original_path = "proofs/harness-runtime-released-report.json"
        original_raw = evidence.canonical_bytes({
            **report, "qualification": False, "state": "Incomplete", "scope": ["harness-runtime-diagnostic"]})
        report_raw = evidence.canonical_bytes(report)
        origin = {
            "kind": "native-harness-fixture-qualification",
            "inputsSha256": evidence.digest(inputs), "reportSha256": hashlib.sha256(report_raw).hexdigest(),
            "originalReportPath": original_path, "originalReportSha256": hashlib.sha256(original_raw).hexdigest(),
            "resourcesSha256": evidence.digest(resources),
        }
        self.inspected = {
            "qualification": True, "code": "None", "reportSha256": origin["reportSha256"],
            "caseStates": {"Passed": 1, "Failed": 0, "NotApplicable": 0, "Incomplete": 0},
        }
        contents.update({
            input_path: evidence.canonical_bytes(inputs), report_path: report_raw,
            original_path: original_raw, "ownership.json": b'{"safe":true}',
        })
        contents.update({
            "diagnostics/" + name: raw for name, raw in
            evidence._render_verified_fixture_qualification(report_raw, self.inspected).items()})
        for path, raw in contents.items():
            target = root / path
            target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            target.write_bytes(raw)
            target.chmod(0o400)
        # An unrelated physical workspace file is never part of the transport.
        (root / "unsafe.log").write_bytes(b"not public")
        entry = {
            "inputs": inputs, "reportPath": report_path, "reportSha256": origin["reportSha256"],
            "qualificationOrigin": origin,
        }
        bundle = parent / "harness.tar"
        with mock.patch.object(ci, "inspect_receipted_profile_qualification", return_value=self.inspected):
            pin = hosted.pack_profile(root, entry, bundle)
        return root, entry, pin, bundle, contents

    def rewrite(self, bundle, pin, mutate):
        import conformance_hosted as hosted

        with tarfile.open(bundle, mode="r:") as archive:
            rows = [(member.name, archive.extractfile(member).read()) for member in archive]
        manifest = evidence.load_json(rows[0][1])
        archive_paths = {hosted._archive_name(path): path for path in manifest["files"]}
        rows = [rows[0], *((archive_paths[name], raw) for name, raw in rows[1:])]
        rows = mutate(rows, manifest)
        raw_manifest = evidence.canonical_bytes(manifest)
        rows[0] = (hosted.MANIFEST, raw_manifest)
        with bundle.open("wb") as output:
            for name, raw in rows:
                hosted._write_member(output, name if name == hosted.MANIFEST else hosted._archive_name(name), raw)
            output.write(b"\0" * 1024)
        pin["manifestSha256"] = hashlib.sha256(raw_manifest).hexdigest()
        pin["transportSha256"] = hashlib.sha256(bundle.read_bytes()).hexdigest()

    def test_exact_transport_preserves_original_root_finite_bytes_and_all_declared_proof_kinds(self):
        import conformance_ci as ci
        import conformance_hosted as hosted

        with tempfile.TemporaryDirectory() as temporary:
            root, entry, pin, bundle, contents = self.fixture(Path(temporary).resolve())
            # Simulate a fresh aggregate runner without changing any packet bytes or root labels.
            root.rename(root.with_name("retained-original"))
            with mock.patch.object(ci, "inspect_receipted_profile_qualification",
                                   return_value=self.inspected) as reader:
                observed = hosted.unpack_profile(bundle, pin, root, common_context=entry["inputs"])
            reader.assert_called_once()
            self.assertEqual(evidence.canonical_bytes(observed), evidence.canonical_bytes(entry))
            files = {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}
            self.assertEqual(files, set(contents))
            self.assertNotIn("unsafe.log", files)
            for path, raw in contents.items():
                self.assertEqual((root / path).read_bytes(), raw)
                self.assertEqual((root / path).stat().st_mode & 0o777, 0o400)
            with self.assertRaisesRegex(evidence.ConformanceError, "^OwnershipInvalid$"):
                hosted.unpack_profile(bundle, pin, root, common_context=entry["inputs"])

    def test_download_hash_original_root_foreign_inputs_and_receipt_pins_reject_before_extraction(self):
        import conformance_hosted as hosted

        for defect in ("bytes", "root", "inputs", "origin", "missing-input"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                root, entry, pin, bundle, _ = self.fixture(Path(temporary).resolve())
                root.rename(root.with_name("retained-original"))
                target = root
                common = copy.deepcopy(entry["inputs"])
                if defect == "bytes":
                    data = bytearray(bundle.read_bytes())
                    data[1024] ^= 1
                    bundle.write_bytes(data)
                elif defect == "root":
                    target = root.with_name("relabeled")
                elif defect == "inputs":
                    common["invocationGroupId"] = str(uuid.uuid4())
                elif defect == "origin":
                    pin["qualificationOrigin"]["resourcesSha256"] = "f" * 64
                else:
                    input_path = hosted.ci.profile_paths("harness")[0]

                    def remove_input(rows, manifest):
                        del manifest["files"][input_path]
                        return [row for row in rows if row[0] != input_path]

                    self.rewrite(bundle, pin, remove_input)
                with self.assertRaises(evidence.ConformanceError):
                    hosted.unpack_profile(bundle, pin, target, common_context=common)
                self.assertFalse(target.exists())

    def test_resealed_traversal_links_duplicates_raw_outputs_undeclared_files_and_size_tricks_reject(self):
        import conformance_hosted as hosted

        for defect in ("traversal", "absolute", "duplicate", "symlink", "hardlink", "raw",
                       "extra", "casefold", "prefix", "size", "tail"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                root, entry, pin, bundle, _ = self.fixture(Path(temporary).resolve())
                root.rename(root.with_name("retained-original"))
                if defect in ("symlink", "hardlink", "tail"):
                    data = bytearray(bundle.read_bytes())
                    if defect == "tail":
                        data.extend(b"foreign-trailing-bytes")
                    else:
                        info = tarfile.TarInfo(hosted.MANIFEST)
                        info.mode, info.size = 0o600, 1
                        info.type = tarfile.SYMTYPE if defect == "symlink" else tarfile.LNKTYPE
                        info.linkname = "outside"
                        data[:512] = info.tobuf(format=tarfile.USTAR_FORMAT)
                    bundle.write_bytes(data)
                    pin["transportSha256"] = hashlib.sha256(data).hexdigest()
                else:
                    def mutate(rows, manifest):
                        if defect == "duplicate":
                            return [*rows, rows[-1]]
                        if defect == "size":
                            manifest["files"][rows[-1][0]]["size"] += 1
                            return rows
                        path = {
                            "traversal": "../outside.json", "absolute": "/outside.json",
                            "raw": "proofs/raw.trx", "extra": "proofs/unselected.py",
                            "casefold": rows[-1][0].upper(), "prefix": rows[-1][0] + "/child.json",
                        }[defect]
                        raw = b"unselected"
                        manifest["files"][path] = {"sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}
                        return [rows[0], *sorted([*rows[1:], (path, raw)])]

                    self.rewrite(bundle, pin, mutate)
                with self.assertRaises(evidence.ConformanceError):
                    hosted.unpack_profile(bundle, pin, root, common_context=entry["inputs"])
                self.assertFalse(root.exists())

    def test_finite_presentation_mutation_is_rejected_after_independent_receipt_replay(self):
        import conformance_ci as ci
        import conformance_hosted as hosted

        with tempfile.TemporaryDirectory() as temporary:
            root, entry, pin, bundle, _ = self.fixture(Path(temporary).resolve())
            root.rename(root.with_name("retained-original"))

            def mutate(rows, manifest):
                path = next(path for path in manifest["files"] if path.endswith("-ci-summary.md"))
                raw = b"optimistic-summary"
                manifest["files"][path] = {"sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}
                return [(name, raw if name == path else data) for name, data in rows]

            self.rewrite(bundle, pin, mutate)
            with mock.patch.object(ci, "inspect_receipted_profile_qualification", return_value=self.inspected):
                with self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
                    hosted.unpack_profile(bundle, pin, root, common_context=entry["inputs"])

    def test_transport_bounds_and_deadline_reject_before_extraction(self):
        import conformance_hosted as hosted

        for bound, value in (("MAX_FILES", 1), ("MAX_BYTES", 1), ("MAX_BUNDLE_BYTES", 1)):
            with self.subTest(bound=bound), tempfile.TemporaryDirectory() as temporary:
                root, entry, pin, bundle, _ = self.fixture(Path(temporary).resolve())
                root.rename(root.with_name("retained-original"))
                with mock.patch.object(hosted, bound, value), self.assertRaises(evidence.ConformanceError):
                    hosted.unpack_profile(bundle, pin, root, common_context=entry["inputs"])
                self.assertFalse(root.exists())
        with tempfile.TemporaryDirectory() as temporary:
            root, entry, pin, bundle, _ = self.fixture(Path(temporary).resolve())
            root.rename(root.with_name("retained-original"))
            with self.assertRaisesRegex(evidence.ConformanceError, "^DeadlineExceeded$"):
                hosted.unpack_profile(bundle, pin, root, common_context=entry["inputs"], deadline=0)

    def test_exact_existing_reader_dependencies_travel_without_workspace_globs_or_authority_reconstruction(self):
        import conformance_ci as ci
        import conformance_hosted as hosted
        import conformance_sdk_checks as sdk

        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root, entry, _, _, contents = self.fixture(parent)
            support = "proofs/original-runtime-context.json"
            settings = "proofs/settings-" + str(uuid.uuid4()) + ".runsettings"
            (root / support).write_bytes(b'{"safe":true}')
            (root / support).chmod(0o400)
            contents[support] = (root / support).read_bytes()
            (root / settings).write_bytes(b"<RunSettings />")
            (root / settings).chmod(0o400)
            contents[settings] = (root / settings).read_bytes()

            def reader(selected_root, *args, **options):
                self.assertEqual(evidence._readonly_report_proof(selected_root, support)[1], contents[support])
                self.assertEqual(sdk.read_bounded(selected_root / settings, 65536), contents[settings])
                return self.inspected

            with mock.patch.object(ci, "inspect_receipted_profile_qualification", side_effect=reader):
                bundle = parent / "with-reader.tar"
                pin = hosted.pack_profile(root, entry, bundle)
                root.rename(root.with_name("retained-original"))
                hosted.unpack_profile(bundle, pin, root, common_context=entry["inputs"])
            self.assertEqual((root / support).read_bytes(), contents[support])
            self.assertEqual((root / settings).read_bytes(), contents[settings])
            self.assertFalse((root / "unsafe.log").exists())

    def test_reader_failure_preserves_original_assertion_and_restores_all_observed_readers(self):
        import conformance_ci as ci
        import conformance_hosted as hosted
        import conformance_sdk_checks as sdk
        import conformance_sources as sources

        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root, entry, _, _, _ = self.fixture(parent)
            originals = (evidence._readonly_report_proof, sdk.read_bounded, sources.read_bounded)
            with mock.patch.object(ci, "inspect_receipted_profile_qualification",
                                   side_effect=evidence.ConformanceError("WitnessMissing")):
                with self.assertRaisesRegex(evidence.ConformanceError, "^WitnessMissing$"):
                    hosted.pack_profile(root, entry, parent / "failed.tar")
            self.assertFalse((parent / "failed.tar").exists())
            self.assertEqual(originals, (evidence._readonly_report_proof, sdk.read_bounded, sources.read_bounded))

    def test_external_reader_catalog_requires_exact_predeclared_source_hash_not_workspace_transport(self):
        import conformance_hosted as hosted
        import conformance_sdk_checks as sdk

        data = (ROOT / "README.md").read_bytes()
        for hashed in (hashlib.sha256(data).hexdigest(), "0" * 64):
            with self.subTest(hashed=hashed), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                with hosted._reader_files(root, {"README.md": hashed}) as files:
                    if hashed == "0" * 64:
                        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                            sdk.read_bounded(ROOT / "README.md", evidence.MAX_REPORT_BYTES)
                    else:
                        self.assertEqual(sdk.read_bounded(ROOT / "README.md", evidence.MAX_REPORT_BYTES), data)
                    self.assertEqual(files, {})

    def test_falsely_claimed_reader_dependency_is_rejected_by_the_unchanged_reader(self):
        import conformance_ci as ci
        import conformance_hosted as hosted

        with tempfile.TemporaryDirectory() as temporary:
            root, entry, pin, bundle, _ = self.fixture(Path(temporary).resolve())
            root.rename(root.with_name("retained-original"))

            def mutate(rows, manifest):
                path, raw = "proofs/unselected.json", b'{"safe":true}'
                hashed = hashlib.sha256(raw).hexdigest()
                manifest["files"][path] = {"sha256": hashed, "size": len(raw)}
                manifest["readerFiles"][path] = hashed
                return [rows[0], *sorted([*rows[1:], (path, raw)])]

            self.rewrite(bundle, pin, mutate)
            with mock.patch.object(ci, "inspect_receipted_profile_qualification", return_value=self.inspected):
                with self.assertRaisesRegex(evidence.ConformanceError, "^ProofMismatch$"):
                    hosted.unpack_profile(bundle, pin, root, common_context=entry["inputs"])

    def test_missing_failed_cancelled_upload_download_and_foreign_receipt_never_create_coordinator(self):
        import conformance_hosted as hosted

        for defect in ("failed", "cancelled", "skipped", "upload", "download", "producer",
                       "missing", "receipt", "assignment"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                staging = Path(temporary).resolve()
                _, _, pin, _, _ = self.fixture(staging)
                needs = {"assignment": {"result": "success"}}
                needs.update({profile: {"result": "success", "outputs": {
                    "producer": "success", "upload": "success",
                    "receipt": evidence.canonical_bytes({**pin, "profileId": profile}).decode("ascii"),
                }} for profile in evidence.PROFILES})
                downloads = {profile: "success" for profile in evidence.PROFILES}
                # This profile's original receipt kind must still match its independent slot.
                if defect in ("failed", "cancelled", "skipped"):
                    needs["metadata"]["result"] = defect
                elif defect in ("upload", "producer"):
                    needs["metadata"]["outputs"][defect] = "failure"
                elif defect == "download":
                    downloads["metadata"] = "failure"
                elif defect == "missing":
                    del needs["metadata"]
                elif defect == "receipt":
                    needs["metadata"]["outputs"]["receipt"] = "{}"
                else:
                    needs["assignment"]["result"] = "failure"
                with mock.patch.object(hosted, "admit_assignment", return_value={}), mock.patch.object(
                        hosted, "unpack_profile") as unpack, mock.patch.object(
                        hosted.ci, "inspect_offline") as inspect:
                    with self.assertRaises(evidence.ConformanceError):
                        hosted.aggregate(ROOT, {}, needs, downloads, staging)
                unpack.assert_not_called()
                inspect.assert_not_called()
                self.assertFalse((staging / "coordinator.json").exists())

    def test_original_hosted_completion_uses_exact_group_owner_and_native_object_for_each_profile(self):
        import conformance_ci as ci
        import conformance_composition_checks as composition
        import conformance_execution as execution
        import conformance_harness as harness
        import conformance_sdk_checks as sdk
        from test_conformance_evidence import ConformanceAdmissionTests

        sources = {"tests/contracts/Hoard.Testing.Conformance/Catalog/catalog.json": "a" * 64}
        identity = {"sourceRevision": "c" * 40, "sourceState": "clean-ci"}
        common = {
            **identity, "sourceManifestSha256": evidence.digest(sources),
            "catalogRevision": evidence.CATALOG_REVISION, "catalogSha256": "a" * 64,
            "sdkSha256": evidence.digest(sources), "invocationGroupId": str(uuid.uuid4()),
        }
        for profile in evidence.PROFILES:
            for defect in ("none", "producer", "foreign-native-input", "completion"):
                with self.subTest(profile=profile, defect=defect):
                    run = mock.Mock(root=Path("/modeled") / profile, state="Allocated", run_id=str(uuid.uuid4()))
                    run.live_children.return_value = []
                    run.transition.side_effect = lambda state: setattr(run, "state", state)
                    run.release.side_effect = lambda: setattr(run, "state", "Released")
                    native = object()
                    inputs = ConformanceAdmissionTests().inputs()
                    inputs.update(**common, profileId=profile, mode="qualification",
                                  sourceManifest=sources, runId=run.run_id, bindings=[])
                    inputs["budgets"]["profileSeconds"] = 3600
                    if defect == "foreign-native-input":
                        inputs["runId"] = str(uuid.uuid4())
                    origin = {
                        "kind": "native-" + ("category" if profile in ("metadata", "artifacts") else profile)
                        + "-fixture-qualification", "inputsSha256": evidence.digest(inputs),
                        "reportSha256": "d" * 64, "originalReportSha256": "e" * 64,
                        "originalReportPath": "proofs/original.json", "resourcesSha256": "f" * 64,
                    }
                    if profile == "compatibility":
                        origin.update(summaryPath="proofs/summary.json", summarySha256="a" * 64)

                    def complete(selected, observed):
                        self.assertIs(observed, native)
                        print(evidence.canonical_bytes({
                            "qualification": True, "profileId": profile,
                            "reportSha256": origin["reportSha256"], "qualificationOrigin": origin,
                        }).decode("ascii"))
                        return 2 if defect == "completion" else 0

                    producer = mock.Mock(return_value=native)
                    if defect == "producer":
                        producer.side_effect = RuntimeError("private-canary")
                    with mock.patch.dict(evidence.os.environ, {"GITHUB_ACTIONS": "true"}), mock.patch.object(
                            execution, "native_execution_supported", return_value=True), mock.patch.object(
                            evidence, "source_identity", return_value=identity), mock.patch.object(
                            evidence, "source_manifest", return_value=sources), mock.patch.object(
                            execution.OwnedRun, "allocate", return_value=run), mock.patch.object(
                            evidence, "admit_invocation", return_value=object()), mock.patch.object(
                            evidence, "_readonly_report_proof", return_value=("", evidence.canonical_bytes(inputs))), \
                            mock.patch.object(sdk, "execute_owned", producer), mock.patch.object(
                                composition, "execute_owned", producer), mock.patch.object(
                                harness, "execute_owned", producer), mock.patch.object(
                                evidence, "complete_native_category_invocation", side_effect=complete), mock.patch.object(
                                evidence, "complete_native_composition_invocation", side_effect=complete), mock.patch.object(
                                evidence, "complete_native_compatibility_invocation", side_effect=complete), mock.patch.object(
                                evidence, "complete_native_harness_invocation", side_effect=complete):
                        if defect == "none":
                            result = ci.execute_hosted_profile(ROOT, profile, run.root, common_context=common)
                            self.assertEqual(result["qualificationOrigin"], origin)
                        else:
                            with self.assertRaises(evidence.ConformanceError):
                                ci.execute_hosted_profile(ROOT, profile, run.root, common_context=common)
                    self.assertEqual(run.state, "Released")
                    args, options = producer.call_args
                    self.assertEqual(args, (ROOT, run))
                    self.assertEqual(options["group_id"], common["invocationGroupId"])
                    if profile != "harness":
                        self.assertTrue(options["qualify"])

    def test_capacity_failure_retains_measured_prerequisite_and_does_not_start_native_work(self):
        import conformance_hosted as hosted
        import conformance_sdk_checks as sdk
        from test_conformance_evidence import ConformanceAdmissionTests

        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary).resolve()
            profiles = staging / "private" / "profiles"
            observed = ConformanceAdmissionTests().inputs()["environment"]
            observed.update(runnerImage="ubuntu24.20261026.1.0", freeBytes=24 * 1024**3 - 1)
            with mock.patch.object(hosted, "admit_assignment", return_value={}), mock.patch.object(
                    hosted, "roots", return_value=profiles), mock.patch.dict(
                    os.environ, {"ImageOS": "ubuntu24", "ImageVersion": "20261026.1.0"}), mock.patch.object(
                    sdk, "probe", side_effect=lambda path: path.write_bytes(evidence.canonical_bytes(observed))), \
                    mock.patch.object(hosted.ci, "execute_hosted_profile") as execute:
                with self.assertRaisesRegex(evidence.ConformanceError, "^InsufficientCapacity$"):
                    hosted.produce(ROOT, "artifacts", {}, staging)
            execute.assert_not_called()
            summary = evidence.load_json((staging / "summary.json").read_bytes())
            self.assertFalse(summary["qualification"])
            self.assertEqual(summary["code"], "InsufficientCapacity")
            self.assertEqual(summary["environment"], observed)
            self.assertFalse((staging / "profile.tar").exists())

    def test_aggregate_uses_real_job_channels_and_public_original_receipt_reader(self):
        import conformance_ci as ci
        import conformance_hosted as hosted

        fixtures = ConformanceProfileTransportTests()
        fixtures.setUp()
        coordinator = fixtures.qualified_coordinator(fixtures.coordinator(), evidence.PROFILES)
        needs = {"assignment": {"result": "success"}}
        entries, pins = {}, {}
        for profile, entry in coordinator["profiles"].items():
            entry["reportPath"] = ci.profile_paths(profile)[1]
            entries[profile] = {key: value for key, value in entry.items() if key != "jobResults"}
            pin = {
                "schemaVersion": 1, "profileId": profile,
                "inputsSha256": evidence.digest(entry["inputs"]), "reportSha256": entry["reportSha256"],
                "qualificationOrigin": entry["qualificationOrigin"],
                "qualificationOriginSha256": evidence.digest(entry["qualificationOrigin"]),
                "transportSha256": "a" * 64, "manifestSha256": "b" * 64, "rootPathSha256": "c" * 64,
            }
            pins[profile] = pin
            needs[profile] = {"result": "success", "outputs": {
                "producer": "success", "upload": "success", "receipt": evidence.canonical_bytes(pin).decode()}}
        downloads = {profile: "success" for profile in evidence.PROFILES}
        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary).resolve()
            context = {"common": entries["metadata"]["inputs"]}

            def inspect(selected):
                self.assertEqual(selected.action, "aggregate")
                self.assertEqual(selected.input_path, staging / "private/profiles")
                trusted = ci.admit_coordinator(
                    evidence.load_json(selected.coordinator_path.read_bytes()), require_all=True)
                self.assertEqual(set(trusted["profiles"]), set(evidence.PROFILES))
                print('{"qualification":true,"code":"None","scope":"modeled-test-only"}')
                return 0

            def unpack(bundle, pin, root, **options):
                profile = root.name
                self.assertEqual(bundle, staging / "downloads" / profile / "profile.tar")
                self.assertEqual(pin, pins[profile])
                self.assertEqual(options["common_context"], context["common"])
                return entries[profile]

            with mock.patch.object(hosted, "admit_assignment", return_value=context), mock.patch.object(
                    hosted, "roots", return_value=staging / "private/profiles"), mock.patch.object(
                    hosted, "unpack_profile", side_effect=unpack) as reader, mock.patch.object(
                    ci, "inspect_offline", side_effect=inspect) as public, mock.patch.object(
                    evidence, "admit_invocation", side_effect=lambda repository, args: mock.Mock(
                        action="aggregate", input_path=Path(args[1]), coordinator_path=Path(args[3]))), \
                    contextlib.redirect_stdout(io.StringIO()):
                hosted.aggregate(ROOT, context, needs, downloads, staging)
            self.assertEqual(reader.call_count, 5)
            public.assert_called_once()

    def test_source_context_rejects_shallow_history_foreign_workflow_and_wrong_merge_head(self):
        import conformance_hosted as hosted

        revision, workflow, head = "a" * 40, "b" * 40, "c" * 40
        environ = {
            "GITHUB_ACTIONS": "true", "GITHUB_SHA": revision, "GITHUB_WORKFLOW_SHA": workflow,
            "HOARD_HEAD_SHA": head, "GITHUB_EVENT_NAME": "pull_request", "GITHUB_RUN_ID": "12",
            "GITHUB_RUN_ATTEMPT": "2",
        }
        for defect in ("none", "merge", "history", "workflow", "sha"):
            with self.subTest(defect=defect):
                selected = {**environ, "GITHUB_SHA": "unknown" if defect == "sha" else revision}

                def git(repository, args):
                    if args[0] == "rev-list":
                        return f'{revision} {"d" * 40} {head if defect != "merge" else "e" * 40}\n'.encode()
                    if args[0] == "rev-parse":
                        return b"true\n" if defect == "history" else b"false\n"
                    return b"foreign" if defect == "workflow" else b"exact-workflow"

                with mock.patch.dict(os.environ, selected), mock.patch.object(hosted, "_git", side_effect=git), \
                        mock.patch.object(hosted, "read_bounded", return_value=b"exact-workflow"), \
                        mock.patch.object(evidence, "source_identity", return_value={
                            "sourceRevision": revision, "sourceState": "clean-ci"}):
                    if defect == "none":
                        identity = hosted._host_identity(ROOT)
                        self.assertEqual(identity["sourceRevision"], revision)
                        self.assertEqual(identity["headRevision"], head)
                        self.assertEqual(identity["workflowRevision"], workflow)
                    else:
                        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
                            hosted._host_identity(ROOT)

    def test_unknown_driver_failures_emit_only_closed_incomplete_status_and_no_success_receipt(self):
        import conformance_hosted as hosted

        for error, code in ((OSError("private-error-canary"), "CommandFailed"),
                            (evidence.ConformanceError("UnknownDiagnostic"), "UnknownDiagnostic")):
            with self.subTest(code=code), mock.patch.object(
                    hosted, "assignment", side_effect=error), mock.patch.object(
                    hosted, "_outputs") as outputs, contextlib.redirect_stdout(io.StringIO()) as observed:
                self.assertEqual(hosted.main(["assignment"]), 2)
            outputs.assert_not_called()
            value = evidence.load_json(observed.getvalue().encode())
            self.assertEqual(value, {
                "schemaVersion": 1, "qualification": False, "state": "Incomplete", "code": code,
                "failurePhase": "boundary",
                "diagnostics": {"preflightReadCode": "None", "persistenceCode": "None"},
            })
            self.assertNotIn("private-error-canary", observed.getvalue())

    def test_programmer_failure_propagates_and_retains_safe_driver_failure_without_raw_error_text(self):
        import conformance_hosted as hosted

        error = AttributeError("private-error-canary")
        with mock.patch.object(hosted, "assignment", side_effect=error), mock.patch.object(
                hosted, "_outputs") as outputs, contextlib.redirect_stdout(io.StringIO()) as observed:
            with self.assertRaises(AttributeError) as raised:
                hosted.main(["assignment"])
        self.assertIs(raised.exception, error)
        outputs.assert_not_called()
        self.assertNotIn("private-error-canary", observed.getvalue())
        summary = evidence.load_json((ROOT / ".foundation/hosted/assignment/summary.json").read_bytes())
        self.assertEqual(summary["code"], "CommandFailed")
        self.assertEqual(summary["failurePhase"], "driver")
        self.assertFalse(summary["qualification"])
        with contextlib.redirect_stderr(io.StringIO()) as retained:
            hosted._unexpected_driver_failure(type(error), error, error.__traceback__)
        self.assertNotIn("private-error-canary", retained.getvalue())
        self.assertEqual(evidence.load_json(retained.getvalue().encode())["failurePhase"], "driver")

    def test_preflight_read_and_diagnostic_persistence_failures_are_explicit_without_masking_primary_failure(self):
        import conformance_hosted as hosted
        from test_conformance_evidence import ConformanceAdmissionTests

        for defect in ("read", "preflight", "persistence", "read-and-persistence"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "summary.json"
                preflight = ConformanceAdmissionTests().inputs()["environment"]
                if defect == "preflight":
                    preflight["private-unadmitted-canary"] = "not-public"
                path.write_bytes(evidence.canonical_bytes({"environment": preflight}))
                with contextlib.ExitStack() as stack:
                    if defect in ("read", "read-and-persistence"):
                        stack.enter_context(mock.patch.object(
                            hosted, "read_bounded", side_effect=OSError("private-read-canary")))
                    if defect in ("persistence", "read-and-persistence"):
                        stack.enter_context(mock.patch.object(
                            Path, "write_bytes", side_effect=OSError("private-write-canary")))
                    value = hosted._failure_projection(path, "WitnessMissing")
                self.assertEqual(value["code"], "WitnessMissing")
                self.assertFalse(value["qualification"])
                expected_read = ("CommandFailed" if defect in ("read", "read-and-persistence") else
                                 "EvidenceSchemaInvalid" if defect == "preflight" else "None")
                expected_write = "CommandFailed" if defect in ("persistence", "read-and-persistence") else "None"
                self.assertEqual(value["diagnostics"], {
                    "preflightReadCode": expected_read, "persistenceCode": expected_write})
                self.assertNotIn("canary", evidence.canonical_bytes(value).decode())
                if expected_write == "None":
                    self.assertEqual(evidence.load_json(path.read_bytes())["diagnostics"], value["diagnostics"])


class ConformanceProfileTransportTests(unittest.TestCase):
    def test_sequential_baseline_rejects_dirty_source_and_cannot_invent_hosted_transports(self):
        import conformance_ci as ci
        import conformance_execution as execution

        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            parent.chmod(0o700)
            invocation = evidence.admit_invocation(ROOT, ["--evidence", str(parent / "baseline")])
            for hosted, source, code in (("false", "dirty-local", "InputChanged"),
                                         ("true", "clean-ci", "UnsupportedProfile")):
                with self.subTest(hosted=hosted), mock.patch.dict(
                        evidence.os.environ, {"GITHUB_ACTIONS": hosted}), mock.patch.object(
                        execution, "native_execution_supported", return_value=True), mock.patch.object(
                        evidence, "source_identity", return_value={"sourceState": source}), mock.patch.object(
                        execution.OwnedRun, "allocate") as allocate:
                    with self.assertRaisesRegex(evidence.ConformanceError, "^" + code + "$"):
                        ci.execute_baseline(invocation)
                    allocate.assert_not_called()

    def test_original_local_baseline_uses_one_bounded_context_and_stops_on_the_first_failure(self):
        import conformance_ci as ci
        import conformance_composition_checks as composition
        import conformance_execution as execution
        import conformance_harness as harness
        import conformance_sdk_checks as sdk
        from test_conformance_evidence import ConformanceAdmissionTests

        sources = {"tests/contracts/Hoard.Testing.Conformance/Catalog/catalog.json": "a" * 64}
        identity = {"sourceRevision": "c" * 40, "sourceState": "clean-local"}
        original_allocate = execution.OwnedRun.allocate
        original_release = execution.OwnedRun.release
        for defect in ("none", "composition", "composition-legacy", "compatibility-legacy", "baseline-cleanup"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                parent = Path(temporary).resolve()
                parent.chmod(0o700)
                invocation = evidence.admit_invocation(ROOT, ["--evidence", str(parent / "baseline")])
                owners, calls = [], []

                def allocate(*args, **kwargs):
                    run = original_allocate(*args, **kwargs)
                    owners.append(run)
                    return run

                def release(owner):
                    if owner is owners[0] and defect == "baseline-cleanup":
                        owner.transition("Retained")
                        raise evidence.ConformanceError("CleanupIncomplete")
                    return original_release(owner)

                def produce(repository, child, **options):
                    profile = child.root.name
                    self.assertEqual(repository, ROOT)
                    self.assertEqual(child.state, "Allocated")
                    self.assertLessEqual(child.deadline, owners[0].deadline - 40)
                    calls.append((profile, options["group_id"]))
                    if profile == defect:
                        raise evidence.ConformanceError("PrerequisiteMissing")
                    if defect == profile + "-legacy":
                        raise RuntimeError("private-canary")
                    return object()

                def complete(selected, native):
                    child = owners[-1]
                    profile, = selected.profiles
                    inputs = ConformanceAdmissionTests().inputs()
                    inputs.update(
                        **identity, profileId=profile, mode="qualification", bindings=[],
                        sourceManifest=sources, sourceManifestSha256=evidence.digest(sources),
                        invocationGroupId=calls[-1][1], runId=child.run_id,
                        sdkSha256=evidence.digest(sources))
                    inputs["budgets"]["profileSeconds"] = execution.profile_budget(profile)
                    paths = {
                        "metadata": "proofs/category-metadata-qualification-run-inputs.json",
                        "artifacts": "proofs/category-artifacts-qualification-run-inputs.json",
                        "composition": "proofs/composition-inputs.json",
                        "compatibility": "proofs/compatibility-runtime-inputs.json",
                        "harness": harness.CATALOG_INPUTS,
                    }
                    sdk.write_new(child.root / paths[profile], evidence.canonical_bytes(inputs))
                    kind = ("native-category-fixture-qualification" if profile in ("metadata", "artifacts")
                            else "native-" + profile + "-fixture-qualification")
                    origin = {
                        "kind": kind, "inputsSha256": evidence.digest(inputs),
                        "reportSha256": "d" * 64, "originalReportSha256": "e" * 64,
                        "originalReportPath": "proofs/original.json", "resourcesSha256": "f" * 64,
                    }
                    if profile == "compatibility":
                        origin.update(summaryPath="proofs/summary.json", summarySha256="a" * 64)
                    print(evidence.canonical_bytes({
                        "qualification": True, "profileId": profile,
                        "reportSha256": origin["reportSha256"], "qualificationOrigin": origin,
                    }).decode())
                    return 0

                def aggregate(selected):
                    self.assertEqual(selected.action, "aggregate")
                    self.assertEqual(selected.input_path, parent / "baseline/proofs/profiles")
                    context = ci.admit_coordinator(
                        evidence.load_json(selected.coordinator_path.read_bytes()), require_all=True)
                    self.assertEqual(set(context["profiles"]), set(evidence.PROFILES))
                    self.assertTrue(all(owner.state == "Released" for owner in owners))
                    return 0

                with mock.patch.dict(evidence.os.environ, {"GITHUB_ACTIONS": "false"}), mock.patch.object(
                        execution, "native_execution_supported", return_value=True), mock.patch.object(
                        execution, "scratch_filesystem", return_value="test"), mock.patch.object(
                        execution.OwnedRun, "allocate", side_effect=allocate), mock.patch.object(
                        execution.OwnedRun, "release", autospec=True, side_effect=release), mock.patch.object(
                        evidence, "source_identity", return_value=identity), mock.patch.object(
                        evidence, "source_manifest", return_value=sources), mock.patch.object(
                        sdk, "execute_owned", side_effect=produce), mock.patch.object(
                        composition, "execute_owned", side_effect=produce), mock.patch.object(
                        harness, "execute_owned", side_effect=produce), mock.patch.object(
                        evidence, "complete_native_category_invocation", side_effect=complete), mock.patch.object(
                        evidence, "complete_native_composition_invocation", side_effect=complete), mock.patch.object(
                        evidence, "complete_native_compatibility_invocation", side_effect=complete), mock.patch.object(
                        evidence, "complete_native_harness_invocation", side_effect=complete), mock.patch.object(
                        evidence, "dispatch_invocation", side_effect=aggregate) as dispatch, contextlib.redirect_stdout(
                        io.StringIO()):
                    if defect == "none":
                        self.assertEqual(ci.execute_baseline(invocation), 0)
                        dispatch.assert_called_once()
                        self.assertEqual([profile for profile, _ in calls], list(evidence.PROFILES))
                    else:
                        code = ("CleanupIncomplete" if defect == "baseline-cleanup" else
                                "EvidenceIncomplete" if defect.endswith("-legacy") else "PrerequisiteMissing")
                        with self.assertRaisesRegex(evidence.ConformanceError, "^" + code + "$"):
                            ci.execute_baseline(invocation)
                        dispatch.assert_not_called()
                        expected = evidence.PROFILES if defect == "baseline-cleanup" else evidence.PROFILES[
                            :evidence.PROFILES.index(defect.removesuffix("-legacy")) + 1]
                        self.assertEqual([profile for profile, _ in calls], list(expected))
                        self.assertFalse((parent / "baseline/proofs/baseline-coordinator.json").exists())
                self.assertEqual(len({group for _, group in calls}), 1)
                self.assertEqual(owners[0].state, "Retained" if defect == "baseline-cleanup" else "Released")
                self.assertTrue(all(owner.state == "Released" for owner in owners[1:]))

    def setUp(self):
        from test_conformance_evidence import ConformanceAdmissionTests

        self.reports = {}
        self.inputs = {}
        self.jobs = {}
        for index, profile in enumerate(evidence.PROFILES):
            report = ConformanceAdmissionTests().report()
            inputs = report["inputs"]
            inputs.update(profileId=profile, mode="qualification", sourceState="clean-ci",
                          runId=str(uuid.uuid4()), bindings=[], invocation=["profile", profile])
            inputs["budgets"]["profileSeconds"] = 3600
            inputs["environment"]["freeBytes"] = (24 + index) * 1024**3
            inputs["environment"]["runnerImage"] = "runner-" + profile
            inputs["environmentSha256"] = evidence.digest(inputs["environment"])
            inputs["configurationSha256"] = hashlib.sha256(("configuration-" + profile).encode()).hexdigest()
            inputs["packages"][0]["sha256"] = hashlib.sha256(profile.encode()).hexdigest()
            case = catalog.expected_cases(profile)[0]
            report.update(state="Incomplete", qualification=False, witnesses=[], results=[{
                "runId": inputs["runId"], "profileId": profile, "bindingId": case.binding_id,
                "matrixId": case.matrix_id, "caseId": case.case_id, "status": "Incomplete",
                "applicable": True, "exclusionRule": "none", "proofSha256": [],
                "attempts": [{"sequence": 1, "startedMs": 0, "endedMs": 1,
                              "status": "Incomplete", "witnessIds": [], "proofSha256": [],
                              "diagnosticCode": "EvidenceIncomplete"}],
            }])
            report["postInputSha256"] = evidence.digest(inputs)
            self.reports[profile] = report
            self.inputs[profile] = copy.deepcopy(inputs)
            self.jobs[profile] = {"job": "success", "upload": "success", "download": "success"}

    def inspect(self):
        inspector = importlib.import_module("conformance_ci").inspect_profile_transports
        packets = {profile: evidence.canonical_bytes(report) for profile, report in self.reports.items()}
        pins = {profile: hashlib.sha256(raw).hexdigest() for profile, raw in packets.items()}
        return inspector(packets, expected_inputs=self.inputs, expected_report_sha256=pins,
                         job_results=self.jobs)

    def test_all_five_distinct_assignments_are_inspectable_but_cannot_qualify(self):
        observed = self.inspect()
        self.assertFalse(observed["qualification"])
        self.assertEqual(observed["code"], "EvidenceIncomplete")
        self.assertEqual(observed["scope"], "profile-transport-consistency-diagnostic")
        self.assertEqual(set(observed["profiles"]), set(evidence.PROFILES))
        self.assertEqual(len({row["environmentSha256"] for row in self.inputs.values()}), 5)
        self.assertEqual(len({row["packages"][0]["sha256"] for row in self.inputs.values()}), 5)
        self.assertEqual(len({row["configurationSha256"] for row in self.inputs.values()}), 5)
        self.assertNotIn(b"runner-", evidence.canonical_bytes(observed))

    def test_local_and_ci_use_the_same_independent_profile_inventories(self):
        ci = self.inspect()
        for profile in evidence.PROFILES:
            self.reports[profile]["inputs"]["sourceState"] = "clean-local"
            self.inputs[profile]["sourceState"] = "clean-local"
            self.reports[profile]["postInputSha256"] = evidence.digest(self.inputs[profile])
        local = self.inspect()
        self.assertEqual(local["expectedCaseCounts"], ci["expectedCaseCounts"])
        self.assertEqual(dict(local["expectedCaseCounts"]), {
            profile: len(catalog.expected_cases(profile)) for profile in evidence.PROFILES})
        self.assertFalse(local["qualification"])

    def test_missing_extra_and_misassigned_profiles_reject(self):
        for defect in ("report", "inputs", "job", "extra", "assignment"):
            with self.subTest(defect=defect):
                reports, inputs, jobs = copy.deepcopy((self.reports, self.inputs, self.jobs))
                if defect == "report":
                    del self.reports["harness"]
                elif defect == "inputs":
                    del self.inputs["harness"]
                elif defect == "job":
                    del self.jobs["harness"]
                elif defect == "extra":
                    self.reports["foreign"] = self.reports["metadata"]
                else:
                    self.reports["metadata"], self.reports["artifacts"] = (
                        self.reports["artifacts"], self.reports["metadata"])
                with self.assertRaises(evidence.ConformanceError):
                    self.inspect()
                self.reports, self.inputs, self.jobs = reports, inputs, jobs

    def test_job_upload_download_failure_cancellation_and_missing_status_reject(self):
        for phase in ("job", "upload", "download"):
            for status in ("failure", "cancelled", "skipped", "timed_out", "neutral", "", None):
                with self.subTest(phase=phase, status=status):
                    self.jobs["artifacts"][phase] = status
                    with self.assertRaises(evidence.ConformanceError):
                        self.inspect()
            del self.jobs["artifacts"][phase]
            with self.assertRaises(evidence.ConformanceError):
                self.inspect()
            self.jobs["artifacts"][phase] = "success"
        self.jobs["artifacts"]["unknown"] = "success"
        with self.assertRaises(evidence.ConformanceError):
            self.inspect()

    def test_foreign_common_context_rejects_even_when_each_assignment_matches(self):
        for field, value in (("invocationGroupId", str(uuid.uuid4())),
                             ("sourceRevision", "f" * 40), ("catalogSha256", "f" * 64),
                             ("sdkSha256", "f" * 64), ("sourceState", "clean-local")):
            with self.subTest(field=field):
                original = self.inputs["harness"][field]
                self.inputs["harness"][field] = value
                self.reports["harness"]["inputs"][field] = value
                with self.assertRaises(evidence.ConformanceError):
                    self.inspect()
                self.inputs["harness"][field] = original
                self.reports["harness"]["inputs"][field] = original

    def test_focused_preparation_dirty_and_changed_original_inputs_reject(self):
        for field, value in (("mode", "diagnostic"), ("mode", "preparation"),
                             ("sourceState", "dirty-local"), ("configurationSha256", "f" * 64),
                             ("environmentSha256", "f" * 64)):
            with self.subTest(field=field, value=value):
                original = self.reports["metadata"]["inputs"][field]
                self.reports["metadata"]["inputs"][field] = value
                with self.assertRaises(evidence.ConformanceError):
                    self.inspect()
                self.reports["metadata"]["inputs"][field] = original

    def test_matching_nonqualifying_assignments_reject_before_cross_profile_mismatch(self):
        for field, value in (("mode", "diagnostic"), ("mode", "preparation"), ("sourceState", "dirty-local")):
            reports, inputs = copy.deepcopy((self.reports, self.inputs))
            for profile in evidence.PROFILES:
                self.reports[profile]["inputs"][field] = value
                self.inputs[profile][field] = value
                self.reports[profile]["postInputSha256"] = evidence.digest(self.inputs[profile])
            with self.subTest(field=field, value=value), self.assertRaisesRegex(
                    evidence.ConformanceError, "^EvidenceIncomplete$"):
                self.inspect()
            self.reports, self.inputs = reports, inputs

    def test_foreign_evaluator_source_rejects_even_with_matching_revision_and_assignment(self):
        inputs = self.reports["harness"]["inputs"]
        inputs["sourceManifest"]["scripts/conformance_evidence.py"] = "f" * 64
        inputs["sourceManifestSha256"] = evidence.digest(inputs["sourceManifest"])
        self.inputs["harness"] = copy.deepcopy(inputs)
        self.reports["harness"]["postInputSha256"] = evidence.digest(inputs)
        with self.assertRaisesRegex(evidence.ConformanceError, "^InputChanged$"):
            self.inspect()

    def test_external_report_pins_and_unique_run_identities_are_required(self):
        inspector = importlib.import_module("conformance_ci").inspect_profile_transports
        packets = {profile: evidence.canonical_bytes(report) for profile, report in self.reports.items()}
        pins = {profile: hashlib.sha256(raw).hexdigest() for profile, raw in packets.items()}
        for defect in ("missing", "different", "bytes"):
            with self.subTest(defect=defect):
                changed, supplied = dict(packets), dict(pins)
                if defect == "missing":
                    del supplied["metadata"]
                elif defect == "different":
                    supplied["metadata"] = "f" * 64
                else:
                    changed["metadata"] += b"\n"
                with self.assertRaises(evidence.ConformanceError):
                    inspector(changed, expected_inputs=self.inputs, expected_report_sha256=supplied,
                              job_results=self.jobs)
        run_id = self.inputs["metadata"]["runId"]
        self.inputs["harness"]["runId"] = run_id
        self.reports["harness"]["inputs"]["runId"] = run_id
        self.reports["harness"]["results"][0]["runId"] = run_id
        with self.assertRaises(evidence.ConformanceError):
            self.inspect()

    def coordinator(self):
        configuration = {
            "revision": evidence.CATALOG_REVISION, "stores": "fresh-owned-synthetic",
            "restore": "locked", "runtimeLogger": "HoardSafe", "consoleLogger": False,
            "sources": {"packageSources": {
                "local": "isolated-current-archives", "nuget.org": "https://api.nuget.org/v3/index.json"},
                "packageSourceMapping": {"local": ["Hoard.*"], "nuget.org": ["*"]}}}
        profiles = {}
        for profile in evidence.PROFILES:
            selected = copy.deepcopy(configuration)
            if profile == "harness":
                selected["sources"] = {
                    "packageSources": {"frozen": "isolated-frozen-archives"},
                    "archives": {"Example.1.0.0.nupkg": "a" * 64}}
            self.inputs[profile]["configurationSha256"] = evidence.digest(selected)
            self.reports[profile]["inputs"]["configurationSha256"] = evidence.digest(selected)
            self.reports[profile]["postInputSha256"] = evidence.digest(self.inputs[profile])
            profiles[profile] = {
                "inputs": copy.deepcopy(self.inputs[profile]),
                "reportSha256": evidence.digest(self.reports[profile]),
                "reportPath": f"proofs/category-{profile}-qualification-report.json",
                "configuration": selected, "jobResults": copy.deepcopy(self.jobs[profile])}
        return {"schemaVersion": 1, "profiles": profiles}

    def test_coordinator_binds_configuration_preimages_without_equal_profile_fingerprints(self):
        ci = importlib.import_module("conformance_ci")
        context = self.coordinator()
        admitted = ci.admit_coordinator(context)
        self.assertNotEqual(admitted["profiles"]["metadata"]["inputs"]["configurationSha256"],
                            admitted["profiles"]["harness"]["inputs"]["configurationSha256"])
        self.assertEqual(admitted["configurationPolicySha256"], evidence.digest({
            "revision": evidence.CATALOG_REVISION, "stores": "fresh-owned-synthetic",
            "restore": "locked", "runtimeLogger": "HoardSafe", "consoleLogger": False}))
        context["profiles"]["metadata"]["configuration"]["restore"] = "unlocked"
        self.assertEqual(admitted["profiles"]["metadata"]["configuration"]["restore"], "locked")
        with self.assertRaises(evidence.ConformanceError):
            ci.admit_coordinator(context)

    def test_coordinator_rejects_foreign_configuration_policy_and_changed_preimages(self):
        ci = importlib.import_module("conformance_ci")
        original = self.coordinator()
        for defect in ("hash", "policy", "source", "field", "extra-profile", "duplicate-run", "version"):
            context = copy.deepcopy(original)
            entry = context["profiles"]["metadata"]
            if defect == "hash":
                entry["inputs"]["configurationSha256"] = "f" * 64
            elif defect == "policy":
                entry["configuration"]["consoleLogger"] = True
                entry["inputs"]["configurationSha256"] = evidence.digest(entry["configuration"])
            elif defect == "source":
                entry["configuration"]["sources"]["packageSources"]["local"] = "/private/canary"
                entry["inputs"]["configurationSha256"] = evidence.digest(entry["configuration"])
            elif defect == "field":
                entry["qualification"] = True
            elif defect == "extra-profile":
                context["profiles"]["service"] = copy.deepcopy(entry)
            elif defect == "duplicate-run":
                context["profiles"]["harness"]["inputs"]["runId"] = entry["inputs"]["runId"]
            else:
                context["schemaVersion"] = True
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                ci.admit_coordinator(context)

    def test_coordinator_configuration_preimage_preserves_opaque_inspection_assignments(self):
        ci = importlib.import_module("conformance_ci")
        context = self.coordinator()
        entry = context["profiles"]["metadata"]
        private = "/private/connection-canary/inspection.json"
        identity = next(iter(set(catalog.ORIGINAL_INSPECTION_WITNESSES)
                             - set(catalog.ORIGINAL_INSPECTION_LITERAL_WITNESSES)))
        configuration = evidence.configuration_record(
            entry["configuration"]["sources"], inspection_inputs={identity: {private: "a" * 64}})
        entry["configuration"] = configuration
        entry["inputs"]["configurationSha256"] = evidence.digest(configuration)
        admitted = ci.admit_coordinator(context)
        self.assertNotIn(private.encode(), evidence.canonical_bytes(admitted))
        files = configuration["inspectionInputs"][identity]
        self.assertEqual(files, {hashlib.sha256(private.encode()).hexdigest(): "a" * 64})
        configuration["inspectionInputs"][identity] = {private: "a" * 64}
        entry["inputs"]["configurationSha256"] = evidence.digest(configuration)
        with self.assertRaises(evidence.ConformanceError):
            ci.admit_coordinator(context)

    def test_coordinator_does_not_infer_missing_jobs_or_profiles_from_green_reports(self):
        ci = importlib.import_module("conformance_ci")
        original = self.coordinator()
        for defect in ("missing-profile", "job", "upload", "download", "missing-status"):
            context = copy.deepcopy(original)
            if defect == "missing-profile":
                del context["profiles"]["harness"]
            elif defect == "missing-status":
                del context["profiles"]["artifacts"]["jobResults"]["download"]
            else:
                context["profiles"]["artifacts"]["jobResults"][defect] = "cancelled"
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                ci.admit_coordinator(context, require_all=True)

    def qualification_origin(self, profile, entry):
        category = profile in ("metadata", "artifacts")
        original = (f"proofs/category-{profile}-qualification-report.json" if category
                    else f"proofs/{profile}-runtime-released-report.json")
        origin = {
            "kind": "native-" + ("category" if category else profile) + "-fixture-qualification",
            "inputsSha256": evidence.digest(entry["inputs"]), "reportSha256": entry["reportSha256"],
            "originalReportPath": original, "originalReportSha256": "a" * 64,
            "resourcesSha256": "b" * 64}
        if profile == "compatibility":
            origin.update(summaryPath="proofs/compatibility-diagnostic-summary.json",
                          summarySha256="c" * 64)
        return origin

    def qualified_coordinator(self, context, profiles):
        entries = {}
        for profile in profiles:
            entry = {key: value for key, value in context["profiles"][profile].items()
                     if key != "configuration"}
            entry["qualificationOrigin"] = self.qualification_origin(profile, entry)
            entries[profile] = entry
        return {"schemaVersion": 2, "configurationPolicy": dict(evidence.configuration_policy()), "profiles": entries}

    def test_coordinator_pins_external_original_receipts_and_freezes_their_fields(self):
        ci = importlib.import_module("conformance_ci")
        for profile in ("metadata", "artifacts", "composition", "compatibility"):
            with self.subTest(profile=profile):
                context = self.qualified_coordinator(self.coordinator(), (profile,))
                entry = context["profiles"][profile]
                admitted = ci.admit_coordinator(context)
                origin = admitted["profiles"][profile]["qualificationOrigin"]
                entry["qualificationOrigin"]["resourcesSha256"] = "d" * 64
                self.assertEqual(origin["resourcesSha256"], "b" * 64)
                for defect in ("inputsSha256", "reportSha256", "kind", "extra"):
                    changed = copy.deepcopy(context)
                    candidate = changed["profiles"][profile]["qualificationOrigin"]
                    candidate[defect] = "f" * 64
                    with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                        ci.admit_coordinator(changed)

    def test_public_verify_uses_only_the_separately_trusted_receipt_and_exact_assignment(self):
        import conformance_cli

        with tempfile.TemporaryDirectory() as temporary:
            directory, coordinator, context = self.aggregate_fixture(Path(temporary).resolve())
            context = self.qualified_coordinator(context, ("composition",))
            entry = context["profiles"]["composition"]
            coordinator.write_bytes(evidence.canonical_bytes(context))
            report = directory / "composition" / entry["reportPath"]
            raw = report.read_bytes()
            output = io.StringIO()
            with mock.patch("conformance_ci.inspect_receipted_profile_qualification", return_value={
                    "qualification": True, "baselineQualification": False, "code": "None",
                    "profileId": "composition", "reportSha256": entry["reportSha256"]}) as reader:
                with contextlib.redirect_stdout(output):
                    result = conformance_cli.main([
                        "--verify", str(report), "--coordinator", str(coordinator)])
            self.assertEqual(result, 0)
            reader.assert_called_once_with(
                directory / "composition", raw, expected_inputs=evidence.admit_entity("RunInputs", entry["inputs"]),
                expected_report_sha256=entry["reportSha256"],
                qualification_origin=evidence.admit_qualification_origin(
                    entry["qualificationOrigin"], profile="composition"))
            packet = json.loads(output.getvalue())
            self.assertTrue(packet["qualification"])
            self.assertFalse(packet["baselineQualification"])
            self.assertNotIn(str(directory), output.getvalue())

    def test_native_local_assignments_do_not_invent_ci_transfer_status_or_allow_ci_omission(self):
        ci = importlib.import_module("conformance_ci")
        context = self.qualified_coordinator(self.coordinator(), ("metadata",))
        entry = context["profiles"]["metadata"]
        entry["jobResults"].update(upload="not-required", download="not-required")
        with self.assertRaises(evidence.ConformanceError):
            ci.admit_coordinator(context)
        entry["inputs"]["sourceState"] = "clean-local"
        entry["qualificationOrigin"]["inputsSha256"] = evidence.digest(entry["inputs"])
        admitted = ci.admit_coordinator(context)
        self.assertEqual(admitted["profiles"]["metadata"]["jobResults"]["upload"], "not-required")
        entry["jobResults"]["job"] = "cancelled"
        with self.assertRaises(evidence.ConformanceError):
            ci.admit_coordinator(context)

    def test_receipted_coordinator_requires_the_common_policy_and_clean_qualifying_inputs(self):
        ci = importlib.import_module("conformance_ci")
        original = self.qualified_coordinator(self.coordinator(), ("metadata",))
        for defect in ("policy", "diagnostic", "preparation", "dirty", "missing-receipt", "extra"):
            context = copy.deepcopy(original)
            entry = context["profiles"]["metadata"]
            if defect == "policy":
                context["configurationPolicy"]["restore"] = "unlocked"
            elif defect in ("diagnostic", "preparation"):
                entry["inputs"]["mode"] = defect
            elif defect == "dirty":
                entry["inputs"]["sourceState"] = "dirty-local"
            elif defect == "missing-receipt":
                del entry["qualificationOrigin"]
            else:
                context["qualification"] = True
            with self.subTest(defect=defect), self.assertRaises(evidence.ConformanceError):
                ci.admit_coordinator(context)

    def test_receipted_dispatch_rejects_missing_authority_and_unimplemented_harness(self):
        context = self.coordinator()
        for profile in evidence.PROFILES:
            entry = context["profiles"][profile]
            with self.subTest(profile=profile), self.assertRaises(evidence.ConformanceError):
                evidence.inspect_receipted_profile_qualification(
                    Path("."), evidence.canonical_bytes(self.reports[profile]),
                    expected_inputs=entry["inputs"], expected_report_sha256=entry["reportSha256"],
                    qualification_origin=None)

    def test_receipted_aggregate_cannot_promote_four_profiles_without_harness_authority(self):
        import conformance_cli

        with tempfile.TemporaryDirectory() as temporary:
            directory, coordinator, context = self.aggregate_fixture(Path(temporary).resolve())
            context = self.qualified_coordinator(
                context, ("metadata", "artifacts", "composition", "compatibility"))
            coordinator.write_bytes(evidence.canonical_bytes(context))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = conformance_cli.main([
                    "--aggregate", str(directory), "--coordinator", str(coordinator)])
            packet = json.loads(output.getvalue())
            self.assertNotEqual(result, 0)
            self.assertFalse(packet["qualification"])
            self.assertEqual(packet["code"], "EvidenceIncomplete")

    def aggregate_fixture(self, parent):
        context = self.coordinator()
        directory = parent / "profiles"
        directory.mkdir()
        for profile in evidence.PROFILES:
            root = directory / profile
            (root / "proofs").mkdir(parents=True)
            entry = context["profiles"][profile]
            inputs = entry["inputs"]
            completion = f"proofs/category-{profile}-qualification-completion-inputs.json"
            (root / completion).write_bytes(evidence.canonical_bytes(inputs))
            (root / completion).chmod(0o400)
            attempt = {
                "sequence": 1, "startedMs": 0, "endedMs": 1, "status": "Incomplete",
                "witnessIds": [], "proofSha256": [], "diagnosticCode": "EvidenceIncomplete"}
            report = {
                **self.reports[profile], "inputs": inputs, "postInputSha256": evidence.digest(inputs),
                "proofs": {completion: evidence.digest(inputs)},
                "results": [evidence._catalog_case_result(
                    inputs, case, "NotApplicable" if case.exclusion else "Incomplete",
                    () if case.exclusion else (attempt,)) for case in catalog.expected_cases(profile)]}
            raw = evidence.canonical_bytes(report)
            (root / entry["reportPath"]).write_bytes(raw)
            entry["reportSha256"] = hashlib.sha256(raw).hexdigest()
        coordinator = parent / "trusted-coordinator.json"
        coordinator.write_bytes(evidence.canonical_bytes(context))
        return directory, coordinator, context

    def test_public_aggregate_checks_all_five_complete_inventories_but_never_qualifies_empty_models(self):
        import conformance_cli

        with tempfile.TemporaryDirectory() as temporary:
            directory, coordinator, context = self.aggregate_fixture(Path(temporary).resolve())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = conformance_cli.main([
                    "--aggregate", str(directory), "--coordinator", str(coordinator)])
            self.assertEqual(result, 2)
            packet, = (json.loads(row) for row in output.getvalue().splitlines())
            self.assertFalse(packet["qualification"])
            self.assertEqual(packet["scope"], "five-profile-structure-diagnostic")
            self.assertEqual(set(packet["profiles"]), set(evidence.PROFILES))
            for profile, observed in packet["profiles"].items():
                self.assertEqual(observed["caseCount"], len(catalog.expected_cases(profile)))
                self.assertEqual(observed["caseStates"]["Passed"], 0)
                self.assertEqual(observed["reportSha256"], context["profiles"][profile]["reportSha256"])
            self.assertNotIn(str(directory), output.getvalue())

    def test_aggregate_rejects_resealed_missing_cases_in_each_profile(self):
        import conformance_cli

        for profile in evidence.PROFILES:
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temporary:
                directory, coordinator, context = self.aggregate_fixture(Path(temporary).resolve())
                entry = context["profiles"][profile]
                path = directory / profile / entry["reportPath"]
                report = json.loads(path.read_bytes())
                report["results"].pop()
                path.write_bytes(evidence.canonical_bytes(report))
                entry["reportSha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                coordinator.write_bytes(evidence.canonical_bytes(context))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result = conformance_cli.main([
                        "--aggregate", str(directory), "--coordinator", str(coordinator)])
                self.assertEqual(result, 1)
                packet, = (json.loads(row) for row in output.getvalue().splitlines())
                self.assertEqual(packet["code"], "WitnessMissing")
                self.assertFalse(packet["qualification"])
                self.assertNotIn("profiles", packet)

    def test_aggregate_keeps_failed_attempt_after_passing_modeled_retry(self):
        import conformance_cli

        with tempfile.TemporaryDirectory() as temporary:
            directory, coordinator, context = self.aggregate_fixture(Path(temporary).resolve())
            entry = context["profiles"]["harness"]
            path = directory / "harness" / entry["reportPath"]
            report = json.loads(path.read_bytes())
            inputs = report["inputs"]
            result = next(row for row in report["results"] if row["caseId"] == "QC-38")
            result["attempts"][0].update(status="Failed", diagnosticCode="AssertionFailed")
            execution = str(uuid.uuid4())
            raw, relative = b"modeled-retry-proof", "proofs/modeled-retry.json"
            proof = directory / "harness" / relative
            proof.write_bytes(raw)
            proof.chmod(0o400)
            hashed = hashlib.sha256(raw).hexdigest()
            report["proofs"][relative] = hashed
            report["witnesses"] = [{
                "executionId": execution, "runId": inputs["runId"],
                "invocationGroupId": inputs["invocationGroupId"], "testIdentity": "Modeled.Retry",
                "bindingId": "none", "matrixId": "none", "packageSha256": inputs["packages"][0]["sha256"],
                "assemblySha256": next(iter(inputs["runtimeAssemblies"].values())),
                "inputSha256": evidence.digest(inputs), "startedMs": 2, "endedMs": 3,
                "status": "Passed", "proofSha256": hashed}]
            result.update(status="Passed", proofSha256=[hashed])
            result["attempts"].append({
                "sequence": 2, "startedMs": 2, "endedMs": 3, "status": "Passed",
                "witnessIds": [execution], "proofSha256": [hashed], "diagnosticCode": "None"})
            path.write_bytes(evidence.canonical_bytes(report))
            entry["reportSha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            coordinator.write_bytes(evidence.canonical_bytes(context))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = conformance_cli.main([
                    "--aggregate", str(directory), "--coordinator", str(coordinator)])
            self.assertEqual(result, 1)
            packet, = (json.loads(row) for row in output.getvalue().splitlines())
            self.assertEqual(packet["code"], "AssertionFailed")
            self.assertEqual(packet["profiles"]["harness"]["failedAttemptCount"], 1)
            self.assertFalse(packet["qualification"])


if __name__ == "__main__":
    unittest.main()
