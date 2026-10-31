using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactOwnershipAssertions;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactBudgetAssertions
{
    public static async Task UnclaimedCleanupFailureAsync(
        IArtifactStore store, bool readSession, Action blockCompletion, Func<Task> waitForCompletion,
        Action releaseCompletion, Action<Func<ValueTask>> observeReclaim, Action removeReclaim,
        Func<Task> whenIdle, Func<ArtifactCleanupOptions, ValueTask<ArtifactResult<ArtifactShutdown>>> stop,
        CancellationToken cancellationToken)
    {
        using var source = new ShortSource("failed unclaimed cleanup"u8.ToArray());
        var published = readSession ? await PublishAsync(store, source, new(1024), cancellationToken) : null;
        using var cancellation = new CancellationTokenSource();
        blockCompletion();
        observeReclaim(() => throw new IOException("synthetic unclaimed cleanup failure"));
        try
        {
            try
            {
                if (published is null)
                {
                    var reserving = store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellation.Token).AsTask();
                    await waitForCompletion();
                    cancellation.Cancel();
                    Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(await reserving);
                }
                else
                {
                    var opening = store.OpenReadAsync(new(published.Stamp.Identity.Digest), new(), cancellation.Token).AsTask();
                    await waitForCompletion();
                    cancellation.Cancel();
                    Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(await opening);
                }
            }
            finally { releaseCompletion(); }
            await whenIdle().WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken)).Code);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                await stop(new())).Code);
        }
        finally
        {
            removeReclaim();
            Assert.Equal(ArtifactCleanupState.Released, Success(await stop(new())).State);
        }
    }

    public static async Task CancelledCommitFencingAsync(
        IArtifactStore store, IArtifactCoordinationAuthority authority, ArtifactStoreIdentity identity,
        Func<Task> whenIdle, bool alreadyCancelled, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("cancelled publication is terminal"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        var stamp = new ArtifactStamp(identity, staged.Identity, Guid.NewGuid());
        var exclusion = Success(await authority.AcquireAsync(new(Guid.NewGuid(),
            ArtifactProtectionOperation.Deletion, identity, staged.Identity.Digest,
            new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), cancellationToken));
        using var cancellation = new CancellationTokenSource();
        if (alreadyCancelled) { cancellation.Cancel(); }
        try
        {
            var failure = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await store.CommitAsync(staged, new(TimeSpan.FromMilliseconds(30)), cancellation.Token));
            Assert.Equal(alreadyCancelled ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded,
                failure.Code);
        }
        finally { await exclusion.DisposeAsync(); }
        await whenIdle().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await store.CommitAsync(staged, new(), cancellationToken));
        var read = await Task.Factory.StartNew(() => store.OpenReadAsync(
            new(staged.Identity.Digest), new(), cancellationToken).AsTask(), CancellationToken.None,
            TaskCreationOptions.LongRunning, TaskScheduler.Default).Unwrap();
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            read).Code);
    }

    public static async Task TransferQueueAsync(
        IArtifactStore store, Action<Func<ValueTask>> observeQueue, CancellationToken cancellationToken)
    {
        var tickets = new List<ArtifactOperationTicket>();
        for (var index = 0; index < 3; index++)
        { tickets.Add(Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken))); }
        var queued = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        ValueTask ObserveQueue() { queued.TrySetResult(); return ValueTask.CompletedTask; }
        observeQueue(ObserveQueue);
        using var first = new PendingSource(cooperative: true);
        var active = store.StageAsync(tickets[0], first, new(), cancellationToken).AsTask();
        await first.Entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
        using var second = new ShortSource([1]);
        var waiting = store.StageAsync(tickets[1], second, new(), cancellationToken).AsTask();
        try
        {
            await queued.Task.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(0, second.BytesRead);
            using var rejected = new ShortSource([1]);
            Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await store.StageAsync(tickets[2], rejected, new(), cancellationToken)).Code);
            Assert.Equal(0, rejected.BytesRead);
        }
        finally { first.Released.TrySetResult(0); }
        var completed = Success(await active);
        var unblocked = Success(await waiting);
        Success(await store.AbandonAsync(completed.Owner, new(), cancellationToken));
        Success(await store.AbandonAsync(unblocked.Owner, new(), cancellationToken));
        using var restored = new ShortSource([1]);
        Success(await store.StageAsync(tickets[2], restored, new(), cancellationToken));
        Assert.Equal(1, restored.BytesRead);
    }

    public static async Task CapCrossingAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(10)), new(), cancellationToken));
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken)).Code);
        using var source = new ShortSource("actual input is too large"u8.ToArray());
        Assert.Equal(ArtifactFailureCode.LimitExceeded, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await store.StageAsync(ticket, source, new(), cancellationToken)).Code);
        Assert.False(source.WasDisposed);
        Assert.NotNull(Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(10)), new(), cancellationToken)));
        Assert.Equal(ArtifactFailureCode.LimitExceeded, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await store.ReserveWriteAsync(new(new ArtifactExpectations(11)), new(), cancellationToken)).Code);
    }

    public static async Task AuthorityDeadlineAsync(
        IArtifactStore store, IArtifactCoordinationAuthority authority, ArtifactStoreIdentity identity,
        CancellationToken cancellationToken)
    {
        using var source = new ShortSource("guard queue budget"u8.ToArray());
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        var stamp = new ArtifactStamp(identity, staged.Identity, Guid.NewGuid());
        await using var exclusion = Success(await authority.AcquireAsync(new(Guid.NewGuid(),
            ArtifactProtectionOperation.Deletion, identity, staged.Identity.Digest,
            new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), cancellationToken));
        var result = await store.CommitAsync(staged,
            new ArtifactTransferOptions(TimeSpan.FromMilliseconds(30)), cancellationToken).AsTask().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Equal(ArtifactFailureCode.DeadlineExceeded, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(result).Code);
    }

    public static async Task CooperativeCancellationAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        using var source = new PendingSource(cooperative: true);
        using var cancelled = new CancellationTokenSource();
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staging = store.StageAsync(ticket, source, new(), cancelled.Token).AsTask();
        await source.Entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
        cancelled.Cancel();
        var result = await staging.WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Equal(ArtifactFailureCode.CancelledBeforeCommit, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(result).Code);
        Assert.False(source.WasDisposed);
    }
}
