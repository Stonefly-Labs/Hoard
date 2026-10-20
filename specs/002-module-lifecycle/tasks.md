# Tasks: Module Registry, Composition and Lifecycle

**Input**: Design documents from `specs/002-module-lifecycle/` (F-02).
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md),
[research.md](research.md), [data-model.md](data-model.md),
[public API](contracts/public-api.md), [lifecycle contract](contracts/lifecycle.md),
[acceptance matrix](contracts/acceptance.md), and [quickstart.md](quickstart.md).

**Generation-stage status (historical)**: Generated implementation instructions;
all 72 tasks were unchecked at generation.
No lifecycle code, fixture package, executable, dependency, or runtime evidence
is delivered by this task-generation stage. The 40 custom criteria in
[composition](checklists/composition.md) and [lifecycle](checklists/lifecycle.md)
remain unchecked and reviewer-owned. Task generation is neither checklist
approval nor authorization to implement. Read-only analysis is the next
separately authorized stage; implementation additionally requires the reviewer
gate and a separate invocation.

**Requirements-review checkpoint (historical)**: The later requested review and user-approved
RQ-01/RQ-02 follow-up satisfy all 40 custom criteria without waivers. The
corrections below retain pending-cleanup safety and distinct baseline/custom
manifests. All 72 implementation tasks were unchecked at that checkpoint; the
review follow-up did not begin the separately scheduled implementation stage.

**Implementation checkpoint**: All 74 implementation tasks, including the
separately authorized T073/T074 convergence corrections, are complete. The original implementation is
recorded below with [measured evidence and LC traceability](plan.md#implementation-evidence).
Runner/helper destinations were consolidated into the one coordinator where
documented, not fabricated as separate files. Root ownership now explicitly
separates module stop from external-owner disposal and shares actual framework
stop through StopHoardApplicationAsync(lease). These are implementation
adjustments to the new opt-in surface, not changes to F-01 registration APIs.
Reviewer-owned requirements checklist bytes remain unchanged. Convergence,
finalization, PR readiness, merge and dependency completion are separate stages.
The [T073 follow-up evidence](plan.md#t073-implementation-follow-up) records
lock-free supervised host notification, retained resources, focused red/green
proof, bounded architecture review and fresh locked acceptance. The
[T074 follow-up evidence](plan.md#t074-implementation-follow-up) records safe
cancellation-failure reporting, known/late diagnostic publication, preserved
resource outcomes and focused/full acceptance. Fresh convergence remains the
next separately authorized stage.

**Tests**: Explicitly required by FR-019, all five independent story tests,
SC-001..SC-007, and LC-01..LC-40. Write focused tests before the corresponding
behavior, capture their intended red result, then make the permitted and
rejected cases pass. A compile failure can establish a missing public contract,
but cannot prove correct runtime rejection. Never accept an unrelated failure,
empty test selection, skipped proof, missing package evidence, or cancellation
delivery as successful behavior.

**Organization**: Shared setup and safety primitives precede five story phases
in specification priority order, followed by cross-cutting acceptance. Stories
share a coordinator; independent validation means each story has a bounded
observable proof, not five independent lifecycle implementations. All paths
below are repository-relative implementation destinations, not existing APIs.

## Format: `[ID] [P?] [Story] Description`

- Each task starts with `- [ ] TNNN`, optional `[P]`, an obligatory story label
  inside story phases, and exact file paths.
- `[P]` means disjoint files and no dependency within the identified parallel
  group, after its prerequisites. It does not authorize agents or a workflow
  engine. The dependency table overrides numeric order for readiness.
- Shared setup/foundational/polish tasks have no story label. Requirements,
  outcomes, and LC case IDs come from the linked specification and contracts.

## Path Conventions

Extend `src/Hoard.Hosting` only for production behavior; Abstractions, Core,
Application, F-01 public registration signatures and family markers remain
unchanged. Reuse the existing unit/integration/architecture projects rather
than introduce a new test framework. Ordinary lifecycle xUnit tests use local
instrumented adapters/TestServer, not an additional mandatory packed-evidence
manifest, so the existing foundation command can still execute the solution.
Package-only proof belongs in the separate lifecycle orchestrator/example.

Use `tests/fixtures/lifecycle/` for six independent packages, and
`examples/LifecycleHost/` for the fixture-only package consumer. Do not rewrite
F-01 fixture/example sources, scenarios, or compile-only behavior. Refresh only
locks necessarily changed by reviewed Hosting dependency/content changes,
including affected existing consumers; retained old source/behavior does not
imply unchanged dependency hashes. Keep standalone projects outside the solution
and hidden repository props inheritance.

`scripts/validate-lifecycle.sh` and `scripts/lifecycle_evidence.py` were proposed
at generation and are now implemented bounded tooling. Reuse suitable public/internal test
inspection and `scripts/foundation_evidence.py` preparation helpers without
calling its main routine recursively, weakening F-01 scans, or importing test
code into product. Local feeds, caches, manifests, binaries and reports belong
in a private resolved temporary directory. Track reviewed lockfiles only.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add only the dependencies and bounded proof support authorized by
the plan; no curated product executable, real provider, UI or infrastructure.

- [x] T001 Update `Directory.Packages.props`, `src/Hoard.Hosting/Hoard.Hosting.csproj` and `tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj` for internal production `NuGet.Versioning`, Hosting's ASP.NET Core shared-framework reference, test-only stable supported `Microsoft.AspNetCore.TestHost` 10.x and the Hosting project reference; assess licenses/advisories, record exact dependency/framework impact in `specs/002-module-lifecycle/research.md`, and generate initial reviewed source/test locks before locked replay without changing the SDK or unrelated versions.
- [x] T002 [P] Write failing tooling regressions in `tests/tooling/test_lifecycle_evidence.py` for missing inputs, empty test/journey selections, nonzero/timed-out subprocesses, stale/nonlocal package provenance, default lock mutation, and cleanup confined to the orchestrator's own resolved temporary directory; exercise only synthetic temporary inputs, never launch the product orchestrator from a test.
- [x] T003 Introduce `scripts/validate-lifecycle.sh` and `scripts/lifecycle_evidence.py` with explicit prerequisites, bounded subprocesses, private temporary-directory cleanup, fail-fast sanitized errors, and deliberate `--update-locks` bootstrap followed by fresh-cache locked replay; reuse foundation copying/packing/hash helpers where suitable and fail explicitly until required later proof sections exist rather than printing premature full acceptance.
- [x] T004 [P] Add deterministic instrumentation in `tests/integration/Hoard.Composition.Tests/LifecycleTestHarness.cs` and `LifecycleTestTimeProvider.cs`: safe-ID monotonic event ledger, controllable phase/request/response/worker barriers, synthetic connection/resource counters, captured normal logs, and fake-time control; release and observe every test-created task/barrier in teardown without real network/service calls or long sleeps.

**Checkpoint**: Preparation support exists, not passing F-02 acceptance.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared opt-in contracts, safe results, and once-only
supervision primitives before any story. These do not implement a second
registration path or configuration subsystem.

- [x] T005 Write failing contract/ownership tests in `tests/integration/Hoard.Composition.Tests/LifecycleContractTests.cs` for explicit immutable inputs, validation success-versus-errors, builder-bound composition, opt-in type-only adapter association, safe result shapes, and unchanged old registration behavior; include null/default-array/duplicate input boundaries rather than trivial getter tests.
- [x] T006 Define `src/Hoard.Hosting/Composition/HoardStartupSelection.cs`, `HoardRequiredCapability.cs`, `HoardPlatformVersions.cs`, `HoardCompositionValidation.cs` and `HoardValidatedComposition.cs` with the model constraints: EnabledModuleIds is "`ImmutableArray<string>`; explicit unique IDs, no unknown entry"; MetadataModuleId is "`string`; enabled Metadata ID"; ArtifactModuleId is "`string`; enabled Artifact ID"; RequiredCapabilities is "`ImmutableArray<HoardRequiredCapability>`; explicit demands, empty allowed". Capability demands contain "`ModuleId`, `CapabilityId`, bounded `VersionRange` and `AllowPrerelease`"; "Reject duplicate demand keys." Versions hold "explicit normalized `HostVersion` and `AbstractionsVersion`". Validation has "either `Composition` and no errors, or no composition and immutable safe diagnostics"; validated composition "has no public constructor" and holds "read-only enabled IDs, disabled declarations, authoritative IDs, platform versions, satisfied capability demands, active edges and activation order", with no live instances, secret options or health.
- [x] T007 [P] Add `src/Hoard.Hosting/Lifecycle/IHoardModule.cs`, `HoardModuleLifecycleRegistration.cs`, `HoardModuleLifecycleExtensions.cs` and the collecting surface in `src/Hoard.Hosting/Routing/HoardModuleEndpointBuilder.cs` from the public contract: six explicit callbacks and `AddModuleLifecycle<TProvider,TModule>` recording types only; associations pair "`ProviderType: Type` with `ModuleType: Type`", with selected adapters "concrete, closed, parameterless". Preserve F-01 APIs/constraints and create no instance, operational service, factory invocation or assembly scanner during registration; endpoint collection remains unpublished until the route gate.
- [x] T008 [P] Define `src/Hoard.Hosting/Lifecycle/HoardLifecycleResults.cs`, `HoardLifecycleDiagnostic.cs` and `HoardLifecycleSnapshot.cs`: status is "Disabled, Enabled, Initializing, Ready, NotReady, Failed, Stopping or Stopped"; readiness contains "`Ready: bool` and immutable health observations" using "Ready, Unavailable, Initializing, TimedOut or Failed", each naming "a declared health responsibility ID". Snapshot contains "lifecycle correlation ID, composition identity, phase, startup admission, aggregate readiness and immutable module observations". Cleanup outcomes are "NotEntered, Completed, Failed, TimedOut, NotAttemptedBudgetExhausted, or UnsafePendingCallback"; root disposal is separate "Completed, Failed, TimedOut, NotAttemptedBudgetExhausted or NotAttemptedUnsafe". Diagnostic fields are "rule code, safe module/registration identity, phase, safe dependency path, fixed corrective-action code/message, correlation ID, and primary-versus-cleanup classification"; no raw exception/URL/option/provider-text fields.
- [x] T009 Write failing primitive tests in `tests/integration/Hoard.Composition.Tests/LifecycleCoordinationTests.cs` for one absolute deadline, capped inner waits including synchronous callbacks, expired inter-phase pauses, once-only entered/completed/cleanup bookkeeping, cancelled individual waiters, and stop winning over publication; use T004 fake time and release pending work after observation.
- [x] T010 Implement `src/Hoard.Hosting/Lifecycle/HoardLifecycleOptions.cs`, `LifecycleDeadline.cs` and `ActivationLedger.cs`: StartupTimeout, ActivationCallbackTimeout, ReadinessTimeout, ShutdownTimeout, DrainTimeout and ModuleCleanupTimeout are "all positive finite `TimeSpan` values"; "Inner budgets are capped by the outer remaining time; a small outer budget is valid, not silently expanded." Apply defaults 120s/30s/5s startup/callback/readiness and 30s/10s/5s shutdown/drain/cleanup, an injected `TimeProvider`, monotonic timestamps and safe observation of pending/faulted tasks; ledger records entry before dispatch and never infers release from cancellation.
- [x] T011 Implement the single-owner lease skeleton in `src/Hoard.Hosting/Lifecycle/HoardServiceComposition.cs` and the contract in `IHoardLifecycle.cs`: acquire ownership from first construction, clean pre-return failures internally, bind builder/composition identity, retain pending activity, and make lease disposal share stop rather than recursively become container-owned; expose explicit incomplete results, not a success-shaped empty stop result. Later build/drain/root-disposal tasks complete this same owner.
- [x] T012 Implement shared-operation state control in `src/Hoard.Hosting/Lifecycle/HoardLifecycleCoordinator.cs`: separate phase/status/readiness/admission, one shared start/stop task, caller-cancelled waits versus host-lifetime cancellation, irreversible stop latch, no callback dispatch/publication after stop, and terminal failed/stopped instance rejection; all story runners use this one coordinator and ledger.
- [x] T013 Run `LifecycleContractTests` and `LifecycleCoordinationTests` through `tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj`, plus T002 tooling regressions via `scripts/validate-lifecycle.sh`'s bounded preparation/runner; record intended red-to-green primitive/contract proof and distinguish this partial checkpoint from LC-01..LC-40 acceptance.

**Checkpoint**: Shared safety primitives are available. All stories wait for
T013; no HTTP, shutdown-completeness or production-support claim follows.

## Phase 3: User Story 1 - Start Only the Intended Modules (Priority: P1)

**Goal**: Validate before construction, preserve F-01 compatibility policy,
freeze explicit selection and activate prerequisites deterministically.

**Independent Test**: Use endpoint-free instrumented adapters with exactly one
metadata/artifact selection, optional protocol/identity choices and shuffled
registration. Prove zero activation on rejection, fixed snapshot and successful
prerequisite-first initialization/readiness without real providers. This is the
first/MVP increment, not permission to use unproved routing or stop behavior.

### Tests for User Story 1

- [x] T014 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/RegistryValidationTests.cs` for LC-02..05/14: unknown/unregistered selection, duplicate IDs even disabled/through two entry points, malformed enum/null/default collections/nested duplicate keys/provenance, family/type mismatch, and missing/duplicate/orphan adapters, with zero constructors/service factories/callbacks/I/O and valid disabled incompatible counterparts.
- [x] T015 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/RuntimeCompatibilityTests.cs` for LC-06/09/12 using applicable F-01 C-01..C-23 policy rows: bounded interval/exact syntax, normalized SemVer, both platform axes, prerelease flags, unavailable versus enabled optional dependencies, and target-specific capability demands; keep source/binary/release classifications as separate LC-39 proof rather than inventing activation equivalents.
- [x] T016 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/SelectionGraphTests.cs` for LC-01/07..12: required absent/disabled targets, optional absent/disabled/compatible/incompatible edges, self/required/enabled-optional cycles, ordinal ready-set ties, safe cycle paths, exact authoritative cardinality and permitted multiple protocol/identity selections; assert no auto-enablement, fallback, substitution or range widening.
- [x] T017 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/CompositionSnapshotTests.cs` for LC-13/14: defensive snapshots, stale builder/adapter/options/selection rejection before construction, builder identity mismatch and unchanged running selection; retain inert legacy registration with no adapter, while selecting it for lifecycle fails explicitly.
- [x] T018 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/SelectedStartupTests.cs` for LC-01/08/17/25 using endpoint-free selections: metadata gate before all construction, service/build/map/init/readiness phase order, prerequisites completed before dependents, explicit ready and required health observations, and no admission/worker before complete readiness; include invalid/missing/duplicate/unknown health observations and optional-health counterparts.

### Implementation for User Story 1

- [x] T019 [P] [US1] Implement internal `src/Hoard.Hosting/Composition/RuntimeCompatibility.cs` using `NuGet.Versioning` and the F-01 policy without referencing its test classifier from product; retain version/range strings on public APIs, explicit prerelease opt-in and release ordering, rejecting disallowed syntax rather than normalizing or widening it.
- [x] T020 [P] [US1] Implement `src/Hoard.Hosting/Composition/RegistryValidator.cs` with metadata/type inspection only: "One registered provider must implement exactly one family marker matching its declared category"; reject abstract/open generic types, unknown enums, null/default collections, invalid lowercase F-01 IDs/version/range syntax, nested duplicate keys and self-dependencies. Apply "Required F-01 text fields must be nonempty and bounded" and reject provenance "including userinfo/query/fragment"; retain explicit structural limits in code/docs without echoing rejected text. Reject registry-wide duplicate IDs and duplicate/orphan adapters; disabled entries may lack adapters and skip active compatibility.
- [x] T021 [US1] Implement `src/Hoard.Hosting/Composition/SelectionGraphValidator.cs`: "Exactly one enabled Metadata and Artifact are permitted, and they must equal the authoritative IDs"; "Protocol and Identity cardinality is zero or more. No defaults are inferred." Enforce enabled target-specific capability/range demands, required and enabled-optional edges, no edge/claim for unavailable optional targets; active edges record "prerequisite ID, dependent ID, optional flag, and declared range/prerelease policy". Use Kahn ordering with an ordinal "`StringComparer.Ordinal` ready set" and report deterministic bounded safe cycle paths before construction.
- [x] T022 [US1] Wire `ValidateComposition(selection, versions, options)` in `src/Hoard.Hosting/Composition/HoardCompositionExtensions.cs` to T019..T021 and snapshot all registrations/associations/inputs, returning explicit invalid results versus a builder-bound immutable composition; "Copy all inputs when validation starts", and invalidate later registration/options/selection changes before activation rather than changing a running graph.
- [x] T023 [US1] Implement `ComposeHoardModulesAsync` in `src/Hoard.Hosting/Lifecycle/HoardServiceCompositionExtensions.cs`: verify the original snapshot, supervise enabled-only inert adapter construction and ordered ConfigureServices with the shared deadline/ledger, record acquisition ownership, reject module-added `IHostedService`/`BackgroundService` descriptor deltas, prohibit nested DI builds in supported adapters, and clean failed composition through the single lease with no leaked raw exception.
- [x] T024 [US1] Add `src/Hoard.Hosting/Lifecycle/HoardApplicationExtensions.cs` and `HoardLifecycleHostedService.cs`: supervise this builder's single `BuildHoardApplicationAsync`, attach root ownership before bridge startup, verify composition identity, dispatch MapHoardModulesAsync's unpublished route-collection phase and require mapping before bridge start; wire normal host start/stop without independent app disposal or `RunAsync` host disposal. Endpoint-free US1 fixtures use no routes; nonempty collections must pass the T038/T039 gate before acceptance.
- [x] T025 [US1] Implement `src/Hoard.Hosting/Lifecycle/HoardInitializationRunner.cs` and `HoardReadinessEvaluator.cs` to await each prerequisite-first initialization and assess every enabled module under the existing capped startup deadline; "Missing required observations fail readiness; duplicates, unknown IDs or inconsistent status are failures, not inferred success." Optional unhealthy observations do not override explicit `Ready=false`, and no-probe modules still return explicit status.
- [x] T026 [US1] Integrate T023..T025 into `src/Hoard.Hosting/Lifecycle/HoardLifecycleCoordinator.cs` using its existing shared tasks/stop latch, false-until-complete readiness and publication guard; fail the entire selected start on any enabled module failure/cancellation/timeout regardless of optional dependency labels, with no retry/degraded success or later dependent initialization.
- [x] T027 [US1] Prepare/run T014..T018 through `scripts/lifecycle_evidence.py` and the existing composition project, capture intended red and green results for LC-01..14 plus scoped startup/readiness proof, and record zero pre-validation construction and identical shuffled-order outcomes; label this first increment partial, not complete lifecycle acceptance.

**Checkpoint**: US1 has an independently observable fixture-only validator and
ordered start. Later route, failure/drain and package proofs remain required.

## Phase 4: User Story 2 - Expose Only Enabled and Ready Functionality (Priority: P1)

**Goal**: Enforce disabled isolation, owned-route safety, complete startup
admission, truthful later readiness and tracked worker admission.

**Independent Test**: TestServer dispatches enabled fixture handlers only after
every selected module is ready; a disabled fixture has zero constructors,
callbacks, routes, workers and connection attempts and returns ordinary 404.
Exercise ambiguous/permitted routes and later health loss/recovery without
replacing selection or automatically draining.

### Tests for User Story 2

- [x] T028 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/EnabledDisabledLifecycleTests.cs` for LC-05/15..17: enabled handler/worker after complete ready, delayed live pipeline safe 503, disabled ordinary 404 and zero construction/service/map/init/probe/worker/stop/connection counters, including incompatible-but-structurally-valid disabled declarations.
- [x] T029 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/OwnedRouteTests.cs` for LC-18..19: renamed parameters, case/trailing-separator equivalents, intersecting method sets, same-owner duplicates and unowned overlap fail before serving; disjoint methods/literals, unique literal precedence and disabled claimant pass. Reject unsupported constraints/optional/default/complex/catch-all patterns, methodless routes, nondefault order, dynamic sources/policies, undeclared responsibilities and missing mappings, while preserving host middleware/access policy.
- [x] T030 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/LifecycleReadinessTests.cs` for LC-17/24..25/30: initial and subsequent false/throw/stall/invalid probe output, required versus optional observations, no-probe explicit status, disabled zero probes, one in-flight aggregate assessment, cancelled waiter isolation and late completion after stop; later loss/recovery changes health only, not selection/admission/drain.
- [x] T031 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/WorkerAdmissionTests.cs` for LC-15/17/26/31: whole RunAsync callback admitted once only after complete readiness, no-worker completion valid, independent hosted services rejected, worker fault closes admission/requests shutdown with no retry, and stop cancels/drains an already admitted callback without claiming per-iteration gating.

### Implementation for User Story 2

- [x] T032 [P] [US2] Create self-contained `tests/fixtures/lifecycle/Protocol.One/Hoard.Fixtures.Lifecycle.Protocol.One.csproj` and `ProtocolOneModule.cs` with an independent Fixture declaration, `IProtocolProvider`, approved Hosting adapter, declared test responsibility/handler, instrumented worker/readiness/phase controls and safe counters; label any NuGet wording lifecycle-only, never implement native registry/cache/upstream behavior.
- [x] T033 [P] [US2] Create self-contained `tests/fixtures/lifecycle/Protocol.Two/Hoard.Fixtures.Lifecycle.Protocol.Two.csproj` and `ProtocolTwoModule.cs` with distinct ID/test route, Fixture provenance and its own approved Hosting adapter/instrumentation; no source/package reference to Protocol.One or other fixtures.
- [x] T034 [P] [US2] Create self-contained `tests/fixtures/lifecycle/Metadata/Hoard.Fixtures.Lifecycle.Metadata.csproj` and `MetadataProvider.cs` using Abstractions only, one matching metadata marker, a static Fixture declaration and test resource/connection counters usable through public fixture APIs; no Hosting/EF/Core/provider edge, schema or database operation.
- [x] T035 [P] [US2] Create self-contained `tests/fixtures/lifecycle/Artifact.One/Hoard.Fixtures.Lifecycle.Artifact.One.csproj` and `ArtifactOneProvider.cs` using Abstractions only, Fixture provenance, public test controls and a distinct artifact ID; no Hosting/other provider dependency or real artifact-store/integrity/publication claim.
- [x] T036 [P] [US2] Create self-contained `tests/fixtures/lifecycle/Artifact.Two/Hoard.Fixtures.Lifecycle.Artifact.Two.csproj` and `ArtifactTwoProvider.cs` independently using Abstractions only, public test controls and an ID distinct from Artifact.One so both packages may be bundled but only one enabled; no shared fixture source/project/package edge or byte-store equivalence claim.
- [x] T037 [P] [US2] Create self-contained `tests/fixtures/lifecycle/Identity/Hoard.Fixtures.Lifecycle.Identity.csproj` and `IdentityModule.cs` with Fixture provenance, identity marker and approved Hosting adapter/instrumentation; add no login, token, authorization, external identity or permission behavior.
- [x] T038 [US2] Complete `src/Hoard.Hosting/Routing/HoardModuleEndpointBuilder.cs` and `HoardOwnedRoute.cs` with framework-parsed absolute literal/required whole-parameter routes, unique parameter names and explicit nonempty uppercase standard-method sets with HEAD explicit; immutable owner/responsibility/precedence/default-order data and internal RequestDelegate only. Require declared responsibility IDs and mapping completeness; reject unsupported matching metadata/patterns rather than pretending arbitrary matching is analyzable.
- [x] T039 [US2] Implement `src/Hoard.Hosting/Routing/HoardRouteOwnershipValidator.cs`: inspect finalized enabled-owned and relevant host endpoint sources, normalize actual framework case/root/trailing-slash semantics, compare path-language intersection, method overlap and equal framework priority, and report both safe owners for same-owner/cross-owner ambiguity; allow disjoint/unique-precedence counterparts, reject unanalyzable unowned/policy/dynamic/order shapes and validate any separately admitted diagnostic namespace as disjoint.
- [x] T040 [US2] Implement `src/Hoard.Hosting/Routing/HoardModuleAdmissionMiddleware.cs` and `src/Hoard.Hosting/Lifecycle/HoardActivityTracker.cs` with atomic startup/stop admission and per-owner request/resource leases retained through response-body completion; blocked mapped traffic gets fixed safe 503, disabled routes stay unmapped/404, and host access policy/middleware is not bypassed. Track request/worker/phase/build activity for later reverse-cleanup/root safety without adding a public management endpoint.
- [x] T041 [US2] Add `src/Hoard.Hosting/Lifecycle/HoardReadinessAssessor.cs` using T025's evaluator and one shared finite assessment deadline/task: enabled probes only, safe reason/owner observations, explicit readiness recovery for identical selection, caller-wait cancellation isolation and no stale publication after stop/failure; later not-ready does not close startup admission or trigger automatic drain/replacement.
- [x] T042 [US2] Implement `src/Hoard.Hosting/Lifecycle/HoardWorkerSupervisor.cs` to admit each enabled RunAsync callback once after complete ready, track its lifetime/stop token and unexpected faults, accept inert completed tasks, and fail/not-ready/close admission/request host stop on worker failure without retry or replacement.
- [x] T043 [US2] Wire T038..T042 into `src/Hoard.Hosting/Lifecycle/HoardApplicationExtensions.cs`, `HoardLifecycleHostedService.cs` and `HoardLifecycleCoordinator.cs`: finalize route gate before initialization/traffic, retain lease ownership, enforce missing-map failure and independent startup protection even with concurrent Generic Host startup/server ordering, and preserve all US1 invariants.
- [x] T044 [US2] Extend `scripts/lifecycle_evidence.py` to separately copy/restore/build/pack all six lifecycle fixture projects outside repository props inheritance with explicit local package mapping, isolated caches and retained source/SHA-512/assets/nuspec evidence; bootstrap/replay each tracked lock and reject inter-fixture references or missing local proof, without rewriting F-01 fixture/example sources.
- [x] T045 [US2] Run T028..T031's red-to-green TestServer/worker/readiness suites and independently prepared six-package proof through `scripts/validate-lifecycle.sh`, record LC-15..19/24..25/31 and disabled zero counters, and rerun US1 selections through the same integrated pipeline with every barrier/task released before test exit.

**Checkpoint**: US2 supplies fixture-only enabled/disabled route and work
isolation. TestServer is not TCP/proxy/TLS drain or native-client evidence.

## Phase 5: User Story 3 - Fail and Stop Without Hiding Partial Startup (Priority: P1)

**Goal**: Bound coordination, retain primary failures, stop once in reverse
dependency order, and never dispose resources still used by pending work.

**Independent Test**: Inject failure/cancellation/timeout at each phase and
position, race stop against readiness, and hold requests/response streams,
workers/build/callbacks beyond budgets. Assert no late work/admission, explicit
incomplete outcomes, safe independent cleanup, and protected owner/dependencies/
root; release/observe all deliberately non-cooperative test work afterward.

### Tests for User Story 3

- [x] T046 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/LifecyclePhaseFailureTests.cs` for LC-20..21/27: constructor/service/build/map/init failures at each position, constructor self-cleanup versus returned partial adapters, never-entered modules, no later dependent initialization, reverse entered cleanup, no ready/work and original failure retention.
- [x] T047 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/LifecycleDeadlineTests.cs` for LC-22..23/29: stop/cancellation in every phase and just before ready, fake-time outer/inner expiry, blocked synchronous composition/host build, expired pause before bridge start and late poisoned build completion; finite coordination never publishes a late app or reuses mutable poisoned state.
- [x] T048 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/LifecycleCleanupTests.cs` for LC-26..29: readiness/admission closes before cooperative drain, reverse cleanup after failure, extra cleanup errors with primary retained, outer deadline not multiplied, explicit budget/timeout/unsafe omissions and continued independent safe cleanup. Hold request/response-body leases and worker/phase/build activity; owners/prerequisites/root stay undisposed. Also hold A.StopAsync beyond its callback budget with A -> B and unrelated C: A retains TimedOut and one attempt, B/root stay protected while A runs, C cleans up within the same outer budget. Release/observe A after the bounded result and assert no outcome rewrite, retry or deferred disposal. DI/adapter resources are never disposed twice; root-disposer failure/stall is distinct from release.
- [x] T049 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/LifecycleConcurrencyTests.cs` for LC-22/30: shared repeated/concurrent start/stop/lease disposal, host stop during build/init/readiness and immediately before admission, cancelled caller waits, concurrent assessments and terminal-instance restart rejection; phase/cleanup/root-disposal attempt counts stay at most once.

### Implementation for User Story 3

- [x] T050 [US3] Implement `src/Hoard.Hosting/Lifecycle/HoardCleanupPlanner.cs` from entered ledger and active dependency edges: returned partial/failing adapters included, never-returned constructor excluded, reverse validated order with dependencies retained during executing dependent cleanup, pending request/response/worker/phase/build protection propagated to prerequisites, and independent safe entries still eligible. Phase explicitly includes non-completed StopAsync after its wait times out; preserve its TimedOut outcome and affected prerequisite UnsafePendingCallback omissions under one stop deadline.
- [x] T051 [US3] Complete stop/drain orchestration in `src/Hoard.Hosting/Lifecycle/HoardLifecycleCoordinator.cs` using T040/T042/T050: atomically close readiness/admission and latch cancellation before drain, share one stop result, cap drain/each cleanup by remaining overall budget, preserve original plus additional failures and prevent any later callback/start/admission; cancellation, terminal state or a timed-out StopAsync wait never implies callback quiescence or released resources. Safe remaining cleanup uses the original deadline, not a new round/budget.
- [x] T052 [US3] Complete `src/Hoard.Hosting/Lifecycle/HoardServiceComposition.cs` root ownership/disposal and `HoardApplicationExtensions.cs` build supervision: root disposal only after global quiescence, including non-completed timed-out StopAsync tasks, and eligible module cleanup; externally owned lease never recursively disposed by DI, pending build protects all potentially used resources, and root timeout/failure/budget/NotAttemptedUnsafe omission is explicit. Never return a poisoned late application or dispose underneath active work.
- [x] T053 [US3] Harden `src/Hoard.Hosting/Lifecycle/ActivationLedger.cs`, `HoardActivityTracker.cs` and `HoardWorkerSupervisor.cs` against late completions/faults and stop-dispatch races, recording StopAsync as pending Phase activity before dispatch and observing actual completion independently from its TimedOut result. Preserve once-only stop/cleanup/resource ownership and worker admission; after publishing the stop result, late completion/fault cannot rewrite outcomes, retry cleanup or trigger deferred dependency/root disposal. No forced thread termination, automatic retry or instance reuse.
- [x] T054 [US3] Extend `scripts/lifecycle_evidence.py`'s focused runner to execute phase/deadline/cleanup/concurrency cases with nonempty test-result counts and bounded subprocesses, preserving safe failure evidence; include fake-time exact arithmetic and documented scheduler tolerance only for final real-time integration backstops.
- [x] T055 [US3] Run T046..T049 red-to-green and integrated US1/US2 regressions through `scripts/validate-lifecycle.sh`, record LC-20..23/26..30, protected request/response/worker/build/cleanup resources and explicit root outcomes in `specs/002-module-lifecycle/plan.md`'s implementation evidence. Include the held A.StopAsync -> B plus independent C proof; all test-created pending work is released/observed, not abandoned after timeout.

**Checkpoint**: P1 lifecycle behavior is demonstrated in fixtures, including
truthful incomplete cleanup. No forced termination, crash cleanup, schema/data
rollback or actual storage recovery is proved.

## Phase 6: User Story 4 - Correct a Composition from Safe Diagnostics (Priority: P2)

**Goal**: Make every rejection/failure actionable without exposing arbitrary
provider data, and expose truthful immutable state without inventing discovery.

**Independent Test**: Capture normal logs, results and serialized failures for
each invalid/failing LC row with seeded credential/URL/path/option/text secrets.
Require safe identity or ordinal, phase, rule/path, action and correlation,
zero seeded values, bounded omission markers and accurate selected/ready state.

### Tests for User Story 4

- [x] T056 [P] [US4] Write failing `tests/integration/Hoard.Composition.Tests/LifecycleDiagnosticTests.cs` applying LC-32..33 to every invalid/failing LC-02..14/18..23/25/28..31 case, including malformed identity/provenance, nested/cleanup/late exceptions and arbitrary secret-bearing text; assert captured normal logs/results/serialization contain no seeded values or raw inner exception, but retain safe module/ordinal, phase, rule/path, action, correlation, primary/cleanup classification and bounded truncation/omitted counts.
- [x] T057 [P] [US4] Write failing `tests/integration/Hoard.Composition.Tests/LifecycleInventoryTests.cs` for LC-34 across registered-disabled, enabled-uninitialized, phase failures, ready/not-ready/recovered/stopping/stopped and incomplete cleanup; build inclusion is only IncludedByRegistration, not exhaustive installed inventory, and no declared/disabled capability becomes an active integration or production support claim.

### Implementation for User Story 4

- [x] T058 [US4] Complete the catalogue/bounding implementation in `src/Hoard.Hosting/Lifecycle/HoardLifecycleDiagnostic.cs` and `HoardLifecycleException.cs`, and wire all validator/coordinator/route/cleanup/late-fault diagnostic call sites under `src/Hoard.Hosting/`: unsafe identities use registration ordinals; "bound messages to 512 characters, paths to 32 IDs and diagnostic collections to 100 entries with an explicit omitted-count marker." Never copy provider descriptions, exception text/stack/inner exception, options, paths or URLs into normal results/logs; expected failures remain explicit, null misuse remains standard argument errors.
- [x] T059 [US4] Complete immutable observations/snapshot publication in `src/Hoard.Hosting/Lifecycle/HoardLifecycleSnapshot.cs` and `HoardLifecycleCoordinator.cs`, separating registration build inclusion, fixed enabled IDs, actual phase/status, startup admission, current readiness, failure and incomplete release; publish only safe declared IDs/reason codes and no delegates/options/operational support inference, HTTP discovery or provider internals.
- [x] T060 [US4] Run T056/T057 through `scripts/validate-lifecycle.sh` against all integrated invalid/failing paths, record LC-32..34 and SC-005 zero-seeded-secret proof with no unexercised rejection class, and document the safe diagnostic/action catalogue in `specs/002-module-lifecycle/quickstart.md` without raw captured secrets.

**Checkpoint**: Safe state/errors are operationally inspectable through library
results only. F-04 still owns authorized management discovery and UI.

## Phase 7: User Story 5 - Change a Distribution with Explicit Restart (Priority: P2)

**Goal**: Prove bundled choice changes need only a new lifecycle, while an
independent package needs a custom rebuild/redeploy; retain API compatibility.

**Independent Test**: Build the baseline fixture host once, switch bundled
protocol selections only after stop/new start, then add Artifact.Two via the
custom package-only host variant without Core/unrelated provider changes.
An invalid replacement fails; explicitly restoring the coherent prior set in a
new instance recovers. Separately run old compiled registration consumers.

### Tests for User Story 5

- [x] T061 [US5] Write failing `tests/integration/Hoard.Composition.Tests/LifecycleRestartTests.cs` for LC-13/35/37: caller mutation/in-place replacement never changes a running selection, new lifecycle validates bundled alternative without rebuild, invalid replacement has no automatic rollback, and explicit previous coherent registration/selection plus new start recovers; no provider data/schema rollback is inferred.
- [x] T062 [P] [US5] Add standalone `tests/fixtures/lifecycle/registration/RegistrationConsumer/RegistrationConsumer.csproj` and `Program.cs` to exercise unchanged AddHoard/AddModule/family/declaration paths and inert legacy registrations; in `scripts/lifecycle_evidence.py`, compile it against packages built from verified merged F-01 commit `837fdf3edf51c3df34710184d018479683c194c2` in an isolated baseline directory, retain that binary, then run it against new Hosting/dependencies without recompiling. Separately compile the same source against new packages and add a non-web consumer probe for packed shared-framework propagation/deployment requirements (LC-39).

### Implementation for User Story 5

- [x] T063 [P] [US5] Create package-only `examples/LifecycleHost/LifecycleHost.csproj`, `Program.cs`, `Adapters/MetadataModule.cs`, `Adapters/ArtifactOneModule.cs` and `Adapters/ArtifactTwoModule.cs`, plus `Custom/LifecycleHost.Custom.csproj`: baseline includes two protocol choices, metadata, Artifact.One and optional identity; the custom variant additionally references independent Artifact.Two. Keep metadata/artifact adapters host-owned; use explicit in-memory selection, supervised build/mapping, normal app start/stop and sole lease disposal, TestServer bounded journeys and self-asserting nonzero event/results, never bare Build/independent app disposal/host RunAsync or a real listener.
- [x] T064 [US5] Complete source/old-binary/package/framework compatibility preparation and assertions in `scripts/lifecycle_evidence.py` for LC-39: isolated explicit feeds/caches, tracked standalone locks, retained old consumer hash, no recompile before the binary run, new source compilation, packed nuspec/framework/asset inspection and standalone framework resolution; report Hosting's new runtime prerequisite explicitly rather than labelling it an API break or unchanged deployment.
- [x] T065 [US5] Extend `scripts/lifecycle_evidence.py` to independently locked-restore/build/execute baseline and custom `examples/LifecycleHost/` variants against only just-packed platform/fixture packages: prove Artifact.Two absent from baseline references/registrations; LC-35 swaps bundled Protocol.One/Protocol.Two using the same binary and Artifact.One, LC-36 adds Artifact.Two/registration/host adapter through custom rebuild/redeploy/new start, LC-37 invalid replacement fails then explicit prior set recovers. Compare Core/unrelated-provider source hashes and package provenance; reject missing/empty journey results.
- [x] T066 [US5] Write `examples/LifecycleHost/README.md` and update `docs/PROVIDERS.md` with actual public phase/selection/adapter APIs and the two fixture journeys, shared-framework/dependency requirements, fixed selections, finite budgets, sole root/resource ownership, diagnostic recovery and trusted-code limits; keep F-01's `examples/CustomHost/README.md` compile-only purpose and sources intact, and state that F-03 owns config/secrets UX rather than inventing a parser.
- [x] T067 [US5] Execute T061 and T064/T065 through `scripts/validate-lifecycle.sh`, record LC-13/35..37/39, exact commands/results and old-binary-versus-new-source/framework evidence in `specs/002-module-lifecycle/plan.md`; no rebuilt consumer, ProjectReference/source import, live listener or successful restore alone substitutes for these proofs.

**Checkpoint**: Both fixture distribution journeys and registration compatibility
have measured evidence; no curated product, published package or native client
is delivered.

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Complete actual dependency/API graphs, default locked acceptance,
architecture review and honest operational/support documentation for all stories.

- [x] T068 Write focused negative/permitted counterpart regressions in `tests/architecture/Hoard.Architecture.Tests/LifecycleBoundaryTests.cs`, then extend `scripts/lifecycle_evidence.py`'s actual project/packed/transitive/API scans using existing inspectors: Hosting HTTP/versioning allowed, Abstractions/Core provider-free, Metadata/Artifact Abstractions-only with no Hosting edge, host-owned adapters and no provider-to-provider/cross-slice coupling. Validate every lifecycle fixture/host and packed framework graph (LC-38); missing/unclassified input fails and all eight F-01 rules/real scans and Identity-via-Hosting exception remain intact.
- [x] T069 Complete `scripts/validate-lifecycle.sh` and `scripts/lifecycle_evidence.py` full/default acceptance: locked source/standalone restores, SDK formatting/analyzers including copied fixtures/consumers/hosts, prepared local package/hash/framework provenance, nonempty focused/full test and journey results, compatibility/boundary proofs, precise partial/full summaries and fail-fast errors. Keep T002 regressions passing; review initial/new and necessarily affected existing locks, then run an independent fresh default replay that never rewrites them or recursively invokes itself from tests.
- [x] T070 Update `README.md`, `docs/DEVELOPMENT.md`, `docs/PROVIDERS.md`, `examples/LifecycleHost/README.md`, `specs/002-module-lifecycle/quickstart.md` and `plan.md` with measured commands/evidence and LC-40 support audit: exact budgets, admission versus readiness/liveness, cleanup/root ownership, unsafe/failed/budget-exhausted omissions, process-level recovery, restart/rebuild and framework impact. Map all FR/SC/LC proofs; distinguish fixtures/TestServer from real provider/native-client/transport/certification support, keep later F-03/F-04/store/conformance/security/UI/curated-host boundaries, and record explicit unaffected-guide/diagram/IaC/release reasons without changing reviewer-owned markers.
- [x] T071 Obtain bounded `hoard-architecture-review` of actual `src/Hoard.Hosting/`, lifecycle fixtures/host adapters, project/packed/transitive/public API graphs and implemented startup/admission/cleanup/resource ownership, using `specs/002-module-lifecycle/contracts/acceptance.md` as proof scope; resolve findings with focused regressions and record concrete review references/remaining blockers in `specs/002-module-lifecycle/plan.md`, never infer approval from the earlier design review.
- [x] T072 Run `bash scripts/validate-lifecycle.sh`, `bash scripts/validate-foundation.sh`, `python3 -m unittest discover -s tests/tooling -v` and `git diff --check`; record actual test/journey counts, zero missing/skipped/empty proof, locked replay and architecture review in `specs/002-module-lifecycle/plan.md`. Audit all LC-01..40, 22 FRs, seven SCs, 20 story scenarios and 12 edge cases, retaining all custom checklist markers; unresolved acceptance/review failures block completion. This implements tasks only: convergence, finalization, PR readiness, merge and dependency completion remain separate driver stages.

## Dependencies & Execution Order

### Phase and User Story Dependencies

```text
Setup T001..T004 -> Foundation T005..T013
  -> US1 T014..T027 -> US2 T028..T045 -> US3 T046..T055
  -> US4 T056..T060 -> US5 T061..T067 -> Polish T068..T072
```

US2 uses US1's validated selection/start and completes routing/readiness/work
admission. US3 uses their actual requests/workers for stop/resource proofs.
US4 applies diagnostics to all integrated failure paths. US5 uses the safe
lifecycle plus independent packages. These are real shared-mechanism
dependencies, not a claim that stories can all implement concurrently.
Each checkpoint has an independent bounded oracle and preserves earlier proofs.

### Task Prerequisites

`Tnnn..Tmmm` means every inclusive task ID. Rows assign direct prerequisites;
their transitive closure also applies. Earlier-story completion gates are
intentional. Unmarked tasks may edit multiple shared files and are serialized.

| Task(s) | Direct prerequisites |
| --- | --- |
| T001 | None |
| T002, T004 | T001 |
| T003 | T001, T002 |
| T005 | T003, T004 |
| T006 | T005 |
| T007, T008 | T006 |
| T009 | T004, T007, T008 |
| T010 | T009 |
| T011 | T010 |
| T012 | T011 |
| T013 | T003, T012 |
| T014..T018 | T013 |
| T019 | T015 |
| T020 | T014, T017 |
| T021 | T016, T019, T020 |
| T022 | T017, T021 |
| T023 | T018, T022 |
| T024 | T023 |
| T025 | T018, T024 |
| T026 | T025 |
| T027 | T003, T014..T018, T026 |
| T028..T037 | T027 |
| T038 | T029 |
| T039 | T038 |
| T040 | T028, T039 |
| T041 | T030, T040 |
| T042 | T031, T041 |
| T043 | T042 |
| T044 | T027, T032..T037 |
| T045 | T028..T031, T043, T044 |
| T046..T049 | T045 |
| T050 | T046, T047, T048 |
| T051 | T049, T050 |
| T052 | T051 |
| T053 | T052 |
| T054 | T044, T053 |
| T055 | T046..T049, T054 |
| T056, T057 | T055 |
| T058 | T056, T057 |
| T059 | T058 |
| T060 | T054, T059 |
| T061 | T060 |
| T062, T063 | T061 |
| T064 | T054, T062, T063 |
| T065 | T061, T064 |
| T066 | T065 |
| T067 | T061, T065, T066 |
| T068 | T067 |
| T069 | T002, T068 |
| T070 | T069 |
| T071 | T070 |
| T072 | T071 |

T003 -> T027 -> T044 -> T054 -> T064 -> T065 -> T068 -> T069
serializes `scripts/lifecycle_evidence.py` edits; T062 edits that helper before
T064, while T063 works on the example only. T010..T012, T023..T026,
T038..T043, T050..T053 and T058..T059 serialize shared state/route/lease files.
T066 precedes T070 on documentation and T001 precedes any project/dependency
edits. Parallel fixture tasks share no source/project/package dependency.

### Parallel Examples per Story

These are file-disjoint work sets, not agent launch instructions:

| Story / point | Parallel task set | Separate destinations |
| --- | --- | --- |
| US1 after T013 | T014, T015, T016, T017, T018 | Five independent validation/startup test files |
| US1 after T014, T015, T017 | T019, T020 | RuntimeCompatibility.cs and RegistryValidator.cs |
| US2 after T027 | T028..T037 | Four test files and six self-contained fixture directories |
| US3 after T045 | T046, T047, T048, T049 | Four phase/deadline/cleanup/concurrency test files |
| US4 after T055 | T056, T057 | Diagnostic and inventory test files |
| US5 after T061 | T062, T063 | Legacy consumer/helper versus new example/host adapters |

Common setup also permits T002 with T004 after T001, and foundational T007
with T008 after T006. `[P]` never means a task can ignore its prerequisites,
share mutable coordinator edits or run the shared orchestrator concurrently.

## Requirement and Proof Traceability

The [acceptance matrix](contracts/acceptance.md#requirement-coverage) remains
the source of FR/SC/scenario-to-LC mappings. This table assigns every LC case
to implementation and a focused proof task; T069/T072 retain full acceptance.

| Case | Implementation / prepared evidence tasks | Focused proof tasks |
| --- | --- | --- |
| LC-01 | T021, T025, T026 | T016, T018, T027 |
| LC-02 | T020, T022 | T014, T027 |
| LC-03 | T020 | T014, T027 |
| LC-04 | T019, T020 | T014, T027 |
| LC-05 | T020, T022 | T014, T028, T045 |
| LC-06 | T019, T021 | T015, T027 |
| LC-07 | T021 | T016, T027 |
| LC-08 | T021, T025 | T016, T018, T027 |
| LC-09 | T019, T021 | T015, T016, T027 |
| LC-10 | T020, T021 | T016, T027 |
| LC-11 | T021 | T016, T027 |
| LC-12 | T019, T021 | T015, T016, T027 |
| LC-13 | T022, T065 | T017, T061, T067 |
| LC-14 | T007, T020, T022 | T005, T014, T017, T027 |
| LC-15 | T032, T038..T043 | T028, T031, T045 |
| LC-16 | T023..T026, T038..T043 | T028, T045 |
| LC-17 | T025, T026, T040..T043 | T018, T028, T030, T031, T045 |
| LC-18 | T038, T039, T043 | T029, T045 |
| LC-19 | T038, T039, T043 | T029, T045 |
| LC-20 | T023, T024, T050..T053 | T046, T055 |
| LC-21 | T025, T026, T050, T051 | T046, T055 |
| LC-22 | T012, T026, T051..T053 | T047, T049, T055 |
| LC-23 | T010, T023..T026, T052, T053 | T009, T047, T055 |
| LC-24 | T025, T041, T043 | T030, T045 |
| LC-25 | T025, T041 | T018, T030, T045 |
| LC-26 | T040, T042, T050..T053 | T031, T048, T055 |
| LC-27 | T023, T050, T051 | T046, T048, T055 |
| LC-28 | T050..T053 | T048, T055 |
| LC-29 | T010, T024, T040, T050..T053 | T047, T048, T055 |
| LC-30 | T012, T041, T051..T053 | T030, T049, T055 |
| LC-31 | T023, T042, T043 | T031, T045 |
| LC-32 | T008, T058 | T056, T060 |
| LC-33 | T008, T058 | T056, T060 |
| LC-34 | T008, T059 | T057, T060 |
| LC-35 | T022, T063, T065 | T061, T067 |
| LC-36 | T034..T037, T044, T063, T065 | T065, T067 |
| LC-37 | T012, T063, T065 | T061, T065, T067 |
| LC-38 | T001, T044, T065, T068 | T068, T071, T072 |
| LC-39 | T001, T062..T064 | T062, T064, T067 |
| LC-40 | T066, T070 | T070..T072 |

Every functional requirement and outcome has both implementation and proof
assignments (ranges below are inclusive, not a claim of completed tests):

| Requirement / outcome | Implementation tasks | Proof / acceptance tasks |
| --- | --- | --- |
| FR-001 | T007, T020, T022, T044, T063..T065 | T014, T017, T027, T057, T062, T067, T068 |
| FR-002 | T008, T025, T041, T059, T070 | T018, T030, T057, T060, T072 |
| FR-003 | T021, T022 | T014, T016, T017, T027 |
| FR-004 | T019..T022 | T014, T017, T027 |
| FR-005 | T019, T021 | T015, T016, T027 |
| FR-006 | T019, T021 | T015, T016, T027 |
| FR-007 | T020, T021, T025 | T016, T018, T027 |
| FR-008 | T019..T026, T052, T053 | T014..T018, T027, T046, T047, T055 |
| FR-009 | T020, T023..T026, T038..T043 | T014, T028..T030, T045 |
| FR-010 | T023, T032..T043 | T028, T029, T031, T045 |
| FR-011 | T010, T025, T026, T040..T043 | T016, T018, T028, T031, T047, T055 |
| FR-012 | T025, T026, T041, T042, T051..T053 | T028, T030, T031, T046, T047, T055 |
| FR-013 | T025, T026, T040..T043, T051..T053 | T028, T030, T047..T049, T055 |
| FR-014 | T025, T041 | T030, T049, T055 |
| FR-015 | T023..T026, T050..T053 | T046..T049, T055 |
| FR-016 | T040, T042, T050..T053 | T031, T047..T049, T055 |
| FR-017 | T008, T050..T053, T058 | T048, T055, T056, T060 |
| FR-018 | T012, T041, T051..T053 | T030, T047, T049, T055 |
| FR-019 | T003, T004, T032..T037, T044, T054, T063..T065, T068..T070 | T013, T027, T045, T055, T060, T067, T072 |
| FR-020 | T008, T019..T026, T039, T041, T050..T053, T058 | T014..T018, T029, T030, T046..T049, T056, T060 |
| FR-021 | T012, T022, T063, T065 | T017, T061, T067 |
| FR-022 | T008, T059, T063, T066, T070 | T057, T060, T067, T068, T071, T072 |
| SC-001 | T019..T026 | T014..T018, T027 |
| SC-002 | T023..T026, T032..T043 | T028, T031, T045 |
| SC-003 | T010, T012, T025, T026, T040..T043, T051..T053 | T018, T028, T030, T031, T046..T049, T055 |
| SC-004 | T010..T012, T023, T024, T040, T050..T053 | T046..T049, T055 |
| SC-005 | T008, T058 | T056, T060 |
| SC-006 | T022, T062..T065 | T017, T061, T064, T067 |
| SC-007 | T008, T044, T059, T063, T066, T068, T070 | T057, T060, T067, T068, T071, T072 |

All 20 story scenarios inherit the unchanged scenario-to-LC mapping in
[acceptance.md](contracts/acceptance.md#outcome-and-story-coverage). T072 audits
the 12 specification edge cases against the same tests; they are not deferred
to generic conformance or later product features.

## Implementation Strategy

### MVP First (US1)

1. Obtain read-only analysis and reviewer-owned implementation authorization
   through the separate driver stages; this task list grants neither.
2. Complete T001..T013, then T014..T027. Observe intended red failures before
   fixes and run the isolated endpoint-free selection/start proof.
3. Stop at the bounded fixture checkpoint if requested. US1 alone is not a
   shippable lifecycle, usable cache, or ready-to-merge F-02 feature.

### Incremental Delivery

1. Add enabled/disabled HTTP/worker isolation and health (US2), then failure/
   deadline/drain/resource safety (US3), preserving the earlier oracles.
2. Apply the safe diagnostic/state matrix to every integrated failure (US4),
   then prove package-only restart/custom/compatibility journeys (US5).
3. Complete actual architecture graphs, locked replay, all docs/support claims
   and implementation architecture review in T068..T072. Re-run checks only
   after changed inputs/findings justify it; never replace focused red/green
   proof with an undifferentiated passing suite.
4. Commit coherent implementation checkpoints and push immediately under
   repository workflow. Converge/finalize/await-merge remain separate
   invocations; no merge, deployment, infrastructure apply, release tag or
   package publication is authorized.

## Notes

- One metadata gate, one version policy, one coordinator and one disposal owner;
  no generic plugin bus, configuration framework, arbitrary route solver or
  per-slice duplicate cache/security invariant.
- Constructor/phase callbacks run trusted in-process code, not sandboxed code.
  Finite waiting cannot forcibly stop arbitrary work; report incomplete release
  and document explicit process recovery rather than silently succeeding.
- Check task boxes only against actual evidence in an authorized implementation
  stage. Never edit the reviewer-owned checklist markers to satisfy the gate.

## Phase 9: Convergence

- [x] T073 CRITICAL: Supervise worker-failure host-shutdown notification outside the coordinator state lock in `src/Hoard.Hosting/Lifecycle/HoardLifecycleCoordinator.cs`, retaining once-only shutdown and tracked pending notification/cancellation activity through `HoardActivityTracker.cs` and `HoardServiceComposition.cs` as needed. The current worker-fault branch calls `IHostApplicationLifetime.StopApplication()` while holding `Gate`; a barrier-held synchronous `ApplicationStopping` callback blocks both `IHoardLifecycle.StopAsync` and snapshot access beyond the original shutdown deadline (isolated diagnostic: both still blocked after 1,001 ms with a 200 ms shutdown budget). Close admission/readiness and preserve WorkerFailure atomically, but dispatch potentially blocking framework notification/service resolution without holding the state lock; keep stop coordination bounded by the same absolute deadline and explicitly protect all resources/root that pending host callbacks may use. Add deterministic barrier/virtual-time regressions in `tests/integration/Hoard.Composition.Tests/WorkerAdmissionTests.cs` and `LifecycleOwnershipTests.cs` proving prompt snapshot access, bounded incomplete stop while notification is held, no unsafe module/root disposal, once-only shutdown/cleanup, safe primary/additional diagnostics, and no late result rewrite/retry/deferred disposal after release; retain the cooperative worker-fault counterpart. Obtain the required bounded implementation architecture review, refresh only necessarily affected reviewed packed-consumer locks, rerun default locked lifecycle/foundation/tooling acceptance, and update measured evidence/support documentation without changing reviewer-owned checklist markers, per Constitution IV/VI, FR-016/FR-017/FR-018/FR-020, SC-004/SC-005, plan: finite shutdown and sole resource ownership, and T042/T051/T053/T071/T072 (contradicts).

## Phase 10: Convergence

- [x] T074 HIGH: Report faults from supervised cancellation callbacks in `src/Hoard.Hosting/Lifecycle/HoardLifecycleCoordinator.cs` instead of merely consuming their task exceptions. `StopCoreAsync` and `CancelPending` call `Observe` without an owner; `Observe` emits no diagnostic for those failures. An isolated public-API probe registered a throwing worker stop-token callback: it executed once, both module cleanups completed, lease `StopResult.Complete` was true, and module/final/snapshot diagnostics were all empty. Cover shared lifetime cancellation and readiness/cleanup timeout cancellation through the same safe diagnostic mechanism, preserving the original startup/worker/timeout failure alongside additional cancellation errors. Publish faults known before coordination completes before releasing their tracked activity/result publication; faults after a bounded result must appear safely in a later snapshot without rewriting returned results, retrying cleanup or triggering deferred disposal. Preserve truthful resource-release outcomes, once-only coordination, lock-free callback dispatch, the original deadline and pending-callback resource protection; do not equate a completed fault with still-running work or invent a second shutdown path. Add focused throwing/cooperative and barrier-held late-fault regressions in `tests/integration/Hoard.Composition.Tests/LifecycleCleanupTests.cs`, `LifecycleDeadlineTests.cs` and `LifecycleOwnershipTests.cs` as appropriate, with safe owner/phase/action/correlation and primary-versus-cleanup classification, zero seeded exception payloads in captured normal logs/results, no duplicate diagnostics for the same callback fault, and every pending test task released/observed. Obtain the bounded implementation architecture review, refresh only necessarily affected reviewed packed-consumer locks, rerun default locked lifecycle/foundation/tooling acceptance, and update measured evidence/support documentation without changing reviewer-owned checklist markers, per FR-017/FR-018/FR-020, SC-004/SC-005, plan: supervised cancellation and sanitized actionable diagnostics, LC-28..33, and T051/T053/T056/T058/T060/T071/T072 (partial).
