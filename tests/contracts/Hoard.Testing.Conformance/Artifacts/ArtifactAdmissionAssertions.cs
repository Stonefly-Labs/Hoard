using Hoard.Abstractions.Storage;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactAdmissionAssertions
{
    public static async Task NoncooperativeInitializationAsync(
        Func<Func<ValueTask>, (IArtifactStoreLifetime Store, ArtifactStoreIdentity Identity,
            IArtifactCoordinationAuthority Authority)> create,
        Func<bool> rootExists, Action<bool> setCleanupAllowed, Func<bool> cleanupAllowed,
        CancellationToken cancellationToken)
    {
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        ValueTask Pause() { entered.TrySetResult(); return new(release.Task); }
        var (store, identity, authority) = create(Pause);
        var initialization = store.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, identity,
            authority), new(TimeSpan.FromMilliseconds(100)), cancellationToken).AsTask();
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
            var failure = Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(
                await initialization.WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.Equal(ArtifactFailureCode.DeadlineExceeded, failure.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failure.Cleanup);
            Assert.False(rootExists());
            var stop = Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                await store.StopAsync(new(TimeSpan.FromMilliseconds(20)), cancellationToken).AsTask().WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, stop.Code);
        }
        finally
        {
            release.TrySetResult();
            await initialization;
            var stopped = await store.StopAsync(new(), cancellationToken);
            setCleanupAllowed(stopped is ArtifactResult<ArtifactShutdown>.Success);
            Assert.True(cleanupAllowed());
        }
        Assert.False(rootExists());
    }

    public static async Task BeforeAdmissionAsync(ArtifactStoreIdentity identity,
        Func<IArtifactStoreLifetime> create, Func<IArtifactCoordinationAuthority> createForeignAuthority,
        Func<bool> rootExists, ArtifactMaintenanceOptions options, ArtifactCleanupOptions cleanup,
        CancellationToken cancellationToken)
    {
        var lifetime = create();
        var store = Assert.IsAssignableFrom<IArtifactStore>(lifetime);
        Assert.Equal(ArtifactFailureCode.Disposed, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken)).Code);
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await lifetime.InitializeAsync(
            new(ArtifactInitializationMode.CreateEmpty, identity, createForeignAuthority()), options, cancellationToken));
        Assert.False(rootExists());
        await lifetime.StopAsync(cleanup, cancellationToken);
    }

    public static async Task ExclusiveCreateAsync(ArtifactStoreIdentity store, IArtifactCoordinationAuthority authority,
        Func<IArtifactStoreLifetime> create, Func<bool> rootExists,
        ArtifactMaintenanceOptions options, ArtifactCleanupOptions cleanup, CancellationToken cancellationToken)
    {
        var first = create();
        var second = create();
        Assert.False(rootExists());
        var result = await first.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, store, authority), options, cancellationToken);
        var admitted = Assert.IsType<ArtifactResult<ArtifactAdmission>.Success>(result);
        Assert.True(admitted.Value.Capabilities.MeetsBaseline);
        Assert.True(rootExists());
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await second.InitializeAsync(
            new(ArtifactInitializationMode.CreateEmpty, store, authority), options, cancellationToken));
        await second.StopAsync(cleanup, cancellationToken);
        await first.StopAsync(cleanup, cancellationToken);
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await second.InitializeAsync(
            new(ArtifactInitializationMode.CreateEmpty, store, authority), options, cancellationToken));
    }

    public static async Task RejectedRootChangesAsync(ArtifactStoreIdentity store,
        IArtifactCoordinationAuthority authority, Func<IArtifactStoreLifetime> create,
        Func<ArtifactStoreIdentity, IArtifactCoordinationAuthority> createAuthority, Func<bool> rootExists,
        Func<byte[], (Func<byte[]> Read, Action Restore)> damageManifest,
        ArtifactMaintenanceOptions options, ArtifactCleanupOptions cleanup, CancellationToken cancellationToken)
    {
        var first = create();
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await first.InitializeAsync(
            new(ArtifactInitializationMode.ReopenCompatible, store, authority), options, cancellationToken));
        Assert.False(rootExists());
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Success>(await first.InitializeAsync(
            new(ArtifactInitializationMode.CreateEmpty, store, authority), options, cancellationToken));
        await first.StopAsync(cleanup, cancellationToken);
        var second = create();
        var foreign = new ArtifactStoreIdentity(store.ProviderModuleId, store.InstanceId, Guid.NewGuid());
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await second.InitializeAsync(
            new(ArtifactInitializationMode.ReopenCompatible, foreign, createAuthority(foreign)), options, cancellationToken));
        await second.StopAsync(cleanup, cancellationToken);
        var manifest = damageManifest([1, 2, 3]);
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await second.InitializeAsync(
            new(ArtifactInitializationMode.ReopenCompatible, store, authority), options, cancellationToken));
        Assert.Equal(new byte[] { 1, 2, 3 }, manifest.Read());
        await second.StopAsync(cleanup, cancellationToken);
        manifest.Restore();
    }

    public static async Task ReopenGuaranteeAsync(ArtifactStoreIdentity identity,
        IArtifactCoordinationAuthority authority, bool durableReopen, Func<IArtifactStoreLifetime> create,
        ArtifactMaintenanceOptions options, ArtifactCleanupOptions cleanup, CancellationToken cancellationToken)
    {
        var first = create();
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Success>(await first.InitializeAsync(
            new(ArtifactInitializationMode.CreateEmpty, identity, authority), options, cancellationToken));
        await first.StopAsync(cleanup, cancellationToken);
        var second = create();
        var result = await second.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible, identity, authority), options, cancellationToken);
        if (durableReopen) { Assert.Equal(identity, Assert.IsType<ArtifactResult<ArtifactAdmission>.Success>(result).Value.Store); }
        else { Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(result); }
        await second.StopAsync(cleanup, cancellationToken);
    }

    public static async Task RejectedSymlinkAsync(ArtifactStoreIdentity identity,
        IArtifactCoordinationAuthority authority, Func<IArtifactStoreLifetime> create,
        Func<string> readSentinel, Func<bool> outsideChildExists,
        ArtifactMaintenanceOptions options, ArtifactCleanupOptions cleanup, CancellationToken cancellationToken)
    {
        var first = create();
        Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(await first.InitializeAsync(
            new(ArtifactInitializationMode.CreateEmpty, identity, authority), options, cancellationToken));
        Assert.Equal(ArtifactFailureAssertions.Canary, readSentinel());
        Assert.False(outsideChildExists());
        await first.StopAsync(cleanup, cancellationToken);
    }
}
