# F-01 Public Library Contracts

**Status**: Implemented source APIs at local acceptance version `0.1.0`, not
published packages.
This contract is a declaration/composition foundation, not a provider SDK with
working cache operations. [Data shapes](../data-model.md) and
[compatibility policy](compatibility.md) are part of this contract.

## Ownership and Dependency Surface

| Package | Public surface in F-01 | Allowed dependencies |
| --- | --- | --- |
| Hoard.Abstractions | Module declarations, metadata vocabulary, family markers | BCL only |
| Hoard.Core | Provider-free engine boundary; no operational API yet | Abstractions and BCL only |
| Hoard.Hosting | Explicit registration builder/records | Abstractions, Core, DI abstractions |
| Hoard.Application | Management boundary only; no endpoint yet | Core, Abstractions, approved public Hosting surface |

All four libraries are packable. Core/Application do not gain placeholder
cache methods, handlers, or arbitrary services merely to populate a directory.
Compiled empty boundary libraries are acceptable; their reference graph is
the F-01 proof, not an implemented engine.

Persistence/artifact fixture providers depend only on Abstractions; protocol
fixtures may use Core and the approved Hosting registration API; identity
fixtures may use the approved Hosting API when necessary. No fixture needs
HTTP integration, a provider SDK, real storage, or another concrete provider.

## Family Interfaces

Namespace: `Hoard.Abstractions.Providers`.

```csharp
public interface IHoardProvider { }
public interface IProtocolProvider : IHoardProvider { }
public interface IMetadataProvider : IHoardProvider { }
public interface IArtifactProvider : IHoardProvider { }
public interface IIdentityProvider : IHoardProvider { }
```

These are signature shorthand, not implementation bodies. They identify
families for authoring and future validation only. Providers must not infer
permission to define independent cache keys, bypass authorization, publish
unverified bytes, or perform unsafe deletion from implementing a marker.
No general hook bus, runtime package loader, or arbitrary callback interface
is introduced.

Operational interfaces are separate later work: metadata repositories and
concurrency in F-05, streaming/staging/commit/delete semantics in F-06,
identity normalization/scheme composition in F-08, and protocol operations
in their native-protocol features. Added required operational members require
an explicit compatible new interface or breaking version transition, not an
assumption that all `0.x` packages interoperate.

## Declarative Metadata

Namespace: `Hoard.Abstractions.Modules`.

The following named shapes are public and owned once by Abstractions:
`ModuleDescriptor`, `ModuleCategory`, `CompatibilityDeclaration`,
`ModuleDependency`, `CapabilityDeclaration`, `ConfigurationRequirement`,
`EndpointResponsibility`, `HealthResponsibility`, `ModuleProvenance`,
and `ModuleSupportStatus`. Their complete fields/constraints are in
[data-model.md](../data-model.md).

Use sealed records with required init-only properties, immutable arrays, and
no provider-specific base types. Do not expose EF Core, `IQueryable`,
`DbContext`, connection/transaction objects, vendor SDK objects, concrete
provider classes, DI services, `HttpContext`, delegates, or arbitrary
`object`/dictionary payloads as an escape hatch.

A provider package conventionally exposes a public static `Declaration`
property returning its immutable `ModuleDescriptor`. The convention does not
require a common static interface. Hosts pass metadata explicitly, so they
can inspect it without constructing providers. Static metadata access and
registration in the documented fixtures must do no external I/O and must not
read secrets. Trusted provider code remains capable of arbitrary process
actions; this contract does not claim isolation from a malicious static getter.

Declarations describe capabilities, not runtime health or support validation.
The absence of runtime F-02/F-03 validation in F-01 must be clearly documented,
not replaced with a permissive success result.

## Registration-Only Hosting API

Namespace: `Hoard.Hosting`.

```csharp
public static HoardBuilder AddHoard(this IServiceCollection services);

public static HoardBuilder AddModule<TProvider>(
    this HoardBuilder builder,
    ModuleDescriptor declaration)
    where TProvider : class, IHoardProvider;
```

The public static methods live on `HoardServiceCollectionExtensions` and
`HoardBuilderExtensions`, respectively. `HoardBuilder` is sealed, exposes a
get-only `Services: IServiceCollection`, and is obtained through `AddHoard`.
`HoardModuleRegistration` is a sealed immutable record with
`Declaration: ModuleDescriptor` and `ProviderType: Type`.

Contract behavior:

1. `AddHoard` wraps the caller's service collection without building a
   container, installing providers, mapping endpoints, or starting workers.
2. `AddModule` appends one registration data object with the supplied
   declaration and `typeof(TProvider)`, and returns the same builder.
3. Registration does not instantiate `TProvider`, register operational family
   services, enumerate assemblies, invoke arbitrary factories, or inspect
   private implementation types. It does not require a constructor constraint.
4. Repeated registrations are retained, not silently deduplicated/replaced.
   Duplicate IDs and other invalid compositions must be detectable by F-02/
   F-03; F-01 does not claim to enforce them.
5. Null service collection, builder, or declaration raises the appropriate
   `ArgumentNullException`. There is no anonymous/default provider fallback.
6. Descriptor/type category agreement, ranges, dependency ordering, singleton
   category selection, secret resolution, enablement, activation, readiness,
   shutdown, and HTTP integration are outside F-01 registration behavior.

Registering record instances in DI is not provider activation. A registration
acceptance case uses a provider whose constructor throws if called; inspecting
the declarations/recorded types must not call it. No log should claim a module
is enabled, validated, or ready merely because its registration was recorded.

## Compile-Only Custom Host

The compile-only `examples/CustomHost` references Hosting plus the four fixture
packages through package references and uses ASP.NET Core's shared framework
for `WebApplication.CreateBuilder`. Its short entry point calls `AddHoard`
and four explicit generic `AddModule` registrations. It never calls
`Build`, `MapHoard`, `Run`, or `Start`; no production lifecycle is available.
No `InternalsVisibleTo`, source import, or host code copied from the platform.

Fixtures: Protocol, Metadata, Artifact.One, Identity are the baseline;
Artifact.Two is built independently in its own project/package. Both artifact
fixtures declare the same logical test module ID/category and compatible
ranges so either can replace the other in separate compositions. They must
not be selected together or advertised as production providers.

The replacement proof changes only the host's artifact PackageReference and
registration type/declaration, then independently restores/builds the copy.
Fixture packages never reference one another, and no Core or unrelated
provider source changes between variants.

Curated distribution documentation must say configuration selects only already
bundled packages; the curated runtime is not delivered in F-01. Adding a custom
provider requires explicit package reference/registration, rebuild, redeploy,
and restart once an operational host exists. Neither NuGet restore at build
time nor this example is runtime installation.

## Invariant and Feature Handoffs

| Concern | Reserved owner / F-01 restraint |
| --- | --- |
| Module registry, activation, service wiring, disabled behavior, readiness/shutdown | F-02 consumes registrations; no provider activation or lifecycle callbacks here |
| Config precedence, secrets, semantic compatibility, category/cardinality validation | F-03; metadata carries requirements but no configured values |
| Management capability discovery | F-04; no API endpoint or UI surface here |
| Metadata operations, transactions, recovery | F-05; no portable `DbContext`, transaction, or NoSQL guarantee |
| Artifact I/O and publication capabilities | F-06; no rename assumption, cross-store transaction, or unconstrained byte-array API |
| Reusable operational conformance/certification | F-07; fixtures prove compilation only |
| Authentication and central permission mapping | F-08; markers confer no authorization |
| Identity/auth partitioning, freshness, safe upstreams, verified publication, cancellation/bounded streaming, single-flight, safe GC, telemetry | Shared Core/security/Hosting as specified by later features; never duplicated in family seams |

## Required F-01 Evidence

Compile four family consumers and both artifact alternatives against local
packages with no source access. Inspect metadata without provider construction.
Build Core independently without concrete providers. Build both custom-host
variants and run the architecture/compatibility checks. Confirm every example
and result is labelled fixture/compile-only. Operational equivalence, integrity,
native-client compatibility, and production support require later evidence.
