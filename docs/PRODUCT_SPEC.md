# Hoard — Product Specification

**Status:** Draft v0.1 · **Date:** 2026-10-19 · **Product name:** Hoard · **License:** MIT

## 1. Overview
A self-hosted, pull-through package-cache service that presents ecosystem-native registry endpoints. The initial release supports NuGet v3 and is designed to add Go, Maven, npm, Python/PyPI, and Rust/Cargo via modular protocol adapters. One ASP.NET Core executable hosts registry APIs and management APIs and can serve a statically exported Next.js management console.

## 2. Architecture and runtime
- **Backend:** .NET 10, ASP.NET Core Minimal APIs, dependency injection, typed `HttpClient` clients, background hosted services, OpenTelemetry.
- **Frontend:** Next.js 16.4 as of 2026-10-19 (upgrade to latest supported stable at implementation), App Router, TypeScript, Tailwind CSS 4, shadcn/ui, Radix/Base UI choice finalized during design setup, Lucide, TanStack Table, Recharts, TanStack Query for client data.
- **Bundling:** Next.js static export and .NET static-file hosting in the default distribution. No SSR, server actions, Next.js API routes, or other runtime-only features in bundled console; management API lives in .NET. Optional separate Next.js hosting may be introduced later.
- **Persistence:** SQLite initially; PostgreSQL provider planned. EF Core for application metadata and migrations.
- **Blob store:** Filesystem initially with SHA-256 content addressing; S3-compatible and Azure Blob later.
- **Structure:** Modular monolith with registry adapters, cache orchestration, persistence/storage adapters, management APIs, and bundled UI.
- **Background services:** Cleanup, stats aggregation, expired-entry maintenance, orphan blob reclamation.

## 3. Core entities
| Entity | Example fields / responsibility |
|---|---|
| `Registry` | Id, ecosystem, upstream base URL, enabled, auth reference, policy |
| `Package` | Id, ecosystem, canonical name, namespace, optional display fields |
| `Artifact` | Digest SHA-256, length, content type, storage locator, committed timestamp |
| `CacheEntry` | Registry Id, normalized request key, method, status, headers, artifact digest, ETag, LastModified, freshness timestamps |
| `FetchLease` | Resource key, owner, creation/expiry (future distributed coordination) |
| `AccessAggregate` | Interval, registry, hits, misses, bytes served, bytes fetched, latency metrics |
| `Policy` | Scope, metadata TTL, retention, max size, immutable behavior, stale-if-error |
| `CredentialReference` | Identifier, secret-provider key; never raw secret in plaintext metadata |

### Identity and invariants
- Request keys include registry identity, protocol-specific canonical path/query, and any response-varying dimensions. Do not cache arbitrary authenticated variants together.
- Artifact bytes keyed by cryptographic digest, not solely package/version.
- A cache entry never references an uncommitted blob.
- Upstream metadata and package artifacts use different caching policies.
- Preserve protocol-required methods, status codes, headers, URL forms, and response content types.

## 4. Cache request lifecycle
1. Route incoming request to an ecosystem adapter.
2. Adapter validates request, produces canonical cache key, determines protocol-specific response handling.
3. Engine checks cache entry and freshness; validates backing artifact availability.
4. Serve fresh hit; for stale metadata, perform conditional upstream revalidation when appropriate.
5. On miss, use in-process per-key single-flight coordination; waiting requests re-check committed entry.
6. Fetch configured upstream using a restricted HTTP client with SSRF and redirect protections; stream response with bounded memory.
7. Stage payload in temporary storage, verify size/hash and optional ecosystem checksum, then atomically commit blob.
8. Atomically publish cache metadata; only then can other requests treat it as a valid hit.
9. Respond with protocol-correct transformed metadata or package content; collect asynchronous access metrics.
10. On error, follow explicit negative cache, retry, stale-if-error and timeout policy; never turn corrupt or partial bytes into hits.

### HTTP behavior
- Support conditional requests (If-None-Match / If-Modified-Since) where applicable.
- Decide 404/410 negative-cache TTL per ecosystem; don't cache 401/403 as shared negative entries by default.
- Correct HEAD and Range handling must be specified and tested before claiming support.
- Stream large artifacts without loading fully into RAM.
- Handle upstream rate limits, redirects and retries safely, with bounded concurrency and exponential backoff for transient failures.
- Define cache-control behavior for transformed registry metadata so clients don't retain stale endpoint URLs.

## 5. Registry adapters: rollout and contracts
### Priority
1. **NuGet v3** — first implementation and acceptance gate.
2. **Go GOPROXY** — second.
3. **Maven** — third.
4. **npm** — fourth.
5. **PyPI** — subsequent.
6. **Cargo** — subsequent.

### Adapter responsibilities
- Register URL routes under stable namespace, e.g. `/r/nuget/{registry}/...`.
- Parse and validate package coordinate/path according to registry's case/encoding rules.
- Select safe upstream endpoint and map request to cache key.
- Transform returned discovery and metadata URLs to local cache endpoints.
- Declare immutable-blob vs mutable-metadata cache behavior.
- Provide setup instructions and an end-to-end compatibility suite.

### NuGet v3 requirements (P0)
- Serve local NuGet v3 service-index JSON (`index.json`) containing correct local resource URLs for supported endpoints.
- Support PackageBaseAddress/flat-container version indexes and `.nupkg` downloads for standard restore.
- Handle registration metadata required by tested clients; consider package metadata/search endpoint requirements explicitly, not silently assume full protocol support.
- Correct NuGet package ID/version normalization, semantic-version edge cases, URL encoding and authentication propagation.
- Ensure every advertised required resource URL routes through cache rather than bypassing it.
- Configure standard clients via `NuGet.Config` or `dotnet nuget add source`.
- Test `dotnet restore`, `dotnet add package`, multi-project transitive restores, fresh cache, warm cache and upstream failure scenarios.
- Document unsupported NuGet endpoints until implemented.

### Go requirements (P1)
- Implement GOPROXY endpoints: `@v/list`, `@v/{version}.info`, `@v/{version}.mod`, `@v/{version}.zip` and module escaping rules.
- Document `GOPROXY` and `GOSUMDB`/private module considerations; never pretend caching substitutes for checksum verification.

### Maven requirements (P1)
- Maven repository-style paths for POM, JAR and related artifacts, metadata (`maven-metadata.xml`), snapshot semantics, checksums and plugin dependencies.
- Document `settings.xml` mirrors; do not treat snapshots as immutable release assets.

### npm requirements (P2)
- Registry metadata documents, scoped packages, tarballs, URL rewriting and request headers; preserve auth boundaries.
- Support common npm clients using `.npmrc`; test lockfile and integrity semantics.

### PyPI and Cargo (P3)
- PyPI: Simple Repository API HTML/JSON negotiation, normalized project names, file links and wheel/sdist handling.
- Cargo: sparse index, index `config.json` download URL rewriting, crate content and authentication limitations.

## 6. Management API (initial contract proposal)
- `GET /api/v1/health` — health/readiness summary (separate unauthenticated liveness endpoint as needed).
- `GET /api/v1/overview` — statistics and status.
- `GET /api/v1/packages?ecosystem=&q=&page=` — searchable catalog.
- `GET /api/v1/packages/{id}` — package details/artifacts.
- `GET /api/v1/requests?cursor=` — recent requests/latency/errors.
- `GET /api/v1/registries` — configured registries.
- `POST /api/v1/registries` — create registry (restricted).
- `PATCH /api/v1/registries/{id}` — update registry (restricted).
- `POST /api/v1/cache/evictions` — selected artifact/entry eviction (restricted, auditable).
- `GET /api/v1/setup/{ecosystem}` — native configuration guidance.
- `GET /metrics` — Prometheus metrics when enabled, restricted on shared networks.

Use OpenAPI and generated TypeScript client types. API pagination should be cursor-based on high-volume activity endpoints. Require confirmation for destructive UI operations.

## 7. UX / design system requirements
### Visual language
- Beautiful, professional infrastructure console; compact information density, crisp typography, neutral tones with restrained accent, subtle depth, dark mode and light mode.
- shadcn/ui components styled with application tokens, not unmodified stock appearance.
- WCAG 2.2 AA target, keyboard-friendly command/search interfaces, reduced-motion support, screen-reader labels and robust color contrast.

### Screens
1. **Overview:** Hits/misses, bandwidth saved, registry health, storage usage, recent request stream.
2. **Packages:** Search, filter by ecosystem/registry, version/artifact details, checksums, last fetched/used.
3. **Activity:** Timeline, latency, hit/miss, status, filters, request diagnostics.
4. **Registries:** Add/edit upstream registry, test reachability, priority and status.
5. **Storage:** Quota, usage distribution, eviction/pinning (pinning later), garbage-collection status.
6. **Settings:** Deployment/security settings, diagnostics, client setup guides.

### Libraries
- Next.js App Router / TypeScript; Tailwind CSS 4; shadcn/ui; Lucide icons; TanStack Table for advanced grids; Recharts for time series; Sonner for notifications; React Hook Form + Zod for validation; `next-themes` for appearance.
- Default bundle uses static export. Keep data loaded client-side from the ASP.NET Core management API. Make base URLs work behind reverse proxies.

## 8. Security and isolation
- Bind only to loopback by default; explicit opt-in to `0.0.0.0`.
- UI management and registry read/write permissions are separate surfaces.
- Team management endpoints must be protected by authentication and HTTPS, either natively or by a documented trusted reverse proxy.
- Team OIDC login and scoped package tokens planned; anonymous registry reads are only allowed by explicit deployment policy.
- Strict allowlist of upstream hosts; validate DNS resolution and redirects against private/link-local/metadata addresses. Avoid open-proxy behavior.
- Enforce path and archive handling constraints, request limits, timeouts and upload/download byte caps where appropriate.
- Never log authorization headers, credential-bearing URLs or secret values.
- Secrets obtained via environment variables, mounted files or external secret providers; do not put cleartext secrets in SQLite.
- Dependency vulnerability scanning and licensing checks in CI; responsible-disclosure policy before public beta.

## 9. Reliability and operations
- Cache hit operations require no upstream network call for fresh immutable content.
- Single-process deduplication on cold misses; multi-node locking deferred.
- Store temp downloads on the same filesystem or use copy/rename semantics that guarantee final atomic visibility.
- Recover on restart by removing expired staging files and reconciling orphan records/blobs.
- Retain access counters asynchronously; batch writes to avoid DB contention.
- Expose OpenTelemetry spans/metrics including request duration, cache result, upstream fetch duration, bytes served/fetched, corruption and eviction counts. Avoid package ID labels on high-cardinality metrics.
- DB backups, data restore, migration procedures, and artifact verification command documented.

## 10. Configuration sketch (illustrative, not final schema)
```yaml
server:
  listen: 127.0.0.1:8484
  publicBaseUrl: http://localhost:8484
storage:
  type: filesystem
  path: ./data/blobs
metadata:
  provider: sqlite
  connection: Data Source=./data/cache.db
registries:
  - id: nuget-org
    ecosystem: nuget
    upstream: https://api.nuget.org/v3/index.json
policies:
  artifactRetention: until-evicted
  metadataTtl: 15m
  maxDiskBytes: 53687091200
```
This is a target UX for configuration, not a promise that a parser or route shape already exists.

## 11. Repository layout (proposal)
```text
/apps/web                  # Next.js console
/src/Cache.Host            # ASP.NET Core host
/src/Cache.Core            # cache orchestration and policies
/src/Cache.Abstractions    # contracts
/src/Cache.Persistence     # EF Core + SQLite/PostgreSQL
/src/Cache.Storage.FileSystem
/src/Cache.Storage.S3      # future
/src/Cache.Registry.NuGet
/src/Cache.Registry.Go
/src/Cache.Registry.Maven
/src/Cache.Registry.Npm
/src/Cache.Registry.PyPI   # future
/src/Cache.Registry.Cargo  # future
/tests/unit
/tests/integration
/tests/protocol
/deploy/docker
/docs/adr
```

## 12. Acceptance criteria — v0.1 NuGet slice
- From a clean environment, install/start one container with persistent volume and no external DB.
- `/` serves the polished management console; health endpoint reflects initialization and disk/database readiness.
- NuGet v3 source configuration points exclusively to local proxy discovery/resource endpoints.
- Fresh `dotnet restore` downloads packages successfully and records cache misses and artifact metadata.
- Second restore after clearing only the *client-side* NuGet caches completes with server-side hits and no repeat upstream artifact fetches.
- 10 simultaneous identical fresh package requests issue one upstream artifact download per server instance.
- Interrupted upstream transfer does not create a valid cache entry.
- Verify sample `.nupkg` digest and provenance; manually evict then refetch it.
- UI presents real metrics, search/detail view, status and errors with accessible loading states.
- Tests run in CI on Linux; release image has deterministic tag and documented upgrade/backup steps.

## 13. Release plan and priorities
| Stage | Focus | Exit gate |
|---|---|---|
| M0 | Core infrastructure | storage, metadata, test harness, one deployable process |
| M1 | **NuGet first** | warm/cold dotnet restore; integrity/redirect/concurrency tests |
| M2 | Go | public module downloads; config generation; integration suite |
| M3 | Maven | release artifacts, metadata and snapshot behavior validated |
| M4 | npm + dashboard finish | npm metadata rewriting; polished package/activity UX |
| Beta | Security + docs | documented single-node team deployment and limits |
| Later | PyPI + Cargo + advanced backends | protocol tests; migration and storage acceptance |

## 14. Open questions
1. Hoard repository organization, domain availability, and trademark clearance (name chosen; clearance pending).
2. Whether v0.1 should require any server-side auth when bound to non-loopback.
3. NuGet API breadth: restore-only first or search/metadata endpoints concurrently.
4. Cache freshness defaults by endpoint and ecosystem.
5. Artifact size quota and eviction heuristics; pinned artifacts policy.
6. Support for multiple upstreams/fallback per ecosystem and private feeds.
7. Exact team profile release gate: auth built in, or tightly documented trusted proxy.
8. Optional standalone Next.js runtime versus static export only.
9. Project minimum OS/architecture targets and packaging matrix.

## 15. References
- Next.js release news: https://nextjs.org/blog
- shadcn/ui official Next.js setup: https://ui.shadcn.com/docs/installation/next
- NuGet v3 protocol: https://learn.microsoft.com/en-us/nuget/api/overview
- Go module proxy protocol: https://go.dev/ref/mod#goproxy-protocol
- PyPI Simple API: https://packaging.python.org/en/latest/specifications/simple-repository-api/
- Cargo registries: https://doc.rust-lang.org/cargo/reference/registries.html

---
These documents are planning specifications, not claims of completed implementation. Routes and default policy values remain subject to ADRs and protocol tests. The product name is Hoard; legal and namespace clearance remains pending.
