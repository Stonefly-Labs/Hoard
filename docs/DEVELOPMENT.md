# Development workflow

## Foundation boundary

The bootstrap established contributor tools and reserved architecture boundaries.
F-01 adds four .NET library projects, immutable provider declarations, explicit
registration, and compile/package/boundary acceptance tooling. F-02 adds
opt-in fixture-tested lifecycle in Hosting. F-03 adds fixture-backed configuration,
owner-scoped local secrets and explicit synthetic conversion through that same
lifecycle. F-04 adds opt-in protected discovery slices in Application and safe
Hosting observations; F-05 adds separate BCL-only metadata operations with
independent SQLite/memory qualification fixtures. Core remains empty. No caching engine,
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

## Releases and deployment

[Version tags publish GitHub source releases](RELEASING.md). They do not run
product builds, package publication, OpenTofu, OIDC login, or deployment.
The [Azure identity root](../infra/bootstrap/README.md) merely prepares one
environment for a later, independently designed deployment workflow.
