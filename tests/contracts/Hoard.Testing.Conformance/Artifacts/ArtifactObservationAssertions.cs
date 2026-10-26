using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactObservationAssertions
{
    public static async Task DirectVerificationAsync(
        IArtifactAssertionSession session, bool duplicate, CancellationToken cancellationToken)
    {
        var bytes = "direct verification before acknowledgement"u8.ToArray();
        ArtifactMutationReceipt? original = null;
        if (duplicate)
        {
            using var initial = new ShortSource(bytes);
            original = await PublishAsync(session.Store, initial, new(1024), cancellationToken);
        }
        using var source = new ShortSource(bytes);
        var ticket = Success(await session.Store.ReserveWriteAsync(
            new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await session.Store.StageAsync(ticket, source, new(), cancellationToken));
        await using var barrier = new ArtifactConformanceBarrier("direct-verification");
        await using var observation = await session.ObserveBoundaryAsync(
            ArtifactObservationPoint.DirectVerification, () => new(barrier.HoldAsync()), cancellationToken);
        var committing = session.Store.CommitAsync(staged, new(), cancellationToken).AsTask();
        ArtifactMutationReceipt receipt;
        try
        {
            await barrier.Entered.WaitAsync(cancellationToken);
            Assert.False(committing.IsCompleted);
        }
        finally
        {
            barrier.Release();
            receipt = Success(await committing.WaitAsync(TimeSpan.FromSeconds(10)));
            await session.AwaitSettlementAsync(CancellationToken.None);
        }
        Assert.Equal(duplicate ? ArtifactMutationOutcome.AlreadyPresentVerified : ArtifactMutationOutcome.Published,
            receipt.Outcome);
        if (original is not null) { Assert.Equal(original.Stamp, receipt.Stamp); }
        Assert.False(source.WasDisposed);
        Assert.Equal(bytes, await ReadAsync(session.Store, receipt.Stamp, cancellationToken));
    }

    public static Task ReceiptPersistedAsync(
        IArtifactStore store, Action<Func<ValueTask>> observe, Action remove, CancellationToken cancellationToken)
        => ReceiptPersistedAsync(store, observer =>
        {
            observe(observer);
            return ValueTask.CompletedTask;
        }, () => { remove(); return ValueTask.CompletedTask; }, cancellationToken);

    public static async Task ReceiptPersistedAsync(
        IArtifactStore store, Func<Func<ValueTask>, ValueTask> observe, Func<ValueTask> remove,
        CancellationToken cancellationToken)
    {
        using var source = new ShortSource("observed publication"u8.ToArray());
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await observe(() => { entered.TrySetResult(); return new(release.Task); });
        var committing = store.CommitAsync(staged, new(), cancellationToken).AsTask();
        ArtifactMutationReceipt? persisted = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5), cancellationToken);
            Assert.False(committing.IsCompleted);
            persisted = Assert.IsType<ArtifactResolution.Committed>(
                Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt;
        }
        finally
        {
            try { await remove(); }
            finally
            {
                release.TrySetResult();
                Assert.Equal(persisted, Success(await committing));
            }
        }
    }

    public static Task ReadOpenedFailureAsync(
        IArtifactStore store, Action<Func<ValueTask>> observe, Action remove, CancellationToken cancellationToken)
        => ReadOpenedFailureAsync(store, () =>
        {
            observe(() => throw new InvalidOperationException("controlled-read-open-failure"));
            return ValueTask.CompletedTask;
        }, () => { remove(); return ValueTask.CompletedTask; }, cancellationToken);

    public static async Task ReadOpenedFailureAsync(
        IArtifactStore store, Func<ValueTask> injectFailure, Func<ValueTask> remove, CancellationToken cancellationToken)
    {
        var bytes = "observed resource opening"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        await injectFailure();
        try
        {
            Assert.Equal(ArtifactFailureCode.InternalFailure, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)).Code);
        }
        finally { await remove(); }
        await using var read = Success(await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken));
        using var destination = new MemoryStream();
        Success(await read.CopyToAsync(destination, new(), cancellationToken));
        Assert.Equal(bytes, destination.ToArray());
        Assert.Equal(ArtifactCleanupState.Released, Success(await read.CloseAsync(new(), cancellationToken)).State);
        var deletion = Success(await store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
        var removed = await store.DeleteAsync(deletion, new(), cancellationToken);
        Assert.True(removed is ArtifactResult<ArtifactMutationReceipt>.Success,
            removed is ArtifactResult<ArtifactMutationReceipt>.Failure failure
                ? failure.Code.ToString() : "Unexpected deletion result.");
    }

    public static Task ReconciliationVerifiedAsync(
        IArtifactStore store, Action<Func<ValueTask>> observeSelected, Action removeSelected,
        Action<Func<ValueTask>> observeBefore, Action<Func<ValueTask>> observeVerified, Action removeReconciliation,
        CancellationToken cancellationToken)
        => ReconciliationVerifiedAsync(store, () =>
        {
            observeSelected(() => throw new InvalidOperationException("controlled-selected-failure"));
            return ValueTask.CompletedTask;
        }, () => { removeSelected(); return ValueTask.CompletedTask; }, observer =>
        {
            observeBefore(observer);
            return ValueTask.CompletedTask;
        }, observer =>
        {
            observeVerified(async () =>
            {
                await observer();
                throw new InvalidOperationException("controlled-verified-failure");
            });
            return ValueTask.CompletedTask;
        }, () => { removeReconciliation(); return ValueTask.CompletedTask; }, cancellationToken);

    public static async Task ReconciliationVerifiedAsync(
        IArtifactStore store, Func<ValueTask> injectSelected, Func<ValueTask> removeSelected,
        Func<Func<ValueTask>, ValueTask> observeBefore, Func<Func<ValueTask>, ValueTask> injectVerified,
        Func<ValueTask> removeReconciliation, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("observed reconciliation"u8.ToArray());
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        await injectSelected();
        try
        {
            Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await store.CommitAsync(staged, new(), cancellationToken)).Code);
        }
        finally { await removeSelected(); }
        var before = 0;
        var verified = 0;
        await observeBefore(() => { Interlocked.Increment(ref before); return ValueTask.CompletedTask; });
        await injectVerified(() =>
        {
            Interlocked.Increment(ref verified);
            return ValueTask.CompletedTask;
        });
        try
        {
            Assert.Equal(ArtifactFailureCode.InternalFailure, Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
                await store.ReconcileAsync(ticket, new(), cancellationToken)).Code);
            Assert.Equal(1, before);
            Assert.Equal(1, verified);
        }
        finally { await removeReconciliation(); }
        var recovered = Assert.IsType<ArtifactResolution.Committed>(
            Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt;
        Assert.Equal(ticket, recovered.Ticket);
        Assert.Equal(staged.Identity, recovered.Stamp.Identity);
    }
}
