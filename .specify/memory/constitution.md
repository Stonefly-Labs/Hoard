# Hoard Constitution

## Core Principles

### I. Cache First, Native Clients, Simple Personal Use

Hoard MUST remain an MIT-licensed, self-hosted pull-through package cache, not
a private package publishing registry. Supported ecosystems MUST work through
their standard clients and configuration without custom client plugins.
NuGet v3 MUST be the first usable protocol; additional ecosystems MUST NOT
delay or weaken its acceptance gate. Adapters MUST preserve native methods,
statuses, headers, encoding, authentication boundaries, and integrity behavior,
and MUST advertise only implemented and tested resources.

Personal and team deployments MUST share the same product and features without
proprietary paywalls. The curated personal distribution MUST run as one service
with SQLite and filesystem storage, loopback defaults, and no required cloud
account, external database, identity provider, or telemetry service. Team
exposure MUST be explicit and secured. Infrastructure choice MUST NOT become
mandatory complexity for personal users.

### II. Versioned Provider Contracts and Explicit Composition

Protocol, metadata persistence, artifact storage, and identity providers MUST
be independently distributable NuGet modules behind versioned contracts.
`Hoard.Abstractions` MUST own stable provider-neutral contracts with deliberately
minimal dependencies. `Hoard.Core` MUST depend on those abstractions, never
concrete providers, EF Core, `DbContext`, or provider-specific SDK types.
EF Core, relational schemas, and migrations MUST remain private to relational
persistence modules; provider details MUST NOT leak into endpoint slices.

The curated host MUST activate installed providers through validated startup
configuration. A custom host MUST explicitly reference and register additional
packages, then rebuild and restart. Modules MUST declare stable IDs, categories,
versions, host/abstractions compatibility ranges, dependencies, capabilities,
sanitized configuration requirements, health, and provenance/support metadata.
Composition MUST reject duplicate IDs, missing modules, dependency cycles,
incompatible versions, unsupported required capabilities, and invalid provider
cardinality with actionable diagnostics; silent fallback is prohibited.

Initially, multiple protocols and authentication schemes MAY coexist, with
exactly one authoritative metadata provider and one artifact provider.
Authentication MUST map to centralized authorization permissions. Disabled
modules MUST expose no routes, workers, or external connections. Required
initialization failure MUST prevent readiness. In-process providers MUST be
treated as trusted application code, not sandboxed extensions; arbitrary
assembly loading, hot installation/replacement, and a marketplace are outside
MVP scope.

### III. Vertical Slices with Centralized Correctness

Management operations and protocol-specific HTTP workflows MUST use vertical
feature slices that colocate endpoint mapping, DTOs, validation, authorization
requirements, orchestration, and focused tests as appropriate. Slices MUST use
explicit application/core contracts rather than another slice's internal
handler. Built-in DI and Minimal APIs are the default; MediatR and CQRS MUST
NOT be mandatory platform dependencies.

Cache identity and auth partitioning, freshness/revalidation, SSRF policy,
verified atomic publication, bounded streaming, single-flight coordination,
safe eviction/garbage collection, and shared audit/telemetry MUST remain
centralized services. Slices and providers MUST NOT duplicate or bypass these
invariants. Share mechanisms by correctness boundary, not by arbitrary layers;
this preserves consistent behavior as protocols and providers grow.

### IV. Verified Bytes, Bounded Work, and Safe Recovery

A valid cache entry MUST reference only a completely committed, integrity-checked
artifact. Core MUST coordinate staging, size/hash verification, blob commit,
and metadata publication so partial or corrupt content never becomes a hit.
Provider contracts MUST declare durability and publication capabilities without
assuming every store supports filesystem rename or cross-store transactions.
Cancellation, interrupted transfers, storage failure, and restart recovery MUST
leave no valid reference to incomplete content.

Cache keys MUST include registry identity, protocol canonicalization, and
response-varying authorization dimensions. Freshness, negative caching,
stale/offline reads, retries, and timeouts MUST be explicit and protocol-aware;
failures MUST NOT become success-shaped cache hits. Fresh immutable hits MUST
not require an upstream call. Concurrent identical cold requests MUST use
single-flight coordination within one process and re-check committed state.
I/O MUST use asynchronous, cancellation-aware streaming with bounded buffers,
concurrency, and backpressure. Eviction and garbage collection MUST protect
live references, shared digests, and active readers.

### V. Security and Isolation from the First Network Feature

Network-capable work MUST enforce security at introduction, not defer it to a
later hardening feature. Binding MUST default to loopback; non-loopback access
MUST require explicit configuration and a documented TLS/authentication posture.
Network-exposed management MUST be authenticated and authorized, directly or
through a documented trusted proxy. Browser login and noninteractive package/CI
credentials MUST remain distinct, with centralized permission checks.

Upstream fetching MUST use approved targets and centralized SSRF controls,
including DNS/IP and redirect validation against disallowed private, link-local,
and metadata-service destinations. Requests MUST NOT form an open proxy or
forward credentials across unauthorized origins. Paths, sizes, timeouts, and
resource use MUST be constrained. Secrets MUST use environment/file references
or approved resolvers, never plaintext metadata, committed examples, URLs, logs,
or telemetry. Diagnostics MUST be actionable and sanitized. Destructive
management actions MUST require explicit confirmation and authorization.

### VI. Evidence Before Capability Claims

Specifications MUST express user outcomes and independently verifiable
acceptance criteria. Plans and tasks MUST trace those requirements to focused
checks. Changed behavior MUST have regression/acceptance evidence; new checks
MUST demonstrate the intended failure before the implementation is accepted.
Architecture checks MUST reject forbidden dependency edges. Each advertised
provider MUST pass its category's common conformance suite, including failure
and recovery cases. Composition checks MUST cover incompatible/missing modules,
disabled activation, readiness failure, and sanitized errors.

Protocol adapters MUST pass end-to-end checks with real native clients,
beginning with `dotnet restore`, for cold, warm, concurrent, and upstream-failure
flows. Shared invariants MUST have focused tests plus integration evidence
through the relevant providers/protocols. Acceptance MUST include interrupted
or corrupt writes and relevant storage, concurrency, and network-boundary
failures. Custom-host examples MUST compile when introduced. Tests and docs
MUST distinguish supported combinations from prospective ones; an unchecked
task, generated artifact, or open PR is not delivery evidence.

### VII. Accessible Static Console, Capability-Driven Experience

The default console MUST use a supported stable Next.js release selected at
implementation, App Router, TypeScript, Tailwind CSS, and shadcn/ui. It MUST be
statically exportable and served by .NET, without SSR, server actions,
Node-only API routes, or a required Node runtime in the bundled distribution.
Management behavior MUST live in the .NET API; the UI MUST consume documented
APIs and sanitized capability descriptors, not concrete provider internals.

The console MUST distinguish installed, enabled, supported, and healthy
capabilities and MUST NOT offer unsupported operations. It MUST provide a
polished responsive dark/light experience, WCAG 2.2 AA accessibility targets,
keyboard operation, reduced-motion support, and clear loading, empty, error,
and destructive-action states. Usability MUST NOT conceal failures or weaken
correctness and authorization.

### VIII. Observable, Compatible, and Reversible Operations

Shared observability MUST use OpenTelemetry with sanitized structured
diagnostics for cache outcomes, upstream work, integrity failures, and resource
use. Metrics MUST avoid unbounded-cardinality labels and secret-bearing data.
Documented health/readiness MUST reflect required provider initialization
rather than merely a live process.

Public contracts and APIs MUST have semantic compatibility/versioning policies;
providers MUST declare supported platform ranges before publication. Schema
and configuration changes MUST include upgrade, backup, recovery, and rollback
instructions, with reversible migrations or a tested backup/restore path where
reversal is unsafe. Runtime configuration changes MUST NOT imply live provider
replacement. Documentation MUST state supported protocols, operational limits,
and actual versus planned behavior. Original code MUST remain MIT-licensed;
third-party licenses and attribution MUST be checked.

## Technology and Distribution Constraints

- The backend MUST target .NET 10 and ASP.NET Core using nullable-aware types,
  built-in DI, Minimal APIs, OpenAPI, and OpenTelemetry.
- `Hoard.Hosting` MUST own composition/lifecycle and HTTP integration;
  `Hoard.Application` MUST own management slices; protocol slices MUST remain
  within `Hoard.Protocols.*`. Concrete `Hoard.Host` MUST assemble the installed
  providers. Approved Hosting contracts MAY support endpoint/identity wiring;
  they MUST NOT introduce core-to-provider or cross-slice internal coupling.
- The first usable distribution MUST be single-node NuGet v3 + SQLite +
  filesystem with bundled static UI. PostgreSQL, other protocols, object stores,
  and identity integrations MUST remain separately scoped provider work, not
  assumed existing capabilities. NoSQL interchangeability requires its own
  contract proof; HA and distributed coordination are deferred.
- Azure MUST remain optional infrastructure. OpenTofu MUST own authorized
  infrastructure changes; environment-scoped GitHub OIDC MUST replace client
  secrets. Writing IaC MUST NOT authorize applying it. Source release tags MUST
  NOT imply deployment, package publication, or cloud permissions.
- The simplest complete solution MUST be preferred. Planned signatures,
  packages, routes, and examples MUST NOT be presented as implemented APIs.
  Foundation/governance work MUST NOT scaffold unrequested product projects,
  manifests, runtimes, CI/CD, or cloud resources.

## Development Workflow and Quality Gates

- Work MUST use an explicit type-prefixed branch, never commits on `main`,
  detached HEAD, or release tags. Contributors MUST inspect branch/worktree,
  preserve unrelated changes, commit coherent work, and push immediately after
  every commit. Failed pushes MUST be reported as unshared checkpoints.
- Each `hoard-speckit` invocation MUST execute at most one scheduled stage
  through its installed `speckit-*` skill. The tracked
  `.specify/hoard-flow.json` MUST own progress; an interrupted `running` stage
  MUST resume the same artifacts without resetting or fabricating evidence.
  Feature context MUST use the recorded directory, not branch-name inference.
- Constitution and completion checkpoints MUST merge into `origin/main` before
  a new specification begins. Backlog selection MUST honor completed
  dependencies. Each successful stage MUST finish with real evidence and
  commit/push its artifacts; incomplete features MUST use draft PRs to `main`.
  Merges MUST require explicit maintainer authorization.
- Custom requirements-quality checklists MUST remain reviewer-owned;
  generation MUST NOT count as approval. Implementation MUST wait for reviewer
  approval or explicit reviewer authorization. Analysis MUST remain read-only;
  significant findings MUST block progress until separately authorized
  remediation and a fresh analysis resolve them.
- Relevant existing format/type/unit/integration checks MUST pass before
  acceptance, or explicit limitations MUST block affected capability claims.
  Until product tooling exists, repository-tool checks are
  `python3 -m unittest discover -s tests/tooling -v`; mock-only IaC checks are
  documented in `docs/DEVELOPMENT.md`. Features MUST introduce and document
  applicable product checks rather than invent successful commands.
- README and affected guides, examples, diagrams, and spec artifacts MUST be
  updated before merge; unaffected documents MUST have an explicit reason.
  PRs MUST use the repository template and include exact relevant check
  commands/results, compatibility impact, operational steps, and risks.
  Substantial provider, dependency, module-lifecycle, or shared-invariant
  changes MUST receive `hoard-architecture-review` before PR handoff.

## Governance

This constitution governs Hoard specifications, plans, implementations, and
reviews. `MUST`, `MUST NOT`, and `MAY` express mandatory rules, prohibitions,
and permitted choices. The charter and product specification describe outcomes;
`docs/ARCHITECTURE.md` and ADR-0001 describe the architectural baseline;
`docs/DEVELOPMENT.md` supplies operational workflow. Conflicts MUST be surfaced
and resolved explicitly, not silently interpreted around this constitution.

Adoption and amendments MUST be reviewed through a PR targeting `main` and
merged only with maintainer authorization. An amendment MUST state its
rationale, affected principles, compatibility consequences, migration plan,
and required documentation updates. Constitution versions MUST follow SemVer:
MAJOR for incompatible principle removal/redefinition, MINOR for new principles
or materially expanded guidance, PATCH for non-semantic clarification. The
original ratification date MUST be preserved; the amendment date MUST reflect
the actual change date.

Every plan and PR MUST assess applicable constitutional rules and record evidence
or blockers. Architectural departures MUST include an ADR and explicit
maintainer approval; a departure that changes a constitutional rule MUST amend
this constitution before dependent work proceeds. Analysis MUST NOT dilute a
principle to accommodate an implementation. Unresolved compliance, integrity,
security, or acceptance failures MUST block progression and merge.

**Version**: 1.0.0 | **Ratified**: 2026-10-20 | **Last Amended**: 2026-10-20
