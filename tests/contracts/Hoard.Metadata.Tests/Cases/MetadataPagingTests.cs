using System.Text.Json.Nodes;
using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataPagingTests
{
    [Fact]
    public async Task Typed_continuation_bridge_covers_all_actual_cursor_fields()
    {
        await using var fixture = await OpenAsync();
        await Commit(fixture, Enumerable.Range(1, 3).Select(number =>
            (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray());
        var first = Success(await fixture.Store.ReadPageAsync(Registries(1), new(), default));
        var continuation = Assert.IsType<MetadataOption<MetadataContinuation>.Some>(first.Continuation).Value;
        var original = Assert.IsType<JsonObject>(JsonNode.Parse(Convert.FromBase64String(continuation.Value)));
        var removed = new HashSet<string>(StringComparer.Ordinal);
        var corrupt = CommonContinuationCorruption(fixture);
        foreach (var component in Enum.GetValues<MetadataContinuationComponent>())
        {
            var damaged = await corrupt(continuation, component, MetadataContinuationCorruption.Omitted, default);
            var cursor = Assert.IsType<JsonObject>(JsonNode.Parse(Convert.FromBase64String(damaged.Value)));
            var field = Assert.Single(original.Select(property => property.Key).Except(cursor.Select(property => property.Key)));
            removed.Add(field);
            Assert.Equal(original.Count - 1, cursor.Count);
            foreach (var property in cursor)
            { Assert.True(JsonNode.DeepEquals(original[property.Key], property.Value)); }
        }
        Assert.Equal(original.Select(property => property.Key).Order(StringComparer.Ordinal), removed.Order(StringComparer.Ordinal));
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            corrupt(continuation, MetadataContinuationComponent.Position, MetadataContinuationCorruption.Null, cancelled.Token).AsTask());
        await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() =>
            corrupt(continuation, (MetadataContinuationComponent)int.MaxValue, MetadataContinuationCorruption.Null, default).AsTask());
        await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() =>
            corrupt(continuation, MetadataContinuationComponent.Position, (MetadataContinuationCorruption)int.MaxValue, default).AsTask());
        Assert.Equal(continuation.Value, Assert.IsType<MetadataOption<MetadataContinuation>.Some>(
            Success(await fixture.Store.ReadPageAsync(Registries(1), new(), default)).Continuation).Value.Value);
    }

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
        var corruption = shape switch
        {
            "null" => MetadataContinuationCorruption.Null,
            "omitted" => MetadataContinuationCorruption.Omitted,
            "wrong-type" => MetadataContinuationCorruption.WrongType,
            "empty" => MetadataContinuationCorruption.Empty,
            "odd-hex" => MetadataContinuationCorruption.OddHex,
            "invalid-hex" => MetadataContinuationCorruption.InvalidHex,
            _ => throw new ArgumentException("Unknown continuation test shape.", nameof(shape))
        };
        await MetadataPagingAssertions.MalformedContinuationFieldsAsync(
            fixture.Store, CommonContinuationCorruption(fixture), corruption, default);
    }
}
