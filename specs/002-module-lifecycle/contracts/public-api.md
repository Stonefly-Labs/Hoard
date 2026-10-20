# F-02 Proposed Public Library Contract

**Status**: Planned additive APIs, not implemented methods or published
packages. No full implementation bodies are specified here.

## Existing Surface and Compatibility

Keep F-01 `AddHoard(IServiceCollection)`, `AddModule<TProvider>(ModuleDescriptor)`,
`HoardBuilder.Services`, `HoardModuleRegistration`, family marker interfaces and
all declaration properties unchanged. Old callers still record metadata/types
without enabling, validating, constructing or running modules. No required
constructor constraint, interface member, declaration field, or implicit
validation is added to those APIs.

New lifecycle use is explicit and opt-in. An old provider may participate via a
host-side adapter without recompiling it. Selecting a registration with no
lifecycle association in the new API fails with `MissingLifecycleAdapter`;
ordinary registration-only use does not. Prove old source and already compiled
registration consumers against new local packages; rebuild alone is not binary
compatibility evidence.

## Ownership and Package Graph

| Owner | Proposed surface / dependency |
| --- | --- |
| Abstractions | Existing BCL-only descriptors/markers unchanged; no DI/HTTP/task callbacks added |
| Hosting | Selection, validation result/composition, budgets, adapter association/interface, owned routes, coordinator/snapshots, HTTP/Generic Host bridge |
| Core / Application | No F-02 implementation or concrete-provider dependency |
| Protocol/Identity fixtures | May implement approved Hosting adapter API; remain independently packaged |
| Metadata/Artifact fixtures | Abstractions-only; host-side adapters reference their public provider APIs |
| LifecycleHost | Hosting plus explicit fixture packages; owns metadata/artifact adapters and explicit selection |

Hosting will use an ASP.NET Core framework reference and `NuGet.Versioning`.
Do not leak version-library types in its public input/result records: version
and interval strings retain the F-01 policy. Document that operational Hosting
consumers need the ASP.NET Core shared framework, and test framework-reference
propagation for packed and standalone consumers. If a non-web registration-only
consumer now requires the shared framework, record this distribution dependency
change explicitly; do not call it a source/binary API break or conceal it.
No new package version is published or release transition authorized here.

## Adapter Registration and Callbacks

New extension on `HoardBuilder`:

```csharp
HoardBuilder AddModuleLifecycle<TProvider, TModule>()
    where TProvider : class, IHoardProvider
    where TModule : class, IHoardModule, new();
```

It records only provider/adapter types. It does not instantiate `TModule`,
register operational services, inspect assemblies on disk, or call factories.
The provider must already have exactly one matching F-01 registration.
Detect invalid/duplicate associations during metadata validation, not through
last-registration-wins semantics.

`Hoard.Hosting.Lifecycle.IHoardModule` is a new opt-in interface:

```csharp
void ConfigureServices(IServiceCollection services);
void MapEndpoints(HoardModuleEndpointBuilder endpoints);
ValueTask InitializeAsync(IServiceProvider services, CancellationToken cancellationToken);
ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken cancellationToken);
Task RunAsync(CancellationToken stoppingToken);
ValueTask StopAsync(CancellationToken cancellationToken);
```

All six methods are explicit on new adapters; an adapter with no services,
routes or ongoing work supplies an inert completion for that phase. This does
not add required members to old providers. Constructors are parameterless and
inert; use built services at initialization, never construct a temporary service
provider during configuration.

Adapters own their phase-acquired resources until `StopAsync` completes. They
must record acquisitions before possible failure, release partial resources,
and not delegate the same ownership to container disposal. Services owned by
DI retain standard DI ownership and are disposed once by their owner; module
stop releases operational activity, not a second disposal of container-owned
objects. Never add a preconstructed owned resource to DI and also dispose it
as adapter-owned. Cleanup ownership and dependency availability must be
documented in each adapter's proof.
The coordinator tracks a non-completed StopAsync as pending Phase activity.
Its wait timing out does not complete the callback or release its owner's,
prerequisites' or root resources; independent safe cleanup may continue under
the same stop deadline. Preserve TimedOut separately from unsafe omissions.

ConfigureServices and MapEndpoints are synchronous, bounded composition
callbacks, not permission to start ongoing work, external connections, or
schema migrations. They may create local composition resources, which the
adapter must release on failed composition. A throwing constructor must clean
its own not-yet-returned resources. ConfigureServices may register only enabled
services; direct provider construction, background-task launch, nested container
build, and independent `IHostedService` registration are prohibited. The
coordinator inspects the service descriptor delta for independent hosted
workers; trusted arbitrary delegate/static code is not sandboxed.

`RunAsync` owns any ongoing module worker, starts only after complete selected
readiness, observes the shared stop token, and completes when stopped. No-worker
modules return a completed task. Unexpected worker failure makes the lifecycle
failed/not-ready and requests host shutdown with a safe diagnostic, never an
automatic restart/replacement loop. Initialization may do bounded preparation
under explicit provider operational policy, not uncontrolled migration.
The admitted unit is the single `RunAsync` callback for this module, not each
iteration inside arbitrary provider code. Stop admits no new worker callback
and cancels the already admitted task, whose remaining execution is in-flight
work to drain. The contract does not claim atomic per-iteration admission.

## Host Composition Boundary

Proposed public extensions/results, all in Hosting:

| API | Agreement |
| --- | --- |
| `ValidateComposition(selection, versions, options)` on `HoardBuilder` | Synchronous metadata-only `HoardCompositionValidation`; returns either a valid immutable composition or safe errors; no activation |
| `ComposeHoardModulesAsync(composition, cancellationToken)` on `HoardBuilder` | Before host build, verify unchanged registry, construct enabled adapters and configure services under supervision; return single-use `HoardServiceComposition` or throw sanitized `HoardLifecycleException` after cleanup |
| `BuildHoardApplicationAsync(serviceComposition, cancellationToken)` on `WebApplicationBuilder` | Supervise this builder's one host build against the existing startup deadline; record pending build activity and safe failures, never publish a late/poisoned result |
| `MapHoardModulesAsync(serviceComposition, cancellationToken)` on `WebApplication` | After build and before start, map/inspect owned routes and install startup/stop admission protection; failure triggers coordinated cleanup; no initialization/traffic yet |
| `HoardServiceComposition : IAsyncDisposable` | Owns the lifecycle lease from first adapter construction and the application returned by supervised build; disposal shares stop, then supervises root disposal only if safe |
| `IHoardLifecycle` resolved from built DI | Read-only snapshot, cancellation-aware `AssessReadinessAsync`, shared `StartAsync` / `StopAsync` results; Generic Host bridge is the normal caller |

Acquire the composition with `await using`, then call the supervised build
extension instead of bare `builder.Build()`. The extension verifies builder/
composition identity, consumes the same absolute startup deadline, and records
the build task before dispatch. If build fails/times out, it returns a sanitized
failure and poisons the lifecycle; a still-running build cannot publish an
application, readiness or operational routes. Its completion/fault is observed
safely; pending build usage prevents concurrent unsafe cleanup/disposal.

Compose registers the single framework bridge and shared lease as an externally
owned DI instance before build. The lease alone owns application/root disposal;
container disposal must not recursively own the lease. Start/stop the returned
app explicitly through its normal host APIs and retain the lease until stop.
Do not independently call app disposal or `RunAsync` (which may dispose the
host) around this ownership boundary. Lease disposal first coordinates stop,
then disposes the app/root only when admitted requests, workers, build and
activation/cleanup callbacks are quiescent, including StopAsync tasks whose
coordination waits timed out. If work remains, report root disposal
NotAttemptedUnsafe rather than destroying resources still in use. A disposer
that itself stalls is supervised and reported incomplete; no forced termination
is claimed.
Observe late cleanup completion/fault without raw payloads; after the shared
stop result is returned, do not rewrite its outcomes, retry cleanup, or start
deferred dependency/root disposal.

Failure before lease return is cleaned internally; failure afterward is covered
by lease disposal, including the supervised build path.
Mapping checks that the application uses that exact composition instance;
missing mapping fails bridge startup rather than bypassing the route gate.

Input/model property types and invariants are in [data-model.md](../data-model.md).
Expected validation failures return explicit errors; misuse such as null
arguments uses standard argument exceptions. Activation exceptions have safe
catalogue data only, with no raw `InnerException`. Do not log swallowed provider
exceptions or return success after failure; retain correlation and category.

## HTTP Surface

The owned endpoint builder exposes mapping by declared responsibility ID,
method list, supported pattern, and ASP.NET Core `RequestDelegate`.
It supplies immutable owner metadata and forbids caller mutation of route
matching/order/source. Endpoint handlers remain inside protocol feature slices;
they may call approved Core/Abstractions contracts, not another slice's internals.

No management/liveness/readiness HTTP endpoint is delivered by F-02. Tests and
future authorized management adapters read `IHoardLifecycle` snapshots.
Startup-blocked normal module requests receive a fixed safe 503 result; disabled
routes are unmapped and return the host's ordinary not-found behavior, not a
pretend disabled-module response. The runtime startup gate covers module traffic
independently of Generic Host server ordering.

No authentication/authorization system is added. The owned builder must preserve
host middleware and required host access policy; it must not create an anonymous
management bypass. Existing central security requirements still apply to any
future listener or protocol handler.

## Evidence and Documentation Obligations

Run [acceptance.md](acceptance.md), compile and execute only the fixture lifecycle
example, preserve F-01's compile-only example, and prove the new packed dependency
graph. Document framework requirements, fixed selection, budgets, safe error
catalogue, partial cleanup, restart and explicit recovery. No fixture, declared
capability or successful registration implies a production support claim.
