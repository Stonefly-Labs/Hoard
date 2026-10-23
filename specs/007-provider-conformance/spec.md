# Feature Specification: Provider Conformance, Compatibility and Composition

**Feature Branch**: `feature/007-provider-conformance`

**Created**: 2026-10-22

**Status**: Draft specification; no reusable certification harness, new CI
workflow, production provider or certification result is delivered by this stage.

**Input**: User description: "Specify repeatable contract and compatibility certification for Hoard modules: consistent provider semantics, lifecycle/startup failure validation, API/version mismatch handling, supported composition permutations, test templates for contributors and CI reporting."

**Backlog**: [F-07](../../docs/HOARD_SPECKIT_MASTER_BACKLOG.md#foundation-f-07)

**Feature Directory**: `specs/007-provider-conformance`

## Clarifications

### Implementation clarification 2026-10-23

Under the maintainer's direction to resolve ambiguities autonomously, preserve
the existing Hosting contracts rather than introduce a new route-declaration
API. Declaration errors reject before provider construction. Actual route
patterns are supplied by constructed modules during `MapEndpoints`; ownership
ambiguity must reject there, before publication, initialization, readiness or
request admission. CP-11 tests that real boundary and its repair, not duplicate
responsibility IDs. This corrects the impossible timing in FR-007/US2.2/QC-14;
it does not approve reviewer-owned checklist CHK014 or change product behavior.

### Session 2026-10-22

No critical ambiguities detected worth formal clarification. Zero questions
were asked or answered; no requirements, acceptance criteria or scope decisions
changed.

All ten review categories are clear for this bounded feature: functional scope
and behavior, domain and data model, interaction and UX flow, applicable
non-functional quality attributes, integration and external dependencies,
edge cases and failure handling, constraints and tradeoffs, terminology and
consistency, completion signals, and miscellaneous/placeholders.

The versioned common inventory, unchanged assertions and explicit applicability
rules distinguish mandatory logical guarantees from optional environmental
evidence. Both independent metadata and both artifact implementations are required
baseline options; actual durable-local proof, process-local simulation and
future service qualification remain separate. Declaration/lifecycle results
cannot certify undeveloped protocol or identity operations, native clients,
production support or multi-node safety.

Composition and compatibility checks preserve existing contracts, including
disabled optional targets, initialization before readiness, retained-old-binary
consumption and permitted dependency counterparts. Finite observation budgets
do not imply settlement or release of non-cooperative work. Run isolation,
bounded retained ownership, safe diagnostics and exact input attribution are
explicit; incomplete, altered or retried-away failures cannot qualify a run.

Exact test interfaces, report formats, finite budget values, CI job structure
and the enumerated bounded composition/version matrix remain planning decisions
under FR-006, FR-011, FR-014 and FR-016 through FR-021. No service-level latency
or throughput promise, rendered UI or new activation mechanism is required.
No consequential product decision blocks planning. This review does not
approve custom checklists, execute qualification or establish runtime evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Qualify Providers Against One Shared Agreement (Priority: P1)

As a provider author, I can run the same applicable contract checks against my
implementation and an independent reference implementation, so a passing result
means the same behavior rather than a provider-specific definition of success.

**Why this priority**: Interchangeability is not credible if providers choose
their own required checks or only demonstrate successful construction.

**Independent Test**: Run the common logical checks through unchanged consumers
against both existing metadata implementations and both artifact implementations.
Introduce a deliberately incorrect implementation and observe an explicit
contract failure. Covers FR-001 through FR-005 and FR-018.

**Acceptance Scenarios**:

1. **Given** two independently implemented options in one category, **When**
   the same common cases run against each, **Then** both use the same expected
   outcomes and case identities, with only composition and isolated test setup
   changing, not the consumer or assertions.
2. **Given** a provider that violates a required rule, **When** its suite runs,
   **Then** the named behavior fails with attributable evidence; the provider
   cannot omit the check or weaken its expectation to receive a passing result.
3. **Given** optional behavior or a non-durable fixture, **When** qualification
   selects applicable checks, **Then** mandatory logical checks remain required,
   and every excluded optional or durability check has an explicit
   capability-based reason and does not confer that qualification.
4. **Given** metadata and artifact qualification, **When** failure, concurrency
   and recovery checks execute, **Then** the existing contract guarantees remain
   intact, including uncertain outcomes, bounded ownership, reference safety
   and the distinction between logical and real durable evidence.
5. **Given** only a protocol or identity declaration fixture, **When** its checks
   pass, **Then** the result claims declaration/lifecycle coverage only and does
   not certify package-client behavior or authentication/authorization.

---

### User Story 2 - Reject Unsafe Host Compositions Before Use (Priority: P1)

As a host maintainer, I can demonstrate which combinations start safely and
which fail before provider work begins, so adding a module never silently
changes selection, readiness or disabled-module behavior.

**Why this priority**: A correct provider can still become unsafe when combined
with incompatible dependencies, duplicate ownership or incomplete initialization.

**Independent Test**: Exercise a documented fixture-host baseline, an alternative
custom composition and controlled invalid compositions. Observe activation,
readiness, shutdown and sanitized failures through the existing lifecycle.
Covers FR-006 through FR-010 and FR-019.

**Acceptance Scenarios**:

1. **Given** the supported fixture baseline and a custom composition replacing
   a singleton provider, **When** each builds, starts and stops, **Then**
   required initialization precedes readiness, only selected providers become
   active, and owned resources follow the documented shutdown outcome.
2. **Given** duplicate IDs, unknown or missing enabled modules, dependency
   cycles, missing required capabilities, invalid singleton counts or route
   ownership conflicts, **When** composition is validated, **Then** declaration
   errors fail actionably before provider construction or external resource work;
   actual route ambiguity fails during mapping before publication,
   initialization, readiness or request admission.
3. **Given** a disabled module with observable construction, route, worker and
   connection hooks, **When** the host starts and receives requests, **Then**
   none of those disabled-module effects occurs.
4. **Given** failed required initialization, cancellation or non-cooperative
   cleanup, **When** the host assesses readiness and shutdown, **Then** it
   reports the actual failure and retained ownership rather than readiness,
   successful cleanup or automatic provider substitution.
5. **Given** incompatible enabled optional dependencies and disabled optional
   targets, **When** the host checks them, **Then** incompatible enabled targets
   fail, while disabled targets remain unavailable and grant no capability.

---

### User Story 3 - Detect Compatibility Regressions Before Release (Priority: P1)

As a module maintainer, I can distinguish declared compatibility from actual
consumer compatibility, so a new package cannot claim support merely because
its version label looks acceptable.

**Why this priority**: Startup version checks cannot discover every incompatible
public-contract or dependency change.

**Independent Test**: Use supported and rejected version combinations, an
unchanged source consumer and a retained older compiled consumer. Demonstrate
that intentional contract and dependency violations fail. Covers FR-011
through FR-014.

**Acceptance Scenarios**:

1. **Given** host, abstraction and dependency ranges with documented inclusive,
   exclusive and prerelease boundaries, **When** boundary combinations run,
   **Then** accepted and rejected results match the existing compatibility
   policy with no implicit widening of a supported range.
2. **Given** a package update declared compatible, **When** unchanged source
   and an older compiled consumer use the candidate packages, **Then** both
   satisfy the supported contract; rebuilding the older consumer does not
   replace the binary-compatibility check.
3. **Given** an intentionally incompatible contract or forbidden direct or
   transitive provider dependency, **When** compatibility checks run, **Then**
   the intended rule fails, while its permitted counterpart passes.
4. **Given** a passing result for one version/configuration, **When** another
   version, capability set or composition is proposed, **Then** the old result
   is not treated as qualification of the untested combination.

---

### User Story 4 - Add a Provider Without Rewriting the Tests (Priority: P2)

As a contributor, I can follow a documented starter example to connect a provider
to the shared suites, understand failures and repeat the checks locally without
obtaining a cloud account or editing shared assertions.

**Why this priority**: A reusable agreement needs a practical independent-author
entry point, not only checks hardwired to existing implementations.

**Independent Test**: Follow the template from a clean checkout with documented
prerequisites, register a separate fixture and run its common and negative
checks using only the documented steps. Covers FR-015 through FR-017.

**Acceptance Scenarios**:

1. **Given** a separately composed contributor fixture, **When** its author
   follows the starter instructions, **Then** the shared applicable suite runs
   without changing platform source, existing providers or common assertions.
2. **Given** an intentionally faulty fixture, **When** the contributor diagnoses
   its result and corrects the fixture, **Then** the same check demonstrably
   fails before and passes after the correction.
3. **Given** interrupted or concurrent test runs, **When** cleanup and a fresh
   run occur, **Then** each run uses isolated owned resources, reports incomplete
   cleanup explicitly and never deletes user data or another run's resources.
4. **Given** optional service-backed qualification, **When** its prerequisites
   are absent, **Then** the report explicitly leaves that profile unqualified;
   the required local baseline still runs without cloud or external credentials.

---

### User Story 5 - Review Trustworthy Automated Qualification Evidence (Priority: P2)

As a reviewer, I can see complete, attributable local and CI results and a
support matrix, so a partial run, simulation or stale report cannot become a
successful certification claim.

**Why this priority**: Repeatable checks only protect users if missing evidence
and unsupported combinations remain visible at handoff.

**Independent Test**: Run the baseline in local and automated environments;
remove, duplicate, alter and substitute result evidence and interrupt a run.
Check the reported status and support matrix. Covers FR-018 through FR-024.

**Acceptance Scenarios**:

1. **Given** a complete successful run, **When** its report is reviewed,
   **Then** every expected case has exactly one attributable outcome and the
   tested versions, packages, configuration, capabilities, environment and
   limitations identify the exact scope of the result.
2. **Given** failed, missing, duplicate, unknown, skipped mandatory, stale or
   mismatched results, **When** qualification is evaluated, **Then** it cannot
   pass; interruption or infrastructure failure is not reported as conformance.
3. **Given** the same supported profile locally and in CI, **When** both run,
   **Then** they use the same case inventory and acceptance rules, and CI
   exposes a failing check and useful sanitized case diagnostics on failure.
4. **Given** secret-bearing injected errors and test configuration, **When**
   reports and automated summaries are produced, **Then** no credentials,
   raw connection settings, private payloads or unsafe exception details appear.
5. **Given** fixture-only, durable-local, simulated-object and untested service
   options, **When** the support matrix is published, **Then** their distinct
   qualification scopes and exclusions remain explicit; none is promoted to
   production support, native-client certification or multi-node safety.

### Edge Cases

- A provider claims a mandatory guarantee but omits its test binding.
- Optional capability declarations change after the case inventory is selected.
- A shared check passes for one implementation but is accidentally never
  invoked for another implementation with the same display name.
- A mandatory failure is relabelled optional, skipped, retried away or hidden
  by aggregating only the successful cases.
- An incompatible optional target is registered but disabled, or enabled at
  a version outside its declared range.
- A newer package accepts an older consumer at compile time but breaks that
  consumer's retained binary or requires an undeclared runtime dependency.
- A forbidden dependency is hidden behind a helper package or unused public
  type; permitted hosting integration must not become a false rejection.
- Failure occurs after a durable commit but before acknowledgment, or a
  provider retains live resources beyond the caller's cancellation deadline.
- A process-local simulation is submitted as abrupt-process recovery or
  remote object-service evidence.
- A required job is cancelled, times out or loses its report after some cases
  passed; a cached report belongs to different source or package bytes.
- Two runs overlap, a test child remains alive or cleanup fails; no unrelated
  process, store or working directory may be removed.
- A report's environment, capability declarations or evidence changes while
  its aggregate status still says passed.
- A real external service is unavailable; no mock or local fallback silently
  replaces the requested service qualification.
- A currently undeveloped category has only marker fixtures; a passing marker
  check must not imply operational provider semantics exist.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Qualification MUST define a versioned common case inventory by
  provider category and claim scope, identifying mandatory behavior, optional
  extensions and required environmental evidence. Existing provider contracts
  remain authoritative; qualification MUST NOT redefine their semantics.
- **FR-002**: Providers in the same category MUST run the same applicable
  shared checks with unchanged expected outcomes and consumers. Provider-specific
  setup, fault injection and cleanup bindings MUST NOT bypass assertions or
  substitute self-reported success for observed behavior.
- **FR-003**: Initial qualification MUST include both independently implemented
  metadata options and both independently implemented artifact options delivered
  by F-05/F-06. Common logical checks MUST run against each applicable option;
  real durable-local proof and simulated object behavior MUST remain separate.
- **FR-004**: Metadata coverage MUST preserve identity partitioning, atomic and
  conditional changes, grouped reads, bounded pages, leases, reference safety,
  uncertain-outcome reconciliation, failures and applicable schema,
  backup/restore and abrupt-process recovery guarantees.
- **FR-005**: Artifact coverage MUST preserve complete verification, committed
  visibility, bounded large streaming, protected reads, shared publication/
  deletion authority, current-incarnation fencing, corruption quarantine,
  uncertain outcomes and applicable interrupted-work recovery. Neither
  universal atomic rename nor cross-store transactions may be assumed.
- **FR-006**: Composition coverage MUST include an explicit bundled-fixture
  baseline and separately packaged custom-host replacement, with deterministic
  provider selection, initialization before readiness and bounded shutdown
  observations. Fixture hosts MUST NOT be presented as a curated product runtime.
- **FR-007**: Invalid composition checks MUST cover duplicate/unknown/missing
  modules, cycles, incompatible dependencies, missing required capabilities,
  invalid provider cardinality and route ownership conflicts. Validation
  failures for declarations MUST occur before provider construction or external
  resource work. Actual route ownership conflicts MUST reject at the existing
  route-composition boundary before publication, initialization, readiness or
  request admission; responsibility IDs MUST NOT be treated as route templates.
- **FR-008**: Disabled-module checks MUST observe absence of construction,
  routes, workers and connections. Multiple protocols and identity schemes
  remain permitted by existing rules; exactly one metadata and one artifact
  provider remain authoritative. No automatic fallback is allowed.
- **FR-009**: Lifecycle checks MUST cover required initialization failure,
  cancellation, readiness admission and shutdown/cleanup failure. Finite caller
  return MUST NOT be equated with actual settlement: non-cooperative work
  retains bounded ownership and blocks readiness/admission as required by the
  existing lifecycle/storage contracts, without forced release or false cleanup.
- **FR-010**: Dependency checks MUST preserve the existing optional-target
  policy: enabled incompatible targets reject composition; disabled or absent
  optional targets grant no integration or capability claim.
- **FR-011**: A documented version matrix MUST cover accepted and rejected
  host/abstraction/dependency combinations, declared range boundaries and
  prerelease behavior under the existing compatibility policy. An accepted
  version declaration alone MUST NOT count as behavior qualification.
- **FR-012**: Updates claiming compatibility MUST demonstrate unchanged source
  consumption and retained-old-binary consumption against candidate packages.
  Baselines and tested package identities MUST be attributable; intentional
  breaks MUST be rejected by dedicated negative checks.
- **FR-013**: Architecture checks MUST reject prohibited direct, transitive and
  public-contract coupling while admitting permitted integration. Core remains
  provider-free; provider-specific frameworks, schemas and SDK types remain
  private. Each rejection rule MUST have an isolated negative and a permitted
  counterpart, without weakening established dependency policy.
- **FR-014**: The support matrix MUST enumerate the finite tested compositions,
  versions, claim scopes and capability conditions, including mandatory baseline
  and replacement cases and known unsupported choices. It MUST NOT imply that
  every possible permutation or an untested version is supported.
- **FR-015**: Contributor templates and instructions MUST enable a separately
  composed provider to use common checks, deterministic fault controls, isolated
  resources and diagnostic guidance without modifying platform behavior or
  shared assertions. At least one correct and one deliberately faulty example
  MUST demonstrate the extension path.
- **FR-016**: Every run MUST declare finite operation, contention, child-process
  and cleanup budgets, identify its owned resources and isolate concurrent
  runs. Incomplete cleanup MUST be explicit and preserve live ownership;
  only exactly identified owned processes and test resources may be terminated
  or removed. Qualification MUST not operate on user production stores.
- **FR-017**: The mandatory local and CI baseline MUST require no cloud account,
  external service or secret. Service-backed profiles, when implemented, MUST
  name their explicit prerequisites and remain unqualified when unavailable;
  absence MUST NOT silently select a simulation or weaken a required job.
- **FR-018**: Each qualification result MUST bind the case inventory and actual
  outcomes to the tested source, package identities/content, configuration,
  capability declarations, host/contract versions and environment. Existing
  lower-level evidence may be reused only when its attribution and completeness
  are verified against those inputs; stale results cannot qualify changed inputs.
- **FR-019**: Evidence MUST include demonstrated red/green pairs for deliberately
  broken category behavior, composition and compatibility/architecture rules.
  Correcting the fixture or composition MUST restore the same check without
  removing it or changing its expected guarantee.
- **FR-020**: Aggregate qualification MUST require exactly one final result
  for every expected case, using explicit pass, fail, justified not-applicable
  and incomplete statuses. Missing, duplicate, unknown, mandatory skipped,
  mismatched or interrupted results MUST block a passing claim. Retry attempts
  MUST remain visible and cannot erase a contract failure within that run.
- **FR-021**: CI MUST run the same shared acceptance rules as local execution
  against every qualifying option in the mandatory matrix, report required
  failures through a failing check and expose per-case outcomes and sanitized
  failure evidence. Focused/partial runs MUST be labelled non-qualifying.
- **FR-022**: Reports, logs and retained evidence MUST exclude secrets, raw
  connection settings, private payloads and unsanitized provider exceptions.
  Failures MUST retain a stable case/provider identity, classified outcome and
  actionable safe diagnostic rather than a success-shaped fallback.
- **FR-023**: Published qualification/support documentation MUST distinguish
  declaration/lifecycle checks, common logical conformance, durable-local proof,
  simulation and actual service qualification. Operational protocol or identity
  certification MUST wait for their real contracts and implementations; native
  package-client acceptance remains SPEC-09.
- **FR-024**: Qualification MUST document how to reproduce the baseline,
  interpret exclusions, add a provider, recover owned test resources and assess
  changed inputs. A passing result is technical evidence for the exact tested
  scope, not automatic maintainer support, release authorization, third-party
  security certification or permission to deploy.

### Key Entities *(include if feature involves data)*

- **Contract Case**: Stable identity, contract revision, required behavior,
  applicability conditions and expected observable outcome.
- **Qualification Profile**: Category, claim scope, capability/environment
  prerequisites, complete expected inventory and finite execution budgets.
- **Provider Binding**: Implementation identity and isolated setup/fault/cleanup
  controls connecting a provider to unchanged common checks.
- **Composition and Version Matrix Entry**: Selected module/package versions,
  dependency/capability conditions, expected startup outcome and support limits.
- **Compatibility Baseline**: Attributable prior public agreement and retained
  consumer used to assess unchanged source and binary consumption.
- **Case Result and Evidence**: Run/case/provider identity, final classification,
  attempts, observed proof, safe diagnostics and any justified exclusion.
- **Qualification Report**: Complete input-bound results, environment and
  derived status for one exact profile; not a provider's self-declared badge.
- **Support Statement**: Human-readable tested scope and limitations, separate
  from provenance, maintainer endorsement or future planned support.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each of the two independent metadata options and two independent
  artifact options completes 100% of its applicable common logical cases through
  unchanged consumers and expectations, with zero missing required bindings.
- **SC-002**: Every documented invalid-composition case is rejected before
  provider construction or external work; both baseline and replacement
  compositions satisfy their startup/shutdown expectations, and disabled
  modules produce zero routes, workers, connections or construction effects.
- **SC-003**: Every required version-boundary and source/retained-binary case
  matches its documented expectation; all intentional contract and forbidden
  dependency negatives fail while their permitted counterparts pass.
- **SC-004**: Every advertised durable claim has successful real interruption/
  recovery evidence at its required boundaries; simulated, excluded and
  undeveloped behavior produces zero unsupported durability, service,
  protocol or identity qualification claims.
- **SC-005**: A contributor following only the documented prerequisites and
  steps can connect one independent example without editing common checks,
  reproduce its intentional failure and obtain a passing result after correcting
  the provider, with zero undocumented setup or cleanup steps.
- **SC-006**: Local and CI qualification cover the same complete required case
  inventory for each mandatory profile; all missing, duplicate, unknown,
  stale, altered, skipped-mandatory and interrupted-evidence challenges block
  passing qualification, with zero false passes.
- **SC-007**: Every defined failure and cleanup case terminates its observation
  within the declared budget and reports actual retained ownership where
  applicable; secret-injection and overlapping-run cases produce zero sensitive
  disclosures, unowned deletions or unsafe live-resource releases.
- **SC-008**: Every passing support statement identifies all tested inputs,
  case outcomes and exclusions, and can be independently reproduced using
  its documented profile; no focused run or untested composition is presented
  as complete certification.

## Assumptions

- F-01 through F-06 are completed dependencies. Their declarations, compatibility
  policy, lifecycle, configuration/secrets, discovery, metadata and artifact
  contracts remain authoritative. This feature generalizes repeatable proof;
  it does not replace those contracts or introduce another activation model.
- The initial independently implemented choices are the F-05 SQLite-backed and
  memory fixtures and F-06 Local and ObjectSemantics fixtures. Existing real
  local database/filesystem recovery evidence remains necessary. In-memory
  behavior and simulated object semantics cannot qualify remote services.
- Protocol and identity fixtures currently supply declarations/lifecycle hooks,
  not operational implementations. Shared category organization must accommodate
  their later suites without inventing authentication or protocol operations
  here. F-08 owns identity contracts; production providers retain their separate
  backlog scopes and real native-client tests remain SPEC-09.
- F-07 implementation includes narrowly scoped automated conformance reporting
  and checks required by this feature, not deployment, package publication,
  release automation or repository governance/branch-protection changes.
  Exact report formats, test interfaces, job structure and execution budgets
  are planning decisions constrained by the requirements above.
- A certification result means technical conformance for named tested inputs,
  not endorsement, cryptographic trust in arbitrary in-process modules or a
  security audit. Providers remain trusted build-time composed code.
- No product cache engine, curated executable, new management endpoint, rendered
  UI, cloud resource, production service provider, hot loading, live provider
  replacement, distributed coordination or multi-node qualification is in scope.
