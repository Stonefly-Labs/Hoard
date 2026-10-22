using System.Security.Cryptography;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore
{
    public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(
        ArtifactWriteIntent intent, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(intent);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Reserve, options.Deadline, ct, token =>
        {
            var expectation = intent.Expectations;
            if (expectation.Checksum is ArtifactOption<ArtifactChecksumExpectation>.Some checksum)
            {
                if (checksum.Value.Algorithm != "sha512") { throw new LocalStateException(ArtifactFailureCode.Unsupported); }
                if (checksum.Value.Digest.Length != 64) { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
            }
            lock (stateSync)
            {
                token.ThrowIfCancellationRequested();
                if (expectation.ByteCap > Limits.ArtifactBytes) { throw new LocalStateException(ArtifactFailureCode.LimitExceeded); }
                var now = Now();
                foreach (var expired in operations.Values.Where(value => value.Kind == ArtifactOperationKind.Write
                    && value.Owner == Guid.Empty && !value.ReservationReleased && now >= value.Expires).Take(100))
                {
                    if (IsBusy(expired.Id)) { continue; }
                    expired.State = "notcommitted";
                    Save(expired);
                    ReleaseStaging(expired);
                }
                if (operations.Count >= Limits.LiveTickets || expectation.ByteCap > Limits.StagingBytes - reserved)
                { throw new LocalStateException(ArtifactFailureCode.Capacity); }
                var issued = Now();
                var operation = new LocalOperation
                {
                    Id = Guid.NewGuid(),
                    Issued = issued,
                    Expires = issued.AddHours(24),
                    Cap = expectation.ByteCap,
                    Kind = ArtifactOperationKind.Write,
                    ExpectedDigest = expectation.Sha256 is ArtifactOption<ArtifactDigest>.Some hash ? hash.Value.Hex : null,
                    ExpectedLength = expectation.ExactLength is ArtifactOption<long>.Some length ? length.Value : null,
                    ExpectedChecksum = expectation.Checksum is ArtifactOption<ArtifactChecksumExpectation>.Some additional
                        ? Convert.ToHexStringLower(additional.Value.Digest.AsSpan()) : null
                };
                operation.Fingerprint = Fingerprint(new { operation.Cap, operation.ExpectedDigest, operation.ExpectedLength, operation.ExpectedChecksum });
                Save(operation);
                if (!operations.TryAdd(operation.Id, operation)) { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                reserved = checked(reserved + operation.Cap);
                return Task.FromResult(Ticket(operation));
            }
        });
    }

    public ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
        ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ticket);
        ArgumentNullException.ThrowIfNull(source);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Stage, options.Deadline, ct, async token =>
        {
            using var slot = await AdmitAsync(token);
            LocalOperation operation;
            ArtifactStagingOwner owner;
            lock (stateSync)
            {
                operation = Find(ticket, ArtifactOperationKind.Write);
                if (!source.CanRead) { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
                if (operation.State != "reserved" || operation.Generation == long.MaxValue)
                { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                if (operation.ReservationReleased)
                {
                    if (operation.Cap > Limits.StagingBytes - reserved) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
                    reserved = checked(reserved + operation.Cap);
                    operation.ReservationReleased = false;
                }
                if (operation.Owner != Guid.Empty) { File.Delete(StagePath(operation)); }
                operation.Session = ownership!.State.SessionId;
                operation.Owner = Guid.NewGuid();
                operation.Generation++;
                operation.OwnerExpires = Now().Add(configuration!.Ownership.Ttl);
                operation.State = "staging";
                Save(operation);
                owner = Owner(operation);
            }
            try
            {
                await using var output = new FileStream(StagePath(operation), FileMode.CreateNew, FileAccess.Write,
                    FileShare.None, 1, FileOptions.Asynchronous | FileOptions.SequentialScan);
                using var sha256 = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
                using var sha512 = operation.ExpectedChecksum is null ? null : IncrementalHash.CreateHash(HashAlgorithmName.SHA512);
                var buffer = new byte[Limits.CopyBufferBytes];
                long length = 0;
                var renewal = time.GetTimestamp();
                while (true)
                {
                    using var inactivity = CancellationTokenSource.CreateLinkedTokenSource(token);
                    inactivity.CancelAfter(options.Inactivity);
                    var count = await source.ReadAsync(buffer, inactivity.Token);
                    token.ThrowIfCancellationRequested();
                    lock (stateSync)
                    {
                        CheckOwner(operation, owner);
                        if (count > operation.Cap - length) { throw new LocalStateException(ArtifactFailureCode.LimitExceeded); }
                        if (time.GetElapsedTime(renewal) >= configuration!.Ownership.Renewal)
                        {
                            operation.OwnerExpires = Now().Add(configuration.Ownership.Ttl);
                            owner = Owner(operation);
                            Save(operation);
                            renewal = time.GetTimestamp();
                        }
                    }
                    if (count == 0) { break; }
                    await output.WriteAsync(buffer.AsMemory(0, count), token);
                    sha256.AppendData(buffer, 0, count);
                    sha512?.AppendData(buffer, 0, count);
                    length = checked(length + count);
                    if (length == count) { await faults.ObserveAsync("stage.prefix"); }
                }
                var digest = Convert.ToHexStringLower(sha256.GetHashAndReset());
                if (operation.ExpectedDigest is { } expected && digest != expected
                    || operation.ExpectedLength is { } exact && length != exact
                    || operation.ExpectedChecksum is { } extra && Convert.ToHexStringLower(sha512!.GetHashAndReset()) != extra)
                { throw new LocalStateException(ArtifactFailureCode.CorruptContent); }
                await output.FlushAsync(token);
                output.Flush(flushToDisk: true);
                lock (stateSync)
                {
                    token.ThrowIfCancellationRequested();
                    CheckOwner(operation, owner);
                    operation.Content = new(digest, length, Guid.NewGuid());
                    operation.Verified = Guid.NewGuid();
                    operation.OwnerExpires = Now().Add(configuration!.Ownership.Ttl);
                    operation.State = "verified";
                    Save(operation);
                }
                await faults.ObserveAsync("stage.verified");
                token.ThrowIfCancellationRequested();
                lock (stateSync) { return Staged(operation); }
            }
            catch
            {
                lock (stateSync)
                {
                    operation.State = "notcommitted";
                    Save(operation);
                    ReleaseStaging(operation);
                }
                throw;
            }
        }, ticket);
    }

    private void ReleaseStaging(LocalOperation operation)
    {
        if (operation.Owner != Guid.Empty) { File.Delete(StagePath(operation)); }
        if (!operation.ReservationReleased)
        {
            reserved = checked(reserved - operation.Cap);
            operation.ReservationReleased = true;
            Save(operation);
        }
    }

    public ValueTask<ArtifactResult<ArtifactStagingOwner>> RenewAsync(
        ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(owner);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync(ArtifactPhase.Maintenance, options.Deadline, ct, token =>
        {
            lock (stateSync)
            {
                var operation = Find(owner.Ticket, ArtifactOperationKind.Write);
                CheckOwner(operation, owner, requireVerified: true);
                token.ThrowIfCancellationRequested();
                operation.OwnerExpires = Now().Add(configuration!.Ownership.Ttl);
                Save(operation);
                return Task.FromResult(Owner(operation));
            }
        }, owner.Ticket);
    }
}
