using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataReconciliationAssertions
{
    public const string CorruptionCanary = "f07-synthetic-corrupt-receipt";

    public static async Task WriterContentionAsync(
        IMetadataStore store, Func<CancellationToken, ValueTask<IAsyncDisposable>> holdWriterAsync,
        Func<CancellationToken, ValueTask> awaitSettlementAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(holdWriterAsync);
        ArgumentNullException.ThrowIfNull(awaitSettlementAsync);
        var batch = Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        var receipt = Success(await store.CommitAsync(batch, new(), cancellationToken));
        try
        {
            await using (var writer = await holdWriterAsync(cancellationToken))
            {
                using var cancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
                cancellation.Cancel();
                foreach (var token in new[] { cancellationToken, cancellation.Token })
                {
                    var failure = Assert.IsType<MetadataResult<MetadataResolution>.Failure>(
                        await store.ReconcileAsync(batch.Ticket, new(TimeSpan.FromMilliseconds(50)), token));
                    Assert.Equal(MetadataFailureCode.Uncertain, failure.Code);
                    Assert.Equal(MetadataPhase.Reconcile, failure.Phase);
                    Assert.Equal(MetadataRetryDisposition.Reconcile, failure.Retry);
                    Assert.Equal(batch.Ticket, Assert.IsType<MetadataOption<MetadataOperationTicket>.Some>(failure.Ticket).Value);
                    await awaitSettlementAsync(cancellationToken);
                }
            }
        }
        finally { await awaitSettlementAsync(CancellationToken.None); }
        Assert.Equal<byte>(MetadataEncoding.Encode(receipt), MetadataEncoding.Encode(
            Assert.IsType<MetadataResolution.Committed>(
                Success(await store.ReconcileAsync(batch.Ticket, new(), cancellationToken))).Receipt));
    }

    public static async Task IoFailureAsync(
        IMetadataStore store, MetadataObservationControl observeAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        var ticket = await Ticket(store, cancellationToken);
        var observed = 0;
        await using (var observation = await observeAsync(MetadataObservationPoint.BeforeReconciliationDecision,
            () =>
            {
                Interlocked.Increment(ref observed);
                throw new IOException(CorruptionCanary);
            }, cancellationToken))
        {
            var failure = Assert.IsType<MetadataResult<MetadataResolution>.Failure>(
                await store.ReconcileAsync(ticket, new(), cancellationToken));
            Assert.Equal(MetadataFailureCode.Uncertain, failure.Code);
            Assert.Equal(MetadataRetryDisposition.Reconcile, failure.Retry);
            Assert.Equal(MetadataPhase.Reconcile, failure.Phase);
            Assert.Equal(ticket, Assert.IsType<MetadataOption<MetadataOperationTicket>.Some>(failure.Ticket).Value);
            Assert.DoesNotContain(CorruptionCanary, failure.ToString());
            Assert.Equal(1, observed);
        }
        Success(await store.CommitAsync(Batch(ticket,
            new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent())), new(), cancellationToken));
        await Read<MetadataRegistry>(store, Registry().Selector, cancellationToken);
    }

    public static async Task LostAcknowledgmentAndAbandonmentAsync(
        IMetadataStore store, MetadataObservationControl observeAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        var batch = Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        await LoseAcknowledgment(store, observeAsync, batch, cancellationToken);
        var resolved = Assert.IsType<MetadataResolution.Committed>(
            Success(await store.ReconcileAsync(batch.Ticket, new(), cancellationToken)));
        Assert.Equal(resolved.Receipt.CommitId, Success(await store.CommitAsync(batch, new(), cancellationToken)).CommitId);
        var abandoned = await Ticket(store, cancellationToken);
        Assert.Equal(abandoned, Assert.IsType<MetadataResolution.NotCommitted>(
            Success(await store.ReconcileAsync(abandoned, new(), cancellationToken))).AbandonedTicket);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await store.CommitAsync(Batch(abandoned,
            new MetadataMutation.PutRegistry(Registry(2), new ExpectedRevision.Absent())), new(), cancellationToken)));
        await Missing(store, Registry(2).Selector, cancellationToken);
    }

    public static async Task DistinctContributionsAsync(
        IMetadataStore store, MetadataObservationControl observeAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        var (registry, _) = await Seed(store, cancellationToken);
        var key = Aggregate(registry);
        var batch = Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.AddAggregateContribution(key, Delta(3)));
        await LoseAcknowledgment(store, observeAsync, batch, cancellationToken);
        var original = Assert.IsType<MetadataResolution.Committed>(
            Success(await store.ReconcileAsync(batch.Ticket, new(), cancellationToken))).Receipt;
        Assert.Equal(original.CommitId, Success(await store.CommitAsync(batch, new(), cancellationToken)).CommitId);
        var tickets = await Task.WhenAll(Enumerable.Range(1, 8).Select(async _ => await Ticket(store, cancellationToken)));
        var outcomes = await Task.WhenAll(tickets.Select(ticket => store.CommitAsync(
            Batch(ticket, new MetadataMutation.AddAggregateContribution(key, Delta(2))), new(), cancellationToken).AsTask()));
        Assert.All(outcomes, result => Success(result));
        Assert.Equal(19, (await Read<MetadataAccessAggregate>(store, new MetadataSelector.Aggregate(key), cancellationToken)).Counters.Hits);
    }

    private static async Task LoseAcknowledgment(
        IMetadataStore store, MetadataObservationControl observeAsync, MetadataMutationBatch batch, CancellationToken cancellationToken)
    {
        var observed = 0;
        await using var observation = await observeAsync(MetadataObservationPoint.AfterCommitDecision, () =>
        {
            Interlocked.Increment(ref observed);
            throw new InvalidOperationException(CorruptionCanary);
        }, cancellationToken);
        var failure = Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(
            await store.CommitAsync(batch, new(), cancellationToken));
        Assert.Equal(MetadataFailureCode.Uncertain, failure.Code);
        Assert.Equal(MetadataRetryDisposition.Reconcile, failure.Retry);
        Assert.Equal(MetadataPhase.Commit, failure.Phase);
        Assert.Equal(batch.Ticket, Assert.IsType<MetadataOption<MetadataOperationTicket>.Some>(failure.Ticket).Value);
        Assert.DoesNotContain(CorruptionCanary, failure.ToString());
        Assert.Equal(1, observed);
    }

    public static async Task CorruptReceiptsAsync(
        IMetadataStore store,
        Func<MetadataCorruptionRequest, CancellationToken, ValueTask<IMetadataCorruptionScope>> corruptAsync,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(corruptAsync);
        var (registry, _) = await Seed(store, cancellationToken);
        var key = Aggregate(registry);
        var batch = Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.AddAggregateContribution(key, Delta(3)));
        var original = Success(await store.CommitAsync(batch, new(), cancellationToken));
        var foreign = await Ticket(store, cancellationToken);
        foreach (var corruption in Enum.GetValues<MetadataOperationCorruption>())
        {
            await using (var scope = await corruptAsync(new MetadataCorruptionRequest.Operation(
                batch.Ticket, corruption, foreign), cancellationToken))
            {
                var damaged = await scope.ObserveAsync(cancellationToken);
                Assert.NotEqual(scope.Original, damaged);
                var resolution = Assert.IsType<MetadataResult<MetadataResolution>.Failure>(
                    await store.ReconcileAsync(batch.Ticket, new(), cancellationToken));
                var replay = Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(
                    await store.CommitAsync(batch, new(), cancellationToken));
                AssertFailure(resolution, MetadataPhase.Reconcile);
                AssertFailure(replay, MetadataPhase.Commit);
                Assert.Equal(damaged, await scope.ObserveAsync(cancellationToken));
                await AssertEffects();
            }
            await AssertOriginal();
        }
        await AssertOriginal();
        await AssertEffects();
        Assert.Equal(foreign, Assert.IsType<MetadataResolution.NotCommitted>(
            Success(await store.ReconcileAsync(foreign, new(), cancellationToken))).AbandonedTicket);

        void AssertFailure<T>(MetadataResult<T>.Failure failure, MetadataPhase phase) where T : notnull
        {
            CorruptFailure<T>(failure, phase);
            Assert.Equal(batch.Ticket, Assert.IsType<MetadataOption<MetadataOperationTicket>.Some>(failure.Ticket).Value);
        }
        async Task AssertEffects() =>
            Assert.Equal(3, (await Read<MetadataAccessAggregate>(store,
                new MetadataSelector.Aggregate(key), cancellationToken)).Counters.Hits);
        async Task AssertOriginal()
        {
            Assert.Equal<byte>(MetadataEncoding.Encode(original), MetadataEncoding.Encode(
                Success(await store.CommitAsync(batch, new(), cancellationToken))));
            Assert.Equal<byte>(MetadataEncoding.Encode(original), MetadataEncoding.Encode(
                Assert.IsType<MetadataResolution.Committed>(
                    Success(await store.ReconcileAsync(batch.Ticket, new(), cancellationToken))).Receipt));
        }
    }
}
