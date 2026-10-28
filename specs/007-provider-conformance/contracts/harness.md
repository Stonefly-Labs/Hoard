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

Artifact assertion sessions and full fault drivers expose
`InjectPublicationAcknowledgmentLossAsync`, an owned registration at actual
publication selection. Its exact injected exception is an expected fault;
arbitrary observer exceptions, including the same type/message, still poison
ownership settlement. Registration observations corroborate entry; common
reconciliation/read/receipt assertions independently establish the outcome.

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

Actual category transport is restricted to independently selected whole scopes
from the catalog: exact binding, identity and primary-case assignments must
match before launch. The category dispatcher requires the predeclared attempt
UUID and an already-written matching category input document. Raw runtime/
owner/witness/completion/proof bytes are returned unchanged; prior harness
evidence cannot be relabeled into a category. Discovery and runtime admission
share the existing bounded transport path.
Its inspection entry point additionally exposes structurally validated
observations under an immutable, explicitly `qualification: false` envelope
with captured inputs/digest. Normal admission shares that parser and still
requires its original qualification-origin policy. Inspection validates all
hash/provenance/timing/completion constraints, but never supplies missing
source/controller corroboration or a qualifying pass.
Metadata category controls additionally rerun SQLite native-stall containment
and all ten recovery barriers/walkthrough with fresh
`category-sqlite-native-noncooperation` and `category-sqlite-recovery`
stores/cache/proofs bound to metadata inputs. Harness defaults are unchanged;
old receipts cannot replace those fresh invocations. Successful seed/readback
events also require exact settled owned-command records. These diagnostic
controls do not yet satisfy the remaining category-control imports.
Native category failures identify scope execution versus joint admission with
closed catalog scope IDs/codes. Unexpected runtime results additionally retain
only observed code/exit, state/mismatch counts and up to four identity hashes;
raw test/failure text and private paths remain excluded. This diagnostic limit
never truncates the actual evidence or admits an incomplete inventory.
The CLI's final failure record also preserves that bounded unexpected-result
context for non-category runtime attempts; exit/status rules remain unchanged.
Fresh metadata-input controls and both complete batches are independently
admitted at exact `564c67f`, run 40193163127 (three jobs/272 foundations without
skips). They remain non-qualifying until control import is implemented.

The original native-boundary deadline fixture uses a private controlled clock
to expire its 100 ms deadline only after the synchronous fault seam is entered;
a 200 ms pre-entry ObjectSemantics observer covers delayed worker execution.
Its common entry/deadline/retained-ownership/20 ms stop assertions remain
unchanged, and actual settlement precedes blocking-event disposal. This
corrects fixture scheduling, not provider behavior or qualification policy.
The twelve related cases pass locally. Exact `0107db5`, run 40199986870, also
passes all three Linux jobs, 273 foundations without skips and the complete
121-scope/1,684-witness diagnostic chain, including this delayed-entry case and
fresh category controls. Failed run 40197707264 at `4e6f03b` identifies this
ObjectSemantics witness but is not admitted evidence. Source-parent changes
below are later than that receipt and still require their own native execution.

For category discovery and execution, an available native command record is
independently joined to the exact run/root/sequence, argv/cwd hashes, PID/start,
matching exit, successful supervisor diagnostics, nested monotonic timing and
actual settled group. Read-only bytes and unchanged prelaunch settings are
required. Create-new hash-only parents bind the record, settings and manifest
to current input/group/attempt/purpose. Native executors cannot omit the record;
explicit non-native diagnostic adapters emit no native receipt. These parents
prove invocation ownership, not assertion success or qualification.
Each category inspection/controller scope additionally joins its independently
validated source receipt to those exact execution-parent bytes, current
read-only command record, actual result record hash and unchanged settings.
Source observations preserve the frozen binding/primary-case/execution/runtime
proof mapping; exact schemas and kind-specific controller proof keys are
required. Native records cannot be omitted or replaced by non-native fixtures.
Create-new read-only source parents remain explicitly non-qualifying; safe
summaries retain only their count and canonical scope-to-parent digest.
This is source linkage, not admission of missing control obligations or a
qualification-origin bypass.
Native parents additionally require an executor-anchored receipt: the original
safe bytes retained only when that `OwnedRun` actually records a command.
Pinned reads reject unknown sequences, changed/writable/nonregular receipt files
and inactive/foreign ownership. Retention is bounded by the 50,000-proof cap.
Execution/source parents retain explicit command sequences so later admission
need not reinterpret the latest counter as an earlier scope's invocation.
These stricter native checks pass exact `d06f256`, run 40204781861: all three
Linux jobs, 273 foundations without skips and 121 scopes/1,684 witnesses.
They do not themselves admit source qualification.

Independent inspection-source admission additionally requires executor-held
pre/post input snapshots, not just argv/cwd hashes or current files. Category
commands name the actual read-only manifest, owner, RunInputs, assembly, settings,
inspection context and relevant prepared configurations. Pinned captures enforce
16-file/256-MiB/five-second bounds and reject identity/timestamp changes even when
bytes are restored; original native receipt retention has a 256-MiB byte cap.
The exact complete frozen scope and source/command/native graph must independently
match those consumed inputs. Safe source graphs and packet copies survive store
cleanup, and case attempts retain source-parent proof hashes. A separate fresh
qualification-input metadata replay is wired; default transport admission and
controller-origin qualification remain closed. This later increment has local
tooling coverage but awaits exact-head native execution. Overall histories remain
non-qualifying with their incomplete obligations; full profile CLI is unfinished.

Recorded native recovery/transfer invocations additionally anchor the exact
control receipt bytes in `controlRecordSha256`. Native recovery orchestration
rechecks that digest, argv/cwd/input map and returned execution hash, not just
PID/start/exit. Metadata seed/kill/readback/walkthrough commands declare both
their actual assembly and immutable current-input document for pre/post capture.
This is provenance preparation only: no controller qualification, passing
metadata control import or complete profile backend is inferred.

Qualification-input metadata attempts now independently corroborate a separate
31-command M/U/R seed/kill/readback/walkthrough graph inside their monotonic
boundaries. Native/controller sequences, exact consumed input hashes, argv/cwd,
owned exits and barriers must agree; complete safe graphs remain under `proofs/`
and enter atomic case proof references. The source summary exposes only the
independently imported `recoverySourcesSha256`. Control-only cases without an
actual RuntimeWitness UUID still remain incomplete; labels/hashes cannot supply
one. Existing diagnostic namespaces/output schemas and the Passed Attempt
requirement are unchanged. Exact native execution of this increment is pending.
A package-only metadata recovery source fact now has a bounded decoder for all
65 input/graph/summary/controller/native files. It emits only consumed-file
hashes after complete graph assertions; a packet is not a RuntimeWitness.
Category dispatch, independent native source joining and case attribution are
not yet wired. Missing context fails explicitly and unrelated valid sessions
remain rejected; no controller qualification is inferred from modeled tests.
The later qualification path now dispatches that fact in its own seventh scope.
Its immutable context and native input snapshots bind the complete consumed
graph; independent source corroboration joins the real runtime UUID/proof to
actual native execution and case controls. Diagnostic scope selection is
unchanged. Bare graphs or unparented runtime witnesses cannot pass. Exact native
execution of the new wiring is pending; model tests are not native receipts.
Expected-timeout native-stall commands now snapshot immutable assembly/current
inputs and independently retain exact native/control linkage. Post-containment
verification runs only after settled timeout ownership, under a bounded
five-second window within the profile budget/reserve; an input change cannot
masquerade as the expected deadline. This prerequisite is not MP-37 case import.
The subsequent MP-37 path now freshly executes that stall inside joint-attempt
bounds and independently corroborates its five-file graph before atomic import.
Its two frozen runtime witnesses remain mandatory; an unrelated recovery-source
UUID cannot substitute or be copied into their case. Both native/recovery graph
digests must come from imported proofs. This wiring is modeled, native-pending.
Its producer bytes additionally require executor-held post-containment output
hashes: predeclared absent retained outputs are sealed only after actual settled
ownership, within the combined input/output bound and post-check deadline.
Regular ownership, identity, no links and read-only retention are enforced;
rehashing replacement producer/graph files cannot replace that original map.
Qualification-input metadata also runs a fresh real competing-process ownership
probe, then owner barrier 30, exact kill/settlement and reopen of the same
database before runtime scopes. The bounded fixture retains distinct actual
owner/probe PIDs and probe-start hash only after checking real owner rejection.
The seven-file graph independently binds both commands, current assembly/input
snapshots, original executor-sealed probe bytes and joint-attempt bounds.
Missing/reordered reopen, changed probe bytes or foreign identities reject.
MP-43's frozen runtime witnesses remain mandatory; no recovery-source UUID is
borrowed. `ownershipSourcesSha256` must reference imported proof bytes.
The real macOS diagnostic is non-qualifying; Linux confirmation is pending.
MP-46 additionally runs the same immutable package-only consumer binary across
both explicit bindings and distinct owned stores before runtime scopes. Its
common assertion body is unchanged; opt-in safe events use exact argv while
legacy invocation/output remains intact. The six-file graph independently
joins both native/controller pairs, immutable assembly/current-input maps,
argv/cwd and ordered joint bounds. Missing/reordered/relabelled compositions
reject; existing runtime witnesses and imported `consumerSourcesSha256` remain
required. Local actual explicit/legacy execution is non-qualifying.
MP-47 additionally executes a staged copy of the sealed pre-F-05 marker with
current Abstractions/Core/Hosting images. Original marker/runtime metadata
and all other retained files stay unchanged. Complete staged images enter
current inputs before execution. The recorded-recovery projector accepts only
the exact original marker line, with no raw retention or frozen-binary edit.
Four-file authority checks original baseline/current platform hashes, complete
native input map, argv/cwd, actual settled success and joint bounds.
`binarySourcesSha256` must come from imported proofs; original runtime witnesses
remain mandatory. Actual macOS execution is non-qualifying and native-pending.
MP-48 runs the entire unchanged verifier suite with an unfiltered fresh loader:
original baseline, original failed-case-refusal mutation, then repair of the same
private adapter. A bounded runner retains no raw diagnostics. A fourteen-file
graph requires complete original interpreter sources and test inventory, sealed
packets/source snapshots, exact original argv/cwd, settled commands and joint
bounds. The red must be the named assertion with zero setup errors/skips.
Two binding-specific source facts consume all actual files and supply distinct
runtime execution UUIDs; recovery's UUID never qualifies MP-48. Imported
`inventorySourcesSha256` is required. The QC-only `none` binding receives no
invented source fact. QC-06/07/08 compose only complete frozen logical,
uncertainty/ownership and schema/recovery bases from both actual bindings in
the same joint attempt. Original UUIDs/proof hashes remain unchanged; report
admission recomputes exact unions and frozen exclusions. Only these fixed QC
keys allow cross-binding links, not arbitrary `none` dimensions. Missing
controls remain incomplete, failed attempts survive and exceeding 128 proofs
on retry rejects without truncation. Exact ee1/run40224149195 now confirms
90/3/9/0 across eight scopes/137 witnesses/six parents; both inventory facts
share one joint native parent. All three Linux jobs, 298 foundations without
skips and 129 aggregate scopes/1,821 witnesses pass. This admits inventory and
QC-06/07/08, not a qualifying complete profile; QC-02/04/05 remain incomplete.

Artifact native diagnostic controllers additionally request exact source
read-site capture for six crash, six retained-work and four transfer facts.
Closed <=1 MiB contexts, <=16 KiB source files and a five-second hook budget
bound capture. Exact owned paths/bytes and no symlink ancestors are required;
create-new hash-only packets cannot overwrite earlier evidence. Parent
diagnostics reselect current source bytes and require all sixteen original
runtime UUID/proof joins and immutable retained packets/consumption receipt.
Twelve native input snapshots include context, actual runner and current
transfer evidence. Discovery and legacy invocations request no capture.
The complete original publisher now emits one aggregate packet-hash index.
Only this index is declared as an ordinary command output: twelve immutable
inputs plus one output remain below the unchanged combined sixteen-file limit.
Actual owned exit precedes read-only output sealing. Independent source checks
bind the exact index/context to the executor-held original output/input hashes
and require every original packet hash; current-byte rehashing cannot substitute
the original seal. Partial sets emit no index. Legacy/discovery paths request
neither capture nor index output. Native replay of this increment is pending.
These packets/index do not replace original transfer/control authority; independent
artifact controller qualification remains closed and its 92/7/4/0 diagnostic
state is unchanged.
Native paced transfer children additionally capture their actual immutable
assembly and current input document. Original controller bytes must match the
executor-held control digest and returned command digest, with exact argv/cwd,
run/root/input-map and settled-exit equality. Per-transfer read-only native
receipts retain original sequences and hashes. An optional sixth safe-mode
runner argument now names its create-new original JSON proof output before
settlement; the measured native command predeclares and seals that output only
after actual exit. Two inputs plus one output preserve the combined sixteen-file
bound. Raw producer hashes must match original held output maps; reserialized
current bytes cannot substitute them. Legacy five-argument behavior is unchanged.
Cleanup and unmeasured transfer output declarations reject. This does not open
independent complete artifact source admission.
The shared pure measurement validator retains all existing exact qualified
sizes, kernel peak, protocol timing and settlement constraints.
Independent source admission now reconstructs each fixed runner/input/recipe/
controller/producer/composite/native-record graph from its original explicit
sequence, including after later commands. Exact generated-byte expectation,
argv/cwd and original held input/output/control hashes are mandatory. Both
consumption and source-parent checks require all four graphs, without fallback.
Qualification-origin joint bounds and complete crash/retention admission remain
unbuilt. Source-index run40228504830 fails its empty-frozenset-versus-tuple test
assertion despite SDK/lock success; the test now asserts no live children.
That overall failed snapshot is not admitted.
Original crash/state/readback and retained-child predicates now share the
independent source layer, preserving their exact validation bodies. Private
qualification-origin transfer paths require artifact qualification inputs;
diagnostic/category namespaces and foreign modes/profiles cannot substitute.
Selection, measured production, source recipes and contexts use that same gate.
This implements isolation/admission, not actual qualification transfers or
complete controller source authority.
Native qualification-origin transfer summary publication additionally requires
all four original graphs in increasing sequence, nonoverlapping transfer times
inside the actual common controller window and disjoint proof paths. Rejection
propagates before publication. The seven immutable transfer-control role hash
sets are source authority only, not qualifying case statuses.
The current artifact controller reader independently reconstructs all twelve
original child observations (exactly 24 original files), four original transfer
graphs, sixteen consumed source packets and the complete-set index sealed by
the original controller. Child run-ID reuse and recovery-error bytes reject.
Explicit original sequence lookup permits delayed admission after later
commands. Native factory/history admission additionally binds the owner,
manifest, exact settings/argv/cwd, twelve input hashes, sole output hash,
settled original command and nested witness times. Mode-derived qualification
namespaces now reach fresh joint-transfer orchestration, runtime contexts,
declared inputs and parent rechecks consistently. SDK diagnostics prepare and
recompute both category qualification inputs and emit a separate non-qualifying
artifact admission summary; transfer/scope failures interrupt rather than pass.
Local complete/factory/history models pass, but actual Linux replay remains
pending and artifact QCs/full profile qualification remain incomplete.
The current quality composer separately requires both bindings' source-parented
AS-11/12 for QC-10 and Local AS-41..44 with exactly four Object simulation
exclusions for QC-11. The independent report join recomputes complete current
attempts, runtime/proof links, timing and exclusions. Missing source parents
prevent source-sensitive qualification cases from passing; foreign/shortened
bases and borrowed durability reject. Diagnostic mode and other artifact QCs
remain incomplete. Retry history is preserved. Local modeled validation passes;
actual Linux replay and full profile qualification remain pending.
QC-09 retains all 84 inherited logical case/binding rows and all current-attempt
runtime observations in a canonical private basis receipt. The ten exact source
anchors and receipt/source-parent hashes form its bounded direct projection;
the underlying complete evidence is never shortened. Report admission rebuilds
the entire receipt and exact proof-path digest. Original bytes survive retries.
Cumulative file/byte budgets include basis receipts before atomic commit.
SDK persistence checks original bytes, read-only permissions and retained
hashes; non-qualifying summaries add quality-source count/digest. Missing,
changed, shortened or overflowing bases reject. Local models pass; actual
native replay, QC-03/04/05/12 and complete profile qualification remain pending.
Qualification-origin artifact controller transports use validated inspection
before mandatory independent source reconstruction and native history
admission, as do other source-only controllers. Ordinary diagnostic and
session-based transports retain their existing admission path.
Category manifests select actual captured provider archives per binding, not the
SDK wrapper package. Frozen-slot/category/inventory mismatches reject before
launch; mixed scopes retain both archives. Native source admission independently
checks the full package set and each entry's association. Existing report
binding/package hash equality remains unchanged; distinct-package models do
not establish actual native qualification.
SDK completion now emits the four partial public category reports only after
input recapture and rechecking the original read-only history hash, complete
frozen final keys/exclusions, public links and every actual proof-file hash.
Runtime proof paths identify original owned logger outputs without copying or
rewriting bytes. Missing/changed histories or files and shortened inventories
reject before report publication. Reports remain explicitly Incomplete/
non-qualifying and make no resource-release/full-evaluator claim; safe summaries
retain history/report hashes and report state. Actual Linux execution is pending.
The prior byte-capture checkpoint cf4/run40227343651 independently passes
three Linux jobs, 300 native foundations without skips, 13-lock/18-package
replay and 129 scopes/1,821 witnesses. It admits original byte capture, not the
later output seal or measurement records. Metadata/artifact states remain
90/3/9/0 and 92/7/4/0; full qualification remains closed.
Exactb1/run40220115471 independently passes all three Linux jobs, 291 native
foundations without skips, 13-lock/18-package replay and 128 scopes/1,819
witnesses. Qualification metadata has seven scopes/135 witnesses/five parents
at 85/8/9/0, admitting controls through MP-47 only, not later inventory/QC work.
Exact5bc/run40218754070 fails at an original MP-19 queue/deadline witness after
287 native foundations and lock/package replay pass; its cause remains unknown
and no ownership/consumer admission follows from that failed run.
Earlier exact `f038df0`, run 40216546349, independently passes three Linux jobs,
283 foundations without skips, 13-lock/18-package replay and 128 scopes/1,819
witnesses, including seven-scope metadata at 80/13/9/0. This admits MP-37/output
anchoring, not later ownership/consumer/binary changes or full qualification.
Earlier exact `2ac4ed6`, run 40215065690, independently passes all three Linux
jobs, 280 foundations without skips and 128 scopes/1,819 witnesses. Its seventh
qualification-input metadata scope and post-timeout input checks pass, retaining
79/14/9/0 across seven scopes/135 witnesses/five parents. This does not admit
the subsequent MP-37/output or MP-43 increments or a complete profile.
The earlier source-linking execution, before executor-held byte anchoring, is
independently admitted at exact `78c5919`, run
40202060742: all three Linux jobs, 273 foundations without skips and all
121 scopes/1,684 witnesses pass, including four metadata/three artifact source
parents and fresh category controls. This is still diagnostic linkage, not
qualification-origin admission or completion of remaining control obligations.
The earlier command-parent path passes exact `ac561f2`, run 40188204924: all three jobs,
269 foundations without failures/errors/skips and 115 scopes/1,457 executions.
This admits invocation ownership for that snapshot, not source qualification.
Complete artifact/metadata diagnostic execution additionally passes exact
`b72829c`, run 40190769309: three jobs, 270 foundations without skips,
121 scopes/1,684 exact witnesses and independently fresh artifact transfer
command/start identities. Both complete histories retain their incomplete
obligations and `qualification: false`; later control changes are not covered.

Category prepared-inspection contexts contain the selected one metadata/two
artifact facts while the complete three-fact configuration fingerprint remains
bound. The standalone prepared scope still requires all three facts. Category
inspection/controller parent joins require the exact catalog scope and binding;
they are diagnostic and do not open qualification. Actual local execution
covers all six category inspection scopes/twelve source executions; remaining
scopes leave the histories explicitly incomplete, with no native containment or
complete profile execution claim.
The native diagnostic path now additionally predeclares and executes all six
metadata scopes under separately captured/recomputed metadata inputs, then
atomically imports all unchanged transports into a private 102-entry diagnostic
history: 96 inherited cases plus six qualification obligations. Missing parent
controls remain incomplete; execution/admission errors
persist incomplete attempts and propagate. Complete Linux execution is admitted
at exact `216413a`, run 40187523765: six scopes/134 witnesses, 71 Passed,
22 Incomplete (six QC and sixteen inherited parent controls), 9 NotApplicable,
0 Failed. Native foundations pass 268 checks without skips. This admits that
diagnostic snapshot, not profile qualification or the later command parents.

The same engine additionally wires all six artifact scopes/227 witnesses under
separately captured/recomputed artifact inputs. It re-executes four actual paced
256 MiB/4 GiB transfer children in `category-artifact-transfers` stores/cache/
proofs before the category controller runs. Controller settings and source
admission require those current measurements; an earlier harness receipt cannot
satisfy this namespace. Default standalone paths remain unchanged. The private
artifact history includes all 103 expected entries (96 inherited plus seven QC)
and uses the same atomic admission, unchanged transports and retained failure
behavior. This native artifact addition remains pending and non-qualifying.

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
native request passed at `9ce6b25`, run `40127065375`: all three jobs,
185 foundations and 73 scopes/617 observations, not complete bindings/category/
session or composition-profile proof.

Owned-session preparation now includes an explicit authority closing fence that
joins recognized/retained guards, queued admissions and actual retained reference
queries before reopen. Its task is stable within a closing generation; reopening
creates a new task rather than borrowing a completed predecessor. Binding-only
compilation makes the same source-linked authority/reference-decision internal,
without importing HostAdapters, Hosting or the other provider. These are not
complete category bindings or substitute mandatory fault controls. Three common
checks requested 74 scopes/620 observations. Run `40128473761` failed before
authority discovery because its scope lacked the original-artifact routing
prefix; that transport is corrected and the failed run is not admitted.

`IArtifactAssertionSession` is explicitly a partial projection, separate from
the complete category session/fault-driver contract. Its typed observation points
select real fixture boundaries, not expected results. The Local implementation
constructs actual store/validator/maintenance/lifetime surfaces, keeps one
identity/authority/resource through compatible reopen, rejects overlapping
registrations/transitions and protects replacements from stale disposal.
Actual settlement joins store stop, final callback work and authority ownership;
allocator retries share that same task and reuse unfinished observations.
Callback failures remain faulted after physical joins, including failure during
stop; a successful retry cannot erase them. Only the controller may physically
delete roots or report `Released`. `AwaitSettlementAsync` joins observed provider
workers only, not authority closure or controller release.

Local/Object provider callbacks have separate final-settlement tracking so idle
and stop retain their work without changing frozen public cancellation/handoff
or admission capacity. Fifteen package-only Local cases include actual native allocator overlap
enforcement and simultaneous registration of every typed observation. Two
interface-only common checks exercise real release ownership on both providers.
Closed supported-name sets bound callback count without a contradictory
sixteen-observer ceiling.

Six further common checks exercise actual receipt-recorded, read-opened and
reconciliation before/verified transitions on both providers. Object uses distinct
new hooks, never unrelated `object.direct` callbacks. Callback failure after a
real stream opens must release stream/guard/single transfer capacity; failure
after content verification must leave actual uncertain publication recoverable.
These hooks are prerequisites, not a completed category fault driver.

The partial Local/Object projections source-link one internal provider-free
ownership/session coordinator. Each still constructs its own real provider and
maps its own private controls; the SDK gains no concrete provider dependency.
Local compatible reopen retains identity/authority/root/content. Object logical
restart must join the old provider and authority before admitting an empty
private child with a fresh epoch/authority under the same allocation. Original
sessions retain immutable identity/authority. Every replacement is tracked
before initialization, including failed/canceled unpublished generations;
only successful admission changes the current cleanup handle. Final settlement
joins every provider/authority generation. Partial projections do not satisfy
mandatory category fault-driver admission or imply durable Object restart.
Sixteen package-only Object cases cover these semantics alongside fifteen Local
cases, including actual allocator overlap and admission-clock cancellation.

Run `40131392286` at `88c5d01` failed pre-runtime with `ProofMismatch`, despite
190 successful foundations and lock replay; it is not admitted. Diagnostic
enumeration now hashes the same consumed managed/runtime formats plus only
the admitted architecture's native assets and all lockfiles. Unconsumed build
assets do not exhaust the input budget. Default full manifests and selected
input caps remain unchanged; traversal still rejects symlinks, non-regular
entries and identity races even outside the selected inputs. The next exact
native run `40133457888` at exact `c58978e` passed all three jobs, 191 foundations
without skips, independent lock replay and strict 76-scope/643-observation
admission; the earlier failed run remains unadmitted.
The owned-Object increment passed exact `36481c0`, run `40134767571`: all three
jobs, 192 foundations without skips, independent lock replay and strict
77-scope/659-observation admission, not category/profile proof.

`ArtifactAssertionOptions` supplies explicit test-fixture limits and a live typed
reference source, never interprets a case/profile ID, and grants no fault-driver
or category admission. Both actual providers receive the immutable limits on
each initialization. Every authority generation consults that source for the
exact protected stamp; prior observations are not cached across queries/reopen.
Absent queries retain fail-closed deletion. Typed observations reject negative/
contradictory counts and available snapshots without revisions; unavailable
zero-count results cannot authorize deletion. Actual source work remains owned
after caller timeout, and reopening/final settlement must join it. Eleven
configured cases cover both providers, pre/post-reopen enforcement, changing
references, unavailable results and retained queries. Exact `853c669`, run
`40136186008`, passed all three jobs, 193 foundations without skips and strict
78-scope/670-observation admission.

Partial exact-stamp payload damage runs inside each provider's own actual worker
supervisor, including native open/observation/mutation/flush/disposal. The SDK
contains no filesystem operations or provider dependency. `PayloadDamage`
observes a real open handle before physical damage; cancellation does not settle
that worker until the callback and native disposal finish. Reopen/final cleanup
must join it. Mutation does not fabricate receipt or quarantine state, and
current full-stamp checks reject old epochs/incarnations. Twenty-three cases
include actual corrupt copy/later quarantine, held native work, failed observers
with unchanged content and faulted final settlement, stale sessions, real ABA,
empty payloads and conflicting reads. Payload run `40137341231` at exact
`1367a51` passed all three jobs, 194 foundations without skips and strict
79-scope/693-observation admission, including all 23 payload rows and actual
prerequisite/replay chains.

The four frozen damaged-read parameters also now execute one provider-free
consumer with mechanically identical checks/order. Actual capture, damage and
restoration retain their legacy fixture boundaries; this is not an owned full
fault driver. Two real-validator mutations require actual corrupt-evidence
failure before substituting success. The unchanged common type assertion fails
and fresh genuine validators pass. Exact transport requires all four frozen
rows plus both mutation rows, rejecting shortened or foreign vectors before
launch. Run `40138438076` at exact `4a907c5` passed all three jobs,
195 foundations without skips and strict 80-scope/699-observation admission,
not complete fault-driver/category admission or full metadata/artifact integration.

The original overlapping read/reconciliation quarantine body and both
admitted-open revalidation rows also now execute provider-free consumers.
Actual provider observer mapping, publication failure, native hold/release
barriers and physical replacement remain fixture-side. Exact assertions and
public-operation order are mechanically preserved; common checks never choose
by provider ID or change expected quarantine outcomes. Named barrier objects
live in wrapper scope while actual observations/releases remain at the original
transition points. Exact transport requires all three unchanged identities and
rejects shortened/foreign vectors before launch. Run `40139402208` at exact
`f05851a` passed all three jobs, 196 foundations without skips and strict
81-scope/702-observation diagnostic admission, not full qualification.

All six original committed-detection parameters now share one provider-free
consumer with mechanically identical assertions/public-operation order.
Their inherited durability expectation is fixed by the independent original
test variant, not provider capabilities, a binding callback or a pass flag.
Physical removal/restoration and publication fault mapping stay fixture-side;
these legacy callbacks do not establish complete owned fault-driver admission.
Exact transport rejects missing/foreign parameters or a changed scope name
before launch. Run `40140436330` at exact `e089042` passed all three jobs,
197 foundations without skips and strict 82-scope/708-observation diagnostic
admission.

Transitive review found omitted Local quarantine stop/reopen checks in three
earlier consumers. Their complete original helper now lives in common code;
only construction stays fixture-side in `ArtifactQuarantineReopen`. The
fixed original Local test variant supplies its actual current lifetime,
identity, authority and fresh-store factory; Object supplies no durable probe.
Every original stop, construction, initialization, corrupt read, finally-stop
and original-store reinitialization remains in order while enclosing streams
and guards retain their original lifetimes. No callback supplies an assertion
or expected result. Three real reopened-store mutation pairs require actual
corruption denial before substituting its code and fail the unchanged common
assertion; genuine stores pass. A frozen transitive-helper/owner guard rejects
omissions. Earlier helper-normalization claims did not prove these durable
checks. Run `40141545447` failed closed with `UnknownDiagnostic` in this scope
and is not admitted. Actual method-level discovery reproduced fifteen rows,
not its nine-row Local-only declaration. Corrected transport requires all
twelve frozen provider parameters plus three mutation rows; prelaunch
admission rejects incomplete original-method expansion. The safe logger is
unchanged and Object's logical rows do not establish durable restart.

The nine remaining original evidence-validation parameters now execute shared
provider-free consumers. Full bodies retain every assertion, public-operation
order and source/guard lifetime after explicit interface/control/helper/token
forwarding, including the complete transitive quarantine helper. Physical
permission changes, payload removal/restoration and actual native readiness
observation remain fixture-side legacy boundaries. No callback supplies
assertions or expected outcomes. Original pre-try Unix rejection remains in
order; the fixture permission setter also retains a local platform guard.
Exact new transport rejects missing/foreign parameters or changed scope names
before launch. Quarantine callers explicitly supply the real durable context
or select logical-only scope; no reopen parameter is defaulted. The newest
request passed run `40143552793` at `c1d2a6b`: all three jobs, 200 foundations
and 84 scopes/732 observations, including the corrected fifteen-row quarantine
scope, not full fault-driver/category/profile admission.

Six original recovery methods now forward all twelve provider parameters (eight
frozen category witnesses and four additional existing cases) to
`ArtifactRecoveryAssertions`. Complete-body parity preserves concurrent
cursor bounds/retirement/expiry, inventory changes, ownerless expiry,
finalized noncommit, staging-generation fencing and non-authoritative
observation. The original wrapper fixes enumeration consistency independently
of provider capabilities and retains clock/driver ownership. No filesystem
control or provider switch enters the common checks. Missing/foreign parameters
and renamed scopes reject before launch. The expanded request is
85 scopes/744 observations passed `40144435943` at `ffec99a` with all three
jobs and 201 foundations, not full category/profile admission.

Five further recovery methods share ten parameters (six frozen witnesses and
four additional existing cases) through provider-free admitted-history,
generation-race and progressing-commit consumers. The SDK owns the original
managed barrier with identical body, 10/20/10-second budgets and source/barrier
nesting, while physical fault registration/removal remains fixture-side.
The legacy barrier alias lives under package-only `Cases/`, so ordinary
contract compilation gains no SDK reference. Complete-body/helper parity and
exact prelaunch parameter admission remain required. Run `40145322908` at
`9d19bd1` passed all three jobs, 203 foundations and 86 scopes/754 observations,
not qualification.

The three remaining original recovery bodies now use interface-only common
consumers: retained Object stop, committed-decision rollback/reopen and
durable-receipt staging release/reopen. One frozen witness and two additional
existing Local facts retain exact original checks, 105 retired incarnations,
real reopened-store readback and source/current/fresh-store lifetimes.
Physical permissions/snapshots, fresh construction, record-write registration
and root-cleanup authorization remain fixture-side, with no assertion or expected
outcome supplied by callbacks. The common consumer determines the real stop
result before the fixture setter/getter reflects root-cleanup permission.
Run `40146117625` at `994f9fb` passed all three jobs, 204 foundations and
87 scopes/757 observations, not qualification.

Six logical admission methods now forward eleven exact identities (four frozen
witnesses and seven additional existing cases) to interface-only consumers.
The common noncooperative check owns its original TCS hold/release, deadlines,
retained-ownership and stop assertions; actual observer registration still
precedes concrete construction. Common checks own admission failures, capability
baseline, corrupt manifest bytes/non-reset, fixed original Local-versus-Object
reopen expectations and outside-sentinel/child assertions. Factories and
callbacks supply only actual construction, authority and raw observations/I/O;
no expected result or asserted outcome is returned by a callback.
Original symlink try/finally, root lifetime and actual cleanup permission remain
fixture-owned. Native concurrent-admission and cross-process root ownership
tests, including bounded output/PID/exit/retained-root helper obligations, are
unchanged. Method-level discovery must match all eleven declared identities;
missing/foreign parameters and renamed scopes reject before launch. The next
request `40146850203` was canceled before jobs, not admitted; its complete scope
is retained in the latest expanded request.

The two remaining deletion methods now forward all four frozen parameters to
shared pending-reclamation and live-reference consumers. Original assertions,
borrowed-source lifetime and publication/read helpers remain unchanged after
explicit interface/control/token forwarding. Common consumers retain uncertain
delete, hidden content, actual cleanup count/bytes, unchanged receipt identity/
stamp/outcome, reclaimed state and idempotent retry, plus both reference denials,
intact public readback and eventual removal. Lost-ack fault registration and
actual reference count/availability remain fixture-side; no callback supplies
an expected result. Exact method-level discovery must contain all four rows.
Native run `40147381011` at `992b4a5` passed all three jobs, 206 foundations
and 89 scopes/772 exact discoveries/executions, including all eleven admission
identities and every actual prerequisite. This is not full qualification.

`DirectVerification` is a distinct typed observation, not an alias for selection
or receipt persistence. Local's optional `publish.direct` runs before original
direct validation for both new/duplicate publication; Object maps its existing
`object.direct`, which also covers both branches. Existing checks, locks,
publication decisions and actual reads remain unchanged. A common consumer holds
real publication at that boundary, rejects a returned acknowledgment while held,
then joins actual completion/worker settlement before checking expected outcome,
same-incarnation duplicate reuse, borrowed-source ownership and public bytes.
It does not assert independent readability at a held selection/verification gate.
Preliminary architecture review identified the selection-only substitution gap;
full fault-driver/origin/category/profile admission and final T081 remain open.
Native run `40148199370` at `6d1f73b` passed all three jobs, 207 foundations
and 90 scopes/776 exact discoveries/executions with every actual prerequisite,
not full qualification.

Scoped capacity injection is a separate typed path from ordinary observation:
the owned projection creates the exact ENOSPC-shaped exception internally and
throws it after Local's actual `stage.prefix` or Object's actual `multipart.part`
write. Every arrival is counted. Only that exact exception is excluded from the
observer-failure queue; it still propagates to the provider's real public failure
classification and cleanup. No queue is cleared and the stable settlement task
is never replaced. Duplicate registration/admission fences and identity-checked
scope disposal remain unchanged. Ordinary same-HRESULT exceptions still poison
final settlement, as do the existing failed-damage observers.

Four exact package-only rows cover both providers: common checks require
repeated Capacity failures, source progress without source disposal, exact
not-committed reconciliation, fresh-scope replacement surviving stale disposal,
restored full single-ticket capacity, and actual publication/readback; the
unexpected-observer counterparts require the exact original exception in the
faulted final task and no optimistic Released observation. This is an injected
storage failure, not measured disk exhaustion or a complete mandatory fault
driver. Native run `40148998281` at `53b1433` passed all three jobs,
208 foundations and 91 scopes/780 exact discoveries/executions with every actual
prerequisite, not complete qualification.

`InjectUnclaimedCleanupFailureAsync` uses the existing Local/Object indexed
undelivered-result reclaim seam. The actual result is indexed before the
injected exception and removed only after genuine successful cleanup. Four
exact parameters cover both providers' reservation and read-open handoffs:
the common consumer holds actual completion, cancels delivery, releases/joins
the worker, requires one failed reclaim and fenced readiness/admission, then
requires a failed stop with retained live ownership and a second failed reclaim.
Only scope removal allows the actual cleanup retry and successful stop/final
settlement. Barrier release, public-task/worker joins and retry use non-cancelable
cleanup paths; the original borrowed source survives until actual settlement.
This does not substitute for physical prefix/object permission-failure cases,
change provider cleanup mechanisms, or declare complete mandatory fault support.
Native run `40149692533` at `1acdeb0` passed all three jobs, 209 foundations
and 92 scopes/784 exact discoveries/executions, not qualification.

The owned synchronous storage hold maps Local's real `BeforeRecordWrite` and
Object's real `BeforeObjectDelete` callbacks. The common consumer publishes and
reserves the deletion ticket before arming; configured available-zero reference
authority permits actual deletion admission. A missing query correctly denies
deletion and cannot count as boundary entry. An early public return before entry
fails immediately. The synchronous hold ignores operation cancellation, counts
arrivals and has a fifteen-second watchdog whose expiry poisons final settlement.
It is not a stalled filesystem syscall.

Both parameters require deadline/uncertain caller failure with retained live
ownership, actual pending workers, fenced admission/readiness, real authority
exclusion and failed retained stop while held. Explicit release precedes genuine
worker settlement and successful stop. Scope disposal is identity-checked and
task-stable, disarms only itself and joins actual workers; stale disposal must
not remove a replacement. Ownership removes remaining controls only after actual
stop/worker settlement. Existing borrowed-source, authority-settlement and root
authorization ordering is preserved. Original cross-process native containment
remains mandatory and separate. Native run `40150871211` at `f68812e` passed
all three jobs, 210 foundations and 93 scopes/786 exact discoveries/executions.

The full Local/Object factories now retain these genuine owned sessions and
return their actual store/validator/maintenance/lifetime/authority references.
The full fault driver requires `DamagePayloadAsync(stamp, truncate, token)`:
no targetless mutation or last-artifact lookup remains. `BorrowedSource` and
`BorrowedDestination` are actual caller-owned streams supplied after their fault
is armed. Their real reads/writes count entry and ignore cancellation until
explicit release; public return, retained cleanup and final worker settlement
remain actual provider behavior. The factory disposes its borrowed streams only
after genuine session close/reopen settlement.

Publication, direct visibility and receipt controls hold their actual named
boundaries. Generation holds verified staging after the common consumer actually
cleans expired ownership and starts a replacement; public stale-owner rejection,
increasing generation, conflicted old cleanup and readback corroborate the control.
Payload damage counts its actual non-holding physical boundary. Capacity and
cleanup reuse the exact privately scoped injected failures; generic entry waits
observe those actual registrations without disarming them on wait cancellation.
Native control still means the documented synchronous fixture boundary, not a
stalled syscall or durable proof.

The registry serializes release-task publication, not actual worker joins;
concurrent release callers share that task, rearm waits for success, and failed
settlement observation can be retried before stable scope disposal. The
architecture review's two-provider deadlock regression first failed, then passed
with independent release/rearming. Twenty-four exact new parameters cover all ten
controls, actual origin capture/reopen and concurrency. Fresh replay passes
311 artifact, 103 Consumer and 89+89 metadata cases. Native run `40153251707`
at `f73a55a` passed all three jobs, 211 foundations and 94 scopes/810 exact
discoveries/executions with every prerequisite. Complete parent-origin/profile ingestion,
category parity/integration, qualification and final T081 remain open.
The diagnostic parent passes only the two admitted provider archive hashes to
these fixture factories and rechecks the exact candidate archive bytes before
writing their fixed runsettings variables. Runtime caches stay independent:
factories never assume the build cache is available, read an arbitrary archive
path, or manufacture a package identity.

The full-binding scope additionally requires the actual controller run ID and
`full-artifact-binding` case identity. Its 24 expected rows emit 26 actual session
origins: one per ordinary row and the original plus actual child for each reopen.
Parent ingestion binds all eight roles independently to the selected adapter/
provider runtime images and package archives, matching admitted descriptor bytes
and preserving strict component identity/runtime/reopen-lineage checks. The safe
logger manifest includes the four real component images alongside the Consumer;
missing admitted images reject before launch. Exact capability/fault serialization
order is retained rather than sorting descriptor arrays.

Fresh local observation corroborates all 208 role/image/archive matches, exact
24-row discovery and both reopen lineages with a separate empty runtime cache.
Raw VSTest output remains in bounded memory only, never retained as proof.
Origin-enabled run `40154183825` at `d1fd43d` passed all three jobs,
212 foundations and 94 scopes/810 exact discoveries/executions with every
prerequisite. This upgrades the existing diagnostic
scope, not complete category/profile qualification or other pending origin imports.

The metadata diagnostic adds six exact rows executing unchanged capacity,
writer-budget and publication-protection consumers through observed independent
Memory/SQLite factories. It requires controller run/case IDs, independent
archive-bound declarations and all six actual component roles, with their four
binding/provider images in the logger manifest. Missing packages/images, foreign
or mixed package families and shortened/foreign inventories reject before launch.
Actual SQLite environment admission remains mandatory. Fixed private metadata
runsettings variables contain only independently rechecked provider archive hashes;
runtime caches remain independent. Exactly one matching origin per row is required.

Local bounded observation confirms six actual metadata origins/36 role/image/
archive matches, not native acceptance or metadata reopen attribution. Fresh replay
passes 311 artifact, 109 Consumer and 89+89 metadata cases. The expanded native
request passed as run `40155045988` at `9034153`: all three jobs,
214 foundations and 95 scopes/816 exact discoveries/executions with every prerequisite.
Other origin/profile imports, complete category/integration qualification and
final T081 remain unfinished; locks, historical seals and reviewer markers are unchanged.

The metadata scope now additionally requires both exact compatible-reopen rows.
Their provider-free consumer corroborates grouped public registry/package bytes,
preserved epoch/authority, genuinely fresh store/fault instances and stale-control
fencing after stale disposal. Failed assertions dispose an unreturned child;
successful handoff preserves caller ownership. Memory's actual closed logical
image is not durable restart. Each reopen row emits its actual parent then child,
and parent ingestion requires two matching origins for that exact witness.

The eight metadata rows yield ten origins, eight creates/two reopens and 60 actual
role/image/archive correspondences with an independent runtime cache. Fresh replay
passes 311 artifact, 111 Consumer and 89+89 metadata cases. The next native
request passed as run `40155922560` at `4548183`: all three jobs,
214 foundations and 95 scopes/818 exact discoveries/executions with every
prerequisite. Complete category/profile qualification and final T081 remain open.

The same observed factories now execute twenty further actual metadata rows:
unchanged entity/relationship and final-graph consumers, independent candidate
snapshots, faulted atomic candidates, grouped reads, lease-generation overflow,
owner/generation/revision fencing and all three decision-time expiry actions.
The actual run clock drives expiry and real fault hooks supply observations;
no common assertion bytes or frozen wrapper identities change. Strict parent
admission requires the complete 28-row scope, with one origin per ordinary row
and two per exact compatible-reopen row: 30 genuine origins and 180 actual
role/image/archive correspondences. Fresh preparation/replay pass 311 artifact,
131 Consumer and 89+89 metadata cases; the next native request is 214 foundations
and 95 scopes/838 observations; it passed as run `40156840261` at `2beff54`,
all three jobs and every prerequisite. Standalone metadata authority
checks do not establish artifact/metadata shared authority; complete category/
profile qualification and final T081 remain open.

Thirty further observed rows import unchanged canonical text, registry/
authorization partitioning, reference replacement/metadata revision ABA/
telemetry rollback, create/revision races and reconciliation contention,
I/O uncertainty, acknowledgment loss, contributions and corrupt receipts.
Both malformed-schema layouts run without pre-admitting schema, preserving the
original empty/partial layout expectations. Neither common assertion bodies nor
provider mechanisms change. Strict admission now requires all 58 metadata rows,
60 actual origins and 360 actual role/image/archive matches. Fresh preparation/
replay pass 311 artifact, 161 Consumer and 89+89 metadata cases; the next native
request passed as run `40157571215` at `8fed412`: all three jobs,
214 foundations and 95 scopes/868 exact discoveries/executions with every prerequisite.
These metadata revision checks do not qualify artifact-incarnation fencing,
the real cross-store authority bridge or complete category/profile acceptance.

Eight further observed schema rows invoke unchanged upgrade, invalid-upgrade,
upgrade-exclusion and future/corrupt-schema consumers. A transparent caller-side
session recorder forwards actual operations/disposal, captures each underlying
observed factory session and real child before handoff, and disposes an
unreturned child on capture failure. It never substitutes itself as an origin
factory/component. The common assertion bodies and their disposal scopes remain
unchanged. Strict parent admission requires each exact lineage count: three for
upgrade, two for invalid/exclusive upgrade and four for future/corrupt schema.
Focused admission checks reject missing/extra/foreign descriptor origins.

The complete 66-row scope emits 82 genuine origins, 68 creates/14 reopens and
492 actual role/image/archive correspondences. Fresh preparation/replay pass
311 artifact, 169 Consumer and 89+89 metadata cases; artifact observation remains
24 rows/26 origins/208 correspondences after the shared count-validator extraction.
The next native request is 215 foundations and 95 scopes/876 observations,
not yet admitted. Memory upgrades/reopen remain logical; native backup/recovery,
complete category/profile imports and final T081 remain separate unfinished work.

Forty-two further observed rows import unchanged bounds/scopes, all page kinds,
request/result bounds, bounded datasets, ticket/lease clock rollback, cancellation
decisions, queue capacity, exception mapping, ledger/diagnostic behavior,
publication evidence/replay/orphan handling, corrupt groups/pages and explicit
admission/invalid-budget/incomplete-cleanup/disposal ownership consumers.
Admission/budget cases start genuinely unprepared. The common disposal callbacks
target the actual store while the enclosing session retains resource ownership.
Origins are captured while components are live and emitted only after assertions
pass. The incomplete-cleanup consumers release their real held work and join
actual settlement before outer disposal; finite timeout never means Released.

Strict parent admission requires all 108 rows and 124 genuine origins
(110 creates/14 reopens), with 744 actual role/image/archive correspondences.
Fresh preparation/replay pass 311 artifact, 211 Consumer and 89+89 metadata
cases. The next native request is 215 foundations and 95 scopes/918 observations,
not yet admitted. Common assertion/disposal scopes and provider mechanisms are
unchanged; complete category/profile imports and final T081 remain unfinished.

Twenty-four further actual rows exercise all six continuation-corruption shapes
over all six components, the five supported query-dimension corruptions and
foreign-store epochs. Epoch consumers prepare two independent actual stores
and require two create origins. Strict parent admission now requires all
132 rows/150 origins (136 creates/14 reopens), with 900 actual role/image/archive
correspondences. Fresh preparation/replay pass 311 artifact, 235 Consumer and
89+89 metadata cases. The next native request is 215 foundations and
95 scopes/942 observations, not yet admitted. Schema run `40158238921` at
`9399c3c` passed all three jobs, 215 foundations without failures/errors/skips,
95 scopes/876 exact observations and every prerequisite. It does not verify
the later controls/cursor increments or establish complete qualification.

The later corruption convergence extension preserves those 132 identities and
requires 152 rows/172 origins (156 creates/16 reopens), with 1,032 role/image/
archive correspondences. Twenty actual rows cover record/operation ownership,
capture conflicts, cancel-after-mutation, retained restoration recovery and
held-candidate reopen/disposal admission. The original wrappers use the same
SDK assertions through typed capture/payload-change controls. Local package and
assertion-mutation parity do not establish complete extraction/native admission.

The artifact payload/progress extension preserves the preceding 54 rows and
requires eight more: bitflip/truncated reads, progressing commits and exact
payload controls on each binding. Capture/replacement/removal use bounded
copied buffers and the exact current stamp, never private paths. Local damaged
reads perform genuine compatible reopen and require both actual origins;
Object remains simulation-only. The typed progress observer registers when
the SDK requests it, after setup publication. The unchanged quarantine helper
and additional async-reopen denial check remain mandatory. Local assertion
parity/negative controls are not a complete QC-03 or native source parent.
The actual authority's read protection must span payload selection, I/O and
file disposal. The typed `PayloadSelected` boundary and waiting-admission
counter corroborate real deletion exclusion; stamp checking alone cannot
authorize recreating a payload after its incarnation has been reclaimed.
Thirty recovery/evidence/expiry and stream-ownership rows further extend the
complete artifact selection to 92. They execute thirteen unchanged SDK entry
points on both actual bindings, including all completion/handle/renewed
descriptor shapes, with one typed origin and real settlement per row. Original
one-byte artifact/staging limits remain required for ownerless-reservation
expiry; a ticket-count limit is not equivalent setup. Complete local wrapper
parity/assertion negatives are not a native source parent.

Seventeen budget/failure/reference/history rows extend that complete selection
to 109. Authority deadlines, canceled commits, capacity crossing, cooperative
cancellation, sanitized failures and live/unavailable reference denial retain
the original harness options. Reclaimed histories retain their original
one-identity budget and forward expiry; the incarnation case is Local-only.
Each requires a genuine typed origin and settled resources. Complete local
wrapper parity and SDK capacity assertion negatives are not native admission.

Twenty handoff/progress/rollback rows extend that complete selection to 129.
Awaited observer installers preserve synchronous entry points and register only
at the shared assertion's requested stage; removals are awaited and barriers
release on removal failure. UTC rollback must not rewind monotonic ownership
time. Every new row requires its actual origin and settlement. Complete local
wrapper parity/assertion negatives remain non-qualifying diagnostics.

Twelve admitted-work/reconciliation/cleanup rows extend the selection to 141,
preserving original deletion-history/transfer/reconciliation limits and the
five-second shutdown allowance. Local before-resolution and Object direct-
verification observations remain the original provider-specific choices.
Recovery installation/removal and acknowledgment-loss registration disposal
are awaited, with original synchronous wrappers forwarding to the same assertions.
Every row requires its actual origin and settlement. Complete twelve-row local
parity and three named SDK-only assertion negatives do not qualify a provider.
Exact earlier `831b00c`/run40271691109 strictly admits artifact129/metadata152:
336 foundations/no skips, unchanged native transfer/recovery obligations.
It does not admit this extension or complete QC-02/QC-03.

Original qualification-input metadata scopes now require independently selected
63-row families, exact role/creation/reopen forests, sealed original runtime
packets and SDK/provider/host/wrapper image pins. Their source parents are
reconstructed from actual held command inputs, provider/context settings,
argv/cwd and current-attempt execution receipts, not caller-provided role maps.
Complete local 152/63/63 metadata replay and three SDK-only mutations pass;
445 tooling tests/19 native skips cover source substitutions. Exact
`74cf619`/run40279501756 now passes all three Linux jobs, 337 foundations/
no skips and independent admission of both original metadata parents (ten
total). Earlier `bc85094`/run40276791513 admits artifact141/metadata152.
Sixteen individual local parameter mutations require exact 2/1/1 named
failures across complete 152/63/63 families, all other rows passing. These
are not admitted native exact-parameter controls; QC-02 remains incomplete.

Eleven history-candidate rows extend the artifact scope to 152. Awaited
observation installers retain the synchronous original common entry points,
seven bounds parameters and two resume cases. Adapters own observation and
one-shot ticket-candidate injection separately, rejecting duplicate owners.
Ordinary observer exceptions fault settlement before injection is considered,
including the same exception type/message. Fresh packages pass 308 selected
Consumer rows without skips. Complete 304-row actual/nine-row frozen parity
also passes; SDK-only bounds/resume mutants give exactly seven/two named
failures in both families, all other rows passing and actual SDK images
matching each archive. The extension awaits exact-head native admission.

Ten receipt/read-opening/reconciliation rows extend the artifact scope to 162.
Typed failure registration accepts only read-opened and verified-reconciliation
points, with ordinary callback exceptions still faulting settlement rather
than being reclassified as injected. Awaited shared overloads preserve all
six original cases, one-slot/no-waiter limits and receipt/readback assertions.
Fresh packages pass 318 selected consumers; complete 314-row actual/six-row
frozen parity passes. Three SDK-only assertion mutants each give both families
two named failures, all other rows passing with exact runtime SDK/archive
images and no skips. This extension awaits exact-head native observation.

Exact `d30271d`/run40286734253 passes all three Linux jobs/337 native
foundations without skips and admits artifact162/metadata152 with ten metadata
parents, not the later argument transport.

Closed metadata argument packets are recorded inside the four actual SDK
methods and joined to source/component identities in runtime proof schema3.
Late output drains calls once. Early original-schema output retains its order
with an explicit per-assertion observation scope; closure joins output before
detaching, overlapping owners reject and object reuse does not replay calls.
Independent logger/parent validation preserves schema1/2 support, existing
packet/proof bounds and immutable cross-scope replay protection. Metadata category
declarations, not reference binding names, govern argument admission. This transport
does not complete QC-02. Independent source admission now requires the frozen
per-witness parameter map and exact original forest nodes. Original authority
re-reads and binds argument bytes into its source-proof digest; missing choices,
wrong valid values and unexpected calls reject. Pairing independently re-admits
both complete original scopes, joins the current shared graph/SDK images and
rejects cross-family replay or old attempts before sealing one control receipt.
QC-02 retains all 96 primary keys and authorized exclusions in a compact full
basis, preserving existing bounds. Report admission independently recomputes
pairing/basis hashes and native parent coverage. Native confirmation is pending.

The next artifact166 increment adds an awaited pending-reclamation injection
overload without changing the original wrapper or assertions. Typed intentional
failure additionally supports delete-removed, identified by exact exception
reference, never type/message. Ordinary same-shaped callbacks fault settlement
and retain ownership with explicit `CleanupIncomplete`; their control reclaims
the pending payload before checking failed ownership. Fresh packages pass 322
selected consumers. Fourteen actual/two original controls pass; an SDK-only
cleanup assertion mutant gives each family exactly two named failures, all
others passing with matching SDK/archive images. These are local diagnostics,
not QC-03 completion. Exact `b66e6b0`/run40292115062 independently admits earlier
artifact162/metadata152 argument transport with three Linux jobs/341 native
foundations passing without skips, not the later maps/pairing/deletion work.

The following artifact168 scope adds both admitted-open quarantine races.
Awaited shared installer/removal and exact-stamp replacement preserve the
original synchronous wrappers and assertions. Replacement's sharing permits
existing readers as the original fault did; serialized fault ownership and
authority-held deletion exclusion remain intact. Initial Local `Unavailable`
is a control-setup failure, not named parity evidence. Fresh packages pass
324 selected consumers. Both actual/original pairs pass; an SDK-only final
quarantine assertion mutant gives each family two named failures with matching
runtime SDK/archive images. QC-03 remains open. Pairing run40295489832 was
canceled before jobs, not admitted; replacement deletion run40297863544 awaits
independent observation.

The next artifact172 increment retains all four validation-first missing/
truncated parameters and Local compatible-reopen assertions through awaited
typed overloads. Fresh packages pass 328 consumers. Four actual/original pairs
pass; an SDK-only incarnation assertion mutant gives four named failures per
family with matching SDK/archive images. Safe-logger replay validates all
172 witnesses/178 origins, six reopen edges, exact counts and role/image/
archive correspondence. Missing, extra or foreign validation origins reject;
Object has no borrowed durable restart. Exact `e39b2ce`/run40293145453 admits
earlier frozen argument maps on Linux: three jobs/341 native foundations pass
without skips. Pairing/newer artifact scopes remain unadmitted natively.

The artifact shared-consumer native source path now uses the same owned-command
reconstruction as metadata, not a copied passing label. It reconstructs readonly
graph/manifest/settings, every runtime proof/origin and six exact loaded/package
images, pins the original-wrapper SDK in the execution inputs and retains both
shared/hook packets with conflict rejection. All 250 witnesses/262 origins remain
required; catalog identities/counts are unchanged. Tooling454 (19 native skips)
passes. Actual native admission, original artifact pairing and QC-03 remain pending;
this source family alone issues no extraction-parity obligation.

The original artifact source path now reconstructs all three unchanged scopes
(183/12/12 witnesses), independently selecting exact per-node forest/role images
and rereading readonly original proofs. Wrapper SDK/archive correspondence and
all manifest images are required in the owned command closure. Its timing must
fit the current attempt. Scope receipts use exact scope-sized observation bounds
without changing per-case limits. Tooling455 (19 native skips) passes; native
admission and original/shared pairing remain pending, with no QC-03 pass issued.

Artifact native parameter pairing now reuses metadata's independently re-admitted
scope mechanism for all three original scopes alongside the complete shared
source. Distinct attempts/parents, exact runtime paths, current sequence/timing,
cross-source execution/origin/component instance isolation and readonly pairing
material are required before QC-03 obligations are issued. QC-03 reconstructs a
full AS-01..48 basis packet without shortening case witness inventories; actual
transfers, Local recovery and four Object exclusions remain unchanged.
Tooling458 (19 native skips) passes. Actual native admission and full feature
acceptance remain pending.

Object payload-access faults are now concrete-binding-owned, matching the
original driver boundary. Native exact-stamp selection/protection still wraps
application and transfers the same captured scope before supervisor hooks;
restoration precedes guard release. The Object provider contains no rename calls.
The unchanged prepared architecture witness gives a named pre-fix `Assert.Empty`
failure and passes after correction. Fresh fourteen-package replay passes
406 consumers; 16 actual/four original access cases and an SDK-only negative
retain exact assertion/image parity. Safe-logger replay checks 250 witnesses/
262 origins. Scoped implementation review has no actionable findings, not final
T081. Native admission remains pending.

The current artifact250 scope adds root-owned synchronous native facts mapped
to immutable opaque file IDs/lengths, including after explicit native stop.
Bound all filesystem entries before filtering; reject overflow, directories and
symlinks explicitly. This repairs the reviewed file-only enumeration gap.
Directory permission scopes reuse pending access ownership; native application
serializes directly rather than reacquiring a transfer slot inside an owned
callback. Awaited cleanup/stop overloads retain original assertions/synchronous
callers. Exact intentional injections do not forgive six same-message ordinary
callback errors; settlement remains faulted. Fresh fourteen-package replay passes
406 consumers; 24 actual controls/12 original wrappers pass. Six SDK-only mutants
give matching 2/2/1/4/1/2 named failures per family with verified loaded/archive
SDK images. Safe-logger replay checks 250 witnesses/262 origins/twelve reopen
edges. Scoped review findings are repaired; native/full QC-03 and final T081 remain open.

The preceding artifact226 scope adds Local record-write permission ownership through
the same pending access registration, capturing the native scope before release
callbacks and restoring the exact original directory mode before closure. Object
rejects this Local-only control before registration. Original failed-quarantine
assertions retain failed stop, payload/mode restoration, retry and same-lifetime
compatible initialization before owned replacement. Pending application joins
shutdown; ordinary release errors/cancellation retain exact faulted settlement.
Already delivered success survives, with no supervisor changes. Initial private
discarded-success expectations were invalid, not proven bugs. Fresh fourteen-
package replay passes 382 consumers; five actual controls/one original wrapper
pass. An SDK-only readiness mutant gives one named failure per family with matching
SDK/archive images. Safe-logger replay checks 226 witnesses/237 origins and eleven
reopen edges. Scoped review finds no actionable issues, not final T081. Native/
full qualification remains open.

The preceding artifact217 scope owns real permission/directory access faults with
opaque exact-stamp scopes. Pending registration precedes application; native
handle capture precedes release observers. Read protection persists through
physical restoration, so deletion cannot reclaim/resurrect restricted bytes.
Cleanup joins application/restoration before native shutdown; failed restoration
remains owned/retryable. Ordinary release errors are retained in faulted
settlement with explicit `CleanupIncomplete`, not converted to successful
qualification. Four rows each cover original validation, concurrent shutdown,
queued deletion and throwing release observers. Fresh fourteen-package replay
passes 373 consumers; sixteen actual/four original parity cases pass. An SDK-only
failure-code mutant causes four named failures per family with matching runtime/
archive SDK images. Safe-logger replay checks 217 witnesses/227 origins and ten
reopen edges. Reviewed guard-lifetime/handoff findings are repaired; this is not
final T081, native artifact217 admission or full QC-03/feature acceptance.

The preceding artifact201 scope also retains Local committed-decision rollback
after 105 retired histories and durable-receipt staging release. Awaited owned
reopen preserves initialization/cleanup and all original assertions/limits.
Third-record-write interruption has one owner, rejects duplicate/hold overlap
and preserves same-shaped ordinary callback failures in faulted settlement.
Object rejects this Local-only boundary explicitly; its genuine physical
deletion hold stays independent. The reviewed alias is fixed and a restored-
alias private negative fails the named Object guard. Fresh fourteen-package
replay passes 357 consumers. Four actual controls/two original wrappers pass;
each SDK-only durable assertion mutant produces one named failure per family
with matching runtime/archive SDK images. Safe-logger replay checks all
201 witnesses/211 origins and ten reopen edges. Full QC-03 remains open.

The preceding artifact197 scope preserves the Local read/reconciliation
quarantine race and six committed-detection parameters. Awaited typed overloads
retain original synchronous wrappers/assertions; public recovery rows expose
genuine selected stamps checked against exact ticket/store/identity before
existing exact-stamp fault controls run. Fresh fourteen-package replay passes
353 consumers; both seven-row families pass. SDK-only race/detection mutants
produce one/six named failures per family with matching SDK/archive images.
Safe-logger replay validates all 197 witnesses/205 origins and eight reopen
edges. Exact origin policy retains Local open/publication reopen, not Object
or Local reconciliation; missing, extra and foreign origins reject. This is
not complete QC-03 or feature acceptance.

The preceding artifact190 scope includes eighteen initial-admission parameters.
Explicit typed probes create genuinely uninitialized owned stores; `None`
preserves ordinary initialized creation. Root existence/readiness are observed
from the actual provider generation. Capability probes preserve unrelated
fields and original limits; foreign authority has a genuinely distinct scope.
Unsuccessful handoff/cancellation/disposal retain actual settlement ownership.
Fresh fourteen-package replay passes 346 consumers; both eighteen-row families
pass. SDK-only no-I/O/range assertion mutants give sixteen/two named failures
per family with matching SDK/archive images. Safe-logger replay admits all
190 witnesses/196 origins and six reopen edges, with exact counts and images.
Scoped architecture review finds no actionable issues, not final T081.

Exact `f4e53b4`/run40297863544 now independently admits artifact166 and metadata
QC-02 pairing. Three Linux jobs/343 foundations pass without skips; metadata
is 93 Passed/0 Incomplete/9 NotApplicable/0 Failed. The overall report remains
`Incomplete`, qualification false. Artifact190 and full QC-03 remain unfinished.

The separate `actual-authority-integration` diagnostic scope requires all
32 exact rows: four actual compositions times eight unchanged/common or
ownership consumers. Reduced/foreign scopes reject before launch; routing
requires the package-only Consumer and actual SQLite environment admission.
`AuthorityIntegrationTests.cs` is source-linked into that Consumer and excluded
from the ordinary SDK test assembly. Its explicit HostAdapters package edge
and updated lock graph are checked with fourteen actual Hoard image/archive
correspondences per preparation. A stable close helper fences new authority
admissions and joins genuine authority holdings, metadata lifetime/work
settlement and both actual disposals. Only the unit resource owner reclaims
after successful settlement; no binding deletion or fabricated Released.
Original common assertion bodies and wrapper disposal remain unchanged.
Fresh preparation/replay pass 267 Consumer, 311 artifact and 89+89 metadata
cases; separate empty-cache discovery/execution confirms all 32 actual rows.
Controls native run `40158951602` at `3fb2705` passed all three jobs,
215 foundations without failures/errors/skips, 95 scopes/918 observations and
every prerequisite. The next request is 216 foundations and 96 scopes/974
observations, not yet admitted or complete T033/category qualification.

Four additional exact diagnostic scopes select faulty/corrected metadata and
artifact consumers, two provider rows each. Their public methods are separate
because runtime selection is by fully qualified method, not a single theory
parameter. Reduced/foreign scopes reject before launch; metadata scopes require
actual SQLite environment admission, and every scope receives its actual family
package hashes. Faulty scopes require the exact named common SDK assertion,
`AssertionFailed`, failed witnesses and process exit one; corrected scopes
require passing witnesses, no failure and process exit zero. Setup, mutation
counter or cleanup failures cannot substitute for the named assertion.

Only `ConformanceCategoryMutations=true` source-links these tests/decorators
into the package-only Consumer. Default discovery excludes them. Both pairs use
unchanged caller/common assertion bodies, SDK/catalog bytes and actual provider
packages; unexpected successful artifact reads remain explicitly owned until
disposed before the actual session. Fresh preparation/replay each reproduce
all eight outcomes and fourteen actual Hoard image/archive matches. Tooling
passes 326 checks (309 passed/seventeen macOS-native skips), including 100 SDK
checks; opt-in formatting and frozen inventory/catalog checks pass. The next
native request is 218 foundations and 100 scopes/982 observations, not yet
admitted or completed T034/category/controller qualification. Historical
seals/locks, task and reviewer markers remain unchanged.

The runtime launcher's independent package-family guard permits only an exact
full-family or same-family paired inventory, not an arbitrary prefix/subset.
Its additional regression initially rejects all four valid paired scopes with
`WitnessMissing`; after repair, generated safe logger settings and method
filters contain the actual family package hashes. Reduced, duplicate and
cross-family rows reject before launch. A controlled command-boundary stop in
this regression is not a native execution receipt. All 326 tooling checks pass;
earlier mutation-head results are not admitted and T034 remains unfinished.

Cursor native run `40159593512` at `5c7522f` passed all three jobs,
215 foundations without failures/errors/skips and 95 scopes/942 exact
discoveries/executions, including every prerequisite. It predates authority/
mutation increments and does not establish complete category qualification.

Category input sources can explicitly select `catalogBindingId` for one of the
four known frozen slots. Independent parent mapping checks category, original
fixture declaration ID and provider package before projecting only the outer
binding identity. Raw descriptor bytes/hash, capabilities and archive
attribution are unchanged; duplicate original declaration IDs reject even under
different projected/unprojected IDs or JSON serialization. Full capture/recapture
binds the selected assignment.
Actual bounded observation/replay each verify four factory/reopen cases,
eight genuine origins and 56 role/image/archive correspondences, without
promoting the selected subset or input wiring to complete profile execution.
Tooling passes 327 checks (310 passed/seventeen macOS-native skips).
Authority run `40160483040` at `eeaa6bf` passed all three jobs,
216 foundations without failures/errors/skips and 96 scopes/974 exact
observations with every prerequisite. It predates mutation/slot input wiring;
the next request is 219 foundations and 100 scopes/982 observations, not yet
admitted or full category/controller qualification.

The category batch import model requires each binding's complete frozen
runtime union and both required package options. Primary runtime context is
the lexicographically first mapped case; UUIDs/hashes are reused only for
catalog-owned obligations without rewriting proofs. Failed attempts persist
through retries and identities/components remain consistent across batches.
Optional prelaunch partitions must be nonempty/disjoint and cover that exact
union. Their copied primary-case maps and independently allocated child attempt
UUIDs are immutable. `finish_parts` admits every scope atomically against its
predeclared attempt/sequence and manifest, rejecting missing/extra scopes,
cross-scope execution/origin reuse and aggregate proof-budget overflow.
Assertion failures retain actual proofs and affect only mapped obligations;
invalid batches append a failed/incomplete attempt without accepting earlier
valid scopes. Single-scope imports follow the same checks.
All original QC rows remain required; missing controller controls stay
incomplete, exclusions invent no execution, and actual profile/evaluator
dispatch remains guarded. Eleven synthetic transport regressions exercise this
model, including an admitted-origin diagnostic fixture and cross-binding
execution-ID replay rejected without changing accepted witnesses/proofs.
The immutable primary-case map is shared by prelaunch manifest selection and
import. These fixtures do not establish actual original-wrapper provenance or
full category execution.

The joint category lifecycle can instead predeclare the complete profile-wide
binding/identity union. This supports genuine mixed-provider parameter families
in one runtime scope without filtering foreign rows or rewriting source
manifests, completion records or proofs into per-binding batches afterward.
Its copied scope maps select exact bindings/primary cases and independent child
attempt UUIDs. A repeated neutral identity in another binding requires another
scope; a duplicate identity inside one scope is ambiguous and rejects.
Both options commit atomically after every scope passes the same exact runtime,
provenance/replay and aggregate-budget admission used by binding-local imports.
Partial/foreign plans and mixing lifecycle APIs reject. Joint interruption or
invalid transport appends attempts for both options without accepting earlier
valid scopes; a fresh retry cannot erase either failure. Actual assertion
failures retain their proofs and affect only the matching binding/cases.
Four synthetic regressions exercise joint selection/immutability, ambiguous
plans, missing/stale later scopes and retries, and cross-binding failure
attribution. A fifth checks the independently selected six scopes/profile
against exact frozen binding inventories and complete method families:
134 metadata/227 artifact binding/identity pairs. Actual joint profile execution and source/controller qualification
remain unwired; these fixtures are not behavioral acceptance.

Run `40161613939 @abfa812` failed mutation diagnostics because the real logger
did not recognize bounded `Assert.IsType()` failures. The repair adds only that
prefix, retaining exact SDK-frame checks and safe projection. All 46 logger
tests pass; actual local observation/replay each reproduce four named failures
and four corrected passes using unchanged Consumer/SDK images. Tooling passes
332 checks (315 passed/seventeen macOS-native skips). That failed run and
confirmed canceled `40162771846 @c1f79b2` are not admitted. Replacement run
`40164176338` at exact `2ecda7f` passed all three jobs, 223 foundations without
failures/errors/skips and 100 scopes/982 exact discoveries/executions with all
prerequisites and mutation scopes. It admits the repaired diagnostic run, not
full category qualification or later `90fd088`. The original-wrapper
proof-contract decision is now resolved through a separate bounded original
observation channel and private execution-proof revision 2. Independent exact
witness policy selects actual original-owner/interface or session-free contract
attribution; typed SDK consumers and unclassified witnesses retain strict typed
origins. No owner is replaced and no extra SDK session supplies the proof.
Original MP-01/AS-01/value-test local observations and independent locked replay
pass six executions/26 image correspondences using minimal diagnostic inputs,
not full category RunInputs. All original, child/reopen and controller paths
must still be wired before complete profiles can qualify.
Six known inspection facts and sixteen controller producer facts now have an
explicit separate non-session policy. An unrelated valid SDK session does not
qualify them. Missing independent inspection/controller admission fails closed,
and selecting a `none` context cannot skip known original evidence requirements.
Diagnostic packet imports remain separate from qualification.
Five additional native scopes now request original observations against a
separate full captured/recomputed input document with frozen binding slots.
They select exact primary cases using the same catalog helper as category
history, require one original proof per execution and reject unrelated typed
origins. The eight executions include both frozen artifact value witnesses,
not only the auxiliary identity-bound test. Local actual observation and
independent locked replay pass all eight with 28 image correspondences, but
remain minimal-input diagnostics. This new full-input native path still needs
an exact-head receipt: it requires 105 scopes/990 observations and all existing
recovery/transfer/containment/replay prerequisites, not complete qualification.
The following metadata expansion observes original MP-02/03/13/23..27/31 with
their actual common-assertion authority facades, through one non-owning source
helper. Actual observation and independent fresh-cache replay pass 26
executions/118 image correspondences using minimal inputs. This changes the
native requirement to 105 scopes/1,008 observations while retaining all
prerequisites; that expanded path requires its own exact-head receipt.
The subsequent artifact publication expansion covers all twelve frozen
parameters through the actual original driver's non-owning observer, preserving
assertions, private lifetime, barriers and existing disposal. Local observation
and independent locked replay pass 36 executions/188 image correspondences
using minimal inputs. Its native requirement is 105 scopes/1,018 observations,
still pending. Earlier `40166560899 @8aaa36d` passed all three jobs,
227 native foundations and 100 scopes/982 observations with every prerequisite;
it is admitted diagnostic evidence, not execution of the later full-input scopes.
Role-image selection subsequently becomes exact-witness-specific within each
binding and is deeply frozen by both histories. Fifty-five single-owner metadata
identities per provider observe the genuine authority shape already used, not
an invented facade, including exact corruption/continuation parameters and
both direct-construction admission witnesses. Actual minimal-input observation/
replay pass 126 executions/638 image correspondences; the expanded native
requirement is 230 foundations and 105 scopes/1,108 observations, pending.
Earlier full-input run `40167209164 @0005638` passed all three jobs,
229 foundations and 105 scopes/990 observations with distinct original/typed
input digests and every prerequisite; its earlier eight-original diagnostic
does not admit these expanded sources. Existing one-root admission remains
strict; multi-owner/reopen scopes are not silently promoted into this policy.
The following increment deliberately adds seven independently selected
multi-owner/reopen forests. Exact node counts, current-execution parentage and
distinct owner/store identities replace the one-root requirement only for those
exact witnesses. Source observation sequences preserve genuine aliases across
independent roots without fabricated reopen edges; schema nodes observe actual
adapters and their underlying fixture authorities. Failed observer capture
after reopen cleans up the newly transferred fixture before propagating failure.
Local observation/replay pass 140 executions, 162 records and 818 image
correspondences. Native admission requires 231 foundations and 105 scopes/1,123
observations, pending. Earlier `40168790991 @3f1409a` passed all three jobs,
230 foundations and 105 scopes/1,082 observations with every prerequisite,
not the later forest increment or complete profiles.
Both actual configured metadata module owners now form a two-root host forest;
their genuine module type/image is checked in local observation/replay.
Thirty-eight additional artifact parameters observe their original driver and
interfaces without changing assertions, factories, barriers or cleanup ownership.
Coverage is 63 operational metadata identities per provider and 181 artifact
witnesses, including real metadata compositions and configured owners. Original bool argument
names/values remain intact, and Local multi-parameter rows cannot fall back to
Object. Nine genuine Local fresh-store children have exact per-node images:
original driver owner versus actual reopened store owner/interfaces/controls.
Observers record factory-returned instances without owning cleanup. Same-object
reinitialization is not a new owner, and early-return reconciliation/Object rows
have no invented child. Both histories freeze all selected nodes before execution;
flat maps cannot replace these different owner images.
Rejected source-created stores use their real provider-owned owner images;
decorated initialization records the exact passed authority. Fixed facts retain
their original parameter identities and independently checked binding ownership.
Actual composed sessions/modules own real interfaces and exact constructor
controls. Successful configured-host parameters retain two independent roots,
not invented reopens; SQLite-bearing integration rows require actual environment
admission. Only exact Local reopen identities receive heterogeneous child images.
Eight value/qualification contracts per binding carry actual loaded Abstractions
type proofs through package-only partial observers. Ordinary predecessor tests
retain no SDK dependency, and primary-case selection excludes non-applicable
durability rows.
Two further native scopes select the four provider-neutral authority/bridge
facts in explicit Local/Object contexts. These and the two rejected-module
parameters carry owner-only observations, never invented sessions/interfaces or
parent edges. The copied-handle fact observes two independent genuine authorities
with non-owning reference history. Existing full-session policies remain strict.
Local observation/replay pass 333 executions, 370 records and
2,122 image correspondences. The external-wrapper scope now separately checks
sixteen source producer packets after exact safe runtime ingestion. Its hash-only
parent receipt binds actual runtime execution/proof IDs, state/producer hashes,
attempt/group/current inputs and the same-run parent transfer measurements.
It creates no provider session, component origin, child-start attestation or
qualifying category result.
Native admission requires 236 foundations and
107 scopes/1,317 observations, pending. Controller and remaining artifact
lifetime attribution and qualifying backends remain unfinished.

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

Current partial T064 admission requires a sibling
`<Project>.conformance.json`, schemaVersion1, with exact fields `project`,
`factoryType`, `adapterPackage`, `declaration`, `components` and `sourceFiles`.
The project is source-root-relative; package/image records contain `packageId`,
`version` and `assemblyName`. Every category role must be present, with factory
ownership matching the adapter package. The prepack binding declaration has no
fabricated archive hash; actual capture still requires the actual package hash.
The project and registration must appear in the unique bounded source inventory.
Admission rejects unknown fields, exclusions, missing hooks, unsafe paths and
symlinks, and fingerprints registration plus captured declared source hashes.
An owned declared-source staging helper rechecks the pinned admission
fingerprint before/after copying read-only files, rejects copy races and
overlapping author/output roots, and leaves original source bytes untouched.
This is not complete MSBuild closure, an owned build, compiled type
validation or executable contributor registration. The custom dispatch guard
still returns `EvidenceIncomplete`; T064 remains open.
Synthetic configuration generation/verification can additionally bind exact
local package IDs outside `Hoard.*`. Additional IDs are bounded, case-folded,
unique and literal, never caller-selected glob patterns. The original default
configuration bytes remain unchanged; a widened or unselected mapping rejects.
Custom build/restore integration remains unfinished.
The typed source helper checks selected actual local adapter/provider IDs and
versions and the adapter's declared `lib/net10.0/<assemblyName>.dll`, then emits
direct construction of `factoryType` with the actual provider archive hash.
The type must expose a public constructor accepting that hash string and
implement the category's binding interface; no reflection/directory loading
is used. A managed metadata-only component verifies compilation/invocation and
intended wrong-category/wrong-constructor compiler rejection. This does not yet
wire or validate arbitrary supplied projects through the public runner.
The generated factory validates the returned declaration against registration:
category, binding ID, provider ID/version, actual provider archive hash and exact
capability/fault sets, independent of set order. Captured role inputs select the
exact declared net10.0 member and consumer image bytes from each actual package
record. Roles may have different owners, and assembly names need not equal
package IDs. Missing/mismatched owners or images, duplicate case-folded package
IDs and conflicting runtime asset owners reject rather than falling back to a
built-in map. This input selection is not proof that the eventual session
actually returns those component instances.
Non-qualifying local lock preparation may also receive an explicit frozen
captured-package policy for registered IDs/versions. Only selected content
hashes are rebound after actual archive SHA-256/SHA-512 comparison; requested/
resolved versions, dependency edges and unselected nodes are unchanged. Replay
verification must receive the same policy and reject changed archive bytes or
graphs. This does not resolve dependencies or change default built-in policy.
Evaluated item admission is a separate non-qualifying input check: require the
selected declared project and toolchain inputs, reject undeclared source paths,
duplicate/malformed rows and unknown metadata, recheck all declared source bytes
and retain only relative source/toolchain hashes. Derived private MSBuild
metadata paths are not retained. Evaluation is not complete dynamic/generated
compiler input capture or evidence that arbitrary MSBuild projects are safe.
Compiler-source admission is another non-qualifying input check. Require closed
per-project receipts, successful build/compiler outcomes and the selected
declared binding project. Reject duplicate or undeclared projects. Match every
observed `source/` hash to frozen author inputs and independently rehash every
`generated/` input beneath a disjoint root; recheck all frozen author inputs,
including unqueried ones. Reject changed/conflicting hashes, links, unknown
namespaces/fields and unsafe paths. These receipts do not by themselves prove
complete compiler/reference/analyzer/package closure or compiled/loaded origin.
Compiled-document receipt admission must bind the successful compiler project,
exact selected DLL/PDB paths and current output hashes. Every document hash must
match an observed compiler source; unknown or mismatched documents reject.
Unknown fields and unsafe paths/links reject. A receipt reader alone does not
parse PE/PDB bytes or prove producer origin, full document coverage or complete
compiler closure. The independent producer must verify actual PE/portable-PDB
identity and checksum before such a receipt can contribute to runtime evidence.
Build-file receipt admission separately checks observed imports and known
physical compiler-input parameters. Require successful declared projects with
source/reference inputs and no reported build/observer errors; a success flag
cannot erase an observer failure. Resolve only disjoint author/generated/
toolchain/package namespaces, rehash every frozen author input and every selected
file, and require selected package files to match a frozen package-file policy.
Reject unknown fields/parameters/namespaces, undeclared inputs, conflicting
hashes, overlapping roots, links and changes. Bound aggregate reads across all
roots. A supplied hash policy alone does not establish archive/member/cache
ownership, complete compiler-option/item-metadata closure or native provenance.
For registered packages with captured identities, a selected-member file policy
may be derived only after actual archive identity and SHA-256/SHA-512 revalidation.
Hash exact selected members without extraction; reject missing/unsafe members,
CRC errors, changed archives, unknown owners/versions, duplicate/ambiguous cache
prefixes and aggregate read-limit violations. Cache prefixes must come from an
independently checked asset graph; this helper does not resolve or validate that
graph, handle all non-runtime package identities or establish native origin.
Separate bounded archive identity now permits packages without runtime images,
using the same archive/metadata capture. It is not a runtime PackageIdentity:
runtime admission must still reject an archive without runtime images.
Selected-member policies may use either closed captured identity shape and must
revalidate the corresponding actual archive. Neither shape resolves the asset
graph, changes locked dependencies or establishes native producer origin.
Compiler-parameter admission must additionally bind one command hash and exact
item-metadata parameter/file keys to every successful file-compilation row.
Reject missing, duplicate or foreign rows/keys, malformed hashes, unknown fields
and oversize receipts. Bind the admitted file-row digest and retain hashes only,
not raw commands/metadata/private paths. Hash-only receipts do not independently
interpret compiler arguments or establish native producer origin.

The implemented metadata consumer bridge compiles a generated typed factory
alongside the package-only consumer and references the exact registered adapter
version. Its shared data attribute expands every common row with the actual
registered binding ID; default builds still expand Memory and SQLite. No
provider-supplied case list, built-in alias or inherited built-in exclusion may
select or shorten the contributor dataset. Category-inconsistent or incomplete
contributor build properties must fail before compilation/package collection.
This bridge alone does not establish full applicable catalog coverage, owned
supplied-project build/pack or native provenance. Artifact-contributor support
and public custom dispatch are not yet implemented.
Build/pack archive selection accepts an explicit registered version rather than
assuming0.1.0. Validate package identity/version before starting commands and
canonicalize only that exact produced archive; a different version is not a
fallback. Existing fixture calls retain the0.1.0 default.
The internal supplied-project build recipe allocates disjoint owned
intermediate/output/extension and prepared-lock paths for every declared project,
outside the read-only staged source tree. Require exact full source inventory;
recheck source bytes/read-only modes, configuration and generated controls even
after command failure. The current recipe uses CustomAfterDirectoryBuildProps
and rejects semicolon configuration/feed paths. It does not yet resolve author
hook conflicts or establish complete evaluated compiler/asset/native provenance,
and is not connected to public contributor dispatch.
Finite restore-graph admission currently supports exactly net10.0 without RID
targets. Bind the prepared-lock hash, exact package/dependency-endpoint sets,
resolved versions and logical content hashes, one expected cache and declared
project paths. Independently rehash cached archive bytes and check package
metadata. Require a closed per-package receipt linking raw archive SHA-256 and
NuGet logical content SHA-512; signed-package logical hashes are not raw archive
hashes. The actual producer uses NuGet's own API but remains private.
This is cross-artifact admission, not signature trust, dependency-range
interpretation, native producer origin or complete evaluated input provenance.

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
