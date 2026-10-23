# F-07 Acceptance and Proof Obligations

**Status**: Planned observable checks, not executed results. QC-01..48 are
F-07 acceptance obligations in addition to every inherited
[matrix entry](matrix.md). Each must have actual runtime/input-bound evidence.
Grouped rows require all subvariants; a total pass count is never sufficient.

## Required Proofs

| ID | Observable proof, including controlled failure | Requirements |
| --- | --- | --- |
| QC-01 | Catalog revision and exact expansion immutable; altered/unknown revision rejects | FR-001 |
| QC-02 | Both metadata adapters execute unchanged shared assertions and exact parameterized witnesses | FR-002..004 |
| QC-03 | Both artifact adapters execute unchanged shared assertions and exact parameterized witnesses | FR-002,003,005 |
| QC-04 | Deliberately faulty metadata and artifact adapters fail named behavior assertions; corrected counterparts pass unchanged checks | FR-002,019 |
| QC-05 | Missing mandatory binding/fault hook fails; optional/durable exclusions cannot remove logical guarantees | FR-001..003 |
| QC-06 | All inherited metadata isolation/atomicity/page/lease/reference cases and convergence regressions remain observed | FR-004 |
| QC-07 | Lost metadata acknowledgment/late native work preserves reconciliation and owned protection, not false rollback/cleanup | FR-004,009 |
| QC-08 | Actual SQLite schema/backup/restore/crash witnesses; memory's nine exclusions cannot borrow them | FR-003,004,023 |
| QC-09 | All inherited artifact verification/visibility/read/deletion/fencing cases and regressions remain observed | FR-005 |
| QC-10 | Both providers actually write/read 256 MiB and 4 GiB with bounded OS RSS, paced non-seekable streams | FR-005 |
| QC-11 | Real Local crash barriers and readback; ObjectSemantics exclusions do not qualify durability | FR-003,005,023 |
| QC-12 | Four metadata/artifact authority integrations preserve live references, readers, ABA fencing and uncertain outcomes | FR-004,005 |
| QC-13 | CP-01/02 package-only baseline/replacement builds and starts/stops with identical consumer | FR-006 |
| QC-14 | Every CP-04..11 preactivation rejection has zero construction/resource effects and passes after valid repair | FR-007,019 |
| QC-15 | CP-03 multiplicity and CP-09/10 singleton subvariants preserve cardinality without fallback | FR-007,008 |
| QC-16 | CP-12 absence of construction/routes/workers/connections is observed independently | FR-008 |
| QC-17 | CP-14/18 required initialization/recovery failure blocks actual readiness | FR-009 |
| QC-18 | CP-15/16 cancellation/late initialization returns within observation budget with retained bounded owner | FR-009 |
| QC-19 | CP-17 fault/non-cooperative cleanup never claims release; subsequent actual settlement observed | FR-009,016 |
| QC-20 | CP-12/13 optional absent/disabled/enabled-compatible/enabled-incompatible cases use unchanged policy | FR-010 |
| QC-21 | CP-19/20 authority/version/guarantee and explicit restart paths; injected unsafe errors stay sanitized | FR-006,009,022 |
| QC-22 | Each runtime version-boundary rejection and permitted repair matches matrix, independent axes retained | FR-011,019 |
| QC-23 | Explicit prerelease gate, exact/build/case precedence and independent flags match current policy | FR-011 |
| QC-24 | Required/enabled optional dependency versions and invalid declarations reject safely; C-01..23 retained | FR-010,011 |
| QC-25 | Unchanged source consumers/implementers compile; sealed old binaries run using actual candidate bytes, no recompile | FR-012 |
| QC-26 | Intentional source/binary breaks produce intended failure and compatible candidate restores same consumer | FR-012,019 |
| QC-27 | ARCH-001..008 isolated negatives and allowed counterparts; graph/package/public/IL coverage remains complete | FR-013,019 |
| QC-28 | Allowed Identity/Hosting/Core path passes; parallel forbidden direct/helper paths fail in both traversal orders | FR-013,019 |
| QC-29 | Finite support matrix labels exact tested versions/scopes; untested Cartesian product is not promoted | FR-014,023 |
| QC-30 | Separately packed contributor adapter runs common suite with no platform/provider/common-assertion edits | FR-015,024 |
| QC-31 | Starter faulty behavior fails named assertion; correcting only adapter restores unchanged suite | FR-015,019 |
| QC-32 | Clean-checkout guide reproduction includes dependencies, setup, package resolution and owned cleanup | FR-015,024 |
| QC-33 | Overlapping runs isolate roots/feeds/caches/processes; outside sentinels never modified | FR-016 |
| QC-34 | Operation/contention/child/profile watchdogs and output-flood limits bound observation/capture without truncating witnesses into success or releasing retained work | FR-009,016 |
| QC-35 | Cleanup failure preserves exact live ownership; retry cleans only settled owned resources with safe guidance | FR-016,022 |
| QC-36 | Reject symlink/foreign/pre-existing roots and unsafe process ledger; no broad deletion/termination | FR-016 |
| QC-37 | Mandatory baseline needs no service/secret; unavailable service request remains explicitly unqualified | FR-017,023 |
| QC-38 | Source/package/lock/config/capability/environment mutation or stale report substitution blocks qualification | FR-018 |
| QC-39 | Missing/duplicate/unknown case or parameterized runtime witness blocks passing | FR-018,020 |
| QC-40 | Altered proof bytes, valid-looking unattested case labels and mismatched input/provenance reject | FR-018,020 |
| QC-41 | Capability change after inventory selection and exclusion reclassification reject | FR-018,020 |
| QC-42 | Skipped mandatory/incomplete/cancelled child cannot pass; optimistic aggregate boolean ignored | FR-020 |
| QC-43 | Failure then passing retry retains failed attempt and blocks qualification; expected-negative experiments isolated | FR-019,020 |
| QC-44 | Unknown/duplicate schema fields, malformed durations, oversized/path-escaping proof and unsupported status reject safely | FR-020,022 |
| QC-45 | Local and CI profile expansions/evaluator hashes match; every mandatory option observed | FR-021 |
| QC-46 | Required job/upload/download cancellation/failure or missing report fails aggregate, even with partial green cases | FR-017,020,021 |
| QC-47 | Recomputed support statement identifies exact inputs/results/exclusions and focused mode cannot qualify baseline | FR-014,023,024 |
| QC-48 | Canary secrets, private payloads/paths, connection settings and raw exceptions absent from all private retained diagnostic evidence and public outputs; no raw spooling | FR-022,024 |

## Red/Green Evidence

At least one assertion-level metadata mutation and one artifact mutation, every
composition rejection family, source and binary break, each architecture rule,
and the contributor faulty adapter need attributed negative/positive witnesses.
Expected-negative children must fail the intended named assertion/diagnostic;
setup/build failure is not behavioral red evidence. Public API build negatives
are the explicit exception: their intended compiler/symbol failure is the proof.
Common assertion source/catalog hashes stay unchanged between each pair.
Correct only the faulty provider/composition/candidate fixture, never the
assertion or expected guarantee. Mutations live in private isolated copies.

Evidence mutation cases use a known-good generated report, alter one relevant
input/result field/proof at a time, and require the independent evaluator to
reject. They must also evaluate the unaltered control successfully. A hardcoded
JSON sample alone cannot establish actual runtime origin/completeness.

## Outcome, Scenario and Edge Coverage

| Outcome | Required proof |
| --- | --- |
| SC-001 | QC-01..06,09; all 192 category entries and exact applicable witnesses |
| SC-002 | QC-13..21; all CP variants |
| SC-003 | QC-22..28; all version, source/binary and architecture variants |
| SC-004 | QC-08,10..12,29,37; environmental exclusions verified |
| SC-005 | QC-30..32,35..36 |
| SC-006 | QC-38..46; five-profile parity and mutation negatives |
| SC-007 | QC-07,18..19,21,33..36,48 |
| SC-008 | QC-29,32,37..48; independently evaluated support statement |

Acceptance scenarios in specification order:
US1.1..5 -> QC-02+03 / 04+05 / 05+08+11 / 06..12 / 29+37;
US2.1..5 -> QC-13 / 14+15 / 16 / 17..19 / 20;
US3.1..4 -> QC-22..24 / 25 / 26..28 / 29+38;
US4.1..4 -> QC-30+32 / 31 / 33..36 / 37;
US5.1..5 -> QC-38..41+47 / 39..44 / 45..46 / 48 / 08+11+29+37.

The 14 edge cases in specification order map to:
QC-05; 41; 39; 42..43; 20+24; 25..26; 27..28; 07+12+18..19;
08+11+37; 38+42+46; 33..36; 38+40..41; 37; 29+47.
All 24 requirements appear in the proof table; all eight outcomes have focused
observations rather than artifact-existence proxies.

## Regression and Completion Gates

Implementation must preserve the existing six acceptance commands, tooling
suite, SDK formatting/analyzers, tracked lock replay, package-source/content
provenance, architecture scans and predecessor retained binaries. The new
orchestrator may share verified low-level execution but cannot omit a gate
or silently weaken its witness checks. Lock update is followed by fresh
default locked replay. Full baseline and all five CI profiles must complete;
focused success is never complete acceptance.

Architecture review must assess the final actual test/package graph, SDK
extraction and authority/ownership seams. Reviewer-owned custom checklist
approval, generated tasks, analysis, implementation, convergence and finalization
remain separately authorized stages. No row here is marked complete by planning.
