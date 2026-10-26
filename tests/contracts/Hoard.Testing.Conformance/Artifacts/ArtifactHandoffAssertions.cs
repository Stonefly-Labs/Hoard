using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactHandoffAssertions
{
    public static Task ReleasedCancellationAsync(
        IArtifactStore store, Action<Func<ValueTask>> observeRelease, Func<Task> holdRelease,
        Func<Task> waitForRelease, Action removeObserver, Action releaseBoundary, CancellationToken cancellationToken)
        => ReleasedCancellationAsync(store,
            observer => { observeRelease(observer); return ValueTask.CompletedTask; }, holdRelease, waitForRelease,
            () => { removeObserver(); return ValueTask.CompletedTask; }, releaseBoundary, cancellationToken);

    public static async Task ReleasedCancellationAsync(
        IArtifactStore store, Func<Func<ValueTask>, ValueTask> observeRelease, Func<Task> holdRelease,
        Func<Task> waitForRelease, Func<ValueTask> removeObserver, Action releaseBoundary, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("released cancellation bookkeeping"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        var invalid = new ArtifactStagedWrite(staged.Owner, staged.Identity, Guid.NewGuid(), staged.PrivateHandle);
        using var cancellation = new CancellationTokenSource();
        async ValueTask Observe()
        {
            cancellation.Cancel();
            await holdRelease();
        }
        await observeRelease(Observe);
        try
        {
            var attempt = store.CommitAsync(invalid, new(), cancellation.Token).AsTask();
            await waitForRelease();
            await removeObserver();
            var result = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await attempt);
            Assert.Equal(ArtifactCleanupState.Released, result.Cleanup);
            Assert.IsType<ArtifactResolution.Pending>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        }
        finally { releaseBoundary(); }
    }

    public static Task SuccessfulResultAsync(
        IArtifactStore store, bool readSession, Action<Func<ValueTask>> observeRelease, Func<Task> holdRelease,
        Func<Task> waitForRelease, Action removeObserver, Action releaseBoundary, CancellationToken cancellationToken)
        => SuccessfulResultAsync(store, readSession,
            observer => { observeRelease(observer); return ValueTask.CompletedTask; }, holdRelease, waitForRelease,
            () => { removeObserver(); return ValueTask.CompletedTask; }, releaseBoundary, cancellationToken);

    public static async Task SuccessfulResultAsync(
        IArtifactStore store, bool readSession, Func<Func<ValueTask>, ValueTask> observeRelease, Func<Task> holdRelease,
        Func<Task> waitForRelease, Func<ValueTask> removeObserver, Action releaseBoundary, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("successful result ownership handoff"u8.ToArray());
        var published = readSession ? await PublishAsync(store, source, new(1024), cancellationToken) : null;
        using var cancellation = new CancellationTokenSource();
        async ValueTask Observe()
        {
            cancellation.Cancel();
            await holdRelease();
        }
        await observeRelease(Observe);
        try
        {
            if (published is null)
            {
                var reserving = store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellation.Token).AsTask();
                await waitForRelease();
                await removeObserver();
                var ticket = Success(await reserving);
                var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
                Success(await store.CommitAsync(staged, new(), cancellationToken));
                Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
            }
            else
            {
                var opening = store.OpenReadAsync(new(published.Stamp.Identity.Digest), new(), cancellation.Token).AsTask();
                await waitForRelease();
                await removeObserver();
                await using var read = Success(await opening);
                using var destination = new MemoryStream();
                Success(await read.CopyToAsync(destination, new(), cancellationToken));
                Assert.Equal("successful result ownership handoff"u8.ToArray(), destination.ToArray());
                Assert.Equal(ArtifactCleanupState.Released, Success(await read.CloseAsync(new(), cancellationToken)).State);
                var deletion = Success(await store.ReserveDeleteAsync(new(published.Stamp), new(), cancellationToken));
                Success(await store.DeleteAsync(deletion, new(), cancellationToken));
            }
        }
        finally
        {
            try { await removeObserver(); }
            finally { releaseBoundary(); }
        }
    }

    public static Task UnclaimedResultAsync(
        IArtifactStore store, bool readSession, Action blockCompletion, Func<Task> waitForCompletion,
        Action releaseCompletion, Func<Task> whenIdle, CancellationToken cancellationToken)
        => UnclaimedResultAsync(store, readSession,
            () => { blockCompletion(); return ValueTask.CompletedTask; }, waitForCompletion,
            () => { releaseCompletion(); return ValueTask.CompletedTask; }, whenIdle, cancellationToken);

    public static async Task UnclaimedResultAsync(
        IArtifactStore store, bool readSession, Func<ValueTask> blockCompletion, Func<Task> waitForCompletion,
        Func<ValueTask> releaseCompletion, Func<Task> whenIdle, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("unclaimed result cleanup"u8.ToArray());
        var published = readSession ? await PublishAsync(store, source, new(1024), cancellationToken) : null;
        using var cancellation = new CancellationTokenSource();
        await blockCompletion();
        try
        {
            if (published is null)
            {
                var reserving = store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellation.Token).AsTask();
                await waitForCompletion();
                cancellation.Cancel();
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership,
                    Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(await reserving).Cleanup);
            }
            else
            {
                var opening = store.OpenReadAsync(new(published.Stamp.Identity.Digest), new(), cancellation.Token).AsTask();
                await waitForCompletion();
                cancellation.Cancel();
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership,
                    Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(await opening).Cleanup);
            }
        }
        finally { await releaseCompletion(); }
        await whenIdle().WaitAsync(TimeSpan.FromSeconds(2));
        if (published is null)
        {
            Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        }
        else
        {
            var deletion = Success(await store.ReserveDeleteAsync(new(published.Stamp), new(), cancellationToken));
            Success(await store.DeleteAsync(deletion, new(), cancellationToken));
        }
    }

    public static Task ExpiredStagingAsync(
        IArtifactStore store, Action<TimeSpan> advanceClock, Action blockCompletion, Func<Task> waitForCompletion,
        Action releaseCompletion, Func<Task> whenIdle, CancellationToken cancellationToken)
        => ExpiredStagingAsync(store, advanceClock,
            () => { blockCompletion(); return ValueTask.CompletedTask; }, waitForCompletion,
            () => { releaseCompletion(); return ValueTask.CompletedTask; }, whenIdle, cancellationToken);

    public static async Task ExpiredStagingAsync(
        IArtifactStore store, Action<TimeSpan> advanceClock, Func<ValueTask> blockCompletion, Func<Task> waitForCompletion,
        Func<ValueTask> releaseCompletion, Func<Task> whenIdle, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("expired unclaimed staging"u8.ToArray());
        using var cancellation = new CancellationTokenSource();
        await blockCompletion();
        try
        {
            var staging = store.StageAsync(ticket, source, new(), cancellation.Token).AsTask();
            await waitForCompletion();
            advanceClock(TimeSpan.FromSeconds(31));
            cancellation.Cancel();
            Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await staging);
        }
        finally { await releaseCompletion(); }
        await whenIdle().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
    }
}
