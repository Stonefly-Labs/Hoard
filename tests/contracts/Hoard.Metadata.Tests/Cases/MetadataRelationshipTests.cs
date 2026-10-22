using Hoard.Abstractions.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataRelationshipTests
{
    [Fact]
    public async Task MP13_Explicit_final_graph_deletion_and_disabled_retention_are_atomic()
    {
        await using var fixture = await OpenAsync();
        var (registry, package) = await Seed(fixture);
        var entry = Entry(package);
        await Commit(fixture, Publish(fixture, entry));
        entry = await Read<MetadataCacheEntry>(fixture, entry.Selector);
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.DeleteRegistry(registry.Id, registry.Revision)), new(), default)));
        Assert.Equal(registry, await Read<MetadataRegistry>(fixture, registry.Selector));
        await Commit(fixture, new MetadataMutation.PutRegistry(registry with { Enabled = false }, new ExpectedRevision.Match(registry.Revision)));
        registry = await Read<MetadataRegistry>(fixture, registry.Selector);
        await Read<MetadataCacheEntry>(fixture, entry.Selector);
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            Publish(fixture, Entry(package, target: "/another"))), new(), default)));
        await Missing(fixture, Entry(package, target: "/another").Selector);
        await Commit(fixture, new MetadataMutation.DeleteRegistry(registry.Id, registry.Revision),
            new MetadataMutation.DeletePackage(package.Key, package.Revision),
            new MetadataMutation.DeleteCacheEntry(entry.Identity, entry.Revision));
        await Missing(fixture, registry.Selector);
        await Missing(fixture, package.Selector);
        await Missing(fixture, entry.Selector);
        Assert.Equal(0, (await Read<MetadataArtifactState>(fixture, new MetadataSelector.Artifact(entry.Digest))).LiveReferences);
    }
}
