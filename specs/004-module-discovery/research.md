# F-04 Research and Decisions

**Date**: 2026-10-21

**Status**: Resolved planning decisions, not implemented behavior.

## R1 - Reuse the actual authorities

**Decision**: Reuse existing registration, configured composition, lifecycle
and route sealing. Add discovery-only associations in Hosting; place management
slices in Application with its explicitly approved Hosting/HTTP dependencies.

**Repository evidence**: `HoardModuleRegistration` stores declaration/type only.
`HoardValidatedComposition` freezes selection/registration/edges and service
snapshot. `HoardValidatedConfiguration.Consume` checks exact unchanged builder
ownership. `HoardServiceComposition` owns lifecycle/root resources.
`HoardModuleEndpointBuilder.Seal` and `HoardRouteOwnershipValidator` already
establish actual mapped responsibilities and reject unsupported/ambiguous routes.

**Rationale**: Discovery must explain those decisions, not construct providers,
revalidate operational settings, build a second container or repair selection.
Register discovery before evaluation snapshots services; mapping after build
must not add service registrations.

**Alternatives considered**: Disk/package scanning cannot establish trusted
inclusion and introduces I/O/loading; separate validators/coordinators duplicate
authority; putting management endpoints in Hosting violates ownership.

## R2 - Explicit inclusion and tested support, not automatic certification

**Decision**: A host-authored immutable catalog may be `complete` or `partial`.
Combine its positive inclusion records with registrations. Only complete
inventory establishes absence. A registered declaration is positive evidence
for that module, not proof that the entire inventory is complete. Require an
explicit operation/version/owner support record with bounded evidence IDs and
`fixture` or `production` scope before advertising support.

**Rationale**: Provenance, compatibility, readiness, route mapping and qualification
are independent. No existing fixture provides production/native-client evidence.

**Alternatives considered**: Equating a package, ModuleSupportStatus or green
health with support makes false claims. A general certification engine is
unnecessary; host assertions plus mandatory executable support tests suffice.

## R3 - Publish one coherent state without request-time probes

**Decision**: Add an internal immutable publication view to the current
coordinator, updated under its existing lock on every discoverable transition.
Include revision, lifecycle/composition identity, last publication time and last
completed assessment time. Requests capture a single published reference and
derive availability from that revision and fixed composition/catalog evidence.

**Repository evidence**: `IHoardLifecycle.Snapshot` currently copies coherent
state under the coordinator lock but has no revision/timestamp fields.
`AssessReadinessAsync` invokes callbacks and therefore is forbidden on discovery
reads. Runtime assessment updates readiness without automatically closing
startup admission or removing routes; stop closes admission before cleanup.

**Rationale**: New reads must not block behind trusted callbacks, mix lifecycle
revisions or claim that refresh performs a new health assessment.

**Alternatives considered**: Reading individual mutable properties races;
calling assessment probes providers; new timers/schedulers imply continuous
monitoring; adding required interface members breaks already compiled consumers.
Keep existing public snapshot constructors/interfaces unchanged.

## R4 - Evidence for actual routes and services

**Decision**: Route bindings refer to owner/responsibility/method in the sealed
actual route ledger. Service bindings refer to opaque host association IDs and
an exact, effective owner-added unkeyed service descriptor. Capture registration
ownership inside existing supervised ConfigureServices, then verify that the
descriptor remains the effective single-service registration at final build.
No `GetService`, factory execution or provider callback is used for discovery.

**Rationale**: Declarations and type existence alone do not prove composition;
another owner's shadowing registration cannot fulfill an operation.

**Alternatives considered**: Reflecting/resolving services can construct them;
assuming all declared endpoints are present is untruthful; a generic service
dependency graph or keyed/enumerable binding engine exceeds F-04.

## R5 - Protect both fixed routes with explicit posture and read policy

**Decision**: Use two literal GET routes and the same explicit
`Hoard.Management.Read` authorization boundary, including the description.
Discovery opt-in defaults to no authorized exposure until a host deliberately
selects `local-loopback` or `secured-network` and configures its policy/posture.
Local mode requires verified loopback-only bindings and direct loopback peers,
no proxy/forwarded-header mode and an explicit no-proxy deployment assertion.
Secured network requires authenticated read permission and HTTPS, directly or
through explicitly trusted proxy configuration; no header-only identity scheme.

**Rationale**: Route authorization does not automatically protect OpenAPI.
Network mode must never inherit the local anonymous exception. Socket topology
cannot be proven from a Host header or a forwarded original-client address.
Unknown binding/posture fails closed; TestServer uses a test-only verifier.
A local proxy that deliberately conceals forwarding is indistinguishable from
a local caller, so proxy isolation is an operator prerequisite, not a claimed
framework guarantee.

**Evidence boundary**: Use actual private ephemeral loopback Kestrel adapter
cases for effective addresses, raw-peer capture ordering and HTTPS recognition.
Mock TestServer identities alone cannot establish those facts. Test-only
certificates are generated in memory and pinned by that client; all listeners
have finite teardown. External proxy/certificate isolation remains an operator
responsibility, not certification from this fixture.

**Alternatives considered**: IP-only checks authorize loopback reverse proxies;
trusting all forwarded headers is unsafe; automatic anonymous fallback violates
the requirement; implementing OIDC/tokens would preempt later identity features.

**Primary references**:

- [Minimal API route groups and authorization](https://learn.microsoft.com/aspnet/core/fundamentals/minimal-apis?view=aspnetcore-10.0)
- [Minimal API security](https://learn.microsoft.com/aspnet/core/fundamentals/minimal-apis/security?view=aspnetcore-10.0)
- [Proxy and load-balancer configuration](https://learn.microsoft.com/aspnet/core/host-and-deploy/proxy-load-balancer?view=aspnetcore-10.0)
- [Unknown proxies and forwarded headers](https://learn.microsoft.com/aspnet/core/breaking-changes/8/forwarded-headers-unknown-proxies)

## R6 - A fixed protected OpenAPI document

**Decision**: Embed a fixed OpenAPI 3.1 document in Application and serve it at
one literal path. The design's [normative document](contracts/openapi.json)
contains closed wire shapes and safe examples; implementation verifies deployed
description/model conformance. Do not inject deployment inventory into it.

**Rationale**: A fixed small API needs no new OpenAPI generator dependency.
Literal paths fit F-02's existing route validator, unlike a default route with
complex parameter segments. Authorization on the data endpoint does not secure
the description endpoint automatically.

**Alternatives considered**: Built-in `AddOpenApi`/`MapOpenApi` is appropriate
for broader future management APIs but introduces a package/document pipeline
now. Public Swagger UI/static-file hosting would create a bypass surface.

**Primary references**:

- [ASP.NET Core OpenAPI generation](https://learn.microsoft.com/aspnet/core/fundamentals/openapi/aspnetcore-openapi?view=aspnetcore-10.0)
- [OpenAPI 3.1.1 specification](https://spec.openapis.org/oas/v3.1.1.html)

## R7 - Allowlisted disclosure, bounded JSON, inert presentation

**Decision**: Freeze a host-approved public presentation catalog. Copy only
canonical known identities, enums, booleans, numeric constraints and explicitly
approved non-secret literal text/defaults. Never automatically copy arbitrary
descriptor descriptions, URLs, allowed values, examples or F-03 input/report
objects. Suppress unapproved metadata with a safe reason. Encode typed DTOs as
`application/json` using default JSON escaping and a capped 4 MiB private buffer.
Future consumers render text, never markup.

**Rationale**: Neither regex validation nor JSON/HTML escaping can recognize
arbitrary credentials in otherwise valid strings. Secret privacy comes from
the explicit projection boundary and absence of runtime/configuration values.
Approved literal content is trusted host code subject to review, not an
automatic secret detector or sandbox for malicious providers/host code.

**Alternatives considered**: Serializing domain records leaks unrelated fields;
filtering a blacklist cannot prove secret removal; relaxed JSON escaping or
HTML interpretation adds risk. Unknown additive descriptive fields are ignored
by consumers; unknown action/state meanings remain non-invocable.

**Primary references**:

- [System.Text.Json encoding](https://learn.microsoft.com/dotnet/standard/serialization/system-text-json/character-encoding)
- [UnsafeRelaxedJsonEscaping cautions](https://learn.microsoft.com/dotnet/api/system.text.encodings.web.javascriptencoder.unsaferelaxedjsonescaping)
- [System.Text.Json migration/default behavior](https://learn.microsoft.com/dotnet/standard/serialization/system-text-json/migrate-from-newtonsoft)

## R8 - Bounded work is not preemptive termination

**Decision**: No pluggable async observation collaborator or per-request
Task.Run/timeout race. Use a lock-free immutable source, bounded loops with
deadline/token checks at least every 64 items and during encoded writes.
Fail before headers if projection/encoding misses the two-second default
budget. Network writes remain cancellation-aware, not a hard transport deadline.
Host authentication/middleware must itself cooperate with cancellation.

**Rationale**: Request timeout middleware signals cancellation; it does not kill
CPU-blocking trusted code or unresponsive transport. F-04 avoids dispatching such
collaborators in its read path rather than pretending they can be terminated.

**Alternatives considered**: A timeout around arbitrary callbacks leaves work
and resources alive; streaming a partial successful inventory conceals failure;
unbounded buffers/queues violate bounded inspection.

**Primary reference**: [Request timeouts](https://learn.microsoft.com/aspnet/core/performance/timeouts?view=aspnetcore-10.0).

## R9 - Reference consumer and bounded proof, not a product UI

**Decision**: A package-independent JSON-only .NET fixture validates wire
compatibility, labels, action eligibility, refresh generations and semantic
presentation records. Use TestServer/test authentication handlers for endpoint
logic, dedicated private loopback Kestrel exposure-adapter cases and separate
package-only baseline/custom lifecycle journeys.

**Rationale**: This proves capability-driven decisions without selecting a
premature Next.js version, generating manifests or claiming rendered WCAG/TLS
certification. Actual browser focus/layout/screen-reader acceptance remains
the later console's obligation.

**Alternatives considered**: A new Next.js app expands scope; tests consuming
Hosting objects can hide wire incompatibility; TestServer is not Kestrel/TLS.

**Primary reference**: [Integration tests and mock authentication](https://learn.microsoft.com/aspnet/core/test/integration-tests?view=aspnetcore-10.0).
