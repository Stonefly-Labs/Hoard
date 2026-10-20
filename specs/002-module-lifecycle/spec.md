# Feature Specification: Module Registry, Composition and Lifecycle

**Feature Branch**: `feature/002-module-lifecycle`

**Created**: 2026-10-20

**Status**: Draft requirements; no runtime lifecycle implementation is delivered
by this specification stage.

**Input**: User description: "Specify how operators assemble Hoard from installed provider NuGet packages and activate selected modules at startup. Define safe module lifecycle, route registration, dependency resolution, readiness, enabled/disabled behavior, diagnostic errors, restart semantics and default-versus-custom distribution expectations."

**Backlog**: [F-02](../../docs/HOARD_SPECKIT_MASTER_BACKLOG.md#foundation-f-02)

**Feature Directory**: `specs/002-module-lifecycle`

## Clarifications

### Session 2026-10-20

No critical ambiguities detected worth formal clarification. Zero questions
were asked or answered; no requirements, acceptance criteria, or scope decisions
changed.

The review found sufficient coverage across all ten ambiguity categories:
functional scope and behavior, domain and data model, interaction and operator
journeys, applicable quality attributes, integration and external dependencies,
edge cases and failure handling, constraints and tradeoffs, terminology and
consistency, completion signals, and placeholders. Explicit selection,
pre-construction validation, enabled optional dependencies, disabled-module
isolation, readiness admission and later health changes, cancellation and finite
budgets, partial-start cleanup, safe diagnostics, and restart/rebuild behavior
already have observable requirements and acceptance outcomes.

Exact lifecycle signatures and state representation, route-conflict inspection,
finite budget defaults, and the stable ordering tie-break remain planning
decisions under those requirements, not unresolved product choices. Production
latency/scale targets, real-provider data recovery and conformance, configuration
sources and secrets, management discovery, and UI/accessibility behavior remain
outside this bounded lifecycle feature as assigned in Assumptions. The existing
security, trust, compatibility, and truthful-support constraints still apply;
no consequential decision blocks planning.

### Approved Follow-up: 2026-10-20

After the requested checklist review, the user approved both recommendations.
Cleanup budget expiry ends coordination waiting, not a still-running cleanup
callback's resource use. Such a callback retains its owner's and prerequisites'
resources and prevents root disposal; independent safe cleanup may continue
within the same shutdown budget. Late completion does not retry cleanup or
rewrite an already returned stop outcome.

The fixture baseline bundles two protocol choices, metadata, one artifact
choice and optional identity. The custom journey adds the second independent
artifact package through rebuild/redeployment; the bundled journey switches
protocol choices without rebuilding. This clarifies FR-017/FR-021/FR-022 and
their existing proof obligations, not product scope or runtime delivery.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start Only the Intended Modules (Priority: P1)

As an operator, I can start a host using only the installed modules I selected,
with their prerequisites validated before activation, so a mistaken composition
never becomes an apparently working service.

**Why this priority**: Every later provider depends on predictable startup and
explicit selection rather than implicit enablement or silent substitution.

**Independent Test**: Start an isolated lifecycle host with instrumented fixture
modules and an explicit selection. Observe validation, activation, and readiness
without a real package registry, database, or identity service. Repeat with
invalid compositions. This covers FR-001 through FR-008.

**Acceptance Scenarios**:

1. **Given** compatible registered modules supplied in different registration
   orders, **When** the same selection starts, **Then** prerequisites are
   activated before their dependents and independent modules have the same
   documented tie-break order on each run.
2. **Given** a selected module that is absent, unregistered, or dependent on a
   disabled required target, **When** startup validates the composition,
   **Then** it fails before any module activation and identifies the unresolved
   selection or dependency; no package is downloaded or substitute enabled.
3. **Given** duplicate IDs, an invalid declaration, a self-dependency or cycle,
   incompatible versions, an unsupported required capability, or invalid
   authoritative-provider selections, **When** startup validates the composition,
   **Then** it fails with the offending modules and rule identified and no
   provider activation side effects.
4. **Given** an optional dependency, **When** its target is absent or disabled,
   **Then** the module may start without that integration and does not activate
   the target or claim its capabilities; **When** the target is enabled but
   incompatible, **Then** the composition fails rather than ignoring it.

---

### User Story 2 - Expose Only Enabled and Ready Functionality (Priority: P1)

As an operator, I can disable a bundled module without leaving its routes,
workers, or external connections running, and trust that readiness means the
selected functionality has initialized.

**Why this priority**: Disabled or uninitialized functionality must not remain an
unexpected network or background-work surface.

**Independent Test**: Use a protocol fixture labelled as a NuGet lifecycle
fixture, dependency fixtures, and counters for construction, routes, workers,
and external calls. Exercise enabled, disabled, delayed, failing, and
post-startup unhealthy states. This proves lifecycle behavior, not NuGet
restore or storage correctness. This covers FR-009 through FR-014.

**Acceptance Scenarios**:

1. **Given** the protocol fixture is enabled and all selected modules initialize
   successfully, **When** startup completes, **Then** its declared test route
   responds, its worker may run, and the host reports ready.
2. **Given** that same fixture is registered but disabled, **When** the host
   starts with another valid selection, **Then** it is never constructed or
   given lifecycle callbacks, has no mapped routes or running workers, and
   causes zero external connection attempts.
3. **Given** a selected module whose initialization is delayed, **When** the
   host process is live, **Then** readiness remains false and normal module
   traffic and ongoing workers do not run until every selected module is ready.
4. **Given** two enabled modules claiming an ambiguous route and method
   combination, **When** startup composes routes, **Then** startup fails before
   serving module traffic and identifies both owners; registration order does
   not select a winner. A disabled claimant causes no route conflict.
5. **Given** a ready module later reports not ready, **When** readiness is
   evaluated, **Then** the host reports not ready and identifies the module
   without enabling a replacement or advertising it as healthy. Recovery of
   that same module may restore readiness without changing the selection.

---

### User Story 3 - Fail and Stop Without Hiding Partial Startup (Priority: P1)

As an operator, I receive a bounded, actionable failure and ordered cleanup
when startup is interrupted or a module fails, and an orderly stop when I
shut down the service.

**Why this priority**: A partially started host must not masquerade as ready or
leave already acquired resources and workers unmanaged.

**Independent Test**: Inject a failure, cancellation, or timeout at each
activation phase; record traffic admission, lifecycle events, acquired-resource
cleanup, and diagnostics. Repeat with cleanup failures and repeated stop
requests. This covers FR-015 through FR-019.

**Acceptance Scenarios**:

1. **Given** several modules initialized and the next selected module fails or
   times out, **When** startup ends, **Then** the host never reports ready or
   serves module traffic, does not initialize later dependents, reports a
   failed start, and cleans up acquired resources in reverse dependency order.
   The partially initialized failing module is included in cleanup.
2. **Given** initialization is cancelled by a stop request, **When** shutdown
   begins, **Then** no further module starts, the host stays not ready, and
   modules that entered activation receive cleanup appropriate to their phase.
3. **Given** a running host with dependent modules, **When** it stops,
   **Then** readiness becomes false and new module traffic/work stops before
   drain and cleanup; dependents stop before their prerequisites within the
   documented finite shutdown budget.
4. **Given** one cleanup operation fails or exceeds that budget, **When** the
   remaining cleanup is attempted, **Then** the original startup/stop outcome
   and the additional cleanup problem are both reported, other eligible cleanup
   is not skipped because of that error, and the host does not wait indefinitely.
5. **Given** concurrent or repeated lifecycle start/stop requests for one host
   instance, **When** they are coordinated, **Then** each module enters each
   activation phase at most once and resource cleanup is not repeated.

---

### User Story 4 - Correct a Composition from Safe Diagnostics (Priority: P2)

As an operator or provider author, I can distinguish installed, registered,
enabled, ready, and failed modules and identify the change needed to correct a
startup failure without exposing credentials or reading platform source.

**Why this priority**: Explicit errors make an extensible system operable;
package presence alone must not imply active or supported functionality.

**Independent Test**: Review the lifecycle result and diagnostics for the
invalid and failing cases above, including deliberately secret-bearing
provider errors. This covers FR-002, FR-020, and FR-022.

**Acceptance Scenarios**:

1. **Given** an invalid selection, dependency chain, version conflict, route
   collision, or initialization failure, **When** an operator inspects the
   result, **Then** it names the safe module identity, failure phase, violated
   constraint, and corrective action without claiming startup succeeded.
2. **Given** a module error containing a credential, credential-bearing address,
   or secret option value, **When** diagnostics are emitted, **Then** those
   values are absent from normal logs and lifecycle results; a safe error
   category and correlation reference still permit investigation.
3. **Given** a disabled module or an enabled module that has not initialized,
   **When** lifecycle state is inspected, **Then** neither is labelled ready
   or represented as an available active integration.

---

### User Story 5 - Change a Distribution with Explicit Restart (Priority: P2)

As a distribution author or operator, I know when selecting a bundled module
only requires restart and when adding a provider requires rebuilding a custom
distribution, so deployment changes are reproducible.

**Why this priority**: Personal use must remain simple without implying that
configuration can install arbitrary executable code or hot-swap resources.

**Independent Test**: Follow the documented bundled-module selection and custom
package/registration journeys using lifecycle fixtures. Compare the running
selection before and after an explicit restart. This covers FR-001, FR-021,
and FR-022.

**Acceptance Scenarios**:

1. **Given** a distribution containing two compatible fixture choices, **When**
   its operator changes the explicit selection, **Then** the running host
   retains its original composition until restart; the next start validates
   and activates the new selection without rebuilding for a bundled choice.
2. **Given** a provider not included and registered in the distribution,
   **When** its author follows the custom-host instructions, **Then** the
   instructions require adding the package and registration, rebuilding,
   redeploying, and restarting without modifying engine source.
3. **Given** an invalid replacement selection, **When** the new host starts,
   **Then** it fails without silently restoring the previous composition;
   documented recovery requires explicitly restoring a coherent previous
   package/selection set and restarting. Lifecycle cleanup does not claim to
   reverse provider-owned persistent data or schema changes.

### Edge Cases

- Two registrations have the same stable ID even if one is disabled: reject
  the ambiguous registry; never select by registration order.
- A disabled module has incompatible platform ranges: validate its descriptor
  structure, but do not activate it or enforce active-version compatibility
  against it merely because its package is present.
- A dependency target is installed but unregistered, or registered but disabled:
  it cannot satisfy a required dependency or silently become enabled.
- Optional enabled dependencies form a cycle: they are real ordering edges and
  must fail just as required cycles do; absent/disabled optional targets
  contribute no ordering edge.
- No authoritative metadata or artifact provider, or more than one, is selected:
  fail rather than invent defaults. Multiple compatible protocols and identity
  schemes are not an error merely because there is more than one.
- Two enabled routes differ only in a way that still gives ambiguous matching
  for the same request: fail rather than trust declaration order. Same paths
  with disjoint methods or otherwise unambiguous matching are allowed.
- Service or route composition fails before initialization: no module traffic
  is admitted, and resources acquired during the entered phases are released.
- An enabled module described by its author as optional fails initialization:
  explicit enablement makes it required for this startup; no degraded-success
  mode silently disables it. Optional dependency absence is a different case.
- A shutdown request arrives during initialization or readiness transition:
  stopping takes precedence; the host cannot later transition to ready.
- A callback ignores cancellation, a cleanup throws, or the process is forcibly
  terminated: bounded coordination must report incomplete work where possible;
  a still-running timed-out cleanup retains owner/prerequisite resources and
  blocks root disposal while independent safe cleanup may continue;
  trusted in-process code is not sandboxed, and crash cleanup is not guaranteed.
- Provider options or exception text contain secrets: diagnostics must remain
  actionable without copying raw configuration or untrusted exception payloads.
- A valid module is registered twice through different host entry points:
  reject duplicate identity instead of constructing it twice or treating the
  second registration as an override.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A host MUST assemble its registry from explicit registrations of
  providers included in its build, using the F-01 declaration and public
  composition boundary. Registry inspection MUST NOT construct providers or
  perform external I/O. There MUST be no runtime package download, arbitrary
  assembly loading, implicit registration by directory contents, or sandbox claim.
- **FR-002**: Lifecycle results MUST distinguish installed package, registered
  declaration, enabled selection, initializing, ready, not ready, failed, and
  stopping/stopped states. Package presence or declared capability alone MUST
  NOT imply activation, readiness, or an operational support claim.
- **FR-003**: Each start MUST use a fixed explicit selection of registered
  modules. Unknown selections and missing/disabled required targets MUST fail.
  The selection MUST identify exactly one authoritative metadata provider and
  one artifact provider; multiple protocols and identity schemes MAY coexist.
  Validation MUST NOT implicitly enable, substitute, or fall back to a provider.
- **FR-004**: Before module activation, the registry MUST reject duplicate
  stable IDs across all registrations, malformed declarations, and disagreement
  between the declared family and registered provider family. Disabled entries
  MUST remain structurally valid but MUST NOT be activated for validation.
- **FR-005**: Before activation, selected modules MUST pass declared host and
  abstractions compatibility, dependency version/prerelease constraints, and
  required capability checks using the
  [F-01 compatibility policy](../001-provider-contracts/contracts/compatibility.md).
  Unsupported or missing declarations MUST fail without widening ranges,
  inventing support, or relying on package restore success.
- **FR-006**: A selected module's required dependencies MUST be enabled and
  compatible. Optional absent/disabled targets MUST contribute no active edge
  or integration/capability claim. Optional enabled targets MUST satisfy the
  same declared compatibility constraints or fail the entire composition;
  neither the target nor integration may be silently disabled to make it pass.
- **FR-007**: The host MUST establish a deterministic dependency order,
  including present enabled optional edges, with a documented stable tie-break
  for unrelated modules. Self-dependencies and cycles MUST fail before
  activation with the involved dependency path identified.
- **FR-008**: Declaration, selection, and dependency validation MUST complete
  before any selected provider is constructed or receives activation callbacks.
  Service composition, route composition, initialization, readiness admission,
  and shutdown MUST be distinct ordered phases. No dependent may initialize
  before its prerequisites have initialized successfully.
- **FR-009**: Disabled modules MUST receive no construction or service,
  route, initialization, worker, readiness-probe, or shutdown callbacks.
  They MUST expose no routes, start no workers, and attempt no external
  connections. Static descriptive registration is not operational enablement.
- **FR-010**: Only enabled modules MAY contribute operational services, routes,
  and workers. Route composition MUST reject ambiguous method/route ownership
  before module traffic is served, identifying the conflicting modules rather
  than choosing by registration order. Disabled routes MUST not be mapped.
- **FR-011**: Initialization MUST be cancellation-aware and governed by
  documented finite host startup/initialization budgets. Dependencies MUST be
  initialized before dependents. Normal module traffic and ongoing workers
  MUST wait until the complete selected composition has initialized and is
  ready; bounded initialization activity itself is permitted.
- **FR-012**: Every explicitly enabled module MUST initialize successfully for
  startup to succeed, regardless of whether another module calls it optional.
  Failure, cancellation, or timeout MUST fail startup, prevent readiness and
  normal traffic, and prevent later dependent initialization. No automatic
  retry loop or degraded-success fallback is part of this feature.
- **FR-013**: Readiness MUST remain false until all selected modules satisfy
  their declared applicable readiness responsibilities. Readiness MUST remain
  distinct from process liveness and MUST become false before shutdown.
  Diagnostic/liveness inspection MAY be available while normal traffic is
  withheld, subject to the host's security posture.
- **FR-014**: After a successful start, a selected module reporting not ready
  MUST make aggregate readiness false with a safe reason. A later successful
  readiness assessment MAY restore it only for the same selected composition.
  This MUST NOT implicitly restart, replace, or disable modules. Automatic
  request draining on a transient health change is not promised by this feature.
- **FR-015**: Failed or cancelled activation MUST trigger cleanup for every
  entered module phase that acquired resources, including a partially
  initialized failing module, in reverse dependency order. No later module
  initialization may proceed after failure or a stop request.
- **FR-016**: Normal shutdown MUST first remove readiness and stop new module
  request/worker admission, then allow in-flight work to drain within a
  documented finite budget and stop/release dependents before prerequisites.
  Initialization cancelled by shutdown MUST NOT subsequently publish readiness.
- **FR-017**: Cleanup MUST be attempted for the other entered modules even
  when one cleanup fails. The host MUST bound its waiting within the shutdown
  budget, report failed/timed-out or unattempted cleanup explicitly, and retain
  the original failure alongside cleanup errors. It MUST NOT report that
  interrupted cleanup completed or that persistent provider changes rolled back.
  A timed-out cleanup callback that is still executing MUST retain its owner's
  and prerequisites' resources and prevent root disposal; independent safe
  cleanup MAY continue within that same budget. Late completion MUST NOT retry
  cleanup or rewrite an already returned stop outcome.
- **FR-018**: Lifecycle coordination MUST prevent duplicate activation phases
  and duplicate cleanup for one host instance, including concurrent/repeated
  start or stop requests. Restart MUST be a new host lifecycle, not reactivation
  of a partially failed instance.
- **FR-019**: Acceptance MUST exercise enabled/disabled routes, worker and
  connection isolation, invalid registries/selections/dependencies, compatibility
  and route conflicts, initialization failure/cancellation/timeout, runtime
  readiness changes, and normal/failed/partial-start cleanup. Instrumented
  fixtures MUST show permitted behavior as well as rejection; they MUST NOT
  be presented as functioning production providers.
- **FR-020**: Validation and lifecycle failures MUST produce actionable,
  sanitized results identifying a safe module identity, phase, violated
  constraint or dependency path, and corrective action. Normal diagnostics
  MUST NOT emit raw option values, credentials, credential-bearing URLs,
  secret-bearing provider exception payloads, or unbounded provider text.
  A safe error category/correlation reference MUST remain when details are unsafe.
- **FR-021**: A running composition MUST remain fixed. Changes to module
  enablement or authoritative selections MUST require explicit restart and
  complete validation on the next start. Selecting an already bundled and
  registered compatible module MUST not require rebuilding; adding an absent
  package/registration MUST require rebuilding and redeployment. Invalid
  replacement selection MUST fail rather than silently reverting.
- **FR-022**: Operator and author documentation MUST describe curated versus
  custom composition, phase ordering, readiness versus liveness, finite budget
  behavior, diagnostics, controlled initialization, restart and explicit rollback.
  It MUST distinguish lifecycle fixtures from later real providers and retain
  F-01 dependency/trust boundaries and centralized cache/security invariants.
  Provider-owned migrations, data recovery, authorization, and conformance MUST
  NOT be implemented or claimed merely through lifecycle hooks.

### Key Entities *(include if feature involves data)*

- **Module Registration**: An F-01 declaration and provider identity recorded in
  the host build, with no provider instance or implied enablement.
- **Startup Selection**: The fixed enabled module set and authoritative metadata
  and artifact choices for one lifecycle; not a configuration file format.
- **Validated Composition**: Registered selected modules whose declarations,
  compatibility, dependencies, capabilities, cardinality, and ordering passed
  pre-activation checks.
- **Dependency Edge**: A required target or an enabled optional target, with
  version/prerelease obligations and ordering; unavailable optional targets
  create no active edge.
- **Lifecycle State**: The observed phase and readiness/failure status of a
  module and aggregate host for one start/stop attempt.
- **Route Ownership**: The enabled module claiming a method and effective route
  match, allowing conflicts to name their owners without a full protocol.
- **Lifecycle Diagnostic**: Safe phase, module/rule/path, error category,
  corrective action, and correlation information, excluding secrets.
- **Lifecycle Fixture**: Instrumented non-production module supplying observable
  routes, worker/connection counters, and controlled failures/readiness changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across the declaration, selection, and dependency rejection cases
  in Story 1, 100% of invalid starts fail before provider activation, with zero
  implicitly enabled or substituted modules; valid counterparts start in the
  documented dependency order regardless of registration order.
- **SC-002**: In paired enabled/disabled acceptance runs, the enabled protocol
  fixture serves its declared test route after readiness, while its disabled
  counterpart has zero mapped routes, lifecycle callbacks, running workers,
  and external connection attempts.
- **SC-003**: Across delayed, failed, cancelled, timed-out, and stopping startup
  cases, there are zero premature ready results or admitted normal requests/
  workers. After a successful start, readiness loss and recovery match the
  selected modules' reported states without changing the composition.
- **SC-004**: For every normal and partial-start shutdown case, lifecycle
  evidence shows dependent-before-prerequisite cleanup, no duplicate phase
  calls, and no waiting beyond the declared coordination budget; every cleanup
  failure or budget-exhausted omission is explicitly distinguishable from success.
- **SC-005**: Each invalid-composition or lifecycle-failure case provides enough
  safe information to identify the affected module/phase and corrective action
  without source inspection. Zero seeded credential values appear in the
  captured normal diagnostics or lifecycle results.
- **SC-006**: Authors can complete both documented distribution journeys using
  fixtures: switch a bundled choice after restart with zero rebuilds, and add
  an independent provider through custom composition with zero engine changes.
  A changed selection never mutates an already running composition.
- **SC-007**: Every delivered example, lifecycle result, and support statement
  distinguishes installed, selected, and operationally ready functionality;
  zero fixture proofs are advertised as production protocols, stores, identity
  schemes, cache behavior, or certification.

## Assumptions

- The ratified [constitution](../../.specify/memory/constitution.md), architecture,
  ADR-0001, and merged [F-01](../001-provider-contracts/spec.md) govern this work.
  F-01's feature and separate completion checkpoint are merged prerequisites.
  This specification stage creates requirements only; it neither plans nor
  implements lifecycle behavior.
- F-01 supplies metadata/type registration, not construction or activation.
  F-02 builds a separate validated lifecycle on that boundary rather than
  treating registration as execution or rewriting F-01's delivered claims.
- Explicit registration is the initial discovery mechanism. Packages are
  trusted in-process code, including static metadata access; disabled-module
  guarantees describe host-controlled execution, not a sandbox against
  malicious code or arbitrary static side effects.
- F-02 may accept an explicit in-memory startup selection for acceptance.
  It owns the lifecycle gate and basic selection/dependency safety, including
  enforcing the existing compatibility policy; it does not require the future
  configuration feature to exist before fixture-based validation is possible.
  F-03 owns configuration sources/precedence, option schemas and semantic
  option validation, secret resolution, migrations, and full operator selection
  UX, consuming the same gate rather than redefining compatibility.
- All explicitly enabled modules are required for a successful start. Optional
  means a dependency may be absent/disabled, not permission to continue after
  an enabled module fails. No degraded startup or automatic enablement is assumed.
- Exact public signatures, state representation, route-collision inspection,
  budget defaults, and documented stable ordering tie-break are planning
  decisions. Budgets must be finite and observable; this feature does not
  promise a production startup latency benchmark or forcibly terminate
  non-cooperative trusted code.
- Readiness is a truthful health signal after successful startup, not a promise
  of automatic failover or per-request protection from later resource failures.
  Existing centralized security and provider error handling remain mandatory.
  Lifecycle-only fixtures need no externally reachable listener. Any introduced
  network listener must obey loopback-first and authenticated/authorized
  network-management constraints; no new anonymous management surface is granted.
- Initialization may prepare provider resources under explicit operational
  policy. It is not permission for uncontrolled schema upgrades or destructive
  migration. Failure cleanup releases resources, not a cross-provider data
  transaction, crash-recovery guarantee, or schema rollback.
- F-04 owns authorized management discovery and UI representation; no discovery
  endpoint or console is delivered here. F-05/F-06 own metadata/artifact
  operations; F-07 owns reusable conformance/certification; F-08 and SPEC-18/24
  own detailed identity/security behavior. SPEC-01 owns the runnable curated
  host and profiles, concrete provider features supply NuGet/SQLite/filesystem,
  and SPEC-09 owns native-client protocol evidence.
- Lifecycle acceptance may use instrumented modules in all required families
  and a NuGet-labelled route fixture without implementing a cache or claiming
  real NuGet v3 support. It needs no cloud account, production database,
  external identity provider, UI, deployment, or infrastructure application.
