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
Metadata's `OpenLegacyAsync` invokes the binding's explicit
`CreateLegacySessionAsync` entry point through the same declaration/ownership/
lazy-getter gate; it never interprets case IDs to choose setup. Both factory
entries create fresh root sessions (`FactoryOperation: create`), while reopen
retains its distinct parent lineage. Memory's concrete factories now implement
this explicit setup; remaining factories and complete qualification are planned.
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

The Memory binding package now supplies current/legacy factories, the same
controlled clock/authority across logical reopen, all required typed controls
and genuine settlement-ledger integration. Reopen atomically closes old
admission before capturing the immutable image, settles the old session and
allocates a new owned resource. Independent committed reads use an explicit
fixture-only path that remains tracked by the same actual-work promise while
bypassing held read observers/late public-call admission; public operation
behavior is unchanged.

Generic controls expose actual named boundaries: independent reads at
`read.item`, writer ownership through the actual semaphore, acknowledgment at
`M1`, schema inspection, and lease/non-cooperation/cleanup at `M0`. Memory
non-cooperation is a held managed callback, not a native database/crash claim.
Capacity injects an actual one-shot write failure and observes its consumption;
persisted corruption observes actual typed raw payload changes. Those two
observations are non-holding; neither substitutes for the typed mutation or
common public-read/fingerprint/receipt checks. Ordinary holds are bounded at
15 seconds; the dedicated cleanup hold is 60 seconds so the real 30-second
provider cleanup deadline can be observed.

The package-mode diagnostic now explicitly references the Memory binding and
derives/reverifies five local package identities/locks. Its shared consumer
source is also in the existing package-only Consumer project. Nineteen focused
adapter rows use a clearly labeled allocator double; a twentieth uses the actual
SDK allocator, proving retained work, rejected premature allocator disposal,
stable-task retry, preserved failure history and no physical release claim.
All 95 selected Memory/adapter tests pass locally against actual packed
SDK/provider/binding packages; native run `40061416909` verified the expanded
37-scope/170-observation diagnostic and all 131 foundation checks.
These remain extraction diagnostics, not T023 completion,
full origin/controller integration or category qualification.

SQLite's fixture-only asynchronous independent read/writer controls retain
underlying work through the genuine worker lifetime, including cancellation and
late acquisition/cleanup. Ordinary idle includes reads, not held writer leases.
Shutdown closes admission, requests writer release, waits for independent work
and closes primary native handles. Escaped diagnostic/cleanup failure faults
that lifetime. Synchronous legacy controls remain caller-owned.

The initial SQLite binding now uses those controls. Reopen closes and joins the
old store before handing the same directory/database to a fresh compatible
session; it neither copies database files nor settles the directory under an
old task before reuse. Only final-head disposal binds the root to its genuine
worker lifetime. Canceled handoff retains the original owner and pending worker.
Upgrade authorization uses actual verified fixture backup files under that
owned root. Typed damage preserves native state/fingerprint storage classes,
opaque continuation fields and exact raw restoration. Raw-state observation
uses a read-only transaction without admission/repair; native value/progress
guards and bounded size preflight precede full-row hashing. Only bounded
32-byte row digests are sorted in managed code, never native full payloads.

A logical publication authority helper is compiled into both independent
binding assemblies; provider transactions/encodings/native mechanisms remain
private and no SDK dependency changes. The package-mode graph now explicitly
prepares/derives/reverifies seven local archives. Its selected 179 tests pass
locally (95 Memory/84 SQLite) with separate empty-cache locked build replay.
All 53 current shared logical assertion methods execute through SQLite; these
179 unit identities are not the catalog's 179 applicable category results.
Native run `40066075996` at `e6c4256` passed all three jobs, 134 foundation checks
without failures/errors/skips and 50 scopes/254 exact observations, including
all 84 SQLite identities. SQLite dispatch requires actual environment/native-runtime inputs. The producer
observes actual configured PRAGMAs/native version and the loaded module, validates
the library against the exact pinned NuGet archive, and fingerprints native
runtime assets before/after execution. A compiled SQLite archive is not execution
evidence; `nativeSqlite: not-used` cannot label an executing SQLite scope.
Complete adapters/category/provenance acceptance remains unfinished.
Fresh locked-restore metadata binds NuGet's normalized signed content hash to
the pinned lock, while the cache's archive SHA-512 and exact native member bytes
are independently checked. Pre/post native provenance must match. Runtime child
temporary files are contained beneath private owned caches. The environment-only
entry point is excluded from the general consumer's default compile items.
The isolated diagnostic runs native non-cooperation only in an isolated owned child.
It observes publication guard counts at the native boundary, caller deadline and
failed cleanup, uncertain outcome/original ticket, disposed admission, genuine
pending settlement and the allocator's retained history. A separate parent-written
recovery receipt binds the exact child PID/start, monotonic interval, diagnostic,
signal exit and observed group exit. Only that complete matching pair can admit
the intentionally contained diagnostic; normal exit, missing proof, setup failure
or an arbitrary timeout cannot pass. The fixed child watchdog is 45 seconds,
inside the five-minute recovery ceiling; cleanup remains 30 seconds and exact
owned termination 10 seconds. Native run `40067365972` at `7530cad` verified
the actual producer/controller pair; full inherited recovery remains unfinished.

The original MP-01..06/13 wrappers delegate to the same packaged SDK methods,
preserving their exact names and original fixture setup/disposal. The bridge
adapts only the existing authority interface, not provider behavior or expected
results. Predecessor preparation includes the SDK as its eighth archive and
checks the unchanged SDK output DLL alongside the test and consumer assemblies
after each composition. Exact safe runtime-origin ingestion remains T025 work.
Ten additional delegates reuse the existing SDK paging/concurrency/publication/
reference methods, preserving the original method names and the six malformed
continuation theory rows. Control-dependent methods have not been replaced by
synthetic successes or dropped during this partial adoption.
Five additional atomicity/publication wrappers now use the SDK's observation
delegate through the original fixture. Scoped registration rejects duplicates,
removes only its own callback and does not cancel or settle an invocation already
underway. The independent-snapshot overload preserves the old signature and
propagates cancellation to managed reads. Schema-hook names remain fixture-
private; this partial bridge does not prove unchanged schema-exclusion/barrier
parity or replace the original SQLite U1 exclusion witness.

The subsequent additive `SchemaCandidatePrepared` observation preserves that
U1 witness: SQLite holds its native write transaction after creating the
candidate schema; Memory observes its actual upgrade decision. The existing
`BeforeSchemaUpgrade` mapping remains SQLite U0 before transaction acquisition.
Both the common exclusion consumer and original MP-35 use the candidate hook.
A provider-specific real-connection regression requires SQLite BUSY (5) at
that boundary; it failed when observing U0. Final package checks pass 180
binding/SDK tests and 11 original schema/observer tests per provider.
The expanded Linux request is 50 scopes/255 observations (85 SQLite identities),
verified by native run `40070802352` at `3bca09c`; it does not establish full
recovery/parity acceptance.

The original MP-08 malformed-continuation theory now retains all six exact
rows while delegating to the same shared SDK consumer. Fixture-private
component mapping calls the existing independent encoding damage helpers.
An actual-cursor parity guard proves every original field is omitted by some
typed component and no unrelated values change, including Memory's combined
epoch/schema representation. Cancellation and unknown controls reject without
modifying a valid continuation. All 79 current predecessor tests pass on both
providers, with identical SDK/suite bytes; exact runtime-origin import and full
extraction remain unfinished.
Six further admission/capacity/lease wrappers share the same SDK consumers,
bringing original adoption to 29 methods. Fresh unadmitted stores and existing
fixture controls/disposal remain intact. The counter bridge reads real boundary
activity and diagnostic occurrences. All 16 affected class tests pass against
both providers with identical suite/dependency bytes and unchanged packages.
Three further clock-dependent wrappers use additive callback overloads
(32 original delegated methods). Existing SDK clock-object signatures forward
to the same assertion bodies. The callback changes the actual original clock
supplied to the store, never a detached substitute. A new actual-store proof
checks original-clock rollback with monotonic ticket issuance; all 80
predecessor tests pass on each provider and 180 SDK/binding tests pass.
The native U1 checkpoint predates these clock changes and does not execute
the original wrapper suite.
Eleven more deadline/reconciliation/replay wrappers forward original writer,
idle-settlement and scoped observation controls (43 delegated methods). The old
writer signature remains; its additive cancellation-aware overload and
registration-owned async lease cannot release a different holder. All 81
predecessor tests pass on both providers, including actual 30-second incomplete
cleanup and cancellation/queue/disposal ownership. This does not establish
full corruption/schema extraction or exact controller-origin import.
Four additional corruption wrappers delegate through the original fixture's
typed scope bridge (47 original methods). Scopes own one target, reject
overlap and atomically exclude registration after close/reopen admission.
An apply/cancellation failure restores only an actually applied mutation;
genuine idle settlement precedes that decision and restored-byte verification.
Failed settlement/restoration retains ownership for explicit recovery. Native
raw observations use independent bounded read-only connections, including from
inside a held primary candidate. Initial captured images are checked under the
writer before replacement; stale images reject without restoring over a newer
commit. All 87 current predecessor tests pass on each provider; 181 selected
SDK/binding tests pass locally. Native run `40097647586` at `84e8a4b` verified
50 scopes/256 observations (86 SQLite identities), actual native containment
and identical eighteen-package/thirteen-lock replay.
The original diagnostics wrapper also shares consumers (48 methods).
An additive overload uses a caller-installed failure hook and the original
canary/sanitizer; the existing scoped-hook signature forwards to that same
assertion core. Original connection-shaped error injection remains intact.
A real-store ownership regression proves shared assertions neither replace
nor dispose that caller's registration. All 88 current predecessor tests pass
on both providers, alongside 181 local SDK/binding tests. The native checkpoint
predates this increment and does not execute original wrappers. Schema/session
extraction and exact controller-origin imports remain unfinished.

All five original schema wrappers now also share these consumers (53 delegated
methods). The additive `IMetadataSchemaAssertionSession` is a narrow assertion
projection, not complete category-binding admission; existing full-session
signatures forward to the same core. Original fixtures supply real schema,
recovery authorization, same-database reopen and settlement. SQLite physical
database/WAL fingerprints run as genuinely worker-owned independent streamed
reads, retaining originally observed WALs and ignoring only newly empty WALs.
Cancellation before handoff retains directory ownership; in-flight physical
read cancellation maps to budget cancellation, not `InternalFailure`.
All 89 current original tests pass per provider and 183 selected SDK/binding
tests pass locally; fresh locked replay reproduces eight archives and exact
DLLs. Native run `40098981184` at `11875e5` verified the preceding diagnostics
checkpoint (50 scopes/256 observations), not original wrapper execution.
Schema run `40100325269` at `82a9b09` subsequently verified all 50 scopes/258
observations, 88 SQLite identities and native containment. Frozen parity and
exact runtime/controller imports remain open.

The diagnostic now adds two exact original-wrapper scopes: 63 frozen runtime
identities each for Memory and SQLite, selected independently from the immutable
F-06 inventory. It compiles the actual original test assembly against the
existing seven-package graph, verifies SDK/provider/Hosting/logger DLLs against
archives and captures its runtime/dependency/native files in immutable inputs.
The safe logger is installed as a verified adapter without adding a predecessor
NuGet dependency. Provider selection is closed and reaches both discovery and
execution test-host settings; console logging stays disabled. Discovery must
match every original parameter before execution; transport uses existing owned,
bounded pre-persistence projection and ingestion. Native run `40101331484` at
`8065dfc` verified all 52 scopes/384 exact discoveries and executions, including
63 original identities per provider, with actual native containment.
Binding/session-origin attribution,
legacy metadata acceptance import and category qualification remain separate,
unfinished gates.

The artifact SDK slice starts with five provider-free publication assertions:
absence/empty content, unknown length/true EOF, every expectation, unsupported
checksum/range and verified duplicate incarnation. Five original two-provider
wrappers preserve their frozen names and delegate; staging-boundary observation
stays original-owned. Existing wrapper publish/read helpers and nested short-read
type retain their signatures while sharing the SDK implementation.
The paired actual-store mutation replaces the second submitted source after two
genuine successful stages/commits; the common EOF assertion rejects it, while
the unmodified store passes. Eleven-archive fresh locked replay and 250 explicit
non-external-proof tests pass. Seventeen actual process/transfer-proof tests are
not satisfied by this selection. Full artifact sessions, historical/candidate
preparation, safe import and qualification remain separate unfinished gates.
The owned Linux diagnostic compiles the actual original artifact assembly and
selects twelve frozen publication parameters plus both source-substitution
pairs as one complete scope. Exact discovery precedes execution; shortened,
renamed or foreign scopes reject. Its existing ten-package graph is privately
rebound and every dependency/logger DLL is archive-verified, without a new
predecessor logger dependency. Artifact runtime/dependency/native bytes enter
immutable pre/post inputs. The thirteen-archive diagnostic feed leaves the
separate eighteen-package/thirteen-lock preparation graph unchanged.
The expanded 53-scope/398-observation native request is pending execution.
Three additional original read/deletion wrappers preserve destination failure,
borrowed stream ownership, exact receipts, recreation/ABA fencing and held-reader
exclusion through shared SDK consumers. Original reference-authority setup
stays in the fixture. A lexical reader scope releases exactly once before
awaiting deletion, including assertion failures. All six frozen parameters form
a separate exact diagnostic scope; shortened or renamed scopes reject.
Thirty-seven affected class tests and 250 non-external-proof artifact tests pass
with fresh eleven-archive replay. The expanded 54-scope/404-observation native
request is pending; full bindings/origins and external proofs remain separate.
Native [40103524667](https://github.com/Stonefly-Labs/Hoard/actions/runs/40103524667)
at `dcb777e5a24665e569f029c1d359060319bfefcf` verifies the earlier publication
transport: all three jobs, 143 foundation checks, 53 scopes/398 exact
discoveries/executions, actual original artifact publication/mutation, native
containment and eighteen-package/thirteen-lock replay.
Exact receipt/protection and permanent quarantine assertions now share SDK
consumers too. Local durable reopen stays fixture-owned; no simulation borrows
it. An actual-validator wrong-receipt mutation fails the common assertion on
both providers while original validators pass. Fresh replay passes 28 affected
tests and 252 non-external-proof artifact tests without skips. A new 23-identity
scope preserves original evidence/quarantine parameters and the mutation pair,
expanding the pending native request to 55 scopes/427 observations. This is
diagnostic evidence, not full category/binding/session-origin completion.
The owning controller now exposes opt-in bounded `stop_at_barrier` recovery
commands. Safe event observation precedes actual child identity verification and
owned pidfd group signaling; success requires accepted signal, actual SIGKILL
exit and complete observed group exit. Wrong/repeated/missing barriers, failure
events, timeout and ordinary exit reject. Parent receipts bind the requested
numeric target and monotonic observation/signal-request times to existing exact
PID/start/exit evidence. Existing command receipts remain unchanged when the
option is absent. Linux process regressions are pending; this primitive is not
execution of the inherited recovery matrices or category proof.
The actual SQLite CrashRunner now has opt-in safe events; unset retains exact
legacy output and invalid mode rejects before store creation. Completion events
follow original assertions; numeric hold events are flushed after the actual
boundary/control write. The SDK diagnostic independently builds/byte-verifies
all six runner dependencies and input-captures its complete runtime/native tree.
It requests ten mutation/upgrade/restore seed/barrier/readback rows plus the real
backup/restore walkthrough. Parent admission requires exact target/sequence,
PID/start, SIGKILL/group exit and bounded monotonic observe/signal order.
All final records are closed IDs/hashes bound to the current inputs, never raw
legacy logs or imported pass labels. Fresh locked local walkthroughs pass;
subsequent Linux verification is below. Live-held probes and full legacy/
category attribution remain pending.
Native [40105402168](https://github.com/Stonefly-Labs/Hoard/actions/runs/40105402168)
at `d7ef7cc3cdc20822c79b340a42e12eef0cbbe383` verifies the earlier exact
evidence/quarantine/mutation transport: all three jobs, 145 foundation checks,
55 scopes/427 observations, native containment and eighteen-package/thirteen-lock
replay, not the subsequent controller/recovery integration.
The corrected native process gate at `62c149c` passed 151 tests without
failures/errors/skips; complete SQLite execution also passed all ten seed/
barrier/kill/readback rows and the actual backup/restore walkthrough at
[40107305423](https://github.com/Stonefly-Labs/Hoard/actions/runs/40107305423).
All three jobs passed, including 55 scopes/427 exact observations and identical
eighteen-package/thirteen-lock replay. Local's
actual runner now has the same explicit safe-event mode, retaining legacy
output when unset and rejecting invalid mode before store creation. Its
unchanged nine-package graph and complete runtime bytes are independently
verified/captured. Six fresh run-bound crash/readback pairs use the same
parent-owned observation/signal/exit gate and original Local assertions,
not ObjectSemantics or metadata provider delegation. Two locked runner builds
and six macOS functional readbacks pass; actual Linux ownership/readback
subsequently passed all six rows at
[40107826472](https://github.com/Stonefly-Labs/Hoard/actions/runs/40107826472).
All three jobs passed, with 152 foundation checks and 55 scopes/427 observations.
Complete legacy/session/category proof remains pending.
The transfer diagnostic now requests both providers' actual paced non-seekable
256 MiB/4 GiB writes and reads. Parent handshakes bracket kernel `/proc` RSS/
high-water observation on the exact owned child; only those kernel values can
supply the inclusive 64 MiB incremental peak check. Exact producer bytes,
hashes, pacing, runtime, PID, run, buffer/slot limits and normal group settlement
are required. Full runtime bytes enter pre/post immutable capture. Two fresh
locked builds and all four real macOS rows pass, including actual `getrusage`
peak bounds. Actual Linux pidfd/status measurement subsequently passed all four
rows at `d429dd2`, run `40109299238`; complete session/category imports remain
pending.
For retained artifact work, explicit safe mode writes bounded closed original
observations before contained/inspected barriers. The owning parent requests
the second actual inspection, then observes its target and signals only that
owned group. Admission requires the exact ordered live-child request/signal/
exit chain, both matching phase/run/PID/provider/scenario records and unchanged
retention/protection/failure assertions. Six actual source/destination/native
rows are requested across both providers; every result explicitly disclaims
durable crash proof. Actual Linux execution passed all six rows at `c7eb90c`,
run `40110165383`, with 165 foundation checks and all three jobs successful.

An additional exact owned scope requests all seventeen original external-proof
artifact wrappers: sixteen frozen crash/noncooperation/transfer identities and
the existing independent cross-process root-owner fact. Four bounded child-text
capture cases make 21 selected identities. Actual runner bytes must match captured
inputs; private per-attempt settings supply its path, the current run ID, fresh
crash-capture storage and parent-admitted transfer proofs. Original legacy child
output is preserved; safe-event mode is not inherited into these wrappers.
Child stdout/stderr is bounded before returning; crash-state size is checked
before read/copy. Recovery error files are written only after the original
empty-stderr assertion, preserving healthy empty captures without persisting raw
failure diagnostics. Transfer proof admission also recognizes actual kernel
`getrusage`/`proc-status` methods while retaining all byte/hash/pacing/RSS/buffer
checks; an unmeasured `declared` method remains rejected.
Two fresh-cache locked builds pass all 21 actual cases, reproduce test assembly
bytes after normalizing source/cache debug paths and verify ten dependency
images. Linux run `40111391053` at `4e3ef47` passed all three jobs, 167 foundation
checks and 56 scopes/448 exact observations, including all 21 external/capture
identities and the actual recovery/transfer/retention prerequisites. Complete
legacy/session/category attribution remains open.
Current package preparation uses current metadata/SDK sources, independently
of sealed historical source/binary recipes. The artifact feed contains eleven
archives, including the SDK. Existing strict local-archive derivation now also
supports the exact package-acceptance lock path through a distinct private
alternate; ordinary and acceptance locks cannot be relabeled/substituted.
Only local archive content hashes can change. Original source locks, external
versions/hashes/edges and package bytes are verified; tracked locks are untouched
by default locked execution. Both metadata and artifact preparations retain
their verified non-qualifying derivation records.
Two fresh-cache locked preparations reproduce all eleven archives, verify ten
loaded dependency images and each execute all 273 original/current artifact
cases plus 89 metadata cases per provider without skips. Actual previously
measured transfer packets are unchanged when exercising their original proof
consumers; this is not fresh measurement/session-origin/category acceptance.
Three original publication race bodies now live in the shared publication
consumer: equivalent concurrent writers, forged staged length and preserving
corrupt evidence. Actual observer registration and payload damage/restore are
fixture-side callbacks; common code accepts no provider ID, concrete type,
filesystem path or provider-selected expected result. All six frozen parameter
identities are retained. Mechanical body comparison preserves every original
check and operation order after explicit store/helper/token/control forwarding.
A real-store adapter that repairs forged staged length demonstrably fails the
unchanged consumer's expected failure-type assertion on both providers; commit
and repaired-claim counters prove the mutation occurred. Fresh genuine stores
pass unchanged. The extra native scope requests those six frozen identities and
two named mutation parameters, expanding the pending vector to 57 scopes/456
observations, not complete session/category attribution.
Two actual fresh-cache locked builds reproduce eleven archives, verify ten
loaded artifact dependency images and each pass 275 artifact cases plus 89
metadata cases per provider without skips. Accepted SDK/package-mode whitespace
and all 277 tooling tests pass (260 passes/seventeen native macOS skips).

Private staging and the four original reconciliation methods now also execute
shared assertions, with ten unchanged frozen parameters. Fixture-owned controls
retain actual prefix entry/release, clock advancement/rollback, authority setup
and post-stage lost-acknowledgment registration. Common code preserves exact
original assertion tokens and ordering after explicit setup/seam/helper/token
forwarding. A real-store mutation reconciles the original ticket and substitutes
a genuine receipt from a different actual publication; the unchanged equality
assertion fails on each provider. One reconciliation and one foreign-publication
counter prove the intended mutation; fresh genuine stores pass unchanged.
The extra exact native scope has eight frozen reconciliation witnesses and two
mutation parameters, requesting 58 scopes/466 observations in total, pending.
These remain diagnostics rather than full binding/session/category attribution.

The three original direct/listing visibility methods now execute shared
consumers with exact original checks/order preserved mechanically. Fixture
callbacks retain actual observer registration and hold/release operations,
including direct-observer removal before release. A Local mutation starts the
actual held commit and immediately returns a genuine earlier receipt, failing
the unchanged pending-task assertion. The test releases the real hold, awaits
actual commit settlement and verifies its distinct published stamp; a fresh
genuine provider passes unchanged. Three frozen visibility facts plus this
mutation request the next 59-scope/470-observation vector, pending.
The preceding race-only vector passed run `40113497329` at `91da8f4`, all three
jobs and 169 foundations, with 57 scopes/456 exact observations and all actual
recovery/transfer/retention prerequisites. Neither vector is category acceptance.

Five original history/budget bodies now also execute shared checks, with exact
assertion tokens/order retained and actual clock, limit/authority setup and
candidate registration fixture-side. Eight identities are frozen category
witnesses; eight additional existing fixture identities are explicitly requested
without altering the frozen inventory. Real-store mutations hide the injected
candidate failure behind one actual retry, causing the unchanged expected
failure-type assertion to fail on both providers; actual observation/reservation/
failure/retry counters corroborate the intended fault. Genuine stores pass.
All sixteen originals plus the two mutation rows request the next
60-scope/488-observation native vector, pending. Remaining budget/ownership and
complete category/session/profile evidence are not supplied by this extraction.
The reconciliation-only request passed run `40114439905` at `517b911`, all three
jobs, 170 foundations and 58 scopes/466 observations, with all actual
recovery/transfer/retention/native prerequisites and eighteen-package/thirteen-
lock replay admitted independently.

Four original cooperative/noncooperative stream-ownership bodies now execute
shared consumers with eight frozen parameters and three unchanged actual
stream-helper bodies. Clock/settlement controls stay fixture-side; the legacy
pending-source name forwards to the shared helper. A real-store mutation first
requires actual cancelled source work with retained live ownership, then
misreports released cleanup. The unchanged equality assertion fails on each
provider, actual release/settlement completes, and genuine stores pass unchanged.
The next ten-row native scope requests 61 scopes/498 observations, pending,
without adding durable crash or kernel RSS claims. The preceding visibility
request passed `40115175363` at `793ad65`, all three jobs, 171 foundations and
59 scopes/470 observations, with all actual prerequisites and eighteen-package/
thirteen-lock replay admitted. Complete category/session/profile gates remain.

Three original cancellation/current-owner bodies now also execute shared
assertions with ten unchanged existing parameters: two frozen category witnesses
and eight explicitly requested additional fixture identities. Actual clock,
publication/progress observers, boundary removal/release and worker settlement
remain fixture-side. A real-store negative waits for the rejected commit's
actual settlement before abandoning the current verified owner, failing the
unchanged pending-state type assertion on each provider. One stage, one commit
and one actual abandonment corroborate the intended mutation; genuine stores
pass unchanged. Its initial setup guard correctly rejected abandonment before
physical settlement under whole-suite concurrency; actual settlement, not
logical return, now precedes the mutation. The next twelve-row scope requests
62 scopes/510 observations, pending. The history request passed `40116055015`
at `37ec19a`, all three jobs, 172 foundations and 60 scopes/488 observations,
with actual prerequisites and eighteen-package/thirteen-lock replay admitted.

Four original result-handoff/expiry bodies now also run shared consumers,
preserving all twelve frozen parameters and exact original assertions/order.
Actual completion/release observers, holds, entry, observer removal, boundary
release, clocks and worker settlement stay fixture-side at the original control
boundaries. Hiding a genuinely reserved ticket after cancellation fails the
unchanged success-type assertion on both providers. Publishing that same actual
ticket corroborates the intended ownership fault, while fresh genuine stores
pass unchanged. The next fourteen-row scope requests 63 scopes/524 observations,
pending, not complete category/session/profile acceptance.
Stream ownership passed `40116943400` at `5974f38`, all three jobs,
173 foundations and 61 scopes/498 observations, with actual prerequisite chains
and eighteen-package/thirteen-lock replay admitted; complete gates remain open.

The remaining six original budget bodies now also execute shared consumers,
preserving sixteen frozen parameters and exact assertion tokens/order: failed
unclaimed cleanup/retry, terminal cancelled publication, full transfer queue,
cap crossing, authority contention and cooperative cancellation. Actual
completion/reclaim/queue observers, barriers, real settlement/stop, limits and
authority creation stay fixture-side. Shared checks use only the Abstractions
authority interface and actual identity, never concrete host adapters. A genuine
input-limit failure mislabeled as capacity fails the unchanged expected-code
assertion on both providers; one actual staging call and one observed limit
failure corroborate it. Genuine stores pass unchanged. The next eighteen-row
native request is 64 scopes/542 observations, pending, not full qualification.
Six original authority bodies now also execute interface-only shared checks,
preserving three frozen category witnesses, three additional existing facts
and the exact copied-guard helper. Actual authority construction, clock,
waiting/retained counters, reference completion and drain remain fixture-side.
A real copied-handle denial repaired into actual recognized retention fails
the unchanged failure-type assertion. The retained guard is explicitly disposed;
genuine authority passes unchanged. The next seven-row native scope is
65 scopes/549 observations, pending. Cancellation passed `40118166329` at
`631f9c4`, all three jobs, 174 foundations, 62 scopes/510 observations and
all actual prerequisites/replay. Handoff-only `40118782562` was canceled while
pending, not admitted; later expanded requests retain its scope.
Both original capability bodies now also run shared interface-only consumers,
preserving sixteen frozen gap parameters, two additional existing complete
profiles and exact original assertion tokens/order. Actual capability injection,
provider construction, filesystem/readiness observation and private-root cleanup remain
fixture-side. Rejection-before-I/O, actual readiness, configured limits, optional
ranges, SHA-512 and stop/release checks remain unchanged. The next eighteen-row
native request is 66 scopes/567 observations, pending, not full qualification.
Expanded budget passed `40119412481` at `70dfdf6`, all three jobs,
176 foundations and 64 scopes/542 observations, including all fourteen handoff
and eighteen budget rows, actual prerequisite chains and replay. This admits
handoff at `70dfdf6`, not the canceled handoff-only run.
Four original metadata/artifact integration bodies now execute shared checks,
preserving sixteen frozen parameters on all four actual SQLite/Memory and
Local/ObjectSemantics combinations. Exact assertions/order, waiting/stream/
commit/evidence helpers and seed data match after explicit forwarding. Actual
composition, proof encoding, waiting counters, M1 hold/entry/release and both
stores' physical settlement stay fixture-side. A real reference-denial result
mislabeled as conflict fails the unchanged expected-code assertion in all four
combinations. One actual deletion/observed denial per negative corroborates it;
genuine stores pass unchanged. The twenty-row native request passed at
`4c87667`, run `40121897879`, all three jobs, 179 foundations and
67 scopes/587 observations, not full typed binding/category/session or
authority-integration task acceptance.
Authority passed `40120167356` at `7ee1c61`, all three jobs,
177 foundations and 65 scopes/549 observations, including all seven authority
rows, actual prerequisite chains and replay; complete gates remain open.
Three original metadata-bridge bodies now also execute interface-only shared
checks, preserving one frozen authority-mismatch witness and two additional
existing exact/invalid-evidence facts. Actual host bridge/controlled-validator
construction, encoding, expiry and observed counters stay fixture-side. The
validator's recognized-reference operation/stamp assertions call the unchanged
shared checks; remaining real retention/decision logic stays fixture-side.
The bridge-only native request was canceled while pending; its three rows are
included in the expanded lifecycle request, not separately accepted.
These host-bridge unit checks do not complete provider/category/session proof.
Capability passed `40120937967` at `2a7be14`, all three jobs,
178 foundations and 66 scopes/567 observations, all eighteen capability rows
and actual prerequisites/replay; complete gates remain open.
Three remaining original lifecycle bodies now use interface-only shared
consumers, preserving four frozen parameters and two existing composed-shutdown
cases. Actual reference-query setup/completion/drain, slow guard implementation,
native I/O holds, physical release/removal and settlement stay fixture-side.
Original assertions/order and the generic bounded-failure helper are unchanged
after explicit seams. The next six-row request is 69 scopes/596 observations,
pending, not complete provider/category/session or full profile qualification.
That lifecycle request passed `40123477371` at `f2cc84d`, all three jobs,
181 foundations and 69 scopes/596 observations, including three bridge and six
lifecycle rows plus actual prerequisites/replay. The canceled bridge-only run
is not separately accepted.
Two original storage-failure/reconciliation bodies now also use shared checks,
preserving four frozen parameters, fixed classifications/sanitizer/source
behavior and original assertion tokens/order. Actual post-visibility fault
registration stays fixture-side. Real access-denied staging failures relabeled
as unavailable fail the unchanged code assertion on both providers; actual
stage/observed denial counts corroborate each negative and genuine stores pass.
The next six-row request is 70 scopes/602 observations, pending, not complete
bindings/category/session or full profile qualification.

Four-way integration passed `40121897879` at `4c87667`, all three jobs,
179 foundations and 67 scopes/587 observations, all twenty integration rows and
actual prerequisite chains/replay. These are diagnostic counts, not complete
category results.
Three original prefix-cleanup bodies now also use interface-only common checks
with all six frozen parameters and unchanged stop/reopen assertions. Actual
permission changes, observer registration/removal, readiness/directory snapshots
and Local-only durable reopen stay fixture-side. Original exact receipt/owner/
cleanup/fencing checks remain common; no simulation durability is borrowed.
The next six-row native request is 71 scopes/608 observations, pending, not
complete bindings/category/session or full profile qualification.
Both remaining original object-cleanup bodies now also execute common checks
with five frozen parameters, preserving selected-object receipt/ownership/
reclamation assertions and exact original order. Actual Unix permissions,
observers, filesystem snapshots/lengths and worker settlement stay fixture-side.
Private hook names translate into the existing logical during/after-assembly
input; common checks own all fixed expected codes/sizes/owners/receipts. The
next five-row request is 72 scopes/613 observations, pending. Original failure-
body extraction does not complete T027/T030 or full binding/category/profile
gates.

Storage-failure passed `40124374635` at `ff50acd`, all three jobs,
182 foundations and 70 scopes/602 observations, including all six new rows and
every actual prerequisite chain/replay, not full qualification.
Configured publication, compatible reopen and fresh-epoch artifact operations
now also execute interface-only shared consumers, retaining fixed original
content, identity/epoch, exact ticket/receipt and protected-read assertions.
Actual hosting/DI/configuration/mapping, module cardinality/identity/readiness,
disabled roots, restart/stop and missing-guarantee inert-start rejection remain
fixture-side; no Hosting/Core dependency enters the SDK. The next four-row
native request preserves all frozen host cases at 73 scopes/617 observations,
pending, not complete bindings/category/session or composition-profile proof.

Owned-session preparation now includes an explicit authority closing fence that
joins recognized/retained guards, queued admissions and actual retained reference
queries before reopen. Its task is stable within a closing generation; reopening
creates a new task rather than borrowing a completed predecessor. Binding-only
compilation makes the same source-linked authority/reference-decision internal,
without importing HostAdapters, Hosting or the other provider. These are not
complete category bindings or substitute mandatory fault controls. Three common
checks request 74 scopes/620 observations, pending.

Object cleanup passed `40126135553` at `3de87aa`, all three jobs,
184 foundations and 72 scopes/613 observations, including all five new rows and
every actual prerequisite chain/replay, not full qualification.

Prefix cleanup passed `40125248164` at `871e3a8`, all three jobs,
183 foundations and 71 scopes/608 observations, including all six cleanup/stop/
reopen rows and every actual prerequisite chain/replay, not full qualification.

The initial executable SDK slice exposes fifty-three methods across
`MetadataBoundsAssertions`, `MetadataPagingAssertions`,
`MetadataConcurrencyAssertions`, `MetadataLeaseAssertions`,
`MetadataIdentityAssertions`, `MetadataEntityAssertions` and
`MetadataReferenceAssertions`, `MetadataTimeAssertions` and
`MetadataReconciliationAssertions`, `MetadataCorruptionAssertions` and
`MetadataAtomicityAssertions`, `MetadataPublicationAssertions` and
`MetadataDeadlineAssertions`, `MetadataAdmissionAssertions` and
`MetadataFailureAssertions` and `MetadataSchemaAssertions`.
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
Lease controls additionally cover generation overflow and exact expiry at the
final renew/release/guard decision. The deadline consumers preserve real writer
budget, cancellation before/after the commit decision, bounded pending readers,
disposal awaiting owned work and known post-decision exception classification.
A pre-canceled reservation is settled before the next operation: definite public
cancellation does not prove that dispatched work has ended. Cleanup releases
held work and joins public tasks and actual settlement without caller
cancellation; disposal still does not imply authoritative resource release.
The incomplete-cleanup case uses a separate 60-second hold to outlast the real
30-second provider cleanup limit; ordinary holds remain 15 seconds and entry
remains bounded to ten seconds. It observes the cleanup failure and closed
diagnostic count while actual settlement is pending, then releases and joins
every started public operation, disposal and settlement observation before
retrying disposal. It does not claim resource release from the failed cleanup.
Required `MetadataFaultCounters` retain only nonnegative counts of concrete
boundary observations and the two closed internal-failure/cleanup diagnostics.
Unknown diagnostics reject at the fixture boundary without retaining raw text.
Admission/budget consumers check no observed boundary work before admission or
for invalid budgets. Storage capacity preserves atomic same-ticket retry; live
ledger capacity cannot evict the original receipt. The diagnostic consumer
checks actual injected failure, closed diagnostic observation and public
diagnostic/debugger redaction. A dropped-diagnostic negative must fail that
unchanged common consumer before actual observation passes.
Five schema consumers take typed metadata sessions; the caller supplies fresh
unadmitted or legacy-compatible sessions as appropriate. They cover unrecognized/
partial layouts, authorized upgrade with entity preservation and receipt epoch
expiry, invalid authorization, concurrent exclusion and future/corrupt reopen.
The upgrade target comes from actual `MetadataSchemaInspection.TargetVersion`,
not a provider name or version-suffix rewrite. Required `ObserveStateAsync`
returns a private-mechanism-derived hash; the SDK checks unchanged state alongside
public rejection/admission/readback. Memory's fixture hash frames and orders raw
stored payloads and every logical state section without decoding or repair.
Concurrent upgrades release their barrier and join both started tasks plus
actual settlement on failure/cancellation. The focused schema session is an
explicitly non-admitted probe with unsupported generic controls; it is not the
complete Memory binding or origin-attributed qualification.
The continuation-corruption consumer owns six malformed shapes and all six
logical contract/epoch/schema/query/page-size/position components. The required
typed control mutates only an opaque token; private field names, JSON and base64
stay in the fixture. Memory schema identity is represented by its epoch, so those
two logical controls mutate the same physical field; every Memory cursor field
is still exercised. Each rejected token must preserve exact valid resume and
complete traversal. A no-op mutation fails the same compiled common consumer
that passes with real field damage; no binding-supplied shortened component list
or expected outcome is accepted.
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
