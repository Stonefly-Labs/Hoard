# F-07 Validation Quickstart

**Status**: Future acceptance guide with partial implementation foundations.
The SDK, focused tests and fixture project manifests now exist, but the
`validate-conformance.sh` commands below, shared suites, adapters, contributor
journey and CI qualification do not. The allocator, runtime logger and focused
composition/version fixtures are also non-qualifying foundations. Native allocator
and logger diagnostics have passed, and all 144 expected composition/version/
classification identities match package-mode discovery; this is not behavior
qualification. Another 41 architecture/inspection and ten SDK catalog identities
match actual discovery. Explicit QC subproof declarations are expectations, not
passing observations. Loaded-provider attribution, final resource projection and complete
profiles remain outstanding. Implementation is
continuing with the existing route-mapping boundary explicitly distinguished
from preconstruction declaration validation. The tooling is not acceptance-ready. See the
[implementation checkpoint](plan.md#partial-implementation-checkpoint).
Existing predecessor commands are available.

## Prerequisites and Safe Workspace

Use a clean checkout, the SDK in `global.json`, Python 3,
Bash and Git. Initial dependency restore needs access to configured NuGet
sources, but no cloud account, service, container or credential. Use a fresh
owner-private parent outside Git and synthetic data only. Artifact qualification
requires at least 24 GiB free local scratch; 4 GiB tests are real transfers.
The actual environment, disk/RSS measurement and limitations appear in reports.

The new native supervisor currently requires Linux x64/arm64 with inherited
kernel process-group confinement. Unsupported hosts, including macOS, fail
prerequisite admission before a provider starts. Portable SDK/schema checks can
run on macOS, but skipped native regressions are incomplete evidence, never
qualification. The Ubuntu foundation workflow runs those regressions without
skips and is explicitly non-qualifying until the complete profiles exist.

Native artifact/baseline workspace allocation currently admits only local GNU
`stat` filesystem types `ext2/ext3`, `xfs`, `btrfs`, `zfs`, `f2fs` and `bcachefs`.
Remote/unknown mounts reject before workspace creation. Safe
`proofs/preflight.json` records observed free bytes, normalized filesystem type
and monotonic allocation duration without a mount path. It is not a qualifying
environment/profile report; complete preflight/report integration is pending.
Insufficient capacity emits safe `Incomplete`/`InsufficientCapacity`, exit `2`,
without creating a workspace or reducing transfer sizes. Evidence violations
remain `Failed`/exit `1`; neither outcome qualifies a scope.
Capacity/filesystem probes and workspace creation are anchored to pinned parent
and root descriptors. Parent substitution or lexical traversal rejects without
redirecting writes to a different root. The latest allocation/catalog increment passed 85 native foundation checks
without skips and eight SDK diagnostic scenarios/25 observations in run
`39924374116` at `79663dd`. This completes T008/T012's foundation scope, not
full SDK/package/profile acceptance.

Current source snapshots include runtime/example projects, tests, scripts,
workflows and build/ignore settings. Sources are copied read-only through pinned
descriptors; aliases, changed ancestors and unlisted special files reject.
Local diagnostics label dirty inputs explicitly; CI requires clean Git state
and the exact workflow checkout SHA. SDK smoke preparation uses an alternate
lock rather than modifying a frozen source lock. Native run `39927534630` at
`4e17986` verified this path with 91 foundation checks without skips and eight
SDK scenarios/25 observations. The next increment adds coherent archive/runtime
package hashes, actual synthetic source-mapping verification and complete SDK
diagnostic pre/post input recomputation. Run `39929542533` at `44881ff` verified
99 native foundation checks and eight SDK scenarios. A shared profile capture
API and immutable typed binding-declaration producer now pass focused local
checks; native execution is recorded below. They do not prove which provider/
runtime executed or provide a working qualification CLI.
SDK runtime input hashes also include generated dependency/runtime configuration,
not just DLLs; post-admission changes reject even when assembly bytes stay fixed.
Run `39932469750` at `525bdf0` verified this shared path with 102 native
foundation checks without skips and nine SDK scenarios/27 observations.
T013's shared capture foundation is complete; T014 and full profile execution
remain unfinished.

The next T014 increment repairs bounded enum parameters in the safe transports.
Its ten-scenario/29-observation native selection passed in run `39933805476`
at `a1fe180`, alongside 103 native checks without skips. Actual-instance
assembly capture and exact selected runtime/package correspondence now pass
locally; the eleventh native scenario/31-observation selection is pending.
These APIs do not yet link loaded session/factory instances to their invocation.
T014 remains unchecked.

Do not point qualification at a user/production database, existing artifact
root or connection string. Private retained diagnostic evidence must already be
sanitized; raw child text is transient bounded input, never a saved log/TRX.
Synthetic fault-test stores are separate resources, not evidence or upload
directories. Never remove a run root with retained children.
See [ownership/budgets](contracts/harness.md#finite-work-and-isolation).

## Current Regression Commands

These entry points already exist; relevant full acceptance remains mandatory
when the new harness is implemented. Artifact evidence needs a fresh path:

```bash
python3 -m unittest discover -s tests/tooling -v
bash scripts/validate-foundation.sh
bash scripts/validate-lifecycle.sh
bash scripts/validate-configuration.sh
bash scripts/validate-discovery.sh
bash scripts/validate-metadata.sh
bash scripts/validate-artifacts.sh --evidence "$HOARD_PRIVATE_PARENT/artifacts-existing"
```

Set `HOARD_PRIVATE_PARENT` to an absolute owner-private directory created for
this work, not a repository directory or broad shared temp root. Run full
acceptance serially unless each run has its own immutable input snapshot and
independent stores/caches. Do not edit shared tooling during acceptance.

## Planned Baseline and Verification

After implementation, with a fresh destination:

```bash
bash scripts/validate-conformance.sh \
  --profile baseline --evidence "$HOARD_PRIVATE_PARENT/f07-baseline"
bash scripts/validate-conformance.sh \
  --verify "$HOARD_PRIVATE_PARENT/f07-baseline/public/report.json"
```

Expected: complete category entries for all four bindings, every required
composition/version/architecture and SDK/evidence case, five verified profiles
and exact support matrix. The category portion alone has 192 entries:
179 passes/13 authorized durability exclusions. No failed, missing, duplicate,
unknown, mandatory-skipped, stale or mismatched witness; no unsettled run-owned
resources. Verification recomputes integrity/completeness; it does not rerun
providers or authorize release/deployment.

The report distinguishes logical, durable-local and simulated evidence and
states exact source/package/configuration/capability/environment inputs.
ObjectSemantics never borrows Local durability. Protocol/identity fixtures
remain declaration/lifecycle-only; no production/native-client/HA support.

## Planned Focused Diagnosis and Contributor Route

```bash
bash scripts/validate-conformance.sh --profile harness --filter QC-39 \
  --evidence "$HOARD_PRIVATE_PARENT/f07-diagnosis"
```

Expected: only the named diagnostic scenario, clearly `qualification: false`.
A successful focused exit cannot qualify baseline. Mutate missing/duplicate/
unknown runtime witnesses, stale inputs, exclusions and proof hashes and observe
explicit evaluator rejection; the unaltered control must pass.

The future `examples/ProviderConformance/README.md` supplies a clean-checkout
recipe for the separate `tests/fixtures/conformance/Contributor` project:

```bash
bash scripts/validate-conformance.sh --profile metadata \
  --binding-project tests/fixtures/conformance/Contributor/Contributor.csproj \
  --evidence "$HOARD_PRIVATE_PARENT/f07-contributor-good"
```

The binding project is explicitly built/packed and its declared category
validated. It must not edit platform source, existing provider implementations,
common assertions or inventory. This forwarding example does not count as a
third independent provider. Select its documented faulty adapter build,
repeat into a different root and require the intended stale-operation assertion
failure. Correct only the adapter and rerun unchanged common checks into another
fresh root; preserve the failed run as red evidence.

## Planned CI Reproduction

Each mandatory CI profile invokes this same command with `metadata`,
`artifacts`, `composition`, `compatibility` or `harness`. The aggregate uses
`--aggregate` on the five sanitized profile reports for one invocation group.
No secret/service requirement and no CI-specific relaxed inventory. A cancelled
job, missing artifact, failed upload or incomplete cleanup blocks the aggregate.
Raw TRX/stdout is not retained, and store files are not uploaded; only validated
public projections are eligible. See [CI contract](contracts/evidence.md#ci-profiles-and-aggregate-check).

## Failure and Owned Recovery

Read stable case/binding ID, safe failure code and corrective template. Do not
paste raw private exceptions/connection settings into PRs. Timeout/cleanup
failure keeps qualification false and names opaque retained resources.

Use the private run ledger to verify exact child PID/start identity and root
ownership. Release controlled barriers, wait within declared cleanup budget,
or terminate only the exact owned isolated test child and confirm exit.
Delete only that settled run's explicit resources. If ownership/exit cannot be
verified, retain the root and report incomplete recovery; never sweep temp
directories, kill by name or claim cancellation released a live guard.

After changing inputs, start a new run; old reports cannot qualify new bytes.
Only intentional dependency-manifest changes use `--update-locks`; preparation
does not qualify and requires a separate fresh default locked baseline replay.
