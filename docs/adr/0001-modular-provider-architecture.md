# ADR-0001: Composable modular monolith with vertical feature slices

- **Status:** Accepted as v0.2 design baseline (implementation pending)
- **Date:** 2026-10-20
- **Decision owners:** Hoard maintainers
- **Related:** `PRODUCT_CHARTER.md`, `PRODUCT_VISION.md`, `PRODUCT_SPEC.md`, `ARCHITECTURE.md`, `HOARD_SPECKIT_MASTER_BACKLOG.md`

## Context

Hoard must serve both tiny personal installations and centralized team deployments while supporting multiple package protocols, relational databases, blob stores, and identity schemes. The v0.1 design used an ASP.NET Core modular monolith and adapters but did not make independent package composition, module lifecycle and compatibility a first-class contract. We also want business features that can be implemented, tested and understood independently, without duplicating universal artifact/cache correctness.

## Decision

1. Use .NET 10 ASP.NET Core modular monolith with **NuGet-distributed, versioned providers**, composed at build time and explicitly activated during startup.
2. Establish stable abstractions independent of EF Core and other provider SDKs; `Hoard.Core` depends only on abstractions, never concrete SQLite/NuGet/Blob/Entra implementations. Keep EF Core private to relational persistence packages.
3. Use **Vertical Slice Architecture** for management API features and protocol-specific endpoint/use-case workflows, colocating endpoint, request/response, validation, orchestration and related tests when appropriate.
4. Keep cross-slice **shared core services** for cache identities/auth separation, freshness policies, SSRF-safe upstream fetch, integrity hashing, staged atomic publication, streaming and backpressure, single-flight, retention/GC, shared audit/telemetry and provider lifecycle/authorization rules. VSA is not grounds for duplicating these invariants.
5. Curated default package/image includes baseline providers and enables them through configuration; custom host project explicitly references additional packages and is republished. Startup rejects missing/incompatible providers and dependency cycles; disabled modules expose no endpoints/workers.
6. Use ASP.NET Core built-in DI and Minimal APIs; neither MediatR/CQRS nor dynamic assembly loading is required. Community plugins are trusted in-process code, not sandboxed. Distinguish package protocol features from persistence/storage singleton selections and multi-scheme identity.
7. Define module metadata/capabilities and a sanitized management API so Next.js can reflect activated support. Enforce provider conformance and integration tests.

## Rationale

- Preserves one-process personal UX while permitting infrastructure choice for teams.
- Establishes clear extension seams before building multiple protocol and DB implementations.
- Allows feature-local development without a bloated horizontal Controller/Service/Repository pattern.
- Centralizes correctness and security invariants so every protocol behaves consistently.
- Avoids operational and security complexity of arbitrary runtime plugin installation before user demand warrants it.

## Consequences

**Positive:** Independent NuGet module releases; explicit dependency direction; consistent provider contract testing; clean contributor onboarding; curated and custom distributions; API capability discovery; maintainable vertical features.

**Costs:** Contract/version governance, startup validation and module registration scaffolding; more package/build/release test permutations; upfront focus on provider-neutral abstractions; strict tests to keep shared core and slices clean.

**Trade-offs:** Config changes only activate providers already included in an image; adding a new NuGet package requires rebuilding/redeploying a custom host. No fully sandboxed plugin mechanism. Relational/NoSQL interchangeability is not promised merely by sharing an interface.

## Alternatives considered

1. **Single monolith with hardcoded adapters:** simpler initially but growing coupling and harder third-party extensions.
2. **Runtime DLL drop-in loader / marketplace:** more dynamic but introduces code-trust, assembly loading, version conflicts and operational complexity.
3. **Microservices per package ecosystem/provider:** isolation but significant networking/deployment overhead, especially for local users.
4. **Horizontal n-tier architecture everywhere:** easy scaffolding but feature changes span multiple folders; rigid repositories could leak provider-specific persistence details.
5. **Pure VSA for all caching logic:** duplicates integrity and coordination across endpoints, increasing correctness/security risk.
6. **Python entry-point / Pluggy runtime:** strong plugin discovery but would replace chosen .NET runtime/stack; useful reference for future developer ergonomics, not a current migration plan.

## Validation criteria

- Default NuGet/SQLite/filesystem combination runs as a single service with zero external dependencies and safe loopback defaults.
- A custom host compiles with separately packaged provider implementations; forbidden compile-time references fail architecture tests.
- Invalid/missing/incompatible provider configuration stops startup with actionable diagnostics.
- Disabled protocol routes and optional workers do not activate.
- Common SQLite and filesystem provider conformance and NuGet native-client tests pass; second protocol and PostgreSQL later validate interchangeability.
- A registry-management slice and NuGet route slice are independently testable while both rely on the same verified cache core.

## Revisit when

- Genuine demand arises for live installation/uninstall of modules or isolated third-party code.
- A second database family reveals material mismatch in the abstraction.
- Multi-node deployments require separate distributed coordination/storage lifecycle services.
- In-process protocol plug-ins prove insufficient for performance/isolation needs.
