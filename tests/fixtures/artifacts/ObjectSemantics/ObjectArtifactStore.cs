using Hoard.Abstractions.Storage;
using System.Security.Cryptography;
using System.Text.Json;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

public sealed partial class ObjectArtifactStore(string root, TimeProvider? clock = null, ObjectFaultControls? controls = null)
    : IArtifactStoreLifetime
{
    private readonly string configuredRoot = root;
    private readonly TimeProvider time = clock ?? TimeProvider.System;
    private readonly ObjectFaultControls faults = controls ?? new();
    private bool initialized;
    private int lifetimeBusy;
    private FileStream? rootLock;
    public bool Ready => initialized && Capabilities.MeetsBaseline;
    public ArtifactCapabilities Capabilities { get; private set; } = new(
        1, ArtifactDurability.SimulationOnly, ArtifactEnumerationConsistency.Incomplete, new ArtifactLimits(),
        conditionalPublication: false, conditionalDeletion: false, stagingRecovery: false,
        ownerFencing: false, readerProtection: false, boundedStreaming: false);

    public async ValueTask<ArtifactResult<ArtifactAdmission>> InitializeAsync(
        ArtifactInitialization request, ArtifactMaintenanceOptions options, CancellationToken ct)
    {
        if (Interlocked.CompareExchange(ref lifetimeBusy, 1, 0) != 0) { return Failure(ArtifactFailureCode.Conflict); }
        try { return await InitializeCoreAsync(request, options, ct); }
        finally { Volatile.Write(ref lifetimeBusy, 0); }
    }

    private async ValueTask<ArtifactResult<ArtifactAdmission>> InitializeCoreAsync(
        ArtifactInitialization request, ArtifactMaintenanceOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(options);
        if (initialized) { return Failure(ArtifactFailureCode.Conflict); }
        if (ct.IsCancellationRequested) { return Failure(ArtifactFailureCode.CancelledBeforeCommit); }
        if (request.Mode != ArtifactInitializationMode.CreateEmpty)
        { return Failure(ArtifactFailureCode.IncompatibleStore); }
        if (OperatingSystem.IsWindows()) { return Failure(ArtifactFailureCode.Unsupported); }
        var probe = await request.Authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
            request.Store, new Hoard.Abstractions.Metadata.ArtifactDigest(new string('0', 64))), new(), ct);
        if (probe is not ArtifactResult<IArtifactProtectionGuard>.Success recognized)
        { return Failure(ArtifactFailureCode.Denied); }
        await recognized.Value.DisposeAsync();
        try
        {
            await faults.ObserveAsync("object.initialize");
            var path = Path.GetFullPath(configuredRoot);
            for (var entry = new DirectoryInfo(path); entry is not null; entry = entry.Parent)
            {
                if (entry.LinkTarget is not null || entry.Exists && (entry.Attributes & FileAttributes.ReparsePoint) != 0)
                { return Failure(ArtifactFailureCode.InvalidInput); }
                if (entry.Exists && (File.GetUnixFileMode(entry.FullName) & (UnixFileMode.OtherWrite | UnixFileMode.GroupWrite)) != 0)
                { return Failure(ArtifactFailureCode.AccessDenied); }
            }
            if (!Directory.Exists(Path.GetDirectoryName(path))) { return Failure(ArtifactFailureCode.InvalidInput); }
            Directory.CreateDirectory(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            if ((File.GetUnixFileMode(path) & (UnixFileMode.GroupRead | UnixFileMode.GroupWrite | UnixFileMode.GroupExecute
                | UnixFileMode.OtherRead | UnixFileMode.OtherWrite | UnixFileMode.OtherExecute)) != 0)
            { return Failure(ArtifactFailureCode.AccessDenied); }
            var ownerPath = Path.Combine(path, ".object-owner");
            var ownerEntry = new FileInfo(ownerPath);
            if (ownerEntry.LinkTarget is not null || ownerEntry.Exists && (ownerEntry.Attributes & FileAttributes.ReparsePoint) != 0)
            { return Failure(ArtifactFailureCode.InvalidInput); }
            rootLock = new FileStream(ownerPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
            if (Directory.EnumerateFileSystemEntries(path).Any(entry => Path.GetFileName(entry) != ".object-owner"))
            {
                rootLock.Dispose();
                rootLock = null;
                return Failure(ArtifactFailureCode.IncompatibleStore);
            }
            var state = new ObjectState(1, request.Store.ProviderModuleId, request.Store.InstanceId,
                request.Store.Epoch, Guid.NewGuid(), time.GetUtcNow(), request.Limits);
            var encoded = JsonSerializer.SerializeToUtf8Bytes(state);
            using (var manifest = new FileStream(Path.Combine(path, "object-manifest.json"), FileMode.CreateNew,
                FileAccess.Write, FileShare.None))
            {
                var checksum = SHA256.HashData(encoded);
                manifest.Write(checksum);
                manifest.Write(encoded);
                manifest.Flush();
            }
            Directory.CreateDirectory(Path.Combine(path, "multipart"), UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            Directory.CreateDirectory(Path.Combine(path, "objects"), UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            Capabilities = new(1, ArtifactDurability.SimulationOnly, ArtifactEnumerationConsistency.Incomplete, request.Limits,
                conditionalPublication: false, conditionalDeletion: false, stagingRecovery: false,
                ownerFencing: false, readerProtection: false, boundedStreaming: false);
            initialized = true;
            await faults.ObserveAsync("object.admitted");
            return new ArtifactResult<ArtifactAdmission>.Success(new(request.Store, Capabilities));
        }
        catch (UnauthorizedAccessException) { return FailedInitialization(ArtifactFailureCode.AccessDenied); }
        catch (IOException) { return FailedInitialization(ArtifactFailureCode.Unavailable); }
        catch (ArgumentException) { return FailedInitialization(ArtifactFailureCode.InvalidInput); }
        catch (Exception) { return FailedInitialization(ArtifactFailureCode.InternalFailure); }
    }

    private ArtifactResult<ArtifactAdmission> FailedInitialization(ArtifactFailureCode code)
    {
        initialized = false;
        rootLock?.Dispose();
        rootLock = null;
        return Failure(code);
    }
    private static ArtifactResult<ArtifactAdmission> Failure(ArtifactFailureCode code)
        => new ArtifactResult<ArtifactAdmission>.Failure(code, ArtifactPhase.Admission, ArtifactAction.OperatorRecovery, Guid.NewGuid());

    public ValueTask<ArtifactResult<ArtifactShutdown>> StopAsync(ArtifactCleanupOptions options, CancellationToken ct)
    {
        if (Interlocked.CompareExchange(ref lifetimeBusy, 1, 0) != 0)
        {
            return ValueTask.FromResult<ArtifactResult<ArtifactShutdown>>(new ArtifactResult<ArtifactShutdown>.Failure(
                ArtifactFailureCode.Conflict, ArtifactPhase.Cleanup, ArtifactAction.Reobserve, Guid.NewGuid()));
        }
        try
        {
            initialized = false;
            rootLock?.Dispose();
            rootLock = null;
            return ValueTask.FromResult<ArtifactResult<ArtifactShutdown>>(new ArtifactResult<ArtifactShutdown>.Success(
                new ArtifactShutdown(ArtifactCleanupState.Released, 0, 0, false)));
        }
        finally { Volatile.Write(ref lifetimeBusy, 0); }
    }
}
