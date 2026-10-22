using System.Text.Json;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

internal sealed record LocalContinuation(Guid Session, ArtifactRecoveryKind Kind, int Size,
    long Revision, int Offset, DateTimeOffset Expires);

public sealed partial class LocalArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactCleanupReport>> AbandonAsync(
        ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(owner);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Cleanup, options.Deadline, ct, token =>
        {
            lock (stateSync)
            {
                var operation = Find(owner.Ticket, ArtifactOperationKind.Write);
                CheckOwner(operation, owner, requireVerified: true);
                if (IsBusy(owner.Ticket.Id)) { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                token.ThrowIfCancellationRequested();
                var path = StagePath(operation);
                var bytes = File.Exists(path) ? new FileInfo(path).Length : 0;
                operation.State = "notcommitted";
                Save(operation);
                ReleaseStaging(operation);
                return Task.FromResult(new ArtifactCleanupReport(1, 0, 0, bytes));
            }
        }, owner.Ticket);
    }

    public ValueTask<ArtifactResult<ArtifactRecoveryPage>> ObserveAsync(
        ArtifactRecoveryQuery query, ArtifactMaintenanceOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(query);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Maintenance, options.Deadline, ct, token =>
        {
            lock (stateSync)
            {
                if (query.Store != StoreIdentity) { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
                var offset = 0;
                var now = Now();
                if (query.Continuation is ArtifactOption<string>.Some next)
                {
                    if (!continuations.TryGetValue(next.Value, out var cursor) || cursor.Session != ownership!.State.SessionId
                        || cursor.Kind != query.Kind || cursor.Size != query.PageSize || cursor.Revision != inventoryRevision || now >= cursor.Expires)
                    { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                    offset = cursor.Offset;
                }
                var rows = Inventory(query.Kind, now).OrderBy(row => row.OperationId).Skip(offset).Take(query.PageSize + 1).ToArray();
                token.ThrowIfCancellationRequested();
                ArtifactOption<string> continuation = new ArtifactOption<string>.None();
                if (rows.Length > query.PageSize)
                {
                    foreach (var expired in continuations.Where(pair => now >= pair.Value.Expires).Select(pair => pair.Key).ToArray())
                    { continuations.Remove(expired); }
                    if (continuations.Count >= 32) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
                    var key = Guid.NewGuid().ToString("N");
                    continuations.Add(key, new(ownership!.State.SessionId, query.Kind, query.PageSize, inventoryRevision,
                        checked(offset + query.PageSize), now.AddSeconds(30)));
                    continuation = new ArtifactOption<string>.Some(key);
                }
                var page = new ArtifactRecoveryPage(rows.Take(query.PageSize), ArtifactEnumerationConsistency.Snapshot, continuation);
                var encoded = JsonSerializer.SerializeToUtf8Bytes(rows.Select(row => new
                {
                    row.Kind,
                    row.OperationId,
                    Stamp = row.Stamp is ArtifactOption<ArtifactStamp>.Some stamp ? stamp.Value : null,
                    Owner = row.Owner is ArtifactOption<ArtifactStagingOwner>.Some owner ? owner.Value : null
                }));
                if (encoded.Length > Limits.PageBytes) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
                return Task.FromResult(page);
            }
        });
    }

    private IEnumerable<ArtifactRecoveryObservation> Inventory(ArtifactRecoveryKind kind, DateTimeOffset now)
    {
        if (kind is ArtifactRecoveryKind.All or ArtifactRecoveryKind.Staging)
        {
            foreach (var operation in operations.Values.Where(value => value.Owner != Guid.Empty && !value.ReservationReleased
                && value.State is "reserved" or "staging" or "verified" or "notcommitted"))
            {
                var abandoned = operation.Session != ownership!.State.SessionId || now >= operation.OwnerExpires;
                yield return new(abandoned ? ArtifactObservationKind.AbandonedStaging : ArtifactObservationKind.ActiveStaging,
                    operation.Id, owner: new ArtifactOption<ArtifactStagingOwner>.Some(Owner(operation)));
            }
        }
        if (kind is ArtifactRecoveryKind.All or ArtifactRecoveryKind.Committed)
        {
            foreach (var decision in decisions.Values.Where(value => !value.Removed))
            { yield return new(ArtifactObservationKind.Committed, decision.Operation, new ArtifactOption<ArtifactStamp>.Some(decision.Content.Stamp(StoreIdentity))); }
        }
        if (kind is ArtifactRecoveryKind.All or ArtifactRecoveryKind.Uncertain)
        {
            foreach (var operation in operations.Values.Where(value => value.State == "deciding"))
            { yield return new(ArtifactObservationKind.Uncertain, operation.Id); }
        }
        if (kind is ArtifactRecoveryKind.All or ArtifactRecoveryKind.PendingReclamation)
        {
            foreach (var decision in removedContent.Values.Where(value => !value.Reclaimed))
            { yield return new(ArtifactObservationKind.PendingReclamation, decision.Operation, new ArtifactOption<ArtifactStamp>.Some(decision.Content.Stamp(StoreIdentity))); }
        }
    }

    public ValueTask<ArtifactResult<ArtifactCleanupReport>> CleanupAsync(
        ArtifactCleanupRequest request, ArtifactMaintenanceOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Maintenance, options.Deadline, ct, async token =>
        {
            if (request.Store != StoreIdentity) { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
            var completed = 0;
            var conflicted = 0;
            long bytes = 0;
            foreach (var target in request.Targets)
            {
                await faults.ObserveAsync("cleanup.candidate");
                lock (stateSync)
                {
                    token.ThrowIfCancellationRequested();
                    if (target is ArtifactCleanupTarget.AbandonedStaging staging)
                    {
                        if (!operations.TryGetValue(staging.Owner.Ticket.Id, out var operation)
                            || operation.Owner == Guid.Empty || Owner(operation) != staging.Owner
                            || IsBusy(operation.Id) || operation.State is not ("reserved" or "staging" or "verified")
                            || operation.Session == ownership!.State.SessionId && Now() < operation.OwnerExpires)
                        { conflicted++; continue; }
                        var path = StagePath(operation);
                        bytes = checked(bytes + (File.Exists(path) ? new FileInfo(path).Length : 0));
                        ReleaseStaging(operation);
                        operation.State = "reserved";
                        operation.Verified = Guid.Empty;
                        operation.Content = null;
                        Save(operation);
                        completed++;
                    }
                    else if (target is ArtifactCleanupTarget.RemovedIncarnation removed)
                    {
                        if (!removedContent.TryGetValue(removed.Stamp.Incarnation, out var retired)
                            || retired.Content.Stamp(StoreIdentity) != removed.Stamp)
                        { conflicted++; continue; }
                        bytes = checked(bytes + Reclaim(retired.Content));
                        completed++;
                    }
                }
            }
            return new ArtifactCleanupReport(completed, conflicted, 0, bytes);
        });
    }
}
