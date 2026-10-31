using Hoard.Abstractions.Metadata;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataBoundsAssertions
{
    public static async Task ExactBoundsAsync(IMetadataStore store, CancellationToken cancellationToken)
    {
        var (registry, _) = await Seed(store, cancellationToken);
        var key = Aggregate(registry);
        await Commit(store, cancellationToken, new MetadataMutation.AddAggregateContribution(key, Delta(long.MaxValue)));
        var original = await Read<MetadataAccessAggregate>(store, new MetadataSelector.Aggregate(key), cancellationToken);
        var extra = Registry(45);
        Assert.Equal(MetadataFailureCode.Capacity, Failed(await store.CommitAsync(
            Batch(await Ticket(store, cancellationToken), new MetadataMutation.PutRegistry(extra, new ExpectedRevision.Absent()),
                new MetadataMutation.AddAggregateContribution(key, Delta())), new(), cancellationToken)));
        await Missing(store, extra.Selector, cancellationToken);
        Assert.Equal(original, await Read<MetadataAccessAggregate>(store, original.Selector, cancellationToken));
        Assert.Equal(253402300799999, new MetadataInstant(253402300799999).UnixMilliseconds);
        Assert.Throws<ArgumentException>(() => new MetadataInstant(DateTimeOffset.UnixEpoch.AddTicks(1)));
        Assert.Throws<ArgumentException>(() => new MetadataInstant(DateTimeOffset.UnixEpoch.ToOffset(TimeSpan.FromHours(1))));
        Assert.Throws<ArgumentException>(() => new MetadataInstant(253402300800000));
    }

    public static async Task ScopesAndIntervalsAsync(IMetadataStore store, CancellationToken cancellationToken)
    {
        var one = Registry();
        var two = Registry(2);
        var scoped = Policy() with { Scope = new MetadataPolicyScope.Registry(one.Id) };
        await Commit(store, cancellationToken, new MetadataMutation.PutRegistry(one, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(two, new ExpectedRevision.Absent()), new MetadataMutation.PutPolicy(scoped, new ExpectedRevision.Absent()),
            new MetadataMutation.AddAggregateContribution(Aggregate(one), Delta(3)),
            new MetadataMutation.AddAggregateContribution(Aggregate(two), Delta(7)));
        two = await Read<MetadataRegistry>(store, two.Selector, cancellationToken);
        Assert.Equal(3, (await Read<MetadataAccessAggregate>(store, new MetadataSelector.Aggregate(Aggregate(one)), cancellationToken)).Counters.Hits);
        Assert.Equal(7, (await Read<MetadataAccessAggregate>(store, new MetadataSelector.Aggregate(Aggregate(two)), cancellationToken)).Counters.Hits);
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.PutRegistry(two with { PolicyId = new MetadataOption<MetadataId>.Some(scoped.Id) },
                new ExpectedRevision.Match(two.Revision))), new(), cancellationToken)));
        var badKey = Aggregate(one) with { End = new(86400001) };
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.AddAggregateContribution(badKey, Delta())), new(), cancellationToken)));
        Assert.Equal(3, (await Read<MetadataAccessAggregate>(store, new MetadataSelector.Aggregate(Aggregate(one)), cancellationToken)).Counters.Hits);
    }
}
