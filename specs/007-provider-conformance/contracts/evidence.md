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

The implemented category batch history derives each binding's entire frozen
runtime union from the independent catalog and requires both category package
options. The primary execution context for a shared runtime witness is its
lexicographically first mapped case. Projection retains the original execution
UUID/proof hash across all explicitly mapped obligations; no transport or proof
is relabeled. Results cannot omit either binding or any QC/control key.
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
