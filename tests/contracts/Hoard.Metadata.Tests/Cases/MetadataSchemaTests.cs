using System.Security.Cryptography;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataSchemaTests
{
    [Fact]
    public async Task MP33_Unrelated_and_partial_layouts_are_not_empty_or_permission_to_create()
    {
        foreach (var partial in new[] { false, true })
        {
            await using var fixture = MetadataFixtureSession.CreateFromEnvironment(new MetadataTestClock());
            Success(await fixture.CreateUnrecognizedLayoutForTestAsync(partial));
            var before = fixture.DatabasePath is { } path ? SHA256.HashData(File.ReadAllBytes(path)) : [];
            Assert.Equal(MetadataSchemaState.Incompatible, Success(await fixture.Schema.InspectAsync(new(), default)).State);
            Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await fixture.Schema.PrepareAsync(
                new MetadataSchemaRequest.CreateIfEmpty(), new(), default)));
            if (fixture.DatabasePath is { } database) { Assert.Equal(before, SHA256.HashData(File.ReadAllBytes(database))); }
        }
    }

    [Fact]
    public async Task MP32_Old_schema_requires_explicit_authorized_upgrade_and_preserves_records()
    {
        var clock = new MetadataTestClock();
        await using var initial = MetadataFixtureSession.Create(
            Environment.GetEnvironmentVariable("HOARD_METADATA_PROVIDER")!, clock, compatibleSchema: "fixture-sqlite-v1");
        var originalAdmission = Success(await initial.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var (registry, package) = await Seed(initial);
        var entry = Entry(package);
        var receipt = await Commit(initial, Publish(initial, entry),
            new MetadataMutation.AddAggregateContribution(Aggregate(registry), Delta(7)),
            new MetadataMutation.AcquireLease(new("maintenance"), Id(55), 300));
        entry = await Read<MetadataCacheEntry>(initial, entry.Selector);
        await using var upgraded = await initial.ReopenAsync();
        Assert.Equal(MetadataSchemaState.UpgradeRequired, Success(await upgraded.Schema.InspectAsync(new(), default)).State);
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await upgraded.Store.ReserveOperationAsync(new(), default)));
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await upgraded.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default)));
        var point = await upgraded.AuthorizeUpgradeAsync();
        var admission = Success(await upgraded.Schema.PrepareAsync(new MetadataSchemaRequest.Upgrade(
            point.SchemaVersion, point.SchemaVersion.Replace("-v1", "-v2", StringComparison.Ordinal), point), new(), default));
        Assert.NotEqual(originalAdmission.Epoch, admission.Epoch);
        Assert.Equal(registry, await Read<MetadataRegistry>(upgraded, registry.Selector));
        Assert.Equal(package, await Read<MetadataPackage>(upgraded, package.Selector));
        var restoredEntry = await Read<MetadataCacheEntry>(upgraded, entry.Selector);
        Assert.True(MetadataEncoding.Encode(entry).AsSpan().SequenceEqual(MetadataEncoding.Encode(restoredEntry).AsSpan()));
        Assert.Equal(7, (await Read<MetadataAccessAggregate>(upgraded, new MetadataSelector.Aggregate(Aggregate(registry)))).Counters.Hits);
        Assert.Equal(MetadataFailureCode.ReconciliationExpired, Failed(await upgraded.Store.ReconcileAsync(receipt.Ticket, new(), default)));
        await using var reopened = await upgraded.ReopenAsync();
        Assert.Equal(MetadataSchemaState.Compatible, Success(await reopened.Schema.InspectAsync(new(), default)).State);
        Success(await reopened.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default));
        Assert.Equal(admission.Epoch, Success(await reopened.Schema.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default)).Epoch);
        Assert.Equal(registry, await Read<MetadataRegistry>(reopened, registry.Selector));
    }

    [Fact]
    public async Task MP33_Future_schema_and_recognized_corruption_are_never_created_over()
    {
        await using var original = await OpenAsync();
        await Seed(original);
        Success(await original.MakeFutureSchemaForTestAsync());
        var files = original.DatabasePath is { } current
            ? new[] { current, current + "-wal" }.Where(File.Exists).ToDictionary(file => file, file => SHA256.HashData(File.ReadAllBytes(file)))
            : [];
        Assert.Equal(MetadataSchemaState.Incompatible, Success(await original.Schema.InspectAsync(new(), default)).State);
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await original.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default)));
        foreach (var (file, digest) in files) { Assert.Equal(digest, SHA256.HashData(File.ReadAllBytes(file))); }
        await using var future = await original.ReopenAsync();
        var before = future.DatabasePath is { } path ? SHA256.HashData(File.ReadAllBytes(path)) : [];
        Assert.Equal(MetadataSchemaState.Incompatible, Success(await future.Schema.InspectAsync(new(), default)).State);
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await future.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default)));
        if (future.DatabasePath is { } database) { Assert.Equal(before, SHA256.HashData(File.ReadAllBytes(database))); }
        await using var corrupt = await OpenAsync();
        var (registry, _) = await Seed(corrupt);
        Success(await corrupt.CorruptRecordForTestAsync(registry.Selector));
        await using var reopened = await corrupt.ReopenAsync();
        Assert.Equal(MetadataFailureCode.CorruptState, Failed(await reopened.Schema.InspectAsync(new(), default)));
        Assert.Equal(MetadataFailureCode.CorruptState, Failed(await reopened.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default)));
    }

    [Fact]
    public async Task MP34_Unsupported_and_foreign_upgrade_authorizations_leave_old_state_unchanged()
    {
        var clock = new MetadataTestClock();
        await using var original = MetadataFixtureSession.Create(
            Environment.GetEnvironmentVariable("HOARD_METADATA_PROVIDER")!, clock, compatibleSchema: "fixture-sqlite-v1");
        Success(await original.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var (registry, _) = await Seed(original);
        await using var current = await original.ReopenAsync();
        var point = await current.AuthorizeUpgradeAsync();
        var target = point.SchemaVersion.Replace("-v1", "-v2", StringComparison.Ordinal);
        foreach (var invalid in new[] { "", new string('v', 65), "v\u0100", "v\n" })
        {
            Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await current.Schema.PrepareAsync(
                new MetadataSchemaRequest.Upgrade(point.SchemaVersion, invalid, point), new(), default)));
        }
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Failure>(await current.Schema.PrepareAsync(
            new MetadataSchemaRequest.Upgrade(point.SchemaVersion, target, point with { Id = Id(999) }), new(), default));
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Failure>(await current.Schema.PrepareAsync(
            new MetadataSchemaRequest.Upgrade(point.SchemaVersion, "unsupported", point), new(), default));
        Assert.Equal(MetadataSchemaState.UpgradeRequired, Success(await current.Schema.InspectAsync(new(), default)).State);
        Success(await current.Schema.PrepareAsync(new MetadataSchemaRequest.Upgrade(point.SchemaVersion, target, point), new(), default));
        Assert.Equal(registry, await Read<MetadataRegistry>(current, registry.Selector));
    }

    [Fact]
    public async Task MP35_Upgrade_exclusion_prevents_partial_admission_and_has_one_winner()
    {
        var clock = new MetadataTestClock();
        await using var original = MetadataFixtureSession.Create(
            Environment.GetEnvironmentVariable("HOARD_METADATA_PROVIDER")!, clock, compatibleSchema: "fixture-sqlite-v1");
        Success(await original.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await Seed(original);
        await using var current = await original.ReopenAsync();
        var point = await current.AuthorizeUpgradeAsync();
        var request = new MetadataSchemaRequest.Upgrade(point.SchemaVersion,
            point.SchemaVersion.Replace("-v1", "-v2", StringComparison.Ordinal), point);
        await using var barrier = new MetadataTestBarrier();
        await using var observation = await CommonObservations(current)(
            MetadataObservationPoint.SchemaCandidatePrepared, () => new(barrier.HoldAsync()), default);
        var first = current.Schema.PrepareAsync(request, new(), default).AsTask();
        await barrier.Entered;
        var second = current.Schema.PrepareAsync(request, new(), default).AsTask();
        Assert.Equal(MetadataFailureCode.IncompatibleSchema, Failed(await current.Store.ReserveOperationAsync(new(), default)));
        Assert.False(second.IsCompleted);
        barrier.Release();
        Success(await first);
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Failure>(await second);
        Assert.Equal(MetadataSchemaState.Compatible, Success(await current.Schema.InspectAsync(new(), default)).State);
    }
}
