using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

public sealed partial class ObjectArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(
        ArtifactWriteIntent intent, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(intent);
        ArgumentNullException.ThrowIfNull(options);
        return OwnedAsync(ArtifactPhase.Reserve, options.Deadline, ct, token =>
        {
            var expected = intent.Expectations;
            if (expected.Checksum is ArtifactOption<ArtifactChecksumExpectation>.Some checksum)
            {
                if (checksum.Value.Algorithm != "sha512") { throw new ObjectOperationException(ArtifactFailureCode.Unsupported); }
                if (checksum.Value.Digest.Length != 64) { throw new ObjectOperationException(ArtifactFailureCode.InvalidInput); }
            }
            lock (pointerSync)
            {
                token.ThrowIfCancellationRequested();
                if (expected.ByteCap > Bounds.ArtifactBytes) { throw new ObjectOperationException(ArtifactFailureCode.LimitExceeded); }
                ExpireHistory(token);
                if (uploads.Count >= Bounds.LiveTickets || expected.ByteCap > Bounds.StagingBytes - reservedBytes)
                { throw new ObjectOperationException(ArtifactFailureCode.Capacity); }
                var encoded = JsonSerializer.SerializeToUtf8Bytes(new
                {
                    expected.ByteCap,
                    Digest = expected.Sha256 is ArtifactOption<ArtifactDigest>.Some digest ? digest.Value.Hex : null,
                    Length = expected.ExactLength is ArtifactOption<long>.Some length ? (long?)length.Value : null,
                    Checksum = expected.Checksum is ArtifactOption<ArtifactChecksumExpectation>.Some extra
                        ? Convert.ToHexStringLower(extra.Value.Digest.AsSpan()) : null
                });
                var now = EffectiveNow();
                var ticket = new ArtifactOperationTicket(Identity, Guid.NewGuid(), ArtifactOperationKind.Write,
                    now, now.AddHours(24), Convert.ToHexStringLower(SHA256.HashData(encoded)));
                var upload = new ObjectOperation(ticket, expected);
                if (!uploads.TryAdd(ticket.Id, upload)) { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                IndexUpload(upload);
                reservedBytes = checked(reservedBytes + expected.ByteCap);
                listingRevision = checked(listingRevision + 1);
                return Task.FromResult(ticket);
            }
        }, undelivered: DiscardUndeliveredUploadAsync);
    }

    private ValueTask DiscardUndeliveredUploadAsync(ArtifactOperationTicket ticket)
    {
        lock (pointerSync)
        {
            if (!uploads.TryGetValue(ticket.Id, out var upload) || upload.Ticket != ticket
                || upload.Owner is not null || upload.Receipt is not null || upload.Deciding)
            { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
            RemoveMultipart(upload);
            ReleasePointerDependency(ticket.Id);
            uploads.TryRemove(ticket.Id, out _);
            indexedTargets.Remove(ticket.Id);
            listingRevision = checked(listingRevision + 1);
        }
        return ValueTask.CompletedTask;
    }

    private void ExpireHistory(CancellationToken token)
    {
        var now = EffectiveNow();
        var retire = uploads.Count >= Bounds.LiveTickets;
        var count = Math.Min(100, uploadCandidates.Count);
        for (var index = 0; index < count; index++)
        {
            var id = uploadCandidates.Dequeue();
            try
            {
                token.ThrowIfCancellationRequested();
                HistoryCandidate("tickets", id.ToString("N"));
                if (!uploads.TryGetValue(id, out var upload)) { continue; }
                if (now < upload.Ticket.Expires || upload.Deciding && upload.Receipt is null || TicketObserved(id))
                { continue; }
                upload.Fenced = true;
                RemoveMultipart(upload);
                ReleasePointerDependency(id);
                if (retire)
                {
                    uploads.TryRemove(id, out _);
                    indexedTargets.Remove(id);
                }
            }
            finally { if (uploads.ContainsKey(id)) { uploadCandidates.Enqueue(id); } }
        }
        count = Math.Min(100, pointerCandidates.Count);
        for (var index = 0; index < count; index++)
        {
            var digest = pointerCandidates.Dequeue();
            try
            {
                token.ThrowIfCancellationRequested();
                HistoryCandidate("decisions", digest);
                var pointer = pointers[digest];
                if (!pointer.Removed || now < pointer.HistoryUntil
                    || retiredObjects.ContainsKey(pointer.Stamp.Incarnation) || pointerDependents.ContainsKey(pointer.Stamp.Incarnation))
                { continue; }
                pointers.Remove(digest);
                listingRevision = checked(listingRevision + 1);
            }
            finally { if (pointers.ContainsKey(digest)) { pointerCandidates.Enqueue(digest); } }
        }
    }

    private void HistoryCandidate(string kind, string id) => faults.BeforeHistoryCandidate?.Invoke(kind, id);

    public ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
        ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ticket);
        ArgumentNullException.ThrowIfNull(source);
        ArgumentNullException.ThrowIfNull(options);
        return OwnedAsync(ArtifactPhase.Stage, options.Deadline, ct, async token =>
        {
            using var lease = await EnterTransferAsync(token);
            ObjectOperation upload;
            ArtifactStagingOwner owner;
            lock (pointerSync)
            {
                upload = Operation(ticket);
                if (!source.CanRead || ticket.Kind != ArtifactOperationKind.Write)
                { throw new ObjectOperationException(ArtifactFailureCode.InvalidInput); }
                if (upload.Owner is not null || upload.Receipt is not null || upload.Fenced || upload.Generation == long.MaxValue)
                { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                if (upload.ReservationReleased)
                {
                    if (upload.Expectations.ByteCap > Bounds.StagingBytes - reservedBytes)
                    { throw new ObjectOperationException(ArtifactFailureCode.Capacity); }
                    reservedBytes = checked(reservedBytes + upload.Expectations.ByteCap);
                    upload.ReservationReleased = false;
                }
                upload.Owner = owner = new(ticket, processSession, Guid.NewGuid(), ++upload.Generation,
                    EffectiveNow().Add(initializedWith!.Ownership.Ttl));
                upload.Writing = true;
                listingRevision = checked(listingRevision + 1);
            }
            FileStream? part = null;
            try
            {
                using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
                using var additional = upload.Expectations.Checksum is ArtifactOption<ArtifactChecksumExpectation>.Some
                    ? IncrementalHash.CreateHash(HashAlgorithmName.SHA512) : null;
                var buffer = new byte[Bounds.CopyBufferBytes];
                long length = 0;
                var partLength = 0;
                var renewed = time.GetTimestamp();
                while (true)
                {
                    using var idle = CancellationTokenSource.CreateLinkedTokenSource(token);
                    idle.CancelAfter(options.Inactivity);
                    var count = await source.ReadAsync(buffer, idle.Token);
                    token.ThrowIfCancellationRequested();
                    lock (pointerSync)
                    {
                        CurrentOwner(upload, owner);
                        if (count > upload.Expectations.ByteCap - length)
                        { throw new ObjectOperationException(ArtifactFailureCode.LimitExceeded); }
                        if (time.GetElapsedTime(renewed) >= initializedWith!.Ownership.Renewal)
                        {
                            upload.Owner = owner = new(ticket, processSession, owner.OwnerId, owner.Generation,
                                EffectiveNow().Add(initializedWith.Ownership.Ttl));
                            renewed = time.GetTimestamp();
                        }
                    }
                    if (count == 0) { break; }
                    if (part is null)
                    {
                        var partId = Guid.NewGuid();
                        lock (pointerSync) { upload.Parts.Add(partId); }
                        part = new FileStream(PartPath(partId), FileMode.CreateNew, FileAccess.Write,
                            FileShare.None, 1, FileOptions.Asynchronous | FileOptions.SequentialScan);
                        partLength = 0;
                    }
                    await part.WriteAsync(buffer.AsMemory(0, count), token);
                    hash.AppendData(buffer, 0, count);
                    additional?.AppendData(buffer, 0, count);
                    length = checked(length + count);
                    partLength = checked(partLength + count);
                    if (length == count) { await faults.ObserveAsync("multipart.part"); }
                    if (partLength >= 8 * 1024 * 1024)
                    {
                        await part.FlushAsync(token);
                        await part.DisposeAsync();
                        part = null;
                    }
                }
                if (part is not null) { await part.FlushAsync(token); await part.DisposeAsync(); part = null; }
                var digest = new ArtifactDigest(Convert.ToHexStringLower(hash.GetHashAndReset()));
                if (upload.Expectations.Sha256 is ArtifactOption<ArtifactDigest>.Some sha && sha.Value != digest
                    || upload.Expectations.ExactLength is ArtifactOption<long>.Some exact && exact.Value != length
                    || upload.Expectations.Checksum is ArtifactOption<ArtifactChecksumExpectation>.Some checksum
                        && !additional!.GetHashAndReset().AsSpan().SequenceEqual(checksum.Value.Digest.AsSpan()))
                { throw new ObjectOperationException(ArtifactFailureCode.CorruptContent); }
                lock (pointerSync)
                {
                    token.ThrowIfCancellationRequested();
                    CurrentOwner(upload, owner);
                    upload.Owner = new(ticket, processSession, owner.OwnerId, owner.Generation,
                        EffectiveNow().Add(initializedWith!.Ownership.Ttl));
                    upload.Verified = new(upload.Owner, new ArtifactIdentity(digest, length), Guid.NewGuid(), Guid.NewGuid().ToString("N"));
                    upload.Writing = false;
                    listingRevision = checked(listingRevision + 1);
                }
                await faults.ObserveAsync("multipart.complete");
                token.ThrowIfCancellationRequested();
                return upload.Verified;
            }
            catch
            {
                if (part is not null) { await part.DisposeAsync(); }
                lock (pointerSync) { upload.Fenced = true; upload.Writing = false; RemoveMultipart(upload); }
                throw;
            }
        }, ticket, undelivered: staged =>
        {
            lock (pointerSync)
            {
                if (!uploads.TryGetValue(staged.Owner.Ticket.Id, out var upload)
                    || upload.Ticket != staged.Owner.Ticket || upload.Owner != staged.Owner
                    || staged.Owner.SessionId != processSession || upload.Verified != staged
                    || upload.Receipt is not null || upload.Deciding)
                { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                upload.Fenced = true;
                upload.Writing = false;
                RemoveMultipart(upload);
            }
            return ValueTask.CompletedTask;
        });
    }

    private void RemoveMultipart(ObjectOperation upload)
    {
        try
        {
            foreach (var piece in upload.Parts) { File.Delete(PartPath(piece)); }
            upload.Parts.Clear();
            listingRevision = checked(listingRevision + 1);
            if (!upload.ReservationReleased)
            {
                reservedBytes = checked(reservedBytes - upload.Expectations.ByteCap);
                upload.ReservationReleased = true;
            }
            failedMultipartCleanup.TryRemove(upload.Ticket.Id, out _);
        }
        catch { failedMultipartCleanup.TryAdd(upload.Ticket.Id, 0); throw; }
    }

    private Task? multipartCleanupRetry;
    private Task RetryMultipartCleanupAsync()
    {
        lock (workSync)
        {
            if (multipartCleanupRetry is { IsCompleted: false }) { return multipartCleanupRetry; }
            return multipartCleanupRetry = Task.Run(() =>
            {
                lock (pointerSync)
                {
                    foreach (var id in failedMultipartCleanup.Keys.Take(100)) { RemoveMultipart(uploads[id]); }
                    if (!failedMultipartCleanup.IsEmpty) { throw new ObjectOperationException(ArtifactFailureCode.CleanupIncomplete); }
                }
            });
        }
    }

    public ValueTask<ArtifactResult<ArtifactStagingOwner>> RenewAsync(
        ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(owner);
        ArgumentNullException.ThrowIfNull(options);
        return OwnedAsync(ArtifactPhase.Maintenance, options.Deadline, ct, token =>
        {
            lock (pointerSync)
            {
                var upload = Operation(owner.Ticket);
                CurrentOwner(upload, owner);
                if (upload.Verified is null || upload.Writing) { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                token.ThrowIfCancellationRequested();
                upload.Owner = new(owner.Ticket, processSession, owner.OwnerId, owner.Generation,
                    EffectiveNow().Add(initializedWith!.Ownership.Ttl));
                upload.Verified = new(upload.Owner, upload.Verified.Identity, upload.Verified.VerifiedCompletion, upload.Verified.PrivateHandle);
                return Task.FromResult(upload.Owner);
            }
        }, owner.Ticket);
    }
}
