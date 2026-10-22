using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveDeleteAsync(
        ArtifactDeleteIntent intent, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(intent);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Reserve, options.Deadline, ct, token =>
        {
            lock (stateSync)
            {
                if (intent.Target.Store != StoreIdentity) { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
                RetireExpiredTickets(token);
                if (operations.Count >= Limits.LiveTickets) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
                token.ThrowIfCancellationRequested();
                var now = Now();
                var operation = new LocalOperation
                {
                    Id = Guid.NewGuid(),
                    Kind = ArtifactOperationKind.Delete,
                    Issued = now,
                    Expires = now.AddHours(24),
                    Content = new(intent.Target.Identity.Digest.Hex, intent.Target.Identity.Length, intent.Target.Incarnation),
                    ReservationReleased = true
                };
                operation.Fingerprint = Fingerprint(operation.Content);
                Save(operation);
                if (!operations.TryAdd(operation.Id, operation)) { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                return Task.FromResult(Ticket(operation));
            }
        });
    }

    public ValueTask<ArtifactResult<ArtifactMutationReceipt>> DeleteAsync(
        ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ticket);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Delete, options.Deadline, ct, async token =>
        {
            LocalOperation operation;
            lock (stateSync)
            {
                operation = Find(ticket, ArtifactOperationKind.Delete);
                if (operation.State == "removed") { return Receipt(operation); }
                if (operation.State != "reserved") { throw new LocalStateException(ArtifactFailureCode.Conflict); }
            }
            var stamp = operation.Content!.Stamp(StoreIdentity);
            var grant = await configuration!.Authority.AcquireAsync(new(ticket.Id, ArtifactProtectionOperation.Deletion,
                StoreIdentity, stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(stamp)), options, token);
            if (grant is not ArtifactResult<IArtifactProtectionGuard>.Success accepted)
            { throw new LocalStateException(grant is ArtifactResult<IArtifactProtectionGuard>.Failure failure ? failure.Code : ArtifactFailureCode.InternalFailure); }
            await using var protection = accepted.Value;
            var gate = DigestGate(stamp.Identity.Digest.Hex);
            await gate.WaitAsync(token);
            try
            {
                LocalDecision? current;
                lock (stateSync) { decisions.TryGetValue(stamp.Identity.Digest.Hex, out current); }
                if (current is { Removed: false })
                {
                    if (current.Content.Stamp(StoreIdentity) != stamp) { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                    LocalOperation? prior;
                    lock (stateSync) { operations.TryGetValue(current.Operation, out prior); }
                    if (prior?.State == "deciding") { await ResolvePublicationAsync(prior, token); }
                }
                lock (stateSync)
                {
                    token.ThrowIfCancellationRequested();
                    if (current is { Removed: false } && !removedContent.ContainsKey(stamp.Incarnation)
                        && removedContent.Count >= Limits.CommittedIdentities)
                    { throw new LocalStateException(ArtifactFailureCode.Capacity); }
                    operation.Receipt = Guid.NewGuid();
                    operation.Outcome = current is { Removed: false } ? ArtifactMutationOutcome.Removed : ArtifactMutationOutcome.AlreadyAbsent;
                    operation.Reclamation = operation.Outcome == ArtifactMutationOutcome.Removed
                        || removedContent.TryGetValue(stamp.Incarnation, out var old) && !old.Reclaimed
                        ? ArtifactReclamation.Pending : ArtifactReclamation.Reclaimed;
                    operation.State = "deciding";
                    Save(operation);
                    if (operation.Outcome == ArtifactMutationOutcome.Removed)
                    {
                        var tombstone = new LocalDecision(operation.Content!, operation.Id, Removed: true,
                            ReconcileUntil: operation.Expires);
                        Save(tombstone);
                        SaveRemoved(tombstone);
                    }
                    operation.State = "removed";
                    Save(operation);
                }
                if (operation.Outcome == ArtifactMutationOutcome.Removed)
                {
                    await faults.ObserveAsync("delete.removed");
                    token.ThrowIfCancellationRequested();
                    lock (stateSync) { Reclaim(operation.Content!); }
                    await faults.ObserveAsync("delete.reclaimed");
                    lock (stateSync)
                    {
                        operation.Reclamation = ArtifactReclamation.Reclaimed;
                        Save(operation);
                    }
                }
                token.ThrowIfCancellationRequested();
                lock (stateSync) { return Receipt(operation); }
            }
            finally { gate.Release(); }
        }, ticket);
    }

    private void SaveRemoved(LocalDecision decision)
    {
        if (!removedContent.ContainsKey(decision.Content.Incarnation) && removedContent.Count >= Limits.CommittedIdentities)
        { throw new LocalStateException(ArtifactFailureCode.Capacity); }
        ownership!.WriteRecord("reclamation", decision.Content.Incarnation.ToString("N"), decision);
        removedContent[decision.Content.Incarnation] = decision;
        inventoryRevision = checked(inventoryRevision + 1);
    }

    private long Reclaim(LocalContent content)
    {
        if (!removedContent.TryGetValue(content.Incarnation, out var tombstone) || tombstone.Content != content)
        { throw new LocalStateException(ArtifactFailureCode.Conflict); }
        if (decisions.TryGetValue(content.Digest, out var current) && !current.Removed
            && current.Content.Incarnation == content.Incarnation)
        { throw new LocalStateException(ArtifactFailureCode.Conflict); }
        var path = PayloadPath(content);
        var length = File.Exists(path) ? new FileInfo(path).Length : 0;
        File.Delete(path);
        SaveRemoved(tombstone with { Reclaimed = true });
        if (current is { Removed: true } && current.Content == content)
        { Save(current with { Reclaimed = true }); }
        return length;
    }
}
