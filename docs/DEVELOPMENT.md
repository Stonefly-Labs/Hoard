# Development workflow

## Foundation boundary

The bootstrap established contributor tools and reserved architecture boundaries.
F-01 adds four .NET library projects, immutable provider declarations, explicit
registration, and compile/package/boundary acceptance tooling. F-02 adds
opt-in fixture-tested lifecycle in Hosting. F-03 adds fixture-backed configuration,
owner-scoped local secrets and explicit synthetic conversion through that same
lifecycle. F-04 adds opt-in protected discovery slices in Application and safe
Hosting observations; F-05 adds separate BCL-only metadata operations with
independent SQLite/memory qualification fixtures. F-06 adds separate BCL-only
artifact operations with independent Local/ObjectSemantics qualification fixtures,
shared reference/read/deletion authority and bounded recovery. These remain
test-only, not production storage or F-07 certification. Core remains empty. No caching engine,
production providers, curated executable, UI, product CI/CD,
or deployment exists.
Azure identity provisioning is a
separate, explicitly authorized [operator action](../infra/bootstrap/README.md).

Current technical intent is defined by the [charter](PRODUCT_CHARTER.md),
[product specification](PRODUCT_SPEC.md), [architecture](ARCHITECTURE.md),
and [modular-provider ADR](adr/0001-modular-provider-architecture.md).

## Everyday change flow

```mermaid
flowchart LR
    Branch["Purpose-named branch"] --> Change["Focused change + tests"]
    Change --> Docs["README + affected docs"]
    Docs --> Commit["Commit → push immediately"]
    Commit --> PR["PR to main"]
    PR --> Review["Review + relevant checks"]
    Review --> Merge["Maintainer-authorized merge"]
```

Use `feature/`, `bugfix/`, `chore/`, `docs/`, `refactor/`, `hotfix/`, or `test/`.
Never commit directly to `main`. Inspect the worktree first, preserve user work,
and honor a branch explicitly designated for the task. Do not force-push shared
history. Push after **every** commit; failures are blockers, not successful
handoffs. Open/update the PR when work is ready; do not merge without permission.

Use the [PR template](../.github/pull_request_template.md). Update the README
and affected docs on the branch before merge; explicitly justify unaffected
documents. Describe actual checks and operational/manual steps. Keep credentials,
state, tfvars, plans, build output, and runtime data out of Git; retain lockfiles.

## Local MCP servers

The repository includes `.mcp.json` for Copilot CLI and `.vscode/mcp.json` for
VS Code Copilot. Both describe the same eight servers; keep their definitions
aligned when changing them. These settings apply to this checkout, not your
user-level MCP configuration or a hosted coding agent.

| Server | Connection | Purpose |
| --- | --- | --- |
| [Microsoft Learn](https://learn.microsoft.com/en-us/training/support/mcp) | Remote HTTP | Official .NET, ASP.NET Core, and Microsoft documentation and code samples |
| [Context7](https://context7.com/docs/resources/all-clients) | Remote HTTP | Library-specific documentation and examples |
| [Next.js DevTools](https://github.com/vercel/next-devtools-mcp) | Local stdio via `npx` | Connect to a future Next.js development server for runtime errors, routes, and logs |
| [shadcn](https://ui.shadcn.com/docs/mcp) | Local stdio via `npx` | Discover components, examples, and registry items for the planned console |
| [Playwright](https://github.com/microsoft/playwright-mcp) | Local stdio via `npx` | Browser interaction and accessibility snapshots with an isolated, nonpersistent profile |
| [Azure MCP](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/) | Local stdio via `npx` | Optional Azure resource inspection, with `--read-only` enabled |
| [Docker MCP Gateway](https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/) | Local stdio via `docker` | Connect to the MCP servers enabled in your local Docker MCP Toolkit |
| [NuGet MCP](https://learn.microsoft.com/en-us/nuget/concepts/nuget-mcp-server) | Local stdio via `dnx` | Official NuGet package discovery, upgrade planning, and dependency vulnerability guidance |

The HTTP servers need network access but no local Node installation. Context7
can be used without a key, subject to anonymous rate limits. If authentication
or a higher quota is needed, configure credentials privately in the client;
never add keys or authorization headers to these tracked files. Documentation
queries go to the respective remote service: do not send secrets or private
source code.

The full Node-based stdio setup needs Node.js 22+ (a supported LTS release)
and npm on `PATH`; Azure MCP 3.0.0 requires Node.js 22 or newer. The servers run
publisher packages through `npx -y`, which downloads and runs code in npm's cache
on first start. The `@latest` packages can pick up
updates later. Azure MCP is instead pinned to stable `3.0.0`: at setup time,
its npm `latest` tag pointed to a prerelease. Review and trust the publishers
before starting them. Next.js DevTools and Azure MCP telemetry are disabled in
both configurations. No package manifest, local `node_modules`, or application
scaffolding is required for this MCP setup.

Playwright uses `--isolated`, so cookies and login state are not persisted or
borrowed from your normal browser. It still needs an installed supported
browser; follow its browser-install guidance if a browser launch reports one
missing. Browser automation is not a substitute for committed end-to-end tests.

Azure resource operations require your own authenticated Azure identity, for
example through `az login`, and appropriate least-privilege RBAC. This setup
does not sign in, select a subscription, or provision resources. The read-only
flag prevents write operations; sensitive-data confirmation remains enabled.
Do not remove that restriction or perform an Azure write without separate
authorization. Azure remains optional for local Hoard development.

The Azure entry is named `azure-mcp` to avoid collisions with an existing
`azure` client plugin, which can take precedence over a same-named workspace
entry. Its read-only restriction does not constrain separately installed Azure
servers. If your client already provides Azure or another server listed here,
choose which connection to use in the client to avoid duplicate tools; this
repository does not disable or modify existing plugins.

Docker Gateway requires a running Docker engine and the `docker mcp` CLI
plugin, normally supplied by Docker Desktop with **MCP Toolkit** enabled.
Check availability with `docker mcp version`. Use Docker Desktop's MCP Toolkit
to select and configure the servers you actually need; no catalog servers are
enabled by this repository. The gateway uses your existing local selection,
so avoid enabling duplicate copies of servers already connected directly here.
Credentials belong in Docker's secret storage, not Git. No TCP gateway port,
all-server catalog flag, or relaxed security settings are configured. If Docker
Desktop is stopped, the gateway cannot connect; start it before starting this
MCP entry. This setup does not start Docker Desktop, change its catalog, or run
Hoard containers.

NuGet MCP requires the .NET 10 SDK or later, including `dnx` on `PATH`.
It downloads and runs the official `NuGet.Mcp.Server` package from nuget.org
using the publisher's recommended `--source` and `--yes` arguments. No
prerelease version is requested; an unversioned package name follows stable
updates. Review the publisher before starting the server. No project, package
reference, or tool manifest is created by this configuration. Project-specific
dependency analysis awaits the feature introducing the .NET projects, and any
package changes must remain within the explicitly requested task and normal
client permissions. If `dnx` cannot load the service index, check network and
trusted proxy access to `https://api.nuget.org/v3/index.json` before retrying;
do not disable TLS or certificate validation to make the server start.

For Copilot CLI, start a new session from this checkout, review any workspace
trust prompt, and use `/mcp` to inspect the servers. `copilot mcp list` also
shows the loaded configuration and its source, but does not prove a server
connection. For VS Code, open `.vscode/mcp.json` and use its **Start** actions;
review server trust prompts and use **MCP: List Servers** for status. Existing
client permission and trust controls still apply.

Hoard has no runnable UI yet. Next.js runtime tools require a running Next.js
16+ development server, and project-specific shadcn registry configuration
belongs to the feature that creates `apps/web`. Do not scaffold an app or run
component installation just to enable these servers. The default shadcn registry
does not require a `components.json` file for discovery.

To roll back, remove the server entries from both files and restart or stop
the affected client connections. This does not alter global settings or npm's
download cache. Product specifications and architecture diagrams are unaffected:
MCP is contributor tooling, not a Hoard runtime capability.

## Checkpointed Spec Kit flow

In a Copilot surface supporting repository skills, ask:

> Use the `hoard-speckit` skill to advance the next stage.

In CLI, `/skills` shows available skills. Name `hoard-speckit` explicitly; exact
slash-command spelling can vary by Copilot surface. The entry point is
[its SKILL.md](../.github/skills/hoard-speckit/SKILL.md).

The bootstrap did not run this flow or pre-ratify the constitution. The initial
constitution stage establishes
[version 1.0.0](../.specify/memory/constitution.md), covering product boundaries,
provider composition, shared correctness/security, evidence, accessibility,
operations, and governance. It creates no feature specification or product code.
Templates remain unchanged; the installed stage skills read the constitution
at runtime.

The constitution adoption PR must merge before a new specification begins.
After merge, the next invocation selects the first dependency-ready open
specification from the [master inventory](HOARD_SPECKIT_MASTER_BACKLOG.md)
and passes its exact prompt to the installed specify skill. The tracked
checkpoint, rather than this guide, records current stage and merge progress.

The first generated feature is
[F-01: platform package boundaries and provider contracts](../specs/001-provider-contracts/spec.md).
Its [built-in quality checklist](../specs/001-provider-contracts/checklists/requirements.md)
validates the specification, not implementation or reviewer-owned custom
checklist approval. Package contracts, custom-host compilation, and architecture
checks described there were acceptance requirements at specification time;
their current bounded implementation is described below.
Its initial [clarification review](../specs/001-provider-contracts/spec.md#clarifications)
records a no-question result with no scope changes; a later user-approved
follow-up resolves the checklist review's optional-dependency ambiguity.
Exact public signatures and
build commands were proposed in the
[implementation plan](../specs/001-provider-contracts/plan.md) and
[public contracts](../specs/001-provider-contracts/contracts/public-api.md),
then delivered by the separately authorized implementation stage. The plan
retains historical design alongside current evidence and includes research,
a declaration model,
compatibility/architecture acceptance contracts, and a
[validation quickstart](../specs/001-provider-contracts/quickstart.md).
The implementation now supplies the foundation commands in that quickstart;
they prove compilation and package boundaries, not product behavior.
Planning did not generate or approve custom reviewer-owned checklists, create
tasks, scaffold projects, or authorize implementation. The subsequent checklist
stage generated separate
[architecture](../specs/001-provider-contracts/checklists/architecture.md) and
[compatibility](../specs/001-provider-contracts/checklists/compatibility.md)
requirements-quality reviews: 20 and 18 criteria respectively.
These standard-depth checklists are for maintainers and provider-contract
reviewers before implementation authorization; they assess written requirements,
not product behavior. At the user's explicit request, a delegated review
initially found architecture 20/20 and compatibility 17/18 satisfied.
The user then approved the recommendation for
[RQ-01: incompatible present optional dependencies](../specs/001-provider-contracts/checklists/compatibility.md#rq-01-incompatible-present-optional-dependency).
The spec, declaration model, and policy now classify an enabled incompatible
optional target as an unsupported composition, without automatic disablement
or substitution; installed/registered-but-disabled optional targets are
unavailable and confer no integration/capability claim. Five new classification
examples bring the written matrix to 23 cases. The delegated re-review closes
CHK014: architecture 20/20 and compatibility 18/18, all 38 criteria satisfied
without waivers. The built-in specification checklist and driver are unchanged.
The subsequent [task-generation stage](../specs/001-provider-contracts/tasks.md)
produced 57 unchecked tasks: shared setup/declarations, four story phases, and
cross-cutting acceptance/documentation work. All 17 requirements and six
outcomes are mapped to implementation and focused proof tasks. The dependency
graph serializes the shared validation script while allowing independent
fixture/test/inspector work; architecture negatives and all 23 compatibility
classifications remain future proof obligations. No product scaffolding or
implementation occurred.

The subsequent read-only cross-artifact analysis found no actionable
duplication, ambiguity, underspecification, inconsistency, constitutional
conflict, or coverage gap. All 17 functional requirements and six buildable
outcomes have implementation/proof tasks; all 57 tasks map to requirements or
shared acceptance prerequisites. The prerequisite graph is complete and
acyclic, including serialized shared-script edits. All feature artifacts and
reviewer-owned checklist markers remained unchanged. The analysis report is
recorded in the draft feature PR, with its completion evidence in the shared
checkpoint; no remediation or implementation occurred. The next scheduled
stage was implementation through a separate `hoard-speckit` invocation, with the
existing reviewer-owned 38/38 checklist gate satisfied. Artifact analysis is
not passing product evidence or permission to skip the remaining stages.

The completed implementation stage delivers declaration-only Abstractions,
provider-free Core/Application, and metadata/type registration in Hosting.
The [provider guide](PROVIDERS.md) and
[compile-only custom-host guide](../examples/CustomHost/README.md) describe
current APIs and limits. `bash scripts/validate-foundation.sh` restores/builds
with locks, checks SDK formatting/analyzers, builds Core in isolation, packs
four local platform libraries and five independent fixtures, compiles family
consumers and both hosts, and executes architecture/compatibility/registration
acceptance. The F-01 host is never run. Current solution tests also include
in-process lifecycle regressions; the dedicated lifecycle graph/distribution/
old-binary proof still requires validate-lifecycle.sh. No listener starts.
Every subprocess has a ten-minute timeout.
A Python standard-library helper owns copying, hashes, metadata manifests, and
explicit subprocess errors; Bash owns prerequisites and private-directory cleanup.
Tests consume the prepared evidence, never recursively invoke the orchestrator,
and deliberately fail when evidence is missing.

Default runs do not rewrite lockfiles. After an intentional contract/dependency
change, `bash scripts/validate-foundation.sh --update-locks` regenerates and
replays standalone locks; review and commit them before the default locked run.
Local acceptance packages omit Git revision stamps and normalize source paths,
so fresh temporary locations and checkpoint commits do not invalidate their
content hashes. This is local proof tooling, not release/package publication.
The helper also canonicalizes unsigned local SDK archive envelopes (ZIP
metadata and OPC relationship IDs/paths) without changing nuspec/assembly/core
property bytes. Focused regressions protect reproducibility and reject signed/
external inputs; no published/external package is rewritten and locked hashes
are never bypassed. Compiler/SDK changes affecting payloads need reviewed locks.
SDK package pruning is disabled in the example so its complete explicit packed
dependency graph remains available for inspection even with ASP.NET's shared
framework. Framework ownership comes from resolved reference-pack metadata,
not trusted namespace/name prefixes.
The implemented-graph architecture review identified three proof gaps, now
corrected with focused regressions: unused framework references create real
dependency edges, prohibited BCL query/connection/transaction shapes cannot
bypass public-surface checks, and all eight named platform/provider/host scans
are mandatory. See the [review and measured evidence](../specs/001-provider-contracts/plan.md#necessary-implementation-details-and-review).
The support-claim audit is complete. The subsequent installed convergence stage
assessed all 17 functional requirements, six buildable success criteria, 15
story acceptance scenarios, nine edge cases, 12 grouped plan decisions, all 57
implementation tasks, and eight constitutional principles against current
scoped code. It found one HIGH-severity partial gap: the graph inspector rejected
the permitted `Identity -> Hosting -> Core` closure under ARCH-008, although
identity providers may use the approved Hosting API and Hosting references Core.
A temporary diagnostic invoking the current compiled graph inspector reproduced
that false rejection; the original permitted fixtures did not cover this path.
[Phase 8 / T058](../specs/001-provider-contracts/tasks.md#phase-8-convergence)
recorded the correction and regression work. That convergence invocation
appended only the new task section; its passing baseline of 81 .NET tests
and 17 tooling tests did not resolve the uncovered path.

The separately authorized T058 implementation now tracks Identity paths whose
first edge reaches Hosting separately from other paths to the same dependency.
Core is permitted through that approved Hosting composition, not directly or
through an unrelated SDK-owned helper. A package-only fixture uses the actual
Hosting registration API; isolated negatives retain both forbidden routes even
when Hosting is also referenced, with normal/reversed edge-order checks.
All four new fixture projects carry locks. No platform API, provider package,
runtime behavior, or reviewer-owned checklist changed. See the
[follow-up evidence](../specs/001-provider-contracts/plan.md#t058-implementation-follow-up-2026-10-20).
The separately authorized follow-up convergence assessment found no actionable
gaps: missing 0, partial 0, contradicts 0, unrequested 0, with zero findings at
any severity. It checked all 17 functional requirements, six buildable success
criteria, 15 story acceptance scenarios, nine edge cases, 12 grouped plan
decisions, all 58 tasks (including T058), and eight constitutional principles.
Fresh default locked acceptance passed all 86 .NET tests (42 foundation,
41 architecture, three composition), zero failed/skipped, including the
permitted Identity/Hosting path and both forbidden alternatives. All 17 Python
tooling tests passed. The assessment left the spec, plan, tasks, and all
reviewer-owned/built-in checklist bytes unchanged; no empty convergence phase
or further implementation task was added. Its report is recorded in the draft
feature PR and shared checkpoint.
The separately authorized
[finalization acceptance](../specs/001-provider-contracts/plan.md#finalization-acceptance-2026-10-20)
repeated the full locked foundation check and all 17 tooling tests, refreshed
the dependency advisory assessment with no known vulnerable packages, and
verified the acceptance traceability, documentation, and existing architecture
reviews. The reviewed implementation, locks, tasks, and checklist markers
remain unchanged. At finalization,
[PR #4](https://github.com/Stonefly-Labs/Hoard/pull/4) was ready for maintainer
review, targeting `main`; the shared checkpoint recorded `await_merge` with
that PR number and no completed feature.

PR #4 subsequently merged into `main` on 2026-10-20 at
`837fdf3edf51c3df34710184d018479683c194c2`. The separate `await_merge` stage
verified the GitHub merge state, merge ancestry in fetched `origin/main`, and
all 58 completed tasks. It created `chore/spec-progress-f-01` from that main
and records F-01 in the shared checkpoint's completed entries, retaining its
directory, PR, and merge commit. At that point the checkpoint had no active
feature and scheduled `specify`; the first dependency-ready entry was
[F-02: module registry, composition and lifecycle](HOARD_SPECKIT_MASTER_BACKLOG.md#foundation-f-02).
The progress checkpoint merged through
[PR #5](https://github.com/Stonefly-Labs/Hoard/pull/5), satisfying the gate for
the subsequent specification stage.

[F-02: module registry, composition and lifecycle](../specs/002-module-lifecycle/spec.md)
now has its own requirements at `specs/002-module-lifecycle`, on
`feature/002-module-lifecycle`. Five prioritized stories, 22 functional
requirements, and seven measurable outcomes cover explicit registered-module
selection, pre-activation dependency/compatibility checks, deterministic ordering,
disabled-route/worker/connection isolation, readiness, bounded initialization,
partial-start cleanup and shutdown, sanitized diagnostics, and restart versus
custom rebuild behavior. The existing F-01 optional-dependency policy is
preserved: absent/disabled optional targets confer no integration; enabled
incompatible targets fail composition. All explicitly enabled modules must
initialize successfully; optional dependency does not mean degraded startup.
The [built-in requirements checklist](../specs/002-module-lifecycle/checklists/requirements.md)
passes all 16 specification-quality criteria, with no unresolved clarification
markers. It is not a custom reviewer-owned approval or runtime acceptance
result. The bounded architecture review found no actionable requirement-level
findings; its operational proof obligations remain future work.

The subsequent
[clarification review](../specs/002-module-lifecycle/spec.md#clarifications)
found no critical ambiguities across all ten review categories. Zero questions
were asked or answered, and no requirements, acceptance criteria, or scope
decisions changed. The built-in specification-quality checklist was revalidated
at 16/16 to 16/16: no newly passing items, regressions, or unchecked items.
Its bytes and historical specification-stage notes remain unchanged; no custom
reviewer-owned approval is implied. Exact lifecycle APIs and state
representation, route-conflict inspection, finite budget defaults, and the stable
ordering tie-break remain planning decisions under the existing requirements.
No consequential product decision blocks planning.

The subsequent [implementation plan](../specs/002-module-lifecycle/plan.md)
defines opt-in Hosting lifecycle adapters on F-01's unchanged registration
boundary. Persistence/artifact providers retain Abstractions-only dependencies
through host-side adapters. Metadata validation precedes all construction;
enabled modules follow deterministic dependency ordering, service composition,
supervised host build, owned-route analysis, initialization and complete
readiness before traffic/worker admission. Startup/stop coordination has finite
deadlines and reports incomplete cleanup rather than pretending cancellation
forcibly stops trusted in-process code.

The [research](../specs/002-module-lifecycle/research.md),
[in-memory model](../specs/002-module-lifecycle/data-model.md),
[public API](../specs/002-module-lifecycle/contracts/public-api.md),
[lifecycle](../specs/002-module-lifecycle/contracts/lifecycle.md) and
[acceptance](../specs/002-module-lifecycle/contracts/acceptance.md) contracts
resolve planning details and map all 22 requirements, seven outcomes and
20 story scenarios to 40 fixture-only proof cases. The restricted owned-route
language rejects unsupported shapes instead of claiming to analyze arbitrary
constraints. The bounded architecture review identified a missing build
supervision boundary and two resource/worker semantics questions; the plan
corrects all three with an explicit supervised build API, retained request/
dependency resource leases and protected root disposal after drain timeout,
and whole-callback worker admission. LC-20/23/26/29 retain those proof duties.
No runtime results or repeat approval are inferred from those design corrections.

The [validation quickstart](../specs/002-module-lifecycle/quickstart.md)
distinguishes current foundation/tooling commands from a proposed lifecycle
validation script, independent packed fixtures and a separate lifecycle-only
host example. Neither that script nor new runtime APIs/projects/dependencies
are created in planning. F-01's compile-only example and all checklists remain
unchanged. The ASP.NET Core shared-framework/versioning dependency impact,
source/binary registration compatibility, deadline/admission/cleanup behavior
and actual package graph still require implementation evidence.

The subsequent checklist stage generated
[composition](../specs/002-module-lifecycle/checklists/composition.md) and
[lifecycle](../specs/002-module-lifecycle/checklists/lifecycle.md)
requirements-quality reviews: 20 criteria each, all 40 unchecked and
reviewer-owned. Standard-depth scope and audience are explicit: maintainer and
provider PR review before implementation authorization. Composition covers
registry/selection, compatibility/dependencies/capabilities, route ownership,
unchanged registration compatibility, and bundled/custom restart journeys.
Lifecycle covers disabled isolation, admission/readiness, finite coordination
budgets, partial-start and normal cleanup, pending-resource protection,
concurrency, and sanitized actionable diagnostics. The planning review's build,
resource-retention, and worker-admission corrections remain written proof
obligations; checklist generation neither evaluates them nor supplies runtime
evidence. Requirements/design artifacts and the built-in 16/16 checklist remain
unchanged; no custom criterion is approved or waived.

The subsequent [task-generation stage](../specs/002-module-lifecycle/tasks.md)
produced 72 unchecked implementation tasks across eight phases: shared setup
and safety primitives (13), US1 selection/start (14), US2 enabled/ready
functionality (18), US3 failure/stop (10), US4 safe diagnostics/state (5),
US5 distribution/restart (7), and cross-cutting acceptance (5).
All 22 functional requirements, seven outcomes and 40 LC acceptance cases
have implementation and focused proof assignments; all 20 story scenarios
retain the acceptance contract's LC mapping. Explicit acyclic prerequisites
serialize shared coordinator/lease/route/tooling edits, while 29 marked tasks
identify scoped file-disjoint parallel opportunities after their prerequisites.
The endpoint-free US1 fixture proof is the first bounded increment, not a
shippable lifecycle or complete F-02.

Tasks retain supervised synchronous build, single disposal ownership, pending
request/response/worker/build protection, finite deadlines and once-only
cleanup as implementation/regression obligations. Independent fixture packages,
package-only host variants, retained old registration binaries, explicit
framework-reference impact, initial reviewed locks and fresh default locked
replay remain required evidence. Existing F-01 fixture/example sources and
compile-only scenarios must stay intact; reviewed Hosting dependency/content
changes may require affected lock refreshes, not silent hash bypasses.
No test may skip a missing package input or accept an empty proof selection.
The task-generation stage did not perform cross-artifact analysis, implement
these obligations or evaluate the custom checklists; all 40 remained unchecked
at that stage.

The subsequent installed read-only cross-artifact analysis found no actionable
duplication, ambiguity, underspecification, inconsistency, constitutional conflict
or coverage gap. All 22 functional requirements and seven buildable outcomes
have implementation and focused proof assignments; all 72 tasks map to those
requirements or shared acceptance prerequisites. The complete prerequisite graph
is acyclic, including serialized shared-file edits; 40 LC cases, 20 story
scenarios and 12 edge cases retain their proof obligations. T002's tooling
regressions and T006's composition inputs are mapped shared prerequisites,
not orphan tasks. The analysis report is recorded in the draft feature PR,
with completion evidence in the shared checkpoint. No feature artifact or
built-in/custom checklist byte changed, and no remediation was needed.

The later explicitly requested checklist review evaluated all 40 custom
criteria at baseline `c7ccde4`: composition 19/20 and lifecycle 19/20, 38/40
satisfied without waivers. Composition CHK014 was left open for
[RQ-02: inconsistent baseline/custom artifact manifests](../specs/002-module-lifecycle/checklists/composition.md#rq-02-baseline-and-custom-artifact-package-lists-disagree).
Lifecycle CHK013 was left open for
[RQ-01: timed-out cleanup callback retention](../specs/002-module-lifecycle/checklists/lifecycle.md#rq-01-explicitly-retain-resources-for-timed-out-cleanup-callbacks).
Both were MEDIUM written-requirements/documentation findings, not demonstrated
runtime defects. The initial review changed checklist markers only, not
spec/design/tasks or the driver checkpoint.

The user subsequently approved both recommendations. The follow-up explicitly
tracks a non-completed StopAsync as pending Phase activity even after its wait
times out: owner/prerequisite/root resources remain protected, independent safe
cleanup shares the original deadline, and late completion after the bounded
result cannot rewrite outcomes, retry or trigger deferred disposal. LC-28/29
and T048/T050..T053/T055 retain the A -> B plus independent C regression duty.
The baseline manifest now consistently includes the two protocols, Metadata,
Artifact.One and optional Identity; only custom adds Artifact.Two and its host
adapter. LC-35/36, T065 and the quickstart require baseline absence and
same-binary bundled protocol switching; independent packing still covers six
fixtures. All 40 custom criteria are now satisfied without waivers after
re-evaluation; the built-in checklist remains 16/16.

Fresh installed read-only cross-artifact analysis found zero actionable
findings, with all 22 requirements/seven outcomes, 72 unchecked tasks, 40 LC
cases, 20 scenarios and 12 edge cases retaining complete proof mappings and
acyclic prerequisites. All feature bytes remained unchanged during that
analysis. The bounded follow-up architecture review also found no actionable
findings or unresolved design questions; actual runtime/package/graph proof
remains an implementation obligation. The PR records both results.
The approved follow-up is not a driver stage, independent human inspection,
runtime implementation or acceptance. The checkpoint/history is byte-for-byte
unchanged; no `begin`/`finish` or progress reset was used.

Specification, clarification, planning, checklist and task generation create no
lifecycle implementation, production executable/provider, configuration parser,
management discovery endpoint, UI, or conformance certification. F-02 can
later prove lifecycle with explicit selections and instrumented fixtures;
F-03 retains configuration sources,
option/secret handling, and operator selection UX, while F-04 retains management
discovery. Read-only analysis likewise supplies no runtime implementation or
passing product evidence. The next scheduled stage was `implement` through a
separate invocation, with the custom checklist gate now satisfied and the
approved findings resolved. This follow-up does not start implementation or
mark any of its 72 tasks complete. Do not reset the checkpoint to fabricate a
scheduled analysis rerun or infer runtime acceptance from `implement` / `ready`.
Task generation and analysis do not require custom checklist approval, but the
later implementation gate does require reviewer approval or explicit reviewer
authorization; their initial generation/analysis did not supply it. The
requested review and approved follow-up now satisfy that requirements gate,
not a feature-completion or runtime-support claim.

### Implemented F-02 lifecycle boundary

The separately authorized implementation adds metadata-only registry/selection/
version/capability validation, deterministic dependency ordering, inert opt-in
adapter association, supervised service/build/route/init phases, readiness,
worker/request admission and bounded reverse cleanup in Hosting. Abstractions,
Core and Application source stay unchanged. F-03 must feed the same validator;
F-04 still owns authorized discovery/UI, not an automatically exposed health
endpoint.

```bash
bash scripts/validate-lifecycle.sh
```

This separate ten-minute-per-subprocess orchestrator packs six independent
fixtures, verifies private-feed/hash/lock provenance, runs TestServer's seven
baseline/custom distribution journeys, retains/runs an old registration binary,
and inspects ten exact project/packed/transitive/API graphs. Source-only filters,
`--packages-only` and `--journeys-only` explicitly report partial proof.
Intentional payload changes use `--update-locks`, reviewed locks and an
independent default replay. The existing foundation command retains its eight
mandatory real scans and original compile-only fixture/example sources. It
excludes only LC-38's separate prepared lifecycle manifest test; lifecycle
acceptance supplies that mandatory proof.

Hosting now propagates the ASP.NET Core shared-framework prerequisite even to
non-web registration-only consumers. Old AddHoard/AddModule APIs remain inert
and source/binary-compatible. NuGet.Versioning is internal; TestHost is test-only
and never classified as verified shared-framework provenance. See
[measured evidence and implementation adjustments](../specs/002-module-lifecycle/plan.md#implementation-evidence).

The [provider guide](PROVIDERS.md#opt-in-lifecycle) and
[example](../examples/LifecycleHost/README.md) document actual APIs and limits.
Use normal app StartAsync, explicit StopHoardApplicationAsync(lease), and sole
external lease disposal. Module-only stop can report NotAttemptedOwnerPending;
only the final lease StopResult reports root release. Shared framework stop,
synchronous notification callbacks, cancellation/deregistration, outstanding
responses/workers and non-cooperative callbacks remain supervised. A bounded
wait is not forced termination: incomplete resources may require process exit.
Later health loss changes readiness only; stop/fault closes admission.

The subsequent installed convergence assessment checked all 22 functional
requirements, seven buildable outcomes, 20 story scenarios, 12 edge cases,
12 grouped plan decisions, all 72 implementation tasks and eight constitutional
principles against current scoped code. It found one **CRITICAL** contradiction
of bounded coordination: the worker-fault branch calls
`IHostApplicationLifetime.StopApplication()` while holding the coordinator's
state lock. Synchronous `ApplicationStopping` callbacks can therefore block
stop coordination and safe state inspection indefinitely.

An isolated public-API/TestServer diagnostic held such a callback after worker
failure: neither stop nor snapshot access completed after 1,001 ms despite a
200 ms shutdown budget. The diagnostic released and observed its pending work.
Fresh default locked lifecycle acceptance passed 126 source tests, nine boundary
proofs and seven package-only journeys; foundation passed 220 .NET tests and
tooling passed 22 tests. Those passing suites do not cover the reproduced
notification path or establish compliance for it.

[Phase 9 / T073](../specs/002-module-lifecycle/tasks.md#phase-9-convergence)
appends the required lock-free supervised notification, resource-retention and
deterministic regression/review work. The existing task prefix, spec, plan and
all built-in/custom checklist bytes remain unchanged. No application code was
modified by convergence. README and this guide record the blocker; provider/
example/quickstart contracts, product intent, diagrams, governance, IaC and
release guides are unaffected because no API, intended behavior, dependency or
operational action changed. Existing implementation evidence remains historical,
not proof of the newly uncovered path.

The separately authorized
[T073 implementation follow-up](../specs/002-module-lifecycle/plan.md#t073-implementation-follow-up)
now records the worker failure and stop latch atomically, registers global
pending Phase activity before drain scheduling, and dispatches host lifetime
resolution/notification outside the state lock. Pending notification or
cancellation protects every module and the root. The existing tracker,
cleanup planner and sole composition owner provide that retention without new
APIs, dependencies or a second shutdown path.

Barrier/virtual-time regressions prove responsive snapshots, a 200 ms original
shutdown deadline, unsafe incomplete cleanup while a notification/cancellation
is held, frozen repeated results and no deferred cleanup after release.
The cooperative counterpart proves once-only notification, module cleanup and
root disposal. The bounded implementation architecture review found no
actionable findings; its static review and runtime proof limits are recorded
in the plan. A full run exposed a test synchronization race: the independent
cleanup proof must await harmless global cancellation quiescence before
advancing its virtual drain timer. That test now does so without weakening
resource-retention assertions.

The subsequent fresh convergence assessment checked all 22 functional
requirements, seven buildable outcomes, 20 story scenarios, 12 edge cases,
12 grouped plan decisions, all 73 existing tasks and eight constitutional
principles. T073's lock-free notification, original deadline and pending-resource
protection are implemented. One **HIGH partial** diagnostics gap was found:
`StopCoreAsync` and `CancelPending` pass cancellation tasks to `Observe`
without an owner, so callback exceptions are consumed without any diagnostic.
An isolated public-API diagnostic registered a throwing worker stop-token
callback. It executed once; both module cleanups completed and final lease
release was complete, but module/final/snapshot diagnostics were all empty.
Actual resource release does not excuse omission of the cancellation failure.

[Phase 10 / T074](../specs/002-module-lifecycle/tasks.md#phase-10-convergence)
appends safe cancellation-failure reporting and focused throwing/cooperative/
late-fault regression work. Existing task bytes, spec, plan and all checklist
markers remain unchanged. Fresh `bash scripts/validate-lifecycle.sh` passed
129 source tests, nine boundary proofs and seven package-only journeys, including
retained old-binary/new-source/framework proof. Fresh
`bash scripts/validate-foundation.sh` passed 223 tests (42 foundation,
49 architecture, 132 composition), zero failed/skipped, with all original
eight scans retained. The tooling suite passed all 22 tests. Those suites
do not exercise the newly reproduced cancellation-error path.

The separately authorized
[T074 implementation follow-up](../specs/002-module-lifecycle/plan.md#t074-implementation-follow-up)
now uses one off-lock cancellation supervisor for lifetime, readiness timeout
and cleanup timeout. Callback faults generate safe additional
`CancellationFailure` diagnostics with owner, originating phase, fixed action
and lifecycle correlation before their tracked activity is released. The
primary worker/startup/timeout finding remains separate. A completed fault does
not falsely retain resources: cooperative work can still finish cleanup and
root disposal, with the cancellation error reported.

Held late-fault proof retains every module/root for lifetime cancellation under
the original shutdown deadline. After bounded stop/disposal, releasing the
callback adds one safe diagnostic to a later snapshot, not to frozen results;
no cleanup retry or deferred disposal occurs. Throwing/cooperative timeout
counterparts cover readiness and module cleanup, including known errors before
result publication and zero seeded payloads in normal results/logs. The bounded
implementation architecture review found no actionable findings; measured
red/green, packed locks and complete acceptance evidence are in the plan.

That implementation checkpoint schedules fresh `converge`. README,
provider/example guides, quickstart, lifecycle
contract/model and implementation evidence document the correction. Spec,
public API/acceptance contracts and reviewer-owned checklists are unchanged.
Product intent, baseline diagrams/ADR, governance, master backlog, F-01
sources/examples, IaC and release guidance are unaffected: existing diagnostic
and resource invariants are restored without new APIs, dependencies, provider
capabilities, permissions or operational actions.

The subsequent installed convergence assessment checked all 22 functional
requirements, seven buildable outcomes, 20 story scenarios, 12 edge cases,
12 grouped plan decisions, all 74 existing tasks and eight constitutional
principles. T074's cancellation-failure reporting is implemented. One **HIGH
partial** gap remains in eventual-fault observation:
`HoardLifecycleCoordinator.Observe` reports only when given an owner and the
shared stop task has already completed. Readiness supplies no owner; timed-out
cleanup faults before stop completes also receive no safe diagnostic.

Two isolated public-API probes reproduced those omissions without a listener
or repository source changes. A readiness callback faulted after the bounded
assessment returned not ready: later snapshots and final diagnostics retained
only Timeout/NotReady. A protocol cleanup faulted after its callback timeout
while independent metadata cleanup held the shared stop open: final diagnostics
contained only Timeout. All three cleanup callbacks ran once, the protocol's
outcome stayed TimedOut, the remaining module cleanups and root disposal
completed, and no seeded payload appeared in snapshots. The diagnostic used
real-time budgets and a 200 ms observer grace; deterministic barrier/virtual-time
regressions belong to the implementation follow-up, not this assessment.

[Phase 11 / T075](../specs/002-module-lifecycle/tasks.md#phase-11-convergence)
appends once-only owner-aware eventual-fault reporting and its focused proof.
The task also requires auditing existing supervised startup/readiness/cleanup
and framework-stop/root-disposal observers for the same timing/ownership
omission, without claiming those additional paths were dynamically reproduced.
Normal awaited failures must not become duplicate diagnostics; eventual faults
must not rewrite results, retry cleanup or trigger deferred disposal.

Fresh `bash scripts/validate-lifecycle.sh` passed 136 source tests, nine boundary
proofs and seven package-only journeys, with six independent packages and
retained old-binary/new-source/shared-framework proof. Fresh
`bash scripts/validate-foundation.sh` passed 230 tests (42 foundation,
49 architecture, 139 composition), zero failed/skipped, retaining the original
eight scans. The tooling suite passed 22 tests. Those passing baselines do not
exercise the newly reproduced omissions and do not resolve F1.

Only the new Phase 11/T075 section was appended to tasks; all previous task
bytes, spec, plan and built-in/custom checklists remain unchanged. No
implementation or checklist approval occurred. README and this guide record
the blocker; provider/example/quickstart contracts, product intent, diagrams,
governance, F-01 sources/examples, IaC and release guidance are unaffected
because no API, intended behavior, dependency or operational action changed.
The next separately authorized stage is `implement` for T075, followed by fresh
convergence. Keep PR #6 draft: finalization, merge, feature completion and
dependency availability remain separate gates.

The separately authorized
[T075 implementation follow-up](../specs/002-module-lifecycle/plan.md#t075-implementation-follow-up)
now binds fault observation to each supervised callback's owner and originating
phase. Safe normal failures or additional `LateCallbackFailure` diagnostics
are recorded inside tracked activity before release, not in a continuation
conditioned on terminal stop. Startup, readiness, cleanup, framework stop and
root disposal share the mechanism; directly awaited faults are not duplicated,
and cooperative cancellation does not become a new eventual fault. Known
errors can appear in the shared stop result; faults after bounded results
appear only in later snapshots, without outcome changes, retry or deferred
disposal. T074 cancellation supervision and the sole lease owner remain intact.

The bounded architecture review found a HIGH omitted worker-fault path during
shutdown and a MEDIUM missing deadline recheck between framework stop and root
disposal. Focused red regressions reproduced both. Workers now record safe
additional failures during drain or after bounded stop, without requesting a
second shutdown. Root disposal is explicitly NotAttemptedBudgetExhausted when
the existing deadline expires before dispatch. Review scope, the corrections'
proof, package locks and full acceptance are recorded in the plan; the review
itself ran no tests and did not re-review the corrections.

README, provider/example guides, quickstart, lifecycle contract/model and task
checkpoint document the corrected behavior. Requirements, public API/acceptance
contracts and reviewer-owned checklist bytes remain unchanged; product intent,
baseline diagrams/ADR, governance, backlog, F-01 sources/examples, IaC and release
guidance are unaffected because no public API, dependency, product capability,
permission or operational action changes. This finishes only implementation;
fresh `converge` is next, and PR #6 remains draft.

The subsequent installed convergence assessment checked all 22 functional
requirements, seven buildable outcomes, 20 story scenarios, 12 edge cases,
12 grouped plan decisions, all 75 existing tasks and eight constitutional
principles against current scoped code. T073..T075's notification, cancellation
and eventual-fault corrections are implemented. One **CRITICAL contradiction**
remains in request resource retention: the admission endpoint registers its
lease-release `OnCompleted` callback after upstream host middleware. Reverse
callback order releases that lease before the earlier middleware's response
completion work finishes.

An isolated public-API/TestServer probe held such a middleware callback.
Protocol cleanup ran once, its artifact prerequisite and independent metadata
cleanup all reported Completed, and UnsafeActivities was empty while response
completion was still pending. The root was incorrectly eligible for external
owner disposal (NotAttemptedOwnerPending); the probe did not attempt root
disposal while holding the callback. A paired callback registered inside the
handler correctly retained protocol/artifact as UnsafePendingCallback and the
root as NotAttemptedUnsafe. Both held callbacks were released and observed.
The probe used a 150 ms real-time drain budget with five-second scheduler
backstops and no listener; deterministic barrier/virtual-time regressions remain
implementation work.

[Phase 12 / T076](../specs/002-module-lifecycle/tasks.md#phase-12-convergence)
appends the completion-boundary correction, pre-/post-admission and handled-error
regressions, pending owner/prerequisite/root protection, cooperative once-only
release and no deferred cleanup requirements. Existing task bytes, spec, plan
and all built-in/custom checklists remain unchanged. The assessment produced
one contradicts/CRITICAL finding and zero missing, partial or unrequested
findings; no application code or checklist approval changed.

Fresh `bash scripts/validate-lifecycle.sh` passed 161 source tests, nine boundary
proofs and seven package-only journeys, including six independent packages and
retained old-binary/new-source/shared-framework proof. Fresh
`bash scripts/validate-foundation.sh` passed 255 tests (42 foundation,
49 architecture, 164 composition), zero failed/skipped, retaining the original
eight scans. `python3 -m unittest discover -s tests/tooling -v` passed 22 tests.
Those passing baselines do not exercise the reproduced pre-admission completion
path and do not resolve F1.

README and this guide record the blocker. Provider/example/quickstart contracts,
product intent, diagrams/ADR, governance, master backlog, F-01 sources/examples,
IaC and release guidance are unaffected: convergence changes no API, intended
behavior, dependency, permission or operational action. Implementation evidence
remains historical, not acceptance of this uncovered path. Keep PR #6 draft;
that convergence checkpoint scheduled `implement` for T076. Finalization,
merge, feature completion and dependency availability remain separate gates.

The separately authorized
[T076 implementation follow-up](../specs/002-module-lifecycle/plan.md#t076-implementation-follow-up)
installs an internal first startup filter during supervised host build. Its
middleware registers the request-completion boundary before host filters and
middleware, so reverse-order completion releases admitted leases last, not on
handler return. Admission still uses the existing coordinator/tracker and
executes through normal host middleware/access policy; there is no new public
API, dependency, admission authority or disposal owner.

Barrier/virtual-time regressions cover callbacks registered by startup filters,
host middleware and handlers, for normal and handled-error responses. Pending
completion keeps the protocol, its artifact prerequisite and root protected
after the original drain budget expires; independent metadata cleanup completes.
Releasing pending work after bounded stop/disposal neither rewrites frozen
results nor retries cleanup/disposal. Cooperative callbacks release one request
activity only after all three registration sites finish, then modules and root
clean up once. A throwing handler-completion callback still runs the earlier
host callbacks before release in TestServer; this is not transport certification.

The bounded architecture review found no confirmed violations or unresolved
design questions. Its throwing-completion proof gap is covered by the added
counterpart; full locked acceptance and reviewed payload-only lock changes are
recorded in the plan. README, provider/example guides, lifecycle contract/model,
quickstart and task evidence describe the corrected boundary. Requirements,
public API/acceptance contracts and reviewer-owned checklists remain unchanged.
Product intent, baseline diagrams/ADR, governance, backlog, F-01 sources/examples,
IaC and release guidance are unaffected: no public API, dependency, product
capability, permission or operational action changes. This completes only
implementation; fresh `converge` is next and PR #6 remains draft.

### F-02 clean convergence

The subsequent installed `speckit-converge` assessment found no actionable gaps
in the current implementation against the spec, plan and all 76 tasks,
including the resulting T073..T076 corrections. It checked 22 functional
requirements, seven buildable outcomes, all 20 story scenarios, 12 edge cases
and 40 LC cases, plus 20 buildable plan obligations and the eight constitutional
principles as applicable to this bounded feature.

The plan obligations cover additive registration compatibility, metadata-only
validation, immutable selection, deterministic dependencies, host-owned
adapters, one coordinator, supervised build, analyzable owned routes, admission,
initial/later readiness, worker supervision, absolute budgets, reverse cleanup,
pending-resource retention, sole root ownership, safe diagnostics, independent
fixtures, restart/custom journeys, source/binary/framework compatibility, and
locked acceptance with architecture review and honest documentation. Current
source and focused proof paths were inspected; checked task boxes alone were
not evidence. There were zero missing, partial, contradictory or unrequested
findings, so `tasks.md` remains byte-for-byte unchanged without an empty phase.
Spec, plan, contracts, all checklist bytes, product/test/tooling sources and
tracked locks also remain unchanged.

| Fresh command | Result |
| --- | --- |
| `bash scripts/validate-lifecycle.sh` | Passed: 169 tests, nine boundary proofs, seven package-only journeys; six independent packages, retained old binary, new-source/shared-framework proof, formatting/analyzers and unchanged locks |
| `bash scripts/validate-foundation.sh` | Passed: 263 tests (42 foundation, 49 architecture, 172 composition), zero failed/skipped; original eight graph scans, ARCH-001..008, C-01..23, isolated Core, five original fixture packages and both compile-only hosts |
| `python3 -m unittest discover -s tests/tooling -v` | Passed: 22 tests |

The earlier direct host-notification-task exception-injection limitation
remains explicitly scoped in the implementation evidence, not a newly claimed
proof. No new runtime change requires another implementation architecture
review. README and this guide record convergence; provider/example/quickstart
contracts, product intent, diagrams/ADR, governance, backlog, IaC and release
guidance are unaffected because no API, behavior, dependency, operational step
or supported capability changes. No extension hooks are registered.

At that checkpoint, `finalize` was scheduled for a separate invocation and
PR #6 remained draft. Clean convergence alone is not finalization, merge
readiness, feature completion or dependency availability.

### F-02 finalization

The separately authorized finalization verifies all 22 requirements, seven
outcomes, 20 story scenarios, 12 edge cases and 40 LC cases through the
[acceptance traceability](../specs/002-module-lifecycle/plan.md#acceptance-traceability)
and clean convergence assessment. All 76 tasks remain complete; the built-in
16/16 and reviewer-owned composition/lifecycle 20/20 each remain unchanged.
No requirement, API, implementation, test, example, lock or checklist approval
changes in finalization.

Fresh default locked lifecycle acceptance passed 169 tests, nine boundary
proofs and seven package-only journeys, with six independent fixtures and
retained-old-binary/new-source/shared-framework compatibility. Foundation
acceptance passed 263 tests (42 foundation, 49 architecture, 172 composition),
zero failed/skipped, retaining the original eight scans, ARCH-001..008,
C-01..23, isolated Core and both compile-only hosts. Both commands verify
formatting/analyzers and package provenance. Tooling passed 22 tests.
The dated dependency assessment covered seven source/test projects with no
known vulnerable direct/transitive entries or assessment errors.
Exact commands/results and documentation review are in
[finalization acceptance](../specs/002-module-lifecycle/plan.md#finalization-acceptance-2026-10-21-utc).

The implemented graph and T073..T076 ownership changes already received the
required custom architecture review. No implementation changed after reviewed
commit `1760c01`, so documentation-only finalization requires no new review.
The recorded direct host-notification-task exception-injection limitation
remains explicit; this handoff does not claim that distinct test or production
provider, native-client or transport certification.

README, specification review status, plan acceptance and this guide now
describe the handoff. Provider/example guides, quickstart/contracts/model,
research, baseline product intent/architecture/diagrams/ADR, governance,
backlog, IaC and release guidance remain accurate: finalization changes no
API, dependency, runtime behavior, support scope, permission or operational step.
No extension hooks are registered.

At finalization, [PR #6](https://github.com/Stonefly-Labs/Hoard/pull/6) targeted
`main` and was ready for maintainer review. The shared checkpoint recorded
`await_merge / ready`, with F-02 still active and no dependent feature unlocked.
Finalization itself performed no infrastructure plan/apply, deployment,
publication, tag, release, permission change or merge.

### F-02 merge completion checkpoint

PR #6 subsequently merged into `main` on 2026-10-21 (UTC) at
`b80c69fc386541be4f56f6ef2edeca40f43a0e1c`. The separate `await_merge` stage
verified GitHub's merged state, merge ancestry in fetched `origin/main`, the
shared finalization checkpoint and ratified constitution, and all 76 completed
tasks. It started `chore/spec-progress-f-02` at that merge, and the helper
independently checked merge ancestry and task completion before recording F-02
with its directory, PR and merge commit.

The completion checkpoint clears the active feature and schedules `specify`;
the next dependency-ready entry is
[F-03: provider configuration and activation validation](HOARD_SPECKIT_MASTER_BACKLOG.md#foundation-f-03).
That progress-only PR had to merge before a new specification could begin from
main. No new specification or later stage ran during that completion invocation,
and no implementation, test, lock, task or reviewer-owned checklist changed.

README, this guide and the specification's current status reflect completion;
historical finalization evidence remains unchanged. Provider/example guides,
quickstart/contracts/model/research and plan acceptance, baseline product
intent/architecture/diagrams/ADR, governance, backlog, IaC and release guidance
are unaffected because this checkpoint changes no API, package graph, command,
runtime/support behavior or operational requirement. No new architecture review,
.NET acceptance or IaC run is warranted for this progress/docs-only scope.
The stage performs no merge, publication, deployment, infrastructure action,
tag, release or permission change.

### F-03 configuration specification

The F-02 completion checkpoint merged through
[PR #7](https://github.com/Stonefly-Labs/Hoard/pull/7). The subsequent
specification stage started `feature/003-provider-configuration` from fetched
`origin/main`, verified the shared checkpoint and ratified constitution, and
pinned [F-03](../specs/003-provider-configuration/spec.md) to
`specs/003-provider-configuration` using the exact backlog prompt.

Five prioritized stories, 22 acceptance scenarios, 26 functional requirements
and eight outcomes cover command line > environment > one file > documented
defaults, canonical-key conflicts, whole-selection replacement, provider option
validation and disabled-module isolation. Configuration must consume F-02's
existing pre-construction composition gate and F-01's compatibility policy,
including incompatible enabled optional targets. Explicit validated defaults
are not fallback from an invalid override. Environment/mounted-file secret
references require no cloud service; safe diagnostics exclude values, locators
and untrusted error payloads. Configuration work has finite coordination budgets,
protects pending resources, observes late faults and cannot activate after failure.
Settings and resolved secrets remain fixed until explicit restart.

Safe configuration evolution requires a supported version, a sanitized preview,
retained original, explicit approval and a complete validated replacement.
The private replacement may preserve secret references, but reports never expose
their locators or resolved credentials. Acceptance must include a representative
and interrupted conversion; synthetic old versions cannot be advertised as
released-format support. Configuration rollback never claims to reverse
provider-owned schema/data changes.

The [built-in requirements checklist](../specs/003-provider-configuration/checklists/requirements.md)
passes all 16 specification-quality criteria, with no unresolved clarification
markers. The bounded architecture review found no actionable findings or
consequential unanswered requirement choices. Exact option-contract ownership/
compatibility, actual lifecycle integration and pending-work retention, and
migration interruption/recovery remain later proof obligations. This review
does not generate or approve custom reviewer-owned checklists.

README and this guide now link the requirements. Provider/example guides,
F-01/F-02 artifacts/checklists, product intent, baseline architecture/diagrams/
ADR, governance, master backlog, IaC and release guides are unaffected: this
stage changes no API, dependency, implemented configuration behavior, provider
support claim, permission or operational command. The specification creates no
parser, resolver, converter, executable, management endpoint, UI or new runtime
API. No extension hooks are configured. The next scheduled stage is `clarify`
through a separate invocation, not planning or implementation.

### F-03 configuration clarification

The subsequent [clarification review](../specs/003-provider-configuration/spec.md#clarifications)
found no critical ambiguities across all ten review categories. Zero questions
were asked or answered; no requirement, acceptance criterion or scope decision
changed. Source precedence and canonical conflicts, effective versus structural
validation, explicit selection through F-02's gate, disabled isolation,
secret ownership/redaction, bounded pending-work safety, fixed-state restart
and interruption-safe conversion already have observable acceptance obligations.

Exact configuration/reference syntax, canonical names, option-contract ownership
and representation, supported version mappings, safe report layout and finite
budgets remain planning decisions under the existing requirements. Management/UI,
production scale targets, real-provider data recovery and cloud integrations
remain separately scoped; synthetic conversions cannot imply released-format
compatibility. No consequential product choice blocks planning.

The built-in requirements checklist was revalidated at 16/16 before and after,
with no newly passing items, regressions or unchecked items; its bytes are
unchanged. No custom reviewer-owned approval, implementation or runtime
acceptance is implied. No extension hooks are configured.

README, this guide and the specification record the result. Provider/example
guides, F-01/F-02 artifacts/checklists, product intent, baseline architecture/
diagrams/ADR, governance, master backlog, IaC and release guides are unaffected:
no requirement, API, dependency, provider support, command, permission or
operational behavior changed. No plan, tasks, parser, resolver, converter,
executable, endpoint or UI was created. The next scheduled stage is `plan`
through a separate invocation.

### F-03 configuration planning

The subsequent installed `speckit-plan` stage pins the same feature directory
and produces the [implementation plan](../specs/003-provider-configuration/plan.md),
[research decisions](../specs/003-provider-configuration/research.md),
[data/ownership model](../specs/003-provider-configuration/data-model.md),
[operator format](../specs/003-provider-configuration/contracts/configuration-format.md),
[Hosting API contract](../specs/003-provider-configuration/contracts/hosting-api.md),
[acceptance matrix](../specs/003-provider-configuration/contracts/acceptance.md)
and [validation guide](../specs/003-provider-configuration/quickstart.md).

The design uses version 1 JSON defaults/one explicit file, `HOARD_CONFIG` JSON
environment overrides and `--hoard:<path>=<JSON>` arguments. It preserves
whole-selection replacement, keyed option merging and structural rejection of
discarded/disabled malformed inputs. Descriptive option contracts live in
Hosting, with host-owned metadata/artifact adapters and no required change to
Abstractions/provider binaries. Configuration delegates composition acceptance
to F-02 and hands only successful single-use fixed owner inputs to the existing
supervised lifecycle; it does not create another readiness or shutdown authority.

Environment/file references resolve only after public checks. Default finite
coordination is 30 seconds outer/five seconds per dispatch, with retained
in-use inputs, supervised cancellation notification and safe late observations,
not forced termination. Reports never expose values, targets or raw callback
errors. Offline preview/apply uses an explicit synthetic `fixture-v0 -> 1`
mapping, full pre-publication validation, private same-directory staging and a
fresh no-clobber destination, retaining the original. Local-platform publication
proof, truthful pending outcomes and separate provider data recovery are
mandatory; released older-format or universal power-loss support is not implied.

All 26 requirements, eight outcomes, 22 scenarios and 13 edge cases map to
36 planned proof cases. The bounded custom architecture review found no
confirmed design contradiction or consequential unresolved question. Its
material future gaps are explicitly included: unchanged option-bearing legacy
provider binary, atomic proof-consumption/disposal/input-transfer races,
safe remapping of even regex-valid unknown lifecycle identities/path elements,
and publication/cancellation/interruption evidence on each claimed platform.
The reviewer ran no tests and approved no custom checklist.

README and this guide link the design. Existing specification/built-in checklist,
F-01/F-02 artifacts and reviewer-owned markers, product/test/tooling/lock files,
provider/example guides, baseline charter/specification/architecture/diagrams/
ADR, governance, backlog, IaC and release guidance remain unchanged. They are
unaffected because planning changes no implemented API, dependency, provider
support, executable command, listener, permission or operational behavior.
Provider/example additions and actual command documentation wait for implementation.

No extension hooks are configured. No task list, custom checklist, parser,
resolver, converter, runtime change, infrastructure plan/apply, publication,
deployment or merge occurs here. The proposed `validate-configuration.sh`
does not exist yet and is not claimed as passing. The next scheduled stage
is `checklist` through a separate invocation; generation is not reviewer approval
or implementation authorization.

### F-03 configuration requirements-quality checklists

The subsequent installed `speckit-checklist` stage pins the same recorded
directory and creates separate
[configuration](../specs/003-provider-configuration/checklists/configuration.md)
and [safety](../specs/003-provider-configuration/checklists/safety.md)
requirements-quality checklists, with 20 criteria each. Both are standard-depth
PR reviews for maintainers and provider-contract reviewers before implementation
authorization. No clarification question was needed: audience, depth and scope
were explicit in the stage invocation.

Configuration criteria cover permitted sources and precedence, canonical
duplicates, whole selections versus keyed options, explicit defaults,
structural versus effective validation, disabled isolation, existing composition
ownership, descriptive option associations, compatibility and bounded inputs.
Safety criteria cover local reference grammar/ownership, safe diagnostic identity
remapping and output surfaces, finite coordination and retained pending resources,
atomic ownership handoff, fixed-state restart, bundled/custom recovery,
versioned preview/approval and original-preserving publication/interruption.
Every criterion asks about written requirement quality with traceable evidence;
none is an implementation procedure or a claim that its criterion is satisfied.

All 40 items were generated unchecked and remain reviewer-owned. Generation is
not evaluation, approval, implementation authorization, exploit review or
runtime evidence.
The specification, seven planning artifacts, built-in 16/16 checklist and all
F-01/F-02 artifacts/approvals remain byte-for-byte unchanged. No extension hooks
are configured. No task list, parser, resolver, converter, runtime API or
configuration validation command is created by this stage.

README and this guide link the new review artifacts. Provider/example guides,
baseline product charter/specification, architecture/diagrams/ADR, constitution,
backlog, test/tooling/lock files, IaC and release documentation are unaffected:
no implemented behavior, dependency, support claim, executable command,
permission or operator procedure changes. Conversion requirements are reviewed
as writing, not performed. No infrastructure plan/apply, deployment, publication
or merge occurs.

After generation, the user explicitly asked Copilot to review both checklists
and flag anything needing attention. The assisted requirements review finds
configuration 20/20 and safety 20/20 satisfied, with no unresolved writing gap,
waiver or decision requiring user attention. Both artifacts now record checked
criteria and grouped written evidence. No specification or design remediation
was needed. This is separately requested requirements evaluation, not another
scheduled driver stage, independent human inspection, implementation
authorization, exploit review or runtime acceptance.

The generation-time checkpoint evidence correctly records 40 initially
unchecked items; the subsequent assisted review is recorded in the checklists
and draft PR, without rewriting stage history. The custom requirements-review
gate is now satisfied. The next separately authorized stage is `tasks`, followed
by read-only analysis; implementation is not started by this review and still
requires the remaining scheduled gates and a separate invocation.

### F-03 configuration task generation

The subsequent installed `speckit-tasks` stage pins the recorded feature
directory and produces the
[implementation task list](../specs/003-provider-configuration/tasks.md):
69 unchecked tasks across eight phases. Setup has four tasks, shared bounded
ownership/metadata primitives have eight, the five story phases have
8/11/11/7/12 respectively, and cross-cutting acceptance has eight.

The source-resolution MVP inspects safe winners/provenance without construction
or secret reads; it cannot produce a successful activation proof. Later
increments add secret-free composition through the actual F-02 gate, local
owner-scoped secrets, restart/bundled/custom journeys and explicit synthetic
conversion. All 26 requirements, eight outcomes and 36 planned CFG proof cases
have implementation/integration and focused evidence assignments, retaining the
acceptance contract's mappings for all 22 scenarios and 13 edge cases.

Task-level prerequisites order shared parser/evaluator/proof/lifecycle and
orchestrator edits. Disjoint tests, local env/file readers and conversion
mapping/publication work have explicit parallel groups; US4/US5 can develop
after the secure secret increment, with shared runner edits serialized.
Every task names destinations and required outcomes, including finite budgets
and size limits, unknown-identity remapping, atomic proof/disposal/input-transfer
races, retained option-bearing provider/lifecycle binaries, actual package
graphs and platform-specific no-clobber/interruption proof. Test instructions
require intended red-before-green evidence and release/observation of held work.

The specification, seven design artifacts and all built-in/custom checklist
bytes remain unchanged. Task generation neither evaluates those checklists
again nor supplies runtime acceptance. The existing assisted 40/40
requirements-quality review remains satisfied. No extension hooks are configured.
No parser, resolver, converter, runtime API, package/example change, dependency,
lockfile or `validate-configuration.sh` is created by this stage.

README and this guide link the generated work and next gate. Provider/example
guides, product charter/specification, baseline architecture/diagrams/ADR,
constitution, backlog, predecessor artifacts, IaC and release documentation are
unaffected: no implemented API, graph, support claim, command, listener,
permission or operational procedure changes. Their actual configuration and
recovery additions remain implementation tasks. No infrastructure plan/apply,
deployment, publication or merge occurs.

At the task-generation checkpoint, the next separately authorized stage was
read-only `analyze`; task generation did not start implementation or authorize
remediation. Reviewed custom checklists do not bypass the analysis gate.

### F-03 configuration cross-artifact analysis

The subsequent installed `speckit-analyze` stage uses the recorded feature
directory and reviews the specification, plan, tasks and supporting contracts
without changing them. It found no actionable duplication, ambiguity,
underspecification, inconsistency, constitution conflict or coverage gap.
All 26 functional requirements and eight buildable outcomes have implementation
and focused proof assignments; all 36 planned CFG cases preserve coverage of
the 22 scenarios and 13 edge cases. All 69 tasks map to requirements or shared
acceptance prerequisites, including the shared harness/primitive proofs in
T001/T012. The complete prerequisite graph is acyclic, the 30 parallel markers
refer to independent ready groups, and shared-file edits are ordered.

The structured report is recorded in
[draft PR #8](https://github.com/Stonefly-Labs/Hoard/pull/8), with completion
evidence in the shared checkpoint. All 12 feature artifacts, the constitution
and existing 16/16 built-in plus 20/20 and 20/20 custom checklist bytes remain
unchanged. No remediation or new checklist approval occurred; no extension
hooks are configured. The existing tooling suite passes all 22 tests.

README and this guide record the analysis and next gate. Provider/example
guides, predecessor artifacts, product charter/specification, baseline
architecture/diagrams/ADR, constitution, backlog, IaC and release documentation
are unaffected: analysis changes no implemented API, graph, support claim,
command, listener, permission or operational procedure. No parser, resolver,
converter, runtime/test/tooling/dependency/lock change, infrastructure action,
deployment, publication or merge occurs.

At the analysis checkpoint, the next separately authorized invocation was
`implement`, with the existing 40/40 custom requirements-review gate satisfied.
All 69 implementation tasks were unchecked. Actual safe output, bounded ownership, retained-binary
compatibility and local-platform publication/interruption still need measured
implementation evidence and the later required architecture review; this
analysis supplies none of that runtime acceptance.

### F-03 configuration implementation

The initial T001..T020 source-resolution checkpoint is historical; subsequent
implementation adds active selection/options, local secrets, configured
lifecycle handoff, restart/distribution and explicit synthetic conversion.
The [complete evidence](../specs/003-provider-configuration/plan.md#complete-implementation)
records actual commands, review disposition and support boundaries. PR #8
remains draft; convergence/finalization/merge are separate authorizations.

The input explicitly supplies Defaults, optional file, argument enumerable and
an environment dictionary/read adapter. It does not inspect developer process
credentials, appsettings, user-secrets or UI state. Snapshotting scans at most
4,096 arguments and 4,096 environment entries, retaining only reserved Hoard
arguments and names eligible for the documented environment-reference grammar.
Defaults/overlay/reserved-argument text is bounded before copying/parsing;
secret strings are immutable references, resolved only after every active
public check passes. Hosts must supply finite in-memory inputs; trusted
enumerators/clock implementations are not a sandbox.

Each explicit document requires version 1; overlays cannot repair document
versions. Canonical keys are case-insensitive after JSON escape decoding;
module selection values are not rewritten. Every supplied occurrence is
structurally checked, including disabled/discarded options. Whole selections
replace; module option leaves and option versions merge independently; secret
reference objects replace atomically. Reports retain only safe identities and
winning source kinds, never values or private origins.

Default coordination is 30 seconds absolute and five seconds per dispatch,
capped by remaining time. Complete synchronous prefixes, async bodies and
cancellation notification are tracked; pending tasks retain inputs after
bounded disposal, with safe eventual diagnostics and frozen results. Expired
monotonic dispatch caps reject even if timeout notification arrives late.
Metric listeners run within supervised callback work, not under the state lock.

Use full fixture acceptance and retained compatibility checks:

```bash
bash scripts/validate-configuration.sh
bash scripts/validate-lifecycle.sh
bash scripts/validate-foundation.sh
python3 -m unittest discover -s tests/tooling -v
```

The configuration runner prepares real package/graph inputs for its two
`Prepared_configuration...` proof tests. Ordinary source/primitive/lifecycle
tests need no such manifest; retained foundation/lifecycle runners exclude
only those configuration-specific preparation tests, not the ordinary
regressions. No missing manifest is treated as a passing proof.

Explicit partial modes are:

```bash
bash scripts/validate-configuration.sh \
  --filter '(FullyQualifiedName~Configuration|FullyQualifiedName~ConfiguredComposition)&FullyQualifiedName!~Prepared_configuration'
bash scripts/validate-configuration.sh --baseline-only
```

An explicit `--baseline-only --update-locks` creates/replays the two new
standalone Baseline locks. `--baseline-only --retain-baseline /absolute/fresh/private/directory`
retains the verified old binaries/assets/hashes outside Git without overwriting
an existing destination. These partial switches alone do not execute configured
package journeys or establish old-binary compatibility against new configuration.
`--evidence-directory /absolute/fresh/private/directory` optionally retains
the partial runner's real TRX and status, including failed red runs. For a full
run it retains the complete owner-private workspace, actual package/graph/
binary/platform evidence, results and final status for independent review;
this can be large. Only fully verified acceptance sets `fullAcceptance: true`.
An optional full-run `--retained-baseline /absolute/private/baseline-directory`
reuses the earlier verified binaries without changing/recompiling their bytes.
The old-provider package is built reproducibly against pre-F-03 Abstractions
with normalized source paths before any optional retained-byte substitution.
Both configured hosts restore/build with the same reviewed package locks, then
receive the verified retained provider DLL in their runtime output. Each journey
records and rechecks that actual DLL hash before/after execution; original
retained bytes never determine a different package hash or bypass locked restore.
Neither option accepts an existing output directory or publishes artifacts.
Intentional dependency/payload changes use explicit `--update-locks`, reviewed
lock diffs and a separate default locked replay. Unit tooling tests use
synthetic inputs; they never recursively run these acceptance suites.

Evaluation succeeds only after the existing F-02 graph gate, enabled-only
required/type/range/allowed-value/address/version checks, every public callback,
local env/file resolution and secret-dependent callbacks. Invalid effective
input never restores a previous value. Proof consumption/disposal uses one
builder ownership gate and rejects stale/foreign/used/disposed proofs before
construction. Configured `ConfigureOptions` shares F-02's ComposingServices
phase, lease, ledger and root; it introduces no second lifecycle authority.
Inputs survive pending delivery/notification/root work, even after bounded
disposal. Legacy F-02 callers without opt-in keep their original APIs/behavior.

Conversion lives in `Hoard.Hosting.Configuration.Conversion`: preview pins
explicit original/proposal/builder/destination context without resolving
secrets; `Session.Approve()` authorizes one full-validation apply, never
activation. No environment/CLI overlays apply during conversion; an explicit
read adapter may supply local secret values during apply. Output preserves
references, not resolved credentials. Exclusive same-directory private staging,
flush/close and no-clobber publication preserve the original. Observe
`Publication.Status` after `PublicationPending`; the returned outcome/report
remain frozen. Remove only identified staging files after their originating
process/work is known to have ended. Do not promise rollback from cancellation.

Actual publication/interruption evidence covers the current macOS local
volume, not Linux, network shares, hostile same-user races or hardware power
loss. Run the same real child matrix on any newly claimed platform.
Configuration restoration never reverses provider schema/artifact changes;
coherent versions, reference targets and provider-owned backups/restore remain
separate recovery prerequisites.

See the [historical MVP evidence](../specs/003-provider-configuration/plan.md#source-resolution-mvp-implementation)
for its earlier scoped review and three corrected findings.
Source/option/diagnostic/ownership types are grouped into cohesive files rather
than one file per ancillary type; there is no new package, runtime dependency
or second lifecycle authority. README, provider guide and the active
plan/quickstart/status banners distinguish fixture support from planned product
features. F-01/F-02 artifacts and reviewer checklists, product intent,
baseline diagrams/ADR, constitution, backlog, infrastructure and release guides
are otherwise unaffected: no real provider, listener, management/API/UI,
deployment, permission or provider-data operation is introduced.

### F-03 convergence: diagnostic follow-up

The installed `speckit-converge` assessed the present scoped implementation
against all 26 FRs, eight buildable SCs, 22 story scenarios, 13 edge cases,
12 grouped plan decisions, 69 original tasks and eight constitutional principles.
Its outcome is **tasks_appended**, with two HIGH partial diagnostic-fidelity
findings and no missing, contradicting or unrequested findings:

| Finding | Current evidence | Remaining task |
| --- | --- | --- |
| F1: known secret setting lost | A public-API probe supplies a CLI reference for `modules:metadata:options:credential`; missing resolution reports `SecretUnavailable`, owner `metadata`, source `CommandLine`, but setting `unknown-setting` | T070: retain safe setting context through resolution and supervised failures |
| F2: option rule/source lost | A public validator returns the declared field/rule `label`/`paired` after a CLI override; the report has the canonical field but only `CheckFailure`, source `Defaults`, no `paired` identity and generic correction | T071: retain the validated declared rule and effective source with host-owned action text |

The probes use current compiled Hosting APIs and existing instrumented fixtures
in a session-private harness, not application changes or personal credentials.
Both failures return no activation proof. No credential disclosure, activation
bypass or new lifecycle authority was observed. These are feature diagnostic
gaps, not a claim that a passing suite proves every requirement.

Fresh exact acceptance commands passed:

| Command | Result |
| --- | --- |
| `bash scripts/validate-configuration.sh` | 168 configuration tests, six boundary proofs, nine package-only journeys, five actual Darwin child interruption barriers; CFG-01..36, formatting/analyzers and tooling passed; locks unchanged |
| `bash scripts/validate-lifecycle.sh` | 336 tests, nine boundary proofs, seven journeys, six independent packages and retained old registration binary passed |
| `bash scripts/validate-foundation.sh` | 42 unit, 54 architecture and 339 composition tests passed, zero failures/skips; retained package/Core/host/rejection proofs passed |
| `python3 -m unittest discover -s tests/tooling -v` | All 38 tests passed |

The stage appends only [Phase 9 / T070–T071](../specs/003-provider-configuration/tasks.md#phase-9-convergence).
All original task bytes/markers, spec, plan, contracts and reviewer checklists
remain unchanged; the earlier implementation-stage status in the task list
is historical, not completion of the two new tasks. No extension hooks exist.
The shared checkpoint returns to `implement / ready`, then requires a fresh
convergence assessment. PR #8 remains draft; finalization and merge are blocked
until the gaps are resolved. No feature completion or dependency unlock occurs.

README and this guide update only current foundation/stage status. Provider/
example/quickstart guidance, baseline product/architecture diagrams/ADR,
governance/backlog, predecessor artifacts, infrastructure and release guides
are otherwise unaffected: no API, dependency, grammar, command, runtime behavior,
platform support, permission or operational procedure changed. Diagnostic
guidance/evidence changes belong to the implementation follow-up. Existing
architecture-review evidence remains historical; this append-only task/docs
checkpoint changes no provider boundary or shared lifecycle invariant.

### F-03 diagnostic implementation follow-up

The separately authorized `speckit-implement` follow-up corrects T070/T071
without changing the original 69 tasks or reviewer-owned checklist approvals.
Secret env/file dispatch now captures the known canonical field alongside
owner/phase/winning source. Failure, timeout, caller cancellation, cancellation
notification failure and eventual check faults keep that context; pending
inputs remain retained and returned reports/outcomes stay frozen.

Public and secret-dependent rule rejection retains `CheckFailure` and a
separate nullable `OptionRule`, validated against the owner's finite declared
rule metadata. The effective violated field supplies its winning source.
Malformed/unknown callback results still fail InvalidCheckResult without
reflecting their identities; correction text is host-owned. Unsupported active
option versions report their canonical version setting and actual source.
No values, locators, raw exceptions or new metric dimensions are added.
F-02 remains the only activation/lifecycle owner; no dependency is added.

Executable red/green evidence and complete acceptance/review disposition are
recorded in the [follow-up plan evidence](../specs/003-provider-configuration/plan.md#diagnostic-implementation-follow-up).
The next scheduled stage is fresh `converge`, not finalize. PR #8 remains
draft; no feature completion, dependency unlock or merge occurs here.
README, provider/example diagnostic guidance, model/contracts and quickstart
are updated. Product intent, baseline architecture/diagrams/ADR, governance,
backlog, predecessor artifacts, IaC and release guides are unaffected because
no provider support, grammar, listener, API endpoint, dependency direction,
platform guarantee, deployment, permission or provider-data operation changes.
The only additive public member is the safe diagnostic `OptionRule`.

### F-03 clean convergence

The subsequent installed `speckit-converge` assesses the present scoped code
against the spec, plan and every task, not checkbox completion or a branch diff.
Its outcome is **converged**, with zero missing, partial, contradicting or
unrequested findings and zero findings at any severity. It checks all 26 FRs,
eight buildable SCs, 22 story scenarios, 13 edge cases, 12 grouped plan
decisions, all 71 tasks including T070/T071, and eight constitutional principles.
No empty convergence phase is appended. All feature artifacts, task bytes,
built-in/custom checklists and constitution remain byte-for-byte unchanged.

The assessment traces source structure/precedence/bounds, actual F-02 composition
and disabled isolation, active option contracts/checks, local owner-only secrets,
finite supervision and retained inputs, single-use proof transfer, configured
delivery, restart/distribution, synthetic conversion and private publication
to their implementation and focused proofs. The twelve plan groups cover
Hosting/dependency compatibility; strict source parsing; merge/fixed provenance;
the existing composition gate; public option checks; local secret ownership;
finite supervision; proof/transfer ownership; sole F-02 delivery/lifecycle;
restart/distribution; synthetic preview/approval; and no-clobber publication.
Documentation and support claims are checked against the actual APIs, example
journeys and measured limits, not inferred from a passing test count.

T070's env/file failures now retain the exact known field, owner and source
through timeout, caller cancellation, notification failure and late faults.
T071's public/secret-dependent rejection retains only the validated declared
OptionRule, effective field/source and host-owned action; explicit active
option-version errors retain their own setting/source. Malformed/unknown
callback identities remain sanitized InvalidCheckResult failures. No activation
bypass, new dependency/lifecycle owner or normal-output payload was observed.

| Validation entry point | Fresh result |
| --- | --- |
| `bash scripts/validate-configuration.sh` with a fresh private `--evidence-directory` | Passed full locked acceptance: 201 configuration tests, six boundary proofs, nine package-only journeys, five actual Darwin interruption barriers, CFG-01..36, formatting/analyzers and 38 tooling tests; no lock mutation |

The optional evidence-directory flag only retains the complete owner-private
workspace; it is not a partial selector. Actual TRX records show 201/201 and
6/6 passed with zero failed, skipped or unexecuted tests. The closed result is
passed/fullAcceptance; the manifest has all 36 cases, 13 actual graph scans,
nine exact journeys, six independent packages and both retained pre-F-03
binaries with verified runtime-provider provenance. Evidence paths are local
artifacts, not committed binaries or a prerequisite for another checkout:
the documented default command prepares equivalent fresh proof inputs.

Publication remains measured Darwin on local device `16777232`, not a verified
filesystem-family, Linux, network-share or power-loss guarantee. The prior
implementation's lifecycle/foundation runs and architecture review remain
historical evidence; this convergence does not claim to rerun them or constitute
an exploit-focused security review. No runtime source, test, dependency or
operational behavior changes in this stage.

Only README, this guide and the driver checkpoint change. Provider/example/
quickstart guidance, product charter/specification, baseline architecture/
diagrams/ADR, backlog/governance, predecessor artifacts, infrastructure and
release guides are unaffected: their APIs, support boundaries, procedures and
intent remain accurate. Existing architecture-review evidence is sufficient
for this documentation/progress-only handoff; finalization retains its own
acceptance/documentation/review gate.

The checkpoint schedules **`finalize / ready`**. PR #8 remains draft; no further
implementation pass is needed for the assessed scope. This invocation does not
finalize, request a merge, complete F-03, unlock dependencies, deploy, apply
infrastructure or publish packages/releases.

### F-03 finalization

The separately authorized finalization verifies the clean convergence result
against all 26 requirements, eight outcomes, 22 story scenarios, 13 edge cases,
36 CFG cases, 12 grouped plan decisions and all 71 completed tasks. The built-in
16/16 and reviewer-owned configuration/safety 20/20 each remain unchanged.
Requirements review is not independent implementation or provider certification.

Fresh full locked configuration acceptance passed 201 tests, six boundary
proofs, nine package-only journeys and five actual Darwin interruption barriers,
with all 13 graph scans, six independent packages, retained pre-F-03 binaries
and verified runtime-provider provenance. The optional private evidence-directory
flag retained the complete workspace and actual 201/201 and 6/6 TRX results,
not a partial selection. Lifecycle acceptance passed 369 tests, nine boundary
proofs and seven journeys; foundation passed 42 unit, 54 architecture and
372 composition tests, zero failed/skipped. Formatting/analyzers and all
38 tooling tests passed; no lock changed. The dated dependency advisory check
covered seven solution projects with no known vulnerable entries or errors.
Commands, acceptance traceability and limitations are recorded in the
[finalization evidence](../specs/003-provider-configuration/plan.md#finalization-acceptance-2026-10-21).

The implemented graph/ownership corrections and T070/T071 already received
the required custom architecture reviews. No implementation changed after
reviewed commit `66fef6b`; this documentation/progress-only finalization does
not require a new review or claim an independent runtime/exploit audit.
Publication remains measured Darwin/local-device behavior, not Linux,
network-filesystem or hardware power-loss certification. Bounded waiting
cannot terminate trusted code, and configuration rollback cannot reverse
provider-owned data changes.

README, specification review status, plan evidence, this guide and the provider
guide's stale future-tense gate description are updated. Provider API/operational
guidance, examples, quickstart/model/contracts/research, baseline product intent,
architecture/diagrams/ADR, governance/backlog, predecessor artifacts, IaC and
release guidance otherwise remain accurate: finalization changes no API,
dependency, runtime, grammar, support scope, permission or operational procedure.
Task bodies/markers and reviewer-owned checklist bytes are preserved.

At finalization, [PR #8](https://github.com/Stonefly-Labs/Hoard/pull/8) targeted
`main` and was ready for maintainer review. The shared checkpoint recorded
`await_merge / ready`, with F-03 still active and dependent work locked.
Finalization itself performed no merge, infrastructure plan/apply, deployment,
package/release publication, tag or permission change.

### F-03 merge completion checkpoint

PR #8 subsequently merged into `main` on 2026-10-21 (UTC) at
`7fd73267a5154583363c94e9e85b9bac7d4a16b3`. The separate `await_merge` stage
verified GitHub's merged state, merge ancestry in fetched `origin/main`, the
shared finalization checkpoint and ratified constitution, and all 71 completed
tasks. It started `chore/spec-progress-f-03` at that merge, and the helper
independently checked merge ancestry and task completion before recording F-03
with its directory, PR and merge commit.

The completion checkpoint clears the active feature and schedules `specify`;
the next dependency-ready entry is
[F-04: module capabilities and management discovery API](HOARD_SPECKIT_MASTER_BACKLOG.md#foundation-f-04).
The progress-only checkpoint subsequently merged through
[PR #9](https://github.com/Stonefly-Labs/Hoard/pull/9), satisfying the next-spec
merge gate.
No new specification or later stage ran during this completion invocation,
and no implementation, test, lock, task or reviewer-owned checklist changed.

README, this guide and the specification's current status reflect completion;
historical finalization evidence remains unchanged. Provider/example guides,
quickstart/contracts/model/research and plan acceptance, baseline product
intent/architecture/diagrams/ADR, governance, backlog, predecessor artifacts,
IaC and release guidance are unaffected because this checkpoint changes no API,
package graph, command, runtime/support behavior or operational requirement.
No new architecture review, .NET acceptance or IaC run is warranted for this
progress/docs-only scope. The stage performs no merge, publication, deployment,
infrastructure action, tag, release or permission change.

### F-04 module discovery specification

The separately authorized `specify` stage starts
`feature/004-module-discovery` from fetched `origin/main` after verifying
the merged F-03 completion checkpoint, ratified constitution and shared
predecessor work. The helper pins
[F-04](HOARD_SPECKIT_MASTER_BACKLOG.md#foundation-f-04) and
`specs/004-module-discovery`; the installed `speckit-specify` receives the exact
backlog prompt with only its command prefix removed.

The [specification](../specs/004-module-discovery/spec.md) contains five
independently testable journeys, 22 acceptance scenarios, 13 edge cases,
22 functional requirements and eight measurable outcomes. It separates known
package inclusion, registration, enablement, distribution support and observed
readiness. Unknown inclusion or support evidence cannot be promoted into an
installed/usable production feature. Capability availability is operation- and
dependency-scoped and must match actual composed fixture routes/services and
published lifecycle observations, never extra probes or a second activation
authority. Failed startup does not become a successful diagnostic service.

Management-read access protects inventory, capability/option details and API
descriptions. Explicit local loopback policy is distinct from secured network
exposure; reference identities exercise enforcement without implementing
production login or token issuance. Sanitized descriptive option metadata
contains no configured values or secret locators. Discovery is read-only and
does not confer execution permission.

The presentation contract requires distinct loading, empty, denied, failed,
unknown, stale, disabled, unsupported and temporarily not-ready states, safe
textual guidance and no unsupported/unavailable action invocation. A reference
consumer must prove these decisions; the rendered Next.js console remains
SPEC-11 and later UI work. Versioned, coherent observations identify their
distribution/lifecycle and freshness; representative local acceptance targets
95% of 100 reads within two seconds for 100 modules with 10 capabilities each
and 10 concurrent readers, without provider I/O or resource growth.
These are future proof obligations, not measurements from specification.

The [built-in quality checklist](../specs/004-module-discovery/checklists/requirements.md)
passes 16/16 specification-quality criteria with no unresolved clarification
markers. It is not reviewer-owned custom checklist approval, implementation
authorization or passing runtime evidence. Exact contracts, public signatures,
limits, route shapes and observation mechanics remain planning decisions.
The bounded `hoard-architecture-review` found no actionable requirements-level
architecture findings or unresolved design questions; route/service truth,
coherent observations, access/redaction and reference-consumer behavior still
require future implementation evidence.
This invocation generates no plan, tasks, custom checklists, endpoint, product
console, provider, package/dependency change or infrastructure. At the
specification checkpoint, the next stage was `clarify` through a separate
invocation.

README and this guide reflect the specification. Provider/example guides,
predecessor artifacts, baseline charter/product specification/architecture/
diagrams/ADR, constitution, master backlog, IaC and release guidance are
unaffected because this stage changes no current API, dependency graph,
validation command, runtime/support behavior or operational procedure. Their
planned discovery/static-console boundaries remain in force.

### F-04 module discovery clarification

The separately authorized `clarify` stage resumes the recorded
`feature/004-module-discovery` branch and `specs/004-module-discovery`, preserving
the completed specification in draft
[PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10).
Before beginning, the branch incorporates merged workflow/release-policy
[PR #11](https://github.com/Stonefly-Labs/Hoard/pull/11) from fetched
`origin/main`, retaining its active feature checkpoint and pushing the merge.
The specification generator is not rerun and no second feature is created.

The installed `speckit-clarify` uses explicitly pinned feature context. The
[dated clarification review](../specs/004-module-discovery/spec.md#clarifications)
finds no critical ambiguities: zero questions, no changed requirements,
acceptance criteria or scope decisions. All ten review categories are clear:
functional scope/behavior, domain/data, interaction/UX, applicable quality
attributes, integration/dependencies, edge cases/failure handling,
constraints/tradeoffs, terminology/consistency, completion signals and
miscellaneous/placeholders.

The review preserves operation-scoped support and availability, the existing
configuration/lifecycle authorities, management-read versus execution permission,
sanitized metadata, coherent bounded observations and unknown/stale consumer
rules. Exact contract shapes, endpoints, limits, finite budgets, safe reason
vocabulary and observation mechanics remain planning decisions. Reference
consumer evidence stays in F-04; rendered screens and production identity
providers stay in their separately scoped workstreams.

Revalidation of the
[built-in specification-quality checklist](../specs/004-module-discovery/checklists/requirements.md)
remains **16/16 to 16/16**: zero newly passing items, regressions or unchecked
items, with every marker and all other checklist bytes unchanged. This is not
custom reviewer approval or runtime evidence. No extension hooks are configured.
At the clarification checkpoint, the next separately authorized stage was
`plan`; that invocation created no design artifacts, tasks, custom checklist,
endpoint, console or provider.

README, this guide and the spec's clarification section are updated with the
checkpoint. Provider/example guides, predecessor artifacts, baseline
charter/product specification/architecture/diagrams/ADR, constitution, backlog,
IaC and release guidance are unaffected: clarification changes no requirement,
public API, dependency graph, current command, runtime/support behavior or
operational procedure. The existing specification-stage architecture review
remains relevant; no new provider contract, composition or shared invariant
change warrants another architecture review. Product/.NET, frontend and IaC
acceptance are not rerun for this documentation/checkpoint-only stage.

### F-04 module discovery planning

The separately authorized `plan` stage runs the installed `speckit-plan`
with `specs/004-module-discovery` explicitly pinned on its recorded branch.
Its [implementation plan](../specs/004-module-discovery/plan.md),
[research](../specs/004-module-discovery/research.md),
[in-process model](../specs/004-module-discovery/data-model.md) and
[validation quickstart](../specs/004-module-discovery/quickstart.md) are design
artifacts, not new runtime behavior. The generated contracts define
[Hosting/Application integration](../specs/004-module-discovery/contracts/hosting-api.md),
[HTTP behavior](../specs/004-module-discovery/contracts/discovery-api.md),
[OpenAPI shapes](../specs/004-module-discovery/contracts/openapi.json),
[consumer presentation](../specs/004-module-discovery/contracts/presentation.md)
and [40 paired acceptance cases](../specs/004-module-discovery/contracts/acceptance.md).
All 22 requirements, eight outcomes, 22 scenarios and 13 edge cases are mapped.

The design keeps F-01/F-02/F-03 interfaces and the sole lifecycle authority.
An immutable host catalog separates known inclusion, tested support and
sanitized public metadata; actual route/service-owner evidence and a single
published lifecycle revision determine operation availability without request
probes, secret reads or construction. Application gains its already approved
Hosting/ASP.NET Core dependencies only during implementation. Core stays
provider-free; metadata/artifact packages remain Abstractions-only.

Two literal protected GET routes cover discovery and its fixed OpenAPI
description; neither bypasses the existing route validator. Explicit local
loopback/no-proxy and authenticated secured-network/TLS/trusted-proxy modes
share management-read enforcement. Defaults authorize no exposure until an
explicit posture/policy is supplied. Bounded private JSON encoding, cooperative
cancellation, closed safe diagnostics and no-store prevent success-shaped
fallbacks or accidental disclosure.

The bounded architecture review identified a missing failure-context schema
field set and an unspecified cross-assembly ownership check. The design now
requires safe phase/approved affected identities in Problem and a Hosting-owned
BindHoardDiscovery guard for the exact app/lease/root/source. It also requires
future private ephemeral loopback Kestrel adapter evidence rather than relying
solely on TestServer for actual binding/raw-peer capture. No external proxy,
production certificate/auth, rendered accessibility or runtime approval is
claimed. All observation/concurrency/package/binary proofs remain future gates.

The JSON-only reference consumer defines textual state distinctions, denied/
failed/stale handling and non-invocable unsupported/unknown/unavailable actions;
the rendered static Next.js console remains later work. The proposed
`bash scripts/validate-discovery.sh` does not exist yet. Existing validation
commands remain unchanged; planning never reports future cases as passed.

README and this guide are updated; spec requirements and all built-in checklist
bytes remain unchanged. Provider/example guides, predecessor artifacts, baseline
charter/product specification/architecture/diagrams/ADR, constitution, backlog,
IaC and release guidance are unaffected: no current API, package graph, command,
runtime/support claim or operational procedure changed. Their established
boundaries already permit this proposed design. No extension hooks, tasks,
custom checklists, source/project/lock changes, frontend, provider, listener,
infrastructure action or release are introduced. The next separately authorized
stage is `checklist`; generation will not approve reviewer-owned criteria.

### F-04 module discovery requirements-quality checklists

The separately authorized `checklist` stage runs the installed
`speckit-checklist` with `specs/004-module-discovery` explicitly pinned.
It creates two new reviewer-owned requirements-quality checklists:
[discovery](../specs/004-module-discovery/checklists/discovery.md) and
[management](../specs/004-module-discovery/checklists/management.md), with
20 criteria each. Both use standard depth for maintainers and PR reviewers
before implementation authorization; provider/composition reviewers own the
first domain and management-API/consumer reviewers the second.

Discovery covers explicit inclusion versus registration and selection,
distribution-qualified operation support, actual composition evidence,
inherited authorities, disabled isolation, coherent lifecycle observations,
failure/restart semantics, finite limits and measurable bounded acceptance.
Management covers equal protection of reads and API descriptions, explicit
local/network exposure assumptions, read versus execution permission,
allowlisted metadata, safe bounded diagnostics, versioned contract consistency
and consumer state/freshness/action rules. Semantic accessibility and fixture
policy/transport evidence are explicitly distinct from rendered WCAG,
production identity or external-proxy certification.

All **40 criteria are generated unchecked**. They ask whether written
requirements are complete, clear, consistent, covered and measurable; they are
not runtime test procedures or a finding that the requirements are satisfied.
Every item references the specification and supporting design sections.
No reviewer evaluation, waiver, remediation or custom checklist approval occurs.
The built-in 16/16 specification-quality checklist and all specification/design
bytes remain unchanged. No extension hooks are configured.

README and this guide link the generated reviews and preserve current versus
planned behavior. Provider/example guides, predecessor artifacts, baseline
charter/product specification/architecture/diagrams/ADR, constitution, backlog,
IaC and release guidance are unaffected: checklist generation changes no
requirement, public API, dependency, current command, runtime/support behavior
or operational procedure. No additional architecture review is needed for
this requirements-review-artifact/documentation/checkpoint-only stage.
Product/.NET, UI and IaC acceptance are not rerun; the proposed discovery
acceptance command still does not exist and is not reported as passing.

The next separately authorized stage is `tasks`, not implementation.
Task generation and subsequent read-only analysis do not approve these custom
checklists. Implementation remains gated on reviewer-owned satisfaction or
explicit reviewer authorization; the draft feature PR remains incomplete.
No task list, endpoint, console, provider, project/lock change, listener,
infrastructure action, tag, release or merge is introduced.

After generation, the user explicitly requested an assisted evaluation of both
checklists. The review assesses all 40 criteria against the unchanged
specification and nine design artifacts at `b5a1880`: **discovery 20/20 and
management 20/20 satisfied**, without unresolved requirements-quality findings,
waivers or decisions needing maintainer attention. Each checklist records
grouped criterion-level evidence and the distinction from independent human
inspection or implementation proof. Only review markers and evidence change;
no requirement or design is remediated.

This separately requested review is not a scheduled driver stage. The
checkpoint stays **`tasks / ready`**; the next invocation still performs task
generation, then separately invoked read-only analysis before implementation.
The custom requirements-quality gate is now satisfied, but actual composition,
publication/cancellation races, redaction/access integration, consumer behavior,
package/binary compatibility and bounded performance remain future proof
obligations. No runtime acceptance, rendered accessibility, production support
or permission to skip later stages follows from the checked markers.

README and this guide reflect the review; the specification, nine design
artifacts, built-in checklist and flow checkpoint are byte-for-byte unchanged.
Provider/example guides, predecessor artifacts, product/architecture/ADR/
diagrams, constitution, backlog, IaC and release guidance remain unaffected
because the assisted review changes no requirements, contract, runtime,
dependency or operational procedure. No additional architecture review or
product/.NET/UI/IaC acceptance is warranted for marker/evidence-only changes.

### F-04 module discovery task generation

The separately authorized `tasks` stage runs the installed `speckit-tasks`
with `SPECIFY_FEATURE_DIRECTORY=specs/004-module-discovery` on the recorded
feature branch. Its [implementation task list](../specs/004-module-discovery/tasks.md)
contains **78 unchecked tasks across eight phases**: four setup tasks,
eight frozen-metadata/publication prerequisites, five story phases of
8/11/16/9/10 tasks, and 12 cross-cutting tasks. Twenty-eight tasks identify
file-disjoint parallel opportunities after explicit prerequisites; the complete
task graph serializes shared coordinator/composition/source/encoding/helper
and lockfile edits.

All 22 requirements, eight outcomes and D01..D40 have implementation and focused
proof assignments. The unchanged acceptance contract supplies the complete
22-scenario/13-edge mapping. Tasks quote model invariants and preserve numeric
schema/collection/text/UTF-8 bounds. Tests precede changed behavior, with actual
negative runtime evidence required beyond initial missing-API compile failures.
The inventory MVP is in-process; it does not expose an unsecured route while
waiting for the management story. Both fixed HTTP slices are introduced together
with explicit read policy/posture, exact app/lease/source ownership, safe
bounded encoding and protected API description.

Actual route/effective owner-service evidence, sole-authority coherent
publication, disabled zero-side-effect inspection, loopback Kestrel/raw-peer/TLS
adapters, separate execution permission, safe full-surface diagnostics, JSON-only
consumer decisions, publication/cancellation races and the specified local
100-read workload remain future proof obligations. Pre-F-04 binaries must be
compiled and retained before platform changes; package-only bundled/custom
journeys, non-web framework propagation and all existing foundation/lifecycle/
configuration proofs remain mandatory. An incomplete proof inventory fails,
never skips into acceptance. Semantic consumer output is not rendered WCAG
evidence, and fixture/adapter evidence is not production qualification.

The built-in checklist and both assisted reviewer-owned 20/20 approvals remain
byte-for-byte unchanged, as do the specification and all nine design artifacts.
No extension hooks are configured. This stage creates no product/test source,
project/lock change, runner, listener, console, provider, infrastructure,
publication or merge. `bash scripts/validate-discovery.sh` is still proposed
and is not run or reported as passing.

README and this guide link the task list and next gate. Provider/example guides,
predecessor artifacts, baseline product/architecture/diagrams/ADR, constitution,
backlog, IaC and release guidance are unaffected because task generation changes
no requirement, design contract, current API, dependency graph, command,
runtime/support behavior or operational procedure. Implementation tasks require
their affected guides to be updated when new APIs actually exist. No additional
architecture review or product/.NET/UI/IaC acceptance is warranted for this
task-artifact/documentation/checkpoint-only change.

At task generation, the next separately authorized stage was read-only
`analyze`. The satisfied
custom requirements-quality gate does not bypass it or authorize implementation,
convergence, finalization or feature completion. Draft
[PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10) remains incomplete.

### F-04 module discovery cross-artifact analysis

The subsequent installed `speckit-analyze` runs read-only with
`SPECIFY_FEATURE_DIRECTORY=specs/004-module-discovery` on the recorded branch.
It assesses the specification, plan, tasks and supporting model/contracts
against constitution v1.0.0. No actionable duplication, ambiguity,
underspecification, inconsistency, coverage gap or constitutional conflict is
identified; no remediation is required.

All 22 functional requirements and eight buildable outcomes have implementation
and focused proof assignments. All 78 unchecked tasks map to requirements or
shared acceptance prerequisites; the complete prerequisite graph is acyclic,
every task reaches final closure, and shared-file edit chains are ordered.
The 40 paired cases, 22 story scenarios and 13 edge cases retain their proof
obligations, including actual route/service correspondence, lifecycle publication
races, protected descriptions, real private loopback adapters, JSON-only consumer
decisions, bounded performance and package/retained-binary compatibility.
Traceability is not proof that any of those future cases pass.

The structured report and coverage table are recorded in draft
[PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10), with stage evidence in
the shared checkpoint. All 14 feature files, including the specification, nine
design artifacts, task bodies/checkboxes and three checklists, remain unchanged.
The built-in 16/16 and existing assisted reviewer-owned 40/40 approvals are
preserved, not reapproved by analysis. No extension hooks are configured.
The repository tooling suite passes all 44 tests.

README and this guide record the analysis and next gate. Provider/example
guides, predecessor artifacts, baseline product/architecture/diagrams/ADR,
constitution, backlog, IaC and release guidance are unaffected: analysis changes
no requirement, design, implemented API, package graph, command, runtime/support
claim or operational procedure. No additional architecture review or product/
.NET/UI/IaC acceptance is warranted for this read-only analysis and documentation/
checkpoint-only change. The proposed discovery runner still does not exist
and is not run or reported as passing.

The checkpoint schedules **`implement / ready`** through a separate invocation,
with the existing custom requirements-quality gate satisfied. That invocation
must complete every remaining task and its checks unless genuinely blocked.
Analysis starts no implementation, listener, console, provider, infrastructure
operation, release or merge, and does not bypass convergence/finalization or
mark F-04 complete.

### F-04 implemented discovery and acceptance

The implementation invocation delivers Hosting's immutable public catalog,
safe source and sole-lifecycle publication plus Application's two protected
GET-only discovery slices. It completes the full task scope, not a single
phase. The [quickstart](../specs/004-module-discovery/quickstart.md#public-integration)
documents exact opt-in/mapping order, direct-local/no-proxy versus authenticated
TLS/trusted-proxy posture and the supported explicit Kestrel URL topology.
The [provider guide](PROVIDERS.md#safe-discovery-metadata-and-observations)
explains approved metadata, exact fixture support/actual binding evidence and
why read permission never authorizes execution.

```bash
bash scripts/validate-discovery.sh
```

The default command passed all 122 actual/declared tests, D01..D40, nine
package journeys, seven distinct wire observations, 18 real graph scans and
12 private-copy runtime mutations. It verifies all required suite classes and
fully qualified theory rows, never merely method names/counts. Missing or stale
proof, nonlocal/hash-drifted packages, skipped rows, retained binary/dependency/
assets drift and lock mutation fail closed. Default workspace cleanup is
owner-private and exact; use a fresh absolute `--evidence-directory` outside
the repository to retain local proof. `--update-locks` is intentional only;
review resulting locks, then independently replay the default.

Final default configuration, lifecycle and foundation checks also passed,
preserving all prior scan inventories, architecture/compatibility classifications
and retained binaries. Tooling passed 61 tests. Local macOS 26.5.0/.NET SDK
10.0.203 measurement recorded 100 complete reads of 100 x 10 contributions at
concurrency 10, zero extra provider activity/resources and p95 0.0354103s in the
retained run (0.066s in the subsequent exact default run).
The [implementation report](../specs/004-module-discovery/plan.md#implementation-evidence)
records exact commands/results, original hashes, earlier failed attempts,
provenance correction, both architecture reviews and red/green evidence.

The BCL-only stdin consumer proves semantic presentation/refresh behavior,
not a rendered console. Protected reads are snapshots of actual publication/
assessment times, not health refreshes or permission grants. Production auth,
external proxy isolation, request-log redaction, native providers/conformance
and rendered accessibility remain unqualified. Only dedicated adapter tests
open finite private ephemeral loopback listeners; no product/public service
or deployment exists.

README/guides/examples and active implementation artifacts are updated.
Product charter/specification/architecture/ADR/diagrams, constitution/backlog,
predecessor artifacts, IaC and release documents are unaffected because their
product scope, approved boundaries, governance and operational release/cloud
procedures did not change. No infrastructure, release, publication or merge
ran. Draft [PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10) remains draft;
the next separately authorized stage is `converge`, not merge or a new feature.

### F-04 convergence: reference-consumer follow-up

The installed `speckit-converge` resumes the interrupted `converge / running`
checkpoint on the recorded branch and explicitly pinned feature directory.
It preserves the already appended
[Phase 9 / T079-T080](../specs/004-module-discovery/tasks.md#phase-9-convergence),
without rerunning `begin`, duplicating tasks or changing any existing task.
The assessment covers 22 functional requirements, eight buildable outcomes,
22 story scenarios, 13 edges, all 80 current tasks, ten grouped plan decisions
and eight constitutional principles. It identifies two **partial** consumer
gaps; there are no additional missing, contradicting or unrequested findings.

| Task | Severity | Current evidence and required correction |
| --- | --- | --- |
| T079 | HIGH | The public JSON reader understands `unknown` and terminal module phases, but action eligibility checks only understood/registered/enabled/ready owners and dependencies. With current host admission, usable capability and independent execution permission retained, all ten tested `unknown`, `stopping`, `draining`, `cleaning-up` and `stopped` owner/dependency cases remain enabled. Future phases correctly reject, and the genuine ready control correctly permits the last-entered `assessing-readiness` phase. Add paired wire regressions and fail closed at the existing interpretation/eligibility boundary. |
| T080 | MEDIUM | Fixture evidence replaces the support semantic line, giving supported, unsupported and unverified contributions identical support text. Unsupported/unverified actions correctly remain hidden and reasons remain available; preserve the explicit support state and fixture qualification separately, with focused wire/reading-order assertions. |

A private session-only reproduction uses actual authorized endpoint bytes and
the compiled JSON reader/projector, not Hosting objects as consumer input.
It confirms both findings without modifying product/test sources or introducing
a product listener. The existing two consumer classes pass all 19 tests,
demonstrating the missing regression coverage rather than disproving the gaps.
Fresh locked discovery acceptance with a private `--evidence-directory` passes
122 declared/executed tests, D01..D40, nine package journeys, 18 real graph scans,
12 runtime mutation checks, original-binary and JSON-consumer proof, with no
lock mutation. The specified 100-read local fixture workload records p95
0.031 seconds and zero additional provider activity/resource deltas.
`python3 -m unittest discover -s tests/tooling -v` passes all 61 tests.
Prior configuration/lifecycle/foundation results remain implementation evidence;
this assessment does not claim to rerun those suites or qualify production
providers, identity, proxy isolation, native clients or rendered accessibility.

Only README, this guide, the append-only task additions and the flow checkpoint
are shared by this stage. The specification, plan, contracts and reviewer-owned
checklists remain unchanged. Provider/example/quickstart guides retain the same
intended APIs and operational procedures; their known consumer proof limits are
recorded here rather than rewriting historical implementation evidence.
Product charter/specification/architecture/ADR/diagrams, governance/backlog,
predecessor artifacts, IaC and release guidance are unaffected because no
requirement, dependency boundary, API, runtime, permission, restart/rollback,
infrastructure or release behavior changes. No new architecture review is
required for this assessment-only checkpoint.

The outcome is **`tasks_appended`**, recovered from the interrupted stage:
78 original tasks remain checked and T079-T080 remain unchecked. The helper
schedules **`implement / ready`** for a separate invocation, then fresh
convergence. Draft [PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10)
must remain draft; finalization and merge are blocked by these two gaps.
No implementation, merge, release, publication or infrastructure operation ran.

### F-04 convergence follow-up implementation

The next `implement` invocation completes T079-T080 without changing the
specification, contracts or reviewer-owned approvals. Reference-consumer
eligibility now requires every owner/dependency to be ready in
`assessing-readiness` or `running`, in addition to existing currentness,
support, availability, admission and independent permission checks. Unknown,
future and terminal phases cannot revive an action merely by retaining
`ready`/`usable` fields. The actual last-entered `assessing-readiness` control
remains eligible. Capability support has its own contextual semantic line,
followed by evidence scope and availability; fixture qualification no longer
replaces supported/unsupported/unverified text or safe corrective reasons.

Fifteen added wire scenarios establish the gaps before correction: 13 intended
runtime assertion failures, with future-phase rejection and genuine ready
controls already passing. All 36 focused consumer/presentation/refresh tests
then pass. Fresh `bash scripts/validate-discovery.sh --evidence-directory
<fresh-private-directory>` passes 137 declared/executed tests with no skips,
D01..D40, ten suites, nine package journeys, seven wire observations, 18 graph
scans, 12 existing runtime mutations and retained-binary/JSON-consumer checks.
No lock changed. The 100-read local fixture workload records p95 0.029193s
and zero extra provider activity/resources. Focused SDK formatting and all
61 tooling tests pass; full SDK formatting/analyzers also pass in acceptance.
Private TRX/log/manifest references and requirement mappings are in the
[follow-up evidence](../specs/004-module-discovery/plan.md#convergence-follow-up-implementation).
Prior configuration/lifecycle/foundation results remain historical; this
consumer-only change does not rerun or expand their qualification.

README, this guide, the example's semantic reading order/guide and the active
plan/tasks/quickstart are updated. Provider/custom-host guides, product
charter/specification/architecture/ADR/diagrams, governance/backlog,
predecessor artifacts, IaC and release guidance are unaffected: provider APIs,
dependencies, composition, transport, operations, restart/rollback and product
scope do not change. No new architecture review is required for this isolated
reference-consumer/evidence correction; the prior reviews remain in the plan.
All 80 tasks are checked, but draft
[PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10) remains draft and F-04
remains incomplete. Next is separately invoked fresh **`converge`**. No merge,
tag, release, package publication, deployment or infrastructure operation ran.

### F-04 clean convergence

The separately invoked installed `speckit-converge` assesses the current scoped
implementation after T079-T080, not a branch diff or task completion claims.
It finds **zero actionable findings** across 22 functional requirements, eight
buildable outcomes, 22 story scenarios, 13 edge cases, all 80 tasks, ten grouped
plan decisions and eight constitutional principles. Missing, partial,
contradicting and unrequested counts are all zero; no severity has a finding.
The specification, plan, tasks, contracts and reviewer-owned checklists remain
byte-for-byte unchanged. No empty convergence phase or new task is added.

The consumer rejects unknown/future and stopping/draining/cleaning-up/stopped
owner or dependency phases despite conflicting ready/usable fields, while the
genuine last-entered `assessing-readiness` control stays eligible subject to
independent execution permission. Explicit support state precedes separate
fixture evidence scope and availability, with safe corrective reasons and
contextual reading order. These close the two prior gaps without weakening
freshness, admission, support, binding or authorization boundaries.

Fresh `bash scripts/validate-discovery.sh --evidence-directory
<fresh-private-directory>` passes **137 declared/executed tests**, zero skips,
D01..D40, ten suites, nine package journeys, seven wire observations, 18 real
graph scans, 12 private-copy runtime mutations, retained binaries, JSON-only
consumer and SDK formatting/analyzers. Default locked mode changes no lock.
The command also passes all 61 tooling tests. Its private evidence run ID is
`a15d7e55-e599-470a-a26e-ba28dc32da90`; logs, TRX, manifests and payloads stay
outside Git. On macOS 26.5.0/.NET SDK 10.0.203, all 100 complete authorized
reads of 100 modules x 10 contributions at concurrency 10 produce
615,887..615,889-byte bodies, p95 **0.0265445 seconds** and zero constructor,
probe, secret-read, service-call, connection or active-resource deltas.
This is local fixture evidence, not a production SLA.

Prior configuration/lifecycle/foundation runs and architecture reviews remain
the implementation evidence recorded in the
[plan](../specs/004-module-discovery/plan.md#implementation-evidence); they are
not new rerun or review claims. This assessment changes no application, test,
tooling, dependency or lifecycle behavior, so no new architecture review is
warranted. Production identity, external proxy isolation, framework request-log
redaction, native protocols/provider conformance and rendered accessibility
remain unqualified.

README and this guide record the clean result; the draft PR carries the full
assessment and the shared flow checkpoint records its evidence. Provider and
example guides, quickstart/contracts/research/model, charter/product
specification/architecture/ADR/diagrams, governance/backlog, predecessor
artifacts, IaC and release guidance are unaffected because APIs, support scope,
dependency boundaries, commands, transport, restart/rollback and operational
procedures are unchanged.

The checkpoint schedules **`finalize / ready`** for a separate invocation.
[PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10) remains draft; clean
convergence does not finalize or complete F-04, request a merge, unlock
dependencies, publish a source release/package, deploy or apply infrastructure.

### F-04 finalization

Finalization verifies the clean convergence result, all 80 checked tasks,
the unchanged 16/16 requirements checklist and the existing reviewer-owned
20/20 discovery and 20/20 management approvals. No requirement, contract,
task body, approval, product/test/tooling source, dependency or lock changes.
The previous production/evidence architecture reviews remain applicable:
Hosting/Application composition and shared lifecycle ownership are unchanged;
the subsequent consumer correction is isolated to reference presentation
and its proof. No new architecture review is warranted for finalization docs.

Fresh locked discovery acceptance passes 137 exact declared/executed tests,
zero skips, D01..D40, ten suites, nine package journeys, seven wire observations,
18 actual graph scans, 11 local feed packages, 12 intended runtime-red mutations
with passing counterparts, JSON consumer and full SDK formatting/analyzers.
All 61 tooling tests pass within acceptance. A second fresh run uses
`--retained-baseline` to import and replay the originally frozen pre-F-04
lifecycle/configuration/options DLLs, with their original hashes, baseline
dependency/assets provenance and no consumer recompilation. This is distinct
from the first run's freshly built immutable merged-baseline consumers.
Commands, run IDs, manifest digests and original binary hashes are in the
[finalization evidence](../specs/004-module-discovery/plan.md#finalization-acceptance).

The exact-original-binary run records 100 complete authorized reads of
100 modules x 10 contributions at concurrency 10, p95 **0.034034 seconds**,
615,888..615,889-byte bodies and zero constructor, probe, secret-read,
service-call, connection or active-resource deltas on macOS 26.5.0/.NET SDK
10.0.203. This is local fixture evidence, not a production SLA.
`dotnet list Hoard.slnx package --vulnerable --include-transitive --format json`
reports no known vulnerable direct/transitive entries or assessment errors
across seven solution projects; it is not an exploit audit or future guarantee.
Previous foundation/lifecycle/configuration full-run results remain historical,
not new finalization rerun claims.

README, this guide and the active spec/plan/tasks/quickstart now record accepted
scope and the merge handoff. Provider and example guides, normative contracts,
research/model, charter/product specification/architecture/ADR/diagrams,
constitution/backlog, predecessor artifacts, IaC and release guidance are
unaffected: public APIs, support limits, commands, dependency boundaries,
transport, permissions, restart/rollback and operational procedures do not change.
Production identity, external proxies, framework request-log redaction,
native protocols/provider conformance and rendered accessibility remain unqualified.

Finalization makes [PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10)
ready for maintainer review/merge and schedules **`await_merge / ready`**.
F-04 is not yet complete and dependencies remain locked. A separate invocation
after the maintainer merges verifies the exact merge commit and publishes the
authorized `v0.0.4-alpha` source prerelease before recording completion.
This invocation does not merge, tag, release, publish packages, deploy or run
OpenTofu plan/apply.

### F-04 merge completion and alpha source release

[PR #10](https://github.com/Stonefly-Labs/Hoard/pull/10) merged on 2026-10-21 at
`287c7b65a068b50e672d92f2d535ef79c910ac0b`. The separately invoked
`await_merge` stage verifies that exact commit in fetched `origin/main`, the
unchanged ratified constitution/finalization checkpoint, all 80 completed tasks
and existing 16/16 requirements, 20/20 discovery and 20/20 management approvals.
Historical product acceptance and architecture reviews remain unchanged;
this documentation/progress-only stage does not rerun product acceptance or
require a new architecture review.

Under the bounded Spec Kit standing authorization, `hoard-release` publishes
the annotated `v0.0.4-alpha` tag at that exact feature merge commit, not the
progress branch tip. `python3 -m unittest discover -s tests/tooling -v` passes
all 61 tests; `python3 scripts/release.py v0.0.4-alpha` and
`python3 scripts/release.py v0.0.4-alpha --check-main` pass. The
[Source release run](https://github.com/Stonefly-Labs/Hoard/actions/runs/39678124349)
succeeds and the [published source prerelease](https://github.com/Stonefly-Labs/Hoard/releases/tag/v0.0.4-alpha)
is non-draft and prerelease-classified, with generated notes. Both automatic
ZIP and TAR.GZ archives are downloaded and verified: identical file inventories,
selected source/checkpoint files matching the merge commit, and exact merge SHA
in the ZIP metadata. The annotated remote tag independently peels to that SHA.
Downloaded verification archives are removed; no release artifact enters Git.

Only after publication verification does the helper independently check the
remote annotated tag and GitHub prerelease and record F-04 complete with
`release_tag` and `release_url`. The running checkpoint was first pushed in
draft [PR #12](https://github.com/Stonefly-Labs/Hoard/pull/12), preserving a
clean-worktree release and durable recovery point. PR #12 merged that running
checkpoint before the completion changes were committed, so it did not record
F-04 complete on `main`. The completion changes are preserved on
`chore/spec-progress-f-04-complete` for a follow-up progress-only PR. The next
scheduled stage is `specify / ready`, but a new specification remains gated on
that follow-up completion checkpoint merging. The existing source release is
unchanged; no tag or release is recreated.

README and this guide record the verified merge/release handoff. Feature
artifacts preserve historical finalization evidence; provider/example guides,
normative contracts, research/model, charter/product specification/architecture/
ADR/diagrams, constitution/backlog, predecessor artifacts, IaC and release
procedures are unaffected: no API, support scope, dependency, command,
permission, transport or restart/rollback change occurs. No older completion
is backfilled with release metadata. This stage starts no new specification,
implements no feature, merges no PR, publishes no binary/package/image and
performs no infrastructure, deployment, governance change or OpenTofu plan/apply.

### F-05 metadata persistence specification

The F-04 completion checkpoint merged through
[PR #13](https://github.com/Stonefly-Labs/Hoard/pull/13). The separately invoked
`specify` stage fetches `origin/main`, verifies the merged checkpoint and ratified
constitution, and starts `feature/005-metadata-persistence` from current main.
The driver pins the exact master F-05 prompt and independent directory
`specs/005-metadata-persistence`; the installed `speckit-specify` uses that explicit
directory and the resolved specification template. No extension hook is
registered, and only one specification is created.

The [specification](../specs/005-metadata-persistence/spec.md) defines five
independently testable journeys: retained identity-isolated state, atomic and
concurrent changes, artifact-reference/lease ownership, controlled durable
upgrades and recovery, and alternative-provider qualification. It includes
23 acceptance scenarios, 14 edge cases, 24 functional requirements, ten logical
entity descriptions and eight measurable outcomes. Story independent tests
cover every requirement. The built-in
[requirements checklist](../specs/005-metadata-persistence/checklists/requirements.md)
passes all 16 specification-quality criteria, with no unresolved clarification
markers. This is generation-time quality review, not the scheduled clarification
stage or reviewer-owned custom checklist approval.

The specification preserves registry/request/authorization identity partitions,
all-or-nothing metadata visibility, consistent grouped reads, conditional
revisions, reconcilable uncertain commits, finite work and safe errors. Artifact
commit evidence comes from shared publication coordination; metadata cannot
establish cross-store atomicity or authorize physical deletion by itself.
Leases reject expired owners without claiming distributed coordination.
Schema compatibility, controlled upgrades, single-upgrader admission, interrupted
recovery and verified backup restoration remain explicit proof obligations.
Provider-private schemas/migrations/frameworks must not leak into consumers.

The master F-05 SQLite acceptance focus is retained as a bounded, real durable
qualification adapter during later implementation, distinct from production
SQLite delivery in original SPEC-03. An independent alternative fixture proves
logical interchangeability, not durable production support for another engine.
Generic certification remains F-07; production PostgreSQL, arbitrary NoSQL,
cross-engine transfer, HA, artifact storage and shared cache algorithms are not
implemented or promised here. Exact signatures, value limits, finite budgets,
schema paths and proof mechanics remain constrained planning decisions.

Only the specification, built-in quality checklist, README, this guide and
shared driver checkpoint change; the ignored local feature pointer is restored.
Provider/example guides, predecessor artifacts, charter/product specification,
architecture/ADR/diagrams, constitution/backlog, package/version policy, runtime
and test source, IaC and release procedures are unaffected because this stage
changes no existing API, dependency, command, operational procedure or supported
capability. No new architecture review is required for this requirements-only
change; substantial contract implementation/design still needs the normal gate.
Existing tooling checks validate the driver; product acceptance and OpenTofu
checks are not rerun for this documentation/checkpoint-only stage.

The checkpoint schedules **`clarify / ready`** for a separate invocation. The
feature PR remains draft. No plan, tasks, custom review, implementation,
qualification, schema upgrade, release, merge, infrastructure or deployment is
performed by this stage.

### F-05 metadata persistence clarification

The separately invoked `clarify` stage uses the recorded
`feature/005-metadata-persistence` branch and explicitly pinned
`specs/005-metadata-persistence`, retaining draft
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14).
Fetched main contains no new commits requiring branch reconciliation. The
installed `speckit-clarify` resolves the existing specification without
rerunning its generator or creating another feature. No extension hooks are
configured.

The [dated review](../specs/005-metadata-persistence/spec.md#clarifications)
finds all ten ambiguity/coverage categories clear: zero questions and no
requirement, acceptance or scope changes. Identity isolation, atomic groups,
consistent reads, revision conflicts, reconcilable uncertain commits,
artifact-evidence authority, reference/lease safety and controlled schema
recovery remain explicit. SQLite durable qualification and alternative-fixture
semantics remain distinct from production support and generic certification.
Exact signatures, value/page limits, timestamp precision, finite budgets,
reconciliation lifetime, schema paths and proof mechanics are constrained
planning decisions, not unresolved product decisions.

Built-in specification-quality revalidation remains **16/16 to 16/16**:
zero newly passing items, regressions or unchecked items. All checklist bytes
remain unchanged; no reviewer-owned custom approval or runtime evidence is
claimed. Only the spec's clarification section, README, this guide and shared
checkpoint change. Provider/example guides, predecessor artifacts, baseline
charter/product specification/architecture/ADR/diagrams, constitution/backlog,
compatibility policy and release/IaC guidance are unaffected: no existing API,
dependency, supported behavior, command or operational procedure changes.
No new architecture-agent review is required for this documentation-only stage;
product/.NET and OpenTofu acceptance are not rerun.

The checkpoint schedules **`plan / ready`** through a separate invocation.
PR #14 remains draft. No design artifacts, tasks, custom review, persistence
implementation, schema upgrade, qualification, release, merge, infrastructure
or deployment are produced by this clarification stage.

### F-05 metadata persistence planning

The separately invoked installed `speckit-plan` uses the same recorded branch
and explicit `SPECIFY_FEATURE_DIRECTORY=specs/005-metadata-persistence`.
The driver begins `plan / running` before setup. No generator or prior stage
is repeated, and no extension hooks are configured. Existing specification
and built-in checklist bytes remain unchanged.

The [plan](../specs/005-metadata-persistence/plan.md),
[research](../specs/005-metadata-persistence/research.md),
[logical model](../specs/005-metadata-persistence/data-model.md),
[API contract](../specs/005-metadata-persistence/contracts/metadata-api.md),
[recovery contract](../specs/005-metadata-persistence/contracts/recovery.md),
[acceptance matrix](../specs/005-metadata-persistence/contracts/acceptance.md)
and [validation quickstart](../specs/005-metadata-persistence/quickstart.md)
resolve the constrained planning details. BCL-only operational interfaces are
opt-in additions alongside the unchanged metadata marker, not new members on
existing providers. Typed atomic groups, snapshot reads, binary canonical keys,
conditional revisions, 24-hour persisted operation tickets and atomic receipts
prevent partial state and blind replay after reconciliation expiry.

Artifact publication requires a host-injected shared authority guard retained
until transaction settlement; metadata neither verifies bytes nor authorizes
physical deletion. Reference generations and lease tombstones protect stale
decisions, while the persisted time floor and final guarded decision define
expiry. Work/result/queue/receipt bounds and finite monotonic deadlines include
explicit uncertainty and retained ownership for non-preemptible native calls.

The proposed file-backed SQLite qualification adapter uses private
`Microsoft.Data.Sqlite`, parameterized SQL and checked WAL/FULL/foreign-key
settings. The private driver version/locks will be selected and assessed during
implementation; no dependency is added now. A separately implemented immutable
memory fixture proves only logical semantics. Host-side adapters reuse F-02
admission/cleanup and F-03 owner options without provider-to-Hosting references,
new Core behavior or a second lifecycle authority.

The 48 acceptance cases trace all 24 FRs, eight SCs, 23 story scenarios and
14 edge cases. They cover unchanged package-only consumer/old-marker binaries,
real child-process termination, one explicit v1-to-v2 upgrade, read-only
incompatible-schema inspection, single-upgrader/store exclusion and verified
quiescent backup/restore. The future metadata command is clearly labelled
unimplemented; SQLite process-crash evidence cannot establish power-loss
certification, production provider support, another engine, HA or generic F-07
qualification. Existing validation commands are regression obligations at
implementation, not product evidence from planning.

The required bounded `hoard-architecture-review` found no confirmed design
violations or unresolved implementation-blocking questions. It identifies
future binary, ownership/interleaving, crash/recovery and exact environment/
dependency evidence gaps; it ran no commands. Constitution checks pass before
research and after design without exceptions.

README and this guide reflect design status. Provider/example guides, existing
feature artifacts, baseline charter/product specification/architecture/ADR/
diagrams, constitution/backlog, compatibility policy, runtime/test/tooling
source, dependency manifests/locks, IaC and release procedures are unaffected:
this stage changes no existing API, command, package graph, supported behavior
or operational procedure. Their implementation updates remain later work.
Only existing repository-tool checks and design/link/scope checks are relevant
now; .NET product acceptance and mock OpenTofu checks are not rerun.

The checkpoint schedules **`checklist / ready`**, retaining draft
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14). No custom checklist
approval, tasks, implementation, schema operation, qualification, source release,
merge, infrastructure or deployment occurs in planning.

### F-05 metadata persistence requirements-quality checklists

The separately invoked installed `speckit-checklist` uses the recorded branch
and explicit `SPECIFY_FEATURE_DIRECTORY=specs/005-metadata-persistence`, after
the driver begins `checklist / running`. No extension hooks are configured.
It creates two standard-depth requirements-quality checklists for maintainer
and provider reviewers before implementation authorization:
[metadata contract](../specs/005-metadata-persistence/checklists/metadata.md)
and [recovery](../specs/005-metadata-persistence/checklists/recovery.md),
20 criteria each. They evaluate the written requirements, not delivered behavior.

Metadata scope covers canonical identity and authorization partitions, common
values, final-graph relationships, atomic groups/reads, concurrent revisions,
publication authority, reference generations, leases, pages, secret handling
and compatibility/qualification boundaries. Recovery scope covers operation
tickets and uncertain outcomes, finite budgets and retained work ownership,
schema admission, controlled upgrades, real crash boundaries, coherent backups,
restoration and attributable durability limits.

The user explicitly requests Copilot's assisted review and identification of
anything needing maintainer judgment. The assessment compares all 40 criteria
with the specification and seven design artifacts: each has written coverage,
with no unresolved requirements-quality finding, waiver or product decision
needing maintainer attention. Evidence is recorded in draft
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14). This is not independent
human inspection, formal checklist approval or passing implementation evidence.
All generated custom markers remain unchecked as required by the checklist
stage; the built-in 16/16 checklist and all existing design artifacts are
unchanged. Later implementation still requires reviewer approval or explicit
reviewer authorization; tasks and analysis may proceed without that approval.

Late native-call/guard ownership, reference/lease/ticket interleavings,
unchanged-consumer/old-binary compatibility and real SQLite crash/upgrade/restore
proof remain explicit implementation obligations, not unresolved design choices
or current support claims. README and this guide link the new artifacts and
record the assisted-review result. Provider/example guides, baseline product/
architecture/ADR/diagrams, constitution/backlog, compatibility/release policy,
existing feature artifacts, runtime/test/tooling sources, dependencies/locks
and IaC are unaffected: no API, behavior, package graph, command or operational
procedure changes. No new architecture review is required for checklist and
status-documentation additions; the planning review remains historical evidence.

The checkpoint schedules **`tasks / ready`**, retaining draft PR #14.
No task generation, analysis, implementation, formal custom checklist approval,
schema operation, qualification, release, merge, infrastructure or deployment
occurs in this invocation.

### F-05 metadata persistence task generation

The separately invoked installed `speckit-tasks` uses the recorded
`feature/005-metadata-persistence` branch and explicit
`SPECIFY_FEATURE_DIRECTORY=specs/005-metadata-persistence`, after the driver
begins `tasks / running`. Its setup resolves the absolute feature directory
and canonical task template. No before/after task extension hooks are configured.

The [task list](../specs/005-metadata-persistence/tasks.md) contains 83 unchecked
tasks: six setup, 11 foundational, 11 US1 retention/isolation, 13 US2 atomicity/
reconciliation, 11 US3 publication/reference/lease, 15 US4 upgrade/recovery,
ten US5 independent qualification, and six cross-cutting acceptance tasks.
All 24 FRs, eight SCs, 23 story scenarios, 14 edge cases and 48 MP cases have
implementation/focused-proof mappings. Direct prerequisites form an explicit
acyclic graph, including serialized evidence-helper/shared-file edits and
pre-change retained-binary provenance. File-disjoint test and independent
SQLite/memory lanes are identified; story dependencies are not disguised as
parallel work.

US1 is the suggested bounded record/identity/page MVP, not full qualification
or a runnable cache. Full F-05 implementation requires every story. Tests must
record intended red before accepted behavior, then attributable green;
concurrency and late ownership use controlled barriers, while durable cases
require actual parent-terminated children, confirmed exit and reopened state.
All 39 logical cases run against each independent fixture; SQLite additionally
requires nine durable cases. Memory reports those nine as explicitly
non-durable NotApplicable, never passing or waiving a logical obligation.

The existing specification, seven planning artifacts and built-in/custom
checklist bytes are unchanged. All 40 custom review markers remain unchecked;
the earlier assisted assessment is not formal approval. Task generation does
not evaluate/approve those checklists, perform cross-artifact analysis or
execute implementation/qualification. Read-only **`analyze`** is the next
separately authorized stage; implementation additionally waits for reviewer
approval or explicit reviewer authorization.

README and this guide link the task artifact and next gate. Provider/example/
quickstart guides, product/architecture/ADR/diagrams, compatibility/release
policy, constitution/backlog, prior features, runtime/test/tooling sources,
dependencies/locks and IaC are unaffected: this stage changes only planned work,
status documentation and checkpoint, not APIs, package edges, operational
behavior or supported capabilities. Implementation tasks explicitly update
their affected surfaces and require a fresh architecture review; the historical
planning review is not implementation acceptance. Draft
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) remains incomplete.
No schema operation, product scaffolding, release, package publication, merge,
infrastructure plan/apply or deployment occurs in task generation.

### F-05 metadata persistence cross-artifact analysis

The separately invoked installed `speckit-analyze` uses explicit
`SPECIFY_FEATURE_DIRECTORY=specs/005-metadata-persistence` after the driver
begins `analyze / running`. Its prerequisite check resolves the recorded
directory, specification, plan, tasks and supporting design documents.
No before/after analysis extension hooks are configured.

Read-only review of the specification, plan, tasks, logical model and three
contracts against constitution v1.0.0 finds no actionable duplication,
ambiguity, underspecification, inconsistency, constitutional conflict or
coverage gap. All 24 FRs and eight buildable SCs have implementation/focused
proof tasks (32/32, 100%); all 23 story scenarios, 14 edge cases and 48 MP cases
retain mappings. Every task has a requirement/story or shared acceptance/
workflow purpose. The 83-node graph has 107 direct edges, no unknown or missing
prerequisites and no cycles; retained-binary preparation precedes platform
changes and shared orchestrator edits remain serialized.

The [structured report](https://github.com/Stonefly-Labs/Hoard/pull/14#issuecomment-6329405510)
records zero findings and no proposed remediation. All 83 tasks, existing
design/specification artifacts and checklist bytes remain unchanged. The
built-in checklist stays 16/16; the two reviewer-owned custom checklists retain
all 40 unchecked markers. Neither the earlier assisted assessment nor analysis
supplies formal approval. The checkpoint schedules **`implement / ready`**,
but that separate invocation still requires reviewer approval or explicit
reviewer authorization before execution.

All 39 logical cases for both independent fixtures, nine additional SQLite
durable cases, real crash/upgrade/restore, late-work ownership, unchanged
consumer/retained-binary and package-boundary proof remain implementation
obligations. No future metadata command runs or gains a passing claim here.
README and this guide record the analysis result and remaining gate. Provider/
example/quickstart guides, baseline charter/product specification/architecture/
ADR/diagrams, prior features, constitution/backlog, compatibility/release policy,
runtime/test/tooling sources, dependencies/locks and IaC are unaffected:
analysis changes no requirement, design, API, package edge, command, operational
procedure or supported behavior. Historical planning architecture review
remains historical; implementation requires the fresh review in its tasks.
Existing repository-tool and artifact-integrity checks apply; .NET product
acceptance and mock OpenTofu checks are not rerun for status/checkpoint-only
changes. Draft [PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) stays
incomplete; no implementation, checklist approval, schema operation,
qualification, source release, merge, infrastructure or deployment occurs.

### F-05 assisted checklist review

The user reiterates that Copilot should run the existing checklists and
highlight only decisions needing maintainer attention. This separately
requested review follows the earlier features' assisted-review pattern; it
does not regenerate checklists, self-approve them during implementation or
advance a scheduled driver stage.

Copilot evaluates all 40 criteria against the specification and seven planning
artifacts at `72f1078`. The
[metadata checklist](../specs/005-metadata-persistence/checklists/metadata.md)
and [recovery checklist](../specs/005-metadata-persistence/checklists/recovery.md)
now record **20/20 and 20/20 satisfied**, with grouped criterion-level evidence.
There is no unresolved requirements-quality finding, waiver or decision needing
maintainer attention. Markers record the requested reviewer assessment, not
independent human inspection, implementation completion or durability evidence.
The custom requirements-quality review gate is satisfied.

The checkpoint remains **`implement / ready`**, all 83 tasks remain unchecked
and the specification, seven planning artifacts and built-in checklist remain
unchanged. No driver stage is begun or finished. Actual transaction/reference/
lease interleavings, finite late-work ownership, independent package/old-binary
compatibility and SQLite crash/upgrade/backup recovery remain mandatory proof
obligations for the next separately authorized implementation invocation.

README and this guide reflect the review. Provider/example/quickstart guides,
baseline charter/product specification/architecture/ADR/diagrams, prior features,
constitution/backlog, compatibility/release policy, runtime/test/tooling sources,
dependencies/locks and IaC guidance are unaffected: review markers/evidence
change no requirement, design, API, dependency boundary, command, operation or
capability. No additional architecture review or product/.NET/IaC acceptance is
warranted for this documentation-only change. Draft
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) remains incomplete;
no implementation, schema operation, qualification, publication, merge,
infrastructure action or deployment occurs.

### F-05 implementation setup

The separately invoked `speckit-implement` runs on the recorded feature branch
with `SPECIFY_FEATURE_DIRECTORY=specs/005-metadata-persistence`. The existing
review gate passes: metadata 20/20, recovery 20/20, built-in requirements 16/16.
There are no pre/post implementation extension hooks.

T001..T006 establish a deterministic clock/owned barrier harness, twelve
fail-closed evidence-tool tests, isolated locked build/package preparation and
the retained marker/registration binary from merged pre-F-05 main
`10ce78851b97b02bd83a8ef7da7ffdc2381d6519`. Private evidence freezes binary,
recipe, dependency, lock, source and package hashes before public API changes.
The SQLite scaffold privately pins Microsoft.Data.Sqlite 10.0.13; exact
native/transitive packages and license/advisory review are in the
[research](../specs/005-metadata-persistence/research.md).

The [metadata quickstart](../specs/005-metadata-persistence/quickstart.md)
documents preparation-only selectors. They explicitly report
`qualification: false`; default full mode fails while runtime case evidence
is missing. Initial missing-runner red and a runtime mutation that accepts
failed cases are both observed; the unmodified verifier passes all twelve
tooling cases. No operational provider, schema, L/D qualification, cache,
release or deployment follows from compiling/packing scaffolds.

The driver remains **`implement / running`**. Continue through all remaining
tasks in this invocation unless genuinely blocked; do not call `finish` or
start convergence from setup. Requirements/checklist bytes remain unchanged.
Provider/example guides, architectural/product diagrams, release/IaC guides
and previous feature artifacts are unaffected by setup because there is no
new operational API, host behavior or supported capability.

### F-05 operational metadata implementation

The full implementation continues beyond setup through all functional and
acceptance obligations in the 83-task feature.
`Hoard.Abstractions.Metadata` now supplies opt-in store/schema/publication
contracts without changing `IMetadataProvider`. Independently packed SQLite and
copy-on-write memory fixtures preserve exact caller identities, atomic groups/
receipts, bounded snapshot reads/keyset pages, references, fenced leases and
explicit admission. HostAdapters uses existing configured F-02/F-03 composition:
one selected authority, inert registration, no routes or disabled I/O, failure
blocks readiness, no fallback or second lifecycle.

```bash
# Full fixture qualification, immutable locks, retained owner-private evidence.
bash scripts/validate-metadata.sh
# Focused proof; rebuild/verify prerequisites, explicitly not full qualification.
bash scripts/validate-metadata.sh --phase logical
bash scripts/validate-metadata.sh --phase recovery
bash scripts/validate-metadata.sh --phase packages
```

Use `--update-locks` only for intentional source/package/dependency changes, then
review locks and replay the default command independently. `--evidence` accepts
a fresh destination outside Git with an existing parent; the runner prints the
retained location. Proofs and synthetic databases/captures/binaries stay private.
Each subprocess is bounded to ten minutes, with stricter operation/admin
budgets. Only the exact owned temporary workspace and known children are cleaned
up. Never remove a live database/WAL/owner file as recovery.

The full manifest accounts for all 96 provider/case entries: 39 logical cases
per implementation, nine additional SQLite durable cases and explicit
`NotApplicable: non-durable fixture` for memory. It records actual local OS/
runtime/filesystem/driver/native versions, effective WAL/FULL/foreign-key/busy
settings, proof hashes/durations, all eight real signal-terminated crash
boundaries, isolated verified-v1 restore, unchanged consumer/common binaries,
frozen marker binary compatibility and permitted/forbidden actual package scans.
Runtime mutations must cause the intended assertion failure, not compilation
failure, before the same repaired test passes.

The [quickstart](../specs/005-metadata-persistence/quickstart.md),
[provider guide](PROVIDERS.md#opt-in-metadata-operations-and-fixture-qualification)
and [recovery guide](../specs/005-metadata-persistence/contracts/recovery.md)
document exact interfaces, ticket reconciliation/expiry, explicit upgrades,
compatible backup readers, artifact reconciliation and cleanup ownership.
File permissions and OS ownership apply only to private local fixture data.
Native timeout cannot preempt I/O: late work retains its connection/lock/guards;
30-second incomplete cleanup remains explicit and may require process termination.
No physical-deletion permission or distributed safety follows from metadata.

The product charter/specification, baseline architecture/ADR and product
diagrams remain unchanged: their production topology and centralized cache
responsibilities are not delivered by test fixtures. Release/IaC/cloud/UI guides,
prior feature artifacts and the compile-only host source remain unaffected:
no deployment, secret permissions, protocol/UI operation, new listener,
production provider or published package is added.

Complete update-lock and independent default locked qualification pass:
59 common tests per provider, 87 applicable case passes and nine explicit
memory durability exclusions. All eight M/U crash boundaries, R0/R1 restore
installation interruptions, native cleanup ownership, unchanged consumer/common
binaries, frozen marker compatibility and seven real package graphs pass.
The final locked foundation/lifecycle/configuration/discovery commands and
76 repository tooling tests pass; every tracked lock hash is unchanged.

The [plan](../specs/005-metadata-persistence/plan.md#implementation-evidence)
records exact commands/results, the measured macOS/APFS configuration, all three
architecture findings and their verified corrections, and the final requirement
audit. No implementation extension hooks are configured. The durable driver
handoff schedules the separately invoked `converge` stage. Draft
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) remains incomplete until
convergence and finalization; feature merge, source release and dependency
completion remain later gates. This invocation runs none of them.

### F-05 convergence

The installed convergence stage assessed all 24 functional requirements, eight
outcomes, 23 story acceptance scenarios, 14 edge cases, 83 existing tasks, eight
numbered integration decisions and eight constitution principles against the
current implementation. It found one HIGH partial gap, F1, under FR-010/FR-015
and T026/T036 (MP-08): a query/epoch-matching continuation with null SQLite
`LastKey` or memory `After` reaches a null dereference, producing
`InternalFailure/OperatorRecovery` instead of `InvalidInput/CorrectInput`.

An SDK-interactive probe against the freshly packaged, unchanged providers
reproduces that outcome in both implementations; an ordinary valid query
continues to succeed afterward. No application or test source was edited.
The stage appended only
[Phase 9 / T084](../specs/005-metadata-persistence/tasks.md#phase-9-convergence),
requiring bounded decoded-field validation and paired malformed/valid cursor
regressions. The original task bytes and all 83 completions remain intact;
specification, plan, constitution and reviewer-owned checklists are unchanged.
There are no convergence extension hooks.

| Convergence check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 76 tests |
| `bash scripts/validate-metadata.sh` | Passed existing full locked qualification and formatting/analyzers: 59 common tests per provider, 87 applicable entries and nine explicit memory durability exclusions; locks unchanged |
| `dotnet fsi --quiet --readline-` with the fresh fixture assemblies and query/epoch-matching null-key continuations | Reproduced F1 in both providers; subsequent valid queries passed |
| SHA-256 append-only artifact checks | Specification/plan unchanged; original tasks byte-identical, exactly one new unchecked T084 |

Fresh qualification retains source commit
`7dcf5090f426ed8088e1b6ba5ec15d11c6e963d8` and source/lock fingerprint
`2594b90d9871c0a0555e2e5c590ea77dab461c543dbe50ededa5dda552922f5a`.
It verifies the existing eight M/U crash boundaries, R0/R1 restore interruptions,
native cleanup ownership, seven package graphs, unchanged consumers/marker
binary and both runtime mutation pairs. This passing existing suite does not
waive F1 or establish clean convergence.

The outcome is `tasks_appended`; the next separately invoked stage is
**`implement`**, not `finalize`. Draft
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) remains incomplete until
T084, fresh convergence and finalization pass. The driver updates only this
handoff documentation and its checkpoint outside the append-only assessment.
Provider/example/API/recovery guides and product/architecture diagrams remain
unaffected: no API, supported behavior, operational procedure, dependency or
production capability changed. No merge, tag, release, infrastructure operation
or deployment ran.

### F-05 T084 implementation correction

The returned implementation stage completes T084 only. SQLite `LastKey` and
memory `After` now use null-safe bounded checks before hex decoding, preserving
the existing complete-query/schema/epoch/size binding and finite decode limits.
Six common theory variants mutate every decoded field (null, omitted,
wrong-type, empty, odd-length and invalid hex); each rejection must return
`InvalidInput/CorrectInput/Page`, allow the original cursor to resume, and
preserve remaining/full dataset traversal.

Both independently packaged providers reproduce the null/omitted
`InternalFailure` assertion before repair. The corrected focused logical gate
passes 65 tests per provider. The full independent locked metadata gate passes
formatting/analyzers, 65 common tests per provider, all 87 applicable entries,
nine explicit memory D exclusions, and existing crash/restore/native-ownership,
package/old-binary/unchanged-consumer/runtime-mutation proofs. Repository tooling
passes 76 tests. Four downstream locks change only local fixture package
content hashes; no dependency identity/version or platform/third-party hash
changes, and default replay preserves the reviewed locks.

[Exact commands and attribution](../specs/005-metadata-persistence/plan.md#t084-malformed-continuation-correction)
include both red runs and the tested working-source fingerprint. README,
plan/tasks, quickstart and acceptance evidence are updated. Provider/API/model/
recovery/example guidance and product/architecture diagrams are unaffected:
they already require malformed-cursor refusal, and no public API, operational
procedure, dependency or shared boundary changes. The earlier architecture
review remains applicable; no new substantial provider-boundary change occurs.
The specification, constitution and reviewer-owned checklists are unchanged;
no implementation hooks exist.

All 84 tasks are complete. The next separately authorized stage is fresh
**`converge`**, not finalize or merge; draft
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) remains incomplete until
convergence and finalization. No merge, tag, release, package publication,
infrastructure operation or deployment ran.

### F-05 fresh convergence: stored-page corruption classification

The separately invoked installed `speckit-converge` assesses the current
implementation after T084 against all 24 functional requirements, eight
outcomes, 23 story acceptance scenarios, 14 edge cases, 84 existing tasks,
eight numbered integration decisions and eight constitution principles.
The malformed-continuation correction passes its common regressions in both
independently packaged providers. One HIGH partial gap remains under
FR-010/FR-013, SC-007 and T024/T026/T036 (MP-21/22).

SQLite page reads deserialize and validate persisted payloads directly.
A syntactically valid registry payload with `Label: null` reaches the generic
caller-input exception mapping and returns `InvalidInput/CorrectInput/Page`.
The identical stored record in a grouped read correctly returns
`CorruptState/OperatorRecovery/Read`. Consumers therefore receive incorrect
caller-correction guidance for damaged stored data. The existing
corruption-aware decoder is the appropriate shared mechanism; globally
reclassifying input failures would break valid malformed-query rejection.

An SDK-interactive probe against the freshly packed, unchanged SQLite fixture
reproduces both results. Malformed JSON is a positive classification control:
both read paths report `CorruptState/OperatorRecovery`. Restoring the original
synthetic payload after each probe makes the same valid grouped read and page
succeed; fixture cleanup also completes. No application or test source is
edited. Private synthetic data, captured output and binaries stay outside Git.

The assessment appends only
[Phase 10 / T085](../specs/005-metadata-persistence/tasks.md#phase-10-convergence),
requiring corruption-aware page decoding and paired structural/value/JSON
corruption, valid-page and caller-input regressions. A SHA-256 prefix comparison
confirms every original task byte and all 84 completions are unchanged.
Specification, plan, constitution and reviewer-owned checklists also remain
unchanged. No pre/post convergence hooks exist.

`$PRIVATE_EVIDENCE` below represents this invocation's owner-private parent
outside Git; personal paths and raw evidence are not committed.

| Convergence check | Result |
| --- | --- |
| `bash scripts/validate-metadata.sh --evidence "$PRIVATE_EVIDENCE/metadata-convergence"` | Passed full locked qualification and formatting/analyzers: 65 common tests per provider, 87 applicable entries and nine explicit memory durability exclusions; locks unchanged |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 76 tests |
| `DYLD_LIBRARY_PATH="$PWD/runtimes/osx-arm64/native" dotnet fsi --quiet --readline-` from the fresh package consumer output, with the bounded synthetic corruption probe on standard input | Reproduced F1; malformed-JSON classification, restored valid reads/pages and cleanup controls passed |
| SHA-256 artifact and source/lock comparison | Original tasks prefix, specification, plan and checklists unchanged; exactly one new unchecked T085; tested source/lock fingerprint unchanged |
| `git diff --check` | Passed |

The full manifest attributes execution to source commit
`50a16a3f54b7a1a75d82ca8905f36742e27c0165` and source/lock fingerprint
`41ef899b40bd4017c3be0973de1bb66e93a81ca7dae3b9ed2cf064f1072b6c1a`.
Its measured configuration remains macOS 26.5.0/APFS, .NET 10.0.7,
Microsoft.Data.Sqlite assembly 10.0.13.0 and native SQLite 3.53.3, with checked
WAL/FULL/foreign-key/busy-timeout-zero settings. Existing eight M/U crash
boundaries, R0/R1 restore interruptions, native cleanup ownership, seven actual
package graphs, unchanged consumer/common binaries, frozen marker compatibility
and both runtime mutation pairs pass. Existing-case success does not resolve
F1 or establish clean convergence. Earlier platform-wide regression results
remain historical; they are not claimed to have been repeated in this stage.

The outcome is **`tasks_appended`** and the next separately invoked stage is
**`implement`** for T085, not finalize or merge. Draft
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) remains incomplete until
the correction, fresh convergence and finalization pass. The driver updates
only README, this guide and its checkpoint outside the append-only assessment.
Provider/API/model/recovery/acceptance/quickstart/example guides and product/
architecture diagrams are unaffected: convergence changes no intended API,
operational procedure, dependency or supported production capability. No new
substantial boundary change requires another architecture review in this stage.
No merge, tag, release, package publication, infrastructure operation or
deployment ran.

### F-05 T085 stored-page corruption correction

The returned implementation stage completes T085. SQLite pages now reuse the
existing bounded corruption-aware record decoder used by exact/grouped reads.
The decoder checks canonical stored-key equality in both paths. Only persisted
JSON/record validation becomes `CorruptState/OperatorRecovery`; caller query/
continuation validation and final result-size failures retain
`InvalidInput/CorrectInput`. No global exception translation changes.

The new packaged MP-21 regression reproduces the null-label failure before
repair: expected `CorruptState`, actual `InvalidInput` (65 pass, one fails).
Five SQLite-specific shapes cover null label/revision, oversized label,
malformed JSON and mismatched identity after a valid first row. Both page and
group reads fail completely with safe phase/retry results, preserve the damaged
payload and recover the exact original encoded page after synthetic restoration.
Both fixture selections also pass the common page-corruption assertion.
The existing malformed-cursor theory and tightened oversized-result controls
preserve caller-correction guidance and valid traversal.

Focused locked replay and full locked qualification pass 66 tests per provider;
the full run passes formatting/analyzers, 87 applicable entries and nine explicit
memory D exclusions, actual crash/restore/native ownership, seven package graphs,
unchanged consumers/common binary, frozen marker and runtime mutation pairs.
Repository tooling passes 76 tests; `git diff --check` passes. Four downstream
locks change only local SQLite/HostAdapters content hashes, without identity,
version, memory/Abstractions or third-party changes. Default replay preserves all
88 reviewed locks. [Exact commands and attribution](../specs/005-metadata-persistence/plan.md#t085-stored-page-corruption-correction)
also record the intermediate lock-refresh/test-comparison correction.

README, plan/tasks, quickstart and acceptance evidence are updated. Provider/API/
model/recovery/example guides and product/architecture/ADR diagrams are
unaffected: existing corruption requirements, public APIs, operational procedures,
package boundaries and production support claims are unchanged. Earlier platform
regression results remain historical, not rerun for this fixture-private change.
The previous architecture review remains applicable without a new substantial
boundary change. Constitution, specification and reviewer-owned checklists are
unchanged; no pre/post implementation hooks exist. Backlog/governance, prior
features, release/cloud/UI/IaC guidance are unaffected; no new permissions,
schema-repair procedure or deployment behavior is introduced.

All 85 tasks are complete. The next separately authorized stage is fresh
**`converge`**, not finalize or merge. Draft
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) remains incomplete until
convergence and finalization. No merge, tag/release, package publication,
infrastructure operation or deployment ran.

### F-05 fresh convergence after T085

The installed append-only assessment checks all 24 functional requirements,
eight buildable outcomes, 23 story scenarios, 14 edge cases, 12 grouped plan
decisions, all 85 existing tasks and eight constitutional principles against
current scoped code. T084/T085's malformed-continuation and returned-page record
decoding corrections are implemented. Two **HIGH partial** gaps remain:

| Finding | Current evidence | Required follow-up |
| --- | --- | --- |
| F1: filtered pages hide corrupt query dimensions | `SqlitePages.cs` filters authorization partitions using `json_extract` before decoding candidate records. A stored entry with null `Identity.AuthorizationPartition` produces `CorruptState/OperatorRecovery/Read` on exact read, but a successful empty page for its original partition. | T086: corruption-aware bounded page selection, with regression coverage and an audit of the analogous aggregate/lease predicates; preserve legitimate foreign-scope absence and query isolation. |
| F2: committed receipt retrieval lacks validation | `SqliteOperations.cs` deserializes stored receipts without the full receipt validation used during schema integrity checks. A persisted receipt with null `Revisions[0].Target` returns successful `MetadataResolution.Committed`. | T087: bounded persisted receipt/state validation and ticket binding before replay/reconciliation, with safe corruption outcomes and focused regressions. |

One bounded diagnostic executes against the fresh package consumer's binaries,
using only a private synthetic database seeded by the existing crash runner.
Both findings are runtime observations, not deductions from checked tasks.
The diagnostic verifies the damaged entry remains unchanged, restores both
synthetic payloads, recovers the original valid page and commit receipt, and
passes final schema integrity. No listener or repository application-code
change is involved. F1's aggregate/lease audit and F2's other malformed/oversized/
ticket-binding cases are implementation obligations, not additional reproduced
paths. There are zero missing, contradicts or unrequested findings and no
requirement waiver.

`$PRIVATE_EVIDENCE` represents the owner-private session evidence parent outside
Git. The F# diagnostic is retained there, not added to the repository.

| Exact command / check | Result |
| --- | --- |
| `bash scripts/validate-metadata.sh --evidence "$PRIVATE_EVIDENCE/metadata-convergence"` | Passed full locked qualification and formatting/analyzers: 66 common tests per provider, 87 applicable passes and nine explicit memory D exclusions |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 76 tests |
| `DYLD_LIBRARY_PATH="$PWD/runtimes/osx-arm64/native" dotnet fsi --quiet --exec "$PRIVATE_EVIDENCE/metadata-corruption-probe.fsx"` from the fresh package consumer output | Reproduced F1/F2; valid-page/original-receipt restoration and final integrity controls passed |
| Artifact/source/lock integrity comparison | Original task prefix, specification, plan and all checklist bytes unchanged; exactly two new unchecked tasks, T086/T087; qualified source fingerprint and all 88 locks unchanged |
| `git diff --check` | Passed |

The full manifest identifies source commit
`bbdf328ca14d8971e123c5da704a1b3fd3c90d69` and source/lock fingerprint
`68215c83a4b41ed5b8f3c10976aa7519e71fc8d82cbd1e657a30cec30e3a513d`.
Configuration remains macOS 26.5.0/APFS, .NET 10.0.7, driver 10.0.13.0 and
native SQLite 3.53.3, with checked WAL/FULL/foreign-keys/busy-timeout-zero.
All existing eight M/U process-stop boundaries, R0/R1 restore interruptions,
native cleanup ownership, seven package graphs, unchanged consumer/common
binaries, frozen marker and both assertion-level runtime mutation pairs pass.
Passing existing cases does not resolve F1/F2. Earlier platform-wide regression
results remain historical and were not repeated for this append-only assessment.

The outcome is **`tasks_appended`** under
[Phase 11](../specs/005-metadata-persistence/tasks.md#phase-11-convergence).
The next separately invoked stage is **`implement`** for both T086 and T087,
then fresh convergence; keep
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) draft.
No pre/post convergence hooks exist. Outside the assessment, the driver updates
only README, this guide and its checkpoint. Provider/API/model/recovery/
acceptance/quickstart/example guides and product/architecture/ADR diagrams are
unaffected: no intended API, operational procedure, dependency boundary or
production capability changes. Their contracts still apply; the new tasks
record implementation gaps, not weaker guarantees. The existing architecture
review remains historical and no new substantial boundary change occurs here.
Governance/backlog, prior features, release/cloud/UI/IaC guidance and permissions
are unaffected. No implementation, merge, tag/release, package publication,
infrastructure operation or deployment ran.

### F-05 T086/T087 filtered-page and receipt corrections

The separately invoked implementation completes both Phase 11 tasks and all
87 feature tasks. SQLite now decodes bounded ordered candidates before applying
payload-based authorization/aggregate/lease filters. Every scanned candidate
consumes the original deadline; only page-sized results and matching lookahead
are retained. Five package-only theory variants prove complete corruption
failure, unchanged damaged payloads, exact restored pages and one-row traversal
that excludes interleaved foreign scopes while preserving healthy empty scopes.

Persisted operation decoding is shared by runtime replay/reconciliation and
schema integrity: native types, ticket bounds, closed state, fingerprint shape,
bounded receipt bytes, public receipt validation and ticket equality are checked
before returning success. Fourteen malformed, oversized, wrong-ticket or
invalid-state/fingerprint forms return sanitized operator-recovery failures with
the original ticket and originating phase. Damaged state and committed aggregate
contributions remain unchanged; synthetic restoration returns the original
receipt without duplicate effects. The memory implementation is unchanged.

`$PRIVATE_EVIDENCE` represents this invocation's owner-private evidence parent
outside Git; raw synthetic databases, binaries and canary captures are not tracked.

| Exact command / check | Result |
| --- | --- |
| `bash scripts/validate-metadata.sh --phase logical --evidence "$PRIVATE_EVIDENCE/red"` | Intended runtime red: six new SQLite failures and 66 passes against unchanged packages |
| `bash scripts/validate-metadata.sh --phase logical --update-locks --evidence "$PRIVATE_EVIDENCE/logical"` | Passed 72 tests per provider and unchanged consumers; not full qualification |
| `bash scripts/validate-metadata.sh --evidence "$PRIVATE_EVIDENCE/qualified"` | Passed complete locked qualification and formatting/analyzers: 72 tests per provider, 87 applicable entries and nine memory D exclusions |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 76 tests |
| Source/lock/proof comparison | Current source and retained proof hashes verified; four locks change only local SQLite/HostAdapters hashes; all 88 locks preserved by locked replay |
| `git diff --check` | Passed |

The [plan](../specs/005-metadata-persistence/plan.md#t086t087-filtered-page-and-receipt-corruption-corrections)
records exact source/environment attribution, the six passing pre-repair memory
controls and the unchanged architectural/regression scope. Existing actual
crash/restore/native ownership, seven package graphs, unchanged consumer/common
binaries, frozen marker and runtime mutation proof pass again. Earlier separate
platform regression commands remain historical, not newly claimed execution.

README, tasks, plan, quickstart and acceptance evidence are current.
Provider/API/model/recovery/example guides and baseline product/architecture/ADR
diagrams are unaffected because the existing contracts, operations, package
boundaries and production support scope do not change. The prior architecture
review remains applicable; no new substantial dependency, lifecycle, authority,
reference or lease boundary is introduced. Governance/backlog, earlier features,
release/cloud/UI/IaC guidance and permissions are unaffected. Specification,
constitution and reviewer-owned checklists remain unchanged; no implementation
hooks exist. Fresh **`converge`** is the next separate stage, then finalization.
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) remains draft. No merge,
tag/release, package publication, infrastructure plan/apply or deployment ran.

### F-05 clean convergence

The subsequent installed `speckit-converge` assessment finds no actionable
missing, partial, contradictory or unrequested work. It checks all 24 functional
requirements, eight buildable success criteria, 23 story acceptance scenarios,
14 edge cases and all 87 existing tasks, including the resulting T084..T087
behavior. Twelve grouped plan decisions and all eight constitution principles
are assessed against the current implementation and fresh attributable proof.
No new task or empty convergence phase is appended; `tasks.md` is byte-for-byte
unchanged. No implementation, requirement, design or checklist approval changes.

The assessment covers additive BCL-only contracts and canonical encoding;
independent SQL/native and immutable-root state machines; atomic
revision/ticket/receipt, snapshot/page, authority/reference/lease behavior;
bounded admission and late ownership; configured F-02/F-03 adapters; schema,
crash and backup/restore recovery; package/binary boundaries; and fail-closed
qualification/documentation. Existing out-of-scope production, F-07,
multi-node, power/device-loss and other-engine/filesystem claims remain excluded.

`$PRIVATE_EVIDENCE` denotes the existing owner-private evidence parent outside
Git. The full run independently verifies all 96 provider/case entries:
87 applicable passes and nine explicit memory durability exclusions, with no
applicable failure or skip. Source/lock fingerprint
`29971e15fbeebde654bad140c1801f840c50018f4b507deaf50243fd5818cb24`
matches the current source; every proof/package hash and all 88 locks are
independently checked. Measured scope remains macOS 26.5.0/APFS, .NET 10.0.7,
driver 10.0.13.0 and native SQLite 3.53.3 with checked WAL/FULL/foreign keys/
busy-timeout-zero.

| Exact command / check | Result |
| --- | --- |
| `bash scripts/validate-metadata.sh --evidence "$PRIVATE_EVIDENCE/metadata-converge"` | Passed complete locked qualification and formatting/analyzers; 72 common tests per provider, all 87 applicable entries and nine memory D exclusions |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 76 tests |
| Independent manifest/source/lock verification | Passed current fingerprint, all proof/package hashes and unchanged 88-lock inventory |
| Additional freshly packaged SQLite corruption probe | Six wrong-type/unknown option discriminators correctly return `CorruptState/OperatorRecovery` for grouped reads, pages, replay and reconciliation; damaged rows stay unchanged and restored original records/receipts and final integrity pass |
| `git diff --check` | Passed |

Full qualification repeats all eight M/U process stops, R0/R1 interrupted
restore installations, native-stall ownership, backup/compatible restore,
seven actual package graphs, unchanged consumer/common binaries, frozen
pre-F-05 marker compatibility and both runtime assertion-failure/green pairs.
Earlier separate foundation/lifecycle/configuration/discovery commands remain
historical, not newly claimed executions. The installed stage has no pre/post
extension hooks.

README and this guide record the clean result and next gate. Spec, plan,
contracts, tasks, constitution, all checklist bytes, product/test/tooling sources
and locks remain unchanged. Provider/example/compatibility/recovery guides and
baseline product/architecture/ADR diagrams are unaffected: this assessment
changes no API, behavior, dependency, operational procedure or support scope.
The existing architecture review remains applicable; no new substantial
boundary change requires another review. Earlier feature artifacts, governance/
backlog and release/cloud/UI/IaC guidance and permissions are unaffected.

The next separately invoked stage is **`finalize`**.
[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) stays draft; clean
convergence is not finalization, feature completion or a merge request.
No merge, tag/release, package publication, infrastructure plan/apply, cloud
mutation or deployment ran.

### F-05 finalization

The separately invoked finalization stage uses the recorded
`feature/005-metadata-persistence` branch and explicit
`SPECIFY_FEATURE_DIRECTORY=specs/005-metadata-persistence`, after the driver
records `finalize / running`. All 87 implementation tasks are complete, fresh
convergence is clean, and the built-in 16/16 and reviewer-owned 40/40 checklist
assessments remain unchanged. All 24 requirements, eight outcomes, 23 story
scenarios and 14 edge cases retain their implementation/proof mappings.

The [implementation architecture reviews](../specs/005-metadata-persistence/plan.md#implementation-evidence)
remain applicable. Their restore-installation, lifecycle-stop and original-ticket
reconciliation findings were corrected and re-reviewed, with runtime proof.
T084..T087 subsequently change fixture-private validation, not public signatures,
dependency direction, lifecycle, publication authority or reference/lease
algorithms. Finalization changes no implementation boundary, so it does not
require another architecture review.

`$PRIVATE_EVIDENCE` below represents this invocation's existing owner-private
evidence parent outside Git; raw databases, binaries and synthetic captures are
not committed.

| Exact command / check | Result |
| --- | --- |
| `bash scripts/validate-metadata.sh --evidence "$PRIVATE_EVIDENCE/f05-finalize-evidence"` | Passed complete locked qualification and formatting/analyzers: 72 common tests per provider, 87 applicable entries and nine explicit memory durability exclusions |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 76 tests |
| Independent manifest/source/lock verification | Passed every proof/package hash, current source fingerprint, eight confirmed crash exits, seven package graphs and all 88 unchanged locks |
| `git diff --check` | Passed |

The final manifest attributes source commit
`9bb288b2234341695599a1c2536d8e88209486de` and fingerprint
`29971e15fbeebde654bad140c1801f840c50018f4b507deaf50243fd5818cb24`.
Measured scope remains macOS 26.5.0/APFS, .NET 10.0.7,
Microsoft.Data.Sqlite assembly 10.0.13.0 and native SQLite 3.53.3, with checked
WAL/FULL/foreign-keys/busy-timeout-zero settings. Full acceptance repeats M0..M2,
U0..U4, R0/R1 restore interruptions, native ownership, compatible backup/restore,
unchanged consumer/common binaries, the frozen marker binary and both runtime
red/green pairs. Separate foundation/lifecycle/configuration/discovery results
remain historical; finalization does not claim new executions of those commands.

README, this guide and feature plan/task/quickstart status now record the merge
handoff. Provider, API/model/recovery/acceptance and CustomHost guidance already
describe the implemented fixture interfaces, commands, reconciliation, recovery
and limits; no additional change is needed because finalization changes none of
those behaviors. Baseline charter/product specification/architecture/ADR diagrams,
earlier features, governance/backlog, release/cloud/UI/IaC guides and permissions
are unaffected: no production provider, endpoint, runtime, deployment or new
operational procedure is delivered. Specification, constitution, checklists,
product/test/tooling sources and locks remain unchanged.

[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) is ready for maintainer
review and merge using the repository template. `finish --pr 14` records
**`await_merge / ready`**, not feature completion or dependency eligibility.
After the maintainer merges, a separate invocation must verify that merge and
publish `v0.0.5-alpha` at its exact merge commit before recording completion.
No merge, tag/release, package publication, infrastructure plan/apply, cloud
mutation or deployment runs in finalization.

### F-05 merge completion and alpha source release

[PR #14](https://github.com/Stonefly-Labs/Hoard/pull/14) merged into `main` at
`81e2e8d41e08aafc9e89f388dab78e7509227dd5`. The separately invoked
`await_merge` stage verifies that exact commit in fetched `origin/main`, all
87 completed tasks, and the merged finalization, checklist and architecture
evidence above. This progress/docs-only stage changes no product code or
dependency; full metadata and earlier platform acceptance remain historical
evidence, not new executions.

The stage starts `chore/spec-progress-f-05` from fetched main before `begin`.
Its running checkpoint is committed/pushed as `eefbd1d` in draft
[PR #15](https://github.com/Stonefly-Labs/Hoard/pull/15), preserving a clean
worktree and durable recovery point before tagging. Under the bounded standing
authorization, the installed `hoard-release` skill publishes
[`v0.0.5-alpha`](https://github.com/Stonefly-Labs/Hoard/releases/tag/v0.0.5-alpha)
at the exact feature merge, not the progress branch tip.

| Exact command / check | Result |
| --- | --- |
| `python3 scripts/release.py v0.0.5-alpha` | Passed; valid prerelease |
| `python3 -m unittest discover -s tests/tooling -v` | Passed all 76 tests |
| `git merge-base --is-ancestor 81e2e8d41e08aafc9e89f388dab78e7509227dd5 origin/main` | Passed |
| `python3 scripts/release.py v0.0.5-alpha --check-main` | Passed; exact merge commit |
| `gh run watch 39730092661 --exit-status --interval 3` | Passed; [Source release run](https://github.com/Stonefly-Labs/Hoard/actions/runs/39730092661) succeeded at the exact merge |
| Release/tag/archive verification | Passed non-draft prerelease, generated PR-linked notes and changelog, annotated remote tag, ZIP commit comment and four exact-merge file comparisons in each automatic archive |
| `git diff --check` | Passed |

The annotated tag object is `f890f2d1f6938751a6e6f64b9815235829cd399c`;
its remote peeled commit is the feature merge above. Both GitHub archive roots
identify that tag object; the ZIP comment identifies the full merge commit.
README, checkpoint, task list and public metadata values match the exact
merge's bytes in both archives. Verification holds downloaded archives only
in memory; no archives, databases, build outputs or credentials enter Git.

Only after publication verification does `finish` independently verify the
remote annotated tag and GitHub prerelease and record F-05 complete with its
`release_tag` and `release_url`. The completion checkpoint and documentation
are shared through PR #15, which must merge before a later invocation can
start the next **`specify`** stage. This invocation starts no new specification
and does not merge that PR.

README and feature plan/task/quickstart status now record the verified handoff.
Provider/API/model/recovery/acceptance and CustomHost guides, baseline product
intent/architecture/ADR diagrams, constitution/backlog, predecessor artifacts,
release/cloud/UI/IaC guidance and permissions are unaffected: no implementation,
signature, package edge, operational procedure or support scope changes.
No new architecture review is needed for this progress/docs-only scope.
Specification and reviewer-owned checklists remain unchanged. This source
release publishes no runtime binaries, packages or containers and performs no
deployment, infrastructure plan/apply, cloud mutation or governance change.

### F-06 artifact storage specification

The F-05 completion checkpoint merged through
[PR #15](https://github.com/Stonefly-Labs/Hoard/pull/15). The separately invoked
`specify` stage fetches `origin/main`, verifies the shared checkpoint and ratified
constitution already merged, and starts `feature/006-artifact-storage` from that
main. The driver pins the exact master F-06 prompt and independent directory
`specs/006-artifact-storage`. The installed `speckit-specify` uses the explicitly
pinned directory and core specification template resolved through the preset
stack. No pre/post extension hooks are configured; only one spec is created.

The [specification](../specs/006-artifact-storage/spec.md) defines five
independently testable journeys: verified publication, bounded large transfers,
interrupted-work recovery, safe deletion, and alternative-store qualification.
It includes 23 acceptance scenarios, 15 edge cases, 25 functional requirements,
nine logical entities and eight measurable outcomes. Story independent tests
map all requirements to observable proof obligations. Its built-in
[requirements checklist](../specs/006-artifact-storage/checklists/requirements.md)
passes all 16 quality criteria with no unresolved clarification markers. This
generation-time review is not the scheduled clarification stage, custom
reviewer-owned checklist approval or product acceptance.

The agreement requires private staging, complete-content verification,
immutable digest identity, conditional publication, reconcilable uncertain
mutations and direct committed-read visibility. Bounded non-seekable streaming,
explicit resource ownership and classified safe failures remain mandatory.
The future qualification must write and read 256 MiB and 4 GiB artifacts within
64 MiB incremental transfer memory per single-transfer run; this is not a
production size default or total host memory ceiling.

Shared coordination owns integrity/publication policy, metadata sequencing
and reader/reference/deletion authority; no provider establishes cross-store
atomicity or independently treats an unreferenced observation as deletion
permission. Recovery must fence expired owners, preserve acknowledged content
and distinguish incomplete staging from committed-but-unreferenced artifacts.
Filesystem and object-store capabilities must preserve the same safety
outcomes without requiring atomic rename or trusting incomplete listings.

The master F-06 filesystem focus remains real durable qualification during
later implementation, distinct from production filesystem delivery in original
SPEC-04. An independent no-rename object-store-semantics fixture proves logical
portability, not qualification of a real remote service or delivery of SPEC-27.
Generic certification remains F-07. Exact signatures, finite operational
budgets, reconciliation lifetimes and stored-content verification schedules
remain planning decisions under these requirements.

Only the spec, built-in checklist, README, this guide and shared flow checkpoint
change; the ignored local feature pointer is restored. Existing provider/example
guides, predecessor artifacts, product charter/specification, architecture/ADR
and diagrams, constitution/backlog, compatibility policy, product/tooling source,
IaC and release guidance are unaffected: this stage changes no existing API,
package edge, operational procedure or supported capability. No new architecture
review is required for this requirements-only change; substantial later contract
design/implementation retains its normal review gate. Repository tooling checks
cover the checkpoint, not artifact-store behavior; product and OpenTofu checks
are not rerun for this documentation/checkpoint-only stage.

| Exact command / check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests/tooling -v` | Passed all 76 tests |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/check-prerequisites.sh --json --paths-only` | Passed; resolves the pinned feature/spec |
| Direct artifact assertions | Passed exact master prompt, feature pointers, completed template and counts above; no pre/post hooks configured |
| `git diff --check` | Passed |

The checkpoint schedules **`clarify / ready`** for a separate invocation; the
feature PR remains draft. No plan, tasks, custom review approval, implementation,
qualification execution, merge, tag/release, infrastructure or deployment occurs.

### F-06 artifact storage clarification

The separately invoked `clarify` stage uses the installed `speckit-clarify`
with `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage`, retaining the
recorded feature branch and directory. The preceding specification checkpoint
is already pushed; [PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16)
remains draft. No pre/post extension hooks are configured.

The [dated clarification review](../specs/006-artifact-storage/spec.md#clarifications)
finds no critical ambiguities worth formal clarification. Zero questions were
asked or answered, and no functional requirements, acceptance scenarios,
outcomes, entities or scope decisions change.

| Ambiguity category | Status |
| --- | --- |
| Functional scope and behavior | Clear |
| Domain and data model | Clear |
| Interaction and UX flow | Clear |
| Non-functional quality attributes | Clear |
| Integration and external dependencies | Clear |
| Edge cases and failure handling | Clear |
| Constraints and tradeoffs | Clear |
| Terminology and consistency | Clear |
| Completion signals | Clear |
| Miscellaneous / placeholders | Clear |

Publication verification and direct-read visibility, uncertain acknowledgment
and recovery, ownership fencing, reader/reference-safe deletion and truthful
provider capabilities already have observable outcomes. Exact signatures,
finite budgets, reconciliation lifetimes, stored-content verification schedules,
capability representation and proof mechanics remain planning decisions, not
unanswered product questions. The 4 GiB/64 MiB target remains a future
qualification obligation, not measured evidence or a production default.

The built-in [quality checklist](../specs/006-artifact-storage/checklists/requirements.md)
is revalidated at **16/16 -> 16/16**, with no newly passing items, regressions
or unchecked items; the entire checklist remains unchanged. No reviewer-owned
custom checklist is generated or approved. Only the specification's
Clarifications section, README, this guide and shared checkpoint change.
Provider/example guides, predecessor artifacts, charter/product specification,
architecture/ADR/diagrams, constitution/backlog, compatibility policy and
release/IaC guidance are unaffected because requirements, public APIs,
dependency edges, operational procedures and supported capabilities do not
change. No new architecture review or product/OpenTofu run is warranted for
this documentation/checkpoint-only stage.

| Exact command / check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests/tooling -v` | Passed all 76 tests |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/check-prerequisites.sh --json --paths-only` | Passed; resolves the pinned feature/spec |
| Direct clarification assertions | Passed dated no-question review, unchanged requirements/checklist, ten clear categories, new local links and absence of hooks/later-stage artifacts |
| `git diff --check` | Passed |

The checkpoint schedules **`plan / ready`** for a separate invocation, with no
clarification blocker. Planning, custom checklist review, task generation,
implementation, qualification execution, merge, publication, infrastructure
and deployment are not performed by this stage.

### F-06 artifact storage planning

The separately invoked `plan` stage retains `feature/006-artifact-storage` and
explicitly pins `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage`.
The installed `speckit-plan` initializes its resolved template once; no
pre/post extension hooks are configured. It creates the
[plan](../specs/006-artifact-storage/plan.md),
[research decisions](../specs/006-artifact-storage/research.md),
[operation model](../specs/006-artifact-storage/data-model.md),
[API contract](../specs/006-artifact-storage/contracts/artifact-api.md),
[recovery protocol](../specs/006-artifact-storage/contracts/recovery.md),
[acceptance matrix](../specs/006-artifact-storage/contracts/acceptance.md)
and [future validation quickstart](../specs/006-artifact-storage/quickstart.md).
These artifacts are design obligations, not implemented public APIs or
executed artifact-store acceptance.

The additive BCL contract preserves `IArtifactProvider`, the existing
`Metadata.ArtifactDigest` and all lifecycle/configuration/metadata APIs.
Stores expose private verified staging, conditional immutable publication,
protected full-copy reads, ticket reconciliation and bounded maintenance.
Full read completion verifies digest/length; an open is not a media scrub,
and a failed copy cannot authorize reuse of partial destination output.
Complete verification is mandatory even for newly submitted duplicate content.

One host-injected shared authority coordinates store publication, readers,
F-05 metadata admission and exclusive deletion. Its metadata bridge validates
exact current commit evidence and holds protection through actual transaction
settlement. A zero-reference observation is not deletion permission.
Store/digest/incarnation and operation receipts fence stale deletion/recreation,
while late uncertain I/O retains exclusion rather than pretending rollback.
The guard-recognition API is provider-neutral; no concrete authority or
provider-private metadata schema leaks into consumers.

All 25 FRs, eight outcomes, 23 scenarios and 15 edge cases are traced to
48 planned cases: 40 common logical cases, four local durability cases and
four package/report cases. Full qualification requires exactly 96 provider/case
entries, 92 applicable passes and four explicit simulated-provider durability
exclusions. Each implementation must actually write/read 256 MiB and 4 GiB
with paced non-seekable streams and at most 64 MiB incremental peak process RSS.
Data generation and OS measurements cannot be replaced by sparse file size,
managed allocation counts, a smaller payload or a skipped test.

The local qualification adapter owns a private same-filesystem root, immutable
payloads and checked decision/receipt records. Actual child-process kills at
B0..B3/D0..D1 prove only the reported process-crash configuration; no portable
BCL flush is advertised as power-loss or directory durability certification.
The independently implemented disk-backed object-semantics fixture uses
multipart/conditional pointers and delayed direct visibility/listing without
rename; it supplies no durable remote-service claim.

Finite budgets now include transfer/control/cleanup/maintenance deadlines,
inactivity, byte/buffer/concurrency/staging limits, owner renewal and 24-hour
receipt retention. Cooperative streams have finite resource-release proof;
non-cooperative negative cases must retain bounded ownership, report incomplete
cleanup and block readiness. Closing a borrowed stream or disposing a live guard
is not an acceptable timeout shortcut.

The required bounded `hoard-architecture-review` identified one P2 omission:
the store lacked a public way to recognize protection acquired by the metadata
bridge. The design correction adds authority-owned `RetainAsync`, atomically
recognizing opaque live identity and pinning the same-operation protection
without another admission acquisition. AS-35 includes foreign/copied/disposed
guard negatives and held-after-expiry settlement. The reviewer otherwise found
no confirmed dependency/API compatibility violation or additional product-policy
question. The correction is recorded in the plan; no second agent review or
runtime proof is claimed. Both pre-research and post-design constitutional
assessments pass without an exception or ADR change.

README and this guide link the new artifacts and accurately schedule
`checklist / ready`. Existing specification and built-in checklist remain
byte-for-byte unchanged, with no custom approval or tasks generated. Provider/
example/compatibility guides, predecessor artifacts, charter/product spec,
baseline architecture/ADR/diagrams, constitution/backlog, product/tooling source,
locks, release and IaC guides remain unaffected: this stage adds proposed
contracts/fixture proof, not existing APIs, dependencies, runnable commands,
supported capabilities or operational procedures. The planned
`bash scripts/validate-artifacts.sh` must not be presented as runnable until
implementation. Existing .NET/OpenTofu acceptance is not rerun for design-only
changes; the tooling checks below do not establish storage behavior.

| Exact command / check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests/tooling -v` | Passed all 76 tests |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/setup-plan.sh --json` | Passed once; copied resolved plan template into the pinned directory |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/check-prerequisites.sh --json --paths-only` | Passed; resolves the pinned feature/spec/plan |
| Direct planning assertions | Passed seven artifacts, 48 cases/25 FRs/eight SCs, six crash barriers, 31 local links/anchors, unchanged spec/16-item checklist and planning-only scope |
| `git diff --check` | Passed |

The feature PR remains draft and the next separate invocation runs `checklist`.
Reviewer approval, tasks/analysis, implementation, qualification, convergence
and finalization remain outstanding. No source release, package publication,
infrastructure plan/apply, settings/permissions change, deployment or merge occurs.

### F-06 artifact storage checklists and assisted review

This subsection records the original checklist checkpoint. The
[approved RQ-01 follow-up](#f-06-approved-rq-01-clarification-and-re-review)
below records the current 40/40 review status.

The separately invoked `checklist` stage retains the recorded branch and pins
`SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage`. After the driver begins
`checklist / running`, the installed `speckit-checklist` resolves its template
and produces two new standard-depth requirements-quality checklists for
maintainer/provider-contract PR review:
[storage](../specs/006-artifact-storage/checklists/storage.md) and
[recovery](../specs/006-artifact-storage/checklists/recovery.md), 20 criteria each.
Generation leaves all 40 markers unchecked; no extension hooks are configured.

Storage covers content identity, complete verification, immutable publication,
read completion, borrowed streams, finite resource limits, private namespaces,
safe diagnostics and honest provider-neutral qualification. Recovery covers
ticket reconciliation, expiry/fencing, bounded maintenance, metadata authority,
protected readers, deletion/recreation, process-crash evidence and incomplete
cleanup. Every question evaluates written requirements and carries specification
traceability; none is an implementation procedure or passing runtime claim.

The maintainer explicitly reiterates: "you review the checklists, then highlight
what needs my attention". After generation completes, the separately authorized
assisted review evaluates all 40 items against the existing specification and
seven planning artifacts. Per-item evidence records **storage 20/20** and
**recovery 19/20**, with recovery CHK012 left unchecked. This is requirements
review, not self-approval during implementation or an unqualified approval of
the entire feature.

**Initial finding: high-priority
[RQ-01](../specs/006-artifact-storage/checklists/recovery.md#rq-01-finite-release-versus-non-cooperative-work).**
FR-009, SC-006 and US2 scenario 3 initially required finite owned-resource
release without an explicit cooperation condition. The API/plan/research and
required AS-39
negative instead permit non-cooperative stream/native work to retain ownership,
stop admission and block readiness until settlement. Bounded retained counts
are not finite release time. The recommendation is to explicitly distinguish
finite caller-return/cleanup-attempt budgets from resource release, guarantee
finite release for cooperative I/O, and require fenced late work, bounded
retained ownership and truthful incomplete cleanup/not-ready otherwise.
No disposal under live work, forced closure of borrowed streams or fabricated
rollback is acceptable. A different safely preemptible execution model would
require reconsidering the design.

At this checklist checkpoint, the maintainer had not approved that clarification
or a waiver. Requirements,
plan, research, model, API/recovery/acceptance contracts, quickstart and historical
built-in 16/16 checklist remain byte-for-byte unchanged. The custom review
did not silently edit them to satisfy its own criterion. RQ-01 needed resolution
and CHK012 re-review before implementation approval. The subsequent
[approved follow-up](#f-06-approved-rq-01-clarification-and-re-review)
records that resolution separately. Checklist generation was
complete, so the driver may schedule `tasks / ready`; neither task generation
nor later analysis bypasses this outstanding requirements gate.

README and this guide link the generated reviews, counts and exact decision
needed. Provider/example/compatibility guides, predecessor artifacts, charter/
product specification, baseline architecture/ADR/diagrams, constitution/backlog,
source/tests/tooling, locks, release and IaC guidance remain unaffected: the
change adds reviewer questions/evidence and checkpoint status, not APIs,
dependency edges, supported capabilities, operational procedures or architecture.
No additional architecture-agent review is needed for this checklist/docs-only
change. Product/.NET/OpenTofu checks are not rerun; the proposed artifact command
remains unimplemented and no storage qualification result is claimed.

| Exact command / check | Result |
| --- | --- |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/check-prerequisites.sh --json --template checklist-template` | Passed; resolves recorded directory, planning documents and canonical checklist template |
| `python3 -m unittest discover -s tests/tooling -v` | Passed all 76 tests |
| Direct generation/review assertions | Passed 40 initially unchecked sequential questions, 100% specification traceability, 40 evidence rows, final 39 satisfied/one unresolved marker, unchanged nine original artifacts and no later-stage scaffolding |
| Local Markdown link/anchor checks | Passed for both new checklists and added README/development links |
| `git diff --check` | Passed |

The feature stays draft in [PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16).
Only the checklist stage and the expressly requested assisted review run here;
no tasks, cross-artifact analysis, requirements remediation, implementation,
qualification, convergence, finalization, release, infrastructure plan/apply,
settings/permissions change, deployment or merge occurs.

### F-06 artifact storage task generation

This subsection records task generation before the separately approved
[RQ-01 correction](#f-06-approved-rq-01-clarification-and-re-review).

The separately invoked `tasks` stage retains `feature/006-artifact-storage`
and explicitly pins `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage`.
After the driver begins `tasks / running`, the installed `speckit-tasks`
resolves its canonical template and all eight specification/design inputs.
No pre/post extension hooks are configured. The generated
[tasks](../specs/006-artifact-storage/tasks.md) contain **86 unchecked tasks**:
six setup, 13 foundational, 11 US1, 11 US2, 15 US3, 12 US4, 12 US5 and six
cross-cutting tasks. All task lines have sequential IDs, exact destination
paths and story labels only in their respective story phases.

The plan's five journeys become independently testable increments in actual
dependency order: verified publication/read, bounded real large transfers,
exact receipt/recovery/ownership, shared-authority deletion, then unchanged
consumer/package/qualification proof. US1 is the smallest useful MVP, not
complete qualification or a runnable cache. The task prerequisite table is
complete and acyclic, with separate provider lanes and file-disjoint test work.
Shared orchestrator edits are serialized, and the old binary is frozen before
public API changes. Parallel markers describe scheduling opportunities, not
permission to launch a workflow engine.

Traceability assigns all 25 FRs, eight SCs, 23 story scenarios, 15 edge cases
and AS-01..48 to implementation and focused proof. Tests require intended
runtime red-before-green evidence rather than treating a missing type as proof
of failure safety. Each independent store must actually write/read both 256 MiB
and 4 GiB through paced non-seekable streams, with <=64 MiB incremental OS
peak RSS. Local B0..B3/D0..D1 require actual parent-signaled exit, fresh reopen,
exact receipt and full acknowledged control/new-content readback. Complete
qualification needs exactly 96 provider/case entries, 92 applicable passes and
four explicit simulated-provider durability exclusions, including every
required subproof on the current source/locks. Focused modes cannot qualify.

The tasks preserve the additive BCL-only boundary, historical digest and marker,
private independent local/object mechanisms, existing lifecycle/configuration
authority and unchanged metadata fixtures/APIs. One controlled host authority
coordinates publication, readers, metadata settlement and exclusive deletion;
zero-reference observation is never deletion permission. No cache engine,
production provider, endpoint, UI, cloud account, vendor SDK or generalized
F-07 certification is introduced by task generation.

**At task generation, RQ-01 remained unresolved and high priority.** The tasks
explicitly retained the conflict between FR-009/SC-006/US2.3 finite release and
design/AS-39 retained non-cooperative ownership. They did not choose the recommended clarification,
amend requirements, mark recovery CHK012 satisfied or grant a waiver.
Implementation had to wait for an approved resolution, aligned artifacts and
re-review (or explicit reviewer authorization), without silently interpreting
contradictory acceptance as satisfied. Read-only analysis may assess the
conflict; critical/high findings require separately authorized remediation and
fresh analysis before progress. Successful task generation itself is not blocked
by unchecked custom review markers and does not bypass their implementation gate.
The [later approved follow-up](#f-06-approved-rq-01-clarification-and-re-review)
updates the current task/review status without changing task markers or the
scheduled stage.

README and this guide link the task list and distinguish planned proof from
current behavior. Specification, seven planning artifacts and all three
checklists remain byte-for-byte unchanged, including built-in 16/16, storage
20/20 and recovery 19/20. Provider/example guides, existing compatibility
policy, predecessor artifacts, charter/product specification, architecture/ADR/diagrams,
constitution/backlog, source/tests/tooling, locks, release and IaC guides are
unaffected: only task/documentation/checkpoint artifacts change, not an API,
dependency edge, supported capability, architecture or operational procedure.
No additional architecture-agent review is needed for this task/docs-only
stage; implementation tasks retain that required pre-handoff review.

| Exact command / check | Result |
| --- | --- |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/setup-tasks.sh --json` | Passed once; resolved the pinned directory, canonical task template and four available design-document entries |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` | Passed; resolved the same feature with tasks included |
| `python3 -m unittest discover -s tests/tooling -v` | Passed all 76 tests |
| Direct task-structure/traceability/integrity assertions | Passed 86 unchecked sequential tasks, 36 parallel markers, all 86 prerequisite rows acyclic, 25 FR/eight SC/48 case/23 scenario/15 edge mappings, 11 unchanged original artifacts and intact review gate |
| Local Markdown link/anchor assertions | Passed all 14 links/anchors in the new task list and added README/development text |
| `git diff --check` | Passed |

The next separately authorized stage is read-only **`analyze`**. The feature
stays draft in [PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16).
No cross-artifact analysis stage, requirements remediation, implementation,
qualification, convergence, finalization, source release, infrastructure
plan/apply, settings/permissions change, deployment or merge occurs here.
Existing product/.NET/OpenTofu checks and the still-unimplemented
`validate-artifacts.sh` are not run for documentation-only task generation;
artifact-structure/link/integrity checks are not runtime storage evidence.

### F-06 approved RQ-01 clarification and re-review

The maintainer explicitly approves the recommended RQ-01 clarification:
"yeah, let's do what you're suggesting". This is a separately authorized
requirements correction and assisted re-review, not another `hoard-speckit`
invocation or implicit implementation approval.

The [specification follow-up](../specs/006-artifact-storage/spec.md#approved-follow-up-2026-10-22-rq-01-resource-ownership)
aligns exactly US2 scenario 3, FR-009 and SC-006 with the existing
[finite-work/ownership design](../specs/006-artifact-storage/contracts/artifact-api.md#finite-work-and-ownership):
caller return and cleanup attempts obey finite budgets; the qualified
cooperative I/O profile also guarantees actual owned-resource release within
the cleanup bound. Non-cooperative stream/native work retains only bounded
owned resources, fences late mutation, reports incomplete cleanup and blocks
admission/readiness until settlement or owner-controlled process termination.
Live handles/buffers/slots/guards cannot be released to fake cleanup, borrowed
streams cannot be forcibly disposed, and uncertainty cannot become false
rollback or successful cleanup.

The separate [recovery CHK012 re-review](../specs/006-artifact-storage/checklists/recovery.md#approved-resolution-and-re-review-2026-10-22)
compares these three updated specification passages with the unchanged API,
research D6, protected-reader/settlement ownership and required AS-39.
They now specify the same safe cooperative-release/non-cooperative-retention
outcomes. CHK012 is satisfied without a waiver: recovery becomes 20/20 and the
combined custom review **40/40**. All other custom markers and the built-in
16/16 requirements checklist remain unchanged. Storage's evidence notes
reference the resolution; none of its markers is re-generated or toggled.
No further maintainer decision remains from this review; actual release,
memory, crash and coordination proof are still future implementation obligations.

The [task list](../specs/006-artifact-storage/tasks.md) updates its current
status, RQ-01 references and focused ownership test instructions to the approved
requirements. Its 86 task IDs/markers, five-story counts, 36 parallel markers
and complete dependency graph are unchanged. No generator, `begin` or `finish`
is rerun. The tracked flow checkpoint stays byte-for-byte unchanged at
**`analyze / ready`**; read-only analysis must run through its installed skill
on a separate invocation before implementation.

README, this guide and draft [PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16)
record approval, the resolved finding and current review status while retaining
the original finding/history. The seven planning artifacts, required AS-39 and
all 48 acceptance cases remain unchanged because they already describe this
cooperation distinction. Provider/example/compatibility policy, predecessor
artifacts, charter/product specification, baseline architecture/ADR/diagrams,
constitution/backlog, source/tests/tooling, locks, release and IaC guidance are
unaffected: the correction aligns written promises with existing design, not
public signatures, dependencies, resource limits, architecture or runtime
behavior. No architecture-agent review is needed for this requirements/docs-only
correction; implementation still requires its planned architecture review.

| Exact command / check | Result |
| --- | --- |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` | Passed; resolves the recorded feature and unchanged task inventory |
| `python3 -m unittest discover -s tests/tooling -v` | Passed all 76 tests |
| Focused clarification/re-review assertions | Passed only US2.3/FR-009/SC-006 plus the approval log changed in the spec, only recovery CHK012 toggled, 40/40 custom criteria satisfied and all 86 unchecked tasks/36 parallel markers/dependencies preserved |
| Artifact/checkpoint integrity assertions | Passed nine unchanged planning/built-in/checkpoint artifacts, required AS-39 unchanged, no source/test/tooling/lock changes and driver still `analyze / ready` |
| Local Markdown link/anchor assertions | Passed all 17 added local links/anchors |
| `git diff --check` | Passed |

No analysis stage, implementation, qualification, convergence/finalization,
release/tag/package publication, infrastructure plan/apply, settings/permissions
change, deployment or merge occurs. Product/.NET/OpenTofu acceptance and the
unimplemented artifact runner are not run for this documentation-only change.

### F-06 artifact storage read-only analysis

The separately invoked `analyze` stage retains the recorded
`feature/006-artifact-storage` branch and explicitly pins
`SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage`. The driver begins
`analyze / running` before the installed `speckit-analyze` initializes the
existing specification, plan and tasks. No generator or earlier stage is
repeated, and no before/after analysis hooks are configured.

The read-only assessment finds no actionable duplication, ambiguity,
underspecification, constitutional conflict, coverage gap or inconsistency.
All **25 functional requirements and eight buildable outcomes** have
implementation/proof tasks: **100% coverage**, with zero actionable findings
and no remediation required. All **86 tasks** map to requirements, stories or
shared acceptance prerequisites; no task is unmapped. The 23 scenarios,
15 edge cases and all 48 acceptance cases retain focused proof assignments.
The 86-row prerequisite graph is complete and acyclic. Shared runner edits
are serialized, provider lanes remain independent and baseline capture
precedes public contract changes. The 36 parallel markers are scheduling
metadata, not authorization for agents or a workflow engine.

The approved RQ-01 clarification agrees across US2.3, FR-009, SC-006,
the API ownership contract, recovery design and T032/T037/T040/AS-39:
finite caller return and cleanup attempts, finite cooperative resource release,
bounded retained non-cooperative ownership, fenced late mutation and blocked
admission/readiness. No live-resource release or fabricated cleanup/rollback
is permitted. The additive BCL boundary, unchanged marker/digest/metadata APIs,
one shared authority and exact local-versus-simulated qualification limits
remain consistent with the constitution. UI, native protocol clients and
production-provider acceptance remain outside this bounded feature.

All **12 feature artifacts remain byte-for-byte unchanged**, including the
86 unchecked implementation tasks, built-in 16/16 checklist and existing
40/40 custom-review markers. Analysis does not re-approve checklists, implement
contracts, qualify storage or establish runtime proof. Actual four size/provider
measurements, six process-crash barriers, authority races, independent packages
and the 96-entry qualification inventory remain future obligations.

The full structured analysis report and per-requirement coverage table are
recorded in draft [PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16).
Only after the read-only skill completes does the driver finish analysis and
update README, this guide and the shared checkpoint. Provider/example guides,
compatibility policy, predecessor artifacts, charter/product specification,
architecture/ADR/diagrams, constitution/backlog, product/test/tooling sources,
locks, release and IaC guidance are unaffected: no requirement, public API,
dependency, support claim, command, permission or operational procedure changes.
No new architecture review is warranted for this report/docs/checkpoint-only
stage; the implementation's planned review remains mandatory.

| Exact command / check | Result |
| --- | --- |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/check-prerequisites.sh --json --require-spec --require-tasks --include-tasks` | Passed once; resolves the recorded feature and all required analysis artifacts |
| `python3 -m unittest discover -s tests/tooling -v` | Passed all 76 tests |
| Direct inventory, traceability, prerequisite and integrity assertions | Passed 33 requirement/outcome mappings, 86 unique sequential unchecked tasks, complete acyclic prerequisites, serialized runner edits, pre-API baseline ordering, 48 case IDs, 36 parallel markers and byte-identical feature artifacts |
| `git diff --check` | Passed |

The checkpoint schedules **`implement / ready`** for a separate invocation,
with the existing reviewer-owned 40/40 custom gate satisfied and no analysis
blocker. PR #16 remains draft. Product/.NET/OpenTofu acceptance and the
unimplemented artifact command are not run for this analysis/docs-only stage.
No implementation, qualification, convergence/finalization, feature completion,
merge, release/tag/package publication, infrastructure plan/apply, governance
change or deployment occurs.

```mermaid
flowchart TD
    Constitution["Constitution · once"] --> ConstitutionPR["Constitution PR merged"]
    ConstitutionPR --> Specify["Select eligible spec → specify"]
    Specify --> Clarify["Clarify"]
    Clarify --> Plan["Plan"]
    Plan --> Checklist["Requirements-quality checklists"]
    Checklist --> Tasks["Tasks"]
    Tasks --> Analyze["Read-only analysis"]
    Analyze --> Gate["Reviewer checklist gate"]
    Gate --> Implement["Implement all remaining tasks"]
    Implement --> Converge["Converge"]
    Converge -->|gaps appended| Implement
    Converge -->|no gaps| Finalize["Validate + docs + feature PR"]
    Finalize --> Merged["Wait for feature merge"]
    Merged --> Release["Publish v0.0.X-alpha at feature merge commit"]
    Release --> Progress["Completion checkpoint PR"]
    Progress -->|checkpoint merged| Specify
```

Each box representing a scheduled stage is **one invocation**, not a command
to run the entire backlog. Clarification is before planning; checklist generation
can use the plan, tasks precede analysis, and analysis precedes implementation.
Convergence is the installed post-implementation gap check. The implementation
invocation covers every remaining task, including tests and documentation:
successful tasks, batches, stories, phases, validation checkpoints, and
commit/push boundaries do not require another approval or invocation. Continue
until all tasks and checks pass, including when resuming or implementing
convergence-added tasks. Genuine blockers, unresolved questions, required
approvals, or user interruption can stop it with the stage still running.
Reviewer-owned checklist approval is not implicit. Completion still stops before
the separately invoked `converge` stage.

`await_merge` includes the post-merge source release, not a second scheduled
stage. The maintainer's standing authorization allows `hoard-speckit` to invoke
`hoard-release` and push the exact `v0.0.X-alpha` tag without another prompt.
X is the pinned feature directory's positive decimal prefix, not its backlog
ID: `specs/001-...` maps to `v0.0.1-alpha`, `002` to `v0.0.2-alpha`, and `010`
to `v0.0.10-alpha`. The tag must be annotated and target the recorded feature
PR's exact merge commit in `origin/main`, even if main has advanced.
Publication must be verified before recording completion or selecting the next
spec. Merges still require explicit authorization; this does not authorize
other release versions, package publication, infrastructure, or deployment.

### Checkpoint contract

- `.specify/hoard-flow.json` is **tracked shared progress**: stage, ready/running
  status, branch, active backlog ID/directory/PR, merged completions, and history.
  `status` also derives `release_tag` for the active directory without network
  calls or checkpoint writes. New completions include the verified
  `release_tag` and `release_url`.
- `.specify/feature.json` is an **ignored local pointer** used by Spec Kit.
  Restore it from the active shared checkpoint when resuming in another checkout.
- The master backlog owns prompts/dependencies; the checkpoint's `completed`
  entries own delivery status. A checked implementation task is not a merged
  feature. Eligibility uses completed dependencies, not phase labels alone.
- The first open eligible row wins. For example, F-08 is skipped until its
  dependency `18` is complete; the driver can then select original spec `01`.
  IDs stay stable and independent from Spec Kit sequential directory numbers.
- Start state is persisted **before** the skill runs; completion is persisted
  only after artifacts and quality gates pass. Commit/push the checkpoint with
  the stage's artifacts. Do not run two driver invocations concurrently.
- Constitution and completion checkpoints must be merged before a new feature
  starts from main. There is intentionally a progress-only PR after each feature
  merge and verified alpha release: it avoids declaring a feature complete in
  its own still-unmerged PR. Previously recorded completions without releases
  remain valid historical records; this policy does not backfill releases.

Inspect without modifying anything:

```bash
python3 scripts/speckit_flow.py status
```

The skill normally manages these commands; they are also available for recovery:

```bash
# On a proper work branch; do not run just to inspect progress.
python3 scripts/speckit_flow.py begin
# Only the specify stage needs the pinned new directory:
# python3 scripts/speckit_flow.py begin --feature-directory specs/001-provider-contracts

# Execute the scheduled installed skill and verify the actual stage gate first.
python3 scripts/speckit_flow.py finish --evidence "Stage result and review/check references"
# At finalize only: add --pr NUMBER.
# At await_merge: first verify the derived source prerelease was published.
```

**Interrupted stage:** `running` means inspect and resume the same artifacts.
Never reset JSON to `ready`, rerun specify into another directory, or invent
successful evidence. A failed stage stays running. A successful stage that
failed to push must be pushed before continuing. Restore corrupted checkpoints
from reviewed Git history and reconcile artifacts; do not silently default.
Already-open feature branches must incorporate merged workflow/tooling updates
from main to use the new release gate; preserve their feature checkpoints and
shared history when reconciling, rather than resetting them to main's state.

**Post-merge release recovery:** start `chore/spec-progress-<id>` from fetched
main before `begin`; commit/push that running checkpoint and open/update its
draft PR before invoking the release skill, so tagging uses a clean worktree.
Verify the `Source release` run, generated notes, source archives, exact tag
commit, and published prerelease. A successful tag push alone is not completion.
The helper's `finish` independently requires an annotated remote tag at the
feature merge commit and a non-draft GitHub prerelease with the expected tag and
URL. Missing publication, collisions, wrong commits, drafts, non-prereleases,
or failed checks leave `await_merge` running.
On retry, reuse only the correct existing tag/release after verification; watch
or rerun the specific failed workflow run when appropriate, never retag,
overwrite, or silently edit a release. Once verified, finish and commit/push
the release-bearing completion checkpoint, then make its PR ready. The next
spec still waits for that checkpoint PR to merge. See [release governance](RELEASING.md).

**Human gates:** requirements-quality custom checklists are reviewer-owned.
Generating them does not approve them. Analysis is read-only; remediation must
be separately authorized. Block on unresolved significant findings, unanswered
scope decisions, or missing acceptance evidence. The helper validates state and
some artifacts; the agent/reviewer must assess semantic correctness.

### Installed skills and agent responsibilities

| Entry point | When to use it |
| --- | --- |
| `hoard-speckit` | Advance/resume one backlog stage and checkpoint it |
| `speckit-constitution` | Governance creation/amendment; no product implementation |
| `speckit-specify`, `speckit-clarify` | Outcome-focused spec and ambiguity resolution |
| `speckit-plan`, `speckit-checklist`, `speckit-tasks` | Design, requirements-quality reviews, executable task breakdown |
| `speckit-analyze` | Read-only cross-artifact consistency gate after tasks |
| `speckit-implement`, `speckit-converge` | Build tasks, then append genuine remaining gaps |
| `speckit-taskstoissues` | Only when explicitly asked to publish tasks as GitHub issues |
| `hoard-architecture-review` agent | Substantial project-reference/provider-contract/composition/shared-invariant changes before PR handoff |
| `hoard-release` | Explicit release request or authorized Spec Kit post-merge alpha release; never deploy |

The architecture agent is read-only and returns concrete `path:line` findings,
not implementation or a blanket approval. Select it in Copilot's agent selector
or delegate a narrowly bounded architecture review when supported. It is not
required for simple doc or repository-tool changes.

## Current checks and future product checks

F-06 implementation passes full **test-fixture** qualification. Its entry point,
`bash scripts/validate-artifacts.sh --evidence <fresh-private-destination>`,
requires an existing owner-private parent outside Git. It prepares the retained
pre-F06 baseline and independent packages with tracked locks, then executes
the complete 96-entry matrix (92 passes/four Object durability exclusions). Set
`HOARD_ARTIFACT_RETAINED_BASELINE` to the original private baseline capture;
the marker binary is hash-verified and reused without rebuilding. The BCL
contracts and independent storage mechanisms also have focused package checks;
use `--phase logical` for nonqualifying common checks,
including real metadata transactions and non-cooperative containment children.
Both fixtures declare the baseline and become ready after successful explicit
admission; missing guarantees/version/authority reject before root I/O.
Failure captures are retained with
`qualification: false`; neither compilation nor the verifier's synthetic tests
qualifies storage. See the [final implementation evidence](../specs/006-artifact-storage/plan.md#final-fixture-qualification-and-handoff-2026-10-22).
The initial `NU1403` failure came from rebuilt Abstractions bytes under local
acceptance version `0.1.0` meeting the old package-content hash. The maintainer
approved reviewed local-package hash refreshes on 2026-10-22. Only 142
`Hoard.*` hashes in 38 of 97 tracked lockfiles change; package versions,
dependency graphs, external-package hashes and frozen baseline locks/binaries
remain unchanged. All five existing regression commands pass separate default
locked replays at that earlier checkpoint. Focused artifact runs still report
`qualification: false`; only complete locked full mode qualifies. The artifact runner permits that local hash-only
metadata lock delta while still rejecting source, dependency/version, external
hash and malformed-hash changes. This does not disable package integrity checks
or authorize rewriting published packages. See
[exact results and audit](../specs/006-artifact-storage/plan.md#approved-lock-refresh-and-locked-replay-2026-10-22).
Provider authoring guidance identifies the additive, fixture-qualified contracts. Custom-host
examples, architecture diagrams, compatibility policy, IaC and release guides
are otherwise unaffected: old APIs/markers and production behavior are unchanged,
and no production storage, deployment or release is delivered.

The resumed mechanisms are recorded in the
[implementation evidence](../specs/006-artifact-storage/plan.md#resumed-storage-mechanisms-and-recovery-2026-10-22).
`--phase logical` runs common package checks and the unchanged round-trip
consumer without durable-crash or external-measurement proof tests.
`--phase recovery` runs ticket/owner checks
and six directly owned SIGKILL/fresh-process reopen journeys. `--phase transfers`
performs real 256 MiB/4 GiB write/read and OS peak-RSS measurements on both
fixtures and four actual-input runtime proof tests. Each rebuilds/hash-verifies prerequisites in a fresh private
workspace; none qualifies storage. `--phase packages` now checks actual resolved
graphs/public signatures, provider/Hosting leak negatives, baseline public member
accessibility and the unchanged old marker binary with current assemblies, plus
both consumer selections. Full mode requires every obligation, input binding
and exact per-AS runtime witness; missing evidence still fails closed.
The unchanged consumer now executes 16 store/evidence/maintenance/read/authority
operations on both choices, rather than only a round trip. It verifies exact
pending/committed/removed receipts, renewal, abandonment, bounded observation,
safe stale cleanup/recreation, unsupported ranges, borrowed stream survival and
independent retained protection. Report validation rejects roundtrip-only or
incomplete/duplicate/foreign operation inventories. Actual compiled consumer
bodies are checked separately from the host composition entry point; a hidden
provider-constructor control rejects. The same resolved negative graph also
rejects an impermissible Core/provider edge, and compiled object code has no
rename calls with the Local mechanism as its positive rename control.
Foundation and lifecycle selectors exclude only artifact graph tests that need
artifact-specific preparation, as they already do for other feature-owned graph
tests. Artifact package mode executes those tests with its real graphs; generic
architecture rejection/permitted and in-memory compatibility checks still run
in the existing foundation/lifecycle suites.
In-process metadata fixtures, not fabricated reference counts,
now test committed orphans, failed publication, live-reference exclusion and
guard retention through lost metadata acknowledgments on SQLite and memory.
Configured artifact fixture selection now uses the existing F-02/F-03 lifecycle:
registration/composition and disabled options perform no storage I/O, while
startup refuses incomplete capabilities. Successful controls prove exactly one
selected ready instance, stop and explicit restart: Local reopens its exact
known identity; Object uses a fresh root/epoch and rejects old tickets.
Lost deletion acknowledgments retain pending
physical status until exact-incarnation cleanup actually finishes; reconciliation
then advances only reclamation status, preserving the logical receipt.
Pre-decision commit cancellation fences the exact settled owner/generation,
including cancellation before the worker starts. Fencing happens after worker
unwind; live I/O is never cleaned underneath it. Independent-thread follow-up
reads guard against rejection paths stranding a provider state lock.
Cancellation settlement recognizes the complete current staged handle, not
just copied owner IDs; stale/forged handles and a newer external renewal cannot
destructively fence valid staging. Progress renewal owned by the cancelled
invocation still receives terminal fencing.
Equivalent-writer proof now holds both admitted publications before releasing
the decision; cleanup proof holds an old generation while replacement staging
is created. Additional checks cover conflicting staged lengths, producer/sink
inactivity and stale versus fresh recovery-page traversal. Package controls
compile actual third-party SDK, raw filesystem and service-locator leaks beside
permitted operation/stream/stamp counterparts.
Ordinary artifact commands own a fresh process session. Timeout or interruption
settles only its observed exact PIDs before returning; process observations share
the original cleanup deadline. A real descendant-timeout test confirms the owned
descendant stops while an unrelated child remains alive. Incomplete settlement
is an explicit failure, not permission to delete the retained evidence.
Architecture review corrected close admission/release ownership, terminal
noncommit cleanup, deadline bookkeeping behind blocked state I/O and ticket
validation/expiry classification. Final architecture review additionally found
successful-result handoff and unclaimed-reclamation defects; exact regression
reds and the corrections are recorded in the final evidence below.
Ticket-expiry admission now has separate finite retained-index budgets and
bounded compaction of expired fully reclaimed history. Physically active or
unresolved ticket work keeps its dependent records. Paired regressions cover
capacity restoration, blocked native/delete/reconciliation ownership and
finalized receipts across delete/recreate; a 105-cycle small-budget Local
journey reopens successfully after UTC rollback. Separate locked logical,
all-six-crash-barrier and package replays bind the current correction; see
[exact evidence and bounded reviews](../specs/006-artifact-storage/plan.md#bounded-ticket-and-reclaimed-history-2026-10-22).
Those earlier partial checks did not enable readiness or complete the stage.
The qualification value record now enforces the exact failure-model exclusions:
none for Local process-crash durability, exactly AS-41..44 for simulation.
Owned-child negatives additionally exercise non-cooperative source, destination
and synchronous native work on both fixtures. The parent validates two
PID/run/provider/scenario-bound observations around an explicit inspection
handshake, then terminates only that child and observes its exit before root
cleanup. Each observation checks retained physical work, borrowed streams,
exclusive root ownership, applicable read/delete protection and incomplete
shutdown with blocked admission. These six cases are containment negatives,
not cooperative release, durable crash recovery or qualification.
Retained-history admission now bounds candidates examined, not just records
removed: at most 100 tickets and 100 candidates per retained-history index,
with at most 100 history retirements per call. Rotating candidate cursors
resume across calls, including after a candidate fault. Incremental
exact-incarnation dependency memberships avoid rebuilding a protected-ticket
set from every ticket; Local rebuilds these indexes from validated bounded
records on reopen. Unexpired, unresolved and physically active dependencies
remain protected. The partial gate still does not establish full qualification.
Public qualification records now require a bounded explicit environment,
baseline capabilities and all 48 immutable per-case statuses, durations and
proof hashes. The old flat constructor explicitly rejects unattached case names
and aggregate hashes. The verifier reads each hashed case payload, checks its
provider/run/source/lock/configuration/capability/environment/package context,
and resolves both runtime subproofs to actual passed TRX tests and measured
durations. Case JSON is limited to 1 MiB and each TRX witness to 16 MiB.
The exact per-AS registry now requires all provider/parameter variants, not
generic passing method names. Full mode binds every case to actual input files,
materializes both public qualification records, and executes runtime/verifier
mutations plus altered-full-manifest rejection checks.

### F-06 final fixture qualification and handoff

The final locked full run and all four separate focused modes bind source
`aa5afb01c594acb418f48db975c408ea3c0350e6ef33cef93ba27fd322739e24`.
The full run ID is `f57fd648-f0fe-4eef-b72d-554b4e691a44`, retained privately at
`../hoard-artifact-evidence/final-qualified-handoff-locked-20261022`.
It contains 92 applicable passes/four explicit Object AS-41..44 exclusions,
229 logical/crash checks, four actual-transfer proof tests, three architecture
checks/eight graph scans, both unchanged consumer selections and the original
marker binary (`5b745ae0860722852921cab4e6b210fa20facb59e53aa6f1f8a157060aba939d`).
All six Python-owned SIGKILL/fresh-process barriers, three executed mutation
pairs and 29 altered-full-manifest rejection checks passed.

Qualification is limited to macOS 26.5 arm64, .NET 10.0.7 and APFS. Local uses
payload/decision `Flush(true)` without directory fsync; Object is process-local
simulation. Incremental OS peak RSS for Local 256 MiB/4 GiB was
2,129,920/17,793,024 bytes and Object 1,916,928/18,595,840 bytes, each below
67,108,864. Transfers run individually with one slot, 256 KiB copy buffers and
a 2 MiB provider buffer limit. No production cache/provider, remote service,
power-loss/network-filesystem/HA support or F-07 certification is inferred.

The final `hoard-architecture-review` found a P1 successful-result handoff race.
Four controlled runtime reds reproduced lost tickets/read sessions. Success
delivery is now serialized against cancellation; abandoned results stay owned
until their provider-private reclamation finishes. A bounded follow-up found
two P2 issues: expired staging reclamation and forgotten cleanup failures.
Six additional actual assertion reds preceded exact-generation cleanup without
new-work expiry requirements, retained failed-cleanup bookkeeping, blocked
admission/readiness/root release and bounded shutdown retries without duplicate
live cleanup. All corrected logical regressions and the final full run passed.

Exact final commands/results are in the
[plan evidence table](../specs/006-artifact-storage/plan.md#final-fixture-qualification-and-handoff-2026-10-22).
All five predecessor scripts passed separate default locked runs; tooling
passed 105 tests and `git diff --check` passed. The final delta is 15 local
`Hoard.*` content hashes in six locks only; dependency graphs/versions, external
hashes and frozen baseline locks/binaries are unchanged.
Full mode refuses `--update-locks`; refresh intentionally, review the delta,
then replay locked acceptance separately. The original pre-F06 capture remains
mandatory. The four focused modes always report `qualification: false`.
README, provider/test guides and the quickstart describe the delivered fixture
scope. Existing examples, product diagrams, compatibility/release policy and
IaC are unaffected: no prior API is removed, no product host/provider is added,
and no infrastructure, merge or release is performed.
The implementation checkpoint does not start convergence or finalize the PR;
the next separately authorized stage is **`converge`**.

### F-06 convergence findings

The separately invoked installed `speckit-converge` assessed the current
implementation in pinned `specs/006-artifact-storage`: 25 FRs, eight buildable
SCs, 23 story scenarios, 15 edge cases, eight Phase 1 design decisions with
their technical constraints, all 86 original tasks and eight constitutional
principles. The 48-case matrix, actual provider/authority paths, compiled
consumer, transfer/crash children and evidence verifier support the assessment;
checked task markers and a passing suite are not proof of uncovered behavior.

**Outcome: `tasks_appended`.** Two HIGH partial gaps remain; zero missing,
contradictory or unrequested findings and zero other severity findings.
The installed skill appended only
[Phase 9 / T087-T088](../specs/006-artifact-storage/tasks.md#phase-9-convergence).
Every preceding byte of tasks.md is preserved. Specification, plan, all other
feature artifacts and every built-in/custom checklist marker are unchanged.
No application, test, tooling or lockfile was modified. No extension hooks exist.

| Finding | Source | Current-code evidence and reproduced result |
| --- | --- | --- |
| F1 / T087: failed staging cleanup ownership | FR-009/012/015, US2/AC3-4, US3/AC4, SC-006; T032/037/043/048/049 | Local's staging failure path marks `notcommitted` before unlink; Object fences the upload before removing multipart files. If unlink fails, each supervisor returns `AccessDenied` with cleanup `Released` and readiness true. Restore access and expire ownership: observation exposes one abandoned stage, but cleanup returns zero completed/one conflict because it rejects Local `notcommitted` or Object `Fenced` state. One payload and its reservation remain; a new full-cap reservation returns `Capacity`. |
| F2 / T088: recovery cursor exhaustion | FR-015, US3/AC4, SC-008; bounded resumable recovery and T043/048/049/055 | Both maintenance implementations retain each consumed continuation and allocate another, with a 32-handle quota. A stable 35-identity inventory, page size one and one sequential caller returns only 32 observations before `Capacity`, without inventory mutation or concurrent scans. |

F1 requires bounded retained/retryable exact-generation reclamation and truthful
cleanup/readiness until settlement, including repeated failure, safe stop/local
reopen and capacity restoration. F2 requires a bounded cursor lifecycle that
permits complete sequential scans beyond 32 pages while retaining expiry,
query/store binding, changed-inventory rejection and listing-safety semantics.
Neither correction is implemented in this convergence stage.

Fresh evidence uses the same source fingerprint
`aa5afb01c594acb418f48db975c408ea3c0350e6ef33cef93ba27fd322739e24`.
Run `d74a80fa-1aa2-42a8-8217-2cf9370c661e` is retained privately at
`../hoard-artifact-evidence/converge-f06-locked-20261022`.
It passes the existing full 96-entry inventory: 92 applicable passes/four Object
durability exclusions, all four actual transfers, six actual crash barriers,
package/architecture/compatibility and fail-closed evidence checks. These
existing cases omit the two newly reproduced paths; their passing status does
not close T087/T088 or establish clean convergence.

| Command / check | Result |
| --- | --- |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --evidence /Users/christopherhouse/projects/hoard-artifact-evidence/converge-f06-locked-20261022` | Passed existing locked full qualification, 92 passes/four exclusions; not a clean-convergence result |
| Owner-private .NET probe referencing this fresh run's compiled Abstractions/Local/Object/HostAdapters assemblies, not rewritten provider code | Reproduced both findings on both providers: stable paging 32/35 then `Capacity`; restored staging access still yields 0 completed/1 conflict, 1 residual file, `Released`, ready true and blocked reservation |
| `python3 -m unittest discover -s tests/tooling -v` | All 105 passed |
| Append-only, feature/checklist integrity, current-source manifest verification, README/development link and `git diff --check` checks | Passed |

The probes and detailed raw proof remain outside Git. README and this guide
now distinguish existing passing qualification from known convergence gaps.
Provider/test guides, examples, quickstart, contracts/model/research, compatibility
policy, charter/product spec, architecture/ADR/diagrams, governance/backlog,
IaC and release guides are unaffected: this stage changes no API, mechanism,
dependency, command, operational configuration or supported environment; the
normative requirements already require both corrections. Those documents may
need implementation evidence updates when the fixes actually exist.
The driver schedules **`implement / ready`**, followed by fresh convergence.
[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) remains draft. No feature
completion, dependency unlock, finalization, merge, tag, publication, infrastructure
action or deployment occurred.

### F-06 convergence follow-up implementation

The separately invoked installed `speckit-implement` completes both
[Phase 9 tasks](../specs/006-artifact-storage/tasks.md#phase-9-convergence).
All 88 tasks are checked; existing reviewer-owned checklist markers are
unchanged. This invocation does not run convergence or finalization.

Failed prefix reclamation now retains exact staging ownership/reservations,
reports retained cleanup and blocks readiness/new admission. Bounded maintenance
can retry after access returns without ticket expiry or reopening a finalized
noncommit. Repeated shutdown failure keeps root ownership; one owned retry task
prevents duplicate live cleanup, and Local stop/reopen restores safe capacity.
Borrowed streams remain intact. Stale owners cannot reclaim new staging.

Recovery continuation successors retire their consumed handles; terminal pages
release them. All 32 independent single-row scans traverse 35 stable identities,
then free quota for another set of scans. Query/page-size/store/revision/expiry,
explicit consistency and no-deletion-authority protections remain intact.

Required architecture review `f06-recovery-followup-review` found one MEDIUM
introduced receipt-recovery issue. Two additional runtime reds preceded its
correction: exact settled receipts remain reconcilable during pending staging
cleanup, and bounded maintenance reclaims only residual staging without touching
committed bytes or reopening tickets. The reviewer ran no tests or post-fix
re-review; paired regressions/full acceptance provide correction evidence.

Six original and two review-correction runtime reds are retained privately.
Fresh source
`42cb2a4eaa77daf772b4197c1b6b189155516a9029aa08f00fdecfa995f1a90c`
qualifies in locked full run `a3c382f7-31a8-45a8-bda1-3037d44f9119`.
It passes 237 common/crash tests, four actual-transfer proof tests, three
architecture checks/eight graphs, six actual SIGKILL/fresh-reopen journeys,
the original frozen binary and both unchanged consumers. The 96-entry matrix
contains 92 passes/four Object durability exclusions; three mutation pairs and
29 altered manifests pass their rejection controls. Exact commands, red paths,
environment/limits and review details are in the
[follow-up evidence](../specs/006-artifact-storage/plan.md#convergence-follow-up-implementation-2026-10-22).
The logical update run passed 231 tests; its qualification remains false.
`python3 -m unittest discover -s tests/tooling -v` passed all 105 tests.
Build analyzers/format verification, hash-only lock audit and
`git diff --check` passed. Only 15 local package hashes in six locks change;
graphs/versions, external hashes and historical baselines remain unchanged.

README, provider/test guides, quickstart and recovery contract are updated.
Other contracts/model/research, examples, baseline product/architecture/diagrams/
ADR/governance/backlog, compatibility, IaC and release guides are unaffected:
no API, dependency boundary, production support, configuration or deployment/
release behavior changes. Predecessor full checks remain historical, not freshly
rerun; the complete affected artifact gate and tooling suite run here.
[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) stays draft. Next:
**`converge / ready`**, separately invoked; no clean-convergence, merge,
feature completion, release, infrastructure or dependency-unlock claim.

### F-06 fresh convergence: unpublished object cleanup

The separately invoked installed `speckit-converge` assesses present scoped
code against all 25 FRs, eight buildable SCs, 23 story acceptance scenarios,
15 edge cases, eight grouped Phase 1 plan decisions, all 88 existing tasks and
eight constitutional principles. T087's failed-staging ownership/receipt
correction and T088's consumed-continuation lifecycle remain covered.
Outcome: **`tasks_appended`**, one **HIGH partial** finding; zero missing,
contradicting or unrequested findings. No critical, medium or low finding.

| ID | Source | Current evidence | Required correction |
| --- | --- | --- | --- |
| F1 | FR-008/009/012/015, US2.2..4, SC-006; bounded private payload/recovery plan; T024/T032/T036/T037/T049/T050/T065 | `ObjectPublication.cs` creates a new assembled object per commit attempt, but failed deletion in its unselected-object `finally` has no retained cleanup index. Three 1 KiB retries leave three untracked payloads while returning `AccessDenied`, cleanup `Released` and readiness true. Abandonment frees the multipart reservation; recovery lists nothing and stop reports release with all three payloads remaining. | Track exact unpublished assembly ownership/capacity before fallible work, fence admission/readiness/retries on incomplete cleanup and provide finite repeatable recovery/shutdown without deleting selected or newer objects. |

The isolated package-only probe uses unchanged assemblies from the fresh
qualification workspace. It injects an actual exception at `pointer.compare`
after assembly and removes write permission from the owned `objects` directory.
Access is restored after each attempt. The otherwise identical writable
control leaves zero objects across all three retries; the failure variant
retains 1,024, 2,048 and 3,072 bytes. After `AbandonAsync`, both variants report
zero `ObserveAsync(All)` rows and admit another full-cap reservation; only the
failure variant still has payloads after successful `StopAsync`. No root or
artifact implementation is edited by the probe, and no external store is used.

The append-only stage adds just
[Phase 10 / T089](../specs/006-artifact-storage/tasks.md#phase-10-convergence).
All previous task text/markers, spec, plan, contracts and reviewer-owned
checklists remain unchanged. The existing task-status header is historical
implementation evidence, not a claim that newly appended T089 is complete.
Implementation must retain focused runtime red/green proof, cover partial and
complete assembly/cancellation/unlink retry/selected-object protection, wire
required runtime witnesses and rerun affected default locked acceptance.
Convergence does not implement the correction.

| Exact command / check | Result |
| --- | --- |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --evidence ../hoard-artifact-evidence/converge-followup-20261023` | Passed existing full locked qualification: 237 common/crash tests, four measured-transfer proof tests, package/architecture/retained-binary/consumer checks, four actual 256 MiB/4 GiB measurements and six actual SIGKILL/reopen barriers; 96 entries, 92 passes/four explicit Object durability exclusions |
| `python3 -m unittest discover -s tests/tooling -v` | All 105 passed |
| `dotnet run --project "$SESSION_FILES/convergence-probe/Probe.csproj" -c Release` | Reproduced F1 using current package assemblies: writable control zero residuals; denied-unlink variant three residual 1 KiB objects, false released cleanup/readiness and successful released shutdown; diagnostic probe, not a passing regression or qualification |
| `artifact_evidence.verify_manifest(manifest, work, artifact_evidence.source_hash(root))` | Passed independent retained full-manifest revalidation against unchanged current source |

`SESSION_FILES` denotes this invocation's private session `files/` directory;
the probe source, exact command output and owned roots are outside Git.
Retained `convergence-probe/result.log` SHA-256:
`99f3aec66a8691d239d8d6ab915e9ff2900c724ba2497eecccb6ba7b86b49ab3`.
Fresh full run `faea99c3-fc0b-44bb-a402-24e223a0158f` binds source
`42cb2a4eaa77daf772b4197c1b6b189155516a9029aa08f00fdecfa995f1a90c`.
These passing existing checks do not cover or waive F1 and do not establish
clean convergence. Full acceptance independently verifies formatting/analyzers.
No dependencies, lockfiles, application/test/tooling sources, historical
baseline inputs or capability claims change.

README and this workflow guide record the current gap and next stage.
Provider/test guides, quickstart, existing examples, product charter/spec/
architecture/diagrams/ADR, governance/backlog, compatibility, IaC and release
guides are unaffected: no API, runtime mechanism, intended contract, supported
environment or operational command is changed by this append-only assessment;
implementation must update affected evidence when T089 is actually fixed.
There are no pre/post convergence hooks. The driver schedules
**`implement / ready`** for T089, followed by a separate fresh convergence.
[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) remains draft.
Finalization is blocked; no merge, feature completion, dependency unlock,
release, package publication, infrastructure action or deployment is authorized
or performed.

### F-06 unpublished-object cleanup implementation

The separately invoked installed `speckit-implement` completes T089 and all
89 tasks. Before any fallible file creation, ObjectSemantics registers each
assembly to its exact upload and reserves its verified length. Its independent
scratch pool is bounded by the staging byte limit and transfer slots, alongside
the existing multipart reservation; the two private pools total at most twice
the staging byte limit, excluding selected/retired content. Selection atomically
transfers the exact object out of scratch accounting. No rename or shared
Local algorithm, public API, dependency or capability change is introduced.

Failed unlink retains partial/complete assemblies and original reservations,
blocks readiness/new admission and prevents commit retries from allocating
more payloads. Exact abandoned-generation maintenance reclaims only that
operation's unselected assembly and multipart pieces, reports actual bytes and
restores capacity only after settlement. Bounded nonduplicating shutdown retry
retains ownership on repeated failure. Selected/current/new content and exact
settled reuse receipts survive cleanup; borrowed sources stay open.

Five actual runtime reds precede the fix. Required bounded architecture review
`f06-t089-architecture` finds no confirmed defect, but identifies a missing
direct equivalent-reuse/unselected-unlink witness. The sixth regression closes
that evidence gap in the final full run; the reviewer ran no commands/tests.
See the [exact commands, audit and limits](../specs/006-artifact-storage/plan.md#unpublished-object-cleanup-implementation-2026-10-22).

| Exact command / check | Result |
| --- | --- |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --filter 'FullyQualifiedName~Unselected_object_cleanup\|FullyQualifiedName~Stop_retains_unselected_object\|FullyQualifiedName~Committed_receipts_remain_reconcilable' --update-locks --evidence ../hoard-artifact-evidence/t089-focused-green-update-20261023` | Seven checks and both unchanged consumers passed; intentional local-payload hash refresh, nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --evidence ../hoard-artifact-evidence/t089-full-locked-20261023` | Separate default locked full qualification passed: 243 common/crash tests, four actual-transfer proof tests, three architecture checks/eight graphs, both unchanged consumers/original marker and six SIGKILL/reopen barriers; 96 entries, 92 passes/four Object durability exclusions |
| `python3 -m unittest discover -s tests/tooling -v` | All 105 passed |
| `artifact_evidence.verify_manifest(manifest, work, artifact_evidence.source_hash(root))` | Independent final-source/lock manifest revalidation passed |
| Hash-only lock audit against `5134e09` | Nine local package content hashes in five locks; dependency graphs/versions, external hashes and frozen baseline unchanged |
| `git diff --check` | Passed |

Full run `a5c38d76-6d43-4cc9-94a6-0ec01f220cfb` binds source
`b4a89fcc5fdf5334a4ab03c493ba62704580643ca486e970ced3e65f9d1da1db`.
The exact catalog requires the new Object AS-15/17/21/27/40 witnesses. Actual
256 MiB/4 GiB write/read measurements meet the 64 MiB incremental RSS limit;
materialized qualification records, three mutation pairs and all 29 altered
manifest controls pass. Full acceptance includes whitespace/build analyzers.
No simulation or stale capture is substituted for durable proof.

README, provider/test guides, quickstart, recovery contract, plan and task status
are synchronized. Spec/API/model/research, existing examples, baseline charter/
product architecture/diagrams/ADR/governance/backlog, compatibility, IaC and
release guides are unaffected: no public signature, dependency boundary,
supported environment or operational command changes. Original task bodies
and reviewer-owned checklist markers stay unchanged. No extension hooks exist.
The five predecessor full gates remain historical; fixture/catalog-only changes
receive complete affected artifact qualification and tooling regressions.

The checkpoint schedules **`converge / ready`** for a separate invocation.
[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) remains draft.
No clean-convergence, finalization, feature completion, dependency unlock,
merge, release, package publication, infrastructure action or deployment.

```bash
python3 -m unittest discover -s tests/tooling -v
bash scripts/validate-foundation.sh
bash scripts/validate-lifecycle.sh
bash scripts/validate-configuration.sh
bash scripts/validate-discovery.sh
dotnet restore Hoard.slnx --locked-mode
dotnet build Hoard.slnx --configuration Release --no-restore
dotnet format Hoard.slnx --verify-no-changes --no-restore
tofu -chdir=infra/bootstrap fmt -check
tofu -chdir=infra/bootstrap init -backend=false
tofu -chdir=infra/bootstrap validate
tofu -chdir=infra/bootstrap test
```

The OpenTofu tests mock Azure/GitHub; they do not provision anything. The .NET
commands build libraries only; no runnable application or product CI exists.
`dotnet test` requires the temporary `HOARD_FOUNDATION_EVIDENCE` manifest prepared
by the full script; a solution build/test alone is not package independence proof.
Partial script selectors `--phase declarations`, `--phase packages`,
`--phase architecture`, and `--phase hosts` cover their named bounded checkpoints,
never full acceptance. Later features
must introduce and document focused backend/UI format/type/unit checks,
architecture tests, provider contract suites, and real-client protocol tests.

### F-06 fresh convergence: corruption quarantine

The installed `speckit-converge` assessed the present scoped implementation
against 25 functional requirements, eight buildable success criteria, 23 story
acceptance scenarios, 15 edge cases, eight grouped plan decisions, all 89
existing tasks and eight constitutional principles. T087/T088/T089's resulting
cleanup/cursor behavior is present, but the outcome is **`tasks_appended`**:
one HIGH partial finding, no missing/contradicting/unrequested findings.

| ID | Source | Current evidence | Remaining work |
| --- | --- | --- | --- |
| F1 | FR-005/010/012, US1/AC5, SC-001/003; T021/T022/T025..T028 | `LocalEvidence.cs:35..36` and `ObjectReadSession.cs:213..215` detect a direct-length mismatch but never mark the selected incarnation corrupt | Quarantine each exact detected-corrupt incarnation across validation/open/publication/reconciliation detection paths, with paired regressions and Local reopen proof |

A private console probe references the actual independently prepared current
assemblies and calls only public artifact/authority contracts. For **each**
provider, an intact published receipt first validates successfully; truncating
its payload makes `ValidateAsync` return `CorruptContent`. Without performing a
full copy (whose existing path does record corruption), `OpenReadAsync` still
returns a successful session. Externally restoring the original bytes then
makes that same evidence validate and a new duplicate commit return
`AlreadyPresentVerified`. No explicit recovery or new incarnation intervenes.
The normative verification policy requires detected corruption to mark that
incarnation unusable; external byte restoration is not authorized automatic
repair. This is missing quarantine, not a demand for continuous media scrubbing.

The skill appends only [Phase 11 / T090](../specs/006-artifact-storage/tasks.md#phase-11-convergence).
All previous task bytes/checkboxes, spec, plan and reviewer-owned checklists
remain unchanged. Application/test/tooling sources and lockfiles are untouched;
the probe and raw qualification captures remain outside Git. No pre/post
convergence hooks are configured. No implementation or checklist self-approval
occurs in this stage.

| Exact command / check | Result |
| --- | --- |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/check-prerequisites.sh --json --require-spec --require-tasks --include-tasks` | Passed; exact pinned directory and required artifacts |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --evidence ../hoard-artifact-evidence/converge-f06-20261023-2021` | Fresh default locked qualification passed: 243 common/crash tests, four actual-transfer proof tests, three architecture checks/eight graphs, original binary and both unchanged consumers; exact 96 entries, 92 passes/four Object AS-41..44 exclusions |
| `dotnet run --project "$SESSION_FILES/corruption-probe/Probe.csproj" -c Release -v quiet` | Reproduced F1 on both providers: initial `Success`, truncation `CorruptContent`, subsequent open `Success`, restored-byte validation `Success`, duplicate reuse `Success (AlreadyPresentVerified)` |
| `python3 -m unittest discover -s tests/tooling -q` | All 105 passed |
| `artifact_evidence.verify_manifest(manifest, work, artifact_evidence.source_hash(root))` | Independent fresh current-source/lock manifest revalidation passed |

`SESSION_FILES` denotes this invocation's private session `files/` directory.
Fresh full run `d43680be-3121-4fbe-a18c-6cea1c01f081` binds source
`b4a89fcc5fdf5334a4ab03c493ba62704580643ca486e970ced3e65f9d1da1db`.
Existing full qualification includes all four real 256 MiB/4 GiB write/read
measurements and six owned SIGKILL/fresh-reopen barriers, with zero failed or
skipped tests. It omits the demonstrated validation-first quarantine sequence
and therefore cannot establish clean convergence. The five predecessor gates
remain historical, not freshly rerun for this append-only assessment.

The driver records this result separately from the skill's append-only write.
README and this guide describe the blocker; provider/test guides, quickstart,
recovery/API/model/research, examples, baseline charter/product architecture/
diagrams/ADR/governance/backlog, compatibility policy, IaC and release guides
are unaffected because no API, intended behavior, dependency, runtime mechanism,
supported environment or operational command is changed. The original evidence
and task-status passages remain chronological implementation history.

Next stage: **`implement`** T090, then separately invoked fresh convergence.
[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) stays draft.
Finalization, feature completion and dependency unlock remain blocked; no
merge, tag, release, package publication, infrastructure action or deployment.

### F-06 corruption quarantine implementation

The separately invoked installed `speckit-implement` completes T090; all 90
tasks are checked and reviewer-owned checklist bytes remain unchanged.
Each independent provider quarantines the exact committed incarnation whenever
validation, open, reuse, full-copy, publication or unresolved reconciliation
detects corruption. External byte restoration does not revive evidence/opens/
reuse. Local quarantine survives compatible reopen; Object retention remains
process-local. Permission and unavailable-directory failures stay distinct.
Finalized receipts remain historical decisions; authorized delete/recreate
produces a new incarnation without poisoning it.

Delayed opens recheck quarantine before handing off a session. Required review
`f06-t090-architecture` found two P2 defects, both reproduced and corrected:
Local unresolved reconciliation now rechecks quarantine after verification,
and failed quarantine persistence retains its in-memory fence, not-ready/
admission block and root ownership. Restore access and retry bounded `StopAsync`
until pending quarantine is durable; failure/timeout never reports root release.
One owned recovery task retries at most 100 pending decisions per call.

| Exact command / check | Result |
| --- | --- |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --update-locks --filter 'FullyQualifiedName~ArtifactEvidenceTests\|FullyQualifiedName~ArtifactReadVerificationTests\|FullyQualifiedName~ArtifactPublicationRaceTests' --evidence ../hoard-artifact-evidence/t090-final-update-20261023` | All 32 focused checks and both consumers passed; final-source local hash refresh, nonqualifying |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --evidence ../hoard-artifact-evidence/t090-full-locked-20261023` | Separate default locked full qualification passed: 261 common/crash tests, four actual-transfer proof tests, three architecture checks/eight graphs, both unchanged consumers/original marker, four actual size/provider measurements and six owned SIGKILL/reopen barriers; exact 96 entries, 92 passes/four Object durability exclusions |
| `python3 -m unittest discover -s tests/tooling -v` | All 105 passed |
| `artifact_evidence.verify_manifest(manifest, work, artifact_evidence.source_hash(root))` | Independent final-source/lock full-manifest revalidation passed |
| Hash-only lock audit against `73a1fc4` | Only 15 local package hashes in six locks; versions/graphs, external hashes and frozen historical inputs unchanged |
| Task/checklist integrity, local documentation links and `git diff --check` | Passed |

Run `555737ba-995c-4501-b205-b2352da0da9a` binds source
`27fada08e37c9fe21949ce5579151e01a1cdafd676b18ae3415fa3950bfd37a4`.
Fourteen intended runtime reds precede their corresponding corrections, with
intact/access/outage/full-copy controls retained. Exact commands, reviewer
findings/corrections, bounded recovery and environment limits are in the
[T090 evidence](../specs/006-artifact-storage/plan.md#corruption-quarantine-implementation-2026-10-22).
The full verifier requires new per-AS witnesses and passes its three executed
mutation pairs/29 altered-manifest controls, formatting and build analyzers.
Actual generated 256 MiB/4 GiB write/read transfers on each fixture meet the
64 MiB incremental OS peak-RSS ceiling; no stale or simulated durability proof
is substituted.

README, provider/test guides, quickstart, recovery contract, plan and task status
are synchronized. Spec/API/model/research, examples, charter/product architecture/
diagrams/ADR/governance/backlog, compatibility, IaC and release guides are
unaffected because no public signature, dependency boundary, supported environment
or operational command changes. No hooks exist. Predecessor full gates remain
historical, not rerun for fixture/catalog-only changes. Qualification remains
test-only macOS/.NET/APFS Local process-crash evidence plus process-local Object
simulation, not production/F-07 or power-loss/remote-service/HA certification.

That implementation checkpoint scheduled separately invoked **`converge / ready`**.
[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) remains draft.
No clean-convergence, finalization, feature completion, merge, release, package
publication, infrastructure action, deployment or dependency unlock is claimed.

### F-06 clean convergence

The subsequent installed `speckit-converge` assesses the present implementation
in the pinned `specs/006-artifact-storage` directory, not a branch diff.
Outcome: **converged**, with zero missing, partial, contradicting or unrequested
findings and zero findings at any severity. The assessment covers all 25 FRs,
eight buildable SCs, 23 story acceptance scenarios, 15 edge cases, eight Phase 1
plan decisions, all 90 existing tasks and eight constitutional principles.
Corrective chains are assessed by their resulting behavior, including
T087/T088 failed-prefix ownership and cursor retirement, T089 bounded
unselected-object cleanup and T090 exact-incarnation corruption quarantine.

No convergence phase or task is appended. Spec, plan, tasks, contracts,
checklists, product/test/tooling sources and lockfiles remain byte-for-byte
unchanged. No custom checklist approval or implementation occurs, and no
extension hooks exist.

| Exact command / check | Result |
| --- | --- |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/check-prerequisites.sh --json --require-spec --require-tasks --include-tasks` | Passed; exact pinned feature and all required artifacts |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --evidence ../hoard-artifact-evidence/converge-t090-20261022` | Fresh default locked full qualification passed: 261 logical/crash checks, four measured-transfer proof checks, three architecture checks/eight actual graphs, original frozen marker, both unchanged 16-operation consumers, four actual size/provider measurements and all six owned SIGKILL/fresh-process barriers; exact 96 entries, 92 passes/four Object AS-41..44 exclusions |
| `python3 -m unittest discover -s tests/tooling -v` | All 105 passed |
| `artifact_evidence.verify_manifest(manifest, work, artifact_evidence.source_hash(root))` | Independent current-source full-manifest revalidation passed |
| Artifact/task/checklist integrity and `git diff --check` | Passed; all 90 tasks remain checked, no feature artifact or source/lock change |

Run `83c78659-2dc0-4564-93da-f74bdd2fc263` binds unchanged source
`27fada08e37c9fe21949ce5579151e01a1cdafd676b18ae3415fa3950bfd37a4`.
Each measured child writes and reads actual paced non-seekable 256 MiB/4 GiB
payloads. Incremental OS peak RSS is Local 2,244,608/17,924,096 bytes and Object
2,129,920/18,661,376 bytes, all below 67,108,864 bytes.
The exact B0/B1/B2/B3/D0/D1 kill/reopen proofs, three executed mutation pairs,
29 altered-manifest rejections, formatting and build analyzers pass.
Qualification remains limited to macOS 26.5 arm64, .NET 10.0.7/APFS,
Local `Flush(true)` without directory fsync and process-local Object simulation.
It is not production/F-07, remote-service, power-loss, Windows or HA certification.

README and this guide record the assessment and next stage. Provider/test
guides, examples, quickstart, feature design/evidence artifacts, baseline
charter/product specification/architecture/diagrams/ADR, governance/backlog,
compatibility, IaC and release guides are unaffected because no requirement,
API, mechanism, dependency, command, supported environment or recovery/rollback
procedure changes. Predecessor acceptance remains historical rather than
newly rerun; only the full affected artifact suite and tooling regressions run
for this assessment.

Next separately invoked stage: **`finalize`**. Draft
[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) carries this assessment.
Clean convergence alone does not finalize the feature, authorize merge,
unlock dependencies, publish a tag/release/package or deploy infrastructure.

### F-06 finalization

The separately invoked finalization stage resumes the recorded
`feature/006-artifact-storage` branch and explicitly pinned
`specs/006-artifact-storage` directory. All 90 tasks are complete and convergence
is clean. The built-in 16/16 and reviewer-owned storage/recovery 40/40 approvals
remain unchanged, without waivers. All 25 requirements, eight outcomes, 23 story
scenarios, 15 edge cases and the exact 48-case matrix retain their proof mappings.

The [implementation architecture reviews](../specs/006-artifact-storage/plan.md#final-fixture-qualification-and-handoff-2026-10-22)
and [T087/T088](../specs/006-artifact-storage/plan.md#convergence-follow-up-implementation-2026-10-22),
[T089](../specs/006-artifact-storage/plan.md#unpublished-object-cleanup-implementation-2026-10-22)
and [T090 corrections](../specs/006-artifact-storage/plan.md#corruption-quarantine-implementation-2026-10-22)
remain applicable. Reported findings were reproduced as runtime assertion reds
and corrected; focused regressions and fresh full acceptance verify the fixes.
The T090 reviewer was not rerun after correction. Finalization changes no
implementation, contract or dependency boundary and does not add another review
or imply blanket independent approval.

| Exact command / check | Result |
| --- | --- |
| `SPECIFY_FEATURE_DIRECTORY=specs/006-artifact-storage .specify/scripts/bash/check-prerequisites.sh --json --require-spec --require-tasks --include-tasks` | Passed; exact pinned feature and required artifacts |
| `HOARD_ARTIFACT_RETAINED_BASELINE=../hoard-artifact-evidence/pre-f06-20261022 bash scripts/validate-artifacts.sh --evidence ../hoard-artifact-evidence/finalize-f06-20261022` | Fresh default locked full qualification passed: 261 logical/crash checks, four measured-transfer proof checks, three architecture checks/eight actual graphs, original frozen marker, both unchanged 16-operation consumers, four actual transfers and six owned SIGKILL/fresh-reopen barriers; exact 96 entries, 92 passes/four Object AS-41..44 exclusions |
| `python3 -m unittest discover -s tests/tooling -v` | All 105 passed |
| `artifact_evidence.verify_manifest(manifest, work, artifact_evidence.source_hash(root))` | Independent current-source full-manifest revalidation passed |
| Task/checklist/source/lock integrity, affected local documentation links and `git diff --check` | Passed; all task bodies/markers, reviewer approvals, normative contracts, product/test/tooling sources and locks preserved |

Run `49189bab-9010-4ec6-a825-2b4d2f2de31b` binds source
`27fada08e37c9fe21949ce5579151e01a1cdafd676b18ae3415fa3950bfd37a4`.
The actual paced non-seekable 256 MiB/4 GiB write/read incremental OS peak RSS
is Local 9,863,168/17,842,176 bytes and Object 2,195,456/18,366,464 bytes,
all below 67,108,864 bytes. B0/B1/B2/B3/D0/D1 owned-child crash/reopen proof,
three executed mutation pairs, 29 altered-manifest negatives, formatting and
build analyzers pass. The environment remains macOS 26.5 arm64, .NET 10.0.7/APFS,
Local `Flush(true)` without directory fsync and process-local Object simulation.
No production/F-07, remote-service, power-loss/OS/device-failure, Windows/
network-filesystem or HA qualification follows. Raw evidence remains outside Git.
The five predecessor full gates remain historical, not newly rerun here.

README, this guide and feature plan/task/quickstart status record the merge
handoff. Provider/test guides, API/model/recovery/acceptance contracts, research
and examples already describe the implemented interfaces, commands, limits and
recovery procedures; no behavior changes require further edits. The normative
specification, constitution and reviewer checklists remain unchanged. Baseline
charter/product specification/architecture/diagrams/ADR, earlier features,
governance/backlog, compatibility, release/cloud/UI/IaC guidance and permissions
are unaffected: no new runtime, capability, dependency or operational procedure
is introduced.

[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) is ready for maintainer
review and merge using the repository template. `finish --pr 16` records
**`await_merge / ready`**, not completion or dependency eligibility. After the
maintainer merges, a separate invocation must verify the merge and publish
`v0.0.6-alpha` at its exact merge commit before recording completion. No merge,
tag/release, package publication, infrastructure plan/apply, repository-setting
change, cloud mutation or deployment runs in finalization.

### F-06 merge completion and alpha source release

[PR #16](https://github.com/Stonefly-Labs/Hoard/pull/16) merged into `main` at
`9389016c0285c79f6f515f59805a5a41c69b0767`. The separately invoked
`await_merge` stage verifies that exact commit in fetched `origin/main`, all
90 completed tasks, unchanged 16/16 built-in and 40/40 reviewer-owned checklist
approvals, and the finalization/convergence/architecture evidence above.
The retained full manifest independently revalidates against unchanged source
`27fada08e37c9fe21949ce5579151e01a1cdafd676b18ae3415fa3950bfd37a4`,
run `49189bab-9010-4ec6-a825-2b4d2f2de31b`, with all 96 attributed entries.
This is verification of retained acceptance, not a new full product execution
or architecture review; the qualification limits above still apply.

The stage starts `chore/spec-progress-f-06` from fetched main before `begin`.
Its running checkpoint is committed/pushed as `f46b561` in draft
[PR #17](https://github.com/Stonefly-Labs/Hoard/pull/17), preserving a clean
worktree and durable recovery point before tagging. Under the bounded standing
authorization, the installed `hoard-release` skill publishes
[`v0.0.6-alpha`](https://github.com/Stonefly-Labs/Hoard/releases/tag/v0.0.6-alpha)
at the exact feature merge, not the progress branch tip.

| Exact command / check | Result |
| --- | --- |
| `python3 scripts/release.py v0.0.6-alpha` | Passed; valid prerelease |
| `python3 -m unittest discover -s tests/tooling -v` | Passed all 105 tests |
| `git merge-base --is-ancestor 9389016c0285c79f6f515f59805a5a41c69b0767 origin/main` | Passed |
| `artifact_evidence.verify_manifest(manifest, work, artifact_evidence.source_hash(root))` | Passed independent retained full-manifest revalidation against unchanged source |
| `python3 scripts/release.py v0.0.6-alpha --check-main` | Passed; exact merge commit |
| `gh run watch 39887599522 --exit-status --interval 3` | Passed; [Source release run](https://github.com/Stonefly-Labs/Hoard/actions/runs/39887599522) succeeded at the exact merge |
| Release/tag/archive verification | Passed non-draft prerelease, generated PR-linked notes/changelog, annotated remote tag, ZIP full-commit comment and four exact-merge file comparisons in each automatic archive |
| `git diff --check` | Passed |

The annotated tag object is `a2b7124ab826c04b43f3dcfc809e1d891f2271bd`;
its remote peeled commit is the feature merge above. README, checkpoint, task
list and `src/Hoard.Abstractions/Storage/IArtifactStore.cs` match the exact
merge's bytes in both source archives. Verification holds downloaded archives
only in memory; no archives, raw qualification evidence, runtime data, build
output or credentials enter Git.

Only after publication verification does `finish` independently verify the
annotated remote tag and published GitHub prerelease and record F-06 complete
with `release_tag` and `release_url`. PR #17 shares the completion checkpoint
and documentation and must merge before a later invocation starts F-07
**`specify`**. This invocation starts no new specification and merges no PR.

README and feature plan/task/quickstart status now record the verified handoff.
Provider/API/model/recovery/acceptance and CustomHost guides, examples, baseline
product intent/architecture/ADR diagrams, constitution/backlog, predecessor
artifacts, release/cloud/UI/IaC guidance and permissions are unaffected: no
implementation, signature, package edge, operational procedure or support scope
changes. No new architecture review is needed for this progress/docs-only scope.
The normative specification and reviewer-owned checklists remain unchanged.
The source release publishes no runtime binaries, packages or containers and
performs no deployment, infrastructure plan/apply, cloud mutation or governance
change.

### F-07 provider conformance specification

The F-06 completion checkpoint merged through
[PR #17](https://github.com/Stonefly-Labs/Hoard/pull/17) at
`e75415fee07a5003c4cb40d869826c19fe0a2f36`. The next invocation fetched
`origin/main`, verified the merged checkpoint and ratified constitution,
and began F-07 on `feature/007-provider-conformance` from that main commit.
The driver pinned the exact dependency-ready master prompt and
`specs/007-provider-conformance` before invoking installed `speckit-specify`.
The resolved core specification template was used; no extension hooks exist.

The [specification](../specs/007-provider-conformance/spec.md) defines five
prioritized journeys, 23 acceptance scenarios, 14 edge cases, 24 functional
requirements and eight measurable outcomes. Scope includes shared category
checks, startup/readiness/disabled-module failures, declared and actual
source/binary compatibility, forbidden/permitted dependency proof, contributor
templates, bounded isolated resources, and attributable fail-closed local/CI
reporting. The [built-in checklist](../specs/007-provider-conformance/checklists/requirements.md)
satisfies 16/16 specification-quality criteria, not custom reviewer approval.

The future baseline must exercise both independent F-05 metadata options and
both independent F-06 artifact options with unchanged common assertions and
consumers. Required logical guarantees cannot become optional exclusions.
Actual local database/filesystem crash evidence, process-local simulations
and future remote-service qualification remain distinct. Marker-only protocol
and identity checks cannot certify operational behavior; F-08 retains identity
contracts, production providers retain their backlog scopes, and native-client
acceptance remains SPEC-09. Existing contracts and finite retained-ownership
semantics are not redefined. CI checks are a future bounded F-07 deliverable,
not a workflow added or executed by specification generation.

Only README, this guide, the checkpoint and the new specification/checklist
change. Provider/API/compatibility/recovery and example guides, existing feature
artifacts, product charter/specification, architecture/ADR/diagrams, governance/
backlog, release/cloud/UI/IaC guidance and runtime/test/tooling sources are
unaffected: this stage changes no API, dependency edge, executable behavior,
support status or operational procedure. No new architecture review or product
acceptance execution is warranted for this requirements-only change.

That specification checkpoint scheduled **`clarify`** in a separate invocation. The feature remains
incomplete and its PR remains draft; no implementation, qualification,
production support, merge, release, package publication, infrastructure action
or deployment is claimed.

### F-07 provider conformance clarification

The installed `speckit-clarify` reviewed the pinned
[specification](../specs/007-provider-conformance/spec.md#clarifications) against
all ten ambiguity categories and the constitution. No critical ambiguity
required a question: zero asked or answered, with no requirement, acceptance
criterion or scope change. Functional scope, domain/data, interaction flow,
applicable quality attributes, integrations, failure handling, constraints,
terminology, completion signals and placeholders are clear for this feature.

Mandatory logical checks, actual durable-local evidence, simulated behavior and
future service qualification remain distinct. Composition, disabled optional
targets, retained binary consumers and permitted dependency counterparts retain
their existing policies. Observation deadlines do not authorize unsafe resource
release; reports must preserve input attribution and reject incomplete evidence.
Exact interfaces, report formats, finite budgets, job structure and the bounded
composition/version matrix remain constrained planning decisions, not unresolved
product choices.

The built-in specification checklist was revalidated unchanged at **16/16 ->
16/16**, with no newly passing items, regressions or unchecked items. No custom
reviewer checklist is approved. No extension hooks are configured; no plan,
tasks, implementation, CI workflow or qualification run is produced here.
The next stage is **`plan / ready`** through a separate invocation; draft
[PR #18](https://github.com/Stonefly-Labs/Hoard/pull/18) remains incomplete.

Only the clarification record, README, this guide and shared checkpoint change.
Provider/API/compatibility/recovery and example guides, predecessor artifacts,
product charter/specification, architecture/ADR/diagrams, governance/backlog,
release/cloud/UI/IaC guidance and runtime/test/tooling sources are unaffected:
no requirement, API, dependency edge, executable behavior, support scope or
operational procedure changes. No architecture-agent review, product acceptance,
infrastructure action, publication or merge is warranted or performed.

### F-07 provider conformance planning

The installed `speckit-plan` used pinned `specs/007-provider-conformance` and
generated the [plan](../specs/007-provider-conformance/plan.md),
[research](../specs/007-provider-conformance/research.md),
[data model](../specs/007-provider-conformance/data-model.md),
[validation quickstart](../specs/007-provider-conformance/quickstart.md) and
four contracts: [shared harness](../specs/007-provider-conformance/contracts/harness.md),
[evidence/CI](../specs/007-provider-conformance/contracts/evidence.md),
[finite matrix](../specs/007-provider-conformance/contracts/matrix.md) and
[acceptance](../specs/007-provider-conformance/contracts/acceptance.md).
No extension hooks are configured.

The design extracts common assertions into a separately packable test-only
SDK, with explicit provider-specific setup/fault bindings outside it. The SDK
does not reference concrete providers or enter production package graphs.
Existing independent mechanisms and platform contracts remain unchanged.
Both metadata and both artifact bindings retain their 192 inherited case
entries (179 applicable passes/13 exclusions required in a successful future
run), including actual SQLite/Local process-crash and 4 GiB/RSS obligations.
The plan adds 20 composition rows with explicit subvariants, existing policy
plus three-axis version boundary expansion, unchanged-source/retained-binary
consumption, isolated architecture negatives and permitted counterparts,
contributor good/faulty examples and 48 F-07 acceptance obligations.

Five mandatory local/CI profiles share one frozen inventory/evaluator.
Every case is bound to actual parameterized runtime witnesses and exact source,
locks, package bytes, configuration, capabilities and environment. Missing,
stale, duplicate, altered, skipped-mandatory, interrupted or retried-away
failures cannot qualify. Finite watchdogs preserve live ownership rather than
claiming settlement. All retained diagnostics, including private evidence,
are sanitized before persistence; raw output is transient and byte-bounded,
never spooled as logs/TRX. Synthetic stores are separate owned resources, not
report artifacts.
The workflow is planned only, with read-only permissions, no credentials,
verified action SHA pins and explicit runner-capacity admission at implementation.

All 24 FRs, eight SCs, 23 scenarios and 14 edge cases have design/proof mappings.
Constitution gates pass before and after design without exceptions. The bounded
architecture review identified retained-diagnostics sanitation and output-capture
bounds that are now corrected in the contracts and QC-34/QC-48 proof obligations.
Planned commands remain clearly marked unavailable. No product code,
new package manifest, workflow, custom checklist, tasks or runtime qualification
is created by this stage. Next is separately invoked **`checklist`**; custom
requirements reviews remain reviewer-owned and draft PR #18 remains incomplete.

README and this guide are updated. Provider/API/compatibility/recovery and
example guides, predecessor artifacts, baseline charter/product specification,
architecture/ADR/diagrams, constitution/backlog and release/cloud/UI/IaC guides
are unaffected: planning changes no implemented contract, dependency edge,
activation behavior, supported provider or operational procedure. The new
future contributor guide is specified, not presented as an existing example.
No merge, release/tag, publishing, infrastructure plan/apply, repository-setting
change, cloud action or deployment is authorized or performed.

### F-07 provider conformance checklists and assisted assessment

The installed `speckit-checklist` used pinned `specs/007-provider-conformance`
after `begin` recorded `checklist / running`. No before/after extension hooks
are configured. Standard-depth scope is requirements quality for maintainers
and provider-contract/evidence reviewers at draft PR review, before
implementation authorization. The two new reviewer-owned files are
[conformance](../specs/007-provider-conformance/checklists/conformance.md) and
[evidence](../specs/007-provider-conformance/checklists/evidence.md), with
20 criteria each. Every criterion cites written requirements; the checklists
assess completeness, clarity, consistency, measurable acceptance, scenarios,
edge cases, bounds, dependencies and scope, not delivered runtime behavior.

At the maintainer's request, an assisted assessment maps all 40 criteria to
written evidence and finds no unresolved requirements-quality blocker or
product decision needing maintainer resolution. All 40 markers remain
unchecked: generation and advisory assessment do not constitute reviewer
approval or authorization to implement. The built-in 16/16 checklist, spec,
plan, contracts and other design artifacts remain unchanged.

The important implementation risks are already explicit requirements:
preserve all 192 inherited category entries and parameterized subproofs during
extraction; freeze old binaries before candidate execution; perform actual
256 MiB/4 GiB and SQLite/Local crash proofs; measure at least 24 GiB private
scratch and sufficient runner capacity without reducing mandatory coverage;
sanitize private diagnostics before persistence as well as public output, and
bound transient capture without raw spooling or truncation into a pass.
Finite observation still preserves live ownership until actual settlement.
These require future evidence, not new product decisions at this checkpoint.

Next is separately invoked **`tasks`**. Task generation and later read-only
analysis do not require custom approval, but implementation remains gated on
reviewer approval or explicit reviewer authorization. Draft PR #18 stays draft.
No task list, implementation, workflow, runtime qualification, merge, release,
publishing, infrastructure plan/apply or deployment is performed here.

README and this guide link the new artifacts and distinguish assessment from
approval. Provider/API/compatibility/recovery and example guides, predecessor
artifacts, charter/product specification, architecture/ADR/diagrams,
constitution/backlog and release/cloud/UI/IaC guides are unaffected: this stage
changes no contract, product dependency, supported behavior or operational
procedure. No architecture change requires a new architecture-agent review.

### F-07 provider conformance task generation

The installed `speckit-tasks` uses the pinned
`SPECIFY_FEATURE_DIRECTORY=specs/007-provider-conformance` and canonical task
template to generate [86 unchecked tasks](../specs/007-provider-conformance/tasks.md).
Setup has six tasks and shared foundations twelve; the five story phases contain
20, 11, 12, six and 13 tasks, followed by six cross-cutting completion tasks.
There are 18 explicitly marked different-file parallel opportunities, subject
to the exact prerequisite graph and immutable-input acceptance isolation.

Every functional requirement, all eight outcomes and QC-01..48 have focused
implementation/proof assignments. The task list preserves all 192 inherited
category entries, every CP/version/architecture subvariant, real durable-local
recovery and actual 256 MiB/4 GiB/RSS proof. It requires safe owned execution,
sanitation before private/public diagnostic persistence, sealed old binaries
before candidate builds, a package-only contributor red/green journey and
all five actual CI profiles. Insufficient runner capacity, incomplete ownership
or missing CI evidence blocks acceptance; no reduced-coverage fallback is allowed.

US1 is the suggested MVP: unchanged common category consumers on all four
independent implementations, exact applicability and deliberate faulty-adapter
proof. It is category-scoped evidence, not complete F-07 qualification.
Each later story has its own independent diagnosis criteria; cross-story
prerequisites honestly identify shared packaged consumer, host and evaluator
integration. Shared-file edits are explicitly serialized and acceptance cannot
overlap edits to fingerprinted inputs.

Existing specification, plan, research, model, contracts, quickstart and all
checklists remain unchanged. All 40 reviewer-owned custom markers remain
unchecked; advisory assessment and task generation do not approve them.
No extension hooks are configured. Next is separately invoked read-only
**`analyze`**; implementation still requires reviewer approval or explicit
authorization and cannot bypass analysis.

README and this guide link the tasks and record the next gate. Provider,
compatibility, custom-host and other example guides, predecessor artifacts,
charter/product specification/architecture/ADR/diagrams, constitution/backlog,
IaC/release/UI guidance are unaffected: task generation changes no requirement,
design, implemented API, package graph, runtime/support claim or operational
procedure. The task list assigns their actual implementation-time updates.
No product project, harness, workflow, listener, qualification, package
publication, release, infrastructure operation or merge occurs in this stage.
Draft [PR #18](https://github.com/Stonefly-Labs/Hoard/pull/18) remains incomplete.

### F-07 provider conformance analysis

The installed `speckit-analyze` runs read-only with explicitly pinned
`SPECIFY_FEATURE_DIRECTORY=specs/007-provider-conformance`, after the driver
records `analyze / running`. Its prerequisite check resolves the recorded
directory and complete design/task inventory; no extension hooks are configured.

The review finds no actionable duplication, ambiguity, underspecification,
inconsistency, coverage gap or constitutional conflict across the specification,
plan, tasks and supporting contracts/model. All 24 functional requirements and
eight buildable outcomes have implementation and focused proof assignments:
32/32 covered, with zero unmapped tasks. Supporting mappings retain QC-01..48,
23 acceptance scenarios, 14 edge cases, all 192 inherited category entries and
every finite composition/version/architecture subvariant. This is an assessment
of planned coverage, not proof that any runtime obligation has passed.

All 86 tasks remain unchecked, with 18 marked parallel opportunities and story
counts 20/11/12/6/13. All 86 exact prerequisite rows are complete, execution-ordered
and acyclic; every task reaches T086 closure. Shared-file edits are serialized.
Old baselines are sealed before candidate builds. Immutable-input acceptance,
real transfer/recovery proof, sanitation before private diagnostic persistence,
bounded live ownership and actual five-profile CI remain future obligations.
Insufficient runner capacity or missing evidence remains a blocker.

All 13 feature artifacts, including task bodies and built-in/custom checklist
markers, remain byte-for-byte unchanged. The structured analysis report is
published in draft [PR #18](https://github.com/Stonefly-Labs/Hoard/pull/18).
No remediation is needed. The next separately authorized stage is **`implement`**,
but execution remains blocked on reviewer approval or explicit reviewer
authorization for all 40 unchecked custom checklist items. Existing advisory
assessment is not approval, and this analysis does not change that gate.

README and this guide record the analysis and next gate. Provider/compatibility,
custom-host and other example guides, predecessor artifacts, charter/product
specification, baseline architecture/ADR/diagrams, constitution/backlog and
IaC/release/UI guidance are unaffected: analysis changes no requirement, design,
API, dependency graph, runtime/support claim or operational procedure.
No product, .NET/native-client or IaC acceptance is implied by this documentation
checkpoint; no implementation, workflow, qualification, release/tag, publishing,
infrastructure operation, repository-setting change, deployment or merge occurs.

### F-07 partial implementation checkpoint

Complete package-component replay now passes all 155 discovered composition/
version identities with exact result-set equality and unchanged consumer bytes.
Source-mode checks pass 148 rows. This verifies the existing declaration/
mapping probes, optional-target cases and explicit version fixtures, closing
T042/T043/T053 without changing the runtime validator or widening ranges.
Ownership/controller, inherited-profile and remaining structured transport work
remain unfinished. The stage remains `implement / running`, 46/86 checked.

The two packaged CP-01/02 rows now emit bounded owner-linked snapshots rather
than unstructured text when explicitly requested by the safe controller. Fresh
seventeen-package execution independently admits both actual schema4 proofs and
six observed before-initialization/ready/stopped snapshots. Missing stages,
changed images/context, false ready/cleanup counters and cross-attempt snapshot
replay reject. A scoped review found that an earlier decoder lost genuine
partial-failure proofs; reproduced zero/one/two-stage controls now retain the
original failed witness, safe diagnostic and available observations. Full tooling
passes 486 tests with nineteen explicit native skips; all 86 runtime logger cases
and focused formatting pass. This remains a macOS diagnostic component, with
filesystem/native SQLite explicitly unobserved, not Linux containment, full T046
integration or qualifying profile evidence. No additional task is checked.
Exact earlier native run40407642140 at `d604993` also passes all five existing
diagnostic jobs; it does not verify this later snapshot increment.

T044 continuation moves the shared cooperative/noncooperative callbacks into
the packaged Host's `OwnershipFixtures.cs`, preserving existing cancellation,
underlying-task and frozen incomplete-stop assertions. Exact packaged discovery
exposes a separate catalog gap: CP-16 lacks both Boolean parameters and CP-17
omits the late-fault shutdown variant. Two tests-first subcases reproduce the
omissions; regenerated SDK data now requires all seven actual CP-15/16/17
identities. All seven source and packaged rows pass, with exact catalog/
discovery/result equality and the packaged callback-owner assertion. Fresh
seventeen-archive and locked replay pass, as do the two safe baseline/replacement
rows again. Full tooling passes 487 tests with nineteen native skips. Native
exact-child containment, safe conversion of ownership output and remaining
T044 obligations are still open; 46/86 remains unchanged.
Native run40415198673 at exact `22ddff9` now succeeds in all five existing
diagnostic jobs after retrying only failed lock preparation on unchanged source.
Attempt1's `CleanupIncomplete` remains recorded; no root cause or cleanup fix
is inferred from attempt2's successful fresh locked replay. These jobs are not
full qualifying profiles or native execution of the seven composition rows.

The next T044 increment adds safe observation transport for all seven ownership
rows. It reuses the bounded composition envelope with a closed stage-specific
counter shape, not arbitrary event text. Actual callback work completion/faults
remain distinct from callback barriers and the frozen stop/root result.
Independent policy requires exact cancellation/retained/settled/stopped sequences
for every parameter and never reclassifies retained roots as released. Fresh
seventeen-package execution admits nine passing schema4 proofs and nineteen
snapshots, including both baseline rows, through the strict logger and independent
RunInputs/image/owner/stage decoder. All 90 logger cases, seven source ownership
rows and 490 tooling tests pass (nineteen native skips). Scoped architecture
review reports no confirmed defect; it is not T081 or native validation. Earlier
claims that ownership output is unstructured describe the preceding checkpoint.
Native exact-child containment, CP-14/18 integration and full qualifying profiles
remain unfinished; no task/checklist status is advanced.

The dedicated native component entry is
`python3 scripts/conformance_composition_checks.py --evidence /private/parent/run`.
Its existing parent must be user-owned and mode 0700, outside the repository.
Unsupported hosts reject before allocation. The diagnostic builds seventeen
archives, prepares only a private consumer lock, locked-replays that consumer
with a fresh cache, and binds the exact nine identities and safe context to an
owned child command. Its immutable command record covers the input/owner/test
manifests, settings, configuration, consumer, packaged Host, SDK, logger and
runtime configuration; manifests additionally bind the remaining images,
archives and locks. Independent ingestion checks actual snapshots before input
recomputation and real process-resource release. Retained module roots remain
incomplete even when process resources release. The added Linux workflow job
has not yet executed; 493 local tooling tests pass with nineteen native skips.
This is not a qualifying profile, final T044 closure or portable proof retention.

The initializer-failure row now uses the same packaged controlled callback and
safe owner transport. It records faulted work and the rollback stop already
performed by `StartAsync`, while distinguishing the absent public stop result
from later complete root disposal. One independent-policy and one logger-stage
test first fail. Actual package execution then exposes an incorrect pre-disposal
stop-count assumption; the exact policy now requires the observed rollback
stop and rejects its omission. Eight focused source rows, 91 logger cases,
494 tooling tests (nineteen native skips), fresh seventeen-package locked replay
and independent ingestion of ten proofs/twenty-one snapshots pass.

The original native diagnostic at `168828c`, run40423940683, fails `InputChanged`
before launching the test child: its command closure contains ordinary writable
build/configuration files, but owned execution requires mode 0400. The entry now
seals all declared runtime images and bound command files before capture, and
emits bounded closed phase labels. Native validation of this repair is pending;
the failed attempt is not reclassified. Superseded run40421829046 was cancelled,
not observed green. CP-14 schema branches, CP-18, complete containment/profile
integration and T044 remain open.

The paired schema-denial/recovery increment binds each actual composition owner
separately instead of attributing both roots to an unused aggregate fixture.
Frozen owner indices require denial/stopped evidence from owner zero and
repair/stopped evidence from distinct owner one, in global stage order. Safe
failed attempts retain their original ordered owner/snapshot prefixes without
claiming repair. Controls reject swapped/reused/missing owners, early repair,
erased failures, optimistic cleanup and unauthorized/missing worker entry.
Actual repair snapshots await both real protocol/identity worker entries;
an initial component attempt exposes the missing wait rather than treating an
asynchronous one-worker snapshot as success. Fresh seventeen-package construction
and fresh-cache locked replay then independently admit all thirteen proofs and
thirty-three snapshots. All 95 logger cases and 496 tooling tests pass with
nineteen native skips; catalog/inventory/format checks pass.

The sealed native successor at `97a24f1`, run40425468998, reaches `runtime-command`
but fails `UnknownDiagnostic`: it routed VSTest output through the closed build
projector. The corrected entry uses the existing closed `tests` projector,
without relaxing diagnostics. Native replay is pending; both failed native jobs
remain failures. Complete containment/controller acceptance and T044 remain open.

Exact `e9a158979d1d3e2028d6aefd3286aa48668da9f7` subsequently passes the native
composition job in run40426812284: all thirteen proofs/thirty-three snapshots,
fresh-cache locked replay, immutable command/input validation, completion input
recomputation and actual process-resource release. Module/root qualification and
profile completion remain false. The private command parent digest is
`d59f6ccc3a7bfbf99e6860d10d96c1f045d30438d3f9cdd5f6e4587784e2d64a`.
Both earlier failed jobs remain recorded; this is not a full workflow/profile
result. Bounded architecture review finds no confirmed defect and does not
replace final T081 review or independently establish native acceptance.

The short job now lives in `conformance-composition.yml`, with independent
concurrency from the longer foundations workflow; no older diagnostic need be
cancelled merely to admit a new composition probe. A small follow-up separates
the platform probe from the component environment, explicitly marking SQLite
version/provenance `unobserved` and binding both environment files to the owned
command. The summary exposes this admitted environment. Native validation of
that metadata/workflow follow-up is pending; no full qualification is implied.

The independent composition workflow now passes at exact
`f6e9db42f227686c865c924ba5b00cfe5bd4e3b5`, run40427660565/job121937366800.
Its thirteen real proofs/thirty-three snapshots pass input/environment binding,
native child execution, independent admission and actual process-resource
release. The summary explicitly records SQLite `unobserved`, Linux x86_64,
SDK10.0.403/runtime10.0.14 and the actual hosted runner/filesystem; it does not
pretend the setup action's requested SDK10.0.203 is the selected SDK under
`global.json` roll-forward. T044 is now checked, 47/86; implementation continues
to T045. This closes bounded CP-14..18 probes, not full profile qualification,
portable evidence retention or final architecture review.

T045 now moves actual Local-store authority/guarantee admission and active-request
callbacks into `OwnershipFixtures` in the packaged Host. Three assembly-owner
assertions first fail against consumer-local delegates; the unchanged selection/
restart control passes. Fresh seventeen-package construction and fresh-cache
locked replay then pass all four CP-19/20 cases. Both source-mode CP-20 cases and
the thirteen-proof/thirty-three-snapshot safe regression pass. All 496 tooling
tests pass with nineteen explicit native skips; catalog/inventory and focused
format checks pass. T045 is checked, 48/86. These ordinary package assertions
do not establish new safe CP-19/20 transport, native evidence or qualification;
T046 continues the complete composition/inherited-profile integration.

The first T046 transport increment extends the closed SDK/logger shapes and
independent source policies to CP-19 store denial/repair and CP-20 selection/
configuration/request drain. Each repair/restart has its distinct actual Host
registry owner; terminal stages retain real store readiness, worker entry,
request/task settlement and root outcomes. Four logger store-stage and nine
restart-stage tests first fail; both independent positive controls first reject
missing policy. Fresh seventeen-package construction/fresh-cache locked replay
then independently admits seventeen proofs/fifty-one snapshots. Source CP-20
passes both cases, the logger passes 108 cases, and tooling passes 498 tests with
nineteen native skips. All focused format/catalog/inventory checks pass.
The first source compile incorrectly referenced an inaccessible lifecycle
composition member; the observation now reads the public enabled-module
snapshot and compiles/passes. T046 remains unchecked, 48/86. Expanded Linux
replay is pending; inherited inventories, all CP transport and full qualification
remain unfinished.

All CP-01..20 rows now emit safe matrix observations for preconstruction
rejection, repair readiness/stop, disabled effects, optional edges/capabilities,
multiplicity and mapping publication. Four logger matrix controls and eleven
independent declaration controls first fail. The first all-CP attempt discovers
that selecting the declaration theory includes four endpoint-declaration
parameters missing from its manifest. These now belong explicitly to CP-11's
catalog witnesses; the method-level selector is not relaxed. Actual execution
also rejects an incorrect mapping policy: rollback has already stopped all
three modules before the rejected snapshot, while their unmaterialized fixture
services receive zero disposal callbacks. Independent challenges reject erased
rollback and invented disposal. Fresh seventeen-package construction/fresh-cache
locked replay then admits thirty-six exact identities/110 snapshots.
All 34 source matrix cases, 112 logger cases and 500 tooling tests pass
(nineteen native skips); focused formatting/catalog/inventory checks pass.
Exact `cb8d6eb`, run40430393637/job121946361759, separately passes the prior
seventeen-row/fifty-one-snapshot native scope with actual process release.
Its success does not qualify the later thirty-six-row scope. T046 remains
unchecked, 48/86, pending complete inherited lifecycle/configuration/discovery
integration and profile evaluation.

Exact `59d9eff5c6c8ddc4ea2a95e5662154c846dab52b` subsequently passes the complete
CP diagnostic scope in run40431979915/job121951597034: 36 proofs/110 snapshots,
native containment and actual process-resource release. It remains explicitly
non-qualifying, with native SQLite provenance unobserved.

The next T046 transport increment discovers an inherited identity collision:
xUnit truncates twenty configuration-structure theory displays into twelve
distinct strings. Hashing only display text therefore fails exact inventory
admission. Opaque identities now use `testCaseSha256`, the lowercase SHA-256 of
strict UTF-8 `adapter-case-id-in-D-format + "\n" + actual-display`. The actual
adapter ID and private display are consumed only in memory. An independently
discovered exact manifest and real execution admit all twenty cases without
persisting private arguments; source bytes match the frozen F-06 assertion file
and platform runtime bytes match actual candidate archives. Changed displays,
changed IDs, copied opaque labels and literal/opaque aliases fail closed.
All 124 logger cases pass, and the same fresh seventeen-package/fresh-cache
component still admits all 36 CP proofs/110 snapshots. This bounded source-mode
experiment is not a complete inherited inventory/controller or native profile
receipt. T046 remains unchecked, 48/86; production APIs, architecture diagrams,
governance, infrastructure and release behavior are unaffected.

The safe discovery experiment is now a committed, locked test-only executable at
`tests/fixtures/conformance/Discovery/`, using typed VSTest discovery events.
It writes only opaque case projections to a create-exclusive bounded output and
prints closed control events. Unknown warnings/messages fail closed. An actual
run exposes an incorrect extension-directory argument; passing the exact staged
xUnit adapter DLL fixes the warning rather than allowing it. Nested adapter
banners use the existing logger classifier.

`python3 tests/fixtures/conformance/baselines/freeze_composition_inventory.py --check`
reconstructs the new immutable catalog from F-06 Git objects without modifying
the existing metadata/artifact inventory. It covers 203 methods/525 parameters,
including the lifecycle/configuration/discovery boundary suites, every CFG/D
method assignment and all forty LC/controller obligations. Actual assertion and
helper source files remain byte-identical to F-06. Independent admission pins
the full canonical catalog digest; a fully resealed changed parameter count first
passes incorrectly, then fails after the pin is enforced. Missing/duplicate/
foreign/raw/extra-key discoveries and changed sources also reject.

Actual committed-client discovery admits all 509 composition parameters
(172 lifecycle, 201 configuration, 136 discovery). This is not execution;
the six architecture methods/16 parameters and prepared controller journeys
remain required. The native composition diagnostic now attempts this discovery
as an additional owned child with sealed runtime/source/method inputs and exact
output-byte hashes. At that checkpoint, native replay remained pending. T046 remains
unchecked; the public qualifying composition profile remains unfinished.
The first expanded native attempt (`1c47134`, run40435425402) rejects
`OwnershipInvalid` before inherited child launch because the full image closure
exceeds the recorder's sixteen direct-file bound. The repair preserves that
bound: a sealed request pins the full closure, verified in the child before/after
discovery and independently recomputed by the parent. Local actual discovery
verifies all 178 images and admits the same 509 identities; all 137 logger/
discovery cases pass. The original native failure remains recorded.

Exact `6178a775281ed8a17742d82524b12de340b9762d` subsequently passes
[run40435964976](https://github.com/Stonefly-Labs/Hoard/actions/runs/40435964976),
job121964573833: 36 CP proofs/110 snapshots, all 509 inherited discovery
identities, verified closure and actual process-resource release. This is
discovery, not inherited runtime or profile qualification.

Scoped `conformance_inherited.controller_transport` now adapts borrowed
controller commands without changing their standalone entry points. Unknown
commands reject before launch. Evidence variables are explicitly forwarded only
to owned files, hashed before/after each command and restored with the original
entry points/environment on exit. A real missing-variable boundary failure
motivates this explicit handoff. Configuration publication uses unreaped owned
leaders, finite exact barrier reads and complete group settlement; no raw spool
or unbounded `communicate` is retained. Discovery bodies must use the fixed
synthetic wire vocabulary and agree with their observation, lifecycle and exact
byte count; a boolean/integer JSON alias first passes incorrectly, then rejects
with canonical typed comparison.

The dirty-local source snapshot
`4f99a9b2c58ba9cf4caef1516f825c3c6f7098e92d8c4781aeaf30fd3d7e887e`
prepares all four evidence families and independently admits all 509 composition
and 16 boundary parameters, with 695 bound controller read inputs. The first
whole-assembly attempts remain failed: one has an incorrect staged normative
contract location, and the corrected layout still reaches the two-minute child
timeout. Reproducing the frozen tests' repository-relative layout and executing
58 exact class scopes preserves that timeout and the complete parameter union.
The later typed-body repair admits all seven retained actual bodies; all 514
tooling tests pass, nineteen native skips. No frozen assertion changed. Native
inherited execution, complete controller/mutation/freshness acceptance, public
profile integration and T046 remain unfinished; task count stays 48/86.

`conformance_evidence.inspect_inherited_runtime_attempts` now owns independent
whole-inventory inspection. It derives exact class scopes from both frozen
discovery inventories, supplies its own complete expected parameter sets, and
re-admits every scope's raw manifest, owner, witnesses, completion and proofs.
The union must include every composition and boundary scope exactly once.
Scope inputs share source/package/environment/run identity and owner bytes;
runtime/configuration inputs must also agree within each assembly. Changed
case assignments, partial theories, omitted boundaries, replayed attempts or
executions and resealed cross-scope inputs reject. Valid failed transport
remains inspectable but never becomes a complete passing execution. Results
stay immutable, nonqualifying and separate from historical controller, native
containment and public-profile acceptance. This internal inspector is not a
new public CLI or evidence of those still-open gates.

The inspector re-admits all 525 retained actual parameters across 58 scopes at
the earlier `4f99a9b` source, after checking the recorded controller inputs,
runtime/package bytes and snapshot with its explicitly bound prepared consumer
lock. Receipt SHA-256:
`4e154892a495985df4277f1d4eac543c72c95d4b8e780dda6142882c59f63a86`.
This is historical transport inspection, not fresh execution or retained
parent-clock corroboration; its bounds come from the retained witnesses.

At dirty-local source
`824ab5a64b4a610f996a9d4ec3669306adb4e762fca039766008452103c8e9ee`,
fresh seventeen-package construction/locked replay and foundation preparation
pass. Both whole-CP and class-CP attempts reach the unchanged two-minute timeout
(29/36 and 30/36 passed); all 36 parameters/110 snapshots then pass in fourteen
complete method scopes. No theory is split. Fresh lifecycle preparation fails
in the host journeys on three attempts, including a controlled-environment run.
Related same-binary probes observe cancellation at the unchanged twenty-second
fixture deadline. One controlled probe passes both hosts, but fresh preparation
still fails, so neither the cause nor an environment repair is established.
The later controller phases and fresh inherited execution have not run. Earlier
failures remain failures; neither timeouts nor assertions were weakened.
`python3 -m unittest discover -s tests/tooling -v` passes 516 tests with nineteen
native skips. T046 and the implementation stage remain incomplete.

Subsequent isolated timing instrumentation identifies framework configuration
watching: `WebApplication.CreateBuilder` alone can consume nineteen seconds,
with further disposal delays. The conformance child environment now explicitly
sets `DOTNET_HOSTBUILDER__RELOADCONFIGONCHANGE=false` through one shared fixture
environment map, in both legacy transport and native owned execution. The
unchanged baseline/custom binaries pass in roughly 150 ms with their original
deadline and assertions; both environment regression controls first fail, then
pass. These synthetic hosts have no framework appsettings reload scenario.
Hoard's explicit configuration evaluation, publication, immutable active
selection and fresh restart paths remain enabled and required. This is a
test-harness environment setting, not a product host behavior change or a
waiver of fresh controller/native/profile acceptance.

Fresh clean-commit `5359f57` validation then passes seventeen-package construction,
fresh-cache locked replay, all 36 CP proofs/110 snapshots without partitioning,
all four real controller preparations, and all 525 inherited parameters in 58
class scopes. The independent scope admission digest is
`d1233b0a4d0e4dafba44bb5dd23dd3c094d688779499fb661c0448b0c1fe7ba8`;
695 private controller inputs remain unchanged. An earlier attempt correctly
rejects an assets-file change because driver restore/build followed input
freezing. Completing preparation before freezing fixes the ordering, not the
input check. Linux run40447989258 passes at exact `5359f57`, still with the older
36-CP/509-discovery-only native scope.

The committed diagnostic executor now promotes the complete execution path:
build both inherited assemblies and the discovery driver, prepare all four
borrowed controller families, stage the normative contract at the frozen
repository-relative location, and discover both exact staged assemblies.
Each of the 58 complete class scopes uses a fresh logger manifest and native
owned command receipt with independently checked argv/cwd/input agreement.
A sealed private fixture-input descriptor keeps the direct-file bound at
thirteen; private inputs and runtime images are rehashed around each child.
The existing whole-inventory inspector independently admits the final union.
Native replay of this extension is pending. Borrowed preparation retains
`controllerNativeContainment=false` and `fullControllerAcceptance=false`;
its input descriptor is not a native I/O trace. Historical sealing before
candidate builds, complete controller/mutation obligations, public composition
profile integration and T046 remain unfinished. No budget or frozen assertion
changes, and no new qualification claim follows.

The first extended native replay, run40449473314 at `d6b2aeb`, passes package
construction, whole CP execution/admission and inherited source builds, then
fails during borrowed preparation with `EvidenceIncomplete`. It is not a
525-parameter native success. Closed controller/operation/error-code progress
now identifies preparation failures without persisting raw diagnostics;
that subsequent diagnostic replay is pending.

Run40449999083 at `6c2ddca` localizes the same failure to foundation preparation,
outside its command transport. A focused reproduction identifies a native-only
input difference: the owned source snapshot is mode 0400, and legacy source
copying preserves that mode before the second CustomHost recipe edits its
derived project/program. That write fails on an ordinary runner. The scoped
controller adapter now makes only bounded, symlink-free owned working copies
writable; original snapshot bytes/modes remain sealed. The regression first
fails, then passes, and an outside sentinel/symlink challenge rejects before
copying. Native confirmation of this repair is pending. Failure output also
retains only allowlisted repository script names/line numbers, not raw exception
messages, paths or child diagnostics.

Run40451074081 at `85b8917` confirms foundation preparation now passes, then
fails the lifecycle boundary transport at its parent-directory SDK-feed lookup.
The native feed is `feed/candidate`, not the private helper's former `feed`
layout. Borrowed boundary invocations now receive explicit owned SDK-archive
and prepared logger paths, checked before/after execution. This also prevents
the logger helper from building an implicit checkout-local copy. Existing
standalone callers retain their original lookup when no override is supplied.
Native replay of this binding repair is pending; earlier failures remain failed.

Exact Linux run40451900182 at `f319b77` now passes all four preparation families,
36 CP proofs/110 snapshots and all 525 inherited parameters in 58 actual owned
class scopes. Each scope has a native command-parent receipt; all 696 private
fixture inputs remain unchanged and actual process resources release. Source:
`a56adf5f1ccd482639deb73ee825172659db21dbcb71b15a712f8f406d569471`;
CP input:
`ec0fb1cecac743e1491dd2063a80ec4f5393728c721adae3a7a47b6388f03c3e`;
complete inherited scope admission:
`40984cc223e9e7387aa741329284b614c77d4a753a1a6024cb55d03434f8b562`.
Native containment describes those runtime children, not borrowed controller
commands. `controllerNativeContainment`, `fullControllerAcceptance`,
`profileComplete` and `qualification` remain false.

The public entry now routes an unchanged complete composition catalog selection
to that same native executor:
`bash scripts/validate-conformance.sh --profile composition --evidence /fresh/private/path`.
Like the metadata/artifact routes, successful observations still end with
`Incomplete`/`EvidenceIncomplete`, exit 2, until independent full acceptance is
delivered. Omitted/duplicate keys, focused/custom/mixed selections cannot launch
a substituted batch; known native failures keep their codes and borrowed runtime
exceptions produce a safe incomplete result. The composition diagnostic workflow
now exercises this public entry and requires its expected nonqualifying exit,
completed native summary, exact CI source/input agreement and released resources.
An early incomplete failure cannot pass just by returning 2. Public-entry Linux
replay subsequently passes at `5d2e959` in run40453911841/job122022680973:
CP36/110, inherited525/58, all 696 unchanged private inputs and released
processes, with expected incomplete exit 2. Source
`c8bedc8e0824d47b282afe64d16500183e018c27b7f1678c3022ec3c3d0d06e3`;
CP input `0046b7bc06d865c41791c1b7f2b2eff5d048a3ee31e5d0409339b0d4d09d3a68`;
inherited scope admission
`843700209e04f1db13fbc300d2f200a67cc1f1d83cb9eb70af9982d1ada81c7c`.
Historical pre-candidate sealing, full controller/mutation
acceptance, portable independent evaluation and T046 remain unfinished.

The historical-ordering continuation exports the exact F-06 recipes before
creating the candidate feed or executing candidate commands. Registration is
prepared once against F-01; configuration retains its two F-02 binaries and
discovery its three F-03 binaries. A private run/root-bound descriptor seals
recipe/source bytes, projects, build outputs, assets and local archives.
Package caches are not represented as immutable historical project trees.
All sealed inputs are rehashed before/after borrowing and around runtime
children. Candidate compatibility recipes copy complete prebuilt project trees
into separate writable replays; they do not restore/build the historical
projects again or replace sealed originals with candidate dependencies.
Registration's original standalone behavior remains available without a
prepared input. The first focused regressions reject the missing preparation
API; subsequent checks cover late preparation, foreign seals, changed ownership,
changed binaries and dependency replacement confined to a replay. Native
confirmation of the reordered public route is pending. Borrowed preparation
still does not have native owning-command receipts; full controller acceptance,
profile evaluation and qualification remain incomplete. T046 is unchecked.
These are tooling changes; product contracts, examples, diagrams, infrastructure
and release behavior are unaffected.

The workflow's retained-seal check must run after actual store release. A
focused replay first reproduces `InputChanged` when that check tries to rehash
already-deleted historical project files. Runtime still verifies all live
historical bytes before cleanup; afterward CI checks the retained descriptor's
exact digest, run/root identity, baseline and nonqualifying mode instead of
requiring deleted stores to exist. Changed bytes, resealed foreign ownership
and false qualification reject. Native confirmation remains pending.

Run40455417840 at `b10def8` confirms the historical ordering at runtime:
CP36/110, inherited525/58, all 2,011 bound private inputs, unchanged sealed
historical binaries and actual process release. Its workflow still fails at
the post-release rehash described above; it is not a successful CI receipt.
Historical seal:
`1cacc48475daded10bdb3703281bbb4faea284156885dd74bdfd9ce933afc358`;
inherited scope admission:
`02b398e7dac50857ebe185b5611715b3dec24cc561067c6107c3641c01355592`.
The separately pushed `f602db4` workflow repair passes
run40455993703/job122030077361: the same CP36/110, inherited525/58, 2,011
unchanged inputs and released resources, plus successful retained-seal CI
checks after expected incomplete exit 2. Source
`e121bffd8100e8697ca8081aff8aa0e1be84a8e08d8860794c19f781108c7a21`;
input `181606131048af27205ee3fa87d7ce73ec5e463d4ded075577ec7636ea4ce1d2`;
seal `631487499f5d50dc15c8930abedd533d0bb23ff6678814005470c631e675026a`;
scope `4a938c6af12ea17f9bed55e81fb1b48ab34534dea4cef0ce9ec4cf6615fc59dd`.

The next continuation wraps historical preparation and four-family controller
preparation in two bounded native child scopes. Each has a sealed request,
source-script binding, native argv/cwd/input/output receipt, exact closed phase
progress and actual namespace/group exit before its result can be consumed.
Controller preparation uses a separately staged immutable logger so a solution
rebuild cannot overwrite a native-bound logger input. Legacy subprocesses
remain inside those scopes; this is batch containment, not a native receipt
for every inner command or complete controller obligations. Raw progress,
unknown failures, changed outputs, omitted phases and optimistic retained-group
claims reject in focused checks. The first parent regression also catches a
wrong receipt property name before native handoff. Native replay is pending;
`controllerNativeContainment`, `fullControllerAcceptance`, `profileComplete`
and `qualification` remain false. No frozen case, assertion or timeout changes.

Run40457447997 at `f6372fe` fails before candidate construction with
`UnknownDiagnostic`: isolated Python omits the script directory, so the new
child cannot import its sibling modules. An actual `-I -S` entry regression
first exits 1 with an import failure, then safely returns its expected
`EvidenceSchemaInvalid` event/exit 2 for a malformed request after admitting
only the sealed script directory explicitly. No private input or traceback is
emitted. The nineteen inherited and five composition/workflow checks pass;
native replay of this bootstrap repair is pending.

Run40457814600 at `b86f79d` passes isolated import bootstrap but fails during
native historical preparation; it is not a successful receipt. The native
guard prohibits `setsid`, while the legacy transports normally request a new
session. Preparation now borrows only its admitted leader's existing group:
Linux leader identity and the ownership ledger's PID/start witness must agree.
Direct children are bounded and reaped without killing their shared group.
Descendant settlement remains the outer native owner's responsibility; a
retained descendant still fails that parent's actual group-exit check. The
standalone legacy transports retain their separate-session ownership behavior.
A Linux-only regression installs the actual guard, first requires rejection
of a legacy nested-session launch, then executes the same child in the admitted
group. Local conformance tooling passes 427 tests with twenty Linux-only skips;
the actual guarded regression and complete native replay remain pending.
No controller/profile qualification, task marker, catalog or budget changes.

Run40458672367 at `c11415b` gets through the historical native wrapper and
CP runtime ingestion, then fails the controller-preparation wrapper with
`OutputLimitExceeded`. It is still a failed receipt. The parent now re-admits
and exposes only its already-closed progress events on failure, so controller
phase/error localization needs no raw child log or private exception text.

The next controller increment reuses the original standalone BCL-only discovery
consumer with an actual serialized response, not an in-process deserialization
substitute. The complete finite presentation is independently compared before
only module IDs are retained: missing/extra fields or lines, private text,
foreign modules, Boolean/integer aliases and optimistic execution authority
reject. The prepared manifest binds consumer source, image, assets, runtime
sidecars and response bytes into the existing frozen private input closure.
The original discovery entry point uses the same extracted execution helper.
A direct local six-module run of the real unchanged consumer passes strict
presentation admission, with image
`bd676fb670f72156a7c0beca9dd79db6b2d3195abc09e246f07b396aaf1a54e0`.
An earlier isolated fresh-home local restore safely rejects unknown diagnostics;
that attempt is not counted as transport success. Full tooling passes 538 tests
with twenty native skips. Native reference execution, the controller wrapper's
output-limit cause, full controller/mutation acceptance and qualification
remain unverified. T046 stays unchecked and implementation stays running.

Run40459781590 at `79b6757` localizes `OutputLimitExceeded` to lifecycle
preparation (after foundation), before the new reference consumer can execute.
Its failed receipt remains failed. The next diagnostic preserves conformance
error codes through borrowed command projection and emits only numeric
allowlisted script/line witnesses after child authorization; no exception
message, source line, arbitrary filename or private path is emitted.

The original discovery mutation workspace's selective F-04 copy omits current
test SDK/fixture/contract inputs. A focused reproduction fails on the missing
Host project. Setup now copies the complete source/tests/specs/examples trees,
excluding build/package outputs through the existing copy helper, plus the
solution marker and root build inputs. Actual fresh compilation then exposes
missing directly consumed Abstractions and NuGet.Versioning references in the
source-mode composition test project. Both are now explicit; locked source
restore records Versioning as direct at the same 7.9.0 version/content hash.
Package-mode references/lock remain unchanged. Actual fresh source
restore/build, all seven positive static-association guard cases and
`dotnet format <copied-composition-project> --verify-no-changes --no-restore -v quiet`
pass. These are setup/positive checks, not mutation detections: no negative
mutation or complete controller is claimed. Full tooling passes 541 tests
with twenty native skips. Native lifecycle diagnosis/repair and the remaining
full-controller obligations continue; no catalog, assertion or budget changes.

Run40461182891 at `bf7c2fc` identifies `conformance_sources.py:57`, a bounded
legacy evidence read, in lifecycle command 77. A local real architecture
boundary invocation passes through discovery, the safe logger and independent
completion/proof validation. It does not reproduce the Linux failure.
Legacy validation now projects bounded stdout first and preserves a closed
zero-observation logger failure before attempting to read absent completion.
Unknown text still rejects, and successful or expected-negative execution
still requires the complete original evidence. The masking regression fails
before the repair; 432 conformance tooling tests pass with twenty native skips
after it. Linux replay and the underlying lifecycle repair remain pending.

Whole-inventory inspection now derives all 36 CFG and forty D case rows from
the independently pinned method assignments and the re-admitted opaque runtime
witnesses, retaining every theory parameter. A case passes only when every
contributing parameter passes and its scope has no diagnostic failure. Red
controls catch both absent case coverage and optimistic cases from incomplete
scopes; all three focused inherited inspector tests pass. Case coverage joins
the retained scope-admission proof, not a full-controller/qualification claim.

Run40462305943 at `b1b985e` exposes the nested legacy logger's
`EvidenceIncomplete` with zero observations. Its receipt remains failed.
Lifecycle graph preparation is now a separate helper: the inherited preparer
retains actual graphs, not an optimistic boundary count, while mandatory
native runtime execution still independently requires the complete sixteen
unchanged architecture parameters (including all nine lifecycle parameters).
The standalone lifecycle entry point reuses graph preparation and still runs
and validates its original boundary command. Both separation/preservation
controls fail before implementation and pass afterward.
`python3 -m unittest discover -s tests/tooling -v`: passed, 545 tests with twenty
native skips. Linux replay and complete controller acceptance remain pending;
no assertions, catalog entries, guard policies or budgets are relaxed.

The completed ownership job122053946415 in run40463591758 executes 433 Linux
tests with zero failures/errors/skips, including the actual group-guard
regressions, but correctly fails `UnknownDiagnostic`: the historical-baseline
unit test leaks three expected progress records. A safe-result reproduction
observes 295 diagnostic bytes before the repair and zero afterward, with all
twenty inherited tests passing. The test now privately captures and asserts
the exact three events, rather than weakening the safe runner or discarding
unknown output. The three inherited inspector checks also confirm opaque
coverage remains accepted by both original CFG and D case verifiers.
Fresh Linux wrapper confirmation remains pending.

The enlarged inherited input closure now passes at exact `8f46a2c` in
[run40465825066](https://github.com/Stonefly-Labs/Hoard/actions/runs/40465825066):
CP36/110, inherited525/58, 2,124 unchanged bound inputs and actual release.
The next prepared-project formatting increment binds generated NuGet imports,
assets and archive caches and requires an individually re-admitted native
command receipt for every selected project. Local receipt/input-drift controls
pass; native confirmation is pending. This does not establish whole-solution
native formatting, full controller/tooling/mutation acceptance or qualification.
Rehashing uses the existing bounded descriptor-relative input reader; a
same-byte symlink substitution fails without admitting an unbound target.

The safe-unit wrapper at `8f46a2c` is independently green in run40465825259,
job122064084083: 433 tests, zero failures/errors/skips and code `None`.
The same checkpoint's locked-replay, metadata and artifact diagnostic jobs pass;
the separate SDK diagnostic is not inferred to have passed.
`python3 scripts/conformance_unit_checks.py --all-tooling` now selects the
documented complete `test_*.py` tooling scope while retaining the same strict
output projection and rejection of skips/unexpected stdout. CI uses this mode.
It reports the selected scope and unexpected diagnostic byte count without
retaining raw framework output. Locally it observes 548 tests, no failures/errors,
zero unexpected diagnostic bytes and twenty explicit native skips, returning 2.
This is not a full-controller tooling proof; fresh Linux full-scope execution
and attributable integration into controller acceptance remain pending.

Prepared-project formatting now passes natively at exact `78a8486`,
run40467841673/job122069149790: forty individually admitted commands
(foundation7/lifecycle9/configuration12/discovery12), CP36/110,
inherited525/58, 2,281 unchanged bound inputs and actual release. The complete
tooling scope also passes independently at exact `7ff5499`,
run40468960470/job122073676284: 548 tests, zero failures/errors/skips or
unexpected diagnostic bytes. Neither receipt claims full-controller acceptance.
The next whole-solution formatting increment restores missing assets in locked
mode, including `Build=false` projects, adds the needed private contributor
package and freezes every tracked source input. Native confirmation now passes
at exact `cfb20eca20f41d0a85b1f7c0adb76baf89ef20d8`,
run40471161893/job122080437087: 41 individually admitted formatter commands
(7/9/12/12 prepared plus one whole solution), CP36/110, inherited525/58,
all 3,181 unchanged inputs and actual release. `solutionFormatting=true`;
full-controller acceptance and qualification remain false.
CP input `b96fce78a07444eb9854eaa1695b0515288ed2be9a75dd3d0d3e28418cf93323`;
scope admission `f38a3a5b9be1ae2f73ad25f638818dd76313f54e9b52c6f2600a17f987b29fbc`;
historical seal `af6d8b561b9b8ef9b5ea35b4cd116fa872bd6fce5b40d837a2264f376372a1fc`.
Controller-bound tooling/mutation obligations remain pending.

The safe logger and Python transport admission now permit a composition-wrapper
assertion symbol only when it exactly equals the selected fully qualified
method. Existing shared SDK assertions remain supported. An actual bounded
xUnit assertion prefix and exact stack frame are still required; an unknown
failure remains unknown, and an assertion failure never becomes passing evidence.
Five focused logger controls first expose the missing wrapper admission, then
pass with all 129 logger cases; all 550 tooling tests pass with twenty explicit
native skips. The original mutation red/repair executions remain unimplemented.
Provider contracts, public examples and architecture diagrams are unaffected:
this increment changes private evidence classification, not provider behavior.

Actual local, non-native discovery mutation execution exposes an opaque failure
headline mismatch: the adapter renders the private original display while the
manifest contains only its actual GUID/display hash. The safe logger now
correlates a `[FAIL]` headline only to an admitted actual failed result, using
the existing bounded transient hash sets in either event order. Raw displays
remain absent from evidence; foreign headlines, passing results and unknown
exceptions cannot become assertion evidence. Both event-order controls first
fail, then all 135 logger cases and focused formatting pass. All 29 legacy
tooling controls pass with one explicit native skip.
The original `catalog-bound` mutation produces all seven actual assertion
failures with complete safe transport. The original `source-identity` and
`path-protection` wrappers instead dereference missing failure/header state
before asserting. Their unchanged recipes now have finite typed `Guard` scopes,
requiring the exact method, matrix, binding, null-reference prefix and stack
frame. These witnesses remain failed with `EvidenceIncomplete`, never assertion,
passing or complete evidence; unknown adapter messages still reject first.
All twelve actual local negatives and twelve repairs execute through
`run_discovery_mutations`, covering 29 parameters each. Each scope independently
admits actual opaque discovery, logger transport and projection. Retained
original source maps, sealed mutant bytes and staged runtime/driver inputs are
revalidated after all repairs, separately from historical mutable read maps.
The native worker now binds this phase to composition inputs and requires all
24 progress ordinals. Workflow challenges first expose missing mutation/repair
and false-qualification checks, then pass after strict completeness admission.
The 145 logger cases and local real executions pass; Linux integration is
pending. Full-controller tooling/provenance obligations and T046 remain open.
Provider contracts, public examples and architecture diagrams are unaffected:
this increment changes private evidence execution, not provider behavior.

Opaque discovery records now carry the actual VSTest case GUID in addition to
their existing opaque identity and selected method. A GUID alone never proves a
scenario: the inherited inspector recomputes the identity's existing hash using
each original mandatory adapter display and requires exactly one matching
actual case. No raw display is retained, no unsalted private-display digest is
introduced, and no literal label is invented from an opaque hash. A real local
driver run corroborates all four adapter parameters. Complete discovery joins
137 parameters, all ten original suites/classes and D01..D40 to their admitted
runtime witnesses; failed scopes cannot produce passed suites. The original
case/suite verifiers still run for successful coverage. Missing/substituted
GUIDs, duplicate parameters, and omitted adapter/suite summaries reject in
focused red/green controls. This is diagnostic provenance, not native or
full-controller qualification; Linux confirmation remains pending.

Native `750e4d9`, run40480747075/job122110128501, reaches mutation admission but
fails `InputChanged` at the original-source comparison before any negative.
Reusing the prepared build tree as an original snapshot is invalid: that tree
also admits explicit package-acceptance lock derivations. Mutation execution
now receives a separately created immutable snapshot from the same verified
repository manifest, with only the actual compiled discovery driver staged
under its excluded build output. Descriptor-relative creation, no-follow reads,
original byte hashes and pre/post repository agreement are unchanged. A new
control first exposes the missing independent snapshot, then verifies that
prepared changes neither enter the new snapshot nor become accepted originals.
The failed native receipt remains failed; repaired native execution is pending.

Complete tooling runs in the trusted owning supervisor, where its native
executor regressions can allocate their own independently owned groups. It
never runs inside a provider child or gains an exception to the provider's
session/group escape ban. The shared safe runner records the complete declared
and actually started test inventories, bounded diagnostic counts and per-test
safe failure locations; cooperative scheduling stops after the current bounded
test at its deadline. Source bytes are compared before/after, tracked test-module
coverage is exact, and missing/duplicate tests, skips, expected failures,
unexpected successes or output cannot pass. A retained input/run/root-bound
proof is independently re-admitted by the workflow after store release.
Its explicit `trusted-tooling-supervisor` role and `nativeContainment=false`
prevent it from being mistaken for native provider execution. This does not
advance full-controller/profile qualification or T046. Public provider
contracts, examples, diagrams, governance and infrastructure are unaffected.
Actual local supervisor replay observes all 557 declared/started tests, zero
failures/errors/unexpected diagnostic bytes and twenty native skips; the
result is correctly `EvidenceIncomplete`, not passing tooling acceptance.

Exact `1606a448c920c956efb144637b34a89626dd7717` now passes Linux
[run40484685752](https://github.com/Stonefly-Labs/Hoard/actions/runs/40484685752),
job122123411570. It admits CP36/110, inherited525/58, all twelve discovery
negatives and repairs with 29 parameters each, all 137 discovery parameters,
four adapter scenarios/ten suites, 41 formatter commands and all 3,181
unchanged bound inputs. Controller-bound tooling admits all 557 declared and
started tests with no skips or unexpected diagnostics; its private proof is
independently re-admitted after actual store/process release. The repaired
independent mutation snapshot is therefore natively confirmed. Scope admission
is `6d591b8bea07eba994c7abe4d3d30e19ce5c4be875bfc65fbbd8b78d207df98b`,
mutation result
`ae98b8e4c026481f73bbb82038f6d9b86c5c1b4c040d24e701186ff8c79ba24b`
and tooling proof
`ce0d5d6797ab0e0af8c1781c9453621cc1ed148d3fe4a0c81fcdc1ce0e4a23f1`.
The original failed receipts remain failed, and the explicit full-controller/
profile/qualification flags remain false. New material and cross-scope
membership gates at `a42d083` await their separate native replay.

Discovery material admission shares the existing original verifier rather
than replacing it with preparation counts: it requires the exact eleven-file
feed and actual SHA-512 bytes, all three retained binary/provenance records,
eighteen graph records, nine package journeys and matching current-run
performance. The owning supervisor reads the fixed controller manifest once
and checks its preparation hash before admitting these materials. Malformed
or changed materials become closed failures. CI rejects omitted materials,
foreign manifest binding and qualification overclaims after store release.
No new full-controller or native-containment claim is introduced.

The supervisor also independently re-admits all twelve actual negative and
repair projections and compares each complete parameter set with its selected
method in the admitted positive discovery inventory. It verifies actual
failure names, typed assertion/finite-Guard classification, repair success and
integer counters; path substitutions, missing repairs, foreign parameters,
changed bytes and malformed rows reject. Actual retained local execution
passes this gate for all twelve pairs/29 parameters against the actual repair
scope identities. A separate actual positive-assembly discovery also
corroborates all 28 unique selected identities against those retained pairs.
Neither local check stands in for the full native positive inventory.
Complete local tooling now observes 560 tests, no failures,
errors or unexpected diagnostic bytes, and twenty explicit native skips.
Native admission of these new gates is pending; T046 remains unchecked.
Public provider contracts, examples, diagrams, governance and infrastructure
are unaffected.

Exact `a42d0834343291fbe9d6ede57c04f5c8212e3c56` now passes
[run40487687455](https://github.com/Stonefly-Labs/Hoard/actions/runs/40487687455),
job122134815231: all eleven feed packages/three retained binaries/eighteen
graphs/nine journeys, current-run performance and actual positive-to-negative/
repair parameter equality are admitted. It also admits CP36/110,
inherited525/58, all twelve negatives/repairs at 29 parameters each, all 560
controller-bound tooling tests, 41 formatter commands, 3,186 unchanged bound
inputs and actual release. Scope:
`091dcd01db7d3a86a6061b4ab0e47a007e03f4d6eccf29ce23ba96607095e65a`;
material manifest:
`fb592a359c4963f034625606c6729c8cefe40dd90a36d2d2812ce9aa904bf99d`;
tooling:
`926e36caeb02e4f0afb863770c2c80b6d91a1701b7833bdbc6dad10ff1b2d1fa`.
T046 remains open: the native batch boundary is not independently observed
native invocation/input evidence for every inner controller command.

The partial T051 binary controls link the existing
`compatibility/BinaryMemberRemoval` consumer and Old/New contract sources into
four nonpackable test projects with distinct project/package identities.
Contract assembly names/versions deliberately match; compiler-emitted fixture
metadata makes the observed bytes distinct. The single unchanged compiled
consumer throws an actual `MissingMethodException` against the broken candidate
and succeeds against the compatible candidate. Explicit collectible fixture
contexts resolve only the selected contract for that identity, and existing
SDK capture corroborates actual loaded bytes/MVID rather than old DLLs or
matching version labels. Atomic replacement of an already loaded baseline
with actual candidate bytes is rejected as `InputChanged`.

These are trusted compiled test fixtures, not provider/plugin discovery.
Their project references are private/nonreferencing test build dependencies,
and each fixture pins its own locked restore path. Actual package-mode replay
first exposes inherited root-lock propagation (`NU1004`); fixture-local lock
ownership fixes it without relaxing locked restore. Architecture review then
finds hard-coded default output paths: a clean redirected replay first fails
`MSB3030`. Copying MSBuild's evaluated `GetTargetPath` outputs fixes the replay
and prevents stale default-output fixture selection. All three controls pass
in the actual isolated package-mode build with
`BaseOutputPath=bin/package-diagnostic/` and an independently reverified
prepared root lock. Combined source-mode compatibility/binding controls pass
23 tests; focused formatting passes. Historical source-consumer recipes,
sealed predecessor replay and source-break execution remain unfinished.
Product/provider contracts, examples,
diagrams, governance and infrastructure are unaffected.

T051 additionally verifies actual portable PDB document hashes against the
three unchanged fixture sources frozen from the exact F-06 commit. Each PDB's
content ID/stamp must match its actual PE's CodeView record before source
attribution. Tooling independently recomputes the frozen JSON from Git blobs,
not the current working source or candidate labels. All seven source/binary
controls pass in source mode and actual isolated redirected package mode.
A private actual build with only a trailing comment added to the retained
consumer still preserves binary behavior but fails exactly its source
attribution row; six other controls pass. This completes T051's test controls,
not historical source/retained compatibility acceptance or T056. Full local
tooling observes 561 tests, no failures/errors/unexpected diagnostic bytes,
and twenty native skips; expected incomplete exit 2.

The exact `022f5f8` native
[run40490532226](https://github.com/Stonefly-Labs/Hoard/actions/runs/40490532226)
fails controller preparation at command44; it is not acceptance. An actual
fresh source snapshot exposes a related whole-solution build failure:
`MSB3030`, missing compatibility fixture outputs. Direct project builds and
cached solution builds had hidden that the four fixture projects were absent
from the solution's build graph. They are now explicit default-build projects.
A second fresh snapshot restores with locked mode, builds the full solution
and passes all seven compatibility controls without rebuilding the test
project. Focused whole-solution formatting and `git diff --check` pass. Native
confirmation of the repaired graph is pending. No package/provider/API
dependency, fixture source, lock, assertion, example or diagram changes.

T054's internal `conformance_baselines.execute_source_recipes` now compiles
the closed `baselines/source-consumers.json` catalog: twenty unchanged F-06
API consumers, retained marker sources, lifecycle/configuration providers
and operational metadata/artifact providers/consumers, plus all four current
SDK bindings. The latter explicitly have no historical SDK release. Source
copies, original locks, candidate feeds and sealed predecessor sources/
binaries are checked before/after. Actual assets must reference the observed
candidate archive SHA-512 values, not just matching version labels.

Actual replay first finds the older projects' explicit versions incompatible
with the later central-version context (`NU1004`/`NU1008`), then the three
recipes whose original locks live in `Baseline/`. The repair preserves their
unchanged source/project/lock bytes: explicit-version projects disable central
versions only for their build; the shared preparer supports a closed Baseline
lock context and writes alternate hashes only under `obj`. Ordinary and
package-acceptance lock behavior is unchanged.

A fresh isolated local replay builds all eighteen candidate packages from the
current source snapshot, then passes all 24 recipes/48 locked restore/build
commands (102 commands including package builds). Its genuine six-entry
predecessor seal is independently checked before/after, including actual
retained binaries; none is rebuilt during source replay. Twelve baseline
tooling controls pass, including source/feed mutation and archive/asset
substitution rejections. Full local tooling: 565 tests, zero failures/errors/
unexpected diagnostic bytes, twenty native skips, expected incomplete exit 2.
This is non-qualifying local source compatibility, not T055 retained runtime
execution, T056 compiler-break controls or a delivered compatibility CLI.
Examples/diagrams and public provider APIs remain unaffected.

Exact `1f94d191d1268c5a45aaa54a70474e529e7aea5b` now passes the clean-solution
graph's native
[run40493145991](https://github.com/Stonefly-Labs/Hoard/actions/runs/40493145991)/
job122151817568: CP36/110, inherited525/58, all twelve negatives/repairs at
29 parameters each, discovery137/4/10, material11/3/18/9, all 561 tooling tests,
41 formatter commands, 3,208 unchanged bound inputs and actual release.
Scope: `7626f987228559bfd2e2414bf2f44566a04e51e073b01503b4ad32ad932a3d25`;
tooling: `48e47152f93c8acd012f0c344f9e5b4afb7724af612c03564fd68d042570acd8`.
Earlier `022f5f8`/`ed04d63` failures are not relabeled; T046 and all full-profile
and qualification claims remain open.

T055's new observer is a fixed BCL-only, nonpackable test project. The harness
supplies it explicitly as a CLR startup hook to unchanged retained executable
bytes; no consumer/provider DLL or dependency/runtime JSON is rewritten.
Private runtime copies replace only four platform DLLs from exact candidate
archives. The observer temporarily captures bounded console text, validates
the original exact safe output and records actual loaded paths, SHA-256 and
loaded-versus-PE MVID. Only finite events and safe hash/MVID proof rows persist.
It is not a provider discovery/loading mechanism or production dependency.

An actual local replay passes all nine predecessor/F-06 scenarios with forty
loaded assembly observations, preserving the original six-entry seal and
every retained consumer/provider/dependency byte. Memory/SQLite and local/
object-semantics execute the frozen operational consumers' journeys, not
the full current common suites; old metadata/artifact markers remain
marker-only. Actual wrong-hash and old-location challenges reject
`InputChanged`/`ProofMismatch` despite application exit zero.

Native execution now binds request/staging manifests, observer and retained
entry DLL inputs plus exact observation bytes to each owning command record.
Independent admission rejects edited observations, missing/duplicate/foreign
loaded identities, candidate hash or MVID-shape changes, false qualification
and optimistic success. It is wired to all-SDK diagnostics only; selected
category qualification is unchanged. Scoped architecture review found writable
observer inputs and the missing candidate Application archive. Sealing the
observer before native capture and explicitly packing Application before
all-SDK replay resolve those findings. The actual input-reader regression first
rejects the writable observer, then passes after sealing. This is not T081's
final review. Fifteen baseline controls and focused observer formatting pass.
Full local tooling: 568 tests, zero failures/errors/
unexpected diagnostic bytes, twenty native skips, expected incomplete exit 2.
Native confirmation is pending, so T055 stays unchecked. README/plan updated;
public provider contracts, examples, diagrams and infrastructure are unchanged.

The next T056 increment reuses the original RequiredMember and BinaryMemberRemoval
fixtures. Actual local source replay performs eight restore/build commands:
unchanged implementer success, exact `CS0535` for
`RequiredContract.IProvider.Required()`, then success after restoring only the
compatible contract. Consumer source and deterministic output bytes are unchanged;
all historical originals/seals remain intact. A dedicated native build projector
admits that precise consumed member, never another `CS0535` member or raw paths.
Result admission rejects unrelated compiler errors, exit-zero and missing symbol
witnesses. The three existing actual binary exception/compatible/substitution
controls join the full SDK's exact runtime inventory; actual VSTest discovery
corroborates all three display identities.

`python3 scripts/conformance_sdk_checks.py --root "$PWD" --evidence
"$PRIVATE_EVIDENCE/run" --compatibility-only` is a bounded non-qualifying
diagnostic, not the public compatibility profile. It shares the full SDK's
preparation and replay path, then verifies unchanged repository/candidate/historical
inputs and releases all owned processes, caches and stores. Its separate Linux
job does not remove any full SDK/category obligation. T055/T056 remain unchecked
pending native evidence. The actual private source-break probe passes; exact
symbol projection and sixteen baseline controls pass. Full safe tooling observes
570 tests, zero failures/errors/unexpected diagnostic bytes and twenty native
skips, expected incomplete exit 2. A first run exposed two smoke-test positional
assumptions; preserving the original leading scenario order repairs that integration.
Provider contracts, examples, architecture diagrams, infrastructure and governance
are unaffected.

Native confirmation at exact `87e9399515ecdbc7faddc8b95154b346d0450894`,
[run40501112699](https://github.com/Stonefly-Labs/Hoard/actions/runs/40501112699),
now closes T055/T056's implementation/control scopes, 52/86. All six jobs pass.
The bounded compatibility job122179087309 confirms all 24 source recipes/nine
retained scenarios/forty loaded assemblies, the exact source compiler break and
repair, unchanged original inputs and actual owned process/cache/store release.
Its source/retained/break proof hashes are respectively
`fe40c2cae55bb1c82d84b8128fa22e3a259e7ecd5731a4dce702e7a744260d4f`,
`831db8eb8752efc0017c45e2a46f80f490453483127a4c0a70750ce1abc7ff94`,
`a6cd9644165c5e9c9620df183c4306c16cc3ecdf3bbf4bdeb1f5dd28c584cc79`.
The separate full SDK job122179087412 executes the exact three binary
exception/compatible/substitution controls; discovery/completion hashes are
`dc741ec6f4c202b2cc40912485eef579093216ad81fa2bec4c170ccd056d29e5` and
`fab74acf8a9fd0ca703db2eaa6a1c207d4f6f5222aec62b9c0a1533f2eec7bb9`.
These controls assert actual exception type and unchanged loaded consumer/
candidate identity, not merely totals. Full profiles, T046 and independent
qualification remain unfinished. Cancelled superseded run40499315656 is not
counted as acceptance.

The next T046 continuation gives the existing standalone BCL discovery consumer
its own native reference phase after complete solution preparation. It executes
the original compiled consumer and serialized response without recompilation.
The supervisor freezes the manifest, source/project/import/asset/sidecar/response
closure, then checks the identical map before and after the invocation. The
child admits the exact original presentation through the existing safe transport;
the parent independently checks its module and actual argv/cwd digests against
the original manifest, owning native command and exact output packet.
The workflow separately re-admits that original input/output/parent linkage.
Changed or omitted source/runtime inputs, foreign paths, direct package
dependencies, unknown descriptor fields and output substitution reject.
`python3 scripts/conformance_unit_checks.py --all-tooling`: 571 tests, zero
failures/errors/unexpected diagnostic bytes, twenty native macOS skips, expected
incomplete exit 2. `git diff --check`: passed. Linux confirmation of this new
phase remains pending; every other inner-command receipt is still required.
T046 remains unchecked, 52/86, implement/running; full-controller/profile/
qualification flags remain false. Provider contracts, examples, diagrams,
infrastructure and governance are unaffected by this test-only continuation.

The follow-up reference receipt comes from the actual bounded launcher rather
than reconstructing command facts alone. While the native preparation group is
borrowed, capture observes the actual child PID/kernel-start identity and group,
freezes launch argv/cwd and stdin digest, and attaches the reaped exit status.
The reference projection preserves only this closed safe packet. The parent
and independent workflow match the observed group PID/start to the original
native execution record, in addition to the complete unchanged input/output
binding. The child is exited; the group is explicitly still `Borrowed` until
the native parent proves its settlement. No escaping/nested session is created.
An unreaped fast-exiting child can retain its kernel identity without being
classified as live: ordinary liveness/cleanup identity probes keep their
existing zombie exclusion. Modeled missing/foreign/live/stdin-substituted
receipts reject; the actual guarded Linux transport test also checks a
fast-exiting native command. `python3 scripts/conformance_unit_checks.py
--all-tooling`: 571 tests, zero failures/errors/unexpected diagnostic bytes,
twenty native macOS skips, expected incomplete exit 2. Linux confirmation is
pending; T046 remains unchecked, 52/86, implement/running. Provider contracts,
examples, diagrams, infrastructure and governance are unaffected.

Exact `8bdce752366307f89509dad1a4e9168771c1753a` now passes
[run40579834470](https://github.com/Stonefly-Labs/Hoard/actions/runs/40579834470),
job122456613486. The original unchanged BCL replay admits six modules/eighteen
inputs; input map `849a2c264eafe68260ffa68ec10e0e6982628d8ab7b2da4f522a7bfc8c880f0c`,
native parent `b96a5a6024dc580937eda85af5f1f42eed33222a9fc44d712ab27923dc754dca`.
CP36/110, inherited525/58, all twelve original negatives/repairs (29 parameters
each), discovery137/four adapters/ten suites, all 571 tooling tests, 41
formatters, 3,216 unchanged inputs and actual release also pass. All six
foundations jobs pass in run40579834545. This confirms the earlier reference
phase, not the later actual-child receipt or journal extension.

The next extension retains a bounded closed launch journal for historical,
controller, reference and mutation native phases. Both finite capture and
interactive `OwnedChild` settlement append actual process/group identities,
argv/cwd, supplied stdin digest and reaped status. The original configuration
controller still checks staging before its kill; no timing/assertion is
replaced. Internal success packets use schema version 2 and include that
journal. Parent admission rejects missing, duplicate, foreign-group and
unsettled observations. CI independently re-opens each original packet/native
parent and checks exact output/hash/owner linkage; reference must match its
single original child observation. Summary receipts explicitly retain
`inputClosureComplete=false`: this is launch observation, not every command's
complete read set. Full safe tooling remains 571 tests with zero failures/
errors/unexpected diagnostic bytes, twenty native macOS skips and expected
incomplete exit 2. Native journal confirmation remains pending; T046 remains
unchecked, 52/86, implement/running. Provider contracts, examples, diagrams,
infrastructure and governance are unaffected.

Exact `42115be5cccb5ac757ed01a5ebd14f3932815974` now confirms the actual
reference-child/group receipt in
[run40581441462](https://github.com/Stonefly-Labs/Hoard/actions/runs/40581441462),
job122470521931. All six foundations jobs in run40581441420 also pass.
Exact `c72ba970e7bb1292bffe425554c4e2899c4b9fb4` subsequently confirms
the four original launch journals in
[run40584775906](https://github.com/Stonefly-Labs/Hoard/actions/runs/40584775906),
job122483743130: historical45/controllers230/reference1/mutations73. Independent
CI re-admits their original output/native-parent bindings after stores release.
CP36/110, inherited525/58, all twelve original negative/repair pairs, discovery
137/four adapters/ten suites, 571 tooling tests, 41 formatters, 3,216 unchanged
inputs and actual process/cache/store release pass. These are schema-v2 launch
receipts, not confirmation of the subsequent selected-input extension.

Internal success transport v3 adds one selected-declared-input snapshot per
actual launch. The trusted selector captures owned project/source/ancestor
configuration, available assets, runtime images/sidecars, explicit file arguments,
local feed archives and supplied evidence manifests. Relative file arguments use
the actual working directory; omitted environments use the actual inherited
environment. Mutable restore outputs are not treated as immutable inputs.
The launcher independently rehashes the selected map before starting the child
and after actual settlement, rejecting changed inputs. Both original parent
admission and independent CI require aligned snapshot counts, valid relative
paths/content hashes, exact map/array digests and original native output linkage.
Unknown schemas, changed snapshot digests, escaped paths and optimistic closure
claims reject. The Linux transport control preserves original staging-before-kill
ordering and checks actual post-launch mutation and pre-launch rejection.

Snapshots retain `inputClosureComplete=false` and
`scope=selected-declared-inputs`: this is not a complete transitive/imported
compiler or runtime read set. `python3 scripts/conformance_unit_checks.py
--all-tooling`: 572 tests, zero failures/errors/unexpected diagnostic bytes,
twenty explicit native macOS skips, expected incomplete exit 2. Focused inherited/
composition/legacy regressions: 66 tests, zero failures, one Linux-only skip.
Native v3 confirmation remains pending; T046 stays unchecked, 52/86,
implement/running, all full-controller/profile/qualification flags false.
Provider contracts, examples, diagrams, infrastructure and governance are
unaffected by this test-transport continuation.

The first v3 native attempt, exact `c7dcb739c991b305a25842bbf95f538945a97d62`,
[run40590586172](https://github.com/Stonefly-Labs/Hoard/actions/runs/40590586172),
job122493477463, fails historical preparation with `EvidenceSchemaInvalid`.
Original finite control400211 and a focused red regression identify the generic
proof-manifest helper's nonempty-list requirement: some actual commands have no
selected declared file arguments. The repair preserves an explicitly empty
partial map and its canonical digest while retaining every nonempty pre/post
hash check, aligned launch count, native ownership check and false closure flag.
The actual guarded Linux test now also covers an empty-map native launch.
Focused regressions: 67 tests, zero failures, one Linux-only skip.
`python3 scripts/conformance_unit_checks.py --all-tooling`: 573 tests, zero
failures/errors/unexpected diagnostic bytes, twenty native macOS skips, expected
incomplete exit 2. Native repair confirmation remains pending; the failed attempt
is retained as failure. T046 stays unchecked, 52/86, implement/running.
Provider contracts, examples, diagrams, infrastructure and governance remain
unaffected.

Exact `b5d6319d9b018ba017b3c3933573204d59fe6ed9` reaches the mutation
phase in
[run40591427509](https://github.com/Stonefly-Labs/Hoard/actions/runs/40591427509),
job122496379218, then fails `OwnershipInvalid` at original
`conformance_inherited.py:1095`. The original discovery launcher supplies the
installed SDK's VSTest DLL as a data argument to the owned discovery driver.
A focused red control reproduces the selector wrongly treating every DLL
argument as the executable. Actual dotnet/VSTest executable and foreign project
targets still reject; supplementary SDK arguments remain environmental inputs,
not private owned files or evidence of complete SDK-byte closure.
Superseded `ec66f5e` composition run40592633301, containing the same reproduced
selector defect, is explicitly cancelled and never counted as acceptance.
All six `c72ba97` foundations jobs now pass in run40584775863.

The selected-file collector also follows literal Compile/ProjectReference/Import/
HintPath declarations, bounded cyclic project traversal and recursively admitted
Hoard cache files. Linked-source/import/project and nested-package omissions
first fail focused controls, then pass; foreign links reject. It deliberately
does not interpret dynamic MSBuild expressions or imported/glob evaluation.
`PYTHONPATH=tests/tooling python3 -m unittest test_conformance_inherited
test_conformance_composition test_conformance_legacy -q`: passed, 68 tests with
one Linux skip. `python3 scripts/conformance_unit_checks.py --all-tooling`:
574 tests, zero failures/errors/unexpected diagnostic bytes, twenty native macOS
skips, expected incomplete exit 2. Native replay remains pending, both original
failed attempts remain failures, and T046 stays unchecked at 52/86,
implement/running. Provider contracts, examples, diagrams, infrastructure and
governance remain unaffected.

The next T046 selected-input increment reads the actual `HoardSafe` logger
configuration from the original runsettings. It follows the existing owned
Root/AttemptId/ManifestSha256/OwnerSha256 descriptors rather than reconstructing
a replacement authority. The matching original runtime manifest, owner,
run-input document, declared images and SDK archives join the same per-launch
pre/post map; expected content hashes must agree before the child starts.
Duplicate/conflicting descriptors, changed manifest/owner/input/image/archive,
foreign or escaping roots, escaped relative image paths and unknown logger
configuration fields reject. Full runtime schema/result semantics remain with
the existing logger and transport admission, not a second result evaluator.

The new focused control first exposes one omitted descriptor and eight missing
rejections; its repaired ten-subcase control passes. Linked regressions: 68 tests,
zero failures, one Linux-only skip. `python3 scripts/conformance_unit_checks.py
--all-tooling`: 574 tests, zero failures/errors/unexpected diagnostic bytes,
twenty native macOS skips, expected incomplete exit 2. Native confirmation of
this extension remains pending. It is still selected-declared-input capture,
not complete compiler/import/runtime I/O closure; T046 remains unchecked,
52/86, implement/running, all full-controller/profile/qualification flags false.
Provider contracts, examples, diagrams, infrastructure and governance remain
unaffected.

Exact `cf6a9a6f2bb34e70cf2a78d00db1e020660b2cee` confirms the repaired v3
transport in
[run40594189002](https://github.com/Stonefly-Labs/Hoard/actions/runs/40594189002),
job122505782182. The original 45 historical, 230 controller, one reference and
73 mutation launches each retain selected-input snapshots, independently admitted
against their original parent/output records after actual release. CP36/110,
inherited525/58, all twelve original negative/repair pairs with 29 parameters
per side, discovery137/four adapters/ten suites, all 574 tooling tests,
41 formatters and 3,272 unchanged controller inputs pass on Linux.
The original BCL reference replay retains six modules/eighteen inputs.
`inputClosureComplete`, `controllerNativeContainment`, `fullControllerAcceptance`,
`profileComplete` and `qualification` remain false as emitted; native component
acceptance does not establish complete dynamic MSBuild/SDK/runtime input closure
or final profile evaluation. T046 remains unchecked, 52/86, implement/running.
Provider contracts, examples, diagrams, infrastructure and governance are
unaffected by this evidence-only checkpoint.

The composition report-schema boundary now derives case/matrix keys and CP
parameter identities from the independent catalog. Six red controls expose
acceptance of omitted/duplicate/foreign parameters, unknown cases/matrices and
excluded mandatory composition coverage. The repair rejects each while
preserving a failed parameter prefix and an empty interrupted attempt.
These synthetic schema controls do not establish runtime origin, re-evaluate
proof bytes or complete T048/T071. Existing runtime ingestion still independently
rejects false readiness and optimistic retained-owner cleanup.
`PYTHONPATH=tests/tooling python3 -m unittest test_conformance_evidence -q`:
passed, 171 tests. `python3 scripts/conformance_unit_checks.py --all-tooling`:
576 tests, zero failures/errors/unexpected diagnostic bytes, twenty native macOS
skips, expected incomplete exit 2. SDK catalog and diff checks pass.
No task or qualification flag changes; product/provider contracts, examples,
diagrams, infrastructure and governance remain unaffected.

Composition's original runtime assignment uses physical `.observe` rows:
one real parameter can assert both rejection and its repair. Final logical
matrix rows must not rewrite that execution's original matrix or invent a new
execution ID. A shared physical assignment catalog and explicit input-bound
case-derivation packet now support this relationship. Report admission checks
the canonical case, exact parameters, original physical assignments, input/run
identity, snapshot-policy digest, time bounds and registered derivation digest.
Missing/altered derivations and changed original matrix/case reject.
The controls remain synthetic schema/derivation controls, not runtime-good
controls or independent replay of original proof bytes. The diagnostic runner's
physical assignments remain unchanged.
`PYTHONPATH=tests/tooling python3 -m unittest test_conformance_evidence
test_conformance_composition -q`: passed, 181 tests.
`python3 scripts/conformance_unit_checks.py --all-tooling`: 577 tests,
zero failures/errors/unexpected diagnostic bytes, twenty native macOS skips,
expected incomplete exit 2. No task/qualification flags change; 52/86,
implement/running. Provider contracts, examples, diagrams, infrastructure and
governance remain unaffected.

T046 is now checked after criterion-level reconciliation with the specification,
not by changing a runtime qualification flag. Its required integration is
verified at exact native `cf6a9a6`: all 525 inherited parameters/58 fresh scopes,
complete frozen source-owned inventories, exact manifests/witnesses, source/
package/runtime agreement, independent original parent/output admission and
actual release. `inspect_inherited_runtime_attempts` rejects omitted scopes,
parameters, reused attempts/executions and mixed source, owner or image inputs;
the original discovery/controller negatives and repairs also execute.
Earlier continuation notes treated universal compiler/SDK/runtime read-I/O
closure as an extra T046 gate. T046/FR-018 do not require syscall tracing.
The approved specification remains the acceptance boundary; no new tracing
requirement or relaxation of attribution, completeness or sanitation is added.
Selected per-command snapshots remain partial, and all full-controller/profile/
qualification flags remain false. T047 and final independent proof evaluation
remain open. Current progress: 53/86, implement/running.

The composition component now writes `proofs/composition-runtime-report.json`
after original runtime admission and fresh completion measurements. Every
canonical CP case references unchanged original witnesses plus its explicit
derivation packet. All nine quality obligations remain `Incomplete`; report
state is `Incomplete`, qualification is false and resources describe the point
of capture, not final cleanup. Source identity, packages, locks, runtime images,
configuration and an actual completion environment probe are recomputed;
only the existing free-space measurement exception applies. Original proof bytes,
derived packets and the immutable completion document are hash-registered.
This is diagnostic publication, not final independent proof/origin evaluation.
A modeled full-catalog control confirms complete logical rows and rejects changed
original proof bytes; it is not counted as runtime evidence.
`PYTHONPATH=tests/tooling python3 -m unittest test_conformance_evidence
test_conformance_composition -q`: passed, 182 tests.
`python3 scripts/conformance_unit_checks.py --all-tooling`: 578 tests,
zero failures/errors/unexpected diagnostic bytes, twenty native macOS skips,
expected incomplete exit 2. Linux confirmation remains pending; T047 stays
unchecked, current progress 53/86. Product/provider contracts, examples, diagrams,
infrastructure and governance are unaffected.

The publication path is now verified at exact
`456f818651c97479076304614f93f63b70307dd5`,
[run40601395925](https://github.com/Stonefly-Labs/Hoard/actions/runs/40601395925),
job122533378626. The actual report has 41 passed logical CP rows and nine
incomplete quality rows; SHA-256
`34374d341b53f5db8f116b6139bf4119c771d6548cc367f0a401b416ba18c5fd`.
CP36/110, inherited525/58, all original negative/repair pairs, 578 tooling
tests, 41 formatting commands, unchanged 3,272 controller inputs and actual
process release also pass. This does not establish final qualification.

The follow-on independent diagnostic reader replays the original manifest,
owner, settings, logger proofs/completion and native parent receipt. It rebuilds
the exact logical result/proof set instead of trusting reported pass counts,
and verifies measured completion inputs. Selected original runtime images,
package archives, locks and command inputs are captured as immutable
hash-addressed evidence before cleanup; their original relative names/hashes
remain linked to the native input map. Stores, feed and cache are still removed.
The copies prove those selected bytes, not universal SDK/compiler read tracing.
Original protocol/parent records and all derivation packets are registered.
The Linux workflow replays after release and applies fourteen mutations to the
actual generated report, rejecting optimistic state/qualification, omitted
results/witnesses/transport/snapshot, changed derivations/matrices/proofs and
extra proof registrations without rewriting original runtime evidence.

`PYTHONPATH=tests/tooling python3 -m unittest test_conformance_evidence
test_conformance_composition -q`: passed, 184 tests.
`python3 scripts/conformance_unit_checks.py --all-tooling`: 580 tests,
zero failures/errors/unexpected diagnostic bytes, twenty native macOS skips,
expected incomplete exit 2. Catalog and diff checks pass. Linux replay
confirmation remains pending; no full-profile/qualification flag changes and
T047/T071 remain open. Provider contracts, examples, diagrams, infrastructure
and governance remain unaffected.

Exact `08fec30` run40604553886/job122540687673 fails with `ProofMismatch`
after completion measurement, before the inherited continuation; it is retained
as failed evidence. A full modeled report-link replay reproduces the defect:
raw persisted JSON lists were compared with already-admitted immutable tuples.
Both sides now pass through strict `RunInputs` admission before comparison;
original bytes still have to match the native command/proof hashes. The model
also executes all fourteen rejecting mutations after deleting stores/feed.
Only transport ingestion is mocked: this is link-level regression coverage,
not actual native-origin acceptance.

The selected-input snapshot uses `configurationPolicy=synthetic-nuget-v1`.
It verifies original configuration bytes before cleanup but does not retain
their absolute scratch path. Replay reconstructs the exact generated local/
public NuGet configuration in memory and checks its original digest.
Matching hashes for an unsupported configuration still reject.
Two focused replay/retention controls pass. Full safe tooling observes 581
tests, zero failures/errors/unexpected diagnostic bytes, twenty native macOS
skips and expected incomplete exit 2; catalog/diff checks pass. Fresh Linux
confirmation remains pending, T047/T071 remain open, 53/86 implement/running.

Native run40463591718 at exact `cd9102977d47ecc486332cf44044bcea6c98d20d`,
job122053635177, passes historical/four-family batch preparation, actual BCL
consumer presentation admission, CP36/110, inherited525/58, all 2,022 unchanged
bound inputs, process release and retained historical-seal verification.
Configuration retains nine journeys/thirteen graphs/five publication barriers;
discovery retains nine journeys/seven observations/eighteen graphs and the
real reference consumer; lifecycle retains seven journeys/ten graphs.
The expected public exit remains 2, not qualification or full-controller
acceptance. Formatting/tooling, mutation and remaining provenance obligations
remain open. The next input-closure regression exposes omitted owned ancestor
MSBuild props/targets, central package/SDK files and per-project locks. Binding
those files makes changes observable; symlinked context rejects without touching
an outside sentinel. All twenty inherited and seven parent tests pass.

T041 now consumes the separately packed `Hoard.Fixtures.Conformance.Host`
instead of compile-linking Host source in package mode. Both existing CP-01/02
rows first fail the added assembly-owner assertion, then pass with the same
consumer image after the package-reference repair. A fresh seventeen-archive
build and independent fresh-cache default locked restore/build pass. The
intentional package lock expansion adds Host, SDK and four binding dependencies,
removing none and changing no resolved version. Bounded architecture review
finds no confirmed issue; this is not the final T081 review.
Source-mode composition/version regressions pass all 148 selected tests after
restoring a missing test dependency. The complete native diagnostic run40405035306
at `ef82218` now passes all five existing jobs, including full SDK diagnostics;
these remain component jobs, not qualifying five-profile CI.
That preceding component run does not qualify a composition profile: the strict safe
logger rejects the existing unstructured observation output as
`UnknownDiagnostic`, leaving safe transport for T046. That preceding T041
checkpoint recorded 43/86 tasks checked.

At exact `ef82218`, run40405035306's isolated metadata/artifact jobs both pass
through the public CLI, including complete original/native source admission,
all real recovery/transfer controls, package-only common consumers and actual
store/feed/cache cleanup. Metadata observes 93 Passed/9 NotApplicable over 102
rows; artifacts observes 99 Passed/4 NotApplicable over 103. Together these are
179 inherited applicable passes, thirteen authorized exclusions and thirteen
category quality passes. Reports remain `Incomplete`, qualification false;
full independent acceptance/portable retention/evaluation remains unfinished.
T026/T032/T035/T036 record execution/wiring/consumer completion, not certification.

T052 adds actual declared/compiled SDK paths for all nine production owners and
permitted test owners, complete/omitted/duplicate/foreign/uninspectable scan
controls, plus actual direct/helper Identity-to-Core routes alongside the allowed
Hosting route in both traversal orders. Four malformed entries first fail with
the wrong exception; the scanner now rejects non-object entries through its
existing `InspectionException`. Standalone graph checks pass 43 cases, then
`bash scripts/validate-foundation.sh --phase architecture` passes with prepared
inputs, including the four new actual Identity paths and unchanged ARCH-001..008.
An initial direct inherited-test invocation lacked `HOARD_FOUNDATION_EVIDENCE`;
it is a setup failure, not a rule regression or qualifying pass. Full tooling
still passes 481 tests with nineteen explicit native skips; scoped formatting,
frozen inventories/catalogs and whitespace checks pass. The stage remains
`implement / running`, now 42/86 tasks checked.

Public metadata/artifact commands now dispatch their existing complete native
category batches rather than reject before execution. Exact full catalog keys
are rechecked; focused/custom-binding, other-profile and offline modes still
reject without allocating or substituting a built-in agreement. Native failures
retain their safe code. A completed batch remains non-qualifying and returns
exit 2 (`EvidenceIncomplete`) until independent evaluation is implemented.
The native backend currently requires Linux x86_64/aarch64; unsupported hosts
reject before allocating. Existing isolated Linux diagnostic jobs now use the
public shell entry and require a complete all-applicable-pass report, original
proof bytes, actual completion inputs and released resources after that expected
exit. A missing report or unrelated incomplete failure cannot make the job pass.
These are component diagnostics, not the future five-profile qualification CI.

Three routing regressions first expose nine intended failures, then all nine CLI
tests pass. Full tooling runs 481 tests successfully with nineteen explicit
native skips; frozen inventory, SDK catalog, shell syntax and whitespace checks
pass. Current-source native CLI execution is pending. No additional task/checklist
or stage marker is completed by routing tests or historical receipts.

T062/T063 now supply a separately packed Memory-forwarding contributor adapter
and package-only good/faulty/corrected controls. Two actual safe-logger witnesses
pass from an isolated source/feed/cache. The faulty state triggers the intended
shared assertion; good/corrected states use the same compiled consumer and six
unchanged platform/provider/adapter/assertion images. All fifteen consumer runtime
package images match their actual local archives. Fresh-cache default locked
restore/build also passes, and its generated consumer lock is retained in Git.
Focused C# whitespace formatting passes; tooling remains 478 passes with
nineteen explicit native skips. Native SDK diagnostics now explicitly select both
contributor controls and pack the contributor before its consumer. Native
admission is pending; the isolated component check does not complete T064..T067
or the public CLI/guide journey. The stage remains `implement / running` with
37/86 tasks checked.

Linux run40395540197 exposed an input-set mismatch: Python's inventory producer
included `conformance_legacy.py`, but the independent C# decoder retained its old
required source list. Focused regressions reproduce rejection of a complete graph
and acceptance of a fully resealed graph omitting that helper. The decoder and
its model fixture now independently require it. Command
`dotnet test tests/contracts/Hoard.Conformance.Tests/Hoard.Conformance.Tests.csproj --no-restore --filter FullyQualifiedName~MetadataInventorySourceTests --verbosity quiet -p:UseSharedCompilation=false -nodeReuse:false`
changes from two intended failures/one pass to three passes. Focused whitespace
formatting, frozen inventory/catalog checks and `git diff --check` pass.
This repairs the demonstrated inventory-controller defect, not the separate
earlier Object native-I/O deadline failure or complete profile qualification.

The latest scoped architecture-review repairs extend bounded group settlement
to interactive legacy children, replace blocking trailing-output reads with
concurrent bounded drains, and bind metadata safe projections to independently
selected provider/configuration. Build commands disable reusable compiler/MSBuild
servers so owned command groups cannot leave such descendants behind. macOS
runtime OS descriptions admit only a closed numeric grammar, not diagnostic text.

`python3 -m unittest discover -s tests/tooling -q` passes 478 tests with nineteen
explicit native skips. Frozen inventory and SDK catalog checks pass.
Fresh `bash scripts/validate-metadata.sh --phase recovery --evidence <fresh-private-path>`
passes with logical/recovery proof and `qualification: false`.
With the documented original `HOARD_ARTIFACT_RETAINED_BASELINE`,
`bash scripts/validate-artifacts.sh --phase recovery --evidence <fresh-private-path>`
passes 33 recovery tests and all six actual Local SIGKILL/reopen barriers.
The corresponding `--phase transfers` attempt fails before starting a transfer:
only approximately 14 GiB is free, below its 16 GiB minimum and the F-07
24 GiB private-local-scratch preflight. Do not reduce those gates or delete
retained evidence/user data to force a pass. These results do not complete
T026/T032 or standalone profile admission.

Explicit maintainer authorization cleared the implementation entry gate without
self-approving the 40 reviewer-owned checklist markers. The driver remains
`implement / running`; do not rerun `begin`, call `finish`, start convergence,
or treat the partial SDK/catalog/manifests as qualification.

The checked-in foundations include strict evidence admission, a frozen
source-level inventory, typed SDK seams, focused unit tests and historical
baseline preparation. Source-derived test identities are not observed runtime
witnesses. A local historical preparation completed before candidate package
builds, but its retained outputs are private, non-qualifying and not committed.
Baseline reuse now verifies all six source/recipe/lock/binary/package inventories
and the original seal. Package-only SDK/Memory checks passed a fresh-cache
locked replay; full profile replay remains unfinished.

The bounded `hoard-architecture-review` of these foundations identified a real
scope decision: Memory's current public controls cannot inject and observe
targeted record/receipt corruption while preserving unrelated state. T003
requires unchanged providers; T021/T023 require unchanged shared assertions and
all mandatory logical controls. A separate binding cannot bridge that gap
without prohibited private access or simulated outcomes. The recommended
resolution was a narrow test-only seam inside the Memory fixture assembly.
The maintainer subsequently directed autonomous resolution and continued
implementation. The fixture now uses bounded private stored encodings and
targeted capture/replacement controls, with real public-path validation;
private state types stay private and no provider depends on the SDK.
Nine package-only checks cover SDK admission and actual corruption/restoration.
No mandatory assertion or applicability rule was weakened.

The same early review found incomplete descendant containment, an unprotected
post-spawn registration window, cleanup/termination budget and state-ordering
defects, and missing binding/matrix checks during witness ingestion. Initial
repairs and targeted regressions are implemented. Native child execution now
requires inherited Linux kernel process-group confinement and stable
PID-handle group signalling (probed Linux 6.9+ support). A two-way startup
handshake prevents target execution before handle, identity and ledger admission.
Group signals use the kernel handle; Linux process fingerprints use actual
kernel start ticks, not second-resolution `ps` dates. Unsupported hosts return
`PrerequisiteMissing` rather than claiming safe generic containment. The Ubuntu
foundation workflow runs sanitized native regressions without skips and does
not claim qualification. Local skipped native checks are incomplete evidence.
Run [39901637391](https://github.com/Stonefly-Labs/Hoard/actions/runs/39901637391)
passed 23 tests without skips and measured 92,112,142,336 free scratch bytes.
Run [39904414231](https://github.com/Stonefly-Labs/Hoard/actions/runs/39904414231)
then observed exactly two intended failures for missing process/group handles.
The repaired handshake and stable-handle implementation passed all 26 native
checks without skips in
[39906330789](https://github.com/Stonefly-Labs/Hoard/actions/runs/39906330789).
A new challenge in
[39906992231](https://github.com/Stonefly-Labs/Hoard/actions/runs/39906992231)
then failed only the diagnostic-parent directory replacement check. The
correction uses original directory device/inode identities and descriptor-relative
ledger writes, diagnostic retention and cleanup; a same-name replacement cannot
recreate ownership. Cleanup traversal also has finite depth/entry bounds.
The correction passed 28 native checks without skips in
[39908082714](https://github.com/Stonefly-Labs/Hoard/actions/runs/39908082714).
Its private ledger format now
requires directory identities: do not resume earlier retained roots as though
they carried the new ownership proof.
Separately, all 72 unchanged inherited metadata tests passed against
candidate Memory packages without skips. Neither focused result is complete
F-07 acceptance. Full challenge coverage remains required before acceptance.
This is not the final architecture review or T081 completion.

The next foundation checkpoint adds a real bounded VSTest logger, private
input/owner manifests, safe per-execution proofs and completion records, and
an SDK resource allocator with native directory identity pins. Settlement
timeouts/faults retain ownership; the SDK never deletes stores or reports
`Released` in-process. Actual controller cleanup remains authoritative.
The executor now accepts only finite VSTest scaffolding plus closed safe events,
not console summaries or arbitrary test output. Python evidence admission binds
packages, bindings, baselines, runtime assets, execution UUIDs, every retry's
proofs, dimensions and monotonic attempt intervals. The logger is not yet wired
to complete controller ingestion or actual loaded-provider proofs.

Portable tooling discovered 141 tests: 132 passed and nine Linux-native checks
were skipped on macOS. The current SDK source tests passed 39 cases; independently
prepared/fresh-cache locked current SDK/logger packages passed 41 cases.
Package-only smoke locks were independently replayed and the project built.
The focused composition/version suite passed 142 cases. A broad direct
composition invocation passed 646 cases and failed five preparation-dependent
checks because foundation/configuration/discovery evidence was not supplied;
this is not a full predecessor acceptance result.
A bounded SDK/logger architecture review found no confirmed architectural
violations, but identified Linux allocator execution and loaded-provider proof
integration as material gaps. This is not final T081 review.

**Resolved timing clarification:** the earlier CP-11/FR-007 wording required
route conflicts to fail before provider construction. Existing Hosting
receives real routes from constructed modules' `MapEndpoints` callbacks and
rejects ambiguity before route publication/readiness, not before construction.
Responsibility IDs are owner-scoped identifiers, not route templates; malformed
or duplicate IDs cannot honestly stand in for CP-11. Those declaration tests
are therefore labelled `endpoint-declaration`, not CP-11.
The maintainer subsequently directed autonomous continuation and resolution.
The implementation preserves public APIs and clarifies actual route-conflict
rejection at mapping, before publication, initialization, readiness or admission;
declaration errors still reject before construction. The actual ambiguity/repair
test observes construction and mapping, zero published routes and zero
initialization/connections/workers/requests for rejection. No product contract
redesign, duplicate-ID substitute or self-approval of CHK014 is used.
The spec/matrix/QC-14/task wording records this explicit timing correction.
Continue the same running implementation stage through all remaining tasks.

The next foundation increment completes T001/T006: the frozen source inventory
now includes the original registration/lifecycle baseline as well as the other
recorded historical revisions, and every evidence entity has required-field and
unknown-extension checks. These are pre-extraction expectations, not copied
runtime passes. The controller now ingests actual logger JSONL/proof/completion
bytes, preserving failed/incomplete attempts while checking exact manifest,
package, assembly, parameter, dimension and monotonic relationships. Proof trees
are descriptor-walked with byte/file/depth/time bounds and reject symlinked roots
and special files rather than following them.

`python3 scripts/conformance_sdk_checks.py --evidence <fresh-private-absolute-path>`
is a **non-qualifying Linux diagnostic**, not the planned conformance CLI.
It seals/verifies all six historical baselines before candidate compilation,
then exercises the SDK allocator and safe logger with fixed source-owned test
identities. Runtime command inputs containing private paths stay in synthetic
stores, not diagnostic/proof directories. Current local archive hashes may be
prepared in the isolated smoke lock with an explicit preparation record;
fresh locked replay preserves its dependency graph and leaves tracked locks
unchanged. Historical platform-built archives now have the separate explicit
preparation described below. Native SDK diagnostics now pass, not qualification. Actual loaded-provider evidence,
all category assertions, full profile evaluation and final review remain required.

The first combined Linux attempt correctly rejected mocked fixture progress
as unknown output and the workflow's lexical `repository/../evidence` path
as repository-relative ownership. Fixture-local capture and an absolute sibling
path repair those integration issues; neither diagnostic nor ownership
admission is weakened.

The source SDK now has a concrete `ConformanceEvidenceBuffer`: it retains at
most 10,000 typed fault observations in order, copies immutable snapshots, and
rejects cancellation/overflow without discarding prior evidence. All 42 source
SDK tests pass locally. Native SDK execution is still incomplete: historical
locked restoration reported compiler/NuGet code 1403 before any candidate
compilation. The locks remain unchanged; bounded archive/assembly fingerprints
are being used to diagnose the platform difference.

Those fingerprints show different Linux assembly bytes, not just ZIP envelopes.
Build commands now disable .NET runtime roll-forward so the pinned SDK/compiler
uses its requested runtime rather than a newer runner patch. This is scoped to
restore/build/pack, not test-runtime selection; missing requested runtime fails
explicitly. Historical locks are not rebound. Native confirmation is pending.

The next native run produced the same differing assembly hashes, so runtime
roll-forward alone does not explain the cross-platform baseline mismatch.
Historical source and locks remain unmodified; the SDK/logger cases have not
executed on Linux yet.

T007 is complete after typed corruption requests were shown to accept missing
subjects/unknown enum values, then repaired at admission. The full source SDK
now passes 42 tests. These contracts and strict evidence entities are not the
remaining category adapters, runtime-provider attribution or final evaluator.

Historical cross-platform preparation is now explicit:
`conformance_baselines.py --prepare-local-archives` creates alternate private
locks, without editing pinned source locks or changing package versions,
dependencies or third-party hashes. The SDK diagnostic opts into this
non-qualifying preparation before candidate compilation. A fresh locked restore
consumes each alternate lock. The private preparation seal uses schema `2`
for this mode; existing strict schema-`1` seals still verify unchanged. Public
F-07 evidence remains schema `1` / catalog `f07-v1`.

Each alternate lock has a recipe-owned record linking its original lock,
prepared bytes, actual local archives and graph-preserving derivation. Seal
verification recomputes that derivation and rejects detached/rehashed graph
changes, absent archives or a downgrade to the old preparation format. Native
confirmation of this increment is pending; it is not provider qualification.

Native confirmation is now available at
[run 39913608773](https://github.com/Stonefly-Labs/Hoard/actions/runs/39913608773),
head checkpoint `53c3857`: all six baselines were prepared/sealed before
candidate compilation and reverified after all SDK/logger cases. The baseline
seal is `41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`;
admitted input digest is
`a982fc72e53d6a62df4aba671761cf4d2b061ccc9d1f65da60f1a5d6711e750d`.
Six allocator facts and the two parameter cases passed; actual assertion,
unknown exception/output, skip and passing-with-stdout cases retained their
expected distinct safe outcomes. The separate Python job passed all 61 checks
with zero failures/errors/skips and 92,111,626,240 free scratch bytes.
Neither the current workflow head nor all 42 source SDK tests are inferred
to have run from this older native checkpoint. Full provider/profile
qualification, actual loaded-provider proof and final resource projection remain
unfinished.

The catalog now maps composition, version and inherited classification rows to
actual methods and exact parameters. Default composition discovery omits seven
mandatory package-only cases; they are not exclusions. The conditional project
now has its own tracked `PackageAcceptance/packages.lock.json`. Deliberate
preparation used the already sealed F-06 artifact feed, followed by a second
empty-cache locked restore and package-mode Release build. No predecessor lock
was changed. Actual bounded discovery matched all 144 distinct expected runtime
identities, including those seven cases, with none missing:

```bash
dotnet test tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj \
  -p:ConformancePackageAcceptance=true -c Release --no-build --no-restore \
  --list-tests --verbosity quiet
python3 scripts/conformance_case_catalog.py --check-sdk
```

Both commands passed. Discovery is not execution/qualification, and one physical
test appearing in multiple matrix dimensions cannot supply borrowed witnesses.
Three intended source logger failures and three Python admission failures
identified the missing finite version-range punctuation. Both layers now preserve
bounded bracket/parenthesis/comma parameters and continue rejecting paths,
free text, embedded quotes and control characters. All 45 current source SDK
tests pass; earlier package-acceptance results remain historical. The Linux
diagnostic now selects these three exact range cases as an additional scenario.
Run [39916071298](https://github.com/Stonefly-Labs/Hoard/actions/runs/39916071298)
at `4678eb8` passed all seven scenarios/15 observations, including those three
range cases; it reproduced the six-baseline seal above and input digest
`a807dba086c63476d9b440a0621f0cf7cded31b194a0dae1b7312a8422127a10`.
This does not imply all 45 source tests ran natively. At that checkpoint T008
remained incomplete until the remaining control mappings were wired; actual loaded-provider attribution and complete
profile evaluation are also unfinished.

A new native concurrency regression holds two independently owned runs at
explicit file barriers, writes the same cache key with distinct values, lets
one watchdog contain its child, and verifies the other remains alive until its
own release. [Run 39914002055](https://github.com/Stonefly-Labs/Hoard/actions/runs/39914002055)
at `6f9e0b7` passed all 62 Python checks with zero failures/errors/skips,
including this native challenge; T009 is complete. The SDK/logger job also
passed again and independently reproduced the same six-baseline seal
`41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`.
It measured 92,111,634,432 free scratch bytes. These observations do not complete
the remaining foundation tasks or qualify a profile.

Cleanup now preserves the evidence root, `proofs`, safe `diagnostics`, runtime
records and ownership ledger; only settled `stores`, `feed` and `cache` are
removed. Retained input archives/binaries needed for verification must therefore
be stored outside those synthetic directories before full cleanup. The current
SDK diagnostic still deliberately retains its baseline/input bytes and remains
`Settling`, not authoritatively `Released`.

The private ownership ledger is now schema `2`, separate from public schema `1`
and baseline seal schema `2`. Old ownership ledgers are not silently adopted.
It retains up to 128 explicit cleanup observations, rejects overflow rather
than truncating history, and publishes state only after atomic ledger
replacement. Live children or failed cleanup/publication remain retained.
Explicit retry after observed exit preserves the previous failure and safe
evidence. Immutable path-free resource projections include actual live PID/start
identities; PID zero/all-zero digest explicitly mean no live child. A preserved
evidence directory is not an active synthetic store. Four focused regressions
cover evidence preservation, live-work retry and failed release publication;
portable conformance checks pass 70 tests with ten native skips. A reproduced
atomic-rename failure also required removing only the writer's identity-checked
partial marker; pre-existing foreign markers remain untouched. All 175 tooling
tests pass with ten native skips. Native foundation job `120293251935` in
[run 39917215214](https://github.com/Stonefly-Labs/Hoard/actions/runs/39917215214)
at `bc27614` passed all 70 checks with zero failures/errors/skips and
92,111,507,456 free scratch bytes; its SDK/logger job also passed. T010 is now
complete, not the full profile/controller lifecycle.

The next diagnostic increment rejects events above 1 KiB before JSON expansion,
keeps raw line buffering within a two-read window (64 KiB/read), and reserves
safe retention space for explicit failure records. Unknown text, output floods,
watchdog expiry and failed containment keep safe prefixes plus closed codes;
raw output is never saved. A closed-output-but-live child remains subject to
the watchdog. The catalog also copies witness/control collections and matches
SDK admission bounds without changing generated bytes. Intended regressions
demonstrated both defects before repair; all 177 tooling checks pass with ten
native skips. Native foundation job `120296941427` in
[run 39918257385](https://github.com/Stonefly-Labs/Hoard/actions/runs/39918257385)
at `ac9be42` then passed all 72 checks with zero failures/errors/skips and
92,111,450,112 free scratch bytes. Its SDK/logger diagnostic also succeeded.
T011 is complete; no provider/profile qualification follows from that result.

The next supervisor increment includes admission/state-publication work in
absolute command deadlines, reserves 40 seconds for termination and cleanup at
profile end, and supplies bounded five-second control/15-second barrier scopes.
An intended regression observed 10.2 seconds of renewed admission controls
against a 0.3-second budget; deadline propagation repairs it. Caller deadlines
cannot widen a scope/profile ceiling. SDK host probes now use at most five
seconds per control. Cleanup leaves time for containment within its outer limit.

Native artifact/baseline admission observes >=24 GiB free space and rejects
remote/unknown filesystems before creating the root. The current conservative
allowlist is GNU `stat` types `ext2/ext3`, `xfs`, `btrfs`, `zfs`, `f2fs` and
`bcachefs`; unsupported mounts are prerequisite failures, not smaller transfer
runs. `proofs/preflight.json` retains path-free capacity/filesystem/duration
facts with `qualification: false`; portable macOS ownership checks explicitly
leave filesystem identity unobserved and cannot start providers. Execution
currently serializes owned commands, stricter than the four-child/one-transfer
upper bounds. Cleanup-budget expiry records retained ownership and leaves
synthetic resources intact; an explicit later retry preserves that failed
observation. All 184 tooling checks pass with ten native skips on macOS.
Native foundation job `120303380550` in
[run 39920220726](https://github.com/Stonefly-Labs/Hoard/actions/runs/39920220726)
at `1675f93` passed all 79 checks with zero failures/errors/skips and
92,111,450,112 free scratch bytes. Its SDK/logger diagnostic passed all seven
scenarios/15 observations, reproduced the same six-baseline seal and bound
input digest `46a16ed43d07b26d2c11cbf5beb19eb0fd157d47c4e01ed9548bd4ad0f198c4d`.

A held-admission regression then demonstrated that another caller could enter
the same run's ownership work. A nonblocking per-run writer gate now rejects
overlapping commands, cleanup and transitions before ledger access, while
allowing cleanup to invoke its own controlled child. Different runs remain
independent. An actual insufficient-capacity admission now produces safe
`Incomplete`/`InsufficientCapacity` and exit `2` without creating a workspace or
altering an outside sentinel. Evidence violations remain `Failed`/exit `1`,
not prerequisite errors. All 187 tooling checks pass with ten native skips.
Native foundation job `120307028359` in
[run 39921337767](https://github.com/Stonefly-Labs/Hoard/actions/runs/39921337767)
at `b9d335a` passed all 82 checks with zero failures/errors/skips and
92,111,400,960 free scratch bytes. Its SDK/logger job passed seven scenarios/15
observations, reverified all six baselines and bound input digest
`ec4c80a84b38a0815d337cac5b121b6e530ff7d34fff718e9a888f69410a8d60`.

The catalog now also maps 41 actual architecture/inspection identities and ten
SDK catalog admission identities. All match real discovery; the combined
non-category mapping contains 195 distinct runtime identities. This is not
architecture/profile qualification. The 192 inherited keys and 13 exclusions
are unchanged. Every QC-01..48 now names individual required subproofs rather
than a single aggregate label: 299 assignments across profile expansions, not
observed passes. Unknown/missing QC maps and overflowing expansions reject.
The regenerated SDK catalog agrees with the independent Python expansion.

Strict SDK catalog tests first reproduced malformed/unknown profile/field,
duplicate-field, invalid-string and incomplete-profile defects. Admission now
rejects those and oversized input/collections/results with closed diagnostics,
never a shortened catalog. All 55 source SDK tests pass; the ten new catalog
identities are selected as an eighth native diagnostic scenario, not full
SDK/package acceptance.

A subsequent allocation challenge reproduced a parent replaced by a symlink
during preflight redirecting workspace creation into an outside sentinel.
Parent/root descriptors now pin capacity/filesystem probes and creation of the
workspace and its synthetic child directories; no resolved replacement path
can redefine ownership. Lexical traversal and substitution during preflight or
immediately after root creation reject, preserving the outside directory and
pre-existing outside root unchanged. All 190 tooling checks pass with ten native
skips. Native foundation job `120317044366` in
[run 39924374116](https://github.com/Stonefly-Labs/Hoard/actions/runs/39924374116)
at `79663dd` passed all 85 checks with zero failures/errors/skips and
92,111,257,600 free scratch bytes. Its SDK/logger job `120317044724` passed
eight scenarios/25 observations, including all ten catalog cases, and
independently reverified all six baselines with the unchanged native seal.
Input digest:
`5d7fb9b9ed2288da5c10c4773da834140172c323822ba31b79e13c6b71c803ff`.
T008/T012 are complete within their catalog/supervisor foundation scope.
This does not imply all 55 source SDK tests ran natively or that the named QC
controls executed. Complete immutable input snapshots, actual loaded-provider
attribution and full profile orchestration remain separate T013/T014 and later
obligations.

T013 now has descriptor-relative source hashing and copying with bounded reads,
aggregate bytes, file count, depth and monotonic time. Root/ancestor aliases,
replacement during creation and unlisted special files reject; post-copy
verification checks exact source equality while excluding generated
`bin`/`obj`/`__pycache__` outputs. Timeout/overflow keep their incomplete codes,
not an invented input-mutation diagnosis. Snapshots include example projects
and build/ignore policy alongside runtime sources, tests, scripts and workflows.
Copied source files are read-only before candidate compilation.

Real Git observations produce immutable `sourceRevision`/`sourceState`.
Ambient Git-directory/index/worktree overrides and global configuration cannot
redirect these observations. Assumed-unchanged/skip-worktree index entries
cannot certify clean CI input. CI requires a clean checkout at exactly
`GITHUB_SHA`, including the actual PR merge-ref checkout rather than silently
substituting its branch-head label; local dirty bytes are explicitly labelled.
The SDK diagnostic now uses this shared snapshot/identity path and verifies it
again after execution, including added files and source-revision changes.

Smoke archive preparation reuses the sealed graph-preserving alternate-lock
helper; the original copied source lock remains read-only and unchanged.
Independent restore/build receives the explicit alternate
`NuGetLockFilePath`, and its derivation/bytes are verified again afterwards.
Immutable source copies are retained input material, not sanitized diagnostic
uploads. A focused actual-checkout probe copied and verified all 703 scoped
files with read-only modes and settled its synthetic resources in 395 ms;
this is diagnostic evidence only. Native run
[39927534630](https://github.com/Stonefly-Labs/Hoard/actions/runs/39927534630)
at `4e17986` then passed all 91 foundation checks without skips and eight SDK
scenarios/25 observations, preserving all six verified historical baselines.

The following input-sealing increment reads package metadata, SHA-256/SHA-512 and
runtime assembly bytes from one bounded archive capture, not separate path
reads. It checks the actual generated source mapping before admitting its
path-free synthetic policy. Bounded lock/runtime inventories and the complete
SDK diagnostic input manifest are recomputed after execution, including fresh
safe environment observations. Free-space variation does not masquerade as
mutable machine identity: the input manifest retains its admission measurement.
Native run
[39929542533](https://github.com/Stonefly-Labs/Hoard/actions/runs/39929542533)
at `44881ff` verified 99 foundation checks without skips, eight SDK scenarios/
25 observations and all six historical seals.

The next increment centralizes capture in `capture_profile_inputs` for all five
admitted profile IDs; the SDK diagnostic now delegates to that shared path.
Selected package, lock, runtime and typed binding-declaration files are read
through pinned roots. Binding snapshots are immutable, bounded and admitted
against actual selected package bytes; capability changes alter their hashes.
The safe configuration policy comes from verified synthetic source mapping,
not arbitrary configuration dictionaries. Environment values must already be
typed observations from the relevant producer; this API is not runtime attestation.
All 207 tooling checks pass with ten native skips, and all 57 source SDK tests
pass. Native confirmation of this shared capture/ninth declaration scenario
is recorded below. Loaded-provider attribution continues to belong to T014; no
qualification or new CLI is claimed. Production reference edges and architecture
diagrams are unaffected by this test-only input capture.
An additional intended regression changed generated `runtimeconfig.json` while
the DLL stayed unchanged; the old inventory missed it. The SDK now inventories
dependency/runtime configuration files alongside assemblies, so these mutations
also reject. Their file hashes are runtime-artifact identity, not configuration
policy values or proof of which runtime loaded.
Native run
[39932469750](https://github.com/Stonefly-Labs/Hoard/actions/runs/39932469750)
at `525bdf0` verified the shared capture and runtime-configuration repair:
102 foundation checks without failures/errors/skips and nine SDK scenarios/
27 observations, with all six historical baselines independently reverified.
T013 is complete as a shared foundation API; actual loaded-provider/session/
runtime provenance remains T014 work. These 27 observations do not constitute
a full 57-test source SDK or package-only run.

T014's enum-parameter regression first failed in both the C# logger and Python
ingestion. Both now accept bounded bare ASCII identifiers (including existing
boolean/null tokens), without accepting spaces, paths, overlong tokens or an
unselected runtime identity. The three token alternatives have distinct initial
characters; boolean/null alternatives are not duplicated inside the identifier
alternative. All 62 source SDK tests and 103 conformance tooling checks pass
(ten native skips locally). Native diagnostics now select ten scenarios/
29 observations, including both actual enum theory rows; verification of this
increment passed in run
[39933805476](https://github.com/Stonefly-Labs/Hoard/actions/runs/39933805476)
at `a1fe180`: 103 native checks without failures/errors/skips, 92,111,106,048
free scratch bytes, ten scenarios/29 observations and all six baselines.
Input digest `8b291f375d50901e255a9d95dbb44e37ed117ab520c04c19e208ebc270388992`.
This repair does not complete loaded-provider provenance or T014.

`ConformanceLoadedAssembly.Capture` now inspects an actual typed instance,
never its rendering or declared package label. Within a five-second scope it
captures at most 64 MiB in reads of at most 64 KiB, hashes those bytes, and checks
their PE assembly name/version and MVID against the loaded module. Its closed
projection contains only name/version, MVID, assembly hash and hashed actual
type name, not paths or object values. No directory discovery or assembly
loading is performed. Python `ingest_loaded_assembly` checks the independently
selected runtime artifact and, when selected, actual embedded package bytes;
an unpackaged test artifact cannot borrow a provider package label. An explicit
`package_id=None` makes only an unpackaged runtime correspondence claim.
The two source facts first failed to compile without the capture API; two Python
regressions also failed before ingestion existed. All 64 source SDK tests and
105 conformance tooling checks now pass (ten native skips locally); the new
eleventh native scenario/31 total observations passed run
[39934964377](https://github.com/Stonefly-Labs/Hoard/actions/runs/39934964377)
at `0a0b1d1`: 105 native foundation checks without failures/errors/skips,
92,111,003,648 free scratch bytes, eleven scenarios/31 observations and all six
baselines. Input digest
`6d21a3127a27650ac8c73e37eb6aaa0552d4c55496581a73cb2d0f600229866b`. These are
component-capture APIs, not session/factory invocation linkage, an actual .NET/
SQLite environment producer, or completed T014/provider qualification.

The next T014 increment adds actual VSTest discovery-event capture, separate
from execution witnesses. Each private attempt manifest/completion has required
`purpose` (`discovery`/`execution`); a discovery UUID cannot be reused as an
execution attempt. Discovery selects exact requested fully qualified methods,
then requires every parameterized identity, actual source assembly and input/
owner/attempt link. Other methods in the same assembly are outside that filter;
an extra parameter row of a selected method fails. Duplicate/foreign results,
unknown messages and incomplete inventory retain only their safe prefix.
Discovery never emits execution UUIDs, witness statuses or assertion passes.
Completion now binds the complete JSONL bytes with an incremental SHA-256;
an intended in-bounds timestamp mutation exposed the missing correspondence
before repair. The executor admits only exact frozen discovery display names
and finite scaffolding, never substring matches or raw diagnostic persistence.
All 213 tooling checks (including 108 conformance checks; ten native skips)
and 70 source SDK tests pass locally. A portable
actual VSTest probe discovered both exact enum rows with no unknown diagnostics;
its temporary private fixtures were removed and it makes no native/qualification
claim. Linux diagnostics now discover each selected scope before executing it,
including four discovery transport regressions: twelve scenarios, 35 selected
discovery records and 35 execution observations. Run
[39936903326](https://github.com/Stonefly-Labs/Hoard/actions/runs/39936903326)
at `6a04293` verified all twelve scopes, 108 native foundation checks without
failures/errors/skips, 92,110,938,112 free scratch bytes and all six baselines.
Input digest `5d058da1593a05b0dad1a11b061bf35161bee428da73a243295bdbca5116fe41`.
T014 remains unchecked for its remaining execution-state and loaded-session/
factory/invocation integration.

`RuntimeCaseHistory` now supplies a single-controller, catalog-owned runtime
case-state API. It freezes admitted inputs and exact expected witnesses,
rejects unknown keys/overlapping or replayed attempts, defaults to one attempt
and permits at most three explicitly selected attempts. Actual transport
admission precedes append-only terminal observations; interruption fabricates no
execution, and rejected provenance closes a safely classified attempt before
surfacing the error. Earlier failures, witnesses and proof references remain
immutable after a passing retry. A latest `Passed` state is not qualification:
report admission still rejects any unsuccessful historical attempt.
`NotApplicable` is selected only from catalog exclusions and carries no runtime
proof. Runtime observations alone remain `Incomplete` when separate catalog
controls are outstanding; control-only cases and full controller/profile wiring
are not implemented by this API. Run
[39938028171](https://github.com/Stonefly-Labs/Hoard/actions/runs/39938028171)
at `a9039fa` verified 111 native checks without failures/errors/skips,
92,110,921,728 free scratch bytes, all twelve diagnostic scopes/35 observations
and all six baselines. Input digest
`dba8a0ef424aa28b2053e7cc0e87a12c66b1b8f9f66227d46071bf218420f6b9`.

Typed observed metadata/artifact session wrappers now actually invoke the supplied
factory and pin each interface reference used by consumers and component capture.
Provider getters are lazy: the caller first owns the returned session for cleanup,
including if a getter, fault-hook admission or origin capture subsequently fails.
Reopen delegates to the actual session and records parent/new session identities;
reference-equality instance IDs remain stable across observations without calling
provider equality, hashing or rendering methods. Real cleanup is delegated, never
inferred from origin capture. The closed observation includes the actual initial
declaration digest and executing .NET runtime/architecture; component-byte capture
shares five seconds and a 256 MiB aggregate bound, with 64 MiB per assembly.
Factory/provider operations still require the owning controller's finite scopes.
Parent ingestion independently selects each role's runtime/package bytes, checks
the immutable declaration, environment and parent identity, and rejects missing or
inconsistent role/instance projections. An unpackaged factory cannot borrow a
provider package label. Three C# missing-API regressions and two Python missing-API
regressions preceded the implementation. All 73 source SDK checks and 218 tooling
checks pass locally (ten native tooling skips); focused format checks pass.
The bounded architecture review found no actionable ownership/dependency defects.
Native run
[39940194762](https://github.com/Stonefly-Labs/Hoard/actions/runs/39940194762)
at `457c4e5` verified 114 checks without failures/errors/skips,
92,110,696,448 free scratch bytes, thirteen scopes/38 discoveries/38 executions
and all six baselines. Input digest
`8ffbb9fc9ca1d634e0030b796ae3454f20577185226bb643f370983787781782`.
At that checkpoint these leaf observations were not yet linked to exact
platform execution/attempt/group/input evidence. SQLite/PRAGMA production and full
controller/evaluator integration remain unfinished, and T014 stays unchecked.
An added source-routing regression caught the session diagnostic mistakenly
selecting the smoke assembly. The explicit source scope list is repaired; all
thirteen scenario launches now have focused assembly/package checks before
discovery, and all sixteen SDK orchestration unit tests pass. Native observation
in run `39940194762` established execution. Its predecessor run `39939945388`
had passed 113 native checks and twelve diagnostic scopes before the source-routing
error safely failed the thirteenth scope with `Incomplete`/`EvidenceIncomplete`.

The current origin channel emits only hashes, canonical UUIDs and closed runtime/
case data through bounded `ITestOutputHelper` packets. It does not export provider
names, paths or tokens. Actual VSTest results carry the packets; the safe logger
requires exact run/case and admitted assembly correspondence, complete packet
inventory/digest and nonreplayed sessions before embedding origins in that result's
execution/attempt/group/input/owner-bound proof. Proofs remain bounded to 64 KiB.
Parent ingestion independently selects role/runtime/package assignments, checks
actual initial declaration/runtime/architecture and reopen lineage, and requires
an attributable origin for a passing provider-bound qualification witness.
This requirement does not invent origins for failed/skipped observations.
Case history freezes role assignments, retains immutable admitted origins and
rejects origin replay under fresh attempt/execution IDs.

The bounded architecture review found an instance-coherence map resetting per
origin. Intended rehashed regressions reproduced contradictory component identities
across origins, separate results and fresh attempts; shared instance-identity maps
now reject all three without deleting prior observations. Packet/missing/digest/
foreign-case/replay/raw-field regressions also preceded repairs. The native selection
now includes a real package-mode output probe over an explicitly synthetic metadata
factory, not a provider qualification, plus its source-owned negative controls:
fifteen scopes/46 expected discovery and execution observations. That full channel
is native-pending. Local tooling passes 221 checks (ten native skips); the complete
80-test source SDK suite and focused formatting verification pass. No CLI/full profiles
or SQLite producer are claimed, and T014 remains unchecked pending its remaining
foundation verification.

Native run
[39943968117](https://github.com/Stonefly-Labs/Hoard/actions/runs/39943968117)
at `068788807481b41eed82c8800f94cd5c2173cafa` closes that pending channel check:
116 foundation checks, zero failures/errors/skips, 92,110,667,776 free scratch
bytes, fifteen scopes/46 exact discoveries/46 execution observations and all six
baselines. Input digest
`9b39c7bffc01e32c147d925b741308417eb2e2cc45e796f5af35b72faee18934`;
baseline seal
`41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`.
The real package-mode probe passed without relaxing unknown-output sanitation.
T014 is complete as the generic discovery/origin/proof/state foundation, not full
profile/provider qualification. T015's existing owned preparation has now been
audited against its exact six revisions and recipe/lock/dependency/binary checks;
the same native run seals/verifies all six before candidate compilation and
reverifies after execution. Its source/recipe/lock/binary/package substitution
and alternate-lock derivation regressions pass. T015 is complete; no historical
SDK release was invented. The next foundation task is the explicit lock-preparation
entry point and all new project locks (T016). Concrete SQLite observations,
shared category assertions/adapters and full CLI/evaluator work remain later tasks.

T016 now introduces the explicit non-qualifying preparation command:

```sh
bash scripts/validate-conformance.sh --update-locks --evidence <fresh-private-path>
```

It requires the existing supported Linux ownership/containment/filesystem and
24 GiB scratch preflight. Six historical baselines seal/verify before current
packages build. Existing predecessor locks are never published or graph-resolved;
bounded, recorded local-archive derivations preserve their versions, graph and
third-party hashes. The thirteen explicitly selected conformance locks may be
resolved during preparation only. A second owned run gets a fresh source snapshot,
feed and cache, with no first-run bin/obj or package-cache reuse, and must build
the unchanged locks using `--locked-mode` without resolution fallback. Package
bytes and lock bytes must match. Only then may the command publish the selected
locks, after rechecking the original repository inputs. Source races/foreign paths
reject instead of overwriting unrelated work. This is build/preparation evidence,
not passing tests or provider qualification; complete profile CLI remains T017.

Three missing-API regressions preceded this increment; a fourth focused case
checks successful publication without unrelated changes. All 225 local tooling checks
pass (ten native skips), including invalid-argument sanitation, no force-resolution
fallback after a locked failure, concurrent-source/foreign-path rejection and
publication preserving unrelated bytes. A local pinned SDK Docker experiment
failed the existing native preflight checks (120 tests, 26 prerequisite errors);
no locks published and no checks were weakened. That task-owned container exited
and was removed. Supported Ubuntu CI now performs the actual preparation/fresh
replay and retains only reviewable source lockfiles via a pinned artifact action;
native verification and lock review are pending. No raw diagnostics/store data is
uploaded, and this preparation job is not a mandatory qualifying F-07 profile.

Initial preparation run
[39946559245](https://github.com/Stonefly-Labs/Hoard/actions/runs/39946559245)
at `082d064` passed all 120 native foundation checks without failures/errors/skips
and repeated the fifteen-scope/46-observation SDK diagnostics with all six
baselines. The new preparation job safely failed at command 124 with compiler
`CS1566`: Application's embedded
`specs/004-module-discovery/contracts/openapi.json` was outside the source snapshot
inventory. A focused snapshot regression reproduced the omission before repair.
That exact compiled resource now participates in source fingerprinting/copying;
unrelated specification prose does not. No predecessor artifacts or assertions
were changed, no locks published on the failed path, and repaired native
preparation is recorded below.

Repair run
[39947737831](https://github.com/Stonefly-Labs/Hoard/actions/runs/39947737831)
at `585970d7e4ba3085724b563b026cb9711e41055d` passed all three native jobs:
120 foundation checks without failures/errors/skips, fifteen SDK scopes/
46 discoveries/46 executions with all six baselines, and both independent
preparation/locked-build graphs. Actual free scratch: 92,112,183,296 bytes.
SDK input digest
`3c77e2758f16fbc38ee08652d9cd01685d9ac99c6288d3801f8a4b7fbc2353bb`;
preparation proof
`8a8f66c6cc4d8cc51845ac5091a62caf9456d1cd7fb5a5fe9ee73600c37f9638`.
Both builds reproduced all 18 current packages and 13 selected lock byte sequences.
The downloaded source-only artifact had exactly that inventory; strict review
confirmed seven new binding/consumer/host/contributor locks, local archive hash
updates only in the three existing smoke/package-acceptance variants, no existing
dependency-graph changes and 20 unchanged third-party identity/version/hash triples.
The command's guarded atomic publication imported those generated bytes. No
predecessor source lock changed. T016 is complete as non-qualifying preparation;
T017 normal-profile/verify/aggregate admission and dispatch is next.

The T017 foundation front end now freezes harness-owned exact catalog keys before
dispatch, rejects unsupported/service profiles without fallback, accepts an
explicit `.csproj` only for metadata/artifact category selection, and rejects
duplicate/abbreviated options, mixed modes, nonexistent case IDs and unsafe
evidence paths before allocation. Filtered selection is diagnostic, never
qualification. The shell wrapper needs Python for admission/help/offline modes;
actual execution remains responsible for its native/.NET/Git prerequisites.
A separate Python entry module preserves the evidence library's exception/type
identity instead of executing it twice under different module names.

Preparation still invokes the real T016 driver. Runtime, verify and aggregate
execution is not delivered: admitted requests explicitly return
`Incomplete`/`EvidenceIncomplete`, exit `2`, without creating evidence, executing
providers, borrowing another profile or accepting a cached success summary.
The four new CLI regressions first failed on the missing API/module, then passed.
The actual shell entry also rejects an unsupported profile safely from another
working directory. All 231 tooling checks pass (ten native skips on macOS), including an additional
explicit contributor-project/unchanged-common-selection/private-parent check.
These checks establish admission and failure routing, not runtime profiles,
independent verification or qualification.

Native run
[39949986671](https://github.com/Stonefly-Labs/Hoard/actions/runs/39949986671)
at `83ddd428dbf0070b23c45f8d4fbf9843255bd087` passed 125 foundation checks without
failures/errors/skips and the real shell-to-preparation route with identical bytes
for all 18 packages/13 locks across independent fresh builds. It also repeated
the fifteen SDK scopes/46 discoveries/46 executions and all six baselines.
Free scratch: 92,110,598,144 bytes; input digest
`e6eb8293e95bd22208dba1df7bc71d1c9cf97f3d002c467ba62bd8d3ded39369`;
preparation proof
`f58635d15061fa1eb4377e4187a26fe35d96809e970eca20e6f3a325c3bee666`.

The foundation gate distinguishes dispatch/admission from the real backends
explicitly scheduled in T035/T046/T057/T064/T071..T074. Requiring those complete
backends at T017 would contradict their dependency on T018. Missing backends
must therefore reject, never fall back or qualify; their guards are not completed
profile implementations. T017 is complete only within this foundation scope.
T018's direct typed `BindingContractTests` run passed 19 tests without skips.
Its missing-hook/backup negatives reject with `BindingInvalid`, corrected hooks
admit, mutable caller collections cannot change captured declarations, provider
capabilities cannot select exclusions, and retained cleanup cannot become a
released observation. Native ownership tests preserve live resources and failed
cleanup history; earlier intended missing-handle, parent-replacement, immutable
input and result-origin red/green repairs remain recorded in the plan.
T018 is complete; story work follows, with all backend/qualification tasks open.

The first T019/T020 tests embed the source-owned frozen inventory into the test
assembly and compare the complete compiled SDK category maps against it. Every
case, parameterized witness, independent control and exclusion must match; this
preserves all inherited convergence obligations without treating their labels as
observed provider behavior. New metadata discovery controls exercise complete,
missing and changed corruption parameters for both bindings; altered owned
manifests reject with `InputChanged`. Artifact controls require both handoff
parameters and reject a row borrowed from the other provider. Missing logical,
streaming or authority hooks reject without reducing the agreement, and object
simulation retains its frozen restart exclusions.

All 103 source SDK tests pass without skips, including these 23 new guards;
focused formatting passes. The new native diagnostic selection contains seventeen
scopes/69 expected observations. Native run
[39953736120](https://github.com/Stonefly-Labs/Hoard/actions/runs/39953736120)
at `fa334245ddac4d6e380faf541aeeeb71dc9f5eaa` verified all seventeen scopes/
69 discoveries/69 executions, 127 foundation checks without failures/errors/
skips and six historical baselines. Independent preparation/replay reproduced
all eighteen package/thirteen lock byte sequences. SDK input digest:
`4732cfb3a9872d8361a56da48dbd0ab5d5a4b1e6607be6931eab02401843f6fd`;
preparation proof:
`40632d60679a7d6311d245af98967ab611638673fcec7564ea185c5e2b728a56`.
An intended routing
regression exposed two new scopes going to the smoke assembly and unknown/mixed
names falling through. The controller now admits only homogeneous SDK-test or
smoke namespaces and rejects unknown/mixed/empty selections before launch. It no
longer needs a second hand-maintained list of scenario names to choose the
assembly. All 232 tooling checks pass (ten native skips). This is partial test
preparation: actual compiled common-consumer parity, four adapters, unchanged
behavioral assertions and real-provider category proof remain unbuilt;
T019/T020 stay unchecked.

The next partial extraction introduces six actual SDK consumers under
`Hoard.Testing.Conformance/Metadata/`: aggregate overflow/bounds, registry scope/
interval isolation, bounded-page traversal, competing creates, revision races/
delete-recreate fencing and lease owner/generation/revision fencing. Assertion
bodies and synthetic data follow the inherited tests; public operations receive
the caller's cancellation token. Consumers take the public store only, not a
provider name, private representation or expected result. They do not own or
dispose the caller's store. A focused portable source probe runs all six against
unchanged Memory source; this is not a package-only or native qualification run.
Two source SDK tests reject a structurally valid contradictory-success store at
the common competing-create assertion and propagate cancellation before commit.
The missing namespace was observed before implementation; that compiler red is
not the behavioral faulty-binding proof required by T034. An initial malformed
synthetic ticket was corrected to the public 24-hour ticket contract so rejection
now reaches the intended assertion rather than failing setup.

The next native SDK diagnostic increment also builds the actual Memory archive,
rebinds only the four local archives in the existing package-acceptance lock and
builds that consumer in an independent fresh cache with locked restore. Its
output is separate from source SDK tests; mixed source/package diagnostic
identities reject before launch. Source locks and third-party graphs are
unchanged and all derivations/archives reverify before completion. The six
real-Memory witnesses enter exact safe discovery and execution ingestion, but
this increment's native result is still pending. Two missing-helper reds and
one mixed-assembly routing failure preceded implementation. Existing witnesses/wrappers and all
remaining common assertions are preserved pending full extraction/adapter
rewiring. T019..T024 remain unchecked; no complete parity or category outcome is
claimed.

The executable slice now also includes nine publication-backed consumers:
entity round trips, registry and authorization-partition isolation, atomic
final-graph deletion/disabled retention, competing reference replacement/
removal, zero-reference ABA fencing, telemetry rollback, all seven page query
kinds and oversized request/result rejection. All fifteen common methods run
against unchanged Memory source. A separate test-only registration authority
supplies typed evidence; it is not an artifact provider or proof of live reader/
publication-guard lifetime. Private provider state and algorithms stay outside
the SDK.

An actual Memory-backed partition-aliasing wrapper was observed failing
`MetadataIdentityAssertions.AuthorizationPartitionIsolationAsync` at its digest
equality assertion. The paired control now requires that exact assertion failure
and runs the same compiled delegate against a fresh correct Memory store. No
common assertion changes between the two executions. This is an observed
behavioral negative, not the initial API compiler red; it does not complete
T034's separately required stale-operation/artifact mutation bindings or their
full runtime evidence. The native selection includes these nine consumers,
the paired negative/control and both existing private record/receipt mechanism
regressions: twenty-one scopes/89 expected observations, not yet observed.
The two new paging APIs were also absent in the initial source-probe compile
before their inherited assertions were introduced.

Review of the native package extension found that the shared build helper used
the project filename as archive identity. That holds for the SDK/logger, but
`Memory.csproj` packs `Hoard.Fixtures.Metadata.Memory`. A focused failing
regression preceded an explicit package-identity parameter at that call site.
The source lock/graph and qualification boundary are unchanged.

Run [40053085598](https://github.com/Stonefly-Labs/Hoard/actions/runs/40053085598)
at `69e5e7e0357e559d0ca077ab71ddaafd62dbdc50` verified the earlier six-consumer
slice's unit diagnostics: 127 foundation checks without failures/errors/skips,
eighteen scopes/71 discoveries/71 executions, all six baselines and identical
eighteen-package/thirteen-lock replay. SDK input digest:
`3396b23f888f1a498cfe7415a7ddf598a7deffa2bc1f4ccdfdecddbd7fd2e60b`;
preparation proof:
`641ff322e4c09f5ba56ae3ed2ab8e8adb99af6228ec38e1376ee2722ce1bae2d`.
It did not yet contain the actual Memory-package consumer execution extension.

Four more inherited consumers now preserve exact ticket expiry/rollback, lease
rollback/next-generation fencing, opaque cursor scope/size/foreign-epoch rejection
with live resume, and exact canonical text/forbidden-value handling. The typed
`MetadataConformanceClock` controls only metadata UTC time; timestamps, timers
and outer deadlines remain real. Cursor checks use two independent prepared
stores without interpreting token encoding. Forbidden URI inputs are constructed
from explicitly synthetic user-info, not credentials. Each missing API was
observed before implementation; these compiler failures are not behavioral
mutation proof. The temporary source probe now passes 22 tests without skips:
nineteen actual common consumers, both private corruption mechanisms and the
paired aliasing/control. Focused formatting and all 236 tooling checks pass
(ten native skips on macOS).

Native run `40053284658` at `3714a91` safely failed its SDK diagnostic during
candidate construction with `Incomplete`/`PrerequisiteMissing`, before any
provider-consumer observations. That is consistent with the archive-name
assumption corrected in `5bdfc98`; the corrected native result is recorded below.
That checkpoint selected twenty-four scopes/93 discovery/execution
observations. No failed native checkpoint or portable source probe is promoted
to package/category qualification, and T019..T024 remain open.

The next common consumer adds fourteen typed receipt-corruption shapes. Common
code owns failure classification, exact original tickets, unchanged damaged
state, independent effects and restored replay/reconciliation; private encodings
stay in the Memory probe. The source-only probe passes 23 tests without skips,
including twenty actual consumers, and ordinary SDK tests pass 105. Source
controls are not complete admitted bindings; full session diagnostic integration
and parity remain open. Current native selection: 24 scopes/94 observations,
pending.

The repaired native run
[40053903410](https://github.com/Stonefly-Labs/Hoard/actions/runs/40053903410)
at `5bdfc98ca5c8586416c4cfa096c243c44dc1f298` succeeded in all three jobs:
131 foundation checks without failures/errors/skips, 21 scopes/89 discoveries/
89 executions and six baselines. This verifies the first fifteen actual
Memory-package consumers, the paired aliasing/control and identical replay of
eighteen packages/thirteen locks. Input digest:
`3d8f73bbf2b089f602a3654a45194c4f50b338981e4ba25b31ca30a994d43aec`;
preparation proof:
`7fd01849664c83ca59b1617edbd2eec0a3937b320bca2e2b0797fa452a5c09f6`.
This is package diagnostic execution, not category qualification.

Three additional common record consumers bring the executable slice to 23
methods. They preserve five page-damage shapes plus permanent corruption,
missing-versus-corrupt grouped reads and all five query-dimension cases,
including unchanged damaged state, complete failures, exact restoration,
single-row traversal and empty foreign scopes. Memory now exercises those
actual corruption paths rather than inheriting the old SQLite-only no-op.
A paired unchanged-scope negative fails the exact common receipt assertion;
the same compiled delegate passes with real Memory mutation/restoration.
The source-only probe passes 31 tests without skips; SDK source tests pass 105,
tooling 236 with ten native skips, and focused formatting/catalog/inventory
checks pass. The native vector is 26 scopes/102 observations, pending.
Native run [40054314377](https://github.com/Stonefly-Labs/Hoard/actions/runs/40054314377)
at `52043f4108949db8f07b4ed0ff677e4481600b65` subsequently verified the first
nineteen consumers against actual Memory packages: all three jobs succeeded,
131 foundation checks without failures/errors/skips, 24 scopes/93 discoveries/
93 executions, six baselines and identical eighteen-package/thirteen-lock
replay. Input digest:
`e52695f91f85dd6661bdf7c3e2593a736106c4a1013a0f5dd62a7bb97c1f150d`;
preparation proof:
`8005f7bedeaab8720c7db522a33f1e125f759d727cb9f848db290ebdfbac7689`.
The new corruption consumers remain pending native package execution.
Bounded architecture review found no actionable defects in this extraction/
mechanism bridge; complete bindings, parity, diagnostic integration and final
provider/package graph review remain outstanding.

Six typed observation consumers bring the slice to 29 methods: independent
candidate reads, each partial-candidate rollback, grouped root snapshots,
reconciliation I/O uncertainty, lost acknowledgment/abandonment and distinct
contributions without duplicate replay. The metadata fault driver now requires
`ObserveBoundaryAsync` over five closed logical points; private Memory strings
remain in its test bridge. SDK-owned counters prove intended callbacks occurred.
Registration disposal does not claim store settlement. Bounded real-time
barriers retain independent cleanup and no raw diagnostics are retained.
Architecture review identified a skipped writer join when a grouped read
faulted/canceled; both regressions failed before repair and pass after joining
both public tasks. Underlying store ownership remains separate.

The source-only probe passes 39 tests without skips and ordinary SDK tests pass
105; tooling 236 with ten native skips and changed format/catalog/inventory
checks pass. Current native vector: 27 scopes/110 observations, pending.
Run [40054937445](https://github.com/Stonefly-Labs/Hoard/actions/runs/40054937445)
at `cf5afb3946871676296322808d5a51f113cd3da8` verified all twenty earlier consumers
including receipt damage through actual Memory packages: all three jobs
succeeded, 131 foundation tests without failures/errors/skips, 24 scopes/
94 observations, six baselines and identical eighteen-package/thirteen-lock
replay. Input digest:
`bafcb0ad8ade5f137ab53c76ccd418c2a4d129a95362fe9c645d62b7642c1f1a`;
preparation proof:
`b673a1828e80f56052739a36fcb7fb3dab3866677bc201e928733c5d2e14a864`.
This remains partial extraction/package diagnostics, not category qualification.

Five further consumers bring the slice to 34 methods: writer-contention
uncertainty and four publication-authority checks for matching evidence,
orphan-versus-rollback, protection across timeout/settlement and replay without
reacquisition. Authority observations count actual acquisition/disposal calls;
revocation changes logical evidence availability. This test probe is not an
artifact store or cross-store integration proof.
Architecture review found skipped/cancelable settlement on writer-contention
failure; both regressions failed first and now pass after unconditional
non-cancelable settlement following exclusion release. Public task completion
does not imply session/resource release.

The source-only probe passes 44 tests without skips, ordinary SDK tests 107,
tooling 236 with ten native skips, and focused format/catalog/inventory checks
pass. Current native selection: 28 scopes/117 observations, pending.
Run [40055429472](https://github.com/Stonefly-Labs/Hoard/actions/runs/40055429472)
at `2c70dc692c5be088db3dea6f27e56bff8396e9d2` verified all 23 earlier consumers,
including actual page/query-dimension corruption and no-op negative/control:
all three jobs succeeded, 131 foundation checks without failures/errors/skips,
26 scopes/102 observations, six baselines and identical eighteen-package/
thirteen-lock replay. Input digest:
`0e87cd4b3fa1076ab99c1d99db9474d6e500b305e4bbe6e80dc3b030d42c8544`;
preparation proof:
`c0e9d29c9f47d67976adc306aff8859c978d38fd970dae558465f8ff9d6db2e0`.
Run [40056205385](https://github.com/Stonefly-Labs/Hoard/actions/runs/40056205385)
at `a1c4a1fd58f9c872e97160397b9d4015ddfb55a2` subsequently verified all 29 earlier
consumers, including atomicity/uncertainty and both failed/canceled-read joins:
all three jobs succeeded, 131 foundation checks without failures/errors/skips,
27 scopes/110 observations, six baselines and identical eighteen-package/
thirteen-lock replay. Input digest:
`ad3ea626a69e4bea331f987c9b716b00cc2aa10f1c5394db4cf8852589fbc525`;
preparation proof:
`18f093bf8be4763ea434961a9a785dcbeaa053dd51530e182b80b31a94c21d00`.
The five newer writer/authority consumers remain pending native execution; all
remaining full task obligations are unchanged.

Seven new lease/deadline consumers bring the slice to 41 methods. They cover
generation overflow, expiry at the final renew/release/guard decision, writer
budget, cancellation decisions, bounded pending readers, disposal ownership and
known exception classification. A full-slice failure exposed a definite canceled
reservation returning while work was still owned; the next reservation correctly
reported Unavailable. The common consumer now joins actual settlement first,
with a focused ordering regression and non-cancelable cleanup. The shared join
helper preserves publication cleanup. Bounded architecture review found no
actionable defects. Source-only Memory: 53 passed; ordinary SDK: 108 passed,
all without skips. Tooling: 236 checks/ten native skips; focused format/catalog/
inventory checks pass. Current native selection: 30 scopes/127 observations,
pending; the inherited incomplete-cleanup case and full extraction remain open.

Run [40057148652](https://github.com/Stonefly-Labs/Hoard/actions/runs/40057148652)
at `bb7478ca56634f085cc0b7f05f0926823ad7639c` verified all 34 earlier consumers
including publication authority and both writer-settlement regressions: all
three jobs succeeded, 131 foundation checks without failures/errors/skips,
28 scopes/117 observations, six historical baselines and identical
eighteen-package/thirteen-lock replay. Input digest:
`de9197030e3a8b8675334191edc4bae59dbb874850a72c52a06fc72c918e0e37`;
preparation proof:
`dfb1356f57a03483dff44f9b8b092c7e58bb26bf33ea21add85344cad184a9e6`.
No current source result substitutes for native package evidence.

Six capacity/admission/diagnostic consumers bring the executable slice to 47.
They preserve storage rollback/same-ticket retry, live-ledger receipt retention,
explicit admission, invalid budgets/closed stores, actual incomplete cleanup and
safe public/debugger diagnostics. Required typed counters record only boundary
and closed diagnostic counts; unknown diagnostic text rejects without retention.
The incomplete-cleanup check holds actual work for up to 60 seconds, outlasting
the real 30-second cleanup limit, while ordinary barriers remain unchanged.
It verifies failed cleanup with settlement still pending, then joins every
started task and genuine settlement before retrying disposal. No early resource
release is inferred. A dropped-diagnostic negative fails the identical common
consumer that passes with actual observation.

Source-only Memory: 60 passed without skips in 33 seconds, including real ledger
filling and cleanup timeout; ordinary SDK: 108 passed. Tooling: 236 checks/ten
native skips; focused formatting/catalog/inventory checks pass. Bounded
architecture review found no actionable defects. Current native selection:
31 scopes/134 observations, pending. Full schema extraction, actual adapters,
wrapper parity and qualification remain unfinished.

Five schema consumers bring the slice to 52 methods: unrecognized/partial
layouts, authorized legacy upgrade with entity/epoch/receipt checks, invalid
authorization, concurrent exclusion and future/corrupt reopen. Common code uses
the inspected target version, never provider names or version suffixes. Required
typed state fingerprints preserve actual raw state without decoding or repair;
the Memory helper frames all logical state sections and raw records. A focused
mutation regression verifies distinct hashes. The schema session probe remains
explicitly non-admitted, not a complete binding. Concurrent upgrades always
release and join both started tasks plus actual settlement.

Source-only Memory: 67 passed; ordinary SDK: 108 passed, without skips.
Tooling: 236 checks/ten native skips; focused SDK/Memory formatting and catalog/
inventory checks pass. Architecture review found no actionable defects.
Current native selection: 32 scopes/141 observations, pending.
Run [40057842920](https://github.com/Stonefly-Labs/Hoard/actions/runs/40057842920)
at `8df0cc67c183bf3d9f7ef016f716a9bae9039aa4` verified all 41 earlier consumers
including lease/deadline rows and pre-canceled reservation ordering: all three
jobs succeeded, 131 foundation checks without failures/errors/skips, 30 scopes/
127 observations, six baselines and identical eighteen-package/thirteen-lock
replay. Input digest:
`66c0778b4286c575a33d24e289da68758199371bb9f043ecf00669c285dc5762`;
preparation proof:
`17711c00cfeee7698e747b0f98de5d6ace3a00ecee3a667ca7c34fd35ee30a20`.
No complete adapter/parity or category qualification is implied.

The 53rd consumer preserves malformed continuation fields through closed typed
controls: six shapes across contract/epoch/schema/query/size/position, with
classification and exact valid resume/traversal checked in common code.
Private JSON/field names stay in the fixture; Memory schema identity uses its
epoch. A no-op mutation fails the named common assertion and real damage passes
the unchanged delegate. Source-only Memory: 74 passed; SDK108 passed, without
skips. Tooling236/ten native skips and focused format/catalog/inventory checks
pass. Current native selection: 33 scopes/148 observations, pending.

Run [40058311447](https://github.com/Stonefly-Labs/Hoard/actions/runs/40058311447)
at `449636a677ea6ee8f7a3c6380e8773ddbf4f3eb4` verified all 47 earlier consumers
including actual ledger fill, real 30-second cleanup failure with retained work
and dropped-diagnostic negative/control: all three jobs succeeded, 131 foundation
checks without failures/errors/skips, 31 scopes/134 observations, six baselines
and identical eighteen-package/thirteen-lock replay. Input digest:
`e3206dfcb1ab2685463eb3647cb91c07c9e4a946343cbf4bc0d500b7a6499aff`;
preparation proof:
`e88a943cd304ee70607ccc074f35af2a49be5bcc5db45cdbcec666d071e1b705`.
Full binding admission/parity and category qualification remain unfinished.

Observed metadata creation now has an explicit legacy factory entry using the
same declaration/lazy-getter/ownership gate as current creation; arbitrary case
IDs do not select setup. Memory exposes the genuine stable pending-work task
separately from its existing bounded settlement observer. Missing APIs failed
first; the new regressions verify actual factory selection and retained work
after a public deadline. SDK109 and source-only Memory75 pass without skips;
tooling236/ten native skips and focused checks pass. Current native selection:
34 scopes/150 observations, pending. Concrete adapters remain unfinished.

Run [40058954688](https://github.com/Stonefly-Labs/Hoard/actions/runs/40058954688)
at `cf9c20f2d9bdbc797ce5c4cacddd13966b02fa3d` verified all 52 earlier consumers
including schema upgrade/reopen/exclusion and raw fingerprint mutation: all
three jobs passed, 131 foundation checks without failures/errors/skips,
32 scopes/141 observations, six baselines and identical eighteen-package/
thirteen-lock replay. Input digest:
`f3f0c286237ef7f0708ffd9a14d0434ca6070b2b08128470fc2dd6c319d629b9`;
preparation proof:
`035624cf6eebad450d3f1e50b919466ef363cd6227180639b0d0a2472a04c5ab`.
Newer source results do not substitute for native execution or qualification.

The first concrete Memory binding now implements explicit current/legacy
factories, typed controls, atomic close/capture/reopen and genuine settlement
ledger integration. Independent committed reads remain tracked actual work;
public operations and SDK/provider dependency boundaries are unchanged.
Reusable provider-private payload damage replaces duplicate JSON mutation in
the existing probes. Disposal pins the actual task after admission closes,
preserves identity on retries, surfaces observation failures and never claims
physical release.

Its 19 allocator-double rows plus one real SDK-allocator integration pass
alongside the earlier 75 Memory probes against actual packed SDK/provider/
binding packages: 95 tests, no skips, ~34s, including real 30-second incomplete
cleanup. Ordinary source SDK109, tooling236/ten native skips and focused checks
pass. The package-mode consumer deliberately adds the existing Memory binding
reference and generated lock; native preparation captures/derives/reverifies
five actual package identities. A bounded custom architecture review found no
actionable defects. Current native vector: 37 scopes/170 observations, verified below;
T023 and complete qualification remain unchecked.

Native continuation run
[40059263911](https://github.com/Stonefly-Labs/Hoard/actions/runs/40059263911)
verified all 53 earlier consumers, 33 scopes/148 observations. Latest verified
factory/settlement run
[40059814134](https://github.com/Stonefly-Labs/Hoard/actions/runs/40059814134)
at `46be806d30be26f47fafaa9b064241c48759d75c` passed all three jobs,
131 foundation checks without failures/errors/skips, 34 scopes/150 observations,
six baselines and eighteen-package/thirteen-lock replay. Input digest:
`be49fdd9b29de2382622b3dc2d77166d5b680fd6b8c76511433725626998becd`;
preparation proof:
`bd7ecd7d3a3e27b88232c8625ca037fd45d7b2a7df2cb445fc1dfcb6603d6c3d`.
Those runs predate the new concrete adapter; do not relabel their scope.

Run [40061416909](https://github.com/Stonefly-Labs/Hoard/actions/runs/40061416909)
at `9be7ad73b34e17b59a5c982b59d9645532f70f72` subsequently passed all three
jobs: 131 foundation checks without failures/errors/skips, 37 scopes/170 exact
discoveries/executions including the concrete Memory binding, six baselines
and identical eighteen-package/thirteen-lock replay. Input digest:
`e8a0ea337babef2f29d884e12be691c654b127c7a657e526ee30181108c10b00`;
preparation proof:
`f7bae966d851b9b034d9d6c620122dc89ad1fe73de922db625e2c5567647bf5f`.
Free scratch: 91,724,914,688 bytes. This remains non-qualifying.

SQLite's prerequisite controls now track independent read work and async writer
leases through the actual worker lifetime, distinct from bounded idle
observation. Held writer leases do not block ordinary idle; shutdown releases
them and waits for their actual cleanup before closing primary native handles.
Caller cancellation retains late work/acquisition; escaped diagnostic/cleanup
failures fault genuine lifetime instead of reporting successful settlement.
Six source-probe checks pass without skips. The canceled-acquisition test first
failed because no actual acquisition boundary was observable; a tracked async
acquisition seam now exposes it. Focused formatting passes, and bounded custom
architecture review found no actionable defects in the lifetime increment.
These are source-only fixture prerequisites, not a completed SQLite binding,
package/native SQLite evidence, durable reopen or category qualification.
Legacy synchronous fixture helpers remain caller-owned. No product contract,
project reference, schema, public API or architecture diagram changed.

The initial SQLite binding now implements current/legacy factories, actual
same-database directory handoff, verified backup authorization and typed
record/operation/continuation controls. Old workers close before ownership
transfers; only final-head disposal binds the directory's actual lifetime.
Canceled reopen preserves the original owner and pending work. Raw state
observation requires no schema admission or repair and preserves native storage
classes. The logical publication authority is compiled from shared fixture
source into both binding assemblies without cross-provider delegation.

Bounded architecture review found full-payload native sorting before size
limits. An intended oversized-unindexed-row failure drove native value/progress
guards, bounded size/count preflight and managed sorting of bounded row digests.
Native limits alone did not reject the existing aggregate row; the test stayed
red until preflight was added. The repair passes in actual package mode.
The reviewed seven-archive graph adds only SQLite binding/provider and six
pinned dependencies, preserving existing third-party hashes/graphs. A separate
empty-cache default locked restore/build passed. Selected package tests pass
135/no skips (~33s): 95 Memory and 40 SQLite, including real 30-second cleanup.
The UTF-8 fingerprint bound rejects multi-byte text before mutation; its intended
failure now passes. Fresh package caches and build output directories prevent
same-version, canonical-timestamp archives from leaving stale copied assemblies.
Memory source94, tooling236/ten native skips and focused checks also pass.
These do not establish Linux-supervisor or complete category qualification.
Native selection remains 37 Memory/SDK/logger scopes. A package-only owned
environment entry point now observes actual configured SQLite state/version
and the loaded native module, compares the library with the exact SHA-512-pinned
NuGet archive, and includes native runtime assets in pre/post input hashing.
The package tests still pass 135/no skips after adding this entry point.
Missing environment admission and omitted native-asset hashing first failed
focused regressions; both repairs pass. Linux producer execution remains pending,
not a verified SQLite scope or category pass.

The remaining current logical consumers now run through the SQLite binding,
including independent candidate reads, exact time/expiry decisions, native writer
contention, query corruption, publication and actual disposal ownership.
All 44 added rows pass; the full selected package suite passes 179/no skips:
95 Memory and 84 SQLite. Every one of the current 53 SDK assertion methods
executes through SQLite. No provider-specific expected results or altered SDK
assertions were added. This local count is not the catalog's 179 applicable
category keys, complete frozen-wrapper parity or Linux SQLite case execution.

Published seven-archive checkpoint
[40064540294](https://github.com/Stonefly-Labs/Hoard/actions/runs/40064540294)
at `721231acffcc801d8b60467391f0c4ac7cdb43ed` passed all three jobs:
131 foundation checks without failures/errors/skips, 37 scopes/170 exact
observations, six historical baselines and identical eighteen-package/
thirteen-lock replay. Input:
`b3cfcb3f9e0bf3dd02784ca2699eb1392f89d2963425b9beb537ed222a80b6f3`;
preparation proof:
`738dbcf048cb1b58193f954caf0130b706e49f2f3d329448cb765016db2e9e90`.
Free scratch: 92,109,443,072 bytes. It verifies package preparation, not the
subsequently added SQLite environment producer or SQLite test execution.

The initial environment checkpoint
[40065028512](https://github.com/Stonefly-Labs/Hoard/actions/runs/40065028512)
passed 132 native foundation checks, then failed safely: SDK diagnostics rejected
`InputChanged`, and lock replay reported compiler `CS8892` at command 169.
Real restored signed SQLite package bytes reproduced the distinction between
NuGet's normalized pinned content hash and raw archive SHA-512. Both identities
are now checked through the fresh locked-restore receipts, with exact member
comparison and unchanged pre/post provenance; no package pin changed.
The probe entry point is excluded from the general consumer, whose actual
fresh-cache eleven-archive locked build now passes without warnings/errors.
Missing owned temporary routing also failed first; child temporary files now
stay beneath private owned caches, with a Linux-only actual-child regression.

Native run
[40066075996](https://github.com/Stonefly-Labs/Hoard/actions/runs/40066075996)
at `e6c4256bcb71fb7726344d714cdba2b83b72b547` passed all three jobs:
134 foundation checks without failures/errors/skips and 50 scopes/254 exact
discoveries/executions with expected diagnostics, including all 84 SQLite
identities. Actual SQLite 3.53.3, WAL/FULL/foreign-keys/busy-timeout-zero and
native archive/member provenance were observed; native temporary placement and
identical eighteen-package/thirteen-lock replay also passed. Full receipt hashes
are in the F-07 plan. This remains a non-qualifying diagnostic run.

The isolated diagnostic runs real SQLite native non-cooperation only in a dedicated
controller-owned child. The typed fault stops at the actual post-commit native
boundary, retaining the publication guard through a one-second caller deadline
and genuine 30-second incomplete cleanup. The producer records actual guard
counts, uncertain outcome and ticket hashes, disposed admission, pending worker
settlement and retained allocator history. A separate parent-written recovery
receipt records the exact PID/start, monotonic duration, SIGKILL and confirmed
group exit after the 45-second watchdog; no ordinary timeout is passing evidence.
The five-minute stall is never selected inside an ordinary test process.
Missing admission first failed a regression. Tooling241 passes locally
(230 passed, eleven native macOS skips); current seven-archive empty-cache
package tests pass 179/no skips, with output DLL bytes matching all seven
archives. Package-mode probe compilation and general-consumer entry-point
isolation build without warnings/errors. Bounded architecture review found no
actionable issues, while explicitly excluding unobserved native behavior.
Native run
[40067365972](https://github.com/Stonefly-Labs/Hoard/actions/runs/40067365972)
at `7530cad06a9010b69b570d48610e3a7479a4f852` passed all three jobs:
136 foundation checks without failures/errors/skips, the same 50 scopes/254
exact observations, and matching actual native producer/controller containment
proofs. SQLite 3.53.3/native provenance, six sealed baselines and identical
eighteen-package/thirteen-lock replay also passed. T026 stays unchecked until
every inherited recovery barrier and full provenance gate passes.

The first seven original metadata wrappers (MP-01..06/13) now delegate to the
existing packaged SDK entity/identity/bounds assertions. Their frozen names,
fixture factory, schema preparation, clock and disposal remain unchanged; a
private authority adapter forwards to the original fixture authority. Metadata
preparation copies/packs the SDK before the package-only suite and includes it
in the eight-archive inventory. Its unchanged-consumer proof now hashes the SDK
DLL as well and rejects changes after either composition. The missing SDK build
and previously undetected SDK mutation both failed focused regressions first.
All 72 actual package-backed predecessor tests passed against Memory and all 72
against SQLite, with no skips. Fresh default locked replay reproduced all eight
archives from an empty cache; seven wrapper dependency DLLs and the separately
built Application DLL matched their archives byte-for-byte. Only the SDK entry
is added to the tracked predecessor test lock; prior entries and third-party
pins are preserved. Private preparation rebounded local payload hashes without
altering historical source locks. Full extraction, typed-control forwarding,
frozen-parameter parity and safe exact witness imports remain unfinished.

A further ten wrappers now delegate shared paging/query/bounds, continuation
scope/epoch, competing-create/revision races and publication/reference/telemetry
assertions, bringing adoption to 17 original methods. The six malformed-cursor
theory rows and control-dependent cases remain unchanged. An actual locked
restore of the repository's package-mode test project used the verified private
eight-archive graph without editing source locks. The same freshly built suite
passed all 21 affected class tests against Memory and all 21 against SQLite,
without failures/skips; focused whitespace and frozen inventory checks pass.
The SDK and provider packages themselves are unchanged by these ten delegates.

Five additional original MP-09/10/26/27 wrappers now delegate to unchanged SDK
atomicity/publication consumers, bringing adoption to 22 methods. A typed
test-side observation bridge uses new scoped registration in the original
HostAdapters fixture. Duplicate registration rejects without replacing the
owner; idempotent scope disposal cannot remove a newer legacy observer and
does not settle an active callback. Existing fixture methods remain available;
an additive independent-snapshot overload honors cancellation and the fixture
keeps concrete schema-hook mapping private.

Three new ownership tests first failed the missing-registration assertion.
After repair, the complete 76-test suite passed on each actual provider.
A fifth observer test subsequently exercised the real schema-upgrade hook and
the atomicity wrapper now checks the SDK's injected canary as well as its
original canary; all 16 affected tests pass on both providers. Fresh default
locked replay reproduced eight archives and their actual DLLs; only the
additive HostAdapters archive differs from the prior preparation. Repository/
historical locks, SDK, provider and platform archives remain unchanged.
Tooling243 (232 passed, eleven macOS-native skips), frozen catalogs and focused
wrapper/fixture whitespace checks pass. Full schema/corruption/control parity
and safe origin imports remain open; SQLite's original U1 exclusion witness is
not replaced by the new SDK U0 mapping.

The next focused repair preserves both boundaries explicitly:
`BeforeSchemaUpgrade` remains SQLite U0 before the transaction;
`SchemaCandidatePrepared` observes U1 after candidate creation with the native
writer held. Memory maps both to its real decision boundary. The shared
exclusion consumer and original MP-35 now select the candidate hook. A real
second connection initially acquired `BEGIN IMMEDIATE` at U0, failing the
expected SQLite BUSY (5) assertion; the U1 repair passes.
Final formatted packages pass 180 selected SDK/binding tests and 11 original
schema/observer tests per provider without skips. An independent empty-cache
locked replay reproduces all eight archives and actual dependency DLLs; its
SDK archive is identical to the seven-archive binding feed. Only the SDK hash
changes in the tracked predecessor test lock, not its graph or other pins.
The expanded native request is 50 scopes/255 observations, including 85 SQLite
identities. Native run `40070802352` at `3bca09c` subsequently verified it.

Native run
[40068886475](https://github.com/Stonefly-Labs/Hoard/actions/runs/40068886475)
at `5528ecd` independently passed all three jobs: 136 foundation checks without
failures/errors/skips, the earlier 50/254 vector, native containment and identical
eighteen-package/thirteen-lock replay. It does not run the original predecessor
wrapper suite or the new candidate-boundary regression.

The next original MP-08 extraction preserves all six frozen malformed-cursor
rows and delegates their assertions to the existing shared SDK consumer
(23 original delegated methods). The original fixture maps semantic components
to its actual provider encoding and reuses the independent provider payload
damage helpers. A new parity guard decodes an actual continuation and proves
typed omission covers every original field, removes only that field and leaves
other values unchanged. Memory's combined epoch/schema mapping remains real,
not an extra synthetic field. Cancelled/unknown typed requests reject and the
valid continuation stays unchanged.
The new guard first failed the missing original-fixture corruption-method
assertion in a successfully compiled package-mode assembly. After repair,
all 79 current predecessor tests pass against each provider without skips.
Fresh default locked replay reproduces eight archives and exact DLLs, using
the same SDK/suite bytes for both compositions. Only the additive HostAdapters
archive changes; SDK/provider/platform archives and source locks are unchanged.
This is not complete metadata extraction or safe exact runtime-origin import.

Six original MP-19/20/28/32 wrappers now additionally share admission,
storage/ledger capacity and lease overflow/owner-generation-revision fencing
consumers, bringing adoption to 29 methods. Fresh admission fixtures remain
unprepared; invalid-budget disposal is still guaranteed by the shared
consumer's `finally`, and capacity/generation callbacks forward the original
controls after cancellation checks. The counter bridge reads actual boundary
activity and diagnostic occurrences, not provider-returned success flags.
An actual locked restore of the repository test project used the already
verified eight-archive graph without source-lock changes. The identical
freshly compiled suite passed all 16 affected class tests against each provider,
without skips. Its seven dependency DLLs match the archives. Focused whitespace
and frozen inventory checks pass; ordinary source-mode assets are restored.
SDK/provider/fixture archives are unchanged by these six delegates.

Three MP-17/29/30 clock-dependent methods now additionally delegate to shared
consumers (32 original methods total). Additive SDK callback overloads target
the original `MetadataTestClock`; existing clock-object signatures remain and
forward to the same assertion bodies. The store's actual `TimeProvider` is
never replaced. MP-29 still runs renew/release/guard with separate fresh
fixtures, including observation at the final decision and the rollback fence.
The new bridge regression first failed the missing callback-overload assertion.
Its repaired actual-store proof observes the original clock rolled back while
new ticket issuance retains the monotonic expiry floor.
All 80 predecessor tests pass on each provider without skips, and all 180
selected SDK/binding tests pass against final formatted packages. Independent
fresh locked replay reproduces eight archives and exact DLLs; both feed
families have the identical SDK archive. Only the SDK hash changes in the
tracked predecessor lock, preserving its graph and other entries. Tooling243,
frozen catalogs and focused formatting pass.

Native [40070802352](https://github.com/Stonefly-Labs/Hoard/actions/runs/40070802352)
at `3bca09c` passed all three jobs: 136 foundation checks without failures/
errors/skips, 50 scopes/255 observations including 85 SQLite identities,
actual native containment and identical eighteen-package/thirteen-lock replay.
This verifies the U1 regression, not the later clock-callback or original-wrapper
suites; those were validated locally. Full category/recovery/origin gates remain.

Eleven original deadline/reconciliation/replay wrappers now additionally share
consumers (43 delegated methods). Scoped observation and actual idle settlement
forward through the original fixture, retaining its original writer mechanism.
The additive cancellation-aware writer overload preserves the old signature,
propagates Memory acquisition cancellation and checks native pre-admission.
The test-side async lease disposes only the holder it acquired; cancellation
after acquisition disposes that holder before reporting cancellation.
A new ownership regression first failed the missing-overload assertion.
After repair, it proves a cancelled acquisition does not release the original
writer: the held commit expires without effects, then the same ticket succeeds
after release. All 81 predecessor tests pass on each provider without skips,
including actual 30-second cleanup failure/retention, both cancellation
decision boundaries, full queue ownership and original-ticket reconciliation.
Fresh default locked replay reproduces eight archives and exact DLLs; only the
additive HostAdapters archive changes. SDK/provider/platform archives and source
locks remain unchanged. Focused compiled whitespace and frozen inventory pass.
Complete corruption/schema extraction and safe exact origin ingestion remain.

Four further original corruption methods now delegate (47 total), preserving
all five stored-query rows and fourteen receipt-corruption shapes. Scoped
fixture controls retain original target ownership, exact restoration, failed
cleanup recovery and close/reopen protection. Native raw reads now use actual
independent bounded connections instead of queueing behind a held primary
candidate. A deliberate queued-reader substitution failed its named fact.
Bounded architecture review found two races: close/reopen could admit an owner
after its empty-owner check, and independent capture could become stale before
replacement. A lifecycle gate makes closure/registration atomic; provider-private
compare/exchange rejects changed images under the actual writer. A real
intervening-commit regression first failed its payload equality assertion before
that repair. Failed or timed-out application settles actual worker activity
before deciding whether restoration is required; failed settlement retains the
owner rather than treating a caller result as release.

All 87 current predecessor tests pass on each provider without skips, and 181
selected SDK/binding tests pass locally. Independent fresh locked replay
reproduces eight archives, seven wrapper DLLs and the separate Application DLL.
Seven actual binding output DLLs match their archives; both feed families keep
the unchanged SDK. Source/historical locks remain unchanged. The expanded Linux
request is 50 scopes/256 observations, including 86 SQLite identities; native
run `40097647586` at `84e8a4b` subsequently verified it, with 136 foundation
checks without failures/errors/skips, genuine native containment and identical
eighteen-package/thirteen-lock replay. Product architecture, ADRs, diagrams and deployment
examples are unaffected: these are test-only controls with no production API,
dependency-edge, composition or infrastructure changes.

The original MP-22 diagnostics method now also delegates (48 methods total).
Its connection-shaped failure injection and initial outcome assertions remain
untouched. The additive SDK overload then shares counters, rollback, every
failure code and all four diagnostic/debug-display checks with the original
canary and sanitizer. It consumes the caller's existing hook without claiming
its registration; the old scoped-hook API forwards to this same core.
The ownership regression first failed the missing-overload assertion, then
proved on actual stores that the original callback remains registered after
the consumer returns. All 88 current predecessor tests pass without skips on
each provider and 181 selected SDK/binding tests pass locally. Fresh locked
replay reproduces eight archives and exact DLLs; SDK bytes agree across feeds.
The predecessor source lock changes only its SDK hash; all other entries and
historical pins remain unchanged. Native run `40097647586` predates this change
and does not execute original wrappers. Schema/session extraction and exact
origin ingestion remain unfinished.

The five original schema wrappers now also delegate (53 methods total) through
an explicitly narrow schema assertion session, without fabricated mandatory
category fault hooks. Existing full-session APIs still forward to the same
assertions. The original factories, real backup authorization, U1 exclusion and
same-database reopen remain in use. Cancellation before transfer leaves the
original directory owner responsible for cleanup. Actual SQLite database/WAL
hashing runs inside owned independent work with bounded streamed buffers;
Memory uses its actual logical image. Initially observed WALs remain mandatory;
only newly empty WAL creation on read-only reopen is ignored.

Bounded architecture review found a real in-flight cancellation diagnostic bug.
Its deterministic actual-file regression first observed
`metadata.internal_failure`; translating the stream's cancellation into the
worker budget failure fixes it without changing generic failure handling.
The regression awaits genuine settlement and checks no diagnostic was emitted.
All 89 current original tests pass per provider; 183 selected SDK/binding tests
pass locally, without skips. Independent fresh locked replay reproduces eight
archives and all wrapper/Application DLLs; seven actual binding DLLs also match
archive members and both feeds use identical SDK bytes. Only the SDK hash
changes in the tracked predecessor lock, preserving other/historical entries.
Native run `40098981184` at `11875e5` passed all three jobs, 136 foundation
checks, 50 scopes/256 exact discoveries/executions, native containment and
eighteen-package/thirteen-lock replay. It predates this schema increment and
does not execute original wrappers. The new request is 50 scopes/258
observations (88 SQLite identities); schema run `40100325269` at `82a9b09`
subsequently verified it, all 136 foundation checks, genuine native containment
and identical eighteen-package/thirteen-lock replay. Exact frozen
parity/controller-origin imports and complete feature gates remain open.
Product architecture, ADRs, diagrams and deployment examples are unaffected:
this changes test-only assertion/session controls, not production contracts,
provider composition, infrastructure or deployment.

The native SDK diagnostic now builds and selects the actual original metadata
test assembly as well: all 63 frozen runtime identities run independently for
Memory and SQLite, after exact safe discovery. It privately rebinds the original
seven-package graph without adding logger dependencies or changing tracked
locks. The logger is installed as a byte-verified adapter; all seven actual
wrapper dependency images must match their archives. Original runtime,
dependency and native files join pre/post immutable input capture. The diagnostic
feed now has ten archives; the separate lock-preparation job's eighteen-package/
thirteen-lock graph is unchanged.

Two named missing-dispatch assertions failed before implementation. Five new
focused regressions cover frozen parameters/assembly selection, refusal of
shortened or renamed scopes, replaced SDK/logger images, actual closed provider
settings and graph-preserving original lock preparation. Runtime-input
recomputation also rejects changes to the added wrapper SDK image. All 248
tooling tests pass locally (237 passes, eleven native macOS skips), with frozen
inventory/catalog and patch-integrity checks passing. Native run
[40101331484](https://github.com/Stonefly-Labs/Hoard/actions/runs/40101331484)
at `8065dfc` verified all three jobs: 141 foundation checks without failures,
errors or skips, all 52 scopes/384 exact discoveries and executions (including
63 frozen original identities per provider), actual native containment and
identical eighteen-package/thirteen-lock replay. These remain harness
diagnostics, not complete binding/session origins, safe legacy metadata imports,
inherited recovery or category/profile qualification. Production architecture,
ADRs, diagrams and deployment examples remain unaffected.

### Partial artifact publication extraction

Five original two-provider publication wrappers now delegate to
`ArtifactPublicationAssertions`, which depends only on `IArtifactStore` and
preserves their existing assertion bodies. The actual staging-boundary wrapper
remains original-owned. Shared publish/read helpers and `ShortSource` keep their
existing wrapper signatures; the latter derives from the same SDK short-read
implementation used by common consumers, rather than maintaining a second copy.
SDK dependencies and production reference edges are unchanged.

Two named missing-consumer assertions failed before extraction. The repaired
paired regression decorates each actual Local/ObjectSemantics store, consuming
the first source but substituting its bytes for the next caller's source.
Two real stages/commits succeed; the unchanged shared consumer rejects the
unread duplicate at its EOF assertion. The undecorated store passes the same
consumer. No unsupported full-session hook or fabricated category binding is
introduced.

Fourteen publication/mutation tests pass. An initial unrestricted run observed
250 passes and seventeen setup failures because actual transfer proofs,
crash/noncooperative runners and cross-process admission prerequisites were not
prepared. The explicit non-external-proof selection then passes all 250 tests
without skips. Those seventeen obligations remain required, not waived.
Private non-qualifying preparation and independent empty-cache default locked
replay reproduce eleven archives and byte-verify ten actual wrapper dependency
DLLs plus the separate Application DLL. This is package/extraction evidence,
not a replacement for category acceptance or the unfinished legacy artifact
preparation/import upgrade. The latter still compares current metadata against
unchanged F-06 inputs and calls today's SDK-dependent recipe on an old SDK-free
tree; it must be split deliberately before full artifact acceptance.

The artifact package-only manifest/lock add only the SDK dependency; all old
entries and vendor pins are preserved. The metadata predecessor lock refreshes
only its SDK hash. Historical recipes, locks and retained binaries are unchanged.
README, provider guide and feature artifacts distinguish this bounded increment
from full qualification. Architecture/ADRs/diagrams/deployment examples remain
unaffected: only test consumers and package-only wrappers change.

The owned Linux diagnostic now builds that actual original artifact assembly
against its ten-package graph. Its exact scope contains all twelve frozen
publication parameters, including the original staging-boundary pair, plus
both actual-store duplicate-source mutation pairs. Both providers' parameters
share one exact scope so method-based selection cannot accidentally omit the
other parameter. Incomplete/renamed/foreign scopes reject before launch.
The safe logger is installed without a predecessor NuGet dependency; every
wrapper SDK/provider/Hosting/logger DLL must match its actual archive.
Original artifact runtime/dependency/native bytes enter pre/post immutable
inputs. The diagnostic feed grows from ten to thirteen archives; the separate
eighteen-package/thirteen-lock preparation graph is unchanged.

Two named missing-dispatch assertions first failed before wiring. All 250
tooling tests now pass locally (239 passes, eleven native macOS skips).
Existing image-replacement tests cover every dependency of both original
assemblies; lock tests preserve both original graphs, and recapture rejects a
changed artifact-wrapper SDK. Frozen inventory/catalog and patch checks pass.
The expanded native request is 53 scopes/398 observations, pending execution.
No recovery/transfer proof, full session origin, safe legacy import or category
qualification is inferred.

Three more original two-provider wrappers now forward to shared
`ArtifactReadAssertions`/`ArtifactDeletionAssertions`. These retain destination
failure/second-copy and borrowed-stream checks, exact delete receipts,
AlreadyAbsent behavior, recreation/ABA fencing, stale cleanup safety and
held-reader exclusion. The fixture still installs the actual reference
authority. The consumer's scoped reader releases exactly once before awaiting
deletion and on failed assertions; it neither leaks the guard nor double-disposes
it. No concrete provider or fixture-private fault type enters the SDK.

All 37 affected class tests pass, followed by all 250 non-external-proof
artifact tests and 89 original metadata tests per provider, without skips.
Fresh empty-cache default locked replay reproduces eleven archives and actual
dependency images; both predecessor locks refresh only their common SDK hash.
The new native scope independently selects all six frozen read/deletion
parameters and rejects shortened/renamed expectations. Its missing-dispatch
assertion first failed by name; all 251 tooling tests now pass locally
(240 passes, eleven native macOS skips), with formatting/catalog checks passing.
The expanded native request is 54 scopes/404 observations, pending Linux
execution. The seventeen external proof prerequisites, full bindings/origins,
safe legacy imports and category/profile gates remain unfinished.

Publication transport subsequently passed on Linux:
[40103524667](https://github.com/Stonefly-Labs/Hoard/actions/runs/40103524667)
at `dcb777e5a24665e569f029c1d359060319bfefcf` passed all three jobs,
143 foundation checks without failures/errors/skips, 53 scopes/398 exact
discoveries/executions (including original artifact publication/mutation),
native containment and identical eighteen-package/thirteen-lock replay.

`ArtifactEvidenceAssertions` now also shares exact receipt/protection validation
and permanent quarantine checks. Both inherited bodies mechanically match after
only dependency/helper/cancellation substitutions. Local durable reopen stays
fixture-owned and is not borrowed by ObjectSemantics. A real validator decorator
accepting the second, wrong-receipt request fails the common `Assert.IsType`
assertion on both providers after a genuine successful validation; the unchanged
validators pass the same consumer. The missing shared consumer and missing
native dispatch were observed failing first, not mistaken for behavioral proof.
Fresh eleven-archive locked replay passes 28 affected class tests, then all
252 non-external-proof artifact tests and 89 metadata tests per provider,
without skips. Both predecessor locks change only the SDK pin. All 252 tooling
tests pass locally (241 passes, eleven native macOS skips), along with format
and frozen catalog checks. The 23-identity native scope retains all original
evidence parameters, the relevant quarantine read parameters and the mutation
pair: 55 scopes/427 observations are requested, pending. Full category bindings,
origins, safe imports and seventeen external-proof obligations remain open.

Protected-read/deletion transport is now independently verified by native
[40104718986](https://github.com/Stonefly-Labs/Hoard/actions/runs/40104718986)
at `c979b6d0be855b9da9addc3513009edd704d6e73`: all three jobs passed,
144 foundation checks without failures/errors/skips, 54 scopes/404 exact
discoveries/executions, actual native containment and eighteen-package/
thirteen-lock replay. This verifies the six original read/deletion parameters,
not later evidence/controller changes or category completion.

The owning controller's opt-in `stop_at_barrier` path admits only a bounded
numeric target in recovery/event scope, with a fifteen-second ceiling. It
observes the safe event before verifying the actual child identity and issuing
owned pidfd group termination. A successful receipt requires that signal to
have been accepted, actual SIGKILL exit and complete group settlement; ordinary
exit, timeout, wrong/repeated barriers or any failure event cannot become a
barrier proof. The parent receipt adds the requested value and monotonic
observation/signal-request times, not child-declared pass booleans. Normal
command/recovery behavior and old receipt shapes are unchanged.
The missing API first failed its admission regression. All 256 tooling tests
pass locally (242 passes, fourteen native macOS skips); the three new Linux
process regressions remain pending native execution. This controller primitive
alone neither drives nor completes the inherited SQLite/Local crash matrices.
Native run `40105833001` at `0af7c98` exposed two assertions failing in the
wrong/repeated-barrier test: its child fixture emitted literal backslash-n bytes
instead of line-delimited events, so the controller correctly reached the
watchdog rather than the intended barrier rejection. The fixture now serializes
canonical events with actual newline framing. The native positive tree-exit and
normal-exit rejection cases did not fail; the corrected full gate remains
pending, not claimed green.

Exact evidence/quarantine transport also passed at native
[40105402168](https://github.com/Stonefly-Labs/Hoard/actions/runs/40105402168)
at `d7ef7cc3cdc20822c79b340a42e12eef0cbbe383`: all three jobs, 145 foundation
checks without failures/errors/skips, 55 scopes/427 exact observations including
the 23 original evidence/quarantine/mutation parameters, actual native
containment and eighteen-package/thirteen-lock replay. It does not verify the
subsequent owning-controller or recovery integration changes.

SQLite's actual CrashRunner now accepts `HOARD_CONFORMANCE_SAFE_EVENTS=1`.
It emits a closed completion event only after existing assertions, and a
closed numeric barrier event after the actual hold boundary/control write,
flushed before awaiting parent termination. Unset preserves exact legacy
output; unknown values reject before opening a store. No raw runtime/OS text
or provider-declared pass fields enter this mode.

The SDK diagnostic now builds that actual runner in locked mode, verifies its
six local dependency images and captures its complete runtime/native tree in
immutable pre/post inputs. It drives M0..M2, U0..U4 and R0/R1 with separate
seed/barrier/readback scopes plus the actual backup/restore walkthrough.
Normal exit, missing completion, missing/wrong/failed barrier or bad parent
receipt prevents the final diagnostic projection. The parent independently
checks exact receipt shape, target, sequence, PID/start hash, SIGKILL/group exit
and bounded monotonic observation/signal ordering. The record contains only
closed IDs and input/controller/readback hashes, not imported raw legacy logs.

Fresh independent locked preparation reproduces eleven archives; a separate
fresh-cache runner build verifies all six actual local DLLs. Actual
backup/restore walkthroughs pass with unchanged legacy output and the new safe
event; invalid mode rejects before store creation. All 258 tooling tests pass
locally (244 passes, fourteen native macOS skips), alongside format/catalog
checks. Controller unit doubles verify all 31 requested scopes and rejection
paths; these are not crash evidence. Subsequent Linux verification is below.
Live-held independent schema/
owner probes, safe legacy witness imports and full T026/category completion
remain open; no memory durability or Local crash proof is inferred.

The corrected native process gate passed at
[40107305423](https://github.com/Stonefly-Labs/Hoard/actions/runs/40107305423),
head `62c149c51b039724938e6547806626bdee8630f4`: 151 foundation tests, no
failures/errors/skips, including observed-barrier/tree-exit, rejected signal,
ordinary-exit and all correctly framed rejection cases. Its complete SQLite
recovery diagnostic subsequently passed: all ten actual seed/barrier/kill/
readback rows and the real backup/restore walkthrough, with 55 scopes/427 exact
observations, genuine native containment and identical eighteen-package/
thirteen-lock replay. All three jobs passed. The superseded failed `0af7c98` run was
canceled after recording its closed failure projection, never accepted.

Local's actual CrashRunner now supports the same explicit safe-event mode.
Unset preserves legacy output; unsupported values reject before store creation.
The controller builds it against its unchanged nine-package local graph,
verifies actual DLLs and captures the complete runtime tree before/after.
It drives B0..B3/D0..D1 crash/readback pairs with fresh run IDs, using the same
owned command, exact event and parent receipt admission as SQLite. Logical
receipt stability, staging-generation fencing, committed/control readback,
pending/reclaimed deletion, ABA safety and no duplicate effect remain asserted
by the original runner. ObjectSemantics borrows no durable rows.

Two fresh-cache locked builds reproduce identical runner DLLs and verify all
nine dependency images. A bounded macOS transport exercise observes the actual
barriers, kills only its own child and passes all six safe-mode readbacks, plus
an unchanged legacy B0 pair and invalid-mode rejection. This is functional
runner validation, explicitly not the Linux pidfd/group ownership proof.
All 259 tooling tests pass locally (245 passes, fourteen native macOS skips),
with formatting and frozen catalogs passing. The new Local controller test first
failed for missing dispatch; its unit double verifies all twelve requested
scopes and rejects changed runner bytes. Subsequent Linux verification is below;
safe legacy witness/session imports and full T032/category completion remain pending.
The real paced 256 MiB/4 GiB/RSS obligations are not replaced by these small
recovery payloads.

### Owned large-transfer measurement

The actual TransferRunner now has explicit safe-event mode. Unset preserves
legacy output; invalid values reject before store creation. Safe mode emits
one closed idle event after the original warmup/GC and waits for the parent's
literal transfer handshake. Actual generated non-seekable source and paced sink
still perform the original full stage/commit/read operation, checking all byte
counts, independent hashes, pacing and exact lengths. The bounded closed
producer proof is written only after those assertions. A second closed event
then holds the child for the parent's final observation and settlement handshake.

The owning command's opt-in mode admits only 256 MiB/4 GiB event transfers.
It validates the live PID/start identity for each bounded `/proc/PID/status`
read, observes kernel `VmRSS` after warmup and monotonic kernel `VmHWM`
throughout/before settlement, and enforces an inclusive 64 MiB incremental peak
ceiling. It does not substitute sampled RSS, GC counters or child-declared
memory for the OS high-water mark. Missing/repeated/reordered events, wrong
sizes, failure events, excessive memory, ordinary exit and missing settlement
cannot produce success. Warmup is bounded to fifteen seconds, settlement to
thirty and the complete transfer to forty minutes, under the existing profile
deadline. Existing commands/receipts are unchanged without this opt-in mode.

Parent receipts contain only bounded numeric measurements, monotonic times,
closed states and child identity hashes. Producer PID, current run, actual CLR,
all expected hashes, exact bytes, pacing and original buffer/slot limits must
match before a proof is admitted. Only the parent may supply RSS fields. The
existing transfer predicate is reused with an explicit `proc-status` method;
legacy validation retains its original default methods and capture rules.
The controller builds/byte-verifies the actual nine-package runner graph,
captures all runtime bytes before/after, runs four real rows serially and
emits only closed row IDs and controller/producer/proof hashes.

Missing admission/controller tests failed by name first. Focused mutations
reject changed PID/hash/runtime/pacing, unknown fields, missing completion and
unbounded memory. Native primitive tests are controller doubles, not transfer
proof. Two fresh-cache locked actual builds reproduce identical runner bytes
and nine dependency images; actual macOS execution passes all four safe
256 MiB/4 GiB read/write rows, an unchanged legacy 256 MiB row and invalid-mode
rejection. Every real row verifies actual hashes/pacing and independent
`getrusage` peak within 64 MiB of the observed idle RSS. This does not claim
Linux pidfd/group/kernel-status evidence; that execution remains pending.
Full original wrapper/session imports and T032/category completion remain open.
Production architecture, ADRs, diagrams and deployment examples are unaffected:
only test-runner transport and parent execution evidence change.
Final checks pass: `python3 -m unittest discover -s tests/tooling -q`
(266 discovered, 250 passes, sixteen native macOS skips),
`python3 scripts/conformance_case_catalog.py --check-sdk`, unchanged frozen
inventory, `dotnet format whitespace` for the runner and `git diff --check`.
The actual runner also acknowledges the literal settlement handshake before
normal exit; missing acknowledgement is not a completed parent measurement.

### Actual Local recovery and retained artifact work

Native
[40107826472](https://github.com/Stonefly-Labs/Hoard/actions/runs/40107826472)
at `e6d79f4ad5da3496f4c29038e55e16f64b8e7688` passed all three jobs,
152 foundation checks without failures/errors/skips, 55 scopes/427 exact
observations, all ten SQLite and all six actual Local observed-barrier kill/
readback rows plus the real backup/restore walkthrough, native containment
and unchanged eighteen-package/thirteen-lock replay. ObjectSemantics borrows
no durable recovery row. Native transfer-process regressions also passed 159
tests without failures/errors/skips at `d429dd2`; actual Linux large-transfer
execution remains running, not inferred from these controller tests.

The actual artifact noncooperative runner now supports explicit safe mode.
Default output is preserved; invalid mode rejects before store creation.
Original code still blocks actual source/destination/native workers, checks
borrowed streams, retained work/root ownership, blocked readiness/admission/
shutdown and appropriate read/delete protection. It repeats every inspection
after the parent's literal request while the same worker remains pending.
Bounded closed observation files precede numeric contained/inspected barriers.

The owning controller's opt-in inspection handshake requires distinct numeric
targets and the existing fifteen-second recovery stop limit. It checks the
live PID/start before sending the bounded literal request; the final observed
barrier then requires accepted owned SIGKILL and confirmed group exit.
Parent receipt admission checks the entire ordered observation/request/
observation/signal/exit chain. Missing, duplicate, reversed, foreign or failed
observations cannot qualify. This option leaves old barrier receipts unchanged.
Producer phase/run/PID/provider/scenario, all original retention flags and
allowed original failure codes must match both records before emitting hashes.
All six source/destination/native rows use actual Local/ObjectSemantics code;
the result explicitly says `durableCrashProof: false`.

Named missing admission/dispatch/handshake assertions failed first. Focused
mutations reject foreign children, mismatched second observations, changed
retention, missing parent request and wrong event chains. Shared receipt
admission now checks numeric bounds before float finiteness, so huge integers
produce `ProofMismatch`, not an escaping overflow; the regression failed first.
Two fresh-cache locked builds reproduce actual runner bytes and verify all nine
dependency images. Actual macOS execution passes both inspections and owned
termination for all six safe rows, an unchanged legacy source row and invalid
mode rejection. These are not Linux pidfd/group receipts.
All 272 tooling tests pass locally (255 passes, seventeen native macOS skips),
with compiled catalog, runner whitespace and patch integrity passing.
Subsequently, complete Linux run
[40109299238](https://github.com/Stonefly-Labs/Hoard/actions/runs/40109299238)
at `d429dd2` passed all four actual paced 256 MiB/4 GiB write/read rows with
parent kernel RSS/high-water and acknowledged settlement, not just controller
regressions. Run
[40110165383](https://github.com/Stonefly-Labs/Hoard/actions/runs/40110165383)
at `c7eb90c` then passed all six retained-worker inspection/termination rows,
165 foundation checks, 55 scopes/427 observations, all recovery/transfer
diagnostics and eighteen-package/thirteen-lock replay. All three jobs passed
in both runs.

The diagnostic now requests all seventeen original external-proof artifact
wrappers after their real prerequisites: sixteen frozen identities plus the
existing cross-process root-owner fact. Four new bounded child-output cases
bring this scope to 21. Actual captured runner bytes, current run ID,
parent-admitted transfer proofs and private per-attempt crash storage reach the
actual test host through closed settings; the legacy child protocol is preserved.
Child output and crash-state reads are bounded before return/copy; raw failure
stderr is never written as a recovery-error proof. Healthy empty legacy captures
remain. The original transfer predicate now also accepts actual kernel
`getrusage`/`proc-status` methods, retaining every byte/hash/pacing/RSS/buffer check
and rejecting an unmeasured `declared` method.
Two fresh-cache locked builds pass all 21 actual cases without skips and verify
ten dependency images. The first byte replay exposed an unmapped generated
test-SDK source path in portable debug metadata; normalizing both source and
cache debug paths in the private recipe reproduces identical test assembly bytes.
`python3 -m unittest discover -s tests/tooling -q` passes 274 tests
(257 passes, seventeen native macOS skips); compiled/frozen catalog, accepted
package-mode whitespace and patch integrity checks pass.
Current artifact package preparation now builds current metadata plus the SDK,
not pre-F-06 source through today's SDK-dependent recipe. Historical source/
binary seals and strict legacy comparison helpers remain unchanged and are not
replaced by current preparation. A real initial default build exposed NU1403
from stale local fixture package hashes. Both current preparers now reuse
explicit non-qualifying local archive derivation: default execution stays locked,
only private alternate local hashes change, original/tracked locks and external
dependency versions/hashes/edges remain unchanged. Package-acceptance locks have
a distinct alternate path; relabeling them as ordinary locks or vice versa is
rejected. Records verify original/prepared locks and actual feed bytes.
Two independent fresh-cache locked preparations reproduce all eleven artifact
archives and ten loaded dependency images. Both pass all 273 artifact cases and
89 metadata cases on each provider without skips. Actual previously measured
transfer packets are consumed unchanged; this is not fresh transfer/session
attribution. Metadata/artifact preparation retains four/five verified lock
derivations, including one package-acceptance lock each. All 276 tooling tests
pass (259 passes/seventeen native macOS skips), with compiled/frozen catalogs
and patch integrity passing.
The expanded Linux request subsequently passed at
[40111391053](https://github.com/Stonefly-Labs/Hoard/actions/runs/40111391053),
head `4e3ef47`: all three jobs, 167 foundation checks without failures/errors/
skips, 56 scopes/448 exact observations and all 21 external/capture identities,
plus actual recovery/transfer/retention prerequisites and identical eighteen-
package/thirteen-lock replay. Full original wrapper/session imports, all
authority combinations and complete category/profile acceptance
remain pending. Product architecture/ADRs/diagrams and deployment examples
remain unaffected by this test-only transport and parent evidence work.

The next extraction moves all three original publication race bodies behind
provider-free common consumers and leaves actual observers/payload mutation
fixture-side. All six frozen parameters, EOF/receipt/stamp/outcome assertions,
concurrent admission ordering, invalid-length rejection and permanent quarantine
remain intact. Mechanical body comparison passes after explicit seam/helper/
token forwarding. Actual missing consumers first failed compilation with CS0117.
A real-store forged-length adapter fails the named unchanged consumer on both
providers; commit/repaired-claim counters prove the intended mutation. Fresh
genuine stores pass unchanged. A missing exact owned scope failed first; its
six frozen identities plus two mutation rows now expand the pending Linux
request to 57 scopes/456 observations. This is still partial extraction/
diagnostic work, not complete category or profile evidence.
Two actual independent fresh-cache locked builds reproduce eleven archives
and ten loaded dependency images, each passing all 275 artifact cases plus
89 metadata cases per provider without skips. Accepted SDK/package-mode
whitespace, compiled/frozen catalogs, all 277 tooling tests (260 passes/seventeen
native macOS skips) and patch integrity pass. Source/tracked locks remain
unchanged; the newly built SDK is admitted through exact private derivation.
The preceding preparation checkpoint also passed native
[40112542005](https://github.com/Stonefly-Labs/Hoard/actions/runs/40112542005)
at `6de5933`: all three jobs, 168 foundation checks without failures/errors/
skips and the unchanged 56 scopes/448 observations, including all recovery/
transfer/retention/external-wrapper rows and eighteen-package/thirteen-lock
replay. Those Linux diagnostics do not substitute for full current-only recipe
or category/session acceptance.

The next artifact increment extracts private staging and all four original
reconciliation bodies. All ten frozen parameters and original assertion tokens/
ordering are preserved by mechanical comparison after explicit setup/seam/
helper/cancellation forwarding. Real prefix barriers, clock and authority setup,
and lost-acknowledgment observer registration remain fixture-side. A genuine
foreign-publication receipt fails the unchanged shared receipt-equality check
on both providers; counters prove one actual reconciliation and one foreign
publication, while fresh genuine providers pass. Missing shared methods first
failed actual compilation; a missing exact reconciliation scope failed its named
tooling regression. The requested native vector adds eight original rows and
two mutation parameters: 58 scopes/466 observations, pending. No complete
category/session/profile claim or task/checklist/stage advance follows.
Two fresh-cache locked builds reproduce eleven archives and verify ten loaded
dependency images; each passes 277 artifact cases and 89 metadata cases per
provider without skips. SDK/accepted-source formatting, compiled/frozen catalogs,
mechanical five-body comparison and all 278 tooling tests pass (261 passes/
seventeen native macOS skips). Earlier actual transfer packets remain unchanged,
not fresh session/category origins. Production APIs/edges/ADRs/diagrams and
deployment examples remain unaffected.

All three original direct/listing visibility bodies now execute shared
provider-free checks with actual fixture hold/release controls. Mechanical
comparison preserves their original checks and ordering. The premature-
acknowledgment negative starts an actual held Local commit, returns a genuine
earlier receipt immediately and fails the unchanged pending-task assertion.
It releases the real hold, awaits actual commit settlement and verifies the
distinct published stamp; the fresh genuine provider passes unchanged.
Missing shared consumers first failed actual compilation with CS0103, and a
missing exact visibility scope failed its named tooling regression. The next
native vector is 59 scopes/470 observations (three frozen visibility facts plus
the mutation added), pending. Complete category/session/profile work remains.

The preceding race request passed at
[40113497329](https://github.com/Stonefly-Labs/Hoard/actions/runs/40113497329),
head `91da8f4`: all three jobs, 169 foundation checks without failures/errors/
skips and 57 scopes/456 exact discoveries/executions. The eight new race rows,
all actual recovery/transfer/retention/external prerequisites, native containment
and eighteen-package/thirteen-lock replay passed strict closed admission.
Two fresh-cache locked visibility builds independently reproduce eleven
archives and verify ten loaded dependency images. Each passes 278 artifact cases
and 89 metadata cases per provider without skips. SDK/accepted-source formatting,
compiled/frozen catalogs, mechanical comparison and all 279 tooling tests pass
(262 passes/seventeen native macOS skips). Earlier actual transfer packets and
tracked locks remain unchanged; these are not fresh category/session origins.
Input: `d76fa0b400774c50f771b733de73a71bc9b0c4c6622097c896b06fff5fc7f664`;
preparation: `ab5517a180e177c516a886857cd9a79809af8c1757bd5b61d64dfe9e1555396b`.

Five original history/budget bodies now use shared consumers while actual clock,
limit/authority setup and candidate observer registration remain fixture-side.
Mechanical comparison preserves all original assertion tokens/order after
explicit seams/helpers/cancellation forwarding. Eight identities are frozen
category witnesses and eight are additional existing fixture cases, not newly
frozen entries. An initial scope-count regression caught that distinction;
the corrected eighteen-row scope preserves all sixteen original cases plus
two real-store hidden-candidate-failure mutations. The negative hides an actual
injected failure behind one genuine retry and fails the unchanged failure-type
assertion; actual candidate/reservation/failure/retry counters corroborate it.
Fresh genuine providers pass unchanged. The next requested native vector is
60 scopes/488 observations, pending; remaining budget/ownership and full
category/session/profile work is not claimed complete.

The preceding reconciliation request passed
[40114439905](https://github.com/Stonefly-Labs/Hoard/actions/runs/40114439905)
at `517b911`: all three jobs, 170 foundations without failures/errors/skips,
58 scopes/466 exact discoveries/executions, all ten new reconciliation rows,
and all actual recovery/transfer/retention/external/native prerequisites plus
eighteen-package/thirteen-lock replay. Input:
`d77ea438c9de9e604ce3432ad462e97943ba04598560e6fcbb37a382e4d8d4b8`;
preparation:
`9821ed48736ad565791cfeca5a571f0d93a77221616548dcc830af1d504f43a1`.
Two fresh-cache locked history builds independently reproduce eleven archives
and verify ten loaded dependency images. Each passes 280 artifact cases and
89 metadata cases per provider without skips. SDK/accepted-source formatting,
compiled/frozen catalogs, mechanical five-body comparison and all 280 tooling
tests pass (263 passes/seventeen native macOS skips). Earlier measured transfer
packets and tracked locks are unchanged, not fresh session/category origins.
Production contracts/edges/ADRs/diagrams and deployment examples are unaffected.

Four cooperative/noncooperative stream-ownership bodies now delegate to shared
consumers, preserving all eight frozen parameters and all three stream-helper
bodies by mechanical token/order comparison. Actual clock/settlement controls
remain fixture-side, and the legacy pending-source name forwards to the shared
implementation. A real-store mutation requires actual cancelled source work
with retained ownership before falsely reporting released cleanup; the unchanged
shared equality assertion fails on both providers. The actual release and
settlement complete, and fresh genuine providers pass unchanged. Missing
consumers first failed actual compilation with CS0103; the missing exact scope
failed its named regression. The next ten-row native scope requests
61 scopes/498 observations, pending, not category or full binding/session proof.

The visibility request passed
[40115175363](https://github.com/Stonefly-Labs/Hoard/actions/runs/40115175363)
at `793ad65`: all three jobs, 171 foundations without failures/errors/skips,
59 scopes/470 exact discoveries/executions, all four new visibility rows and
all actual recovery/transfer/retention/external/native prerequisites plus
eighteen-package/thirteen-lock replay. Input:
`d4db9e7fe5f3788b99f5a2a8fd5f6c1e708f18639894afd71c3c8edf5dc949fd`;
preparation:
`ea2609497216261e1c752d4376603f80f60c64f267ffdbdb711309c42ca8688a`.

Three original cancellation/current-owner bodies now use shared checks with
all ten existing parameters intact: two frozen category witnesses and eight
additional fixture identities. Mechanical comparison preserves exact original
assertion tokens/order after explicit clock/observer/boundary/settlement seams.
A real-store mutation waits for actual rejected-work settlement, then abandons
the current verified owner; the unchanged pending-state assertion fails on
both providers, while genuine stores pass unchanged. The first mutation tried
abandonment after logical return but before physical settlement, so its setup
guard failed under whole-suite concurrency despite focused success. Waiting on
the actual fixture settlement fixed that race without sleeps, weakened guards
or relaxed expected exceptions. The next twelve-row scope requests
62 scopes/510 observations, pending. Remaining budget/ownership and complete
binding/session/category/profile work stays unfinished.

The history request passed
[40116055015](https://github.com/Stonefly-Labs/Hoard/actions/runs/40116055015)
at `37ec19a`: all three jobs, 172 foundations without failures/errors/skips,
60 scopes/488 exact discoveries/executions, all eighteen history rows and every
actual recovery/transfer/retention/external/native prerequisite plus eighteen-
package/thirteen-lock replay. Input:
`4e103311ace86f8845a03cd53ac86133ccd912051d6b794b9c7caea7ecdd985b`;
preparation:
`d5169e04bb38147d9de543490952e264146aa6f6955c5798b85180766b199f8f`.

Four original result-handoff/expiry bodies now execute shared consumers with
twelve frozen parameters and exact assertion tokens/order preserved. Actual
completion/release observers, holds, entry, removal/release, clocks and worker
settlement remain fixture-side. A real-store negative hides a genuine reserved
ticket after cancellation; the unchanged success assertion fails on both
providers. Publishing that same actual ticket corroborates retained ownership;
fresh genuine stores pass unchanged. The next fourteen-row native scope requests
63 scopes/524 observations, pending, not complete category/session/profile proof.

The stream-ownership request passed
[40116943400](https://github.com/Stonefly-Labs/Hoard/actions/runs/40116943400)
at `5974f38`: all three jobs, 173 foundations without failures/errors/skips,
61 scopes/498 exact discoveries/executions, all ten ownership rows and every
actual recovery/transfer/retention/external/native prerequisite plus eighteen-
package/thirteen-lock replay. Input:
`6fad4115ca745592821a96dae8607e8171065480706f50f5f68ef777f78ef61f`;
preparation:
`405328324fd3fbb4f5c6d06017f0475b31387e56edc18c015abdf0bcf989cc90`.

The six remaining original budget bodies now run shared consumers with sixteen
frozen parameters and unchanged assertion tokens/order. They cover failed
unclaimed-result cleanup/retry, terminal cancelled publication, full transfer
queue, cap crossing, authority contention and cooperative cancellation.
Actual completion/reclaim/queue observers, boundaries, real settlement/stop,
limits and authority creation remain fixture-side. Shared authority checks take
only the Abstractions interface and actual identity. A genuine input-limit
failure deliberately mislabeled as capacity fails the unchanged expected-code
assertion on both providers; genuine stores pass unchanged. The next eighteen-
row native request is 64 scopes/542 observations, pending, not complete
category/session/profile proof.
Six original authority bodies now execute shared interface-only consumers,
preserving three frozen category witnesses plus three additional existing facts
and the exact copied-guard helper. Actual construction, clock, waiting/retained
counters, reference completion and drain stay fixture-side. A real authority
first rejects a copied handle, then a faulty adapter repairs it using the
original recognized handle. The unchanged failure-type assertion fails; actual
repaired retention is explicitly disposed and genuine authority passes unchanged.
The next seven-row native scope is 65 scopes/549 observations, pending.

Cancellation run `40118166329` at `631f9c4` passed all three jobs,
174 foundations without failures/errors/skips and 62 scopes/510 exact
discoveries/executions, all twelve cancellation rows and all actual prerequisite
chains/native containment plus eighteen-package/thirteen-lock replay. Input:
`3db30cc16c206a72a14d64b3d9f1bfecb3b9f9c772adec7959cb1947b99585c2`;
preparation:
`8a3b47f7297e523d12ae142b6da3d7ade1c43bd37552696087d4e1a076cbd420`.
Handoff-only run `40118782562` was canceled while pending, not accepted.
Later expanded requests include its full scope.

Both original capability bodies now run shared interface-only consumers,
preserving sixteen frozen missing-guarantee/version/authority parameters plus
two additional existing complete-profile cases. Actual capability injection,
provider construction, filesystem and readiness observation stay fixture-side.
Common checks preserve exact assertions/order for rejection before I/O,
readiness, configured limits, optional ranges, SHA-512 and stop/release.
The next eighteen-row native scope requests 66 scopes/567 observations, pending,
not complete category/session/profile proof.

Four original metadata/artifact integration bodies now execute shared checks
across every SQLite/Memory and Local/ObjectSemantics combination, preserving
sixteen frozen parameters, exact original assertions/order and helpers/data.
Actual composition, proof encoding, waiting counters, M1 hold/entry/release and
both stores' physical settlement remain fixture-side. Common checks retain
reference-versus-deletion ordering, failed transaction orphan visibility, actual
reference removal and stale-proof rejection, and lost-acknowledgment protection.
An actual reference denial deliberately mislabeled as conflict fails the
unchanged expected-code assertion in all four combinations, with exactly one
actual deletion and denial observed; genuine stores pass unchanged.
The twenty-row native request passed at `4c87667`, run `40121897879`,
all three jobs, 179 foundations and 67 scopes/587 observations, not complete
typed bindings, category/session imports or T033 acceptance.

Authority run `40120167356` at exact head
`7ee1c61a26fc9fb55473dcbc1c7890d2675ba579` passed all three jobs,
177 foundations without failures/errors/skips, 65 scopes/549 exact discoveries/
executions, all seven authority rows and every actual recovery/transfer/
retention/external/native prerequisite plus eighteen-package/thirteen-lock replay.
Input: `8bb1f75b731599fe38faefa2ef2ca84be4debc749f4b3a4cac566a7ae8fff303`;
preparation:
`126ca87d840a7576d8ac58b045ba3b14a1627d9ba7fb4542e76e2bca39724cf2`.

Three original metadata-bridge bodies now execute interface-only shared
consumers, preserving the frozen mismatched-authority witness plus two
additional existing facts. Actual host bridge/controlled-validator construction,
encoding, expiry injection and waiting/retained/call counters stay fixture-side.
The validator's exact recognized-reference operation/stamp assertions now call
the shared helper; its remaining real retention/decision logic is unchanged.
Original exact-evidence protection, invalid evidence and authority mismatch
checks preserve all assertion tokens/order. The bridge-only native request was
canceled while pending; its three rows are included in the expanded lifecycle
request, not separately accepted. These are host-bridge unit checks, not
complete four-provider binding/category/session proof.

Capability run `40120937967` at exact head
`2a7be14b5a32b2a11e28f582448977d89c346778` passed all three jobs,
178 foundations without failures/errors/skips, 66 scopes/567 exact discoveries/
executions, all eighteen capability rows and every actual recovery/transfer/
retention/external/native prerequisite plus eighteen-package/thirteen-lock replay.
Input: `fca6f8887233d4f1d32430c41520fdbf276c763dbd2f3b6b685f796e0950c649`;
preparation:
`9966fd10a5f0c49b1d2b026339153ec7a350030aa07972e2a91ae39762be4297`.

The three remaining original noncooperation/lifecycle bodies now use shared
interface-only consumers: composed shutdown with a retained reference query,
concurrent close with actual slow guard release, and deadline/stop with held
native I/O. Four parameters are frozen; two composed-shutdown cases are
additional existing facts. Actual composition, query completion/drain, slow
guard implementation, held native boundaries, physical release/removal and
settlement stay fixture-side. Shared checks retain original ownership, fencing,
deadline, retry and shutdown assertions, including the generic bounded-failure
helper. The next six-row request is 69 scopes/596 observations, pending, not
complete binding/session/category or full profile acceptance.

That lifecycle request passed `40123477371` at exact head
`f2cc84decfbd1b099f57e82b40d9636b65b8695e`: all three jobs,
181 foundations without failures/errors/skips and 69 scopes/596 exact
discoveries/executions, including all three bridge and six lifecycle rows.
Every actual prerequisite chain/native containment/eighteen-package/thirteen-
lock replay passed strict admission. Input:
`bf6e1a22dac1c6c3a58b55f70430e981eeffb67d443dc64dbba19cab031e1643`;
preparation:
`01f0cb2c3088be6ea79682ab8bb10d5359e703d40f31907f9ab1f43c50800bf9`.
This does not accept the canceled bridge-only run.

Two original storage-failure/reconciliation bodies now use shared consumers,
preserving four frozen parameters, fixed error classifications, exact failure
actions, borrowed-source handling, fixed sanitizer checks and committed-byte/
receipt retry checks. Actual post-visibility fault registration stays
fixture-side. A real access-denied staging failure relabeled as unavailable
fails the unchanged code assertion on each provider; actual stage/observed
denial counts each equal one and genuine stores pass unchanged. The next
six-row request is 70 scopes/602 observations, pending, not complete bindings/
category/session or full profiles. The original foundation harness remains
SDK-independent; its fixed sanitizer is preserved rather than introducing a
reverse dependency.

Four-way integration run `40121897879` at exact head
`4c876675728a7fa21b47942c816e065cafdeb140` passed all three jobs,
179 foundations without failures/errors/skips and 67 scopes/587 exact
discoveries/executions, including all twenty integration rows and every actual
prerequisite chain/native containment/eighteen-package/thirteen-lock replay.
Input: `a5869dfd419f2fcc869633479bc99c4524ad1affa9fec306c8496079583047ea`;
preparation:
`f15f9d1ec24f010e0e96d50e15ab3a1aa16c94a46e9bca929e5fca0596fb9c24`.

Three original prefix-cleanup bodies now use interface-only common checks with
all six frozen parameters, including the original post-stop Local reopen
assertions. Actual permission changes, observer registration/removal, readiness
and directory snapshots, stop implementation and Local-only durable reopen
remain fixture-side. Common checks preserve exact receipt/owner/cleanup/fencing
assertions and do not pretend ObjectSemantics has durable restart. The next
six-row native request is 71 scopes/608 observations, pending, not complete
bindings/category/session or full profile acceptance.

Both remaining original object-cleanup bodies now execute common checks with
five frozen parameters: reused selected-object receipt/cleanup and unselected
assembly ownership/retry/reclamation. Actual Unix permission changes, observers,
filesystem snapshots/lengths and physical worker settlement stay fixture-side.
The fixture translates its private progress/compare hook into the existing
logical during/after-assembly input; common checks own every fixed code, size,
owner and receipt expectation. Guarded physical restoration remains fixture-side,
without analyzer suppressions. The next five-row request is 72 scopes/613
observations, pending. Original failure-body extraction is complete, not full
T027/T030, binding/session/category or profile acceptance.

Storage-failure run `40124374635` at exact head
`ff50acda07e9bc8eb00277de2eb20140d2f39e5f` passed all three jobs,
182 foundations without failures/errors/skips and 70 scopes/602 exact
discoveries/executions, including all six failure/mutation rows and every
actual prerequisite chain/native containment/eighteen-package/thirteen-lock
replay. Input:
`af73ffddfa86f65c5855735147a1d7ad4da4bdb06e123601cd023587d26a7a7a`;
preparation:
`9a90d9553f8c410ccf50b6222ad4f5bb156cc1645412ac138d307449f27f8355`.

Configured publication, compatible reopen and fresh-epoch artifact operations
now execute interface-only shared consumers with fixed original content,
identity/epoch, exact receipt/ticket and protected-read expectations. Actual
host construction, DI selection, configuration evaluation, mapping, module
cardinality/identity/readiness, disabled-root observations, restart selection,
stop and missing-guarantee inert-start rejection remain in the hosting fixture.
No Hosting/Core dependency enters the SDK. All four frozen host cases remain
unchanged. Run `40127065375` at `9ce6b25` passed all three jobs,
185 foundations and 73 scopes/617 observations, not complete binding/session/
category or composition-profile acceptance.

The owned artifact adapter prerequisite now has an opt-in authority closing
fence. It synchronously rejects new acquisitions, preserves same-operation
retention, drains already queued admissions, and completes one stable task only
after all guards, waiters and real retained reference queries settle. Reopen is
rejected while live work remains and creates a fresh settlement generation.
Default authority behavior is unchanged until the fence is explicitly requested.

Architecture review rejected adding HostAdapters merely to reuse the authority:
Local/Object bindings instead source-link the existing authority with a binding-
only symbol making both authority/reference-decision types internal. Existing
HostAdapters public types remain public; there are no new package dependencies,
provider algorithm copies or SDK Core/Hosting references. This does not implement
complete category sessions or mandatory fault controls.

The missing lifecycle hooks first failed actual compilation with CS1061, and
missing exact transport failed its named tooling regression. Two independent
preparations each passed 298 artifacts and 89 metadata cases per provider with
no skips, reproducing eleven archives/ten loaded dependency images. Two separate
binding-package builds also reproduced both archives; runtime probes exercised
both actual private authority copies and rejected public type/dependency leakage.
Tooling passed 294 discovered / 277 passed / seventeen native macOS skips;
SDK, accepted-wrapper and authority whitespace plus frozen/compiled catalogs
passed. The three-row native request was 74 scopes/620 observations.
Run `40128473761` failed before authority discovery because its scope lacked the
original-artifact routing prefix; the repaired scope now reaches the correct
original artifact assembly. The failed run is never admitted.

Object-cleanup run `40126135553` at exact head
`3de87aadf19bc83da2a8dc229335a19630d77ae5` passed all three jobs,
184 foundations without failures/errors/skips and 72 scopes/613 exact
discoveries/executions, including all five new object-cleanup rows and every
actual prerequisite chain/native containment plus eighteen-package/thirteen-lock
replay. Input:
`b7b093f225913a2cf45192913ed1deafc54bd0d1e205fb008743a0e37f919bd0`;
preparation:
`a9a2e018a0f4f2f2b6cafcc64a998704fc65e03197d1df57fc09575e6c6aac18`.

The partial `LocalArtifactAssertionSessions` adapter now creates the actual
Local provider under an allocator-owned `store` child with typed scoped
observers and compatible identity/authority-preserving reopen. It joins real
provider stop, callback workers and fenced authority on one stable final task;
stale disposal cannot release a replacement. Disposal retries reuse pending
allocator observation, and observer failure remains faulted even if it occurred
before cleanup or while stop was waiting. No full binding/fault-driver support,
physical root deletion or `Released` observation is claimed.

Architecture review found that removing provider activities before the release
callback made idle/stop optimistic. Simply delaying that removal passed twelve
new Local cases but failed eight inherited handoff/cancellation cases. Separate
final-settlement tracking on Local/Object fixes both: original admission,
ticket-use, mutation and cancellation seams remain, while stop/idle join real
callbacks and final cleanup. All 300 artifact cases pass twice, and both
89-case metadata runs pass on each preparation. Fourteen final Local package-only
cases also pass, including real native allocator overlap rejection and failure
while stop awaits a callback. Fifteen independently built archives match exactly
with ten Consumer dependency image checks; tracked locks remain unchanged.
The recorded observation double is not native/category-origin proof.

Repository tooling passed 298 discovered / 281 passed / seventeen native macOS
skips. A first run honestly rejected insufficient real scratch capacity;
only inspected, completed private package caches were removed before rerunning,
without changing the 24 GiB gate or deleting evidence/images/source. Formatting,
frozen inventory, compiled catalogs and patch checks pass. Replacement native
execution requests 75 scopes/636 observations, pending. T027–T030 and full
category/profile gates remain open; the stage remains `implement / running`.

The next owned-Object design review identified missing genuine transition hooks
and an observer-capacity contradiction: seventeen typed Local points could not
all register under a sixteen-callback ceiling. Closed supported-name sets
already bound both fixture dictionaries, so every supported observer can now
coexist without admitting unknown names. A new Local case first failed with
fourteen existing cases passing; all fifteen now pass.

Object receipt/read/reconciliation callbacks now occur at distinct actual
transitions, not aliases of the earlier `object.direct` boundary. Receipt
notification follows actual recording, opened-read notification is inside
stream/guard/transfer reclamation, and reconciliation notification follows
actual content verification. Three provider-free consumers execute six actual
Local/Object rows. The single-slot callback-failure fixture supplies an explicit
successful zero-reference decision: its first deletion attempt correctly failed
under the default fail-closed authority, not because resources leaked.
All 306 artifact cases and both 89-case metadata choices pass without skips.
This prepared real controls without claiming a complete category fault driver.

Native run `40131392286` at exact head
`88c5d0182ad68dd65006e2ae3c86f3dce90a4525` passed 190 foundations without
failures/errors/skips and eighteen-package/thirteen-lock replay, but SDK
diagnostics failed pre-runtime with `ProofMismatch` after locked build replay.
No authority/Local discovery or passing receipt is admitted for that run.

Diagnostic inventory now hashes consumed managed/runtime formats, admitted-
architecture native assets and every lock, rather than all copied build assets.
The full-tree walk still rejects symlinks/special entries and identity races,
including excluded-architecture symlinks; source/lock/package seals and input
recomputation remain. Default full manifests and the existing 256 MiB/file/time
limits are unchanged. A sparse unconsumed build archive over the existing limit
reproduces the old rejection and now leaves selected inputs unchanged; an
oversized selected DLL still rejects. New phase markers separate actual SQLite
environment admission from runtime inventory capture so replacement failures
remain diagnosable. Native diagnosis is not claimed closed before replacement
execution. Tooling passes 299 discovered / 282 passed / seventeen macOS-native
skips. Replacement run `40133457888` at exact
`c58978ef016f53ab3fc8898b62b61b7bdd7d2631` passed all three jobs, 191 native
foundations without failures/errors/skips, independent eighteen-package/
thirteen-lock replay and strict 76-scope/643-observation admission, including
all fifteen Local and six observation rows plus actual prerequisite chains.
Input: `0e910492b63112b05c09277e70402c5c81fc6f1541a7cf938d8e3d3ee690b0e9`;
preparation:
`feef714d4c3428eda397c0440a8c7a63284ef8b1d4e285f1b33bdeb2e9b23439`.
This verifies the replacement, not the earlier failed run or full category/
profile acceptance.

The partial Object projection and shared internal artifact lifecycle coordinator
are now implemented. Local/Object packages source-link the same provider-free
owner/session code and existing internal authority algorithm, while keeping
actual construction and private controls independent. Compatible Local reopen
is unchanged. Object logical restart joins the old store/authority before
creating an empty private child with a fresh epoch/authority; it cannot recover
old content or borrow Local's durable behavior. Each session retains its original
identity/authority, and failed/unpublished generations remain tracked until
cleanup through the original handle.

The first fresh package preparation passed 306 artifact cases and both 89-case
metadata choices; its final package-only Consumer passed fifteen Local and
sixteen Object rows. Bounded architecture review found no confirmed defect and
identified two coverage gaps, now covered: actual direct-stop/disposal allocator
overlap and cancellation after replacement admission has begun. The latter
cancels through the actual admission clock after a new child exists, not a
timing delay. Provider/authority joins, failed observer tasks and pending
allocator observations retain their original ownership semantics. Formatting
passes for SDK, both bindings and Consumer; tooling passes 300 discovered /
283 passed / seventeen macOS-native skips. Independent fresh replay passes all
306 artifact, 31 Local/Object and 89+89 metadata cases without skips. Fifteen
archives reproduce exactly, canonical archive-map SHA-256
`727d42f8e1fdb9829e83e10f6a2d615a220f9fab425489b9892205c8cac51f99`;
ten Consumer runtime images match their archives. Previously measured transfer
packets remain reused unchanged, not fresh category/session origins.
Run `40133457888` verifies the preceding 76-scope vector. Owned-Object run
`40134767571` at exact `36481c058514a9d5dd22f13e51c5b629c1d8d656` passed all
three jobs, 192 foundations without failures/errors/skips, independent
eighteen-package/thirteen-lock replay and strict 77-scope/659-observation
admission, including all sixteen Object rows and every actual prerequisite.
Input: `f54fde15ced6fd40571bb85d43385c3a584bb4fe0dd9423539b8c41abd145526`;
preparation:
`9d7247e9ebc725519057d265ea8ac2c51bd3528558dc18b2c2c99981ab2b5ce1`.
These are diagnostic projections, not complete bindings, a 192/179/13 category
result or profile acceptance. T027–T030 and subsequent gates remain open.
Product architecture/ADR diagrams and custom-host examples are unaffected:
only test-private source composition and diagnostic consumers change.

Explicit typed artifact assertion setup now forwards actual limits and live
reference queries through both independent factories and all reopen generations.
The default overload remains fail-closed. SDK observations carry bounded typed
reference facts, not provider-selected expected results. Neither the existing
private authority algorithm nor any production API/package edge changes.
Seven initial configured cases passed; review identified missing post-reopen
limit enforcement and non-cooperative callback ownership coverage. The limit
is now actually rejected after reopen, and four further Local/Object cases
hold real reference queries after caller timeout through reopen/final cleanup.
The final package-only Consumer passes all 42 cases, with 306 artifact and
89+89 metadata cases passing in the first fresh preparation. Independent fresh
replay passes all 306 artifact, 42 Consumer and 89+89 metadata cases without
skips; fifteen archives match exactly, canonical map SHA-256
`2da3a01d231df7002b306c6208fb31f063fb963a86c7e97c7355592367314075`.
Ten Consumer dependency images match package bytes. The missing typed API first
produced the intended CS0246
compiler negative; missing exact transport failed its named regression with
two related lookup errors. Tooling passes 301 discovered / 284 passed /
seventeen macOS-native skips; SDK/binding/Consumer formatting, frozen inventory
and compiled catalogs pass.

Real local free capacity fell below the unchanged 24 GiB full-artifact gate.
Only 76 explicitly inspected completed-mode dependency caches were removed,
preserving sources, feeds, manifests, historical seals and actual runtime
images; measured free scratch then exceeded 28 GiB. No capacity guard, transfer
size or proof was relaxed. Run `40136186008` at exact
`853c669abb6554efaddc95a49d9fdf9a61f250ad` passed all three jobs,
193 foundations without failures/errors/skips and strict
78-scope/670-observation admission, including eleven configured rows and all
actual prerequisites/eighteen-package/thirteen-lock replay.
Input: `c4104825bfe5fc601fb7a053e04002be75dbbfcea90d8da81799a99b5eee2f9b`;
preparation:
`60b8884d1bb7f40c3689ee07d8a2dea553fc7b31f8cd759745a1e39c13dec77f`.

The next partial artifact control performs exact-stamp payload damage through
each independent provider's real worker supervisor. Native open/observer/
mutation/flush/disposal remain inside actual settlement; bindings only forward
typed requests. The new boundary holds a real read-write file handle and caller
cancellation cannot let reopen/final cleanup finish early. Physical changes do
not alter receipt or quarantine bookkeeping; public read/copy discovers damage.
The intended missing API first produced CS1061/CS0117. Exact transport first
failed its single named missing-factory assertion. Ten initial payload rows pass
with all 52 Consumer, 306 artifact and 89+89 metadata cases. Bounded architecture
review found no confirmed defect; the final 23 payload rows also cover failed
observers, real same-digest replacement, stale sessions/Object epochs, empty
content and incompatible open readers. Independent fresh locked replay passes
all 65 Consumer, 306 artifact and 89+89 metadata cases without skips; fifteen
archives reproduce exactly, canonical archive-map SHA-256
`a19809e0bcb89f0cb1269443063ad2681048b4015ad0dff6e8e800ea68268e4d`.
Ten dependency images match archive bytes. Full tooling passes 302 discovered /
285 passed / seventeen macOS-native skips; 76 SDK tooling checks, prepared
SDK/providers/bindings/Consumer whitespace, frozen inventory and catalogs pass.
Existing measured transfer packets are reused unchanged, not fresh origins.
The next request is 194 native foundations and 79 scopes/693 observations,
pending, not full category/profile acceptance. Production contracts,
architecture/ADR diagrams, custom-host examples, historical seals, tracked locks,
tasks and reviewer-owned checklists are unaffected by this test-private control.

The original damaged-read body now executes `ArtifactReadAssertions.DamagedReadAsync`.
All four frozen provider/truncation parameters, exact assertions and operation
order are mechanically identical after explicit interface/callback/helper/token
forwarding. Physical capture/damage/restoration stay at their original legacy
fixture boundaries, not inside the SDK and not falsely advertised as complete
owned fault-driver admission. Two real-validator mutations require one actual
corrupt-evidence denial before deliberately returning success; each fails the
unchanged common type assertion and a fresh genuine validator passes.

The missing shared method first produced the intended CS0117, independently
confirmed in the isolated compiler output. Exact transport first failed its
single named missing-factory assertion. Both fresh preparations pass all
308 artifact, 65 Consumer and 89+89 metadata cases without skips; fifteen
archives reproduce exactly, canonical archive-map SHA-256
`85e853c19f63153a3abb5a454bf24369b85a9f7678fed3b49a5ece6c141a398f`;
ten Consumer dependency images match package bytes. Initial full tooling
correctly rejected real scratch below 24 GiB (five failures/nineteen errors).
Only 55 explicitly inspected inactive dependency caches were removed across
completed preparations/wrappers; sources, feeds, manifests, historical seals,
intermediates and runtime images remain. After observing 25.188 GiB free, all
303 tooling checks pass (286 passed/seventeen macOS-native skips). SDK/wrapper
whitespace, all 77 SDK tooling checks, frozen inventory and catalogs pass.
Payload run `40137341231` at exact `1367a51` passed all three jobs,
194 foundations without failures/errors/skips and strict 79-scope/693-observation
admission, including all 23 payload rows, every actual prerequisite and
eighteen-package/thirteen-lock replay.
Input: `ad1b244e0b8c7715661fa905ac001b3c74307c910e5252820319dd7161af2a92`;
preparation:
`cfd9c8c52dee1e50978d3ed7660f077b40c0599259c6a49baee971d1a3a5d56a`.
Damaged-read run `40138438076` at exact
`4a907c5ec8b854198019b467c1069a2cdd33c00b` passed all three jobs,
195 foundations without failures/errors/skips and strict
80-scope/699-observation admission, including independent eighteen-package/
thirteen-lock replay and every actual prerequisite chain.
Input: `517a48389245ba621b1b0f5833d20c5b32cc4e041ccfba43ea2e9b1a5f4ccadf`;
preparation:
`beef2e645dafcc90515bbfa292afb3425cec4c95096e7eba63ca91237dd8c335`.
No full
category/profile result, new transfer origin or additional completed task is
claimed. Architecture/ADR diagrams and deployment/custom-host examples remain
unaffected by this assertion-only extraction.

Two more original bodies now execute provider-free read consumers: Local's
overlapping read/reconciliation quarantine race and both admitted-open
revalidation parameters. Mechanical body comparison preserves exact assertions
and public-operation order after explicit fixture/barrier/interface/token
forwarding. Named barriers are constructed/disposed in wrapper scope; their
actual observer installation, hold, restoration, release and every public
operation remain at the original logical transition. Actual observer mapping,
publication fault, physical payload changes and native settlement stay
fixture-side. No simulated durable recovery or provider-selected expectation
enters the SDK.

Both missing methods first produced CS0117, with each exact symbol confirmed
in isolated compiler output. Exact three-row transport first failed its named
missing-factory assertion. Two independent fresh preparations each pass
308 artifact, 65 Consumer and 89+89 metadata cases without skips; fifteen
archives reproduce exactly, canonical archive-map SHA-256
`40c0bb713c9d1499f8143d67da6812a1e3d1939593b634a9aa71fc76a2a339ae`.
Ten dependency images match archive bytes. All 304 tooling checks pass
(287 passed/seventeen macOS-native skips), including 78 SDK transport checks;
prepared SDK/wrapper whitespace, frozen inventory, catalogs and patch checks
pass. Previously measured transfer packets remain reused unchanged.
Read-race run `40139402208` at exact
`f05851abac1421518824782860e6db0ba24ab984` passed all three jobs,
196 foundations without failures/errors/skips and strict
81-scope/702-observation diagnostic admission, including independent
eighteen-package/thirteen-lock replay and all actual prerequisite chains.
Input: `303eeb1b8c696bc06d5e523e08b39947583e57237f420ba4d12b489e5b4b95fa`;
preparation:
`7ddb771f7d4e378bb8567796a12eb31f68b9f1008cd2aca463dfd85362a4bc29`.
Complete fault drivers, origins and category/integration/profile gates
remain unfinished. Tasks, reviewer markers, tracked locks, historical seals and
product/architecture/deployment examples remain unchanged.

All six original committed-detection parameters now execute
`ArtifactReadAssertions.CommittedDetectionQuarantineAsync`. Mechanical
whole-body comparison preserves exact assertions/public-operation order after
explicit fixture/interface/helper/token forwarding and the fixed inherited
durability variant. That expectation comes from the independent frozen test
parameter, never provider capabilities, a binding callback or a pass flag.
Physical removal/restoration and publication fault mapping stay fixture-side.
The old SDK first produced the intended missing-method `CS0117`; exact
six-row transport first failed its named missing-factory assertion.
Two independent fresh preparations each pass 308 artifact, 65 Consumer and
89+89 metadata cases without skips. Fifteen archives reproduce exactly,
canonical archive-map SHA-256
`2ae90bb74588acae39078dfb97f206b5f640d254d91179c4fa29caa786b2a591`;
ten Consumer dependency images match package bytes.
Full tooling initially failed because available scratch fell below the
unchanged 24 GiB admission gate. Removing only ten identity-verified inactive
dependency caches restored 24.140 GiB; sources, feeds, manifests, intermediates,
runtime images and historical seals were preserved. The rerun passes all
305 checks (288 passed/seventeen macOS-native skips), including 79 SDK checks.
Prepared SDK/wrapper whitespace, frozen inventory, catalogs and patch checks
pass. Committed-detection run `40140436330` at exact
`e08904228390c68f468739148ca05e39eac3542b` passed all three jobs,
197 foundations without failures/errors/skips and strict 82-scope/708-observation
diagnostic admission, including independent eighteen-package/thirteen-lock
replay and every actual prerequisite chain.
Input: `1a3c4f2f2d11f54ad715dd4ae58dfcb3ea92282b03ca017a473804377c398d0e`;
preparation:
`7bfbecaf99c2da8314713f14117b2cc9d340d0af417bb59d54c9fe29a6d823e7`.
This does not establish omitted durable checks or full qualification.
Tasks, reviewer markers, tracked locks and production/deployment documents
remain unchanged; measured transfer packets remain reused, not fresh origins.

Transitive-helper review found that the corrupt-existing, damaged-read and
committed-detection extractions had replaced the full original quarantine
helper with only its immediate common checks, omitting Local's durable
stop/reopen check. Earlier normalized-helper parity claims did not establish
that check; historical diagnostic receipts remain evidence only of the
assertions actually executed, not the omitted checks or full qualification.
The complete original helper now executes in common code, including every
stop/factory/initialize/corrupt-read/finally-stop/original-reinitialize operation.
`ArtifactQuarantineReopen` carries only public interfaces/identity/authority
and a fixture-only fresh-store factory; the fixed Local variant supplies it
and Object supplies none. Enclosing source, duplicate and guard lifetimes
remain intact; no callback supplies assertions or expected results.
Whole-helper comparison against `d7ef7cc^` is exactly equal after explicit
interface/factory/token forwarding. A frozen whitespace-normalized body and
per-wrapper owner guard now protect that transitive obligation.
Three actual reopened-store mutation pairs require real `CorruptContent`
denial before changing it to `NotFound`; all fail the unchanged common equality
assertion and pass with genuine stores. Their initial compilation produced
the intended missing-context `CS0246`; exact nine-row transport first failed
its named missing-factory assertion.
Fresh preparation/replay pass 311 artifact, 65 Consumer and 89+89 metadata cases
without skips; fifteen archives reproduce exactly, canonical archive-map
SHA-256 `9f08a15f5fd77ecffa4aaad4e5c05d6e333ba282e3ce1b23d5e606a67d593fb3`;
ten Consumer dependency images match package bytes.
All 307 tooling checks pass (290 passed/seventeen macOS-native skips), including
81 SDK checks; prepared formatting, frozen inventory, catalogs and patch checks
pass. Run `40141545447` at exact
`be3b3f2d5ed49f7a0d7a742f9b9b105ec6f7e2df` passed the ownership and fresh-lock
jobs but failed the SDK diagnostic with `UnknownDiagnostic` in the new
quarantine scope. It is not admitted. Actual `dotnet vstest --ListTests`
reproduced fifteen selected rows against its nine-row Local-only declaration:
method-level filters also discover all six Object parameters. Corrected
transport declares all twelve frozen provider parameters plus three mutation
rows. Prelaunch admission now rejects incomplete original-method expansion,
including a regressed canonical factory; the safe logger is unchanged.
Object's logical rows gain no durable-restart claim; fresh native confirmation
remains pending.
Tasks, reviewer markers, tracked locks, historical seals and production/
architecture/deployment examples remain unchanged; transfer origins are reused.

The remaining nine original evidence-validation parameters now execute
`FailedQuarantinePersistenceAsync`, `ValidationFirstCorruptionAsync` and
`ValidationAccessFailureAsync`. Entire-body comparison preserves exact
assertions, public-operation order and source/guard lifetimes after explicit
fixture/interface/helper/token forwarding. The complete transitive quarantine
helper remains protected, now including both newly extracted caller owners.
Physical path capture, permission changes, payload removal/restoration and
actual native readiness observation stay fixture-side; these legacy controls
do not establish full owned fault-driver admission. The original pre-try Unix
rejection remains at its transition; the permission setter repeats its local
platform guard so the analyzer's platform guarantee does not depend on another
callback.
All three missing methods first produced their exact intended `CS0117`;
nine-row transport first failed its named missing-factory assertion.
Fresh preparation/replay pass 311 artifact, 65 Consumer and 89+89 metadata cases
without skips. Fifteen archives reproduce exactly, canonical map SHA-256
`89efb47ca07de4de7e3d6e7d0b72f2dbd00efe580428865729ca24dc66d158c8`;
ten Consumer dependency images match package bytes.
All 308 tooling checks pass (291 passed/seventeen macOS-native skips), including
82 SDK checks; prepared formatting, frozen inventory, catalogs and patch checks
pass. Reopen parameters are no longer defaulted: every caller must explicitly
supply its real durable context or select logical-only scope. Final tooling
initially failed with five failures/nineteen errors below the unchanged
24 GiB gate. Cleanup removed only 69 exact identity-verified inactive
dependency caches, preserving every source, feed, manifest, intermediate,
runtime image and historical seal. Available scratch reached 24.248 GiB and
full tooling passed; after two additional completed caches were removed,
29.663 GiB was observed. Shared-host capacity changes are not attributed solely
to that cleanup. The newest request is 200 foundations and 84 scopes/732
observations, pending. Tasks, reviewer markers, tracked locks, historical seals and product/
architecture/deployment examples remain unchanged; full bindings, origins and
category/integration/profile acceptance remain unfinished.

Six original recovery methods now execute provider-free `ArtifactRecoveryAssertions`
for all twelve Local/Object parameters (eight frozen category witnesses and
four additional existing cases). Complete-body comparison retains
32 independent scans over 35 identities, consumed/query-bound/expired cursor
rejection, changed inventory, ownerless expiry, finalized noncommit, staging
generation fencing and recovery observation without deletion authority.
Fixed original variants retain Snapshot versus Incomplete consistency without
trusting advertised capabilities. Driver/clock/disposal stay fixture-side;
transitive publication/read helpers and source implementation are unchanged.
All six forwards first fail with intended missing-class `CS0103`; the exact
twelve-row scope first fails its missing-factory assertion. Omitted/foreign
parameters and renamed scopes reject before launch. Actual prepared-assembly
method-level discovery matches all twelve declared identities. All 309 tooling
checks pass (292 passed/seventeen macOS-native skips), including 83 SDK checks;
prepared SDK/wrapper formatting, frozen inventory, catalogs and patch checks
pass. Fresh preparation/replay passes 311 artifact, 65 Consumer and 89+89
metadata cases without skips; all fifteen archive digests reproduce exactly,
canonical full-filename map SHA-256
`1a547dfbe4ecb1e2bf1f1a10b3c60b5517b7b41a62e5cc40dcc91199eb8ad243`.
Ten actual Consumer dependency images match package bytes in each preparation;
transfer packets remain reused unchanged, not new origins. The expanded request is
201 foundations and 85 scopes/744 observations, pending, not qualification.
Remaining recovery faults/reopen controls, full bindings, origins and complete
category/profile acceptance are unfinished. Product/architecture/deployment
examples, tasks, reviewer markers, tracked locks and historical seals are
unaffected.

Run `40143552793` at exact head
`c1d2a6b4f40d5f2d5110bfe433619948292c90d1` passed all three jobs, 200 foundations
without failures/errors/skips and 84 scopes/732 exact discoveries/executions,
including the corrected fifteen-row quarantine-reopen scope and all nine
validation rows. The strict observer admitted actual prerequisite recovery,
transfers, ownership/native containment and eighteen-package/thirteen-lock
fresh replay. The prior failed run remains unadmitted. Input:
`c7fea35cc7c3e63d863e587a5dc9482fe9d066a86bddb9acb2a37b0be189fa02`;
preparation:
`19c50dc4dd12c6a62739c36308b20de4b5784040dc5b3497ca2d48820c258770`.
Free scratch was 91,722,289,152 bytes, not full qualification.

Five additional original recovery methods now use provider-free admitted-history,
generation-race and progressing-commit assertions over ten parameters (six
frozen witnesses and four additional existing cases). Full-body comparison
preserves all original assertions, operation order, source/barrier nesting and
read/receipt corroboration after explicit interface/control/clock/helper/token
forwarding. The SDK owns the unchanged original managed barrier, including
10/20/10-second entry/hold/settlement budgets, with a complete-body guard.
Physical registration/removal and lost acknowledgments remain fixture-side.
Ordinary compilation initially caught an SDK reference from putting the
legacy alias in the always-compiled harness; the alias now lives under
package-only `Cases/` without changing ordinary project references. Fresh
package-only compilation then confirmed intended missing shared-barrier
`CS0234`; exact ten-row transport first failed its missing-factory assertion.
Actual prepared-assembly discovery matches all ten independently declared
identities. All 311 tooling checks pass (294 passed/seventeen macOS-native
skips), including 85 SDK checks; prepared SDK/wrapper/harness/alias formatting,
frozen inventory, catalogs and patch checks pass.
Fresh preparation/replay passes 311 artifact, 65 Consumer and 89+89 metadata
cases without skips. All fifteen actual archive digests reproduce exactly,
canonical full-filename map SHA-256
`6dfb8daba9d51a1febd6266820be21464adc295942db22657507804cba5cd75a`;
ten actual Consumer dependency images match package bytes in each preparation.
Transfer packets remain reused unchanged, not new origins.
Run `40145322908` at `9d19bd1` passed all three jobs, 203 foundations and
86 scopes/754 observations, not full recovery/fault-driver/category/profile
admission. Tasks, reviewer
markers, locks, historical seals and product/architecture/deployment examples
are unaffected.

Run `40144435943` at exact head
`ffec99af90689b61938b5e66cc8e0df64d291c44` passed all three jobs, 201 foundations
without failures/errors/skips and 85 scopes/744 exact discoveries/executions,
including all twelve new recovery rows and every actual prerequisite recovery/
transfer/ownership/native-containment/eighteen-package/thirteen-lock replay
chain. Input:
`1661a1db69757112fac7ed84cb1609420164d098ea6eb85a1c52ea41b5879985`;
preparation:
`984c234bb9ef59234094386ea64dd64fdb56dfbc41b6f237c933fa20a2de0c04`.
Free scratch was 91,717,603,328 bytes, not full qualification.

The three remaining original recovery bodies now share retained Object stop,
committed-decision rollback/reopen and durable-receipt staging release/reopen
consumers. One frozen witness and two additional existing Local facts retain
every original assertion, 105 retired incarnations, public read/receipt
corroboration, operation order and source/current/fresh-store lifetime after
explicit interface/control/clock/factory/token forwarding. Permissions,
directory snapshots, record-write registration, real Local construction and
root-cleanup authorization stay fixture-side; common checks determine actual
stop outcomes before fixture setter/getter cleanup observation.
Object gains no durable-reopen claim. All three absent methods first fail with
their intended `CS0117`; exact three-row transport first fails its missing
factory assertion. Full tooling passes 312 checks (295 passed/seventeen
macOS-native skips), including 86 SDK checks; prepared SDK/wrapper formatting,
frozen inventory, catalogs and patch checks pass. Actual prepared-assembly
discovery matches all three independently declared facts.
Fresh preparation/replay passes 311 artifact, 65 Consumer and 89+89 metadata
cases without skips; all fifteen actual archives reproduce exactly, canonical
full-filename map SHA-256
`61e01e8345fa09ef873567e1e3451af5aef9f83a1f814566318d782116f6e935`.
Ten actual Consumer dependency images match package bytes in each preparation;
transfer packets remain reused unchanged, not new origins.
Run `40146117625` at `994f9fb` passed all three jobs, 204 foundations and
87 scopes/757 observations. Original recovery-body extraction is complete, not T027
or full bindings/origins/category/profile acceptance. Tasks, reviewer markers,
locks, historical seals and product/architecture/deployment examples remain
unaffected.

The exact managed-barrier run head is
`9d19bd1119a821e85e81019b9d393d5bd19e2f7d`; all 203 foundation checks pass
without failures/errors/skips, with 86 scopes/754 exact discoveries/executions
and every prerequisite recovery/transfer/ownership/native-containment and
eighteen-package/thirteen-lock replay chain admitted. Input:
`109cc8ddc69a9b07d0032104e9f2ca7201a64492f1213816a20a6f93fd5e3a7d`;
preparation:
`d49f56e11cebbe844a9eff4a076db30dc5da3c7b8438d632144a04db1ca789bc`.
Free scratch was 91,716,227,072 bytes, not full qualification.

Six original admission methods now forward eleven exact identities (four frozen
witnesses and seven additional existing cases) to `ArtifactAdmissionAssertions`.
Complete-body comparison preserves every original assertion/order, managed
initialization hold/release, 100/20-millisecond deadlines and two-second waits,
actual exclusive admission, missing/foreign/corrupt-root non-reset, fixed
Local/Object reopen expectations, sentinel checks and outer symlink/root
lifetimes. Actual construction, preconstruction fault registration, authority,
manifest/sentinel I/O and cleanup authorization stay fixture-side.
Native concurrency and cross-process admission tests, complete child proof and
root cleanup helpers remain unchanged. The absent consumer class first causes
intended `CS0103`; the exact eleven-row scope first fails its missing-factory
assertion. Full tooling passes 313 checks (296 passed/seventeen macOS-native
skips), including 87 SDK checks. Actual prepared-assembly discovery matches
all eleven independently declared identities; formatting, frozen inventory,
catalogs and patch checks pass. Fresh preparation/replay passes 311 artifact,
65 Consumer and 89+89 metadata cases without skips; fifteen actual archives
reproduce exactly, canonical full-filename map SHA-256
`e9b04122b8c1012d0b7e8af1650eec2bd9f419a1568d1bdf3f99912192182213`.
Ten actual dependency images match package bytes per preparation; transfer
packets are reused unchanged, not new origins. Its native request
`40146850203` was canceled before any jobs ran and is not admitted; all eleven
identities remain in the latest expanded request. This is not complete
bindings/origins/category/profile acceptance. Tasks, reviewer markers, locks,
historical seals and product/architecture/deployment examples are unaffected.

Both remaining original deletion methods now forward all four frozen provider
parameters to `PendingReclamationAsync` and `LiveReferencesAsync`. Complete-body
comparison preserves every assertion/order and borrowed-source/public helper
lifetime: uncertain deletion, actual pending/reclaimed cleanup, exact receipt
continuity and idempotent retry, both reference denials, intact readback and
eventual authorized removal. Actual fault registration and reference controls
remain fixture-side. Missing methods first fail intended `CS0117`; the exact
four-row scope first fails its missing-factory assertion. Full tooling passes
314 checks (297 passed/seventeen macOS-native skips), including 88 SDK checks.
Prepared-assembly discovery matches all four frozen parameters; formatting,
frozen inventory, catalogs and patch checks pass. Fresh preparation/replay
passes 311 artifact, 65 Consumer and 89+89 metadata cases without skips;
fifteen actual archives reproduce exactly, canonical full-filename map SHA-256
`7f8df462bdb0b2fdf8c93cdd438edbf099eed2443154cf7cfc24564061227bdb`.
Ten actual dependency images match package bytes per preparation; transfer
packets remain reused unchanged, not new origins. All original deletion bodies
are now shared, not T027/T030 or full bindings/origins/category/profile
acceptance. Native run `40147381011` binds exact head
`992b4a5c43efe4057879ede6bc232903225e1f94`: all three jobs, 206 foundations
without failures/errors/skips and 89 scopes/772 exact discoveries/executions,
including all eleven admission identities and every actual prerequisite chain.
Input: `474ce5c8a63f3d2bd169d503a92713d0e911e04a1235a76fc7932eb2c5912926`;
preparation: `49b91dc028b3c3d510ce346751a803cd4c48da53e0659849c61c3cfc609bd135`;
free scratch 91,721,879,552 bytes. This is diagnostic, not full acceptance.
Tasks, reviewer markers, locks, historical seals and product/
architecture/deployment examples are unaffected.

Recovery-reopen native run `40146117625` binds exact head
`994f9fb8819b7ff363382c3ff66b6087d5e34002`: all three jobs, 204 foundations
without failures/errors/skips, 87 scopes/757 exact discoveries/executions and
every actual prerequisite recovery/transfer/ownership/native-containment and
eighteen-package/thirteen-lock replay chain pass. Input:
`b3ae300a176e670997e660d96364e71c2061bac336fb8a536efb9b93e7b0c491`;
preparation:
`6fc731b1195af2c5a1ee8f575aba556933327c7e915813c5bf178a801fe99b37`;
free scratch 91,717,259,264 bytes. This does not complete category qualification.

Preliminary adapter architecture review rejected using selection as a generic
direct-verification witness, because duplicates need not select a new pointer.
The new `DirectVerification` observation maps Local's optional `publish.direct`
immediately before its original new/duplicate direct checks and Object's existing
`object.direct`. Local's complete publication implementation is unchanged apart
from those two optional observations; provider mechanisms remain independent.
Four shared consumer rows hold actual publication before acknowledgment, then
join completion/worker settlement and check correct outcome, exact duplicate
incarnation, borrowed-source ownership and public bytes. They do not claim
independent readability while a verification/selection gate is held.
The absent common method first fails intended `CS0117`; the four-row scope first
fails its missing-factory regression. Full tooling passes 315 checks (298 passed/
seventeen macOS-native skips), including 89 SDK checks. Actual prepared-assembly
discovery matches all four declared parameters; formatting, frozen inventory,
catalogs and patch checks pass. Fresh preparation/replay passes 311 artifact,
69 Consumer and 89+89 metadata cases without skips; fifteen actual archives
reproduce exactly, canonical full-filename map SHA-256
`298788d00993d47090cc2c433bd176311704767e623e3bdc788fba7943b57474`.
Ten dependency images match package bytes per preparation; transfer packets
remain reused unchanged, not new origins. Native run `40148199370` binds exact
head `6d1f73bf1f58cc46f68c1102a22a6289be07f717`: all three jobs,
207 foundations without failures/errors/skips and 90 scopes/776 exact
discoveries/executions with all four direct-verification rows and every actual
prerequisite proof. Input:
`422b243a0f9e2f7eb89e140c2b9f4246b357bb9b279e4ba7e8d4b0c118e75bef`;
preparation: `444b482499b205b3759d11413638d0ba03d9df45595e378a5cf29a5f482badba`;
free scratch 91,721,908,224 bytes. This is diagnostic, not qualification.
Complete mandatory
fault drivers, origins, category/profile admission and final T081 remain open.
Tasks, reviewer markers, locks, historical seals and product/architecture/
deployment examples remain unaffected.

Scoped capacity injection now uses each provider's genuine post-write staging
prefix. The projection constructs its own ENOSPC-shaped exception; only that
registration's exact instance bypasses observer-failure recording, while public
provider classification/cleanup remain real. Ordinary exceptions with the same
HRESULT still fault the original stable final settlement task. No failures are
cleared and no store result is substituted. This is injected storage failure,
not actual disk exhaustion or complete mandatory fault-driver admission.

Four package-only rows prove repeated failure, full single-ticket staging
capacity restoration, exact reconciliation, borrowed-source ownership, a fresh
scope surviving stale disposal and real publication/readback after repair.
They also distinguish genuine successful final settlement from ordinary
observer-error poisoning with the exact original exception. The absent common
method first fails intended `CS0117`; the exact scope first fails its factory
regression. Actual prepared discovery matches all four identities.

Fresh preparations pass 311 artifact, 73 Consumer and 89+89 metadata cases;
both Consumer builds additionally pass the tightened single-ticket limit.
Fifteen actual archive bytes reproduce the canonical full-filename map SHA-256
`2a871fdf07934fae09154e259a523d244fa937b2199c05b2dd900c1641ae6992`;
ten runtime dependency images match archive bytes per preparation. Tooling
passes 316 checks (299 passed/seventeen macOS-native skips), including 90 SDK
checks; formatting, frozen inventory, catalogs and patch checks pass. The native
foundation selector locally observes 208 checks with zero failures/errors but
seventeen native skips, correctly returning `Incomplete`/`EvidenceIncomplete`;
Native run `40148998281` binds exact head
`53b14333b5f9d2f175627c89801cac218f72c14c`: all three jobs, 208 foundations
without failures/errors/skips and 91 scopes/780 exact discoveries/executions,
including all four capacity/ordinary-observer rows and every actual prerequisite.
Input: `82b2c9e0ee5a59a944cee386943a3123d8dabeaa9b142a6e6182fb9caa42a2ba`;
preparation: `0fe7ad5982183dc9e6753d78fe562040d0428438d8bbef21cf7739d6fe96c2f6`;
free scratch 91,721,900,032 bytes. This remains diagnostic, not qualification.
Transfer packets remain reused unchanged,
not fresh origins. T027..T030, full fault drivers/origins/category/profile
qualification and final T081 remain open; tasks, reviewer markers, tracked locks,
historical seals and product/architecture/deployment examples are unaffected.

Scoped unclaimed-result cleanup injection now targets each independent provider's
existing indexed reclaim seam. The actual result is indexed before injection and
removed only after genuine cleanup. Four common parameters hold real reservation/
read-open completion, cancel delivery, release and join actual workers, and require
one failed reclaim, fenced readiness/admission, failed stop with retained live
ownership and a second failed reclaim. Only scope removal permits the real stop
retry and genuine successful final settlement. The original borrowed source
outlives that cleanup; no failure queue or stable promise is reset. This seam does
not replace the original physical prefix/object permission-failure checks.

The absent common method first fails intended `CS0117`; the exact runtime scope
first fails its factory regression. Actual prepared discovery matches all four
parameters. Fresh preparation/replay passes 311 artifact, 77 Consumer and 89+89
metadata cases without skips; fifteen actual archives reproduce canonical
full-filename map SHA-256
`0f1c8ce1efd3893ba836768053303d17c09ec5fc1fcd7e42cf9be0689dccdcdc`;
ten runtime images match their package bytes per preparation. Tooling passes
317 checks (300 passed/seventeen macOS-native skips), including 91 SDK checks.
SDK/both adapter/Consumer formatting, frozen inventory, catalogs and patch checks
pass. Transfer packets remain reused unchanged, not fresh origins. The next
native run `40149692533` at exact head
`1acdeb0b777e31929e7f70bccdfe89a2dc598bbd` passed all three jobs,
209 foundations without failures/errors/skips and 92 scopes/784 exact
discoveries/executions, including every actual prerequisite. Input:
`b4b5a27b071937cd524f6d1c2a97fab1049b991a6d049db0801849a8a90dd6cf`;
preparation:
`a11e22af6fefffdb261a13df75e1d305e9ec565005cc331c2e42b521d8b42e4b`.
Full mandatory fault drivers/origins/category/profile qualification and final
T081 remain open; tasks, reviewer markers, tracked locks, historical seals and
product/architecture/deployment examples are unaffected.

Owned synchronous storage holds now map Local's existing record-write and
Object's existing delete callbacks. Reserve deletion before arming and configure
genuine available reference authority. The first actual package run correctly
failed both new rows because missing reference authority denies deletion before
entry; explicit available-zero authority fixes setup without relaxing the guard.
An early public return before boundary entry now fails immediately.

Both common parameters require retained deadline/uncertain caller failure,
pending actual workers, fenced readiness/admission, real authority exclusion
and failed retained stop while held. Explicit release must precede genuine
worker settlement and successful stop. Scope disposal is identity-checked,
task-stable and joins real workers; stale disposal cannot remove a replacement.
Ownership removes remaining controls only after stop/worker settlement. The
fifteen-second watchdog poisons final settlement on unexpected expiry. These
are controlled synchronous fixture boundaries, not stalled filesystem syscalls;
original cross-process native containment remains separate and mandatory.

The absent common method first fails intended `CS0117`; the exact runtime scope
first fails its factory regression. Actual prepared discovery matches both
parameters. Fresh preparation/replay passes 311 artifact, 79 Consumer and 89+89
metadata cases without skips. Fifteen actual archives reproduce canonical
full-filename map SHA-256
`bed443dfceb7b1526fe8340f1fa0771856e2416233f4e6372c191085cee6bdcf`;
ten runtime dependency images match package bytes per preparation. Tooling
passes 318 checks (301 passed/seventeen macOS-native skips), including 92 SDK
checks; SDK/both adapter/Consumer formatting, frozen inventory, catalogs and
patch checks pass. Transfer packets remain reused unchanged, not fresh origins.
Bounded custom architecture review found no actionable ownership/concurrency/
boundary bug; this is a control review, not final T081. The next native request
passed as run `40150871211` at exact head
`f68812e9e2d9f48ced1be13d16554b67c118129c`: all three jobs,
210 foundations without failures/errors/skips and 93 scopes/786 exact
discoveries/executions, including every actual prerequisite. Input:
`8d841ae64a58df3ad5b548c9c1c1cfa4d0147e08500a3a068c057db2eed9ee13`;
preparation:
`965ec29517b5fc9fa3a3ea2cf140f12b65ac57d91751d576e2b856eecfc777eb`.
Full mandatory
fault-driver/origin/category/profile qualification, tasks and reviewer markers
remain open. Tracked locks, historical seals and product/architecture/deployment
examples remain unaffected.

Full Local/Object factories now wrap their actual owned projections without
substituting store results or component identities. Their full driver connects
all ten mandatory controls: publication/direct/receipt/verified-generation gates,
exact-stamp physical damage, scoped capacity/indexed cleanup faults, real
synchronous fixture holds, and actual borrowed source/sink streams. Stream
entry and cancellation-insensitive work are real; only explicit release permits
actual provider settlement, after which the factory may dispose its caller-owned
streams. Damage rejects a foreign incarnation and targets the first of two
artifacts without altering the second. Expired-owner cleanup is an actual
maintenance precondition before replacement staging; no provider guard was relaxed.
Observed full-session reopen preserves Local publication/identity and restarts
Object simulation empty with a fresh epoch; stale controls reject.

The new consumers/factories first failed actual missing-member/type compilation.
The first execution exposed the missing expiry-cleanup precondition on both
providers. Bounded custom architecture review then found a release-lock deadlock:
native disposal joined all workers while preventing release of a held publication.
A new two-provider regression reproduced both failures. Release callers now share
an in-progress task published under the registry semaphore but join outside it.
Native settlement observation precedes stable scope disposal; failed observation
can retry without caching a failed disposal promise. Both regressions pass and
subsequent rearming succeeds. This is a prerequisite review, not final T081.

Actual prepared discovery matches all 24 new parameters, including ten controls
per provider, two observed reopens and two concurrent releases. Fresh preparation/
independent replay pass 311 artifact, 103 Consumer and 89+89 metadata cases without
skips; fifteen actual archives reproduce full-filename map SHA-256
`2068add411613f471e6bfefd14cabb609fba189354c9edeec4f2320269dd07bf`;
ten runtime dependency images match archive bytes per preparation. Tooling passes
319 checks (302 passed/seventeen macOS-native skips), including 93 SDK checks;
20 typed binding/origin unit cases pass after restoring missing test dependencies.
SDK/both adapter/Consumer formatting, frozen inventory/catalogs and patch checks
pass. Transfer packets remain reused unchanged, not fresh origins. The next native
run `40153251707` at `f73a55a530b887eb9db70d8924ce7f7921a45028` passed all
three jobs, 211 foundations and 94 scopes/810 exact discoveries/executions with
every prerequisite. Remaining
category parity, parent-origin ingestion, integrations, complete profiles and final
T081 remain unfinished. Tasks/reviewer markers, historical seals and tracked locks
are unchanged; production architecture, deployment examples and diagrams are
unaffected because this increment adds test-only factories/controls.
The runtime uses a separate cache from candidate construction. The full-binding
scope therefore supplies only the two admitted provider archive hashes through
fixed private runsettings variables, after rechecking actual archive bytes.
Factories do not read an assumed build cache or substitute assembly hashes for
package hashes; malformed, missing, foreign and absent-archive inputs reject.

The full-binding diagnostic now transports actual origins, not just captures
them inside the Consumer. All 24 rows use observed sessions and the controller's
required `HOARD_ORIGIN_RUN_ID`; ordinary rows emit one origin and both reopen
rows emit parent then child, yielding 26 origins. Independently constructed
archive-bound declarations preserve the SDK's exact serialized descriptor bytes.
Parent ingestion pins all eight roles to actual binding/provider runtime images
and their own packages, requires the exact per-row origin count and matching
binding, and retains existing runtime/identity/reopen-lineage checks. The logger
manifest explicitly includes all four component images alongside the Consumer;
missing admitted images reject before launch.

Fresh preparation/replay pass 311 artifact, 103 Consumer and 89+89 metadata cases.
Bounded in-memory observation of actual VSTest output proves exact 24-row discovery,
24 creates/two reopens and 208 actual role/image/archive matches using a separate
empty runtime cache; no raw output/TRX is retained. This is local non-qualifying
observation, not native parent acceptance. The fifteen-package map remains
`2068add411613f471e6bfefd14cabb609fba189354c9edeec4f2320269dd07bf`.
Tooling passes 320 checks (303 passed/seventeen macOS-native skips), including
94 SDK checks; Consumer formatting and frozen safeguards pass. The origin-enabled
native successor passed as run `40154183825` at exact head
`d1fd43d9abcbe1bdeb9e393d28d7aad345f9c054`: all three jobs, 212 foundations
without failures/errors/skips and 94 scopes/810 exact discoveries/executions with
every prerequisite, including actual artifact origin admission.
Other origin/profile imports, category parity/integrations and final
T081 remain unfinished. Tasks/reviewer markers, historical seals and tracked locks
are unchanged. Product/deployment examples and architecture diagrams are unaffected:
this increment only wires test provenance into the existing diagnostic boundary.

Six new metadata rows now run the unchanged shared capacity, writer-budget and
publication-protection consumers through observed Memory/SQLite sessions. Actual
controller run/case IDs and independent provider-archive declarations accompany
all six origins. Every role is pinned to its actual binding/provider runtime
image and respective archive; all four component images enter the safe logger
manifest, exact binding/count checks apply, and actual SQLite environment admission
still precedes launch. The existing settlement-aware SQLite test allocator is
reused, not a second physical-release implementation.

The missing origin mapping first failed its intended regression. Fresh preparation/
replay pass 311 artifact, 109 Consumer and 89+89 metadata cases. Bounded local
observation confirms exact six-row discovery and 36 actual metadata role/image/
archive matches with a separate empty runtime cache; the 24 artifact rows still
produce 26 origins/208 matches. The fifteen-package map is unchanged. Tooling
passes 322 checks (305 passed/seventeen macOS-native skips), including 96 SDK checks;
Consumer formatting, frozen safeguards and patch checks pass. The new native request
passed as run `40155045988` at `90341537c34772face78946f2bc294dd1ee6f8b0`:
all three jobs, 214 foundations without failures/errors/skips and
95 scopes/816 exact discoveries/executions with every prerequisite, not category qualification.
Other origin imports, metadata reopen attribution, complete profiles/integrations
and final T081 remain open; tasks/reviewer markers, locks and historical seals are
unchanged. Production/deployment examples and diagrams are unaffected.

The admitted earlier full-control receipt binds input
`7b14f67d94d2800d7b4bbba02b4f018d3409bb6920eab160371b05a2ac2ca6be`,
preparation `13c78f0aea8139bc54e5052cc6a49b035bc03d15fa3ea18205104750ac9ce11c`
and 91,716,939,776 free scratch bytes. It predates both origin increments and
must not be cited as their native acceptance.

Actual compatible metadata reopen now has a provider-free shared consumer.
It seeds and publicly reads a grouped registry/package snapshot, reopens the
actual session, requires fresh store/fault instances and the same authority/epoch,
disposes the stale session, corroborates exact public readback and rejects stale
fault arming. A failed assertion disposes the unreturned child; successful
handoff leaves final disposal with the caller. Memory reuses a closed logical
image, not crash persistence. Two new observed factory rows emit actual parent/
child origins; the parent now requires two origins for these exact witnesses.

The missing reopen inventory first failed its intended regression. An incidental
immutable-array/span compilation error was corrected before runtime validation.
Fresh preparation/replay pass 311 artifact, 111 Consumer and 89+89 metadata cases.
Eight exact metadata rows emit ten origins, eight creates/two reopens and
60 actual role/image/archive correspondences with independent runtime caches.
Fifteen archives reproduce full-filename map SHA-256
`f351b872a7a4c111fe1b1321c7a7955e2b82c5763be59c00eab3ecd69b28789c`;
ten dependency images match package bytes per preparation. Tooling passes
322 checks (305 passed/seventeen macOS-native skips), including 96 SDK checks;
SDK/Consumer formatting, frozen safeguards and patch checks pass. The expanded
native request passed as run `40155922560` at
`4548183b5e6907be94f3fe52393a729c16299d2d`: all three jobs,
214 foundations without failures/errors/skips and 95 scopes/818 exact discoveries/
executions with every prerequisite.
All 20 typed binding/origin SDK contract tests also pass.
Complete category/profile origin imports, remaining parity/integrations and
final T081 are still open; tasks/reviewer markers, historical seals and tracked
locks are unchanged. Production/deployment examples and diagrams are unaffected.

The admitted artifact-origin receipt binds input
`df4c59c2f1ea075c8b14de7db16bdecdfd6c540698f739210fbd22abc276279b`,
preparation `45e3cc6040d45061ca26d51bae4bba0adf9fc8139fc1a9f942662b5584288640`
and 91,721,523,200 free scratch bytes; it predates metadata-origin execution.
The admitted metadata-origin receipt binds input
`fc41f51c1091f64152f3d4c64b4ba0bf209c996f8fd4591e4b9649687ae8dac1`,
preparation `5b4f9f3b1438fa5910ba8c8770c66b6e216f366e677e2fe68ba0ed99570ded51`
and 91,716,923,392 free scratch bytes; it predates the reopen increment.

Twenty further actual metadata rows now execute unchanged shared entity/
relationship, final-graph, independent-candidate, faulted-atomic-candidate,
grouped-read and lease generation/fence/decision-expiry consumers through both
observed factories. All three expiry actions use the actual injected clock and
real boundary observers. The exact-scope regression first rejected the missing
rows. Common assertion bytes, frozen wrappers, independent store mechanisms,
locks, historical seals and reviewer markers are unchanged.

Fresh exclusive preparation and independent replay pass 311 artifact,
131 Consumer and 89+89 metadata cases without failures/skips. Fifteen archives
still reproduce map `f351b872a7a4c111fe1b1321c7a7955e2b82c5763be59c00eab3ecd69b28789c`.
Actual bounded output observation in an independent empty runtime cache discovers
all 28 metadata rows and verifies 30 genuine origins, 28 creates/two reopens and
180 actual role/image/archive correspondences. Tooling passes 322 checks
(305 passed/seventeen macOS-native skips), including 96 SDK checks; Consumer
formatting and patch checks pass. The next native request is 214 foundations
and 95 scopes/838 observations; it passed as run `40156840261` at
`2beff5414c948814599a0f7f20426028579adb33`, all three jobs,
214 foundations without failures/errors/skips and every prerequisite. These standalone metadata
checks are not shared artifact-authority integration or complete category/profile
qualification. Remaining imports/integrations and final T081 stay open;
production/deployment examples and architecture diagrams are unaffected.

Thirty further observed metadata rows now import unchanged canonical text,
registry/authorization isolation, reference replacement/metadata revision ABA/
telemetry rollback, create/revision races, reconciliation contention/I/O/
acknowledgment/contribution/corrupt-receipt consumers and both malformed-schema
layouts. Layout assertions start genuinely unprepared. The exact-scope regression
first rejected the missing rows. No common assertion, provider mechanism, frozen
wrapper, lock, historical seal, task or reviewer marker changes.

Fresh preparation/replay pass 311 artifact, 161 Consumer and 89+89 metadata
cases without failures/skips, preserving the same fifteen-archive map.
Independent fresh-cache actual-output observation verifies all 58 rows,
60 actual origins, 58 creates/two reopens and 360 actual role/image/archive
correspondences. Tooling passes 322 checks (305 passed/seventeen macOS-native
skips), including 96 SDK checks; Consumer formatting, frozen catalog/inventory
and patch checks pass. The next native request is 214 foundations and
95 scopes/868 observations; it passed as run `40157571215` at
`8fed4125a4457e21af84b33a5c1f9be80b4dca26`, all three jobs,
214 foundations without failures/errors/skips and every prerequisite. Standalone metadata reference
revision ABA is not artifact-incarnation or shared-authority qualification;
remaining category/profile imports, integrations and final T081 remain open.
Product/deployment examples and architecture diagrams are unaffected.

The admitted compatible-reopen run binds input
`6269c9ddadd831a7cdef59dfd7e8d2194bd767e316e7e8fb7d2272fc04886890`,
preparation `d6b7c46e8a76016e6290406375013dfbd2b2668ae1eddc859fba1a15d6a1f83d`
and 91,721,584,640 free scratch bytes. It predates these fifty further common rows.

Eight further observed schema rows now invoke unchanged upgrade,
invalid-upgrade, upgrade-exclusion and future/corrupt-schema consumers. A
transparent caller-side recorder forwards real operations/disposal, records actual
observed factory sessions and their genuine reopens, and disposes an unreturned
child on capture failure. It never appears as an origin factory/component.
Strict parent admission requires exact two/three/four-origin counts and matching
descriptors; focused admission checks reject missing/extra/foreign descriptor origins.
Common assertion bodies, enclosing disposal scopes and provider mechanisms stay
unchanged.

Fresh preparation/replay pass 311 artifact, 169 Consumer and 89+89 metadata
cases without failures/skips. All fifteen archives preserve the same map.
Actual bounded fresh-cache observation verifies 66 exact rows, 82 origins,
68 creates/14 reopens and 492 role/image/archive correspondences; the independent
artifact replay still verifies 24 rows/26 origins/208 correspondences.
Tooling passes 323 checks (306 passed/seventeen macOS-native skips), including
97 SDK checks; Consumer formatting, frozen catalog/inventory and patch checks pass.
The next native request is 215 foundations and 95 scopes/876 observations,
not yet admitted. Memory upgrades/reopen remain logical. Full category/profile
imports, complete recovery-profile admission, integrations and final T081 remain separate
unfinished work; historical seals, locks, tasks and reviewer markers are unchanged.
Product/deployment examples and diagrams are unaffected.

The admitted entity/atomicity/lease run binds input
`b964bc83022faac1ac7891361f8b89dddb97f97a03d760553f9b26ec8adfd432`,
preparation `5927c9a5161d6646c61102a0cb3f0442efa1da4c1009f66bba533aa4d6b00999`
and 91,721,551,872 free scratch bytes; it predates reference/schema increments.

Forty-two further observed rows now import unchanged bounds/scopes, page kinds/
request/result limits/datasets, ticket/lease clock rollback, cancellation/queue/
exception mapping, ledger/diagnostic, publication evidence/replay/orphan,
corrupt groups/pages and admission/budget/incomplete-cleanup/disposal consumers.
Admission/budget cases start unprepared. Store disposal stays inside the common
consumer while the enclosing session owns resources; origins are captured while
live and emitted only after assertions pass. Real held work is released and
joined before outer disposal, never declared Released because a timeout returned.

The missing inventory first fails its regression. Fresh preparation/replay pass
311 artifact, 211 Consumer and 89+89 metadata cases without failures/skips;
the same fifteen-archive map reproduces. Actual bounded fresh-cache observation
verifies all 108 rows, 124 origins, 110 creates/14 reopens and 744 actual
role/image/archive correspondences. Tooling passes 323 checks (306 passed/
seventeen macOS-native skips), including 97 SDK checks; Consumer formatting,
frozen catalog/inventory and patch checks pass. The next native request is
215 foundations and 95 scopes/918 observations, not yet admitted. Common
assertions, provider mechanisms, historical seals, locks, tasks and reviewer
markers are unchanged. Complete category/profile imports, integrations and
final T081 remain open; product/deployment examples and diagrams are unaffected.

The admitted reference/reconciliation run binds input
`1fd6680fdc710f2753985b0b24f7c7a6f1351ec1b47d15a5f1527534035b70cc`,
preparation `d5ee7e5f0d0c4e43c46b95cb7861df4d08f1ccd55f82d6da2ec13bbdd29a2fe3`
and 91,721,572,352 free scratch bytes; it predates schema/control increments.

Twenty-four further actual rows exercise six continuation-corruption shapes,
each over all six components, five supported query-dimension corruptions and
foreign-store epochs through unchanged common consumers. Epoch cases prepare
two independent actual stores and emit both actual create origins. The absent
inventory first fails its regression; strict parent admission requires every
new identity and its exact one/two-origin count.

Fresh preparation/replay pass 311 artifact, 235 Consumer and 89+89 metadata
cases without failures/skips; the same fifteen-archive map reproduces. Actual
bounded fresh-cache observation verifies 132 rows, 150 genuine origins,
136 creates/14 reopens and 900 role/image/archive correspondences. Tooling
passes 323 checks (306 passed/seventeen macOS-native skips), including 97 SDK
checks; Consumer formatting, frozen inventory/catalog and patch checks pass.
The next native request is 215 foundations and 95 scopes/942 observations,
not yet admitted. Assertions, provider mechanisms, historical seals, locks,
tasks and reviewer markers remain unchanged. Complete category/profile
qualification, integrations and final T081 remain open; product/deployment
examples and diagrams are unaffected.

Schema run `40158238921` at exact head
`9399c3ca10bb59a474462a892ae326655ce819db` passed all three jobs,
215 foundations without failures/errors/skips, 95 scopes/876 exact
discoveries/executions and every prerequisite. Input:
`70cde04a349134675712f565458f275d9bd6cdce105ccf0c6ad9fd49de433cbd`;
preparation:
`a2f2fb64e77dc059b89e55d8e7bd5cd8e6df6a0743b3eb06fbb1fa5c4fe82167`;
free scratch 91,721,506,816 bytes. It predates controls/cursor imports.

The package-only Consumer now source-links
`tests/contracts/Hoard.Conformance.Tests/AuthorityIntegrationTests.cs`; the
ordinary SDK contract project excludes that file so it does not acquire a
concrete provider dependency. All four actual SQLite/Memory and Local/Object
compositions exercise eight consumers: reference admission, failed transaction,
actual live references, lost acknowledgment, incarnation ABA, protected reader,
foreign/copied authority handles and shutdown with a real recognized guard.
Existing common assertion bodies and original wrapper disposal are unchanged.

A separate stable qualification-close task fences new authority admissions,
captures genuine metadata lifetime/work settlement after disposal starts and
joins actual authority holdings and both disposals. The existing unit owner
receives that actual task and reclaims only after success; pending/faulted
settlement cannot mean Released. This remains unit/package diagnostic evidence,
not the final native controller/category ownership proof.

The new exact-scope regression first fails for absent scope. Initial package
restore then rejects the missing direct dependency graph with NU1004; the
Consumer lock is explicitly regenerated from the actual packed feed for its
new HostAdapters edge, existing versions and actual archive hashes. Historical
locks and preparation's no-graph-resolution rules remain unchanged. Fresh
preparation/replay pass 267 Consumer, 311 artifact and 89+89 metadata cases,
with fifteen matching archives and fourteen actual Hoard image/archive pairs.
An independent empty runtime cache confirms exactly 32 discoveries/passes.
Tooling passes 324 checks (307 passed/seventeen macOS-native skips), including
98 SDK checks; ordinary binding/catalog tests pass 23 without skips. Consumer
and HostAdapters formatting, frozen inventory/catalog and patch checks pass.
Bounded custom architecture review finds no confirmed blocker; its pending
runtime/lock-replay evidence gaps are addressed by these actual runs.

Controls native run `40158951602` at exact head
`3fb2705c1639e11e7c1ca730e769cffe92b131e5` passed all three jobs,
215 foundations without failures/errors/skips, 95 scopes/918 exact
discoveries/executions and every prerequisite. Input:
`5cc167d09eb4b693ea636094e623b6bf2b9bb45586e497016e42b8da2a091591`;
preparation:
`79a05caec7d7126f532473f579c6cc8d736f14c81bd33265665afecc8b99f59e`;
free scratch 91,721,510,912 bytes. It predates cursor/authority imports.
The new native request is 216 foundations and 96 scopes/974 observations, not
yet admitted. T033/category qualification, later profiles and final T081 remain
open; tasks, reviewer markers and historical seals are unchanged. README and
affected guides/contracts are updated; product/deployment examples and diagrams
are unaffected by this test-only package edge and additional close helper.

Category-mutation tests are source-linked into the package-only Consumer only
with `ConformanceCategoryMutations=true`; ordinary Consumer and SDK contract
builds exclude these intentional failures. The metadata decorator replays a
genuine successful commit after ticket expiry, and the artifact decorator
actually publishes staged bytes before returning them. Both faulty/corrected
pairs call the same private helpers and unchanged common SDK assertion bodies.
Unexpected successful reads in the faulty artifact case remain owned and are
disposed before the actual session, so leaked guards cannot mask the failure.

Fresh preparation and an independent fresh-cache locked replay each observe
exactly eight rows: four named SDK assertion failures and four corrected passes,
with fourteen actual Hoard images matching the unchanged archives. All rows
execute from one Consumer assembly per preparation; SDK/catalog/assertion bytes
are unchanged. Exact scope, provider-package hash, SQLite admission and named
assertion manifest regressions pass. Tooling passes 326 checks (309 passed/
seventeen macOS-native skips), including 100 SDK checks; opt-in Consumer
formatting, frozen inventory/catalog and patch checks pass. Scratch-capacity
failures are resolved by reclaiming completed private dependency caches, not
lowering the unchanged 24 GiB guard. The next native request is 218 foundations
and 100 scopes/982 observations, not yet admitted. T034/full category/controller
qualification and final T081 remain open. README and affected guides/contracts
are updated; product/deployment examples and diagrams are unaffected by these
isolated test-only decorators and opt-in callers.

An additional launch-boundary regression exposes the old full-family-only
runtime guard: all four intended mutation scopes initially reject with
`WitnessMissing`. The launcher now admits only exact full-family or same-family
paired inventories, still rejecting reduced, duplicate and cross-family rows.
The regression reaches a controlled command boundary and checks the generated
safe logger settings, exact method filter and independently hashed package
files, not merely the earlier mocked `test_attempt` handoff. Tooling again
passes 326 checks (309 passed/seventeen macOS-native skips); this is not a
native mutation receipt. Cancellation of obsolete pending run `40161267008`
was requested; its initial head is not admitted. The next exact-head request
retains 218 foundations and 100 scopes/982 observations.

Cursor native run `40159593512` at exact head
`5c7522fcff37fdb48e12e5ba7a1e9377b75414ac` passed all three jobs,
215 foundations without failures/errors/skips, 95 scopes/942 exact discoveries/
executions and every prerequisite. Input:
`b25a73b12c913e9dc52bb37f99e7f5715cfb95e8ac8f581d07c4907f18c669c5`;
preparation:
`8166e2e6cef3c6b3430721ba11d6f23ccea4d8ada689463e1d9721d4a88d6c1d`;
free scratch 91,721,383,936 bytes. It predates authority/mutation increments.

Category input sources may explicitly select `catalogBindingId` for the four
frozen slots. Parent capture checks the independently selected category,
existing fixture declaration ID and exact provider package identity before
projecting only `ProviderBinding.bindingId`. Raw declaration bytes/hash,
capabilities, adapter and archive attribution remain unchanged. Without this
field the existing declaration identity is retained. One original declaration
ID cannot enter the profile twice, even with different JSON serialization or
projected/unprojected identities. These are capture-time
assignments, not new descriptor/report fields, provider-renaming APIs or
provider-selected exclusions.

The absent slot API, missing profile-source field and duplicate-descriptor
admission each first fail their focused regressions. A differently serialized
duplicate also failed before identity-based rejection replaced hash-only checks.
Full capture/recapture
checks prove changing the assignment or capabilities changes admitted inputs.
Actual bounded observation plus independent empty-cache replay each verify
four selected factory/reopen cases, eight genuine origins (four creates/four
reopens), 56 role/image/archive matches and fourteen unchanged runtime Hoard
images. Every emitted descriptor hash matches its original unmodified captured
declaration despite the projected outer slot ID. Tooling passes 327 checks
(310 passed/seventeen macOS-native skips); frozen inventory/catalog and patch
checks pass. No SDK/provider package, lock or common assertion changed.
Complete category runners/imports, applicability/evaluation and T035/T081
remain unfinished; admitted execution/verify/aggregate still reject explicitly.
README and affected guides/model/contracts are updated; product/deployment
examples and diagrams are unaffected by this test-only input projection.

Authority native run `40160483040` at exact head
`eeaa6bf261a87edbb4df2b5cedebfb633fdacc5e` passed all three jobs,
216 foundations without failures/errors/skips, 96 scopes/974 exact discoveries/
executions and every prerequisite. Input:
`66c397e9b6a3824d1c0770794185e079ca10db6fe5d346fdcdf41f0683721d94`;
preparation:
`ac34b453116593d113688cee1c89130f565b2ef9d930ce3a08b484f469c75809`;
free scratch 91,721,281,536 bytes. It predates mutations/slot input wiring.
The next request is 219 foundations and 100 scopes/982 observations, not yet
admitted or complete category/controller qualification.

Category batch ingestion now selects each binding's full frozen witness union,
not a caller-supplied reduced inventory. Independent catalog/package checks
require both category options. The parent fixes a shared witness's execution
context to its lexicographically first mapped case, then reuses its actual UUID
and proof hash for every owned obligation without rewriting proof bytes.
Append-only retries retain failed attempts; execution/session identities and
component consistency extend across batches. Results require every profile key,
including six metadata/seven artifact QC rows. Unobserved controller controls
stay incomplete, and exclusions have no invented attempts or runtime evidence.
`CategoryRuntimeHistory.begin(..., partitions=...)` can predeclare nonempty,
disjoint scopes covering exactly the complete frozen binding inventory.
`runtime_partitions(binding_id)` exposes copied immutable primary-case maps and
independent child attempt UUIDs for manifest construction. `finish_parts`
requires every declared scope, its exact attempt/sequence and unchanged proofs;
cross-scope execution/session/observation replay and component inconsistency
reject atomically. A failed batch appends a failed/incomplete attempt without
admitting successful earlier scopes; a fresh retry preserves that history.
Valid assertion failures retain their actual witnesses/proofs and affect their
mapped obligations, not unrelated passed cases. Existing single-scope callers
use the same admission path. Aggregate proof counts/bytes remain bounded.
This is an import/state-model increment: actual profile runners, lower-level
adapter wiring, controller evidence and independent evaluation remain unbuilt.
The initial three regressions exposed the absent importer. Three partition
regressions first failed at the missing API; a fourth covers assertion
attribution. Eleven category-focused cases now pass,
including malformed/reduced/overlapping plans, independent scope attempts,
cross-scope replay, atomic retries and assertion attribution. The earlier
single-scope diagnostic fixture supplies structurally valid synthetic origins
and rejects a cross-binding execution-ID replay without changing accepted
witnesses/proofs. It is not actual original-wrapper provenance. An immutable
identity-to-primary-case map is available before manifest construction and
reused during import. Full tooling passes
332 checks (315 passed/seventeen macOS-native skips) after reclaiming inspected
completed private dependency caches to restore transient headroom above the
unchanged 24 GiB guard.

Native repaired-launch run `40161613939` at `abfa812` failed with
`EvidenceIncomplete` in category mutations; it is not admitted. Actual local
safe-logger reproduction isolates its cause: genuine `Assert.IsType()` failures
at the intended SDK frames were classified `Unknown`. The closed prefix
allowlist now includes that assertion, without relaxing exact frame matching,
bounds, unknown-output handling or canary sanitization. Its intended regression
first fails only the new type-assertion row; all 46 logger tests then pass.
Actual unchanged Consumer/SDK images plus independent empty-cache replay each
observe all eight discoveries/executions: four named assertion failures and
four corrected passes through the real launch settings/logger. These are
bounded local logger diagnostics, not full category input/profile evidence.
Superseded run `40162771846 @c1f79b2` is confirmed canceled and not admitted.
Replacement run `40164176338` at exact head
`2ecda7f4ae7f96a0be64bbb838e07bdf07dc4873` passed all three jobs,
223 foundations without failures/errors/skips and the strict 100-scope/
982-discovery/execution vector, including every native prerequisite and all
four mutation scopes. Input:
`a9b4f33d0b3e6dde4ea577d856f0d7a54e113fe712daf5054b55bce4501b0e91`;
preparation:
`69a1b07eb8ac465a00fc829cb2d5bfdf7b13929f6500e371245f4e5ab2352af1`;
free scratch 91,719,884,800 bytes. It is admitted diagnostic evidence, not full
category qualification or verification of the later `90fd088` follow-up.
The subsequent autonomous-continuation instruction resolves the original-wrapper
proof-contract decision. A closed frozen-identity policy now selects actual
original-owner/interface observations or relevant loaded contracts for the first
MP-01/AS-01/value witnesses; full typed SDK origins remain mandatory elsewhere.
The original owner retains disposal/root cleanup and original clocks/assertion
order. A separate bounded `hoard-original-v1` channel feeds only the explicit
`originalObservations` field of private execution-proof revision 2; v1 remains
unchanged and public entities/reports stay v1. Histories preserve these immutable
observations and reject replay under fresh executions/attempts.

Actual first observation and independent fresh-cache locked wrapper replay each
pass six exact discoveries/executions, four original owners, two session-free
contract contexts and 26 actual role/image correspondences. SDK archive:
`a94e225acd4ef19a8d1b363f5c7eedf498bae9364fbc2838f917f17c595485e3`.
Both use minimal local logger inputs, not full qualifying RunInputs; no native,
complete wrapper or category qualification follows. Complete creation/reopen,
child/controller instrumentation and actual profile/evaluator wiring remain
unfinished.
Tooling passes 335 checks (318 passed/seventeen macOS-native skips); all
68 logger/typed-binding contract tests pass without skips. The new original
history replay regression rejects under a fresh execution/attempt while retaining
previously admitted proof bytes. Capacity-only failures were resolved by deleting
thirteen inspected completed private caches, preserving all retained images,
archives, source and receipts and the unchanged 24 GiB guard. Scoped custom
architecture review found no confirmed blocker for the first increment, not
complete qualification readiness.
The subsequent full-input diagnostic wiring selects five additional native
scopes/eight executions, including both frozen artifact value witnesses. A
separate fully captured input document projects frozen binding slots without
changing raw descriptor bytes or typed SDK binding inputs; both documents share
actual source/packages/runtime/invocation group and independently recompute
after execution. Primary-case selection is shared with category history, and
every new execution requires its original observation rather than successful
status or an unrelated typed session. Native admission remains pending.

The two dispatch/proof regressions first fail on the missing APIs, then pass.
Full tooling passes 337 checks (320 passed/seventeen macOS-native skips).
The default predecessor `ArtifactValueTests` passes all seven tests without
skips; actual package-only observation and independent fresh-cache replay pass
eight executions/28 role-image correspondences. Those local probes still use
minimal inputs, not full qualifying inputs. Eighteen more inspected completed
private caches were reclaimed after capacity-only failures, with the 24 GiB
guard and all source/archive/runtime/proof/receipt data preserved. This code
requests a future exact-head native vector of 105 scopes/990 observations and
all existing prerequisites; complete category/profile qualification remains open.
The next metadata expansion adds original MP-02/03/13/23..27/31 observations.
Each caller pins the same authority facade it actually passes to unchanged
common assertions; one shared non-owning helper captures only original
fixture/interfaces before their existing disposal. No extra factory/session,
clock or root is introduced. Exact source-owned case names come from
`CallerMemberName`, not provider outcomes. Actual local observation and
independent fresh-cache replay pass 26 executions/118 image correspondences
(twenty metadata owners, two artifact owners and four session-free contexts),
reproducing the same SDK archive. The expanded routing requirement first fails
on the old eight-execution scope. Tooling remains 337 checks passing
(320 passed/seventeen macOS-native skips); metadata source whitespace and frozen
inventory/SDK catalog checks pass. Local probes still use minimal inputs; the
new native requirement is 105 scopes/1,008 observations, not an admitted receipt.
README and affected model/contracts/guides are updated; production/deployment
examples and diagrams are unaffected. Tasks/reviewer markers remain unchanged.

All twelve frozen artifact publication parameters now observe their genuine
original owner/interfaces through one driver helper, including the actual
private lifetime. Assertions, barriers, clocks, construction and disposal stay
unchanged; AS-13 retains shared primary-case ownership. The expanded regression
first fails at 26 rather than 36 executions. Actual observation and independent
empty-cache locked replay each pass 36 exact executions, 32 original owners,
four session-free contexts and 188 image correspondences, reproducing SDK
`a94e225acd4ef19a8d1b363f5c7eedf498bae9364fbc2838f917f17c595485e3`.
Local probes still use minimal inputs. Native admission now requires
105 scopes/1,018 observations with every prerequisite, not qualification.
`python3 -m unittest discover -s tests/tooling -v` passes 337 checks
(320 passed/seventeen macOS-native skips); frozen inventory and SDK catalog
checks pass. Changed driver/publication-file whitespace verification passes.
The broader folder check found pre-existing whitespace at
`ArtifactEvidenceTests.cs:79..80`; that unrelated file is unchanged.

Original-provenance run
[40166560899](https://github.com/Stonefly-Labs/Hoard/actions/runs/40166560899)
binds exact head `8aaa36d745ad4dfe52776b818b668be244c96bc6`: all three jobs,
227 native foundations without failures/errors/skips and 100 scopes/982 exact
discoveries/executions, with all recovery/transfer/containment/replay
prerequisites. Input:
`759b9ef9d73c65723b5aff95515b6650831430f4433396f5c435ad8133b7e8ef`;
preparation:
`81450552403c843f0c8307063bdc17357ad2e96d3642a639ff1cfc5dc2b4dddf`.
This admitted diagnostic predates full-input original scopes; it does not
qualify the later changes or complete categories/profiles.

Original role images are now selected per exact witness inside each binding
and deeply frozen before execution in both histories. Flat, foreign-witness,
cross-binding and extra-role assignments cannot stand in for the selected
original. Forty-two single-owner metadata identities per provider now observe
the actual original authority or the same facade used by unchanged assertions;
no unused companion facade is manufactured. Parameterized, multi-owner and
reopen cases retain their strict existing admission.

The new immutability regression first fails on the old flat-map parser.
Expanded routing first fails at 36 instead of 100 executions, then passes.
Actual minimal-input observation and independent empty-cache locked replay
each pass 100 discoveries/executions, 96 original owners, four session-free
contexts and 508 role/image correspondences, with the unchanged SDK archive.
`python3 -m unittest discover -s tests/tooling -v` passes 338 checks
(321 passed/seventeen macOS-native skips); metadata source whitespace, frozen
inventory and SDK catalog checks pass. Bounded custom architecture review
finds no confirmed blocker; this is not final T081 or native admission.
The new native requirement is 230 foundations and 105 scopes/1,082 observations,
still pending. README and affected guides/model/contracts are updated;
production/deployment examples and diagrams are unaffected. No task/reviewer,
historical-seal, lock, public schema or running-stage marker changes.

Exact query-corruption and continuation parameters plus both directly
constructed admission witnesses now extend original metadata coverage to
55 identities per provider. The same source helper carries the actual `shape`
argument; the independent frozen catalog selects all parameter rows and their
genuine authority image. Assertions, construction and disposal are unchanged.
Parent ingestion now rejects additional roots for these one-observation
policies, not just the diagnostic post-check. The added extra-root regression
first fails because the old ingestion accepts it; expanded routing first fails
at 100 instead of 122 executions, before the two direct cases bring it to 126.
Actual local minimal-input observation and independent fresh-cache locked replay
each pass 126 discoveries/executions, 122 original owners, four contract
contexts and 638 image correspondences, reproducing the unchanged SDK archive.
Full tooling remains 338 checks passing (321 passed/seventeen macOS-native
skips); metadata whitespace and both frozen catalogs pass.
The expanded native requirement is 230 foundations and 105 scopes/1,108
observations, pending; broader multi-owner/reopen/controller paths remain work.

Full-input run
[40167209164](https://github.com/Stonefly-Labs/Hoard/actions/runs/40167209164)
binds exact head `0005638ac1b6a75f267d95332ebbb865b51ec436`: all three jobs,
229 foundations without failures/errors/skips and 105 scopes/990 exact
discoveries/executions, including eight original executions, plus every
recovery/transfer/containment/replay prerequisite pass. Typed input:
`824568e3af9b8df6bd2cc69dda0464875a1d6c009d9a25c66fef3865a1e8b39c`;
separate original input:
`743646e7c2a0094bf4e1df8c2d8700fba64e6ce899ee9ef57ba24d193049c8b9`;
preparation:
`3f7f3616d95db05ffe188f099dac364f7b1e6d28fc175605c95ee2583fd1fc19`.
Both inputs independently recompute. This admitted diagnostic receipt does
not qualify later expanded sources, category profiles or the unfinished stage.
README and affected guides/model/contracts reflect that distinction;
production/deployment examples and diagrams are unaffected.

Prefix-cleanup run `40125248164` at exact head
`871e3a860a07646c513de01095cc29ad3e4add70` passed all three jobs,
183 foundations without failures/errors/skips and 71 scopes/608 exact
discoveries/executions, including all six cleanup/stop/reopen rows and every
actual prerequisite chain/native containment/eighteen-package/thirteen-lock
replay. Input:
`43b6d2627018f373112f5c9fc9e905e204b6bc291b0ed528d77f755d2b9117e3`;
preparation:
`86efcad80e99ec07ca0f96bbc7dcba8b4ef98a237780a71c764e063839f4e0d1`.

The expanded budget request passed `40119412481` at exact head
`70dfdf63f59a13ba39d934a7ef09f148bfc58c57`: all three jobs, 176 foundations
without failures/errors/skips, 64 scopes/542 exact discoveries/executions, all
fourteen handoff and eighteen budget rows plus every actual recovery/transfer/
retention/external/native prerequisite and eighteen-package/thirteen-lock replay.
Input: `d5769b5f8fa45e080866fc154d65c9764ccb1d9e70cdd906af8811ff5b22f8cd`;
preparation:
`6916185a0c4940561f05c14fdf31883391b5f35e4992d35ac28b50e955b6730a`.
This admits handoff at `70dfdf6`, not the canceled handoff-only run.

Native prerequisite run
[40062534006](https://github.com/Stonefly-Labs/Hoard/actions/runs/40062534006)
at `a81c0380f6bed06d8870c6b43263aa480ae5d04b` passed all three jobs,
131 foundation checks without failures/errors/skips, earlier 37 scopes/
170 observations, six baselines and identical eighteen-package/thirteen-lock
replay. Input:
`12d9b6f9217f8bcd55f59657d41972652d746d71e44fb4fc6d55fb43a7c3a381`;
preparation proof:
`70790529869264a78361c61119a4184b4c900f9887490d46d6746fcee0574f23`.
Free scratch: 92,109,668,352 bytes. It predates the concrete SQLite binding
and seven-archive graph; no SQLite execution is attributed to it.

Seven further operational metadata witnesses now observe independently selected
creation/reopen forests, bringing coverage to 62 identities per provider.
Exact node counts/current-execution parent indices and distinct owner/store
identities are mandatory. Non-owning source sequences preserve actual aliases
across independent roots without inventing reopen edges. Schema observations
capture the actual adapter owner and underlying fixture authority; unchanged
assertions keep their existing facade behavior. Failed observation after real
reopen disposes the newly transferred fixture before rethrowing.

Actual minimal-input observation and independent empty-cache locked replay each
pass 140 discoveries/executions, 162 records (158 original owners/four contracts)
and 818 image correspondences. SDK archive reproduces as
`032389ce6626072e1d3b455d1af77779e6656f46f5cba1187df3dbdf591922c1`.
Tooling passes 339 checks (322 passed/seventeen explicit macOS-native skips);
SDK logger/binding tests pass 69 without skips. SDK/test-project formatting,
metadata-folder whitespace, frozen inventory and SDK catalog checks pass.
Bounded custom architecture review finds no confirmed blocker with explicit
read-only/diff-reproduction limits, not final T081. Native admission requires
231 foundations and 105 scopes/1,123 observations, pending.

Earlier witness-specific run
[40168790991](https://github.com/Stonefly-Labs/Hoard/actions/runs/40168790991)
at exact `3f1409a6705b43c8d1ba347396f03db6ab3497d2` passed all three jobs,
230 foundations without failures/errors/skips, 105 scopes/1,082 exact
discoveries/executions and every recovery/transfer/containment/replay prerequisite.
Typed input:
`55cfb28e9b89f2979276bb699f842cafada908ae341f4d2c64b6c96aff070312`;
separate original input:
`04433046300ac1cdc4ee0c7366c9c17f7e8aa3b154112af9e213c40d940624a4`;
preparation:
`81f24eea2c58cb12588e2c50f3cc9bc5ece9ce5fd3316473c93769c1ca00a72a`.
Both inputs independently recompute; free scratch is 91,721,125,888 bytes.
This admits the earlier diagnostic, not later forest sources or complete profiles.
Host/controller attribution, broader artifacts and qualifying backends remain
unfinished. README and affected guides/model/contracts reflect this distinction;
product/deployment examples and diagrams are unaffected.

The configured-host witness now observes both actual composed module owners
and their existing session interfaces after unchanged assertions, including
rejected schema admission. Its two independent roots use the existing
reference-continuity sequence; no new fixture, module or disposal is introduced.
Thirty-eight more original artifact parameters observe their genuine drivers
across deletion, reconciliation, read revalidation/destination failure,
publication races, storage failures and selected budget checks.

Coverage is 63 operational metadata identities per provider and 50 artifact
parameters. The missing host policy first fails `WitnessMissing`; missing
host/artifact routing first fails exact execution counts. Actual local
observation and independent empty-cache locked replay each pass 180
discoveries/executions, 204 records (200 original owners/four contracts) and
1,104 role/image correspondences. Host owner hashes match the actual
`MetadataFixtureModule` type. The SDK archive is unchanged from the forest
increment. These remain minimal-input diagnostics, not qualifying RunInputs.
Full tooling passes 339 checks (322 passed/seventeen explicit macOS-native
skips); changed metadata/artifact source whitespace, frozen inventory and SDK
catalog checks pass. Native admission requires 231 foundations and
105 scopes/1,163 observations, pending. Controllers, remaining artifact
lifetimes and qualifying backends remain unfinished. README and related
guides/model/contracts are updated; product/deployment examples and diagrams
are unaffected.

Forty-four further original artifact budget/recovery parameters now observe
their existing drivers, including all frozen boolean variants. Source argument
names/values are preserved. The expanded frozen inventory first fails exact
counting; actual parent dispatch then exposes a one-parameter-only provider
selector that misassigns Local boolean rows to Object. Explicit total provider
assignment fixes it without a fallback; the regression independently derives
binding identity from frozen cases.

Actual minimal-input observation and independent empty-cache locked replay
each pass 224 executions, 248 records (244 original owners/four contracts) and
1,412 role/image correspondences with the same SDK archive. Full tooling passes
339 checks (322 passed/seventeen explicit macOS-native skips); changed artifact
source whitespace, frozen inventory and SDK catalog checks pass. Four inspected
completed diagnostic dependency caches were reclaimed while preserving
source/archive/runtime/proof/receipt data and the unchanged 24 GiB guard.
Native admission requires 231 foundations and 105 scopes/1,207 observations,
pending. Controllers, remaining artifact lifetimes and qualifying backends remain
unfinished; public contracts, locks, task/reviewer markers and production/
deployment examples and diagrams are unchanged.

Earlier parameterized run
[40169478754](https://github.com/Stonefly-Labs/Hoard/actions/runs/40169478754)
at exact `ed235eeac3ec1e460fc449bc7aa4e9f4f765fc31` passed all three jobs,
230 foundations without failures/errors/skips, 105 scopes/1,108 exact
discoveries/executions and every recovery/transfer/containment/replay prerequisite.
Typed input:
`dc470af7df962339056aa5f0aa92b5ae3137655f3275c4ed265b753193e2e296`;
separate original input:
`fef2354d0ed33670ffb8a4a128851bea09dd7c3b3ab3c4d138491c9025ba8b01`;
preparation:
`54b224c34992d3c9a45553bd80d9ada659b1b8023c9506269a707d335120b435`.
Both input documents independently recompute; free scratch is 91,721,109,504
bytes. This admits that earlier diagnostic, not later forest/host/artifact
sources or qualifying profiles.

Sixteen further original artifact parameters now observe seven genuinely
factory-created Local fresh stores. Their actual owner/interfaces/controls
have exact per-node images instead of borrowing the original driver's test
assembly. The empty controls passed to each fresh constructor are that real
store's controls, not a companion. Source observation records are non-owning
and emitted after unchanged assertions/cleanup; same-object in-place
reinitialization remains that same original object.

Both histories freeze all node maps before execution, and manifests enumerate
each selected image. Legacy common metadata maps remain supported, while these
artifact owner changes require an exact node sequence. Swapped/wrong/missing
maps reject. Actual probing exposed reconciliation's early-return path: it
never creates a child, so policy does not invent one. Object remains root-only.
Transitive common-helper body/hash checks remain unchanged; forwarding checks
now include the observation sequence.

Actual minimal-input observation and independent empty-cache locked replay
each pass 240 executions, 271 records (267 original owners/four contracts)
and 1,573 role/image correspondences, reproducing the unchanged forest SDK.
Full tooling passes 340 checks (323 passed/seventeen explicit macOS-native
skips); changed artifact source whitespace, frozen inventory and SDK catalog
checks pass. Formatting the newly touched evidence wrapper repairs its existing
two-line whitespace without assertion changes. Native admission requires
232 foundations and 105 scopes/1,223 observations, pending. Controllers,
remaining artifact lifetimes and qualifying backends remain unfinished.
README and related guides/model/contracts are updated; product/deployment
examples and diagrams, public contracts, seals, locks and reviewer/task markers
are unchanged.

Bounded custom architecture review found no confirmed blocker in this increment,
with current-file/no-diff-reconstruction and no-validation limitations; final
T081 remains open.

Earlier owner run
[40170918399](https://github.com/Stonefly-Labs/Hoard/actions/runs/40170918399)
at exact `4ed4c23aca500827a26d692e011794a2ad84f202` passed all three jobs,
231 foundations without failures/errors/skips, 105 scopes/1,163 exact
discoveries/executions and every prerequisite. Typed input:
`69d28d12e977e66c52c7c4f805171b825c7d3c6fabf2074d710535052f7f7cfa`;
separate original input:
`96335b1825f3c29f7ab9f489622e1197d437315cda3882d69deea43e9e696b78`;
preparation:
`794df389df462f2a03e34e539928ef4214d02eba2c9f925ec5de6864d99cadec`.
Both documents independently recompute; free scratch is 91,721,052,160 bytes.
This admits earlier forests/hosts/fifty artifact parameters, not later budget/
quarantine sources or qualifying profiles.

Fifty-three further artifact witnesses now observe actual rejected provider
roots, the exact admitted decorator, lifecycle/validation/cleanup owners and
fixed-binding facts. Rejected factories retain their real stores and foreign
authorities; explicit controls belong to those actual stores. Driver observation
records the authority really passed to initialization, not an unused underlying
authority. Facts preserve their source parameter lists, with independently
checked frozen binding ownership and no Object fallback. Prefix-stop and
failed-quarantine sources add two genuine Local fresh-store children, totaling
nine; assertion and cleanup ownership remain unchanged.

After intended routing failures and updated non-owning observer forwarding,
actual minimal-input first/replay each pass 293 exact executions, 326 records
(322 original owners/four contracts) and 1,958 image correspondences. The SDK
archive is unchanged. Full tooling passes 340 checks (323 passed/seventeen
macOS-native skips), as do changed-source whitespace, frozen inventory, SDK
catalog and patch checks. Native admission requires 232 foundations and
105 scopes/1,276 observations, pending; qualifying backends and remaining
controller/lifetime attribution are unfinished.

Budget run
[40171398685](https://github.com/Stonefly-Labs/Hoard/actions/runs/40171398685)
at exact `cd5e7598f74e3aaee9263736eeb0ee8556f2b84b` passes all three jobs,
231 foundations without failures/errors/skips, 105 scopes/1,207 exact
discoveries/executions and every prerequisite. Typed input:
`d4f6225797f06597ceb589a017a92b90e2950d182250cdc24ab3378f553f0767`;
original input:
`14439256a8c25f61cdc1dd985647887b033a23e1ccb782aee876a79c6bff1312`;
preparation:
`330756cdf89bc5f4079c7c2886de85435129a19f49c584ecf08f5bb47c446f3a`.
Both documents independently recompute; free scratch is 91,716,349,952 bytes.
This admits those budget/recovery sources, not later quarantine/rejection/
lifecycle sources or qualifying profiles.

Eighteen further original executions observe actual artifact/metadata session
and configured-module owners. The test-only fixture's read-only controls retain
the exact constructor objects, with no second instance, cleanup owner or SDK
dependency. Successful configured-host parameters retain two independent real
module/session roots after unchanged stop/readiness assertions; shared reference
history does not invent a reopen edge. Heterogeneous child images apply only to
the nine exact Local reopen identities. SQLite-bearing rows require actual
SQLite environment admission.

After the intended 293-versus-311 dispatch failure, the private probe corrects
stale root dependency assets through real isolated local-feed locked fixture
package preparation, and fixes a probe-only image-loop shadow. Fresh first/
replay each pass 311 exact executions, 346 records (342 original owners/four
contracts) and 2,098 image correspondences, including real owner-type hashes.
The SDK archive is unchanged; both runs reproduce fixture archive
`c123bb3df647329059657e39b540effc5dab6c640e41e5d5b9ee01e78a28c633`.
Full tooling passes 340 checks (323 passed/seventeen macOS-native skips);
changed-source formatting, frozen inventory, SDK catalog and patch checks pass.
Bounded custom architecture review finds no confirmed blocker, with explicit
current-file/no-diff-reconstruction and no-validation limits; final T081 and
qualification remain open. Current native target is 232 foundations and
105 scopes/1,294 observations, pending.

Six inspected completed private dependency caches were reclaimed without
discarding source, feed, runtime, proofs or receipts, or lowering the 24 GiB
capacity guard. README and related model/contracts/guides are updated; common
assertions, production APIs/providers, SDK signatures, locks, task/reviewer
markers and production/deployment examples/diagrams are unaffected.

Six more frozen qualification/marker contract tests use package-only partial
observers for actual loaded Abstractions types. Each binding now selects eight
value/contract witnesses, not invented provider sessions. Default contract/value
execution passes eighteen tests without skips or a new SDK dependency.
Routing's applicable AS-47 selection exposes an old test expectation that
incorrectly included excluded Object AS-41; independent expectations now exclude
non-applicable rows too. These contract passes do not claim excluded durability.
Actual fresh first/replay each pass 323 exact executions, 358 records (342 owners/
sixteen loaded contracts) and 2,110 image correspondences with the unchanged SDK.
Full tooling passes 340 checks (323 passed/seventeen macOS-native skips);
scoped formatting, frozen inventory, SDK catalog and patch checks pass.
Current native target is 232 foundations and 105 scopes/1,306 observations,
pending; remaining controller/authority/rejected-host/child attribution and
qualifying backends remain unfinished.

Quarantine run
[40172357792](https://github.com/Stonefly-Labs/Hoard/actions/runs/40172357792)
at exact `789382edfef5875328d32649843eec209864d7e0` passes all three jobs,
232 foundations without failures/errors/skips, 105 scopes/1,223 exact executions
and every prerequisite. Typed input:
`d39266356a4dc3920400a65ec168a5ef264f1359fef97472f3ff85060ebcdd8f`;
original input:
`79ce10b819d0a1e7c65b8e88a32c93cc8c209b4f9ac3dae68898ac2235ee6b2b`;
preparation:
`fa92a4780e39ae90126bb61e4cff033d02819726dceeee67ebb3569d3745762f`.
Both documents independently recompute; free scratch is 91,720,994,816 bytes.
It does not admit later lifecycle/composition/qualification-contract sources or
qualifying profiles. Production/deployment examples/diagrams, public APIs,
provider implementations, common assertions, SDK binary/signatures, locks and
task/reviewer markers remain unaffected.

The private revision-2 proof now admits a separate closed `original-owner` kind:
exactly the genuine existing owner, independent roots only. Four provider-neutral
authority/bridge facts run in explicit Local/Object binding contexts, while two
rejected configured-module parameters observe their actual module without ever
reading or inventing its unavailable session. The copied-handle fact retains
both real authorities and shared reference history. Existing original-instance
roles, loaded-contract policy and typed origins remain strict; no control,
provider parameter or cleanup ownership is fabricated.

The SDK test first fails at unsupported-kind capture, parent admission first
fails `WitnessMissing`, and dispatch first fails five versus seven scopes.
Actual fresh first/replay each pass 333 exact executions, 370 records (354
genuine owners/sixteen contracts), 2,122 PE/archive correspondences and actual
authority/bridge/module type hashes. SDK archive:
`7651009db9b2ae1f857deb2973198d74edbf051e37514dbc4f013ddafe13dd26`.
All fifty logger regressions and 341 tooling checks pass (324 tooling passes/
seventeen explicit macOS-native skips), alongside changed-source formatting,
frozen inventory, SDK catalog and patch checks. Bounded custom architecture
review finds no confirmed finding, with current-file/no-execution/no-independent-
diagnostic-verification limitations; final T081 remains open.
The independent native target is 233 foundations and 107 scopes/1,317
executions, pending. These local probes remain minimal-input non-qualifying
diagnostics, not category/profile acceptance.

Lifecycle run
[40173345291](https://github.com/Stonefly-Labs/Hoard/actions/runs/40173345291)
at exact `88aa8a1dcd05d62538fc263bf1a665ceb2dbef64` passes all three jobs,
232 foundations without failures/errors/skips, 105 scopes/1,276 exact executions
and every prerequisite. Typed input:
`33c661c2e2d86a71c5d1b200c7562c6e68cb62ba2c269763e900e84c65c0ddec`;
original input:
`5cf83d15ec21a163a92eca0e28e64343f192c22ac9647985763d8b016b6b8705`;
preparation:
`979c95c8713ef3794a6c7a3392c36db1b85fc086f81115d04fc8195dd7d3da3c`.
Both documents independently recompute; free scratch is 91,716,321,280 bytes.
It does not admit later composed/contract/owner-only sources or complete
profiles. README and affected guides/model/contracts are updated; product
APIs/providers, common assertions, package references/locks, task/reviewer
markers and production/deployment examples/diagrams are unaffected.

The existing external-wrapper diagnostic now independently admits all sixteen
crash/retention/transfer producer packets after safe runtime ingestion. Its
hash-only parent receipt binds exact source execution/runtime-proof hashes,
producer/state bytes, attempt/group/current inputs and the same-run parent
transfer measurement receipt. Kill/state/readback/acknowledged-receipt and
ordered live-retention invariants remain mandatory; stale/self-reported transfer
packets cannot substitute for the parent measurements.

Three new missing-function reds are repaired. All 105 SDK diagnostic tooling
tests and 344 tooling checks pass (327 passed/seventeen native macOS skips);
frozen inventory, SDK catalog and patch checks pass. Twelve preserved genuine
source packets also pass re-admission, explicitly historical readback rather
than fresh current-run evidence. No fresh complete controller receipt is claimed
locally. The unchanged 107-scope/1,317-execution native request now requires 236
foundations and the sixteen-source receipt hash, pending. Category/controller
provenance and qualifying backends remain unfinished. This supplemental receipt
invents no provider session/component or child-start proof. SDK binaries,
provider code, source wrappers, common assertions, locks, task/reviewer markers,
production/deployment examples and diagrams are unaffected.

Loaded-contract run
[40174640775](https://github.com/Stonefly-Labs/Hoard/actions/runs/40174640775)
at exact `8c969bda5050b7c67f7fac87a27e7fbe19e35c7f` passes all three jobs,
232 foundations without failures/errors/skips, 105 scopes/1,306 exact executions
and every prerequisite. Typed input:
`1aae44bb77b109090b75209437639ccdd5884c47dacd0a6a13ee35c50224941a`;
original input:
`2df4b9914a51514d197a7ccfa4f60d53c94d84844d51a85083f60850e20d3642`;
preparation:
`aa9ea7e25ce3014341491b674f7290b94832cb5a73a74fc1229388f345eee7de`.
Both documents independently recompute; free scratch is 91,721,003,008 bytes.
This admits composed/contract sources, not later owner-only/producer-packet
sources or qualifying profiles.

The closed source policy separately identifies all six frozen inspection
witnesses and sixteen original crash/retention/transfer producers. A structurally
valid but unrelated provider session is not their proof; qualification rejects
until actual independent inspection/controller evidence is admitted. Known
original requirements also apply to `none` binding contexts rather than being
skipped when no provider is selected. Diagnostic observations remain separate
and non-qualifying; ordinary typed consumers keep their prior requirements.
Twenty-four source/binding substitutions and three missing-provider contexts
first passed incorrectly before the regressions/repair. The whole qualified
metadata batch also now rejects despite valid ordinary provider origins.
The earlier positive-origin cross-binding replay fixture is explicitly
diagnostic, not a successful qualified batch. Shared immutable producer policy
now drives both packet import and this gate, without changing source wrappers,
SDK/package/lock bytes or frozen identities. Full tooling passes 351 checks
(334 passed/seventeen explicit macOS-native skips); native target is 243
foundations, 107 scopes/1,317 executions and the sixteen-source receipt,
unadmitted.

Owner-only run
[40175617630](https://github.com/Stonefly-Labs/Hoard/actions/runs/40175617630)
at exact `c2d3e2b137540528e35fb9e61c35019ff99e095c` now passes all three jobs,
233 foundations without failures/errors/skips, 107 scopes/1,317 exact executions
and every prerequisite. Typed input:
`514c741d134f348c36543d0d8360f72194cf4a5ff3c8045f56d96b71f37705a5`;
original input:
`48190daa0a42318bb9aba59415e04c1bfb56fdd2c6dc26b44690201d9702ebe7`;
preparation:
`4f91a94daa5d3f8102121025c6762b03330910dc32486954428f8baff905e737`.
Both documents independently recompute; free scratch is 91,720,790,016 bytes.
This admits genuine owner-only sources, not later controller-packet,
partitioned-category or non-session-gate sources or qualifying profiles.

Controller-packet run
[40176564122](https://github.com/Stonefly-Labs/Hoard/actions/runs/40176564122)
at exact `165efbf3344257be22f8fdef449d02dd4a267709` is now admitted: all three
jobs successful, 236 foundations without failures/errors/skips, 107 scopes/
1,317 exact discoveries/executions and every prerequisite. Fresh sixteen-source
receipt:
`455659d31f331da913a568f332a05a7342cbeace75dd016327cd03e11a1fa752`;
typed input:
`62d1ec6338d88c075b1c798dff2fcdfbd4c8cc64f83f444fe8ecad50341203cb`;
original input:
`64c5131682da321cdd38e3b18057759f8c1bbfe51ca69244a6f591dd0b77b723`;
preparation:
`eb82088ea5c71fec52059e0de45863375db2e9ccf5529dfabe65bc383dda4d5b`.
Both input documents independently recompute; free scratch is 91,720,732,672
bytes. This admits that diagnostic snapshot only, not later partition/gate
changes, new inspection capture or qualifying profiles.

The six original architecture facts now optionally capture the exact selected
JSON/source, project/nuspec XML and PE bytes actually consumed by inspectors.
The source context is copied and closed; cached immutable bytes are checked
against preselected hashes and reverified before a bounded hash-only packet
can be written after unchanged assertions. Unknown/missing/changed/oversized
inputs, abandoned scopes and repeated completion reject without a new
successful packet. Raw paths/bodies do not enter packets. With no context the
predecessor read behavior is unchanged. This test-only source hook adds no SDK
reference or provider/session observation; independent preparation, parent
runtime/packet admission and category integration remain unwired and
qualification still rejects inspection witnesses.
Sixteen focused .NET checks pass without skips (twelve capture cases and four
unchanged standalone boundary facts). All 351 tooling checks pass (334 passed/
seventeen explicit native macOS skips), with changed-file whitespace, frozen
inventory, SDK catalog and patch checks passing. Production/provider APIs,
package/SDK references and lockfiles, reviewer/task markers and deployment
examples/diagrams are unaffected.

The first independent inspection diagnostic channel now selects exactly the
three literal-only metadata facts in their actual architecture assembly.
The source context is allocated only for execution, independently from
discovery, and binds the current run/attempt/inputs and frozen empty external
file maps. Parent admission joins the exact packets to admitted runtime proofs,
rejecting missing/extra/duplicate/stale/mismatched packets or external file
claims, and retains a separate hash-only receipt. The candidate build and
runtime input inventory include this actual assembly and independently verified
logger dependencies without adding a project/SDK reference. Prepared graph
inspection provenance and qualifying categories remain incomplete.
All 108 SDK diagnostic tooling checks and 354 tooling checks pass (337 passed/
seventeen explicit macOS-native skips); frozen inventory, SDK catalog and patch
checks pass. At that checkpoint native execution was requested for 246 foundations and
108 scopes/1,320 exact discoveries/executions, including the three-source
inspection receipt; its subsequent admission is recorded below.

Non-session-policy run
[40178051713](https://github.com/Stonefly-Labs/Hoard/actions/runs/40178051713)
at exact `0d08045a4ca36426f27043899932a02acc028769` is now admitted: all three
jobs successful, 243 foundations without failures/errors/skips, 107 scopes/
1,317 exact discoveries/executions and every prerequisite. Typed input:
`948de6053b9d2d7ecf73c9c3d33dea500b2d1de4410e9fbfd25af50c1e901673`;
original input:
`ffbd5cbb055f3b66662432bbd580b9cb0dc8abf79682708a78437793088430b5`;
sixteen-source receipt:
`5c033a90b6223ebe194a152c2f68e4c1c985e9e87e1af6e5f7b0bd02b2bd56d9`;
preparation:
`e32e432ddaf71067e487c98d9c1450a340562c592a291271961bdc2207305cb5`.
Both input documents independently recompute; free scratch is 91,720,114,176
bytes. This admits the atomic category/non-session gate snapshot, not later
inspection capture/parent sources or qualifying profiles.

Prepared-graph plumbing now has an injected resolver in the existing graph
constructor. The predecessor default is unchanged; the new callback path never
invokes its raw-output runner or guesses output names. A separate bounded
MSBuild probe queries actual `TargetPath`, `ProjectAssetsFile`, `ReferencePath`
and `Compile` values. Only the metadata actually consumed by inspectors is
projected into private configuration. Unknown metadata is not retained.
The owned-child wrapper rejects foreign/symlinked projects, changed project
bytes, stale/extra/changed response fields and outputs outside its root.
Raw tool output stays transient, bounded to 1 MiB with a 110-second inner
deadline inside the 120-second owned-child budget. An actual local Hosting
probe resolves 310 references and 84 compile inputs. This is metadata plumbing,
not native ownership or prepared-graph acceptance.

The actual literal inspection scope also passes local discovery/execution and
an independent fresh-root replay: three exact facts and three source packets
per run, with actual runtime proofs admitted by the existing strict parent.
Both use the same architecture image
`1ae924ee321b8ec990fd826563ea7a316b0cc141cbc3a4c0b0de92f06cc099d8`.
Their explicitly diagnostic inputs have no historical baselines or native
containment claim. They do not replace native execution.
Three resolver regressions first fail at the missing callback/functions and
now pass. All 357 tooling checks pass (340 passed/seventeen explicit native
macOS skips). Exact selected-file inventories, prepared graph execution and
qualifying profile admission were unfinished at that checkpoint. Production/reference/lock
bytes and deployment examples/diagrams are unaffected.

Literal-inspection native
[40180137288](https://github.com/Stonefly-Labs/Hoard/actions/runs/40180137288)
at exact `3eaa70c842a7a9b24affdcda361ca473600663d1` is now independently
admitted: all three jobs successful, 246 foundations without failures/errors/
skips, 108 scopes/1,320 exact discoveries/executions and every prerequisite.
Typed input:
`48f176803cb49ef7b26dd56a70be368f461fa113a9815edf3676996f036a7bfe`;
original input:
`703b5cce69ff86d58cc80bdb3a89829a78a6b5cc145806baba4918282cd6e98c`;
sixteen-source receipt:
`573aedbe09a0f8c4463aa1f7ff76791fd60c9a93d3c09b34b2ca43c6f1d40ca9`;
three-source inspection receipt:
`79c4d2538dbdaa28f1241170b3dd18a06e0db8dec0204235de56ce0d1366e3a8`;
preparation:
`41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`.
Both input documents independently recompute; free scratch is 91,715,252,224
bytes. This admits that literal-inspection snapshot, not later resolver/
prepared-inspection sources or qualifying profiles.

Prepared inspection now reuses the predecessor graph recipes with actual
bounded resolution, exact full/consumer-body file selection and independently
established framework reference roots. Immutable selected file assignments
extend the configuration fingerprint without exposing paths or misclassifying
the files as runtime/source inventory. Execution-only contexts and the separate
prepared parent receipt require all three actual facts and exact current
run/attempt/input/file/runtime correspondences.
The native path builds the five missing projects with locked preparation
without packing Application, selects the correct already sealed family images,
and independently recollects every selected file for pre/post input comparison.

Actual local preparation builds seventeen distinct original projects and
resolves seven metadata/ten-project and eight artifact/eleven-project graphs.
All three prepared facts pass against the independently reverified predecessor
seal. A fresh locked build replay also passes through the production dispatcher
and strict source parent, with 367 metadata/336 artifact consumer-body/376 full
artifact selected files. Independent production recollection matches its
configuration fingerprint. This replay remains explicitly non-qualifying with
no native containment or complete compatibility-profile claim.
All 120 SDK diagnostic checks and all 366 tooling checks pass (349 passed/
seventeen explicit macOS-native skips); frozen inventory, SDK catalog and patch
checks pass. The next native request is 258 foundations and 109 scopes/1,323
exact discoveries/executions, with separate literal and prepared three-source
receipts. It is not admitted yet. Qualifying profiles and T019/T020 remain
unfinished; no task/checklist marker, production/reference/lock bytes,
deployment example or diagram is changed.

The extraction transport guards now select every applicable parameter family
from the immutable embedded inventory, rather than only MP-21 and AS-15.
They include families with one selected row and test the full selection,
one omitted row and one changed/foreign row. Foreign artifact controls borrow
the opposite provider where the frozen row has that parameter; provider-neutral
families use a deliberately unselected parameter instead. All 2 SQLite/
2 memory/85 Local/84 ObjectSemantics family/case groups are exercised under
the three controls without changing any runtime test identity or catalog row.
The missing shared selection helper first fails compilation with CS0117;
the repaired 23 focused .NET checks pass without skips, with changed-file
whitespace, frozen inventory, SDK catalog and patch checks passing.
This expands discovery/ownership transport guards only, not actual extraction
or category acceptance. T019/T020 and qualifying profiles remain unchecked.

Category history now also accepts a predeclared joint profile scope map.
This addresses real artifact methods whose discovery includes both providers'
parameter rows: imports must not split/rewrite actual source transports after
execution. The complete binding/identity union and primary cases are copied
before launch, each scope owns a fresh attempt UUID, and repeated neutral
identities require different scopes. Both binding histories commit only after
all scopes, replay/origin state and aggregate budgets validate. Case matching
uses binding plus identity, so one provider's failed execution cannot fail the
other provider's same-named successful fact. Failed/incomplete joint attempts
survive fresh retries; binding-local and joint lifecycle APIs cannot interleave.
The catalog independently selects six complete scopes/profile, preserving
both providers' real method parameter families: 134 metadata and 227 artifact
binding/identity pairs, with no duplicate identity inside one scope.
Four regressions first fail at missing joint/partition APIs; a fifth checks
binding-specific assertion failure attribution. All 91 strict evidence
checks and all 371 tooling checks now pass (354 passed/seventeen explicit native
macOS skips), with frozen inventory, SDK catalog and patch checks passing.
This is synthetic diagnostic model evidence, not execution of joint profiles
or admission of independent inspection/controller qualification. No task,
review, product/reference/lock or deployment/diagram claims change.

The next increment connects actual runtime transport to the catalog-owned
scope map. `category_attempt` requires an already-written matching category
input document, exact predeclared attempt/binding/primary-case assignments and
the complete independently selected scope. Discovery and execution share the
same strict transport path as existing diagnostics; returned raw manifest,
owner, completion, witness and proof bytes are preserved for history admission.
Prepared category scopes select the one metadata or two artifact facts and
their source context, but still verify the complete three-fact configuration
fingerprint. Standalone prepared execution still requires all three facts.
Inspection/controller parent joins additionally require the exact catalog
binding and case scope; they remain diagnostic, not qualification authority.

Actual local execution uses freshly captured metadata/artifact input documents
and all six inspection scopes, totaling twelve actual source executions.
Package, lock, runtime-image and inspected-file fingerprints reverify afterward.
Both histories explicitly interrupt as incomplete because their other scopes
have not executed; no old runtime/input documents are relabeled. The first
private diagnostic capture omitted the recomputed binding capability digest;
it is superseded, not admitted as the fresh-input replay. The corrected replay
recaptures all fingerprints before execution and independently reverifies them.
Three new regressions first fail at missing runtime-scope, category-source
receipt and category-dispatch APIs. All 123 SDK checks and all 374 tooling checks
pass (357 passed/seventeen explicit native macOS skips), with inventory/catalog
and patch checks passing.

Native [40183443219](https://github.com/Stonefly-Labs/Hoard/actions/runs/40183443219)
at exact `d59c1d9b25d24963ffc5566973fc56430cd0d8ed` independently passes all
three jobs, 258 foundations without failures/errors/skips and 109 scopes/1,323
exact discoveries/executions. Preparation verifies thirteen locks, eighteen
packages and its fresh locked replay; scratch is 91,719,708,672 bytes.
The typed input is
`1606d6a58132fb9885944f63d225e21f11f6b8106f87d5bffa1f973c0b1d8ff8`;
original input:
`4f5d9a968b15483548f51c1080bd1940851131f92230f8844491a37b2e440227`;
sixteen-source receipt:
`f18c669925e15cee429d136f76c390431c383a3f2c671943d133598f71712ad3`;
literal receipt:
`74932aa9326da1ad5032fad785bf1e9e443b99d011facea8b61beb1d975a6a76`;
prepared receipt:
`e398c7a3418daf891ebafd48ab49ab9a831d560ab399995ea0558c081f65afc9`.
This admits the prepared-inspection native snapshot, not subsequent parameter
guards, joint history or category dispatcher changes. Qualifying profiles,
independent source/controller qualification and T019/T020 remain incomplete.
Product/reference/lock bytes and deployment examples/diagrams are unaffected.

Category discovery/execution now request an opt-in owned-command record to
support the remaining independent source-proof admission. The executor freezes
and hashes the actual argument vector and working directory, binding observed
PID/start identity, run/root/sequence, monotonic timing, exit, diagnostics and
whole-group settlement in a create-new, read-only private receipt. Raw argument
or directory values never enter the record. Ordinary commands that do not opt
in remain unchanged; existing recovery/transfer receipt schemas are preserved.
Requests must be boolean, cannot record cleanup, and reject over 1,024 arguments,
64 KiB encoded argument bytes or invalid Unicode before native child launch.
Incomplete/non-native diagnostics carry no native record hash and never gain
qualification by this optional field.

The new admission regression first fails at the absent argument, then passes.
An initially overbroad subprocess mock intercepted the existing ownership
probe, exposing the need to reject malformed/oversized record requests before
that probe; moving admission earlier corrects it. All 375 tooling checks pass
(358 passed/seventeen explicit macOS-native skips), with inventory/catalog and
patch checks passing. The existing Linux-only safe-output test now asserts
successful/failed records, exact argument hash, PID/start, private read-only
receipt and absence of raw canaries; those native assertions await Linux.
No native success or source/controller qualification is inferred from local
skips. Task/checklist markers, packages/locks and deployment diagrams stay fixed.

Complete metadata batch orchestration is now wired into the native diagnostic
path. It independently captures the metadata profile and its two frozen binding
declarations before any execution, writes a dedicated input document and
predeclares all six scope UUID/maps. The dispatcher executes all 134 catalog
witness occurrences and passes the original transport objects to joint
admission only after every scope finishes. A create-new private 102-entry history
includes all 96 inherited cases and six qualification obligations and
records scope/result hashes and terminal state counts; execution or admission
failure preserves incomplete histories and propagates the original failure.
Missing parent controls are not treated as passes. The whole diagnostic retains
`qualification: false` and never substitutes for the qualification backend.
Completion independently recaptures metadata inputs and inspected bytes again.

The new orchestration regression first fails at the missing API, then verifies
all scopes/unchanged transport identity, partial execution failure and rejected
atomic admission. Existing real input-capture checks additionally verify a
separately captured/recomputed metadata profile rather than relabeled harness
inputs. All 124 SDK checks and all 376 tooling checks pass (359 passed/seventeen
explicit native macOS skips); frozen inventory/catalog and patch checks pass.
The added admission-error fixture passes its focused rerun.
The requested native addition is six scopes/134 exact executions and a
102-entry diagnostic history; parent controls, independent non-session
qualification, full artifact/category CLI acceptance and T019/T020 remain
unfinished. That complete Linux metadata batch is now admitted at `216413a`
as recorded below.

Category command parents now independently read each available owned-executor
record before discovery/execution output admission. They require exact
run/root/sequence, argument/cwd hashes, nonzero PID/start identity, read-only
record bytes, successful supervisor diagnostics, matching exit, bounded nested
monotonic times and actual whole-group settlement. Settings are independently
re-read against the prelaunch bytes. A create-new hash-only parent joins the
record to its manifest, input/group/attempt/purpose and settings; no raw command,
settings or private paths are retained there. Native executors cannot omit the
record; explicit non-native diagnostic adapters produce no native receipt.
Invocation ownership alone is not assertion success or qualification.

The parent regression first failed at the missing API, then exercised changed,
foreign, missing, writable, unsettled and replayed records plus changed settings.
The existing exact-scope regression now also joins all eighteen simulated
discovery/execution invocations and labels them non-native. All 377 tooling
checks pass (360 passed/seventeen native macOS skips); inventory/catalog and
patch checks pass. Native parent execution is pending, not admitted. The earlier
metadata summary serialization boundary additionally reproduced its mappingproxy
TypeError before repair; all124 SDK checks passed at `216413a`. No task/checklist,
provider/package/reference/lock or deployment surface changes in this increment.

Exact metadata native run
[40187523765](https://github.com/Stonefly-Labs/Hoard/actions/runs/40187523765)
at `216413ae43fdc2feb923a1c8fd0d334a3eee5f03` passed all three jobs and
268 foundations without failures/errors/skips. Strict independent projection
admits the existing 109 scopes/1,323 discoveries/executions and separate six
metadata scopes/134 witnesses: 115 scopes/1,457 executions in total.
Metadata input `2dc2334ddc805d5c42bc20d6d7d46ac1b6fda4bff27e63e82925962082366073`
and result `d2101a72a53af1c01382597cd7272ce2b650d3e04681a84abed2c74f4def7669`
retain 71 Passed, 22 Incomplete, 9 NotApplicable and 0 Failed. The private history
correctly includes 96 inherited cases plus six QC obligations. The first private
observer incorrectly expected 96 entries and rejected the successful run; frozen
`expected_cases("metadata")` independently explains all 102 entries, and corrected
projection passes without changing production results or weakening controls.
The orchestration fixture now derives its expected count from that full catalog.
All prior native prerequisites and thirteen-lock/eighteen-package fresh replay
pass; free scratch 91,718,258,688 bytes. This admits actual metadata diagnostic
execution and native executor records at `216413a`, not source qualification,
the 22 outstanding obligations or later independent command-parent admission.

Independent command-parent run
[40188204924](https://github.com/Stonefly-Labs/Hoard/actions/runs/40188204924)
at exact `ac561f200fc1f12b580ccdfe37cc79391f909fd0` is now admitted: all three
jobs, 269 foundations without failures/errors/skips and 115 scopes/1,457
executions, including actual native category command-parent joins. Metadata
inputs `d80314d11ee346b738659b10613614b08dbeacc1e58929c707c67af8275ed8d5`;
results `8a8348a2a1912ae8f0244d59e35b32a51ee02136724c9a62642dd1293dd0e8a9`.
The unchanged 102-entry state remains 71 Passed/22 Incomplete/9 NotApplicable/
0 Failed. This admits that source snapshot, not later artifact batch wiring.

Both categories now share complete predeclared batch execution and retained
failure handling. The native path independently captures artifact inputs and
its two declarations before any runtime execution, re-executes all four actual
paced transfer children under `category-artifact-transfers`, then runs all six
artifact scopes/227 witness occurrences. Stores, cache, producer/measurement
proofs and parent summary use that separate namespace; runtime controller
settings and exact source-packet admission select the same fresh measurements.
Legacy harness paths/defaults remain unchanged. Artifact and metadata inputs
are independently recaptured at completion. Artifact history retains all 103
entries: 96 inherited cases plus seven QC obligations, never a reduced inventory.
Exact `b72829c15da565262f1bc6b5e9fa607b460b4656`, run
[40190769309](https://github.com/Stonefly-Labs/Hoard/actions/runs/40190769309),
now independently admits this execution: all three jobs, 270 foundations
without failures/errors/skips and 121 scopes/1,684 exact witnesses (109/1,323
prior plus metadata 6/134 and artifact 6/227). All four new transfer command/
start identities differ from earlier measurements. Artifact input:
`fa1e862fab5da10010366ddf1d4385d562aab5680ede5d4a5757bd9443f42c4f`;
result: `1fd7285494f0febb4d09ec9f74e9801022ea62f77c10fb63cf6c6e6da39bd001`.
Artifact history retains 92 Passed/7 Incomplete/4 NotApplicable/0 Failed;
metadata retains 71/22/9/0. Qualification remains false, all prior native
prerequisites and 13-lock/18-package fresh replay pass. This does not admit
later parser or metadata-control changes.

The artifact orchestration test first fails at the missing shared API, then
passes unchanged transport identity and execution/admission failure checks for
both profiles. Measurement tests cover both namespaces, exact stores/cache and
unchanged RSS/PID/hash/runtime/pacing constraints. Wrong profile/mode/traversal
namespaces and borrowing old harness receipts reject. Real input capture now
checks independent artifact recapture too. All 378 tooling checks pass
(361 passed/seventeen explicit native macOS skips), including 126 SDK checks;
frozen inventory/catalog and patch checks pass. Existing production providers,
package/reference/lock bytes, checklists/tasks and deployment diagrams are
unchanged; source/controller qualification and remaining controls stay closed.

Runtime transport parsing and qualification-origin admission now have a shared
staged boundary. `inspect_runtime_attempt` returns an immutable envelope with
`qualification: false`, the admitted input snapshot/digest and structurally
validated observations. Parent corroboration can inspect those observations
without first claiming qualified origins. Normal `ingest_runtime_attempt`
uses that same parser, then applies the unchanged original/session/non-session
qualification rules against the captured immutable inputs, not caller mutations.
No bypass flag is added and unadmitted inspection/controller witnesses still
reject qualification.

The new test first fails at the missing inspection API, then verifies immutable
non-qualifying output, retained input identity and rejection of changed proofs,
truncated witness streams and contradictory completion. Existing unrelated
session/source substitution cases now also prove that inspection is explicitly
non-qualifying while normal admission still rejects. All 92 evidence tests and
all 379 tooling checks pass (362 passed/seventeen explicit native macOS skips),
with frozen inventory/catalog and patch checks passing. This is a prerequisite
for independent source corroboration, not its implementation or a qualifying
profile. Tasks/checklists, package/provider/reference/lock bytes and deployment
diagrams are unaffected.

Metadata category orchestration now separately executes the SQLite native
stall/retained-cleanup control and all M0..2/U0..4/R0..1 recovery barriers plus
walkthrough against the captured metadata inputs. The closed
`category-sqlite-native-noncooperation` and `category-sqlite-recovery`
namespaces allocate fresh stores, cache and producer/proof paths; legacy
defaults remain unchanged. Native-stall packets carry the current input hash.
Seed and readback controller records now require the exact sequence, valid PID/start,
successful exit/settlement, finite timing and five-minute recovery bound, not
just a successful event. Wrong-seed/readback regressions first reproduced
acceptance before repair. Both namespaces, wrong-profile/mode/traversal rejection
and unchanged failure handling pass all 380 tooling checks (363 passed/seventeen
native macOS skips), frozen inventory/catalog and patch checks. Exact native
run 40192845240 at `fffaf6f` passes 272 foundations without skips and the
13-lock/18-package replay, but SDK diagnostics end `EvidenceIncomplete` after
entering metadata batching. It is not admitted; phase progression alone is
not a control receipt or root-cause diagnosis. No missing obligation is marked
passed and no qualification gate changes.

Unexpected runtime results now retain bounded closed diagnostic context instead
of losing everything behind `EvidenceIncomplete`: observed code/exit, witness
state counts, mismatch count and at most four exact identity hashes. Full
runtime evidence remains unchanged; this truncates diagnostic context only,
never a passing inventory. Native category errors distinguish the current
catalog scope from joint admission. No raw identity, assertion message, private
path or output is printed. The missing-context regression first fails before
repair; safe projection and both batch failure phases pass all 381 tooling
checks (364 passed/seventeen native macOS skips), inventory/catalog and patch
checks. This enables diagnosis of the pending native failure, not a claimed
repair or qualifying result.

Exact `564c67ff384b1cdf93cc8eb7944e725d1073df73`, run
[40193163127](https://github.com/Stonefly-Labs/Hoard/actions/runs/40193163127),
now passes all three jobs and 272 foundations without skips, independently
admitting both complete batches plus the fresh metadata-input stall and all
ten recovery barriers/walkthrough. Controller/start and seed/readback hashes
are disjoint from earlier harness controls. Metadata input
`cee1270735cad75aa57f343da95f2f6128ae1c5e0b702d61e0f6bb3adff4200f`;
result `b39503b9196fca72c6c9a96bc92e16a37e5556d2f8827e71e28900802454e6cc`;
recovery summary `e4f96944ee4e7e370db20dc285ca2cbc8a7330969513de507f0beda6d1342d7a`.
The 121 scopes/1,684 witnesses and both incomplete category states remain
unchanged; actual controls are not yet imported as passing case obligations.

Later `f5daff9`, run 40194969166, passes 273 foundations and lock replay but
fails earlier during original-wrapper observations, before category execution.
This is not the same failing phase or evidence of a deterministic controller
regression. Its top-level CLI path discarded the bounded unexpected-result
context added for category failures. A main-path regression reproduces that
loss; the CLI now preserves the same <=1KiB closed/hash-only context without
changing exit/status/admission policy. All 381 tooling checks, frozen inventory/
catalog and patch checks pass. The intermittent failure's cause and native
verification of this final projection were pending at that checkpoint.

Exact `4e6f03b`, run
[40197707264](https://github.com/Stonefly-Labs/Hoard/actions/runs/40197707264),
passes 273 foundations without skips and lock replay, then records 182 Passed/
1 Failed original-wrapper witnesses. The sole identity hash
`7c11f2a8b0d0e729b01671bcb71168424cfcd0549a3dc00f0c950260c23fdad1`
resolves against the frozen catalog to ObjectSemantics'
`Deadline_and_stop_return_while_a_native_io_boundary_holds_provider_state`.
The bounded projection works; this failed run is not admitted.

That fixture previously started its 100 ms wall deadline before the worker
reached the native fault seam. A 200 ms `pointer.compare` observer reproduces
the entry-assertion failure deterministically with the real ObjectSemantics
provider (Local passes). The regression remains in the existing frozen test
identity. Only this fixture now injects a one-shot controlled clock and advances
its 100 ms deadline once the synchronous native boundary is entered. The
shared consumer's entry, bounded failure, retained ownership and 20 ms stop
assertions are unchanged. The native hold remains live until `finally` releases
it; actual settlement is awaited before its events are disposed. Production
providers, shared SDK assertions, package references/locks and inventories
are unchanged. This is a deliberate fixture-scheduling correction, not a claim
that the old setup is token-identical.

Fresh locked package preparation followed by
`dotnet test <private-current>/tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj -c Release --no-build --no-restore -p:ArtifactPackageAcceptance=true --filter FullyQualifiedName~ArtifactNonCooperationTests`
passes all twelve cases on macOS. This is local diagnostic evidence, not native
Linux containment. All 381 tooling checks (seventeen explicit native macOS
skips), frozen inventory/catalog checks,
`dotnet format whitespace --folder tests/contracts/Hoard.Artifacts.Tests/Cases --include ArtifactNonCooperationTests.cs --verify-no-changes --verbosity quiet`
and `git diff --check` pass. Exact-head Linux confirmation was then pending;
the reproduction establishes a real setup race but does not prove the precise
assertion behind every earlier intermittent run. No task/checklist marker or
qualification gate changes. Deployment diagrams/examples are unaffected.

Exact `0107db5546578ae8b10ec2177223fe38fbee208c`, run
[40199986870](https://github.com/Stonefly-Labs/Hoard/actions/runs/40199986870),
now passes all three Linux jobs and 273 foundations without failures/errors/
skips. Independent strict projection admits all 121 scopes/1,684 exact witnesses,
both complete batches, fresh metadata native-stall/ten-barrier recovery and
independent artifact transfers. The delayed-entry case now passes in the real
native chain; the failed `4e6f03b` receipt remains unadmitted. Metadata input
`24813b35ddc840ec4fe8640f523c93649e3a7f27293a70e3252209d0269b898b`;
result `a6a526ba772f1d09cfb7671c28060a5d9a363ea7704252660d4752822725df87`.
Artifact input `b80273f8bb92d8dd0fa8ce9ce4caa4e9174247ccc5bbe541fd258a7a00334516`;
result `763e256aed15d97740ff268da7a600259ed801b1031da9a68d2a4d129028a59a`.
The 13-lock/18-package fresh replay also passes. Histories still retain 22
metadata/seven artifact incomplete obligations and `qualification: false`.
The transient watcher TLS failure was retried without admitting unavailable
logs. This exact receipt does not cover the later source-parent changes below.

Category inspection/controller execution now additionally writes a create-new,
read-only `category-source-<attempt>.json` parent. It independently rereads the
exact source receipt and joins every frozen identity/binding/primary-case to its
actual execution ID and runtime proof hash. Source receipt hashes, schemas,
scope/run/group/attempt/input agreement, exact complete witness sets and
kind-specific controller proof keys are checked, not accepted from a count.
For a native owned run, its existing execution parent and command record are
mandatory: current root/run/attempt/manifest/input, actual result record hash,
read-only parent/record bytes, unchanged settings and settled children must
agree. Explicit non-native fixtures may have no command parent, but retain
`nativeContainment: false`; no native success fallback exists.

The scope summary retains this new parent hash, and safe category summaries
expose a parent count plus canonical scope-to-parent digest (four metadata/
three artifact sources on a complete run). The missing-API regression fails
first; tests cover every inspection scope, controller source/execution/proof
substitution, foreign/writable command parents, changed settings, retained
children, missing native records and propagation of source-parent failures
through the actual category dispatcher. These are simulated tooling fixtures,
not native receipts. This increment does not qualify source origins or import
the remaining controller/QC obligations. Shared assertions, providers,
packages/locks, inventories, task/checklist markers and deployment examples/
diagrams remain unchanged. Exact-head Linux evidence is recorded below.
All 381 tooling checks pass (seventeen explicit native macOS skips), as do
frozen inventory/catalog and patch checks. A rerun temporarily hit the unchanged
24 GiB workspace-capacity gate; removing only this increment's four disposable
restore caches restored capacity and the full suite passed without a bypass.

Exact `78c591989bd6305171677a48fbdbe1d566a2eff2`, run
[40202060742](https://github.com/Stonefly-Labs/Hoard/actions/runs/40202060742),
now independently admits these source links: all three Linux jobs and 273
foundations pass without failures/errors/skips, along with 13-lock/18-package
fresh replay, all 121 scopes/1,684 witnesses and fresh category controls.
Metadata's four source parents have canonical digest
`5827833f284e247b197dee07bfb3a194633364bb2b43fd95a13c103ca8ee9354`;
artifact's three have
`7da9ef71f4f337e33e821d05b2a035bbc6e0b8b7c03a3c234e21ddf7ae22a6f9`.
Metadata input/result:
`ab90f8659476d9c56a7cee107dd1023f9501e294c238f91b7367e0853b606fab`/
`84e778a6f47708fa643f58b0ee58c95310de86e3c92b00d64e30eee185d699fe`.
Artifact input/result:
`a3bf730e03b4cf94693333b82028b4d52bd0f9100265e4b6caa38ac29f78b056`/
`3be3d48a2eb738271d35ac9565e3539fa3a4cd53fcea70e39af70cbd5908e4f3`.
Both histories remain explicitly non-qualifying with unchanged 22 metadata/
seven artifact incomplete obligations. This establishes source-to-execution
linkage, not qualification-origin admission or control-to-case import.

Native `OwnedRun` now retains original safe execution-receipt bytes for commands
it actually recorded, bounded by the existing 50,000-proof limit. Its pinned
reader rejects unknown sequences, changed bytes, writable/nonregular files and
inactive/foreign ownership; a syntactically valid file alone is not authority.
Both category command and source parents use this reader, and retain an explicit
command sequence for later source corroboration. The missing-reader regression
failed before implementation; all 381 tooling checks pass afterwards with 17
explicit macOS-native skips. Linux-only regressions additionally exercise
same-length immutable substitution, an unowned valid receipt and rereading an
earlier command after a later failed command. Exact `d06f2561d8817ac94f493ec22ca6c41fa271eb0d`,
[40204781861](https://github.com/Stonefly-Labs/Hoard/actions/runs/40204781861),
independently passes all three Linux jobs, 273 foundations without skips,
13-lock/18-package replay and all 121 scopes/1,684 witnesses. Four metadata/
three artifact parents pass. States remain 71/22/9/0 and 92/7/4/0 with
qualification false; this snapshot predates inspection-origin admission.

`conformance_sources.py` now owns shared inspection validation and independent
native corroboration, without importing the SDK build/diagnostic controller into
the generic evidence parser. The default transport API still rejects inspection/
controller witnesses even with unrelated valid sessions. Only the concrete
native source context can corroborate an exact complete inspection scope:
actual command ownership, current input/owner/manifest/context/settings bytes,
frozen binding/primary-case identities, consumed-file packets, monotonic timing
and settled children must agree. No opaque admission token or pass boolean is used.

Recorded category commands now snapshot at most 16 owner-held read-only input
files through pinned descriptors, before launch and after settlement. Each
capture has a five-second/256-MiB bound; changed identities or timestamps reject
even if bytes are restored. Executor-held records bind those actual hashes.
Retention is bounded by 50,000 records/256 MiB. Rewiring all current proof hashes
cannot relabel an earlier diagnostic input snapshot as qualification.

The SDK path separately captures and recomputes qualification-mode metadata
inputs, executes its complete six scopes/134 witnesses, and independently
corroborates source origins during atomic joint admission after later commands.
Case attempts reference source-parent hashes; their complete safe graph and
source packets are retained in `proofs/`, not only disposable stores. Histories
remain non-qualifying while required controls are incomplete. This later path
passes all 383 local tooling checks with 17 explicit macOS-native skips; actual
Linux execution is pending. The first full rerun exposed a missing explicit mode
in a legacy simulated fixture; the fixture now declares diagnostic mode rather
than adding a production fallback. The real 24-GiB gate also rejected local
capacity; removing eight inspected obsolete task-generated restore caches,
without deleting feeds/images/receipts or weakening the guard, restored admission.
Controller-source qualification, control imports and the full CLI are unfinished.

A subsequent recovery increment now records an executor-held digest of the
actual recovery/transfer control receipt whenever native execution recording is
requested. Thus matching PID/start/exit alone cannot authenticate rewritten
barrier observations or measurements. Native SDK recovery commands require that
anchored record to match the exact argv/cwd and returned result hash; diagnostic
adapters cannot manufacture a native parent. Metadata's 31 seed/kill/readback/
walkthrough commands additionally snapshot the actual assembly and a create-new
immutable current-input document. Both old and category namespaces retain their
existing closed outputs and qualification false. A missing corroboration API
fails before implementation; changed barrier values/timing, sequence, argv/cwd,
input maps and rejected native readers fail afterwards. All 384 local tooling
checks pass with 17 explicit macOS-native skips; the actual Linux barrier test
now also checks the executor-held controller-byte digest. Native execution of
this later increment is pending. These records are prerequisites, not admitted
metadata obligations or controller qualification.

Metadata qualification-input execution now begins its joint attempt before
31 fresh recovery commands in `qualification-sqlite-recovery`. A create-new
sidecar retains each actual mode/barrier/sequence and native/controller digest.
Independent source admission requires the complete ordered seed/kill/readback
chain for M0..M2, U0..U4, R0/R1 and the walkthrough, exact current input/assembly
snapshots, native argv/cwd, owned settled exit, barrier observations and nested
attempt timing. Pure command/barrier validators are shared without importing
SDK build orchestration into generic evidence. Safe native/source graphs and
their input document are atomically retained in history and linked from cases;
`recoverySourcesSha256` is taken from the independently imported proof set.

The actual-witness requirement remains unchanged. The eight control-only
recovery cases have no runtime UUID yet, so even corroborated controller graphs
retain `Incomplete`, not invented successful witnesses or weakened Attempt
validation. Metadata remains 71/22/9/0, artifacts 92/7/4/0, qualification false.
The missing graph API fails first; missing steps, foreign sequences/current
inputs/timing and consistently rewired wrong native input maps reject. All 386
local tooling checks pass with 17 explicit macOS-native skips.

Exact `d0b6bd3` run 40207993043 has a failed foundation job: 275 checks, one
`OwnershipInvalid` in release-publication retry, no skips. Its SDK and lock jobs
subsequently succeeded: 127 scopes and 1,818 actual witnesses, including the six
fresh qualification-input metadata scopes and four source parents. The overall
run remains failed and unadmitted. The ownership failure is not diagnosed. Both
bounded observers transiently failed TLS; a completed-job API stream recovered
only safe failure identities, without persisting raw logs. The foundational
runner now additionally retains at most four allowlisted repository-relative
source/line locations, never raw traceback text, private paths, locals or
exception messages. Its missing-location regression fails before implementation;
the canary projection passes afterwards. Native confirmation of the later graph/
location changes is pending. No ownership guard, control or task marker is relaxed.

The subsequent `d80f9cc` run 40208706531 failed SDK execution during metadata
recovery and its 276-check foundation job. Exact `7649a8a` run 40210363855 then
localized the same foundation failure to the barrier test's result-digest
assertion at line 479. Both the test and native recovery producer referenced
nonexistent `CommandResult.execution_sha256`; the executor exposes
`execution_record_sha256`. The portable regression uses the actual dataclass,
fails with the old attribute, and rejects absent or mismatched actual record
digests after correction. All 387 local tooling checks pass with 17 explicit
native skips. Corrected native execution is pending; these failed runs are not
admitted, and the earlier release-retry ownership failure is not explained by
this distinct defect. Evidence and harness contracts are unchanged.

The next controller-witness prerequisite is test-only
`MetadataRecoverySource` plus a package-only `MetadataRecoveryRuntimeTests`
fact. A closed current-run/group/attempt/root/input context declares exactly 65
files. Bounded reads hash the bytes actually consumed; all 31 ordered commands,
native/controller digests, immutable input references, settled exits, M/U/R
barrier timing and summary readbacks must agree before a create-new hash-only
packet is written. The positive model and four semantically inconsistent but
self-consistently rehashed graphs pass/reject as intended; the full SDK source
suite passes all 119 checks. These are modeled source checks, not native receipts.
The new package fact requires `HOARD_METADATA_RECOVERY_CONTEXT` and fails
explicitly if absent. It is not yet selected by category dispatch or independently
joined to case witnesses. Default admission rejects substituting an unrelated
valid SDK session for it. Package-mode compilation/native execution and complete
source/case integration remain pending; eight control-only cases stay incomplete.
No provider reference, public SDK API, package dependency, inventory, report
entity or diagram changes. Existing examples do not invoke this private fact.

The corrected producer at exact `b6b97c4`, run 40211472681, still failed its
279-check native foundation job at the barrier digest assertion, line 479.
Inspection of that exact source identifies the earlier expression failure:
`hashlib` was never imported in the Linux-only test module. The test now imports
it explicitly; the producer already imports it and its actual result-digest
contract remains repaired. Native execution of the import correction is pending.
The old line location alone did not prove which expression failed; the SDK's
separately projected AttributeError remains the evidence for the result-field
defect. No separate release-retry ownership repair or native success is claimed.

Exact `7dc1ac8`, run 40212543819, subsequently passes all 279 Linux foundations
without failures, errors or skips, including the repaired native barrier proof.
Both SDK diagnostics and lock replay fail with safe compiler code `CS0103`
during fresh candidate replay. Actual MSBuild evaluation reproduces the source
ownership bug: the new fact under `fixtures/conformance/Consumer/` is also
compiled by that separate consumer, which does not contain its decoder.
The fact now resides in `Hoard.Conformance.Tests/Native/` and the existing
non-package condition removes `Native/**/*.cs`. Evaluated compile items verify
that the fixture consumer excludes it, default SDK tests contain only the
decoder, and package-mode SDK tests contain both. All 119 SDK source tests and
the focused formatter check pass. Full package/native replay remains pending;
the failed overall run is not admitted. No package references or locks change.

The subsequent runtime-source integration now selects a seventh metadata scope
only for qualification inputs. It runs the package-only source fact through
fresh discovery/execution, with a create-new current context and pre/post native
snapshots of that context, recovery graph and recovery input document. Source
corroboration independently recomputes all 65 expected consumed-file hashes
from the executor-held 31-command graph, requires the actual runtime proof/UUID,
and verifies exact native command/settings/input maps, root ownership and nested
timing. The controller graph must precede that source command and remain inside
the overall joint attempt. Safe source packets/parents are retained atomically.

Only eligible SQLite cases with complete corroborated controls and that
independently parented actual source witness can pass. Eight modeled recovery
cases pass with the real modeled execution UUID; bare graphs, missing parent/
witness and rewritten consumed-file hashes reject or remain incomplete.
Diagnostic metadata stays at six scopes/134 witnesses and 71/22/9/0; the new
qualification-input execution requires seven scopes/135 witnesses and five
source parents, with a modeled target of 79/14/9/0. Actual native confirmation is
pending; no modeled UUID is admitted as a native receipt. All 388 tooling checks
pass with 17 explicit macOS-native skips. Full profile/QC work remains unfinished.

The next native-stall prerequisite retains the original executor command for its
expected deadline, with the actual test assembly and a create-new immutable
current-input document in the pre/post snapshot map. Previously post-input
verification ran only when no failure existed: a deliberately timed-out command
could therefore retain pre-input hashes without a post-containment check. A
settled `DeadlineExceeded` now gets a fresh at-most-five-second verification
window, still capped by the profile deadline and cleanup reserve. Restored-byte
rewrites or other changed inputs become `InputChanged`, not the expected timeout.
Retained/live groups and unrelated failure handling are unchanged.

The native-stall producer independently joins its exact arguments, working
directory, input map and controller bytes to the executor-held original record,
requiring the explicit expected deadline. Normal source corroboration still
requires `None`; it cannot inherit this exception. Its create-new hash-only graph
remains non-qualifying and is not yet imported as MP-37 case evidence. Portable
regressions fail first for omitted native snapshots and missing expected-deadline
corroboration, then pass for all three namespaces. The existing Linux watchdog
regression now checks post-timeout reads and rejects changed/restored inputs;
that native extension is explicitly skipped on macOS, not claimed executed.
All 388 tooling checks pass with 17 native skips; exact Linux replay is pending.

The subsequent MP-37 integration independently consumes that five-file native
stall graph through the concrete owned-run authority. Exact current input bytes,
assembly/package, original native record, argv/cwd/input map, expected deadline,
retained guards/cleanup and joint-attempt bounds must all agree. The pure stall
validator is shared with production of the diagnostic packet, not reimplemented
in the category backend. A fresh qualification stall now runs after joint begin,
before recovery commands and all runtime scopes; either control failure
interrupts the joint attempt and cannot reach admission.

MP-37 retains its two frozen actual runtime witness IDs plus the corroborated
control proof graph. The recovery fact's UUID is used only for previously
control-only cases, never copied into an already-witnessed unrelated case.
Missing either original witness remains incomplete. Final atomic admission
requires both native/recovery graphs, and the summary's native graph digest is
taken from actually imported proofs. The seven scopes/135 witnesses/five source
parents are unchanged; the new modeled metadata target is 80/13/9/0. Exact Linux
confirmation is pending. Missing graph admission and unrelated source-UUID
attribution fail in red before repair. All 391 tooling checks pass with 17 native
skips; the full stage and other controls/QC graphs remain unfinished.

A further red regression demonstrates that rehashing a schema-valid replacement
producer packet could otherwise escape the original command/control linkage.
Expected native output paths are now predeclared only for recorded recovery
commands, bounded together with input paths to 16, inside retained `proofs/`,
disjoint from inputs and absent before launch. Only after exact settled
containment does the executor seal regular single-link owned outputs read-only,
hash their actual bytes and retain those hashes in its original native receipt.
The input/output post-check shares the same bounded deadline. Symlinks, hard
links, directories, unsafe paths or changed identities reject without touching
outside sentinels. Native-stall source admission requires that exact output map,
so a self-consistent replacement producer/graph now rejects. The extended
watchdog exercises actual timeout output capture on Linux; its local skip is
explicit, while the filesystem sealing/substitution regressions run portably.

The MP-43 ownership increment runs `hold-owner-probe` and `reopen-owner` in a
fresh qualification-only namespace, after joint begin and before runtime
scopes. The first fixture owns SQLite, starts a distinct actual process, bounds
and checks its rejection output, retains the closed PID/start-hash probe packet,
and only then exposes owner barrier 30. The supervisor kills the owner and
observes settled containment before sealing that packet; the second command
successfully reopens the exact database. Existing legacy modes are unchanged.
Independent seven-file graph admission reconstructs both native commands,
immutable assembly/current inputs, distinct probe/owner identities, original
output bytes and joint timing. Rehashed probe substitution and absent readback
reject. MP-43 uses only its original frozen runtime witnesses, never the
unrelated recovery fact UUID. The summary requires `ownershipSourcesSha256`
from imported proofs; any ownership-control failure interrupts joint admission.

All 393 tooling checks pass with 17 explicit native skips. Fresh standard
`metadata_evidence.prepare_packages(..., False)` completes its locked build
replay with eight packages, and fixture whitespace verification passes. A real
separate-process rejection, exact owner kill and reopen also pass on macOS,
explicitly without Linux confinement or qualification. The modeled metadata
target is 81/12/9/0 across unchanged seven scopes/135 witnesses/five parents;
exact Linux confirmation and the rest of the implementation stage are pending.

MP-46 next builds the existing package-only metadata consumer in the native
SDK path and snapshots its runtime with current inputs. The common
`MetadataConsumer.cs` assertion body remains unchanged. An opt-in safe-event
mode accepts only explicit `sqlite|memory` and an absolute owned database path;
legacy environment selection/output is unchanged. One immutable binary runs
both compositions in distinct fresh stores after joint begin and before
runtime scopes. Independent six-file authority requires both exact native/
controller records, argv/cwd/current-input maps, the same consumer assembly
and nested ordered timing. A missing/reordered/relabelled composition rejects;
the final summary requires imported `consumerSourcesSha256`. MP-46's original
runtime witnesses remain mandatory. Missing authority fails before repair.

All 395 tooling checks pass with 17 native skips. Fresh standard locked metadata
package preparation completes with eight packages, runtime package byte checks
pass, and the identical consumer runs both explicit and legacy modes on both
providers on macOS. Consumer assembly/common assertion hashes stay unchanged
across all four executions. These are non-qualifying diagnostics, not Linux
containment. The modeled target is 83/10/9/0; seven scopes/135 witnesses/five
parents are unchanged, and exact Linux/full-stage confirmation remains pending.

Build-path review found that prepared inspection already builds this consumer.
The SDK path now reuses it rather than allocating its create-new derived lock
twice, and verifies runtime package bytes immediately after that existing
build. All 134 focused SDK tooling checks pass; no lock overwrite is permitted.

MP-47 now stages only copies of the already sealed pre-F-05 marker/runtime,
replacing Abstractions/Core/Hosting with current package-consumer images.
Retained binaries and recipes are never rebuilt or modified during candidate
execution. The staged runtime joins immutable input capture before execution.
A narrow recorded-recovery output mode recognizes only the exact original
`metadata-marker-compatible` line, projecting a closed safe event without
persisting raw output or changing the frozen binary. Other lines reject.
Independent four-file authority checks the exact baseline revision/descriptor,
original marker/runtime metadata, current platform image hashes, full native
input map, argv/cwd and joint-attempt bounds. The frozen runtime witnesses stay
mandatory; `binarySourcesSha256` comes only from imported proofs.

All 399 tooling checks pass with 18 native skips. Missing projector/authority
APIs fail before repair; marker/current-image substitutions reject. Staging
preserves original bytes and replaces only the three platform images. A real
unchanged marker built against revision
`10ce78851b97b02bd83a8ef7da7ffdc2381d6519` also executes successfully against
current platform assemblies on macOS, with all retained files unchanged.
This is explicitly non-qualifying, not a Linux containment or temporal-baseline
receipt. The modeled metadata target is 85/8/9/0 across unchanged seven scopes/
135 witnesses/five parents; native/full-stage gates remain pending.

MP-48 now runs the complete unchanged original metadata verifier suite in three
separate commands: baseline, the original failed-case-refusal mutation, and
repair of that same private adapter to original bytes. A fresh unfiltered loader
prevents inherited runner filters from narrowing the inventory. Existing bounded
diagnostic handling suppresses raw exception text; named assertion failure,
zero errors/skips/diagnostic bytes, complete unchanged test inventory and exact
source restoration are required. Create-new read-only packets/source snapshots
are executor-declared outputs, not caller-supplied success flags.

Fourteen-file independent authority checks all ten actual interpreter source
inputs, original command/output records, exact argv/cwd, ordered settled commands
and joint bounds. Separate SQLite/memory runtime facts read and hash the complete
graph and emit distinct original execution UUIDs. Original source inputs and all
snapshot bytes remain unchanged; the frozen 192 inherited keys are untouched.
Missing authority fails in red; rehashed setup failure and borrowing recovery's
UUID also reject. Its initial modeled target is 87/6/9/0 with eight scopes/137
witnesses/seven source parents, not a native or qualifying receipt. A subsequent
qualification joint-plan regression reaches an unguarded inventory lookup for
the QC-only `none` binding. Only actual provider bindings now receive source
facts; the complete joint plan includes `none` without inventing a source fact.
No native inventory admission is inferred from local source/controller checks.

QC-06/07/08 now derive from independently fixed complete logical,
uncertainty/ownership and schema/recovery bases for both metadata options.
The joint history composes only freshly admitted same-sequence case attempts
inside the same joint bounds, retaining original witness UUIDs and every
runtime/controller/source proof hash. The report model independently recomputes
the same unions and exact catalog witness sets. Cross-binding proof links are
permitted only for these three exact QC keys; ordinary dimension matching and
all other QC gates remain unchanged. All nine frozen memory durability
exclusions must match exactly, with no invented durability execution. Diagnostic
mode never promotes a QC. Missing controls stay incomplete; assertion failures
remain failed, and histories preserve failed attempts. A retry exceeding the
existing 128-proof collection bound fails explicitly as `OutputLimitExceeded`;
neither earlier failures nor evidence are truncated. The new modeled target is
90/3/9/0 across eight scopes/137 witnesses. The initial modeled seven-parent
expectation is superseded by the actual six-parent native receipt below.
QC-02/04/05 and full profile/stage completion remain pending.

`python3 -m unittest discover -s tests/tooling -q` passes 406 checks with 18
explicit native skips. New state/report tests first fail on missing QC
composition and cover same-attempt proof unions, diagnostic refusal, missing
recovery controls, retained failure history, bounded retries, shortened/foreign
witnesses, missing cases, changed timing and unauthorized exclusions. Their
native-import seam is explicitly modeled, not actual native execution.
Frozen inventory/SDK catalog checks and `git diff --check` pass; no C# source,
package references or locks change in this increment.

The exact corrective quality checkpoint `ee1e7358a71d39294d911f369c49e4db40dc5ea9`,
[run40224149195](https://github.com/Stonefly-Labs/Hoard/actions/runs/40224149195),
independently passes all three Linux jobs, 298 native foundations with zero
failures/errors/skips, 13-lock/18-package fresh replay and 129 aggregate scopes/
1,821 exact witnesses. Qualification-input metadata has eight scopes, 137
witnesses and six source parents at 90 Passed/3 Incomplete/9 NotApplicable/
0 Failed. Both inventory facts execute in one joint scope with distinct actual
UUIDs and one shared parent; the initial observer's seven-parent expectation
was a model error, not a failed CI job. Correcting that exact expectation leaves
all other strict admission checks intact. Inputs
`50523a4bf570d1bd8f685f45838051b98f30897138b3b29e7a7e3af1ec5e78c0`,
results `87ba280b1bec3891f2b1a55abde3af23c446967e82e61a9d10afa7da9551c57b`,
parents `70e497c26b681d714341741dae271572cbaff5c190e28d9e10c826a01fdaa9be`.
All six independent recovery/native/ownership/consumer/binary/inventory graph
digests are distinct. This admits MP-48 and QC-06/07/08, not a complete profile.
Earlier exact `a19d2a99ff2fb07f0c8e399fac8eb31188e1fff2`,
[run40222425942](https://github.com/Stonefly-Labs/Hoard/actions/runs/40222425942),
passes 294 foundations and lock replay but fails the SDK's qualification joint
plan with `KeyError` for the QC-only `none` binding. Safe traceback attribution
confirms the catalog selector already repaired in `ee1`; no inventory admission
comes from that failed run. The separate older MP-19 cause remains unknown.

Artifact source read-site capture is now requested only by the actual native
artifact diagnostic controller, never legacy harness or discovery execution.
Its fixed context selects all sixteen original crash/retention/transfer facts
and their one-to-three exact source files. Original assertions remain unchanged.
The optional test-only `HOARD_ARTIFACT_SOURCE_CONTEXT` hook validates a closed
<=1 MiB context, exact owned absolute paths and identities, no symlink ancestors,
<=16 KiB actual source files and a five-second hook budget. It checks the bytes
actually asserted/serialized against the corresponding file and emits one
create-new hash-only packet per fact. Missing/malformed requested context fails,
while absent context preserves legacy behavior. Parent diagnostics reselect
current bytes, require exactly sixteen matching packets, bind original runtime
UUIDs/proofs, retain immutable hash-only copies and recheck their consumption
receipt. Twelve immutable native inputs include the original context, actual
crash runner, current transfer summary and four transfer proofs. The source
authority still rejects artifact controller qualification: original transfer
controls and independent full source admission remain
unbuilt. Diagnostic 92/7/4/0 is unchanged; no borrowed old run qualifies it.

The original capture publisher additionally aggregates original serialized
packet hashes under a bounded per-context lock. Only the complete selected
source set emits `proofs/artifact-source-seal-ATTEMPT.json`; partial publication
emits no index, and replacing an earlier packet cannot change its retained
original hash. The native ordinary command declares this one previously absent
output alongside twelve immutable inputs, preserving the combined sixteen-file
limit. Existing settled-exit, regular/current-user/no-link output checks seal
the index read-only and pin its original bytes in the executor-held record.
Independent source admission reparses a closed, duplicate-free index, requires
the exact original packet-name/hash set and identities, and joins its raw hash
and immutable context hash to that original ordinary execution. C# JSON order
need not equal Python canonical order. Consumption and source-parent checks
revalidate the same seal; rehashing current packets/index cannot replace the
executor's original output hash. Legacy/discovery paths declare no such output.
Cleanup and unmeasured transfer commands still cannot declare outputs;
ordinary/recovery and the measured-only transfer mode below retain the same
ownership, count, path and settlement safeguards.
This is implemented diagnostic output authority, not complete artifact source
qualification or fresh Linux acceptance.

Each actual native paced transfer now declares its immutable runner assembly
and a create-new current-input document as original execution inputs. The
controller checks the exact original executor-held record against argv/cwd,
run/root, input map and the original controller bytes; the returned command
digest must equal that record. A read-only per-transfer `native-execution.json`
retains sequence, run/root/group/input and controller/execution digests without
private paths or raw output. Foreign runs/assemblies, substituted command-result
digests and post-record controller rewrites reject before a native receipt is
written. Provider/size selectors are validated before path construction.
Legacy non-native diagnostic adapters retain their existing behavior and no
native receipt. The unchanged pure measurement validator now lives in the
shared source module, not the SDK orchestration layer. The Linux process
protocol regression additionally checks actual original input/controller
hashes; its small handshake child is not a real 256 MiB/4 GiB transfer.
The subsequent original-output increment supplies an optional sixth transfer
runner argument only in safe-event mode, requiring an exact absolute proof
path. The original bounded JSON is written create-new both to the unchanged
legacy store location and to that explicit proof path before settlement.
Native measured commands predeclare only the latter as an output; after actual
owned exit the existing regular/current-user/no-link checks seal its original
bytes read-only. Two immutable inputs plus one output retain the combined
sixteen-file bound. Unmeasured transfers/cleanup cannot request output sealing.
Controller admission joins the producer's raw hash to the original output map,
not a late canonical reserialization; even semantically identical replacement
JSON rejects. The per-transfer native receipt retains `producerSha256`.
Non-native adapters preserve their original five-argument behavior.

The actual TransferRunner compiles with zero warnings/errors after a verified
private lock derivation and required restore; tracked locks/references remain
unchanged. Its scoped whitespace check passes. Actual local 256 MiB transfers
on both options produce byte-identical legacy and explicit proof files with
correct PID/run/provider/count/digest/pacing values. These are bounded local
diagnostics without native-containment or OS-peak assertions, not the full
4 GiB/Linux qualification chain. The original native-output protocol regression
and all independent complete transfer/control authority still require replay.
An independent transfer source reader now selects the actual fixed runner
suffix, exact provider/qualified-size namespace paths, immutable original
inputs, read-only recipe/controller/producer/composite and original executor
record. It independently recomputes the generated-byte expectation, reuses the
same pure complete producer/measurement validators, requires exact original
argv/cwd/input/output/control maps and reconstructs the closed recipe. It reads
the original explicit sequence even after later commands; producer labels and
rewired current hashes do not replace executor-held bytes. Both initial
source-consumption ingestion and its parent recheck require all four graphs.
Missing or changed graphs propagate; no capture/index receipt is admitted as a
fallback. Shared runtime assembly hashing is reused by metadata and artifacts;
the generic source layer never imports SDK build orchestration.
Original crash/state/readback, retained-child and UUID/exit validators now live
in that same source layer and are reused by SDK orchestration. Five function
ASTs match exactly, excluding only the lazy artifact-evidence import. Missing
shared APIs fail the three existing adversarial suites before extraction; their
full vectors pass afterwards.
The private `qualification-artifact-transfers` namespace now requires artifact
qualification inputs and uses distinct stores/cache/proofs/input documents.
Controller selection, measured production, source recipes and source contexts
share this gate. Diagnostic/category receipts or foreign modes/profiles cannot
substitute; all three namespace variants retain the same measurement and
original-input/output substitution negatives. These are local unit models,
not actual qualification-origin transfers or an opened qualifying backend.
Native qualification-origin transfer controllers now recheck all four graphs
against their actual common start/end window before publishing a summary.
Sequences must increase, transfer windows must not overlap, and source proof
paths must be disjoint. The independent reader returns immutable original
proofs and seven transfer-control role hash sets; this does not change any
case status. Early/late, overlap, reordered sequence, reused proof path and
missing-source cases reject. No summary is written after joint-source rejection.
All seven artifact QCs and artifact qualification remain closed: actual fresh
native qualification execution and complete crash/retention source
corroboration still need completion.

Exact source-index `a9e75c848c3572a035a7317a6a20b8e89540cd0f`,
[run40228504830](https://github.com/Stonefly-Labs/Hoard/actions/runs/40228504830),
passes SDK diagnostics and locked package replay but fails one of 302 native
foundations, with zero errors/skips. Safe source attribution resolves exactly
to `test_conformance_execution.py:410`: the new test compares the correct empty
`frozenset` returned by `live_children()` to an empty tuple. The correction
asserts emptiness, preserving the actual original settled-record and ownership
checks. This is a demonstrated assertion-shape error, not a runtime ownership
repair or overall native admission. Pending `055abe1`/run40229217713 was
superseded before execution by the producer checkpoint and grants no evidence.

Exact `cf4a70f278d9e5542cc344e9cd4aa77d78273b40`,
[run40227343651](https://github.com/Stonefly-Labs/Hoard/actions/runs/40227343651),
now independently passes all three jobs, 300 native foundations without
failures/errors/skips, 13-lock/18-package replay and 129 aggregate scopes/1,821
witnesses. Artifact diagnostic inputs
`337cabdce73202d4264349233a71bf7fd8b262792b9fcfc63f17b7abaaba63fb`,
results `9f9eb9ef391d4f57c727ced04d9e235ec89fe4df70e49fa1ea79e2dd25251e58`,
three-source-parent digest
`ab689a81d9e0131fff30bb4997568568273a89282eb2d368b88e524d1f67c351`;
states remain 92 Passed/7 Incomplete/4 NotApplicable/0 Failed. Qualification-input
metadata remains 90/3/9/0, eight scopes/137 witnesses/six source parents, with
inputs `8ebf690eafddce0036de0e678943b12e3b504b4c599ade06e8b4c6e9f62d9559`,
results `22fb257f87af3056b9e76095b45c6c6983dad577933edc4d411cc1a8ac9337f4`.
This admits original byte capture only, not the later output-seal or native
measurement-record increments. Their exact native replays remain pending;
neither profile qualifies.

The next controller-source increment independently reconstructs all six
crash/state/recovery-error triples and six retained-child packets, requiring
the exact 24-file inventory, distinct child run IDs and empty recovery errors.
SDK receipt generation and parent consumption share this reader. Independent
controller admission reconstructs the four original qualification transfers,
sixteen consumed packets, summary/consumption/external receipts and original
output index: 44 immutable source proof files in its complete graph model.
Delayed admission selects the original explicit controller sequence rather
than the latest command. Native factory/history admission additionally binds
the exact owner/manifest/settings, twelve input hashes, sole index output,
argv/cwd, original settled command and nested witness times. Rehashed outer
parents cannot conceal changed inputs, outputs, invocation or witness windows.

SDK diagnostics now prepare/recompute distinct qualification inputs for both
categories and schedule fresh artifact qualification-origin transfers inside
the joint attempt before its scopes. Runtime settings, declared inputs, source
contexts and parent rechecks use that same mode-derived namespace. Transfer
or scope failure retains an interrupted history without publishing success.
The new `artifactQualificationAdmission` diagnostic summary remains
`qualification: false`; artifact QCs and full profile/evaluator work are not
completed by this source join. Actual Linux execution of this increment is
pending. Safe projection now attributes run40230791595's sole foundation failure
(303 tests, zero errors/skips) to its original source line 413: the same empty
frozenset-versus-tuple assertion already fixed in `72899cf`. Its SDK/lock jobs
succeed, but that overall failed snapshot is not admitted.
Run40232608162 passes foundations/locks with SDK execution still running
at observation, not an overall admitted snapshot.

The transfer/durability quality checkpoint reuses the metadata algorithm with a
catalog-owned per-category basis. Artifact QC-10 requires both bindings'
AS-11/12 cases and their original controller source parents; QC-11 requires
Local AS-41..44 and exactly four empty-attempt simulation exclusions on Object.
Missing source authority keeps inherited source-sensitive cases incomplete.
Report admission independently recomputes complete same-attempt bases, exact
runtime/proof links, bounded intervals and exclusions. Wrong/shortened/foreign
or borrowed provenance rejects; failed retries remain visible. Diagnostic mode
and QC-03/04/05/09/12 remain incomplete. Actual native execution of this
increment is pending; these local models are not qualification evidence.

Current QC-09 composition covers all 84 applicable inherited logical
case/binding rows (AS-01..10,13..40,45..48). Their complete original current
attempts and runtime observations are retained in a canonical private basis
receipt, never truncated to the 128-direct-witness limit. The complete model
has 217 nested observations and ten catalog-selected source anchors. Public
report admission independently reconstructs the entire receipt and requires its
exact proof-path digest; outer projections cannot omit/replace cases, source
anchors or earlier attempt bytes. Metadata and QC-10/11 retain their direct
composition. Case/attempt witness/hash bounds are unchanged.

History retains immutable basis bytes across retries and accounts for their
bytes/files before atomic commit, including cumulative profile proof budgets.
SDK recording writes create-new/read-only originals and checks existing bytes,
permissions and proof hashes before publishing a history. Its non-qualifying
summary adds `qualitySourceCount` and `qualitySourcesSha256` only when such
receipts exist. Missing/changed/mutable receipts and budget overflow reject;
failure retains incomplete/failed history without a partial passing basis.
QC-03/04/05/12 and full profile/evaluator acceptance remain incomplete; actual
Linux execution of this increment is pending.

Exact `5f81b926ca7add6845cb19cccba200b668eb0831`,
[run40232608162](https://github.com/Stonefly-Labs/Hoard/actions/runs/40232608162),
independently passes all three jobs: 306 native foundations without failures/
errors/skips, 13-lock/18-package replay and 129 aggregate scopes/1,821 witnesses.
Metadata qualification inputs/results:
`67751d46b2bbb9921c47d37517d40cf5ac71a5e039314bdd7a740ecef34969dd` /
`9a19332e8a626b9166f09100a897d309ca1eacf284392d6bc3f183d364d18f75`,
eight scopes/137 witnesses/six source parents, still 90/3/9/0.
Artifact diagnostic inputs/results:
`c5fac58965e91b057f49abe1ee2ce4e770824a5a100be182f99c8250f89f5a37` /
`bd5a427e736b27e235a62441782e99ca056ec8fd410f97f2846c81f5c45d8d2b`,
six scopes/227 witnesses/three source parents, still 92/7/4/0.
This admits original native index/output and transfer-source graphs in the
existing diagnostic execution, not later complete controller/QC joins or fresh
qualification-origin transfers. Superseded pending 97a/run40234467588 grants no
native evidence. Exact f1ba/run40235078726 passes 311 native foundations and
the lock job but fails SDK diagnostics at the qualification-origin artifact
`controller` with `WitnessMissing`. That snapshot
is not admitted. Category control/scope/admission failures now emit at most four
static source-role/line locations, matching the foundational safe diagnostic
pattern without retaining raw traceback text, exception messages or frame locals.
The original safe projector omitted the two new qualification phase labels;
their independently projected presence corrects the earlier diagnostic-phase
attribution. A focused regression reproduces premature ordinary session admission
for the source-only artifact controller. It now uses validated transport
inspection before its unchanged mandatory source reconstruction/parent checks
and final native history admission, matching inspection/metadata controllers.
Ordinary/diagnostic session admission is unchanged. Actual Linux replay of the
repair remains pending.

Category execution/discovery manifests now select the provider archive for each
binding rather than using the SDK package as every witness's package identity.
The common frozen-slot selector requires the exact captured binding/category/
provider archive and inventory hash; foreign or changed assignments reject
before launch. Mixed scopes retain both actual provider archives and each exact
entry's association. Independent native source admission reselects that complete
set and checks each entry, while report admission keeps its existing exact
binding/package hash equality. Wrapper assembly and SDK provenance remain
separate captured inputs. Twelve scope assertion reds and both distinct-package
report failures reproduce the old mismatch before repair; corrected models and
cross-provider borrowing negatives pass. These models do not replace native
execution or complete qualification acceptance.

Category histories now retain all safe runtime witnesses and proof links in an
original read-only, bounded file with an independently returned `historySha256`.
Runtime proof keys name the actual `runtime-<attempt UUID>/proof-<execution
UUID>.json` files; bytes and execution identities are unchanged. After actual
post-input recapture and immutable-input comparison, SDK completion admits the
public report shape, exact frozen final keys/exclusions, original history hash
and every retained proof file's current hash through bounded descriptor-based
input reads. Missing/changed/mutable histories, shortened cases, changed inputs
and substituted proof bytes reject before writing a report. Free-space variation
retains its actual post-input digest without fabricating equal measurements.
The four diagnostic/qualification-input category reports explicitly remain
`Incomplete`/`qualification: false`, with no resource-release or full-baseline
claim. Final summaries add `reportState`/`reportSha256`; terminal SDK failures
retain only the same bounded static source locations, never raw traceback text.
This wires real report admission into the next Linux replay; it does not finish
the profile evaluator or remaining QCs.

QC-12's independent catalog and embedded SDK resource now require the exact
32 `AuthorityIntegrationTests` parameter rows: all four pairings times eight
consumers. Diagnostic orchestration uses the same immutable selection. Focused
catalog/scenario assertions first reproduce the missing witness set; source-row
parity, missing-pairing, missing-consumer and single-row/foreign-row negatives
then pass. Cross-binding quality rows remain outside ordinary provider scopes.
No existing diagnostic execution becomes qualification evidence: fresh
qualification-origin integration source admission was still unbuilt at that
catalog checkpoint.

Exact `3166f667bf70a0756f7b2a8c42ec35034d6fc35b`,
[run40237666479](https://github.com/Stonefly-Labs/Hoard/actions/runs/40237666479),
passes 315 native foundations and locked replay but fails SDK diagnostics.
Its bounded safe locations independently attribute `WitnessMissing` to
`scripts/conformance_evidence.py:1619`, the ordinary source-only admission guard
already addressed by controller routing repair `13aecdf`. The failed snapshot
is not admitted; this attribution does not establish native repair success.

Catalog checkpoint validation: all 427 tooling checks pass with 19 explicit native skips;
all 133 source SDK checks pass. Focused formatting, frozen inventory, SDK catalog
and whitespace checks pass. The preceding byte-capture checkpoint compiled
the original artifact package-acceptance project with freshly rebuilt SDK,
metadata/artifact providers and adapters
against a private prepared lock; no tracked locks change. Initial compile
attempts correctly reject stale retained fixture archives; rebuilding the
matching graph resolves them, without changing APIs. Removing only this task's
temporary duplicate restore caches restores the existing 24 GiB scratch gate;
the gate is not reduced or mocked. New source-capture tests first fail on the
absent API before implementation. These local checks do not execute fresh large
transfers, establish native artifact admission or finish the implementation stage.
Provider/contributor/deployment guides, examples and diagrams are unaffected:
there is no new supported command, provider API, package dependency or deployment.

### Fresh authority-integration source admission

Qualification-only `original-integration` now executes the complete 32-row matrix
in the package-only Consumer with primary case QC-12 and actual Local/Object
binding archives. Each original row emits its actual metadata, artifact-store
and composition loaded-contract images before the unchanged assertions. SQLite
prerequisites are checked before launch. The exact six-image manifest and
original context are immutable execution inputs, not provider-selected claims.

The independent native factory reconstructs metadata/artifact/package image
assignments and the full source receipt, then joins the executor-held ordinary
command record, owner, RunInputs, manifest, settings/encoded context, fixed
argv/cwd, complete input map, successful exit, no live children and bounded
command/witness times. Source-parent publication and history admission are
atomic for all 32 rows. QC-12 consumes only its current witness IDs and one
native source parent; missing parents, incomplete rows, retiming and borrowed
earlier-attempt executions reject or remain incomplete. Failed modeled attempts
remain retained across passing retries. No existing diagnostic is promoted.

`python3 -m unittest discover -s tests/tooling -v` passes 433 tests with 19
explicit native skips. `dotnet test tests/contracts/Hoard.Conformance.Tests/Hoard.Conformance.Tests.csproj --no-restore --verbosity quiet`
passes all 133 source SDK tests. Scoped C# whitespace, frozen inventory, embedded
catalog and whitespace checks pass. A private local package-only restore/run
executes all 32 actual integration cases with three image observations each:
all pass without skips. This is non-native validation; the unchanged-head Linux
retry below subsequently admits the integration source path. No tracked lock, public provider API,
production dependency or supported command changes; provider/contributor/
deployment guides, examples and diagrams are unaffected.

Exact `a5fe97e`, [run40238458550](https://github.com/Stonefly-Labs/Hoard/actions/runs/40238458550),
independently passes all three Linux jobs: 317 native foundations without skips,
13 locks/18 packages and 135 aggregate scopes/2,048 witnesses. Metadata's native
qualification-input batch has 8 scopes/137 witnesses/6 parents and 90 Passed,
3 Incomplete, 9 NotApplicable, 0 Failed. Artifacts has 6 scopes/227 witnesses/
3 parents and 95 Passed, 4 Incomplete, 4 NotApplicable, 0 Failed. This establishes
the earlier controller-routing and QC-09 basis repairs, not this fresh
integration scope or the newer public-report admission gate. No task or
reviewer-owned checklist markers advance; the implementation stage remains open.

### Fresh named category mutation source pairs

Qualification-only `mutation-repair` scopes now execute each category's two
faulty bindings before their two corrected bindings in the same package-only
Consumer. Both sides pin the same six images, actual provider archives, SDK and
immutable RunInputs. The negative must exit one with both fixed named assertion
failures; a build/setup error cannot substitute. The corrected side must pass
unchanged consumers. No old diagnostic execution is promoted.

The independent native factory reconstructs the full negative manifest,
re-ingests its original logger transport and checks original executor-held
argv/cwd/input files, settings, owner, exact identities/frames, settled exit and
ordered command/witness bounds. Rehashed replacement records are not authority.
Its retained negative packets join the fresh corrected parent atomically;
QC-04 requires the complete current pair and one parent, with no prior-attempt
execution reuse. Focused models exercise actual producer parent publication
and independent factory admission, including a coherently rehashed foreign
assertion/setup failure. These are modeled rejection checks, not native passes.

`python3 -m unittest discover -s tests/tooling -v` passes 437 tests with 19
native skips. An initial run hit the existing real descendant startup timing
assertion; its unchanged focused rerun and full rerun pass.
`dotnet test tests/contracts/Hoard.Conformance.Tests/Hoard.Conformance.Tests.csproj --no-restore --verbosity quiet`
passes 133 tests without skips. Frozen inventory, embedded catalog and patch
whitespace pass. Native pair admission was pending at that checkpoint and is
now established at exact `58a9495`; no task/checklist
markers advance. A separate fresh private package-only restore against the
current SDK executes all eight actual mutation rows: four corrected passes and
four faulty failures, each in its fixed shared assertion frame. This is local
non-native validation, not native parent admission. Its snapshot and temporary
lock are isolated from the earlier authority-check feed/cache/lock.
README, plan and evidence/matrix contracts are updated.
Provider/contributor/deployment guides, examples and diagrams are unaffected:
no public API, dependency, supported command or deployment behavior changes.

Exact `a83380c`/run40240608803 independently passes all three Linux jobs:
319 native foundations without skips, locked replay and 135 aggregate scopes/
2,048 witnesses. The four public category reports are admitted as `Incomplete`;
metadata remains 90/3/9/0 and artifacts 95/4/4/0. This predates fresh QC-12/QC-04
admission. Exact `9a5ebdb`/run40243784950 attempt one passes 325 foundations and
locked replay, but its SDK job fails the earlier MP-46 configured-selection
wrapper with `UnknownDiagnostic` before reaching the new QC-12 scope.
Only that failed job was retried at the unchanged head. Attempt two now
independently passes all three jobs: 325 foundations without skips, 13 locks/
18 packages and 136 aggregate scopes/2,080 witnesses. Its fresh QC-12 scope
admits all 32 actual integration rows with one native parent. Qualification-
input artifacts now has seven scopes/259 witnesses/four parents and
96 Passed/3 Incomplete/4 NotApplicable/0 Failed; metadata remains 90/3/9/0.
Artifact input/result are
`7f0e5b5c7b5e4b9b6b583d9711e35bf38c52812d76bd7b728f5c4732f93cea0a` /
`f940a01b256c543ccdc58fcabc35317d0f2cb70d143400118f0fa5fd9a40dd93`.
All four public reports remain `Incomplete`. The unchanged MP-46 row passes on
retry; no timing or other cause is established. This does not admit the newer
QC-04 path at `426511a`/run40246023608. That run subsequently passes all 329
native foundations without skips and locked replay, but its SDK job fails
fresh metadata mutation source reconstruction at
`conformance_sources.py:172 -> _readonly:56`: logger witness files were not
sealed read-only. No new source parent is admitted; no raw CI log is retained.

The supervisor now seals validated runtime source witnesses, completion and
proof files only after the owned child is settled. Before changing permissions
it rechecks that file bytes match the already inspected transport. Live
children or changed bytes reject; the independent readonly guard is not weakened.
An intended-red regression reproduced the missing seal, then passed the repair,
including both negative and shared-consumer scopes and live/changed-output
rejections. The full 439-check tooling run passes with 19 explicit native skips;
frozen inventory, embedded catalog and whitespace checks pass. Fresh Linux
repair admission is now established at exact `58a9495`, recorded below.
No consumer assertions, budgets, C# or locks
change, and this observed failure is not attributed to timing.

### Fresh shared metadata SDK consumer source control

Metadata qualification-input batches additionally execute the current F-07
package-only Consumer under a closed private `metadata/shared-consumer` scope.
The immutable catalog selects all 132 exact rows and expected origin counts;
both actual bindings retain their original `full-metadata-binding` case context.
The older F-05 metadata Consumer remains a separate MP-47 control.

The launcher captures all six Consumer/SDK/provider/binding images as immutable
command inputs. Independent source admission reconstructs the complete manifest
and re-ingests original readonly logger witnesses, proofs and completion using
independently selected role/image assignments. Exact per-row origin counts,
binding descriptors, loaded packages, instance consistency and reopen lineage
must match. The original executor-held record and readonly native record,
execution receipt, owner, full input map, fixed settings/argv/cwd and settled
command/witness bounds must agree; rehashing a replacement record is not authority.
Both the Consumer and frozen metadata wrappers must use identical shared SDK
image bytes with correspondence to the same admitted SDK archive. The wrapper
SDK is additionally captured in the original native input map; a changed or
unpinned wrapper SDK rejects. An explicit intended-red regression reproduced
the earlier missing check before the source and command-boundary repair.
The retained graph is `proofs/qualification-metadata-shared-consumer-native-executions.json`,
also exposed as `sharedConsumerSourcesSha256` in the metadata diagnostic summary.

These 132 rows remain private source-control transport, not public category
witnesses. The 128-witness case bound is unchanged. QC-02 stays `Incomplete`
pending complete frozen-wrapper/common-consumer extraction and parity evidence;
source presence or a passing marker Consumer cannot substitute.
`python3 -m unittest discover -s tests/tooling -v` passes 439 checks with 19
explicit native skips. The full source producer/factory regression rejects
coherently rehashed missing origins, foreign descriptors/images, wrong case
contexts, duplicate sessions, missing rows, relabeled manifests and replaced
or incorrectly scoped commands/settings. Frozen inventory, embedded catalog and
whitespace checks pass. Exact `58a9495` now establishes fresh Linux admission
of this control, recorded below.
That source-control checkpoint needed no C# or lock changes; source SDK results
above remain from the prior checkpoint.
README, plan and evidence/matrix contracts are updated. Other guides, examples
and diagrams are unaffected: no public API, supported command, production
dependency or deployment changes. All unchecked tasks/checklists stay unchanged.

### Package-only hook rejection before factory dispatch

The existing metadata `admission` rows and artifact `PublicationBoundary` rows
exercise missing-hook admission through the actual packaged observed-session
entry points, not only direct declaration validation. For each mandatory
logical hook, a probe copies the actual binding declaration except that hook;
its factory throws a different exception if dispatched. The row requires the
exact `BindingInvalid` argument rejection, zero factory calls and no allocated
resource. Metadata tests both ordinary and legacy entry points.
Missing bindings must reject with the named `binding` argument before
dereference. Each hook omission runs both with the actual capabilities and
with a claimed logical exclusion (`exclude:MP-21` or `exclude:AS-15`). These
claims cannot turn mandatory logical hooks into optional/durability omissions.
An isolated fresh-package replay verifies three SDK-only mutations: missing
mandatory-hook validation, an early return for claimed logical exclusions, and
missing null-binding validation. Each produces exactly four named assertion
failures and 114 other passes without skips. The unchanged SDK passes all
156 metadata/artifact binding rows without skips. All trials use identical
Consumer sources, freshly packed current dependencies and isolated caches/locks;
these are local diagnostics, not native qualification.

After all negatives, the same row opens the unchanged actual binding and runs
its existing common consumer with its original typed origin. The independent
test expectation lists mandatory faults rather than obtaining them from the
provider or the admission implementation. No identities, origin counts,
132/24-row source selections, public witnesses, SDK contract or provider
package changes are needed. These checks do not complete extraction parity or
QC-05 composition/native admission, and no task/checklist markers advance.

An isolated local source snapshot freshly packs all 14 Consumer dependencies.
A private SDK-only mutation removes mandatory-fault admission while preserving
the category check. The unchanged Consumer sources produce exactly four named
admission assertion failures (114 other selected rows pass, no skips), rather
than build/setup failures. Restoring the unchanged SDK passes all 132 metadata
and 24 artifact binding rows with zero skips. Both trials retain identical
Consumer source hashes and separate package caches/derived locks. This is
non-native diagnostic evidence, not source-parent or category qualification.

An earlier local attempt reused older artifact binding archives: both existing
concurrent-release rows rejected them, and neither archive contained the
current `ReleaseCoreAsync` implementation symbol. Rebuilding all dependencies
from the current snapshot fixes that diagnostic-input mismatch; no source
assertion, release implementation or budget is changed.

Focused `test_conformance_sdk_checks.py -k full_` passes six tests and
`test_conformance_evidence.py -k native_shared_metadata` passes its independent
source reconstruction/forgery test. Scoped C# whitespace, frozen inventory,
embedded catalog and `git diff --check` pass. The 439-check full tooling run and
133 source SDK tests above remain prior-checkpoint results, not newly repeated
checks. README, active plan and evidence/matrix contracts are updated; other
provider/contributor/deployment guides, examples and diagrams are unaffected
because no public API, supported command, product dependency or deployment
behavior changes.

### Independently selectable hook-admission consumers

Both Consumer categories expose
`Missing_hooks_reject_before_dispatch_and_actual_binding_passes`, with exactly
two provider rows each. They reuse the existing common consumer/control bodies
and admission helper rather than copying assertions. Dedicated sessions use
`QC-05`; the original 132 metadata/24 artifact rows keep their names and
contexts. This avoids filtering two parameters out of a larger method family:
the runtime filter selects entire fully qualified methods.

The SDK diagnostic runner admits only the complete fixed
`hook-admission-metadata` and `hook-admission-artifacts` selections, with one
actual typed origin per row and six pinned images per category, including the
SDK. Missing SDK/component inputs, missing provider archives and reduced or
foreign identities reject before launch. SQLite admission remains mandatory
for the metadata family. These private diagnostic scopes do not yet supply
native QC-05 source parents or complete public qualification.
The focused routing regression also rejects missing, duplicate and foreign
binding origins after execution, and checks the independent role assignments.

Qualification-input batches now execute each complete two-row family exactly
once as a predeclared `hook-admission` scope. The original
`qualification-{metadata,artifacts}-hook-admission-native-executions.json`
graphs bind the original inputs, exact expected selection and held execution
record. Independent admission re-ingests readonly witnesses/proofs and checks
one typed origin per row, descriptor/role/image correspondence, exact settings,
argv/cwd, all six image pins, ownership and settled command/witness bounds.
Metadata and artifact histories collect these controls independently and
retain their original packets under the existing file/byte limits. Reduced or
foreign selections and substituted contexts/commands reject.
Public QC-05 composition now consumes those same original executions through
independent native ingestion, not copied private witness labels. Each retains
its runtime proof/execution ID; both point to the one original native graph.
All four missing-hook, missing-binding, logical-exclusion and durability-policy
obligation controls must be independently reconstructed from that graph.
Missing rows/parents/controls remain `Incomplete`, and foreign origins or
attempt/window mismatches reject. The scope uses the planned attempt UUID
and actual producer time bounds. Its current create-new source graph supports
one attempt; a repeated attempt explicitly rejects rather than reusing or
overwriting prior evidence. This is modeled composition wiring pending
exact-head Linux admission, not complete category qualification.
All 124 evidence and 147 SDK tooling tests pass, including both original graph
producers/factories, history retention/quota checks and mandatory prelude
failure propagation. Frozen inventory, embedded catalog and patch whitespace
checks pass. The earlier full local suite hit the existing 24 GiB artifact
scratch preflight on a volume with about 22 GiB free. Small ownership unit
fixtures now explicitly use the harness profile rather than the default
baseline profile; they observe real available capacity but do not need
artifact transfer space. Artifact filesystem/parent-race unit tests provide
explicit adequate-capacity inputs so their intended controls are reached.
An intended-red zero-capacity ownership-fixture regression reproduces the
accidental baseline dependency. After repair, all 56 execution tests pass
with 19 native skips, and all 443 tooling tests pass with those same skips.
New direct allocation tests retain below-threshold rejection before root
creation and exact 24 GiB admission for both artifact/baseline profiles.
These are modeled unit capacity inputs, not native artifact scratch evidence.
Production preflight, actual-run capacity reporting and transfer budgets are
unchanged; real artifact execution still needs adequate local scratch.
No C# source, tracked lock, public catalog or task/checklist marker changes.

An intended-red selector regression fails before the scopes exist. After
wiring, all 147 SDK diagnostic tooling tests pass. A fresh local snapshot packs
all 14 dependencies and runs the four dedicated rows against three SDK-only
mutations (missing mandatory-hook guard, forged-exclusion bypass and missing
null-binding guard). Each produces exactly four named assertion failures with
zero skips; the unchanged SDK passes all 160 original-plus-dedicated rows
without skips. Consumer source hashes are unchanged across trials. Scoped C#
whitespace, frozen inventory, SDK catalog and patch whitespace checks pass.
No public SDK/provider contract, tracked lock or task/checklist marker changes.

### Packaged durability-exclusion admission controls

The admission helper now independently checks both complete 48-case binding
sets per category, `none` matrix identities and exact catalog exclusions.
Only memory MP-36/38..45 may use `non-durable fixture`; only ObjectSemantics
AS-41..44 may use `simulation: no durable restart`. All other category and QC
entries must remain unexcluded. Provider capabilities cannot select these
expectations. These checks run before opening a session in the existing
admission rows and dedicated families; runtime identities and origin counts
are unchanged. SDK/provider contracts and embedded/frozen catalogs are unchanged.

A fresh-package intended-red replay packs all 14 dependencies and independently
changes only the SDK catalog to add a logical exclusion, exclude a durable
provider case or remove an authorized non-durable exclusion. Each mutation
incorrectly passes all four dedicated rows before the Consumer repair.
A separate fresh 14-package replay after repair rejects each mutation with
exactly four failures at `BindingAdmissionAssertions.CatalogDurability`,
zero passes/skips; the unchanged SDK passes all 160 original-plus-dedicated
rows without skips. Consumer sources are identical across trials within each
phase. Bounded readonly receipts retain hashes/counts, not raw child output.
Scoped C# whitespace, frozen inventory, embedded catalog and patch whitespace
checks pass. These are local diagnostics, not native admission or public QC-05
composition. No task/checklist markers advance; other provider/contributor/
deployment guides, examples and diagrams are unaffected because no public API,
supported command, production dependency or deployment behavior changes.

### Public native-hook composition and shared packet admission

Exact `93e5fe6`/run40255871799 passes 333 native foundations without skips and
fresh 13-lock/18-package replay, but metadata source aggregation fails with
`ProofMismatch`. Bounded locations identify `metadata_controls` rejecting the
shared original owner packet retained by both shared-consumer and hook graphs.
An intended-red regression reproduces that collision. The merger now admits
overlapping source paths only for identical bytes; a changed owner packet or
duplicate control name still rejects. No provenance check is weakened.

The public QC-05 increment additionally passes the actual producer branch and
independent native history/source composition in modeled fixtures for both
categories. Each missing obligation, missing row/parent, foreign origin and
changed attempt window fails closed. All 444 tooling tests pass with 19 native
skips; all 133 source SDK contract tests pass without skips. Frozen inventory,
regenerated SDK catalog and patch whitespace checks pass.

A new isolated snapshot freshly packs all 14 Consumer dependencies with the
updated embedded QC-05 witness catalog. The three catalog mutations each
produce four named `BindingAdmissionAssertions.CatalogDurability` failures,
zero passes/skips, and the unchanged Consumer passes all 160 rows. Consumer
sources remain identical across trials. Bounded readonly receipts retain
hashes/counts, not raw output. These are local diagnostics; exact-head Linux
admission and complete extraction/parity remain outstanding. No task/checklist
markers advance. README, active plan and evidence/matrix contracts are updated;
provider/contributor/deployment guides, examples and diagrams are unaffected
because no supported public API, production dependency or deployment changes.

### Actual artifact-binding publication assertion parity

`ArtifactConformanceSessionTests` now executes the existing shared
`ArtifactPublicationAssertions` empty/absence, unknown-length/real-EOF,
complete-expectation, unsupported-checksum/range and verified-duplicate
consumers through both actual observed bindings. Its complete two-provider
method family has ten rows, each retaining one original typed origin.
The full artifact binding diagnostic scope grows from 24 to 34 rows without
removing existing identities. The manifest now pins the actual SDK alongside
the Consumer, two providers and two adapters. Reduced/foreign selections,
missing new consumer families and missing SDK/component images reject before
launch. Resource settlement/borrowed-ownership checks remain unchanged.

The focused selector first fails because those ten actual-binding rows are
missing. After wiring, all 147 SDK tooling tests pass; the complete 444-test
tooling suite passes with 19 native skips. Changed C# whitespace, frozen
inventory, embedded catalog and patch whitespace checks pass. A fresh isolated
14-package replay passes all 170 original-plus-expanded Consumer rows and
retains three catalog mutants with four named failures each, no skips.

A separate bounded parity replay compares the ten actual-binding publication
rows with their ten corresponding frozen wrapper rows. Both complete families
pass without skips and load identical SDK image bytes. An isolated SDK-only
change deliberately falsifies the shared duplicate byte-count expectation:
both families then have exactly two named failures at
`ArtifactPublicationAssertions.VerifiedDuplicatesAsync`, eight passes and no
skips. Consumer/wrapper source hashes remain unchanged across both trials;
fresh feeds/caches and derived locks are isolated. This tests shared-assertion
reachability/parity, not a faulty-provider qualification pair. Receipts are
bounded/read-only and retain hashes/counts, never raw child output.

This is local publication-family parity only; complete artifact extraction,
native admission, QC-03 and qualifying profiles remain unfinished. SDK/provider
contracts, frozen/embedded catalogs, tracked locks and task/checklist markers
are unchanged. README, active plan and evidence/matrix contracts are updated;
provider/contributor/deployment guides, examples and diagrams are unaffected
because no public API, supported command, production dependency or deployment
behavior changes.

### Actual artifact-binding read, retry and deletion consumer parity

The next complete two-provider Consumer family invokes unchanged common
assertions for borrowed destination failure/second-copy rejection, exact
acknowledged reconciliation/retry, conflicting staged length, deletion and
recreation with stale-incarnation fencing, and held-reader deletion exclusion.
Its ten rows use actual observed bindings, emit one original typed origin each,
and retain resource settlement checks. The closed full artifact binding scope
grows from 34 to 44 rows; no previous identity or six-image requirement changes.
Omission of each new consumer family rejects before dispatch.

The focused scope test first fails for the missing ten rows and passes after
wiring. All 444 tooling tests pass with 19 native skips; scoped C# whitespace,
frozen inventory, embedded catalog and patch whitespace checks pass.
A fresh 14-package replay passes all 180 Consumer rows without skips and
retains all three four-failure catalog-policy controls.

A separate bounded parity replay passes all ten new actual-binding rows and
their ten frozen-wrapper counterparts with identical loaded SDK bytes.
An SDK-only mutation reverses the common conflicting-staged-length stamp
assertion. Both families then have exactly two failures at
`ArtifactPublicationAssertions.ConflictingStagedLengthAsync`, eight passes and
no skips. Consumer/wrapper sources stay unchanged across trials. This proves
local shared-assertion reachability, not a faulty-provider pair or native
QC-03 parent. An initial private replay rejected a non-unique mutation target;
a fresh create-new workspace uses the uniquely scoped assertion without
changing repository assertions or reusing the failed workspace.

Full extraction/category qualification and task/checklist completion remain
unfinished. README, plan and evidence/matrix contracts are updated.
SDK/provider contracts, frozen catalogs, tracked locks, provider/contributor/
deployment guides, examples and diagrams are unaffected: no production API,
dependency, supported command or deployment behavior changes.

### Actual boundary consumers and expected acknowledgment loss

The full artifact diagnostic scope now has 54 rows: eight new actual-binding
boundary consumers and two ordinary observer-error controls preserve the earlier
44 identities and six-image pins. Shared private staging, equivalent writers
and lost acknowledgment run on both bindings; the existing Local
receipt-before-ack and Object direct-availability assertions retain their
original provider scope. Held work is released and joined even on assertion
failure; no synchronous wait adapts asynchronous observer registration.

The first packaged replay passes six boundary rows but fails both acknowledgment
rows because an ordinary observer exception correctly faults ownership.
`InjectPublicationAcknowledgmentLossAsync` now explicitly registers one expected
exception at real publication selection. Only that exact instance is exempt
from the existing unexpected-observer ledger. Two ordinary observers throwing
the same exception type/message at that same boundary still require failed
settlement, the original exception and no authoritative release.

All 190 fresh-package Consumer rows pass without skips. Both complete eight-row
boundary/frozen-wrapper families pass with identical SDK bytes; an isolated
shared concurrent-receipt assertion mutation gives each two named
`ConcurrentEquivalentWritersAsync` failures/six passes. The full 444-test tooling
suite passes with 19 native skips, SDK contracts pass 133 without skips, and
changed C# formatting/frozen inventory/embedded catalog/whitespace checks pass.

Correction to earlier catalog-control classification: removing the empty
memory MP-36 exclusion caused SDK catalog initialization failure, not a named
consumer assertion. Earlier third-control receipts do not establish that
assertion negative. The updated attack includes an explicit unauthorized
durability control so its catalog is structurally valid; all three attacks now
require both actual assertion text and the fixed catalog assertion frame,
with four named failures each. Repository catalog/parsing rules are unchanged.

Exact `2f5841ba344b8b1d021dffbca31a3b8fd54a5081`,
[run40259904782](https://github.com/Stonefly-Labs/Hoard/actions/runs/40259904782),
independently passes all Linux jobs, 336 foundations/no skips and fresh
13-lock/18-package replay. Public QC-05 and identical-owner source-packet
merging are admitted. Metadata qualification-input has ten scopes/141 witnesses/
eight parents and 92 Passed/1 Incomplete/9 NotApplicable/0 Failed; artifacts has
nine/263/six and 98/1/4/0. All four public reports remain `Incomplete`.
The bounded observer initially rejects the guessed foundation count; a fresh
receipt requires the measured exact 336, without changing any source threshold.
This head does not admit the later read/retry/deletion or typed fault changes.

The interim `hoard-architecture-review` confirms the new exception identity
boundary and finds remaining metadata corruption ownership/CAS and artifact
payload/progress gaps. These are implementation work, not waived acceptance
criteria or a final T081 review. Tasks/checklists remain unchanged.

### Actual metadata corruption ownership and closure

The interim metadata findings are repaired with one provider-neutral,
source-linked ownership helper, not shared storage mechanisms. Each adapter
registers a record or exact epoch/operation target before capture and keeps it
owned through application/restoration. Closure admission and target admission
share one gate. Scope disposal serializes restoration, checks the original
fingerprint and removes only its own owner. Both adapters use their existing
compare-exchange primitives and applied callbacks: a stale capture releases
without restoring over a newer commit. Cancellation after mutation restores
with an uncanceled control path. A restoration failure retains its owner for
explicit `RestoreCorruptionsAsync`; still-applying work rejects that recovery.
Typed `CorruptionCaptured` and `PayloadChanged` observations remain adapter-side.
Fractional-state damage now supports a reserved operation without requiring a
committed receipt; the capture race commits that same operation before the
compare-exchange attempt.

The four original record/operation ownership regressions first fail at the
shared assertion through freshly packed actual bindings. Twenty final rows
cover scope overlap/concurrent restoration, record/operation capture conflicts,
cancel-after-mutation, failed-restoration recovery and reopen/disposal admission
while real candidate work is held. The closed metadata scope grows from 132 to
152, requiring 172 typed origins/1,032 role-image/archive correspondences.
A fresh fourteen-package replay passes all 210 selected Consumer rows without
skips. Its first green attempt fails the two reserved-operation capture cases
before the missing primitive is repaired; that failed workspace is retained.

For each provider, all six record/closure rows and all six original wrappers
pass with identical SDK bytes. Changing only the SDK replacement-ownership
assertion gives each family exactly one named `ScopeOwnershipAsync` failure/
five passes; Consumer/wrapper sources remain unchanged. Tooling passes 444
tests with 19 native skips; SDK contracts pass 133 without skips. Changed-source
whitespace and Git whitespace checks pass. These are local results, not a new
native/category admission. Artifact payload/progress controls, complete
extraction and later stages remain unfinished; no checklist/task marker advances.
Examples, deployment instructions and diagrams are unaffected by these
test-only controls; no product API or infrastructure is changed.

### Actual artifact payload and progress controls

Independent Local/Object controls now capture, replace and remove only the
exact current stamp, through real tracked work with a five-second budget and
64 KiB bound. They preserve receipts/quarantine, copy submitted and captured
bytes, reject missing targets and prevent stale-incarnation ABA edits.
Eight new actual-binding rows extend the artifact scope from 54 to 62.
Local damaged-read rows genuinely reopen and contribute parent/child origins;
Object retains simulation-only scope. The original permanent-quarantine body
and its frozen checksum are unchanged. Additional original negative-consumer
checks reject lost quarantine denial after asynchronous compatible reopen and
accept the genuine reopened store, without changing runtime identities.

The first payload replay exposes both progress rows; coherent monotonic clock
advancement fixes Local, while Object still records failed settlement because
the observer was registered during setup publication. An awaited SDK installer
now registers at the assertion's actual installation point. It preserves the
legacy wrapper entry point and unchanged progress/receipt assertions.
A later negative-consumer replay catches an inaccessible internal SDK helper;
the wrapper now uses its existing local helper. Failed workspaces are retained.

The interim architecture review additionally finds a check/I/O deletion race:
replacement can recreate retired bytes after deletion reports reclamation.
Controlled actual-binding regressions reproduce two named
`PayloadControlsExcludeDeletionAsync` failures before repair. Both providers
now acquire the existing authority's read protection inside tracked work and
hold it through selection, payload I/O and disposal. At the typed
`PayloadSelected` boundary, the regression observes genuine queued deletion,
not an arbitrary sleep, across replacement, capture and removal; deletion
completes with reclamation only after each control settles. The initial race
probes fail setup/cleanup and are not counted as named assertion evidence.

The final fresh fourteen-package replay passes all 218 selected Consumer rows,
zero skips. Eight actual payload/progress rows and thirteen original rows
(six corresponding wrappers plus seven deliberate-negative consumers) pass
with identical SDK bytes. SDK-only damaged-read assertion mutation gives four
named failures in each corresponding family; the progress mutation gives two.
No Consumer/wrapper source changes occur within a mutation trial. Full tooling,
133 SDK contracts, changed C# whitespace, frozen inventory, embedded catalog
and Git whitespace checks pass. These are local diagnostics, not new native
admission, QC-03 completion or a completed implementation stage.
README, provider guidance and active plan/quickstart/contracts are updated.
Examples, diagrams and deployment guides are unaffected: no product API,
deployment behavior, infrastructure or dependency boundary changes.

Exact `e192af0fe5ae1be1d8f89ff0c595cb22266b5613`,
[run40260447361](https://github.com/Stonefly-Labs/Hoard/actions/runs/40260447361),
independently admits the older read/deletion source checkpoint: all three
Linux jobs, 336 foundations without skips, locked replay and unchanged complete
native obligations pass. All public reports remain `Incomplete`. This does not
admit later boundary, metadata ownership or payload/progress changes.

### Actual artifact recovery, expiry and stream-ownership consumers

Thirty more actual-binding rows directly call thirteen existing SDK entry
points without changing their assertions. Both providers execute exact receipt
validation, recovery pages, 32 independent sequential cursors, changed inventory,
staging-generation expiry, ownerless expiry, finalized noncommit/mutations,
idle-read expiry, cooperative inactivity, non-cooperative source/destination
ownership and the completion/handle/renewed descriptor shapes. Each row emits
one actual typed origin and requires real settlement, never physical Released.
The complete artifact scope grows from 62 to 92 and rejects reduced selections.

The closed-scope regression first fails before these families are wired.
The first fresh package replay exposes two ownerless-expiry setup mismatches:
using a ticket-count cap changes the retired-ticket result to InvalidInput.
The adapter setup now preserves the unchanged original test's one-byte artifact
and staging limits. No provider/assertion/timing behavior is changed; the failed
workspace is retained. A fresh fourteen-package replay then passes all 248
selected Consumer rows without skips.

The complete thirty-row actual/frozen-wrapper families both pass with identical
SDK bytes. An SDK-only recovery-page operation-ID assertion mutation gives
each exactly two named `RecoveryPagesAsync` failures/28 passes, zero skips,
without editing either consumer's source. These are local diagnostic results,
not complete extraction, native source admission or QC-03 completion.
README, provider and active specification guidance are updated; examples,
diagrams and deployment remain unaffected by package-only test wiring.

### Package-only schema-probe compilation repair

Linux SDK/preparation runs at `9f3035d` and `a3e765e` fail with `CS0535`
before category diagnostics: `MemorySchemaProbe` does not implement
`IMetadataConformanceFaultDriver.RestoreCorruptionsAsync`. Normal source-mode
SDK tests exclude `MemoryMechanismTests.cs`; they cannot validate this surface.
A fresh isolated package-mode build reproduces that exact missing member.
The schema-only probe now explicitly throws its existing unsupported-operation
error, consistent with its other unsupported full-binding lifecycle hooks;
it does not pretend to restore owned corruption. The same package-mode build
passes afterward using identical SDK archive bytes. This fixes compilation,
not native runtime admission; fresh Linux completion remains pending.

### Actual artifact budget, failure and reference consumers

Seventeen further observed rows reuse eight unchanged SDK methods for authority
deadlines, both canceled-commit admission shapes, capacity crossing, cooperative
cancellation, sanitized storage failures, live/unavailable reference denial and
bounded reclaimed identity/incarnation history. Limits and reference callbacks
preserve each original wrapper's setup; only the original Local incarnation
case is selected. Forward history expiry advances the coherent controlled clock
without adding rollback behavior.

The closed-scope regression first fails before wiring. Fresh fourteen-package
replay passes all 265 selected Consumer rows without skips; the artifact
selection is now 109. Complete seventeen-row actual/frozen-wrapper families
pass with identical SDK bytes. An SDK-only capacity assertion mutation gives
each exactly two named `CapCrossingAsync` failures/fifteen passes, no skips,
with both consumer sources unchanged. This is local extraction parity, not
native admission, complete QC-03 or stage completion. Examples, diagrams and
deployment remain unaffected by this package-only test wiring.

### Actual artifact handoff, progress cancellation and clock rollback

Twenty additional observed handoff/progress and rollback rows extend the
artifact selection to 129. Four handoff assertions and progress-renewal
cancellation gain awaited installer overloads; original synchronous entry
points forward to the same assertions. Installation/removal occurs exactly
when requested, after setup publication, without early no-op observers or
async-void adapters. Actual barriers release even if removal fails.

Six named clock regressions first fail while all 279 other selected rows pass:
UTC rollback also rewinds the old controlled timestamp. Independent monotonic
ticks now advance with `Advance` but not `SetUtc`. Fresh packages pass all 285
selected rows. Complete twenty-row actual/frozen-wrapper parity passes with
identical SDK bytes, plus both original discarded-ticket negative consumers.
An SDK-only successful-read assertion mutation gives each corresponding family
two named failures/eighteen passes, no skips. Source-mode SDK contracts pass
133 tests; package-only SDK contracts also compile. These remain local
diagnostics; examples, diagrams and deployment are unaffected.

### Native source-sealing and shared-consumer admission history

The latest independently admitted earlier head is `831b00c`,
[run40271691109](https://github.com/Stonefly-Labs/Hoard/actions/runs/40271691109):
all three Linux jobs pass, with 336 native foundations/no skips and the full
129-row artifact/152-row metadata sources. Exact `ef680f3`/run40270185078 also
passes strict admission of its earlier 92-row artifact scope. Original native
transfer/recovery obligations are unchanged. Metadata qualification-input
diagnostics remain 92 Passed/1 Incomplete/9 NotApplicable/0 Failed, report
`Incomplete`, qualification false; shared-source coverage does not close QC-02.

The current local extension adds twelve admitted deletion-history, transfer-queue,
released-shutdown, reconciliation-history/replacement and late-cleanup rows:
141 artifact identities and 297 selected fresh-package Consumer passes, no skips.
Three awaited recovery overloads forward original synchronous callers into the
same assertions. Both complete twelve-row actual/frozen-wrapper families pass
with identical SDK bytes. SDK-only deletion-history, reconciliation-history and
cleanup-generation mutations each give both families exactly two named failures/
ten passes, no skips. Tooling passes 444 tests/19 native skips, source SDK
contracts pass 133/zero skips, and focused whitespace/catalog checks pass.
This extension is not native admission, complete extraction or stage completion.
Examples, diagrams, production module boundaries and deployment are unaffected.

Complete local metadata parity now passes all 152 actual consumers, 63 original
memory witnesses and 63 original SQLite witnesses with identical SDK archives.
SDK-only continuation, query-dimension and lease-expiry mutations yield,
respectively, 12/6/6, 10/5/5 and 6/1/1 named failures across those families, with
no skips or incidental failures. Original lease loops explain the split-row
counts; method totals are not parameter parity.

Qualification-input original metadata scopes now enter `NativeCategorySources`
rather than ordinary runtime ingestion. Admission independently selects every
role image/creation/reopen forest, checks sealed runtime packets against actual
transport bytes, pins SDK/provider/host/wrapper images and reconstructs exact
provider/context settings plus held argv/cwd/input closure and current attempt
parents. Modeled substitutions and the full tooling suite pass: 445 tests,
19 native skips. Exact `74cf619a8c33dc440891130c69bd9fab6453542e`,
[run40279501756](https://github.com/Stonefly-Labs/Hoard/actions/runs/40279501756),
now passes all three Linux jobs and 337 native foundations/no skips. Its
metadata report retains ten scopes/141 public executions and now ten source
parents, with 92 Passed/1 Incomplete/9 NotApplicable/0 Failed. Earlier
`bc8509471c5f0a69bf34a582e18932f9e7731bd9`/run40276791513 passes all three
jobs and 336 foundations, admitting artifact141/metadata152 with eight parents.
Both retain original native transfer/recovery obligations and qualification
false; neither grants QC-02 or advances task/checklist/stage markers.

Complete local metadata replay now separately targets each of six continuation
shapes, five query dimensions, three lease actions and two layout booleans.
All sixteen SDK-only mutations produce exactly 2/1/1 named failures in the
complete 152/63/63 actual/memory/SQLite families; every other row passes, with
zero skips. These historical-source diagnostics do not grant native parameter
quality or borrow source identities from a later head.

Eleven history-candidate rows extend the artifact scope to 152. Awaited common
assertion overloads retain synchronous original wrappers and all seven frozen
page-bound parameters/two resume cases. The adapters separately own observations
and one-shot ticket-candidate injection; duplicate registrations reject, and
same-shaped ordinary observer exceptions still fault actual settlement while
injection is armed. Fresh fourteen-package replay passes 308 selected Consumer
rows without skips. Subsequent complete parity includes the duplicate-owner
guards: 304 actual rows and all nine corresponding frozen history rows pass;
SDK-only bounds/resume mutations give exactly seven/two named failures in both
families, with every other row passing, zero skips and exact SDK/archive image
correspondence. The new scope awaits exact-head Linux observation.
Examples, diagrams, production dependency boundaries and deployment are
unaffected; complete extraction and implementation remain unfinished.

Ten subsequent receipt/read-opening/reconciliation rows extend the artifact
scope to 162. Typed registration restricts intentional failure to the two
supported observation points and retains the exact private exception filter;
same-shaped ordinary callback exceptions still fault actual settlement.
Awaited shared overloads preserve all six original observation cases and the
one-slot/no-waiter read limits. Receipt observer removal cannot strand its
held commit if removal fails. Fresh fourteen-package replay passes 318 selected
consumers. Complete 314-row actual/six-row frozen parity passes; SDK-only
receipt/read-payload/verified-counter mutants each produce two named failures
in both families, all other rows passing with matching SDK/archive images and
no skips. Tooling passes 445 checks/19 native skips and source contracts pass
133/zero skips. Exact-head Linux admission remains outstanding; no tasks or
reviewer-owned checklists are marked complete.

Exact `d30271d`,
[run40286734253](https://github.com/Stonefly-Labs/Hoard/actions/runs/40286734253),
passes all three Linux jobs and 337 native foundations without skips, admitting
artifact162/metadata152, ten metadata scopes/141 public executions and ten
metadata source parents. Its metadata report remains `Incomplete`, qualification
false. The later argument transport still needs its own exact-head result.

Metadata argument capture records only the sixteen closed enum/layout choices
inside the four common SDK methods, without altering their assertions. Late
source output drains pending calls once. Original schema observations retain
their early output and acquire an explicit per-assertion disposable argument
scope; closure joins in-flight output before releasing either component-role
owner. Overlap rolls back without replacing existing owners, and later object
reuse cannot resend old calls or write to a closed helper. Pending/live calls
remain bounded. Independent C# and Python validation joins the third packet
prefix to actual source/component identities in runtime proof schema3 and
rejects foreign contexts, role/value mismatches, unknown fields and replay.
Argument admission uses the declared metadata category, not reference-provider
binding names; both logger and parent have contributor-name regressions.
Legacy schema1/2 transport remains diagnostic-compatible. Case/category
histories retain immutable argument maps and reject cross-scope call reuse.
Both native source authorities now enforce a closed per-witness parameter map.
Original authority re-reads argument packets from readonly proofs, independently
validates their roles/contexts and commits them into the source-proof digest.
Missing choices, wrong valid values, unexpected calls and wrong original forest
nodes reject even after coherent rehashing. All 278 retained local SDK proofs
match the expected source-node maps. Cross-family pairing now re-admits both
complete original scopes, requires the current shared graph and SDK image
correspondence, rejects cross-family replay/old attempts and seals one receipt.
QC-02 composes all 96 primary keys, including MP-46 host provenance, MP-48
inventory controllers and the nine authorized exclusions. A compact complete
basis preserves the 128-witness/proof bounds; public report admission recomputes
both pairing and basis hashes. These modeled checks are not new native admission.
The subsequent artifact166 increment adds both pending-reclamation consumers
and same-shaped ordinary delete-removed callback failures. Awaited injection
preserves the original synchronous wrapper and every cleanup/readback/receipt
assertion. Ordinary failures remain in the actual settlement ledger, with
explicit `CleanupIncomplete` and no false release. Fresh fourteen-package
replay passes 322 selected consumers without skips. Fourteen actual controls/
two original deletion wrappers pass; an SDK-only cleanup assertion mutant gives
each family exactly two named failures, with matching runtime SDK/archive
images. This is not complete QC-03. Exact `b66e6b0`/run40292115062 independently
passes all three Linux jobs and 341 native foundations without skips, admitting
the earlier artifact162/metadata152 argument-transport snapshot, not the later
frozen-map/pairing/deletion changes.
The next two admitted-open quarantine races extend the artifact scope to 168
and fresh-package replay to 324 passes. Awaited shared hooks preserve the
original wrappers and assertions. Replacement permits existing readers as the
original fault did, retaining serialized fault work and actual authority
protection against deletion. Initial Local `Unavailable` exposed the overly
exclusive sharing mode, not a named assertion failure. Both original/actual
pairs pass; an SDK-only final quarantine assertion mutant gives exactly two
named failures per family, with matching runtime SDK/archive images. Full
QC-03 remains open. Pairing run40295489832 was canceled before jobs and is not
admitted; replacement deletion run40297863544 awaits independent observation.
The next artifact172 increment retains all four validation-first missing/
truncated parameters and Local compatible-reopen proof. Fresh packages pass
328 selected consumers; four actual/original pairs pass. An SDK-only incarnation
assertion mutant gives four named failures per family with matching runtime
SDK/archive images. Safe-logger replay validates all 172 witnesses/178 origins,
six reopen edges and exact per-row origin counts/role-image-package matches.
Missing, extra or foreign validation origins reject; Object never borrows a
Local restart. Tooling452/19 native skips and source contracts152/zero skips
pass. Exact `e39b2ce`/run40293145453 independently admits earlier frozen argument
maps with three Linux jobs/341 native foundations passing without skips.
QC-02 pairing/newer artifact native confirmation and full acceptance remain open.
Examples, diagrams, production dependencies and infrastructure
are unaffected.

The artifact shared-consumer source path now reuses the existing metadata native
reconstruction rather than accepting diagnostic receipts as qualification.
Its actual command closure pins the extra original-wrapper SDK image; readonly
graph/manifest/settings, exact 250 witnesses/262 origins, six runtime/package
images, native execution record and original proof bytes are independently
reconstructed. It runs before unchanged real transfer controls, and both shared/
hook source families retain original packets with conflicting overlaps rejected.
The catalog relocation changes no identity or origin count. Expanded artifact
source/launch guards and tooling454 (19 native skips) pass; actual Linux admission,
original artifact parameter pairing and full QC-03 remain pending. No budgets,
task/checklist markers, production dependencies, examples, diagrams or
infrastructure change.

Original artifact source reconstruction now also covers `original` (183 exact
witnesses), `original-local` and `original-object` (twelve each). It independently
selects per-node roles and complete forests, verifies readonly images/proofs and
wrapper SDK/archive correspondence, and pins every manifest image in the actual
native command. Scope receipt bounds use the exact inventory, not a per-case
128-row limit. Command timing must remain inside its containing attempt; the new
regression exposed and closed that missing artifact check. Tooling455 (19 native
skips) passes, including missing/foreign rows, forests, roles, reused instances,
SDK and native-command mutations. Actual Linux admission and parameter pairing
remain pending; no QC-03, task/checklist or stage completion is claimed.
Examples, diagrams, production dependencies and infrastructure are unaffected.

Artifact parameter pairing is now wired through the native source collector:
re-admit all three complete original scopes alongside the shared-consumer source,
reject stale attempts and borrowed execution/origin/component instances across
sources, then persist readonly input/time-bound pairing material. Reuse the same
scope-proof reconstruction as metadata. QC-03 now composes every AS-01..48 key,
recomputing its full basis packet rather than truncating direct proofs; real
transfer and Local recovery sources and all four Object exclusions remain
mandatory. Tooling458 (19 native skips) passes. Synthetic/report mutation guards
are not actual Linux admission or qualification; the implementation stage remains
running. Examples, diagrams, production dependencies and infrastructure are
unaffected.

Native run `40320966626` at `c6fdc27` passes foundations and locked replay but
rejects `artifacts/original` at the read-only proof check. The three original
artifact scopes were missing from the transport inspection/sealing dispatch.
They now use the existing path that checks actual child settlement and unchanged
captured bytes before sealing logger records and proofs. Regression coverage
includes all three scopes, live-child/changed-output rejection and unchanged
diagnostic-mode dispatch. This repairs transport admission, not qualification;
exact `5ba30af` / run `40328218160` passes all three Linux jobs, 350 native
foundation checks without skips, and fresh package/lock replay. Qualification-input
metadata executes ten scopes/141 witnesses/ten native parents with 93 passes,
nine exclusions and zero failed/incomplete cases. Artifacts executes nine
scopes/263 witnesses/nine parents with 99 passes, four exclusions and zero
failed/incomplete cases. Both category reports remain `Incomplete`,
qualification false; full CLI/evaluator/cleanup, contributor, composition,
compatibility and five-profile acceptance are not inferred.
Other guides/examples, diagrams, product APIs, package dependencies and
infrastructure are unaffected because this changes only test transport routing.

Category report publication also retains `proofs/category-<profile>-<mode>-completion-inputs.json`
with the actual completion inputs and `0400` permissions. Its hash is the report's
`postInputSha256`; bounded descriptor-based verification rechecks that packet and
the existing immutable-input comparison before report publication. Free-space
variation is not hidden by rewriting either measurement or hash. Missing,
writable, altered, foreign-input, malformed and symlink packets reject. This
does not change the CLI guard, release resources or qualify a category.

For an isolated native extraction diagnostic, use
`python3 scripts/conformance_sdk_checks.py --root <checkout> --evidence <fresh-private-path> --category metadata`
or select `artifacts`. The same Linux ownership/scratch prerequisites and shared
historical/package preparation apply. The selected batch performs its own
recovery/transfer/source controls, then recaptures inputs and performs bounded
synthetic-store/feed/cache release before report publication. The captured
resource projection is actual, not an inferred successful exit; failed input
recomputation or cleanup prevents publication. Reports remain `Incomplete`,
qualification false. The existing full diagnostic job is preserved alongside
two explicitly non-qualifying isolated extraction jobs. Native admission of
these new paths is pending; public `validate-conformance.sh` profile, verify and
aggregate execution is not inferred.

Run `40341286948` passed the three foundation jobs but exposed `InputChanged`
in both isolated category jobs: cleanup removed runsettings that their proof
registries still required. Generated settings now use
`proofs/settings-<attempt>.runsettings`, with the same exact native-command input
hashes and source admission; cleanup still removes synthetic stores/feed/cache.
A regression verifies settings remain read-only and byte-identical after store
deletion. Fresh native confirmation is pending; no qualification is inferred.

Legacy metadata/artifact validation now invokes the existing `HoardSafe` logger
through `conformance_legacy.py`. It bounds transient output, retains only closed
safe projections, stages bounded allowlisted execution inputs, checks actual
loaded SDK/archive byte agreement and requires `.runtime.json` attribution on
replay. Recovery/barrier output is concurrently drained and rejected when
unexpected, including trailing artifact crash output; profiler text is admitted
only by its exact OS grammar before numeric RSS projection. The ordinary
command transport keeps its group leader unreaped until owned group settlement,
preventing PID/group reuse during cleanup. Real configured memory MP-18
execution and independent sidecar replay pass; an unconfigured witness fails
closed rather than becoming evidence. Full legacy entry points and fresh
recovery/transfers remain acceptance obligations, not inferred passes.

Architecture policy regressions distinguish the test-only conformance SDK from
permitted vendor-driver SDKs, including declared-unused and compiled
direct/transitive paths. The focused architecture/policy filter passes 34 cases
and whitespace formatting passes. Historical lifecycle/configuration graph
tests still require their prepared manifests; this focused result does not
claim those full scans or compatibility-profile acceptance.

Tests-first CP-01..20 coverage reuses `ConformanceMatrixTests.cs`, preserving the
existing catalog/runtime identities instead of introducing duplicate test types.
Source matrix/version and related lifecycle/configuration/discovery regressions
pass (188 cases), as do the final five CP-16/17 assertions. A focused
Release/net10.0 package replay of CP-01/02/18/19 passes five cases after explicit
non-qualifying local archive hash rebinding and independent locked restore.
Tracked locks are unchanged and source-mode assets are restored. This closes
the tests-first tasks, not fresh-source composition-profile qualification;
the SDK diagnostic path still does not execute the composition project.

Linux run `40312172408` at `516b6e4` fails the prepared Object no-rename architecture
witness; its other two jobs pass. The cause is qualification-only directory moves
introduced inside the Object provider assembly, not its publication mechanism.
Move that access-fault scope back to its concrete test binding, matching original
driver ownership; do not exempt qualification code or weaken the scan. Native
selection/protection, capture-before-hook and restoration-before-guard-release
remain. The unchanged prepared witness gives a named `Assert.Empty` failure on
the prior graph and passes on the corrected graph. Fresh fourteen-package replay
passes 406 consumers; 16 actual/four original access cases pass, and their SDK-only
negative gives four named failures per family with matching runtime/archive
images. Safe-logger replay checks 250 witnesses/262 origins. Contracts152/
tooling452 (19 native skips) pass. Scoped implementation review has no actionable
findings, not final T081. Native admission remains pending. Examples, diagrams,
production dependencies and infrastructure remain unchanged.

The current artifact250 extension preserves every retained prefix/object cleanup
and stop assertion through awaited overloads while keeping synchronous callers.
Native storage facts remain immutable/path-free, root-owned through explicit
stop and bounded across all filesystem entries. Unexpected directories/symlinks
or capacity overflow fail explicitly, never become empty successful observations.
This repairs the scoped file-only enumeration finding; its private restored
mutant causes four named guard failures. Real directory permission restrictions
share pending application/restoration ownership and avoid nested transfer admission
inside callbacks. Ordinary same-type/message errors retain exact faulted settlement.
The first Local commit-progress error probe never reached that native boundary;
its corrected setup first publishes the identical payload, without weakening
any error assertions. Fresh fourteen-package replay passes 406 consumers;
24 actual controls/12 original wrappers pass. Six SDK-only assertion mutants give
2/2/1/4/1/2 named failures in each family, all other cases passing, with matching
runtime/archive SDK images. Safe-logger replay checks 250 witnesses/262 origins/
twelve reopen edges. Contracts152/tooling452 (19 native skips) pass. Scoped review
findings are repaired, not final T081. Native/full QC-03 and remaining stage work
stay unfinished; examples, diagrams, production dependencies and infrastructure
are unaffected.

The preceding artifact226 extension adds genuine Local decisions-directory write
denial through the same pending access owner, not synthetic validator failures.
The original failed-quarantine test retains failed stop, payload restoration,
permission restoration, stop retry and same-lifetime compatible initialization
before owned replacement. Object rejects this unsupported control before owner
allocation. Pending application joins shutdown; ordinary release errors and
cancellation retain exact errors/faulted settlement after original mode
restoration. Existing delivered-success semantics are unchanged; earlier private
discarded-success expectations were invalid, not proven bugs. Fresh fourteen-
package replay passes 382 consumers; five actual controls/one original wrapper
pass. An SDK-only readiness mutant causes one named failure per family with
matching SDK/archive images. Safe-logger replay checks 226 witnesses/237 origins
and eleven reopen edges. Contracts152/tooling452 (19 native skips) pass. Scoped
review finds no actionable issues, not final T081. Native/full qualification
remains unfinished; examples, diagrams, production dependencies and infrastructure
are unaffected.

The preceding artifact217 extension owns real Unix payload permission/directory
access faults through application, restoration and closure. Exact-stamp guards
prevent physical deletion until restoration; capturing the native scope before
release callbacks closes the reviewed failed-result handoff gap. Four rows each
cover original validation, concurrent shutdown, queued deletion and ordinary
release errors. Ordinary errors still produce `CleanupIncomplete` and faulted
settlement after actual restoration. Fresh fourteen-package replay passes 373
consumers; sixteen actual controls/four original wrappers pass. The SDK-only
failure-code mutant yields four named failures per family with matching loaded
SDK/archive images. Safe-logger replay checks 217 witnesses/227 origins and ten
reopen edges. Contracts152 and tooling452/19 native skips pass; scoped review
finds no remaining actionable issues, not final T081. Full QC-03/stage acceptance
remain open. Examples, diagrams, production dependencies and infrastructure are
unaffected.

The preceding artifact201 extension retains Local committed-decision rollback
after 105 retired histories and durable-receipt staging-release recovery.
Original limits, UTC/monotonic distinction, synchronous signatures and assertions
remain. Awaited reopen uses the genuinely initialized owned replacement; old
wrappers still initialize raw replacements and preserve initialization-failure
cleanup. Owned third-record-write interruption rejects duplicate/hold overlap;
ordinary same-message callbacks fault actual settlement. Scoped review found
an Object deletion/record alias: a distinct Local-only hook now rejects Object
explicitly, and a restored-alias private negative fails the named guard.
Fresh fourteen-package replay passes 357 consumers. Four actual controls/two
original wrappers pass; each SDK-only durable assertion mutant gives one named
failure per family with matching runtime/archive SDK images. Safe-logger replay
admits 201 witnesses/211 origins and ten reopen edges. Tooling452/19 native
skips and contracts152/zero skips pass. Follow-up review finds no remaining
actionable issues, not final T081. Full QC-03/stage acceptance remain open;
examples, diagrams, production dependencies and infrastructure are unchanged.

The preceding artifact197 extension preserves the Local read/reconciliation
quarantine race and all six committed-detection parameters. Public recovery
rows supply genuine selected stamps checked against exact ticket/store/
identity; no incarnation or private payload path is fabricated. Awaited
overloads retain synchronous wrappers and every original assertion. Fresh
fourteen-package replay passes 353 selected consumers. Both seven-row families
pass; SDK-only race/detection assertion mutants produce one/six named failures
per family with matching runtime/archive SDK images. Safe-logger replay admits
197 witnesses/205 origins and eight reopen edges. Exact origin policy requires
the Local open/publication reopen, not Object or Local reconciliation.
Tooling452/19 native skips and source contracts152/zero skips pass.
Complete QC-03 and feature acceptance remain unfinished; examples, diagrams,
production dependencies and infrastructure are unaffected.

The preceding artifact190 extension preserves all eighteen original admission
parameters with genuine uninitialized lifetimes and raw root/readiness facts.
Default creation is unchanged; explicit typed probes preserve unrelated
capabilities, original default/configured limits, actual foreign scope and
owned shutdown. Fresh fourteen-package replay passes 346 selected consumers.
Both eighteen-row actual/original families pass. SDK-only no-I/O and optional-
range assertion mutants yield sixteen/two named failures per family, with
matching runtime/archive SDK images. Safe-logger replay admits 190 witnesses/
196 origins, six reopen edges and exact role/image/archive correspondence.
Scoped architecture review finds no actionable issues, not final T081.
Tooling452/19 native skips and source contracts152/zero skips pass.

Exact `f4e53b4`/run40297863544 now independently passes all three Linux jobs,
343 native foundations without failures/errors/skips, artifact166 source
admission and metadata QC-02 pairing. Metadata has 93 Passed/0 Incomplete/
9 NotApplicable/0 Failed, but the overall report remains `Incomplete`,
qualification false. Artifact190, full QC-03 and feature acceptance remain
unfinished. Examples, diagrams, production dependencies and infrastructure
are unaffected by this test-only admission extension.

Fresh fourteen-package replay passes 318 selected consumers. Complete
152 shared/63 memory-original/63 SQLite-original safe-logger families pass
without skips and contain exactly 32/16/16 distinct source-bound argument
calls. Each loaded SDK matches the same admitted local archive image before
and after its family; all 64 call UUIDs differ. Tooling451/19 native skips
and source contracts152/zero skips pass. The scoped architecture follow-up
finds no actionable issues, but lacks a deterministic selected-receiver/
closure-race regression and is not final T081 or native admission.

Exact `58a949543ea160b5be21c13db581f01387d33719`,
[run40249387122](https://github.com/Stonefly-Labs/Hoard/actions/runs/40249387122),
independently passes all three Linux jobs: 331 native foundations without
failures/errors/skips and fresh 13-lock/18-package replay. It admits the
source-sealing repair, both category QC-04 negative/corrected pairs and the
complete 132-row shared metadata source control, including identical
wrapper/Consumer SDK image bytes and their original native input pins.

Qualification-input metadata has nine scopes/139 witnesses/seven source
parents and 91 Passed/2 Incomplete/9 NotApplicable/0 Failed. Artifacts has eight
scopes/261 witnesses/five source parents and 97/2/4/0. All four public reports
remain `Incomplete`; metadata QC-02/QC-05 and artifact QC-03/QC-05 are not
completed by these results. No task/checklist markers advance.

Metadata inputs/results are
`28496c509c14253a9e231e1932f881878963f79aaeadce0e3bd8ba8403922f8f` /
`e8969be40b9a620de308b583942e0fc36b29e9542b778ce443472ea351e4e636`;
its shared-consumer source digest is
`beb6ea5565bfe0fa55425c903be333298faf60b9931df6d965401b070c26c1a6`.
Artifact inputs/results are
`4c1387ad9c652b0cc653642332070a4943f7e0771d6121d25dabb723222918c8` /
`d1801411c4e00bee34628855a23f1853b97422509e596b49c2df23d1cb3d9fc6`.
The bounded safe receipt is retained read-only; no raw CI log is retained.
This older head does not admit the subsequent packaged hook/null/exclusion
controls or dedicated hook diagnostic families. Exact `97b6d0b`,
[run40252743943](https://github.com/Stonefly-Labs/Hoard/actions/runs/40252743943),
passes 332 native foundations and locked replay but fails one existing
`Lost_metadata_acknowledgment_keeps_real_reference_protection_until_physical_settlement`
SQLite/Local row in the complete 183-row original artifact scope:
`UnknownDiagnostic`, 182 Passed/1 Failed. The hook diagnostics ran earlier.
Three complete unchanged local four-row acknowledgment-family trials and one
complete 183-row artifact trial pass without skips; these do not reproduce
the failure or establish its cause and do not admit native behavior.
No assertion, deadline or provider code was changed. Exact `b0852b7`,
[run40253289352](https://github.com/Stonefly-Labs/Hoard/actions/runs/40253289352),
independently passes all three Linux jobs with unchanged runtime/Consumer
bytes: 332 native foundations without failures/errors/skips and fresh
13-lock/18-package replay. Both complete two-row hook diagnostic families
pass, as does the complete 183-row original artifact scope. The ordinary SDK
diagnostic summary has 111 scopes and 1,327 discoveries/executions; this is
not a combined total for the additional category source graphs.
Qualification-input metadata remains nine scopes/139 witnesses/seven parents,
91 Passed/2 Incomplete/9 NotApplicable/0 Failed; artifacts remains eight
scopes/261 witnesses/five parents and 97/2/4/0. All four public reports remain
`Incomplete`. The original bounded receipt is retained read-only.
This independently admits the packaged hook/null/exclusion guards and
dedicated diagnostic families, not the newer private native hook-source
reconstruction at `93e5fe6`/run40255871799. The unchanged-runtime success
does not establish the earlier failure's cause or advance task/checklist
markers.

Exact `b1bbbb63fb5687fb709c029902ba7c9caf5f28d2`,
[run40220115471](https://github.com/Stonefly-Labs/Hoard/actions/runs/40220115471),
independently passes all three jobs: 291 native foundations without failures/
errors/skips, 13-lock/18-package fresh replay and 128 scopes/1,819 witnesses.
Qualification-input metadata has seven scopes/135 witnesses/five source parents
and 85/8/9/0; input
`12f73c5aaf1ac6c6c7d1a0370d96ed951f98039346f6a16ea5c2a9c767085150`,
result `3ba98fed69680237fcc8bea2833f1aa82bf8817aad7bd87649465a48efec5ae8`,
binary graph `25e6f7d54d15dc2f39d714b3c2a687050ca48be1000ac505126a32c0a7d6ebb2`.
This admits ownership, unchanged consumer and frozen-binary controls through
MP-47. It does not admit later inventory/QC changes or a complete profile.

`python3 -m unittest discover -s tests/tooling -q` passes 402 checks with 18
explicit native skips. The source SDK project passes all 121 checks; scoped
`dotnet format whitespace ... --verify-no-changes` passes. The unchanged
inventory/catalog checks pass, and actual MSBuild package compile selection
includes both the decoder and its native facts. Actual isolated CLI commands on
macOS run all 17 unchanged tests three times: 0/1/0 assertion failures, no setup
errors/skips/raw diagnostics, with the same adapter restored and original suite/
verifier unchanged. These are non-qualifying diagnostics, not Linux admission.

Exact `5bc86feada20039e93c203669b8c8941786ea84d`,
[run40218754070](https://github.com/Stonefly-Labs/Hoard/actions/runs/40218754070),
passes 287 native foundations with no failures/errors/skips and the 13-lock/
18-package replay. Its SDK batch rejects `EvidenceIncomplete` from
`UnknownDiagnostic`, exit 1, with 62 Passed/1 Failed. The mismatch hash
`8761af132f080f40d5999df167d880f419587ca1418400246a283227e0f63d87`
resolves against known identities to
`MetadataDeadlineTests.MP19_Queue_capacity_and_held_work_deadlines_have_finite_owned_results`.
The underlying cause is not established. This is not ownership/consumer admission;
the exact later binary checkpoint succeeds independently. That success does
not diagnose this earlier failure. No legacy
deadline assertions or native admission gates are weakened to obtain a pass.

Earlier exact `f038df04ee1d989b3cd81fe7d9247c0fb041016c`,
[run40216546349](https://github.com/Stonefly-Labs/Hoard/actions/runs/40216546349),
now independently passes all three Linux jobs: 283 foundations without
failures/errors/skips, 13-lock/18-package replay and 128 scopes/1,819 witnesses.
Qualification-input metadata has seven scopes/135 witnesses/five parents and
80/13/9/0; input
`b32cf27c4305cdacdda667f5724b3f307b1bb2999df6a1339dbb7ba014e189eb`,
result `d9256476167ed952f9c3ce8774ac3b5cbf1a36417f11f68e5c9e01abea131211`,
native graph `81f7f254e4a9dc40ce902ee179e8b86cc1e16f921daa43053fab1085f0db6810`.
This admits MP-37 native-stall/output anchoring only, not later ownership,
consumer, frozen-binary or full-profile qualification. The pending
`1bcac02`/`b0715dc` runs were automatically superseded and provide no evidence.

Earlier exact `2ac4ed66505c1035aab0c490510eeee44d475e32`,
[run40215065690](https://github.com/Stonefly-Labs/Hoard/actions/runs/40215065690),
now independently passes all three Linux jobs: 280 native foundations without
failures/errors/skips, 13-lock/18-package fresh replay and 128 scopes/1,819
actual witnesses. The seventh qualification-input metadata scope executes,
retaining 135 witnesses/five source parents and 79/14/9/0 states. Inputs
`d2e42b6fa37b81b9f16b7217aaebdb23f2eead7f4083f9c2247ee7165b5edb9d`,
results `5c9e045a2c63b0f73a96b79a66d656d44ec7eca34cdca9cb58dc15b76c645fa4`,
recovery graph `ba56997c57233678128e087ac25a3ff70a0a73e0cdc8bf04b35fa3f98dc3ef08`.
This admits runtime recovery-source dispatch and post-timeout input checks,
not subsequent MP-37/output sealing, MP-43 or complete profile qualification.

The earlier source-ownership correction at exact `602fa44820c68d55222971ffdd93e9c7105f3cdb`,
[run40213503846](https://github.com/Stonefly-Labs/Hoard/actions/runs/40213503846),
now independently passes all three Linux jobs: 279 foundations without
failures/errors/skips, 13-lock/18-package fresh replay and 127 scopes/1,818
witnesses. Its six-scope qualification-input metadata graph retains 71/22/9/0;
input `52dab298cfee5cfa75f9be4666c6fe6512b30ed1a06ea37b98a570713d6fd479`,
result `5c9290141ad44332229e29027720e8304eea120a13d0962650d1c8d01f2aae4e`.
This validates source compile ownership and the prior complete native recovery
graph, not the later seventh scope, timeout repair or MP-37 import. No later
native success or profile qualification is inferred.

The [plan checkpoint](../specs/007-provider-conformance/plan.md#partial-implementation-checkpoint)
records the delivered scope, review findings and remaining evidence. T002..T005
manifest/solution setup is complete; remaining task markers await their full
verification. No complete F-07 qualification CLI,
common consumer suites, contributor journey, five-profile CI baseline or certification is
available. Existing predecessor acceptance scripts remain the documented
entry points; full predecessor regressions were not rerun for this partial
checkpoint. No production API, production provider, cloud resource, release,
deployment, merge, or repository setting changed.

## Releases and deployment

[Version tags publish GitHub source releases](RELEASING.md). They do not run
product builds, package publication, OpenTofu, OIDC login, or deployment.
The [Azure identity root](../infra/bootstrap/README.md) merely prepares one
environment for a later, independently designed deployment workflow.
