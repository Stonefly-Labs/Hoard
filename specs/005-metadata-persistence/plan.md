# Implementation Plan: Metadata Persistence Provider Contract

**Branch**: `feature/005-metadata-persistence` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-metadata-persistence/spec.md`

**Status**: Phase 0/1 design only. No metadata API, database, migration,
qualification adapter or acceptance command below has been implemented by this
stage. Existing specification and checklist markers are unchanged.

## Summary

Add BCL-only, opt-in metadata operations alongside the existing
`IMetadataProvider` marker. Specify bounded immutable records, typed atomic
mutations and grouped reads, conditional revisions, provider-issued operation
tickets and reconcilable receipts. Publication uses the shared authority's
artifact guard; persistence owns metadata transactions, not byte verification,
cross-store commit or physical deletion.

Prove the contract using a private, file-backed SQLite qualification adapter
and an independently implemented copy-on-write memory fixture. The same
package-only consumer runs both logical case sets. SQLite additionally proves
process-crash durability, controlled schema upgrades and verified backup/restore.
Neither fixture is the production provider from SPEC-03 or F-07 certification.

## Technical Context

**Language/Version**: Nullable-aware C# / .NET 10, repository-pinned SDK;
Python standard-library acceptance orchestration and Bash entry point.

**Primary Dependencies**: Abstractions stays BCL-only. SQLite qualification
uses private `Microsoft.Data.Sqlite` from the stable .NET 10 servicing line,
selected with an advisory/license check and pinned centrally with tracked
locks during implementation. No SQLite/EF package currently exists in
`Directory.Packages.props`. Direct parameterized SQL is sufficient; EF Core is
not mandatory and no EF migrations/tool dependency is introduced.

**Storage**: One local SQLite file on a local filesystem, WAL,
`synchronous=FULL`, foreign keys enabled on every connection; integer UTC
milliseconds and binary identity fields. Alternative fixture uses an immutable
state root and serialized copy-on-write commits, not SQLite or EF InMemory.

**Testing**: Existing xUnit and architecture tooling; new bounded metadata
tests, independently packed fixtures and a package-only consumer. A separate
child runner supports parent-controlled abrupt termination at named durable
boundaries. Existing foundation/lifecycle/configuration/discovery commands are
regression gates at implementation, not claimed execution in planning.

**Target Platform**: Single process/node on contributor macOS and Linux with
local SQLite files; qualification reports exact OS/runtime/native SQLite
version and filesystem/configuration. No network filesystem, power-loss rig,
external database, listener or cloud account is required.

**Project Type**: Additive provider-contract library and test-only qualification
packages/tools; no production persistence package or runnable cache.

**Performance Goals**: Correct finite outcomes, not throughput or a production
latency SLA. Default operation budget five seconds (allowed 1 ms to 30 seconds),
including queueing, authority acquisition, contention and commit. Limits and
late native-call uncertainty are explicit in the public contract.

**Constraints**: At most 64 mutations or read selectors, 100 rows per page,
1 MiB encoded request/result, 32 queued operations per store, and one owned
SQLite worker. Receipt retention is 24 hours; expired/unknown tickets can never
execute. Per-store operation ledger capacity 100,000, with bounded pruning.
No unbounded retries, enumeration, detached work or unsafe thread termination.

**Scale/Scope**: Five stories, 23 scenarios, 14 edge cases, all 24 FRs and eight
SCs. Forty-eight paired logical/recovery/support proof cases are defined in
[acceptance](contracts/acceptance.md). Real SQLite durable qualification is
distinct from memory semantics and production support.

## Constitution Check

*Gate evaluated before research and re-evaluated after Phase 1 design.*

| Principle / constraint | Pre-research | Post-design evidence |
| --- | --- | --- |
| I: cache/native/personal simplicity | Pass: bounded metadata foundation | Local SQLite qualification, no publishing, network client or cloud requirement |
| II: explicit versioned provider boundaries | Pass: marker remains compatible | [Public contract](contracts/metadata-api.md) adds separate interfaces; database types stay private, singleton selection uses F-02/F-03 |
| III: centralized correctness | Pass: no endpoint or cache engine | Caller canonicalization and injected shared publication authority; metadata cannot issue blob-deletion permission |
| IV: verified bounded recovery | Pass: transactions and failures are required | Atomic receipts, guarded publication, finite limits, fenced leases, [recovery contract](contracts/recovery.md) |
| V: security/isolation | Pass: no listener, no raw secrets | Typed secret references, strict upstream/header validation, scoped cursors, closed diagnostics and redacted private handles |
| VI: evidence before capability | Pass: independent implementations required | Same logical suite twice plus real SQLite crash/upgrade/backup cases; package/old-binary proof; red-before-green |
| VII: static accessible console | Not exercised: no UI | No UI/package/Node changes; future consumers use APIs, not database schemas |
| VIII: compatible reversible operation | Pass: opt-in addition | Original marker/registration binaries retained; explicit schema authorization, tested restoration, no hot swap or silent fallback |
| Workflow | Pass: correct branch, `plan / running` | One installed stage, no tasks/custom approval/product code, durable checkpoint and draft PR |

No constitutional exception, ADR change or new runtime dependency direction is
proposed. Passing design gates is not passing implementation evidence.

## Project Structure

### Documentation (this feature)

```text
specs/005-metadata-persistence/
|-- spec.md                         # Existing, unchanged
|-- checklists/requirements.md      # Existing, unchanged
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
`-- contracts/
    |-- metadata-api.md
    |-- recovery.md
    `-- acceptance.md
```

Custom reviewer-owned checklists and `tasks.md` belong to separate later stages.

### Source Code (repository root, future implementation only)

```text
src/Hoard.Abstractions/Metadata/              # BCL-only public records/interfaces
tests/contracts/Hoard.Metadata.Tests/         # Common logical suite + durable cases
tests/fixtures/metadata/Sqlite/               # Private SQL/schema/backup adapter
tests/fixtures/metadata/Memory/               # Independent copy-on-write implementation
tests/fixtures/metadata/Consumer/             # One package-only consumer
tests/fixtures/metadata/CrashRunner/          # Controlled child process, no listener
tests/fixtures/metadata/HostAdapters/         # F-02/F-03 integration outside providers
tests/architecture/Hoard.Architecture.Tests/ # Existing boundary tests extended
scripts/validate-metadata.sh                  # Future acceptance entry point
scripts/metadata_evidence.py                  # Future bounded evidence orchestrator
```

**Structure Decision**: Both provider fixtures reference Abstractions only
(SQLite additionally references its private driver); neither references the
other, Hosting, Core or Application. The host-side adapter uses existing
`IHoardModule` and owner options to initialize/admit/dispose the selected
store. Existing Core remains provider-free and no shared caching engine is
introduced. Existing declaration-only metadata fixtures remain untouched:
new operational fixtures opt in separately.

## Phase 0: Resolved Research

[research.md](research.md) records decisions, alternatives, repository evidence
and primary SQLite/Microsoft references. A bounded research agent investigated
durability, concurrency, backup, migration and driver limitations.

SQLite has one writer; its async driver APIs actually run synchronously.
The design therefore owns a bounded worker and cannot equate caller timeout
with native execution cancellation. WAL + FULL is explicitly verified, but
process-kill evidence is not power-loss/device-loss certification. EF's
abandoned migration-lock caveat reinforces explicit offline upgrade admission;
we do not add EF solely to exercise a mechanism the contract does not require.
No unresolved planning clarification remains.

## Phase 1: Design and Integration

1. Add separate metadata interfaces and closed immutable value/result records
   without adding members to existing provider markers. Reject invalid
   identities/limits rather than silently canonicalizing/truncating.
2. Reserve durable, provider-issued operation tickets before mutation.
   Apply typed mutations, final lease/revision checks, reference-edge changes
   and the committed receipt in one transaction. Resolve uncertain operations
   through the same ledger; unknown or expired tickets cannot be executed.
3. Implement bounded exact reads/pages and snapshot groups. Ordinary reads
   share no historical snapshot. Continuations are typed, query-bound and
   deterministic on unchanged data, not exports or authorization grants.
4. Obtain shared-authority artifact guards outside the database transaction
   and hold them through the publication outcome. Validate every digest/length;
   never persist raw evidence. Preserve reference generation/tombstones and
   fenced lease generations; never issue physical deletion authority.
5. Build SQLite qualification with private parameterized SQL, checked PRAGMAs,
   bounded lock acquisition, persistent receipts and schema state. Build the
   memory fixture independently with immutable-root swaps; share DTOs and tests,
   not transaction/reference/lease implementation code.
6. Supply host-side adapters only in fixtures. Existing configuration selects
   one explicit metadata authority; existing lifecycle initialization blocks
   normal use until schema admission succeeds. Disabled fixtures do not open a
   file, start a worker or run migrations. No discovery capability/support claim
   is added merely because fixture composition succeeds.
7. Drive abrupt stops with child/parent barriers, not timing sleeps or exceptions
   pretending to be crashes. Demonstrate supported v1-to-v2 upgrades and
   coherent backup restoration in isolated temporary stores.
8. Build/pack both fixtures, rerun the unchanged consumer against each selection,
   retain an old marker/registration binary, and reject SDK/schema leaks using
   the existing architecture inspector. Introduce the future commands and
   update README, provider guide and affected examples at implementation.

## Acceptance Traceability

Case IDs below refer to the normative [acceptance matrix](contracts/acceptance.md).
All are planned obligations; no case has passed in this planning stage.

| Requirements | Proof cases | Outcomes |
| --- | --- | --- |
| FR-001, FR-002, FR-003, FR-004 | MP-01..08, MP-11, MP-13 | SC-001, SC-002, SC-007 |
| FR-005, FR-006, FR-007 | MP-09..13 | SC-002, SC-003 |
| FR-008 | MP-14..18, MP-38..40 | SC-003, SC-007 |
| FR-009, FR-010 | MP-19..22, MP-37 | SC-007 |
| FR-011, FR-012, FR-013 | MP-23..27, MP-39 | SC-003, SC-004 |
| FR-014 | MP-28..30 | SC-004 |
| FR-015 | MP-07..08 | SC-007 |
| FR-016 | MP-06, MP-16, MP-31 | SC-001, SC-003 |
| FR-017, FR-018 | MP-32..36, MP-41..43 | SC-005 |
| FR-019 | MP-04, MP-22, MP-47 | SC-007, SC-008 |
| FR-020 | MP-38..43 | SC-003, SC-005 |
| FR-021 | MP-36, MP-44..45 | SC-005, SC-008 |
| FR-022 | MP-46..47 | SC-006, SC-008 |
| FR-023, FR-024 | MP-01..48, scoped by qualification class | SC-006, SC-008 |

## Review and Handoff

The required bounded `hoard-architecture-review` of the seven design artifacts
on 2026-10-21 found no confirmed violations, implementation-blocking
contradictions or unresolved design questions. Its material evidence gaps are
explicit future obligations: retained binaries/unchanged consumer, admission
and late-work ownership, ticket/reference/lease interleavings, real SQLite
crash/schema/backup recovery, and exact dependency/environment qualification.
The agent ran no commands and made no implementation/qualification claim.

Implementation evidence, custom requirements-quality review, tasks, analysis,
production qualification and schema operations remain outstanding. No extension
hooks are configured. The next separately authorized stage is `checklist`.

## Complexity Tracking

No constitutional violations require an exception. The operation ledger,
artifact guard and separate durable fixture are necessary for the specified
uncertain-commit, cross-store and real-crash guarantees; a generic repository,
public transaction/session, query language or production host is unnecessary.
