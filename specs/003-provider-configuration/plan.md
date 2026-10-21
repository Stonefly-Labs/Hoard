# Implementation Plan: Provider Configuration and Activation Validation

**Branch**: `feature/003-provider-configuration` | **Date**: 2026-10-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-provider-configuration/spec.md`

**Status**: Historical Phase 0/1 design, generated through the installed
`speckit-plan` skill with the recorded feature directory explicitly pinned.
The design below remains the feature target. The appended
[complete implementation evidence](#complete-implementation) records the actual
fixture-backed behavior and measured scope; the earlier
[source-resolution MVP](#source-resolution-mvp-implementation) is historical.
Planning itself produced no implementation.

## Summary

Add an opt-in configuration boundary to Hosting: strict, source-aware JSON
inputs resolve command line > environment > one explicit file > distribution
defaults; whole selections replace rather than union. Descriptive host-side
option contracts preserve Abstractions and existing provider binaries.
Configuration invokes F-02's metadata-only composition gate before bounded
active option checks and environment/file secret resolution. Only a successful,
single-use private proof can enter the existing lifecycle, which remains the
sole activation, readiness, admission and shutdown authority.

Use a fixed startup snapshot, owner-scoped option delivery, closed safe
diagnostics, and finite supervision that observes non-cooperative work without
claiming termination. Explicit offline conversion writes a validated, complete
new file while preserving the original; one labelled synthetic older format
proves conversion and interruption behavior without inventing release support.
No curated host, real provider, management endpoint, cache engine, UI or cloud
resolver is introduced.

## Technical Context

**Language/Version**: Nullable-aware C# / .NET 10, repository-pinned SDK.

**Primary Dependencies**: Existing Hosting references only: Abstractions, Core,
ASP.NET Core shared framework and internal NuGet.Versioning. System.Text.Json,
System.IO, immutable collections, TimeProvider and task/cancellation primitives
are framework facilities. No YAML parser, binder-based merge, new runtime
package or cloud SDK is required.

**Storage**: Explicit configuration and mounted secret files; private
same-directory conversion staging/output. No metadata database, persistence
schema, implicit state file, stored resolved secret or provider data migration.

**Testing**: Existing xUnit foundation/composition/architecture projects,
instrumented independent lifecycle fixtures and package-only TestServer hosts;
Python standard-library tooling tests. Add configuration cases to the existing
composition project, retaining F-01/F-02 acceptance and compatibility proofs.

**Target Platform**: Single process; Linux deployment and macOS contributor
validation on local filesystems. Other OS/filesystem conversion guarantees
remain unclaimed until equivalent publication tests pass.

**Project Type**: Additive public Hosting library APIs and fixture examples,
not a product CLI/web service.

**Performance Goals**: Configuration coordination defaults to one 30-second
absolute budget, each dispatched check/read/resolution capped at five seconds
and remaining outer time. Sequential callbacks, at most one pending collaborator
per failed evaluation; no retry/activation after failure. Virtual time proves
deadline arithmetic; real-time tests use an explicit scheduler allowance.
No production throughput or startup latency claim.

**Constraints**: Per document/overlay at most 1 MiB UTF-8, depth 16, 4,096
canonical assignments and 256 enabled IDs; at most 256 option fields per
module, 16 KiB per ordinary string/reference locator, 64 KiB per resolved
secret, and 100 safe diagnostics plus omitted count. Limit checks precede
unbounded allocation/iteration; limits apply to discarded/disabled input too.
Configuration budget values are trusted host options, not provider-controlled
configuration. Positive finite host overrides may narrow or expand timing;
invalid budgets fail before callbacks.

**Scale/Scope**: Four source levels, one explicit JSON file, local environment
and file secrets, current document version 1, per-module options version 1,
one synthetic `fixture-v0 -> 1` conversion. All 26 FRs/eight SCs, five stories,
22 scenarios and 13 edge cases have proof obligations. No production protocol,
store, identity system, native-client compatibility or F-07 certification.

## Constitution Check

*Gate evaluated before research and re-evaluated against the completed design.*

| Principle / constraint | Pre-research gate | Post-design evidence |
| --- | --- | --- |
| I: cache/native/personal simplicity | Pass: configuration only, no cache/protocol claim | Local JSON/environment/files; no required cloud or executable |
| II: versioned explicit composition | Pass: preserve F-01/F-02 and provider graph | [Library contract](contracts/hosting-api.md) keeps Abstractions unchanged, delegates to `ValidateComposition`, and rejects fallback/bypass |
| III: VSA/shared correctness | Pass: no slice or cache implementation | Configuration supervision is Hosting-local; no copied cache/SSRF/authorization algorithms |
| IV: bounded work/recovery | Pass: finite coordination and retained pending work required | [State/ownership model](data-model.md), absolute deadline and pending-input leases; original-preserving conversion |
| V: introduction-time security | Pass: references only, no listeners | Closed safe output, owner-scoped secrets and full rejection before construction; no listener/security override keys |
| VI: evidence before claims | Pass: fixtures and paired failures required | [Acceptance matrix](contracts/acceptance.md) traces all requirements/outcomes/scenarios; future commands labelled |
| VII: accessible static console | Pass: UI excluded | No Next.js, Node runtime, endpoint or UI contract; F-04 retains discovery |
| VIII: compatible/reversible operations | Pass: additive APIs and explicit restart | Existing sources/binaries and framework graph retained; synthetic conversion/recovery and support audit |
| Workflow/governance | Pass: correct clean shared branch, recorded `plan / running` | Exactly one installed stage, review and persistent checkpoint; reviewer-owned markers unchanged |

No constitutional exception or governance amendment is needed. These are design
gates, not passing implementation or platform-conformance results.

## Project Structure

### Documentation (this feature)

```text
specs/003-provider-configuration/
|-- spec.md
|-- checklists/requirements.md  # Existing built-in quality review, unchanged
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
`-- contracts/
    |-- configuration-format.md
    |-- hosting-api.md
    `-- acceptance.md
```

Custom checklists and `tasks.md` belong to subsequent separately authorized
stages. Do not generate them during planning.

### Source Code (repository root, planned changes only)

```text
src/Hoard.Hosting/
|-- Configuration/             # New parser/merge/contracts/evaluator/secrets/conversion
|-- Composition/               # Existing gate, not reimplemented
`-- Lifecycle/                 # Additive configured overload; reuse coordinator
tests/
|-- integration/Hoard.Composition.Tests/ # Configuration cases beside lifecycle cases
|-- architecture/Hoard.Architecture.Tests/
|-- unit/Hoard.Foundation.Tests/        # Existing registration/API compatibility
`-- fixtures/
    |-- lifecycle/                    # Extend fixture options/counters if needed
    `-- configuration/LegacyOptions/  # Option-bearing pre-F-03 binary proof
examples/LifecycleHost/                # Extend package-only baseline/custom journeys
scripts/validate-configuration.sh       # Future focused acceptance orchestrator
docs/PROVIDERS.md                      # Author option/ownership guidance
docs/DEVELOPMENT.md                    # Commands, gates, operational scope
```

**Structure Decision**: Keep new public option metadata, evaluator interfaces,
secret input types and host-side adapters in Hosting. Metadata/artifact
providers remain Abstractions-only; the composing host supplies their option
descriptions/checks/adapters. Protocol/identity adapters may use the already
approved Hosting edge. No new assembly, shared secret service bus or schema
framework; no required member added to existing descriptors/interfaces.

## Phase 0: Resolved Research

[research.md](research.md) records decisions, alternatives, primary references
and limits. The bounded research agent investigated public .NET configuration,
JSON parsing, cancellation and file publication semantics without repository
source disclosure or changes. Standard provider/binder behavior is not the
strict merge contract required here; use a small source-preserving parser.
Same-directory no-clobber publication is a platform-tested obligation, not an
inferred universal durability guarantee. No unresolved clarification remains.

## Phase 1: Design and Integration

1. Parse each supplied source independently, preserving occurrences and shape.
   Reject malformed/unknown/duplicate identities before merge even if the
   source is overridden or the module disabled. Normalize keys, not raw values.
2. Merge individual known option keys; replace each selection as a whole.
   Freeze values and winning source kinds, preserving explicit emptiness.
   File/default document versions are checked independently, never overridden.
3. Check identity-list/enablement agreement and translate selection to the
   existing `HoardStartupSelection`. Invoke `ValidateComposition` unchanged for
   declaration, category, compatibility, cardinality, capability and ordering.
   Validate metadata contract associations without constructing callbacks.
4. Check active options, option versions and public cross-field rules; skip
   disabled operational checks. Then resolve selected secret references and
   run secret-dependent owner checks under the same budget. Every selected
   module must pass; no degraded selection or hidden recovery default.
5. Publish a private single-use `HoardValidatedConfiguration` plus safe report.
   The configured compose overload atomically checks current builder/registry,
   consumes the proof and transfers fixed owner inputs into F-02's existing
   composition lease. `IHoardConfiguredModule` receives only its owner's options
   under the existing supervised service-composition phase.
6. F-02 continues supervised construction, host build, route mapping,
   initialization/readiness, requests/workers and stop/disposal. No second
   coordinator or config-owned root service provider is introduced.
7. Offline conversion previews never read secrets or activate providers.
   Approved apply repeats full validation, including secret checks, but never
   composes. It writes private staging, flushes and publishes to a fresh
   destination, retaining source bytes. A later explicit start revalidates.

Detailed grammar, new interface shapes, freshness checks, ownership,
diagnostics and conversion approval rules are in the three contracts.

## Validation Strategy and Acceptance

[quickstart.md](quickstart.md) distinguishes existing executable checks from
the future focused command. The [acceptance matrix](contracts/acceptance.md)
specifies 36 paired configuration cases, all 26 FRs/eight SCs, every story
scenario and edge-case mapping. Its existence is not execution evidence.

Implementation must demonstrate the intended failure before accepting each
new behavior, then run focused configuration acceptance and existing default
locked lifecycle/foundation suites. Preserve independent packages, original
eight architecture scans, F-01 compatibility classifications and the retained
F-01/F-02 registration binary/new-source/framework proofs. Add a retained
pre-F-03 lifecycle consumer binary and an option-bearing Abstractions-only
provider binary, receiving ordinary/secret options through a new host adapter
without rebuilding that provider; recompilation alone is insufficient.
Proof input manifests must reject missing/empty selections, never skip.

Use exact virtual-time assertions for timeout/cancellation races; all held
test work is released and observed. Real filesystem tests cover original
preservation, no-clobber races and process interruption at publication
boundaries. Conversion support is limited to tested local platforms; there is
no arbitrary power-loss, adversarial same-user filesystem or distributed
filesystem guarantee.

## Documentation, Operations and Stage Boundary

Planning updates README and development workflow only, linking this design
and the next `checklist` stage. Existing provider/example guides remain accurate
for implemented F-01/F-02 APIs; their F-03 additions wait for implementation.
Baseline product charter/specification, architecture/diagrams/ADR, constitution,
backlog, predecessor artifacts/checklists, IaC and release guides are unaffected:
no implemented API, dependency graph, runtime support, listener, permission,
operational command or infrastructure behavior changes in this stage.

Implementation must update provider and example guides with actual supported
grammar, finite budgets, secret delivery and conversion/recovery procedures,
and revise any affected diagrams then. Existing illustrative product YAML is
not an accepted format or promised legacy conversion. No listener, cloud
permission, apply/deployment, release or publication is authorized.

The planning architecture review and actual stage validation are recorded in
the shared checkpoint and draft PR. Later implementation still needs review
of actual dependency/API/ownership evidence before final handoff. The next
separate invocation generates reviewer-owned custom checklists; no approval
or implementation authorization is implied.

## Planning Review

The bounded `hoard-architecture-review` found no confirmed design contradiction
or consequential unresolved question. It ran no tests and conferred no checklist
approval or runtime acceptance. Its material future proof gaps are now explicit
in CFG-17, CFG-21, CFG-29..30 and CFG-33: legacy option-bearing provider binaries,
atomic proof-consume/dispose/mutation races and input transfer, remapping even
regex-safe unknown F-02 diagnostic IDs/dependency paths, and cancellation/
interruption/no-clobber publication on each claimed local platform.
Existing empty-option metadata fixtures alone do not prove configured old
provider support. The actual implementation/package graph must still receive
the later required architecture review.

## Complexity Tracking

No constitution violations. A strict source parser and opaque configuration
proof are needed to enforce duplicate/list/secret rules the generic host
configuration chain does not provide. Keep them local to Hosting rather than
introducing a generic schema engine, extension loader or new package family.

## Source-resolution MVP implementation

**Historical checkpoint**: The following describes committed `cbca13c`, not
the current complete implementation below. Its partial command counts,
unimplemented obligations and running-stage state are retained as evidence of
that increment, not present limitations.

The installed `speckit-implement` stage began on the recorded branch/directory
after the pushed analysis checkpoint and satisfied 16/16 built-in plus 20/20
and 20/20 reviewer-owned requirements gates. No extension hooks exist.
This checkpoint implements only T001..T020, the incremental source-resolution
MVP explicitly described in the task list. T021..T069 remain unchecked.
**The stage stays `implement / running`; no `finish` is called.** PR #8 remains
draft, and no later driver stage, merge or dependency unlock occurs.

### Delivered scope and deviations

- Inert immutable option associations and descriptor-field validation;
  private defensive input snapshots, safe bounded reports, owner-only typed
  options/secret handles and an inaccessible, not-yet-usable proof declaration.
- Strict versioned Defaults/file parsing, optional supplied environment JSON
  and reserved CLI assignments, per-source canonical duplicate/known-name/type/
  reference/address checks, keyed option merge and whole-selection replacement.
  Versions count toward the document assignment limit and are independently
  validated before precedence. Safe provenance contains no values/origins.
- Full-callback supervision under a monotonic absolute budget and capped
  dispatch budgets, non-inline collaborator cancellation, tracked notification,
  pending-input retention, bounded disposal and safe once-only eventual faults.
  Metrics use closed labels and execute inside supervised work, never under the
  state lock. No post-terminal dispatch or successful proof is exposed.
- Fail-closed evidence scaffolding with explicit partial selectors, actual
  pinned-baseline compilation and retained binary hashes, private workspace
  cleanup, local provenance/lock checks and exact case/platform inventory
  guards. Default full configuration acceptance deliberately fails.

Ancillary model/result/lease types are grouped in cohesive source files rather
than every proposed filename. Deadline/pending-work state lives within the
configuration supervisor; it owns no DI root or provider cleanup. Existing
test internals access is reused. No runtime dependency, Abstractions/Core/
Application source, old API or lifecycle source changes.

Input snapshotting scans no more than 4,096 argument elements and 4,096
environment entries before allocation can grow unbounded. Only reserved Hoard
arguments and reference-eligible environment names are retained; immutable
secret text references are not resolved/validated here. Defaults/overlay/CLI
text has a one-MiB hard ceiling, with narrower trusted evaluation limits still
enforced. Supplying finite in-memory inputs and a cooperative monotonic clock
remains the trusted host's responsibility, not a malicious-enumerator sandbox.

`EvaluateConfigurationAsync` intentionally returns **Failed /
IncompleteConfiguration** after valid source resolution, with safe provenance
and no successful proof. Existing opt-out F-02 composition remains unchanged;
option metadata is not an enforced configured lifecycle gate yet. Active option
checks, secret resolution/checks, proof consumption/input transfer, configured
delivery, restart/distribution, conversion/publication and full new-package/
old-binary compatibility evidence remain T021..T069.

### Red-before-green and architecture review

Initial tooling tests failed with missing `configuration_evidence`; initial
contract/coordination and source tests failed with absent API/types before
implementation. These compile/import failures establish missing interfaces,
not runtime safety. Current paired executable source/primitive tests prove
the measured rejection/retention outcomes; they are not complete CFG acceptance.

The required bounded read-only `hoard-architecture-review` reviewed this
increment, not the unfinished configured lifecycle or conversion. It ran no
commands/tests and did not independently inspect the private binaries or
packed graph. It found three MEDIUM defects, each reproduced dynamically
before correction:

| Finding | Red regression | Correction / current evidence |
| --- | --- | --- |
| Elapsed dispatch cap could lose to delayed timer delivery | `Elapsed_dispatch_cap_wins_even_when_timeout_notification_is_delayed` returned Failed/IncompleteConfiguration rather than TimedOut | Recheck monotonic dispatch elapsed time after await before accepting the result; virtual clock advances without delivering timers |
| Unbounded pre-evaluation input snapshot enumeration | `Input_snapshots_stop_at_hard_bounds_before_exhausting_supplied_collections` missed InputLimit; `Oversized_snapshot_argument_does_not_enumerate_following_inputs` consumed the next argument | Incremental hard count/byte ceilings; private input error becomes an explicit safe evaluation failure before callbacks |
| Known structural fields lost their safe owner/setting identity | `Known_field_failures_keep_safe_identity_but_unknown_names_are_not_reflected` reported configuration/unknown-setting for known protocol count | Preserve canonical registered context; unknown names remain safe categories without reflection |

All four regressions now pass. Further focused checks cover exact versus
over document/depth/selection/assignment/field/string/locator limits, UTF-8 byte
counting, all four sources, independent versions, replaced arrays/atomic
references, absent versus explicit unavailable sources, malformed disabled/
discarded values, typed secret-access separation, late faults, pending
cancellation/resources and cancellation at the completion boundary.
Held test callbacks/notifications are released and observed. The architecture
review is not an exploit audit or approval of later unimplemented work.

### Retained baseline and support boundaries

Both standalone fixtures compile against archived merged F-02 revision
`b80c69fc386541be4f56f6ef2edeca40f43a0e1c`, whose ancestry in fetched main is
verified. Metadata/provider dependencies remain Abstractions-only. The
pre-F-03 lifecycle consumer executes successfully against that old baseline.
New Baseline locks are generated explicitly and replayed locked.
The current invocation retains the binary/output/assets manifest privately
outside Git for later handoff; no generated binary or private path is committed.

| Retained fixture | SHA-256 |
| --- | --- |
| LegacyOptions | `64f344f212973d9660d81f0073f93c145b887bf7310c505409aadb4017d3677e` |
| LifecycleConsumer | `0930d7196a2b529421cd307848a9747007c7682eb8d68836c90a674130c5bec2` |

This proves baseline preparation/retention only. It does not yet prove the
unchanged provider/lifecycle binaries with new configured adapters/runtime;
T049/T063 retain those obligations. Existing F-01/F-02 acceptance independently
retains its old registration binary and actual graph scans.

README, development/provider guides, quickstart and model/contract status
banners describe actual partial support. Existing lifecycle/custom-host
examples, predecessor artifacts/checklists, product charter/specification,
baseline architecture/diagrams/ADR, constitution, backlog, IaC and release
guides are otherwise unaffected: no provider operation, listener, endpoint/UI,
permission, data/schema migration, deployment or conversion is introduced.
No full F-03 support, native-client or conformance claim is made.
Required setup verification adds only an upload `.terraformignore` to the
existing bootstrap module, excluding transient state/plans/private inputs while
retaining its provider lock. No infrastructure resource/configuration changes,
plan or apply accompany that exclusion file.

### Validation checkpoint

| Command | Current result |
| --- | --- |
| `bash scripts/validate-configuration.sh --filter 'FullyQualifiedName~Configuration'` | Passed: 66 source/primitive tests; partial proof only |
| `bash scripts/validate-configuration.sh --baseline-only` | Passed: two pre-F-03 fixture binaries built with isolated locked packages; old lifecycle consumer executed |
| `python3 -m unittest discover -s tests/tooling -v` | Passed: 32 tooling tests, including malformed inventory/counter rejection and red/green evidence retention |
| `bash scripts/validate-lifecycle.sh --update-locks` | Passed: 235 tests, nine boundary proofs, seven package-only journeys and retained old registration binary |
| `bash scripts/validate-foundation.sh --update-locks` | Passed: 42 unit, 49 architecture and 238 composition tests; isolated Core, provider/host package and architecture-pair proofs |
| `bash scripts/validate-lifecycle.sh` | Passed: independent default locked replay with the same 235 tests/nine boundary proofs/seven package-only journeys |
| `bash scripts/validate-foundation.sh` | Passed: independent default locked replay with the same 42/49/238 tests and package/architecture proofs |
| `dotnet format Hoard.slnx --verify-no-changes --no-restore -v quiet` | Passed |
| `git diff --check` | Passed |
| `bash scripts/validate-configuration.sh` | Expected nonzero rejection: runtime, package and publication proofs are not implemented; **not full configuration acceptance** |

The focused run was also repeated with an explicit private
`--evidence-directory`; its actual TRX and manifest record `scope: partial`,
`status: passed`, and `fullAcceptance: false`. Default full-run rejection was
observed dynamically, not inferred from the source. The retained baseline
hashes remain unchanged.

Structural lock review confirms ten existing locks change only 16 local
Hosting/rebuilt lifecycle-fixture `contentHash` entries: package IDs, versions
and dependency edges are unchanged. The two new Baseline locks are intentional.
Default locked replays do not refresh locks. Read-only assertions confirm
exactly T001..T020 checked, all 49 remaining tasks unchecked, preserved driver
history, `implement / running`, unchanged reviewer-owned checklists/specification/
constitution and valid local documentation targets. Post-implementation hooks
remain absent.

These checks preserve the delivered F-01/F-02 scope and this source-only
increment on the current macOS host. They do not establish configured lifecycle,
secret resolution, new-runtime compatibility of the retained F-03 fixtures,
conversion, publication/interruption, Linux or complete CFG-01..CFG-36 support.

## Complete implementation

The same `implement / running` invocation resumed after `cbca13c`; it did not
rerun `begin`, regenerate requirements or approve reviewer checklists. This
section supersedes the historical MVP's current-support statements. The
implementation remains fixture-backed Hosting library behavior, not a product
Host/cache, operational provider, listener, UI, native client or conformance
qualification. Convergence, finalization and merge are separate authorizations.

### Delivered behavior and placement

The shared evaluator now runs bounded metadata/source resolution, the actual
F-02 `ValidateComposition`, exact enabled-identity agreement, active ordinary
rules and all Public callbacks, then active local secret resolution and Secrets
callbacks. It checks the exact service snapshot and cancellation/deadline before
creating a private single-use proof. Disabled fields still receive structural
validation but no operational compatibility/options callbacks, reads or
construction. No defaults or previous successful values are revived.

Atomic proof consumption/disposal and configuration-association registration
use the builder gate. Arbitrary concurrent external IServiceCollection mutation
is unsupported trusted-host behavior, not a thread-safe collection/sandbox claim.
Foreign/stale/disposed/used proofs reject before construction; configured and
legacy attempts cannot both own an enabled opt-in activation. F-02 remains the
only service ledger, root, readiness and stop owner. ConfigureOptions immediately
precedes ConfigureServices in the same supervised ComposingServices phase.
Owner inputs survive bounded delivery, notification and root work until actual
quiescence; releasing them later never retries provider/root cleanup.

Environment lookup uses only explicitly supplied snapshots/read adapters and OS
name semantics. Mounted files use real bounded strict UTF-8 reads, permitted
deployment symlinks and documented BOM/NUL/newline/size rules. Actual regular
file, symlink, device, directory and FIFO counterparts run on this host. Each
selected owner/field resolves independently; shared references are not an atomic
cross-owner rotation mechanism. Public reports/displays/telemetry retain no
resolved values, locators, source/proposal text or collaborator exception text.
Managed strings cannot promise memory zeroization or sandbox malicious modules.

Explicit `fixture-v0` preview pins private source/proposal/builder/destination
context, runs shared public validation without secrets or activation, and
requires explicit one-use session approval. Apply rechecks freshness and full
ordinary/secret rules without ambient config/CLI overlays, then publishes only
the reference-bearing proposal. Conversion rejects unsupported explicit option
versions even on disabled entries; ordinary startup deliberately skips disabled
version semantics. Existing/racing destinations and aliases are never replaced.
Exclusive same-directory 0600 staging is written, flushed and closed before
no-clobber publication. A bounded unresolved wait reports PublicationPending;
live publication/supervision observation does not rewrite the returned result.

Related types remain grouped in cohesive files instead of every planned
ancillary filename: proof/ownership in HoardConfigurationEvaluation, env/file
readers in ConfigurationSecretResolver, conversion preview/apply results in
ConfigurationConversionResults, and corresponding tests in five focused
configuration test classes. No production dependencies or Abstractions/Core/
Application API/source changes were needed. Metadata/artifact fixtures retain
empty mappings where they have no fields; the option-bearing unchanged old
metadata binary plus both protocols prove real ordinary/secret mapping instead
of inventing operational fields on empty providers.

### Red-before-green and architecture-review disposition

Before their implementation, configured composition and conversion tests failed
to compile with missing interfaces/APIs; secret and prepared-distribution tests
then failed executably with missing resolution/proof inputs. Those failures
identify absent behavior, not safety by themselves. Subsequent focused runs
proved 16 configured cases, 107 combined source/configured/secret cases and
20 conversion cases. The first complete locked run passed 131 configuration
tests, six actual graph/boundary proofs, nine package journeys and five real
process-interruption barriers. It was not accepted as final coverage merely
because those counts passed.

The required complete `hoard-architecture-review` independently read governing
contracts, current Hosting/F-02 integration and focused tests/runner, selected
retained graph/project records and extracted nuspecs. It inspected the recorded
131/6 TRX summaries and manifest, but did not execute suites, independently hash
retained binaries or run fresh compiled-API inspection. It found four MEDIUM
completion blockers, corrected as follows:

| Finding | Regression/evidence | Correction |
| --- | --- | --- |
| Two publication-status reads could miss a concurrent commit | Controlled actual post-commit observer remains held through virtual timeout; result is Published, output parses, outcome/report freeze | Capture one status snapshot before outcome classification. The exact two-getter interleaving was code-inspected, not dynamically reproduced; the controlled counterpart passed before and after |
| F-02 failures lost actionable closed reason/known context | Three executable cases failed with generic Defaults/configuration/unknown-setting for version, cardinality and dependency | Preserve closed CompositionRule, registered owner, effective selection source and bounded path; unknown regex-valid path elements become generated ordinals; preserve upstream omitted count; no duplicate graph algorithm |
| Disabled unsupported option versions passed conversion | Explicit disabled version 99 returned Validated before correction; paired version 99 rejection/version 1 full apply now pass without disabled work | Check every explicitly supplied conversion option version, leaving ordinary startup's disabled exemption intact |
| Class-only inventory could certify absent scenarios | One unrelated passed method per class incorrectly certified all 36 cases; deleting required pipe/race/delivery/notification/commit scenarios now fails | Require explicit Class.Method scenario sets plus exact graphs, journeys, packages, binary provenance and real publication barriers |

The newly required blocked-delivery test found an additional tightly coupled
defect: after timed-out ConfigureOptions eventually returned, ConfigureServices
still ran. The executable red recorded construct/options/services. The existing
coordinator now rechecks admission before calling ConfigureServices; the green
case records no late services, activation, prerequisite cleanup or root disposal.
This is the same F-02 phase/ledger, not a new lifecycle authority.

Expanded proof includes simultaneous configured consumers/proof disposal/
contract mutation/legacy attempts with real secret handles, held delivery and
prerequisites, and real TestServer stopping/cancellation notifications protecting
secrets/root until actual completion. Every test-held activity is released and
observed. Nine direct-F-02/configured paired cases additionally cover optional
targets, compatibility, cycles, prerelease policy and malformed declarations;
multiple protocols/identities retain the actual activation order. Effective
allowed-value/range tests distinguish discarded semantic errors from structural
errors. Environment OS-case and independently resolved shared-owner references
have explicit counterparts.

Python tooling additionally reproduces malformed retained-manifest failure and
acceptance of duplicated/missing graphs/journeys/binaries/packages or changed
bytes before hardening. It now checks exact inventories and real local artifact
hashes, contains retained inputs to their private root, and copies only known
runtime artifacts, not unrelated files. These synthetic tooling tests do not
recursively execute acceptance. All 37 tooling tests pass.

### Actual package, compatibility and platform provenance

The runner first builds the pinned pre-F-03 baseline and reproducibly packs
LegacyOptions with `--no-build`. Optional original privately retained DLL/PDB
bytes are substituted only after packing, without recompiling/replacing those
originals. Configured hosts restore/build against the same reviewed package
locks in both modes, then receive the verified retained provider DLL in their
runtime outputs. Actual provider hashes are checked before/after execution and
required in every journey record. It compiles the new lifecycle consumer,
executes the unchanged old lifecycle binary with new dependencies and preserves
the separate retained F-01 registration binary proof.
Both original hashes in the historical table remain unchanged. Source-only
formatting of the fixture consumer does not change the retained binary.

Configured baseline/custom projects are standalone package consumers, not
product solution members or hidden ProjectReferences. Their exact four/five
journeys use the same built distribution for bundled switching and explicit
recovery; only custom references/registers Artifact.Two. The old provider
actually accepts ordinary/secret values through its new host adapter. The
distributed baseline/custom JSON is read during these journeys; the synthetic
JSON is previewed with zero secret reads. Original three/four F-02 inventories
remain unchanged.

All 13 actual scans are required: platform, Protocol.One/Two, Metadata,
Artifact.One/Two, Identity, configured-baseline/custom, old-provider,
lifecycle-consumer, registration and conversion-process. Source/project/packed/
compiled API/assets/runtimeconfig checks retain the original direction and
shared-framework proofs. Local packages and old binaries are verified by
content hash; default replay cannot refresh locks or accept missing manifests.

Real child processes are terminated by specific PID at staged, partial-write,
flush, pre-publish and post-publish barriers. The original remains byte-identical;
final output is absent or complete valid version 1; staging/output permissions
are inspected and only identified harness files are removed.
Measured scope is **Darwin on the current local device**, recorded as
`tested-local-device-<st_dev>`, not a verified APFS-family claim. Linux code is
present but unmeasured here; Windows publication is explicitly rejected.
Network shares, hostile same-user directory attacks, power loss and universal
durability remain unclaimed.

### Requirement/case and documentation audit

The task/acceptance matrices retain FR-001..026, SC-001..008, all 22 scenarios
and 13 edge cases. `REQUIRED_TESTS` now maps each CFG-01..36 to explicit actual
passed scenario names, not a passing class. The manifest records actual TRX
identities and separately verified exact journey/graph/binary/publication proof.
CFG-31/34 also rely on this manual documentation/support audit; unrelated
runtime methods are not treated as proof of prose correctness.

README, development/provider/example guides, quickstart, model/contract status
and actual JSON examples now document implemented signatures, supplied-source
grammar, owner-only secrets, finite budgets/pending retention, restart versus
custom rebuild, explicit approval/publication/recovery and measured scope.
Audit found no unresolved production/native-client/conformance claims, safe-output
values/locators, hidden fallback/listener/security keys, automatic download/
assembly loading or configuration-restores-data promise. Examples intentionally
show invented reference names as inputs, never as normal diagnostic outputs.

Product charter/specification, baseline architecture/diagrams/ADR, constitution,
backlog, predecessor specs, reviewer checklists, infrastructure and release
guides are unaffected: the same provider/module/lifecycle boundary remains;
no real provider operation, listener, UI, cloud permissions, schema/data migration,
deployment or release is added. Original specification/research statements
describe what their originating design stages produced, not a current runtime
support banner. Reviewer-owned approvals remain byte-identical.

### Complete acceptance commands

The corrected full explicit lock-refresh and subsequent locked replay passed
158 configuration tests, six boundary proofs, nine package journeys, five
actual Darwin interruption barriers, formatting/analyzers and 37 tooling tests.
Both runs reused the original retained baseline. Their private full workspaces
retain actual packages/graphs/binaries, TRX and passed/fullAcceptance results
for independent review, not just console counts; no private outputs are in Git.
Final retained suite results and review follow-up disposition are recorded below.

The same architecture reviewer inspected the live corrections, associated
runtime/tooling tests, retained initial failures and actual 158/6 manifest/TRX
records. All four original findings and the additional late-service defect are
**closed**, with no newly introduced actionable issue or unresolved design
question in that bounded follow-up. It did not rerun suites, independently
hash packages/binaries or repeat compiled-API inspection, and did not certify
the then-pending fresh retained-suite gates. The exact two-status-read race
remains a code-inspected finding, not an invented dynamic red result.

A final task audit added eight non-production I/O counterparts: actual source/
hardlink/symlink aliases, nonprivate/direct-symlink publication parents,
pre-dispatch cancelled apply and source/services changes after full validation
but before atomic publication. These add no production behavior. Their exact
scenario identities are required by CFG-28..30; no test count substitutes for
those cases or for the separate documentation audit.

### Final default replay, correction and stage boundary

The final runtime additions pair held prepublication and actual postcommit work
with both caller cancellation and timeout. Before commit, unresolved work remains
PublicationPending until observed; after commit, both paths remain Published.
The invalid-replacement package journey records its actual diagnostic count,
not an invented positive event count. The full retained run then passed
168 configuration tests, six boundary proofs, nine journeys and five barriers;
the separate lifecycle/foundation/tooling gates also passed.

The literal no-argument configuration replay subsequently found a real proof
tooling defect: NU1403 rejected LegacyOptions because its standalone baseline
project lacked path normalization. Substituting one original private binary
before packing had hidden that newly compiled DLL's location-dependent package
hash. No lock/hash validation was bypassed. The fixture now uses the existing
deterministic PathMap convention, and original-byte runtime delivery happens
after reproducible packing and locked host restore/build as described above.
The original retained files remain byte-identical. A new executable Python
counterexample first failed because host hashes alone accepted missing or
different runtime-provider bytes; every journey now requires actual retained
provider provenance. The tooling suite consequently contains 38 tests.

| Exact public command | Final measured result |
| --- | --- |
| `bash scripts/validate-configuration.sh` | Passed with no optional arguments: independent fresh locked replay, same 168/6/9/5 results, no lock mutation |
| `bash scripts/validate-lifecycle.sh` | Passed: 336 tests, nine boundary proofs, seven package-only journeys, six independent packages and unchanged old registration binary |
| `bash scripts/validate-foundation.sh` | Passed: 42 unit, 54 architecture and 339 composition tests, zero failed/skipped; isolated Core, five independent providers, both compile-only hosts and original architecture/registration proofs |
| `python3 -m unittest discover -s tests/tooling -v` | Passed: 38 tests, including actual runtime-provider provenance regression |
| `dotnet format Hoard.slnx --verify-no-changes --no-restore -v quiet` | Passed; complete configuration acceptance additionally checks standalone projects |
| `git diff --check` | Passed |

The successful `bash scripts/validate-configuration.sh --update-locks` invocation
also supplied a fresh private `--evidence-directory`; only intended local
payload hashes were refreshed.
A subsequent full locked run supplied `--retained-baseline` with the original
private inputs and another fresh `--evidence-directory`; it independently
passed the same 168/6/9/5 obligations with all 38 tooling tests. Both retained
complete workspaces have passed/fullAcceptance results, actual TRX, packages,
graphs and runtime-provider hashes. The intervening literal default command
used neither optional flag. These are three real distinct executions, not
claims inferred from an explicit-retained-only run.

The last lifecycle/foundation suites preceded only the narrow proof-tooling/
standalone fixture correction; no production C# or runtime-test behavior changed
after those suites. Configuration acceptance rebuilt and checked the corrected
fixture in all three executions. Earlier explicit lifecycle/foundation
`--update-locks` runs and their locked replays remain historical evidence.
An intermediate test build's CA1416 diagnostic was corrected with an explicit
Windows guard, not an analyzer suppression or skipped test.

All T001..T069 are reconciled against the delivered behavior, grouped placement,
case/requirement matrices and measured outcomes above. Reviewer-owned checklists,
specification, research, constitution and predecessor artifacts remain unchanged.
Post-implementation hooks are absent. The four architecture-review findings and
late-service defect remain closed; the later standalone reproducibility fix is
proof-tooling-only and makes no new production boundary claim. Publication
support remains Darwin on the measured current local device, not certified
APFS, Linux, network-share or power-loss support.

The implementation checkpoint ends at **`converge / ready`** with draft PR #8.
It neither runs convergence/finalization nor marks the PR ready, merges,
unlocks backlog dependencies, applies infrastructure or publishes a release.

## Diagnostic implementation follow-up

The separately authorized `implement` invocation executes only the convergence
tasks T070/T071, in that order. All 71 tasks are now complete; this is not a
fresh convergence assessment or finalization. The original 69 task descriptions,
specification, constitution and reviewer-owned checklist approvals are unchanged.
No pre/post implementation extension hooks are registered.

### Corrections and red-before-green proof

T070 passes the canonical secret setting into the existing supervisor's dispatch
context. Originating failures, timeout/caller cancellation, separately supervised
cancellation notification and eventual faults use the captured owner/setting/
source/phase. A failure raised internally by the resolver now records that
context before the bounded result; an already recorded parser rejection is not
duplicated. Resource retention, serial dispatch, absolute deadlines and frozen
reports/outcomes remain unchanged.

T071 validates callback field/rule identities before mapping the effective
field's source into a rejection. `Rule` remains CheckFailure; the additive
nullable `HoardConfigurationDiagnostic.OptionRule` contains only the declared
owner rule. The supervisor independently checks that rule against validated
owner metadata, while host-owned text supplies the corrective action. Malformed/
unknown callback results remain InvalidCheckResult without reflecting supplied
identities. Unsupported active option versions name their own canonical setting
and effective source. Neither provider messages nor source values/locators are
added to reports or metric labels.

| Focused command | Executable red | Green |
| --- | --- | --- |
| `bash scripts/validate-configuration.sh --filter 'FullyQualifiedName~Known_secret_failures_keep\|FullyQualifiedName~Pending_secret_diagnostics_keep'` | 16 executed: 12 failed with known fields reported as unknown-setting; four permitted counterparts passed | All 16 passed |
| `bash scripts/validate-configuration.sh --filter 'FullyQualifiedName~Declared_option_rules_keep\|FullyQualifiedName~Unsupported_active_option_version_keeps\|FullyQualifiedName~Secret_option_rules_keep'` | 17 executed: 12 failed on missing OptionRule, Defaults instead of effective source, or unknown-setting instead of optionsversion; five safe/accepted counterparts passed | All 17 passed |

Actual red/green TRX and closed partial status were retained through each
command's optional fresh private `--evidence-directory`. Two earlier test
authoring compiler errors were corrected before the executable red runs; they
are not evidence of the diagnostic defects.
The 33 new cases distinguish two known secret fields and env/file readers,
paired available/unavailable reads, timeout/caller cancellation, held throwing
notification and late faults, all four public-option source levels, ordinary/
secret-dependent rules, explicit environment/CLI option versions and malformed/
undeclared callback results. Held work is released and observed. Returned reports
stay byte-identical while live supervision appends safe eventual faults.
Public rejection prevents all secret reads; no rejection constructs providers.
Seeded values/locators are absent from serialized results and captured telemetry.

The exact five new scenario identities are mandatory in the corresponding
CFG-10/12/13/14/17/18/19/20/26 inventories. Tooling regression removes each one
individually and requires acceptance rejection despite unrelated passing methods.
No existing scenario, graph, binary, publication or package proof is waived.

### Architecture review and compatibility

The required bounded read-only `hoard-architecture-review` found no actionable
findings or unresolved design questions in T070/T071. It inspected origin
propagation, declared-rule validation, provenance/actions, diagnostic bounds,
frozen results and focused proof inventory. It ran no commands/tests, did not
independently rehash binaries or inspect compiled API/package graphs, and did
not assess the then-pending final locked and retained-suite runs. It is a
static follow-up review, not an exploit audit or fresh convergence.

Only the safe nullable OptionRule public diagnostic member is added. Existing
F-01/F-02 signatures, Abstractions/Core/Application, provider dependency
directions and production package dependencies remain unchanged. The evaluator
still feeds the actual F-02 composition authority and transfers inputs through
the same single-use proof/lease; it adds no activation or cleanup path.
Local packed Hosting/rebuilt-fixture content changes require explicit reviewed
contentHash updates and independent default locked replays, not version/edge
changes or lock bypasses.

README, development/provider/example diagnostic guidance, model/contracts and
quickstart reflect the implemented context and safe OptionRule field.
Baseline product intent/architecture/diagrams/ADR, governance/backlog,
predecessor artifacts, IaC and release guides are unaffected: no grammar,
listener, provider operation, data migration, deployment, permission or platform
support guarantee changes. Publication remains measured Darwin/local-device
behavior, not certified Linux/network-filesystem/power-loss support.

### Follow-up acceptance and checkpoint

| Command | Result |
| --- | --- |
| `bash scripts/validate-configuration.sh` | Passed literal default command: 201 configuration tests, six boundary proofs, nine package-only journeys, five actual Darwin interruption barriers, all CFG-01..36, formatting/analyzers and 38 tooling tests; no lock mutation |
| `bash scripts/validate-lifecycle.sh --update-locks` | Passed: 369 tests, nine boundary proofs, seven package-only journeys, six independent packages and retained old binary |
| `bash scripts/validate-foundation.sh --update-locks` | Passed: 42 unit, 54 architecture and 372 composition tests, zero failed/skipped; retained Core/package/host/declaration/registration proofs |
| `bash scripts/validate-lifecycle.sh` | Passed independent default locked replay with the same 369/9/7 results |
| `bash scripts/validate-foundation.sh` | Passed independent default locked replay with the same 42/54/372 results |
| `python3 -m unittest discover -s tests/tooling -v` | All 38 tests passed, including removal of each new required diagnostic scenario |
| `dotnet format Hoard.slnx --verify-no-changes --no-restore -v quiet` | Passed |
| `git diff --check` | Passed |

Complete configuration lock refresh and independent locked acceptance also
retained separate actual package/graph/binary/TRX/publication workspaces through
`--evidence-directory`; both passed the same 201/6/9/5 obligations with closed
passed/fullAcceptance status. The literal default command above used no optional
flags. No production C# or runtime-test changes followed these results.

Structural review of 14 affected locks found exactly 26 changed contentHash
entries: Hosting (14), rebuilt lifecycle Identity (4), Protocol.One (4) and
Protocol.Two (4). Package IDs, versions, dependency edges and original Baseline
locks are unchanged. Default locked replays neither refresh nor bypass locks.
Source/package/API and old-binary proof remains fixture-only; no platform,
production provider, native-client or conformance certification is inferred.

The implementation checkpoint schedules **fresh `converge / ready`** and keeps
PR #8 draft. It does not execute convergence/finalize, mark the feature complete,
unlock dependents, merge, deploy, apply infrastructure or publish packages/releases.
