# Tasks: Module Capabilities and Management Discovery

**Input**: Design documents from `specs/004-module-discovery/` (F-04).
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md),
[research.md](research.md), [data-model.md](data-model.md),
[Hosting integration](contracts/hosting-api.md),
[HTTP contract](contracts/discovery-api.md),
[OpenAPI](contracts/openapi.json),
[presentation contract](contracts/presentation.md),
[acceptance matrix](contracts/acceptance.md) and [quickstart.md](quickstart.md).

**Status**: Task generation only. All 78 tasks are unchecked; no new API,
endpoint, project, lockfile, runner, listener or consumer is implemented here.
The built-in requirements checklist remains 16/16 and the separately requested
assisted review of [discovery](checklists/discovery.md) and
[management](checklists/management.md) remains 20/20 each. Task generation
changes neither their reviewer-owned approval nor any specification/design
bytes. Next is separately invoked read-only analysis, not implementation.

**Tests**: Explicitly required by FR-022, SC-001..SC-008, each story's independent
test and D01..D40. Write paired permitted/rejected checks first, record their
intended red result, implement, then record green. A missing-API compile failure
can establish an initial contract red result, not runtime rejection, coherent
publication, access enforcement or resource release. Runtime negatives must
exercise the actual mechanism and fail without it. Never skip missing evidence,
use the projection under test as its own oracle or infer support from a test
count. Reuse existing test infrastructure without weakening earlier proofs.

**Organization**: Shared setup and frozen/publication primitives precede five
story phases in specification priority order, then cross-cutting acceptance.
US1 is an in-process inventory MVP, not an exposed HTTP service. US2 adds
operation truth; US3 introduces both protected HTTP slices together. US4 can
exercise serialized examples independently of a listener; US5 stresses the
same authorities and proves restart/distribution journeys. These are testable
increments, not permission to stop an implementation invocation between them.

## Format: `[ID] [P?] [Story] Description`

- Every task has an unchecked checkbox, sequential ID and exact
  repository-relative destination paths. Only story tasks carry `[US1]`..`[US5]`.
- `[P]` identifies file-disjoint ready groups described below, after their
  listed prerequisites. It does not authorize agents or a workflow engine.
  The explicit prerequisite table, not numeric adjacency, determines readiness.
- FR/SC references use the specification; D references use the acceptance
  contract, whose scenario/edge mappings remain authoritative. Quoted
  invariants and numeric limits are requirements, not implementation choices.
- Destination filenames describe cohesive responsibilities; use existing
  helpers before creating another mechanism. Record any equivalent grouping
  in implementation evidence without changing contract meaning.

## Path Conventions

Production changes are additive Hosting discovery/publication integration and
Application management slices. Application may gain its already approved
Hosting/ASP.NET Core references; Core remains provider-free and Abstractions
BCL-only. Keep ModuleDescriptor, provider markers, IHoardModule,
IHoardLifecycle, existing snapshot constructors and configured composition/
build/map/start/stop signatures unchanged. Metadata/artifact providers remain
Abstractions-only. Never add a second lifecycle/validation authority, service
container, health scheduler, secret resolver or general capability rules engine.

Extend existing composition/architecture projects. New package-only consumers
and the JSON-only consumer are standalone fixtures, not product projects or
source-reference shortcuts. Use current framework dependencies; add no third-
party runtime/SDK/frontend package, production identity, provider, curated Host,
Next.js scaffold, public listener or infrastructure. Only dedicated D20/D21
adapter cases may open private ephemeral loopback Kestrel/TLS listeners.

Prepared packages, manifests, baseline assemblies and invented sensitive
fixtures belong to a resolved owner-private temporary workspace, never Git.
Evidence carries safe IDs/hashes, not private paths or raw payloads. Bash owns
prerequisites and narrow cleanup; Python standard-library helpers own bounded
subprocesses, copying/hashes and explicit evidence errors. Tests consume
prepared proof and never recursively invoke an orchestrator. Preserve existing
default runner behavior and exact required suite/scan inventories. Generate
locks only for intentional manifest changes, review them, then independently
replay default locked acceptance with no lock mutation.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare instrumentation, fail-closed evidence collection and truly
pre-F-04 binaries before modifying platform manifests or behavior.

- [ ] T001 [P] Add `tests/integration/Hoard.Composition.Tests/DiscoveryTestHarness.cs` using existing lifecycle/time/configuration fixtures: immutable complete/partial catalogs, all provider families, included-unregistered and disabled options, independent route/service invocation and constructor/validator/secret/probe/worker/connection counters, safe output/log/telemetry capture, explicit fixture identities and publication/cancellation barriers; release and observe every held activity with finite teardown and no developer credentials.
- [ ] T002 [P] Write failing `tests/tooling/test_discovery_evidence.py` for missing/empty/duplicate/stale case, suite and package-journey inventories, nonzero/timed-out subprocesses, nonlocal packages/hash drift, rebuilt retained binaries, incomplete performance samples, lock mutation and unsafe workspace cleanup; use synthetic temporary inputs rather than recursively executing acceptance.
- [ ] T003 Introduce `scripts/validate-discovery.sh` and `scripts/discovery_evidence.py` following the existing evidence helpers: explicit prerequisites, bounded subprocesses, private workspace, red/green capture, safe failures and intentional `--update-locks`; incomplete proof inventories must fail until later tasks supply them, and no public/product listener or real secret may be used.
- [ ] T004 [P] Add baseline source recipes and isolated locks under `tests/fixtures/discovery/RetainedLifecycle/RetainedLifecycle.csproj`, `Program.cs`, `Baseline/packages.lock.json`, `tests/fixtures/discovery/RetainedConfiguration/RetainedConfiguration.csproj`, `Program.cs`, `Baseline/packages.lock.json` and `tests/fixtures/discovery/LegacyOptions/Baseline/packages.lock.json`; identify immutable merged pre-F-04 revisions, compile lifecycle/configuration consumers and the existing Abstractions-only option-bearing provider into the private workspace, freeze source/binary/dependency hashes, and retain the F-01 registration binary proof without recompiling retained outputs against new platform code (D38).

**Checkpoint**: An incomplete discovery runner fails explicitly; retained
binary provenance precedes all new platform dependency or behavior changes.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish additive immutable metadata, safe records and the sole
coordinator's internal publication. Every story waits for T012.

- [ ] T005 [P] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryContractTests.cs` for immutable catalog/options, duplicate/conflicting/orphan identities and associations, complete versus partial knowledge, defensive copies, invalid limits before activation, opt-in timing before configuration/service snapshots and unchanged discovery-free F-01/F-02/F-03 contracts; pair every structural rejection with a valid counterpart without introducing active option validation (D02, D06, D38).
- [ ] T006 Add the approved references in `src/Hoard.Application/Hoard.Application.csproj` and `tests/integration/Hoard.Composition.Tests/Hoard.Composition.Tests.csproj`, preserving current package versions and solution layout; Application must reference Hosting and `Microsoft.AspNetCore.App`, composition tests must reference Application, and packed/non-web framework propagation remains a later mandatory proof, not an assumed transitive success (D38).
- [ ] T007 Define immutable catalog/options/safe model records in `src/Hoard.Hosting/Discovery/HoardDiscoveryCatalog.cs`, `HoardDiscoveryOptions.cs` and `HoardDiscoveryObservation.cs`: distribution identity is "Explicit public host identity; not a filesystem path or arbitrary executable metadata"; completeness is "`complete` or `partial`; only complete records establish absence"; inclusion records are "Explicit positive records for included packages, including unregistered ones"; support records use "Exact capability ID/version, operation ID, owner IDs and tested evidence IDs/scope". Preserve all model fields and enforce 256 modules, 64 contributions/module and 4,096 total, 256 option fields/module and 4,096 total, 32 bindings/dependencies/owners/evidence IDs per contribution, 100 diagnostics plus omitted count, canonical IDs at most 128 characters, labels 160, descriptions 512, corrective templates 256, default two-second deadline and 4 MiB body; host deadlines must be positive finite and static bounds checked before copying/enumeration (D06, D35).
- [ ] T008 Define `src/Hoard.Hosting/Discovery/DiscoveryPublicationPolicy.cs`, `DiscoveryReason.cs`, `IHoardDiscoverySource.cs` and `HoardDiscoveryReadResult.cs` with closed reason/action templates, approved affected identities, safe phase and random correlation: public text is "Explicit host-approved literals keyed to known declaration identities; no runtime/configuration values"; provenance is "Bounded declared classification plus approved public publisher, not certification or raw URLs"; module reasons are "Closed safe reasons for unavailable/unknown public metadata or state"; failures are never partial success or exception-bearing records. Unknown diagnostic codes become `observation-unavailable`; order bounded reasons deterministically and retain omitted count without reflecting unknown input identities (D03, D22..D24, D40).
- [ ] T009 [P] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryPublicationTests.cs` with deterministic barriers for initial registered publication, phase/assessment/admission/worker/stop/cleanup/late-diagnostic transitions, monotonically advancing revisions, nullable pre-assessment time and exact lifecycle/catalog ownership; readers must not acquire the coordinator lock, call Snapshot/AssessReadinessAsync, construct modules or run callbacks (D14..D16, D31).
- [ ] T010 Implement internal `src/Hoard.Hosting/Discovery/DiscoveryLifecyclePublication.cs` and integrate `src/Hoard.Hosting/Lifecycle/HoardLifecycleCoordinator.cs` under its existing Gate: publish one bounded immutable reference after every discoverable construction/service/build/mapping/initialization/assessment/worker/admission/stop/drain/cleanup/terminal/late-safe-diagnostic transition. Include composition/lifecycle identity, positive revision, publication/assessment times, module/host phase and readiness; use acquire/release publication with no callbacks, serialization or I/O under Gate and no sequencing, ownership, stop-result or public snapshot/interface change (D14..D16, D31).
- [ ] T011 Implement `src/Hoard.Hosting/Discovery/HoardDiscoveryExtensions.cs` and additive storage in `src/Hoard.Hosting/HoardBuilder.cs` plus `src/Hoard.Hosting/Lifecycle/HoardServiceCompositionExtensions.cs`: AddHoardDiscovery freezes catalog/options before EvaluateConfigurationAsync or legacy validation/compose snapshots, retaining same-root discovery inputs for T019's source-factory wiring. Catalog inputs are "immutable arrays/closed records, not lazy callbacks"; later mutation rejects or cannot change that lifecycle. Validate only discovery structure/associations, never patch consumed proofs, build another container or give the source private options, IConfiguration, secret handles or file readers (D05, D06, D38).
- [ ] T012 Run T005/T009 contract/publication checks through `scripts/discovery_evidence.py` and T002 tooling regressions, recording intended red-to-green and unchanged opt-out behavior; verify invalid static metadata fails before activation, initial publication exists, all held work is observed and incomplete full-acceptance mode still fails.

**Checkpoint**: Shared metadata/publication is usable without an HTTP surface;
the existing lifecycle remains the sole activation/readiness/resource owner.

## Phase 3: User Story 1 - Inspect the Actual Distribution and Running Selection (Priority: P1)

**Goal**: Inspect established inventory knowledge and fixed selection without
constructing disabled or unregistered providers.

**Independent Test**: Inspect safe in-process observations for complete and
partial fixture distributions across all families; compare inclusion,
registration, selected roles and lifecycle observations with independent
records/counters. Covers US1-1..4, FR-001..004/008/021 and D01..D07.

### Tests for User Story 1

- [ ] T013 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryInventoryTests.cs` for known included/unregistered, registered/disabled, enabled and absent versus unknown entries, all families, selected metadata/artifact authorities and multiple protocol/identity selections, approved compatibility/provenance and unknown publisher/support; never enumerate binaries or invent an absent installed entry (D01..D04, D07).
- [ ] T014 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryDisabledTests.cs` pairing disabled missing/invalid operational options, inaccessible invented secret references and incompatible active ranges with enabled counterparts; inspection must produce zero option checks, secret reads, constructors, readiness probes, routes/workers/connections while inherited structural validation still applies (D05, D06).
- [ ] T015 [P] [US1] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryCatalogTests.cs` for conflicting category/version, duplicate/orphan bindings/public fields, post-freeze mutation, a registered declaration as positive knowledge but not completeness, and exact collection/text boundaries; pair safe public metadata with suppressed unapproved metadata (D02, D03, D06, D22, D23, D35).

### Implementation for User Story 1

- [ ] T016 [US1] Implement `src/Hoard.Hosting/Discovery/DiscoveryInventoryProjector.cs` from frozen inclusion/registrations/selection and one publication: `id/category/version` are "Safe known declaration identity; no CLR type/assembly path"; inclusion/registration/enablement retain "Independent positive knowledge, registration and fixed selection"; compatibility is "Declared host/abstractions ranges and prerelease flags; never a fresh validation result"; selected roles are "Metadata/artifact authority or selected identity, derived from validated fixed selection". Included-unregistered is registered/enabled false and unknown with missing-registration; disabled readiness is disabled, never unhealthy or newly validated (FR-001..004, D01..D07).
- [ ] T017 [US1] Implement `src/Hoard.Hosting/Discovery/DiscoveryOptionProjector.cs` with "Safe descriptive fields only, not operational settings or winning sources": "Secret fields have no default/example/allowed values"; safe numeric constraints and known field IDs/types/required/secret flags come from matching metadata, while descriptions/ordinary defaults/allowed literals require separate host approval. Enforce OpenAPI constraints of lengths 0..16,384, integer bound text at most 20 characters, at most 64 allowed values of at most 160 characters, public defaults/descriptions at most 512 and secret/type agreement; emit metadata-suppressed for unapproved material, with no configured values, winning sources, raw option contracts or secret locators (FR-013, D05, D22, D23, D35).
- [ ] T018 [US1] Implement `src/Hoard.Hosting/Discovery/HoardDiscoverySource.cs` with internally owned singleton construction: Capture takes one volatile immutable publication reference and projects the frozen catalog/selection with cancellation and finite budget checks; report missing/inconsistent authority explicitly, never refresh/probe providers or cache a prior healthy result. Until operation evidence is implemented, declarations remain unverified/non-usable rather than fabricated supported capabilities (FR-008..010/021, D05, D07, D33).
- [ ] T019 [US1] Complete same-root source-factory registration in `src/Hoard.Hosting/Discovery/HoardDiscoveryExtensions.cs` before evaluation/service snapshots and source binding during supervised composition in `src/Hoard.Hosting/Lifecycle/HoardServiceCompositionExtensions.cs`; extend `tests/integration/Hoard.Composition.Tests/DiscoveryInventoryTests.cs` to capture from actual legacy and configured fixture compositions, retaining exact source/catalog/lifecycle identity and proving no disabled resource or secret activity. Never add registrations after configuration evaluation or host build (D01..D07).
- [ ] T020 [US1] Extend the inventory section of `scripts/discovery_evidence.py` and run T013..T015 plus actual-composition assertions, recording D01..D07 red/green, selected-role comparisons and zero disabled events; keep full mode incomplete and record that this MVP exposes no HTTP route, production provider or action.

**Checkpoint**: US1 is a truthful, independently inspectable inventory MVP.
It is not permission to expose an unprotected endpoint or stop implementation.

## Phase 4: User Story 2 - Know What Is Supported and Usable Now (Priority: P1)

**Goal**: Derive operation-scoped support/availability from actual composition
and the captured authority observation, not declarations or aggregate health.

**Independent Test**: Pair actual owned route and effective service operations
with removed/shadowed/wrong-owner counterparts; exercise dependencies and
readiness/stop changes using independent invocation/callback counters.
Covers US2-1..5, FR-005..010/015/022 and D07..D17.

### Tests for User Story 2

- [ ] T021 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryRouteBindingTests.cs` for exact sealed owner/responsibility/method evidence versus declared-only, missing/wrong-method/wrong-owner routes, management-route collisions and service-only operations; independently call fixture handlers under their own policy, preserving F-02 route validation/admission (D09, D38, D39).
- [ ] T022 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryServiceBindingTests.cs` for the exact effective owner-added unkeyed single-service descriptor versus shadowed/removed/wrong-owner/keyed/enumerable ambiguity; assert no discovery factory invocation or resolution and independently prove the actual fixture service is callable only when composed (D10).
- [ ] T023 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryCapabilityTests.cs` for exact tested fixture support versus prospective/unverified/unsupported, overlapping versions/operations/owners, multi-owner emission once under first sorted owner, operation-specific required dependencies and absent/disabled optional integrations; enabled incompatible targets must still fail inherited composition without repair (D07, D08, D11..D13).
- [ ] T024 [P] [US2] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryLifecycleTests.cs` for initializing/ready/not-ready/unknown/failed states, explicit inherited reassessment loss/recovery, unrelated module not-ready, stop/drain/cleanup/terminal overrides and failed-start local reports; repeated reads must add zero probes and neither remove routes, close runtime admission on readiness loss nor start a diagnostic listener (D12, D14..D17).

### Implementation for User Story 2

- [ ] T025 [US2] Seal actual route evidence in `src/Hoard.Hosting/Discovery/DiscoveryBindingLedger.cs`, `src/Hoard.Hosting/Routing/HoardModuleEndpointBuilder.cs` and `src/Hoard.Hosting/Lifecycle/HoardApplicationExtensions.cs` at the existing ownership/conflict-validation boundary: route evidence is "derived from the existing sealed owned routes and final route validation"; no descriptor-only route, custom matcher, handler delegate or private URL may be published, and no operation is usable before both ledgers are final (D09).
- [ ] T026 [US2] Capture owner-added descriptors during supervised ConfigureServices in `src/Hoard.Hosting/Lifecycle/HoardServiceCompositionExtensions.cs` and finalize service evidence in `src/Hoard.Hosting/Discovery/DiscoveryBindingLedger.cs` before build: "The exact service descriptor must have been added by that owner's supervised ConfigureServices and remain the effective unkeyed single-service registration." Removed/shadowed/foreign/keyed/enumerable ambiguity is unavailable, never resolved to manufacture proof; preserve F-03 owner option handoff and existing build supervision (D10).
- [ ] T027 [US2] Implement `src/Hoard.Hosting/Discovery/DiscoveryCapabilityEvaluator.cs` with identity "(capabilityId, capabilityVersion, operationId, ownerIds)" and "Owners are sorted canonical distinct IDs; overlapping contributions remain separate." Capabilities are "Scoped contributions; not a global union of capability names"; emit multi-owner contributions once under the first sorted owner. `usable` requires exact supported evidence/scope, all owners/dependencies enabled/compatible, actual sealed bindings, serving phase/open startup admission and their same-revision readiness; unsupported/unverified/unknown inputs never promote through global health, and unrelated readiness loss does not suppress independent operations (FR-005..007, D07..D16).
- [ ] T028 [US2] Implement deterministic reason derivation in `src/Hoard.Hosting/Discovery/DiscoveryAvailabilityReasons.cs` using T008's closed templates for missing inclusion/registration, disabled, unsupported/unverified, dependencies/bindings, initializing/not-ready/stopping/stopped/unknown; retain all applicable bounded reasons plus omitted count and safe approved affected IDs without echoing diagnostic payloads or suggesting fallback/hot-install/data rollback (FR-007/015, D11..D17, D24, D29).
- [ ] T029 [US2] Integrate evaluator and ledgers into `src/Hoard.Hosting/Discovery/HoardDiscoverySource.cs`, ensuring every module/global/capability field uses the captured revision and frozen ledger identity. Preserve "Module phase means the last entered authority phase": a ready module may remain assessing-readiness while host phase is running; terminal/late revisions cannot revive availability, and discovery cannot assess, activate or reinterpret stop ownership (D14..D16, D31).
- [ ] T030 [US2] Complete failed-start/stop/recovery assertions in `tests/integration/Hoard.Composition.Tests/DiscoveryLifecycleTests.cs` using existing safe local reports and real inherited transitions, including late worker/readiness faults; verify no failed selection is made successful to serve discovery and no runtime readiness loss is misreported as drained traffic or removed mappings (D15..D17).
- [ ] T031 [US2] Extend `scripts/discovery_evidence.py` with exact D08..D17 results and independent route/service counters, run T021..T024/T030 with US1 regressions and record paired outcomes; fixture support/evidence must remain explicitly synthetic and full acceptance must remain incomplete until access/consumer/bounded/package proof exists.

**Checkpoint**: Operation claims match actual fixture composition and inherited
observations. No management listener or execution permission is introduced.

## Phase 5: User Story 3 - Inspect Safely with the Right Management Access (Priority: P1)

**Goal**: Introduce the discovery and fixed-description routes together behind
the same explicit read policy/posture, with bounded safe output.

**Independent Test**: Exercise actual serialized responses and descriptions
with permitted/denied identities and invented sensitive inputs. Pair TestServer
policy branches with private loopback Kestrel binding/raw-peer/TLS adapters.
Covers US3-1..4, FR-011..014/016/020 and D18..D24/D37..D40.

### Tests for User Story 3

- [ ] T032 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryOwnershipTests.cs` for Hosting-owned BindHoardDiscovery accepting only the exact retained app/lease/root/catalog/source, idempotence for that pair and rejection of foreign app/root or substituted source before mapping; verify no DI-only ownership shortcut, new service registration or configuration-proof consumption (D38).
- [ ] T033 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryAuthorizationTests.cs` for equal protection of both literal GET routes, authorized read versus 401/403, missing policy/authentication services as startup errors, no inventory on denial, management-read without mutation/activation/secrets/execution, and no public description/static/development bypass (D18, D19, D37, D39).
- [ ] T034 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryExposureTests.cs` using an internal test-only verifier for explicit direct-loopback and secured-network policies: deny null/nonlocal raw peers, wildcard/unknown effective binding, configured proxy/local forwarded headers and untrusted/spoofed forwarding; require authenticated read plus direct HTTPS or explicitly validated trusted topology and fail 503 until protection is verified (D20, D21).
- [ ] T035 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryDisclosureTests.cs` seeding invented configured values, env/file locators, private paths, credential URLs, defaults/allowed values, markup/control/long text, unknown identifiers and raw collaborator errors; capture safe model/JSON/description/examples/problems/logs/telemetry and assert zero markers with retained safe phase/reason/approved affected identity/correction/correlation (D22..D24, D40).
- [ ] T036 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryWireContractTests.cs` comparing emitted required properties/types/enums/limits/examples and closed Problem shape with `specs/004-module-discovery/contracts/openapi.json`; cover both literal routes, generic non-reflecting query 400, ordinary 405 without implicit HEAD support, no-store/private/no-cache/nosniff on success/failure, no ETag/304 or credentialed wildcard CORS and no deployment-specific description data (D24, D39).
- [ ] T037 [P] [US3] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryKestrelAdapterTests.cs` with private ephemeral loopback-only Kestrel instances and in-memory client-pinned certificates: prove effective address acquisition, raw peer before forwarding rewrites regardless of opt-in order, HTTPS recognition and fail-closed pre-verification; reject wildcard/nonloopback config without opening such sockets and stop/dispose every listener/client within finite budgets, without global trust changes or external proxy/certificate certification (D20, D21).

### Implementation for User Story 3

- [ ] T038 [US3] Add the public Hosting-owned BindHoardDiscovery guard in `src/Hoard.Hosting/Lifecycle/HoardServiceComposition.cs` and `src/Hoard.Hosting/Discovery/DiscoveryOwnership.cs`: ReferenceEquals must match the actual retained application, root, lease and owned source/catalog; return only IHoardDiscoverySource, reject foreign/substituted pairs with safe StaleComposition, and make exact-pair binding idempotent without exposing internals or altering ownership (D38).
- [ ] T039 [US3] Implement shared requirements/posture validation in `src/Hoard.Hosting/Discovery/DiscoveryExposureRequirement.cs`, `DiscoveryExposureVerifier.cs` and opt-in integration in `src/Hoard.Hosting/Lifecycle/HoardServiceCompositionExtensions.cs`: explicit modes only, named management-read policy and required auth services, direct local no-proxy assertion with verified loopback bindings/raw peer, or authenticated secured-network HTTPS/trusted immediate peers/networks and validated TLS termination; absent/misconfigured/unknown protection fails closed, never by Host or forwarded-header heuristics (D18..D21).
- [ ] T040 [US3] Implement `src/Hoard.Hosting/Discovery/DiscoveryRawPeerStartupFilter.cs` and actual Kestrel address/posture adapter in `DiscoveryExposureVerifier.cs`, wiring `src/Hoard.Hosting/Lifecycle/HoardServiceCompositionExtensions.cs` so raw peer capture is immediately after F-02's outer completion boundary and before every existing startup filter/forwarding rewrite regardless of registration order; other unknown server topologies require separate tested adapters, no public test-verifier bypass or admission-owner change (D20, D21).
- [ ] T041 [US3] Add Application wire DTOs/projection in `src/Hoard.Application/Features/Modules/GetDiscovery/Response.cs` and `Projector.cs`, separate from Hosting's safe model, matching the normative OpenAPI fields: schemaVersion 1; lifecycle UUID; revision is "Positive monotonic integer encoded as decimal text to avoid JavaScript integer precision loss" with positive pattern and at most 20 characters; assessment time nullable before assessment, sorted unique modules/options/contributions, selectedRoles at most three, all required state dimensions and no private model serialization (D03, D24, D39).
- [ ] T042 [US3] Implement shared `src/Hoard.Application/Discovery/DiscoveryResponseWriter.cs`, `DiscoveryProblem.cs` and `DiscoveryTelemetry.cs`: encode typed DTOs/fixed description with default JSON escaping into a capped private 4 MiB UTF-8 buffer before headers, checking monotonic deadline/cancellation at least every 64 items and on buffer writes. Dispose buffer after send/failure, return closed bounded safe problems for owned failures, never commit 200 after pre-dispatch cancellation or overflow; telemetry uses closed outcome/reason/phase and route templates, not payloads, URLs, module/operation/correlation metric dimensions or response dumps (D22..D24, D34, D35, D40).
- [ ] T043 [US3] Implement `src/Hoard.Application/Features/Modules/GetDiscovery/Endpoint.cs` with explicit management-read plus shared exposure requirement, safe query rejection, same-root bound capture/projection/writer and cancellation-aware send; retain generic 400, challenge/forbid without inventory and safe unavailable 503, no stale/empty success, mutation endpoint, extra probe or permission grant (D18..D24, D39).
- [ ] T044 [US3] Embed the fixed normative document as `src/Hoard.Application/Discovery/openapi.json` via `src/Hoard.Application/Hoard.Application.csproj`; implement `src/Hoard.Application/Features/Modules/GetDiscoveryDescription/Endpoint.cs` and `src/Hoard.Application/Discovery/HoardDiscoveryApplicationExtensions.cs` so MapHoardDiscovery binds the exact composition and maps both protected literal GET routes before MapHoardModulesAsync's existing combined validation. Serve no anonymous static copy/Swagger UI or deployment inventory and use the same protection/cache/size/problem rules (D19, D38, D39).
- [ ] T045 [US3] Add separate execution-permission integration in `tests/integration/Hoard.Composition.Tests/DiscoveryAuthorizationTests.cs`: after discovery truthfully reports a fixture operation usable, management-read-only still cannot execute it, permitted execution succeeds under its own policy/counter, and no inspection can change config/selection or resolve secrets (D18, D26, D37).
- [ ] T046 [US3] Complete full-surface marker/diagnostic capture in `tests/integration/Hoard.Composition.Tests/DiscoveryDisclosureTests.cs`, including actual denials, deadline/encoding failures, late safe lifecycle states and the deployed description; confirm every owned failure retains safe phase/correction/correlation/approved affected IDs where known and unknown text is suppressed rather than merely escaped (D22..D24, D40).
- [ ] T047 [US3] Extend `scripts/discovery_evidence.py` with exact D18..D24/D37/D39/D40 result inventories, run T032..T037/T045/T046 and US1/US2 regressions, record schema/actual JSON checks and mandatory real-loopback adapter outcomes with finite teardown; distinguish policy/adapter evidence from external proxy isolation, production auth/TLS and public transport certification.

**Checkpoint**: Both read-only routes are protected at introduction. Usability
is neither execution authorization nor production/provider certification.

## Phase 6: User Story 4 - Represent Availability Clearly in Management Views (Priority: P2)

**Goal**: Prove textual state/action/freshness decisions from public serialized
JSON without scaffolding a product frontend or depending on .NET providers.

**Independent Test**: Feed actual serialized observations and bounded
malformed/future/failure examples into a standalone JSON-only consumer. Check
labels, guidance, reading order, action eligibility and refresh races.
Covers US4-1..5, FR-015..020/022 and D25..D30/D32/D37.

### Tests for User Story 4

- [ ] T048 [P] [US4] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryPresentationTests.cs` for distinct absent/unknown inclusion, included-unregistered, disabled, unsupported/unverified, fixture-only, initializing/not-ready/stopping/stopped and unknown meanings; require textual corrective guidance, logical contextual labels, hidden unsupported actions and disabled unavailable/unknown actions with independent execution permission (D25, D26, D28, D29, D37).
- [ ] T049 [P] [US4] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryConsumerRefreshTests.cs` with a monotonic fake clock and response barriers for loading/refreshing/empty/denied/failed/stale states, denied inventory discard, failed refresh immediate staleness, exact 30-second age boundary, older generation/revision rejection and new lifecycle only on the latest generation (D27, D32).
- [ ] T050 [P] [US4] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryConsumerCompatibilityTests.cs` for additive unknown descriptive fields, unknown operation/state/category/schema, malformed or missing required fields, duplicate module/contribution identities and unsafe text; preserve only safe known inventory, never infer new actions or report incompatible data as empty success, and parse actual bytes instead of Hosting objects (D28, D30).

### Implementation for User Story 4

- [ ] T051 [US4] Add standalone `tests/fixtures/discovery/ReferenceConsumer/ReferenceConsumer.csproj`, `Program.cs` and `DiscoveryJsonReader.cs` with BCL-only JSON contract parsing and bounded required-field/type/identity validation, no Hosting/provider/Application references; expose a fixture adapter for the existing tests, tolerate only safe additive descriptions, compare revision decimal strings without precision loss and fail closed on unknown action/version semantics (D30, D38).
- [ ] T052 [US4] Implement `tests/fixtures/discovery/ReferenceConsumer/PresentationProjector.cs` preserving separate inclusion/registration/enablement/support/readiness dimensions, explicit fixture evidence labels, assessment/publication times and safe reasons. Unsupported actions hide; supported unavailable/unknown actions cannot invoke; even usable known actions require an independent execution-permission input, not management-read or provider identity (D25, D26, D37).
- [ ] T053 [US4] Implement `tests/fixtures/discovery/ReferenceConsumer/RefreshState.cs` with "monotonically increasing client refresh generation and local monotonic receipt timer" and "a failed refresh immediately makes retained data stale"; receipt age over 30 seconds expires actions, denied access discards sensitive inventory and older attempts/revisions cannot overwrite latest accepted lifecycle state or fabricate a new assessment (D27, D32).
- [ ] T054 [US4] Add `tests/fixtures/discovery/ReferenceConsumer/PresentationText.cs` and `examples/LifecycleHost/Discovery/presentation-examples.json` with bounded inert semantic labels/status/guidance and logical reading/focus order for every state; no color/hover/motion/markup dependency. Separate bundled config/restart, custom package/registration/rebuild/redeploy/restart and runtime investigation, with no hot-install/data-rollback suggestion; identify fixture/observation/permission limits and do not claim DOM/ARIA/contrast/browser/WCAG acceptance (D25..D29).
- [ ] T055 [US4] Wire T048..T050 through the standalone consumer's JSON entry point in `tests/integration/Hoard.Composition.Tests/DiscoveryPresentationTests.cs`, including actual authorized/denied/error endpoint bytes plus synthetic future/malformed counterparts; independently inspect semantic reading order and hidden/disabled actions without leaking internal models or executing an action (D25..D30, D37).
- [ ] T056 [US4] Extend `scripts/discovery_evidence.py` to build/run the JSON-only consumer and record exact D25..D30 decisions and refresh-generation cases, run T048..T050/T055 with HTTP regressions, and reject missing/empty consumer evidence rather than treating examples or semantic checks as a delivered Next.js console.

**Checkpoint**: Consumer decisions and semantic presentation are proven from
the wire contract; rendered UI/accessibility remain later work.

## Phase 7: User Story 5 - Refresh a Consistent, Bounded Observation (Priority: P2)

**Goal**: Prove publication coherence, explicit bounded failure, zero read side
effects and fresh lifecycle identity across bundled/custom restart journeys.

**Independent Test**: Race reads with inherited readiness/stop publications;
cancel before/during projection/encoding; exhaust exact bounds and record the
specified 100-read local workload. Compare package-only restart identities
and independent provider hashes. Covers US5-1..4, FR-008..010/017/019/021
and D15..D17/D31..D36.

### Tests for User Story 5

- [ ] T057 [P] [US5] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryRaceTests.cs` with barriers around capture/publication, explicit reassessment, admission closure, shutdown and late diagnostics: each module/global/capability result must belong to exactly one lifecycle/revision, never mix old/new fields or revive terminal availability; simultaneous readers cannot block behind authority callbacks or add probes/resources (D15, D16, D31).
- [ ] T058 [P] [US5] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryBoundsTests.cs` for unavailable/missing/inconsistent source, pre-cancellation and mid-projection/encoding cancellation, monotonic deadline, exact/over collection/text/4 MiB UTF-8 boundaries including escaped expansion, omitted diagnostics and zero-provider-disposal; require explicit safe failure/no 200 before dispatch, disposal of private buffers and release/observation of all held test work without kill guarantees (D33..D35).
- [ ] T059 [P] [US5] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryPerformanceTests.cs` for 100 complete authorized TestServer reads, 100 modules x 10 contributions each, concurrency 10 and p95 <= two seconds; verify actual counts/complete parsed bodies, bytes, SDK/OS/environment and before/after constructor/secret/probe/service/connection/resource counters, not mocked timing or omitted slow samples (D36).
- [ ] T060 [P] [US5] Write failing `tests/integration/Hoard.Composition.Tests/DiscoveryRestartTests.cs` for immutable running selection despite edited config, explicit same-binary bundled restart, rebuilt custom distribution, invalid replacement then explicit recovery, fresh lifecycle IDs and stale/lower-generation old-response rejection; no live install/provider swap or automatic data rollback (D17, D32).

### Implementation and Proof for User Story 5

- [ ] T061 [US5] Complete and exercise the bounded read path in `src/Hoard.Hosting/Discovery/HoardDiscoverySource.cs` and `src/Hoard.Application/Discovery/DiscoveryResponseWriter.cs` against T057/T058: enforce "capture/projection/encoding checks cancellation and a monotonic two-second default deadline at least every 64 items and on bounded buffer writes"; "No pooled buffer or HttpContext escapes the request." Resolve exposed races/limit errors at the existing capture/encoding boundary, not with per-read Task.Run, retries, lock acquisition, subscriptions, provider callbacks or a second coordinator; retain actual assessment times and safe explicit failures (D31, D33..D35).
- [ ] T062 [US5] Add package-only baseline `examples/LifecycleHost/Discovery/LifecycleHost.Discovery.csproj`, `Program.cs`, `baseline.json` and approved catalog fixtures: inspect known/unregistered/disabled/unknown entries, execute same-binary bundled protocol selection plus restart and invalid replacement/explicit recovery through existing configuration/lifecycle APIs, and emit safe observation/actual-operation evidence with distinct lifecycle IDs via TestServer only (D01..D05, D09, D17, D32).
- [ ] T063 [US5] Add `examples/LifecycleHost/Discovery/Custom/LifecycleHost.Discovery.Custom.csproj`, `custom.json` and host-side catalog/adapters, referencing the separately packed alternative artifact fixture rather than its source project; rebuild/redeploy/restart the custom fixture, label support as fixture-only, prove actual operations and compare unrelated provider source/binary hashes with the baseline without engine changes or metadata/artifact Hosting dependencies (D08..D10, D29, D32, D38).
- [ ] T064 [US5] Extend package-journey preparation/verification in `scripts/discovery_evidence.py` for T062/T063: exact nonempty baseline/bundled-restart/invalid-replacement/recovery/custom-rebuild inventories, independent JSON observations/route/service counters, local package provenance/hashes and lifecycle identities; fail stale/missing/duplicate proof, preserve existing preparation helpers and execute no nested orchestrator or public listener (D32, D38).
- [ ] T065 [US5] Add performance/resource evidence validation to `scripts/discovery_evidence.py` and regressions to `tests/tooling/test_discovery_evidence.py`: reject wrong module/contribution/read/concurrency counts, incomplete/noncurrent bodies, missing environment/byte/resource data, hidden failures/slow samples and nonzero provider I/O/probe/resource deltas; calculate p95 from all 100 actual samples and record the local fixture-only scope (D35, D36).
- [ ] T066 [US5] Run prepared T057..T060 checks, package-only baseline/custom journeys and T065 evidence validation through `scripts/discovery_evidence.py`, record D31..D36 red/green and actual bounded workload results, then run prior-story regressions; full acceptance remains incomplete until cross-cutting proof closes. Document any inability to obtain mandatory loopback/performance/package evidence as a blocker, never a passing proxy or production SLA.

**Checkpoint**: Coherent bounded observations and both distribution journeys
are evidenced. Cross-cutting packaging/binary/review/regression gates remain.

## Phase 8: Polish and Cross-Cutting Concerns

**Purpose**: Preserve architectural/binary compatibility, require complete
acceptance evidence and document current behavior before PR handoff.

- [ ] T067 [P] Add paired architectural tests in `tests/architecture/Hoard.Architecture.Tests/DiscoveryBoundaryTests.cs` and standalone fixtures under `tests/fixtures/architecture/Discovery/PermittedApplication/PermittedApplication.csproj`, `ForbiddenProvider/ForbiddenProvider.csproj` and `CrossSlice/CrossSlice.csproj`: permit approved Application -> Hosting -> Core/framework paths, reject provider coupling/private types/cross-slice internals and preserve ARCH-001..008 including existing Identity path distinctions; add exact fixture ownership/locks, not blanket exemptions (D38).
- [ ] T068 Integrate real discovery graph/package scans in `scripts/foundation_evidence.py`, `tests/architecture/Hoard.Architecture.Tests/InspectionEvidence.cs` and `scripts/discovery_evidence.py` as required by T067, preserving every existing runner's exact scan inventory and discovery-free operation; inspect declared/resolved/packed/compiled Application/framework propagation and retain Core/Abstractions/provider rules without trusting namespace prefixes or ignoring unknown dependencies (D38).
- [ ] T069 [P] Add standalone new-source `tests/fixtures/discovery/ApplicationConsumer/ApplicationConsumer.csproj`, `Program.cs` and non-web `tests/fixtures/discovery/NonWebConsumer/NonWebConsumer.csproj`, `Program.cs`, using only local packed platform references and tracked consumer locks; compile/bind protected discovery via public APIs and prove the non-web consumer receives ASP.NET Core framework requirements transitively, with no product source ProjectReferences (D38).
- [ ] T070 Run retained T004 pre-F-04 lifecycle/configuration/Abstractions-only option-provider binaries and the pre-existing F-01 registration proof against new local platform packages via `scripts/discovery_evidence.py`, without recompilation; compare retained hashes before/after, execute T069 consumers, verify source/binary/hash provenance and fail missing/mismatched evidence explicitly (D38).
- [ ] T071 Complete adversarial `tests/tooling/test_discovery_evidence.py` cases for exact D01..D40/no-skip suite and package-journey closure, missing red/green/JSON/counters/architecture/binary/adapter samples, incomplete lock inventory, unsafe manifests and stale/mismatched performance evidence; reject empty success and nonzero child results without adding dependencies or recursively running acceptance (D01..D40).
- [ ] T072 Finalize `scripts/validate-discovery.sh` and `scripts/discovery_evidence.py` with exact required suite/case/journey inventories, immutable local package hashes, actual serialized JSON, all independent counters, retained/source consumers, mandatory D20/D21 adapters, performance/environment data, test totals/no skips and explicit failures; tests consume prepared evidence, no recursive runner calls, source package publication, real secrets or product/public listeners (D01..D40).
- [ ] T073 Generate and review intentional project/standalone lock updates with `bash scripts/validate-discovery.sh --update-locks` and existing runners' documented update modes only where the new approved graph requires them; retain `src/Hoard.Application/packages.lock.json`, `tests/integration/Hoard.Composition.Tests/packages.lock.json` and all new fixture/consumer/baseline locks, then replay fresh default locked discovery acceptance and prove default mode changes no lockfile (D38).
- [ ] T074 Run `bash scripts/validate-discovery.sh`, `bash scripts/validate-configuration.sh`, `bash scripts/validate-lifecycle.sh`, `bash scripts/validate-foundation.sh` and `python3 -m unittest discover -s tests/tooling -v`; require focused format/analyzers/build, all D01..D40, prior configuration/lifecycle/foundation architecture/compatibility/package/binary proofs and zero skipped mandatory evidence. Record exact commands/results, red-to-green references and genuine platform limitations, not generated artifacts as passing acceptance.
- [ ] T075 [P] Update `README.md`, `docs/DEVELOPMENT.md`, `docs/PROVIDERS.md`, `examples/LifecycleHost/README.md`, `examples/CustomHost/README.md` and `specs/004-module-discovery/quickstart.md` with actual opt-in APIs, protected description, explicit direct-local/no-proxy versus secured-network posture, allowlisted metadata, observation freshness, read/execution distinction, consumer limits and new validation commands. Explain bundled config/restart, custom rebuild/redeploy/restart and remove-opt-in/restart rollback without data rollback; identify fixture/adapter-only scope and unaffected product/architecture/governance/IaC/release documents with reasons (SC-008).
- [ ] T076 Obtain bounded `hoard-architecture-review` of actual changes to `src/Hoard.Hosting/Discovery/`, lifecycle/routing integration, Application slices/references and evidence tooling; remediate actionable findings with focused red/green regressions and review evidence in `specs/004-module-discovery/plan.md`, preserving the public/binary boundaries, sole lifecycle authority, raw-peer ordering, route/service proof, bounded ownership and no unsupported claims.
- [ ] T077 Reconcile every requirement/outcome, 22 story scenarios, 13 edges and 40 cases with actual implementation/proof in `specs/004-module-discovery/plan.md` and `quickstart.md`, including environment/performance data, package/framework/retained hashes, safe examples and review references. Record failures/blockers honestly, preserve requirement/design meaning and reviewer-owned checklist bytes, and do not claim rendered WCAG, production provider/auth/proxy/native-client/conformance qualification (FR-022, SC-001..008).
- [ ] T078 Re-run affected focused/default checks only if review or final documentation exposed new changes/failures, verify `git diff --check`, local documentation links, all required locked outputs and T001..T077 proof, then commit/push coherent work immediately and update draft feature PR #10 using its template. Record implementation completion in `specs/004-module-discovery/tasks.md` only after every task passes; do not run convergence/finalization, merge, publish packages/releases or declare F-04/backlog completion.

**Checkpoint**: All implementation tasks and proofs pass; a separate invocation
still owns convergence, followed by finalization and the merge/release gates.

## Dependencies and Execution Order

### Phase and Story Dependencies

```text
Setup T001..T004 -> Foundation T005..T012 -> US1 T013..T020
                                                |
                                                v
                                          US2 T021..T031
                                                |
                                                v
                                          US3 T032..T047
                                           /           \
                                          v             v
                                  US4 T048..T056   US5 T057..T066
                                           \           /
                                            v         v
                                     Cross-cutting T067..T078
```

US1 needs no later story for its in-process inventory proof. US2 intentionally
depends on the inventory source; US3 depends on its truthful operation model
before exposure. US4 uses its own JSON consumer and US5 the existing read/
publication path; both depend on US3 for actual endpoint bytes, not on each
other's implementation. Their shared evidence-helper edits are serialized.
Every story has independent assertions/counters, not five source authorities.

### Explicit Task Prerequisites

Each row lists all direct prerequisites; transitive prerequisites also apply.
`none` means independently ready. All tasks are
ordered topologically, including shared-file edits and final evidence gates.

| Task | Direct prerequisites |
| --- | --- |
| T001 | none |
| T002 | none |
| T003 | T002 |
| T004 | none |
| T005 | T001, T003, T004 |
| T006 | T003, T004 |
| T007 | T005, T006 |
| T008 | T007 |
| T009 | T001, T003, T004 |
| T010 | T007, T009 |
| T011 | T008, T010 |
| T012 | T005, T006, T008, T009, T010, T011 |
| T013 | T012 |
| T014 | T012 |
| T015 | T012 |
| T016 | T013, T015 |
| T017 | T014, T015 |
| T018 | T016, T017 |
| T019 | T018, T014 |
| T020 | T013, T014, T015, T019 |
| T021 | T020 |
| T022 | T020 |
| T023 | T020 |
| T024 | T020 |
| T025 | T021 |
| T026 | T022, T025 |
| T027 | T023, T024, T025, T026 |
| T028 | T023, T024 |
| T029 | T027, T028 |
| T030 | T024, T029 |
| T031 | T021, T022, T023, T030 |
| T032 | T031 |
| T033 | T031 |
| T034 | T031 |
| T035 | T031 |
| T036 | T031 |
| T037 | T031 |
| T038 | T032 |
| T039 | T033, T034, T038 |
| T040 | T037, T039 |
| T041 | T035, T036 |
| T042 | T035, T036, T041 |
| T043 | T040, T042 |
| T044 | T043 |
| T045 | T033, T044 |
| T046 | T035, T044 |
| T047 | T032, T033, T034, T035, T036, T037, T045, T046 |
| T048 | T047 |
| T049 | T047 |
| T050 | T047 |
| T051 | T048, T049, T050 |
| T052 | T051 |
| T053 | T051 |
| T054 | T052 |
| T055 | T048, T050, T052, T053, T054 |
| T056 | T049, T050, T055 |
| T057 | T047 |
| T058 | T047 |
| T059 | T047 |
| T060 | T047 |
| T061 | T057, T058 |
| T062 | T060, T061 |
| T063 | T062 |
| T064 | T056, T063 |
| T065 | T059, T064 |
| T066 | T057, T058, T059, T060, T061, T065 |
| T067 | T056, T066 |
| T068 | T067 |
| T069 | T056, T066 |
| T070 | T068, T069 |
| T071 | T070 |
| T072 | T071 |
| T073 | T072 |
| T074 | T073 |
| T075 | T074 |
| T076 | T074 |
| T077 | T075, T076 |
| T078 | T077 |

Shared edits are explicitly serialized:
`scripts/discovery_evidence.py` T003 -> T012 -> T020 -> T031 -> T047 ->
T056 -> T064 -> T065 -> T066 -> T068 -> T070 -> T072;
`tests/tooling/test_discovery_evidence.py` T002 -> T065 -> T071;
`HoardServiceCompositionExtensions.cs` T011 -> T019 -> T026 -> T039 -> T040;
`DiscoveryBindingLedger.cs` T025 -> T026;
`HoardDiscoverySource.cs` T018 -> T029 -> T061;
`DiscoveryResponseWriter.cs` T042 -> T061;
Application manifest T006 -> T044 -> T073; final evidence/docs T075/T076 -> T077.
Keep default runner/lock changes isolated and reviewed; `[P]` never overrides
these dependencies or permits simultaneous edits to a shared fixture/helper.

## Requirement, Outcome and Proof Traceability

T001..T012 are shared contract/instrumentation/publication prerequisites.
The acceptance contract retains complete mappings to all 22 story scenarios
and 13 ordered edges; the case-to-task table below assigns every such proof.

| Requirement | Implementation / integration tasks | Focused proof / closure |
| --- | --- | --- |
| FR-001 | T007, T011, T016, T018, T019 | T005, T013..T015, T020 |
| FR-002 | T008, T016, T017, T027, T041 | T013, T015, T023, T035, T046 |
| FR-003 | T010, T016, T027, T029, T041 | T009, T013, T024, T030 |
| FR-004 | T011, T016..T019 | T005, T014, T020 |
| FR-005 | T007, T027..T029 | T013, T023, T031 |
| FR-006 | T025..T027, T029 | T021..T024, T030, T031 |
| FR-007 | T008, T027, T028, T042 | T023, T035, T046 |
| FR-008 | T010, T011, T018, T025..T029 | T014, T024, T030, T057 |
| FR-009 | T010, T018, T029, T041, T053, T061 | T009, T024, T049, T057, T060 |
| FR-010 | T008, T018, T029, T042, T043, T061 | T024, T030, T046, T058 |
| FR-011 | T038..T040, T043, T044 | T032..T034, T036, T037, T047 |
| FR-012 | T039, T040, T043, T044 | T034, T036, T037, T047 |
| FR-013 | T008, T017, T041, T042, T044 | T014, T015, T035, T036, T046 |
| FR-014 | T008, T017, T028, T042 | T015, T035, T046, T058 |
| FR-015 | T008, T028, T052, T054 | T035, T048, T055 |
| FR-016 | T039, T043..T045, T052 | T033, T045, T048, T055 |
| FR-017 | T051..T053, T055 | T048..T050, T055, T060 |
| FR-018 | T051..T053 | T045, T048..T050, T055 |
| FR-019 | T051, T052, T054 | T048, T050, T055, T069 |
| FR-020 | T041..T044, T051, T075 | T033, T036, T050, T055, T077 |
| FR-021 | T010, T018, T029, T042, T053, T061..T065 | T014, T024, T049, T057..T060, T066 |
| FR-022 | T001..T078 | T020, T031, T047, T056, T066..T074, T076..T078 |
| SC-001 | T016..T019, T027, T029 | T013..T015, T020, T023, T024 |
| SC-002 | T025..T029, T061 | T021..T024, T030, T057 |
| SC-003 | T038..T045 | T032..T034, T036, T037, T045, T047 |
| SC-004 | T008, T017, T028, T041, T042, T044 | T035, T036, T046, T047 |
| SC-005 | T051..T054 | T045, T048..T050, T055, T056 |
| SC-006 | T010, T018, T029, T042, T053, T061..T064 | T024, T030, T049, T057, T058, T060, T066 |
| SC-007 | T007, T042, T061, T065 | T058, T059, T065, T066 |
| SC-008 | T027, T044, T054, T062..T064, T069, T075 | T023, T036, T048, T055, T060, T070, T077 |

| Acceptance cases | Focused test tasks | Implementation / acceptance tasks |
| --- | --- | --- |
| D01..D04 | T005, T013, T015 | T007, T016, T018..T020 |
| D05..D06 | T005, T014, T015 | T007, T011, T016..T020 |
| D07..D08 | T013, T023 | T008, T027, T029, T031 |
| D09 | T021 | T025, T027, T029, T031, T062, T063 |
| D10 | T022 | T026, T027, T029, T031, T062, T063 |
| D11..D13 | T023, T024 | T027..T029, T031 |
| D14..D17 | T009, T024, T030, T057 | T010, T029, T031, T061, T066 |
| D18..D19 | T033, T045 | T039, T043..T045, T047 |
| D20..D21 | T034, T037 | T039, T040, T043, T044, T047 |
| D22..D24 | T015, T035, T036, T046 | T008, T017, T028, T041, T042, T047 |
| D25..D26 | T048, T055 | T052, T054, T056 |
| D27 | T049 | T053, T056 |
| D28..D29 | T048, T050, T055 | T051, T052, T054, T056, T075 |
| D30 | T050, T055 | T051, T056 |
| D31 | T009, T057 | T010, T029, T061, T066 |
| D32 | T049, T060 | T053, T062..T064, T066 |
| D33..D35 | T015, T058 | T007, T018, T042, T061, T065, T066 |
| D36 | T059 | T065, T066 |
| D37 | T033, T045, T048, T055 | T043, T045, T052, T056 |
| D38 | T005, T032, T067, T069 | T004, T006, T011, T038, T063, T064, T068..T070, T073 |
| D39 | T021, T033, T036 | T041..T044, T047, T075 |
| D40 | T035, T046 | T008, T042, T047 |

T071..T074 require closure of the entire matrix, not a union of optional
partial modes. T075..T078 preserve documentation/review evidence and the
distinction between implementation completion and later driver stages.

## Parallel Execution Examples

Only execute a group after its shared predecessors complete:

- Setup: T001 harness, T002 tooling regressions and T004 retained inputs are
  file-disjoint. T003 waits for T002; T006 waits for baseline provenance T004.
- Foundation: T005 contract tests and T009 publication tests can be authored
  together after setup. T010 publication and T008 safe records use different
  files once their own prerequisites pass.
- US1: after T012, T013 inventory, T014 disabled and T015 catalog tests are
  independent. T016 inventory and T017 option projection can then proceed
  separately; T018 waits for both.
- US2: after T020, T021 route, T022 service, T023 capability and T024 lifecycle
  tests are file-disjoint. Route/service ledger edits T025/T026 are serial.
- US3: after T031, T032 ownership, T033 authorization, T034 posture, T035
  disclosure, T036 wire and T037 Kestrel tests are independent files. T041/T042
  wire encoding can proceed alongside T038..T040 Hosting protection once their
  respective tests are authored; endpoint mapping waits for both chains.
- US4: after T047, T048 presentation, T049 refresh and T050 compatibility tests
  are independent; after T051, T052 projection and T053 refresh use different
  files. T054 guidance then feeds the serial actual-JSON integration.
- US5: after T047, T057 races, T058 bounds, T059 workload and T060 restart tests
  are file-disjoint and can overlap US4's consumer files. T064 still waits for
  T056's shared helper update; do not run these as simultaneous helper edits.
- Cross-cutting: T067 architecture fixtures and T069 source/non-web consumers
  are independent after both stories finish. T075 documentation and T076
  architecture review may overlap after passing acceptance, but serialize any
  review remediation touching those documents before T077 reconciliation.

These examples describe possible contributor concurrency, not a request to
launch agents. Bounded test listeners/workspaces remain independently owned.

## Implementation Strategy

1. Prepare instrumentation, failing evidence checks and pre-change binaries,
   then complete the frozen catalog/safe records/single-publication foundation.
2. Deliver US1's in-process inventory MVP and verify it independently; continue
   directly into actual route/service/support correspondence in US2.
3. Introduce both HTTP slices only with US3's complete shared protection and
   safe bounded encoding. Verify real loopback adapter behavior, not merely
   TestServer claims, before accepting exposure.
4. Prove US4's JSON-only consumer decisions and US5's race/cancellation/
   restart/performance obligations. No phase boundary requests renewed
   authorization during a later full-stage implementation invocation.
5. Close package/framework/architecture/retained-binary evidence, replay
   reviewed locks and all relevant existing suites, update affected guides and
   resolve architecture findings. Mark tasks complete only with passing proof,
   commit and push immediately, keeping the feature PR draft.
6. Stop at the implementation-stage boundary. Convergence, finalization,
   maintainer-authorized merge and exact post-merge alpha source release each
   retain the checkpointed driver's existing authorization/gates.

## Notes

- All 78 tasks start unchecked: shared setup 4, foundation 8, US1 8, US2 11,
  US3 16, US4 9, US5 10 and cross-cutting 12. There are 28 `[P]` tasks.
- All model/schema limits apply even when not repeated on each task. Unknown
  support/state/identity never becomes usable; availability never grants
  execution permission; a fresh read never implies a fresh health assessment.
- No task authorizes infrastructure plan/apply, governance/permission changes,
  public network exposure, provider/package downloads at runtime, product UI,
  production identity/provider qualification, package publication or merge.
