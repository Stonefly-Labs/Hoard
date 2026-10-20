# F-01 Research and Design Decisions

**Date**: 2026-10-20

**Scope**: Planning only; no dependencies installed or product projects created.

The specification, clarification review, constitution, architecture, and
ADR-0001 determine product scope. Public upstream documentation was researched
for packaging, DI, version semantics, and inspection tooling. All planning
unknowns are resolved below; no product clarification is outstanding.

## 1. Deliver a declaration foundation, not premature provider operations

**Decision**: Put immutable module declarations and four category-specific
provider marker interfaces in BCL-only `Hoard.Abstractions`. Put explicit
declaration/type registration in `Hoard.Hosting`. Compile a provider-free Core
boundary and an Application boundary, without implementing cache operations,
HTTP endpoints, activation, or a curated executable.

**Rationale**: F-01 must prove independent contracts and composition, while
F-02/F-03 own activation and validation, F-05/F-06 own store operations, and
F-08 owns identity behavior. A marker identifies the extension family, not
functional storage, protocol, or authentication support. Later operational
contract additions must obey the pre-1.0 breaking-change policy.

**Alternatives considered**: Designing repository CRUD, artifact staging, or
authentication methods now would preempt subsequent requirements. Empty
untyped interfaces without family distinctions would not express ownership.
Splitting abstractions into four packages adds release complexity without
an established need.

**Evidence**: [specification assumptions](spec.md#assumptions),
[architecture](../../docs/ARCHITECTURE.md#3-assemblies-and-allowed-dependencies),
and [ADR-0001](../../docs/adr/0001-modular-provider-architecture.md).

## 2. Keep descriptor inspection separate from provider construction

**Decision**: A provider package exposes a static immutable declaration that
the host passes to `AddHoard().AddModule<TProvider>(declaration)`. Registration
records the declaration and type token in DI, without constructing the provider,
building a second container, or invoking lifecycle callbacks. Family markers
have no registration, HTTP, or service-provider methods.

**Rationale**: Authors can inspect compatibility without creating services,
resolving credentials, or opening external connections. The static declaration
pattern is an authoring convention, not a static-abstract-interface requirement.
Registration does not imply enablement, singleton category selection, readiness,
or runtime compatibility approval.

**Alternatives considered**: Reading an instance `Descriptor` property would
require construction. Static abstract members would add generic authoring
constraints without improving the explicit declaration/type pairing. Calling
provider factories during registration would activate trusted code prematurely.
Using `TryAdd` keyed by module ID could silently discard invalid duplicates.

**Evidence**: Microsoft documents service descriptors as registration metadata:
[DI registration](https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection#service-registration-methods)
and [ServiceDescriptor](https://learn.microsoft.com/en-us/dotnet/api/microsoft.extensions.dependencyinjection.servicedescriptor).

## 3. Use SDK packaging and actual package-only consumer proofs

**Decision**: Target `net10.0`; plan an SDK baseline of `10.0.100` with
`rollForward: latestFeature` and `allowPrerelease: false`. Introduce SDK-style
projects, central dependency versions, and tracked restore lockfiles during
implementation. Pack platform libraries and independently build five fixture
packages against those packages in an isolated local feed. The custom-host
consumer uses PackageReference, not ProjectReference or internal access.

**Rationale**: A source-project reference alone cannot prove the published
dependency surface is usable. Fixture projects must not inherit hidden
repository props, friend assemblies, source imports, or solution references.
Five packages cover four families and two independent artifact implementations.
No public package publishing or runnable distribution is required.

**Alternatives considered**: ProjectReference-only fixtures would conceal
packaging mistakes. Publishing test packages to nuget.org would add permissions,
irreversible external effects, and misleading support claims. Building a
production host is unnecessary for compile-only acceptance.

**Evidence**:
[SDK packing](https://learn.microsoft.com/en-us/nuget/create-packages/creating-a-package-dotnet-cli),
[local feeds](https://learn.microsoft.com/en-us/nuget/hosting-packages/local-feeds),
[global.json](https://learn.microsoft.com/en-us/dotnet/core/tools/global-json),
and [PackageReference assets](https://learn.microsoft.com/en-us/nuget/consume-packages/package-references-in-project-files#controlling-dependency-assets).
`PrivateAssets=all` controls propagation, not encapsulation: it cannot make an
SDK type in a public signature safe or remove the referencing project's own
dependency closure.

## 4. Represent compatibility without a versioning dependency in abstractions

**Decision**: Store normalized version and range strings in declarations.
Adopt the explicit bounded interval subset and separate prerelease opt-in
defined in [the compatibility contract](contracts/compatibility.md).
Use `NuGet.Versioning` only in acceptance tests for parsing/comparison in F-01;
the later F-03 runtime evaluator consumes the same written policy.

**Rationale**: Host version, abstraction version, and module release version
are distinct axes. NuGet interval notation is familiar, but package resolution
rules are not a sufficient host compatibility policy. In particular, do not
assume `VersionRange.Satisfies` enforces Hoard's prerelease restrictions:
explicit opt-in is a separate condition before interval evaluation.

**Alternatives considered**: A homegrown SemVer parser is unnecessary. Adding
NuGet.Versioning to Abstractions would expand every provider's dependency
closure for metadata that can be represented as strings. Floating versions or
unbounded ranges would make author claims harder to audit.

**Evidence**:
[NuGet version ranges and normalization](https://learn.microsoft.com/en-us/nuget/concepts/package-versioning),
[NuGet dependency resolution](https://learn.microsoft.com/en-us/nuget/concepts/dependency-resolution),
and [NuGet.Versioning](https://www.nuget.org/packages/NuGet.Versioning/7.9.0).
NuGet uses case-insensitive prerelease labels and ignores build metadata in
precedence; the Hoard policy states these choices explicitly.

## 5. Check resolved dependencies and compiled usage, not names alone

**Decision**: Use one architecture test project with Mono.Cecil for compiled
assembly/type/IL inspection. Combine resolved restore graphs and
`project.assets.json` with compiled references; inspect package-only consumers
as well as source projects. Define package ownership explicitly. Use isolated
negative inputs, including a synthetic cyclic graph because MSBuild rejects
project cycles before an assembly can be compiled.

**Rationale**: Direct `.csproj` checks miss transitive dependencies, unused
declared references, public generic signatures, and same-assembly cross-slice
handler calls. Cecil provides an established object model without loading
provider code. It belongs only in tests. Missing metadata or unresolved
inspection inputs must fail explicitly, not pass an incomplete scan.

**Alternatives considered**: Namespace-only tests cannot establish actual
assembly identity or package closure. Reflection would load inspected
assemblies and complicate isolation. BCL `System.Reflection.Metadata` is a
valid zero-package alternative but needs more handle/signature/IL decoding
code for this check set. A production scanning framework is not needed.

**Evidence**:
[Mono.Cecil upstream](https://github.com/jbevain/cecil),
[Mono.Cecil package](https://www.nuget.org/packages/Mono.Cecil/0.11.6),
[metadata reader](https://learn.microsoft.com/en-us/dotnet/api/system.reflection.metadata.metadatareader),
and [NuGet dependency resolution](https://learn.microsoft.com/en-us/nuget/concepts/dependency-resolution).
The published package is compatible through `netstandard2.0`; it is not a
runtime dependency of any Hoard module.

## 6. Select a small, pinned test/tooling stack

**Decision**: Use nullable-aware C#, SDK analyzers, `dotnet format`, and the
existing VSTest-compatible `dotnet test` route with the following stable
planning pins, verified on nuget.org on 2026-10-20:

| Dependency | Planned version | Placement |
| --- | --- | --- |
| Microsoft.Extensions.DependencyInjection.Abstractions | 10.0.13 | Hosting only |
| NuGet.Versioning | 7.9.0 | Compatibility acceptance tests only |
| xunit | 2.9.3 | Test projects only |
| xunit.runner.visualstudio | 4.0.1 | Test adapter, private assets |
| Microsoft.NET.Test.Sdk | 18.11.0 | Test projects only |
| Mono.Cecil | 0.11.6 | Architecture tests only |

**Rationale**: The DI abstraction package has no package dependencies for its
`net10.0` group; Abstractions and Core still need no external PackageReference.
The adapter supports xUnit v2 and .NET 8+, covering `net10.0`. Pin direct versions
centrally and lock transitive resolution instead of floating at restore time.
Review licenses, advisories, and package contents when actually adding them;
this research is not a future dependency-health guarantee.

**Alternatives considered**: A third-party composition framework or mandatory
MediatR is unnecessary. xUnit v3 would work, but its new runner model is not
needed for these focused library checks. Custom test/format tooling adds no
value here.

**Evidence**:
[DI package](https://www.nuget.org/packages/Microsoft.Extensions.DependencyInjection.Abstractions/10.0.13),
[xUnit](https://www.nuget.org/packages/xunit/2.9.3),
[adapter](https://www.nuget.org/packages/xunit.runner.visualstudio/4.0.1),
[test SDK](https://www.nuget.org/packages/Microsoft.NET.Test.Sdk/18.11.0),
and [format command](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-format).

## 7. Keep validation claims scoped

**Decision**: Define future acceptance commands in `quickstart.md`, clearly
labelled unavailable until implementation. Run only existing repository checks
at this planning checkpoint. Preserve custom checklist review, task generation,
read-only analysis, and implementation as separate stages.

**Rationale**: Compilation proves public contract/composition usability, not
working providers, startup enforcement, native-client restore, storage safety,
or a functioning cache. There is no UI, database, HTTP, cloud, or workload
performance claim to measure in F-01.

**Alternatives considered**: Running invented product commands or scaffolding
projects during planning would misrepresent evidence and violate stage limits.
