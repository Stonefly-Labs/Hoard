using System.Security.Cryptography;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

public sealed partial class ObjectArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(
        ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(staged);
        ArgumentNullException.ThrowIfNull(options);
        var owner = staged.Owner;
        var recognized = false;
        return OwnedAsync(ArtifactPhase.Publication, options.Deadline, ct, async token =>
        {
            using var lease = await EnterTransferAsync(token);
            ObjectOperation upload;
            var renewedAt = time.GetTimestamp();
            ObjectPointer? observed;
            lock (pointerSync)
            {
                upload = Operation(staged.Owner.Ticket);
                if (upload.Receipt is { } receipt) { return receipt; }
                CurrentOwner(upload, staged.Owner);
                if (upload.Verified != staged) { throw new ObjectOperationException(ArtifactFailureCode.InvalidInput); }
                recognized = true;
                pointers.TryGetValue(staged.Identity.Digest.Hex, out observed);
            }
            var admitted = await initializedWith!.Authority.AcquireAsync(new(upload.Ticket.Id,
                ArtifactProtectionOperation.Publication, Identity, staged.Identity.Digest), new(), token);
            if (admitted is not ArtifactResult<IArtifactProtectionGuard>.Success accepted)
            { throw new ObjectOperationException(admitted is ArtifactResult<IArtifactProtectionGuard>.Failure failed ? failed.Code : ArtifactFailureCode.InternalFailure); }
            await using var protection = accepted.Value;
            await faults.ObserveAsync("object.publication-admitted");
            var objectId = Guid.NewGuid();
            var selected = false;
            try
            {
                async ValueTask Progress()
                {
                    await faults.ObserveAsync("object.commit-progress");
                    lock (pointerSync)
                    {
                        token.ThrowIfCancellationRequested();
                        CurrentOwner(upload, owner);
                        if (time.GetElapsedTime(renewedAt) >= initializedWith!.Ownership.Renewal)
                        {
                            owner = new(owner.Ticket, owner.SessionId, owner.OwnerId, owner.Generation,
                                EffectiveNow().Add(initializedWith.Ownership.Ttl));
                            upload.Owner = owner;
                            renewedAt = time.GetTimestamp();
                        }
                    }
                }
                await AssembleObjectAsync(upload, objectId, options, token, Progress);
                await faults.ObserveAsync("pointer.compare");
                ObjectPointer? current;
                lock (pointerSync)
                {
                    token.ThrowIfCancellationRequested();
                    CurrentOwner(upload, owner);
                    pointers.TryGetValue(staged.Identity.Digest.Hex, out current);
                    if (current is null || current.Removed)
                    {
                        if (current?.Version != observed?.Version) { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                        if (current is null && pointers.Count >= Bounds.CommittedIdentities
                            || pointers.Values.Count(pointer => !pointer.Removed) + retiredObjects.Count >= Bounds.CommittedIdentities)
                        { throw new ObjectOperationException(ArtifactFailureCode.Capacity); }
                        var version = checked((current?.Version ?? 0) + 1);
                        current = new(new ArtifactStamp(Identity, staged.Identity, Guid.NewGuid()), objectId, version,
                            upload.Ticket.Id, upload.Ticket.Expires);
                        upload.Deciding = true;
                        upload.Selected = current;
                        upload.Outcome = ArtifactMutationOutcome.Published;
                        upload.ReceiptId = Guid.NewGuid();
                        upload.Proof = Guid.NewGuid().ToString("N");
                        pointers[staged.Identity.Digest.Hex] = current;
                        listingRevision = checked(listingRevision + 1);
                        selected = true;
                    }
                }
                if (!selected)
                {
                    if (current.Corrupt) { throw new ObjectOperationException(ArtifactFailureCode.CorruptContent); }
                    if (current.Stamp.Identity != staged.Identity) { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                    if (!await VerifyObjectAsync(current, options, token, Progress))
                    {
                        lock (pointerSync)
                        {
                            if (pointers[staged.Identity.Digest.Hex] == current)
                            { pointers[staged.Identity.Digest.Hex] = current with { Corrupt = true }; }
                        }
                        throw new ObjectOperationException(ArtifactFailureCode.CorruptContent);
                    }
                    lock (pointerSync)
                    {
                        upload.Selected = current;
                        upload.Deciding = true;
                        upload.Outcome = ArtifactMutationOutcome.AlreadyPresentVerified;
                        upload.ReceiptId = Guid.NewGuid();
                        upload.Proof = Guid.NewGuid().ToString("N");
                    }
                }
                else { await faults.ObserveAsync("pointer.selected"); }
                await faults.ObserveAsync("object.direct");
                token.ThrowIfCancellationRequested();
                await using (var direct = new FileStream(ObjectPath(current.ObjectId), FileMode.Open, FileAccess.Read, FileShare.Read))
                {
                    if (direct.Length != current.Stamp.Identity.Length) { throw new ObjectOperationException(ArtifactFailureCode.CorruptContent); }
                }
                lock (pointerSync)
                {
                    if (pointers[staged.Identity.Digest.Hex] != current) { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                    return RecordObjectReceipt(upload);
                }

            }
            finally { if (!selected) { File.Delete(ObjectPath(objectId)); } }
        }, staged.Owner.Ticket, cancellationSettled: () =>
        {
            lock (pointerSync)
            {
                if (uploads.TryGetValue(staged.Owner.Ticket.Id, out var cancelled)
                    && cancelled.Ticket == staged.Owner.Ticket && !cancelled.Deciding && cancelled.Receipt is null
                    && !cancelled.Fenced && cancelled.Owner == owner
                    && (recognized || cancelled.Verified == staged && owner.SessionId == processSession
                        && EffectiveNow() < owner.Expires && EffectiveNow() < owner.Ticket.Expires))
                {
                    cancelled.Fenced = true;
                    RemoveMultipart(cancelled);
                }
            }
        });
    }

    private ArtifactMutationReceipt RecordObjectReceipt(ObjectOperation upload)
    {
        var stamp = upload.Selected!.Stamp;
        var proof = new ArtifactCommitEvidence(stamp, upload.Ticket.Id, upload.ReceiptId,
            upload.Proof, (ArtifactPublicationOutcome)upload.Outcome);
        upload.Receipt = new(upload.Ticket, upload.ReceiptId, upload.Outcome, stamp, ArtifactVisibility.Committed,
            ArtifactReclamation.NotApplicable, new ArtifactOption<ArtifactCommitEvidence>.Some(proof));
        RemoveMultipart(upload);
        return upload.Receipt;
    }

    private async Task AssembleObjectAsync(ObjectOperation upload, Guid objectId, ArtifactTransferOptions options, CancellationToken token,
        Func<ValueTask> progress)
    {
        await using var output = new FileStream(ObjectPath(objectId), FileMode.CreateNew, FileAccess.Write,
            FileShare.None, 1, FileOptions.Asynchronous | FileOptions.SequentialScan);
        var buffer = new byte[Bounds.CopyBufferBytes];
        using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        long length = 0;
        foreach (var part in upload.Parts)
        {
            await using var input = new FileStream(PartPath(part), FileMode.Open, FileAccess.Read,
                FileShare.Read, 1, FileOptions.Asynchronous | FileOptions.SequentialScan);
            while (true)
            {
                using var idle = CancellationTokenSource.CreateLinkedTokenSource(token);
                idle.CancelAfter(options.Inactivity);
                var count = await input.ReadAsync(buffer, idle.Token);
                if (count == 0) { break; }
                if (count > upload.Verified!.Identity.Length - length) { throw new ObjectOperationException(ArtifactFailureCode.CorruptContent); }
                await output.WriteAsync(buffer.AsMemory(0, count), token);
                hash.AppendData(buffer, 0, count);
                length = checked(length + count);
                await progress();
            }
        }
        if (length != upload.Verified!.Identity.Length
            || Convert.ToHexStringLower(hash.GetHashAndReset()) != upload.Verified.Identity.Digest.Hex)
        { throw new ObjectOperationException(ArtifactFailureCode.CorruptContent); }
        await output.FlushAsync(token);
    }

    private async Task<bool> VerifyObjectAsync(ObjectPointer pointer, ArtifactTransferOptions options, CancellationToken token,
        Func<ValueTask>? progress = null)
    {
        var path = ObjectPath(pointer.ObjectId);
        if (!File.Exists(path)) { return false; }
        await using var file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read,
            1, FileOptions.Asynchronous | FileOptions.SequentialScan);
        using var digest = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        var buffer = new byte[Bounds.CopyBufferBytes];
        long length = 0;
        while (true)
        {
            using var idle = CancellationTokenSource.CreateLinkedTokenSource(token);
            idle.CancelAfter(options.Inactivity);
            var count = await file.ReadAsync(buffer, idle.Token);
            if (count == 0) { break; }
            length = checked(length + count);
            if (length > pointer.Stamp.Identity.Length) { return false; }
            digest.AppendData(buffer, 0, count);
            if (progress is not null) { await progress(); }
        }
        return length == pointer.Stamp.Identity.Length
            && Convert.ToHexStringLower(digest.GetHashAndReset()) == pointer.Stamp.Identity.Digest.Hex;
    }
}
