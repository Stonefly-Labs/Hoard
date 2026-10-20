# F-02 Composition and Lifecycle Model

**Status**: Proposed in-memory models; not implemented APIs or a persistence
schema. Existing [F-01 shapes](../001-provider-contracts/data-model.md) are
unchanged. Public Hosting types use immutable records/collections where they
describe snapshots; mutable execution bookkeeping stays internal.

## Registration and Adapter Association

`HoardModuleRegistration` remains `Declaration: ModuleDescriptor` plus
`ProviderType: Type`. A new Hosting `HoardModuleLifecycleRegistration` pairs
`ProviderType: Type` with `ModuleType: Type`. These are data, not instances.

One registered provider must implement exactly one family marker matching its
declared category. Reject abstract/open generic provider types, unknown category
values, null fields, default immutable arrays, invalid ID/version/range syntax,
duplicate dependency/capability/endpoint/health/configuration keys, invalid
provenance URLs (including userinfo/query/fragment), and self-dependencies.
Required F-01 text fields must be nonempty and bounded. IDs use F-01's lowercase
grammar; reject rather than normalize an invalid identity.

Duplicate module IDs fail across the entire registry, even disabled entries.
Reject multiple adapters for the same registration and orphan adapter
associations. All selected modules require a concrete, closed, parameterless
`IHoardModule` adapter type. Disabled registrations may lack an adapter because
F-01 registration-only packages remain valid registry entries. Validation
inspects types/metadata only, never constructors or static factories.

No runtime scanner infers installed-but-unregistered modules. Installation is
build/package evidence outside the operational registry; snapshots report
`IncludedByRegistration` for registered packages, not a supposedly exhaustive
installed-package inventory.

## Startup Selection and Platform Versions

`HoardStartupSelection`:

| Field | Type / rule |
| --- | --- |
| EnabledModuleIds | `ImmutableArray<string>`; explicit unique IDs, no unknown entry |
| MetadataModuleId | `string`; enabled Metadata ID |
| ArtifactModuleId | `string`; enabled Artifact ID |
| RequiredCapabilities | `ImmutableArray<HoardRequiredCapability>`; explicit demands, empty allowed |

Exactly one enabled Metadata and Artifact are permitted, and they must equal
the authoritative IDs; enabling a second non-authoritative one is invalid.
Protocol and Identity cardinality is zero or more. No defaults are inferred.
`HoardRequiredCapability` contains `ModuleId`, `CapabilityId`, bounded
`VersionRange` and `AllowPrerelease`. The target must be enabled and explicitly
declare a satisfying capability. A different module's capability or unavailable
optional target cannot satisfy it. Reject duplicate demand keys.

`HoardPlatformVersions` holds explicit normalized `HostVersion` and
`AbstractionsVersion`. The host version identifies the Hoard platform release,
not the example assembly version. Validate both; do not infer either from a
restored provider package.

`HoardLifecycleOptions` holds `StartupTimeout`, `ActivationCallbackTimeout`,
`ReadinessTimeout`, `ShutdownTimeout`, `DrainTimeout`, and
`ModuleCleanupTimeout`, all positive finite `TimeSpan` values. Inner budgets
are capped by the outer remaining time; a small outer budget is valid, not
silently expanded. `TimeProvider` is an injectable coordinator dependency,
not serialized configuration or a provider-selected clock.

Copy all inputs when validation starts. A successful composition is bound to
the originating builder/registration snapshot; later registrations/options/
selection changes invalidate it before activation, never update a running host.

## Validated Composition and Dependencies

`HoardCompositionValidation` contains either `Composition` and no errors, or
no composition and immutable safe diagnostics. Invalid input is not a default
valid empty composition. `HoardValidatedComposition` has no public constructor:
read-only enabled IDs, disabled declarations, authoritative IDs, platform
versions, satisfied capability demands, active edges and activation order.
It contains no live provider, options/secret values, or operational health.

Structure validation includes disabled entries, but active host/abstractions
range checks apply only to selected entries. Dependencies on a disabled
declaring module are not active. For each enabled declaring module:

- A required dependency must name a registered enabled target satisfying its
  module-version range and prerelease flag.
- An optional absent/disabled target is unavailable, with no ordering edge or
  integration/capability claim.
- An enabled optional target is checked exactly like a required one.

An active edge records prerequisite ID, dependent ID, optional flag, and declared
range/prerelease policy. Capability/version claims do not create implicit
dependencies. Use Kahn ordering with an ordinal (`StringComparer.Ordinal`)
ready set, independent of registration order. Reject cycles, including enabled
optional cycles, with a deterministic bounded safe cycle path. Self-reference
is structurally invalid even in a disabled declaration.

## Runtime State and Phase Ledger

Separate `HoardLifecyclePhase` from `HoardModuleStatus`:

| Phase | Entry / completion rule |
| --- | --- |
| Registered / Validating | Metadata only; no adapter/provider construction |
| Constructing / ComposingServices | Enabled adapter enters ledger before construction/callback; services not yet built |
| BuildingHost / ComposingRoutes | Host builds once; enabled owned routes finalize before initialization |
| Initializing | Each module in activation order; wait for its successful completion |
| AssessingReadiness | All selected modules initialized; required health checks pass |
| Running | Startup admission latched open; tracked workers may run |
| Stopping / Draining / CleaningUp | Stop latched; close admission, cancel workers, drain, reverse cleanup |
| Stopped | Cleanup result recorded; cannot restart this instance |

Status is one of Disabled, Enabled, Initializing, Ready, NotReady, Failed,
Stopping or Stopped. Enabled is not ready. During service/route composition,
enabled entries retain their actual phase, not an initializing/ready claim.
Failure at any startup phase enters the stop path; modules never entered are
reported as not started, not successfully stopped.

An internal activation record tracks safe module ID, adapter ownership,
entered/completed phase bits, pending callback/task, acquired-resource ownership,
worker cancellation/task, and a single cleanup-attempt state. Constructors
must be inert and clean their own allocations if they throw before returning;
an object that was never returned cannot receive a stop callback.
Successfully constructed adapters receive stop once even if service/map/init
later fails. A non-cooperative pending phase is explicitly unsafe to clean
concurrently and is reported incomplete, not successfully released.
Phase activity includes the StopAsync task, recorded before dispatch and
retained while executing even if its coordination wait is TimedOut. Its owner
and prerequisites remain protected; mark affected prerequisite omissions
UnsafePendingCallback and root disposal NotAttemptedUnsafe, not the timed-out
callback as completed. Independent safe cleanup may continue within the same
outer deadline. Track actual task completion separately from the immutable
reported cleanup outcome; after returning the stop result, late completion/fault
is safely observed without rewriting it, retrying cleanup or deferred disposal.
Track admitted request/resource leases through response completion as well as
worker and build activity. A timed-out drain retains those leases for the owner
and its prerequisites; it does not permit resource release. A pending host build
protects all potentially used resources. The composition lease is the single
owner of the built application's root disposal and records unsafe omission
instead of allowing concurrent disposal underneath active work.

Start and stop each share one task among concurrent callers. Caller
cancellation cancels that caller's wait; host lifetime cancellation controls
shared startup. A failed/stopped instance never starts again. A stop latch
prevents any later callback dispatch or ready publication.

## Route Ownership

`HoardOwnedRoute` is Hosting-only: module ID, endpoint responsibility ID,
normalized parsed pattern, immutable uppercase methods, framework precedence,
default order, and internally held request delegate. It is operational data,
not an extension of F-01's descriptive `EndpointResponsibility`.

Responsibility IDs must be declared by their owner. Multiple routes may satisfy
one responsibility; each declared responsibility needs a mapping or startup
fails. Only enabled owners contribute routes. Reject arbitrary endpoint
metadata/policies that change matching, fallback routes, dynamic endpoint
sources, and nondefault order. See
[route language and conflict rules](contracts/lifecycle.md#owned-routes).
No body/options/delegate is included in public diagnostic snapshots.

## Readiness and Diagnostics

`HoardModuleReadiness` contains `Ready: bool` and immutable health observations.
Each observation names a declared health responsibility ID and a platform
reason code (Ready, Unavailable, Initializing, TimedOut or Failed); no free
provider error text. Missing required observations fail readiness; duplicates,
unknown IDs or inconsistent status are failures, not inferred success.
Optional health observations may be unhealthy without making the module
unready, but `Ready=false` always makes it unready. With no declared probes,
the module must still explicitly report its ready/not-ready status.

`HoardLifecycleSnapshot` contains lifecycle correlation ID, composition identity,
phase, startup admission, aggregate readiness and immutable module observations.
Installed/build presence, enabled selection and operational readiness stay
separate. Post-start health loss changes aggregate readiness only; stop closes
the startup admission latch. Readiness never changes selected IDs.

`HoardLifecycleDiagnostic` fields: rule code, safe module/registration identity,
phase, safe dependency path, fixed corrective-action code/message, correlation
ID, and primary-versus-cleanup classification. No raw exception, arbitrary
provider string, option value, private path, or URL field. Output fields and
collections have documented truncation limits with explicit truncation markers.

`HoardStopResult` preserves primary startup/stop failure and per-module cleanup:
NotEntered, Completed, Failed, TimedOut, NotAttemptedBudgetExhausted, or
UnsafePendingCallback. Cleanup completed does not mean persistent changes
rolled back. `Stopped` is a terminal coordination state, not a claim of
resource release if any record is incomplete.
In particular, TimedOut records bounded waiting, not StopAsync quiescence.
Root disposal has a separate Completed, Failed, TimedOut,
NotAttemptedBudgetExhausted or NotAttemptedUnsafe outcome. Unsafe activity
records include only the safe kind and owner IDs, never request URLs/payloads.
