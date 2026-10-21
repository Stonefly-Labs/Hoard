# F-03 Validation Quickstart

**Status**: Implemented fixture-backed validation guide. Hosting supplies
configured activation, explicit local secret references and synthetic-only
conversion. This is a library/TestServer example, not a product executable,
real provider, native-client or conformance claim. No cloud account is needed.

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

These retain F-01/F-02 fixture acceptance alongside F-03. A bare `dotnet test` is not
a substitute for the scripts' actual package/graph proof inputs.

## Full Acceptance and Focused Commands

Run complete locked configuration acceptance:

```bash
bash scripts/validate-configuration.sh
```

It runs the [CFG-01..36 obligations](contracts/acceptance.md), format/analyzer
checks, actual source/project/packed/API/assets graphs, independent baseline/
custom package hosts, retained old binaries and the real child interruption
matrix. Prepared distribution/graph tests reject missing proof manifests.
See the [measured evidence](plan.md#complete-implementation) for actual counts,
review disposition and the measured macOS local-volume scope. Linux and other
filesystems require their own real acceptance run before a support claim.

These modes remain explicitly partial:

```bash
bash scripts/validate-configuration.sh \
  --filter '(FullyQualifiedName~Configuration|FullyQualifiedName~ConfiguredComposition)&FullyQualifiedName!~Prepared_configuration'
bash scripts/validate-configuration.sh --baseline-only
```

The first runs nonempty ordinary configuration regressions under a bounded
runner; the second compiles independent fixture sources against pinned merged
pre-F-03 packages and verifies their baseline locks/hashes. To explicitly
generate the new baseline locks, use `--baseline-only --update-locks`, then
review and replay without that flag. An optional `--retain-baseline` fresh
private directory retains the actual old binaries/assets outside Git.
Neither mode runs configured package journeys or proves new binary compatibility.
An optional `--evidence-directory /absolute/fresh/private/directory` retains
actual TRX/closed status for either a failing red run or passing green run.
For full acceptance it retains the complete private package/graph/binary/
publication workspace for independent inspection. Failures still exit nonzero
and never set fullAcceptance or infer their own intended red cause.
Full-run `--retained-baseline /absolute/private/baseline-directory` reuses the
verified original binary bytes without rebuilding/replacing them.
Locked package restore uses the reproducible pre-F-03 provider build in either
mode. After restore/build, each configured host receives the verified retained
provider DLL; actual runtime hashes are checked before/after all journeys.
This separates original-binary compatibility from deterministic package hashes
without changing locks during replay.

Use the existing scripts' explicit `--update-locks` pattern only if adding or
changing a manifest makes initial lock generation necessary; inspect lock diffs
and replay the default locked command afterwards. Do not restore/install
dependencies solely to read the design. Local packed Hosting payload changes
also require reviewed content-hash lock updates, not dependency/version changes.

`HoardConfigurationInput` receives explicit finite Defaults/arguments/environment
snapshots and an optional file/read adapter; it does not capture ambient
developer credentials. Snapshot scan ceilings are 4,096 arguments/environment
entries, with one-MiB Defaults/overlay/reserved-argument text. The current public
`EvaluateConfigurationAsync` returns a safe report and a single-use
`Configuration` proof only after composition, active public checks, local
secret resolution and secret-dependent checks pass. Consume it once with
`builder.ComposeHoardModulesAsync(evaluation.Configuration, token)` and use
the existing F-02 lease build/map/start/stop/dispose sequence. Dispose unused
evaluations/proofs; transferred inputs instead belong to the lease. Never use
source parsing or a conversion result as startup approval.

## 1. Source Resolution Without Construction

The [baseline JSON](../../examples/LifecycleHost/Configuration/baseline.json)
uses the configured example's registered fixture inventory and invented
environment-reference names. Supply only an explicit dictionary/read adapter
containing invented values; the runner creates secret snapshots in memory and never
captures a personal process environment. The
[custom JSON](../../examples/LifecycleHost/Configuration/custom.json) additionally
selects the custom-only artifact. JSON is reference input for the public
library APIs; the self-checking example is not a general-purpose operator CLI.

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

The [synthetic example](../../examples/LifecycleHost/Configuration/synthetic-fixture-v0.json)
is not a released format. Use an explicit source file and fresh destination
in an already owner-restricted directory:

```csharp
await using var preview = await builder.PreviewConfigurationConversionAsync(
    sourcePath, destinationPath, platformVersions, lifecycleOptions,
    readEnvironment: (name, _) => ValueTask.FromResult(
        suppliedSecrets.TryGetValue(name, out var value) ? value : null),
    cancellationToken: token);
if (preview.Session is null)
{
    throw new InvalidOperationException("Configuration preview rejected; inspect the safe report.");
}
preview.Session.Approve();
await using var applied = await builder.ApplyConfigurationConversionAsync(
    preview.Session, token);
```

Import `Hoard.Hosting.Configuration.Conversion`. Inspect both safe reports and
the apply outcome; approval is explicit and single-use. No ambient
HOARD_CONFIG/CLI/default overlays participate. Only the supplied local reader
is used for secret lookups at apply, not preview.

Apply repeats full validation and writes complete version 1
references without resolved secrets. Reused/unapproved session, changed input,
invalid target, unknown version or missing secret must leave no published
replacement. Existing/racing destinations remain untouched.
Cancellation at the publication boundary must report the actual complete-file
outcome or explicit `PublicationPending` while the OS operation is unresolved,
never promise rollback because only its wait was cancelled.
`applied.Publication.Status` and `applied.Supervision` expose later safe
observation; the original result/report remain frozen. Full apply does not
activate providers; next startup must evaluate fresh inputs separately.

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
PR. Preserve F-01/F-02 artifacts and reviewer-owned approvals.
Update README, development/provider/example guides and actual command support.
Run the required bounded architecture review on real API/package/ownership
changes. Passing fixture checks never claims a runnable cache, real provider,
management UI, native-client compatibility or conformance certification.
