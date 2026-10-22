using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore(string root, TimeProvider? clock = null, LocalFaultControls? controls = null)
    : IArtifactStoreLifetime
{
    private readonly string configuredRoot = root;
    private readonly TimeProvider time = clock ?? TimeProvider.System;
    private readonly LocalFaultControls faults = controls ?? new();
    private LocalRoot? ownership;
    private volatile bool initialized;
    private int lifecycleActive;
    private readonly object initializationSync = new();
    private Task<ArtifactResult<ArtifactAdmission>>? initializationTask;
    private CancellationTokenSource? initializationCancellation;
    public bool Ready
    {
        get
        {
            lock (activitySync)
            {
                return initialized && lifecycleActive == 0 && !stopping
        && retained.Count == 0 && incompleteHandoffs.Count == 0 && incompleteReadCloses.IsEmpty && Capabilities.MeetsBaseline;
            }
        }
    }
    public ArtifactCapabilities Capabilities { get; private set; } = new(
        1, ArtifactDurability.LocalProcessCrash, ArtifactEnumerationConsistency.Snapshot, new ArtifactLimits());

    public async ValueTask<ArtifactResult<ArtifactAdmission>> InitializeAsync(
        ArtifactInitialization request, ArtifactMaintenanceOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(options);
        if (Interlocked.CompareExchange(ref lifecycleActive, 1, 0) != 0) { return Failure(ArtifactFailureCode.Conflict); }
        var deadline = new CancellationTokenSource(options.Deadline, time);
        var cancellation = CancellationTokenSource.CreateLinkedTokenSource(ct, deadline.Token);
        var token = cancellation.Token;
        Task<ArtifactResult<ArtifactAdmission>> work;
        lock (initializationSync)
        {
            initializationCancellation = cancellation;
            initializationTask = work = Task.Run(async () =>
            {
                try { return await InitializeCoreAsync(request, options, token); }
                catch (Exception error) { return FailedInitialization(FailureCode(error, ct)); }
                finally
                {
                    lock (initializationSync) { initializationCancellation = null; cancellation.Dispose(); deadline.Dispose(); }
                    Volatile.Write(ref lifecycleActive, 0);
                }
            });
        }
        try
        {
            var result = await work.WaitAsync(token);
            return result is ArtifactResult<ArtifactAdmission>.Failure { Code: ArtifactFailureCode.CancelledBeforeCommit }
                && !ct.IsCancellationRequested ? Failure(ArtifactFailureCode.DeadlineExceeded) : result;
        }
        catch (OperationCanceledException)
        {
            return new ArtifactResult<ArtifactAdmission>.Failure(ct.IsCancellationRequested
                ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded,
                ArtifactPhase.Admission, ArtifactAction.OperatorRecovery, Guid.NewGuid(),
                cleanup: work.IsCompleted ? ArtifactCleanupState.Released : ArtifactCleanupState.RetainedLiveOwnership);
        }
    }

    private async ValueTask<ArtifactResult<ArtifactAdmission>> InitializeCoreAsync(
        ArtifactInitialization request, ArtifactMaintenanceOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(options);
        if (initialized) { return Failure(ArtifactFailureCode.Conflict); }
        if (ct.IsCancellationRequested) { return Failure(ArtifactFailureCode.CancelledBeforeCommit); }
        var capabilities = new ArtifactCapabilities(1, ArtifactDurability.LocalProcessCrash, ArtifactEnumerationConsistency.Snapshot, request.Limits);
        Capabilities = faults.CapabilitiesForAdmission?.Invoke(capabilities) ?? capabilities;
        if (!Capabilities.MeetsBaseline || Capabilities.Limits != request.Limits
            || Capabilities.Durability != capabilities.Durability || Capabilities.Enumeration != capabilities.Enumeration
            || Capabilities.RangeReads || !Capabilities.Sha512)
        { return Failure(ArtifactFailureCode.Unsupported); }
        var probe = await request.Authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
            request.Store, new Hoard.Abstractions.Metadata.ArtifactDigest(new string('0', 64))), new(), ct);
        if (probe is not ArtifactResult<IArtifactProtectionGuard>.Success accepted) { return Failure(ArtifactFailureCode.Denied); }
        await accepted.Value.DisposeAsync();
        try
        {
            await faults.ObserveAsync("initialize.before-root");
            ct.ThrowIfCancellationRequested();
            ownership = LocalRoot.Open(configuredRoot, request, time.GetUtcNow());
            ct.ThrowIfCancellationRequested();
            configuration = request;
            slots = new SemaphoreSlim(request.Limits.TransferSlots, request.Limits.TransferSlots);
            shutdown.Dispose();
            shutdown = new();
            stopping = false;
            if (request.Mode == ArtifactInitializationMode.ReopenCompatible) { await RecoverAsync(ct); }
            initialized = true;
            await faults.ObserveAsync("initialize.admitted");
            ct.ThrowIfCancellationRequested();
            return new ArtifactResult<ArtifactAdmission>.Success(new(request.Store, Capabilities));
        }
        catch (LocalStateException error) { faults.RecordInitializationFailure(error); return FailedInitialization(error.Code); }
        catch (UnauthorizedAccessException) { return FailedInitialization(ArtifactFailureCode.AccessDenied); }
        catch (IOException) { return FailedInitialization(ArtifactFailureCode.Unavailable); }
        catch (ArgumentException error) { faults.RecordInitializationFailure(error); return FailedInitialization(ArtifactFailureCode.InvalidInput); }
        catch (OperationCanceledException) { return FailedInitialization(ArtifactFailureCode.CancelledBeforeCommit); }
        catch (Exception) { return FailedInitialization(ArtifactFailureCode.InternalFailure); }
    }

    private ArtifactResult<ArtifactAdmission> FailedInitialization(ArtifactFailureCode code)
    {
        initialized = false;
        ownership?.Dispose();
        ownership = null;
        return Failure(code);
    }

    private static ArtifactResult<ArtifactAdmission> Failure(ArtifactFailureCode code)
        => new ArtifactResult<ArtifactAdmission>.Failure(code, ArtifactPhase.Admission, ArtifactAction.OperatorRecovery, Guid.NewGuid());

    public async ValueTask<ArtifactResult<ArtifactShutdown>> StopAsync(ArtifactCleanupOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(options);
        var started = time.GetTimestamp();
        Task? opening;
        Task cancelled;
        lock (initializationSync)
        {
            opening = initializationTask;
            cancelled = initializationCancellation?.CancelAsync() ?? Task.CompletedTask;
        }
        try { await Task.WhenAll(opening ?? Task.CompletedTask, cancelled).WaitAsync(options.Deadline, ct); }
        catch (Exception error) when (error is TimeoutException or OperationCanceledException)
        { return Failed<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, live: true); }
        if (Interlocked.CompareExchange(ref lifecycleActive, 1, 0) != 0)
        {
            return new ArtifactResult<ArtifactShutdown>.Failure(
                ArtifactFailureCode.Conflict, ArtifactPhase.Cleanup, ArtifactAction.Reobserve, Guid.NewGuid());
        }
        try
        {
            Task[] pending;
            lock (activitySync)
            {
                stopping = true;
                pending = [.. activities.Values, shutdown.CancelAsync()];
            }
            var remaining = options.Deadline - time.GetElapsedTime(started);
            if (remaining <= TimeSpan.Zero)
            { return Failed<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, live: true); }
            try { await Task.WhenAll(pending).WaitAsync(remaining, ct); }
            catch (Exception error) when (error is TimeoutException or OperationCanceledException)
            { return Failed<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, live: true); }
            remaining = options.Deadline - time.GetElapsedTime(started);
            if (remaining <= TimeSpan.Zero)
            { return Failed<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, live: true); }
            try { await Task.WhenAll(RetryUndeliveredCleanup()).WaitAsync(remaining, ct); }
            catch (Exception)
            { return Failed<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, live: true); }
            LocalReadSession[] sessions;
            lock (stateSync) { sessions = readers.ToArray(); }
            foreach (var session in sessions)
            {
                remaining = options.Deadline - time.GetElapsedTime(started);
                if (remaining < TimeSpan.FromMilliseconds(1)
                    || await session.CloseAsync(new(remaining), ct) is not ArtifactResult<ArtifactShutdown>.Success)
                { return Failed<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, live: true); }
            }
            ownership?.Dispose();
            ownership = null;
            initialized = false;
            return new ArtifactResult<ArtifactShutdown>.Success(
                new ArtifactShutdown(ArtifactCleanupState.Released, 0, 0, false));
        }
        finally { Volatile.Write(ref lifecycleActive, 0); }
    }
}
