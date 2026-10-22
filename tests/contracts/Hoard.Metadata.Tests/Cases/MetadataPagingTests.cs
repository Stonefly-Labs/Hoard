using System.Collections.Immutable;
using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Abstractions.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataPagingTests
{
    [Fact]
    public async Task MP07_All_seven_query_kinds_keep_scope_and_tuple_order()
    {
        await using var fixture = await OpenAsync();
        var (registry, package) = await Seed(fixture);
        var entry = Entry(package);
        await Commit(fixture, Publish(fixture, entry), new MetadataMutation.PutPolicy(Policy(), new ExpectedRevision.Absent()),
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
        foreach (var query in queries) { Assert.Single(await Traverse(fixture, query)); }
        Assert.Empty(await Traverse(fixture, new MetadataPageQuery.Packages(Id(999))
        { PageSize = 1, Continuation = None<MetadataContinuation>() }));
        Assert.Empty(await Traverse(fixture, new MetadataPageQuery.CacheEntries(registry.Id, new("foreign"), None<MetadataPackageKey>())
        { PageSize = 1, Continuation = None<MetadataContinuation>() }));
    }

    [Fact]
    public async Task MP07_Oversized_requests_and_results_fail_whole_instead_of_truncating()
    {
        await using var fixture = await OpenAsync();
        var (_, package) = await Seed(fixture);
        var entries = Enumerable.Range(1, 64).Select(number => Entry(package, target: "/large/" + number) with
        {
            Headers = new([new("content-type", new string('<', 4000)), new("content-language", new string('<', 4000))])
        }).ToArray();
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.CommitAsync(
            Batch(await Ticket(fixture), entries.Select(entry => (MetadataMutation)Publish(fixture, entry)).ToArray()), new(), default)));
        await Missing(fixture, entries[0].Selector);
        foreach (var entry in entries) { await Commit(fixture, Publish(fixture, entry)); }
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.ReadAsync(new(
            entries.Select(entry => entry.Selector).ToImmutableArray()), new(), default)));
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.ReadPageAsync(
            new MetadataPageQuery.CacheEntries(package.Key.RegistryId, new("anonymous"), None<MetadataPackageKey>())
            { PageSize = 100, Continuation = None<MetadataContinuation>() }, new(), default)));
        var small = await Traverse(fixture, new MetadataPageQuery.CacheEntries(package.Key.RegistryId, new("anonymous"), None<MetadataPackageKey>())
        { PageSize = 1, Continuation = None<MetadataContinuation>() });
        Assert.Equal(64, small.Length);
    }

    [Fact]
    public async Task MP07_Bounded_datasets_traverse_once_without_truncation()
    {
        await using var fixture = await OpenAsync();
        Assert.Empty(await Traverse(fixture, Registries()));
        foreach (var target in new[] { 1, 100, 205 })
        {
            var before = (await Traverse(fixture, Registries())).Length;
            for (var start = before; start < target; start += 64)
            {
                await Commit(fixture, Enumerable.Range(start + 1, Math.Min(64, target - start))
                    .Select(number => (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray());
            }
            var actual = await Traverse(fixture, Registries());
            Assert.Equal(target, actual.Length);
            Assert.Equal(target, actual.Select(record => record.Selector).Distinct().Count());
            var keys = actual.Select(record => Convert.ToHexStringLower(MetadataEncoding.Key(record.Selector).AsSpan())).ToArray();
            Assert.Equal(keys.Order(StringComparer.Ordinal), keys);
        }
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.ReadPageAsync(Registries(101), new(), default)));
        Assert.Throws<ArgumentException>(() => new MetadataReadGroup(new MetadataSelector[65].ToImmutableArray()));
    }

    [Fact]
    public async Task MP08_Continuation_is_bound_to_scope_size_and_epoch_and_is_not_a_snapshot()
    {
        await using var fixture = await OpenAsync();
        await Commit(fixture, Enumerable.Range(1, 4).Select(number =>
            (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray());
        var query = Registries(1);
        var first = Success(await fixture.Store.ReadPageAsync(query, new(), default));
        Assert.Single(first.Records);
        var next = query with { Continuation = first.Continuation };
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.ReadPageAsync(next with { PageSize = 2 }, new(), default)));
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.ReadPageAsync(
            new MetadataPageQuery.Packages(Id(1)) { PageSize = 1, Continuation = first.Continuation }, new(), default)));
        await using var foreign = await OpenAsync();
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await foreign.Store.ReadPageAsync(next, new(), default)));
        var two = await Read<MetadataRegistry>(fixture, new MetadataSelector.Registry(Id(2)));
        await Commit(fixture, new MetadataMutation.DeleteRegistry(two.Id, two.Revision),
            new MetadataMutation.PutRegistry(Registry(5), new ExpectedRevision.Absent()));
        var three = await Read<MetadataRegistry>(fixture, new MetadataSelector.Registry(Id(3)));
        await Commit(fixture, new MetadataMutation.PutRegistry(three with { Label = new("updated") }, new ExpectedRevision.Match(three.Revision)));
        var remainder = await Traverse(fixture, next);
        Assert.Equal(new[] { Id(3), Id(4), Id(5) }, remainder.Cast<MetadataRegistry>().Select(record => record.Id));
        Assert.Equal("updated", ((MetadataRegistry)remainder[0]).Label.Value);
    }

    [Theory]
    [InlineData("null")]
    [InlineData("omitted")]
    [InlineData("wrong-type")]
    [InlineData("empty")]
    [InlineData("odd-hex")]
    [InlineData("invalid-hex")]
    public async Task MP08_Malformed_continuation_fields_reject_input_and_preserve_valid_resume(string shape)
    {
        await using var fixture = await OpenAsync();
        await Commit(fixture, Enumerable.Range(1, 3).Select(number =>
            (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray());
        var query = Registries(1);
        var first = Success(await fixture.Store.ReadPageAsync(query, new(), default));
        var continuation = Assert.IsType<MetadataOption<MetadataContinuation>.Some>(first.Continuation).Value;
        var cursor = Assert.IsType<JsonObject>(JsonNode.Parse(Convert.FromBase64String(continuation.Value)));
        var valid = query with { Continuation = first.Continuation };
        foreach (var field in cursor.Select(property => property.Key).ToArray())
        {
            var malformed = cursor.DeepClone().AsObject();
            if (shape == "omitted") { Assert.True(malformed.Remove(field)); }
            else
            {
                malformed[field] = shape switch
                {
                    "null" => null,
                    "wrong-type" => JsonValue.Create(42),
                    "empty" => JsonValue.Create(""),
                    "odd-hex" => JsonValue.Create("000"),
                    "invalid-hex" => JsonValue.Create("zz"),
                    _ => throw new ArgumentException("Unknown continuation test shape.")
                };
            }
            var invalid = query with
            {
                Continuation = new MetadataOption<MetadataContinuation>.Some(new(
                    Convert.ToBase64String(JsonSerializer.SerializeToUtf8Bytes(malformed))))
            };
            var failure = Assert.IsType<MetadataResult<MetadataPage>.Failure>(
                await fixture.Store.ReadPageAsync(invalid, new(), default));
            Assert.Equal(MetadataFailureCode.InvalidInput, failure.Code);
            Assert.Equal(MetadataRetryDisposition.CorrectInput, failure.Retry);
            Assert.Equal(MetadataPhase.Page, failure.Phase);
            var resumed = Success(await fixture.Store.ReadPageAsync(valid, new(), default));
            Assert.Equal(Id(2), Assert.IsType<MetadataRegistry>(Assert.Single(resumed.Records)).Id);
        }
        Assert.Equal(new[] { Id(2), Id(3) },
            (await Traverse(fixture, valid)).Cast<MetadataRegistry>().Select(record => record.Id));
        Assert.Equal(new[] { Id(1), Id(2), Id(3) },
            (await Traverse(fixture, query)).Cast<MetadataRegistry>().Select(record => record.Id));
    }
}
