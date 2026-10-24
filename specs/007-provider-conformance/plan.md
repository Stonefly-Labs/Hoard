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
Run `39940194762` at `457c4e5` verified 114 native checks without
failures/errors/skips, 92,110,696,448 free scratch bytes, thirteen scopes/
38 observations and all six baselines. Input digest
`8ffbb9fc9ca1d634e0030b796ae3454f20577185226bb643f370983787781782`.
At that checkpoint these leaf APIs still needed exact execution/attempt/group/input linkage, actual SQLite/PRAGMA
production and full controller/evaluator integration; T014 remains unchecked.
An additional intended controller regression exposed the new session scope
selecting the smoke assembly instead of the source SDK test assembly. Explicit
source routing is repaired; all thirteen scopes now have a checked launch against
their actual admitted assembly/package before discovery, and all sixteen SDK
orchestration unit checks pass. Run `39940194762` verifies the repaired routing;
it does not verify the subsequent origin channel described below.

The next increment implements the exact result-origin channel. The SDK emits
hash-only, canonical UUID/runtime/case packets, each below 1 KiB; the actual VSTest
result supplies their execution context. The safe logger validates the closed
packet/schema inventory and exact run/case/admitted assemblies, then binds origins
inside its immutable execution/attempt/group/input/owner proof (64 KiB maximum).
Parent admission independently selects every component's runtime/package bytes,
checks descriptor/runtime/architecture and reopen lineage, and requires origins
for passing provider-bound qualification witnesses. Failure/skip observations do
not fabricate origin data. Case history retains immutable origins and frozen role
assignments, rejecting session replay under fresh attempt/execution UUIDs.

The focused architecture review exposed instance-coherence maps resetting per
origin; intended rehashed C#/Python regressions reproduced conflicting identities
across origins, separate results and retries. Shared maps now reject those mutations
without replacing prior evidence. The fifteen-scope/46-observation native selection
adds a real package-mode channel probe using an explicitly synthetic metadata
factory and independently planned declaration, plus six logger mutation rows.
This diagnostic setup is not observed provider behavior or qualification; its
actual factory/session capture must match the planned input, and all probe roles
remain explicitly unpackaged test artifacts. Local tooling passes 221 checks
(ten native skips), source SDK tests pass, and native channel verification is
pending. T014 remains unchecked; concrete adapters, actual SQLite environment
production and complete CLI/profile/evaluator behavior are not implemented claims.

### T014/T015 foundation closure

Native run [39943968117](https://github.com/Stonefly-Labs/Hoard/actions/runs/39943968117)
at `068788807481b41eed82c8800f94cd5c2173cafa` passed all 116 foundation checks
without failures/errors/skips, measured 92,110,667,776 free scratch bytes and
admitted all fifteen scopes/46 discoveries/46 executions. The synthetic
package-mode origin channel actually executed without broad output allowlisting.
Input digest `9b39c7bffc01e32c147d925b741308417eb2e2cc45e796f5af35b72faee18934`.
All six historical baselines sealed before candidate builds and reverified
afterwards, with seal
`41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`.
T014 is complete within generic runtime discovery/origin/proof/state foundations.
The existing owned baseline implementation also satisfies T015: exact frozen
revisions/recipes, independent feeds/caches, original historical source locks,
explicit graph-preserving alternate-lock derivations when actual local archives
differ, and source/recipe/lock/dependency/package/binary recomputation. Focused
substitution/derivation regressions pass; no old SDK release or copied runtime pass
is invented. T015 is complete. T016 and later controller/category/SQLite/evaluator
tasks remain open; these observations remain non-qualifying diagnostics.

### Partial T016: explicit lock preparation

`scripts/validate-conformance.sh --update-locks --evidence <fresh-private-path>`
now drives non-qualifying six-baseline-first preparation. Ten existing
prerequisite projects preserve their historical lock graphs using recorded
local-archive-only derivations; thirteen explicit new/variant conformance locks
are prepared. A second owned source/feed/cache must locked-build the same graph
and reproduce every package/lock byte before publication. No predecessor lock is
copied back; repository source changes and foreign paths block publication.
Three intended missing-API regressions precede implementation; a fourth focused
publication case also passes. All 225 local
tooling checks pass (ten native skips). A local Linux Docker experiment rejected
native prerequisites before preparing anything (120 checks/26 prerequisite
errors); the stopped container was removed without relaxing containment or
filesystem admission. A dedicated non-qualifying Ubuntu CI job now performs the
native experiment and uploads only source locks for review. Actual replay and
tracked lock generation/review remain pending; T016 stays unchecked and T017
default profile/verify/aggregate behavior remains unimplemented.

The first supported preparation run `39946559245` at `082d064` passed
120 native foundation checks with zero failures/errors/skips and repeated all
fifteen SDK scopes/46 observations and six baselines. Preparation then failed
safely at command 124 (`CS1566`) because the source inventory omitted Application's
embedded F-04 OpenAPI contract. A focused intended snapshot failure preceded
adding that exact compiled resource to immutable source capture. No locks were
published and no assertions/old artifacts changed.

Repair run `39947737831` at `585970d7e4ba3085724b563b026cb9711e41055d`
passed all 120 native foundation checks without failures/errors/skips, fifteen
SDK scopes/46 discoveries/46 executions and all six baselines, plus the full
preparation job. Free scratch was 92,112,183,296 bytes; SDK input digest
`3c77e2758f16fbc38ee08652d9cd01685d9ac99c6288d3801f8a4b7fbc2353bb`.
Independent fresh source/cache/feed builds reproduced identical bytes for all
18 packages and 13 locks; preparation proof
`8a8f66c6cc4d8cc51845ac5091a62caf9456d1cd7fb5a5fe9ee73600c37f9638`.
The downloaded source-only lock artifact matched the exact inventory. Review
confirmed seven new locks, local-archive hash updates only in three existing
F-07 variants, unchanged existing graphs and all 20 third-party identity/version/
hash triples. Guarded publication imported those generated bytes without
predecessor lock changes. T016 is complete; T017 CLI admission/dispatch remains next.

### Partial T017: exact invocation admission

Four new CLI regressions failed first on the absent admission/dispatch API and
entry module, then passed. The new immutable invocation records exact
independently expanded catalog keys, profile scope, diagnostic/preparation mode,
explicit category project and private destination. Unsupported/service profiles
cannot fall back, case filters are exact, and repeated/abbreviated options,
conflicting modes, invalid bindings and existing/nonprivate/symlinked destinations
reject before allocation. Public errors never interpolate arbitrary arguments.
The separate entry module avoids duplicate evidence module/type identities.

Preparation routes to the real T016 implementation. Runtime, verify and aggregate
requests are admitted but execution is explicitly unavailable:
`Incomplete`/`EvidenceIncomplete`, exit `2`, with no root or passing report.
No schema-only check is presented as independent verification. T017 remains
unchecked pending actual dispatch; T018/story work has not started.
An additional real shell-entry regression rejects an unsupported profile from
another working directory without private stdout/stderr.
`python3 -m unittest discover -s tests/tooling -q` passes 230 checks with ten
native skips on macOS; catalog/frozen inventory, shell syntax and whitespace
checks pass. No C# or package graph changed in this increment. Native validation
of the new shell-to-preparation route remains pending.

### T017/T018 foundation closure

Run [39949986671](https://github.com/Stonefly-Labs/Hoard/actions/runs/39949986671)
at `83ddd428dbf0070b23c45f8d4fbf9843255bd087` passed all three native jobs:
125 foundation checks without failures/errors/skips, fifteen SDK scopes/
46 discoveries/46 executions/all six historical baselines, and real preparation
through the new shell/CLI dispatch. Both independent source/cache/feed builds
reproduced all 18 package and 13 lock byte sequences.
Free scratch: 92,110,598,144 bytes; SDK input digest
`e6eb8293e95bd22208dba1df7bc71d1c9cf97f3d002c467ba62bd8d3ded39369`;
preparation proof
`f58635d15061fa1eb4377e4187a26fe35d96809e970eca20e6f3a325c3bee666`.
An additional local contributor-project selection/private-parent regression brings
the portable total to 231, with ten native skips. No harness implementation changed
after the native run; its test count does not include that additional regression.

**Dependency boundary clarified:** T017 implements exact immutable admission,
real preparation dispatch and explicit fail-closed routing for unavailable
backends, not the profile/evaluation behavior explicitly assigned to
T035/T046/T057/T064/T071..T074. Requiring those later backends at this gate would
create a dependency cycle through T018. No scope/outcome is removed: their tasks
stay unchecked and their CLI requests still return `EvidenceIncomplete` rather
than a fake passing run or schema-only verification. T017's foundation is complete.

T018 reran the complete portable tooling suite, including the specified evidence
and execution files, alongside
`DOTNET_CLI_USE_MSBUILD_SERVER=0 MSBUILDDISABLENODEREUSE=1 dotnet test tests/contracts/Hoard.Conformance.Tests/Hoard.Conformance.Tests.csproj --no-restore --filter FullyQualifiedName~BindingContractTests -p:UseSharedCompilation=false -nodeReuse:false --verbosity quiet`
(19 passed, no skips). Missing mandatory hooks and durable-backup support produce
the intended `BindingInvalid`; repaired declarations admit. Caller mutation does
not change copied capabilities/faults or catalog expectations. Missing actual
session hooks reject despite optimistic declarations; retained cleanup observations
cannot become `Released`. Native execution regressions also prove retained live
work, failed cleanup publication and failure-preserving retry. Their earlier
intended admission/ownership/input/origin reds and passing repairs are recorded
above, not newly invented failures. T018's foundational gate is complete.
This is not real-provider category, contributor, profile or full evaluator proof.

### Partial T019/T020: pre-extraction inventory and discovery guards

The test assembly now embeds the independent frozen inventory. Its category
guards compare every compiled SDK case, parameter, control and exclusion against
that source baseline, not a provider-selected subset. Metadata has complete/
missing/changed parameter controls for both bindings and rejects shortened
post-selection manifests with `InputChanged`. Artifact handoff controls reject
missing rows and the other provider's exact row; simulation keeps its frozen
restart exclusions instead of inheriting Local proof. Every required metadata/
artifact hook is challenged without reducing the expected map.

These 23 new C# cases pass alongside the existing tests (103 total, no skips);
focused SDK formatting passes. The tests reuse the existing owned logger fixture,
and the new inventory resource is test-only. No SDK/provider/package-reference
graph or public product operation changes. A first assertion incorrectly compared
the count of offered discovery records to retained valid rows; it was corrected
to check the actual JSONL prefix, not a logger behavior change.

Two new native diagnostic scopes select the 12 metadata and 11 artifact guards
with exact test identities; the total is seventeen scopes/69 observations.
Their new routing regression first failed four ways: the two scopes selected
the smoke assembly, and unknown/mixed namespaces had no safe rejection. Explicit
homogeneous SDK-test/smoke namespace admission fixes the routing without
service/unknown fallback or another scenario-name allowlist. All 232 portable
tooling checks pass (ten native skips); catalog/frozen inventory/whitespace checks
pass. Native run `39953736120` at
`fa334245ddac4d6e380faf541aeeeb71dc9f5eaa` subsequently verified all seventeen
scopes/69 discoveries/69 executions, 127 foundation checks without failures/
errors/skips, six baselines and byte-identical eighteen-package/thirteen-lock
preparation/replay. Input digest:
`4732cfb3a9872d8361a56da48dbd0ab5d5a4b1e6607be6931eab02401843f6fd`;
preparation proof:
`40632d60679a7d6311d245af98967ab611638673fcec7564ea185c5e2b728a56`.

T019/T020 remain unchecked: these inventory/transport guards cannot establish that
actual common consumers were extracted, execute unchanged for all four adapters
or reject behavioral provider mutations. Completing those tests remains next;
no category/story qualification is claimed. README/development guidance reflects
this boundary; provider/contributor examples, product architecture/ADR/diagrams,
governance, predecessor, infrastructure, release and UI guides are unaffected by
test-only guard additions with no new working product/qualification command.

### Initial executable metadata consumer slice

Six inherited assertion bodies now exist in the SDK behind `IMetadataStore`
and cancellation only: MP-05 exact bounds/aggregate overflow, MP-06 registry/
interval isolation, MP-07 bounded datasets, MP-11 competing creates, MP-12
revision races/delete-recreate and MP-28 owner/generation/revision fences.
Common synthetic data and expected results remain SDK-owned. The consumers
do not construct/select/dispose providers, accept expected-result callbacks,
refer to private storage formats or alter production contracts.

A focused temporary source probe executed all six against unchanged Memory
source (six passed, no skips). It is not package-only evidence: source was
compiled into the probe. Two normal SDK tests prove a structurally valid store
returning eight successful competing creates fails the common `Assert.Single`,
and cancellation reaches reservation before any commit. The absent namespace
was observed first; that compiler failure is not T034's behavioral mutation
proof. A malformed test ticket initially rejected during receipt construction;
correcting it to the public 24-hour lifetime makes the test reach the intended
common assertion. All 105 source SDK tests and focused formatting pass.

The next diagnostic increment adds actual Memory package construction and a
separate package-mode test output. Exact four-local-archive lock derivation
preserves the source variant and third-party graph; independent fresh-cache
locked restore/build precedes six actual Memory consumer witnesses. Mixed
source/package test identities reject. Two absent-helper errors and one
mixed-assembly routing failure were observed before the fix. Expected diagnostic
total is nineteen scopes/77 observations; actual execution is pending.
Full executable parity tests,
the remaining consumers, typed adapters, existing-wrapper forwarding and
package-only category runs remain incomplete; T019..T024 stay unchecked.

### Publication-backed executable slice

Nine additional SDK consumers preserve entity round trips, registry/auth
partition isolation, final-graph deletion/disabled retention, reference
replacement/removal races, zero-reference ABA, invalid telemetry rollback,
all seven page query kinds and oversized request/result rejection. They use
only public store and typed conformance publication authority contracts;
synthetic records and expected outcomes stay in the SDK. The temporary source
probe executes all fifteen consumers against unchanged Memory code.
The test-only registration authority supplies matching logical evidence, not
real artifact storage, protected-reader lifetime or cross-provider integration.

The two paging consumers initially produced intended missing-member compiler
errors. A separate actual Memory-backed aliasing wrapper then failed the
unchanged authorization-partition consumer at its digest equality assertion;
the paired test requires that exact assertion failure and invokes the same
compiled delegate on a fresh corrected Memory store. No expected result is
supplied by the store. This observed behavioral negative is not T034's required
stale-operation/artifact binding evidence. Native diagnostics select the nine
additional consumers, the paired aliasing test and both existing private Memory
mechanism regressions; the total becomes twenty-one scopes/89 observations.
Actual native execution is pending; full task acceptance and all four-provider
extraction parity remain incomplete.

The Memory diagnostic pack call now supplies its explicit NuGet identity:
`Memory.csproj` does not produce `Memory.0.1.0.nupkg`. A focused intended-red
regression preceded correcting the helper's original SDK/logger filename
assumption. No dependency graph or expected assertion changes.

Native run `40053085598` at `69e5e7e0357e559d0ca077ab71ddaafd62dbdc50`
verified the first slice's two source consumer tests alongside all earlier
diagnostics: eighteen scopes/71 discoveries/71 executions, 127 native foundation
checks without failures/errors/skips, six baselines and eighteen-package/
thirteen-lock replay. This predates actual Memory-package consumer execution.

### Exact time, cursor and canonical identity consumers

Four further inherited checks bring the executable slice to nineteen consumers:
exact ticket expiry/rollback, lease rollback/next-generation fencing, opaque
continuation scope/size/foreign-epoch rejection with live resume, and exact
canonical text/forbidden-value handling. A typed harness-owned UTC clock retains
real timestamps/timers; no sleeps or provider-returned expectations replace the
original decisions. The continuation consumer uses two independent prepared
stores and does not parse private token representations. Synthetic user-info
values are constructed for the URI rejection checks. Missing APIs were observed
first; that compiler red remains distinct from the observed aliasing mutation.

The complete temporary source probe passes 22 checks without skips, including
all nineteen consumers, private corruption regressions and paired aliasing/
correct-store execution. Focused formatting and all 236 tooling tests pass
(ten native skips). The current exact native diagnostic vector is twenty-four
scopes/93 observations; that result is pending. Run `40053284658` at `3714a91`
failed safely during candidate construction with `Incomplete`/
`PrerequisiteMissing`, consistent with the archive-name assumption repaired in
`5bdfc98`. No consumer observation or package/category success is claimed for
that failed checkpoint. Full extraction/parity, typed adapters and their task
acceptance remain open.

### Typed receipt-corruption consumer and repaired native package execution

The twentieth actual common consumer covers all fourteen typed operation
corruptions without provider encoding knowledge. It owns the original operation,
expected failure code/phase/retry/ticket, independent aggregate count, damaged
fingerprint stability, exact restored replay/reconciliation receipts and foreign
ticket abandonment. Its control accepts only existing typed corruption requests
and checksum scopes; a full session can pass `Faults.CorruptAsync` directly.
Actual Memory private mutations are shared with the retained independent
mechanism test; no provider-selected expected result or passing flag was added.
A missing-common-API compiler failure preceded implementation. The temporary
source-only probe now passes 23 tests without skips, including all twenty
consumers. This is not complete MP-15/session diagnostic extraction or T019/T021
acceptance. Source SDK tests pass 105; all 236 tooling tests pass with ten native
macOS skips. The current exact native selection is 24 scopes/94 observations,
not yet observed.

Run [40053903410](https://github.com/Stonefly-Labs/Hoard/actions/runs/40053903410)
at `5bdfc98ca5c8586416c4cfa096c243c44dc1f298` verified the archive-name repair:
all three jobs succeeded, 131 native foundation tests without failures/errors/
skips, 21 scopes/89 discoveries/89 executions, six historical baselines and
byte-identical replay of eighteen packages/thirteen locks. This includes the
first fifteen actual Memory-package consumers and the aliasing negative/control.
Input digest:
`3d8f73bbf2b089f602a3654a45194c4f50b338981e4ba25b31ca30a994d43aec`;
preparation proof:
`7fd01849664c83ca59b1617edbd2eec0a3937b320bca2e2b0797fa452a5c09f6`.
Free scratch was 91,725,619,200 bytes. This remains non-qualifying package
diagnostics, not complete metadata/profile qualification.

### Shared record/group/query-dimension corruption checks

Three more actual common consumers bring the slice to 23 methods. They preserve
missing-versus-corrupt complete groups, five page-record damage shapes plus
permanent corruption, invalid page requests, exact restored pages and all five
query-dimension shapes. Selected counts, foreign empty scopes, complete page/
group failures, phases/retries, damaged fingerprints, exact restoration and
single-row traversal stay SDK-owned. Typed controls retain the existing fault
signatures; private Memory encodings remain solely in its test probe.
Memory now actually exercises the query-dimension damage skipped by the
inherited SQLite-only branches. The private record mutation helper is shared
with the independent mechanism check instead of duplicating mutation logic.

A paired unchanged-scope negative fails the common receipt consumer's exact
`NotEqualException`; the identical compiled delegate passes with actual Memory
damage/restoration. This is a corruption-control behavioral negative, not T034's
required stale-operation/artifact binding proof. Missing record consumer APIs
also failed compilation before implementation. The full source-only probe
passes 31 tests without skips; ordinary SDK tests pass 105, tooling 236 with ten
native macOS skips, and focused formatting/catalog/inventory checks pass.
The native selection is now 26 scopes/102 observations, still pending.

Native run [40054314377](https://github.com/Stonefly-Labs/Hoard/actions/runs/40054314377)
at `52043f4108949db8f07b4ed0ff677e4481600b65` then verified all nineteen earlier
consumers against the actual Memory package: all three jobs succeeded, 131
foundation tests without failures/errors/skips, 24 scopes/93 discoveries/
93 executions, six baselines and byte-identical eighteen-package/thirteen-lock
replay. Input digest:
`e52695f91f85dd6661bdf7c3e2593a736106c4a1013a0f5dd62a7bb97c1f150d`;
preparation proof:
`8005f7bedeaab8720c7db522a33f1e125f759d727cb9f848db290ebdfbac7689`.
Free scratch was 91,721,003,008 bytes. The four new corruption consumers and
no-op negative/control still await their native package run.

The bounded `hoard-architecture-review` found no actionable violations or
unresolved design questions in the receipt/record consumers, existing typed
controls and concrete Memory mechanism bridge. It specifically checked
SDK-owned expectations, private encoding separation, restoration independent
of caller cancellation, unchanged-delegate negatives and Abstractions/xUnit-only
SDK dependencies. This is not final review of the unfinished full provider/
package graph. Full bindings, wrapper parity and diagnostic integration remain
open; T019..T024 are not complete.

### Typed observation boundaries and atomic/uncertain outcomes

Six actual consumers bring the executable slice to 29 methods. Three preserve
independent candidate invisibility, faults after each of three mutations and
complete success, and grouped-root reads versus later independent reads. Three
preserve reconciliation I/O uncertainty and original-ticket usability, lost
acknowledgment/replay/abandonment, and eight independent contributions totaling
19 without duplicate uncertain replay. SDK-owned callback counters corroborate
the intended mutation/reconciliation/acknowledgment fault boundaries.

The test SDK adds five closed `MetadataObservationPoint` values and
`MetadataObservationControl`, with matching required `ObserveBoundaryAsync`
on the typed metadata fault driver. No provider name, private boundary string
or expected-result override enters common code. The Memory test bridge maps
logical points to its actual private observations, rejects duplicate/unknown
registration and validates `metadata.internal_failure` immediately without raw
diagnostic retention. Observation disposal removes a registration only; store
work remains session-owned. The common barrier bounds real entry/hold/settlement
waits to 10/15/10 seconds; no controlled UTC clock can extend those waits.

Missing common APIs failed before implementation. A bounded architecture review
then found that a failed/canceled grouped read could skip joining its already
started writer. Both focused regressions failed before repair; cleanup now uses
`Task.WhenAll` to join both public tasks regardless of the read outcome. This
does not claim settlement of underlying work. The source-only probe passes 39
tests without skips, including both failure modes and all 29 consumers.
Ordinary SDK tests pass 105, tooling 236 with ten native skips, and changed
format/catalog/inventory checks pass. Current native vector: 27 scopes/
110 observations, pending. Full adapters, unchanged-wrapper forwarding, parity,
session diagnostics and actual profile execution remain unfinished.

Native run [40054937445](https://github.com/Stonefly-Labs/Hoard/actions/runs/40054937445)
at `cf5afb3946871676296322808d5a51f113cd3da8` separately verified the twentieth
receipt-corruption consumer through the actual Memory package: all three jobs
succeeded, 131 foundation tests without failures/errors/skips, 24 scopes/
94 discoveries/94 executions, six historical baselines and byte-identical
eighteen-package/thirteen-lock replay. Input digest:
`bafcb0ad8ade5f137ab53c76ccd418c2a4d129a95362fe9c645d62b7642c1f1a`;
preparation proof:
`b673a1828e80f56052739a36fcb7fb3dab3866677bc201e928733c5d2e14a864`.
Free scratch was 92,110,262,272 bytes. Newer source results are not substituted
for native package observations.

### Writer exclusion and publication-authority consumers

Five more consumers bring the executable slice to 34 methods. Writer contention
preserves uncertainty for normal/pre-canceled reconciliation without exclusion,
original tickets and exact committed readback after release. Four publication
consumers preserve forged/mismatched/revoked evidence rejection, orphan rather
than blob rollback, protection across the caller's timeout through actual owned
settlement, and replay without authority reacquisition or duplicate references.
The typed authority adds acquisition/active-guard observations and evidence
revocation; no provider-selected outcome flag or concrete artifact type was
introduced. The source probe's guard tracks real acquisition/disposal calls
idempotently, but remains logical evidence/guard simulation, not T033.

Missing APIs failed before implementation. Bounded architecture review found
writer-contention failure cleanup could skip actual settlement or use a canceled
caller token. Two focused failure/canceled-caller regressions failed first;
outer cleanup now drains actual settlement with `CancellationToken.None` after
writer exclusion disposal, even when assertions fail. Protection cleanup likewise
joins its public commit and genuine settlement callback without caller
cancellation. These joins do not infer session/resource release.

The source-only Memory probe passes 44 tests without skips, covering all 34
methods; ordinary SDK tests pass 107, including both cleanup regressions.
All 236 tooling checks pass with ten native macOS skips; focused formatting,
catalog and frozen inventory checks pass. The current native vector is 28
scopes/117 observations, pending. Full typed bindings, unchanged wrapper parity,
all metadata cases and actual cross-store authority integration remain open.

Native run [40055429472](https://github.com/Stonefly-Labs/Hoard/actions/runs/40055429472)
at `2c70dc692c5be088db3dea6f27e56bff8396e9d2` verified all 23 earlier consumers
including actual record/query-dimension corruption and no-op negative/control:
all three jobs succeeded, 131 foundation checks without failures/errors/skips,
26 scopes/102 discoveries/102 executions, six baselines and identical
eighteen-package/thirteen-lock replay. Input digest:
`0e87cd4b3fa1076ab99c1d99db9474d6e500b305e4bbe6e80dc3b030d42c8544`;
preparation proof:
`c0e9d29c9f47d67976adc306aff8859c978d38fd970dae558465f8ff9d6db2e0`.
Free scratch was 92,110,331,904 bytes.

Native run [40056205385](https://github.com/Stonefly-Labs/Hoard/actions/runs/40056205385)
at `a1c4a1fd58f9c872e97160397b9d4015ddfb55a2` then verified all 29 earlier
consumers, including atomicity/uncertainty and both failed/canceled-read joins:
all three jobs succeeded, 131 foundation checks without failures/errors/skips,
27 scopes/110 discoveries/110 executions, six baselines and identical
eighteen-package/thirteen-lock replay. Input digest:
`ad3ea626a69e4bea331f987c9b716b00cc2aa10f1c5394db4cf8852589fbc525`;
preparation proof:
`18f093bf8be4763ea434961a9a785dcbeaa053dd51530e182b80b31a94c21d00`.
Free scratch was 92,108,992,512 bytes. The five newer writer/authority consumers
and ordinary SDK settlement regressions still await their native run.

### Lease decision and deadline ownership consumers

Seven additional methods bring the executable slice to 41: generation overflow,
expiry at the final renew/release/guard decision, writer budget, cancellation
decisions, queue capacity, disposal ownership and known exception classification.
The overflow probe uses the same fixed harness clock as the store so its 1 ms
lease cannot expire incidentally. The typed logical controls keep private
observation strings and generation mutation in the concrete fixture.

The full source probe initially failed because a pre-canceled reservation could
return definite cancellation while dispatched work remained owned; the next
reservation correctly reported Unavailable. The consumer now unconditionally
joins genuine settlement before requesting a fresh ticket. A focused SDK
regression verifies this ordering and the non-cancelable cleanup token.
Started public tasks and actual settlement are joined together, including
failure paths; the shared helper also preserves publication cleanup. Bounded
architecture review found no actionable defects in this increment.

The source-only Memory probe passes 53 tests without skips; ordinary SDK tests
pass 108. Tooling passes 236 checks with ten native macOS skips; focused
formatting, catalog, frozen inventory and whitespace checks pass. Exact discovery
confirmed all nine new Memory wrapper rows. Current native selection:
30 scopes/127 observations, pending. Full extraction, schema/diagnostic controls,
the inherited incomplete-cleanup case, typed adapters and wrapper parity remain
open; T019..T086 are not marked complete.

Native run [40057148652](https://github.com/Stonefly-Labs/Hoard/actions/runs/40057148652)
at `bb7478ca56634f085cc0b7f05f0926823ad7639c` verified all 34 earlier consumers,
including publication authority and both writer-settlement regressions. All
three jobs succeeded: 131 foundation checks without failures/errors/skips,
28 scopes/117 discoveries/117 executions, six historical baselines and
byte-identical eighteen-package/thirteen-lock replay. Input digest:
`de9197030e3a8b8675334191edc4bae59dbb874850a72c52a06fc72c918e0e37`;
preparation proof:
`dfb1356f57a03483dff44f9b8b092c7e58bb26bf33ea21add85344cad184a9e6`.
Free scratch was 92,110,127,104 bytes. This remains non-qualifying diagnostics.

### Capacity, admission and incomplete-cleanup consumers

Six further methods bring the executable slice to 47. They preserve injected
storage-capacity rollback/same-ticket retry, live-ledger capacity without receipt
eviction, explicit schema admission, invalid-budget/closed-store rejection,
incomplete cleanup with actual retained work and safe diagnostic projections.
The required typed fault counters expose only nonnegative boundary/internal-
failure/incomplete-cleanup counts; fixture mapping rejects unknown diagnostic
strings immediately, without storing raw text or accepting expected-result flags.

Six missing common APIs failed compilation first. The source-only probe then
passed all 60 tests without skips, including real ledger filling, the provider's
actual 30-second cleanup failure and a paired dropped-diagnostic assertion
negative/unchanged observed control. The complete probe took 33 seconds.
Ordinary SDK tests pass 108; tooling passes 236 with ten native macOS skips;
focused formatting, catalog, frozen inventory and whitespace checks pass.
Bounded architecture review found no actionable defects in the new controls,
failure/admission consumers or incomplete-cleanup ownership paths.

The special cleanup hold is 60 seconds, not a shortened substitute; ordinary
holds remain 15 seconds with ten-second entry waits. First disposal failure is
observed through its actual task. Final cleanup releases the barrier, joins
public commit, first disposal, every started settlement observation and actual
settlement, then retries disposal even if a join fails. No returned failure or
completed public task is promoted to resource release.
Current native selection is 31 scopes/134 observations, pending. Full schema
setup/upgrade extraction, actual adapters, unchanged wrapper parity and complete
category acceptance remain open; T019..T086 are still unchecked.

### Typed schema consumers and actual state fingerprints

Five methods bring the executable slice to 52, covering six schema rows:
unrecognized and partial layouts, authorized legacy upgrade, invalid/foreign
authorization, concurrent upgrade exclusion, and future/recognized-corrupt
state across reopen. Common code takes typed sessions and uses actual inspected
current/target versions; no provider-name branch, private schema number or
version-suffix rewrite enters its expectations. Legacy setup remains caller-
owned. It preserves registry/package/cache-entry/aggregate readback, changes
admission epoch, expires the old receipt and re-admits the same epoch on reopen.
Rejected layouts/upgrades also preserve state hashes and deny ordinary admission.

The required typed `ObserveStateAsync` returns an actual private state hash.
Memory's fixture-only helper hashes schema/epoch/time/change state, raw encoded
records, reference edges, dependent sets and operation ledger. Domain/section
tags, collection counts, length frames and deterministic order preserve structure;
raw damaged payloads are neither decoded nor repaired. A focused regression
observes unchanged hashes, distinct actual record damage and schema mutation.
The nested schema probe reopens real Memory images and explicitly cannot be
admitted as a complete binding; missing generic controls/cleanup observation
throw, rather than supplying passing observations.

The six consumer rows initially failed missing API/probe compilation. The full
source-only probe now passes 67 tests without skips; SDK tests pass 108. All 236
tooling checks pass with ten native macOS skips; focused SDK and Memory formatting,
catalog, frozen inventory and whitespace checks pass. Bounded architecture review
found no actionable defects in extraction, raw fingerprints or upgrade ownership.
Current native selection is 32 scopes/141 observations, pending. Full adapters,
factory admission, unchanged wrappers and complete category parity remain open.

Native run [40057842920](https://github.com/Stonefly-Labs/Hoard/actions/runs/40057842920)
at `8df0cc67c183bf3d9f7ef016f716a9bae9039aa4` verified all 41 earlier consumers,
including the lease/deadline rows and pre-canceled reservation ordering repair.
All three jobs succeeded: 131 foundation checks without failures/errors/skips,
30 scopes/127 discoveries/127 executions, six historical baselines and identical
eighteen-package/thirteen-lock replay. Input digest:
`66c0778b4286c575a33d24e289da68758199371bb9f043ecf00669c285dc5762`;
preparation proof:
`17711c00cfeee7698e747b0f98de5d6ace3a00ecee3a667ca7c34fd35ee30a20`.
Free scratch was 92,110,221,312 bytes. This remains non-qualifying diagnostics.

### Typed malformed-continuation consumer

The 53rd method preserves all six malformed cursor shapes across closed logical
contract-version/epoch/schema/query/page-size/position controls. Common code owns
the component inventory, InvalidInput/CorrectInput/Page classification, exact
valid resume after every failure and complete remaining/full traversal. Private
field names, JSON and base64 stay in the concrete bridge. Memory's schema
identity uses its epoch, so both controls target that field while all five
physical cursor fields remain covered. The new required method signature is
also exposed as a typed delegate for prepared stores.

Missing typed-control compilation failed first. All six source rows pass; a
paired no-op mutation fails the exact common IsType assertion, and real Memory
damage passes the unchanged compiled delegate. Source-only Memory now passes 74
tests without skips, ordinary SDK 108; tooling 236 with ten native macOS skips,
focused formatting, catalog, frozen inventory and whitespace checks pass.
Actual discovery confirms the six enum identities and paired negative.
Current native vector is 33 scopes/148 observations, pending. This does not
complete typed adapters, inherited wrapper parity or T019/T021 acceptance.

Native run [40058311447](https://github.com/Stonefly-Labs/Hoard/actions/runs/40058311447)
at `449636a677ea6ee8f7a3c6380e8773ddbf4f3eb4` verified all 47 earlier consumers,
including actual ledger filling, the real 30-second cleanup failure with work
still owned, and the dropped-diagnostic negative/control. All three jobs passed:
131 foundation checks without failures/errors/skips, 31 scopes/134 discoveries/
134 executions, six historical baselines and identical eighteen-package/
thirteen-lock replay. Input digest:
`e3206dfcb1ab2685463eb3647cb91c07c9e4a946343cbf4bc0d500b7a6499aff`;
preparation proof:
`e88a943cd304ee70607ccc074f35af2a49be5bcc5db45cdbcec666d071e1b705`.
Free scratch was 92,109,975,552 bytes. Schema/newer source results are not
substituted for native execution or qualification.

### Explicit legacy factories and genuine settlement identity

Typed bindings now expose `CreateLegacySessionAsync`; the observed wrapper's
`OpenLegacyAsync` uses the same admission, cleanup ownership and lazy-getter
path as current creation, without case-ID routing. Both represent fresh root
creation in the existing origin protocol; reopen lineage is unchanged. A
regression uses an arbitrary case ID, proves only the legacy factory ran, and
captures the actual pinned roles without early getters.

Memory's fixture exposes `ObserveWorkSettlementForTest` separately from its
existing ten-second bounded `WhenIdleAsync` observer. A held-worker regression
observes the public deadline, verifies the genuine task remains pending with
stable identity, then releases and joins public/actual work. This is a prerequisite
for concrete adapters passing genuine settlement to the resource ledger, not
proof of resource release or a completed adapter.

Missing APIs failed compilation first. Ordinary SDK tests pass 109 and source-
only Memory passes 75 without skips. Tooling236/ten native macOS skips, focused
SDK/Memory formatting, catalog, frozen inventory and whitespace checks pass.
Current native selection is 34 scopes/150 observations, pending; the shared
consumer count remains 53.

Native run [40058954688](https://github.com/Stonefly-Labs/Hoard/actions/runs/40058954688)
at `cf9c20f2d9bdbc797ce5c4cacddd13966b02fa3d` verified all 52 earlier consumers,
including actual schema upgrade/reopen/exclusion and raw fingerprint mutation.
All three jobs passed: 131 foundation checks without failures/errors/skips,
32 scopes/141 discoveries/141 executions, six historical baselines and identical
eighteen-package/thirteen-lock replay. Input digest:
`f3f0c286237ef7f0708ffd9a14d0434ca6070b2b08128470fc2dd6c319d629b9`;
preparation proof:
`035624cf6eebad450d3f1e50b919466ef363cd6227180639b0d0a2472a04c5ab`.
Free scratch was 91,725,152,256 bytes. Complete bindings/parity remain open.

### Concrete Memory adapter and package-only control execution

`tests/fixtures/conformance/Bindings/Memory/MemoryBinding.cs` now implements
explicit current/legacy creation, actual store/schema/authority/fault roles,
controlled UTC time, logical image reopen and resource-ledger ownership.
Atomic close/capture excludes new work before preserving immutable raw state.
An independent committed-read seam remains inside the provider's actual
activity ledger and bypasses only held test observers/late public-call admission,
without changing public provider operations.

Required typed controls use actual Memory mechanisms. Generic gates expose
named actual boundaries; one-shot capacity consumption and typed raw mutation
observations are non-holding. Memory's managed held callback is not a native
database or process-crash guarantee. Private record/operation/continuation
damage now lives in reusable provider-private `MemoryPayloadDamage`, also used
by the existing probes. SDK references remain provider-neutral.

Disposal closes admission before capturing the genuine stable idle promise.
Allocator observations run alongside public disposal, never replace its task
with a timeout/public-completion promise, preserve identity on retries and never
claim physical `Released`. Resource-observer errors surface rather than becoming
settled observations. A real-allocator integration holds actual work, observes
retention, rejects premature allocator disposal, then retries with the same
genuine task while preserving prior failure history. Only that allocator's
observation budget is 20ms; the provider's real 30-second cleanup stays intact.

The first adapter test failed compilation for the absent binding. The focused
snapshot test initially compared caller-supplied revision bytes instead of the
actual committed public snapshot; it now compares exact committed encoding.
The cleanup double initially threw a raw observation timeout; matching the
allocator's structured `Retained/CleanupIncomplete` semantics preserves the
actual provider's incomplete-cleanup failure. Nineteen adapter unit rows and
one actual-allocator row now pass with all 75 earlier Memory probes against
freshly packed SDK/provider/binding packages: 95 tests, no skips, ~34s. Shared
source SDK109, tooling236/ten native skips, catalog, frozen inventory and
focused whitespace/format checks pass. A bounded custom architecture review
found no actionable defects in the adapter/ownership/package boundary.

The package-mode test graph deliberately adds the existing Memory binding
package and links the same Consumer test source; its tracked lock was generated
with the package manager. Native preparation now builds/derives/reverifies the
binding archive and captures all five actual package identities/runtime bytes.
Current diagnostic vector: 37 scopes/170 observations, verified below. Source/local
package success is not Linux supervisor, full role-origin or category proof;
T023 and complete bindings/parity remain unchecked.

Native continuation run
[40059263911](https://github.com/Stonefly-Labs/Hoard/actions/runs/40059263911)
at `f7d7756910f9ca47ae4ed696094a7c50b2288160` verified all 53 earlier consumers:
all three jobs, 131 foundation checks without failures/errors/skips,
33 scopes/148 discoveries/148 executions, six historical baselines and
eighteen-package/thirteen-lock replay. Input digest:
`a6c7d76fead1013ff1cbdd71db4bef9e8b25d27e250bf936a05ff4c20873171f`;
preparation proof:
`433c6a0ceed8fad880a5eeed6130e74188e83b49b9af96f3402bc44d9b240719`.
Free scratch: 92,109,885,440 bytes.

Native factory/settlement run
[40059814134](https://github.com/Stonefly-Labs/Hoard/actions/runs/40059814134)
at `46be806d30be26f47fafaa9b064241c48759d75c` also passed all three jobs and
131 foundation checks without failures/errors/skips, 34 scopes/150 exact
discovery/execution observations, six baselines and eighteen-package/thirteen-
lock replay. Input digest:
`be49fdd9b29de2382622b3dc2d77166d5b680fd6b8c76511433725626998becd`;
preparation proof:
`bd7ecd7d3a3e27b88232c8625ca037fd45d7b2a7df2cb445fc1dfcb6603d6c3d`.
Free scratch: 92,109,897,728 bytes. Neither run includes the new concrete adapter.

Native binding run
[40061416909](https://github.com/Stonefly-Labs/Hoard/actions/runs/40061416909)
at `9be7ad73b34e17b59a5c982b59d9645532f70f72` passed all three jobs:
131 foundation checks without failures/errors/skips, 37 scopes/170 exact
discoveries/executions, all concrete Memory adapter rows, six historical
baselines and byte-identical eighteen-package/thirteen-lock replay. Input:
`e8a0ea337babef2f29d884e12be691c654b127c7a657e526ee30181108c10b00`;
preparation proof:
`f7bae966d851b9b034d9d6c620122dc89ad1fe73de922db625e2c5567647bf5f`.
Free scratch: 91,724,914,688 bytes. No category qualification follows.

### SQLite genuine lifetime prerequisites

The SQLite fixture exposes its stable actual worker task separately from its
bounded idle observer. New async independent read/writer controls register
under that lifetime before work starts. Read work participates in idle; held
writer leases do not, because writer-budget consumers legitimately observe
idle while holding the writer. Shutdown closes admission, releases owned
writer leases, waits for real independent work and then closes primary native
handles. Caller cancellation does not erase ownership; late acquisitions close
their actual handles before lifetime completes. Escaped diagnostic or native
lease-cleanup failures surface through genuine lifetime, not unobserved tasks
or successful cleanup observations. Existing synchronous fixture controls
remain caller-owned and are not the new adapter's ownership seam.

Six focused source-probe tests pass without skips: public-deadline retention
and native-handle cleanup/reopen; independent read idle/lifetime; writer lease
idle versus lifetime; canceled independent read retention; canceled late writer
acquisition; and escaped diagnostic failure with faulted lifetime. Missing
lifetime/read/writer APIs initially failed compilation; the late-acquisition
test separately failed at its missing actual observation boundary before the
async seam repair. Focused formatting passes. A bounded custom architecture
review found no actionable defects in this increment; it reviewed source
without independently attributing Git diff or rerunning checks.

This is not a concrete SQLite adapter, durable same-directory session handoff,
typed corruption suite, package/native SQLite environment production or full
T022 acceptance. No public operation contract, schema, project reference or
production architecture changes. T019..T086 remain unchecked and implementation
continues; the reviewer-owned checklist markers remain untouched.

### Initial concrete SQLite binding and seven-archive package execution

`SqliteBinding` now supplies explicit current/legacy factories, actual typed
roles, harness clock and tracked async independent controls. Reopen closes and
joins the old native worker before transferring the same owned directory and
database to a current-compatible session. It does not copy database files,
allocate a replacement root or bind the old task to a directory subsequently
reused by another worker. Old-session disposal cannot release the new head's
root. Final-head disposal closes admission, pins the genuine final worker task,
preserves identity on retries and never reports physical `Released`.
Canceled reopen preserves the original owner/actual pending work for disposal.
Actual verified backup files under that root authorize upgrades.

Provider-private raw record/operation controls preserve exact encoded data,
native BLOB/TEXT/NULL fingerprints and fractional REAL state. Typed scopes
fingerprint damage, corroborate public failures/effects, restore exact original
rows and verify original-ticket replay. Continuation mutation uses SQLite's
actual six opaque fields. Raw state observation works before admission and on
unrecognized/future/corrupt/oversized state, without decoding or repair.

The bounded custom architecture review found a MEDIUM native-sort defect:
full-payload SQL ordering could sort excessive input before managed size limits.
The intended regression first accepted an oversized unindexed native row.
Native value-size/progress limits and a bounded size/count preflight now precede
full-row hashing; native full-payload sorting was removed. Managed sorting
retains only bounded 32-byte row digests. Native limits alone did not reject
the aggregate existing row, so the regression remained red until size preflight
was added. It now passes alongside exact raw preservation/restoration.
Bounds are 128 schema objects, 64 columns/table, one million rows total,
2 MiB/cell, 2 MiB + 64 KiB/native row and 256 MiB hashed input; the actual
five-second worker budget also drives SQLite's progress handler. Existing
incompatible state rejects explicitly when it exceeds those fixture controls.

The logical publication authority implementation is compiled from one shared
BCL-only fixture source into both independent binding assemblies, rather than
SQLite calling Memory or adding provider/encoding types to the SDK. Provider
mechanisms and product reference edges remain unchanged.

Actual package-only selection passes 135 tests without skips: 95 existing
Memory/adapter rows and 40 SQLite mechanism/adapter rows, including real
30-second incomplete cleanup, three actual schema/backup consumers, same-root
handoff, canceled handoff, six continuation shapes, fourteen receipt shapes
and five record shapes within their shared consumers. The absent binding/raw
APIs failed compilation before implementation. The earlier source-only SQLite
run passed 37, the canceled-handoff case then passed separately, and the
native-bound regression subsequently passed after its intended failures.
Memory source94 also passed after sharing authority.

An additional intended failure supplied 128 multi-byte fingerprint characters
(256 UTF-8 bytes). Replacement now enforces the same 128-byte bound as raw
capture before any mutation, with structured `InvalidInput` and unchanged state.
All five raw-operation cases and the full 135-case package selection pass.
Fresh cache and build output directories were required: canonical archive
timestamps otherwise left an earlier same-version DLL in reused build output.
The updated archive/cache DLL hashes were checked against the actual output;
no earlier feed/cache evidence was overwritten.

Seven current local archives were packed through private graph-preserving
derived locks. NuGet deliberately generated the package-mode lock addition:
only the SQLite binding/provider and six pinned SQLite dependencies were added;
prior graphs and all existing third-party hashes are unchanged. A second empty
cache default locked restore/build passed without warnings/errors or lock
changes. Tooling236 (ten native macOS skips), focused formatting, frozen
inventory, SDK catalog and whitespace checks pass. The native SDK diagnostic
now prepares/derives/reverifies all seven archives, but its selected executions
remain the existing 37 Memory/SDK/logger scopes until actual SQLite environment
production is implemented. SQLite must not borrow `nativeSqlite: not-used`.
No SQLite Linux-supervisor, abrupt-crash, role-origin/controller or full
category qualification follows from these local package checks.

Native prerequisite run
[40062534006](https://github.com/Stonefly-Labs/Hoard/actions/runs/40062534006)
at `a81c0380f6bed06d8870c6b43263aa480ae5d04b` passed all three jobs:
131 foundation checks without failures/errors/skips, the earlier 37 scopes/
170 exact observations, six baselines and eighteen-package/thirteen-lock replay.
Input digest:
`12d9b6f9217f8bcd55f59657d41972652d746d71e44fb4fc6d55fb43a7c3a381`;
preparation proof:
`70790529869264a78361c61119a4184b4c900f9887490d46d6746fcee0574f23`.
Free scratch: 92,109,668,352 bytes. It predates the concrete SQLite binding and
seven-archive diagnostic graph; no expanded execution is attributed to it.
T022/T023 and full category/parity acceptance remain unchecked.

### Actual SQLite environment producer, pending Linux verification

The package-mode test assembly now has an explicitly selected test-only entry
point for owned environment observation, not a product executable. The test SDK's
generated entry point is disabled only in package mode. The producer opens the
real SQLite binding through the native resource allocator, prepares its schema,
reads actual PRAGMAs/native version and captures the loaded `libe_sqlite3.so`
module path relative to immutable runtime output plus its SHA-256. It awaits
genuine session settlement before writing a path-free report; physical release
remains the parent controller's responsibility after actual exit.

The parent checks exact schema/configuration/runtime/architecture, compares the
loaded file with the selected member of the exact locked NuGet archive, and
records external archive SHA-256/SHA-512/source mapping provenance. Native runtime
assets now join pre/post input hashing. A missing-API environment admission
regression and a native-asset mutation escaping recomputation both failed first;
the repairs pass, with all 135 existing package-selected tests still passing.
Linux producer execution is not yet observed. Selection stays at the existing
37 Memory/SDK/logger scopes; no SQLite-case or full category pass is inferred.
No new dependency/package/project, product executable or qualification is added.

### Complete current logical consumer coverage through the SQLite binding

The remaining 38 current SDK assertion methods now execute through the actual
SQLite binding, adding 44 exact parameterized rows. They use the same compiled
assertions as Memory and typed independent-read, corruption, publication,
writer, clock and settlement controls. No SDK assertion or provider-selected
expectation changed. All 44 added rows pass; full package selection passes
179/no skips (95 Memory, 84 SQLite). All 53 current SDK metadata assertion
methods are invoked by the SQLite binding suite, including previously checked
schema/receipt/cleanup paths. These 179 local unit identities are not the
catalog's 179 applicable category keys. Full frozen-wrapper parity, abrupt
recovery, native origin/controller imports and category qualification remain
unchecked; T019..T086 are not advanced by this focused coverage increment.

Native seven-archive checkpoint
[40064540294](https://github.com/Stonefly-Labs/Hoard/actions/runs/40064540294)
at `721231acffcc801d8b60467391f0c4ac7cdb43ed` passed all three jobs:
131 foundation checks without failures/errors/skips, 37 scopes/170 exact
observations, six historical baselines and identical eighteen-package/
thirteen-lock replay. Input digest:
`b3cfcb3f9e0bf3dd02784ca2699eb1392f89d2963425b9beb537ed222a80b6f3`;
preparation proof:
`738dbcf048cb1b58193f954caf0130b706e49f2f3d329448cb765016db2e9e90`.
Free scratch: 92,109,443,072 bytes. It predates the environment producer and
additional SQLite logical rows; no SQLite execution is attributed to it.

### Native environment repairs and explicitly gated SQLite diagnostic selection

Native run
[40065028512](https://github.com/Stonefly-Labs/Hoard/actions/runs/40065028512)
at `2ba946511971bb47a5186f1e6bbac28f61c97c80` passed 132 foundation checks with
zero failures/errors/skips, but SDK diagnostics failed with `InputChanged` and
preparation failed with `CS8892` at command 169. Neither job qualified.
The real restored signed native archive reproduced the mistaken comparison of
normalized NuGet content hash with raw archive SHA-512. The parent now checks
both separate fresh locked-restore receipts: normalized content remains pinned
through NuGet metadata, raw archive SHA-512 matches the cache receipt, and
selected member bytes match the observed runtime native file. Full provenance
must remain identical after execution; no dependency/hash pin is edited.
The focused normalized-versus-raw regression failed first and now passes, as
does preparation using actual restored signed archive/member bytes.

The probe's source is explicitly excluded from the general package consumer,
preserving its generated test entry point. That exact consumer now restores
through private graph-preserving locks and builds from a fresh cache against
eleven actual current archives with zero warnings/errors. The additional
artifact manifests remain stubs, not new artifact bindings or qualification.
Missing temporary-directory routing also failed first: all owned child temp
variables now target private cache directories. A Linux-only child regression
checks actual temporary-file placement, not environment labels alone.

The request expands to 50 diagnostic scopes/254 exact observations, including
all 84 actual SQLite test identities. Local package-mode discovery matches that
entire SQLite set. Missing/unused environment, wrong PRAGMAs or absent native
runtime hashes reject before discovery; positive routing selects the exact
package-mode assembly. Those routing regressions failed before repair.
Portable tooling239 passes (228 passed, eleven native macOS skips).
Successful Linux producer/SQLite-case execution remains pending, and no catalog
qualification, durable crash proof, wrapper parity or origin/controller pass is
inferred. Existing 37-scope native receipts remain historical and unchanged.

### Verified native SQLite environment and all selected common consumers

Native run
[40066075996](https://github.com/Stonefly-Labs/Hoard/actions/runs/40066075996)
at `e6c4256bcb71fb7726344d714cdba2b83b72b547` passed all three jobs:
134 foundation checks without failures/errors/skips, 50 scopes/254 exact
discoveries/executions with expected diagnostic codes, including all 84 SQLite
identities, six sealed baselines and identical eighteen-package/thirteen-lock
replay. Actual SQLite 3.53.3 used WAL/FULL/foreign-keys/busy-timeout-zero;
native temporary placement also passed. Free scratch: 92,109,283,328 bytes.
Baseline seal:
`41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`;
input:
`f62bb15ae3eb9f61b0d41b8877f357a952b8ec66115cb2f729bcaf86eb19fdb6`;
preparation:
`7d07bbef488638178a8d215491ac7601bef81628dc1014d156bb5dcc21569ae4`;
loaded native library:
`b0f5c48026fedcf9f05cf31c6fadf9e1e001ca59cd85aa68b8b6814e52c18a07`;
native package archive:
`d07d13b4779123cfa56b3348b504d57a2ab6fc10c764fb6e2c9d787987e39201`.
The normalized pinned NuGet content hash and raw archive SHA-512 were both
verified independently through their fresh locked-restore receipts. This run
establishes actual selected Linux SQLite execution, not full frozen-wrapper
parity, abrupt recovery, origin/controller qualification or a category pass.

### Isolated native non-cooperation diagnostic

The next increment requests the real five-minute SQLite native stall through
the typed binding at its post-commit boundary, exclusively in a dedicated
parent-owned package-mode child. A one-second caller deadline must yield
`Uncertain/Commit/Reconcile` with the original ticket while the publication
guard remains held. Genuine 30-second cleanup must record incomplete cleanup,
disposed admission, retained allocator history and the still-pending actual
worker task. The child never deletes resources, reports release or returns a
passing result; it waits for exact-owned containment.

The parent requires a separate immutable recovery-command receipt binding
the actual child PID/start identity, monotonic duration, `DeadlineExceeded`,
SIGKILL and confirmed process-group exit after its 45-second watchdog. Producer
observations must match the frozen input digest and controller PID/receipt;
normal exit, setup failure, missing proof, live children or inconsistent
guard/cleanup/ticket observations reject. Recovery receipts are written beneath
the pinned proof directory with exclusive no-follow creation after observation.
This is a closed expected-fault diagnostic, never generic timeout-as-success.

The missing admission API first failed the focused regression. Its positive
and contradictory producer/controller cases now pass, as do early-exit,
setup-failure, missing-proof and live-child rejection. Tooling241 passes
(230 passed, eleven native macOS skips). A fresh private seven-archive locked
restore and package test passes 179/no skips, with all seven output DLLs
byte-identical to current archives. The two probe sources are excluded from
the general consumer; its actual package build and the package-mode producer
compile with zero warnings/errors. Focused whitespace checks pass.
Bounded architecture review found no actionable issues. Actual Linux verification
is recorded below. T022/T026 and full category/wrapper/origin gates remain
unchecked; no existing historical receipts or source locks changed.

### Verified actual native non-cooperation and exact-owned containment

Native run
[40067365972](https://github.com/Stonefly-Labs/Hoard/actions/runs/40067365972)
at `7530cad06a9010b69b570d48610e3a7479a4f852` passed all three jobs:
136 foundation checks without failures/errors/skips, the same 50 scopes/254
exact discoveries/executions with expected diagnostic codes, and the dedicated
native producer/controller pair. Actual SQLite 3.53.3, WAL/FULL/foreign-keys/
busy-timeout-zero, loaded native/archive provenance, six sealed baselines and
identical eighteen-package/thirteen-lock replay also passed.
Free scratch: 92,109,389,824 bytes.

Baseline seal:
`41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`;
input:
`9446cd06ee92bbb30603ee5d611f8c1089de307cfdd1c25d53b314ba2cf05a30`;
preparation:
`a2260c969ae7f9b5ab6f886a19c6e6505d5e65f1e798800ed579f0ee4e85ec25`;
native producer:
`d309875c00837713387d60d35f60759cf45a18bff927def1e325fdd86ec0ad64`;
controller:
`52f0919856d3c19355be49443c5780a4dce727cf83da962c4829091f021388e7`;
child start:
`c0ad251e40f4fc0f1dd8022ddafbc5af6eafcc9d8e737a646343ef51d57d9eec`.
The native library and native archive SHA-256 remain respectively
`b0f5c48026fedcf9f05cf31c6fadf9e1e001ca59cd85aa68b8b6814e52c18a07`
and `d07d13b4779123cfa56b3348b504d57a2ab6fc10c764fb6e2c9d787987e39201`.
This remains `qualification: false`, `mode: native-noncooperation`, `code: None`.
It proves the actual selected native ownership/containment diagnostic, not all
inherited abrupt recovery, frozen-wrapper parity, origin/controller imports or
category qualification. No broad task marker changes follow from this result.

## Partial implementation checkpoint

### First frozen logical wrappers use the packaged common assertions

The seven original MP-01..06/13 wrappers now delegate to the existing SDK
entity/identity/bounds methods. Their fully qualified method names and `[Fact]`
attributes remain unchanged. The original fixture factory, schema preparation,
clock and disposal remain in place; a private authority-interface bridge
forwards registration, revocation, guard counts and acquisition without owning
another authority, changing expected results or introducing provider switches.
The SDK itself is unchanged and still references only Abstractions and xUnit.

Metadata preparation copies/packs the SDK before the package-only wrappers and
admits eight archives. The tracked package-mode test lock adds only the SDK
entry; all existing entries, graphs and third-party pins remain unchanged.
A private source snapshot prepared current local archive identities without
editing repository or retained historical locks. An independent default locked
replay with a fresh cache reproduced all eight archives byte-for-byte; all seven
actual wrapper dependency DLLs and Application's separately built DLL matched
their respective archive members. An initial verification helper incorrectly
looked for Application in the wrapper output, although the suite does not
reference it; checking its actual build output repaired that evidence check,
not a runtime or dependency failure.

The identical package-backed predecessor suite executed all 72 tests against
Memory and all 72 against SQLite, with no failures/skips. The frozen SDK output
now joins test/consumer hashes and is checked after each composition. Missing
SDK preparation first failed with absent pack discovery; an SDK-only mutation
first passed incorrectly, then failed after the guard. Tooling243 passes
(232 passed, eleven native macOS skips); focused package-backed whitespace
verification, frozen inventory and SDK catalog checks pass. These local results
are not new native CI receipts, full wrapper parity, exact safe origin imports
or a category pass. T019/T021..T025 remain unchecked.

### Further pure paging, concurrency and reference wrapper adoption

Ten further original methods now delegate to unchanged SDK methods:
MP-07's three query/bounds/dataset wrappers, MP-08 scope/epoch, MP-11/12
create/revision races, MP-23 publication evidence and MP-24/25/31 reference/
ABA/telemetry checks. This brings actual adoption to 17 methods across fifteen
MP keys. Existing frozen names/attributes, six malformed-continuation theory
rows and all remaining control-dependent assertions are preserved. The foreign
store required by MP-08 still uses the original independent fixture factory
and owned disposal; the common consumer chooses no provider.

The actual repository package-mode project restored in locked mode against the
previously verified eight-archive private graph with an explicit private lock.
No source lock or SDK/provider archive changed. One fresh test assembly passed
all 21 affected class tests against Memory and all 21 against SQLite without
failures/skips; the second composition used `--no-build`. Focused whitespace
and frozen inventory checks pass. These are focused local wrapper regressions,
not complete category, native recovery or exact runtime-origin acceptance.

### Scoped original observation controls and five more common wrappers

Original MP-09's independent/faulted candidate wrappers, MP-10 grouped reads
and MP-26/27 orphan/retained-publication wrappers now call unchanged SDK
consumers through typed observations (22 original delegated methods total).
The original atomicity diagnostic check remains and additionally rejects the
SDK's injected canary. Store setup, original authority and lifecycle ownership
remain fixture-owned; the SDK does not depend on HostAdapters or providers.

The fixture adds scoped observation registration using an atomic dictionary
admission and registration-specific callback identity. Duplicate admission
rejects without replacing the current observer. Idempotent disposal removes
only its own callback, leaves a newer legacy registration intact and neither
cancels nor settles an in-flight callback. A cancellation-aware independent
read overload preserves the original signature; concrete schema-hook mapping
stays in the fixture. The typed bridge rejects cancelled/unknown requests
without leaked registrations.

Three focused ownership tests first failed the missing-method assertion in an
otherwise successfully compiled package-mode test assembly. They subsequently
use the typed API directly. The first control preparation encountered a nested
test declaration (`CS0106`); this was repaired before execution and is not
counted as an intended behavioral red. A fresh preparation passed all 76 tests
against Memory and all 76 against SQLite without skips. After adding the
actual schema-hook test and SDK-canary assertion, a fresh default locked replay
passed all 16 affected tests against each provider. The latter includes all
five observation tests and actual legacy-schema upgrade callbacks on both
implementations.

The independent fresh-cache replay reproduced all eight archives. All seven
wrapper dependency DLLs and the separately built Application DLL matched
archive members. Only the additive HostAdapters fixture archive differs from
the prior increment; SDK, providers and platform archives are identical.
Current source and historical locks remain unchanged; private preparation
rebinds only current local archive identities while preserving graphs/pins.
Tooling243 passes (232 passed, eleven macOS-native skips), as do frozen
catalogs and focused compiled wrapper/fixture whitespace checks.

This is not complete control/schema/corruption extraction, safe exact origin
ingestion or category qualification. In particular, the original SQLite MP-35
exclusion wrapper observes U1, whereas the existing SDK's `BeforeSchemaUpgrade`
mapping observes U0. Full parity must preserve the original U1 subproof rather
than silently substituting the new hook. T019/T021..T026 remain unchecked.

### Preserve the actual writer-held schema exclusion boundary

The new real-connection regression initially observed `BeforeSchemaUpgrade`
at U0. An independent `BEGIN IMMEDIATE` succeeded, failing the named expected
SQLite BUSY (5) assertion with actual null. The repair adds the distinct
`SchemaCandidatePrepared` enum member at the end, preserving existing values
and U0 semantics. SQLite maps it to U1 after candidate-table creation within
the native write transaction; Memory maps it to its real upgrade decision.
The unchanged shared exclusion consumer and original MP-35 use that boundary,
with concrete hook names remaining fixture-private.

Final formatted archives pass 180 selected SDK/binding tests without skips.
The independent original-wrapper preparation/default locked replay reproduces
eight archives and exact seven dependency DLLs plus the separate Application
DLL. Its SDK archive is byte-identical to the seven-archive binding feed.
All 11 original schema/observer tests pass without skips against each provider.
Only the SDK content hash changes in the tracked predecessor test lock; its
dependency graph, all other entries and historical pins remain unchanged.
Tooling243 passes (232 passed, eleven native macOS skips), frozen catalogs and
focused whitespace checks pass. The requested native vector grows to
50 scopes/255 observations, including 85 SQLite identities; its Linux execution
is pending. This repairs the focused U1 parity gap, not complete extraction,
abrupt recovery or exact origin/controller ingestion. T019/T021..T026 remain
unchecked.

Earlier native run
[40068886475](https://github.com/Stonefly-Labs/Hoard/actions/runs/40068886475)
at `5528ecd0042e2efe38cbcbc2d02ee2824859f1ca` passed all three jobs: 136
foundation checks without failures/errors/skips, 50 scopes/254 observations,
actual native containment, six baselines and identical eighteen-package/
thirteen-lock replay. Free scratch: 92,109,242,368 bytes. Input:
`b48a18e304c759ec50856c694fc1de816180c0006c5d34f158e6e88d70666d04`;
preparation: `6a97865603dadee2f809ac3d0f1364a04959f2967ade03a06b9e8ec5fd898551`;
producer: `fecbaafa13859dbd633a934adffc4495727ebff678424eddf9e9bbb68593d8c9`;
controller: `67e7e728fd8319965925e02492558e2fe3caa76eff96831a979c8ceb100b2cf3`;
child start: `f6eac5a379d3d34ccde54da8bb0696b3cdadf3d07f41255bc383bf2fdc087b1a`;
baseline seal: `41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`.
That run does not execute original predecessor wrappers or the new U1
regression. SQLite remains 3.53.3 with unchanged pinned native provenance.

### Original malformed-continuation wrapper extraction

The six frozen MP-08 malformed-continuation rows now delegate to the existing
shared SDK consumer (23 original delegated methods total). A typed test-side
bridge forwards semantic component/shape requests to the original fixture;
concrete field mapping stays fixture-private and reuses each provider's existing
independent payload-damage helper. Neither shared assertions nor the bridge
select a concrete provider. Memory's combined epoch/schema field remains
covered rather than inventing another encoded property.

A new parity guard first failed the named missing-fixture-method assertion
in an otherwise successfully compiled package-mode test assembly. After repair
it decodes an actual valid continuation, exercises every typed component and
proves all original fields are covered, exactly one is omitted per request and
other values remain unchanged. Cancelled/unknown requests reject and valid
continuation bytes remain unchanged. All six inherited shape rows still check
structured failure, valid resume and complete subsequent traversal through the
unchanged SDK consumer.

All 79 current predecessor tests pass without skips against Memory and SQLite
using the identical compiled suite and SDK. Fresh empty-cache default locked
replay reproduces all eight archives and seven wrapper dependency DLLs plus
the separate Application DLL. Only the additive HostAdapters fixture archive
changes from the schema repair; SDK/provider/platform archives and repository/
historical locks remain unchanged. Frozen inventory and focused compiled
whitespace checks pass. Complete control/session extraction, exact safe origin
ingestion and category acceptance remain open; T019/T021..T026 are unchecked.

### Original admission, capacity and pure lease wrappers

Six MP-19/20/28/32 methods now delegate to existing shared admission,
storage/ledger capacity and lease overflow/owner-generation-revision fencing
consumers (29 original delegated methods total). Exact names/attributes are
unchanged. Admission retains its fresh unprepared fixture; invalid budgets
still guarantee disposal in the shared consumer's `finally`. Capacity and
generation callbacks check cancellation before forwarding original controls.
A test-side counter bridge reads actual fixture boundary activity and diagnostic
occurrences; it supplies no provider-selected expectations.

The actual repository test project restored in locked package mode against the
previously verified eight-archive graph with an explicit private lock.
The same freshly compiled suite passed all 16 affected class tests against
Memory and SQLite without skips. Its seven actual dependency DLLs match archive
members. Focused whitespace and frozen inventory checks pass; ordinary source
assets are restored. No SDK/provider/fixture archive or source lock changes.
Clock/deadline/corruption/session extraction and exact origin/controller imports
remain unfinished. These six delegates do not complete T019/T021..T026.

### Original clock ownership and three time-dependent delegates

MP-17 ticket expiry/rollback and MP-29/30 lease decision/rollback now share
SDK consumers (32 original delegated methods). Additive callback overloads
drive the original `MetadataTestClock` actually supplied to the fixture store;
the existing SDK clock-object signatures forward to the same assertion bodies.
There is no alternate clock, provider-selected expectation or duplicated
consumer logic. MP-29 retains all three renew/release/guard subproofs with
separate fresh fixtures and final-decision observations.

A new regression first failed the missing callback-overload assertion in a
successfully compiled package-mode assembly. Its repaired actual-store body
drives the original clock backward and verifies new ticket issuance keeps
the expiry-based monotonic floor. All 80 current predecessor tests pass on
each provider without skips. All 180 selected SDK/binding tests pass against
final formatted archives, including existing clock-object call sites.
Fresh empty-cache locked replay reproduces eight archives and seven wrapper
DLLs plus the separate Application DLL. The seven-archive binding output DLLs
match archive members and its SDK archive is identical to the wrapper feed.
Only the SDK hash changes in the tracked predecessor lock; graphs, other
entries and historical pins are unchanged. Tooling243 (232 passed, eleven
macOS-native skips), frozen catalogs and focused formatting pass.

### Native writer-held exclusion confirmed

[40070802352](https://github.com/Stonefly-Labs/Hoard/actions/runs/40070802352)
at `3bca09c36a15f29279de6f4d28c498cdd47e6a56` passed all three jobs:
136 foundation checks without failures/errors/skips and exactly 50 scopes/
255 discoveries/executions with expected diagnostics, including all 85 SQLite
identities and the real BUSY (5) candidate-boundary regression. Actual SQLite
3.53.3/PRAGMAs/native member provenance, native non-cooperation containment,
six baselines and identical eighteen-package/thirteen-lock replay also pass.
Free scratch: 92,109,254,656 bytes. Input:
`44d6e93b40e2eb6e89f120fc6b95c94848c293023647910cb9045b5edec1dc58`;
preparation: `a3dc25aa986c12802ee7df4ee615b9098e1eecd5220d45286cf7969542317f72`;
producer: `73e2d0e4180c0d44fb4ebe735a1dcfcb8832770cc829bcecbce0e484d7d7d55b`;
controller: `8aec3e932c184d2eff293a606d02960c4a9f7dced12c292cfe3586cc0c05da9d`;
child start: `c620ce3e9f495fe0ff220977b69ed5575a6f093df7f9fda5b851d9d016c1c3fe`.
The baseline seal and pinned native provenance are unchanged. This checkpoint
predates the callback-clock changes and does not run original predecessor
wrappers. Complete recovery, extraction and exact origin imports remain open.

### Original deadline and reconciliation ownership controls

Six original MP-18/19/37 deadline methods and five MP-14/15/16 reconciliation/
replay methods now call existing shared consumers (43 original delegated
methods). Frozen names/attributes, original fixture setup and actual writer
mechanisms remain unchanged. Settlement forwards the original actual idle
observation, not merely the caller result. Shared scopes own observation
registration; complete cleanup still requires the original fixture's disposal.

The fixture adds a cancellation-aware writer overload and preserves the prior
signature. Memory acquisition receives its cancellation token; native
pre-admission checks cancellation before the existing immediate writer hold.
A test-side async lease disposes only its acquired holder and is idempotent;
cancellation detected after acquisition disposes that holder before throwing.
A new regression first failed the missing-overload assertion. Its repaired
body proves cancelled acquisition cannot release an existing holder: the
held commit times out without effects and same-ticket retry succeeds after
the original holder releases.

All 81 current predecessor tests pass without skips against each provider,
including actual 30-second incomplete cleanup/retention, cancellation before/
after the decision, full queue ownership, concurrent disposal and uncertain
reconciliation preserving the original ticket. The same suite/SDK bytes serve
both compositions. Fresh empty-cache default locked replay reproduces eight
archives, seven wrapper dependency DLLs and the separate Application DLL.
Only the additive HostAdapters archive changes from the clock increment;
SDK/provider/platform archives and repository/historical locks remain identical.
Frozen inventory and focused compiled whitespace checks pass.
Corruption/schema extraction and safe exact runtime/controller-origin imports
remain unfinished; T019/T021..T026 stay unchecked.

### Original corruption ownership and independent native observations

Three original MP-21 methods and the MP-15 persisted-receipt method now call
existing shared consumers (47 delegated methods). All five query-dimension
rows and fourteen receipt shapes remain unchanged. A typed test-side bridge
maps corruption requests to fixture-private controls; no provider switch or
private database type enters the SDK/common consumers.

Original fixture scopes exclusively own each target, restore cancelled or
failed applied mutations, verify original raw hashes and retain failed cleanup
for explicit recovery. Disposal/reopen cannot abandon a live or retained owner.
Independent SQLite capture/observation reuses existing owned independent-work
execution and bounded native row readers, preserving BLOB/TEXT/NULL/fractional
state distinctions. The held-candidate fact reads both committed record and
reserved operation rows; substituting the queued getters failed that named
test. It also proves stale record/operation replacement returns `Conflict`
without mutation notification or changing committed images.

Bounded architecture review identified two real races. Atomic lifecycle
admission now excludes new corruption owners once closure/reopen begins.
Compare/exchange checks captured images under the actual native transaction or
Memory writer, so stale capture cannot overwrite a later acknowledged commit.
The controlled intervening-commit regression first failed its payload equality
assertion against the unguarded SQLite package. Actual idle settlement precedes
the applied-mutation decision and restoration verification; caller timeout is
not release, and failed settlement/restoration retains the recovery owner.
Closure/reopen ordering, overlap, cancellation and retry regressions pass.

All 87 current predecessor tests pass without skips on each provider using the
same compiled suite/SDK; 181 selected SDK/binding tests pass locally. Independent
fresh default locked replay reproduces eight archives and all actual DLLs.
Seven binding output DLLs match archives, and the shared SDK archive remains
identical in both feed families and to the prior clock increment. Repository
and historical locks remain unchanged. The expanded Linux request is 50
scopes/256 observations (86 SQLite identities); native verification follows.
Original diagnostics/schema extraction, exact runtime/controller-origin
integration and complete category/recovery gates remain open.

Native run [40097647586](https://github.com/Stonefly-Labs/Hoard/actions/runs/40097647586)
at `84e8a4bc1445d6ed79fc93365d720cd5f34dce51` passed all three jobs:
136 foundation checks without failures/errors/skips, exactly 50 scopes/256
discoveries/executions with expected diagnostics, all 86 SQLite identities
including held-candidate observations/stale-image rejection, native containment
and identical eighteen-package/thirteen-lock replay. Free scratch:
91,724,525,568 bytes. SQLite 3.53.3/native member bytes and PRAGMAs remain pinned.
Input: `3683becf9bb859ad2db6f555b5f6e7c6cdfaa55fd728447050ce9c9c9c0a6317`;
preparation: `2f4fac4dfd6d834a6594188d862b96aba8635a9eaf0689bfb1eaeaae96f09387`;
producer: `08c57d34158d4ea9cafea9d0303e3d8a6cfe50fc54895441b2afde194caa0e2f`;
controller: `a1dd1bee735ceee5a191cae58373cb849c530b14f31db27484fac5f3d3972a59`;
child start: `9a404081fa983f90e5cf28e294fe75c7e1a4e809889d2b2dad5ed4b1b66d223a`.
The six-baseline seal is unchanged. This checkpoint does not execute original
wrappers or establish category qualification.

### Original diagnostic hook ownership

The MP-22 wrapper now also shares consumers (48 delegated methods). Original
connection-shaped error injection and its initial failure checks stay intact.
An additive SDK overload takes a caller-installed real fault hook, original
canary and sanitizer, sharing counter/rollback, all failure-code and four
diagnostic/debug-display assertions. The existing API installs its scoped hook
and forwards to this same core. Neither path gives a provider expected results.

A new actual-store regression first failed the missing-overload assertion;
after repair it proves the original callback still owns its registration when
the consumer returns. All 88 current predecessor tests pass without skips on
each provider, and 181 selected SDK/binding tests pass locally. Independent
fresh locked replay reproduces eight archives and all actual DLLs; both feed
families use identical SDK bytes. Only the SDK hash changes in the tracked
predecessor lock, preserving all other entries and historical pins. The native
checkpoint above predates this increment and does not run original wrappers.
Schema/session extraction and exact runtime/controller-origin integration
remain unfinished; full feature gates and final review stay open.

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
reference edges and production provider contracts are unchanged. Complete common consumers,
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
