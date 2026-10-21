# Tasks: Provider Configuration and Activation Validation

**Input**: Design documents from `specs/003-provider-configuration/` (F-03).
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md),
[research.md](research.md), [data-model.md](data-model.md),
[operator format](contracts/configuration-format.md),
[Hosting API](contracts/hosting-api.md),
[acceptance matrix](contracts/acceptance.md), and [quickstart.md](quickstart.md).

**Implementation-stage status**: All 69 tasks are complete. The initial
T001..T020 source-resolution increment is historical; see the
[complete implementation evidence](plan.md#complete-implementation) for actual
results, grouped-file placement, review corrections and platform limitations.
This checkpoint ends at `converge / ready`; convergence, finalization, PR
readiness, merge and backlog completion remain separate authorizations.
The built-in requirements
checklist remains 16/16; the separately requested assisted requirements review
of [configuration](checklists/configuration.md) and [safety](checklists/safety.md)
remains 20/20 each. Their reviewer-owned bytes and all specification/design
artifacts were unchanged by task generation. That stage neither approved
checklists nor authorized implementation. Read-only analysis subsequently
passed; the current invocation completes only implementation.

**Tests**: Explicitly required by FR-026, SC-001..SC-008, every story's independent
test, and CFG-01..CFG-36. Write focused paired permitted/rejected tests first,
record the intended red result, then implement and record green. Missing APIs
may initially produce compile failures, but these do not prove runtime
rejection, resource retention or safe output. Empty selections, skipped proof,
unobserved test tasks and missing evidence cannot pass.

**Organization**: Shared setup and bounded ownership primitives precede five
story phases in specification priority order, then cross-cutting acceptance.
Independent story tests observe their own outcomes using fixtures; they do not
create five evaluators or bypass shared source/validation/lifecycle prerequisites.

## Format: `[ID] [P?] [Story] Description`

- Every implementation task has a status checkbox, sequential ID and exact
  repository-relative destination paths. Story phases require `[US1]`..`[US5]`;
  setup, foundational and polish tasks have no story label.
- `[P]` means disjoint files within the explicitly identified ready group,
  after all listed prerequisites. It is not permission to launch agents or a
  workflow engine. The dependency table, not numeric adjacency, decides readiness.
- FR, SC and CFG references point to the linked requirements and acceptance
  contract. Original destination filenames remain planning instructions; the
  linked implementation evidence records cohesive grouping rather than a file
  for every ancillary type.

## Path Conventions

Production changes stay in `src/Hoard.Hosting/Configuration/` and additive
integration with existing Hosting lifecycle/composition ownership. Do not change
Abstractions/Core/Application public APIs, provider dependency direction,
F-01/F-02 signatures, the existing composition acceptance algorithm, framework
requirements or production dependencies. No new schema framework, product Host,
management endpoint, UI, real provider, network listener or cloud resolver.

Extend existing xUnit projects and local lifecycle fixtures. New configuration
tests belong beside existing composition tests; ordinary tests must remain
usable by the retained foundation/lifecycle runners. Required package/binary
evidence belongs to the focused orchestrator, not a new mandatory manifest for
every ordinary xUnit test. Reuse deterministic lifecycle time/test support where
appropriate without changing existing scenario meaning.

`scripts/validate-configuration.sh` and `scripts/configuration_evidence.py`
were not delivered by task generation. Implementation now supplies complete
CFG-01..36 acceptance and explicitly partial modes; missing or incomplete
scenario/package/platform evidence still fails closed.
Reuse suitable existing evidence preparation helpers without recursive suite
invocations, weakened scans or product-to-test imports. Retained binaries,
private source/proposal/secret files, feeds, manifests and outputs belong in an
owner-private resolved temporary workspace, never Git. Track necessary reviewed
lockfiles; bootstrap only after manifest changes or a missing-dependency failure,
then replay fresh locked acceptance. Standalone package consumers/child fixtures
must not inherit hidden source ProjectReferences or enter the product solution.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare fixture-only proof and fail-closed orchestration using the
existing framework and dependencies. No configuration acceptance claim yet.

- [X] T001 [P] Add `tests/integration/Hoard.Composition.Tests/ConfigurationTestHarness.cs` using existing `LifecycleTestTimeProvider.cs`/lifecycle instrumentation: copied environment dictionaries, invented source/secret payloads, owner/phase event and construction/route/worker/connection/read counters, safe log/telemetry capture, input-disposal probes and controllable synchronous/async/cancellation barriers; teardown must release and observe every held activity without personal credentials or network listeners.
- [X] T002 [P] Write failing regressions in `tests/tooling/test_configuration_evidence.py` for missing/empty/duplicate or incomplete CFG selections, nonzero/timed-out subprocesses, stale/nonlocal packed inputs, changed retained binaries, missing platform publication proof, default lock mutation and cleanup limited to its own resolved workspace; use synthetic temporary inputs rather than recursively running acceptance.
- [X] T003 Introduce `scripts/validate-configuration.sh` and `scripts/configuration_evidence.py` with explicit prerequisites, bounded subprocesses, private workspace ownership, sanitized fail-fast errors, intended red/green evidence capture and explicit `--update-locks` followed by default locked replay; reuse existing preparation helpers and fail incomplete acceptance until the later case/package/platform sections exist (CFG-36).
- [X] T004 [P] Add standalone baseline sources/locks in `tests/fixtures/configuration/LegacyOptions/LegacyOptions.csproj`, `LegacyOptionsProvider.cs`, and `tests/fixtures/configuration/LifecycleConsumer/LifecycleConsumer.csproj`, `Program.cs`, with isolated `Baseline/packages.lock.json` files: an option-bearing metadata/artifact provider using only pre-F-03 Abstractions and a pre-F-03 F-02 lifecycle consumer. Identify immutable baseline revisions from merged Git history, compile into the private workspace before new Hosting behavior, retain hashes/dependencies without rebuilding those binaries later, and preserve the existing F-01 registration binary proof (CFG-33).

**Checkpoint**: Harness and provenance inputs exist; an incomplete runner fails,
not prints passing configuration acceptance.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish metadata, private inputs, safe records and bounded
pre-composition ownership shared by every story. All stories wait for T012.

- [X] T005 [P] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationContractTests.cs` for inert option registration, descriptor-field bijection, duplicate/orphan associations, immutable defensive copies, private proof construction, safe display/result shapes, invalid trusted limits/budgets before any callback, and unchanged opt-out registration/lifecycle APIs; test malformed/default collections and metadata boundaries, not trivial getters (CFG-09, CFG-17, CFG-21).
- [X] T006 Define `src/Hoard.Hosting/Configuration/HoardModuleConfiguration.cs`, `HoardOptionField.cs`, `HoardOptionValidator.cs` and `HoardModuleConfigurationExtensions.cs`, plus metadata collection in `src/Hoard.Hosting/HoardBuilder.cs`: preserve "Exactly one association per configurable registered provider; no factories/construction/I/O" and "Bijective with descriptor keys; defaults only apply when explicitly present in defaults source". Record current/supported option versions, finite fields/rules, required/secret flags, ordinary constraints and safe examples; require canonical key/flag agreement, no secret defaults, implicit empty contracts only for zero-field descriptors, and invoke no delegate or constructor during registration (FR-009, CFG-09).
- [X] T007 Define private immutable source/assignment/input models in `src/Hoard.Hosting/Configuration/HoardConfigurationInput.cs`, `ConfigurationSource.cs`, `SettingIdentity.cs`, `SourceAssignment.cs` and trusted `HoardConfigurationOptions.cs`: source invariant "One of each kind; one explicit file; private path/text never reported"; identity "ASCII key segments; metadata-bijective identity; values are not normalized"; assignment "Unique in that source, even if later overridden; structural shape checked before merging". Copy in-memory documents/argv/environment adapters, redact display, and enforce plan defaults of 1 MiB UTF-8 per document/overlay, depth 16, 4,096 canonical assignments, 256 enabled IDs, 256 fields/module, 16 KiB ordinary strings/reference locators, 64 KiB secrets and 100 diagnostics. Validate positive finite host overrides before work (CFG-05).
- [X] T008 Define closed `src/Hoard.Hosting/Configuration/HoardConfigurationDiagnostic.cs`, `HoardConfigurationReport.cs` and `HoardConfigurationEvaluation.cs`, plus a non-publicly-constructible, unusable-until-T029 proof declaration in `HoardValidatedConfiguration.cs`, with "bounded safe identity/category/source/phase/rule/action/correlation" and "Success only after all checks; failure has no composition proof; frozen returned outcome". Use host-owned codes/action templates, registered metadata identities or generated ordinals, immutable provenance/status reports, bounded live supervision observations and omitted count; no raw values, paths, hashes, source text, collaborator messages/inner exceptions or value-bearing automatic serialization. Emit only bounded phase/category/source metric labels, not correlation/secret dimensions (FR-024, CFG-17).
- [X] T009 [P] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationCoordinationTests.cs` with virtual time for one absolute deadline, capped dispatch waits, synchronous prefixes, caller cancellation without inline collaborator notification, slow/throwing notification, retained buffers/stream/CTS/secret inputs, bounded disposal and late success/fault observation; include cancellation immediately before success and require frozen outcomes/no later dispatch or activation (CFG-18..20).
- [X] T010 Implement `src/Hoard.Hosting/Configuration/ConfigurationSupervisor.cs`, `ConfigurationDeadline.cs` and `PendingConfigurationActivity.cs` following existing F-02 supervision prior art without introducing a lifecycle/root owner: 30-second absolute outer/five-second per-dispatch defaults capped by remaining time, monotonic injected TimeProvider, serial full-callback dispatch and terminal admission closure before supervised cancellation notification. Pending activity "Outlives bounded wait when necessary; never represented as terminated/released"; record originating owner/phase, observe faults before release, retain in-use inputs through notification, and make explicit disposal report pending rather than block or dispose live resources (FR-016, CFG-18..20).
- [X] T011 Implement `src/Hoard.Hosting/Configuration/HoardModuleOptions.cs`, `HoardSecretValue.cs` and `OwnerOptionsLease.cs` with fixed typed ordinary values/secret handles for one owner: "No whole-host access; no reread; no public automatic serialization or value-bearing ToString". Distinguish optional absence, reject secret access through ordinary getters, make sensitive access explicit and display/debug output redacted, retain inputs until the actual last supervised user releases them, and document best-effort clearing rather than managed-memory isolation (FR-015, FR-017, CFG-16, CFG-20..22).
- [X] T012 Run the contract/coordination/ownership primitive tests in `tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj` and T002 tooling regressions through the bounded preparation/runner in `scripts/configuration_evidence.py`; record intended red-to-green evidence, no held test activities, invalid-option early rejection and unchanged legacy behavior without claiming full CFG acceptance.

**Checkpoint**: Safe shared primitives are usable; no successful configuration
proof or configured activation is exposed before the remaining gates exist.

## Phase 3: User Story 1 - Know Which Configuration Will Be Used (Priority: P1)

**Goal**: Resolve deterministic, inspectable sources without constructing
providers or resolving secrets.

**Independent Test**: Supply all four fixture source levels and inspect only
source-resolution results: exact winner/provenance, whole-selection replacement,
keyed option retention, no hidden defaults, and structural failures even in
discarded/disabled input. Source-only inspection is not a successful activation
proof. Covers US1-1..4, FR-001..005/024 and CFG-01..05/26.

### Tests for User Story 1

- [X] T013 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationSourceTests.cs` for repeated four-level precedence/provenance, optional absence versus explicit unavailable file/empty environment, exactly one file selector including programmatic/CLI conflict, OS case-equivalent `HOARD_CONFIG` collisions, malformed/reserved Hoard argv versus unrelated host args, and bounded source reads with zero secrets/constructors (CFG-01, CFG-05).
- [X] T014 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationStructureTests.cs` for decoded escaped/case-equivalent duplicates, repeated IDs/capabilities/CLI paths, unknown/unsafe keys, null/comments/trailing commas/coercion/nested objects, every exact/over input limit and malformed secret/address representations in overridden/disabled occurrences; pair safe public addresses and valid references without reading targets (CFG-02, CFG-05, CFG-15, CFG-35).
- [X] T015 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationMergeTests.cs` for whole enabled/identity/capability array and authoritative scalar replacement, keyed option/option-version retention, atomic reference-object replacement, explicit empty selections/values, invalid Defaults and no post-merge metadata default or previous-state recovery; distinguish overridden representable semantic invalidity from structural rejection (CFG-03..04, CFG-10).
- [X] T016 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationVersionTests.cs` for independent mandatory integer version 1 in Defaults/every supplied file, missing/malformed/unsupported/newer versions, forbidden overlay version and inability to repair a bad document via precedence; keep option-version semantic tests for US2 and synthetic conversion for US5 (CFG-26).

### Implementation for User Story 1

- [X] T017 [US1] Implement bounded occurrence-aware parsing in `src/Hoard.Hosting/Configuration/ConfigurationParser.cs` and `ConfigurationNames.cs`: ASCII alphanumeric key segments with single internal dot/hyphen, alphanumeric ends, maximum 128 characters and ASCII lowercase key identity after JSON escape decoding; preserve exact F-02 lowercase module-ID value policy rather than normalize values. "Ordinary option values are string, Boolean, Int64 or an address string." Apply known-key/type/duplicate/reference/credential-address structural checks to every occurrence; reference grammar is closed env/file kind/target only, and address user-info/query/fragment are always rejected, never reflected (FR-002, FR-013, CFG-02, CFG-05, CFG-15).
- [X] T018 [US1] Implement `src/Hoard.Hosting/Configuration/ConfigurationSourceReader.cs` with explicit versioned Defaults, optional one explicit JSON file, one `HOARD_CONFIG` JSON overlay and `--hoard:<path>=<JSON-value>` leaf assignments; reject overlay versions, repeated/empty/unreadable/conflicting file selectors and unknown reserved args. Enumerate case-equivalent overlay names, preserve optional absence, extract Hoard args before generic-host parsing, bound reads/allocation under T010, and never read appsettings/user-secrets/UI state or selected secret targets (FR-001, FR-021, CFG-01, CFG-05, CFG-26).
- [X] T019 [US1] Implement `src/Hoard.Hosting/Configuration/ConfigurationMerger.cs` and `EffectiveConfiguration.cs`: "No reload or mutable source references; private values separated from safe view". Freeze whole-selection replacements, individual owner option leaves/option versions, atomic reference objects, explicit emptiness and winning source kind at command line > environment > file > defaults; validate all source structures first, never materialize informative defaults or revive discarded values (FR-003..005, CFG-01..04).
- [X] T020 [US1] Wire internal source resolution/inspection in `src/Hoard.Hosting/Configuration/ConfigurationSourceResolution.cs` using T017..T019 and safe T008 reports, without constructing a public successful proof or calling providers/secrets; run T013..T016 and the applicable CFG-17 output assertions through `scripts/configuration_evidence.py`, recording deterministic paired outcomes and bounds as the source-only MVP checkpoint.

**Checkpoint**: US1's source-resolution MVP is independently observable, not a
runnable cache or authorization to activate an incompletely checked selection.

## Phase 4: User Story 2 - Activate Only a Valid Intended Composition (Priority: P1)

**Goal**: Submit only valid intended selections/ordinary options to the existing
composition and lifecycle authorities; preserve disabled isolation and opt-out
compatibility.

**Independent Test**: With secret-free instrumented fixture contracts, pair valid
multiple protocol/identity selections with every rejection; observe zero
construction/secret reads before acceptance, disabled zero events and readiness
decided solely by F-02. Secret-bearing success is added by US3, not faked here.
Covers US2-1..5, FR-006..012/025 and CFG-06..12/21..22/35.

### Tests for User Story 2

- [X] T021 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/ConfiguredSelectionTests.cs` pairing actual F-02 `ValidateComposition` results for missing/unknown registrations, category/authority cardinality, enablement/identity disagreement, declaration/version/prerelease/capability/dependency/cycle rejection and disabled/optional compatibility; assert the existing activation order, no auto-enablement/substitution/download/listener and remapped unknown IDs/path elements (CFG-06..08, CFG-17, CFG-35).
- [X] T022 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationOptionTests.cs` for inspectable inert contracts, missing/orphan/duplicate/flag/key collisions, missing configured adapter, public required/type/range/allowed-value/address/cross-field/version rules, malformed validator results and overridden semantic versus structural errors; ensure public context exposes only owner ordinary values/reference presence and no I/O/constructors (CFG-09..10, CFG-12, CFG-26).
- [X] T023 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationDisabledTests.cs` for registered disabled incompatible ranges, absent required options, unsupported integer option versions and syntactically valid inaccessible references yielding zero public/secret callbacks, reads, constructors/routes/workers/connections; malformed/unknown disabled input or association still rejects, and any owner's public rejection prevents all secret dispatch (CFG-08, CFG-11..12).
- [X] T024 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationProofTests.cs` for foreign/stale/disposed/failed proof, service/contract mutation, concurrent consumption/disposal/legacy-compose races, cancelled-before-dispatch and exactly one ownership transfer or release; rejected paths construct nothing, an opt-in enabled registration requires configuration even with a bare legacy composition, and opt-out F-02 callers remain unchanged (CFG-21).
- [X] T025 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/ConfiguredDeliveryTests.cs` for owner-only ConfigureOptions before ConfigureServices in F-02 ComposingServices, normal TestServer readiness/admission/stop, thrown/blocked delivery, retained input/root/prerequisite resources and notification races; release held work and prove no late ready result or deferred provider/root disposal (CFG-21..22).

### Implementation for User Story 2

- [X] T026 [US2] Add `src/Hoard.Hosting/Configuration/ConfigurationCompositionBridge.cs`: ProviderSelection invariant "Identity set agrees exactly with enabled Identity category; F-02 validates remaining graph". Translate exact effective selections/capability records into `HoardStartupSelection`, call existing `ValidateComposition` without duplicating its graph/range/cardinality algorithm, inspect contract/adapter metadata without construction and map every lifecycle ID/dependency-path element against known metadata before safe reporting (FR-006..009, CFG-06..09, CFG-17).
- [X] T027 [US2] Implement `src/Hoard.Hosting/Configuration/ConfigurationOptionChecker.cs` and `HoardOptionCheckContext.cs`/`HoardOptionCheckResult.cs`: enabled-only required/range/allowed-value/absolute HTTP(S)/cross-field checks, current option version 1 required for nonempty active contracts, no hidden defaults, disabled operational/version skips, and supervised Public callbacks for every active owner before any secret phase. Return only declared field/rule/status identities; unknown/malformed callback results become InvalidCheckResult without arbitrary text or provider I/O (FR-010..012, CFG-09..12, CFG-26).
- [X] T028 [US2] Add `src/Hoard.Hosting/Configuration/HoardConfigurationExtensions.cs` and `ConfigurationEvaluator.cs` for the planned `EvaluateConfigurationAsync(input, platformVersions, lifecycleOptions, configurationOptions, cancellationToken)` sequence: T020 source resolution, T026 real gate, all T027 public checks, then required secret/check completion and only then a private proof. At this increment accept secret-free selections only; unresolved active secrets fail explicitly, never produce an intermediate successful proof. Freeze terminal results and close dispatch under T010 before returning (FR-012, CFG-12, CFG-18..21).
- [X] T029 [US2] Implement `src/Hoard.Hosting/Configuration/HoardValidatedConfiguration.cs` and `ConfigurationOwnershipGate.cs`: "Not publicly constructible; consumption atomic; stale/failed/disposed proof cannot activate". Hold the private composition, exact builder/service/contract snapshot and owner inputs; atomically arbitrate freshness, cancellation, consume versus disposal/legacy consumption, no pending work and once-only transfer to the existing F-02 lease before construction. Unused proof disposal releases only safe unused inputs, with explicit pending outcomes when required (CFG-21).
- [X] T030 [US2] Add `src/Hoard.Hosting/Configuration/IHoardConfiguredModule.cs` and the configured overload in `src/Hoard.Hosting/Lifecycle/HoardServiceCompositionExtensions.cs`; integrate owner-input retention into existing `HoardServiceComposition.cs`/`ActivationLedger.cs` and supervised delivery into existing `HoardLifecycleCoordinator.cs` as needed. Share the old internal compose/ledger/root implementation, reject enabled opt-in legacy bypass as ConfigurationRequired, call ConfigureOptions immediately before ConfigureServices under the same F-02 phase/deadline, and introduce no second root/readiness/stop authority (FR-008, FR-018, CFG-21..22).
- [X] T031 [US2] Run T021..T025 plus source regressions through `scripts/configuration_evidence.py`, using secret-free valid counterparts, actual F-02 failure categories/order and configured TestServer lifecycles; record intended red/green, zero rejected/disabled events and retained opt-out behavior without claiming secret-bearing or package-only acceptance yet.

**Checkpoint**: Secret-free valid configuration reaches F-02's sole readiness
gate; no missing secret can be mistaken for a permitted empty credential.

## Phase 5: User Story 3 - Supply Secrets Without Leaking Them (Priority: P1)

**Goal**: Complete local env/file reference resolution and owner-only fixed
delivery with safe failures, bounded pending work and no leaked payloads.

**Independent Test**: Use invented dictionary/file targets, actual local-file
counterparts, faulting validators/readers and virtual-time barriers. Capture
normal results/logs/reports/telemetry and lifecycle counters: exact owner values
on success, zero seeded payloads and activation on rejection, retained in-use
resources and safely observed eventual faults. Covers US3-1..5,
FR-013..017/024..026 and CFG-13..22.

### Tests for User Story 3

- [X] T032 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/EnvironmentSecretTests.cs` for exact OS-semantic target naming, per-owner success/reuse and missing/empty/whitespace-only/denied/oversize failures with no alternate lookup; include `[A-Za-z_][A-Za-z0-9_]{0,127}` boundaries and overlay-name collision isolation using invented dictionaries, never developer credentials (CFG-13, CFG-16).
- [X] T033 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/FileSecretTests.cs` for absolute local regular files and deployment symlinks, strict UTF-8 without BOM/NUL, at most one trailing LF/preceding CR removal, exact/over 64 KiB, empty/whitespace/denied/missing/invalid text and directory/device/pipe rejection or bounded behavior; pair simulated denied reads with actual local-file proofs on each claimed platform (CFG-14).
- [X] T034 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationDiagnosticTests.cs` seeding values/locators into unknown regex-valid keys/selections/capabilities/dependency paths/versions, file errors, exceptions and malformed callback results; inspect normal configured-host logs/errors/results/reports/preview-ready report types/telemetry/display for zero payload, safe phase/source/rule/action/correlation, 100-diagnostic cap/omitted count and bounded metric labels (CFG-17).
- [X] T035 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationPendingTests.cs` holding full synchronous/async validator/read/resolver prefixes, cancellation at every phase/success boundary and slow/throwing notification; prove exact virtual outer/capped budgets, no next dispatch, bounded Dispose with retained input/stream/CTS/secrets, once-only safe late faults and frozen outcomes, then release/observe all held work (CFG-18..20).
- [X] T036 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/SecretOwnershipTests.cs` for fixed per-owner snapshots after target mutation, explicit independently resolved shared references, absent optional secret versus empty reference/literal, forbidden ordinary accessor/serialization and redacted display. Extend blocked configured-delivery/notification consume-dispose races with real secret handles and assert exactly one release authority, retained inputs and no deferred root/provider disposal (CFG-16, CFG-20..22).

### Implementation for User Story 3

- [X] T037 [P] [US3] Implement `src/Hoard.Hosting/Configuration/EnvironmentSecretReader.cs` using the trusted injected snapshot/read adapter and exact OS name lookup, with closed env kind, documented target grammar, finite size check, immutable exact nonempty value and no fallback/interpolation/recursive expansion or implicit second lookup (FR-013..017, CFG-13).
- [X] T038 [P] [US3] Implement `src/Hoard.Hosting/Configuration/FileSecretReader.cs` with absolute local targets, supported-platform regular-file checks, permitted deployment-owned symlinks, single open/bounded async reads under T010, strict UTF-8/BOM/NUL/newline policy and host-owned safe errors; retain a pending stream until its actual read/notification finishes, not until a timed wait returns (FR-014, FR-016, CFG-14).
- [X] T039 [US3] Complete `src/Hoard.Hosting/Configuration/ConfigurationSecretResolver.cs` and `ConfigurationEvaluator.cs`: SecretReference invariant "Closed grammar, no expression; absent optional secret differs from empty literal/reference". After all owners pass public checks, resolve active owner fields once, stop on first failure, then run supervised Secrets callbacks with owner-only handles; disabled fields never resolve. Only full success can create T029's proof; reports/conversion serialization never receive resolved material (FR-012..017, CFG-11..16).
- [X] T040 [US3] Complete safe event/failure mapping in `src/Hoard.Hosting/Configuration/HoardConfigurationDiagnostic.cs`, `HoardConfigurationEvaluation.cs` and `ConfigurationSupervisor.cs` for resolver/check/cancellation/late failures, including remapping even regex-valid unknown F-02 identities and nested paths. Observe originating task/owner/phase faults once before release, never store raw exceptions in public objects or logging calls and never revise terminal results or create high-cardinality metrics (FR-024, CFG-17..20).
- [X] T041 [US3] Complete sensitive retention/transfer in `src/Hoard.Hosting/Configuration/OwnerOptionsLease.cs`, `ConfigurationOwnershipGate.cs` and existing `src/Hoard.Hosting/Lifecycle/HoardServiceComposition.cs`/`HoardActivityTracker.cs`: unused evaluation/proof disposal and configured consumption share the atomic gate, transfer once before adapters, retain each owner's inputs through pending F-02 delivery/cancellation work and release only after actual last use; no deferred provider/root cleanup after a bounded return (FR-015..016, CFG-20..22).
- [X] T042 [US3] Run T032..T036 with preceding story regressions through `scripts/configuration_evidence.py`; record paired env/file success/failures, real local-platform reads, zero seeded output, exact virtual-time and separately stated real scheduler tolerance, no late activation, and released/observed held test work. This is the secure configuration increment, not full conversion/package support.

**Checkpoint**: Both supported local secret kinds work with fixed owner-scoped
delivery, bounded truthful failure and no normal-output disclosure.

## Phase 6: User Story 4 - Change Settings Through an Explicit Restart (Priority: P2)

**Goal**: Prove fixed running state, same-built bundled switching, explicit custom
package addition and coherent manual recovery without previous-value fallback.

**Independent Test**: Run package-only baseline/custom LifecycleHost fixtures
through TestServer before and after file/environment/secret edits. Switch
bundled protocols without rebuilding; add the separate artifact package only in
the custom build; reject invalid restart and explicitly restore compatible
inputs. Covers US4-1..4, FR-018..020/026 and CFG-23..25/31..33.

### Tests for User Story 4

- [X] T043 [P] [US4] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationRestartTests.cs` editing source bytes, environment, owner settings, selections and secret targets after valid start; assert no running change/reread, F-02 stop followed by a newly evaluated lifecycle sees the intended replacement, and old disabled callbacks/routes/workers/connections remain zero (CFG-23).
- [X] T044 [P] [US4] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationDistributionTests.cs` consuming packed baseline/custom proof inputs: two bundled protocol selections work with the same baseline binary, baseline lacks the second artifact dependency, custom addition requires that independent package/registration and rebuild/redeploy/restart, no Core or concrete cross-provider edit; fail explicitly for missing proof inputs (CFG-24, CFG-32..33).
- [X] T045 [P] [US4] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationRecoveryTests.cs` for invalid replacement/absent custom module with zero prior-value reuse/anonymous/store substitution, explicit fresh coherent previous configuration/reference/distribution recovery, no saved resolved-secret rollback and no implied reversal of provider data (CFG-25, CFG-31, CFG-35).

### Implementation for User Story 4

- [X] T046 [US4] Extend fixture descriptors/adapters in `tests/fixtures/lifecycle/Protocol.One/ProtocolOneModule.cs`, `Protocol.Two/ProtocolTwoModule.cs`, `Metadata/MetadataProvider.cs`, `Artifact.One/ArtifactOneProvider.cs` and `examples/LifecycleHost/Adapters/MetadataModule.cs`, `ArtifactOneModule.cs`, `ArtifactTwoModule.cs` for described public/secret options and inert owner mapping. Keep metadata/artifact packages Abstractions-only and prior F-02 default journeys valid; add a new host-side `examples/LifecycleHost/Adapters/LegacyOptionsModule.cs` to configure the unchanged T004 option-bearing binary without recompiling it (CFG-16, CFG-24, CFG-33).
- [X] T047 [US4] Extend `examples/LifecycleHost/Program.cs`, `LifecycleHost.csproj`, `Custom/LifecycleHost.Custom.csproj` and necessary reviewed locks with explicit configured baseline/custom TestServer journeys and fixture JSON under `examples/LifecycleHost/Configuration/`; baseline bundles two protocols/one artifact, custom alone includes the second artifact. Extract reserved args before generic-host setup, use fresh evaluations on restart, preserve existing journey selectors/counts and never add a real listener or source ProjectReference package escape (CFG-23..25, CFG-33).
- [X] T048 [US4] Update `examples/LifecycleHost/README.md` with actual fixture configuration/reference creation, fixed-state semantics, bundled no-rebuild switch versus custom include/register/rebuild/redeploy/restart, explicit invalid-replacement recovery and coherent versions/references/data prerequisites; never publish a credential, generated secret rollback file or production cache/conformance claim (FR-018..020, CFG-24..25, CFG-31, CFG-34).
- [X] T049 [US4] Add package-only restart/distribution/old-provider adapter execution to `scripts/configuration_evidence.py` and run T043..T045 plus configured host journeys using locked fresh-cache packages; verify unchanged baseline binary/provider hashes, no custom artifact in baseline assets, exact nonempty journey inventory and zero Core/cross-provider changes, recording CFG-23..25/32..33 evidence.

**Checkpoint**: Both distribution journeys and explicit recovery are proved with
fixtures; no package download/hot swap or provider data rollback is implied.

## Phase 7: User Story 5 - Upgrade Configuration Without Losing the Original (Priority: P2)

**Goal**: Deliver explicit synthetic-only conversion with secret-free preview,
exact approval/full validation and original-preserving complete fresh output.

**Independent Test**: Preview/apply the documented fixture-v0 mapping, compare
meaning and original bytes, reject unsupported/unmappable/stale sessions, and
interrupt a child process at publication boundaries. Original is recoverable;
final output is absent or complete, with truthful pending outcomes. Covers
US5-1..4, FR-021..023/026 and CFG-26..31.

### Tests for User Story 5

- [X] T050 [P] [US5] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationConversionPreviewTests.cs` for exact synthetic root/option/reference preservation, all six required fields, unknown/omitted/unversioned/YAML/unsupported option-version rejection and no provider/access widening; original bytes unchanged, zero secret reads/constructors and safe category-only changes without raw proposal, digest or locator (CFG-26..27, CFG-31).
- [X] T051 [P] [US5] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationConversionApprovalTests.cs` for unapproved/reused/disposed session, changed original/proposal/builder/registry/contracts/mapping/destination and full validation failure including unavailable secret; approved apply has no ambient overlays or activation, persists original references not values and requires a separately validated next start (CFG-28).
- [X] T052 [P] [US5] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationPublicationTests.cs` using real owner-private local directories for exclusive private same-directory staging, flush/close, no-clobber success/existing/racing destination and source alias/hardlink/symlink preservation; output is complete valid version 1 or absent, original bytes never change, and only tested local OS/filesystems can claim support (CFG-29).
- [X] T053 [P] [US5] Write failing `tests/integration/Hoard.Composition.Tests/ConfigurationInterruptionTests.cs` for write/flush/close/publish faults, cancellation before dispatch/at atomic commit, blocked publication returning PublicationPending and safe later actual outcome without rewriting returned results; add child-process barrier expectations for staged/flush/pre-/post-publication termination, no partial final file and targeted staging recovery with all held test tasks observed (CFG-30).

### Implementation for User Story 5

- [X] T054 [P] [US5] Implement `src/Hoard.Hosting/Configuration/Conversion/FixtureV0Mapping.cs` for only explicit `configurationversion: "fixture-v0"` to integer 1, renaming enabled/metadata/artifact/identities/capabilities/providers to enabledmodules/metadatamodule/artifactmodule/identitymodules/requiredcapabilities/modules. Require all six roots, preserve exact explicit selection/option/reference meaning and reject unknown/unmappable/access-widening input; startup remains version-1-only and never converts automatically (FR-021..022, CFG-26..27).
- [X] T055 [US5] Implement `src/Hoard.Hosting/Configuration/Conversion/HoardConfigurationConversionSession.cs`, `HoardConfigurationConversionExtensions.cs` and `ConfigurationConversionPreview.cs`: session invariant "Preview does not resolve secrets; no public digest/locator; single approved apply". Pin private original/proposal bytes/digests, mapping/registry/builder context and opaque session ID; run the shared structure/composition/public checks without constructing a proof usable for activation and report only Added/Removed/Changed/ReferenceChanged/SelectionChanged/VersionChanged safe identities/categories (CFG-27).
- [X] T056 [US5] Implement `src/Hoard.Hosting/Configuration/Conversion/ConfigurationConversionApply.cs`: consume approval once, verify unchanged original/proposal/contracts/mapping/builder/fresh destination, repeat full shared evaluation including secrets under finite supervision without composing, then serialize only original reference-bearing configuration and release its unused proof safely. No ambient env/CLI overlays, provider data migration, guessed mapping or publication after failed validation (FR-022, CFG-28).
- [X] T057 [P] [US5] Implement `src/Hoard.Hosting/Configuration/Conversion/ConfigurationPublisher.cs`: publication invariant "Never overwrite source/destination; complete file or no final file; original retained". Use exclusive owner-private same-directory staging in an owner-restricted destination directory, bounded writes, flush/close and supported-platform atomic no-clobber publication; reject existing/racing destinations/aliases without touching them, and expose safe categories rather than paths or a universal power-loss/network-share/hostile-directory guarantee (CFG-29).
- [X] T058 [US5] Integrate publication supervision in `src/Hoard.Hosting/Configuration/Conversion/ConfigurationConversionApply.cs` and `ConfigurationPublication.cs`: cancellation before dispatch prevents publication, after dispatch reports the actual outcome or explicit PublicationPending while unresolved; keep the task/staging/notification lease until actual completion, observe faults safely, freeze the returned result and never report definite rollback from a cancelled wait (FR-016, FR-022, CFG-30).
- [X] T059 [US5] Add standalone child harness `tests/fixtures/configuration/ConversionProcess/ConversionProcess.csproj`, `Program.cs` and reviewed lock with safe staged/write/flush/pre-/post-publish barriers; extend `scripts/configuration_evidence.py` to terminate only its specific child PID at each barrier, inspect original/final bytes and private staging permissions, release/observe surviving work and clean only known harness-owned files. Exercise cancellation/no-clobber/fault counterparts on each claimed local platform, not mocked publication alone (CFG-29..30).
- [X] T060 [US5] Update `docs/PROVIDERS.md` and `specs/003-provider-configuration/quickstart.md` with actual preview/approval/apply APIs, synthetic-only mapping/current versus unsupported versions, no overlays, owner-private output/staging cleanup, truthful pending observation and explicit validated restart/recovery. State provider schema/data version/backups/restore/irreversibility as separate prerequisites and do not claim configuration restoration reverses data or illustrative YAML is supported (FR-021..023, CFG-31, CFG-34).
- [X] T061 [US5] Run T016/T050..T053 and the real child publication matrix through `scripts/configuration_evidence.py`, recording intended red/green, full non-activating validation, zero seeded output, original retention/no-clobber and exact OS/filesystem support. Keep unsupported platforms blocked or explicitly unclaimed; process interruption is not hardware power-loss evidence (CFG-26..31).

**Checkpoint**: Every declared synthetic conversion has safe preview, approved
validated complete publication and interruption evidence; released-format,
provider-data and arbitrary filesystem support remain unclaimed.

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verify actual package/API boundaries, retained compatibility,
complete reproducible acceptance and truthful documentation before later
convergence/finalization. Do not mark a feature merged or run another driver
stage here.

- [X] T062 Write `tests/architecture/Hoard.Architecture.Tests/ConfigurationBoundaryTests.cs` inspecting actual source/project/packed/API evidence for unchanged BCL-only Abstractions, provider-free Core, Abstractions-only metadata/artifact, host-owned adapters, unchanged shared-framework/dependency graph and no new runtime package/cross-provider/slice/loading/listener edges; demonstrate intended rejection with synthetic forbidden-edge/missing-evidence counterparts before accepting the permitted actual graph, and retain the original eight scans and F-01/F-02 acceptance rather than replacing them with new checks (CFG-32, CFG-35).
- [X] T063 Complete compatibility/graph evidence in `scripts/configuration_evidence.py` and `tests/integration/Hoard.Composition.Tests/ConfigurationDistributionTests.cs`: run retained F-01 registration and pre-F-03 F-02 lifecycle binaries against new local packages without recompilation, prove the unchanged option-bearing provider receives ordinary/secret values via its new host adapter, compile equivalent new-source consumers, inspect real packed/project/API/assets/runtimeconfig graphs and framework propagation, and fail missing/stale/empty provenance explicitly (CFG-32..33).
- [X] T064 Complete `scripts/configuration_evidence.py` and `tests/tooling/test_configuration_evidence.py` with a fail-closed exact CFG-01..36 inventory linked to nonempty actual tests/journeys/platform outputs, format/analyzer invocation, captured intended red/green and retained-binary/package hashes; fresh locked default replay must not mutate source or standalone locks, skip missing manifests, treat a partial selector as full acceptance or recursively run foundation/lifecycle suites from tooling unit tests (CFG-36).
- [X] T065 Update `README.md`, `docs/DEVELOPMENT.md`, `docs/PROVIDERS.md`, `examples/LifecycleHost/README.md` and `specs/003-provider-configuration/quickstart.md` with implemented signatures/strict JSON source grammar, owner-only secrets/trust limits, finite budgets/pending resources, restart/rebuild/recovery, exact existing commands and measured platform scope; distinguish fixture-only current support from planned product YAML/providers/UI/client/conformance, and explain unchanged baseline diagrams/ADR/product/IaC/release guides unless actual behavior makes an update necessary (CFG-31, CFG-34).
- [X] T066 Audit delivered examples/normal output/support statements using `specs/003-provider-configuration/contracts/acceptance.md` and actual `examples/LifecycleHost/`/`docs/PROVIDERS.md` content; record CFG-34..35 findings in `specs/003-provider-configuration/plan.md` with zero unresolved false claims, credentials/locators in safe output, hidden fallback/listener/security settings, automatic download/loading or data-reversal promises. Leave all reviewer-owned checklist markers unchanged.
- [X] T067 Obtain the required bounded read-only `hoard-architecture-review` of actual Hosting configuration/public graph, sole F-02 authority, atomic proof/input-transfer ownership, unknown-identity remapping, pending work, retained binaries and conversion publication; record concrete findings/references in `specs/003-provider-configuration/plan.md` and resolve blocking defects with focused regression evidence before acceptance. Planning review is not implementation approval (CFG-17..22, CFG-29..33).
- [X] T068 Run `bash scripts/validate-configuration.sh`, `bash scripts/validate-lifecycle.sh`, `bash scripts/validate-foundation.sh` and `python3 -m unittest discover -s tests/tooling -v` after the implementation/review corrections, with documented format/analyzers included in focused acceptance; record exact results and local-platform limitations in `specs/003-provider-configuration/plan.md`, require all intended case/proof selections nonempty and all test-held work released/observed, and investigate relevant regressions rather than accepting skips (CFG-01..36).
- [X] T069 Record measured case/requirement/outcome traceability, red-before-green references, package/binary provenance, architecture-review disposition, exact commands/results and tested conversion platforms in `specs/003-provider-configuration/plan.md`; reconcile current support in `README.md`/`docs/DEVELOPMENT.md` and task status in `specs/003-provider-configuration/tasks.md`. Commit coherent implementation checkpoints and push immediately after each commit; leave convergence, finalization/PR readiness, merge and backlog completion to their separately authorized stages.

## Dependencies & Execution Order

### Phase and Story Dependencies

```text
Setup T001..T004 -> Foundation T005..T012
  -> US1 T013..T020 (source-resolution MVP)
  -> US2 T021..T031 (secret-free configured composition)
  -> US3 T032..T042 (secure local secret delivery)
       -> US4 T043..T049 (restart/distribution)
       -> US5 T050..T061 (conversion/publication)
  -> Cross-cutting T062..T069 -> later converge/finalize stages
```

US4 and US5 may develop concurrently after US3: their source/test files are
disjoint, but their shared orchestrator edits are serialized explicitly.
US1..US3 are genuinely ordered by the shared evaluation pipeline; claiming
independence by duplicating gates/resolvers is prohibited. Every story still has
an independently observable test described in its phase.

### Task-Level Prerequisites

All members of a listed range share the listed prerequisites unless another row
specifically distinguishes them. These are actual prerequisites, not implied
by numeric order. Tests precede their behavior; write/capture the red result
before beginning the corresponding implementation task.

| Task(s) | Prerequisites |
| --- | --- |
| T001, T002, T004 | None; independent setup files |
| T003 | T002 |
| T005, T009 | T001..T004 |
| T006 | T005 |
| T007 | T006 |
| T008 | T007 |
| T010 | T008, T009 |
| T011 | T007, T008, T010 |
| T012 | T005..T011 |
| T013..T016 | T012 |
| T017 | T013..T016 |
| T018 | T017 |
| T019 | T018 |
| T020 | T013..T019 |
| T021..T025 | T020 |
| T026 | T021..T025 |
| T027 | T026 |
| T028 | T027 |
| T029 | T028 |
| T030 | T029 |
| T031 | T021..T030 |
| T032..T036 | T031 |
| T037, T038 | T032..T036 |
| T039 | T037, T038 |
| T040 | T039 |
| T041 | T040 |
| T042 | T032..T041 |
| T043..T045 | T042 |
| T046 | T043..T045, T004 |
| T047 | T046 |
| T048 | T047 |
| T049 | T043..T048 |
| T050..T053 | T042 |
| T054, T057 | T050..T053 |
| T055 | T054 |
| T056 | T055 |
| T058 | T056, T057 |
| T059 | T058, T049 (serialize orchestrator edits) |
| T060 | T058 |
| T061 | T050..T060 |
| T062 | T049, T061 |
| T063 | T062 |
| T064 | T063 |
| T065 | T064 |
| T066 | T065 |
| T067 | T066 |
| T068 | T067 |
| T069 | T068 |

T063 does not run/accept T062's architecture test until its actual graph inputs
exist. T066's audit is read-only except its evidence section; it must not race
T067/T069's edits to the same plan. `[P]` never overrides those constraints.

### Parallel Opportunities and Examples

Independent ready groups are T001/T002/T004, T005/T009, US1's T013..T016,
US2's T021..T025, US3's T032..T036 and then T037/T038, US4's T043..T045,
US5's T050..T053 and then T054/T057.
Never run shared orchestrator, lifecycle lease/coordinator or plan/docs edits
concurrently.

| Story | Parallel example after prerequisites |
| --- | --- |
| US1 | After T012, author `ConfigurationSourceTests.cs` (T013) and `ConfigurationMergeTests.cs` (T015) together; all four test files must exist before parser implementation. |
| US2 | After T020, author `ConfiguredSelectionTests.cs` (T021) and `ConfigurationProofTests.cs` (T024) together; serialize bridge/evaluator/proof/lifecycle edits. |
| US3 | After T031, author `FileSecretTests.cs` (T033) and `ConfigurationPendingTests.cs` (T035) together; after T032..T036, implement the disjoint env/file readers (T037/T038). |
| US4 | After T042, author restart/distribution/recovery tests (T043..T045) together; serialize fixture/example/orchestrator integration. |
| US5 | After T042, author preview/approval/publication/interruption tests (T050..T053) together; then mapping (T054) and publisher (T057) are disjoint. |

These are execution opportunities, not instructions to launch subagents.

## Requirement and Proof Traceability

### Functional Requirements

The existing acceptance contract owns detailed scenario and edge-case mappings.
Every one of its 36 cases has implementation and focused proof assignments below,
so all 22 story scenarios and 13 edge cases retain that transitive mapping.
SC outcomes have explicit assignments as well; counts do not prove acceptance.

| Requirement | Implementation / integration tasks | Focused proof / acceptance tasks |
| --- | --- | --- |
| FR-001 | T007, T018..T020 | T013, T020 |
| FR-002 | T006..T007, T017..T018 | T014, T022 |
| FR-003 | T017, T019 | T015, T022 |
| FR-004 | T019, T026..T028 | T015, T021, T045 |
| FR-005 | T008, T019..T020, T039, T047 | T013, T036, T043 |
| FR-006 | T026, T047 | T021, T044 |
| FR-007 | T019, T026 | T015, T021 |
| FR-008 | T026, T029..T030 | T021, T024..T025 |
| FR-009 | T006, T027 | T005, T022 |
| FR-010 | T027..T028, T039 | T022, T023, T035 |
| FR-011 | T017, T026..T027, T039 | T014, T021, T023 |
| FR-012 | T028..T030, T039, T041 | T023..T025, T035..T036 |
| FR-013 | T017, T037..T039 | T014, T032..T034 |
| FR-014 | T037..T039 | T032..T033 |
| FR-015 | T011, T039, T041 | T034, T036, T043 |
| FR-016 | T007, T010..T011, T028..T030, T041, T058 | T009, T025, T035..T036, T053 |
| FR-017 | T011, T017, T037..T039 | T014, T032, T036 |
| FR-018 | T019, T029..T030, T047 | T024..T025, T043 |
| FR-019 | T046..T048 | T044, T049, T062..T063 |
| FR-020 | T047..T048, T060 | T045, T049 |
| FR-021 | T017..T018, T027, T054, T060 | T016, T022, T050 |
| FR-022 | T054..T059 | T050..T053, T061 |
| FR-023 | T048, T060, T065 | T045, T050, T066 |
| FR-024 | T008, T010, T017..T020, T026, T040, T055..T058 | T014, T034..T035, T050..T053 |
| FR-025 | T017, T026, T028, T037..T039, T047 | T021, T032..T033, T045, T062, T066 |
| FR-026 | All story integrations, T063..T065, T069 | All focused proof tasks, T067..T068 |

### Success Criteria

| Outcome | Evidence-producing tasks |
| --- | --- |
| SC-001 | T013..T016, T020, T022, T031 |
| SC-002 | T021..T025, T031, T036, T042 |
| SC-003 | T014, T023, T032..T033, T036, T042 |
| SC-004 | T034, T042, T050..T053, T061 |
| SC-005 | T009, T024..T025, T035..T036, T042, T053 |
| SC-006 | T043..T045, T049, T062..T063 |
| SC-007 | T016, T045, T050..T053, T059..T061 |
| SC-008 | T048, T060, T065..T069 |

### Configuration Cases

| Case | Implementation / integration tasks | Focused proof tasks |
| --- | --- | --- |
| CFG-01 | T018..T020 | T013, T020 |
| CFG-02 | T006, T017..T018 | T014 |
| CFG-03 | T019 | T015 |
| CFG-04 | T019, T026..T027 | T015, T021 |
| CFG-05 | T007, T010, T017..T018 | T005, T013..T014 |
| CFG-06 | T026 | T021 |
| CFG-07 | T026, T030 | T021, T031 |
| CFG-08 | T026..T027 | T021, T023 |
| CFG-09 | T006, T026..T027 | T005, T022 |
| CFG-10 | T017, T019, T027 | T015, T022 |
| CFG-11 | T026..T027, T039 | T023 |
| CFG-12 | T028, T039 | T022..T023, T031, T042 |
| CFG-13 | T037, T039 | T032, T042 |
| CFG-14 | T038..T039 | T033, T042 |
| CFG-15 | T017, T037..T039 | T014, T032..T034 |
| CFG-16 | T011, T039, T041 | T032, T036 |
| CFG-17 | T008, T026, T040, T055..T058 | T034, T050..T053 |
| CFG-18 | T007, T010, T028, T039 | T009, T035 |
| CFG-19 | T010, T028..T030, T039..T041 | T009, T024, T035..T036 |
| CFG-20 | T010..T011, T040..T041 | T009, T035..T036 |
| CFG-21 | T029..T030, T041 | T024..T025, T036 |
| CFG-22 | T030, T041 | T025, T036 |
| CFG-23 | T019, T039, T047 | T043, T049 |
| CFG-24 | T046..T048 | T044, T049 |
| CFG-25 | T047..T048, T060 | T045, T049 |
| CFG-26 | T017..T018, T027, T054 | T016, T022, T050 |
| CFG-27 | T054..T055 | T050, T061 |
| CFG-28 | T056 | T051, T061 |
| CFG-29 | T057, T059 | T052, T059, T061 |
| CFG-30 | T058..T059 | T053, T059, T061 |
| CFG-31 | T048, T054, T060, T065 | T045, T050, T066 |
| CFG-32 | T046..T047, T063 | T044, T062..T063 |
| CFG-33 | T004, T046..T047, T063 | T044, T049, T063 |
| CFG-34 | T048, T060, T065 | T066, T068 |
| CFG-35 | T017, T026, T028, T047 | T014, T021, T045, T062, T066 |
| CFG-36 | T003, T064 | T002, T064, T068 |

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete shared setup/foundation, T001..T012.
2. Complete US1, T013..T020, and demonstrate deterministic safe source inspection
   with rejected structural counterparts and no provider/secret activity.
3. Stop at that observable MVP checkpoint if working incrementally. Do not deploy
   it as a cache or turn partial source resolution into a successful proof.

### Incremental Delivery

1. Add US2's secret-free real-gate/configured-lifecycle increment.
2. Add US3's local references, safe failure and retained pending-work proof before
   claiming secure credential-bearing configuration.
3. Add US4's restart/bundled/custom journeys and US5's explicit synthetic conversion;
   serialize shared runner edits while their independent tests can develop together.
4. Complete actual graphs/binaries, docs/support audit, architecture review and
   full retained suites. Only then record implementation completion; subsequent
   converge/finalize/merge gates remain separate invocations.

### Notes

- Never self-approve reviewer-owned checklists or edit their markers here.
- Never treat cancellation delivery, an expired wait, a returned result or a
  test count as proof that pending work ended or inputs/root were released.
- Capture the intended failure before accepting each changed behavior; preserve
  exact retained bytes and real package/platform provenance.
- Commit coherent work on the recorded branch and push immediately after each
  commit. Keep the feature PR draft until separately authorized finalization.
- No infrastructure plan/apply, deployment, package/release publication or merge
  is authorized by these tasks.

## Phase 9: Convergence

The present-code assessment found two HIGH partial diagnostic-fidelity gaps.
All original T001..T069 remain unchanged. Public-API probes against the current
binaries reproduce both gaps despite passing existing CFG-01..36 acceptance:
a missing CLI-supplied secret reports `unknown-setting`, and a declared
`paired` option-rule rejection on a CLI-overridden field reports only
`CheckFailure` with source `Defaults`. Both paths still reject without an
activation proof; no credential disclosure or activation bypass was observed.
Execute T070 before T071 to serialize shared supervisor/report and acceptance
inventory edits. Finalization requires implementation and a fresh convergence
assessment, not just the existing passing test counts.

- [ ] T070 Preserve the known canonical secret setting through active env/file dispatch and originating failure, timeout, cancellation-notification and late-fault diagnostics in `src/Hoard.Hosting/Configuration/ConfigurationSecretResolver.cs` and `ConfigurationSupervisor.cs`; retain the actual winning source and registered owner without exposing values, locators or raw errors. Add focused paired regressions in `tests/integration/Hoard.Composition.Tests/ConfigurationSecretTests.cs` and `ConfigurationCoordinationTests.cs` that distinguish multiple known fields, cover unavailable and pending outcomes, keep returned reports frozen and release/observe held work; require the new scenario identities in `scripts/configuration_evidence.py`. Record intended red/green and safe-output evidence during implementation per FR-024, US3/AC2, SC-004, CFG-13..14/17..20 and T034/T040 (partial, HIGH).
- [ ] T071 Preserve effective setting-source provenance and the validated declared option-rule identity in active option diagnostics in `src/Hoard.Hosting/Configuration/ConfigurationOptionChecker.cs`, `ConfigurationSupervisor.cs` and `HoardConfigurationReport.cs`, using bounded known metadata and host-owned corrective-action text rather than provider messages; do not collapse a declared `paired` rejection into an unnamed generic check or label a CLI-supplied failing field as Defaults. Cover public and secret-dependent rule rejections, explicit option-version provenance and malformed/unknown rule counterparts in `tests/integration/Hoard.Composition.Tests/ConfiguredCompositionTests.cs` and `ConfigurationSecretTests.cs`, and require the new scenario identities in `scripts/configuration_evidence.py`. Preserve fail-before-activation ordering, redaction, diagnostic bounds and F-02 authority; update affected diagnostic guidance/evidence and record intended red/green during implementation per FR-024, US2/AC3, SC-004, CFG-10/12/17/26 and T022/T034/T040 (partial, HIGH).
