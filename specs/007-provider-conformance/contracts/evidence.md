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
proofs. Their qualification admission remains unimplemented and fails closed,
including when the execution selects `none` rather than a provider binding.
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
