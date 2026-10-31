# F-07 Research and Decisions

**Status**: Planning decisions, not executed qualification. All choices preserve
the [specification](spec.md) and predecessor contracts.

## 1. Reuse by extracting assertions, not wrapping fixed providers

**Decision**: Package test-only common consumers/binding contracts in
`Hoard.Testing.Conformance`. Keep named case wrappers in the existing suites
and implement independent adapters outside the SDK.

**Rationale**: `tests/contracts/Hoard.Metadata.Tests/Cases/MetadataCases.cs`
uses concrete `MetadataFixtureSession`; that session selects only SQLite/memory.
`tests/contracts/Hoard.Artifacts.Tests/Cases/ArtifactProviderDrivers.cs`
constructs Local/ObjectSemantics directly and branches for private faults.
The existing logical guarantees are reusable; their current setup is not an
independent-author API. The SDK must not reference these providers or permit
bindings to return their own pass/fail decisions.

**Alternatives considered**: Shell orchestration alone leaves the consumer
hardwired. Copying assertions into a template permits drift. Adding test hooks
to product contracts changes the wrong boundary. A new runtime loader is outside
scope. Provider mechanisms remain independent; no publication algorithm moves
into the test harness.

## 2. Authoritative inventory plus observed runtime witnesses

**Decision**: Preserve MP-01..48 and AS-01..48 and their subproofs, with an exact
parameterized runtime witness catalog for every applicable case. Add a versioned
F-07 catalog for matrix and harness cases. A binding never chooses its inventory.

**Rationale**: `scripts/artifact_case_catalog.py` already maps actual test names,
provider parameters and required subproofs. `scripts/artifact_evidence.py`
checks input hashes and exact entries. `scripts/metadata_evidence.py` validates
96 entries and recovery/package proof, but the new adapter must independently
map every required runtime witness, not infer completeness from a declared
case name, `positive/negative` flag or total pass count. F-04/F-05/F-06 input
hashes include broader tooling; extract profile-specific immutable snapshots
so concurrent jobs cannot alter one another's inputs.

**Alternatives considered**: Self-reported success, report digests alone,
aggregate TRX totals and old accepted reports are insufficient. Do not weaken
the existing fingerprints to make concurrent source mutation appear valid.

## 3. Reuse lower-level evidence conditionally

**Decision**: Adapt existing scripts/functions where their observed witnesses
and completeness satisfy the new contract. Regenerate child evidence inside
each qualification invocation. Verify exact package bytes, source/lock/config/
capability/environment inputs and evidence provenance before import.

**Rationale**: Existing prior-feature acceptance is substantive, but historical
passes and schema-compatible JSON do not qualify changed inputs. Source
snapshots, local package-source mapping and package SHA-256/SHA-512 checks are
already established repository mechanisms. Metadata/artifact old-marker
baselines are intentionally historical; they must not be replaced with current
source consumers.

**Alternatives considered**: Reimplementing all recovery orchestrators creates
unnecessary divergent proof. Blindly chaining six successful commands loses
per-case attribution. Importing arbitrary uploaded results lets incomplete
inventories become success.

## 4. Freeze old source and binary inputs independently

**Decision**: Preserve existing lower-level baseline revisions and freeze an
F-07 pre-extraction baseline at F-06 merge
`9389016c0285c79f6f515f59805a5a41c69b0767`. Compile baseline consumers once
from that revision, hash and seal them before candidate packages are built;
do not compile those binaries during candidate execution. New SDK version
compatibility starts with its own recorded initial version, not a fictional
historical SDK consumer.

**Rationale**: Source compatibility means unchanged source recompiles; binary
compatibility means the old compiled consumer works without recompilation.
These are separate obligations. Preserve baseline runtime/dependency manifests
and prove actual candidate resolution, not accidental old-DLL loading.

**Alternatives considered**: Rebuilding the old source against the candidate
proves only source compatibility; successful package restore proves neither
behavior nor retained-binary compatibility.

**Source**: Microsoft [.NET compatibility categories](https://learn.microsoft.com/dotnet/core/compatibility/categories).

## 5. Finite, honest environmental scope

**Decision**: Qualify all four fixture options, with real SQLite/Local durable
proof only. Serialize large-transfer work, check scratch capacity, preserve
existing limits and record the actual OS/runtime/filesystem. An unavailable
environment yields incomplete qualification.

**Rationale**: F-05 requires actual database recovery/backup/schema checks;
F-06 requires actual 4 GiB reads/writes and OS RSS measurements. A memory image
or disk-backed object simulation does not prove process-crash durability of a
service. Cancellation cannot preempt arbitrary native or non-cooperative code.
Outer watchdogs contain test observations, not production contract semantics.

**Alternatives considered**: Replacing large tests with sparse sizes, borrowing
local recovery passes for ObjectSemantics, claiming every OS from one run, or
treating timeout as successful cleanup would violate the specification.

## 6. Same local/CI evaluator, sanitized artifacts only

**Decision**: Five mandatory profile jobs (`metadata`, `artifacts`,
`composition`, `compatibility`, `harness`) and one aggregate job. Use
`pull_request`, `push` to main and manual dispatch; `contents: read`, no secrets,
OIDC, publishing or repository-setting changes. Pin all actions to verified
full upstream commit SHAs during implementation. Matrix `fail-fast: false`;
no `continue-on-error` on qualifying jobs. Upload only schema-validated public
evidence, with seven-day retention where repository policy permits.

**Rationale**: Matrix failure must not hide remaining outcomes. The aggregate
job requires all five profile reports for the same source snapshot and policy.
Artifact upload is best effort with `if: always()` and a finite timeout;
cancellation, runner loss and forced shutdown can still prevent it, so absence
must fail closed. GitHub's log masking is not an artifact sanitization policy.
No action version/SHA is invented by planning.

**Alternatives considered**: Trusting only green job labels, publishing private
TRX/workspaces, using `pull_request_target` to execute PR code with privileged
context, optional baseline failures, mutable action tags or cloud-backed default
jobs are rejected. No mandatory branch-protection setting is changed here.

**Sources**:
- GitHub [job matrix failure handling](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations).
- GitHub [workflow cancellation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-cancellation).
- GitHub [workflow artifacts](https://docs.github.com/en/actions/tutorials/store-and-share-data).
- GitHub [GITHUB_TOKEN permissions](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token).
- GitHub [secure use of Actions](https://docs.github.com/en/actions/reference/security/secure-use).

## 7. Explicit retained ownership and safe evidence projection

**Decision**: A run ledger owns fresh private roots and exact child identities.
Never recursively remove a live root, kill by process name, log raw provider
exceptions or assume task cancellation settles native work. A public projection
is built from an allowlisted schema, not raw-output regex replacement. The same
sanitation applies to private retained diagnostic evidence, before persistence;
raw child output is transient bounded input, never a spool/log file.

**Rationale**: Existing artifact cleanup already refuses roots with live
children; lifecycle and storage contracts require retained ownership. A
provider-specific fault hook can help setup/observe a boundary, but only common
assertions decide whether the invariant held. Hashes attest byte correspondence,
not honesty of malicious trusted code or cryptographic certification.

**Alternatives considered**: Global temp cleanup, broad process termination,
unbounded waits, forced release of live guards and raw diagnostic artifacts
would violate resource isolation and sanitized reporting requirements.

## Resolved Scope

No new operational protocol/identity contract, product provider, listener,
cache engine, UI, release/deployment or cloud resource is planned. No remaining
`NEEDS CLARIFICATION` decision blocks Phase 1. Implementation must verify action
SHAs, runner free space, SDK extraction parity and actual witness coverage;
those are proof obligations, not completed research claims.
