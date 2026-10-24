using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactLifecycleAssertions
{
    public static async Task ComposedShutdownAsync(
        IArtifactStore store, IArtifactCoordinationAuthority authority, ArtifactStoreIdentity identity,
        Func<bool> hasRetainedWork, Func<ValueTask> dispose, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("authority shutdown"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        var receipt = Success(await store.CommitAsync(staged, new(), cancellationToken));
        var request = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Deletion,
            identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
            await authority.AcquireAsync(request, new(TimeSpan.FromMilliseconds(20)), cancellationToken));
        Assert.True(hasRetainedWork());
        await Assert.ThrowsAsync<InvalidOperationException>(() => dispose().AsTask());
        Assert.True(hasRetainedWork());
    }

    public static async Task ConcurrentCloseAsync(
        IArtifactStore store, Action delayRelease, Func<Task> releaseEntered, Action release,
        CancellationToken cancellationToken)
    {
        using var source = new ShortSource("concurrent close"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        delayRelease();
        var session = Success(await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken));
        var close = session.CloseAsync(new(), cancellationToken).AsTask();
        try
        {
            await releaseEntered().WaitAsync(TimeSpan.FromSeconds(2));
            var retry = await session.CloseAsync(new(TimeSpan.FromMilliseconds(20)), cancellationToken);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(retry).Code);
            using var destination = new MemoryStream();
            Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await session.CopyToAsync(destination, new(), cancellationToken)).Code);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken)).Code);
        }
        finally
        {
            release();
            Success(await close);
            Success(await session.CloseAsync(new(), cancellationToken));
        }
    }

    public static async Task NativeBoundaryAsync(
        Task mutation, Func<bool> waitForEntry, Func<ArtifactCleanupOptions, ValueTask<ArtifactResult<ArtifactShutdown>>> stop)
    {
        Assert.True(await Task.Run(waitForEntry));
        await mutation.WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
            await stop(new(TimeSpan.FromMilliseconds(20))).AsTask().WaitAsync(TimeSpan.FromSeconds(2))).Code);
    }

    public static async Task BoundedFailureAsync<T>(Task<ArtifactResult<T>> task) where T : notnull
    {
        var failure = Assert.IsType<ArtifactResult<T>.Failure>(await task);
        Assert.True(failure.Code is ArtifactFailureCode.DeadlineExceeded or ArtifactFailureCode.Uncertain);
        Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failure.Cleanup);
    }
}
