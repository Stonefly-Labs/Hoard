using Hoard.Abstractions.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataRoundTripTests
{
    [Fact]
    public async Task MP01_Every_entity_round_trips_and_invalid_relationships_leave_no_changes()
    {
        await using var fixture = await OpenAsync();
        var (registry, package) = await Seed(fixture);
        var policy = Policy();
        var scoped = Policy(10) with { Scope = new MetadataPolicyScope.Registry(registry.Id) };
        var replacement = registry with
        {
            PolicyId = new MetadataOption<MetadataId>.Some(scoped.Id),
            Secret = new MetadataOption<MetadataSecretReference>.Some(new("fixture.metadata", "fixture.secret", "opaque-key"))
        };
        var entry = Entry(package);
        var aggregate = Aggregate(registry);
        await Commit(fixture, new MetadataMutation.PutRegistry(replacement, new ExpectedRevision.Match(registry.Revision)),
            new MetadataMutation.PutPolicy(scoped, new ExpectedRevision.Absent()), new MetadataMutation.PutPolicy(policy, new ExpectedRevision.Absent()),
            Publish(fixture, entry), new MetadataMutation.AcquireLease(new("maintenance"), Id(11), 300),
            new MetadataMutation.AddAggregateContribution(aggregate, Delta()));
        var actual = await Read<MetadataRegistry>(fixture, registry.Selector);
        Assert.Equal(replacement with { Revision = actual.Revision }, actual);
        var actualPackage = await Read<MetadataPackage>(fixture, package.Selector);
        Assert.Equal(package, actualPackage);
        var actualPolicy = await Read<MetadataPolicy>(fixture, scoped.Selector);
        Assert.Equal(scoped with { Revision = actualPolicy.Revision }, actualPolicy);
        var actualEntry = await Read<MetadataCacheEntry>(fixture, entry.Selector);
        Assert.True(MetadataEncoding.Encode(entry with { Revision = actualEntry.Revision }).AsSpan()
            .SequenceEqual(MetadataEncoding.Encode(actualEntry).AsSpan()));
        Assert.Equal(1, (await Read<MetadataArtifactState>(fixture, new MetadataSelector.Artifact(entry.Digest))).LiveReferences);
        Assert.Equal(1, (await Read<MetadataAccessAggregate>(fixture, new MetadataSelector.Aggregate(aggregate))).Counters.Hits);
        Assert.Equal(1, (await Read<MetadataWorkLease>(fixture, new MetadataSelector.Lease(new("maintenance")))).Generation);
        var invalid = Package(Registry(99));
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.CommitAsync(
            Batch(await Ticket(fixture), new MetadataMutation.PutPackage(invalid, new ExpectedRevision.Absent())), new(), default)));
        await Missing(fixture, invalid.Selector);
        Assert.Equal(actual, await Read<MetadataRegistry>(fixture, registry.Selector));
    }

    [Fact]
    public async Task MP05_Exact_bounds_and_overflow_reject_the_entire_candidate()
    {
        await using var fixture = await OpenAsync();
        var (registry, _) = await Seed(fixture);
        var key = Aggregate(registry);
        await Commit(fixture, new MetadataMutation.AddAggregateContribution(key, Delta(long.MaxValue)));
        var original = await Read<MetadataAccessAggregate>(fixture, new MetadataSelector.Aggregate(key));
        var extra = Registry(45);
        Assert.Equal(MetadataFailureCode.Capacity, Failed(await fixture.Store.CommitAsync(
            Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(extra, new ExpectedRevision.Absent()),
                new MetadataMutation.AddAggregateContribution(key, Delta())), new(), default)));
        await Missing(fixture, extra.Selector);
        Assert.Equal(original, await Read<MetadataAccessAggregate>(fixture, original.Selector));
        Assert.Equal(253402300799999, new MetadataInstant(253402300799999).UnixMilliseconds);
        Assert.Throws<ArgumentException>(() => new MetadataInstant(DateTimeOffset.UnixEpoch.AddTicks(1)));
        Assert.Throws<ArgumentException>(() => new MetadataInstant(DateTimeOffset.UnixEpoch.ToOffset(TimeSpan.FromHours(1))));
        Assert.Throws<ArgumentException>(() => new MetadataInstant(253402300800000));
    }

    [Fact]
    public async Task MP06_Scopes_and_intervals_cannot_cross_registry_boundaries()
    {
        await using var fixture = await OpenAsync();
        var one = Registry();
        var two = Registry(2);
        var scoped = Policy() with { Scope = new MetadataPolicyScope.Registry(one.Id) };
        await Commit(fixture, new MetadataMutation.PutRegistry(one, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(two, new ExpectedRevision.Absent()), new MetadataMutation.PutPolicy(scoped, new ExpectedRevision.Absent()),
            new MetadataMutation.AddAggregateContribution(Aggregate(one), Delta(3)),
            new MetadataMutation.AddAggregateContribution(Aggregate(two), Delta(7)));
        two = await Read<MetadataRegistry>(fixture, two.Selector);
        Assert.Equal(3, (await Read<MetadataAccessAggregate>(fixture, new MetadataSelector.Aggregate(Aggregate(one)))).Counters.Hits);
        Assert.Equal(7, (await Read<MetadataAccessAggregate>(fixture, new MetadataSelector.Aggregate(Aggregate(two)))).Counters.Hits);
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.PutRegistry(two with { PolicyId = new MetadataOption<MetadataId>.Some(scoped.Id) },
                new ExpectedRevision.Match(two.Revision))), new(), default)));
        var badKey = Aggregate(one) with { End = new(86400001) };
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.AddAggregateContribution(badKey, Delta())), new(), default)));
        Assert.Equal(3, (await Read<MetadataAccessAggregate>(fixture, new MetadataSelector.Aggregate(Aggregate(one)))).Counters.Hits);
    }
}
