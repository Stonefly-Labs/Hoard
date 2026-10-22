# F-06 Provider-Neutral Artifact API

**Status**: Planned additive signatures and normative semantics.
Types are defined by the [model](../data-model.md); all implementations and
commands remain future work.

## Ownership and Signature Inventory

Keep the existing `IArtifactProvider` marker, module descriptors, registration,
lifecycle/configuration and metadata APIs unchanged. An operational provider
additionally implements `IArtifactStore`; a selected store without mandatory
guarantees fails operational admission rather than falling back. Old marker-only
hosts/providers remain valid for their old declaration-only use.

Proposed namespace: `Hoard.Abstractions.Storage`. All named records are closed,
immutable BCL values; no SDK, filesystem path, Hosting type, `DbContext`, raw
exception, arbitrary predicate or `IServiceProvider` crosses this boundary.
Declarations below are a signature inventory, not implementation bodies.

```csharp
public interface IArtifactStore
{
    ArtifactCapabilities Capabilities { get; }
    ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(
        ArtifactWriteIntent intent, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveDeleteAsync(
        ArtifactDeleteIntent intent, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
        ArtifactOperationTicket ticket, Stream source,
        ArtifactTransferOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactStagingOwner>> RenewAsync(
        ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(
        ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<IArtifactReadSession>> OpenReadAsync(
        ArtifactReadRequest request, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactMutationReceipt>> DeleteAsync(
        ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactResolution>> ReconcileAsync(
        ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactCleanupReport>> AbandonAsync(
        ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct);
}

public interface IArtifactReadSession : IAsyncDisposable
{
    ArtifactStamp Stamp { get; }
    ValueTask<ArtifactResult<ArtifactReadCompletion>> CopyToAsync(
        Stream destination, ArtifactTransferOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactShutdown>> CloseAsync(
        ArtifactCleanupOptions options, CancellationToken ct);
}

public interface IArtifactEvidenceValidator
{
    ValueTask<ArtifactResult<ArtifactStamp>> ValidateAsync(
        ArtifactCommitEvidence evidence, IArtifactProtectionGuard protection,
        ArtifactCallOptions options, CancellationToken ct);
}

public interface IArtifactMaintenance
{
    ValueTask<ArtifactResult<ArtifactRecoveryPage>> ObserveAsync(
        ArtifactRecoveryQuery query, ArtifactMaintenanceOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactCleanupReport>> CleanupAsync(
        ArtifactCleanupRequest request, ArtifactMaintenanceOptions options, CancellationToken ct);
}

public interface IArtifactStoreLifetime
{
    ValueTask<ArtifactResult<ArtifactAdmission>> InitializeAsync(
        ArtifactInitialization request, ArtifactMaintenanceOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactShutdown>> StopAsync(
        ArtifactCleanupOptions options, CancellationToken ct);
}

public interface IArtifactCoordinationAuthority
{
    ValueTask<ArtifactResult<IArtifactProtectionGuard>> AcquireAsync(
        ArtifactProtectionRequest request, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<IArtifactProtectionGuard>> RetainAsync(
        IArtifactProtectionGuard protection, ArtifactProtectionRequest expected,
        ArtifactCallOptions options, CancellationToken ct);
}

public interface IArtifactProtectionGuard : IAsyncDisposable
{
    ArtifactProtectionGrant Grant { get; }
}
```

Initialization injects exactly one authority and immutable store identity/options;
ordinary calls cannot substitute authority. Lifetime/maintenance are separate
contracts so read/write consumers cannot implicitly initialize, sweep or
reconfigure the store.

`RetainAsync` recognizes authority-owned opaque guard identity and atomically
pins its held protection for the same admitted operation, mode, store and stamp.
It returns an independently disposable reference to that same protection, not
a new gate acquisition. Reject copied field-equivalent wrappers, foreign guards,
disposed handles and changed scope. Reference counting prevents release of
exclusion while a retained owner still runs. Admission expiry rejects new
operations; it cannot revoke genuinely held in-flight work or its settlement
retention. Retention cannot renew admission or authorize a different operation.

The evidence validator calls this configured-authority recognition seam before
provider decision locks, owns the returned retention through validation, and
then releases it. It validates the exact receipt/stamp, current decision,
known-corruption state and direct payload availability without a new admission
or full media scrub. No recursion through OpenRead or metadata is permitted.
The bridge retains its original protection through the actual metadata outcome.
A metadata evidence handle encodes only the bounded store/ticket/stamp reference;
foreign, expired or unknown receipts reject.

## Verified Publication

1. Record a write ticket with the validated intent and staging-capacity
   reservation before I/O; the local durable profile persists it before returning.
   A reservation failure touches no source bytes.
2. `StageAsync` owns private staging, not the supplied stream. Consume from its
   current position through EOF using fixed asynchronous buffers/backpressure;
   seeking, length properties and replayability are not required. Check actual
   size incrementally and hash every byte. No hidden buffering in temp memory.
3. Match every expectation, record computed digest/length and verified completion
   under the current fenced owner. Any mismatch is definite nonpublication.
   A newly submitted stream must always be consumed/verified, even if its
   declared digest already exists. A decided ticket rejects staging; reconciliation
   without a new stream is distinct from accepting a new artifact.
4. `CommitAsync` obtains shared publication protection before provider decision
   locks. Check current generation/expiry again at the decision. If no identity
   exists, publish a fresh incarnation conditionally. If an incarnation exists,
   reverify its full bytes/length under protection; valid equivalent content
   reuses it, conflict/corruption never overwrites it.
5. Success requires the complete immutable bytes to be directly readable by
   committed identity under the selected configuration and a retained receipt.
   Commit may spend its finite transfer budget verifying an existing multi-GB
   artifact or resolving direct visibility. Listing cannot establish this.
6. Receipt carries `Published` or `AlreadyPresentVerified` evidence. No store
   operation writes cache metadata or claims an atomic cross-store transaction.

When digest is first computed, the provider serializes only its conditional
namespace decision, not all store transfers. Same-digest writers may stage
concurrently; failed losers clean up only their own staging. A conflicting
length under the same SHA-256 or detected stored corruption is explicit.
Automatic repair/replacement of corrupt incarnations is outside this feature.
Equivalent reuse records a per-ticket reuse decision bound to the existing
stamp before success (persisted for the local durable profile); losing its
acknowledgment does not require changing the existing namespace decision.

## Read Completion and Verification Policy

Open acquires shared reader protection and checks current decision/store/stamp,
then opens the exact immutable payload. Staging and logical tombstones are
never targets. No raw backing stream/path escapes.

Copy is asynchronous, bounded and backpressured; it hashes the exact bytes
delivered, verifies EOF and length, and completes only after writes to the
borrowed destination finish. The operation does not flush/dispose that destination
or certify its durability. Empty artifacts complete with SHA-256(empty), zero
length and no writes. A session permits one copy; early disposal is not success.
`CloseAsync` reports definite release or incomplete cleanup within its budget.
`DisposeAsync` uses the default cleanup budget and, on incomplete cleanup,
surfaces a fixed sanitized failure/event while the store supervisor retains
live ownership; it cannot silently succeed or dispose handles under active I/O.

The baseline verifies every new input, every existing-artifact reuse and every
full read. Open is not a media scrub. Detected corruption marks that incarnation
unusable, invalidates future evidence validation/reuse, and reports failure rather
than absence. No continuous audit/automatic repair is claimed. Corruption can
be detected after partial bytes reached a destination: that copy has no verified
success and the caller must abort/discard partial output, not cache/serve it as
completed content. Concurrent media damage is an explicit storage-failure model,
not a promise of never delivering a prefix before detection.

## Shared Reference and Deletion Authority

The host injects one authority shared by:

- store publication and protected reads;
- the adapter implementing existing `IMetadataPublicationAuthority`;
- physical deletion and relevant recovery decisions.

The metadata bridge resolves `MetadataArtifactEvidence` to current verified
store evidence, acquires shared protection, rechecks the exact stamp/direct
availability through `IArtifactEvidenceValidator` and returns the existing
digest/length guard. Hold protection until
the metadata transaction definitely settles, including late work after caller
timeout. Do not query the provider while holding a database transaction or
provider-private lock. Integration uses the existing metadata contract without
changing the SQLite/memory fixtures.

Deletion's exclusive guard closes admission of new readers/publications/reference
guards, drains existing shared guards and validates the selected metadata
authority's current zero-reference revision. Missing artifact metadata is
eligible only when an authoritative exact read confirms absence while that
same exclusion is held; a failed/unavailable query denies deletion.
F-05 `ConfirmUnreferenced` is one check inside this guard, not the guard itself.
All reference-creating paths must enter this authority; otherwise operational
composition is invalid.

The provider checks the ticket's exact incarnation again before the logical
removal decision and keeps exclusion until outcome is definite. `Removed`
prevents new opens, but space may be `ReclamationPending`. Background cleanup
can remove only that logically removed incarnation; it never removes a newly
published one at the same digest. Readers admitted before removal finish on
stable bytes or keep removal blocked.

First-use deletion of an old stamp after recreation yields `Conflict`. Repeated
same-ticket deletion returns the original logical receipt; a new ticket for that
old stamp while still absent yields `AlreadyAbsent`, never a false count of newly
removed bytes. A bare zero-reference observation, caller flag, expired grant,
foreign locator or delayed listing is never sufficient authority.

## Finite Work and Ownership

All bounds below are the qualification profile, not production defaults. Smaller
configured limits may reject work explicitly; claiming this full profile requires
admitting both SC-002 sizes. Limits are checked before allocations/I/O and during
work with checked 64-bit arithmetic.

| Resource | Default / maximum |
| --- | --- |
| Artifact byte cap | 8 GiB / 8 GiB; explicit smaller per-write cap allowed |
| Reserved staging bytes | 16 GiB total, reserve each ticket's cap until terminal cleanup |
| Transfer slots / waiting calls | Four / 32; bounded admission, no per-chunk tasks |
| Copy buffer / provider transfer buffers | 256 KiB / 2 MiB per admitted transfer |
| Control deadline | Five seconds / 30 seconds, positive and at least 1 ms |
| Transfer total deadline | Ten minutes / 30 minutes, positive and at least 1 ms |
| Transfer inactivity | 30 seconds / two minutes, never extends total deadline |
| Cleanup deadline | Five seconds / 30 seconds |
| Maintenance deadline / page | 30 seconds / two minutes; at most 100 observations or targets |
| Encoded decision / recovery page | 16 KiB / 1 MiB, fail rather than truncate |
| Owner TTL / renewal | 30 seconds / two minutes; renew at ten-second intervals |
| Live tickets / committed identities | 100,000 each; pending outcomes consume capacity |
| Ticket lifetime | 24 hours; capped, never extended by retry |

The slot follows the full operation; an open read retains a slot until disposed.
Read sessions and verified staging have 30-second idle ownership; renewals are
owned only while an active transfer/decision is progressing within its original
deadline. Stage success returns a fresh owner expiry; callers must commit or
explicitly renew/abandon within it. A renewal does not change generation or
revive an expired owner. Maintenance acquisition uses the same fenced rules.

Queueing, guards, verification, contention, visibility probes, I/O and receipt
construction consume the original monotonic deadline. Visibility/lock retries
are cooperative, at most one per 50 ms and within that deadline, never retries
of an unknown mutation under a new ticket. Nested work inherits the smaller
remaining budget; commit explicitly takes a transfer budget for full
existing-content verification.

Source/destination streams are borrowed and must honor asynchronous cancellation
for the qualified finite-release guarantee. Cancellation/deadline returns within
the caller budget; cooperative owned resources settle within cleanup budget.
Provider-owned handles, buffers, slots and guards are never released under live
I/O. A non-cooperative stream/native call keeps bounded ownership, stops further
admission and reports `CleanupIncomplete`/not-ready. Before publication, fence
the ticket so late source completion cannot commit; after a decision attempt
return `Uncertain(ticket)` and retain exclusion until reconciliation settles.
Do not close borrowed streams, kill threads, detach tasks or claim a permanent
device stall was successfully cleaned. F-02 host ownership handles incomplete
shutdown; a controlled child proves the negative and is terminated by its owner.

## Outcomes and Diagnostics

`ArtifactResult<T>` is a closed success/failure sum. Successful operations use
typed variants rather than nulls. Failure contains a fixed phase/reason,
correlation ID, safe action and ticket when needed, not sensitive arguments.

| Outcome | Meaning / safe action |
| --- | --- |
| `InvalidInput` | Malformed values, bounds, wrong intent; correct input, no mutation |
| `NotFound` | Confirmed exact committed absence, never an outage |
| `AlreadyPresentVerified` | Both submitted and existing content fully verified |
| `Conflict` / `Denied` | Stale stamp/owner or current reference/reader authority; re-observe, never bypass |
| `Unsupported` | Optional algorithm/operation unavailable; no silent downgrade |
| `LimitExceeded` / `Capacity` | Byte, queue, staging or ledger bound; stop without successful truncation |
| `AccessDenied` / `Unavailable` | Distinct access/device failure; explicit noncommit or uncertainty |
| `CorruptContent` / `CorruptState` | Bad bytes or decision/ledger; quarantine/block normal use, operator recovery |
| `CancelledBeforeCommit` / `DeadlineExceeded` | Known no mutation decision; late work fenced, cleanup status explicit |
| `Uncertain` | Decision may have happened; reconcile exact ticket, no new-ticket replay |
| `ReconciliationExpired` | Unknown, expired, foreign epoch or discarded history; stop automation |
| `CleanupIncomplete` / `Disposed` | Retained live ownership or closed admission; never claim success |

`Removed`, `AlreadyAbsent` and reclamation status are successful deletion
receipt variants. Pending reconciliation is not a final success. Unexpected
provider errors surface as sanitized `InternalFailure` with operator-recovery
guidance and a safe structured event. Known errors are translated at the owning
boundary; no broad catch-and-return-miss. Exceptions after a decision cannot
erase an existing receipt or prove rollback.

Public formatting/events omit raw paths, input bytes, credential-bearing URIs,
opaque handles, caller text, object-service versions and exception objects.
Only fixed phase/code, safe provider ID, counts and correlation are reported;
no unbounded metric dimensions. No new telemetry backend is required.

## Capabilities and Host Composition

Both fixtures declare full baseline integrity, bounded streaming, conditional
publication/deletion and reader protection. Local declares local process-crash
durability under exclusive same-filesystem ownership; alternative declares
simulation only, no rename, delayed enumeration/direct visibility, no durable
restart claim. Both explicitly disable range operations.

The external fixture module adapter registers in F-02/F-03, initializes only
when selected, recovers before readiness, maps no endpoints and stops using
owned lifetime rules. Disabled modules create no directory, worker or connection.
Duplicate/missing/mismatched mandatory contracts or authority wiring fail
startup; no fallback and no discovery "supported" claim from installation alone.
Changing store requires explicit validated composition/restart, not hot swap.
Core, Application and protocol slices gain no concrete-store reference.
