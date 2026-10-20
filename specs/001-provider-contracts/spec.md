# Feature Specification: Platform Package Boundaries and Provider Contracts

**Feature Branch**: `feature/001-provider-contracts`

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "Specify an open extensibility foundation for Hoard that allows independent package-manager, metadata, artifact storage and identity providers without modifying the caching engine. Include versioned contracts, clean package boundaries, a small custom-host experience, extensibility constraints and acceptance checks that prevent concrete-provider coupling."

**Backlog**: [F-01](../../docs/HOARD_SPECKIT_MASTER_BACKLOG.md#foundation-f-01)

## Clarifications

### Session 2026-10-20

No critical ambiguities detected worth formal clarification. Zero questions
were asked or answered; no requirements or scope decisions changed.

The review found sufficient coverage of functional scope, domain/declaration
concepts, author journeys, applicable quality attributes, integration boundaries,
failure cases, constraints/tradeoffs, terminology, completion signals, and
placeholders. Runtime performance, scale, recovery, UI states, and operational
provider behavior are explicitly outside this compile-only foundation, not
unspecified F-01 acceptance obligations. Exact public signatures, dependency
versions, build layout, and commands remain planning decisions under the
existing requirements. No consequential product decision blocks planning.

### Approved Follow-up 2026-10-20

The user approved the delegated checklist review's recommendation for RQ-01.
For an enabled module, an enabled optional dependency must satisfy its declared
version range and explicit prerelease policy or the composition is unsupported;
there is no automatic disablement or substitution to make it pass. An absent
or installed/registered-but-disabled optional target is unavailable and provides
no integration or capability claim. This clarifies FR-012 and its acceptance
examples only; runtime enforcement remains F-02/F-03 work. The follow-up does
not rerun or advance a scheduled Spec Kit stage or authorize implementation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extend Hoard Without Changing Its Engine (Priority: P1)

As an independent provider author, I can develop and distribute a provider for
one of Hoard's four provider families using its published contracts, without
editing the caching engine or depending on another concrete provider.

**Why this priority**: Independent extension is the feature's primary promise.
Without it, provider choice would require maintaining a fork of Hoard.

**Independent Test**: Compile a separately maintained fixture provider for each
family using only permitted public dependencies, with no internal-source access
or real external service. Verify the engine independently with every concrete
provider excluded. This covers FR-001 through FR-005 and FR-013.

**Acceptance Scenarios**:

1. **Given** the public contracts and no concrete providers, **When** a maintainer
   builds the caching engine, **Then** it succeeds without restoring or loading
   any concrete protocol, metadata, artifact storage, or identity provider.
2. **Given** a provider author working outside the platform's source projects,
   **When** they implement a fixture for any of the four provider families,
   **Then** it compiles against public contracts without privileged access,
   copying platform internals, or modifying engine source.
3. **Given** two independently built fixture implementations of the same family,
   **When** a host author changes the selected package and registration,
   **Then** both compositions compile without changing the engine or unrelated
   provider source; no functional equivalence of unfinished providers is claimed.

---

### User Story 2 - Prevent Accidental Provider Coupling (Priority: P1)

As a platform maintainer, I receive a failing architecture check when a change
introduces a forbidden dependency, so extensibility does not erode as features
and contributors are added.

**Why this priority**: Written boundaries alone cannot protect independently
released providers or prevent implementation details from spreading.

**Independent Test**: Run boundary checks on a permitted reference composition,
then introduce each prohibited reference in isolated negative fixtures and
confirm rejection identifies the source, target, and violated rule. This covers
FR-002 through FR-005 and FR-014.

**Acceptance Scenarios**:

1. **Given** the allowed package graph below, **When** boundary checks inspect
   the reference composition, **Then** the checks pass.
2. **Given** an engine dependency on a concrete provider or provider-specific
   persistence framework, **When** boundary checks run, **Then** they fail even
   if that dependency arrives through an intermediate package or public type.
3. **Given** a protocol referring to a concrete storage or persistence provider,
   an application slice exposing a provider-private type, or a slice accessing
   another slice's internal handler, **When** boundary checks run, **Then** each
   change fails with the offending dependency identified.
4. **Given** a dependency cycle or a provider-specific type added to a public
   shared contract, **When** boundary checks run, **Then** the change fails
   rather than becoming an accepted extension pattern.

---

### User Story 3 - Assemble a Small Custom Host (Priority: P2)

As a custom-distribution author, I can follow one self-contained example to
reference provider packages and explicitly register them through public
composition contracts, without copying the curated host or engine.

**Why this priority**: A small, working composition example proves that the
extension boundary is usable rather than merely an internal convention.

**Independent Test**: Compile a minimal custom-host example using public
platform entry points and fixture providers, without private APIs or live
infrastructure. This is a composition proof, not a runnable cache acceptance
test. This covers FR-006 through FR-009 and FR-016.

**Acceptance Scenarios**:

1. **Given** an author with the documented prerequisites and fixture packages,
   **When** they follow the custom-host example, **Then** the example compiles
   with explicit provider references and registrations and no platform-source
   edits.
2. **Given** that example, **When** the author replaces a fixture provider with
   an independently built compatible fixture of the same family, **Then** only
   the example's provider reference and registration need change.
3. **Given** a provider absent from the host's build, **When** an author reads
   the installation instructions, **Then** the instructions require adding the
   package, rebuilding, redeploying, and restarting, and do not suggest that
   configuration downloads or dynamically installs it.

---

### User Story 4 - Understand Compatibility Before Adoption (Priority: P2)

As a provider author or distribution maintainer, I can identify a provider's
public contract compatibility and release obligations before adopting or
upgrading it.

**Why this priority**: Independent distribution is only useful when compatibility
and code-trust limits are explicit.

**Independent Test**: Review sample provider declarations and classify compatible,
incompatible, and prerelease combinations using the documented policy alone;
compare a breaking contract-change fixture with that policy. This covers
FR-010 through FR-012, FR-015, and FR-017.

**Acceptance Scenarios**:

1. **Given** a provider declaration, **When** a maintainer inspects it,
   **Then** its stable identity, category, version, supported host and
   abstractions ranges, dependencies, capabilities, and support/provenance
   information are available without constructing provider services.
2. **Given** a supported contract release, **When** an author proposes a change
   that requires an existing provider to change source or behavior, **Then**
   the compatibility policy classifies it as breaking and requires an explicit
   version transition and migration guidance.
3. **Given** an incompatible or undeclared compatibility range, **When** a
   maintainer evaluates a composition, **Then** it is not represented as
   supported and no silent fallback is described; runtime enforcement belongs
   to the subsequent lifecycle and activation features.
4. **Given** the family responsibility descriptions, **When** a maintainer
   reviews their ownership boundaries, **Then** they distinguish multiple
   protocol and identity schemes from single authoritative metadata and
   artifact selections, and reserve shared cache correctness and authorization
   decisions to centralized services.
5. **Given** an enabled module with an optional dependency, **When** a maintainer
   classifies a composition, **Then** an enabled target outside its range or
   without required prerelease opt-in makes the composition unsupported, while
   an absent or installed-but-disabled target is unavailable without a claim
   to that integration or capability; incompatibility is not silently repaired.

### Edge Cases

- A provider transitively brings its database or storage SDK into the engine's
  dependency closure: reject the dependency, not just a direct reference.
- An otherwise neutral contract exposes a database context, query object,
  vendor SDK result, or concrete provider type: reject that public surface.
- A shared contract gains a new required member or tighter behavioral guarantee:
  classify it as breaking for existing implementers, even if consumers compile.
- A prerelease provider or host falls outside the declared range: require
  explicit prerelease compatibility; do not infer support from a nearby release.
- An optional dependency is enabled but incompatible: classify the composition
  as unsupported, not implicitly disable the integration. A target that is
  merely installed/registered but disabled is unavailable, not an active
  dependency or an advertised integration.
- Two modules declare the same stable ID, omit compatibility information, or
  declare mutually dependent modules: the contract must represent these inputs
  for later validation; F-01 does not implement the startup validator.
- A fixture provider compiles but does not fetch packages, persist metadata, or
  verify bytes: describe it only as contract/composition evidence, never as a
  supported production provider.
- An artifact store cannot use filesystem rename or a metadata store cannot
  share a transaction with it: the family boundaries must not imply those
  guarantees or permit bypassing centralized publication invariants.
- An identity provider authenticates a caller: it must not confer permissions
  outside Hoard's centralized authorization boundary.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The platform MUST define publicly consumable extension contracts
  for package protocols, metadata persistence, artifact storage, and identity,
  allowing independently packaged implementations of each family.
- **FR-002**: Each public contract MUST have one documented owning package and
  purpose. Shared abstractions MUST have no dependency on concrete providers,
  provider SDKs, persistence frameworks, or host-specific HTTP integration.
- **FR-003**: The caching engine MUST build and be testable against shared
  abstractions without any concrete provider, database context, persistence
  framework, or provider-specific SDK in its dependency closure.
- **FR-004**: The documented package graph MUST be acyclic and distinguish the
  concrete host, hosting/composition, management slices, protocol slices,
  shared engine, public abstractions, and concrete provider families. The
  allowed directions MUST follow the ownership table below.
- **FR-005**: Public contracts and management/protocol slices MUST NOT expose
  provider-private persistence, migration, or SDK types. Providers MUST NOT
  depend on unrelated concrete providers, and slices MUST use shared public
  contracts rather than another slice's internal handler.
- **FR-006**: Public composition contracts MUST let a custom host explicitly
  register a referenced provider without private APIs, engine edits, or
  a required orchestration framework beyond the platform's existing baseline.
- **FR-007**: The foundation MUST include one minimal, self-contained,
  compile-checked custom-host example using public contracts and fixture
  providers. It MUST document prerequisites, package references, registration,
  and how to replace a fixture without changing platform source.
- **FR-008**: Documentation MUST distinguish a curated distribution's
  configuration of already bundled providers from a custom distribution's
  package references, rebuild, redeployment, and restart.
- **FR-009**: The extension model MUST be explicit build-time composition of
  trusted in-process code. It MUST NOT promise arbitrary assembly loading,
  runtime downloads, hot installation/replacement, sandboxing, or a marketplace.
- **FR-010**: A public module declaration MUST describe a stable unique ID,
  category, semantic module version, supported host and abstractions version
  ranges, required and optional dependencies, declared capabilities,
  sanitized configuration requirements, applicable endpoint and health
  responsibilities, and provenance/support status. Inspecting this declaration
  MUST NOT require activation, external connections, or secret values.
- **FR-011**: A written public compatibility policy MUST distinguish module,
  host, and abstractions versions; classify source, binary, and behavioral
  compatibility for consumers and implementers; and require a major version
  change for breaking stable contracts. Before version 1.0, breaking changes
  MUST require an explicit minor-version transition and updated declared ranges,
  rather than an assumption that all pre-1.0 releases interoperate.
- **FR-012**: The policy MUST define how supported ranges and prereleases are
  interpreted, require explicit prerelease opt-in, and require migration
  guidance for breaking changes. Unsupported, missing, or incompatible
  declarations MUST NOT be described as supported or silently substituted.
  For each enabled module, enabled optional dependencies MUST satisfy their
  declared version ranges and prerelease flags or the composition MUST be
  classified as unsupported, without automatic disablement or substitution.
  Absent or installed/registered-but-disabled optional targets MUST be treated
  as unavailable and MUST NOT confer integration or capability support.
  Runtime enforcement is deferred to F-02/F-03.
- **FR-013**: Acceptance evidence MUST include independently compiled fixture
  providers covering all four families, plus an engine-only build without
  concrete providers. Fixtures MUST use permitted public dependencies only;
  at least one family MUST have two independent fixture implementations.
- **FR-014**: Automated architecture checks MUST accept permitted dependencies
  and reject direct or transitive forbidden dependencies, provider-type leakage,
  package cycles, and cross-slice internal coupling. Isolated negative fixtures
  MUST demonstrate rejection for each rule, with the offending source, target,
  and rule identified.
- **FR-015**: Provider contracts MUST preserve shared ownership of cache identity
  and authentication partitioning, freshness, safe upstream access, verified
  publication, bounded streaming and cancellation, single-flight coordination,
  reference-safe deletion, authorization, and telemetry. They MUST NOT grant a
  provider permission to bypass or independently redefine those guarantees.
  Detailed operations and guarantees remain owned by their subsequent features.
- **FR-016**: Foundation examples and documentation MUST state that successful
  compilation proves contract usability only. They MUST NOT advertise a
  runnable cache, complete protocol, real persistence/storage/identity provider,
  production activation, or certification not delivered by this feature.
- **FR-017**: Family responsibilities MUST distinguish multiple protocol and
  identity implementations from the initial single authoritative metadata
  provider and single authoritative artifact provider. Authentication MUST
  remain distinct from centralized authorization; category-specific selection,
  validation, and authentication behavior are not implemented here.

### Contract Ownership and Dependency Boundary

These names and boundaries are existing product constraints from the
[architecture](../../docs/ARCHITECTURE.md) and
[ADR-0001](../../docs/adr/0001-modular-provider-architecture.md), not new API
signatures or an implementation plan.

| Boundary | Required ownership and permitted direction |
| --- | --- |
| `Hoard.Abstractions` | Provider-neutral public contracts and descriptor vocabulary; only deliberately minimal common dependencies, no concrete provider or hosting implementation. |
| `Hoard.Core` | Shared cache invariants; depends on abstractions and common framework facilities, never concrete providers or their SDKs. |
| `Hoard.Hosting` | Public composition boundary and eventual lifecycle/HTTP integration; may use Abstractions, Core, and host framework facilities. |
| `Hoard.Application` | Management feature slices; may use Core, Abstractions, and approved public Hosting contracts, not provider-private types. |
| `Hoard.Protocols.*` | Protocol-specific translation and feature slices; may use Core, Abstractions, and approved public Hosting contracts, not other concrete provider families. |
| `Hoard.Persistence.*` | Private metadata implementations, schemas, and migrations; implement Abstractions and keep persistence frameworks private. |
| `Hoard.Storage.*` | Private artifact implementations; implement Abstractions and keep storage SDK details private. |
| `Hoard.Identity.*` | Identity implementations and principal mapping; use Abstractions and approved public Hosting contracts, not private authorization shortcuts. |
| `Hoard.Host` | Concrete distribution assembly; references Hosting, Application, and explicitly selected provider packages. |
| Management console | Consumes management capabilities through the eventual public service boundary; no direct provider/package coupling and no UI implementation in F-01. |

### Key Entities *(include if feature involves data)*

- **Provider Contract**: A public, versioned agreement owned by a named boundary,
  identifying family responsibilities and compatibility obligations; not a
  concrete implementation or database schema.
- **Module Declaration**: Descriptive identity, category, compatibility,
  dependency, capability, configuration, health, and provenance information
  associated with a distributable provider.
- **Compatibility Declaration**: Supported host/abstractions ranges and
  prerelease policy, distinct from the provider's own release version.
- **Host Composition**: Explicit platform and provider references and
  registrations forming one curated or custom distribution.
- **Architecture Rule**: An allowed or forbidden relationship between package
  boundaries or public types, with a corresponding acceptance check.
- **Fixture Provider**: A non-production independent implementation used only
  to prove public-contract consumption and composition.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Authors demonstrate independent extensions in all four provider
  families without modifying platform source or accessing private contracts.
- **SC-002**: Maintainers can replace either of two independent fixtures in one
  family by changing host composition alone, with zero engine or unrelated
  provider source changes.
- **SC-003**: Every forbidden relationship named in FR-014 is detected by an
  isolated negative acceptance case, while the permitted reference composition
  passes; there are zero undetected violations in that defined case set.
- **SC-004**: A custom-distribution author can complete the single documented
  composition example without undocumented steps, private entry points, copied
  engine code, or a live external service; its acceptance check succeeds.
- **SC-005**: Maintainers can classify every case in a documented compatibility
  example set covering stable-compatible, stable-breaking, pre-1.0-breaking,
  missing-range, out-of-range, and prerelease combinations without guessing
  implicit support.
- **SC-006**: Every delivered example and support statement explicitly
  distinguishes foundation evidence from operational capability; no fixture is
  presented as a production-ready provider or functioning package cache.

## Assumptions

- The ratified [constitution](../../.specify/memory/constitution.md) and merged
  architecture baseline supply the product, trust, and dependency constraints.
  F-01 has no earlier feature dependency.
- Primary users of this foundation are provider authors, host authors, and
  maintainers. A runnable end-user cache and its performance targets belong to
  later features; this stage creates requirements only.
- F-01 establishes family extension seams, descriptive contracts, compatibility
  policy, boundary checks, and a compile-only custom-host proof. It does not
  pre-design the detailed repository, transaction, artifact, or identity
  operations that subsequent family specifications must establish.
- F-02 owns registry/lifecycle ordering, activation, readiness, and shutdown;
  F-03 owns configuration precedence, secret resolution, selection validation,
  and runtime compatibility enforcement; F-04 owns management discovery;
  F-05/F-06 own detailed metadata/artifact semantics; F-07 owns reusable
  conformance/certification; F-08 owns detailed identity scheme composition.
  Those are later consumers, not prerequisites or capabilities claimed here.
- Fixtures can exercise declaration and registration boundaries without
  implementing production cache behavior. The acceptance proofs introduced
  by F-01 do not replace later provider conformance or native-client checks.
- Exact public signatures, dependency versions, build layout, and commands are
  planning decisions constrained by these requirements and the constitution.
  New APIs or packages are not assumed to exist today.
- No cloud account, external database, live upstream registry, user interface,
  product deployment pipeline, or infrastructure application is needed to
  evaluate this foundation.
