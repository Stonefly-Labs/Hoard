# F-06 Acceptance and Qualification Matrix

**Status**: Normative proof obligations. No row is an executed result; actual
qualification is recorded separately in the [final evidence](../plan.md#final-fixture-qualification-and-handoff-2026-10-22).
All changed behavior needs focused red-before-green evidence; compilation
failure, generated tasks and an existing passing suite are not substitutes.

## Qualification Classes

- **L**: AS-01..40, identical logical suite/consumer against both independent
  providers, including actual large transfers and all authority/ownership cases.
- **D**: AS-41..44, local durable-only proof with actual parent-killed children.
  Object simulation records explicit non-applicability, never borrowed passes.
- **Q**: AS-45..48, packaging, compatibility, qualification and evidence integrity,
  attributed to each provider where applicable.

Full manifest has exactly 96 provider/case entries: 92 applicable passes and
four explicit object D exclusions. Arithmetic: 44 L/Q cases x two providers
plus four local D passes, with four object D exclusions. No skipped, missing,
stale, duplicate or unrecognized entry qualifies. A case may require multiple
subproofs; each must be attributable and pass.

## Required Cases

| ID | Class | Observable paired proof | Requirements |
| --- | --- | --- | --- |
| AS-01 | L | Empty SHA-256 content round-trips as zero length, unlike absence | FR-001,011 |
| AS-02 | L | Pause staging/verification: committed opens expose no prefix; commit then exact full read | FR-002,004,006 |
| AS-03 | L | Unknown length and positive short reads continue through real EOF under admitted cap | FR-001,003,007,011 |
| AS-04 | L | SHA-256, SHA-512 and length mismatch each fail; matching controls publish | FR-003,012 |
| AS-05 | L | Unsupported checksum/range explicitly rejects before input I/O; no silent downgrade | FR-003,023,024 |
| AS-06 | L | Submitted duplicate is fully consumed/verified; incomplete/mismatched duplicate cannot reuse existing bytes | FR-003,005 |
| AS-07 | L | Barrier-controlled equivalent writers get one immutable incarnation and own receipts | FR-005,006 |
| AS-08 | L | Conflicting length/identity claim leaves existing valid content/stamp unchanged | FR-001,005,012 |
| AS-09 | L | Corrupt existing payload refuses reuse, reports corruption and remains preserved/quarantined | FR-005,010 |
| AS-10 | L | Truncated/modified read fails completion, invalidates health/evidence; absence and outage controls differ | FR-006,010,012 |
| AS-11 | L | Actual 256 MiB write/read, paced non-seekable streams, exact hash/length and <=64 MiB incremental peak RSS | FR-007..009,011 |
| AS-12 | L | Actual 4 GiB write/read with same concurrency/buffers/RSS ceiling, no payload preloading | FR-007..009,011 |
| AS-13 | L | Oversized declared length rejected before reads; unknown/false length crossing cap on last chunk fails, no successful truncation | FR-003,008 |
| AS-14 | L | Full queue, transfer slots, staging and ticket limits reject boundedly; releasing capacity restores admission | FR-008,009 |
| AS-15 | L | Cancel during stage/verify before decision; definite noncommit, late commit fenced, cooperative resources settle | FR-007,009,012 |
| AS-16 | L | Stalled producer/consumer and guard/visibility work obey total/inactivity deadlines, no hidden retries | FR-007..009 |
| AS-17 | L | Capacity/device-full, permission and unavailable cases stay distinct from miss/empty success | FR-008,012 |
| AS-18 | L | Copy/dispose/failure preserve borrowed streams and release owned handles/slots/guards; early disposal has no verified completion | FR-009,011 |
| AS-19 | L | Diagnostics and retained public proof omit synthetic secrets, private paths, opaque handles and raw exceptions | FR-012,021 |
| AS-20 | L | Unexpected fault before/after decision surfaces safe internal failure/noncommit or uncertainty, never empty success | FR-012,013 |
| AS-21 | L | Lost write acknowledgment reconciles exact receipt; same-ticket retry is idempotent, changed intent conflicts | FR-004,013 |
| AS-22 | L | Expired/unknown/foreign-epoch ticket cannot replay; clock rollback cannot revive decided expiry | FR-013,017 |
| AS-23 | L | Renew/cleanup race at exact expiry; stale owner cannot append, renew, commit or abandon new generation | FR-015,017 |
| AS-24 | L | Bounded multi-page changed inventory/continuations and repeated cleanup preserve active/unseen work | FR-008,015 |
| AS-25 | L | Incomplete/delayed listing cannot establish direct absence or authorize deletion | FR-015,023 |
| AS-26 | L | Committed blob plus failed metadata publication remains identifiable, not a fabricated entry or automatic rollback | FR-004,016 |
| AS-27 | L | Maintenance expiry/replacement and late I/O retain ownership; stale cleanup never removes newer work | FR-009,015,017 |
| AS-28 | L | Live reference denies physical deletion; authoritative zero reference permits it | FR-018,020 |
| AS-29 | L | Barrier-held reader completes unchanged bytes; exclusive deletion cannot truncate it or admit a new open after removal | FR-018,019 |
| AS-30 | L | New metadata reference/publication races old zero-reference decision; shared exclusion rejects stale removal | FR-018,019 |
| AS-31 | L | Delete/recreate same digest gives fresh stamp; old authority/ticket/cleanup cannot remove it | FR-019,020 |
| AS-32 | L | Removed, repeated same-ticket receipt and new-ticket already-absent are distinct and exact | FR-013,020 |
| AS-33 | L | Lost deletion acknowledgment reconciles; failed/pending reclamation does not claim freed space | FR-012,013,020 |
| AS-34 | L | Invalid digest, foreign locator/store/epoch, traversal and symlink attempts leave outside sentinel untouched | FR-001,021 |
| AS-35 | L | Foreign/copied/disposed guards and new-work expired grants reject; held same-operation settlement retains safely past expiry; unavailable metadata denies deletion | FR-017..019,021 |
| AS-36 | L | Same consumer uses both packages without provider types/rename assumptions; actual configured singleton selection | FR-022,025 |
| AS-37 | L | Object multipart/delayed direct visibility/conditional version races preserve baseline; local direct-visibility control | FR-006,023,024 |
| AS-38 | L | Missing mandatory capability/version/authority rejects initialization; unsupported optional operations fail safely | FR-012,023,024 |
| AS-39 | L | Non-cooperative source/destination/native decision: bounded slots, incomplete cleanup, retained borrowed resources/guards and blocked readiness | FR-008,009,012 |
| AS-40 | L | Disabled store performs no I/O/work; initialization failure blocks readiness; shutdown/restart is explicit, not hot replacement | FR-017,022,024 |
| AS-41 | D | Actual B0/B1 process kills exclude partial content and fence old staging owners | FR-002,014,015,017 |
| AS-42 | D | Actual B2 kill reconciles published unacknowledged content exactly once, no false rollback | FR-006,013,014 |
| AS-43 | D | Actual B3 kill preserves acknowledged control/new bytes and matching receipts | FR-006,014 |
| AS-44 | D | Actual D0/D1 kills preserve logical deletion, reconcile reclamation and fence later incarnation | FR-013..015,019,020 |
| AS-45 | Q | Independent packages, actual resolved graphs and public API inspection preserve BCL boundary; prohibited SDK/provider/Hosting leaks fail with allowed counterparts | FR-022,025 |
| AS-46 | Q | Retained pre-F-06 marker/registration binary runs unrebuilt; new source/consumer packages compile and run both choices | FR-022,024,025 |
| AS-47 | Q | Full qualification attributes exact capabilities/environment/config/limits/results; simulation/durable exclusions and recovery walkthrough reproducible | FR-023..025 |
| AS-48 | Q | Missing/failed/skipped/foreign/stale/hash-altered case evidence and unsafe support overclaim all fail report validation | FR-012,024,025 |

AS-37 uses provider-specific mechanism drivers but the same consumer assertions;
local visibility is immediate, simulation explicitly delays it. AS-39 is an
unsupported/non-cooperative negative, not a successful resource-release claim.

## Requirement, Outcome and Scenario Coverage

Every FR appears in the matrix, including the full FR-007..009, FR-013..017
and FR-018..021 ranges. Success outcomes map as follows:

| Outcome | Required proof |
| --- | --- |
| SC-001 | AS-01..10,18 |
| SC-002 | AS-11,12 on each provider, actual byte counts and RSS |
| SC-003 | AS-06..09 |
| SC-004 | AS-21,22,33,41..44 |
| SC-005 | AS-23,27..35,44 |
| SC-006 | AS-13..20,27,34,35,38,39 |
| SC-007 | AS-01..40 on both; AS-36,45,46 prove unchanged consumer/boundary |
| SC-008 | AS-41..48 and the executed recovery walkthrough |

Story/scenario coverage is exact: US1.1..5 -> AS-02/04/03/07/08..09;
US2.1..5 -> AS-11..12/13/15..16/17/01; US3.1..5 ->
AS-41/21+42/43/23..24/26; US4.1..4 -> AS-28..29/30..31/32/33..35;
US5.1..4 -> AS-36+45..46/25+37/05+38/47..48.

The 15 spec edge cases in order map to:
AS-01+03; 04+13; 05+06; 07..09; 15+20+21;
41..43; 16..17; 23; 24+27; 26; 29..31; 32..33+44;
34..35; 25+37; 09..10.

## Measurement and Evidence Rules

Run AS-11/12 in fresh isolated measured children, one transfer at a time on each
provider. Warm code with a bounded small transfer, then establish idle RSS;
no preloaded payload or artificial baseline ballast. Use a deterministic
generated non-seekable producer, independently computed expected digest and a
non-seekable hashing sink. Record actual 268435456 and 4294967296 bytes on both
write/read, buffer/slot limits and deliberate paced backpressure on both ends.
Do not substitute sparse-file length, allocation counters or a smaller payload.

Retain OS peak resident-memory evidence with units and baseline, plus sampled
RSS and runtime/process IDs. Count the full provider process including native
buffers/mapped payloads; filesystem page cache outside that process is not RSS.
Incremental peak is peak measured RSS minus warmed idle RSS, at most 67108864
bytes in every run. An unavailable trustworthy measurement, insufficient disk,
timeout, missing child or skipped large test blocks full qualification.

The orchestrator sets bounded subprocess deadlines (40 minutes for a measured
transfer child, five minutes for a crash child) with stricter internal operation
budgets. It retains failure evidence, terminates only owned exact PIDs and waits
for exit before scoped cleanup. Children cannot recursively invoke acceptance.

Manifest binds current source and lock hashes, independently packed nupkg hashes,
versions, config/capability hashes, actual OS/runtime/filesystem, exact command,
case/provider IDs, result, duration and proof hashes. Crashes include exact
barrier/signal/receipt/readback proof. Full mode checks formatting/analyzers,
old binary/unchanged consumer and actual graph negatives. Lock-update mode
requires intentional manifest changes and a separate default locked replay.
Partial modes always say `qualification: false`; local proof never certifies
object persistence, a remote service, production support or F-07 certification.
