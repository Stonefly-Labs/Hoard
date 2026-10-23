# Implementation Plan: Provider Conformance, Compatibility and Composition

**Branch**: `feature/007-provider-conformance` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-provider-conformance/spec.md`

**Status**: The authorized implementation continues `implement / running`, with
the resolved CP-11 timing clarification recorded below. No completed harness, shared
assertion extraction, five-profile workflow, custom checklist approval or qualification
result is delivered. Public product contracts and required outcomes remain
unchanged; necessary fixture-private controls are extended as recorded below.

## Foundation continuation

The maintainer's subsequent instruction to make decisions and keep implementing
resolves the earlier pause. Necessary fixture-private controls are being
implemented rather than weakening assertions. Memory now stores bounded private
record/receipt encodings within its independent immutable copy-on-write state,
validates corruption through real public read/reconcile/replay paths, and
exposes bounded targeted capture/replacement controls. No SDK dependency,
private state type, SQLite delegation, public operation signature change or
provider-returned pass flag was introduced. The package-only tests exercised
five record shapes and fourteen receipt/ledger shapes, original-ticket
classification, unchanged damaged state, independent effects and restoration.
Nine SDK/package checks passed after a separate fresh-cache locked restore.
T003's fixture-private seam wording is updated to reflect this necessary
implementation decision; mandatory outcomes and reviewer-owned markers remain.

Witness ingestion now requires expected binding/matrix dimensions. Two
dimension-only mutations were observed failing before the fix and pass after
rejection was added. Baseline verification recomputes all six sealed source,
recipe, lock, binary and package inventories/hashes before reuse, including the
distinct F-06 artifact feed. The original private preparation seal verified
unchanged; it remains non-qualifying.

Initial executor corrections guard post-spawn registration, constrain inherited
environment, propagate termination control deadlines and perform synthetic
cleanup in an identity-checked, bounded helper before marking release.
Linux x64/arm64 child bootstraps install inherited kernel filters that prevent
session/group and namespace escapes before executing a test program.
The controller requires a two-way startup handshake: the target remains blocked
until identity/ledger registration and kernel PID-handle group signalling
admission succeed. Group termination uses the stable kernel handle, not a
numeric PID that could be reused. Linux identity also records kernel start ticks
rather than second-resolution `ps` start times. The group-handle prerequisite
requires Linux 6.9 or later support and is probed, not inferred from a version
label. Native regressions
must run without skips on Linux; macOS cannot provide the required generic
containment and therefore returns `PrerequisiteMissing`, not a qualified result
or case exclusion. Existing predecessor tooling is unaffected by this admission
restriction. A least-privilege Ubuntu foundation workflow runs sanitized
non-qualifying regressions; it is not the planned five-profile baseline.

The historical checkpoint and unresolved review inventory below explain the
earlier pause. Native foundation run
[39901637391](https://github.com/Stonefly-Labs/Hoard/actions/runs/39901637391)
passed 23 checks without skips and measured 92,112,142,336 free scratch bytes.
Subsequent run
[39904414231](https://github.com/Stonefly-Labs/Hoard/actions/runs/39904414231)
observed exactly the two intended missing-handle admission failures before
the handshake/handle correction. The repair passed 26 native checks without
skips in
[39906330789](https://github.com/Stonefly-Labs/Hoard/actions/runs/39906330789).
The next native challenge,
[39906992231](https://github.com/Stonefly-Labs/Hoard/actions/runs/39906992231),
failed exactly the diagnostic-parent directory replacement case. Its correction
anchors ledger/diagnostic/cleanup operations to verified directory descriptors
and records original child-directory device/inode identities. Same-name directory
replacement is rejected before child launch; cleanup depth and entries are
bounded. The correction passed 28 native checks without skips in
[39908082714](https://github.com/Stonefly-Labs/Hoard/actions/runs/39908082714).
Earlier retained private
ledgers lack these directory identities and are not admitted for ordinary
resume/cleanup under the new format.
The unchanged inherited metadata suite also passed 72 tests against candidate
Memory bytes; this is a focused regression, not category qualification.
Subsequent repairs remain subject to full challenge coverage and final
architecture review before qualification.

### Current SDK/evidence checkpoint and timing clarification

The test-only SDK now includes a native identity-pinned resource allocator,
validated cleanup/fault observations and a real bounded VSTest logger with
private input/owner manifests and hashed runtime proofs. SDK settlement never
deletes resources or reports authoritative `Released`. Complete controller
ingestion and actual loaded-provider proofs are not yet implemented.
Strict model admission binds input/package/binding/baseline/runtime inventories,
actual execution UUIDs, append-only attempts, exact dimensions and monotonic
attempt/witness intervals. Finite VSTest scaffolding is projected without raw
console/TRX persistence. Composition and version fixtures use existing Hosting
validation; they are focused foundations, not complete profile coverage.

Observed checks: 141 portable tooling tests discovered (132 passed, nine native
skips on macOS); 39 source SDK tests passed; 41 tests passed against freshly
packed SDK/logger packages after independent fresh-cache locked replay.
Package-only logger smoke locks also replayed and built. The focused new
composition/version suites passed 142 tests. A broad direct integration run
passed 646 and failed five preparation-dependent evidence checks: required
foundation/configuration/discovery inputs were absent. No complete predecessor
acceptance is claimed. Formatting/catalog checks passed. A bounded SDK/logger
architecture review reported no confirmed architectural violations, with Linux
allocator execution and loaded-provider proof integration still unproven;
it is not final T081 review.

**Resolved under autonomous-continuation direction:** CP-11 and FR-007 formerly
required actual route conflicts to reject before provider construction, while the existing
Hosting contract learns routes only through constructed modules' `MapEndpoints`.
The actual `AmbiguousRoute` check therefore runs at route composition, before
publication/readiness. Owner-scoped endpoint responsibility IDs do not encode
routes; malformed/duplicate-ID tests are not CP-11 proof and are labelled
`endpoint-declaration` instead. Preconstructing modules just to inspect their
routes would itself violate the requested boundary.

The maintainer directed continued autonomous resolution rather than another
pause. Preserve existing public APIs and explicitly correct CP-11/FR-007/US2.2/
QC-14/T042 to the actual mapping boundary before publication, initialization,
readiness and admission. The real ambiguity/repair test observes that boundary;
it never claims zero construction or substitutes malformed IDs for routes.
Public product behavior is unchanged; no route-declaration redesign was added.
Reviewer-owned CHK014 text/markers remain untouched and are not self-approved.
Complete profile evidence remains required before task completion.

### Runtime ingestion and native SDK diagnostic increment

T001/T006 are complete: the frozen pre-extraction inventory includes all six
historical revisions, and strict model tests exercise required fields and
unknown extensions across every data-model entity as well as bounds, immutable
expectations, status/schema and relationship mutations. No runtime pass is
imported from that inventory.

`ingest_runtime_attempt` now validates actual safe-logger JSONL, proof and
completion bytes against immutable run inputs, trusted manifest/owner hashes,
independent expected identities/dimensions and parent monotonic intervals.
Assertion, unknown, skipped and interrupted outcomes remain distinct; completion
counts/flags cannot replace missing observations. Actual loaded-provider proof
and complete profile orchestration remain outstanding.

Proof traversal rejects symlinked roots/ancestors and special files, is anchored
to directory descriptors, and enforces finite file/byte/depth/time bounds.
A native SDK diagnostic workflow now prepares/seals/verifies all six baselines
before compiling candidates, explicitly labels isolated local-archive lock
preparation, independently replays locks and exercises fixed SDK/logger cases.
Its result is pending real Linux execution; unit mocks or portable passes do
not establish that evidence. All diagnostics remain `qualification: false`.

Linux historical locked restoration subsequently exposed different compiled
archive bytes from the macOS-prepared pins. A build-runtime pin did not change
those fingerprints. Explicit historical preparation now creates alternate
private locks, preserving every original source lock, dependency/version and
third-party hash. Private seal schema `2` records the recipe/actual archive
derivation; strict old schema-`1` seals remain supported unchanged. Public
evidence schema/catalog versions do not change. Independent verification
recomputes each derivation rather than accepting rehashed graph changes.
This is preparation before candidate compilation, not baseline substitution
during execution. Native diagnostic run `39913608773` at `53c3857` passed:
six baselines were sealed before candidate compilation, all six allocator facts
and five logger smoke scenarios produced the expected observations, and inputs/
baselines reverified afterwards. Its independent Python job passed 61 checks
without failures/errors/skips. Baseline seal:
`41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`.
No provider/profile qualification is inferred.

The catalog's 144 distinct composition/version/classification runtime identities
now match actual bounded package-mode discovery, including all seven mandatory
package-only composition identities. Canonical matrix keys remain unchanged;
separate reject/repair dimensions still require separately attributed executions,
not borrowed witnesses. A tracked conditional composition lock was deliberately
prepared against the already sealed F-06 feed and successfully restored in a
second empty cache before building/discovering the consumer. No predecessor lock
changed, and no behavior pass or current candidate-provider qualification is
inferred from discovery.

The inherited classification rows require brackets, parentheses and commas in
quoted version parameters. Three intended logger failures and three Python
admission failures demonstrated the previous grammar limitation. Both admission
layers now preserve those bounded ASCII characters without allowing paths,
embedded quotes, whitespace or control characters inside parameter strings.
Source SDK tests pass 45 checks; Linux diagnostic run `39916071298` at `4678eb8`
passed all seven scenarios/15 observations, including the three actual
range-parameter cases. It reproduced the same six-baseline seal and bound input
digest `a807dba086c63476d9b440a0621f0cf7cded31b194a0dae1b7312a8422127a10`.
This does not infer all 45 SDK tests ran natively. Embedded SDK
catalog generation matches the independent expansion. Remaining control mappings,
loaded-provider attribution and complete profile evaluation keep T008 unchecked.

### Evidence-preserving cleanup increment

An intended failure reproduced deletion of retained proof/diagnostic bytes by
cleanup. Another reproduced a live child remaining merely `Settling` instead
of recording retained ownership. Cleanup now deletes only the three
identity-checked synthetic directories (`stores`, `feed`, `cache`), never the
evidence root, proofs, safe diagnostics or runtime records. A private schema-`2`
ownership ledger atomically publishes state and bounded append-only cleanup
observations. Publication failure cannot make in-memory ownership `Released`.
Only actual exit and completed synthetic deletion admit release; explicit
`Retained -> Settling` retry preserves prior failure observations.

The controller can project immutable path-free `ResourceOwnership` records,
including actual still-live PID/start identities. No-live-child projection uses
PID zero and an all-zero digest, not an invented execution identity. Portable
focused checks passed 70 tests with ten Linux-native skips; native foundation
job `120293251935` in run `39917215214` at `bc27614` then passed all 70 with zero
failures/errors/skips, measuring 92,111,507,456 free scratch bytes. Its SDK/logger
job also passed. T010 is complete. Existing SDK diagnostics intentionally retain
baseline/input bytes and remain `Settling`; they do not claim full-run cleanup
or promote the new projection into qualification. Callers must retain required
input/proof bytes outside synthetic deletion directories before full cleanup.
The downstream profile/controller gates remain unchecked pending their
complete verification. An actual atomic-rename failure additionally exposed a
stale staged ledger blocking retained-state publication. Failed publication now
removes only its own identity-checked temporary marker; a pre-existing foreign
marker is never removed or overwritten. All 175 tooling tests pass with ten
native skips on macOS.

### Bounded diagnostic and catalog admission increment

An intended catalog regression demonstrated mutable witness declarations;
the Python expectation model now copies both collections and enforces the same
ASCII/name/duplicate/count/exclusion bounds as the SDK. The embedded catalog
bytes remain unchanged. T008's remaining control mappings are not inferred.

Two intended diagnostic reds demonstrated a valid oversized event being
accepted and a large JSON array being expanded before rejection. Event bytes
now reject above 1 KiB before parsing, preserving `OutputLimitExceeded` through
the test-output adapter. Raw capture uses at most 64 KiB/read and a two-read
line window; safe retention reserves space for a closed failure record within
the existing 8 MiB/child and 64 MiB/profile limits. Unknown output, floods,
watchdog expiry and containment failure preserve already admitted safe
observations and explicit failure codes, never raw messages or shortened
passing evidence. Watchdog coverage includes a child that closes both output
streams but remains live. All 177 tooling tests pass with ten native skips on
macOS. Native foundation job `120296941427` in run `39918257385` at `ac9be42`
then passed all 72 checks with zero failures/errors/skips, observing
92,111,450,112 free scratch bytes; the SDK/logger diagnostic also passed.
T011 is complete. These diagnostics do not qualify a provider/profile.

### Supervisor deadline and local-scratch increment

Intended regressions exposed missing cleanup reserve, restarted admission
deadlines, and renewed state-publication controls taking 10.2 seconds against a
0.3-second command allowance. Effective absolute deadlines now include admission
and state publication, never widen a stricter caller/scope/profile limit, and
reserve 40 seconds for termination/cleanup before ordinary command admission.
Control/barrier scopes are five/15 seconds; SDK host probes also use five-second
controls. Cleanup reserves its containment allowance within the outer limit.
Commands currently execute serially, below the four-child/one-transfer maxima.

Another regression reproduced a root being created before a remote filesystem
was rejected. Native artifact/baseline admission now checks actual >=24 GiB
capacity and a conservative local-filesystem allowlist before root creation.
Path-free `proofs/preflight.json` retains the observed capacity, filesystem and
monotonic duration, explicitly non-qualifying. Allocation/preflight time counts
against the profile budget. macOS ownership fixtures remain portable but leave
filesystem identity unobserved; provider execution still rejects.
An expired cleanup records retained ownership without deleting resources; an
explicit retry preserves that failure history.
All 184 tooling checks pass with ten native skips. Native run `39920220726`
at `1675f93` then passed all 79 foundation checks with zero failures/errors/skips,
observing 92,111,450,112 free scratch bytes. Its SDK/logger diagnostic passed
seven scenarios/15 observations, independently reproduced the six-baseline
seal and bound input digest
`46a16ed43d07b26d2c11cbf5beb19eb0fd157d47c4e01ed9548bd4ad0f198c4d`.

A further held-admission regression exposed concurrent access to one run's
writer. A nonblocking per-run gate now rejects overlapping commands, cleanup
and transitions before ownership access; nested controlled cleanup remains
allowed. Actual capacity rejection now emits `Incomplete`/exit `2` without
creating a workspace or changing an outside sentinel. Evidence violations
remain `Failed`/exit `1`. All 187 tooling checks pass with ten native skips.
Native run
[39921337767](https://github.com/Stonefly-Labs/Hoard/actions/runs/39921337767)
at `b9d335a` passed all 82 foundation checks with zero failures/errors/skips,
observing 92,111,400,960 free scratch bytes. Its SDK/logger diagnostic passed
seven scenarios/15 observations and reverified all six baselines, binding input
digest `ec4c80a84b38a0815d337cac5b121b6e530ff7d34fff718e9a888f69410a8d60`.

### Expanded catalog and allocation-identity increment

Actual architecture discovery now matches all 41 distinct expected
ARCH-001..008, identity-path and inspection-failure identities, with none
missing. Together with the earlier 144 composition/version/classification
identities and ten SDK catalog admission identities, this maps 195 distinct
non-category runtime names. The 192 inherited category keys and 13 exclusions
are unchanged. Discovery does not establish architecture/profile behavior.

QC-01..48 now enumerate their individual required subproofs: 299 assignments
across profile expansions, not 299 observed passes. Missing/extra QC IDs,
mutable declarations and result overflow reject. Generated SDK bytes agree
with the independent Python expansion. Intended strict SDK catalog reds
preceded rejection of unknown profiles, malformed/duplicate/unknown/missing
fields, invalid strings, missing profiles, duplicate keys and oversized
input/collections/results. All 55 source SDK tests pass. The new ten catalog
cases match actual discovery and are selected as an eighth native diagnostic
scenario; that targeted scenario is not full SDK/package acceptance.

A further intended allocation red reproduced a parent swapped to an outside
sentinel during capacity preflight being followed for workspace creation.
Parent/root descriptors now pin capacity/filesystem probes, workspace creation
and synthetic child directories. Parent replacement and lexical traversal
reject; a second challenge swaps the parent immediately after root creation
and preserves the pre-existing outside root unchanged. No outside files or
directories are created, overwritten or removed. All 190 portable tooling
checks pass with ten native skips. Native run
[39924374116](https://github.com/Stonefly-Labs/Hoard/actions/runs/39924374116)
at `79663dd` then passed all 85 foundation checks with zero
failures/errors/skips and 92,111,257,600 free scratch bytes. Its SDK/logger job
passed eight scenarios/25 observations, including all ten catalog admission
cases, and independently reverified all six baselines with seal
`41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`.
Input digest:
`5d7fb9b9ed2288da5c10c4773da834140172c323822ba31b79e13c6b71c803ff`.
T008/T012 are complete within their independently expanded catalog and bounded
supervisor scope. This is not full 55-test native SDK/package coverage, executed
QC control coverage or completed profile orchestration. T013/T014 and later
tasks retain those input/provenance/integration obligations.

### T013 immutable source-snapshot increment

Five intended failures reproduced aliased source/snapshot roots, a source
ancestor changed after inspection, an unlisted FIFO, and snapshot creation
following a replaced owned root into an outside directory. Source/root/parent
descriptors now anchor bounded hashing/copying and exact post-copy traversal;
no outside directory is modified. Files are read-only before candidate
compilation; generated outputs are excluded only from source comparison, not
silently substituted for admitted runtime inputs. Timeout/overflow retain
their safe incomplete classifications.

Real Git observations now label clean-local, dirty-local and exact clean-CI
source identity. Ambient Git overrides cannot redirect scope; index
assume-unchanged/skip-worktree flags cannot produce a clean CI claim.
CI identity must equal the actual workflow `GITHUB_SHA`, including PR merge-ref
checkout rather than just a branch-head label. Example/build/ignore sources
are included. The SDK diagnostic reuses this path and checks source/identity
again after runtime execution. Its original source smoke lock is immutable;
the existing graph-preserving helper prepares a separate alternate lock for
independent explicit locked replay and verifies its derivation afterwards.

All 196 tooling checks pass with ten native skips; the conformance subset has
91 cases. A focused actual-checkout probe copied and exactly verified 703
read-only scoped files in 395 ms, labelled actual dirty-local inputs and
settled its synthetic resources without provider execution. This is not
qualification. Native run
[39927534630](https://github.com/Stonefly-Labs/Hoard/actions/runs/39927534630)
at `4e17986` then passed 91 foundation checks with zero failures/errors/skips
and 92,111,253,504 free scratch bytes. SDK job `120327506542` passed eight
scenarios/25 observations through the new read-only snapshot/alternate-lock
path. It independently reverified all six baselines with the unchanged seal
`41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`
and bound input digest
`9bfeaac44eab42b175d40bbbd76945f53b1640207befde112bf8af485d75ad7c`.

The next increment binds local package ID/version to actual embedded nuspec
metadata, archive SHA-256/SHA-512 and runtime hashes from one captured byte
sequence. It rejects escaping/duplicate/special/encrypted members and bounded
archive/expansion overflow. Bounds are 64 MiB/archive, 128 MiB expanded,
1,024 members and a 1 MiB central directory, with finite five-second capture
and 64 KiB assembly reads. Selected-file hashing also uses pinned descriptors.
Actual generated NuGet configuration must match the shared synthetic source
mapping before its path-free policy is hashed; arbitrary configuration and
environment dumps are not accepted as configuration inputs.

SDK diagnostic completion recaptures bounded lock/runtime file inventories,
packages, source identity/manifests, verified baselines, synthetic configuration,
and fresh environment observations. Added locks/runtime assemblies also change
the input digest. Every role is compared; only live free-space variation is
excluded from immutable identity, preserving its original admission measurement.
Admission/completion probes retain separate safe observations and independent
caches. These changes do not establish actual loaded-provider provenance.
T013 remains unchecked until complete per-profile capability/declaration
capture and integration pass; the newest increment still needs native execution.
All 204 tooling checks pass with ten native skips on macOS; the conformance
subset contains 99 cases. Catalog generation, frozen baseline inventory and
whitespace checks also pass. No C# or production boundary changed in this
increment; the earlier 55-test source SDK result is not a fresh native result.

### T013 shared profile and binding-declaration capture

Native run [39929542533](https://github.com/Stonefly-Labs/Hoard/actions/runs/39929542533)
at `44881ff` passed all 99 foundation checks with zero failures/errors/skips
and 92,111,134,720 free scratch bytes. SDK job `120334108701` passed eight
scenarios/25 observations through coherent package capture, real synthetic
source-mapping verification and complete input/environment recomputation.
All six baselines reverified with the same seal; input digest
`9d5195ca7fa08543d24fb92b0b478d2f5bcff06b9f612881ff6f20b955926e96`.

The following increment adds `ConformanceBindingSnapshot.Capture`, emitting
immutable bounded UTF-8 bytes from the actual typed declaration only after
mandatory fault admission. The closed eight-field record contains no outcome,
connection string, environment dump or root path. Python `capture_binding`
reads the actual pinned file, validates fields/faults and package ID/version/
archive correspondence, and derives binding-descriptor/capability hashes
from those bytes, not supplied digest labels. This is the conformance binding
descriptor, not proof of an entire product `ModuleDescriptor` or loaded factory.

`capture_profile_inputs` now shares actual source/Git identity and exact
snapshot checks, local packages, selected lock/runtime bytes, binding declarations,
verified historical seals, synthetic source policy and typed observed environment
across the five admitted profile IDs. Sources/identity are checked again at
admission; completion uses the same capture and full comparison. The SDK
diagnostic delegates to it instead of maintaining a second input assembler.
An actual private portable fixture covers package/declaration correspondence,
capability mutation, exact source mismatch and path-free public inputs.
Its synthetic compiled-byte fixture is not loaded-provider evidence.

The missing C# snapshot API produced four expected CS0103 errors across its two
new facts; two Python capture tests failed on their missing API before repair.
These are implementation reds, not qualifying assertion-negative executions.
All 207 tooling checks pass with ten native skips;
102 are conformance checks. All 57 source SDK tests and focused C# formatting
pass. The two new declaration facts form a ninth native diagnostic scenario
(27 expected observations); native execution is pending. T013 remains unchecked
until that shared-path verification completes. Profile execution/evaluation,
actual loaded providers and SQLite environment production remain later tasks.

A further mutation regression changed generated `runtimeconfig.json` without
touching a DLL and observed missing input rejection. SDK runtime inventory now
also binds `.deps.json`, `.runtimeconfig.json` and `.runtimeconfig.dev.json`
bytes. These compiled runtime artifacts remain separate from the shared
synthetic configuration-policy digest. This does not replace T014 loaded-runtime
proof. The existing focused SDK mutation test now covers that repaired boundary.

Run [39931791961](https://github.com/Stonefly-Labs/Hoard/actions/runs/39931791961)
at `4a284f8` first verified shared capture: 102 native foundation checks,
zero failures/errors/skips, nine SDK scenarios/27 observations and all six
historical baselines. Input digest
`e0e65eab2797443efa5057091e3675bcfe24e2514f310c865147b30cd5f93358`.
Final runtime-configuration repair run
[39932469750](https://github.com/Stonefly-Labs/Hoard/actions/runs/39932469750)
at `525bdf0` repeated all 102 native checks without failures/errors/skips,
measured 92,111,089,664 free scratch bytes, and passed the nine SDK scenarios/
27 observations with complete shared input/environment recomputation. All six
baselines reverified with the unchanged seal. Input digest
`3b43174ff47f2604acb6dd67af5d81189538815e80a6d730cc09a54fff078b37`.
T013 is complete within its shared input-capture foundation scope. T014 retains
actual loaded-factory/session/runtime provenance; later profile tasks retain
their real SQLite/environment producer and full orchestration obligations.
No category or five-profile qualification follows from these diagnostic runs.

### Partial T014: enum transport and actual-instance component capture

Enum identities first failed focused C#/Python regressions, then passed with
bounded bare identifier tokens and unchanged exact parent matching. Run
[39933805476](https://github.com/Stonefly-Labs/Hoard/actions/runs/39933805476)
at `a1fe180` passed 103 native foundation checks with zero failures/errors/skips,
92,111,106,048 free scratch bytes, ten scenarios/29 observations and all six
historical baselines. Input digest
`8b291f375d50901e255a9d95dbb44e37ed117ab520c04c19e208ebc270388992`.

The next local increment adds actual typed-instance assembly capture: bounded
coherent bytes, loaded module/PE MVID and name/version checks, and actual type
hashes without provider rendering, path projection, directory discovery or
assembly loading. Independent Python ingestion requires the selected runtime
artifact and any selected package's actual embedded assembly bytes, not a
copied package label. Two missing C# capture facts and two missing Python
ingestion cases preceded implementation. All 64 source SDK tests and 105
conformance tooling checks pass (ten native skips locally); native verification
of the eleventh scenario/31-observation selection is pending. These component
APIs do not yet prove actual session/factory/invocation linkage, complete
discovery, append-only execution state or actual provider/runtime environment.
T014 remains unchecked.

Run [39934964377](https://github.com/Stonefly-Labs/Hoard/actions/runs/39934964377)
at `0a0b1d1` subsequently verified the component capture: 105 native checks,
zero failures/errors/skips, 92,111,003,648 free scratch bytes, eleven scenarios/
31 observations and all six historical baselines. Input digest
`6d21a3127a27650ac8c73e37eb6aaa0552d4c55496581a73cb2d0f600229866b`.

The next local increment separates actual VSTest discovery from execution:
required purpose-bound manifests/completions, exact selected methods and all
their parameter rows, actual source bytes, safe append-only discovery records
and independent Python provenance/interval admission. A discovery record cannot
become an execution witness. Incremental completion hashing additionally binds
the entire record stream; an intended in-bounds timestamp mutation failed
before that repair. A portable real VSTest enum-discovery probe passed with
no unknown diagnostics and removed its temporary private fixtures. All 108
conformance tooling checks pass (ten native skips locally). Linux diagnostics
now discover each selected scope before execution and add four discovery
transport regressions: twelve scenarios/35 discovery records/35 execution
observations, native verification pending. Complete append-only execution state
and loaded-session/factory/invocation integration remain unfinished T014 work.

Run [39936903326](https://github.com/Stonefly-Labs/Hoard/actions/runs/39936903326)
at `6a04293` then verified separate discovery: 108 native checks without
failures/errors/skips, 92,110,938,112 free scratch bytes, all twelve scopes/
35 selected discovery records/35 execution observations and all six historical
baselines. Input digest
`5d058da1593a05b0dad1a11b061bf35161bee428da73a243295bdbca5116fe41`.

The next local increment adds a catalog-owned single-controller runtime
case-history API, not the full dispatcher. It freezes exact expected keys/
witnesses and admitted inputs, observes parent monotonic boundaries, rejects
overlap/replay, and preserves immutable failed attempts/witnesses/proofs through
a passing retry. Invalid provenance closes an unsuccessful attempt and raises
its safe error; interruptions and catalog exclusions invent no execution.
Default one/maximum three attempts and proof bounds remain enforced.
Outstanding independent controls keep runtime-only observations incomplete.
Two missing-API regressions preceded implementation; all three focused history
regressions pass locally and run `39938028171` at `a9039fa` verified 111 native
checks without failures/errors/skips, 92,110,921,728 free scratch bytes, all twelve
diagnostic scopes/35 observations and all six baselines. Input digest
`dba8a0ef424aa28b2053e7cc0e87a12c66b1b8f9f66227d46071bf218420f6b9`.

The current increment adds actual typed factory/session origin APIs for both
categories. Wrappers defer provider getters until callers own cleanup, pin the
exact interfaces common consumers receive, preserve actual reopen lineage and
stable reference-equality identities, and delegate cleanup without release claims.
The closed path-free origin includes actual initial declaration SHA-256 and
executing .NET runtime/architecture. All component byte reads share five seconds/
256 MiB, retaining the 64 MiB per-assembly bound. Parent ingestion independently
selects role-specific runtime/package assignments and rejects immutable declaration,
environment, parent or repeated-instance inconsistencies. Wrapper/forwarder roles
need not pretend to belong to one package. Three C# missing-API regressions and two
Python missing-API regressions preceded implementation. Local source SDK tests
pass (73), tooling passes (218, ten native skips), and focused formatting passes.
The bounded architecture review found no actionable ownership/dependency defect.
The thirteen-scope/38-observation native selection is pending. These leaf APIs
still need exact execution/attempt/group/input linkage, actual SQLite/PRAGMA
production and full controller/evaluator integration; T014 remains unchecked.

## Partial implementation checkpoint

The driver remains **`implement / running`**. Authorization to start was explicit;
the 40 custom checklist markers remain reviewer-owned and unchecked. All 86
tasks originally started unchecked; T002..T005 manifest/solution setup is now
verified complete. Remaining markers await their full acceptance obligations:
scaffolding and focused successes do not establish complete task acceptance.
No `finish` or convergence ran.

Delivered foundations comprise the source-derived frozen inventory/generator,
SDK and fixture manifests, typed binding/session/resource/diagnostic/witness
contracts, an independently expanded catalog, strict Python evidence entities,
source snapshots, initial witness admission, owned execution and historical
baseline preparation. The solution registers SDK unit tests normally and
excludes package-only fixture projects from default builds. Production
reference edges and production provider contracts are unchanged. Common consumers,
adapters, the conformance CLI/evaluator/reports, complete compatibility/composition
profiles, contributor example and five-profile CI are not delivered.

Historical preparation completed locally before candidate package builds:
the sealed proof SHA-256 was
`a725a20dcbb635944f64fed007205d06de532ca7f2b4f87c104ac4434ffa8215`.
This is **preparation, `qualification: false`**, not imported passing evidence.
The private seal and retained source/binary/feed/cache resources are outside Git.
The F-06 artifact recipe intentionally retains pre-F-06 metadata packages in
its own feed/cache, separate from F-06 metadata acceptance. Baseline integrity
and safe reuse must be verified before candidate execution; do not rebuild or
substitute retained binaries.

An early, bounded `hoard-architecture-review` identified these unresolved
foundation findings. This does not satisfy the final T081 review gate.

| Severity | Surface | Required correction |
| --- | --- | --- |
| High | `scripts/conformance_execution.py` descendant tracking | Account for children leaving the original session/group; retain ownership when actual settlement cannot be established. Add a detached-descendant regression. |
| High | Executor post-`Popen` registration | Guard identity/ledger registration immediately after spawn and contain or retain the child on registration failure. Add injected-failure regressions. |
| Medium | Executor termination/release | Propagate finite deadlines through control calls and destructive cleanup; never persist `Released` before successful deletion or equate timeout with settlement. |
| Medium | `scripts/conformance_evidence.py` witness admission | Compare expected binding and matrix dimensions, not only names/input/package/assembly hashes. Add dimension-only mutation cases. |
| Medium | SDK metadata fault interfaces | Express typed targeted record/receipt faults, scoped restoration and opaque before/after fingerprints while keeping assertions in common consumers and private storage access in adapters. |

**Historical decision at the earlier checkpoint:** T003 required unchanged provider
implementations, but Memory exposes neither targeted receipt mutation nor
opaque observations of its private `MemoryState`/operation ledger.
`MemoryFaultControls.CorruptRecordForTestAsync` sets global `Schema = 4`; it
cannot preserve the existing receipt-corruption assertions that independently
read unchanged aggregates and corroborate unchanged damaged ledger fields.
A binding alone cannot add those controls without private access or fabricated
behavior. The recommended resolution is authorization for a narrowly scoped
test-only seam inside the Memory fixture assembly, with no SDK dependency or
private types exposed. The maintainer was unavailable to answer that request,
so no provider edits, applicability waivers or assertion reductions were made.

Focused checks observed before this checkpoint: all 121 Python tooling tests
and six SDK binding tests passed; frozen inventory/catalog comparisons and
SDK/test formatting checks passed. These do **not** cover the review findings
or establish complete model/execution/evidence correctness. Full predecessor
acceptance, independent locked package replay, actual large transfers/recovery,
clean contributor execution and local/CI conformance qualification remain
unrun. Resume with the scope decision, repair the foundation findings and
complete all remaining tasks before finishing this stage.

README, development/provider guidance and this quickstart reflect the partial
state. Custom-host examples, product charter/specification, architecture/ADR/
diagrams, predecessor artifacts, governance, release/IaC/UI guidance remain
unchanged because no supported product API, provider implementation,
production graph or operational procedure changed.

## Summary

Extract reusable, test-only category suites from the existing package-acceptance
tests, keeping their assertions and independent implementations. A separately
packable `Hoard.Testing.Conformance` library supplies the common consumers,
binding contracts and fixed case catalog; provider-specific adapters supply only
construction, controlled faults and owned-resource observations. No platform
library depends on the test kit.

Add one bounded orchestrator that verifies exact runtime witnesses, package
bytes, configuration, capabilities and environment before deriving a result.
Retain F-05/F-06 logical and real local recovery obligations, F-01 compatibility/
architecture policy and F-02/F-03 lifecycle enforcement. A finite fixture-host
and version matrix, contributor good/faulty examples and narrowly scoped CI
use the same inventory and acceptance evaluator locally and automatically.

## Technical Context

**Language/Version**: Nullable-aware C#/.NET 10 under the existing `global.json`;
Python 3 standard library for evidence evaluation/orchestration; Bash entry point.

**Primary Dependencies**: Reuse centrally pinned xUnit, Microsoft.NET.Test.Sdk,
ASP.NET Core TestHost and Mono.Cecil in test projects only. SQLite remains
private to its existing fixture. No new production or vendor dependency.
Local packing is acceptance evidence, not authorization to publish NuGet packages.

**Storage**: Synthetic SQLite/memory and Local/ObjectSemantics stores in fresh
owner-private roots outside Git. JSON manifests and sanitized summaries;
retained build/test diagnostics are sanitized before persistence. Existing
Abstractions metadata/artifact interfaces and authority seams stay unchanged.

**Testing**: Extract common assertions without narrowing coverage. Add binding,
inventory/evidence, mutation, contributor and CI-parity regressions. Real
process interruption and 256 MiB/4 GiB transfer/RSS checks remain required.
All six existing feature validation entry points remain regression gates;
no prior passing report qualifies current changed inputs automatically.

**Target Platform**: Mandatory CI on `ubuntu-24.04`, exact image/runtime/filesystem
recorded; local macOS or Linux uses the identical profiles. A run qualifies only
its actual environment. No Windows, remote-service, OS/power-loss or HA claim.
Dependency restoration may need nuget.org; no external running service, cloud
account or credential is required.

**Project Type**: Test SDK, contributor fixtures, evidence CLI and conformance
CI only. Core remains empty/provider-free; no curated server or UI is created.

**Performance Goals**: Finite observable completion, not production throughput.
Preserve F-05/F-06 operation/buffer/queue limits and the <=64 MiB incremental
peak RSS criterion for each actual large artifact transfer. Outer observation
budgets never increase an inner contract deadline or release late work.

**Constraints**: [Harness contract](contracts/harness.md) defines exact budgets,
isolation and retained ownership. Full artifact profile requires at least
24 GiB free private local scratch at admission; transfers and large copies are
serial within that profile. Insufficient resources are `Incomplete`, never a
smaller substitute. Hosted-runner capacity must be measured at implementation;
if inadequate, resolve an explicitly provisioned runner prerequisite rather than
delete unrelated runner software or reduce mandatory coverage.

**Scale/Scope**: Five stories, 23 scenarios, 14 edge cases, 24 FRs/eight SCs;
192 inherited category entries, 20 composition rows, policy/boundary and
architecture expansions, and 48 F-07 proof obligations. Five mandatory CI
profiles execute the same finite catalog as local baseline mode.
See [matrix](contracts/matrix.md) and [acceptance](contracts/acceptance.md).

## Constitution Check

*Evaluated before Phase 0 and re-evaluated after Phase 1 design.*

| Principle / constraint | Pre-research gate | Post-design gate |
| --- | --- | --- |
| I: cache/native/personal | Pass: qualification foundation only | No publishing registry, native-client claim or required cloud dependency |
| II: versioned explicit composition | Pass: existing contracts authoritative | Test SDK outside production graph; explicit package bindings and unchanged singleton/optional-target policy |
| III: centralized correctness | Pass: no new engine/slice | Shared assertions exercise existing authority/contracts; no duplicated publication, GC or activation implementation |
| IV: verified bounded recovery | Pass: all prior guarantees retained | Real local crash/large-transfer proof; finite observations retain live ownership; simulation never supplies durability |
| V: security/isolation | Pass: no new network feature | Private synthetic roots, exact process ownership, allowlisted reports, no raw artifact uploads or CI secrets |
| VI: evidence before claims | Pass: paired independent fixtures | Exact expected inventory, runtime witness mapping, red/green pairs, fail-closed aggregation and five-profile CI parity |
| VII: static accessible console | Not exercised | No rendered UI, Next.js/Node, management API or OpenAPI change |
| VIII: compatibility/reversibility | Pass: separate test extension | Frozen source/binary baselines, unchanged policies, scoped reproducible reports, explicit incomplete cleanup and unsupported choices |
| Workflow | Pass: recorded branch, pinned directory, `plan / running` | Installed planning skill only; separate later checklist/tasks/analysis/implementation gates; draft PR and durable checkpoint |

No exception, constitutional amendment or ADR change is proposed. These are
design gates, not passing runtime evidence. The bounded architecture review
identified a retained-diagnostics sanitation gap and an unspecified child-output
bound; both are corrected in the contracts below. No reviewer-owned checklist
approval or runtime evidence follows from that review.

## Project Structure

### Documentation (this feature)

```text
specs/007-provider-conformance/
|-- spec.md
|-- checklists/requirements.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
`-- contracts/
    |-- harness.md
    |-- evidence.md
    |-- matrix.md
    `-- acceptance.md
```

Custom reviewer-owned checklists and `tasks.md` are separate later stages.

### Source Code (future implementation, not created by planning)

```text
tests/contracts/Hoard.Testing.Conformance/     # Packable test SDK, no providers
tests/contracts/Hoard.Conformance.Tests/       # SDK/evaluator integration checks
tests/contracts/Hoard.Metadata.Tests/          # Existing case wrappers retained
tests/contracts/Hoard.Artifacts.Tests/         # Existing case wrappers retained
tests/fixtures/conformance/Bindings/           # Existing-provider setup adapters
tests/fixtures/conformance/Contributor/        # Separate good/faulty adapter example
tests/fixtures/conformance/Host/               # In-process packaged fixture host
tests/fixtures/conformance/Consumer/           # Package-only shared-kit consumer
tests/integration/Hoard.Composition.Tests/     # Extend existing lifecycle checks
tests/architecture/Hoard.Architecture.Tests/   # Real graph and permitted counterparts
tests/tooling/test_conformance_evidence.py     # Evidence mutation/CLI regressions
scripts/validate-conformance.sh                # Shared local/CI entry point
scripts/conformance_evidence.py                # Bounded execution and evaluator
scripts/conformance_case_catalog.py            # Versioned expected cases/witnesses
.github/workflows/conformance.yml              # Five profiles + aggregate check
examples/ProviderConformance/README.md          # Contributor reproduction guide
```

**Structure Decision**: The test SDK references Abstractions and test frameworks,
not Hosting, Core or concrete providers. Its optional composition test driver
lives in the host fixture, outside the SDK. Bindings may reference the SDK and
their own provider package; composition adapters own Hosting integration.
Provider implementations never reference one another or the test SDK.
Existing production references and public contracts do not change.

## Phase 0: Resolved Research

[Research](research.md) resolves extraction strategy, assertion authority,
runtime attribution, old consumers, finite environment scope, CI and cleanup.
Existing concrete helpers are not already an independent contributor entry point:
extract their common consumers behind typed bindings, rather than merely wrap
the old scripts and call it reusable certification. No unresolved product
clarification remains. Runner capacity and action commit selection are explicit
implementation prerequisites, not invented planning evidence.

## Phase 1: Design and Integration

1. Freeze catalog revision `f07-v1` and pre-extraction witnesses. Extract shared
   logical consumers, retaining all case IDs and inherited subproofs.
2. Implement four separate binding adapters and validate capability/applicability
   before executing common assertions. Missing mandatory hooks are failures.
3. Produce and independently evaluate input-bound evidence; upgrade weaker
   lower-level witness attribution where required instead of trusting pass counts.
4. Exercise the finite baseline/replacement, startup/lifecycle and version
   matrix through existing composition APIs. Preserve architecture negatives
   and permitted Identity -> Hosting -> Core path handling.
5. Compile unchanged source and run frozen old binaries against candidate
   packages; demonstrate isolated breaking counterparts.
6. Prove the contributor route with a separately built, test-only forwarding
   adapter and deliberate faulty behavior, never edits to shared assertions.
7. Add the five-profile CI with read-only permissions, exact revision inputs,
   bounded execution and sanitized-only uploads. A separate aggregate check
   recomputes completeness rather than trusting job status or summary labels.

## Requirement and Outcome Traceability

| Requirements | Design owner | Required proof |
| --- | --- | --- |
| FR-001..003 | Harness catalog, binding contracts | QC-01..05; all 192 inherited entries |
| FR-004 | Metadata binding/common suite | QC-06..08; MP-01..48 on both |
| FR-005 | Artifact binding/common suite | QC-09..12; AS-01..48 on both |
| FR-006..010 | Composition matrix | QC-13..21; CP-01..20 |
| FR-011 | Version expansion | QC-22..24 |
| FR-012 | Compatibility baselines | QC-25..26 |
| FR-013 | Existing actual graph inspectors | QC-27..28; ARCH-001..008 paired |
| FR-014 | Exact support matrix | QC-29,47 |
| FR-015 | Packaged contributor entry point | QC-30..32 |
| FR-016 | Owned resources and budgets | QC-33..36 |
| FR-017 | Local/CI prerequisites and exclusions | QC-37,46 |
| FR-018 | Evidence input/witness binding | QC-38..41 |
| FR-019 | Recorded mutation pairs | QC-04,14,22,26..28,31 |
| FR-020 | Independent completeness evaluator | QC-39..44 |
| FR-021 | Five-profile CI parity | QC-45..46 |
| FR-022 | Closed safe diagnostics | QC-21,35,48 |
| FR-023..024 | Scope and reproduction guide | QC-29..32,37,47..48 |

All eight outcomes and all 23 scenarios/14 edge cases are mapped in
[acceptance](contracts/acceptance.md). Prior requirements/checklist markers stay
unchanged. No tasks are generated and no product acceptance is claimed.

## Planning Review

The custom architecture review found that public-only sanitation would not
satisfy FR-022 for private retained logs/evidence, and that finite child deadlines
alone do not bound output memory/disk use. The design now requires sanitation
before diagnostic persistence, checks both private retained diagnostics and
public projections, forbids raw-output spooling, and declares finite incremental
capture limits with an explicit overflow failure. Synthetic live test stores
are resources, not diagnostic evidence; ownership-driven retention does not
qualify them as safe report artifacts. QC-34/QC-48 include those exact proofs.

Implementation still owes actual extraction parity, runner capacity, source/
binary resolution, process settlement, output-flood and sanitation evidence.
Planning establishes no passing product behavior or blanket certification.

## Complexity Tracking

No constitutional violation requires an exception. One shared test SDK and
one evidence evaluator are necessary for independently packaged authors to use
unchanged assertions; a general plugin system, second activation model,
credentialed service matrix and certification marketplace are rejected.
