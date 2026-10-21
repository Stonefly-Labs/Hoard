# Implementation Plan: Provider Configuration and Activation Validation

**Branch**: `feature/003-provider-configuration` | **Date**: 2026-10-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-provider-configuration/spec.md`

**Status**: Phase 0/1 design only, generated through the installed
`speckit-plan` skill with the recorded feature directory explicitly pinned.
All new APIs, paths, grammar and checks below are planned, not implemented.
No task list, custom checklist approval or runtime acceptance is produced here.

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
