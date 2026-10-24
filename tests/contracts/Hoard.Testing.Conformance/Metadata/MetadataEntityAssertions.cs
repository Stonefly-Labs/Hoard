using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataEntityAssertions
{
    public static async Task RoundTripAndInvalidRelationshipsAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, CancellationToken cancellationToken)
    {
        var (registry, package) = await Seed(store, cancellationToken);
        var policy = Policy();
        var scoped = Policy(10) with { Scope = new MetadataPolicyScope.Registry(registry.Id) };
        var replacement = registry with
        {
            PolicyId = new MetadataOption<MetadataId>.Some(scoped.Id),
            Secret = new MetadataOption<MetadataSecretReference>.Some(new("fixture.metadata", "fixture.secret", "opaque-key"))
        };
        var entry = Entry(package);
        var aggregate = Aggregate(registry);
        await Commit(store, cancellationToken, new MetadataMutation.PutRegistry(replacement, new ExpectedRevision.Match(registry.Revision)),
            new MetadataMutation.PutPolicy(scoped, new ExpectedRevision.Absent()), new MetadataMutation.PutPolicy(policy, new ExpectedRevision.Absent()),
            Publish(authority, entry), new MetadataMutation.AcquireLease(new("maintenance"), Id(11), 300),
            new MetadataMutation.AddAggregateContribution(aggregate, Delta()));
        var actual = await Read<MetadataRegistry>(store, registry.Selector, cancellationToken);
        Assert.Equal(replacement with { Revision = actual.Revision }, actual);
        var actualPackage = await Read<MetadataPackage>(store, package.Selector, cancellationToken);
        Assert.Equal(package, actualPackage);
        var actualPolicy = await Read<MetadataPolicy>(store, scoped.Selector, cancellationToken);
        Assert.Equal(scoped with { Revision = actualPolicy.Revision }, actualPolicy);
        var actualEntry = await Read<MetadataCacheEntry>(store, entry.Selector, cancellationToken);
        Assert.True(MetadataEncoding.Encode(entry with { Revision = actualEntry.Revision }).AsSpan()
            .SequenceEqual(MetadataEncoding.Encode(actualEntry).AsSpan()));
        Assert.Equal(1, (await Read<MetadataArtifactState>(store, new MetadataSelector.Artifact(entry.Digest), cancellationToken)).LiveReferences);
        Assert.Equal(1, (await Read<MetadataAccessAggregate>(store, new MetadataSelector.Aggregate(aggregate), cancellationToken)).Counters.Hits);
        Assert.Equal(1, (await Read<MetadataWorkLease>(store, new MetadataSelector.Lease(new("maintenance")), cancellationToken)).Generation);
        var invalid = Package(Registry(99));
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.CommitAsync(
            Batch(await Ticket(store, cancellationToken), new MetadataMutation.PutPackage(invalid, new ExpectedRevision.Absent())),
            new(), cancellationToken)));
        await Missing(store, invalid.Selector, cancellationToken);
        Assert.Equal(actual, await Read<MetadataRegistry>(store, registry.Selector, cancellationToken));
    }

    public static async Task FinalGraphDeletionAndDisabledRetentionAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, CancellationToken cancellationToken)
    {
        var (registry, package) = await Seed(store, cancellationToken);
        var entry = Entry(package);
        await Commit(store, cancellationToken, Publish(authority, entry));
        entry = await Read<MetadataCacheEntry>(store, entry.Selector, cancellationToken);
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.DeleteRegistry(registry.Id, registry.Revision)), new(), cancellationToken)));
        Assert.Equal(registry, await Read<MetadataRegistry>(store, registry.Selector, cancellationToken));
        await Commit(store, cancellationToken, new MetadataMutation.PutRegistry(
            registry with { Enabled = false }, new ExpectedRevision.Match(registry.Revision)));
        registry = await Read<MetadataRegistry>(store, registry.Selector, cancellationToken);
        await Read<MetadataCacheEntry>(store, entry.Selector, cancellationToken);
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            Publish(authority, Entry(package, target: "/another"))), new(), cancellationToken)));
        await Missing(store, Entry(package, target: "/another").Selector, cancellationToken);
        await Commit(store, cancellationToken, new MetadataMutation.DeleteRegistry(registry.Id, registry.Revision),
            new MetadataMutation.DeletePackage(package.Key, package.Revision),
            new MetadataMutation.DeleteCacheEntry(entry.Identity, entry.Revision));
        await Missing(store, registry.Selector, cancellationToken);
        await Missing(store, package.Selector, cancellationToken);
        await Missing(store, entry.Selector, cancellationToken);
        Assert.Equal(0, (await Read<MetadataArtifactState>(store, new MetadataSelector.Artifact(entry.Digest), cancellationToken)).LiveReferences);
    }
}
