using System.Diagnostics;
using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataDeadlineAssertions
{
    public static async Task IncompleteCleanupAsync(
        IMetadataStore store, MetadataObservationControl observeAsync, Func<MetadataFaultCounters> observeCounters,
        Func<ValueTask> disposeAsync, Func<CancellationToken, ValueTask> awaitSettlementAsync,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        ArgumentNullException.ThrowIfNull(observeCounters);
        ArgumentNullException.ThrowIfNull(disposeAsync);
        ArgumentNullException.ThrowIfNull(awaitSettlementAsync);
        await using var barrier = new MetadataConformanceBarrier(TimeSpan.FromSeconds(60));
        var batch = Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        var before = observeCounters();
        await using var observation = await observeAsync(
            MetadataObservationPoint.BeforeCommitDecision, barrier.HoldAsync, cancellationToken);
        var committing = store.CommitAsync(batch, new(TimeSpan.FromMilliseconds(200)), cancellationToken).AsTask();
        Task<Exception?>? disposing = null;
        Task? settling = null;
        try
        {
            await barrier.WaitForEntryAsync(cancellationToken);
            Assert.Equal(MetadataFailureCode.DeadlineExceeded, Failed(await committing));
            disposing = Record.ExceptionAsync(async () => await disposeAsync());
            var error = Assert.IsType<InvalidOperationException>(await disposing.WaitAsync(TimeSpan.FromSeconds(35)));
            Assert.True(error.Message.Contains("cleanup incomplete", StringComparison.Ordinal),
                "Cleanup did not report incomplete owned work.");
            Assert.Equal(before.IncompleteCleanups + 1, observeCounters().IncompleteCleanups);
            settling = awaitSettlementAsync(CancellationToken.None).AsTask();
            Assert.False(settling.IsCompleted);
            Assert.Equal(MetadataFailureCode.Disposed, Failed(await store.ReserveOperationAsync(new(), cancellationToken)));
        }
        finally
        {
            barrier.Release();
            try
            {
                await JoinSettlement(Task.WhenAll(committing, disposing ?? Task.CompletedTask,
                    settling ?? Task.CompletedTask), awaitSettlementAsync);
            }
            finally { await disposeAsync().AsTask().WaitAsync(TimeSpan.FromSeconds(35)); }
        }
    }

    public static async Task WriterBudgetAsync(
        IMetadataStore store, Func<CancellationToken, ValueTask<IAsyncDisposable>> holdWriterAsync,
        Func<CancellationToken, ValueTask> awaitSettlementAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(holdWriterAsync);
        ArgumentNullException.ThrowIfNull(awaitSettlementAsync);
        var batch = Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        try
        {
            await using (var writer = await holdWriterAsync(cancellationToken))
            {
                var elapsed = Stopwatch.StartNew();
                Assert.Equal(MetadataFailureCode.DeadlineExceeded, Failed(await store.CommitAsync(
                    batch, new(TimeSpan.FromMilliseconds(50)), cancellationToken)));
                Assert.True(elapsed.Elapsed < TimeSpan.FromSeconds(2));
                await awaitSettlementAsync(cancellationToken);
                await Missing(store, Registry().Selector, cancellationToken);
            }
        }
        finally { await awaitSettlementAsync(CancellationToken.None); }
        Success(await store.CommitAsync(batch, new(), cancellationToken));
        await Read<MetadataRegistry>(store, Registry().Selector, cancellationToken);
    }

    public static async Task CancellationDecisionsAsync(
        IMetadataStore store, MetadataObservationControl observeAsync,
        Func<CancellationToken, ValueTask> awaitSettlementAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        ArgumentNullException.ThrowIfNull(awaitSettlementAsync);
        using var alreadyCancelled = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        alreadyCancelled.Cancel();
        try
        {
            Assert.Equal(MetadataFailureCode.CancelledBeforeCommit, Failed(await store.ReserveOperationAsync(new(), alreadyCancelled.Token)));
        }
        finally { await awaitSettlementAsync(CancellationToken.None); }
        foreach (var point in new[] { MetadataObservationPoint.BeforeCommitDecision, MetadataObservationPoint.AfterCommitDecision })
        {
            await using var barrier = new MetadataConformanceBarrier();
            using var cancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            var registry = Registry(point == MetadataObservationPoint.BeforeCommitDecision ? 1 : 2);
            var batch = Batch(await Ticket(store, cancellationToken),
                new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
            await using (var observation = await observeAsync(point, barrier.HoldAsync, cancellationToken))
            {
                var committing = store.CommitAsync(batch, new(), cancellation.Token).AsTask();
                try
                {
                    await barrier.WaitForEntryAsync(cancellationToken);
                    cancellation.Cancel();
                    Assert.Equal(point == MetadataObservationPoint.BeforeCommitDecision
                        ? MetadataFailureCode.CancelledBeforeCommit : MetadataFailureCode.Uncertain, Failed(await committing));
                    Assert.Equal(MetadataFailureCode.Unavailable, Failed(await store.ReserveOperationAsync(new(), cancellationToken)));
                }
                finally
                {
                    barrier.Release();
                    await JoinSettlement(committing, awaitSettlementAsync);
                }
            }
            var resolution = Success(await store.ReconcileAsync(batch.Ticket, new(), cancellationToken));
            if (point == MetadataObservationPoint.BeforeCommitDecision)
            {
                Assert.IsType<MetadataResolution.NotCommitted>(resolution);
                await Missing(store, registry.Selector, cancellationToken);
            }
            else
            {
                Assert.IsType<MetadataResolution.Committed>(resolution);
                await Read<MetadataRegistry>(store, registry.Selector, cancellationToken);
            }
        }
    }

    public static async Task QueueCapacityAsync(
        IMetadataStore store, MetadataObservationControl observeAsync,
        Func<CancellationToken, ValueTask> awaitSettlementAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        ArgumentNullException.ThrowIfNull(awaitSettlementAsync);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var observation = await observeAsync(MetadataObservationPoint.ReadItem,
            () => { entered.TrySetResult(); return new(release.Task); }, cancellationToken);
        var reads = new List<Task<MetadataResult<MetadataReadSnapshot>>>();
        try
        {
            reads.Add(store.ReadAsync(new([Registry().Selector]), new(TimeSpan.FromMilliseconds(200)), cancellationToken).AsTask());
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(10), cancellationToken);
            for (var index = 0; index < 32; index++)
            { reads.Add(store.ReadAsync(new([Registry().Selector]), new(), cancellationToken).AsTask()); }
            Assert.Equal(MetadataFailureCode.Capacity, Failed(await store.ReadAsync(new([Registry().Selector]), new(), cancellationToken)));
            Assert.Equal(MetadataFailureCode.DeadlineExceeded, Failed(await reads[0]));
            Assert.Equal(MetadataFailureCode.Unavailable, Failed(await store.ReserveOperationAsync(new(), cancellationToken)));
        }
        finally
        {
            release.TrySetResult();
            await JoinSettlement(Task.WhenAll(reads).WaitAsync(TimeSpan.FromSeconds(10)), awaitSettlementAsync);
        }
        await Ticket(store, cancellationToken);
    }

    public static async Task DisposalOwnershipAsync(
        IMetadataStore store, MetadataObservationControl observeAsync,
        Func<ValueTask> disposeAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        ArgumentNullException.ThrowIfNull(disposeAsync);
        await using var barrier = new MetadataConformanceBarrier();
        var batch = Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        await using var observation = await observeAsync(
            MetadataObservationPoint.BeforeCommitDecision, barrier.HoldAsync, cancellationToken);
        var committing = store.CommitAsync(batch, new(), cancellationToken).AsTask();
        Task? disposing = null;
        try
        {
            await barrier.WaitForEntryAsync(cancellationToken);
            disposing = disposeAsync().AsTask();
            Assert.False(disposing.IsCompleted);
            Assert.Equal(MetadataFailureCode.Disposed, Failed(await store.ReserveOperationAsync(new(), cancellationToken)));
        }
        finally
        {
            barrier.Release();
            if (disposing is null) { await committing; }
            else { await Task.WhenAll(committing, disposing); }
        }
    }

    public static async Task KnownExceptionsAsync(
        IMetadataStore store, MetadataObservationControl observeAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        foreach (var exception in new Exception[] { new ArgumentException(MetadataReconciliationAssertions.CorruptionCanary),
            new OverflowException(MetadataReconciliationAssertions.CorruptionCanary),
            new IOException(MetadataReconciliationAssertions.CorruptionCanary) })
        {
            var registry = Registry(exception is ArgumentException ? 11 : exception is OverflowException ? 12 : 13);
            var batch = Batch(await Ticket(store, cancellationToken),
                new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
            var observed = 0;
            MetadataResult<MetadataCommitReceipt> result;
            await using (var observation = await observeAsync(MetadataObservationPoint.AfterCommitDecision, () =>
            {
                Interlocked.Increment(ref observed);
                throw exception;
            }, cancellationToken))
            { result = await store.CommitAsync(batch, new(), cancellationToken); }
            Assert.Equal(1, observed);
            Assert.Equal(MetadataFailureCode.Uncertain, Failed(result));
            Assert.Equal(batch.Ticket, Assert.IsType<MetadataOption<MetadataOperationTicket>.Some>(
                Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(result).Ticket).Value);
            Assert.IsType<MetadataResolution.Committed>(Success(await store.ReconcileAsync(batch.Ticket, new(), cancellationToken)));
            await Read<MetadataRegistry>(store, registry.Selector, cancellationToken);
        }
    }
}
