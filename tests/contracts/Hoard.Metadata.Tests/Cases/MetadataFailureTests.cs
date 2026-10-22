using System.Diagnostics;
using Hoard.Abstractions.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataFailureTests
{
    [Fact]
    public async Task MP20_Injected_storage_capacity_rolls_back_and_allows_same_ticket_retry()
    {
        await using var fixture = await OpenAsync();
        var batch = Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        fixture.InjectStorageCapacityForTest();
        Assert.Equal(MetadataFailureCode.Capacity, Failed(await fixture.Store.CommitAsync(batch, new(), default)));
        await Missing(fixture, Registry().Selector);
        Success(await fixture.Store.CommitAsync(batch, new(), default));
        await Read<MetadataRegistry>(fixture, Registry().Selector);
    }

    [Fact]
    public async Task MP20_Live_ledger_capacity_is_classified_without_evicting_a_receipt()
    {
        await using var fixture = await OpenAsync();
        var batch = Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        var receipt = Success(await fixture.Store.CommitAsync(batch, new(), default));
        Success(await fixture.FillLedgerForTestAsync());
        Assert.Equal(MetadataFailureCode.Capacity, Failed(await fixture.Store.ReserveOperationAsync(new(), default)));
        var stored = Assert.IsType<MetadataResolution.Committed>(Success(await fixture.Store.ReconcileAsync(batch.Ticket, new(), default)));
        Assert.Equal(receipt.CommitId, stored.Receipt.CommitId);
        Assert.Equal(receipt.CommitId, Success(await fixture.Store.CommitAsync(batch, new(), default)).CommitId);
    }

    [Fact]
    public async Task MP21_Absence_succeeds_but_corruption_fails_the_complete_group()
    {
        await using var fixture = await OpenAsync();
        var (registry, package) = await Seed(fixture);
        var absent = Registry(99).Selector;
        var before = Success(await fixture.Store.ReadAsync(new([package.Selector, absent, registry.Selector]), new(), default));
        Assert.IsType<MetadataReadItem.NotFound>(before.Items[1]);
        Success(await fixture.CorruptRecordForTestAsync(registry.Selector));
        Assert.Equal(MetadataFailureCode.CorruptState, Failed(await fixture.Store.ReadAsync(new([package.Selector, absent, registry.Selector]), new(), default)));
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
        foreach (var code in Enum.GetValues<MetadataFailureCode>())
        {
            var failure = new MetadataResult<MetadataPage>.Failure(code, MetadataPhase.Commit,
                MetadataRetryDisposition.OperatorRecovery, Id(1));
            Assert.Equal(code, failure.Code);
            MetadataTestData.AssertSanitized(failure.ToString());
        }
        foreach (var value in new MetadataDiagnostic[]
        {
            new MetadataArtifactEvidence(MetadataTestData.Canary), new MetadataContinuation(MetadataTestData.Canary),
            new PublicLabel(MetadataTestData.Canary), new MetadataSecretReference("fixture", "resolver", MetadataTestData.Canary)
        })
        {
            MetadataTestData.AssertSanitized(value.ToString());
            var display = Attribute.GetCustomAttribute(value.GetType(), typeof(DebuggerDisplayAttribute), inherit: true);
            Assert.NotNull(display);
            MetadataTestData.AssertSanitized(((DebuggerDisplayAttribute)display).Value);
        }
    }
}
