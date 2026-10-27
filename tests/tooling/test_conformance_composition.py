import contextlib
import io
from pathlib import Path
import sys
import tempfile
import textwrap
from types import MappingProxyType, SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


class CompositionDiagnosticTests(unittest.TestCase):
    def test_prepared_formatting_requires_exact_native_receipts_and_unchanged_closure(self):
        import hashlib
        import time
        import conformance_composition_checks as checks
        import conformance_evidence as evidence
        for mutation in ("none", "foreign-root", "argv", "cwd", "inputs", "sequence", "hash",
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
                    self.assertEqual(4, len(kwargs["execution_inputs"]))
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
                if mutation == "none":
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        observed = checks._format_prepared_controllers(run, controllers, files, closure)
                    self.assertFalse(observed["qualification"])
                    self.assertFalse(observed["solutionFormatting"])
                    self.assertEqual(list(projects), [row["controller"] for row in observed["commands"]])
                    self.assertEqual(4, run.command.call_count)
                    self.assertEqual([
                        {"qualification": False, "phase": "inherited-prepared-formatting",
                         "controller": phase, "command": number}
                        for number, phase in enumerate(projects, 1)
                    ], [evidence.load_json(line.encode()) for line in output.getvalue().splitlines()])
                else:
                    code = ("InputChanged" if mutation.startswith("changed-") or mutation == "symlink" else
                            "CommandFailed" if mutation == "failed" else
                            "EvidenceSchemaInvalid" if mutation == "missing-phase" else "ProofMismatch")
                    with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(
                            evidence.ConformanceError, code):
                        checks._format_prepared_controllers(run, controllers, files, closure)
                    if mutation in ("duplicate", "missing-phase", "missing-assets"):
                        run.command.assert_not_called()

    def test_controller_failure_exposes_only_revalidated_closed_progress(self):
        import conformance_composition_checks as checks
        import conformance_evidence as evidence
        for private in (False, True):
            with self.subTest(private=private), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                for directory in ("proofs", "diagnostics", "source/scripts"):
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
        for mutation in ("none", "changed-output", "missing-phase", "retained-process", "child-failed"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                source = root / "stores/source"
                (source / "scripts").mkdir(parents=True)
                (source / "scripts/conformance_inherited.py").write_bytes(b"frozen controller")
                run = SimpleNamespace(root=root, run_id="run", root_id="root", command_sequence=0)
                record = {}

                def command(arguments, **kwargs):
                    request = Path(arguments[arguments.index("--request") + 1])
                    output = Path(arguments[arguments.index("--output") + 1])
                    raw = evidence.canonical_bytes({
                        "schemaVersion": 1, "qualification": False, "phase": "historical",
                        "runId": "run", "rootId": "root", "result": {"seal": "bound"},
                    })
                    output.write_bytes(raw + b"\n" if mutation == "changed-output" else raw)
                    record.update(
                        runId="run", rootId="root", argvSha256=evidence.digest(arguments),
                        cwdSha256=hashlib.sha256(str(source).encode()).hexdigest(),
                        inputFiles={path: evidence.file_sha256(root / path) for path in kwargs["execution_inputs"]},
                        outputFiles={output.relative_to(root).as_posix(): hashlib.sha256(raw).hexdigest()},
                        groupState="Retained" if mutation == "retained-process" else "Exited",
                        exitCode=0, diagnosticCode="None",
                    )
                    self.assertIn(request.relative_to(root).as_posix(), kwargs["execution_inputs"])
                    self.assertEqual((output.relative_to(root).as_posix(),), kwargs["execution_outputs"])
                    run.command_sequence = 1
                    events = tuple({"event": "control", "code": "None", "value": number}
                                   for number in ((2, 4, 0) if mutation == "missing-phase" else (2, 3, 4, 0)))
                    if mutation == "child-failed":
                        events = (*events[:2], MappingProxyType({
                            "event": "control", "code": "OutputLimitExceeded", "value": 0}))
                    return CommandResult(0, events, 1, evidence.digest(record))

                run.command = mock.Mock(side_effect=command)
                run.read_execution_record = mock.Mock(side_effect=lambda sequence: evidence.canonical_bytes(record))
                if mutation == "none":
                    result, parent = checks._controller_phase(run, ROOT, source, "historical")
                    self.assertEqual({"seal": "bound"}, result)
                    self.assertEqual(evidence.digest(record), parent)
                else:
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output), self.assertRaisesRegex(
                            evidence.ConformanceError, "OutputLimitExceeded" if mutation == "child-failed"
                            else "ProofMismatch"):
                        checks._controller_phase(run, ROOT, source, "historical")
                    if mutation == "child-failed":
                        self.assertEqual([2, 3, 0], [event["value"] for event in
                                                   evidence.load_json(output.getvalue().encode())["events"]])

    def test_workflow_checks_retained_historical_seal_after_stores_are_released(self):
        import hashlib
        import conformance_evidence as evidence
        import conformance_inherited as inherited
        workflow = (ROOT / ".github/workflows/conformance-composition.yml").read_text()
        script = workflow.split("<<'PY'\n", 1)[1].split("\n          PY", 1)[0]
        code = compile(textwrap.dedent(script), "<composition-workflow>", "exec")
        for mutation in ("none", "changed-bytes", "resealed-foreign-root", "false-qualification"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "proofs").mkdir()
                inputs = {"runId": "run", "sourceRevision": "a" * 40, "sourceState": "clean-ci",
                          "mode": "diagnostic", "profileId": "composition"}
                baseline = {"runId": "run", "rootId": "root", "qualification": False,
                            "nativeContainment": False, "mode": "preparation",
                            "schemaVersion": 1, "baselineRevision": inherited.BASELINE,
                            "recipeSourceSha256": "b" * 64, "files": {}, "retained": {},
                            "registration": {"assembly": str(root / "stores/old/RegistrationConsumer.dll"),
                                             "sha256": "c" * 64}}
                for phase, revision, names in (
                        ("configuration", "b80c69fc386541be4f56f6ef2edeca40f43a0e1c",
                         ("LegacyOptions", "LifecycleConsumer")),
                        ("discovery", "7fd73267a5154583363c94e9e85b9bac7d4a16b3",
                         ("RetainedLifecycle", "RetainedConfiguration", "LegacyOptions"))):
                    baseline["retained"][phase] = [{
                        "name": name, "baseline": revision, "assembly": str(root / f"stores/{phase}/{name}.dll"),
                        "assets": str(root / f"stores/{phase}/{name}.assets.json"), "sha256": "c" * 64,
                    } for name in names]
                for entry in (baseline["registration"], *baseline["retained"]["configuration"],
                              *baseline["retained"]["discovery"]):
                    for field in ("assembly", "assets"):
                        if field in entry:
                            baseline["files"][Path(entry[field]).relative_to(root).as_posix()] = "c" * 64
                if mutation == "resealed-foreign-root":
                    baseline["rootId"] = "foreign-root"
                elif mutation == "false-qualification":
                    baseline["qualification"] = True
                raw = evidence.canonical_bytes(baseline)
                summary = {
                    "qualification": False, "profileComplete": False, "passedComponents": 36,
                    "admittedSnapshots": 110, "processResourcesReleased": True,
                    "inputSha256": evidence.digest(inputs),
                    "inheritedRuntime": {
                        "qualification": False, "profileComplete": False, "executionComplete": True,
                        "nativeContainment": True, "controllerNativeContainment": False,
                        "fullControllerAcceptance": False, "historicalBinariesPreparedBeforeCandidate": True,
                        "historicalBaselineSealSha256": hashlib.sha256(raw).hexdigest(),
                        "passedParameters": 525, "scopes": 58, "commands": [{}] * 58,
                    },
                }
                (root / inherited.CONTROLLER_BASELINES).write_bytes(
                    raw + b"\n" if mutation == "changed-bytes" else raw)
                for path, value in (("proofs/composition-diagnostic-summary.json", summary),
                                    ("proofs/composition-inputs.json", inputs),
                                    ("runtime-owner.json", {"runId": "run", "rootId": "root"})):
                    (root / path).write_bytes(evidence.canonical_bytes(value))
                output = io.StringIO()
                with mock.patch.object(sys, "argv", ["workflow", str(root), "a" * 40]), mock.patch.object(
                        evidence, "admit_entity", side_effect=lambda kind, value: value), \
                        contextlib.redirect_stdout(output):
                    if mutation == "none":
                        exec(code, {"__name__": "__main__"})
                        self.assertEqual({"qualification": False, "status": "Incomplete",
                                          "code": "EvidenceIncomplete"},
                                         evidence.load_json(output.getvalue().encode()))
                    else:
                        with self.assertRaisesRegex(SystemExit, "WitnessMissing"):
                            exec(code, {"__name__": "__main__"})
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


if __name__ == "__main__":
    unittest.main()
