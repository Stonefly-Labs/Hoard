# Fixture-only lifecycle host

This package-only example validates F-02 Hosting APIs. It is not a cache, native
package protocol, database, blob store, identity service or curated distribution.
It runs bounded in-process TestServer journeys, never a listener. No cloud,
Node runtime, external service or provider publication is needed.

Run from the repository root:

```bash
bash scripts/validate-lifecycle.sh
```

The orchestrator independently packs platform libraries and all six fixtures
into a private local feed, restores each standalone consumer with tracked locks
and explicit source mapping, builds both variants and executes self-checking
journeys. It removes its own resolved temporary directory. A missing package,
stale hash, empty test/journey selection or failed/timed-out subprocess fails.
Use `--update-locks` only for intentional dependency/payload changes; review the
generated locks, then independently replay the default command. Do not run
these local-only package references against public feeds or substitute project
references/source inclusion. The F-01 [CustomHost](../CustomHost/README.md)
remains compile-only and is never executed.

## Included packages and journeys

Baseline references Protocol.One, Protocol.Two, Metadata, Artifact.One and
optional Identity. Identity stays disabled; Artifact.Two is absent from both
baseline references and registrations. Each provider fixture is independently
packed, without references to another fixture. Metadata/artifact packages use
only Abstractions; adapters in this host own Hosting integration.

The already-built baseline binary starts/stops a lifecycle using Protocol.One,
then creates a new lifecycle selecting Protocol.Two with the same Artifact.One.
There is no intervening rebuild. Enabled test handlers respond, disabled routes
are ordinary 404s with no phase/worker/synthetic-connection activity, and
mutating a caller selection cannot change the active composition.

`Custom/LifecycleHost.Custom.csproj` additionally references Artifact.Two and
includes its host-owned adapter. Rebuild/redeploy this variant and start a
fresh lifecycle selecting that artifact. Both binaries separately reject an
invalid replacement, then explicitly restore the prior coherent selection in
a new lifecycle. Seven nonempty successful journeys are required in total.
The tool also compares platform/unrelated-provider source hashes.

## Public boundary and ownership

`Program.cs` uses explicit immutable in-memory selection, not a configuration
parser. The sequence is registration, adapter association, metadata validation,
`await using` composition lease, supervised build, owned mapping, normal
`app.StartAsync`, `app.StopHoardApplicationAsync(lease)`, then lease disposal. Old registration
consumers still work without opting into lifecycle. The acceptance harness
retains a binary built against merged F-01 packages and runs it against the new
Hosting payload without recompiling it; separate new-source and non-web probes
verify framework propagation. Hosting now requires the ASP.NET Core shared
framework as well as .NET 10. This changes deployment prerequisites, not the
old public registration signatures.

Do not call bare Build/StopAsync, independent application disposal or host RunAsync around
the lease. Module stop and root disposal are deliberately separate:
`IHoardLifecycle.StopAsync` shares module coordination and reports
NotAttemptedOwnerPending when root disposal belongs to the external owner.
The explicit stop wrapper and lease disposal share one actual framework-stop
task, including synchronous stopped notifications. Lease disposal supervises root disposal,
under the same original shutdown deadline. Inspect its final `StopResult`.
Incomplete release throws a sanitized lifecycle exception; no repeated disposal
or late callback retries cleanup.

Adapters own their acquired fixture resources and release partial acquisitions
once. DI-owned resources remain container-owned. A stalled request/response,
worker, build, activation or cleanup callback protects its owner, prerequisites
and root. TimedOut means waiting ended, not that trusted code stopped.
Unsafe/budget-exhausted omissions are explicit; independent safe cleanup may
continue, but incomplete terminal lifecycles may require process termination.
Nothing rolls back provider schemas/data or proves crash cleanup.
The supervised build installs the request-completion boundary before host
startup filters/middleware. A request lease remains active through their
response-completion callbacks as well as handler callbacks, including handled
errors; it does not release when the handler returns. Pending completion after
drain expiry retains owner/prerequisite/root resources. Releasing it after the
bounded result cannot retry cleanup or trigger deferred disposal. Normal host
middleware and access policy still apply without extra caller wiring.
Worker-failure host notification runs outside the state lock and is tracked
before stop begins. A pending synchronous stopping notification or lifetime
cancellation callback may use any module/root resource, so all remain protected
while snapshots and bounded stop remain available. Releasing such a callback
after the returned incomplete result does not trigger deferred cleanup/disposal.
Throwing lifetime or readiness/cleanup-timeout cancellation callbacks report
safe additional `CancellationFailure` diagnostics before tracked activity is
released. They do not overwrite primary failures or imply that already released
resources remain active. Late faults appear in a later snapshot, not in frozen
stop/disposal results. Correct the named owner's cancellation handling before
restarting; no provider exception payload is exposed.

Startup/readiness/cleanup and framework-stop/root-disposal faults likewise
report once before releasing tracked activity. Faults after an abandoned wait,
including worker faults during shutdown, add safe `LateCallbackFailure`
diagnostics even if shared stop is still running. Direct failures are not
duplicated; cooperative cancellation is not a new fault. Frozen results and
once-only ownership remain unchanged. An expired budget after framework stop
leaves root disposal NotAttemptedBudgetExhausted, without dispatch or retry.

The [provider guide](../../docs/PROVIDERS.md#opt-in-lifecycle) documents APIs,
route restrictions, safe diagnostic catalogue, status/readiness distinctions
and defaults: startup 120s, callback 30s, aggregate readiness 5s; shutdown 30s,
drain at most 10s, module cleanup at most 5s. Test-only failure cases use barriers
and virtual time, with five-second real scheduler backstops, not production
performance claims. Later health loss changes readiness only; stop/fault closes
admission. Host middleware/access policy still applies.

F-03 owns configuration/secrets UX, F-04 authorized discovery/UI, and later
features own real provider/cache operations and conformance. TestServer does
not certify TCP/proxy/TLS drain, native-client restore or production safety.
No infrastructure apply, deployment, release or package publication occurs.
