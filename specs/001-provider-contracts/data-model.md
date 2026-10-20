# F-01 Declaration and Evidence Model

**Status**: Planned public shapes, not implemented APIs or a database schema.
All owning packages target `net10.0`. Names below are the proposed F-01 names
to implement and verify, not published package claims.

## ModuleDescriptor

**Owner**: `Hoard.Abstractions.Modules`

**Purpose**: Describe a package without constructing a provider.

| Field | Planned type | Meaning / constraint |
| --- | --- | --- |
| Id | `string` | Stable lowercase identifier, pattern `[a-z0-9]+([.-][a-z0-9]+)*`; never inferred from assembly or class name |
| Category | `ModuleCategory` | One of Protocol, Metadata, Artifact, Identity |
| Version | `string` | Module's normalized three-part SemVer, optional prerelease/build metadata |
| Compatibility | `CompatibilityDeclaration` | Separate host and abstraction ranges and prerelease flags |
| Dependencies | `ImmutableArray<ModuleDependency>` | Required/optional module IDs and version requirements |
| Capabilities | `ImmutableArray<CapabilityDeclaration>` | Descriptive ID, version, explanation; not proof of implemented behavior |
| Configuration | `ImmutableArray<ConfigurationRequirement>` | Option key, description, required flag, secret-reference flag; no values/default secrets |
| Endpoints | `ImmutableArray<EndpointResponsibility>` | Stable responsibility ID and description, not an HTTP callback or active route |
| Health | `ImmutableArray<HealthResponsibility>` | Stable responsibility ID, required-for-readiness flag, description; no probe execution |
| Provenance | `ModuleProvenance` | Publisher, source/support URLs where available, support status |

Declarations are sealed immutable record shapes with init-only properties and
immutable child collections. Required fields have no success-shaped defaults;
optional collections are explicitly empty, not default/uninitialized arrays.
Descriptions are documentation, never executable expressions, secret values,
live readiness, or configured provider state.

These constraints define a supported declaration. F-01 can represent invalid
inputs for later validators; it does not silently sanitize or certify them.
F-02 owns duplicate IDs and dependency graphs; F-03 owns semantic validation,
category/type matching, cardinality, and runtime compatibility/configuration.
F-01's acceptance examples must still satisfy this model.

## CompatibilityDeclaration and ModuleDependency

**Owner**: `Hoard.Abstractions.Modules`

`CompatibilityDeclaration` has required `HostRange`, `AbstractionsRange`
(strings), and `AllowPrereleaseHost`, `AllowPrereleaseAbstractions` (booleans,
false unless explicitly opted in). Ranges use the bounded interval/exact
syntax in [compatibility.md](contracts/compatibility.md).

`ModuleDependency` has required `ModuleId`, `VersionRange`, `Optional`, and
`AllowPrerelease` fields. An optional dependency may be absent; if present and
used, it must be compatible. Duplicate declarations, self-references, and
cycles are unsupported compositions, not automatically deduplicated edges.
Dependencies are descriptive relationships between modules, not instructions
to download NuGet packages or load assemblies.

## Capability and Responsibility Metadata

**Owner**: `Hoard.Abstractions.Modules`

- `CapabilityDeclaration`: required `Id`, normalized `Version`, `Description`.
- `ConfigurationRequirement`: required `Key`, `Description`, `Required`,
  `SecretReference`. A secret-reference entry describes the requirement for a
  reference, never contains the reference's resolved value.
- `EndpointResponsibility`: required `Id`, `Description`. No route delegate,
  `HttpContext`, middleware type, or configured upstream URL.
- `HealthResponsibility`: required `Id`, `Description`, `RequiredForReadiness`.
  This states a future obligation, not a current status.
- `ModuleProvenance`: required `Publisher`, `SupportStatus`; optional public
  `SourceUrl`, `SupportUrl` (`Uri?`). Support status is `Fixture`, `Community`, or
  `MaintainerSupported`; authors must not mistake it for certification.

Names, keys, IDs, versions, ranges, publishers, and descriptions above are
`string`; flags are `bool`; `SupportStatus` is `ModuleSupportStatus`.

IDs use the module-ID grammar. Configuration keys are nonempty documented
option paths. Public URLs must not carry credentials, tokens, or private
environment details. Fixtures use `Fixture` status, no operational capabilities,
and empty configuration/endpoint/health collections rather than fake service
promises. Operational providers' later features define their actual metadata.

## Provider Family Seams

**Owner**: `Hoard.Abstractions.Providers`

`IHoardProvider` is the common marker. `IProtocolProvider`,
`IMetadataProvider`, `IArtifactProvider`, and `IIdentityProvider` inherit it.
They contain no operational members in F-01. One package may expose multiple
modules, each with a single category/declaration/implementation pairing.

| Family | Responsibility boundary | Initial selection model, enforced later |
| --- | --- | --- |
| Protocol | Native translation and protocol feature slices; calls shared Core for cache work | Multiple enabled protocols |
| Metadata | Private data/schema/transaction implementation behind later operations | Exactly one authoritative provider |
| Artifact | Private byte-store implementation behind later streaming/publication operations | Exactly one authoritative provider |
| Identity | Authenticate/map identity through later shared contracts; never grant independent permissions | Multiple schemes |

No marker promises read/write behavior or functional interchangeability.
Authorization and universal cache correctness remain centrally owned.

## HoardModuleRegistration

**Owner**: `Hoard.Hosting`

Required immutable properties `Declaration: ModuleDescriptor` and
`ProviderType: Type` pair descriptive metadata with the explicitly referenced
implementation. Hosting alone owns this type; Abstractions never contains
reflection/DI/HTTP composition objects. Registrations are added to
`IServiceCollection` as data. They are not provider instances, selected
implementations, activated modules, or status records.

The constrained generic registration requires a class implementing
`IHoardProvider`; category correctness and composition validity are later
validation responsibilities. Null arguments fail with standard argument errors;
no catch/fallback converts invalid input into a successful registration.

## Architecture Evidence

**Owner**: Architecture test project; never a runtime module.

An inspection node has resolved project/package/assembly identity and boundary
ownership. An edge records reference kind (declared, resolved transitive,
signature, or IL use), source, and target. A violation records `RuleId`,
source/target identity, inspected location/member, and a dependency path for a
transitive violation. Ownership is explicit and checked against assembly
identity; namespace spelling alone does not establish trust.

The graph includes local package consumers and declared project edges even
when unused by emitted IL. Public-surface checks recurse through constructed
generics, arrays, modifiers, constraints, base types/interfaces, attributes,
fields, properties, events, and method parameters/returns. Slice checks inspect
nonpublic member use within an assembly as well as external assembly use.
Missing inspection inputs or unclassified non-framework dependencies are errors.

## Relationships and State

A provider package supplies a declaration plus a family implementation.
A host explicitly references its package and records a registration.
Declarations refer to compatibility requirements, dependencies, and descriptive
capabilities; architecture evidence checks actual build relationships separately.
Metadata never makes a forbidden compile-time dependency permitted.

F-01 has no runtime state machine. The evidence sequence is source compilation,
local packing, independent consumer restore/build, and result inspection.
Installed/enabled/active/ready/disabled states, initialization transitions,
shutdown, cache publication, and persistence lifecycle belong to later features.
