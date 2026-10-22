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
    private volatile bool initialized;
    private int lifetimeBusy;
    private readonly object admissionSync = new();
    private Task<ArtifactResult<ArtifactAdmission>>? admissionWork;
    private CancellationTokenSource? admissionCancellation;
    private FileStream? rootLock;
    public bool Ready
    {
        get
        {
            lock (workSync)
            {
                return initialized && lifetimeBusy == 0 && !stopRequested
        && lateWork.Count == 0 && incompleteHandoffs.Count == 0 && unfinishedReadCloses.IsEmpty && Capabilities.MeetsBaseline;
            }
        }
    }
    public ArtifactCapabilities Capabilities { get; private set; } = new(
        1, ArtifactDurability.SimulationOnly, ArtifactEnumerationConsistency.Incomplete, new ArtifactLimits());

    public async ValueTask<ArtifactResult<ArtifactAdmission>> InitializeAsync(
        ArtifactInitialization request, ArtifactMaintenanceOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(options);
        if (Interlocked.CompareExchange(ref lifetimeBusy, 1, 0) != 0) { return Failure(ArtifactFailureCode.Conflict); }
        var deadline = new CancellationTokenSource(options.Deadline, time);
        var cancellation = CancellationTokenSource.CreateLinkedTokenSource(ct, deadline.Token);
        var token = cancellation.Token;
        Task<ArtifactResult<ArtifactAdmission>> operation;
        lock (admissionSync)
        {
            admissionCancellation = cancellation;
            admissionWork = operation = Task.Run(async () =>
            {
                try { return await InitializeCoreAsync(request, options, token); }
                catch (Exception error) { return FailedInitialization(MapError(error, ct)); }
                finally
                {
                    lock (admissionSync) { admissionCancellation = null; cancellation.Dispose(); deadline.Dispose(); }
                    Volatile.Write(ref lifetimeBusy, 0);
                }
            });
        }
        try
        {
            var result = await operation.WaitAsync(token);
            return result is ArtifactResult<ArtifactAdmission>.Failure { Code: ArtifactFailureCode.CancelledBeforeCommit }
                && !ct.IsCancellationRequested ? Failure(ArtifactFailureCode.DeadlineExceeded) : result;
        }
        catch (OperationCanceledException)
        {
            return new ArtifactResult<ArtifactAdmission>.Failure(ct.IsCancellationRequested
                ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded,
                ArtifactPhase.Admission, ArtifactAction.OperatorRecovery, Guid.NewGuid(),
                cleanup: operation.IsCompleted ? ArtifactCleanupState.Released : ArtifactCleanupState.RetainedLiveOwnership);
        }
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
        var capabilities = new ArtifactCapabilities(1, ArtifactDurability.SimulationOnly, ArtifactEnumerationConsistency.Incomplete, request.Limits);
        Capabilities = faults.CapabilitiesForAdmission?.Invoke(capabilities) ?? capabilities;
        if (!Capabilities.MeetsBaseline || Capabilities.Limits != request.Limits
            || Capabilities.Durability != capabilities.Durability || Capabilities.Enumeration != capabilities.Enumeration
            || Capabilities.RangeReads || !Capabilities.Sha512)
        { return Failure(ArtifactFailureCode.Unsupported); }
        var probe = await request.Authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
            request.Store, new Hoard.Abstractions.Metadata.ArtifactDigest(new string('0', 64))), new(), ct);
        if (probe is not ArtifactResult<IArtifactProtectionGuard>.Success recognized)
        { return Failure(ArtifactFailureCode.Denied); }
        await recognized.Value.DisposeAsync();
        try
        {
            await faults.ObserveAsync("object.initialize");
            ct.ThrowIfCancellationRequested();
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
            bucketPath = path;
            initializedWith = request;
            processSession = state.Process;
            utcFloor = state.Created;
            transferSlots = new(request.Limits.TransferSlots, request.Limits.TransferSlots);
            stopToken.Dispose();
            stopToken = new();
            stopRequested = false;
            initialized = true;
            await faults.ObserveAsync("object.admitted");
            ct.ThrowIfCancellationRequested();
            return new ArtifactResult<ArtifactAdmission>.Success(new(request.Store, Capabilities));
        }
        catch (UnauthorizedAccessException) { return FailedInitialization(ArtifactFailureCode.AccessDenied); }
        catch (IOException) { return FailedInitialization(ArtifactFailureCode.Unavailable); }
        catch (ArgumentException) { return FailedInitialization(ArtifactFailureCode.InvalidInput); }
        catch (OperationCanceledException) { return FailedInitialization(ArtifactFailureCode.CancelledBeforeCommit); }
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

    public async ValueTask<ArtifactResult<ArtifactShutdown>> StopAsync(ArtifactCleanupOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(options);
        var start = time.GetTimestamp();
        Task? admitting;
        Task cancellation;
        lock (admissionSync)
        {
            admitting = admissionWork;
            cancellation = admissionCancellation?.CancelAsync() ?? Task.CompletedTask;
        }
        try { await Task.WhenAll(admitting ?? Task.CompletedTask, cancellation).WaitAsync(options.Deadline, ct); }
        catch (Exception error) when (error is OperationCanceledException or TimeoutException)
        { return Rejected<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, retainedOwnership: true); }
        if (Interlocked.CompareExchange(ref lifetimeBusy, 1, 0) != 0)
        {
            return new ArtifactResult<ArtifactShutdown>.Failure(
                ArtifactFailureCode.Conflict, ArtifactPhase.Cleanup, ArtifactAction.Reobserve, Guid.NewGuid());
        }
        try
        {
            Task[] pending;
            lock (workSync)
            {
                stopRequested = true;
                pending = [.. ownedWork.Values, stopToken.CancelAsync()];
            }
            var remaining = options.Deadline - time.GetElapsedTime(start);
            if (remaining <= TimeSpan.Zero)
            { return Rejected<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, retainedOwnership: true); }
            try { await Task.WhenAll(pending).WaitAsync(remaining, ct); }
            catch (Exception error) when (error is OperationCanceledException or TimeoutException)
            { return Rejected<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, retainedOwnership: true); }
            remaining = options.Deadline - time.GetElapsedTime(start);
            if (remaining <= TimeSpan.Zero)
            { return Rejected<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, retainedOwnership: true); }
            try { await Task.WhenAll(RetryUndeliveredCleanup()).WaitAsync(remaining, ct); }
            catch (Exception)
            { return Rejected<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, retainedOwnership: true); }
            ObjectReadSession[] admitted;
            lock (pointerSync) { admitted = sessions.ToArray(); }
            foreach (var session in admitted)
            {
                remaining = options.Deadline - time.GetElapsedTime(start);
                if (remaining < TimeSpan.FromMilliseconds(1)
                    || await session.CloseAsync(new(remaining), ct) is not ArtifactResult<ArtifactShutdown>.Success)
                { return Rejected<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, retainedOwnership: true); }
            }
            initialized = false;
            rootLock?.Dispose();
            rootLock = null;
            return new ArtifactResult<ArtifactShutdown>.Success(
                new ArtifactShutdown(ArtifactCleanupState.Released, 0, 0, false));
        }
        finally { Volatile.Write(ref lifetimeBusy, 0); }
    }
}
