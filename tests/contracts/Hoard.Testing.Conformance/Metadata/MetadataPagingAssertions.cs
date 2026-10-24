using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataPagingAssertions
{
    public static async Task MalformedContinuationFieldsAsync(
        IMetadataStore store, MetadataContinuationCorruptionControl corruptAsync,
        MetadataContinuationCorruption corruption, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(corruptAsync);
        if (!Enum.IsDefined(corruption)) { throw new ArgumentException("BindingInvalid"); }
        await Commit(store, cancellationToken, Enumerable.Range(1, 3).Select(number =>
            (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray());
        var query = Registries(1);
        var first = Success(await store.ReadPageAsync(query, new(), cancellationToken));
        var continuation = Assert.IsType<MetadataOption<MetadataContinuation>.Some>(first.Continuation).Value;
        var valid = query with { Continuation = first.Continuation };
        foreach (var component in Enum.GetValues<MetadataContinuationComponent>())
        {
            var damaged = await corruptAsync(continuation, component, corruption, cancellationToken);
            var invalid = query with { Continuation = new MetadataOption<MetadataContinuation>.Some(damaged) };
            var failure = Assert.IsType<MetadataResult<MetadataPage>.Failure>(
                await store.ReadPageAsync(invalid, new(), cancellationToken));
            Assert.Equal(MetadataFailureCode.InvalidInput, failure.Code);
            Assert.Equal(MetadataRetryDisposition.CorrectInput, failure.Retry);
            Assert.Equal(MetadataPhase.Page, failure.Phase);
            var resumed = Success(await store.ReadPageAsync(valid, new(), cancellationToken));
            Assert.Equal(Id(2), Assert.IsType<MetadataRegistry>(Assert.Single(resumed.Records)).Id);
        }
        Assert.Equal(new[] { Id(2), Id(3) },
            (await Traverse(store, valid, cancellationToken)).Cast<MetadataRegistry>().Select(record => record.Id));
        Assert.Equal(new[] { Id(1), Id(2), Id(3) },
            (await Traverse(store, query, cancellationToken)).Cast<MetadataRegistry>().Select(record => record.Id));
    }

    public static async Task AllQueryKindsAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, CancellationToken cancellationToken)
    {
        var (registry, package) = await Seed(store, cancellationToken);
        var entry = Entry(package);
        await Commit(store, cancellationToken, Publish(authority, entry),
            new MetadataMutation.PutPolicy(Policy(), new ExpectedRevision.Absent()),
            new MetadataMutation.AcquireLease(new("maintenance-a"), Id(3), 300),
            new MetadataMutation.AddAggregateContribution(Aggregate(registry), Delta()));
        MetadataPageQuery[] queries = [
            Registries(1), new MetadataPageQuery.Packages(registry.Id) { PageSize = 1, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.CacheEntries(registry.Id, new("anonymous"), new MetadataOption<MetadataPackageKey>.Some(package.Key))
                { PageSize = 1, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Policies(new MetadataPolicyScope.Global()) { PageSize = 1, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Aggregates(registry.Id, new("anonymous"), new(0), new(86400000))
                { PageSize = 1, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Leases(new("maintenance-")) { PageSize = 1, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Artifacts { PageSize = 1, Continuation = None<MetadataContinuation>() }];
        foreach (var query in queries) { Assert.Single(await Traverse(store, query, cancellationToken)); }
        Assert.Empty(await Traverse(store, new MetadataPageQuery.Packages(Id(999))
        { PageSize = 1, Continuation = None<MetadataContinuation>() }, cancellationToken));
        Assert.Empty(await Traverse(store, new MetadataPageQuery.CacheEntries(registry.Id, new("foreign"), None<MetadataPackageKey>())
        { PageSize = 1, Continuation = None<MetadataContinuation>() }, cancellationToken));
    }

    public static async Task OversizedRequestsAndResultsAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, CancellationToken cancellationToken)
    {
        var (_, package) = await Seed(store, cancellationToken);
        var entries = Enumerable.Range(1, 64).Select(number => Entry(package, target: "/large/" + number) with
        {
            Headers = new([new("content-type", new string('<', 4000)), new("content-language", new string('<', 4000))])
        }).ToArray();
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.CommitAsync(
            Batch(await Ticket(store, cancellationToken), entries.Select(entry => (MetadataMutation)Publish(authority, entry)).ToArray()),
            new(), cancellationToken)));
        await Missing(store, entries[0].Selector, cancellationToken);
        foreach (var entry in entries) { await Commit(store, cancellationToken, Publish(authority, entry)); }
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.ReadAsync(new(
            entries.Select(entry => entry.Selector).ToImmutableArray()), new(), cancellationToken)));
        var oversized = Assert.IsType<MetadataResult<MetadataPage>.Failure>(await store.ReadPageAsync(
            new MetadataPageQuery.CacheEntries(package.Key.RegistryId, new("anonymous"), None<MetadataPackageKey>())
            { PageSize = 100, Continuation = None<MetadataContinuation>() }, new(), cancellationToken));
        Assert.Equal(MetadataFailureCode.InvalidInput, oversized.Code);
        Assert.Equal(MetadataRetryDisposition.CorrectInput, oversized.Retry);
        Assert.Equal(MetadataPhase.Page, oversized.Phase);
        var small = await Traverse(store,
            new MetadataPageQuery.CacheEntries(package.Key.RegistryId, new("anonymous"), None<MetadataPackageKey>())
            { PageSize = 1, Continuation = None<MetadataContinuation>() }, cancellationToken);
        Assert.Equal(64, small.Length);
    }

    public static async Task BoundedDatasetsAsync(IMetadataStore store, CancellationToken cancellationToken)
    {
        Assert.Empty(await Traverse(store, Registries(), cancellationToken));
        foreach (var target in new[] { 1, 100, 205 })
        {
            var before = (await Traverse(store, Registries(), cancellationToken)).Length;
            for (var start = before; start < target; start += 64)
            {
                await Commit(store, cancellationToken, Enumerable.Range(start + 1, Math.Min(64, target - start))
                    .Select(number => (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray());
            }
            var actual = await Traverse(store, Registries(), cancellationToken);
            Assert.Equal(target, actual.Length);
            Assert.Equal(target, actual.Select(record => record.Selector).Distinct().Count());
            var keys = actual.Select(record => Convert.ToHexStringLower(MetadataEncoding.Key(record.Selector).AsSpan())).ToArray();
            Assert.Equal(keys.Order(StringComparer.Ordinal), keys);
        }
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.ReadPageAsync(Registries(101), new(), cancellationToken)));
        Assert.Throws<ArgumentException>(() => new MetadataReadGroup(new MetadataSelector[65].ToImmutableArray()));
    }

    public static async Task ContinuationScopeAndEpochAsync(
        IMetadataStore store, IMetadataStore foreign, CancellationToken cancellationToken)
    {
        await Commit(store, cancellationToken, Enumerable.Range(1, 4).Select(number =>
            (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray());
        var query = Registries(1);
        var first = Success(await store.ReadPageAsync(query, new(), cancellationToken));
        Assert.Single(first.Records);
        var next = query with { Continuation = first.Continuation };
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.ReadPageAsync(next with { PageSize = 2 }, new(), cancellationToken)));
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.ReadPageAsync(
            new MetadataPageQuery.Packages(Id(1)) { PageSize = 1, Continuation = first.Continuation }, new(), cancellationToken)));
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await foreign.ReadPageAsync(next, new(), cancellationToken)));
        var two = await Read<MetadataRegistry>(store, new MetadataSelector.Registry(Id(2)), cancellationToken);
        await Commit(store, cancellationToken, new MetadataMutation.DeleteRegistry(two.Id, two.Revision),
            new MetadataMutation.PutRegistry(Registry(5), new ExpectedRevision.Absent()));
        var three = await Read<MetadataRegistry>(store, new MetadataSelector.Registry(Id(3)), cancellationToken);
        await Commit(store, cancellationToken, new MetadataMutation.PutRegistry(
            three with { Label = new("updated") }, new ExpectedRevision.Match(three.Revision)));
        var remainder = await Traverse(store, next, cancellationToken);
        Assert.Equal(new[] { Id(3), Id(4), Id(5) }, remainder.Cast<MetadataRegistry>().Select(record => record.Id));
        Assert.Equal("updated", ((MetadataRegistry)remainder[0]).Label.Value);
    }
}
