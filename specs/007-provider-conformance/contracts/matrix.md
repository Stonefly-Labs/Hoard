# F-07 Finite Qualification Matrix

**Status**: Required future test inventory, not tested support. Catalog revision
`f07-v1` owns expansion; results cannot define or shrink it. Each listed
subvariant is an explicit expected key, not a single aggregate pass.

## Category Inventory and Claim Scope

| Profile/binding | Exact inherited cases | Required outcome/classes |
| --- | --- | --- |
| metadata/sqlite | MP-01..48 | 48 applicable passes, including nine real durable cases |
| metadata/memory | MP-01..48 | 39 passes; MP-36,38..45 explicitly `NotApplicable: non-durable fixture` |
| artifacts/local | AS-01..48 | 48 applicable passes, including AS-41..44 real local recovery |
| artifacts/object | AS-01..48 | 44 passes; AS-41..44 explicitly `NotApplicable: simulation: no durable restart` |

Exactly 192 inherited entries: 179 applicable passes and 13 explicit
non-applicability entries for a successful category baseline. This arithmetic
does not replace checking each case's required runtime witnesses/subproofs.
Keep all existing cases and later convergence regressions from the authoritative
[metadata matrix](../../005-metadata-persistence/contracts/acceptance.md) and
[artifact matrix](../../006-artifact-storage/contracts/acceptance.md).
MP-47/48 and AS-45..48 retain inherited evidence obligations; they do not
substitute for the new F-07 evaluator.

Metadata publication/authority and artifact deletion integration exercise all
four concrete pairings: `sqlite/local`, `sqlite/object`, `memory/local`,
`memory/object`. A named underlying runtime witness may serve multiple mapped
obligations only if every required parameter combination is observed.
QC-12's catalog names eight actual consumers per pairing: reference admission,
failed transaction, live references, lost acknowledgment, incarnation fencing,
held reader, foreign authority and shutdown. All 32 exact parameter rows are
mandatory alongside the seven QC controls. Diagnostic execution or catalog
presence alone does not establish qualification-origin integration admission.
The fresh qualification-only `original-integration` scope retains all 32 rows
under their actual Local/Object bindings. Three actual loaded images per row
and one independently reconstructed native command/source parent form its
current-attempt basis; no inherited AS row substitutes for a pairing/consumer.
Exact `9a5ebdb`/run40243784950's unchanged-head retry now admits all 32 rows
under one native source parent. This does not complete full profile acceptance.

QC-04 requires two corrected metadata identities and two corrected artifact
identities across their respective category profiles. A qualification-only
`mutation-repair` scope in each profile runs its fresh faulty family first,
requiring the fixed named assertion failures, then its unchanged corrected
family. Both sides share six pinned images, SDK/provider bytes and immutable
inputs. The independent source parent retains the original negative transport
and held command closure with ordered settled bounds; setup failures and
previous-attempt borrowing reject. Negative rows are retained source evidence,
not failed public witnesses. Local/model validation is not fresh Linux
qualification of these pairs.
Runtime source witnesses/completion/proofs are sealed only after child
settlement and rechecking their captured bytes; unsealed, changed or live-child
transport cannot substitute for the required readonly originals.

Metadata additionally executes all 132 exact F-07 common-consumer rows in a
fresh qualification-input private source scope covering both actual bindings.
Their original `full-metadata-binding` context, exact origin counts and typed
image/descriptor/reopen correspondence are independently reconstructed with
the six-image manifest and original native command/input closure. Admission
also requires identical admitted SDK image bytes in the shared Consumer
and frozen metadata wrappers, with the wrapper SDK pinned in the native input
map. These rows are not public QC-02 witnesses or replacements for frozen MP/convergence
parity. QC-02 remains `Incomplete`, the 128-witness bound is unchanged, and
fresh Linux admission of this control is pending. The older MP-47 marker
Consumer retains its distinct purpose.

The existing metadata `admission` and artifact `PublicationBoundary` Consumer
rows additionally require every mandatory logical hook omission to reject
before factory dispatch/allocation, then run the unchanged actual binding's
common assertion and original typed origin. Metadata covers ordinary and
legacy opening. Missing bindings reject before dereference, and claimed
logical `MP-21`/`AS-15` exclusions cannot bypass any mandatory hook.
The original 132 metadata/24 artifact identities and origin counts are preserved.
This coverage is not a public QC-05 witness or completed QC-05 qualification.
Separate dedicated hook-admission diagnostic families select two provider rows
per category with `QC-05` contexts, reusing those same assertions. They leave
the original 132/24-row selections unchanged. A qualification-only predeclared
`hook-admission` scope executes each complete family once and retains
independently reconstructed native controls,
including original readonly transports, typed origins, six images and held
commands. History retains these packets within existing quotas; exact Linux
admission is pending. Public QC-05 composition requires both original provider
rows, one original native graph parent and all four independently reconstructed
hook/binding/logical/durability obligation controls. Missing rows, parent or
controls remain `Incomplete`; no witness is relabeled or borrowed. The
create-new graph currently admits one attempt and rejects source reuse.
Modeled composition does not establish native or complete category qualification.

Packaged admission now also checks the complete 48-case sets for both
bindings and the exact nine memory/four ObjectSemantics exclusions, with all
other category/QC entries unexcluded. These expectations are independently
owned by the Consumer, not derived from binding capability claims.
Local SDK-catalog mutations for logical exclusion, durable reclassification
and missing authorized exclusions fail named catalog assertions; unchanged
Consumer rows pass. Exact-head native QC-05 admission and complete category
extraction/parity remain separate unfinished gates.

The full artifact binding diagnostic scope also executes the shared publication
empty/absence, unknown-length/real-EOF, expectation, unsupported-operation and
verified-duplicate consumers against both actual bindings. Its complete ten-row
family extends the preserved 24 rows to 34, with six pinned images including
the SDK and one actual typed origin per new row. Local complete-family parity
against the corresponding frozen wrappers includes a paired shared-assertion
mutation, not a faulty-provider qualification claim. Full QC-03 extraction,
native source admission and category qualification remain unfinished.

The next complete two-provider family adds ten destination-failure, exact
retry, conflicting-staged-length, deletion/recreation and held-reader exclusion
rows, bringing the diagnostic scope to 44 with all original identities and
six-image requirements preserved. The complete actual-binding and corresponding
frozen-wrapper families have matching local shared-assertion negative behavior.
No diagnostic row substitutes for full QC-03 extraction or native qualification.

Eight boundary-consumer rows plus two ordinary observer-error controls extend
the full scope to 54. Private staging, concurrent writers and lost acknowledgment
cover both bindings; visibility-before-ack is Local and independent direct
availability is Object, matching the unchanged shared assertions' original
scope. Expected fault registration does not excuse arbitrary observer failures.

Protocol/identity fixtures qualify declarations and lifecycle only. No
operational case inventory is invented for them. There are no remote-service
profiles in the initial catalog; requesting one is an explicit unsupported
invocation, never an automatic simulation selection.

## Fixture-Host Compositions

All packages use their actual local versions (initial repository baseline
`0.1.0`) and exact content hashes. Normal platform host/abstractions versions
are `0.1.0`; illustrative version-policy cases below are distinct.
Hosts use existing in-process ASP.NET Core TestHost and lifecycle/configuration
APIs, not a curated executable or public listener.

CP-01 bundles explicit protocol-one, SQLite metadata, Local artifacts and
identity fixtures. CP-02 replaces SQLite/Local with memory/ObjectSemantics in a
separately packaged host while keeping shared consumer code identical.
CP-03 selects two protocols and two distinct identity schemes with one metadata
and artifact provider; it makes no authentication/protocol-operation claim.
Enabled provider selections are configured explicitly; no test relies on
default or fallback selection.

| ID | Input or controlled subvariants | Expected observable result |
| --- | --- | --- |
| CP-01 | Bundled fixture baseline | Build/start/initialize/readiness/stop succeeds; only selected modules active |
| CP-02 | Separate package-only replacement host | Same consumer/start/stop agreement, different singleton implementation packages |
| CP-03 | Two protocol and two identity fixtures | Permitted multiplicity, no route/identity ownership conflicts |
| CP-04 | Duplicate stable ID | Reject before construction/resource work |
| CP-05 | Enabled unknown/unregistered ID | Same preactivation rejection, actionable safe rule |
| CP-06 | Missing required dependency | Same; no substitution |
| CP-07 | Enabled dependency cycle | Same, even when registrations are reordered |
| CP-08 | Required capability absent | Same, not weaker fallback behavior |
| CP-09 | Metadata count zero / two | Both reject before construction |
| CP-10 | Artifact count zero / two | Both reject before construction |
| CP-11 | Conflicting actual route ownership | Reject during mapping before route publication, initialization, workers/connections, readiness or request admission |
| CP-12 | Disabled observable module; optional target absent / registered-disabled | Zero construction/routes/workers/connections; unavailable capability and no active dependency edge |
| CP-13 | Enabled optional compatible / incompatible | Compatible passes; incompatible rejects, never auto-disables |
| CP-14 | Required initializer fails | Not ready, actual safe failure, owned cleanup observed |
| CP-15 | Cancel during initialization / readiness assessment | No premature admission or ready success; exact retained/settled state |
| CP-16 | Initializer ignores cancellation until controlled release | Finite caller return, bounded retained owner, blocked readiness, eventual real settlement |
| CP-17 | Shutdown faults / non-cooperative shutdown | Explicit failure/incomplete cleanup; no false disposal or resource reuse |
| CP-18 | Required provider recovery fails | No ready state or alternate provider activation |
| CP-19 | Authority identity mismatch / missing mandatory store guarantee | Admission rejects before store I/O |
| CP-20 | Valid explicit stop/restart; request/config change while active | Restart path succeeds after settlement; no hot provider replacement |

For CP-04..13, each rejected subvariant has a paired valid repair changing only
its declaration/selection. Instrument module constructors, hooks, route requests,
worker starts and connection attempts independently; checking only route count
does not prove disabled construction/connection absence. CP-14..20 verify actual
readiness/admission and ownership through existing APIs, not reported flags.
CP-11 changes only the conflicting mapped route in its repair. Construction and
mapping are necessary to obtain actual route patterns; neither is reported
absent. Its rejected composition publishes no routes and starts no initialization,
workers, connections or request admission. Malformed/duplicate responsibility
IDs are independent preconstruction declaration checks, not CP-11 proof.
The composition profile also retains the complete applicable F-02/F-03/F-04
regression inventories from their existing validation entry points.

## Version/Policy Expansion

Retain all [F-01 C-01..23 classifications](../../001-provider-contracts/contracts/compatibility.md#classification-acceptance-matrix),
including source/binary/behavioral change classification cases. Policy-only
release classification is not presented as runtime behavior evidence.
For each of the three independent axes `host`, `abstractions`, `dependency`,
expand the following numeric/range rows (other axes held valid):

| Range | Candidate | Flag | Expected |
| --- | --- | --- | --- |
| `[0.1.0,0.2.0)` | `0.1.0` | false | Accept inclusive lower |
| `[0.1.0,0.2.0)` | `0.2.0` | false | Reject exclusive upper |
| `(0.1.0,0.2.0]` | `0.1.0` | false | Reject exclusive lower |
| `(0.1.0,0.2.0]` | `0.2.0` | false | Accept inclusive upper |
| `[0.1.0]` | `0.1.0+build.7` | false | Accept exact/build metadata |
| `[0.1.0,0.2.0)` | `0.1.1-rc.1` | false / true | Reject / accept prerelease |
| `[0.1.1,0.2.0)` | `0.1.1-rc.1` | true | Reject below stable lower |
| `[0.1.1-rc.1,0.1.1]` | `0.1.1-rc.2` | false / true | Reject / accept; range text is not opt-in |
| `[0.1.0,0.2.0)` | `0.2.0-rc.1` | false / true | Reject / accept according to explicit flag |
| `[0.1.1-RC.1]` | `0.1.1-rc.1` | true | Accept case-insensitive precedence |
| empty; `1.*`; `[0.1.0,)`; reversed; empty-open; `[0.1]` | `0.1.1` | false | Reject each malformed/disallowed range |
| `[0.1.0,0.2.0)` | `0.1.0.0`; malformed canary | false | Reject each malformed candidate safely |

Host and abstraction prerelease flags are independent; enable only one with
both candidates prerelease and require rejection on the other. Dependency
rows run with required and enabled optional targets. Also verify absent and
registered-disabled optional targets at an incompatible version confer no
capability and do not themselves reject. Prerelease module version never
grants a platform flag. Evaluate through actual runtime validation plus the
policy classifier where applicable; do not implement a new range evaluator.

## Source, Binary and Architecture Inventory

| Family | Required paired checks |
| --- | --- |
| Unchanged source | Existing common consumer and provider implementer sources compile against candidate packages without edits, including all four category bindings |
| Retained binary | Frozen pre-F-07 consumer/provider binaries plus existing pre-F-02..F-06 marker/lifecycle/configuration/discovery consumers run without recompilation; bind actual candidate assemblies |
| Intentional source break | Remove/change consumed required API; exact unchanged-source build fails for intended symbol; compatible counterpart builds |
| Intentional binary break | Remove referenced member or change assembly identity; actual retained binary invocation fails for intended incompatibility; compatible candidate succeeds without replacing old binary |
| Architecture | ARCH-001..008: isolated negative plus permitted counterpart per existing rules, full graph/assets/nuspec/public surface/IL inspection |
| Architecture special paths | Declared-unused edges, transitive helper and nested contract leakage; allowed Identity -> Hosting -> Core; direct/helper Identity -> Core even alongside allowed path, both edge traversal orders |
| Inspection failure | Missing graph, unresolved type, ambiguous ownership and incomplete required scans fail closed, never empty success |

The F-07 pre-extraction baseline is exact F-06 merge
`9389016c0285c79f6f515f59805a5a41c69b0767`. Existing older-feature baselines
retain their recorded revisions. Baseline package/source/recipe/binary hashes
are frozen before candidate execution. Candidate source cannot supply an
edited baseline. The newly introduced SDK has no fictional old release; its
initial API/consumer becomes a future compatibility baseline only.

## Unsupported Choices and Reporting

Only named rows and their catalogued subvariants qualify. Do not infer the
Cartesian product of protocol/identity schemes, arbitrary provider versions,
production SQLite/filesystem packages, remote services, native clients,
Windows/network filesystem, OS/power-loss recovery or multi-node behavior.
The [48 F-07 proof obligations](acceptance.md) cover harness/evidence correctness
and each required matrix family. Every report lists its exact expanded inventory,
actual versions/environments, exclusions and limitations rather than a generic
provider-wide certification badge.
