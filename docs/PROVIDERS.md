# Provider author guide

F-01 supplies source-level .NET 10 declarations and registration-only composition
at local acceptance package version `0.1.0`. Nothing is published to nuget.org.
There is no working cache, production persistence provider, protocol, byte store, authentication,
or certification. F-02 adds opt-in fixture-tested module lifecycle in
Hosting; F-04 adds protected metadata/observations, not provider operations. Start with the
[compile-only host](../examples/CustomHost/README.md) and
[validation quickstart](../specs/001-provider-contracts/quickstart.md).
For lifecycle use, see the [package-only lifecycle host](../examples/LifecycleHost/README.md).

F-07 shared conformance is partially implemented, not available as provider
certification. Its SDK now has 53 executable metadata methods, typed sessions,
an identity-pinned allocator, bounded runtime logger and exact discovery/origin
transport. Native run
[40059814134](https://github.com/Stonefly-Labs/Hoard/actions/runs/40059814134)
verified those initial consumers and factory/settlement prerequisites:
131 foundation checks without failures/errors/skips, 34 scopes/150 observations,
six historical baselines and eighteen-package/thirteen-lock replay.

`Hoard.Fixtures.Conformance.Bindings.Memory` now implements explicit current/
legacy setup, typed logical controls, independent committed snapshots and atomic
logical reopen. Its `MemoryBinding` constructor requires the provider archive's
actual SHA-256 (and version); declarations do not independently prove package
provenance. The harness supplies `ConformanceRunContext`, owns cleanup and must
bind actual observed role/assembly/package origins. The adapter closes admission
before pinning the genuine work task, preserves that identity on retries, and
never reports physical `Released`. Memory remains non-durable; logical image/
upgrade controls grant no backup, durable restart or process-crash guarantee.
Private encoding mutation is shared by the adapter and existing focused tests,
without an SDK reference in Memory or private provider types in the SDK.
Twenty focused adapter rows pass against locally packed packages, including the
real 30-second incomplete cleanup and actual allocator retention/retry.
Native run [40061416909](https://github.com/Stonefly-Labs/Hoard/actions/runs/40061416909)
verified those rows within 37 scopes/170 exact observations, alongside all
131 foundation checks and unchanged six-baseline/eighteen-package/thirteen-lock replay.
The SQLite fixture now exposes genuine worker-lifetime settlement and tracked
async independent read/writer controls. Cancellation of a control caller does
not release the underlying work; shutdown waits for late native handles.
The initial SQLite binding uses those tracked controls, with explicit current/
legacy factories and same-database reopen. A single directory transfers only
after the old worker actually closes; no old lifetime task is bound to a
directory subsequently reused by a new worker. Only the final head registers
that directory's genuine lifetime with the resource observer. Failed/canceled
handoff keeps the original owner and pending work available for final disposal.
Real fixture backups authorize upgrades; raw record/operation/token corruption
preserves SQLite BLOB/TEXT/NULL/REAL distinctions and exact restoration.
Raw fingerprints use read-only transactions without schema admission/repair,
native value/progress limits, bounded size preflight and sorted row digests,
not a native full-payload sorter. The existing synchronous fixture helpers
retain their caller-owned semantics.

The same logical publication authority source is compiled into both binding
assemblies, without cross-provider delegation or a new SDK dependency.
The package-mode graph now has seven local archives. Its intentional NuGet lock
adds only the SQLite binding/provider and six pinned SQLite dependencies,
preserving prior graphs/third-party hashes. A separate empty-cache locked build
passes. All 179 selected Memory/SQLite package tests pass locally without skips
(95 Memory, 84 SQLite); this includes actual incomplete cleanup, not Linux
supervisor/category qualification. Native run
[40066075996](https://github.com/Stonefly-Labs/Hoard/actions/runs/40066075996)
passed all three jobs, 134 foundation checks without failures/errors/skips and
50 scopes/254 exact observations, including all 84 SQLite identities.
An owned package-only environment probe observes
actual SQLite PRAGMAs/version and the loaded native module, validates its bytes
against the pinned NuGet archive, and fingerprints runtime native assets.
That run verified actual SQLite 3.53.3 loading. SQLite test dispatch rejects
missing actual environment/native-runtime inputs and never borrows `nativeSqlite: not-used`.
NuGet's normalized signed-package content hash remains pinned separately from
the downloaded archive hash; both fresh locked-restore receipts and exact native
member bytes are verified, with unchanged pre/post provenance. Child temporary
files are routed into private owned caches, not global temporary storage.
The isolated diagnostic requests actual native non-cooperation in a dedicated owned
child: publication guards remain held after the caller deadline and failed
cleanup, and the parent admits proof only after its PID/start-bound watchdog
confirms SIGKILL and group exit. Native run
[40067365972](https://github.com/Stonefly-Labs/Hoard/actions/runs/40067365972)
at `7530cad` verified this complete observation/containment pair; this does not
complete inherited crash/recovery or category qualification.
All 53 current SDK logical assertion methods now execute through SQLite too;
the additional 44 parameterized rows cover actual independent reads, clocks,
publication, corruption and decision/settlement controls. This local 179-test
selection is not the catalog's 179 applicable category results or wrapper parity.
The original MP-01..06/13 wrappers now invoke the same packaged SDK assertions.
A thin test-side authority bridge delegates to the original fixture authority;
it does not replace provider setup, clocks, schema preparation or disposal.
All 72 predecessor tests pass against each provider using the identical compiled
suite and SDK. Ten more original wrappers now share paging, concurrency,
publication-evidence and reference assertions (17 delegated methods total);
all 21 affected class tests pass against each provider without skips.
Its eight-archive preparation adds the SDK, while the independent binding
diagnostic still uses seven archives. Other wrappers remain unextracted.
Five further atomicity/publication wrappers now use scoped typed observations
(22 delegated methods total). The original fixture adds ownership-safe
registration and a cancellation-aware independent-read overload without SDK
dependencies or changing existing operation signatures. Unregistration removes
only that registration, never another owner or active work. The full 76-test
suite passed against both providers; after adding the actual schema-hook check
and SDK-canary assertion, all 16 affected tests passed against each provider.
Only the additive HostAdapters fixture archive changed; SDK/provider/platform
archives and repository/historical locks remain unchanged by this increment.
The subsequent schema-boundary repair adds `SchemaCandidatePrepared`: SQLite
maps it to U1 after candidate creation with the native writer held, while its
existing `BeforeSchemaUpgrade` remains U0 before the transaction. Memory maps
both observations to its actual upgrade decision. The unchanged shared
exclusion consumer and original MP-35 now select the distinct candidate hook.
A second real SQLite connection must receive BUSY (5); the regression failed
at U0 before repair. Final packages pass 180 selected binding/SDK tests and
11 original schema/observer tests per provider without skips. Fresh locked
eight-archive replay reproduces exact DLLs; only the tracked SDK archive hash
changes, preserving the predecessor dependency graph and all other lock entries.
The requested Linux vector becomes 50 scopes/255 observations, including
85 SQLite identities. Native
[40070802352](https://github.com/Stonefly-Labs/Hoard/actions/runs/40070802352)
at `3bca09c` verified that vector, 136 foundation checks without skips,
native containment and identical eighteen-package/thirteen-lock replay.
The six original MP-08 malformed-continuation rows now use the same shared
consumer, bringing adoption to 23 original methods. Fixture-private mapping
forwards to each provider's existing independent payload-damage helper.
A parity guard enumerates every actual cursor field and proves typed omission
covers it while preserving all other values. Memory's combined epoch/schema
field is covered without inventing a separate encoded field. Cancelled and
unknown controls reject without modifying the valid continuation. All 79
current predecessor tests pass without skips against each provider using the
same SDK/suite bytes. Fresh locked replay reproduces eight archives and exact
DLLs; only the additive HostAdapters archive changes from the schema repair.
Six further original MP-19/20/28/32 wrappers now delegate to the existing
admission, storage/ledger capacity and lease-generation/fencing consumers
(29 delegated methods total). Admission still uses fresh unadmitted stores,
not the prepared ordinary-case helper. A thin counter bridge observes actual
fixture activity and diagnostic counts; capacity/generation callbacks preserve
existing controls and check cancellation before dispatch. All 16 affected
class tests pass against each provider without skips using the same compiled
suite and seven byte-matched dependencies. No package or source-lock changes
accompany these delegates.
Three more MP-17/29/30 wrappers now share clock-dependent consumers through
callbacks that drive the original `MetadataTestClock` supplied to the store
(32 delegated methods). Existing SDK clock signatures forward to those same
assertion bodies. All three final-decision lease actions retain independent
fresh fixtures. A new actual-store regression proves clock rollback reaches
the original clock while issued tickets retain their monotonic floor.
All 80 predecessor tests pass on each provider without skips, alongside
180 selected SDK/binding tests. Fresh locked replay reproduces eight archives
and exact DLLs, with the identical SDK archive in both feed families. Only its
SDK hash changes in the tracked predecessor lock; other entries remain pinned.
Eleven more original deadline/reconciliation/replay methods now use shared
consumers (43 delegated methods). The fixture adds a cancellation-aware writer
overload while preserving its old signature; a test-side disposable lease
releases only its own holder. Settlement forwards the original actual idle
observation, not caller-task completion. A new cancellation/ownership regression
first failed the missing overload assertion, then proved cancellation leaves
the existing writer held, the timed-out commit absent and same-ticket retry
successful only after release. All 81 current predecessor tests pass on each
provider without skips, including genuine 30-second incomplete cleanup.
Fresh locked replay reproduces eight archives and exact DLLs; only the
additive HostAdapters archive changes from the clock increment. SDK/provider/
platform archives and source locks are unchanged.
Four original corruption wrappers now also share consumers (47 delegated
methods), including all five query-dimension rows and fourteen receipt shapes.
Original fixture scopes own target-specific corruption, reject overlapping
owners and atomically exclude new owners once closure/reopen is admitted.
Failed restoration retains a recoverable owner; cancellation after mutation
restores before release. Native capture/observation uses actual separate,
bounded read-only connections. Replacement checks the captured record/image
inside the real writer transaction; Memory checks under its own writer.
An intervening commit yields `Conflict` without restoring the obsolete image.
Restoration waits for genuine idle settlement before deciding whether mutation
occurred and verifies original bytes before releasing an applied scope.
All 87 current predecessor tests pass on each provider, and 181 selected
SDK/binding tests pass locally. Fresh locked replay reproduces eight archives
and exact DLLs; seven binding output DLLs match their archives and both feed
families retain the unchanged SDK. Native
[40097647586](https://github.com/Stonefly-Labs/Hoard/actions/runs/40097647586)
at `84e8a4b` verified 50 scopes/256 observations (86 SQLite identities), actual
containment and identical eighteen-package/thirteen-lock replay.
The MP-22 diagnostics wrapper now also shares consumers (48 delegated methods).
Its original connection-shaped failure hook and canary remain fixture-owned;
an additive overload shares the counter, rollback, failure-shape and diagnostic/
debug-display assertions without replacing that hook. The prior signature
continues to install its own scoped hook and forwards to the same core.
A new actual-store regression proves the original callback still owns its
registration after the consumer returns. All 88 current predecessor tests pass
on each provider, and 181 SDK/binding tests pass locally. Fresh locked replay
reproduces eight archives and exact DLLs; both feeds have identical SDK bytes.
Only its hash changes in the tracked predecessor lock; other entries stay
pinned. The native checkpoint predates this increment and does not execute
original wrappers. Schema extraction and exact origin integration remain open.
The five original schema wrappers now delegate as well (53 methods total).
Their narrow `IMetadataSchemaAssertionSession` projection exposes only actual
original fixture controls; it is not admission as a complete category binding.
Recovery authorization and same-database reopen retain original ownership.
SQLite fingerprints stream actual database/WAL bytes inside owned independent
work; initially observed WALs remain mandatory, while newly created empty WALs
do not imply mutation. Memory fingerprints its actual immutable logical image.
Cancelled physical reads settle without false internal-failure diagnostics.
All 89 current predecessor tests pass on each provider and 183 selected
SDK/binding tests pass locally, with independently replayed exact package/DLL
bytes. Run `40098981184` at `11875e5` verified the previous diagnostics checkpoint,
50 scopes/256 observations and native containment; it does not run original
wrappers. Schema run `40100325269` at `82a9b09` subsequently verified 50 scopes/
258 observations, all 88 SQLite identities and actual native containment.
Exact frozen parity and controller-origin integration remain unfinished.
The diagnostic now includes the original packaged test assembly, selecting all
63 frozen original runtime identities per provider, not only newer binding tests.
Its seven-package graph is privately rebound without changing tracked locks;
the logger is installed only as a byte-verified runtime adapter. Original
wrapper, provider, Hosting and shared SDK images enter immutable pre/post inputs.
Exact safe discovery precedes execution. Native run
[40101331484](https://github.com/Stonefly-Labs/Hoard/actions/runs/40101331484)
at `8065dfc` verified all 52 scopes/384 observations, including all 63 original
identities per provider, and actual native containment. These diagnostics do not establish
session-origin completeness, legacy acceptance-import safety, recovery controls
or category qualification.
Five original artifact publication wrappers now forward to common SDK assertions
using only `IArtifactStore`. Both actual independent options retain absence/empty
content, positive short reads and true EOF, exact expectations, unsupported
requests and fully verified immutable duplicate incarnations. Existing wrapper
helpers and nested short-read type forward to that same implementation.
An actual-store source-substitution mutation reaches two successful native
stages/commits but fails the common duplicate EOF assertion; each unchanged
store then passes. Fresh eleven-archive locked replay verifies every dependency
image, and 250 artifact tests pass without skips. This selection excludes the
seventeen tests requiring actual process/transfer proofs; no inherited proof,
durability exclusion or category acceptance is replaced by this focused result.
The legacy artifact preparer still assumes unchanged F-06 metadata and an old
SDK-free source tree; its historical/candidate recipe split and safe import
remain unfinished.
The Linux diagnostic additionally selects all twelve frozen publication
parameters and both actual-store source-substitution pairs from the original
artifact test assembly. Its ten-package graph is privately rebound without
editing tracked locks, and every dependency/logger image is archive-verified.
The expanded 53-scope/398-observation request awaits native execution; it remains
diagnostic transport, not artifact binding/session-origin or category evidence.
Three further original wrappers share provider-free read/deletion checks:
destination failure/borrowed streams, exact delete receipts with recreation and
stale-incarnation fencing, and a reader held across deletion admission.
Original authority setup remains in each fixture; the common reader scope
releases exactly once before observing deletion, also on assertion failure.
All 37 affected class tests, 250 non-external-proof artifact tests and 89 metadata
tests per provider pass with independently replayed eleven-archive bytes.
The six exact frozen read/deletion parameters are selected separately in the
native diagnostic, expanding it to 54 scopes/404 observations, pending.
Exact receipt/protection validation and permanent quarantine assertions now
share common consumers as well. Fixture-owned Local durable reopen remains
separate; ObjectSemantics never borrows that proof. Actual-validator mutation
pairs fail the common receipt assertion and pass with the original validators.
Fresh eleven-archive replay passes 252 non-external-proof artifact tests and
89 metadata tests per provider. Their 23-identity diagnostic scope expands the
pending native request to 55 scopes/427 observations.
Publication transport is verified by native
[40103524667](https://github.com/Stonefly-Labs/Hoard/actions/runs/40103524667):
143 foundation checks, 53 scopes/398 exact observations, actual original
publication/mutation execution, native containment and eighteen-package/
thirteen-lock replay. It does not verify these subsequent extractions.
Native [40105402168](https://github.com/Stonefly-Labs/Hoard/actions/runs/40105402168)
verifies the subsequent exact evidence/quarantine scope and mutation pair:
all three jobs, 145 foundation checks, 55 scopes/427 observations, native
containment and eighteen-package/thirteen-lock replay. It does not verify the
later owning-controller or recovery changes.

SQLite recovery diagnostics now use an explicit safe-event runner mode and
parent-owned barrier termination, requesting all ten mutation/upgrade/restore
barrier/readback rows plus the actual backup/restore walkthrough. Fresh locked
builds verify actual runner dependencies; local walkthroughs preserve legacy
output and pass in safe mode. Linux crash execution is pending, and live-held
probes, exact wrapper/session attribution and full category qualification remain
open. These diagnostics confer no memory or ObjectSemantics durability.

Local now has the same explicit safe-event runner integration for its six
publication/deletion crash/readback rows, sharing only parent receipt admission
with SQLite, never provider mechanisms or simulation durability. Fresh locked
runner builds and macOS functional readbacks pass; actual Linux owning-controller
execution subsequently passed at `e6d79f4`, including all six Local rows.
Large transfer/RSS proofs and category/session/
legacy witness integration remain unfinished.
SQLite's ten actual kill/readback rows and backup/restore walkthrough have
subsequently passed on Linux at `62c149c`, with all three jobs successful.
The transfer controller now requests both artifact providers' actual paced
256 MiB/4 GiB writes and reads, with parent-owned kernel RSS/high-water
observation and exact producer binding. All four real macOS rows and their OS
peak bounds pass; Linux owned measurement subsequently passed all four rows at
`d429dd2`, run `40109299238`. Original wrapper/session imports
and full category acceptance remain pending. ObjectSemantics borrows no
SQLite/Local durable recovery proof.
The same actual runner now exposes safe two-phase live inspection for retained
source/destination/native workers on both providers. The parent requests the
second original inspection before owned termination and admits matching
phase/run/PID/retention records. Linux execution passed all six rows at
`c7eb90c`, run `40110165383`, with 165 foundation checks and all three jobs
successful. This work explicitly supplies no durable crash proof.
All seventeen original external-proof artifact wrappers and four bounded
child-output cases are now requested after these real diagnostic prerequisites.
Sixteen identities are frozen category witnesses; the existing cross-process
root-ownership fact is additional, not a new frozen category entry.
Two fresh-cache locked builds pass all 21 cases and verify ten dependency images.
Child captures are bounded before return/persistence; healthy legacy empty error
files remain, but failure stderr is not copied into proof files. Linux execution passed at
`4e3ef47`, run `40111391053`, with all three jobs, 167 foundation checks and
56 scopes/448 exact observations, including all 21 external/capture identities.
Complete session/category imports remain pending.

Current package preparation now uses current metadata/SDK sources and an
eleven-archive artifact feed; it does not rebuild historical metadata with
today's SDK-dependent recipe. Shared explicit lock derivation changes only local
archive hashes in private alternate locks, verifies original/prepared/feed bytes
and preserves tracked locks plus all external graph pins. Ordinary and
package-acceptance lock paths cannot be substituted. Two fresh-cache locked
preparations reproduce all eleven archives, verify ten loaded dependency images,
and each pass all 273 artifact cases plus 89 metadata cases on each provider.
These are actual functional/preparation results, not complete input-bound
legacy/session/category imports or replacement historical binaries.

The original publication race wrappers now forward all three methods/six frozen
parameters to provider-free consumers. Real fixture observer and payload
damage/restore operations remain fixture-side; expectations and ordering remain
shared. A real-store adapter that repairs a forged length fails the original
`InvalidInput` type assertion on both providers, while fresh genuine stores pass
the same unchanged consumer. Mechanical body comparison preserves all original
checks and control ordering after explicit seam/token forwarding.
Two fresh-cache locked builds reproduce eleven archives, verify ten loaded
artifact dependency images and each pass 275 artifact cases plus 89 metadata
cases per provider without skips; accepted-source formatting also passes.
The additional exact native scope is six original rows plus two named mutation
rows. It passed at `91da8f4`, run `40113497329`, with all three jobs, 169
foundation checks and 57 scopes/456 observations, not category completion.

Private staging and all four original reconciliation methods now use shared
consumers with their ten frozen parameters intact. Actual prefix barriers,
clock advancement/rollback, authority setup and lost-acknowledgment observers
remain fixture-side; common consumers retain every original check and ordering.
A real-store mutation first reconciles the original ticket, then substitutes a
genuine receipt from a different actual publication. The unchanged consumer's
receipt-equality assertion fails on both providers; reconciliation/publication
counters prove the intended mutation, and fresh genuine stores pass unchanged.
The next exact native scope adds eight original reconciliation witnesses plus
two mutation parameters. It passed at `517b911`, run `40114439905`, all three
jobs and 170 foundations with 58 scopes/466 observations, not category or
complete session evidence.

The three original visibility bodies now run provider-free shared checks while
fixture callbacks retain actual receipt/listing/direct-availability boundaries.
Their exact checks/order are mechanically preserved. A Local mutation starts
the actual held commit but returns a genuine earlier receipt immediately;
the unchanged pending-task assertion fails. The test releases the actual hold,
awaits the genuine commit and verifies its distinct published stamp; a fresh
genuine provider passes unchanged. The next native request adds these three
frozen witnesses and the mutation: 59 scopes/470 observations. It passed at
`793ad65`, run `40115175363`, all three jobs and 171 foundations.

Five original history/budget bodies now run shared checks: incarnation/history
capacity, bounded candidate examination/resumption and ticket-expiry capacity.
All original assertions/order remain, with actual clock, limits, authority setup
and candidate registration fixture-side. Eight identities are frozen category
witnesses; eight additional existing fixture identities are requested explicitly
without changing the frozen catalog. A real-store adapter hides the actual
injected candidate failure behind one actual retry, causing the unchanged
consumer's expected failure-type assertion to fail on both providers. Counters
corroborate actual candidate observation, 106 reservations, one hidden failure
and one retry; genuine stores pass unchanged. The next native vector adds these
sixteen originals and two mutations: 60 scopes/488 observations. It passed at
`37ec19a`, run `40116055015`, all three jobs and 172 foundations.

Four original stream-ownership bodies now run shared checks: cooperative
inactivity, idle-read expiry, noncooperative source and noncooperative destination.
All eight frozen parameters and all three real stream-helper bodies are
preserved. The legacy pending-source name forwards to the same SDK helper,
not a separate implementation. Actual clock and settlement remain fixture-side.
A real-store mutation requires an actual cancelled source with retained live
ownership, then falsely reports released cleanup. The unchanged shared equality
assertion fails on both providers. The original release runs, actual work
settles, and fresh genuine stores pass unchanged. This is logical stream-
ownership proof, not a new durable crash or kernel RSS claim. The next ten-row
native scope requests 61 scopes/498 observations. It passed at `5974f38`,
run `40116943400`, all three jobs and 173 foundations; complete qualification
remains unfinished.

Three original cancellation/current-owner bodies now run shared assertions:
external renewal survives older cancellation, progress renewal fences the same
admitted owner, and invalid/stale cancelled descriptors preserve the current
verified handle. Two identities are frozen category witnesses; eight are
additional existing fixture cases. Actual clocks, publication/progress observers,
boundary removal/release and worker settlement remain fixture-side. A real-store
mutation waits for the actual rejected commit to settle, then abandons the
current verified owner. The unchanged pending-state type assertion fails on
both providers; one stage, one commit and one actual abandonment corroborate it.
Fresh genuine stores pass unchanged. The next twelve-row native scope requests
62 scopes/510 observations, pending, not complete binding/category/session proof.
Four original result-handoff/expiry bodies now also run common checks with all
twelve frozen parameters. Actual completion/release observers, barriers, clock
and settlement remain fixture-side. Hiding a genuinely reserved ticket after
cancellation fails the unchanged success assertion on both providers; publishing
that same ticket corroborates the intended ownership fault and genuine stores
pass unchanged. The next fourteen-row native scope requests
63 scopes/524 observations, pending, not full qualification.

Complete category suites/adapters, contributor workflow and controller/profile
ingestion remain unfinished. Focused composition/version fixtures
do not establish category or host-profile qualification. CP-11 preserves actual
route rejection during mapping before publication/initialization/readiness;
declaration validation remains preconstruction. Responsibility IDs are not
route declarations, and product contracts are unchanged.
Do not use the new executor as acceptance-ready tooling. See the
[implementation checkpoint](../specs/007-provider-conformance/plan.md#partial-implementation-checkpoint).

F-06 adds **fixture-qualified** BCL-only operations in
`Hoard.Abstractions.Storage`, separate from the unchanged `IArtifactProvider`
marker and historical `Metadata.ArtifactDigest`. Initialization/coordination
fixtures now exercise complete-stream verification, protected copies, exact
receipts, fenced cleanup and deletion. The host adapter composes unchanged
SQLite/memory packages with actual evidence validation and current reference
queries under the shared authority. Local crash checks use actual killed
children and fresh reopen; object semantics remain process-local. The
packages also have focused resolved-graph/public-member inspection, leak
negatives and frozen-marker compatibility checks; these do not certify a
production implementation. The unchanged package-only consumer now exercises
all 16 store/evidence/maintenance/read/authority operations on each choice,
including independent guard retention, exact reconciliation, abandonment,
deletion and safe recreation. Actual compiled-body inspection rejects hidden
concrete-provider coupling; the independent object mechanism has no filesystem
rename calls. Both fixtures declare the mandatory baseline and become ready
after successful explicit admission; missing guarantees/version/authority
reject before root I/O. The final locked run qualifies 92 applicable cases
with exactly four Object durability exclusions on the recorded macOS/.NET/APFS
environment. Neither fixture is a production provider or remote service. The local-package
hash blocker is resolved with reviewed hash-only lock updates and separate
default locked regressions; versions, dependency graphs and frozen baselines
are unchanged. Follow the
[final evidence](../specs/006-artifact-storage/plan.md#final-fixture-qualification-and-handoff-2026-10-22)
and [API inventory](../specs/006-artifact-storage/contracts/artifact-api.md)
for actual availability. These fixtures do not grant production or F-07
certification to another implementation.

Streams are borrowed at their current position: providers never seek, flush or
dispose them. Destination bytes are invalid unless the full verified copy
completes. A timeout does not prove physical settlement: non-cooperative I/O
retains its bounded handles, slots and opaque guards, reports incomplete cleanup
and blocks admission rather than releasing live protection. Use the exact
reserved ticket to reconcile uncertainty; never replay it as a new mutation.
The fixture child runner exercises source, destination and synchronous native
stalls on each provider. Parent-controlled inspection confirms retained work,
borrowed streams, root ownership, applicable guards and incomplete shutdown
before terminating the exact owned child; this is unsupported-worker containment,
not a durable crash or cooperative-release pass.
Qualification records reject durable-case exclusions for Local and require
exactly AS-41..44 for the process-local simulation; the classes cannot be exchanged.
Construct records with `ArtifactQualificationEnvironment` and 48 immutable
`ArtifactQualificationCaseResult` values, each with a closed status, duration
and bounded proof hashes. Environment labels are bounded printable ASCII;
their SHA-256 is derived from the four newline-delimited labels. Aggregate
hashes and exclusions are derived from the results. The former flat
case-name/hash constructor deliberately throws rather than implying qualification.
Report validation checks inner case/context identity and actual passed TRX
witnesses, not merely the outer file hash. The exact per-AS catalog requires
every provider/parameter variant; full acceptance also cross-binds actual
package, lock, configuration, capability and environment inputs, measured
transfers, killed-process recovery and materialized public qualification records.
The former five-argument session factory remains available. Trusted fixture
composition can explicitly provide `ArtifactFixtureAdmissionProfile` for a
known-identity Local reopen; there is no automatic root discovery/reset.
Object replacement uses a fresh root/epoch and cannot reconcile old tickets.
Successful result handoff and cancellation are serialized. If cancellation
wins first, the provider retains responsibility for reclaiming unclaimed
tickets/staging/read sessions. Exact-generation cleanup remains valid after
ownership expiry without authorizing new work. Failed reclamation blocks
readiness/new admission and retains root ownership; bounded `StopAsync` retries
only that resource and never starts a duplicate live cleanup attempt.
Failed prefix reclamation is observable and retryable by its exact staging
generation, including finalized noncommits, without waiting for ticket expiry.
Maintenance does not reopen finalized tickets or reclaim committed bytes.
Settled commit receipts remain reconcilable while residual staging is pending;
exact cleanup preserves those receipts and restores capacity/readiness.
Recovery continuations are single-use: a successful page replaces its consumed
handle, and a terminal page releases it. Up to 32 independent scans can progress
beyond 32 pages without artificial expiry waits; query/page-size/store/revision/
expiry checks and explicit listing consistency still apply. See the
[follow-up evidence](../specs/006-artifact-storage/plan.md#convergence-follow-up-implementation-2026-10-22).
The Object fixture also registers each unselected assembly before file creation.
Its scratch pool reserves the verified length, at most the configured staging
byte limit and transfer-slot count, independently of multipart reservations.
Thus multipart plus assembly scratch is bounded by twice the staging byte limit;
selected/retired content is accounted separately. Failed unlink retains the
exact assembly and original multipart reservation, blocks readiness/admission
and prevents commit retries from allocating more payloads. Exact staging
maintenance or bounded shutdown retries reclaim only that unselected object.
Partial assemblies count their reserved maximum until actual removal; cleanup
reports actual reclaimed bytes. Conditional selection transfers the object out
of scratch ownership atomically. Equivalent reuse retains its original selected
content and settled receipt even when the redundant assembly cannot be removed.
See the [T089 evidence](../specs/006-artifact-storage/plan.md#unpublished-object-cleanup-implementation-2026-10-22).
Every committed-content corruption detection quarantines the exact current
incarnation, including missing payloads, validation-first truncation, duplicate
verification, full-copy completion and unresolved-publication reconciliation.
Restoring bytes externally cannot revive opens, evidence validation or reuse;
explicit authorized deletion/recreation produces a different incarnation.
Local persists quarantine across compatible reopen; Object retains it only
within its declared process lifetime. Permission failures and unavailable
directories remain distinct failures, not corruption. Quarantine persistence
failure retains the Local in-memory fence, blocks readiness/new admission and
keeps root ownership. Restore access and retry bounded `StopAsync` until the
pending record is durable before reopening; failed stop is not resource release.
Finalized receipts remain historical decisions, not current health certificates.
See the [T090 evidence](../specs/006-artifact-storage/plan.md#corruption-quarantine-implementation-2026-10-22).
Expired ticket history may be retired, but live content identity remains
independent of its receipt anchor. Retained tombstones and reclaimed-incarnation
records also consume finite bookkeeping capacity until safe expiry-based
compaction; active or unresolved ticket work prevents premature removal.
Admission examines at most 100 ticket candidates and 100 candidates per retained
history index, with at most 100 history retirements. Rotating cursors and
incremental exact-incarnation dependency indexes preserve progress without
whole-table dependency scans. Capacity can remain unavailable while these
bounded pages advance; providers do not hide an unbounded sweep or retry.
An admitted reconciliation preserves an already-finalized receipt even if
another operation subsequently deletes and recreates the digest.
Logically removed content can still occupy space until exact-incarnation
reclamation is confirmed. See the [current quickstart](../specs/006-artifact-storage/quickstart.md)
for full/focused commands and the precise qualification limits.

## Public ownership and authoring

`Hoard.Abstractions` owns immutable sealed module records in
`Hoard.Abstractions.Modules` and the `IHoardProvider`, `IProtocolProvider`,
`IMetadataProvider`, `IArtifactProvider`, and `IIdentityProvider` markers in
`Hoard.Abstractions.Providers`. All are BCL-only. Markers grant no operations or
permissions. Core references Abstractions only and has no operational members.
Application owns the two discovery slices and references Hosting/framework,
never concrete providers or another slice's internals. Hosting owns DI/HTTP integration and internally uses
NuGet.Versioning; its package propagates the ASP.NET Core shared-framework
requirement, including to non-web registration-only consumers. This is a
deployment prerequisite change, not a change to the old registration signatures.

The [public API contract](../specs/001-provider-contracts/contracts/public-api.md)
and [declaration model](../specs/001-provider-contracts/data-model.md) specify
every field. Expose a static immutable `Declaration` as the
[protocol fixture](../tests/fixtures/providers/Protocol/ProtocolProvider.cs)
does; explicitly populate required properties and use `[]` for empty immutable
collections. IDs follow `[a-z0-9]+([.-][a-z0-9]+)*`. Versions have three SemVer
components. Metadata describes dependencies, capabilities, configuration
requirements, endpoint/health responsibilities, and provenance, not resolved
secrets, route delegates, probes, current health, or selected implementations.
Source/support URLs must be public and contain no credentials or private details.
`Fixture`, `Community`, and `MaintainerSupported` are provenance declarations,
not certification. The five test fixtures advertise no operational capability.

`services.AddHoard().AddModule<TProvider>(declaration)` records an immutable
`HoardModuleRegistration` containing the supplied declaration and type token.
It preserves duplicates, requires no public/default constructor, and neither
constructs a provider nor builds a container. Null arguments throw
`ArgumentNullException`. Invalid IDs, default arrays, category/type disagreement,
version conflicts, and invalid selections are representable for later
validators; registration is not validation, enablement, readiness, or fallback.

## Composition, family selection, and trust

A future curated distribution will configure only already bundled providers.
A custom distribution must reference packages and explicitly register types,
then rebuild, redeploy, and restart an operational host. Build-time NuGet restore
is not runtime installation. No arbitrary assembly loading, runtime downloads,
hot installation/replacement, sandbox, or marketplace is delivered.
Provider code, including static metadata getters, is trusted in-process code
with the host's privileges. Packaging does not isolate malicious code.

Multiple protocols and identity schemes may eventually coexist. Initially
there will be one authoritative metadata provider and one artifact provider;
F-01 does not enforce selection/cardinality. Authentication remains distinct
from centralized authorization. Provider implementations must not depend on
other concrete providers, even of the same family. SDK/EF/schema/migration
details stay private to their owning provider, never Core or endpoint contracts.
Do not expose `DbContext`, `IQueryable`, transaction/connection objects, vendor
SDK objects, HTTP context, delegates, or arbitrary payload escape hatches in
provider-neutral declarations.

Cache identity/auth partitioning, freshness, safe upstream/SSRF policy,
integrity and verified atomic publication, bounded asynchronous streaming and
cancellation, single-flight, reference-safe deletion/GC, authorization, and
shared audit/telemetry remain centralized Core/security/Hosting responsibilities.
Markers never authorize a provider to bypass or duplicate these invariants.
No rename, portable transaction, NoSQL interchangeability, or cross-store
atomicity guarantee follows from a marker.

## Safe discovery metadata and observations

Register `AddHoardDiscovery(catalog, options)` on the same `HoardBuilder` before
`EvaluateConfigurationAsync` or `ValidateComposition`. Frozen immutable
inclusion records are explicit knowledge, not assembly scanning. Complete
inventory can establish absence; a partial catalog cannot. Registration,
enablement, selected authority, provenance, tested support and observed readiness
remain separate dimensions. Existing provider markers/descriptors/interfaces
and discovery-free registration/configuration/lifecycle signatures are unchanged.

Descriptions, ordinary public defaults/choices and publisher labels need
separate host-approved plain-text publication records. Raw provider descriptions,
URLs, private option values/sources and secret locators are not public defaults.
Secret fields omit defaults/choices/examples. A declaration or healthy startup
does not establish support: contributions need exact capability/version/operation/
owners/evidence scope plus actual sealed route/method and/or effective unkeyed
owner-added service evidence. Factories are never resolved to establish it.
Multi-owner contributions emit once; unrelated not-ready modules do not veto
an independent operation.

`lease.BindHoardDiscovery(app)` returns only the exact composition's safe source.
`Capture` reads one immutable published revision with its actual assessment
time; it never probes or repairs providers. Reassess only through the inherited
explicit lifecycle operation. Readiness loss does not itself remove routes or
close admission; shutdown always overrides old readiness. Stop/start a fresh
lifecycle to change fixed selection. Discovery cancellation owns only its
request buffers, not provider resources.

Map `app.MapHoardDiscovery(lease)` before `MapHoardModulesAsync`. Both GET-only
data/description routes require the same management-read policy and verified
exposure posture; no anonymous static document is served. Direct-local mode
requires verified loopback, a direct/no-proxy assertion and no forwarding.
Secured-network mode requires authenticated read permission and HTTPS or the
explicit trusted immediate-proxy/TLS topology. Production verification supports
Kestrel with explicit `UseUrls(...).PreferHostingUrls(true)`, not arbitrary
`Listen` overrides/unknown servers. Configure usable authentication defaults
or explicit existing schemes on the read policy. Host authentication, proxy
isolation and request logging remain deployment responsibilities: discovery-owned
diagnostics are sanitized, not a guarantee that framework logs redact queries.

The [quickstart](../specs/004-module-discovery/quickstart.md) covers public
wiring, bounds, refresh rules and fixture-only acceptance. A usable operation
still needs its own execution policy; management-read grants none. Reference
consumer decisions do not certify production protocols/providers, F-07
conformance, external proxies, authentication or rendered accessibility.

## Opt-in metadata operations and fixture qualification

F-05 adds `Hoard.Abstractions.Metadata`, not members on `IMetadataProvider`.
`IMetadataStore`, `IMetadataSchemaAdministration` and
`IMetadataPublicationAuthority` are separate BCL-only contracts. Existing
marker-only registrations still compile and their frozen pre-F-05 binary
executes unchanged against the new platform. Core remains provider-free.

The independently packed [SQLite](../tests/fixtures/metadata/Sqlite/) and
[memory](../tests/fixtures/metadata/Memory/) implementations are **test fixtures**,
not production providers. They share public validation, synthetic inputs and
assertions, never transaction, reference, lease or recovery algorithms. SQLite
privately owns its SQL, native driver, file lock, worker, WAL schema and backup;
memory owns immutable committed roots and non-durable logical images.

Use the compiled [fixture host adapter](../tests/fixtures/metadata/HostAdapters/MetadataFixtureModule.cs)
and [configured integration test](../tests/contracts/Hoard.Metadata.Tests/Cases/MetadataHostIntegrationTests.cs)
as the executable composition example. Existing F-02/F-03 selects one metadata
authority. Module registration/construction opens nothing; initialization explicitly
inspects/creates/adopts the configured store, fails readiness on error and maps
no routes. Disabled modules create no file or worker. Secrets, admission policy
and publication authority are host-owned, not caller-substituted or re-resolved
by persistence. The fixture introduces no discovery support claim.

Reserve an operation ticket before mutation. Retry identical content with that
same ticket only while valid; reconcile uncertain acknowledgment rather than
inventing a new ticket. Reconciliation either returns the original receipt or
abandons/fences the reservation. Expired/foreign/pruned tickets cannot execute.
Atomic batches use revision conditions and final graph validation; read groups
have one committed snapshot, while keyset pages are not historical snapshots.
Keep caller canonicalization/auth partitions exact; providers do not normalize
identities or make authorization decisions.

Publication guards come from the one injected shared authority, are acquired
outside writer exclusion and remain owned through actual settlement. Artifact
length/reference changes commit with the entry and receipt. Zero-reference
confirmation is metadata evidence only: byte verification, active readers,
cross-store sequencing, orphan handling and physical deletion remain shared
cache/storage responsibilities. Leases use owner/generation/expiry fencing and
a monotonic effective time floor, not a distributed lock.

Operations have one overall budget (default five seconds, 1 ms..30 seconds);
administration defaults to 30 seconds with a two-minute maximum. A caller
deadline does not preempt native I/O. Late work blocks admission and retains
connection/lock/guards; cleanup exceeding 30 seconds reports explicit incomplete
ownership, never successful disposal. Trusted stuck native code may require
operator-controlled process termination.

Run `bash scripts/validate-metadata.sh`; see the
[quickstart](../specs/005-metadata-persistence/quickstart.md) and
[recovery procedure](../specs/005-metadata-persistence/contracts/recovery.md).
All 39 L cases apply independently to both packages. SQLite additionally has
nine D cases; memory reports `NotApplicable: non-durable fixture`. These results
do not qualify PostgreSQL/NoSQL, other filesystems, multi-node operation,
power/device-loss protection, F-07 certification or production cache support.

## Compatibility and release obligations

The [normative policy and all 23 examples](../specs/001-provider-contracts/contracts/compatibility.md)
distinguish **module**, **host**, and **abstractions** release versions.
Dependencies constrain the target module's version. Platform ranges separately
constrain host and abstractions, not an arbitrary custom executable's version.

Only exact `[1.2.3]` and bounded intervals such as `[1.2.0,2.0.0)` are accepted
by the written policy. Bounds are explicit three-part versions; inclusive and
exclusive bounds are supported. Missing, empty/reversed, unbounded, bare-minimum,
and floating ranges are unsupported. Build metadata does not affect precedence;
prerelease labels compare case-insensitively. Prereleases precede their stable
release and require a separate explicit opt-in for each host, abstractions,
or dependency axis. A `-rc` bound or prerelease module version does not opt in.
Restore success and registration alone prove none of these compatibility claims.

A required target must be enabled and compatible. An absent, installed-disabled,
or registered-disabled optional target is unavailable: no integration/capability
claim or active dependency edge. An enabled optional target must meet its range
and prerelease flag, even if the integration is allegedly unused. Incompatibility
makes the composition unsupported. Never silently disable a module/integration,
ignore a dependency, fall back, or substitute another provider. Operators must
explicitly change selection or install a compatible version and revalidate.
F-01 classifies examples; F-02's explicit validator now enforces these rules.
F-03 resolves configuration into that same gate, without duplicating it.

## Opt-in lifecycle

Add `AddModuleLifecycle<TProvider, TModule>()` after the provider registration.
It records types only. `IHoardModule` in `Hoard.Hosting.Lifecycle` explicitly
implements ConfigureServices, MapEndpoints, InitializeAsync,
CheckReadinessAsync, RunAsync and StopAsync. Constructors are parameterless and
inert. Metadata/artifact packages remain Abstractions-only; their adapters live
in the host. Protocol/identity packages may use approved Hosting APIs.

Supply `HoardStartupSelection`, `HoardPlatformVersions` and
`HoardLifecycleOptions` to `ValidateComposition`. No IDs/defaults are inferred:
exactly one enabled Metadata and Artifact must equal their authoritative IDs;
zero or more protocols/identity schemes are permitted. Registry structure is
checked even for disabled declarations; active compatibility applies only to
selected entries. Validation runs no constructors, factories, callbacks or I/O.
Malformed records, unavailable required targets, incompatible enabled optional
targets, cycles and unsatisfied target-specific capabilities fail explicitly.

Acquire `ComposeHoardModulesAsync` with `await using`, call
`BuildHoardApplicationAsync`, then `MapHoardModulesAsync`, then normal
`app.StartAsync` / `app.StopHoardApplicationAsync(lease)`. Do not independently
call bare app StopAsync, dispose the app or use app.RunAsync. One external lease
shares the actual framework-stop task and owns root disposal; a canceled
ApplicationStopped token does not prove its callbacks finished.
`IHoardLifecycle.StopAsync` shares module cleanup only; its root outcome is
`NotAttemptedOwnerPending` until external-owner disposal when safe. Inspect
`lease.StopResult` after disposal; incomplete disposal throws a sanitized
`HoardLifecycleException` and preserves that result. Repeated disposal shares
one operation, not a second cleanup attempt.

ConfigureServices/MapEndpoints are bounded composition, not worker/I/O hooks.
Do not build nested containers or register independent `IHostedService`s.
Adapters own phase-acquired resources, including partial failures; throwing
constructors clean their own pre-return allocations. DI retains its own
resource ownership. RunAsync is one admitted callback after complete selected
readiness, not a per-iteration scheduler; no-worker completion is valid.
Worker faults atomically close admission and request shutdown, without retry.
Host lifetime resolution and synchronous stopping notifications run outside the
lifecycle state lock. They are tracked before stop begins as global Phase
activity: a pending notification or lifetime-cancellation callback protects all
module resources and the root while snapshot/stop coordination remains bounded.

Map declared responsibilities through
`routes.Map(responsibilityId, pattern, methods, RequestDelegate)`.
Only absolute literals and required unconstrained whole-segment parameters,
explicit uppercase standard methods (HEAD explicit), and default order are
supported. All declared responsibilities need mappings. Equal framework
precedence with intersecting paths/methods fails, including same-owner,
renamed-parameter, case and trailing-slash equivalents. Disjoint methods/paths
and a unique more-specific literal pass. Constraints, defaults, optional/
complex/catch-all paths, dynamic/custom matching and unowned ambiguity fail.
Host middleware and access policy remain outside and apply normally; no
management/health endpoint or anonymous policy is added. Finalized routes must
not be changed while the lifecycle runs.

Readiness is neither liveness nor startup admission. All enabled modules must
initialize and explicitly report ready, including required health observations,
before workers/owned requests are admitted. Disabled modules have no callbacks,
routes or synthetic connection attempts. Later assessment can report health
loss/recovery for the fixed selection without automatically closing admission,
draining, replacing or disabling modules. Caller cancellation only cancels an
individual shared-operation wait; compose/build/map cancellation latches failed
startup. Stop permanently closes admission before cancellation/drain/cleanup.

Defaults are 120s absolute startup, 30s activation callback, 5s aggregate
readiness, and 30s total shutdown including at most 10s drain and 5s per module
cleanup. All durations must be positive/finite; inner waits never expand the
remaining outer budget, including synchronous callbacks/build and inter-phase
pauses. `TimeProvider` supplies monotonic deadlines.

Cleanup is reverse dependency order, once per returned adapter. Failed,
TimedOut, NotAttemptedBudgetExhausted and UnsafePendingCallback remain distinct
from Completed/NotEntered. Root outcomes additionally distinguish framework/
owner pending, unsafe omission, budget exhaustion, failure and timeout.
Outstanding requests retain ownership through response completion (including
handled errors). Supervised build installs the internal completion boundary
before host startup filters/middleware. Admitted leases release only after
their response-completion callbacks and handler callbacks finish, in reverse
registration order, not on handler return. Host middleware/access policy still
applies; no caller-installed admission middleware is needed.
Workers, build, activation, cleanup and cancellation callbacks
retain resources they may still use. A timed-out StopAsync does not release its
owner/prerequisites/root. Independent safe cleanup may continue under the same
deadline. Late completion cannot rewrite returned outcomes, retry or trigger
deferred disposal. Trusted non-cooperative code may require process termination.

Diagnostics expose fixed rule/action codes, safe IDs or registration ordinals,
phase, correlation and primary/cleanup classification, not provider exception
text, inner exceptions, options or URLs. Messages/actions are at most 512
characters; paths at most 32 IDs; diagnostic lists at most 100 with explicit
omitted counts. IDs are bounded to 128 characters, versions/publishers/option
keys to 256, ranges to 512, descriptions/URLs to 2048, and each nested descriptor
collection to 1000. These are structural limits, not production scalability
claims. Snapshots report IncludedByRegistration, fixed selection, phase and
readiness, never exhaustive installed inventory or certified capabilities.

Lifetime and readiness/cleanup-timeout cancellation faults use the safe
`CancellationFailure` code, originating owner/phase, fixed corrective action
and lifecycle correlation, classified as additional cleanup diagnostics.
They preserve the primary failure and are recorded before cancellation activity
is released. Correct the trusted module's cancellation callback before starting
a fresh lifecycle. Completed faults are not still-running activity: successful
resource release and a cancellation diagnostic can coexist. A fault after a
bounded result appears in a later snapshot only; it cannot rewrite that result,
retry cleanup or trigger deferred disposal.

Supervised startup, readiness, cleanup, framework-stop and root-disposal faults
are recorded once with their originating owner/phase before tracked activity
is released. A fault after its bounded wait is abandoned reports additional
`LateCallbackFailure`, even before shared stop completes; directly awaited
faults keep their normal category without duplication. Worker faults during
shutdown are also additional diagnostics, not a second shutdown request.
Cooperative cancellation is not a new eventual fault. Late reporting never
revises returned resource outcomes or starts deferred disposal. The lease
rechecks the original deadline after framework stop; if exhausted, root
disposal remains NotAttemptedBudgetExhausted rather than being dispatched.

Changing a bundled choice needs a fresh validated lifecycle, not a rebuild.
Adding an absent package needs reference, registration/adapter, rebuild,
redeploy and restart. Invalid replacement never rolls back silently; explicitly
restore the prior coherent set and start a new instance. Stop is not schema/data
rollback, crash recovery or forced termination.

Assess source compatibility for **consumers and implementers**, binary
compatibility for previously compiled supported modules, and behavioral
compatibility for documented obligations. Required member additions, removals,
signature/identity changes, and stronger publication/auth guarantees are breaking
even when a revised consumer compiles. Stable breaking contracts require a
major transition; pre-1.0 breaks require an explicit minor transition, e.g.
`0.1` to `0.2`, and updated narrow ranges. Patch releases remain nonbreaking;
never infer blanket `0.x` interoperability.

Before a breaking release, document affected members/behaviors, consumer and
implementer source impact, old-binary impact, old/new compatibility ranges,
provider/host code/configuration changes and rebuilds, qualification evidence,
and rollback/backup instructions. Publish migration guidance with that release.
Retain a coherent previous host/contract/provider set for rollback; do not
relabel incompatible binaries as supported. Local compile tests do not authorize
package publication or replace later behavior/conformance qualification.

## F-03 configuration boundary

`Hoard.Hosting.Configuration` adds an opt-in pre-activation boundary. Existing provider
interfaces/descriptors, Abstractions/Core/Application and lifecycle signatures
are unchanged. Metadata/artifact providers keep their Abstractions-only edge;
the composing host owns the new option descriptions.

`AddModuleConfiguration<TProvider>(HoardModuleConfiguration, HoardOptionValidator?)`
records an inert association. Fields must bijectively match descriptor keys and
required/secret flags; duplicate/orphan/colliding associations fail inspection.
Types are String, Boolean, Integer, Address and Secret, with version 1 metadata.
Informative defaults/examples are not injected into effective settings; secret
defaults/examples are forbidden. Registration/inspection invokes no provider,
adapter or validator. During evaluation, the existing F-02 composition gate
owns graph/cardinality/version/capability decisions. All active ordinary rules
and Public callbacks finish before any secret resolution. Secrets callbacks
receive only their owner's resolved handles. Disabled modules receive neither
callback nor secret read. Validators return declared field/rule identities,
not arbitrary messages; exceptions and malformed results become safe failures.
Composition failures retain a closed CompositionRule, known registered owner,
effective selection-source provenance and a bounded DependencyPath. Unknown
IDs/path elements become generated categories, even if their syntax is valid;
raw versions/capability targets and collaborator messages are never forwarded.
Active option-rule rejections retain `CheckFailure` plus a separately validated
`OptionRule` from that owner's declared rule IDs, canonical field and its
winning source. CorrectiveAction is host-owned text, never a provider message.
Malformed/undeclared field or rule results become `InvalidCheckResult` without
reflecting the supplied identity. Unsupported active option versions identify
`modules:<owner>:optionsversion` and its effective source. Secret resolution,
timeout, cancellation notification and late faults retain the originating
registered owner/field/source; locators and secret values remain private.
Returned reports stay frozen; eventual faults appear only in live Supervision.

`HoardConfigurationInput` takes explicit Defaults, optional file, arguments and
an environment dictionary/read adapter. Inputs and owner options have redacted
display and no public value-bearing serialization; explicit secret-handle access
is not process isolation or guaranteed managed-memory zeroization. The input
does not capture ambient process credentials. See the
[development guide](DEVELOPMENT.md#f-03-configuration-implementation) for
snapshot ceilings, source grammar, finite coordination and pending retention.

`EvaluateConfigurationAsync(input, platformVersions, lifecycleOptions,
configurationOptions, cancellationToken)` returns a safe report and, only on
complete success, an unconstructible `HoardValidatedConfiguration`. Consume it
once with `builder.ComposeHoardModulesAsync(proof, token)`, then use the existing
build/map/start/stop/lease-disposal sequence. `await using` the evaluation
disposes an unused proof; after transfer, only the F-02 lease owns the inputs.
Foreign/stale/disposed/used proofs fail before construction. Do not mutate a DI
service collection concurrently with composition; trusted host code is not
sandboxed. Fresh restart uses a fresh builder, evaluation and lifecycle.

A configurable selected adapter implements `IHoardConfiguredModule` in addition
to `IHoardModule`. `ConfigureOptions(HoardModuleOptions options)` runs immediately
before ConfigureServices under the same supervised F-02 phase/deadline. It
stores/maps only its own typed ordinary values and explicitly accessed secret
handles; it must not connect, start workers, log/serialize credentials or
retain a host-wide resolver. Use GetString/GetBoolean/GetInteger/GetSecret, with
`GetSecret(key).Reveal()` only at intentional sensitive-use boundaries.
Required/secret flags must match the descriptor. Zero-field legacy adapters
need no new interface. Enabled opt-in registrations reject bare legacy compose
as ConfigurationRequired; opt-out F-02 source/binaries remain supported.

Environment names use OS lookup semantics with no fallback; omitted supplied
environment is empty. File targets are absolute, bounded strict UTF-8 without
BOM/NUL; at most one final LF and preceding CR are removed. Empty/whitespace,
unavailable or oversized values reject. Deployment symlinks to regular files
work; zero-length directory/device/pipe inputs fail before reading, and all
dispatched reads remain bounded. Values are frozen until explicit restart.
Release clears owned secret references after the last actual supervised user,
not merely after a timed wait. This is not managed-memory zeroization or a
malicious-provider/enumerator/clock sandbox.

### Explicit synthetic conversion

Import `Hoard.Hosting.Configuration.Conversion`. Call
`PreviewConfigurationConversionAsync(sourcePath, destinationPath,
platformVersions, lifecycleOptions, configurationOptions, readEnvironment,
readSecretFile, cancellationToken)` on the registered builder. Only the exact
documented synthetic `fixture-v0` mapping is supported; startup still accepts
integer version 1 only. Preview reads the explicit document, checks shared
structure/composition/public semantics and returns safe change categories plus
a private session, with no secret read or activation proof.

Inspect its report, call `preview.Session.Approve()` deliberately, then
`builder.ApplyConfigurationConversionAsync(session, token)`. Apply consumes
approval once, checks unchanged source/builder/destination context, repeats
full option/secret checks and writes the reference-bearing proposal to a fresh
file, never the original. An explicit environment reader supplies secret
lookups only; conversion never applies HOARD_CONFIG, CLI or remembered overlays.
An apply result is not startup approval: start from a fresh complete evaluation.

Output directories must already be owner-restricted. Same-directory staging is
exclusively created at mode 0600, written/flushed/closed before no-clobber
publication. Existing/racing destinations and source aliases are not overwritten.
Cancelled waits after dispatch can return PublicationPending; inspect the
separate live Publication.Status and Supervision without rewriting the frozen
result or assuming rollback. If a process is interrupted, inspect the original,
any complete final output and only its identified private
`.hoard-configuration-<id>.tmp` files; remove staging only after actual work ends.
Do not use broad directory cleanup or recover resolved-secret rollback files.

Actual child-process interruption tests cover the current macOS local volume.
Linux publication code is present but unmeasured here; network filesystems,
hostile same-user directory races and power-loss durability are not certified.
Provider schema/data compatibility, backups, restore and irreversible changes
remain provider-owned prerequisites. Restoring configuration never reverses
provider data. No released older version, YAML converter or automatic migration
is claimed.
Conversion also rejects explicitly unsupported option versions on disabled
providers, without invoking their callbacks/readers; ordinary startup retains
its intentional disabled-version exemption.

## Later-feature handoffs

| Feature | Reserved work |
| --- | --- |
| F-02 | Implemented bounded, fixture-only module composition/lifecycle; no operational provider |
| F-03 | Implemented fixture-backed configuration, owner secrets and synthetic conversion feeding the existing validator |
| F-04 | Sanitized management capability discovery |
| F-05 | Implemented additive metadata operations and independent fixture qualification; production persistence remains separate |
| F-06 | Artifact streaming, staging, commit visibility, read/delete guarantees |
| F-07 | Reusable operational provider conformance and support qualification |
| F-08 | Identity normalization, scheme composition, central permission mapping |

Architecture checks inspect actual source/package graphs, signatures, and IL
using explicit ownership; they neither execute providers nor certify their
behavior. Unused framework references still count as dependencies; being a BCL
type does not make query/connection/transaction objects valid shared contracts.
All eight named platform/provider/host scans are required, not just a nonempty
scan manifest. Identity providers may reference the approved Hosting API,
including its transitive Core dependency. That does not permit a direct
Identity-to-Core reference or an unrelated SDK-mediated path; the scanner
tracks those paths separately even when both reach the same assembly.
Native-client restore, crash recovery, transport-level HTTP drain,
performance, operational provider conformance and production deployment remain
separate acceptance work. F-02 tests only application-level TestServer behavior.
