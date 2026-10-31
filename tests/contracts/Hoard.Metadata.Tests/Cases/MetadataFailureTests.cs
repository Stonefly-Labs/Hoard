using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Metadata;
using Xunit.Abstractions;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataFailureTests(ITestOutputHelper output)
{
    [Fact]
    public async Task MP20_Injected_storage_capacity_rolls_back_and_allows_same_ticket_retry()
    {
        await using var fixture = await OpenAsync();
        await MetadataFailureAssertions.StorageCapacityAsync(fixture.Store, cancellationToken =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            fixture.InjectStorageCapacityForTest();
            return ValueTask.CompletedTask;
        }, default);
        ObserveOriginal(output, fixture, nameof(MetadataFailureTests));
    }

    [Fact]
    public async Task MP20_Live_ledger_capacity_is_classified_without_evicting_a_receipt()
    {
        await using var fixture = await OpenAsync();
        await MetadataFailureAssertions.LedgerCapacityAsync(fixture.Store, cancellationToken =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            return fixture.FillLedgerForTestAsync();
        }, default);
        ObserveOriginal(output, fixture, nameof(MetadataFailureTests));
    }

    [Fact]
    public async Task MP21_Absence_succeeds_but_corruption_fails_the_complete_group()
    {
        await using var fixture = await OpenAsync();
        await MetadataCorruptionAssertions.AbsenceAndCorruptGroupsAsync(fixture.Store,
            (selector, token) => CommonCorruptRecordAsync(fixture, selector, token), default);
        ObserveOriginal(output, fixture, nameof(MetadataFailureTests));
    }

    [Fact]
    public async Task MP21_Stored_page_corruption_fails_whole_and_preserves_data()
    {
        await using var fixture = await OpenAsync();
        await MetadataCorruptionAssertions.PageRecordsAsync(fixture.Store,
            (request, token) => CommonCorruptionAsync(fixture, request, token),
            (selector, token) => CommonCorruptRecordAsync(fixture, selector, token), default);
        CommonDiagnosticAssertions(fixture);
        ObserveOriginal(output, fixture, nameof(MetadataFailureTests));
    }

    [Theory]
    [InlineData("cache-auth")]
    [InlineData("aggregate-auth")]
    [InlineData("aggregate-start")]
    [InlineData("aggregate-end")]
    [InlineData("lease-resource")]
    public async Task MP21_Corrupt_query_dimensions_cannot_disappear_behind_page_filters(string shape)
    {
        await using var fixture = await OpenAsync();
        var corruption = shape switch
        {
            "cache-auth" => MetadataRecordCorruption.CacheAuthorization,
            "aggregate-auth" => MetadataRecordCorruption.AggregateAuthorization,
            "aggregate-start" => MetadataRecordCorruption.AggregateStart,
            "aggregate-end" => MetadataRecordCorruption.AggregateEnd,
            "lease-resource" => MetadataRecordCorruption.LeaseResource,
            _ => throw new ArgumentException("Unknown corruption test shape.", nameof(shape))
        };
        var authority = CommonAuthority(fixture);
        await MetadataCorruptionAssertions.QueryDimensionsAsync(fixture.Store, authority,
            (request, token) => CommonCorruptionAsync(fixture, request, token), corruption, default);
        CommonDiagnosticAssertions(fixture);
        ObserveOriginal(output, fixture, authority, nameof(MetadataFailureTests), shape: shape);
    }

    [Fact]
    public async Task MP22_Diagnostics_and_all_failure_shapes_are_sanitized()
    {
        await using var fixture = await OpenAsync();
        fixture.Controls.SetObserver("mutation.applied", () => throw new InvalidOperationException(
            "Data Source=/private/" + MetadataTestData.Canary + ";Password=" + MetadataTestData.Canary));
        var result = await fixture.Store.CommitAsync(Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(
            Registry() with { Label = new(MetadataTestData.Canary) }, new ExpectedRevision.Absent())), new(), default);
        Assert.Equal(MetadataFailureCode.InternalFailure, Failed(result));
        foreach (var diagnostic in fixture.Controls.Diagnostics.Append(result.ToString()!))
        { MetadataTestData.AssertSanitized(diagnostic); }
        Assert.Contains("metadata.internal_failure", fixture.Controls.Diagnostics);
        await MetadataFailureAssertions.DiagnosticsAsync(fixture.Store, () => CommonCounters(fixture),
            MetadataTestData.Canary, MetadataTestData.AssertSanitized, default);
        CommonDiagnosticAssertions(fixture);
        ObserveOriginal(output, fixture, nameof(MetadataFailureTests));
    }
}
