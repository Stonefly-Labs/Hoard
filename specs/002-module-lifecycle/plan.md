# Implementation Plan: Module Registry, Composition and Lifecycle

**Branch**: `feature/002-module-lifecycle` | **Date**: 2026-10-20
**Spec**: [spec.md](spec.md) | **Backlog**: F-02

**Input**: `specs/002-module-lifecycle/spec.md`, including its no-question
clarification review. Historical planning decisions below are retained; the
separately authorized implementation and its measured evidence are recorded
under [Implementation evidence](#implementation-evidence). Old F-01 registration
calls remain inert; lifecycle is explicitly opt-in.

## Summary

Extend the existing explicit `AddHoard` / `AddModule<TProvider>` boundary with
an opt-in Hosting lifecycle adapter and a metadata-only composition validator.
Freeze an explicit in-memory selection, validate the complete registry before
constructing adapters/providers, and topologically order enabled modules.
Compose enabled services before building DI; compose owned, analyzable HTTP
routes after build; then initialize, assess readiness, admit work, and stop
through one bounded coordinator. Never infer enablement from package presence.
The explicit supervised build API and composition lease own application/root
disposal; pending request/worker/phase/build activity prevents unsafe release.
Phase includes a StopAsync still executing after its cleanup wait timed out.

Reuse F-01's declaration shapes and compatibility policy without adding
required members or changing registration behavior. Keep persistence/storage
adapters on the host side, so their provider packages need no Hosting reference.
Prove lifecycle with independent fixture packages and in-process HTTP tests,
not a curated product, database, real NuGet implementation, or native-client
claim.

## Technical Context

**Language/Version**: Nullable-aware C#, .NET 10 / `net10.0`; existing SDK pin,
deterministic build, analyzers, and warnings-as-errors policy.

**Primary Dependencies**: Existing built-in DI and `NuGet.Versioning` policy;
proposed ASP.NET Core shared-framework reference in Hosting for HTTP integration,
and test-only `Microsoft.AspNetCore.TestHost` 10.x. Choose and lock its supported
stable patch at implementation. Reuse existing xUnit/test SDK/architecture
tooling. No new runtime framework, MediatR, configuration parser, or loader.
Production `NuGet.Versioning` belongs only in Hosting; its existing test-only
classifier is a policy oracle, not a runtime service to reference from product.

**Storage**: In-memory registrations, immutable selection/composition,
coordinator state, sanitized results, and test event ledgers only. No schema,
cache bytes, migrations, or persistent inventory.

**Testing**: Existing tooling unittest suite, F-01 locked foundation acceptance,
focused xUnit lifecycle/validator tests, TestServer route/admission tests,
architecture scans, and package-only custom lifecycle-host compilation/runs
using fixtures. Deterministic barriers and `TimeProvider`-based deadlines rather
than long sleeps; small real-time integration bounds only as a final backstop.

**Target Platform**: Existing .NET 10 developer/CI platforms; single-process,
single-node trusted composition. In-memory tests need no listener/cloud service.

**Project Type**: Packable Hosting library extension, independent fixture
libraries, tests, and a clearly labelled lifecycle-only custom-host example.
No production `Hoard.Host`, UI, product CI/CD, or infrastructure.

**Performance Goals**: Deterministic ordering and zero pre-validation
construction; zero disabled activity and premature admission; coordination
bounded by finite observable budgets. No throughput/production latency claim.
Topological sorting is O((V + E) log V) with an ordinal ready queue; route
ownership comparison is bounded by the declared route count (pairwise is
sufficient for this initial small startup registry).

**Constraints**: Explicit fixed selection; exactly one enabled Metadata and
one Artifact, any number of Protocol/Identity; no fallback, retry, hot reload,
arbitrary assembly loading, or sandbox claim. Defaults: 120-second overall
startup, 30-second individual activation callback, 5-second readiness assessment,
30-second overall stop including at most 10 seconds of drain and at most
5 seconds per module cleanup. All are validated positive finite durations;
inner deadlines are capped by remaining outer time. See
[lifecycle contract](contracts/lifecycle.md#budgets-and-non-cooperative-code).

**Scale/Scope**: All 22 FRs, seven SCs, five stories/20 scenarios, and 12 edge
cases. Four provider families, at least two independent artifact choices and
two bundled selectable protocol fixtures. No fixed production module limit or
certification matrix is invented. No unresolved technical clarification.

## Constitution Check

*Pre-research gate: PASS. Post-design gate: PASS subject to future proof below;
design alignment is not passing implementation evidence.*

| Principle / constraint | Design response and required evidence |
| --- | --- |
| I: cache-first / simple personal use | Fixture-only lifecycle; no publishing/cache feature, cloud, external DB, or mandatory service. Real NuGet remains the first later usable protocol. |
| II: contracts / composition | Preserve F-01 shapes/markers/APIs; validate registry, family, ranges, dependencies, capabilities and cardinality before construction; no disabled hooks or fallback. Packed providers and negative architecture scans must prove the graph. |
| III: VSA / shared correctness | Hosting owns lifecycle and admission once; protocol fixtures own their test handlers. Core/Application stay unchanged; no duplicated cache/auth/SSRF/GC mechanisms or cross-slice calls. |
| IV: bounded work / recovery | Linked cancellation, absolute deadlines, tracked entered phases, reverse cleanup, explicit incomplete results. No forced termination, schema reversal, or crash-cleanup promise. |
| V: security | No listener or management endpoint needed; safe catalogue diagnostics never copy provider exception messages/options. Future listener defaults remain loopback-first; no new auth bypass or upstream client. |
| VI: evidence | Acceptance matrix maps every FR/SC/story to focused positive/negative proofs. Red regressions precede fixes; fixtures and in-memory transport cannot certify production providers or native clients. |
| VII: static accessible console | No UI, Node, SSR, or discovery endpoint; future F-04/API consumers can consume immutable safe state, not provider internals. |
| VIII: operations / compatibility | Finite documented budgets, readiness distinct from liveness, fixed selection and restart/rebuild/explicit recovery guides; additive opt-in API, unchanged old registration-only binaries. |
| Workflow | Only plan in this invocation; custom checklists remain reviewer-owned and absent. No tasks, implementation, infrastructure action, publication, or merge. Commit/push checkpoint and retain draft PR. |

No exception, constitutional amendment, or new ADR is required: this design
implements the accepted baseline without claiming the illustrative baseline
signatures already exist. Post-design checks preserve the same boundaries.

## Project Structure

### Documentation (this feature)

```text
specs/002-module-lifecycle/
  spec.md
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/
    public-api.md
    lifecycle.md
    acceptance.md
  checklists/requirements.md
```

`tasks.md` and custom requirements-quality checklists are later-stage outputs,
not generated here.

### Source Code (repository root)

Proposed locations, not files created by this stage:

```text
src/Hoard.Hosting/
  Composition/                 metadata validator and immutable selection/order
  Lifecycle/                   coordinator, budgets, safe results and adapters
  Routing/                     owned route builder and startup conflict gate
src/Hoard.Abstractions/         existing declarations and markers unchanged
src/Hoard.Core/                 existing provider-free boundary unchanged
src/Hoard.Application/          existing management boundary unchanged
tests/unit/Hoard.Foundation.Tests/
                               retain old API/compatibility regressions
tests/integration/Hoard.Composition.Tests/
                               expand existing composition acceptance
tests/architecture/             retain and expand real dependency scans
tests/fixtures/lifecycle/
  Protocol.One/ Protocol.Two/ Metadata/ Artifact.One/ Artifact.Two/ Identity/
                               independent lifecycle fixture packages
examples/LifecycleHost/         package-only, fixture-only executable harness
scripts/validate-lifecycle.sh   proposed bounded validation orchestrator
```

**Structure Decision**: Extend the existing library and tests rather than
scaffold an application. Lifecycle fixtures are separate from F-01's unchanged
compile-only providers and `examples/CustomHost`. Host-side adapter source in
the lifecycle example composes metadata/artifact fixtures without reversing
provider dependencies. Preserve F-01 `validate-foundation.sh` behavior; a new
bounded lifecycle orchestrator owns its extra packed/test evidence and locks,
not an unrelated CI system.

## Phase 0: Research Decisions

[research.md](research.md) resolves lifecycle integration, compatibility reuse,
adapter ownership, analyzable routes, deadlines, and safe diagnostics. Generic
Host cancellation does not forcibly terminate code, and runtime route matching
does not offer a complete arbitrary-overlap startup proof. The design owns
both obligations explicitly rather than assuming framework defaults solve them.

## Phase 1: Design and Contracts

- [data-model.md](data-model.md): immutable inputs, validation rules, states,
  route ownership, readiness observations, diagnostics and cleanup evidence.
- [public-api.md](contracts/public-api.md): proposed opt-in library surface and
  assembly/dependency ownership, with unchanged registration compatibility.
- [lifecycle.md](contracts/lifecycle.md): ordered phases, route matching scope,
  traffic/worker admission, cancellation, stop races and finite cleanup.
- [acceptance.md](contracts/acceptance.md): LC-01 through LC-40, requirement/
  outcome/story traceability and architecture/package proof obligations.
- [quickstart.md](quickstart.md): current versus future commands and repeatable
  fixture-only validation/restart/custom distribution journeys.

The validator is the single safety gate F-03 must call after resolving future
configuration. F-02 introduces explicit `RequiredCapability` inputs rather than
silently treating F-01's capability declarations as requirements; F-03 may
translate configured requirements into this same representation. F-04 owns
authorized discovery, F-05/F-06 operations and recovery, F-07 conformance,
F-08 detailed identity, SPEC-01 the curated host, and SPEC-09 native clients.

## Requirement and Acceptance Traceability

The complete mapping is in
[acceptance.md](contracts/acceptance.md#requirement-coverage); it maps all
FR-001..FR-022 and SC-001..SC-007, plus every story scenario. Coverage includes
disabled structural validation versus active compatibility, enabled optional
cycles, ambiguous routes with different parameter names/casing, safe
diagnostics, constructor/service/map failures, concurrent stop races, and
non-cooperative callbacks. Tests must show positive counterparts rather than
only validating rejection.

## Validation and Handoff

At planning: verify local links/anchors, all mappings, no unresolved design
placeholders, unchanged spec/checklists/F-01/product sources, exact pinned
paths, relevant tooling tests and whitespace. Obtain a bounded
`hoard-architecture-review` on the proposed lifecycle, public surface, and
dependency directions before PR handoff.

At implementation: use the [quickstart](quickstart.md) and acceptance matrix,
introduce locked test dependencies only then, obtain implementation architecture
review, and capture measured proof separately from these proposals. Run the
existing complete foundation acceptance to detect package/graph/API regressions.
Future commands in this plan are not current successful evidence.

### Planning Architecture Review

The bounded `hoard-architecture-review` identified one confirmed HIGH design
gap and two design questions (HIGH and MEDIUM), corrected in these artifacts:
the public build path now explicitly supervises synchronous host build rather
than leaving an unbounded bare `Build`; over-budget requests retain owner/
dependency resource leases and prohibit unsafe root disposal; and worker
admission is explicitly the whole `RunAsync` callback, not an unimplementable
per-iteration gate. LC-20/23/26/29 require the corresponding regression proof.
These are design corrections, not executed runtime evidence or checklist
approval. Implemented resource/admission/budget/API/packed-graph proofs and
implementation architecture review remain outstanding.

### Approved Checklist Follow-up

The user approved RQ-01/RQ-02 from the requested checklist review. The updated
spec/model/contracts explicitly retain a non-completed StopAsync as pending
Phase activity: timeout ends waiting, not resource use. Protect its owner,
prerequisites and root; preserve TimedOut and unsafe omissions, continue
independent safe cleanup within the same deadline, and observe late faults
without retry, returned-result mutation or deferred disposal. LC-28/29 and
T048/T050..T053 require a barrier-held A -> B plus independent C proof.

The quickstart and acceptance manifests now agree with T063/T065: baseline
includes Protocol.One, Protocol.Two, Metadata, Artifact.One and optional
Identity; custom adds Artifact.Two and its host adapter. The no-rebuild journey
switches bundled protocols, while all six fixture packages remain independently
packed. These approved design/documentation corrections create no runtime
evidence, package dependency, new task or driver stage transition.

A bounded `hoard-architecture-review` of the approved follow-up found no
actionable findings or unresolved design questions. Pending-cleanup retention,
same-deadline independent cleanup, once-only/late-result behavior, independent
package manifests and unchanged public compatibility were reviewed as written
obligations. Actual runtime, retained-binary/framework and implemented-graph
proofs remain required; the reviewer ran no commands or tests.

## Complexity Tracking

No constitutional violations or exceptions. A module adapter, one coordinator,
and a restricted owned-route API are necessary to keep DI/HTTP dependencies
out of persistence/storage while enforcing disabled isolation and startup
safety. Do not add a plugin bus, generic orchestration framework, distributed
lifecycle, general route theorem prover, or configuration subsystem.

## Implementation evidence

### Delivered boundary and necessary adjustments

Production behavior is confined to Hosting's Composition/Lifecycle/Routing
directories. Abstractions/Core/Application and F-01 public registration source,
markers and descriptors are unchanged. There is no product executable, real
provider, configuration/secret parser, operational cache/security mechanism,
management HTTP endpoint or UI.

One coordinator owns initialization, readiness assessment and worker supervision.
T025/T041/T042/T053's proposed separate HoardInitializationRunner,
HoardReadinessAssessor and HoardWorkerSupervisor files were deliberately
consolidated into HoardLifecycleCoordinator rather than adding pass-through
classes or separate state/locks. HoardReadinessEvaluator, ActivationLedger,
HoardActivityTracker, LifecycleDeadline and HoardCleanupPlanner retain their
focused responsibilities. Tests exercise behavior, not hypothetical file names.

The implemented ownership boundary corrects a planning ambiguity:
IHoardLifecycle.StopAsync shares immutable **module-only** coordination.
NotAttemptedOwnerPending explicitly distinguishes eligible root disposal that
still belongs to the external composition lease. Only lease disposal owns
framework-stop completion and root disposal; its final StopResult is separate
and remains available when incomplete disposal throws a sanitized exception.
Repeated/concurrent disposal shares one task. No unsafe frozen result is
retried or changed because a held callback finishes later.

Use normal app.StartAsync, then StopHoardApplicationAsync(lease), then lease
disposal. This additive stop wrapper shares the **actual** normal framework
StopAsync task, including synchronous ApplicationStopped notifications, with
the owner. Bare application StopAsync/RunAsync/independent disposal is outside
the supported ownership boundary. A canceled notification token does not prove
notification callbacks or framework stop finished. This supersedes planning's
unqualified normal-stop wording without changing F-01 APIs.

Startup/activation/readiness defaults remain 120s/30s/5s; shutdown/drain/cleanup
30s/10s/5s. The shutdown deadline begins at the stop latch. All positive finite
TimeSpan values are accepted, including durations beyond a .NET timer's maximum:
bounded timer slices preserve both deadlines and propagate a callback's own
TimeoutException. Timeout is bounded coordination, never forced termination.
Cancellation callbacks and linked-token deregistration remain tracked activity.
Readiness source disposal waits for its probe tasks, off the evaluator's return
path; cancellation cannot be lost by unregistering a pending probe too early.

Hosting now has an ASP.NET Core framework reference and internal
NuGet.Versioning 7.9.0; test-only TestHost is stable 10.0.13. Licenses/advisories
and the removed redundant DI package are recorded in research.md. SDK and
unrelated dependency versions are unchanged. Even non-web registration-only
Hosting consumers now need ASP.NET Core's shared framework: a deployment
prerequisite change, not a registration source/binary API break.

### Architecture review and corrections

Actual implementation review by custom `hoard-architecture-review`
`cbe146d7-63db-4227-b2bb-0a38e8aa411e` identified three HIGH and one MEDIUM
issues: root disposal overlapping framework shutdown, unsupervised/locked route
finalization, early handler-error lease release, and ignored mid-operation
compose/build/map cancellation. Corrections separate root ownership, supervise
route finalization/revalidation outside the lifecycle lock, retain request
leases through response completion, and latch/recheck caller cancellation.
LifecycleOwnershipTests, LifecycleCleanupTests and WorkerAdmissionTests exercise
these paths.

A bounded corrective review by `hoard-architecture-review`
(`lifecycle-correction-review`) identified two HIGH and two MEDIUM issues:
linked-CTS disposal could block readiness return; ApplicationStopped was not a
framework-stop completion barrier; long timer-slice waits could swallow the
operation's own timeout; and external HTTP packages inherited framework-only
identity exemptions. All four were corrected with focused regressions:
barrier-held cancellation/deregistration returns boundedly; concurrent stop/
disposal retains root through stopped notifications; long-budget faults
propagate without spinning; and InspectionNode.IsFramework records verified
reference-pack provenance independently of architectural ownership.

Readiness-stop regression additionally exposed lost cancellation when linked
sources were disposed before a still-running probe completed. Disposal now
waits for probe completion off-path, while cancellation is explicitly requested
and tracked. Virtual-time regression coordination now waits for the intended
timer's next delay, not an unrelated startup timer. These were actual failing
runtime cases before correction, not inferred success from cancellation delivery.
Reviewers ran no commands/tests and did not approve custom checklist markers;
the final corrections are substantiated by the automated regressions below,
not claimed as a new independent human approval.

Graph inspection retains all ARCH-001..008 rules, F-01's exact eight scan IDs,
and the permitted Identity -> Hosting -> Core path separately from forbidden
direct/alternative paths. Framework roll-forward requires verified known
reference-pack provenance, identical name/culture/key, and a nondecreasing
version. External packages, including TestHost (Sdk ownership), retain strict
identities and compiled-reference inspection. Packed framework references must
equal resolved references. Public HTTP/Hosting types are allowed only in
approved families; NuGet.Versioning never becomes a public contract.

### Acceptance traceability

The existing acceptance matrix maps all 22 FRs, seven SCs and 20 story scenarios
to LC-01..40; the following table identifies the executed implementation or
explicit documentation proof. The 12 specification edge cases correspond to
the registry, platform, missing/optional dependency, cardinality, route,
partial-phase, selected failure, stop-race, non-cooperation, diagnostic and
duplicate-registration rows below. No requirement is implemented by a second
configuration/selection path.

| Cases | Concrete proof |
| --- | --- |
| LC-01 | SelectedStartupTests reverses real registration records, records monotonic actual initialization/cleanup events, checks completed prerequisites and the same ordinal order |
| LC-02..05, LC-14 | RegistryValidationTests and LifecycleContractTests reject malformed/unknown/duplicate/orphan/missing inputs before construction; valid disabled incompatible registration remains inert |
| LC-06..12 | RuntimeCompatibilityTests and SelectionGraphTests cover both platform axes, interval/prerelease policy, missing/disabled required and optional targets, active cycles, target-specific capabilities and exact cardinality with permitted multiple protocols/identities |
| LC-13 | CompositionSnapshotTests, LifecycleRestartTests and package journeys reject stale/different builders and retain the original running selection |
| LC-15..17 | EnabledDisabledLifecycleTests uses actual TestServer dispatch, including concurrent Generic Host startup: early 503, no worker, ready handler, disabled 404 and post-stop 503; package counters prove zero disabled connection attempts |
| LC-18..19 | OwnedRouteTests covers parameter/case/slash/method/literal conflicts, missing/undeclared responsibilities, constraints/defaults/optional/complex/catch-all routes, custom sources/policies/order, unowned overlap and preserved fallback authorization |
| LC-20..21, LC-27 | LifecyclePhaseFailureTests, SelectedStartupTests and LifecycleOwnershipTests cover constructor self-cleanup, services/map/init/readiness/build failure, each initialization position, partial adapters and no later work |
| LC-22..23 | LifecycleConcurrencyTests, LifecycleDeadlineTests and LifecycleOwnershipTests cover stop during init/readiness, canceled waiters, build/finalization cancellation and virtual-time expiry, startup pause, aggregate deadline, no late application/publication |
| LC-24..25 | LifecycleReadinessTests plus deadline/cancellation tests cover later loss/recovery, shared assessment, required/optional observations, unknown/duplicate/invalid/missing observations and blocked cancellation |
| LC-26..31 | LifecycleCleanupTests/ConcurrencyTests/OwnershipTests/WorkerAdmissionTests cover request completion, worker/callback/build retention, reverse cleanup, A -> B plus independent C, fixed outer exhaustion, shared once-only operations, hosted-worker bypass, worker fault and root failure/stall |
| LC-32..33 | Captured normal framework logs and safe diagnostic assertions are shared across registry/selection/route/phase/worker/root failures; LifecycleDiagnosticTests checks bounded action/path/list omission; held cleanup later faults safely without rewriting the returned result |
| LC-34 | LifecycleInventoryTests and readiness/failure/cleanup snapshots distinguish IncludedByRegistration, disabled/enabled/phase/ready/stopped/incomplete state without inventory/support inference |
| LC-35..37 | Package-only baseline/custom Program.cs executes seven nonempty self-checking journeys, bundled protocol selection with no intervening rebuild, absent-baseline Artifact.Two addition and explicit prior-set recovery |
| LC-38 | LifecycleBoundaryTests requires ten exact actual platform/provider/baseline/custom/registration graph IDs; full foundation retains eight original scans, negative/permitted pairs and Identity path distinctions |
| LC-39 | Isolated merged-F-01 package build, retained consumer DLL hash/run against new runtime, separate new-source compilation, non-web runtimeconfig and packed nuspec/framework/restore provenance |
| LC-40 | README, DEVELOPMENT, PROVIDERS, quickstart and LifecycleHost guide document current APIs, budgets, diagnostics, ownership/recovery and fixture-only support limits |

### Measured commands

Initial missing tooling/contracts/validation/composition/route APIs produced
intended red failures, then focused primitives (5), validator/startup (47), and
HTTP/readiness/worker (21) tests passed. Subsequent corrective regressions
exposed the concrete cancellation/deadline failures above before their fixes.
An earlier focused run failed after foundation cleanup because its assets
pointed into the deleted private cache; the focused runner now restores its
project locked before --no-restore testing. Compile/import corrections and
virtual timer-selection fixes were rerun rather than recorded as passing proof.
Partial filters always label themselves partial, never full acceptance.

| Command | Result |
| --- | --- |
| `dotnet restore Hoard.slnx --locked-mode -v quiet` | Passed; no source/test lock mutation |
| `dotnet format Hoard.slnx --no-restore -v quiet` | Passed; SDK formatting applied, full acceptance verifies no changes |
| `dotnet format whitespace tests/fixtures/lifecycle --folder -v quiet` | Passed |
| `dotnet format whitespace examples/LifecycleHost --folder -v quiet` | Passed |
| `bash scripts/validate-lifecycle.sh --update-locks` | Passed: 126 source tests, nine boundary proofs, seven package-only journeys; six independent fixture packages, retained old binary/new source/framework proof |
| `bash scripts/validate-lifecycle.sh` | Passed independently with unchanged locks: 126 source tests, nine boundary proofs, seven package-only journeys; six independent packages and retained old binary verified |
| `bash scripts/validate-foundation.sh --update-locks` | Passed: 220 .NET tests (42 foundation, 49 architecture, 129 composition), zero failed/skipped; affected F-01 consumer locks refreshed/replayed |
| `bash scripts/validate-foundation.sh` | Passed independently: same 220 tests, zero failed/skipped, original eight real graph scans and compile-only package/host proofs retained |
| `python3 -m unittest discover -s tests/tooling -v` | Passed: 22 tests |
| `git diff --check` | Passed before the implementation checkpoint |

The final documentation audit passed 171 local file/anchor links and verified
exactly T001..T072 checked, with no unchecked implementation task. The spec,
all built-in/custom checklist bytes, F-01 artifacts and Abstractions/Core/
Application sources remain unchanged; original fixture/example sources are
preserved, apart from explicitly permitted affected locks.

Local packs normalize unsigned archive envelope metadata and source paths using
the existing foundation helper; package payload/source/nuspec bytes and hashes
are not bypassed. Standalone package locks are tracked; source/project imports,
stale/nonlocal packages, missing/empty/skipped evidence or failed/timed-out
subprocesses fail explicitly. Private temporary directories are removed only
through their resolved owner registry. No build output/feed/cache is committed.

### Support and unaffected-document audit

All fixtures retain Fixture provenance and non-production names. TestServer
proves application-level routing/admission/drain only, not a TCP/TLS/proxy
listener, production latency, native-client restore, real provider behavior,
crash recovery or conformance certification. Disabled inclusion never means
active integration/support. Bounded waits cannot kill trusted code; incomplete
terminal lifecycles may require process termination. Cleanup is neither schema/
data rollback nor automatic restoration of a prior configuration.

Product charter/specification, baseline architecture diagrams, ADR-0001,
constitution and master backlog are unaffected: this delivers their existing
Hosting/provider directions without changing product scope, shared cache/
security invariants, governance or dependency completion. F-01 fixture/example
sources and compile-only README remain unchanged; only necessarily affected
consumer locks were refreshed. LifecycleHost is separate and explicitly
fixture-only. F-03 owns configuration/secrets/operator selection, F-04 discovery/
UI, later features real protocol/store/identity/cache operations, conformance
and native clients. IaC/release guides are unaffected: no plan/apply, permissions,
deployment, package publication, tag, release or merge occurred.

Requirements/custom checklist bytes remain reviewer-owned and unchanged.
Implementation does not run convergence/finalization, ready or merge the draft
PR, finish F-02's dependency checkpoint, or authorize a dependent feature.

### T073 implementation follow-up

The separately authorized follow-up resolves the CRITICAL worker-fault
notification path found by convergence. WorkerFailure, failed owner state,
closed readiness/admission and the once-only stop latch remain atomic under
Gate. Register composition-wide Phase activity before scheduling stop, then
resolve IHostApplicationLifetime and invoke synchronous StopApplication on a
supervised task outside that lock. Retain the activity until notification
returns; translate notification-task errors to safe HostStopFailure and use
the existing late-fault observer. Do not start another shutdown budget.

The existing HoardActivityTracker, HoardCleanupPlanner and composition lease
already retain all module/root resources for composition-wide activity.
No tracker, planner, disposal-owner, public API, project or dependency change
is needed. A held host-stopping notification or lifetime-cancellation callback
therefore yields explicit UnsafePendingCallback / NotAttemptedUnsafe rather
than disposing resources it can still use. Late completion cannot rewrite
the immutable module/lease results, retry cleanup or trigger deferred disposal.

#### Focused failure and correction evidence

WorkerAdmissionTests adds a barrier-held ApplicationStopping notification:
snapshot access stays responsive; virtual stop time advances 199 ms without
completion, then the final 1 ms exhausts the original 200 ms shutdown budget.
WorkerFailure remains primary, with safe additional Timeout diagnostics.
LifecycleOwnershipTests independently holds host notification and lifetime
cancellation: after the one-second drain cap, nine seconds of the original
ten-second shutdown budget remain, all modules/root are retained, and global
Phase activity remains explicit. Repeated stop/disposal returns the same frozen
outcomes; releasing/observing the callback triggers no cleanup/root disposal.
The cooperative worker-fault counterpart now asserts one notification, one
cleanup per module and one root disposal across concurrent disposal callers.

Before the product change, the three new cases produced two runtime failures
(held notification/snapshot and held notification/ownership) and one passing
cancellation counterpart. An initial no-restore attempt instead encountered
stale assets from a deleted prior acceptance cache; locked restore corrected
setup before recording the intended runtime failures.

The first full lifecycle run subsequently exposed a virtual-time scheduling
race in the existing independent-cleanup regression: advancing drain expiry
while harmless global cancellation was still pending correctly made every
module unsafe, contradicting that test's expectation of quiescent independent
cleanup. The test now waits for that global activity to finish before advancing
time, without releasing the deliberately held worker or weakening its
owner/prerequisite/root assertions. The pair passed five consecutive Release
replays, then both complete acceptance commands passed.

#### Bounded implementation architecture review

Custom hoard-architecture-review (`t073-architecture`) reviewed the changed
coordinator and worker/ownership regressions with immediate tracker/planner/
lease/deadline/bridge context. It found no actionable findings or unresolved
design questions: activity precedes drain scheduling, service resolution and
notification do not hold Gate, ownership remains centralized and outcomes
remain frozen. The reviewer ran no commands/tests. Its evidence limitations
were pending full acceptance, the not-yet-rerun strengthened cooperative case,
and no direct notification-task fault injection for HostStopFailure /
LateCallbackFailure. Subsequent focused/full runs below address the first two;
the latter remains a focused test-scope limitation, not a claimed injection
result. Existing cleanup late-fault and safe-diagnostic regressions remain.
The later test-only synchronization correction changes no production ownership.

#### Measured follow-up commands

| Command | Result |
| --- | --- |
| `dotnet restore tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj --locked-mode --verbosity quiet` | Passed; restored missing local assets without lock changes |
| `dotnet test tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj --no-restore --filter 'FullyQualifiedName~Held_worker_fault_notification\|FullyQualifiedName~Worker_fault_retains_all_resources' --verbosity quiet` | Intended red before product fix: two failed, one passed, zero skipped |
| `dotnet test tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj -c Release --no-restore --filter 'FullyQualifiedName~WorkerAdmissionTests\|FullyQualifiedName~LifecycleOwnershipTests\|FullyQualifiedName~LifecycleCleanupTests\|FullyQualifiedName~LifecycleConcurrencyTests' --verbosity quiet` | Passed after correction: 21 tests, zero failed/skipped, including strengthened cooperative case |
| `dotnet test tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj -c Release --no-build --no-restore --filter 'FullyQualifiedName~LifecycleCleanupTests.Timed_out_cleanup_or_worker' --verbosity quiet` | Passed five consecutive replays: two tests each, zero failed/skipped |
| `dotnet format Hoard.slnx --no-restore --verify-no-changes --verbosity quiet` | Passed; complete acceptance also verifies formatting/analyzers for source and standalone consumers |
| `bash scripts/validate-lifecycle.sh --update-locks` | Passed after test synchronization correction: 129 source tests, nine boundary proofs, seven package-only journeys; six independent packages and retained old binary/new-source/framework proof |
| `bash scripts/validate-lifecycle.sh` | Passed independently with unchanged locks: same 129 tests, nine proofs and seven journeys |
| `bash scripts/validate-foundation.sh --update-locks` | Passed: 223 .NET tests (42 foundation, 49 architecture, 132 composition), zero failed/skipped; affected packed Hosting consumer hashes refreshed |
| `bash scripts/validate-foundation.sh` | Passed independently: same 223 tests, zero failed/skipped; original eight scans, ARCH-001..008, C-01..23, isolated Core and compile-only hosts retained |
| `python3 -m unittest discover -s tests/tooling -v` | Passed: 22 tests |
| `git diff --check` | Passed |

Exactly ten affected standalone locks change only contentHash fields for the
new Hosting payload and its dependent lifecycle protocol/identity fixture
packages. Package versions, dependency metadata, baseline old-binary lock,
Abstractions-only fixtures and platform/test locks remain unchanged. A structured
old/new comparison verifies that scope; default lifecycle and foundation
replays use fresh private feeds/caches without hash bypass or lock mutation.

README, DEVELOPMENT, PROVIDERS, LifecycleHost guide, quickstart, lifecycle
contract and in-memory model document the corrected notification ownership.
Spec, public API contract, acceptance obligations, all built-in/reviewer-owned
checklists, F-01 source/examples and Abstractions/Core/Application source stay
unchanged. Product intent, baseline diagrams/ADR, governance, master backlog,
IaC and release guidance are unaffected: this corrects the existing invariant
without changing product scope, dependencies, permissions or operational steps.
No extension hooks are registered (`.specify/extensions.yml` is absent).
No infrastructure, deployment, publication, tag, release or merge occurred.

T001..T073 are now complete. This checkpoint completes only implement; a fresh
convergence assessment is the next separately authorized stage. Keep the PR
draft and do not infer finalization, merge readiness or dependency completion.

### T074 implementation follow-up

The separately authorized implementation resolves the HIGH cancellation-error
reporting gap found by follow-up convergence. Lifetime, readiness-timeout and
cleanup-timeout cancellation now share one off-lock supervisor. It records
safe additional `CancellationFailure` diagnostics before releasing tracked
activity, retaining the originating owner/phase, fixed corrective action and
lifecycle correlation without copying exception/inner payloads. The existing
bounded diagnostic catalogue owns publication; no second shutdown path, public
signature, dependency, provider boundary or disposal owner is introduced.

Primary startup/worker/timeout diagnostics remain separate. A completed fault
is no longer pending resource use: otherwise cooperative modules/root may
release successfully while reporting the cancellation problem. Pending
callbacks still retain their owner/prerequisites/root, with composition-wide
protection for lifetime cancellation. Late faults appear in later snapshots,
not frozen module/lease results, and cannot retry cleanup or launch deferred
disposal. The original absolute shutdown deadline remains unchanged. The
existing disposed-source race is ignored only when its associated work has
already completed; cancellation exceptions otherwise become safe diagnostics.

#### Focused failure and correction evidence

Seven new cases extend the existing cleanup/deadline/ownership test files:
throwing/cooperative lifetime cancellation, throwing/cooperative readiness and
cleanup timeout cancellation, and a held lifetime callback that faults after
bounded stop/disposal following worker failure. Barriers/virtual time establish
known errors before publication, retained resources during pending work,
preserved primary errors, originating phase/owner/action/correlation, one
diagnostic per failed cancellation operation, once-only cleanup/root disposal
and no seeded payloads in captured normal logs/results. Every held test task is
released/observed; repeated operations preserve immutable results.

The nine-case targeted run before production changes failed four missing-error
assertions; five cooperative/existing cases passed. An initial no-restore
attempt instead found stale assets referencing a deleted prior acceptance
cache. Locked restore repaired setup before the intended runtime red result.
The first focused green run found one test-only ImmutableArray backing-array
equality assertion; comparing diagnostic sequences corrected that oracle.
All 32 focused cases then passed with the production correction.

#### Bounded implementation architecture review

Custom hoard-architecture-review (`t074-architecture`) reviewed the changed
coordinator/catalogue and cleanup/deadline/ownership regressions with immediate
tracker/planner/lease/deadline context. It found no actionable findings or
unresolved design questions: safe reporting precedes activity release, callbacks
do not hold Gate, original deadlines/centralized ownership and frozen outcomes
remain intact. It ran no commands/tests. Its stated evidence gaps were refreshed
packed-consumer locks and complete lifecycle/foundation/tooling acceptance;
the subsequent measured runs below supply those proofs. The earlier T073
direct host-notification-task fault-injection limitation remains unchanged;
this follow-up directly exercises cancellation faults, not that separate path.

#### Measured follow-up commands

| Command | Result |
| --- | --- |
| `dotnet restore tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj --locked-mode -v quiet` | Passed; repaired missing local assets without lock changes |
| `dotnet test tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj -c Release --no-restore --filter 'FullyQualifiedName~Lifetime_cancellation_fault_is_reported\|FullyQualifiedName~Timeout_cancellation_reports_additional_fault\|FullyQualifiedName~Worker_fault_retains_all_resources' -v minimal` | Intended red before production correction: four failed, five passed, zero skipped |
| `dotnet test tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj -c Release --no-restore --filter 'FullyQualifiedName~LifecycleCleanupTests\|FullyQualifiedName~LifecycleDeadlineTests\|FullyQualifiedName~LifecycleOwnershipTests\|FullyQualifiedName~WorkerAdmissionTests\|FullyQualifiedName~LifecycleConcurrencyTests' -v minimal` | Passed after correction: 32 tests, zero failed/skipped |
| `dotnet format Hoard.slnx --no-restore --verify-no-changes --verbosity quiet` | Passed; complete acceptance also verifies source/standalone formatting and analyzers |
| `bash scripts/validate-lifecycle.sh --update-locks` | Passed: 136 source tests, nine boundary proofs, seven package-only journeys, six independent packages and retained old-binary/new-source/framework proof |
| `bash scripts/validate-lifecycle.sh` | Independent default passed: same 136 tests, nine proofs and seven journeys, no lock mutation |
| `bash scripts/validate-foundation.sh --update-locks` | Passed: 230 tests (42 foundation, 49 architecture, 139 composition), zero failed/skipped; affected packed Hosting consumer hashes refreshed |
| `bash scripts/validate-foundation.sh` | Independent default passed: same 230 tests, zero failed/skipped; original eight scans, ARCH-001..008, C-01..23, isolated Core and compile-only hosts retained |
| `python3 -m unittest discover -s tests/tooling -v` | Passed: 22 tests |
| `git diff --check` | Passed |

A structured old/new comparison verifies exactly ten affected standalone locks
and 16 changed contentHash fields for Hosting and dependent lifecycle
protocol/identity fixture payloads. No version/dependency metadata changes;
Abstractions-only fixtures, baseline old-binary lock and platform/test locks
remain unchanged. Fresh independent default runs verify package provenance
without hash bypass or rewriting locks.

README, DEVELOPMENT, PROVIDERS, LifecycleHost guide, quickstart, lifecycle
contract/model and task checkpoint document actual diagnostic semantics.
Spec, public API/acceptance contracts, built-in/reviewer-owned checklists,
F-01 sources/examples and Abstractions/Core/Application source are unchanged.
Product charter/specification, baseline architecture/diagrams/ADR, governance,
master backlog, IaC and release guides are unaffected: this restores existing
diagnostic/resource invariants without changing product scope, dependencies,
permissions or operational steps. No extension hooks are registered
(`.specify/extensions.yml` is absent); no infrastructure, deployment,
publication, tag, release or merge occurred.

T001..T074 are complete. This finishes only implement; fresh convergence is
the next separately authorized stage. Keep PR #6 draft without claiming
finalization, merge readiness, feature completion or dependency availability.

### T075 implementation follow-up

The separately authorized implementation resolves the HIGH eventual-fault
diagnostic omission found by convergence. A small internal CallbackObservation
binds each supervised operation to its owner, originating phase and safe normal
failure category. It records failures inside tracked activity, before release,
then throws only a sanitized HoardLifecycleException. Once a bounded wait is
abandoned, a later non-cancellation fault becomes additional LateCallbackFailure
without depending on whether shared stop has completed. Normal awaited paths
recognize already reported safe exceptions and do not duplicate diagnostics.
Callback-thrown TimeoutException retains Timeout and existing cleanup/root
TimedOut classification rather than being mistaken for an ordinary failure.

Startup construction/service/build/map/initialization, initial/later readiness,
cleanup, actual framework stop and root disposal use this same mechanism.
Readiness linked-source disposal is safely observed too. The remaining task
continuation only consumes already categorized task exceptions; it is not the
diagnostic publication mechanism. T074's off-lock cancellation supervisor stays
unchanged. Cooperative cancellation is not a new eventual fault. Root disposal
uses the existing composition-wide activity tracker and sole lease owner.

Known faults are published before quiescence, so the shared stop/final result
can include them. A fault after a bounded result adds only to a later snapshot;
it cannot rewrite immutable outcomes, retry cleanup or start deferred disposal.
Completed faults do not falsely retain resources. Pending work still protects
its owner/prerequisites/root under the original absolute deadlines. There is
no public API, dependency, provider boundary or second shutdown path change.

#### Focused failure and correction evidence

The first six-case run reproduced the original readiness/cleanup omissions:
three missing-diagnostic assertions failed and three cooperative counterparts
passed. The expanded 19-case pre-fix run failed six missing-diagnostic
assertions, with 13 passing counterparts/direct-failure cases and zero skipped.
It also exercised initial readiness, startup, framework-stop and root-disposal
faults after bounded results. Existing directly awaited phase/cleanup cases now
assert once-only categories; added callback-thrown TimeoutException cases
preserve normal timeout classifications.

The focused suite also covers cleanup faulting while independent cleanup keeps
shared stop open: the original callback remains TimedOut, prerequisite and
independent cleanup complete once when safe, and final root disposal completes.
Initial/later readiness and post-result startup/cleanup/framework/root cases
assert safe owner/phase/action/correlation, frozen results, no retry/deferred
disposal and zero seeded exception payloads in normal logs/results. All held
work is released and observed with barriers/fake time and bounded scheduler
backstops, not observer sleeps. A test-only compile syntax error and two test
oracles were corrected during development: Timeout plus LateCallbackFailure
are separate findings, and a direct cleanup timeout waits for its supervised
cancellation to quiesce before claiming otherwise safe root release.

#### Bounded implementation architecture review

Custom hoard-architecture-review (`t075-architecture`) reviewed the changed
coordinator/lease and immediate tracker/deadline/planner/bridge context with
the focused regressions. It found two related confirmed gaps, both reproduced
and corrected within this implementation:

| Finding | Correction and focused proof |
| --- | --- |
| HIGH: worker faults after stop was latched were swallowed before activity release | Record one safe additional LateCallbackFailure with owner/Running phase during drain or after bounded stop; never request shutdown again. Both timings now have barrier-held regressions, plus cooperative late-worker counterparts and unchanged frozen outcomes. |
| MEDIUM: root disposal could be dispatched after time expired while resuming from successful framework stop | Recheck the same absolute deadline immediately before root dispatch; return NotAttemptedBudgetExhausted without invoking disposal. An injected inter-phase clock advances time after the preceding timestamp read and proves zero disposer calls across repeated disposal. |

Before these corrections, the six-case review follow-up failed three intended
assertions (worker during drain, worker after bounded stop, root budget boundary)
and passed three counterparts. The complete focused suite after correction
passed 69 tests with zero failures/skips. The reviewer ran no commands/tests
and did not independently re-review these corrections; their resolution is
supported by the failing-then-passing regressions and full acceptance below,
not a fabricated clean re-review. Its remaining evidence gaps were pending full
packed-lock acceptance and the previously acknowledged absence of a direct
host-notification-task exception injection. This change exercises actual
framework-stop faults, not that distinct notification-task injection.

#### Measured follow-up commands

| Command | Result |
| --- | --- |
| `bash scripts/validate-lifecycle.sh --filter 'FullyQualifiedName~Timed_out_readiness_reports_eventual_fault_once\|FullyQualifiedName~Timed_out_cleanup_reports_eventual_fault_before'` | Intended red before product correction: three failed, three passed, zero skipped; direct runner output confirmed the missing diagnostic assertions |
| `dotnet test tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj -c Release --no-restore --filter 'FullyQualifiedName~reports_eventual_fault\|FullyQualifiedName~Framework_stop_and_root_disposal_report_faults_once\|FullyQualifiedName~Entered_failure_preserves_safe_primary\|FullyQualifiedName~Cleanup_exception_does_not_skip' -v minimal` | Expanded pre-fix red: six failed, 13 passed, zero skipped |
| `dotnet test tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj -c Release --no-restore --filter 'FullyQualifiedName~Worker_fault_during_drain\|FullyQualifiedName~Timed_out_cleanup_or_worker\|FullyQualifiedName~Budget_expiry_between_framework_stop' -v minimal` | Review findings red before correction: three failed, three passed, zero skipped |
| `dotnet test tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj -c Release --no-restore --filter 'FullyQualifiedName~LifecycleReadinessTests\|FullyQualifiedName~LifecycleDeadlineTests\|FullyQualifiedName~LifecycleCleanupTests\|FullyQualifiedName~LifecycleOwnershipTests\|FullyQualifiedName~LifecyclePhaseFailureTests\|FullyQualifiedName~WorkerAdmissionTests\|FullyQualifiedName~LifecycleConcurrencyTests' -v minimal` | Passed after all corrections: 69 tests, zero failed/skipped |
| `dotnet format Hoard.slnx --no-restore --verbosity quiet` | Passed; SDK formatting applied before packed acceptance |
| `bash scripts/validate-lifecycle.sh --update-locks` | Passed: 161 source tests, nine boundary proofs, seven package-only journeys, six independent packages and retained old-binary/new-source/framework proof |
| `bash scripts/validate-lifecycle.sh` | Independent default passed: same 161 tests, nine proofs and seven journeys; source/standalone SDK formatting/analyzers and package provenance verified without lock mutation |
| `bash scripts/validate-foundation.sh --update-locks` | Passed: 255 tests (42 foundation, 49 architecture, 164 composition), zero failed/skipped; affected packed Hosting consumer hashes refreshed |
| `bash scripts/validate-foundation.sh` | Independent default passed: same 255 tests, zero failed/skipped; original eight scans, ARCH-001..008, C-01..23, isolated Core and both compile-only hosts retained |
| `python3 -m unittest discover -s tests/tooling -v` | Passed: 22 tests |

A structured old/new lock comparison verifies ten affected standalone files
and 16 contentHash-only changes for Hosting and dependent lifecycle
protocol/identity fixture payloads. No versions or dependency metadata change;
Abstractions-only fixtures, baseline old-binary and platform/test locks remain
unchanged. Both independent defaults use fresh private feeds/caches without
hash bypass or lock rewriting. Whitespace, local documentation links and
protected-artifact checks pass before the shared checkpoint.

README, DEVELOPMENT, PROVIDERS, LifecycleHost guide, quickstart, lifecycle
contract/model and task checkpoint document actual diagnostic/deadline
semantics. Spec, public API/acceptance contracts, built-in/reviewer-owned
checklists, F-01 sources/examples and Abstractions/Core/Application source are
unchanged. Product charter/specification, baseline architecture/diagrams/ADR,
governance, master backlog, IaC and release guides are unaffected: these
corrections restore existing fault/deadline/resource invariants without new
product scope, APIs, dependencies, permissions or operational actions.
No extension hooks are registered (`.specify/extensions.yml` is absent).
No infrastructure plan/apply, deployment, publication, tag, release or merge
occurred. Implementation, fresh convergence, finalization and dependency
completion remain separate gates; PR #6 stays draft.

T001..T075 are complete. This finishes only implement; fresh convergence is
the next separately authorized stage, not finalization or dependency completion.

### T076 implementation follow-up

The separately authorized implementation resolves the CRITICAL request-ownership
contradiction found by convergence. Supervised BuildHoardApplicationAsync inserts
an internal IStartupFilter first in the service collection immediately before
build, after host/module configuration. Its outer middleware registers one
per-request completion boundary before other startup-filter/host middleware
callbacks. Since response completion runs callbacks in reverse registration
order, this boundary releases admitted resource leases last. Endpoint dispatch
transfers the existing coordinator/tracker lease to that boundary rather than
registering an endpoint-local release callback.

The internal boundary serializes admission against completion, releases each
lease once and refuses admission after completion. It can retain multiple
admissions if the same host request is re-executed; that is bookkeeping, not
another admission authority. It never releases on handler return or exception.
The existing coordinator, tracker, cleanup dependency propagation, immutable
results and sole external root owner are unchanged. Host middleware and required
access policy still run normally. No public API or dependency changes.

#### Focused failure and correction evidence

The previous handler-only handled-error test now covers six cases: callbacks
registered by host middleware, a host startup filter or the handler, each on
normal and handled-error responses. With completion held, fake time expires
the one-second drain cap under the original 30-second stop deadline. The
protocol and its artifact prerequisite remain UnsafePendingCallback, metadata
cleans safely once, the protocol Request stays tracked, and module/final root
outcomes are NotAttemptedUnsafe. Dispose before releasing completion, then
release and observe the held task: repeated stop/disposal preserves frozen
outcomes, no retry/deferred cleanup occurs, and root disposal stays unattempted.

Two cooperative normal/handled-error cases hold all three callback registration
sites in reverse order. A single Request activity remains through each callback;
none can observe owner/prerequisite/root cleanup while using those resources.
Once all callbacks return, activity drains and module cleanup/root disposal
complete exactly once. The initial eight-case pre-fix run failed six intended
assertions and passed the two handler-only counterparts: four earlier host
callbacks allowed unsafe Completed outcomes, and both cooperative cases lost
request activity before the host callbacks ran. Direct runner output confirmed
the exact assertion failures, not setup or compiler failures.

The post-fix focused cleanup/ownership/worker/route suite passed 64 tests. The
architecture review identified a material proof gap for completion-callback
exceptions. An added third cooperative row throws from the handler's completion
callback, then holds both earlier host callbacks. TestServer still executes
those callbacks before boundary release; all callbacks run once and safe
cleanup/root disposal complete without a new lifecycle fault or second owner.
The resulting focused suite passes 65 tests. Every held task is released and
observed with deterministic barriers/virtual time and scheduler backstops;
there is no listener, observer sleep or transport-conformance claim.

#### Bounded implementation architecture review

Custom hoard-architecture-review (`t076-architecture`) reviewed the modified
application/admission integration and regressions with immediate tracker,
coordinator, dependency-cleanup and sole-lease ownership context. No confirmed
actionable architecture violation or unresolved design question was found.
It verified by inspection that first filter registration covers earlier host
callbacks without dispatching around host middleware/authorization, and the
completion/admission locks have no reverse tracker dependency or provider
callback invocation.

The reviewer ran no commands/tests. Its two material evidence gaps were
throwing-completion-callback coverage (supplied by the subsequent regression)
and full packed-lock acceptance (supplied below). No production correction was
required after review, and no independent re-review of that added test is
claimed. The earlier direct host-notification-task fault-injection limitation
remains unchanged; this follow-up does not newly claim that distinct proof.

#### Measured follow-up commands

| Command | Result |
| --- | --- |
| `SPECIFY_FEATURE_DIRECTORY=specs/002-module-lifecycle .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` | Passed; pinned directory, all reviewer-owned/built-in checklists passed unchanged (20/20, 20/20, 16/16) |
| `bash scripts/validate-lifecycle.sh --filter 'FullyQualifiedName~Response_completion_retains_owner_prerequisite_and_root_after_drain_expiry\|FullyQualifiedName~Cooperative_response_completion_releases_one_request_only_after_all_host_and_handler_callbacks'` | Intended pre-fix red: six failed, two passed, zero skipped; direct no-build runner confirmed unsafe cleanup/premature activity-release assertions |
| `bash scripts/validate-lifecycle.sh --filter 'FullyQualifiedName~LifecycleCleanupTests\|FullyQualifiedName~LifecycleOwnershipTests\|FullyQualifiedName~WorkerAdmissionTests\|FullyQualifiedName~OwnedRouteTests'` | Passed after correction and throwing-completion counterpart: 65 tests, zero failed/skipped; host fallback authorization proof retained |
| `dotnet format Hoard.slnx --no-restore --include src/Hoard.Hosting/Routing/HoardModuleAdmissionMiddleware.cs src/Hoard.Hosting/Lifecycle/HoardApplicationExtensions.cs tests/integration/Hoard.Composition.Tests/LifecycleCleanupTests.cs tests/integration/Hoard.Composition.Tests/LifecycleOwnershipTests.cs --verbosity quiet` | Passed; complete acceptance also verifies source/standalone SDK formatting and analyzers |
| `bash scripts/validate-lifecycle.sh --update-locks` | Passed: 169 source tests, nine boundary proofs, seven package-only journeys; six independent packages and retained old-binary/new-source/framework proof |
| `bash scripts/validate-lifecycle.sh` | Independent default passed: same 169 tests, nine proofs and seven journeys; provenance verified without lock mutation |
| `bash scripts/validate-foundation.sh --update-locks` | Passed: 263 tests (42 foundation, 49 architecture, 172 composition), zero failed/skipped; affected packed Hosting consumer hashes refreshed |
| `bash scripts/validate-foundation.sh` | Independent default passed: same 263 tests, zero failed/skipped; original eight scans, ARCH-001..008, C-01..23, isolated Core and both compile-only hosts retained |
| `python3 -m unittest discover -s tests/tooling -v` | Passed: 22 tests |
| `git diff --check` | Passed |

A structured old/new comparison verifies ten affected standalone locks with
16 contentHash-only changes for Hosting and dependent lifecycle protocol/identity
fixture payloads. No version/dependency metadata change; Abstractions-only
fixtures, retained old-binary baseline and platform/test locks are unchanged.
Independent defaults use fresh private feeds/caches without hash bypass or
lock rewriting.
The documentation audit resolves 156 local file/anchor links across nine
changed Markdown files; task-body/previous-marker and PR-template fidelity
checks pass, alongside whitespace and protected-artifact checks.

README, DEVELOPMENT, PROVIDERS, LifecycleHost guide, quickstart, lifecycle
contract/model and task checkpoint document the corrected completion boundary.
Spec, public API/acceptance contracts, built-in/reviewer-owned checklists,
F-01 source/example scenarios and Abstractions/Core/Application source remain
unchanged. Product charter/specification, baseline architecture/diagrams/ADR,
governance, master backlog, IaC and release guides are unaffected: the existing
request/resource invariant is restored without new product scope, APIs,
dependencies, permissions or operational steps. No extension hooks are
registered (`.specify/extensions.yml` is absent); no infrastructure plan/apply,
deployment, publication, tag, release or merge occurred.

T001..T076 are complete. This finishes only implement; fresh convergence is
the next separately authorized stage. Keep PR #6 draft, without claiming
clean convergence, finalization, merge readiness or dependency completion.
