# Implementation Plan: Module Capabilities and Management Discovery

**Branch**: `feature/004-module-discovery` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-module-discovery/spec.md`

**Status**: Phase 0/1 design only, generated through the installed
`speckit-plan` skill with explicitly pinned feature context. All new APIs,
routes, files and acceptance commands below are proposed, not implemented.
The specification and built-in checklist remain unchanged.

## Summary

Add opt-in discovery metadata and a read-only observation source in Hosting,
then two management vertical slices in Application: a complete discovery read
and its protected OpenAPI description. Freeze explicit distribution/support
records before configured composition. Derive operation availability from
actual owned route/service composition and one atomically published lifecycle
observation, without provider construction, secret resolution or health probes.

Preserve the F-01/F-02/F-03 contracts and sole lifecycle authority. Add an
internal bounded publication view to the existing coordinator, not another
readiness controller, scheduler or activation path. Application consumes safe
Hosting models, never private options, provider implementations or slice
internals. A fixture reference consumer proves state/action rules; no Next.js
application, production identity provider or listener is introduced.

## Technical Context

**Language/Version**: Nullable-aware C# / .NET 10, repository-pinned SDK.

**Primary Dependencies**: Existing Hosting dependencies and ASP.NET Core shared
framework; built-in DI, authorization, routing, System.Text.Json, immutable
collections, TimeProvider and bounded buffers. Application adds the already
approved reference to Hosting and `Microsoft.AspNetCore.App` during
implementation. No new third-party runtime package, mediator, frontend package
or concrete-provider reference is needed. OpenAPI is a fixed embedded document,
not a new generation/UI package.

**Storage**: Immutable in-process catalog, sealed composition evidence and
published lifecycle state. No database, runtime filesystem enumeration,
configuration/secret read, persisted inventory or external discovery service.

**Testing**: Existing xUnit composition/architecture projects and in-process
TestServer fixtures; an Application reference is added to composition tests.
Package-only discovery consumers and retained old binaries exercise distribution
and compatibility. A .NET reference consumer uses public JSON, not Hosting
internals; no rendered screen or accessibility certification is claimed.
Mandatory exposure-adapter cases additionally use private ephemeral loopback
Kestrel/TLS listeners with in-memory certificates pinned only to their clients
and finite teardown. Python standard-library tooling validates acceptance
evidence and existing tools.

**Target Platform**: Single-process .NET 10; contributor macOS and eventual
Linux deployments. TestServer proves middleware/contract logic; separate
loopback Kestrel cases prove effective binding/raw-peer/TLS adapter behavior,
not external proxy isolation, production certificates or transport certification.

**Project Type**: Additive library/management slices with fixture-only hosts,
not a curated executable or runnable cache.

**Performance Goals**: Default observation/projection/serialization deadline
two seconds, checked using monotonic time and cancellation. SC-007 requires
95% of 100 complete authorized TestServer reads within two seconds at concurrency
10, for 100 modules and 10 contributions each. Record environment, actual counts,
latencies and resource counters; no public-network or production SLA follows.

**Constraints**: Per lifecycle at most 256 known module entries, 64
contributions per module/4,096 total, 256 option fields per module/4,096 total,
32 bindings/dependencies per contribution and 100 diagnostics with omitted
count. Public identities are canonical and at most 128 characters; labels
160, descriptions 512 and corrective templates 256. A successful UTF-8 JSON
body is at most 4 MiB. Check collection bounds before copying/enumerating and
encoded byte bounds before response headers; never truncate into success.
Secret fields have no defaults/examples/allowed-value payloads. Positive
finite host deadlines may be configured; invalid limits fail before activation.

**Scale/Scope**: All 22 FRs, eight SCs, five stories/22 scenarios and 13 edge
cases are mapped to 40 paired acceptance cases. No runtime installation,
continuous health monitoring, general management CRUD/pagination, production
providers, browser login/tokens, native-client support or F-07 certification.

## Constitution Check

*Gate evaluated before research and re-evaluated after Phase 1 design.*

| Principle / constraint | Pre-research gate | Post-design evidence |
| --- | --- | --- |
| I: cache/native/personal simplicity | Pass: inspection only, no protocol claim | Local policy needs no cloud; fixture support cannot become production support |
| II: versioned explicit composition | Pass: retain existing gates and contracts | [Hosting contract](contracts/hosting-api.md) leaves Abstractions/interfaces unchanged; sealed owner evidence, no construction/fallback |
| III: VSA/shared correctness | Pass: Application owns management | Two slices use a shared safe source; Hosting owns lifecycle/security integration, no cross-slice handler calls |
| IV: bounded work/recovery | Pass: no external/provider calls | [Model](data-model.md) uses immutable publications, finite limits, bounded pre-response encoding and cooperative cancellation |
| V: introduction-time security | Pass: protect reads and descriptions together | [HTTP contract](contracts/discovery-api.md) requires explicit local/network posture, read authorization, no-cache and allowlisted output |
| VI: evidence before claims | Pass: paired fixtures, not inferred qualification | [Acceptance](contracts/acceptance.md) covers actual routes/services, failures and consumer decisions; red-before-green required |
| VII: accessible static console | Pass: no frontend scaffold | [Presentation contract](contracts/presentation.md) consumes JSON, defines semantic labels/order and fail-closed actions; rendered UI remains later |
| VIII: compatible/reversible operations | Pass: additive opt-in, restart only | Retained binaries, public versioned schema, no data migration; remove opt-in and restart to roll back |
| Workflow/governance | Pass: shared correct branch and `plan / running` | One installed stage; future checklists stay reviewer-owned, no tasks or implementation authorization |

No constitutional exception, ADR amendment or governance change is needed.
These are design conclusions; actual enforcement and binary/transport proofs
remain implementation obligations. Architecture-review results are recorded
separately below before handoff.

## Project Structure

### Documentation (this feature)

```text
specs/004-module-discovery/
|-- spec.md                         # Existing requirements, unchanged
|-- checklists/requirements.md      # Existing built-in review, unchanged
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
`-- contracts/
    |-- hosting-api.md
    |-- discovery-api.md
    |-- openapi.json
    |-- presentation.md
    `-- acceptance.md
```

Custom checklists and `tasks.md` belong to later separately authorized stages.

### Source Code (repository root, planned changes only)

```text
src/Hoard.Hosting/
|-- Discovery/                     # Catalog, safe source, policy/posture helpers
|-- Lifecycle/                     # Internal atomic publication, same coordinator
`-- Routing/                       # Sealed actual owner/binding evidence
src/Hoard.Application/
|-- Features/Modules/GetDiscovery/  # Endpoint, wire DTOs, projection, focused tests
|-- Features/Modules/GetDiscoveryDescription/
`-- Discovery/                     # Shared wire encoding/embedded OpenAPI asset
tests/integration/Hoard.Composition.Tests/
tests/architecture/Hoard.Architecture.Tests/
tests/fixtures/discovery/           # JSON-only consumer and retained-binary inputs
examples/LifecycleHost/Discovery/   # Package-only baseline/custom TestServer hosts
scripts/validate-discovery.sh       # Future focused acceptance orchestrator
scripts/discovery_evidence.py       # Future standard-library evidence helper
```

**Structure Decision**: Approved Application -> Hosting and HTTP dependencies
are explicit, including nuspec/framework propagation and updated locks during
implementation. Core remains provider-free and Abstractions remains BCL-only.
Metadata/artifact packages do not gain Hosting/Application references; host-side
catalogs and adapters supply their discovery associations. No new platform
assembly or generic plugin/capability rules engine is needed.

## Phase 0: Resolved Research

[research.md](research.md) records repository evidence, decisions, alternatives
and primary public references. A bounded research agent checked official
ASP.NET Core authorization/proxy/OpenAPI, JSON, timeout and TestServer guidance.
No private source was submitted to documentation services.

Important distinctions: OpenAPI is not automatically protected; JSON escaping
is not secret redaction; cancellation does not kill trusted code; a loopback
proxy connection cannot establish that its original caller is local. Fixed
literal routes also preserve F-02's constrained route-validation envelope.
No unresolved product or implementation clarification remains.

## Phase 1: Design and Integration

1. Register immutable catalog/publication metadata and discovery options before
   F-03 evaluation or legacy composition takes its service snapshot. Validate
   only discovery structure/bounds/associations; use existing composition
   validation for selection, compatibility and provider cardinality.
2. Freeze a safe projection from explicit host-approved fields. Do not serialize
   ModuleDescriptor, provenance URLs, option contracts, configuration reports,
   private options or exceptions wholesale. Unknown/unapproved text is replaced
   by a closed reason/template, even when it looks syntactically harmless.
3. Record actual owned endpoint bindings at the existing route sealing boundary
   and effective service registrations during existing service composition.
   No service is resolved/constructed to prove registration. Invalid or
   shadowed evidence cannot satisfy a contribution.
4. In the same coordinator state transitions and lock, publish a bounded
   immutable lifecycle view with composition identity, revision, publication/
   assessment timestamps, phase, admission and module states. Requests capture
   one pointer; they never call `AssessReadinessAsync`, acquire the coordinator
   lock, subscribe callbacks or invoke a provider. Stop invalidates usability
   before publishing the terminal phases.
5. After supervised build, Application obtains its safe source through the
   narrow Hosting-owned `BindHoardDiscovery` guard, which verifies the exact
   app retained by its lease and source/root/catalog ownership without exposing
   internals. Map the two Application endpoints before
   `MapHoardModulesAsync` performs its existing combined route validation.
   Resolve explicit management-read policy/posture and seal bindings before
   startup admission. Missing protection/collisions fail startup, not fallback.
6. For each authorized request, derive independent operation support and
   availability from fixed catalog plus one lifecycle revision. Bound projection
   and JSON encoding before beginning the body; return explicit failure on
   unavailable source, cancellation, deadline or encoded-size exhaustion.
7. Serve a protected fixed OpenAPI 3.1 description with the same access/posture
   and no-cache rules. Test deployed JSON/description against the normative
   [OpenAPI contract](contracts/openapi.json); do not add a public Swagger UI.
8. Prove presentation behavior with a JSON-only reference consumer: generation-
   aware refresh, distinct states, no unsupported/unavailable/stale actions,
   safe explanations and semantics usable by a future static console.

Detailed interfaces, exposure policy and publication/compatibility boundaries
are in the [Hosting contract](contracts/hosting-api.md). Wire fields, statuses
and consumer behavior are in the other contracts, not copied into slice internals.

## Validation Strategy and Acceptance

[quickstart.md](quickstart.md) distinguishes current commands from proposed
discovery acceptance. The [40-case matrix](contracts/acceptance.md) traces every
requirement/outcome, story scenario and edge case. Case count is not evidence.

Implementation must demonstrate the intended failure before each new behavior
is accepted, then run focused default locked discovery acceptance plus retained
configuration/lifecycle/foundation suites. Preserve original architecture scans,
compatibility classifications and package-source/hash/old-binary checks. Add
positive Application -> Hosting/framework packaging and negative provider/
cross-slice dependency proofs without weakening existing restrictions.

Authorization/posture tests use explicit fixture identities/connection data;
D20/D21 also require finite, private ephemeral loopback Kestrel adapter proof.
They do not certify production login, external proxies/certificates or public
network isolation. Cancellation tests release and observe all held work.
No assertion may infer process termination, provider conformance or screen
accessibility from an in-process response.

## Architecture Review and Design Corrections

The bounded `hoard-architecture-review` identified one confirmed medium contract
gap and one medium cross-assembly ownership question. Both are addressed in
the design before checkpointing:

- The closed OpenAPI Problem schema now requires a safe failure phase and
  permits approved affected module/operation IDs, matching the promised
  diagnostics and D24 without raw provider records.
- Hosting now owns an explicit `BindHoardDiscovery` guard returning only the
  safe source after exact app/lease/root/catalog checks. Application does not
  access internals or substitute a DI lookup for authoritative ownership.

The review also identified the limits of TestServer exposure evidence. D20/D21
now require real private loopback Kestrel adapter checks with finite teardown;
external proxy isolation/production certificate claims remain excluded.
Coherent publication, deadline/buffer lifetime, package-framework propagation
and retained-binary proofs remain mandatory future acceptance, not results.
The specific corrections are checked for cross-artifact/schema consistency;
this is not a second architecture review or runtime approval. No unresolved
design finding or constitutional exception remains.

## Documentation, Operations and Stage Boundary

Update README and development stage guidance now. During implementation update
provider-author and package-only host guides for new opt-in APIs, protected
OpenAPI, explicit local/network posture, truthful support and restart/rebuild
journeys. Existing public docs remain accurate until those APIs exist.

Rollback removes discovery opt-in/mapping and restarts a compatible host; it
does not uninstall a package, swap a live provider or roll back provider data.
There is no schema migration, cloud/infrastructure change, deployment,
permissions-setting change, tag or release in this stage.

Planning stops after design, bounded architecture review and the shared
checkpoint. Next is `checklist`, not tasks or implementation. The existing
16/16 built-in review is not custom reviewer approval.

## Complexity Tracking

No constitutional violation requires an exception. The only new assembly
edges are the already permitted Application -> Hosting/ASP.NET Core edges.
Static OpenAPI avoids a new generation dependency; immutable in-process
publications avoid request-time callbacks, locks and supervision machinery.
