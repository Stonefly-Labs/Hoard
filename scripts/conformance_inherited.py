"""Exact source-owned inherited composition inventories and opaque discovery admission."""

from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from types import SimpleNamespace
import xml.etree.ElementTree as ET

from conformance_evidence import ConformanceError, digest, load_json

INVENTORY_PATH = "tests/fixtures/conformance/baselines/composition-inventory.json"
BASELINE = "9389016c0285c79f6f515f59805a5a41c69b0767"
INVENTORY_SHA256 = "9b45196787d57b0437c14e73345b1a0ba4b1544a41d95f7fca3ea32b7635de50"
GROUPS = frozenset(("lifecycle", "configuration", "discovery"))
ASSEMBLIES = frozenset(("Hoard.Composition.Tests", "Hoard.Architecture.Tests"))


@contextmanager
def controller_transport(repository, owner, *, sdk_package=None, logger_path=None):
    import configuration_evidence as configuration
    import discovery_evidence as discovery
    import foundation_evidence as foundation
    import lifecycle_evidence as lifecycle
    import conformance_legacy as legacy
    from conformance_lock_preparation import prepare_project_lock, verify_project_lock

    repository, owner = Path(repository).resolve(strict=True), Path(owner).resolve(strict=True)
    if owner == repository or owner.is_relative_to(repository):
        raise ConformanceError("OwnershipInvalid")
    modules = (foundation, lifecycle, configuration, discovery)
    originals = {module: module.run for module in modules}
    original_graph = foundation.inspection_graph
    original_copy = foundation.copy_source
    original_processes, original_selectors = configuration.subprocess, configuration.selectors
    environment = {key: value for key, value in os.environ.items()
                   if key.startswith("HOARD_") or key == "NUGET_PACKAGES"}
    preparations = {}
    state = {"lockDerivations": [], "inputFiles": {}, "phase": "preparation", "commandSequence": 0}
    runtime_inputs = {}
    if sdk_package is not None or logger_path is not None:
        if sdk_package is None or logger_path is None:
            raise ConformanceError("PrerequisiteMissing")
        for path in (sdk_package, logger_path):
            path = Path(path)
            legacy.no_symlinks(path)
            if (not path.is_absolute() or not path.is_file()
                    or not path.resolve(strict=True).is_relative_to(owner)
                    or not 0 < path.stat().st_size <= 64 * 1024**2):
                raise ConformanceError("OwnershipInvalid")
            runtime_inputs[path] = legacy._hash(path)

    def command(*arguments, cwd=None, env=None, expected=None, input=None):
        if not arguments or any(not isinstance(argument, str) for argument in arguments):
            raise ConformanceError("OwnershipInvalid")
        state["commandSequence"] += 1
        arguments = list(arguments)
        effective = dict(env or {})
        bound = {}
        runtime = {}
        if arguments[:2] == ["dotnet", "test"] and runtime_inputs:
            bound.update(runtime_inputs)
            runtime = {"sdk_package": sdk_package, "logger_path": logger_path}
            for path, hashed in runtime_inputs.items():
                if legacy._hash(path) != hashed:
                    raise ConformanceError("InputChanged")
                state["inputFiles"][path.relative_to(owner).as_posix()] = hashed
        for key in ("HOARD_FOUNDATION_EVIDENCE", "HOARD_LIFECYCLE_EVIDENCE",
                    "HOARD_CONFIGURATION_EVIDENCE", "HOARD_DISCOVERY_EVIDENCE"):
            if key not in effective and key in os.environ:
                effective[key] = os.environ[key]
            if key in effective:
                path = Path(effective[key])
                legacy.no_symlinks(path)
                if (not path.is_absolute() or not path.is_file()
                        or not path.resolve(strict=True).is_relative_to(owner)
                        or not 0 < path.stat().st_size <= 16 * 1024**2):
                    raise ConformanceError("OwnershipInvalid")
                path = path.resolve(strict=True)
                bound[path] = legacy._hash(path)
                state["inputFiles"][path.relative_to(owner).as_posix()] = bound[path]
        if arguments[:2] == ["dotnet", "restore"] and "--configfile" in arguments:
            project = Path(arguments[2]).resolve(strict=True)
            configuration_file = Path(arguments[arguments.index("--configfile") + 1]).resolve(strict=True)
            if not project.is_relative_to(owner) or not configuration_file.is_relative_to(owner):
                raise ConformanceError("OwnershipInvalid")
            feeds = ET.parse(configuration_file).findall("./packageSources/add[@key='local']")
            if len(feeds) != 1:
                raise ConformanceError("InputChanged")
            feed = Path(feeds[0].get("value", "")).resolve(strict=True)
            if not feed.is_relative_to(owner):
                raise ConformanceError("OwnershipInvalid")
            if "--locked-mode" in arguments and (project.parent / "packages.lock.json").is_file():
                key = (project, feed)
                if key not in preparations:
                    alternate, record = prepare_project_lock(project, owner, feed, "inherited-controller")
                    preparations[key] = alternate, record
                    if record is not None:
                        state["lockDerivations"].append(record)
                alternate, record = preparations[key]
                if record is not None:
                    verify_project_lock(record, owner, feed)
                    arguments.append("-p:NuGetLockFilePath=" + str(alternate))
        try:
            return legacy.composition_controller_command(
                arguments, cwd=repository if arguments[0] == "git" else cwd,
                env=effective, expected=expected, input=input, **runtime)
        except RuntimeError as error:
            codes = ("CommandFailed", "UnknownDiagnostic", "PrerequisiteMissing", "OutputLimitExceeded")
            code = next((code for code in codes
                         if str(error) == "Legacy composition command " + code + "."), "EvidenceIncomplete")
            print(json.dumps({
                "qualification": False, "phase": "inherited-controller-failure",
                "controller": state["phase"] if state["phase"] in (
                    "foundation", "lifecycle", "configuration", "discovery") else "preparation",
                "commandSequence": state["commandSequence"],
                "operation": arguments[1] if len(arguments) >= 2 and arguments[0] == "dotnet" and arguments[1] in (
                    "restore", "build", "pack", "format", "test", "--version") else "control",
                "code": code,
            }), flush=True)
            raise
        finally:
            if any(legacy._hash(path) != hashed for path, hashed in bound.items()):
                raise ConformanceError("InputChanged")

    def text_command(*arguments, **kwargs):
        return command(*arguments, **kwargs).stdout

    def graph(projects, ownership, *, resolve=None):
        return original_graph(projects, ownership, resolve=resolve or legacy.resolve_project)

    def copy_source(source, target, *, include_outputs=False):
        source, target = Path(source), Path(target)
        for path in (source, target):
            legacy.no_symlinks(path)
            if not path.is_absolute() or not path.resolve().is_relative_to(owner):
                raise ConformanceError("OwnershipInvalid")
        if source == owner or target.resolve().is_relative_to(source.resolve()):
            raise ConformanceError("OwnershipInvalid")
        count, size = 0, 0
        ignored = shutil.ignore_patterns(*(() if include_outputs else ("bin", "obj", "*.nupkg")))
        for directory, directories, filenames in os.walk(source, followlinks=False):
            omitted = ignored(directory, directories + filenames)
            directories[:] = [name for name in directories if name not in omitted]
            for name in (*directories, *(name for name in filenames if name not in omitted)):
                path = Path(directory) / name
                legacy.no_symlinks(path)
                count += 1
                if path.is_file():
                    size += path.stat().st_size
                elif not path.is_dir():
                    raise ConformanceError("OwnershipInvalid")
                if count > 50000 or size > 256 * 1024**2:
                    raise ConformanceError("OutputLimitExceeded")
        result = shutil.copytree(source, target) if include_outputs else original_copy(source, target)
        for path in (target, *target.rglob("*")):
            path.chmod(0o700 if path.is_dir() else 0o600 | (path.stat().st_mode & 0o111))
        return result

    try:
        foundation.run = command
        foundation.inspection_graph = graph
        foundation.copy_source = copy_source
        for module in (lifecycle, configuration, discovery):
            module.run = text_command
        configuration.subprocess = SimpleNamespace(
            Popen=lambda args, **kwargs: legacy.PublicationChild(args, owner=owner, **kwargs),
            PIPE=legacy.subprocess.PIPE, STDOUT=legacy.subprocess.STDOUT)
        configuration.selectors = SimpleNamespace(
            DefaultSelector=legacy.PublicationSelector, EVENT_READ=legacy.selectors.EVENT_READ)
        yield state
        for (project, feed), (_, record) in preparations.items():
            if record is not None:
                verify_project_lock(record, owner, feed)
    finally:
        configuration.subprocess, configuration.selectors = original_processes, original_selectors
        foundation.inspection_graph = original_graph
        foundation.copy_source = original_copy
        for module, original in originals.items():
            module.run = original
        for key in list(os.environ):
            if key.startswith("HOARD_") or key == "NUGET_PACKAGES":
                del os.environ[key]
        os.environ.update(environment)


def inventory(data, sources):
    value = load_json(data)
    if digest(value) != INVENTORY_SHA256:
        raise ConformanceError("ProofMismatch")
    if (not isinstance(value, dict) or set(value) != {
            "schemaVersion", "baselineRevision", "qualification", "identityOrigin", "sourceFiles",
            "controllerSources", "lifecycleCases", "caseMethods", "entries", "groupParameters"}
            or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1
            or value["baselineRevision"] != BASELINE or value["qualification"] is not False
            or value["identityOrigin"] != "baseline-source-methods-and-exact-parameter-counts"
            or value["lifecycleCases"] != [f"LC-{number:02}" for number in range(1, 41)]
            or not isinstance(value["sourceFiles"], dict) or not value["sourceFiles"]
            or not isinstance(value["controllerSources"], dict) or len(value["controllerSources"]) != 7
            or not isinstance(value["caseMethods"], dict)
            or set(value["caseMethods"]) != {*(f"CFG-{number:02}" for number in range(1, 37)),
                                            *(f"D{number:02}" for number in range(1, 41))}
            or not isinstance(value["entries"], list) or not 1 <= len(value["entries"]) <= 10000
            or not isinstance(value["groupParameters"], dict) or value["groupParameters"].keys() != GROUPS):
        raise ConformanceError("EvidenceSchemaInvalid")
    for path, hashed in value["sourceFiles"].items():
        if (not isinstance(path, str) or not isinstance(hashed, str)
                or re.fullmatch(r"[0-9a-f]{64}", hashed) is None or sources.get(path) != hashed):
            raise ConformanceError("InputChanged")
    for path, hashed in value["controllerSources"].items():
        if (not isinstance(path, str) or not isinstance(hashed, str)
                or re.fullmatch(r"[0-9a-f]{64}", hashed) is None):
            raise ConformanceError("EvidenceSchemaInvalid")
    methods = {}
    totals = Counter()
    for entry in value["entries"]:
        if (not isinstance(entry, dict) or set(entry) != {
                "fullyQualifiedName", "parameterCount", "group", "sourcePath", "sourceSha256"}
                or not isinstance(entry["fullyQualifiedName"], str)
                or re.fullmatch(r"Hoard\.(?:Composition|Architecture)\.Tests\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+",
                                entry["fullyQualifiedName"]) is None
                or entry["fullyQualifiedName"] in methods
                or not isinstance(entry["group"], str) or entry["group"] not in GROUPS
                or type(entry["parameterCount"]) is not int or not 1 <= entry["parameterCount"] <= 10000
                or not isinstance(entry["sourcePath"], str)
                or value["sourceFiles"].get(entry["sourcePath"]) != entry["sourceSha256"]):
            raise ConformanceError("WitnessMissing")
        methods[entry["fullyQualifiedName"]] = entry
        totals[entry["group"]] += entry["parameterCount"]
    if dict(totals) != value["groupParameters"]:
        raise ConformanceError("WitnessMissing")
    for required in value["caseMethods"].values():
        if (not isinstance(required, list) or not required
                or any(not isinstance(method, str) or method not in methods for method in required)
                or len(set(required)) != len(required)):
            raise ConformanceError("WitnessMissing")
    return methods


def admit_discovery(data, methods, *, assembly):
    if assembly not in ASSEMBLIES:
        raise ConformanceError("WitnessMissing")
    expected = {name: entry for name, entry in methods.items() if name.startswith(assembly + ".")}
    rows = load_json(data)
    if not expected or not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
        raise ConformanceError("WitnessMissing")
    seen = set()
    counts = Counter()
    admitted = []
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"testIdentity", "fullyQualifiedName"}
                or not isinstance(row["fullyQualifiedName"], str) or row["fullyQualifiedName"] not in expected
                or not isinstance(row["testIdentity"], str)
                or re.fullmatch(re.escape(row["fullyQualifiedName"])
                                + r'\(testCaseSha256: "[0-9a-f]{64}"\)', row["testIdentity"]) is None
                or row["testIdentity"] in seen):
            raise ConformanceError("WitnessMissing")
        seen.add(row["testIdentity"])
        counts[row["fullyQualifiedName"]] += 1
        entry = expected[row["fullyQualifiedName"]]
        admitted.append({
            **row, "assemblyId": "test-assembly", "packageId": "Hoard.Testing.Conformance",
            "bindingId": "none", "matrixId": "inherited." + entry["group"],
            "caseId": "inherited-" + entry["group"], "assertionSymbol": None,
        })
    if dict(counts) != {name: entry["parameterCount"] for name, entry in expected.items()}:
        raise ConformanceError("WitnessMissing")
    return sorted(admitted, key=lambda row: row["testIdentity"])


def execution_scopes(discoveries, methods):
    if not isinstance(discoveries, dict) or set(discoveries) != ASSEMBLIES:
        raise ConformanceError("WitnessMissing")
    scopes = {}
    for assembly in sorted(ASSEMBLIES):
        for row in admit_discovery(discoveries[assembly], methods, assembly=assembly):
            key = (assembly, row["fullyQualifiedName"].rsplit(".", 1)[0])
            scopes.setdefault(key, []).append(row)
    return {key: tuple(rows) for key, rows in sorted(scopes.items())}


CONTROLLER_BASELINES = "proofs/inherited-controller-baselines.json"


def _controller_baseline_files(owner, roots):
    import conformance_legacy as legacy
    from conformance_evidence import file_sha256

    files, size = {}, 0
    for root in roots:
        legacy.no_symlinks(root)
        if not root.is_dir() or not root.resolve(strict=True).is_relative_to(owner):
            raise ConformanceError("OwnershipInvalid")
        for directory, directories, filenames in os.walk(root, followlinks=False):
            if Path(directory) == root:
                directories[:] = [name for name in directories if name not in (
                    "cache", "old-cache", "old-platform-cache", "baseline-cache", "baseline-replay-cache")]
            for name in (*directories, *filenames):
                path = Path(directory) / name
                legacy.no_symlinks(path)
                if path.is_file():
                    size += path.stat().st_size
                    if len(files) >= 50000 or size > 256 * 1024**2:
                        raise ConformanceError("OutputLimitExceeded")
                    files[path.relative_to(owner).as_posix()] = file_sha256(path)
                elif not path.is_dir():
                    raise ConformanceError("OwnershipInvalid")
    return dict(sorted(files.items()))


def prepare_controller_baselines(repository, run):
    """Seal historical controller inputs before any candidate command or feed exists."""
    import configuration_evidence as configuration
    import discovery_evidence as discovery
    import lifecycle_evidence as lifecycle
    import conformance_baselines as baselines
    import conformance_legacy as legacy
    from conformance_evidence import synthetic_nuget_configuration

    if run.command_sequence != 0 or (run.root / "feed/candidate").exists():
        raise ConformanceError("InputChanged")
    historical = run.root / "stores/inherited-historical"
    if historical.exists() or (run.root / CONTROLLER_BASELINES).exists():
        raise ConformanceError("InputChanged")
    frozen = baselines.export_revision(repository, run, BASELINE, "inherited-f06-recipes")
    recipes = baselines._hash_tree(frozen, exclude_outputs=True)
    historical.mkdir(mode=0o700)
    roots, retained = [frozen], {}
    with controller_transport(repository, run.root) as controls:
        controls["phase"] = "lifecycle"
        print(json.dumps({"qualification": False, "phase": "inherited-historical-preparation",
                          "controller": "lifecycle"}), flush=True)
        registration_root = historical / "registration"
        registration_root.mkdir(mode=0o700)
        feed = registration_root / "feed"
        feed.mkdir(mode=0o700)
        config = registration_root / "NuGet.Config"
        config.write_bytes(synthetic_nuget_configuration(feed))
        registration = lifecycle.prepare_registration_baseline(frozen, registration_root, config, False)
        feed.rmdir()
        roots.append(registration_root)
        for phase, module in (("configuration", configuration), ("discovery", discovery)):
            controls["phase"] = phase
            print(json.dumps({"qualification": False, "phase": "inherited-historical-preparation",
                              "controller": phase}), flush=True)
            target = historical / phase
            target.mkdir(mode=0o700)
            retained[phase] = module.prepare_baseline(frozen, target, False)
            roots.append(target)
    if baselines._hash_tree(frozen, exclude_outputs=True) != recipes:
        raise ConformanceError("InputChanged")
    files = _controller_baseline_files(run.root, roots)
    document = {
        "schemaVersion": 1, "qualification": False, "nativeContainment": False, "mode": "preparation",
        "runId": run.run_id, "rootId": run.root_id, "baselineRevision": BASELINE,
        "recipeSourceSha256": digest(recipes), "registration": registration, "retained": retained,
        "files": files,
    }
    path = run.root / CONTROLLER_BASELINES
    legacy._write(path, document)
    for relative in (*files, CONTROLLER_BASELINES):
        (run.root / relative).chmod(0o400)
    seal = {"path": CONTROLLER_BASELINES, "sha256": legacy._hash(path)}
    verify_controller_baselines(run, seal)
    return seal


def verify_controller_baselines(run, seal):
    import configuration_evidence as configuration
    import discovery_evidence as discovery
    import conformance_legacy as legacy
    from conformance_evidence import file_sha256, relative_path
    from conformance_sources import read_bounded

    if (not isinstance(seal, dict) or set(seal) != {"path", "sha256"}
            or seal["path"] != CONTROLLER_BASELINES or not isinstance(seal["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", seal["sha256"]) is None):
        raise ConformanceError("ProofMismatch")
    path = run.root / CONTROLLER_BASELINES
    legacy.no_symlinks(path)
    raw = read_bounded(path, 16 * 1024**2)
    if hashlib.sha256(raw).hexdigest() != seal["sha256"]:
        raise ConformanceError("InputChanged")
    value = load_json(raw)
    if (not isinstance(value, dict) or set(value) != {
            "schemaVersion", "qualification", "nativeContainment", "mode", "runId", "rootId",
            "baselineRevision", "recipeSourceSha256", "registration", "retained", "files"}
            or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1
            or value["qualification"] is not False or value["nativeContainment"] is not False
            or value["mode"] != "preparation" or value["runId"] != run.run_id or value["rootId"] != run.root_id
            or value["baselineRevision"] != BASELINE or not isinstance(value["recipeSourceSha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", value["recipeSourceSha256"]) is None
            or not isinstance(value["registration"], dict)
            or set(value["registration"]) != {"assembly", "sha256"}
            or not isinstance(value["retained"], dict) or set(value["retained"]) != {"configuration", "discovery"}
            or not isinstance(value["files"], dict) or not 1 <= len(value["files"]) <= 50000):
        raise ConformanceError("EvidenceSchemaInvalid")
    size = 0
    for relative, hashed in value["files"].items():
        path = run.root / relative_path(relative)
        legacy.no_symlinks(path)
        if not path.is_file():
            raise ConformanceError("InputChanged")
        if not isinstance(hashed, str) or re.fullmatch(r"[0-9a-f]{64}", hashed) is None:
            raise ConformanceError("EvidenceSchemaInvalid")
        size += path.stat().st_size
        if size > 256 * 1024**2:
            raise ConformanceError("OutputLimitExceeded")
        if file_sha256(path) != hashed:
            raise ConformanceError("InputChanged")
    entries = [value["registration"]]
    for phase, revision, names in (
            ("configuration", configuration.BASELINE, {"LegacyOptions", "LifecycleConsumer"}),
            ("discovery", discovery.BASELINE, {"RetainedLifecycle", "RetainedConfiguration", "LegacyOptions"})):
        retained = value["retained"][phase]
        if (not isinstance(retained, list) or len(retained) != len(names)
                or any(not isinstance(entry, dict) or not isinstance(entry.get("name"), str)
                       or entry.get("baseline") != revision or not isinstance(entry.get("assets"), str)
                       for entry in retained)
                or {entry["name"] for entry in retained} != names):
            raise ConformanceError("EvidenceSchemaInvalid")
        for entry in retained:
            assets = Path(entry["assets"])
            if (not assets.is_absolute() or not assets.is_relative_to(run.root)
                    or assets.relative_to(run.root).as_posix() not in value["files"]):
                raise ConformanceError("ProofMismatch")
        entries.extend(retained)
    for entry in entries:
        if (not isinstance(entry, dict) or not isinstance(entry.get("assembly"), str)
                or not isinstance(entry.get("sha256"), str)):
            raise ConformanceError("EvidenceSchemaInvalid")
        assembly = Path(entry["assembly"])
        if (not assembly.is_absolute() or not assembly.is_relative_to(run.root)
                or value["files"].get(assembly.relative_to(run.root).as_posix()) != entry["sha256"]):
            raise ConformanceError("ProofMismatch")
    return value


def replay_controller_baseline(owner, baseline, phase, target):
    """Copy the prebuilt project tree; candidate dependency replacement stays in the replay."""
    import foundation_evidence as foundation
    from conformance_evidence import file_sha256

    source = owner / "stores/inherited-historical" / phase / "retained"
    destination = target / "retained"
    foundation.copy_source(source, destination, include_outputs=True)
    retained = []
    for entry in baseline["retained"][phase]:
        replay = dict(entry)
        for key in ("assembly", "assets"):
            replay[key] = str(destination / Path(entry[key]).relative_to(source))
        if file_sha256(Path(replay["assembly"])) != replay["sha256"]:
            raise ConformanceError("InputChanged")
        retained.append(replay)
    return retained


def prepare_controller_evidence(repository, owner, source, *, sdk_package=None, logger_path=None,
                                prepared_baselines=None):
    """Prepare fresh borrowed evidence, without claiming full controller acceptance."""
    import configuration_evidence as configuration
    import discovery_evidence as discovery
    import foundation_evidence as foundation
    import lifecycle_evidence as lifecycle
    import conformance_legacy as legacy
    from conformance_sources import read_bounded

    owner, source = Path(owner), Path(source)
    legacy.no_symlinks(owner)
    legacy.no_symlinks(source)
    owner, source = Path(owner).resolve(strict=True), Path(source).resolve(strict=True)
    if source == owner or not source.is_relative_to(owner):
        raise ConformanceError("OwnershipInvalid")
    manifests, phases = {}, {}
    with controller_transport(repository, owner, sdk_package=sdk_package, logger_path=logger_path) as controls:
        for phase in ("foundation", "lifecycle", "configuration", "discovery"):
            controls["phase"] = phase
            print(json.dumps({"qualification": False, "phase": "inherited-controller-preparation",
                              "controller": phase}), flush=True)
            target = owner / "stores" / ("inherited-controller-" + phase)
            target.mkdir(mode=0o700)
            if phase == "foundation":
                core, providers, config = foundation.packages(source, target, False)
                document = {
                    "core": core, "providers": providers, "localFeed": str(target / "feed"),
                    "sourceHashesBefore": foundation.source_hashes(source),
                }
                document["hosts"] = foundation.hosts(source, target, config, False)
                document["sourceHashesAfter"] = foundation.source_hashes(source)
                summary = {"providerPackages": len(providers), "customHosts": len(document["hosts"])}
            elif phase == "lifecycle":
                config, providers = lifecycle.prepare_packages(source, target, False)
                registration = lifecycle.registration_compatibility(
                    source, target, config, False,
                    prepared=None if prepared_baselines is None else prepared_baselines["registration"])
                journeys, hosts = lifecycle.host_journeys(source, target, config, False)
                boundaries = lifecycle.lifecycle_graphs(source, target, providers, hosts, registration)
                manifest = Path(os.environ["HOARD_LIFECYCLE_EVIDENCE"])
                document = load_json(read_bounded(manifest, 16 * 1024**2))
                summary = {"providerPackages": len(providers), "journeys": journeys,
                           "boundaryParameters": boundaries}
            else:
                module = configuration if phase == "configuration" else discovery
                retained = (module.prepare_baseline(source, target, False) if prepared_baselines is None
                            else replay_controller_baseline(owner, prepared_baselines, phase, target))
                config, providers = lifecycle.prepare_packages(source, target, False)
                if phase == "configuration":
                    provider, consumer = configuration.compatibility(source, target, config, retained, False)
                    registration = lifecycle.registration_compatibility(
                        source, target, config, False, "registration-baseline",
                        prepared=None if prepared_baselines is None else prepared_baselines["registration"])
                    hosts, journeys = configuration.configured_journeys(source, target, config, retained, False)
                    conversion, publication = configuration.interrupted_publication(source, target, config, False)
                    graphs = configuration.configuration_graphs(
                        source, target, providers, hosts, provider, consumer, registration, conversion)
                    document = {"graphs": graphs, "journeys": journeys, "oldBinaries": retained,
                                "publication": publication, "packages": providers}
                    summary = {"retainedBinaries": len(retained), "journeys": len(journeys),
                               "graphs": len(graphs), "publicationBarriers": len(publication["barriers"])}
                else:
                    old = next(entry for entry in retained if entry["name"] == "LegacyOptions")
                    old_provider = Path(old["assembly"]).parents[3] / "LegacyOptions.csproj"
                    discovery.run("dotnet", "pack", str(old_provider), "-c", "Release", "--no-build",
                                  "--no-restore", "-o", str(target / "feed"), "-v", "quiet")
                    foundation.canonicalize_acceptance_archive(
                        target / "feed/Hoard.Fixtures.Configuration.LegacyOptions.0.1.0.nupkg")
                    consumers = discovery.compatibility(source, target, config, retained, False)
                    hosts, journeys, observations, bodies = discovery.package_journeys(
                        source, target, config, retained, False)
                    registration = lifecycle.registration_compatibility(
                        source, target, config, False, "registration-baseline",
                        prepared=None if prepared_baselines is None else prepared_baselines["registration"])
                    graphs = discovery.graphs(
                        source, target, config, providers, hosts, consumers, old_provider, registration, False)
                    document = {"graphs": graphs, "journeys": journeys, "observations": observations,
                                "responseBodies": bodies, "oldBinaries": retained, "packages": providers}
                    summary = {"retainedBinaries": len(retained), "journeys": len(journeys),
                               "observations": len(observations), "graphs": len(graphs)}
            if phase != "lifecycle":
                manifest = target / (phase + "-evidence.json")
                legacy._write(manifest, document)
            variable = "HOARD_" + phase.upper() + "_EVIDENCE"
            manifests[variable] = str(manifest)
            phases[phase] = {
                **summary, "manifestPath": manifest.relative_to(owner).as_posix(),
                "manifestSha256": legacy._hash(manifest),
            }
        legacy._write(owner / "proofs/inherited-controller-lock-derivations.json", controls["lockDerivations"])
        legacy._write(owner / "proofs/inherited-controller-command-inputs.json", controls["inputFiles"])
    return {"qualification": False, "fullControllerAcceptance": False, "nativeContainment": False,
            "manifests": manifests, "phases": phases}


def controller_read_inputs(owner, manifests, *, extra=()):
    """Bind private fixture inputs; this is not a native controller I/O trace."""
    import conformance_legacy as legacy
    from conformance_evidence import file_sha256
    from conformance_sources import read_bounded

    owner = Path(owner).resolve(strict=True)
    files, size = {}, 0

    def bind(path):
        nonlocal size
        path = Path(path)
        legacy.no_symlinks(path)
        if not path.is_file() or not path.resolve(strict=True).is_relative_to(owner):
            raise ConformanceError("OwnershipInvalid")
        path = path.resolve(strict=True)
        relative = path.relative_to(owner).as_posix()
        if relative not in files:
            size += path.stat().st_size
            if len(files) >= 50000 or size > 256 * 1024**2:
                raise ConformanceError("OutputLimitExceeded")
            files[relative] = file_sha256(path)

    def collect(value):
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str) and value.startswith("/"):
            path = Path(value)
            # Manifests also contain route literals and SDK paths, not private fixture inputs.
            if not path.is_relative_to(owner):
                return
            legacy.no_symlinks(path)
            if not path.resolve().is_relative_to(owner):
                raise ConformanceError("OwnershipInvalid")
            if path.is_file():
                bind(path)
                if path.name == "project.assets.json":
                    assets = load_json(read_bounded(path, 16 * 1024**2))
                    for identity, entry in assets["libraries"].items():
                        if identity.startswith("Hoard.") and entry["type"] == "package":
                            for cache in assets["packageFolders"]:
                                for item in (Path(cache) / entry["path"]).glob("*"):
                                    if item.is_file():
                                        bind(item)
            elif path.is_dir():
                for item in path.rglob("*"):
                    if (item.is_file() and item.suffix in (".cs", ".csproj")
                            and not {"bin", "obj"}.intersection(item.relative_to(path).parts)):
                        bind(item)

    for path in (*manifests.values(), *extra):
        bind(path)
    for path in manifests.values():
        collect(load_json(read_bounded(Path(path), 16 * 1024**2)))
    return dict(sorted(files.items()))
