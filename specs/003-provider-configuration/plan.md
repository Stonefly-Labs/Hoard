# Implementation Plan: Provider Configuration and Activation Validation

**Branch**: `feature/003-provider-configuration` | **Date**: 2026-10-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-provider-configuration/spec.md`

**Status**: Historical Phase 0/1 design, generated through the installed
`speckit-plan` skill with the recorded feature directory explicitly pinned.
The design below remains the complete feature target. The appended
[source-resolution MVP evidence](#source-resolution-mvp-implementation) records
the current partial implementation; activation, secrets, conversion and full
F-03 acceptance remain unfinished. Planning itself produced no implementation.

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
