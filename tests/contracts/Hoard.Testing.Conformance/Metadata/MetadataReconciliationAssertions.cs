using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataReconciliationAssertions
{
    public const string CorruptionCanary = "f07-synthetic-corrupt-receipt";

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
