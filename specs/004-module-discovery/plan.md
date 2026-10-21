# Implementation Plan: Module Capabilities and Management Discovery

**Branch**: `feature/004-module-discovery` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-module-discovery/spec.md`

**Status**: F-04 implementation evidence is recorded below. The original Phase
0/1 design is retained as the contract/rationale, not a separate authority.
The specification and reviewer-owned checklists remain unchanged.
Convergence/finalization, merge and release are not part of this implementation.

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

## Implementation Evidence

F-04 now supplies the additive Hosting discovery surface and Application's
two protected management slices. The original design sections above remain
historical rationale. This evidence supersedes their future-tense status, not
the specification or normative contracts. No requirement, provider interface,
existing lifecycle signature, public snapshot constructor, constitution or
reviewer-owned checklist was changed. Requirements remain 16/16; the assisted
discovery/management requirements-quality reviews remain 20/20 each.

### Implemented authority, ownership and boundaries

`AddHoardDiscovery` freezes bounded immutable catalog/options/publication records
before evaluation/validation snapshots. The existing lifecycle coordinator
publishes one immutable reference with acquire/release semantics. Capture takes
that reference once, projects inventory and evaluates exact operation scopes
without its Gate, Snapshot, provider callbacks, configuration/secret access,
service resolution or a readiness scheduler. Stop/cleanup/late publications
override earlier readiness without changing inherited resource ownership.
Declared inclusion, registration, fixed selection, compatibility, public
provenance, tested support and observed availability remain independent.

Actual sealed owned route/method/responsibility and effective single unkeyed
owner-added service descriptors establish composition, never declaration alone.
Removed/keyed/shadowed/wrong-owner descriptors cannot prove support; factories
are not invoked. Operations evaluate their own owners/dependencies, not
unrelated aggregate health. Multi-owner contributions emit once. Management-read
alone is denied by the advertised `/fixture-inspect` operation's separate
execution policy and leaves its counter zero; explicit execution permission
permits that exact owned handler and increments its independent counter.

The Hosting-owned `BindHoardDiscovery` guard retains exact app/root/lease/source/
catalog identity. Application maps both routes before module validation and
uses separate wire DTOs. Both routes have the same policy/posture protection,
GET/query/method rules, no-store/private/no-cache/nosniff and closed safe errors.
Kestrel verification deliberately supports explicit
`UseUrls(...).PreferHostingUrls(true)`, not unseen `Listen` overrides or unknown
servers. Local mode requires verified direct loopback/no-proxy deployment;
network mode requires authenticated permission plus direct HTTPS or explicit
trusted one-hop TLS termination. Authentication needs usable defaults or
explicit registered policy schemes. Test-only exposure adapters are internal
and available only to named fixture/test assemblies.

All catalog/schema/text limits are checked before activation. Capture,
projection and bounded buffer writes check cancellation/monotonic deadline.
Encoding uses a capped `IBufferWriter<byte>` and completes before success
dispatch, including escaped-byte and oversized reservation limits. Request
cancellation/overflow owns no provider resources. Clock implementations must
be trusted inert time sources, not provider/I/O hooks.

### Case, requirement, scenario and edge reconciliation

The unchanged [acceptance tables](contracts/acceptance.md#requirement-and-outcome-coverage)
map every FR-001..FR-022, SC-001..SC-008, 22 story scenarios and 13 ordered edges
to D01..D40. Each case now maps to actual named methods in `CASE_TESTS`; complete
freshly listed fully qualified scenarios (including theory arguments) must equal
the actual passing TRX inventory. Every required suite class and both TLS/local
and forwarding-registration-order counterparts are mandatory. Missing rows,
empty/duplicate/stale evidence and skipped results fail, not count as coverage.

| Actual cases | Implementation and independent proof |
| --- | --- |
| D01..D04 | Frozen inventory, registered/disabled/included/unregistered, complete/partial absence, approved provenance and all family/authority selections; Inventory/Catalog tests and package wire bodies |
| D05..D06 | Disabled invalid operational options/secrets/ranges versus enabled gates; exact metadata/text/collection bounds reject before constructor/validator/secret/probe activity |
| D07..D08 | Exact fixture-only support versus declared/unverified/unsupported, with actual owned binding counterparts; Capability tests |
| D09..D10 | Route method/owner/responsibility and effective service descriptor proof; RouteBinding/ServiceBinding tests plus independently invoked package handlers/services |
| D11..D13 | Independent version/owner/operation scopes, multi-owner emission, required/optional dependencies and inherited incompatible-enabled rejection |
| D14..D17 | Initial registered and subsequent phase/readiness/admission/stop/cleanup/late diagnostic publication; explicit loss/recovery, preserved mapped handler and zero additional read probes |
| D18..D19 | Same authorization for both routes/trailing slashes; anonymous 401, insufficient 403, permitted 200 and fail-before-start missing policy/auth/default schemes |
| D20..D21 | Actual ephemeral loopback Kestrel, pinned generated TLS certificate, effective addresses and raw peer before forwarding in both registration orders; invalid topology rejected without public socket |
| D22..D24 | Approved public literals, omitted secret/value/source metadata, bounded inert text, closed reason/phase/correlation/corrective errors; Disclosure/Catalog/WireContract tests and captured owned telemetry |
| D25..D26 | Actual wire JSON to semantic inventory/action states; unsupported hidden, unavailable disabled, usable still separately permission-gated |
| D27..D30 | Loading/refreshing/current/empty/denied/error/stale, denial discard, failure/age expiry, inert labels/order/guidance and malformed/additive/unknown semantics |
| D31..D32 | Held capture versus explicit reassessment/stop, coherent old/new revisions; seven fresh package lifecycle identities, nine journeys, fixed selection after actual file edit and old/duplicate response rejection |
| D33..D35 | Missing/wrong-lifecycle publication, pre/mid-projection HTTP cancellation/deadline with live module calls unchanged, actual encoding cancellation/deadline, exact/over 4 MiB and UTF-8 escaping/allocation bounds |
| D36 | Actual authorized 100 x 10-contribution workload, 100 complete bodies at concurrency 10 and independent before/after activity counters |
| D37 | Advertised operation's independent authorization/counter, not an unrelated endpoint or inferred permission |
| D38 | Same-root guard, retained binary/public-source/non-web consumers, exact 18 actual graphs, approved Application/framework path and required provider/cross-slice rejections |
| D39..D40 | Embedded unchanged normative OpenAPI/actual wire/problem/method/cache protections and bounded closed telemetry/late-state guidance, not a public static copy or raw diagnostic dump |

These close US1-1..4, US2-1..5, US3-1..4, US4-1..5 and US5-1..4 and
E01..E13 under their existing case mappings. The semantic reference consumer
reads actual public bytes only, caps 4 MiB/depth 32, compares decimal-text
revisions without numeric precision loss and recognizes only its exact known
capability/version/operation/owner tuple. A failed refresh stales retained data;
401/403 discards it; receipt age over 30 seconds expires actions; old or duplicate
terminal generations/revisions cannot overwrite current lifecycle state.
No rendered WCAG/DOM/ARIA/browser acceptance or Next.js application follows.

### Measured gates and local workload

Environment: macOS 26.5.0, stable .NET SDK 10.0.203, Python 3.15.0.
The retained locked run `discovery-locked-final` recorded **122/122 declared
and executed tests** (121 composition plus one prepared architecture test),
zero skips, D01..D40, ten nonempty suites/all required classes, nine package
journeys, seven matching original wire bodies and 18 real graph scans.
All 12 private-copy runtime mutations reached their intended failing assertions
and corresponding genuine green results. Compilation errors cannot substitute
for red evidence. The private manifest/TRX/log/performance artifacts are
outside Git; only safe scope, IDs and hashes are documented here.

The required 100-module x 10-contribution, 100-authorized-read workload at
concurrency 10 produced 100 complete parsed bodies of **615,888..615,889 bytes**.
Retained-run p95 was **0.0354103 seconds**; the additional exact default command
recorded **0.066 seconds**. Constructor, readiness-probe, secret-read,
service-call, connection and active-resource deltas were all zero.
This is local TestServer fixture performance, not public-network throughput,
native-client qualification or a production SLA.

| Exact command | Result |
| --- | --- |
| `bash scripts/validate-discovery.sh --update-locks` | Passed intentional preparation, format/analyzers, all discovery/package/graph/consumer/mutation gates; original retained binaries additionally supplied privately |
| `bash scripts/validate-discovery.sh` | Passed independent fresh locked acceptance: 122 tests, 40 cases, nine journeys, 18 graphs, 12 runtime mutations, zero skips and no lock mutation |
| `bash scripts/validate-configuration.sh` | Passed: 201 tests, six boundary proofs, nine package journeys and five real Darwin interruption barriers; CFG-01..36 preserved |
| `bash scripts/validate-lifecycle.sh` | Passed: 489 tests, nine boundary proofs, seven package journeys; six independent packages and retained binary proof preserved |
| `bash scripts/validate-foundation.sh` | Passed: 42 unit, 54 architecture and 492 composition tests, zero skips; unchanged ARCH-001..008, C-01..23 and package/registration/retained proofs |
| `python3 -m unittest discover -s tests/tooling -v` | Passed 61 tests, including 17 fail-closed discovery tooling tests |

Existing runner update modes also passed before fresh default replay. Review
of all 16 modified existing locks found no removed dependency or changed
existing type/requested/resolved version; changes are expected local payload
hashes and approved Application/Hosting/project graph additions. New independent
fixture/consumer/baseline locks are tracked; default modes cannot create,
remove or mutate any lock. No third-party runtime package/version was added.

Earlier incomplete runs failed explicitly on standalone build preparation,
formatting and missing linked test input; none was reported as acceptance.
Two configuration default attempts returned a closed child-command failure;
direct fixture replay and a diagnostic full replay passed, followed by a
successful unmodified documented default replay. No reproducible cause was
established or speculative production fix made; these earlier failures are
not counted as successful evidence.

### Original binary provenance and packaging

The immutable merged pre-F-04 revision is
`7fd73267a5154583363c94e9e85b9bac7d4a16b3`. Three principal binaries were
captured before platform changes and remained hash-identical through final
compatibility execution; they were not recompiled against new platform code:

| Principal binary | Original SHA-256 |
| --- | --- |
| RetainedLifecycle | `8bbd529178abd6c7c106ca0c4bf8b64d15d987c8a7c915f4657efebbdf772981` |
| RetainedConfiguration | `5b556883aa8542fbea90ef693b720f0853ff7c668981a00dec9c2ba6966c3ce8` |
| LegacyOptions | `744043a957806145d8065186eefdfc5af1d8fe2d85df5104b143ef89a60eba66` |

The initial retained manifest omitted dependency/assets digests. Review did
not silently treat recalculated hashes as frozen provenance: original principal
hashes and source recipes were checked, every dependency DLL/inventory and
runtime JSON was independently compared with a fresh build of that exact merged
baseline, and assets' targets/libraries/dependency groups/frameworks matched.
A separate verified copy then sealed those digests without changing the
original binaries or original evidence. Strict import now requires the saved
complete dependency inventory and assets digest and rejects drift/removal/
addition/missing digests before copying. New baseline exports include them.

The unchanged option-bearing DLL is actually loaded by package-only hosts.
New source Application and non-web consumers restore only local packages and
prove transitive ASP.NET Core shared-framework requirements. Eleven feed
packages have exact local identities/hashes. Existing F-01 retained registration
proof remains required. Eighteen declared/resolved/packed/compiled graphs include
the true Application assembly, permitted wrapper classified as Host, forbidden
provider and cross-slice cases; no architecture exemption was broadened.
Metadata/artifact packages remain Abstractions-only and Core provider-free.

### Review corrections and equivalent grouping

The production architecture review identified uncapped intermediate JSON writer
allocation, missing protections on trailing-slash matches and action recognition
by operation name alone. Six actual runtime failures in
`discovery-review/architecture-red.trx` preceded the corrections; the focused
green suite is `architecture-green.trx`. Authentication-default regression
`auth-red.trx` additionally failed before the startup validation correction.
The distinct evidence-boundary review then found missing theory/class closure
and recalculated retained digests. Six runtime tooling failures in
`evidence-red.log` preceded strict scenario/import guards; `evidence-green.log`
and final full acceptance pass. Both reviews were read-only; remediation and
executed evidence are recorded here, not claimed as reviewer-run tests.

Approved equivalent groupings: normative OpenAPI is linked directly as an
embedded resource instead of duplicated under `src`; RetainedLifecycle links
the immutable merged lifecycle Program instead of copying it, with explicit
baseline blob verification; NonWebConsumer links the public Application source;
existing fixture controls/adapters and ownership scan helpers are reused.
No public arbitrary exposure adapter, second container/coordinator, runtime
assembly scanning, provider loader, scheduler or new product project was added.

### Documentation and handoff boundary

README, development/provider guides, both example guides, this plan and the
quickstart describe actual opt-in/protection, freshness, limits, permission and
restart/rollback procedures. Charter/product specification, architecture/ADR/
product diagrams, constitution, backlog, predecessor artifacts, IaC and release
guidance are unaffected: scope, dependency invariants, governance, infrastructure
and release/deployment behavior did not change. Their planned APIs remain
planned beyond these explicit implemented discovery surfaces.

Rollback removes discovery registration/mapping together and restarts a
compatible build, never swaps a live provider or reverses provider data.
Framework request logging, production authentication and external proxy
isolation still need deployment review; owned sanitized telemetry is not
framework-wide query redaction. Fixture/native/conformance/accessibility
qualifications were not expanded. No OpenTofu/apply, cloud resources, package
publication, tag, release, merge or dependent feature was authorized/executed.
The draft feature PR remains incomplete until separately invoked convergence
and finalization; this implementation invocation stops before `converge`.
