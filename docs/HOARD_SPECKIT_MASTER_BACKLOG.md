# Hoard — Spec Kit Master Specification Backlog

**Status:** Revised v0.2 implementation inventory (2026-10-20) · **Product:** Hoard · **License:** MIT · **Source baseline:** Product Charter, Product Vision, Product Specification (2026-10-19)

> **Purpose.** This is a master *feature specification* inventory and prompt library: the original 35 specs are preserved, with eight new architecture foundation specs (F-01–F-08). These are not already-created Spec Kit specifications. Each numbered entry is meant to become an independently reviewable `/speckit.specify` feature. Scope and priority are proposals that should be refined during implementation.

## How to use this document

1. Initialize GitHub Spec Kit in the Hoard repository and create the project constitution **once**. Review the existing Hoard charter, vision, and product spec before generating features.
2. Work in dependency order. Paste **one** prompt at a time into your coding agent using `/speckit.specify` (the block includes the command). Don't paste the entire backlog as a single feature.
3. Review the generated spec and clarify unclear requirements before generating a plan and tasks. Use `/speckit.plan`, `/speckit.tasks`, `/speckit.implement` and quality gates as appropriate. `/speckit.specify` focuses on user outcomes, not implementation details. See [GitHub Spec Kit quickstart](https://github.com/github/spec-kit/blob/main/docs/quickstart.md).
4. Mark a spec completed only after its acceptance scenarios and appropriate real-client or fault-injection tests pass. Dependencies below refer to **capabilities ready for integration**, not necessarily entire feature rollout.
5. Feature sequence numbers are logical backlog identifiers, not a guarantee of branch naming or release versions. Spec Kit manages active feature directories; don't rely on `git checkout` alone to select a feature.

## Shared guardrails (apply to every generated specification)

- Hoard is a **self-hosted pull-through cache**, not a general private publishing registry. No proprietary paywalls or a required SaaS service.
- **One product, two deployment profiles**: personal laptop (SQLite + filesystem, loopback default) and shared team/CI (hardened network exposure, optional PostgreSQL/object storage). A personal install must stay lightweight.
- **NuGet first**, then Go and Maven, then npm, then Python/PyPI and Rust/Cargo. The MVP must be genuinely useful with NuGet alone.
- **Security/integrity fundamentals are never postponed** until later security feature specs: no partial blobs as hits, verify content, prevent SSRF, protect management exposure and credentials from the first network-capable implementation.
- Management UI: **latest stable Next.js at implementation**, App Router, TypeScript, Tailwind CSS, shadcn/ui, polished custom design tokens, accessible primitives and responsive dark/light modes. The default UI must be statically exportable and served by the .NET host; optional Node-hosted console is a later choice.
- Implementation constraints belong principally in the constitution and technical planning: .NET 10 ASP.NET Core **composable** modular monolith; `Hoard.Core` independent of EF Core/concrete providers; relational provider implementations may use EF Core; OpenTelemetry, OpenAPI and real-client tests.
- Vertical Slice Architecture for management workflows and protocol-specific endpoints (endpoint, DTO, validation, handler and focused tests colocated). Reusable cache lifecycle, atomic artifact integrity, streaming, security, coordination and provider abstractions belong in shared core services; no mandatory MediatR/CQRS.
- Independently distributed NuGet packages + explicit host composition/startup activation. Curated default distribution is configuration-driven; arbitrary dynamic assembly loading, marketplace and hot install are out of scope.
- Public module descriptors declare version/compatibility/capabilities/configuration; provider conformance suites and compatibility failures must be tested; modules are trusted in-process code.
- Honest protocol support: never advertise unsupported registry resources; preserve correct status, headers, auth boundaries, local download URLs and checksum behavior.

## Suggested initial constitution prompt

```text
/speckit.constitution Hoard is an MIT-licensed self-hosted pull-through package cache, with NuGet first, a lightweight SQLite/filesystem personal distribution, and secure team deployment. .NET 10 ASP.NET Core modular monolith with NuGet-distributed protocol/persistence/blob/identity providers, stable Hoard.Abstractions contracts, provider capabilities/descriptors, explicit module registration and startup validation. Hoard.Core must never reference concrete providers or EF Core; EF Core belongs inside relational persistence modules. Implement HTTP management features and ecosystem protocol endpoints as Vertical Slice Architecture (colocated DTOs, validation, handlers, endpoint registration and tests), while shared correctness concerns—cache keys/auth partitioning, freshness, SSRF policy, atomic verified blobs, streaming, single-flight concurrency, eviction and observability—remain centralized domain/platform services rather than replicated in slices. Built-in DI and Minimal APIs; no mandatory MediatR. Curated distribution uses config-driven activation; custom host references additional NuGet packages. No dynamic arbitrary plugin loading or hot replacement for MVP. Fail startup on invalid modules/versions; all providers pass common conformance tests and protocol adapters pass real-client end-to-end tests. Next.js App Router + Tailwind/shadcn/ui polished accessible statically exported UI served by .NET. Protect secrets, credentials and network boundary, preserve native protocols, provide reversible migrations and clear docs. Feature specifications emphasize user outcomes and acceptance criteria.
```

## Phase gates

| Phase | Gate | Specs |
|---|---|---|
| A0 — Composable platform foundation | Versioned contracts, module lifecycle, provider categories, config and conformance baseline | F-01–F-07, 01 |
| A — Secure foundations | Runnable personal cache foundation, reliable storage, safe HTTP semantics and vertical slices | 02–06, 18 (security acceptance baseline) |
| B — NuGet vertical slice | Real dotnet restore cold/warm, polished starter console, distributable artifact | 07–14, 35 (foundation) |
| C — More ecosystems | Go, Maven, npm production test suites and secure team operations; identity module boundary | 15–18, F-08, 24–25 |
| D — Differentiation | Practical retention, offline cache, lockfile prewarming and excellent analytics | 19–23, 32–33 |
| E — Extended providers | PostgreSQL, object storage, PyPI, Cargo, security intelligence | 26–31 |
| F — Scale-out | Multi-replica only if demand justifies it | 34 |

**Priority codes:** P0 = first usable NuGet release; P1 = near-term differentiation/robust team operation; P2 = ecosystem expansion and advanced capabilities; P3 = explicitly deferred high complexity. The numbered inventory is in *feature-family order*, not a strict execution queue; follow the dependency IDs and phase gates. Spec 18's essential safety controls must be present for P0 even though extended hardening is a P1 workstream. Likewise the contributor/release baseline of 35 starts on day one.

## Updated implementation order / dependency policy

1. Start with `F-01` (contracts/package graph), `F-02` (lifecycle), `F-03` (configuration), and `F-05`/`F-06` (persistence/storage contracts) **before** concrete providers.
2. Establish `F-04` capabilities and `F-07` conformance harness while constructing the first working provider implementations.
3. Build original `SPEC-01` through `SPEC-14` as the first usable NuGet product; organize app and NuGet endpoints as vertical slices, not a layers-first Controller/Service/Repository scaffolding.
4. Prove architecture with a second ecosystem adapter and PostgreSQL early enough to catch leaky contracts; the original priority labels remain release planning proposals.
5. Add `F-08` before `SPEC-24`, then expand provider families gradually. Keep original numeric IDs stable for references.

All original 35 feature specifications and their prompts remain below. Their shared prerequisites and architectural constraints are updated by the new F-series specifications and by the preceding guardrails, even where the original standalone prompt has not been rewritten verbatim.

## Master inventory

| ID | Priority | Spec | Depends on |
|---|---|---|---|
| F-01 | P0 | [Platform package boundaries and provider contracts](#foundation-f-01) | None |
| F-02 | P0 | [Module registry, composition and lifecycle](#foundation-f-02) | F-01 |
| F-03 | P0 | [Provider configuration and activation validation](#foundation-f-03) | F-01,F-02 |
| F-04 | P0 | [Module capabilities and management discovery API](#foundation-f-04) | F-01,F-02,F-03 |
| F-05 | P0 | [Metadata persistence provider contract](#foundation-f-05) | F-01 |
| F-06 | P0 | [Artifact blob storage provider contract](#foundation-f-06) | F-01 |
| F-07 | P0 | [Provider conformance, version compatibility and composition tests](#foundation-f-07) | F-01–F-06 |
| F-08 | P1 | [Identity scheme and authorization provider architecture](#foundation-f-08) | F-01,F-02,F-03,18 |
| 01 | P0 | [Project foundation and deployment profiles](#spec-01) | F-01,F-02,F-03 |
| 02 | P0 | [Registry configuration and upstream governance](#spec-02) | 01 |
| 03 | P0 | [Metadata persistence and schema lifecycle](#spec-03) | 01,F-05,F-07 |
| 04 | P0 | [Content-addressed artifact storage](#spec-04) | 01,03,F-06,F-07 |
| 05 | P0 | [HTTP cache lifecycle and freshness rules](#spec-05) | 02,03,04 |
| 06 | P0 | [Concurrent fetch deduplication and streaming](#spec-06) | 04,05 |
| 07 | P0 | [NuGet v3 discovery and flat-container proxy](#spec-07) | 02,05,06,F-01,F-02,F-04 |
| 08 | P0 | [NuGet registration and compatibility coverage](#spec-08) | 07 |
| 09 | P0 | [Real-client protocol integration test harness](#spec-09) | 07 |
| 10 | P0 | [Management API, pagination and OpenAPI](#spec-10) | 01,03,05,F-04 |
| 11 | P0 | [Next.js console shell and design system](#spec-11) | 01,10 |
| 12 | P0 | [Overview, package explorer and request activity](#spec-12) | 10,11 |
| 13 | P0 | [Setup assistant and ecosystem-native snippets](#spec-13) | 07,11 |
| 14 | P0 | [Local distribution, Docker and upgrade experience](#spec-14) | 01,03,11,F-03 |
| 15 | P1 | [Go GOPROXY adapter](#spec-15) | 02,05,06,09,13 |
| 16 | P1 | [Maven repository adapter](#spec-16) | 02,05,06,09,13 |
| 17 | P1 | [npm registry adapter](#spec-17) | 02,05,06,09,13 |
| 18 | P1 | [Security boundaries and secrets hardening](#spec-18) | 01,02,05,10 |
| 19 | P1 | [Retention, quotas, eviction and garbage collection](#spec-19) | 03,04,10,12 |
| 20 | P1 | [Cache pinning and retention exceptions](#spec-20) | 19,12 |
| 21 | P1 | [Offline mode and stale-if-error behavior](#spec-21) | 05,13,19 |
| 22 | P1 | [Lockfile import and cache prewarming](#spec-22) | 07,15,16,17,19,20 |
| 23 | P1 | [Detailed metrics, bandwidth savings and diagnostics](#spec-23) | 05,10,12 |
| 24 | P1 | [Team OIDC login, scoped access tokens and permissions](#spec-24) | 10,11,18,F-08 |
| 25 | P1 | [Audit trail and sensitive operations](#spec-25) | 10,18,24 |
| 26 | P2 | [PostgreSQL team persistence](#spec-26) | 03,14,F-05,F-07 |
| 27 | P2 | [S3-compatible and Azure Blob storage providers](#spec-27) | 04,19,26,F-06,F-07 |
| 28 | P2 | [Python PyPI Simple API adapter](#spec-28) | 02,05,06,09,13 |
| 29 | P2 | [Cargo sparse registry adapter](#spec-29) | 02,05,06,09,13 |
| 30 | P2 | [Supply-chain controls: quarantine and package cooldown](#spec-30) | 05,18,20,22 |
| 31 | P2 | [Vulnerability intelligence and package risk visibility](#spec-31) | 03,12,18,30 |
| 32 | P2 | [Self-service CI integrations and preflight verification](#spec-32) | 13,21,22,23,24 |
| 33 | P2 | [Recovery, integrity audit and disaster restore](#spec-33) | 03,04,14,19,26,27 |
| 34 | P3 | [Multi-instance coordination and high availability](#spec-34) | 24,26,27 |
| 35 | P1 | [Open-source contributor experience and release governance](#spec-35) | 01,09,14,F-01,F-07 |

## Foundational architecture specifications (new in v0.2)

These are build-enabling implementation capabilities; preserve the original SPEC-01–35 numbering and avoid counting them as already implemented. Every prompt below may be sent independently to `/speckit.specify` after the constitution is established.

<a id="foundation-f-01"></a>
### F-01: Platform package boundaries and provider contracts

**Priority:** P0  
**Dependencies:** None  
**Description:** Define dependency graph for Hoard.Host, Hosting, Abstractions, Core, Application vertical slices and independently distributed Protocols/Persistence/Storage/Identity providers. Identify stable contract ownership, no circular references, no EF Core dependency in Core, explicit registration contracts and public API compatibility policy.

**Definition of done / acceptance focus:** A compilation/reference test proves Core can build without any concrete provider; a fake third-party provider compiles against public abstractions; architecture reference tests fail forbidden dependencies.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify an open extensibility foundation for Hoard that allows independent package-manager, metadata, artifact storage and identity providers without modifying the caching engine. Include versioned contracts, clean package boundaries, a small custom-host experience, extensibility constraints and acceptance checks that prevent concrete-provider coupling.
```

<a id="foundation-f-02"></a>
### F-02: Module registry, composition and lifecycle

**Priority:** P0  
**Dependencies:** F-01  
**Description:** Provide module descriptors, unique IDs, startup registration/discovery of compiled-in packages, validated ordering, service registration, endpoint mapping, initialization, health/readiness and shutdown. Disable inactive module routes/workers; do not use arbitrary hot loading.

**Definition of done / acceptance focus:** Enabled NuGet module maps endpoints; disabled module maps none; conflicting IDs, cycles, absent dependencies and initialization failures fail startup; proper shutdown observed.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify how operators assemble Hoard from installed provider NuGet packages and activate selected modules at startup. Define safe module lifecycle, route registration, dependency resolution, readiness, enabled/disabled behavior, diagnostic errors, restart semantics and default-versus-custom distribution expectations.
```

<a id="foundation-f-03"></a>
### F-03: Provider configuration and activation validation

**Priority:** P0  
**Dependencies:** F-01,F-02  
**Description:** Declare provider-specific options/schema with secret redaction, configuration precedence, selection cardinality (one metadata + blob, multiple protocols/auth schemes), compatibility checks, source-of-truth and upgrade behavior.

**Definition of done / acceptance focus:** Missing configured provider and malformed options fail startup; no accidental fallback to insecure modes; log/diagnostics redact secrets; config-driven bundled-provider switch works after restart.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify secure, intelligible configuration of installed Hoard modules, including enablement, provider selection, per-provider settings and secret references. Include precedence, invalid configurations, disabled modules, compatibility failures, safe migration, diagnostics and restart behavior.
```

<a id="foundation-f-04"></a>
### F-04: Module capabilities and management discovery API

**Priority:** P0  
**Dependencies:** F-01,F-02,F-03  
**Description:** Expose module IDs, category, version, support status, enabled/available state, readiness, feature capabilities and sanitized configuration metadata through authorized management API to inform Next.js UI.

**Definition of done / acceptance focus:** Capabilities endpoint matches actual enabled HTTP routes/services; no secrets exposed; UI hides unsupported actions and distinguishes unavailable vs disabled.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify a management experience where users can inspect installed, enabled and healthy Hoard modules, what each supports, and why a capability is unavailable. Include secure API discovery, UI representation, actionable diagnostics and truthful feature advertisement.
```

<a id="foundation-f-05"></a>
### F-05: Metadata persistence provider contract

**Priority:** P0  
**Dependencies:** F-01  
**Description:** Define provider-agnostic repository/transaction operations for registry, package metadata, cache entries, reference integrity, leases, policy and aggregates. EF Core/migrations are private to relational implementations. Clarify atomicity, isolation and concurrency requirements; avoid pretending NoSQL has EF Core semantics.

**Definition of done / acceptance focus:** SQLite passes deterministic contract tests for isolation, unique identities, migrations and crash recovery; Core does not use DbContext; second provider can implement without application refactor.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify interchangeable Hoard metadata persistence with identical correctness guarantees for registry state, cached entries, transactions, concurrent writes and schema upgrades. Include portability expectations, failure recovery, provider-specific implementation boundaries and measurable conformance.
```

<a id="foundation-f-06"></a>
### F-06: Artifact blob storage provider contract

**Priority:** P0  
**Dependencies:** F-01  
**Description:** Define streaming read/write, temp/staging, verified commit visibility, content-addressable identity, conditional publication, deletion, leases, failure recovery and capability differences between file/object stores. Do not require universal atomic rename.

**Definition of done / acceptance focus:** Filesystem passes shared conformance; interrupted/corrupt write never becomes a hit; low-memory multi-GB streaming tested; alternative object store can be added without core rewrite.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify interchangeable Hoard artifact stores that stream large content, verify integrity and never expose incomplete blobs. Cover commit semantics, crash recovery, content addressing, deletion, provider capabilities and differences between filesystem and object storage.
```

<a id="foundation-f-07"></a>
### F-07: Provider conformance, version compatibility and composition tests

**Priority:** P0  
**Dependencies:** F-01–F-06  
**Description:** Create reusable category-specific provider contract suites, fake/fixture providers, compile dependency rules, version matrix, default/custom host smoke tests, integration DB/object-store tests and incompatible module failure tests. Real-client protocol tests remain SPEC-09.

**Definition of done / acceptance focus:** CI runs same suite against each qualifying provider and at least two independently implemented provider options as delivered; documented support/compatibility matrix; red/green tests for host composition.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify repeatable contract and compatibility certification for Hoard modules: consistent provider semantics, lifecycle/startup failure validation, API/version mismatch handling, supported composition permutations, test templates for contributors and CI reporting.
```

<a id="foundation-f-08"></a>
### F-08: Identity scheme and authorization provider architecture

**Priority:** P1  
**Dependencies:** F-01,F-02,F-03,18  
**Description:** Separate OIDC browser login, Entra conveniences, local users and package-client/API tokens from normalized Hoard authorization. Define scheme composition, principal/role mapping, secret boundaries, endpoint policies and default network restrictions.

**Definition of done / acceptance focus:** Generic OIDC and local scheme can coexist when selected; tokens are scoped; protected endpoints remain protected if a provider is disabled or misconfigured; audit shows normalized actor.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify configurable Hoard authentication providers and standardized authorization for browser users and package-manager/CI clients. Cover OIDC/Entra, local/API tokens, identity mapping, coexistence, management-versus-package permissions, fail-closed behavior and provider compliance.
```

## Detailed specifications and ready-to-use prompts

<a id="spec-01"></a>
### SPEC-01: Project foundation and deployment profiles

**Priority:** P0  
**Dependencies:** None  
**Description:** Establish a runnable Hoard application composed from registered modules and one installable product, personal and team profiles, configuration validation, health endpoints, embedded management UI asset delivery, and clear startup diagnostics. Personal mode has safe loopback defaults and no required external services; team mode requires explicit network/security decisions.

**Definition of done / acceptance focus:** A clean install launches on a laptop with a persistent data directory; invalid config fails intelligibly; team exposure cannot silently inherit anonymous administrative access; startup and shutdown are clean.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify As a developer or administrator, I want to start Hoard as a single local process or container and select personal or team deployment settings without switching products. Specify onboarding, valid configuration, startup behavior, health feedback, persisted configuration, unsafe-exposure prevention, and upgrade compatibility. Include first-run, restart, invalid-config, and network-exposure acceptance scenarios.
```

<a id="spec-02"></a>
### SPEC-02: Registry configuration and upstream governance

**Priority:** P0  
**Dependencies:** 01  
**Description:** Manage enabled registries by unique ID, ecosystem, permitted upstream endpoints, base URL mapping and policy defaults. Include connectivity diagnostics, read-only configuration support for automation and change validation. Treat upstream definitions as trusted administrative configuration, not user-supplied arbitrary URLs.

**Definition of done / acceptance focus:** Administrators can add, disable, diagnose and update configured registries; invalid endpoints and ID collisions are rejected; requests cannot select unconfigured hosts.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify how Hoard users configure multiple named upstream registries, safely test connectivity, change or disable them, and see current status. Ensure public package requests can only use approved registry targets and that changes have predictable impact on cached entries and client URLs. Cover invalid URLs, duplicate IDs, unavailable endpoints, and safe error feedback.
```

<a id="spec-03"></a>
### SPEC-03: Metadata persistence and schema lifecycle

**Priority:** P0  
**Dependencies:** 01  
**Description:** Implement the SQLite metadata provider against F-05 contracts; persist registries, canonical package identities, artifact references, HTTP cache entries, fetch status, policy records and aggregates. Preserve upstream identity and vary dimensions to prevent cross-registry or cross-auth contamination. Implement recoverable schema upgrades and backup-friendly database behavior.

**Definition of done / acceptance focus:** Restart retains entries and references; unique constraints reject collisions; interrupted migrations have documented recovery; no stored entry references an uncommitted blob.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify persistent metadata behavior for a self-hosted package cache that supports restarts, version upgrades, different upstream registries and multiple protocol request forms. Define consistency rules, safe migrations, data retention, backup/restore expectations, and failure scenarios, while keeping the personal installation dependency-free.
```

<a id="spec-04"></a>
### SPEC-04: Content-addressed artifact storage

**Priority:** P0  
**Dependencies:** 01,03  
**Description:** Implement the filesystem artifact storage provider against F-06 contracts: store validated immutable payloads by SHA-256 digest on a local filesystem, with staged writes, atomic visibility, deduplication, content-length verification and safe paths. Keep logical cache entries distinct from blobs and avoid public exposure of staging files.

**Definition of done / acceptance focus:** Identical bytes deduplicate; interrupted writes are never served; stored digest matches content; no traversal possible; restart can clean abandoned staging files.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify reliable local artifact storage where package downloads are staged, verified, atomically committed, shared across logical references when identical, and never served while incomplete. Define user-visible behavior on disk-full, interruption, corruption, duplicate content, deletion, and restart.
```

<a id="spec-05"></a>
### SPEC-05: HTTP cache lifecycle and freshness rules

**Priority:** P0  
**Dependencies:** 02,03,04  
**Description:** Single orchestration path for adapter-specific request identities, cache hits/misses, mutable registry metadata vs immutable artifacts, HTTP validators, negative caching, upstream retries and stale response policy. Respect response-varying headers and auth partitioning.

**Definition of done / acceptance focus:** Fresh immutable hits make zero upstream calls; stale metadata revalidates; 401/403 not shared-cached; unsafe variants cannot collide; bounded failure handling is observable.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify transparent pull-through caching behavior for native package managers: fresh hits, first misses, metadata refresh, conditional revalidation, negative results, redirects, errors, and stale entries. Preserve package-manager semantics and prevent serving one registrant or authorization variant to another. Cover response status, headers, freshness, and failure paths.
```

<a id="spec-06"></a>
### SPEC-06: Concurrent fetch deduplication and streaming

**Priority:** P0  
**Dependencies:** 04,05  
**Description:** Per-key single-flight fetches within one instance, bounded-memory streaming, cancellation semantics that do not abort all waiters, upstream concurrency limits, graceful retries and client disconnect handling. Defer distributed locks.

**Definition of done / acceptance focus:** 20 simultaneous same-key cold requests produce one upstream transfer on one node; no unbounded memory growth; cancellation and failures release waiters and permit retry.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify the experience when many developers or CI agents request the same uncached artifact at once. Hoard should avoid redundant upstream downloads, stream large files without excessive memory, safely handle disconnected clients, and report failures consistently. Include concurrency, cancellation, timeout and recovery acceptance tests.
```

<a id="spec-07"></a>
### SPEC-07: NuGet v3 discovery and flat-container proxy

**Priority:** P0  
**Dependencies:** 02,05,06  
**Description:** NuGet independently distributable protocol module with feature-local Minimal API slices using shared cache contracts; lead adapter for NuGet v3: local service-index discovery, supported resource URLs, package version listing, nupkg fetching, client configuration, canonical package IDs/versions and upstream endpoint rewrite rules. Advertise only supported routes.

**Definition of done / acceptance focus:** Clean/warm dotnet restore and dotnet add package pass; all advertised required URLs remain inside Hoard; original packages pass integrity checks; unsupported routes are not misrepresented.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify a NuGet v3 pull-through cache usable as a standard NuGet source in NuGet.Config. Users must restore direct and transitive packages with unmodified dotnet tooling; discovery, version lookup and package downloading must remain routed through Hoard. Cover first restore, second restore, version normalization, bad versions, upstream outage, and unsupported resource behavior.
```

<a id="spec-08"></a>
### SPEC-08: NuGet registration and compatibility coverage

**Priority:** P0  
**Dependencies:** 07  
**Description:** NuGet v3 registration pages and metadata demanded by commonly used official clients; protocol-specific JSON URL handling, prerelease and version edge cases, optional search capability disclosure, HEAD/range behavior as supported and regression fixtures.

**Definition of done / acceptance focus:** Representative modern dotnet/NuGet client flows work; registration URLs are local; tests cover semantic version/casing edge cases and errors; compatibility matrix is explicit.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify complete NuGet consumption workflows beyond basic package downloads, including registration metadata, prerelease versions, version normalization, and common dotnet client commands. Define observable compatibility, supported and unsupported NuGet v3 capabilities, protocol response accuracy, and scenarios that prevent direct upstream bypass.
```

<a id="spec-09"></a>
### SPEC-09: Real-client protocol integration test harness

**Priority:** P0  
**Dependencies:** 07  
**Description:** Black-box integration harness with disposable cache/upstream test instances, reproducible fixtures, test runners invoking real dotnet clients, request-count assertion, corruption and outage injection, and CI execution. Expand harness for later adapters.

**Definition of done / acceptance focus:** CI reliably validates cold/warm restores, single-flight request count, crash safety, metadata rewrite, upstream outage and no unintended internet bypass.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify an automated compatibility and regression test experience using real package-manager clients and controlled test registries. For the first release prioritize dotnet restore and package-add flows. Tests must prove correct returned packages, expected upstream request counts, safe behavior during failures, and protocol conformance without relying exclusively on mocks.
```

<a id="spec-10"></a>
### SPEC-10: Management API, pagination and OpenAPI

**Priority:** P0  
**Dependencies:** 01,03,05  
**Description:** Versioned read and action APIs for overview, registries, packages, artifacts, requests, health, client setup and eviction. Stable error envelope, pagination/filtering, validation, auth boundaries, typed contract generation and idempotency where relevant.

**Definition of done / acceptance focus:** OpenAPI published; generated client compiles; pagination stable; error contracts clear; privileged actions cannot be performed anonymously on exposed team deployments.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify a stable management API so Hoard users and the web console can inspect registry state, packages, cache performance, recent requests, setup instructions and maintenance actions. Define searchable/paginated behavior, clear error messages, permission boundaries and backward-compatible versioning expectations.
```

<a id="spec-11"></a>
### SPEC-11: Next.js console shell and design system

**Priority:** P0  
**Dependencies:** 01,10  
**Description:** Slick responsive management console using latest stable Next.js App Router at implementation, TypeScript, Tailwind CSS, shadcn/ui with accessible primitives, Lucide, theme tokens and dark/light modes. Default static export integrates into .NET host: no server actions, Next API routes, runtime SSR or other incompatible assumptions.

**Definition of done / acceptance focus:** Same build works as static bundled console; responsive keyboard-accessible navigation; meaningful empty/loading/error states; WCAG 2.2 AA target and reduced motion respected.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify the visual and interaction foundations for Hoard’s polished management console. Users should experience a distinctive modern developer tool, with cohesive dark and light themes, accessible navigation, responsive layouts, strong information hierarchy, and reliable loading/empty/error states. The default experience must run from a single Hoard server without needing a separate Node server.
```

<a id="spec-12"></a>
### SPEC-12: Overview, package explorer and request activity

**Priority:** P0  
**Dependencies:** 10,11  
**Description:** Overview KPIs, actionable service and upstream status, sortable/filterable package lists and artifact details, checksum display, status-tagged request activity and drilldowns. Aggregation minimizes high-volume DB writes.

**Definition of done / acceptance focus:** Users can locate package/version, inspect source/digest and see hit vs miss; dashboards accurately reflect representative test traffic; empty states guide next actions.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify an operational dashboard that immediately shows whether Hoard is working and why it matters. Users can see cache hits/misses, stored bytes, fetched bandwidth, upstream health, recent requests, and search or filter cached packages by ecosystem, registry and version. Describe meaningful drilldowns and empty/error states.
```

<a id="spec-13"></a>
### SPEC-13: Setup assistant and ecosystem-native snippets

**Priority:** P0  
**Dependencies:** 07,11  
**Description:** Generate safe, copyable instructions and examples for NuGet.Config and dotnet commands first; progressively add Go, Maven, npm, pip, Cargo. Include server public-base URL, TLS/credentials considerations and verification action.

**Definition of done / acceptance focus:** User configures dotnet from UI in minutes; snippets use actual configured base URL; no secrets copied in plaintext; validation instructions prove use of Hoard.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify a guided package-manager setup experience that helps a developer point standard tooling at Hoard without installing a special CLI. Start with NuGet and support additional ecosystems when available. Include OS-appropriate copyable snippets, configurable registry URLs, troubleshooting, success verification, and security warnings for team-hosted caches.
```

<a id="spec-14"></a>
### SPEC-14: Local distribution, Docker and upgrade experience

**Priority:** P0  
**Dependencies:** 01,03,11  
**Description:** Self-contained binary/container, multi-platform packaging, persistence mount contract, signal handling, safe upgrades, immutable image tags, release notes, config examples and quickstart under five minutes.

**Definition of done / acceptance focus:** Clean host/container install works; upgrades preserve cache; UI loads without Node; persistent data survives container replacement; release artifacts are reproducible.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify installation and lifecycle experiences for individual developers and small teams: download/run or start a single Docker container, initialize persistent storage, reach the console, upgrade without data loss, and recover common errors. The default distribution must not require external PostgreSQL, Redis or a separate Next.js runtime.
```

<a id="spec-15"></a>
### SPEC-15: Go GOPROXY adapter

**Priority:** P1  
**Dependencies:** 02,05,06,09,13  
**Description:** GOPROXY module endpoint support for list/info/mod/zip, path escaping, module version handling, checksums, proxy environment configuration and explicit private-module/GOSUMDB guidance.

**Definition of done / acceptance focus:** go mod download and go build pass in cold/warm tests; module escaping correct; no accidental checksum bypass; proxy fallback behavior documented.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify a native Go module proxy so developers can point GOPROXY at Hoard and use normal go build and go mod download commands. Support module version metadata and artifacts, correct path-escaping behavior, upstream outages and clear guidance on checksum verification and private modules.
```

<a id="spec-16"></a>
### SPEC-16: Maven repository adapter

**Priority:** P1  
**Dependencies:** 02,05,06,09,13  
**Description:** Maven2 layout for POM/JAR/source artifacts and metadata, checksum files, snapshot freshness distinctions, parent POM and plugin dependencies, settings.xml mirror instructions; Gradle compatibility tests where feasible.

**Definition of done / acceptance focus:** mvn dependency:resolve/build passes for releases and snapshots; parent/plugin paths work; changing snapshots obey freshness policy; checksum handling correct.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify a transparent Maven-compatible repository proxy so Maven users can configure Hoard as a mirror and restore ordinary dependencies, transitive POMs and plugin artifacts. Include releases versus mutable snapshots, metadata refresh, checksums, missing dependencies and offline behavior.
```

<a id="spec-17"></a>
### SPEC-17: npm registry adapter

**Priority:** P1  
**Dependencies:** 02,05,06,09,13  
**Description:** Full and abbreviated packuments as needed, scoped package names, tarball URLs rewritten into Hoard, lockfile integrity, npm client headers and trusted authenticated metadata partitioning.

**Definition of done / acceptance focus:** npm install/ci succeed using .npmrc; tarball URLs never bypass Hoard; scoped packages work; lockfile integrity remains valid; untrusted auth headers not leaked.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify an npm-compatible pull-through registry consumed by ordinary npm commands. Developers should install scoped/unscoped and transitive dependencies through Hoard, with metadata and tarball links remaining local. Include npm ci, lockfiles, cache freshness, metadata variants, errors and upstream credential privacy.
```

<a id="spec-18"></a>
### SPEC-18: Security boundaries and secrets hardening

**Priority:** P1  
**Dependencies:** 01,02,05,10  
**Description:** SSRF prevention including DNS rebinding and redirects, outbound IP restrictions, path sanitization, secret source abstraction, scrubbed logs, host/header limits, admin protection, trusted proxy contract and policy tests. Security first even on personal installations.

**Definition of done / acceptance focus:** External arbitrary URL fetch blocked; redirects to private/link-local/metadata targets refused; secrets never logged; admin endpoints protected when network exposed; adversarial tests pass.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify security protections for Hoard as a network-capable package proxy, including strictly approved upstream registries, safe redirects and address resolution, isolation of credentials, secure logs, denial of path traversal and prevention of unauthenticated management exposure. Define abuse-case tests and safe defaults for both deployment profiles.
```

<a id="spec-19"></a>
### SPEC-19: Retention, quotas, eviction and garbage collection

**Priority:** P1  
**Dependencies:** 03,04,10,12  
**Description:** Separate logical entry eviction from content blob reclamation; global and per-registry quotas, LRU or configurable policies, low-disk safeguards, dry run, protection for active streams, observability and safe orphan cleanup.

**Definition of done / acceptance focus:** Disk budget enforced eventually; no live blob deleted; GC safe after crash; operator can preview and trigger eviction; metrics show reclaimed space accurately.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify how Hoard protects a developer laptop or team server from unbounded cache growth. Users can see usage, set disk budgets and retention rules, preview eviction candidates, safely evict entries, and reclaim unreferenced blobs without harming active downloads or leaving corrupted metadata.
```

<a id="spec-20"></a>
### SPEC-20: Cache pinning and retention exceptions

**Priority:** P1  
**Dependencies:** 19,12  
**Description:** Pin individual versions/artifacts and optionally package ranges or lockfile manifests, preserve pinned blobs across eviction, show pinned byte cost and provide explicit unpin workflows and policy precedence.

**Definition of done / acceptance focus:** Pinned artifacts survive quota eviction; pin operations are idempotent and auditable; insufficient free space handled clearly; unpin returns normal eviction eligibility.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify cache pinning so developers and CI teams can retain critical package versions even under normal eviction. Cover package/version and artifact selection, visibility of pinned storage, conflicts with quotas, unpinning, policy precedence, and corrupted or missing pinned content.
```

<a id="spec-21"></a>
### SPEC-21: Offline mode and stale-if-error behavior

**Priority:** P1  
**Dependencies:** 05,13,19  
**Description:** Explicit offline control, behavior per ecosystem for already stored immutable content and stale metadata, clear cache-miss errors, last-success timestamps, temporary upstream outages, readable UI state and no silent invalid-index promises.

**Definition of done / acceptance focus:** Offline cached packages served when safe; absent packages produce clear failure; stale metadata clearly marked; toggling reconnect behaves predictably; tests for registry outages.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify dependable offline and upstream-outage behavior for developers traveling or teams experiencing registry outages. Cached immutable artifacts should remain usable, stale metadata should follow explicit policy with visible warnings, and unavailable uncached versions must fail clearly. Cover manual offline toggle, reconnect and per-ecosystem nuances.
```

<a id="spec-22"></a>
### SPEC-22: Lockfile import and cache prewarming

**Priority:** P1  
**Dependencies:** 07,15,16,17,19,20  
**Description:** Upload or point to lockfiles/manifests for supported ecosystems; parse exact resolutions without executing scripts, preview download scope and storage estimate, queue bounded warmup, progress/cancellation and integrity verification. Avoid treating manifests as trusted URLs.

**Definition of done / acceptance focus:** Lockfile warms reproducible dependency closure for supported files; no install scripts executed; unsafe sources rejected; progress and partial failures visible.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify a lockfile-driven cache warming experience: users supply standard dependency lockfiles and can preview, queue, follow, cancel and retry prefetches before CI or offline work. Support only verified ecosystems, preserve source and integrity data, avoid executing package scripts, and clearly report unsupported files and partial results.
```

<a id="spec-23"></a>
### SPEC-23: Detailed metrics, bandwidth savings and diagnostics

**Priority:** P1  
**Dependencies:** 05,10,12  
**Description:** OpenTelemetry spans, Prometheus endpoint, aggregate dashboards for hit rate, bytes avoided, remote time avoided estimates, top ecosystem traffic, upstream latencies/errors, cardinality limits, tracing correlation and export. Metrics claims must distinguish measured vs estimated.

**Definition of done / acceptance focus:** Operators can compare cold/warm traffic and attributable saved bytes; dashboards reconcile to instrumentation; labels bounded; sensitive package/credential data not leaked.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify high-quality cache observability so users can quantify bandwidth saved, hit rates, latency and reliability by ecosystem and registry and troubleshoot individual failed requests. Include time ranges, accurate calculation definitions, privacy controls, OpenTelemetry integration and low-cardinality metrics appropriate for a busy CI service.
```

<a id="spec-24"></a>
### SPEC-24: Team OIDC login, scoped access tokens and permissions

**Priority:** P1  
**Dependencies:** 10,11,18  
**Description:** OIDC browser login for management, device-free normal browser flow, token auth for package clients, role-based least privilege for operator/viewer/admin, local mode controls, bootstrap and break-glass procedure, token revocation and safe auth caching.

**Definition of done / acceptance focus:** Admin pages require login on team mode; read-only operators cannot mutate; tokens scoped to registry access and revocable; audit trails omit token plaintext.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify safe shared-team operation where administrators sign in with an OIDC identity provider and package clients authenticate using scoped access tokens when required. Include role permissions, setup/bootstrap, token issuance and revocation, anonymous-read policies, lost-access recovery, and clear distinction between console and registry permissions.
```

<a id="spec-25"></a>
### SPEC-25: Audit trail and sensitive operations

**Priority:** P1  
**Dependencies:** 10,18,24  
**Description:** Audit config changes, credential references, role/token changes, pin/eviction, offline mode, maintenance actions and job triggers; immutability/tamper resistance appropriate to a single-instance OSS server, export, retention and redaction.

**Definition of done / acceptance focus:** Privileged changes attributable with time and safe metadata; audit export filters; no secret-bearing fields recorded; users can see change history.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify an operator audit history for security-relevant changes in Hoard, including registry configuration, access controls, cache eviction and pinning, offline mode and administrative jobs. Users must understand who changed what and when without exposing tokens, credentials or private URLs. Include retention and export needs.
```

<a id="spec-26"></a>
### SPEC-26: PostgreSQL team persistence

**Priority:** P2  
**Dependencies:** 03,14  
**Description:** Swappable EF provider for PostgreSQL, migrations, compatible semantics and pagination, connection pooling, backfill/move process from SQLite with consistency and downtime requirements, team backup/restore docs. No HA implied.

**Definition of done / acceptance focus:** Parity integration suite passes with PG; upgrade path documented; schema migrates safely; SQLite stays first-class.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify optional PostgreSQL persistence for team deployments while retaining a fully supported SQLite personal installation. Cover configuration, schema parity, migration/backup, failure recovery, integrity verification, and operator visibility; do not require PostgreSQL for ordinary installations.
```

<a id="spec-27"></a>
### SPEC-27: S3-compatible and Azure Blob storage providers

**Priority:** P2  
**Dependencies:** 04,19,26  
**Description:** Plug-in provider contracts for staged writes, commit/availability semantics, digest integrity, downloads, deletion, permissions, bucket/container setup and garbage collection. Adapt to non-atomic rename and eventual consistency where applicable.

**Definition of done / acceptance focus:** Providers pass common blob-contract tests; no incomplete blob becomes hit; identity/secret rules documented; healthy rollback from errors.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify optional object-storage-backed artifact persistence for shared Hoard servers, initially S3-compatible stores and Azure Blob. Ensure integrity, deduplication, streaming and deletion remain equivalent to local disk despite different storage semantics. Cover credential setup, misconfiguration, outages and safe cleanup.
```

<a id="spec-28"></a>
### SPEC-28: Python PyPI Simple API adapter

**Priority:** P2  
**Dependencies:** 02,05,06,09,13  
**Description:** PEP 503/691-compatible simple index HTML and JSON variants as supported, normalized names, wheel/sdist links and hashes, pip setup, dynamic file URL rewriting and edge cases of canonical metadata.

**Definition of done / acceptance focus:** pip install works for wheels/sdists and transitive dependencies in isolated environments; links remain local; hash checking passes; name normalization correct.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify a PyPI-compatible package cache consumed by unmodified pip. Users should browse and download versions using the Simple Repository API, with correctly normalized project names, artifact links and integrity hashes. Include HTML/JSON negotiation, wheels, sdists, transitive dependencies and authentication edge cases.
```

<a id="spec-29"></a>
### SPEC-29: Cargo sparse registry adapter

**Priority:** P2  
**Dependencies:** 02,05,06,09,13  
**Description:** Sparse index version entries, config.json rewriting to local crate endpoint, crate content and checksum expectations, Cargo config examples, git-index compatibility explicitly out of scope unless implemented.

**Definition of done / acceptance focus:** cargo build/fetch passes with sparse source and correct download rewriting; crate digest verification works; upstream never bypassed; documented auth limits.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify a Cargo sparse-registry pull-through cache that works with standard Rust tooling. Developers configure Cargo once and retrieve index entries and crate archives through Hoard, with no inadvertent upstream bypass. Include config.json endpoint mapping, checksum checks, offline runs and unsupported registry modes.
```

<a id="spec-30"></a>
### SPEC-30: Supply-chain controls: quarantine and package cooldown

**Priority:** P2  
**Dependencies:** 05,18,20,22  
**Description:** Configurable newly published version cooldown, upstream publish-time trust limitations, warning/quarantine for failed hashes, rule precedence, safe admin override with audit and no opaque blocking. Keep separate from CVE intelligence.

**Definition of done / acceptance focus:** Too-new versions held according to rules, cached older versions unaffected, compromised content never served, overrides explicit and audited, decisions explainable.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify supply-chain safety controls that prevent immediate use of newly published package versions when a team enables a cooldown policy, and quarantine artifacts that fail integrity verification. Define clear policy scope, trusted time data limitations, informative client errors, review/override workflows and audit records.
```

<a id="spec-31"></a>
### SPEC-31: Vulnerability intelligence and package risk visibility

**Priority:** P2  
**Dependencies:** 03,12,18,30  
**Description:** Optional advisory enrichment via trusted data feeds, package ecosystem/version mapping, asynchronous ingestion, advisory freshness/attribution, false-positive handling and policy separation from proxy data path. No claims of full security assurance.

**Definition of done / acceptance focus:** Cached package detail shows sourced advisories when configured; stale/unavailable advisories disclosed; base cache works without enrichment; no silent false assurance.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify optional vulnerability visibility for cached packages with advisory sources, package/version matching, update status, severity and links to original reports. Operators should be able to understand potential exposure without blocking ordinary restores by default. Include stale feeds, missing data, false positives and privacy boundaries.
```

<a id="spec-32"></a>
### SPEC-32: Self-service CI integrations and preflight verification

**Priority:** P2  
**Dependencies:** 13,21,22,23,24  
**Description:** Actionable samples for GitHub Actions/Azure Pipelines and common CI, diagnostics of routing, endpoint health, lockfile warmup, least-privilege tokens, safe caching patterns and measurable restore improvements. No proprietary runner coupling.

**Definition of done / acceptance focus:** Documented workflow succeeds across at least two CI systems; tests show no secret exposure; routing check demonstrates package requests actually hit cache.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify an easy CI onboarding experience where teams can configure existing runners to consume Hoard as their package registry proxy, verify traffic routes through the cache, securely handle tokens and optionally warm dependencies. Include examples for common CI systems, diagnostics and meaningful before/after measurements.
```

<a id="spec-33"></a>
### SPEC-33: Recovery, integrity audit and disaster restore

**Priority:** P2  
**Dependencies:** 03,04,14,19,26,27  
**Description:** Admin-integrity scan for missing/corrupt blobs and dangling references, repair/eviction strategies, database backup with blob consistency, restore manifest, crash injection, operator runbook and safe-dry-run validation.

**Definition of done / acceptance focus:** Recovery tests survive interrupted fetches and DB restart; corrupt blobs rejected and surfaced; backup/restore yields consistent cache; no silent loss of pinned content.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify operational recovery tools for Hoard administrators to verify stored artifacts, detect corrupted or orphaned data, recover after an interrupted write, back up and restore metadata plus blobs and safely repair cache indexes. Include readable reports, dry-run operations and auditable destructive repair.
```

<a id="spec-34"></a>
### SPEC-34: Multi-instance coordination and high availability

**Priority:** P3  
**Dependencies:** 24,26,27  
**Description:** Design distributed single-flight, metadata coordination, shared storage, health-aware routing, migrations and background job ownership. Only after proven single-node demand.

**Definition of done / acceptance focus:** Two-node tests prove one effective commit per cache key, no corruption during failover, and graceful degraded behavior when coordination lost.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify how organizations could run multiple Hoard server instances against shared persistence without duplicate conflicting writes or cache corruption. Include node failure, rolling upgrades, distributed locks, background job ownership, observable failover and operational boundaries; preserve single-instance simplicity.
```

<a id="spec-35"></a>
### SPEC-35: Open-source contributor experience and release governance

**Priority:** P1  
**Dependencies:** 01,09,14  
**Description:** MIT license, notices/SBOM/dependency license review, CONTRIBUTING, architecture docs, ADRs, issue templates, security policy, automated lint/tests, signed provenance where feasible, compatibility matrix and semantic release notes.

**Definition of done / acceptance focus:** Fresh contributor can build/test; releases include checksums/license/compatibility; security reporting path clear; unsupported features disclosed.

**Paste into Spec Kit `specify`:**

```text
/speckit.specify Specify a contributor-friendly MIT-licensed open-source project experience for Hoard: local build/test instructions, clear modules and adapter contracts, review expectations, issue and security reporting, versioned release notes, compatibility statements and repeatable release checks. Include a measurable new-contributor happy path.
```

## Cross-cutting acceptance matrix

| Quality area | Required evidence |
|---|---|
| Native clients | Official package-manager cold/warm install/restore and transitive dependency tests for each advertised adapter |
| Cache correctness | Mutable/immutable rules, conditional validation, bounded negative caching, HTTP statuses/headers, origin identity isolation |
| Reliability | Concurrent same-key requests, upstream timeouts, retries, client disconnects, crash restart, disk full and incomplete fetches |
| Security | Restricted upstreams including redirect/DNS resolution, safe logging, management auth when exposed, no credential cross-contamination |
| Data integrity | SHA-256 validation, checksum support where available, no partial hits, no dangling blob references, corruption recognition |
| UX | Dark/light, mobile/tablet, keyboard, screen-reader labels, empty/loading/errors, copied client setup that works |
| Operations | Startup diagnostics, metrics, backups, schema migration, pruning, documented restore procedures |
| Open source | MIT license, contributor docs, documented supported features and limitations, repeatable CI builds/releases |
| Composition | No forbidden dependency directions, no provider collisions, disabled routes absent, secure invalid-configuration failures |
| Provider conformance | Shared category tests, metadata/blob transaction-integrity correctness, version compatibility, custom host smoke test |
| Feature cohesion | Management/protocol operations built as vertical slices; shared cache invariants remain centrally implemented |

## Deliberate exclusions (unless separately approved)

Package publishing and private hosted registry workflows; enterprise SCIM and full artifact-governance suite; air-gap replication/synchronization; unreviewed arbitrary plugin execution or runtime plugin hot-loading; transparent capture of third-party traffic without package-manager config; claiming security certification; multi-instance HA in the first release.

## VSA guidance for every generated SpecKit feature

- Prefer `Features/<Domain>/<UseCase>/` for ASP.NET Core management operations and `Hoard.Protocols.<Name>/Features/<UseCase>/` for native registry endpoints. Colocate validation, request/response contracts, endpoint mapping and focused tests where useful; avoid mandatory MediatR and horizontal `Controllers/Services/Repositories` layering.
- Never implement independent cache freshness, secure upstream fetching, hash verification, atomic blob publication, single-flight coordination, GC reference safety or authorization primitives in every slice. Those are **shared services** in Hoard Core/Hosting.
- Providers own external technology integration and private models/migrations. No feature slice directly depends on `DbContext`, file-path internals or a concrete identity provider. No runtime dynamic assembly discovery from arbitrary directories for MVP.
- When creating a feature spec, explicitly include both the specific user outcome and any applicable module/provider acceptance tests. Use ADR-0001 and `ARCHITECTURE.md` to guide the implementation plan, not to force internal design details into end-user acceptance criteria.

## Decision register to settle before dependent specs

1. Cache quotas and eviction defaults; immutable artifact retention horizon.
2. Exact upstream base URL and registry routing shape (keep externally exposed paths stable).
3. Offline metadata freshness policy per protocol and negative response TTL.
4. Team authorization timing: require auth before network-exposed beta; decide anonymous package reads per registry.
5. Source-of-truth configuration: file/env vs mutable UI settings and precedence; secret reference store.
6. Next.js static export constraints and routing/base path assumptions, especially reverse proxies.
7. Public repo and executable naming/namespace: **Hoard** chosen, clearance remains separate.
8. Minimum .NET client version, OS support matrix, published package-manager test versions, supported NuGet v3 resources.

## References

- Hoard Architecture (`ARCHITECTURE.md`)
- ADR 0001 (`docs/adr/0001-modular-provider-architecture.md`)

- Hoard Product Charter (`PRODUCT_CHARTER.md`)
- Hoard Product Vision (`PRODUCT_VISION.md`)
- Hoard Product Specification (`PRODUCT_SPEC.md`)
- [GitHub Spec Kit quickstart](https://github.com/github/spec-kit/blob/main/docs/quickstart.md)
- [GitHub Spec Kit reference](https://github.com/github/spec-kit/blob/main/docs/reference/core.md)
