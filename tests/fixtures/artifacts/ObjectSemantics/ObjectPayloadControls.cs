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

    public ValueTask<ArtifactResult<IAsyncDisposable>> RestrictPayloadAccessForQualificationAsync(
        ArtifactStamp stamp, bool unavailable, Action<IAsyncDisposable> ownScope, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(stamp);
        ArgumentNullException.ThrowIfNull(ownScope);
        return OwnedAsync(ArtifactPhase.Maintenance, TimeSpan.FromSeconds(5), cancellationToken,
            token => WithQualificationPayloadAsync<IAsyncDisposable>(stamp, token, async (path, protection) =>
            {
                var access = QualificationPayloadAccess.Create(path, unavailable, protection);
                try { ownScope(access); return access; }
                catch { await access.DisposeAsync(); throw; }
            }, transferProtection: true),
            undelivered: access => access.DisposeAsync());
    }

    private sealed class QualificationPayloadAccess(
        string path, string directory, bool unavailable, UnixFileMode originalMode,
        IArtifactProtectionGuard protection) : IAsyncDisposable
    {
        private readonly SemaphoreSlim gate = new(1, 1);
        private bool restored;
        private bool released;
        public static QualificationPayloadAccess Create(
            string path, bool unavailable, IArtifactProtectionGuard protection)
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix permission proof required."); }
            var directory = Path.GetDirectoryName(path) ?? throw new InvalidOperationException("BindingInvalid");
            var access = new QualificationPayloadAccess(path, directory, unavailable,
                unavailable ? default : File.GetUnixFileMode(path), protection);
            if (unavailable) { Directory.Move(directory, directory + "-qualification-offline"); }
            else { File.SetUnixFileMode(path, UnixFileMode.UserWrite); }
            return access;
        }
        public async ValueTask DisposeAsync()
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix permission proof required."); }
            await gate.WaitAsync();
            try
            {
                if (released) { return; }
                if (!restored)
                {
                    if (unavailable) { Directory.Move(directory + "-qualification-offline", directory); }
                    else { File.SetUnixFileMode(path, originalMode); }
                    restored = true;
                }
                await protection.DisposeAsync();
                released = true;
            }
            finally { gate.Release(); }
        }
    }

    private Task<T> WithQualificationPayloadAsync<T>(
        ArtifactStamp stamp, CancellationToken cancellationToken, Func<string, Task<T>> action) =>
        WithQualificationPayloadAsync(stamp, cancellationToken, (path, _) => action(path), transferProtection: false);

    private async Task<T> WithQualificationPayloadAsync<T>(
        ArtifactStamp stamp, CancellationToken cancellationToken,
        Func<string, IArtifactProtectionGuard, Task<T>> action, bool transferProtection)
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
            var protection = accepted.Value;
            var transferred = false;
            try
            {
                ObjectPointer pointer;
                lock (pointerSync)
                {
                    if (!pointers.TryGetValue(stamp.Identity.Digest.Hex, out var selected)
                        || selected.Removed || selected.Stamp != stamp)
                    { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                    pointer = selected;
                }
                await faults.ObserveAsync("object.qualification-payload-selected");
                var result = await action(ObjectPath(pointer.ObjectId), protection);
                transferred = transferProtection;
                return result;
            }
            finally { if (!transferred) { await protection.DisposeAsync(); } }
        }
        finally { qualificationPayload.Release(); }
    }
}
