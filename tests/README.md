# Test layout

`tooling/` contains executable Python standard-library tests for the repository
checkpoint/release helpers:

```bash
python3 -m unittest discover -s tests/tooling -v
```

F-01 introduces three .NET 10 test projects:

| Project | Bounded evidence |
| --- | --- |
| `unit/Hoard.Foundation.Tests` | Declaration compiler cases, registration without construction, C-01 through C-23 compatibility/release obligations |
| `architecture/Hoard.Architecture.Tests` | Declared/resolved/packed/compiled dependency graph including unused framework references, recursive public surface including prohibited BCL shapes, slice IL, ARCH-001 through ARCH-008 negatives and permitted graph, mandatory eight real scans and explicit inspection failures |
| `integration/Hoard.Composition.Tests` | Isolated Core, five independent package/family consumers, package source/hash provenance, baseline/replacement custom hosts |

Run `bash scripts/validate-foundation.sh`. Tests require its
`HOARD_FOUNDATION_EVIDENCE` manifest and fail explicitly if it is absent.
They inspect generated files rather than invoking the script or executing
providers. The only executed compatibility input is a tiny synthetic binary
caller demonstrating a removed member; neither custom host is executed.
Standalone `fixtures/` and `examples/CustomHost` projects stay outside
`Hoard.slnx`, are copied outside repository props inheritance, and carry locks.
Architecture and compatibility fixture trees carry their own complete props.
The orchestrator verifies their formatting separately.

The script's `--phase declarations`, `--phase packages`, `--phase architecture`,
and `--phase hosts` selectors provide focused partial checks. The default full
run is required for acceptance. See the [quickstart](../specs/001-provider-contracts/quickstart.md).
Architecture checks protect declared/resolved metadata, signatures and IL;
reflection strings and malicious trusted code are not sandboxed or exhaustively
analyzed. Synthetic SDK types exercise leakage without introducing EF or a
real vendor dependency into the product.
The permitted Identity fixture consumes the actual local Hosting package/API.
Its transitive Core dependency must pass, while direct Identity-to-Core and
SDK-helper-to-Core paths still fail even with Hosting present. Normal/reversed
edge-order regressions protect the distinct path states from visitation-order
shortcuts.

`conformance/` and `protocols/` remain reserved. Provider conformance must
eventually exercise every advertised implementation; protocol tests must use
real native package clients. Compile-only fixtures do not satisfy either gate.

F-06 adds `contracts/Hoard.Artifacts.Tests` to the solution. Its value checks
run source-level; additional `Cases/` compile only with
`ArtifactPackageAcceptance=true` against independently prepared packages.
`scripts/validate-artifacts.sh --filter 'FullyQualifiedName~Artifact&FullyQualifiedName!~ArtifactTransferProofTests'` runs the
current package-only checks with a retained pre-F06 baseline and always reports
nonqualification. Coverage now includes independent streaming/publication/read/
deletion mechanisms, real SQLite/memory reference transactions and six actual
local parent-kill/fresh-reopen barriers. `--phase logical` excludes the crash
children and external-measurement proof tests; `--phase recovery` additionally drives Python-owned crash children
with independent hash/receipt validation. `--phase transfers` executes real
256 MiB/4 GiB write/read and OS peak-RSS measurements on both providers, then
four runtime tests validate those actual inputs and rejection variants.
All focused modes remain partial. `--phase packages` runs eight actual graph scans, compiled
provider/Hosting leak negatives, public-member compatibility including
accessibility, the frozen old marker binary and both consumer selections.
Default full acceptance passed on the follow-up source: 237 logical/crash checks,
four actual-transfer proof tests, three architecture checks, both consumers,
the original retained binary, all six Python-owned crash barriers and exactly
96 case entries (92 passes/four Object durability exclusions). Both fixtures
admit complete baseline profiles and support explicit configured ready/start/
stop/restart controls; they remain test-only, not production/F-07-certified.
The local-package hash blocker is resolved by reviewed `Hoard.*` hash-only lock
refreshes and separate default locked regressions. Versions, dependency graphs,
external hashes and frozen historical baselines remain unchanged. See the
[resolution and evidence](../specs/006-artifact-storage/plan.md#approved-lock-refresh-and-locked-replay-2026-10-22).
Logical mode additionally runs six owned-child non-cooperative source,
destination and native-deletion containment checks. Two explicit parent
observations verify retained work/streams/root/guards and incomplete shutdown
before exact-child termination; these are not durable-crash or cooperative
resource-release passes. Public qualification-record checks reject mixed durable
and simulation exclusion sets, flat unattached hashes and missing per-case
results or explicit environment. Tooling negatives now recompute proof hashes
around altered payloads and require paired passed TRX witnesses, exact executed
test names and matching durations. These are evidence-integrity checks, not a
replacement for execution. The exact per-AS catalog now requires every relevant
provider/parameter variant; full mode cross-binds actual context inputs,
materializes public qualification records and rejects 29 altered full manifests.
Controlled handoff tests cover delivered versus unclaimed tickets/read sessions,
expired staged-result cleanup, and failed reclamation blocking readiness/
admission/stop until an exact bounded retry succeeds.
Bounded-history checks also distinguish examined candidates from removals:
seven original runtime reds exercise fully ineligible tables, and paired
cursor-progress checks preserve a faulted candidate while reaching entries
beyond the first 100. Local reopen and held-ticket regressions cover rebuilt
dependency indexes without treating a bounded removal count as bounded traversal.
Follow-up regressions deny actual staging-directory unlink after a real prefix,
repeat failed cleanup/stop, restore access and verify exact bounded reclamation,
capacity/readiness restoration, borrowed-stream survival and Local reopen.
Separate post-commit permission failures preserve exact settled reconciliation
and committed bytes while maintenance reclaims only residual staging. Paging
regressions run 32 independent single-row scans through 35 identities, rejecting
consumed/query-mismatched/expired handles and proving terminal quota release.
Their exact runtime names are required by the AS-17/21/24/27/40 catalog.

OpenTofu mock-provider tests live beside the bootstrap at
`infra/bootstrap/tests/` and run with `tofu -chdir=infra/bootstrap test`.
