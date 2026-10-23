# F-06 Artifact Qualification Quickstart

**Status**: Full test-fixture qualification passed on the final intended source:
96 provider/case entries, 92 passes and exactly four Object AS-41..44
non-applicability results, not skips. The recorded environment is macOS 26.5
arm64, .NET 10.0.7 and APFS, with Local payload/decision `Flush(true)` but no
directory fsync; no power-loss or production-provider claim follows.
PR #16 is merged and
[`v0.0.6-alpha`](https://github.com/Stonefly-Labs/Hoard/releases/tag/v0.0.6-alpha)
publishes source only at its exact merge commit. The completion checkpoint in
[PR #17](https://github.com/Stonefly-Labs/Hoard/pull/17) must merge before F-07
`specify`; no new product qualification is claimed by that handoff.
See the [merge/release evidence](plan.md#merge-completion-and-alpha-source-release).
Both independent fixtures declare the baseline and become ready only after
explicit admission. Existing F-02/F-03 composition covers inert/disabled
selection, rejected missing guarantees and successful startup/stop/restart.
Local reopens its exact known identity; Object replacement uses a fresh root
and epoch, never a durable-restart claim.
The unchanged compiled consumer exercises all 16 common operations on both
choices. Current full acceptance includes 261 logical/crash checks, four actual-transfer
proof tests, three architecture checks, eight graph scans, the original frozen
marker binary, six Python-owned kill/reopen barriers and 29 altered-manifest
rejections. See [exact commands and evidence](plan.md#corruption-quarantine-implementation-2026-10-22).
Every focused mode remains `qualification: false`, even with passing results.
Expired ticket retirement now restores finite admission; retained identity and
reclaimed-incarnation history has separate bounded bookkeeping and compacts
only after expiry, physical reclamation and dependent-work settlement.
Candidate traversal now resumes bounded pages of at most 100 tickets and
100 candidates per retained-history index instead of scanning all records;
at most 100 histories retire per call. Incremental dependency indexes preserve
active/unresolved work and rebuild on Local reopen. Capacity may remain
unavailable while finite pages advance; there is no hidden automatic retry.
Live content survives ticket retirement. Exact finalized reconciliation
receipts survive later deletion/recreation, including an already-admitted
reconciliation that resumes after the original ticket expires.
Qualification records now enforce zero durable exclusions for Local and exactly
AS-41..44 for the simulation. Logical mode also runs six owned-child
non-cooperative source/destination/native containment checks. Their second
parent inspection precedes exact-child termination and confirms retained work,
streams, root ownership, applicable guards and incomplete shutdown. They are
not durable crash evidence or successful cooperative cleanup.
Qualification values now require an explicit bounded environment and exactly
48 immutable case results with statuses, durations and proof hashes. The old
flat case-name/hash constructor rejects such unattached claims. Case-report
validation reads the hashed payload and verifies its context and paired passed
TRX witnesses, including executed names and duration. The exact semantic catalog
requires every provider and parameter variant, and full verification binds
actual lock/package/configuration/capability/environment inputs to all cases.
Successful result delivery is serialized against cancellation. Unclaimed
tickets, staging and reads remain provider-owned until exact reclamation;
expiry does not prevent cleanup of that generation. Failed cleanup blocks
admission/readiness and root release until a bounded exact `StopAsync` retry
succeeds. Non-cooperative resources are never declared released.
Failed staging prefixes also retain ownership when unlink fails. Observe the
exact abandoned generation and retry bounded maintenance after restoring access,
or retry stop; neither path waits for ticket expiry or reopens a finalized
noncommit. Settled commit receipts remain reconcilable while exact residual
staging is pending; maintenance preserves committed content and receipt identity.
Readiness/new admission remain blocked until actual reclamation settles.
Recovery continuations are single-use and bound to store/query/page size/revision/
expiry. Each successful page replaces its consumed handle and terminal pages
release their slot, allowing 32 independent scans to progress beyond 32 pages.
Unselected Object assemblies now have exact ownership before creation, bounded
count/verified-length reservations and failed-unlink tracking. The assembly pool
is bounded by the staging byte limit and transfer slots in addition to multipart
reservations, so the two private payload pools total at most twice the staging
limit. Pending scratch blocks readiness/new admission and commit retries until
exact maintenance or shutdown reclaims it. Selected content is never scratch;
settled equivalent-reuse receipts survive cleanup failure. Partial/complete
assemblies, cancellation, repeated denied cleanup and actual byte/capacity
restoration are exercised by the final locked run.
Detected corruption now quarantines the exact current incarnation across
validation/open/reuse/copy/publication/reconciliation paths. Neither restoring
the original length nor replacing the bytes externally clears quarantine.
Local preserves it across compatible reopen; Object promises only process-local
retention. Permission and unavailable-directory failures do not quarantine
intact content. If Local cannot persist a detected quarantine, readiness/new
admission are fenced and shutdown retains root ownership until persistence
succeeds: restore access and retry bounded `StopAsync` before reopening.
Previously finalized receipts remain reconcilable without certifying health;
unresolved corrupt publication cannot be finalized after an overlapping
read detects corruption. Authorized delete/recreate uses a fresh incarnation.
The [follow-up evidence](plan.md#corruption-quarantine-implementation-2026-10-22)
supersedes earlier source qualification. Clean convergence and finalization
are complete; [PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) is ready
for maintainer review and merge. See the [finalization evidence](plan.md#finalization-evidence).
The next separately invoked stage is `await_merge`; no merge, source release,
feature completion or dependency unlock is claimed by this quickstart.
See the [approved hash refresh and locked replay](plan.md#approved-lock-refresh-and-locked-replay-2026-10-22).

Read [API](contracts/artifact-api.md), [model](data-model.md),
[recovery](contracts/recovery.md) and [exact case matrix](contracts/acceptance.md).

## Prerequisites

For the current package-only checks, provide the retained owner-private
pre-F06 baseline captured before public contract additions:

```bash
export HOARD_ARTIFACT_RETAINED_BASELINE="../hoard-artifact-evidence/pre-f06-20261022"
bash scripts/validate-artifacts.sh --phase logical \
  --evidence "../hoard-artifact-evidence/fresh-focused-check"
```

The retained marker is hash-verified and copied, never rebuilt against new
contracts. This focused check reports `qualification: false`. Do not manufacture
a replacement baseline if its original source/binary/dependency hashes are
missing. Default full mode now executes and verifies the complete inventory;
it still fails closed for any missing, failed, stale or hash-altered obligation.

Use Git, Bash, Python 3.11+ and the stable .NET 10 SDK selected by `global.json`.
Existing package versions/locks remain authoritative; no vendor SDK or cloud
account is needed. Use a fresh owner-private destination outside the checkout
on a local filesystem with at least 16 GiB free scratch space. Keep room for
retained failure evidence; preflight insufficient space must fail, not skip.

The full run needs an actual macOS/Linux peak-RSS measurement, permission to
start and signal only owned child processes, and exclusive ownership of each
scratch root. No server, container, network filesystem or rendered UI is needed.
Only the actual OS/runtime/filesystem exercised can be reported as qualified.

## Repository Checks

```bash
python3 -m unittest discover -s tests/tooling -v
SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage \
  .specify/scripts/bash/check-prerequisites.sh --json --paths-only
git diff --check
```

These validate repository tooling, pinned paths and patch hygiene, not artifact
semantics, RSS, crash recovery or reviewer-owned checklist approval.

## Full Command

```bash
bash scripts/validate-artifacts.sh --evidence "$PRIVATE_EVIDENCE/artifacts-full"
```

`PRIVATE_EVIDENCE` denotes an explicitly chosen existing owner-private parent
outside Git. The runner must reject a preexisting destination and create its
own child with owner-only access before retaining captures.
It restores/builds/formats with tracked locks and build analyzers, packs independent fixtures,
executes the same parameterized common cases and unchanged consumer, measures both payload sizes on
both providers, drives real local crash children, verifies retained old
binaries/graphs and writes an exact attributable manifest.

Full success requires 96 provider/case entries: 92 applicable passes and four
explicit object durable exclusions, not skips. All subproofs must pass.
Missing space, RSS measurement, crash evidence, changed lock or failed case
prevents qualification. No secret/path-bearing diagnostic is copied into the
public console summary; raw captures, exact commands and detailed proof paths
stay in the private evidence workspace, never Git.
Inspect `manifest.json`, `qualification-record-local.json` and
`qualification-record-object.json`. The full manifest links actual case JSON/
TRX witnesses, package/context inputs, OS memory captures, crash state/readback
and executed mutation pairs. The public record type validates each provider's
48 statuses/durations/hashes and exact durability exclusions; a record alone
does not replace the full manifest's input/proof verification.

Available focused commands rebuild/verify prerequisites and always report
`qualification: false`, even if their selection passes:

```bash
bash scripts/validate-artifacts.sh --phase logical --evidence "$PRIVATE_EVIDENCE/artifacts-logical"
bash scripts/validate-artifacts.sh --phase transfers --evidence "$PRIVATE_EVIDENCE/artifacts-transfers"
bash scripts/validate-artifacts.sh --phase recovery --evidence "$PRIVATE_EVIDENCE/artifacts-recovery"
bash scripts/validate-artifacts.sh --phase packages --evidence "$PRIVATE_EVIDENCE/artifacts-packages"
```

The logical phase excludes durable-crash and external-measurement proof tests
(its non-cooperative containment children still execute). Recovery checks exact owner/ticket
semantics, then kills each Python-owned B0/B1/B2/B3/D0/D1 child only after its
matching handshake, confirms SIGKILL exit, and opens the same root in a fresh
process. Captures bind original state hashes, acknowledged control bytes,
new-content hashes/lengths, exact receipts and recreated-incarnation fencing.
The transfer phase uses generated paced non-seekable streams, warmed idle RSS,
OS peak RSS and actual full byte counts, then runs four attributed proof tests.
No phase certifies the other provider's durability or substitutes its output
for the full 96-case manifest.
The package phase inspects eight actual resolved package graphs and compiled
public signatures, rejects provider/Hosting leak controls, compares baseline
members including accessibility/invocation flags, executes the original marker
binary with current platform assemblies and runs both unchanged consumer choices.
These are focused proofs; only default full mode qualifies the complete matrix.

Use `--update-locks` only for intentional dependency/project-manifest or local
package-payload changes; review those tracked locks and then run a separate
default locked acceptance. The approved F-06 unblock refreshes only local
`Hoard.*` package hashes, preserving dependency versions/graphs and external
hashes. Frozen baseline locks and binaries are never refreshed. A focused
locked replay still reports nonqualification. Full mode refuses `--update-locks`;
its qualification requires a separate default locked run.

## Reproducible Runtime Scenarios

1. Pause a non-seekable staged write before EOF and verification; committed
   open must not expose it. Finish valid/empty input and compare exact
   digest/length; reject every wrong expectation and unsupported algorithm.
2. Race equivalent writes with barriers, then inject existing corruption.
   Both submitted inputs must be fully verified; no conflicting overwrite or
   corrupt reuse may be reported as success.
3. Inspect isolated 256 MiB/4 GiB runs on both providers: actual counts, expected
   digest, paced producer/consumer, idle baseline and OS peak RSS <=64 MiB above
   baseline. Managed allocation counters alone are insufficient.
4. Follow the [recovery walkthrough](contracts/recovery.md#reproducible-recovery-walkthrough-after-implementation)
   with actual B0..B3/D0..D1 signals, exact ticket reconciliation, repeated bounded
   cleanup and acknowledged control readback. No new-ticket replay on uncertainty.
5. Hold readers/reference guards, race deletion, then recreate the digest.
   Verify current authority denies unsafe removal and old stamps cannot remove
   the fresh incarnation. Pending physical space reclamation is not freed space.
6. Delay multipart direct visibility and listing independently in the alternative.
   No commit success precedes direct availability; listing absence is never
   authority. The unchanged consumer uses neither rename nor provider types.
7. Cancel cooperative transfers and inspect release bounds. For an intentionally
   non-cooperative child, inspect explicit incomplete cleanup, bounded retained
   ownership and blocked readiness, then terminate only that child after proof.
8. Verify unavailable/capacity/permission/corruption outcomes remain distinct,
   borrowed streams stay caller-owned, and malformed/foreign paths leave an
   outside sentinel untouched.

Stop every owned process before removing only its exact resolved scratch paths.
Retain nonsecret evidence outside Git until review; never recursively delete a
broad parent, user's data or an unrecognized store.

## Configured Restart and Recovery

`ArtifactCompositionTests` demonstrates the existing module lifecycle without
new product configuration or routes. Registration/composition creates no root;
initialization is explicit. After clean shutdown, trusted fixture composition
can register an `ArtifactFixtureAdmissionProfile` with
`Mode = ReopenCompatible` and the exact previous Local `Store` identity.
`ArtifactFixtureSession.CreateForQualificationAsync` retains its original
five-argument signature and adds an explicit six-argument profile overload.
Missing identity, corrupt/incompatible roots or authority/capability mismatches
fail; no auto-discovery, reset, provider fallback or hot replacement is performed.
Object restarts deliberately use a new empty root/epoch and reject old tickets.

For a lost mutation acknowledgment, preserve the original ticket, reconcile
that exact ticket and compare its receipt/stamp. Never create a replacement
ticket to infer rollback. Use bounded query-bound recovery pages and exact
generation/incarnation cleanup targets. Removed receipts may still report
pending physical reclamation; do not count freed space before actual cleanup.
The executed crash walkthrough seeds acknowledged control bytes, captures the
exact B0/B1/B2/B3/D0/D1 handshake, kills only its owned PID and reopens in a
fresh process to compare control/new bytes, receipts and stale-owner fencing.

## Existing Regression Commands

```bash
bash scripts/validate-foundation.sh
bash scripts/validate-lifecycle.sh
bash scripts/validate-configuration.sh
bash scripts/validate-discovery.sh
bash scripts/validate-metadata.sh
python3 -m unittest discover -s tests/tooling -v
```

These already exist but do not prove F-06 behavior. Implementation must record
their exact results, review provider/dependency architecture, update README and
affected guides/examples, and preserve prior contracts, reviewer approvals
and dependency graphs/versions. T083 permits reviewed local-package hash-only
refreshes followed by separate locked replay, never frozen-baseline changes.
No infrastructure plan/apply, package publication, release, deployment, production
recovery operation, cache engine, protocol endpoint or UI is authorized here.
