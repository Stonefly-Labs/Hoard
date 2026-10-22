# Feature Specification: Metadata Persistence Provider Contract

**Feature Branch**: `feature/005-metadata-persistence`

**Created**: 2026-10-21

**Status**: Draft specification; no persistence implementation, schema upgrade,
provider qualification or product runtime is delivered by this stage.

**Input**: User description: "Specify interchangeable Hoard metadata persistence with identical correctness guarantees for registry state, cached entries, transactions, concurrent writes and schema upgrades. Include portability expectations, failure recovery, provider-specific implementation boundaries and measurable conformance."

**Backlog**: [F-05](../../docs/HOARD_SPECKIT_MASTER_BACKLOG.md#foundation-f-05)

**Feature Directory**: `specs/005-metadata-persistence`

## Clarifications

### Session 2026-10-21

No critical ambiguities detected worth formal clarification. Zero questions
were asked or answered; no requirements, acceptance criteria or scope decisions
changed.

All ten review categories are clear for this bounded feature: functional scope
and behavior, domain and data model, interaction and UX flow, applicable
non-functional quality attributes, integration and external dependencies,
edge cases and failure handling, constraints and tradeoffs, terminology and
consistency, completion signals, and miscellaneous/placeholders.

Caller-supplied canonical identities, atomic metadata groups, consistent grouped
reads, revision conflicts and uncertain-commit reconciliation have explicit
observable outcomes. Shared publication authority supplies artifact evidence;
metadata reference checks never authorize physical deletion alone. Ownership
guards reject expired lease holders without promising distributed coordination.
Controlled schema admission, single-upgrader exclusion and tested recovery
preserve committed state without silent reset or fallback.

Real SQLite durability qualification and an independent alternative fixture are
required, but neither implies production provider delivery or generic F-07
certification. Exact operation signatures, common value and page limits,
timestamp precision, finite budgets, reconciliation lifetime, supported schema
paths and proof mechanics remain planning decisions under the existing
requirements. No throughput target, production service-level promise, rendered
UI, cross-engine transfer or multi-node support is in scope. No consequential
product decision blocks planning; this review does not approve custom checklists
or establish runtime evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retain Correctly Isolated Cache State (Priority: P1)

As an operator, I can retain registry settings and cached metadata across
restarts without mixing upstreams, package identities or authorization
contexts, so durable state remains trustworthy regardless of the chosen
metadata provider.

**Why this priority**: Every later cache operation depends on finding the
correct durable record, not merely a record with a similar package name.

**Independent Test**: Store a bounded dataset containing registries, canonical
package identities, cache entries, policies, credential references and access
aggregates. Read it back, restart the durable qualification provider, and
compare values and identity partitions. Include duplicate and invalid records.
This covers FR-001 through FR-004, FR-015 and FR-019.

**Acceptance Scenarios**:

1. **Given** valid registry, package, cache-entry, policy and aggregate records,
   **When** acknowledged changes are read after a clean restart, **Then** their
   values, relationships and supported timestamp precision are preserved.
2. **Given** the same package and request form in two registries or two
   authorization partitions, **When** entries are written and retrieved,
   **Then** neither partition overwrites, reveals or satisfies the other.
3. **Given** two inputs declared equivalent by the caller's canonical identity
   rules and a third distinct input, **When** records are created, **Then**
   the equivalent inputs cannot create duplicate logical identities and the
   distinct input is not merged by provider-specific text comparison.
4. **Given** missing or malformed identity components, invalid relationships,
   or raw credentials in place of secret references, **When** a change is
   submitted, **Then** it is rejected with a safe actionable reason and no
   partial record is retained.
5. **Given** more records than one permitted result page, **When** a consumer
   follows the documented ordering and continuation rules, **Then** reads
   remain bounded and cover an unchanged dataset exactly once; the effect of
   concurrent changes is explicit rather than promising a frozen listing.

---

### User Story 2 - Resolve Concurrent Changes Without Partial Success (Priority: P1)

As a cache or management-operation author, I can group related metadata changes
and detect competing writes, so interrupted work and contention do not produce
lost updates or half-completed operations.

**Why this priority**: A persistence abstraction is not interchangeable if
the same operation silently changes meaning under concurrency or failure.

**Independent Test**: Coordinate competing writers and readers using controlled
barriers, inject failures before and after the durable commit boundary, and
reopen the store after abrupt process termination. Observe logical outcomes,
not implementation-specific lock or transaction names. This covers FR-005
through FR-010, FR-018 and FR-020.

**Acceptance Scenarios**:

1. **Given** an operation changing related records, **When** another consumer
   reads before and after commit, **Then** it observes only committed state;
   a grouped consistent read never combines part of the old group with part
   of the new group.
2. **Given** two writers using the same observed record revision, **When**
   both attempt conflicting changes, **Then** at most one succeeds against
   that revision and the other receives an explicit conflict, not a silent
   overwrite. Concurrent first creation likewise yields one logical identity.
3. **Given** an operation failing or being cancelled before commit, **When**
   its state is inspected or the store restarts, **Then** none of its changes
   are visible and earlier committed state remains intact.
4. **Given** a commit succeeds but its acknowledgment is lost, **When** the
   caller reconciles or retries the same logical operation, **Then** the
   outcome is identified without duplicate changes or duplicate aggregate
   contributions; uncertainty is not reported as a definite rollback.
5. **Given** competing updates, exhausted capacity or an unavailable store,
   **When** an operation reaches its documented finite budget, **Then** the
   caller receives a classified, sanitized failure and safe retry/reconciliation
   guidance rather than endless waiting, empty-success results or an
   unrequested switch to another provider.

---

### User Story 3 - Preserve Artifact References and Coordination Ownership (Priority: P1)

As a cache-operation author, I can publish and remove metadata references
without misrepresenting artifact availability or allowing an expired work
owner to overwrite newer work.

**Why this priority**: Metadata is the visibility boundary for valid cache
entries; a complete transaction alone cannot establish that artifact bytes
were safely committed elsewhere.

**Independent Test**: Use controlled artifact-commit evidence and competing
metadata writers to exercise reference creation, replacement, deletion and
work ownership. Simulate a crash between artifact commit and metadata commit
without requiring a working artifact provider. This covers FR-011 through
FR-014 and FR-016.

**Acceptance Scenarios**:

1. **Given** missing, uncommitted or mismatched artifact evidence, **When**
   a valid cache entry is published, **Then** publication is rejected; with
   accepted committed-artifact evidence, the entry and its metadata references
   become visible together.
2. **Given** a committed artifact followed by failed metadata publication,
   **When** recovery inspects the operation, **Then** no valid cache entry
   exists for it, the unreferenced artifact can be reconciled later, and
   persistence does not pretend it rolled back the artifact store.
3. **Given** multiple entries referencing one digest and a concurrent entry
   replacement or removal, **When** reference state is updated, **Then**
   committed live references are neither lost nor counted twice, and a
   conditional unreferenced determination cannot silently succeed against an
   outdated metadata revision. This alone never authorizes physical deletion
   while readers or other cross-store protections remain relevant.
4. **Given** a work lease expires and a new owner acquires it, **When** the
   former owner attempts a guarded change or lease release, **Then** it
   cannot alter the new owner's work; acquisition, renewal, expiry and release
   have deterministic ownership rules and do not imply multi-node support.

---

### User Story 4 - Upgrade and Recover Durable Metadata Deliberately (Priority: P1)

As an operator, I can determine whether my metadata is compatible, authorize a
supported upgrade, and recover from interruption using a documented backup,
so an application update does not silently destroy persistent state.

**Why this priority**: Provider interchangeability includes safe operation of
existing data, not only successful writes to a new empty store.

**Independent Test**: Exercise a new store, a supported earlier schema, a
newer unsupported schema, interrupted upgrade steps and restoration from a
known backup. Compare logical contents and check readiness admission without
requiring a production host. This covers FR-017 through FR-021.

**Acceptance Scenarios**:

1. **Given** an empty store or a supported compatible schema, **When** the
   documented initialization policy is applied, **Then** the operator can
   distinguish creation, no-change readiness and required upgrade; destructive
   or incompatible changes do not run without explicit authorization.
2. **Given** a supported older schema and a verified recovery point, **When**
   an authorized upgrade completes, **Then** identities, relationships and
   committed values are preserved and the resulting schema version is
   identifiable before normal use is admitted.
3. **Given** an unsupported newer schema, an unsupported upgrade path or a
   failed required upgrade, **When** initialization runs, **Then** normal
   use remains blocked with safe recovery guidance; existing data is not
   reset, downgraded or opened using an incompatible interpretation.
4. **Given** an interruption at each documented upgrade boundary or two
   simultaneous upgrade attempts, **When** recovery runs, **Then** no consumer
   uses a mixed schema, at most one upgrader proceeds, and the operator can
   follow the tested resume-or-restore path.
5. **Given** a backup taken using the provider's documented consistency
   procedure, **When** it is restored with the required compatible application
   version, **Then** the captured metadata is recovered; any artifact-store
   reconciliation needed before cache use is explicit, and rollback never
   assumes every schema change has a safe inverse.

---

### User Story 5 - Qualify an Alternative Without Rewriting Cache Operations (Priority: P2)

As a provider author or distribution maintainer, I can implement and evaluate
the same metadata agreement using a different persistence engine, so choosing
infrastructure does not change cache correctness or force unrelated code
changes.

**Why this priority**: Independent implementation is the proof that the
contract is provider-neutral rather than a wrapper around the first provider.

**Independent Test**: Run the common logical cases against a durable local
qualification provider and an independently implemented alternative fixture,
then swap them in the same consumer. Report durable recovery qualifications
separately from fixture-only semantic results. This covers FR-022 through
FR-024 and the portability aspects of FR-001 through FR-021.

**Acceptance Scenarios**:

1. **Given** two independently implemented qualification providers, **When**
   the same consumer changes its explicit provider selection, **Then** the
   common operations and required correctness outcomes are unchanged without
   modifying cache or management-operation source.
2. **Given** a provider unable to deliver a mandatory guarantee, **When**
   compatibility and conformance are evaluated, **Then** it is not accepted as
   conforming rather than silently weakening atomicity, identity isolation,
   concurrency or durability requirements.
3. **Given** provider-specific schemas, query facilities and failure details,
   **When** a consumer uses the shared agreement, **Then** it requires no
   provider-private types, schema knowledge or migration commands, and errors
   disclose no raw credentials or connection settings.
4. **Given** qualification results for an implementation and version, **When**
   maintainers publish the support scope, **Then** each required case has an
   attributable result, limitations are explicit, and an in-memory fixture,
   successful compilation or declared capability is not advertised as durable
   production support or qualification for an untested provider.

### Edge Cases

- Identity fields differ only by case, Unicode representation, escaped content
  or authorization partition; caller-defined canonical distinctions survive.
- A registry is disabled or removal is requested while cache entries refer to
  it; no silent orphaning or unbounded implicit cascade is permitted.
- Two transactions create the same identity, update the same revision, or
  replace the last artifact reference in opposite orders.
- A consistent grouped read overlaps a commit; separate ordinary reads do not
  implicitly promise one shared historical snapshot.
- Cancellation arrives after durable commit but before the caller receives
  acknowledgment; reconciliation must establish the outcome.
- A logical operation is retried after an uncertain outcome, including an
  access-aggregate contribution that must not be counted twice.
- A lease expires during work, is renewed at its expiry boundary, or is
  reacquired before a previous owner sends a delayed completion.
- A crash leaves a committed artifact with no metadata, or a restored metadata
  backup refers to an artifact absent from the restored storage set.
- Capacity exhaustion or a damaged/unavailable store prevents commit or
  recovery; no repair path silently drops or resets existing records.
- A page continuation is reused with a different filter, ordering or identity
  scope; it is rejected rather than crossing the original query boundary.
- Timestamps fall on expiry or precision boundaries; every provider uses the
  agreement's same ordering, precision and expiry comparisons.
- An upgrade is interrupted before, during or after a durable schema change;
  a second upgrader or older application attempts to open that store.
- A backup is attempted during writes; its documented procedure must either
  capture a coherent recovery point or explicitly require quiescence.
- A diagnostic contains a provider exception, credential-bearing connection
  setting or unauthorized record content; none may leak to logs or consumers.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The metadata agreement MUST cover registry state, canonical package
  metadata, cache entries, committed-artifact references, work leases, policies
  and access aggregates, including bounded retrieval and conditional changes
  appropriate to each entity. Logical validation and result meaning MUST be
  independent of a provider's schema or query facilities.
- **FR-002**: Persistence MUST preserve supplied canonical identities, including
  registry, protocol request/method and response-varying authorization dimensions.
  It MUST enforce their declared uniqueness without independently rewriting
  them or applying conflicting provider-specific comparison rules.
- **FR-003**: Supported values and relationships MUST survive acknowledged
  durable commit and restart. The agreement MUST define common value limits,
  timestamp precision and expiry comparisons; invalid or unrepresentable values
  MUST be rejected explicitly rather than truncated or silently reinterpreted.
- **FR-004**: Required relationships MUST remain valid on creation, replacement
  and deletion. A referenced parent cannot be silently removed; grouped removal
  MUST be explicit, bounded and atomic for the affected metadata.
- **FR-005**: A declared group of related metadata changes MUST commit entirely
  or not at all, without exposing intermediate changes to other consumers.
  Work abandoned before commit MUST not leave visible changes.
- **FR-006**: Consumers MUST be able to request a consistent grouped read of
  related records. Such a read MUST observe one committed logical state;
  independent reads outside that group need not share a snapshot.
- **FR-007**: Conditional updates, deletes and first creation MUST detect stale
  revisions and duplicate identities under competing writers. No conflicting
  update may silently overwrite a change committed since its expected revision.
- **FR-008**: Cancellation and failure outcomes MUST distinguish definite
  non-commit from commit success and uncertain acknowledgment. Repeating or
  reconciling the same logical mutation MUST establish its outcome without
  duplicate effects; the supported reconciliation lifetime and any expiry
  MUST be explicit, with no blind replay after that lifetime.
- **FR-009**: Operations MUST honor cancellation and documented finite work,
  result-size and contention budgets. Exhaustion MUST produce an explicit
  outcome; hidden unbounded retries and enumeration are prohibited.
- **FR-010**: Outcomes MUST distinguish not found, invalid input, identity/revision
  conflict, cancelled-before-commit, unavailable/capacity failure, incompatible
  schema and uncertain commit as applicable. Diagnostics MUST be actionable,
  sanitized and explicit about safe retry or reconciliation; failure MUST NOT
  become an empty successful result or silent provider fallback.
- **FR-011**: Valid cache-entry publication MUST require accepted evidence of
  a fully committed, integrity-checked artifact with matching digest and length.
  Entry changes and their metadata references MUST be atomic. Evidence comes
  from the shared publication authority; persistence MUST NOT claim to verify
  artifact bytes or create cross-store atomicity by itself.
- **FR-012**: Reference changes MUST preserve all committed live metadata
  references under concurrent publication, replacement and removal. Conditional
  unreferenced determinations MUST detect intervening metadata changes; they
  MUST NOT independently authorize physical artifact deletion.
- **FR-013**: The agreement MUST represent the safe recovery distinction between
  committed metadata, abandoned metadata work and committed artifacts without
  metadata. A store outage or corrupt record MUST NOT be mistaken for a miss;
  cross-store reconciliation remains owned by shared cache coordination.
- **FR-014**: Lease acquisition, renewal, guarded mutation and release MUST
  enforce current ownership and expiry atomically, reject stale owners and
  define the expiry boundary consistently. These operations MUST NOT claim
  distributed locking or multi-instance safety without separate qualification.
- **FR-015**: Reads MUST support bounded pages with deterministic ordering,
  documented continuation behavior and explicit concurrent-change semantics.
  Continuations MUST remain bound to their original query and identity scope;
  an unchanged dataset MUST have neither omissions nor duplicates.
- **FR-016**: Policies and aggregates MUST preserve their declared scopes;
  aggregate updates MUST have defined concurrent/retry behavior without
  duplicate contributions. Delayed telemetry aggregation MUST NOT weaken the
  transactional guarantees of cache visibility or reference integrity.
- **FR-017**: Before normal metadata use, the provider MUST identify empty,
  compatible, upgrade-required and incompatible schema states. Required
  initialization or upgrade failure MUST prevent readiness/use, and a newer
  unsupported schema MUST remain unchanged.
- **FR-018**: Schema creation and upgrades MUST follow explicit operational
  policy, prevent competing upgraders and preserve required committed data.
  Destructive or incompatible upgrades MUST require explicit authorization;
  interrupted steps MUST have a tested resume-or-restore procedure and MUST
  NOT admit normal consumers to partially upgraded state.
- **FR-019**: Secret values MUST NOT be stored in ordinary metadata. Registry
  credentials MUST remain references to the existing secret authority;
  diagnostics and qualification artifacts MUST exclude secrets, raw connection
  settings and unauthorized record contents.
- **FR-020**: Durable qualification MUST cover abrupt process termination before
  commit, after commit but before acknowledgment, and after acknowledgment,
  plus interrupted upgrades.
  Acknowledged committed changes MUST survive restart under the provider's
  documented durability configuration; partial groups MUST never become visible.
- **FR-021**: Each durable provider MUST document and demonstrate a consistent
  backup/restore procedure, supported upgrade paths and rollback by safe inverse
  or verified backup restoration. Required application versions and artifact
  reconciliation MUST be explicit; unrecoverable failures MUST not reset data.
- **FR-022**: Public metadata operations and results MUST remain provider-neutral.
  Schemas, migrations, persistence frameworks and engine-specific types MUST
  remain provider-private. Shared cache and feature consumers MUST not acquire
  concrete-provider dependencies or duplicate identity/publication invariants.
- **FR-023**: Every provider claiming conformance MUST satisfy the same mandatory
  logical, atomicity, concurrency, failure and applicable durable-recovery cases.
  Optional capabilities may extend operations, never relax these guarantees;
  unsupported guarantees MUST block a conformance claim.
- **FR-024**: Qualification MUST include a durable default-local implementation
  and a separately implemented alternative proving unchanged consumer behavior.
  Results MUST identify provider/version, configuration, cases and limitations;
  fixture semantics, durable qualification and production support MUST be
  reported separately. Compile-only or fixture evidence MUST NOT qualify
  untested persistence engines.

### Key Entities *(include if feature involves data)*

- **Registry State**: Stable registry identity, ecosystem/upstream association,
  enablement, policy associations and secret references; no raw credentials.
- **Canonical Package Identity**: Caller-defined normalized package identity
  within its ecosystem and registry context, plus retained descriptive metadata.
- **Cache Entry**: Complete request and authorization identity, response metadata,
  freshness information, committed-artifact association and change revision.
- **Artifact Reference**: Digest, length and accepted commit evidence associated
  with live metadata; not artifact bytes or proof that physical deletion is safe.
- **Metadata Operation**: A bounded atomic group, its logical identity, expected
  revisions and reconcilable outcome, including uncertain acknowledgment.
- **Work Lease**: Resource identity, current owner, validity interval and
  ownership generation guarding later changes from stale owners.
- **Policy Record**: Scoped cache behavior inputs retained without reimplementing
  policy decisions inside persistence.
- **Access Aggregate**: Scoped measurement interval and counters with defined
  contribution/retry semantics, distinct from cache-correctness state.
- **Schema State and Recovery Point**: Provider-private schema compatibility
  status and a coherently captured metadata backup with restoration conditions.
- **Qualification Result**: Implementation/version and configuration, attributable
  common-case outcomes, durability evidence and explicit support limitations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every defined entity round-trip and identity-partition case retains
  the expected committed values and relationships across restart, with zero
  duplicate logical identities or cross-registry/authorization observations.
- **SC-002**: In each controlled competing-write case, exactly one first creation
  or conflicting change against the same revision succeeds; all losing writers
  receive the documented conflict and there are zero silent lost updates.
- **SC-003**: Every injected transaction failure, cancellation and abrupt-stop
  boundary produces either the complete committed group or none of it, never
  a partial group; retry/reconciliation produces zero duplicate effects.
- **SC-004**: All reference/lease cases reject uncommitted artifact publication,
  stale reference decisions and expired ownership, with zero lost committed
  live references or metadata-only claims of safe physical deletion.
- **SC-005**: Every supported upgrade and documented interruption boundary has
  a successful resume-or-restore demonstration; unsupported schemas remain
  unchanged, no mixed schema admits use, and restored metadata matches the
  captured logical recovery point.
- **SC-006**: One unchanged consumer completes the mandatory logical case set
  against two independent implementations by changing provider composition
  alone, with zero changes to cache or management-operation source. Durable
  qualification is claimed only where its additional cases also pass.
- **SC-007**: Every defined failure class yields a safe classified outcome within
  its declared finite budget; the secret-leakage case set has zero exposures,
  and all paged unchanged-dataset traversals have zero omissions or duplicates.
- **SC-008**: Each advertised qualification has a result for 100% of its required
  cases, attributable version/configuration and a reproducible operator recovery
  walkthrough with no undocumented steps; fixture-only results and untested
  alternatives are never labelled production-qualified.

## Assumptions

- F-01 is the formal dependency and supplies the package/provider boundary.
  Existing F-02 lifecycle, F-03 configuration/secret handling and F-04 discovery
  remain authorities for their respective concerns; this feature does not
  replace their APIs or introduce new management endpoints.
- This is the metadata agreement and bounded qualification feature, not the
  production persistence rollout. The master F-05 acceptance focus requires
  real SQLite-backed durability, isolation, migration and crash-recovery proof
  during later implementation. A bounded qualification adapter satisfies that
  proof obligation without claiming the production SQLite provider delivered
  by original SPEC-03 or a runnable cache.
- A separately implemented alternative fixture proves contract independence.
  An in-memory fixture may prove common logical behavior only, never durable
  recovery. Production PostgreSQL and other database providers, cross-engine
  data transfer and generic certification infrastructure remain separately
  scoped work; F-07 generalizes conformance/composition tooling.
- EF Core, database schemas and migrations remain private to relational
  providers under the existing architecture and constitution. This inherited
  boundary does not prescribe new public signatures, a query language, a
  transaction implementation or a physical data model.
- The initial deployment has one authoritative metadata provider in one
  process/node. Provider replacement requires validated composition and restart,
  not hot swapping. Distributed leases, multi-node writes, HA and arbitrary
  NoSQL interchangeability are not promised by a shared contract.
- Protocol canonicalization, authorization, cache policies, single-flight,
  artifact integrity/commit, active-reader protection and physical garbage
  collection remain shared-core or appropriate provider responsibilities.
  Controlled artifact evidence can prove metadata behavior before F-06;
  no distributed metadata/blob transaction is assumed.
- Durability is qualified for documented local storage/configuration and process
  failure, not an unconditional guarantee against device loss. Backup recovery
  must state its capture point and any associated artifact-store requirements.
- Exact value limits, operation shapes, finite budgets, supported reconciliation
  lifetime, schema-version paths and qualification mechanics are planning
  decisions constrained by these outcomes. No throughput target or
  production-scale latency promise is introduced at this contract stage.
- This specification stage creates no product code, packages, production
  database, rendered console, CI/CD, release tag, infrastructure or deployment.
  All scenarios and success criteria are future acceptance obligations, not
  measured results or reviewer-owned implementation approval.
