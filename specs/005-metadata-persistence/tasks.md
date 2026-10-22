# Tasks: Metadata Persistence Provider Contract

**Input**: Design documents from `specs/005-metadata-persistence/` (F-05).
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md),
[research.md](research.md), [data-model.md](data-model.md),
[metadata API](contracts/metadata-api.md), [recovery](contracts/recovery.md),
[acceptance](contracts/acceptance.md) and [quickstart.md](quickstart.md).

**Status**: All 85 implementation tasks are verified and complete, including
immutable qualification/regression replay, documentation, requirement audit
and the T084 malformed-continuation and T085 stored-page corruption
corrections with paired red/green proof.
The driver checkpoint schedules a fresh `converge` next;
convergence/finalization/merge/release are not part of this implementation.
The built-in requirements checklist remains 16/16. The reviewer-owned
[metadata](checklists/metadata.md) and [recovery](checklists/recovery.md)
checklists record the separately requested assisted review, 40/40 satisfied.
That completed review, not generation or analysis, satisfies the implementation
gate. Their markers are read-only during implementation.

**Tests**: Explicitly required by FR-023/FR-024, the five independent story
tests, SC-001..SC-008 and MP-01..MP-48. Write positive and rejection/fault
checks first and record the intended red result before implementing the
behavior. A missing-type compile failure proves only an initial API gap;
atomicity, deadlines, sanitization, ownership and recovery need runtime
negatives that fail without their mechanism. Use controlled clocks/barriers,
not sleeps as correctness evidence. D cases require actual parent-terminated
children, confirmed exit and reopened contents, never an exception crash proxy.

**Organization**: Shared setup and minimum admitted transaction infrastructure
precede five story phases in specification priority order, then cross-cutting
acceptance. The stories are independently testable increments of one contract,
not independent storage engines: their actual dependencies are explicit below.
US1 is the smallest useful round-trip increment, not complete qualification or
a usable cache. During a subsequently authorized implementation invocation,
continue through every remaining task; a successful phase/checkpoint is not a
request to stop or renew authorization.

## Format: `[ID] [P?] [Story] Description`

- Every task has a checkbox, sequential ID and repository-relative destination
  paths. Only story tasks carry `[US1]` through `[US5]`.
- `[P]` marks file-disjoint ready work after the listed prerequisites, not
  permission to run agents or a workflow engine. The prerequisite table is
  authoritative; numerical adjacency alone is not a dependency.
- FR/SC IDs refer to the specification; MP IDs refer to the acceptance matrix.
  All numeric/value constraints quoted below are normative, not implementation
  choices. Read the linked model/contracts for the complete operation semantics.
- Filenames describe cohesive responsibilities. Reuse existing helpers;
  equivalent grouping may be recorded in implementation evidence without
  weakening semantics, proof inventory or provider independence.

## Path Conventions

Public additions belong in `src/Hoard.Abstractions/Metadata/`, BCL-only.
Keep existing `IMetadataProvider`, descriptors, registration, lifecycle and
configuration signatures unchanged. Core remains provider-free; do not build a
cache engine, production persistence provider, artifact store, endpoint or UI.

`tests/fixtures/metadata/Sqlite/` and `Memory/` are independently packed,
test-only providers referencing Abstractions, never each other, Core,
Application or Hosting. SQLite alone adds its private checked driver. They may
share public value validation, inputs and assertions, never transaction,
reference, lease or recovery implementations. HostAdapters owns the approved
F-02/F-03 integration outside those provider packages.

Use existing xUnit, architecture inspection and Python/Bash evidence patterns.
Fixtures and consumer/crash tools are standalone projects; add the focused
contract tests to `Hoard.slnx`. Track every new/changed package lock. Generate
locks only for declared manifest changes, then independently replay locked
acceptance without lock mutation. Package outputs, database/WAL/backup files,
retained binaries and canary inputs belong to an owner-private temporary
workspace, never Git. Every subprocess has a maximum ten-minute timeout;
operations and administration have their stricter documented budgets.

No network filesystem, cloud account, listener, external database, package
publication, F-07 certification, power-loss rig or product CI is introduced.
Fixture results cannot establish production support, other engines, arbitrary
filesystems, multi-node coordination or physical blob-deletion permission.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare fail-closed evidence and pre-change compatibility proof
before changing platform dependencies or behavior.

- [X] T001 [P] Create `tests/contracts/Hoard.Metadata.Tests/Hoard.Metadata.Tests.csproj` and `MetadataTestHarness.cs` with existing xUnit conventions, deterministic clocks, caller/engine/authority barriers, synthetic records and canary capture; add the test project to `Hoard.slnx`, keep new fixture projects standalone, and make every held activity observable with finite teardown.
- [X] T002 [P] Write failing `tests/tooling/test_metadata_evidence.py` for missing/duplicate/stale case and package inventories, false memory durability, missing red/green proof, failed/timed-out children, absent barrier/exit/state evidence, unsafe cleanup, lock/hash drift and partial-phase prerequisites; use synthetic evidence inputs, not recursive acceptance execution.
- [X] T003 Introduce `scripts/validate-metadata.sh` and `scripts/metadata_evidence.py` using existing evidence helpers: prerequisite checks, private workspace, bounded subprocesses, explicit failures, `--update-locks`, default locked mode and `--phase logical|recovery|packages`; full qualification must fail until every applicable proof exists and focused phases must reject absent/stale prerequisites.
- [X] T004 [P] Add `tests/fixtures/metadata/RetainedMarker/RetainedMarker.csproj`, `Program.cs` and `Baseline/packages.lock.json` as recipes for a marker/registration consumer compiled against an immutable merged pre-F-05 revision into the private workspace; freeze source/binary/dependency hashes before new Abstractions code, reuse existing retained-registration evidence where suitable, and never rebuild the retained binary against the new API (MP-47).
- [X] T005 Select a stable supported 10.x `Microsoft.Data.Sqlite` version with current advisory, license and native/transitive-dependency review; record nonsecret selection evidence in `specs/005-metadata-persistence/research.md`, pin it in `Directory.Packages.props`, create `tests/fixtures/metadata/Sqlite/Sqlite.csproj`, `Memory/Memory.csproj`, `Consumer/Consumer.csproj`, `CrashRunner/CrashRunner.csproj` and `HostAdapters/HostAdapters.csproj`, and generate/review their `packages.lock.json` files with the driver confined to SQLite.
- [X] T006 Extend `scripts/metadata_evidence.py` to build the retained baseline before current code, independently restore/build/pack fixture projects, compile tests against prepared packages and fingerprint source/manifests/locks; run T002 tooling negatives and prove incomplete full mode fails rather than producing a qualification-shaped success.

**Checkpoint**: Baseline provenance and a failing incomplete acceptance runner
exist; no metadata support claim follows from scaffolding or package compilation.

Setup evidence (2026-10-21): initial missing-runner red; 12 tooling cases green;
removing failed-case rejection produces the intended runtime assertion failure,
then the unmodified verifier passes. Baseline-only and package-preparation modes
complete with `qualification: false`; default locked full mode fails explicitly
because logical/recovery/package runtime evidence does not yet exist. The
package-only test harness builds against the prepared Abstractions package.
Private run artifacts retain recipe/binary/source/lock/package hashes.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define the additive closed contract and minimal admitted stores,
including the shared prerequisites needed to test each later story.

- [X] T007 Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataValueTests.cs` and `MetadataContractTests.cs` for immutable bounded inputs, invalid/default values, exact encoding, closed results/operations and redacted handles; enforce "All collections are immutable, initialized and bounded before enumeration or copying", compare the pre-F-05 public surface and pair every rejection with a valid boundary value (MP-01/04/05/22/47).
- [X] T008 Add `src/Hoard.Abstractions/Metadata/MetadataValues.cs` with the model's exact constraints: `MetadataId` is "Nonempty GUID; canonical 16-byte network-order representation"; `CanonicalText` is "1..1,024 UTF-8 bytes, valid Unicode, no NUL/control characters or unpaired surrogates; exact byte equality, no case/Unicode/URL normalization"; `PublicLabel` is "0..512 UTF-8 bytes, plain text without controls"; revision is "Opaque nonempty 128-bit value; newly assigned on each successful replacement, never reused on deletion/recreation; not a timestamp or sortable sequence"; expected revision is "Closed choice `Absent` or `Match(revision)`; no unconditional overwrite/delete"; instant is "UTC Unix milliseconds, inclusive 0..253402300799999; non-millisecond or non-UTC inputs are invalid"; digest is "SHA-256, exactly 32 bytes; lowercase hex only for textual display"; lengths/counters are "Signed 64-bit, nonnegative; checked overflow rejects the complete mutation"; optional dimensions use "an explicit `None` union case".
- [X] T009 Add `src/Hoard.Abstractions/Metadata/MetadataRecords.cs` with every model entity/key and explicit immutable option choices: secret reference is "Structured owner ID, resolver ID and opaque key, each at most 128 UTF-8 bytes"; request method is "uppercase token, at most 16 ASCII bytes" with required caller-supplied auth partition, and "Request targets cannot contain credentials"; upstreams are "absolute HTTPS/HTTP URIs without user info, query or fragment, at most 2,048 UTF-8 bytes"; headers are "At most 32 approved header values, at most 8 KiB encoded total", allow only content type/cache-control/ETag/last-modified/expires/vary/content-language, and enforce "ETag is at most 512 bytes and header values contain no CR/LF". Cache status is "200..299", timestamps satisfy "`created <= validated <= freshUntil`"; policy durations are "0..31,536,000,000 ms" with nonnegative byte limits, aggregate interval is "Nonempty half-open `[start,end)`, at most 24 hours", and schema versions are "bounded to 64 ASCII bytes".
- [X] T010 Add `src/Hoard.Abstractions/Metadata/MetadataOperations.cs` and `MetadataEncoding.cs` for all closed selectors, seven page-query kinds and listed mutations; batches/read groups have "1..64" items, each logical mutation target occurs at most once, whole-batch lease guards cannot mutate the guarded lease, and "Maximum encoded request/result is 1 MiB". Deterministic UTF-8 encoding uses fixed field order, GUID network bytes, integer milliseconds, explicit optional choices and counters/revisions; fingerprint excludes renewable evidence handles, never logical digest/length, expectations, scopes or guard.
- [X] T011 Add `src/Hoard.Abstractions/Metadata/IMetadataStore.cs`, `IMetadataSchemaAdministration.cs`, `IMetadataPublicationAuthority.cs` and `MetadataResults.cs` with the exact separate API interfaces, async disposal and closed result/receipt/resolution/schema/guard records; existing marker gains no members. Use fixed failure/phase/action codes and correlation IDs, redacted ticket/cursor/evidence/recovery views, no payload-bearing receipt, raw exception, database/query type, service locator or success-shaped failure (MP-21/22/47).
- [X] T012 Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataAdmissionTests.cs` for ordinary calls before admission, explicit empty creation, compatible inspection, invalid configuration/timeout rejection and disposal; add shared positive/rejection scenarios that both providers must run while distinguishing logical schema simulation from durability (MP-19/21/32/33/37).
- [X] T013 [P] Implement `tests/fixtures/metadata/Sqlite/SqliteMetadataStore.cs`, `SqliteWorker.cs` and `SchemaV2.sql` as minimum file-backed admitted infrastructure: private parameterized SQL for all logical tables/ledger/edges/tombstones/time floor/epoch, exact binary keys, read-only inspection before recognized mutating policy, checked WAL/FULL/foreign keys/busy-timeout zero, explicit v2 creation and one owned worker with 32 waiting operations. Do not expose partial writes, automatic migration or a production provider claim.
- [X] T014 [P] Independently implement `tests/fixtures/metadata/Memory/MemoryMetadataStore.cs` and `MemoryState.cs` with immutable committed roots, serialized copy-on-write candidate swaps, explicit logical admission and the same bounds/outcomes; no SQLite calls, EF InMemory, delegated SQLite state machine or durable recovery point. Keep all state/transaction algorithms private and distinct.
- [X] T015 [P] Add `tests/fixtures/metadata/HostAdapters/ControlledPublicationAuthority.cs` and `MetadataFixtureModule.cs` using existing `IHoardModule`, configured singleton selection and owner-scoped options: register without opening a store, open/inspect/explicitly prepare in InitializeAsync, map no routes, block readiness/use on failure and stop/dispose through existing resource ownership. Disabled fixtures must open no file, worker, secret or connection; the authority is injected once, never caller-substituted.
- [X] T016 Implement the minimum reserve/typed-commit/read plumbing in `tests/fixtures/metadata/Sqlite/SqliteMutations.cs` and `Memory/MemoryMutations.cs`: persisted SQLite reservations and atomic changes+receipt, independent memory equivalents, final candidate-graph validation independent of input order, exact revision conditions, host-injected publication guard acquisition outside writer exclusion and atomic entry/edge changes; use positive lease/aggregate fixtures without claiming the later interleaving/recovery cases passed.
- [X] T017 Run T007/T012 through `scripts/metadata_evidence.py` with both prepared providers and T015 adapters; record initial red and green for additive contracts/minimum admission, preserved opt-out behavior and finite teardown. Keep full qualification incomplete; no unimplemented later MP case may pass merely because its public type exists.

**Checkpoint**: Both admitted fixtures can execute bounded synthetic work.
Later story gates, not this checkpoint, establish their correctness scope.

## Phase 3: User Story 1 - Retain Correctly Isolated Cache State (Priority: P1)

**Goal**: Retain exact bounded records and identity partitions across reads and
SQLite clean restart without inventing canonicalization or leaking credentials.

**Independent Test**: Round-trip every entity/optional field in a bounded
synthetic dataset, compare all values/relationships/partitions, traverse
unchanged 0/1/100/205-row datasets and reopen SQLite. Seed special lease/receipt
states through controlled fixture setup where necessary; their mutation and
failure guarantees remain US2/US3 obligations. Covers US1.1..5, MP-01..08/13;
acknowledged abrupt-restart durability is additionally proven by US2 MP-40.

### Tests for User Story 1

- [X] T018 [P] [US1] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataRoundTripTests.cs` for every entity, optional field, policy/aggregate scope and accepted value boundary, plus clean SQLite reopen; reject malformed identities/relationships, fractional/non-UTC timestamps, overflow, cross-scope policy links and invalid aggregate keys without truncation or partial state (MP-01/05/06).
- [X] T019 [P] [US1] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataIdentityTests.cs` for two registries/auth partitions including explicit anonymous partitions, exact case/Unicode/escaped keys and caller-normalized duplicate conflicts; reject malformed Unicode, credential-bearing URIs, forbidden headers/raw-credential shapes and preserve losing state (MP-02..04).
- [X] T020 [P] [US1] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataPagingTests.cs` for 0/1/100/205 rows, unsigned UTF-8/network-GUID/numeric tuple order, exact-once unchanged traversal, oversized request/result failures, query-bound cursor rejection and specified concurrent insertion/deletion/replacement effects without cross-page snapshot promises (MP-07/08).
- [X] T021 [P] [US1] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataRelationshipTests.cs` for final-graph insertion/deletion in different input orders, explicit bounded child+parent removal, rejected referenced-parent/implicit-cascade deletion, policy/aggregate children, package/registry ecosystem matching and disabled-registry retention with publication refusal (MP-01/06/13).

### Implementation for User Story 1

- [X] T022 [US1] Complete `tests/fixtures/metadata/Sqlite/SqliteRecords.cs` and extend `SqliteMutations.cs` for exact binary-key serialization, all scoped records, conditional CRUD, checked aggregates and final graph referential integrity; keep SQL/connection errors private and preserve complete candidate rollback on structural failure.
- [X] T023 [P] [US1] Independently complete `tests/fixtures/metadata/Memory/MemoryRecords.cs` and extend `MemoryMutations.cs` for the same public records, identity/scope/final-graph rules and defensive immutable values, without sharing SQLite transaction/relationship algorithms.
- [X] T024 [P] [US1] Implement `tests/fixtures/metadata/Sqlite/SqliteReads.cs` for all selectors in one committed snapshot, explicit per-item absence and whole-group corruption/unavailability failure; materialize bounded immutable results and never expose a lazy reader or reference-edge enumeration.
- [X] T025 [P] [US1] Implement `tests/fixtures/metadata/Memory/MemoryReads.cs` from one immutable root per group, with explicit absence and equivalent bounded/error semantics; independent calls need not share a historical root.
- [X] T026 [US1] Add `src/Hoard.Abstractions/Metadata/MetadataContinuation.cs` plus `tests/fixtures/metadata/Sqlite/SqlitePages.cs` and `Memory/MemoryPages.cs`: page size "1..100", cursor "Encode/decode bounds are 16 KiB", complete query/version/epoch/order/page-size binding, ascending tuple comparison and strictly-greater last-key continuation. Preserve cursors across ordinary reopen of the same epoch/schema, reject changed scopes/foreign epochs, and fail oversized successful pages rather than shortening them.
- [X] T027 [US1] Extend `scripts/metadata_evidence.py` and `tests/contracts/Hoard.Metadata.Tests/MetadataHostIntegrationTests.cs` to execute actual configured SQLite/memory adapter selection, ready/failed/disabled paths and clean SQLite reopen; assert no fallback, disabled activity, endpoint, duplicate lifecycle authority or discovery support claim (MP-01/13/32/46).
- [X] T028 [US1] Run T018..T021 and T027 through `scripts/metadata_evidence.py`, recording attributable paired MP-01..08/13 results against both implementations and clean-restart contents; document the bounded US1 MVP and outstanding concurrency, lease/reference and durable qualification in `specs/005-metadata-persistence/quickstart.md`.

**Checkpoint**: US1 round-trip/isolation/page acceptance passes. This is not
complete L/D qualification, production persistence or permission to stop.

## Phase 4: User Story 2 - Resolve Concurrent Changes Without Partial Success (Priority: P1)

**Goal**: Atomic groups/reads, explicit conflicting writes and reconcilable
uncertain outcomes remain bounded under contention, cancellation and crashes.

**Independent Test**: Controlled readers/writers see all-old or all-new state,
one conflicting winner and no duplicate receipt/contribution. Fault each
candidate change; end caller waits at finite deadlines while retaining owned
late work. Kill/reopen SQLite at M0/M1/M2 and compare complete baseline/group/
receipt state. Covers US2.1..5, MP-09..22/31/37..40.

### Tests for User Story 2

- [X] T029 [P] [US2] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataAtomicityTests.cs` and `MetadataConcurrencyTests.cs` with barriers for mid-candidate rollback, grouped old/new reads, independent reads straddling commit, concurrent first creates and same-revision update/delete/delete-recreate conflicts; use actual separate SQLite connections where isolation/lock behavior is asserted, not only the store queue (MP-09..13).
- [X] T030 [P] [US2] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataOperationTests.cs` for original receipt replay, changed committed fingerprint conflict, renewable evidence excluded from fingerprint, lost acknowledgment reconciliation, reserved-ticket abandonment fencing delayed commits, aggregate once-only effects, concurrent distinct contributions and exact expiry/foreign/pruned ticket refusal (MP-14..18/31).
- [X] T031 [P] [US2] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataBudgetTests.cs`, `MetadataFailureTests.cs` and `MetadataOwnershipTests.cs` for cancellation at each decision boundary, finite queue/lock/authority budgets, counter/ledger/queue/storage capacity, corruption versus absence, every safe failure class/canary exclusion and late native-call cleanup ownership; prove bounded caller results without pretending native I/O was preempted (MP-18..22/27/37).

### Implementation for User Story 2

- [X] T032 [US2] Complete `tests/fixtures/metadata/Sqlite/SqliteOperations.cs` and integrate `SqliteMutations.cs` with transaction-local final revisions/relationships/fingerprint and atomic committed receipts: tickets have "24-hour lifetime", ledger capacity "100,000", prune "only expired ledger rows, at most 100 per reservation", and reconcile serializes with commits to return the receipt or atomically abandon/fence a reservation. Missing/foreign/expired tickets never execute; definite rollback retains the same reserved ticket.
- [X] T033 [P] [US2] Independently complete `tests/fixtures/metadata/Memory/MemoryOperations.cs` and integrate `MemoryMutations.cs` with equivalent root-atomic tickets/receipts, abandonment exclusion, capacity/pruning, final revision checks, nonduplicate aggregate contributions and expired-ticket refusal; do not reuse SQLite ledger/transaction logic.
- [X] T034 [US2] Complete `tests/fixtures/metadata/Sqlite/SqliteWorker.cs` for a monotonic overall budget, default five seconds and allowed 1 ms..30 seconds, 32 queued calls, immediate native busy detection and only lock-acquisition retries at most 50 ms apart within the original budget; validation, queueing, authority acquisition, I/O and result construction share that budget. A late unobserved commit returns Uncertain with ticket, blocks new admission and retains connection/guards until settlement; finite cleanup never disposes live work or reports false success.
- [X] T035 [P] [US2] Complete `tests/fixtures/metadata/Memory/MemoryAdmission.cs` and `MemoryMetadataStore.cs` for the same finite budget/admission/cancellation/disposal outcomes without simulating SQLite internals; distinguish known non-commit from uncertainty, reject invalid timeout before worker/I/O and retain owned late authority/candidate work until settled.
- [X] T036 [US2] Add `tests/fixtures/metadata/Sqlite/SqliteFailures.cs` and `Memory/MemoryFailures.cs` to translate known capacity/unavailable/corruption/commit-phase failures into closed safe outcomes; unexpected faults must emit a safe structured event and explicit operator-recovery failure, never raw exception text, content-bearing diagnostics, empty success or fallback (MP-20..22).
- [X] T037 [US2] Implement `tests/fixtures/metadata/CrashRunner/Program.cs` and `MutationCrashScenario.cs` for parent-seeded reservations and named M0/M1/M2 barriers around a group changing at least two related entities, artifact references and an aggregate+receipt; acknowledgment carries only safe fixture IDs, and the child blocks at the exact boundary without self-throwing a fake crash.
- [X] T038 [US2] Extend `scripts/metadata_evidence.py` with bounded parent control that waits for each exact M barrier, terminates only its known child PID/process tree, confirms exit before reopening, compares all baseline and group/receipt data and performs same-ticket reconciliation/replay; record effective WAL/FULL/foreign keys and OS/runtime/native version, distinguishing process-stop proof from power/device loss (MP-38..40).
- [X] T039 [US2] Run T029..T031 and M0/M1/M2 cases through `scripts/metadata_evidence.py` with both L implementations and SQLite-only D attribution; prove one conflicting winner, no partial state, zero duplicate contribution and explicit late-work ownership, preserving every earlier MP result.
- [X] T040 [US2] Add failing/repaired `tests/contracts/Hoard.Metadata.Tests/MetadataTelemetryTests.cs` for scoped concurrent and uncertain aggregate contributions, checked overflow, duplicate batch targets and invalid contribution rollback of the entire entry/reference group; keep telemetry policy/aggregation scheduling outside providers (MP-06/16/20/31).
- [X] T041 [US2] Update `specs/005-metadata-persistence/quickstart.md` with actual focused logical/mutation-recovery selectors, exact red/green evidence and safe same-ticket retry/reconcile/expiry guidance; record deterministic state comparisons, finite error outcomes and remaining upgrade/reference qualification, never all-case acceptance from partial results.

**Checkpoint**: US2 transaction/operation and mutation-crash proof passes.
Publication/reference/lease adversarial cases and schema recovery remain.

## Phase 5: User Story 3 - Preserve Artifact References and Coordination Ownership (Priority: P1)

**Goal**: Accepted shared-authority evidence protects atomic metadata visibility;
stale reference observations and expired/replaced owners cannot act.

**Independent Test**: Controlled authority guards reject uncommitted/forged/
mismatched evidence, survive late work, and distinguish orphan blobs from
committed entries. Race shared-digest changes and zero-reference observations;
exercise lease expiry, reacquisition, clock changes and final decision checks.
Covers US3.1..4, MP-23..30, with US2 late-work/receipt regression.

### Tests for User Story 3

- [X] T042 [P] [US3] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataPublicationTests.cs` and `MetadataReferenceTests.cs` pairing accepted authority evidence with missing/forged/uncommitted/mismatched evidence, same digest multiple edges, atomic replacement/removal, stale zero-reference revision including ABA, and committed-blob/failed-metadata orphan recovery (MP-23..26).
- [X] T043 [P] [US3] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataGuardTests.cs` for one guard per distinct digest/length, acquisition outside internal locks/transactions, exact artifact matching, host-only authority injection, already-committed replay without new evidence, renewal-independent fingerprint and retained guards through rollback/late native settlement/caller cancellation (MP-14/23/27/37).
- [X] T044 [P] [US3] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataLeaseTests.cs` for exact owner/generation/revision, acquisition/reacquisition/release tombstones, just-before/exact expiry and final guarded decision, forward/backward clocks and overflow; lease reads must not certify current ownership and no case may claim distributed locking (MP-28..30).

### Implementation for User Story 3

- [X] T045 [US3] Complete `tests/fixtures/metadata/Sqlite/SqlitePublication.cs` and extend `SqliteMutations.cs` to acquire all authority guards before the transaction, validate digest/length, preserve immutable length per digest, change entries/edges/reference revisions atomically and retain zero-edge generations; ConfirmUnreferenced requires the current revision and zero live edges, producing only metadata evidence, never physical deletion authority.
- [X] T046 [P] [US3] Independently complete `tests/fixtures/metadata/Memory/MemoryPublication.cs` and extend `MemoryMutations.cs` with guard-protected candidate/root publication, edge accounting, immutable digest length, retained reference generations and stale/ABA rejection; share no SQLite reference algorithm and persist/log no raw evidence.
- [X] T047 [US3] Complete `tests/fixtures/metadata/Sqlite/SqliteLeases.cs` with "effectiveNow = max(current UTC milliseconds, persistedTimeFloor)", durably advancing the floor with every ownership/ticket-time decision; TTL is "1..300 seconds", "`effectiveNow >= expires` expired", generation is positive/increments on reacquisition and "overflow fails, never wraps". Check batch owner/generation/expiry under writer exclusion immediately before commit; renew from effectiveNow and tombstone release.
- [X] T048 [P] [US3] Independently complete `tests/fixtures/metadata/Memory/MemoryLeases.cs` with the same effective-time/final-guard/generation semantics in root-atomic decisions, then extend T030 ticket-time tests in `MetadataOperationTests.cs` for clock rollback and exact expiry using the same public time rules.
- [X] T049 [US3] Integrate settlement-owned guard cleanup in `tests/fixtures/metadata/Sqlite/SqliteWorker.cs`, `SqlitePublication.cs`, `Memory/MemoryAdmission.cs` and `MemoryPublication.cs`; exercise actual stalled authority/commit work and stop through `HostAdapters/MetadataFixtureModule.cs`, proving no connection/guard disposal under live work, blocked admission and explicit incomplete ownership (MP-27/37).
- [X] T050 [US3] Add `tests/fixtures/metadata/HostAdapters/OrphanReconciliationScenario.cs` using synthetic committed artifacts and failed metadata, including the real M1/M0 evidence where applicable; prove no valid new entry on non-commit and no fictitious artifact rollback, byte verification or safe-deletion grant (MP-25/26/39).
- [X] T051 [US3] Run T042..T044 and T049/T050 via `scripts/metadata_evidence.py`, recording paired MP-23..30 results for both providers, relevant MP-14/27/37/39 regressions and observed guard lifetime/committed reference counts at every barrier.
- [X] T052 [US3] Update `specs/005-metadata-persistence/quickstart.md` and `docs/PROVIDERS.md` with actual evidence/lease/reference signatures and qualified limits: caller canonicalization/auth, byte integrity, cross-store sequencing, active readers and physical deletion remain outside metadata; fixture composition is not a discovered production capability or distributed coordination.

**Checkpoint**: US3 authority/reference/lease acceptance passes without adding
an artifact store, cache engine, GC authority or multi-node guarantee.

## Phase 6: User Story 4 - Upgrade and Recover Durable Metadata Deliberately (Priority: P1)

**Goal**: Inspect/admit only recognized stores, explicitly authorize supported
upgrades with a verified recovery point, and recover complete captured state.

**Independent Test**: Exercise Empty/Compatible/UpgradeRequired/Incompatible/
CorruptState and unchanged unrelated/future databases. Verify v1 capture,
explicit v1-to-v2, U0..U4 termination, second-process ownership, compatible v1
restore, epoch invalidation and synthetic artifact reconciliation. Memory
proves only the applicable logical admission state machine, never a D result.
Covers US4.1..5, MP-32..36/41..45 and ownership MP-37.

### Tests for User Story 4

- [X] T053 [P] [US4] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataSchemaTests.cs` for all admission states, true-empty versus unrelated/partial layout, unchanged newer schema, corruption, explicit create/upgrade only, expected version/path and missing/stale recovery authorization; memory must exercise MP-32..35 semantics without producing a durable recovery point.
- [X] T054 [P] [US4] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataBackupTests.cs` and `MetadataUpgradeTests.cs` for complete logical capture/digest, committed WAL content, wrong provider/application/capture, stale/unverified backup, unresolved/reserved tickets, preserved receipts and epochs/cursors; unsupported inverse/downgrade leaves data intact (MP-34/36/44/45).
- [X] T055 [P] [US4] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataUpgradeCrashTests.cs` and `MetadataStoreOwnershipTests.cs` for every U barrier, actual second-process store/upgrader exclusion, bounded loser, crash-released OS lock and future-schema database/WAL byte hashes; require reopened schema/contents and no mixed-layout admission, not merely an exit code (MP-35/41..43).

### Implementation for User Story 4

- [X] T056 [US4] Complete `tests/fixtures/metadata/Sqlite/SqliteSchemaAdministration.cs` and add `SchemaV1.sql`: v1 includes all entities/ledger/tombstones/time floor/epoch; v2 adds the private nullable recovery annotation/index via transactional rebuild. Read-only inspection must validate recognized shape/integrity without mutating database/WAL or PRAGMAs; distinguish empty/compatible/old/new/corrupt and gate every ordinary API, never reinterpret unrelated data as empty.
- [X] T057 [US4] Implement `tests/fixtures/metadata/Sqlite/SqliteStoreOwnership.cs` with a process-lifetime OS-released exclusive private-file lock held through worker settlement/disposal, plus offline single-upgrader admission; no lock-file-existence heuristic, lock deletion, live-file replacement or guessed repair. Normal use and upgrade contenders receive finite classified failure without weakening SQLite writer exclusion.
- [X] T058 [US4] Implement `tests/fixtures/metadata/Sqlite/SqliteBackup.cs` for quiescence/settled work and no unresolved/live reservations, finite driver `BackupDatabase`, isolated compatible-reader verification and bounded full logical/ledger/generation traversal; retain private handles and record safe capture/provider/schema/application IDs and digests, never live-main-file-only copying or normal-output paths.
- [X] T059 [US4] Implement `tests/fixtures/metadata/Sqlite/SqliteUpgrade.cs` for explicit `Upgrade(v1,v2,verifiedRecoveryPoint)`, current-store/capture freshness, no intervening mutation and writer exclusion; atomically copy/rebuild, validate logical contents/relations/receipts, set v2 and rotate epoch before commit, then reopen/verify/admit. Preserve backup/history; unknown paths and failures remain blocked without reset, downgrade or fallback.
- [X] T060 [P] [US4] Implement `tests/fixtures/metadata/Memory/MemorySchemaAdministration.cs` with independent logical classification, explicit policy, synthetic verified-state authorization and single upgrade/use owner for MP-32..35; distinguish this fixture-private simulation from a real recovery point, and report all nine D cases as NotApplicable rather than passed/skipped logical obligations.
- [X] T061 [US4] Implement `tests/fixtures/metadata/Sqlite/SqliteRestore.cs` and `CrashRunner/RecoveryScenario.cs` for restoration into a fresh target with the documented compatible v1 reader/application, full digest verification and epoch rotation before admission; preserve original/backup data, explicitly lose post-capture writes, reject restored-away tickets/cursors and require synthetic artifact reconciliation before cache-use claims (MP-36/44/45).
- [X] T062 [US4] Add `tests/fixtures/metadata/CrashRunner/UpgradeCrashScenario.cs` and extend `Program.cs` with blocking U0 after verified backup, U1 during rebuild, U2 after schema/epoch update before commit, U3 after commit before acknowledgment and U4 after admission acknowledgment; include independent read/admission attempts at U1/U2 and safe barrier IDs only.
- [X] T063 [US4] Extend `scripts/metadata_evidence.py` parent orchestration for U0..U4 and real competing owner/upgrader children: terminate exact known children, confirm exit, reopen and compare complete v1/old epoch at U0..U2 or v2/new epoch at U3/U4, execute explicit retry/restore, reject repeated migration/old handles, and verify OS lock release and unchanged unsupported future database/WAL bytes.
- [X] T064 [US4] Complete administrative deadline/cleanup wiring in `tests/fixtures/metadata/Sqlite/SqliteSchemaAdministration.cs`, `SqliteBackup.cs`, `tests/fixtures/metadata/Memory/MemorySchemaAdministration.cs` and `tests/fixtures/metadata/HostAdapters/MetadataFixtureModule.cs`: positive overall default 30 seconds, maximum two minutes, including exclusion, verification and migration; late native calls retain ownership and prevent readiness/clean disposal rather than claiming hard preemption or successful recovery.
- [X] T065 [US4] Run T053..T055 and actual backup/restore/upgrade/owner scenarios through `scripts/metadata_evidence.py`; require paired logical MP-32..35 and SQLite D MP-36/41..45 with all U barrier contents, captured-state digest, compatible application identity and explicit artifact-reconciliation results, preserving earlier crash/guard acceptance.
- [X] T066 [US4] Replace future-only recovery instructions in `specs/005-metadata-persistence/contracts/recovery.md` and `quickstart.md` with reproducible implemented fixture commands and exact evidence for upgrade, backup, rollback/restore, compatible application versions, finite failures and artifact reconciliation; retain original normative outcomes and distinguish process-stop/local-filesystem limits from device-loss or product backup support.
- [X] T067 [US4] Update `tests/contracts/Hoard.Metadata.Tests/MetadataHostIntegrationTests.cs` and run actual F-02/F-03 configured adapter initialization/failure/stop paths: no schema auto-upgrade, second lifecycle, secret re-resolution, fallback or usable store before admission, no disabled resource activity, and incomplete native cleanup must remain owned and non-ready (MP-32..37/43).

**Checkpoint**: Supported schema paths and every documented interruption have
verified resume-or-restore evidence; memory remains non-durable.

## Phase 7: User Story 5 - Qualify an Alternative Without Rewriting Cache Operations (Priority: P2)

**Goal**: Prove the same unchanged package consumer and logical suite across
independent providers, with exact case/version/configuration attribution and
fail-closed support boundaries.

**Independent Test**: Run the same consumer binary/common case assembly with
only explicit host composition changed; compare both complete L inventories.
SQLite additionally supplies every D result. Reject missing/failed obligations,
SDK/schema leaks and altered/rebuilt retained binaries. Covers US5.1..4,
MP-46..48 and the portability obligation for every preceding case.

### Tests for User Story 5

- [X] T068 [P] [US5] Write failing `tests/contracts/Hoard.Metadata.Tests/MetadataQualificationTests.cs` for all 48 exact IDs/classes/applicability, case artifact attribution, duplicate/missing/failed required results, provider/configuration mismatch and memory D/production overclaims; no capability declaration, compilation or fixture-only result can qualify untested engines (MP-48).
- [X] T069 [P] [US5] Write failing `tests/architecture/Hoard.Architecture.Tests/MetadataBoundaryTests.cs` using prepared real package graphs/public surfaces and focused forbidden fixtures under `tests/fixtures/metadata/Forbidden/`: reject driver/connection/SQL/query/provider-type leaks and forbidden Core/consumer edges while permitted SQLite-private dependencies pass; preserve every earlier scanner rule and required inventory (MP-47).

### Implementation for User Story 5

- [X] T070 [US5] Implement `tests/fixtures/metadata/Consumer/Program.cs`, `MetadataJourney.cs` and host composition in `HostAdapters/MetadataComposition.cs`: one compiled provider-neutral journey and unchanged common logical case assembly run both implementations using only explicit composition/adapter selection, never provider conditionals in business logic, source references, private schemas or changed cache/management source (MP-46).
- [X] T071 [US5] Extend `scripts/metadata_evidence.py` package phase to independently pack SQLite/memory/host adapters and run the unchanged consumer/common suite with locked local package feeds; hash consumer/common binaries before and after both selections, record exact package identities/graphs and retain package-only dependency isolation.
- [X] T072 [US5] Extend `tests/architecture/Hoard.Architecture.Tests/MetadataBoundaryTests.cs`, the existing public-surface/graph inspection helpers only where needed and `scripts/metadata_evidence.py` to execute permitted/forbidden actual packages with paired intended scanner failures; run the frozen old marker/registration binary unchanged against the new platform, checking hashes/provenance rather than recompiling it (MP-47).
- [X] T073 [US5] Complete `scripts/metadata_evidence.py` qualification manifest with exact schema/provider/module/package/native versions, source commit, OS/runtime/local-filesystem/effective safe PRAGMAs, case/class/applicability/result/duration, barrier/exit/state evidence, proof hashes and limitations; require all 39 L cases for each provider and nine additional D cases for SQLite, with explicit `NotApplicable: non-durable fixture` for memory D and no raw paths/settings/records/canaries.
- [X] T074 [US5] Run `tests/tooling/test_metadata_evidence.py` and `MetadataQualificationTests.cs` against omitted/failed/stale/foreign/hash-mismatched proof to demonstrate claim rejection; then run `bash scripts/validate-metadata.sh --phase packages` with prepared current prerequisites and record consumer/boundary/retained-binary MP-46..48 acceptance.
- [X] T075 [US5] Update `docs/PROVIDERS.md` and `examples/CustomHost/README.md` with opt-in separate metadata interfaces, marker-only compatibility, host-owned admission/secrets/authority composition and one-authority selection, plus independent L/D scope and production nonclaims; use compiled fixture-backed examples, not production SQLite/PostgreSQL APIs that do not exist.
- [X] T076 [US5] Run the same full logical case inventory against both independently packaged fixtures via `scripts/metadata_evidence.py`, confirm no implementation algorithm is shared beyond allowed public validation/test inputs, and record MP-01..35/37/46..48 outcomes and honest D applicability without waiving any L obligation.
- [X] T077 [US5] Update `specs/005-metadata-persistence/plan.md` and `contracts/acceptance.md` with attributable logical/durable/package evidence and actual supported fixture configurations; keep spec outcomes intact, every MP case individually accounted for and production/F-07/other-engine claims explicitly excluded.

**Checkpoint**: Unchanged-consumer portability and complete fixture-scoped
qualification are demonstrated, not inferred from declared capabilities.

## Phase 8: Polish and Cross-Cutting Acceptance

**Purpose**: Verify the exact complete requirements, preserve existing behavior
and hand off honest documentation and reviewed boundaries.

- [X] T078 Run `bash scripts/validate-metadata.sh --update-locks` only for the intentional declared dependency changes, review every resulting tracked lock, then independently run `bash scripts/validate-metadata.sh` with no lock mutation; require build/SDK formatting/analyzers, all applicable MP results, real crash/recovery, consumer/boundary/old-binary proof and complete manifest, recording exact commands/results in `specs/005-metadata-persistence/quickstart.md`.
- [X] T079 Run `bash scripts/validate-foundation.sh`, `bash scripts/validate-lifecycle.sh`, `bash scripts/validate-configuration.sh`, `bash scripts/validate-discovery.sh`, `python3 -m unittest discover -s tests/tooling -v` and `git diff --check`; fix tightly coupled regressions without weakening prior checks/inventories and record exact results and unchanged locks in `specs/005-metadata-persistence/plan.md`.
- [X] T080 [P] Update `README.md` and `docs/DEVELOPMENT.md` for the implemented metadata contract/fixtures and actual validation commands, linking acceptance/recovery and distinguishing qualification from production cache/providers; review affected provider/example/compatibility guides and diagrams, explicitly justify unchanged surfaces and document operational permissions/manual recovery/rollback limits.
- [X] T081 Perform the required bounded `hoard-architecture-review` of public additions, package graphs, provider independence, host admission/late ownership and shared authority/reference/lease boundaries; record findings and resolved evidence in `specs/005-metadata-persistence/plan.md`, fix in-scope blockers and rerun affected proof rather than treating the historical planning review as implementation approval.
- [X] T082 Audit `specs/005-metadata-persistence/tasks.md`, `plan.md`, `quickstart.md` and `contracts/acceptance.md` against all 24 FRs, eight SCs, 23 story scenarios, 14 edge cases and 48 MP cases; require runtime red-to-green/attribution, no unchecked or unverified earlier implementation task, no leaked secret/private artifact and no overstated production/durability support. Preserve reviewer-owned checklist markers; unresolved evidence blocks completion.
- [X] T083 Commit coherent verified artifacts and checkpoint through the separately authorized implementation stage, push immediately after each commit and update draft PR #14 using `.github/pull_request_template.md`; record remaining gates in `docs/DEVELOPMENT.md`. All implementation tasks must pass before the driver finishes implementation; do not run convergence/finalization, merge, tag, publish packages or apply infrastructure in that invocation.

## Dependencies and Execution Order

### Task Prerequisites

Each row lists **direct** prerequisites; their ancestors are also required.
Ranges are inclusive. `T018..T021`, for example, means all four tasks.
No unlisted numeric adjacency is a prerequisite. Each story's test-writing
tasks record the intended red before their corresponding implementation.
Where a base mechanism already exists, demonstrate a failing targeted
negative/fault variant, not a fabricated red result.

| Task(s) | Direct prerequisites |
| --- | --- |
| T001, T002, T004 | None |
| T003 | T002 |
| T005 | T001, T004 |
| T006 | T003, T004, T005 |
| T007 | T006 |
| T008 | T007 |
| T009 | T008 |
| T010 | T009 |
| T011 | T010 |
| T012 | T011 |
| T013, T014, T015 | T012 |
| T016 | T013, T014, T015 |
| T017 | T016 |
| T018, T019, T020, T021 | T017 |
| T022, T023 | T018, T019, T021 |
| T024 | T022 |
| T025 | T023 |
| T026 | T020, T024, T025 |
| T027 | T026 |
| T028 | T027 |
| T029, T030, T031 | T028 |
| T032, T033 | T029, T030 |
| T034 | T031, T032 |
| T035 | T031, T033 |
| T036 | T034, T035 |
| T037 | T036 |
| T038 | T037 |
| T039 | T038 |
| T040 | T039 |
| T041 | T040 |
| T042, T043, T044 | T041 |
| T045, T046 | T042, T043 |
| T047 | T044, T045 |
| T048 | T044, T046 |
| T049 | T047, T048 |
| T050 | T049 |
| T051 | T050 |
| T052 | T051 |
| T053, T054, T055 | T052 |
| T056 | T053, T054 |
| T057 | T055, T056 |
| T058 | T057 |
| T059 | T058 |
| T060 | T053 |
| T061 | T059 |
| T062 | T061 |
| T063 | T055, T062 |
| T064 | T060, T063 |
| T065 | T064 |
| T066 | T065 |
| T067 | T066 |
| T068, T069 | T067 |
| T070 | T068 |
| T071 | T069, T070 |
| T072 | T071 |
| T073 | T072 |
| T074 | T073 |
| T075 | T074 |
| T076 | T075 |
| T077 | T076 |
| T078 | T077 |
| T079 | T078 |
| T080 | T077 |
| T081 | T079, T080 |
| T082 | T081 |
| T083 | T082 |

T022 and T023 are ready together; only T023 carries `[P]` to indicate the
independent provider lane. The same convention applies to T032/T033,
T034/T035, T045/T046 and T047/T048. T060 can run alongside the SQLite schema
lane after its own red tests. T080 edits different documents while T078/T079
record acceptance. Never parallelize edits to the same file: all orchestrator
changes are serialized; baseline T004 completes before platform changes;
US1/US2/US3 share provider mutation/worker files in the listed order; T048
modifies operation tests only after US2 is complete. Do not treat distinct
provider files as permission to share their implementation algorithms.

### Phase and Story Graph

```text
Setup T001..T006
  -> Foundation T007..T017
  -> US1 T018..T028 (P1: bounded retention/isolation/page MVP)
  -> US2 T029..T041 (P1: transaction/reconciliation/budget/crash)
  -> US3 T042..T052 (P1: adversarial publication/reference/lease)
  -> US4 T053..T067 (P1: schema/upgrade/backup/restore)
  -> US5 T068..T077 (P2: unchanged-consumer qualification)
  -> Cross-cutting T078..T083
```

US2 builds on US1 records/read paths. US3 builds on US2 settled-outcome and
ownership mechanisms. US4 requires those receipts/epochs/references and closed
ownership before quiescent capture. US5 requires all prior cases to prove
unchanged full logical behavior. Their checks can run independently after
prerequisites, but stories are not falsely advertised as parallel implementations.
All five stories are mandatory for full F-05 delivery.

## Requirement and Acceptance Traceability

Ranges are inclusive. The acceptance contract's class/scenario/edge mapping
remains authoritative; shared setup/foundation and final full gates support
every row without replacing the focused behavior proof.

| Requirement | Implementation tasks | Focused proof tasks / MP cases |
| --- | --- | --- |
| FR-001 | T008..T016, T022..T026 | T018/T021/T028; MP-01/06/07/13 |
| FR-002 | T008..T010, T022..T026 | T019/T020/T029; MP-02..04/08/11 |
| FR-003 | T008..T010, T022/T023 | T007/T018/T038; MP-01/05/40 |
| FR-004 | T016, T022/T023 | T021/T029; MP-01/09/13 |
| FR-005 | T016, T032/T033, T045/T046 | T029/T039/T040; MP-09/24/31/38..40 |
| FR-006 | T024/T025 | T029/T039; MP-10 |
| FR-007 | T016, T022/T023, T032/T033 | T029/T039; MP-11..13 |
| FR-008 | T010, T032..T035, T047/T048 | T030/T038/T039; MP-14..18/38..40 |
| FR-009 | T003, T008..T010, T026, T034/T035, T064 | T020/T031/T039/T065; MP-07/19/20/37 |
| FR-010 | T011, T036, T056..T059 | T031/T039/T053/T065; MP-18..22/32..37 |
| FR-011 | T011, T016, T045/T046, T049 | T042/T043/T051; MP-23/24/27 |
| FR-012 | T045/T046 | T042/T051; MP-24/25 |
| FR-013 | T024/T025, T036, T050, T061 | T031/T038/T042/T065; MP-21/26/39/45 |
| FR-014 | T047..T049 | T044/T051; MP-28..30 |
| FR-015 | T010, T024..T026 | T020/T028; MP-07/08 |
| FR-016 | T009, T022/T023, T032/T033 | T018/T030/T040; MP-06/16/31 |
| FR-017 | T012..T016, T056/T057, T060/T064 | T053/T055/T065/T067; MP-32/33/35/43 |
| FR-018 | T057..T064 | T053..T055/T065/T067; MP-34..36/41..43 |
| FR-019 | T008/T009/T011, T036, T073 | T007/T019/T031/T069/T074; MP-04/22/47 |
| FR-020 | T037/T038, T062/T063 | T039/T055/T065; MP-38..43 |
| FR-021 | T058/T059/T061, T066 | T054/T065; MP-36/44/45 |
| FR-022 | T011/T015, T070..T072 | T069/T074; MP-46/47 |
| FR-023 | T003/T006, T073 | T068/T074/T076/T078/T082; MP-01..48 by class |
| FR-024 | T005/T013/T014, T070..T073 | T065/T074/T076/T078; MP-01..48 by class |

| Outcome | Evidence tasks | Required observable result |
| --- | --- | --- |
| SC-001 | T018..T021/T028/T038/T039 | Exact retained values; zero duplicate identities or cross-partition observations, including durable restart |
| SC-002 | T029/T039/T051 | One conflicting winner, explicit losers and no lost committed references |
| SC-003 | T029..T031/T038..T040/T051/T065 | Complete group or none; zero duplicated replay effects at every failure/crash boundary |
| SC-004 | T042..T044/T051 | Reject invalid publication/stale reference/expired owner; no metadata-only deletion claim |
| SC-005 | T053..T055/T063/T065/T067 | All U boundaries recover complete state, unchanged unsupported data and verified captured restore |
| SC-006 | T070/T071/T074/T076 | One unchanged binary/common suite, two independent implementations; D claims only where applicable |
| SC-007 | T007/T020/T031/T039/T051/T065/T074 | Finite classified failures, zero canary exposure and complete unchanged-dataset pagination |
| SC-008 | T065/T066/T068/T073/T074/T077/T078/T082 | 100% applicable attributable cases, reproducible recovery and honest L/D/production separation |

| Acceptance cases | Test/proof tasks |
| --- | --- |
| MP-01..06 | T007/T018/T019/T021/T028 |
| MP-07..08 | T020/T028 |
| MP-09..13 | T021/T029/T039 |
| MP-14..18 | T030/T039/T048 |
| MP-19..22 | T031/T039 |
| MP-23..27 | T042/T043/T049..T051 |
| MP-28..30 | T044/T051 |
| MP-31 | T040 |
| MP-32..35 | T012/T053/T055/T065/T067 |
| MP-36 | T054/T065 |
| MP-37 | T031/T039/T049/T064/T067 |
| MP-38..40 | T037..T039 |
| MP-41..43 | T055/T062/T063/T065 |
| MP-44..45 | T054/T061/T065 |
| MP-46 | T027/T070/T071/T074/T076 |
| MP-47 | T004/T069/T072/T074 |
| MP-48 | T068/T073/T074 |

US1.1..5 map to T018..T021/T028 plus T038/T039; US2.1..5 to
T029..T031/T038..T040; US3.1..4 to T042..T044/T049..T051; US4.1..5 to
T053..T055/T061..T067; US5.1..4 to T068..T077.
The 14 edge cases, in specification order, map to:
T018/T019; T021; T029/T042; T029; T030/T038; T030/T040;
T044; T042/T050/T061; T031/T054; T020; T018/T044;
T055/T063; T054/T058/T065; T031/T069/T074.

## Parallel Examples by User Story

These are scheduling examples, not instructions to launch agents.

| Ready point | File-disjoint work |
| --- | --- |
| US1 after T017 | T018 round-trip tests, T019 identity tests, T020 paging tests and T021 relationship tests |
| US1 after red tests | T022 SQLite records/mutations and T023 independent memory records/mutations; T024/T025 reads in their respective ready lanes |
| US2 after T028 | T029 atomicity/concurrency tests, T030 ticket tests and T031 budget/failure/ownership tests |
| US2 after red tests | T032 SQLite operations and T033 memory operations, followed by their respective T034/T035 admission work |
| US3 after T041 | T042 publication/reference tests, T043 guard tests and T044 lease tests |
| US3 after red tests | T045 SQLite publication and T046 memory publication, followed by each lane's T047/T048 lease work |
| US4 after T052 | T053 schema tests, T054 backup/upgrade tests and T055 process/ownership tests |
| US4 after T053..T055 | T060 memory logical schema simulation alongside T056..T059 SQLite schema/ownership/backup/upgrade |
| US5 after T067 | T068 qualification tests and T069 architecture negatives |
| Final after T077 | T080 README/development documentation alongside T078/T079 acceptance and evidence recording |

## Implementation Strategy

### MVP First

Complete setup/foundation and US1, then validate its bounded data/identity/page
increment through the actual selected fixture adapters and clean SQLite reopen.
This is the suggested MVP scope, not a product deployment or complete F-05
claim. Do not certify concurrency, crash recovery, upgrades or lease/reference
safety from that subset.

### Incremental Delivery

Proceed US1 -> US2 -> US3 -> US4 -> US5, maintaining earlier checks after
each change and sharing coherent commits immediately. Each story gate is a
validation point within the full implementation invocation, not a stop/approval
boundary. Fix in-scope failures and continue unless genuinely blocked.
After all 83 tasks and complete locked acceptance pass, the driver may finish
implementation and schedule a separate convergence invocation. Convergence,
finalization, feature merge and the authorized post-merge source prerelease
remain later gates; no dependency/backlog completion follows from task checks.

## Notes

- Counts: setup 6, foundation 11, US1 11, US2 13, US3 11, US4 15, US5 10,
  cross-cutting 6; total 83, all initially unchecked.
- No extension hooks are configured. No runtime, schema operation, dependency
  change, new runner execution or checklist approval occurs in task generation.
- Red/green proof, exact commands/results and safe attributable manifests must
  be retained in implementation evidence. Do not tick failed/unverified work.
- Existing foundation/lifecycle/configuration/discovery acceptance must remain
  unchanged in meaning. Do not loosen scanners or silently omit old proofs.

## Phase 9: Convergence

- [X] T084 Validate required decoded continuation fields before dereferencing or decoding them in `tests/fixtures/metadata/Sqlite/SqlitePages.cs` and `tests/fixtures/metadata/Memory/MemoryPages.cs`: a query/epoch-matching cursor with null or omitted `LastKey`/`After` currently returns `InternalFailure/OperatorRecovery` instead of `InvalidInput/CorrectInput`. Add paired null/omitted/malformed-field rejection and valid-resume regressions to `tests/contracts/Hoard.Metadata.Tests/Cases/MetadataPagingTests.cs` for both independently packaged providers; preserve query/scope/epoch binding, finite decode bounds and unchanged store usability, replay the applicable qualification checks, and update affected evidence/documentation per FR-010, FR-015, US1/AC5 and T026/T036 (MP-08) (partial).

T084 evidence: both freshly packaged providers fail the null and omitted
regressions with `InternalFailure` before the repair. Null-safe bounded key
patterns now reject those fields before dereference/hex decoding. Six common
theory cases mutate each decoded field (null, omitted, wrong-type, empty,
odd-length and invalid hex); each rejection asserts
`InvalidInput/CorrectInput/Page`, then resumes the original cursor successfully.
Complete remaining and original traversals prove unchanged store usability.
Focused logical replay passes; full independent locked qualification passes
65 common tests per provider, all 87 applicable entries and nine explicit
memory durability exclusions, including existing scope/epoch binding,
crash/recovery/package/old-binary proofs and formatting/analyzers. Four fixture
consumer locks change only local fixture content hashes; default replay
preserves them. Repository tooling passes 76 tests. See
[correction evidence](plan.md#t084-malformed-continuation-correction).

## Phase 10: Convergence

- [X] T085 Classify invalid stored page records as `CorruptState/OperatorRecovery/Page` in `tests/fixtures/metadata/Sqlite/SqlitePages.cs`, reusing the existing corruption-aware record decoding in `SqliteMetadataStore.cs` rather than translating caller validation failures globally: a persisted registry payload with `Label: null` currently returns `InvalidInput/CorrectInput/Page`, while the identical record in a grouped read correctly returns `CorruptState/OperatorRecovery/Read`. Add focused regressions in `tests/contracts/Hoard.Metadata.Tests/Cases/MetadataFailureTests.cs` for syntactically valid but structurally/value-invalid stored records and malformed JSON, requiring whole-page failure without partial rows, sanitized diagnostics and preserved stored data; pair them with valid-page recovery and unchanged `InvalidInput/CorrectInput` results for malformed caller queries/continuations and oversized results. Replay applicable locked qualification and update affected evidence/documentation per FR-010, FR-013, SC-007 and T024/T026/T036 (MP-21/22) (partial, HIGH).

T085 evidence: the new packaged MP-21 regression first fails with expected
`CorruptState`, actual `InvalidInput` (65 passing tests, one failure). Page
and exact reads now share the existing bounded corruption-aware decoder,
including canonical stored-key comparison. SQLite-specific cases cover null
label/revision, oversized label, malformed JSON and mismatched identity:
both read paths fail completely with sanitized operator-recovery results,
leave the damaged payload unchanged and recover the exact original page
after synthetic payload restoration. Both fixtures also pass the shared
page-corruption assertion. Caller query/continuation and oversized-result
failures retain `InvalidInput/CorrectInput/Page`. Focused and full locked
replay pass 66 tests per provider; full qualification retains 87 applicable
passes and nine memory D exclusions. Four locks change only local SQLite/
HostAdapters content hashes; default replay preserves them. Tooling passes
76 tests. See [T085 evidence](plan.md#t085-stored-page-corruption-correction).

## Phase 11: Convergence

- [ ] T086 Prevent corrupt persisted query dimensions from disappearing behind page filters in `tests/fixtures/metadata/Sqlite/SqlitePages.cs`: a stored cache entry with null `Identity.AuthorizationPartition` currently yields a successful empty scoped page although exact/grouped reads report `CorruptState/OperatorRecovery/Read`. Make candidate selection and stored-record validation preserve `CorruptState/OperatorRecovery/Page` without weakening query/auth isolation, bounded work/results or deterministic continuation semantics; audit the aggregate interval/partition and lease-prefix predicates for the same omission. Add focused package-only regressions to `tests/contracts/Hoard.Metadata.Tests/Cases/MetadataFailureTests.cs` proving whole-page failure, unchanged damaged data, sanitized diagnostics and valid-page recovery, paired with legitimate empty foreign-scope pages and existing pagination/input-rejection controls. Record runtime red/green evidence, replay applicable locked qualification and update affected documentation per FR-010, FR-013, FR-015, US1/AC5, SC-007 and T024/T026/T036 (MP-21/22) (partial, HIGH).
- [ ] T087 Validate bounded persisted operation/receipt data before returning committed replay or reconciliation results in `tests/fixtures/metadata/Sqlite/SqliteOperations.cs`, reusing the existing receipt validation/integrity mechanisms in `SqliteIntegrity.cs` and `MetadataEncoding` where suitable: a committed receipt with null `Revisions[0].Target` currently returns successful `MetadataResolution.Committed`. Check stored bounds, closed state/fingerprint/receipt structure and receipt-to-ledger ticket binding before exposing a receipt; classify corrupt persisted data as sanitized `CorruptState/OperatorRecovery` for the originating operation, not caller-invalid input, success, missing state or definite non-commit. Add focused package-only persisted-receipt regressions in `tests/contracts/Hoard.Metadata.Tests/Cases/MetadataReconciliationTests.cs` or `MetadataFailureTests.cs` for malformed/structurally invalid, oversized and mismatched-ticket receipts, preserving damaged data, original-ticket ownership, committed metadata and nonduplicate aggregate effects; pair with valid original-receipt replay/reconciliation and unchanged memory semantics. Record runtime red/green evidence, replay applicable locked qualification and update affected documentation per FR-008, FR-009, FR-010, FR-013, US2/AC4, SC-003, SC-007 and T032/T036 (MP-14/15/21/22) (partial, HIGH).

Both HIGH partial findings were reproduced against fresh independently packed
SQLite binaries without application-code changes. The filtered-page probe
returns zero rows while the same damaged entry fails exact reading; the receipt
probe returns a committed success with a null target. Restoring the synthetic
payloads recovers the original page/receipt and passes schema integrity.
Fresh full locked qualification passes 66 common tests per provider and all
87 applicable entries, with nine explicit memory D exclusions; those existing
cases do not cover or waive these paths. T084/T085 and all previous task bytes
remain unchanged. Implement T086/T087 before fresh convergence/finalization.
