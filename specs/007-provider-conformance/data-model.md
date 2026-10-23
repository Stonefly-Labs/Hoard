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
| RunInputs | run/group UUIDs, profile, source manifest, inventory/SDK hashes, packages/locks, typed binding and sealed historical baseline inventories, runtime assembly hashes, safe config/capabilities, environment, budgets, exact safe invocation | Canonical digest recomputed at admission and completion; mutable source/input mismatch blocks qualification |
| ResourceOwnership | run ID, opaque root ID, child PID/start identity, state, bounded cleanup observations | Private ledger resolves actual paths; public projection never contains paths or user data; PID zero/all-zero digest explicitly mean no live child, not a fabricated execution |
| Attempt | sequence, start/end monotonic durations, observed status, actual execution UUID/proof references, safe diagnostic code | Append-only; failed attempt cannot disappear after retry |
| CaseResult | run/profile/binding/matrix/case key, final status, attempts, applicable/exclusion rule, proof hashes | Exactly one final per expected key; all required subproofs present and attributable |
| QualificationReport | schema/catalog revision, RunInputs, exact results, resource settlement, derived qualification and scope limits | Independently recomputed, never trusted from a boolean field |
| SupportStatement | report digest, tested profiles/options/versions/environment, exclusions and unsupported scope | Human-readable projection of verified report, not endorsement or production support |

`CaseResult` key is `(runId, profileId, bindingId, matrixId, caseId)`; unused
binding/matrix dimensions use the explicit catalog value `none`, not omitted
or inferred values. Attempts are children of one result, not extra final
entries. A single runtime test can witness several cases only through explicit
catalog mappings, never matching a display-name substring.

`RunInputs.bindings`, `baselines` and `runtimeAssemblies` bind actual admitted
declarations, retained compatibility artifacts and compiled test artifacts
before execution. Binding packages must match the package inventory exactly;
source/environment digests must match their canonical admitted contents.
Historical binaries remain separate from candidate package identities even
when package versions coincide. Diagnostic work may have no historical
baselines; qualification still requires its independently selected baseline
and scope obligations.

`Attempt.witnessIds` reference actual `RuntimeWitness.executionId` UUIDs,
not test display names, totals or catalog labels. Exact parameterized
`testIdentity` values remain independently catalog-matched. Referenced runtime
observations must match run/group/input/package/assembly/proof provenance;
each attempt's observations must match its result's binding/matrix dimensions
and fit wholly inside its monotonic interval; retries cannot overlap.
duplicate executions and final keys, dangling references and orphan
observations reject. Case proof references retain the union of all attempts,
including an earlier failed attempt followed by a passing diagnostic retry.
Catalog exclusions carry no attempts or fabricated runtime proofs. An
interrupted attempt may have no runtime observations and carries a closed
failure code; runtime skips are `Incomplete`, never exclusion witnesses.

The safe VSTest attempt transport additionally binds a private owner manifest
and an immutable per-attempt manifest to actual run inputs, admitted assembly
paths/hashes and package identities. Each JSONL witness references one exact
proof file with matching execution/attempt/parameter/dimension/input/assembly/
package fields and monotonic duration. The completion record is independently
checked against those observations, not trusted as a passing boolean. Partial
safe observations survive interrupted/skipped/unknown executions; they remain
incomplete. Only an actual frozen assertion symbol can classify an assertion
negative. Test-source hashes do not substitute for loaded-provider evidence.

## Validation and Bounds

### Binding input snapshot

The test SDK's `ConformanceBindingSnapshot.Capture` produces an immutable
UTF-8 declaration record with exactly `schemaVersion`, `bindingId`, `category`,
`packageId`, `packageVersion`, `packageSha256`, `capabilities` and `faults`.
Categories use `metadata`/`artifacts`; faults use the closed
`ConformanceFault` names. Mandatory category hooks and durable metadata's
backup hook must be admitted before capture. No pass/exclusion field is accepted.

Python `capture_binding` reads at most 64 KiB from the actual pinned declaration
file, checks its package against captured archive bytes, hashes that complete
binding descriptor and separately hashes its category/capabilities/faults.
The adapter ID is still a selected stable identity; actual loaded factory/
session provenance belongs to runtime ingestion, not this snapshot.
`capture_profile_inputs` assembles all source/material/declaration roles from
actual files and observed producers. Completion recaptures those same roles;
only measured free-space variation is excluded from immutable machine identity,
retaining the admission measurement rather than fabricating equal free bytes.
`runtimeAssemblies` also inventories selected generated dependency/runtime
configuration files as runtime artifacts. They cannot stand in for an assembly
execution witness; loaded-origin checks must identify the actual assembly.

### Shared bounds

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
