# Tasks: Provider Conformance, Compatibility and Composition

**Input**: [Specification](spec.md), [plan](plan.md), [research](research.md),
[data model](data-model.md), [harness](contracts/harness.md),
[matrix](contracts/matrix.md), [evidence](contracts/evidence.md) and
[acceptance](contracts/acceptance.md).

**Prerequisites**: Read-only analysis must pass before implementation. The 40
custom checklist items remain reviewer-owned and unchecked; implementation
requires reviewer approval or explicit authorization. This task list grants
neither approval nor qualification.

**Tests**: Explicitly required by the specification. Add focused regressions
first and record their intended failure before correcting behavior. Expected
negative children must fail the named assertion, not setup, except intentional
source-compatibility compiler negatives. Preserve unchanged controls and all
inherited subproofs. No test result is claimed by generating this file.

**Organization**: Setup, shared foundations, five story increments, then complete
acceptance/documentation. All 86 tasks start unchecked. `[P]` identifies
different-file work that may run concurrently only after its listed prerequisites.
Exact prerequisites below override file order; shared-file edits are serialized.
Paths are repository-relative. New filenames are planned implementation targets,
not claims that commands or APIs already exist.

## Phase 1: Setup

**Purpose**: Freeze the existing agreement and introduce test-only manifests;
do not build candidate packages before sealing compatibility baselines.

- [x] T001 Record pre-extraction MP-01..48, AS-01..48, all parameterized runtime names/subproofs, convergence regressions and historical baseline revisions in `tests/fixtures/conformance/baselines/inventory.json`; pin F-07 baseline to `9389016c0285c79f6f515f59805a5a41c69b0767` without copying old passes into new runs (FR-001,012,018; QC-01,25).
- [x] T002 Create locally packable nullable .NET 10 test SDK manifest `tests/contracts/Hoard.Testing.Conformance/Hoard.Testing.Conformance.csproj`, referencing only Abstractions and existing central test dependencies; never Hosting, Core or providers, and never publish the package (FR-002,013).
- [x] T003 [P] Add four independent binding project manifests under `tests/fixtures/conformance/Bindings/{Sqlite,Memory,Local,ObjectSemantics}/`, each referencing the SDK and its own existing provider only; keep SQLite/native/vendor dependencies private, public operation contracts unchanged and provider mechanisms independent; allow necessary fixture-private bounded encoding/fault seams to preserve mandatory corruption assertions (FR-002,003,013).
- [x] T004 [P] Add explicit package-only project manifests `tests/fixtures/conformance/Consumer/Consumer.csproj`, `tests/fixtures/conformance/Host/Host.csproj` and `tests/fixtures/conformance/Contributor/Contributor.csproj`; keep Hosting integration outside the SDK and use no directory assembly discovery or product listener (FR-006,015).
- [x] T005 Register SDK, bindings, fixtures and `tests/contracts/Hoard.Conformance.Tests/Hoard.Conformance.Tests.csproj` in `Hoard.slnx` and existing build/package conventions; use centrally pinned dependencies and preserve all production reference edges (FR-013).
- [x] T006 [P] Write failing strict-model/catalog tests in `tests/tooling/test_conformance_evidence.py` for the required data-model fields, duplicate keys, bounds, immutable expected keys and unsupported schemas/statuses before implementing the evaluator (FR-001,018,020,022; QC-01,44).

## Phase 2: Foundational prerequisites

**Purpose**: Safe immutable inputs, typed bindings, owned execution and observed
evidence are required by every story. No candidate behavior can qualify yet.

- [x] T007 Implement typed immutable binding/session/fault/context/cleanup contracts in `tests/contracts/Hoard.Testing.Conformance/Bindings/` and strict evidence entities in `scripts/conformance_evidence.py` using every required field/relationship in `data-model.md`; enforce "All collections are copied, bounded and immutable after admission; absent required values fail validation", "Stable IDs: ASCII `[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}`", "lowercase SHA-256 hex; NuGet SHA-512 additionally retained where used", "JSON schema revision `1`, catalog revision `f07-v1`", and "unknown schema/status/ fields, duplicate object keys, non-finite numbers and path traversal reject"; use typed existing provider contracts, never provider pass booleans (FR-001,002,018,020; QC-01,05,44).
- [x] T008 Implement independently expanded catalog `scripts/conformance_case_catalog.py` and matching SDK catalog in `tests/contracts/Hoard.Testing.Conformance/Catalog/`; freeze all 192 inherited keys, CP-01..20 subvariants, version/architecture expansions and QC-01..48 with exact witness mappings; enforce "At most 10,000 expanded results/profile, 128 witnesses/case, three attempts/ case (default one), 1,024 bytes/safe diagnostic and 16 MiB/public report" and "Proof manifests permit at most 50,000 files and 256 MiB total"; use explicit `none` binding/matrix dimensions and reject overflow, never truncate (FR-001,014,020; QC-01,39,44).
- [x] T009 [P] Add failing owned-root/process, watchdog, concurrency, output-flood and canary persistence regressions in `tests/tooling/test_conformance_execution.py`; include hostile/symlink/pre-existing roots, outside sentinels, PID/start mismatch and non-cooperative work before implementing execution (FR-009,016,022; QC-33..36,48).
- [x] T010 Implement private resource ledger/allocation and cleanup in `scripts/conformance_execution.py`; enforce `Allocated -> Active -> Settling -> Released` or `Settling -> Retained -> Settling`, actual exit/settlement before release, one writer/root, independent stores/caches/feeds and no symlinked ancestor; reject user stores/foreign roots and preserve live children/resources without broad deletion or name-based termination (FR-016; QC-33,35,36).
- [x] T011 Implement bounded incremental diagnostic projection in `tests/contracts/Hoard.Testing.Conformance/Diagnostics/` and `scripts/conformance_execution.py`; reads <=64 KiB, transient aggregate <=1 MiB/child, sanitized retention <=8 MiB/child and <=64 MiB/profile, no raw TRX/stdout/stderr disk spool; closed safe codes/templates must sanitize before private/public persistence and output overflow must yield `OutputLimitExceeded`, never shortened passing evidence (FR-016,022; QC-34,48).
- [x] T012 Add finite supervisor/environment preflight in `scripts/conformance_execution.py` with all harness budgets: five-second ordinary controls, 15-second barriers, ten-minute ordinary children, 40-minute transfer children, five-minute recovery children, ten-second exact-owned termination, 30-second cleanup, 90-minute metadata/180-minute artifact/60-minute other profiles and 480-minute sequential baseline; max four children/one transfer child, monotonic observations and stricter inner limits win; require actual >=24 GiB private local artifact scratch, recording insufficient capacity as `Incomplete` without deleting unrelated files or reducing transfers (FR-009,016,017; QC-34..37).
- [x] T013 Implement immutable per-profile source/input snapshots in `scripts/conformance_evidence.py`, binding actual source bytes, SDK/catalog, locks, local nupkg SHA-256/SHA-512/source mapping, safe synthetic configuration/capabilities, runtime assemblies and exact environment; enforce "private mount/root paths and arbitrary environment-variable dumps are forbidden", no production connection strings, pre/post recomputation and explicit dirty-local versus clean-CI identity (FR-018,022; QC-38,41,48).
- [x] T014 Implement runtime discovery/witness and safe proof ingestion in `scripts/conformance_evidence.py` plus `tests/contracts/Hoard.Testing.Conformance/Evidence/`; require exact fully qualified parameter identities, execution IDs, actual invocation/loaded assembly and proof/input provenance, never totals/substrings/copied labels; retain append-only attempts and `Expected -> Running -> Passed | Failed | NotApplicable | Incomplete`, reject unknown diagnostics safely and separate synthetic stores from retained diagnostic evidence (FR-018,020,022; QC-39,40,42..44,48).
- [x] T015 Implement baseline preparation in `scripts/conformance_baselines.py` using the owned bounded executor: build/seal source/recipe/lock/dependency/binary hashes from exact F-06 merge and each predecessor's recorded baseline before candidate builds; never rebuild/substitute retained binaries during candidate execution or invent an old SDK release (FR-012,018; QC-25).
- [x] T016 Add lock-preparation entry point in `scripts/validate-conformance.sh` and generate/review tracked `packages.lock.json` for all new projects and local package source mapping through `--update-locks`; use sealed historical baseline first, label preparation non-qualifying and perform independent fresh default locked build replay without editing predecessor locks unnecessarily (FR-012,018,021).
- [x] T017 Implement CLI admission/dispatch in `scripts/validate-conformance.sh` and `scripts/conformance_evidence.py`: exact planned profiles, fresh evidence path, explicit category binding project, diagnostic filter, preparation, verify and aggregate modes; safe exit codes 0/1/2, no service-profile fallback and diagnostic/preparation always `qualification: false` (FR-016,017,020,024; QC-37,47).
- [x] T018 Run foundational red/green regressions in `tests/tooling/test_conformance_execution.py`, `tests/tooling/test_conformance_evidence.py` and typed SDK tests in `tests/contracts/Hoard.Conformance.Tests/BindingContractTests.cs`; prove missing mandatory fault hooks fail admission, immutable copied declarations, no provider-selected expectations and safe incomplete ownership; record actual intended failures and passing repairs (FR-001,002,016,020,022; QC-01,05,33..36,44,48).

**Checkpoint**: Foundations admit safe test runs, not a qualifying category or
five-profile baseline. All Phase 1/2 tasks must pass before story work starts.
T017 is the admission/dispatch boundary: preparation executes, while an unbuilt
runtime/evaluation backend must explicitly reject with `EvidenceIncomplete`.
It does not complete the implementations separately assigned to T035, T046,
T057, T064 or T071..T074. Those tasks must replace the current guards before
their modes can execute or qualify; no passing profile/verification is implied.

## Phase 3: US1 - Qualify providers against one shared agreement (P1, MVP)

**Goal**: Unchanged common assertions execute against both independent metadata
and both artifact implementations without weakening inherited guarantees.

**Independent test**: Run complete metadata and artifact profiles with exact
192-entry equality (179 applicable passes/13 authorized exclusions), all named
subproofs and four integrations. Faulty metadata/artifact bindings fail named
assertions; corrected bindings pass unchanged consumers. Actual SQLite/Local
crash proof and real transfers remain mandatory; this is not the full baseline.

### Tests first

- [X] T019 [P] [US1] Add extraction-parity and hook-admission tests in `tests/contracts/Hoard.Conformance.Tests/MetadataBindingTests.cs` from frozen inventory, including all inherited convergence regressions; fail when either provider misses a parameterized witness or supplies its own expected result (FR-002..004; QC-02,05..08).
- [X] T020 [P] [US1] Add extraction-parity, streaming/authority and durability-scope tests in `tests/contracts/Hoard.Conformance.Tests/ArtifactBindingTests.cs`; fail for missing AS subproofs or simulation borrowing Local recovery (FR-002,003,005; QC-03,05,09..12).

### Implementation

- [X] T021 [US1] Extract metadata common consumers/assertions into `tests/contracts/Hoard.Testing.Conformance/Metadata/` behind typed sessions/fault controls, preserving public-read/receipt corroboration, identity partitioning, atomic/conditional/grouped reads, bounded pages, leases, references, uncertain outcomes and all MP/convergence cases without concrete-provider switches (FR-002,004; QC-02,06,07).
- [X] T022 [P] [US1] Implement SQLite setup/fault/reopen/settlement adapter in `tests/fixtures/conformance/Bindings/Sqlite/SqliteBinding.cs`, retaining independent provider mechanisms, schema/backup/recovery barriers and actual late native-work protection; never move private DB types into common checks (FR-002..004; QC-02,07,08).
- [X] T023 [P] [US1] Implement independent memory adapter in `tests/fixtures/conformance/Bindings/Memory/MemoryBinding.cs` with all mandatory logical controls and only MP-36,38..45 catalog-authorized non-durable exclusions, not SQLite delegation (FR-002..004; QC-02,05,08).
- [X] T024 [US1] Rewire existing wrappers in `tests/contracts/Hoard.Metadata.Tests/Cases/MetadataCases.cs` and its session helpers to shared consumers, preserving frozen names/parameters or explicitly mapped reviewed replacements; prove identical common source bytes for both bindings (FR-002,004,018; QC-02,06).
- [X] T025 [US1] Upgrade `scripts/metadata_evidence.py` and `scripts/validate-metadata.sh` imports/logger integration to exact runtime witness attribution and pre-persistence bounded safe projection; retain all MP subproofs, historical baselines and fresh input hashes rather than weakening fingerprints or trusting 96 labels (FR-004,018,022; QC-06..08,38..40,48).
- [X] T026 [US1] Execute real SQLite schema/backup/restore/abrupt-process recovery via `tests/fixtures/metadata/CrashRunner/` and `scripts/conformance_evidence.py`; observe required barriers, owned termination/exit and readback, with memory exclusions explicitly non-durable (FR-003,004; QC-08).
- [X] T027 [US1] Extract artifact common consumers/assertions into `tests/contracts/Hoard.Testing.Conformance/Artifacts/`, keeping verification/visibility, protected reads, shared authority, incarnation fencing, quarantine, uncertain publication/deletion and recovery assertions independent of Local/ObjectSemantics implementations (FR-002,005; QC-03,09).
- [X] T028 [P] [US1] Implement Local binding/fault/reopen/settlement adapter in `tests/fixtures/conformance/Bindings/Local/LocalBinding.cs` with existing validator, maintenance/lifetime and same authority, retaining independent filesystem publication and real crash barriers (FR-002,003,005; QC-03,09,11).
- [X] T029 [P] [US1] Implement independent ObjectSemantics adapter in `tests/fixtures/conformance/Bindings/ObjectSemantics/ObjectSemanticsBinding.cs`; preserve direct-visibility and receipt/generation controls without calling Local, with only AS-41..44 excluded for simulation/no durable restart (FR-002,003,005; QC-03,05,11).
- [X] T030 [US1] Rewire `tests/contracts/Hoard.Artifacts.Tests/Cases/ArtifactProviderDrivers.cs` and existing artifact case wrappers to common consumers while preserving actual frozen case/parameter names and expected subproofs; remove concrete-provider branching from common assertions (FR-002,005,018; QC-03,09).
- [X] T031 [US1] Adapt `scripts/artifact_evidence.py`, `scripts/artifact_case_catalog.py` and `scripts/validate-artifacts.sh` to safe bounded witness ingestion without weakening existing exact inventory/source/package checks or inherited recovery/large-transfer proof (FR-005,018,022; QC-09..11,38..40,48).
- [X] T032 [US1] Execute actual paced non-seekable 256 MiB and 4 GiB write/read transfers on both options via `tests/fixtures/artifacts/TransferRunner/`, retaining <=64 MiB incremental OS peak RSS per actual transfer and inherited buffers/deadlines; serialise large work and preserve real Local AS-41..44 barrier/exit/readback proofs via `tests/fixtures/artifacts/CrashRunner/` (FR-003,005,016; QC-10,11).
- [X] T033 [US1] Add/execute all `sqlite/local`, `sqlite/object`, `memory/local`, `memory/object` authority integration rows in `tests/contracts/Hoard.Conformance.Tests/AuthorityIntegrationTests.cs`, proving live references/readers, current-incarnation ABA fencing, uncertain outcomes and no independent unsafe deletion authority (FR-004,005; QC-12).
- [X] T034 [US1] Add isolated faulty metadata stale-operation and artifact visibility/verification adapters in `tests/fixtures/conformance/Bindings/Mutations/` and paired tests in `tests/contracts/Hoard.Conformance.Tests/CategoryMutationTests.cs`; record named assertion failures and corrected passes with unchanged assertion/catalog hashes, not incidental build errors (FR-002,019; QC-04).
- [X] T035 [US1] Wire metadata/artifact profiles in `scripts/conformance_evidence.py` to independently selected immutable applicability, exact lower-level input/witness imports and final-key equality; reject missing mandatory hooks and retain 192 entries with only 13 authorized durability exclusions, never successful reduced inventories (FR-001..005,018,020; QC-01..12).
- [X] T036 [US1] Implement package-only common consumer in `tests/fixtures/conformance/Consumer/` that explicitly references independently packed SDK/bindings/provider packages; prove unchanged consumer bytes, exact local package resolution and no concrete provider references inside the SDK (FR-002,003,013,018; QC-02,03).
- [X] T037 [US1] Run complete independent category acceptance through `scripts/validate-conformance.sh` metadata/artifact profiles and frozen wrapper parity tests, comparing observed per-parameter witnesses against `tests/fixtures/conformance/baselines/inventory.json`; retain all logical/recovery/large-transfer and category mutation proofs in safe input-bound reports (FR-001..005,018,019; QC-01..12).
- [X] T038 [US1] Record actual category scope/exclusions and extraction evidence in `specs/007-provider-conformance/plan.md` and `docs/PROVIDERS.md`, explicitly distinguishing real SQLite/Local durability, memory/object simulation and declaration-only protocol/identity from production/native-client support (FR-003,014,023; QC-29).

## Phase 4: US2 - Reject unsafe host compositions before use (P1)

**Goal**: Existing lifecycle APIs validate finite explicit compositions, with no
fallback, disabled effects, premature readiness or false cleanup.

**Independent test**: Run the composition profile over every CP-01..20
subvariant, paired repairs and inherited F-02/F-03/F-04 inventories. Observe
construction, routes, workers, connections, actual readiness/admission and
settlement independently; no category throughput proof is required to diagnose
a composition row.

### Tests first

- [X] T039 [P] [US2] Add complete CP-01..13 theory rows and assertion-level rejection/repair pairs in `tests/integration/Hoard.Composition.Tests/ConformanceCompositionTests.cs`, including reordered cycles, both zero/two singleton cases and independent disabled effects (FR-006..008,010,019; QC-13..16,20).
- [X] T040 [P] [US2] Add CP-14..20 controlled failure/cancellation/non-cooperation/restart tests in `tests/integration/Hoard.Composition.Tests/ConformanceOwnershipTests.cs`; distinguish finite return from actual release and inject unsafe error canaries (FR-006,009,016,022; QC-17..19,21).

### Implementation

- [X] T041 [US2] Implement explicit in-process packaged fixture host and identical baseline/replacement consumer in `tests/fixtures/conformance/Host/`; select SQLite/Local versus memory/ObjectSemantics packages, initialize before readiness and observe bounded stop without exposing a curated executable/public listener (FR-006; QC-13).
- [X] T042 [US2] Implement independently observable constructor/route/worker/connection probes and declaration repair fixtures in `tests/fixtures/conformance/Host/CompositionFixtures.cs`; exercise CP-03 multiplicity, CP-04..10 preconstruction declaration rejection, CP-11 actual mapping ambiguity before publication/initialization/readiness/admission, and all repairs with existing Hosting validation, not a second activation implementation (FR-007,008,019; QC-14,15).
- [X] T043 [US2] Implement CP-12/13 disabled/absent/compatible/incompatible optional targets in `tests/fixtures/conformance/Host/CompositionFixtures.cs`, proving unavailable capability/no active edge for disabled/absent targets and no auto-disable/fallback for incompatible enabled targets (FR-008,010; QC-16,20).
- [X] T044 [US2] Implement controlled CP-14..18 initializer/readiness/recovery/shutdown probes in `tests/fixtures/conformance/Host/OwnershipFixtures.cs`, using existing lifecycle ownership and barriers; observe retained bounded work before exact-child containment and eventual actual settlement, never claim cooperative cleanup from termination (FR-009,016; QC-17..19).
- [X] T045 [US2] Implement CP-19 authority identity/missing guarantee admission and CP-20 settled stop/restart/request-active-config cases in `tests/fixtures/conformance/Host/OwnershipFixtures.cs`; reject before store I/O and preserve explicit restart rather than hot replacement (FR-006,009,022; QC-21).
- [X] T046 [US2] Integrate complete inherited lifecycle/configuration/discovery inventories into composition profile in `scripts/conformance_evidence.py`, adapting legacy diagnostic capture before reuse; require fresh child manifests, exact runtime witnesses and source/input agreement, not old green reports (FR-006..010,018,022; QC-13..21,38..40,48).
- [X] T047 [US2] Run `scripts/validate-conformance.sh` composition profile and tests in `tests/integration/Hoard.Composition.Tests/ConformanceMatrixTests.cs` using `tests/fixtures/conformance/Host/OwnershipFixtures.cs`, retaining each CP subvariant, rejection/repair proof, disabled counters, readiness/ownership observations and safe failure codes (FR-006..010,019; QC-13..21).
- [X] T048 [US2] Add missing/duplicate CP-witness, false readiness and optimistic cleanup report challenges to `tests/tooling/test_conformance_evidence.py`; require independent rejection despite successful host exit/status labels (FR-009,018,020; QC-18,19,39,42).
- [X] T049 [US2] Document finite packaged baseline/replacement and actual lifecycle-only protocol/identity scope in `examples/CustomHost/README.md` and `docs/PROVIDERS.md`, retaining explicit enablement/restart/no-fallback and unsettled ownership recovery limits (FR-006,008,014,023,024; QC-29).

## Phase 5: US3 - Detect compatibility regressions before release (P1)

**Goal**: Version declarations, unchanged source, genuine retained binaries and
actual dependency graphs each have their own attributable proof.

**Independent test**: Run compatibility profile, every version-policy expansion,
sealed baseline consumers and ARCH-001..008 isolated negatives/permitted pairs.
Deliberate source/binary breaks fail for the intended symbol/runtime rule while
compatible counterparts pass unchanged consumers.

### Tests first

- [X] T050 [P] [US3] Add every range/candidate/flag row from `contracts/matrix.md` in `tests/integration/Hoard.Composition.Tests/ConformanceVersionTests.cs`, expanded across host/abstractions/required and enabled-optional dependency axes, malformed inputs and independent prerelease flags; use actual runtime validator plus existing classifier, no new range parser (FR-010,011,019; QC-22..24).
- [X] T051 [P] [US3] Add source/retained-binary provenance and intended-break controls in `tests/contracts/Hoard.Conformance.Tests/CompatibilityBaselineTests.cs`, rejecting candidate-rebuilt baselines or accidental old DLL resolution (FR-012,018,019; QC-25,26).
- [X] T052 [P] [US3] Extend `tests/architecture/Hoard.Architecture.Tests/ConformanceArchitectureTests.cs` with SDK-outside-production positive/negative graph cases, complete required scan checks and inspection-failure challenges; preserve all eight established rules, declared-unused/transitive/public/IL cases and both Identity path edge orders (FR-013,019; QC-27,28).

### Implementation

- [X] T053 [US3] Add explicit version-policy fixture inputs in `tests/fixtures/conformance/Host/VersionFixtures.cs`; exercise inclusive/exclusive/exact/build/case/prerelease/malformed rows and absent/registered-disabled optional targets, preserving C-01..23 classifications and no range widening (FR-010,011; QC-22..24).
- [X] T054 [US3] Add source consumer/provider-implementer build recipes in `tests/fixtures/conformance/baselines/source-consumers.json` for all four bindings and inherited API surfaces; compile unchanged historical sources against exact candidate packages, never edit consumers to accommodate a break (FR-012; QC-25).
- [X] T055 [US3] Extend `scripts/conformance_baselines.py` to execute sealed F-06/predecessor retained consumers/providers against observed candidate assemblies, verifying frozen binary/dependency hashes before/after and actual loaded bytes without recompilation; distinguish old marker baselines from operational common-suite evidence (FR-012,018; QC-25).
- [X] T056 [US3] Add isolated candidate source/binary breaks and compatible repairs under `tests/fixtures/conformance/Compatibility/`, reusing existing compatibility fixtures where possible; record intended consumed-symbol compiler failure or actual retained-member/assembly invocation failure and unchanged-consumer corrected success (FR-012,019; QC-26).
- [X] T057 [US3] Wire actual graph/assets/nuspec/public-surface/IL inspection into compatibility profile in `scripts/conformance_evidence.py`, reusing existing inspectors; reject missing/unresolved/ambiguous/incomplete scans, preserve ARCH-001..008 paired cases and permitted Identity -> Hosting -> Core alongside forbidden direct/helper paths in both traversal orders (FR-013,018,019; QC-27,28).
- [X] T058 [US3] Add compatibility profile version/source/binary/import challenges in `tests/tooling/test_conformance_evidence.py`, rejecting changed version/package bytes, omitted axes or sealed baseline substitution despite matching version strings (FR-011,012,018,020; QC-22..26,38..40).
- [X] T059 [US3] Run compatibility profile via `scripts/validate-conformance.sh`, retaining exact expanded classifications/runtime rows, unchanged-source and old-binary actual resolution, all architecture negatives/permitted counterparts and unchanged assertion hashes (FR-011..014,019; QC-22..29).
- [X] T060 [US3] Update compatibility guidance in `docs/PROVIDERS.md` with actual tested baseline revisions/packages, declared-versus-observed compatibility and finite unsupported versions; state new SDK has no historical release and qualification never authorizes publishing/release/deployment (FR-012,014,023,024; QC-25,29).
- [X] T061 [US3] Record immutable source/binary/graph proof references and red/green classification in `specs/007-provider-conformance/plan.md`, explicitly distinguishing policy-only C classifications from runtime behavior and avoiding untested Cartesian-product support (FR-011..014,018,019; QC-22..29).

## Phase 6: US4 - Add a provider without rewriting tests (P2)

**Goal**: A separately packaged forwarding adapter uses the unchanged suite and
reproduces a diagnosable fault using documented no-service prerequisites.

**Independent test**: Follow only the contributor guide from a fresh checkout:
build good adapter, run complete applicable suite, select stale-operation fault,
observe named failure and correct only adapter for passing rerun. Preserve
separate run identities and common-source hashes; do not count the example as
a third independent implementation.

### Tests first

- [X] T062 [P] [US4] Add package-only contributor good/faulty/corrected journey tests in `tests/contracts/Hoard.Conformance.Tests/ContributorJourneyTests.cs`, asserting intended stale conditional-operation failure, unchanged platform/provider/assertion bytes and explicit category validation (FR-015,019; QC-30,31).

### Implementation

- [X] T063 [US4] Implement good and selectable faulty forwarding bindings in `tests/fixtures/conformance/Contributor/`, using typed setup/fault/cleanup seams over one existing fixture; faulty adapter returns stale conditional result, never changes shared expected outcomes or pretends to be an independent provider (FR-015,019; QC-30,31).
- [ ] T064 [US4] Wire explicit `--binding-project` build/pack/category admission in `scripts/conformance_evidence.py` and `tests/fixtures/conformance/Consumer/`, using complete applicable common catalog and exact new package hashes, no reflection/directory loading or provider-chosen case omissions (FR-015,018; QC-30).
- [ ] T065 [US4] Write clean-checkout reproduction and owned-recovery guide in `examples/ProviderConformance/README.md` covering dependency restore, private scratch, explicit package resolution, good/faulty/corrected commands, exclusions, safe diagnostics, changed-input reruns and unavailable service scope; no undocumented/cloud/credential requirement (FR-015..017,023,024; QC-32,35..37).
- [ ] T066 [US4] Execute guide verbatim from an isolated clean source snapshot via `scripts/validate-conformance.sh`, recording separate good/red/corrected runs, actual unchanged consumer/assertion hashes and intended assertion failure with corrected package-only behavior (FR-015,019,024; QC-30..32).
- [ ] T067 [US4] Reproduce overlapping contributor runs, interrupted child retention/recovery and unavailable-service rejection using `tests/tooling/test_conformance_execution.py` and guide commands; verify outside sentinel preservation, exact process ownership and safe explicit incomplete status (FR-016,017,024; QC-33..37).

## Phase 7: US5 - Review trustworthy automated qualification evidence (P2)

**Goal**: Strict observed-input evaluation and five-profile CI fail closed while
producing complete safe finite support statements.

**Independent test**: Evaluate freshly generated successful runtime reports and
single-field/proof mutations; all missing/duplicate/stale/altered/excluded/
retried-away failures reject. Local/CI inventories match; cancelled/missing jobs
or artifacts cannot qualify. Canary inspection covers all private diagnostics
and public files, not only upload text.

### Tests first

- [ ] T068 [US5] Add generated-good-control mutation tests in `tests/tooling/test_conformance_evidence.py` for QC-38..44: every input class, exact keys/parameters, provenance/proofs, capability/exclusion changes, incomplete/skipped/unknown outcomes, append-only failed retries, optimistic summaries, duplicate/unknown schema fields, malformed Unicode/durations, oversize/path escapes and proof limits; samples alone cannot prove runtime origin (FR-018..020,022).
- [ ] T069 [P] [US5] Add local/CI parity, all-five-report aggregation and job/upload/download/cancellation failure tests in `tests/tooling/test_conformance_ci.py`, including foreign invocation/SHA, missing profile and focused/preparation mode rejection (FR-017,020,021; QC-45..47).
- [ ] T070 [P] [US5] Add all-output canary challenges in `tests/tooling/test_conformance_sanitation.py` for retained private diagnostic/proof files, filenames, public JSON/JUnit/Markdown and CI summaries; unsafe provider errors/configuration/payloads/paths must not persist, and unknown text must fail safely rather than disappear into success (FR-022,024; QC-48).

### Implementation

- [ ] T071 [US5] Complete independent strict evaluator in `scripts/conformance_evidence.py`: expand expected catalog independently, verify exact results/witnesses/proof bytes and input origin, immutable applicability, red/green/baselines/crash/transfers, failed attempt history and actual settlement; derive qualification rather than trust cached booleans (FR-018..020; QC-38..44).
- [ ] T072 [US5] Implement safe JSON/JUnit/Markdown reports and finite support matrix in `scripts/conformance_evidence.py`; enforce run `Created -> Admitted -> Running -> Evaluating -> Complete` with `Failed`/`Incomplete` not qualification, immutable input/environment/exclusion scope, safe resource IDs and no unsupported service/native/protocol/identity/production/HA claims (FR-014,020,022..024; QC-29,37,47,48).
- [ ] T073 [US5] Implement `--verify` and exact five-profile `--aggregate` in `scripts/conformance_evidence.py`, checking predeclared per-profile assignments and common invocation/source/catalog/configuration policy without demanding identical provider/environment hashes; reject non-success required jobs, missing/foreign reports and diagnostic/preparation runs (FR-018,020,021,024; QC-45..47).
- [ ] T074 [US5] Wire full sequential baseline and harness profile in `scripts/validate-conformance.sh` and `scripts/conformance_evidence.py`, using same inventories/evaluator for local and CI, finite total scheduling/cleanup budgets and non-qualifying focused mode; include contributor/tooling/mutation obligations, never recursive self-qualification or automatic failure-erasing retries (FR-016..021; QC-33..47).
- [ ] T075 [US5] Implement `.github/workflows/conformance.yml` with five mandatory isolated profiles and `always()` aggregate, PR/main-push/manual triggers, exact workflow source SHA/history and verified full upstream action SHA pins; `contents: read`, `fail-fast: false`, no `continue-on-error`, secrets/OIDC/publishing/`pull_request_target` or governance changes; 120/210/15-minute job budgets and bounded always-on safe allowlisted upload with seven-day retention (FR-017,020..022; QC-45,46,48).
- [ ] T076 [US5] Measure actual `ubuntu-24.04` artifact runner image/runtime/filesystem/free scratch in `.github/workflows/conformance.yml` and report environment; require >=24 GiB admission and full real transfers; if unavailable, record an explicit runner prerequisite/blocker rather than remove unrelated software, lower coverage or claim CI success (FR-005,016,017,021; QC-10,37,46).
- [ ] T077 [US5] Execute generated-report mutation controls and all-output sanitation/output-flood regressions through `tests/tooling/test_conformance_evidence.py`, `test_conformance_sanitation.py` and `test_conformance_execution.py`; retain intended rejecting/accepting safe witnesses without raw logs and ensure retained live resources block qualification (FR-016,018..020,022; QC-33..44,48).
- [ ] T078 [US5] Execute all five actual CI profiles and aggregate in `.github/workflows/conformance.yml`, verifying each mandatory option and observed job/upload/download status, same catalog/evaluator bytes as local, safe artifacts only and exact source/profile environment assignment; failed/cancelled/missing evidence remains a blocker (FR-017,020,021; QC-45,46).
- [ ] T079 [US5] Recompute support statement from verified local and CI reports through `scripts/validate-conformance.sh --verify` and `--aggregate`; demonstrate altered optimistic summaries, focused mode, stale inputs and untested cross-products cannot qualify despite prior green evidence (FR-014,018,020,023,024; QC-29,38,47).
- [ ] T080 [US5] Update `specs/007-provider-conformance/quickstart.md` and `examples/ProviderConformance/README.md` with implemented commands, actual prerequisites, local/CI reproduction, safe failure/recovery and finite scopes; replace future-command warnings only for delivered behavior and record all remaining limitations honestly (FR-017,023,024; QC-32,37,47,48).

## Phase 8: Polish and cross-cutting completion

**Purpose**: Verify all required work, actual final graph and documentation
without treating task completion as convergence/finalization/merge authority.

- [ ] T081 Obtain required `hoard-architecture-review` of final SDK/binding/host/package graph, common assertion extraction, authority and retained ownership/evidence seams; fix in-scope findings and record review references in `specs/007-provider-conformance/plan.md`, preserving provider independence and all permitted/forbidden paths (FR-002,004..006,013,016,018; QC-02,03,12,27,28,33..36).
- [ ] T082 Run all existing regression entry points from `specs/007-provider-conformance/quickstart.md`: `bash scripts/validate-foundation.sh`, `bash scripts/validate-lifecycle.sh`, `bash scripts/validate-configuration.sh`, `bash scripts/validate-discovery.sh`, `bash scripts/validate-metadata.sh` and `bash scripts/validate-artifacts.sh --evidence <fresh-private-path>`; retain exact commands/results, SDK formatting/analyzers, locked package/source provenance, all prior binaries/scan inventories and witnesses without concurrent input edits (FR-001..013,018,022).
- [ ] T083 Run fresh default locked full baseline and independent verify/aggregate via `scripts/validate-conformance.sh`, after all source fixes/review; prove 192 inherited entries, every CP/version/architecture subvariant, QC-01..48 and all real transfer/recovery/contributor/local-CI obligations with actual settled resources and no unauthorized exclusions; incomplete capacity/ownership/CI is a blocker, not a task pass (FR-001..024; SC-001..008).
- [ ] T084 Run `python3 -m unittest discover -s tests/tooling -v`, repository SDK format/analyzer checks and `git diff --check`; verify tracked lock replay, feature/local documentation links and test-only package graph, recording exact outcomes in `specs/007-provider-conformance/plan.md` rather than relying on task checkmarks (FR-013,018,021,024).
- [ ] T085 Update `README.md`, `docs/DEVELOPMENT.md`, `docs/PROVIDERS.md`, `examples/CustomHost/README.md`, `examples/ProviderConformance/README.md` and affected feature artifacts with actual commands/results, finite support, ownership/recovery and current-versus-planned behavior; explicitly justify unaffected charter/product/architecture/ADR/diagrams/governance/backlog/predecessor/IaC/release/UI documents (FR-014,017,022..024).
- [ ] T086 Audit all requirement/outcome/scenario/edge/QC assignments in `specs/007-provider-conformance/tasks.md` against final input-bound evidence in `specs/007-provider-conformance/plan.md`; mark only verified successful tasks, preserve reviewer checklist ownership and unresolved blockers, push coherent checkpoints immediately and retain draft PR until separately authorized convergence/finalization (FR-001..024; SC-001..008).

## Dependencies and execution order

### Exact task prerequisites

`none` means no task prerequisite. Each row enumerates direct prerequisites;
transitive prerequisites also apply. The Phase 2 completion gate is T018.
Task IDs remain execution-ordered; no forward dependency is required.

| Task | Prerequisites |
| --- | --- |
| T001 | none |
| T002 | T001 |
| T003 | T002 |
| T004 | T002 |
| T005 | T003, T004 |
| T006 | T001 |
| T007 | T005, T006 |
| T008 | T001, T007 |
| T009 | T007 |
| T010 | T009 |
| T011 | T010 |
| T012 | T011 |
| T013 | T008, T012 |
| T014 | T013 |
| T015 | T012, T014 |
| T016 | T005, T015 |
| T017 | T014, T016 |
| T018 | T008, T009, T010, T011, T012, T013, T014, T015, T016, T017 |
| T019 | T018 |
| T020 | T018 |
| T021 | T019 |
| T022 | T021 |
| T023 | T021 |
| T024 | T022, T023 |
| T025 | T024 |
| T026 | T025 |
| T027 | T020 |
| T028 | T027 |
| T029 | T027 |
| T030 | T028, T029 |
| T031 | T030 |
| T032 | T031 |
| T033 | T024, T030 |
| T034 | T024, T030 |
| T035 | T026, T032, T033, T034 |
| T036 | T035 |
| T037 | T019, T020, T036 |
| T038 | T037 |
| T039 | T018 |
| T040 | T018 |
| T041 | T039, T040, T036 |
| T042 | T041 |
| T043 | T042 |
| T044 | T041 |
| T045 | T044 |
| T046 | T035, T043, T045 |
| T047 | T046 |
| T048 | T018, T047 |
| T049 | T038, T048 |
| T050 | T018 |
| T051 | T018 |
| T052 | T018 |
| T053 | T041, T050 |
| T054 | T036, T051 |
| T055 | T015, T054 |
| T056 | T055 |
| T057 | T046, T052, T053, T056 |
| T058 | T048, T057 |
| T059 | T058 |
| T060 | T049, T059 |
| T061 | T038, T060 |
| T062 | T018 |
| T063 | T024, T062 |
| T064 | T036, T057, T063 |
| T065 | T064 |
| T066 | T065 |
| T067 | T066 |
| T068 | T058, T067 |
| T069 | T018 |
| T070 | T018 |
| T071 | T064, T068 |
| T072 | T070, T071 |
| T073 | T069, T072 |
| T074 | T067, T073 |
| T075 | T074 |
| T076 | T075 |
| T077 | T068, T070, T074 |
| T078 | T076, T077 |
| T079 | T037, T047, T059, T066, T078 |
| T080 | T065, T079 |
| T081 | T061, T080 |
| T082 | T081 |
| T083 | T082 |
| T084 | T083 |
| T085 | T049, T060, T080, T084 |
| T086 | T085 |

### Story dependencies and shared files

All story test-writing tasks can start after T018. US1 supplies the packaged
common consumer required by US2/US3 and the metadata adapter required by US4.
US2 and US3 can diagnose their own rows independently, but both use the shared
host. Finish T041 before adding either composition or version fixtures.
US4's CLI wiring follows compatibility profile wiring to serialize the shared
orchestrator. US5 closes independent evaluation and the actual full five-profile
claim after all profile producers exist.

Shared edits have explicit chains:

- `scripts/conformance_execution.py`: T010 -> T011 -> T012, then execution only.
- `scripts/conformance_evidence.py`: T007 -> T013 -> T014 -> T017 -> T035 ->
  T046 -> T057 -> T064 -> T071 -> T072 -> T073 -> T074.
- `scripts/validate-conformance.sh`: T016 -> T017 -> T074.
- `tests/tooling/test_conformance_evidence.py`: T006 -> T018 -> T048 ->
  T058 -> T068; T077 executes, not edits, those completed tests.
- Host composition fixtures: T042 -> T043; ownership fixtures T044 -> T045.
  Distinct fixture files may proceed independently after T041.
- `scripts/conformance_baselines.py`: T015 -> T055.
- Plan evidence: T038 -> T061 -> T081 -> T082 -> T083 -> T084 -> T086.
  Provider/compatibility guide: T038 -> T049 -> T060 -> T085.
  Contributor guide: T065 -> T080 -> T085.

No edits to fingerprinted sources/scripts/tests/workflow/locks may overlap an
acceptance run. Parallel execution needs genuinely isolated immutable source
snapshots, feeds/caches/stores/ledgers and sufficient resources; separate output
directories alone do not supply isolation. Large artifact work stays serial.
Default local baseline and final predecessor checks run sequentially. Finish
all requested implementation tasks in one implementation-stage invocation
unless blocked; these increment boundaries are not renewed approval requests.

## Parallel examples

| Story | Safe different-file work after prerequisites |
| --- | --- |
| US1 | T019 with T020 after T018; T022 with T023 after T021; T028 with T029 after T027 |
| US2 | T039 with T040 after T018; T042 and T044 after T041 use distinct fixtures |
| US3 | T050, T051 and T052 after T018; no simultaneous shared orchestrator edits |
| US4 | T062 can run beside earlier story tests after T018; adapter T063 follows metadata extraction |
| US5 | T069 and T070 after T018, independent of profile implementation; T068 waits for generated real reports |

Do not parallelize a marked task with its own prerequisites. T003/T004 are
independent after T002; T006 is independent after T001; T009 and T008 use
different files after T007.

## Requirement and proof traceability

| Requirements | Implementation tasks | Focused proof tasks / obligations |
| --- | --- | --- |
| FR-001 | T001, T007, T008, T035 | T006, T018, T037; QC-01,05 |
| FR-002 | T007, T021..024, T027..030, T036 | T019, T020, T034, T037; QC-02..05 |
| FR-003 | T022, T023, T026, T028, T029, T032 | T026, T032, T037; QC-02,03,08,11 |
| FR-004 | T021..026, T033 | T019, T026, T033, T037; QC-06..08,12 |
| FR-005 | T027..033 | T020, T032, T033, T037; QC-09..12 |
| FR-006 | T041, T045, T046 | T039, T040, T047; QC-13,21 |
| FR-007 | T042, T046 | T039, T047; QC-14,15 |
| FR-008 | T042, T043, T046 | T039, T047; QC-15,16 |
| FR-009 | T010..012, T044..046 | T009, T040, T047, T048; QC-07,17..19,21,34 |
| FR-010 | T043, T053 | T039, T047, T050, T059; QC-20,24 |
| FR-011 | T053, T057 | T050, T058, T059; QC-22..24 |
| FR-012 | T015, T054..056 | T051, T058, T059; QC-25,26 |
| FR-013 | T002..005, T036, T057 | T052, T059, T081; QC-27,28 |
| FR-014 | T038, T049, T060, T072 | T059, T079; QC-29,47 |
| FR-015 | T063..065 | T062, T066; QC-30..32 |
| FR-016 | T010..012, T017, T074 | T009, T018, T067, T077; QC-33..36 |
| FR-017 | T012, T017, T065, T075, T076 | T067, T069, T078; QC-37,46 |
| FR-018 | T013..015, T025, T031, T035, T046, T055, T057, T071 | T048, T058, T068, T077; QC-38..41 |
| FR-019 | T034, T042, T056, T063 | T034, T039, T050..052, T059, T066, T077; QC-04,14,22,26..28,31,43 |
| FR-020 | T007, T008, T014, T071..074 | T006, T048, T058, T068, T069, T077; QC-39..44,46 |
| FR-021 | T073..076 | T069, T078, T079; QC-45,46 |
| FR-022 | T011, T013, T014, T025, T031, T046, T072, T075 | T009, T040, T068, T070, T077; QC-21,35,44,48 |
| FR-023 | T038, T049, T060, T065, T072, T080 | T067, T079; QC-29,37,47 |
| FR-024 | T017, T065, T072..074, T080, T085 | T066, T067, T079, T083..086; QC-30..32,35..37,47,48 |

| Outcome | Closure tasks |
| --- | --- |
| SC-001 | T019..038, T083; exact inherited cases/witnesses, not count alone |
| SC-002 | T039..049, T083; all CP subvariants and independent observations |
| SC-003 | T050..061, T083; every version/source/binary/architecture pair |
| SC-004 | T026, T032, T033, T067, T076, T079, T083; real recovery/transfer and exclusions |
| SC-005 | T062..067, T080, T083; documented clean-checkout package-only journey |
| SC-006 | T068..079, T083; generated controls, strict mutations and CI parity |
| SC-007 | T009..018, T040, T044..048, T067, T070, T077, T083; bounded safe actual ownership |
| SC-008 | T065, T071..080, T083..086; reproducible exact scope and no false qualification |

All QC-01..48 have focused tasks above; the inherited cases, 23 story scenarios
and 14 edges retain their mappings in [acceptance](contracts/acceptance.md#outcome-scenario-and-edge-coverage).
No group-level mapping permits omission of a named subvariant.

## Implementation strategy

1. Complete safe setup/foundations and seal genuine old baselines before any
   candidate package build. Test helpers are not product APIs.
2. Deliver US1 first as the MVP: both complete category profiles, package-only
   unchanged consumers and assertion-level metadata/artifact red/green proof.
   This is category-scoped evidence only, not complete F-07 qualification.
3. Add the finite composition, compatibility and contributor increments, keeping
   each story's independent diagnosis and unchanged common contract.
4. Close independent evaluation, all five CI profiles and safe reports. A
   missing runner capacity prerequisite, failed job or retained live owner is
   a genuine blocker, never permission to reduce mandatory coverage.
5. Obtain final actual-graph architecture review, run all existing checks and
   fresh complete baseline, then synchronize docs and evidence. Keep failed
   attempts visible; mark only verified tasks complete.

No deployment/demo service, provider/package publication, release/tag, cloud
apply, repository setting change or merge is part of these tasks. Implementation
completion schedules a separate convergence invocation; it does not run later
stages or complete the feature automatically.
