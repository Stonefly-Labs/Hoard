# F-04 Validation Quickstart

**Status**: Planning-only guide. Discovery APIs, package consumers and the
focused command below do not exist yet. No command is reported as passing
product acceptance by this document.

## Prerequisites and Current Checks

Use the stable .NET 10 SDK selected by `global.json`, Git, Python 3.11+ and
network access for the repository's pinned NuGet restore. No Node, browser,
cloud account, external database or public listener is needed. Future D20/D21
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
documented foundation/fixture lifecycle/configuration scopes, not F-04.
Do not rerun product suites merely to validate planning documents. No OpenTofu
plan/apply or infrastructure operation is needed.

The normative [OpenAPI document](contracts/openapi.json) is already a planning
artifact and can be parsed now:

```bash
python3 -m json.tool specs/004-module-discovery/contracts/openapi.json > /dev/null
```

Parsing proves JSON syntax only, not schema conformance or endpoint behavior.

## Proposed Focused Acceptance Command

After implementation has actually introduced it:

```bash
bash scripts/validate-discovery.sh
```

The future Bash orchestrator owns prerequisites/private workspace cleanup and
bounded subprocesses; a standard-library helper validates hashes, exact proof
inventories and failures, following existing evidence tooling. It must restore
tracked locks, build/format/analyze, pack local libraries/independent fixtures,
build/run package-only discovery hosts and the JSON-only reference consumer,
and execute the [40-case matrix](contracts/acceptance.md) plus compatibility/
architecture checks. Only the exposure-adapter tests may start ephemeral
loopback Kestrel/TLS instances, with in-memory certificates pinned solely by
their clients and finite teardown. It must not create a public/product listener,
download runtime providers, publish packages or read real developer secrets.

Tests consume prepared evidence and never recursively invoke the orchestrator.
Every required suite/journey/case is nonempty and verified; a missing/empty/
duplicate/stale input fails instead of being skipped. `--update-locks` is
proposed only for intentional dependency/consumer changes; after reviewing
those locks independently replay the default command.

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
