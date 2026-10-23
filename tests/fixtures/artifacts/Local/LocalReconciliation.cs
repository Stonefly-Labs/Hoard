using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactResolution>> ReconcileAsync(
        ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ticket);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync<ArtifactResolution>(ArtifactPhase.Reconcile, options.Deadline, ct, async token =>
        {
            LocalOperation operation;
            lock (stateSync)
            {
                operation = Find(ticket);
                if (operation.State is "committed" or "removed") { return Resolution(operation); }
                if (operation.State == "notcommitted") { return new ArtifactResolution.NotCommitted(ticket); }
                if (operation.State != "deciding") { return new ArtifactResolution.Pending(ticket); }
            }
            await faults.ObserveAsync("reconcile.before-resolution");
            var gate = DigestGate(operation.Content!.Digest);
            await gate.WaitAsync(token);
            try
            {
                lock (stateSync)
                {
                    if (operation.State != "deciding") { return Resolution(operation); }
                }
                if (operation.Kind == ArtifactOperationKind.Delete) { ResolveDeletion(operation); }
                else { await ResolvePublicationAsync(operation, token); }
                lock (stateSync)
                {
                    return Resolution(operation);
                }
            }
            finally { gate.Release(); }
        }, ticket);
    }

    private ArtifactResolution Resolution(LocalOperation operation)
        => operation.State switch
        {
            "committed" => new ArtifactResolution.Committed(Receipt(operation)),
            "removed" when operation.Outcome == ArtifactMutationOutcome.AlreadyAbsent => new ArtifactResolution.AlreadyAbsent(Receipt(operation)),
            "removed" => new ArtifactResolution.Removed(Receipt(operation)),
            "notcommitted" => new ArtifactResolution.NotCommitted(Ticket(operation)),
            _ => new ArtifactResolution.Pending(Ticket(operation))
        };

    private void ResolveDeletion(LocalOperation operation)
    {
        lock (stateSync)
        {
            if (operation.Outcome == ArtifactMutationOutcome.AlreadyAbsent && operation.Receipt != Guid.Empty)
            { operation.State = "removed"; Save(operation); return; }
            if (decisions.TryGetValue(operation.Content!.Digest, out var decision) && decision.Removed
                && decision.Operation == operation.Id && decision.Content == operation.Content)
            {
                if (!removedContent.ContainsKey(decision.Content.Incarnation)) { SaveRemoved(decision); }
                operation.Reclamation = File.Exists(PayloadPath(decision.Content)) ? ArtifactReclamation.Pending : ArtifactReclamation.Reclaimed;
                if (operation.Reclamation == ArtifactReclamation.Reclaimed) { Reclaim(decision.Content); }
                operation.State = "removed";
                Save(operation);
            }
            else { operation.State = "notcommitted"; Save(operation); }
        }
    }

    private async Task ResolvePublicationAsync(LocalOperation operation, CancellationToken token)
    {
        LocalDecision? current;
        lock (stateSync) { decisions.TryGetValue(operation.Content!.Digest, out current); }
        if (current is not null && current.Operation == operation.Id && !current.Removed
            && current.Content == operation.Content)
        {
            if (current.Corrupt || !await VerifyPayloadAsync(current.Content, new(), token))
            { throw new LocalStateException(ArtifactFailureCode.CorruptContent); }
            lock (stateSync)
            {
                FinalizePublication(operation);
                ReleaseStaging(operation);
            }
        }
        else
        {
            if (current?.Content.Incarnation == operation.Content!.Incarnation)
            { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
            lock (stateSync)
            {
                operation.State = "notcommitted";
                Save(operation);
                ReleaseStaging(operation);
                File.Delete(PayloadPath(operation.Content!));
            }
        }
    }

    private async Task RecoverAsync(CancellationToken ct)
    {
        operations.Clear();
        decisions.Clear();
        removedContent.Clear();
        pendingStagingCleanup.Clear();
        continuations.Clear();
        ClearHistoryIndexes();
        reserved = 0;
        foreach (var operation in ownership!.ReadRecords<LocalOperation>("tickets", Limits.LiveTickets, value => value.Id.ToString("N")))
        {
            ct.ThrowIfCancellationRequested();
            try
            {
                _ = Ticket(operation);
                if (operation.Cap < 0 || operation.Cap > Limits.ArtifactBytes
                    || operation.Kind == ArtifactOperationKind.Write && operation.Cap == 0
                    || !operations.TryAdd(operation.Id, operation)
                    || operation.State is not ("reserved" or "staging" or "verified" or "deciding" or "committed" or "notcommitted" or "removed"))
                { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
                if (operation.Content is not null) { _ = operation.Content.Stamp(StoreIdentity); }
                IndexTicket(operation);
                if (!operation.ReservationReleased) { reserved = checked(reserved + operation.Cap); }
            }
            catch (Exception error) when (error is ArgumentException or OverflowException)
            { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
        }
        if (operations.Count > Limits.LiveTickets || reserved > Limits.StagingBytes)
        { throw new LocalStateException(ArtifactFailureCode.Capacity); }
        foreach (var decision in ownership.ReadRecords<LocalDecision>("decisions", Limits.CommittedIdentities, value => value.Content.Digest))
        {
            ct.ThrowIfCancellationRequested();
            try
            {
                _ = decision.Content.Stamp(StoreIdentity);
                var retained = operations.TryGetValue(decision.Operation, out var ticket);
                if (decision.Operation == Guid.Empty
                    || decision.ReconcileUntil is { } until
                        && (until.Offset != TimeSpan.Zero || until < DateTimeOffset.UnixEpoch.AddHours(24)
                            || retained && until != ticket!.Expires)
                    || !retained && (decision.ReconcileUntil is not { } expiry || Now() < expiry)
                    || !decisions.TryAdd(decision.Content.Digest, decision))
                { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
                if (decisions.Count > Limits.CommittedIdentities) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
                IndexDecision(decision);
            }
            catch (ArgumentException) { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
        }
        foreach (var retired in ownership.ReadRecords<LocalDecision>("reclamation", Limits.CommittedIdentities, value => value.Content.Incarnation.ToString("N")))
        {
            if (!retired.Removed || !removedContent.TryAdd(retired.Content.Incarnation, retired))
            { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
            if (removedContent.Count > Limits.CommittedIdentities) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
            _ = retired.Content.Stamp(StoreIdentity);
            IndexReclamation(retired);
        }
        foreach (var operation in operations.Values)
        {
            ct.ThrowIfCancellationRequested();
            if (operation.State == "deciding")
            {
                if (operation.Kind == ArtifactOperationKind.Delete) { ResolveDeletion(operation); }
                else { await ResolvePublicationAsync(operation, ct); }
            }
            else if (operation.State is "staging" or "verified")
            {
                operation.State = "reserved";
                Save(operation);
            }
            else if (operation.State == "notcommitted")
            {
                ReleaseStaging(operation);
            }
            else if (operation.State == "committed")
            {
                if (operation.Content is null || operation.Receipt == Guid.Empty || operation.Proof.Length != 32)
                { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
                ReleaseStaging(operation);
            }
            else if (operation.State == "removed")
            {
                if (operation.Kind != ArtifactOperationKind.Delete || operation.Content is null
                    || operation.Receipt == Guid.Empty
                    || operation.Outcome is not (ArtifactMutationOutcome.Removed or ArtifactMutationOutcome.AlreadyAbsent))
                { throw new LocalStateException(ArtifactFailureCode.CorruptState); }
                if (removedContent.TryGetValue(operation.Content.Incarnation, out var retired)
                    && retired.Reclaimed && operation.Reclamation != ArtifactReclamation.Reclaimed)
                {
                    operation.Reclamation = ArtifactReclamation.Reclaimed;
                    Save(operation);
                }
            }
        }
    }
}
