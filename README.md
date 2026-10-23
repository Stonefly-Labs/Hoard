<p align="center">
  <img src="docs/assets/hoard-banner.svg" alt="Hoard — Fetch once. Build forever. A local home for your dependencies." width="880">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-34d399.svg"></a>
  <img alt="Status: foundation, not yet runnable" src="https://img.shields.io/badge/status-foundation-fbbf24.svg">
  <a href="docs/ARCHITECTURE.md"><img alt="Planned backend: .NET 10" src="https://img.shields.io/badge/planned-.NET%2010-8b5cf6.svg"></a>
  <a href="CONTRIBUTING.md"><img alt="Contributions welcome" src="https://img.shields.io/badge/contributions-welcome-38bdf8.svg"></a>
</p>

# Hoard

### Fetch once. Build forever. 📦

**One local destination for the dependencies your tools already use.**
Hoard is an MIT-licensed, self-hosted pull-through package cache being designed
for developer laptops, shared teams, and CI runners. Native package managers,
less repeated downloading, and a clear view of what's cached—without turning
dependency management into another full-time job.

> [!IMPORTANT]
> **Foundation only.** This repository currently contains product/design documents,
> development workflows, repository tooling, .NET provider contracts and a tested
> fixture-only module lifecycle, configuration, protected discovery boundaries,
> opt-in metadata operations with SQLite/memory qualification fixtures,
> and fixture-qualified artifact storage with independent local and simulated-object mechanisms,
> plus an operator-run Azure identity bootstrap.
> There is no runnable cache, production provider, UI, container, or published package.
> Everything in the product overview below describes the planned experience.

[Explore the vision](docs/PRODUCT_VISION.md) ·
[Read the architecture](docs/ARCHITECTURE.md) ·
[Follow the backlog](docs/HOARD_SPECKIT_MASTER_BACKLOG.md) ·
[Contribute](CONTRIBUTING.md)

## ✨ The idea

| For your laptop | For your team |
| --- | --- |
| SQLite + filesystem, with no required cloud account | The same product, with explicit TLS and authentication |
| Loopback-first defaults and a lightweight runtime | A shared cache for developer machines and CI |
| Native package-manager configuration | Provider choices without a separate enterprise edition |

**NuGet comes first.** Go, Maven, npm, PyPI, and Cargo follow the
[dependency-ordered specification backlog](docs/HOARD_SPECKIT_MASTER_BACKLOG.md).
Hoard is a cache, **not a private package publishing registry**.

## 🧭 How it will fit together

```mermaid
flowchart LR
    Client["Native package clients"] --> Protocol["Protocol providers<br/>NuGet first"]
    Console["Static Next.js console"] --> API["ASP.NET Core<br/>management slices"]
    Protocol --> Core["Shared cache engine<br/>integrity · freshness · streaming"]
    API --> Core
    Core --> Metadata["Metadata provider<br/>SQLite first"]
    Core --> Artifacts["Artifact provider<br/>filesystem first"]
    Core --> Upstream["Approved upstream registries"]
```

The planned implementation is a **.NET 10 / ASP.NET Core composable modular
monolith** with independently distributed NuGet providers. Management workflows
and protocol endpoints use vertical slices; shared correctness invariants stay
in the cache engine. The **Next.js App Router / TypeScript / Tailwind / shadcn/ui**
console is statically exported and served by .NET—no mandatory Node server.

Read the [architecture](docs/ARCHITECTURE.md) for dependency boundaries,
module lifecycle, trust boundaries, and deferred capabilities.

## 🛠️ Start here today

```bash
git clone https://github.com/Stonefly-Labs/Hoard.git
cd Hoard
git switch -c chore/your-change

# Standard-library tests for the repository tools; no application build.
python3 -m unittest discover -s tests/tooling -v

# .NET 10 foundation/solution acceptance; old package examples stay compile-only.
bash scripts/validate-foundation.sh

# Fixture-only lifecycle, in-process HTTP, package/restart and compatibility proof.
bash scripts/validate-lifecycle.sh

# Fixture-only configuration, local secrets and original-preserving conversion.
bash scripts/validate-configuration.sh

# Protected discovery, JSON consumer, private loopback adapters and compatibility.
bash scripts/validate-discovery.sh

# Metadata semantics on independent packages, real SQLite crash/recovery proof.
bash scripts/validate-metadata.sh
```

For repository work, use Git, GitHub CLI, Python 3.11+, and a stable .NET 10 SDK
matching `global.json`. The foundation check restores pinned dependencies from
nuget.org and builds temporary local packages; it requires network access.
OpenTofu and Azure CLI
are needed only when working on the [Azure bootstrap](infra/bootstrap/README.md).
There is no runnable cache or Node project yet. The lifecycle harness uses only
in-memory TestServer, never a listening product service. Dedicated discovery
adapter tests additionally open and close private ephemeral loopback Kestrel/TLS
listeners. Hosting and Application consumers now
require the ASP.NET Core shared framework. See the
[foundation quickstart](specs/001-provider-contracts/quickstart.md) and
[provider author guide](docs/PROVIDERS.md) for the exact supported scope.

Repository-scoped [MCP settings](docs/DEVELOPMENT.md#local-mcp-servers) connect
Copilot CLI and VS Code to Microsoft Learn, Context7, Next.js DevTools, shadcn,
Playwright, read-only Azure MCP, Docker MCP Gateway, and NuGet MCP. These are
optional contributor tools, not application dependencies; no global MCP
settings are changed.

### Repository map

```text
.github/             Copilot instructions/skills/agents, templates, tag releases
.specify/            Installed Spec Kit and shared Hoard flow checkpoint
apps/web/            Reserved for the statically exported management console
docs/                Product intent, architecture, workflow, and release guidance
infra/bootstrap/     Operator-run Azure OIDC identity + GitHub environment setup
scripts/             Small, dependency-free repository tools
specs/               Reviewable feature specifications; not delivered capabilities
src/                 Four platform library boundaries; production Host/providers reserved
tests/               Tooling, foundation unit/architecture/composition checks, fixtures
examples/CustomHost/ Package-only compile proof; never starts a host
examples/LifecycleHost/ Package-only lifecycle fixtures; in-process TestServer only
```

## 🤝 Build with us

All work happens on `chore/`, `feature/`, `bugfix/`, `docs/`, or another
purpose-named branch—not directly on `main`. Commit coherent changes, **push
after each commit**, and open a PR when the work is ready. Update the README
and affected documentation **before merging**, with an explicit explanation
when a document is unaffected.

The [contributor guide](CONTRIBUTING.md) covers setup and PR expectations.
The [development workflow](docs/DEVELOPMENT.md) documents the checkpointed
`hoard-speckit` skill, architecture reviewer, release skill, and quality gates.
Each implementation invocation completes all remaining spec tasks without
per-task or per-phase approval, unless blocked by a question, required approval,
failure, or interruption. The one-stage boundary still applies.
The initial [constitution](.specify/memory/constitution.md) is version 1.0.0;
its adoption has merged. The first feature specification,
[platform package boundaries and provider contracts](specs/001-provider-contracts/spec.md),
defines the compile-only foundation, not a runnable cache.
Its initial [clarification review](specs/001-provider-contracts/spec.md#clarifications)
found no critical ambiguities requiring questions; a later
[approved follow-up](specs/001-provider-contracts/spec.md#approved-follow-up-2026-10-20)
resolves the optional-dependency ambiguity found during checklist review. Its
[implementation plan](specs/001-provider-contracts/plan.md) now documents
provider-neutral declarations, explicit registration, compatibility policy,
and package-only composition and boundary acceptance evidence. Its historical
design is retained separately from measured implementation results. The custom
[architecture](specs/001-provider-contracts/checklists/architecture.md) and
[compatibility](specs/001-provider-contracts/checklists/compatibility.md)
requirements-quality checklists have received an explicitly requested delegated
review: all 38 criteria are satisfied after the user-approved
[optional-dependency policy clarification](specs/001-provider-contracts/checklists/compatibility.md#rq-01-incompatible-present-optional-dependency).
Enabled optional dependencies must be compatible; installed/registered but
disabled targets are unavailable and confer no integration/capability support.
This is requirements review, not implementation evidence or authorization;
the [implementation task list](specs/001-provider-contracts/tasks.md) maps
all 17 requirements and six outcomes to dependency-ordered work.
F-01 now provides immutable declarations and family markers in
`Hoard.Abstractions`, empty provider-free Core/Application boundaries, and
registration-only Hosting APIs. The acceptance command builds five independent
fixture packages, four family consumers plus the second artifact consumer,
and both [custom-host variants](examples/CustomHost/README.md). It exercises
all eight architecture rejection rules and 23 compatibility classifications.
Registration records metadata/types without constructing, enabling, validating,
or activating providers. These are local compile proofs, not released packages,
working stores/protocols/authentication, native-client evidence, or certification.
The original implementation includes architecture-review corrections and the
support-claim audit. Convergence then identified a false rejection of permitted
Identity-to-Hosting references when Hosting transitively reaches Core.
[Task T058](specs/001-provider-contracts/tasks.md#phase-8-convergence) corrects
that check using distinct Hosting-mediated and other dependency paths, with
positive and negative regressions preserving forbidden-edge detection.
The follow-up convergence assessment found no remaining gaps across all
17 requirements, six outcomes, acceptance scenarios, plan decisions, and
58 tasks. Fresh locked acceptance passed all 86 .NET tests and 17 tooling tests;
the specification, plan, tasks, and reviewer-owned checklists stayed unchanged.
Finalization acceptance is recorded in the
[plan](specs/001-provider-contracts/plan.md#finalization-acceptance-2026-10-20);
[PR #4](https://github.com/Stonefly-Labs/Hoard/pull/4) merged into `main` on
2026-10-20. The separate `await_merge` completion checkpoint records F-01 as
complete, retaining its feature directory, PR, and verified merge commit.
The progress checkpoint merged through
[PR #5](https://github.com/Stonefly-Labs/Hoard/pull/5), satisfying the next-spec
merge gate. The subsequent
[F-02 specification: module registry, composition and lifecycle](specs/002-module-lifecycle/spec.md)
defines startup selection and dependency validation, disabled-module isolation,
route ownership, readiness, bounded initialization/cleanup, safe diagnostics,
and explicit restart/custom-distribution journeys. Its
[built-in quality checklist](specs/002-module-lifecycle/checklists/requirements.md)
passes all 16 specification-quality criteria, not implementation or
reviewer-owned approval.
The [clarification review](specs/002-module-lifecycle/spec.md#clarifications)
found no critical ambiguities across all ten review categories: zero questions
and no requirement or scope changes. The built-in checklist remains 16/16;
exact lifecycle APIs, finite budget defaults, and ordering details remain
planning decisions under the existing requirements at that review.
The subsequent [F-02 implementation plan](specs/002-module-lifecycle/plan.md)
now proposes an opt-in Hosting adapter, metadata-only validation, deterministic
ordering, owned-route conflict checks, supervised build/initialization and
bounded cleanup, safe readiness/results, and fixed-selection restart journeys.
Its research, in-memory model, public/lifecycle/acceptance contracts and
[validation quickstart](specs/002-module-lifecycle/quickstart.md) map all
22 requirements, seven outcomes and 20 story scenarios to 40 fixture-only proof
cases. Architecture review led to explicit build supervision, protection of
resources still used after drain timeout, and precise worker admission semantics.
These are design obligations, not measured runtime evidence.
The subsequent checklist stage generated separate
[composition](specs/002-module-lifecycle/checklists/composition.md) and
[lifecycle](specs/002-module-lifecycle/checklists/lifecycle.md)
requirements-quality checklists with 20 criteria each. These standard-depth
reviews are for maintainers and provider reviewers before implementation
authorization; all 40 items remain unchecked and reviewer-owned. They cover
selection/compatibility and route ownership, plus admission, readiness, bounded
coordination, resource retention, cleanup, and safe diagnostics. Generation is
not requirements approval or runtime evidence.
The subsequent [implementation task list](specs/002-module-lifecycle/tasks.md)
contains 72 unchecked tasks across shared setup/safety primitives, five story
phases and cross-cutting acceptance. It maps all 22 requirements, seven outcomes
and 40 acceptance cases to implementation and focused proof, with explicit
prerequisites and file-disjoint parallel opportunities. Tests precede changed
behavior; supervised build, response/resource retention, root disposal, old
binary compatibility and package graphs remain proof obligations, not results.
At task generation, all 40 custom checklist items remained untouched and
reviewer-owned.
The subsequent read-only cross-artifact analysis found no actionable duplication,
ambiguity, underspecification, inconsistency, constitutional conflict or coverage
gap. All 22 requirements and seven buildable outcomes have implementation and
proof assignments; all 72 tasks map to requirements or shared acceptance
prerequisites. The complete acyclic prerequisite graph, 40 LC cases, 20 story
scenarios and 12 edge cases were checked. The analysis report is recorded in
the draft feature PR; feature artifacts and all checklist markers are unchanged.
The later explicitly requested checklist review initially satisfied 19/20
composition and 19/20 lifecycle criteria, 38/40 total. It identified
[timed-out cleanup resource retention](specs/002-module-lifecycle/checklists/lifecycle.md#rq-01-explicitly-retain-resources-for-timed-out-cleanup-callbacks)
as needing an explicit pending-callback rule and focused proof obligation, and
[baseline/custom package manifests](specs/002-module-lifecycle/checklists/composition.md#rq-02-baseline-and-custom-artifact-package-lists-disagree)
as needing consistent journey instructions. The user approved both corrections;
the spec, model, contracts, acceptance cases, tasks and quickstart now include
pending StopAsync retention and consistent baseline/custom recipes. Re-evaluation
satisfies all 40/40 custom criteria without waivers. Fresh read-only analysis
and a bounded architecture review found no actionable findings; runtime proof
remains outstanding.
Those specification/design/review stages introduced no lifecycle runtime.
The subsequent authorized implementation adds opt-in metadata validation,
ordinal dependency ordering, supervised composition/build/initialization,
owned route checks, readiness, worker/request admission and bounded cleanup in
Hosting. Old `AddHoard`/`AddModule` calls remain inert. Six independent fixture
packages and the [lifecycle example](examples/LifecycleHost/README.md) exercise
bundled protocol changes, custom artifact addition, explicit recovery and
retained-old-binary registration compatibility.

The external composition lease alone stops the framework host and disposes its
root, after module cleanup and quiescence. `IHoardLifecycle.StopAsync` reports
module coordination; `NotAttemptedOwnerPending` does not claim root release.
Inspect the lease's final `StopResult`. A timeout is bounded waiting, not forced
termination: outstanding work retains resources and can require process exit.
See the [implementation evidence](specs/002-module-lifecycle/plan.md#implementation-evidence)
for exact acceptance results and review limits. Fixtures prove neither real
providers/native clients nor TCP/TLS/proxy drain. Configuration/secrets,
management discovery, caching, conformance, a curated product host and UI remain
later work. Convergence and finalization are separate driver stages.
The subsequent F-02 convergence assessment found one **CRITICAL** shutdown
coordination gap: worker failure invokes synchronous host-stop notification
while holding the lifecycle state lock. A held `ApplicationStopping` callback
blocked both stop and snapshot access beyond the configured shutdown budget.
[Phase 9 / T073](specs/002-module-lifecycle/tasks.md#phase-9-convergence)
records the separately authorized correction: host notification now runs outside
the state lock, tracked before stop begins so pending callbacks protect all
module/root resources. Deterministic regressions cover responsive snapshots,
the original shutdown deadline, once-only cooperative cleanup, and incomplete
cleanup without late retry/disposal. See the
[follow-up evidence](specs/002-module-lifecycle/plan.md#t073-implementation-follow-up).
Fresh convergence verified the T073 notification/deadline/resource boundary but
found one **HIGH** partial diagnostics gap: exceptions from supervised lifetime
and timeout cancellation tasks are consumed without being reported. A
public-API probe invoked a throwing stop-token callback once, yet module stop,
final lease disposal and the final snapshot all contained zero diagnostics.
[Phase 10 / T074](specs/002-module-lifecycle/tasks.md#phase-10-convergence)
now records the separately authorized correction. Lifetime, readiness-timeout
and cleanup-timeout cancellation share off-lock supervision that records safe
additional `CancellationFailure` diagnostics before releasing tracked activity.
Completed faults do not imply pending resource use; late faults appear only in
later snapshots, without changing returned results or triggering deferred cleanup.
Throwing/cooperative and held late-fault regressions preserve primary errors,
deadlines and once-only ownership. See the
[T074 evidence](specs/002-module-lifecycle/plan.md#t074-implementation-follow-up).
The subsequent fresh convergence assessment verified T074 but found one
**HIGH** partial gap in eventual-fault reporting. A readiness callback that
faults after its assessment times out has no diagnostic owner; a timed-out
cleanup fault is also omitted if it occurs before the shared stop completes.
Two isolated public-API probes confirmed the missing safe failure categories,
without changing resource-release outcomes or exposing provider payloads.
[Phase 11 / T075](specs/002-module-lifecycle/tasks.md#phase-11-convergence)
now records the separately authorized correction. Supervised callbacks publish
one safe owner/phase diagnostic before releasing tracked activity, regardless
of whether stop has finished. Direct failures are not duplicated; late faults
do not rewrite returned outcomes or retry cleanup. The implementation review
also identified and corrected omitted worker faults during shutdown and root
disposal dispatch after budget expiry, with failing-then-passing regressions.
See the [T075 evidence](specs/002-module-lifecycle/plan.md#t075-implementation-follow-up).
The subsequent fresh convergence assessment verified T073..T075 but found one
**CRITICAL** response-completion ownership gap. The admission endpoint releases
its request lease before an earlier host-middleware `OnCompleted` callback
finishes: a held callback had no tracked request activity while protocol and
prerequisite cleanup already reported Completed. The paired callback registered
inside the handler correctly retained those resources.
[Phase 12 / T076](specs/002-module-lifecycle/tasks.md#phase-12-convergence)
now records the separately authorized correction. Supervised host build installs
the request-completion boundary before host startup filters and middleware;
admission transfers the request lease to that boundary instead of releasing it
from an endpoint-registered callback. Normal and handled-error regressions prove
owner/prerequisite/root retention after drain expiry, independent safe cleanup,
and cooperative once-only release through all host/handler completion callbacks,
including a throwing callback. Host middleware and access policy still apply.
See the [T076 evidence](specs/002-module-lifecycle/plan.md#t076-implementation-follow-up).
The subsequent fresh convergence assessment found no actionable gaps across
all 22 requirements, seven outcomes, 20 story scenarios, 12 edge cases,
40 acceptance cases, 20 plan obligations and 76 tasks under the eight
constitutional principles. No convergence tasks were appended; the spec, plan,
tasks and reviewer-owned checklists remain unchanged. The next separately
authorized stage at that checkpoint was `finalize`. See the
[convergence checkpoint](docs/DEVELOPMENT.md#f-02-clean-convergence)
for the assessment.
Finalization now verifies the bounded acceptance, unchanged reviewer-owned
gates and implementation architecture-review evidence in the
[plan](specs/002-module-lifecycle/plan.md#finalization-acceptance-2026-10-21-utc).
[PR #6](https://github.com/Stonefly-Labs/Hoard/pull/6) merged into `main` on
2026-10-21 (UTC) at `b80c69fc386541be4f56f6ef2edeca40f43a0e1c`.
The separate `await_merge` stage verified that merge in fetched main and all
76 completed tasks, then recorded F-02 as complete with its directory, PR and
merge commit. The completion checkpoint merged through
[PR #7](https://github.com/Stonefly-Labs/Hoard/pull/7), satisfying the next-spec
gate. The subsequent
[F-03 specification: provider configuration and activation validation](specs/003-provider-configuration/spec.md)
defines deterministic source precedence, explicit provider choices, active option
validation, disabled-module isolation, environment/file secret references, safe
diagnostics, fixed-state restart and reviewed configuration conversion/recovery.
It consumes the existing lifecycle composition gate rather than creating another
activation path. Five prioritized stories, 26 requirements and eight outcomes
have a [built-in specification-quality checklist](specs/003-provider-configuration/checklists/requirements.md)
passing 16/16 criteria; the bounded architecture review found no actionable
findings. These are requirements only: no configuration parser, resolver,
migration tool, new runtime API, discovery endpoint or UI was implemented.
Custom reviewer approval and runtime proof remain later gates.
The subsequent [clarification review](specs/003-provider-configuration/spec.md#clarifications)
found no critical ambiguities across all ten review categories: zero questions,
with requirements, acceptance criteria and scope unchanged. The built-in
checklist remains 16/16, with no newly passing, regressed or unchecked items.
Exact syntax, option contracts, version mappings and finite budget values remain
planning decisions under the specified behavior.
The subsequent [implementation plan](specs/003-provider-configuration/plan.md)
resolves these choices into strict JSON sources, whole-selection replacement,
Hosting-owned option contracts, private single-use validation proofs and
owner-scoped environment/file secrets. Its
[research](specs/003-provider-configuration/research.md),
[state/ownership model](specs/003-provider-configuration/data-model.md),
[contracts](specs/003-provider-configuration/contracts/configuration-format.md)
and [validation guide](specs/003-provider-configuration/quickstart.md) define
36 planned proof cases, including original-preserving synthetic conversion,
bounded pending-work safety and retained binary compatibility.
The bounded planning architecture review found no confirmed contradictions;
actual lifecycle integration, diagnostic remapping and platform publication
remain implementation proof obligations. No runtime API, parser or new check
command is implemented by planning, and existing specification/checklist bytes
remain unchanged.
The subsequent checklist stage generated separate
[configuration](specs/003-provider-configuration/checklists/configuration.md) and
[safety](specs/003-provider-configuration/checklists/safety.md)
requirements-quality checklists with 20 criteria each. These standard-depth
reviews are for maintainers and provider-contract reviewers before implementation
authorization. The 40 reviewer-owned criteria cover
source/option/composition clarity and compatibility, plus secrets, diagnostics,
bounded ownership, restart and original-preserving conversion. Generation is
not requirements approval, implementation authorization or runtime evidence.
At the user's explicit follow-up request, Copilot evaluated all 40 criteria:
configuration 20/20 and safety 20/20 satisfied, with no unresolved writing gaps
or decisions needing user attention. Both checklists record the evidence.
This satisfies the custom requirements-review gate only, not implementation
authorization or runtime acceptance. The specification, design and built-in
16/16 checklist remain unchanged. That review did not start task generation
or implementation.
The subsequent [implementation task list](specs/003-provider-configuration/tasks.md)
originally contained 69 unchecked tasks: shared setup/bounded ownership primitives, five
story phases and cross-cutting acceptance. Source inspection is the first MVP;
composition, secrets, restart/distribution and synthetic conversion follow with
paired tests. Every requirement, outcome and planned CFG-01..36 proof case has
task assignments, including retained binaries, atomic ownership races and
platform publication/interruption. Independent tests/readers may run in parallel;
shared evaluator/lifecycle/orchestrator edits are ordered explicitly.
Specification/design and all checklist bytes remain unchanged. No configuration
API, parser, resolver, converter or validation command is implemented by task
generation.
The subsequent installed read-only analysis found no actionable duplication,
ambiguity, underspecification, inconsistency, constitution conflict or coverage
gap. All 26 requirements and eight buildable outcomes have implementation/proof
tasks; all 69 tasks map to requirements or shared acceptance prerequisites.
The 36 planned cases retain coverage of all 22 scenarios and 13 edge cases,
with complete acyclic prerequisites and ordered shared-file edits.
The report is recorded in [draft PR #8](https://github.com/Stonefly-Labs/Hoard/pull/8)
and completion evidence in the shared checkpoint. Specification, design, task
and checklist bytes remain unchanged; no remediation or implementation occurred.
At that checkpoint, the next separately authorized stage was `implement`, with
the existing 40/40 custom requirements-review gate satisfied. Analysis is not
runtime acceptance.

F-03 now implements strict versioned JSON sources, inert option metadata,
active ordinary checks and local environment/mounted-file secret references.
`EvaluateConfigurationAsync` delegates selection to F-02 and returns a private
single-use proof only after every active check succeeds. Configured adapters
receive fixed owner-only values immediately before service configuration;
legacy compose cannot bypass an enabled opt-in registration. Disabled modules
perform no operational checks or secret reads. No ambient process credentials,
hidden defaults, reload, provider download or fallback are introduced.

Explicit synthetic `fixture-v0` conversion offers secret-free preview, exact
session approval, full validation and complete fresh-file publication without
overwriting the original or an existing/racing destination. A pending bounded
wait is not a rollback guarantee. This is not support for a released old format,
illustrative product YAML, provider-data migration or universal filesystem
power-loss recovery.

`bash scripts/validate-configuration.sh` runs the complete fixture acceptance:
source/option/ownership tests, real packed graphs, unchanged old binaries,
package-only TestServer restart/custom-distribution journeys and actual child
interruption at publication boundaries. Partial `--filter`/`--baseline-only`
modes remain explicitly partial. See the
[implementation evidence](specs/003-provider-configuration/plan.md#complete-implementation),
[provider API guide](docs/PROVIDERS.md#f-03-configuration-boundary) and
[quickstart](specs/003-provider-configuration/quickstart.md).
Publication is measured on this macOS local volume; Linux and other
filesystems are not certified by that run. No runnable cache, production
provider, native-client or conformance claim follows.

The first F-03 convergence assessment reproduced two **HIGH** diagnostic gaps
despite passing existing acceptance: secret failures lost their known setting
identity, and option-check failures discarded the declared rule and winning source.
[Phase 9 / T070–T071](specs/003-provider-configuration/tasks.md#phase-9-convergence)
records the follow-up without changing the original 69 tasks, specification
or reviewer-owned checklists. The separately authorized implementation now
preserves each secret's canonical setting/source through failure, cancellation
and late faults. Option rejections expose only a validated declared `OptionRule`,
the effective field's source and host-owned guidance; unsupported active option
versions identify their own setting/source. No values, locators or provider
messages are exposed, and F-02 remains the sole activation authority.
The subsequent fresh convergence assessment found no actionable gaps across
all 26 requirements, eight outcomes, 22 scenarios, 13 edge cases, 12 grouped
plan decisions, 71 tasks and eight constitutional principles, including
T070/T071. No tasks were appended or artifacts/checklists rewritten.
See the [clean convergence checkpoint](docs/DEVELOPMENT.md#f-03-clean-convergence)
for evidence and measured scope. The separately authorized
[finalization acceptance](specs/003-provider-configuration/plan.md#finalization-acceptance-2026-10-21)
verifies the complete configuration and retained lifecycle/foundation checks,
unchanged requirements-review gates and implementation architecture-review
evidence. [PR #8](https://github.com/Stonefly-Labs/Hoard/pull/8) merged into
`main` on 2026-10-21 (UTC) at
`7fd73267a5154583363c94e9e85b9bac7d4a16b3`. The separate `await_merge` stage
verified that merge in fetched main and all 71 completed tasks, then recorded
F-03 as complete with its directory, PR and merge commit. The progress-only
completion checkpoint merged through
[PR #9](https://github.com/Stonefly-Labs/Hoard/pull/9), satisfying the next-spec
merge gate. No new specification or implementation ran in that completion stage.

The subsequent [F-04 specification: module capabilities and management
discovery](specs/004-module-discovery/spec.md) defines read-only inspection of
known distribution inventory, registration, enablement, support and observed
readiness. Five journeys, 22 functional requirements and eight measurable
outcomes require truthful route/service capability claims, management-read
protection, secret-free descriptive metadata, coherent bounded observations and
safe unavailable-state guidance. Its presentation contract distinguishes
unsupported, disabled, unknown, stale and temporarily not-ready states and
constrains consumer action eligibility without treating capability availability
as execution permission. Reference-consumer proof is in scope; rendered product
screens remain later console work.
The [built-in quality checklist](specs/004-module-discovery/checklists/requirements.md)
passes all 16 specification-quality criteria with no unresolved clarification
markers. This is requirements review only, not custom reviewer approval,
implementation authorization, a discovery endpoint or a delivered UI.
The [clarification review](specs/004-module-discovery/spec.md#clarifications)
found no critical ambiguities across all ten review categories: zero questions
and no requirement or scope changes. The built-in checklist remains 16/16;
exact contract shapes, limits and observation mechanics remain planning
decisions. The subsequent
[F-04 implementation plan](specs/004-module-discovery/plan.md) proposes an
explicit public catalog, atomic lifecycle observations, actual route/service
binding evidence and two protected read-only management routes in Application.
Its research, model, OpenAPI/library/presentation contracts and
[validation guide](specs/004-module-discovery/quickstart.md) map all requirements
and outcomes to 40 future fixture proof cases, including a JSON-only reference
consumer and bounded loopback exposure-adapter tests. Architecture review led
to explicit failure context and a Hosting-owned app/lease/source guard.
These are design obligations, not implemented endpoints or passing runtime
evidence. The subsequent requirements-quality checklist stage generates
[discovery](specs/004-module-discovery/checklists/discovery.md) and
[management](specs/004-module-discovery/checklists/management.md) reviews with
20 criteria each. These standard-depth reviews are for maintainers,
provider/composition reviewers and management-API/consumer reviewers before
implementation authorization. They cover inventory/support truth, coherent
bounded observations, protected disclosure and safe presentation/action rules.
All **40 criteria were generated unchecked and reviewer-owned**; generation
neither evaluates requirements nor supplies runtime evidence. At the user's
explicit follow-up request, the assisted review records **discovery 20/20 and
management 20/20 satisfied**, with no unresolved finding, waiver or decision
requiring maintainer attention. Criterion-level evidence is in each checklist.
The specification, planning artifacts and built-in 16/16 checklist are
unchanged. This satisfies requirements-quality review only, not runtime
acceptance or implementation completion. No task list or implementation was
created by that review.
The subsequent [task-generation stage](specs/004-module-discovery/tasks.md)
produces **78 unchecked tasks**: shared setup/publication primitives, five
story phases and cross-cutting acceptance/documentation work. All 22
requirements, eight outcomes and 40 paired cases have implementation and proof
assignments, with explicit prerequisites and file-disjoint parallel groups.
The work preserves inherited composition/lifecycle authorities, introduces both
HTTP routes only with shared protection, and requires actual binding evidence,
JSON-consumer decisions, loopback exposure adapters, bounded observations and
package/retained-binary proofs. These are future obligations, not passing runtime
results. Existing specification/design/checklist bytes remain unchanged.
At task generation, the next separately authorized stage was read-only
`analyze`, not implementation; the proposed discovery runner still does not exist.
The subsequent installed read-only analysis found no actionable inconsistencies,
ambiguities, coverage gaps or constitutional conflicts. All 22 requirements and
eight buildable outcomes have implementation and focused proof assignments;
all 78 tasks map to requirements or shared acceptance prerequisites. The complete
dependency graph is acyclic, including ordered shared-file edits, and all
40 cases, 22 scenarios and 13 edge cases retain their proof obligations.
The report is recorded in draft
[PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10). All 14 feature files,
including task checkboxes and existing 40/40 custom checklist approvals, remain
unchanged. At that checkpoint the next separately authorized stage was `implement`; analysis
introduces no runtime behavior or passing product evidence.

F-04 now implements opt-in immutable discovery catalogs, the lifecycle owner's
atomic observations, actual route/service binding evidence and protected
`GET /api/v1/discovery` and `GET /api/v1/discovery/openapi.json` slices in
Application. Registration precedes configuration/composition snapshots;
`BindHoardDiscovery` verifies the exact retained app/root/lease and
`MapHoardDiscovery` precedes module mapping. Explicit verified direct-local or
authenticated TLS/trusted-proxy posture is mandatory. Metadata is allowlisted;
reads never resolve secrets, activate providers or refresh readiness.
The BCL-only reference consumer exercises semantic state/action/freshness rules,
not a delivered console.
Usability never grants execution permission.
See the [implemented validation guide](specs/004-module-discovery/quickstart.md)
and [evidence report](specs/004-module-discovery/plan.md#implementation-evidence).
The implementation checkpoint was distinct from convergence, finalization,
merge and release; [PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10)
remained draft at that stage.
The resumed convergence review identified two consumer gaps:
[Phase 9 / T079-T080](specs/004-module-discovery/tasks.md#phase-9-convergence).
Unknown or terminal owner/dependency phases can leave actions enabled when
other fields still claim readiness/usability; fixture evidence text also
replaces the distinct supported/unsupported/unverified label. The follow-up
implementation completes both tasks: owner/dependency phases must be
`assessing-readiness` or `running` alongside ready state, and support text
precedes a separate evidence-scope label. Paired wire regressions reproduce
the original failures and now pass; locked discovery acceptance includes all
15 added scenarios without lock changes. That checkpoint scheduled fresh
`converge`; specification and reviewer approvals remained unchanged.
The subsequent [clean convergence assessment](docs/DEVELOPMENT.md#f-04-clean-convergence)
finds no remaining gaps across all 22 requirements, eight outcomes, 22 scenarios,
13 edge cases and 80 tasks, including both consumer corrections. Fresh locked
discovery acceptance passes 137 tests, all 40 cases, nine package journeys,
18 graph scans and 12 runtime mutations, with no skips or lock changes.
The specification, plan, tasks and reviewer-owned checklists remain unchanged.
That convergence checkpoint scheduled **`finalize`**, not merge, and kept
[PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10) draft.
F-04 [finalization](docs/DEVELOPMENT.md#f-04-finalization) now verifies all
80 completed tasks, unchanged reviewer approvals, prior architecture reviews
and fresh locked acceptance. A second fresh run replays the originally frozen
pre-F-04 lifecycle/configuration/options binaries without recompiling them.
README, affected guides and feature statuses now reflect the accepted
fixture-backed scope. [PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10)
merged into `main` on 2026-10-21 at
`287c7b65a068b50e672d92f2d535ef79c910ac0b`.
The separate `await_merge` stage verified that merge, all 80 completed tasks
and the published [v0.0.4-alpha source prerelease](https://github.com/Stonefly-Labs/Hoard/releases/tag/v0.0.4-alpha)
at that exact commit, including generated notes and both source archives.
It records F-04 complete with its feature directory, PR, merge commit and release
evidence. [PR #12](https://github.com/Stonefly-Labs/Hoard/pull/12) merged the
running checkpoint before the completion changes were committed. The follow-up
completion checkpoint merged through
[PR #13](https://github.com/Stonefly-Labs/Hoard/pull/13), satisfying the next-spec
merge gate.
No new specification, implementation, package publication or deployment ran
in this completion stage; the prerelease contains source only.
The subsequent [F-05 specification: metadata persistence provider
contract](specs/005-metadata-persistence/spec.md) defines isolated durable state,
atomic related changes, explicit concurrency/retry outcomes, reference and lease
safety, controlled schema upgrades, backup/recovery and provider-neutral
qualification. Five journeys, 23 scenarios, 24 requirements and eight measurable
outcomes pass the 16-item [built-in specification-quality
checklist](specs/005-metadata-persistence/checklists/requirements.md).
These are future acceptance obligations: bounded SQLite durability proof and
an independent alternative fixture do not claim the later production provider,
generic certification, cross-store transactions or multi-node safety.
No persistence code, schema or new validation command exists from this stage;
the subsequent [clarification review](specs/005-metadata-persistence/spec.md#clarifications)
finds all ten review categories clear, with zero questions and no requirement,
acceptance or scope changes. The built-in quality checklist remains 16/16 with
no marker changes; this is not custom reviewer approval or runtime evidence.
The subsequent [implementation plan](specs/005-metadata-persistence/plan.md),
[logical model](specs/005-metadata-persistence/data-model.md) and
[public contract](specs/005-metadata-persistence/contracts/metadata-api.md)
resolve operation shapes, common limits/budgets, 24-hour operation tickets,
publication guards, reference generations and fenced leases without changing
existing provider markers. The [recovery design](specs/005-metadata-persistence/contracts/recovery.md)
defines controlled schema admission, real process-crash boundaries and verified
backup restoration; [48 planned proof cases](specs/005-metadata-persistence/contracts/acceptance.md)
separate SQLite durability from independent memory-fixture semantics.
The [validation quickstart](specs/005-metadata-persistence/quickstart.md) clearly
labels new commands as future implementation work. Bounded architecture review
found no design findings; no API, fixture, schema, qualification or production
support is delivered by planning. The subsequent checklist stage adds standard-depth
[metadata contract](specs/005-metadata-persistence/checklists/metadata.md) and
[recovery](specs/005-metadata-persistence/checklists/recovery.md)
requirements-quality checklists, with 20 criteria each for maintainer/provider
reviewers. At the user's request, an assisted assessment finds written coverage
for all 40 criteria, with no unresolved finding or decision needing maintainer
attention. Generated markers remain unchecked: the assessment is not formal
checklist approval or implementation evidence. The subsequent
[task-generation stage](specs/005-metadata-persistence/tasks.md) defines 83
unchecked tasks: shared setup/foundation, five story increments and cross-cutting
acceptance. All 24 requirements, eight outcomes, 23 scenarios, 14 edge cases and
48 planned proof cases map to implementation and focused checks, with explicit
prerequisites and independent provider lanes. Existing specification/design and
checklist bytes remain unchanged; no product implementation or qualification
occurs. At that checkpoint, read-only `analyze` was the next separate stage.
The subsequent installed read-only analysis finds no actionable duplication,
ambiguity, underspecification, inconsistency, coverage gap or constitutional
conflict. All 24 requirements and eight buildable outcomes have tasks; all 23
scenarios, 14 edge cases and 48 proof cases retain focused mappings. The
83-task, 107-edge prerequisite graph is complete and acyclic. The
[analysis report](https://github.com/Stonefly-Labs/Hoard/pull/14#issuecomment-6329405510)
records the assessment; feature artifacts and every checklist marker remain
unchanged. The subsequently requested assisted checklist review evaluates and
marks **metadata 20/20 and recovery 20/20 satisfied**, with criterion-group
evidence in each checklist and no unresolved finding or decision needing
maintainer attention. This satisfies the custom requirements-quality review
gate; **`implement`** remains next through a separate invocation. The checkpoint,
all 83 tasks and the specification/design remain unchanged. Requirements review
and artifact analysis are not persistence, durability or production-support
evidence.
The separately authorized implementation delivers the operational contract and
fixture qualification. Setup
T001..T006 added the deterministic harness, independently packed fixture
scaffolds, pinned private SQLite dependency, retained pre-F-05 binary recipe
and fail-closed [metadata evidence command](scripts/validate-metadata.sh).
The subsequent implementation adds BCL-only records and separate store/schema/
publication interfaces without changing the marker. Independently packaged
SQLite and copy-on-write memory fixtures exercise transactions, receipts,
references, leases, admission and bounded cleanup. The runner uses one common
test/consumer binary for both compositions, real parent-terminated SQLite
children, verified isolated restore, actual package scans and the frozen old
marker binary. Its complete manifest requires all 39 logical cases for both
providers and nine SQLite-only durable cases; memory durability is explicitly
not applicable. Preparation and focused selectors never claim full qualification.
The [quickstart](specs/005-metadata-persistence/quickstart.md) documents commands,
retained private evidence, recovery and fixture-only limits. Implementation
does not deliver a production persistence provider or runnable cache.
Complete locked qualification passes all 87 applicable provider/case entries;
the nine memory durability entries are explicitly non-applicable. Existing
foundation/lifecycle/configuration/discovery acceptance and repository tooling
also pass with unchanged lock hashes. The feature remains a draft in
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14); separate `converge`
and `finalize` stages remain before any merge gate.
The subsequent convergence assessment appends one HIGH-priority correction,
[Phase 9 / T084](specs/005-metadata-persistence/tasks.md#phase-9-convergence):
both fixture providers classify a null decoded continuation key as
`InternalFailure/OperatorRecovery` instead of `InvalidInput/CorrectInput`.
Fresh locked qualification still passes its existing cases; the additional
probe exposes a missing malformed-cursor regression, not a clean convergence
result. Product code, specification, plan and existing task completions are
unchanged. That checkpoint returned to **`implement`** for T084.
The subsequent implementation correction is complete: both fixtures reject
null/omitted decoded keys safely, and six paired malformed-field regressions
preserve valid resumption and complete dataset traversal. Full locked
qualification passes 65 common tests per provider, all 87 applicable entries
and nine explicit memory durability exclusions. See the
[correction evidence](specs/005-metadata-persistence/plan.md#t084-malformed-continuation-correction).
Fresh **`converge`** is next, followed by finalization; PR #14 remains draft.
That fresh assessment finds one HIGH partial gap in SQLite page reads:
a stored registry with a null label is incorrectly classified as
`InvalidInput/CorrectInput`, while grouped reads correctly return
`CorruptState/OperatorRecovery` for the same record.
[Phase 10 / T085](specs/005-metadata-persistence/tasks.md#phase-10-convergence)
records the correction and missing regression; no implementation changes occur
in convergence. Fresh full locked qualification passes its existing cases but
does not cover or waive this additional runtime-proven gap. The next stage is
**`implement`** for T085, then fresh convergence; PR #14 stays draft.
The T085 correction is now complete: SQLite pages reuse the corruption-aware
stored-record decoder and return `CorruptState/OperatorRecovery` for damaged
payloads, while bad caller input retains `InvalidInput/CorrectInput`.
Paired regressions prove complete failure, sanitized diagnostics, unchanged
damaged data and exact valid-page recovery. Full locked qualification passes
66 common tests per provider and all 87 applicable entries, with nine explicit
memory durability exclusions. See [T085 evidence](specs/005-metadata-persistence/plan.md#t085-stored-page-corruption-correction).
All 85 tasks are complete; fresh **`converge`** is next, then finalization.
PR #14 remains draft; no merge is requested.
The subsequent fresh convergence finds two HIGH partial corruption gaps in
SQLite: a damaged authorization-partition field is silently omitted from a
filtered page, and reconciliation returns a successful committed receipt with
an invalid null target. Both are reproduced against freshly packed binaries;
restoring the synthetic data recovers valid results and integrity.
[Phase 11 / T086 and T087](specs/005-metadata-persistence/tasks.md#phase-11-convergence)
append the correction and regression work without changing application code,
the specification, plan, previous tasks or checklist markers. Full locked
qualification passes its existing 66 tests per provider and 87 applicable
entries, but does not cover or waive these newly demonstrated paths.
The next stage is **`implement`** for both tasks, followed by fresh convergence;
PR #14 stays draft, with no merge requested.
Both corrections are now complete. SQLite validates page candidates before
payload-based filters and uses one bounded ledger/receipt decoder for replay,
reconciliation and schema integrity. Paired regressions preserve damaged data,
query isolation, original-ticket recovery and nonduplicate effects. Full locked
qualification passes 72 common tests per provider and all 87 applicable entries,
with nine explicit memory durability exclusions. See
[T086/T087 evidence](specs/005-metadata-persistence/plan.md#t086t087-filtered-page-and-receipt-corruption-corrections).
All 87 tasks are verified complete; fresh **`converge`** is next, then
finalization. [PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) remains
draft; no merge is requested.
The subsequent installed convergence assessment finds no actionable gaps across
all 24 requirements, eight outcomes, 23 scenarios, 14 edge cases and 87 tasks.
Fresh full locked qualification passes 72 common tests per provider and all
87 applicable entries, with nine explicit memory durability exclusions.
Tasks, specification, plan, checklists, product/tooling sources and all 88 locks
remain unchanged. See the [clean convergence evidence](docs/DEVELOPMENT.md#f-05-clean-convergence).
The next separately invoked stage is **`finalize`**; PR #14 remains draft,
and no merge is requested.
Finalization now verifies all 87 completed tasks, clean convergence, unchanged
requirements/checklist approvals, applicable architecture reviews and current
documentation. Fresh full locked qualification passes 72 common tests per
provider, all 87 applicable entries and nine explicit memory durability
exclusions, with all 88 locks unchanged. See the
[finalization evidence](docs/DEVELOPMENT.md#f-05-finalization).
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) merged into `main` at
`81e2e8d41e08aafc9e89f388dab78e7509227dd5`. The separate **`await_merge`** stage
verified that merge and published
[`v0.0.5-alpha`](https://github.com/Stonefly-Labs/Hoard/releases/tag/v0.0.5-alpha)
at that exact commit. Its successful source-release run, generated notes,
annotated remote tag and both automatic source archives are verified; no
runtime binaries or packages are published. See the
[merge/release evidence](docs/DEVELOPMENT.md#f-05-merge-completion-and-alpha-source-release).
[Completion-checkpoint PR #15](https://github.com/Stonefly-Labs/Hoard/pull/15)
merged into `main`, recording F-05 complete with release metadata.
**F-06 is merged and its alpha source release is published; the completion
checkpoint awaits maintainer merge.**
The additive BCL-only storage contracts have independent Local and simulated
ObjectSemantics fixtures for verified streaming/publication, protected reads,
exact-ticket reconciliation, bounded recovery and reference-safe deletion.
The current locked run contains **96 attributed entries: 92 passes and exactly
four Object AS-41..44 exclusions**, on macOS 26.5 arm64, .NET 10.0.7 and APFS.
Actual 256 MiB/4 GiB write/read runs on each fixture stayed below 64 MiB
incremental OS peak RSS; all six local SIGKILL/fresh-process barriers passed.
The same compiled consumer exercises all 16 common operations on both choices.
Eight resolved graphs, compiled leak/consumer controls and the original
pre-F06 marker binary preserve package independence and compatibility.

Both fixtures declare the required baseline and become ready only after
successful explicit admission. Missing guarantees/version/authority reject
before root I/O; disabled selections remain inert. Existing F-02/F-03
composition tests demonstrate startup/stop and explicit restart: Local reopens
its exact known identity; Object replacement starts a fresh root and epoch.
Cancellation cannot discard a successfully handed-off ticket/read session.
Unclaimed results are reclaimed under retained ownership; expired staging is
matched by exact generation, and failed unclaimed-result reclamation blocks admission/readiness
until an exact bounded shutdown retry succeeds.

The full verifier requires every AS case's exact parameterized runtime witnesses,
actual context/package/lock hashes, paired passed TRX names and durations,
four measurements, six crash proofs and materialized public qualification records.
Executed mutation pairs and 29 altered-full-manifest checks reject false claims.
All four focused modes remain `qualification: false`; their passes never
substitute for full acceptance. All five predecessor gates pass separately
with tracked locks; only 15 local fixture-package hashes in six locks changed
in the final checkpoint, preserving versions, graphs, external hashes and the
frozen baseline. See the [follow-up evidence](specs/006-artifact-storage/plan.md#convergence-follow-up-implementation-2026-10-22)
and [qualification guide](specs/006-artifact-storage/quickstart.md).
These are test-only fixtures, not a working cache, production provider, remote
service, power-loss certification or generalized F-07 conformance.

The subsequent convergence assessment reproduced two **HIGH partial gaps** on
both fixtures despite a fresh passing full locked run.
[Phase 9 / T087-T088](specs/006-artifact-storage/tasks.md#phase-9-convergence)
recorded the remaining work: failed staging reclamation reported release/readiness
but strands bytes and reserved capacity even after access returns; sequential
recovery paging exhausted the 32 retained cursor slots before finishing a stable
35-row inventory. The follow-up implementation completes both tasks on both
fixtures: failed prefixes retain exact cleanup ownership, block readiness/new
admission and support bounded maintenance or shutdown retry without reopening
finalized tickets. Settled commit receipts remain reconcilable while residual
staging is reclaimed, with committed bytes untouched. Consumed recovery cursors
are retired; 32 independent scans each traverse all 35 rows and free their
terminal handles. Fresh locked qualification passes 237 logical/crash tests,
all transfer/crash/package proofs and the exact 92-pass/four-exclusion matrix.
All 88 tasks are checked; reviewer-owned checklists remain unchanged.
See the [follow-up checkpoint](docs/DEVELOPMENT.md#f-06-convergence-follow-up-implementation).
That implementation checkpoint scheduled fresh **`converge`**;
[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) remains draft.
No clean-convergence, finalization, merge or release is claimed.

Fresh convergence verifies those two corrections but reproduces a separate
ObjectSemantics unpublished-assembly leak:
[Phase 10 / T089](specs/006-artifact-storage/tasks.md#phase-10-convergence).
Failed unlink after assembly leaves another untracked payload on each commit
retry while reporting released cleanup and readiness. Abandonment releases its
reservation and shutdown reports release without reclaiming those objects.
The writable-directory control leaves no residual payloads. A fresh full locked
run passes the existing matrix, but does not cover or waive this new failure
path. That assessment scheduled **`implement`** for T089, then fresh convergence.
See the [assessment and reproduction](docs/DEVELOPMENT.md#f-06-fresh-convergence-unpublished-object-cleanup).
The subsequent implementation completes T089: unselected assemblies are owned
before creation, count/byte bounded and retained on failed unlink. Incomplete
cleanup blocks readiness and retries until exact maintenance or shutdown
reclaims the payload; selected objects and settled reuse receipts survive.
Fresh locked full qualification passes 243 logical/crash checks and the exact
92-pass/four-exclusion matrix, including partial/complete assembly failures,
cancellation, repeated denial and restored capacity.
All 89 tasks are checked. See the
[implementation evidence](specs/006-artifact-storage/plan.md#unpublished-object-cleanup-implementation-2026-10-22).
The next stage is fresh **`converge`**; PR #16 stays draft, with no finalization,
feature completion or release claim.

The preceding convergence verifies T089's cleanup correction but finds that both
evidence validators fail to quarantine a detected-truncated incarnation.
After validation returns `CorruptContent`, opens still succeed; externally
restoring the bytes lets the same evidence validate and duplicate publication
return `AlreadyPresentVerified`, without explicit recovery.
[Phase 11 / T090](specs/006-artifact-storage/tasks.md#phase-11-convergence)
records the HIGH partial correction and paired regression work. A fresh full
locked run still passes its existing 92-pass/four-exclusion matrix; it does not
cover or waive this validation-first corruption path. That assessment scheduled
T090 implementation. See the
[assessment and reproduction](docs/DEVELOPMENT.md#f-06-fresh-convergence-corruption-quarantine).

The subsequent implementation completes T090 and all **90 tasks**. Every
committed-content detection path quarantines the exact incarnation; external
byte restoration cannot revive opens, evidence validation or duplicate reuse.
Local quarantine persists across reopen, including bounded shutdown persistence
retry after a denied record write. Object quarantine remains process-local.
Delayed opens and unresolved reconciliation recheck quarantine before settlement;
access failures remain distinct, and authorized delete/recreate gets a new stamp.
Original finalized receipts remain reconcilable historical decisions, not health
certificates. Fresh locked qualification passes 261 logical/crash checks and the
exact 92-pass/four-exclusion matrix with all transfer/crash/package proofs.
See the [implementation evidence](specs/006-artifact-storage/plan.md#corruption-quarantine-implementation-2026-10-22).
The next stage is separately invoked fresh **`converge`**; PR #16 stays draft.
No finalization, feature completion, merge or release is claimed.

The subsequent installed convergence assessment finds no actionable gaps across
all 25 functional requirements, eight success criteria, 23 acceptance scenarios,
15 edge cases, eight plan decisions, 90 existing tasks and eight constitutional
principles. T087..T090 remain satisfied, including retained failed cleanup,
consumed-cursor retirement and exact-incarnation corruption quarantine.
No tasks are appended; all feature artifacts and reviewer-owned checklists
remain unchanged. Fresh default locked full qualification again passes 261
logical/crash checks, all transfer/crash/package proofs and the exact
92-pass/four-exclusion matrix. See the
[clean convergence checkpoint](docs/DEVELOPMENT.md#f-06-clean-convergence).
That checkpoint scheduled **`finalize`** and kept PR #16 draft;
convergence alone did not establish merge readiness or feature completion.

The subsequent finalization verifies all 90 completed tasks, unchanged reviewer
approvals and corrected architecture findings, and repeats full locked artifact
qualification and tooling regressions. README, development guidance and feature
status now record the [finalization evidence](docs/DEVELOPMENT.md#f-06-finalization).
[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) subsequently merged at
`9389016c0285c79f6f515f59805a5a41c69b0767`. The separate **`await_merge`** stage
verified that merge and published
[`v0.0.6-alpha`](https://github.com/Stonefly-Labs/Hoard/releases/tag/v0.0.6-alpha)
at that exact commit. Its successful source-release run, annotated remote tag,
generated notes and both automatic source archives are verified. The helper
records F-06 complete with release metadata in
[completion-checkpoint PR #17](https://github.com/Stonefly-Labs/Hoard/pull/17).
That completion checkpoint subsequently merged through PR #17, enabling the
separately invoked F-07 specification stage below.
See the [merge/release evidence](docs/DEVELOPMENT.md#f-06-merge-completion-and-alpha-source-release).
No runtime binaries, packages, containers, infrastructure action or deployment
are included; no new spec or PR merge runs in this invocation.

The separately invoked **`specify`** stage creates the
[F-06 artifact blob storage provider contract](specs/006-artifact-storage/spec.md)
on `feature/006-artifact-storage`. Five journeys cover complete verified
publication, bounded multi-GB streaming, interrupted-work recovery, reader-
and reference-safe deletion, and provider-neutral qualification without assuming
atomic rename. Its [built-in quality checklist](specs/006-artifact-storage/checklists/requirements.md)
passes all 16 criteria across 25 requirements and eight measurable outcomes,
including the required 4 GiB transfer proof within 64 MiB incremental transfer
memory. At that specification checkpoint the fixtures were later proof
obligations, not delivered providers or remote-service support. See the
[stage scope](docs/DEVELOPMENT.md#f-06-artifact-storage-specification).
The subsequent [clarification review](specs/006-artifact-storage/spec.md#clarifications)
finds all ten ambiguity categories clear, with zero questions and no requirement
or scope changes. The built-in quality checklist remains 16/16; exact budgets
and proof mechanics remain constrained planning decisions. See the
[review evidence](docs/DEVELOPMENT.md#f-06-artifact-storage-clarification).
The subsequent [implementation plan](specs/006-artifact-storage/plan.md)
defines additive BCL-only operations, exact finite budgets, protected full-read
completion, ticket/incarnation recovery and one shared authority for metadata
publication and safe deletion. Its [acceptance matrix](specs/006-artifact-storage/contracts/acceptance.md)
traces all 25 requirements/eight outcomes to 48 planned cases, including actual
256 MiB/4 GiB and peak-RSS proof on both independent fixtures. Local process-crash
qualification remains distinct from simulated object semantics and power-loss
or production-provider claims. Architecture review's guard-recognition omission
is addressed by authority-owned retention without reentering admission.
See the [planning scope](docs/DEVELOPMENT.md#f-06-artifact-storage-planning)
and [qualification guide](specs/006-artifact-storage/quickstart.md).
Those were planning-only artifacts; the implementation evidence above records
the subsequently delivered APIs and acceptance command.
The subsequent checklist stage generates standard-depth
[storage](specs/006-artifact-storage/checklists/storage.md) and
[recovery](specs/006-artifact-storage/checklists/recovery.md) requirements-quality
checklists for maintainer/provider review, with 20 initially unchecked items each.
At the maintainer's explicit request, a separate assisted review evaluates every
item, initially satisfying storage **20/20**, recovery **19/20**. The
[high-priority consistency issue](specs/006-artifact-storage/checklists/recovery.md#rq-01-finite-release-versus-non-cooperative-work)
identified a conflict: the specification promised finite resource release in all
failure cases, while the plan permits non-cooperative I/O to retain bounded
resources and block readiness until actual settlement. At that checkpoint,
recovery CHK012 remained unchecked and blocked implementation approval,
not task generation; no requirement change or waiver was presumed.
See the [review scope](docs/DEVELOPMENT.md#f-06-artifact-storage-checklists-and-assisted-review).
The subsequent [implementation task list](specs/006-artifact-storage/tasks.md)
initially contained **86 unchecked tasks**: shared setup/contracts, five story phases and
cross-cutting acceptance. All 25 requirements, eight outcomes, 23 scenarios,
15 edge cases and 48 acceptance cases have implementation/proof assignments,
with explicit prerequisites and file-disjoint parallel opportunities. US1 is
the verified-publication/read MVP, not complete qualification or a runnable cache.
Actual four size/provider transfer measurements, six local crash barriers,
shared reference/deletion authority, independent packages and exact 96-entry
qualification were future obligations at task generation. Task generation left all existing
requirements, design artifacts and checklist markers unchanged; planned tasks
did not resolve RQ-01 or bypass the requirements-review gate.
See the [task-stage scope](docs/DEVELOPMENT.md#f-06-artifact-storage-task-generation).
The subsequent [maintainer-approved RQ-01 clarification](specs/006-artifact-storage/spec.md#approved-follow-up-2026-10-22-rq-01-resource-ownership)
aligns US2 scenario 3, FR-009 and SC-006 with the existing design: finite caller
return and cleanup attempts, finite actual resource release for cooperative
I/O, and bounded retained ownership/incomplete cleanup/blocked admission and
readiness for non-cooperative work until settlement or owner-controlled process
termination. No live-resource release, forced borrowed-stream disposal or false
cleanup/rollback is allowed. The separate recovery CHK012 re-review now satisfies
**all 40/40 custom criteria without waivers**; AS-39 remains mandatory and all
86 implementation tasks remained unchecked at that clarification checkpoint. See the
[follow-up evidence](docs/DEVELOPMENT.md#f-06-approved-rq-01-clarification-and-re-review).
At that checkpoint, the next separately authorized stage was read-only **`analyze`**.
No analysis, implementation or qualification execution occurred in the approved
clarification/re-review; satisfied criteria establish requirements quality,
not delivered behavior or permission to skip the analysis gate.
The subsequent installed read-only analysis finds no actionable duplication,
ambiguity, underspecification, constitutional conflict, coverage gap or
inconsistency. All 25 requirements and eight buildable outcomes have
implementation/proof tasks; all 86 tasks map to requirements or shared acceptance
prerequisites. The complete prerequisite graph is acyclic, shared-runner edits
are serialized and retained baseline capture precedes public API changes.
The approved RQ-01 distinction remains consistent with required AS-39.
All 12 feature artifacts, 86 then-unchecked tasks and existing checklist markers
remained unchanged by analysis. The full report is recorded in draft
[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16); see the
[analysis scope](docs/DEVELOPMENT.md#f-06-artifact-storage-read-only-analysis).
That checkpoint scheduled **`implement / ready`** for a separate invocation,
with the existing 40/40 custom-review gate satisfied. Analysis supplies no
runtime evidence and executes no implementation or qualification.

The separately invoked **F-07 `specify`** stage creates the
[provider conformance, compatibility and composition specification](specs/007-provider-conformance/spec.md).
Five journeys define reusable category checks, safe host compositions, version
and consumer compatibility, contributor templates, and attributable local/CI
reports. Its [built-in quality checklist](specs/007-provider-conformance/checklists/requirements.md)
passes 16/16 criteria across 24 requirements and eight measurable outcomes.
The planned baseline uses the existing independent metadata/artifact fixtures,
keeping logical, durable-local and simulated qualification distinct. It does
not deliver a harness, CI workflow, production provider or certification result;
operational protocol/identity and native-client checks remain separately scoped.
See the [stage scope](docs/DEVELOPMENT.md#f-07-provider-conformance-specification).
The subsequent [clarification review](specs/007-provider-conformance/spec.md#clarifications)
found no critical ambiguities across all ten review categories: zero questions
and no requirement or scope changes. The built-in checklist remains 16/16;
custom reviewer approval and qualification evidence are not implied.
Exact interfaces, report formats, budgets and the bounded matrix remain
planning decisions. See the [review scope](docs/DEVELOPMENT.md#f-07-provider-conformance-clarification).
The subsequent [implementation plan](specs/007-provider-conformance/plan.md)
defines a test-only shared SDK, explicit provider bindings, five local/CI
profiles, a finite composition/version matrix and fail-closed evidence.
It retains all 192 inherited metadata/artifact entries and adds 48 focused
proof obligations, including contributor red/green examples and exact runtime
witness attribution. Real durable-local, simulated and unqualified service
scopes remain separate. These are design artifacts, not implemented commands,
CI, approved custom checklists or certification results. See the
[planning scope](docs/DEVELOPMENT.md#f-07-provider-conformance-planning).
The subsequent checklist stage creates standard-depth
[conformance](specs/007-provider-conformance/checklists/conformance.md) and
[evidence](specs/007-provider-conformance/checklists/evidence.md)
requirements-quality checklists, 20 criteria each, for maintainer review before
implementation. The requested assisted assessment finds written support for all
40 criteria and no unresolved requirements blocker or product decision.
All 40 reviewer-owned markers remain unchecked; assessment is not approval.
Preserving inherited assertion coverage, actual large-transfer/recovery proof,
CI scratch capacity and sanitation before diagnostic persistence remain
implementation obligations. See the
[assessment scope](docs/DEVELOPMENT.md#f-07-provider-conformance-checklists-and-assisted-assessment).
The subsequent [task list](specs/007-provider-conformance/tasks.md) defines 86
unchecked tasks across setup, shared foundations, five story increments and
final acceptance. It maps all 24 requirements, eight outcomes and QC-01..48
to implementation and focused proof, preserving all inherited cases and
subvariants. Explicit prerequisites serialize shared tooling edits and seal
old binaries before candidate builds. The MVP is complete category-scoped US1,
not full five-profile qualification. No implementation or qualification ran.
The subsequent read-only analysis finds no actionable cross-artifact or
constitutional findings. All 24 requirements and eight outcomes have
implementation and focused proof tasks; all 86 tasks have complete acyclic
prerequisites. Feature artifacts and checklist markers remain unchanged.
At that analysis checkpoint, **`implement`** required reviewer approval or
explicit authorization for the 40 unchecked custom checklist items.
Analysis supplies no runtime qualification. See the
[analysis scope](docs/DEVELOPMENT.md#f-07-provider-conformance-analysis).

Implementation subsequently began with explicit maintainer authorization;
the reviewer-owned checklist markers remain unchanged. Partial test SDK,
catalog, baseline-preparation and evidence/execution foundations are checked in,
but no common-suite extraction or five-profile qualification is delivered.
Implementation continues under the maintainer's direction to resolve issues
autonomously. The Memory fixture now has bounded, targeted corruption controls
and real stored-payload/receipt validation without a dependency on the SDK.
Witness binding/matrix admission and initial ownership/cleanup fixes are
implemented; full acceptance and final architecture review remain outstanding.
Native execution admission now requires both inherited Linux confinement and
kernel PID-handle group signalling, verified before the target is released;
unsupported hosts fail admission rather than claiming unsafe settlement.
The corrected directory-ownership implementation passed 28 native checks without
skips. The SDK now also has owned-resource allocation and a bounded VSTest logger;
composition/version fixtures exercise existing Hosting APIs. These remain
non-qualifying foundations, not shared provider suites or a completed CLI.
Under the maintainer's autonomous-continuation direction, CP-11/FR-007 now
explicitly preserve the existing lifecycle: declarations reject before
construction; actual route conflicts reject during mapping before publication,
initialization, readiness or admission. No product route-contract redesign or
duplicate-ID substitute is used. See the
[implementation checkpoint](specs/007-provider-conformance/plan.md#partial-implementation-checkpoint).

Setup tasks T001..T006 are now complete, including all six historical revision
pins and strict required-field/extension checks for every evidence entity.
Actual safe-logger records can now be ingested with exact manifest/proof/
completion relationships; proof walking rejects symlinked roots and bounded
overflow. A separate diagnostic Linux SDK/logger job seals historical baselines
before candidate compilation. Its [Linux run](https://github.com/Stonefly-Labs/Hoard/actions/runs/39913608773)
passed all six allocator facts and five logger smoke scenarios, including the
required negative/incomplete classifications. None of this
completes the remaining foundations or grants provider qualification.

The SDK also supplies a bounded safe fault-observation buffer with immutable
snapshots; observations are setup evidence, never provider-selected pass results.
T007's typed contracts and strict entities are complete; category adapters,
runtime attribution, independent evaluation and the remaining foundations are
not.
Cross-platform historical archive preparation is explicit and non-qualifying:
alternate locks preserve the original dependency graph/source locks and bind
the platform-built bytes before any candidate compilation.
All 144 distinct composition/version/classification runtime identities now match
actual package-mode discovery. A separate tracked composition package lock was
prepared against the sealed historical feed and replayed in an independent fresh
cache without changing predecessor locks. This verifies discovery, not behavior
or loaded-provider attribution. The logger and Python ingestion preserve finite
version-range parameter punctuation while still rejecting paths and free text;
55 current source SDK checks pass, not a current package-acceptance result.
The catalog also maps 41 architecture/inspection identities and ten SDK catalog
admission identities, all matched against actual discovery. QC-01..48 now name
their individual required subproofs instead of one aggregate label. These are
expectations, not executed control results. Strict SDK catalog admission rejects
unknown profiles, malformed/duplicate fields, missing profiles and overflowing
results without returning a shortened catalog.
T009's owned-execution regression inventory also passes on Linux, including
concurrent private caches and containment that leaves the other run alive.
Cleanup now removes only settled synthetic stores, feeds and caches, retaining
proofs, safe diagnostics and the ownership ledger. Live work and failed ledger
publication remain `Retained`; explicit retries preserve earlier cleanup failures.
T010's controller helper/private ledger passed all 70 native foundation checks;
end-to-end profile integration remains unfinished. Diagnostic capture now also
checks the 1 KiB event limit before JSON expansion, bounds raw line buffering,
and preserves safe prefixes plus closed failure codes. T011 passed all 72 native
foundation checks in run `39918257385`; its SDK/logger diagnostic also passed.
This is not completed-profile evidence.

The next supervisor increment counts admission work in command deadlines,
reserves termination/cleanup time, and bounds control/barrier scopes. Native
artifact/baseline allocation now checks both actual capacity and a finite local
filesystem allowlist before creating a workspace; path-free preflight facts are
retained separately from synthetic stores. Run `39920220726` passed all 79
native foundation checks plus its six-baseline SDK/logger diagnostic. A further
one-writer gate rejects overlapping commands, cleanup and state publication
before admission. Insufficient scratch now reports explicit `Incomplete`, not
a reduced run; evidence violations retain `Failed`. Run `39921337767` at
`b9d335a` passed all 82 native foundation checks and seven SDK scenarios/15
observations. A subsequent parent-substitution regression exposed allocation
following a swapped ancestor after preflight. Capacity/filesystem probes and
workspace creation now use pinned directory descriptors; parent substitution
or traversal rejects without writing to the outside sentinel.
The current changes pass 190 tooling checks with ten native skips on macOS.
Run [39924374116](https://github.com/Stonefly-Labs/Hoard/actions/runs/39924374116)
at `79663dd` then passed all 85 native foundation checks without skips and eight
SDK diagnostic scenarios/25 observations, including the ten catalog cases.
T008/T012 are complete within their catalog/supervisor foundation scope.
Immutable complete input snapshots, loaded-provider attribution and profile
integration remain unfinished; no qualification is claimed.

The next T013 increment shares descriptor-anchored read-only source snapshots
with the SDK diagnostic, including example projects and build/ignore settings.
Aliased/replaced roots, changed ancestors and unlisted special files reject
without redirecting writes. Real Git identity distinguishes dirty local bytes
from a clean CI checkout pinned to the exact workflow SHA, without ambient Git
overrides. SDK smoke preparation now uses a separate alternate lock; frozen
source locks are never rewritten. Run
[39927534630](https://github.com/Stonefly-Labs/Hoard/actions/runs/39927534630)
at `4e17986` verified this path: 91 native foundation checks without skips,
eight SDK scenarios/25 observations, and all six historical baselines.
The following input-sealing increment captures package metadata/archive/runtime
hashes from one bounded byte sequence, verifies actual synthetic source mapping,
and recomputes complete SDK diagnostic inputs after execution. Free space remains
an admission measurement, not a supposedly immutable value. Run
[39929542533](https://github.com/Stonefly-Labs/Hoard/actions/runs/39929542533)
at `44881ff` verified 99 native foundation checks and eight SDK scenarios.
The next increment adds immutable typed binding snapshots and shared profile
capture of actual source, packages, locks, declarations, runtime files,
synthetic source policy and verified historical baselines. It passes 207 local
tooling checks (ten native skips) and 57 source SDK tests; native verification
is recorded below. Actual loaded-provider attribution remains T014 work.
An additional mutation challenge exposed unbound generated runtime configuration.
SDK capture now includes dependency/runtime configuration files alongside DLLs;
changing them after admission also rejects.
Run [39932469750](https://github.com/Stonefly-Labs/Hoard/actions/runs/39932469750)
at `525bdf0` verified that repair and shared capture: 102 native checks without
skips, nine SDK scenarios/27 observations and all six historical baselines.
T013's input-capture foundation is complete; implementation continues with T014,
not qualification or merge readiness.

T014's first repair admits bounded enum parameter tokens in both runtime
transports while retaining exact independently expected identities. Local
regressions pass, and a tenth native diagnostic scenario now selects the two
actual enum theory rows. Run
[39933805476](https://github.com/Stonefly-Labs/Hoard/actions/runs/39933805476)
at `a1fe180` verified 103 native checks without skips and ten scenarios/
29 observations. Actual-instance assembly capture and strict runtime/package
correspondence also passed run
[39934964377](https://github.com/Stonefly-Labs/Hoard/actions/runs/39934964377)
at `0a0b1d1`: 105 native checks without skips, eleven scenarios/31 observations
and all six baselines. The next local increment separates exact discovery from
execution and binds completion to the captured record bytes; actual portable
VSTest discovery and run
[39936903326](https://github.com/Stonefly-Labs/Hoard/actions/runs/39936903326)
at `6a04293` passed: 108 native checks without skips, twelve scenarios/
35 discovery records/35 execution observations and all six baselines. A
catalog-owned append-only runtime case-history API also passed run
[39938028171](https://github.com/Stonefly-Labs/Hoard/actions/runs/39938028171)
at `a9039fa`: 111 native checks without skips and the same twelve diagnostic
scopes/35 observations. The next increment adds typed observed metadata/artifact
sessions: actual factory invocation, cached consumer/component references,
reopen lineage, actual .NET runtime/architecture and independently checked
role-specific assembly/package correspondence. Run
[39940194762](https://github.com/Stonefly-Labs/Hoard/actions/runs/39940194762)
at `457c4e5` verified 114 native checks without skips, thirteen scopes/
38 observations and all six baselines after repairing a diagnostic source-routing
failure. The current increment carries bounded hash-only session observations
through actual VSTest result proofs, binding them to exact case/execution/
attempt/group/input/owner provenance and independent role assignments. Local
regressions pass. Run
[39943968117](https://github.com/Stonefly-Labs/Hoard/actions/runs/39943968117)
at `0687888` verified all 116 native checks without skips, fifteen scopes/
46 discoveries/46 executions and all six baselines. T014/T015 are complete within
their foundation scope. Lock preparation, actual SQLite environment production
and full controller/profile integration remain unfinished.

The T016 preparation entry point now exists as
`bash scripts/validate-conformance.sh --update-locks --evidence <fresh-private-path>`.
It is explicitly non-qualifying: it seals six historical baselines first, builds
the current package graph, and requires a second fresh source/cache/feed locked
replay before publishing only the reviewable conformance locks. Native verification
and the remaining tracked locks are pending; default profile/verify/aggregate CLI
behavior is not implemented yet. The dedicated CI preparation job retains source
locks only, not raw test output or synthetic store data.

The [shared checkpoint](.specify/hoard-flow.json) records the next authorized
stage; constitution and specification artifacts are not product implementation.

## 🚀 Releases are not deployments

Pushing a reviewed `vMAJOR.MINOR.PATCH` or prerelease tag publishes a GitHub
Release with generated notes and GitHub's source archives. It does **not**
build, publish packages/images, provision Azure, or deploy anything.
The Spec Kit flow has standing authorization to publish `v0.0.X-alpha` after
each feature PR merges, where X is the numeric spec-directory prefix (`001`
becomes `1`). It verifies publication at the exact feature merge commit before
recording completion; the completion checkpoint must then merge before starting
the next spec. Previously completed specs are not retroactively released.
See [release governance](docs/RELEASING.md) for the exact process.

## 📚 Project documents

| Document | What it answers |
| --- | --- |
| [Product charter](docs/PRODUCT_CHARTER.md) | Why Hoard exists, scope, and non-goals |
| [Product vision](docs/PRODUCT_VISION.md) | Intended experience and design direction |
| [Product specification](docs/PRODUCT_SPEC.md) | Planned product behavior and constraints |
| [Architecture](docs/ARCHITECTURE.md) | Boundaries, providers, and correctness invariants |
| [Master backlog](docs/HOARD_SPECKIT_MASTER_BACKLOG.md) | Feature prompts, priorities, and dependencies |
| [Constitution](.specify/memory/constitution.md) | Governing principles, compatibility, and quality gates |
| [Development workflow](docs/DEVELOPMENT.md) | Branches, Spec Kit checkpoints, and PR handoff |
| [Azure bootstrap](infra/bootstrap/README.md) | Passwordless deployment identity preparation |
| [Release guide](docs/RELEASING.md) | Tag-driven source releases, separate from CI/CD |

## License

[MIT](LICENSE) © Stonefly Labs. No required SaaS service, proprietary feature
tiers, or cloud dependency for personal use are planned.
