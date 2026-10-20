# F-02 Acceptance and Traceability

**Status**: Proof obligations with [implementation evidence](../plan.md#implementation-evidence).
This matrix alone is not passing proof. Every fixture must use
Fixture provenance and lifecycle-only wording; real NuGet/storage/identity,
cache behavior, native clients and F-07 certification are outside these proofs.

## Fixture and Harness Rules

Independently pack Protocol.One, Protocol.Two, Metadata, Artifact.One,
Artifact.Two and Identity lifecycle fixtures. No fixture references another
concrete provider. Metadata/artifact packages remain Abstractions-only;
host-side adapters own Hosting references. The two artifact choices use
distinct IDs so both can be bundled, with only one enabled. At least two
protocol choices support the without-rebuild selection journey.

The baseline host includes Protocol.One, Protocol.Two, Metadata, Artifact.One
and optional Identity, not Artifact.Two. The custom variant adds Artifact.Two
and its host-owned adapter through rebuild/redeployment. Independently packing
all six fixtures does not imply including all six in the baseline.

Each adapter exposes test-only event counters and barriers for construction,
each phase, request admission, worker work, readiness, external connection
attempts, acquired resource release and cleanup. Synthetic external calls are
counted, not made to a real service. Record safe IDs and monotonic sequence
numbers, not secrets. Controlled failing variants target each entered phase.
Do not rewrite F-01's original independent packages or compile-only example.

Use TestServer for actual handler dispatch through the application pipeline.
Use pure coordinator tests for fake time/non-cooperation; every task/barrier
created by tests must be released/observed before test exit so tests do not
leak runaway work. Real-time integration deadline assertions allow documented
scheduler tolerance; virtual-time tests prove deadline arithmetic exactly.

## Acceptance Matrix

| ID | Case | Required observable proof |
| --- | --- | --- |
| LC-01 | Valid selection and shuffled registration | Same ordinal topological order, all selected modules ready; prerequisites finish before dependents |
| LC-02 | Unknown/unregistered selection | Explicit safe rejection, zero constructors/callbacks/package retrieval |
| LC-03 | Duplicate identity / duplicate registration | Reject even when disabled or same provider registered by two entry points; never last-wins |
| LC-04 | Malformed descriptor / family disagreement | Structural rejection for enabled and disabled entries, including invalid enum/default array/duplicate nested IDs/unsafe provenance; safe ordinal identity if needed |
| LC-05 | Disabled incompatible platform | Structurally valid disabled module not evaluated against active version ranges and never constructed |
| LC-06 | Platform/version/prerelease policy | Runtime matches applicable F-01 C-01..C-23 classifications; source/binary/release cases remain separate API proof, not runtime activation |
| LC-07 | Required target absent/unregistered/disabled | Fail without implicit enablement; valid selected target counterpart starts |
| LC-08 | Optional unavailable / enabled compatible | No edge/integration for absent/disabled; compatible enabled target precedes dependent |
| LC-09 | Optional enabled incompatible/prerelease | Fail entire composition; no target/integration disablement, substitution or widening |
| LC-10 | Self, required cycle and optional enabled cycle | Reject before construction; deterministic safe involved path; absent optional edge removes the cycle |
| LC-11 | Authoritative cardinality | Zero/two Metadata or Artifact or mismatched authoritative ID fails; multiple Protocol/Identity succeeds |
| LC-12 | Required capability | Missing/disabled target, missing ID or incompatible version/prerelease fails; correct enabled target succeeds |
| LC-13 | Fixed validated snapshot | Mutation/stale builder cannot activate a different graph; original arrays cannot mutate running selection |
| LC-14 | Missing/duplicate/orphan adapter | Fail before adapter/provider construction; old registration-only use still inert and valid |
| LC-15 | Enabled protocol route/worker | Declared test handler serves and worker starts only after all selected initialization/readiness success |
| LC-16 | Disabled isolation | Zero construction and all phase/probe/stop callbacks, mapped routes, workers, connection attempts; ordinary not-found for disabled test route |
| LC-17 | Delayed initialization/readiness | Live in-process host/pipeline stays not ready, requests blocked and workers absent until complete ready; no phase bypass |
| LC-18 | Ambiguous route ownership | Parameter-renamed, case/slash-equivalent and overlapping-method conflicts fail with both safe owners; same-owner duplicates fail too |
| LC-19 | Permitted/unsupported routing | Disjoint methods/literals and unique literal precedence succeed; unsupported constraints/catch-all/order/policies/unowned overlaps fail before serving; disabled claimant contributes no conflict |
| LC-20 | Constructor/service/host-build/map failure | Failed start, zero admitted work; returned adapters/partial composition resources cleaned; throwing constructor self-cleans; supervised build/lease handles failure before bridge start |
| LC-21 | Initialization failure at each position | Failing partial adapter included; later modules do not initialize; original failure retained; no ready/traffic/worker |
| LC-22 | Startup cancellation and stop race | Stop during each phase and immediately before ready wins, no subsequent phase dispatch or ready publication |
| LC-23 | Startup deadline / callback timeout | Virtual time proves single absolute and capped inner deadlines, including sync composition/supervised build; record pending build, safe failed result, no late application/ready publication or indefinite coordination wait |
| LC-24 | Later readiness loss/recovery | Same selection, safe affected module, aggregate false then true; disabled modules unprobed; no automatic replacement/drain |
| LC-25 | Invalid/failing/timed-out readiness | Missing required health ID, unknown/duplicate IDs, inconsistent output, throwing or stalled probe never means ready |
| LC-26 | Normal stop and drain | Ready false/admission closed before drain; no new request/RunAsync callback, in-flight request/worker cooperative completion then reverse-dependent cleanup; callback is the documented worker admission unit |
| LC-27 | Partial-start cleanup | Every entered returned adapter including failed phase stops in reverse order; never-entered modules do not receive cleanup |
| LC-28 | Cleanup error / timeout | Preserve primary plus extra cleanup failure; fixed outer deadline not multiplied. Hold A.StopAsync past its callback budget with A depending on B and unrelated C: preserve A TimedOut, no second stop, B/root protected while A still runs, C cleanup continues safely within the same outer budget |
| LC-29 | Exhausted budget / non-cooperation | Explicit timed-out/unattempted/unsafe statuses; barrier-held request/response stream protects owner/prerequisites/root. Pending phase/worker/build and timed-out but executing StopAsync likewise prevent unsafe release; prerequisite omissions are UnsafePendingCallback and root NotAttemptedUnsafe. After the bounded stop result, release/observe the held cleanup task and assert no result rewrite, retry, deferred disposal or late publication |
| LC-30 | Repeated/concurrent lifecycle calls | Shared start/stop outcomes, each phase and cleanup at most once; terminal instance cannot restart; cancelled waiter does not cancel another caller's shared operation |
| LC-31 | Independent hosted-worker bypass | Reject module-added IHostedService/BackgroundService; owned worker faults close admission and request shutdown without silent retry |
| LC-32 | Secret-safe diagnostics | Seed credentials, URLs, paths/options and arbitrary secrets in provider exceptions/identity/text; zero seeded values in captured normal logs/results/serialized errors; safe code/correlation/action retained |
| LC-33 | Safe actionable rule coverage | Each invalid/failure row identifies safe module or ordinal, phase, rule/path and corrective action; bounded output/omitted counts, no raw inner exception |
| LC-34 | Truthful inventory/state | Distinguish registered build inclusion, enabled, phase, ready/unready/failed/stopped; no inferred exhaustive installed inventory or production support |
| LC-35 | Bundled restart journey | Same built baseline host switches Protocol.One/Protocol.Two selections only after new lifecycle, zero rebuild, old composition unchanged before stop; Artifact.One remains the bundled artifact choice |
| LC-36 | Independent custom journey | Artifact.Two absent from baseline references/registrations; add its independent package/registration/host adapter in custom variant, rebuild/redeploy/new start, zero Core or unrelated provider edits |
| LC-37 | Invalid replacement and recovery | New invalid selection fails without silent rollback; explicit prior package/selection + new lifecycle recovers; no persistent rollback claim |
| LC-38 | Architecture boundary proof | Actual project/packed/transitive/API graphs reject forbidden edges; Hosting HTTP/versioning allowed, Abstractions/Core remain provider-free, Metadata/Artifact have no Hosting edge |
| LC-39 | Source/binary/package compatibility | Existing registration consumers/implementers still compile and old supported binaries still run registration paths; new framework dependency documented and packed framework-reference propagation verified |
| LC-40 | Documentation/support audit | Current/future commands honest; budgets, cleanup, trust, phase/restart and curated/custom limits explicit; zero fixture-to-production/native-client/certification overclaims |

## Requirement Coverage

| Requirement | Proof cases |
| --- | --- |
| FR-001 | LC-02, LC-14, LC-34, LC-36, LC-38..39 |
| FR-002 | LC-17, LC-24..25, LC-34, LC-40 |
| FR-003 | LC-02, LC-07, LC-11, LC-13 |
| FR-004 | LC-03..05, LC-14 |
| FR-005 | LC-06, LC-09, LC-12 |
| FR-006 | LC-07..10, LC-12 |
| FR-007 | LC-01, LC-08, LC-10 |
| FR-008 | LC-01..14, LC-20..23 |
| FR-009 | LC-05, LC-16, LC-19, LC-24 |
| FR-010 | LC-15..19, LC-31 |
| FR-011 | LC-01, LC-15, LC-17, LC-23 |
| FR-012 | LC-17, LC-21..23, LC-25, LC-31 |
| FR-013 | LC-17, LC-22, LC-25..26 |
| FR-014 | LC-24..25, LC-30 |
| FR-015 | LC-20..23, LC-27, LC-29 |
| FR-016 | LC-22, LC-26..29 |
| FR-017 | LC-28..29, LC-33 |
| FR-018 | LC-22, LC-29..30 |
| FR-019 | LC-01..40 (fixture-only positive and rejection coverage) |
| FR-020 | LC-02..14, LC-18..23, LC-25, LC-28..29, LC-32..33 |
| FR-021 | LC-13, LC-35..37 |
| FR-022 | LC-34..40 |

## Outcome and Story Coverage

| Outcome | Proof cases |
| --- | --- |
| SC-001 | LC-01..14 |
| SC-002 | LC-15..16, LC-31 |
| SC-003 | LC-17, LC-21..25, LC-29, LC-31 |
| SC-004 | LC-20, LC-22..23, LC-26..30 |
| SC-005 | LC-32..33 applied to every invalid/failing matrix case |
| SC-006 | LC-13, LC-35..37, LC-39 |
| SC-007 | LC-34, LC-38..40 |

| Story scenario | Proof cases |
| --- | --- |
| US1-1 | LC-01 |
| US1-2 | LC-02, LC-07 |
| US1-3 | LC-03..06, LC-10..12 |
| US1-4 | LC-08..09 |
| US2-1 | LC-15 |
| US2-2 | LC-16 |
| US2-3 | LC-17 |
| US2-4 | LC-18..19 |
| US2-5 | LC-24..25 |
| US3-1 | LC-21, LC-23, LC-27 |
| US3-2 | LC-22, LC-27 |
| US3-3 | LC-26 |
| US3-4 | LC-28..29 |
| US3-5 | LC-30 |
| US4-1 | LC-33 |
| US4-2 | LC-32 |
| US4-3 | LC-34 |
| US5-1 | LC-13, LC-35 |
| US5-2 | LC-36 |
| US5-3 | LC-37 |

## Evidence Gates and Limits

Use the existing foundation and implemented lifecycle commands in
[quickstart.md](../quickstart.md). Introduced behavior needs regressions that
fail without the behavior, not tests merely restating constants or declarations.
No skipped assertion, missing packed input or empty test selection may yield
passing acceptance. Keep commands bounded and fail with sanitized actionable
errors; tests consume prepared package evidence without recursively invoking
the orchestrator.

Package-only example variants must restore locked from temporary local packages,
not source/project references to platform/providers. Compile and execute their
bounded lifecycle fixture journeys without starting a production service.
Retain framework/source/hash evidence and locks; review changed graph inspection
inputs explicitly rather than weakening F-01 rules to accept a new edge.

Before merge, obtain architecture review of actual implemented module ownership,
startup isolation and new graph; keep reviewer-owned requirements checklists
separate from automated acceptance. TestServer's application drain proof is
not socket/proxy/TLS/drain conformance. Cleanup is not provider migration rollback,
and API compilation is not native-client or provider certification.
