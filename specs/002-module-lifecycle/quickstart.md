# F-02 Lifecycle Validation Quickstart

**Status**: Implemented fixture-only acceptance guide. Measured results are in
[the plan](plan.md#implementation-evidence); no operational provider/cache or
published package is implied.

## Current Prerequisites and Checks

Use the repository's supported stable .NET 10 SDK (`global.json`), Python
3.11+, Bash and Git. Current checks from the repository root:

```bash
python3 -m unittest discover -s tests/tooling -v
bash scripts/validate-foundation.sh
```

The first tests repository tools; the second retains F-01 build/package proofs
and runs current solution tests, including source-level TestServer lifecycle
regressions. It does not supply LC-38's separate lifecycle manifest, package-only
journeys or retained-old-binary proof, so it is not full F-02 acceptance.
Do not run standalone foundation tests without the prepared evidence manifest.
No Azure account, Node runtime, database, identity provider or infrastructure
application is needed.

## Lifecycle Validation Command

```bash
bash scripts/validate-lifecycle.sh
```

The default script restores/builds locked, verifies SDK formatting/analyzers,
prepares independently packed lifecycle fixtures/platform packages, compiles
source/binary registration compatibility consumers, run composition/unit/
architecture tests with prepared evidence, and executes the fixture-only
package host journeys below. Use bounded subprocesses and a private temporary
directory; remove that directory on exit. No test recursively starts the
orchestrator or silently skips missing evidence.

For intentional dependency/payload changes, run
`bash scripts/validate-lifecycle.sh --update-locks`, review the changed tracked
locks, then run the default command independently. Keep tracked
locks (including standalone packed hosts/consumers), reviewed framework/versioning
dependencies and package provenance. It must not modify F-01's compile-only
example/providers or call infrastructure/package-publication operations.

`--filter FILTER`, `--packages-only` and `--journeys-only` are explicitly partial,
never full LC-01..40 acceptance. Every subprocess has a ten-minute backstop;
ordinary tests use virtual time/barriers with five-second scheduler backstops.
Hosting locks internal NuGet.Versioning 7.9.0 (Apache-2.0); test-only TestHost
10.0.13 (MIT) does not upgrade the installed runtime. Hosting consumers need
the ASP.NET Core shared framework, even non-web registration consumers.

## Journey A: Bundled Choices Without Rebuild

Use the [package-only fixture harness](../../examples/LifecycleHost/README.md). It includes
Protocol.One, Protocol.Two, Metadata, Artifact.One and optional Identity, each
with explicit registrations and lifecycle adapters. Artifact.Two is absent from
baseline references/registrations and reserved for Journey B's custom rebuild.
Independently packing all six fixtures does not include them all in this host.
Its startup selection is an in-memory test input, not promised YAML/JSON/CLI
configuration.

1. Build once from packed packages; create a fresh host with one artifact and
   protocol choice selected. Validate before construction, compose services,
   acquire the lifecycle lease with `await using`, use the supervised
   `BuildHoardApplicationAsync` boundary, map routes, then explicitly start/stop
   through normal StartAsync and `StopHoardApplicationAsync(lease)`, sharing
   framework stop with lease disposal. The lease alone owns application
   disposal; do not use bare Build/StopAsync, independent app disposal or a
   RunAsync helper that bypasses that boundary. Every selected module must
   become ready.
2. Send a request through the in-process test pipeline to the enabled test
   route; observe one response and worker admission only after complete ready.
   The disabled fixture route is absent; all its construction/callback/worker/
   connection counters remain zero.
3. Change the caller's original selection while the first host runs; confirm
   the runtime selection does not change. Stop it, then create a new lifecycle
   from the same already-built packages with the alternate bundled protocol
   choice, retaining Artifact.One. No rebuild occurs; new selection undergoes
   the complete gate.

This simulates curated selection semantics, not a runnable NuGet/SQLite/
filesystem distribution. No TCP listener is needed; TestServer is not evidence
of transport-level drain or real package-manager support.

## Journey B: Add an Independent Custom Package

Start from the package-only lifecycle example, not F-01's compile-only example.
Add the independent Artifact.Two package reference and Abstractions-only
provider declaration to the custom variant; put its lifecycle adapter on the
host side. Register both through the public boundaries, choose its ID
explicitly, restore/build with reviewed locks, redeploy the test composition
and create a new lifecycle.

Confirm zero engine/Core or unrelated provider edits and no provider-to-provider
reference. The old running lifecycle cannot acquire the new package via selection
or disk scanning. Missing package/registration/adapter is an actionable startup
error, never an automatic download or fallback.

The default command builds and runs this bounded fixture journey.
It is not a community provider SDK, production artifact store or certification.

## Failure, Readiness and Shutdown Exercises

Use deterministic fixture barriers rather than a real unavailable service:

1. Shuffle valid registrations; order stays ordinal topological. Exercise each
   invalid registry/selection/dependency/capability input and verify zero
   constructors before rejection.
2. Delay/fail/cancel/time out an entered phase and readiness probe. While
   pending, there is no ready result, admitted normal request or ongoing worker.
   Route conflicts fail before initialization/traffic; disjoint methods and
   unique literal precedence succeed.
3. Seed arbitrary credential-bearing provider text, unsafe IDs and exceptions;
   capture normal logs/results. Only safe catalogue codes, safe IDs or ordinal
   references and correlation information may appear.
4. After a successful start, change fixture readiness; aggregate readiness
   drops and recovers without changing selection or automatically draining.
5. Stop during startup or running traffic. Readiness/admission closes first;
   cooperative in-flight work drains, then entered adapters clean up in reverse
   order once. Concurrent/repeated start/stop callers cannot duplicate work.
6. Advance fake time through overall/per-phase deadlines and inject cleanup
   failure/non-cooperation. Preserve primary errors, continue safe cleanup,
   explicitly mark incomplete/unattempted work and never reuse the instance.
   Hold a request/response stream past drain expiry: its owner/prerequisites
   and root disposal remain protected. A stalled build cannot return a late
   application; an in-flight worker is one admitted callback, not a promise
   of atomic per-iteration admission.
7. Hold A.StopAsync past its callback budget, with A depending on B and unrelated
   C, while outer stop time remains. A stays TimedOut, B/root remain protected
   while it executes, and quiescent C cleans up under the same deadline.
   After the bounded stop result, release/observe A and verify no second stop,
   returned-result rewrite or deferred dependency/root disposal.
8. Fail a worker while a synchronous host-stopping notification or lifetime
   cancellation callback is held. Snapshot access stays responsive and stop
   uses its original absolute deadline; global Phase activity protects every
   module and the root. Release/observe the callback after incomplete stop and
   confirm frozen outcomes with no retry/deferred disposal. A cooperative
   worker-fault counterpart cleans modules/root and notifies only once.
9. Throw from lifetime and readiness/cleanup-timeout cancellation callbacks;
   retain the primary failure plus one safe additional `CancellationFailure`
   per failed cancellation operation, with owner/phase/action/correlation and
   no seeded exception payloads in results/logs. Completed faults may coexist
   with successful resource release. Hold a lifetime callback beyond bounded
   stop/disposal, then release it to throw: only a later snapshot gains the
   diagnostic, while returned results and cleanup/disposal attempts stay fixed.
10. Fault a callback after its readiness or cleanup wait times out. Hold an
    independent cleanup open to prove known eventual faults are reported before
    shared stop completes; release a callback after bounded results to prove
    only later snapshots change. Startup, framework-stop and root-disposal
    counterparts retain safe owner/phase/action/correlation and once-only
    diagnostics. Direct awaited exceptions, including their own TimeoutException,
    preserve normal categories/outcomes without duplication; cooperative
    cancellation adds no new fault. Fault a worker during drain and after
    bounded stop without requesting shutdown again. Expire the original budget
    between framework stop and root dispatch: disposal remains unattempted.

Default coordination budgets are 120s total startup, 30s per activation
callback, 5s aggregate readiness, and 30s total stop with 10s drain / 5s per
module cleanup caps. Tests use short explicit values or fake time; they do not
wait minutes. Details and trusted-code limitations are in
[lifecycle.md](contracts/lifecycle.md#budgets-and-non-cooperative-code).

## Safe Diagnostic Catalogue

Normal results expose RuleCode, safe ModuleId (or registration ordinal),
Phase, bounded DependencyPath, fixed CorrectiveAction, CorrelationId and
primary/cleanup classification. No provider exception, inner exception, secret
option, URL or private path is copied. Output is bounded to 100 diagnostics and
32 path IDs with explicit omitted counts; fixed action/message text is at most
512 characters. See the provider guide for structural input limits.

| Rule codes | Corrective action |
| --- | --- |
| MalformedRegistry, DuplicateModule, InvalidSelection, InvalidLifecycleAdapter | Correct explicit declaration/identity/selection/adapter structure and revalidate; never choose an override by registration order |
| InvalidBudget | Supply positive finite durations; inner budgets do not expand outer time |
| UnknownSelection, MissingLifecycleAdapter, MissingDependency | Include/register/associate the explicitly selected and required modules; no download or auto-enablement |
| UnsupportedPlatform, UnsupportedDependency, UnsupportedCapability | Install compatible versions or explicitly correct the selected target/range/prerelease policy |
| DependencyCycle, InvalidCardinality | Remove active cycle or choose exactly one authoritative metadata/artifact provider |
| UnsupportedRouteShape, AmbiguousRoute, MissingEndpoint, MissingMapping | Use the supported route language, declared responsibilities and supervised map boundary before start |
| IndependentWorker | Use the one admitted RunAsync callback, not independent hosted services |
| InvalidReadiness, NotReady | Correct explicit status and required declared observations; enabled does not mean ready |
| StaleComposition, Cancelled, TerminalLifecycle | Create a fresh validated lifecycle; do not mutate/reactivate a failed or stopped instance |
| PhaseFailure, WorkerFailure | Investigate the safe owner/phase/correlation and explicitly restart a coherent composition; no automatic retry |
| CleanupFailure, HostStopFailure, RootDisposalFailure | Inspect separate module/root outcomes and retained ownership; cleanup does not imply rollback |
| CancellationFailure | Correct the named owner's trusted cancellation callback for the originating phase before starting a fresh lifecycle; reported as an additional cleanup diagnostic, not proof of pending resource use |
| Timeout, UnsafePendingCallback, LateCallbackFailure | Inspect trusted cooperation; incomplete retained resources may require process termination/restart |

Returned stop outcomes never change after late completion/fault. A safely
observed late callback failure may appear in a **new** snapshot, not rewrite an
earlier immutable stop result or trigger deferred cleanup.

## Explicit Recovery and Documentation

An invalid replacement start must fail, not silently restore its predecessor.
Restore the previous coherent package/registration/selection set explicitly,
redeploy if package references changed, and start a fresh lifecycle. Cleanup
releases resources; no schema/data rollback or crash cleanup is promised.
Non-cooperative trusted code may require process termination; bounded coordinator
waiting cannot forcibly stop it or prove all resources released.

README, development/provider guides and the example document actual APIs,
framework requirements, phase/resource ownership, diagnostics, budgets and
restart semantics. `IHoardLifecycle.StopAsync` reports module coordination,
with `NotAttemptedOwnerPending` until eligible external-owner root disposal.
Inspect the separate final `lease.StopResult`; incomplete disposal throws a
sanitized lifecycle exception, without retrying cleanup or rewriting outcomes.
Pending cancellation callbacks and their linked-token deregistration are also
supervised activity, not synchronous unbounded waits.

The [provider guide](../../docs/PROVIDERS.md#opt-in-lifecycle) lists diagnostic
codes/actions, bounded structural/output fields and trust limits. Normal
diagnostics never carry provider exception/inner text, options or URLs.
F-01 remains compile-only. The implementation evidence records unaffected product diagrams,
configuration, management/UI, storage, protocol, IaC and release boundaries
explicitly. No new management HTTP surface, auth permission, live service,
deployment, publication, or persistent-data migration is required by this guide.
