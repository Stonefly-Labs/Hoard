using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

public sealed partial class ObjectArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveDeleteAsync(
        ArtifactDeleteIntent intent, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(intent);
        ArgumentNullException.ThrowIfNull(options);
        return OwnedAsync(ArtifactPhase.Reserve, options.Deadline, ct, token =>
        {
            lock (pointerSync)
            {
                if (intent.Target.Store != Identity) { throw new ObjectOperationException(ArtifactFailureCode.InvalidInput); }
                ExpireHistory(token);
                if (uploads.Count >= Bounds.LiveTickets) { throw new ObjectOperationException(ArtifactFailureCode.Capacity); }
                token.ThrowIfCancellationRequested();
                var now = EffectiveNow();
                var bytes = JsonSerializer.SerializeToUtf8Bytes(new
                {
                    intent.Target.Incarnation,
                    intent.Target.Identity.Digest.Hex,
                    intent.Target.Identity.Length,
                    Identity.Epoch
                });
                var ticket = new ArtifactOperationTicket(Identity, Guid.NewGuid(), ArtifactOperationKind.Delete,
                    now, now.AddHours(24), Convert.ToHexStringLower(SHA256.HashData(bytes)));
                if (!uploads.TryAdd(ticket.Id, new(ticket, new ArtifactExpectations(1))
                { DeleteTarget = intent.Target, ReservationReleased = true }))
                { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                listingRevision = checked(listingRevision + 1);
                return Task.FromResult(ticket);
            }
        });
    }

    public ValueTask<ArtifactResult<ArtifactMutationReceipt>> DeleteAsync(
        ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ticket);
        ArgumentNullException.ThrowIfNull(options);
        return OwnedAsync(ArtifactPhase.Delete, options.Deadline, ct, async token =>
        {
            ObjectOperation deletion;
            ArtifactStamp target;
            lock (pointerSync)
            {
                deletion = Operation(ticket);
                if (deletion.Receipt is not null) { return RefreshDeletionReceipt(deletion); }
                if (ticket.Kind != ArtifactOperationKind.Delete || deletion.DeleteTarget is not { } stamp)
                { throw new ObjectOperationException(ArtifactFailureCode.InvalidInput); }
                target = stamp;
            }
            var admission = await initializedWith!.Authority.AcquireAsync(new(ticket.Id,
                ArtifactProtectionOperation.Deletion, Identity, target.Identity.Digest,
                new ArtifactOption<ArtifactStamp>.Some(target)), options, token);
            if (admission is not ArtifactResult<IArtifactProtectionGuard>.Success accepted)
            { throw new ObjectOperationException(admission is ArtifactResult<IArtifactProtectionGuard>.Failure failed ? failed.Code : ArtifactFailureCode.InternalFailure); }
            await using var exclusion = accepted.Value;
            ObjectPointer? observed;
            lock (pointerSync) { pointers.TryGetValue(target.Identity.Digest.Hex, out observed); }
            await faults.ObserveAsync("pointer.compare");
            lock (pointerSync)
            {
                token.ThrowIfCancellationRequested();
                pointers.TryGetValue(target.Identity.Digest.Hex, out var current);
                if (current != observed) { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                if (current is { Removed: false })
                {
                    if (current.Stamp != target) { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                    if (uploads.Values.Any(upload => upload.Selected == current && upload.Deciding && upload.Receipt is null))
                    { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                }
                deletion.Outcome = current is { Removed: false } ? ArtifactMutationOutcome.Removed : ArtifactMutationOutcome.AlreadyAbsent;
                deletion.Deciding = true;
                deletion.ReceiptId = Guid.NewGuid();
                if (current is { Removed: false })
                {
                    var tombstone = current with
                    {
                        Removed = true,
                        Version = checked(current.Version + 1),
                        OperationId = ticket.Id,
                        HistoryUntil = ticket.Expires
                    };
                    pointers[target.Identity.Digest.Hex] = tombstone;
                    retiredObjects[target.Incarnation] = tombstone;
                    deletion.Selected = tombstone;
                }
                var pending = retiredObjects.ContainsKey(target.Incarnation);
                deletion.Receipt = new(ticket, deletion.ReceiptId, deletion.Outcome, target,
                    ArtifactVisibility.Removed, pending ? ArtifactReclamation.Pending : ArtifactReclamation.Reclaimed);
                listingRevision = checked(listingRevision + 1);
            }
            if (deletion.Outcome == ArtifactMutationOutcome.Removed)
            {
                await faults.ObserveAsync("pointer.tombstone");
                token.ThrowIfCancellationRequested();
                lock (pointerSync) { ReclaimObject(target); }
                await faults.ObserveAsync("object.reclaimed");
                lock (pointerSync)
                {
                    deletion.Receipt = new(ticket, deletion.ReceiptId, deletion.Outcome, target,
                        ArtifactVisibility.Removed, ArtifactReclamation.Reclaimed);
                }
            }
            token.ThrowIfCancellationRequested();
            return deletion.Receipt;
        }, ticket);
    }

    private ArtifactMutationReceipt RefreshDeletionReceipt(ObjectOperation operation)
    {
        var receipt = operation.Receipt!;
        if (receipt.Reclamation == ArtifactReclamation.Pending
            && !retiredObjects.ContainsKey(receipt.Stamp.Incarnation))
        {
            receipt = new(receipt.Ticket, receipt.ReceiptId, receipt.Outcome, receipt.Stamp,
                receipt.Visibility, ArtifactReclamation.Reclaimed);
            operation.Receipt = receipt;
        }
        return receipt;
    }

    private long ReclaimObject(ArtifactStamp stamp)
    {
        if (!retiredObjects.TryGetValue(stamp.Incarnation, out var retired) || retired.Stamp != stamp)
        { return 0; }
        if (pointers.TryGetValue(stamp.Identity.Digest.Hex, out var current)
            && !current.Removed && current.ObjectId == retired.ObjectId)
        { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
        var path = ObjectPath(retired.ObjectId);
        var bytes = File.Exists(path) ? new FileInfo(path).Length : 0;
        faults.BeforeObjectDelete?.Invoke();
        File.Delete(path);
        retiredObjects.Remove(stamp.Incarnation);
        listingRevision = checked(listingRevision + 1);
        return bytes;
    }
}
