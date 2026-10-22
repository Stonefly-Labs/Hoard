# Tasks: Artifact Blob Storage Provider Contract

**Input**: Design documents from `specs/006-artifact-storage/` (F-06).
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md),
[research.md](research.md), [data-model.md](data-model.md),
[artifact API](contracts/artifact-api.md), [recovery](contracts/recovery.md),
[acceptance](contracts/acceptance.md) and [quickstart.md](quickstart.md).

**Status**: All 86 implementation tasks are verified against the final source
and retained full manifest. Default locked full qualification passed with
exactly 96 entries: 92 passes/four explicit Object AS-41..44 exclusions.
All four fresh focused modes passed without claiming qualification; all five
predecessor gates passed separately locked. Actual transfer/crash evidence,
successful and rejected composition, executed mutation negatives, architecture
findings/corrections, exact commands and task-to-file groupings are recorded in
the [final audit](plan.md#final-fixture-qualification-and-handoff-2026-10-22).
The initial local-package hash blocker is resolved; dependency graphs/versions,
external hashes and frozen historical inputs remain unchanged. These are
test-only qualified fixtures, not a production cache/provider or F-07 claim.
Convergence/finalization/merge/release are separate stages.
The reviewer-owned [storage](checklists/storage.md) and
[recovery](checklists/recovery.md) checklists are now 20/20 each.
[RQ-01](checklists/recovery.md#rq-01-finite-release-versus-non-cooperative-work)
is resolved by the [maintainer-approved clarification](spec.md#approved-follow-up-2026-10-22-rq-01-resource-ownership)
to US2 scenario 3, FR-009 and SC-006 and the separate recovery CHK012 re-review.
Finite caller-return/cleanup-attempt budgets, finite cooperative release and
bounded retained non-cooperative ownership now agree with the existing design
and required AS-39. The custom requirements-review gate is satisfied without
waivers; read-only analysis passed before implementation. Critical/high
analysis findings require separately authorized remediation and fresh analysis.
The approved clarification itself ran no driver stage and marked no task
complete; task generation was not checklist approval or remediation.

**Tests**: Explicitly required by the five story tests, FR-014/FR-025,
SC-001..SC-008 and AS-01..AS-48. Write paired successful and rejection/fault
checks first, execute the intended red assertion before the corresponding
implementation, then retain green evidence. Missing-type compilation proves
only an API gap, not runtime publication, ownership, memory or recovery safety.
Use controlled clocks/barriers, not sleeps as correctness evidence. Actual
256 MiB/4 GiB byte counts, OS peak RSS and parent-killed children cannot be
replaced by synthetic counters, sparse length, exceptions or skipped cases.

**Organization**: Setup and shared contracts/admission precede five story
phases in specification priority order, then cross-cutting acceptance. The
stories are independently testable increments of the same stores, not five
independent implementations. Their actual dependencies are explicit below.
US1 is the smallest useful verified round-trip increment, not a complete
qualification or usable cache. A subsequently authorized implementation
invocation continues through every remaining task; a successful phase,
validation checkpoint or commit/push is not a request for renewed permission.

## Format: `[ID] [P?] [Story] Description`

- Every task has a completion checkbox, sequential ID and exact
  repository-relative destination paths. Only story tasks have `[US1]`..`[US5]`.
- `[P]` identifies file-disjoint work after its listed prerequisites, not
  permission to launch agents or workflow engines. The prerequisite table is
  authoritative; numerical adjacency alone is not a dependency.
- FR/SC IDs refer to the specification; AS IDs refer to the acceptance matrix.
  Quoted model constraints are normative. Read the linked API/recovery contract
  for full state, lock-order, outcome and ownership semantics.
- Filenames group cohesive responsibilities. Reuse existing helpers; an
  equivalent grouping may be documented during implementation without
  weakening provider independence, traceability or proof requirements.

## Path Conventions

Public additions live in `src/Hoard.Abstractions/Storage/`, BCL-only. Preserve
`IArtifactProvider`, `Metadata.ArtifactDigest`, module descriptors and all
F-01/F-02/F-03/F-04/F-05 APIs. Core stays empty/provider-free; no cache engine,
production storage package, endpoint, UI, new telemetry backend or product CI
is introduced.

`tests/fixtures/artifacts/Local/` and `ObjectSemantics/` are separate, independently
packed, test-only providers referencing Abstractions only. They share public
value validation and test inputs/assertions, never staging, journal, publication,
ownership or deletion algorithms. ObjectSemantics uses disk-backed payloads,
multipart completion and conditional versioned pointers, never Local's journal
or rename. HostAdapters owns controlled shared authority, the F-05 bridge and
existing F-02/F-03 integration outside either store package.

Add `tests/contracts/Hoard.Artifacts.Tests/` to `Hoard.slnx`; fixture projects,
Consumer, CrashRunner and TransferRunner remain standalone. Use current xUnit,
architecture inspectors and Python/Bash evidence helpers. Track new/changed
locks; use lock-update mode only for intentional project/manifest or local
package-payload changes, then review the delta and replay default locked
acceptance separately. The approved unblock permits local `Hoard.*` content-hash
refreshes only, not dependency changes or rewriting frozen baseline inputs.
No new vendor/native package is planned. Existing metadata fixtures are
consumed unchanged from packages.

Private payloads, decisions, synthetic canaries, baseline binaries and proof
captures belong in a fresh owner-private workspace outside Git. Ordinary
subprocesses retain the existing ten-minute ceiling; the artifact orchestrator
explicitly permits at most 40 minutes for a measured transfer child and five
minutes for a crash child, with stricter internal operation budgets. Retain
failure evidence and stop/wait for only owned exact PIDs before scoped cleanup.
No recursive child acceptance or cleanup of an unrecognized root is permitted.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare fail-closed evidence and retained compatibility proof before
changing public contracts or behavior.

- [x] T001 [P] Create `tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj` and `ArtifactTestHarness.cs` with existing xUnit/package-consumer conventions, deterministic clocks, named barriers, bounded teardown and synthetic canaries; add only the contract test project to `Hoard.slnx` and prepare provider-neutral test drivers.
- [x] T002 [P] Write failing `tests/tooling/test_artifact_evidence.py` for missing/duplicate/foreign/stale cases, wrong durability exclusions, tampered source/lock/package/proof hashes, missing runtime red/green pairs, false byte/RSS/crash proof, failed children, unsafe destinations/cleanup and partial-mode overclaims; use synthetic evidence, never recursive acceptance.
- [x] T003 Introduce `scripts/validate-artifacts.sh` and `scripts/artifact_evidence.py` using existing foundation/lifecycle evidence helpers: prerequisites, fresh owner-private destination, bounded subprocess ownership, explicit failure retention, default locked mode, intentional `--update-locks` and `--phase logical|transfers|recovery|packages`; incomplete full inventory must fail, and every focused mode must report `qualification: false`.
- [x] T004 [P] Add `tests/fixtures/artifacts/RetainedMarker/RetainedMarker.csproj`, `Program.cs` and `Baseline/packages.lock.json` as recipes for a marker/registration consumer compiled against a recorded immutable merged pre-F-06 revision; freeze baseline source, binary and dependency hashes in the private workspace before new Abstractions code, reuse existing retained-binary tooling and never rebuild that binary against the new API (AS-46).
- [x] T005 Create standalone `tests/fixtures/artifacts/Local/Local.csproj`, `ObjectSemantics/ObjectSemantics.csproj`, `HostAdapters/HostAdapters.csproj`, `Consumer/Consumer.csproj`, `CrashRunner/CrashRunner.csproj` and `TransferRunner/TransferRunner.csproj`; keep provider references Abstractions-only, host/framework/metadata dependencies outside them, and generate/review each new `packages.lock.json` using current versions without a new vendor SDK.
- [x] T006 Extend `scripts/artifact_evidence.py` to build/freeze the retained baseline first, prepare independent current platform/fixture packages and unchanged existing metadata packages, compile package-only tests/tools and fingerprint actual sources/manifests/locks; run T002 negatives and prove unfinished full mode fails without manufacturing case results.

**Checkpoint**: Baseline provenance and incomplete, fail-closed acceptance
exist. Project creation or compilation is not storage qualification.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish additive values, closed outcomes, finite options and
minimum initialized stores/authority before story implementation.

- [x] T007 Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactValueTests.cs` and `ArtifactContractTests.cs` for every model boundary, malformed/default/foreign value, immutable defensive copy, closed outcome and redacted formatting; compare the pre-F-06 surface and pair each rejected bound with its valid counterpart.
- [x] T008 Add `src/Hoard.Abstractions/Storage/ArtifactIdentity.cs`, `ArtifactExpectations.cs` and `ArtifactEvidence.cs`: reuse existing `Metadata.ArtifactDigest`; identity length is "nonnegative signed 64-bit length, no larger than admitted maximum"; store identity has "Nonempty provider module ID (existing ID grammar, max 128 UTF-8 bytes), nonempty instance/epoch GUIDs"; stamp has "nonempty incarnation GUID"; expectations have "Optional SHA-256, exact nonnegative length, optional bounded additional checksum; required positive admitted byte cap"; evidence has "Stamp, ticket/receipt ID, bounded opaque proof handle, verified publication outcome". Handles are "at most 4 KiB"; reject oversized/malformed/foreign-store/epoch values before I/O. Checksum algorithm ID is "ASCII algorithm ID (1..16 bytes)" with "immutable expected digest bytes (1..64 bytes)"; admit only `sha512` with exactly 64 bytes, classify unknown algorithms `Unsupported` and invalid known lengths `InvalidInput`, never ignore an expectation.
- [x] T009 Add `src/Hoard.Abstractions/Storage/ArtifactOperations.cs` and `ArtifactReceipts.cs`: ticket fields are "Store epoch, provider-issued ID, operation kind, issued/expiry instants, immutable intent fingerprint" with "24-hour reconciliation lifetime"; write intent binds "Expectations and byte cap", delete intent "Exact target stamp"; staging owner binds "Ticket, process session, owner ID, positive nonwrapping generation, expiry"; staged write binds "Owner, computed identity, verified completion marker, private handle"; receipt binds "Ticket, final outcome, target stamp, logical visibility and physical-reclamation status". Resolution is the closed `Pending`, `Committed`, `NotCommitted`, `Removed`, `AlreadyAbsent` choice. Only reserve issues tickets; changed intent, unknown/expired history and foreign epoch never replay as a new operation; identical finalized logical receipts survive same-ticket retries.
- [x] T010 Add `src/Hoard.Abstractions/Storage/ArtifactReads.cs`, `ArtifactProtection.cs`, `ArtifactMaintenance.cs` and `ArtifactCapabilities.cs` for all model records: full or range reads with "nonnegative offset/positive count without overflow"; protection requests bind the described operation/mode/store/digest/exact-or-optional stamp, and grants bind "authority instance, operation ID, mode, store, digest, applicable stamp, generation and finite admission expiry". Recovery has "at most 100 observations/page", a "store/query-bound continuation (at most 4 KiB)" and cleanup "at most 100 exact abandoned staging generations or already logically removed incarnations"; observations never imply absence/authority. Capabilities are "a versioned immutable record" containing every listed guarantee, limit, verification and optional behavior; both fixtures disable range before storage I/O. Include initialization/admission/shutdown, cleanup/page reports and attributable qualification record fields from the model.
- [x] T011 Add `src/Hoard.Abstractions/Storage/ArtifactResults.cs` and `ArtifactOptions.cs` with the API's complete closed outcomes, safe phase/reason/action/correlation and explicit cleanup/uncertainty states. Encode the exact qualification limits: 8 GiB artifact cap, 16 GiB reserved staging, four transfer slots, 32 waiters, 256 KiB copy buffer, 2 MiB provider transfer buffers/transfer, control five seconds/max 30 seconds, transfer ten minutes/max 30 minutes, inactivity 30 seconds/max two minutes, cleanup five seconds/max 30 seconds, maintenance 30 seconds/max two minutes, 16 KiB decision/1 MiB page, owner TTL 30 seconds/max two minutes with ten-second renewal, 100,000 live tickets/committed identities each, 24-hour ticket lifetime; control/transfer are positive and at least 1 ms. Use checked arithmetic, original monotonic total deadlines and explicit overflow/capacity rejection, not truncated success or automatic retries.
- [x] T012 Add `src/Hoard.Abstractions/Storage/IArtifactStore.cs`, `IArtifactReadSession.cs`, `IArtifactEvidenceValidator.cs`, `IArtifactMaintenance.cs`, `IArtifactStoreLifetime.cs` and `IArtifactCoordinationAuthority.cs` (including `IArtifactProtectionGuard`) with every signature in the API inventory; retain separate lifetime/maintenance, borrowed streams and authority-owned recognition/retention. Preserve the empty marker and historical digest namespace; leak no path, SDK, Hosting/EF type, raw exception or service locator.
- [x] T013 Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactAdmissionTests.cs` and `ArtifactAuthorityTests.cs` for explicit create/reopen, use-before-admission, foreign/corrupt/incompatible roots, invalid limits, exclusive process ownership and authority wiring; test shared/exclusive fairness, opaque same-operation `RetainAsync`, independent disposal, expiry and copied/foreign/disposed guard rejection without reentrant acquisition.
- [x] T014 Implement minimum local initialization in `tests/fixtures/artifacts/Local/LocalArtifactStore.cs`, `LocalRoot.cs` and `LocalState.cs`: trusted private root, same-filesystem staging/data/decision records, exclusive OS process/session ownership, versioned checksummed bounded state and explicit create-empty/reopen-compatible; reject symlinks/escaping ancestors/cross-volume staging, preserve corrupt evidence and never auto-reset or claim future mutation cases pass.
- [x] T015 [P] Independently implement minimum initialization in `tests/fixtures/artifacts/ObjectSemantics/ObjectArtifactStore.cs` and `ObjectState.cs`: private disk-backed payloads, process-local epoch, multipart records and conditional versioned pointers; use no Local code/journal/rename and make explicit that replacement instances cannot reconcile prior epochs or claim durable restart.
- [x] T016 [P] Implement `tests/fixtures/artifacts/HostAdapters/ArtifactCoordinationAuthority.cs` and `ArtifactProtectionGuard.cs` with bounded fair shared publication/read/reference protection, exclusive deletion admission, recognized opaque retention/reference counting and current store/operation/stamp checks; retain genuinely held in-flight protection past admission expiry, make no provider/database call under provider state locks, and do not treat copied fields or an expired new grant as authority.
- [x] T017 [P] Implement `tests/fixtures/artifacts/HostAdapters/ArtifactMetadataPublicationAuthority.cs` as the existing F-05 seam adapter: bounded evidence-to-ticket/stamp encoding, selected-store validation under the same recognized shared guard and existing `MetadataCommittedArtifact(digest,length)` result; hold protection through actual metadata settlement, including late uncertainty, without publishing metadata, inspecting schemas or treating `ConfirmUnreferenced` as permission.
- [x] T018 Add provider-private fault/barrier controls in `tests/fixtures/artifacts/Local/LocalFaultControls.cs` and `ObjectSemantics/ObjectFaultControls.cs`, plus common assertion adapters in `tests/contracts/Hoard.Artifacts.Tests/ArtifactProviderDrivers.cs`; observe real state boundaries, root confinement and owned resources without sharing implementations, injecting test behavior through public contracts or turning simulated failures into crash proof.
- [x] T019 Run T007/T013 through `scripts/artifact_evidence.py` against prepared packages; retain contract/admission/authority red/green proof, baseline API preservation and finite teardown while refusing unimplemented case/qualification claims.

**Checkpoint**: Both minimum fixtures can be initialized under explicit
authority and limits. Later story gates establish mutation/read/recovery safety.

## Phase 3: User Story 1 - Publish Only Complete, Verified Artifacts (Priority: P1)

**Goal**: Publish immutable complete bytes, obtain attributable evidence and
complete protected verified reads without exposing staging or corrupt reuse.

**Independent Test**: Pause before EOF/verification, round-trip empty and
unknown-length non-seekable input, exercise every checksum/length expectation,
then race equivalent/conflicting writers and corrupt existing content.
Require complete input verification, one immutable incarnation and exact read
completion. Covers US1.1..5, AS-01..10 and FR-001..006/FR-010; full crash proof
for FR-006 remains US3.

### Tests for User Story 1

- [x] T020 [P] [US1] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactPublicationTests.cs` for AS-01..06: no prefix before EOF, exact empty/unknown-length/positive-short-read behavior, every matching/mismatching SHA-256/SHA-512/length expectation, unsupported checks/range before I/O and fully consumed submitted duplicates; expected length reached is not EOF and actual excess is rejected before append.
- [x] T021 [P] [US1] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactPublicationRaceTests.cs` and `ArtifactReadVerificationTests.cs` for AS-07..10: equivalent writers, conflicting identity/length, existing corruption and truncated/modified read versus true absence/outage; verify both streams, preserve valid content/stamp, invalidate later evidence/healthy reuse and never accept partial destination output.
- [x] T022 [P] [US1] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactEvidenceTests.cs` for attributable published/reused receipts, stale/deleted/foreign/expired evidence and recognized guard retention; require exact current stamp/direct availability, reject copied/disposed protection and prove no recursive read/metadata admission during validation (AS-02/06/10/35).

### Implementation for User Story 1

- [x] T023 [US1] Implement `tests/fixtures/artifacts/Local/LocalStaging.cs`: reserve/persist ticket intent and capacity before source reads, allocate a fenced owner, consume current-position input asynchronously through real EOF using incremental SHA-256/optional SHA-512, enforce all expectations/caps and flush verified private state; never seek/dispose caller input or expose staging.
- [x] T024 [P] [US1] Independently implement `tests/fixtures/artifacts/ObjectSemantics/ObjectStaging.cs` with private disk-backed multipart pieces, complete-stream hashes/expectations, cap reservation and fenced verified completion; no in-memory whole payload, Local staging helper or source-verification bypass for duplicates.
- [x] T025 [US1] Implement `tests/fixtures/artifacts/Local/LocalPublication.cs` and `LocalDecisions.cs`: acquire publication authority before digest gates, recheck owner, verify existing full bytes before reuse, publish only flushed immutable incarnations through bounded same-filesystem intent/decision/receipt records, preserve corrupt/conflicting content and require direct availability plus retained evidence before success.
- [x] T026 [P] [US1] Independently implement `tests/fixtures/artifacts/ObjectSemantics/ObjectPublication.cs` and `ObjectPointers.cs`: finalize immutable multipart payloads and conditionally select a versioned visible pointer without rename; resolve delayed direct visibility within the original budget or report exact-ticket uncertainty, never success from listing or shared Local logic.
- [x] T027 [US1] Implement `tests/fixtures/artifacts/Local/LocalReadSession.cs` and `LocalEvidenceValidator.cs`: protected exact-incarnation opens, one bounded full copy, final EOF/hash/length verification, explicit partial-output failure and corruption invalidation; evidence validation retains recognized protection before decision locks, checks receipt/current health/direct availability without a media scrub and never disposes borrowed destinations.
- [x] T028 [P] [US1] Independently implement `tests/fixtures/artifacts/ObjectSemantics/ObjectReadSession.cs` and `ObjectEvidenceValidator.cs` with the same public copy/evidence outcomes over immutable object payloads and conditional pointers; range/seeking/concurrent/repeated copies reject, and logical tombstones/staging are not read targets.
- [x] T029 [US1] Add `tests/fixtures/artifacts/Consumer/ArtifactConsumer.cs` and `Program.cs` as one provider-neutral package-only consumer for reserve/stage/commit/protected full read/evidence validation; select either store through injected composition, retain the same consumer source/binary for later complete qualification and do not reference concrete stores or rename semantics.
- [x] T030 [US1] Run T020..T022 and the T029 consumer through `scripts/artifact_evidence.py`; retain attributable paired AS-01..10 results for each fixture, exact input/readback and matching/conflicting receipts, with `qualification: false` and no attribution of unexecuted later cases.

**Checkpoint**: Verified publication/read MVP passes on both fixtures. This
does not qualify large transfers, crash recovery or safe physical deletion.

## Phase 4: User Story 2 - Transfer Large Artifacts Within a Fixed Resource Budget (Priority: P1)

**Goal**: Bound real transfer memory, admission and work; distinguish failures
and retain correct resource ownership across cancellation or stalls.

**Independent Test**: On each store, write/read actual 256 MiB and 4 GiB through
paced non-seekable producer/sink at fixed concurrency and buffers; verify exact
bytes/hash and <=64 MiB incremental peak process RSS. Exercise limits, deadlines,
failure classification, borrowed resources and non-cooperative work in a
controlled child. Covers US2.1..5, AS-11..20/39 and the empty-content AS-01.
Apply the approved RQ-01 distinction between finite caller-return/cleanup
attempts, finite cooperative release and bounded retained non-cooperative
ownership; retained live resources are not successful cleanup.

### Tests for User Story 2

- [x] T031 [P] [US2] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactBudgetTests.cs` for AS-13..17: declared/actual/last-chunk cap crossings, slot/queue/staging/ticket exhaustion, total/inactivity/guard/visibility deadlines, cooperative cancellation before decision and distinct full/access/unavailable failures; check original deadlines include queueing and retries.
- [x] T032 [P] [US2] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactOwnershipTests.cs` and `ArtifactNonCooperationTests.cs` for AS-18/39: borrowed stream survival, one-copy/early-close semantics, owned handle/buffer/slot/guard release after real quiescence, explicit `CloseAsync`/`DisposeAsync` incomplete-cleanup reporting and fenced late mutation; assert finite caller-return/cleanup-attempt budgets and cooperative release under approved FR-009/SC-006, and prove retained bounded ownership/not-ready for non-cooperative source/destination/native work without unsafe disposal, detached tasks or false rollback.
- [x] T033 [P] [US2] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactFailureTests.cs` and `ArtifactConfinementTests.cs` for AS-19/20/34: unexpected faults on both sides of decision, malformed/foreign-store/epoch/traversal/symlink attempts and synthetic secrets/private paths/opaque handles/raw exceptions; require sanitized actionable codes and an untouched outside sentinel, never miss/empty success or fallback.
- [x] T034 [P] [US2] Add `tests/fixtures/artifacts/TransferRunner/Program.cs`, `GeneratedSource.cs`, `HashingSink.cs` and `tests/contracts/Hoard.Artifacts.Tests/ArtifactTransferProofTests.cs`: bounded warmup/idle handshake, deterministic non-seekable generated content, independently computed expected digest, deliberately paced producer and sink, actual write/read counts 268435456 and 4294967296, fixed one-transfer profile and proof checks that reject smaller/sparse/preloaded payloads (AS-11/12).

### Implementation for User Story 2

- [x] T035 [US2] Complete `tests/fixtures/artifacts/Local/LocalTransferSupervisor.cs` and integrate `LocalStaging.cs`, `LocalPublication.cs` and `LocalReadSession.cs` with bounded slots/waiters/reservations, monotonic total/inactivity/cleanup budgets, checked counts and <=2 MiB transfer-owned buffers; exact-ticket cancellation before decision fences late commit, while a possible decision returns uncertainty and retains owned activity until settled.
- [x] T036 [P] [US2] Independently complete `tests/fixtures/artifacts/ObjectSemantics/ObjectTransferSupervisor.cs`, `ObjectStaging.cs`, `ObjectPublication.cs` and `ObjectReadSession.cs` with the same limits/ownership contract; conditional visibility probes are at most one per 50 ms within the remaining original deadline, with no hidden retry/new ticket or unbounded multipart memory.
- [x] T037 [US2] Complete shutdown/close ownership in `tests/fixtures/artifacts/Local/LocalLifetime.cs`, `LocalReadSession.cs`, `ObjectSemantics/ObjectLifetime.cs` and `ObjectReadSession.cs`: cooperative resources settle within cleanup budget, held non-cooperative activity keeps bounded handles/slots/guards, blocks admission/readiness and emits explicit incomplete cleanup; borrowed streams are never forcibly closed and expiry never revokes live read protection. Apply only the maintainer-approved RQ-01 resolution.
- [x] T038 [US2] Complete owning-boundary failure mapping and fixed safe events in `tests/fixtures/artifacts/Local/LocalFailures.cs` and `ObjectSemantics/ObjectFailures.cs`, integrating T033 confinement/fault paths; preserve known failure distinctions and after-decision uncertainty, redact public values/proof/diagnostics and never broadly catch into miss/default success.
- [x] T039 [US2] Extend `scripts/artifact_evidence.py` and `tests/tooling/test_artifact_evidence.py` with actual macOS/Linux OS peak-RSS capture plus sampled RSS, units, warmed idle baseline, exact child/runtime IDs, actual byte/hash/buffer/slot/pacing proof and 40-minute child deadline; fail absent measurement/space/child or incremental peak above 67108864 bytes, never substitute managed allocations or artificial baseline ballast.
- [x] T040 [US2] Execute T031..T033 through `scripts/artifact_evidence.py` against both stores, including an owner-controlled non-cooperative child; retain paired AS-13..20/34/39 results, actual cleanup/ownership observations and exact process exit after the negative, applying the approved RQ-01 clarification without treating retained ownership as successful release.
- [x] T041 [US2] Execute T034 via `scripts/artifact_evidence.py` in four fresh measured children (each size on each provider); retain AS-11/12 actual write/read counts, independent hash, deliberate backpressure, baseline/OS peak/sampled RSS and full-process <=64 MiB increment in every run; missing space/platform support fails, not skips, and this partial gate never qualifies the feature.

**Checkpoint**: Bounded real transfers and classified ownership/failure cases
pass under the approved cooperation profile. No crash or deletion claim follows.

## Phase 5: User Story 3 - Recover Interrupted Work Without Losing Committed Content (Priority: P1)

**Goal**: Resolve exact mutation outcomes after lost acknowledgment/process
failure, fence stale ownership and reclaim only bounded eligible abandoned work.

**Independent Test**: Reconcile lost acknowledgments/expired tickets, race
renewal and cleanup with changing pages, then kill/reopen the actual local
store at B0..B3 and compare complete acknowledged control bytes and receipts.
Compose failed metadata publication without fabricating entries or rolling
back committed blobs. Covers US3.1..5, AS-21..27/41..43; deletion crash AS-44
belongs to US4.

### Tests for User Story 3

- [x] T042 [P] [US3] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactReconciliationTests.cs` for AS-21/22: exact lost-ack receipts, idempotent same-ticket retry, changed intent conflict, no staging on decided tickets, unknown/foreign/expired ticket refusal, 24-hour retention and clock rollback that cannot revive expiry.
- [x] T043 [P] [US3] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactRecoveryTests.cs` and `ArtifactOwnerFencingTests.cs` for AS-23..25/27: equality-at-expiry, renewal/cleanup barriers, restart/replacement generations, stale append/renew/commit/abandon/cleanup, changing multi-page inventory/query-bound continuation and incomplete listings; protect active/unseen/newer work and retain late I/O ownership.
- [x] T044 [P] [US3] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactMetadataIntegrationTests.cs` for AS-26 using unchanged F-05 SQLite/memory packages and the actual selected-store bridge; failed/lost metadata publication must leave identifiable committed bytes, no fabricated entry/cross-store rollback and protection held until the real metadata outcome.
- [x] T045 [P] [US3] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactCrashProofTests.cs` for AS-41..43: actual B0/B1/B2/B3 parent-observed barrier/signal/exit, fresh-process reopen, old-owner fencing, complete control/new readback, exact-ticket receipts and no duplicate effect; reject wrong/missing barrier, graceful exit, exception proxy or borrowed object durability.

### Implementation for User Story 3

- [x] T046 [US3] Complete `tests/fixtures/artifacts/Local/LocalReconciliation.cs`, `LocalDecisions.cs` and `LocalReceipts.cs`: persist ticket/intent and finalized per-ticket publish/reuse receipts, settle unfinished authoritative decisions before new admission or replacement, preserve 24-hour history and refuse expired/foreign replay; corrupt/inconsistent state blocks rather than resets or guesses rollback.
- [x] T047 [P] [US3] Independently complete `tests/fixtures/artifacts/ObjectSemantics/ObjectReconciliation.cs` and `ObjectReceipts.cs` for exact conditional-pointer outcomes within the admitted process lifetime; changed intents/epochs reject, lost direct visibility stays uncertain and no replacement instance claims durable receipts.
- [x] T048 [US3] Implement `tests/fixtures/artifacts/Local/LocalMaintenance.cs` and `LocalOwnership.cs`: "effectiveNow < expiry", equality expired, persisted nondecreasing UTC expiry decisions plus monotonic budgets, session/generation fencing, ten-second renewal only during active original-deadline work, bounded <=100-row/target pages and repeatable exact-generation cleanup; stale listings never grant absence/eviction authority.
- [x] T049 [P] [US3] Independently implement `tests/fixtures/artifacts/ObjectSemantics/ObjectMaintenance.cs` and `ObjectOwnership.cs` with bounded process-lifetime owners, query/store-bound continuations, independently delayed listing and exact multipart-generation cleanup; never delete finalized objects, active/unseen work or new generations from an old observation.
- [x] T050 [US3] Complete private bounded state accounting in `tests/fixtures/artifacts/Local/LocalState.cs` and `ObjectSemantics/ObjectState.cs`: pending tickets/receipts/staging/reclamation consume capacity, overflow fails, unknown/corrupt decisions block admission, and receipt eviction never precedes lifetime expiry; bounded maintenance may prune only fully reclaimed tombstones with all linked decisions settled, never reuse incarnation IDs or revive old stamps.
- [x] T051 [US3] Wire explicit recovery-before-admission and safe stop/reopen into `tests/fixtures/artifacts/Local/LocalLifetime.cs`, `ObjectSemantics/ObjectLifetime.cs` and `HostAdapters/ArtifactFixtureSession.cs`; the local root fences prior sessions only after exclusive ownership, alternate replacement uses a new epoch, and unresolved/corrupt/late work prevents readiness without another lifecycle authority.
- [x] T052 [P] [US3] Implement `tests/fixtures/artifacts/CrashRunner/Program.cs` and `CrashData.cs` for independently seeded B0..B3 roots, durable known-ticket/barrier handshakes, acknowledged control artifact and exact reopen/readback/reconciliation modes; a child never recursively invokes acceptance or infers a boundary from elapsed sleep.
- [x] T053 [P] [US3] Complete `tests/fixtures/artifacts/HostAdapters/ArtifactMetadataPublicationAuthority.cs` and T044 integration drivers for actual SQLite/memory package composition with each store, including guard retention across failed/delayed metadata settlement and exact-current-evidence rejection; keep existing metadata fixtures/APIs unchanged and never hold their transaction while querying a store.
- [x] T054 [US3] Extend `scripts/artifact_evidence.py` and `tests/tooling/test_artifact_evidence.py` to drive/validate B0..B3: signal only the known owned PID after its exact handshake, confirm signal exit, reopen in a fresh process within five minutes and bind barrier/run/state hashes, receipt and full control/new digest/length; fail missing proof or copied provider evidence.
- [x] T055 [US3] Run T042..T044 through `scripts/artifact_evidence.py`; retain AS-21..27 paired results against both stores, failed-metadata composition proof for both metadata choices, bounded multi-page cleanup and exact expiry/replacement observations, with no durable or orphan-eviction overclaim.
- [x] T056 [US3] Run real B0/B1/B2/B3 local children through `scripts/artifact_evidence.py`; retain AS-41..43 exact kill/reopen/receipt/control-byte evidence, explicit object durable non-applicability and actual OS/runtime/filesystem/flush configuration, never infer power-loss/device/OS-crash/network-filesystem qualification.

**Checkpoint**: Exact lost-ack recovery, owner-safe maintenance and local
process-crash publication proof pass. Physical deletion remains US4.

## Phase 6: User Story 4 - Delete Artifacts Without Racing Readers or New References (Priority: P1)

**Goal**: Remove only an exact currently authorized incarnation, protect
admitted readers/reference publication and distinguish logical removal from
actual physical reclamation.

**Independent Test**: Barrier-race live references/readers/new publication with
exclusive deletion; recreate the digest and apply old stamps/tickets/cleanup.
Exercise lost acknowledgments, pending reclamation, foreign authority and real
local D0/D1 kills. Covers US4.1..4, AS-28..35/44.

### Tests for User Story 4

- [x] T057 [P] [US4] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactDeletionRaceTests.cs` for AS-28..30: live references deny removal, held readers finish complete bytes, exclusive deletion closes new admissions and an old zero-reference observation cannot beat new publication/reference admission; use authoritative current metadata, not a caller flag.
- [x] T058 [P] [US4] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactDeletionTests.cs` for AS-31..33: fresh incarnation after delete/recreate, stale-ticket/cleanup conflicts, exact same-ticket logical receipt, new-ticket already-absent distinction, lost acknowledgment and failed/pending physical reclamation without false freed bytes.
- [x] T059 [P] [US4] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactDeletionAuthorityTests.cs` for AS-34/35: foreign/copied/disposed guards, expired new admission, genuine held same-operation settlement beyond expiry, unavailable/missing metadata authority and foreign store/epoch/locator confinement; denial must preserve payload and outside sentinel.
- [x] T060 [P] [US4] Extend `tests/contracts/Hoard.Artifacts.Tests/ArtifactCrashProofTests.cs` with AS-44 D0/D1 proof assertions: logical tombstone prevents opens, exact removal/reclamation reconciles after signal exit, repeated cleanup is harmless and recreated content survives old deletion/cleanup.

### Implementation for User Story 4

- [x] T061 [US4] Complete `tests/fixtures/artifacts/HostAdapters/ArtifactCoordinationAuthority.cs` and `ArtifactMetadataPublicationAuthority.cs` for fair exclusive deletion: close new shared admission, drain actual readers/publications/references, obtain current authoritative zero-reference revision or exact authoritative absence under exclusion and retain protection through uncertain settlement; deny unavailable authority or composition that permits bypassing reference admission.
- [x] T062 [US4] Implement `tests/fixtures/artifacts/Local/LocalDeletion.cs`, extending `LocalDecisions.cs` and `LocalReceipts.cs` for exact-stamp reserved delete, current authority/incarnation recheck and flushed intent/tombstone/receipt before acknowledgment; return removed/already-absent/conflict/denied/uncertain distinctly and never free exclusion just because caller waiting ended.
- [x] T063 [P] [US4] Independently implement `tests/fixtures/artifacts/ObjectSemantics/ObjectDeletion.cs` and extend `ObjectPointers.cs`/`ObjectReceipts.cs` for conditional-version tombstones, exact-incarnation tickets, same logical retry receipts and deferred physical status, without rename or Local decision helpers.
- [x] T064 [US4] Complete `tests/fixtures/artifacts/Local/LocalReclamation.cs` and `LocalMaintenance.cs` for bounded exact logically-removed-incarnation cleanup, pending/confirmed reclamation reporting and safe tombstone pruning only after payload removal/settled decisions; repeated recovery cannot reopen removed bytes or delete a later incarnation.
- [x] T065 [P] [US4] Independently complete `tests/fixtures/artifacts/ObjectSemantics/ObjectReclamation.cs` and `ObjectMaintenance.cs` for equivalent bounded conditional-object reclamation, preserving finalized/new objects and current readers while reporting actual pending space rather than inferred freed bytes.
- [x] T066 [US4] Extend `tests/fixtures/artifacts/CrashRunner/Program.cs`, `CrashData.cs` and `scripts/artifact_evidence.py` for D0/D1 barriers with retained-then-reclaimed payload, actual owned signal exit, fresh reopen and delete/recreate/stale-cleanup readback; validate each subproof through `tests/tooling/test_artifact_evidence.py`.
- [x] T067 [US4] Execute T057..T059 through `scripts/artifact_evidence.py` against both stores and both F-05 metadata choices; retain paired AS-28..35 authority/reader/reference/incarnation outcomes, exact receipts and reclamation counts, with protected reads never truncated and unavailable authority never granting removal.
- [x] T068 [US4] Run actual local D0/D1 crash children through `scripts/artifact_evidence.py`; retain AS-44 tombstone/receipt/reclamation/control/new-incarnation proof and explicit alternative-provider durability exclusions, completing all six required crash barriers without borrowing logical simulation results.

**Checkpoint**: Protected deletion/recreation and local removal recovery pass.
Full interchangeable-package/report qualification remains US5.

## Phase 7: User Story 5 - Qualify Different Storage Mechanisms Honestly (Priority: P2)

**Goal**: Demonstrate the same complete logical agreement on independent
mechanisms, additive package compatibility and truthful exact qualification.

**Independent Test**: Run the unchanged consumer/common suite on explicitly
selected Local and ObjectSemantics packages; exercise independent direct/list
delays and conditional conflicts, rejected mandatory guarantees, disabled/no-I/O
and failure/readiness ownership. Inspect actual graphs and retained binaries,
then reject altered/missing/overclaimed evidence. Covers US5.1..4,
AS-36..40/45..48 and all common cases, with local-only durable attribution.

### Tests for User Story 5

- [x] T069 [P] [US5] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactCompositionTests.cs` and `ArtifactCapabilityTests.cs` for AS-36..40: actual configured singleton selection, independent multipart/direct/listing delays and conditional version races, missing mandatory capability/version/authority rejection, unsupported optional operations, disabled no-I/O and failed initialization/cleanup not-ready with explicit restart only.
- [x] T070 [P] [US5] Add failing `tests/architecture/Hoard.Architecture.Tests/ArtifactBoundaryTests.cs` plus `tests/fixtures/artifacts/BoundaryLeak/BoundaryLeak.csproj` and `LeakingArtifactContract.cs` with tracked locks: inspect actual resolved package/transitive graphs and compiled public signatures, pairing rejected SDK/provider/Hosting/raw-path/service-locator leaks and forbidden Core/consumer dependencies with allowed BCL/host-adapter counterparts; prove providers independent and ObjectSemantics not implemented via Local/rename (AS-45).
- [x] T071 [P] [US5] Write failing `tests/contracts/Hoard.Artifacts.Tests/ArtifactCompatibilityTests.cs` for AS-46: execute the frozen unrebuilt pre-F-06 marker/registration binary with current platform packages, compare old public members/digest/marker semantics and compile/run new package-only source/consumer for both selections without rebuilding the retained binary.
- [x] T072 [P] [US5] Extend failing `tests/tooling/test_artifact_evidence.py` for AS-47/48 with exact 96-entry provider/case inventory, 92 applicable passes/four object D exclusions, every required subproof, capability/config/environment attribution, safe recovery walkthrough and rejection of missing/failed/skipped/duplicate/foreign/stale/hash-altered evidence or simulation/production support overclaim.

### Implementation for User Story 5

- [x] T073 [US5] Complete `tests/fixtures/artifacts/Local/LocalCapabilities.cs` and local initialization checks with all mandatory guarantees, exact configured limits/verification policy, optional SHA-512/full-read-only support and measured local process-failure configuration; reject unknown mandatory versions/values without implying power-loss or untested filesystem support.
- [x] T074 [P] [US5] Independently complete `tests/fixtures/artifacts/ObjectSemantics/ObjectCapabilities.cs` and initialization checks with simulated no-rename conditional publication/deletion, delayed direct/list enumeration, full baseline safety/limits and explicit no-durable-restart/range claims; mandatory gaps fail rather than downgrade safety or select Local.
- [x] T075 [US5] Implement `tests/fixtures/artifacts/HostAdapters/ArtifactFixtureModule.cs` and `ArtifactFixtureRegistration.cs` using existing F-02/F-03 selection/options/lifecycle only: instantiate/initialize/recover solely when enabled/selected, no disabled directory/worker/connection, no routes, required failure blocks readiness, and owned stop retains unresolved resources; reject duplicate/missing/mismatched authority/contracts with no fallback/hot replacement or installation-only support claim.
- [x] T076 [US5] Complete the T029 package-only consumer in `tests/fixtures/artifacts/Consumer/ArtifactConsumer.cs` and `Program.cs` to exercise all common operation journeys through contracts/explicit host composition; run the same compiled consumer for each selected store with no provider-private types/branching and execute the retained binary unchanged.
- [x] T077 [US5] Extend `scripts/artifact_evidence.py` to independently pack fixtures/negative controls, collect actual assets/nuspec/public-assembly graphs for T070 and compare baseline members for T071; use existing architecture inspectors, retain source/package/hash attribution and prove provider Abstractions-only independence without weakening existing allowed/forbidden rules.
- [x] T078 [US5] Complete `scripts/artifact_evidence.py` and T072 verifier with implementation/package/version/hash, config/capability/source/lock hashes, OS/runtime/filesystem, exact command, run/provider/case/class/result/duration/proof hashes, six crash signals/receipts/readback and four actual transfer measurements; enforce all 96 entries/92 passes/four explicit object AS-41..44 exclusions, every subproof and runtime red/green evidence, sanitized public reports and false qualification for partial modes.
- [x] T079 [US5] Run T069..T072 through `scripts/artifact_evidence.py`, including actual configured selection, unchanged consumer, retained binary, independence/public-graph negatives and altered-evidence rejection; retain AS-36..40/45..48 paired applicable proof without a remote-service, production-provider or F-07 certification claim.
- [x] T080 [US5] Execute each focused mode in `scripts/validate-artifacts.sh` (`logical`, `transfers`, `recovery`, `packages`) with fresh private destinations and required rebuilt/hash-verified prerequisites; confirm passing selected cases still report `qualification: false`, missing/stale prerequisites fail and no mode borrows another run's proof.

**Checkpoint**: Independent mechanisms and package/report boundaries pass
their focused gates. Only complete current-source acceptance can qualify F-06.

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Complete honest documentation, immutable full acceptance,
regressions and architecture review before implementation handoff.

- [x] T081 Update `README.md`, `docs/DEVELOPMENT.md`, `docs/PROVIDERS.md` and `specs/006-artifact-storage/quickstart.md` for actual APIs/command availability, private roots, borrowed/partial output, limits, RQ-01's approved interpretation, evidence/recovery/reclamation steps and explicit simulation/process-crash/production exclusions; explain unaffected compatibility policy/examples/diagrams/IaC/release guides rather than rewriting planned architecture or claiming a usable cache.
- [x] T082 Run default locked full `bash scripts/validate-artifacts.sh --evidence <fresh-private-destination>` from the final intended source: restore/build, SDK format/analyzers, independent packages, same common suite/consumer, actual four size/provider measurements, all six local crash barriers, retained binary and graph/report negatives; require exact 96 entries with 92 passes/four exclusions and unchanged source/locks, fail rather than skip any missing requirement.
- [x] T083 Run existing `bash scripts/validate-foundation.sh`, `bash scripts/validate-lifecycle.sh`, `bash scripts/validate-configuration.sh`, `bash scripts/validate-discovery.sh`, `bash scripts/validate-metadata.sh`, `python3 -m unittest discover -s tests/tooling -v` and `git diff --check`; record exact results and preserve every prior contract, example and reviewer-owned approval. Preserve tracked lock dependency graphs, versions and external-package hashes; the maintainer-approved 2026-10-22 unblock permits reviewed content-hash-only refreshes for rebuilt local `Hoard.*` acceptance packages, followed by a separate default locked replay. Frozen historical baseline locks/binaries remain immutable; new project/lock additions still require review.
- [x] T084 Invoke the existing `.github/agents/hoard-architecture-review.agent.md` reviewer for the substantial F-06 contract/provider/shared-authority implementation before handoff; record findings/references in `specs/006-artifact-storage/plan.md`, correct in-scope defects with focused runtime proof and preserve opt-out compatibility, centralized reference authority and independent mechanism boundaries.
- [x] T085 Audit `specs/006-artifact-storage/contracts/acceptance.md` against the retained `scripts/artifact_evidence.py` full manifest and final source/lock fingerprints: all 25 FRs, eight SCs, 23 scenarios, 15 edge cases, 48 cases and every transfer/crash/authority subproof need actual applicable evidence. After T084 fixes, rerun affected checks and the default locked full/regression gates when source/lock drift invalidates their prior proof; never count stale results or mark failed tasks complete.
- [x] T086 Record exact implementation commands/results, safe qualification/environment/limitation evidence and architecture reference in `specs/006-artifact-storage/plan.md`, `quickstart.md`, `README.md` and `docs/DEVELOPMENT.md`; update task markers only for verified work, preserve all custom checklist markers and share coherent commits with immediate pushes. Do not begin convergence/finalize, declare backlog completion, merge, tag, publish packages or deploy as part of implementation.

## Dependencies & Execution Order

### Task Prerequisites

Every actual prerequisite is explicit, with transitive prerequisites inherited.
`None` means independently ready after the global implementation/review gates.
Writing tests includes their intended red run before dependent implementation.
File ownership and prerequisite completion both govern parallel scheduling.

| Task | Prerequisites |
| --- | --- |
| T001 | None |
| T002 | None |
| T003 | T002 |
| T004 | None |
| T005 | T001, T004 |
| T006 | T003, T004, T005 |
| T007 | T006 |
| T008 | T007 |
| T009 | T008 |
| T010 | T009 |
| T011 | T010 |
| T012 | T011 |
| T013 | T012 |
| T014 | T013 |
| T015 | T013 |
| T016 | T013 |
| T017 | T016 |
| T018 | T014, T015, T017 |
| T019 | T018 |
| T020 | T019 |
| T021 | T019 |
| T022 | T019 |
| T023 | T020, T021, T022 |
| T024 | T020, T021, T022 |
| T025 | T023 |
| T026 | T024 |
| T027 | T025 |
| T028 | T026 |
| T029 | T022, T027, T028 |
| T030 | T029 |
| T031 | T030 |
| T032 | T030 |
| T033 | T030 |
| T034 | T030 |
| T035 | T031, T032, T033 |
| T036 | T031, T032, T033 |
| T037 | T035, T036 |
| T038 | T037 |
| T039 | T034, T038 |
| T040 | T039 |
| T041 | T040 |
| T042 | T041 |
| T043 | T041 |
| T044 | T041 |
| T045 | T041 |
| T046 | T042, T043, T044, T045 |
| T047 | T042, T043, T044 |
| T048 | T046 |
| T049 | T047 |
| T050 | T048, T049 |
| T051 | T050 |
| T052 | T045, T051 |
| T053 | T044, T051 |
| T054 | T052, T053 |
| T055 | T054 |
| T056 | T055 |
| T057 | T056 |
| T058 | T056 |
| T059 | T056 |
| T060 | T056 |
| T061 | T057, T058, T059 |
| T062 | T060, T061 |
| T063 | T061 |
| T064 | T062 |
| T065 | T063 |
| T066 | T060, T064, T065 |
| T067 | T066 |
| T068 | T067 |
| T069 | T068 |
| T070 | T068 |
| T071 | T068 |
| T072 | T068 |
| T073 | T069 |
| T074 | T069 |
| T075 | T073, T074 |
| T076 | T071, T075 |
| T077 | T070, T072, T076 |
| T078 | T072, T077 |
| T079 | T078 |
| T080 | T079 |
| T081 | T080 |
| T082 | T081 |
| T083 | T082 |
| T084 | T083 |
| T085 | T084 |
| T086 | T085 |

T023/T024, T025/T026, T027/T028, T035/T036, T046/T047,
T048/T049, T062/T063, T064/T065 and T073/T074 are separate provider lanes.
Only the alternative carries `[P]` when marking both would be redundant.
T014/T015/T016 are file-disjoint after T013; T017 may follow T016 while
provider initialization proceeds. T052 crash-child work and T053 metadata
integration are likewise disjoint after T051.

All changes to `scripts/artifact_evidence.py`/its tooling tests are serialized:
T002 -> T003 -> T006 -> T019 -> T030 -> T039 -> T040 -> T041 ->
T054 -> T055 -> T056 -> T066 -> T067 -> T068 -> T072 -> T077 ->
T078 -> T079 -> T080 -> T082. Commands do not grant permission to
concurrently edit the same runner. T004/T006 freeze the baseline before
public changes T008 onward. Within each provider lane, later stories may
extend earlier staging/read/state/receipt files only after the earlier gate.
Tests marked `[P]` use distinct files (T060 extends the crash tests only after
US3 completes). New assembly/package preparation must finish before consuming
its proof; no sibling store implementation may be reused to satisfy independence.

### Phase and Story Graph

```text
Setup T001..T006
  -> Foundation T007..T019
  -> US1 T020..T030 (P1: verified publication/read MVP)
  -> US2 T031..T041 (P1: budgets/ownership/actual multi-GB RSS)
  -> US3 T042..T056 (P1: reconciliation/maintenance/B0..B3)
  -> US4 T057..T068 (P1: shared-authority deletion/D0..D1)
  -> US5 T069..T080 (P2: unchanged-consumer/package/qualification)
  -> Cross-cutting T081..T086
```

US2 requires US1's real streaming/read paths; US3 adds durable settlement and
maintenance to those bounded owned operations. US4 requires exact receipts,
incarnations and settled shared protection before physical deletion. US5
requires the earlier common behavior to demonstrate interchangeability.
These are real dependencies, not an assertion that stories can all be
implemented concurrently. Each story's focused tests run independently once
its prerequisites exist. All five stories are mandatory for complete F-06.

## Requirement and Acceptance Traceability

Ranges are inclusive. Setup/foundation and final current-source gates support
all rows but do not replace focused behavioral proof. FR-009/SC-006/AS-39
use the approved RQ-01 ownership distinction; mapping is not runtime evidence.

| Requirement | Implementation tasks | Focused proof tasks / cases |
| --- | --- | --- |
| FR-001 | T008, T023..T028 | T020/T021/T030/T033; AS-01/03/08/34 |
| FR-002 | T023..T028, T046/T048/T051 | T020/T030/T045/T056; AS-02/41 |
| FR-003 | T008, T023/T024 | T020/T031/T030/T040; AS-03..06/13 |
| FR-004 | T009/T017/T025..T029, T046/T047/T053 | T020/T022/T030/T042/T044/T055; AS-02/21/26 |
| FR-005 | T023..T028 | T020/T021/T030; AS-06..09 |
| FR-006 | T025..T028, T046/T047/T051 | T020/T021/T030/T045/T056/T069/T079; AS-02/07/10/37/42/43 |
| FR-007 | T023/T024/T027/T028/T034..T037 | T020/T031/T032/T040/T041; AS-03/11/12/15/16 |
| FR-008 | T011/T023/T024/T035..T037/T048..T050 | T031/T032/T040/T041/T043/T055; AS-11..14/16/17/24/39 |
| FR-009 | T011/T027/T028/T035..T037/T048..T051 | T031/T032/T040/T041/T043/T055; AS-11/12/14..16/18/27/39; approved RQ-01 profile |
| FR-010 | T025..T028/T038 | T021/T030; AS-09/10 |
| FR-011 | T023/T024/T027/T028/T034/T037 | T020/T032/T030/T040/T041; AS-01/03/11/12/18 |
| FR-012 | T011/T035..T039/T046/T047/T061..T065/T073..T078 | T020..T022/T031..T033/T040/T058/T059/T067/T069/T072/T079; AS-04/08/10/15/17..20/33/34/38/39/48 |
| FR-013 | T009/T025/T026/T046/T047/T062..T066 | T033/T040/T042/T055/T056/T058/T067/T068; AS-20..22/32/33/42/44 |
| FR-014 | T014/T025/T046/T048/T051/T052/T054 | T045/T056/T060/T068; AS-41..44 |
| FR-015 | T048..T052/T054/T064/T065 | T043/T055/T045/T056/T060/T068; AS-23..25/27/41/44 |
| FR-016 | T017/T029/T046/T047/T048/T049/T053 | T044/T055; AS-26 |
| FR-017 | T009/T014..T018/T035..T037/T046..T051/T061 | T013/T032/T040/T042/T043/T055/T056/T059/T067/T069/T079; AS-22/23/27/35/40/41 |
| FR-018 | T016/T017/T027/T028/T053/T061..T065 | T057/T059/T067; AS-28..30/35 |
| FR-019 | T016/T017/T027/T028/T053/T061..T066 | T057..T060/T067/T068; AS-29..31/35/44 |
| FR-020 | T009/T050/T061..T066 | T057/T058/T067/T060/T068; AS-28/31..33/44 |
| FR-021 | T008..T010/T014..T018/T038/T061..T065 | T033/T040/T059/T067; AS-19/34/35 |
| FR-022 | T012/T014..T017/T029/T073..T077 | T069..T071/T079; AS-36/40/45/46 |
| FR-023 | T010/T026/T048/T049/T073..T078 | T020/T043/T055/T069/T072/T079; AS-05/25/37/38/47 |
| FR-024 | T011/T012/T073..T078 | T020/T032/T040/T069..T072/T079/T080/T082; AS-05/37..40/46..48 |
| FR-025 | T004..T006/T014/T015/T029/T039/T052/T054/T066/T073..T078 | T041/T056/T068/T070..T072/T079/T082; AS-36/45..48 and complete applicable matrix |

| Outcome | Evidence tasks | Required observable result |
| --- | --- | --- |
| SC-001 | T020..T022/T030/T032/T040 | Exact complete digest/length; no staged prefix, mismatch/conflict/corruption success or partial-copy completion |
| SC-002 | T034/T039/T041/T082 | Actual 256 MiB and 4 GiB write/read on each provider, fixed paced profile, <=67108864-byte incremental OS peak RSS |
| SC-003 | T020/T021/T030 | One equivalent immutable incarnation; fully verified submissions; conflicting/corrupt reuse rejected without overwrite |
| SC-004 | T042/T045/T055/T056/T058/T060/T067/T068 | Exact retained outcomes across every local B0..B3/D0..D1 interruption, no duplicate effect or false rollback |
| SC-005 | T043/T055/T057..T060/T067/T068 | Stale ownership/reference/read/delete/recreate cannot remove protected/new/foreign content or truncate a reader |
| SC-006 | T031..T033/T040/T043/T055/T059/T067/T069/T072/T079 | Finite classified caller return/cleanup attempts, finite cooperative release and bounded retained non-cooperative ownership; no unsafe release, false cleanup/rollback, fallback/canary exposure/miss-shaped outage |
| SC-007 | T029/T030/T041/T055/T067/T069..T071/T076/T079/T082 | Same consumer/common assertions on independent mechanisms with actual configured selection and truthful local-only D attribution |
| SC-008 | T045/T054/T056/T060/T066/T068/T072/T078..T082/T085/T086 | All applicable attributed cases/subproofs, six reproducible crash barriers, declared configuration/limits/exclusions and honest walkthrough |

| Acceptance cases | Test/proof tasks |
| --- | --- |
| AS-01..06 | T020/T022/T030 |
| AS-07..10 | T021/T022/T030 |
| AS-11..12 | T034/T039/T041 |
| AS-13..17 | T031/T040 |
| AS-18 | T032/T040 |
| AS-19..20 | T033/T040 |
| AS-21..22 | T042/T055 |
| AS-23..25 | T043/T055 |
| AS-26 | T044/T053/T055 |
| AS-27 | T032/T043/T055 |
| AS-28..30 | T057/T067 |
| AS-31..33 | T058/T067 |
| AS-34..35 | T013/T022/T033/T040/T059/T067 |
| AS-36..38 | T069/T076/T079 |
| AS-39 | T032/T040; approved RQ-01 profile |
| AS-40 | T069/T075/T079 |
| AS-41..43 | T045/T052/T054/T056 |
| AS-44 | T060/T066/T068 |
| AS-45..46 | T004/T070/T071/T076/T077/T079 |
| AS-47..48 | T002/T072/T078..T080/T082/T085/T086 |

US1.1..5 map respectively to T020/T030, T020/T030, T020/T030,
T021/T030 and T021/T030. US2.1..5 map to T034/T041,
T031/T040, T031/T032/T040, T031/T033/T040 and T020/T030.
US3.1..5 map to T045/T056, T042/T055/T056, T045/T056,
T043/T055 and T044/T053/T055. US4.1..4 map to T057/T067,
T057/T058/T067, T058/T067 and T058/T059/T067.
US5.1..4 map to T070/T071/T076/T079, T043/T055/T069/T079,
T020/T069/T079 and T072/T078/T079/T082.

The 15 edge cases, in specification order, map to:
T020/T030; T020/T031/T040; T020/T030; T021/T030;
T031/T033/T040/T042/T055; T045/T056;
T031/T033/T040; T043/T055; T043/T055;
T044/T053/T055; T057/T058/T067;
T058/T060/T067/T068; T033/T059/T040/T067;
T043/T055/T069/T079; T021/T022/T030.

## Parallel Examples by User Story

These are scheduling examples, not instructions to launch agents.

| Ready point | File-disjoint work |
| --- | --- |
| US1 after T019 | T020 publication tests, T021 race/read-verification tests and T022 evidence tests |
| US1 after red tests | T023 Local and T024 Object staging, then each lane's T025/T026 publication and T027/T028 reads |
| US2 after T030 | T031 budgets, T032 ownership/non-cooperation, T033 failures/confinement and T034 transfer child/proof tests |
| US2 after red tests | T035 Local and T036 Object transfer supervisors; integrate shared close/failure proof only after both |
| US3 after T041 | T042 receipts, T043 recovery/fencing, T044 metadata integration and T045 crash-proof tests |
| US3 after red tests | T046 Local and T047 Object reconciliation, followed by their own T048/T049 maintenance lanes |
| US3 after T051 | T052 crash child and T053 host-side metadata bridge integration |
| US4 after T056 | T057 deletion races, T058 outcomes/incarnations, T059 authority/confinement and T060 crash-proof extension |
| US4 after T061 | T062 Local and T063 Object deletion (T062 also requires T060), then each lane's T064/T065 reclamation |
| US5 after T068 | T069 composition/capabilities, T070 architecture, T071 binary compatibility and T072 report negatives |
| US5 after T069 | T073 Local and T074 Object capability declarations/admission |

## Implementation Strategy

### MVP First

After the remaining read-only analysis gate passes, complete
setup/foundation and US1. Validate its complete verified publication/read
increment with both fixtures and the same package-only consumer. This is the
suggested MVP, not a deployment, complete F-06 support or permission to skip
actual multi-GB memory, process-crash and deletion proof.

### Incremental Delivery

Proceed US1 -> US2 -> US3 -> US4 -> US5, keeping earlier behavior green and
sharing coherent commits immediately. Validation checkpoints stay inside the
full implementation invocation; continue unless genuinely blocked. Full
qualification requires every applicable case and subproof on the final source,
not the union of stale partial runs. After all 86 tasks and checks pass, the
driver may finish implementation and schedule a separate convergence invocation.
Convergence/finalization, feature merge and the authorized post-merge source
prerelease remain separate gates.

## Notes

- Counts: setup 6, foundation 13, US1 11, US2 11, US3 15, US4 12, US5 12,
  cross-cutting 6; total 86, all initially unchecked.
- No extension hooks are configured. Original task generation changed no
  existing requirement, design, checklist marker, dependency, runtime or
  qualification. The separately approved RQ-01 follow-up now aligns the three
  specification passages and closes recovery CHK012; all 86 task markers and
  their dependency graph remain unchanged.
- RQ-01 is resolved without a waiver, not by task generation or a passing old
  suite. Actual ownership/release proof on both fixtures remains mandatory.
- Qualification is limited to the actual tested local process-crash
  environment and simulated alternative. Production filesystem SPEC-04,
  remote providers SPEC-27, generalized conformance F-07, HA, native protocol
  clients, power-loss certification, retention/GC, infrastructure and deployment
  remain outside this feature.
