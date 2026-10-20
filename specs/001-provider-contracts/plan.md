# Implementation Plan: Platform Package Boundaries and Provider Contracts

**Branch**: `feature/001-provider-contracts` | **Date**: 2026-10-20 |
**Spec**: [spec.md](spec.md)

**Input**: `specs/001-provider-contracts/spec.md` (F-01), including its
no-question clarification review.

**Status**: F-01 compile-only implementation now exists. The original planning
sections below retain design rationale and historical stage gates; the
implementation evidence section records current delivery and limits. There is
no runnable cache, working provider, UI, product CI/CD, or cloud resource.

## Summary

Establish independently consumable, versioned provider declarations and public
composition seams without implementing a caching engine or production provider.
Use BCL-only abstractions, provider-free Core/Application boundary libraries,
and a small Hosting registration API. Prove the seams during implementation
with five separately packaged fixture providers spanning four families, a
compile-only custom host, and architecture checks with isolated rejection cases.

[Research](research.md) selects .NET 10 SDK packaging, explicit metadata/type
registration without activation, bounded compatibility intervals with separate
prerelease opt-in, and test-only assembly/dependency inspection. Detailed
lifecycle, selection validation, store operations, identity behavior, HTTP
discovery, reusable conformance, and native-client behavior stay in later
backlog features.

## Technical Context

**Language/Version**: C#, nullable enabled, `net10.0`; SDK baseline `10.0.100`
with stable-only `latestFeature` roll-forward. No multi-targeting in F-01.

**Primary Dependencies**: Abstractions and Core: BCL only. Hosting:
Microsoft.Extensions.DependencyInjection.Abstractions 10.0.13. No ASP.NET HTTP
surface is needed for registration-only F-01. Research records exact test-only
pins; none are added at this stage.

**Storage**: None. Module declarations are immutable in-memory metadata;
local NuGet feeds and build outputs are temporary acceptance artifacts, not
runtime data or package publication.

**Testing**: Existing Python tooling suite now. Planned xUnit/VSTest projects
for contract/registration cases, compatibility examples, architecture scans,
independent package consumers, and fixture replacement; Mono.Cecil and
NuGet.Versioning stay test-only. SDK formatting/analyzers cover future C#.

**Target Platform**: SDK builds on Linux, macOS, and Windows; no production
OS/architecture support matrix or deployable runtime is introduced.

**Project Type**: NuGet library foundation plus a compile-only ASP.NET Core
custom-host example. The example must not run or listen.

**Performance Goals**: No request-throughput, memory, or latency claim.
Inspection and registration must not construct provider services or perform
external I/O; package tests need no live service.

**Constraints**: Acyclic resolved package graph; zero concrete providers,
EF Core, or SDK dependencies in Core; no provider-private types in public
contracts/slices; no source sharing or friend access in fixture consumers.
No operational methods whose guarantees belong to F-05/F-06/F-08.

**Scale/Scope**: Four platform libraries, four provider families represented by
five independent fixture packages, one custom-host source example, and focused
unit/architecture/composition checks. Curated Host and real provider directories
remain reserved.

## Constitution Check

The ratified [constitution](../../.specify/memory/constitution.md) applies.
The pre-research assessment found no violation: the spec requires compile-only
foundations and explicitly assigns operational work to later features. The
post-design assessment below is a design review, not passing implementation
evidence or reviewer-owned checklist approval.

| Gate | Before research | After design / evidence |
| --- | --- | --- |
| I: Cache-first, personal simplicity | Pass: no publishing-registry feature or external service needed | Pass: fixtures/local feed only; no cloud, DB, upstream, or runnable-cache claim |
| II: Neutral versioned contracts and composition | Pass: ownership follows ADR-0001 | Pass: [public API](contracts/public-api.md) keeps Abstractions BCL-only; registrations record explicit types without activation; [compatibility](contracts/compatibility.md) covers all three version axes |
| III: Slices and shared invariants | Pass: no endpoint behavior in scope | Pass: [boundary rules](contracts/architecture-rules.md) reject private/provider leakage and cross-slice handlers; no per-provider cache algorithm |
| IV: Verified bytes, bounded work, recovery | Pass: no I/O operations introduced | Pass: family markers make no rename, transaction, publication, or deletion promise; operational guarantees remain mandatory for later contracts |
| V: Security at network introduction | Pass: no network service introduced | Pass: compile-only host never runs; declarations contain references/descriptions, not secrets; in-process code is trusted, not sandboxed |
| VI: Evidence before claims | Pass: spec has independently testable outcomes | Pass: traceability and negative-check matrix below; package-only consumers, provider-free build, and swap proof required before implementation acceptance |
| VII: Accessible static console | Not applicable: no UI | Preserved: future UI consumes management API/capabilities only; no Next.js or Node dependency added |
| VIII: Compatibility and reversible operations | Pass: public compatibility is in scope | Pass: breaking stable/pre-1.0 transitions, prereleases, migration obligations, and unsupported cases are specified; no schema/infra/runtime migration |
| Workflow and technology constraints | Pass: ratified constitution on main; recorded feature branch and directory used | Pass: only planning artifacts now; tasks/checklists/reviewer approval and implementation remain gated; architecture review required before this design handoff |

No constitutional exception or architectural departure is requested.

## Project Structure

### Documentation (this feature)

```text
specs/001-provider-contracts/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- public-api.md
|   |-- compatibility.md
|   `-- architecture-rules.md
`-- checklists/requirements.md
```

At the original planning checkpoint `tasks.md` and custom checklists were absent.
They were subsequently generated/reviewed through their separately authorized stages.

### Planned implementation layout (not created by planning)

```text
Hoard.slnx
global.json
Directory.Build.props
Directory.Packages.props
src/
|-- Hoard.Abstractions/           # declarations and family seams
|-- Hoard.Core/                   # provider-free library boundary, no engine yet
|-- Hoard.Hosting/                # explicit registration records
`-- Hoard.Application/            # boundary only, no management endpoint
examples/
`-- CustomHost/                   # package-only compile proof, never run
tests/
|-- unit/Hoard.Foundation.Tests/
|-- architecture/Hoard.Architecture.Tests/
|-- integration/Hoard.Composition.Tests/
`-- fixtures/
    |-- providers/                # Protocol, Metadata, Artifact.One, Artifact.Two, Identity
    `-- architecture/             # isolated positive and forbidden-reference inputs
scripts/
`-- validate-foundation.sh        # bounded local package/build/test orchestration
```

**Structure Decision**: Use the architecture's existing reserved boundaries.
F-01 adds only four platform library projects during implementation; it does not
populate `src/Hoard.Host`, real providers, or `apps/web`. Fixture consumers are
built outside the source graph in temporary directories using explicit package
references. Test outputs and feeds are ignored; central dependency pins and
applicable `packages.lock.json` files are tracked. No product CI is introduced.
The solution contains platform libraries and test projects, not package-only
fixtures or the example: those are built after local packing. Composition
tests consume the isolated build outputs prepared by the orchestrator rather
than recursively invoking it.

## Phase 0: Research

[research.md](research.md) records decisions, rationale, alternatives, upstream
sources, and pinned dependency choices. The key design choice is a deliberately
small declaration/registration seam; no unresolved technical or product
clarification remains. The plan does not treat future semantic operations as
missing F-01 functionality.

## Phase 1: Design and Contracts

- [data-model.md](data-model.md): immutable declarations, compatibility,
  registration records, and architecture evidence; no database model.
- [contracts/public-api.md](contracts/public-api.md): family seams, metadata
  shapes, registration-only API, ownership, and later-feature handoffs.
- [contracts/compatibility.md](contracts/compatibility.md): version/range policy
  and stable, pre-1.0, missing, out-of-range, and prerelease examples.
- [contracts/architecture-rules.md](contracts/architecture-rules.md): allowed
  graph, inspection inputs, rejected cases, and actionable diagnostics.
- [quickstart.md](quickstart.md): future reproducible package-only validation,
  build/format/test commands, expected evidence, and honest support limits.

There is no HTTP/OpenAPI contract in this feature. F-04 will specify discovery;
the static UI constraint is preserved without designing UI endpoints here.

### Requirement and acceptance traceability

These are planned proof obligations, not executed product checks or tasks.
Each negative fixture must be observed failing its named rule before the
permitted counterpart is accepted; do not weaken checks to make fixtures pass.

| Requirements / outcomes | Design | Planned focused evidence |
| --- | --- | --- |
| FR-001, FR-002, FR-013 / SC-001 | Four family markers, BCL-only public metadata | Five independently packed providers consume platform packages with no source/friend access |
| FR-003 / SC-001 | Core references Abstractions only | Restore/build Core alone in a clean work directory and inspect its complete resolved dependency closure |
| FR-004, FR-005, FR-014 / SC-003 | Acyclic graph plus assembly/public-surface/IL checks | Permitted graph passes; every `ARCH-*` negative case rejects with source, target, rule, and transitive path where applicable |
| FR-006, FR-007 / SC-004 | Explicit declaration/type registration | Package-only custom host builds without copied platform code, private APIs, activation, or external services |
| FR-007, FR-013 / SC-002 | Two independent artifact fixtures | Swap only host package reference and registration type/declaration; rebuild both variants, verify no Core/unrelated source change |
| FR-008, FR-009, FR-016 / SC-006 | Curated/custom and trust/compile-only documentation | Review all example/support text; no fixture described as functional or certified; no dynamic-loading/install API |
| FR-010 | Immutable static declaration, separate registration | Inspect all descriptor fields without constructing fixture provider; constructor sentinel remains untouched |
| FR-011, FR-012 / SC-005 | Compatibility policy and example matrix | Classify C-01 through C-23, including binary/behavioral breaks, prerelease gates, enabled optional conflicts, and unavailable installed/registered-but-disabled targets |
| FR-015, FR-017 | Responsibility matrix and category declarations | Review all four seams for invariant ownership; no auth-to-permission, rename, transaction, or operational-support implication |

### Validation and documentation handoff

At this planning checkpoint run the existing Python tooling suite and diff/
artifact checks only. Before handoff obtain `hoard-architecture-review` on the
provider-boundary design and resolve significant findings. That review does not
approve custom requirements-quality checklists or replace later code review.

**Design review, 2026-10-20**: `hoard-architecture-review` found no confirmed
violations or unresolved F-01 design questions. It explicitly left actual
dependency/API compliance, independent package/replacement proofs, and runtime/
console guarantees unverified until their implementation checks exist. No
custom checklist was approved. The existing tooling suite passed all 14 tests;
pinned feature-path resolution and whitespace checks passed.

**Approved review follow-up, 2026-10-20**: After the checklist review found
RQ-01, the user approved a fail-closed optional-dependency policy. FR-012, the
declaration model, and the compatibility policy now require an enabled optional
target to satisfy its range/prerelease flag or make the composition unsupported,
without automatic disablement/substitution. Installed/registered-but-disabled
targets are unavailable and confer no integration/capability claim. C-19 through
C-23 add the classification obligations; the quickstart now requires all 23
cases. This changes no signatures, package graph, or F-01 runtime scope.
The [review record](checklists/compatibility.md#rq-01-incompatible-present-optional-dependency)
tracks the criterion's re-evaluation separately from scheduled stage progress.

At implementation, introduce the commands in the quickstart and require them to
pass before claiming F-01 acceptance. Update README, `docs/DEVELOPMENT.md`,
`src/README.md`, `tests/README.md`, and the example guide when those capabilities
actually exist. No native NuGet restore, production provider conformance, HTTP
startup, resilience, or performance claim follows from these checks.

At this stage README and development guidance link this design. The charter,
product specification, architecture/diagrams, ADR-0001, constitution, and master
backlog remain unchanged because this design applies their existing boundaries.
Reserved source/test guides remain accurate: no product projects or commands
are created now. There is no existing product example to update.

### Compatibility and rollback

The planned initial platform contract/package version is `0.1.0`, for local
acceptance packages only; it creates no release tag or public NuGet publication.
A later stable API requires separate release authorization. Later operational
contract changes must make explicit version transitions and provide migration
guidance. There is no runtime, data, infrastructure, or permissions migration
at this checkpoint; rollback is a reviewed documentation/checkpoint revert.

## Complexity Tracking

None. The planned library boundaries are mandated by the existing architecture;
test-only inspection and package fixtures are directly required acceptance
mechanisms, not a new runtime extension framework.

## Implementation Evidence (2026-10-20)

F-01 now delivers four .NET 10 platform libraries, declaration/family contracts,
registration-only Hosting, three acceptance test projects, five independent
provider fixture packages, and the package-only custom-host example. All packages
are local `0.1.0` proof artifacts, not published products. Core and Application
are empty dependency boundaries; no operational methods or working provider
have been invented. Source declarations and the written policy retain the
approved optional-dependency behavior; runtime enforcement remains F-02/F-03.

### Acceptance and traceability

The original traceability table and [tasks](tasks.md#requirement-and-acceptance-traceability)
map every one of the 17 FRs and six SCs. The concrete evidence is:

| Requirement / outcome | Implemented proof and observed result |
| --- | --- |
| FR-001, FR-002, FR-010, FR-013 / SC-001 | [Declaration consumers](../../tests/fixtures/declarations/) accept immutable required/init-only shapes and explicit empty arrays, reject missing required fields/mutation/mutable collection assignment, and can represent unsupported inputs for later validation. Five [provider packages](../../tests/fixtures/providers/) compile/pack independently; five family-typed consumers cover four families plus Artifact.Two, with no source/friend/import access. |
| FR-003 / SC-001 | [Core independence test](../../tests/integration/Hoard.Composition.Tests/CoreIndependenceTests.cs) inspects a separately copied, restored, built Core with only Abstractions reachable. Actual project/asset closure is Abstractions/BCL only. |
| FR-004, FR-005, FR-014 / SC-003 | [Architecture tests](../../tests/architecture/Hoard.Architecture.Tests/ArchitectureRuleTests.cs) reject all ARCH-001 through ARCH-008 inputs: direct/unused framework and transitive/project/packed dependencies, direct/recursive/attribute/constraint/event leakage including prohibited BCL query/connection/transaction shapes, unrelated/same-family providers, private slice SDK use, same-assembly/async/nested/external slice calls, and synthetic project/package cycles. The permitted graph and eight real source/provider/host graphs pass. |
| FR-004, FR-005, FR-014 / SC-003 | [Completeness failures](../../tests/architecture/Hoard.Architecture.Tests/InspectionFailureTests.cs) reject missing assembly/assets/references, unknown ownership, duplicate ownership, empty manifests, unmapped slices, unresolved inputs, and omission of each of the eight required real scans with distinct inspection errors. Framework ownership uses actual resolved reference-pack provenance, not prefixes. |
| FR-006, FR-010 / SC-004 | [Registration tests](../../tests/unit/Hoard.Foundation.Tests/ModuleRegistrationTests.cs) prove caller collection/fluent identity, exact appended metadata/type records, duplicate preservation, standard null failures, no operational registration/factory, and no invocation of the throwing constructor. |
| FR-006, FR-007, FR-008, FR-009, FR-013, FR-016 / SC-002, SC-004, SC-006 | [Host tests](../../tests/integration/Hoard.Composition.Tests/CustomHostTests.cs) compile baseline/Artifact.Two copies with only artifact reference/registration edits and a derived lock change. Platform/unrelated provider source hashes are unchanged. Neither host is run; no Build/Run/Start/mapping or private/source imports exist. [Guide](../../examples/CustomHost/README.md) documents exact reproduction and limits. |
| FR-011, FR-012 / SC-005 | [Compatibility examples](../../tests/unit/Hoard.Foundation.Tests/CompatibilityExamplesTests.cs) and [release obligations](../../tests/unit/Hoard.Foundation.Tests/ContractChangeExamplesTests.cs) classify every C-01 through C-23, plus bound/normalization/availability edges. Required-member source fails with CS0535; the old binary caller fails with MissingMethodException against the removed API while the migrated source compiles. Behavioral tightening is explicitly a written breaking obligation, not a store-conformance claim. |
| FR-002, FR-013 / SC-001, SC-004 | [Package tests](../../tests/integration/Hoard.Composition.Tests/ProviderPackageTests.cs) compare packed dependencies to exact-target assets; every consumed local archive has matching local-feed source metadata and SHA-512 bytes. All 46 checked-in projects have locks. Generated family consumers and the derived replacement host bootstrap/replay their own temporary locks. |
| FR-008, FR-009, FR-015, FR-016, FR-017 / SC-006 | [Provider guide](../../docs/PROVIDERS.md), README, source/test guides, quickstart and example explicitly reserve shared invariants/authorization/cardinality and named F-02 through F-08 handoffs. Fixtures have Fixture provenance and no operational capabilities/configuration/endpoints/health promises. Curated configuration is distinguished from custom reference/register/rebuild/redeploy/restart. |

The negative-first observations were: declarations failed with missing public
types (CS0246); package acceptance failed on missing required build evidence;
architecture tests failed on the absent inspector; registration failed on the
missing Hosting API; compatibility tests failed on the absent evaluator/change
examples. Implemented rejection fixtures then failed for their named diagnostic/
rule while permitted counterparts passed. Archive regressions first failed on
the missing canonicalization helper, then passed. Review-follow-up scan
regressions first failed to compile on the missing exact-coverage gate; all
five added forbidden graphs now reject for their intended rule.

### Exact checks and measured scope

- `bash scripts/validate-foundation.sh --update-locks` — passed after the
  reproducibility correction; bootstrapped applicable locks and fresh-cache
  locked replay, Release builds/analyzers, source and standalone SDK formatting,
  Core isolation, platform/provider packs, family consumers, both hosts,
  source/binary break inputs, and all acceptance tests.
- `bash scripts/validate-foundation.sh` — passed independently in fresh private
  directories/caches without lock updates; 81 .NET tests: 42 foundation,
  36 architecture, three composition; zero failed/skipped. Repeated clean
  locked replay passed after canonicalization, the consumer-lock audit, and
  all three architecture-review corrections.
- `python3 -m unittest discover -s tests/tooling -v` — passed all 17 tests
  (the original 14 plus three focused archive-envelope regressions).
- `git diff --check` — passed.
- `dotnet list Hoard.slnx package --vulnerable --include-transitive --format json`
  — no known vulnerable packages at assessment; exact pins/license and
  transitive-license evidence are in [research](research.md#implementation-dependency-and-tooling-assessment-2026-10-20).
- Local documentation file/anchor audit — passed 117 checks across 14 affected
  Markdown files; all reviewer-owned and built-in checklist files remain unchanged.

The default script restores dependencies before any build, has explicit source
mapping, ten-minute subprocess timeouts, and fails closed on missing proof
inputs. It uses a Python standard-library helper for copying/hashing/ZIP/XML/
JSON and a Bash wrapper for prerequisites/resolved private-directory cleanup.
No test recursively invokes it or loads provider assemblies for execution.
The tiny synthetic compatibility binary caller is intentionally executed;
web hosts and providers are not.

### Necessary implementation details and review

Fresh locked replay found SDK pack ZIP timestamps/OPC IDs were not reproducible
even with `Deterministic=true`. Local unsigned Hoard archive envelopes are now
canonicalized before restore, preserving DLL/nuspec/core-property bytes.
Focused Python regressions prove envelope reproducibility/payload preservation
and reject signed/external/incomplete inputs. Local packages also normalize
compiled paths and omit Git revision stamps. No hash check, source mapping,
locked restore, or payload comparison was disabled. Compiler changes altering
payloads still require reviewed lock regeneration. This is bounded acceptance
tooling, not a release packaging/signing pipeline.

The compile-only web example disables SDK package pruning so its explicit
packed dependency graph remains inspectable; this does not introduce runtime
behavior. No approved dependency pin was replaced and no test/version/scanner
package enters runtime dependencies.

Required implemented-graph `hoard-architecture-review` completed. It identified
three medium-severity gaps in the acceptance machinery, not concrete-provider
coupling in the four delivered libraries. All were corrected before handoff:

| Finding | Correction and regression evidence |
| --- | --- |
| Unused ASP.NET framework references were classified but not connected to the consuming project. | Resolved framework assemblies now create dependency edges; explicit framework declarations require matching resolved inputs. Empty Abstractions/Core fixtures with only unused ASP.NET references reject under ARCH-001/ARCH-002. |
| The BCL allowance admitted explicitly forbidden query/connection/transaction contracts. | Exact BCL query/connection/transaction identities are rejected before the general allowance, preserving recursive expansion. Direct query, nested query, and connection-plus-transaction fixtures reject under ARCH-004. |
| A nonempty real-scan list could omit mandatory proof graphs. | The manifest names exactly eight required scans and rejects missing/duplicate identities. Eight omission regressions independently remove platform, each provider, and each host; every omission is an inspection error. |

The full bootstrap/fresh locked replay and all 81 acceptance tests passed
after these changes. No unresolved review finding or design question remains.
Reviewer-owned checklist markers remain unchanged; this is not self-approval
or a replacement for later convergence/finalization review.

### Documentation, operational limits, and rollback

README, development/source/test guides, provider author guide, custom-host guide,
quickstart, declaration/API/acceptance status headers, research, and task status
now distinguish actual compile-only APIs from later behavior. The charter,
product specification, architecture/diagrams, ADR-0001, constitution, master
backlog, infrastructure/release guides, and reserved UI/provider guides are
unaffected: implementation follows their existing ownership/graph, introduces
no lifecycle/store/protocol/network/UI behavior, changes no governance/backlog
dependency, and provisions/publishes/deploys nothing. The architecture's
operational sketches remain future work rather than new F-01 APIs.
The final SC-006 audit checked the README, provider author guide, example guide,
fixture declarations, and evidence above against all 17 FRs and six SCs.
Every delivered fixture remains compile-only with Fixture provenance and empty
operational capability/configuration/endpoint/health declarations. No runtime,
native-client, production-support, certification, or release claim was added.

There is no data/schema/configuration/permissions migration. Rollback is a
reviewed source change with matching lockfiles. The wrapper removes only its
own resolved temporary directory; feeds/caches/evidence/binaries remain
untracked. No source release, NuGet publication, cloud apply, or merge is
authorized. Passing this implementation does not certify provider behavior,
prove native-client restoration, or complete the feature: convergence,
finalization, authorized merge, and the merged progress checkpoint remain.

### T058 Implementation Follow-up (2026-10-20)

The first convergence assessment found one HIGH partial gap against FR-004,
FR-014, US2/AC1 and SC-003: the dependency inspector rejected the permitted
`Identity -> Hosting -> Core` closure. T058 now corrects that acceptance-tool
behavior; no platform library, public API, runtime dependency, or provider
operation changed.

Identity-rooted traversal records whether its first edge reaches Hosting and
keeps that visit state separate from other paths to the same node. Core is
allowed through the approved Hosting composition, not directly or through an
unrelated SDK/helper. Other rules still apply throughout both traversals;
concrete-provider targets, forbidden Core dependencies, and cycles remain
rejected. Separating visit states prevents the permitted route from hiding an
alternative forbidden route.

The permitted fixture consumes the actual local `Hoard.Hosting` package and
calls its approved registration API. Two isolated negatives include Hosting
alongside either a direct Core package reference or an SDK-owned helper that
references Core. Five added architecture cases cover the positive, both
negatives, and normal/reversed edge-order assertions for the forbidden helper
path. The four new fixture projects carry generated/reviewed locks; all 50
projects now have locks, and existing project locks/platform package hashes
are unchanged.

- `bash scripts/validate-foundation.sh --phase architecture --update-locks`
  before the inspector correction: expected regression failure, three failed
  and 29 passed, zero skipped. The positive reported ARCH-008 for the approved
  Hosting path; both order checks exposed the hidden helper path. Fixture
  lock bootstrap/replay completed before those intended test failures.
- `bash scripts/validate-foundation.sh` after correction: passed fresh default
  locked acceptance, all 86 .NET tests (42 foundation, 41 architecture, three
  composition), zero failed/skipped, source/standalone formatting and analyzers,
  isolated Core, five independent providers, both hosts, all eight architecture
  rules, and all 23 compatibility cases.
- `python3 -m unittest discover -s tests/tooling -v`: passed all 17 tests.
- `git diff --check`: passed.
- Task/lock/document audit: all 58 tasks complete with unchanged task bodies,
  specification, reviewer checklists, platform sources and existing locks;
  all 50 projects carry locks; 108 local links across eight affected Markdown
  files resolve.

A narrowly scoped read-only `hoard-architecture-review` found no actionable
findings or unresolved T058 design questions. It confirmed the restricted
Hosting path and independent visited states; execution evidence is the parent
acceptance run above, not a claim by the reviewer.

README, development/provider/test guides, the quickstart and architecture
acceptance contract describe the corrected rule. The specification, public
API/declaration/compatibility contracts, research, original task bodies and all
reviewer-owned checklists are unchanged. Charter, product specification,
architecture/diagrams, ADR, constitution, backlog, source/custom-host guides,
and infrastructure/release guidance need no changes: ownership, product
packages, registration APIs, trust/operational limits, and workflows are
unchanged. No new external dependency, migration, publication, deployment, or
infrastructure action occurred. Rollback remains a reviewed source change with
matching fixture locks.

All 58 tasks were checked at that checkpoint. The next stage was another
separately authorized convergence assessment, not finalization or a
clean-convergence/feature-complete claim.

### Finalization Acceptance (2026-10-20)

The separately authorized follow-up convergence assessment found zero missing,
partial, contradictory, or unrequested work at any severity. It assessed all
17 functional requirements, six buildable success criteria, 15 story acceptance
scenarios, nine edge cases, 12 grouped plan decisions, all 58 tasks, and eight
constitutional principles. Its report is retained in
[PR #4](https://github.com/Stonefly-Labs/Hoard/pull/4). No task was appended.
Finalization verifies that resulting scope and evidence; it does not implement
another feature or repeat a scheduled convergence stage.

| Finalization gate | Evidence / result |
| --- | --- |
| Requirements and acceptance traceability | All 17 FRs and six SCs map to the implemented proofs in [Acceptance and traceability](#acceptance-and-traceability) and [tasks](tasks.md#requirement-and-acceptance-traceability); all 58 tasks remain complete. |
| Independent contracts and Core | Fresh full acceptance builds Core with only Abstractions/BCL reachable, packs all five independent four-family fixtures, compiles their package-only consumers, and verifies local-feed source/SHA-512 provenance. |
| Public composition and replacement | Both package-only hosts compile; only artifact composition and its derived lock change. Platform/unrelated-provider hashes remain unchanged. Registration and metadata inspection never construct the throwing provider. Neither host is run. |
| Architecture and compatibility | All ARCH-001 through ARCH-008 rejection/permitted pairs, exactly eight real scans, inspection failures, C-01 through C-23, and intended source/binary break proofs pass. T058 accepts Identity through Hosting without masking direct/helper Core paths, in either edge order. |
| Reviewer-owned requirements gate | Existing architecture 20/20 and compatibility 18/18 approvals remain unchanged. Finalization neither re-approves these checklists nor treats them as product certification. |
| Required architecture review | The original implemented-graph review and its three resolved findings are recorded above. The scoped T058 review found no actionable finding or unresolved question. `git diff --exit-code 54ace9b..HEAD -- src tests scripts examples Directory.Build.props Directory.Packages.props Hoard.slnx global.json` passed before the finalization commit: no implementation change since that reviewed checkpoint requires another review. |
| Support and constitutional limits | Fixtures remain compile-only, with Fixture provenance and no operational capability promises. All eight principles remain satisfied within F-01 scope; cache/network/console/store/identity behavior stays with its named later feature. No architectural exception or governance change is requested. |

Fresh checks for finalization:

| Exact command / check | Result |
| --- | --- |
| `bash scripts/validate-foundation.sh` | Passed default locked replay without lock updates: all 86 .NET tests (42 foundation, 41 architecture, three composition), zero failed/skipped; Release builds/analyzers, source/standalone SDK formatting, isolated Core, independent package/host and all architecture/compatibility/declaration/registration proofs. |
| `python3 -m unittest discover -s tests/tooling -v` | Passed all 17 tests. |
| `dotnet list Hoard.slnx package --vulnerable --include-transitive --format json` | Seven source/test projects assessed; zero known vulnerable direct/transitive package entries and zero assessment errors. This dated result is not a future guarantee; dependency pins/licenses remain as recorded in research. |
| `git diff --check` | Passed. |
| Documentation/artifact audit | Passed 149 local file/anchor checks across 18 documents; all 50 project locks remain tracked, 58 task bodies/markers and all three checklist files are unchanged. PR headings/comments/checklist ordering follow the repository template. |

Finalization updates README/development stage status, the specification's
review status, this acceptance record, the shared checkpoint, and the PR
handoff. Requirements, public APIs, dependency graph, task bodies, and checklist
approvals do not change. Provider/source/test/custom-host guides, quickstart,
declaration/API/architecture/compatibility contracts, and research are
unaffected: their current commands, support boundaries, and implementation
explanations remain accurate. Charter, product specification,
architecture/diagrams, ADR-0001, constitution, backlog, reserved UI/provider
guides, infrastructure, and release documentation need no edits because this
handoff adds no product behavior, ownership/dependency change, governance,
infrastructure, or release action.

The checkpoint records `await_merge`, ready, with PR #4 targeting `main`;
the PR is ready for maintainer review. F-01 is not marked complete, and no
dependent work is unlocked. The next separately authorized invocation must
verify that PR merged before publishing the progress-only completion checkpoint
from fetched main; that checkpoint must also merge before a new specification
begins. No merge, publication, deployment, IaC plan/apply, permissions change,
or data/schema migration occurred. Rollback remains a reviewed source change
with matching locks. Temporary acceptance directories were cleaned by the
wrapper; no feed, cache, binary, credential, or evidence artifact is committed.
