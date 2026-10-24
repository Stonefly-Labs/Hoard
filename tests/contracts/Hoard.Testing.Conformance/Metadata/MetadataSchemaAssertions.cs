using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataSchemaAssertions
{
    public static async Task UnrecognizedLayoutAsync(
        IMetadataConformanceSession session, bool partial, CancellationToken cancellationToken)
    {
        Success(await session.Faults.CreateUnrecognizedLayoutAsync(partial, cancellationToken));
        var before = await session.Faults.ObserveStateAsync(cancellationToken);
        Assert.Equal(MetadataSchemaState.Incompatible, Success(await session.Schema.InspectAsync(new(), cancellationToken)).State);
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await session.Schema.PrepareAsync(
            new MetadataSchemaRequest.CreateIfEmpty(), new(), cancellationToken)));
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await session.Store.ReserveOperationAsync(new(), cancellationToken)));
        Assert.Equal(before, await session.Faults.ObserveStateAsync(cancellationToken));
    }

    public static async Task UpgradeAsync(IMetadataConformanceSession legacy, CancellationToken cancellationToken)
    {
        var originalAdmission = Success(await legacy.Schema.PrepareAsync(
            new MetadataSchemaRequest.CreateIfEmpty(), new(), cancellationToken));
        var (registry, package) = await Seed(legacy.Store, cancellationToken);
        var entry = Entry(package);
        var receipt = await Commit(legacy.Store, cancellationToken, Publish(legacy.Authority, entry),
            new MetadataMutation.AddAggregateContribution(Aggregate(registry), Delta(7)),
            new MetadataMutation.AcquireLease(new("maintenance"), Id(55), 300));
        entry = await Read<MetadataCacheEntry>(legacy.Store, entry.Selector, cancellationToken);
        await using var current = await legacy.ReopenAsync(cancellationToken);
        var inspection = Success(await current.Schema.InspectAsync(new(), cancellationToken));
        Assert.Equal(MetadataSchemaState.UpgradeRequired, inspection.State);
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await current.Store.ReserveOperationAsync(new(), cancellationToken)));
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await current.Schema.PrepareAsync(
            new MetadataSchemaRequest.InspectOnly(), new(), cancellationToken)));
        var point = await current.Faults.AuthorizeUpgradeAsync(cancellationToken);
        Assert.Equal(inspection.CurrentVersion, point.SchemaVersion);
        var admission = Success(await current.Schema.PrepareAsync(
            new MetadataSchemaRequest.Upgrade(point.SchemaVersion, inspection.TargetVersion, point), new(), cancellationToken));
        Assert.NotEqual(originalAdmission.Epoch, admission.Epoch);
        Assert.Equal(registry, await Read<MetadataRegistry>(current.Store, registry.Selector, cancellationToken));
        Assert.Equal(package, await Read<MetadataPackage>(current.Store, package.Selector, cancellationToken));
        var restoredEntry = await Read<MetadataCacheEntry>(current.Store, entry.Selector, cancellationToken);
        Assert.True(MetadataEncoding.Encode(entry).AsSpan().SequenceEqual(MetadataEncoding.Encode(restoredEntry).AsSpan()));
        Assert.Equal(7, (await Read<MetadataAccessAggregate>(current.Store,
            new MetadataSelector.Aggregate(Aggregate(registry)), cancellationToken)).Counters.Hits);
        Assert.Equal(MetadataFailureCode.ReconciliationExpired, Failed(await current.Store.ReconcileAsync(receipt.Ticket, new(), cancellationToken)));
        await using var reopened = await current.ReopenAsync(cancellationToken);
        Assert.Equal(MetadataSchemaState.Compatible, Success(await reopened.Schema.InspectAsync(new(), cancellationToken)).State);
        Success(await reopened.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), cancellationToken));
        Assert.Equal(admission.Epoch, Success(await reopened.Schema.PrepareAsync(
            new MetadataSchemaRequest.InspectOnly(), new(), cancellationToken)).Epoch);
        Assert.Equal(registry, await Read<MetadataRegistry>(reopened.Store, registry.Selector, cancellationToken));
    }

    public static async Task InvalidUpgradeAsync(IMetadataConformanceSession legacy, CancellationToken cancellationToken)
    {
        Success(await legacy.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), cancellationToken));
        var (registry, _) = await Seed(legacy.Store, cancellationToken);
        await using var current = await legacy.ReopenAsync(cancellationToken);
        var inspection = Success(await current.Schema.InspectAsync(new(), cancellationToken));
        Assert.Equal(MetadataSchemaState.UpgradeRequired, inspection.State);
        var point = await current.Faults.AuthorizeUpgradeAsync(cancellationToken);
        var before = await current.Faults.ObserveStateAsync(cancellationToken);
        foreach (var invalid in new[] { "", new string('v', 65), "v\u0100", "v\n" })
        {
            Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await current.Schema.PrepareAsync(
                new MetadataSchemaRequest.Upgrade(point.SchemaVersion, invalid, point), new(), cancellationToken)));
            Assert.Equal(before, await current.Faults.ObserveStateAsync(cancellationToken));
            Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await current.Store.ReserveOperationAsync(new(), cancellationToken)));
        }
        foreach (var request in new[]
        {
            new MetadataSchemaRequest.Upgrade(point.SchemaVersion, inspection.TargetVersion, point with { Id = Id(999) }),
            new MetadataSchemaRequest.Upgrade(point.SchemaVersion, "f07-synthetic-unsupported-schema", point)
        })
        {
            Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Failure>(
                await current.Schema.PrepareAsync(request, new(), cancellationToken));
            Assert.Equal(before, await current.Faults.ObserveStateAsync(cancellationToken));
            Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await current.Store.ReserveOperationAsync(new(), cancellationToken)));
        }
        Assert.Equal(MetadataSchemaState.UpgradeRequired, Success(await current.Schema.InspectAsync(new(), cancellationToken)).State);
        Success(await current.Schema.PrepareAsync(
            new MetadataSchemaRequest.Upgrade(point.SchemaVersion, inspection.TargetVersion, point), new(), cancellationToken));
        Assert.Equal(registry, await Read<MetadataRegistry>(current.Store, registry.Selector, cancellationToken));
    }

    public static async Task UpgradeExclusionAsync(IMetadataConformanceSession legacy, CancellationToken cancellationToken)
    {
        Success(await legacy.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), cancellationToken));
        await Seed(legacy.Store, cancellationToken);
        await using var current = await legacy.ReopenAsync(cancellationToken);
        var inspection = Success(await current.Schema.InspectAsync(new(), cancellationToken));
        Assert.Equal(MetadataSchemaState.UpgradeRequired, inspection.State);
        var point = await current.Faults.AuthorizeUpgradeAsync(cancellationToken);
        var request = new MetadataSchemaRequest.Upgrade(point.SchemaVersion, inspection.TargetVersion, point);
        await using var barrier = new MetadataConformanceBarrier();
        await using var observation = await current.Faults.ObserveBoundaryAsync(
            MetadataObservationPoint.SchemaCandidatePrepared, barrier.HoldAsync, cancellationToken);
        var first = current.Schema.PrepareAsync(request, new(), cancellationToken).AsTask();
        Task<MetadataResult<MetadataSchemaAdmission>>? second = null;
        try
        {
            await barrier.WaitForEntryAsync(cancellationToken);
            second = current.Schema.PrepareAsync(request, new(), cancellationToken).AsTask();
            Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await current.Store.ReserveOperationAsync(new(), cancellationToken)));
            Assert.False(second.IsCompleted);
        }
        finally
        {
            barrier.Release();
            await JoinSettlement(second is null ? first : Task.WhenAll(first, second), current.Faults.AwaitSettlementAsync);
        }
        Success(await first);
        Assert.NotNull(second);
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Failure>(await second);
        Assert.Equal(MetadataSchemaState.Compatible, Success(await current.Schema.InspectAsync(new(), cancellationToken)).State);
    }

    public static async Task FutureAndCorruptAsync(
        IMetadataConformanceSession original, IMetadataConformanceSession corrupt, CancellationToken cancellationToken)
    {
        Success(await original.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), cancellationToken));
        await Seed(original.Store, cancellationToken);
        Success(await original.Faults.SetFutureSchemaAsync(cancellationToken));
        await RejectFuture(original, cancellationToken);
        await using var future = await original.ReopenAsync(cancellationToken);
        await RejectFuture(future, cancellationToken);
        Success(await corrupt.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), cancellationToken));
        var (registry, _) = await Seed(corrupt.Store, cancellationToken);
        Success(await corrupt.Faults.CorruptRecordAsync(registry.Selector, cancellationToken));
        await using var reopened = await corrupt.ReopenAsync(cancellationToken);
        var before = await reopened.Faults.ObserveStateAsync(cancellationToken);
        CorruptFailure(await reopened.Schema.InspectAsync(new(), cancellationToken), MetadataPhase.Schema);
        CorruptFailure(await reopened.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), cancellationToken), MetadataPhase.Schema);
        Assert.Equal(before, await reopened.Faults.ObserveStateAsync(cancellationToken));
    }

    private static async Task RejectFuture(IMetadataConformanceSession session, CancellationToken cancellationToken)
    {
        var before = await session.Faults.ObserveStateAsync(cancellationToken);
        Assert.Equal(MetadataSchemaState.Incompatible, Success(await session.Schema.InspectAsync(new(), cancellationToken)).State);
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await session.Schema.PrepareAsync(
            new MetadataSchemaRequest.CreateIfEmpty(), new(), cancellationToken)));
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await session.Store.ReserveOperationAsync(new(), cancellationToken)));
        Assert.Equal(before, await session.Faults.ObserveStateAsync(cancellationToken));
    }
}
