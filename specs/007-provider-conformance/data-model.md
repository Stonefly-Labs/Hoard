# F-07 Qualification Data Model

**Status**: Test/evidence model only. No database schema, product descriptor
field or management API changes. All collections are copied, bounded and
immutable after admission; absent required values fail validation.

## Entities and Relationships

| Entity | Required fields and relationships | Validation/invariant |
| --- | --- | --- |
| ContractCase | `caseId`, `contractRevision`, category, claim class, requirement references, expected witness IDs, applicability rule | Catalog-owned stable identity; assertions/expected results never supplied by a binding |
| QualificationProfile | `profileId`, revision, case expansion, binding/matrix IDs, budgets, prerequisites | Full expected keys frozen before execution; optional exclusions only catalog-authorized |
| ProviderBinding | stable binding ID, provider package/version/hash, category, descriptor/capability hash, factory/fault adapter identity | No display-name identity; one implementation per binding; no self-reported pass |
| MatrixEntry | ID, selected module/package identities, platform versions, enabled set, expected rule/readiness/ownership outcome | Exact finite composition; success declaration cannot imply behavior qualification |
| CompatibilityBaseline | immutable revision, source/lock/recipe hashes, retained binary/dependency hashes, API scope | Prepared before candidate; retained consumer cannot be rebuilt/substituted during execution |
| RunInputs | run/group UUIDs, profile, source manifest, inventory/SDK hashes, packages/locks, typed binding and sealed historical baseline inventories, runtime assembly hashes, safe config/capabilities, environment, budgets, exact safe invocation | Canonical digest recomputed at admission and completion; mutable source/input mismatch blocks qualification |
| ResourceOwnership | run ID, opaque root ID, child PID/start identity, state, bounded cleanup observations | Private ledger resolves actual paths; public projection never contains paths or user data; PID zero/all-zero digest explicitly mean no live child, not a fabricated execution |
| Attempt | sequence, start/end monotonic durations, observed status, actual execution UUID/proof references, safe diagnostic code | Append-only; failed attempt cannot disappear after retry |
| CaseResult | run/profile/binding/matrix/case key, final status, attempts, applicable/exclusion rule, proof hashes | Exactly one final per expected key; all required subproofs present and attributable |
| QualificationReport | schema/catalog revision, RunInputs, exact results, resource settlement, derived qualification and scope limits | Independently recomputed, never trusted from a boolean field |
| SupportStatement | report digest, tested profiles/options/versions/environment, exclusions and unsupported scope | Human-readable projection of verified report, not endorsement or production support |

`CaseResult` key is `(runId, profileId, bindingId, matrixId, caseId)`; unused
binding/matrix dimensions use the explicit catalog value `none`, not omitted
or inferred values. Attempts are children of one result, not extra final
entries. A single runtime test can witness several cases only through explicit
catalog mappings, never matching a display-name substring.

`RunInputs.bindings`, `baselines` and `runtimeAssemblies` bind actual admitted
declarations, retained compatibility artifacts and compiled test artifacts
before execution. Binding packages must match the package inventory exactly;
source/environment digests must match their canonical admitted contents.
Historical binaries remain separate from candidate package identities even
when package versions coincide. Diagnostic work may have no historical
baselines; qualification still requires its independently selected baseline
and scope obligations.

`Attempt.witnessIds` reference actual `RuntimeWitness.executionId` UUIDs,
not test display names, totals or catalog labels. Exact parameterized
`testIdentity` values remain independently catalog-matched. Referenced runtime
observations must match run/group/input/package/assembly/proof provenance;
each attempt's observations must match its result's binding/matrix dimensions
and fit wholly inside its monotonic interval; retries cannot overlap.
duplicate executions and final keys, dangling references and orphan
observations reject. Case proof references retain the union of all attempts,
including an earlier failed attempt followed by a passing diagnostic retry.
Catalog exclusions carry no attempts or fabricated runtime proofs. An
interrupted attempt may have no runtime observations and carries a closed
failure code; runtime skips are `Incomplete`, never exclusion witnesses.

The safe VSTest attempt transport additionally binds a private owner manifest
and an immutable per-attempt manifest to actual run inputs, admitted assembly
paths/hashes and package identities. Each JSONL witness references one exact
proof file with matching execution/attempt/parameter/dimension/input/assembly/
package fields and monotonic duration. The completion record is independently
checked against those observations, not trusted as a passing boolean. Partial
safe observations survive interrupted/skipped/unknown executions; they remain
incomplete. Only an actual frozen assertion symbol can classify an assertion
negative. Test-source hashes do not substitute for loaded-provider evidence.

Private attempt manifests and completion records require `purpose` equal to
`discovery` or `execution`; completion also hashes the exact complete JSONL
bytes as `recordsSha256`. A retained exclusive attempt claim prevents replay
across both purposes. Discovery JSONL records bind schema/run/group/attempt/
sequence/input/manifest/owner, exact selected test identity and fully qualified
method, actual assembly SHA-256 and monotonic `discoveredMs`. Exact method
selection can exclude unrelated methods in the same assembly, never additional
parameter rows of a selected method. Duplicate rows, missing required rows,
foreign source/provenance, changed record bytes or unknown diagnostics block
passing discovery. Partial safe records survive but remain incomplete.
Discovery records have no execution ID, result status or execution-witness
claim and cannot enter execution ingestion. Parent invocation intervals and
input/package inventories are independently checked for both transports.

Parameterized transport identities preserve exact parent-expected display
names. Values may be bounded quoted ASCII/version-range tokens, finite decimal
tokens or bare ASCII identifiers of at most 128 characters (including enum,
boolean and null display tokens). This grammar does not select expectations or
authorize arbitrary text, paths, missing parameters or normalization.

## Validation and Bounds

Category batch history imports the full frozen witness union per binding.
Shared witnesses use the lexicographically first mapped case as their owned
runtime context and retain the same execution UUID/hash across mapped results.
The immutable identity-to-primary-case map is exposed before manifest creation
and reused during import; callers do not supply a separate selection algorithm.
Before launch, callers may partition that whole map into disjoint, nonempty
scopes. The history copies/fixes those maps, independently allocates child
attempt UUIDs and requires each actual manifest to retain its assigned scope
and sequence. Every scope is validated before any batch witness/proof/provenance
is committed. Cross-scope execution/session/observation reuse rejects; failures
remain append-only and fresh retries cannot overwrite them. Actual assertion
failures retain their original witnesses and hashes and affect mapped cases.
No input-selected reduced inventory, rewritten proof, lost failed retry or
excluded execution is admitted. Both binding options and all QC/control keys
remain required; missing controller observations remain incomplete.
Synthetic positive-origin coverage verifies that a cross-binding execution-ID
replay rejects without mutating previously accepted witnesses or proof bytes.
These model fixtures do not establish actual wrapper provenance.

### Binding input snapshot

The test SDK's `ConformanceBindingSnapshot.Capture` produces an immutable
UTF-8 declaration record with exactly `schemaVersion`, `bindingId`, `category`,
`packageId`, `packageVersion`, `packageSha256`, `capabilities` and `faults`.
Categories use `metadata`/`artifacts`; faults use the closed
`ConformanceFault` names. Mandatory category hooks and durable metadata's
backup hook must be admitted before capture. No pass/exclusion field is accepted.

Python `capture_binding` reads at most 64 KiB from the actual pinned declaration
file, checks its package against captured archive bytes, hashes that complete
binding descriptor and separately hashes its category/capabilities/faults.
The adapter ID is still a selected stable identity; actual loaded factory/
session provenance belongs to runtime ingestion, not this snapshot.

Capture-time binding source assignments may additionally specify
`catalogBindingId`. This is not a descriptor or report schema field. The
independent four-slot catalog mapping checks the original declaration ID,
category and exact provider package before projecting only the outer
`ProviderBinding.bindingId` to `sqlite`, `memory`, `local` or `object`.
Descriptor bytes/hash, capability hash, adapter and package identity remain
unchanged; no field is rewritten inside the declaration. Without this explicit
assignment, capture retains the original declaration ID. A profile rejects
duplicate original declaration IDs, including simultaneous projected/unprojected
assignments with identical or differently serialized declaration bytes.
Recapture binds assignment changes through the actual binding
inventory and capability-map keys. Origin matching still uses the original
complete descriptor hash and independently selected component assignments.
This input mechanism does not select exclusions, execute profiles or qualify
a provider.

`capture_profile_inputs` assembles all source/material/declaration roles from
actual files and observed producers. Completion recaptures those same roles;
only measured free-space variation is excluded from immutable machine identity,
retaining the admission measurement rather than fabricating equal free bytes.
`runtimeAssemblies` also inventories selected generated dependency/runtime
configuration files as runtime artifacts. They cannot stand in for an assembly
execution witness; loaded-origin checks must identify the actual assembly.

`ConformanceLoadedAssembly.Capture` observes an actual typed instance, reads
at most 64 MiB from its loaded assembly's symlink-checked path, and uses that one
captured byte sequence for SHA-256 and PE metadata. Assembly name/version and
MVID must match the loaded module; the actual type name is hashed, never rendered
from the provider object. The closed projection is `assemblyName`,
`assemblyVersion`, `moduleVersionId`, `assemblySha256` and `typeSha256`.
`ingest_loaded_assembly` validates it against an independently selected admitted
runtime artifact and optional selected package's embedded runtime inventory.
Explicitly unpackaged test artifacts make no package-origin claim. Component
correspondence alone is not session/factory/invocation attribution or hostile
provider attestation; those execution links remain required.

`ConformanceSessionOrigin` is a separate closed leaf observation: `schemaVersion`,
`runId`, `caseId`, fresh `sessionId`, nullable `parentSessionId`, derived
`factoryOperation`, initial `descriptorSha256`, actual `runtimeVersion`,
`processArchitecture` and `components`. Each fixed role contains `instanceId` and
the closed loaded-assembly projection. Metadata roles are factory/session/store/
schema/authority/faults; artifact roles replace schema with validator/maintenance/
lifetime. Reference-equality IDs are stable within one factory/reopen lineage
(at most 1,024 actual instances), without provider equality/hash/rendering.
No private resource path or opaque store/authority token is projected.
Typed observed wrappers actually invoke factories/reopen and cache consumer
references. The caller owns disposal before any potentially failing getter or
capture; disposal/cleanup observations remain delegated to the actual session.
Capture shares a five-second/256 MiB component-byte scope, 64 MiB per assembly.
`ingest_session_origin` checks exact role inventories against independently
selected runtime/package assignments, immutable declaration/environment and
expected parent identity; inconsistent records for one instance ID reject.
This observation is not an execution witness, pass result or qualification.
Exact platform execution/attempt/group/input linkage is required for result admission.

The implemented private wire channel uses a hash-only projection inside
`sessionOrigins` on the actual VSTest execution proof. Component records contain
only `instanceId`, `assemblySha256`, `moduleVersionId` and `typeSha256`; names,
paths and tokens are never wire data. Complete bounded packets carry the session
UUID, sequential index/count and SHA-256; exact run/case and actual source-result
context bind the projection to its owner/input/group/attempt/execution envelope.
Manifest expectations now require an independent `caseId`. Parent admission checks
the selected declaration, runtime/architecture and role-specific runtime/package
assignments, including explicitly unpackaged test roles. Passing typed-binding
qualification witnesses require full session origins; the original-wrapper
classification below selects its distinct required attribution. Failed/skipped observations
do not invent them. Reopen parents and factory identities must match previously
observed lineage. Instance identity maps span origins/results within an attempt
and all attempts of a case, rejecting changed module/type/assembly for one UUID.
Case history retains immutable origins and rejects session replay even when the
attempt and execution UUIDs are fresh. These checks remain foundation APIs, not
complete profile evaluation or hostile-provider attestation.

### Original-wrapper attribution

The maintainer's instruction to make implementation decisions and continue
resolves the earlier provenance pause. Exact frozen runtime identity now selects
the required proof kind independently: an original operational wrapper observes
its real existing owner and consumer-facing interfaces; a session-free value
test observes its relevant loaded contract. Neither creates a replacement SDK
session. Actual typed SDK binding consumers retain complete typed-session origins.
Unclassified witnesses retain the existing typed-origin requirement; there is
no permissive default or provider-selected classification.

The closed incremental policy covers 63 operational metadata identities per
provider, twelve original artifact publication parameters, both frozen artifact value witnesses (expectations/checksums
and redacted diagnostics/get-only members), and the auxiliary identity-bound value test. The
non-owning `ConformanceOriginalObservation` captures exact run/case/test/binding,
fresh observation UUID, nullable parent observation, kind, operation, actual
runtime/architecture and immutable components. Metadata roles are owner/store/
schema/authority/controls; artifact roles are owner/store/validator/maintenance/
lifetime/authority/controls; session-free observations have only contract.
An owner is the original returned fixture/driver or actual schema adapter, not an invented factory or SDK
session. Contract capture reads the actual loaded `Type`/module bytes and makes
no provider-session claim. Reference-equality IDs preserve actual aliases and
reopen lineage without invoking component equality, hashing or rendering.
Capture neither disposes an interface nor authorizes root deletion.

The separate `hoard-original-v1` channel uses the same bounded, digest-checked
packet framing as typed origins. Its projection contains only closed metadata
and hash/UUID component identities, never private names, paths or tokens.
Execution proof revision 2 explicitly adds `originalObservations`; revision 1
remains unchanged and rejects unknown fields. Public entities remain revision 1.
The parent independently checks witness kind, exact context, role inventory,
runtime/package correspondence, selected provider package, lineage and replay.
A typed session cannot replace required original-instance/contract evidence.
Both case and category histories retain immutable observations and reject
observation replay across fresh attempts/execution UUIDs.

Original instrumentation is opt-in through a bounded context keyed by exact
runtime identity; absent context preserves predecessor diagnostic behavior.
Missing observations still prevent qualifying admission. The first actual
observation and independent fresh-cache locked replay cover six executions and
26 actual image correspondences, but use minimal local logger inputs. They are
bounded diagnostics, not full qualifying RunInputs or complete wrapper/profile
coverage. Broader creation/reopen/child/controller instrumentation remains work.
The expanded local frozen-witness observation/replay passes eight executions
and 28 image correspondences, still with minimal diagnostic inputs. Five native
scopes now use a second fully captured immutable `RunInputs` document at
`proofs/original-run-inputs.json`, preserving raw typed-binding inputs separately.
Only its explicit descriptor-source projection selects frozen binding slots;
raw descriptor bytes/hash and archive attribution remain unchanged. Both input
documents share source/runtime/package bytes and invocation group, and are
independently recomputed after execution. Their digests are separately reported
as `inputsSha256` and `originalWrapperInputsSha256` in the diagnostic summary.
This native path remains unadmitted pending its exact-head run, not a qualifying
profile or a public report-schema change.
The metadata expansion retains the actual facade passed to each common
assertion and emits through one non-owning source helper. `CallerMemberName`
preserves exact unparameterized identities; parameterized/unclassified cases
are not silently admitted. Expanded local observation/replay pass 26 executions
and 118 image correspondences with the unchanged SDK archive. The corresponding
native scope vector is 105 scopes/1,008 observations, still requiring its
own exact-head receipt and every existing prerequisite.
The artifact policy subsequently includes all twelve frozen publication
parameters. Their source-owned driver helper observes the actual owner, private
lifetime, store/validator/maintenance, authority and controls; no companion
session or cleanup transfer is introduced. Shared AS-13 witness ownership still
comes from the immutable primary-case helper, not duplicated proof bytes.
Local observation and independent locked replay pass 36 executions/188 image
correspondences with minimal inputs. Native admission now requires
105 scopes/1,018 observations and all prerequisites; it remains unadmitted.
Private original-image assignments are now nested by binding and exact runtime
identity, then role. Both histories deeply freeze this bounded structure before
execution. Ingestion requires the selected identity and exact role inventory;
flat, foreign-witness or cross-binding assignments cannot serve as fallback.
This permits truthful original authority shapes without inventing an unused
facade. Fifty-five single-owner metadata identities per provider are observed,
including exact query-corruption/continuation parameters and direct-construction
admission witnesses. The current one-observation policy also rejects extra
roots rather than accepting arbitrary passing provenance.
Minimal-input observation/replay pass 126 executions/638 image correspondences;
the expanded native path requires 230 foundations and 105 scopes/1,108
observations, still pending. Public entity/proof schemas remain unchanged.
Earlier full-input run `40167209164 @0005638` independently reproduced distinct
original and typed input digests across 105 scopes/990 observations and every
prerequisite. This admits only its earlier eight-original diagnostic, not these
expanded sources or qualifying profiles.
The following forest increment adds independently fixed multi-owner/reopen
topologies: three independent MP-29 roots; two MP-08 roots; two unrecognized
layout roots; a three-node MP-32 upgrade chain; two future/corrupt roots with one
child each; and one root/child for MP-34 and MP-35. Ingestion requires exact
counts/current-execution edges and distinct actual owner/store IDs, rejecting
missing/extra roots, foreign or wrong parents, and reused owners/stores.
All other classified witnesses retain their one-root/contract requirement.
The original producer's new overload separates previous identity continuity
from actual parentage, preserving existing signatures and genuine aliases
without fabricated reopen edges. Schema nodes observe the actual adapter owner
and underlying fixture authority; assertion/facade behavior is unchanged.
Observation failure during reopen disposes the newly transferred fixture before
rethrowing. No observer otherwise takes cleanup ownership.
Local observation/replay pass 140 executions, 162 records (158 original owners
and four contracts) and 818 image correspondences with SDK archive
`032389ce6626072e1d3b455d1af77779e6656f46f5cba1187df3dbdf591922c1`.
The configured-host witness adds two independent roots whose actual owners
are the composed modules, not additional fixture sessions; both admitted and
rejected-schema lifetimes retain original construction/assertion/disposal.
Artifact operational policy now includes 183 exact witnesses across publication, deletion,
reconciliation, read revalidation/destination failure, publication races, storage
failures, all frozen budgets and selected recovery cases. Exact source-owned
boolean argument names/values are preserved; provider selection rejects missing
assignments rather than defaulting multi-parameter Local rows to Object.
Their original drivers retain cleanup ownership.
Nine actual Local fresh-store reopen edges require exact per-node role-image
maps. Parent admission selects each immutable node by index; flat maps cannot
substitute for these different original/reopened owner images. Legacy common
role maps remain supported for the already classified metadata forests.
Both histories freeze every node before execution, and manifests include all
node images. Source records actual factory objects without taking cleanup
ownership. Same-object in-place reinitialization remains that original object;
the early-return reconciliation row and Object rows have no invented child.
Rejected store roots use actual provider-owned owner images; the decorated
authority uses the exact source-owned decorator image. Source-fixed facts and
non-provider parameters have explicit independently checked binding assignments,
without guessed Object fallback or invented provider parameters.
Actual metadata-composed sessions and configured-module owners use their real
HostAdapters images, actual interfaces and actual source-created controls.
Configured-host parameters each have two independent roots with shared reference
history; only exact Local reopen identities select heterogeneous child images.
Eight actual value/qualification contracts per binding observe the loaded
Abstractions contract type. Primary-case selection excludes non-applicable
durability rows, without turning contract validation into a durability pass.
Four provider-neutral authority/bridge facts additionally run in each explicit
artifact binding context. These and the two rejected-module parameters require
closed `original-owner` observations with exactly the actual owner role and no
parent edges. They cannot replace full original-instance roles or claim a
provider session. The copied-handle fact retains two independent actual roots
and shared reference history; owner reuse rejects. No unavailable session,
interface, control, provider parameter or cleanup ownership is invented.
Current local observation/replay pass 333 executions, 370 records
(354 original owners/sixteen contracts) and 2,122 image correspondences with SDK
archive `7651009db9b2ae1f857deb2973198d74edbf051e37514dbc4f013ddafe13dd26`.
The existing external-wrapper scope separately emits a hash-only, non-qualifying
parent receipt for sixteen actual source executions. It links immutable runtime
execution/proof IDs to producer/state hashes, the attempt/group/input document
and the same-run transfer measurement receipt. Source-selected booleans do not
substitute for independently checked kill/state/readback/retention/transfer
invariants. No session, component origin, child-start identity or category pass
is invented by this supplemental receipt.
Native admission requires 236 foundations and 107 scopes/1,317 observations,
pending. Private revision-2 evidence adds this closed kind; public schemas,
existing kind policies and typed-session origins are unchanged.

### Shared bounds

- Stable IDs: ASCII `[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}`. Digests:
  lowercase SHA-256 hex; NuGet SHA-512 additionally retained where used.
- Public JSON schema revision `1`, catalog revision `f07-v1`; the explicitly
  extended private execution proof uses revision `2` as described above. Unknown schema/status/
  fields, duplicate object keys, non-finite numbers and path traversal reject.
- At most 10,000 expanded results/profile, 128 witnesses/case, three attempts/
  case (default one), 1,024 bytes/safe diagnostic and 16 MiB/public report.
  Proof manifests permit at most 50,000 files and 256 MiB total; payloads,
  databases, raw logs and transfer bodies are not public evidence.
- Profile/catalog expansion beyond these bounds is an explicit future revision,
  not silent truncation. Large payload sizes do not raise report limits.
- Environment includes OS/version/architecture, SDK/runtime/native SQLite
  version when relevant, local filesystem type, runner image identity when
  applicable, safe PRAGMAs and measured free space. Private mount/root paths
  and arbitrary environment-variable dumps are forbidden.
- Configuration hashes bind a canonical synthetic allowlisted configuration;
  public digests are not computed from real secrets. No profile accepts a
  production connection string or pre-existing user store.

## State Transitions

**Run**: `Created -> Admitted -> Running -> Evaluating -> Complete`.
Admission failure or interrupted/over-budget work becomes `Incomplete`;
contract violations become `Failed`. Either can retain owned resources.
`Complete` is not synonymous with qualifying: all applicable results,
valid exclusions, proofs, input stability and settlement must pass evaluation.

**Case**: `Expected -> Running -> Passed | Failed | NotApplicable | Incomplete`.
`NotApplicable` is selected from the frozen catalog before execution and must
carry its precise environmental/capability reason. An attempted failure cannot
be relabelled excluded. A recovered retry remains failure-tainted in that run.

The single-controller `RuntimeCaseHistory` API selects a case's exact key,
witnesses and authorized exclusion from the independent catalog, never a
provider-selected expectation list. It captures parent monotonic boundaries,
admits actual transport records, rejects overlapping/replayed attempts and
execution UUID reuse, and preserves immutable prior attempts/witnesses/proofs.
Default attempt count is one; an explicit limit cannot exceed three. Invalid
provenance surfaces its closed error and appends a failed/incomplete observation
without inventing an execution. Catalog exclusions and interrupted attempts
likewise fabricate no witness. A later passing attempt cannot erase the
report-level failure taint. Outstanding separate catalog controls prevent a
runtime-only passing case; control-only cases and complete controller wiring
remain separate unfinished work.

**Ownership**: `Allocated -> Active -> Settling -> Released`, or
`Settling -> Retained -> Settling`. Only actual settlement/exit permits
`Released`; expiration/cancellation/observation timeout does not. Retained
resources block passing qualification and cannot be recycled by a new run.

**Evidence**: private observed witnesses -> safe validated projection -> sealed
manifest -> independent evaluation -> scope statement. Modifying bytes, inputs,
declarations or environment after sealing invalidates the projection. Reports
are technical evidence, not signatures or an in-process provider sandbox.
