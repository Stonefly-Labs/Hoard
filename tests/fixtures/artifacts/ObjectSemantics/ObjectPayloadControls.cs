using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

public sealed partial class ObjectArtifactStore
{
    private const int MaximumQualificationPayloadBytes = 65536;
    private readonly SemaphoreSlim qualificationPayload = new(1, 1);

    public ValueTask<ArtifactResult<byte[]>> CapturePayloadForQualificationAsync(
        ArtifactStamp stamp, int maximumBytes, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(stamp);
        if (maximumBytes is < 0 or > MaximumQualificationPayloadBytes)
        { return ValueTask.FromResult(Rejected<byte[]>(ArtifactFailureCode.InvalidInput, ArtifactPhase.Maintenance)); }
        return OwnedAsync(ArtifactPhase.Maintenance, TimeSpan.FromSeconds(5), cancellationToken,
            token => WithQualificationPayloadAsync(stamp, token, async path =>
            {
                await using var file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read,
                    4096, FileOptions.Asynchronous);
                if (file.Length > maximumBytes) { throw new ObjectOperationException(ArtifactFailureCode.Capacity); }
                var bytes = new byte[(int)file.Length];
                await file.ReadExactlyAsync(bytes, token);
                if (await file.ReadAsync(new byte[1], token) != 0)
                { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                return bytes;
            }));
    }

    public ValueTask<ArtifactResult<long>> ReplacePayloadForQualificationAsync(
        ArtifactStamp stamp, ReadOnlyMemory<byte> payload, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(stamp);
        if (payload.Length > MaximumQualificationPayloadBytes)
        { return ValueTask.FromResult(Rejected<long>(ArtifactFailureCode.InvalidInput, ArtifactPhase.Maintenance)); }
        var snapshot = payload.ToArray();
        return OwnedAsync(ArtifactPhase.Maintenance, TimeSpan.FromSeconds(5), cancellationToken,
            token => WithQualificationPayloadAsync(stamp, token, async path =>
            {
                await using var file = new FileStream(path, FileMode.OpenOrCreate, FileAccess.Write, FileShare.Read,
                    4096, FileOptions.Asynchronous);
                file.SetLength(0);
                await file.WriteAsync(snapshot, token);
                await file.FlushAsync(token);
                return (long)snapshot.Length;
            }));
    }

    public ValueTask<ArtifactResult<long>> RemovePayloadForQualificationAsync(
        ArtifactStamp stamp, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(stamp);
        return OwnedAsync(ArtifactPhase.Maintenance, TimeSpan.FromSeconds(5), cancellationToken,
            token => WithQualificationPayloadAsync(stamp, token, async path =>
            {
                await using var file = new FileStream(path, FileMode.Open, FileAccess.Read,
                    FileShare.ReadWrite | FileShare.Delete, 1, FileOptions.Asynchronous);
                var length = file.Length;
                token.ThrowIfCancellationRequested();
                File.Delete(path);
                return length;
            }));
    }

    private async Task<T> WithQualificationPayloadAsync<T>(
        ArtifactStamp stamp, CancellationToken cancellationToken, Func<string, Task<T>> action)
    {
        await qualificationPayload.WaitAsync(cancellationToken);
        try
        {
            var admission = await initializedWith!.Authority.AcquireAsync(new(Guid.NewGuid(),
                ArtifactProtectionOperation.Read, Identity, stamp.Identity.Digest,
                new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), cancellationToken);
            if (admission is not ArtifactResult<IArtifactProtectionGuard>.Success accepted)
            {
                throw new ObjectOperationException(admission is ArtifactResult<IArtifactProtectionGuard>.Failure failure
                    ? failure.Code : ArtifactFailureCode.InternalFailure);
            }
            await using var protection = accepted.Value;
            ObjectPointer pointer;
            lock (pointerSync)
            {
                if (!pointers.TryGetValue(stamp.Identity.Digest.Hex, out var selected)
                    || selected.Removed || selected.Stamp != stamp)
                { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                pointer = selected;
            }
            await faults.ObserveAsync("object.qualification-payload-selected");
            return await action(ObjectPath(pointer.ObjectId));
        }
        finally { qualificationPayload.Release(); }
    }
}
