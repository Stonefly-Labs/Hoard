# F-03 Validation Quickstart

**Status**: Planned validation/run guide. F-03 has no implemented configuration
API, command or converter yet. Existing commands below are runnable; the named
future command and scenarios are implementation acceptance obligations.
No full implementation code, product host, external provider or cloud account
is required.

## Prerequisites and Existing Baseline

Use repository Git/Python 3.11+ and the stable .NET 10 SDK pinned by global.json,
with network access to restore the existing locked NuGet dependencies.
Run from the repository root on the recorded type-prefixed feature branch.

```bash
python3 scripts/speckit_flow.py status
SPECIFY_FEATURE_DIRECTORY=specs/003-provider-configuration \
  bash .specify/scripts/bash/check-prerequisites.sh --json --paths-only
python3 -m unittest discover -s tests/tooling -v
```

The prerequisite output must resolve this feature directory, independent of
the display branch name. Do not run `begin` merely to inspect.

The existing product-foundation checks are:

```bash
bash scripts/validate-lifecycle.sh
bash scripts/validate-foundation.sh
```

These remain F-01/F-02 fixture acceptance, not F-03 evidence before its cases
exist. They must still pass after implementation. A bare `dotnet test` is not
a substitute for the scripts' actual package/graph proof inputs.

## Planned Focused Command

Implementation must introduce and document `bash scripts/validate-configuration.sh`
before claiming it works. The default mode must use locked restore and run
the [CFG-01..36 obligations](contracts/acceptance.md), formatting/analyzers,
actual independent package consumers, retained binary compatibility,
TestServer journeys and local-filesystem conversion tests. It must fail for
missing/empty proof selections, never skip absent manifests.

Use the existing scripts' explicit `--update-locks` pattern only if adding or
changing a manifest makes initial lock generation necessary; inspect lock diffs
and replay the default locked command afterwards. Do not restore/install
dependencies for this documentation-only planning stage.

## 1. Source Resolution Without Construction

Prepare isolated fixture Defaults/file documents in the
[version 1 grammar](contracts/configuration-format.md), a copied `HOARD_CONFIG`
environment overlay and Hoard CLI arguments. Use known registered fixture
option contracts, not arbitrary product-sketch keys. Do not use personal
environment credentials or log raw argv/file content.

Validate conflicting keys at all four levels and inspect the safe report:
CLI wins, unrelated option keys remain, whole selections replace, and the
winning source kind appears without raw values. Repeat to prove determinism.
Pair valid input with same-source escaped/case duplicates, unknown disabled
keys, invalid explicit empties and unreadable explicitly requested file.
Every failure must have zero adapter/provider constructors and secret reads.

## 2. Active Options, Selection and Disabled Isolation

Select fixture metadata/artifact authority plus two protocols/identities as
appropriate. Exercise the existing gate's compatibility/optional-dependency/
capability outcomes and valid counterpart. Supply representable invalid lower
options overridden by valid effective values; separately reject structural
errors that remain invalid despite override.

Leave a disabled module without required settings and point its syntactically
valid reference at an inaccessible target. It must get zero callbacks/reads,
construction/routes/workers/connections. Missing config contract, flag mismatch
or a selected adapter unable to receive configured options must fail before
any secret work.

## 3. Secrets, Bounded Work and Delivery

Create isolated invented environment/file secret targets, owner-private local
files and explicit references. Valid selected owners receive fixed values only;
ordinary report/telemetry capture contains neither those values nor locators.
Pair missing/empty/denied/malformed/raw-literal/credential-address input with
safe action/correlation diagnostics, no fallback.

Use deterministic barriers and virtual time to hold synchronous/async checks,
reads and cancellation callbacks. Assert the original absolute budget, no
activation, retained in-use objects and safely observed late faults; release
every test task before exit. Confirm success proof consumption/freshness and
legacy-path bypass rejection. During F-02 configured delivery, use existing
ledger/lease tests for partial failure/pending-resource protection.

## 4. Restart and Distribution Journeys

Use package-only baseline and custom LifecycleHost fixtures, in-memory
TestServer only. Editing sources/secret targets leaves the current lifecycle
unchanged. Stop through F-02, create fresh inputs and restart to observe the
replacement. Switch a bundled protocol without rebuilding; formerly selected
fixture activity is zero on the new start.

The baseline must not reference/register the custom artifact package. Add that
independent package and host adapter to the custom build, then rebuild,
redeploy fixture inputs and start anew with no Core edits. Invalid replacement
must fail; explicit restoration of a coherent previous distribution/config/
reference set is the only recovery. Do not generate rollback secret values.

## 5. Explicit Synthetic Conversion and Interruption

Use only the documented `fixture-v0` mapping, labelled synthetic and not a
released compatibility promise. Call preview from the fixture harness: original
bytes stay unchanged, selected values/reference meaning remain preserved,
no secret read/provider construction, safe categories without private proposal.

Approve the exact private session and a fresh owner-restricted output
destination. Apply repeats full validation and writes complete version 1
references without resolved secrets. Reused/unapproved session, changed input,
invalid target, unknown version or missing secret must leave no published
replacement. Existing/racing destinations remain untouched.
Cancellation at the publication boundary must report the actual complete-file
outcome or explicit `PublicationPending` while the OS operation is unresolved,
never promise rollback because only its wait was cancelled.

Inject failure and terminate a child fixture process at staged/write/flush/
pre-/post-publication barriers on each claimed local platform. The original
must remain byte-identical; the final output is absent or complete and valid,
never partial. Explicitly inspect/remove only known private staging files
created by the harness. No broad cleanup, in-place source replacement or
hardware power-loss claim. A next startup revalidates the published document.

Recovery instructions must separately require provider version/data compatibility
and real backup/restore where necessary. Restoring config cannot reverse schema
or stored artifact changes; fixtures do not prove real provider recovery.

## Recording Evidence

Record exact commands/results and cases/platforms in the implementation plan/
PR when they exist. Preserve F-01/F-02 artifacts and reviewer-owned approvals.
Update README, development/provider/example guides and actual command support.
Run the required bounded architecture review on real API/package/ownership
changes. Passing fixture checks never claims a runnable cache, real provider,
management UI, native-client compatibility or conformance certification.
