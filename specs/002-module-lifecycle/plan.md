# Implementation Plan: Module Registry, Composition and Lifecycle

**Branch**: `feature/002-module-lifecycle` | **Date**: 2026-10-20
**Spec**: [spec.md](spec.md) | **Backlog**: F-02

**Input**: `specs/002-module-lifecycle/spec.md`, including its no-question
clarification review. This is a proposed implementation design, not delivered
lifecycle behavior. The existing F-01 libraries remain registration-only.

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
