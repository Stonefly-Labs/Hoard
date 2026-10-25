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

Native run [40098981184](https://github.com/Stonefly-Labs/Hoard/actions/runs/40098981184)
at `11875e52e5c77c7f6953c6f1062afc7373f7713b` passed all three jobs:
136 foundation checks without failures/errors/skips, 50 scopes/256 exact
discoveries/executions with expected diagnostics, native containment and
identical eighteen-package/thirteen-lock replay. Free scratch: 91,719,897,088
bytes. Input:
`eb4c53bdb06caff9246aa0a05401ffe164cfdeb3e0a9b16df9b3eb19ac24e1c8`;
preparation:
`54d791988b5aa58f0baf168bd727716944f81b091c0e428c0158c7f768d8e1b9`;
producer:
`34696faa6cab04fdeeffcd6966d9d7e9283d10b9c118fc632792b9a490ecd055`;
controller:
`77c388d5cb3fb061ff0239efce61de847aa5c9f8e867382c152fafcd1e4854de`;
child start:
`77bcddc6ba2da5c5906cc1629a4b6d8ae3077b65e05de8dc1bd70e9dd95df2a1`.
Baseline seal and actual SQLite 3.53.3/native-member/PRAGMA pins are unchanged.
This gate does not execute original wrapper suites.

### Original schema session ownership

The five original schema wrappers now delegate (53 methods total), preserving
their exact names, unrelated/partial loop, original legacy factories and real
recovery authorization/reopen/U1 exclusion. A narrow
`IMetadataSchemaAssertionSession` exposes only these actual controls; it does
not pretend to implement a full category binding or unsupported fault hooks.
Existing full-session signatures project into the same shared assertions.
Memory observes actual immutable logical state; SQLite preserves inherited
physical database/WAL byte checks through worker-owned streamed fingerprints.
Initially observed WAL files remain mandatory, while newly empty WAL creation
on read-only reopen is ignored. Cancellation before reopen handoff retains
the original directory owner for cleanup, never a successful partial transfer.

The actual original-control regression first failed its missing-API assertion,
then proved cancelled reopen/authorization/snapshot preservation, continued
original-store usability, real future-schema mutation and actual closed-store/
new-store handoff. A binding regression proves physical writes change the
fingerprint and rejected future-schema reopen does not. Bounded architecture
review found cancellation from `FileStream.ReadAsync` could emit a false
internal-failure diagnostic. A deterministic in-flight regression first failed
with `metadata.internal_failure`; translating only token-matched stream
cancellation into the worker's existing budget failure fixes it. That
regression waits for actual settlement and rejects any diagnostic emission.
Direct comparison with predecessor wrapper bodies preserves every inherited
schema assertion, including exact encoded entry preservation and physical
database/WAL byte checks; complete frozen runtime parity is a separate gate.

All 89 current predecessor tests pass without skips on each provider, and
183 selected SDK/binding tests pass locally. Fresh independent locked replay
reproduces eight archives, seven wrapper DLLs and the separate Application
DLL. All seven actual binding output DLLs match archives; SDK bytes agree
across feed families. Only the SDK hash changes in the tracked predecessor
lock, preserving other/historical pins. The expanded native request is 50
scopes/258 observations (88 SQLite identities), subsequently verified below.
Exact frozen/runtime/controller-origin integration, actual inherited recovery
and complete category/profile acceptance remain unfinished. No additional task
or reviewer-owned checklist is marked complete by this checkpoint.

Native run [40100325269](https://github.com/Stonefly-Labs/Hoard/actions/runs/40100325269)
at `82a9b0912a21e5e3986271287d0a8be71c5cd9ee` passed all three jobs:
136 foundation checks without failures/errors/skips, exactly 50 scopes/258
discoveries/executions with expected diagnostics, all 88 SQLite identities,
actual native containment and eighteen-package/thirteen-lock replay. Free
scratch: 91,724,460,032 bytes. Input:
`b14dbdf8efb765d9982c64ec3dbda2defe41ca3a40797b337a5c899072825812`;
preparation:
`b5ab83472771b403020cded50b3ee7af3a078bf29b2fac55b7188c7aa4e8448b`;
producer:
`7a0b2e1acd86a77e1aef266d1b52d5542b2b7b56674358127881e9625c8eda29`;
controller:
`a79ae525c7509b80f9d0ff8bb689ed6d2af2e3e952b8b9b36226271dcbb8eba0`;
child start:
`56343d36650030db00b5194c19f427f7d7de135580d4466f2b0be6af8b7d1753`.
Baseline seal and actual SQLite/native/PRAGMA pins remain unchanged. This gate
does not execute original wrappers.

### Frozen original-wrapper diagnostic transport

The native diagnostic now compiles the actual original metadata test assembly
against its existing seven-package graph, then independently selects all 63
frozen runtime identities for Memory and SQLite. Expectations come from the
immutable F-06 catalog, not provider declarations, discovery totals or method
prefix counting. Shortened, renamed or foreign scopes reject before launch.
Exact safe discovery must match before executing the same selected parameters.
Both phases receive closed provider selection in actual test-host settings,
with the default console logger disabled.

The original graph is privately rebound through the existing preparation helper
and reverified before/after execution; tracked and historical locks remain
unchanged. Core/Hosting/HostAdapters are independently packed for this diagnostic,
extending its feed from seven to ten archives without changing SDK dependency
edges. All seven wrapper dependency DLLs must match archive members. The safe
logger is installed as a byte-verified adapter, not a new predecessor NuGet
dependency. Original runtime, dependency and native images enter immutable input
capture, whose recomputation rejects a changed wrapper SDK image. The separate
eighteen-package/thirteen-lock preparation job remains unchanged.

Two missing-dispatch assertions failed by name before implementation. Five new
focused regressions now cover every frozen parameter and actual original
assembly selection, shortened/renamed-scope rejection, replaced SDK/logger
images, closed provider settings and unchanged original package graph. All 248
tooling tests pass locally (237 passes, eleven native macOS skips); frozen
inventory/catalog and patch integrity checks pass. The expanded native request
is 52 scopes/384 observations: the prior 50/258 vector plus 63 original wrappers
per provider. This is diagnostic execution evidence,
not completed extraction parity or binding/session-origin/controller import.
Legacy `metadata_evidence.py` runtime import, actual recovery and full category/
profile acceptance remain unfinished. No task/checklist marker is completed.

Native run [40101331484](https://github.com/Stonefly-Labs/Hoard/actions/runs/40101331484)
at `8065dfcea7e180d10b097899117d8d25eed17aa0` verified all three jobs:
141 foundation checks without failures/errors/skips, all 52 scopes/384 exact
discoveries/executions with the expected diagnostic vector, all 63 original
identities independently on Memory and SQLite, actual native containment and
identical eighteen-package/thirteen-lock replay. Six-baseline seal:
`41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`;
input: `f3104f9ad2ae1fc5ac8311e06fbb87458ae1c79d3a59ba7a9aaf4118766f53f5`;
preparation: `b14732b6f47bc0b0305832362f3baedf6ae46e7107be165aeb1feb2b92c43084`;
producer: `810a2f8b1f6f723e067e03934a55c12fb88d4add56f356787aae93125f685925`;
controller: `aa4c67d3e787292f365049d3700c8b1c4f3590df00f1e7ef18139b573040a849`;
child start: `56ee92225e02d89f457c7c4233021c17562e8c6c6fd71d0af0d306d401bb334d`.
Free scratch was 91,724,349,440 bytes. SQLite/native/PRAGMA pins are unchanged.
This verifies original-wrapper execution transport, not complete session origins,
extraction parity or category/profile acceptance.

### Initial original artifact publication extraction

Five original two-provider wrappers delegate to provider-free
`ArtifactPublicationAssertions` over `IArtifactStore`: absence/empty content,
unknown length/positive short reads/true EOF, every declared expectation,
unsupported checksum/range and fully verified duplicate incarnation. Assertion
bodies and frozen wrapper names/parameters are preserved. The staging-prefix
boundary wrapper stays original-owned. Existing shared publish/read signatures
forward to the same SDK helpers; the original nested `ShortSource` remains as
a sealed derived compatibility surface over the shared implementation.
No full-category session, provider-selected expectation or no-op hook is added.

Both named missing-consumer assertions first failed `Assert.NotNull`, not a
compiler/setup error. After extraction, a bounded mutation consumes the first
source, then stages the recorded bytes instead of reading the duplicate caller's
source. Each actual Local/ObjectSemantics store completes two real stages and
commits; the common consumer rejects the unread duplicate at `Assert.True` on
EOF. Its undecorated store passes the unchanged consumer. All fourteen selected
publication/mutation tests pass without skips.

The first unrestricted artifact attempt observed 250 passes and seventeen
setup failures: actual transfer proof files, crash/noncooperative runner and
cross-process admission prerequisites were absent. These are not behavioral
negatives or accepted exclusions. The explicit non-external-proof selection
then passes all 250 tests without skips. Private non-qualifying preparation and
independent empty-cache default locked replay reproduce all eleven archives,
verify ten actual wrapper dependency DLLs and the separate Application DLL.
The artifact package-only manifest/lock add only the SDK; all prior entries and
vendor pins remain unchanged. The metadata predecessor lock refreshes only its
SDK hash; historical sources/graphs/binaries remain unchanged.

The standalone legacy artifact preparer remains unconverted: its unchanged-F-06
metadata comparison cannot accept intentional F-07 fixture changes, and its call
to the current metadata recipe on a historical SDK-free source tree cannot
build. This increment uses separate current-candidate preparation, not weakened
historical comparisons. A deliberate pinned historical/current-candidate split,
safe witness import, full artifact adapters, actual crash/transfer proofs and
all category/profile gates remain unfinished. T027/T030/T031 and reviewer-owned
checklist markers remain unchecked.

### Safe original artifact publication transport

The owned Linux diagnostic now builds the actual original artifact assembly
against its existing ten-package graph. One source-owned scope selects all
twelve frozen publication parameters, including the original staging-boundary
pair, plus the two actual-store duplicate-source mutation pairs. Both providers
remain in that one exact scope: method-based test filters cannot distinguish
their parameters, and a falsely reduced expectation must not pass. Shortened,
renamed and foreign scopes reject before launch; exact safe discovery precedes
execution through the existing bounded projection/ingestion.

Local/ObjectSemantics/artifact HostAdapters are independently packed after the
original metadata dependencies. This extends the diagnostic feed to thirteen
archives without changing the separate eighteen-package/thirteen-lock job.
The safe logger is byte-verified and installed only as an adapter. All ten
actual wrapper dependency DLLs must match their archives; original artifact
runtime/dependency/native files join immutable pre/post capture. Both source
locks and historical recipes remain unchanged by this transport increment.

Two named missing-dispatch assertions failed before wiring. All 250 tooling
tests pass locally (239 passes, eleven native macOS skips). The existing
runtime-image regression now rejects replacement of every dependency for both
original assemblies; graph-preserving lock tests cover both wrappers and input
recapture rejects a changed artifact-wrapper SDK image. Frozen inventory/catalog
and patch-integrity checks pass. Native selection expands to 53 scopes/398
observations, pending Linux execution. This is not completed artifact binding,
session-origin attribution, safe legacy import or recovery/transfer acceptance.
No task/checklist marker or driver stage is advanced.

### Shared protected reads and exact deletion semantics

Three more original two-provider wrappers delegate to provider-free
`ArtifactReadAssertions`/`ArtifactDeletionAssertions`: destination failure and
second-copy rejection without disposing borrowed streams, exact delete receipts
with recreation/stale-incarnation fencing, and held-reader exclusion. All
inherited assertions remain, including AlreadyAbsent behavior and stale cleanup
preserving the recreated bytes. Actual reference-authority setup remains
fixture-owned. The reader uses one lexical asynchronous disposal scope before
awaiting deletion, preserving the same successful ordering while also releasing
the guard on failed assertions; no double-disposal is introduced.

All 37 affected class tests pass. Independent empty-cache default locked replay
reproduces eleven archives and every actual dependency image. Its explicit
non-external-proof artifact selection passes 250 tests, and both original
metadata suites pass 89 each, without skips. Both predecessor locks refresh
only the common SDK hash; old graph entries and vendor pins remain unchanged.
No durable/external-proof obligation is waived by those focused results.

An independent native scope selects the six exact frozen read/deletion
parameters. Its named missing-dispatch assertion failed before wiring, then
correct routing/complete selection and shortened/renamed-scope rejection pass.
All 251 tooling tests pass locally (240 passes, eleven native macOS skips);
formatting, frozen inventory/catalog and patch-integrity checks pass.
The expanded native request is 54 scopes/404 observations, pending Linux
execution. Complete artifact adapters/origins, safe legacy preparation/import,
actual recovery/transfers and all category/profile gates remain unfinished.
No task, reviewer checklist or driver stage is advanced.

Native [40103235096](https://github.com/Stonefly-Labs/Hoard/actions/runs/40103235096)
at `665b537e9b6e5377b90cd39f579a82c687e46255` verified all three jobs,
141 foundation checks without failures/errors/skips, 52 scopes/384 exact
discoveries/executions, native containment and identical eighteen-package/
thirteen-lock replay. Input:
`2fb427ab4d5c59c2835adc7e3c11070dbc76b7841b82d8d237e34ec04c67b3f8`;
preparation: `2e2db7eff237f93969b31a62ad51bb659d494e8a557771c58c020377b9ce5c25`;
producer: `9ac918d304b9354c9be4956b2d27a5ed7ba5b336559bab6c10102c813bbd4564`;
controller: `d113eff6e93385331e6965e652f673edd025fcf326f1db309eedc86f98ae6605`;
child start: `a3b9418cf9646b9537bd70b668c7517d864393d490274e4de4af0420107a4da0`.
Free scratch: 91,724,251,136 bytes; six-baseline and SQLite/native/PRAGMA pins
are unchanged. This verifies the first artifact SDK archive with existing
metadata/SDK scopes, not original artifact execution or this read/deletion
increment.

### Shared exact evidence and permanent quarantine

The ninth original artifact wrapper delegates exact receipt/protection
validation to `ArtifactEvidenceAssertions`; the reused quarantine helper now
shares its logical assertions too. Both inherited bodies mechanically match
after only store/validator/authority/identity/helper/cancellation substitutions.
The common checks retain wrong receipt rejection, opaque same-operation guard
identity, copied/disposed guard denial, foreign epochs, permanent corruption
after restored bytes, duplicate-publication rejection, abandonment and original
receipt reconciliation. The existing Local durable reopen remains outside the
SDK and is never borrowed by ObjectSemantics.

The missing shared consumer first failed by name. A narrowly scoped validator
decorator forwards the first valid request to the actual provider and accepts
the second wrong receipt. The unchanged common `Assert.IsType` rejects this
mutation after two calls on both providers; fresh actual validators pass the
same assertion bytes. This is a behavioral negative, unlike the initial
missing-consumer setup failure, and is not a completed category mutation binding.
Fresh preparation and independent empty-cache default locked replay reproduce
eleven archives and every actual dependency image. Twenty-eight affected tests
pass, followed by all 252 non-external-proof artifact tests and 89 original
metadata tests per provider, without skips. Both predecessor locks refresh only
the SDK pin; historical graphs/vendor entries remain unchanged.

The new exact native scope selects 21 frozen evidence/quarantine parameters and
two actual-validator mutation parameters. Its named missing-dispatch assertion
failed first; complete routing and shortened/renamed-scope rejection now pass.
All 252 tooling tests pass locally (241 passes, eleven native macOS skips),
with formatting, catalog/inventory and patch-integrity checks. The expanded
native request is 55 scopes/427 observations, pending. Seventeen external-proof
prerequisites, full category bindings/session origins, safe legacy imports and
all profile/evaluator acceptance remain unfinished; no task/checklist or driver
stage advances.

### Verified original artifact publication transport

Native [40103524667](https://github.com/Stonefly-Labs/Hoard/actions/runs/40103524667)
at `dcb777e5a24665e569f029c1d359060319bfefcf` passed all three jobs:
143 foundation checks without failures/errors/skips, 53 scopes/398 exact
discoveries/executions including all twelve original publication parameters
and the two actual-store source-substitution mutations, real native containment,
and identical eighteen-package/thirteen-lock replay. Six-baseline seal and
SQLite/native/PRAGMA pins remain unchanged.

Input: `0309c9865b7319d393b0c2006ef0f2d159f36e8c9b0f43f7b50f896e02c1fca9`;
preparation: `8e1ab1e63d37a2e3bc201b700d0b1bc7bc4898243e4d388d70e470d6a39c4539`;
producer: `7cf8c51cd88be2b59bd5a10792efd9110904be800c1bac47b6de0d5b24b34121`;
controller: `be1ed47d468062e026dd55dd418df81be45b4958a2b528c1b03e5e9472db117e`;
child start: `8ca395b6e6656e825bb79bad8c807523e83efba3e2cb96ad0763fecc18478b57`.
Free scratch: 92,108,894,208 bytes. This verifies publication transport, not the
subsequent protected-read/deletion/evidence increments or category qualification.

### Observed-barrier owning-controller primitive

`OwnedRun.command(stop_at_barrier=...)` now restricts requested targets to bounded
integers, recovery/event scope and a fifteen-second ceiling. Safe projection
observes the matching barrier before checking the exact live child/start identity
and requesting pidfd group termination. The termination primitive reports
whether the owned signal was actually accepted. Successful barrier receipts
require that signal, actual SIGKILL exit and complete group exit; normal exit,
timeout, wrong/repeated barriers and failure events reject. Parent-recorded
barrier value/monotonic observation/signal-request times augment the existing
PID/start/interval/exit evidence only for this opt-in path. Existing command
behavior and receipt shape are unchanged otherwise.

The missing API was observed failing the new admission test before
implementation. All 256 tooling tests pass locally (242 passes, fourteen native
macOS skips), with frozen inventory/catalog and patch-integrity checks passing.
Three new Linux regressions cover owned tree termination after observation,
ordinary exit without proof, wrong/repeated/failed/unobserved barriers and
rejected signal delivery. Their native execution is pending. This is a
controller prerequisite, not actual SQLite/Local crash-matrix execution or
T026/T032 completion; runner integration/readback and complete witness
attribution remain unfinished.

### Safe SQLite recovery runner and controller integration

The prior controller checkpoint's native foundation job at
[40105833001](https://github.com/Stonefly-Labs/Hoard/actions/runs/40105833001)
observed 149 tests with two assertions failing in the wrong/repeated-barrier
regression. Its fixture emitted literal backslash-n bytes, not event-delimiting
newlines; the controller therefore timed out instead of reaching the intended
rejection. The test now constructs canonical events with actual newline
framing. Positive owned-tree exit and normal-exit rejection cases did not fail.
The corrected full native gate remains pending; no failed run is accepted.

The actual SQLite CrashRunner now accepts only unset legacy mode or explicit
`HOARD_CONFORMANCE_SAFE_EVENTS=1`; invalid values fail before store opening.
Legacy output remains byte-for-byte unchanged. In safe mode existing successful
assertion paths emit a closed completion event, and actual hold boundaries emit
closed numeric events after the control write and flush before awaiting
termination. Raw runtime/OS strings and inherited pass labels are not persisted
as diagnostics.

The SDK diagnostic now builds that runner against its unchanged six-package
local graph through a privately derived locked restore, byte-verifies every
actual local dependency image and input-captures the entire runner/native tree
before/after execution. It requests separate actual seed, observed-barrier kill
and readback scopes for M0..M2, U0..U4 and R0/R1, plus the original real
backup/restore walkthrough. Each barrier requires a complete parent receipt
with exact schema/sequence/target, nonzero PID/start identity, SIGKILL/group exit,
finite bounded monotonic observation/signal ordering and no failure code.
Only complete event/receipt chains produce the input-bound hash-only diagnostic;
arbitrary timeout, normal exit and missing/wrong proof cannot pass.

The missing safe event was observed after a successful actual walkthrough;
the missing parent-chain admission assertion also failed by name before wiring.
Fresh independent locked preparation reproduces eleven archives. A separate
fresh-cache runner build verifies six actual local DLLs. Its first restore
correctly failed when the private copy omitted the existing fixture-scoped
central version file; copying that unchanged file fixed the private recipe
without repository manifest/lock edits. Actual backup/restore walkthroughs now
pass in both unchanged legacy and safe mode, and invalid mode rejects before
store creation. Formatting and all 258 tooling tests pass locally (244 passes,
fourteen native macOS skips). Controller unit doubles verify all 31 requested
scopes and rejection paths; they are not crash evidence.

Linux execution of the ten actual barrier/termination/readback rows is pending.
Live-held independent schema/owner probes, exact wrapper/session attribution,
safe legacy imports and complete T026/category acceptance remain unfinished.
No memory durability or Local crash proof is inferred, and no task/checklist
or driver stage advances.

### Verified protected-read/deletion transport

Native [40104718986](https://github.com/Stonefly-Labs/Hoard/actions/runs/40104718986)
at `c979b6d0be855b9da9addc3513009edd704d6e73` passed all three jobs,
144 foundation checks without failures/errors/skips, 54 scopes/404 exact
discoveries/executions including all six original read/deletion parameters,
actual native containment and eighteen-package/thirteen-lock replay.
Input: `e4a639d998ad4315b01b32b48559cf5d8c06b29dc4b4a0c22663afa9ea02aed9`;
preparation: `ad430a4561164b0705d3d8943bf31191fc2a2c0dd8558f76dc2896da49221803`;
producer: `74147986bef844694caeffc3a0f50de0a6780d267545f4e6a5cb1cdce26ba820`;
controller: `d0509971f2671113f38351ae64696be8c8a2c3c753c429d8be12e8a85d118470`;
child start: `a1abb762b5faf9d1f2227dbac4109726c88d139eba1f373a4cbd56e5078d88cd`.
Free scratch: 92,108,972,032 bytes; six-baseline and SQLite/native/PRAGMA pins
remain unchanged. This verifies read/deletion transport, not later evidence/
controller increments or full category acceptance.

### Verified exact evidence/quarantine transport

Native [40105402168](https://github.com/Stonefly-Labs/Hoard/actions/runs/40105402168)
at `d7ef7cc3cdc20822c79b340a42e12eef0cbbe383` passed all three jobs:
145 foundation checks without failures/errors/skips, 55 scopes/427 exact
discoveries/executions including 21 frozen evidence/quarantine parameters and
both wrong-receipt mutation parameters, native containment and eighteen-package/
thirteen-lock replay. Six-baseline and SQLite/native/PRAGMA pins are unchanged.
Input: `715fbfaeb8861b2e327a7e29cbbbe3ff80a79ba3c56b8fafb3d0d908a9b15592`;
preparation: `69e35939c5061ff02d773464d80165dddff8f0b38e03595055b9332f6888998f`;
producer: `9ed624fd2d24d8b229b642f1bba488b700d864bf4209b0c4f014e40f2b83cee0`;
controller: `f8db39c7d6c640dd3f97e8a0778655d51b43ebf0ccc8653ccf1373022cf77c76`;
child start: `c9386051ef170a11d8bdfc2933e01dad51cda9f7a23063a4324bef46010bb4a9`.
Free scratch: 91,724,279,808 bytes. It does not verify the subsequent owning
controller/recovery changes or advance any category/task/stage.

### Safe Local crash runner integration

The corrected native owning-process gate at
[40107305423](https://github.com/Stonefly-Labs/Hoard/actions/runs/40107305423),
head `62c149c51b039724938e6547806626bdee8630f4`, passed 151 foundation tests
without failures/errors/skips, including every corrected rejection variant,
actual owned tree exit, rejected signal delivery and normal-exit denial.
Its complete SQLite diagnostic is still running. The superseded failed
`0af7c98` run was canceled after recording its closed failure projection;
no failed/canceled checkpoint is accepted as passing.

Local's actual CrashRunner now accepts explicit safe-event mode, preserves
legacy output when unset and rejects invalid values before store creation.
The diagnostic builds it against its unchanged nine-package local graph,
verifies every actual local image and input-captures its entire runtime tree.
It drives B0..B3/D0..D1 with fresh run IDs and separate crash/readback scopes.
Only parent command/event/receipt admission is shared with SQLite; provider
publication/recovery implementations remain independent, and ObjectSemantics
borrows no durable proof. Original control/content readback, exact receipts,
generation fencing, reconstruction, pending/reclaimed deletion, ABA safety and
no duplicate effect assertions remain intact.

The missing Local controller assertion failed by name first. Its unit double
now verifies all twelve scopes, matching run arguments/targets and changed
runner-byte rejection. Two independent fresh-cache locked builds reproduce
identical actual runner bytes and verify all nine local dependency images.
A bounded macOS functional exercise observes actual barrier events, kills
only its own child and passes all six safe-mode readbacks, an unchanged legacy
B0 pair and invalid-mode rejection. This is not a Linux pidfd/group ownership
receipt or category acceptance. All 259 tooling tests pass locally (245 passes,
fourteen native macOS skips), with format/catalog/inventory checks passing.

Actual Linux Local crash execution, full legacy/session attribution and
T032/category completion remain pending. Small recovery payloads do not
substitute for actual paced 256 MiB/4 GiB transfers or incremental OS peak RSS.
No task/checklist/stage advances.

### Native SQLite recovery verified; owned transfer integration

Native
[40107305423](https://github.com/Stonefly-Labs/Hoard/actions/runs/40107305423)
at `62c149c51b039724938e6547806626bdee8630f4` subsequently passed all three
jobs, including 151 foundation checks without failures/errors/skips,
55 scopes/427 exact discoveries/executions, genuine native containment, all
ten actual SQLite seed/barrier/kill/readback rows and the actual backup/restore
walkthrough. Separate preparation replays the unchanged eighteen-package/
thirteen-lock graph. Closed receipts:

- Baseline seal: `41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`.
- Input: `d25705becfb777ccaffb80e3679b0361d29dd4bc3c5c22878f57c937d932607e`.
- Walkthrough: `74780450ba91bb05571def5745b138cbab41d02e62da0eda42527b33df22803a`.
- Preparation: `2ebbd2f2232a44e0e64ca773e8721f7c58db1b5c5bfd9dc3cb49b07d33520b2c`.
- Free scratch: 91,724,234,752 bytes.

All ten closed parent controller/readback records have distinct child-start
and controller hashes and bind this exact input; no raw legacy log is imported.
This does not complete live-held independent probes, legacy/session/category
attribution or T026. Local integration is published at `e6d79f4`; exact native
run `40107826472` remains running, never inferred from SQLite or simulation.

The actual TransferRunner now supports the same opt-in safe-event mode,
preserving legacy output when absent and rejecting invalid mode before store
creation. Safe mode emits idle after original warmup/GC, waits for the parent's
literal transfer handshake, performs the original actual stage/commit/full read
and verifies generated non-seekable bytes, both paced directions, exact counts,
independent hashes and lengths. It writes only a bounded closed producer proof,
then holds for final parent observation. The final settlement acknowledgement
follows the literal parent handshake; normal process/group exit remains required.

The owning command admits this mode only for exact qualified sizes in transfer/
event scope. Bounded kernel `/proc/PID/status` reads require stable live owned
PID/start identity and exact positive RSS/high-water fields. The parent observes
idle `VmRSS`, samples actual kernel `VmHWM` throughout/before settlement and
enforces the inclusive 64 MiB incremental peak. This is not a sampled-RSS or GC
counter substitute. Startup is bounded to fifteen seconds, settlement to thirty
and the entire transfer to forty minutes under the unchanged profile deadline.
Ordinary exit, missing/repeated/reordered events, wrong sizes, excessive RSS,
failed diagnostics and missing settlement acknowledgement cannot pass.
Non-opted-in commands and receipts preserve their existing behavior.

The common parent receipt admission is reused by recovery and transfer paths.
Transfer admission additionally requires exact metric/time shape, bounded
monotonic observation and completed protocol. Producer PID/run/runtime, exact
independent hashes/bytes, pacing and original buffer/slot limits must match.
Only parent observations supply memory. The existing transfer predicate is
reused with an explicit `proc-status` method; default legacy methods and
historical measurement capture rules remain unchanged. The actual nine-package
runner graph and full runtime bytes enter locked build, image verification and
pre/post immutable capture. Four real Local/ObjectSemantics rows are requested
serially; final summaries contain only closed IDs and bound proof hashes.

Missing measurement/admission/controller assertions failed by name before
implementation. Focused mutation tests reject changed PID/hash/runtime/pacing,
extra fields, missing completion, invalid ordering and unbounded memory. Native
primitive tests use labeled controller doubles, never claimed real transfer
proof. Two actual independent fresh-cache locked builds reproduce identical
runner bytes and verify nine dependency images. Actual macOS safe-mode
execution passes both sizes for both providers, plus an unchanged legacy
256 MiB row and invalid-mode rejection. All real rows verify both actual
read/write hashes/pacing and independent `getrusage` peak within 64 MiB of
observed idle RSS. These are not Linux pidfd/status or category receipts.

Actual Linux owned transfer measurement, original wrapper/session imports,
noncooperative artifact children, four actual authority combinations and full
T032/category/profile completion remain pending. No task/checklist/stage
advances. Product architecture/ADRs/diagrams and deployment examples are
unaffected: only test-runner transport and parent evidence change.
Final `python3 -m unittest discover -s tests/tooling -q` passes 266 tests
(250 passes, sixteen native macOS skips). The compiled SDK catalog, unchanged
frozen inventory, runner whitespace verification and patch integrity pass.
The final acknowledged protocol was recompiled in two fresh caches and all
five actual macOS transfer rows rerun successfully after adding the explicit
settlement acknowledgement.

### Native Local recovery verified; live artifact worker inspection

Native
[40107826472](https://github.com/Stonefly-Labs/Hoard/actions/runs/40107826472)
at `e6d79f4ad5da3496f4c29038e55e16f64b8e7688` passed all three jobs:
152 foundation checks without failures/errors/skips, 55 scopes/427 exact
discoveries/executions, ten SQLite and six actual Local observed-barrier kill/
readback rows plus the actual backup/restore walkthrough, genuine native
containment and identical eighteen-package/thirteen-lock replay.
Input: `167511b7f2a68798a14d65b42a3332a3045a673013c9948b933ddd30deb8833b`.
Preparation: `baf0643822c7cbdb6e08a6c991ecb0374256b274013ac96bc43dded08316939e`.
Baseline seal remains `41b210b8650f0c6070215818fd1699beffe28cb047b68ae37a45d4a997fa9081`;
free scratch is 91,724,165,120 bytes. Each Local row has distinct controller and
child-start hashes and the exact successful original readback. This is not
ObjectSemantics durability or complete legacy/session/category attribution.

Native process/memory/settlement regressions at
`d429dd24fb18efda382502ff0a3461ab9ffc6b4f`, run `40109299238`,
job `120917473901`, passed all 159 foundation tests without failures/errors/
skips. This includes the real owned-controller memory and acknowledgement
regressions, not actual large-transfer proof; the complete run remains running.

The actual noncooperative artifact runner now supports opt-in safe events,
preserving legacy output and rejecting invalid mode before store creation.
Original code still stalls actual source/destination/native work, checks
pending worker, untouched borrowed streams, retained root/cleanup, blocked
readiness/admission/shutdown and appropriate read/delete protection, then repeats
those original inspections after the literal parent request while work remains
live. Bounded closed observation files are flushed before numeric barriers.
No provider pass label replaces these actual assertions.

The owning command adds an opt-in contained-barrier inspection request before
its existing observed-stop target. Both targets must be distinct bounded
integers in recovery/event scope; the same fifteen-second bound remains.
Live exact PID/start is required before the request, then observed target,
accepted owned SIGKILL and confirmed group exit. Parent receipt admission
checks exact ordered observation/request/observation/signal/exit times and both
matching phase/run/PID/provider/scenario producer records, with unchanged
retention/failure predicates. Old barriers/receipts are unchanged without opt-in.
Six actual Local/ObjectSemantics source/destination/native rows are requested;
their final record explicitly has `durableCrashProof: false`.

Named missing dispatch, producer admission and parent handshake assertions
failed first. Focused negatives reject foreign/mismatched second observations,
changed retention/protection, absent request and reversed/repeated barriers.
Numeric timestamp validation now checks bounds before floating finiteness:
the regression observed an escaping overflow on huge integers first, and those
values now fail closed as `ProofMismatch`. No receipt or diagnostic fallback
was added. Two independent fresh-cache locked builds reproduce actual runner
bytes and all nine local dependency images. Actual macOS execution passes both
original inspections and parent termination for all six safe rows, an unchanged
legacy source row and invalid-mode rejection. These are not Linux pidfd/group
or durable crash receipts.

All 272 tooling tests pass locally (255 passes, seventeen native macOS skips),
with SDK catalog, runner whitespace and patch integrity passing. Actual Linux
retained-worker inspection, original wrapper/session/legacy imports, all four
authority combinations and complete category/profile acceptance remain pending.
Production architecture/ADRs/diagrams and deployment examples remain unaffected
by test transport and parent evidence changes. No task/checklist/stage advances.

### Native transfer/retention verification and original external wrapper transport

Complete native
[40109299238](https://github.com/Stonefly-Labs/Hoard/actions/runs/40109299238)
at `d429dd24fb18efda382502ff0a3461ab9ffc6b4f` passed all three jobs:
159 foundation checks without failures/errors/skips, 55 scopes/427 exact
observations, ten SQLite and six Local recovery rows, all four actual paced
256 MiB/4 GiB Local/ObjectSemantics write/read rows, native containment and
eighteen-package/thirteen-lock replay. Parent kernel RSS/high-water observations
and acknowledged settlement were admitted for each actual transfer.
Input: `f36b1b808151c587387efae9f67ba60b726e6e5375fdaa23ac3244450b19f13e`.
Preparation: `a81a10ab8b8589894c52411cd29c8bea28facf28c0f62ce491b6ee5bf0dbe1d5`.
Free scratch: 92,108,427,264 bytes.

Native
[40110165383](https://github.com/Stonefly-Labs/Hoard/actions/runs/40110165383)
at `c7eb90cb44bdddc9f63d570ccc96ccba821a6b01` then passed all three jobs:
165 foundation checks without failures/errors/skips, the same 55/427 vector,
all recovery/transfer rows and six actual retained-worker two-phase
inspection/termination chains. Exact producer phase/run/PID/retention records,
parent observation/request/signal/exit ordering and distinct controller/child-start
hashes were safely verified. These rows explicitly have `durableCrashProof: false`.
Input: `5cf3e4daba4401d70831f94cc4d44079f889ff46def27b92f36c68a3947da4ef`.
Preparation: `02de92c9d78b68ab324e3243e9caca9ff85da094f431d79e0d773e792c3bf8a3`.
Free scratch: 91,723,952,128 bytes. Six historical baseline seals, SQLite/native
pins and eighteen-package/thirteen-lock replay remain unchanged.

The next diagnostic adds all seventeen existing external-proof artifact
wrappers: sixteen frozen crash/noncooperation/transfer identities plus the
independent existing cross-process root-owner fact. Four new bounded child-output
cases make one exact 21-identity scope. A named failing scope test caught the
distinction between the sixteen frozen witnesses and that additional original
fact; both are now preserved without modifying the frozen inventory.
The actual test host receives only closed settings for the input-captured
runner, current run ID, parent-admitted transfer proofs and fresh private
per-attempt crash captures. No safe-event flag is inherited into original
legacy child wrappers. This scope runs after real diagnostic prerequisites.

The original wrappers now share an internal bounded text reader, with a finite
deadline, exact 16,384-character limit and CRLF allowance that never consumes
the next packet. Crash-state length is checked before allocation/copy; recovery
stderr is asserted empty before creating the healthy empty legacy error file,
never copied on failure. The original transfer predicate adds actual kernel
`getrusage`/`proc-status` methods while preserving all byte/hash/pacing/RSS/buffer
assertions; an unmeasured `declared` method remains rejected.
Actual compiler CS0103 exposed the missing reader before implementation.

Two actual fresh-cache locked builds pass all 21 cases without skips and verify
ten dependency images. Initial assembly byte replay exposed the test SDK's
generated source path outside the source-only debug map; mapping both private
source/cache roots reproduces assembly SHA-256
`1d980fc8946c268247f802cf674bdb9155caba5eed8119f5647a8b4670f890ec`.
The copied actual transfer packets are unchanged, with real `getrusage` peaks,
not fabricated method substitutions. All 274 tooling tests pass locally
(257 passes/seventeen native macOS skips); compiled SDK/frozen catalog,
accepted package-mode whitespace and patch integrity checks pass.
The expanded native request is 56 scopes/448 observations, pending.
These remain diagnostics, not the catalog's 179 applicable category passes,
complete legacy/session origins, all authority combinations or full profiles.
No task/checklist/stage advances; production APIs/edges/ADRs/diagrams and
deployment examples remain unaffected by this test-transport increment.

### Current package preparation separated from historical recipes

Current artifact preparation no longer archives pre-F-06 metadata source and
then passes it to today's SDK-dependent metadata build recipe. It builds the
current metadata fixtures and SDK explicitly, copies those actual archives to
the current artifact feed and includes the SDK in its exact eleven-package
inventory. This intentionally supports F-07's authorized current wrapper
extraction; it does not claim current wrappers equal historical F-06 source.
Historical source/binary preparation and seals remain separate and unchanged;
the strict legacy source/lock comparison helper is not weakened.

A named current-source regression first rejected the historical archive command.
The first actual build then failed NU1403 on stale local fixture hashes, while
independent comparison confirmed produced archives matched the existing current
feed. Both current preparers now reuse the existing strict local-archive
derivation helper instead of force-resolving a new graph or changing tracked
predecessor locks. Default restore/build stays locked against a private alternate,
recording/verifying original/prepared hashes and exact local archive bytes.
External package hashes/versions/edges and every original source lock remain
unchanged. Explicit update-lock behavior remains separate.

The shared helper adds only an explicit package-acceptance option. Its exact
`PackageAcceptance/packages.lock.json` input and distinct
`obj/F07.preparation.acceptance.packages.lock.json` output cannot be relabeled
as ordinary lock paths or substituted. The named missing-option regression
failed first; closed-path and original-lock preservation cases pass. Ordinary
historical derivation records retain their unchanged shape and behavior.

Two actual independent fresh-cache locked current preparations reproduce all
eleven archives with combined archive-map SHA-256
`5d98baea004102cdb99dd29b6f1566e0acf1720ed2e3d9b920ba0b817b44933c`.
All ten loaded artifact dependency images match their archives. Both complete
runs pass all 273 artifact cases, plus 89 metadata cases on memory and 89 on
SQLite, without skips. Metadata/artifact preparation retains four/five verified
lock derivations, with one acceptance lock each. Previously measured actual
macOS transfer packets are unchanged when consumed by their original assertions;
they are not new current-run transfer/session-origin/category proof.
All 276 tooling tests pass (259 passes/seventeen native macOS skips), with
compiled/frozen catalogs and patch integrity passing. Source and tracked locks
are not rewritten by these default locked preparations.

This is non-qualifying preparation/functional evidence, not complete safe
legacy runtime import, profile/controller integration or the catalog's 179
applicable category passes. No task/checklist/stage advances. Product APIs,
dependency edges, architecture/ADRs/diagrams and deployment examples are
unaffected by this current tooling/preparation correction.

The preceding original-wrapper native diagnostic subsequently passed at
[40111391053](https://github.com/Stonefly-Labs/Hoard/actions/runs/40111391053),
head `4e3ef47c1b200251c0e12c258317e5a43d2d0957`. All three jobs passed:
167 foundation checks without failures/errors/skips, 56 scopes/448 exact
discoveries/executions, including all 21 original external/capture identities,
all ten SQLite/six Local recovery rows, actual paced transfer/RSS/settlement
rows and retained-worker inspection/termination chains, native containment and
unchanged eighteen-package/thirteen-lock replay.
Input: `92aadefd023ac0519274d5f097fb813c43c508c934e21a92a50bc7fe3cd2f64c`.
Preparation: `42e787cc053ea1e1465aadbed898362c59d1dd8d5b2ffa53ffd68d8d8e16b8a7`.
Free scratch: 91,723,743,232 bytes. These are actual owned diagnostics,
not complete category/session-origin imports.

### Shared publication race assertions and real-store negative control

The preceding preparation checkpoint passed native
[40112542005](https://github.com/Stonefly-Labs/Hoard/actions/runs/40112542005)
at `6de5933db158923413d084cf5673e561661f2e76`: all three jobs, 168 foundation
checks without failures/errors/skips, the unchanged 56-scope/448-observation
vector including all 21 external/capture rows, real recovery/transfer/retention
diagnostics, native containment and eighteen-package/thirteen-lock replay.
Input: `9dca6ddbdbcc8305dc9f2b46a5e8bb1907d41d8651fa9c95ad6473a2007d5504`.
Preparation: `7268c461265ec64f2491319d72c3cb1d72927e1f07016eb13eca07fb84571f1b`.
Free scratch: 91,723,599,872 bytes. The actual current-only package recipes
were separately exercised on macOS above; native diagnostics are not relabeled
as those recipe runs or full category/session evidence.

All three original publication race methods now forward to provider-free
publication consumers, retaining all six frozen parameter identities.
Equivalent concurrent writers still enter the actual provider publication
admission barrier together, stay pending until release, fully consume sources
and return one stamp, distinct receipts and exactly one published/one verified-
duplicate outcome. The forged staged-length case still rejects with InvalidInput
before accepting the original staged descriptor and preserving original bytes.
Corrupt content is still neither overwritten nor reused, and restored bytes
remain quarantined after exact staging abandonment.

Actual observer registration and payload damage/restore stay fixture-side;
common code receives only store/control callbacks and cancellation, never
provider IDs/types, filesystem paths or provider-selected expectations.
Mechanical body comparison of every original method passes after only explicit
store/helper/token/control forwarding; original checks and order are intact.
Actual package-mode compilation failed first with CS0117 for the missing shared
methods, then passed after extraction.

The focused negative uses the actual Local/ObjectSemantics stores. A forwarding
adapter repairs a forged length to the actually staged length, so the provider
commits it and the unchanged consumer's expected failure-type assertion fails.
Two commit calls and one repaired claim prove the intended mutation, not an
incidental setup/compilation failure. Fresh genuine providers pass that same
consumer unchanged. Existing duplicate-source negative controls retain their
behavior through a shared test-only forwarding base.

A named missing exact scope failed first. The requested new native scope has
the six frozen race witnesses and two named length-mutation parameters, appended
after original external wrappers. Expected vector: 57 scopes/456 observations,
pending Linux execution. Complete binding/session/category/profile evidence
remains separate; no task/checklist/stage advances.
Two actual independent fresh-cache locked preparations reproduce eleven
archives with combined archive-map SHA-256
`64ad96aa8bcd1a24cd971053260e3c6d7d3867739238196c61d593cfae65ec3f`.
Ten loaded artifact dependency images match their actual archives. Each run
passes all 275 artifact cases plus 89 metadata cases on each provider, without
skips. The new SDK is resolved through explicit private lock derivation; tracked
source locks stay unchanged. Accepted SDK/package-mode whitespace, compiled/
frozen catalogs, all 277 tooling tests (260 passes/seventeen native macOS skips)
and patch integrity pass. Product APIs/edges/ADRs/diagrams and deployment
examples remain unaffected by this test-only extraction.

Private staging and all four original reconciliation methods now forward to
provider-free shared consumers. All ten frozen parameters and original
assertion tokens/order match mechanically after explicit setup/seam/helper/
cancellation forwarding. Actual prefix barriers, clock advancement/rollback,
authority setup and post-stage lost-acknowledgment observer registration remain
fixture-side; provider IDs, concrete types and provider-chosen expectations do
not enter shared assertions.

A real-store negative first reconciles the original ticket and then publishes
different bytes through the actual provider. Substituting that genuine foreign
receipt fails the unchanged consumer's named receipt-equality assertion on both
providers. Exactly one reconciliation and one foreign publication prove the
intended mutation; fresh genuine stores pass unchanged. Missing shared
staging/reconciliation consumers first failed actual package-mode compilation
with CS0117/CS0103. An intermediate compiler failure exposed a test referencing
the SDK's internal success helper; using the existing fixture-side helper fixed
it without widening SDK visibility.

The named missing-scope regression failed before implementation. Its new exact
scope adds eight frozen reconciliation rows and two mutation parameters after
the existing race scope. Private staging's two existing identities remain in
the original publication scope, not duplicated. The requested native vector
is 58 scopes/466 observations, pending. No full task/checklist/stage advances.
Two actual independent fresh-cache locked preparations reproduce all eleven
archives with combined archive-map SHA-256
`1baf7e7a08abc7e3588c8ada5d2869074f49599c72c1ef43f15d242e44f6f13a`;
ten loaded artifact dependency images match their archives. Each run passes
277 artifact cases and 89 metadata cases per provider without skips. These
functional runs reuse unchanged actual earlier transfer packets, not fresh
current-run session/category origins. SDK and accepted package-source whitespace,
compiled/frozen catalogs, all 278 tooling tests (261 passes/seventeen native
macOS skips), mechanical five-body comparison and patch integrity pass.
Tracked locks, production contracts/edges/ADRs/diagrams and deployment examples
are unaffected by this test-only extraction.

All three original direct/listing visibility bodies now execute provider-free
shared checks. Exact assertion tokens/order match mechanically after explicit
setup/seam/helper/cancellation forwarding. Receipt/listing/direct-availability
observer registration, finite actual fixture entry waits and release controls
remain fixture-side, including direct-observer removal before release.

A real Local negative starts the actual held commit but immediately returns a
genuine earlier publication receipt. The unchanged shared pending-task
assertion fails. The test releases the actual hold, awaits actual commit
settlement, verifies one mutated commit call and a distinct Published stamp;
the fresh genuine store passes that same consumer unchanged. Actual missing
shared consumers first failed package-mode compilation with CS0103, and the
missing exact visibility scope failed its named tooling regression. The new
scope appends three frozen visibility identities and this mutation to request
59 scopes/470 observations, pending. No category/task/checklist/stage advance.

The preceding native race request passed
[40113497329](https://github.com/Stonefly-Labs/Hoard/actions/runs/40113497329)
at exact head `91da8f433af10b19924f45365b9eea6938101612`. All three jobs passed,
169 foundation checks had no failures/errors/skips, and strict admission verified
57 scopes/456 exact discoveries/executions, including all eight race rows.
Actual SQLite/Local recovery, all four paced transfer/RSS rows, all six
two-phase retained-worker chains, original external wrappers, native containment
and eighteen-package/thirteen-lock replay also passed. Retained-worker receipts
remain explicitly non-durable. Input:
`d76fa0b400774c50f771b733de73a71bc9b0c4c6622097c896b06fff5fc7f664`;
preparation:
`ab5517a180e177c516a886857cd9a79809af8c1757bd5b61d64dfe9e1555396b`.
The new reconciliation/visibility requests remain separate and pending.
Two actual independent fresh-cache locked preparations reproduce eleven archives
with combined archive-map SHA-256
`546ba43f818b769a3c6286e8efcae631087b31d8fdbb1acb43905af770c32e5b`;
ten loaded dependency images match their archives. Each run passes 278 artifact
cases and 89 metadata cases per provider without skips. Previously measured
actual transfer packets are unchanged, not fresh session/category origins.
All 279 tooling tests pass (262 passes/seventeen native macOS skips), alongside
SDK/accepted-source formatting, compiled/frozen catalogs, mechanical three-body
comparison and patch integrity. Product APIs/edges/ADRs/diagrams, deployment
examples and tracked locks remain unaffected.

Five original history/budget bodies now run provider-free shared consumers:
reclaimed-incarnation/history capacity, bounded candidate examination, faulted
candidate resumption and ticket-expiry capacity. Exact assertion tokens/order
match mechanically after explicit setup/seam/helper/cancellation forwarding.
Actual clock, limits/reference authority setup and candidate observer
registration remain fixture-side; no concrete providers or provider-selected
expected outcomes enter the SDK.

A real-store mutation hides the actual injected history-candidate failure
behind one actual retry. The unchanged consumer's expected failure-type
assertion fails on each provider, with actual candidate observation, exactly
106 reservations, one hidden failure and one retry proving the intended mutation.
Fresh genuine providers pass the unchanged consumer. Actual missing shared
consumers first failed package-mode compilation with CS0103. A missing exact
scope failed its named regression; its first count then revealed eight frozen
category identities, not sixteen. The other eight identities are additional
existing fixture cases and are requested explicitly without changing the frozen
inventory. The new eighteen-row scope contains all sixteen originals plus
two mutations, requesting 60 scopes/488 observations, pending. Remaining budget/
ownership cases and full binding/session/category/profile gates stay unfinished.

The preceding reconciliation run
[40114439905](https://github.com/Stonefly-Labs/Hoard/actions/runs/40114439905)
passed at exact head `517b91119d0f122837d1d0c32099761a46f03909`: all three jobs,
170 foundations without failures/errors/skips, 58 scopes/466 exact discoveries/
executions including all ten new reconciliation rows, actual SQLite/Local
recovery, four paced transfers, six retained-worker chains, original external
wrappers, native containment and eighteen-package/thirteen-lock replay. Input:
`d77ea438c9de9e604ce3432ad462e97943ba04598560e6fcbb37a382e4d8d4b8`;
preparation:
`9821ed48736ad565791cfeca5a571f0d93a77221616548dcc830af1d504f43a1`.
Visibility run `40115175363` binds exact head
`793ad65639f5671bcdf6493299a50b2d80525b38` and remains pending separate admission.
Two actual independent fresh-cache locked builds reproduce eleven archives
with combined archive-map SHA-256
`9e8e53140f63b3db291645c842b9300a1ead852305528a1c7c8b78ec43986115`;
ten loaded dependency images match their archives. Each passes 280 artifact
cases and 89 metadata cases per provider without skips. Earlier measured
transfer packets are unchanged, not fresh session/category origins.
All 280 tooling tests pass (263 passes/seventeen native macOS skips), along
with SDK/accepted-source whitespace, compiled/frozen catalogs, mechanical
five-body comparison and patch integrity. Product APIs/edges/ADRs/diagrams,
deployment examples and tracked locks are unaffected by this extraction.

Four original stream-ownership methods now execute provider-free shared checks:
cooperative source/destination inactivity, idle-read expiry, retained
noncooperative source and retained noncooperative destination. All eight frozen
parameters and original assertion tokens/order match mechanically after explicit
setup/seam/helper/cancellation forwarding. All three stream-helper bodies also
match exactly. The legacy pending-source type forwards to that same shared
implementation, preserving remaining fixture consumers rather than duplicating
it. Actual clock and provider settlement remain fixture-side.

A genuine-store mutation requires actual source cancellation with retained live
ownership before falsely reporting Released cleanup. The unchanged shared
retained-ownership equality assertion fails on both providers. Actual source
release and provider settlement complete; one actual stage and one altered
report corroborate the mutation. Fresh genuine providers pass unchanged.
This is logical stream/ownership proof, not durable crash or new kernel RSS
measurement. Missing consumers first failed actual package-mode compilation
with CS0103; the missing exact scope failed its named tooling regression.
The new ten-row scope appends eight frozen originals plus two mutation
parameters, requesting 61 scopes/498 observations, pending. Remaining budget/
ownership and complete binding/session/category/profile work is not supplied.

The preceding visibility run
[40115175363](https://github.com/Stonefly-Labs/Hoard/actions/runs/40115175363)
passed at exact head `793ad65639f5671bcdf6493299a50b2d80525b38`: all three jobs,
171 foundations without failures/errors/skips and 59 scopes/470 exact
discoveries/executions, including all four new visibility rows. All actual
SQLite/Local recovery, four paced transfer/RSS rows, six retained-worker chains,
external wrappers, native containment and eighteen-package/thirteen-lock replay
also passed strict admission. Input:
`d4db9e7fe5f3788b99f5a2a8fd5f6c1e708f18639894afd71c3c8edf5dc949fd`;
preparation:
`ea2609497216261e1c752d4376603f80f60c64f267ffdbdb711309c42ca8688a`.
History run `40116055015` binds exact head
`37ec19a9e6f203106088b37a0ac696c6aab9111d` and remains pending separate admission.
Two actual independent fresh-cache locked builds reproduce eleven archives
with combined archive-map SHA-256
`6f0ca1bf3a3c4a189675211cf3e38eba7f67dfe874383dad494f76d822ecfa32`;
ten loaded dependency images match their archives. Each passes 282 artifact
cases and 89 metadata cases per provider without skips. Earlier actual transfer
packets are unchanged, not fresh session/category origins. All 281 tooling
tests pass (264 passes/seventeen native macOS skips), along with SDK/accepted-
source formatting, compiled/frozen catalogs, mechanical four-body/three-helper
comparison and patch integrity. Production APIs/edges/ADRs/diagrams, deployment
examples and tracked locks are unaffected.

Three original cancellation/current-owner bodies now execute shared checks:
external renewal survives an older cancellation, progress renewal fences the
same admitted owner, and invalid/stale cancelled descriptors preserve the
current verified handle. Exact original assertion tokens/order match
mechanically after explicit setup/seam/helper/cancellation forwarding. Actual
clock, publication/progress observer registration, boundary removal/release and
worker settlement stay fixture-side. Two identities are frozen category
witnesses and eight are additional existing fixture cases, not new frozen
entries.

A real-store mutation captures actual verified staging, forwards the cancelled
altered-completion commit to the genuine provider, waits for actual worker
settlement and abandons that current verified owner. The unchanged consumer's
pending-state type assertion fails on both providers. Exactly one stage, one
commit and one actual abandonment corroborate the intended failure, while
fresh genuine stores pass unchanged. The first version attempted abandonment
after logical return but before physical settlement: its strict setup guard
failed for both providers under whole-suite concurrency despite focused
success. Actual fixture settlement before abandonment fixes that race without
sleeps/retries, changed shared expectations or relaxed exception guards.

Actual missing shared methods first failed package-mode compilation with
CS0117; the missing exact scope failed its named tooling regression. The new
twelve-row scope appends ten original cases plus two mutations, requesting
62 scopes/510 observations, pending. Complete task/checklist/stage acceptance
does not advance.

Corrected `cancellation-settled` and independent `cancellation-replay` private
preparations each passed all 284 artifact cases and 89 metadata cases per provider,
without skips. Eleven archives and ten actual loaded dependency images reproduce
exactly; combined archive-map SHA-256:
`44f0c0efc66c7dcb83d809b90e8d5c1e6238397ae83a9b2c99f8b26d14d95826`.
Earlier measured transfer packets are unchanged, not fresh session/category
origins. `python3 -m unittest discover -s tests/tooling -v` passed:
282 discovered, 265 passed and seventeen native macOS skips. SDK and accepted
artifact whitespace checks, compiled/frozen catalogs, three-body mechanical
comparison and patch integrity passed.

The preceding history request
[40116055015](https://github.com/Stonefly-Labs/Hoard/actions/runs/40116055015)
passed at exact head `37ec19a9e6f203106088b37a0ac696c6aab9111d`: all three jobs,
172 foundations without failures/errors/skips, 60 scopes/488 exact discoveries/
executions and all eighteen history rows. All actual SQLite/Local recovery,
four paced transfer/RSS rows, six retained-worker chains, external wrappers,
native containment and eighteen-package/thirteen-lock replay passed admission.
Input: `4e103311ace86f8845a03cd53ac86133ccd912051d6b794b9c7caea7ecdd985b`;
preparation:
`d5169e04bb38147d9de543490952e264146aa6f6955c5798b85180766b199f8f`.
Stream-ownership run `40116943400` passed at exact head
`5974f38025d550fab727e3a8bb878077af2e6749`: all three jobs, 173 foundations
without failures/errors/skips, 61 scopes/498 exact discoveries/executions and all
ten ownership rows. All actual recovery/transfer/retention/external/native
prerequisites and eighteen-package/thirteen-lock replay passed strict admission.
Input: `6fad4115ca745592821a96dae8607e8171065480706f50f5f68ef777f78ef61f`;
preparation:
`405328324fd3fbb4f5c6d06017f0475b31387e56edc18c015abdf0bcf989cc90`.

Four original result-handoff/expiry bodies now execute provider-free shared
consumers, preserving all twelve frozen parameter identities and exact original
assertion tokens/order after explicit setup/seam/helper/cancellation forwarding.
Actual completion/release observers, holds, entry, observer removal, boundary
release, clocks and worker settlement stay fixture-side at the original control
boundaries. A genuine-store mutation hides a successful reservation after
actual cancellation at release. The unchanged success-type assertion fails on
each provider; exactly one reservation and actual publication with that same
hidden ticket corroborate the intended fault. Fresh genuine providers pass
unchanged. Missing consumers first failed actual compilation with CS0103, and
the missing exact native scope failed its named tooling regression.

The new fourteen-row scope requests twelve frozen witnesses plus two mutations,
63 scopes/524 observations, pending, not complete category/session/profile proof.
The preceding cancellation request binds exact head
`631f9c46a90936361c04aa431e5a6f1f5a19b41b`, run `40118166329`, now admitted
below. Tooling passed 283 discovered / 266 passed /
seventeen native macOS skips. SDK/accepted-wrapper whitespace checks, compiled/
frozen catalogs and four-body mechanical comparison passed. Complete task,
reviewer-checklist and stage acceptance remain open.

Both original capability bodies now execute interface-only shared consumers,
preserving sixteen frozen missing-guarantee/version/authority parameters and
two additional existing complete-capability cases. Actual injection, provider
construction, filesystem/readiness observation and private-root cleanup remain
fixture-side. Exact original assertion tokens/order match mechanically after
explicit setup/observation/cancellation forwarding: rejection before I/O,
actual readiness, configured limits, optional ranges, SHA-512 and stop/release.
The complete-capability consumer owns its original fixed configured limits;
providers do not supply expected capability values.

Missing shared consumers first failed actual compilation with CS0103; the
missing exact native scope failed its named tooling regression before wiring.
The new eighteen-row scope requests 66 scopes/567 observations, pending, not
complete category/session/profile proof. The preceding authority request binds
exact head `7ee1c61a26fc9fb55473dcbc1c7890d2675ba579`, run `40120167356`,
now admitted below. Tooling passed 286 discovered / 269 passed /
seventeen native macOS skips. SDK/accepted-wrapper whitespace, compiled/frozen
catalogs and two-body mechanical comparison passed. Task, reviewer-checklist and
stage acceptance remain open.

`capability` and independent `capability-replay` each passed 289 artifact cases
plus 89 metadata cases per provider, without skips. Eleven archives and ten
actual loaded dependency images reproduce exactly; combined archive-map SHA-256:
`9a9c1292007452bdbc978884184e0aca00c6d404840e207e8af9236db736293e`.
Previously measured transfer packets remain unchanged, not fresh session/
category origins. Tracked locks, historical consumers/binaries and production
APIs remain unchanged.

Expanded budget run
[40119412481](https://github.com/Stonefly-Labs/Hoard/actions/runs/40119412481)
passed at exact head `70dfdf63f59a13ba39d934a7ef09f148bfc58c57`: all three
jobs, 176 foundations without failures/errors/skips, 64 scopes/542 exact
discoveries/executions, all fourteen handoff rows and eighteen budget rows.
All actual recovery/transfer/retention/external/native prerequisite chains,
native containment and eighteen-package/thirteen-lock replay passed strict
admission. Input:
`d5769b5f8fa45e080866fc154d65c9764ccb1d9e70cdd906af8811ff5b22f8cd`;
preparation:
`6916185a0c4940561f05c14fdf31883391b5f35e4992d35ac28b50e955b6730a`.
This admits handoff at `70dfdf6`, not the canceled handoff-only run.

Four original metadata/artifact integration bodies now execute interface-only
shared consumers on all four actual SQLite/Memory and Local/ObjectSemantics
combinations, preserving sixteen frozen parameter identities. Exact assertion
tokens/order, waiting/stream/commit/evidence helpers and seed data match
mechanically after explicit setup/seam/cancellation forwarding. Actual
composition, proof encoding, waiting counters, M1 hold/entry/release and both
stores' physical settlement remain fixture-side at the original boundaries.
The shared consumer retains reference-versus-deletion ordering, failed-
transaction orphan visibility, actual reference removal/stale-proof rejection
and lost-acknowledgment reference protection without concrete provider types.

A real-store mutation requires an actual reference-denied deletion before
misclassifying that result as conflict. The unchanged shared expected-code
assertion fails on each of the four combinations; exactly one actual deletion
and observed denial corroborate each negative, and fresh genuine stores pass
unchanged. Missing shared type first failed actual compilation with CS0246;
the missing exact twenty-row scope failed its named tooling regression before
wiring. It requests 67 scopes/587 observations, pending, not complete
category/session/profile proof or T033 acceptance.

The preceding capability request binds exact head
`2a7be14b5a32b2a11e28f582448977d89c346778`, run `40120937967`, now admitted
below. Tooling passed 287 discovered / 270 passed /
seventeen native macOS skips. SDK/accepted-wrapper whitespace, compiled/frozen
catalogs, four-body and helper/data mechanical comparisons and patch integrity
passed. Complete task, reviewer-checklist and stage acceptance remain open.

`integration` and independent `integration-replay` each passed all 293 artifact
cases plus 89 metadata cases per provider without skips. Eleven archives and
ten actual loaded dependency images reproduce exactly; combined archive-map
SHA-256:
`a2dbaeef9d08c7d257c4111450e711a0f6f6c3e87f97e46cf7c1d3ea296cd154`.
Previously measured transfer packets remain unchanged, not fresh session/
category origins. Tracked locks, historical consumers/binaries and production
APIs are unchanged.

Authority run
[40120167356](https://github.com/Stonefly-Labs/Hoard/actions/runs/40120167356)
passed at exact head `7ee1c61a26fc9fb55473dcbc1c7890d2675ba579`: all three
jobs, 177 foundations without failures/errors/skips, 65 scopes/549 exact
discoveries/executions and all seven authority rows. Every actual recovery/
transfer/retention/external/native prerequisite chain, native containment and
eighteen-package/thirteen-lock replay passed strict admission. Input:
`8bb1f75b731599fe38faefa2ef2ca84be4debc749f4b3a4cac566a7ae8fff303`;
preparation:
`126ca87d840a7576d8ac58b045ba3b14a1627d9ba7fb4542e76e2bca39724cf2`.

Three original metadata-bridge bodies now execute interface-only shared
consumers, preserving one frozen authority-mismatch witness and two additional
existing exact/invalid-evidence facts. Actual host bridge/controlled-validator
construction, encoding, expiry and observed waiting/retained/call counters stay
fixture-side. The validator delegates its exact recognized-reference operation/
stamp assertions to the shared helper; all remaining real retention/decision
logic stays unchanged in the fixture. Mechanical comparison preserves original
assertion tokens/order and that validator body after explicit seams.

The missing common type first failed actual compilation with CS0246; the
missing scope failed its named tooling regression. The exact-scope check then
exposed that the frozen witness is the mismatch fact, not the positive bridge
fact. The two non-frozen existing identities are now explicit without changing
the baseline. The new three-row request is 68 scopes/590 observations, pending,
not complete provider/category/session qualification; these remain host-bridge
unit checks with a controlled validator.

The preceding four-way integration request binds exact head
`4c876675728a7fa21b47942c816e065cafdeb140`, run `40121897879`, pending
separate strict admission. Tooling passed 288 discovered / 271 passed /
seventeen native macOS skips. SDK/accepted-wrapper whitespace, compiled/frozen
catalogs, three-body/recognized-reference/validator mechanical comparisons and
patch integrity passed. Task, reviewer-checklist and stage gates remain open.

`bridge` and independent `bridge-replay` each passed all 293 artifact cases
plus 89 metadata cases per provider without skips. Eleven archives and ten
actual loaded dependency images reproduce exactly; combined archive-map SHA-256:
`9f6e6dc8112844aa28f250f8f26308f3209476b0be31808114e00e47b53f6cae`.
Previously measured transfer packets remain unchanged, not fresh session/
category origins. Tracked locks, historical consumers/binaries and production
APIs are unchanged.

Capability run
[40120937967](https://github.com/Stonefly-Labs/Hoard/actions/runs/40120937967)
passed at exact head `2a7be14b5a32b2a11e28f582448977d89c346778`: all three
jobs, 178 foundations without failures/errors/skips, 66 scopes/567 exact
discoveries/executions and all eighteen capability rows. Every actual recovery/
transfer/retention/external/native prerequisite chain, native containment and
eighteen-package/thirteen-lock replay passed strict admission. Input:
`fca6f8887233d4f1d32430c41520fdbf276c763dbd2f3b6b685f796e0950c649`;
preparation:
`9966fd10a5f0c49b1d2b026339153ec7a350030aa07972e2a91ae39762be4297`.

The three remaining original noncooperation/lifecycle bodies now execute shared
interface-only consumers: composed shutdown with an actual retained reference
query, concurrent close with real slow physical guard release, and deadline/
stop with held native I/O. Four parameters are frozen category witnesses; two
composed-shutdown cases are additional existing facts. Actual composition,
query setup/completion/drain, slow guard implementation, native I/O holds,
physical release/removal and settlement stay fixture-side. Shared consumers
own the unchanged shutdown/ownership/fencing/deadline/retry checks and generic
bounded-failure helper. Mechanical comparison verifies their exact tokens/order
and unchanged fixture setup/release/slow-guard logic after explicit seams.

Missing shared consumers first failed actual package-mode compilation with
CS0103; the missing exact scope failed its named tooling regression. The new
six-row native request is 69 scopes/596 observations, pending, not complete
bindings/category/session or full profile qualification. The preceding bridge
request binds exact head `b4d4517d82515534afe1b84ad5f7d81245916f82`,
run `40122736140`, pending separate strict admission.

Tooling passed 289 discovered / 272 passed / seventeen native macOS skips.
SDK/accepted-wrapper whitespace, compiled/frozen catalogs, three-body/helper/
fixture-seam mechanical comparison and patch integrity passed. Tracked locks,
historical consumers/binaries, production APIs and reviewer-owned checklists
are unchanged. Broad task and stage gates remain open.

`lifecycle` and independent `lifecycle-replay` each passed all 293 artifact
cases and 89 metadata cases per provider without skips. Eleven archives and ten
actual loaded dependency images reproduce exactly; combined archive-map SHA-256:
`2370051325ecef8fbb98849c1efee3018e93d44901d009b61aae2a8c6b27d238`.
Previously measured transfer packets remain unchanged, not fresh session/
category origins or new durable proof.

Two original storage-failure/reconciliation bodies now execute interface-only
shared consumers with all four frozen parameters, fixed classification/
sanitizer checks and the unchanged failing-source helper. Actual post-visibility
fault registration stays fixture-side. Common checks preserve original borrowed
source, unpublished staging, committed-byte, exact-ticket/action and receipt
retry assertions. Actual access-denied staging failures deliberately relabeled
as unavailable fail the unchanged code assertion on both providers; exactly one
stage/observed denial each corroborates the mutation. Genuine stores pass the
unchanged consumers.

Missing consumers first failed actual package-mode compilation with CS0103;
the missing exact scope failed its named tooling regression. The intermediate
`failures` preparation rejected an attempted SDK dependency from the separate
foundation-only harness. That harness remains unchanged and SDK-independent;
the common consumers retain the same fixed canaries and two sanitizer checks
rather than introducing a reverse dependency or provider-selected verifier.
Mechanical comparison checks both original bodies, failing-source helper,
sanitizer tokens/fixed values and unchanged remaining physical-cleanup bodies/
helpers. The new six-row request is 70 scopes/602 observations, pending.

Tooling passed 290 discovered / 273 passed / seventeen native macOS skips.
SDK/accepted-wrapper whitespace, compiled/frozen catalogs, exact mechanical
comparisons and patch integrity passed. The preceding lifecycle request binds
exact head `f2cc84decfbd1b099f57e82b40d9636b65b8695e`, run `40123477371`,
pending separate strict admission. Bridge-only run `40122736140` at `b4d4517`
was canceled while pending, not accepted; the expanded lifecycle request
includes its three rows, still pending. Broad tasks/checklists/stage remain
open; no full binding/session/category/profile qualification is claimed.

Four-way integration run
[40121897879](https://github.com/Stonefly-Labs/Hoard/actions/runs/40121897879)
passed at exact head `4c876675728a7fa21b47942c816e065cafdeb140`: all three
jobs, 179 foundations without failures/errors/skips, 67 scopes/587 exact
discoveries/executions and all twenty integration rows. Every actual recovery/
transfer/retention/external/native prerequisite chain, native containment and
eighteen-package/thirteen-lock replay passed strict admission. Input:
`a5869dfd419f2fcc869633479bc99c4524ad1affa9fec306c8496079583047ea`;
preparation:
`f15f9d1ec24f010e0e96d50e15ab3a1aa16c94a46e9bca929e5fca0596fb9c24`.
These are diagnostic results, not complete T033 or category qualification.

`failures-fixed` and independent `failures-replay` each passed all 295 artifact
cases and 89 metadata cases per provider without skips. Eleven archives and ten
actual loaded dependency images reproduce exactly; combined archive-map SHA-256:
`6ceb368a187a5d85704bfe409a9f71a35c7f071b2d3276223ad465b6ba50a9eb`.
Previously measured transfer packets remain unchanged, not fresh session/
category origins or new durable proof. Historical consumers/binaries, tracked
locks and production APIs remain unchanged.

Configured publication, compatible reopen and fresh-epoch artifact operations
now execute interface-only shared consumers, preserving fixed original content,
identity/epoch, exact ticket/receipt and protected-read assertions. Actual host
construction, DI/configuration evaluation, mapping, module cardinality/identity/
readiness, disabled-root observations, restart selection, stop and missing-
guarantee inert-start rejection remain in the hosting fixture. No Hosting/Core
dependency enters the SDK. Mechanical comparison verifies all three artifact
operation blocks and unchanged complete host orchestration/defaults/inert-start
body after explicit store/identity/cancellation forwarding.

Missing consumers first failed actual package-mode compilation with CS0103;
the missing exact scope failed its named tooling regression. All four frozen
host cases remain unchanged. The new four-row native request is 73 scopes/
617 observations, pending, not complete binding/session/category/composition
profile acceptance. Tooling initially rejected local scratch below its actual
24 GiB gate; reclaiming only 32 inspected completed-session NuGet caches restored
capacity without changing that guard or deleting source, package archives,
manifests or loaded images. The rerun passed 293 discovered / 276 passed /
seventeen native macOS skips. SDK/accepted-wrapper whitespace, compiled/frozen
catalogs, exact comparisons and patch integrity passed.

Prefix-cleanup run
[40125248164](https://github.com/Stonefly-Labs/Hoard/actions/runs/40125248164)
passed at exact head `871e3a860a07646c513de01095cc29ad3e4add70`: all three
jobs, 183 foundations without failures/errors/skips, 71 scopes/608 exact
discoveries/executions and all six cleanup/stop/reopen rows. Every actual
recovery/transfer/retention/external/native prerequisite chain, native containment
and eighteen-package/thirteen-lock replay passed strict admission. Input:
`43b6d2627018f373112f5c9fc9e905e204b6bc291b0ed528d77f755d2b9117e3`;
preparation:
`86efcad80e99ec07ca0f96bbc7dcba8b4ef98a237780a71c764e063839f4e0d1`.
Object-cleanup run `40126135553` binds exact head
`3de87aadf19bc83da2a8dc229335a19630d77ae5`, pending separate strict admission.
Broad tasks, reviewer-owned checklists and stage gates remain open.

`configured` and independent `configured-replay` each passed all 295 artifact
cases and 89 metadata cases per provider without skips. Eleven archives and ten
actual loaded dependency images reproduce exactly; combined archive-map SHA-256:
`499229ddb0e58c9b57ed2c1cf59a44142e25b7bcd29c3cbe04867d767c56b1ce`.
Previously measured transfer packets remain unchanged, not fresh session/
category origins or new durable proof. Historical consumers/binaries, tracked
locks and production APIs remain unchanged.

Both remaining original object-cleanup bodies now execute common interface-only
checks with all five frozen parameters, completing original failure-body
extraction without claiming T027/T030 complete. Selected-object receipt/reuse,
unselected assembly ownership/retry, exact reclaimed bytes and fresh-owner
fencing assertions preserve original tokens/order. Actual permission changes,
observer registration/removal, filesystem snapshots/lengths and physical worker
settlement stay fixture-side. The private progress/compare hook translates to
the existing logical during/after-assembly input; shared checks own all fixed
expected codes/sizes/owners/receipts. SDK code has no private hook names,
filesystem operations or concrete-provider switches.

Missing consumers first failed actual package-mode compilation with CS1061;
the missing exact scope failed its named tooling regression. The intermediate
`object-cleanup` preparation failed CA1416 because an outer platform guard
does not flow into deferred restore lambdas. Reusing a fixture-side restoration
helper with its own existing Unix guard fixes the actual cause, without
suppressions or changes to physical restoration/order. Mechanical comparison
verifies both bodies, actual observer callbacks, exact semantic phase mapping,
guarded restore helper and unchanged other cleanup bodies/helpers after explicit
seams. Only the non-I/O path calculation moved into fixture setup.

Tooling passed 292 discovered / 275 passed / seventeen native macOS skips.
SDK/accepted-wrapper whitespace, compiled/frozen catalogs, exact comparisons
and patch integrity passed. The new five-row native request is 72 scopes/
613 observations, pending. The preceding prefix request binds exact head
`871e3a860a07646c513de01095cc29ad3e4add70`, run `40125248164`, pending
separate strict admission. Broad tasks, reviewer-owned checklists and stage
gates remain open.

Storage-failure run
[40124374635](https://github.com/Stonefly-Labs/Hoard/actions/runs/40124374635)
passed at exact head `ff50acda07e9bc8eb00277de2eb20140d2f39e5f`: all three
jobs, 182 foundations without failures/errors/skips, 70 scopes/602 exact
discoveries/executions and all six storage-failure/mutation rows. Every actual
recovery/transfer/retention/external/native prerequisite chain, native containment
and eighteen-package/thirteen-lock replay passed strict admission. Input:
`af73ffddfa86f65c5855735147a1d7ad4da4bdb06e123601cd023587d26a7a7a`;
preparation:
`9a90d9553f8c410ccf50b6222ad4f5bb156cc1645412ac138d307449f27f8355`.

`object-cleanup-fixed` and independent `object-cleanup-replay` each passed all
295 artifact cases and 89 metadata cases per provider without skips. Eleven
archives and ten actual loaded dependency images reproduce exactly; combined
archive-map SHA-256:
`d0a046589837aa55c1dd6ccac19965ba7c6bce41a89d1592ab569a7f9339a5f5`.
Previously measured transfer packets remain unchanged, not fresh session/
category origins or new durable proof. Historical consumers/binaries, tracked
locks and production APIs remain unchanged.

Three original prefix-cleanup bodies now execute interface-only shared checks
with all six frozen parameters: committed receipts with residual staging,
failed prefix reclamation/fencing and failed-prefix stop/settlement. Original
Local post-stop reopen assertions also execute shared checks. Actual permission
changes, observer registration/removal, readiness/directory snapshots, concrete
stop implementation and Local-only reopen/initialization/final stop remain
fixture-side. The same borrowed source survives the stop/reopen fixture scope.
Common checks preserve exact receipt/owner/cleanup/fencing assertions and every
operation/order; ObjectSemantics gains no claimed durable restart.

Missing common type first failed actual package-mode compilation with CS0246;
the missing exact scope failed its named tooling regression. Mechanical
comparison verifies all three bodies, post-stop reopen checks and unchanged
actual stop/reopen/control setup after explicit seams. The new six-row request
is 71 scopes/608 observations, pending. Tooling passed 291 discovered /
274 passed / seventeen native macOS skips. SDK/accepted-wrapper whitespace,
compiled/frozen catalogs, exact comparisons and patch integrity passed. Broad
tasks, reviewer-owned checklists and stage gates remain open.

Lifecycle run
[40123477371](https://github.com/Stonefly-Labs/Hoard/actions/runs/40123477371)
passed at exact head `f2cc84decfbd1b099f57e82b40d9636b65b8695e`: all three
jobs, 181 foundations without failures/errors/skips and 69 scopes/596 exact
discoveries/executions, including all three bridge and six lifecycle rows.
Every actual recovery/transfer/retention/external/native prerequisite chain,
native containment and eighteen-package/thirteen-lock replay passed strict
admission. Input:
`bf6e1a22dac1c6c3a58b55f70430e981eeffb67d443dc64dbba19cab031e1643`;
preparation:
`01f0cb2c3088be6ea79682ab8bb10d5359e703d40f31907f9ab1f43c50800bf9`.
The first observer invocation expected 180 foundations and correctly rejected
that mismatch; rerunning with the observed exact 181 passed. This is observer
configuration, not a failing CI run or acceptance of the canceled bridge-only
run. Storage-failure run `40124374635` binds exact head
`ff50acda07e9bc8eb00277de2eb20140d2f39e5f`, pending separate strict admission.

`prefix` and independent `prefix-replay` each passed all 295 artifact cases
and 89 metadata cases per provider without skips. Eleven archives and ten
actual loaded dependency images reproduce exactly; combined archive-map SHA-256:
`d79953069b35ca32f181a4e6f3f1a08e68e0841424c052efb00d024e1eee8511`.
Previously measured transfer packets remain unchanged, not fresh session/
category origins or new durable proof. Historical consumers/binaries, tracked
locks and production APIs remain unchanged.

`handoff` and independent `handoff-replay` preparations each passed 286 artifact
cases plus 89 metadata cases per provider, without skips. Eleven archives and ten
actual loaded dependency images reproduce exactly; combined archive-map SHA-256:
`5f0303c67e701e52fd8df820dd4564f238959233251906c2b7939e1aafd78745`.
Earlier measured transfer packets remain unchanged, not fresh session/category
origins. No tracked locks, historical binaries or production APIs changed.

The remaining six original `ArtifactBudgetTests` bodies now execute provider-
free shared consumers: failed unclaimed-result cleanup/retry, terminal cancelled
publication, full transfer queue, cap crossing, authority contention and
cooperative cancellation. All sixteen frozen parameters and exact original
assertion tokens/order match mechanically after explicit setup/seam/helper/
cancellation forwarding. Actual completion/reclaim/queue observers, barriers,
real worker settlement/stop, limits and authority creation remain fixture-side.
The common authority checks accept only the Abstractions interface and actual
identity, not the concrete host adapter.

A genuine-store mutation requires the actual input-limit failure before
misclassifying it as capacity. The unchanged shared expected-code equality
assertion fails on each provider; one actual staging call and one observed
limit failure corroborate the intended fault. Fresh genuine providers pass
unchanged. Missing common consumers first failed actual compilation with
CS0103; the missing exact native scope failed its named tooling regression.
The eighteen-row scope requests sixteen frozen witnesses plus two mutations,
64 scopes/542 observations, pending, not category/session/profile acceptance.
The preceding handoff request binds exact head
`ffda43a96151de9c71dfc99dda5b22c374739b24`, run `40118782562`. It was
canceled while pending and is not admitted; later expanded requests retain
the full handoff scope.

Tooling passed 284 discovered / 267 passed / seventeen native macOS skips.
SDK/accepted-wrapper whitespace checks, compiled/frozen catalogs and six-body
mechanical comparison passed. Complete task, reviewer-checklist and stage gates
remain open; this finishes the original budget-body extraction, not T027/T030
or the complete artifact binding/profile.

`budget` and independent `budget-replay` preparations each passed all 288
artifact cases plus 89 metadata cases per provider without skips. Eleven
archives and ten actual loaded dependency images reproduce exactly; combined
archive-map SHA-256:
`7b31d0e687344cc81863a4c2fc1e40b977e3fac648c65694337df249246aa439`.
Previously measured transfer packets remain unchanged, not fresh session/
category origins; tracked locks and historical consumers/binaries are unchanged.

Six original authority bodies now execute interface-only shared consumers,
preserving three frozen category witnesses, three additional existing facts,
all assertion tokens/order and the exact copied-guard helper. Actual authority
construction, clock, waiting/retained counters, reference completion and drain
remain fixture-side. A real authority rejects the copied handle before a faulty
adapter repairs it using actual recognized retention. The unchanged failure-
type assertion fails; actual denial/repair counters each equal one, repaired
retention is explicitly disposed, and genuine authority passes unchanged.
Missing shared type first failed actual compilation with CS0246. An intermediate
build also exposed the missing Abstractions.Metadata import for `ArtifactDigest`;
adding its existing namespace fixes that without dependencies/API changes.
The missing exact seven-row scope failed its named tooling regression before
wiring. It requests 65 scopes/549 observations, pending, not complete
category/session/profile qualification.

The cancellation request
[40118166329](https://github.com/Stonefly-Labs/Hoard/actions/runs/40118166329)
passed at exact head `631f9c46a90936361c04aa431e5a6f1f5a19b41b`: all three
jobs, 174 foundations without failures/errors/skips, 62 scopes/510 exact
discoveries/executions, all twelve cancellation rows and all actual recovery/
transfer/retention/external/native prerequisite chains plus eighteen-package/
thirteen-lock replay. Input:
`3db30cc16c206a72a14d64b3d9f1bfecb3b9f9c772adec7959cb1947b99585c2`;
preparation:
`8a3b47f7297e523d12ae142b6da3d7ade1c43bd37552696087d4e1a076cbd420`.
The budget request binds exact head
`70dfdf63f59a13ba39d934a7ef09f148bfc58c57`, run `40119412481`, now admitted
below. It includes the canceled handoff-only request's scope, but that does not
make the canceled run successful.

`authority-fixed` and independent `authority-replay` each passed 289 artifact
cases plus 89 metadata cases per provider, without skips. Eleven archives and
ten actual loaded dependency images reproduce exactly; combined archive-map
SHA-256:
`a4ba04603332bd0ebeee15f619893a021c76274e750535399086d024e429beb4`.
Previously measured transfer packets remain unchanged, not fresh session/
category origins. Tooling passed 285 discovered / 268 passed / seventeen native
macOS skips. SDK/accepted-wrapper whitespace, compiled/frozen catalogs, six-body/
copied-helper mechanical comparison and patch integrity passed. Complete task,
reviewer-checklist and stage acceptance remain open.

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

### Authority quiescence before owned artifact adapters

Architecture review identified that retained-query drain and provider idle
snapshots do not account for ordinary/retained guards or queued authority
admissions. An explicit test-fixture closing fence now rejects new acquisitions
and exposes one stable settlement task covering all those owners plus actual
retained reference queries. Existing same-operation retention and already queued
admission remain valid until their guards settle. Reopen rejects live ownership
and creates a fresh settlement generation; the default unfenced behavior is
unchanged. This does not add a production contract or a second authority engine.

Local/Object binding projects source-link the single existing authority source.
A binding-only compilation symbol makes both authority/reference-decision types
internal while preserving their public HostAdapters form. No new package
dependency, Hosting/cross-provider edge or public binding type collision is
introduced. Complete owned category sessions and mandatory fault controls remain
unfinished; T028/T029 are not checked.

Three common interface-only checks exercise retained/queued guards, actual
noncooperating reference settlement, canceled waiters and reopen generations.
Missing lifecycle hooks first failed actual package-mode compilation with CS1061;
missing transport failed its exact-scope tooling regression. The next three-row
native request is 74 scopes/620 observations, pending. Tooling passed 294
discovered / 277 passed / seventeen native macOS skips. SDK, accepted-wrapper
and authority whitespace, compiled/frozen catalogs and patch checks passed.

`authority-ownership` and independent `authority-ownership-replay` each passed
298 artifacts and 89 metadata cases per provider without skips. Eleven archives
and ten loaded dependency images reproduce exactly; combined archive-map SHA-256:
`7d459f8975685ec1b67efaeaba8bf8b42a8707dc48244c5a0915ef7a4d16d28a`.
Two additional independent source-linked package builds reproduced Local
`a1187da22da2f26329977f14adcb19a99e0f575a714bd02fe5a50db6a4782435`
and ObjectSemantics
`01c740523891b11ec1a28d56c17615f74eea7c256d9b756866bafcb143cb2212`.
Runtime probes exercised actual private authority copies, retained guard
settlement and reopen, and inspected actual public visibility and dependency
closures. The first private recipe omitted nested central package policy and
failed NU1010; copying that existing policy corrected the recipe, not project
dependencies. Tracked locks and historical sources/binaries remain unchanged.
Previously measured transfer packets are unchanged, not fresh category origins.

Object-cleanup run
[40126135553](https://github.com/Stonefly-Labs/Hoard/actions/runs/40126135553)
passed at exact head `3de87aadf19bc83da2a8dc229335a19630d77ae5`: all three
jobs, 184 foundations without failures/errors/skips, 72 scopes/613 exact
discoveries/executions and all five new rows. Every actual prerequisite chain,
native containment and eighteen-package/thirteen-lock replay passed strict
admission. Input:
`b7b093f225913a2cf45192913ed1deafc54bd0d1e205fb008743a0e37f919bd0`;
preparation:
`a9a2e018a0f4f2f2b6cafcc64a998704fc65e03197d1df57fc09575e6c6aac18`.
Configured-store run `40127065375` binds exact head
`9ce6b252918149d225a0794fe168989dc317692f` and passed strict admission:
all three jobs, 185 foundations without failures/errors/skips and 73 scopes/
617 exact discoveries/executions, including all four frozen host cases,
every actual prerequisite/native containment chain and eighteen-package/
thirteen-lock replay. Input:
`3efc4e7b362041d781d77b0f3f9b5338907723485e4b6cbfdea472f9e8e7949f`;
preparation:
`494dbcfb5394f72be741bc448043709b0fa30d54536f0a9fce648698968d595b`.
The driver remains `implement / running`; broad tasks, reviewer-owned
checklists and full profile/category gates remain open.

### Partial owned Local artifact assertion session

`IArtifactAssertionSession` and typed `ArtifactObservationPoint` expose only an
explicit partial assertion projection, not a complete category binding or
mandatory fault-driver stubs. The Local factory allocates before construction,
uses the real provider beneath the allocator root's `store` child and joins
failed admission. Actual validator, maintenance/lifetime, scoped observer
registration and compatible reopen preserve one resource/identity/authority;
stale disposal cannot release a replacement. No root is physically deleted and
no `Released` observation is fabricated.

Disposal serializes transitions, shares concurrent attempts, reuses unfinished
allocator observations, and preserves one actual settlement task through retry.
That task joins real store/worker/authority ownership; actual observer failures
fault it only after physical joins, including failures completed before cleanup
and failures while stop is already awaiting a callback. Ready remains false
after a recorded observer failure. `AwaitSettlementAsync` documents its narrower
provider-worker-only guarantee.

Bounded architecture review identified optimistic callback ownership and
overlapping allocator observation. Four new regressions first failed with eight
existing Local cases passing. Delaying removal of original activity/retained
entries passed those twelve cases but broke eight frozen public handoff/
cancellation assertions in the full 300-case suite. Separate final-settlement
tracking now joins actual release callbacks/token disposal/final callbacks on
both providers while preserving original public admission, ticket-use, mutation
and cancellation seams. The reviewer found no further correctness issue in
this split; follow-up cases close the identified real-allocator-overlap and
callback-throw-during-stop coverage gaps.

The final package-only Consumer has fourteen Local rows, including scoped
registration, unchanged publication/expectation/staging consumers, compatible
reopen/stale disposal, retained guards, shared disposal, failed admission and
both recorded/native allocation retries. Two additional actual Local/Object
wrapper rows share a provider-free callback-ownership assertion. Both
independent package preparations pass all 300 artifact cases and 89 metadata
cases per provider without skips; the final Consumer passes fourteen without
skips. Fifteen archives reproduce exactly, manifest SHA-256:
`c90b76c93373d9b104d2b9a5d0326685a7ab88759a5f04572fa376c3e8a34cc8`.
Ten Consumer dependency images match package bytes. Previously measured
transfer packets are reused unchanged, not fresh category/session origins.
Historical sources/binaries and tracked dependency locks remain unchanged.

Native run `40128473761` at `1dc7ccf923adf6d19d3ee487e2abf5e87efdc025`
passed foundations and lock replay but failed SDK transport with `WitnessMissing`
before authority discovery. Its scope omitted the `original-artifact-` routing
prefix. An exact assembly-routing regression first reproduced that failure and
now passes; the failed run is never admitted. Local/Object binding preparation,
isolated package-only Consumer runtime/logger/dependency verification, complete
input capture and exact fourteen-row Local-vector rejection are now wired into
the diagnostic. Replacement execution requests 75 scopes/636 observations,
pending. These are diagnostic observations, not 192/179/13 category results.

Tooling passed 298 discovered / 281 passed / seventeen macOS-native skips.
Initial full tooling honestly hit the existing real 24 GiB scratch gate; only
inspected completed private package caches were removed before successful
rerun. SDK/provider/wrapper/binding/Consumer whitespace, compiled/frozen
catalogs and patch hygiene pass. README, development/provider guides, quickstart
and harness contract reflect this partial state. Product APIs, architecture/
ADR/diagrams and custom-host examples are unaffected: no production contract,
dependency graph, supported hosting/deployment or configuration behavior changed.
Only T001–T018 remain checked; complete Local/Object category bindings and
controls, parity/import/profile gates, contributor/aggregate work and final
architecture review remain unfinished. No convergence, finish, merge or release.

### Actual Object observation transitions and bounded consumed-input capture

The next bounded architecture review recommends sharing only internal owned-
session lifecycle machinery between bindings, with provider construction/control
mapping independent. Local compatible reopen must retain identity/authority;
Object logical restart must instead join the old generation before creating a
fresh epoch/authority/private child, keeping original-session identity immutable
and retaining failed replacements under the original cleanup handle. This
coordinator/Object session is still planned, not implemented.

Review identified missing Object transition hooks and a sixteen-observer ceiling
incompatible with the seventeen-point typed surface. Both fixture dictionaries
are already finitely bounded by their closed supported-name sets. Removing the
contradictory count limit admits every supported registration without admitting
unknown names; session-level duplicate/replacement protection remains unchanged.
The new complete-registration Local case first failed with fourteen existing
cases passing. All fifteen now pass, including actual invocation and removal.

Four Object hooks now expose actual receipt recording, opened streams and
reconciliation before/after verification. They do not alias `object.direct`,
which occurs before those distinct transitions. Receipt notification follows
actual in-memory simulation receipt recording; no durability is invented.
Read-open notification stays inside the existing stream/guard/slot cleanup
scope, and verified notification follows actual content verification before
final recovery recording. Three provider-free consumers run on both choices,
checking real receipt equality while notification is held, reclamation after
opened-read callback failure under one transfer slot, and actual uncertain-
publication recovery after verified callback failure. The deletion fixture
explicitly supplies a successful zero-reference decision; its original default
authority correctly denied deletion rather than proving a resource leak.
All 306 artifact and 89 metadata cases per choice pass without skips.

Native run
[40131392286](https://github.com/Stonefly-Labs/Hoard/actions/runs/40131392286)
at exact head `88c5d0182ad68dd65006e2ae3c86f3dce90a4525` passed 190
foundations without failures/errors/skips and eighteen-package/thirteen-lock
replay, but failed SDK diagnostics pre-runtime with `ProofMismatch` after
locked build replay. Preparation proof:
`9936626469727a04d13147f3e510ea336ec32f3cfe5a82d97b318a4645a1a11c`.
No runtime input receipt, authority/Local discovery or passing diagnostic is
admitted for this run.

Candidate enumeration previously hashed all copied outputs before selecting
runtime inputs, allowing unconsumed build/native assets to exhaust the bounded
inventory. It now selects the existing consumed managed/runtime formats,
admitted-architecture native assets and all locks during the same descriptor-
safe traversal. It does not increase the default 256 MiB, file-count or time
caps. Full manifests remain strict; every tree entry still receives type/
identity/race checks, including excluded-architecture symlinks. All source,
package, selected-native, lock and recomputation seals remain. A sparse
unconsumed archive above the old limit reproduces full-manifest rejection but
no longer blocks selected capture; an oversized selected DLL still rejects,
selected native mutation still invalidates inputs, and a foreign-native symlink
still rejects. New phase markers distinguish actual SQLite environment
admission from runtime capture. The native failure's exact source is not
claimed confirmed until replacement evidence is available.

Two independent preparations each passed all 306 artifact cases, fifteen Local
Consumer cases and 89 metadata cases per choice without skips. The reproduced
fifteen-archive map is
`bc1945e3f1ad5f5b9a7425aef9e026faea3a62909c925e7d6c67913a206a29a5`;
ten Consumer dependency images match their actual archives. Tooling passes
299 discovered / 282 passed /
seventeen macOS-native skips; whitespace, frozen/compiled catalogs and patch
checks pass. Replacement run `40133457888` at exact
`c58978ef016f53ab3fc8898b62b61b7bdd7d2631` passed all three jobs: 191 foundations
without failures/errors/skips, independent eighteen-package/thirteen-lock replay
and strict 76-scope/643-observation admission, including fifteen Local and six
observation rows and all actual prerequisite chains.
Input: `0e910492b63112b05c09277e70402c5c81fc6f1541a7cf938d8e3d3ee690b0e9`;
preparation:
`feef714d4c3428eda397c0440a8c7a63284ef8b1d4e285f1b33bdeb2e9b23439`.
The replacement verifies input capture through completion; it does not
retroactively admit the earlier failure or establish its precise root cause.
This remains partial F-07 implementation, not
complete Local/Object bindings, category/profile gates or a 192/179/13 result.
Tracked locks, historical seals and reviewer-owned checklists remain unchanged.

### Shared artifact ownership and partial Object assertion session

Local/Object now source-link one internal provider-free lifecycle coordinator
and session base, retaining separate actual construction, readiness, worker
settlement and private typed-boundary mappings. The SDK still references only
Abstractions/test dependencies; neither binding imports the other provider,
Hosting or the HostAdapters package. The existing source-linked authority is
the only authority algorithm.

Local compatible reopen keeps identity/authority/root/content. Object accepts
only `CreateEmpty`; its logical restart first joins old provider/authority work,
then creates an empty private child and fresh epoch/authority under the same
allocation. Original identity/authority remain immutable. Replacement authority
and session generations are tracked before initialization; only successful
admission changes `Current`. Failed/canceled replacements are joined through
the original cleanup handle. Final stable settlement joins every generation,
preserves observer failures and reuses pending allocator observations; neither
binding deletes allocator roots or reports `Released`.

Object's `CleanupCandidate` maps the actual per-target `multipart.cleanup`
callback in `CleanupAsync`, equivalent to Local's per-target cleanup observation.
It is not an alias of the synchronous history-candidate index hook. All seventeen
typed observers can register together. Sixteen Object package-only cases cover
unchanged publication/expectation/private-stage consumers, scoped observations,
fresh logical restart, stale disposal, callback joins/failure, failed replacement
and initialization, cancellation before/during replacement admission, retained
authority and direct provider stop/disposal retries with real native allocation.
The existing fifteen Local cases remain unchanged apart from sharing the
provider-neutral recording allocator helper. Bounded architecture review found
no confirmed defect; its two coverage gaps were closed before publication.

The intended exact-Object-vector regression failed before transport was added;
missing scenario references also produced two expected harness lookup errors,
not runtime assertion failures. All 74 SDK tooling checks now pass. The first
fresh package preparation passed 306 artifact cases and 89 metadata cases per
provider; the final Consumer passed all 31 Local/Object cases without skips.
Formatting passes for SDK/both bindings/Consumer. Tooling passes 300 discovered /
283 passed / seventeen macOS-native skips. Independent fresh replay passes all
306 artifact cases, 31 Local/Object cases and 89 metadata cases per choice without
skips; fifteen archives reproduce exactly, canonical archive-map SHA-256
`727d42f8e1fdb9829e83e10f6a2d615a220f9fab425489b9892205c8cac51f99`.
Ten Consumer dependency images match their actual archives. Previously measured
transfer packets remain reused unchanged, not fresh category/session origins.
The preceding 76-scope request passed at exact `c58978e`, run `40133457888`.
Owned-Object run `40134767571` at exact
`36481c058514a9d5dd22f13e51c5b629c1d8d656` passed all three jobs:
192 foundations without failures/errors/skips, independent eighteen-package/
thirteen-lock replay and strict 77-scope/659-observation admission, including
all sixteen Object rows and every actual prerequisite chain.
Input: `f54fde15ced6fd40571bb85d43385c3a584bb4fe0dd9423539b8c41abd145526`;
preparation:
`9d7247e9ebc725519057d265ea8ac2c51bd3528558dc18b2c2c99981ab2b5ce1`.
Neither is full category/profile qualification.
Tracked locks, historical seals, tasks and reviewer-owned checklists remain
unchanged. Product contracts, architecture/ADR diagrams and custom-host examples
are unaffected by this test-only ownership extraction.

### Typed artifact limits and live reference setup

Both partial factories now accept explicit SDK `ArtifactAssertionOptions` while
preserving the original default overload. Options carry immutable actual limits
and an optional live typed reference source, not case/profile selectors or pass
flags. Every provider initialization receives those limits; every authority
generation invokes the source for the protected stamp and translates only its
availability/count/revision into the unchanged private authority algorithm.
Missing queries retain fail-closed deletion. `ArtifactReferenceObservation`
rejects negative or contradictory counts and available results without
revisions; unavailable zero counts cannot authorize deletion.

The intended missing API produced CS0246 before implementation. Seven initial
configured rows passed; bounded architecture review found no confirmed defect
but identified two coverage gaps. Actual 1,025-byte reservations now fail both
before and after the configured 1,024-byte limit survives reopen. Four more
Local/Object cases retain genuine reference queries after caller timeout and
prove reopen/final cleanup cannot finish before actual query settlement.
The final Consumer passes all 42 cases, including eleven configured rows.
The first fresh preparation passes all 306 artifact and 89+89 metadata cases.
Independent fresh replay passes 306 artifact, 42 Consumer and 89+89 metadata
cases without skips; fifteen archives match exactly, canonical map SHA-256
`2da3a01d231df7002b306c6208fb31f063fb963a86c7e97c7355592367314075`.
Ten Consumer runtime images match actual package bytes. Existing measured transfer packets
remain reused unchanged, not fresh category/session origins.

The exact-scope regression first failed its named missing-transport assertion
with two related lookup errors, not runtime assertion failures. All 75 SDK
tooling checks pass. Full tooling passes 301 discovered / 284 passed /
seventeen macOS-native skips; SDK/binding/Consumer formatting, frozen inventory,
compiled catalogs and patch checks pass. Real scratch fell below the unchanged
24 GiB full-artifact gate; 76 explicitly inspected completed-mode dependency
caches were recovered, preserving sources/feeds/manifests/historical seals/
runtime images and observing more than 28 GiB free before full tooling.
Run `40136186008` at exact `853c669abb6554efaddc95a49d9fdf9a61f250ad`
passed all three jobs, 193 foundations without failures/errors/skips and strict
78-scope/670-observation admission with all actual prerequisites and independent
eighteen-package/thirteen-lock replay. Input:
`c4104825bfe5fc601fb7a053e04002be75dbbfcea90d8da81799a99b5eee2f9b`;
preparation:
`60b8884d1bb7f40c3689ee07d8a2dea553fc7b31f8cd759745a1e39c13dec77f`.
Full artifact fault drivers, category/session origins and four-way
metadata/artifact integration acceptance remain unfinished. Product contracts,
architecture diagrams, deployment examples, tracked locks, tasks and reviewer
checklists are unaffected.

### Actual owned artifact payload damage

Both partial sessions now forward exact-stamp payload damage into their own
independent provider's actual worker supervisor. Local uses `ExecuteAsync`;
Object uses `OwnedAsync`. Each resolves its own current nonremoved incarnation,
opens its own private file, observes the typed boundary with that real handle
held, then performs bounded one-byte damage or truncation and flushes/disposes
inside actual worker settlement. No SDK/provider dependency or public product
contract changes. Receipt/quarantine bookkeeping is not forged: unchanged
public copy/open detects corruption. Empty truncation explicitly fails; byte
damage also corrupts an empty payload by adding one byte.

New cases first rejected the old API with CS1061/CS0117; the exact transport
regression separately failed its intended single missing-factory assertion.
Ten initial rows pass with all 52 Consumer, 306 artifact and 89+89 metadata
cases. Bounded architecture review found no confirmed defect. Added coverage
exercises failed observers and unchanged bytes with faulted final settlement,
actual same-digest deletion/replacement, stale sessions/Object epochs, empty
content and incompatible read handles. Independent fresh replay passes all
65 Consumer (23 payload), 306 artifact and 89+89 metadata cases without skips.
Fifteen archives reproduce exactly, canonical archive-map SHA-256
`a19809e0bcb89f0cb1269443063ad2681048b4015ad0dff6e8e800ea68268e4d`;
ten Consumer dependency images match package bytes. Existing measured transfer
packets remain reused unchanged, not fresh category/session origins.
Full tooling passes 302 discovered / 285 passed / seventeen macOS-native skips;
76 SDK tooling checks, all six affected prepared project whitespace checks,
frozen inventory, catalogs and patch checks pass.

The next request is 194 native foundations and 79 scopes/693 observations,
pending. Complete fault-driver/category admission, origins and four-way
integration acceptance remain unfinished. Tasks/checklist markers, historical
seals, tracked locks, production APIs, architecture/ADR diagrams and deployment
examples are unaffected.

### Unchanged damaged-read consumer and actual-validator mutation

The four original damaged-read provider/truncation parameters now execute
`ArtifactReadAssertions.DamagedReadAsync`. Mechanical whole-body comparison
preserves exact assertions and operation order after explicit fixture callback,
interface, helper and cancellation forwarding. Actual capture/damage/restore
remain at the original legacy fixture boundaries; this extraction does not
claim complete owned fault-driver admission. SDK checks retain corrupt copy,
borrowed destination, subsequent open/evidence invalidation and permanent
quarantine after actual restoration.

The missing method first produced CS0117, confirmed independently in the
isolated compiler output. A real validator mutation requires one actual corrupt
denial before returning success; the unchanged common type assertion fails on
both providers, and genuine fresh validators pass. Its exact six-row transport
first failed the named missing-factory assertion and now passes alongside all
77 SDK tooling checks, including original assembly routing and missing/foreign
vector rejection. Independent fresh preparations each pass 308 artifact,
65 Consumer and 89+89 metadata cases without skips; fifteen archives reproduce
exactly, canonical archive-map SHA-256
`85e853c19f63153a3abb5a454bf24369b85a9f7678fed3b49a5ece6c141a398f`;
ten dependency images match package bytes. Previously measured transfer packets
remain reused unchanged, not fresh origins.

Real scratch again fell below the unchanged 24 GiB gate; initial full tooling
reported five failures/nineteen errors. Removing only 55 explicitly inspected
inactive dependency caches preserves source/feeds/manifests/historical seals/
intermediates/runtime images. With 25.188 GiB observed, all 303 tooling checks
pass (286 passed/seventeen macOS-native skips); SDK/wrapper whitespace,
frozen inventory, compiled catalogs and patch checks pass.
Payload run `40137341231` at exact
`1367a512b8abc3fb5105000ef561fb599642ee29` passed all three jobs,
194 foundations without failures/errors/skips, independent eighteen-package/
thirteen-lock replay and strict 79-scope/693-observation admission.
Input: `ad1b244e0b8c7715661fa905ac001b3c74307c910e5252820319dd7161af2a92`;
preparation:
`cfd9c8c52dee1e50978d3ed7660f077b40c0599259c6a49baee971d1a3a5d56a`.
Damaged-read run `40138438076` at exact
`4a907c5ec8b854198019b467c1069a2cdd33c00b` passed all three jobs,
195 foundations without failures/errors/skips, independent eighteen-package/
thirteen-lock replay and strict 80-scope/699-observation admission.
Input: `517a48389245ba621b1b0f5833d20c5b32cc4e041ccfba43ea2e9b1a5f4ccadf`;
preparation:
`beef2e645dafcc90515bbfa292afb3425cec4c95096e7eba63ca91237dd8c335`.
Remaining common consumers, complete fault drivers, origins and full category/
integration/profile gates remain unfinished. Tasks, reviewer markers, tracked
locks, historical seals, product contracts, architecture/ADR diagrams and
deployment examples are unchanged.

### Original read/open quarantine races

Two further original bodies now execute provider-free consumers: Local's
overlapping read/reconciliation quarantine race and both admitted-open
revalidation rows. Mechanical comparison preserves exact original assertions
and public-operation order after explicit fixture/barrier/interface/token
forwarding. Named barriers live in wrapper scope; actual installation, hold,
physical restoration and release stay at their original logical transitions.
Publication fault injection, native provider observation mapping and physical
payload I/O remain fixture-side. No provider switch, filesystem dependency,
substitute expected result or simulated durability enters the common checks.

Both missing shared methods first produced CS0117, with precise symbols
confirmed independently. The exact three-row transport first failed its named
missing-factory assertion. Independent fresh preparations each pass all
308 artifact, 65 Consumer and 89+89 metadata cases without skips; fifteen
archives reproduce exactly, canonical archive-map SHA-256
`40c0bb713c9d1499f8143d67da6812a1e3d1939593b634a9aa71fc76a2a339ae`;
ten Consumer dependency images match package bytes. Existing measured transfer
packets remain reused unchanged, not fresh origins.
All 304 tooling checks pass (287 passed/seventeen macOS-native skips), including
78 SDK transport checks; prepared SDK/wrapper whitespace, frozen inventory,
compiled catalogs and patch checks pass.

Read-race run `40139402208` at exact
`f05851abac1421518824782860e6db0ba24ab984` passed all three jobs,
196 foundations without failures/errors/skips, independent eighteen-package/
thirteen-lock replay and strict 81-scope/702-observation diagnostic admission.
Input: `303eeb1b8c696bc06d5e523e08b39947583e57237f420ba4d12b489e5b4b95fa`;
preparation:
`7ddb771f7d4e378bb8567796a12eb31f68b9f1008cd2aca463dfd85362a4bc29`.
Full drivers, origins and category/integration/profile gates remain
unfinished. Tasks, reviewer markers, tracked locks, historical seals and
product/architecture/deployment examples are unchanged.

### Original committed-detection quarantine consumer

All six original open/publication/reconciliation parameters now execute one
provider-free consumer. Mechanical whole-body comparison preserves exact
assertions/public-operation order after explicit fixture/interface/helper/token
forwarding and the fixed inherited durability variant. The independent frozen
test parameter fixes that expectation; provider-advertised capabilities,
binding callbacks and pass flags cannot select a weaker expected result.
Physical removal/restoration and publication fault mapping remain fixture-side,
not newly admitted full owned fault controls.
The old SDK first fails with the intended missing-method `CS0117`; exact
six-row transport first fails its named missing-factory assertion.

Two independent fresh preparations each pass 308 artifact, 65 Consumer and
89+89 metadata cases without skips. Fifteen archives reproduce exactly,
canonical archive-map SHA-256
`2ae90bb74588acae39078dfb97f206b5f640d254d91179c4fa29caa786b2a591`;
ten Consumer dependency images match package bytes. Full tooling initially
failed below the unchanged 24 GiB scratch gate. Ten identity-verified inactive
dependency caches were removed, preserving sources, feeds, manifests,
intermediates, runtime images and historical seals; 24.140 GiB was restored.
The rerun passes 305 checks (288 passed/seventeen macOS-native skips), including
79 SDK checks; prepared formatting, frozen inventory, catalogs and patch checks
pass. Committed-detection run `40140436330` at exact
`e08904228390c68f468739148ca05e39eac3542b` passed all three jobs,
197 foundations without failures/errors/skips, independent eighteen-package/
thirteen-lock replay and strict 82-scope/708-observation diagnostic admission.
Input: `1a3c4f2f2d11f54ad715dd4ae58dfcb3ea92282b03ca017a473804377c398d0e`;
preparation:
`7bfbecaf99c2da8314713f14117b2cc9d340d0af417bb59d54c9fe29a6d823e7`.
This does not establish omitted durable checks. Full gates remain
unfinished. Tasks, reviewer markers, tracked locks, historical seals and
product/architecture/deployment examples remain unchanged.

### Restored transitive Local quarantine ownership

Review found that corrupt-existing, damaged-read and committed-detection
extraction had replaced the complete quarantine helper with only its immediate
common checks, omitting Local's durable stop/reopen check. Earlier normalized-
helper parity claims did not establish that check; historical diagnostic
receipts prove only the assertions actually executed, not omitted checks.
The complete original helper is now provider-free common code. A typed context
supplies the original public lifetime/identity/authority and fixture-only fresh
store factory for the fixed Local variant; Object has no durable-restart claim.
Every stop/factory/initialize/corrupt-read/finally-stop/original-reinitialize
operation and enclosing source/duplicate/guard lifetime is preserved.
No callback supplies assertions or expected results.
Whole-helper comparison against `d7ef7cc^` matches exactly after explicit
interface/factory/token forwarding. A frozen normalized-body and per-wrapper
owner guard now protect that transitive obligation.

Three real reopened-store mutation pairs require actual `CorruptContent`
denial before substituting `NotFound`, fail the unchanged common equality
assertion, and pass with genuine stores. Initial compilation first fails with
missing-context `CS0246`; exact nine-row transport first fails its named
missing-factory assertion. Fresh preparation/replay pass 311 artifact,
65 Consumer and 89+89 metadata cases without skips; fifteen archives reproduce,
canonical map SHA-256
`9f08a15f5fd77ecffa4aaad4e5c05d6e333ba282e3ce1b23d5e606a67d593fb3`;
ten Consumer dependency images match package bytes. All 307 tooling checks pass
(290 passed/seventeen macOS-native skips), including 81 SDK checks; prepared
formatting, frozen inventory, catalogs and patch checks pass. The next request
for 199 foundations/83 scopes/717 observations failed closed:
`40141545447` at exact `be3b3f2d5ed49f7a0d7a742f9b9b105ec6f7e2df` passed the
ownership and fresh-lock jobs but returned `UnknownDiagnostic` in the new
quarantine scope. It is not admitted. Actual method-level VSTest discovery
reproduced fifteen rows against its nine-row Local-only declaration.
Corrected transport includes every selected frozen provider parameter plus
all three mutation rows, and prelaunch admission rejects partial method
expansion even from a regressed canonical factory. Logger admission is not
relaxed and Object's logical rows establish no durable restart. Full drivers,
origins and category/integration/profile gates remain unfinished; tasks,
reviewer markers, tracked locks, historical seals and product/architecture/
deployment examples remain unchanged.

### Remaining original evidence-validation consumers

All nine remaining persistence/corruption/access parameters now execute
provider-free consumers with exact whole-body assertion/public-operation
order and source/guard lifetime parity after explicit fixture/interface/
helper/token forwarding. The complete transitive quarantine helper and both
new caller owners remain guarded. Physical path capture, permissions,
removal/restoration and actual native readiness observation remain legacy
fixture-side controls, not complete owned fault-driver admission. Original
pre-try Unix rejection stays in order; the permission setter also keeps a
local platform guard for analyzer correctness across callback boundaries.
All three missing methods first fail with their exact intended `CS0117`;
nine-row transport first fails its named missing-factory assertion.

Fresh preparation/replay pass 311 artifact, 65 Consumer and 89+89 metadata
cases without skips; fifteen archives reproduce exactly, canonical map SHA-256
`89efb47ca07de4de7e3d6e7d0b72f2dbd00efe580428865729ca24dc66d158c8`;
ten Consumer dependency images match package bytes. All 308 tooling checks pass
(291 passed/seventeen macOS-native skips), including 82 SDK checks; prepared
formatting, frozen inventory, catalogs and patch checks pass. The newest
request is 200 foundations and 84 scopes/732 observations, pending. Reopen
arguments are no longer defaulted: callers explicitly select actual durable
context or logical-only scope. Final tooling initially failed below the
unchanged 24 GiB gate; 69 identity-verified inactive dependency caches were
removed while preserving sources, feeds, manifests, intermediates, runtime
images and historical seals. Full tooling passed after 24.248 GiB was observed;
after two further completed caches were removed, 29.663 GiB was observed.
Shared-host capacity changes are not attributed solely to that cleanup.
Tasks, reviewer markers, tracked locks, historical seals and product/
architecture/deployment examples remain unchanged. Full bindings, origins and
category/integration/profile acceptance remain unfinished.

### Native confirmation of complete quarantine scope and validation

[40143552793](https://github.com/Stonefly-Labs/Hoard/actions/runs/40143552793)
at exact head `c1d2a6b4f40d5f2d5110bfe433619948292c90d1` passed all three jobs,
200 foundations without failures/errors/skips, and all 84 scopes/732 exact
discoveries/executions, including fifteen quarantine-reopen rows and nine
validation rows. The strict observer admitted every prerequisite recovery,
transfer, ownership/native-containment and eighteen-package/thirteen-lock
fresh-replay chain. The failed earlier `40141545447` remains unadmitted.
Input: `c7fea35cc7c3e63d863e587a5dc9482fe9d066a86bddb9acb2a37b0be189fa02`.
Preparation: `19c50dc4dd12c6a62739c36308b20de4b5784040dc5b3497ca2d48820c258770`.
Free scratch: 91,722,289,152 bytes. This is non-qualifying diagnostic evidence,
not full binding/category/profile admission.

### Shared original recovery-page and generation checks

Six original `ArtifactRecoveryTests` methods now forward all twelve Local/Object
parameters (eight frozen category witnesses and four additional existing
cases) to provider-free `ArtifactRecoveryAssertions`: sequential recovery,
changed inventory, ownerless expiry, finalized noncommit, expiry/restage
generation fencing and bounded non-authoritative recovery pages. Complete-body
comparison against the preceding committed wrappers preserves every assertion,
operation order and borrowed-stream lifetime after explicit public-interface,
clock, shared-helper and cancellation forwarding. The original fixed variant
selects Snapshot versus Incomplete enumeration, not advertised capabilities.
Driver construction, limits, clock and disposal remain in the original wrapper.
The transitive publication/read helpers already forward to the identical SDK
implementations; the borrowed source is the SDK implementation's legacy subclass.
All six wrappers first failed with the intended missing-class `CS0103`, and
the twelve-row transport first failed its missing-factory assertion. Exact
transport rejects omitted/foreign parameters and renamed scopes before launch.
Actual prepared-assembly method-level VSTest discovery matches all twelve
declared identities. Full tooling passes 309 checks (292 passed/seventeen
macOS-native skips), including 83 SDK checks; prepared SDK/wrapper formatting,
frozen inventory, catalogs and patch checks pass.
Two fresh preparations pass 311 artifact, 65 Consumer and 89+89 metadata cases
without skips. All fifteen actual archive digests reproduce exactly, canonical
full-filename map SHA-256
`1a547dfbe4ecb1e2bf1f1a10b3c60b5517b7b41a62e5cc40dcc91199eb8ad243`;
ten Consumer dependency images match actual package bytes in each preparation.
Transfer packets are reused unchanged, not new origins.
The expanded native request is 201 foundations and 85 scopes/744 observations,
pending, not full recovery/fault-driver/category/profile qualification.
Product, architecture and deployment examples are unaffected by this test-only
extraction; tasks, reviewer markers, locks and historical seals are unchanged.

### Native confirmation of shared recovery pages and generations

[40144435943](https://github.com/Stonefly-Labs/Hoard/actions/runs/40144435943)
at exact head `ffec99af90689b61938b5e66cc8e0df64d291c44` passed all three jobs,
201 foundations without failures/errors/skips and 85 scopes/744 exact
discoveries/executions, including all twelve new recovery rows. Every actual
prerequisite recovery/transfer/ownership/native-containment and eighteen-package/
thirteen-lock replay chain passed strict admission. Input:
`1661a1db69757112fac7ed84cb1609420164d098ea6eb85a1c52ea41b5879985`.
Preparation: `984c234bb9ef59234094386ea64dd64fdb56dfbc41b6f237c933fa20a2de0c04`.
Free scratch: 91,717,603,328 bytes, not full category/profile qualification.

### Shared admitted-history and generation races

Five more original recovery methods now share provider-free
`SettledReceiptReplacementAsync`, `AdmittedDeleteHistoryAsync`,
`AdmittedReconciliationHistoryAsync`, `LateCleanupGenerationAsync` and
`ProgressingCommitAsync`. Ten original parameters comprise six frozen category
witnesses and four additional existing cases, without modifying the baseline.
Complete-body comparison preserves all assertions, operation order, managed
source/barrier nesting and public read/receipt corroboration after explicit
interface/clock/physical-control/helper/token forwarding.

The SDK owns the original managed `ArtifactConformanceBarrier` body, not a
replacement with looser timing: entry/hold/settlement budgets remain 10/20/10
seconds, with a frozen complete-body regression guard. The legacy alias
inherits that implementation. Initial ordinary compilation correctly exposed
an SDK reference if the alias stayed in the always-compiled harness; moving
only the alias into the existing package-only `Cases/` boundary preserves
ordinary-project references unchanged. Fresh package-only compilation then
confirmed the intended missing shared-barrier `CS0234`; exact transport first
failed its missing-factory assertion. Physical registration/removal and lost
acknowledgment injection remain fixture-side; no provider switch enters SDK
assertions. Actual prepared-assembly discovery matches all ten independently
declared identities. All 311 tooling checks pass (294 passed/seventeen
macOS-native skips), including 85 SDK checks; prepared SDK/wrapper/harness/alias
formatting, frozen inventory, catalogs and patch checks pass.
Fresh preparation/replay passes 311 artifact, 65 Consumer and 89+89 metadata
cases without skips. All fifteen actual archive digests reproduce exactly,
canonical full-filename map SHA-256
`6dfb8daba9d51a1febd6266820be21464adc295942db22657507804cba5cd75a`;
ten actual Consumer dependency images match package bytes in each preparation.
Transfer packets remain reused unchanged, not new origins.
Run `40145322908` at `9d19bd1` passed all three jobs, 203 foundations and
86 scopes/754 observations, not full recovery/fault-driver/category/profile admission.
Tasks, reviewer markers, tracked locks, historical seals and product/
architecture/deployment examples are unaffected.

### Remaining object stop and actual Local reopen checks

All three remaining original recovery bodies now forward provider-free
`RetainedObjectStopAsync`, `CommittedDecisionRollbackAsync` and
`DurableReceiptReleaseAsync`. One frozen object-stop witness and two additional
existing Local facts preserve independent implementations, 105 retired
incarnations, rollback readback, durable receipt reconciliation, stop/retry,
exact owner/cleanup and every source/current/fresh-store lifetime.
Complete-body comparison against the preceding commit passes after explicit
public-interface, clock, physical-control, real factory and token forwarding.
The source in the release/reopen case remains borrowed through both
lifetimes; it is not returned after being disposed by a smaller consumer.

Permissions, directory snapshots, record-write registration, real fresh Local
construction and root-cleanup authorization remain fixture-side. The common
consumer determines the actual stop result, then the fixture setter and getter
reflect cleanup permission; callbacks contain no assertions or expected outcomes.
Object gains no durable-reopen claim. All three missing consumers first fail
with exact intended `CS0117`; exact three-row transport first fails its
missing-factory assertion. Full tooling passes 312 checks (295 passed/seventeen
macOS-native skips), including 86 SDK checks; prepared SDK/wrapper formatting,
frozen inventory, catalogs and patch checks pass. Actual prepared-assembly
discovery matches the exact three independently declared facts.
Fresh preparation/replay passes 311 artifact, 65 Consumer and 89+89 metadata
cases without skips; all fifteen actual archives reproduce exactly, canonical
full-filename map SHA-256
`61e01e8345fa09ef873567e1e3451af5aef9f83a1f814566318d782116f6e935`.
Ten actual Consumer dependency images match package bytes in each preparation;
transfer packets remain reused unchanged, not new origins.
Run `40146117625` at `994f9fb` passed all three jobs, 204 foundations and
87 scopes/757 observations. Original recovery-body extraction is complete, not T027,
full bindings, origins or category/profile acceptance. Tasks, reviewer markers,
tracked locks, historical seals and product/architecture/deployment examples
are unaffected.

### Original admission checks and native managed-barrier receipt

Native run `40145322908` binds exact
`9d19bd1119a821e85e81019b9d393d5bd19e2f7d`: all three jobs, 203 foundations
without failures/errors/skips, 86 scopes/754 exact discoveries/executions and
every prerequisite recovery/transfer/ownership/native-containment and
eighteen-package/thirteen-lock replay chain pass. Input:
`109cc8ddc69a9b07d0032104e9f2ca7201a64492f1213816a20a6f93fd5e3a7d`;
preparation:
`d49f56e11cebbe844a9eff4a076db30dc5da3c7b8438d632144a04db1ca789bc`;
free scratch 91,716,227,072 bytes. This is diagnostic evidence, not qualification.

Six original admission methods now forward all eleven identities (four frozen
witnesses and seven additional existing cases) to provider-free
`ArtifactAdmissionAssertions`. Complete-body comparison preserves every original
assertion/order, initialization TCS hold/release, 100/20-millisecond deadlines,
two-second waits, exclusive create, missing/foreign/corrupt-root non-reset,
fixed original Local/Object reopen expectations and outside-sentinel/child
checks. Physical construction, preconstruction observer registration, authority,
manifest/sentinel I/O, symlink try/finally and root cleanup authorization remain
fixture-side. Native concurrency and cross-process ownership tests, complete
bounded child-output/PID/exit/retained-root helper and actual root disposal are
unchanged. Factories/callbacks supply no asserted outcome or expected result.

The absent class first fails intended `CS0103`; exact eleven-row transport
first fails its missing-factory assertion. Actual prepared-assembly discovery
matches all eleven declared identities. Full tooling passes 313 checks
(296 passed/seventeen macOS-native skips), including 87 SDK checks; prepared
SDK/wrapper formatting, frozen inventory, catalogs and patch checks pass.
Fresh preparation/replay passes 311 artifact, 65 Consumer and 89+89 metadata
cases without skips; all fifteen actual archive hashes reproduce exactly,
canonical full-filename map SHA-256
`e9b04122b8c1012d0b7e8af1650eec2bd9f419a1568d1bdf3f99912192182213`.
Ten actual dependency images match package bytes per preparation; transfer
packets remain reused unchanged, not new origins. Its native request
`40146850203` was canceled before jobs and is not admitted; the latest expanded
request retains all eleven identities. This is not complete
bindings/origins/category/profile acceptance. Tasks, reviewer markers, locks,
historical seals and product/architecture/deployment examples remain unaffected.

### Remaining deletion settlement and reference checks

Both remaining original deletion methods now forward all four frozen provider
parameters to `ArtifactDeletionAssertions.PendingReclamationAsync` and
`LiveReferencesAsync`. Complete-body comparison preserves original assertions,
operation order, borrowed-source lifetime and publication/read helpers after
explicit interface/control/token forwarding. Common checks retain uncertain
deletion, hidden content, actual pending/reclaimed cleanup count/bytes, unchanged
receipt identity/stamp/outcome, idempotent retry, both live/unavailable reference
denials, intact readback and eventual authorized removal.
Actual lost-ack registration and reference count/availability remain fixture-side.
No callback supplies an asserted outcome or expected result.

Missing consumers first fail intended `CS0117`; the exact four-row scope first
fails its missing-factory assertion. Actual prepared-assembly discovery matches
all four frozen parameters. Full tooling passes 314 checks (297 passed/seventeen
macOS-native skips), including 88 SDK checks; prepared SDK/wrapper formatting,
frozen inventory, catalogs and patch checks pass. Fresh preparation/replay
passes 311 artifact, 65 Consumer and 89+89 metadata cases without skips;
all fifteen actual archives reproduce exactly, canonical full-filename map
SHA-256 `7f8df462bdb0b2fdf8c93cdd438edbf099eed2443154cf7cfc24564061227bdb`.
Ten actual dependency images match package bytes per preparation; transfer
packets remain reused unchanged, not new origins. Original deletion-body
extraction is complete, not T027/T030 or full bindings/origins/category/profile
acceptance. Native run `40147381011` binds exact head
`992b4a5c43efe4057879ede6bc232903225e1f94`: all three jobs, 206 foundations
without failures/errors/skips and 89 scopes/772 exact discoveries/executions,
including all eleven admission identities and every actual prerequisite chain.
Input: `474ce5c8a63f3d2bd169d503a92713d0e911e04a1235a76fc7932eb2c5912926`;
preparation: `49b91dc028b3c3d510ce346751a803cd4c48da53e0659849c61c3cfc609bd135`;
free scratch 91,721,879,552 bytes. This remains diagnostic evidence.
Tasks, reviewer markers, locks, historical seals and product/
architecture/deployment examples are unaffected.

### Distinct direct-verification control and adapter architecture constraints

Preliminary architecture review identified that publication selection cannot
stand in for direct verification: Object duplicates do not invoke
`pointer.selected`, and Local's digest gate also prevents equating a held
selection with independent readable acknowledgment. The additive
`DirectVerification` observation now maps Local's optional `publish.direct`
before its original new/duplicate direct validation and Object's existing
`object.direct`. Local's complete implementation is unchanged apart from those
two observations; no provider mechanism or production reference edge is shared.
Four common rows hold actual publication before acknowledgment, then join
completion/worker settlement and assert correct outcome, same-incarnation
duplicate reuse, borrowed-source ownership and actual public bytes. No held-gate
independent-readability guarantee is invented.

The missing shared method first fails intended `CS0117`; the exact four-row
scope first fails its missing-factory regression. Actual prepared-assembly
discovery matches all four parameters. Full tooling passes 315 checks (298 passed/
seventeen macOS-native skips), including 89 SDK checks; formatting, frozen
inventory, catalogs and patch checks pass. Fresh preparation/replay passes
311 artifact, 69 Consumer and 89+89 metadata cases without skips; fifteen actual
archives reproduce exactly, canonical full-filename map SHA-256
`298788d00993d47090cc2c433bd176311704767e623e3bdc788fba7943b57474`.
Ten dependency images match package bytes per preparation; transfer packets
remain reused unchanged, not new origins. Native run `40148199370` binds exact
head `6d1f73bf1f58cc46f68c1102a22a6289be07f717`: all three jobs,
207 foundations without failures/errors/skips and 90 scopes/776 exact
discoveries/executions, including all four direct-verification rows and every
actual prerequisite proof. Input:
`422b243a0f9e2f7eb89e140c2b9f4246b357bb9b279e4ba7e8d4b0c118e75bef`;
preparation: `444b482499b205b3759d11413638d0ba03d9df45595e378a5cf29a5f482badba`;
free scratch 91,721,908,224 bytes. This remains diagnostic, not full qualification.

The remaining full-adapter design must keep intentional typed fault injection
separate from observer failures that poison final settlement, target payload
damage by exact stamp, preserve actual borrowed source/sink work and classify
synchronous provider-boundary blocking truthfully rather than claiming a stalled
filesystem syscall. Controls must not be released implicitly before lifetime
settlement. Complete fault-driver/origin/category/profile admission and final
T081 remain open; the preliminary review is not a final architecture pass.
Tasks, reviewer markers, locks, historical seals and product/architecture/
deployment examples are unaffected.

### Scoped capacity injection without observer-failure suppression

The owned partial artifact projection now exposes a counted scoped capacity
injection at each provider's genuine post-write staging-prefix boundary.
Registration constructs its own fixed ENOSPC-shaped `IOException`; only that
exact instance avoids ordinary observer-failure recording while propagating to
the actual provider classifier/cleanup. Other exceptions, including the same
HRESULT, retain permanent fail-closed settlement. No queue reset, replacement
settlement task, store proxy, physical disk-exhaustion claim or full mandatory
fault-driver declaration is introduced.

Four package-only parameters run against both actual providers. Common checks
require repeated classified failure, source progress/borrowed ownership, exact
not-committed reconciliation, a fresh scope surviving stale disposal and actual
publication/readback after repair. A one-ticket staging limit makes capacity
restoration necessary for each following reservation. Ordinary same-code observer
errors must remain the exact exception in the genuinely faulted final task;
the injected counterparts require genuine successful final settlement.

The missing common method first fails actual `CS0117`; the missing exact
four-row runtime scope first fails its factory regression. Actual prepared
discovery matches all four identities. Tooling passes 316 checks (299 passed/
seventeen macOS-native skips), including 90 SDK checks. The native foundation
selector observes 208 checks locally with zero failures/errors but seventeen
native skips, so correctly returns `Incomplete`/`EvidenceIncomplete`, not native
acceptance. Fresh preparations pass 311 artifact, 73 Consumer and 89+89 metadata
cases without skips. Fifteen actual archives reproduce the full-filename map
SHA-256 `2a871fdf07934fae09154e259a523d244fa937b2199c05b2dd900c1641ae6992`;
ten dependency images match their archive bytes per preparation. Transfer packets
remain reused unchanged, not fresh origins. Native run `40148998281` binds exact
head `53b14333b5f9d2f175627c89801cac218f72c14c`: all three jobs,
208 foundations without failures/errors/skips and 91 scopes/780 exact
discoveries/executions, including all four capacity/ordinary-observer rows and
every actual prerequisite proof. Input:
`82b2c9e0ee5a59a944cee386943a3123d8dabeaa9b142a6e6182fb9caa42a2ba`;
preparation: `0fe7ad5982183dc9e6753d78fe562040d0428438d8bbef21cf7739d6fe96c2f6`;
free scratch 91,721,900,032 bytes. This remains diagnostic, not full qualification.

T027..T030, complete mandatory fault drivers/origins, category/profile acceptance
and final T081 remain open. Tasks, reviewer markers, tracked locks, historical
seals and product/architecture/deployment examples remain unaffected.

### Scoped actual unclaimed-result cleanup failure and retry ownership

The partial artifact projection now injects a counted, exact-instance
`IOException` at each independent provider's existing undelivered-result reclaim
seam. The provider indexes actual cleanup before that seam and removes its index
only after successful cleanup. This is not a surrogate for physical prefix or
unselected-object permission failures; those original checks remain unchanged.

Four common parameters hold real reservation/read-open completion, cancel
delivery, release and join the actual worker, and require one genuine failed
reclaim, fenced readiness/admission, failed stop with retained live ownership and
a second genuine failed reclaim. After scope removal, the real stop retry must
reclaim actual work, settle workers and produce genuine successful final
settlement. The original borrowed source outlives that work. No provider
implementation, failure queue, settlement promise or root authorization changes.

The absent consumer first fails intended `CS0117`; the exact four-row runtime
scope first fails its factory regression. Actual prepared-assembly discovery
matches all four identities. Tooling passes 317 checks (300 passed/seventeen
macOS-native skips), including 91 SDK checks. SDK/both adapter/Consumer formatting,
frozen inventory, catalogs and patch checks pass. Fresh preparation/replay passes
311 artifact, 77 Consumer and 89+89 metadata cases without skips. Fifteen actual
archives reproduce canonical full-filename map SHA-256
`0f1c8ce1efd3893ba836768053303d17c09ec5fc1fcd7e42cf9be0689dccdcdc`;
ten actual dependency images match their package bytes per preparation.
Transfer packets remain reused unchanged, not new origins. The next native
request passed as run `40149692533` at exact head
`1acdeb0b777e31929e7f70bccdfe89a2dc598bbd`: all three jobs,
209 foundations without failures/errors/skips, 92 scopes/784 exact discoveries/
executions and every actual prerequisite. Input:
`b4b5a27b071937cd524f6d1c2a97fab1049b991a6d049db0801849a8a90dd6cf`;
preparation:
`a11e22af6fefffdb261a13df75e1d305e9ec565005cc331c2e42b521d8b42e4b`;
free scratch 91,721,879,552 bytes.
Full fault-driver/origin/category/profile qualification and final T081 remain
open; tasks, reviewer markers, tracked locks, historical seals and product/
architecture/deployment examples remain unaffected.

### Genuine synchronous storage holds and retained authority

The partial artifact projection now maps an owned synchronous hold to Local's
existing record-write callback and Object's existing physical-delete callback,
without changing either provider mechanism. Deletion is reserved before arming.
The first actual package run correctly failed both new rows because the default
partial session has no reference-query authority and denies deletion before
native entry. Explicit available-zero reference authority fixes setup without
weakening that guard; an early public return before entry now fails immediately.
This is controlled synchronous fixture blocking, not a stalled filesystem syscall.

Both common parameters require deadline/uncertain caller return with retained
ownership, actual pending workers, admission/readiness fencing, real authority
exclusion and failed retained stop while held. Explicit release precedes actual
worker settlement and successful stop; the borrowed source outlives the work.
Scope disposal is identity-checked, task-stable, and joins genuine workers after
disarming. Stale disposal cannot remove a replacement. Ownership removes remaining
controls only after stop/worker settlement. The fifteen-second watchdog records
unexpected expiry against final settlement rather than fabricating cleanup.

The absent shared consumer first fails intended `CS0117`; the exact two-row scope
first fails its factory regression. Actual prepared-assembly discovery matches
both identities. Tooling passes 318 checks (301 passed/seventeen macOS-native
skips), including 92 SDK checks. SDK/both adapter/Consumer formatting, frozen
inventory, catalogs and patch checks pass. Fresh preparation/replay passes
311 artifact, 79 Consumer and 89+89 metadata cases without skips; fifteen actual
archives reproduce canonical full-filename map SHA-256
`bed443dfceb7b1526fe8340f1fa0771856e2416233f4e6372c191085cee6bdcf`.
Ten runtime dependency images match package bytes per preparation; transfer
packets remain reused unchanged, not fresh origins.

Bounded custom architecture review found no actionable ownership/concurrency/
boundary bug; it is a control prerequisite review, not final T081 or complete
category admission. Original cross-process native containment remains mandatory
and separate. Native run `40150871211` at exact head
`f68812e9e2d9f48ced1be13d16554b67c118129c` passed all three jobs,
210 foundations without failures/errors/skips, 93 scopes/786 exact discoveries/
executions and every actual prerequisite. Input:
`8d841ae64a58df3ad5b548c9c1c1cfa4d0147e08500a3a068c057db2eed9ee13`;
preparation:
`965ec29517b5fc9fa3a3ea2cf140f12b65ac57d91751d576e2b856eecfc777eb`;
free scratch 91,716,579,328 bytes. Full mandatory fault-driver/origin/category/profile
qualification, tasks and reviewer markers remain open. Tracked locks, historical
seals and product/architecture/deployment examples remain unaffected.

### Full artifact factories and executable mandatory controls

`LocalBinding` and `ObjectSemanticsBinding` now implement the full typed
artifact binding/session boundary over their actual independent owned stores,
validator/maintenance/lifetime and shared authority. No store proxy or component
identity substitution is introduced. All ten declared controls execute real work:
publication-selected/direct-verification/receipt/verified-generation gates,
exact-stamp physical payload damage, scoped capacity/indexed cleanup injection,
synchronous fixture holds and borrowed non-cooperative source/sink streams.
Generation's common consumer performs real expired-owner maintenance cleanup
before re-staging; the first run failed both providers without that required
precondition, and no guard was weakened. Old owner/cleanup rejection, increasing
generation and readback corroborate actual replacement.

The full damage API now requires an exact stamp. Its common consumer targets the
first of two artifacts, rejects a foreign incarnation without entry/damage, proves
the second remains intact and observes corruption/quarantine through public I/O.
Borrowed stream reads/writes are actual pending I/O ignoring operation cancellation
until explicit release; actual provider public return/retained cleanup and worker
settlement are not manufactured. Streams are disposed by their caller-side factory
only after actual close/reopen settlement. Generic entry waits observe genuine
registrations and cancellation does not remove the armed fault. Reopen captures
actual components/parent lineage, preserves Local identity/publication, gives the
simulation an empty fresh epoch and rejects stale controls.

The absent consumers/factories first failed actual compilation. Bounded custom
architecture review found a real cross-control deadlock: native release joined
all workers under the shared registry semaphore and prevented release of a held
publication. Both new concurrent-release regressions first failed. In-progress
release tasks are now published under that semaphore but awaited outside it,
preserving independent release and preventing premature rearm. Native settlement
is observed before stable scope disposal, allowing failed observation to retry
without permanently caching a failed scope-disposal task. Both regressions and
subsequent native rearming pass. This review is not final T081.

Actual prepared discovery equals all 24 independent expected identities. Fresh
preparation/replay pass 311 artifact, 103 Consumer and 89+89 metadata cases without
skips. Fifteen actual archives reproduce full-filename map SHA-256
`2068add411613f471e6bfefd14cabb609fba189354c9edeec4f2320269dd07bf`;
ten runtime dependency DLLs match archive bytes per preparation. Tooling passes
319 checks (302 passed/seventeen macOS-native skips), including 93 SDK checks;
20 typed binding/origin unit cases pass after restoring missing dependencies.
SDK/both adapter/Consumer formatting, frozen inventory/catalogs and patch checks
pass. Transfer packets are reused unchanged, not new origins. The next native
run `40153251707` at `f73a55a530b887eb9db70d8924ce7f7921a45028` passed all
three jobs, 211 foundations and 94 scopes/810 exact discoveries/executions with
every prerequisite. Parent-origin/
profile ingestion, remaining category parity/integrations, full qualification and
final T081 remain open. Tasks/reviewer markers, tracked locks, historical seals and
production architecture/deployment examples/diagrams remain unchanged.
Runtime caches remain independent. The parent rechecks both admitted provider
archives before passing only their hashes through fixed private runsettings
variables; fixture construction no longer assumes candidate cache availability.
Missing/foreign/malformed or absent-archive inputs fail before launch.

### Full artifact diagnostic origin transport and admission

All 24 full-binding Consumer rows now emit actual observed-session packets using
the controller's required run ID and the fixed `full-artifact-binding` case ID.
There are 24 creates and two genuine reopens; reopened packets follow their actual
parents. Independently constructed package declarations match the SDK's exact
serialized bytes, including capability/fault order. Parent ingestion pins each
of eight roles to its actual adapter/provider runtime image and respective package,
requires one origin per ordinary row/two per reopen and matches the independently
selected binding descriptor. Existing runtime, component identity and reopen
lineage checks are unchanged. The safe logger manifest must admit all four
binding/provider images as well as the Consumer; missing input images fail before
launch rather than weakening the logger's actual-image checks.

Fresh preparation/replay pass 311 artifact, 103 Consumer and 89+89 metadata cases;
the fifteen-package map remains
`2068add411613f471e6bfefd14cabb609fba189354c9edeec4f2320269dd07bf`.
Ten runtime dependencies match archive bytes in each preparation. Bounded actual
VSTest output observation, kept only in memory, matches all 24 discovered identities,
26 origins and 208 actual role/image/archive correspondences with an independent
empty runtime cache. This is not native parent acceptance. Tooling passes 320
checks (303 passed/seventeen macOS-native skips), including 94 SDK checks.
Consumer formatting, frozen inventory/catalogs and patch checks pass. The
origin-enabled native successor passed as run `40154183825` at
`d1fd43d9abcbe1bdeb9e393d28d7aad345f9c054`: all three jobs, 212 foundations
without failures/errors/skips and 94 scopes/810 exact discoveries/executions
with every prerequisite, including actual artifact origin admission.
Other origin/profile imports, category parity/
integrations, complete qualification and final T081 remain unfinished.
Tasks/reviewer markers, tracked locks and historical seals remain untouched;
test-only provenance changes do not alter product/deployment examples or diagrams.

### Actual metadata factory origins through unchanged common work

Six additional package-only rows run existing capacity, writer-budget and
publication-protection consumers through observed Memory/SQLite sessions. There
is no new provider mechanism or result substitution. Independent declarations
preserve exact metadata capability/fault serialization order and provider archive
hashes. All six actual component roles are assigned independently to their adapter/
provider runtime images and archives. The four real component images enter the
safe logger manifest; exact per-witness origin count and descriptor checks apply,
with existing SQLite environment admission before launch. The existing
settlement-aware test allocator is reused without claiming physical release.

The absent metadata origin map first failed its intended regression. Fresh
preparation/replay pass 311 artifact, 109 Consumer and 89+89 metadata cases;
all fifteen archives reproduce the unchanged map above, and ten actual runtime
dependencies match archive bytes per preparation. Bounded actual VSTest observation
with a separate empty runtime cache proves exact six-row discovery, six metadata
origins and 36 role/image/archive correspondences. Artifact observation still
matches 24 rows, 26 origins and 208 correspondences. These local checks do not
establish native parent acceptance. Tooling passes 322 checks (305 passed/seventeen
macOS-native skips), including 96 SDK checks; Consumer formatting, frozen
inventory/catalogs and patch checks pass. The next native request is 214
foundations and 95 scopes/816 observations; it passed as run `40155045988`
at exact head `90341537c34772face78946f2bc294dd1ee6f8b0`: all three jobs,
no foundation failures/errors/skips and every actual prerequisite.

The earlier admitted full-control run binds input
`7b14f67d94d2800d7b4bbba02b4f018d3409bb6920eab160371b05a2ac2ca6be`,
preparation `13c78f0aea8139bc54e5052cc6a49b035bc03d15fa3ea18205104750ac9ce11c`
and 91,716,939,776 free scratch bytes; it predates both origin increments.
Metadata reopen attribution, other origin/profile imports, remaining parity/
integrations, full qualification and final T081 remain open. Task/reviewer markers,
tracked locks and historical seals are unchanged. Test-only provenance wiring does
not alter production/deployment examples or architecture diagrams.

### Actual metadata compatible-reopen attribution

A provider-free `MetadataSchemaAssertions.CompatibleReopenAsync` now seeds and
publicly reads grouped registry/package state, reopens the genuine session,
requires fresh store/fault instances and the same authority/epoch, disposes the
stale session, verifies byte-exact public readback and rejects stale fault arming.
An unreturned child is disposed on failed assertions; successful handoff leaves
final disposal with its caller. Memory uses its actual closed logical image,
not durable restart. Two additional observed factory rows capture their genuine
parent/child origins; strict ingestion requires two origins for those exact rows.

The absent reopen inventory first failed its intended regression. An incidental
immutable-array/span compiler error was corrected before runtime validation.
Fresh preparation/replay pass 311 artifact, 111 Consumer and 89+89 metadata cases.
Eight metadata rows produce ten origins, eight creates/two reopens and 60 actual
role/image/archive correspondences with separate empty runtime caches. All
fifteen archives reproduce full-filename map SHA-256
`f351b872a7a4c111fe1b1321c7a7955e2b82c5763be59c00eab3ecd69b28789c`;
ten runtime dependency images match archive bytes per preparation. Tooling passes
322 checks (305 passed/seventeen macOS-native skips), including 96 SDK checks;
SDK/Consumer formatting, frozen safeguards and patch checks pass. The expanded
native request passed as run `40155922560` at
`4548183b5e6907be94f3fe52393a729c16299d2d`: all three jobs,
214 foundations without failures/errors/skips and 95 scopes/818 exact
discoveries/executions with every prerequisite.
All 20 typed binding/origin SDK contract tests also pass.

Artifact-origin admission binds input
`df4c59c2f1ea075c8b14de7db16bdecdfd6c540698f739210fbd22abc276279b`,
preparation `45e3cc6040d45061ca26d51bae4bba0adf9fc8139fc1a9f942662b5584288640`
and 91,721,523,200 free scratch bytes. Metadata-origin admission binds input
`fc41f51c1091f64152f3d4c64b4ba0bf209c996f8fd4591e4b9649687ae8dac1`,
preparation `5b4f9f3b1438fa5910ba8c8770c66b6e216f366e677e2fe68ba0ed99570ded51`
and 91,716,923,392 free scratch bytes. Neither verifies the new reopen increment.
Complete category/profile origin imports, remaining parity/integrations, full
qualification and final T081 remain unfinished. Tasks/reviewer markers, historical
seals and tracked locks are unchanged; production/deployment examples and
architecture diagrams are unaffected by test-only common assertions/provenance.

### Actual metadata entity, atomicity and lease imports

Twenty additional observed rows now call unchanged common consumers through the
independent Memory/SQLite factories: entity/relationship roundtrip, final-graph
deletion/disabled retention, independent candidate snapshots, faulted atomic
candidates, grouped reads, lease-generation overflow, owner/generation/revision
fencing and renew/release/guard decision-time expiry. The actual injected clock
and real fault-driver hooks drive observations; no copied expectation bodies,
synthetic success hooks or common assertion edits are introduced.

The exact-scope regression first failed because the new identities were absent.
Fresh exclusive preparation/replay pass 311 artifact, 131 Consumer and
89+89 metadata cases without failures/skips. All fifteen normalized archives
remain byte-identical with map SHA-256
`f351b872a7a4c111fe1b1321c7a7955e2b82c5763be59c00eab3ecd69b28789c`.
Actual bounded output observation with a separate empty runtime cache confirms
28 exact metadata rows, 30 genuine origins, 28 creates/two reopens and
180 actual role/image/archive correspondences. Tooling passes 322 checks
(305 passed/seventeen macOS-native skips), including 96 SDK checks; Consumer
formatting and patch checks pass. The next native request is 214 foundations
and 95 scopes/838 observations; it passed as run `40156840261` at
`2beff5414c948814599a0f7f20426028579adb33`: all three jobs,
214 foundations without failures/errors/skips and every prerequisite.

Standalone metadata publication/reference checks do not establish the actual
artifact evidence bridge or shared artifact-authority integration. Complete
category/profile imports, integrations and final T081 remain unfinished.
Frozen wrappers/assertions, historical seals, locks, tasks and reviewer markers
are unchanged; production/deployment examples and architecture diagrams are
unaffected by these test-only consumer imports.

### Actual metadata identity, references and reconciliation imports

Thirty additional observed rows now invoke unchanged canonical text, registry/
authorization partitioning, reference replacement/metadata revision ABA/
telemetry rollback, competing creates/revisions and reconciliation contention,
I/O uncertainty, lost acknowledgment, distinct contributions and corrupt-receipt
consumers. Both malformed-schema layouts start genuinely unprepared, retaining
the original empty/partial schema expectations rather than corrupting an
already-admitted layout.

The exact-scope regression first rejected the missing identities. Fresh exclusive
preparation and independent replay pass 311 artifact, 161 Consumer and
89+89 metadata cases without failures/skips, with unchanged fifteen-archive
map `f351b872a7a4c111fe1b1321c7a7955e2b82c5763be59c00eab3ecd69b28789c`.
Actual bounded output observation with a separate empty runtime cache confirms
58 exact rows, 60 genuine origins, 58 creates/two reopens and 360 actual
role/image/archive correspondences. Tooling passes 322 checks (305 passed/
seventeen macOS-native skips), including 96 SDK checks; Consumer formatting,
frozen catalogs/inventory and patch checks pass. The next native request is
214 foundations and 95 scopes/868 observations; it passed as run `40157571215`
at `8fed4125a4457e21af84b33a5c1f9be80b4dca26`, all three jobs,
zero foundation failures/errors/skips and every prerequisite.

Compatible-reopen run `40155922560` binds input
`6269c9ddadd831a7cdef59dfd7e8d2194bd767e316e7e8fb7d2272fc04886890`,
preparation `d6b7c46e8a76016e6290406375013dfbd2b2668ae1eddc859fba1a15d6a1f83d`
and 91,721,584,640 free scratch bytes; it predates these fifty further rows.
Metadata zero-reference revision ABA is not artifact-incarnation/shared-authority
qualification. Complete category/profile imports, integrations and final T081
remain open; frozen assertions/wrappers, provider mechanisms, historical seals,
locks, tasks and reviewer markers are unchanged. Production/deployment examples
and architecture diagrams are unaffected by these test-only imports.

### Actual metadata schema consumer lineage

Eight observed rows now execute unchanged upgrade, invalid-upgrade,
upgrade-exclusion and future/corrupt-schema consumers through genuine legacy/
current factories. A transparent caller-side recorder forwards actual operations
and disposal and captures each underlying observed session and actual reopen
before handoff; failed capture disposes the unreturned child. The recorder never
substitutes itself as a factory/component and does not change the common
assertions or their enclosing disposal scopes.

The missing schema inventory first fails its intended regression. Strict
multi-origin admission requires three origins for upgrade, two
for invalid/exclusive upgrade and four for future/corrupt schema, with matching
independent descriptors. Missing, extra and foreign descriptor origins fail.
The shared artifact count validator retains its original one/two-origin rules.

Fresh exclusive preparation/replay pass 311 artifact, 169 Consumer and
89+89 metadata cases without failures/skips. All fifteen normalized archives
preserve map `f351b872a7a4c111fe1b1321c7a7955e2b82c5763be59c00eab3ecd69b28789c`.
Actual bounded output observation with an independent empty runtime cache
verifies all 66 metadata rows, 82 origins, 68 creates/14 reopens and
492 actual role/image/archive correspondences; artifact replay retains
24 rows/26 origins/208 correspondences. Tooling passes 323 checks
(306 passed/seventeen macOS-native skips), including 97 SDK checks; Consumer
formatting, frozen catalog/inventory and patch checks pass. The next native
request is 215 foundations and 95 scopes/876 observations, not yet admitted.

Entity/atomicity/lease native admission binds input
`b964bc83022faac1ac7891361f8b89dddb97f97a03d760553f9b26ec8adfd432`,
preparation `5927c9a5161d6646c61102a0cb3f0442efa1da4c1009f66bba533aa4d6b00999`
and 91,721,551,872 free scratch bytes. It predates reference/schema increments.
Memory upgrades/reopens are logical, not durable recovery. Complete category/
profile imports, complete recovery-profile admission, integrations and final T081 remain
separate unfinished work. Historical seals, locks, tasks and reviewer markers
stay untouched; production/deployment examples and diagrams are unaffected.

### Actual metadata bounds, diagnostics and ownership consumers

Forty-two observed rows now import unchanged bounds/scopes, page kinds/request/
result limits/datasets, ticket/lease clock rollback, cancellation/queue/exception
mapping, ledger/diagnostic, publication evidence/replay/orphan, corrupt groups/
pages and explicit admission/invalid-budget/incomplete-cleanup/disposal consumers.
Admission/budget cases start unprepared. Store-level disposal stays inside the
original common consumer while the enclosing session retains resource ownership;
origins are captured while actual components are live and emitted only after
assertions pass. Incomplete-cleanup cases retain actual held work until release
and genuine settlement, never equating finite return with Released.

The missing identities first fail the exact-inventory regression. Fresh exclusive
preparation/replay pass 311 artifact, 211 Consumer and 89+89 metadata cases
without failures/skips, preserving the same fifteen-archive map. Actual bounded
output observation with an independent empty runtime cache confirms 108 exact
rows, 124 origins, 110 creates/14 reopens and 744 actual role/image/archive
correspondences. Tooling passes 323 checks (306 passed/seventeen macOS-native
skips), including 97 SDK checks; Consumer formatting, frozen catalog/inventory
and patch checks pass. The next native request is 215 foundations and
95 scopes/918 observations, not yet admitted.

Reference/reconciliation native admission binds input
`1fd6680fdc710f2753985b0b24f7c7a6f1351ec1b47d15a5f1527534035b70cc`,
preparation `d5ee7e5f0d0c4e43c46b95cb7861df4d08f1ccd55f82d6da2ec13bbdd29a2fe3`
and 91,721,572,352 free scratch bytes. It predates schema/control increments.
Common assertions/disposal scopes, provider mechanisms, historical seals, locks,
tasks and reviewer markers remain unchanged. Complete category/profile imports,
integrations and final T081 remain open; production/deployment examples and
architecture diagrams are unaffected by these test-only imports.

### Actual metadata continuation, query-dimension and foreign-epoch consumers

Twenty-four further observed rows execute unchanged common consumers for all
six continuation-corruption shapes (each over six continuation components),
the five supported query-dimension corruptions and foreign-store epochs.
Each epoch consumer prepares two independent actual stores; strict admission
requires both actual create origins, not a synthetic foreign-token claim.

The absent identities first fail the inventory regression. Fresh exclusive
preparation/replay pass 311 artifact, 235 Consumer and 89+89 metadata cases
without failures/skips, preserving the same fifteen-archive map. Actual bounded
fresh-cache observation verifies 132 exact rows, 150 origins, 136 creates/
14 reopens and 900 role/image/archive correspondences. Tooling passes 323 checks
(306 passed/seventeen macOS-native skips), including 97 SDK checks; Consumer
formatting, frozen inventory/catalog and patch checks pass. The next native
request is 215 foundations and 95 scopes/942 observations, not yet admitted.

Schema native run `40158238921` at
`9399c3ca10bb59a474462a892ae326655ce819db` passed all three jobs,
215 foundations without failures/errors/skips, 95 scopes/876 exact
discoveries/executions and every prerequisite. Input:
`70cde04a349134675712f565458f275d9bd6cdce105ccf0c6ad9fd49de433cbd`;
preparation:
`a2f2fb64e77dc059b89e55d8e7bd5cd8e6df6a0743b3eb06fbb1fa5c4fe82167`;
free scratch 91,721,506,816 bytes. It predates controls/cursor increments.
Common assertions/disposal scopes, provider mechanisms, historical seals,
locks, tasks and reviewer markers remain unchanged. Complete category/profile
qualification, integrations and final T081 remain open; production/deployment
examples and diagrams are unaffected by these test-only imports.

### Actual four-way authority integration consumers

The package-only Consumer now source-links the planned
`Hoard.Conformance.Tests/AuthorityIntegrationTests.cs` while the ordinary SDK
test project excludes it. This reuses the Consumer's existing unit resource
owner and isolates the additional explicit HostAdapters package dependency
from SDK/Core. All four actual SQLite/Memory and Local/Object compositions
run reference-admission, failed-transaction, live-reference, lost-acknowledgment,
incarnation ABA, protected-reader, foreign/copied-handle and shutdown consumers.
The first seven reuse unchanged common bodies; shutdown holds a real recognized
guard while a separate stable close task fences admissions and joins genuine
metadata worker settlement, authority holdings and both disposals. Root
reclamation belongs only to the unit owner after successful settlement.
Original wrapper disposal is unchanged; no synthetic metadata bridge or
fabricated Released substitutes for actual composition.

The absent scope fails its initial regression. NU1004 then correctly rejects
the missing direct dependency graph; the Consumer lock is regenerated from
actual packed archives for the explicit new edge, not by relaxing locked replay
or rewriting historical locks. Fresh preparation/replay pass 267 Consumer,
311 artifact and 89+89 metadata cases without failures/skips. Fifteen normalized
archives reproduce map
`2a2290ffc16031eed65385620927f0768f9b54631eb734f76cc2f473d0200079`;
fourteen actual Hoard images match archive bytes per preparation. Separate
empty-cache observation verifies exactly 32 discoveries/passes. Tooling passes
324 checks (307 passed/seventeen macOS-native skips), including 98 SDK checks;
ordinary binding/catalog tests pass 23 without skips. Consumer/HostAdapters
formatting, frozen inventory/catalog and patch checks pass. Bounded custom
architecture review found no confirmed blocker; the actual preparation/replay
and execution address its pending runtime/lock evidence gaps.

Controls run `40158951602` at
`3fb2705c1639e11e7c1ca730e769cffe92b131e5` passed all three jobs,
215 foundations without failures/errors/skips, 95 scopes/918 exact observations
and every prerequisite. Input:
`5cc167d09eb4b693ea636094e623b6bf2b9bb45586e497016e42b8da2a091591`;
preparation:
`79a05caec7d7126f532473f579c6cc8d736f14c81bd33265665afecc8b99f59e`;
free scratch 91,721,510,912 bytes. It predates cursor/authority imports.
The new native request is 216 foundations and 96 scopes/974 observations,
not yet admitted. T033/category qualification, subsequent profiles and final
T081 remain unfinished. Tasks/reviewer markers and historical seals are
unchanged; production/deployment examples and diagrams are unaffected.

### Isolated category-mutation diagnostic checkpoint

The package-only Consumer conditionally source-links `CategoryMutationTests.cs`
and the two isolated decorators with `ConformanceCategoryMutations=true`.
Ordinary Consumer builds omit all intentional failures, and the ordinary SDK
contract project excludes the source-linked file. No package graph or lock
changes are required. Faulty metadata replays an actual prior successful commit
after expiry; faulty artifacts genuinely commit staged bytes before returning.
Both providers in each family execute identical private caller helpers and
unchanged common assertions. Corrected pairs disable only the deliberate fault.
Mutation counters distinguish setup failure; the artifact decorator owns and
disposes unexpected successful read sessions before session shutdown.

The absent exact-scope regression first fails. Fresh locked preparation and
independent fresh-cache replay each observe eight exact rows: four named common
assertion failures and four corrected passes. All pairs execute the same
Consumer image per preparation, fourteen actual Hoard images match archives,
and SDK/catalog/common assertion bytes are unchanged. Mutation/caller source
hash: `e5a9cefa84d91a0c84c656cc7f3ede8108f2a01a2cb2aa1ddf010ae9487d0058`;
unchanged SDK archive:
`ff017330f594505a0ea3ccbcf42f994062e79c3f002f370e7df392f357140a3e`.
The default-build discovery explicitly excludes mutations before opt-in rebuild.
Exact scope, named assertion manifest, provider-package hash and SQLite
environment admission regressions pass. Tooling passes 326 checks (309 passed/
seventeen macOS-native skips), including 100 SDK checks; opt-in Consumer
formatting, frozen inventory/catalog and patch checks pass. Local capacity
failures are resolved by reclaiming completed private dependency caches,
preserving sources/archives/runtime images/receipts and the unchanged 24 GiB
guard. The next native request is 218 foundations and 100 scopes/982 observations,
not yet admitted. T034/full category/controller qualification, subsequent
profiles and final T081 remain open. Tasks, reviewer markers and historical
seals/locks are unchanged; product/deployment examples and diagrams are
unaffected by these isolated test-only decorators and opt-in callers.

A subsequent launch-boundary regression finds the remaining full-family-only
runtime guard, with `WitnessMissing` for all four otherwise valid paired scopes.
The repair admits only exact full-family or same-family paired inventories;
reduced, duplicate and cross-family rows reject before launch. The regression
checks actual generated safe logger settings, method filters and hashes of
independently created package files before a controlled command-boundary stop,
not a native execution or the earlier mocked `test_attempt` handoff.
All 326 tooling checks pass (309 passed/seventeen macOS-native skips). The
obsolete pending mutation run `40161267008` was requested to cancel and is not
admitted. The replacement exact-head request retains 218 foundations and
100 scopes/982 observations; T034/category/controller qualification remains open.

Cursor native run `40159593512` binds exact head
`5c7522fcff37fdb48e12e5ba7a1e9377b75414ac`: all three jobs,
215 foundations without failures/errors/skips, 95 scopes/942 exact discoveries/
executions and every prerequisite pass. Input:
`b25a73b12c913e9dc52bb37f99e7f5715cfb95e8ac8f581d07c4907f18c669c5`;
preparation:
`8166e2e6cef3c6b3430721ba11d6f23ccea4d8ada689463e1d9721d4a88d6c1d`;
free scratch 91,721,383,936 bytes. It predates authority/mutation increments
and remains diagnostic, not category qualification.

### Explicit category binding-slot input checkpoint

Capture-time `binding_sources` can explicitly select `catalogBindingId` for the
four frozen category slots. The independent catalog mapping requires the
original fixture declaration ID, category and exact provider package identity;
only the outer `ProviderBinding.bindingId` is projected. Descriptor bytes/hash,
capability hash, adapter identity and actual package identity remain unchanged.
Unprojected capture preserves existing IDs, and one original declaration ID
cannot enter a profile twice through projected/unprojected assignments, including
different JSON serialization. No C# declaration,
provider/SDK operation, package graph, lock or SDK catalog changes.

Focused intended failures expose the absent slot argument, missing profile
source field and duplicate-descriptor admission before repair. A differently
serialized duplicate also failed before original-ID rejection replaced hash-only
checks. Full profile
capture/recapture proves assignment/capability changes alter admitted inputs.
Actual bounded observation and independent empty-cache replay each verify all
four slots through four selected factory/reopen cases: eight genuine origins,
four creates/four reopens, 56 role/image/archive correspondences and fourteen
unchanged Hoard runtime images. Every origin joins the original raw descriptor
hash, not a rewritten projected declaration. Policy source-map digest:
`c690a938f46e50f37a8ca4392648d51a63c856a4f6dc789b61ab213f53329de7`.
Tooling passes 327 checks (310 passed/seventeen macOS-native skips); frozen
inventory/catalog and patch checks pass. This is input wiring only: complete
category runtime/import/applicability/evaluation and T035/T081 remain unfinished.
Execution/verify/aggregate guards are unchanged. Task/reviewer markers and
historical seals remain unchanged; product/deployment examples and diagrams
are unaffected.

Authority native run `40160483040` binds exact head
`eeaa6bf261a87edbb4df2b5cedebfb633fdacc5e`: all three jobs, 216 foundations
without failures/errors/skips, 96 scopes/974 exact discoveries/executions and
every prerequisite pass. Input:
`66c397e9b6a3824d1c0770794185e079ca10db6fe5d346fdcdf41f0683721d94`;
preparation:
`ac34b453116593d113688cee1c89130f565b2ef9d930ce3a08b484f469c75809`;
free scratch 91,721,281,536 bytes. It predates mutation/slot input increments.
The next request is 219 foundations and 100 scopes/982 observations, not yet
admitted or complete category/controller qualification.

### Full category batch input/import model and actual logger repair

`CategoryRuntimeHistory` independently selects both required package/binding
options and each binding's complete frozen runtime union. A witness's primary
execution context is the lexicographically first catalog case mapping it;
the same actual execution UUID/hash can then satisfy other explicitly mapped
keys without rewriting proof bytes. Append-only attempts retain failed imports
before retries. Exact identity, current-run input/owner/assembly/package
provenance, qualification origins, monotonic bounds and cross-batch execution/
session/component consistency remain mandatory.

Across the two category profiles, result vectors retain all 192 inherited keys
plus the original six metadata/seven artifact QC obligations. No vector is returned while
a binding/control scope is unobserved. Controller-only obligations require an
explicit owned attempt and remain incomplete when interrupted/unimplemented;
exclusions have no attempted execution. Synthetic transport regressions cover
both full inventories, shared UUIDs/hashes, exclusions, missing QC controls,
reduced manifest rejection, retained failure/retry and absent qualification
origins. A fifth regression supplies structurally valid synthetic qualification
origins, then rejects cross-binding execution-ID replay without changing
previously accepted witnesses/proofs. The immutable primary-case selection is
exposed before manifest construction and reused during import. These model
fixtures do not establish actual original-wrapper provenance or genuine category
execution. Actual runner,
legacy adapter integration, controller proof ingestion, evaluation and T035/
T081 remain unfinished; execution/verify/aggregate guards are unchanged.

Native run `40161613939 @abfa812` failed `EvidenceIncomplete` at category
mutations. Actual local launch/settings/logger reproduction establishes that
both faulty pairs reached the intended SDK assertions but `Assert.IsType()`
was absent from the bounded xUnit prefix allowlist. The repair adds only that
prefix, retaining exact named SDK frame checks and sanitization. The new
regression first fails its type-assertion row, then all 46 logger tests pass.
Actual logger observation and independent fresh-cache replay each reproduce
eight exact discoveries/executions, four named failures and four corrected
passes with unchanged Consumer/SDK images. Logger DLL SHA-256:
`39cee1a181c1386707b962f93261a6a9cbbae1460ee51fd17140663178e7e4be`;
Consumer `5dfa9f2a710c3dfbd4262a9bec74d6158778497c88cd51a72cddd0d9cf50168b`;
SDK `40d9858083c1777943515b193f30f36bd23349d08d70d73ef070ea76172aac85`.
These are bounded local logger diagnostics, not complete profile inputs or
native admission. Superseded slot run `40162771846 @c1f79b2` is confirmed
canceled; neither run contributes an admitted receipt.

Full tooling passes 332 checks (315 passed/seventeen macOS-native skips).
Capacity-only failures were resolved by reclaiming 28 inspected completed
private dependency caches, preserving sources/archives/images/receipts and the
unchanged 24 GiB guard; the follow-up reclaimed another twelve completed
red-probe dependency caches after the same capacity-only failure recurred.
C# logger/tests formatting, frozen inventory/catalog
and patch checks pass. Replacement native run
[40164176338](https://github.com/Stonefly-Labs/Hoard/actions/runs/40164176338)
at exact head `2ecda7f4ae7f96a0be64bbb838e07bdf07dc4873` passed all three jobs,
223 foundations without failures/errors/skips and the strict 100-scope/
982-discovery/execution vector with every prerequisite and all mutation scopes.
Input: `a9b4f33d0b3e6dde4ea577d856f0d7a54e113fe712daf5054b55bce4501b0e91`;
preparation:
`69a1b07eb8ac465a00fc829cb2d5bfdf7b13929f6500e371245f4e5ab2352af1`;
free scratch 91,719,884,800 bytes. This is admitted diagnostic evidence, not
full category qualification or verification of later `90fd088`.
That receipt alone changes no admission rule or schema. The later first-slice
original-wrapper implementation below is a separate test-evidence clarification.
README and affected guides/model/contracts are updated; product/deployment
examples and diagrams, historical seals, task/reviewer markers and locks are
unchanged. Implementation remains running.

### Non-owning original-wrapper provenance

The maintainer explicitly instructed autonomous decisions and continued
implementation rather than another approval pause. Following the bounded custom
architecture review, original wrappers now have a distinct, versioned observation
path. The independent frozen-identity policy initially covers MP-01's original
roundtrip, both AS-01 parameters and the session-free identity-bound test. Actual
SDK consumers and all unclassified witnesses retain strict typed session origins;
there is no provider-selected kind, artificial companion session or permissive
fallback.

`ConformanceOriginalObservation` captures actual original owners/interfaces with
reference-equality component IDs, source/runtime/image attribution and optional
reopen lineage, but never disposes or reclaims a root. A loaded-contract
observation captures the actual relevant `Type`/module, not a fictional provider
session. The separate `hoard-original-v1` packet channel feeds a distinct
`originalObservations` collection only in private execution-proof revision 2;
revision-1 proofs and public revision-1 entities remain unchanged. Parent
admission independently checks kind, exact context/roles, selected store package,
runtime/image correspondence, lineage and cross-attempt replay. Unknown or
missing required provenance cannot pass.

The first wrapper slice pins the actual metadata authority facade used by the
common assertion and observes the existing artifact driver/lifetime/controls.
A package-only partial value-test observer leaves predecessor default builds
without SDK dependencies or invented sessions. Original factories, clocks,
common assertions, runtime identities and cleanup remain unchanged.
The initial model/logger tests first fail on missing APIs/admission. The new
producer and typed logger/binding contracts pass 68 tests without skips.

Actual observation and independent fresh-cache locked wrapper replay each
observe six exact discoveries/executions: both metadata providers, both artifact
providers and two session-free contexts, with 26 actual role/image
correspondences. The reproduced SDK archive is
`a94e225acd4ef19a8d1b363f5c7eedf498bae9364fbc2838f917f17c595485e3`.
These use minimal local logger inputs and are bounded diagnostics, not qualifying
RunInputs, complete original coverage, native admission or complete profiles.
Remaining direct-construction/reopen, child/controller and evaluator wiring
continues. README and affected guides/model/contracts describe the distinction;
production/deployment examples/diagrams are unaffected. Reviewer markers,
historical seals, public product contracts and locks remain unchanged.
Full tooling passes 335 checks (318 passed/seventeen macOS-native skips),
including all three new original-observation admission/replay regressions.
Capacity-only failures were resolved by reclaiming thirteen inspected completed
private caches while preserving sources/archives/images/receipts and the unchanged
24 GiB guard. The synthetic complete-category origin fixture now independently
assigns each selected provider package to its original store/schema roles rather
than borrowing a generic fixture package. Bounded custom architecture review
found no confirmed blocker for this first slice; complete qualifying inputs and
coverage remain explicitly outstanding.

### Full-input original-observation diagnostic wiring

The initial identity-bound contract probe is an auxiliary original test, not
one of the frozen category value witnesses. Both actual frozen value witnesses
(expectations/checksums and redacted diagnostics/get-only members) now have
package-only loaded-contract observations after their unchanged assertions.
The auxiliary hook remains supported. No frozen identity/assertion/ownership,
SDK archive, public contract, tracked lock or predecessor dependency changes.

Five exact native scopes now schedule eight original executions. A separately
captured full input document projects original binding descriptors into frozen
catalog slots while preserving their raw bytes/hash and package relationships;
the existing typed-binding input document retains its original IDs. Source,
runtime/package bytes and invocation group are shared. Both documents recompute
independently after execution and report separate digests. Manifest primary-case
selection reuses the same immutable helper as category history. Selected
component images are independently declared; every new passing execution must
contain exactly one original observation of its independently selected kind,
not an unrelated typed session or only a successful result.

Two focused regressions first fail on the missing APIs, then pass after wiring.
They check exact scopes, selected frozen binding/case/image/context before
launch, real settings generation, shortened/provider-selected rejection and
missing/replayed/substituted observations. Full tooling passes 337 checks
(320 passed/seventeen macOS-native skips). The predecessor value-test command
`dotnet test tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj --no-restore -c Release --filter FullyQualifiedName~ArtifactValueTests -p:UseSharedCompilation=false -nodeReuse:false -v quiet`
passes all seven tests without skips, with no original context/SDK dependency.
Actual local package-only observation and independent fresh-cache locked replay
each pass eight discoveries/executions, four original owners, four session-free
contract contexts and 28 image correspondences, reproducing the unchanged SDK
archive `a94e225acd4ef19a8d1b363f5c7eedf498bae9364fbc2838f917f17c595485e3`.
These remain minimal-input diagnostics; the new full-input path requires its
own exact-head native receipt (105 scopes/990 observations plus every existing
prerequisite). No such receipt or category qualification is claimed yet.
`dotnet format tests/contracts/Hoard.Artifacts.Tests/Hoard.Artifacts.Tests.csproj --no-restore --verify-no-changes --verbosity quiet`,
`python3 tests/fixtures/conformance/baselines/freeze_inventory.py --check`,
`python3 scripts/conformance_case_catalog.py --check-sdk` and `git diff --check`
all pass.

Capacity-only tooling failures were resolved by reclaiming eighteen inspected
completed private caches, retaining source/archive/runtime/proof/receipt data
and the unchanged 24 GiB guard. README and affected guides/model/contracts are
updated; production/deployment examples and diagrams are unaffected. Broader
original/direct/reopen/controller coverage and executable qualifying profiles,
later stories and final T081 remain unfinished. No task/reviewer marker or flow
checkpoint is advanced.

### Original identity, publication and reference owners

Original metadata MP-02/03/13/23..27/31 now share the existing non-owning
observation policy with MP-01. Each wrapper pins exactly the authority facade
already passed to its unchanged common assertion. A shared source helper
observes that facade plus the original returned fixture/store/schema/controls,
while the same `await using` still owns disposal. `CallerMemberName` identifies
each exact unparameterized source method; no parameter-selected fallback,
companion factory/session, new clock/root or ownership transfer is introduced.
Uninstrumented/parameterized identities remain subject to their existing strict
admission rather than inheriting this policy.

The expanded routing regression first fails as intended on the prior
eight-execution scope. Actual local source launch and independent empty-cache
locked replay each pass 26 exact discoveries/executions, twenty metadata owners,
two artifact owners, four loaded-contract contexts and 118 image correspondences.
Both reproduce the unchanged SDK archive
`a94e225acd4ef19a8d1b363f5c7eedf498bae9364fbc2838f917f17c595485e3`.
These local probes still use minimal diagnostic inputs, not qualifying reports.
The expanded full-input native path requires 105 scopes/1,008 observations and
all existing prerequisites; the earlier `0005638` request covers only the
eight-execution increment and cannot admit these later source changes.

`python3 -m unittest discover -s tests/tooling -q` passes 337 checks
(320 passed/seventeen macOS-native skips).
`dotnet format whitespace --folder tests/contracts/Hoard.Metadata.Tests/Cases --verify-no-changes --verbosity quiet`,
`python3 tests/fixtures/conformance/baselines/freeze_inventory.py --check`,
`python3 scripts/conformance_case_catalog.py --check-sdk` and `git diff --check`
all pass. The 23 focused metadata/artifact inventory/discovery/hook guards also
pass without skips; their historical partial-T019/T020 limits still apply.
README and affected guides/model/contracts are updated; production/deployment
examples and diagrams are unaffected. No task/checklist marker, historical seal,
lock or flow checkpoint is advanced; complete original/direct/reopen/controller
coverage, category/profile qualification and later stages remain unfinished.

Recovery-reopen native run `40146117625` binds exact head
`994f9fb8819b7ff363382c3ff66b6087d5e34002`: all three jobs, 204 foundations
without failures/errors/skips, 87 scopes/757 exact discoveries/executions and
every prerequisite recovery/transfer/ownership/native-containment and
eighteen-package/thirteen-lock replay chain pass. Input:
`b3ae300a176e670997e660d96364e71c2061bac336fb8a536efb9b93e7b0c491`;
preparation:
`6fc731b1195af2c5a1ee8f575aba556933327c7e915813c5bf178a801fe99b37`;
free scratch 91,717,259,264 bytes. This is diagnostic evidence, not qualification.

### Original artifact publication owners

All twelve frozen original publication parameters (AS-01..06 and shared AS-13)
now capture their actual driver and its existing store, validator, maintenance,
private lifetime, authority and fault controls. One non-owning driver helper
uses source-owned caller names and the genuine provider parameter. It creates
no session, changes no assertion/barrier/clock and transfers no cleanup.
Shared witnesses keep the catalog's existing primary-case ownership; no proof
is relabeled or duplicated.

The routing regression first fails at 26 rather than 36 executions, then passes.
Actual local observation and independent fresh-cache locked replay each pass
36 exact discoveries/executions, 32 original owners, four session-free contract
contexts and 188 role/image correspondences, with unchanged SDK archive
`a94e225acd4ef19a8d1b363f5c7eedf498bae9364fbc2838f917f17c595485e3`.
These probes use minimal diagnostic inputs. The expanded full-input native
vector requires 105 scopes/1,018 observations and every prerequisite, not
category/profile qualification; its receipt remains pending.

`python3 -m unittest discover -s tests/tooling -v` passes 337 checks
(320 passed/seventeen macOS-native skips).
`python3 tests/fixtures/conformance/baselines/freeze_inventory.py --check`,
`python3 scripts/conformance_case_catalog.py --check-sdk` and changed
driver/publication-file whitespace verification pass. The broader folder
formatter found pre-existing whitespace at `ArtifactEvidenceTests.cs:79..80`;
that unrelated file remains unchanged. README and affected guides/model/
contracts are updated; production/deployment examples and diagrams are
unaffected. Task/reviewer markers, historical seals, locks and the running
checkpoint remain unchanged. Full original/direct/reopen/controller coverage,
qualifying category/profile runners and later stories remain unfinished.

Earlier run
[40166560899](https://github.com/Stonefly-Labs/Hoard/actions/runs/40166560899)
binds exact head `8aaa36d745ad4dfe52776b818b668be244c96bc6`: all three jobs,
227 native foundations without failures/errors/skips, 100 scopes/982 exact
discoveries/executions and every recovery/transfer/containment/replay
prerequisite pass. Input:
`759b9ef9d73c65723b5aff95515b6650831430f4433396f5c435ad8133b7e8ef`;
preparation:
`81450552403c843f0c8307063bdc17357ad2e96d3642a639ff1cfc5dc2b4dddf`.
This admitted diagnostic receipt predates full-input original scopes and does
not qualify these later changes.

### Witness-specific original authority images

The flat per-binding image map could not truthfully describe original wrappers
that use the fixture authority directly versus those that pass a test facade
to common assertions. Original assignments are now nested by binding, exact
runtime identity and role, bounded and deeply frozen by both history classes.
Ingestion selects only that exact identity and exact role inventory; no flat,
foreign-witness or cross-binding fallback is accepted. Typed-origin assignments
and all public/private proof schemas are unchanged.

Forty-two single-owner metadata identities per provider now observe the real
fixture/store/schema/controls and genuine authority shape. Assertions that
already passed a facade pin and observe that same facade; all others observe
the fixture's existing authority. No unused facade, factory/session, clock/root
or cleanup transfer is introduced. Parameterized, multi-owner and reopen
witnesses remain outside this one-root policy.

The focused assignment immutability regression first fails with
`EvidenceIncomplete` in the old flat parser. Expanded independent frozen
routing first fails at 36 rather than 100 executions. Actual minimal-input
observation and independent empty-cache locked replay each pass 100 exact
discoveries/executions: 84 metadata owners, twelve artifact owners, four
session-free contexts and 508 actual role/image correspondences. Both reproduce
SDK archive `a94e225acd4ef19a8d1b363f5c7eedf498bae9364fbc2838f917f17c595485e3`.
They are diagnostics, not qualifying input/evaluator/profile evidence.

`python3 -m unittest discover -s tests/tooling -v` passes 338 checks
(321 passed/seventeen macOS-native skips).
`dotnet format whitespace --folder tests/contracts/Hoard.Metadata.Tests/Cases --verify-no-changes --verbosity quiet`,
`python3 tests/fixtures/conformance/baselines/freeze_inventory.py --check` and
`python3 scripts/conformance_case_catalog.py --check-sdk` pass.
Bounded custom architecture review finds no confirmed blocker, with native
full-input admission still pending. The expanded native requirement is
230 foundations and 105 scopes/1,082 observations, retaining every prior
prerequisite; it does not complete final T081 or any qualifying profile.
README and affected guides/model/contracts are updated; production/deployment
examples and diagrams are unaffected. Tasks/reviewer markers, locks, historical
seals and the running checkpoint remain unchanged. Complete original/reopen/
controller attribution and later implementation tasks remain unfinished.

### Exact parameterized and direct-construction originals

All five query-dimension corruption parameters and six malformed-continuation
parameters now observe genuine original instances after unchanged assertions.
The shared helper uses the actual `shape` argument plus source-owned caller
identity; independent frozen selection includes every parameter, with the same
already-used facade for query dimensions and real fixture authority for
continuations. Both original admission witnesses also observe their directly
constructed fixtures without adding factories, initialization or disposal.
Original metadata coverage is now 55 exact identities per provider.

Parent ingestion additionally requires the current policy's one observation;
an extra independently numbered root can no longer pass merely because its
roles and context otherwise match. The added regression first fails because
the previous ingestion accepts it. Expanded routing first fails at 100 versus
122 executions before adding the two direct witnesses brings the total to 126.
Actual minimal-input observation and independent fresh-cache locked replay
each pass 126 exact discoveries/executions, 122 original owners, four
session-free contexts and 638 role/image correspondences, reproducing SDK
`a94e225acd4ef19a8d1b363f5c7eedf498bae9364fbc2838f917f17c595485e3`.
No category/profile qualification is inferred.

`python3 -m unittest discover -s tests/tooling -v` passes 338 checks
(321 passed/seventeen macOS-native skips).
`dotnet format whitespace --folder tests/contracts/Hoard.Metadata.Tests/Cases --verify-no-changes --verbosity quiet`,
`python3 tests/fixtures/conformance/baselines/freeze_inventory.py --check`,
`python3 scripts/conformance_case_catalog.py --check-sdk` and `git diff --check`
pass. The new full-input native vector requires 230 foundations and
105 scopes/1,108 observations, pending. Broader multi-owner/reopen/controller
coverage and qualifying runners remain unfinished. README and affected
guides/model/contracts are updated; product/deployment examples and diagrams,
SDK/public contracts, locks, historical seals, reviewer/task markers and the
running checkpoint are unchanged.

Full-input run
[40167209164](https://github.com/Stonefly-Labs/Hoard/actions/runs/40167209164)
binds exact head `0005638ac1b6a75f267d95332ebbb865b51ec436`: all three jobs,
229 native foundations without failures/errors/skips, 105 scopes/990 exact
discoveries/executions (including eight originals) and every recovery/transfer/
containment/replay prerequisite pass. Typed input:
`824568e3af9b8df6bd2cc69dda0464875a1d6c009d9a25c66fef3865a1e8b39c`;
separate original input:
`743646e7c2a0094bf4e1df8c2d8700fba64e6ce899ee9ef57ba24d193049c8b9`;
preparation:
`3f7f3616d95db05ffe188f099dac364f7b1e6d28fc175605c95ee2583fd1fc19`.
Both input documents independently recompute. This admits only that earlier
diagnostic increment, not later expanded sources or qualifying profiles.

### Genuine original creation/reopen forests

Seven further metadata identities now observe their actual independent roots
and schema-reopen chains, bringing operational coverage to 62 identities per
provider. The closed catalog fixes every node count and parent index; parent
ingestion rejects extra/missing roots, foreign/current-execution parent mismatch
and reused owner/store IDs. SDK continuation separates previous reference-equality
identity state from actual parentage, retaining existing binary signatures.
Source sequences are non-owning. Schema observations capture the actual adapter
owner and genuine underlying fixture authority without manufacturing an unused
facade; existing assertion-facing authority behavior is unchanged. Failed
observation after real reopen disposes the newly transferred fixture before
propagating failure.

The positive forest admission regression first fails `WitnessMissing`; the SDK
regression first fails for the missing `previous` overload. Actual minimal-input
observation and independent empty-cache locked replay each pass 140 exact
discoveries/executions, 162 records (158 original owners/four contracts) and
818 role/image correspondences. SDK archive reproduces as
`032389ce6626072e1d3b455d1af77779e6656f46f5cba1187df3dbdf591922c1`.
These probes are not qualifying RunInputs.

`python3 -m unittest discover -s tests/tooling -v` passes 339 checks
(322 passed/seventeen explicit macOS-native skips).
`dotnet test tests/contracts/Hoard.Conformance.Tests/Hoard.Conformance.Tests.csproj --no-restore -c Release --filter 'FullyQualifiedName~RuntimeLoggerTests|FullyQualifiedName~BindingContractTests' -p:UseSharedCompilation=false -nodeReuse:false -v quiet`
passes 69 without skips. SDK/test-project format, metadata-folder whitespace,
frozen inventory and SDK catalog checks pass. A bounded custom architecture
review finds no confirmed blocker, with read-only/diff-reproduction limits;
it is not final T081. Native admission now requires 231 foundations and
105 scopes/1,123 observations, pending. Host/controller attribution, broader
artifact coverage and qualifying backends remain unfinished. README and affected
guides/model/contracts are updated; product/deployment examples and diagrams,
public product contracts, historical seals, locks and reviewer/task markers
are unaffected.

Earlier witness-specific run
[40168790991](https://github.com/Stonefly-Labs/Hoard/actions/runs/40168790991)
binds exact head `3f1409a6705b43c8d1ba347396f03db6ab3497d2`: all three jobs,
230 foundations without failures/errors/skips, 105 scopes/1,082 exact
discoveries/executions (100 originals) and every recovery/transfer/containment/
replay prerequisite pass. Typed input:
`55cfb28e9b89f2979276bb699f842cafada908ae341f4d2c64b6c96aff070312`;
separate original input:
`04433046300ac1cdc4ee0c7366c9c17f7e8aa3b154112af9e213c40d940624a4`;
preparation:
`81f24eea2c58cb12588e2c50f3cc9bc5ece9ce5fd3316473c93769c1ca00a72a`.
Both input documents independently recompute; free scratch is 91,721,125,888
bytes. This admits that earlier diagnostic, not the later forest sources or
qualifying profiles.

### Actual configured host owners and further artifact parameters

The original configured-host witness observes two genuine composed module
owners and their existing session interfaces, including rejected schema
admission. Both roots preserve original construction/assertions/disposal; no
additional factory/session or synthetic module is created. Local probes also
check the actual owner type hash against `MetadataFixtureModule`.
Thirty-eight further artifact parameters observe the existing driver/interfaces
after unchanged common assertions across deletion, reconciliation, read
revalidation/destination failure, publication races, storage failures and
selected budget checks. More complicated parameter/reopen/controller shapes
are deliberately not admitted through a single-root shortcut.

The host's missing forest policy first fails `WitnessMissing`; host/artifact
routing first fails exact execution counts. Coverage becomes 63 operational
metadata identities per provider and 50 artifact parameters. Actual minimal-input
observation plus independent empty-cache locked replay each pass 180 exact
discoveries/executions, 204 records (200 original owners/four contracts) and
1,104 role/image correspondences, reproducing unchanged SDK archive
`032389ce6626072e1d3b455d1af77779e6656f46f5cba1187df3dbdf591922c1`.
No category/profile qualification is inferred.

`python3 -m unittest discover -s tests/tooling -q` passes 339 checks
(322 passed/seventeen explicit macOS-native skips).
Changed metadata/artifact source whitespace, frozen inventory, SDK catalog and
patch checks pass. The next native vector requires 231 foundations and
105 scopes/1,163 observations, pending. Controller and remaining artifact
lifetime attribution, qualifying backends and later tasks remain unfinished.
README and affected guides/model/contracts are updated; product/deployment
examples and diagrams, public product contracts, historical seals, locks and
reviewer/task markers are unaffected.

### Exact artifact budget booleans and recovery owners

Forty-four further frozen artifact budget/recovery parameters now observe their
actual driver/interfaces after unchanged common assertions. The helper retains
source-owned argument names and actual bool values. Existing roots, clocks,
barriers, ownership and disposal stay unchanged. Recovery cases that genuinely
reopen or directly construct different owners are not admitted as single roots.
Coverage is now 63 operational metadata identities/provider and 94 artifact
parameters.

The expanded inventory first fails exact execution counting. Full dispatch then
fails on a Local boolean identity: the previous one-parameter-only selector
silently selected Object. Explicit total assignments now handle additional
parameters and reject absent assignments, with independent test expectations
derived from frozen case ownership rather than copying the selector.
Actual minimal-input observation and independent empty-cache locked replay each
pass 224 exact discoveries/executions, 248 records
(244 original owners/four contracts) and 1,412 actual role/image correspondences.
SDK archive remains
`032389ce6626072e1d3b455d1af77779e6656f46f5cba1187df3dbdf591922c1`.

`python3 -m unittest discover -s tests/tooling -q` passes 339 checks
(322 passed/seventeen explicit macOS-native skips); changed artifact source
whitespace, frozen inventory, SDK catalog and patch checks pass. Four inspected
completed diagnostic dependency caches were reclaimed, preserving all
source/archive/runtime/proof/receipt data and the unchanged 24 GiB guard.
Native admission requires 231 foundations and 105 scopes/1,207 observations,
pending. Controllers, remaining artifact lifetimes and qualifying backends are
unfinished; no task/checklist completion or profile qualification is inferred.
README and related guides/model/contracts are updated; product/deployment
examples and diagrams, public contracts, historical seals and locks are unaffected.

Earlier parameterized run
[40169478754](https://github.com/Stonefly-Labs/Hoard/actions/runs/40169478754)
binds exact `ed235eeac3ec1e460fc449bc7aa4e9f4f765fc31`: all three jobs,
230 foundations without failures/errors/skips, 105 scopes/1,108 exact
discoveries/executions and every prerequisite pass. Typed input:
`dc470af7df962339056aa5f0aa92b5ae3137655f3275c4ed265b753193e2e296`;
separate original input:
`fef2354d0ed33670ffb8a4a128851bea09dd7c3b3ab3c4d138491c9025ba8b01`;
preparation:
`54b224c34992d3c9a45553bd80d9ada659b1b8023c9506269a707d335120b435`.
Both input documents independently recompute; free scratch is 91,721,109,504
bytes. This admits that earlier diagnostic, not the later forest/host/artifact
sources or qualifying profiles.

### Genuine Local quarantine children and exact per-node images

Sixteen additional original artifact parameters now observe their actual
quarantine/publication/read/validation owners. Seven Local rows genuinely
construct a fresh store through the existing reopen factory. Non-owning source
records retain those actual objects and their actual explicitly passed empty
controls, then emit them after unchanged assertions and existing cleanup.
Original driver ownership remains in the test assembly; reopened owner/
interfaces/controls belong to Local, with the genuine unchanged authority.
No facade, companion controls, additional store or cleanup ownership is created.
The same original store's in-place reinitialization remains that same object,
not a fabricated fresh owner.

Per-node image assignment is exact and deeply frozen before execution in both
histories. Legacy metadata common role maps remain accepted; these different
artifact owner images require a complete ordered node sequence, not a flat
fallback. Manifests enumerate every node image, and source role maps now include
only identities owned by that frozen binding. The new image regression first
fails `EvidenceIncomplete`; it now rejects swapped/wrong/missing node assignments
while retaining a snapshot despite later source-map mutation. Routing first
fails at 224 versus 240 executions.

The first actual probe correctly exposes a topology mismatch for Local
`detection: "reconciliation"`: its unchanged common consumer returns early and
never calls the fresh-store factory. Independent policy now requires one root
there, not an invented eighth child. Object also stays root-only. Existing
transitive helper body/hash checks remain unchanged, with only observer
forwarding expectations updated. Actual minimal-input observation and independent
empty-cache locked replay each pass 240 exact discoveries/executions, 271 records
(267 original owners/four contracts) and 1,573 role/image correspondences.
SDK archive remains
`032389ce6626072e1d3b455d1af77779e6656f46f5cba1187df3dbdf591922c1`.

`python3 -m unittest discover -s tests/tooling -q` passes 340 checks
(323 passed/seventeen explicit macOS-native skips). Changed artifact source
whitespace, frozen inventory, SDK catalog and patch checks pass. Formatting the
now-touched evidence wrapper also repairs its pre-existing two-line whitespace;
no assertion behavior changes. Native admission requires 232 foundations and
105 scopes/1,223 observations, pending. Controllers, remaining artifact
lifetimes and qualifying backends remain unfinished. README and related guides/
model/contracts are updated; public product contracts, historical seals, locks,
task/reviewer markers and production/deployment examples/diagrams are unaffected.

The bounded custom architecture review found no confirmed blocker in genuine
reopen ownership, exact node/image admission or unchanged cleanup. It inspected
current files without independently reconstructing the Git delta or executing
validation; it does not verify reported hashes/passes or complete final T081.

Earlier owner run
[40170918399](https://github.com/Stonefly-Labs/Hoard/actions/runs/40170918399)
binds exact `4ed4c23aca500827a26d692e011794a2ad84f202`: all three jobs,
231 foundations without failures/errors/skips, 105 scopes/1,163 exact
discoveries/executions and every recovery/transfer/containment/replay prerequisite
pass. Typed input:
`69d28d12e977e66c52c7c4f805171b825c7d3c6fabf2074d710535052f7f7cfa`;
separate original input:
`96335b1825f3c29f7ab9f489622e1197d437315cda3882d69deea43e9e696b78`;
preparation:
`794df389df462f2a03e34e539928ef4214d02eba2c9f925ec5de6864d99cadec`.
Both input documents independently recompute; free scratch is 91,721,052,160
bytes. It admits earlier creation/reopen forests, configured hosts and fifty
artifact parameters, not later budget/quarantine sources or qualifying profiles.

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
