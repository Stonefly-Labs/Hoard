using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

public sealed partial class ObjectArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactResolution>> ReconcileAsync(
        ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ticket);
        ArgumentNullException.ThrowIfNull(options);
        return OwnedAsync<ArtifactResolution>(ArtifactPhase.Reconcile, options.Deadline, ct, async token =>
        {
            ObjectOperation upload;
            ObjectPointer pointer;
            lock (pointerSync)
            {
                upload = Operation(ticket);
                if (upload.Receipt is { } receipt)
                {
                    if (ticket.Kind == ArtifactOperationKind.Delete) { receipt = RefreshDeletionReceipt(upload); }
                    return receipt.Outcome switch
                    {
                        ArtifactMutationOutcome.Removed => new ArtifactResolution.Removed(receipt),
                        ArtifactMutationOutcome.AlreadyAbsent => new ArtifactResolution.AlreadyAbsent(receipt),
                        _ => new ArtifactResolution.Committed(receipt)
                    };
                }
                if (upload.Fenced) { return new ArtifactResolution.NotCommitted(ticket); }
                if (!upload.Deciding || upload.Selected is not { } selected) { return new ArtifactResolution.Pending(ticket); }
                pointer = selected;
                if (!pointers.TryGetValue(pointer.Stamp.Identity.Digest.Hex, out var current) || current != selected)
                { throw new ObjectOperationException(ArtifactFailureCode.CorruptState); }
            }
            await faults.ObserveAsync("object.direct");
            lock (pointerSync)
            {
                if (upload.Receipt is { } settled) { return new ArtifactResolution.Committed(settled); }
            }
            var admission = await initializedWith!.Authority.AcquireAsync(new(Guid.NewGuid(),
                ArtifactProtectionOperation.Read, Identity, pointer.Stamp.Identity.Digest,
                new ArtifactOption<ArtifactStamp>.Some(pointer.Stamp)), options, token);
            if (admission is not ArtifactResult<IArtifactProtectionGuard>.Success accepted)
            { throw new ObjectOperationException(admission is ArtifactResult<IArtifactProtectionGuard>.Failure failed ? failed.Code : ArtifactFailureCode.InternalFailure); }
            await using var protection = accepted.Value;
            lock (pointerSync)
            {
                if (upload.Receipt is { } settled) { return new ArtifactResolution.Committed(settled); }
            }
            if (pointer.Corrupt || !await VerifyObjectAsync(pointer, new(), token))
            { throw new ObjectOperationException(ArtifactFailureCode.CorruptContent); }
            lock (pointerSync)
            {
                token.ThrowIfCancellationRequested();
                if (upload.Receipt is { } settled) { return new ArtifactResolution.Committed(settled); }
                if (pointers[pointer.Stamp.Identity.Digest.Hex] != pointer)
                { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                return new ArtifactResolution.Committed(RecordObjectReceipt(upload));
            }
        }, ticket);
    }
}
