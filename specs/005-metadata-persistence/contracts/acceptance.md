# F-05 Metadata Acceptance and Qualification

**Status**: Implemented fixture proof obligations; measured command results
and review corrections are recorded in the [plan](../plan.md#implementation-evidence).
Each row requires a positive control and the stated rejection/fault assertion.
All assertions use public outcomes and committed contents unless specifically
testing provider-private recovery/configuration.

## Qualification Classes

**L: logical semantics** applies to both independently implemented fixtures.
**D: durable local recovery** additionally applies to real file-backed SQLite.
Memory must report D as `NotApplicable: non-durable fixture`, never a pass or
generic skip of an L obligation. Production support requires separate rollout/
operational acceptance; neither L nor D alone grants it. A provider missing a
mandatory applicable result cannot claim that class.

All cases have implementation/version/configuration attribution. No production
PostgreSQL, NoSQL, alternate filesystem, byte store, native protocol client or
F-07 certification follows from the fixture results.

## Common and Durable Cases

| ID | Class | Positive control and required negative/fault proof |
| --- | --- | --- |
| MP-01 | L | Round-trip every logical entity/optional field; reject missing/default identities and invalid relationships without changes |
| MP-02 | L | Same canonical package/request in two registries remains isolated; query for one cannot satisfy another |
| MP-03 | L | Same registry/request in two auth partitions remains isolated; include anonymous vs authenticated partitions |
| MP-04 | L | Preserve exact case/Unicode/escaped canonical keys; equivalent caller-normalized duplicate conflicts; reject malformed Unicode, credentials in URI, forbidden headers and invalid secret-reference shapes |
| MP-05 | L | Preserve accepted UTC millisecond/counter/size boundaries; reject fractional precision, overflow and oversized values without truncation |
| MP-06 | L | Scoped policies/aggregates round-trip; cross-registry policy association and invalid/overlapping-key aggregate input cannot cross scope |
| MP-07 | L | Traverse datasets of 0, 1, 100 and 205 rows in fixed order exactly once; oversized requests/results fail, not truncate |
| MP-08 | L | Resume same-query cursor; reject changed filter, registry, auth partition, size, version or epoch; demonstrate documented insert/delete/update semantics without snapshot promises |
| MP-09 | L | Commit multi-entity group all at once; injected failure after each candidate mutation leaves none visible |
| MP-10 | L | Barrier-coordinated grouped reads observe all-old or all-new; ordinary independent reads may straddle a commit |
| MP-11 | L | Competing first creates yield exactly one winner and explicit losers; no duplicate canonical identity |
| MP-12 | L | Competing same-revision updates/deletes yield exactly one winner; stale revision cannot overwrite after delete/recreate |
| MP-13 | L | Explicit bounded child+parent deletion works; referenced parent deletion and unbounded implicit cascade fail atomically; disable preserves children and blocks new publication |
| MP-14 | L | Same ticket/payload replay returns original receipt; changed committed payload conflicts; no duplicate state changes |
| MP-15 | L | Inject lost acknowledgment after commit, then reconcile receipt; reserved reconciliation abandons/fences a delayed commit |
| MP-16 | L | Retry uncertain aggregate contribution once; concurrent distinct-ticket contributions sum exactly with no duplicate deltas |
| MP-17 | L | Resolve tickets before expiry; at exact expiry/after pruning/foreign epoch refuse all execution, never blind replay |
| MP-18 | L | Cancel before admission/commit leaves no changes; cancel after unobserved commit attempt reports uncertainty, then reconciles |
| MP-19 | L | Finite queue/lock/authority budgets succeed below limit and fail at deadline; no hidden commit retry or over-capacity admission |
| MP-20 | L | Counter, ledger, queue and injected storage capacity limits yield classified failures, preserve prior state and do not evict live receipts |
| MP-21 | L | Explicit not-found selector succeeds only on absence; unavailable/corrupt state fails the group, never returns empty/miss |
| MP-22 | L | Safe error codes/corrective templates for every failure class; injected canary secret/connection/path/record content never appears in diagnostics, debugger strings or evidence |
| MP-23 | L | Authority-accepted publication succeeds; missing, uncommitted, forged or digest/length-mismatched evidence fails without entry/edge |
| MP-24 | L | Entry+edge replacement/removal atomic; multiple entries share digest without lost/double references under competing changes |
| MP-25 | L | Current zero-reference confirmation succeeds as metadata evidence; intervening publication/replacement invalidates stale reference revision, including ABA |
| MP-26 | L | Simulate committed blob then failed metadata; no valid new entry and explicit orphan reconciliation, never fictitious blob rollback |
| MP-27 | L | Publication guards retained through success/rollback and late commit settlement; cancellation cannot release protection or dispose live work |
| MP-28 | L | Acquire/renew/release exact lease owner; competitor/replayed old generation cannot act after reacquisition |
| MP-29 | L | Boundary `now == expires` rejects renew/release/guarded mutation; just-before expiry works, final decision rechecks expiry |
| MP-30 | L | Forward/backward clock changes and generation tombstones preserve committed expiry/fencing decisions; overflow fails rather than wraps |
| MP-31 | L | Batched telemetry success never changes entry/reference atomicity; invalid contribution rolls back its entire declared group |
| MP-32 | L | Empty/compatible/old/new schema classifications; ordinary calls blocked until admitted; inspect-only never silently creates/upgrades |
| MP-33 | L | Explicit create succeeds only for true empty state; unknown layout/version and corruption remain unchanged and blocked |
| MP-34 | L | Authorized supported upgrade preserves logical state; missing/stale recovery authorization or unsupported path fails before changes |
| MP-35 | L | One upgrade/use owner; competing attempts fail within budget; partial upgrade never admits normal use (memory proves state machine only) |
| MP-36 | D | Recovery point verified in isolated target; invalid backup/application/provider/capture and outstanding unresolved tickets block upgrade/restore admission |
| MP-37 | L | Owned work settles before normal cleanup; deliberately late work gives explicit incomplete ownership, blocks new admission and never disposes live resources |
| MP-38 | D | Kill child at M0 after uncommitted group changes; reopen sees none, baseline preserved, reconcile fences reservation |
| MP-39 | D | Kill at M1 after durable commit before acknowledgment; reopen sees complete group+receipt, replay adds nothing, committed artifact/reference distinction retained |
| MP-40 | D | Kill at M2 after acknowledgment; all acknowledged values/receipts survive; effective WAL/FULL/foreign-key settings and local environment recorded |
| MP-41 | D | Upgrade U0/U1/U2 kills recover complete v1, no mixed layout; explicit retry/restore succeeds with all baseline values |
| MP-42 | D | Upgrade U3/U4 kills recover complete v2/new epoch; old ticket/cursor execution rejected and no repeated migration |
| MP-43 | D | Real second-process upgrade/store exclusion and crash-released OS lock; no guessed lock deletion, bounded loser, unsupported future schema byte-for-byte unchanged |
| MP-44 | D | Quiescent driver backup captures committed WAL data; isolated restore matches full logical digest and documented capture point |
| MP-45 | D | Tested rollback to compatible v1 backup; newer writes intentionally absent, old tickets invalid, missing synthetic artifact set blocks cache-use claim |
| MP-46 | L | Unchanged package-only consumer completes same L cases with composition-only SQLite/memory switch; no concrete provider dependency in consumer logic |
| MP-47 | L | Existing architecture negatives plus permitted real packages; reject SDK/query/connection leaks; old marker/registration consumer binary runs unchanged |
| MP-48 | L | Manifest accounts for every required case with proof artifact; attempted conformance with missing/failed applicable case rejected; memory cannot claim D/production support |

## Determinism and Failure Evidence

Use controlled clocks/barriers and state assertions, not timing sleeps as
correctness proof. Concurrency tests use separate callers and actual separate
SQLite engine connections where relevant; one in-memory lock does not prove
SQLite isolation. Verify intermediate reads never see candidate changes.
Known queue/writer capacity fixtures prove budgets; process-isolated stuck
native-call fixtures prove bounded caller results and retained ownership.

Every new behavior must have a recorded red result before its accepted
implementation: e.g. stale revision accepted, receipt absent/double aggregate,
invalid publication visible, partial group or unsafe schema admission.
Use narrowly scoped test doubles/fault points for logical failures, but real
parent-terminated processes for D crash cases. Test hooks remain fixture-only;
no production backdoor or swallowed failure.

Private fixture storage/content is synthetic. Capture only fixed case IDs,
versions, PRAGMAs, timing/counter summaries and hashes, never raw connection
strings, canary secrets, SQL parameters or user record payloads.

## Story and Edge-Case Coverage

| Specification acceptance scenarios | Cases |
| --- | --- |
| US1.1..5: retain/isolate/validate/page | MP-01..08, MP-13, MP-40 |
| US2.1..5: grouped reads/conflicts/cancel/uncertainty/budgets | MP-09..22, MP-37..40 |
| US3.1..4: artifact evidence/orphans/references/leases | MP-23..30 |
| US4.1..5: schema/upgrade/incompatibility/interruption/restore | MP-32..36, MP-41..45 |
| US5.1..4: composition/mandatory guarantees/boundaries/support | MP-46..48 plus all applicable preceding cases |

The 14 edge cases map in specification order to: MP-02..05; MP-13;
MP-11..12/24..25; MP-10; MP-15/18/39; MP-14..17/31;
MP-28..30; MP-26/45; MP-20..21/36; MP-08; MP-05/29..30;
MP-35/41..43; MP-44; MP-22/47.

## Evidence and Regression Gates

`validate-metadata.sh` restores/builds with tracked locks, verifies
SDK formatting/analyzers, packages the fixtures independently, runs common and
durable tests, executes both consumer selections and retains the old binary.
Manifest fields: schema version, exact provider/module/package/native versions,
source commit, OS/runtime, effective configuration (safe allowlist), case ID/
class/expected applicability/result, durations, crash barrier/exit confirmation,
artifact digest and limitations. Every applicable case must pass with no
unexplained skips; report memory's non-durable exclusions explicitly.

New architecture negatives must demonstrate failures without weakening the
existing scanner. Run existing foundation/lifecycle/configuration/discovery
acceptance to preserve old registration/configuration/readiness/discovery
behavior. No source packages are published and no release tag or product CI
is introduced by this feature. Full commands appear in the
[quickstart](../quickstart.md). Focused/preparation selectors explicitly remain
non-qualifying; only full mode can report complete qualification.

## Measured Fixture Scope

| Provider | Logical result | Durable result |
| --- | --- | --- |
| SQLite 0.1.0, fixture-sqlite-v2 | All 39 L cases passed | All nine D cases passed |
| Memory 0.1.0, fixture-memory-v2 | All 39 L cases passed | Nine `NotApplicable: non-durable fixture` entries |

The final current-source locked run verifies all 96 entries, with 87 applicable
passes and no missing/failed/skipped applicable case. It executes 59 common tests
per provider, all eight M/U crashes, additional R0/R1 restore interruptions,
native-stall ownership, backup/restore, unchanged consumers, frozen marker
compatibility, seven actual package graphs and both runtime mutation pairs.
Source/configuration attribution, exact commands/results and resolved review
findings are in the [plan](../plan.md#implementation-evidence). The measured
macOS/APFS process-stop scope grants no production, other-engine/filesystem,
power-loss, multi-node or F-07 claim.
