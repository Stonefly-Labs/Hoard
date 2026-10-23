# Implementation Plan: Provider Conformance, Compatibility and Composition

**Branch**: `feature/007-provider-conformance` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-provider-conformance/spec.md`

**Status**: The authorized implementation continues `implement / running`, with
the resolved CP-11 timing clarification recorded below. No completed harness, shared
assertion extraction, five-profile workflow, custom checklist approval or qualification
result is delivered. Public product contracts and required outcomes remain
unchanged; necessary fixture-private controls are extended as recorded below.

## Foundation continuation

The maintainer's subsequent instruction to make decisions and keep implementing
resolves the earlier pause. Necessary fixture-private controls are being
implemented rather than weakening assertions. Memory now stores bounded private
record/receipt encodings within its independent immutable copy-on-write state,
validates corruption through real public read/reconcile/replay paths, and
exposes bounded targeted capture/replacement controls. No SDK dependency,
private state type, SQLite delegation, public operation signature change or
provider-returned pass flag was introduced. The package-only tests exercised
five record shapes and fourteen receipt/ledger shapes, original-ticket
classification, unchanged damaged state, independent effects and restoration.
Nine SDK/package checks passed after a separate fresh-cache locked restore.
T003's fixture-private seam wording is updated to reflect this necessary
implementation decision; mandatory outcomes and reviewer-owned markers remain.

Witness ingestion now requires expected binding/matrix dimensions. Two
dimension-only mutations were observed failing before the fix and pass after
rejection was added. Baseline verification recomputes all six sealed source,
recipe, lock, binary and package inventories/hashes before reuse, including the
distinct F-06 artifact feed. The original private preparation seal verified
unchanged; it remains non-qualifying.

Initial executor corrections guard post-spawn registration, constrain inherited
environment, propagate termination control deadlines and perform synthetic
cleanup in an identity-checked, bounded helper before marking release.
Linux x64/arm64 child bootstraps install inherited kernel filters that prevent
session/group and namespace escapes before executing a test program.
The controller requires a two-way startup handshake: the target remains blocked
until identity/ledger registration and kernel PID-handle group signalling
admission succeed. Group termination uses the stable kernel handle, not a
numeric PID that could be reused. Linux identity also records kernel start ticks
rather than second-resolution `ps` start times. The group-handle prerequisite
requires Linux 6.9 or later support and is probed, not inferred from a version
label. Native regressions
must run without skips on Linux; macOS cannot provide the required generic
containment and therefore returns `PrerequisiteMissing`, not a qualified result
or case exclusion. Existing predecessor tooling is unaffected by this admission
restriction. A least-privilege Ubuntu foundation workflow runs sanitized
non-qualifying regressions; it is not the planned five-profile baseline.

The historical checkpoint and unresolved review inventory below explain the
earlier pause. Native foundation run
[39901637391](https://github.com/Stonefly-Labs/Hoard/actions/runs/39901637391)
passed 23 checks without skips and measured 92,112,142,336 free scratch bytes.
Subsequent run
[39904414231](https://github.com/Stonefly-Labs/Hoard/actions/runs/39904414231)
observed exactly the two intended missing-handle admission failures before
the handshake/handle correction. The repair passed 26 native checks without
skips in
[39906330789](https://github.com/Stonefly-Labs/Hoard/actions/runs/39906330789).
The next native challenge,
[39906992231](https://github.com/Stonefly-Labs/Hoard/actions/runs/39906992231),
failed exactly the diagnostic-parent directory replacement case. Its correction
anchors ledger/diagnostic/cleanup operations to verified directory descriptors
and records original child-directory device/inode identities. Same-name directory
replacement is rejected before child launch; cleanup depth and entries are
bounded. The correction passed 28 native checks without skips in
[39908082714](https://github.com/Stonefly-Labs/Hoard/actions/runs/39908082714).
Earlier retained private
ledgers lack these directory identities and are not admitted for ordinary
resume/cleanup under the new format.
The unchanged inherited metadata suite also passed 72 tests against candidate
Memory bytes; this is a focused regression, not category qualification.
Subsequent repairs remain subject to full challenge coverage and final
architecture review before qualification.

### Current SDK/evidence checkpoint and timing clarification

The test-only SDK now includes a native identity-pinned resource allocator,
validated cleanup/fault observations and a real bounded VSTest logger with
private input/owner manifests and hashed runtime proofs. SDK settlement never
deletes resources or reports authoritative `Released`. Complete controller
ingestion and actual loaded-provider proofs are not yet implemented.
Strict model admission binds input/package/binding/baseline/runtime inventories,
actual execution UUIDs, append-only attempts, exact dimensions and monotonic
attempt/witness intervals. Finite VSTest scaffolding is projected without raw
console/TRX persistence. Composition and version fixtures use existing Hosting
validation; they are focused foundations, not complete profile coverage.

Observed checks: 141 portable tooling tests discovered (132 passed, nine native
skips on macOS); 39 source SDK tests passed; 41 tests passed against freshly
packed SDK/logger packages after independent fresh-cache locked replay.
Package-only logger smoke locks also replayed and built. The focused new
composition/version suites passed 142 tests. A broad direct integration run
passed 646 and failed five preparation-dependent evidence checks: required
foundation/configuration/discovery inputs were absent. No complete predecessor
acceptance is claimed. Formatting/catalog checks passed. A bounded SDK/logger
architecture review reported no confirmed architectural violations, with Linux
allocator execution and loaded-provider proof integration still unproven;
it is not final T081 review.

**Resolved under autonomous-continuation direction:** CP-11 and FR-007 formerly
required actual route conflicts to reject before provider construction, while the existing
Hosting contract learns routes only through constructed modules' `MapEndpoints`.
The actual `AmbiguousRoute` check therefore runs at route composition, before
publication/readiness. Owner-scoped endpoint responsibility IDs do not encode
routes; malformed/duplicate-ID tests are not CP-11 proof and are labelled
`endpoint-declaration` instead. Preconstructing modules just to inspect their
routes would itself violate the requested boundary.

The maintainer directed continued autonomous resolution rather than another
pause. Preserve existing public APIs and explicitly correct CP-11/FR-007/US2.2/
QC-14/T042 to the actual mapping boundary before publication, initialization,
readiness and admission. The real ambiguity/repair test observes that boundary;
it never claims zero construction or substitutes malformed IDs for routes.
Public product behavior is unchanged; no route-declaration redesign was added.
Reviewer-owned CHK014 text/markers remain untouched and are not self-approved.
Complete profile evidence remains required before task completion.

### Runtime ingestion and native SDK diagnostic increment

T001/T006 are complete: the frozen pre-extraction inventory includes all six
historical revisions, and strict model tests exercise required fields and
unknown extensions across every data-model entity as well as bounds, immutable
expectations, status/schema and relationship mutations. No runtime pass is
imported from that inventory.

`ingest_runtime_attempt` now validates actual safe-logger JSONL, proof and
completion bytes against immutable run inputs, trusted manifest/owner hashes,
independent expected identities/dimensions and parent monotonic intervals.
Assertion, unknown, skipped and interrupted outcomes remain distinct; completion
counts/flags cannot replace missing observations. Actual loaded-provider proof
and complete profile orchestration remain outstanding.

Proof traversal rejects symlinked roots/ancestors and special files, is anchored
to directory descriptors, and enforces finite file/byte/depth/time bounds.
A native SDK diagnostic workflow now prepares/seals/verifies all six baselines
before compiling candidates, explicitly labels isolated local-archive lock
preparation, independently replays locks and exercises fixed SDK/logger cases.
Its result is pending real Linux execution; unit mocks or portable passes do
not establish that evidence. All diagnostics remain `qualification: false`.

Linux historical locked restoration subsequently exposed different compiled
archive bytes from the macOS-prepared pins. A build-runtime pin did not change
those fingerprints. Explicit historical preparation now creates alternate
private locks, preserving every original source lock, dependency/version and
third-party hash. Private seal schema `2` records the recipe/actual archive
derivation; strict old schema-`1` seals remain supported unchanged. Public
evidence schema/catalog versions do not change. Independent verification
recomputes each derivation rather than accepting rehashed graph changes.
This is preparation before candidate compilation, not baseline substitution
during execution; native acceptance remains pending.

## Partial implementation checkpoint

The driver remains **`implement / running`**. Authorization to start was explicit;
the 40 custom checklist markers remain reviewer-owned and unchecked. All 86
tasks originally started unchecked; T002..T005 manifest/solution setup is now
verified complete. Remaining markers await their full acceptance obligations:
scaffolding and focused successes do not establish complete task acceptance.
No `finish` or convergence ran.

Delivered foundations comprise the source-derived frozen inventory/generator,
SDK and fixture manifests, typed binding/session/resource/diagnostic/witness
contracts, an independently expanded catalog, strict Python evidence entities,
source snapshots, initial witness admission, owned execution and historical
baseline preparation. The solution registers SDK unit tests normally and
excludes package-only fixture projects from default builds. Production
reference edges and production provider contracts are unchanged. Common consumers,
adapters, the conformance CLI/evaluator/reports, complete compatibility/composition
profiles, contributor example and five-profile CI are not delivered.

Historical preparation completed locally before candidate package builds:
the sealed proof SHA-256 was
`a725a20dcbb635944f64fed007205d06de532ca7f2b4f87c104ac4434ffa8215`.
This is **preparation, `qualification: false`**, not imported passing evidence.
The private seal and retained source/binary/feed/cache resources are outside Git.
The F-06 artifact recipe intentionally retains pre-F-06 metadata packages in
its own feed/cache, separate from F-06 metadata acceptance. Baseline integrity
and safe reuse must be verified before candidate execution; do not rebuild or
substitute retained binaries.

An early, bounded `hoard-architecture-review` identified these unresolved
foundation findings. This does not satisfy the final T081 review gate.

| Severity | Surface | Required correction |
| --- | --- | --- |
| High | `scripts/conformance_execution.py` descendant tracking | Account for children leaving the original session/group; retain ownership when actual settlement cannot be established. Add a detached-descendant regression. |
| High | Executor post-`Popen` registration | Guard identity/ledger registration immediately after spawn and contain or retain the child on registration failure. Add injected-failure regressions. |
| Medium | Executor termination/release | Propagate finite deadlines through control calls and destructive cleanup; never persist `Released` before successful deletion or equate timeout with settlement. |
| Medium | `scripts/conformance_evidence.py` witness admission | Compare expected binding and matrix dimensions, not only names/input/package/assembly hashes. Add dimension-only mutation cases. |
| Medium | SDK metadata fault interfaces | Express typed targeted record/receipt faults, scoped restoration and opaque before/after fingerprints while keeping assertions in common consumers and private storage access in adapters. |

**Historical decision at the earlier checkpoint:** T003 required unchanged provider
implementations, but Memory exposes neither targeted receipt mutation nor
opaque observations of its private `MemoryState`/operation ledger.
`MemoryFaultControls.CorruptRecordForTestAsync` sets global `Schema = 4`; it
cannot preserve the existing receipt-corruption assertions that independently
read unchanged aggregates and corroborate unchanged damaged ledger fields.
A binding alone cannot add those controls without private access or fabricated
behavior. The recommended resolution is authorization for a narrowly scoped
test-only seam inside the Memory fixture assembly, with no SDK dependency or
private types exposed. The maintainer was unavailable to answer that request,
so no provider edits, applicability waivers or assertion reductions were made.

Focused checks observed before this checkpoint: all 121 Python tooling tests
and six SDK binding tests passed; frozen inventory/catalog comparisons and
SDK/test formatting checks passed. These do **not** cover the review findings
or establish complete model/execution/evidence correctness. Full predecessor
acceptance, independent locked package replay, actual large transfers/recovery,
clean contributor execution and local/CI conformance qualification remain
unrun. Resume with the scope decision, repair the foundation findings and
complete all remaining tasks before finishing this stage.

README, development/provider guidance and this quickstart reflect the partial
state. Custom-host examples, product charter/specification, architecture/ADR/
diagrams, predecessor artifacts, governance, release/IaC/UI guidance remain
unchanged because no supported product API, provider implementation,
production graph or operational procedure changed.

## Summary

Extract reusable, test-only category suites from the existing package-acceptance
tests, keeping their assertions and independent implementations. A separately
packable `Hoard.Testing.Conformance` library supplies the common consumers,
binding contracts and fixed case catalog; provider-specific adapters supply only
construction, controlled faults and owned-resource observations. No platform
library depends on the test kit.

Add one bounded orchestrator that verifies exact runtime witnesses, package
bytes, configuration, capabilities and environment before deriving a result.
Retain F-05/F-06 logical and real local recovery obligations, F-01 compatibility/
architecture policy and F-02/F-03 lifecycle enforcement. A finite fixture-host
and version matrix, contributor good/faulty examples and narrowly scoped CI
use the same inventory and acceptance evaluator locally and automatically.

## Technical Context

**Language/Version**: Nullable-aware C#/.NET 10 under the existing `global.json`;
Python 3 standard library for evidence evaluation/orchestration; Bash entry point.

**Primary Dependencies**: Reuse centrally pinned xUnit, Microsoft.NET.Test.Sdk,
ASP.NET Core TestHost and Mono.Cecil in test projects only. SQLite remains
private to its existing fixture. No new production or vendor dependency.
Local packing is acceptance evidence, not authorization to publish NuGet packages.

**Storage**: Synthetic SQLite/memory and Local/ObjectSemantics stores in fresh
owner-private roots outside Git. JSON manifests and sanitized summaries;
retained build/test diagnostics are sanitized before persistence. Existing
Abstractions metadata/artifact interfaces and authority seams stay unchanged.

**Testing**: Extract common assertions without narrowing coverage. Add binding,
inventory/evidence, mutation, contributor and CI-parity regressions. Real
process interruption and 256 MiB/4 GiB transfer/RSS checks remain required.
All six existing feature validation entry points remain regression gates;
no prior passing report qualifies current changed inputs automatically.

**Target Platform**: Mandatory CI on `ubuntu-24.04`, exact image/runtime/filesystem
recorded; local macOS or Linux uses the identical profiles. A run qualifies only
its actual environment. No Windows, remote-service, OS/power-loss or HA claim.
Dependency restoration may need nuget.org; no external running service, cloud
account or credential is required.

**Project Type**: Test SDK, contributor fixtures, evidence CLI and conformance
CI only. Core remains empty/provider-free; no curated server or UI is created.

**Performance Goals**: Finite observable completion, not production throughput.
Preserve F-05/F-06 operation/buffer/queue limits and the <=64 MiB incremental
peak RSS criterion for each actual large artifact transfer. Outer observation
budgets never increase an inner contract deadline or release late work.

**Constraints**: [Harness contract](contracts/harness.md) defines exact budgets,
isolation and retained ownership. Full artifact profile requires at least
24 GiB free private local scratch at admission; transfers and large copies are
serial within that profile. Insufficient resources are `Incomplete`, never a
smaller substitute. Hosted-runner capacity must be measured at implementation;
if inadequate, resolve an explicitly provisioned runner prerequisite rather than
delete unrelated runner software or reduce mandatory coverage.

**Scale/Scope**: Five stories, 23 scenarios, 14 edge cases, 24 FRs/eight SCs;
192 inherited category entries, 20 composition rows, policy/boundary and
architecture expansions, and 48 F-07 proof obligations. Five mandatory CI
profiles execute the same finite catalog as local baseline mode.
See [matrix](contracts/matrix.md) and [acceptance](contracts/acceptance.md).

## Constitution Check

*Evaluated before Phase 0 and re-evaluated after Phase 1 design.*

| Principle / constraint | Pre-research gate | Post-design gate |
| --- | --- | --- |
| I: cache/native/personal | Pass: qualification foundation only | No publishing registry, native-client claim or required cloud dependency |
| II: versioned explicit composition | Pass: existing contracts authoritative | Test SDK outside production graph; explicit package bindings and unchanged singleton/optional-target policy |
| III: centralized correctness | Pass: no new engine/slice | Shared assertions exercise existing authority/contracts; no duplicated publication, GC or activation implementation |
| IV: verified bounded recovery | Pass: all prior guarantees retained | Real local crash/large-transfer proof; finite observations retain live ownership; simulation never supplies durability |
| V: security/isolation | Pass: no new network feature | Private synthetic roots, exact process ownership, allowlisted reports, no raw artifact uploads or CI secrets |
| VI: evidence before claims | Pass: paired independent fixtures | Exact expected inventory, runtime witness mapping, red/green pairs, fail-closed aggregation and five-profile CI parity |
| VII: static accessible console | Not exercised | No rendered UI, Next.js/Node, management API or OpenAPI change |
| VIII: compatibility/reversibility | Pass: separate test extension | Frozen source/binary baselines, unchanged policies, scoped reproducible reports, explicit incomplete cleanup and unsupported choices |
| Workflow | Pass: recorded branch, pinned directory, `plan / running` | Installed planning skill only; separate later checklist/tasks/analysis/implementation gates; draft PR and durable checkpoint |

No exception, constitutional amendment or ADR change is proposed. These are
design gates, not passing runtime evidence. The bounded architecture review
identified a retained-diagnostics sanitation gap and an unspecified child-output
bound; both are corrected in the contracts below. No reviewer-owned checklist
approval or runtime evidence follows from that review.

## Project Structure

### Documentation (this feature)

```text
specs/007-provider-conformance/
|-- spec.md
|-- checklists/requirements.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
`-- contracts/
    |-- harness.md
    |-- evidence.md
    |-- matrix.md
    `-- acceptance.md
```

Custom reviewer-owned checklists and `tasks.md` are separate later stages.

### Source Code (future implementation, not created by planning)

```text
tests/contracts/Hoard.Testing.Conformance/     # Packable test SDK, no providers
tests/contracts/Hoard.Conformance.Tests/       # SDK/evaluator integration checks
tests/contracts/Hoard.Metadata.Tests/          # Existing case wrappers retained
tests/contracts/Hoard.Artifacts.Tests/         # Existing case wrappers retained
tests/fixtures/conformance/Bindings/           # Existing-provider setup adapters
tests/fixtures/conformance/Contributor/        # Separate good/faulty adapter example
tests/fixtures/conformance/Host/               # In-process packaged fixture host
tests/fixtures/conformance/Consumer/           # Package-only shared-kit consumer
tests/integration/Hoard.Composition.Tests/     # Extend existing lifecycle checks
tests/architecture/Hoard.Architecture.Tests/   # Real graph and permitted counterparts
tests/tooling/test_conformance_evidence.py     # Evidence mutation/CLI regressions
scripts/validate-conformance.sh                # Shared local/CI entry point
scripts/conformance_evidence.py                # Bounded execution and evaluator
scripts/conformance_case_catalog.py            # Versioned expected cases/witnesses
.github/workflows/conformance.yml              # Five profiles + aggregate check
examples/ProviderConformance/README.md          # Contributor reproduction guide
```

**Structure Decision**: The test SDK references Abstractions and test frameworks,
not Hosting, Core or concrete providers. Its optional composition test driver
lives in the host fixture, outside the SDK. Bindings may reference the SDK and
their own provider package; composition adapters own Hosting integration.
Provider implementations never reference one another or the test SDK.
Existing production references and public contracts do not change.

## Phase 0: Resolved Research

[Research](research.md) resolves extraction strategy, assertion authority,
runtime attribution, old consumers, finite environment scope, CI and cleanup.
Existing concrete helpers are not already an independent contributor entry point:
extract their common consumers behind typed bindings, rather than merely wrap
the old scripts and call it reusable certification. No unresolved product
clarification remains. Runner capacity and action commit selection are explicit
implementation prerequisites, not invented planning evidence.

## Phase 1: Design and Integration

1. Freeze catalog revision `f07-v1` and pre-extraction witnesses. Extract shared
   logical consumers, retaining all case IDs and inherited subproofs.
2. Implement four separate binding adapters and validate capability/applicability
   before executing common assertions. Missing mandatory hooks are failures.
3. Produce and independently evaluate input-bound evidence; upgrade weaker
   lower-level witness attribution where required instead of trusting pass counts.
4. Exercise the finite baseline/replacement, startup/lifecycle and version
   matrix through existing composition APIs. Preserve architecture negatives
   and permitted Identity -> Hosting -> Core path handling.
5. Compile unchanged source and run frozen old binaries against candidate
   packages; demonstrate isolated breaking counterparts.
6. Prove the contributor route with a separately built, test-only forwarding
   adapter and deliberate faulty behavior, never edits to shared assertions.
7. Add the five-profile CI with read-only permissions, exact revision inputs,
   bounded execution and sanitized-only uploads. A separate aggregate check
   recomputes completeness rather than trusting job status or summary labels.

## Requirement and Outcome Traceability

| Requirements | Design owner | Required proof |
| --- | --- | --- |
| FR-001..003 | Harness catalog, binding contracts | QC-01..05; all 192 inherited entries |
| FR-004 | Metadata binding/common suite | QC-06..08; MP-01..48 on both |
| FR-005 | Artifact binding/common suite | QC-09..12; AS-01..48 on both |
| FR-006..010 | Composition matrix | QC-13..21; CP-01..20 |
| FR-011 | Version expansion | QC-22..24 |
| FR-012 | Compatibility baselines | QC-25..26 |
| FR-013 | Existing actual graph inspectors | QC-27..28; ARCH-001..008 paired |
| FR-014 | Exact support matrix | QC-29,47 |
| FR-015 | Packaged contributor entry point | QC-30..32 |
| FR-016 | Owned resources and budgets | QC-33..36 |
| FR-017 | Local/CI prerequisites and exclusions | QC-37,46 |
| FR-018 | Evidence input/witness binding | QC-38..41 |
| FR-019 | Recorded mutation pairs | QC-04,14,22,26..28,31 |
| FR-020 | Independent completeness evaluator | QC-39..44 |
| FR-021 | Five-profile CI parity | QC-45..46 |
| FR-022 | Closed safe diagnostics | QC-21,35,48 |
| FR-023..024 | Scope and reproduction guide | QC-29..32,37,47..48 |

All eight outcomes and all 23 scenarios/14 edge cases are mapped in
[acceptance](contracts/acceptance.md). Prior requirements/checklist markers stay
unchanged. No tasks are generated and no product acceptance is claimed.

## Planning Review

The custom architecture review found that public-only sanitation would not
satisfy FR-022 for private retained logs/evidence, and that finite child deadlines
alone do not bound output memory/disk use. The design now requires sanitation
before diagnostic persistence, checks both private retained diagnostics and
public projections, forbids raw-output spooling, and declares finite incremental
capture limits with an explicit overflow failure. Synthetic live test stores
are resources, not diagnostic evidence; ownership-driven retention does not
qualify them as safe report artifacts. QC-34/QC-48 include those exact proofs.

Implementation still owes actual extraction parity, runner capacity, source/
binary resolution, process settlement, output-flood and sanitation evidence.
Planning establishes no passing product behavior or blanket certification.

## Complexity Tracking

No constitutional violation requires an exception. One shared test SDK and
one evidence evaluator are necessary for independently packaged authors to use
unchanged assertions; a general plugin system, second activation model,
credentialed service matrix and certification marketplace are rejected.
