using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore
{
    private const int MaximumQualificationPayloadBytes = 65536;
    private readonly SemaphoreSlim qualificationPayload = new(1, 1);

    public ValueTask<ArtifactResult<byte[]>> CapturePayloadForQualificationAsync(
        ArtifactStamp stamp, int maximumBytes, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(stamp);
        if (maximumBytes is < 0 or > MaximumQualificationPayloadBytes)
        { return ValueTask.FromResult(Failed<byte[]>(ArtifactFailureCode.InvalidInput, ArtifactPhase.Maintenance)); }
        return ExecuteAsync(ArtifactPhase.Maintenance, TimeSpan.FromSeconds(5), cancellationToken,
            token => WithQualificationPayloadAsync(stamp, token, async path =>
            {
                await using var file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read,
                    4096, FileOptions.Asynchronous);
                if (file.Length > maximumBytes) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
                var bytes = new byte[(int)file.Length];
                await file.ReadExactlyAsync(bytes, token);
                if (await file.ReadAsync(new byte[1], token) != 0)
                { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                return bytes;
            }));
    }

    public ValueTask<ArtifactResult<long>> ReplacePayloadForQualificationAsync(
        ArtifactStamp stamp, ReadOnlyMemory<byte> payload, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(stamp);
        if (payload.Length > MaximumQualificationPayloadBytes)
        { return ValueTask.FromResult(Failed<long>(ArtifactFailureCode.InvalidInput, ArtifactPhase.Maintenance)); }
        var snapshot = payload.ToArray();
        return ExecuteAsync(ArtifactPhase.Maintenance, TimeSpan.FromSeconds(5), cancellationToken,
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
        return ExecuteAsync(ArtifactPhase.Maintenance, TimeSpan.FromSeconds(5), cancellationToken,
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
            var admission = await configuration!.Authority.AcquireAsync(new(Guid.NewGuid(),
                ArtifactProtectionOperation.Read, StoreIdentity, stamp.Identity.Digest,
                new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), cancellationToken);
            if (admission is not ArtifactResult<IArtifactProtectionGuard>.Success accepted)
            {
                throw new LocalStateException(admission is ArtifactResult<IArtifactProtectionGuard>.Failure failure
                    ? failure.Code : ArtifactFailureCode.InternalFailure);
            }
            await using var protection = accepted.Value;
            LocalContent content;
            lock (stateSync)
            {
                if (!decisions.TryGetValue(stamp.Identity.Digest.Hex, out var decision)
                    || decision.Removed || decision.Content.Stamp(StoreIdentity) != stamp)
                { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                content = decision.Content;
            }
            await faults.ObserveAsync("qualification.payload-selected");
            return await action(PayloadPath(content));
        }
        finally { qualificationPayload.Release(); }
    }
}
