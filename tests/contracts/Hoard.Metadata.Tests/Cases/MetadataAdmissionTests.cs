using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;

namespace Hoard.Metadata.Tests;

public sealed class MetadataAdmissionTests
{
    [Fact]
    public async Task MP32_Ordinary_use_requires_explicit_schema_admission()
    {
        await using var fixture = MetadataFixtureSession.CreateFromEnvironment(new MetadataTestClock());
        Assert.Equal(0, fixture.Controls.ActivityCount);
        var denied = await fixture.Store.ReserveOperationAsync(new(), default);
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Assert.IsType<MetadataResult<MetadataOperationTicket>.Failure>(denied).Code);
        var inspection = Assert.IsType<MetadataResult<MetadataSchemaInspection>.Success>(
            await fixture.Schema.InspectAsync(new(), default));
        Assert.Equal(MetadataSchemaState.Empty, inspection.Value.State);
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Failure>(
            await fixture.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default));
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
            await fixture.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        Assert.IsType<MetadataResult<MetadataOperationTicket>.Success>(
            await fixture.Store.ReserveOperationAsync(new(), default));
    }

    [Fact]
    public async Task MP19_Invalid_budgets_and_closed_instances_do_not_dispatch_work()
    {
        var fixture = MetadataFixtureSession.CreateFromEnvironment(new MetadataTestClock());
        try
        {
            Assert.IsType<MetadataResult<MetadataSchemaInspection>.Failure>(
                await fixture.Schema.InspectAsync(new(TimeSpan.Zero), default));
            Assert.IsType<MetadataResult<MetadataSchemaInspection>.Failure>(
                await fixture.Schema.InspectAsync(new(TimeSpan.FromMinutes(3)), default));
            Assert.Equal(0, fixture.Controls.ActivityCount);
            Assert.IsType<MetadataResult<MetadataOperationTicket>.Failure>(
                await fixture.Store.ReserveOperationAsync(new(TimeSpan.FromSeconds(31)), default));
        }
        finally { await fixture.DisposeAsync(); }
        Assert.Equal(MetadataFailureCode.Disposed, Assert.IsType<MetadataResult<MetadataOperationTicket>.Failure>(
            await fixture.Store.ReserveOperationAsync(new(), default)).Code);
    }
}
