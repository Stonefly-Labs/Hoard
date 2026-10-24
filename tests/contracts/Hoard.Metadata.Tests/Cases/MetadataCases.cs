using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Metadata.Tests;

internal static class MetadataCases
{
    public static IMetadataConformanceAuthority CommonAuthority(MetadataFixtureSession fixture) =>
        new PublicationAuthority(fixture.Authority);

    private sealed class PublicationAuthority(ControlledPublicationAuthority authority) : IMetadataConformanceAuthority
    {
        public int Acquisitions => authority.Acquisitions;
        public int ActiveGuards => authority.ActiveGuards;
        public MetadataArtifactEvidence Register(ArtifactDigest digest, long length) => authority.Register(digest, length);
        public void Revoke(MetadataArtifactEvidence evidence) => authority.Revoke(evidence);
        public ValueTask<MetadataResult<IMetadataPublicationGuard>> AcquireAsync(
            MetadataArtifactEvidence evidence, MetadataCallOptions options, CancellationToken cancellationToken) =>
            authority.AcquireAsync(evidence, options, cancellationToken);
    }

    public static MetadataId Id(int value) => new(MetadataTestData.Id(value));
    public static MetadataRevision Revision() => new(Guid.NewGuid());
    public static MetadataOption<T> None<T>() where T : notnull => new MetadataOption<T>.None();
    public static T Success<T>(MetadataResult<T> result) where T : notnull => result switch
    {
        MetadataResult<T>.Success success => success.Value,
        MetadataResult<T>.Failure failure => throw new Xunit.Sdk.XunitException($"Expected metadata success; got {failure.Code}/{failure.Phase}."),
        _ => throw new Xunit.Sdk.XunitException("Unknown metadata outcome.")
    };
    public static MetadataFailureCode Failed<T>(MetadataResult<T> result) where T : notnull =>
        Assert.IsType<MetadataResult<T>.Failure>(result).Code;
    public static async ValueTask<MetadataFixtureSession> OpenAsync(MetadataTestClock? clock = null)
    {
        var fixture = MetadataFixtureSession.CreateFromEnvironment(clock ?? new());
        try
        {
            Success(await fixture.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
            return fixture;
        }
        catch { await fixture.DisposeAsync(); throw; }
    }
    public static async ValueTask<MetadataOperationTicket> Ticket(MetadataFixtureSession fixture) =>
        Success(await fixture.Store.ReserveOperationAsync(new(), default));
    public static MetadataMutationBatch Batch(MetadataOperationTicket ticket, params MetadataMutation[] mutations) =>
        new(ticket, [.. mutations], None<MetadataLeaseGuard>());
    public static async ValueTask<MetadataCommitReceipt> Commit(MetadataFixtureSession fixture, params MetadataMutation[] mutations) =>
        Success(await fixture.Store.CommitAsync(Batch(await Ticket(fixture), mutations), new(), default));
    public static async ValueTask<T> Read<T>(MetadataFixtureSession fixture, MetadataSelector key) where T : MetadataRecord =>
        Assert.IsType<T>(Assert.IsType<MetadataReadItem.Found>(
            Success(await fixture.Store.ReadAsync(new([key]), new(), default)).Items[0]).Record);
    public static async ValueTask Missing(MetadataFixtureSession fixture, MetadataSelector key) =>
        Assert.IsType<MetadataReadItem.NotFound>(Success(await fixture.Store.ReadAsync(new([key]), new(), default)).Items[0]);
    public static MetadataRegistry Registry(int value = 1) => new()
    {
        Id = Id(value),
        Ecosystem = new("nuget"),
        Upstream = new("https://packages.example.invalid/v3/"),
        Enabled = true,
        Label = new("synthetic registry"),
        PolicyId = None<MetadataId>(),
        Secret = None<MetadataSecretReference>(),
        Revision = Revision()
    };
    public static MetadataPackage Package(MetadataRegistry registry, string name = "example.package") => new()
    {
        Key = new(registry.Id, registry.Ecosystem, new(name)),
        Label = new("synthetic package"),
        Revision = Revision()
    };
    public static MetadataPolicy Policy(int value = 9) => new()
    {
        Id = Id(value),
        Scope = new MetadataPolicyScope.Global(),
        MetadataTtlMilliseconds = 31536000000,
        RetentionMilliseconds = 0,
        MaximumArtifactBytes = long.MaxValue,
        Immutable = false,
        StaleIfErrorMilliseconds = 1,
        Revision = Revision()
    };
    public static ArtifactDigest Digest(int value = 1) => new(value.ToString("x64"));
    public static MetadataCacheEntry Entry(MetadataPackage package, string partition = "anonymous", string target = "/flat/example/1.0.0") => new()
    {
        Identity = new(package.Key.RegistryId, package.Key.Ecosystem, new(target), "GET", new(partition)),
        Package = package.Key,
        Digest = Digest(),
        Length = 1024,
        Status = 200,
        Headers = new([new("etag", "\"synthetic\""), new("cache-control", "max-age=60")]),
        Created = new(0),
        Validated = new(1),
        FreshUntil = new(253402300799999),
        Revision = Revision()
    };
    public static MetadataAggregateKey Aggregate(MetadataRegistry registry, string partition = "anonymous") =>
        new(registry.Id, new(partition), new(0), new(86400000));
    public static MetadataAggregateDelta Delta(long hits = 1) => new()
    { Hits = hits, Misses = 0, BytesServed = 0, BytesFetched = 0, LatencyMilliseconds = 0, Samples = 1 };
    public static async ValueTask<(MetadataRegistry Registry, MetadataPackage Package)> Seed(MetadataFixtureSession fixture)
    {
        var registry = Registry();
        var package = Package(registry);
        await Commit(fixture, new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        return (await Read<MetadataRegistry>(fixture, registry.Selector), await Read<MetadataPackage>(fixture, package.Selector));
    }
    public static MetadataMutation.PublishCacheEntry Publish(MetadataFixtureSession fixture, MetadataCacheEntry entry,
        ExpectedRevision? expected = null) =>
        new(entry, expected ?? new ExpectedRevision.Absent(), fixture.Authority.Register(entry.Digest, entry.Length));
    public static MetadataPageQuery Registries(int count = 100, MetadataOption<MetadataContinuation>? continuation = null) =>
        new MetadataPageQuery.Registries { PageSize = count, Continuation = continuation ?? None<MetadataContinuation>() };
    public static async ValueTask<ImmutableArray<MetadataRecord>> Traverse(MetadataFixtureSession fixture, MetadataPageQuery query)
    {
        var records = ImmutableArray.CreateBuilder<MetadataRecord>();
        for (var pages = 0; pages < 1000; pages++)
        {
            var page = Success(await fixture.Store.ReadPageAsync(query, new(), default));
            records.AddRange(page.Records);
            if (page.Continuation is MetadataOption<MetadataContinuation>.None) { return records.ToImmutable(); }
            query = query with { Continuation = page.Continuation };
        }
        throw new Xunit.Sdk.XunitException("Metadata traversal did not terminate.");
    }
}
