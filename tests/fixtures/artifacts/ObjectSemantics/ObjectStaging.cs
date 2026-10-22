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
                var effectiveNow = EffectiveNow();
                foreach (var expired in uploads.Values.Where(value => value.Ticket.Kind == ArtifactOperationKind.Write
                    && value.Owner is null && !value.ReservationReleased && effectiveNow >= value.Ticket.Expires).Take(100))
                {
                    if (MutationActive(expired.Ticket.Id)) { continue; }
                    expired.Fenced = true;
                    RemoveMultipart(expired);
                }
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
                if (!uploads.TryAdd(ticket.Id, new(ticket, expected))) { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                reservedBytes = checked(reservedBytes + expected.ByteCap);
                listingRevision = checked(listingRevision + 1);
                return Task.FromResult(ticket);
            }
        });
    }

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
        }, ticket);
    }

    private void RemoveMultipart(ObjectOperation upload)
    {
        foreach (var piece in upload.Parts) { File.Delete(PartPath(piece)); }
        upload.Parts.Clear();
        listingRevision = checked(listingRevision + 1);
        if (!upload.ReservationReleased)
        {
            reservedBytes = checked(reservedBytes - upload.Expectations.ByteCap);
            upload.ReservationReleased = true;
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
