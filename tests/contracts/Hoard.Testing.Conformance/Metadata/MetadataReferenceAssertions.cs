using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataReferenceAssertions
{
    public static async Task EntryReplacementAndRemovalAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, CancellationToken cancellationToken)
    {
        var (_, package) = await Seed(store, cancellationToken);
        var first = Entry(package);
        var second = Entry(package, target: "/second");
        await Commit(store, cancellationToken, Publish(authority, first), Publish(authority, second));
        Assert.Equal(2, (await Read<MetadataArtifactState>(store, new MetadataSelector.Artifact(first.Digest), cancellationToken)).LiveReferences);
        first = await Read<MetadataCacheEntry>(store, first.Selector, cancellationToken);
        var replacement = first with { Digest = Digest(2) };
        var tickets = await Task.WhenAll(Enumerable.Range(0, 4).Select(async _ => await Ticket(store, cancellationToken)));
        var outcomes = await Task.WhenAll(tickets.Select(ticket => store.CommitAsync(Batch(ticket,
            Publish(authority, replacement, new ExpectedRevision.Match(first.Revision))), new(), cancellationToken).AsTask()));
        Assert.Single(outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Success>());
        Assert.Equal(3, outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Failure>().Count(result => result.Code == MetadataFailureCode.Conflict));
        Assert.Equal(1, (await Read<MetadataArtifactState>(store, new MetadataSelector.Artifact(first.Digest), cancellationToken)).LiveReferences);
        Assert.Equal(1, (await Read<MetadataArtifactState>(store, new MetadataSelector.Artifact(replacement.Digest), cancellationToken)).LiveReferences);
        first = await Read<MetadataCacheEntry>(store, first.Selector, cancellationToken);
        second = await Read<MetadataCacheEntry>(store, second.Selector, cancellationToken);
        await Commit(store, cancellationToken, new MetadataMutation.DeleteCacheEntry(first.Identity, first.Revision),
            new MetadataMutation.DeleteCacheEntry(second.Identity, second.Revision));
        Assert.Equal(0, (await Read<MetadataArtifactState>(store, new MetadataSelector.Artifact(first.Digest), cancellationToken)).LiveReferences);
        Assert.Equal(0, (await Read<MetadataArtifactState>(store, new MetadataSelector.Artifact(second.Digest), cancellationToken)).LiveReferences);
    }

    public static async Task ZeroReferenceAbaFencingAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, CancellationToken cancellationToken)
    {
        var (_, package) = await Seed(store, cancellationToken);
        var entry = Entry(package);
        await Commit(store, cancellationToken, Publish(authority, entry));
        entry = await Read<MetadataCacheEntry>(store, entry.Selector, cancellationToken);
        await Commit(store, cancellationToken, new MetadataMutation.DeleteCacheEntry(entry.Identity, entry.Revision));
        var zero = await Read<MetadataArtifactState>(store, new MetadataSelector.Artifact(entry.Digest), cancellationToken);
        await Commit(store, cancellationToken, new MetadataMutation.ConfirmUnreferenced(entry.Digest, zero.Revision));
        await Commit(store, cancellationToken, Publish(authority, entry));
        entry = await Read<MetadataCacheEntry>(store, entry.Selector, cancellationToken);
        await Commit(store, cancellationToken, new MetadataMutation.DeleteCacheEntry(entry.Identity, entry.Revision));
        var again = await Read<MetadataArtifactState>(store, zero.Selector, cancellationToken);
        Assert.NotEqual(zero.Revision, again.Revision);
        Assert.Equal(0, again.LiveReferences);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.ConfirmUnreferenced(entry.Digest, zero.Revision)), new(), cancellationToken)));
        await Commit(store, cancellationToken, new MetadataMutation.ConfirmUnreferenced(entry.Digest, again.Revision));
    }

    public static async Task InvalidTelemetryRollsBackEntryAndReferencesAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, CancellationToken cancellationToken)
    {
        var (registry, package) = await Seed(store, cancellationToken);
        var entry = Entry(package);
        var delta = Delta() with { Hits = -1 };
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            Publish(authority, entry), new MetadataMutation.AddAggregateContribution(Aggregate(registry), delta)),
            new(), cancellationToken)));
        await Missing(store, entry.Selector, cancellationToken);
        await Missing(store, new MetadataSelector.Artifact(entry.Digest), cancellationToken);
        await Commit(store, cancellationToken, Publish(authority, entry),
            new MetadataMutation.AddAggregateContribution(Aggregate(registry), Delta()));
        Assert.Equal(1, (await Read<MetadataArtifactState>(store, new MetadataSelector.Artifact(entry.Digest), cancellationToken)).LiveReferences);
        Assert.Equal(1, (await Read<MetadataAccessAggregate>(store, new MetadataSelector.Aggregate(Aggregate(registry)), cancellationToken)).Counters.Hits);
    }
}
