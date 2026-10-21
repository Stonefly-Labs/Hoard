# Feature Specification: Module Capabilities and Management Discovery

**Feature Branch**: `feature/004-module-discovery`

**Created**: 2026-10-21

**Status**: Draft requirements only; no discovery endpoint, management screen,
production provider or new runtime behavior is delivered by this stage.

**Input**: User description: "Specify a management experience where users can inspect installed, enabled and healthy Hoard modules, what each supports, and why a capability is unavailable. Include secure API discovery, UI representation, actionable diagnostics and truthful feature advertisement."

**Backlog**: [F-04](../../docs/HOARD_SPECKIT_MASTER_BACKLOG.md#foundation-f-04)

**Feature Directory**: `specs/004-module-discovery`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inspect the Actual Distribution and Running Selection (Priority: P1)

As an operator, I can inspect which modules my distribution includes, which are
registered and enabled, and their observed health, so package presence is not
mistaken for usable functionality.

**Why this priority**: Every capability claim depends on a truthful inventory
and a clear distinction between availability, selection and runtime condition.

**Independent Test**: Inspect a fixture distribution with enabled, disabled and
included-but-unregistered modules, plus a requested absent module. Compare the
inventory with its explicit distribution records, configuration and lifecycle
observations, without constructing disabled providers. This covers FR-001
through FR-004, FR-008 and FR-021.

**Acceptance Scenarios**:

1. **Given** a distribution containing registered modules from each provider
   family, **When** an authorized operator inspects discovery, **Then** each
   module has its stable identity, category, version, provenance/support
   classification, registration, enablement and observed readiness shown
   separately; the selected authoritative metadata and artifact providers are
   identifiable without exposing their settings.
2. **Given** an included but unregistered module and a registered disabled
   module, **When** their entries are inspected, **Then** the former is not
   selectable through configuration alone, the latter is labelled disabled
   rather than unhealthy, and neither contributes an operational capability.
3. **Given** a requested module absent from the distribution or a package whose
   inclusion is not known, **When** a diagnostic or consumer represents it,
   **Then** absence is reported only when established, otherwise inclusion is
   unknown; neither case invents an installed, registered or healthy module.
4. **Given** a registered disabled module with missing operational settings,
   unavailable secrets or incompatible active-version ranges, **When**
   discovery is inspected, **Then** its descriptive metadata remains visible
   without option checks, secret resolution, activation or connection attempts,
   preserving the existing disabled-module rules.

---

### User Story 2 - Know What Is Supported and Usable Now (Priority: P1)

As an operator or management consumer, I can distinguish a declared feature
from supported, currently usable functionality and understand why it is
unavailable, so discovery never promises a route or operation that cannot work.

**Why this priority**: Truthful feature advertisement prevents misleading
setup guidance and unsafe assumptions by downstream management experiences.

**Independent Test**: Compare discovery with instrumented fixture routes and
service availability across compatible, disabled, initializing, ready,
not-ready and stopping states. Include dependencies, unsupported operations
and fixture-only support claims. This covers FR-005 through FR-010,
FR-015 and FR-022.

**Acceptance Scenarios**:

1. **Given** a compatible ready selection with implemented fixture operations,
   **When** capabilities are inspected, **Then** every advertised usable
   operation has its actual enabled route or service and required dependencies;
   no disabled, absent or merely prospective operation is advertised as usable.
2. **Given** an installed module declaring a feature that the distribution
   does not implement or qualify, **When** discovery is inspected, **Then**
   that declaration may be described but is not labelled supported or usable;
   fixture evidence is not presented as production or native-client support.
3. **Given** an integration with an absent or disabled optional dependency,
   **When** its capability is inspected, **Then** that integration is
   unavailable with a dependency reason while unrelated supported operations
   remain independently described; an enabled incompatible target still fails
   the existing composition gate rather than being hidden by discovery.
4. **Given** a ready module becomes not ready or the host starts stopping,
   **When** a fresh observation is requested, **Then** readiness and affected
   capability availability reflect that observation without changing enablement
   or support classification, and process liveness is not reported as readiness.
5. **Given** a failed start that never exposes a management service, **When**
   the operator follows diagnostic guidance, **Then** the safe existing
   startup report explains the failure; discovery does not start another
   listener or report the failed selection as a running healthy service.

---

### User Story 3 - Inspect Safely with the Right Management Access (Priority: P1)

As an operator, I can grant read-only management inspection without granting
module changes or exposing credentials and deployment internals to other
callers.

**Why this priority**: Discovery introduces a management network surface;
access control and secret protection must be present at introduction.

**Independent Test**: Exercise local and network-exposed fixture hosts with
authorized, unauthenticated and insufficiently authorized callers. Seed secret
values, reference locators and unsafe provider text into inputs and failures;
inspect responses, discovery documentation and captured diagnostics. This
covers FR-011 through FR-014, FR-016 and FR-020.

**Acceptance Scenarios**:

1. **Given** explicit management-read access, **When** the caller requests
   inventory, capability details or sanitized option definitions, **Then**
   inspection succeeds without granting configuration writes, activation,
   secret access or permission to execute the described operation.
2. **Given** network-exposed management, **When** an unauthenticated or
   insufficiently authorized caller requests discovery or its API description,
   **Then** access is denied without module/configuration disclosure; exposure
   without the documented authentication, authorization and TLS/trusted-proxy
   posture is rejected, not repaired with anonymous access.
3. **Given** the documented loopback-only local policy, **When** a permitted
   local caller inspects discovery, **Then** no external identity or cloud
   account is required; the policy cannot silently authorize a network caller
   or trust caller-supplied forwarding headers.
4. **Given** secret-bearing settings, file/environment references, unsafe
   descriptive text and collaborator failures, **When** all discovery surfaces
   and normal diagnostics are captured, **Then** they contain no seeded
   secrets, locators, configured values or raw exception payloads; safe field
   identities, types, constraints and required/secret classifications remain.

---

### User Story 4 - Represent Availability Clearly in Management Views (Priority: P2)

As a management user, I can recognize a disabled module, missing support,
temporary unhealthiness and a failed refresh without reading source code or
being invited to run an unsupported action.

**Why this priority**: A truthful discovery response only helps users if its
consumer preserves the distinctions and explains practical next steps.

**Independent Test**: Apply discovery examples to the bounded presentation
contract and a reference consumer fixture. Check state labels, available
actions and explanations for each state, including unknown future fields,
loading, empty and error results. This covers FR-015 through FR-020
and FR-022.

**Acceptance Scenarios**:

1. **Given** otherwise similar absent, unregistered, disabled, unsupported and
   temporarily not-ready entries, **When** they are represented, **Then** each
   has a distinct textual state and appropriate next step, not one generic
   unavailable or green/red badge.
2. **Given** an unsupported operation or a supported but temporarily unavailable
   operation, **When** actions are represented, **Then** unsupported actions
   are hidden and temporarily unavailable actions are non-invocable with a
   safe explanation; inventory details still explain missing support.
3. **Given** slow loading, no registered modules, denied access, a failed
   refresh or a response the consumer cannot interpret, **When** the view
   updates, **Then** each condition is explicit rather than shown as healthy,
   empty success or continued current availability; retained observations
   are marked stale and cannot authorize actions.
4. **Given** keyboard, non-color and assistive-technology inspection of the
   presentation examples, **When** status and corrective guidance are
   evaluated, **Then** their meaning and action eligibility remain available
   through labels and logical reading/focus order, without color-only,
   hover-only or motion-dependent explanations.
5. **Given** safe diagnostic categories for missing packages, disabled choices,
   invalid configuration and readiness failure, **When** a user follows the
   guidance, **Then** it distinguishes configuration plus restart, custom
   package inclusion plus rebuild/redeploy/restart, and provider-specific
   investigation; no discovery action installs or hot-swaps a module.

---

### User Story 5 - Refresh a Consistent, Bounded Observation (Priority: P2)

As an operator or consumer author, I can refresh discovery and recognize which
running instance and observation it describes, without activating modules or
depending on external services.

**Why this priority**: A fast but mixed or stale report can be as misleading as
an incorrect capability declaration.

**Independent Test**: Refresh while fixture readiness changes, shutdown begins
and a replacement host starts. Use cancellation and unavailable observation
sources, then compare all results with their lifecycle and observation identity.
This covers FR-008 through FR-010, FR-017, FR-019 and FR-021.

**Acceptance Scenarios**:

1. **Given** readiness changes during inspection, **When** a discovery result
   is returned, **Then** its module states, aggregate readiness and derived
   capability states belong to one identified coherent observation, not a
   mixture of old and new states.
2. **Given** configuration edits or a newly deployed distribution, **When**
   discovery is refreshed before and after explicit restart, **Then** the
   old lifecycle retains its fixed selection and the new one has a distinct
   lifecycle identity; old observations are never presented as the new host.
3. **Given** cancellation or an unavailable observation source, **When**
   refresh cannot complete within its documented finite budget, **Then**
   failure is explicit, no unknown state becomes healthy or usable, and
   discovery does not activate, probe, restart or otherwise mutate a provider.
4. **Given** repeated and concurrent inspection of a representative local
   distribution, **When** results are refreshed, **Then** they meet the bounded
   inspection target without external calls, extra readiness callbacks,
   secret resolution or growth in active module resources.

### Edge Cases

- A binary is present but no explicit inclusion or registration record exists:
  report only established knowledge; do not scan/load arbitrary code to fill
  an inventory gap.
- A disabled module has invalid active options or an inaccessible secret:
  descriptive inspection must not introduce a second activation gate.
- Multiple modules declare the same capability identity: attribute each
  contribution to its owner and scope; do not merge incompatible versions or
  imply that one ready contributor satisfies another's requirements.
- One operation requires several modules while another needs only one:
  compute availability per operation rather than copying a global green badge.
- A module is healthy but the distribution has not qualified its declaration:
  health does not promote declared support into tested support.
- A capability has no HTTP route because it is a service feature: do not invent
  an endpoint; conversely, a declared route that is not actually enabled cannot
  establish usable functionality.
- A runtime readiness loss leaves routes mapped under the existing lifecycle:
  report not-ready accurately without claiming that discovery drained traffic,
  removed routes or revoked another request's authorization.
- A failed start or shutdown leaves no reachable management surface: safe local
  reports remain the fallback diagnostic channel, not a new unsecured listener.
- An unknown module, capability state or response version reaches an older
  consumer: preserve safe known information but never infer action eligibility
  or treat an incompatible response as a successful empty inventory.
- Descriptions contain markup, control characters, long text or credentials:
  constrain and present inert safe text; never execute it or copy raw payloads
  into errors.
- A request arrives during an observation update or shutdown: return a coherent
  identified observation or explicit failure, never mixed or fabricated success.
- A consumer retains a previously ready result after access denial, transport
  failure or host replacement: label it stale and do not derive current actions
  or permissions from it.
- A caller has management-read access but lacks a described operation's own
  permission: capability availability is not authorization to execute it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Authorized users MUST be able to inspect the distribution's known
  included module inventory and registered declarations, distinguishing known
  inclusion, registration and enabled selection. Absence MUST be asserted only
  when authoritative inclusion information establishes it; otherwise inclusion
  is unknown. Discovery MUST NOT discover packages by arbitrary assembly
  loading, runtime downloads, provider construction or external I/O.
- **FR-002**: Each known module entry MUST expose a safe stable ID, category,
  module version, declared platform compatibility, provenance/support
  classification and descriptive capabilities. Unknown provenance or support
  evidence MUST remain unknown/unverified, not official, certified or supported
  by inference from packaging or successful startup.
- **FR-003**: Discovery MUST separately represent inclusion/registration,
  enablement, lifecycle phase, observed readiness and support classification.
  Disabled, initializing, ready, not-ready, failed, stopping/stopped and unknown
  observations MUST NOT collapse into one healthy/unhealthy flag. Selected
  authoritative metadata/artifact providers and selected identity schemes MUST
  be identifiable without exposing configured values.
- **FR-004**: Inspection of a disabled registration MUST remain descriptive:
  no operational option validation, secret resolution, provider construction,
  readiness callback, route/worker activation or connection attempt. Unknown
  required settings and active-version incompatibility MUST NOT turn a disabled
  entry into an active failure. Existing structural validation is unchanged.
- **FR-005**: Capabilities MUST have stable identities, documented meanings and
  owning-module/operation scope, distinguishing declaration, distribution
  support and current availability. Support MUST require explicitly identified
  implemented and tested behavior for the distribution; unknown or prospective
  declarations MUST NOT become supported through health or package presence.
- **FR-006**: A capability MAY be advertised as currently usable only when its
  implementation is supported for that distribution, its owners and required
  dependencies are enabled/compatible, its actual route or service is composed,
  and the applicable observed lifecycle readiness permits its use. Unavailable
  optional targets confer no integration. An enabled incompatible optional
  target MUST still fail the inherited composition gate.
- **FR-007**: Capability availability MUST be scoped to the described operation,
  its contributors and dependencies. Overlapping declarations MUST retain
  ownership and version/scope distinctions rather than silently unioning them.
  Each unavailable or indeterminate capability MUST provide a safe reason
  category and actionable next step; unknown inputs MUST NOT yield usable.
- **FR-008**: Discovery MUST consume the established registration,
  configuration and lifecycle authorities from
  [F-01](../001-provider-contracts/spec.md),
  [F-02](../002-module-lifecycle/spec.md) and
  [F-03](../003-provider-configuration/spec.md). It MUST NOT reimplement their
  validation, readiness, activation or secret-resolution rules, run extra
  health probes, change selections or silently repair a failed composition.
- **FR-009**: Each successful result MUST identify its response version,
  distribution, host lifecycle and observation freshness, with module states,
  aggregate readiness and capability derivations drawn from one coherent
  observation. Refresh MUST reflect new published readiness/stopping states;
  liveness MUST remain distinct. Readiness loss MUST NOT be described as
  automatic traffic draining or route removal unless the lifecycle does so.
- **FR-010**: Failed or unavailable observation MUST produce an explicit safe
  failure or identified unknown state, never a fabricated healthy result.
  A failed startup MUST NOT be made successful to expose discovery; when no
  management surface exists, guidance MUST use existing safe local diagnostics.
  Discovery MUST NOT introduce a separate diagnostic listener.
- **FR-011**: Inventory, capability details, option metadata and discovery API
  descriptions MUST enforce the same explicit management-read access boundary.
  Network management MUST require authenticated, authorized access and the
  documented TLS or trusted-proxy posture from its first exposure; absent or
  misconfigured protection MUST fail closed. Unauthenticated/unauthorized
  callers MUST receive no deployment inventory or settings information.
- **FR-012**: Loopback-only personal inspection MAY use an explicitly documented
  local anonymous management policy without cloud or external identity
  dependencies. Network exposure MUST be explicit and MUST NOT inherit that
  exception or trust unvalidated caller-supplied forwarding headers. Detailed
  discovery MUST NOT be placed on an unauthenticated liveness surface.
- **FR-013**: Discovery MUST expose only sanitized descriptive configuration
  metadata: safe setting identity, description, type, required/optional and
  secret classification, constraints and approved non-secret public defaults.
  Effective configured values, raw configuration, secret values/locators,
  credential-bearing addresses, private file paths and source payloads MUST
  NOT appear in responses, descriptions, examples, errors or emitted telemetry.
  No discovery request may resolve a secret.
- **FR-014**: Provider-supplied text and failure payloads MUST be bounded,
  sanitized and inert on all discovery surfaces. Unsafe or unknown text MUST
  be replaced by safe categories rather than echoed. Every failure MUST retain
  a safe affected identity where possible, phase/reason, corrective guidance
  and correlation reference without exposing raw collaborator exceptions.
- **FR-015**: Diagnostics and representation MUST distinguish at least missing
  inclusion, missing registration, disabled selection, unsupported/unverified
  implementation, unavailable dependency, initializing, not-ready, stopping
  and unknown observation. Corrective guidance MUST distinguish configuration
  plus restart, package inclusion/registration plus rebuild/redeploy/restart,
  and investigation of configuration or runtime failures; it MUST NOT suggest
  automatic install, hot replacement or data rollback.
- **FR-016**: Discovery MUST be read-only. Inspection permission MUST NOT grant
  configuration mutation, module activation, secret access or permission to
  execute a described operation. Each operation's own authorization MUST
  remain authoritative; capability availability is not a permission grant or
  a substitute for execution-time checks.
- **FR-017**: The management presentation contract MUST preserve discovery's
  independent state dimensions, safe reasons and observation freshness.
  Loading, genuinely empty, denied, failed, unknown and stale results MUST be
  distinct. Retained data after a failed refresh MUST be labelled stale and
  MUST NOT establish current availability or action eligibility.
- **FR-018**: Management consumers MUST hide unsupported actions and make
  supported but currently unavailable actions non-invocable with a safe
  explanation. Unknown state/meaning or incompatible response versions MUST
  fail closed for action eligibility, not hide an error as empty success.
  Inventory details MUST still explain unsupported and unavailable features.
- **FR-019**: Presentation requirements and examples MUST communicate states
  and guidance through text and logical reading/focus order, not color,
  hover or motion alone, and support keyboard/assistive-technology use under
  the product's WCAG 2.2 AA target. The consumer MUST need only the management
  contract, not provider internals or a server-side console runtime.
- **FR-020**: Discovery MUST provide a documented versioned read contract and
  safe representative examples covering identities, state meanings, permission
  requirements, failure responses and consumer handling of unknown additions
  and incompatible versions. Additive unknown descriptive fields MUST NOT
  authorize unknown operations. Public contract evolution MUST follow the
  existing compatibility policy.
- **FR-021**: Inspection MUST be bounded, cancellation-aware and independent
  of upstream/provider service calls, with a documented finite response
  budget. Repeated/concurrent reads MUST NOT activate modules, resolve secrets,
  add readiness callbacks or accumulate provider resources. A running
  selection remains fixed until explicit restart; a replacement lifecycle
  MUST be distinguishable from retained earlier observations.
- **FR-022**: Acceptance MUST compare capability claims to actual composed
  fixture routes/services and inherited lifecycle observations, with paired
  permitted/rejected cases for selection, dependencies, health changes,
  authorization, redaction, observation failure and consumer action decisions.
  A reference consumer MUST demonstrate the presentation contract without
  claiming a delivered product console. Fixture-only support MUST be labelled;
  no production provider, native-client compatibility, provider conformance,
  curated runnable cache or rendered product UI is implied.

### Key Entities *(include if feature involves data)*

- **Distribution Inventory**: Explicit knowledge of included module packages,
  distribution identity and support evidence; not a runtime code loader or a
  list of everything installed on the machine.
- **Module Discovery Entry**: Safe declaration identity and version, provenance,
  registration/enablement and observed lifecycle/readiness dimensions.
- **Capability Contribution**: A module's versioned, scoped declaration about
  an operation, linked to distribution support evidence, actual route/service
  availability and relevant dependency/readiness requirements.
- **Discovery Observation**: A coherent read result with response version,
  distribution/lifecycle identity, freshness and derived availability; not an
  activation request or a promise of future readiness.
- **Sanitized Option Description**: Public field requirements and secret
  classification without configured values or secret reference locators.
- **Availability Explanation**: Safe reason, affected identity, next step and
  correlation reference when applicable, not copied provider failure text.
- **Management Presentation State**: Consumer interpretation of inventory,
  support, availability, freshness and action eligibility; separate from a
  user's authorization to execute an operation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every inventory acceptance case distinguishes known inclusion,
  registration, enablement, support and observed readiness correctly; zero
  absent, disabled, unknown or fixture-only modules are promoted into a
  functioning production capability.
- **SC-002**: Across every route/service, dependency and lifecycle case in
  Story 2, 100% of usable claims match actual enabled supported operations and
  the same observation's readiness. Disabled/absent optional dependencies
  produce zero integration claims; refresh observes readiness loss and stop
  without changing the selected composition.
- **SC-003**: All unauthorized network inspection and description requests are
  denied with zero inventory/configuration disclosure; permitted local and
  authenticated management-read cases succeed without granting mutation,
  secret access or execution permission. Missing network protection never
  silently enables anonymous discovery.
- **SC-004**: Zero seeded secret values, reference locators, configured values,
  private paths or raw collaborator payloads appear in captured discovery
  outputs, documentation examples, errors or telemetry. Every rejected case
  still offers a safe reason and corrective next step.
- **SC-005**: For every state and failure example in Story 4, the reference
  consumer preserves distinct textual states and guidance, hides all
  unsupported actions and permits zero unavailable/unknown/stale actions.
  State and guidance remain understandable without color, hover or motion.
- **SC-006**: All refresh, cancellation, failure and restart cases return a
  coherent identified observation or explicit failure within the documented
  budget, with zero mixed-lifecycle results, invented ready states, activation,
  secret reads, extra readiness probes or provider service calls.
- **SC-007**: For a representative local fixture distribution of 100 modules
  with 10 capability contributions each, 95% of 100 inspection requests,
  exercised with 10 concurrent readers, present a complete current observation
  within two seconds. The published measurement records environment and input
  bounds, and repeated reads add zero provider resources or external calls.
- **SC-008**: Every documented discovery example states its support/evidence
  scope and observation/authorization limits. Both bundled-choice and custom
  package guidance identify the required restart/rebuild steps without engine
  changes, live installation or unsupported production/conformance claims.

## Assumptions

- The ratified [constitution](../../.specify/memory/constitution.md),
  [architecture](../../docs/ARCHITECTURE.md) and
  [ADR-0001](../../docs/adr/0001-modular-provider-architecture.md) govern this
  feature. F-01 through F-03 and their completion checkpoints are merged
  prerequisites. This invocation writes requirements only, not public
  signatures, routes, endpoint code, projects, tasks or a console.
- "Installed" means known inclusion in the assembled distribution, not all
  binaries on disk or a machine-wide package inventory. Explicit distribution
  inclusion records may describe unregistered packages; where those records
  do not exist, registration alone cannot prove completeness or absence.
  The exact record format and observation representation belong to planning.
- Distribution support describes explicitly implemented and tested behavior
  within a stated scope. It is separate from publisher provenance, compatibility,
  current health and a future category-conformance certification. Foundation
  fixtures may advertise only their tested synthetic operations.
- The management discovery read surface, versioned consumer contract,
  presentation rules and reference consumer examples belong to F-04.
  General management APIs/pagination remain SPEC-10 and the actual
  Next.js console/rendered accessible screens remain SPEC-11 and subsequent UI
  features. F-04 must prove consumer state/action decisions with fixtures,
  not scaffold a frontend or postpone defining UI representation.
- The eventual bundled console remains statically exportable and consumes
  management discovery client-side under the existing product constraints.
  Presentation examples do not establish measured accessibility of screens
  that do not yet exist.
- Management-read authorization uses explicit host-provided policy, including
  validated trusted-proxy integration where chosen. F-04 must define and
  exercise the enforcement boundary using test identities before any network
  exposure; it does not implement production identity schemes, browser login,
  token issuance or the broader F-08/SPEC-18/SPEC-24 workstreams.
- A successful read consumes published observations from the existing
  lifecycle authority rather than probing providers. Timestamp/observation
  identity conveys when readiness was assessed, not continuous monitoring or
  a guarantee that an operation remains healthy after the read.
- The two-second representative inspection target is a bounded local
  acceptance baseline, not a public network latency or production-scale SLA.
  Exact response size/text limits, finite timeout values, safe reason
  vocabulary, endpoints, schema and compatibility mechanics belong to planning.
- This feature adds no listener by itself, module install/enable controls,
  live configuration reload, schema/data migration, caching engine, production
  provider, external identity/cloud dependency, package publication or product
  CI/deployment. Discovery must not bypass centralized security/correctness or
  cross provider and vertical-slice dependency boundaries.
