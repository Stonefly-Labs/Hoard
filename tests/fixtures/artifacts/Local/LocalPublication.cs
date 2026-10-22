using System.Security.Cryptography;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(
        ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(staged);
        ArgumentNullException.ThrowIfNull(options);
        var owner = staged.Owner;
        var recognized = false;
        return ExecuteAsync(ArtifactPhase.Publication, options.Deadline, ct, async token =>
        {
            using var slot = await AdmitAsync(token);
            LocalOperation operation;
            var renewal = time.GetTimestamp();
            lock (stateSync)
            {
                operation = Find(staged.Owner.Ticket, ArtifactOperationKind.Write);
                if (operation.State == "committed") { return Receipt(operation); }
                CheckOwner(operation, staged.Owner, requireVerified: true);
                if (Staged(operation) != staged) { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
                recognized = true;
            }
            var request = new ArtifactProtectionRequest(operation.Id, ArtifactProtectionOperation.Publication,
                StoreIdentity, staged.Identity.Digest);
            var admission = await configuration!.Authority.AcquireAsync(request, new(), token);
            if (admission is not ArtifactResult<IArtifactProtectionGuard>.Success acquired)
            { throw new LocalStateException(admission is ArtifactResult<IArtifactProtectionGuard>.Failure failure ? failure.Code : ArtifactFailureCode.InternalFailure); }
            await using var protection = acquired.Value;
            await faults.ObserveAsync("publish.admitted");
            var gate = DigestGate(staged.Identity.Digest.Hex);
            await gate.WaitAsync(token);
            try
            {
                LocalDecision? current;
                lock (stateSync)
                {
                    CheckOwner(operation, staged.Owner, requireVerified: true);
                    decisions.TryGetValue(staged.Identity.Digest.Hex, out current);
                    if (current is { Removed: false, Corrupt: true }) { throw new LocalStateException(ArtifactFailureCode.CorruptContent); }
                    if (current is { Removed: false } && current.Content.Length != staged.Identity.Length)
                    { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                }
                if (current is { Removed: true })
                {
                    LocalOperation? deletion;
                    lock (stateSync) { operations.TryGetValue(current.Operation, out deletion); }
                    if (deletion?.State == "deciding") { ResolveDeletion(deletion); }
                }
                if (current is { Removed: false })
                {
                    LocalOperation? previous;
                    lock (stateSync) { operations.TryGetValue(current.Operation, out previous); }
                    if (previous?.State == "deciding") { await ResolvePublicationAsync(previous, token); }
                    if (!await VerifyPayloadAsync(current.Content, options, token, async () =>
                    {
                        await faults.ObserveAsync("publish.progress");
                        lock (stateSync)
                        {
                            token.ThrowIfCancellationRequested();
                            CheckOwner(operation, owner, requireVerified: true);
                            if (time.GetElapsedTime(renewal) >= configuration!.Ownership.Renewal)
                            {
                                operation.OwnerExpires = Now().Add(configuration.Ownership.Ttl);
                                owner = Owner(operation);
                                Save(operation);
                                renewal = time.GetTimestamp();
                            }
                        }
                    }))
                    {
                        lock (stateSync) { Save(current with { Corrupt = true }); }
                        throw new LocalStateException(ArtifactFailureCode.CorruptContent);
                    }
                    lock (stateSync)
                    {
                        token.ThrowIfCancellationRequested();
                        CheckOwner(operation, owner, requireVerified: true);
                        operation.Content = current.Content;
                        operation.Outcome = ArtifactMutationOutcome.AlreadyPresentVerified;
                        FinalizePublication(operation);
                        ReleaseStaging(operation);
                        return Receipt(operation);
                    }
                }
                await faults.ObserveAsync("publish.before-decision");
                lock (stateSync)
                {
                    token.ThrowIfCancellationRequested();
                    CheckOwner(operation, staged.Owner, requireVerified: true);
                    if (decisions.Values.Count(value => !value.Removed) + removedContent.Values.Count(value => !value.Reclaimed) >= Limits.CommittedIdentities)
                    { throw new LocalStateException(ArtifactFailureCode.Capacity); }
                    operation.Receipt = Guid.NewGuid();
                    operation.Proof = Guid.NewGuid().ToString("N");
                    operation.Outcome = ArtifactMutationOutcome.Published;
                    operation.State = "deciding";
                    Save(operation);
                    File.Move(StagePath(operation), PayloadPath(operation.Content!), overwrite: false);
                    Save(new LocalDecision(operation.Content!, operation.Id));
                }
                await faults.ObserveAsync("publish.decided");
                lock (stateSync)
                {
                    FinalizePublication(operation);
                    ReleaseStaging(operation);
                }
                await using (var direct = new FileStream(PayloadPath(operation.Content!), FileMode.Open, FileAccess.Read, FileShare.Read))
                {
                    if (direct.Length != operation.Content!.Length) { throw new LocalStateException(ArtifactFailureCode.CorruptContent); }
                }
                await faults.ObserveAsync("publish.receipted");
                token.ThrowIfCancellationRequested();
                lock (stateSync) { return Receipt(operation); }
            }
            finally { gate.Release(); }
        }, staged.Owner.Ticket, cancellationSettled: () =>
        {
            lock (stateSync)
            {
                if (operations.TryGetValue(staged.Owner.Ticket.Id, out var cancelled)
                    && Ticket(cancelled) == staged.Owner.Ticket
                    && Owner(cancelled) == owner && cancelled.State == "verified"
                    && (recognized || Staged(cancelled) == staged
                        && cancelled.Session == ownership!.State.SessionId
                        && Now() < cancelled.OwnerExpires && Now() < cancelled.Expires))
                {
                    cancelled.State = "notcommitted";
                    Save(cancelled);
                    ReleaseStaging(cancelled);
                }
            }
        });
    }

    private void FinalizePublication(LocalOperation operation)
    {
        if (operation.Receipt == Guid.Empty) { operation.Receipt = Guid.NewGuid(); }
        if (operation.Proof.Length == 0) { operation.Proof = Guid.NewGuid().ToString("N"); }
        operation.State = "committed";
        Save(operation);
    }

    private ArtifactMutationReceipt Receipt(LocalOperation operation)
    {
        var stamp = operation.Content!.Stamp(StoreIdentity);
        if (operation.Kind == ArtifactOperationKind.Delete)
        {
            if (operation.Reclamation == ArtifactReclamation.Pending
                && removedContent.TryGetValue(stamp.Incarnation, out var retired)
                && retired.Content == operation.Content && retired.Reclaimed)
            {
                operation.Reclamation = ArtifactReclamation.Reclaimed;
                Save(operation);
            }
            return new(Ticket(operation), operation.Receipt, operation.Outcome, stamp,
                ArtifactVisibility.Removed, operation.Reclamation);
        }
        return new(Ticket(operation), operation.Receipt, operation.Outcome, stamp, ArtifactVisibility.Committed,
            ArtifactReclamation.NotApplicable, new ArtifactOption<ArtifactCommitEvidence>.Some(new(
                stamp, operation.Id, operation.Receipt, operation.Proof, (ArtifactPublicationOutcome)operation.Outcome)));
    }

    private async Task<bool> VerifyPayloadAsync(LocalContent content, ArtifactTransferOptions options, CancellationToken ct,
        Func<ValueTask>? progress = null)
    {
        var path = PayloadPath(content);
        if (!File.Exists(path)) { return false; }
        await using var input = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read,
            1, FileOptions.Asynchronous | FileOptions.SequentialScan);
        using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        var buffer = new byte[Limits.CopyBufferBytes];
        long length = 0;
        while (true)
        {
            using var inactivity = CancellationTokenSource.CreateLinkedTokenSource(ct);
            inactivity.CancelAfter(options.Inactivity);
            var count = await input.ReadAsync(buffer, inactivity.Token);
            ct.ThrowIfCancellationRequested();
            if (count == 0) { break; }
            length = checked(length + count);
            if (length > content.Length) { return false; }
            hash.AppendData(buffer, 0, count);
            if (progress is not null) { await progress(); }
        }
        return length == content.Length && Convert.ToHexStringLower(hash.GetHashAndReset()) == content.Digest;
    }
}
