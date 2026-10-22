# Implementation Plan: Artifact Blob Storage Provider Contract

**Branch**: `feature/006-artifact-storage` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-artifact-storage/spec.md`

**Status**: Implementation running; the local acceptance-package hash blocker
is resolved by the approved refresh and separate locked replays below.
The design below remains the full obligation;
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

**Initial blocker (resolved below)**: the mandatory default locked regression
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

That attempt preserved `implement / running` rather than waiving the gate.
The approved follow-up below resolves the lock blocker, not the remaining
implementation/qualification obligations.

### Approved Lock Refresh and Locked Replay 2026-10-22

The maintainer authorized resolving the blocker after the content-hash-only
refresh and separate locked replay were explained. T083 now explicitly permits
reviewed hash-only changes for rebuilt local `Hoard.*` acceptance packages,
not dependency/version changes or edits to frozen historical baseline inputs.
The implementation checkpoint remains `implement / running`: T001..T006 are
complete and 80 tasks remain unchecked. This follow-up does not execute or
finish another driver stage, implement storage behavior or waive a gate.

The audit covers all **97 tracked lockfiles** against `4f78ca2`: only **142
local-package `contentHash` values in 38 lockfiles** differ. Requested/resolved
versions, dependency edges, external-package hashes and historical baseline
locks are unchanged. The original pre-F06 source archive, retained marker,
dependencies and recipe lock still match their frozen hashes; no old binary
was rebuilt. Audit and command logs are retained under the owner-private
`../hoard-artifact-evidence/lock-unblock-*` paths outside Git.

The artifact runner still builds F-05 fixtures from immutable baseline source
and locks. Its current-input comparison now allows only valid local `Hoard.*`
SHA-512 content-hash refreshes while preserving the lock graph. Changed fixture
source/project files, dependency/version changes, external hash changes and
malformed local hashes still reject. The focused regression first reproduced
the old rejection, then passed with these negative controls.

| Exact command / check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests/tooling -p test_artifact_evidence.py -v` | Initial red at approved local hash delta; green 13 passed |
| `bash scripts/validate-foundation.sh --update-locks` | Passed; intentional local hash regeneration and replay |
| `bash scripts/validate-lifecycle.sh --update-locks` | Passed |
| `bash scripts/validate-configuration.sh --update-locks` | Passed |
| `bash scripts/validate-discovery.sh --update-locks` | Passed |
| `bash scripts/validate-metadata.sh --update-locks` | Regenerated locks, then failed with generic child-command error; no full pass claimed for this attempt |
| `bash scripts/validate-foundation.sh` | Separate default locked replay passed 628 tests across five assemblies, zero failures/skips; Core/packages/hosts/architecture/compatibility/format gates passed |
| `bash scripts/validate-lifecycle.sh` | Separate default locked replay passed 504 tests, nine boundary proofs and seven package journeys |
| `bash scripts/validate-configuration.sh` | Separate default locked replay passed 201 tests, six boundary proofs, nine journeys and five interrupted-publication barriers |
| `bash scripts/validate-discovery.sh` | Separate default locked replay passed 137 tests, nine journeys and 18 actual graph scans |
| `bash scripts/validate-metadata.sh --evidence ../hoard-artifact-evidence/lock-unblock-metadata-locked-20261022` | Complete default locked replay passed: 72 logical tests per provider, four boundary tests, 96-case manifest with 87 passes/nine memory durability exclusions; recovery/retained-binary/negative proof passed |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --filter 'FullyQualifiedName~Artifact' --evidence ../hoard-artifact-evidence/lock-unblock-artifacts-locked-20261022` | Default locked focused replay passed 32 tests; `qualification: false`; original baseline reused unchanged |
| `python3 -m unittest discover -s tests/tooling -v` | All 89 passed |
| Full tracked-lock semantic audit and frozen-baseline hash verification | Passed; 38 hash-only lock deltas, no version/graph/external-hash drift; baseline intact |
| `git diff --check` | Passed |

All default locked replays preserve their lock inputs. No public API,
dependency declaration, fixture source, example source, custom checklist or
driver checkpoint changes in this follow-up. README/development/provider/test
guides and this feature's task/quickstart evidence are synchronized. Architecture
diagrams, charter/specification/ADR, compatibility policy, example guides, IaC
and release guides are unaffected because this changes acceptance fingerprints
and tooling policy, not runtime behavior, dependency boundaries or operations.
The substantial partial F-06 implementation still needs its own architecture
review and all remaining behavior/qualification tasks; this unblock is not that
review or full artifact acceptance. PR #16 stays draft; no merge, tag,
publication, deployment or infrastructure action is authorized or performed.

### Resumed Storage Mechanisms and Recovery 2026-10-22

The interrupted `implement / running` stage resumes on the recorded feature
branch without another `begin` or generator. This is **partial implementation
evidence, not feature qualification or a completed stage**. The 80 remaining
task markers stay unchecked until their complete obligations are verified;
reviewer-owned checklist markers, requirements and the driver checkpoint are
unchanged. No requirement waiver or new maintainer decision is inferred.

The independently packaged fixtures now implement private bounded disk-backed
staging, full EOF/hash/length verification, conditional immutable publication,
verified duplicate reuse, protected one-copy reads, exact-ticket receipts,
generation-fenced cleanup and exact-incarnation deletion/reclamation. Local
uses checksummed intent/decision/receipt records and same-volume publication;
ObjectSemantics independently uses multipart assembly/versioned pointers with
no Local reference, shared mutation algorithm or rename. Object state remains
process-local. Both still declare missing mandatory guarantees and not-ready;
this work does not claim completed provider capabilities or F-07 certification.

The same compiled package-only consumer performs a round trip on both choices.
The host adapter separately composes both stores with **unchanged F-05 SQLite
and memory packages**: actual failed metadata transactions leave identifiable
committed orphan bytes, current live references deny deletion, committed
reference removal permits it, stale evidence cannot recreate an entry, and
lost metadata acknowledgments retain the actual reference guard until physical
settlement. No metadata schema, provider source or existing metadata API changes.

Local crash drivers seed acknowledged independent control content, pause at
actual B0/B1/B2/B3/D0/D1 boundaries, and are killed by their exact owning parent.
Fresh processes reopen the same roots and verify original tickets, complete
control/new bytes, identical logical receipts, old-owner fencing and
delete/recreate/stale-cleanup safety. B0/B1 without decision intent remain
resumable under a new session/generation; only a recorded authoritative decision
is settled as committed or definitely not committed. This is the consistent
reading confirmed by architecture review, not a requirement amendment.
D1 first failed its intended reclamation assertion; recovery now advances
physical status from the persisted reclaimed-incarnation record.

Named architecture review `artifact-recovery-review` found no provider/metadata
dependency-boundary break and four concrete partial-mechanism defects:
concurrent copy/close admission and premature second-close success; object
cleanup reopening finalized noncommit; deadline reporting behind state locks
held during blocked I/O; and expired/altered ticket failures mapped to
uncertainty. Fixes use atomic per-session copy admission/single physical close,
terminal cleanup fencing, separate supervisor bookkeeping locks and
lock-independent exact-ticket failure classification. Focused tests also prove
bounded non-cooperative initialization/stop and synchronous native-I/O
retention. A native macOS failure was observed in concurrent
`DriveInfo.GetDrives`/`GetAllMountPoints`; local mount enumeration is serialized,
with a 16-root parallel admission regression. This partial review is not final
architecture approval or completion of T084.

Retained private runs include actual prior-code assertion failures, not just
compilation errors. `resume-review-ownership-red-20261022` contains five expected
assertion failures after correcting a test import and disabling parallel native
mount enumeration for that old-code capture; the earlier native crash/compile
failures are preserved but not counted as logical red evidence.
`resume-crash-barriers-proof-red-20261022` has five passes and the exact D1
reclamation failure. Earlier publication, integrity, deadline and reconciliation
red/green runs remain under `../hoard-artifact-evidence/resume-*`.

| Exact command / check | Result |
| --- | --- |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --update-locks --filter 'FullyQualifiedName~Artifact' --evidence ../hoard-artifact-evidence/resume-metadata-settlement-green-20261022` | Passed 109 focused tests and both unchanged-consumer choices; includes six actual C# parent-kill/reopen cases and 12 actual metadata/store composition checks; `qualification: false` |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --update-locks --phase recovery --evidence ../hoard-artifact-evidence/resume-recovery-phase-20261022` | Passed 14 owner/ticket checks plus six Python-owned SIGKILL/fresh-process journeys; independent expected hashes/counts, exact state/receipt/owner/reclamation proof; `qualification: false` |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase logical --evidence ../hoard-artifact-evidence/resume-logical-locked-20261022` | Separate default locked replay passed 103 checks and both unchanged-consumer choices; `qualification: false` |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --update-locks --phase transfers --evidence ../hoard-artifact-evidence/resume-measured-transfers-20261022` | Earlier source actually wrote/read 268435456 and 4294967296 bytes on both providers; exact independent digest/count/pacing and <=64 MiB incremental OS peak RSS passed in all four children; explicitly not final-current-source qualification |
| `python3 -m unittest discover -s tests/tooling -p test_artifact_evidence.py -v` | Passed all 14, including actual recovery-readback mutation negatives |
| `python3 -m unittest discover -s tests/tooling -v` | Passed all 90 |
| `dotnet format whitespace tests/fixtures/artifacts --folder --verify-no-changes -v quiet` and `dotnet format whitespace tests/contracts/Hoard.Artifacts.Tests --folder --verify-no-changes -v quiet` | Both passed |
| `git diff --check` | Passed |

Recovery/logical evidence at source fingerprint
`33435a0cb052ab49da3f8283bd41bea5d9ba74c186efa2a8b77c3fca2c6ece4d`
is attributable to those captures, not later source changes. Recovery run ID
`ece5f849-e445-478a-93fd-d84a68bc7043` binds all six directly owned signals and
fresh reopen processes. Original pre-F06 baseline/marker bytes remain reused,
never rebuilt against new contracts. Only reviewed artifact-local package hashes
change; dependency versions/graphs and external hashes remain fixed.

At this recovery checkpoint package mode was still unimplemented; the subsequent
package/review work below supersedes that limitation. Full mode remains
fail-closed. Outstanding work includes complete active-owner renewal/idle cases, independently controlled direct/list
visibility and unresolved-guard ownership, complete configured F-02/F-03
selection/readiness/disabled behavior, actual package/public-API graph negatives
and old binary inspection, every AS subproof, hardened exact manifest closure,
final-current-source transfer replay and full locked qualification/regression/
architecture gates. Existing focused passes do not mark these complete.

README, development/provider/test guides and quickstart now distinguish
executed partial mechanisms from those obligations. Compatibility policy,
custom-host example sources/guides, product charter/specification,
architecture/ADR/diagrams, IaC and release guides remain unaffected: dependency
directions, old marker/digest/API behavior and planned product boundaries are
preserved; no production provider, cache engine, endpoint/UI, cloud resource,
infrastructure plan/apply, deployment, tag/release/package publication or merge
is introduced. PR #16 remains draft; implementation continues without advancing
to convergence or finalization.

### Resumed Package and Review Checks 2026-10-22

The package phase now executes eight resolved-asset/nuspec/assembly graph scans
through the existing architecture inspector, including actual Local and
ObjectSemantics packages and an intentionally leaking provider/Hosting control.
It runs the original hash-verified pre-F06 marker executable with current
platform assemblies and the same compiled round-trip consumer for both stores.
Baseline copying now preserves archived package and assembly inputs rather than
dropping them with the source-copy helper's build-output exclusions.
Public member comparisons additionally check accessibility and invocation flags;
an in-memory negative pair rejects private/static replacements of a public method.
This remains focused nonqualification, not complete AS-45/46 evidence.

Architecture reviewer `artifact-review` identified six concrete defects.
Corrections restore residual committed staging reservations on reopen, settle
expired ownerless reservations in bounded admission batches, renew commit
ownership only on verified copy progress, fence/close idle read sessions, and
refuse composed shutdown while authority-owned reference work remains live.
The sixth finding prompted the public-member accessibility check above.
Focused cases cover expiry versus capacity, interrupted persisted reservation
release, commit progress crossing TTL, idle-copy rejection and composed shutdown.
The reservation-expiry red run failed both provider runtime assertions before
the correction; the first reservation-release test needed its fault count
corrected (three ticket writes, not four). Neither simulated record failure
nor idle-copy checks are represented as new actual crash/timer qualification.

| Exact command / check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests/tooling -p test_artifact_evidence.py -v` | Package-mode runtime red: expected assertion `0 != 1`; green: 15 passed |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase packages --evidence ../hoard-artifact-evidence/resume-packages-locked-20261022` | Passed eight scans, one architecture test, retained binary and both consumers; nonqualifying earlier source |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --update-locks --filter 'FullyQualifiedName~Artifact' --evidence ../hoard-artifact-evidence/resume-reviewed-all-20261022` | Passed 118 artifact checks and both consumer choices; `qualification: false` |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 91 tests |
| `dotnet format whitespace tests/fixtures/artifacts --folder --verify-no-changes -v quiet` and `dotnet format whitespace tests/contracts/Hoard.Artifacts.Tests --folder --verify-no-changes -v quiet` | Passed |
| `dotnet format whitespace tests/architecture/Hoard.Architecture.Tests --folder --include ArtifactBoundaryTests.cs --verify-no-changes -v quiet` | Passed; corrected an initial invocation that incorrectly supplied a file as a folder |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase packages --evidence ../hoard-artifact-evidence/resume-reviewed-packages-locked-20261022` | Separate locked replay passed two architecture checks, eight scans, frozen binary and both consumers; `qualification: false` |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --filter 'FullyQualifiedName~Artifact' --evidence ../hoard-artifact-evidence/resume-reviewed-focused-locked-20261022` | Separate locked replay passed all 118 checks, including crash children, plus both consumers; `qualification: false` |
| `bash scripts/validate-metadata.sh --evidence ../hoard-artifact-evidence/resume-reviewed-metadata-locked-20261022` | Passed complete unchanged F-05 96-case qualification |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --evidence ../hoard-artifact-evidence/resume-reviewed-full-gate-20261022` | Expected failure after locked prerequisites: complete provider/case execution is not implemented; `qualification: false` |

Those focused locked captures bind source fingerprint
`a83e9bc1376bd5075be52be37d8f5203293995ce2d5700964cdd5a8abddeabae`.
The five changed existing lockfiles contain only local `Hoard.*` content-hash
updates; versions/graphs/external hashes are unchanged. The new negative-control
lock is tracked separately. No remaining task or full-stage gate is inferred
from these focused passes.

A subsequent correction makes authority drain and store shutdown share one
original five-second cleanup budget rather than each receiving five seconds.
After the resulting local host-adapter hash refresh, both default locked gates
were repeated on source
`e1eed660f9c3347d14096db3437a3d4a638936ef9ff0de8f7ba71d9ae2a44163`:

| Exact command | Result |
| --- | --- |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --update-locks --filter 'FullyQualifiedName~Artifact' --evidence ../hoard-artifact-evidence/resume-budgeted-shutdown-update-20261022` | Passed 118 checks plus both consumers; nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --filter 'FullyQualifiedName~Artifact' --evidence ../hoard-artifact-evidence/resume-budgeted-shutdown-locked-20261022` | Separate default locked replay passed 118 checks plus both consumers; nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase packages --evidence ../hoard-artifact-evidence/resume-budgeted-packages-locked-20261022` | Separate default locked replay passed both architecture checks/eight scans, frozen binary and both consumers; nonqualifying |

Task markers and reviewer-owned checklists remain conservative and unchanged.
Configured lifecycle selection/readiness, comprehensive graph-negative shapes,
all acceptance subproofs and exact current-source full qualification remain
unfinished. No stage completion or final architecture approval is claimed.

### Continued Composition and Settlement Checks 2026-10-22

Configured artifact registration/module composition now uses F-02/F-03's
existing APIs. Both selections are inert until initialization, disabled invalid
options touch no root, and missing baseline guarantees block startup/readiness.
This proves fail-closed admission only; successful ready-store composition is
still outstanding. Focused input-fault controls distinguish access, capacity,
unavailability and unexpected internal failures without exposing exceptions.
An observed full transfer queue rejects before reading input and restores
capacity after actual release. Object listing and direct availability have
independent barriers, not a shared visibility shortcut.

A new lost-deletion-acknowledgment test first failed for both providers:
reconciliation still reported `Pending` after physical reclamation completed.
Receipts now refresh that physical status from the exact retired incarnation
while preserving the receipt ID, stamp and logical outcome.

Pre-decision cancellation tests first failed, and an intermediate cancellation
wrapper stranded provider state after a rejected retry. Teardown's retained-work
error masked the original subsequent-read timeout. Isolated managed-stack and
ownership observations identified the blocked state-monitor admission; those
temporary diagnostics were removed. Terminal fencing now runs in the owning
supervisor only after the worker unwinds, with exact ticket/session/owner/
generation and pre-decision checks. This also covers an already-cancelled
caller whose worker body never begins. Four focused cases prove terminal
noncommit, refused retry and a subsequent read initiated on a distinct thread.
No guard, buffer, slot or staging is released underneath live I/O.

| Exact command | Result |
| --- | --- |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --update-locks --filter 'FullyQualifiedName~Cancelled_commit_before_decision' --evidence ../hoard-artifact-evidence/resume-cancellation-settlement-20261022` | Passed four cancellation cases and both unchanged consumer choices; nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase logical --evidence ../hoard-artifact-evidence/resume-settlement-logical-locked-20261022` | Separate default locked replay passed 128 checks and both consumers; `qualification: false` |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase packages --evidence ../hoard-artifact-evidence/resume-settlement-packages-20261022` | Separate default locked replay passed two architecture checks/eight actual graphs, unchanged frozen binary and both consumers; `qualification: false` |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 91 tests |

These captures bind source
`e69798badba77fceeb72a52f16e36323c0f96429c0428aacad5a1059d3512bff`.
The intentional test manifest adds the already centrally pinned TestHost
dependency only in artifact package-acceptance mode; its new lock entry is
reviewed separately from local package content hashes. Other existing lock
changes contain only rebuilt local artifact fixture hashes; existing package
versions, dependency graphs, external hashes and frozen inputs are unchanged.
Earlier four actual large-transfer runs in
`resume-current-transfers-20261022` predate cancellation changes and are not
final-source proof. The failed/hung intermediate directory named
`resume-cancelled-publication-green-20261022` is failure evidence, not a green
claim. Full qualification remains fail-closed; the implementation stage and
unfinished task markers are not advanced by these focused checks.

The bounded follow-up reviewer `artifact-composition-review` found a further
destructive cancellation edge: an already-cancelled stale-after-renewal or
forged completion/private handle could bypass full worker validation and fence
valid current staging. Six paired-provider runtime assertions reproduced the
incorrect `NotCommitted` result before correction. Settlement now requires the
complete current owner, including expiry, and either prior full recognition
by this invocation or a currently valid, exact staged handle. The invocation
tracks its own progress renewals separately from external renewals. Two
additional tests cancel after progress renewal and preserve already-committed
content while fencing only the cancelled duplicate.

`HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --update-locks --filter 'FullyQualifiedName~ArtifactBudgetTests|FullyQualifiedName~Progressing_commit_renews_owner' --evidence ../hoard-artifact-evidence/resume-invalid-cancelled-handle-green-20261022`
passes 22 checks and both unchanged consumers on source
`066d2dcf6e5d398c2d7646c1ad8137facd08f8594cd5356820d74d4b27437193`,
still nonqualifying. The preceding 128-check locked logical capture is
historical rather than proof of this later source.

The reviewer closed that finding by source inspection. Its remaining
external-renewal evidence gap is now covered by a deterministic pre-decision
barrier: renewal changes the owner expiry after full recognition, cancellation
settles without fencing that newer owner, and its exact renewed handle still
publishes/readbacks successfully on both stores.

`HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase logical --evidence ../hoard-artifact-evidence/resume-external-renewal-logical-locked-20261022`
passes 138 checks and both consumers in a separate default locked run on source
`1f3370c7b5414b0a282e688893f3241776902d51a5ccdfab81b67213f289fbc3`.
Both artifact fixture/test folder whitespace checks and `git diff --check`
also pass. These remain focused nonqualification evidence, not stage completion.

### Controlled Interleavings and Command Ownership 2026-10-22

Equivalent writers now both reach an actual admitted-publication barrier before
either decision proceeds. A changed staged length rejects without damaging the
valid incarnation, followed by a successful valid retry/readback. Cooperative
source/sink inactivity settles with exact terminal noncommit and borrowed-stream
survival. Delayed cleanup rechecks an exact old generation after replacement
staging exists; changed inventory rejects an old continuation, while a fresh
bounded traversal visits all expected observations.

Ordinary artifact commands now start a distinct owned process session rather
than relying on immediate-child timeout cleanup. Timeout and interruption signal
only observed live exact PIDs in that session, wait for root/pipes, and confirm
settlement under one cleanup deadline. Failed settlement explicitly retains
failure evidence. An actual root/descendant timeout test confirms both stop
while a separately owned unrelated child survives. An interrupt regression
first failed its expected owned-PID assertions, then passed after cleanup was
wired before propagating the interrupt.

Compiled negative contracts now expose third-party `NuGetVersion`, `FileInfo`,
`FileStream` and `IServiceProvider` alongside the previous provider/Hosting
leaks. The existing inspector missed the raw filesystem/service-locator types
because they are BCL types; the actual package-boundary test failed before the
new artifact/Abstractions-specific restrictions. Allowed operation interfaces,
borrowed `Stream` and `ArtifactStamp` counterparts remain accepted. Hosting's
legitimate service-provider lifecycle surface is not restricted by this rule.

| Exact command / check | Result |
| --- | --- |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase logical --evidence ../hoard-artifact-evidence/resume-controlled-logical-locked-20261022` | Separate default locked replay passed 146 checks and both consumers, source `f9df022dba41f83c07ed86c38ad3c08998f349a2eb1830df4c0ac6d4208a2013`; predates the subsequent runner/boundary-only changes; nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase packages --evidence ../hoard-artifact-evidence/resume-bcl-artifact-boundary-red-20261022` | Intended compiled runtime boundary assertion failed, not compilation |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase packages --evidence ../hoard-artifact-evidence/resume-bcl-artifact-boundary-green-20261022` | Passed both architecture checks/eight actual scans, frozen marker and both consumers on source `9559be6d1f3d7a935b98d2f5232105037ec4fead8e79cd8032f17ce89f1af566`; nonqualifying |
| `python3 -m unittest discover -s tests/tooling -p test_artifact_evidence.py -k interrupted -v` | Intended runtime owned-PID assertion failed before correction |
| `python3 -m unittest discover -s tests/tooling -p test_artifact_evidence.py -v` | All 19 passed, including actual descendant timeout/unrelated-process preservation |
| `python3 -m unittest discover -s tests/tooling -v` | All 95 passed |
| `dotnet format whitespace tests/fixtures/artifacts --folder --verify-no-changes -v quiet` | Passed |
| `dotnet format whitespace tests/contracts/Hoard.Artifacts.Tests --folder --verify-no-changes -v quiet` | Passed |
| `dotnet format whitespace tests/architecture/Hoard.Architecture.Tests --folder --verify-no-changes -v quiet` | Passed |
| `git diff --check` | Passed |

The intentional fixture-hook package rebuild was separately replayed with
default locked inputs. Only local package-content hashes changed; no external
dependency, version or graph change is introduced. Original baseline/marker
inputs remain unchanged. Full-source qualification and successful readiness
remain incomplete; all partial modes retain `qualification: false`, the driver
remains `implement / running`, and custom checklists/task completion markers
are untouched. PR #16 stays draft. README/development/quickstart and task-status
notes are synchronized; product architecture/diagrams, examples, predecessor
guides, IaC and release guidance remain unaffected because their API/dependency/
operational claims do not change.

### Complete Common Consumer and Scoped Graph Checks 2026-10-22

The same compiled consumer now executes all 16 common store/read/evidence/
maintenance/authority methods for each selected package. It verifies pending
and exact committed/deletion reconciliation, same-ticket retries, verified
duplicate reuse, renewal, terminal abandonment, bounded observation, explicit
unsupported range rejection, deletion/absence/recreation, stale cleanup safety
and protected full readback. Independently retained protection remains valid
after the original reference is disposed. Explicit read close reports physical
release without closing borrowed streams; consumer sources now actually track
EOF/disposal rather than returning an unconditional `CanRead` value.

The runner rejects old roundtrip-only reports and any incomplete/duplicate/
foreign operation inventory. The first verifier regression needed both correctly
identified provider reports: an initial single-provider mock already rejected
the object mismatch, so that first pass was not red evidence. Corrected paired
reports reproduced the intended acceptance failure before the report was
strengthened.

Actual consumer IL, fields, locals and signatures are inspected independently
of Program's permitted host composition. A compiled constructor hidden behind
an `object` return type demonstrates concrete-provider rejection. The same
actual resolved negative graph, assigned the Core policy for that canary,
rejects its provider dependency; the real platform graph remains permitted.
Compiled object code has no filesystem rename calls, paired with actual Local
rename calls. Operand inspection reuses the existing slice inspector's logic;
the shared helper preserves its original method/IL diagnostics.

Full foundation acceptance initially failed because its selectors ran the new
artifact-preparation-dependent tests without artifact graphs. Foundation's three
selectors and the equivalent lifecycle selector now follow their existing
feature-owned preparation exclusions. Artifact package mode still executes
both graph-dependent artifact tests with actual prepared inputs; no generic
architecture, public-member or compatibility test is skipped.

| Exact command / check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests/tooling -p test_artifact_evidence.py -k roundtrip_only -v` | Corrected paired-provider red: expected runtime exception was not raised before report validation was strengthened |
| `bash scripts/validate-foundation.sh --phase architecture` | Intended integration red: 49 passed, the two unprepared artifact graph tests failed |
| `bash scripts/validate-foundation.sh` | Passed complete default locked acceptance: 13 artifact value/contract, nine metadata, 42 foundation, 58 architecture and 507 composition tests; graph/compatibility/format gates passed |
| `bash scripts/validate-lifecycle.sh` | Passed default locked acceptance: 504 tests, nine boundary proofs, seven package journeys, six independent fixtures and retained old binary |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase packages --evidence ../hoard-artifact-evidence/resume-sixteen-operation-consumer-20261022` | Passed all three artifact architecture tests, eight scans, frozen marker and both identical 16-operation consumer choices; `qualification: false` |
| `python3 -m unittest discover -s tests/tooling -q` | All 97 passed |
| `dotnet format whitespace tests/fixtures/artifacts/Consumer --folder --verify-no-changes -v quiet` | Passed |
| `dotnet format whitespace tests/architecture/Hoard.Architecture.Tests --folder --verify-no-changes -v quiet` | Passed |
| `git diff --check` | Passed |

Latest artifact package/consumer capture binds source
`e8ce094ebc9cf700337415cc6c1bf32bcb50172e5c9a296f5b80c0153c07f86d`.
Foundation's run predates the final standalone consumer read-close/retention
extension, which does not change its solution inputs. No lock or product API
changes occur in this checkpoint. All partial results remain nonqualifying,
both fixtures remain not-ready, and the full inventory/readiness/final review
obligations stay open. README/provider/development/quickstart guides distinguish
that boundary; planned product diagrams, old examples, IaC and release guidance
are unaffected. No driver/task/checklist completion is inferred.

### Bounded Ticket and Reclaimed History 2026-10-22

Expired tickets previously exhausted admission permanently. Actual red captures
cover both stores' write/delete reservations and Local reopen/UTC rollback.
Reservations now release expired staging independently of ticket eviction,
retire at most 100 eligible history records per batch when ticket capacity is
full, and preserve unresolved decisions and every physically active
ticket-bearing invocation, including reconciliation. Local decisions carry
expiry provenance so live committed identity survives removal of its old
ticket anchor; legacy missing provenance remains conservative.

Bounded reviewer `artifact-ticket-retirement-review` identified P1: retirement
removed the incidental lifetime bound on reclaimed-incarnation records and
removed-digest decisions/pointers. The fix independently limits each retained
index, rejects new-index growth before logical mutation, and compacts at most
100 exact expired fully reclaimed histories per reservation. Live/unresolved/
physically active dependencies block compaction. Local persists its
nondecreasing time floor before unlinking, never removes a newer incarnation,
and handles orphan reclaimed tombstones after an interrupted two-record removal.
Object retains its own operation/expiry provenance without a Local journal or
restart claim. An initial three-case runtime red reproduced new-digest budget
bypass on both stores and Local reopen failure after 105 delete/recreate cycles
at bookkeeping budget one. Those cases now pass.

Follow-up reviewer `artifact-history-bound-review` confirmed the P1 mechanism
addressed and found P2: a reconciliation admitted before another reconciliation
finalized the ticket could later overwrite that finalized commit after
delete/recreate. A paired actual runtime red reproduced Local's false
`NotCommitted` result and Object's old-payload failure. Local now rechecks
final state after taking its digest gate. Object rechecks finalized receipts
around asynchronous read-protection admission and verifies unresolved bytes
under a genuine shared guard. Reviewer `artifact-settled-reconciliation-review`
found no high-confidence defect in that narrow correction. These are scoped
source reviews, not independently rerun evidence or final feature approval.

| Exact command / check | Result |
| --- | --- |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --filter 'FullyQualifiedName~Reclaimed_identity_history_has_a_finite_budget|FullyQualifiedName~Local_reopen_preserves_committed_decisions' --evidence ../hoard-artifact-evidence/resume-retained-history-budget-red-20261022` | Intended runtime red: both new-digest budget assertions and Local reopen failed |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --filter 'FullyQualifiedName~Admitted_reconciliation_preserves_the_settled_receipt' --evidence ../hoard-artifact-evidence/resume-settled-reconciliation-red-20261022` | Intended runtime red on both providers, not compilation failures |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase logical --update-locks --evidence ../hoard-artifact-evidence/resume-settled-reconciliation-logical-update-20261022` | Passed 160 checks and both 16-operation consumers; intentional fixture hash refresh |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase logical --evidence ../hoard-artifact-evidence/resume-history-final-logical-locked-20261022` | Separate default locked replay passed 160 checks and both consumers; nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase recovery --evidence ../hoard-artifact-evidence/resume-history-final-recovery-locked-20261022` | Passed 30 recovery/reconciliation checks and all six actual SIGKILL/fresh-process barriers B0/B1/B2/B3/D0/D1; nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase packages --evidence ../hoard-artifact-evidence/resume-history-final-packages-locked-20261022` | Passed three architecture tests, eight scans, unchanged frozen marker and both consumers; nonqualifying |
| `dotnet format whitespace tests/fixtures/artifacts/Local/Local.csproj --no-restore --verify-no-changes --verbosity quiet` | Passed |
| `dotnet format whitespace tests/fixtures/artifacts/ObjectSemantics/ObjectSemantics.csproj --no-restore --verify-no-changes --verbosity quiet` | Passed |
| `dotnet format whitespace tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj --no-restore --verify-no-changes --verbosity quiet` | Passed |
| `python3 -m unittest discover -s tests/tooling -q` | All 97 passed |
| `git diff --check` | Passed |

The three locked artifact captures bind source
`ee3d0bbfd1c31c0aa676e280a8e20f842a7478295bdbf5cd4f5ef2b512c2d33c`.
Frozen marker SHA-256 remains
`5b745ae0860722852921cab4e6b210fa20facb59e53aa6f1f8a157060aba939d`.
Lock changes are reviewed local-package content hashes only; dependency
versions/graphs and external hashes remain unchanged. No task/checklist/driver
completion or capability/readiness is inferred. Final-source transfer/full
qualification and remaining task obligations stay open. README, development,
provider and quickstart guidance describes these partial mechanisms; product
architecture/diagrams, old examples, IaC and release guidance remain unaffected
because no existing public API/dependency direction, deployment or release
behavior changes.

### Qualification Failure Models and Owned Non-Cooperative Children 2026-10-22

A public-record runtime red demonstrated that Local durability could accept
simulated durable-case exclusions and simulation could omit them. The
qualification constructor now requires no exclusions for Local and exactly
AS-41..44 for simulation. All 14 public value/contract checks pass.

Six new package-only tests first failed at their actual missing child
handshake against the previous runner, then passed with its explicit
`noncooperative` mode. Each provider is exercised with a never-settling
borrowed source, borrowed destination and synchronous native deletion boundary.
The child uses one transfer slot/no waiters and never releases the stalled
worker. Two explicit parent observations verify bounded caller return,
retained physical work, intact streams, blocked admission, incomplete shutdown,
exclusive root ownership and the applicable read/delete guard. Only after the
second PID/run/provider/scenario-bound inspection does the parent terminate
that exact process and await exit before allowing root cleanup. These are
unsupported-worker containment negatives, not cooperative release or durable
crash recovery.

Private runtime red/green captures are retained under the session's
`files/f06-qualification-model-{red,green}/` and `files/f06-child-{red,green}/`.
The child reds are six actual assertion failures, not missing-type/compiler
errors; the green snapshot compiles with zero warnings/errors. The package-only
locked logical replay below independently rebuilds these source inputs.

The Abstractions payload correction required intentional hash-only updates
using each predecessor command's `--update-locks` mode and the artifact logical
update mode. An audit found exactly 107 local `Hoard.*` content-hash changes
across 46 lockfiles, with no dependency graph/version or external-hash change.
Frozen historical inputs remain unchanged.

| Exact command / check | Result |
| --- | --- |
| `bash scripts/validate-foundation.sh` | Separate default locked replay passed 14 artifact, nine metadata, 42 foundation, 58 architecture and 507 composition checks plus package/format/compatibility gates |
| `bash scripts/validate-lifecycle.sh` | Separate default locked replay passed 504 tests, nine boundary proofs, seven package journeys and retained binary |
| `bash scripts/validate-configuration.sh` | Separate default locked replay passed 201 tests, six boundary proofs, nine journeys and five actual interrupted-publication barriers |
| `bash scripts/validate-discovery.sh` | Separate default locked replay passed 137 tests, D01..D40, nine journeys, 18 actual graph scans and retained consumers |
| `bash scripts/validate-metadata.sh --evidence ../hoard-artifact-evidence/resume-model-metadata-locked-20261022` | Separate default locked replay passed unchanged F-05 full 96-case qualification |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase logical --evidence ../hoard-artifact-evidence/resume-model-child-logical-locked-20261022` | Separate default locked replay passed 167 checks, including all six owned-child cases, and both 16-operation consumers; nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase recovery --evidence ../hoard-artifact-evidence/resume-model-child-recovery-locked-20261022` | Passed 30 recovery/reconciliation checks and six actual SIGKILL/fresh-process reopen journeys B0/B1/B2/B3/D0/D1; nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase packages --evidence ../hoard-artifact-evidence/resume-model-child-packages-locked-20261022` | Passed three architecture tests, eight actual scans, frozen marker and both consumers; nonqualifying |
| `python3 -m unittest discover -s tests/tooling -q` | All 97 passed |
| `dotnet format whitespace tests/fixtures/artifacts/CrashRunner --folder --verify-no-changes --verbosity quiet` | Passed |
| `dotnet format whitespace tests/contracts/Hoard.Artifacts.Tests --folder --verify-no-changes --verbosity quiet` | Passed |
| `dotnet format whitespace src/Hoard.Abstractions/Hoard.Abstractions.csproj --no-restore --verify-no-changes --verbosity quiet` | Passed |
| `git diff --check` | Passed |

This is a partial checkpoint, not task/driver completion or feature approval.
The three artifact captures bind source
`b90fd134aacb1cc44455194cf6f4de859a7a9e7e4f138fa792b4a6fed262c1e0`.
Both fixtures remain not-ready and full mode remains fail-closed. README,
development/provider/test guides and quickstart describe that distinction.
Existing product architecture/diagrams, examples, IaC and release guidance
remain unaffected: no production provider, dependency-direction, deployment
or release behavior changes.

### Bounded Candidate Traversal and Incremental Dependencies 2026-10-22

The prior history correction bounded removals but still scanned whole tables
and rebuilt a protected-ticket set. Seven actual runtime reds now demonstrate
the distinction with more than 100 entirely ineligible ticket, dependency,
decision and reclamation candidates. The new independent mechanisms examine
at most 100 tickets and 100 candidates per retained-history index per call,
while preserving the shared limit of 100 history retirements.

Rotating candidates resume after skipped entries and faults. Incremental
exact-incarnation dependency memberships retain every unexpired, unresolved or
physically active ticket; an expired settled ticket may release its dependency
without evicting its classification record. Local tracks existing in-memory
ticket mutation even when persistence fails and rebuilds all indexes from
validated bounded records during reopen. Exact list-node membership prevents
stale candidate accumulation when Local removes a linked decision out of order;
the independent object pointer queue removes only through its own cursor.
All index sizes remain proportional to their finite ticket/history tables.

Paired progress checks reach beyond the first 100 entries and revisit the
exact candidate whose injected fault interrupted a page. Existing physical
ticket-user, finalized-receipt, small-budget history and 105-cycle Local
reopen/rollback checks remain in the full logical run. Bounded reviewer
`artifact-candidate-page-review` found no concrete high-confidence issue in
the new indexes/mutation/recovery paths; it did not run acceptance or obtain
an independent Git diff, and is not final feature architecture approval.

| Exact command / check | Result |
| --- | --- |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --update-locks --filter 'FullyQualifiedName~History_maintenance_bounds_examined_candidates' --evidence ../hoard-artifact-evidence/resume-history-candidate-pages-red-20261022` | Seven intended runtime assertion failures against instrumented whole-table selection; no compiler failure |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase logical --update-locks --evidence ../hoard-artifact-evidence/resume-history-cursor-pages-update-20261022` | Passed 176 checks and both identical 16-operation consumers; reviewed local-package hash update |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase logical --evidence ../hoard-artifact-evidence/resume-history-cursor-pages-locked-20261022` | Separate default locked replay passed 176 checks and both consumers; nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase recovery --evidence ../hoard-artifact-evidence/resume-history-cursor-recovery-locked-20261022` | Passed 30 checks and all six actual SIGKILL/fresh-process B0/B1/B2/B3/D0/D1 journeys; nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --phase packages --evidence ../hoard-artifact-evidence/resume-history-cursor-packages-locked-20261022` | Passed three architecture tests, eight actual graphs, unchanged marker and both consumers; nonqualifying |
| `dotnet format whitespace tests/fixtures/artifacts/Local --folder --verify-no-changes --verbosity quiet` | Passed |
| `dotnet format whitespace tests/fixtures/artifacts/ObjectSemantics --folder --verify-no-changes --verbosity quiet` | Passed |
| `dotnet format whitespace tests/contracts/Hoard.Artifacts.Tests --folder --verify-no-changes --verbosity quiet` | Passed |
| `python3 -m unittest discover -s tests/tooling -q` | All 97 passed |
| `git diff --check` | Passed |

All three locked captures bind source
`f0b15db95186963a2e9b21c7c74a624f18e50b4d7b7b4be4d33489f2a8a74112`.
Only 15 local `Hoard.*` hashes in six locks change; versions, dependency graphs,
external hashes and frozen baselines remain unchanged. The immediately prior
checkpoint's five full locked predecessor gates remain applicable: only
artifact fixture/runtime-test inputs change here. README/development/provider/
test/quickstart guides now explain finite candidate pages; old examples,
product diagrams, IaC and release behavior are unaffected. Capability/readiness,
full attributable qualification, final-source transfers and remaining task
obligations stay open; no task/checklist/driver completion is inferred.
