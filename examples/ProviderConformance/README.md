# Reproduce a separately packaged contributor

This example forwards to the existing test-only Memory metadata fixture. It is
not a third independent implementation, a production provider or publishing
support. The public controller builds and packs the explicitly registered
project, runs the unchanged complete common metadata suite and records actual
package/component origins. Providers and their MSBuild projects are trusted
in-process code: review them before execution.

**Current boundary:** these commands produce diagnostic observations, not a
qualifying report. Successful common execution still ends with
`qualification:false`, `profileComplete:false` and `EvidenceIncomplete` exit2.
The faulty run must have an actual named failed assertion, not merely a nonzero
exit. Independent qualification, `--verify`, `--aggregate` and five-profile CI
acceptance are not delivered by this walkthrough.

Built-in metadata/artifact runs without `--binding-project` additionally produce
closed JSON/JUnit/Markdown/CI-summary projections under their owned
`diagnostics/` directory. Original diagnostic summaries remain
Incomplete/NotQualified, including their explicit JUnit qualification error.
Complete built-in runs now additionally require their original Released native
owner/evaluation to publish finite fixture-qualified projections and return0;
at exact `984bb2e`, actual Linux artifact execution and separate-process receipt
verification pass103 cases/263 witnesses; isolated metadata execution and
independent verification pass102 cases/141 witnesses at that same source.
An earlier concurrent metadata failure remains unexplained. They deny full
baseline qualification. Neither the qualified projections nor the native-owner
receipt are wired into this separate contributor route or qualifying offline
verification. Do not infer complete private-file sanitation from a safe summary.

## Prerequisites and private scratch

Use an ordinary unprivileged user on native Linux x86_64 or arm64, with procfs,
Python3, Bash, Git, the SDK selected by the repository's `global.json`, and its
matching .NET10 runtime. The controller measures actual SDK/runtime versions and
requires native containment; macOS/Windows do not silently substitute managed
tests for this public command. Initial restore needs access to the configured
public NuGet feed. No Azure resource, cloud account, service, token, personal
NuGet configuration or credential is required.

Start at the root of a fresh checkout of this feature. Keep the checkout
unchanged throughout the three runs. Do not share evidence directories with
another command or edit scripts, bindings or assertion sources during a run.
The shell blocks below are sequential and use the same Bash session.

```bash
set -euo pipefail
umask 077
repo="$(pwd -P)"
work="$(mktemp -d "${TMPDIR:-/tmp}/hoard-contributor.XXXXXXXX")"
export HOARD_CONTRIBUTOR_WORK="$work"
python3 --version
dotnet --version
dotnet --list-runtimes
python3 - "$repo" "$work/adapter" <<'PY'
import json
from pathlib import Path
import shutil
import sys

source, target = map(Path, sys.argv[1:])
sidecar = source / "tests/fixtures/conformance/Contributor/Contributor.conformance.json"
registration = json.loads(sidecar.read_text())
for relative in registration["sourceFiles"]:
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / relative, destination)
PY
project="$work/adapter/tests/fixtures/conformance/Contributor/Contributor.csproj"
adapter_source="$work/adapter/tests/fixtures/conformance/Contributor/ForwardingMetadataBinding.cs"
cp "$adapter_source" "$work/original-forwarding.cs"
```

The copied registration explicitly lists all source/import/lock inputs. Its
package-only references are resolved from a controller-owned feed; evaluation,
restore, compiler/PDB/package inputs and actual archive/content hashes are
captured. The controller stages a fresh private cache and rejects changed or
unregistered inputs. Do not run `dotnet restore` against a personal feed, supply
alternative binaries, edit a derived lock or use `--update-locks` to hide a
replay failure. The first run performs the required dependency restore itself.

Each evidence path below must be absent under the private0700 parent. The
controller owns only its allocated subdirectories; it must not clean the
adapter sources, sibling runs or outside sentinels.

## Good, faulty and corrected runs

```bash
run_contributor() {
    local label="$1"
    local status=0
    bash scripts/validate-conformance.sh \
        --profile metadata --binding-project "$project" \
        --evidence "$work/$label" > "$work/$label-console.jsonl" || status=$?
    if [ "$status" -ne 2 ]; then
        printf 'Unexpected contributor exit for %s: %s\n' "$label" "$status" >&2
        return 1
    fi
}
run_contributor good

python3 - "$adapter_source" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
original = path.read_text()
needle = "inner = new(providerPackageSha256);\n        this.injectStaleReplay = injectStaleReplay;"
if original.count(needle) != 1:
    raise SystemExit("Contributor fault location changed; do not mutate a different source.")
path.write_text(original.replace(needle, needle.replace("= injectStaleReplay;", "= true;")))
PY
run_contributor faulty

cp "$work/original-forwarding.cs" "$adapter_source"
run_contributor corrected
```

Only the external adapter's constructor body changes. Its API/default argument,
the platform checkout, provider, common consumers, assertions, capabilities and
expected outcomes do not change. The faulty package enables the existing stale
conditional-operation adapter. The intended failure is the `time-ticket`
common-consumer row, executing
`MetadataTimeAssertions.TicketExpiryAndRollbackAsync`. The same cached stale
commit also violates the `receipts` and `publication-replay` consumers. Exactly
these three named rows must fail; unrelated failures must not be excused by the
selected fault. The correction restores the original adapter source, not the
assertion or an expected result.

All three runs have different roots/run IDs. An incomplete failed observation
is never converted into the corrected run, overwritten, retried away or used
as qualification. The successful diagnostic summary exists only after actual
common runtime and post-input/settlement checks; exit2 alone proves nothing.

## Inspect finite diagnostics and unchanged inputs

The following is a diagnostic inspection, **not** the independent evaluator.
It reads only bounded toolkit-generated packets, prints only frozen catalog
identities and safe hashes/counts, and requires the intended failed row plus
passing good/corrected runs. It checks common consumer/assertion source hashes,
SDK/provider/binding image bytes and provider package hashes across the runs.
Executable source/build/configuration workspaces are transient owned inputs;
only hash-named original runtime image copies remain for this inspection.
Adapter-specific compiled-driver/PDB provenance remains bound separately to
each run; do not claim those artifacts are invariant merely because the common
assertion source is unchanged.

```bash
PYTHONPATH=scripts python3 - "$work" <<'PY'
import json
from pathlib import Path
import sys
import conformance_case_catalog as catalog
import conformance_evidence as evidence
from conformance_sdk_checks import read_bounded

def require(condition):
    if not condition:
        raise evidence.ConformanceError("ProofMismatch")

def inspect(root, faulty):
    inputs = evidence.admit_entity("RunInputs", evidence.load_json(
        read_bounded(root / "proofs/contributor-inputs.json", 16 * 1024 * 1024)))
    binding = "example.metadata.forwarding"
    require(inputs["bindings"][0]["bindingId"] == binding)
    expected = catalog.metadata_common_consumer_origin_counts(binding_ids=(binding,))
    attempts = tuple(root.glob("runtime-*/witnesses.jsonl"))
    require(len(attempts) == 1)
    witnesses = [evidence.load_json(line) for line in read_bounded(
        attempts[0], 1024 * 1024).splitlines()]
    require(len(witnesses) == len(expected))
    require({row["testIdentity"] for row in witnesses} == set(expected))
    require(all(row["status"] in ("Passed", "Failed") for row in witnesses))
    failed = sorted(row["testIdentity"] for row in witnesses if row["status"] == "Failed")
    expected_failures = {name for name in expected if any(
        'consumer: "' + consumer + '"' in name
        for consumer in ("time-ticket", "receipts", "publication-replay"))}
    require(len(expected_failures) == 3)
    require(set(failed) == expected_failures if faulty else not failed)
    ledger = evidence.load_json(read_bounded(root / "ownership.json", 1024 * 1024))
    require(ledger["state"] == "Released")
    require(not any((root / name).exists() for name in ("stores", "cache", "feed")))
    if not faulty:
        summary = evidence.load_json(read_bounded(
            root / "proofs/contributor-runtime-summary.json", 1024 * 1024))
        require(summary["qualification"] is False and summary["profileComplete"] is False)
        require(summary["passedParameters"] == len(expected))
    names = ("Hoard.Testing.Conformance.dll", "Hoard.Fixtures.Metadata.Memory.dll",
             "Hoard.Fixtures.Conformance.Bindings.Memory.dll")
    images = {}
    for name in names:
        selected = [(path, hashed) for path, hashed in inputs["runtimeAssemblies"].items()
                    if Path(path).name == name]
        require(len(selected) == 1)
        path, hashed = selected[0]
        retained = "proofs/contributor-runtime-inputs/" + hashed
        require(evidence.input_manifest(root, (retained,))[retained] == hashed)
        images[name] = hashed
    common = {path: hashed for path, hashed in inputs["sourceManifest"].items()
              if path.endswith(".cs") and path.startswith((
                  "tests/fixtures/conformance/Consumer/", "tests/contracts/Hoard.Testing.Conformance/"))}
    require(bool(common))
    providers = [package["sha256"] for package in inputs["packages"]
                 if package["packageId"] == "Hoard.Fixtures.Metadata.Memory"]
    require(len(providers) == 1)
    print(json.dumps({"runId": inputs["runId"], "failedTests": failed,
                      "commonSourcesSha256": evidence.digest(common),
                      "imagesSha256": evidence.digest(images), "providerPackageSha256": providers[0],
                      "qualification": False}))
    return inputs["runId"], common, images, providers[0], inputs["invocation"][1]

try:
    root = Path(sys.argv[1])
    rows = [inspect(root / label, label == "faulty") for label in ("good", "faulty", "corrected")]
    require(len({row[0] for row in rows}) == 3)
    require(all(row[1:4] == rows[0][1:4] for row in rows))
    require(rows[0][4] == rows[2][4] and rows[0][4] != rows[1][4])
except (evidence.ConformanceError, OSError, ValueError):
    print(json.dumps({"qualification": False, "code": "EvidenceIncomplete"}))
    raise SystemExit(2)
PY
```

Do not upload the workspace or dump unknown exception text, configuration,
payload bytes or filenames. The controller admits closed diagnostics before
persistence; unknown SDK/provider text fails safely rather than disappearing
into success. Keep proof/ownership history for investigation. Use a new absent
evidence path for changed sources/packages/SDK/runtime/configuration; never edit
an old input packet or claim an old receipt accepts new bytes.

## Owned retention and recovery

An evidence root is single-writer. Two contributor commands may run concurrently
only with distinct private roots; the same path or overlapping operations on one
owner must reject. If settlement observes live work, it records `Retained` and
`CleanupIncomplete`, preserving resources and the failed cleanup attempt.

The **original owner**, still holding its exact process handles and saved
PID/start identities, can inspect/terminate its own contained child, observe
exit, then explicitly retry settlement. The retry appends cleanup history; it
does not erase the first failure or make its runtime attempt pass. Reproduce
these existing safety controls from the same checkout:

```bash
PYTHONPATH=scripts:tests/tooling python3 -m unittest \
    test_conformance_execution.ConformanceExecutionTests.test_live_work_is_retained_then_retry_records_exit_without_erasing_the_failure \
    test_conformance_execution.ConformanceExecutionTests.test_failed_release_publication_cannot_claim_release_and_retry_keeps_evidence \
    test_conformance_execution.ConformanceExecutionTests.test_one_owned_writer_rejects_overlapping_commands_and_cleanup_before_admission \
    test_conformance_execution.ConformanceExecutionTests.test_preflight_parent_swap_cannot_create_a_workspace_under_an_outside_sentinel \
    -v
```

These are toolkit-owned recovery demonstrations, not adoption of an arbitrary
old CLI directory. The CLI has no `--recover` or force-delete command. If the
original controller/handles are lost, preserve the root and request maintainer
inspection; do not reconstruct an owner, trust a bare PID, kill by process name,
follow a substituted path or delete a retained root. Missing/foreign/reused
process identity or unverifiable descendants must remain incomplete.

The separate [native generated-report controls](../../specs/007-provider-conformance/quickstart.md#native-generated-report-controls)
exercise the standard metadata/artifact executors before and after actual
settlement, plus their retained reports, through the same explicit test-only
command as category CI. They do not accept contributor bindings or qualify a
provider. Their host orchestration regressions and genuine Linux executions
pass for both standard categories at `bddb2a8`. The expanded independent report-
boundary/failed-retry controls also pass at immutable `887aaba`: four live,
eight released-origin and nine retained-report checks per category. They do
not qualify this contributor journey or complete generic/five-profile
qualification.

For actual overlapping contributors, keep the restored adapter unchanged and
use different roots. The duplicate path must fail without disturbing either
valid owner or an outside sentinel. The final command explicitly rejects an
optional service-backed profile that is not implemented; it does not pretend
to contact or qualify an external service.

```bash
printf 'outside-sentinel\n' > "$work/outside-sentinel"
run_contributor overlap-one &
first="$!"
run_contributor overlap-two &
second="$!"
for ((attempt=0; attempt<100; attempt++)); do
    if [ -f "$work/overlap-one/ownership.json" ]; then break; fi
    sleep 0.1
done
test -f "$work/overlap-one/ownership.json"
status=0
bash scripts/validate-conformance.sh --profile metadata --binding-project "$project" \
    --evidence "$work/overlap-one" > "$work/duplicate-console.jsonl" || status=$?
test "$status" -eq 2
wait "$first"
wait "$second"
status=0
bash scripts/validate-conformance.sh --profile service-backed \
    --evidence "$work/unavailable-service" > "$work/service-console.jsonl" || status=$?
test "$status" -eq 2
PYTHONPATH=scripts python3 - "$work" <<'PY'
import json
from pathlib import Path
import sys
import conformance_case_catalog as catalog
import conformance_evidence as evidence
from conformance_sdk_checks import read_bounded

root = Path(sys.argv[1])
def require(condition):
    if not condition:
        raise evidence.ConformanceError("ProofMismatch")

try:
    expected = catalog.metadata_common_consumer_origin_counts(binding_ids=("example.metadata.forwarding",))
    summaries = [evidence.load_json(read_bounded(
        root / label / "proofs/contributor-runtime-summary.json", 1024 * 1024))
        for label in ("overlap-one", "overlap-two")]
    require(len({summary["resources"][0]["runId"] for summary in summaries}) == 2)
    for label, summary in zip(("overlap-one", "overlap-two"), summaries):
        require(summary["qualification"] is False and summary["profileComplete"] is False)
        require(summary["passedParameters"] == len(expected) and summary["sessionOrigins"] == sum(expected.values()))
        require(all(resource["state"] == "Released" for resource in summary["resources"]))
        require(not any((root / label / name).exists() for name in ("stores", "cache", "feed")))
    duplicate = evidence.load_json(read_bounded(root / "duplicate-console.jsonl", 65536))
    service = evidence.load_json(read_bounded(root / "service-console.jsonl", 65536))
    require(duplicate["code"] == "OwnershipInvalid" and duplicate["qualification"] is False)
    require(service["code"] == "UnsupportedProfile" and service["qualification"] is False)
    require(not (root / "unavailable-service").exists())
    require(read_bounded(root / "outside-sentinel", 64) == b"outside-sentinel\n")
    print(json.dumps({"qualification": False, "concurrentRuns": 2, "duplicate": duplicate["code"],
                      "service": service["code"], "outsideSentinelPreserved": True}))
except (evidence.ConformanceError, OSError, ValueError):
    print(json.dumps({"qualification": False, "code": "EvidenceIncomplete"}))
    raise SystemExit(2)
PY
```

## Other bindings, exclusions and unavailable services

Supply a reviewed `.csproj` with its explicit closed `.conformance.json`
registration, exact package identities, typed factory, role owners and complete
source/import/lock inventory. See [provider contracts](../../docs/PROVIDERS.md).
The controller does not scan directories for arbitrary plugins or reflectively
load an unregistered factory.

Choose exactly `--profile metadata` or `--profile artifacts` for a contributor.
Artifact registration requires one frozen durability and one enumeration marker;
actual capabilities must match before/after assertions. Its complete common
scope includes applicable real crash/recovery, retained-child and256 MiB/4 GiB
transfer obligations. It additionally requires an admitted local filesystem and
at least24 GiB free scratch. Do not lower that gate or substitute sparse files,
managed simulations or an untested filesystem.

Provider-selected exclusions, `--filter` with a contributor, partial/duplicate
agreements and mixed categories reject; preparation/focused evidence cannot
qualify. Private filesystem-record/object-residual mechanics stay mandatory for
their original built-in fixtures, not arbitrary contributors. No third-party
service is needed for this example. If another binding requires an unavailable
service or unsupported native facility, report its explicit prerequisite/
incomplete scope; do not silently skip it, switch to Memory, add credentials to
evidence, claim a service test ran or widen the finite support statement.
