# F-06 Artifact Qualification Quickstart

**Status**: Partial implementation; the local-package lock blocker is resolved.
Independent partial mechanisms now execute streaming/publication, protected
reads, exact receipts, cleanup/deletion, real metadata integration and local
parent-kill recovery checks. Full qualification remains incomplete and both
fixtures remain not-ready. Logical, transfer and recovery modes execute real
focused proof and always report `qualification: false`; the package phase also
runs actual graph/public-member and frozen-binary checks. Full mode still
fails closed rather than inventing missing results.
See the [approved hash refresh and locked replay](plan.md#approved-lock-refresh-and-locked-replay-2026-10-22).

Read [API](contracts/artifact-api.md), [model](data-model.md),
[recovery](contracts/recovery.md) and [exact case matrix](contracts/acceptance.md).

## Prerequisites

For the current package-only checks, provide the retained owner-private
pre-F06 baseline captured before public contract additions:

```bash
export HOARD_ARTIFACT_RETAINED_BASELINE="../hoard-artifact-evidence/pre-f06-20261022"
bash scripts/validate-artifacts.sh --filter 'FullyQualifiedName~Artifact' \
  --evidence "../hoard-artifact-evidence/fresh-focused-check"
```

The retained marker is hash-verified and copied, never rebuilt against new
contracts. This focused check reports `qualification: false`. Do not manufacture
a replacement baseline if its original source/binary/dependency hashes are
missing. The default full command currently exits unsuccessfully because its
case execution is unfinished; it cannot produce a qualifying manifest.

Use Git, Bash, Python 3.11+ and the stable .NET 10 SDK selected by `global.json`.
Existing package versions/locks remain authoritative; no vendor SDK or cloud
account is needed. Use a fresh owner-private destination outside the checkout
on a local filesystem with at least 16 GiB free scratch space. Keep room for
retained failure evidence; preflight insufficient space must fail, not skip.

The full run needs an actual macOS/Linux peak-RSS measurement, permission to
start and signal only owned child processes, and exclusive ownership of each
scratch root. No server, container, network filesystem or rendered UI is needed.
Only the actual OS/runtime/filesystem exercised can be reported as qualified.

## Checks Available During Planning

```bash
python3 -m unittest discover -s tests/tooling -v
SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage \
  .specify/scripts/bash/check-prerequisites.sh --json --paths-only
git diff --check
```

These validate repository tooling, pinned paths and patch hygiene, not artifact
semantics, RSS, crash recovery or reviewer-owned checklist approval.

## Proposed Full Command (Not Yet Implemented)

```bash
bash scripts/validate-artifacts.sh --evidence "$PRIVATE_EVIDENCE/artifacts-full"
```

`PRIVATE_EVIDENCE` denotes an explicitly chosen existing owner-private parent
outside Git. The runner must reject a preexisting destination and create its
own child with owner-only access before retaining captures.
It restores/builds/formats with tracked locks, packs independent fixtures,
executes the same common cases/consumer twice, measures both payload sizes on
both providers, drives real local crash children, verifies retained old
binaries/graphs and writes an exact attributable manifest.

Full success requires 96 provider/case entries: 92 applicable passes and four
explicit object durable exclusions, not skips. All subproofs must pass.
Missing space, RSS measurement, crash evidence, changed lock or failed case
prevents qualification. No secret/path-bearing diagnostic is copied into the
public report; raw synthetic private captures stay outside Git.

Available focused commands rebuild/verify prerequisites and always report
`qualification: false`, even if their selection passes:

```bash
bash scripts/validate-artifacts.sh --phase logical --evidence "$PRIVATE_EVIDENCE/artifacts-logical"
bash scripts/validate-artifacts.sh --phase transfers --evidence "$PRIVATE_EVIDENCE/artifacts-transfers"
bash scripts/validate-artifacts.sh --phase recovery --evidence "$PRIVATE_EVIDENCE/artifacts-recovery"
bash scripts/validate-artifacts.sh --phase packages --evidence "$PRIVATE_EVIDENCE/artifacts-packages"
```

The logical phase excludes crash children. Recovery checks exact owner/ticket
semantics, then kills each Python-owned B0/B1/B2/B3/D0/D1 child only after its
matching handshake, confirms SIGKILL exit, and opens the same root in a fresh
process. Captures bind original state hashes, acknowledged control bytes,
new-content hashes/lengths, exact receipts and recreated-incarnation fencing.
The transfer phase uses generated paced non-seekable streams, warmed idle RSS,
OS peak RSS and actual full byte counts. No phase certifies the other provider's
durability or substitutes its output for the unfinished 96-case full manifest.
The package phase inspects eight actual resolved package graphs and compiled
public signatures, rejects provider/Hosting leak controls, compares baseline
members including accessibility/invocation flags, executes the original marker
binary with current platform assemblies and runs both unchanged consumer choices.
These are focused proofs, not complete AS-45/46 or full qualification.

Use `--update-locks` only for intentional dependency/project-manifest or local
package-payload changes; review those tracked locks and then run a separate
default locked acceptance. The approved F-06 unblock refreshes only local
`Hoard.*` package hashes, preserving dependency versions/graphs and external
hashes. Frozen baseline locks and binaries are never refreshed. A focused
locked replay still reports nonqualification. Do not install/restore
dependencies merely for planning.

## Scenarios to Inspect After Implementation

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

## Existing Regression Commands at Implementation

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
