"""Original harness observations; component success is not profile qualification."""

import hashlib
import os
from pathlib import Path
from types import MappingProxyType
import uuid

import conformance_evidence as evidence
from conformance_case_catalog import catalog_admission_witnesses
from conformance_execution import OwnedRun
from conformance_sources import runtime_arguments, runtime_runner, runtime_settings


CATALOG_FRAME = "proofs/harness-catalog.json"
CATALOG_INPUTS = "proofs/harness-inputs.json"
FROZEN_INPUTS = "proofs/harness-frozen-inputs/"
CONTRIBUTOR_FRAME = "proofs/harness-contributors.json"
CATEGORY_CONTROL_FRAME = "proofs/harness-category-controls.json"


def _frozen_inputs(inputs):
    return {
        **inputs["runtimeAssemblies"], **inputs["locks"],
        **{f'feed/candidate/{row["packageId"]}.{row["version"]}.nupkg': row["sha256"]
           for row in inputs["packages"]},
    }


def _catalog_manifest(inputs, assembly, attempt):
    identities = catalog_admission_witnesses()
    package = next((row for row in inputs["packages"]
                    if row["packageId"] == "Hoard.Testing.Conformance"), None)
    if package is None or assembly not in inputs["runtimeAssemblies"]:
        raise evidence.ConformanceError("InputChanged")
    return {
        "schemaVersion": 1, "runId": inputs["runId"], "invocationGroupId": inputs["invocationGroupId"],
        "attemptId": evidence._uuid(attempt), "attemptSequence": 1, "purpose": "execution",
        "inputSha256": evidence.digest(inputs), "runInputsPath": CATALOG_INPUTS,
        "assemblies": [{"id": "test-assembly", "path": assembly,
                        "sha256": inputs["runtimeAssemblies"][assembly]}],
        "packages": [{"id": package["packageId"],
                      "path": f'feed/candidate/{package["packageId"]}.{package["version"]}.nupkg',
                      "sha256": package["sha256"]}],
        "expected": [{
            "testIdentity": identity, "fullyQualifiedName": identity.split("(")[0],
            "assemblyId": "test-assembly", "packageId": package["packageId"],
            "bindingId": "none", "matrixId": "none", "assertionSymbol": None, "caseId": "QC-01",
        } for identity in identities],
    }


def prepare_catalog(repository, run, *, group_id):
    import conformance_baselines as baselines
    import conformance_sdk_checks as sdk
    from conformance_prepare import Project, build_project
    from conformance_sources import read_bounded

    if type(run) is not OwnedRun or run.state != "Active":
        raise evidence.ConformanceError("OwnershipInvalid")
    group_id = evidence._uuid(group_id)
    (run.root / "cache/.local/share").mkdir(parents=True, mode=0o700)
    (run.root / "cache/.local").chmod(0o700)
    source, sources = evidence.snapshot_sources(repository, run, transient=True)
    observed = sdk.environment(run, scope="build")
    msbuild = sdk.selected_msbuild(observed)
    configuration, feed = baselines._config(run, "candidate")
    projects = (
        Project("src/Hoard.Abstractions/Hoard.Abstractions.csproj", "Hoard.Abstractions"),
        Project(sdk.SDK + "/Hoard.Testing.Conformance.csproj", "Hoard.Testing.Conformance"),
        Project(sdk.LOGGER + "/Hoard.Conformance.TestLogger.csproj", "Hoard.Conformance.TestLogger"),
        Project(sdk.TESTS + "/Hoard.Conformance.Tests.csproj"),
    )
    for project in projects:
        build_project(run, source, project, configuration, feed,
                      update=False, historical_lock=True, msbuild=msbuild)
    _, runner_material = sdk.runtime_runner_material(observed)
    sdk.write_new(run.root / "proofs/sdk-vstest-inputs.json", runner_material)
    runtime = {}
    for folder in (sdk.TESTS, sdk.LOGGER):
        prefix = (source / folder / "bin/Release/net10.0").relative_to(run.root).as_posix()
        runtime.update({
            prefix + "/" + path: hashed
            for path, hashed in evidence.proof_manifest(run.root / prefix).items()
            if path.endswith((".dll", ".deps.json", ".runtimeconfig.json", ".so", ".dylib"))
        })
    runtime["proofs/sdk-vstest-inputs.json"] = hashlib.sha256(runner_material).hexdigest()
    source_prefix = source.relative_to(run.root).as_posix()
    locks = [source_prefix + "/" + path for path in evidence.proof_manifest(
        source, include_file=lambda path: path.endswith("packages.lock.json"))]
    capture = {
        "profile_id": "harness", "mode": "qualification", "invocation_group_id": group_id,
        "package_versions": [{"packageId": row.package, "version": "0.1.0"}
                             for row in projects if row.package is not None],
        "feed": feed.relative_to(run.root).as_posix(),
        "configuration": configuration.relative_to(run.root).as_posix(),
        "lock_paths": locks, "runtime_paths": list(runtime), "binding_sources": [],
        "observed_environment": observed, "budgets": {**sdk.BUDGETS, "profileSeconds": 3600},
        "invocation": ["profile", "harness", "native-source-admission"],
        "ci_revision": os.environ.get("GITHUB_SHA") if os.environ.get("GITHUB_ACTIONS") == "true" else None,
    }
    if os.environ.get("GITHUB_ACTIONS") == "true" and capture["ci_revision"] is None:
        raise evidence.ConformanceError("InputChanged")
    inputs = evidence.capture_profile_inputs(run, repository, source, **capture)
    if inputs["sourceManifest"] != sources or inputs["runtimeAssemblies"] != runtime:
        raise evidence.ConformanceError("InputChanged")
    sdk.write_new(run.root / CATALOG_INPUTS, evidence.canonical_bytes(inputs))
    (run.root / FROZEN_INPUTS).mkdir(mode=0o700)
    for relative, hashed in _frozen_inputs(inputs).items():
        (run.root / relative).chmod(0o400)
        target = run.root / (FROZEN_INPUTS + hashed)
        if not target.exists():
            sdk.write_new(target, read_bounded(run.root / relative, evidence.MAX_PROOF_BYTES))
    # Configuration identity hashes normalized policy, not the XML bytes.
    sdk.write_new(run.root / (FROZEN_INPUTS + inputs["configurationSha256"]),
                  read_bounded(configuration, 64 * 1024))
    sdk.write_new(run.root / "runtime-owner.json", evidence.canonical_bytes({
        "schemaVersion": 1, "runId": run.run_id, "invocationGroupId": group_id,
        "rootId": run.root_id, "rootPathSha256": hashlib.sha256(str(run.root).encode()).hexdigest(),
    }))
    assembly = source_prefix + "/" + sdk.TESTS + "/bin/Release/net10.0/Hoard.Conformance.Tests.dll"
    return inputs, assembly, source, capture


def execute_catalog(run, inputs, assembly):
    import conformance_sdk_checks as sdk

    inputs = evidence.admit_entity("RunInputs", inputs)
    if (type(run) is not OwnedRun or run.state != "Active"
            or inputs["profileId"] != "harness" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id):
        raise evidence.ConformanceError("OwnershipInvalid")
    manifest = _catalog_manifest(inputs, evidence.relative_path(assembly), str(uuid.uuid4()))
    expected = {identity: ("none", "none") for identity in catalog_admission_witnesses()}
    result, observed, transport, _ = sdk._execute_runtime_transport(
        run, inputs, run.root / assembly, manifest, expected, {"category_scope": ("harness", "catalog")})
    sdk.validate_observation(
        observed, result, tuple(expected), "None", "Passed", 0, transport["proofs"], "None")
    if result.execution_record_sha256 is None:
        raise evidence.ConformanceError("OwnershipInvalid")
    for purpose, bounds in transport["nativeTransports"].items():
        folder = run.root / (("discovery-" if purpose == "discovery" else "runtime-") + bounds["attemptId"])
        names = ({"completion.json", "discovered.jsonl"} if purpose == "discovery" else
                 {"completion.json", "witnesses.jsonl", *transport["proofs"]})
        for name in names:
            (folder / name).chmod(0o400)
    sdk.write_new(run.root / CATALOG_FRAME, evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False, "scope": "harness-native-catalog",
        "inputsSha256": evidence.digest(inputs), "assemblyPath": assembly, **transport["nativeTransports"],
    }))
    inspected = inspect_catalog(run.root, inputs)
    if tuple(inspected["witnesses"]) != tuple(observed["witnesses"]):
        raise evidence.ConformanceError("ProofMismatch")
    return inspected


def inspect_catalog(root, inputs):
    import conformance_sdk_checks as sdk

    root = Path(root)
    inputs = evidence.admit_entity("RunInputs", inputs)
    if inputs["profileId"] != "harness" or inputs["mode"] != "qualification":
        raise evidence.ConformanceError("UnsupportedProfile")
    hashes = {}

    def read(path, limit=evidence.MAX_REPORT_BYTES):
        hashed, raw = evidence._readonly_report_proof(root, path)
        if len(raw) > limit:
            raise evidence.ConformanceError("OutputLimitExceeded")
        hashes[path] = hashed
        return raw

    phase = evidence._record({
        "attemptId": evidence._uuid, "startedMs": evidence._number, "endedMs": evidence._number})
    frame = evidence._runtime_json(read(CATALOG_FRAME), {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "scope": evidence._constant("harness-native-catalog"),
        "inputsSha256": evidence._constant(evidence.digest(inputs)),
        "assemblyPath": evidence.relative_path, "discovery": phase, "execution": phase,
    })
    if (frame["discovery"]["attemptId"] == frame["execution"]["attemptId"]
            or frame["discovery"]["endedMs"] > frame["execution"]["startedMs"]
            or any(not 0 <= bounds["endedMs"] - bounds["startedMs"]
                   <= min(180, inputs["budgets"]["childSeconds"]) * 1000
                   for bounds in (frame["discovery"], frame["execution"]))):
        raise evidence.ConformanceError("ProofMismatch")
    if evidence.canonical_bytes(inputs) != read(CATALOG_INPUTS):
        raise evidence.ConformanceError("InputChanged")
    for hashed in set(_frozen_inputs(inputs).values()):
        if hashlib.sha256(read(FROZEN_INPUTS + hashed, evidence.MAX_PROOF_BYTES)).hexdigest() != hashed:
            raise evidence.ConformanceError("InputChanged")
    configuration = read(FROZEN_INPUTS + inputs["configurationSha256"], 64 * 1024)
    if (configuration != evidence.synthetic_nuget_configuration(root / "feed/candidate")
            or inputs["configurationSha256"] != evidence.configuration_fingerprint(evidence.synthetic_source_mapping())):
        raise evidence.ConformanceError("InputChanged")
    owner_data = read("runtime-owner.json", 64 * 1024)
    owner = evidence._runtime_json(owner_data, {
        "schemaVersion": evidence._constant(1), "runId": evidence._constant(inputs["runId"]),
        "invocationGroupId": evidence._constant(inputs["invocationGroupId"]),
        "rootId": evidence.stable_id,
        "rootPathSha256": evidence._constant(hashlib.sha256(str(root).encode()).hexdigest()),
    })
    runner = runtime_runner(root, inputs)
    read("proofs/sdk-vstest-inputs.json")
    expected = {identity: ("none", "none") for identity in catalog_admission_witnesses()}
    discovered, witnesses = None, None
    sequences = []
    for purpose in ("discovery", "execution"):
        bounds = frame[purpose]
        attempt = bounds["attemptId"]
        manifest_data = read(f"runtime-input-{attempt}.json")
        manifest = {**_catalog_manifest(inputs, frame["assemblyPath"], attempt), "purpose": purpose}
        if evidence.canonical_bytes(manifest) != manifest_data:
            raise evidence.ConformanceError("ProofMismatch")
        assembly = root / frame["assemblyPath"]
        settings = runtime_settings(
            root, assembly, attempt, hashlib.sha256(manifest_data).hexdigest(),
            hashlib.sha256(owner_data).hexdigest(), "")
        arguments = runtime_arguments(
            assembly, root / f"stores/settings-{attempt}.runsettings", tuple(expected),
            discovery=purpose == "discovery", runner_prefix=runner["prefix"])
        receipt, record = sdk.verify_category_command_proof(
            root, run_id=inputs["runId"], root_id=owner["rootId"], arguments=arguments,
            cwd=assembly.parent, manifest=manifest, settings_data=settings,
            started_ms=bounds["startedMs"], ended_ms=bounds["endedMs"], settings_directory="stores")
        sequence = receipt["commandSequence"]
        sequences.append(sequence)
        read(f"proofs/category-command-{attempt}-{purpose}.json", 64 * 1024)
        read(f"proofs/execution-command-{sequence:04}.json", 64 * 1024)
        frozen = {**sdk.harness_catalog_runtime_inputs(inputs, frame["assemblyPath"]),
                  CATALOG_INPUTS: evidence.digest(inputs), "runtime-owner.json": hashlib.sha256(owner_data).hexdigest(),
                  f"runtime-input-{attempt}.json": hashlib.sha256(manifest_data).hexdigest()}
        if any(record.get("inputFiles", {}).get(path) != hashed for path, hashed in frozen.items()):
            raise evidence.ConformanceError("ProofMismatch")
        folder = ("discovery-" if purpose == "discovery" else "runtime-") + attempt
        transport = {
            "inputs": inputs, "expected_tests": expected, "manifest_data": manifest_data, "owner_data": owner_data,
            "manifest_sha256": hashlib.sha256(manifest_data).hexdigest(),
            "owner_sha256": hashlib.sha256(owner_data).hexdigest(),
            "completion_data": read(folder + "/completion.json", 64 * 1024),
            "started_ms": bounds["startedMs"], "ended_ms": bounds["endedMs"],
        }
        if purpose == "discovery":
            discovered = evidence.ingest_runtime_discovery(
                **transport, discoveries_data=read(folder + "/discovered.jsonl", 1024 * 1024))
            if (discovered["diagnosticCode"] != "None"
                    or {row["testIdentity"] for row in discovered["discoveries"]} != set(expected)):
                raise evidence.ConformanceError("WitnessMissing")
        else:
            witness_data = read(folder + "/witnesses.jsonl", 1024 * 1024)
            rows = [evidence.load_json(line) for line in witness_data.splitlines()]
            if len(rows) != len(expected):
                raise evidence.ConformanceError("WitnessMissing")
            proofs = {f'proof-{evidence._uuid(row["executionId"])}.json': read(
                folder + f'/proof-{row["executionId"]}.json', 64 * 1024) for row in rows}
            observed = evidence.ingest_runtime_attempt(**transport, witnesses_data=witness_data, proofs=proofs)
            witnesses = observed["witnesses"]
            if (observed["diagnosticCode"] != "None" or len(witnesses) != len(expected)
                    or {row["testIdentity"] for row in witnesses} != set(expected)
                    or any(row["status"] != "Passed" for row in witnesses)):
                raise evidence.ConformanceError("EvidenceIncomplete")
    if sequences != sorted(set(sequences)) or discovered is None or witnesses is None:
        raise evidence.ConformanceError("ProofMismatch")
    return MappingProxyType({
        "qualification": False, "scope": "harness-native-catalog", "code": "None",
        "witnesses": tuple(witnesses), "proofs": MappingProxyType(hashes),
        "startedMs": frame["discovery"]["startedMs"], "endedMs": frame["execution"]["endedMs"],
    })


def execute_contributor_journey(repository, run, inputs, source):
    import conformance_contributors as contributors
    import conformance_sdk_checks as sdk
    from conformance_sources import read_bounded

    inputs = evidence.admit_entity("RunInputs", inputs)
    if (type(run) is not OwnedRun or run.state != "Active" or run.live_children()
            or inputs["profileId"] != "harness" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id
            or Path(source) != run.root / "stores/snapshot"
            or evidence.source_manifest(repository) != inputs["sourceManifest"]):
        raise evidence.ConformanceError("OwnershipInvalid")
    evidence.verify_snapshot(source, inputs["sourceManifest"])
    registration_path = "tests/fixtures/conformance/Contributor/Contributor.conformance.json"
    original = contributors.admit_binding_project(
        Path(source) / registration_path.replace(".conformance.json", ".csproj"), "metadata")
    adapter = run.root / "stores/contributor-source"
    adapter.mkdir(mode=0o700)
    for relative, hashed in original.sources.items():
        target = adapter / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        raw = read_bounded(Path(source) / relative, evidence.MAX_PROOF_BYTES)
        if hashlib.sha256(raw).hexdigest() != hashed:
            raise evidence.ConformanceError("InputChanged")
        sdk.write_new(target, raw)
        target.chmod(0o600)
    project = adapter / original.project
    forwarding = project.parent / "ForwardingMetadataBinding.cs"
    good = read_bounded(forwarding, 64 * 1024)
    needle = b"inner = new(providerPackageSha256);\n        this.injectStaleReplay = injectStaleReplay;"
    if good.count(needle) != 1:
        raise evidence.ConformanceError("InputChanged")
    destination = run.root / "proofs/contributors"
    destination.mkdir(mode=0o700)
    owners, rows = [], []
    for label in ("good", "faulty", "corrected"):
        if evidence.source_manifest(repository) != inputs["sourceManifest"]:
            raise evidence.ConformanceError("InputChanged")
        forwarding.write_bytes(good.replace(needle, needle.replace(b"= injectStaleReplay;", b"= true;"))
                               if label == "faulty" else good)
        binding = contributors.admit_binding_project(project, "metadata")
        child = OwnedRun.allocate(destination / label, repository, profile="metadata")
        child.deadline = min(child.deadline, run.deadline)
        owners.append(child)
        try:
            contributors.execute_owned(
                repository, child, project=project, category="metadata",
                binding_inputs_sha256=binding.inputs_sha256, group_id=inputs["invocationGroupId"])
        except sdk._RuntimeObservationError:
            if label != "faulty":
                raise
        else:
            if label == "faulty":
                raise evidence.ConformanceError("EvidenceIncomplete")
        resources = child.resource_projection()
        if (child.state != "Released" or child.live_children()
                or any(row["state"] != "Released" for row in resources)):
            raise evidence.ConformanceError("CleanupIncomplete")
        child_inputs = evidence.admit_entity("RunInputs", evidence.load_json(
            read_bounded(child.root / "proofs/contributor-inputs.json", evidence.MAX_REPORT_BYTES)))
        observed = contributors.inspect_metadata_binding_runtime(
            child.root, expected_inputs=child_inputs, expected_fault="stale-replay" if label == "faulty" else "none")
        for path in evidence.proof_manifest(child.root):
            (child.root / path).chmod(0o400)
        rows.append({
            "label": label, "path": child.root.relative_to(run.root).as_posix(), "inputs": child_inputs,
            "proofsSha256": evidence.digest(observed["proofs"]), "resources": resources,
        })
    if (evidence.source_manifest(repository) != inputs["sourceManifest"]
            or contributors.admit_binding_project(project, "metadata").inputs_sha256 != original.inputs_sha256):
        raise evidence.ConformanceError("InputChanged")
    sdk.write_new(run.root / CONTRIBUTOR_FRAME, evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False, "scope": "harness-contributor-journey",
        "inputsSha256": evidence.digest(inputs), "runs": rows,
    }))
    inspect_contributor_journey(run.root, expected_inputs=inputs)
    return tuple(owners)


def inspect_contributor_journey(root, *, expected_inputs):
    import conformance_contributors as contributors

    root = Path(root)
    inputs = evidence.admit_entity("RunInputs", expected_inputs)
    if inputs["profileId"] != "harness" or inputs["mode"] != "qualification":
        raise evidence.ConformanceError("UnsupportedProfile")
    hashed, raw = evidence._readonly_report_proof(root, CONTRIBUTOR_FRAME)
    frame = evidence._runtime_json(raw, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "scope": evidence._constant("harness-contributor-journey"),
        "inputsSha256": evidence._constant(evidence.digest(inputs)),
        "runs": evidence._list(evidence._record({
            "label": evidence._one_of("good", "faulty", "corrected"), "path": evidence.relative_path,
            "inputs": lambda row: evidence.admit_entity("RunInputs", row),
            "proofsSha256": evidence.sha256,
            "resources": evidence._list(lambda row: evidence.admit_entity("ResourceOwnership", row), 1, minimum=1),
        }), 3, minimum=3),
    }, limit=evidence.MAX_REPORT_BYTES)
    proofs, results, invariants, bindings, packages, run_ids, root_ids = (
        {CONTRIBUTOR_FRAME: hashed}, [], [], [], [], set(), set())
    for row, label in zip(frame["runs"], ("good", "faulty", "corrected")):
        child = row["inputs"]
        if (row["label"] != label or row["path"] != "proofs/contributors/" + label
                or child["profileId"] != "metadata" or child["mode"] != "diagnostic"
                or child["invocationGroupId"] != inputs["invocationGroupId"]
                or child["sourceManifest"] != inputs["sourceManifest"]
                or child["sourceRevision"] != inputs["sourceRevision"]
                or child["sourceState"] != inputs["sourceState"]
                or child["catalogSha256"] != inputs["catalogSha256"]
                or child["sdkSha256"] != inputs["sdkSha256"]
                or child["runId"] in run_ids or child["runId"] == inputs["runId"]):
            raise evidence.ConformanceError("InputChanged")
        run_ids.add(child["runId"])
        observed = contributors.inspect_metadata_binding_runtime(
            root / row["path"], expected_inputs=child, expected_fault="stale-replay" if label == "faulty" else "none")
        owner_hash, owner_raw = evidence._readonly_report_proof(root / row["path"], "runtime-owner.json")
        owner = evidence.load_json(owner_raw)
        if (evidence.digest(observed["proofs"]) != row["proofsSha256"]
                or owner["rootId"] in root_ids
                or any(resource["runId"] != child["runId"] or resource["rootId"] != owner["rootId"]
                       or resource["state"] != "Released" or resource["childPid"] != 0
                       or resource["childStartSha256"] != "0" * 64
                       or resource["diagnosticCode"] != "None" for resource in row["resources"])):
            raise evidence.ConformanceError("ProofMismatch")
        root_ids.add(owner["rootId"])
        proofs.update({row["path"] + "/" + path: value for path, value in observed["proofs"].items()})
        proofs[row["path"] + "/runtime-owner.json"] = owner_hash
        adapter = child["bindings"][0]["adapterId"]
        common_packages = tuple(sorted(
            (package for package in child["packages"] if package["packageId"] != adapter),
            key=lambda package: package["packageId"]))
        selected = [package["sha256"] for package in child["packages"] if package["packageId"] == adapter]
        if len(selected) != 1 or observed["sessionOrigins"] != 86 or len(observed["witnesses"]) != 76:
            raise evidence.ConformanceError("WitnessMissing")
        invariants.append(evidence.digest(common_packages))
        bindings.append(child["invocation"][1])
        packages.append(selected[0])
        results.append(observed)
    if (len(set(invariants)) != 1 or bindings[0] != bindings[2] or bindings[0] == bindings[1]
            or packages[0] == packages[1] or packages[1] == packages[2]):
        raise evidence.ConformanceError("InputChanged")
    return MappingProxyType({
        "qualification": False, "scope": "harness-contributor-journey", "code": "None",
        "runs": tuple(results), "proofs": MappingProxyType(proofs),
    })


def execute_category_controls(repository, run, inputs):
    import importlib.util
    import conformance_sdk_checks as sdk
    from conformance_sources import NativeCategoryEvaluation, read_bounded

    inputs = evidence.admit_entity("RunInputs", inputs)
    if (type(run) is not OwnedRun or run.state != "Active" or run.live_children()
            or inputs["profileId"] != "harness" or inputs["mode"] != "qualification"
            or inputs["runId"] != run.run_id
            or evidence.source_manifest(repository) != inputs["sourceManifest"]):
        raise evidence.ConformanceError("OwnershipInvalid")
    if inputs["sourceState"] not in ("clean-local", "clean-ci"):
        raise evidence.ConformanceError("InputChanged")
    source_path = "tests/tooling/test_conformance_evidence.py"
    source = Path(repository) / source_path
    if hashlib.sha256(read_bounded(source, 1024 * 1024)).hexdigest() != inputs["sourceManifest"][source_path]:
        raise evidence.ConformanceError("InputChanged")
    spec = importlib.util.spec_from_file_location("test_conformance_evidence", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    destination = run.root / "proofs/category-controls"
    destination.mkdir(mode=0o700)
    evaluations, rows = [], []
    for profile in ("metadata", "artifacts"):
        child, child_root = None, destination / profile

        def execute(invocation):
            nonlocal child
            if invocation.profiles != (profile,) or invocation.evidence != child_root or child is not None:
                raise evidence.ConformanceError("InputChanged")
            child = OwnedRun.allocate(child_root, repository, profile=profile)
            child.deadline = min(child.deadline, run.deadline)
            native = sdk.execute_owned(
                repository, child, category=profile, qualify=True, group_id=inputs["invocationGroupId"])
            if type(native) is not NativeCategoryEvaluation or native._source._run is not child:
                raise evidence.ConformanceError("OwnershipInvalid")
            evaluations.append(native)
            return evidence.complete_native_category_invocation(invocation, native)

        try:
            status = module.run_native_category_controls(
                ["--profile", profile, "--evidence", str(child_root)], executor=execute)
            if (type(status) is not int or status != 0 or child is None
                    or len(evaluations) != len(rows) + 1):
                raise evidence.ConformanceError("EvidenceIncomplete")
        finally:
            if child is not None and child.state in ("Allocated", "Active"):
                child.transition("Settling")
            if child is not None and child.state == "Settling":
                child.release()
        child_inputs = evidence.admit_entity("RunInputs", evidence.load_json(read_bounded(
            child.root / f"proofs/category-{profile}-qualification-run-inputs.json", evidence.MAX_REPORT_BYTES)))
        original_path = f"proofs/category-{profile}-qualification-report.json"
        report_path = f"proofs/category-{profile}-fixture-qualification-report.json"
        _, original = evidence._readonly_report_proof(child.root, original_path)
        report_sha, report = evidence._readonly_report_proof(child.root, report_path)
        origin = evidence.native_category_qualification_receipt(
            child, report, original_report_data=original, expected_inputs=child_inputs,
            native_evaluation=evaluations[-1])
        control_path = f"proofs/category-{profile}-native-controls.json"
        control_sha, _ = evidence._readonly_report_proof(child.root, control_path)
        rows.append({
            "profileId": profile, "path": child.root.relative_to(run.root).as_posix(), "inputs": child_inputs,
            "reportPath": report_path, "qualificationOrigin": origin,
            "controlOrigin": {
                "kind": "native-category-control-observation", "inputsSha256": evidence.digest(child_inputs),
                "reportSha256": report_sha, "proofPath": control_path, "proofSha256": control_sha,
            },
        })
    sdk.write_new(run.root / CATEGORY_CONTROL_FRAME, evidence.canonical_bytes({
        "schemaVersion": 1, "qualification": False, "scope": "harness-native-category-controls",
        "inputsSha256": evidence.digest(inputs), "runs": rows,
    }))
    inspect_category_controls(run.root, expected_inputs=inputs)
    return tuple(evaluations)


def inspect_category_controls(root, *, expected_inputs):
    root = Path(root)
    inputs = evidence.admit_entity("RunInputs", expected_inputs)
    if inputs["profileId"] != "harness" or inputs["mode"] != "qualification":
        raise evidence.ConformanceError("UnsupportedProfile")
    if inputs["sourceState"] not in ("clean-local", "clean-ci"):
        raise evidence.ConformanceError("InputChanged")
    hashed, raw = evidence._readonly_report_proof(root, CATEGORY_CONTROL_FRAME)
    frame = evidence._runtime_json(raw, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "scope": evidence._constant("harness-native-category-controls"),
        "inputsSha256": evidence._constant(evidence.digest(inputs)),
        "runs": evidence._list(evidence._record({
            "profileId": evidence._one_of("metadata", "artifacts"), "path": evidence.relative_path,
            "inputs": lambda row: evidence.admit_entity("RunInputs", row),
            "reportPath": evidence.relative_path,
            "qualificationOrigin": evidence.admit_qualification_origin,
            "controlOrigin": evidence._record({
                "kind": evidence._constant("native-category-control-observation"),
                "inputsSha256": evidence.sha256, "reportSha256": evidence.sha256,
                "proofPath": evidence.relative_path, "proofSha256": evidence.sha256,
            }),
        }), 2, minimum=2),
    }, limit=evidence.MAX_REPORT_BYTES)
    results, proofs, identities = [], {CATEGORY_CONTROL_FRAME: hashed}, {inputs["runId"]}
    for row, profile in zip(frame["runs"], ("metadata", "artifacts")):
        child = row["inputs"]
        if (row["profileId"] != child["profileId"] or row["profileId"] != profile
                or row["path"] != "proofs/category-controls/" + profile
                or child["mode"] != "qualification" or child["runId"] in identities
                or any(child[key] != inputs[key] for key in (
                    "invocationGroupId", "sourceRevision", "sourceState", "sourceManifest",
                    "catalogSha256", "sdkSha256"))
                or row["reportPath"] != f"proofs/category-{profile}-fixture-qualification-report.json"):
            raise evidence.ConformanceError("InputChanged")
        identities.add(child["runId"])
        child_root = root / row["path"]
        _, report = evidence._readonly_report_proof(child_root, row["reportPath"])
        inspected = evidence.inspect_receipted_native_category_controls(
            child_root, report, expected_inputs=child,
            expected_report_sha256=row["qualificationOrigin"]["reportSha256"],
            qualification_origin=row["qualificationOrigin"], control_origin=row["controlOrigin"])
        original_path = row["qualificationOrigin"]["originalReportPath"]
        original_sha, original = evidence._readonly_report_proof(child_root, original_path)
        original = evidence.admit_entity("QualificationReport", evidence.load_json(original))
        child_proofs = {
            **original["proofs"], original_path: original_sha,
            row["reportPath"]: row["qualificationOrigin"]["reportSha256"],
            row["controlOrigin"]["proofPath"]: row["controlOrigin"]["proofSha256"],
        }
        source_path = f"proofs/category-{profile}-native-controls-source.py"
        source_sha, _ = evidence._readonly_report_proof(child_root, source_path)
        child_proofs[source_path] = source_sha
        proofs.update({row["path"] + "/" + path: value for path, value in child_proofs.items()})
        results.append(inspected)
    return MappingProxyType({
        "qualification": False, "scope": "harness-native-category-controls", "code": "None",
        "runs": tuple(results), "proofs": MappingProxyType(proofs),
    })
