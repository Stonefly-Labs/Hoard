# F-05 Durable Admission and Recovery

**Status**: Implemented test-fixture procedures, not product backup tooling.
Public outcomes: [metadata API](metadata-api.md). Run from the repository root:

```bash
# Fresh logical/package prerequisites, then all durable scenarios.
bash scripts/validate-metadata.sh --phase recovery
# Complete qualification also includes formatting, package boundaries and red/green.
bash scripts/validate-metadata.sh
```

The owner-private retained evidence contains `proofs/crash-M0.json` through
`crash-U4.json`, `recovery-walkthrough.json`, `ownership.json` and
`native-ownership.json`. The parent-controlled
[runner](../../../tests/fixtures/metadata/CrashRunner/Program.cs) seeds fixed
synthetic data, blocks at each named boundary, confirms signal exit and compares
reopened contents/receipts/baseline. No child exception substitutes for a crash.
Full results and actual version/filesystem attribution are recorded in the
[implementation evidence](../plan.md#implementation-evidence).

The compatible application identities are `fixture-sqlite-app-v1` and
`fixture-sqlite-app-v2`; they are reader modes in the same test-fixture binary,
not released production applications. Private methods
`CaptureRecoveryPointAsync` and `RestoreToIsolatedTargetAsync` belong to
`SqliteMetadataStore`, not the provider-neutral public contract. Memory's
logical upgrade authorization and immutable image are **not** recovery points.

## Qualification Configuration

Use a fresh private temporary directory on a local filesystem. Record runtime,
OS, driver/native SQLite versions and the effective PRAGMAs: journal mode WAL,
synchronous FULL, foreign keys on, native busy timeout zero. Reject unsupported
settings rather than downgrade guarantees. Use private connections and
parameterized commands; bind canonical keys as binary components, not
locale-dependent text. One owned worker serializes requests; explicit separate
test connections exercise actual engine isolation/lock contention.

Process termination is the durable fault model. Record this limitation:
SIGKILL/process-tree termination is not a power interruption, filesystem
corruption simulator or guarantee against device loss. Never qualify another
filesystem, engine or provider from these results.

## Schema Inventory and Admission

Provider-private schema versions are `fixture-sqlite-v1` and
`fixture-sqlite-v2`; the admitted public operation contract remains version 1.
v1 contains the complete logical entities, revisions, receipt ledger,
reference/lease tombstones, time floor and store epoch. v2 adds a private
nullable recovery-annotation column and an index without changing logical
values; its migration exercises a transactional copy/rebuild boundary.
The annotation has no public payload/extension API.

| Observed state | Inspect result | Explicit allowed action |
| --- | --- | --- |
| No user/schema records | Empty | `CreateIfEmpty`, creates v2 under exclusion |
| Recognized complete v2 | Compatible | Inspect-only admission, no changes |
| Recognized complete v1 | UpgradeRequired | Authorized v1 -> v2 with verified backup |
| Newer/unknown version, partial/unrecognized layout | Incompatible | Stop, retain bytes; compatible binary or verified restore |
| Recognized version but integrity/relation check fails | CorruptState | Stop, preserve evidence and recover; never treat as empty |

Empty detection inspects actual contents, not merely a missing version table.
An unrelated pre-existing SQLite database is incompatible, not permission to
create/drop tables. Verify schema shape and logical integrity before admitting
use, including receipts, reference edges and monotonic-generation state.
An unsupported path (including v2 -> v1) makes no modification.
Inspection opens existing data read-only and never changes journal mode,
schema or contents. Apply mutating connection/setup PRAGMAs only after
recognizing an admissible store under the explicit policy; inspecting an
unsupported future schema must leave its database/WAL bytes unchanged.

Normal use and upgrades require one process-lifetime exclusive owner of the
store's private lock file, using an OS-released lock, not lock-file existence.
The owner holds it from open through worker settlement/disposal; competing
opens/upgraders have bounded failure. Test actual second-process exclusion.
An upgrade additionally uses one SQLite write transaction and closes normal
operation admission. Do not delete/replace a locked file or blindly remove an
engine lock after a crash. SQLite/OS recovery, not a persistent "owner=true"
flag, releases ownership on process exit. This is local-file single-node
protection, not distributed coordination or an advisory-lock guarantee on NFS.

## Authorized Upgrade v1 to v2

1. Stop traffic/workers through the existing host lifecycle and acquire exclusive
   offline ownership. Inspect exact provider/version; refuse mismatch.
2. Capture a consistent backup through the private driver backup procedure.
   Reopen/restore it in an isolated target with a compatible v1 reader and
   compare all logical values, identities, references, receipts and schema ID.
   Record its content digest, capture ID and application compatibility.
3. Require an explicit `Upgrade(v1,v2,recoveryPoint)` request. The provider
   verifies the point belongs to the current store/capture and no mutation has
   occurred since it. A stale or unverified backup cannot authorize upgrade.
4. In one transaction, copy/rebuild the affected table, create the private
   column/index, validate row counts/relationships/receipt state, set schema v2,
   rotate the store epoch and invalidate old ticket/cursor admission.
5. Commit, reopen/check integrity and all logical contents, then admit normal
   operations. Retain the backup and version manifest until operator policy
   explicitly retires it. No background auto-upgrade or downgrade occurs.

Upgrade invalidates externally held operation tickets/cursors. Require all
uncertain operations reconciled and no reserved live operation tickets before
the backup/upgrade capture. Reject upgrade otherwise; do not orphan an action
and then encourage replay with a new ticket. Preserve committed receipt history
in the backup/migration; rotated epoch makes old execution impossible.

## Interrupted Upgrade Matrix

Parent-controlled crash barriers (each tested with baseline committed data):

| Boundary | Expected restart result | Operator action |
| --- | --- | --- |
| U0: after verified backup, before write transaction | Complete v1 | Reinspect and explicitly retry with verified point |
| U1: after private copy/rebuild starts, before schema-ID change | Transaction rolls back to complete v1 | Reinspect integrity, explicitly retry or restore |
| U2: after schema-ID/epoch update, before commit | Complete v1, old epoch | Same as U1; no mixed schema |
| U3: after commit before initialization acknowledgment | Complete v2, new epoch | Inspect/admit v2; never blindly repeat migration |
| U4: after admission acknowledgment | Complete v2 | Reopen/admit without mutation |

Child writes a named barrier acknowledgment only after reaching the exact
boundary, then blocks. Parent terminates only the known child PID/process tree
and waits for exit before reopening; do not release the child normally or use
an exception as a crash proxy. Timeouts are explicit test failures. At U1/U2,
an independent reader/admission attempt must not observe/use a mixed layout.

Capacity, disk/write errors or damaged schema during upgrade block admission.
Preserve the original and verified backup; never run guessed repair, silently
drop rows, reset to empty or fall back to memory/another provider.

## Backup and Restore Walkthrough

1. Quiesce application mutations and settle all owned native operations.
   Reconcile uncertain tickets; abandon unused reservations through the
   public API. Hold exclusive offline store ownership.
2. Use `SqliteConnection.BackupDatabase` into a new private destination,
   under a finite administrative budget (default 30 seconds, maximum two
   minutes). A stuck native call reports incomplete ownership rather than
   successful backup/cleanup. Never copy only the live main `.db`: committed
   state may still be in WAL.
3. Open the captured database in an isolated verification directory using the
   documented compatible application version. Run integrity checks and
   bounded traversal of every logical entity, ledger and generation table.
   Compute a stable logical digest in key order; record capture/provider/schema/
   application versions, backup digest and PRAGMAs, not private paths/secrets.
4. To restore, stop the current owner, retain the failed/current data separately,
   restore into private sibling staging and verify again before installation at
   a fresh target. Rotate epoch and close the complete staging database before
   its no-overwrite installation under target ownership. A cancellation or
   parent kill after native backup (R0) or before installation (R1) must leave
   the selected target absent, never admissible with the historical epoch.
   Old tickets/cursors must
   not execute against a historical ledger. Do not overwrite a live database
   or delete its WAL/SHM files by hand.
5. For rollback after an unsafe-to-reverse upgrade, select the compatible v1
   application and verified v1 backup. No inverse v2 -> v1 migration is promised.
   Changes after capture are not restored; the operator accepts the recovery
   point explicitly.
6. Reconcile restored metadata against the associated artifact-storage set
   through shared cache coordination before serving hits. Missing artifacts
   invalidate cache use, not proof of valid bytes; retain orphan blobs for
   later safe reconciliation. The metadata procedure does not restore blobs
   or authorize physical deletion.

The fixture walkthrough uses synthetic artifact authority and compares complete
bounded datasets. It proves a metadata recovery point, not live product
backup tooling or cross-engine export. Administrative handles/paths stay
provider-private and redacted from normal results, logs and qualification output.

## Mutation Crash Boundaries

The durable suite terminates separate children at M0 before commit decision,
M1 after native durable commit before caller acknowledgment, and M2 after
acknowledgment. Each group changes at least two related entities, reference
state and an aggregate contribution with one receipt.

M0 restarts with no group changes and a resolvable reserved ticket; reconcile
fences it as abandoned. M1/M2 restart with the complete group and committed
receipt, and identical replay before expiry has zero additional effects.
Seed the ticket before starting the child; acknowledgment barriers carry only
fixture IDs. Test all prior acknowledged baseline values after every crash.
Crash after blob commit but before metadata commit leaves no valid new entry;
it is an orphan-storage recovery case, not a rolled-back blob claim.
