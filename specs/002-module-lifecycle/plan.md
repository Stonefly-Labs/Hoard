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
