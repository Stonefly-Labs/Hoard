# F-05 Logical Metadata Model

**Status**: Implemented public values and fixture-tested observable semantics,
not a portable physical schema. See [API](contracts/metadata-api.md) and
[implementation evidence](plan.md#implementation-evidence).

## Common Values and Validation

All collections are immutable, initialized and bounded before enumeration or
copying. No public record contains `object`, arbitrary JSON, a delegate,
database handle, provider-private type or raw secret. Values round-trip exactly;
invalid input is rejected, never normalized, rounded, truncated or repaired.

| Value | Definition / common bound |
| --- | --- |
| `MetadataId` | Nonempty GUID; canonical 16-byte network-order representation |
| `CanonicalText` | 1..1,024 UTF-8 bytes, valid Unicode, no NUL/control characters or unpaired surrogates; exact byte equality, no case/Unicode/URL normalization |
| `PublicLabel` | 0..512 UTF-8 bytes, plain text without controls |
| `MetadataRevision` | Opaque nonempty 128-bit value; newly assigned on each successful replacement, never reused on deletion/recreation; not a timestamp or sortable sequence |
| `ExpectedRevision` | Closed choice `Absent` or `Match(revision)`; no unconditional overwrite/delete |
| `MetadataInstant` | UTC Unix milliseconds, inclusive 0..253402300799999; non-millisecond or non-UTC inputs are invalid |
| `ArtifactDigest` | SHA-256, exactly 32 bytes; lowercase hex only for textual display |
| Byte length / counters | Signed 64-bit, nonnegative; checked overflow rejects the complete mutation |
| Secret reference | Structured owner ID, resolver ID and opaque key, each at most 128 UTF-8 bytes; existing secret authority owns interpretation/resolution |
| Header collection | At most 32 approved header values, at most 8 KiB encoded total |
| Aggregate interval | Nonempty half-open `[start,end)`, at most 24 hours |

Canonical text is opaque input from the appropriate identity authority.
Persistence cannot decide whether two differently cased names are equivalent.
Identical canonical tuples are unique; distinct tuples remain distinct.
An empty optional dimension uses an explicit `None` union case, not an empty
string or a provider-dependent null comparison.

`MetadataRequestIdentity` contains registry ID, ecosystem, canonical request
target, canonical method (uppercase token, at most 16 ASCII bytes), and a
required authorization partition. Anonymous access has an explicit caller-
supplied partition, never a default inferred by persistence. Request targets
cannot contain credentials; canonical keys are not authorization grants.

Upstream addresses are absolute HTTPS/HTTP URIs without user info, query or
fragment, at most 2,048 UTF-8 bytes. Registry credentials use only the structured
secret reference. Free-form registry options/connection strings are absent.
Persisted response metadata is a closed allowlist: content type, cache-control,
ETag, last-modified, expires, vary and content-language. Reject Set-Cookie,
authorization/proxy-authorization, credentials in URLs and unlisted headers.
ETag is at most 512 bytes and header values contain no CR/LF. Protocols/core
select safe response metadata; persistence enforces this structural boundary,
not SSRF, authentication or arbitrary secret-content detection.

## Entity Definitions

| Record / key | Fields and relationships | Conditional change rules |
| --- | --- | --- |
| Registry / registry ID | Ecosystem, upstream address, enabled flag, optional policy ID and secret reference, public label, revision | Create absent; update matching revision; disabling retains children; deletion rejects remaining packages/entries/policies/aggregates scoped to it |
| Package / `(registry ID, ecosystem, canonical package name)` | Display label, revision; registry must exist and ecosystem match | Uniqueness uses exact key; deletion rejects live entries |
| Policy / policy ID | Scope `Global` or `Registry(id)`, metadata TTL, retention, maximum artifact bytes, immutable flag, stale-if-error duration, revision | Durations 0..31,536,000,000 ms; nonnegative byte limit; no policy evaluation in persistence; registry-bound links cannot cross scopes |
| Cache entry / request identity | Package key, status 200..299, approved headers, digest/length, created/validated/fresh-until instants, revision | Registry/package must exist and match identity; `created <= validated <= freshUntil`; new or replaced artifact needs accepted authority guard |
| Artifact state / digest | Length, reference revision and live reference edges to cache-entry identities | Digest length immutable; edges equal currently committed entries; update reference revision whenever an edge changes; retain zero-reference generation to prevent ABA |
| Work lease / canonical resource key | Owner ID, positive generation, acquired/expires instants, revision | Acquire absent/expired; renew/release exact owner/generation; retain last generation after release; overflow fails, never wraps |
| Access aggregate / `(registry ID, auth partition, interval start,end)` | Hits, misses, served bytes, fetched bytes, latency-millisecond total, sample count, revision | Nonnegative contributions atomically add; operation receipt deduplicates complete contribution; registry must exist |
| Operation ticket / `(store epoch, ticket ID)` | Issued/expires instants, state, committed fingerprint/receipt if any | Store-issued and persisted before use, 24-hour lifetime; never accept missing/foreign/expired tickets for execution |
| Schema state / provider-owned store | Provider ID, private schema version, admitted operation contract version, compatibility state, recovery guidance code | No normal operations until explicit admission; versions bounded to 64 ASCII bytes |
| Recovery point / opaque ID | Store epoch, provider/schema/application versions, capture ID, verified logical digest, fixture-private backup locator | Not a public database path, secret or cross-engine transfer format; `ToString` redacts handles |

Valid cache entries in this feature are positive artifact-backed records.
Negative caching and other HTTP status semantics are later shared-cache work,
not implemented by storing arbitrary statuses now.

A policy cannot be removed while a registry points at it. Registry-scoped
policies and aggregates are children for deletion checks even if the registry
has been disabled. Bounded explicit removal can delete children then parents
in one atomic group; there is no unbounded implicit cascade. A group containing
more than the permitted number of dependents must first remove bounded child
groups, and cannot delete the parent until the final invariant check succeeds.

## Atomic Groups, Reads and Results

`MetadataMutationBatch` holds one ticket, 1..64 closed typed mutations,
optional whole-batch lease guard and publication-evidence handles for affected
artifacts. Each logical record is targeted at most once in a batch, including
aggregate and lease records; duplicate targets are invalid. Revisions,
relationships and final graph invariants are checked in the same transaction.
Relationship checks use the final candidate graph, so insertion/removal order
within a batch cannot create transient constraint failure. A failure returns
no partial record result.

`MetadataReadGroup` has 1..64 typed selectors; it returns one immutable committed
logical snapshot and a result per selector, including explicit `NotFound`.
An ordinary exact read is a one-selector group; separate calls have no shared
snapshot. A corruption/unavailability error fails the group, never masquerades
as selector-level absence. Success and every failure are closed result variants,
with fixed reason codes/corrective templates, not raw exception text.

Public request/result encoding is deterministic UTF-8 for the documented
typed fields (fixed field order, GUID network byte order, integer milliseconds,
no optional-field ambiguity). It exists for size/fingerprint measurement, not
as a public arbitrary-payload storage escape hatch. Aggregate counters and
revision values are part of the encoding. Maximum encoded request/result is
1 MiB; a page too large fails rather than silently shortening a successful page.

## Operation State Transitions

1. `ReserveOperationAsync` durably creates a random ticket in `Reserved`.
   A reservation acknowledgment loss cannot have mutated user data; an
   unidentified reservation expires. Capacity failure is explicit.
2. `CommitAsync` accepts only that store's unexpired reserved ticket. Canonical
   mutation content (including expected revisions, scope, lease guard and
   artifact digest/length, excluding renewable evidence handles) is SHA-256
   fingerprinted. Identical retry content must have the same fingerprint.
3. In one atomic commit, apply the entire candidate state and move the ticket
   to `Committed(fingerprint,receipt)`. A repeated matching committed request
   returns that receipt without applying changes; a different payload conflicts.
4. A definite pre-commit rollback leaves the ticket reserved and explicitly
   permits an identical retry within its lifetime. No background retry occurs.
5. `ReconcileAsync` serializes with commits. A committed ticket returns its
   receipt. A still-reserved ticket is atomically fenced to `Abandoned` and
   returns `NotCommitted`; delayed queued commits can no longer use it.
   If exclusion/outcome cannot be established within budget, return `Uncertain`.
6. `Abandoned` cannot execute again. At `now >= expires`, any execution returns
   `ReconciliationExpired`; a missing or foreign ticket also never executes.
   A caller must not blindly reserve a new ticket for an unresolved old action.
7. Prune only expired ledger rows, at most 100 per reservation. At capacity
   100,000, reject reservation rather than evicting live receipts or endlessly
   pruning. Every receipt is available through its 24-hour lifetime.

No operation returns a definite rollback after crossing an unobserved commit
boundary. Cancellation can stop waiting while an owned native call completes;
that unresolved outcome retains its ticket and shared-publication protection.

## Reference and Ownership Transitions

Publication acquires a guard from the host-injected shared authority for each
distinct digest/length. Untrusted/missing/mismatched evidence is invalid; a
caller cannot mint acceptance by setting a boolean. Guards protect publication
until the owned transaction settles and are disposed after commit/rollback.
No evidence handle or secret locator is persisted in entries/receipts or logged.
Artifact state and entry reference edges change together.

An unreferenced observation returns `(digest, referenceRevision, count=0)`.
`ConfirmUnreferenced` succeeds only against that current revision and zero
references inside a transaction. Its receipt is metadata evidence only;
active readers, outstanding publications and physical deletion remain shared
coordination responsibilities. Artifact-generation records are not deleted in
this feature, preventing a removed/recreated digest from reusing an old revision.

Leases use `effectiveNow = max(current UTC milliseconds, persistedTimeFloor)`.
Every transactional ownership/ticket-time decision advances the floor durably
with that decision. Clock rollback cannot revive an ownership generation already
expired/replaced by a committed decision; forward jumps may expire work early.
Lease TTL is 1..300 seconds, with `effectiveNow >= expires` expired. Renew
extends from effectiveNow, never from a caller clock. Each reacquisition increments
generation; release tombstones it. Reads report recorded lease data only, never
certify current ownership. A guarded mutation rechecks owner, generation and
expiry immediately before its commit decision under the same writer exclusion.
No distributed clock/lock guarantee follows.

## Pages and Continuations

Queries are closed typed choices for registries, packages by registry, cache
entries by registry plus auth partition (optional package), policies by scope,
aggregates by registry/partition/interval, leases by exact resource-prefix
scope, and artifact states. Each query has only ascending canonical-key order.
Compare component tuples lexicographically using unsigned UTF-8 bytes (GUIDs
use network bytes; integers numeric); never database locale or UTF-16 collation.

A continuation includes contract version, store epoch, canonical complete query,
page size (1..100), order and last key. Encode/decode bounds are 16 KiB, and
every resumed call must match all fields. Reject changed filters/scope/order/
size, malformed fields, foreign epochs and incompatible versions.
The continuation is not an authorization capability or secret. Each page is a
committed snapshot; no snapshot survives across pages. On unchanged data,
strictly-greater-than-last-key traversal returns every row once. Concurrent
inserts before the cursor may be missed; later keys may appear; deletes vanish
and replacements may show their current values. Restart preserves cursors for
the same epoch/schema; restore or incompatible schema change rotates epoch
and invalidates tickets/cursors.
