# F-07 Shared Harness and Contributor Contract

**Status**: Proposed test-only interfaces and command behavior, not implemented
APIs. Product [metadata](../../005-metadata-persistence/contracts/metadata-api.md),
[artifact](../../006-artifact-storage/contracts/artifact-api.md),
[lifecycle](../../002-module-lifecycle/plan.md) and
[compatibility](../../001-provider-contracts/contracts/compatibility.md)
agreements remain authoritative.

## Package and Binding Boundary

`Hoard.Testing.Conformance` is a locally packable .NET 10 test SDK. It owns
versioned catalogs, common consumers/assertions and the following test contracts.
It references Abstractions and existing test dependencies only. It does not
discover assemblies, construct a provider by string name, or become a runtime
dependency of any platform/provider package.

| Test-only contract | Required operations/data | Authority boundary |
| --- | --- | --- |
| `IConformanceBinding` | Immutable ID/category/package/capability declaration; `CreateSessionAsync(context, cancellationToken)` | Explicit test-program registration; no directory scanning or provider-selected cases |
| `IMetadataConformanceSession` | Existing `IMetadataStore`, schema administration and publication authority; typed fault driver; reopen/settlement observation | No concrete database type in common consumers; schema/recovery operations stay behind test controls |
| `IArtifactConformanceSession` | Existing store, validator, maintenance/lifetime and same coordination authority; typed fault driver; reopen/settlement observation | No private payload paths in common checks; common code owns expected bytes/digest/reference state |
| `IConformanceFaultDriver` | Catalogued fault capability IDs; arm/release named barriers; inject one named fault; observe typed boundary/state evidence | Setup/observations only; never `RunCase`, `Assert`, expected-outcome override or pass boolean |
| `ConformanceRunContext` | Run/case identity, controlled clock, finite budgets, owned-resource allocator, safe evidence sink | Harness-owned synthetic resources and input snapshot; no arbitrary output/path callbacks |
| `ConformanceCleanupObservation` | Released/retained state, exact opaque owned resource IDs, safe reason | Common evaluator checks actual settlement; dispose alone is not proof |

Exact C# member types follow these shapes during implementation without
weakening the listed invariants. Use cancellation-aware `ValueTask`/`Task`,
immutable result values and existing provider contracts, not `object`,
reflection, `dynamic` or casts through `any`-equivalents. A binding lacking a
mandatory fault/control hook fails admission. Optional environmental hooks
cannot exclude common logical assertions.

Metadata controls cover independent committed snapshots, writer contention,
lost acknowledgments, corruption/capacity, schema/version state, ledger/lease
boundaries, backup/restore and actual durable barriers when applicable.
Artifact controls cover publication/direct-visibility barriers, source/sink
and native non-cooperation, payload damage, capacity/cleanup faults, generation
and receipt/recovery boundaries. Observations are corroborated by public reads,
receipts and independent common assertions, not trusted fault-driver assertions.
Durable proof is executed by parent-owned child processes outside the session.

## Extraction and Unchanged Consumer Rules

1. Preserve all inherited case identities, runtime parameter distinctions and
   positive/negative subproofs before extracting common consumers.
2. Remove common-suite references/switches on concrete provider/session types.
   Provider-private setup remains in adapters; public contract observations
   and expected outcomes remain in the SDK.
3. Existing test wrappers may forward to common checks so prior witness names
   and scripts remain stable. A changed witness name requires an explicit
   reviewed catalog mapping, never silently dropping a test.
4. Pack SDK, provider and adapter independently. The package-only consumer
   references the SDK and explicit binding packages; its common test source
   stays byte-identical for each option.
5. Preserve all independent mechanisms. Do not extract provider implementations
   into a common reference store or make the memory/object option call SQLite/
   Local. Test adapters may share harness setup, not implementation algorithms.

## Finite Work and Isolation

| Scope | Observation budget / bound |
| --- | --- |
| Ordinary harness control/authority operation | Five seconds; existing stricter contract limit wins |
| Barrier arrival / deterministic contention observation | 15 seconds, monotonic; no sleep-based correctness proof |
| Ordinary test child command | Ten minutes including queueing/output capture |
| Artifact measured transfer child | 40 minutes, preserving stricter inner transfer deadline |
| Recovery/crash child | Five minutes; terminate only after required named barrier is observed |
| Child termination and exit observation | Ten seconds, exact owned PID/start identity; inability to confirm exit retains root |
| Cleanup observation | 30 seconds; retained work remains retained after caller return |
| Metadata profile | 90 minutes including recovery/cleanup observations |
| Composition/compatibility/harness profile | 60 minutes each |
| Artifact profile | 180 minutes; transfers serial within profile |
| Full local baseline | 480 minutes, five profiles sequential including coordinator cleanup; no unbounded retries |
| CI profile / aggregate job timeout | 120 minutes (non-artifact), 210 minutes (artifact), 15 minutes (aggregate) |
| Per-run owned test children | Four total, one large-transfer child; one bounded output reader per child |
| Child diagnostic capture | Incremental reads <=64 KiB; <=1 MiB transient aggregate buffer/child; no raw-output disk spool |
| Sanitized retained diagnostics | <=8 MiB/child and <=64 MiB/profile, including event/JUnit summaries |
| Private workspace | Fresh child of owner-private local parent outside Git; no symlinked ancestor, never existing user store |

The baseline coordinator rejects budget configurations that cannot contain
their scheduled children plus cleanup; watchdog expiry gives `Incomplete`,
not an assertion pass. Inherited internal operation/streaming/queue/buffer
limits remain authoritative; these outer budgets are not new provider limits.
At most three explicit diagnostic attempts may be recorded, with no automatic
retry erasing failure. Mutation challenges use separate child-run identities.

Each run copies its input snapshot before executing; source/lock/package inputs
are read-only during cases. Concurrent runs get independent stores, caches,
feeds, output roots and process ledgers. A second writer to a run root rejects.
No global temp sweeps, name-based process termination or deletion of live
roots is permitted. Hostile paths, symlinks and another run's ownership fail
without modifying an outside sentinel.

For deliberately non-cooperative work, first observe retained authority and
blocked admission/readiness. Only then may the harness terminate its exact
isolated test child, observe actual exit, and clean that child's synthetic
resources. This containment is not evidence of cooperative provider cleanup.
If exit cannot be confirmed, persist the private recovery ledger, emit safe
`CleanupIncomplete` and leave resources untouched.

Capture stdout/stderr incrementally, projecting only allowlisted typed events
and safe compiler/test codes before diagnostic persistence. Do not use unbounded
`communicate()`/`ReadToEnd()` capture or retain raw TRX/exception streams. Legacy
logger/parser integration must enforce these limits and sanitation rather than
inherit its current capture behavior. An oversized event, buffer/spool limit,
or unbounded output flood gives safe `OutputLimitExceeded`, blocks qualification
and triggers exact-owned-child containment with actual exit observation.
Never drop required witnesses and return a passing shortened report. Retained
diagnostic files, not just public uploads, undergo the sanitation gate.

## Contributor Entry Point

The starter is a separately packaged forwarding adapter over one existing
fixture, not a third claimed independent storage implementation. It registers
the above binding contracts and changes only composition/setup code. Its good
form runs the complete applicable shared suite. Its faulty form deliberately
returns a stale value for a documented conditional operation; the unchanged
common check must fail at its named assertion, not at build/setup.

Correct only the adapter behavior, then rerun the same consumer/assertion.
Record separate failed and corrected runs with their different package hashes.
Neither the expected negative run nor a subsequent retry can be passed off as
the original successful qualification.

## Planned CLI

`bash scripts/validate-conformance.sh` will expose:

- `--profile baseline|metadata|artifacts|composition|compatibility|harness`
  (default `baseline`), `--evidence <fresh-private-path>` (required).
- `--filter <catalog-case-id>` for non-qualifying diagnosis only.
- `--update-locks` only for intentional manifest changes, always non-qualifying;
  a separate default locked replay is required.
- `--binding-project <project>` only with a category profile for a contributor
  binding; builds an explicit test reference, never scans arbitrary assemblies.
- `--verify <public-report>` checks integrity/completeness without executing
  providers; verification does not claim a fresh runtime run.
- `--aggregate <report-directory>` evaluates the exact five expected profiles
  from one invocation group; foreign/missing reports fail.

Normal qualification exits `0` only for complete requested scope, `1` for
observed contract/evidence failure, `2` for invalid invocation/prerequisite/
interruption/incomplete ownership. Focused/preparation execution may exit `0`
for successful diagnostic work but must always set `qualification: false` and
`mode: diagnostic|preparation`; CI never uses it as a qualifying result.
Every failure includes a stable safe rule/case identity and corrective code.
