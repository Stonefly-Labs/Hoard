# F-04 Validation Quickstart

**Status**: Implemented fixture-backed library/API acceptance, not a runnable
cache, production provider or rendered console. The
[implementation evidence](plan.md#implementation-evidence) records measured
results and boundaries. Clean convergence and
[finalization](plan.md#finalization-acceptance) pass; maintainer merge and the
separately invoked post-merge completion stage remain pending.

## Prerequisites and Current Checks

Use the stable .NET 10 SDK selected by `global.json`, Git, Python 3.11+ and
network access for the repository's pinned NuGet restore. No Node, browser,
cloud account, external database or public listener is needed. D20/D21
adapter tests need permission to open private ephemeral loopback-only ports;
they must close them within finite test budgets.
From the repository root, these commands already exist:

```bash
python3 -m unittest discover -s tests/tooling -v
bash scripts/validate-foundation.sh
bash scripts/validate-lifecycle.sh
bash scripts/validate-configuration.sh
```

The first command checks repository tooling. The other commands prove their
documented foundation/fixture lifecycle/configuration scopes. No OpenTofu
plan/apply or infrastructure operation is needed.

The normative [OpenAPI document](contracts/openapi.json) is embedded unchanged
in Application, not copied to a public static directory. Syntax-only inspection:

```bash
python3 -m json.tool specs/004-module-discovery/contracts/openapi.json > /dev/null
```

Parsing proves JSON syntax only, not schema conformance or endpoint behavior.

## Focused Acceptance Command

```bash
bash scripts/validate-discovery.sh
```

The Bash entry point checks prerequisites; its standard-library helper owns
private workspace cleanup and
bounded subprocesses and validates hashes, exact proof
inventories and failures, following existing evidence tooling. It restores
tracked locks, build/format/analyze, pack local libraries/independent fixtures,
build/run package-only discovery hosts and the JSON-only reference consumer,
and executes the [40-case matrix](contracts/acceptance.md) plus compatibility/
architecture checks. Only the exposure-adapter tests may start ephemeral
loopback Kestrel/TLS instances, with in-memory certificates pinned solely by
their clients and finite teardown. It must not create a public/product listener,
download runtime providers, publish packages or read real developer secrets.

Tests consume prepared evidence and never recursively invoke the orchestrator.
Every required suite/journey/case is nonempty and verified; a missing/empty/
duplicate/stale input fails instead of being skipped. `--update-locks` is
only for intentional dependency/consumer changes; after reviewing
those locks independently replay the default command.

Use `--evidence-directory /absolute/fresh/private/directory` to retain a run;
the directory must be fresh, owner-private and outside the repository. Default
runs remove only their exact owned workspace. `--retained-baseline` reuses
previously frozen pre-F-04 binaries after source/identity/hash validation.
Import also requires saved complete dependency and assets digests; legacy
manifests without them fail, never silently rebaseline against current files.
`--phase baseline --retain-baseline /absolute/fresh/private/directory` captures
those binaries against merged `7fd73267a5154583363c94e9e85b9bac7d4a16b3`,
not current platform sources. Manifests/logs are private temporary evidence,
never committed response/configuration dumps. Runtime mutation recipes operate
only on private copies; compilation failure is not accepted as a runtime red.

## Public Integration

Use the same service collection, builder, evaluated composition and supervised
lease as F-03. Before configuration evaluation/legacy validation, call:

```csharp
builder.AddHoardDiscovery(
    new HoardDiscoveryCatalog("my-distribution", "0.1.0", "partial"),
    new HoardDiscoveryOptions
    {
        Exposure = HoardDiscoveryExposure.LocalLoopback,
        DirectLocalNoProxy = true
    });
```

`Hoard.Hosting.Discovery` owns these types and `IHoardDiscoverySource`.
An empty partial catalog does not infer installed packages or tested support.
Supply explicit inclusion/publication/contribution records as appropriate.
Collections and public text are bounded and immutable. Host time providers must
be trusted inert clocks, not I/O or provider callbacks. Defaults are a monotonic
two-second cooperative deadline and a 4 MiB encoded-body ceiling; configured
deadlines must be positive finite. Limits are checked before activation and
encoding finishes before committing success.

For explicit anonymous direct-local use, configure the named
`Hoard.Management.Read` policy deliberately (for example,
`AddAuthorization(options => options.AddPolicy("Hoard.Management.Read",
policy => policy.RequireAssertion(_ => true)))`) and configure Kestrel through
`web.WebHost.UseUrls("http://127.0.0.1:5080").PreferHostingUrls(true)`.
This is a wiring fragment, not a command to start a product listener.
No proxy/forwarded-header processing or wildcard binding is supported in
local mode. Never proxy public traffic into this anonymous surface.

For secured-network use select `SecuredNetwork`, require authenticated
management-read permission and configure usable authentication defaults or
explicit registered read-policy schemes. Use direct HTTPS, or explicitly opt
into trusted immediate TLS termination with one forwarded hop, known peers/
networks and validated forwarded protocol/resulting HTTPS. The production
adapter requires explicit `UseUrls(...).PreferHostingUrls(true)` so effective
bindings are not hidden by `Listen` overrides. Unknown servers/topologies fail
closed; TestServer's internal fixture adapter is not a public extension point.
Host auth/proxy/request-logging posture still needs deployment review; sanitizing
discovery-owned diagnostics does not redact framework request query logs.

After successful evaluation/composition, use the public extensions from
`Hoard.Hosting.Lifecycle` and `Hoard.Application.Discovery`:

```csharp
var app = await web.BuildHoardApplicationAsync(lease, cancellationToken);
app.MapHoardDiscovery(lease);
await app.MapHoardModulesAsync(lease, cancellationToken);
await app.StartAsync(cancellationToken);
// Stop through the inherited wrapper, then dispose the external lease.
await app.StopHoardApplicationAsync(lease, cancellationToken);
```

`lease.BindHoardDiscovery(app).Capture(cancellationToken)` is the in-process
read-only equivalent, guarded by exact app/root/source/catalog ownership.
Both literal GET routes share authorization, exposure verification,
no-store/private/no-cache/nosniff and bounded errors. Queries return a generic
400; unsupported methods return 405, with no implicit HEAD, ETag/304, mutation
or static OpenAPI bypass. Missing protection fails startup or returns closed
503 while actual protection is unverified. No inventory is returned on denial.

Each body carries lifecycle ID, decimal-text revision, publication/capture and
actual readiness-assessment times. Reads do not refresh health, activate
providers, resolve service factories/secrets or change selection. Usability
requires exact tested scope, actual bindings and current contributors; it is
not execution permission. Reassess only through the existing lifecycle API.

The JSON-only `ReferenceConsumer` executable reads stdin, not a filename.
It caps input at 4 MiB/depth 32 and recognizes actions only for its exact
synthetic capability/version/operation/owner tuple. Unknown semantics cannot
enable actions. Owners/dependencies must be ready in `assessing-readiness` or
`running`; unknown or terminal phases override conflicting ready/usable claims.
Support state, evidence scope and availability have separate contextual semantic
lines, including explicit fixture qualification and unsupported/unverified
corrective guidance. Refresh generations/revisions reject old or duplicate terminal
responses; denial discards data, failure immediately stales it, and monotonic
receipt age over 30 seconds expires actions (exactly 30 seconds is current).
Textual labels and reading order are semantic proof, not DOM/ARIA/browser/WCAG
acceptance.

## Validation Journeys

1. **Known inventory, disabled isolation**: Build a fixture catalog with known
   included/unregistered and registered/disabled entries. Use a partial catalog
   counterpart to prove unknown versus absent. Inspect the safe model and actual
   HTTP JSON; assert zero disabled constructors/checks/secrets/probes/workers/
   routes/connections, with selected authorities visible.
2. **Real capability correspondence**: Compose a supported synthetic route and
   separately a service-only operation. Compare actual route/method and effective
   owner descriptor counters with discovery; remove/shadow bindings, change
   required/optional dependency states and preserve distinct owner/version scopes.
   Fixture evidence must remain labelled fixture-only.
3. **Lifecycle observation**: Use inherited explicit readiness assessment and
   barriers to publish ready/not-ready/recovery/stop. Repeated discovery reads
   must add no probes and produce one lifecycle/revision across all fields.
   Failed startup retains local diagnostics, not a new listener.
4. **Protected inspection and description**: Mock authorized/unauthenticated/
   insufficient identities, direct local and secured-network/proxy posture.
   Both literal routes have identical enforcement, no-store/nosniff and safe
   denials. Reject null/nonlocal peers, unknown/wildcard bindings, spoofed
   forwarding and missing protection; TestServer's internal verifier cannot
   become a production bypass. Separately prove actual effective-address and
   raw-peer-capture behavior using finite loopback Kestrel cases, including a
   locally generated/pinned certificate for HTTPS recognition. No production
   certificate or external-proxy certification is claimed.
5. **No disclosure**: Seed invented markers into values, locators, private
   paths, arbitrary metadata/defaults/allowed values and collaborator exceptions.
   Capture all owned responses, description/examples, errors and telemetry.
   None may contain those markers; safe identity/reason/correction remains.
6. **Reference consumer**: Parse actual JSON and feed all presentation states
   in [presentation.md](contracts/presentation.md). Unsupported actions hide;
   unavailable/unknown/stale actions cannot execute. Denial clears sensitive
   retained data; receipt age, refresh-generation and host-replacement races
   cannot revive an old result. Verify semantic labels/order, not rendered UI.
7. **Bounds and performance**: Exercise at/over-limit encoded JSON, Unicode
   escaping expansion, pre/mid cancellation and deadline exhaustion. Then record
   100 complete authorized reads of 100 modules x 10 capabilities at concurrency
   10; require p95 <= two seconds, exact sample counts and zero extra resources,
   probes/secret reads/provider service calls. Record environment; do not report
   public-network/production throughput or preemptive transport termination.
8. **Distribution and compatibility**: Run package-only same-binary bundled
   restart and rebuilt custom-artifact journeys, invalid replacement and
   explicit recovery. Prove lifecycle IDs differ and unrelated providers retain
   their source/binary hashes. Run pre-F-04 binaries without rebuilding, plus
   new-source and non-web Application consumers. Restore default locked
   foundation/lifecycle/configuration acceptance as regression gates.

## Review, Troubleshooting and Recovery

Inspect closed reason/correlation and observation times; never dump private
configuration, request payloads, secret locators or exceptions. A new GET reads
the last published assessment, not a new health probe. Unknown publication,
unsupported bindings, deadline or size failure must not become empty/healthy
success. The source never repairs a failed composition.

Use the explicit local policy only on verified loopback bindings with no proxy.
Public/team management needs explicit authenticated read permission and TLS/
trusted-proxy posture. No Host/forwarded-header heuristic establishes that the
original caller is local; the operator must not forward public traffic into
the anonymous local surface.

For a bundled choice, explicitly change validated selection and restart.
For an absent custom provider, add package/registration, rebuild, redeploy and
restart. Roll back discovery itself by removing opt-in/mapping and restarting
a compatible build. None of these actions implies provider-data rollback.
No release, deployment or infrastructure operation belongs to this guide.
