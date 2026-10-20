# Hoard — Architecture

**Version:** 0.2 (proposed)  
**Date:** 2026-10-20  
**Status:** Architectural baseline, subject to RFC/ADR review  
**Product:** Hoard · MIT

## 1. Executive decision

Hoard is a .NET 10 / ASP.NET Core **composable modular monolith**. Modules are distributed as NuGet packages and are assembled into a deployment at build time. Built-in and bundled providers are selected, validated and activated **at startup**, with explicit restart for changes. Normal management and registry HTTP workflows use **Vertical Slice Architecture (VSA)**. Cross-feature caching integrity, atomic blob publication, request coordination, authentication isolation, bounded streaming and cache policy semantics are centrally implemented shared services, not duplicated in each vertical slice.

The first official distribution is NuGet v3 + SQLite metadata + filesystem artifacts, with a statically exported Next.js management UI served by ASP.NET Core. PostgreSQL, object stores, other package protocols and identity systems are independent provider implementations. The first release is single-process/single-node; HA and dynamic plugins are deferred.

## 2. Architecture shape

```text
                   Next.js static management UI
                               |
                  ASP.NET Core Hoard.Host
             module composition + HTTP pipeline
                   /                   \
     Hoard.Application           Hoard.Protocols.*
      management slices          protocol slices
                \                   /
                 Hoard.Core (shared engine)
                 |                 |
          Hoard.Abstractions (contracts)
                /       |          \
       Persistence.*  Storage.*   Identity.*
          SQLite       Files       Local
          Postgres     S3/Blob     OIDC/Entra
```

The diagram expresses runtime interactions; compile-time dependency edges must follow the next section rather than imply `Hoard.Core` depends on the providers.

## 3. Assemblies and allowed dependencies

| Project/package | Owns | May reference |
|---|---|---|
| `Hoard.Abstractions` | Public contracts, stable IDs, result/option types, capability definitions | BCL and deliberately minimal dependencies |
| `Hoard.Core` | Cache orchestration, key isolation, revalidation, hash/integrity, single-flight, GC primitives | Abstractions, common framework libraries |
| `Hoard.Hosting` | Registration, module descriptors, validation, lifecycle, endpoint integration | Abstractions, Core, ASP.NET Core |
| `Hoard.Application` | Management API vertical slices (queries/commands) | Core, Abstractions, approved Hosting API |
| `Hoard.Protocols.*` | Each package protocol's routing, encoding, wire format, response rewriting, protocol slices | Abstractions, Core, approved Hosting API |
| `Hoard.Persistence.*` | Provider-private schema, migrations, repositories, isolation/transactions | Abstractions, EF Core or provider SDK as needed |
| `Hoard.Storage.*` | Provider-private streaming, staging, commit/read/delete | Abstractions, provider SDK as needed |
| `Hoard.Identity.*` | External schemes, credential/token verification, principal mapping | Abstractions, approved Hosting API |
| `Hoard.Host` | Concrete app, default provider package references, config, UI asset bundling | Hosting, Application, installed providers |
| `apps/web` | User-facing Next.js experience | HTTP management API, OpenAPI/capability schema only |

**Forbidden examples:** `Hoard.Core -> Hoard.Persistence.Sqlite`; `Hoard.Application -> DbContext`; NuGet protocol referencing Azure Blob provider; one feature slice referencing another slice's internal handler. Contract ownership must be kept minimal and stable; architectural tests enforce this.

## 4. Provider categories and cardinality

| Category | Initial cardinality | First implementation | Later implementations |
|---|---|---|---|
| Package protocol | Many simultaneously | NuGet v3 | Go, Maven, npm, PyPI, Cargo |
| Metadata persistence | Exactly one authoritative | SQLite | PostgreSQL, SQL Server, MySQL; NoSQL only after separate proof |
| Artifact storage | Exactly one authoritative | Filesystem | S3-compatible, Azure Blob |
| Authentication | Multiple supported schemes | Loopback/local and optional package tokens | Generic OIDC, Entra configuration convenience |
| Authorization | Central permission model | Core role/permission checks | Claims mapping, more advanced policies |
| Secrets | Potentially multiple resolvers | Environment/file | Key Vault or community integrations |
| Behavior hooks | Narrow, documented extension points only | No general public hook bus needed MVP | Audit/export, notifications, retention hooks after demand |

Authentication does not automatically grant authorization. Browser users, CI credentials and native package clients are distinct entry points with normalized Hoard principals and policy checks.

## 5. Module declaration and lifecycle

Each module exposes a stable ID/category, semantic module version, compatible host/abstractions version range, capability set, required module dependencies, sanitized option schema, optional endpoints, readiness probes and support/provenance information.

1. **Build-time assembly:** Curated Host references approved modules. Custom Host projects reference further provider NuGet packages.
2. **Startup discovery/registration:** Explicit registrations or deterministic scanning of known referenced assemblies; never load arbitrary directory content by default.
3. **Configuration:** Resolve enabled modules; select singleton-provider categories; validate plugin options, secrets presence, duplicates and dependency graph.
4. **Compatibility:** Check host/abstractions versions and required provider capabilities; fail startup on invalid composition. Do not silently fall back to SQLite or anonymous auth.
5. **DI + HTTP composition:** Register services/options, map protocol slices for enabled modules, attach proper auth/policies and observability.
6. **Initialize:** Run migrations or health initialization per operational policy; readiness becomes true only after required modules report ready. Migrations should be explicit or controlled, not an uncontrolled automatic cross-version upgrade.
7. **Serve:** Expose sanitized capability/health inventory; disabled modules do not expose routes, hosted workers, or unexpected external connections.
8. **Shutdown:** Stop traffic and dispose dependencies in order; drain active requests as practical.

**Security:** In-process module code runs with the application process privileges. NuGet packaging gives distribution, **not isolation**. No plugin marketplace/hot install/load in MVP. Custom assemblies must be reviewed, allowlisted and included in the build/deployment artifact.

## 6. Feature boundaries: VSA with deliberate exceptions

### Use VSA here

- Management endpoints: create/update registry, probe upstream, list/filter cached packages, purge/pin artifacts, view stats, inspect installed modules, update allowed policies.
- Each ecosystem-specific HTTP route: NuGet service index, version listing, registration metadata, package stream; npm metadata and tarball routes, etc.
- Each slice may contain `Endpoint.cs`, `Request.cs`, `Response.cs`, `Validator.cs`, `Handler.cs` and tests, or fewer files where cohesive. Use Minimal APIs and dependency injection. No enforced MediatR/CQRS and no layers-first per-feature ceremony.

### Do **not** force these into isolated per-feature copies

| Shared concern | Owner and reason |
|---|---|
| Cache identity/auth variant separation | Core; contamination must not differ by adapter |
| HTTP freshness/revalidation/negative caching | Core policies with protocol-defined inputs |
| Artifact digest, staging, atomic visibility | Core and store contract; invariant across all protocols |
| Large streaming/backpressure and single-flight | Core; request lifecycle and concurrency shared |
| Storage reference counts, safe eviction and GC | Core; physical deletion must not race live readers |
| SSRF-safe upstream client behavior, secret redaction | Central security/Hosting; uniform threat boundary |
| Authorization permissions and audit/telemetry foundation | Shared policy/observability; endpoints declare access requirements |
| Persistence/blob/auth contracts and provider lifecycle | Abstractions/Hosting; one consistent interchange protocol |

**Guiding rule:** Share by invariant and infrastructure boundary, not by arbitrary "service" naming. Slices orchestrate; core protects the platform.

### Illustrative feature module

```text
Hoard.Application/
  Features/
    Registries/
      CreateRegistry/
        Endpoint.cs
        Request.cs
        Validator.cs
        Handler.cs
    Packages/
      PurgePackage/
        Endpoint.cs
        Handler.cs
Hoard.Protocols.NuGet/
  NuGetModule.cs
  Features/
    GetServiceIndex/
    GetPackageVersions/
    DownloadPackage/
```

The NuGet `DownloadPackage` slice translates native paths/protocol semantics into a core cache request and streams its result; it **must not** implement its own content hash/atomic publishing algorithm.

## 7. Illustrative APIs (not yet committed public signatures)

```csharp
public interface IHoardModule
{
    ModuleDescriptor Descriptor { get; }
    void ConfigureServices(IServiceCollection services, IConfiguration configuration);
    void MapEndpoints(IEndpointRouteBuilder endpoints);
}

public interface IArtifactStore
{
    Task<ArtifactReadResult?> OpenReadAsync(ArtifactKey key, CancellationToken ct);
    Task<ArtifactCommitResult> StageAndCommitAsync(
        ArtifactKey key, Stream content, ArtifactExpectations expected, CancellationToken ct);
    Task DeleteAsync(ArtifactKey key, CancellationToken ct);
}
```

Exact signatures need separate design and conformance tests. `IArtifactStore` must not assume object stores support filesystem renames; publish semantics are a **capability** with safe fallback/coordination. Provider contract types might live in category-specific abstractions assemblies later, if the global abstraction package becomes too large.

Custom host sketch:

```csharp
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddHoard()
    .AddNuGet()
    .AddPostgres()
    .AddS3Storage()
    .AddOidcAuthentication();
var app = builder.Build();
app.MapHoard();
app.Run();
```

These extension methods are intended future Hoard APIs, not current packages.

## 8. Configuration and capability UX

**Curated distribution:** Includes a documented package set; install/run once and select built-in provider choices in validated configuration. Selecting a provider that is not installed is an error; no automatic package downloads. Simple default uses SQLite + filesystem + NuGet on loopback. Team listeners require explicit TLS/auth posture.

**Custom distribution:** Reference desired NuGet packages in a `.csproj`, register providers, publish a new binary/image, configure choices and restart. Build composition is explicit/reproducible.

**Management API:** Expose installed/available/active provider lists, descriptive capabilities, versions, health and sanitized config definitions, behind appropriate management access. The Next.js interface only offers actions declared as supported; it must not mistake "installed" for "enabled" or "healthy".

**Configurations:** Define CLI/environment/file precedence; support reference-based secrets; validator catches unknown IDs, incompatible modules, missing required capabilities and wrong cardinality; version configs and document migration. Never log raw credentials.

## 9. Persistence and object-store neutrality

`Hoard.Core` consumes repository and artifact-store contracts and controls cross-store sequencing. Relational providers may use EF Core and independently own their migration history/DDL. No direct DbContext leakage into request slices. Do not presume cross-database joins, portable DDL or relational semantics from a NoSQL option.

Blob payloads belong in storage providers; metadata providers store references. Cache visibility occurs only after validated blob commit. Garbage collection must account for active readers, pinning and shared digests. For HA later, coordinate distributed locks, blob publication and worker ownership in a separate spec; a local store is not transparently shared between replicas.

## 10. Security and threat boundaries

- Default bound to loopback with optional anonymous local UX; require explicit secure network binding and authenticated management in team mode.
- Protocol routes must preserve native client credentials without contaminating cache identities/headers across principals or origins.
- Restrict approved upstream targets; validate redirects, DNS/IP policy and metadata/link-local/private destinations consistently.
- Sanitized provider error reporting; secrets from environment/mounted secret files/future external resolvers. 
- Trust boundary of a plugin is the trust boundary of the host. Plugin signing/provenance and allowlisting help operational review but cannot sandbox malicious in-process code.
- API tokens and CI authentication are distinct from interactive OIDC; authorization stays centrally normalized.

## 11. Testing and verification

1. **Architecture tests:** Forbidden references fail CI; code samples for custom host compile.
2. **Category contract suites:** Same storage, persistence and identity behavior tested against every advertised implementation.
3. **Protocol black-box tests:** Native package managers (beginning with `dotnet restore`) against a real Hoard/upstream test harness, cold/warm/error flows.
4. **Module composition:** Enabled/disabled routes, collision/dependency validation, incompatible versions, readiness failure, no secret leakage.
5. **VSA tests:** Feature-level handler and endpoint acceptance; reused core correctness tested once comprehensively plus integration checks through each protocol.
6. **Chaos:** Interrupted writes, corrupt blobs, storage full, concurrent requests, upstream SSRF attempts, stale metadata, migrations, restart recovery.
7. **Release:** Curated image plus at least one working custom host; SBOM/license/compatibility manifest and docs.

## 12. Rollout sequence

- **Foundation:** F-01–F-07, Host and basic slices; provider contract tests and secure config defaults.
- **First usable product:** SQLite + filesystem + NuGet protocol module, real-client test harness, management API + Next.js static console.
- **Prove interchangeability early:** PostgreSQL and a second independent package protocol, even if later than MVP release gate.
- **Team:** Identity scheme module model (F-08), OIDC/Entra, scoped native client tokens, hardened shared service experience.
- **Expansion:** More protocols/stores, SQL Server/MySQL where demand warrants; separately assess NoSQL.
- **Deferred:** Runtime plugin marketplace/loading, untrusted plugin sandboxing, live provider swap, cross-language RPC plugins and multi-node HA.

## 13. ADRs and unresolved decisions

**Accepted for design planning:** [ADR-0001: Composable modular monolith with vertical feature slices](adr/0001-modular-provider-architecture.md).

**To decide before stable API release:** exact public module registration signatures; `Hoard.Abstractions` split threshold; EF migrations operational policy; capabilities schema version; custom module version ranges; NuGet request adapter contract; explicit source-of-truth for provider settings; default identity/token posture; multi-tenant cache isolation; exact licensing/provenance acceptance requirements.

This document is a decision framework, not generated source code or a guarantee that all future providers are implemented.
