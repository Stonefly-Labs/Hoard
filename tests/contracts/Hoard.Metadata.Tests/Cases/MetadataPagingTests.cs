using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataPagingTests
{
    [Fact]
    public async Task MP07_All_seven_query_kinds_keep_scope_and_tuple_order()
    {
        await using var fixture = await OpenAsync();
        await MetadataPagingAssertions.AllQueryKindsAsync(fixture.Store, CommonAuthority(fixture), default);
    }

    [Fact]
    public async Task MP07_Oversized_requests_and_results_fail_whole_instead_of_truncating()
    {
        await using var fixture = await OpenAsync();
        await MetadataPagingAssertions.OversizedRequestsAndResultsAsync(fixture.Store, CommonAuthority(fixture), default);
    }

    [Fact]
    public async Task MP07_Bounded_datasets_traverse_once_without_truncation()
    {
        await using var fixture = await OpenAsync();
        await MetadataPagingAssertions.BoundedDatasetsAsync(fixture.Store, default);
    }

    [Fact]
    public async Task MP08_Continuation_is_bound_to_scope_size_and_epoch_and_is_not_a_snapshot()
    {
        await using var fixture = await OpenAsync();
        await using var foreign = await OpenAsync();
        await MetadataPagingAssertions.ContinuationScopeAndEpochAsync(fixture.Store, foreign.Store, default);
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
