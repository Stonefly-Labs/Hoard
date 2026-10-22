using System.Text.Json;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

internal sealed record ObjectCursor(ArtifactRecoveryKind Kind, int PageSize, long Revision,
    int Offset, DateTimeOffset Until);

public sealed partial class ObjectArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactCleanupReport>> AbandonAsync(
        ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(owner);
        ArgumentNullException.ThrowIfNull(options);
        return OwnedAsync(ArtifactPhase.Cleanup, options.Deadline, ct, token =>
        {
            lock (pointerSync)
            {
                var upload = Operation(owner.Ticket);
                CurrentOwner(upload, owner);
                if (MutationActive(owner.Ticket.Id)) { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                token.ThrowIfCancellationRequested();
                var bytes = upload.Parts.Sum(part => new FileInfo(PartPath(part)).Length);
                upload.Fenced = true;
                RemoveMultipart(upload);
                return Task.FromResult(new ArtifactCleanupReport(1, 0, 0, bytes));
            }
        }, owner.Ticket);
    }

    public ValueTask<ArtifactResult<ArtifactRecoveryPage>> ObserveAsync(
        ArtifactRecoveryQuery query, ArtifactMaintenanceOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(query);
        ArgumentNullException.ThrowIfNull(options);
        return OwnedAsync(ArtifactPhase.Maintenance, options.Deadline, ct, async token =>
        {
            if (query.Store != Identity) { throw new ObjectOperationException(ArtifactFailureCode.InvalidInput); }
            await faults.ObserveAsync("object.list");
            lock (pointerSync)
            {
                token.ThrowIfCancellationRequested();
                var now = EffectiveNow();
                var offset = 0;
                if (query.Continuation is ArtifactOption<string>.Some value)
                {
                    if (!listingCursors.TryGetValue(value.Value, out var cursor) || cursor.Kind != query.Kind
                        || cursor.PageSize != query.PageSize || cursor.Revision != listingRevision || now >= cursor.Until)
                    { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                    offset = cursor.Offset;
                }
                var rows = ObjectObservations(query.Kind, now).OrderBy(row => row.OperationId)
                    .Skip(offset).Take(query.PageSize + 1).ToArray();
                ArtifactOption<string> next = new ArtifactOption<string>.None();
                if (rows.Length > query.PageSize)
                {
                    foreach (var old in listingCursors.Where(pair => now >= pair.Value.Until).Select(pair => pair.Key).ToArray())
                    { listingCursors.Remove(old); }
                    if (listingCursors.Count >= 32) { throw new ObjectOperationException(ArtifactFailureCode.Capacity); }
                    var handle = Guid.NewGuid().ToString("N");
                    listingCursors.Add(handle, new(query.Kind, query.PageSize, listingRevision,
                        checked(offset + query.PageSize), now.AddSeconds(30)));
                    next = new ArtifactOption<string>.Some(handle);
                }
                var encoded = JsonSerializer.SerializeToUtf8Bytes(rows.Select(row => new
                {
                    row.Kind,
                    row.OperationId,
                    Stamp = row.Stamp is ArtifactOption<ArtifactStamp>.Some stamp ? stamp.Value : null,
                    Owner = row.Owner is ArtifactOption<ArtifactStagingOwner>.Some owner ? owner.Value : null
                }));
                if (encoded.Length > Bounds.PageBytes) { throw new ObjectOperationException(ArtifactFailureCode.Capacity); }
                return new ArtifactRecoveryPage(rows.Take(query.PageSize), ArtifactEnumerationConsistency.Incomplete, next);
            }
        });
    }

    private IEnumerable<ArtifactRecoveryObservation> ObjectObservations(ArtifactRecoveryKind kind, DateTimeOffset now)
    {
        if (kind is ArtifactRecoveryKind.All or ArtifactRecoveryKind.Staging)
        {
            foreach (var upload in uploads.Values.Where(upload => upload.Owner is not null && !upload.ReservationReleased && upload.Receipt is null))
            {
                yield return new(now >= upload.Owner!.Expires ? ArtifactObservationKind.AbandonedStaging : ArtifactObservationKind.ActiveStaging,
                    upload.Ticket.Id, owner: new ArtifactOption<ArtifactStagingOwner>.Some(upload.Owner));
            }
        }
        if (kind is ArtifactRecoveryKind.All or ArtifactRecoveryKind.Committed)
        {
            foreach (var pointer in pointers.Values.Where(pointer => !pointer.Removed))
            {
                yield return new(ArtifactObservationKind.Committed, pointer.OperationId, new ArtifactOption<ArtifactStamp>.Some(pointer.Stamp));
            }
        }
        if (kind is ArtifactRecoveryKind.All or ArtifactRecoveryKind.Uncertain)
        {
            foreach (var upload in uploads.Values.Where(upload => upload.Deciding && upload.Receipt is null))
            { yield return new(ArtifactObservationKind.Uncertain, upload.Ticket.Id); }
        }
        if (kind is ArtifactRecoveryKind.All or ArtifactRecoveryKind.PendingReclamation)
        {
            foreach (var pointer in retiredObjects.Values)
            {
                yield return new(ArtifactObservationKind.PendingReclamation, pointer.OperationId, new ArtifactOption<ArtifactStamp>.Some(pointer.Stamp));
            }
        }
    }

    public ValueTask<ArtifactResult<ArtifactCleanupReport>> CleanupAsync(
        ArtifactCleanupRequest request, ArtifactMaintenanceOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(options);
        return OwnedAsync(ArtifactPhase.Maintenance, options.Deadline, ct, async token =>
        {
            if (request.Store != Identity) { throw new ObjectOperationException(ArtifactFailureCode.InvalidInput); }
            var completed = 0;
            var conflicted = 0;
            long bytes = 0;
            foreach (var target in request.Targets)
            {
                await faults.ObserveAsync("multipart.cleanup");
                lock (pointerSync)
                {
                    token.ThrowIfCancellationRequested();
                    if (target is ArtifactCleanupTarget.AbandonedStaging abandoned)
                    {
                        if (!uploads.TryGetValue(abandoned.Owner.Ticket.Id, out var upload) || upload.Owner != abandoned.Owner
                            || upload.Receipt is not null || upload.Deciding || upload.Fenced || MutationActive(upload.Ticket.Id)
                            || EffectiveNow() < abandoned.Owner.Expires)
                        { conflicted++; continue; }
                        bytes = checked(bytes + upload.Parts.Sum(part => new FileInfo(PartPath(part)).Length));
                        RemoveMultipart(upload);
                        upload.Owner = null;
                        upload.Verified = null;
                        upload.Fenced = false;
                        completed++;
                    }
                    else if (target is ArtifactCleanupTarget.RemovedIncarnation removed)
                    {
                        if (!retiredObjects.TryGetValue(removed.Stamp.Incarnation, out var retired) || retired.Stamp != removed.Stamp)
                        { conflicted++; continue; }
                        bytes = checked(bytes + ReclaimObject(removed.Stamp));
                        completed++;
                    }
                }
            }
            return new ArtifactCleanupReport(completed, conflicted, 0, bytes);
        });
    }
}
