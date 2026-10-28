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
certification. Its artifact test-only fault drivers now distinguish explicit
`InjectPublicationAcknowledgmentLossAsync` from ordinary boundary observers:
only the exact registered injected exception is expected; other exceptions
continue to fault ownership settlement.

The public `scripts/validate-conformance.sh --profile metadata|artifacts
--evidence <fresh-private-path>` entry now dispatches the complete built-in
category batch on supported Linux hosts. It preserves independently selected
case keys, exact native source/witness admission, immutable applicability and
actual resource cleanup. Even a successful component batch retains an
`Incomplete`, non-qualifying report and returns exit 2 (`EvidenceIncomplete`):
the independent evaluator is unfinished. Unsupported native hosts fail
`PrerequisiteMissing` before allocation. Focused/custom-binding commands and
other profiles remain explicitly incomplete, without fallback. This is not yet
the external contributor entry point or category certification.
Both built-in jobs at exact `ef82218` now pass complete component execution on
Linux, including real SQLite schema/backup/recovery, Local abrupt-process
recovery and both paced 256 MiB/4 GiB transfer sizes on each artifact fixture.
The 192 inherited entries retain exactly 179 applicable passes and thirteen
exclusions: Memory MP-36/38..45 and ObjectSemantics AS-41..44. Memory claims
logical behavior only; ObjectSemantics claims no durable process restart.
Package-only consumer/source controls use identical consumer/SDK images across
the respective bindings and independently checked package resolution. Reports
still do not qualify providers. Protocol/identity fixtures remain declaration/
lifecycle checks, not native-client or production support.

The complete category runtime acceptance is independently confirmed again at
feature head `44fd370b221aaf247eee52b1fad28a647370d772`,
[run40612965869](https://github.com/Stonefly-Labs/Hoard/actions/runs/40612965869):
metadata job122569229740 and artifacts job122569229921 both succeed through the
public profile commands and post-release report/proof/completion checks.

| Category | Passed catalog results | Authorized exclusions | Runtime scopes / parameters |
| --- | --- | --- | --- |
| Metadata: SQLite and Memory | 93 | 9 Memory durability cases | 10 / 141 |
| Artifacts: Local and ObjectSemantics | 99 | 4 ObjectSemantics restart cases | 9 / 263 |

These totals include thirteen additional category quality results; the frozen
inherited inventory is still exactly192 entries,179 applicable passes and13
exclusions, not a smaller replacement inventory. Native recovery, paced real
256MiB/4GiB transfers, authority integration, package-only common consumers and
intended-failure/corrected mutation sources remain independently bound to the
current attempt. Frozen-wrapper parity and omitted/renamed-parameter controls
pass in the full tooling suite. The [implementation evidence](../specs/007-provider-conformance/plan.md#complete-category-runtime-acceptance-t037t038)
records input/result/report hashes and the exact checks.

SQLite exercises actual file-backed transactions, schemas, backup/recovery and
abrupt-process cases; Local exercises actual files and recovery. These fixtures
are not production persistence/storage modules. Memory has no crash-durability
claim; ObjectSemantics is an independent logical simulation, not an object-service
client, durable remote restart, HA or distributed consistency claim. No protocol
native-client, authentication/identity, upstream cache or untested cross-product
support is implied. Source wrapper assertions remain shared with the test SDK;
concrete setup/fault/cleanup belongs to bindings, not provider-selected expected
outcomes. T037/T038 are complete execution/documentation tasks, not provider
qualification: reports remain `Incomplete`, exit2, and independent full-profile
evaluation, compatibility, contributor and five-profile aggregation remain open.

Architecture checks additionally keep the test SDK outside all nine production
owner classes, permit explicit test owners, require complete scan inventories,
and reject malformed entries through the inspection-error boundary. Actual
direct/helper Identity-to-Core paths remain forbidden in either traversal order
even with the permitted Identity-to-Hosting-to-Core route present.

Finite composition execution is now confirmed at exact `44fd370`,
run40612965874/job122568697750: all 36 physical CP parameters and 110 snapshots
support 41 logical passing subvariants after independent post-release replay.
This includes explicit baseline/replacement, disabled-effect counters,
rejection/repair, actual readiness/admission and retained/eventually settled
ownership. T047 is an execution checkpoint, not a new qualified provider scope:
nine quality-source rows, full-controller acceptance and qualification remain
incomplete. The version logger's local 114-parameter/170-observation protocol
replay likewise does not establish historical SDK or untested version support;
the release-classifier rows remain policy-only, never runtime claims.

## Finite packaged composition and ownership limits

The test-only packaged Host selects SQLite/Local for its baseline and
Memory/ObjectSemantics for its replacement, using one unchanged package-only
consumer. Host/binding images must match their independently packed local
`[0.1.0]` archives. SQLite/Local exercise file-backed stores; Memory and
ObjectSemantics do not acquire durable restart guarantees from composition.
Protocol and identity modules here are declaration/lifecycle probes invoked
through TestServer, not package-protocol clients, an authentication system or
a production service. This does not broaden the category scopes above.

Selection and enablement are explicit: installation/registration is not
activation. Disabled modules expose no routes/workers/connections/store
effects. Missing or incompatible required modules, invalid cardinality,
incompatible enabled optional targets and mismatched authority/guarantees
reject rather than falling back or silently changing the selected providers.
The fixture initializes selected stores before readiness and request admission.
Configuration remains fixed for an active request; changing selection requires
settled stop and explicit fresh restart, not hot replacement.

Cancellation or a finite stop response can leave initialization/request/stop
work retained. In that state, refuse unsafe root disposal and restart; retain
ownership until the actual callbacks settle and inspect the existing lifecycle
result. Do not equate loss of a reference, removal of scratch evidence, eventual
callback settlement alone, or forced child termination with a cooperatively
released module root or recovered store. Native exact-child containment and
process-resource release are separate evidence from module-root cleanup.
There is no new force-recovery or production host API.

Exact `0e49db127ee1a38b49dd157adc7eba1a02a99b11`,
[run40620701197](https://github.com/Stonefly-Labs/Hoard/actions/runs/40620701197)
job122595970901, now confirms all36 CP parameters/110 ordered snapshots,
41 logical passing subvariants and independent post-release report replay.
All29 generated-report mutations and both original-proof semantic challenges
reject despite successful host labels: readiness before initialization and
completed stop while ownership is retained. The workflow requires the exact
29/two receipt before success. Inherited525 parameters/58 scopes,3,273 bound
controller inputs,41 formatting commands, mutation pairs/reference consumer
and actual process release also verify. T048/T049 are finite control/documentation
checkpoints, not qualification: nine quality-source rows remain `Incomplete`,
all qualification/full-controller flags remain false and the public composition
command retains expected exit2. The compile-only
[CustomHost](../examples/CustomHost/README.md#f-07-finite-packaged-composition-and-recovery-limits)
still never calls application `Build`, `Run` or `Start`.

## Finite compatibility evidence and author obligations

The public compatibility diagnostic is available on the supported Linux
confinement hosts with the repository's pinned .NET SDK, Git history and locked
package prerequisites. Use a fresh child of an owned, mode0700 private parent,
outside the checkout:

```bash
bash scripts/validate-conformance.sh --profile compatibility \
  --evidence "$HOARD_PRIVATE_PARENT/compatibility"
```

Its expected result is still `Incomplete`/exit2, even after successful execution
and process release. It does not run the unfinished independent qualification
evaluator, and `--verify`/five-profile `--aggregate` remain unfinished. Never
interpret a diagnostic's component success or workflow conclusion as provider
qualification. A repeated run needs a different fresh evidence child; do not
edit or reuse a retained baseline or repair a report in place.

The immutable
[baseline inventory](../tests/fixtures/conformance/baselines/inventory.json)
pins these source revisions, not a range of allegedly supported releases:

| Baseline purpose | Exact revision |
| --- | --- |
| F-07 pre-extraction F-06 source | `9389016c0285c79f6f515f59805a5a41c69b0767` |
| Lifecycle predecessor | `837fdf3edf51c3df34710184d018479683c194c2` |
| Configuration predecessor | `b80c69fc386541be4f56f6ef2edeca40f43a0e1c` |
| Discovery predecessor | `7fd73267a5154583363c94e9e85b9bac7d4a16b3` |
| Metadata predecessor | `10ce78851b97b02bd83a8ef7da7ffdc2381d6519` |
| Artifacts predecessor | `830972f24795ffaaaa18cb35138db7da59022313` |

Historical sources, recipes, locks, dependencies and binaries are sealed before
candidate compilation. Current local acceptance packages retain version
`0.1.0`; equal version labels never establish equal bytes. Actual archive
SHA-256/SHA-512, assembly hashes and source/lock identity must agree before and
after execution. The tested packages include `Hoard.Abstractions`, `Hoard.Core`,
`Hoard.Hosting`, inherited fixture modules/providers and the four
`Hoard.Fixtures.Conformance.Bindings.{Sqlite,Memory,Local,ObjectSemantics}`
adapters. `Hoard.Testing.Conformance` is new in F-07: its current-source adapters
are not evidence of a historical SDK release.

Exact `c9a5990462be78df7220469b88342b662ac19edc`,
[run40621394269](https://github.com/Stonefly-Labs/Hoard/actions/runs/40621394269),
job122600307923 confirms 24 source recipes: twenty unchanged historical F-06
consumer/provider sources and four current-source SDK adapters. Nine separately
retained scenarios observe forty actually loaded assemblies without rebuilding
the old consumers against the candidate. Old marker consumers establish only
their consumed API/invocation compatibility, not operational metadata/artifact
conformance. An intended missing-member source break must fail compilation at
the named member; compatible sources must compile unchanged. Candidate-rebuilt
old consumers, accidental resolution to old platform DLLs, altered dependencies
or substituted same-version baselines do not satisfy these obligations.

That same native receipt confirms all88 architecture parameters over22 graphs
and eight required real scans, plus114 version parameters/170 observations.
Declared host/abstractions/required/enabled-optional ranges are tested against
the finite [version matrix](../specs/007-provider-conformance/contracts/matrix.md),
including independent prerelease flags and explicit rejection/repair. Invalid,
out-of-range or unsupported versions reject; disabled/absent optional targets
do not become active edges or grant capabilities. C-05/06/16/17 remain
release-policy classifications, not runtime compatibility claims. Source,
retained-binary, graph and runtime-version checks establish different facts;
none replaces another or grants untested Cartesian-product support.

The supplemental seven-parameter PE/PDB-source and isolated binary
break/repair/substitution attempt at `3ca391a` failed schema admission before
confirming its binary scope. The transport repair permits only the four exact
frozen public source identities; arbitrary/private paths remain prohibited.
A fresh native confirmation is still required.
It supplements, never replaces, the nine genuine historical retained scenarios.
Overall compatibility qualification remains false. These test-only results
authorize neither package publication, source release, deployment nor production,
protocol/native-client, identity, external-service or HA support.

### Contributor registration admission, not execution

For metadata/artifact projects, public invocation admission now requires a
sibling `<Project>.conformance.json` registration. The
[forwarding fixture registration](../tests/fixtures/conformance/Contributor/Contributor.conformance.json)
declares the source-root-relative project, source-qualified factory type,
adapter package, binding declaration, every category component's package/image
identity and explicit source inventory. Unknown fields, provider-selected
exclusions, missing hooks/components, unsafe paths and source symlinks reject.
Bounded source hashing freezes a declared-input fingerprint.

This does not prove complete MSBuild source/import/lock closure or compiled
factory/category identity. No external project is built in place, no typed
factory bridge executes yet, and custom execution still returns
`EvidenceIncomplete`. Adapter wrappers, underlying provider and shared
authority/fault helpers remain separately declared; this forwarding example
does not become an independent provider or inherit built-in runtime evidence.
Owned snapshots, actual package/runtime attribution and separately packaged
good/red/corrected complete-suite runs remain required by T064..T067.

### Earlier F-07 diagnostic checkpoints

The test-only package-mode composition consumer now explicitly references
`Hoard.Fixtures.Conformance.Host` at `[0.1.0]`; Host source links remain only in
source mode. Both real SQLite/Local and Memory/ObjectSemantics rows run from the
same consumer image, check initialization before readiness, make in-process
protocol/identity probe requests, leave the disabled store untouched and observe
complete stop. The loaded Host image matches its local archive, and independent
fresh-cache default locked restore/build passes. These two rows now emit closed,
bounded before-initialization/ready/stopped snapshots linked to the actual Host
owner and loaded archive bytes. Independent ingestion admits six actual snapshots,
requires successful stage invariants, and rejects omitted/replayed observations
or false readiness/cleanup. Genuine failed attempts retain available ordered
snapshots and original proofs, never an inferred pass. No output guard is relaxed.
This is diagnostic component evidence: remaining composition output conversion,
inherited inventories and independent full-profile evaluation remain unfinished.
Complete component replay additionally passes all 155 discovered packaged
composition/version rows and 148 source-mode rows: declaration rejection/
repairs, mapping ambiguity, optional-target inactivity and capability denial,
all four version axes, independent prerelease flags and finite inherited
classifications. Policy-only release classifications remain policy-only;
these component passes do not widen declared ranges or qualify a profile.
The packaged Host also owns shared controlled callbacks for all seven
CP-15/16/17 rows. Both initializer `lateFault` parameters and all three shutdown
variants are now mandatory catalog witnesses, with exact package discovery/
result parity. All seven now emit bounded owner-linked observations of actual
callback/task completion and faults, readiness/admission, stop/root outcomes and
module counters. Independent stage policies reject false settlement/release;
settled retained roots remain incomplete. Nine actual safe proofs and nineteen
snapshots pass together with baseline/replacement. Native containment, complete
ownership/profile integration and qualification remain open.
The initializer-failure row also preserves actual task faults and rollback stop
before complete owner disposal. Ten actual package proofs/twenty-one snapshots
pass independent ingestion. The dedicated native composition diagnostic records
the command/input closure and checks process-resource release separately from
cooperative module-root cleanup. Its first Linux attempt rejects unsealed
command inputs. Its sealed successor reaches launch but rejects test output
through the build projector. The corrected test projector passes the Linux
thirteen-row replay at exact `e9a1589`, including actual process-resource release.
The schema-denial and corrupt-manifest recovery rows now add distinct actual
denial/repair owners, closed failure/admission/worker/root counters and retained
failed prefixes. Actual admission passes thirteen package proofs/thirty-three
snapshots; a successful repair waits for both real worker entries first.
The short native component has its own diagnostic workflow, not a qualifying
profile. Its component environment explicitly leaves SQLite provenance
unobserved rather than claiming the platform-only probe measured that library.
Exact `f6e9db4` passes this independent native workflow with all thirteen proofs/
thirty-three snapshots and real process-resource release. This closes the
bounded CP-14..18 probe implementation (T044), not complete provider or
composition qualification. CP-19 authority/guarantee admission and CP-20 active
request controls now execute from the shared Host package, preserving real
Local-store pre-I/O denial and explicit settled restart. All four package cases
pass after three intended consumer-local ownership failures. Safe CP-19/20
transport, inherited inventories and full profile integration remain unfinished.
The subsequent safe transport increment independently admits all seventeen
selected package proofs/fifty-one snapshots, including CP-19 pre-I/O denial/
repair and CP-20 fixed configuration, request drain and distinct fresh restart.
Independent challenges reject optimistic cleanup, hidden fallback, premature
request settlement and hot replacement. This is diagnostic component evidence,
not complete profile qualification; expanded native replay remains pending.
The seventeen-row native replay subsequently passes at exact `cb8d6eb`.
All CP-01..20 safe component rows now independently admit thirty-six actual
identities/110 snapshots, including every declaration-theory parameter.
Route-conflict observations preserve the real early rollback stops and zero
disposal callbacks for unmaterialized fixture services; complete root stop
does not invent module disposal. Inherited inventories/full-profile acceptance
remain unfinished. Exact `59d9eff` separately passes the larger native scope
with actual process-resource release. A bounded inherited configuration
experiment now admits all twenty historical structure-theory cases, preserving
unchanged assertion source and candidate platform image/archive agreement.
Opaque `testCaseSha256` identities bind the actual adapter ID plus private
display in memory; hashing display alone is insufficient because xUnit truncates
twenty cases into twelve distinct names. Private arguments are not retained,
and changed case IDs/displays or duplicate literal aliases reject. This does
not yet integrate complete inherited inventories or qualify a profile.
The subsequent committed discovery tool has a locked test-only TranslationLayer
dependency, bounded typed events and closed diagnostics. The independently pinned
F-06 catalog covers 203 methods/525 parameters: all 509 composition parameters
are discovered and admitted, while six architecture methods/16 parameters and
prepared distribution/controller journeys remain unexecuted in this increment.
Neither discovery nor an observed count substitutes for those runtime obligations.
The first native discovery attempt rejects its oversized direct input list
before child launch. A pinned closure request now verifies all images in the
child and parent without widening recorder limits; that local check alone does
not establish native replay.
Exact `6178a77` subsequently passes Linux run40435964976 with all 509 discovery
identities, the 36 CP proofs/110 snapshots and actual process-resource release.
Scoped safe controller preparation then produces five foundation packages/two
CustomHosts, seven lifecycle journeys/ten graphs, nine configuration journeys/
thirteen graphs/five actual publication barriers, and nine discovery journeys/
seven observations/eighteen graphs, including the required retained binaries.
All 509 inherited composition parameters and 16 boundary parameters subsequently
pass independent local runtime ingestion in 58 exact class scopes. This is a
non-qualifying diagnostic, not native inherited execution, complete historical
controller/mutation acceptance, public profile integration or T046 completion.

Legacy interactive runners preserve the unreaped leader until all owned
descendants settle, including descendants that close or inherit output handles.
Post-handshake output drains concurrently within bounded retention; it cannot
block transfer completion indefinitely. Safe metadata replay additionally
requires the independently selected provider and explicit configuration digest;
Memory evidence cannot be relabeled SQLite or replayed against another workspace.
Fresh metadata recovery and six real Local SIGKILL/reopen journeys pass, still
with `qualification: false`. Required large-transfer replay remains blocked by
insufficient local scratch; no capacity threshold, transfer size, applicability
rule or acceptance gate was reduced.
The independent C# inventory decoder requires the same actual legacy transport
input as Python; removing it and resealing command hashes cannot bypass admission.

The test-only `Hoard.Fixtures.Conformance.Contributor` package now exposes
`ForwardingMetadataBinding(providerPackageSha256, injectStaleReplay: false)`.
It explicitly forwards Memory setup, schema, authority, faults, reopen and
actual cleanup ownership. Its declaration identifies a non-durable forwarding
example, retaining the real underlying provider package identity. Setting
`injectStaleReplay: true` selects the existing isolated stale-replay decorator;
it returns an old successful receipt after expiry, so unchanged
`MetadataTimeAssertions.TicketExpiryAndRollbackAsync` rejects it at the intended
assertion. Switching only that flag back repairs behavior without changing
platform, provider, adapter, assertion or consumer image bytes.
Package-only tests also execute actual legacy upgrade/reopen and reject artifact
category admission. The package is not published, an independent implementation,
complete conformance, or a substitute for the still-unbuilt public contributor
CLI/guide journey.

Metadata test-only corruption controls now retain per-record or exact
epoch/operation ownership through application and verified restoration. Scope
overlap and reopen/disposal reject while a target is owned; once closure is
admitted, later corruption rejects before touching the store. Both adapters use
their own compare-exchange primitives. `CorruptionCaptured` and `PayloadChanged`
are typed observation points, not provider strings in shared assertions.
Cancellation after a mutation restores before releasing the target.
`RestoreCorruptionsAsync` explicitly retries failed restoration, while an
applying owner still rejects recovery and closure. No private database image
type enters the SDK; Memory gains no durability.

Artifact fault drivers additionally expose bounded exact-stamp payload capture,
replacement and removal. Each provider executes its own tracked controls,
rejects stale incarnations and enforces a 64 KiB qualification-payload limit;
capture and replacement copy caller-owned bytes. Controls do not fabricate
receipts or clear quarantine. They hold genuine authority read protection
through target selection, I/O and file disposal, excluding concurrent deletion.
`PayloadSelected` observes that actual check/I/O boundary; the waiting-admission
counter corroborates genuine deletion blocking without a timing-only assertion.
`CommitProgress` maps independently to each
provider's genuine progress boundary. Registration occurs at the common
assertion's requested installation point, not during its setup publication.
Local damaged-read consumers preserve compatible-reopen quarantine through the
observed session; Object does not claim durable reopen. The original permanent
quarantine helper remains unchanged, with explicit async-reopen denial negatives.
The 62-row actual artifact selection and local wrapper/assertion parity remain
diagnostic evidence, not complete extraction or provider certification.

The full artifact diagnostic selection additionally includes thirty unchanged
recovery/evidence/expiry and stream-ownership consumers, bringing its scope to
92. Both providers execute exact receipts, bounded/query-bound pages, cursor
retirement, changed inventories, expired staging generations/reservations,
finalized outcomes, idle readers, cooperative/non-cooperative streams and all
three canceled-descriptor shapes. Ownerless reservation expiry preserves the
original one-byte artifact/staging limits, not a substituted ticket-count limit.
Every added row requires its actual origin and settled owned resources; local
thirty-row wrapper/assertion parity does not grant native qualification.

Seventeen further observed rows extend that diagnostic scope to 109, retaining
original authority/cancellation/capacity limits, sanitized storage errors,
live/unavailable reference decisions and reclaimed-history bounds. The original
reclaimed-incarnation case remains Local-only. Each row requires its genuine
origin and settled resources; complete seventeen-row wrapper parity and named
SDK-only capacity assertion negatives are local diagnostics, not qualification.

Twenty handoff/progress and rollback rows extend this selection to 129.
Awaited installation/removal preserves existing synchronous consumers and
common assertions, with genuine provider observations at the requested point.
UTC rollback does not rewind controlled monotonic time. Complete local wrapper
parity and successful-read assertion negatives do not establish native admission.

Twelve admitted-work/reconciliation/cleanup rows extend the selection to 141.
They retain the original one-identity deletion-history budget, one-slot/one-waiter
transfer queue, five-second shutdown allowance and one-ticket reconciliation
budget. Original Local before-resolution versus Object direct-verification
boundaries remain explicit adapter choices. Recovery installation/removal is
awaited, and intentional acknowledgment loss uses the owned typed injection;
ordinary observer failures are not forgiven. Twelve-row identical-SDK wrapper
parity and three named assertion negatives remain local, non-qualifying evidence.
Strict native run40271691109 at `831b00c` admits the earlier 129/152 artifact/
metadata sources, not this 141-row extension or complete category qualification.

Complete local metadata parity passes 152 actual rows and both 63-row original
families using identical SDK archives. Continuation, query-dimension and lease-
expiry SDK mutations fail the corresponding named assertions in all families.
Qualification-input original memory/SQLite scopes now independently reconstruct
role/creation/reopen attribution and require sealed original runtime packets,
the exact SDK/provider/host/wrapper images and their held command inputs.
Exact `74cf619`/run40279501756 admits these original metadata parents on Linux:
all three jobs pass, 337 native foundations without skips and ten metadata
parents. Earlier `bc85094`/run40276791513 admits artifact141/metadata152.
The metadata report remains `Incomplete`, qualification false. All sixteen
individual parameter mutations also produce exact 2/1/1 actual/memory/SQLite
named failures across complete 152/63/63 families, but these local diagnostics
do not supply an admitted native exact-parameter control or complete QC-02.

Eleven further history-candidate rows extend the artifact scope to 152.
The adapter owns candidate observations and a one-shot ticket-candidate
failure separately; duplicate registrations reject without replacing the
current owner. All seven frozen bounds parameters and both resume cases
retain their shared assertions. Ordinary observer exceptions are recorded
before the private injection runs and still fault settlement, even if their
type/message matches the injection. Fresh fourteen-package replay passes
308 selected metadata/artifact consumers. Complete 304-row actual/nine-row
frozen replay passes, including duplicate-registration guards; SDK-only bounds
and resume mutants give both families exactly seven/two named failures,
respectively, with all other rows passing and identical runtime SDK/archive
images. Native observation and complete category qualification remain outstanding.

Ten further receipt/read-opening/reconciliation rows extend the artifact scope
to 162. Owned failure registration admits only read-opened and verified-
reconciliation points; ordinary callback errors, including the same exception
type/message, still fault settlement. Awaited overloads preserve all six
original observation cases and the one-transfer-slot/no-waiter read limits.
Fresh packages pass 318 selected consumers. Complete 314-row actual/six-row
frozen parity passes, while each of three SDK-only assertion mutants produces
two named failures in both families and all other rows pass with exact SDK
image/archive correspondence. These are local diagnostics, not complete QC-03.

Exact `d30271d`/run40286734253 independently admits artifact162/metadata152
on Linux: all three jobs and 337 native foundations pass without skips, with
ten metadata parents. The later argument transport is not covered by that head.

Common metadata assertions now record their closed enum/layout arguments
against the actual component objects. Late output drains each call once;
early original-schema output has an explicitly owned disposable observation
scope. Closure joins output before releasing ownership, overlap cannot replace
an existing owner, and reused objects cannot replay historical calls. The safe
logger and parent independently validate schema3 argument/source/role joins;
schema1/2 remain supported. Metadata category declarations, not reference
binding names, govern argument admission. This is transport, not an independently
composed native QC-02 control or completed provider qualification.
Independent source admission additionally checks the frozen per-witness
argument map and exact original forest nodes. Original proof digests include
the independently re-read arguments. Pairing now independently re-admits both
complete original scopes and joins the current shared graph/SDK images before
issuing all four QC-02 controls. QC-02 retains the complete 96-key basis and
authorized exclusions in a compact packet, independently recomputed by report
admission. Exact-head native confirmation remains pending.

The subsequent artifact scope has 166 rows: pending physical reclamation and
ordinary same-shaped delete-removed callback failures run on both bindings.
The awaited shared injection overload preserves the synchronous original
wrapper and its assertions; only the exact owned exception is intentional.
Ordinary callbacks fault actual settlement and retain cleanup ownership.
Fresh packages pass 322 selected consumers; fourteen actual/two original
controls pass and an SDK-only cleanup assertion mutant gives exactly two named
failures per family with matching SDK/archive images. This is local parity,
not full QC-03. Exact `b66e6b0`/run40292115062 independently passes three Linux
jobs/341 native foundations without skips and admits the earlier artifact162/
metadata152 argument transport, not the later map/pairing/deletion changes.

Two admitted-open quarantine races extend the artifact scope to 168; fresh
packages pass 324 selected consumers. Awaited shared hooks preserve both
original wrappers and assertions. Exact-stamp replacement now permits existing
readers, matching the original fault without releasing actual deletion
protection or serialized fault ownership. Both actual/original pairs pass; an
SDK-only final quarantine assertion mutant gives two named failures per family
with matching runtime SDK/archive images. QC-03 remains unfinished. Pairing
run40295489832 was canceled before jobs, not admitted; replacement deletion
run40297863544 awaits independent observation.

All four validation-first missing/truncated payload rows now run through the
actual bindings, retaining Local compatible reopen without borrowing it for
Object. The artifact scope is 172; fresh packages pass 328 selected consumers.
Four actual/original pairs pass; an SDK-only incarnation assertion mutant gives
four named failures per family with matching SDK/archive images. Safe-logger
replay checks 172 witnesses/178 origins, six reopen edges and exact role/image/
archive matches. Missing, extra and foreign validation origins reject.
Exact `e39b2ce`/run40293145453 independently admits earlier frozen metadata
argument maps with all three Linux jobs/341 native foundations passing without
skips. QC-02 pairing/newer artifact scopes and complete QC-03 remain unadmitted.

The complete artifact shared-consumer source family now has qualification-only
native reconstruction and original proof retention. It requires all 250 witnesses/
262 origins, exact six consumer/SDK/binding/provider images and the same SDK in
original wrappers, plus the executor-held command/input closure. Tooling454
(19 native skips) passes. Actual native admission and QC-03 pairing remain pending.

Original artifact scopes now reconstruct all 183 mixed and twelve repeated
witnesses per provider from exact native forests/role images, readonly original
proofs and wrapper SDK/archive correspondence. The command closure includes all
manifest images and must fit its containing attempt. Tooling455 (19 native skips)
passes; this source reconstruction alone is not QC-03 pairing or native admission.

Artifact native parameter pairing now re-admits all original scopes alongside
the shared-consumer source with cross-source execution/origin/instance isolation.
QC-03 requires readonly pairing material and a recomputed full AS-01..48 basis,
including actual transfers, Local recovery and the four Object exclusions.
Tooling458 (19 native skips) passes. Native admission and full qualification
remain pending; no provider guarantee or exclusion is changed.

Native run `40320966626` rejected writable original-artifact proofs before
source admission. All three qualification scopes now use the existing
settlement/byte-check/read-only sealing path; diagnostic mode and provider
mechanisms are unchanged. Exact `5ba30af` / run `40328218160` passes all three
Linux jobs and admits all current category cases (metadata 93 passes/nine
exclusions; artifacts 99 passes/four exclusions; no failed/incomplete cases).
The reports still explicitly remain `Incomplete`, qualification false; this
is not full provider or five-profile acceptance.

Actual completion inputs are retained as read-only category proof packets, bound
to `postInputSha256` and independently rechecked against admission inputs. Free
space may vary as a measurement; immutable provider/source/environment inputs
may not. The reports remain non-qualifying.

`conformance_sdk_checks.py --category metadata|artifacts` selects only one native
extraction batch after shared package/baseline preparation. It must recheck
inputs and release synthetic resources before reporting actual ownership.
The report remains `Incomplete`/non-qualifying; independent public profile
evaluation and native confirmation of this isolated path are still pending.

The first isolated native run failed report admission after actual cleanup
because generated runsettings were still stored among disposable synthetic
resources. Settings now belong to retained read-only input proofs, and native
command/source attribution uses that exact location. Cleanup is not weakened,
and fresh native success is not presumed.

Legacy metadata/artifact imports now require original safe-logger attribution,
actual SDK package/image correspondence and exact per-parameter results, not
TRX labels alone. Unknown/oversized child diagnostics fail without raw spooling;
barrier output and post-handshake crash output are drained through termination.
Runtime staging rejects preexisting logs/reports/dumps before copying any
execution input. OS peak RSS remains an actual profiler measurement, with only
its checked numeric projection retained. These transport changes do not waive
SQLite/Local recovery, real transfers, independent implementations or the
thirteen authorized simulation exclusions.

The architecture inspector now identifies `Hoard.Testing.Conformance` by its
case-insensitive package/assembly identity, not the generic SDK category alone.
Production module paths to it reject, including transitive paths; ordinary
vendor-driver SDK permissions are preserved. Misclassifying this test SDK as
BCL/Abstractions/helper is an inspection failure. Explicit test owners may
consume it. Controlled declared and compiled graph cases do not replace the
full required project/package scan inventory.

CP-01..20 tests now cover declaration rejection/repair, disabled effects,
late-fault sanitization, retained ownership, refusal of unsafe restart and
active-request drain/admission. Focused package-only CP-01/02/18/19 cases pass
against separately rebound retained archives; that replay is not fresh-source
profile acceptance and does not change production support claims.

Object's driver-owned access faults now reside in its concrete binding, not the
provider assembly; native exact-stamp selection/protection and pre-hook handle
capture are unchanged. The provider has no rename mechanism. The unchanged
prepared architecture witness fails on the preceding graph and passes on the
repair. Fresh fourteen-package replay passes 406 consumers; 16 actual/four
original access cases and the SDK-only negative retain exact assertion parity.
Safe-logger replay checks 250 witnesses/262 origins. Native admission is pending.

The current artifact250 scope preserves retained prefix, reused/unselected object,
committed residual and failed-stop cleanup through actual storage facts and mode
restrictions. Facts contain opaque file IDs/lengths only, stay root-owned even
after explicit stop, and fail explicitly on overflow/directories/symlinks.
Enumeration now bounds all entries, repairing the scoped architecture finding.
Fresh fourteen-package replay passes 406 consumers; 24 actual controls/12 original
wrappers pass. Six SDK-only mutants cause matching 2/2/1/4/1/2 named failures per
family with matching loaded SDK/archive images. Six ordinary same-message callback
errors retain exact faulted settlement. Safe-logger replay checks 250 witnesses/
262 origins and twelve reopen edges, including Local prefix-stop replacement,
never Object restart. Native/full QC-03 and final T081 remain unfinished.

The preceding artifact226 scope also owns genuine Local decisions-directory write
denial. Original failed-quarantine assertions retain failed stop, payload/mode
restoration, retry and same-lifetime compatible initialization before owned reopen.
The same single pending access owner captures handles before release callbacks
and restores modes before closure; Object rejects this Local-only control before
allocation. Ordinary release errors/cancellation retain exact faulted settlement;
delivered success remains delivered under unchanged supervisor semantics.
Fresh fourteen-package replay passes 382 consumers; five actual controls/one
original wrapper pass. An SDK-only readiness mutant gives one named failure per
family with matching SDK/archive images. Safe-logger replay checks 226 witnesses/
237 origins and eleven reopen edges. Scoped review finds no actionable issues,
not final T081 or native/full qualification.

The preceding artifact217 scope preserves original validation access failures with
real Unix mode changes/directory removal, not synthetic result codes. Opaque
exact-stamp scopes retain read protection until restoration, preventing deletion
or payload resurrection. Their pending owner captures the actual native scope
before release callbacks, so an ordinary callback exception cannot strand it.
Shutdown joins pending application/restoration before worker/authority settlement;
ordinary errors remain explicit `CleanupIncomplete` with faulted settlement.
Fresh fourteen-package replay passes 373 consumers; sixteen actual controls/
four original wrappers pass. An SDK-only failure-code mutant gives four named
failures per family with matching SDK/archive images. Safe-logger replay checks
217 witnesses/227 origins and ten reopen edges. Scoped findings are repaired,
not final T081 or full QC-03/feature acceptance.

The preceding artifact201 scope retains Local committed-decision clock rollback
after 105 retired histories and durable-receipt staging-release recovery.
Awaited compatible reopen preserves original assertions and synchronous
wrappers. Exact-occurrence record interruption is owned and mutually exclusive
with the synchronous hold; ordinary same-message callback errors retain actual
faulted settlement. Object explicitly rejects the Local record boundary and
keeps its independent physical deletion hold. Scoped review's alias finding is
fixed; restoring the unsafe alias privately fails the focused named guard.
Fresh fourteen-package replay passes 357 consumers, four actual controls/two
original wrappers and one named failure per SDK-only durable assertion mutant
in each family with matching runtime/archive SDK images. Safe-logger replay
checks 201 witnesses/211 origins and ten reopen edges. Full QC-03 remains open.

The preceding artifact197 scope also preserves the Local concurrent read/
reconciliation quarantine race and all six committed-detection parameters.
Public recovery rows supply genuine selected stamps checked against exact
ticket/store/identity before existing typed damage/restoration controls run.
Awaited common overloads retain synchronous wrappers and every assertion.
Fresh fourteen-package replay passes 353 selected consumers; both seven-row
families pass, and SDK-only race/detection mutants produce one/six named
failures per family with matching SDK/archive images. Safe-logger replay
checks 197 witnesses/205 origins and eight reopen edges. Local open/publication
retain compatible reopen, not Object or Local reconciliation. Full QC-03 and
feature acceptance remain unfinished.

The preceding artifact190 scope adds all eighteen original admission rows through
genuinely uninitialized owned stores, not stopped initialized ones. Closed
typed probes change only the selected capability or actual authority scope;
raw root/readiness observations remain provider facts. Ordinary creation still
initializes. Original default/configured limits and actual settlement are
preserved. Fresh fourteen-package replay passes 346 selected consumers; both
eighteen-row families pass, with SDK-only no-I/O/range mutants producing
sixteen/two named failures per family and matching SDK/archive images.
Safe-logger replay admits 190 witnesses/196 origins and all six reopen edges.
Scoped architecture review finds no actionable issues, not final T081.

Exact `f4e53b4`/run40297863544 now passes all three Linux jobs and 343 native
foundations without failures/errors/skips. Independent admission includes
artifact166 and metadata QC-02 pairing: 93 Passed/0 Incomplete/9 NotApplicable/
0 Failed. The overall report is still `Incomplete`, qualification false;
artifact190, full QC-03 and feature acceptance remain unfinished.

Its initial SDK checkpoint has 53 executable metadata methods, typed sessions,
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
62 scopes/510 observations. It passed at `631f9c4`, run `40118166329`,
all three jobs and 174 foundations, not complete binding/category/session proof.
Four original result-handoff/expiry bodies now also run common checks with all
twelve frozen parameters. Actual completion/release observers, barriers, clock
and settlement remain fixture-side. Hiding a genuinely reserved ticket after
cancellation fails the unchanged success assertion on both providers; publishing
that same ticket corroborates the intended ownership fault and genuine stores
pass unchanged. The next fourteen-row native scope requests
63 scopes/524 observations, pending, not full qualification.
The remaining six original budget bodies also use shared checks with sixteen
frozen parameters, covering failed unclaimed cleanup/retry, terminal cancelled
publication, queue/capacity, authority deadlines and cooperative cancellation.
Actual controls, limits, settlement/stop and authority setup stay fixture-side;
shared authority checks use only Abstractions. A genuine input-limit failure
mislabeled as capacity fails the unchanged expected-code assertion; genuine
stores pass. The next eighteen-row native request is 64 scopes/542 observations.
It passed at `70dfdf6`, run `40119412481`, all three jobs and 176 foundations,
including the fourteen-row handoff scope, not complete qualification.
Six original authority bodies now also use shared interface-only checks,
preserving three frozen witnesses, three additional existing facts and the
copied-guard helper. Actual authority creation, clock, waiting/retained counters,
reference completion and drain remain fixture-side. Repairing an actual copied-
handle rejection through genuine recognized retention fails the unchanged
failure-type assertion; genuine authority passes. The next seven-row native
request passed at `7ee1c61`, run `40120167356`, all three jobs,
177 foundations and 65 scopes/549 observations. Handoff run `40118782562` was
canceled while pending, not admitted; later expanded requests retain that scope.
Both original capability bodies now run shared interface-only checks, with
sixteen frozen gap parameters and two additional existing complete profiles.
Actual injection, construction, filesystem/readiness observation and private-root cleanup
remain fixture-side. Original rejection-before-I/O, readiness, configured
limits, optional ranges, SHA-512 and stop checks remain unchanged.
The eighteen-row native scope passed at `2a7be14`, run `40120937967`,
all three jobs, 178 foundations and 66 scopes/567 observations, not full
qualification.
Four original metadata/artifact integration bodies now also use shared checks
with sixteen frozen parameters over all four SQLite/Memory and Local/
ObjectSemantics combinations. Actual composition, proof encoding, waiting
counters, M1 controls and physical settlement stay fixture-side. An actual
reference-denial result mislabeled as conflict fails the unchanged expected-
code assertion in every combination; genuine stores pass unchanged.
The twenty-row native request passed at `4c87667`, run `40121897879`,
all three jobs, 179 foundations and 67 scopes/587 observations, not full
bindings/category/session or authority-integration task acceptance.
Three original metadata-bridge bodies now use shared interface-only checks.
The mismatched-authority witness is frozen; exact-evidence and invalid-evidence
facts are additional existing cases. Actual host bridge/controlled validator,
encoding, expiry and observed counters remain fixture-side; the validator's
recognized-reference operation/stamp checks delegate unchanged to the SDK.
The bridge-only native request was canceled while pending; its three rows are
included in the expanded lifecycle request, not separately accepted.
These host-bridge unit checks are not full provider/category qualification.
Three remaining original lifecycle bodies now use interface-only common checks:
retained reference-query shutdown, concurrent close/slow guard release and held
native I/O deadline/stop. Four parameters are frozen; two composed-shutdown
cases are additional existing facts. Actual composition, query drain, slow
guard implementation, physical holds/releases and settlement stay fixture-side.
The next six-row request is 69 scopes/596 observations, pending, not complete
bindings/category/session or full profile qualification.
That lifecycle request passed `40123477371` at `f2cc84d`, all three jobs,
181 foundations and 69 scopes/596 observations, including the three bridge and
six lifecycle rows plus actual prerequisites/replay. The canceled bridge-only
run is not separately accepted.
Two original storage-failure/reconciliation bodies now also share fixed
classification, sanitizer, borrowed-source, committed-byte and receipt checks
with four frozen parameters. Actual post-visibility fault registration remains
fixture-side. Real access-denied failures relabeled as unavailable fail the
unchanged common code assertion on both providers; genuine stores pass.
The next six-row request is 70 scopes/602 observations, pending, not complete
bindings/category/session or full profile qualification.

Four-way integration passed `40121897879` at `4c87667`, all three jobs,
179 foundations and 67 scopes/587 observations including twenty integration
rows and all actual prerequisites/replay. These are still diagnostic counts,
not the 179 applicable category results.
Three original prefix-cleanup bodies now also share all six frozen parameters
and unchanged stop/reopen assertions. Actual permissions, observer controls,
filesystem/readiness snapshots and Local-only durable reopen remain
fixture-side. The next six-row native request is 71 scopes/608 observations,
pending, not full binding/session/category/profile qualification.
Both remaining original object-cleanup bodies now also share five frozen
parameters and unchanged selected-object/owner/reclamation checks. Actual Unix
permissions, observers, filesystem snapshots/lengths and worker settlement
remain fixture-side. Private hook names map to the existing logical during/
after-assembly input, not provider-selected expected results. The next five-row
request is 72 scopes/613 observations, pending. Original failure-body extraction
does not complete T027/T030 or full binding/session/category/profile gates.

Storage-failure passed `40124374635` at `ff50acd`, all three jobs,
182 foundations and 70 scopes/602 observations, all six new rows and actual
prerequisites/replay, not full category/profile qualification.
Configured publication, compatible reopen and fresh-epoch artifact operations
now also share interface-only checks. Actual host construction/DI/configuration,
mapping, module identity/readiness, disabled-root checks, restart/stop and
missing-guarantee inert-start rejection remain fixture-side. No Hosting/Core
dependency enters the SDK. The next four-row request preserves all frozen host
cases passed at `9ce6b25`, run `40127065375`: all three jobs, 185 foundations
and 73 scopes/617 observations, not full binding/category/profile qualification.

Owned artifact sessions now have an authority-quiescence prerequisite: an
explicit closing fence rejects new acquisitions while retaining existing handles
and queued work until every recognized guard and retained reference query settles.
Reopen cannot reuse a completed prior-generation settlement. Both binding
packages source-link that same fixture authority as internal types, preserving
their SDK/own-provider-only dependencies instead of importing HostAdapters,
Hosting or the other provider. No complete binding/fault-control admission or
physical release is claimed. Three common checks requested 74 scopes/620
observations; run `40128473761` failed before authority discovery because its
scope lacked the original-artifact routing prefix. That routing is corrected;
the failed run is not admitted. Two independent package builds reproduce both private
authority archives and exercise actual retained-guard/reopen behavior.

`LocalArtifactAssertionSessions` is a partial assertion projection, not an
`IArtifactConformanceBinding` or complete fault driver. It constructs the real
Local store beneath an allocator-owned child, registers scoped typed observers,
reopens with the same identity/authority, and joins actual stop, callback work
and fenced authority before settling ownership. Disposing a stale session cannot
release its replacement. Retry reuses a pending allocator observation and the
same actual task; observer failures remain faulted after physical joins rather
than becoming successful cleanup. It never deletes roots or reports `Released`.
Both providers separately track release-callback settlement from public
operation admission, preserving inherited cancellation/handoff/capacity checks.
Fifteen package-only Local cases and two common Local/Object callback cases
pass. All seventeen typed observers can coexist: closed supported-name sets
already impose a finite bound, so the contradictory sixteen-callback ceiling
is removed on both fixtures.

Object now has distinct actual receipt-recorded, read-opened and reconciliation
before/verified hooks. Receipt notification follows the actual receipt mutation;
opened-read notification remains inside stream/guard/transfer cleanup ownership;
verified notification follows actual content verification. Six common Local/
Object checks retain real receipt equality, reclaim resources after callback
failure with one transfer slot and recover actual uncertain publication after
verified-callback failure. The deletion fixture explicitly supplies a successful
zero-reference decision; the default authority correctly denies unproven deletion.
These hooks are prerequisites, not a complete fault driver.

`ObjectArtifactAssertionSessions` now supplies the corresponding partial owned
projection. Both artifact binding packages compile one internal source-linked
ownership/session coordinator; actual provider construction, readiness, worker
joins and private boundary mappings remain separate. There are no new package
dependencies on the other provider, Hosting or HostAdapters.
Local reopen preserves identity/authority/content. Object logical restart joins
the old store and authority, then uses a new empty child and fresh epoch/authority
under the same allocation. Old sessions retain immutable identity/authority;
failed or canceled replacement generations stay tracked until original-handle
cleanup. This is simulation, never Local recovery or a durability exclusion
substitute. `CleanupCandidate` maps Object's actual per-target `multipart.cleanup`
transition, not its synchronous history-index callback. Sixteen package-only
Object cases and the unchanged fifteen Local cases exercise these surfaces.

Run `40131392286` at `88c5d01` passed foundations/lock replay but failed
pre-runtime with `ProofMismatch`; it is not admitted. Input enumeration now
hashes consumed managed/runtime images, active-architecture native assets and
all locks under unchanged bounds, retaining full-tree symlink/type/race checks.
Replacement run `40133457888` at exact `c58978e` passed all three jobs,
191 foundations without skips and strict 76-scope/643-observation admission.
The earlier failed run remains unadmitted. The owned-Object increment passed
`40134767571` at exact `36481c0`: all three jobs, 192 foundations without skips
and strict 77-scope/659-observation admission. Neither partial projection admits
a full artifact binding/category/profile.

Both factories also accept explicit `ArtifactAssertionOptions`: immutable actual
`ArtifactLimits` and a live typed reference query. Each actual initialization,
including compatible/fresh reopen, receives those limits; authority generations
invoke the source for the exact protected stamp rather than caching a prior
decision. `ArtifactReferenceObservation` contains availability/count/revision,
not a pass flag, and rejects negative counts, unavailable nonzero counts and
available results without revisions. Null queries retain default fail-closed
deletion; unavailable zero-reference observations cannot authorize deletion.
Four held-query cases prove that caller timeout does not settle real query work
or let reopen/final cleanup finish early. Eleven configured rows pass alongside
the existing thirty-one owned rows. This is test-fixture setup, not product
configuration or complete fault-driver/metadata integration acceptance.
Run `40136186008` at exact `853c669` passed all three jobs, 193 foundations
without skips and strict 78-scope/670-observation admission.

The partial sessions also expose exact-stamp payload damage. Local admits the
physical mutation through its own `ExecuteAsync`; Object uses its independent
`OwnedAsync`. Neither moves native file operations into the SDK/binding nor
changes receipt/quarantine state to fabricate public corruption detection.
An actual open-file boundary is observed inside that owned work. All observers,
native disposal and final callbacks must settle before reopen/root cleanup;
caller cancellation alone cannot release them. Truncating an empty payload
fails explicitly; byte damage changes the first byte, or adds one to an empty
payload. Foreign stamps, stale sessions/epochs and removed incarnations cannot
damage the current replacement. Twenty-three cases cover actual copy/quarantine,
held work, failed observers, conflicting reads and these boundaries.
Payload run `40137341231` at exact `1367a51` passed all three jobs,
194 foundations without skips and strict 79-scope/693-observation admission.
The frozen four-parameter damaged-read case also now executes the same
provider-free consumer on both implementations, preserving exact assertions
and operation order. Actual file capture/damage/restoration remain in the
legacy fixture; this does not convert those callbacks into owned full-driver
admission. A real validator's actual corrupt-evidence denial, deliberately
reported as success, fails the unchanged common assertion on both providers;
fresh genuine validators pass. Run `40138438076` at exact `4a907c5` passed all
three jobs, 195 foundations without skips and strict 80-scope/699-observation
admission, not complete fault-driver/category/profile admission.
The original Local read/reconciliation quarantine race and both admitted-open
revalidation rows also now execute provider-free consumers. Actual publication
faults, provider-specific observation mapping, physical replacement and named
hold/release barriers remain fixture-side at their original transition points.
Common code contains no Local/Object switch, filesystem I/O or substitute
expected outcome. Exact checks/public-operation order remain unchanged.
Run `40139402208` at exact `f05851a` passed all three jobs, 196 foundations
without skips and strict 81-scope/702-observation diagnostic admission.
All six original committed-detection parameters also execute one provider-free
consumer with mechanically identical checks and public-operation order.
The independent frozen test variant supplies its inherited durability
expectation; provider-advertised capabilities or binding-selected outcomes
cannot weaken the expected receipt/reconciliation checks. Physical removal,
restoration and publication fault mapping remain fixture-side.
Run `40140436330` at exact `e089042` passed all three jobs, 197 foundations
without skips and strict 82-scope/708-observation diagnostic admission.
Transitive review corrected omitted Local quarantine stop/reopen checks in
the damaged-read, committed-detection and corrupt-existing consumers. The
shared helper now retains every original lifecycle operation and assertion;
a typed context carries only the original public lifetime/identity/authority
and fixture-side fresh-store construction. The fixed original Local variant
supplies that context; Object supplies none and gains no durable-restart claim.
Three real reopened-store mutation pairs require actual corrupt-read denial
before changing its code, fail the unchanged common assertion, and pass with
genuine stores. A frozen transitive-body/owner guard rejects helper or wrapper
omissions. Earlier helper-normalization parity claims did not establish these
durable checks. Run `40141545447` failed closed with `UnknownDiagnostic` in the
new quarantine scope and is not admitted. Actual method-level discovery
reproduced fifteen rows against its Local-only nine-row declaration. The scope
now declares all twelve frozen provider parameters plus three mutation rows;
prelaunch admission rejects partial method expansion instead of relaxing the
logger. Object's logical rows do not establish durable restart.
All nine remaining original evidence-validation parameters now execute
provider-free common consumers. Complete-body comparison preserves every
original assertion, public-operation order and source/guard lifetime, including
retained ownership after denied quarantine persistence, stop retry and real
durable reopen, validation-first restoration, replacement incarnation and
original receipt, and intact content after access denial/unavailability.
Physical permissions/removal/restoration and actual native readiness observation
remain fixture-side legacy controls, not full owned fault-driver admission.
Exact new transport requires all nine original identities; the nine-row request
passed run `40143552793` at `c1d2a6b`: all three jobs, 200 foundations and
84 scopes/732 observations, including the corrected fifteen-row quarantine
scope, not full qualification. Every quarantine
caller must explicitly supply its durable context or select logical-only
scope; there is no defaulted reopen parameter.

Six original recovery methods now share provider-free assertions across all
twelve Local/Object parameters (eight frozen category witnesses and four
additional existing cases): concurrent cursor capacity/retirement and
expiry, changed inventory, ownerless ticket expiry, finalized noncommit,
staging-generation fencing and observation without deletion authority.
The wrapper retains its original fixed consistency expectation, clock and
driver lifetime; provider-advertised capabilities do not select expectations.
Fresh preparation/replay passes 311 artifact and 65 Consumer cases.
Run `40144435943` at `ffec99a` passed all three jobs, 201 foundations and
85 scopes/744 observations, not qualification.

Five additional recovery methods now share admitted-reconciliation/deletion
history, replacement-generation races and progressing-commit checks on ten
parameters (six frozen witnesses and four additional existing cases).
Common checks own the unchanged original managed barrier at its original
source/barrier lifetime position. Physical fault registration stays fixture-side.
Fresh independent replay passes 311 artifact and 65 Consumer cases.
Run `40145322908` at `9d19bd1` passed all three jobs, 203 foundations and
86 scopes/754 observations, not qualification.

All remaining original recovery bodies now forward shared checks: retained
object stop, committed-decision rollback/reopen and durable-receipt staging
release/reopen. One frozen witness and two additional existing Local facts retain
actual independent implementations, 105 retired incarnations, public readback,
original stop/retry and source lifetimes. Physical permissions, fresh Local
construction, record-write registration and cleanup authorization stay
fixture-side; Object gains no durable-reopen claim.
Fresh independent replay passes 311 artifact and 65 Consumer cases.
Run `40146117625` at `994f9fb` passed all three jobs, 204 foundations and
87 scopes/757 observations, not qualification.

Six original admission methods now forward eleven identities (four frozen
witnesses and seven additional existing cases) to provider-free checks.
Common consumers retain original deadlines, live initialization ownership,
exclusive create, missing/foreign/corrupt-root non-reset, fixed original
Local/Object reopen expectations and symlink sentinel/child checks.
Actual construction, fault registration, manifest/sentinel I/O, symlink
try/finally and root-cleanup permission stay fixture-side. The two native
concurrency/cross-process tests and complete child ownership helper are unchanged.
Fresh independent replay passes 311 artifact and 65 Consumer cases; the next
native request `40146850203` was canceled without jobs, not admitted; the latest
expanded request retains all eleven admission identities.

Both remaining original deletion bodies now share all four frozen parameters:
lost delete acknowledgment retains pending physical reclamation through exact
cleanup/receipt settlement, and live or unavailable reference authority denies
removal without harming public bytes. Common checks own every expected
code/receipt/size; actual observer registration and reference controls remain
fixture-side. Fresh independent replay passes 311 artifact and 65 Consumer cases;
native run `40147381011` at `992b4a5` passed all three jobs, 206 foundations
and 89 scopes/772 exact discoveries/executions with all actual prerequisites.

The owned projections now expose a distinct `DirectVerification` observation:
Local's optional `publish.direct` precedes its original direct validation on
both new and duplicate publication; Object uses its existing `object.direct`.
Selection, verification and independently readable acknowledgment are not
interchangeable. Four common rows hold actual publication before acknowledgment,
then check outcome, same-incarnation duplicate reuse, borrowed source and public
bytes after genuine settlement. No provider mechanism is shared or replaced,
and this does not yet admit full fault drivers/bindings. Fresh independent replay
passes 311 artifact and 69 Consumer cases. Native run `40148199370` at
`6d1f73b` passed all three jobs, 207 foundations and 90 scopes/776 exact
discoveries/executions with every actual prerequisite, not full qualification.

`InjectCapacityFailureAsync` returns an owned, counted scope that throws a fixed
ENOSPC-shaped `IOException` at Local's actual `stage.prefix` or Object's actual
`multipart.part`, after the real prefix write. It is injected storage failure,
not physical disk exhaustion. Only the exact internally created exception for
that registration bypasses observer-failure recording; unexpected observer
exceptions, including another ENOSPC-shaped exception, still poison the same
final settlement task. Scope disposal cannot remove a newer registration.
Common checks exercise repeated failures, exact not-committed reconciliation,
borrowed sources, replacement scopes and actual publication/readback after
repair. Package-only tests constrain staging capacity to one full ticket and
observe genuine successful versus faulted final settlement on both providers.
Fresh preparations pass 311 artifact and 73 Consumer cases. Native run
`40148998281` at `53b1433` passed all three jobs, 208 foundations and
91 scopes/780 exact discoveries/executions with every actual prerequisite.
This is diagnostic evidence, not full fault-driver admission.

`InjectUnclaimedCleanupFailureAsync` targets the existing actual indexed
undelivered-result reclaim seam, not prefix/object permission failures. A real
reservation or read-open completes behind a managed barrier; cancellation rejects
delivery, and the injected reclaim failure preserves its genuine cleanup index.
Common checks require one actual failed reclaim, fenced readiness/admission,
failed stop with retained ownership and a second actual failed reclaim. Removing
the scope permits the real stop cleanup retry and successful final settlement,
without clearing observer errors or replacing settlement promises. Four new rows
pass on both providers; fresh replay covers 311 artifact and 77 Consumer cases.
Native run `40149692533` at `1acdeb0` passed all three jobs, 209 foundations
and 92 scopes/784 exact discoveries/executions, not qualification.

`HoldSynchronousStorageAsync` controls Local's existing `BeforeRecordWrite` or
Object's existing `BeforeObjectDelete`. Reserve the delete ticket before arming,
and explicitly configure available reference authority; the default partial
projection correctly denies deletion without it. A counted synchronous hold
ignores operation cancellation, has a fifteen-second fail-closed watchdog and
requires explicit release. Disposal disarms only its own registration and joins
actual workers; stale disposal cannot remove a replacement. Ownership teardown
removes remaining controls only after provider stop and worker settlement.
Common checks require real deadline/uncertain caller return with retained work,
fenced admission/readiness, genuine authority exclusion, failed stop while held
and actual successful stop after release. This is a synchronous fixture-boundary
hold, not a stalled filesystem syscall or a replacement for original owned-child
containment. Fresh replay covers 311 artifact and 79 Consumer cases;
native run `40150871211` at `f68812e` passed all three jobs, 210 foundations
and 93 scopes/786 exact discoveries/executions, not qualification.

`LocalBinding` and `ObjectSemanticsBinding` now implement the full typed artifact
factory/session boundary over their actual independent stores, validators,
maintenance/lifetimes and authority. All ten mandatory controls are executable:
publication-selected/direct-verification/receipt/verified-generation gates,
exact-stamp physical damage, scoped capacity/indexed cleanup failures, synchronous
fixture holds and genuine borrowed source/sink streams. The generation check
performs actual expired-owner maintenance cleanup before re-staging and proves
old descriptors/cleanup cannot affect the replacement. Damage explicitly targets
the first of two artifacts, rejects a foreign incarnation and preserves the other.
Source/sink release only unblocks actual I/O; it never substitutes a provider result.
Caller-owned stream disposal follows actual provider settlement.

Releases share an in-progress task but do not hold the registry semaphore while
joining workers. A two-provider regression first reproduced the architecture
review's cross-control release deadlock, then passed with independent release and
rearming. Native settlement is observed before stable scope disposal, so a join
timeout does not permanently cache a failed disposal task. Actual full-session
origin capture/reopen preserves Local identity/publication and gives the simulation
a fresh empty epoch. Twenty-four new package-only parameters pass; fresh replay
covers 311 artifact, 103 Consumer and 89+89 metadata cases. The next native request
passed as run `40153251707` at `f73a55a`: all three jobs, 211 foundations and
94 scopes/810 exact discoveries/executions, including every prerequisite.
Parent-origin ingestion, remaining category
parity/integration and complete profiles remain unfinished; this is not qualification.

Those 24 full-binding rows now emit 26 actual component origins, including the
two original/reopened pairs. The diagnostic parent independently binds all eight
roles to the respective adapter/provider runtime DLLs and package archive bytes,
admits those four images into the safe logger manifest and requires the exact
per-row origin count and binding descriptor. Missing runtime images reject before
launch. Local fresh-cache observation corroborates all 208 role/image/archive
matches and actual reopen lineage without persisting raw output. Origin-enabled
native run `40154183825` at `d1fd43d` passed all three jobs, 212 foundations
and 94 scopes/810 exact discoveries/executions with every prerequisite.
This does not complete other category/profile imports
or upgrade the simulation to durable recovery.

Six metadata-origin rows now use the actual independent Memory/SQLite factories
with unchanged shared capacity, writer-budget and publication-protection consumers.
Each of six origins binds all six actual roles to its own adapter/provider images
and archives; the safe logger admits those four images and the parent retains
SQLite environment admission and exact binding/count checks. Local fresh-cache
observation confirms 36 image/archive correspondences; fresh replay covers
311 artifact, 109 Consumer and 89+89 metadata cases. The expanded native request
passed as run `40155045988` at `9034153`: all three jobs, 214 foundations
and 95 scopes/816 exact discoveries/executions with every prerequisite.
Metadata reopen attribution and other
category/profile imports remain unfinished; no durable memory or category
qualification is claimed.

Two further metadata rows now execute provider-free compatible-reopen assertions:
actual grouped public readback, fresh store/fault instances, preserved epoch/
authority and stale-control rejection after stale disposal. Memory uses its actual
closed logical image, not durable restart. Both real reopen lineages are emitted
and strict ingestion requires two origins for each exact reopen witness. The
eight metadata rows yield ten actual origins/60 image/archive correspondences;
fresh replay passes 311 artifact, 111 Consumer and 89+89 metadata cases.
The expanded native request passed as run `40155922560` at `4548183`:
all three jobs, 214 foundations and 95 scopes/818 exact discoveries/executions
with every prerequisite. Complete category/profile qualification remains unfinished.

The observed metadata scope now also imports twenty actual rows using unchanged
entity/relationship, final-graph, independent-candidate, faulted-atomic-candidate,
grouped-read and lease overflow/fence/decision-expiry consumers. Both independent
factories execute the same consumers with real fault controls and the injected
clock. All 28 rows produce 30 actual origins/180 role/image/archive matches.
Fresh preparation/replay pass 311 artifact, 131 Consumer and 89+89 metadata cases;
its native request passed as run `40156840261` at `2beff54`: all three jobs,
214 foundations and 95 scopes/838 exact discoveries/executions with every prerequisite. These
standalone metadata authority checks are not shared artifact-authority integration,
durable Memory recovery or complete category/profile qualification.

Thirty more observed rows now import unchanged canonical identity, registry/
authorization partitioning, reference replacement/ABA/rollback, create/revision
races, reconciliation contention/I/O/acknowledgment/contributions/corrupt receipts
and both malformed-schema layouts. Layout checks start genuinely unprepared;
no common assertion or independent provider mechanism changes. All 58 metadata
rows emit 60 genuine origins/360 actual role/image/archive matches. Fresh
preparation/replay pass 311 artifact, 161 Consumer and 89+89 metadata cases;
its native request passed as run `40157571215` at `8fed412`: all three jobs,
214 foundations and 95 scopes/868 exact discoveries/executions with every prerequisite.
Metadata zero-reference revision ABA is not artifact-incarnation fencing or
shared-authority integration; full category/profile qualification remains open.

Eight observed schema rows now invoke unchanged upgrade, invalid-upgrade,
upgrade-exclusion and future/corrupt-schema consumers through actual legacy/
current factories. The transparent recorder captures underlying observed
sessions, not itself as a factory/component, and disposes an unreturned child on
capture failure. Parent admission requires each exact two/three/four-origin
lineage and rejects missing, extra or foreign descriptor origins. All 66 rows
emit 82 actual origins/492 role/image/archive matches; fresh preparation/replay
pass 311 artifact, 169 Consumer and 89+89 metadata cases. The next native request
is 215 foundations and 95 scopes/876 observations, not yet admitted. Memory
upgrades are logical; native backup/recovery and complete profiles remain separate.

Forty-two further rows invoke unchanged bounds/scopes, paging, time rollback,
cancellation/queue/exception mapping, ledger/diagnostic, publication, corruption,
admission and disposal consumers. Admission/budget cases start unprepared;
store-level disposal retains the enclosing session/resource owner. Origins are
captured while actual components are live and emitted only after assertions
succeed. Both real incomplete-cleanup cases retain work until barrier release
and genuine settlement; no timeout is promoted to Released. All 108 rows emit
124 actual origins/744 role/image/archive matches. Fresh preparation/replay pass
311 artifact, 211 Consumer and 89+89 metadata cases; the next native request is
215 foundations and 95 scopes/918 observations, not yet admitted or full
category/profile qualification.

Twenty-four further actual rows exercise six continuation-corruption shapes
(each across all six components), five supported query-dimension corruptions
and independent foreign-store epochs. Both stores in each epoch case are
genuinely prepared; strict admission requires both actual create origins.
All 132 rows emit 150 origins/900 role/image/archive matches. Fresh preparation/
replay pass 311 artifact, 235 Consumer and 89+89 metadata cases; the next native
request is 215 foundations and 95 scopes/942 observations, not yet admitted.
Schema run `40158238921` at `9399c3c` passed all three jobs, 215 foundations
without skips and 95 scopes/876 observations with every prerequisite. It
predates controls/cursor imports and is not complete category qualification.

The package-only Consumer now runs 32 exact actual authority-integration rows:
each SQLite/Memory and Local/Object combination exercises reference admission,
failed transactions, live references, lost acknowledgments, current-incarnation
ABA, protected readers, foreign/copied handles and shutdown holdings. The real
bridge and existing common assertion bodies are used, not synthetic standalone
metadata evidence. A stable separate close task joins authority admissions/
holdings, genuine metadata worker settlement and both actual disposals. The
existing unit owner observes that task before reclaiming its root; this is not
controller-authorized Released or category qualification. Original wrapper
disposal remains unchanged. Fresh preparation/replay pass 267 Consumer,
311 artifact and 89+89 metadata cases; fourteen consumed Hoard images match
their actual archives. The Consumer-only HostAdapters edge and its lock graph
are updated; SDK/Core dependency boundaries and historical locks are unchanged.
Bounded architecture review found no confirmed blocker. Controls native run
`40158951602` at `3fb2705` passed all three jobs, 215 foundations without skips
and 95 scopes/918 observations; the next request is 216 foundations and
96 scopes/974 observations, not yet admitted.

Isolated opt-in mutations now wrap the actual metadata and artifact stores.
Stale metadata replay fails unchanged
`MetadataTimeAssertions.TicketExpiryAndRollbackAsync`; actual premature artifact
publication fails unchanged `ArtifactPublicationAssertions.PrivateStagingAsync`.
Each faulty/corrected pair uses the same caller and common assertions across
both independent providers. Unexpected successful read sessions are disposed
before actual artifact-session shutdown. Fresh preparation/replay each produce
four named assertion failures and four corrected passes, with fourteen actual
Hoard image/archive matches and unchanged SDK/catalog/assertion bytes.
Intentional failures are excluded from ordinary builds. The next native request
is 218 foundations and 100 scopes/982 observations, not yet admitted or complete
T034/category qualification. No provider operation or SDK dependency changed.

The runtime package-family guard now also admits each exact paired inventory.
A launch-boundary regression first rejects all four valid scopes, then verifies
the actual generated filter/settings and independently hashed package files
after repair. Reduced, duplicate or cross-family selections still reject before
launch. Earlier mutation-head results are not admitted; provider operations,
common assertions and qualification requirements remain unchanged.

Cursor native run `40159593512` at `5c7522f` passed all three jobs,
215 foundations without skips and 95 scopes/942 exact observations with every
prerequisite. It does not verify authority integrations or category mutations.

An explicit `catalogBindingId` input assignment can project a known fixture
declaration into its frozen `sqlite`, `memory`, `local` or `object` catalog slot.
Parent capture verifies the exact category, original declaration ID and package,
preserving all raw declaration bytes/hashes and provider package attribution.
Foreign assignments and duplicate original declaration IDs reject, regardless
of JSON serialization; ordinary
declaration capture is unchanged. Actual factory/reopen observation and fresh
replay each verify four cases/eight origins and 56 role/image/archive matches,
not a complete category run or applicability/exclusion decision.
Authority native run `40160483040` at `eeaa6bf` passed all three jobs,
216 foundations without skips and 96 scopes/974 exact observations with every
prerequisite. It predates mutations and slot input wiring; the next request is
219 foundations and 100 scopes/982 observations, not yet admitted.

Full-binding batch ingestion now rejects reduced frozen witness inventories
and preserves shared execution/proof identities, append-only attempts and all
QC/controller obligations. Missing controls cannot become passing category
results; actual profile runners/evaluation remain unfinished.
Prelaunch manifest selection and import share the immutable primary-case map.
Synthetic positive-origin coverage rejects cross-binding execution-ID replay
without mutating accepted evidence; actual original-wrapper provenance remains
unfinished.
Run `40161613939 @abfa812` exposed a real `Assert.IsType()` logger-prefix gap.
Its bounded repair retains exact SDK-frame attribution and reproduces four
named failures/four corrected passes through the actual logger in independent
local observations. That failed run and canceled `40162771846 @c1f79b2` are not
admitted receipts. Replacement run `40164176338` at exact `2ecda7f` passed all
three jobs, 223 foundations without failures/errors/skips and 100 scopes/982
exact discoveries/executions with every prerequisite, including all mutation
scopes. It is admitted diagnostic evidence, not full category qualification or
evidence for later `90fd088`; the wrapper evidence-contract decision remains
separate from that receipt. The maintainer's autonomous-continuation instruction
now resolves it through independently catalogued original-instance,
loaded-contract and unchanged typed-session proof requirements.
The first original MP-01/AS-01/value-test instrumentation captures actual existing
owners and interfaces without replacing factory/resource ownership. Actual
observation and independent fresh-cache locked replay each pass six executions
and 26 image correspondences. These minimal-input local logger diagnostics do
not qualify full categories; wider original/reopen/controller coverage remains
unfinished.

The native diagnostic now also schedules five original-observation scopes
(eight executions), including both frozen artifact value witnesses rather than
only the auxiliary identity-bound test. Original and typed-binding inputs retain
separate immutable manifests and binding IDs, the same actual packages/source/
invocation group, and independent pre/post recomputation. Native execution of
this full-input path is not yet admitted. Local observation and fresh-cache
replay pass eight executions/28 role-image correspondences using minimal inputs,
not qualifying category evidence.
Original metadata coverage subsequently adds MP-02/03/13/23..27/31. The actual
facade passed to each unchanged common assertion is pinned and observed with
its original owner, never replaced by a companion SDK session. Local observation
and independent locked replay pass 26 executions/118 image correspondences.
Native admission must now cover 105 scopes/1,008 observations; wider originals,
direct/reopen/controller paths and qualifying profiles remain unfinished.
The publication expansion adds all twelve frozen original artifact publication
parameters, observing the existing driver's actual private lifetime and
interfaces without extra construction or ownership transfer. Minimal-input
local observation and independent locked replay pass 36 executions/188 image
correspondences. Its native requirement is 105 scopes/1,018 observations,
still pending. Earlier `40166560899 @8aaa36d` passed all three jobs,
227 native foundations and 100 scopes/982 observations with every prerequisite;
that admitted diagnostic receipt predates full-input original execution.
The following increment selects immutable role images per exact witness,
not one universal authority image per binding. Fifty-five single-owner metadata
identities per provider now capture genuine original references: the existing
fixture authority where no facade was passed, or the exact already-used facade.
No unused authority is created merely for evidence. Local observation/replay
pass 126 executions/638 image correspondences with minimal inputs, including
all query-corruption/continuation parameters and both direct-construction
admission witnesses. Exact one-observation admission also rejects extra roots.
The new native vector is 230 foundations and 105 scopes/1,108 observations,
pending. Multi-owner and reopen witnesses remain explicitly unclassified.
Earlier full-input `40167209164 @0005638` passed all three jobs,
229 foundations and 105 scopes/990 observations with distinct original/typed
input digests and every prerequisite. It admits the earlier eight-original
diagnostic only, not these expanded sources or qualifying profiles.
Genuine multi-owner and schema-reopen observation subsequently covers
62 operational metadata identities per provider. Independent source policy
selects each exact forest, not arbitrary extra roots. A sequence preserves
reference-equality aliases across independent roots while parent edges represent
only actual reopens. Schema observations capture the actual adapter owner and
its real underlying fixture authority; no unused facade is manufactured.
Local observation/replay pass 140 executions, 162 records and 818 image
correspondences with reproduced SDK archive
`032389ce6626072e1d3b455d1af77779e6656f46f5cba1187df3dbdf591922c1`.
Native admission now requires 231 foundations and 105 scopes/1,123 observations,
pending. Earlier `40168790991 @3f1409a` passed all three jobs, 230 foundations
and 105 scopes/1,082 observations with every prerequisite; it does not admit
the later forest increment or complete profiles.
The following increment observes both genuinely configured metadata module
owners, including rejected schema admission, and 38 more artifact parameters
through their existing driver. Metadata now covers 63 operational identities
per provider; artifacts cover 181 publication/deletion/reconciliation/read/race/
failure/budget/recovery/quarantine/rejection/lifecycle witnesses, including exact
fixed-binding facts and all frozen budget booleans. Nine actual Local fresh stores have
exact per-node images: original driver owner in the test assembly, reopened
owner/interfaces/controls in Local, and unchanged shared authority. Explicitly
passed empty controls are the real fresh store's controls, not companions.
In-place reinitialization preserves the same original object; reconciliation's
early return and Object cases have no fabricated fresh-store child.
Rejected admission/capability roots observe the actual source-created provider
stores and controls, not a driver facade. Decorated admission observes the exact
authority passed into the store, not its unused underlying authority. Fixed
facts retain their real parameter lists and independently frozen bindings.
Actual metadata-composed sessions and configured modules now own their real
artifact interfaces. Read-only test-fixture controls retain the exact objects
passed to store construction, without an SDK dependency or a second controls
object. Each successful configured-host parameter has two independent real
module/session roots, not an invented parent edge; SQLite-bearing integration
rows require actual SQLite environment admission.
No additional stores, factories or cleanup owners are created.
Eight actual value/qualification contracts per binding carry loaded-contract
proofs, not fabricated provider sessions. The partial observer is package-only:
ordinary predecessor contract tests still have no SDK dependency.
Four provider-neutral authority/bridge facts and both rejected-module parameters
now require closed `original-owner` proof: only the genuine existing owner,
never a fabricated session, provider interface or control. Pure facts run in
explicit Local/Object contexts without invented provider arguments. The copied
handle fact observes both independent authorities; rejected modules never expose
a session. Owner-only evidence cannot replace any full session-role policy.
Local observation/replay pass 333 executions, 370 records
(354 original owners/sixteen contracts) and 2,122 image correspondences with the
extended private-evidence SDK archive. The external-wrapper scope now separately
admits all sixteen controller/transfer producer packets and links their hashes
to the actual runtime execution/proof and current input document. Real kill/
state/readback and both retained-work phases are checked; transfer packets must
also match the same-run parent measurement receipt. This is no replacement for
loaded-provider provenance, owned-controller/category acceptance or qualification.
Native admission requires 236 foundations and
107 scopes/1,317 observations, pending. Controllers, remaining artifact lifetimes
and complete qualifying profiles are still unfinished.

Object cleanup passed `40126135553` at `3de87aa`, all three jobs,
184 foundations and 72 scopes/613 observations, all five object-cleanup rows and
actual prerequisites/replay, not full category/profile qualification.

Prefix cleanup passed `40125248164` at `871e3a8`, all three jobs,
183 foundations and 71 scopes/608 observations, all six cleanup/stop/reopen rows
and actual prerequisites/replay, not full category/profile qualification.

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
