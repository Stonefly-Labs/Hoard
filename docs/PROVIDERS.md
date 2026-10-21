# Provider author guide

F-01 supplies source-level .NET 10 declarations and registration-only composition
at local acceptance package version `0.1.0`. Nothing is published to nuget.org.
There is no working cache, protocol, persistence, byte store, authentication,
or certification. F-02 now adds opt-in fixture-tested module lifecycle in
Hosting; this does not implement provider operations. Start with the
[compile-only host](../examples/CustomHost/README.md) and
[validation quickstart](../specs/001-provider-contracts/quickstart.md).
For lifecycle use, see the [package-only lifecycle host](../examples/LifecycleHost/README.md).

## Public ownership and authoring

`Hoard.Abstractions` owns immutable sealed module records in
`Hoard.Abstractions.Modules` and the `IHoardProvider`, `IProtocolProvider`,
`IMetadataProvider`, `IArtifactProvider`, and `IIdentityProvider` markers in
`Hoard.Abstractions.Providers`. All are BCL-only. Markers grant no operations or
permissions. Core references Abstractions only; Core/Application have no
operational members yet. Hosting owns DI/HTTP integration and internally uses
NuGet.Versioning; its package propagates the ASP.NET Core shared-framework
requirement, including to non-web registration-only consumers. This is a
deployment prerequisite change, not a change to the old registration signatures.

The [public API contract](../specs/001-provider-contracts/contracts/public-api.md)
and [declaration model](../specs/001-provider-contracts/data-model.md) specify
every field. Expose a static immutable `Declaration` as the
[protocol fixture](../tests/fixtures/providers/Protocol/ProtocolProvider.cs)
does; explicitly populate required properties and use `[]` for empty immutable
collections. IDs follow `[a-z0-9]+([.-][a-z0-9]+)*`. Versions have three SemVer
components. Metadata describes dependencies, capabilities, configuration
requirements, endpoint/health responsibilities, and provenance, not resolved
secrets, route delegates, probes, current health, or selected implementations.
Source/support URLs must be public and contain no credentials or private details.
`Fixture`, `Community`, and `MaintainerSupported` are provenance declarations,
not certification. The five test fixtures advertise no operational capability.

`services.AddHoard().AddModule<TProvider>(declaration)` records an immutable
`HoardModuleRegistration` containing the supplied declaration and type token.
It preserves duplicates, requires no public/default constructor, and neither
constructs a provider nor builds a container. Null arguments throw
`ArgumentNullException`. Invalid IDs, default arrays, category/type disagreement,
version conflicts, and invalid selections are representable for later
validators; registration is not validation, enablement, readiness, or fallback.

## Composition, family selection, and trust

A future curated distribution will configure only already bundled providers.
A custom distribution must reference packages and explicitly register types,
then rebuild, redeploy, and restart an operational host. Build-time NuGet restore
is not runtime installation. No arbitrary assembly loading, runtime downloads,
hot installation/replacement, sandbox, or marketplace is delivered.
Provider code, including static metadata getters, is trusted in-process code
with the host's privileges. Packaging does not isolate malicious code.

Multiple protocols and identity schemes may eventually coexist. Initially
there will be one authoritative metadata provider and one artifact provider;
F-01 does not enforce selection/cardinality. Authentication remains distinct
from centralized authorization. Provider implementations must not depend on
other concrete providers, even of the same family. SDK/EF/schema/migration
details stay private to their owning provider, never Core or endpoint contracts.
Do not expose `DbContext`, `IQueryable`, transaction/connection objects, vendor
SDK objects, HTTP context, delegates, or arbitrary payload escape hatches in
provider-neutral declarations.

Cache identity/auth partitioning, freshness, safe upstream/SSRF policy,
integrity and verified atomic publication, bounded asynchronous streaming and
cancellation, single-flight, reference-safe deletion/GC, authorization, and
shared audit/telemetry remain centralized Core/security/Hosting responsibilities.
Markers never authorize a provider to bypass or duplicate these invariants.
No rename, portable transaction, NoSQL interchangeability, or cross-store
atomicity guarantee follows from a marker.

## Compatibility and release obligations

The [normative policy and all 23 examples](../specs/001-provider-contracts/contracts/compatibility.md)
distinguish **module**, **host**, and **abstractions** release versions.
Dependencies constrain the target module's version. Platform ranges separately
constrain host and abstractions, not an arbitrary custom executable's version.

Only exact `[1.2.3]` and bounded intervals such as `[1.2.0,2.0.0)` are accepted
by the written policy. Bounds are explicit three-part versions; inclusive and
exclusive bounds are supported. Missing, empty/reversed, unbounded, bare-minimum,
and floating ranges are unsupported. Build metadata does not affect precedence;
prerelease labels compare case-insensitively. Prereleases precede their stable
release and require a separate explicit opt-in for each host, abstractions,
or dependency axis. A `-rc` bound or prerelease module version does not opt in.
Restore success and registration alone prove none of these compatibility claims.

A required target must be enabled and compatible. An absent, installed-disabled,
or registered-disabled optional target is unavailable: no integration/capability
claim or active dependency edge. An enabled optional target must meet its range
and prerelease flag, even if the integration is allegedly unused. Incompatibility
makes the composition unsupported. Never silently disable a module/integration,
ignore a dependency, fall back, or substitute another provider. Operators must
explicitly change selection or install a compatible version and revalidate.
F-01 classifies examples; F-02's explicit validator now enforces these rules.
F-03 will resolve configuration into that same gate, not duplicate it.

## Opt-in lifecycle

Add `AddModuleLifecycle<TProvider, TModule>()` after the provider registration.
It records types only. `IHoardModule` in `Hoard.Hosting.Lifecycle` explicitly
implements ConfigureServices, MapEndpoints, InitializeAsync,
CheckReadinessAsync, RunAsync and StopAsync. Constructors are parameterless and
inert. Metadata/artifact packages remain Abstractions-only; their adapters live
in the host. Protocol/identity packages may use approved Hosting APIs.

Supply `HoardStartupSelection`, `HoardPlatformVersions` and
`HoardLifecycleOptions` to `ValidateComposition`. No IDs/defaults are inferred:
exactly one enabled Metadata and Artifact must equal their authoritative IDs;
zero or more protocols/identity schemes are permitted. Registry structure is
checked even for disabled declarations; active compatibility applies only to
selected entries. Validation runs no constructors, factories, callbacks or I/O.
Malformed records, unavailable required targets, incompatible enabled optional
targets, cycles and unsatisfied target-specific capabilities fail explicitly.

Acquire `ComposeHoardModulesAsync` with `await using`, call
`BuildHoardApplicationAsync`, then `MapHoardModulesAsync`, then normal
`app.StartAsync` / `app.StopHoardApplicationAsync(lease)`. Do not independently
call bare app StopAsync, dispose the app or use app.RunAsync. One external lease
shares the actual framework-stop task and owns root disposal; a canceled
ApplicationStopped token does not prove its callbacks finished.
`IHoardLifecycle.StopAsync` shares module cleanup only; its root outcome is
`NotAttemptedOwnerPending` until external-owner disposal when safe. Inspect
`lease.StopResult` after disposal; incomplete disposal throws a sanitized
`HoardLifecycleException` and preserves that result. Repeated disposal shares
one operation, not a second cleanup attempt.

ConfigureServices/MapEndpoints are bounded composition, not worker/I/O hooks.
Do not build nested containers or register independent `IHostedService`s.
Adapters own phase-acquired resources, including partial failures; throwing
constructors clean their own pre-return allocations. DI retains its own
resource ownership. RunAsync is one admitted callback after complete selected
readiness, not a per-iteration scheduler; no-worker completion is valid.
Worker faults atomically close admission and request shutdown, without retry.
Host lifetime resolution and synchronous stopping notifications run outside the
lifecycle state lock. They are tracked before stop begins as global Phase
activity: a pending notification or lifetime-cancellation callback protects all
module resources and the root while snapshot/stop coordination remains bounded.

Map declared responsibilities through
`routes.Map(responsibilityId, pattern, methods, RequestDelegate)`.
Only absolute literals and required unconstrained whole-segment parameters,
explicit uppercase standard methods (HEAD explicit), and default order are
supported. All declared responsibilities need mappings. Equal framework
precedence with intersecting paths/methods fails, including same-owner,
renamed-parameter, case and trailing-slash equivalents. Disjoint methods/paths
and a unique more-specific literal pass. Constraints, defaults, optional/
complex/catch-all paths, dynamic/custom matching and unowned ambiguity fail.
Host middleware and access policy remain outside and apply normally; no
management/health endpoint or anonymous policy is added. Finalized routes must
not be changed while the lifecycle runs.

Readiness is neither liveness nor startup admission. All enabled modules must
initialize and explicitly report ready, including required health observations,
before workers/owned requests are admitted. Disabled modules have no callbacks,
routes or synthetic connection attempts. Later assessment can report health
loss/recovery for the fixed selection without automatically closing admission,
draining, replacing or disabling modules. Caller cancellation only cancels an
individual shared-operation wait; compose/build/map cancellation latches failed
startup. Stop permanently closes admission before cancellation/drain/cleanup.

Defaults are 120s absolute startup, 30s activation callback, 5s aggregate
readiness, and 30s total shutdown including at most 10s drain and 5s per module
cleanup. All durations must be positive/finite; inner waits never expand the
remaining outer budget, including synchronous callbacks/build and inter-phase
pauses. `TimeProvider` supplies monotonic deadlines.

Cleanup is reverse dependency order, once per returned adapter. Failed,
TimedOut, NotAttemptedBudgetExhausted and UnsafePendingCallback remain distinct
from Completed/NotEntered. Root outcomes additionally distinguish framework/
owner pending, unsafe omission, budget exhaustion, failure and timeout.
Outstanding requests retain ownership through response completion (including
handled errors). Supervised build installs the internal completion boundary
before host startup filters/middleware. Admitted leases release only after
their response-completion callbacks and handler callbacks finish, in reverse
registration order, not on handler return. Host middleware/access policy still
applies; no caller-installed admission middleware is needed.
Workers, build, activation, cleanup and cancellation callbacks
retain resources they may still use. A timed-out StopAsync does not release its
owner/prerequisites/root. Independent safe cleanup may continue under the same
deadline. Late completion cannot rewrite returned outcomes, retry or trigger
deferred disposal. Trusted non-cooperative code may require process termination.

Diagnostics expose fixed rule/action codes, safe IDs or registration ordinals,
phase, correlation and primary/cleanup classification, not provider exception
text, inner exceptions, options or URLs. Messages/actions are at most 512
characters; paths at most 32 IDs; diagnostic lists at most 100 with explicit
omitted counts. IDs are bounded to 128 characters, versions/publishers/option
keys to 256, ranges to 512, descriptions/URLs to 2048, and each nested descriptor
collection to 1000. These are structural limits, not production scalability
claims. Snapshots report IncludedByRegistration, fixed selection, phase and
readiness, never exhaustive installed inventory or certified capabilities.

Lifetime and readiness/cleanup-timeout cancellation faults use the safe
`CancellationFailure` code, originating owner/phase, fixed corrective action
and lifecycle correlation, classified as additional cleanup diagnostics.
They preserve the primary failure and are recorded before cancellation activity
is released. Correct the trusted module's cancellation callback before starting
a fresh lifecycle. Completed faults are not still-running activity: successful
resource release and a cancellation diagnostic can coexist. A fault after a
bounded result appears in a later snapshot only; it cannot rewrite that result,
retry cleanup or trigger deferred disposal.

Supervised startup, readiness, cleanup, framework-stop and root-disposal faults
are recorded once with their originating owner/phase before tracked activity
is released. A fault after its bounded wait is abandoned reports additional
`LateCallbackFailure`, even before shared stop completes; directly awaited
faults keep their normal category without duplication. Worker faults during
shutdown are also additional diagnostics, not a second shutdown request.
Cooperative cancellation is not a new eventual fault. Late reporting never
revises returned resource outcomes or starts deferred disposal. The lease
rechecks the original deadline after framework stop; if exhausted, root
disposal remains NotAttemptedBudgetExhausted rather than being dispatched.

Changing a bundled choice needs a fresh validated lifecycle, not a rebuild.
Adding an absent package needs reference, registration/adapter, rebuild,
redeploy and restart. Invalid replacement never rolls back silently; explicitly
restore the prior coherent set and start a new instance. Stop is not schema/data
rollback, crash recovery or forced termination.

Assess source compatibility for **consumers and implementers**, binary
compatibility for previously compiled supported modules, and behavioral
compatibility for documented obligations. Required member additions, removals,
signature/identity changes, and stronger publication/auth guarantees are breaking
even when a revised consumer compiles. Stable breaking contracts require a
major transition; pre-1.0 breaks require an explicit minor transition, e.g.
`0.1` to `0.2`, and updated narrow ranges. Patch releases remain nonbreaking;
never infer blanket `0.x` interoperability.

Before a breaking release, document affected members/behaviors, consumer and
implementer source impact, old-binary impact, old/new compatibility ranges,
provider/host code/configuration changes and rebuilds, qualification evidence,
and rollback/backup instructions. Publish migration guidance with that release.
Retain a coherent previous host/contract/provider set for rollback; do not
relabel incompatible binaries as supported. Local compile tests do not authorize
package publication or replace later behavior/conformance qualification.

## F-03 configuration boundary

`Hoard.Hosting.Configuration` adds an opt-in pre-activation boundary. Existing provider
interfaces/descriptors, Abstractions/Core/Application and lifecycle signatures
are unchanged. Metadata/artifact providers keep their Abstractions-only edge;
the composing host owns the new option descriptions.

`AddModuleConfiguration<TProvider>(HoardModuleConfiguration, HoardOptionValidator?)`
records an inert association. Fields must bijectively match descriptor keys and
required/secret flags; duplicate/orphan/colliding associations fail inspection.
Types are String, Boolean, Integer, Address and Secret, with version 1 metadata.
Informative defaults/examples are not injected into effective settings; secret
defaults/examples are forbidden. Registration/inspection invokes no provider,
adapter or validator. During evaluation, the existing F-02 composition gate
owns graph/cardinality/version/capability decisions. All active ordinary rules
and Public callbacks finish before any secret resolution. Secrets callbacks
receive only their owner's resolved handles. Disabled modules receive neither
callback nor secret read. Validators return declared field/rule identities,
not arbitrary messages; exceptions and malformed results become safe failures.
Composition failures retain a closed CompositionRule, known registered owner,
effective selection-source provenance and a bounded DependencyPath. Unknown
IDs/path elements become generated categories, even if their syntax is valid;
raw versions/capability targets and collaborator messages are never forwarded.

`HoardConfigurationInput` takes explicit Defaults, optional file, arguments and
an environment dictionary/read adapter. Inputs and owner options have redacted
display and no public value-bearing serialization; explicit secret-handle access
is not process isolation or guaranteed managed-memory zeroization. The input
does not capture ambient process credentials. See the
[development guide](DEVELOPMENT.md#f-03-configuration-implementation) for
snapshot ceilings, source grammar, finite coordination and pending retention.

`EvaluateConfigurationAsync(input, platformVersions, lifecycleOptions,
configurationOptions, cancellationToken)` returns a safe report and, only on
complete success, an unconstructible `HoardValidatedConfiguration`. Consume it
once with `builder.ComposeHoardModulesAsync(proof, token)`, then use the existing
build/map/start/stop/lease-disposal sequence. `await using` the evaluation
disposes an unused proof; after transfer, only the F-02 lease owns the inputs.
Foreign/stale/disposed/used proofs fail before construction. Do not mutate a DI
service collection concurrently with composition; trusted host code is not
sandboxed. Fresh restart uses a fresh builder, evaluation and lifecycle.

A configurable selected adapter implements `IHoardConfiguredModule` in addition
to `IHoardModule`. `ConfigureOptions(HoardModuleOptions options)` runs immediately
before ConfigureServices under the same supervised F-02 phase/deadline. It
stores/maps only its own typed ordinary values and explicitly accessed secret
handles; it must not connect, start workers, log/serialize credentials or
retain a host-wide resolver. Use GetString/GetBoolean/GetInteger/GetSecret, with
`GetSecret(key).Reveal()` only at intentional sensitive-use boundaries.
Required/secret flags must match the descriptor. Zero-field legacy adapters
need no new interface. Enabled opt-in registrations reject bare legacy compose
as ConfigurationRequired; opt-out F-02 source/binaries remain supported.

Environment names use OS lookup semantics with no fallback; omitted supplied
environment is empty. File targets are absolute, bounded strict UTF-8 without
BOM/NUL; at most one final LF and preceding CR are removed. Empty/whitespace,
unavailable or oversized values reject. Deployment symlinks to regular files
work; zero-length directory/device/pipe inputs fail before reading, and all
dispatched reads remain bounded. Values are frozen until explicit restart.
Release clears owned secret references after the last actual supervised user,
not merely after a timed wait. This is not managed-memory zeroization or a
malicious-provider/enumerator/clock sandbox.

### Explicit synthetic conversion

Import `Hoard.Hosting.Configuration.Conversion`. Call
`PreviewConfigurationConversionAsync(sourcePath, destinationPath,
platformVersions, lifecycleOptions, configurationOptions, readEnvironment,
readSecretFile, cancellationToken)` on the registered builder. Only the exact
documented synthetic `fixture-v0` mapping is supported; startup still accepts
integer version 1 only. Preview reads the explicit document, checks shared
structure/composition/public semantics and returns safe change categories plus
a private session, with no secret read or activation proof.

Inspect its report, call `preview.Session.Approve()` deliberately, then
`builder.ApplyConfigurationConversionAsync(session, token)`. Apply consumes
approval once, checks unchanged source/builder/destination context, repeats
full option/secret checks and writes the reference-bearing proposal to a fresh
file, never the original. An explicit environment reader supplies secret
lookups only; conversion never applies HOARD_CONFIG, CLI or remembered overlays.
An apply result is not startup approval: start from a fresh complete evaluation.

Output directories must already be owner-restricted. Same-directory staging is
exclusively created at mode 0600, written/flushed/closed before no-clobber
publication. Existing/racing destinations and source aliases are not overwritten.
Cancelled waits after dispatch can return PublicationPending; inspect the
separate live Publication.Status and Supervision without rewriting the frozen
result or assuming rollback. If a process is interrupted, inspect the original,
any complete final output and only its identified private
`.hoard-configuration-<id>.tmp` files; remove staging only after actual work ends.
Do not use broad directory cleanup or recover resolved-secret rollback files.

Actual child-process interruption tests cover the current macOS local volume.
Linux publication code is present but unmeasured here; network filesystems,
hostile same-user directory races and power-loss durability are not certified.
Provider schema/data compatibility, backups, restore and irreversible changes
remain provider-owned prerequisites. Restoring configuration never reverses
provider data. No released older version, YAML converter or automatic migration
is claimed.
Conversion also rejects explicitly unsupported option versions on disabled
providers, without invoking their callbacks/readers; ordinary startup retains
its intentional disabled-version exemption.

## Later-feature handoffs

| Feature | Reserved work |
| --- | --- |
| F-02 | Implemented bounded, fixture-only module composition/lifecycle; no operational provider |
| F-03 | Implemented fixture-backed configuration, owner secrets and synthetic conversion feeding the existing validator |
| F-04 | Sanitized management capability discovery |
| F-05 | Metadata operations, concurrency, transactions, schema/recovery |
| F-06 | Artifact streaming, staging, commit visibility, read/delete guarantees |
| F-07 | Reusable operational provider conformance and support qualification |
| F-08 | Identity normalization, scheme composition, central permission mapping |

Architecture checks inspect actual source/package graphs, signatures, and IL
using explicit ownership; they neither execute providers nor certify their
behavior. Unused framework references still count as dependencies; being a BCL
type does not make query/connection/transaction objects valid shared contracts.
All eight named platform/provider/host scans are required, not just a nonempty
scan manifest. Identity providers may reference the approved Hosting API,
including its transitive Core dependency. That does not permit a direct
Identity-to-Core reference or an unrelated SDK-mediated path; the scanner
tracks those paths separately even when both reach the same assembly.
Native-client restore, crash recovery, transport-level HTTP drain,
performance, operational provider conformance and production deployment remain
separate acceptance work. F-02 tests only application-level TestServer behavior.
