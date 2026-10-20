# F-02 Lifecycle Validation Quickstart

**Status**: Proposed implementation acceptance guide. F-02 runtime APIs,
fixtures, lifecycle example and lifecycle validation script do not exist yet.
Do not run future commands as though planning delivered them.

## Current Prerequisites and Checks

Use the repository's supported stable .NET 10 SDK (`global.json`), Python
3.11+, Bash and Git. Current checks from the repository root:

```bash
python3 -m unittest discover -s tests/tooling -v
bash scripts/validate-foundation.sh
```

The first tests repository tools; the second builds/packs/tests the F-01
foundation and never starts a server. Neither proves F-02 lifecycle behavior.
Do not run standalone foundation tests without the prepared evidence manifest.
No Azure account, Node runtime, database, identity provider or infrastructure
application is needed.

## Future Implementation Validation Command

After the implementation stage adds and documents the script:

```bash
# FUTURE: not present at planning time
bash scripts/validate-lifecycle.sh
```

The default script must restore/build locked, verify SDK formatting/analyzers,
prepare independently packed lifecycle fixtures/platform packages, compile
source/binary registration compatibility consumers, run composition/unit/
architecture tests with prepared evidence, and execute the fixture-only
package host journeys below. Use bounded subprocesses and a private temporary
directory; remove that directory on exit. No test recursively starts the
orchestrator or silently skips missing evidence.

The script must document a deliberate `--update-locks` path for initial/new
dependency locks, followed by an independent default locked replay. Keep tracked
locks (including standalone packed hosts/consumers), reviewed framework/versioning
dependencies and package provenance. It must not modify F-01's compile-only
example/providers or call infrastructure/package-publication operations.

Expected outcomes are [LC-01..LC-40](contracts/acceptance.md), not a particular
test count selected during planning. Capture exact commands/results and test
counts at implementation; do not pre-fill successful output.

## Journey A: Bundled Choices Without Rebuild

Use the planned `examples/LifecycleHost` package-only fixture harness. It includes
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
   through normal host APIs and the coordinator bridge. The lease alone owns
   application disposal; do not use bare Build, independent app disposal or
   a RunAsync helper that bypasses that boundary. Every selected module must
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

Build and run this bounded fixture journey as part of future validation.
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

Default coordination budgets are 120s total startup, 30s per activation
callback, 5s aggregate readiness, and 30s total stop with 10s drain / 5s per
module cleanup caps. Tests use short explicit values or fake time; they do not
wait minutes. Details and trusted-code limitations are in
[lifecycle.md](contracts/lifecycle.md#budgets-and-non-cooperative-code).

## Explicit Recovery and Documentation

An invalid replacement start must fail, not silently restore its predecessor.
Restore the previous coherent package/registration/selection set explicitly,
redeploy if package references changed, and start a fresh lifecycle. Cleanup
releases resources; no schema/data rollback or crash cleanup is promised.
Non-cooperative trusted code may require process termination; bounded coordinator
waiting cannot forcibly stop it or prove all resources released.

At implementation, update README, development/provider guides and the new
example with actual APIs/commands, framework requirements, phase/resource
ownership, safe diagnostics, budgets, readiness/liveness and restart semantics.
Retain F-01 example's compile-only label. Document unaffected product diagrams,
configuration, management/UI, storage, protocol, IaC and release boundaries
explicitly. No new management HTTP surface, auth permission, live service,
deployment, publication, or persistent-data migration is required by this guide.
