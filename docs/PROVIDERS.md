# Provider author guide

F-01 supplies source-level .NET 10 declarations and registration-only composition
at local acceptance package version `0.1.0`. Nothing is published to nuget.org.
There is no working cache, protocol, persistence, byte store, authentication,
provider activation, or certification. Start with the
[compile-only host](../examples/CustomHost/README.md) and
[validation quickstart](../specs/001-provider-contracts/quickstart.md).

## Public ownership and authoring

`Hoard.Abstractions` owns immutable sealed module records in
`Hoard.Abstractions.Modules` and the `IHoardProvider`, `IProtocolProvider`,
`IMetadataProvider`, `IArtifactProvider`, and `IIdentityProvider` markers in
`Hoard.Abstractions.Providers`. All are BCL-only. Markers grant no operations or
permissions. Core references Abstractions only; Core/Application have no
operational members yet. Hosting alone references DI abstractions.

The [public API contract](../specs/001-provider-contracts/contracts/public-api.md)
and [declaration model](../specs/001-provider-contracts/data-model.md) specify
every field. Expose a static immutable `Declaration` as the
[protocol fixture](../tests/fixtures/providers/Protocol/ProtocolProvider.cs)
does; explicitly populate required properties and use `[]` for empty immutable
collections. IDs follow `[a-z0-9]+([.-][a-z0-9]+)*`. Versions have three SemVer
components. Metadata describes dependencies, capabilities, configuration
requirements, endpoint/health responsibilities, and provenance, not resolved
secrets, route delegates, probes, current health, or selected implementations.
Source/support URLs must be public and contain no credentials or private details.
`Fixture`, `Community`, and `MaintainerSupported` are provenance declarations,
not certification. The five test fixtures advertise no operational capability.

`services.AddHoard().AddModule<TProvider>(declaration)` records an immutable
`HoardModuleRegistration` containing the supplied declaration and type token.
It preserves duplicates, requires no public/default constructor, and neither
constructs a provider nor builds a container. Null arguments throw
`ArgumentNullException`. Invalid IDs, default arrays, category/type disagreement,
version conflicts, and invalid selections are representable for later
validators; registration is not validation, enablement, readiness, or fallback.

## Composition, family selection, and trust

A future curated distribution will configure only already bundled providers.
A custom distribution must reference packages and explicitly register types,
then rebuild, redeploy, and restart an operational host. Build-time NuGet restore
is not runtime installation. No arbitrary assembly loading, runtime downloads,
hot installation/replacement, sandbox, or marketplace is delivered.
Provider code, including static metadata getters, is trusted in-process code
with the host's privileges. Packaging does not isolate malicious code.

Multiple protocols and identity schemes may eventually coexist. Initially
there will be one authoritative metadata provider and one artifact provider;
F-01 does not enforce selection/cardinality. Authentication remains distinct
from centralized authorization. Provider implementations must not depend on
other concrete providers, even of the same family. SDK/EF/schema/migration
details stay private to their owning provider, never Core or endpoint contracts.
Do not expose `DbContext`, `IQueryable`, transaction/connection objects, vendor
SDK objects, HTTP context, delegates, or arbitrary payload escape hatches in
provider-neutral declarations.

Cache identity/auth partitioning, freshness, safe upstream/SSRF policy,
integrity and verified atomic publication, bounded asynchronous streaming and
cancellation, single-flight, reference-safe deletion/GC, authorization, and
shared audit/telemetry remain centralized Core/security/Hosting responsibilities.
Markers never authorize a provider to bypass or duplicate these invariants.
No rename, portable transaction, NoSQL interchangeability, or cross-store
atomicity guarantee follows from a marker.

## Compatibility and release obligations

The [normative policy and all 23 examples](../specs/001-provider-contracts/contracts/compatibility.md)
distinguish **module**, **host**, and **abstractions** release versions.
Dependencies constrain the target module's version. Platform ranges separately
constrain host and abstractions, not an arbitrary custom executable's version.

Only exact `[1.2.3]` and bounded intervals such as `[1.2.0,2.0.0)` are accepted
by the written policy. Bounds are explicit three-part versions; inclusive and
exclusive bounds are supported. Missing, empty/reversed, unbounded, bare-minimum,
and floating ranges are unsupported. Build metadata does not affect precedence;
prerelease labels compare case-insensitively. Prereleases precede their stable
release and require a separate explicit opt-in for each host, abstractions,
or dependency axis. A `-rc` bound or prerelease module version does not opt in.
Restore success and registration alone prove none of these compatibility claims.

A required target must be enabled and compatible. An absent, installed-disabled,
or registered-disabled optional target is unavailable: no integration/capability
claim or active dependency edge. An enabled optional target must meet its range
and prerelease flag, even if the integration is allegedly unused. Incompatibility
makes the composition unsupported. Never silently disable a module/integration,
ignore a dependency, fall back, or substitute another provider. Operators must
explicitly change selection or install a compatible version and revalidate.
F-01 classifies test examples; runtime enforcement is future F-02/F-03 work.

Assess source compatibility for **consumers and implementers**, binary
compatibility for previously compiled supported modules, and behavioral
compatibility for documented obligations. Required member additions, removals,
signature/identity changes, and stronger publication/auth guarantees are breaking
even when a revised consumer compiles. Stable breaking contracts require a
major transition; pre-1.0 breaks require an explicit minor transition, e.g.
`0.1` to `0.2`, and updated narrow ranges. Patch releases remain nonbreaking;
never infer blanket `0.x` interoperability.

Before a breaking release, document affected members/behaviors, consumer and
implementer source impact, old-binary impact, old/new compatibility ranges,
provider/host code/configuration changes and rebuilds, qualification evidence,
and rollback/backup instructions. Publish migration guidance with that release.
Retain a coherent previous host/contract/provider set for rollback; do not
relabel incompatible binaries as supported. Local compile tests do not authorize
package publication or replace later behavior/conformance qualification.

## Later-feature handoffs

| Feature | Reserved work |
| --- | --- |
| F-02 | Module registry, service wiring, activation, disabled behavior, readiness/shutdown |
| F-03 | Configuration precedence, secret references/resolution, semantic compatibility, category/cardinality validation |
| F-04 | Sanitized management capability discovery |
| F-05 | Metadata operations, concurrency, transactions, schema/recovery |
| F-06 | Artifact streaming, staging, commit visibility, read/delete guarantees |
| F-07 | Reusable operational provider conformance and support qualification |
| F-08 | Identity normalization, scheme composition, central permission mapping |

Architecture checks inspect actual source/package graphs, signatures, and IL
using explicit ownership; they neither execute providers nor certify their
behavior. Unused framework references still count as dependencies; being a BCL
type does not make query/connection/transaction objects valid shared contracts.
All eight named platform/provider/host scans are required, not just a nonempty
scan manifest. Identity providers may reference the approved Hosting API,
including its transitive Core dependency. That does not permit a direct
Identity-to-Core reference or an unrelated SDK-mediated path; the scanner
tracks those paths separately even when both reach the same assembly.
Native-client restore, crash recovery, HTTP lifecycle,
performance, and production deployment are separate acceptance work.
