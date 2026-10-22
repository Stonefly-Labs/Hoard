# F-05 Metadata Validation Quickstart

**Status**: Implementation in progress. The preparation/evidence command and
project scaffolds now exist; operational adapters and full qualification do
not. Full and focused qualification deliberately fail until their attributable
runtime prerequisites exist. Do not infer support from packaging scaffolds.

## Prerequisites

Use Git, Python 3.11+, Bash and the stable .NET 10 SDK selected by `global.json`.
Restore pinned packages from nuget.org; implementation must choose/check/pin
the new private SQLite dependency and track all changed/new lockfiles. Use a
private temporary directory on a local filesystem with enough room for database,
WAL and verified backup copies. No external database/cloud/container/listener
or native package-manager upstream is required.

Read the [API](contracts/metadata-api.md), [model](data-model.md),
[recovery procedure](contracts/recovery.md) and
[acceptance matrix](contracts/acceptance.md) first.

## Checks Available Today

```bash
python3 -m unittest discover -s tests/tooling -v
git diff --check
```

These validate repository tooling/patch hygiene, not metadata semantics.

Setup-only modes are available for fresh, explicit owner-private destinations:

```bash
# No metadata qualification: freeze old binaries from immutable pre-F-05 main.
bash scripts/validate-metadata.sh --prepare-baseline /private/new/baseline
# No metadata qualification: additionally build/pack isolated fixture scaffolds.
bash scripts/validate-metadata.sh --prepare-only /private/new/setup
```

Use `--update-locks` only for intentional manifest/dependency changes. Setup
pins Microsoft.Data.Sqlite 10.0.13 and its private native graph; the
[selection review](research.md#implementation-dependency-selection-2026-10-21)
records versions/licenses/advisory scope. Both modes explicitly report
`qualification: false`. Default locked replay rejects missing/drifted locks.
T001..T006 preparation passed, with 12 tooling cases and an intended runtime
negative for failed-case acceptance. Full mode currently exits 1 with
`Metadata qualification incomplete`; this is the required fail-closed setup
result, not a failed or passing metadata implementation.

## Planned End-to-End Acceptance

After implementation introduces/documents the entry point:

```bash
# Future initial dependency/lock generation, then independent locked replay.
bash scripts/validate-metadata.sh --update-locks
bash scripts/validate-metadata.sh
```

The first command intentionally updates only declared implementation dependency
locks; the default replay must fail on missing/drifted locks. The orchestrator
owns private temporary directories and bounded subprocesses (ten-minute maximum
per child, with stricter per-operation budgets), always reports errors, and
cleans up only its known paths/processes after confirming work stopped.

Expected phases: build/format; independent fixture packing; shared logical
suite against SQLite and memory; SQLite-only durability/upgrade/backup suite;
unchanged consumer execution for both composition choices; retained-binary/
architecture proof; complete attributable result manifest. Per-case results
must follow [qualification classes](contracts/acceptance.md#qualification-classes).
No test recursively invokes the orchestrator.

For a focused rerun after prepared evidence exists, the implementation should
expose these bounded selectors:

```bash
# Future focused selectors; neither alone establishes complete qualification.
bash scripts/validate-metadata.sh --phase logical
bash scripts/validate-metadata.sh --phase recovery
bash scripts/validate-metadata.sh --phase packages
```

`logical` runs the same cases against both independent implementations;
`recovery` runs real file-backed SQLite child-stop and operator recovery cases;
`packages` runs unchanged-consumer, boundary and old-binary proof.
Any selector must fail explicitly if prerequisite evidence is absent/stale.

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
