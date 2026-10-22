# F-05 Metadata Validation Quickstart

**Status**: The additive operation contracts, independent test-only providers,
configured host adapters and qualification command are implemented. Qualification
is fail-closed and fixture-scoped, never production provider delivery. The
[plan](plan.md#implementation-evidence) records completed checks and stage gates.

## Prerequisites

Use Git, Python 3.11+, Bash and the stable .NET 10 SDK selected by `global.json`.
Restore pinned packages from nuget.org; Microsoft.Data.Sqlite 10.0.13 and all
transitive/native dependencies have tracked locks. Use a
private temporary directory on a local filesystem with enough room for database,
WAL and verified backup copies. No external database/cloud/container/listener
or native package-manager upstream is required.

Read the [API](contracts/metadata-api.md), [model](data-model.md),
[recovery procedure](contracts/recovery.md) and
[acceptance matrix](contracts/acceptance.md) first.

## Repository Tooling Checks

```bash
python3 -m unittest discover -s tests/tooling -v
git diff --check
```

These validate repository tooling/patch hygiene, not metadata semantics.

Setup-only modes are available for fresh, explicit owner-private destinations:

```bash
# No metadata qualification: freeze old binaries from immutable pre-F-05 main.
bash scripts/validate-metadata.sh --prepare-baseline /private/new/baseline
# No metadata qualification: additionally build/pack isolated fixture packages.
bash scripts/validate-metadata.sh --prepare-only /private/new/setup
```

Use `--update-locks` only for intentional manifest/dependency changes. Setup
pins Microsoft.Data.Sqlite 10.0.13 and its private native graph; the
[selection review](research.md#implementation-dependency-selection-2026-10-21)
records versions/licenses/advisory scope. Both modes explicitly report
`qualification: false`. Default locked replay rejects missing/drifted locks.
The historical T001..T006 checkpoint deliberately refused full qualification
until runtime proof existed. The completed runner now executes that proof;
preparation remains explicitly non-qualifying.

## End-to-End Fixture Acceptance

```bash
# Only after intentional manifest/source package changes; review resulting locks.
bash scripts/validate-metadata.sh --update-locks
# Independent immutable locked replay.
bash scripts/validate-metadata.sh
```

The first command intentionally updates only declared implementation dependency
locks; the default replay must fail on missing/drifted locks. The orchestrator
owns private temporary directories and bounded subprocesses (ten-minute maximum
per child, with stricter per-operation budgets), always reports errors, and
cleans up only its known paths/processes after confirming work stopped. It
retains an owner-private evidence directory outside Git before cleanup, printing
its location. `--evidence /private/new/proof` selects a fresh destination; the
parent must already exist and the destination must be outside the repository.
The destination is created owner-only before any proof is copied; preparation
and failed-run retention enforce the same boundary.
Retained fixture databases, captures, raw synthetic test inputs and binaries
are private diagnostics, not portable production backups. Remove only that
specific evidence directory after review, never a broad parent/workspace.

Executed phases: build/format; independent fixture packing; shared logical
suite against SQLite and memory; SQLite-only durability/upgrade/backup suite;
unchanged consumer execution for both composition choices; retained-binary/
architecture proof; complete attributable result manifest. Per-case results
must follow [qualification classes](contracts/acceptance.md#qualification-classes).
No test recursively invokes the orchestrator.

Focused selectors rebuild and verify fresh prerequisites in the same owned
workspace; they never trust a stale prior manifest:

```bash
# Each reports qualification: false, even when its selected proof passes.
bash scripts/validate-metadata.sh --phase logical
bash scripts/validate-metadata.sh --phase recovery
bash scripts/validate-metadata.sh --phase packages
```

`logical` freezes the old binary, prepares packages and runs the same common
assembly/consumer for both compositions. `recovery` additionally runs actual
SQLite child-stop/backup/restore/ownership proof. `packages` additionally runs
boundary, retained-binary and runtime red/green proof. Prerequisite source,
lock/package hashes and exact inventories are checked before each dependent
phase. Only unfiltered full mode includes the complete formatting gate and
reports full qualification.

Inspect `qualification.json`: 96 exact provider/case entries, including 39 L
cases for each provider, nine SQLite D passes and nine explicit memory D
non-applicability entries. Proof references/hashes, test durations, all eight
confirmed signal exits, actual environment and effective PRAGMAs are retained.
Each provider records the configured `fixture.metadata` module at version
`0.1.0` with configuration/options version 1; the configured-host scenario checks
the actual registration. Memory D exclusions reference the overclaim-refusal
proof with zero execution duration, never SQLite's durable results.
The runner reproduces assertion-level red/green pairs by disabling failed-case
refusal and post-commit exception uncertainty in isolated copies, then runs the
same tests against the repaired implementation. Compilation/import failure is
not accepted as that runtime evidence.

The providers use `MetadataResult<T>` failures with fixed codes, phase, retry
disposition and correlation. Before a commit attempt, cancellation/deadline
fences later execution. After an unobserved attempt, retain the ticket and
reconcile; do not automate a new-ticket replay. Expiry/epoch refusal requires
explicit application/operator recovery. Native work outliving its caller
retains authority guards and process/file ownership, including after explicit
incomplete cleanup.

## Scenarios to Inspect

1. Seed registries, auth partitions, packages/policies and artifact-backed
   entries using accepted synthetic publication guards. Read a consistent
   group/page; reopen SQLite and compare the entire bounded dataset.
2. Race first creation and same-revision updates with barriers. Assert one
   winner, explicit conflicts and unchanged losing state; inject mid-group
   failure to prove no partial visibility.
3. Reserve a ticket, commit a group including aggregate contribution, lose
   acknowledgment, reconcile and retry the same content. Assert one receipt
   and zero duplicate effects. At/after expiry or after backup restoration,
   require explicit refusal rather than new-ticket automated replay.
4. Exercise rejected evidence, shared-digest reference replacement, stale zero-
   reference decisions and expired/reacquired leases. Inspect retained guard
   ownership under cancellation; no metadata result can permit blob deletion.
5. Parent-terminate a known child at M0/M1/M2 and U0..U4, wait for exit and reopen.
   Compare complete expected state/receipt/schema, not just process exit codes.
6. Follow every [backup/restore step](contracts/recovery.md#backup-and-restore-walkthrough)
   with synthetic data: verified recovery point, authorized v1 -> v2, deliberate
   failure and isolated v1 restoration with compatible binary. Check epoch
   invalidation and required synthetic artifact reconciliation before use.
7. Run one consumer binary against SQLite and memory by composition change
   alone. Inspect manifests: all L cases both, D only SQLite, no production/
   alternative-engine/certification inference.

## Existing-Behavior Regression Gate at Implementation

```bash
bash scripts/validate-foundation.sh
bash scripts/validate-lifecycle.sh
bash scripts/validate-configuration.sh
bash scripts/validate-discovery.sh
python3 -m unittest discover -s tests/tooling -v
```

These are existing commands, but passing them does not establish F-05 acceptance.
Record exact commands/results alongside the new metadata evidence. Provider/
README/example guides must distinguish operation-contract qualification from
production SQLite delivery, with safe failure/upgrade/rollback instructions.
No OpenTofu apply, infrastructure mutation, package publication, release,
production database repair or rendered UI is part of this guide.

## Measured Implementation Results

`$PRIVATE_EVIDENCE` below represents the existing owner-private evidence parent
outside Git; personal directory paths are deliberately not published.

| Executed command | Result |
| --- | --- |
| `bash scripts/validate-metadata.sh --update-locks --evidence "$PRIVATE_EVIDENCE/metadata-qualified-update"` | Passed complete fixture qualification; resulting locks reviewed |
| `bash scripts/validate-metadata.sh --evidence "$PRIVATE_EVIDENCE/metadata-qualified-settled"` | Passed independent current-source locked qualification and formatting/analyzers; all locks unchanged |
| `bash scripts/validate-metadata.sh --phase packages --evidence "$PRIVATE_EVIDENCE/metadata-qualified-packages-repaired"` | Passed fresh prerequisite/package proof; correctly reports `qualification: false` |
| `bash scripts/validate-foundation.sh` | Passed 615 .NET tests and original package/compatibility/boundary proofs |
| `bash scripts/validate-lifecycle.sh` | Passed 504 tests, nine boundary proofs and seven package journeys |
| `bash scripts/validate-configuration.sh` | Passed 201 tests, six boundary proofs, nine package journeys and five real interruption barriers |
| `bash scripts/validate-discovery.sh` | Passed 137 tests, D01..D40, nine package journeys and 18 actual graph scans |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 76 tests |
| `git diff --check` | Passed |

The complete run executes 59 common tests per provider with zero failures or
skips and verifies 96 exact entries: 87 applicable passes and nine memory D
exclusions. Actual M0/M1/M2, U0..U4, R0/R1 and native-stall ownership/recovery
proof, unchanged binaries and all seven package graphs pass. The measured
environment is macOS 26.5.0/APFS, .NET 10.0.7, driver assembly 10.0.13.0 and
SQLite 3.53.3. These results qualify only this fixture configuration for the
documented process-stop fault model. See the [plan](plan.md#implementation-evidence)
for source attribution, architecture corrections and the complete requirement
audit; later convergence/finalization/merge/release gates remain separate.

### T084 continuation correction

The convergence-added correction is complete. Both fixture providers now
classify null/omitted decoded last keys as `InvalidInput/CorrectInput` before
dereference or hex decoding, without changing cursor binding, limits or valid
resumption. Six common theory variants corrupt every decoded field and verify
that rejected cursors leave valid paging and the complete dataset usable.
Null/omitted variants fail against both pre-repair packages, then pass after
the correction.

| Executed command | Result |
| --- | --- |
| `bash scripts/validate-metadata.sh --phase logical --update-locks --evidence "$PRIVATE_EVIDENCE/metadata-t084-logical"` | Passed 65 tests per provider; explicitly not full qualification |
| `bash scripts/validate-metadata.sh --evidence "$PRIVATE_EVIDENCE/metadata-t084-qualified"` | Passed formatting/analyzers and full locked qualification: 65 tests per provider, 87 applicable entries and nine explicit memory D exclusions; no lock mutation |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 76 tests |
| `git diff --check` | Passed |

The four refreshed downstream locks change only local fixture content hashes,
not dependencies or versions. Actual crash/restore, native ownership, package
graphs, retained marker and unchanged consumers pass again. Exact red commands,
source/configuration attribution and unaffected regression/review boundaries
are in the [plan](plan.md#t084-malformed-continuation-correction).
The next separately authorized stage is fresh convergence; PR #14 remains draft.
