# Feature Specification: Artifact Blob Storage Provider Contract

**Feature Branch**: `feature/006-artifact-storage`

**Created**: 2026-10-22

**Status**: Draft specification; no artifact-store implementation, production
provider, qualification result or runnable cache is delivered by this stage.

**Input**: User description: "Specify interchangeable Hoard artifact stores that stream large content, verify integrity and never expose incomplete blobs. Cover commit semantics, crash recovery, content addressing, deletion, provider capabilities and differences between filesystem and object storage."

**Backlog**: [F-06](../../docs/HOARD_SPECKIT_MASTER_BACKLOG.md#foundation-f-06)

**Feature Directory**: `specs/006-artifact-storage`

## Clarifications

### Session 2026-10-22

No critical ambiguities detected worth formal clarification. Zero questions
were asked or answered; no requirements, acceptance criteria or scope decisions
changed.

All ten review categories are clear for this bounded feature: functional scope
and behavior, domain and data model, interaction and UX flow, applicable
non-functional quality attributes, integration and external dependencies,
edge cases and failure handling, constraints and tradeoffs, terminology and
consistency, completion signals, and miscellaneous/placeholders.

Complete-stream verification, immutable content identity, direct committed-read
visibility and explicit uncertain-mutation outcomes define publication safety.
Shared coordination supplies metadata-publication and reader/reference/deletion
authority; providers do not independently infer reference safety or cross-store
rollback. Ownership expiry, later content incarnations and incomplete listings
have explicit protection requirements. Detected corruption invalidates healthy
claims without promising continuous detection or automatic repair.

Real local-filesystem durability and bounded multi-GB streaming qualification
remain required, separately from production SPEC-04 delivery. The independent
object-store-semantics fixture proves logical portability without atomic rename,
not remote-service qualification or generic F-07 certification. Exact operation
signatures, finite operational budgets, reconciliation lifetimes, stored-content
verification schedules and capability representation remain planning decisions
under the existing requirements. No latency/throughput service-level promise,
rendered UI, distributed coordination or live provider replacement is in scope.
No consequential product decision blocks planning; this review does not approve
custom checklists or establish runtime evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publish Only Complete, Verified Artifacts (Priority: P1)

As a cache-operation author, I can stream an artifact into the selected store
and obtain evidence that its complete bytes were verified and committed, so
readers never mistake a partial download for reusable cached content.

**Why this priority**: Trustworthy publication is the minimum agreement every
store must satisfy before a cache entry can reference its content.

**Independent Test**: Submit known content with matching and mismatching
expectations, observe reads while the write is incomplete, and race equivalent
and conflicting publications. Use controlled publication coordination rather
than a product cache. Covers FR-001 through FR-006 and FR-010.

**Acceptance Scenarios**:

1. **Given** a new artifact whose stream has not ended, **When** another
   consumer tries to open its committed identity, **Then** no staged prefix
   is available as a committed artifact; after successful verification and
   commit, the complete bytes and matching digest and length are available.
2. **Given** a supplied expected digest, length or supported additional
   checksum, **When** the completed content disagrees with any expectation,
   **Then** publication fails explicitly and produces no committed-artifact
   evidence or replacement of existing valid content.
3. **Given** valid content with no externally supplied digest or length,
   **When** the stream ends within the admitted limits, **Then** its identity
   and length are established from the complete content before publication;
   unknown length does not mean unlimited input.
4. **Given** two writers publishing identical content, **When** they complete
   concurrently, **Then** both outcomes identify the same immutable content
   without conflicting visible versions; reuse of an existing artifact does
   not bypass verification of either submitted stream.
5. **Given** an existing committed identity, **When** a writer supplies
   different bytes under that identity or the stored content fails verification,
   **Then** the conflict or corruption is explicit and no unchecked overwrite,
   successful reuse or valid cache-hit claim occurs.

---

### User Story 2 - Transfer Large Artifacts Within a Fixed Resource Budget (Priority: P1)

As an operator, I can store and retrieve multi-gigabyte artifacts without
memory usage growing with the artifact size, and cancel stalled work without
leaving a valid partial artifact.

**Why this priority**: A store that only handles small buffered payloads cannot
serve ordinary large dependencies reliably on a personal machine.

**Independent Test**: Stream generated content through non-seekable sources and
destinations, including slow consumers. Apply cancellation and capacity failures
at controlled boundaries, check caller/transfer resource ownership, and measure
incremental transfer memory for different artifact sizes under the same
concurrency limit. Covers FR-007 through FR-009, FR-011 and FR-012.

**Acceptance Scenarios**:

1. **Given** admitted 256 MiB and 4 GiB artifacts and one active transfer,
   **When** each is written and read without preloading its payload into memory,
   **Then** both reproduce the expected bytes within the same fixed transfer
   memory budget, including when the producer or consumer is deliberately slow.
2. **Given** a stream whose declared size is absent, false or above the
   configured limit, **When** admission or streaming detects a limit violation,
   **Then** work stops with a classified limit failure, never truncation
   reported as success or unbounded staging growth.
3. **Given** a stalled producer, slow reader or pending store operation,
   **When** cancellation or the declared finite work budget takes effect,
   **Then** resources are released within the documented bound and the outcome
   distinguishes definite non-commit from possible completed commit.
4. **Given** exhausted capacity, denied access, unavailable storage or a
   missing committed artifact, **When** the operation completes, **Then**
   these outcomes remain distinguishable and sanitized; an outage is not
   treated as a miss and the provider is not silently replaced.
5. **Given** a valid empty artifact, **When** it is committed and read,
   **Then** zero length is preserved as valid content, distinct from not found,
   cancellation or a failed read.

---

### User Story 3 - Recover Interrupted Work Without Losing Committed Content (Priority: P1)

As an operator, I can restart after an interrupted transfer or lost
acknowledgment, identify the actual publication outcome, and reclaim abandoned
work without deleting valid artifacts or inventing cache entries.

**Why this priority**: Clean shutdown alone does not establish durability or
safe recovery from process failure.

**Independent Test**: Abruptly stop a durable qualification store at each
documented staging, verification, publication and acknowledgment boundary,
restart it, and reconcile operations and expired staging ownership. Covers
FR-013 through FR-017 and the durable portions of FR-006.

**Acceptance Scenarios**:

1. **Given** an interruption before verified publication, **When** the store
   restarts, **Then** the incomplete attempt is not readable as committed
   content and previously acknowledged artifacts remain intact.
2. **Given** verified publication followed by lost acknowledgment, **When**
   the caller reconciles or retries the same logical operation within its
   supported reconciliation lifetime, **Then** the outcome can be established
   without duplicate logical publication or replacement of valid content;
   uncertainty is never reported as definite rollback.
3. **Given** an acknowledged commit followed by abrupt process termination,
   **When** the durable provider reopens under its documented configuration,
   **Then** the complete artifact remains readable with the acknowledged
   identity and length, and no partial artifact is admitted.
4. **Given** abandoned staging and a still-active or renewed write owner,
   **When** bounded recovery runs, **Then** only eligible abandoned work is
   reclaimed; stale owners cannot commit, renew or remove the new owner's work.
5. **Given** a committed blob whose later metadata publication failed,
   **When** recovery examines it, **Then** it remains distinct from a valid
   cache entry and can be reported for shared reconciliation; the store does
   not invent metadata or assume cross-store rollback.

---

### User Story 4 - Delete Artifacts Without Racing Readers or New References (Priority: P1)

As a cache-maintenance author, I can request physical deletion only through
current shared-coordination authority, so reclaiming space does not destroy
content still used by a reader or newly published cache entry.

**Why this priority**: Digest deduplication makes a single physical artifact
relevant to multiple entries; an old unreferenced observation is not deletion
permission.

**Independent Test**: Coordinate a reader, publication and conditional deletion
with barriers and controlled reference authority. Exercise stale decisions,
ownership expiry and repeated deletion without implementing retention policy.
Covers FR-018 through FR-021 and the deletion aspects of FR-012 and FR-017.

**Acceptance Scenarios**:

1. **Given** an artifact with a live metadata reference or an active protected
   reader, **When** deletion is requested, **Then** reference authority denies
   removal or the documented reader-safe protocol defers removal; an already
   admitted reader completes without truncation caused by deletion.
2. **Given** a formerly unreferenced artifact and a competing new reference or
   publication, **When** an old deletion decision is applied, **Then** it
   cannot delete the newly protected content; reference admission and physical
   removal have a shared exclusion/revalidation rule rather than a
   check-then-delete race.
3. **Given** an authorized deletion of an unreferenced, unprotected artifact,
   **When** deletion succeeds and is repeated, **Then** the artifact cannot be
   newly opened, the repeated request has an explicit already-absent outcome,
   and neither outcome claims removal of unrelated content.
4. **Given** failed deletion, expired authority or a locator not belonging to
   the selected store, **When** removal is attempted, **Then** a safe failure
   or conflict is returned; there is no unauthorized path access, stale-owner
   removal or false claim that storage has been reclaimed.

---

### User Story 5 - Qualify Different Storage Mechanisms Honestly (Priority: P2)

As a provider author or distribution maintainer, I can qualify a store against
one correctness agreement and declare its actual capabilities, so a different
storage mechanism does not require rewriting cache operations or weakening
publication safety.

**Why this priority**: A filesystem-only assumption disguised as a shared
contract would prevent genuine provider interchangeability.

**Independent Test**: Run the common logical cases against a durable local
qualification provider and an independently implemented object-store-semantics
fixture with no atomic rename. Use the same consumer, exercise delayed
visibility and conditional conflicts, and separate simulated behavior from
durable or production qualification. Covers FR-022 through FR-025.

**Acceptance Scenarios**:

1. **Given** two independent implementations using different publication
   mechanisms, **When** explicit composition changes the selected provider,
   **Then** the unchanged consumer receives the same mandatory integrity,
   visibility, concurrency, read and deletion outcomes without provider-private
   types or filesystem assumptions.
2. **Given** a provider with delayed final-content visibility or delayed
   enumeration, **When** publication and recovery are exercised, **Then**
   successful commit still guarantees the required direct committed read,
   and an incomplete listing is not evidence that a referenced blob is absent.
3. **Given** missing mandatory guarantees or an unsupported optional operation,
   **When** compatibility is evaluated or the operation requested, **Then**
   admission fails or an explicit unsupported outcome is returned; no
   capability declaration silently relaxes safety or implies untested support.
4. **Given** results from a local durable store and a simulated alternative,
   **When** maintainers describe support, **Then** every required case and
   limitation is attributable to an implementation and configuration; simulation
   is not advertised as qualification of a real remote service.

### Edge Cases

- A zero-byte artifact, unknown-length stream, short read and early end-of-stream.
- A declared length smaller or larger than the actual content; the size limit
  is crossed on the final chunk.
- A digest mismatch, unsupported checksum expectation, or attempted reuse of
  an existing identity without consuming and verifying the submitted content.
- Two equivalent writes, conflicting identity claims, or corrupt content
  already present at an otherwise valid committed identity.
- Cancellation during staging, verification, publication or acknowledgment,
  including cancellation racing a completed commit.
- An abrupt stop before publication, after publication but before acknowledgment,
  or immediately after acknowledgment.
- Storage full, permission denial, interrupted connection or a stalled producer
  or reader; none is misclassified as a successful empty artifact or cache miss.
- An expired staging owner attempts to commit after recovery or reassignment;
  a renewal races cleanup at the exact expiry boundary.
- Recovery restarts midway through cleanup, or a staging inventory spans
  multiple pages and changes concurrently.
- A committed blob has no metadata reference because metadata publication failed.
- A deletion decision becomes stale when a new reference or publication starts;
  deletion races an active reader or a later incarnation of the same digest.
- Repeated deletion, unknown deletion acknowledgment, or delayed physical space
  reclamation after logical removal.
- A malformed digest or foreign locator attempts path traversal or access
  outside the provider's configured namespace.
- Delayed object listing, incomplete multipart work or unavailable direct reads
  after a purported commit; absence from a listing does not establish absence.
- Persisted corruption is detected after an earlier successful commit; the
  artifact must not continue to be reported as healthy or successfully reusable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agreement MUST identify immutable artifact bytes by their
  complete-content cryptographic digest and retain their exact length. Package
  coordinates, request paths and provider-private locators MUST NOT substitute
  for content identity or grant authorization to read that content.
- **FR-002**: Writes MUST distinguish private in-progress content from committed
  artifacts. Staging MUST NOT be readable through committed-artifact operations
  or exposed as a valid cache hit, including during failure and recovery.
- **FR-003**: Publication MUST require complete-stream integrity verification,
  comparison with every supplied supported digest/checksum/length expectation,
  and enforcement of admitted size limits. Without external expectations,
  digest and length MUST still be established from the complete stream.
  Unsupported expectations MUST fail explicitly, not be ignored.
- **FR-004**: Successful commit MUST return attributable evidence identifying
  the committed digest, length, selected store and publication outcome, suitable
  for shared coordination to authorize later metadata publication. The store
  MUST NOT publish cache metadata or claim a cross-store transaction.
- **FR-005**: Conditional publication MUST preserve immutable identity under
  concurrent writes. Equivalent verified content MAY reuse an existing valid
  artifact; conflicting or corrupt content MUST NOT be overwritten or reused
  as success. Deduplication MUST NOT bypass submitted-content verification.
- **FR-006**: After acknowledged commit, a direct read by committed identity
  MUST provide the complete verified content under the provider's documented
  durability conditions, until authorized deletion or an explicitly reported
  storage failure. Delayed internal visibility MUST be resolved before commit
  success, or reported as an uncertain/failed outcome within the finite budget.
- **FR-007**: Reads and writes MUST support asynchronous, cancellation-aware
  streaming and backpressure without whole-artifact memory buffering. Transfer
  memory MUST remain bounded independently of content size at fixed admitted
  concurrency.
- **FR-008**: The agreement MUST define validated size, transfer-memory,
  concurrency, staging-capacity, time and cleanup-work limits. Unknown length
  MUST remain subject to the byte limit; excess input MUST fail, not truncate
  successfully. Exhausted limits MUST NOT trigger hidden unbounded retries.
- **FR-009**: Read ownership and disposal, input-stream ownership and
  cancellation behavior MUST be explicit. Completion, failure and cancellation
  MUST release owned transfer resources within documented finite bounds without
  disposing resources retained by the caller.
- **FR-010**: Committed reads MUST distinguish absent content from unavailable,
  truncated or detected-corrupt content. Detected corruption MUST invalidate
  healthy/reusable claims and prevent successful completion as verified content.
  The documented verification policy MUST state when stored bytes are checked;
  commit verification MUST NOT imply continuous detection of later damage.
- **FR-011**: Valid empty content MUST round-trip with its own identity and
  zero length, distinct from a missing artifact or failed transfer. Stream
  behavior MUST NOT require the source or destination to support seeking.
- **FR-012**: Outcomes MUST distinguish invalid input, absent, already present
  and verified, conflict, unsupported capability, cancellation before commit,
  capacity/access/unavailability failures, corruption and uncertain mutation
  as applicable. Diagnostics and proof artifacts MUST be actionable and exclude
  secrets, credential-bearing locations and provider-private sensitive details.
  Errors MUST NOT become success-shaped results or silent provider fallback.
- **FR-013**: Mutation acknowledgment MUST distinguish definite non-commit,
  success and uncertainty. Retry or reconciliation of the same logical write
  or deletion MUST establish its outcome without unsafe duplicate effects.
  Supported reconciliation lifetime, expiry and safe behavior after expiry
  MUST be explicit; cancellation alone is not evidence of rollback.
- **FR-014**: Durable qualification MUST exercise abrupt process termination
  before publication, after publication before acknowledgment, and after
  acknowledgment. Restart MUST preserve acknowledged complete artifacts and
  exclude incomplete work under the declared durability configuration.
- **FR-015**: Recovery MUST classify active staging, abandoned staging, committed
  artifacts and uncertain operations without inferring cache-entry validity.
  Cleanup MUST be bounded, resumable and safe to repeat; incomplete enumeration
  MUST NOT justify deleting unobserved or potentially live content.
- **FR-016**: Committed artifacts without metadata references MUST remain
  identifiable for shared reconciliation. The store MUST NOT manufacture a
  metadata reference or remove such artifacts solely because a write or later
  metadata acknowledgment was lost.
- **FR-017**: Staging and maintenance ownership MUST define acquisition,
  renewal, expiry and release with a consistent expiry boundary. Expired or
  replaced owners MUST be unable to commit or clean up a newer owner's work.
  These protections MUST NOT imply distributed lease or multi-node support.
- **FR-018**: Physical deletion MUST require current shared-coordination
  authority covering live metadata references, publication in progress and
  active readers. A metadata-only unreferenced observation MUST NOT suffice.
  The storage agreement MUST support enforcing that authority without
  inspecting provider-private metadata schemas.
- **FR-019**: Reference/publication admission and deletion MUST share an
  exclusion or conditional revalidation rule that rejects stale authority and
  protects a later incarnation of the same digest. An admitted protected reader
  MUST either finish on stable complete content or prevent physical removal;
  deletion MUST NOT truncate its read.
- **FR-020**: Deletion MUST distinguish removed, already absent, denied/conflict,
  failed and uncertain outcomes. Successful logical removal MUST prevent new
  opens until a newly authorized publication; any delayed physical reclamation
  and its observable status MUST be explicit rather than claimed as freed space.
- **FR-021**: All identities and locators MUST be validated and confined to the
  selected provider's configured namespace. User/package input MUST NOT select
  arbitrary filesystem paths or remote objects; malformed or foreign locators
  MUST fail without accessing unrelated content.
- **FR-022**: Common operations, evidence and outcomes MUST remain
  provider-neutral. Private paths, remote-service types and publication
  mechanisms MUST NOT leak into consumers. Core and endpoint operations MUST
  not depend on a concrete store or duplicate shared publication/deletion rules.
- **FR-023**: Providers MUST declare their durability conditions, committed-read
  visibility, conditional publication/deletion, staging recovery, reader
  protection, enumeration consistency and optional operations. Atomic rename
  MUST NOT be assumed. Optional range reads or other extensions MUST NOT be
  advertised unless independently qualified; the baseline requires full reads,
  not protocol-level Range or HEAD support.
- **FR-024**: Every conforming provider MUST satisfy the same mandatory
  integrity, publication, streaming, ownership, deletion and failure outcomes.
  Capabilities MUST NOT weaken these guarantees; an implementation unable to
  meet them MUST fail admission rather than rely on silent unsafe fallback.
- **FR-025**: Qualification MUST include a real durable default-local store and
  an independently implemented object-store-semantics fixture lacking atomic
  rename, using an unchanged consumer. Reports MUST identify implementation,
  version, configuration, required case results and exclusions, separating
  simulation, durable qualification and production-service support.

### Key Entities *(include if feature involves data)*

- **Artifact Identity**: Complete-content digest and exact length describing
  immutable bytes, independent of package/request identity and access rights.
- **Integrity Expectations**: Optional externally supplied digest, checksum and
  length assertions plus admitted byte limits; never substitutes for verification.
- **Staged Write**: Private incomplete work, current owner, expiry and logical
  operation identity; it is not a committed artifact or cache entry.
- **Committed Artifact Evidence**: Attributable store, digest, length and
  publication outcome consumed by shared metadata-publication coordination.
- **Protected Read**: An admitted read of committed content with explicit
  ownership, lifetime and protection against concurrent deletion.
- **Mutation Outcome**: Logical write/deletion identity, definite or uncertain
  result, and bounded reconciliation conditions.
- **Deletion Authority**: Current shared-coordination permission bound to the
  intended content incarnation and reference/publication/reader protections.
- **Recovery Observation**: Bounded evidence about staged, committed, abandoned
  or uncertain work, with enumeration consistency and continuation conditions.
- **Store Capability and Qualification Record**: Declared guarantees and
  optional behavior, tested implementation/configuration, attributable results
  and limits on support claims.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every successful publication and read case reproduces the expected
  complete digest and length; all incomplete, mismatched and conflicting-content
  cases produce zero valid partial artifacts or false successful reuse.
- **SC-002**: A single-transfer qualification writes and reads both 256 MiB and
  4 GiB artifacts with no more than 64 MiB incremental peak transfer memory above
  the idle baseline in each run, including the slow-producer/consumer case.
  The measurement includes provider-owned buffers and excludes payload fixtures
  preloaded in memory, which are prohibited in this test.
- **SC-003**: Every controlled equivalent-publication race resolves to one
  immutable content identity with complete bytes; every conflicting or
  detected-corrupt publication is rejected without overwriting valid content.
- **SC-004**: At every documented abrupt-stop boundary, restart exposes no
  partial artifact and retains all acknowledged artifacts; retry/reconciliation
  produces zero unsafe duplicate effects or false rollback claims.
- **SC-005**: Every stale-owner, reader/deletion and reference/publication race
  rejects unsafe removal or stale mutation, with zero truncated protected reads,
  deletion of newly protected content or removal outside the selected namespace.
- **SC-006**: All cancellation, limit and storage-failure cases return a
  classified outcome and release owned resources within their declared finite
  bounds, with zero silent fallbacks, secret exposures or outages reported as misses.
- **SC-007**: One unchanged consumer completes 100% of the mandatory logical
  cases against two independent implementations using different publication
  mechanisms; no consumer rewrite or assumption of universal atomic rename is
  required, and durable proof is claimed only for cases actually executed.
- **SC-008**: Every advertised qualification includes attributable results for
  all required cases, declared capability/limitation records and a reproducible
  interrupted-write recovery walkthrough with no undocumented operator steps;
  simulated alternatives never become claims of production-service support.

## Assumptions

- F-01 is the formal dependency and supplies existing provider/package
  boundaries. F-02 lifecycle, F-03 configuration/secrets, F-04 discovery and
  F-05 metadata/reference operations remain their respective authorities.
  This feature adds no new management endpoint or competing activation model.
- This is the storage agreement and bounded qualification feature, not a
  production provider rollout. The master F-06 filesystem acceptance focus
  requires real local-filesystem durability, crash recovery and multi-GB
  streaming proof during implementation. A bounded qualification adapter
  satisfies that obligation without delivering original SPEC-04's production
  filesystem provider or a working cache.
- The alternative fixture must independently model conditional publication,
  multipart/incomplete work and delayed visibility/listing without atomic
  rename. It needs no cloud account and proves logical portability only.
  Production object storage remains SPEC-27; F-07 owns generalized conformance
  and composition infrastructure. No remote vendor is qualified by simulation.
- SHA-256 content addressing is inherited from the product baseline. Additional
  ecosystem expectations are validated only when explicitly supported; they
  do not replace the common content identity. Sharing physical bytes by digest
  does not share request metadata, authorization or read permissions.
- The initial model is one authoritative store in one process/node. Changing
  providers requires validated composition and restart, not live swapping.
  Distributed writers/leases, cross-store migration and HA are separately
  scoped; remote storage does not by itself make multiple hosts safe.
- Shared cache coordination owns integrity/publication policy, metadata
  sequencing, reference admission, reader/deletion exclusion and recovery
  decisions. Providers supply the mechanisms and truthful outcomes needed
  to enforce them, not parallel cache engines. Controlled coordination fixtures
  can prove this contract without implementing retention or garbage collection.
- Acknowledged durability is qualified for the documented storage configuration
  and process-failure model, not unconditional survival of device loss or every
  power failure. Later integrity verification can detect damage after commit;
  this stage promises neither continuous media auditing nor automatic repair.
- The 4 GiB/64 MiB test is a bounded contract acceptance target, not a default
  production artifact limit, throughput promise or total host memory ceiling.
  Exact operation signatures, finite time/concurrency/staging limits,
  reconciliation lifetimes, verification schedule and capability representation
  are planning decisions constrained by the outcomes above.
- Range/HEAD protocol behavior, archive extraction, public uploads, production
  cache algorithms, retention policy, backup/disaster-recovery tooling, UI,
  runtime distribution, product CI/CD, package publication, infrastructure and
  deployment remain outside this feature. This stage creates only requirements
  and their built-in quality review, not passing product evidence or approval
  of reviewer-owned custom checklists.
