# F-07 Evidence, Aggregation and CI Contract

**Status**: Planned schema/evaluator/workflow contract, not an emitted report.
See [model](../data-model.md), [matrix](matrix.md) and [harness](harness.md).

## Input Manifest

Schema `1` requires `runId`, `invocationGroupId`, `profileId`, `mode`,
`catalogRevision`, `catalogSha256`, `sdkSha256`, `sourceRevision`,
`sourceManifestSha256`, package identities/content hashes, lock hashes,
configuration/capability hashes, environment manifest/hash, finite budgets and
exact sanitized invocation. Source manifest lists sorted relative paths and
byte hashes for all scoped sources, scripts, tests, workflow, build/package
settings, locks and catalogs. Ignored build/runtime files cannot enter the
source fingerprint. Dirty local tracked input bytes are included and explicitly
labelled; a clean CI source revision is required.

At admission and after execution, independently recompute these inputs.
Capabilities cannot change after selecting applicability. Package attribution
includes package ID/version, nupkg SHA-256, NuGet content hash, source mapping,
and actual resolved/runtime loaded assemblies. Equal version labels with
different bytes are different tested inputs. No arbitrary commit label, empty
hash map or hash of a filename counts as source/content proof.

An explicit capture-time `catalogBindingId` assignment connects each known
fixture declaration to its frozen category slot without changing the
declaration. Independent parent mapping checks category, original declaration
ID and exact provider package before projecting only `ProviderBinding.bindingId`.
The original raw descriptor hash, capabilities, adapter and package attribution
remain bound; unknown/cross-slot assignments and duplicate original declaration
IDs reject, including differently serialized declarations.
Assignment removal/change must alter recaptured inputs. This adds no descriptor
or report field and grants no applicability, exclusion or passing-result claim.
Actual factory/reopen observations continue to join the original complete
descriptor hash, not a rewritten declaration or copied display label.

Profile reports in one baseline share source/catalog/configuration-policy
inputs and invocation group, not necessarily package or environment hashes:
different providers and CI runners have different exact bytes/environments.
Each profile's manifest must match its predeclared input assignments. The
aggregate records all environments and claims no untested cross-product.

## Observed Results

Each expected key has exactly one final outcome:

| Outcome | Meaning | Qualification effect |
| --- | --- | --- |
| `Passed` | All named expected observations/subproofs completed | Eligible only with valid attributable evidence |
| `Failed` | Contract assertion or evidence rule violated | Blocks entire requested scope |
| `NotApplicable` | Frozen catalog authorizes named exclusion | Allowed only for that case/binding/class; confers no excluded claim |
| `Incomplete` | Unobserved, interrupted, infrastructure failure, unknown settlement | Blocks entire requested scope |

No `Skipped`, `Unknown` or success default is accepted. Every runtime witness
contains the exact fully qualified case/parameter identity, execution ID,
provider binding/package, start/end monotonic duration, result and immutable
proof digest. The evaluator checks required witness sets, individual outcomes,
expected invocation/assembly and test discovery inventory. A TRX total or
copied case name/flag is not enough. Missing mandatory tests cannot become a
smaller expected inventory.

QC-12 explicitly requires all 32 fully parameterized
`AuthorityIntegrationTests.Actual_compositions_preserve_shared_authority`
witnesses in the independent and embedded SDK catalogs, in addition to its
seven controls. The SDK diagnostic scenario uses that exact selection and
rejects missing pairings, consumers or individual rows before execution.
These cross-binding quality witnesses are not ordinary single-provider runtime
scopes. Qualification has a separate fresh `original-integration` scope in the
package-only Consumer. Its three loaded-contract observations independently
identify the actual metadata store, artifact store and composition images for
each row; they do not assert object identity by image alone. Independent native
source admission reconstructs all 32 rows, the exact six-image manifest and
provider package correspondence. It checks the executor-held command record,
owner, inputs, settings/encoded original context, fixed argv/cwd, complete
immutable input map, successful settled exit and command/witness bounds before
admitting one parent shared by the complete set. Rehashing a replaced record or
receipt is not authority. QC-12 requires all current-attempt rows and that parent;
missing source parents or rows cannot qualify, and prior execution IDs cannot be
reused in a retry. Local execution and modeled rejection checks do not establish
fresh Linux source admission by themselves. Exact `9a5ebdb`/run40243784950's
unchanged-head retry subsequently admits this complete scope and one native
parent; artifact reports remain `Incomplete`, not full profile qualification.

QC-04 has a separate qualification-only `mutation-repair` scope per category,
with both corrected binding identities fixed in the independent/SDK catalogs.
Each scope first executes fresh faulty rows against the same Consumer, SDK,
provider packages, six images and immutable inputs. Independent native admission
re-ingests the original negative transport and reconstructs its entire manifest,
requiring both exact named assertion frames, Failed/Assertion status and exit
one. Setup failures cannot substitute. Its original executor-held command,
readonly receipt, settings, argv/cwd, full input map, owner and ordered settled
command/witness bounds must match the same current pair. Rehashed file records
do not replace held authority. The corrected successful source parent retains
the negative packets; they are not failed public report witnesses. QC-04
requires both current corrected rows and one common source parent, never
missing rows/parents or borrowed previous-attempt executions. Implementation
and modeled rejection checks do not claim fresh Linux pair admission.
The source supervisor seals inspected runtime witnesses, completion and proof
files read-only after owned-child settlement, rechecking exact captured bytes
before sealing. Live children or changed bytes reject. Independent source
reconstruction still requires readonly originals; writable logger output cannot
be admitted or silently copied into replacement authority.

The metadata qualification-input batch also executes a distinct fresh F-07
package-only common Consumer as private source transport. Its immutable
152-row selection, both binding identities and exact origin counts are not
caller-provided. Session contexts stay `full-metadata-binding`, not QC-02.
Independent admission reconstructs the complete six-image/package manifest
and original readonly runtime transport with independent typed role assignments,
descriptor/image/instance/reopen correspondence and exact per-row origin counts.
It joins the original held command and readonly native record to the current
owner, input closure, fixed settings/argv/cwd, successful exit and settled
command/witness bounds; a rehashed replacement record cannot substitute.
The Consumer and frozen metadata wrappers must use identical SDK image bytes
from the same admitted SDK package, and the wrapper SDK must be pinned in
the original native command input map. Matching package labels alone cannot
substitute for this byte-level correspondence.
The retained graph is separate from the old MP-47 marker Consumer. These 152
rows are private source evidence, not public case witnesses: the 128-witness
bound is unchanged. QC-02 remains incomplete pending full extraction/parity
and composition, and local modeled rejection checks do not claim native
admission of this new control.

The twenty added corruption convergence rows preserve the original 132
identities and extend the required origin count to 172. Their typed controls
must retain exact-target ownership through restoration, reject closure/late
admission, protect an intervening committed image on CAS conflict, restore
canceled applications and explicitly recover failed restoration. Two actual
reopen rows add parent edges; neither a successful local package replay nor a
shared-assertion mutation pair substitutes for fresh native source admission.

Within the existing metadata `admission` and artifact `PublicationBoundary`
Consumer rows, every mandatory logical hook omission must reject through
observed-session opening before factory dispatch or resource allocation.
Metadata includes both ordinary and legacy opening. The unchanged actual
binding then executes the existing common assertion in the same row and emits
its original typed origin. Probe declarations copy actual package identity and
capabilities but cannot choose expected faults. Missing bindings must reject
before dereference; repeating each missing hook with a claimed logical
`MP-21`/`AS-15` exclusion must still reject before factory dispatch. These checks
retain the 132/24-row identities and origin counts; they do not establish QC-05
source composition or substitute for full extraction/parity/native admission.
Dedicated two-provider hook-admission methods additionally use `QC-05`
contexts and the same assertion bodies. Their diagnostic selections pin all
six actual Consumer/SDK/binding/provider images and require one typed origin
per row. Qualification-input batches execute each complete family once as a
predeclared `hook-admission` scope and retain original native hook controls.
Independent reconstruction requires readonly
original transport/proofs, exact origins, all six images and the original held
command, settings/argv/cwd and settled bounds. Both histories retain the
original packets under existing proof limits. Identical source packets shared
by independent controls may merge; overlapping paths with different bytes and
duplicate control names reject.

Public QC-05 composition requires both exact original provider executions and
their one original native graph parent, plus all four independently reconstructed
hook/binding/logical-exclusion/durability obligation controls. Missing
rows/parents/controls remain `Incomplete`; origin, attempt and window mismatch
reject. Original execution IDs and runtime proof hashes are preserved. The
producer uses the predeclared UUID and actual execution bounds, never a
permissive zero start. Current create-new hook graphs support one attempt and
explicitly reject subsequent attempts rather than reuse earlier sources.
This wiring has modeled validation but awaits exact-head Linux admission;
complete category qualification remains unfinished.

The packaged admission Consumer additionally owns the complete 48-case
binding sets and fixed durability policy: only memory MP-36/38..45 and
ObjectSemantics AS-41..44 may carry their exact frozen exclusion rules.
All other category/QC entries remain unexcluded. Provider capabilities
cannot choose expected exclusions or reclassify a durable provider.
Three SDK-catalog-only mutations reject at the named Consumer catalog
assertion after an observed intended-red replay; the unchanged full 160-row
Consumer still passes. This local diagnostic evidence does not itself admit
a native source parent or complete public QC-05.

The implemented category batch history derives each binding's entire frozen
runtime union from the independent catalog and requires both category package
options. The primary execution context for a shared runtime witness is its
lexicographically first mapped case. Projection retains the original execution
UUID/proof hash across all explicitly mapped obligations; no transport or proof
is relabeled. Results cannot omit either binding or any QC/control key.

The package-only full artifact binding diagnostic scope additionally selects
the complete two-provider publication consumer family: empty/absence,
unknown-length/real-EOF, all expectations, unsupported checksum/range and
verified duplicates. Ten actual-binding rows extend the preserved 24 original
rows to 34; every publication row requires one actual typed origin. All six
Consumer/SDK/provider/adapter images are pinned, and missing SDK or any selected
consumer family rejects. A local shared-assertion mutation fails both
corresponding complete actual-binding and frozen-wrapper families at the same
named assertion, with identical SDK bytes and unchanged Consumer/wrapper
sources. This is publication-family parity, not a native QC-03 source parent
or full category qualification.

A second complete ten-row actual-binding family covers destination failure,
exact acknowledged retries, conflicting staged length, deletion/recreation
and held-reader exclusion. The full diagnostic scope is now 44 rows,
preserving all original identities, one typed origin per added row and all six
image pins. Missing any new family rejects. Corresponding complete local
actual-binding/frozen-wrapper parity includes a same-named conflicting-stamp
shared-assertion mutation with unchanged Consumer/wrapper sources and identical
SDK bytes within each trial. This remains local assertion parity, not a native
QC-03 parent or complete artifact extraction.

The scope now includes eight boundary consumers and two unexpected-observer
ownership controls, totaling 54 rows. Publication selection uses an explicit
typed acknowledgment-loss registration; an ordinary same-message exception at
that boundary must still fault settlement. Local complete boundary-family
parity retains identical SDK bytes and a paired concurrent-receipt assertion
mutation. It does not supply missing metadata/artifact extraction controls.

Eight payload/progress rows extend the complete artifact selection to 62.
They preserve every earlier identity/image requirement. Local bitflip/truncated
read rows require a genuine compatible-reopen child origin in addition to
their parent; Object rows have no durable-reopen claim. Exact payload controls
must reject stale stamps after actual deletion/recreation and preserve
independent public content/receipts. Matching local SDK-only assertion
negatives and original async-reopen denial negatives remain diagnostic parity,
not native QC-03 source admission or complete category execution.
Payload-control deletion races additionally require actual authority queue
observation while selection/I/O is held, completed reclamation after control
settlement and rejection of subsequent retired-stamp replacement. A delay or
sequential stale-stamp check alone is not this exclusion proof.
The subsequent recovery/evidence/expiry and ownership extension preserves those
62 identities and adds thirty required rows, for 92 total. Each requires one
actual origin; every canceled-descriptor shape must be present on both
providers. Complete local actual/frozen-wrapper assertion parity preserves
identical SDK bytes and original setup, but is not complete/native QC-03
evidence or a replacement for inherited recovery/transfer sources.

The budget/failure/reference/history extension retains all 92 identities and
adds seventeen, for 109 total. Every new row requires one actual origin;
the inherited reclaimed-incarnation row remains Local-only. Complete local
actual/frozen-wrapper parity uses identical SDK bytes and unchanged consumers;
named SDK capacity assertion negatives do not substitute for native admission,
faulty-provider qualification or the remaining inherited source obligations.

Twenty handoff/progress/rollback rows retain those identities and extend the
selection to 129, with one actual origin per added row. Awaited installers
and independent monotonic clock observations do not change frozen identities.
Complete local wrapper parity/assertion negatives remain distinct from native
source admission and complete QC-03.

Twelve admitted-history/queue/shutdown and reconciliation/cleanup rows extend
the artifact selection to 141 without removing an earlier identity. Each
requires one actual origin and real owned settlement. Recovery overloads await
installation/removal at the original assertion's requested point; typed
acknowledgment-loss injection does not forgive arbitrary observer exceptions.
Complete twelve-row actual/frozen-wrapper parity and three shared-assertion
negative controls remain local diagnostics, not complete QC-03. Strict native
run40271691109 at `831b00c` admits the earlier artifact129/metadata152 sources
only; its metadata report remains explicitly `Incomplete`, qualification false.

Qualification-input original metadata scopes no longer use ordinary runtime
ingestion: independent source admission reconstructs all 63 witnesses per
provider and their exact role/creation/reopen forests, checks sealed runtime
proof/witness/completion bytes and pins the SDK/provider/host/wrapper images.
Source parents bind the original argv, cwd, complete held input closure, provider
and original-context settings, execution receipt and current attempt. Missing,
foreign, unsealed or borrowed sources reject. Complete local 152/63/63 parity
and three SDK-only negative controls do not themselves grant QC-02; actual
Linux run40279501756 at exact `74cf619` now admits both original metadata
parents: all three jobs and 337 native foundations/no skips, ten metadata
parents, qualification false. Earlier `bc85094`/run40276791513 independently
admits artifact141/metadata152. Sixteen individual local parameter mutations
give exact 2/1/1 named failures across complete 152/63/63 families, all other
rows passing, but are not admitted native exact-parameter controls. Complete
extraction-quality composition remains outstanding.

Eleven history-candidate observations extend the artifact scope to 152:
seven original bounds parameters, both resume cases and two ordinary-observer
failure controls. Owned one-shot injection follows observation; an ordinary
same-shaped exception still faults settlement and does not count as injected.
Every row requires its actual origin. Fresh-package replay passes 308 selected
Consumer rows without skips. Complete 304-row actual/nine-row frozen parity
passes; SDK-only bounds/resume mutations give exactly seven/two named failures
in both families, all remaining rows passing, with exact SDK/archive image
correspondence. The new scope awaits exact-head native admission.

Ten receipt/read-opening/reconciliation rows extend the artifact scope to 162.
Private exact-exception injection is restricted to the two supported callback
points; same-shaped ordinary callback failures still fault owned settlement.
Awaited overloads preserve the six original observations and their receipt/
readback assertions. Fresh packages pass 318 selected consumers; complete
314-row actual/six-row frozen parity passes, and three SDK-only assertion
mutants each give two named failures per family with all other rows passing
and exact SDK/archive image correspondence. These remain local diagnostics,
not independent native admission or complete extraction-quality composition.

Exact `d30271d`/run40286734253 subsequently admits artifact162/metadata152 and
ten metadata source parents on Linux, with all three jobs and 337 native
foundations passing without skips. It does not admit the later argument
transport.

Runtime proof schema3 adds a nonempty `metadataArguments` array alongside
`sessionOrigins` and `originalObservations`; schema1/2 retain their exact
existing shapes. `hoard-metadata-argument-v1` packets contain only run/case,
unique call/source/component UUIDs, source kind, component role and closed
argument kind/value fields. The four SDK assertions capture actual arguments,
not caller-provided receipts. Late writers drain pending calls once. Early
original-schema writers use an explicit disposable scope: one owner per
component/role, rollback on overlap, and joined output before detachment.
Scope closure and object reuse cannot credit the same call to another source.
C# and Python independently require current source/role identity, bounded
values, exact fields and replay-free calls, including cross-scope history.
Argument admission uses the declared metadata category, not reference binding names.
Existing 128-packet and 64-KiB proof bounds are unchanged. Schema3 transport
does not itself qualify the full sixteen-choice extraction map. Independent
source authorities additionally enforce the frozen per-witness map, including
empty maps and exact original lease/layout forest nodes. Original authority
re-reads arguments from readonly proofs and includes validated arguments in its
source-proof digest. Coherently rehashed missing/wrong/unexpected argument facts
reject. Pairing re-admits both complete original scopes, joins the current
shared graph and admitted SDK images, rejects replay/old attempts, then seals
one readonly receipt before issuing the four QC-02 controls. QC-02 retains the
complete MP-01..48 basis for both bindings and authorized exclusions in a compact
packet, not a truncated witness list. Report admission independently recomputes
pairing and basis hashes and checks original native parent coverage. Native
confirmation of the new composition remains pending.

The subsequent artifact166 scope adds both pending-reclamation consumers and
same-shaped ordinary delete-removed callback controls. Only the exact injected
exception is intentional; ordinary errors fault actual settlement and retain
cleanup ownership with `CleanupIncomplete`. Fresh fourteen-package replay
passes 322 consumers; fourteen actual/two original controls pass. An SDK-only
cleanup assertion mutant gives each family exactly two named failures, all
others passing with matching runtime SDK/archive images. No native or complete
QC-03 claim follows from these local receipts. Exact `b66e6b0`/run40292115062
independently admits the earlier artifact162/metadata152 argument transport:
three Linux jobs/341 native foundations pass without skips. The later frozen
maps, QC-02 pairing and deletion changes remain unadmitted natively.

Before launch, the complete map can be partitioned into copied immutable,
nonempty disjoint scopes with independent child attempt UUIDs. Admission is
atomic across exactly those scopes and preserves their actual proof bytes,
primary cases and attempt sequences. Missing/changed scopes or cross-scope
execution/session/observation replay reject without accepting earlier scopes.
Assertion failures retain actual proofs and affect only mapped obligations;
retry history and aggregate proof bounds remain unchanged.
Append-only failures survive retries, excluded cases have no invented
executions, and unobserved controller controls stay incomplete. This state
model does not yet wire actual profile runners or independent evaluation.
Manifest builders can obtain the same immutable primary-case map used by
import. A synthetic diagnostic batch with admitted origins followed by a structurally valid
cross-binding execution-ID replay confirms rejection without changing accepted
witnesses/proofs. Partitioned model fixtures additionally check immutable plans,
atomic failure/retry, cross-scope provenance and assertion attribution; none is
actual provider qualification or wrapper provenance.

Original-wrapper proof requirements are now explicitly selected by frozen
runtime identity, not solely the binding dimension. The initial closed policy
requires non-owning actual-owner/interface observations for original MP-01 and
AS-01 wrappers, and relevant loaded-contract attribution for the session-free
artifact identity-bound test. Typed SDK consumers and unclassified witnesses
retain complete typed-session requirements. No extra SDK session can substitute
for an original observation. This test-evidence clarification changes no
production provider contract or mandatory outcome.
The separate closed non-session policy identifies all six frozen inspection
witnesses and sixteen crash/retention/transfer producer identities. Valid
ordinary provider sessions cannot substitute for their independent source
proofs. The default transport API fails closed for these witnesses,
including when the execution selects `none` rather than a provider binding.
Inspection qualification now has a separate concrete native-source context that
independently corroborates frozen complete scopes against actual executor-held
command/input snapshots, source packets and the complete source-parent graph.
Caller flags, unrelated sessions and current files alone cannot grant admission.
Controller-source qualification remains unimplemented and closed.
Known original observation requirements likewise cannot be skipped through
that context. Diagnostic producer receipts and structural model fixtures never
qualify those source witnesses.

The original six architecture facts now have an optional private
`HOARD_INSPECTION_CONTEXT` source-capture hook, without an SDK dependency.
Its closed schema-1 context selects exact run/attempt/current-input identity,
existing output directory and at most six case maps of canonical absolute
file paths to expected content hashes. The context is private configuration,
not a public report. Absent context preserves predecessor I/O; malformed
requested capture rejects rather than disabling capture.
The actual inspector read sites consume the same cached immutable bytes that
are hashed: JSON/source text, project/nuspec XML and Cecil PE images. Selection
is copied, exact and bounded to 2,048 files, 64 MiB/file and 256 MiB cached
snapshots; individual reads use <=64 KiB chunks and a five-second checked
deadline within the outer owned-child budget. Completion rechecks every
selected file. Unselected/missing/changed/oversized reads and failed or
abandoned captures produce no successful packet. A <=512 KiB hash-only
schema-1 packet contains run/attempt/test/input identity and opaque path IDs
mapped to actual content hashes, never paths or file bodies, and is explicitly
non-qualifying. Literal-only facts may have an empty preselected file map;
their executing assembly still requires independent runtime attribution.
This hook is not parent/runtime admission, containment or provider/component
observation, and does not open the fail-closed qualification gate.
The three literal-only metadata facts additionally have a diagnostic parent
channel: exact discovery/execution in the actual architecture assembly,
independent execution-only context allocation, exact packet set/schema and
run/attempt/current-input/runtime-proof correspondence. Their independently
selected external-file inventory is empty; this does not admit a prepared
graph fact with missing file evidence. An additional hash-only parent receipt
records source execution/runtime/source packet digests. It never replaces a
provider session or opens category qualification. The architecture project has
no SDK reference; its diagnostic output receives independently package-verified
logger dependencies rather than introducing a test-project dependency edge.
Prepared-project resolution has an additional private projecting probe. It
queries actual MSBuild output/assets paths and reference/compile metadata
inside the owned child, retaining only fields the original inspectors use.
Raw tool output is transient and bounded to 1 MiB with a 110-second inner
deadline inside the 120-second owning command. Parent admission requires the
exact current project/hash and projected schema; foreign/symlinked projects,
changed inputs, extra/stale response fields and outputs outside the owned root
reject. The existing graph constructor accepts this resolver without invoking
its predecessor raw runner. Pure predecessor recipes retain their original
ownership and seven metadata/eight artifact scans; actual project resolution
is cached per distinct project within each category.

The separate prepared-inspection diagnostic scope selects all three frozen
prepared facts. Its independent file selector follows the actual full versus
consumer-body read sets, including the appropriate configuration, assets,
project/reference PE images, feature sources, project XML and package nuspecs.
Full inspections additionally select the exact sealed metadata-marker or
artifact-marker Abstractions image and current Abstractions image.
Ordinary files must remain in the owned root with no symlinks. External PE
references are restricted to the corresponding framework reference packs under
the independently resolved dotnet installation, with matching framework/package
metadata and the actual .NET 10 reference layout. Graph labels cannot establish
these trusted roots. Missing/foreign/oversized inputs reject, never shorten a
successful selection.

Selected immutable path/content assignments extend the synthetic configuration
policy fingerprint using opaque path IDs. No path or file body enters public
RunInputs, and these files are not mislabeled as runtime assemblies or source
inputs. Discovery allocates no capture context. Execution binds exact current
run/attempt/input assignments and the selected files; parent admission requires
all and only the matching source packets joined to admitted runtime proofs.
A separate non-qualifying hash-only receipt preserves those correspondences.
The native diagnostic candidate explicitly builds missing Application/consumer/
negative projects with locked preparation but does not pack Application or
extend the existing package inventory. It verifies the family-specific sealed
images before execution and independently selects/hashes files again for both
input documents' completion recomputation. This path does not establish full
historical compatibility, native containment on unsupported hosts, or qualifying
complete category qualification. The default non-session gate remains closed.
The separate native inspection path requires fresh qualification-mode RunInputs
captured before execution and independently recomputed afterwards. It checks
actual owner/manifest/context/settings bytes and exact native argv/cwd, requires
pre/post immutable input snapshots and settled children, and nests witness timing
inside that command. Rewriting all current files and parent hashes cannot turn
an old diagnostic command into qualification. Sanitized packets and complete
source/native parents are retained under `proofs/`; case-attempt proof lists
include source-parent hashes. This implementation has local tooling coverage,
but exact-head Linux execution is pending. Controller admission, remaining
controls and complete profile CLI are not implemented by this path.

Metadata recovery additionally retains and independently corroborates all
31 fresh qualification-input seed/kill/readback/walkthrough commands, including
their actual native/controller sequences, consumed inputs, barriers, settled
exits and nested attempt timing. Safe source/native bytes enter atomic history
proof budgets and case references. This does not manufacture RuntimeWitness
execution UUIDs for control-only cases: those attempts remain incomplete even
when their controller graph is valid. Passed Attempt validation, immutable
frozen inventories and default source rejection are unchanged.

A package-only metadata source fact additionally prepares a hash-only consumed
file packet after checking all 65 declared proof files and the complete recovery
graph. It contains no fabricated execution UUID. Its bounded decoder has modeled
unit coverage, but dispatch, actual native execution and independent
packet-to-RuntimeWitness/case attribution remain pending. A correct unrelated
session cannot substitute for this known independent source.
The subsequent qualification-only source scope now retains the actual runtime
proof, native command/source parent and hash-only packet as a corroborated graph.
Only the logger-supplied execution UUID, independently bound to this graph and
complete case controls, may satisfy recovery case witnessIds. No caller pass
map or fabricated label is accepted. Diagnostic source admission stays closed
and unchanged; actual native confirmation of this additional scope is pending.
The native-stall prerequisite separately retains a hash-only original execution/
controller/producer graph and immutable current-input document. Only its explicit
expected-deadline corroboration accepts `DeadlineExceeded`; changed post-inputs
become `InputChanged`, and ordinary source/command admission still requires
success. No MP-37 runtime source or qualifying case is inferred from that graph.
The later MP-37 importer now independently corroborates that complete graph
against concrete owned execution and exact joint timings. It retains MP-37's
two actual frozen runtime IDs, with the graph's proof hashes, rather than
borrowing the recovery fact's UUID. Missing original witnesses or graphs stay
incomplete. Summary native/recovery digests require actually imported proofs;
no producer flag establishes admission. Actual native confirmation is pending.
Native-stall producer hashes must also match output bytes independently sealed
and hashed by the executor after settled containment, retained in its original
native record. Caller-authored or consistently rehashed replacement packets do
not establish provenance. Ordinary command/source record shapes stay unchanged
when no retained outputs were explicitly requested.

The MP-43 ownership graph separately retains seven exact input/graph/probe/
controller/native files. Original native output hashes bind the closed probe
packet to the observed owner command, with a distinct actual child PID/start
hash and successful competing-owner rejection before barrier 30. Only settled
owner termination followed by successful reopening of the same database,
inside joint-attempt bounds, supplies the control proof. Both commands require
the current immutable assembly/input map and exact argv/cwd. Consistently
rehashed probe replacements or missing/reordered readback commands reject.
The case still requires its frozen actual runtime witnesses, with no unrelated
source UUID. `ownershipSourcesSha256` comes only from imported proof bytes.
No public entity schema changes or native success are inferred from models.

MP-46 retains a separate six-file graph/input/two-command-pair proof. The same
immutable package-only consumer must execute both independently selected
bindings through explicit argv and isolated owned stores inside the joint
attempt. Its common assertion body remains unchanged; legacy invocation stays
supported. Original native records bind exact assembly/current inputs,
argv/cwd, successful settled commands and ordered timing. Missing, reordered
or relabelled compositions cannot supply `unchanged-package-consumer`.
Original runtime witnesses remain required, and `consumerSourcesSha256` is
taken only from imported bytes. No public entity schema changes.

MP-47 retains a four-file graph/input/controller/native proof. The already
sealed pre-F-05 marker and original runtime metadata must match the exact
metadata-marker baseline descriptor; staged Abstractions/Core/Hosting images
must match current captured package-consumer images. Complete staged runtime
bytes are immutable pre/post native inputs. Exact argv/cwd, successful settled
command and joint bounds are required. A closed exact-line projector preserves
the original binary without raw output persistence. Missing/substituted images
or original execution records reject. Existing runtime witnesses remain required;
`binarySourcesSha256` references only imported proof bytes. Public schemas stay
unchanged and macOS execution supplies no Linux/temporal-baseline receipt.

MP-48 retains fourteen graph/input/three native-controller-packet-source groups.
All ten actual interpreter source files and the current-input document are
immutable native inputs; packets and executed source snapshots are original
executor-sealed outputs. The complete unchanged verifier suite runs before
mutation and after repair of the same private adapter. Independent authority
reconstructs its inventory from actual source, requires the named assertion red
with no errors/skips/raw diagnostic bytes, checks exact original argv/cwd and
ordered settled joint bounds, and rejects consistently rehashed setup failures.
Two binding-specific runtime facts consume the complete graph and produce
distinct original execution UUIDs. Neither can borrow recovery's unrelated UUID.
`inventorySourcesSha256` references only imported proof bytes; public schemas
and frozen inherited inventory remain unchanged.

QC-06/07/08 are fixed composite relationships, not extra runtime executions.
Their complete frozen logical, uncertainty/ownership and schema/recovery bases
span both metadata bindings within one joint attempt/sequence. Preserve every
original witness UUID and runtime/controller/source proof hash; no provider
witness is relabeled `none`. Report admission independently reconstructs each
exact union and complete named witness set from its basis attempts. Only these
three exact QC keys may link both binding dimensions, with unchanged matrix/
run/input/time/proof validation. All nine frozen memory durability exclusions
must match exactly and contribute no invented execution. Missing cases,
parameters or controls remain incomplete or reject; failures retain their
original diagnostic and append-only history. Diagnostics never promote QCs.
The unchanged 128-proof collection bound still applies across retries; overflow
is explicit `OutputLimitExceeded`, never truncated evidence. QC-02/04/05,
independent final evaluation and full profile qualification remain unfinished.

Artifact diagnostic source capture is a separate hash-only provenance channel.
Only the actual native category controller requests its bounded sixteen-fact
context. The original six crash, six retained-work and four transfer facts
capture the exact bytes they assert or serialize; crash state/error files are
included, not inferred from a producer label. Context/source path containment,
no symlinks, exact selected files, finite reads/time and create-new packets are
required. Parent diagnostics join all and only those packets to current source
hashes and original actual runtime UUIDs/proofs, retaining read-only packets
and a checked consumption receipt. Native inputs additionally snapshot context,
actual runner, transfer summary and four current transfer proofs. No paths or
source bodies enter the retained packets. Legacy harness and discovery do not
request this channel. A complete-set hash-only index now retains hashes of the
original serialized packets, not late rereads. It is the one predeclared output
of the original ordinary native command, sealed only after actual settled exit.
Independent admission requires its closed schema and exact run/group/attempt/
root/input identities, exact sixteen packet-name/hash entries, immutable
context equality and original executor input/output hashes. Raw index bytes
are authenticated without imposing Python canonical JSON order on C# output.
The consumption receipt retains `outputSealSha256`; parent admission rechecks
the same original index and immutable retained packets. The combined sixteen
input/output bound is unchanged. This implemented diagnostic seal still needs
fresh native execution, and independent native artifact control/source
qualification stays closed.

Native transfer measurements additionally retain per-transfer immutable
current-input documents and original execution receipts. Exact assembly/input
hashes, run/root, argv/cwd and executor-held original controller digest must
agree with the returned command digest before a read-only native receipt is
written. The receipt retains original sequence and controller/execution hashes,
not raw paths or output. The optional explicit safe-mode producer path is now
the measured command's one predeclared output: original bounded JSON is written
create-new before settlement and sealed only after actual exit. Admission
requires its raw hash in the original held output map and records
`producerSha256`; even semantically identical reserialization rejects. Two
immutable inputs plus one output preserve the combined sixteen-file limit.
Legacy five-argument behavior remains unchanged; unmeasured transfers/cleanup
cannot declare outputs. Complete independent transfer/control admission and
fresh native corroboration remain required. Non-native diagnostic adapters
cannot emit these native receipts.

Independent transfer graph admission reselects the unique fixed runner suffix,
exact provider/qualified-size recipe paths and original immutable input document.
It recomputes the generated-byte expectation, validates complete producer/kernel
measurement fields and the exact composite, and joins raw output/controller
hashes to the executor-held original explicit sequence/argv/cwd/input map.
The complete closed recipe must equal those independently selected values.
Ingestion and source-parent rechecking require all four graphs, even after later
commands. Rewired current recipe/control/producer hashes cannot replace original
native records. This closes diagnostic transfer-graph substitution only; fresh
qualification-origin joint bounds and complete artifact controller admission
remain required.
Original crash/state/readback and retained-child validation is shared with the
independent source layer without assertion changes. Private
`qualification-artifact-transfers` input/recipe/store/cache/proof paths require
artifact qualification inputs; diagnostic/category paths and foreign
mode/profile labels reject before execution. Complete original native graph
checks also apply there. Local modeled graphs are not fresh native
qualification execution or complete controller authority.
The independent qualification-origin four-transfer join requires actual common
start/end bounds, serial increasing sequences/nonoverlapping transfer windows
and disjoint original proof paths. It returns immutable source bytes and seven
control-role hash sets. Native transfer controllers invoke it before summary
publication; missing/rejected source authority cannot produce a success-shaped
summary. This does not derive artifact QCs or full profile qualification.

Complete controller-source admission now independently reconstructs the twelve
original crash/retained-child observations from exactly 24 original files.
Shared predicates, distinct non-profile child run IDs and empty recovery-error
bytes are mandatory. The same join validates all four qualification-origin
transfers, sixteen consumed source packets and canonical transfer/consumption/
external receipts against the original complete-set output index. Original
explicit command sequences survive later scopes; a latest-command substitution
cannot replace held output authority. The native factory joins exact owner,
manifest/settings, twelve input hashes, one output, argv/cwd, settlement and
witness timing, and category history routes this controller through that
factory. Both SDK qualification input sets are recomputed at completion.
Fresh qualification transfers precede scopes inside the observed joint attempt;
mode-derived namespaces agree across producer/context/input/parent surfaces.
This private 44-file source graph and its non-qualifying diagnostic summary
introduce no public schema or status changes. Actual Linux replay remains
pending and artifact QCs/full profile qualification remain incomplete.
Quality composition separately uses a catalog-owned basis: QC-10 includes
AS-11/12 on both options; QC-11 includes Local AS-41..44 and the four exact empty
Object exclusion records. Source-sensitive inherited qualification cases require
original controller parents. Report validation recomputes exact current-attempt
basis closure, runtime/proof links, timing and exclusions; missing/shortened/
foreign or borrowed provenance rejects. Earlier failed attempts survive retries.
Diagnostic mode and other artifact QCs remain incomplete; actual Linux replay
and full profile qualification remain pending. No public schema changes.
QC-09's private canonical basis receipt retains every original current attempt
and all runtime observations for all 84 inherited logical case/binding rows.
Its ten catalog-selected source anchors and receipt/source-parent hashes are
a bounded direct projection, not shortened evidence. Report links independently
reconstruct the entire receipt and require its exact retained path/hash.
Earlier receipt bytes remain identical across retries. The 16 MiB receipt and
cumulative profile proof budgets are checked before atomic commit; missing,
replaced, shortened or overflowing bases reject. SDK recording requires exact
read-only originals and emits quality-source count/digest without a passing
qualification claim. Actual native replay and remaining QCs are still pending.
The qualification-origin artifact controller uses validated transport inspection
before independent original source/parent checks and final native history
admission. Inspection alone does not qualify a witness or bypass session/source
policy; ordinary and diagnostic transports retain their original admission.
Category runtime witnesses identify the actual provider archive selected for
their binding, separately from the executing SDK/test assembly. Frozen-slot
selection requires exact captured binding/category/package/inventory agreement.
Mixed scopes retain the complete archive set and per-entry identities; native
source admission reselects both independently. Public report binding/package
hash equality is not weakened to accommodate an SDK package hash.
Original bounded read-only category histories retain every safe witness and
proof link with an independently returned history hash. Runtime proof paths name
the actual owned logger files. After post-input recapture, SDK completion checks
that original history, exact frozen final keys/exclusions, public report links
and every current proof-file hash using bounded descriptor-based reads. It then
emits four Incomplete/non-qualifying category reports with explicit state/hash,
never resource-release or full-profile claims. Changed inputs, histories,
inventories and proof bytes reject before publication. Admissible free-space
variation retains its actual post-input hash, not a fabricated equal snapshot.

`hoard-original-v1` packets use bounded sequential chunks and a complete digest,
with exact run/case/test/binding and hash-only component roles. A private
revision-2 execution proof adds a distinct `originalObservations` collection;
revision-1 proof fields and public report/entity schemas remain unchanged.
Parent admission checks independently selected roles/packages, current runtime,
actual owner context, reopen lineage and observation/instance consistency.
Histories reject observation replay even with fresh attempt/execution UUIDs.
An observation neither transfers cleanup ownership nor proves SDK factory
execution; loaded-contract attribution makes no provider-session claim.

Actual local logger observation and independent fresh-cache locked replay each
pass six exact executions with 26 actual image correspondences. They deliberately
use minimal diagnostic logger inputs and do not qualify category profiles.
Complete original-wrapper/direct-construction/reopen/controller instrumentation
and full current-run input/evaluator integration remain unfinished.
The policy now also includes both actual frozen artifact value witnesses:
expectations/checksums and redacted diagnostics/get-only members. Their loaded
types are observed after the unchanged assertions; the default predecessor build
still has no SDK dependency. Expanded local observation and independent locked
replay pass eight executions/28 actual image correspondences, with minimal inputs.
Five new native diagnostic scopes use separate full captured inputs with frozen
slots, exact primary-case ownership shared with category admission, mandatory
original proofs per execution and independent post-run recomputation. The typed
binding input document remains unchanged in meaning. Native admission for this
new full-input path is pending; complete category/profile/evaluator integration
and wider original/direct/reopen/controller coverage remain unbuilt.
Metadata MP-02/03/13/23..27/31 now also observe their genuine original owners
and the same authority facade passed to unchanged common assertions. One source
helper captures actual references without reopening, disposing or replacing
anything. Local actual observation and independent locked replay pass 26
executions/118 image correspondences with the unchanged SDK archive; they
remain minimal-input diagnostics. Native admission must include the expanded
105-scope/1,008-observation vector, not reuse the earlier eight-execution request.
All twelve frozen artifact publication parameters now share one original-driver
observer after unchanged assertions. It captures the genuine private lifetime
and interfaces without extra sessions, disposal or provider-selected outcomes.
AS-13 retains shared-witness primary-case ownership rather than relabeled or
duplicated proof bytes. Minimal-input observation and independent locked replay
pass 36 executions/188 image correspondences. The expanded full-input native
vector is 105 scopes/1,018 observations and remains pending; the earlier
admitted `40166560899 @8aaa36d` diagnostic predates these full-input scopes.
Independent original image assignments now select exact witness-specific roles
inside each binding and freeze them before execution. Admission accepts no flat
or foreign-witness fallback and requires the exact role inventory. Metadata
wrappers capture the fixture's actual authority unless their unchanged assertion
already used a facade, in which case that same facade is pinned and observed.
Expanded single-owner observation/replay pass 126 executions/638 image
correspondences with minimal inputs, including exact query-corruption/
continuation parameters and both direct-construction admission witnesses.
Admission also rejects extra roots for the current one-observation policies.
Native admission requires 230 foundations and 105 scopes/1,108 observations;
it remains pending. Earlier full-input `40167209164 @0005638` passed all three
jobs, 229 foundations and 105 scopes/990 observations with distinct original/
typed input digests and every prerequisite. Its earlier eight-original
diagnostic does not admit these expanded sources. Multi-owner/reopen and
controller/category/profile coverage are not implied.
Original forest policy now explicitly selects seven additional metadata
lifetime shapes, including independent roots and real schema-reopen chains.
Each execution must match its exact node count and current-execution parent
indices; no root/store owner is reused or borrowed from another execution.
One source sequence preserves actual reference aliases across disjoint roots
without inventing parent edges. Schema roles use the actual adapter owner and
underlying fixture authority, not a newly created evidence facade.
Local observation/replay pass 140 executions, 162 records and 818 actual image
correspondences. Native admission requires 231 foundations and
105 scopes/1,123 observations, pending. Earlier `40168790991 @3f1409a`
passed all three jobs, 230 foundations and 105 scopes/1,082 observations with
every prerequisite; it admits earlier witness-specific diagnostics, not these
later forest sources or complete categories/profiles. Wire schemas are unchanged.
The configured metadata host now contributes two actual module-owned roots,
including rejected schema admission, while 38 additional artifact parameters
observe their existing driver/interfaces after unchanged assertions. Coverage
is 63 operational metadata identities per provider and 183 artifact witnesses,
including actual metadata compositions and configured owners. Source boolean names/values
remain unchanged; multi-parameter provider assignment has no Object fallback.
Nine actual Local fresh-store children require exact immutable per-node image
maps, not a flat original-owner image or cross-node fallback. Legacy metadata
forests retain their common role maps. Both histories freeze all nodes and
manifests enumerate every selected image; Object and early-return reconciliation
rows cannot borrow a Local child. Observers never take cleanup ownership.
Rejected source-created store owners and actual admitted decorator authorities
retain their exact images. Fixed facts keep source parameters and independent
binding assignments; no absent provider token defaults to Object.
Metadata-composed owners and successful configured modules use actual
HostAdapters images/interfaces/controls. Two independent module roots preserve
reference history without invented parent edges or borrowed Local child images.
Eight value/qualification contracts per binding retain actual loaded contract
PE/type proof; they cannot impersonate provider sessions or excluded durability.
Primary frozen-case selection considers applicable rows only.
The private revision-2 channel also admits closed `original-owner` observations
for four provider-neutral authority/bridge facts per explicit artifact binding
and both rejected-module parameters. Only the actual owner role is permitted;
parents, invented sessions/interfaces/controls and substitution for a required
original-instance reject. The copied-handle fact observes both independent
authorities with shared reference history and distinct owner IDs. Rejected
modules never expose a session; observation transfers no cleanup ownership.
Local observation/replay pass 333 executions, 370 records and 2,122 image
correspondences. The existing external-wrapper scope separately validates its
sixteen genuine crash/retention/transfer producer packets. A hash-only supplemental
receipt links each to the actual runtime execution/proof and attempt/group/input
document. Crash state/handshake/kill/fresh readback and acknowledged receipt,
ordered retained-work phases and signal exit, and same-run independently measured
transfer proof correspondence are required. Missing/foreign packets, false
settlement, extra files, reused child runs and stale measurement receipts reject.
It invents no session/component/child-start proof and does not yet satisfy
category/controller qualification.
Native admission requires 236 foundations and
107 scopes/1,317 observations, pending; controllers, remaining artifact lifetimes
and complete qualification are not inferred.

The implemented private transport distinguishes `purpose: discovery` from
`purpose: execution` and hashes each complete JSONL stream in its completion
record. Discovery observes exact selected methods and every expected parameter
row from VSTest discovery events, with actual source assembly and immutable
owner/input/attempt provenance. It emits no execution UUID/status and cannot be
ingested as a runtime witness. This diagnostic transport does not by itself
implement the complete profile/evaluator or loaded-session attribution below.

The implemented typed session-origin producer is another leaf, not a replacement
for that transport. It actually calls the selected metadata/artifact factory,
pins the exact interfaces consumers use, records reopen lineage and captures
actual component assemblies and executing .NET runtime/architecture. Parent
ingestion independently selects every role's admitted runtime/package bytes,
checks the initial declaration and expected parent, and rejects missing,
extra or inconsistent instance records. Factory and provider roles may belong
to different packages. Origins contain no pass status or private tokens/paths.
The caller must own session disposal before capture, and origin observation
cannot imply resource release.

The current result channel carries a hash-only origin projection through bounded
SDK output packets into the actual VSTest result's immutable proof. It contains no
assembly names, private paths or tokens. Required manifest `caseId`, canonical UUIDs,
complete packet indices/count/digest and admitted assembly bytes are checked before
persistence. The execution proof binds those origins to exact test identity,
execution/attempt/group/input/owner provenance. Parent admission independently
checks the planned role/runtime/package assignments, declaration/environment and
reopen lineage. One instance UUID cannot change assembly/module/type across origins,
results or case attempts; fresh execution/attempt IDs cannot launder session replay.
Passing provider-bound qualification witnesses require attributable origins, while
failed/skipped observations do not fabricate them. Native run `39943968117` at
`0687888` verified the full diagnostic channel: fifteen scopes/46 observations and
116 foundation checks without failures/errors/skips. SQLite/PRAGMA production and
complete profile evaluation are later work, not implied by this synthetic probe.

Attempts are append-only. Any genuine contract failure in the run blocks
qualification even if a retry passes. Deliberate red/green experiments are
separate expected-negative child executions: the parent passes only if it
observes the intended named assertion failure and the corrected counterpart
passes the same assertion. Build, setup, timeout or infrastructure failure is
not a valid red result.

Lower-level evidence is reusable only when its exact cases, observed runtime
witnesses, proofs and source/lock/package/config/capability/environment inputs
match this admitted run. Parent imports must validate those child manifests,
not merely a lower-level exit code or previously trusted `qualified` boolean.
Do not copy old runtime passes into a new UUID. Historical compatibility
baseline artifacts are a different explicit entity, not current-run evidence.

## Deterministic Evaluation

1. Validate bounded strict schema, duplicate keys and all digests/proof paths.
   Reject unknown field/status/schema versions, malformed Unicode or non-finite
   durations. Treat import exceptions as safe classified failures, not success.
2. Expand the catalog independently from outcomes. Check exact expected key
   equality (including binding/matrix dimensions), uniqueness and witness sets.
3. Re-evaluate applicability from immutable capabilities/profile/environment;
   reject mandatory exclusions, changed declarations and unauthorized claims.
4. Verify every required proof byte hash and its runtime/input relationship.
   Artifact filenames, count, case labels and hash correspondence alone do not
   establish a witness's origin or satisfy missing assertions.
5. Validate red/green pairs, compatibility baseline identities, crash barrier/
   exit/readback evidence and measured-transfer proof through existing checks.
6. Check attempt history, input stability, profile completion and actual resource
   settlement. Any failure, missing proof or retained ownership blocks passing.
7. Recompute aggregate status and human-readable support statement. Reject an
   optimistic or altered cached summary rather than trusting it.

Report/proof hashes provide correspondence and change detection, not signatures
or hostile-provider attestation. The trust boundary remains reviewed test code
and trusted in-process provider code; this is not security certification.

## Diagnostics and Public Projection

Allow only stable catalog/provider IDs, package/version identities, numeric
measurements, verified hashes, closed failure codes and harness-owned corrective
templates. Do not interpolate provider exception messages, connection settings,
paths, environment values, payloads, SQL or opaque authority tokens. Derive
public output from typed safe observations, not raw log replacement.

Sanitation is required before any diagnostic persistence, including private
retained logs/test results, not just uploads. Capture raw child text only in
the bounded transient buffers declared by the harness; never spool raw
stdout/stderr/TRX or provider exceptions. A safe logger/event projection keeps
exact runtime identities/results without raw failure messages. Legacy evidence
adapters must enforce this before reuse. Unknown diagnostic text maps to a safe
classified failure, not retained raw output or silently discarded success.

Synthetic stores needed to exercise faults are test resources, not diagnostic
evidence. Keep them separate from retained diagnostic/proof directories;
unsettled ownership may require preserving a private store, but it cannot be
included in evidence or treated as sanitized output. If any projection fails
validation, emit a fixed safe failure code and withhold it, never retain/upload
the raw source as fallback. Canary challenges inspect every retained diagnostic
file and public output, including JUnit/Markdown, filenames and CI summaries.

## CI Profiles and Aggregate Check

Planned workflow `.github/workflows/conformance.yml`:

| Job/profile | Mandatory execution | Result artifact |
| --- | --- | --- |
| `metadata` | Both bindings, full MP inventory, durable SQLite and package proofs | Safe profile JSON, per-case JUnit, summary, safe proof manifest |
| `artifacts` | Both bindings, full AS inventory, real transfers/local crash proof, four metadata/storage integrations | Same, no bodies/databases/raw TRX |
| `composition` | CP-01..20 and inherited lifecycle/configuration/discovery regression witnesses | Same |
| `compatibility` | Version matrix, unchanged-source/retained-binary, architecture pairs and foundation gates | Same |
| `harness` | QC harness/evidence mutations, contributor package-only path, tooling regression suite | Same |
| `qualification` | Strict aggregate of all five admitted profile reports | Recomputed finite support matrix and failing/passing check |

All jobs run on the same checked-out workflow source SHA and catalog, using
isolated snapshots/caches. PR merge-ref SHA versus head SHA must be explicit;
never mix their artifacts. CI obtains source history needed for the immutable
baselines. Pack local Hoard packages from those exact snapshots with tracked
locks/source mapping; do not retrieve a published package of the same name.
No dependency/tool installation step is presented as runtime qualification.

Matrix `fail-fast: false`, no `continue-on-error`, finite job/upload timeouts,
`contents: read`, verified full upstream action SHA pins, no cloud permissions,
secrets, publishing or `pull_request_target`. Do not add branch-protection rules.
Use the existing SDK pin and Python 3; no new application/package manager.
Conformance does not alter the separate source-release workflow.

Run public projection/upload on failure with `if: always()` when possible.
The aggregate also runs with `always()` and inspects all required job outcomes;
non-success job or missing/invalid profile blocks qualification even if an
upload step succeeds. Artifact download/upload failure, cancellation or runner
loss cannot synthesize passed results. Seven-day retention, unique invocation/
profile artifact identities and exact file allowlists; no all-workspace glob.
The local baseline uses the same catalog/evaluator, not a CI-specific expectation.

Platform and artifact jobs may execute concurrently in separate snapshots;
large transfers stay serial within each artifact profile. Local baseline is
sequential by default to avoid shared input mutation/resource contention.
Preflight free space and actual runner image are reported; inadequate capacity
is an infrastructure blocker, never a skipped mandatory durability/4 GiB case.

## Scope Labels

Reports distinguish `declaration-lifecycle`, `common-logical`,
`durable-local-process-crash`, `object-simulation` and `unqualified-service`.
There is no initial service profile. A contributor's forwarding adapter does
not count as a third independent implementation. No operational protocol/
identity, native-client, production-provider, Windows, network-filesystem,
power-loss or multi-node qualification follows from these reports.
