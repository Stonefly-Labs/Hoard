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
their foundation scope. Actual SQLite environment production
and full controller/profile integration remain unfinished.

The T016 preparation entry point now exists as
`bash scripts/validate-conformance.sh --update-locks --evidence <fresh-private-path>`.
It is explicitly non-qualifying: it seals six historical baselines first, builds
the current package graph, and requires a second fresh source/cache/feed locked
replay before publishing only the reviewable conformance locks. Native run
[39947737831](https://github.com/Stonefly-Labs/Hoard/actions/runs/39947737831)
at `585970d` verified identical bytes for all 18 packages and 13 locks across both
fresh builds. The reviewed inventory adds seven locks and updates only local-archive
hashes in three existing F-07 variants; all dependency graphs and 20 third-party
identities are unchanged. T016 is complete; default profile/verify/aggregate CLI
behavior is not implemented yet. The dedicated CI preparation job retains source
locks only, not raw test output or synthetic store data.
The initial native preparation failed safely on a missing embedded F-04 OpenAPI
contract (`CS1566`); a red snapshot regression confirmed the omission. That exact
compiled resource is now included in source fingerprints/snapshots; the repaired
native replay passed.

The T017 foundation admits exact profile/catalog selectors, mutually
exclusive preparation/verification/aggregation requests, explicit category project
paths and fresh private evidence destinations. `--help` describes the current
boundary. Only preparation executes; admitted runtime/verify/aggregate requests
currently return sanitized `Incomplete`/`EvidenceIncomplete`, exit `2`, without
creating an evidence root. They do not fall back to a different profile or qualify
from an optimistic report. Native run
[39949986671](https://github.com/Stonefly-Labs/Hoard/actions/runs/39949986671)
verified the real CLI-to-preparation route and both fresh locked-build graphs.
T017/T018 complete the foundation gate only; profile implementations and the
independent evaluator remain mandatory later tasks, not delivered behavior.

Initial T019/T020 guards now compare the compiled SDK catalog against the frozen
192-entry inventory, including every parameter/control and the 13 exclusions.
Safe discovery challenges reject missing/altered metadata rows, foreign artifact
provider rows and shortened owned manifests. These are pre-extraction regression
guards, not execution of shared assertions against the four adapters; T019/T020
remain open for their complete extraction tests.

Native run [39953736120](https://github.com/Stonefly-Labs/Hoard/actions/runs/39953736120)
verified those guards: 127 foundation checks without failures/errors/skips,
seventeen scopes/69 discoveries/69 executions, all six historical baselines and
byte-identical replay of eighteen packages/thirteen locks.

The SDK now contains fifty-three executable metadata consumers: entity round trips,
registry/authorization isolation, graph deletion, reference replacement/ABA,
telemetry rollback, aggregate bounds, all seven page queries and oversized/
bounded paging, competing creates, revision/delete-recreate races and lease
fences, exact canonical text, opaque continuation scope/epoch binding, exact
ticket expiry and clock rollback, fourteen receipt-corruption shapes, page/group
corruption and all five query-dimension corruptions, atomic/grouped snapshots,
faulted candidates, lost acknowledgments, distinct contribution replay,
writer-contention uncertainty, publication evidence/protection and replay
without authority reacquisition, lease-generation overflow/final-decision expiry,
writer deadlines, cancellation decisions, queue bounds, disposal ownership and
known exception classification, storage/ledger capacity, explicit admission,
invalid budgets, incomplete cleanup, sanitized diagnostics and explicit schema
upgrade/rejection with unchanged-state and reopen checks, and malformed
continuation components with exact valid resume. They
accept public store/authority contracts, a harness-owned clock or typed boundary/corruption
control where needed and cancellation; expected outcomes stay in the SDK.
A focused source probe executes all fifty-three
against unchanged Memory source, and a contradictory-success store fails the
competing-create assertion. This is partial extraction: existing
wrappers, full shared suites and complete typed adapters remain outstanding.
Native run [40059814134](https://github.com/Stonefly-Labs/Hoard/actions/runs/40059814134)
verified all fifty-three against the actual Memory package, plus explicit legacy
factory/genuine settlement prerequisites: all three jobs passed, with
131 foundation checks and 34 scopes/150 exact observations. No category/profile
qualification is claimed.
Observed metadata factories now expose explicit legacy-session setup without
case-ID routing, and Memory exposes its genuine pending-work task separately
from bounded settlement observers. The first concrete Memory adapter now has
explicit current/legacy factories, typed controls, atomic logical reopen and
actual-work ownership integration; its 20 focused adapter rows also passed in
native run [40061416909](https://github.com/Stonefly-Labs/Hoard/actions/runs/40061416909):
all three jobs, 131 foundation checks and 37 scopes/170 exact observations.
The initial SQLite binding now adds explicit current/legacy factories, actual
same-database reopen with exclusive directory handoff, verified backup-based
upgrade authorization and typed raw-state controls. The package-only graph
passes 179 selected checks across Memory and SQLite, including native storage
types, cancellation/late cleanup and real 30-second incomplete cleanup.
These are focused local package checks, not complete category, Linux-supervisor
or profile qualification. An owned SQLite environment probe captures actual
PRAGMAs/native version and verifies the loaded library against locked archive
bytes. Native run [40066075996](https://github.com/Stonefly-Labs/Hoard/actions/runs/40066075996)
passed all three jobs, 134 foundation checks without skips and 50 scopes/254 exact
observations, including all 84 SQLite identities and actual SQLite 3.53.3 loading.
All SQLite cases require actual environment and native-runtime admission.
Native run [40067365972](https://github.com/Stonefly-Labs/Hoard/actions/runs/40067365972)
at `7530cad` also verified the isolated, controller-owned native non-cooperation
child: 136 foundation checks without skips, the same 50 scopes/254 observations,
and matching producer/containment receipts. The five-minute native stall never
runs inside the test process, and retention is not release.
All 53 current shared logical metadata assertion methods now execute through
the SQLite binding too. These local checks are not the catalog's 179 applicable
category results or proof of complete frozen-wrapper parity.
Twenty-two original wrappers across MP-01..13/23..27/31 now delegate to
the same packaged SDK
assertions without changing their frozen names or original fixture lifecycle.
The package-only predecessor suite passes all 72 tests against each actual
provider. Its preparation includes eight archives; this is separate from the
seven-archive binding diagnostic. The next ten delegates pass all 21 affected
tests against each provider. Five further control-dependent wrappers now share
atomicity/publication consumers through scoped observation registration.
Unregistering a hook neither removes a newer owner nor settles an active
callback. Full wrapper extraction/parity is unfinished.
The shared schema-exclusion consumer now preserves the original SQLite U1
writer-held boundary through a distinct `SchemaCandidatePrepared` observation;
the existing pre-transaction U0 hook is unchanged. A real second connection
must observe SQLite BUSY (5). Focused final-package checks pass 180 binding/SDK
tests and 11 original schema/observer tests per provider, without skips.
Native run [40070802352](https://github.com/Stonefly-Labs/Hoard/actions/runs/40070802352)
at `3bca09c` verified the expanded 50-scope/255-observation vector, including
the writer-held regression, native containment and all three successful jobs.
This is not category qualification.
The six original malformed-continuation rows now share the SDK corruption
consumer through fixture-private encoding controls (23 delegated methods).
An actual-cursor parity check proves every original field is covered without
changing unrelated fields; all 79 current predecessor tests pass against each
provider using identical SDK/suite bytes. Full extraction remains unfinished.
Six further admission, capacity and lease-fencing wrappers now share existing
consumers (29 delegated methods). Their 16 affected class tests pass against
each provider; fresh unadmitted stores, original controls and disposal remain
fixture-owned, with no SDK/provider package changes.
Three clock-dependent wrappers now share consumers through callbacks that
drive the original store clock (32 delegated methods). Existing SDK clock
signatures remain available. All 80 predecessor tests pass on each provider,
alongside 180 SDK/binding tests; complete extraction/origin import is unfinished.
Eleven further deadline/reconciliation wrappers now share consumers through
original writer/settlement controls (43 delegated methods). All 81 current
predecessor tests pass on each provider, including real 30-second incomplete
cleanup and cancellation that cannot release another writer's ownership.
Four further corruption wrappers now share consumers (47 delegated methods),
retaining every original corruption parameter. Fixture-owned scopes reject
overlap and closure races, retain failed restoration for recovery and reject
stale replacements without rolling back an intervening commit. Independent
native readers preserve committed-row visibility while a candidate is held.
All 87 current predecessor tests pass on each provider; 181 selected SDK/binding
tests pass locally. Native run
[40097647586](https://github.com/Stonefly-Labs/Hoard/actions/runs/40097647586)
at `84e8a4b` verified 50 scopes/256 observations (86 SQLite identities), native
containment and identical eighteen-package/thirteen-lock replay.
The original diagnostics wrapper now also shares consumers (48 delegated
methods) through an additive overload that retains its original failure hook
and canary. All 88 current predecessor tests pass on each provider and 181
SDK/binding tests pass locally. The native checkpoint predates this diagnostics
increment and does not execute the original wrapper suite.

All five original schema wrappers now also delegate (53 methods total), using
a narrow schema-only projection of their original fixtures, real recovery
authorizations, same-database reopen and actual settlement. SQLite preserves
physical database/WAL byte checks through worker-owned streamed fingerprints;
Memory observes its actual logical image. In-flight stream cancellation now
settles without a false internal-failure diagnostic. All 89 current predecessor
tests pass on each provider and 183 selected SDK/binding tests pass locally.
Fresh independent locked replay reproduces eight archives and exact DLLs.
Native run [40098981184](https://github.com/Stonefly-Labs/Hoard/actions/runs/40098981184)
at `11875e5` verified the preceding diagnostics checkpoint (50 scopes/256
observations). Schema run
[40100325269](https://github.com/Stonefly-Labs/Hoard/actions/runs/40100325269)
at `82a9b09` subsequently verified all 50 scopes/258 observations, including
physical fingerprints and in-flight stream cancellation, with native containment.
Neither native checkpoint executes the original wrapper suite; exact frozen
parity/controller-origin integration and full feature acceptance remain open.

The Linux diagnostic now also builds the actual original metadata test assembly
against its existing seven-package graph and selects all 63 frozen runtime
identities independently for Memory and SQLite. Safe discovery must match before
execution; shortened/renamed scopes and replaced SDK/logger bytes reject.
Native run [40101331484](https://github.com/Stonefly-Labs/Hoard/actions/runs/40101331484)
at `8065dfc` verified all 52 scopes/384 exact discoveries and executions,
including all 63 frozen identities per provider, with actual native containment.
This is diagnostic transport, not category qualification or completed session-
origin/controller integration; the legacy metadata acceptance import remains
unfinished.

Five original artifact publication wrappers now share provider-free SDK
assertions for absence/empty content, real EOF, every expectation, unsupported
requests and fully verified duplicates. Existing helper signatures and the
short-read stream surface remain available to all other wrappers. Actual Local
and ObjectSemantics stores reject a substituted duplicate source at the shared
EOF assertion and pass without that mutation. Fresh eleven-archive locked replay
and 250 non-external-proof artifact tests pass. Seventeen process/transfer-proof
tests still require their actual prepared runners and evidence; this is not
artifact qualification. The legacy artifact preparation/import path, complete
bindings, recovery and large transfers remain unfinished.
The owned Linux diagnostic now requests the original publication assembly too:
all twelve frozen publication parameters plus both source-substitution pairs,
with exact discovery and byte-verified dependencies. Its expanded 53-scope/
398-observation request is pending Linux execution; it does not supply those
missing process/transfer proofs or complete session-origin attribution.
Three more original artifact wrappers now share protected-read/deletion
assertions, preserving borrowed stream ownership, exact receipts, stale
incarnation fencing and held-reader exclusion. The reader is released exactly
once before awaiting deletion, including when an assertion fails. All 37
affected class tests and 250 non-external-proof artifact tests pass, alongside
89 metadata tests per provider and fresh eleven-archive replay. Their six frozen
parameters expand the native request to 54 scopes/404 observations, pending.
Exact receipt/protection and permanent quarantine assertions are now shared
too, retaining Local-only durable reopen checks outside the common SDK.
Both actual validators reject a wrong-receipt mutation through the unchanged
consumer; corrected validators pass. Fresh replay passes 252 non-external-proof
artifact tests. Native
[40105402168](https://github.com/Stonefly-Labs/Hoard/actions/runs/40105402168)
verifies 55 scopes/427 observations, including original evidence/quarantine and
both wrong-receipt mutation parameters, with all three jobs passing.
The preceding publication transport is verified on Linux:
[40103524667](https://github.com/Stonefly-Labs/Hoard/actions/runs/40103524667)
passed all three jobs, including 53 scopes/398 exact observations and actual
original publication/mutation execution; this is not complete category evidence.
The owning controller's observed-barrier stop path and all ten actual SQLite
mutation/upgrade/restore kill/readback rows, plus the real backup/restore
walkthrough, passed on Linux at
[40107305423](https://github.com/Stonefly-Labs/Hoard/actions/runs/40107305423).
All three jobs passed, including 151 foundation checks and 55 scopes/427
observations. This is recovery diagnostic evidence, not complete category proof.
The same parent receipt gate now requests Local B0..B3/D0..D1 crash/readback
rows through the actual artifact runner. Two fresh locked builds reproduce
identical runner bytes and nine dependency images; all six safe-mode local
readbacks pass on macOS. Linux owning-controller execution subsequently passed
at [40107826472](https://github.com/Stonefly-Labs/Hoard/actions/runs/40107826472):
all three jobs, 152 foundation checks, all six Local and ten SQLite rows.
The transfer diagnostic now requests actual paced, generated, non-seekable
256 MiB/4 GiB reads/writes for both artifact providers. Parent-controlled
handshakes bracket independent Linux kernel RSS/high-water measurements and
enforce the 64 MiB incremental peak bound. Two locked builds and all four real
macOS transfer rows pass, including actual `getrusage` peaks. Linux owned
measurement passed all four rows at
[40109299238](https://github.com/Stonefly-Labs/Hoard/actions/runs/40109299238).
The artifact runner now also requests two actual live inspections of retained
source, destination and native workers on both providers before parent-owned
termination. Linux inspection/termination passed all six rows at
[40110165383](https://github.com/Stonefly-Labs/Hoard/actions/runs/40110165383),
with all three jobs, 165 foundation checks and 55 scopes/427 observations.
This is explicitly not durable crash evidence.
The diagnostic now also requests all seventeen original external-proof artifact
wrappers (sixteen frozen identities plus the existing cross-process root-owner
fact) and four bounded child-capture tests. Two fresh-cache locked builds pass
all 21 cases with identical normalized assembly bytes and ten verified dependency
images. Linux execution passed at
[40111391053](https://github.com/Stonefly-Labs/Hoard/actions/runs/40111391053):
all three jobs, 167 foundation checks, 56 scopes/448 exact observations and all
21 external/capture identities. Complete legacy/session/category attribution
remains unfinished.
Current artifact package preparation now builds current metadata plus the shared
SDK, rather than applying today's SDK recipe to pre-F-06 source. Strict private
lock derivations preserve tracked locks and external dependency graphs. Two
fresh-cache locked preparations reproduce eleven archives and verify ten loaded
artifact dependency images; actual functional execution passes all 273 artifact
cases and 89 metadata cases on each provider. This is non-qualifying preparation,
not a rebuild/replacement of sealed historical binaries or full profile evidence.
Three original publication-race methods now forward to shared provider-free
consumers, preserving all six frozen parameters, concurrent admission ordering,
conflicting-length rejection and permanent corrupt-content quarantine. Actual
fixture observers and payload mutation stay outside the SDK. A real-store
forged-length mutation fails the named unchanged consumer on both providers;
the genuine stores pass. Two fresh-cache locked builds reproduce eleven
archives and each pass 275 artifact cases plus 89 metadata cases per provider.
The expanded native request adds those six witnesses and two mutation rows.
It passed at `91da8f4`, run
[40113497329](https://github.com/Stonefly-Labs/Hoard/actions/runs/40113497329):
all three jobs, 169 foundation checks and 57 scopes/456 exact observations.
Private staging and all four original reconciliation methods now also delegate
to shared consumers, retaining their ten frozen parameters and fixture-side
barrier, clock and lost-acknowledgment controls. A real-store foreign-receipt
mutation fails the unchanged receipt-equality assertion on both providers;
genuine stores pass. Run
[40114439905](https://github.com/Stonefly-Labs/Hoard/actions/runs/40114439905)
at `517b911` passed all three jobs, 170 foundation checks and 58 scopes/466
observations, including eight reconciliation witnesses and two mutation rows.
This remains partial implementation, not complete category/profile qualification.
All three original direct/listing visibility bodies also now execute shared
consumers with real fixture-side hold/release controls. A genuine pending Local
commit paired with a premature acknowledgment fails the unchanged shared
pending-task assertion; the genuine store passes. The expanded native request added
three frozen visibility witnesses and that mutation (59 scopes/470 observations) and
passed at `793ad65`, run
[40115175363](https://github.com/Stonefly-Labs/Hoard/actions/runs/40115175363),
with all three jobs, 171 foundations and 59 scopes/470 observations.
Five original history/budget methods now also use shared checks, preserving
eight frozen category witnesses plus eight additional existing fixture cases.
Actual clocks, authority setup and candidate observers remain fixture-side.
Real-store hidden-candidate-failure mutations fail the unchanged shared type
assertion on both providers; genuine stores pass. The next native request adds
all sixteen original rows plus two mutations. It passed at `37ec19a`, run
[40116055015](https://github.com/Stonefly-Labs/Hoard/actions/runs/40116055015):
all three jobs, 172 foundations and 60 scopes/488 observations. Remaining
budget and ownership cases are not claimed complete.
Four cooperative/noncooperative stream-ownership methods now also use shared
checks with all eight frozen parameters and all three stream-helper bodies
preserved. Real-store optimistic-cleanup mutations fail the unchanged retained-
ownership assertion on both providers; actual work settles after real release,
and genuine stores pass. The next ten-row native scope requests
61 scopes/498 observations. It passed at `5974f38`, run
[40116943400](https://github.com/Stonefly-Labs/Hoard/actions/runs/40116943400):
all three jobs, 173 foundations and the exact requested scope, not complete
category/profile acceptance.
Three original cancellation/current-owner bodies now also use shared checks,
retaining two frozen category witnesses plus eight additional existing cases.
A real-store mutation waits for actual rejected-work settlement, then abandons
the current verified owner; the unchanged pending-state assertion fails on
both providers and genuine stores pass. The next twelve-row native scope
requests 62 scopes/510 observations. It passed at `631f9c4`, run
[40118166329](https://github.com/Stonefly-Labs/Hoard/actions/runs/40118166329):
all three jobs and 174 foundations. Full feature acceptance remains unfinished.
Four original result-handoff/expiry bodies now also execute shared checks,
preserving twelve frozen parameters and fixture-side completion/release barriers.
A real reserved ticket deliberately hidden after cancellation fails the
unchanged success assertion; that same actual ticket still publishes, and
genuine stores pass. The next fourteen-row native request is
63 scopes/524 observations, pending, not complete feature acceptance.
The six remaining original budget bodies now also delegate to shared checks,
preserving sixteen frozen parameters for failed cleanup, terminal cancellation,
queue/capacity, authority deadlines and cooperative cancellation. A genuine
input-limit failure deliberately mislabeled as capacity fails the unchanged
code assertion; genuine stores pass. The next eighteen-row native request is
64 scopes/542 observations. It passed at `70dfdf6`, run
[40119412481](https://github.com/Stonefly-Labs/Hoard/actions/runs/40119412481):
all three jobs, 176 foundations and both handoff/budget scopes. Complete
bindings/profiles remain unfinished.
Six original authority bodies now also run shared interface-only checks,
preserving three frozen witnesses, three additional existing facts and the
copied-guard helper. Repairing an actually rejected copied handle into a real
recognized retention fails the unchanged failure-type assertion; the genuine
authority passes. The seven-row native request passed at `7ee1c61`, run
[40120167356](https://github.com/Stonefly-Labs/Hoard/actions/runs/40120167356):
all three jobs, 177 foundations and 65 scopes/549 observations.
Handoff-only run `40118782562` was canceled while pending, not accepted;
later expanded requests include its scope.
Both original capability bodies now also execute shared interface-only checks,
preserving sixteen frozen gap parameters and two additional existing complete-
profile cases. Actual injection, provider creation, filesystem/readiness
observation and private-root cleanup remain fixture-side. The next eighteen-row native
request passed at `2a7be14`, run
[40120937967](https://github.com/Stonefly-Labs/Hoard/actions/runs/40120937967):
all three jobs, 178 foundations and 66 scopes/567 observations, not complete
qualification.
Four original metadata/artifact integration bodies now also run shared checks
on all four SQLite/Memory and Local/ObjectSemantics combinations, preserving
sixteen frozen parameters. Real reference-denial mutations fail the unchanged
expected-code assertion on each combination; genuine stores pass unchanged.
The twenty-row native request passed at `4c87667`, run
[40121897879](https://github.com/Stonefly-Labs/Hoard/actions/runs/40121897879):
all three jobs, 179 foundations and 67 scopes/587 diagnostic observations;
complete typed bindings, category/session imports and feature gates remain open.
Three original metadata-bridge bodies now also run interface-only shared checks,
preserving the frozen mismatched-authority witness and two additional existing
facts. Actual bridge/validator construction, encoding, expiry and ownership
counters remain fixture-side; recognized-reference checks are shared unchanged.
The bridge-only native request was canceled while pending; its three rows are
included in the expanded lifecycle request below, not separately accepted.
These host-bridge unit checks are not complete provider/category qualification.
Three remaining original lifecycle bodies now use shared interface-only checks,
preserving four frozen parameters and two additional composed-shutdown cases.
Actual reference queries, slow guard release, native I/O holds and settlement
remain fixture-side. The six-row native request passed at `f2cc84d`, run
[40123477371](https://github.com/Stonefly-Labs/Hoard/actions/runs/40123477371):
all three jobs, 181 foundations and 69 scopes/596 observations, not complete
bindings/category/profile qualification.
Two original storage-failure/reconciliation bodies now also use shared checks,
preserving four frozen parameters and fixed sanitizer/source behavior. Genuine
access-denied failures mislabeled as unavailable fail the unchanged code
assertion; genuine stores pass. The six-row native request passed at `ff50acd`,
run [40124374635](https://github.com/Stonefly-Labs/Hoard/actions/runs/40124374635):
all three jobs, 182 foundations and 70 scopes/602 observations, not complete
category/profile qualification.
Three original prefix-cleanup bodies now also share six frozen parameters and
their original stop/reopen checks. Actual permissions, observers, filesystem
snapshots and Local-only durable reopen remain fixture-side. The six-row native
request passed at `871e3a8`, run
[40125248164](https://github.com/Stonefly-Labs/Hoard/actions/runs/40125248164):
all three jobs, 183 foundations and 71 scopes/608 observations, not full
qualification.
Both remaining original object-cleanup bodies now also use shared checks with
five frozen parameters. Actual Unix permissions, observers, filesystem sizes
and worker settlement remain fixture-side. The next five-row native request is
72 scopes/613 observations, pending; full binding/category/profile gates remain
open.
Configured publication, compatible reopen and fresh-epoch artifact checks now
also share interface-only consumers. Actual host/DI/mapping/readiness/restart
and missing-guarantee checks remain in the hosting fixture. The next four-row
native request passed at `9ce6b25`, run
[40127065375](https://github.com/Stonefly-Labs/Hoard/actions/runs/40127065375):
all three jobs, 185 foundations and 73 scopes/617 observations, not complete
binding/category/profile qualification.

An opt-in authority shutdown fence now joins recognized/retained guards, queued
admissions and actual retained reference queries before allowing reopen. Local
and Object binding packages compile the same authority source as internal types,
without adding Hosting or the other provider to their dependency closures.
This is an owned-session prerequisite, not a complete binding. Three new shared
checks requested 74 scopes/620 observations. Run `40128473761` failed before
authority discovery because its scope lacked the original-artifact routing
prefix; that transport is corrected, not accepted as a passing run. The
preceding object-cleanup run `40126135553` at `3de87aa` passed all three jobs,
184 foundations and 72 scopes/613 observations, not full qualification.

An explicitly partial owned Local assertion session now supports typed real
observers, compatible reopen and joined provider/authority settlement. Stale
sessions cannot dispose replacements; retries preserve the same actual task and
pending allocator observation, including callback failure. Separate callback
ownership keeps idle/stop honest without changing frozen public result-handoff
or capacity behavior on either artifact provider. Fifteen package-only Local
cases include real native-allocator overlap rejection and concurrent registration
of every typed observer; two common Local/Object checks hold actual release
callbacks through stop. Six further common checks now observe real persisted
receipts, opened-read failure reclamation and verified reconciliation on both
providers, without aliasing Object's distinct transitions to `object.direct`.
Closed supported-point sets bound observer registration, not an arbitrary
sixteen-slot limit.

Native run `40131392286` at `88c5d01` passed 190 foundations and lock replay but
failed before runtime scopes with `ProofMismatch`; it is not admitted. Runtime
input enumeration now hashes consumed managed images, active-architecture
native assets and locks within unchanged bounds, not unrelated copied build
assets; full-tree symlink/type/race checks and default full-manifest limits
remain. Replacement run `40133457888` at exact `c58978e` passed all three jobs,
191 foundations without skips and strict 76-scope/643-observation admission.
The earlier failed run is not retroactively admitted.

Both partial artifact projections now use one internal, provider-free,
source-linked lifecycle coordinator while constructing their own independent
providers. Object logical restart joins the old provider and authority before
admitting an empty private child with a fresh epoch/authority; it is not durable
recovery. Old identity/authority remain immutable, and failed or canceled
replacements remain owned through original-session cleanup. Sixteen Object
package-only cases cover actual observations, publication, restart, callback
failure, stale disposal and allocator retry alongside the fifteen Local cases.
Their exact native transport passed at `36481c0`, run `40134767571`: all three
jobs, 192 foundations without skips and strict 77-scope/659-observation admission.

Typed `ArtifactAssertionOptions` now supplies actual limits and live reference
queries without case-ID setup switches or SDK provider dependencies. Both real
providers enforce configured limits before/after reopen and consult the current
query under their real authority. Missing/unavailable queries remain fail-closed;
timed-out query work stays owned through reopen/final cleanup. Eleven additional
package-only rows cover this setup. Exact `853c669`, run `40136186008`,
passed all three jobs, 193 foundations without skips and strict
78-scope/670-observation admission.

Both partial projections now damage an exact current payload through their own
provider's actual worker supervisor, not untracked binding-side file writes.
The typed damage boundary holds a real native file handle; canceled callers
cannot let reopen/final settlement release that work early. Twenty-three
package-only cases cover real truncation/byte corruption, quarantine, observer
failure, stale sessions/epochs/incarnations, empty payloads and conflicting open
handles. Fresh replay passes all 65 Consumer cases and reproduces fifteen
archives. Payload run `40137341231` at exact `1367a51` passed all three jobs,
194 foundations without skips and strict 79-scope/693-observation admission.
The original damaged-read case now also uses a provider-free consumer with all
four frozen parameters and mechanically identical assertions/order. Actual
capture, damage and restoration stay fixture-side; two genuine-validator
mutation pairs prove the shared check rejects revived corrupt evidence.
Fresh replay passes 308 artifact and 65 Consumer cases. Run `40138438076` at
exact `4a907c5` passed all three jobs, 195 foundations without skips and strict
80-scope/699-observation admission.
The original admitted-open and overlapping read/reconciliation quarantine races
also now use provider-free consumers with identical checks/public-operation
order and original fixture-side barriers. Both fresh preparations pass all
308 artifact and 65 Consumer cases. Run `40139402208` at exact `f05851a`
passed all three jobs, 196 foundations without skips and strict
81-scope/702-observation diagnostic admission.
All six original committed-detection variants now also use one provider-free
consumer with identical checks/order. Their inherited durability expectation
is fixed by the independent test variant, never provider-advertised capability.
Fresh replay passes 308 artifact and 65 Consumer cases; the newest native
run `40140436330` at exact `e089042` passed all three jobs, 197 foundations
without skips and strict 82-scope/708-observation diagnostic admission.
Transitive review found that three earlier extractions omitted the original
Local quarantine stop/reopen check. That complete helper is now shared and
restored in all three paths, with fixture-only construction and identical
lifecycle/assertion order. Three actual reopened-store mutation pairs and a
frozen helper/ownership guard protect it; earlier helper-normalization parity
claims did not establish this durable check. Fresh replay passes 311 artifact
and 65 Consumer cases. Run `40141545447` failed closed with `UnknownDiagnostic`
in the new quarantine scope; it is not admitted. Actual method-level discovery
selected fifteen rows, not its nine-row Local-only declaration. The declaration
now includes every selected parameter, with prelaunch closure protection.
The remaining nine original evidence-validation parameters now also execute
provider-free consumers, preserving failed-persistence retention, real access
faults, permanent quarantine, replacement incarnation and original receipt
checks. Physical controls remain fixture-side. Fresh replay passes 311 artifact
and 65 Consumer cases. Quarantine callers must now explicitly supply their
durable context or select logical-only scope. Native run `40143552793` passed
all three jobs, 200 foundations and 84 scopes/732 observations at `c1d2a6b`,
including the corrected fifteen-row quarantine scope. Six original recovery methods (twelve
Local/Object parameters) now share provider-free cursor, inventory and
generation-fencing assertions. Fixed original variants retain their distinct
enumeration consistency; clock control and driver lifetime stay fixture-side.
Fresh independent replay passes 311 artifact and 65 Consumer cases.
Native run `40144435943` at `ffec99a` passed all three jobs, 201 foundations
and 85 scopes/744 observations.
Five further recovery methods now share admitted-history/generation-race and
progress checks across ten parameters. The unchanged managed barrier body and
its source/barrier lifetime order live in the SDK; physical fault registration
stays fixture-side. Fresh independent replay passes 311 artifact and 65 Consumer
cases. Native run `40145322908` at `9d19bd1` passed all three jobs,
203 foundations and 86 scopes/754 observations.
The remaining object-stop and two real Local-reopen bodies now also use common
checks, preserving retry, exact ownership, 105 retired incarnations, rollback
readback and the borrowed source spanning stop/reopen. Physical permissions,
fresh construction and root-cleanup authorization stay fixture-side.
Fresh independent replay passes 311 artifact and 65 Consumer cases.
Native run `40146117625` at `994f9fb` passed all three jobs, 204 foundations
and 87 scopes/757 observations; full bindings/category/profile acceptance
remains unfinished.
Six original admission methods now share interface-only checks across eleven
identities, retaining actual initialization holds, exclusive create, corrupt
manifest non-reset, fixed Local/Object reopen scope and symlink sentinel checks.
Physical construction, manifest/sentinel I/O and root cleanup stay fixture-side;
native concurrency and cross-process ownership helpers remain unchanged.
Fresh independent replay passes 311 artifact and 65 Consumer cases.
Its native request `40146850203` was canceled before any jobs ran; its scope
is retained in the latest expanded request.
The two remaining deletion methods now also forward all four original parameters
to common checks, preserving uncertain removal, actual reclamation, exact receipt
continuity and live/unavailable reference denial. Fault registration and actual
reference controls stay fixture-side. Fresh independent replay passes 311 artifact
and 65 Consumer cases. Native run `40147381011` at `992b4a5` passed all three
jobs, 206 foundations and 89 scopes/772 exact discoveries/executions, including
the previously canceled admission scope and all prerequisite proofs.
Typed direct-verification observations now cover both new and verified-duplicate
publications on both actual providers, without treating selection as verification
or holding a selected pointer as proof of independent readability.
Fresh independent replay passes 311 artifact and 69 Consumer cases. Native run
`40148199370` at `6d1f73b` passed all three jobs, 207 foundations and
90 scopes/776 exact discoveries/executions with every actual prerequisite.
This is diagnostic evidence, not full qualification.
Scoped capacity injection now throws an actual ENOSPC-shaped exception after
each provider's genuine prefix write. Only that registration's exact injected
exception avoids observer-failure poisoning; ordinary same-code exceptions still
fault final settlement. Four package-only rows prove repeated failure, full
single-ticket capacity restoration, exact reconciliation, stale-scope disposal,
successful publication/readback and genuine successful or faulted settlement.
Fresh package preparations pass 311 artifact, 73 Consumer and 89+89 metadata
cases. Native run `40148998281` at `53b1433` passed all three jobs,
208 foundations and 91 scopes/780 exact discoveries/executions with every
actual prerequisite.
This injects storage failure, not actual disk exhaustion.
Scoped unclaimed-result cleanup injection now retains genuinely indexed
reservation/read handoffs, fences admission/readiness, and reports retained
ownership through a failed stop. Removing the scope permits the real cleanup
retry and actual successful final settlement. Four new package-only rows pass;
fresh replay covers 311 artifact, 77 Consumer and 89+89 metadata cases.
Native run `40149692533` at `1acdeb0` passed all three jobs, 209 foundations
and 92 scopes/784 exact discoveries/executions. This does not
replace physical permission-failure checks or complete mandatory fault drivers.
Owned synchronous holds now use Local's actual record-write and Object's actual
delete callbacks, with deletion reserved before arming and explicit reference
authority. Two package-only rows retain real workers, authority protection and
failed-stop ownership until explicit release, then require actual settlement.
These are controlled synchronous fixture boundaries, not stalled filesystem
syscalls or replacements for the original cross-process containment proof.
Fresh replay covers 311 artifact, 79 Consumer and 89+89 metadata cases;
native run `40150871211` at `f68812e` passed all three jobs, 210 foundations
and 93 scopes/786 exact discoveries/executions, including every prerequisite.
Full Local/Object binding factories now preserve actual provider components and
connect all ten mandatory controls to genuine work. Exact-stamp damage cannot
select a hidden last payload; borrowed source/sink streams remain caller-owned
through actual worker settlement. Twenty-four package-only rows cover the controls,
actual origin capture/reopen, stale fencing and independent concurrent release.
The architecture review's release-lock deadlock was reproduced on both providers
and fixed without changing provider mechanisms or stable settlement promises.
Fresh replay covers 311 artifact, 103 Consumer and 89+89 metadata cases.
Native run `40153251707` at `f73a55a` passed all three jobs, 211 foundations
and 94 scopes/810 exact discoveries/executions with every prerequisite.
Full category/profile qualification and remaining implementation tasks are unfinished.
The full-binding diagnostic now emits 26 actual component origins across those
24 rows, including two genuine reopen lineages. Parent ingestion pins every role
to its independently selected runtime DLL and package; the logger manifest also
admits the four real binding/provider images. Fresh local observation matches all
208 role/image/archive correspondences with an independent runtime cache.
Origin-enabled run `40154183825` at `d1fd43d` passed all three jobs,
212 foundations and 94 scopes/810 exact discoveries/executions with every
prerequisite. These diagnostics do not establish complete category/profile qualification.
Six additional metadata rows now execute unchanged capacity, writer-budget and
publication-protection consumers through observed Memory/SQLite factories.
Their six actual origins match all 36 role/image/archive correspondences; parent
ingestion uses independent binding declarations, actual component images and
archive-bound runsettings, retaining SQLite environment admission. Fresh replay
covers 311 artifact, 109 Consumer and 89+89 metadata cases. The expanded native
request passed as run `40155045988` at `9034153`: all three jobs,
214 foundations and 95 scopes/816 exact discoveries/executions with every
prerequisite. Other origin/profile imports remain open.
Two further metadata rows now corroborate actual compatible reopen with grouped
public readback, preserved epoch/authority and stale-control fencing. The eight
metadata rows produce ten actual origins, including both real child lineages;
Memory uses its closed logical image, not durable restart. Fresh replay covers
311 artifact, 111 Consumer and 89+89 metadata cases. The expanded native request
passed as run `40155922560` at `4548183`: all three jobs, 214 foundations
and 95 scopes/818 exact discoveries/executions with every prerequisite.
Complete category/profile imports remain open.

Twenty further actual metadata rows now import unchanged entity/relationship,
final-graph, independent-candidate, faulted-atomic-candidate, grouped-read and
lease overflow/fence/decision-expiry consumers through both observed factories.
The scope is 28 rows/30 origins/180 actual role/image/archive matches. Fresh
preparation/replay pass 311 artifact, 131 Consumer and 89+89 metadata cases;
its native request passed as run `40156840261` at `2beff54`: all three jobs,
214 foundations and 95 scopes/838 exact discoveries/executions with every prerequisite.
This remains diagnostic work, not complete category/profile qualification.

Thirty further observed rows now import unchanged canonical identity, registry/
authorization isolation, reference replacement/ABA/rollback, create/revision races,
reconciliation and malformed-schema consumers. All 58 metadata rows produce
60 genuine origins/360 actual role/image/archive matches. Fresh preparation/
replay pass 311 artifact, 161 Consumer and 89+89 metadata cases; the next native
request passed as run `40157571215` at `8fed412`: all three jobs,
214 foundations and 95 scopes/868 exact discoveries/executions with every prerequisite. Metadata reference ABA
is not artifact-incarnation/shared-authority qualification.

Eight further observed schema rows execute unchanged upgrade, invalid-upgrade,
upgrade-exclusion and future/corrupt-schema consumers. A transparent recorder
captures the actual factory sessions and every genuine reopen, preserving common
assertions and cleanup ownership. All 66 metadata rows produce 82 origins/
492 actual role/image/archive matches. Fresh preparation/replay pass 311 artifact,
169 Consumer and 89+89 metadata cases; the next native request is
215 foundations and 95 scopes/876 observations, not yet admitted.
Memory upgrades/reopens remain logical, not durable recovery or full qualification.

Forty-two more actual rows import unchanged bounds, paging, clock rollback,
cancellation/queue/exception, ledger/diagnostic, publication, corruption, admission
and disposal consumers. Store-level disposal keeps its outer session owner;
origins are captured while live and emitted only after assertions succeed.
All 108 metadata rows emit 124 origins/744 actual role/image/archive matches.
Fresh preparation/replay pass 311 artifact, 211 Consumer and 89+89 metadata cases;
the next native request is 215 foundations and 95 scopes/918 observations,
not yet admitted or complete category/profile qualification.

Twenty-four further actual rows cover all six continuation-corruption shapes,
the five supported query-dimension corruptions and independent foreign-store
epochs. All 132 metadata rows emit 150 genuine origins/900 role/image/archive
matches; fresh preparation/replay pass 311 artifact, 235 Consumer and 89+89
metadata cases. The next native request is 215 foundations and 95 scopes/942
observations, not yet admitted. Schema run `40158238921` at `9399c3c` passed all
three jobs, 215 foundations without skips and 95 scopes/876 observations with
every prerequisite; it does not verify subsequent controls/cursor increments.

The package-only Consumer now executes 32 exact authority-integration rows
across SQLite/Memory and Local/ObjectSemantics, using the actual evidence bridge
and unchanged common reference, uncertain-outcome, reader, incarnation and
foreign-handle assertions. A separate qualification-close helper joins real
authority holdings, metadata worker settlement and both disposals; the unit
owner alone reclaims its root after successful settlement. Fresh preparation/
replay pass 267 Consumer, 311 artifact and 89+89 metadata cases. This remains
diagnostic, not completed T033/category qualification. Controls run `40158951602`
at `3fb2705` passed all three jobs, 215 foundations without skips and
95 scopes/918 observations; the new native request is 216 foundations and
96 scopes/974 observations, not yet admitted.

The opt-in category-mutation Consumer now exercises stale metadata replay and
premature artifact publication against both independent providers per family.
Four faulty rows fail the named unchanged SDK assertions; four corrected rows
pass the same callers and assertions. Fresh preparation/replay reproduce all
eight outcomes and fourteen actual Hoard image/archive matches. Intentional
failures are absent from ordinary Consumer builds. The next native request is
218 foundations and 100 scopes/982 observations, not yet admitted; T034 and
complete category/profile qualification remain open.

The runtime launcher now separately admits the exact paired scopes for their
own package family; reduced, duplicate and cross-family selections reject
before launch. This repairs a launch guard missed by the earlier selection
mocks; no native mutation result is admitted from the earlier head.

Cursor native run `40159593512` at `5c7522f` passed all three jobs,
215 foundations without skips and 95 scopes/942 exact observations with every
prerequisite. It predates authority integrations and category mutations.

Explicit category input assignments now connect the four frozen catalog slots
to their existing fixture declarations without renaming providers or rewriting
declaration bytes. Category/descriptor/package mismatches and duplicate
declarations reject. Actual factory/reopen observation and independent replay
each verify four cases, eight origins and 56 role/image/archive matches.
This is input wiring, not an executable qualification profile. Authority run
`40160483040` at `eeaa6bf` passed all three jobs, 216 foundations without skips
and 96 scopes/974 exact observations with every prerequisite; it predates
mutations and category-slot input wiring.

Category batch ingestion now requires each binding's complete frozen runtime
inventory, preserves shared execution/proof identities and all 192 inherited
keys, and keeps missing controller/QC proofs incomplete. It is not yet wired
to executable profiles. Native run `40161613939` exposed an `Assert.IsType()`
logger classification gap; the bounded allowlist repair preserves exact SDK
frame checks. Actual logger observation and independent replay now reproduce
four named mutation failures and four corrected passes. That failed run and
superseded canceled run `40162771846` are not admitted native receipts.

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
