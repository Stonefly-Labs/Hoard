# F-03 Acceptance and Traceability

**Status**: Planned proof obligations, not passing results. Use independent
non-production fixtures; retain F-01/F-02 compatibility and locked acceptance.
Each rejection needs a paired permitted case with observable differences.

## Harness Rules

Extend existing composition tests and package-only LifecycleHost baseline/
custom variants rather than a product Host. Add described fixture fields,
owner callbacks, secret reads, construction/route/worker/connection counters,
safe log/telemetry capture and controlled barriers. Metadata/artifact providers
remain independently packed and Abstractions-only; host adapters own config.
The baseline bundles two protocol choices and one artifact choice; the custom
variant adds the second independent artifact package/registration and rebuilds.

Use isolated local environment dictionaries/files and invented seeded values/
locators; do not read developer credentials. Public input adapters can simulate
denied reads on platforms/users where chmod alone is not reliable. Use actual
local-file integration counterparts, not mocks alone. Test normal configured
TestServer dispatch without a network listener. Virtual-time tests cover exact
absolute/per-dispatch deadlines; real-time backstops are test-hang limits, not
production guarantees. Release and observe every test-held task/notification
before exit; no runaway thread or leaked resource is an acceptable passing test.

## Configuration Cases

| ID | Case | Required observable proof |
| --- | --- | --- |
| CFG-01 | Four-source precedence/provenance | Each winner/source kind correct in repeated runs; absent optional file/env/CLI distinct from explicit invalid input |
| CFG-02 | Canonical duplicates and unknown keys | File/default/env object duplicates, JSON-escaped/case equivalents and repeated CLI paths fail in overridden/disabled input; cross-source same key valid; unknown/unsafe names not echoed |
| CFG-03 | Whole selection versus keyed merge | Enabled/identity/capability arrays replace entirely, authoritative scalar replaces, unrelated ordinary option keys remain; atomic reference objects never partially merge |
| CFG-04 | Explicit empty/defaults | Invalid effective empty selection/option never revives defaults; valid Defaults use same registration/option gate; null or wrong shape rejected even if overridden |
| CFG-05 | Requested source/read/limits | Absent optional source succeeds; requested missing/denied file, empty env JSON, repeated file selector, malformed JSON/argv, unknown reserved flag and every declared limit reject boundedly without payloads |
| CFG-06 | Installed/registered/identity/cardinality | Missing/unknown target, wrong category, identity-set disagreement, zero/two authority choices or omitted enablement reject with zero constructors; valid multiple protocols/identities reaches F-02 |
| CFG-07 | Existing gate delegation | Real `ValidateComposition` handles duplicates/declarations/versions/prerelease/capabilities/required targets/cycles with unchanged outcomes, not a parallel validator |
| CFG-08 | Optional and disabled compatibility | Absent/disabled optional targets no edge/integration; enabled incompatible target fails; disabled incompatible range remains allowed, no operational checks |
| CFG-09 | Descriptive option contracts | Metadata inspectable without construction/callback/secret/I/O; absent/orphan/duplicate/canonical collision/descriptor flag mismatch/unsupported adapter fails safely; empty legacy schema valid |
| CFG-10 | Effective public option rules | Missing/type/range/allowed-value/cross-setting/version errors fail; overridden representable invalid semantic value ignored, unknown/malformed lower input still fails |
| CFG-11 | Disabled isolation | Absent required options/unsupported option version/nonexistent valid reference allowed; zero public/secret callbacks, reads, constructors, routes/workers/connections; malformed reference/unknown key still fails |
| CFG-12 | Gate ordering | Invalid structure/composition/public check in any owner results in zero secret reads and zero constructors; secret check failure results in zero constructor/service-composition events |
| CFG-13 | Environment secret success/failure | Exact valid owner value, missing/empty/whitespace/too-large denied input failure, no alternate lookup; process/OS naming semantics and env overlay-name collision covered |
| CFG-14 | Mounted file secret | UTF-8/newline policy, local regular file and deployment symlink success; missing/empty/denied/invalid UTF-8/BOM/NUL/directory/device/pipe/too-large rejected or bounded before activation |
| CFG-15 | Secret grammar/raw credential | Unknown kind/extra fields/raw string/interpolation/malformed target reject; address user-info/query/fragment never echoed or accepted even in discarded/disabled values; valid public address counterpart |
| CFG-16 | Secret ownership/fixed value | Only owner gets its option set; explicit shared reference works for each selected owner; no reread after target mutation or access through normal string getter; redacted ToString/serialization surfaces |
| CFG-17 | Safe diagnostics/all surfaces | Seed values/locators in source keys/IDs/versions, including regex-safe unknown F-02 selection/capability/dependency-path IDs, file errors, callback exception and malformed result; map unknown identities to categories, zero payload in normal logs/results/reports/preview/telemetry; safe rule/action/source/correlation and bounds/omitted counts present |
| CFG-18 | Sync-prefix and async timeouts | Hold validator/read/resolver synchronous prefix and async body; exact outer/capped inner budget, failure/not-ready/zero construction; no multiplied waits or post-deadline dispatch |
| CFG-19 | Cancellation races/notification | Cancel before entry, each phase and just before success; slow/throwing synchronous cancellation callback cannot block bounded result; original phase/owner retained and safe notification failure observed |
| CFG-20 | Pending retention and eventual outcomes | Held check/read/notification retains in-use buffers/stream/CTS/secrets; bounded Dispose reports pending, not released; later success cannot activate, later fault observed safely once, frozen outcomes unchanged |
| CFG-21 | Configured compose and bypass | Race consume/dispose/service and contract mutation/legacy compose: one atomic transfer or release, zero rejected-path construction; successful proof uses existing ledger/lease, blocked delivery/notification inputs retained; foreign/stale/disposed proof rejected; ordinary legacy path unchanged |
| CFG-22 | Delivery/lifecycle failure | ConfigureOptions before ConfigureServices; own values only; thrown/blocked delivery handled by existing F-02 phase budget/retention, no root/prerequisite release while executing, no late activation/deferred disposal |
| CFG-23 | Fixed-state restart | Edit file/env/target/options/selection while running: active values unchanged; new lifecycle reevaluates and sees replacement, no hidden reload |
| CFG-24 | Bundled/custom journeys | Same built baseline switches protocols after restart/no rebuild, old disabled provider events zero; custom artifact absent baseline, separate package inclusion/rebuild/redeploy/restart, zero engine/provider-cross edits |
| CFG-25 | Invalid replacement/explicit recovery | Invalid restart never reuses prior values; explicit coherent previous distribution/config/references starts fresh; no retained raw-secret rollback file or data-reversal claim |
| CFG-26 | Document and option versions | Missing/malformed/newer/unsupported file/default version cannot be masked by overlay; overlay version rejected; active option version checked, disabled semantic version skipped |
| CFG-27 | Synthetic conversion preview | Exact fixture-v0 root mapping preserves explicit selections/options/reference meaning, original bytes unchanged, no secret reads/constructor, safe change list and no raw proposal/locators |
| CFG-28 | Approval/context/full validation | Unapproved/reused session, changed original/proposal/registry/mapping/destination, invalid/unmappable choice/version or unavailable secret rejects; approved valid output repeats full checks with zero activation |
| CFG-29 | Atomic original-preserving publication | Same-directory private staging, flush/close/no-clobber; destination already exists or races with publication fails unchanged; original retained byte-for-byte, no source alias overwrite; success output valid complete current file |
| CFG-30 | Interrupted/failed publication | Inject write/flush/close/publish faults, cancellation at publication, and terminate child conversion at staged/flush/pre-/post-publish barriers; original recoverable, final absent or complete, no partial final file; truthful pending/actual publication outcome and safe staging cleanup instructions |
| CFG-31 | Configuration/data recovery separation | Document coherent versions/references and backups, synthetic-only conversion limits; no promise config rollback reverses provider data; no automatic rewrite of illustrative YAML or unversioned file |
| CFG-32 | Architecture and packages | Real source/project/packed/API graphs preserve BCL-only Abstractions, provider-free Core, Abstractions-only metadata/artifact, permitted host adapters; no extra runtime packages/concrete cross-reference |
| CFG-33 | Old-source/binary/framework | Retained F-01 registration and pre-F-03 F-02 lifecycle binaries run new packages without rebuild; unchanged option-bearing Abstractions-only provider binary receives ordinary/secret options via new host adapter; new source compiles, existing shared-framework propagation and declarations intact |
| CFG-34 | Fixture/support/doc audit | All examples and reports say fixture-only/current versus planned, finite budgets/restart/custom rebuild/private files/trust limits explicit; zero production/native-client/conformance claims |
| CFG-35 | Security posture/no fallback | No server/listener/auth policy keys accepted; invalid store/identity/secret never selects substitute/anonymous/broader exposure; no new listener, download or runtime assembly load |
| CFG-36 | Complete reproducible acceptance | Focused command locks/replays actual packed inputs, nonempty exact case selection, format/analyzers and package-only journeys; existing lifecycle/foundation scripts and Python suite remain passing, no missing-proof skips |

## Functional Requirement Coverage

| Requirement | Cases |
| --- | --- |
| FR-001 | CFG-01, CFG-05 |
| FR-002 | CFG-02, CFG-05, CFG-09 |
| FR-003 | CFG-03..04, CFG-10 |
| FR-004 | CFG-04, CFG-06, CFG-25 |
| FR-005 | CFG-01, CFG-16..17, CFG-23 |
| FR-006 | CFG-06, CFG-24, CFG-35 |
| FR-007 | CFG-03, CFG-06 |
| FR-008 | CFG-07..08, CFG-21..22 |
| FR-009 | CFG-09..10, CFG-26 |
| FR-010 | CFG-10, CFG-12, CFG-18 |
| FR-011 | CFG-02, CFG-08, CFG-11..12 |
| FR-012 | CFG-12, CFG-18..22 |
| FR-013 | CFG-13..15, CFG-17 |
| FR-014 | CFG-13..15 |
| FR-015 | CFG-16..17, CFG-20, CFG-23 |
| FR-016 | CFG-18..20, CFG-22 |
| FR-017 | CFG-15..16 |
| FR-018 | CFG-21..23 |
| FR-019 | CFG-24, CFG-32 |
| FR-020 | CFG-25, CFG-31 |
| FR-021 | CFG-26, CFG-31 |
| FR-022 | CFG-27..30 |
| FR-023 | CFG-25, CFG-31 |
| FR-024 | CFG-02, CFG-05, CFG-17..20, CFG-27..30 |
| FR-025 | CFG-06, CFG-13..15, CFG-35 |
| FR-026 | CFG-01..36 |

## Outcomes, Scenarios and Edge Cases

| Outcome | Cases |
| --- | --- |
| SC-001 | CFG-01..05, CFG-10 |
| SC-002 | CFG-06..12, CFG-21..22 |
| SC-003 | CFG-11..16 |
| SC-004 | CFG-17, CFG-27..30 |
| SC-005 | CFG-18..22 |
| SC-006 | CFG-23..25, CFG-32..33 |
| SC-007 | CFG-26..31 |
| SC-008 | CFG-31..36 |

| Story scenario (spec order) | Cases |
| --- | --- |
| US1-1 | CFG-01 |
| US1-2 | CFG-03 |
| US1-3 | CFG-02, CFG-05 |
| US1-4 | CFG-04, CFG-06 |
| US2-1 | CFG-06..07, CFG-21..22 |
| US2-2 | CFG-06..08, CFG-12 |
| US2-3 | CFG-09..10, CFG-17 |
| US2-4 | CFG-08, CFG-11 |
| US2-5 | CFG-08 |
| US3-1 | CFG-13..14, CFG-16 |
| US3-2 | CFG-13..15 |
| US3-3 | CFG-15 |
| US3-4 | CFG-18..20 |
| US3-5 | CFG-17 |
| US4-1 | CFG-16, CFG-23 |
| US4-2 | CFG-24 |
| US4-3 | CFG-24, CFG-32..33 |
| US4-4 | CFG-25, CFG-31 |
| US5-1 | CFG-26 |
| US5-2 | CFG-27..28 |
| US5-3 | CFG-28..30 |
| US5-4 | CFG-31 |

| Edge case (13 bullets in spec order) | Cases |
| --- | --- |
| 1: explicit invalid/empty override | CFG-04 |
| 2: normalization collision | CFG-02 |
| 3: malformed disabled input | CFG-02, CFG-11, CFG-15 |
| 4: discarded semantic versus structural error | CFG-10 |
| 5: authority omitted from enabled selection | CFG-06 |
| 6: disabled active-version incompatibility | CFG-08 |
| 7: optional enabled incompatible | CFG-08 |
| 8: disabled secret target inaccessible | CFG-11 |
| 9: changing secret target | CFG-16, CFG-23 |
| 10: empty/timeout/late resolver | CFG-13..14, CFG-18..20 |
| 11: secret-bearing identities/errors | CFG-02, CFG-17 |
| 12: conversion access/provider widening | CFG-27..28, CFG-35 |
| 13: unmappable/data-incompatible recovery | CFG-28, CFG-31 |

## Acceptance Gate

Do not infer completion from counts/checkmarks. Actual focused and retained
suite results, package provenance, platform publication evidence, representative
red-before-green regressions, documentation/support audit and required
architecture review must be recorded during implementation/finalization.
The planning review is not a runtime or exploit-focused audit.
