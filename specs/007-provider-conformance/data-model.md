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
| RunInputs | run UUID, profile, source manifest, inventory/SDK hashes, packages/locks, safe config/capabilities, environment, budgets, exact safe invocation | Canonical digest recomputed at admission and completion; mutable source/input mismatch blocks qualification |
| ResourceOwnership | run ID, opaque root ID, child PID/start identity, state, bounded cleanup observations | Private ledger resolves actual paths; public projection never contains paths or user data |
| Attempt | sequence, start/end monotonic durations, observed status, witness/proof references, safe diagnostic code | Append-only; failed attempt cannot disappear after retry |
| CaseResult | run/profile/binding/matrix/case key, final status, attempts, applicable/exclusion rule, proof hashes | Exactly one final per expected key; all required subproofs present and attributable |
| QualificationReport | schema/catalog revision, RunInputs, exact results, resource settlement, derived qualification and scope limits | Independently recomputed, never trusted from a boolean field |
| SupportStatement | report digest, tested profiles/options/versions/environment, exclusions and unsupported scope | Human-readable projection of verified report, not endorsement or production support |

`CaseResult` key is `(runId, profileId, bindingId, matrixId, caseId)`; unused
binding/matrix dimensions use the explicit catalog value `none`, not omitted
or inferred values. Attempts are children of one result, not extra final
entries. A single runtime test can witness several cases only through explicit
catalog mappings, never matching a display-name substring.

## Validation and Bounds

- Stable IDs: ASCII `[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}`. Digests:
  lowercase SHA-256 hex; NuGet SHA-512 additionally retained where used.
- JSON schema revision `1`, catalog revision `f07-v1`; unknown schema/status/
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

**Ownership**: `Allocated -> Active -> Settling -> Released`, or
`Settling -> Retained -> Settling`. Only actual settlement/exit permits
`Released`; expiration/cancellation/observation timeout does not. Retained
resources block passing qualification and cannot be recycled by a new run.

**Evidence**: private observed witnesses -> safe validated projection -> sealed
manifest -> independent evaluation -> scope statement. Modifying bytes, inputs,
declarations or environment after sealing invalidates the projection. Reports
are technical evidence, not signatures or an in-process provider sandbox.
