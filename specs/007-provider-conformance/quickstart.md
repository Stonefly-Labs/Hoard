# F-07 Validation Quickstart

**Status**: Future acceptance guide with partial implementation foundations.
The SDK, focused tests and fixture project manifests now exist, but the
`validate-conformance.sh` commands below, shared suites, adapters, contributor
journey and CI qualification do not. The new execution/ingestion foundations
have unresolved review findings and are not acceptance-ready. See the
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
