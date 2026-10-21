# F-05 Resolved Research

**Date**: 2026-10-21. Design decisions, not implementation results.

## 1. Add operations without changing existing markers

**Decision**: Keep `IMetadataProvider : IHoardProvider` unchanged. Add
`IMetadataStore`, schema-administration and publication-authority contracts in
`Hoard.Abstractions.Metadata`. Consumers receive the selected store explicitly
through the host adapter, never query a service locator or infer a default.

**Rationale**: Existing F-01 fixtures and retained binaries implement an empty
marker. F-02 already owns singleton selection/admission and F-03 owns options
and secret resolution. Operational opt-in must not break declaration-only
providers or introduce a second composition/lifecycle authority.

**Alternatives considered**: Adding required members to the existing marker
breaks old implementations; default interface implementations can conceal
missing guarantees. A new abstractions assembly adds packaging work without
demonstrated need. Public `DbContext`, transactions and generic `IQueryable`
would violate the established boundary.

**Repository evidence**:
`src/Hoard.Abstractions/Providers/IMetadataProvider.cs`,
`src/Hoard.Hosting/Lifecycle/IHoardModule.cs`,
`src/Hoard.Hosting/Configuration/HoardModuleOptions.cs`,
and [provider guidance](../../docs/PROVIDERS.md).

## 2. Real SQLite proof with a minimal private adapter

**Decision**: Use direct `Microsoft.Data.Sqlite`, parameterized SQL, binary
identity comparisons and application-owned revision values. Pin a supported
stable 10.x package and native dependencies at implementation after advisory
and license review. Require checked WAL, FULL synchronous mode and foreign
keys on each connection; reject an unsupported configuration.

**Rationale**: The acceptance focus needs actual transactions, recovery and
upgrades, not a production ORM/model. SQLite WAL allows readers with a writer
but still has only one writer. FULL syncs the WAL on commit; claims remain
limited to tested local configurations/process failure, not hardware loss.

**Alternatives considered**: EF Core would also be legal privately but adds
model/migration machinery not needed by this fixture. EF SQLite lacks native
database-generated concurrency tokens and has migration/query limitations.
No ORM dependency is needed merely to demonstrate contract neutrality.
SQLite `:memory:` cannot prove restart durability.

**Primary sources**:
[SQLite WAL](https://www.sqlite.org/wal.html),
[synchronous PRAGMA](https://www.sqlite.org/pragma.html#pragma_synchronous),
[foreign keys](https://www.sqlite.org/foreignkeys.html),
[EF SQLite limitations](https://learn.microsoft.com/en-us/ef/core/providers/sqlite/limitations).

## 3. Bounded asynchronous facade over synchronous SQLite

**Decision**: One explicitly owned worker per SQLite store, queue capacity 32,
no per-call detached `Task.Run`, native busy timeout disabled, and bounded
nonblocking lock-acquisition attempts under a monotonic operation deadline.
Use synchronous native calls only on that worker; expose `ValueTask` contracts.
Late execution remains tracked and prevents disposal/admission until settled.

**Rationale**: Microsoft.Data.Sqlite async methods execute synchronously.
Cancellation/deadlines bound caller waiting but cannot terminate arbitrary
native/filesystem calls. A commit already attempted requires reconciliation,
not a false cancellation/rollback result. There is no claim of hard real-time
termination on a stuck device.

**Alternatives considered**: Calling `ExecuteNonQueryAsync` alone falsely
suggests nonblocking/cancellable I/O; unbounded task creation or hidden engine
busy retries loses the work budget. Killing a worker thread is unsafe.

**Primary sources**:
[SQLite async limitations](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/async),
[busy timeout](https://www.sqlite.org/c3ref/busy_timeout.html).

## 4. Atomic receipts, not blind retries

**Decision**: Reserve a provider-issued persisted ticket, valid for 24 hours,
before submitting a mutation. Store the mutation fingerprint and committed
receipt atomically with its changes. Reconciliation serializes with writers;
it returns a committed receipt or fences an unused ticket as abandoned.
Expired/unknown tickets never execute, even if their old receipt was pruned.

**Rationale**: Connection loss during commit cannot prove rollback. At-most-once
aggregate contributions need the same atomic ledger as state updates. Requiring
an existing reserved ticket avoids replay after retention without maintaining
permanent unbounded tombstones or trusting caller timestamps.

**Alternatives considered**: A caller-generated ID with receipt deletion can
replay after expiry; automatic retry assumes rollback; an external in-memory
receipt does not survive a crash; distributed exactly-once claims exceed scope.

**Primary source**:
[commit failure and idempotency](https://learn.microsoft.com/en-us/ef/core/miscellaneous/connection-resiliency#transaction-commit-failure-and-the-idempotency-issue).
The principle applies independently of EF's SQL Server-oriented retry strategy;
no such strategy is assumed for SQLite.

## 5. Independent semantics and honest qualification

**Decision**: Build the alternative with immutable dictionaries and one
serialized atomic root swap. Share only public records/validation of wire
bounds, test inputs and assertions, not SQL or transaction/reference/lease
algorithms. Run the same unchanged consumer and logical suite twice.

**Rationale**: A wrapper around SQLite is not independent. EF InMemory ignores
or rejects transaction semantics and cannot establish this contract's guarantees.
Memory results explicitly exclude durable restart/crash/backup qualification.

**Alternatives considered**: A second production engine introduces external
infrastructure and premature rollout. EF InMemory or mocked store methods do
not prove all-or-nothing state and conditional writes.

**Primary source**:
[EF testing without a database](https://learn.microsoft.com/en-us/ef/core/testing/testing-without-the-database#in-memory-provider).

## 6. Authority, references and leases remain separate

**Decision**: Host injects one shared publication authority into the operational
store. It validates opaque artifact evidence and holds a guard through the
metadata outcome. Metadata owns transactional reference edges, revisions and
fenced lease generations; it never verifies bytes, deletes blobs or invents
canonical identities. Lease decisions use a persisted nondecreasing UTC floor
and a final transaction-local ownership/expiry check.

**Rationale**: Metadata alone cannot establish cross-store integrity or protect
readers. Tombstoned artifact/lease generations prevent ABA after removal and
reacquisition. Clock rollback must not resurrect an ownership generation already
expired or superseded by a committed decision.

**Alternatives considered**: A caller-supplied `Committed=true` is not accepted
evidence; reference count zero is not physical deletion permission; lease names
do not establish distributed fencing/HA. No cache engine or F-06 byte store is
implemented to test this seam.

**Repository sources**: Constitution III/IV and
[architecture section 9](../../docs/ARCHITECTURE.md#9-persistence-and-object-store-neutrality).

## 7. Controlled schema admission and backup restoration

**Decision**: Qualification schema has exactly one supported upgrade, v1 to v2.
Create/upgrade requires explicit policy, exclusive offline store ownership and
a verified recovery point for upgrades. A single SQLite transaction changes
data and schema version; named crash barriers cover before, during and after
commit. Use the driver's backup API under quiescence; verify by restoring into
an isolated target before upgrade. Never copy a live main database file alone.

**Rationale**: SQLite's backup API produces a coherent database, including
committed WAL state. Quiescence simplifies the qualification procedure.
Transactions plus exclusive application admission prevent mixed-schema use.
EF SQLite's persistent migration-lock row can be abandoned on termination:
adding EF would not remove the need for explicit recovery and finite waits.

**Alternatives considered**: Automatic startup upgrades, destructive downgrade,
blind deletion of an engine lock, guessed repair and cross-engine transfer are
unsafe or outside scope. Safe rollback here is verified backup restoration,
not a promise that every migration has an inverse.

**Primary sources**:
[SQLite online backup](https://www.sqlite.org/backup.html),
[Microsoft.Data.Sqlite backup](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/backup),
[SQLite concurrent migration limitations](https://learn.microsoft.com/en-us/ef/core/providers/sqlite/limitations#concurrent-migrations-protection).

All exact bounds, operation shapes, schema paths and recovery mechanics are
resolved in the accompanying contracts. Package selection is a normal pinned
implementation dependency step, not an unresolved product decision. No external
documentation query included repository source, connection settings or secrets.
