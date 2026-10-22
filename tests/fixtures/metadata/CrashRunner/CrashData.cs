using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;

internal static class CrashData
{
    internal static MetadataId Id(int value) => new(new Guid(value, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1));
    internal static MetadataRevision Revision() => new(Guid.NewGuid());
    internal static MetadataOption<T> None<T>() where T : notnull => new MetadataOption<T>.None();
    internal static MetadataRegistry Registry(int value = 1) => new()
    {
        Id = Id(value),
        Ecosystem = new("nuget"),
        Upstream = new("https://fixture.example.invalid/v3/"),
        Enabled = true,
        Label = new("synthetic"),
        Secret = None<MetadataSecretReference>(),
        PolicyId = value == 1 ? new MetadataOption<MetadataId>.Some(Id(9)) : None<MetadataId>(),
        Revision = Revision()
    };
    internal static MetadataPackage Package(int value = 1) => new()
    {
        Key = new(Id(1), new("nuget"), new("synthetic-" + value)),
        Label = new("synthetic"),
        Revision = Revision()
    };
    internal static MetadataCacheEntry Entry(int value = 1) => new()
    {
        Identity = new(Id(1), new("nuget"), new("/synthetic/" + value), "GET", new("anonymous")),
        Package = Package(value).Key,
        Digest = new(value.ToString("x64")),
        Length = value * 1024L,
        Status = 200,
        Headers = new([new("etag", "\"synthetic\"")]),
        Created = new(0),
        Validated = new(1),
        FreshUntil = new(60000),
        Revision = Revision()
    };
    internal static MetadataPolicy Policy() => new()
    {
        Id = Id(9),
        Scope = new MetadataPolicyScope.Registry(Id(1)),
        MetadataTtlMilliseconds = 1000,
        RetentionMilliseconds = 2000,
        MaximumArtifactBytes = 1000000,
        Immutable = false,
        StaleIfErrorMilliseconds = 0,
        Revision = Revision()
    };
    internal static MetadataAggregateKey Aggregate(int value = 1) => new(Id(1), new("partition-" + value), new(0), new(60000));
    internal static MetadataAggregateDelta Delta(int value) => new()
    { Hits = value, Misses = 1, BytesFetched = 1024, BytesServed = 2048, LatencyMilliseconds = 3, Samples = 1 };
    internal static T Success<T>(MetadataResult<T> result) where T : notnull => result is MetadataResult<T>.Success success
        ? success.Value : throw new InvalidOperationException(result is MetadataResult<T>.Failure failure
            ? $"Fixture operation failed: {failure.Code}/{failure.Phase}." : "Invalid fixture outcome.");
    internal static void Require(bool condition)
    { if (!condition) { throw new InvalidOperationException("Metadata recovery assertion failed."); } }
    internal static MetadataMutationBatch Batch(MetadataOperationTicket ticket, params MetadataMutation[] mutations) => new(ticket, [.. mutations], None<MetadataLeaseGuard>());
    internal static async Task<MetadataCommitReceipt> Commit(MetadataFixtureSession fixture, params MetadataMutation[] mutations) =>
        Success(await fixture.Store.CommitAsync(Batch(Success(await fixture.Store.ReserveOperationAsync(new(), default)), mutations), new(), default));
    internal static ImmutableArray<MetadataSelector> Selectors(int value = 1) => value == 1
        ? [Registry().Selector, Package().Selector, Policy().Selector, Entry().Selector, new MetadataSelector.Artifact(Entry().Digest),
            new MetadataSelector.Lease(new("maintenance-1")), new MetadataSelector.Aggregate(Aggregate())]
        : [Package(2).Selector, Entry(2).Selector, new MetadataSelector.Artifact(Entry(2).Digest),
            new MetadataSelector.Lease(new("maintenance-2")), new MetadataSelector.Aggregate(Aggregate(2))];
    internal static async Task<MetadataReadSnapshot> Read(MetadataFixtureSession fixture, int value = 1) =>
        Success(await fixture.Store.ReadAsync(new(Selectors(value)), new(), default));
    internal static async Task Seed(MetadataFixtureSession fixture)
    {
        var entry = Entry();
        await Commit(fixture, new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()),
            new MetadataMutation.PutPolicy(Policy(), new ExpectedRevision.Absent()),
            new MetadataMutation.PutPackage(Package(), new ExpectedRevision.Absent()),
            new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), fixture.Authority.Register(entry.Digest, entry.Length)),
            new MetadataMutation.AcquireLease(new("maintenance-1"), Id(11), 300),
            new MetadataMutation.AddAggregateContribution(Aggregate(), Delta(5)),
            new MetadataMutation.PutRegistry(Registry(2), new ExpectedRevision.Absent()));
    }
    internal static MetadataMutationBatch RenewEvidence(MetadataFixtureSession fixture, MetadataMutationBatch batch) =>
        new(batch.Ticket, batch.Mutations.Select(mutation => mutation is MetadataMutation.PublishCacheEntry publication
            ? publication with { Evidence = fixture.Authority.Register(publication.Record.Digest, publication.Record.Length) } : mutation).ToImmutableArray(), batch.LeaseGuard);
}

internal sealed class CrashClock : TimeProvider
{
    public override DateTimeOffset GetUtcNow() => DateTimeOffset.FromUnixTimeMilliseconds(1_800_000_000_000);
}
