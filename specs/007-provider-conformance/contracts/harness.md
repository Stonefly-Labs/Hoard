# F-07 Shared Harness and Contributor Contract

**Status**: Test-only binding/session contracts and the observed-session foundation
are implemented; complete common consumers and CLI behavior below remain planned.
Product [metadata](../../005-metadata-persistence/contracts/metadata-api.md),
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
| `ConformanceCleanupObservation` | Released/retained state, exact opaque still-owned resource IDs, closed safe reason | Released has no remaining IDs/reason; retained requires IDs and a failure reason; dispose alone is not proof |

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

`ConformanceObservedMetadataSession.OpenAsync` and
`ConformanceObservedArtifactSession.OpenAsync` actually call the supplied typed
binding. Put the returned session in `await using` before `CaptureOrigin`.
Potentially failing provider getters run only after cleanup ownership is returned
to the caller; their exact references are cached for both consumers and capture.
Reopen creates an observed wrapper around the actual reopened session with parent
lineage; cleanup/disposal delegate to that real session and confer no release
claim. Component reads share five seconds/256 MiB (64 MiB per assembly). Factory,
getter and provider work still require finite owning-controller scopes; these
wrappers are not a non-cooperation containment mechanism.

`ConformanceSessionOriginOutput.Write` sends a hash-only origin projection through
the actual xUnit output helper. The safe VSTest logger reassembles bounded packets
only from the corresponding actual result, requires exact manifest run/case and
admitted assembly hashes, and embeds the closed origin in that execution's proof.
Parent admission independently checks role/runtime/package assignments, initial
declaration, environment and reopen lineage. Session replay and contradictory
instance identities across origins, results and case attempts reject; failed/
skipped observations do not fabricate missing origins. Passing provider-bound
qualification witnesses require attributable origins. The synthetic package-mode
transport probe is diagnostic, not provider qualification. Its native execution
passed in run `39943968117` at `0687888` (fifteen scopes/46 observations, all 116
foundation checks without failures/errors/skips). Complete CLI/profile/evaluator
integration remains planned.

## Extraction and Unchanged Consumer Rules

The initial executable SDK slice exposes thirty-four methods across
`MetadataBoundsAssertions`, `MetadataPagingAssertions`,
`MetadataConcurrencyAssertions`, `MetadataLeaseAssertions`,
`MetadataIdentityAssertions`, `MetadataEntityAssertions` and
`MetadataReferenceAssertions`, `MetadataTimeAssertions` and
`MetadataReconciliationAssertions`, `MetadataCorruptionAssertions` and
`MetadataAtomicityAssertions` and `MetadataPublicationAssertions`.
They consume an already-prepared fresh
`IMetadataStore`, a caller cancellation token and, for publication cases, the
session's `IMetadataConformanceAuthority`; the caller retains store ownership.
They cover entity round trips, identity/partition isolation, final-graph deletion,
page kinds/bounds, conditional races, reference accounting/ABA, telemetry rollback
and lease/ticket expiry fences, not all inherited witnesses for the corresponding case IDs.
Time assertions additionally require the same harness-owned
`MetadataConformanceClock` supplied when constructing the store.
Only metadata UTC time is controlled; inherited timestamps/timers and outer
execution budgets still use real time. The assertions exercise exact expiry and
rollback without sleeping or trusting provider-supplied expected results.
The continuation consumer also requires a separately prepared foreign store;
scope/size/epoch rejection and live resume are observed through public operations,
without interpreting a provider's private token encoding.
Canonical identity checks preserve case, Unicode normalization distinctions and
encoded separators, and reject synthetic user-info/header/secret-reference inputs.
The receipt-corruption consumer uses the existing typed
`MetadataCorruptionRequest`/`IMetadataCorruptionScope` control signature (the
session fault driver's `CorruptAsync` method group). All fourteen logical shapes,
failure phases/retries/original tickets, unchanged damaged fingerprints,
independent aggregate effects, restored exact receipts and foreign-ticket
abandonment are checked in common code. Private encodings remain in the fixture.
Its public failure strings reject a shared synthetic canary; the focused Memory
probe rejects every provider diagnostic rather than retaining raw output.
Full session-level diagnostic integration and extraction parity remain pending.
Record consumers use those same typed scopes plus the existing
`CorruptRecordAsync` signature for permanent corruption. The SDK owns five
record-damage shapes, missing-versus-corrupt complete groups, invalid page
requests, exact restored pages and all five query-dimension cases. The latter
check selected counts, whole failures before filtering, stable damaged state,
exact restoration, single-row traversal and empty foreign scopes. Actual Memory
mutations now exercise paths that the inherited SQLite-only branches skipped.
An unchanged corruption scope must fail the named common assertion; the same
compiled receipt consumer then passes with actual Memory mutation/restoration.
Six observation-based consumers use `MetadataObservationControl`, matching the
session fault driver's required `ObserveBoundaryAsync` signature. Its five
closed logical points cover before/after commit decisions, each mutation, each
read item and reconciliation decisions; private boundary strings stay in the
fixture. Callback counts prove the selected failure boundaries were reached.
They retain independent candidate reads, every partial-candidate rollback,
grouped root snapshots, reconciliation I/O uncertainty, lost acknowledgment/
abandonment and distinct aggregate contributions without duplicate replay.
Barrier entry/hold/settlement waits use real bounded time. Observation disposal
removes registration only: pending store work remains session-owned. Failure
cleanup joins every launched public read/write task even when the read faults
or cancels; that is not proof of underlying store settlement.
Writer-contention checks additionally take the typed `HoldWriterAsync` and
`AwaitSettlementAsync` signatures. Both normal and pre-canceled reconciliation
must stay uncertain without exclusion; cleanup always releases exclusion then
joins actual settlement with a non-cancelable cleanup token.
The typed publication authority now exposes actual acquisition/active-guard
counts and evidence revocation. Four consumers preserve forged/mismatched/
revoked evidence rejection, orphan-versus-rollback, guard protection through
caller timeout and actual settlement, and replay without authority reacquisition.
The focused registration authority supplies logical evidence and guard lifetime
only, not real artifact retention or cross-store integration.
No method accepts a provider name or expected outcome. Session/adapter routing,
all other inherited assertions and unchanged-wrapper forwarding remain pending.
Invoking this partial slice cannot qualify a metadata binding.

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

## Preparation Entry Point and Planned CLI

The preparation-only entry point is implemented:
`bash scripts/validate-conformance.sh --update-locks --evidence <fresh-private-path>`.
It seals six historical baselines before current builds and requires a second
fresh source/feed/cache locked replay with identical package/lock bytes before
publishing only the explicit conformance lock inventory. Existing prerequisite
locks use recorded local-archive derivations, never graph resolution or writeback.
The command rejects concurrent repository input changes and foreign output paths.
Native run `39947737831` at `585970d` verified both fresh build graphs with identical
bytes for all 18 packages/13 locks; generated source locks are reviewed/tracked.
T017's foundation now admits the selectors/modes below, freezes independent exact
catalog keys and rejects invalid/ambiguous options or unsafe destinations before
allocation. Only preparation executes. Other admitted modes explicitly return
`Incomplete`/`EvidenceIncomplete`, exit `2`; runtime runners and independent
verification/aggregation remain unimplemented. Native run `39949986671` verifies
the real preparation route. T017 completes admission/failure routing, not the
backends explicitly scheduled in T035/T046/T057/T064/T071..T074.
Preparation is always non-qualifying.

`bash scripts/validate-conformance.sh` recognizes:

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
