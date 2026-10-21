# F-04 Acceptance and Traceability

**Status**: Future proof obligations, not executed tests. Paired positive and
negative checks must demonstrate the intended failure before the implementation
is accepted. Case IDs group behavior; do not replace assertions with test counts.

## Forty Focused Cases

| Case | Required paired proof |
| --- | --- |
| D01 | Included/unregistered and registered/disabled entries remain distinct from enabled ready entries |
| D02 | Complete inventory establishes absence; partial/unknown inclusion never invents absence or installed modules |
| D03 | Safe identities/category/version/compatibility/provenance survive projection; unknown provenance is not supported/certified |
| D04 | Fixed authoritative selections and multiple protocol/identity choices are identifiable without settings |
| D05 | Disabled missing/invalid options, unavailable secrets and incompatible active ranges cause zero checks/reads/construction/probes/routes/workers/connections |
| D06 | Duplicate/conflicting/orphan catalog associations and invalid limits reject safely before activation; valid counterparts preserve F-02/F-03 gates |
| D07 | Unknown inclusion/support/evidence remains unknown or unverified, never green from successful startup |
| D08 | Exact tested fixture support differs from prospective/unsupported and never becomes production/native-client/conformance support |
| D09 | Actual sealed owned route/method/responsibility enables the supported fixture operation; absent/wrong binding does not |
| D10 | Exact effective owner service descriptor establishes composition without resolution; shadowed/removed/wrong-owner/keyed ambiguity does not |
| D11 | Overlapping capability versions/owners/operations remain independent; no union across incompatible scopes |
| D12 | Required contributors/dependencies determine each operation; unrelated runtime not-ready does not supply or suppress another's support |
| D13 | Optional absent/disabled dependency removes integration; enabled incompatible target fails inherited validation with no repair |
| D14 | Registered/initializing/ready/not-ready/failed/unknown observations yield distinct availability; global liveness is never readiness |
| D15 | Explicit inherited reassessment publishes readiness loss/recovery; reads add zero probes and preserve mapped routes/admission semantics |
| D16 | Stop/drain/cleanup/stopped override previously ready module statuses; terminal/late publications never revive actions |
| D17 | Failed startup exposes safe existing reports only; discovery never starts a separate listener or revives failed selection |
| D18 | Authorized management read succeeds but cannot mutate/activate/resolve secrets; absent policy fails startup |
| D19 | Both routes deny unauthenticated network and insufficient permission (401/403) without inventory; permitted identities succeed |
| D20 | Explicit direct loopback local policy succeeds; null/nonlocal peer, wildcard/unknown binding, proxy configuration and forwarded headers fail closed; actual loopback Kestrel adapter verifies binding and pre-forwarding peer capture |
| D21 | Secured HTTPS/trusted-proxy posture plus read permission succeeds; missing TLS/auth/permission, unknown proxy and spoofed forwarding do not; ephemeral loopback TLS/pinned test certificate proves adapter recognition, not external proxy certification |
| D22 | Seeded values/locators/private paths/raw errors in options, defaults, allowed values, URLs, descriptions and unknown identifiers are absent from every owned output |
| D23 | Approved plain text is inert/bounded; unapproved markup/control/long and credential-like provider text is suppressed, not merely escaped |
| D24 | Known safe reason/phase/correlation/approved affected IDs and corrective guidance survive in the closed Problem schema; unknown codes/exception payloads map to closed safe failures |
| D25 | Reference consumer distinguishes absent/unregistered/disabled/unsupported/not-ready/unknown with textual next steps |
| D26 | Unsupported actions hidden; known supported unavailable operations disabled; independent execution permission still required |
| D27 | Loading/refreshing/empty/denied/error/stale differ; denied clears sensitive retained data and failed refresh/age expiry permits no actions |
| D28 | Semantic labels/status/explanations and logical keyboard/reading order remain understandable without color/hover/motion; no rendered accessibility claim |
| D29 | Guidance separates bundled config/restart, custom package/registration/rebuild/redeploy/restart and runtime investigation; no hot install or data rollback |
| D30 | Unknown additive descriptive fields tolerated; unknown state/operation/version, malformed/duplicate identities and missing required fields fail closed |
| D31 | Barrier-controlled publication/read races produce one lifecycle/revision for module/global/capability fields, never mixed state |
| D32 | Same-binary bundled switch and rebuilt custom fixture use fresh lifecycle IDs; stale/lower-generation or old-lifecycle responses cannot overwrite current state |
| D33 | Missing/unavailable/inconsistent publication returns safe 503/unknown, not cached healthy, empty or partial success |
| D34 | Pre-canceled and mid-projection/encoding/deadline cases cannot commit 200; all buffers/work are released/observed without provider disposal or kill claims |
| D35 | At-limit/over-limit catalog/text/response sizes, escaped UTF-8 expansion and per-request cancellation stay bounded; overflow is explicit |
| D36 | 100 modules x 10 contributions, 100 authorized complete reads at concurrency 10: p95 <= two seconds; record environment/counts/bytes/resources, zero provider I/O/probes/resource growth |
| D37 | Management-read alone cannot execute a fixture operation; separate execution policy still denies after discovery reports usable |
| D38 | Hosting-owned BindHoardDiscovery accepts only its exact retained app/lease/root/source, rejects foreign/substituted pairs; approved Application -> Hosting/framework packages work, forbidden edges still fail and retained binaries run without provider rebuild |
| D39 | Deployed description/DTOs/examples match normative OpenAPI, both routes stay protected/no-store/nosniff and no public static copy, ETag/304 or wildcard credentialed CORS appears |
| D40 | Success/denial/cancellation/late-state diagnostics use closed bounded telemetry labels and safe templates, no raw payloads/URLs or high-cardinality module metrics |

Fixture handlers/services must have independent counters proving whether the
advertised operation actually exists and can be called under its own permission.
Do not derive the expected result from the same projection under test. Explicit
route/service removals, owner shadowing and readiness barriers must fail against
the pre-change implementation. Reference consumers must parse actual serialized
JSON, not use internal model instances as a compatibility shortcut.

## Requirement and Outcome Coverage

| Requirement | Proof cases |
| --- | --- |
| FR-001 | D01, D02, D05, D06 |
| FR-002 | D03, D07, D08, D22 |
| FR-003 | D01, D04, D14, D16 |
| FR-004 | D05, D06 |
| FR-005 | D07, D08, D11 |
| FR-006 | D09, D10, D12, D13, D14, D16 |
| FR-007 | D11, D12, D13, D24 |
| FR-008 | D05, D06, D13, D15, D17 |
| FR-009 | D14, D15, D16, D31, D32 |
| FR-010 | D17, D24, D33 |
| FR-011 | D18, D19, D21, D39 |
| FR-012 | D20, D21, D39 |
| FR-013 | D05, D22, D23, D39, D40 |
| FR-014 | D22, D23, D24, D35, D40 |
| FR-015 | D24, D25, D29 |
| FR-016 | D18, D26, D37 |
| FR-017 | D25, D27, D30, D32 |
| FR-018 | D26, D27, D30, D37 |
| FR-019 | D28, D30, D38 |
| FR-020 | D19, D30, D39 |
| FR-021 | D05, D15, D31, D32, D33, D34, D35, D36 |
| FR-022 | D01-D40, especially D08, D09, D10, D26, D28, D38 |
| SC-001 | D01-D08, D14 |
| SC-002 | D09-D16, D31 |
| SC-003 | D18-D21, D37, D39 |
| SC-004 | D22-D24, D39, D40 |
| SC-005 | D25-D30, D37 |
| SC-006 | D15-D17, D31-D35 |
| SC-007 | D35, D36 |
| SC-008 | D08, D29, D32, D38, D39 |

Ranges above are inclusive existing case IDs, not permission to omit cases.

## Story Scenarios and Edge Cases

| Scenario | Proof cases |
| --- | --- |
| US1-1 | D03, D04 |
| US1-2 | D01 |
| US1-3 | D02 |
| US1-4 | D05 |
| US2-1 | D09, D10, D12 |
| US2-2 | D07, D08 |
| US2-3 | D13 |
| US2-4 | D14, D15, D16 |
| US2-5 | D17 |
| US3-1 | D18, D37 |
| US3-2 | D19, D21, D39 |
| US3-3 | D20 |
| US3-4 | D22, D23, D24, D40 |
| US4-1 | D25 |
| US4-2 | D26 |
| US4-3 | D27, D30 |
| US4-4 | D28 |
| US4-5 | D29 |
| US5-1 | D31 |
| US5-2 | D32 |
| US5-3 | D33, D34 |
| US5-4 | D35, D36 |

Edge cases retain their order in the specification:

| Edge | Proof cases |
| --- | --- |
| E01: binary without explicit knowledge | D02, D06 |
| E02: disabled invalid options/secrets | D05 |
| E03: overlapping contributions | D11 |
| E04: different operation dependencies | D12 |
| E05: healthy but unqualified | D07, D08 |
| E06: service-only or unmapped route | D09, D10 |
| E07: readiness loss with mapped routes | D15 |
| E08: no reachable failed/stopped management service | D16, D17 |
| E09: unknown module/state/version | D02, D30 |
| E10: unsafe descriptive text | D22, D23, D35 |
| E11: read during update/shutdown | D16, D31, D33 |
| E12: stale retention/access loss/replacement | D27, D32 |
| E13: read permission versus operation permission | D26, D37 |

## Evidence and Compatibility Obligations

The future orchestrator requires exact nonempty case, suite and package-journey
inventories; actual emitted JSON, route/service independent counters, red/green
results, test totals/no skips, SDK/OS and performance samples. Missing/empty/
duplicate/stale evidence must fail explicitly, with regression tests in the
existing Python tooling suite. Manifests carry only safe IDs/hashes, never
secret payloads or configured private paths.

Package-only baseline must inspect known/disabled/unknown entries, perform the
same-binary bundled restart, demonstrate invalid replacement and explicit
recovery. Custom host adds a separately packed artifact provider, rebuilds and
uses a new lifecycle; compare source/binary hashes of unrelated providers.
Retain already compiled pre-F-04 lifecycle/configuration consumers and the
Abstractions-only option-bearing provider; run them against new platform
packages without recompilation. A separate new-source Application consumer and
non-web consumer prove new APIs and framework propagation. Preserve existing
F-01/F-02/F-03 binary, architecture and hash proofs.

Do not weaken ARCH-001..008 or approve unknown dependencies to make Application
compile. Add an Application -> Hosting -> Core permitted graph counterpart and
separate forbidden provider/cross-slice paths. Document lock changes and replay
default locked restore after intentionally generating new consumer locks.

TestServer/mock identities prove endpoint/policy logic. D20/D21 additionally
require actual ephemeral loopback Kestrel adapter checks with finite teardown,
in-memory certificates pinned only by the test client and no public/wildcard
binding. Reject wildcard/non-loopback configuration without opening such a
listener. All exposure claims remain unqualified until those cases pass.
Neither tier certifies external proxy isolation, production certificates/auth,
native protocols, provider conformance or rendered WCAG compliance. All held
work is released and observed; timeout is not proof of forced termination.
