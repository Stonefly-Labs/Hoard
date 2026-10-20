# Tasks: Platform Package Boundaries and Provider Contracts

**Input**: Design documents from `specs/001-provider-contracts/` (F-01).
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [public API](contracts/public-api.md),
[compatibility policy](contracts/compatibility.md),
[architecture rules](contracts/architecture-rules.md), and
[quickstart.md](quickstart.md).

**Status**: All 57 implementation tasks are complete, including architecture
review corrections and the final support-claim audit (T056-T057). Checked tasks
record actual bounded implementation evidence, never feature merge/completion.
The reviewer-owned architecture and compatibility checklists already record
38/38 satisfied requirements-quality criteria; they are not implementation
evidence. Read-only analysis passed before this separately authorized
implementation invocation. See the current [implementation evidence](plan.md#implementation-evidence-2026-10-20)
and tracked checkpoint; convergence/finalization remain separate stages.

**Tests**: Required by FR-013/FR-014, the four stories' independent tests, and
SC-001 through SC-006. Write the focused acceptance tests before their
implementation. Observe the intended missing-contract/behavior failure, then
make the positive case pass. For architecture rules, record rejection of each
isolated forbidden input for the intended rule before accepting its permitted
counterpart; an unrelated compilation failure is not rejection evidence.

**Organization**: Shared setup and declaration prerequisites precede one phase
per user story, in specification priority order, followed by cross-cutting
acceptance/documentation work. These are implementation instructions for a
authorized implementation stage, not permission to implement later features.

## Format: `[ID] [P?] [Story] Description`

- Every task is a `TNNN` checklist item with explicit file paths and evidence-backed completion state.
- `[P]` means different files and no dependency on another task in the indicated
  parallel group, after the listed prerequisites are complete. It does not
  override prerequisites or authorize agents/workflow engines.
- `[US1]` through `[US4]` identify specification user stories. Shared setup,
  foundational, and polish tasks have no story label.
- References to requirements, outcomes, rules, and cases use the IDs in the
  linked feature artifacts; the traceability table below assigns every FR/SC.

## Path Conventions

Paths are repository-relative. The four packable platform libraries belong in
`src/`; test projects in `tests/unit/`, `tests/architecture/`, and
`tests/integration/`; standalone inputs in `tests/fixtures/`; the compile-only
consumer in `examples/CustomHost/`. The solution includes platform/test projects,
not fixture/example projects. Build standalone copies outside repository props
inheritance. Local feeds, caches, manifests, and outputs belong only in the
orchestrator's private temporary directory, never Git.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Introduce only the .NET foundation/build inputs authorized by F-01.
Do not populate the curated Host, real provider directories, or `apps/web`.

- [X] T001 Configure `global.json` for SDK `10.0.100`, stable-only `latestFeature` roll-forward, and `Directory.Build.props` for `net10.0`, nullable-aware C#, SDK analyzers, restore lockfile generation, and local package version `0.1.0`; add only applicable C# formatting settings to `.editorconfig`.
- [X] T002 [P] Pin the six dependencies from research in `Directory.Packages.props`: DI abstractions 10.0.13, NuGet.Versioning 7.9.0, xunit 2.9.3, xunit.runner.visualstudio 4.0.1, Microsoft.NET.Test.Sdk 18.11.0, and Mono.Cecil 0.11.6; assess licenses/advisories when adding them and record any blocker in `specs/001-provider-contracts/research.md` rather than silently replacing a pin.
- [X] T003 Create packable `src/Hoard.Abstractions/Hoard.Abstractions.csproj`, `src/Hoard.Core/Hoard.Core.csproj`, `src/Hoard.Hosting/Hoard.Hosting.csproj`, and `src/Hoard.Application/Hoard.Application.csproj` with the public API's allowed references; keep Abstractions/Core BCL-only apart from Core's Abstractions reference, DI abstractions in Hosting only, and Core/Application free of invented operational members.
- [X] T004 Create `tests/unit/Hoard.Foundation.Tests/Hoard.Foundation.Tests.csproj`, `tests/architecture/Hoard.Architecture.Tests/Hoard.Architecture.Tests.csproj`, `tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj`, and `Hoard.slnx`; keep NuGet.Versioning in unit acceptance tests, Mono.Cecil in architecture tests, test dependencies non-transitive/private where appropriate, and standalone fixtures/examples outside the solution; generate source/test project lockfiles with an initial pinned restore before verifying locked-mode replay.
- [X] T005 [P] Extend `.gitignore` for .NET build/test outputs and generated local feeds/caches without ignoring `packages.lock.json`; preserve existing secret, runtime-data, infrastructure-state, and `.terraform.lock.hcl` handling.

**Checkpoint**: Four library boundaries and three test projects are defined;
there is still no runnable product or production provider.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement declaration shapes shared by all stories and the bounded
validation entry-point foundation. All stories wait for this phase.

- [X] T006 Add failing public-consumer compilation cases in `tests/unit/Hoard.Foundation.Tests/DeclarationContractTests.cs` with isolated source inputs in `tests/fixtures/declarations/` to distinguish required/init-only immutable declarations from missing required members or mutable collection contracts; include accepted explicit empty collections and representable unsupported inputs, without adding F-03 semantic validation or tests of trivial getters.
- [X] T007 Define `src/Hoard.Abstractions/Modules/ModuleCategory.cs` and `src/Hoard.Abstractions/Modules/ModuleSupportStatus.cs` using the exact model choices: Category is "One of Protocol, Metadata, Artifact, Identity"; "Support status is `Fixture`, `Community`, or `MaintainerSupported`; authors must not mistake it for certification."
- [X] T008 [P] Implement `src/Hoard.Abstractions/Modules/CompatibilityDeclaration.cs` and `src/Hoard.Abstractions/Modules/ModuleDependency.cs` as sealed immutable records: compatibility "has required `HostRange`, `AbstractionsRange` (strings), and `AllowPrereleaseHost`, `AllowPrereleaseAbstractions` (booleans, false unless explicitly opted in)"; dependency "has required `ModuleId`, `VersionRange`, `Optional`, and `AllowPrerelease` fields." Keep compatibility descriptive; registration must not enable targets or repair optional conflicts.
- [X] T009 [P] Implement `src/Hoard.Abstractions/Modules/CapabilityDeclaration.cs` and `src/Hoard.Abstractions/Modules/ConfigurationRequirement.cs`: "`CapabilityDeclaration`: required `Id`, normalized `Version`, `Description`"; "`ConfigurationRequirement`: required `Key`, `Description`, `Required`, `SecretReference`." Preserve "IDs use the module-ID grammar" and "Configuration keys are nonempty documented option paths"; secret-reference metadata describes a requirement, never a resolved value.
- [X] T010 [P] Implement `src/Hoard.Abstractions/Modules/EndpointResponsibility.cs`, `src/Hoard.Abstractions/Modules/HealthResponsibility.cs`, and `src/Hoard.Abstractions/Modules/ModuleProvenance.cs`: endpoint has "required `Id`, `Description`"; health has "required `Id`, `Description`, `RequiredForReadiness`"; provenance has "required `Publisher`, `SupportStatus`; optional public `SourceUrl`, `SupportUrl` (`Uri?`)." Apply "IDs use the module-ID grammar" and "Public URLs must not carry credentials, tokens, or private environment details." Do not add route delegates, probes, live status, or HTTP types.
- [X] T011 Implement `src/Hoard.Abstractions/Modules/ModuleDescriptor.cs` with the data model's exact field types and constraints: Id is "Stable lowercase identifier, pattern `[a-z0-9]+([.-][a-z0-9]+)*`; never inferred from assembly or class name"; Category is "One of Protocol, Metadata, Artifact, Identity"; Version is "Module's normalized three-part SemVer, optional prerelease/build metadata"; Compatibility is "Separate host and abstraction ranges and prerelease flags"; Dependencies are "Required/optional module IDs and version requirements"; Capabilities are "Descriptive ID, version, explanation; not proof of implemented behavior"; Configuration is "Option key, description, required flag, secret-reference flag; no values/default secrets"; Endpoints are "Stable responsibility ID and description, not an HTTP callback or active route"; Health is "Stable responsibility ID, required-for-readiness flag, description; no probe execution"; Provenance is "Publisher, source/support URLs where available, support status". Use the model-wide constraints "Declarations are sealed immutable record shapes with init-only properties and immutable child collections" and "Required fields have no success-shaped defaults; optional collections are explicitly empty, not default/uninitialized arrays"; run T006's positive/negative consumers without claiming unsupported declarations are validated.
- [X] T012 Introduce `scripts/validate-foundation.sh` with explicit prerequisites, fail-fast subprocess handling, a private resolved temporary directory, sanitized actionable errors, and targeted cleanup limited to its own generated paths; establish a build-evidence manifest consumed by tests rather than recursive invocation from tests, and add complete proof steps in T021/T022/T034/T042/T048/T052 before this entry point can report full success.

**Checkpoint**: Public metadata uses BCL-only types and represents declarations
without runtime state. All names, keys, IDs, versions, ranges, publishers, and
descriptions in these shapes are `string`; flags are `bool`; child collections
use the model's `ImmutableArray<T>`. No parser, secret resolver, startup
validator, provider selection, or activation is introduced here.

## Phase 3: User Story 1 - Extend Hoard Without Changing Its Engine (Priority: P1)

**Goal**: Prove independent public-package consumption for four provider
families, with two independent artifact fixtures and a provider-free Core.

**Independent Test**: Build Core in isolation with only Abstractions reachable;
then compile/pack five copied standalone provider projects against just-built
local packages. Inspect actual resolved and packed dependencies, not merely
successful compilation. No source/friend access, external service, or Core edit
is allowed. This is the suggested first/MVP increment, not complete F-01.

### Tests for User Story 1

- [X] T013 [P] [US1] Write failing package-independence acceptance tests in `tests/integration/Hoard.Composition.Tests/ProviderPackageTests.cs` for five unique local fixture packages, four family consumer builds, no ProjectReference/source import/friend access/hidden repository props, and agreement between each packed `.nuspec` and resolved consumer assets.
- [X] T014 [P] [US1] Write failing provider-free acceptance tests in `tests/integration/Hoard.Composition.Tests/CoreIndependenceTests.cs` requiring an isolated Core restore/build, declared project edges and the complete resolved closure containing only Core/Abstractions/BCL; fail explicitly for missing proof inputs instead of accepting a solution build or `--no-dependencies`.

### Implementation for User Story 1

- [X] T015 [US1] Define `src/Hoard.Abstractions/Providers/IHoardProvider.cs`, `src/Hoard.Abstractions/Providers/IProtocolProvider.cs`, `src/Hoard.Abstractions/Providers/IMetadataProvider.cs`, `src/Hoard.Abstractions/Providers/IArtifactProvider.cs`, and `src/Hoard.Abstractions/Providers/IIdentityProvider.cs` exactly as marker inheritance in the public API; document that they grant no cache, storage, authentication, or authorization operations.
- [X] T016 [P] [US1] Create self-contained `tests/fixtures/providers/Protocol/Hoard.Fixtures.Protocol.csproj` and `ProtocolProvider.cs` with its own dependency/build settings, Abstractions PackageReference, public static immutable Declaration, and `IProtocolProvider` implementation; use Fixture support status, no operational capabilities, and empty configuration/endpoint/health collections.
- [X] T017 [P] [US1] Create self-contained `tests/fixtures/providers/Metadata/Hoard.Fixtures.Metadata.csproj` and `MetadataProvider.cs` with its own dependency/build settings, Abstractions PackageReference, public static immutable Declaration, and `IMetadataProvider` implementation; add no EF Core, DB, transactions, or operational capability claim.
- [X] T018 [P] [US1] Create self-contained `tests/fixtures/providers/Artifact.One/Hoard.Fixtures.Artifact.One.csproj` and `ArtifactOneProvider.cs` using only an Abstractions PackageReference, a static Fixture declaration, and `IArtifactProvider`; choose the logical test module ID/category and compatible platform ranges also used by Artifact.Two, with no byte-store operations.
- [X] T019 [P] [US1] Create independent `tests/fixtures/providers/Artifact.Two/Hoard.Fixtures.Artifact.Two.csproj` and `ArtifactTwoProvider.cs` using only an Abstractions PackageReference and `IArtifactProvider`; match Artifact.One's logical test ID/category and compatible ranges without referencing its package/source, and make no equivalence or production-support claim.
- [X] T020 [P] [US1] Create self-contained `tests/fixtures/providers/Identity/Hoard.Fixtures.Identity.csproj` and `IdentityProvider.cs` with its own dependency/build settings, Abstractions PackageReference, public static immutable Fixture declaration, and `IIdentityProvider`; implement no authentication, permissions, external connections, or secret access.
- [X] T021 [US1] Extend `scripts/validate-foundation.sh` to copy only Core/Abstractions and their complete build inputs into a clean work directory, restore/build Core independently and capture its actual closure, then pack all four platform libraries as local `0.1.0` packages into a fresh private feed; use explicit sources and an isolated cache so published/stale Hoard packages cannot satisfy the proof.
- [X] T022 [US1] Extend `scripts/validate-foundation.sh` to copy, locked-restore, compile, and pack each of the five standalone fixture projects separately outside repository props inheritance using the just-built feed and explicit nuget.org source; bootstrap applicable fixture locks with an initial pinned restore in isolation and retain them beside the source projects before repeating with fresh locked-mode copies; compile family-typed public consumers, capture source/package identities, `.nuspec`, resolved assets, and outputs in the evidence manifest, and reject inter-fixture references or missing local package provenance.
- [X] T023 [US1] Run T013/T014 through the focused composition runner for `tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj` after preparing isolated outputs with `scripts/validate-foundation.sh`; record five independently built packages, four family consumer successes, and the provider-free Core closure, without requiring US3's host or US4's classifier to claim this story's bounded result.

**Checkpoint**: All four family seams are consumable and both artifact packages
exist independently. A host swap is verified in US3; this checkpoint proves
neither runtime behavior nor complete feature acceptance.

## Phase 4: User Story 2 - Prevent Accidental Provider Coupling (Priority: P1)

**Goal**: Enforce the documented dependency/public-surface/slice boundaries with
complete inspection inputs, isolated negatives, and actionable diagnostics.

**Independent Test**: Build the separate permitted/forbidden architecture
fixtures, run each negative through its intended `ARCH-*` rule, then run the
permitted graph. Also inspect US1's actual packed library/provider inputs when
available; the final gate adds both US3 host variants.

### Tests for User Story 2

- [X] T024 [US2] Write failing rule-driven tests in `tests/architecture/Hoard.Architecture.Tests/ArchitectureRuleTests.cs` for ARCH-001 through ARCH-008, their permitted counterparts, and explicit inspection errors; assert source/target/rule/location and transitive paths rather than accepting any nonzero subprocess exit or unrelated rule failure.

### Implementation for User Story 2

- [X] T025 [US2] Define test-only `tests/architecture/Hoard.Architecture.Tests/BoundaryOwnership.cs` and `InspectionEvidence.cs` plus `tests/fixtures/architecture/ownership.json`: an inspection node has "resolved project/package/assembly identity and boundary ownership"; an edge records "reference kind (declared, resolved transitive, signature, or IL use), source, and target"; a violation records "`RuleId`, source/target identity, inspected location/member, and a dependency path for a transitive violation." Validate actual assembly identity, source-folder/slice namespace agreement, and framework provenance from resolved assets rather than namespace/name-prefix trust.
- [X] T026 [P] [US2] Create self-contained permitted fixtures under `tests/fixtures/architecture/Permitted/` covering the allowed graph, provider-private SDK use outside Core's closure, neutral public signatures, and isolated same-assembly slices using public shared contracts; give every negative below a named permitted counterpart.
- [X] T027 [P] [US2] Create isolated inputs under `tests/fixtures/architecture/ForbiddenAbstractions/`, `ForbiddenCore/`, and `TransitiveCore/` for ARCH-001/ARCH-002/ARCH-003, including provider/EF/SDK and Hosting/HTTP edges, unused declared references, neutral-looking intermediate helpers, and packed `.nuspec`/resolved-package negatives; never add forbidden references to the product solution.
- [X] T028 [P] [US2] Create isolated inputs under `tests/fixtures/architecture/PublicTypeLeaks/`, `ProviderCoupling/`, and `ApplicationInternals/` for ARCH-004/ARCH-005/ARCH-008, covering direct and recursively nested generic/attribute/constraint leaks, unrelated and same-family concrete-provider references, private EF/SDK use in slices, and unapproved package edges.
- [X] T029 [P] [US2] Create isolated inputs under `tests/fixtures/architecture/CrossSlice/` for ARCH-007 same-assembly handler/member calls, external assembly use, and compiler-generated async/nested ownership, plus `tests/fixtures/architecture/Cycles/graph.json` for ARCH-006 project/package cycles that MSBuild cannot compile; include otherwise identical non-coupled/acyclic counterparts.
- [X] T030 [P] [US2] Implement `tests/architecture/Hoard.Architecture.Tests/DependencyGraphInspector.cs` to combine declared project edges, exact-target resolved assets, packed dependencies, and compiled assembly references; traverse full closures and cycles using T025 ownership, enforcing ARCH-001/ARCH-002/ARCH-003/ARCH-005/ARCH-006/ARCH-008 without an assembly-only or direct-reference shortcut.
- [X] T031 [P] [US2] Implement `tests/architecture/Hoard.Architecture.Tests/PublicSurfaceInspector.cs` with test-only Mono.Cecil for ARCH-004: recursively inspect nested generics, arrays, modifiers, generic constraints, base types/interfaces, attributes, fields, properties, events, and method parameters/returns; reject provider-private/framework/SDK leakage according to the source boundary without executing inspected assemblies.
- [X] T032 [P] [US2] Implement `tests/architecture/Hoard.Architecture.Tests/SliceUsageInspector.cs` with test-only Mono.Cecil to apply ARCH-007/ARCH-008 to type/member/IL use, including nonpublic same-assembly calls and generated async/nested types; validate folder/namespace mappings and permit neutral shared coordination without treating namespace presence alone as a violation.
- [X] T033 [US2] Implement inspection aggregation/error handling in `tests/architecture/Hoard.Architecture.Tests/ArchitectureInspection.cs` and focused failure tests in `InspectionFailureTests.cs`; fail on unresolved references, missing/empty restore/build inputs, unknown non-framework dependencies, duplicate ownership, unmapped slices, and incomplete scans, with distinct sanitized inspection-error versus violation diagnostics and no provider assembly execution.
- [X] T034 [US2] Extend `scripts/validate-foundation.sh` to prepare isolated architecture assemblies, package assets/manifests, declared graph inputs, and permitted/negative pair identities for `tests/architecture/Hoard.Architecture.Tests/Hoard.Architecture.Tests.csproj`; supply the same explicit inspection manifest for real platform/provider outputs, without recursively calling orchestration from tests.
- [X] T035 [US2] Execute and record intended rejection of every ARCH-001 through ARCH-008 negative and its positive counterpart in `tests/architecture/Hoard.Architecture.Tests/ArchitectureRuleTests.cs`, including direct/transitive, unused, packed, recursively leaked, cyclic, and same-assembly cases; keep unexpected passes, wrong-rule failures, and incomplete inspection as acceptance blockers.
- [X] T036 [US2] Run the permitted graph and actual library/fixture package boundary checks through `tests/architecture/Hoard.Architecture.Tests/Hoard.Architecture.Tests.csproj`; reconcile resolved and packed ownership/closure evidence from US1, and document the bounded source/metadata/IL guarantee rather than a malicious-code sandbox or complete reflection-string analysis.

**Checkpoint**: The defined forbidden case set has zero undetected violations
and the permitted graph passes. No rule may be weakened to accommodate a
negative fixture. HTTP startup/lifecycle, store correctness, and native-client
conformance are still outside F-01.

## Phase 5: User Story 3 - Assemble a Small Custom Host (Priority: P2)

**Goal**: Provide public registration-only composition and one self-contained
package-only custom host, with a second independent artifact composition.

**Independent Test**: Inspect metadata/register a provider whose constructor
throws without invoking it; compile two isolated copies of the example using
only local packages. Compare the host edits and unchanged platform/unrelated
provider inputs. Never execute a web host.

### Tests for User Story 3

- [X] T037 [P] [US3] Write failing tests in `tests/unit/Hoard.Foundation.Tests/ModuleRegistrationTests.cs` for builder/collection identity, fluent return identity, exactly appended declaration/type records, duplicate preservation, null service/builder/declaration ArgumentNullExceptions, metadata inspection without a throwing provider constructor, and absence of operational provider registrations, factories, or a second container.
- [X] T038 [P] [US3] Write failing tests in `tests/integration/Hoard.Composition.Tests/CustomHostTests.cs` for package-only baseline/replacement compilation, permitted source edits limited to the artifact PackageReference and registration type/declaration with the corresponding derived lockfile regeneration, unchanged platform/unrelated fixture source hashes, complete isolated assets, and no Build/Run/Start/route-mapping calls or platform-private access in the example.

### Implementation for User Story 3

- [X] T039 [US3] Implement `src/Hoard.Hosting/HoardBuilder.cs` and `HoardModuleRegistration.cs`: "`HoardBuilder` is sealed, exposes a get-only `Services: IServiceCollection`, and is obtained through `AddHoard`"; the registration has "Required immutable properties `Declaration: ModuleDescriptor` and `ProviderType: Type`". Keep these DI/reflection composition objects out of Abstractions and model records as registration data, not selected/ready providers.
- [X] T040 [US3] Implement `src/Hoard.Hosting/HoardServiceCollectionExtensions.cs` and `HoardBuilderExtensions.cs` with the exact public `AddHoard`/`AddModule<TProvider>` signatures and `where TProvider : class, IHoardProvider`; append one registration instance, retain repeats, return the same builder, and throw standard null argument errors without constructor constraints, provider activation, scanning, semantic validation, enablement, or fallback.
- [X] T041 [US3] Create self-contained `examples/CustomHost/CustomHost.csproj` and `Program.cs` with explicit Hosting/Protocol/Metadata/Artifact.One/Identity PackageReferences and complete independent build/dependency settings; use the ASP.NET shared framework only for `WebApplication.CreateBuilder`, `AddHoard`, and four explicit generic registrations, never Build, MapHoard, Run, Start, source imports, ProjectReference, or friend access.
- [X] T042 [US3] Extend `scripts/validate-foundation.sh` to copy/locked-restore/build the example outside the source graph, then build a second copy replacing only Artifact.One's package reference and registration type/declaration with Artifact.Two's; bootstrap and retain the baseline lock before locked replay and explicitly regenerate the copied replacement lock for its changed PackageReference (a derived dependency artifact, not an unrelated source edit); compare source digests and allowed host changes, preserve both output/asset manifests for composition/architecture tests, and never select both artifact fixtures or run either host.
- [X] T043 [US3] Write `examples/CustomHost/README.md` with prerequisites, exact package IDs/versions and local feed/cache configuration, copy/restore/build commands, expected output locations, provider replacement edits, rerun/cleanup steps, and registration-only limitations; distinguish curated already-bundled configuration from custom package reference/registration, rebuild, redeploy, and restart, with trusted-code/no-dynamic-install/no-certification warnings.
- [X] T044 [US3] Run focused `ModuleRegistrationTests` and `CustomHostTests` from `tests/unit/Hoard.Foundation.Tests/Hoard.Foundation.Tests.csproj` and `tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj` on the prepared evidence; verify both example variants pass and the constructor sentinel remains untouched, using only documented public entry points and no live infrastructure.

**Checkpoint**: The example proves public composition usability and a
composition-only fixture swap, not provider functional equivalence, a working
cache, enabled routes, initialized services, or production activation.

## Phase 6: User Story 4 - Understand Compatibility Before Adoption (Priority: P2)

**Goal**: Make declaration, version, dependency-availability, trust, and breaking
change obligations decidable from a written policy with bounded test evidence.

**Independent Test**: Classify every C-01 through C-23 row from the policy;
show the relevant version axis, explicit prerelease gate, or release obligation
that determines the result. Inspect breaking-change fixture evidence without
shipping a runtime evaluator, release pipeline, or general API-diff product.

### Tests for User Story 4

- [X] T045 [P] [US4] Write failing data-driven tests in `tests/unit/Hoard.Foundation.Tests/CompatibilityExamplesTests.cs` for C-01 through C-04, C-07 through C-15, and C-18 through C-23, preserving expected classifications from policy; include exact/inclusive/exclusive bounds, invalid or absent ranges, build-metadata precedence, case-insensitive prerelease labels, independent flags, and enabled versus absent/installed-registered-but-disabled optional targets with no capability claim or silent repair.
- [X] T046 [P] [US4] Write failing release-obligation tests in `tests/unit/Hoard.Foundation.Tests/ContractChangeExamplesTests.cs` for C-05/C-06/C-16/C-17, requiring consumer/implementer source, binary, and behavioral explanations, stable-major versus pre-1.0-minor transitions, updated ranges, and migration/qualification/rollback guidance; reject a patch/minor proposal that merely leaves one consumer compiling.

### Implementation for User Story 4

- [X] T047 [US4] Implement test-only `tests/unit/Hoard.Foundation.Tests/CompatibilityExampleEvaluator.cs` using NuGet.Versioning for normalized comparisons after enforcing the policy's exact/bounded three-part interval subset and separate prerelease flags; classify required and optional selection availability using test inputs only, reject enabled optional conflicts without disablement/substitution, and add no runtime state, parser dependency, or compatibility-success default to platform libraries.
- [X] T048 [US4] Create isolated old/new contract and compiled-consumer examples in `tests/fixtures/compatibility/RequiredMember/` and `BinaryMemberRemoval/`, and extend `scripts/validate-foundation.sh` to capture their intended source/binary break evidence; retain expected negative results as such, never publish these packages or break the real platform graph.
- [X] T049 [US4] Implement bounded release-change examples in `tests/unit/Hoard.Foundation.Tests/ContractChangeExamples.cs` using T048 evidence for required-member and removed-binary-member consequences and an explicit behavioral-obligation change example for C-16; explain policy-derived version/range/migration requirements without claiming an exhaustive automatic binary or semantic compatibility analyzer.
- [X] T050 [US4] Write `docs/PROVIDERS.md` as the public author guide linking the normative compatibility policy and owning APIs: document module/host/abstractions axes, source/binary/behavioral transitions, exact/range/prerelease interpretation, all required migration fields, optional-dependency availability/no-fallback rules, provenance limits, shared invariant ownership, multi-protocol/identity versus single metadata/artifact selections, and named F-02 through F-08 handoffs with no operational provider promise.
- [X] T051 [US4] Execute all 23 named classifications through `tests/unit/Hoard.Foundation.Tests/Hoard.Foundation.Tests.csproj`, verify the breaking source/binary fixtures fail for their intended reasons, and compare results/explanations against `specs/001-provider-contracts/contracts/compatibility.md`; missing cases, guessed classifications, enabled optional conflicts treated as supported, or absent/disabled integrations advertised as available block acceptance.

**Checkpoint**: Compatibility examples are classified and release obligations
are documented. Registration alone still means neither enabled nor compatible;
runtime rejection remains F-02/F-03 and conformance/certification remains F-07.

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integrate all bounded proofs, document actual capabilities, and
prepare honest acceptance evidence without merging, publishing, or deploying.

- [X] T052 Complete `scripts/validate-foundation.sh` as one bounded, non-recursive end-to-end command: locked solution restore, Release build, SDK format/analyzer verification, isolated Core proof, four local platform packs, five independent provider packs/consumers, both custom-host builds, breaking-change inputs, and unit/architecture/composition tests; include both hosts' packed/resolved dependencies in the final scan and fail on any missing, skipped, or unexpectedly passing proof.
- [X] T053 Audit/replay and track applicable `packages.lock.json` files beside every source/test/standalone project under `src/`, `tests/`, and `examples/CustomHost/`, generating any newly introduced fixture locks before their locked acceptance run; ensure isolated copies consume their own settings/locks and just-built Hoard packages, verify SDK formatting for fixture/example projects outside `Hoard.slnx`, and keep feeds, evidence manifests, caches, and binaries untracked.
- [X] T054 Update `README.md`, `docs/DEVELOPMENT.md`, `src/README.md`, `tests/README.md`, `specs/001-provider-contracts/quickstart.md`, and the implementation evidence section of `plan.md` with actual package boundaries, exact available commands/results, dependency license/advisory assessment, supported compile-only examples, later-feature exclusions, and rollback/cleanup; explicitly justify unaffected charter/specification/architecture/ADR/diagrams rather than implying runtime features exist.
- [X] T055 Run `bash scripts/validate-foundation.sh`, `python3 -m unittest discover -s tests/tooling -v`, and `git diff --check`; record exact results and links to all FR/SC, ARCH-001 through ARCH-008 positive/negative, C-01 through C-23, five-provider-package, two-host, constructor-sentinel, and Core-closure evidence in `specs/001-provider-contracts/plan.md`, resolving real failures without bypasses.
- [X] T056 Obtain the required `hoard-architecture-review` of the implemented project/package graph, provider declarations, registration seam, and shared-invariant handoffs, and record findings/resolutions in `specs/001-provider-contracts/plan.md`; significant issues block handoff, and any remediation must rerun affected checks without changing reviewer-owned checklist markers.
- [X] T057 Audit every delivered example/declaration/support statement in `README.md`, `docs/PROVIDERS.md`, `examples/CustomHost/README.md`, and `specs/001-provider-contracts/plan.md` against SC-006 and the traceability table; record remaining limits, actual review/check evidence, and unaffected-document reasons, with no runnable-cache, native-client, production-provider, runtime-validation, certification, release, deployment, or feature-completion claim.

**Checkpoint**: F-01 implementation evidence can be handed to the separate
converge/finalize stages. Checked tasks alone do not complete the feature,
unlock dependencies, authorize a merge, or replace a merged completion
checkpoint.

## Dependencies & Execution Order

### Phase and Story Dependencies

```text
Setup -> Foundational -> US1 package/engine proof -----------+
                    |                  |                   |
                    |                  +-> US3 host/swap ---+-> Polish
                    +-> US2 isolated architecture checks --+   -> acceptance handoff
                    |      (US1 outputs for real scan)      |
                    +-> US4 compatibility examples --------+
```

US1 and US2 are P1; US3 and US4 are P2. Default to that sequential phase
order for one implementer. The common phase is a prerequisite for every story.
US2's isolated inspector/fixture work does not require US1 fixture
implementations, but its real-package completion check T036 requires US1
outputs. US3 requires US1 packages and the public Hosting seam it introduces;
it does not require the compatibility classifier. US4's policy logic and
fixture source are semantically independent of US2/US3; its orchestration
integration waits for their shared-script edits as recorded below. Final
acceptance must inspect both US3 hosts as well as the earlier graphs.

### Task Prerequisites

These are dependency edges, not permission to skip unfinished lower-priority
work. Every story task also inherits the common Phase 2 completion gate.
Lists/ranges in the left column apply to each listed task. A prerequisite
includes its own transitive prerequisites.

| Task(s) | Required predecessor(s) |
| --- | --- |
| T001, T002, T005 | None |
| T003 | T001, T002 |
| T004 | T003 |
| T006 | T004 |
| T007 | T006 |
| T008, T009, T010 | T007 |
| T011 | T008, T009, T010 |
| T012 | T001, T004, T005 |
| T013, T014 | Common phase |
| T015 | T013, T014 |
| T016, T017, T018, T019, T020 | T015 |
| T021 | T015, T012 |
| T022 | T016, T017, T018, T019, T020, T021 |
| T023 | T022 |
| T024 | Common phase |
| T025 | T024 |
| T026, T027, T028, T029, T030, T031, T032 | T025 |
| T033 | T030, T031, T032 |
| T034 | T026, T027, T028, T029, T033, T022 |
| T035 | T034 |
| T036 | T035, T023 |
| T037, T038 | Common phase |
| T039 | T037 |
| T040 | T039 |
| T041 | T040, T023 |
| T042 | T038, T041, T034 |
| T043 | T042 |
| T044 | T037, T038, T040, T042, T043 |
| T045, T046 | Common phase |
| T047 | T045 |
| T048 | T046, T042 |
| T049 | T046, T047, T048 |
| T050 | T049 |
| T051 | T045, T047, T049, T050 |
| T052 | T023, T036, T044, T051 |
| T053 | T052 |
| T054 | T053 |
| T055 | T054 |
| T056 | T055 |
| T057 | T056 |

The shared `scripts/validate-foundation.sh` edits are intentionally serialized:
T012 -> T021 -> T022 -> T034 -> T042 -> T048 -> T052. T048's wait on T042
is a shared-file integration constraint, not a semantic need for a host to
understand compatibility; US4's tests/classifier and breaking fixture source
can be prepared independently, then integrated by the single script owner.
Likewise T034 waits for T022 to avoid simultaneous orchestration edits.

### Within Each Story

Tests precede the contracts/behavior they protect. Fixtures are independent
source inputs, not forbidden references in production libraries. Model/graph
inputs precede inspectors and integration; registration precedes the example.
Test-only evaluation/scanning dependencies must never leak into runtime packs.
Do not run tests needing the final evidence manifest until their preparation
steps have produced the declared complete inputs.

### Parallel Opportunities and Examples

Setup T002 and T005 have no file overlap with T001. In the common phase,
T008/T009/T010 can proceed together after T007; T011 waits for all three.
There is one owner for central project settings, restore lock generation, and
the orchestration script.

| Story | Safe parallel group | Prerequisites / independent outputs |
| --- | --- | --- |
| US1 | T013 + T014 | Common phase; separate package/Core acceptance test files |
| US1 | T016 + T017 + T018 + T019 + T020 | T015; five separate standalone provider directories, no inter-fixture references |
| US2 | T026 + T027 + T028 + T029 | T025; permitted, dependency, leak/coupling, and slice/cycle fixture directories |
| US2 | T030 + T031 + T032 | T025; graph, recursive public-surface, and slice-usage inspectors share only the completed evidence contract |
| US3 | T037 + T038 | Common phase; unit registration versus package-only host acceptance tests |
| US4 | T045 + T046 | Common phase; version/dependency classifications versus breaking-release obligations |

These are task-level examples, not commands to launch a fleet. Subsequent
integrations wait for the prerequisite table and shared-file ownership.

## Requirement and Acceptance Traceability

The table assigns implementation and focused proof tasks, not completed
evidence. Shared setup T001-T012 supports all rows.

| Requirement / outcome | Implementation tasks | Focused proof / review tasks |
| --- | --- | --- |
| FR-001 | T015-T020 | T013, T022, T023 |
| FR-002 | T003, T007-T011, T015, T025, T030, T031, T050 | T006, T024, T035, T036, T056 |
| FR-003 | T003, T021, T030 | T014, T023, T027, T035, T036 |
| FR-004 | T003, T025, T030, T050 | T024, T026-T029, T035, T036, T056 |
| FR-005 | T025, T028-T033 | T024, T035, T036, T052 |
| FR-006 | T039, T040, T041 | T037, T038, T044 |
| FR-007 | T018, T019, T041-T043 | T038, T044, T052 |
| FR-008 | T043, T050, T054 | T057 |
| FR-009 | T040, T041, T043, T050 | T037, T038, T044, T057 |
| FR-010 | T007-T011, T016-T020, T039 | T006, T037, T044, T057 |
| FR-011 | T048-T050 | T046, T051 |
| FR-012 | T008, T047, T049, T050 | T045, T046, T048, T051 |
| FR-013 | T015-T022, T042 | T013, T014, T023, T038, T044 |
| FR-014 | T025-T034 | T024, T035, T036, T052, T055 |
| FR-015 | T015, T040, T050, T054 | T056, T057 |
| FR-016 | T016-T020, T041, T043, T050, T054 | T057 |
| FR-017 | T007, T015, T050 | T056, T057 |
| SC-001 | T015-T022 | T013, T014, T023 |
| SC-002 | T018, T019, T042 | T038, T044 |
| SC-003 | T025-T034 | T024, T035, T036, T052 |
| SC-004 | T039-T043 | T037, T038, T044 |
| SC-005 | T047-T050 | T045, T046, T048, T051 |
| SC-006 | T043, T050, T054 | T057 |

**Rule coverage**: ARCH-001/ARCH-002/ARCH-003 inputs are T027;
ARCH-004/ARCH-005/ARCH-008 inputs are T028;
ARCH-006/ARCH-007 inputs are T029. T026 supplies permitted counterparts;
T030-T033 implement inspection/completeness; T024/T035/T036/T052 prove results.

**Case coverage**: T045/T047 cover C-01-C-04, C-07-C-15, and C-18-C-23;
T046/T048/T049 cover C-05, C-06, C-16, and C-17. T051 requires all 23 results,
including the approved optional-dependency rule; no selection/runtime evaluator
or capability advertisement is introduced by these examples.

## Implementation Strategy

### MVP First (User Story 1)

1. Complete setup and foundational declarations, including their failing-first
   contract checks.
2. Deliver US1's independent four-family/five-package and Core-only proofs.
3. Stop at its bounded checkpoint and inspect actual compiled/package evidence.
   This is an initial increment, not a deployable demo or complete F-01.

### Incremental Delivery

1. Add US2's isolated forbidden/permitted checks and real-package scan.
2. Add US3's registration API, documented host, and artifact replacement proof.
3. Add US4's full policy classification/release-change examples.
4. Integrate the final orchestrator, locked restores, formatting, documentation,
   acceptance evidence, and architecture review before handing off to converge.

Within an authorized implementation stage, commit coherent tasks/groups and
push immediately after each commit. Do not use this strategy to bypass the
one-stage-per-invocation driver, analysis, or reviewer-owned gates.

### Parallel Work Strategy

After shared declarations, separate contributors may prepare the marked test,
provider, inspector, and compatibility inputs. Serialize changes to shared
settings, the solution, locks, and orchestration; merge prepared inputs only
after their declared prerequisites. Default to one implementer; no workflow
engine or automatic agent fleet is requested.

## Notes

- No task adds production SQLite/filesystem/NuGet/identity providers, HTTP
  endpoints, UI, CI/CD, runtime assembly loading, live provider swaps, cloud
  resources, or package publication.
- F-02 owns registry/lifecycle/activation/readiness/shutdown; F-03 owns
  configuration/secrets/runtime compatibility/category/cardinality validation;
  F-04 discovery; F-05 metadata operations; F-06 artifact operations; F-07
  conformance/certification; F-08 identity normalization/scheme composition.
- Shared identity/auth partitioning, freshness, safe upstream access, verified
  publication, bounded streaming/cancellation, single-flight, safe GC,
  authorization, and telemetry remain mandatory later-feature invariants,
  never discretionary provider behavior.
- Keep reviewer-owned checklist markers unchanged. Analysis was read-only;
  convergence remains a separate invocation, and significant analysis findings need separate
  remediation authorization and fresh analysis.
- Missing SDKs/packages or failed checks block the affected proof; never
  substitute success-shaped defaults, skip missing inputs, or claim fixtures
  are functional providers. Record compatibility changes and migration needs.
- No infrastructure plan/apply, release, deployment, or merge is authorized.
