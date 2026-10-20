# F-02 Research and Decisions

**Date**: 2026-10-20 | **Status**: Planning, not implemented proof.
**Inputs**: [specification](spec.md), ratified constitution, existing F-01
source APIs/declarations and [compatibility policy](../001-provider-contracts/contracts/compatibility.md).
All planning unknowns are resolved below; package patch selection at
implementation is normal locked dependency maintenance, not an open behavior
decision.

## R-01: Preserve Registration, Add an Explicit Lifecycle Adapter

**Decision**: Keep `AddHoard`, `AddModule<TProvider>`, all markers and descriptors
unchanged. Add an independent, explicit type association from the registered
provider to a Hosting `IHoardModule` adapter. Store types only; instantiate
enabled adapters only after full metadata validation. One adapter owns
service/route/initialization/worker/stop hooks for one declaration.

**Rationale**: F-01 registrations can already represent invalid inputs and have
no constructor constraint. Adding required members to existing provider markers
would break implementers and incorrectly turn registration into activation.
The new opt-in association can require a public parameterless adapter constructor
without changing provider constructors or existing consumers. Adapter
constructors must be inert; DI services are available at initialization.

Persistence/artifact packages continue to reference only Abstractions.
Host-side adapters can reference Hosting and those packages. Protocol/identity
packages may use the approved Hosting API. No factory scanning or arbitrary
assembly loader is needed. Installed packages not registered remain outside
the runtime registry; document build inclusion instead of scanning disk.

**Alternatives considered**: Add methods to family markers (breaking); put
ASP.NET/DI callbacks into Abstractions (forbidden dependency); require every
provider family to reference Hosting (forbidden graph); instantiate providers
to inspect declarations (violates pre-construction validation).

## R-02: One Metadata Gate and One Version Policy

**Decision**: Snapshot explicit selections, adapter associations, registered
records, platform versions and required capability demands. Enforce descriptor
structure for all registrations; enforce platform/dependency compatibility,
cardinality, capability demands, and active graph only for enabled modules.
Topological order uses the ordinal smallest ready module ID.

**Rationale**: Disabled presence cannot satisfy a required dependency or confer
capabilities. Enabled optional targets are real compatibility/ordering edges.
F-01 uses `NuGet.Versioning` only in tests; promote the policy to an internal
Hosting implementation and reuse the 23 cases as regressions without referencing
a test assembly. Preserve interval syntax, explicit prerelease flags and
case-insensitive NuGet prerelease precedence; do not replace them with
`System.Version`, package restore, or a permissive custom parser.

**Alternatives considered**: F-03 reimplements a second validator (drift);
registration-order traversal (nondeterministic); auto-enable dependencies or
select defaults (forbidden); demand operational capabilities from every
declaration without explicit input (invented requirement).

## R-03: Explicit Coordinator, Not Hosted-Service Ordering Assumptions

**Decision**: A single Hosting coordinator supervises module phases and owns
admission, tracked workers and reverse cleanup. A Generic Host bridge calls it,
but an independent startup gate protects module traffic even if the HTTP server
becomes live before initialization finishes. Module adapters must not register
independent `IHostedService`/`BackgroundService` workers.

**Rationale**: Framework services, host configuration, and concurrent service
start options can affect timing. Registration order alone cannot prove all
module readiness or reverse dependency cleanup. Use public lifetime signals
to close admission on stop, and an explicit state machine for start/stop races.
No claim depends on undocumented exact server/service stop interleaving.

The worker admission unit is the complete `RunAsync` task. Once admitted, it
drains cooperatively on stop; this interface cannot promise atomic admission
for each internal worker iteration. Track outstanding requests through response
completion, retain their resource leases after drain expiry, and protect their
owners/prerequisites and root disposal until quiescence.

**Alternatives considered**: One independent hosted service per provider
(allows premature workers and ordering drift); enable traffic merely on
`ApplicationStarted` (not provider readiness); start tasks in constructors
(disabled and pre-validation side effects).

**Sources**:
[Hosted services (.NET 10)](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/host/hosted-services?view=aspnetcore-10.0),
[Generic Host shutdown](https://learn.microsoft.com/en-us/dotnet/core/extensions/generic-host#host-shutdown).

## R-04: Analyze a Supported Route Language Before Serving

**Decision**: Enabled adapters map routes only through an owned builder.
Initially support literal path segments and required unconstrained single
parameters, explicit standard HTTP methods, and default endpoint order.
Use framework route parsing, normalize case/trailing separator behavior,
ignore parameter names for equivalence, and compare framework precedence and
method overlap. Reject optional/default/complex/constrained/catch-all routes,
custom matcher policies, nondefault order and unowned module endpoints with
`UnsupportedRouteShape`, rather than claiming to prove arbitrary constraints.

**Rationale**: Runtime routing uses all candidates, policy filtering and
precedence; mere string equality misses ambiguous parameter names/casing.
ASP0022 is intentionally conservative, not a complete startup overlap solver.
The restricted language allows a complete ambiguity decision for what this
feature accepts: equal priority plus intersecting path/method languages fails;
different precedence, disjoint paths or methods passes. Public API expansion
requires proof and acceptance examples before broader protocol routes use it.

**Alternatives considered**: Detect only duplicate strings (incomplete);
wait for `AmbiguousMatchException` on a live request (too late); invent a
general regex/constraint intersection solver (unnecessary complexity);
silently choose a registered winner or force unique `Order` (violates spec).

**Sources**:
[Routing concepts (.NET 10)](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/routing?view=aspnetcore-10.0#routing-concepts),
[ASP0022 conservative conflict detection](https://learn.microsoft.com/en-us/aspnet/core/diagnostics/asp0022?view=aspnetcore-10.0).

## R-05: Absolute Deadlines, Explicit Incomplete Work

**Decision**: Validate positive finite budgets. Use monotonic `TimeProvider`
timestamps, remaining-time calculations and linked cancellation for each
supervised callback. Startup defaults to 120 seconds overall / 30 per callback;
readiness 5 seconds per aggregate assessment; shutdown 30 overall with up to
10 for draining and up to 5 per module cleanup. Do not reset outer deadlines
per module. Each lifecycle phase is dispatched at most once.

**Rationale**: Cancellation tokens are cooperative. Supervising the await
provides a finite coordination result but cannot stop arbitrary trusted code.
Non-cooperative work poisons the instance; close admission, report in-flight/
unattempted cleanup, observe eventual task faults without raw error text, and
never reuse its mutable services/router/selection. Avoid concurrent cleanup
against a still-executing activation callback. Process exit, not safe module
replacement, is the recovery boundary.

The user-approved RQ-01 follow-up explicitly includes non-completed StopAsync
as pending Phase activity after its wait times out. Preserve TimedOut for that
callback, retain owner/prerequisite/root resources, and continue independent
safe cleanup under the same deadline. Late completion/fault is observed safely;
after the stop result returns it cannot rewrite outcomes, retry cleanup or
launch deferred disposal. LC-28/29 and T048/T050..T053 retain this proof duty.

Expose a supervised `BuildHoardApplicationAsync` boundary; merely acquiring an
`await using` lease around a bare synchronous Build cannot bound a stalled
build. The composition lease owns the returned app/root and supervises eligible
disposal within remaining stop time. Pending build/callback/request/worker
activity blocks unsafe resource release and root disposal explicitly. Never
return a late poisoned build or let ordinary host disposal bypass that owner.

**Alternatives considered**: Token alone (unbounded await); a fresh shutdown
budget per module (unbounded total); thread abort (unsafe/unavailable);
claim cleanup succeeded after timeout (false); let one cleanup exception skip
all others (violates spec).

**Source**:
[HostOptions.ShutdownTimeout](https://learn.microsoft.com/en-us/dotnet/api/microsoft.extensions.hosting.hostoptions.shutdowntimeout?view=net-10.0).
The library needs its own bounded waits; framework cancellation is not evidence
that callbacks or resource release actually completed.

## R-06: Safe Diagnostic Catalogue Rather Than Exception Redaction Guessing

**Decision**: Generate bounded diagnostics from platform-owned rule codes,
validated identifiers/versions and fixed corrective-action templates.
Never include raw exception message/stack/inner exception, options, arbitrary
provider text or URLs. Unsafe identities become `registration-N` references.
Retain category, phase, path of safe IDs and a generated correlation ID.
Preserve primary failure separately from cleanup findings.

**Rationale**: Pattern-based redaction cannot recognize arbitrary seeded secrets
inside otherwise ordinary provider text. Not copying untrusted payloads makes
the zero-secret requirement meaningful. Readiness returns platform-defined
status/reason codes and declared health IDs, not arbitrary diagnostic prose.
Build/provenance information remains descriptive and cannot certify a fixture.

**Alternatives considered**: Catch/log `Exception` with message or inner
exception (leaks); return only false (not actionable); expose provider-defined
free text and hope to scrub all secrets (unprovable).

## R-07: In-Process Acceptance Plus Unchanged Foundation Evidence

**Decision**: Use TestServer and independently packed fixture modules for
startup route dispatch, worker admission, failure and restart proofs.
Keep old compile-only example/providers intact and add a separate lifecycle
example. Reuse existing architecture inspections and full locked foundation
acceptance. Introduce focused lifecycle validation tooling at implementation,
not this planning stage.

**Rationale**: TestServer exercises the application/DI/routing pipeline without
opening a socket. It cannot prove TCP drain, real production storage, native
NuGet restore or provider conformance. A tracked in-flight request barrier proves
the scoped application admission/drain contract, not Kestrel transport behavior.
New framework dependencies and independent-host locks need package proof.

**Alternatives considered**: Start a product server or provision resources
(unrequested); relabel compile-only fixtures as functioning providers (false);
write full operational conformance now (F-07/later features); run only unit
tests while ignoring packed Hosting's new shared-framework requirements
(misses compatibility/distribution impact).

**Source**:
[ASP.NET Core integration tests (.NET 10)](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests?view=aspnetcore-10.0).

## Resolved Decisions and Research Limits

This research selects signatures/ownership, route scope, ordering and budget
defaults without changing the specification. It uses current repository
constraints and first-party framework documentation, including one bounded
documentation research delegation. It makes no empirical claim about code not
yet implemented and no assertion of complete arbitrary-route analysis.
No runtime packages were installed or version locks changed.
