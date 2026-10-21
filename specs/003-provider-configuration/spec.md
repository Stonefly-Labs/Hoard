# Feature Specification: Provider Configuration and Activation Validation

**Feature Branch**: `feature/003-provider-configuration`

**Created**: 2026-10-20

**Status**: Draft requirements; configuration behavior is not implemented by
this specification stage.

**Input**: User description: "Specify secure, intelligible configuration of installed Hoard modules, including enablement, provider selection, per-provider settings and secret references. Include precedence, invalid configurations, disabled modules, compatibility failures, safe migration, diagnostics and restart behavior."

**Backlog**: [F-03](../../docs/HOARD_SPECKIT_MASTER_BACKLOG.md#foundation-f-03)

**Feature Directory**: `specs/003-provider-configuration`

## Clarifications

### Session 2026-10-20

No critical ambiguities detected worth formal clarification. Zero questions
were asked or answered; no requirements, acceptance criteria or scope decisions
changed.

All ten review categories are clear for this bounded feature: functional scope
and behavior, domain and data model, interaction and operator journeys,
applicable non-functional quality attributes, integration and external
dependencies, edge cases and failure handling, constraints and tradeoffs,
terminology and consistency, completion signals, and placeholders.

The existing requirements distinguish structural checks from effective-value
validation, whole-selection replacement from keyed option merging, and disabled
declarations from active compatibility and secret resolution. They preserve the
existing lifecycle gate, prohibit fallback, fix settings and resolved secrets
until restart, and require bounded coordination with pending-resource retention
and safe late-fault observation. Version conversion separates the private
replacement from the sanitized preview, retains the original on interruption,
and does not claim to reverse provider-owned data changes.

Exact configuration/reference syntax, canonical naming rules, option-contract
representation and ownership, supported version mappings, safe report layout
and finite budget values remain planning decisions under these observable
requirements. Production throughput/scale targets, management/UI behavior,
real-provider data recovery and cloud secret integrations remain outside this
feature as assigned in Assumptions. Synthetic conversion fixtures cannot imply
released-format compatibility. No consequential product decision blocks
planning; no custom checklist approval or runtime evidence is implied.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Know Which Configuration Will Be Used (Priority: P1)

As an operator, I can combine a documented configuration file with deployment
overrides and understand the resulting choices before modules activate, so
local and shared installations behave reproducibly.

**Why this priority**: Selection and validation are only intelligible when the
source of each effective choice is deterministic rather than hidden.

**Independent Test**: Supply fixture module declarations and conflicting values
through each supported source. Inspect the safe configuration result without
constructing providers. This covers FR-001 through FR-005 and FR-024.

**Acceptance Scenarios**:

1. **Given** the same setting in distribution defaults, the configuration file,
   environment overrides and command-line overrides, **When** configuration is
   resolved, **Then** command line wins over environment, environment over file,
   and file over defaults, with the winning source kind and canonical setting
   identified without exposing its value.
2. **Given** a higher-priority source supplies an enabled-module list or
   authoritative provider selection, **When** sources are combined, **Then**
   that whole selection replaces its lower-priority counterpart; lists are
   never implicitly unioned, while unrelated provider setting keys are retained.
3. **Given** duplicate assignments within one source, an unknown setting or an
   unreadable explicitly requested file, **When** configuration is checked,
   **Then** the result identifies the ambiguity or unavailable source and fails
   rather than using an arbitrary winner or continuing with defaults.
4. **Given** a documented distribution default selection, **When** an operator
   supplies no override, **Then** that selection is still validated against the
   actual registered modules; an explicit empty or invalid override never
   restores a lower-priority default to make startup succeed.

---

### User Story 2 - Activate Only a Valid Intended Composition (Priority: P1)

As an operator, I can select installed providers and their settings with clear
pre-start errors, so a typo, incompatible dependency or disabled module cannot
turn into unintended functionality.

**Why this priority**: Configuration must preserve the existing lifecycle
safety gate, not create an alternative activation path or insecure fallback.

**Independent Test**: Resolve selections and option sets for instrumented
fixtures, then submit valid results to the existing lifecycle. Pair every
rejection with a valid counterpart and record construction, routes, workers and
connection attempts. This covers FR-006 through FR-012 and FR-025.

**Acceptance Scenarios**:

1. **Given** multiple registered protocols and identity schemes plus exactly
   one selected metadata and artifact provider, **When** valid configuration
   starts the host, **Then** only the selected modules activate and the existing
   lifecycle decides ordering and readiness.
2. **Given** an unknown or unregistered provider, zero or multiple authoritative
   choices, conflicting enablement and selection, a missing required dependency,
   a cycle, incompatible versions or an unsupported required capability,
   **When** configuration is validated, **Then** startup fails before provider
   construction with no substitute, automatic enablement or package download.
3. **Given** an enabled module with missing, mistyped, out-of-range or
   semantically inconsistent settings, **When** its configuration is checked,
   **Then** activation is blocked and the safe module, setting, rule and
   corrective action are reported; an arbitrary provider error is not echoed.
4. **Given** a registered but disabled module with absent required settings,
   incompatible active-version ranges or an unavailable secret reference,
   **When** another valid selection starts, **Then** that disabled module is
   neither activated nor asked to resolve secrets or validate operational
   settings; malformed structure, unknown keys and duplicate identities still fail.
5. **Given** an optional dependency, **When** its target is absent or disabled,
   **Then** it contributes no integration or capability; **When** the target is
   enabled but incompatible, **Then** the configuration fails without silently
   disabling either the target or the integration.

---

### User Story 3 - Supply Secrets Without Leaking Them (Priority: P1)

As an operator, I can reference credentials held outside normal configuration
and receive safe failures, so deployment troubleshooting does not disclose
credentials or require a cloud secret service.

**Why this priority**: Secret handling is part of introducing configuration,
not a later hardening step.

**Independent Test**: Use environment and mounted-file secret fixtures with
seeded payloads. Exercise success, absence, access denial, malformed references,
resolution timeout and secret-bearing validator errors. Inspect captured normal
outputs as well as activation counters. This covers FR-013 through FR-017
and FR-024 through FR-026.

**Acceptance Scenarios**:

1. **Given** an enabled provider requiring a credential, **When** its secret
   reference points to an available environment value or readable mounted
   file, **Then** that credential is provided only to its selected owner for
   this startup and is absent from the safe configuration report.
2. **Given** a missing, empty, inaccessible, unsupported or malformed required
   reference, **When** resolution is attempted, **Then** startup fails without
   provider construction, anonymous access, an empty credential or a substitute
   source; the diagnostic identifies the setting and corrective action safely.
3. **Given** raw credential text in a secret-marked setting or a credential
   embedded in an address, **When** configuration is checked, **Then** the
   unsupported representation is rejected without repeating the credential.
4. **Given** a resolver or option validator that fails, ignores cancellation or
   includes secrets in an error, **When** the finite configuration budget expires
   or validation fails, **Then** the host remains not ready, never activates a
   provider and reports a bounded sanitized failure, not a successful fallback.
5. **Given** secret values and locators seeded into configuration and failing
   collaborators, **When** normal logs, errors, reports and captured telemetry
   are inspected, **Then** none contains those payloads; safe setting/source
   categories and a correlation reference remain available.

---

### User Story 4 - Change Settings Through an Explicit Restart (Priority: P2)

As an operator, I can change a bundled provider or its settings deliberately
and recover from an invalid replacement without mutating a running service.

**Why this priority**: Predictable restart and recovery matter more than
suggesting that configuration can install code or safely hot-swap resources.

**Independent Test**: Run fixture hosts before and after changing configuration
and secret targets. Exercise both a bundled selection switch and an absent
custom provider, then follow the documented recovery steps. This covers FR-018
through FR-020 and FR-026.

**Acceptance Scenarios**:

1. **Given** a running valid selection, **When** its source file, environment,
   settings or secret target changes, **Then** its active configuration remains
   unchanged until explicit restart; the next start resolves and validates anew.
2. **Given** two bundled and registered compatible choices, **When** the
   documented selection change is applied and the host restarts, **Then** the
   replacement is used without rebuilding and the formerly selected module
   has no active routes, workers or connection attempts.
3. **Given** a requested provider absent from the distribution, **When** an
   operator follows the custom-distribution instructions, **Then** adding its
   package and registration requires rebuild, redeployment and restart, not
   runtime download or edits to the caching engine.
4. **Given** invalid replacement configuration, **When** restart fails,
   **Then** no previous configuration is silently restored; the operator can
   explicitly restore a compatible previous configuration and secret-reference
   set and restart, subject to separately documented provider data compatibility.

---

### User Story 5 - Upgrade Configuration Without Losing the Original (Priority: P2)

As an operator, I can recognize configuration version incompatibility and
review a safe conversion before replacing anything, so upgrades do not
silently change provider choices, credentials or persistent data.

**Why this priority**: Configuration evolution needs an explicit recovery path
before the first incompatible change, without pretending storage migrations
are configuration edits.

**Independent Test**: Use current, explicitly supported older and unsupported
configuration-version fixtures. Compare original and proposed configuration,
effective selections and safe reports; simulate an interrupted conversion.
This covers FR-021 through FR-023 and FR-026.

**Acceptance Scenarios**:

1. **Given** configuration with a missing, malformed or unsupported version,
   **When** it is read, **Then** startup fails with safe upgrade guidance before
   activation and does not rewrite or guess its meaning.
2. **Given** a documented supported older version, **When** an operator requests
   a migration preview, **Then** the original stays unchanged and the proposed
   conversion identifies selection, source and setting changes without
   materializing secret values or silently widening access.
3. **Given** a reviewed valid conversion and a retained original, **When** the
   operator explicitly applies it, **Then** the complete replacement is either
   available for a later validated restart or not published at all; an
   interruption never leaves a partially overwritten original.
4. **Given** an incompatible provider data/schema upgrade, **When** configuration
   rollback is considered, **Then** instructions require the provider's separate
   backup/restore or compatibility procedure and do not claim that restoring
   configuration reverses data changes.

### Edge Cases

- A higher-priority source explicitly clears a required selection or supplies
  an invalid value: fail rather than reinstate a lower-priority value.
- Two names normalize to the same setting within one source: reject the
  duplicate; case or alternative spelling must not create a hidden override.
- A malformed or unknown supplied setting belongs to a disabled module:
  structural/name validation still fails, but disabled operational requirements
  and secret targets are not evaluated.
- An overridden lower-priority setting is structurally valid but semantically
  invalid for the active provider: evaluate effective semantics, not the
  discarded value; unknown keys and malformed source structure still fail.
- A selected authoritative provider is omitted from explicit enablement, or
  selection and enablement disagree: fail rather than implicitly enable it.
- A registered disabled module has an incompatible active-version range:
  retain the existing lifecycle distinction between valid declaration structure
  and active compatibility; do not introduce a stricter parallel gate.
- An enabled optional dependency is incompatible: reject the composition;
  absent/disabled optional targets still provide no active integration.
- A disabled module's secret target is nonexistent or inaccessible: do not
  resolve it, report it as a startup dependency or contact an external service.
- A secret target changes during resolution: one resolved value is fixed for
  the affected setting's startup snapshot; no later callback rereads its source.
  Cross-source atomic secret rotation is not promised.
- A resolver returns an empty result, times out or fails late: activation remains
  prohibited; late failure is safely observed without rewriting a returned
  result, retrying activation or exposing a raw exception.
- A configuration source or exception contains credentials in an address,
  key, module identity or reference locator: emit safe bounded categories and
  correlation information, not untrusted text or raw file contents.
- A migration would remove an explicitly selected identity scheme, introduce a
  new default provider or broaden listener exposure: surface the change for
  explicit review; never apply it silently during startup.
- A migration has no safe complete mapping or the previous provider data is
  incompatible: refuse conversion/rollback and require the documented manual
  or backup/restore procedure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Operators MUST have documented distribution defaults, one explicit
  configuration-file source, environment overrides and command-line overrides.
  Their precedence MUST be command line > environment > file > defaults.
  Unconfigured optional sources MAY be absent; an explicitly requested source
  that cannot be read MUST fail. No hidden persisted/UI-managed state may
  override these sources.
- **FR-002**: Sources MUST resolve to canonical setting identities using a
  documented naming/normalization rule. Duplicate assignments to one canonical
  setting within the same source, unknown keys and malformed source structure
  MUST fail, including in overridden or disabled sections. Repeating a setting
  across different sources is a normal precedence case, not a duplicate.
- **FR-003**: Higher-priority values MUST replace lower-priority values for the
  same setting; unrelated provider setting keys MUST remain. Enabled-module and
  identity-scheme lists MUST be replaced as whole selections, never unioned;
  authoritative provider choices are likewise whole values. Explicit empty
  values MUST remain explicit and MUST fail when the effective rule requires a
  value. Only effective values undergo active semantic/range validation.
- **FR-004**: Documented defaults MUST be visible inputs to the same validation
  as operator choices, not recovery fallbacks. Invalid explicit values, absent
  required selections and missing installed providers MUST NOT be repaired by
  lower-priority defaults or a previous successful configuration.
- **FR-005**: One start MUST use a fixed effective configuration, with source
  provenance available for each effective setting. Safe inspection MUST show
  setting identity, winning source kind and validation status without requiring
  source-code inspection or exposing raw values.
- **FR-006**: Configured modules MUST be included and explicitly registered in
  the distribution. Selecting an unknown, absent or unregistered provider MUST
  fail without package download, arbitrary code loading or automatic registration.
- **FR-007**: Effective configuration MUST explicitly identify enabled modules,
  exactly one authoritative metadata provider and one artifact provider, and any
  selected identity schemes. Multiple protocols and identity schemes MAY
  coexist. Authoritative choices and identity selections MUST agree with module
  enablement and registered category; disagreement MUST fail, not enable a target.
- **FR-008**: Configuration MUST consume the existing
  [F-02 lifecycle composition gate](../002-module-lifecycle/spec.md), preserving
  [F-01 compatibility policy](../001-provider-contracts/contracts/compatibility.md)
  for declarations, versions, dependencies, capabilities, cardinality and ordering.
  It MUST NOT implement a divergent acceptance rule or bypass that gate.
  Required targets must be enabled; optional absent/disabled targets confer no
  integration; enabled incompatible optional targets fail the whole composition.
- **FR-009**: Each configurable registered module MUST provide descriptive option
  requirements covering known names, types, required/optional status, constraints,
  safe defaults, secret classification and configuration-version compatibility.
  Descriptions and safe examples MUST require no provider construction, secret
  resolution or external I/O and MUST NOT contain credentials. Exact schema
  representation is a planning decision.
- **FR-010**: Enabled modules' effective options MUST satisfy required fields,
  types, ranges and declared cross-setting rules before activation. Validation
  MUST NOT construct providers, initialize resources or contact provider services.
  Necessary secret resolution is a distinct bounded step; secret-dependent
  validation MUST complete before activation as well.
- **FR-011**: Disabled registered modules MUST remain structurally valid, with
  known setting names and valid reference syntax, but MUST NOT require missing
  operational values, active-version compatibility or secret resolution.
  They MUST receive no operational option callbacks, construction, routes,
  workers or connection attempts. Installed presence is not enablement.
- **FR-012**: Source/structure, selection/composition and non-secret option checks
  MUST pass before any secret is resolved. All required active secret resolution
  and remaining option checks MUST then pass before any provider construction
  or lifecycle activation. Every explicitly enabled module must pass; no
  degraded-start mode may silently remove a failing module.
- **FR-013**: Secret-marked settings MUST accept explicit references rather than
  embedded credential values. Environment-value and mounted-file references
  MUST work without a cloud account. Raw secret literals in ordinary sources,
  command-line arguments, examples or credential-bearing addresses MUST be
  rejected without echoing them. Secret source contents are distinct from
  configuration values that reference those sources.
- **FR-014**: Only documented, explicitly included secret resolvers MAY be used;
  environment and mounted-file resolution form the initial supported set.
  Unsupported reference kinds MUST fail, with no runtime extension loading.
  A required missing, empty, unreadable or denied target MUST fail without
  substituting an anonymous identity, empty credential or alternate source.
- **FR-015**: Resolved secrets MUST be supplied only to their selected owner
  within its startup configuration and MUST NOT enter persisted configuration,
  migration output, safe inspection or ordinary diagnostics. Each setting's
  resolved value MUST remain fixed for that lifecycle; target changes require
  restart and fresh resolution. This does not promise memory isolation from
  trusted in-process code.
- **FR-016**: Configuration evaluation, secret resolution and any author-supplied
  option checks MUST honor cancellation and documented finite coordination
  budgets. Failure, cancellation or timeout MUST prevent activation and readiness.
  Pending trusted work MUST NOT be treated as terminated, have its in-use
  resources disposed, or activate a provider after the result is returned.
  Eventual faults MUST be observed with safe diagnostics, without changing
  returned outcomes or retrying activation.
- **FR-017**: Secret reference grammar and ownership rules MUST be documented,
  with no implicit interpolation, command execution, recursive reference
  expansion or cross-provider access. An explicitly reused reference MAY supply
  multiple selected owners, but does not grant an owner access to another
  provider's option set or all host configuration.
- **FR-018**: Running enablement, provider choices, options and resolved secrets
  MUST remain unchanged by source edits. Changes require explicit restart and
  the complete validation sequence on the new lifecycle. F-02 alone continues
  to own activation, readiness, worker/request admission and shutdown.
- **FR-019**: Switching to an already bundled and registered compatible provider
  MUST require configuration and restart, not a rebuild. Adding a provider
  outside the distribution MUST require explicit package inclusion/registration,
  rebuild, redeployment and restart, without changing cache-engine source.
- **FR-020**: Invalid replacement configuration MUST fail without silently
  restoring previous values. Recovery MUST explicitly restore a coherent
  compatible distribution/configuration/secret-reference set and restart.
  Retaining previous secret values in a generated rollback file is prohibited.
- **FR-021**: Configuration MUST have an explicit supported version and a
  documented relationship to module option versions. Missing, malformed, newer
  or otherwise unsupported versions MUST fail with migration guidance.
  Startup MUST NOT silently rewrite inputs, assume an unknown version or
  apply persistent provider schema/data migrations.
- **FR-022**: For every declared supported configuration conversion, operators
  MUST be able to preview safe changes, retain the original and explicitly
  approve applying a fully validated replacement. Conversion MUST preserve
  explicit choices and secret references or identify any non-preservable change
  for approval; it MUST NOT silently broaden access or introduce new providers.
  Private replacement configuration may retain reference locators; the safe
  preview/report MUST describe reference changes without exposing those locators.
  Failed or interrupted conversion MUST leave the original recoverable and
  MUST NOT publish a partial replacement. Unmappable inputs MUST fail with
  documented manual guidance rather than guessed semantics.
- **FR-023**: Upgrade and rollback instructions MUST distinguish configuration
  conversion from provider-owned schema/data changes. They MUST state compatible
  versions, backup/restore prerequisites and any irreversible step. Restoring
  configuration alone MUST NOT be described as reversing persistent data.
- **FR-024**: Every configuration failure MUST provide a bounded, sanitized
  diagnostic with safe setting/module identity where possible, source kind,
  failure phase/category, violated rule, corrective action and correlation
  reference. Raw values, secret locators/contents, source file text,
  credential-bearing addresses and untrusted collaborator error payloads MUST
  be absent from normal logs, reports, results and emitted telemetry. Unsafe
  identity/path text MUST be replaced by safe categories, not copied verbatim.
- **FR-025**: Invalid provider or identity configuration MUST NOT fall back to
  another store, anonymous mode, broader network exposure or disabled protection.
  Configuration MUST preserve existing loopback-first and explicit secured
  network-management constraints; it does not authorize new listeners or
  introduce identity/authorization mechanisms.
- **FR-026**: Acceptance and operator/author guidance MUST cover source
  precedence/duplicates/empty values, valid and invalid active options,
  disabled isolation, composition compatibility, secret success/failures/
  redaction/budgets, fixed-state restart, bundled/custom journeys and safe
  version conversion/recovery. Paired permitted/rejected fixture evidence MUST
  precede claims of behavior, including at least one representative supported
  conversion and an interrupted conversion; synthetic version fixtures MUST be
  labelled as such rather than claimed as released-format support.
  Examples MUST distinguish fixture configuration
  from production-provider support; no runtime result, conformance, native-client
  support or real data migration is implied by this specification.

### Key Entities *(include if feature involves data)*

- **Configuration Source**: A documented default, file, environment or command-line
  input with a precedence rank and canonical setting assignments.
- **Option Definition**: A provider's descriptive field names, constraints,
  defaults, secret classification and version obligations; not an active provider.
- **Effective Configuration**: The fixed winning selections/options and source
  provenance for one attempted start; raw secrets are excluded from its safe view.
- **Provider Selection**: Enabled registered identities and authoritative
  category choices submitted to the existing lifecycle composition gate.
- **Secret Reference**: An explicit supported environment/file locator associated
  with a secret-marked setting; neither the credential nor a general expression.
- **Resolved Secret**: A sensitive value scoped to selected owners and a lifecycle,
  absent from persisted inputs, reports and migration artifacts.
- **Configuration Diagnostic**: Safe source/setting/category/phase, correction and
  correlation information without copied untrusted payloads.
- **Configuration Conversion**: An explicitly supported version-to-version
  mapping, safe preview, retained original and validated proposed replacement;
  separate from provider data migration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across all four source levels, every tested conflicting setting
  resolves to the documented winner in repeated runs; list replacement never
  silently enables a lower-priority module. Every same-source duplicate, unknown
  key and explicit invalid/empty required value fails without fallback.
- **SC-002**: All invalid selection, compatibility and active-option cases in
  Story 2 fail before provider construction with zero implicit substitutions or
  external provider calls; paired valid choices reach the existing readiness
  gate. Disabled fixtures have zero activation, secret-resolution, route,
  worker and connection events.
- **SC-003**: Both supported local secret sources satisfy a valid selected
  provider, while every missing, empty, denied, malformed, unsupported and
  raw-literal case fails before activation without anonymous/empty substitution.
  Unused disabled secret targets are contacted zero times.
- **SC-004**: Zero seeded credential values, secret locators or untrusted error
  payloads appear in captured normal diagnostics, safe reports, conversion
  previews or telemetry across success and failure cases. Each failure still
  identifies a safe setting/category and corrective action without source
  inspection.
- **SC-005**: Cancelled, failing and non-cooperative configuration checks produce
  a failure within the documented finite coordination budget, with zero ready
  results, late activations or falsely reported resource releases. Observed
  late faults never change an already returned outcome.
- **SC-006**: Operators can complete both documented distribution journeys:
  one bundled switch with zero rebuilds and one custom addition with zero
  engine changes. Source/secret edits change zero active settings before
  restart; valid restart selects the intended replacement and invalid restart
  never silently reuses the last successful configuration.
- **SC-007**: Every declared supported conversion passes original-retention,
  safe-preview, validated-replacement and interruption cases; unsupported or
  unmappable versions cause zero automatic rewrites. Documented recovery
  restores a compatible configuration or explicitly requires separate provider
  recovery, never an unsupported data-rollback claim.
- **SC-008**: Every delivered configuration example and support statement
  identifies its current versus planned status and restart/rebuild obligations;
  zero fixture results are represented as a runnable cache, production provider,
  management UI, real-client compatibility or provider certification.

## Assumptions

- The ratified [constitution](../../.specify/memory/constitution.md),
  [architecture](../../docs/ARCHITECTURE.md), ADR-0001 and merged
  [F-01](../001-provider-contracts/spec.md) /
  [F-02](../002-module-lifecycle/spec.md) govern this work. Their feature and
  completion checkpoints are merged prerequisites. This stage specifies
  requirements only; it creates no parser, resolver, executable or new API.
- Command line > environment > file > documented defaults is the baseline
  precedence. One explicitly chosen file avoids implicit multi-file layering.
  A required configuration version travels with the file/document; equivalent
  no-file distribution defaults must declare their version. Exact syntax,
  canonical names, public signatures, safe report presentation and finite budget
  values belong to planning under these observable rules.
- Distributions may ship explicit known provider choices as defaults; this
  feature does not create a curated executable or assume NuGet/SQLite/filesystem
  implementations exist. Fixture defaults must name actual included registrations
  and pass the same gate, preserving F-02's prohibition on invented fallback.
- File/default option objects combine by canonical setting key; module/scheme
  collections and authoritative choices are whole selections. Explicit emptiness
  is not omission. Default values, if any, are public non-secret documented
  choices, not hidden recovery state.
- Structural option descriptions and pre-activation validation do not permit
  constructing a provider or reaching its services. Provider-authored checks
  remain trusted in-process code; finite waiting does not forcibly terminate
  them or sandbox access to process memory/environment. Resource retention and
  safe late-fault handling apply to any non-cooperative check introduced.
- Environment and mounted-file secret references are sufficient for personal
  and fixture acceptance. External secret services are optional future resolvers,
  not a required cloud dependency. No secret-management service, interactive
  credential editor or general templating/expression language is introduced.
- There is no previously released configuration schema to claim compatible.
  Planning must name the current version and supported conversions explicitly;
  synthetic older-version fixtures may exercise the conversion/recovery
  mechanism but must not invent released-format compatibility. Unsupported
  versions may require manual conversion; no universal converter is promised.
- F-04 owns authorized management discovery and UI; inspection here is a
  host/operator result, not a new network endpoint. F-05/F-06 and concrete
  providers own persistence/storage contracts and data migrations; F-07 owns
  conformance; F-08 and SPEC-18/24 own detailed identity/security integration.
  SPEC-01 owns runnable profiles/host; SPEC-02 owns upstream registry governance.
- Existing public registration/lifecycle compatibility and provider dependency
  boundaries must be preserved. Option metadata and configuration integration
  must not force Core or provider contracts to depend on concrete stores,
  credentials services or management internals. Exact contract changes and
  dependency graphs require later planning and implementation evidence.
- Acceptance may use instrumented non-production providers and isolated local
  secret sources. It requires no cache engine, external database, cloud account,
  real identity service, UI, deployment, infrastructure application or native
  package-manager support claim.
