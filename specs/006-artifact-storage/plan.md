# Implementation Plan: Artifact Blob Storage Provider Contract

**Branch**: `feature/006-artifact-storage` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-artifact-storage/spec.md`

**Status**: Implementation running, currently blocked on existing locked
acceptance package hashes. The design below remains the full obligation;
partial current code/evidence is distinguished in
[Implementation Evidence](#implementation-evidence). No storage qualification.

## Summary

Add separate BCL-only artifact operations alongside the existing
`IArtifactProvider` marker. Stream into private staging, verify the entire input,
conditionally publish an immutable incarnation, and return reconcilable evidence
before metadata publication. Protected full reads verify completion; deletion
requires the same injected shared authority used by reference admission.

Qualify a real local-filesystem adapter and an independently implemented
object-store-semantics fixture with no rename. One package-only consumer and the
same logical cases exercise both. Real child-process interruption proves only
the local adapter's stated process-crash durability. Neither fixture delivers
production SPEC-04/SPEC-27 providers or generalized F-07 certification.

## Technical Context

**Language/Version**: Nullable-aware C# / .NET 10 with the repository's
`global.json`; Python standard-library orchestration and a Bash entry point.

**Primary Dependencies**: BCL only for public operations and both storage
fixtures: asynchronous streams, incremental SHA-256/SHA-512, immutable records
and owned synchronization. Existing xUnit, packaging and architecture tools
remain test-only. No new vendor SDK, database or native package is planned.

**Storage**: Private local root, exclusive process ownership, same-filesystem
staging/data/decision records and checked flushes for the durable fixture.
Independent alternative uses private disk-backed object payloads, conditional
versioned pointers, multipart state and deliberately delayed visibility/listing;
it shares neither the local adapter's journal nor publication implementation.

**Testing**: Common logical tests, controlled host/reference authority, package-only
consumer, retained pre-F-06 binary, real crash child and isolated large-transfer
measurement child. Exact evidence inventory and negative/positive pairs are in
[acceptance](contracts/acceptance.md). Existing suites remain regression gates.

**Target Platform**: Single process/node, initially qualified on the exact local
macOS or Linux filesystem/runtime actually exercised. No network filesystem,
Windows durability, device loss, OS crash or power-loss claim is inferred.
No server, cloud account, container or remote object service is required.

**Project Type**: Additive library contracts plus test-only qualification
packages/tools; Core stays empty and provider-free.

**Performance Goals**: Each provider writes and reads 256 MiB and 4 GiB with
at most 64 MiB incremental peak process RSS per isolated single-transfer run,
including paced non-seekable producer/consumer behavior. No throughput SLA.

**Constraints**: Qualification profile: at most 8 GiB per artifact, 16 GiB
reserved staging, four admitted transfers, 32 waiters, 256 KiB copy buffers
and at most 2 MiB provider-owned transfer buffers per active transfer.
Control deadline defaults to five seconds/max 30 seconds; transfer deadline
ten minutes/max 30 minutes; cleanup five seconds/max 30 seconds; maintenance
30 seconds/max two minutes. These include queueing, guards and storage work.
Receipt retention 24 hours, 100,000 live tickets and 100,000 committed identities;
ownership TTL 30 seconds with renewal every ten seconds, maximum TTL two minutes.
See [limits and ownership](contracts/artifact-api.md#finite-work-and-ownership).

**Scale/Scope**: Five stories, 23 scenarios, 15 edge cases, 25 FRs/eight SCs;
40 common cases, four local durable cases and four qualification-report cases.
Large-transfer cases run on both implementations; only the local adapter
claims process-crash durability.

## Constitution Check

*Gate evaluated before Phase 0 research and re-evaluated after Phase 1 design.*

| Principle / constraint | Before research | After design |
| --- | --- | --- |
| I: cache/native/personal | Pass: storage foundation only | Local fixtures, no publishing registry, network or cloud requirement |
| II: provider composition | Pass: additive contract | Marker unchanged; BCL-only signatures; fixtures reference only Abstractions; host adapter owns F-02/F-03 wiring |
| III: centralized correctness | Pass: no endpoint/cache engine | One injected authority for metadata publication, protected reads and deletion; providers implement mechanisms, not reference policy |
| IV: verified bounded recovery | Pass: all safety outcomes mandatory | Complete input/hash checks, incarnation fencing, conditional visibility, explicit uncertainty, bounded recovery and resource ownership |
| V: security/isolation | Pass: no listener | Validated digest/opaque handles, confined owner-private roots, no raw paths/errors in results, no silent fallback |
| VI: evidence before claim | Pass: two independent mechanisms | Paired logical suite, 4 GiB/RSS checks on both, actual local crash barriers, fail-closed evidence and old-binary/package proofs |
| VII: static accessible console | Not exercised | No UI/Node/OpenAPI/management endpoint; future UI remains API-driven |
| VIII: compatibility/recovery | Pass: opt-in extension | Existing digest and metadata seam retained; honest verification/durability limits; explicit initialization/recovery, no hot swap |
| Workflow | Pass: recorded branch and running plan | One installed stage; no task generation/custom approval/runtime changes; checkpoint and draft PR |

No exception or ADR amendment is proposed. Gates are design assessments, not
executed product evidence. Non-cooperative I/O cannot be promised forced
completion: qualified streams must cooperate; unsupported late work fails closed,
retains ownership and blocks readiness rather than claiming successful cleanup.

## Project Structure

### Documentation (this feature)

```text
specs/006-artifact-storage/
|-- spec.md
|-- checklists/requirements.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
`-- contracts/
    |-- artifact-api.md
    |-- recovery.md
    `-- acceptance.md
```

Custom checklists and `tasks.md` belong to separate later stages.

### Source Code (repository root, future implementation only)

```text
src/Hoard.Abstractions/Storage/                 # Public BCL operations and values
tests/contracts/Hoard.Artifacts.Tests/         # Common suite, no product listener
tests/fixtures/artifacts/Local/                # Durable local qualification only
tests/fixtures/artifacts/ObjectSemantics/      # Independent no-rename simulation
tests/fixtures/artifacts/HostAdapters/         # Authority + existing lifecycle/config
tests/fixtures/artifacts/Consumer/             # One unchanged package-only consumer
tests/fixtures/artifacts/CrashRunner/          # Parent-controlled local crash child
tests/fixtures/artifacts/TransferRunner/       # Generated data and measured RSS
tests/architecture/Hoard.Architecture.Tests/   # Extend actual graph/API proofs
scripts/validate-artifacts.sh                  # Planned, not currently runnable
scripts/artifact_evidence.py                   # Planned bounded orchestrator
```

**Structure Decision**: Providers reference Abstractions only; neither calls
Hosting, Core, the metadata fixture or its sibling. HostAdapters references
existing Hosting/metadata contracts and supplies the shared authority. The
metadata integration proof composes the existing SQLite/memory fixtures from
their packages without changing them. The prior marker-only artifact fixture
and all old consumers remain valid. No production storage project is created.

## Phase 0: Resolved Research

[research.md](research.md) records repository evidence, official sources,
decisions and alternatives. A bounded research agent investigated .NET streaming,
flush/publication, cancellation and generic conditional-object semantics.
Portable BCL operations do not certify directory/power-loss durability or make
arbitrary custom streams preemptible. Same-process exclusion and real
process-crash proof are required; `File.Move` alone is not the conditional
publication agreement. No planning clarification remains unresolved.

## Phase 1: Design and Integration

1. Add separate interfaces, closed outcomes and validated immutable values;
   reuse the existing BCL `Metadata.ArtifactDigest` without moving/changing it.
   The namespace is historical, not a database dependency.
2. Reserve a provider-issued operation ticket before source I/O. Stage and
   verify the entire stream, then commit only a current verified staging owner.
   Successful deduplication verifies both the submitted stream and existing
   bytes; corrupt content is quarantined, never automatically overwritten.
3. Persist local mutation intent and an authoritative per-digest decision
   before acknowledgment. Reconcile after crash before reopening normal
   admission. Incarnation and ticket identity protect delete/recreate and
   lost-acknowledgment races; uncertainty never means rollback.
4. Use provider-owned protected read sessions and bounded copy-to-caller
   destinations, not raw provider streams. A full-copy success requires final
   digest/length verification. Partial output on failure is explicitly unusable.
5. Inject one shared coordination authority at host composition. Its F-05
   publication adapter validates commit evidence and holds protection through
   the actual metadata outcome; its deletion guard excludes new admissions,
   current readers and live references through logical removal.
6. Local publication uses immutable data plus same-filesystem decision records
   under exclusive root/session ownership. The independent object fixture
   finalizes multipart payloads and conditionally creates versioned pointers,
   resolving delayed direct visibility before success. Neither uses listing
   as proof of absence.
7. Exercise renewal/expiry, bounded recovery, corruption, foreign handles,
   read/reference/delete races, non-cooperative late ownership and truthful
   capabilities before claiming support. Real OS-killed children and actual
   multi-GB byte counts/RSS are mandatory, not mocked or skipped.
8. Add fail-closed packaging, retained-binary, architecture, attribution and
   regression checks. Document command availability only at implementation.
   Rollback during this stage is a normal documentation/checkpoint revert.

## Acceptance Traceability

IDs refer to the [normative matrix](contracts/acceptance.md); all are future
proof obligations. The matrix also maps every story/scenario and edge case.

| Requirements | Case IDs | Outcomes |
| --- | --- | --- |
| FR-001..006 | AS-01..10, AS-21, AS-41..44 | SC-001, SC-003, SC-004 |
| FR-007..009, FR-011 | AS-03, AS-11..18, AS-39 | SC-002, SC-006 |
| FR-010, FR-012 | AS-08..10, AS-17..20, AS-34, AS-38..39 | SC-001, SC-006 |
| FR-013..017 | AS-21..27, AS-40..44 | SC-004, SC-005, SC-008 |
| FR-018..021 | AS-28..35, AS-44 | SC-005, SC-006 |
| FR-022..025 | AS-36..40, AS-45..48 | SC-007, SC-008 |

## Review and Handoff

The required bounded `hoard-architecture-review` found one P2 contract omission:
the independent provider had no public way to recognize a guard acquired by
the metadata bridge without trusting its fields. The design now adds
authority-owned `RetainAsync`, which recognizes opaque identity and pins the
same held protection without reentering admission; AS-35 requires foreign,
copied and disposed negatives plus held-after-expiry settlement. No concrete
authority dependency or existing API change is needed.

Implementation evidence, reviewer-owned custom checklist approval, tasks,
read-only analysis and runtime acceptance remain outstanding. No extension
hooks are configured. The next scheduled stage is `checklist`, not implementation.

## Implementation Evidence

Implementation is running on the pinned feature branch. Reviewer-owned gates
are 20/20 each, the built-in gate is 16/16 and the prior read-only analysis is
clear. No checkpoint finish, convergence or qualification is recorded here.

T001..T006 setup freezes the immutable merged pre-F06 revision
`830972f24795ffaaaa18cb35138db7da59022313` **before any new public contract**.
The retained marker/registration consumer also checks the historical digest.
The private `pre-f06-20261022/retained-binaries.json` capture records 136
source hashes, nine binary/dependency hashes and the baseline archive/lock hash.
Retained binary SHA-256:
`5b745ae0860722852921cab4e6b210fa20facb59e53aa6f1f8a157060aba939d`.
Raw evidence is in the owner-private sibling evidence workspace, outside Git.

| Exact command | Result |
| --- | --- |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` | Passed; pinned directory and all required artifacts |
| `python3 -m unittest discover -s tests/tooling -p test_artifact_evidence.py -v` | Red: assertion failures retained; green: 12 passed |
| `dotnet restore tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj --force-evaluate -v quiet` | Passed; new lock generated intentionally |
| `dotnet build tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj -c Release --no-restore -v quiet` | Passed; zero warnings/errors |
| `bash scripts/validate-artifacts.sh --update-locks --evidence ../hoard-artifact-evidence/setup-update-20261022` | Expected failure after independent package build; no case execution implemented, `qualification: false` |
| `bash scripts/validate-artifacts.sh --evidence ../hoard-artifact-evidence/setup-locked-20261022` | Separate default locked replay built successfully, then expected incomplete-qualification failure; no fabricated cases |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 88 tests |

Only the artifact contract-test project joins the solution. Each store recipe
depends only on Abstractions; framework/Hosting/metadata dependencies remain in
HostAdapters. Executable scaffolds explicitly exit unsuccessfully until their
behavioral tasks are implemented. Existing metadata fixture sources and locks
are unchanged. Store behavior, transfers, crashes, consumer compatibility,
architecture review and full regression gates remain pending.

### Partial foundation and blocking regression

Partial T007..T019 work adds BCL-only values and the exact separate operation,
lifetime, evidence and maintenance interfaces. Existing public files and Core
are unchanged. Value validation has retained runtime assertion failures followed
by 13 passing checks; a missing-type compiler failure is not counted as runtime
red. The package-only suite now has 32 passing value/contract/admission/authority/
bridge checks, including an actual child-process ownership rejection and a
successful fresh-process reopen after release.

The local fixture currently initializes only private checksummed root state;
the independent object fixture only initializes a process-scoped multipart/
payload namespace, with no rename or restart claim. **All storage operation
bodies remain explicit fail-closed placeholders.** Their capability records
declare the missing mandatory guarantees, `MeetsBaseline`/readiness are false,
and no operational composition, transfer, crash or deletion result is claimed.
The metadata adapter's wiring tests use a controlled validator; they are not
AS-26 integration against working artifact stores or completed metadata entries.
T007..T019 therefore remain conservatively unchecked, as do all story tasks.

After adding public contracts, the runner copies and hash-verifies the original
unrebuilt marker and dependencies using `HOARD_ARTIFACT_RETAINED_BASELINE`.
It reconstructs existing F-05 fixture packages from immutable revision
`830972f` with their **unchanged** source and locks, then consumes those
packages with the new platform. It refuses any change to those old inputs.
Only newly introduced artifact-project locks are intentionally refreshed.

| Exact command / check | Result |
| --- | --- |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --update-locks --filter 'FullyQualifiedName~Artifact' --evidence ../hoard-artifact-evidence/unchanged-metadata-foundation-20261022` | Passed 32 tests; `qualification: false`; unchanged F-05 source/locks |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --update-locks --filter 'FullyQualifiedName~Artifact' --evidence ../hoard-artifact-evidence/blocked-foundation-update-20261022` | Passed 32 tests; current limited capabilities explicitly not ready; `qualification: false` |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --filter 'FullyQualifiedName~Artifact' --evidence ../hoard-artifact-evidence/blocked-foundation-locked-20261022` | Separate default locked replay passed 32 tests with identical source SHA-256 `91348a433517cfcdd84ce4b64a6b0026641230b425fb38c12aa153d960cb71ad`; `qualification: false` |
| `python3 -m unittest discover -s tests/tooling -p test_artifact_evidence.py -v` | Current verifier: 12 passed |
| `TMPDIR="$PWD/../hoard-artifact-evidence/tooling-final-20261022" python3 -m unittest discover -s tests/tooling -v` | All 88 passed; retained owner-private scratch and result capture |
| `dotnet format Hoard.slnx --verify-no-changes --no-restore --include src/Hoard.Abstractions/Storage tests/contracts/Hoard.Artifacts.Tests -v quiet` | Passed |
| `dotnet format "../hoard-artifact-evidence/blocked-foundation-locked-20261022/current/tests/fixtures/artifacts/$project/$project.csproj" --verify-no-changes --no-restore -v quiet` for `Local ObjectSemantics HostAdapters CrashRunner` | All four standalone fixture checks passed |
| `git diff --check` | Passed |
| Direct existing `foundation_evidence.main()` with repository root and fresh retained `foundation-preliminary-20261022` workspace, default locked mode | **Failed**: `NU1403`, changed `Hoard.Abstractions.0.1.0` content rejected by the pre-existing Protocol fixture lock |
| `python3 scripts/foundation_evidence.py "$PWD" "$PWD/../hoard-artifact-evidence/foundation-locked-blocker-20261022"` | Reproduced failure, exit 1, `NU1403`; exact output retained in `command.txt` |

The frozen `RetainedMarker.dll` also executes unchanged with the current
Abstractions/Core/Hosting assemblies copied into a separate execution directory:
`dotnet ../hoard-artifact-evidence/blocked-foundation-locked-20261022/retained-current/RetainedMarker.dll`
prints `artifact-marker-compatible`. Original and executed binary SHA-256 is
`5b745ae0860722852921cab4e6b210fa20facb59e53aa6f1f8a157060aba939d`;
`retained-current.json` records this **nonqualifying** replay. This one replay
does not complete T071's remaining consumer/API/graph proof.

The direct invocation retained `foundation-regression.txt` and the complete
failed workspace; it ran the existing locked foundation implementation, not a
replacement test or fabricated pass. No old fixture/consumer lock was changed
to hide the failure. The .NET source restore/build before the package gate
succeeded.

**Blocker requiring resolution**: the mandatory default locked regression
restores pre-existing package-only fixtures against the newly packed additive
Abstractions assembly under the existing local version `0.1.0`. Its bytes
necessarily differ from the old package, so NuGet correctly rejects the old
content hash. Completing that gate requires either explicitly approved,
content-hash-only refresh/replay of the affected pre-existing acceptance locks
(without changing dependency versions), or an approved regression-tooling
strategy that tests the current platform while preserving those locks. F-06's
T083's explicit instruction to preserve prior tracked locks, except reviewed
new project/lock additions, prevents silently choosing the
first option. Consuming unchanged F-05 packages solves F-06 preparation but does
not solve the independent foundation gate.

The checkpoint remains `implement / running`; no driver finish, architecture
review, convergence, merge or release is attempted. Resolve this gate before
counting the remaining implementation/qualification work complete.
