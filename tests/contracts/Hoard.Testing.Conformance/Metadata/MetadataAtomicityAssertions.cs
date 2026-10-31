using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataAtomicityAssertions
{
    public static async Task IndependentCandidateAsync(
        IMetadataStore store, MetadataObservationControl observeAsync,
        Func<MetadataReadGroup, CancellationToken, ValueTask<MetadataResult<MetadataReadSnapshot>>> independentReadAsync,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        ArgumentNullException.ThrowIfNull(independentReadAsync);
        await using var barrier = new MetadataConformanceBarrier();
        var group = new MetadataReadGroup([Registry().Selector, Registry(2).Selector]);
        await using var observation = await observeAsync(
            MetadataObservationPoint.BeforeCommitDecision, barrier.HoldAsync, cancellationToken);
        var committing = Commit(store, cancellationToken,
            new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(Registry(2), new ExpectedRevision.Absent())).AsTask();
        try
        {
            await barrier.WaitForEntryAsync(cancellationToken);
            var before = Success(await independentReadAsync(group, cancellationToken));
            Assert.Equal(2, before.Items.Length);
            Assert.All(before.Items, item => Assert.IsType<MetadataReadItem.NotFound>(item));
        }
        finally { barrier.Release(); await committing; }
        var after = Success(await independentReadAsync(group, cancellationToken));
        Assert.Equal(2, after.Items.Length);
        Assert.All(after.Items, item => Assert.IsType<MetadataReadItem.Found>(item));
    }

    public static async Task FaultedCandidatesAsync(
        IMetadataStore store, MetadataObservationControl observeAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        for (var fault = 1; fault <= 3; fault++)
        {
            var seen = 0;
            await using var observation = await observeAsync(MetadataObservationPoint.MutationApplied, () =>
            {
                if (++seen == fault) { throw new InvalidOperationException(MetadataReconciliationAssertions.CorruptionCanary); }
                return ValueTask.CompletedTask;
            }, cancellationToken);
            var mutations = Enumerable.Range(1, 3).Select(number =>
                (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray();
            Assert.Equal(MetadataFailureCode.InternalFailure, Failed(await store.CommitAsync(
                Batch(await Ticket(store, cancellationToken), mutations), new(), cancellationToken)));
            Assert.Equal(fault, seen);
            foreach (var number in Enumerable.Range(1, 3)) { await Missing(store, Registry(number).Selector, cancellationToken); }
        }
        await Commit(store, cancellationToken, Enumerable.Range(1, 3).Select(number =>
            (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray());
        Assert.Equal(3, (await Traverse(store, Registries(), cancellationToken)).Length);
    }

    public static async Task GroupedReadsAsync(
        IMetadataStore store, MetadataObservationControl observeAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        await using var barrier = new MetadataConformanceBarrier();
        var first = Registry();
        var second = Registry(2);
        await Commit(store, cancellationToken, new MetadataMutation.PutRegistry(first, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(second, new ExpectedRevision.Absent()));
        first = await Read<MetadataRegistry>(store, first.Selector, cancellationToken);
        second = await Read<MetadataRegistry>(store, second.Selector, cancellationToken);
        var once = 0;
        await using (var observation = await observeAsync(MetadataObservationPoint.ReadItem,
            () => Interlocked.Increment(ref once) == 1 ? barrier.HoldAsync() : ValueTask.CompletedTask, cancellationToken))
        {
            var reading = store.ReadAsync(new([first.Selector, second.Selector]), new(), cancellationToken).AsTask();
            Task<MetadataCommitReceipt>? writing = null;
            try
            {
                await barrier.WaitForEntryAsync(cancellationToken);
                writing = Commit(store, cancellationToken,
                    new MetadataMutation.PutRegistry(first with { Label = new("new") }, new ExpectedRevision.Match(first.Revision)),
                    new MetadataMutation.PutRegistry(second with { Label = new("new") }, new ExpectedRevision.Match(second.Revision))).AsTask();
                barrier.Release();
                var old = Success(await reading);
                Assert.Equal(2, old.Items.Length);
                Assert.All(old.Items, item => Assert.Equal("synthetic registry",
                    Assert.IsType<MetadataRegistry>(Assert.IsType<MetadataReadItem.Found>(item).Record).Label.Value));
            }
            finally
            {
                barrier.Release();
                if (writing is null) { await reading; }
                else { await Task.WhenAll(reading, writing); }
            }
        }
        var snapshot = Success(await store.ReadAsync(new([first.Selector, second.Selector]), new(), cancellationToken));
        Assert.Equal(2, snapshot.Items.Length);
        Assert.All(snapshot.Items, item => Assert.Equal("new",
            Assert.IsType<MetadataRegistry>(Assert.IsType<MetadataReadItem.Found>(item).Record).Label.Value));
        var before = await Read<MetadataRegistry>(store, first.Selector, cancellationToken);
        var current = await Read<MetadataRegistry>(store, second.Selector, cancellationToken);
        await Commit(store, cancellationToken,
            new MetadataMutation.PutRegistry(current with { Label = new("later") }, new ExpectedRevision.Match(current.Revision)));
        Assert.NotEqual(before.Label, (await Read<MetadataRegistry>(store, second.Selector, cancellationToken)).Label);
    }
}
