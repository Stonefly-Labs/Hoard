# F-06 Artifact Operation Model

**Status**: Planned public values and private state constraints; no code delivered.
All public records are immutable, validated and BCL-only. Optional values and
results use closed choices, never success-shaped default/null payloads.

## Identity, Evidence and Expectations

| Value | Fields / validation | Meaning |
| --- | --- | --- |
| `ArtifactIdentity` | Existing `Metadata.ArtifactDigest`; nonnegative signed 64-bit length, no larger than admitted maximum | Complete SHA-256 content, not package identity or permission |
| `ArtifactStoreIdentity` | Nonempty provider module ID (existing ID grammar, max 128 UTF-8 bytes), nonempty instance/epoch GUIDs | Selected namespace; durable reopen preserves both IDs, explicit reinitialization changes epoch |
| `ArtifactStamp` | Store identity, content identity, nonempty incarnation GUID | One visible lifetime; delete/recreate never reuses it |
| `ArtifactExpectations` | Optional SHA-256, exact nonnegative length, optional bounded additional checksum; required positive admitted byte cap | All supported expectations checked at EOF; absent length is bounded, zero length is valid |
| `ArtifactCommitEvidence` | Stamp, ticket/receipt ID, bounded opaque proof handle, verified publication outcome | Attributable evidence, not a cache entry, authorization token or permanent health certificate |

Reuse `ArtifactDigest` in its existing namespace without changing its semantics.
No public path, URL, object-service version or remote SDK handle is a content
identity. Provider-owned opaque handles are at most 4 KiB; reject oversized,
malformed, foreign-epoch or foreign-store values before accessing storage.
All value/debug formatting is redacted. In-process code is trusted, not sandboxed.

The additional `ArtifactChecksumExpectation` carries an ASCII algorithm ID
(1..16 bytes) and immutable expected digest bytes (1..64 bytes). This profile
admits only `sha512` with exactly 64 bytes as the additional algorithm, alongside
the separate SHA-256 expectation. An unrecognized algorithm yields `Unsupported`
at reservation before source I/O, not an ignored assertion. Invalid known
algorithm length yields `InvalidInput`.
Claimed length above cap is rejected before source reads; actual excess fails
before excess bytes are appended to staging. EOF is required even when expected
length has been reached. A short positive read is not EOF.

## Tickets, Staging and Decisions

| Value | Fields / validation | Relationship |
| --- | --- | --- |
| `ArtifactOperationTicket` | Store epoch, provider-issued ID, operation kind, issued/expiry instants, immutable intent fingerprint | Recorded before mutation (persisted for durable profile), 24-hour reconciliation lifetime |
| `ArtifactWriteIntent` | Expectations and byte cap | Ticket fingerprint excludes stream object, includes every semantic expectation |
| `ArtifactDeleteIntent` | Exact target stamp | Binds deletion to the observed incarnation, not a bare digest |
| `ArtifactStagingOwner` | Ticket, process session, owner ID, positive nonwrapping generation, expiry | Only current unexpired generation may append/verify/commit/renew/abandon |
| `ArtifactStagedWrite` | Owner, computed identity, verified completion marker, private handle | Cannot be forged from a caller claim; never a committed-read target |
| `ArtifactMutationReceipt` | Ticket, final outcome, target stamp, logical visibility and physical-reclamation status | Retained for exact retry/reconciliation, excludes sensitive paths |
| `ArtifactResolution` | `Pending`, `Committed`, `NotCommitted`, `Removed`, `AlreadyAbsent` | Pending is not success; expired/unknown is a classified failure |

Only reserve issues a new ticket. Reconciliation never executes a new mutation.
A staged retry uses the same live ticket/intent, a fresh fenced owner generation
and complete input verification. A decided ticket cannot accept new source bytes;
use reconciliation for its outcome and a new ticket for a new submitted stream.
Same-ticket commit/delete retry returns the identical finalized logical receipt.
Changed intent or foreign epoch is never accepted as a new operation.

```text
Reserved -> Staging -> Verified -> PublicationPending -> Committed
    |          |          |               |
    +----------+----------+-> NotCommitted +-> Uncertain -> Reconcile

DeleteReserved -> AuthorityHeld -> RemovalPending -> Removed / AlreadyAbsent
       |                |               |
       +----------------+-> NotCommitted +-> Uncertain -> Reconcile
```

`Uncertain` describes what the caller knows, not a third visible content state.
The authoritative decision (persisted journal for the local profile) determines
the eventual outcome. The simulated profile reconciles within its admitted
process lifetime; a replacement instance has a new epoch and cannot claim
durable recovery or replay a previous epoch's ticket. Before the
decision boundary, cancellation fences later commit. After attempted decision,
unknown outcome retains operation and guard ownership until settlement.
No normal admission passes unresolved startup decisions.

## Protected Reads and Shared Authority

`ArtifactReadRequest` contains a digest, optional expected stamp and a closed
read mode: `Full` or `Range(offset,count)`. Range values must be nonnegative
offset/positive count without overflow, but both fixtures return `Unsupported`
for that mode before storage I/O; only `Full` is qualified. This is not an
HTTP Range/HEAD implementation. An expected
stamp prevents silently following a recreated incarnation; ordinary authorized
reads by digest open the current committed incarnation. Length/stamp reported at
open are provisional observations; full copy verifies actual content.

`IArtifactReadSession` owns one provider handle and one authority read guard.
It admits one full copy, never concurrent copies/seeking/range. The destination
is borrowed. Success records exact digest, length and stamp at EOF after all
destination writes. Partial copies, cancellation or early disposal cannot return
verified-completion evidence. Dispose releases owned handles/guards after live
I/O stops; it never disposes the caller's source/destination.

`ArtifactProtectionRequest` is a closed choice: publication takes store/digest
and an optional observed stamp (absent for first publication); read takes the
same with its optional expected stamp; metadata reference and deletion require
an exact stamp. Every request also binds an operation ID: the provider ticket
for mutation, or a fresh authority-recognized admission ID for read/metadata.
Publication/reference/read modes are shared; deletion is exclusive.
`ArtifactProtectionGrant` binds authority instance, operation ID, mode, store,
digest, applicable stamp, generation and finite admission expiry. Only the
configured authority issues/recognizes grants; a caller record is insufficient.
The host-injected `IArtifactCoordinationAuthority` validates current authority,
not a caller boolean. Its `RetainAsync` recognizes the actual live opaque handle
and pins the same protection atomically, without reentering the admission gate.
Copied fields, disposed handles and foreign authority instances do not qualify.
Retention is for the same admitted operation/scope, not a new authorization;
held in-flight references survive admission expiry until actual settlement.
Shared guards may coexist; exclusive deletion closes new admission,
waits for admitted readers/publications and checks the current metadata reference
revision/zero count. Exact-stamp checks occur again at the provider decision.
Readers cannot be revoked under live I/O merely because the guard TTL elapsed.
Stuck operations keep exclusion and block readiness.

The F-05 bridge converts bounded opaque metadata evidence to a current stamp
through the selected store. It returns the existing
`MetadataCommittedArtifact(digest,length)` under the same authority guard.
It neither writes metadata itself nor treats `ConfirmUnreferenced` as permission.
Evidence from a deleted/replaced incarnation cannot authorize a new reference.

## Recovery Observations and Capabilities

`ArtifactRecoveryQuery` has kind, at most 100 observations/page and a store/query-
bound continuation (at most 4 KiB); no arbitrary path, predicate or unbounded
enumerable. Observations contain typed staging, committed, uncertain or pending-
reclamation state, safe IDs and exact incarnation where applicable. Listing
completeness/consistency is explicit; changed/expired continuations yield conflict.
A page is an observation, never absence, ownership or deletion authority.

`ArtifactCleanupRequest` names at most 100 exact abandoned staging generations
or already logically removed incarnations. Cleanup rechecks authority/ownership,
never decides retention and never removes a visible unreferenced blob. Page
progress is repeatable and resumable; one call cannot sweep an unbounded root.

`ArtifactCapabilities` is a versioned immutable record: mandatory guarantees,
durability/failure model and configuration, direct visibility, conditional
publication/deletion, staging recovery/ownership, reader protection, enumeration
consistency, verification policy, limits and optional checksums/range reads.
Unknown mandatory versions/values reject operational admission. Optional range
is false for both fixtures; no Range/HEAD endpoint is introduced.

`ArtifactQualificationRecord` binds implementation/package/version/hash, config
hash, source/lock hashes, OS/runtime/filesystem, capabilities, exact required
case set, results/proof hashes and exclusions. Durable and simulated classes
are not interchangeable.

## Private Local State and Clock Rules

The local fixture owns bounded ticket records, immutable data incarnations,
checksummed current/tombstone decisions and staging owner records. A digest's
decision includes the operation ID, preventing a lost receipt from erasing the
commit decision. Finalize unfinished receipts before subsequent mutations can
replace that decision; retain finalized receipts for the ticket lifetime.
Deletion records logical absence before payload reclamation, so crash between
those steps cannot reopen removed content. Corrupt decision/ledger state blocks
admission without resetting or silently deleting evidence.

Ownership uses `effectiveNow < expiry`; equality is expired. Runtime budgets use
monotonic elapsed time. Persist nondecreasing observed UTC expiry decisions;
rollback cannot revive an expired ticket/generation. Restart fences the previous
process session before renewal or cleanup; recovery never assumes elapsed wall
time proves ownership while an old session still holds root ownership.
Counter overflow fails explicitly. Bounds include tickets/receipts, staged and
pending-reclamation objects; exhausted capacity fails admission, not evidence
eviction before expiry.
Prune a tombstone only after its payload is confirmed reclaimed and all linked
pending decisions are settled; receipt history remains for its full lifetime.
Fresh incarnation GUIDs are never reused, so tombstone pruning cannot revive an
old stamp. Pruning uses bounded maintenance pages, not a full in-memory scan.
