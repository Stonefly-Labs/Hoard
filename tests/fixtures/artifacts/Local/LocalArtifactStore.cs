using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore(string root, TimeProvider? clock = null, LocalFaultControls? controls = null)
    : IArtifactStoreLifetime
{
    private readonly string configuredRoot = root;
    private readonly TimeProvider time = clock ?? TimeProvider.System;
    private readonly LocalFaultControls faults = controls ?? new();
    private LocalRoot? ownership;
    private bool initialized;
    private int lifecycleActive;
    public bool Ready => initialized && Capabilities.MeetsBaseline;
    public ArtifactCapabilities Capabilities { get; private set; } = new(
        1, ArtifactDurability.LocalProcessCrash, ArtifactEnumerationConsistency.Snapshot, new ArtifactLimits(),
        conditionalPublication: false, conditionalDeletion: false, stagingRecovery: false,
        ownerFencing: false, readerProtection: false, boundedStreaming: false);

    public async ValueTask<ArtifactResult<ArtifactAdmission>> InitializeAsync(
        ArtifactInitialization request, ArtifactMaintenanceOptions options, CancellationToken ct)
    {
        if (Interlocked.CompareExchange(ref lifecycleActive, 1, 0) != 0) { return Failure(ArtifactFailureCode.Conflict); }
        try { return await InitializeCoreAsync(request, options, ct); }
        finally { Volatile.Write(ref lifecycleActive, 0); }
    }

    private async ValueTask<ArtifactResult<ArtifactAdmission>> InitializeCoreAsync(
        ArtifactInitialization request, ArtifactMaintenanceOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(options);
        if (initialized) { return Failure(ArtifactFailureCode.Conflict); }
        if (ct.IsCancellationRequested) { return Failure(ArtifactFailureCode.CancelledBeforeCommit); }
        var probe = await request.Authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
            request.Store, new Hoard.Abstractions.Metadata.ArtifactDigest(new string('0', 64))), new(), ct);
        if (probe is not ArtifactResult<IArtifactProtectionGuard>.Success accepted) { return Failure(ArtifactFailureCode.Denied); }
        await accepted.Value.DisposeAsync();
        try
        {
            await faults.ObserveAsync("initialize.before-root");
            ownership = LocalRoot.Open(configuredRoot, request, time.GetUtcNow());
            Capabilities = new(1, ArtifactDurability.LocalProcessCrash, ArtifactEnumerationConsistency.Snapshot, request.Limits,
                conditionalPublication: false, conditionalDeletion: false, stagingRecovery: false,
                ownerFencing: false, readerProtection: false, boundedStreaming: false);
            initialized = true;
            await faults.ObserveAsync("initialize.admitted");
            return new ArtifactResult<ArtifactAdmission>.Success(new(request.Store, Capabilities));
        }
        catch (LocalStateException error) { return FailedInitialization(error.Code); }
        catch (UnauthorizedAccessException) { return FailedInitialization(ArtifactFailureCode.AccessDenied); }
        catch (IOException) { return FailedInitialization(ArtifactFailureCode.Unavailable); }
        catch (ArgumentException) { return FailedInitialization(ArtifactFailureCode.InvalidInput); }
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

    public ValueTask<ArtifactResult<ArtifactShutdown>> StopAsync(ArtifactCleanupOptions options, CancellationToken ct)
    {
        if (Interlocked.CompareExchange(ref lifecycleActive, 1, 0) != 0)
        {
            return ValueTask.FromResult<ArtifactResult<ArtifactShutdown>>(new ArtifactResult<ArtifactShutdown>.Failure(
                ArtifactFailureCode.Conflict, ArtifactPhase.Cleanup, ArtifactAction.Reobserve, Guid.NewGuid()));
        }
        try
        {
            ownership?.Dispose();
            ownership = null;
            initialized = false;
            return ValueTask.FromResult<ArtifactResult<ArtifactShutdown>>(new ArtifactResult<ArtifactShutdown>.Success(
                new ArtifactShutdown(ArtifactCleanupState.Released, 0, 0, false)));
        }
        finally { Volatile.Write(ref lifecycleActive, 0); }
    }
}
