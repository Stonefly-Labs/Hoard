"""Prepare immutable historical sources/binaries before F-07 candidate builds.

Preparation never qualifies providers. Every build uses a private, revision-local
feed/cache and the historical locks; candidate execution may only verify/reuse
the resulting sealed bytes.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tarfile
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile

from foundation_evidence import canonicalize_acceptance_archive
from conformance_evidence import MAX_REPORT_BYTES, ConformanceError, canonical_bytes, digest, file_sha256, load_json, relative_path, sha256, synthetic_nuget_configuration, verify_snapshot
from conformance_execution import OwnedRun, capture_control, no_symlinks
from conformance_lock_preparation import prepare_project_lock, read_lock, rebind_local_archives, verify_project_lock


BASELINE = "9389016c0285c79f6f515f59805a5a41c69b0767"
BASELINES = (
    ("registration", "837fdf3edf51c3df34710184d018479683c194c2",
     "tests/fixtures/lifecycle/registration/RegistrationConsumer", "RegistrationConsumer.csproj"),
    ("lifecycle", "b80c69fc386541be4f56f6ef2edeca40f43a0e1c",
     "tests/fixtures/configuration/LifecycleConsumer", "LifecycleConsumer.csproj"),
    ("configuration", "7fd73267a5154583363c94e9e85b9bac7d4a16b3",
     "tests/fixtures/discovery/RetainedConfiguration", "RetainedConfiguration.csproj"),
    ("metadata-marker", "10ce78851b97b02bd83a8ef7da7ffdc2381d6519",
     "tests/fixtures/metadata/RetainedMarker", "RetainedMarker.csproj"),
    ("artifact-marker", "830972f24795ffaaaa18cb35138db7da59022313",
     "tests/fixtures/artifacts/RetainedMarker", "RetainedMarker.csproj"),
)
SOURCE_RECIPES_PATH = "tests/fixtures/conformance/baselines/source-consumers.json"
RETAINED_SCENARIOS = ("registration", "lifecycle", "configuration", "metadata-marker", "artifact-marker",
                      "memory", "sqlite", "local", "object")
OBSERVER_PROJECT = "tests/fixtures/conformance/Compatibility/Observer/Observer.csproj"
BREAK_CONTROLS_PATH = "tests/fixtures/conformance/Compatibility/break-controls.json"
HISTORICAL_BINARY_FIXTURE = "tests/fixtures/compatibility/BinaryMemberRemoval/"
HISTORICAL_BINARY_PROJECTS = ("Old/BinaryContract.csproj", "Consumer/BinaryConsumer.csproj")
HISTORICAL_BINARY_INPUTS = "proofs/historical-binary-inputs.json"
HISTORICAL_BINARY_PREPARATION = "F07BinaryPreparation.json"
HISTORICAL_BINARY_PREPARATION_PROOF = "proofs/historical-binary-preparation.json"
HISTORICAL_BINARY_IMAGES = {
    variant + "/" + target + suffix:
    HISTORICAL_BINARY_FIXTURE + project + "/bin/Release/net10.0/" + name + suffix
    for variant, project, name, target in (
        ("baseline", "Old", "BinaryContract", "BinaryContract"),
        ("consumer", "Consumer", "BinaryConsumer", "RetainedConsumer"))
    for suffix in (".dll", ".pdb")
}
BREAK_CONTROLS = {
    "schemaVersion": 1, "qualification": False, "baselineRevision": BASELINE,
    "source": {"fixture": "tests/fixtures/compatibility/RequiredMember", "compilerCode": "CS0535",
               "symbol": "RequiredContract.IProvider.Required()", "repair": "restore-compatible-contract"},
    "binary": {"fixture": "tests/fixtures/conformance/Compatibility", "failure": "MissingMethodException",
               "symbol": "BinaryContract.Api.Describe()", "consumerRecompiled": False},
}
SOURCE_BREAK_SOURCES = "proofs/compatibility-source-break-sources.json"
SOURCE_BREAK_INPUTS = "proofs/compatibility-source-break-inputs.json"
SOURCE_RECIPE_POLICY = (
    *((project, "historical-f06", "api-consumer") for project in (
        "tests/fixtures/lifecycle/registration/RegistrationConsumer/RegistrationConsumer.csproj",
        "tests/fixtures/configuration/LifecycleConsumer/LifecycleConsumer.csproj",
        "tests/fixtures/discovery/RetainedConfiguration/RetainedConfiguration.csproj")),
    *((f"tests/fixtures/{category}/RetainedMarker/RetainedMarker.csproj", "historical-f06", "marker-consumer")
      for category in ("metadata", "artifacts")),
    *((f"tests/fixtures/lifecycle/{name}/Hoard.Fixtures.Lifecycle.{name}.csproj",
       "historical-f06", "provider-implementer")
      for name in ("Protocol.One", "Protocol.Two", "Metadata", "Artifact.One", "Artifact.Two", "Identity")),
    ("tests/fixtures/configuration/LegacyOptions/LegacyOptions.csproj", "historical-f06", "provider-implementer"),
    *((f"tests/fixtures/{category}/{name}/{name}.csproj", "historical-f06",
       "operational-consumer" if name == "Consumer" else "provider-implementer")
      for category, names in (("metadata", ("Sqlite", "Memory", "HostAdapters", "Consumer")),
                              ("artifacts", ("Local", "ObjectSemantics", "HostAdapters", "Consumer")))
      for name in names),
    *((f"tests/fixtures/conformance/Bindings/{name}/{name}.csproj", "candidate-source-manifest",
       "sdk-binding-current") for name in ("Memory", "Sqlite", "Local", "ObjectSemantics")),
)


def validate_source_recipes(document):
    if (not isinstance(document, dict) or set(document) !=
            {"schemaVersion", "qualification", "baselineRevision", "recipes"}
            or type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1
            or document["qualification"] is not False or document["baselineRevision"] != BASELINE
            or not isinstance(document["recipes"], list)
            or any(not isinstance(row, dict) or set(row) != {"project", "sourceKind", "role"}
                   for row in document["recipes"])
            or tuple((row["project"], row["sourceKind"], row["role"]) for row in document["recipes"])
            != SOURCE_RECIPE_POLICY):
        raise ConformanceError("EvidenceIncomplete")
    return document


def source_recipes(repository):
    return validate_source_recipes(load_json(read_lock(Path(repository) / SOURCE_RECIPES_PATH)))


def _copy_recipe_sources(source, target, manifest):
    from conformance_sources import read_bounded
    target.mkdir(mode=0o700)
    for relative, expected in manifest.items():
        original = source / relative_path(relative)
        raw = read_bounded(original, 64 * 1024**2)
        if hashlib.sha256(raw).hexdigest() != sha256(expected):
            raise ConformanceError("InputChanged")
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with destination.open("xb") as output:
            output.write(raw)
        destination.chmod(0o400)
    verify_snapshot(target, manifest)


def _source_recipe_packages(project, feed, *, baseline=False):
    raw = read_lock(project.parent / ("Baseline/packages.lock.json" if baseline else "packages.lock.json"))
    _, packages, _ = rebind_local_archives(raw, feed)
    assets_raw = read_lock(project.parent / "obj/project.assets.json")
    assets = load_json(assets_raw)
    if not isinstance(assets, dict) or not isinstance(assets.get("libraries"), dict):
        raise ConformanceError("InputChanged")
    actual = {}
    for identity, library in assets["libraries"].items():
        if not identity.startswith("Hoard."):
            continue
        if (not isinstance(library, dict) or library.get("type") != "package"
                or not re.fullmatch(r"Hoard\.[A-Za-z0-9.]+/0\.1\.0", identity)):
            raise ConformanceError("InputChanged")
        filename = identity.replace("/", ".") + ".nupkg"
        if filename not in packages:
            raise ConformanceError("InputChanged")
        package = feed / filename
        content = base64.b64encode(hashlib.sha512(package.read_bytes()).digest()).decode("ascii")
        if library.get("sha512") != content:
            raise ConformanceError("InputChanged")
        actual[filename] = file_sha256(package)
    if not actual or actual != packages:
        raise ConformanceError("InputChanged")
    return packages, hashlib.sha256(assets_raw).hexdigest()


def execute_source_recipes(repository, run, candidate, candidate_sources, baseline_sha256, *, msbuild=None):
    """Compile copied source inputs; never rebuild or modify sealed retained binaries."""
    candidate = Path(candidate)
    no_symlinks(candidate)
    if run.state != "Active" or candidate == run.root or not candidate.resolve(strict=True).is_relative_to(run.root):
        raise ConformanceError("OwnershipInvalid")
    verify_snapshot(candidate, candidate_sources)
    document = source_recipes(repository)
    baseline = verify_prepared_baselines(run.root, baseline_sha256)
    historical, = (entry for entry in baseline["entries"] if entry["id"] == "f06")
    roots = {
        "historical-f06": (run.root / "stores/f06", historical["sources"]),
        "candidate-source-manifest": (candidate, candidate_sources),
    }
    copies = {}
    for kind, (source, manifest) in roots.items():
        target = run.root / "stores" / ("source-compatibility-" + kind)
        _copy_recipe_sources(source, target, manifest)
        copies[kind] = target
    feed = run.root / "feed/candidate"
    no_symlinks(feed)
    feed_hashes = _hash_tree(feed)
    if not feed_hashes:
        raise ConformanceError("PrerequisiteMissing")
    verify_snapshot(feed, feed_hashes)
    config = run.root / "stores/source-compatibility.NuGet.Config"
    with config.open("xb") as output:
        output.write(synthetic_nuget_configuration(feed))
    records = []
    for recipe in document["recipes"]:
        kind = recipe["sourceKind"]
        _, manifest = roots[kind]
        copied = copies[kind]
        project = copied / recipe["project"]
        if recipe["project"] not in manifest:
            raise ConformanceError("InputChanged")
        verify_snapshot(copied, manifest)
        preparations = []
        project_xml = ET.parse(project)
        references = project_xml.findall(".//PackageReference")
        explicit = [reference for reference in references if reference.get("Version") is not None]
        if explicit and len(explicit) != len(references):
            raise ConformanceError("InputChanged")
        properties = ("-p:ManagePackageVersionsCentrally=false",) if explicit else ()
        baseline_lock = not (project.parent / "packages.lock.json").is_file()
        _build(run, project, config, "candidate", source_root=copied, preparations=preparations,
               properties=properties, baseline=baseline_lock, msbuild=msbuild)
        verify_snapshot(copied, manifest)
        verify_snapshot(feed, feed_hashes)
        for preparation in preparations:
            verify_project_lock(preparation, copied, feed)
        packages, assets_sha = _source_recipe_packages(project, feed, baseline=baseline_lock)
        assembly_name = project_xml.findtext(".//AssemblyName") or project.stem
        assembly = project.parent / "bin/Release/net10.0" / (assembly_name + ".dll")
        no_symlinks(assembly)
        if not assembly.is_file():
            raise ConformanceError("EvidenceIncomplete")
        records.append({
            **recipe, "sourceSha256": digest(manifest), "assemblySha256": file_sha256(assembly),
            "assetsSha256": assets_sha, "packages": packages, "lockPreparations": preparations,
            "properties": list(properties),
        })
    for kind, (_, manifest) in roots.items():
        verify_snapshot(copies[kind], manifest)
    verify_snapshot(candidate, candidate_sources)
    verify_prepared_baselines(run.root, baseline_sha256)
    return {"schemaVersion": 1, "qualification": False, "mode": "source-compatibility",
            "baselineSealSha256": baseline_sha256, "recipeSha256": digest(document),
            "candidatePackages": feed_hashes, "recipes": records}


def verify_source_break_result(result):
    _verify_source_break_events(result.exit_code, result.events)


def _verify_source_break_events(exit_code, events):
    if (exit_code != 1 or not events
            or any(dict(event) not in (
                {"event": "build", "code": "CommandFailed", "value": 0},
                {"event": "build", "code": "CommandFailed", "value": 535}) for event in events)
            or not any(event["value"] == 535 for event in events)):
        raise ConformanceError("ProofMismatch")


def source_break_build_inputs(project, sources, *, contract=None):
    fixture = BREAK_CONTROLS["source"]["fixture"] + "/"
    projects = {
        fixture + variant + "/RequiredContract.csproj": variant for variant in ("Old", "New")}
    projects[fixture + "Consumer/RequiredConsumer.csproj"] = "Consumer"
    if project not in projects or contract not in (None, "Old", "New"):
        raise ConformanceError("EvidenceIncomplete")
    variant = projects[project]
    if (variant == "Consumer") != (contract is not None):
        raise ConformanceError("EvidenceIncomplete")
    required = (
        "Directory.Build.props", "Directory.Packages.props", "global.json",
        "tests/fixtures/compatibility/Directory.Build.props", project,
        fixture + variant + "/packages.lock.json",
        fixture + variant + ("/Provider.cs" if variant == "Consumer" else "/Contract.cs"))
    if not set(required) <= sources.keys():
        raise ConformanceError("EvidenceIncomplete")
    return (
        SOURCE_BREAK_INPUTS if contract is not None else SOURCE_BREAK_SOURCES,
        "stores/candidate.NuGet.Config",
        *("stores/compatibility-source-break/" + path for path in required),
        *(("stores/compatibility-source-break/" + fixture + contract
           + "/bin/Release/net10.0/RequiredContract.dll",) if contract is not None else ()))


def source_break_output_properties(root, variant):
    if variant not in ("Old", "New", "Consumer"):
        raise ConformanceError("EvidenceIncomplete")
    return (
        "-p:OutputPath=" + str(Path(root) / "proofs" / ("source-break-output-" + variant)) + os.sep,
        "-p:AppendTargetFrameworkToOutputPath=false")


def source_break_output_paths(variant):
    if variant not in ("Old", "New", "Consumer"):
        raise ConformanceError("EvidenceIncomplete")
    name = "RequiredConsumer" if variant == "Consumer" else "RequiredContract"
    return tuple("proofs/source-break-output-" + variant + "/" + name + suffix for suffix in (".dll", ".pdb"))


def _prepare_source_break_outputs(run, variant):
    import conformance_evidence as evidence

    run._check_ledger()
    with evidence._input_root(run.root) as (_, root), evidence._input_parent(
            root, source_break_output_paths(variant)[0], create=True):
        pass


def _stage_source_break_outputs(run, variant, *, repair=False):
    import conformance_evidence as evidence

    source = Path(source_break_output_paths(variant)[0]).parent
    if repair and variant != "Consumer":
        raise ConformanceError("EvidenceIncomplete")
    target = (Path("stores/compatibility-source-break") / BREAK_CONTROLS["source"]["fixture"]
              / variant / "bin/Release" / ("net10.0-repair" if repair else "net10.0"))
    with evidence._input_root(run.root) as (_, root), evidence._input_parent(
            root, source.as_posix()) as (parent, name):
        descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            original = os.fstat(descriptor)
            if original.st_uid != os.getuid():
                raise ConformanceError("InputChanged")
            with evidence._input_parent(root, target.as_posix(), create=True) as (destination, target_name):
                try:
                    os.stat(target_name, dir_fd=destination, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise ConformanceError("InputChanged")
                os.rename(name, target_name, src_dir_fd=parent, dst_dir_fd=destination)
                actual = os.stat(target_name, dir_fd=destination, follow_symlinks=False)
                if (actual.st_dev, actual.st_ino) != (original.st_dev, original.st_ino):
                    raise ConformanceError("InputChanged")
        finally:
            os.close(descriptor)
    return run.root / target


def execute_source_break(run, candidate, candidate_sources, config, baseline_sha256, *, msbuild=None):
    """Challenge the unchanged historical implementer, then repair only its contract."""
    from conformance_sources import read_bounded
    if (type(run) is not OwnedRun or run.state != "Active"
            or Path(config) != run.root / "stores/candidate.NuGet.Config"):
        raise ConformanceError("OwnershipInvalid")
    verify_snapshot(candidate, candidate_sources)
    controls = load_json(read_bounded(candidate / BREAK_CONTROLS_PATH, 4096))
    if canonical_bytes(controls) != canonical_bytes(BREAK_CONTROLS):
        raise ConformanceError("EvidenceIncomplete")
    baseline = verify_prepared_baselines(run.root, baseline_sha256)
    historical, = (entry for entry in baseline["entries"] if entry["id"] == "f06")
    copied = run.root / "stores/compatibility-source-break"
    _copy_recipe_sources(run.root / "stores/f06", copied, historical["sources"])
    fixture = copied / controls["source"]["fixture"]
    source_frame = {
        "schemaVersion": 1, "qualification": False, "baselineSealSha256": baseline_sha256,
        "sources": historical["sources"], "controlsSha256": digest(controls)}
    with (run.root / SOURCE_BREAK_SOURCES).open("xb") as destination:
        destination.write(canonical_bytes(source_frame))
    (run.root / SOURCE_BREAK_SOURCES).chmod(0o400)
    commands = []
    for variant in ("Old", "New"):
        project = fixture / variant / "RequiredContract.csproj"
        project_relative = project.relative_to(copied).as_posix()
        _prepare_source_break_outputs(run, variant)
        commands.extend({**row, "role": variant} for row in _build(
            run, project, config, "compatibility-source", msbuild=msbuild,
            properties=source_break_output_properties(run.root, variant),
            execution_inputs=_freeze_build_inputs(
                run, source_break_build_inputs(project_relative, historical["sources"])),
            execution_outputs=source_break_output_paths(variant)))
        _stage_source_break_outputs(run, variant)
    contracts = {variant: fixture / variant / "bin/Release/net10.0/RequiredContract.dll"
                 for variant in ("Old", "New")}
    for contract in contracts.values():
        no_symlinks(contract)
        contract.chmod(0o400)
    hashes = {variant: file_sha256(contract) for variant, contract in contracts.items()}
    if hashes["Old"] == hashes["New"]:
        raise ConformanceError("ProofMismatch")
    project = fixture / "Consumer/RequiredConsumer.csproj"
    original = historical["sources"][project.with_name("Provider.cs").relative_to(copied).as_posix()]
    project_relative = project.relative_to(copied).as_posix()
    manifest_path = SOURCE_BREAK_INPUTS
    manifest = {"sources": historical["sources"], "contracts": hashes, "controls": digest(controls)}
    with (run.root / manifest_path).open("xb") as destination:
        destination.write(canonical_bytes(manifest))
    (run.root / manifest_path).chmod(0o400)
    consumer_outputs = source_break_output_paths("Consumer")
    compatible_inputs = _freeze_build_inputs(
        run, source_break_build_inputs(project_relative, historical["sources"], contract="Old"))
    _prepare_source_break_outputs(run, "Consumer")
    commands.extend({**row, "role": "consumer"} for row in _build(
        run, project, config, "compatibility-source",
        properties=(*source_break_output_properties(run.root, "Consumer"),
                    "-p:ContractAssembly=" + str(contracts["Old"])), msbuild=msbuild,
        execution_inputs=compatible_inputs, execution_outputs=consumer_outputs))
    consumer_directory = _stage_source_break_outputs(run, "Consumer")
    original_outputs = {suffix: file_sha256(consumer_directory / ("RequiredConsumer" + suffix))
                        for suffix in (".dll", ".pdb")}
    baseline_output = original_outputs[".dll"]
    _, arguments, _ = project_build_commands(
        project, config, properties=(*source_break_output_properties(run.root, "Consumer"),
                                    "-p:ContractAssembly=" + str(contracts["New"])), msbuild=msbuild)
    result = run.command(
        arguments, cwd=project.parent, cache_id="compatibility-source", kind="compatibility-source",
        env={"DOTNET_ROLL_FORWARD": "Disable"}, record_execution=True,
        execution_inputs=_freeze_build_inputs(
            run, source_break_build_inputs(project_relative, historical["sources"], contract="New")))
    sequence = run.command_sequence
    verify_source_break_result(result)
    negative = run.read_execution_record(sequence)
    commands.append({"role": "negative", "sequence": sequence,
                     "executionSha256": hashlib.sha256(negative).hexdigest()})
    (run.root / f"diagnostics/command-{sequence:04}.jsonl").chmod(0o400)
    _, repair_arguments, _ = project_build_commands(
        project, config, properties=(*source_break_output_properties(run.root, "Consumer"),
                                    "-p:ContractAssembly=" + str(contracts["Old"])), msbuild=msbuild)
    _prepare_source_break_outputs(run, "Consumer")
    _command(run, repair_arguments, cwd=project.parent, cache_id="compatibility-source",
             execution_inputs=compatible_inputs, execution_outputs=consumer_outputs)
    repair = run.read_execution_record(run.command_sequence)
    commands.append({"role": "repair", "sequence": run.command_sequence,
                     "executionSha256": hashlib.sha256(repair).hexdigest()})
    repaired_directory = _stage_source_break_outputs(run, "Consumer", repair=True)
    if any(value != file_sha256(directory / ("RequiredConsumer" + suffix))
           for directory in (consumer_directory, repaired_directory) for suffix, value in original_outputs.items()):
        raise ConformanceError("InputChanged")
    verify_snapshot(copied, historical["sources"])
    verify_snapshot(candidate, candidate_sources)
    verify_prepared_baselines(run.root, baseline_sha256)
    if any(file_sha256(contracts[variant]) != value for variant, value in hashes.items()):
        raise ConformanceError("InputChanged")
    packet = {"schemaVersion": 2, "qualification": False, "mode": "source-break-control",
            "baselineSealSha256": baseline_sha256, "controlsSha256": digest(controls),
            "consumerSourceSha256": original, "consumerAssemblySha256": baseline_output,
            "contracts": hashes, "compilerCode": controls["source"]["compilerCode"],
            "symbol": controls["source"]["symbol"], "repair": controls["source"]["repair"],
            "negativeSequence": sequence, "negativeExecutionSha256": hashlib.sha256(negative).hexdigest(),
            "inputsSha256": file_sha256(run.root / manifest_path),
            "sourceFrameSha256": file_sha256(run.root / SOURCE_BREAK_SOURCES),
            "consumerPdbSha256": original_outputs[".pdb"],
            "contractPdbSha256": {variant: file_sha256(path.with_suffix(".pdb"))
                                  for variant, path in contracts.items()},
            "commands": commands}
    inspected = inspect_source_break_control(
        run.root, canonical_bytes(packet), expected_baseline_sha256=baseline_sha256, msbuild=msbuild)
    if (inspected["runId"] != run.run_id or inspected["rootId"] != run.root_id
            or any(hashlib.sha256(run.read_execution_record(row["sequence"])).hexdigest()
                   != row["executionSha256"] for row in inspected["commands"])):
        raise ConformanceError("OwnershipInvalid")
    return packet


def inspect_source_break_control(root, packet_data, *, expected_baseline_sha256, msbuild=None, retained=False):
    """Inspect recorded correspondence; only the original live owner can supply native origin."""
    import conformance_evidence as evidence

    root = Path(root).absolute()
    baseline = (_prepared_baseline_document(root, expected_baseline_sha256) if retained
                else verify_prepared_baselines(root, expected_baseline_sha256))
    historical = next(row for row in baseline["entries"] if row["id"] == "f06")
    packet = evidence._runtime_json(packet_data, {
        "schemaVersion": evidence._constant(2), "qualification": evidence._constant(False),
        "mode": evidence._constant("source-break-control"),
        "baselineSealSha256": evidence._constant(sha256(expected_baseline_sha256)),
        "controlsSha256": evidence._constant(digest(BREAK_CONTROLS)),
        "consumerSourceSha256": sha256, "consumerAssemblySha256": sha256,
        "contracts": evidence._record({"Old": sha256, "New": sha256}),
        "compilerCode": evidence._constant(BREAK_CONTROLS["source"]["compilerCode"]),
        "symbol": evidence._constant(BREAK_CONTROLS["source"]["symbol"]),
        "repair": evidence._constant(BREAK_CONTROLS["source"]["repair"]),
        "negativeSequence": evidence._integer, "negativeExecutionSha256": sha256,
        "inputsSha256": sha256, "sourceFrameSha256": sha256, "consumerPdbSha256": sha256,
        "contractPdbSha256": evidence._record({"Old": sha256, "New": sha256}),
        "commands": evidence._list(evidence._record({
            "role": evidence._one_of("Old", "New", "consumer", "negative", "repair"),
            "sequence": evidence._integer, "executionSha256": sha256}), 8, minimum=5),
    }, limit=64 * 1024)
    source_sha, source_raw = evidence._readonly_report_proof(root, SOURCE_BREAK_SOURCES)
    source_frame = evidence._runtime_json(source_raw, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "baselineSealSha256": evidence._constant(sha256(expected_baseline_sha256)),
        "sources": evidence._hash_map, "controlsSha256": evidence._constant(digest(BREAK_CONTROLS)),
    }, limit=MAX_REPORT_BYTES)
    inputs_sha, inputs_raw = evidence._readonly_report_proof(root, SOURCE_BREAK_INPUTS)
    inputs = evidence._runtime_json(inputs_raw, {
        "sources": evidence._hash_map, "contracts": evidence._record({"Old": sha256, "New": sha256}),
        "controls": evidence._constant(digest(BREAK_CONTROLS)),
    }, limit=MAX_REPORT_BYTES)
    fixture = BREAK_CONTROLS["source"]["fixture"] + "/"
    if (source_sha != packet["sourceFrameSha256"] or inputs_sha != packet["inputsSha256"]
            or source_frame["sources"] != historical["sources"] or inputs["sources"] != historical["sources"]
            or inputs["contracts"] != packet["contracts"] or packet["contracts"]["Old"] == packet["contracts"]["New"]
            or historical["sources"].get(fixture + "Consumer/Provider.cs") != packet["consumerSourceSha256"]):
        raise ConformanceError("ProofMismatch")
    copied = root / "stores/compatibility-source-break"
    config = root / "stores/candidate.NuGet.Config"
    if not retained:
        verify_snapshot(copied, historical["sources"])
    expected = []
    for role, variant, contract in (
            ("Old", "Old", None), ("New", "New", None), ("consumer", "Consumer", "Old"),
            ("negative", "Consumer", "New"), ("repair", "Consumer", "Old")):
        name = "RequiredConsumer" if variant == "Consumer" else "RequiredContract"
        project = fixture + variant + "/" + name + ".csproj"
        target = copied / project
        properties = (*source_break_output_properties(root, variant), *((
            "-p:ContractAssembly=" + str(copied / fixture / contract / "bin/Release/net10.0/RequiredContract.dll"),)
            if contract is not None else ()))
        paths = source_break_build_inputs(project, historical["sources"], contract=contract)
        input_files = {
            SOURCE_BREAK_SOURCES if contract is None else SOURCE_BREAK_INPUTS:
                source_sha if contract is None else inputs_sha,
            "stores/candidate.NuGet.Config": hashlib.sha256(
                synthetic_nuget_configuration(root / "feed/candidate")).hexdigest(),
            **{"stores/compatibility-source-break/" + path: value for path, value in historical["sources"].items()
               if "stores/compatibility-source-break/" + path in paths},
        }
        if contract is not None:
            input_files["stores/compatibility-source-break/" + fixture + contract
                        + "/bin/Release/net10.0/RequiredContract.dll"] = packet["contracts"][contract]
        if set(input_files) != set(paths):
            raise ConformanceError("ProofMismatch")
        if not retained and evidence.input_manifest(root, paths) != input_files:
            raise ConformanceError("InputChanged")
        dll, pdb = source_break_output_paths(variant)
        output_files = {
            dll: packet["consumerAssemblySha256"] if variant == "Consumer" else packet["contracts"][variant],
            pdb: packet["consumerPdbSha256"] if variant == "Consumer" else packet["contractPdbSha256"][variant]}
        steps = (project_build_steps(target, config, properties=properties, msbuild=msbuild)
                 if role not in ("negative", "repair") else (
                     project_build_commands(target, config, properties=properties, msbuild=msbuild)[1],))
        for index, arguments in enumerate(steps):
            expected.append((role, arguments, target.parent, input_files,
                             output_files if role != "negative" and index == len(steps) - 1 else {}))
    if len(expected) != len(packet["commands"]):
        raise ConformanceError("ProofMismatch")
    previous_sequence, previous_end, started, owner, negative_sha = 0, 0, None, None, None
    commands = []
    for declaration, (role, arguments, cwd, input_files, output_files) in zip(packet["commands"], expected):
        sequence = declaration["sequence"]
        if declaration["role"] != role or sequence <= previous_sequence:
            raise ConformanceError("ProofMismatch")
        record_sha, record_raw = evidence._readonly_report_proof(root, f"proofs/execution-command-{sequence:04}.json")
        record = evidence._runtime_json(record_raw, {
            "schemaVersion": evidence._constant(1), "sequence": evidence._constant(sequence),
            "childPid": evidence._integer, "childStartSha256": sha256,
            "startedMs": evidence._number, "endedMs": evidence._number,
            "exitCode": evidence._constant(1 if role == "negative" else 0),
            "diagnosticCode": evidence._constant("None"), "groupState": evidence._constant("Exited"),
            "scope": evidence._constant("ordinary"), "runId": evidence._uuid, "rootId": evidence.stable_id,
            "argvSha256": sha256, "cwdSha256": sha256, "inputFiles": evidence._hash_map,
            **({"outputFiles": evidence._hash_map} if output_files else {}),
            **({"diagnosticsSha256": sha256} if role == "negative" else {}),
        }, limit=64 * 1024)
        identity = (record["runId"], record["rootId"])
        if (record_sha != declaration["executionSha256"] or record["childPid"] == 0
                or record["childStartSha256"] == "0" * 64 or record["argvSha256"] != digest(arguments)
                or record["cwdSha256"] != hashlib.sha256(str(cwd).encode()).hexdigest()
                or record["inputFiles"] != input_files or record.get("outputFiles", {}) != output_files
                or record["startedMs"] < previous_end or record["endedMs"] < record["startedMs"]
                or owner is not None and owner != identity):
            raise ConformanceError("ProofMismatch")
        if not retained:
            for path, hashed in output_files.items():
                directory = "net10.0-repair" if role == "repair" else "net10.0"
                variant = "Old" if role == "Old" else "New" if role == "New" else "Consumer"
                physical = ("stores/compatibility-source-break/" + fixture + variant
                            + "/bin/Release/" + directory + "/" + Path(path).name)
                actual, _ = evidence._readonly_report_proof(root, physical)
                if actual != hashed:
                    raise ConformanceError("InputChanged")
        if role == "negative":
            negative_sha, raw = evidence._readonly_report_proof(root, f"diagnostics/command-{sequence:04}.jsonl")
            if (negative_sha != record["diagnosticsSha256"] or len(raw) > 64 * 1024
                    or packet["negativeSequence"] != sequence or packet["negativeExecutionSha256"] != record_sha):
                raise ConformanceError("ProofMismatch")
            events = [evidence._runtime_json(line, {
                "event": evidence._constant("build"), "code": evidence._constant("CommandFailed"),
                "value": evidence._integer}, limit=512) for line in raw.splitlines()]
            _verify_source_break_events(record["exitCode"], events)
            if raw != b"".join(canonical_bytes(event) + b"\n" for event in events):
                raise ConformanceError("ProofMismatch")
        owner = identity
        started = record["startedMs"] if started is None else started
        previous_sequence, previous_end = sequence, record["endedMs"]
        commands.append({"sequence": sequence, "executionSha256": record_sha})
    return {
        "schemaVersion": 1, "qualification": False, "mode": "source-break-native-correspondence",
        "baselineSealSha256": expected_baseline_sha256,
        "summarySha256": hashlib.sha256(packet_data).hexdigest(),
        "sourceFrameSha256": source_sha, "inputsSha256": inputs_sha,
        "negativeDiagnosticsSha256": negative_sha, "runId": owner[0], "rootId": owner[1],
        "startedMs": started, "endedMs": previous_end, "commands": commands,
    }


def retained_recipe(scenario):
    from conformance_legacy import COMPOSITION_MARKERS, ARTIFACT_CONSUMER_OPERATIONS
    consumers = {
        "registration": "RegistrationConsumer.dll", "lifecycle": "LifecycleConsumer.dll",
        "configuration": "RetainedConfiguration.dll",
        "metadata-marker": "RetainedMarker.dll", "artifact-marker": "RetainedMarker.dll",
    }
    if scenario in consumers:
        assembly = consumers[scenario]
        expected = (scenario + "-compatible" if scenario.endswith("-marker") else COMPOSITION_MARKERS[assembly])
        return scenario, "retained/bin/Release/net10.0/", assembly, expected
    if scenario in ("memory", "sqlite"):
        return ("f06", "tests/fixtures/metadata/Consumer/bin/Release/net10.0/",
                "Hoard.Fixtures.Metadata.Consumer.dll", "metadata-package-consumer-compatible")
    if scenario in ("local", "object"):
        expected = {"qualification": False, "provider": scenario, "roundTrip": True,
                    "operations": list(ARTIFACT_CONSUMER_OPERATIONS)}
        return ("f06", "tests/fixtures/artifacts/Consumer/bin/Release/net10.0/",
                "Hoard.Fixtures.Artifacts.Consumer.dll", canonical_bytes(expected).decode("utf-8"))
    raise ConformanceError("UnsupportedProfile")


def stage_retained_runtime(run, baseline_sha256, scenario):
    from conformance_sources import read_bounded
    if run.state != "Active":
        raise ConformanceError("OwnershipInvalid")
    sealed = verify_prepared_baselines(run.root, baseline_sha256)
    baseline_id, prefix, assembly, _ = retained_recipe(scenario)
    baseline, = (entry for entry in sealed["entries"] if entry["id"] == baseline_id)
    images = {path.removeprefix(prefix): hashed
              for path, hashed in baseline["binaries"].items() if path.startswith(prefix)}
    stem = assembly.removesuffix(".dll")
    if (not {assembly, stem + ".deps.json", stem + ".runtimeconfig.json"} <= images.keys()
            or len(images) > 1024):
        raise ConformanceError("EvidenceIncomplete")
    runtime = run.root / "stores" / ("retained-compatibility-" + scenario)
    runtime.mkdir(mode=0o700)
    for relative, expected in images.items():
        original = run.root / "stores" / baseline_id / prefix / relative_path(relative)
        raw = read_bounded(original, 64 * 1024**2)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ConformanceError("InputChanged")
        destination = runtime / relative
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with destination.open("xb") as output:
            output.write(raw)
        destination.chmod(0o400)
    packages, platform = {}, {}
    for name in ("Abstractions", "Core", "Hosting", "Application"):
        filename = f"Hoard.{name}.dll"
        package = run.root / "feed/candidate" / f"Hoard.{name}.0.1.0.nupkg"
        no_symlinks(package)
        if not package.is_file() or package.stat().st_size > 64 * 1024**2:
            raise ConformanceError("InputChanged")
        package_sha = file_sha256(package)
        try:
            with zipfile.ZipFile(package) as archive:
                entries = [item for item in archive.infolist() if item.filename == "lib/net10.0/" + filename]
                if len(entries) != 1 or not 0 < entries[0].file_size <= 16 * 1024**2:
                    raise ConformanceError("InputChanged")
                raw = archive.read(entries[0])
        except zipfile.BadZipFile:
            raise ConformanceError("InputChanged") from None
        if file_sha256(package) != package_sha:
            raise ConformanceError("InputChanged")
        packages[package.name] = package_sha
        platform[filename] = hashlib.sha256(raw).hexdigest()
        destination = runtime / filename
        if destination.exists():
            destination.chmod(0o600)
        destination.write_bytes(raw)
        destination.chmod(0o400)
    verify_prepared_baselines(run.root, baseline_sha256)
    return {
        "scenario": scenario, "baselineId": baseline_id, "baselineSealSha256": baseline_sha256,
        "runtimePath": runtime.relative_to(run.root).as_posix(), "assembly": assembly,
        "frozenFiles": images, "candidatePackages": packages, "candidateAssemblies": platform,
        "stagedFiles": _hash_tree(runtime), "commonSuiteExecuted": False,
        "scope": "operational-consumer" if scenario in ("memory", "sqlite", "local", "object") else
                 "marker-only" if scenario.endswith("-marker") else "inherited-api",
    }


def retained_request(staged, output_path):
    scenario = staged["scenario"]
    _, _, _, expected = retained_recipe(scenario)
    names = [name for name in staged["stagedFiles"] if "/" not in name and name.endswith(".dll")
             and not name.startswith(("System.", "Microsoft.Extensions.", "Microsoft.AspNetCore."))]
    required = [staged["assembly"].removesuffix(".dll"), "Hoard.Abstractions"]
    if scenario not in ("memory", "sqlite", "local", "object"):
        required.append("Hoard.Hosting")
    else:
        family = "Metadata" if scenario in ("memory", "sqlite") else "Artifacts"
        provider = {"memory": "Memory", "sqlite": "Sqlite", "local": "Local", "object": "ObjectSemantics"}[scenario]
        required.append(f"Hoard.Fixtures.{family}.{provider}")
    return {
        "schemaVersion": 1, "scenario": scenario, "outputPath": output_path, "expectedOutput": expected,
        "images": [{"path": staged["runtimePath"] + "/" + name, "sha256": staged["stagedFiles"][name]}
                   for name in sorted(names)], "required": required}


def verify_retained_observation(raw, request, expected_sha256):
    if len(raw) > 1024**2 or hashlib.sha256(raw).hexdigest() != sha256(expected_sha256):
        raise ConformanceError("ProofMismatch")
    observed = load_json(raw)
    if (not isinstance(observed, dict) or set(observed) !=
            {"schemaVersion", "qualification", "scenario", "code", "loaded"}
            or type(observed["schemaVersion"]) is not int or observed["schemaVersion"] != 1
            or observed["qualification"] is not False or observed["scenario"] != request["scenario"]
            or observed["code"] != "None" or not isinstance(observed["loaded"], list)
            or not 2 <= len(observed["loaded"]) <= 128):
        raise ConformanceError("ProofMismatch")
    expected = {Path(image["path"]).stem: image["sha256"] for image in request["images"]}
    names = []
    for image in observed["loaded"]:
        if (not isinstance(image, dict) or set(image) != {"name", "sha256", "moduleVersionId"}
                or not isinstance(image["name"], str) or image["name"] not in expected
                or image["sha256"] != expected[image["name"]] or not isinstance(image["moduleVersionId"], str)):
            raise ConformanceError("ProofMismatch")
        try:
            mvid = uuid.UUID(image["moduleVersionId"])
        except ValueError:
            raise ConformanceError("ProofMismatch") from None
        if mvid.int == 0 or str(mvid) != image["moduleVersionId"]:
            raise ConformanceError("ProofMismatch")
        names.append(image["name"])
    if names != sorted(set(names)) or not set(request["required"]) <= set(names):
        raise ConformanceError("ProofMismatch")
    return observed


def execute_retained_consumers(run, candidate, candidate_sources, config, baseline_sha256, *, msbuild=None):
    from conformance_sources import read_bounded
    if type(run) is not OwnedRun or run.state != "Active":
        raise ConformanceError("OwnershipInvalid")
    verify_snapshot(candidate, candidate_sources)
    _build(run, candidate / OBSERVER_PROJECT, config, "compatibility-observer", msbuild=msbuild)
    verify_snapshot(candidate, candidate_sources)
    observer = (candidate / OBSERVER_PROJECT).parent / (
        "bin/Release/net10.0/Hoard.Conformance.Compatibility.Observer.dll")
    no_symlinks(observer)
    observer.chmod(0o400)
    observer_relative = observer.relative_to(run.root).as_posix()
    observer_sha = file_sha256(observer)
    records = []
    for scenario in RETAINED_SCENARIOS:
        staged = stage_retained_runtime(run, baseline_sha256, scenario)
        runtime = run.root / staged["runtimePath"]
        namespace = "retained-compatibility-" + scenario
        request_path, output_path = f"proofs/{namespace}-request.json", f"proofs/{namespace}-observation.json"
        manifest_path = f"proofs/{namespace}-staged.json"
        request = retained_request(staged, output_path)
        for path, document in ((request_path, request), (manifest_path, staged)):
            with (run.root / path).open("xb") as output:
                output.write(canonical_bytes(document))
            (run.root / path).chmod(0o400)
        workspace = run.root / "stores" / (namespace + "-workspace")
        workspace.mkdir(mode=0o700)
        env = {
            "DOTNET_STARTUP_HOOKS": str(observer), "HOARD_COMPATIBILITY_ROOT": str(run.root),
            "HOARD_COMPATIBILITY_REQUEST": request_path, "HOARD_METADATA_WORKSPACE": str(workspace)}
        if scenario in ("memory", "sqlite"):
            env["HOARD_METADATA_PROVIDER"] = scenario
        arguments = [scenario, str(workspace)] if scenario in ("local", "object") else []
        entry = runtime / staged["assembly"]
        verify_snapshot(runtime, staged["stagedFiles"])
        result = run.command(
            ["dotnet", str(entry), *arguments], cwd=workspace, kind="events", env=env,
            cache_id="retained-compatibility", timeout=120, record_execution=True,
            execution_inputs=(observer_relative, entry.relative_to(run.root).as_posix(), request_path, manifest_path),
            execution_outputs=(output_path,))
        sequence = run.command_sequence
        command_raw = run.read_execution_record(sequence)
        command = load_json(command_raw)
        raw = read_bounded(run.root / output_path, 1024**2)
        observed = verify_retained_observation(raw, request, command["outputFiles"].get(output_path))
        if (result.exit_code or len(result.events) != 1 or result.events[0] !=
                {"event": "test", "code": "None", "value": len(observed["loaded"])}):
            raise ConformanceError("CommandFailed")
        verify_snapshot(runtime, staged["stagedFiles"])
        if file_sha256(observer) != observer_sha:
            raise ConformanceError("InputChanged")
        for filename, expected in staged["candidatePackages"].items():
            no_symlinks(run.root / "feed/candidate" / filename)
            if file_sha256(run.root / "feed/candidate" / filename) != expected:
                raise ConformanceError("InputChanged")
        verify_prepared_baselines(run.root, baseline_sha256)
        records.append({
            "scenario": scenario, "scope": staged["scope"], "commonSuiteExecuted": False,
            "sequence": sequence, "executionSha256": hashlib.sha256(command_raw).hexdigest(),
            "requestSha256": file_sha256(run.root / request_path),
            "stagedSha256": file_sha256(run.root / manifest_path),
            "observationSha256": hashlib.sha256(raw).hexdigest(), "loadedAssemblies": len(observed["loaded"]),
        })
    verify_snapshot(candidate, candidate_sources)
    return {"schemaVersion": 1, "qualification": False, "mode": "retained-compatibility",
            "baselineSealSha256": baseline_sha256, "observerSha256": observer_sha, "scenarios": records}


def _command(run, args, *, cwd, cache_id, execution_inputs=(), execution_outputs=()):
    recording = ({"record_execution": True, "execution_inputs": execution_inputs,
                  "execution_outputs": execution_outputs} if execution_inputs or execution_outputs else {})
    observed = run.command(args, cwd=cwd, kind="build", cache_id=cache_id,
                           env={"DOTNET_ROLL_FORWARD": "Disable"}, **recording)
    if observed.exit_code or any(event["code"] != "None" for event in observed.events):
        codes = sorted({event["value"] for event in observed.events if event["code"] == "CommandFailed"})
        diagnostic = {"code": "CommandFailed", "compilerCodes": codes,
                      "commandSequence": run.command_sequence}
        if cache_id in {name for name, _, _, _ in BASELINES} | {"f06", "f06-artifacts"}:
            diagnostic["baselineId"] = cache_id
            if 1403 in codes:
                diagnostic["localArchives"] = local_archive_diagnostics(run.root / "feed" / cache_id)
        print(json.dumps(diagnostic), file=sys.stderr)
        raise ConformanceError("CommandFailed")


def local_archive_diagnostics(feed):
    result = {}
    for name in ("Hoard.Abstractions", "Hoard.Core", "Hoard.Hosting", "Hoard.Application"):
        path = feed / f"{name}.0.1.0.nupkg"
        no_symlinks(path)
        if not path.exists():
            continue
        if not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
            raise ConformanceError("OutputLimitExceeded")
        try:
            with zipfile.ZipFile(path) as archive:
                entry = archive.getinfo(f"lib/net10.0/{name}.dll")
                if entry.file_size > 16 * 1024 * 1024:
                    raise ConformanceError("OutputLimitExceeded")
                result[name] = {"archiveSha256": file_sha256(path),
                                "assemblySha256": hashlib.sha256(archive.read(entry)).hexdigest()}
        except (zipfile.BadZipFile, KeyError):
            raise ConformanceError("InputChanged") from None
    return result


def export_revision(repository, run, revision, name):
    code, _ = capture_control(
        ["git", "merge-base", "--is-ancestor", revision, "origin/main"], cwd=repository)
    if code:
        raise ConformanceError("InputChanged")
    destination = run.root / "stores" / name
    destination.mkdir(mode=0o700)
    archive = run.root / "stores" / f"{name}.tar"
    code, _ = capture_control(
        ["git", "archive", "--format=tar", f"--output={archive}", revision,
         "Directory.Build.props", "Directory.Packages.props", "global.json", "src", "tests", "specs"],
        cwd=repository)
    if code:
        raise ConformanceError("InputChanged")
    if archive.stat().st_size > 256 * 1024 * 1024:
        raise ConformanceError("InputChanged")
    with tarfile.open(archive) as source:
        members = source.getmembers()
        if (len(members) > 50_000 or sum(member.size for member in members) > 256 * 1024 * 1024
                or any(not (member.isfile() or member.isdir()) for member in members)):
            raise ConformanceError("InputChanged")
        source.extractall(destination, filter="data")
    return destination


def _hash_tree(root, *, exclude_outputs=False):
    return {
        path.relative_to(root).as_posix(): file_sha256(path)
        for path in sorted(root.rglob("*")) if path.is_file()
        and (not exclude_outputs or not {"bin", "obj"}.intersection(path.relative_to(root).parts))
    }


def _config(run, name):
    feed = run.root / "feed" / name
    feed.mkdir(mode=0o700)
    config = run.root / "stores" / f"{name}.NuGet.Config"
    config.write_bytes(synthetic_nuget_configuration(feed))
    return config, feed


def project_build_commands(project, config, *, feed=None, lock=None, properties=(), msbuild=None, update_lock=False):
    if msbuild is None:
        common = ["-p:UseSharedCompilation=false", "-nodeReuse:false", "-v", "quiet", *properties]
        if lock is not None:
            common.append("-p:NuGetLockFilePath=" + str(lock))
        restore = ["dotnet", "restore", str(project), "--force-evaluate" if update_lock else "--locked-mode",
                   "--configfile", str(config), *common]
        compile_command = ["dotnet", "build", str(project), "-c", "Release", "--no-restore", *common]
        pack = ["dotnet", "pack", str(project), "-c", "Release", "--no-build",
                "--no-restore", "-o", str(feed), *common]
    else:
        common = ["-nologo", "-p:UseSharedCompilation=false", "-nodeReuse:false", "-verbosity:quiet", *properties]
        if lock is not None:
            common.append("-p:NuGetLockFilePath=" + str(lock))
        restore = [*msbuild, str(project), "-target:Restore",
                   "-p:RestoreForceEvaluate=true" if update_lock else "-p:RestoreLockedMode=true",
                   "-p:RestoreConfigFile=" + str(config), *common]
        compile_command = [*msbuild, str(project), "-target:Build", "-p:Configuration=Release", *common]
        pack = [*msbuild, str(project), "-target:Pack", "-p:Configuration=Release",
                "-p:NoBuild=true", "-p:PackageOutputPath=" + str(feed), *common]
    return restore, compile_command, pack


def project_build_steps(project, config, *, feed=None, lock=None, properties=(), msbuild=None):
    restore, compile_command, pack = project_build_commands(
        project, config, feed=feed, lock=lock, properties=properties, msbuild=msbuild)
    if msbuild is None:
        return (restore, compile_command, pack) if feed is not None else (restore, compile_command)
    command = list(compile_command)
    command.append("-restore")
    # Restore properties replace build globals; preserve the entire original restore evaluation.
    for argument in restore[len(msbuild) + 2:]:
        switch, separator, value = argument.partition(":")
        if separator and switch.casefold() in ("-p", "-property", "/p", "/property"):
            command.append("-restoreProperty:" + value)
    if feed is not None:
        command[len(msbuild) + 1] = "-target:Pack"
        command.append("-p:PackageOutputPath=" + str(feed))
    return (command,)


def _build(run, project, config, name, *, pack=False, feed=None, source_root=None, preparations=None,
           properties=(), baseline=False, msbuild=None, execution_inputs=(), execution_outputs=()):
    lock_args = []
    if preparations is not None:
        alternate, record = prepare_project_lock(project, source_root, run.root / "feed" / name, name,
                                                 baseline=baseline)
        if alternate is not None:
            preparations.append(record)
            lock_args = [f"-p:NuGetLockFilePath={alternate}"]
        elif baseline:
            lock_args = [f"-p:NuGetLockFilePath={project.parent / 'Baseline/packages.lock.json'}"]
    records = []
    steps = project_build_steps(
        project, config, feed=feed if pack else None, properties=(*lock_args, *properties), msbuild=msbuild)
    for index, command in enumerate(steps):
        if execution_inputs or execution_outputs:
            _command(run, command, cwd=project.parent, cache_id=name, execution_inputs=execution_inputs,
                     execution_outputs=execution_outputs if index == len(steps) - 1 else ())
            records.append({"sequence": run.command_sequence,
                            "executionSha256": hashlib.sha256(
                                run.read_execution_record(run.command_sequence)).hexdigest()})
        else:
            _command(run, command, cwd=project.parent, cache_id=name)
    if pack:
        for package in feed.glob("*.nupkg"):
            canonicalize_acceptance_archive(package)
    return tuple(records)


def historical_binary_build_inputs(project, sources):
    if project not in HISTORICAL_BINARY_PROJECTS:
        raise ConformanceError("EvidenceIncomplete")
    variant = project.split("/", 1)[0]
    required = (
        "Directory.Build.props", "Directory.Packages.props", "global.json",
        "tests/fixtures/compatibility/Directory.Build.props",
        HISTORICAL_BINARY_FIXTURE + project,
        HISTORICAL_BINARY_FIXTURE + variant + "/packages.lock.json",
        HISTORICAL_BINARY_FIXTURE + ("Old/Contract.cs" if variant == "Old" else "Consumer/Program.cs"))
    if not set(required) <= sources.keys():
        raise ConformanceError("EvidenceIncomplete")
    return (
        HISTORICAL_BINARY_INPUTS, "stores/f06.NuGet.Config",
        *("stores/f06/" + path for path in required),
        *(("stores/f06/" + HISTORICAL_BINARY_IMAGES["baseline/" + name]
           for name in ("BinaryContract.dll", "BinaryContract.pdb")) if variant == "Consumer" else ()))


def historical_binary_build_properties(source, project):
    if project not in HISTORICAL_BINARY_PROJECTS:
        raise ConformanceError("EvidenceIncomplete")
    return (
        "-p:PathMap=" + str(source) + os.sep + "=/_/",
        *(("-p:ContractAssembly=" + str(source / HISTORICAL_BINARY_IMAGES["baseline/BinaryContract.dll"]),)
          if project.startswith("Consumer/") else ()))


def _freeze_build_inputs(run, paths):
    for relative in paths:
        path = run.root / relative
        no_symlinks(path)
        if not path.is_file() or path.stat().st_uid != os.getuid():
            raise ConformanceError("InputChanged")
        path.chmod(0o400)
    return paths


def _freeze_historical_binary_inputs(run, project, sources):
    return _freeze_build_inputs(run, historical_binary_build_inputs(project, sources))


def prepare(repository, run, *, prepare_local_archives=False, msbuild=None):
    frozen = export_revision(repository, run, BASELINE, "f06")
    specs = (*BASELINES, ("f06", BASELINE, None, None))
    entries = []
    for name, revision, recipe, project_file in specs:
        source = frozen if name == "f06" else export_revision(repository, run, revision, name)
        source_hashes = _hash_tree(source, exclude_outputs=True)
        config, feed = _config(run, name)
        preparations = [] if prepare_local_archives else None

        def build(project, configuration, cache_id, *, pack=False, feed=None, properties=(), execution_inputs=()):
            return _build(
                run, project, configuration, cache_id, pack=pack, feed=feed,
                source_root=source, preparations=preparations, msbuild=msbuild,
                properties=properties, execution_inputs=execution_inputs)

        for package in ("Abstractions", "Core", "Hosting", "Application"):
            project = source / f"src/Hoard.{package}/Hoard.{package}.csproj"
            if project.is_file():
                build(project, config, name, pack=True, feed=feed)
        if name == "f06":
            metadata_projects = (
                "metadata/Sqlite/Sqlite.csproj", "metadata/Memory/Memory.csproj",
                "metadata/HostAdapters/HostAdapters.csproj",
            )
            for relative in metadata_projects:
                build(source / "tests/fixtures" / relative, config, name, pack=True, feed=feed)
            build(source / "tests/fixtures/metadata/Consumer/Consumer.csproj", config, name)
            # F-06's artifact recipe deliberately consumes pre-F-06 metadata
            # binaries, not same-version recompilations against new abstractions.
            artifact_config, artifact_feed = _config(run, "f06-artifacts")
            for package in ("Abstractions", "Core", "Hosting", "Application"):
                filename = f"Hoard.{package}.0.1.0.nupkg"
                shutil.copy2(feed / filename, artifact_feed / filename)
            for package in ("Sqlite", "Memory", "HostAdapters"):
                filename = f"Hoard.Fixtures.Metadata.{package}.0.1.0.nupkg"
                shutil.copy2(run.root / "feed/artifact-marker" / filename, artifact_feed / filename)
            artifact_projects = (
                "artifacts/Local/Local.csproj", "artifacts/ObjectSemantics/ObjectSemantics.csproj",
                "artifacts/HostAdapters/HostAdapters.csproj",
            )
            for relative in artifact_projects:
                build(source / "tests/fixtures" / relative, artifact_config, "f06-artifacts",
                      pack=True, feed=artifact_feed)
            build(source / "tests/fixtures/artifacts/Consumer/Consumer.csproj", artifact_config, "f06-artifacts")
            inputs = {"schemaVersion": 1, "qualification": False, "mode": "historical-binary-inputs",
                      "baselineRevision": BASELINE, "sourceSha256": digest(source_hashes), "sources": source_hashes}
            with (run.root / HISTORICAL_BINARY_INPUTS).open("xb") as output:
                output.write(canonical_bytes(inputs))
            (run.root / HISTORICAL_BINARY_INPUTS).chmod(0o400)
            binary_commands = []
            project = HISTORICAL_BINARY_PROJECTS[0]
            binary_commands.extend(
                {**row, "project": project} for row in build(
                    source / HISTORICAL_BINARY_FIXTURE / project, config, name,
                    properties=historical_binary_build_properties(source, project),
                    execution_inputs=_freeze_historical_binary_inputs(run, project, source_hashes)))
            original_contract = source / HISTORICAL_BINARY_IMAGES["baseline/BinaryContract.dll"]
            if not original_contract.is_file():
                raise ConformanceError("EvidenceIncomplete")
            project = HISTORICAL_BINARY_PROJECTS[1]
            binary_commands.extend(
                {**row, "project": project} for row in build(
                    source / HISTORICAL_BINARY_FIXTURE / project, config, name,
                    properties=historical_binary_build_properties(source, project),
                    execution_inputs=_freeze_historical_binary_inputs(run, project, source_hashes)))
            binary_preparation = {
                "schemaVersion": 1, "qualification": False, "mode": "historical-binary-preparation",
                "baselineRevision": BASELINE, "inputsSha256": file_sha256(run.root / HISTORICAL_BINARY_INPUTS),
                "commands": binary_commands}
            binary_preparation_path = source / "tests/fixtures" / HISTORICAL_BINARY_PREPARATION
            for path in (binary_preparation_path, run.root / HISTORICAL_BINARY_PREPARATION_PROOF):
                with path.open("xb") as output:
                    output.write(canonical_bytes(binary_preparation))
                path.chmod(0o400)
            recipes = {relative: file_sha256(source / "tests/fixtures" / relative)
                       for relative in (*metadata_projects, *artifact_projects, "metadata/Consumer/Consumer.csproj",
                                        "artifacts/Consumer/Consumer.csproj",
                                        *("compatibility/BinaryMemberRemoval/" + project
                                          for project in HISTORICAL_BINARY_PROJECTS))}
            recipes[HISTORICAL_BINARY_PREPARATION] = file_sha256(binary_preparation_path)
        else:
            if name == "artifact-marker":
                for relative in ("metadata/Sqlite/Sqlite.csproj", "metadata/Memory/Memory.csproj",
                                 "metadata/HostAdapters/HostAdapters.csproj"):
                    build(source / "tests/fixtures" / relative, config, name, pack=True, feed=feed)
            target = source / "retained"
            shutil.copytree(frozen / recipe, target, ignore=shutil.ignore_patterns("bin", "obj"))
            baseline_lock = target / "Baseline/packages.lock.json"
            if baseline_lock.is_file():
                shutil.copy2(baseline_lock, target / "packages.lock.json")
            versions = source / "retained/Directory.Packages.props"
            versions.write_text(
                '<Project><PropertyGroup><ManagePackageVersionsCentrally>false</ManagePackageVersionsCentrally>'
                '</PropertyGroup></Project>')
            recipes = _hash_tree(target, exclude_outputs=True)
            build(target / project_file, config, name)
        recipe_root = source / ("tests/fixtures" if name == "f06" else "retained")
        for sequence, record in enumerate(preparations or ()):
            record_path = recipe_root / "F07LockPreparation" / f"{sequence:04}.json"
            record_path.parent.mkdir(exist_ok=True, mode=0o700)
            with record_path.open("xb") as output:
                output.write(canonical_bytes(record) + b"\n")
            record_path.chmod(0o400)
            recipes[record_path.relative_to(recipe_root).as_posix()] = file_sha256(record_path)
        binaries = {
            path.relative_to(source).as_posix(): file_sha256(path)
            for path in sorted(source.rglob("*")) if path.is_file()
            and "bin" in path.relative_to(source).parts
            and path.suffix in (".dll", ".json", ".so", ".dylib", ".pdb")
        }
        if not binaries:
            raise ConformanceError("EvidenceIncomplete")
        for relative in binaries:
            (source / relative).chmod(0o400)
        if any(file_sha256(source / path) != expected for path, expected in source_hashes.items()):
            raise ConformanceError("InputChanged")
        locks = {path: value for path, value in source_hashes.items() if path.endswith("packages.lock.json")}
        locks.update({record["preparedLock"]: record["preparedSha256"] for record in preparations or ()})
        package_hashes = {
            path.name: {"sha256": file_sha256(path), "sha512": hashlib.sha512(path.read_bytes()).hexdigest()}
            for path in sorted(feed.glob("*.nupkg"))
        }
        if name == "f06":
            package_hashes.update({
                "artifacts/" + path.name: {
                    "sha256": file_sha256(path), "sha512": hashlib.sha512(path.read_bytes()).hexdigest()}
                for path in sorted(artifact_feed.glob("*.nupkg"))
            })
        entries.append({
            "id": name, "revision": revision, "sourceSha256": digest(source_hashes),
            "sources": source_hashes, "recipeSha256": digest(recipes), "recipes": recipes,
            "lockSha256": digest(locks), "locks": locks, "binaries": binaries, "packages": package_hashes,
        })
    evidence = {"schemaVersion": 3, "qualification": False, "mode": "preparation",
                "baselineRevision": BASELINE, "entries": entries}
    sealed = run.root / "proofs" / "baselines.json"
    with sealed.open("xb") as destination:
        destination.write(canonical_bytes(evidence) + b"\n")
    sealed.chmod(0o400)
    return sealed


def _prepared_baseline_document(root, expected_sha256):
    root = Path(root).absolute()
    no_symlinks(root)
    if (not root.is_dir() or root.stat().st_uid != os.getuid()
            or stat.S_IMODE(root.stat().st_mode) & 0o077):
        raise ConformanceError("OwnershipInvalid")
    seal = root / "proofs/baselines.json"
    no_symlinks(seal)
    if not seal.is_file() or seal.stat().st_size > MAX_REPORT_BYTES:
        raise ConformanceError("InputChanged")
    with seal.open("rb") as source:
        raw = source.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES or hashlib.sha256(raw).hexdigest() != sha256(expected_sha256):
        raise ConformanceError("InputChanged")
    evidence = load_json(raw)
    if (not isinstance(evidence, dict) or set(evidence) !=
            {"schemaVersion", "qualification", "mode", "baselineRevision", "entries"}
            or type(evidence["schemaVersion"]) is not int or evidence["schemaVersion"] not in (1, 2, 3)
            or evidence["qualification"] is not False or evidence["mode"] != "preparation"
            or evidence["baselineRevision"] != BASELINE or not isinstance(evidence["entries"], list)):
        raise ConformanceError("EvidenceIncomplete")
    revisions = {name: revision for name, revision, _, _ in (*BASELINES, ("f06", BASELINE, None, None))}
    if (len(evidence["entries"]) != len(revisions)
            or any(not isinstance(entry, dict) or not isinstance(entry.get("id"), str) for entry in evidence["entries"])
            or {entry.get("id") for entry in evidence["entries"] if isinstance(entry, dict)} != set(revisions)):
        raise ConformanceError("EvidenceIncomplete")
    fields = {"id", "revision", "sourceSha256", "sources", "recipeSha256", "recipes",
              "lockSha256", "locks", "binaries", "packages"}
    for entry in evidence["entries"]:
        if not isinstance(entry, dict) or set(entry) != fields or entry["revision"] != revisions[entry["id"]]:
            raise ConformanceError("EvidenceIncomplete")
        for field in ("sources", "recipes", "locks", "binaries", "packages"):
            if not isinstance(entry[field], dict) or not entry[field] or len(entry[field]) > 50_000:
                raise ConformanceError("EvidenceIncomplete")
        for field, hash_field in (("sources", "sourceSha256"), ("recipes", "recipeSha256"), ("locks", "lockSha256")):
            if digest(entry[field]) != sha256(entry[hash_field]):
                raise ConformanceError("InputChanged")
        if evidence["schemaVersion"] == 3 and entry["id"] == "f06":
            required_recipes = {"compatibility/BinaryMemberRemoval/" + project
                                for project in HISTORICAL_BINARY_PROJECTS}
            if (not set(HISTORICAL_BINARY_IMAGES.values()) <= set(entry["binaries"])
                    or not required_recipes <= set(entry["recipes"])):
                raise ConformanceError("EvidenceIncomplete")
    return evidence


def verify_prepared_baselines(root, expected_sha256):
    root = Path(root).absolute()
    evidence = _prepared_baseline_document(root, expected_sha256)
    seal = root / "proofs/baselines.json"
    for entry in evidence["entries"]:
        source = root / "stores" / entry["id"]
        no_symlinks(source)
        count = 0
        for path in source.rglob("*"):
            count += 1
            if count > 50_000 or path.is_symlink():
                raise ConformanceError("InputChanged")
        expected_sources = dict(entry["sources"])
        if entry["id"] != "f06":
            expected_sources.update({"retained/" + path: value for path, value in entry["recipes"].items()})
        elif evidence["schemaVersion"] >= 2:
            for path, value in entry["recipes"].items():
                relative = "tests/fixtures/" + path
                if relative in expected_sources and expected_sources[relative] != value:
                    raise ConformanceError("InputChanged")
                expected_sources[relative] = value
        expected_locks = {path: value for path, value in entry["sources"].items()
                          if path.endswith("packages.lock.json")}
        recipe_root = source / ("tests/fixtures" if entry["id"] == "f06" else "retained")
        for path in entry["recipes"]:
            if not path.startswith("F07LockPreparation/"):
                continue
            if evidence["schemaVersion"] < 2 or not re.fullmatch(r"F07LockPreparation/[0-9]{4}\.json", path):
                raise ConformanceError("InputChanged")
            record = load_json(read_lock(recipe_root / relative_path(path)))
            if (not isinstance(record, dict) or not isinstance(record.get("feedId"), str) or record["feedId"] not in
                    ({entry["id"], "f06-artifacts"} if entry["id"] == "f06" else {entry["id"]})):
                raise ConformanceError("InputChanged")
            verify_project_lock(record, source, root / "feed" / record["feedId"])
            if (record["project"] not in expected_sources
                    or expected_sources.get(record["originalLock"]) != record["originalSha256"]
                    or record["preparedLock"] in expected_locks):
                raise ConformanceError("InputChanged")
            expected_locks[record["preparedLock"]] = record["preparedSha256"]
        if entry["locks"] != expected_locks:
            raise ConformanceError("InputChanged")
        if _hash_tree(source, exclude_outputs=True) != expected_sources:
            raise ConformanceError("InputChanged")
        for field in ("sources", "recipes", "locks", "binaries"):
            base = source if field != "recipes" else source / ("tests/fixtures" if entry["id"] == "f06" else "retained")
            for relative, expected in entry[field].items():
                path = base / relative_path(relative)
                no_symlinks(path)
                if not path.is_file() or file_sha256(path) != sha256(expected):
                    raise ConformanceError("InputChanged")
        actual_binaries = {
            path.relative_to(source).as_posix(): file_sha256(path)
            for path in source.rglob("*") if path.is_file()
            and "bin" in path.relative_to(source).parts
            and path.suffix in ((".dll", ".json", ".so", ".dylib", ".pdb") if evidence["schemaVersion"] == 3
                                else (".dll", ".json", ".so", ".dylib"))
        }
        if actual_binaries != entry["binaries"]:
            raise ConformanceError("InputChanged")
        feeds = {entry["id"]: set()}
        for relative, expected in entry["packages"].items():
            relative_path(relative)
            artifact = relative.startswith("artifacts/")
            filename = relative.removeprefix("artifacts/") if artifact else relative
            if "/" in filename or not filename.endswith(".nupkg") or artifact and entry["id"] != "f06":
                raise ConformanceError("EvidenceIncomplete")
            feed = "f06-artifacts" if artifact else entry["id"]
            feeds.setdefault(feed, set()).add(filename)
            package = root / "feed" / feed / filename
            no_symlinks(package)
            if (not isinstance(expected, dict) or set(expected) != {"sha256", "sha512"}
                    or not package.is_file() or file_sha256(package) != sha256(expected["sha256"])
                    or hashlib.sha512(package.read_bytes()).hexdigest() != expected["sha512"]):
                raise ConformanceError("InputChanged")
        for feed, expected in feeds.items():
            if {path.name for path in (root / "feed" / feed).glob("*.nupkg")} != expected:
                raise ConformanceError("InputChanged")
    if file_sha256(seal) != expected_sha256:
        raise ConformanceError("InputChanged")
    return evidence


def stage_historical_binary_fixture(run, runtime, seal_sha256):
    import conformance_evidence as evidence

    if run.state != "Active":
        raise ConformanceError("OwnershipInvalid")
    prepared = verify_prepared_baselines(run.root, seal_sha256)
    if prepared["schemaVersion"] != 3:
        raise ConformanceError("EvidenceIncomplete")
    entry = next(row for row in prepared["entries"] if row["id"] == "f06")
    try:
        prefix = Path(runtime).absolute().relative_to(run.root).as_posix()
    except ValueError as error:
        raise ConformanceError("InputChanged") from error
    images = []
    with evidence._input_root(run.root) as (_, root):
        for target, original in HISTORICAL_BINARY_IMAGES.items():
            source = "stores/f06/" + original
            relative = prefix + "/compatibility-fixtures/" + target
            no_symlinks(run.root / relative)
            with evidence._input_parent(root, relative) as (parent, name):
                temporary = ".historical-binary-" + uuid.uuid4().hex + ".tmp"
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o400, dir_fd=parent)
                try:
                    with os.fdopen(descriptor, "wb") as output:
                        hashed, _ = evidence._source_file(
                            root, source, remaining=16 * 1024**2,
                            deadline=time.monotonic() + 5, target=output)
                        if hashed != entry["binaries"][original]:
                            raise ConformanceError("InputChanged")
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                finally:
                    try:
                        os.unlink(temporary, dir_fd=parent)
                    except FileNotFoundError:
                        pass
            actual, _ = evidence._source_file(
                root, relative, remaining=16 * 1024**2, deadline=time.monotonic() + 5)
            if actual != hashed:
                raise ConformanceError("InputChanged")
            images.append({"source": source, "runtime": relative, "sha256": hashed})
    verify_prepared_baselines(run.root, seal_sha256)
    return {"schemaVersion": 1, "qualification": False, "mode": "historical-binary-staging",
            "baselineSealSha256": seal_sha256, "images": images}


def inspect_historical_binary_preparation(root, seal_sha256, *, msbuild=None, retained=False):
    """Replay retained correspondence; native authority requires the original live-captured token."""
    import conformance_evidence as evidence

    root = Path(root).absolute()
    prepared = (_prepared_baseline_document(root, seal_sha256) if retained
                else verify_prepared_baselines(root, seal_sha256))
    if prepared["schemaVersion"] != 3:
        raise ConformanceError("EvidenceIncomplete")
    entry = next(row for row in prepared["entries"] if row["id"] == "f06")
    hashed, raw = evidence._readonly_report_proof(root, HISTORICAL_BINARY_PREPARATION_PROOF)
    if not retained:
        original_sha, _ = evidence._readonly_report_proof(
            root, "stores/f06/tests/fixtures/" + HISTORICAL_BINARY_PREPARATION)
        if original_sha != hashed:
            raise ConformanceError("ProofMismatch")
    packet = evidence._runtime_json(raw, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "mode": evidence._constant("historical-binary-preparation"),
        "baselineRevision": evidence._constant(BASELINE), "inputsSha256": sha256,
        "commands": evidence._list(evidence._record({
            "sequence": evidence._integer, "executionSha256": sha256,
            "project": evidence._one_of(*HISTORICAL_BINARY_PROJECTS)}), 4, minimum=2),
    }, limit=64 * 1024)
    inputs_sha, inputs_raw = evidence._readonly_report_proof(root, HISTORICAL_BINARY_INPUTS)
    inputs = evidence._runtime_json(inputs_raw, {
        "schemaVersion": evidence._constant(1), "qualification": evidence._constant(False),
        "mode": evidence._constant("historical-binary-inputs"),
        "baselineRevision": evidence._constant(BASELINE),
        "sourceSha256": sha256, "sources": evidence._hash_map,
    }, limit=MAX_REPORT_BYTES)
    if (entry["recipes"].get(HISTORICAL_BINARY_PREPARATION) != hashed
            or packet["inputsSha256"] != inputs_sha or inputs["sources"] != entry["sources"]
            or inputs["sourceSha256"] != entry["sourceSha256"]):
        raise ConformanceError("ProofMismatch")
    if not retained:
        for relative in HISTORICAL_BINARY_IMAGES.values():
            actual, _ = evidence._readonly_report_proof(root, "stores/f06/" + relative)
            if actual != entry["binaries"][relative]:
                raise ConformanceError("InputChanged")
        evidence.verify_synthetic_source_mapping(root, "stores/f06.NuGet.Config", "feed/f06")
    expected = []
    for project in HISTORICAL_BINARY_PROJECTS:
        properties = historical_binary_build_properties(root / "stores/f06", project)
        target = root / "stores/f06" / HISTORICAL_BINARY_FIXTURE / project
        paths = historical_binary_build_inputs(project, entry["sources"])
        physical = {
            HISTORICAL_BINARY_INPUTS: inputs_sha,
            "stores/f06.NuGet.Config": hashlib.sha256(
                evidence.synthetic_nuget_configuration(root / "feed/f06")).hexdigest(),
            **{"stores/f06/" + path: inputs["sources"][path] for path in inputs["sources"]
               if "stores/f06/" + path in paths},
            **{"stores/f06/" + path: entry["binaries"][path] for path in HISTORICAL_BINARY_IMAGES.values()
               if "stores/f06/" + path in paths},
        }
        if (set(physical) != set(paths)
                or not retained and evidence.input_manifest(root, paths) != physical):
            raise ConformanceError("ProofMismatch")
        for arguments in project_build_steps(
                target, root / "stores/f06.NuGet.Config", properties=properties, msbuild=msbuild):
            expected.append((project, arguments, target.parent, physical))
    if len(expected) != len(packet["commands"]):
        raise ConformanceError("ProofMismatch")
    previous_sequence, previous_end, started, owner = 0, 0, None, None
    commands = []
    for declaration, (project, arguments, cwd, physical) in zip(packet["commands"], expected):
        sequence = declaration["sequence"]
        if declaration["project"] != project or sequence <= previous_sequence:
            raise ConformanceError("ProofMismatch")
        record_sha, record_raw = evidence._readonly_report_proof(
            root, f"proofs/execution-command-{sequence:04}.json")
        record = evidence._runtime_json(record_raw, {
            "schemaVersion": evidence._constant(1), "sequence": evidence._constant(sequence),
            "childPid": evidence._integer, "childStartSha256": sha256,
            "startedMs": evidence._number, "endedMs": evidence._number,
            "exitCode": evidence._constant(0), "diagnosticCode": evidence._constant("None"),
            "groupState": evidence._constant("Exited"), "scope": evidence._constant("ordinary"),
            "runId": evidence._uuid, "rootId": evidence.stable_id,
            "argvSha256": sha256, "cwdSha256": sha256, "inputFiles": evidence._hash_map,
        }, limit=64 * 1024)
        identity = (record["runId"], record["rootId"])
        if (record_sha != declaration["executionSha256"] or record["childPid"] == 0
                or record["childStartSha256"] == "0" * 64
                or record["argvSha256"] != digest(arguments)
                or record["cwdSha256"] != hashlib.sha256(str(cwd).encode()).hexdigest()
                or record["inputFiles"] != physical
                or record["startedMs"] < previous_end or record["endedMs"] < record["startedMs"]
                or owner is not None and owner != identity):
            raise ConformanceError("ProofMismatch")
        owner = identity
        started = record["startedMs"] if started is None else started
        previous_sequence, previous_end = sequence, record["endedMs"]
        commands.append({"sequence": sequence, "executionSha256": record_sha})
    return {"schemaVersion": 1, "qualification": False, "mode": "historical-binary-native-preparation",
            "baselineSealSha256": seal_sha256, "preparationSha256": hashed, "inputsSha256": inputs_sha,
            "runId": owner[0], "rootId": owner[1], "startedMs": started, "endedMs": previous_end,
            "commands": commands}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--verify-sha256")
    parser.add_argument("--prepare-local-archives", action="store_true")
    options = parser.parse_args()
    run = None
    try:
        if options.verify_sha256 is not None:
            if options.prepare_local_archives:
                raise ConformanceError("PrerequisiteMissing")
            verified = verify_prepared_baselines(options.evidence, options.verify_sha256)
            print(json.dumps({"mode": "verification", "qualification": False,
                              "baselines": len(verified["entries"]), "proofSha256": options.verify_sha256}))
            return 0
        run = OwnedRun.allocate(options.evidence, options.root, profile="baseline")
        sealed = prepare(options.root.resolve(), run, prepare_local_archives=options.prepare_local_archives)
        print(json.dumps({"mode": "preparation", "qualification": False,
                          "proofSha256": file_sha256(sealed)}))
        run.transition("Settling")
        return 0
    except (ConformanceError, OSError, tarfile.TarError) as error:
        code = str(error) if isinstance(error, ConformanceError) else "PrerequisiteMissing"
        print(json.dumps({"mode": "preparation", "qualification": False, "code": code}), file=sys.stderr)
        if run is not None and run.state in ("Active", "Allocated"):
            run.transition("Settling")
            if run.live_children():
                run.transition("Retained")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
