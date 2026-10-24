using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataCorruptionAssertions
{
    public static async Task AbsenceAndCorruptGroupsAsync(
        IMetadataStore store,
        Func<MetadataSelector, CancellationToken, ValueTask<MetadataResult<MetadataId>>> corruptRecordAsync,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(corruptRecordAsync);
        var (registry, package) = await Seed(store, cancellationToken);
        var request = new MetadataReadGroup([package.Selector, Registry(99).Selector, registry.Selector]);
        var before = Success(await store.ReadAsync(request, new(), cancellationToken));
        Assert.Equal(3, before.Items.Length);
        Assert.IsType<MetadataReadItem.NotFound>(before.Items[1]);
        Success(await corruptRecordAsync(registry.Selector, cancellationToken));
        CorruptFailure(await store.ReadAsync(request, new(), cancellationToken), MetadataPhase.Read);
    }

    public static async Task PageRecordsAsync(
        IMetadataStore store,
        Func<MetadataCorruptionRequest, CancellationToken, ValueTask<IMetadataCorruptionScope>> corruptAsync,
        Func<MetadataSelector, CancellationToken, ValueTask<MetadataResult<MetadataId>>> corruptRecordAsync,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(corruptAsync);
        ArgumentNullException.ThrowIfNull(corruptRecordAsync);
        var healthy = Registry();
        var damaged = Registry(2) with { Label = new(MetadataReconciliationAssertions.CorruptionCanary) };
        await Commit(store, cancellationToken,
            new MetadataMutation.PutRegistry(healthy, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(damaged, new ExpectedRevision.Absent()));
        var query = Registries();
        var baseline = Success(await store.ReadPageAsync(query, new(), cancellationToken));
        Assert.Equal(2, baseline.Records.Length);
        foreach (var invalid in new[] { query with { PageSize = 101 }, query with
        {
            Continuation = new MetadataOption<MetadataContinuation>.Some(new(MetadataReconciliationAssertions.CorruptionCanary))
        } })
        {
            var failure = Assert.IsType<MetadataResult<MetadataPage>.Failure>(
                await store.ReadPageAsync(invalid, new(), cancellationToken));
            Assert.Equal(MetadataFailureCode.InvalidInput, failure.Code);
            Assert.Equal(MetadataRetryDisposition.CorrectInput, failure.Retry);
            Assert.Equal(MetadataPhase.Page, failure.Phase);
            Assert.DoesNotContain(MetadataReconciliationAssertions.CorruptionCanary, failure.ToString());
        }
        foreach (var corruption in new[] { MetadataRecordCorruption.NullLabel, MetadataRecordCorruption.OversizedLabel,
            MetadataRecordCorruption.NullRevision, MetadataRecordCorruption.MalformedEncoding, MetadataRecordCorruption.MismatchedKey })
        {
            await using (var scope = await corruptAsync(
                new MetadataCorruptionRequest.Record(damaged.Selector, corruption), cancellationToken))
            {
                var fingerprint = await scope.ObserveAsync(cancellationToken);
                Assert.NotEqual(scope.Original, fingerprint);
                CorruptFailure(await store.ReadPageAsync(query, new(), cancellationToken), MetadataPhase.Page);
                CorruptFailure(await store.ReadAsync(new([healthy.Selector, damaged.Selector]), new(), cancellationToken),
                    MetadataPhase.Read);
                Assert.Equal(fingerprint, await scope.ObserveAsync(cancellationToken));
                await Read<MetadataRegistry>(store, healthy.Selector, cancellationToken);
            }
            var restored = Success(await store.ReadPageAsync(query, new(), cancellationToken));
            Assert.Equal<byte>(MetadataEncoding.Encode(baseline), MetadataEncoding.Encode(restored));
            Assert.IsType<MetadataOption<MetadataContinuation>.None>(restored.Continuation);
            await Read<MetadataRegistry>(store, damaged.Selector, cancellationToken);
        }
        Success(await corruptRecordAsync(damaged.Selector, cancellationToken));
        CorruptFailure(await store.ReadPageAsync(query, new(), cancellationToken), MetadataPhase.Page);
    }

    public static async Task QueryDimensionsAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority,
        Func<MetadataCorruptionRequest, CancellationToken, ValueTask<IMetadataCorruptionScope>> corruptAsync,
        MetadataRecordCorruption corruption, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(corruptAsync);
        if (corruption is not (MetadataRecordCorruption.CacheAuthorization or MetadataRecordCorruption.AggregateAuthorization
            or MetadataRecordCorruption.AggregateStart or MetadataRecordCorruption.AggregateEnd or MetadataRecordCorruption.LeaseResource))
        { throw new ArgumentException("BindingInvalid", nameof(corruption)); }
        var (registry, package) = await Seed(store, cancellationToken);
        var first = Entry(package, target: "/a");
        var damaged = Entry(package, target: "/b");
        var aggregate = Aggregate(registry);
        await Commit(store, cancellationToken, Publish(authority, first), Publish(authority, damaged),
            Publish(authority, Entry(package, partition: "other", target: "/a0")),
            Publish(authority, Entry(package, partition: "other", target: "/a1")),
            Publish(authority, Entry(package, partition: "other", target: "/a2")),
            new MetadataMutation.AddAggregateContribution(aggregate, Delta()),
            new MetadataMutation.AddAggregateContribution(Aggregate(registry, "other"), Delta()),
            new MetadataMutation.AddAggregateContribution(aggregate with { Start = new(1) }, Delta()),
            new MetadataMutation.AcquireLease(new("maintenance-a"), Id(3), 300),
            new MetadataMutation.AcquireLease(new("maintenance-b"), Id(3), 300),
            new MetadataMutation.AcquireLease(new("other-a"), Id(3), 300));
        MetadataPageQuery query = corruption switch
        {
            MetadataRecordCorruption.CacheAuthorization => new MetadataPageQuery.CacheEntries(
                registry.Id, new("anonymous"), new MetadataOption<MetadataPackageKey>.Some(package.Key))
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            MetadataRecordCorruption.LeaseResource => new MetadataPageQuery.Leases(new("maintenance-"))
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            _ => new MetadataPageQuery.Aggregates(registry.Id, new("anonymous"), aggregate.Start, aggregate.End)
            { PageSize = 100, Continuation = None<MetadataContinuation>() }
        };
        MetadataSelector selector = corruption switch
        {
            MetadataRecordCorruption.CacheAuthorization => damaged.Selector,
            MetadataRecordCorruption.LeaseResource => new MetadataSelector.Lease(new("maintenance-b")),
            _ => new MetadataSelector.Aggregate(aggregate)
        };
        MetadataPageQuery[] emptyQueries = [
            new MetadataPageQuery.CacheEntries(registry.Id, new("foreign"), None<MetadataPackageKey>())
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Aggregates(registry.Id, new("foreign"), aggregate.Start, aggregate.End)
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Aggregates(registry.Id, new("anonymous"), new(2), aggregate.End)
            { PageSize = 100, Continuation = None<MetadataContinuation>() },
            new MetadataPageQuery.Leases(new("foreign-"))
            { PageSize = 100, Continuation = None<MetadataContinuation>() }];
        var baseline = Success(await store.ReadPageAsync(query, new(), cancellationToken));
        Assert.Equal(corruption is MetadataRecordCorruption.CacheAuthorization or MetadataRecordCorruption.LeaseResource
            ? 2 : 1, baseline.Records.Length);
        foreach (var empty in emptyQueries) { Assert.Empty(await Traverse(store, empty, cancellationToken)); }
        await using (var scope = await corruptAsync(new MetadataCorruptionRequest.Record(selector, corruption), cancellationToken))
        {
            var fingerprint = await scope.ObserveAsync(cancellationToken);
            Assert.NotEqual(scope.Original, fingerprint);
            CorruptFailure(await store.ReadPageAsync(query, new(), cancellationToken), MetadataPhase.Page);
            CorruptFailure(await store.ReadAsync(new([registry.Selector, selector]), new(), cancellationToken), MetadataPhase.Read);
            Assert.Equal(fingerprint, await scope.ObserveAsync(cancellationToken));
        }
        var restored = Success(await store.ReadPageAsync(query, new(), cancellationToken));
        Assert.Equal<byte>(MetadataEncoding.Encode(baseline), MetadataEncoding.Encode(restored));
        Assert.Equal(baseline.Records.Select(record => record.Selector),
            (await Traverse(store, query with { PageSize = 1 }, cancellationToken)).Select(record => record.Selector));
        foreach (var empty in emptyQueries) { Assert.Empty(await Traverse(store, empty, cancellationToken)); }
    }
}
