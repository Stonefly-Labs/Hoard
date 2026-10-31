using Hoard.Abstractions.Storage;
using System.Security.Cryptography;
using System.Text;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore
{
    private const int MaximumQualificationPayloadBytes = 65536;
    private readonly SemaphoreSlim qualificationPayload = new(1, 1);

    public ArtifactResult<(KeyValuePair<string, long>[] Staging, KeyValuePair<string, long>[] Payloads)> ObserveStorageForQualification()
    {
        try
        {
            return new ArtifactResult<(KeyValuePair<string, long>[], KeyValuePair<string, long>[])>.Success(
                (ObserveQualificationFiles("staging"), ObserveQualificationFiles("data")));
        }
        catch (Exception error)
        {
            return Failed<(KeyValuePair<string, long>[], KeyValuePair<string, long>[])>(
                FailureCode(error, CancellationToken.None), ArtifactPhase.Maintenance);
        }
    }

    private KeyValuePair<string, long>[] ObserveQualificationFiles(string child)
    {
        var directory = new DirectoryInfo(Path.Combine(Path.GetFullPath(configuredRoot), child));
        if (directory.LinkTarget is not null) { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
        var files = directory.EnumerateFileSystemInfos().Take(1025).ToArray();
        if (files.Length > 1024) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
        return files.Select(file =>
        {
            if (file.LinkTarget is not null || file is not FileInfo regular)
            { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
            return new KeyValuePair<string, long>(
                Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(file.Name))), regular.Length);
        }).OrderBy(file => file.Key, StringComparer.Ordinal).ToArray();
    }

    public async ValueTask<ArtifactResult<IAsyncDisposable>> RestrictStorageCleanupForQualificationAsync(
        bool payloads, Action<IAsyncDisposable> ownScope, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(ownScope);
        await qualificationPayload.WaitAsync(cancellationToken);
        try
        {
            var access = QualificationPayloadAccess.RestrictDirectoryWrites(
                Path.Combine(Path.GetFullPath(configuredRoot), payloads ? "data" : "staging"));
            try { ownScope(access); return new ArtifactResult<IAsyncDisposable>.Success(access); }
            catch { await access.DisposeAsync(); throw; }
        }
        finally { qualificationPayload.Release(); }
    }

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

    public ValueTask<ArtifactResult<IAsyncDisposable>> RestrictPayloadAccessForQualificationAsync(
        ArtifactStamp stamp, bool unavailable, Action<IAsyncDisposable> ownScope, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(stamp);
        ArgumentNullException.ThrowIfNull(ownScope);
        return ExecuteAsync(ArtifactPhase.Maintenance, TimeSpan.FromSeconds(5), cancellationToken,
            token => WithQualificationPayloadAsync<IAsyncDisposable>(stamp, token, async (path, protection) =>
            {
                var access = QualificationPayloadAccess.Create(path, unavailable, protection);
                try { ownScope(access); return access; }
                catch { await access.DisposeAsync(); throw; }
            }, transferProtection: true),
            undelivered: access => access.DisposeAsync());
    }

    public ValueTask<ArtifactResult<IAsyncDisposable>> RestrictRecordWritesForQualificationAsync(
        Action<IAsyncDisposable> ownScope, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(ownScope);
        return ExecuteAsync<IAsyncDisposable>(ArtifactPhase.Maintenance, TimeSpan.FromSeconds(5), cancellationToken,
            async token =>
            {
                await qualificationPayload.WaitAsync(token);
                try
                {
                    var directory = Path.GetDirectoryName(ownership!.RecordPath("decisions", "qualification"))
                        ?? throw new InvalidOperationException("BindingInvalid");
                    var access = QualificationPayloadAccess.RestrictDirectoryWrites(directory);
                    try { ownScope(access); return access; }
                    catch { await access.DisposeAsync(); throw; }
                }
                finally { qualificationPayload.Release(); }
            }, undelivered: access => access.DisposeAsync());
    }

    private sealed class QualificationPayloadAccess(
        string path, string directory, bool unavailable, UnixFileMode originalMode,
        IArtifactProtectionGuard? protection) : IAsyncDisposable
    {
        private readonly SemaphoreSlim gate = new(1, 1);
        private bool restored;
        private bool released;
        public static QualificationPayloadAccess RestrictDirectoryWrites(string directory)
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix permission proof required."); }
            var mode = File.GetUnixFileMode(directory);
            var access = new QualificationPayloadAccess(directory, directory, false, mode, null);
            File.SetUnixFileMode(directory, mode & ~(UnixFileMode.UserWrite | UnixFileMode.GroupWrite | UnixFileMode.OtherWrite));
            return access;
        }
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
                if (protection is not null) { await protection.DisposeAsync(); }
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
            var admission = await configuration!.Authority.AcquireAsync(new(Guid.NewGuid(),
                ArtifactProtectionOperation.Read, StoreIdentity, stamp.Identity.Digest,
                new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), cancellationToken);
            if (admission is not ArtifactResult<IArtifactProtectionGuard>.Success accepted)
            {
                throw new LocalStateException(admission is ArtifactResult<IArtifactProtectionGuard>.Failure failure
                    ? failure.Code : ArtifactFailureCode.InternalFailure);
            }
            var protection = accepted.Value;
            var transferred = false;
            try
            {
                LocalContent content;
                lock (stateSync)
                {
                    if (!decisions.TryGetValue(stamp.Identity.Digest.Hex, out var decision)
                        || decision.Removed || decision.Content.Stamp(StoreIdentity) != stamp)
                    { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                    content = decision.Content;
                }
                await faults.ObserveAsync("qualification.payload-selected");
                var result = await action(PayloadPath(content), protection);
                transferred = transferProtection;
                return result;
            }
            finally { if (!transferred) { await protection.DisposeAsync(); } }
        }
        finally { qualificationPayload.Release(); }
    }
}
