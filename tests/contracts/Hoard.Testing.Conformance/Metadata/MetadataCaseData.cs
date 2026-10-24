using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;

namespace Hoard.Testing.Conformance.Metadata;

internal static class MetadataCaseData
{
    public static MetadataId Id(int value) => new(new Guid(value, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1));
    public static MetadataOption<T> None<T>() where T : notnull => new MetadataOption<T>.None();
    public static T Success<T>(MetadataResult<T> result) where T : notnull => result switch
    {
        MetadataResult<T>.Success success => success.Value,
        MetadataResult<T>.Failure failure => throw new Xunit.Sdk.XunitException($"Expected metadata success; got {failure.Code}/{failure.Phase}."),
        _ => throw new Xunit.Sdk.XunitException("Unknown metadata outcome.")
    };
    public static MetadataFailureCode Failed<T>(MetadataResult<T> result) where T : notnull =>
        Assert.IsType<MetadataResult<T>.Failure>(result).Code;
    public static async ValueTask<MetadataOperationTicket> Ticket(IMetadataStore store, CancellationToken cancellationToken) =>
        Success(await store.ReserveOperationAsync(new(), cancellationToken));
    public static MetadataMutationBatch Batch(MetadataOperationTicket ticket, params MetadataMutation[] mutations) =>
        new(ticket, [.. mutations], None<MetadataLeaseGuard>());
    public static async ValueTask<MetadataCommitReceipt> Commit(
        IMetadataStore store, CancellationToken cancellationToken, params MetadataMutation[] mutations) =>
        Success(await store.CommitAsync(Batch(await Ticket(store, cancellationToken), mutations), new(), cancellationToken));
    public static async ValueTask<T> Read<T>(
        IMetadataStore store, MetadataSelector key, CancellationToken cancellationToken) where T : MetadataRecord =>
        Assert.IsType<T>(Assert.IsType<MetadataReadItem.Found>(
            Success(await store.ReadAsync(new([key]), new(), cancellationToken)).Items[0]).Record);
    public static async ValueTask Missing(IMetadataStore store, MetadataSelector key, CancellationToken cancellationToken) =>
        Assert.IsType<MetadataReadItem.NotFound>(Success(await store.ReadAsync(new([key]), new(), cancellationToken)).Items[0]);
    public static MetadataRegistry Registry(int value = 1) => new()
    {
        Id = Id(value),
        Ecosystem = new("nuget"),
        Upstream = new("https://packages.example.invalid/v3/"),
        Enabled = true,
        Label = new("synthetic registry"),
        PolicyId = None<MetadataId>(),
        Secret = None<MetadataSecretReference>(),
        Revision = new(Guid.NewGuid())
    };
    public static MetadataPackage Package(MetadataRegistry registry, string name = "example.package") => new()
    {
        Key = new(registry.Id, registry.Ecosystem, new(name)),
        Label = new("synthetic package"),
        Revision = new(Guid.NewGuid())
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
        Revision = new(Guid.NewGuid())
    };
    public static MetadataAggregateKey Aggregate(MetadataRegistry registry, string partition = "anonymous") =>
        new(registry.Id, new(partition), new(0), new(86400000));
    public static MetadataAggregateDelta Delta(long hits = 1) => new()
    { Hits = hits, Misses = 0, BytesServed = 0, BytesFetched = 0, LatencyMilliseconds = 0, Samples = 1 };
    public static async ValueTask<(MetadataRegistry Registry, MetadataPackage Package)> Seed(
        IMetadataStore store, CancellationToken cancellationToken)
    {
        var registry = Registry();
        var package = Package(registry);
        await Commit(store, cancellationToken, new MetadataMutation.PutPackage(package, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        return (await Read<MetadataRegistry>(store, registry.Selector, cancellationToken),
            await Read<MetadataPackage>(store, package.Selector, cancellationToken));
    }
    public static MetadataPageQuery Registries(int count = 100, MetadataOption<MetadataContinuation>? continuation = null) =>
        new MetadataPageQuery.Registries { PageSize = count, Continuation = continuation ?? None<MetadataContinuation>() };
    public static async ValueTask<ImmutableArray<MetadataRecord>> Traverse(
        IMetadataStore store, MetadataPageQuery query, CancellationToken cancellationToken)
    {
        var records = ImmutableArray.CreateBuilder<MetadataRecord>();
        for (var pages = 0; pages < 1000; pages++)
        {
            var page = Success(await store.ReadPageAsync(query, new(), cancellationToken));
            records.AddRange(page.Records);
            if (page.Continuation is MetadataOption<MetadataContinuation>.None) { return records.ToImmutable(); }
            query = query with { Continuation = page.Continuation };
        }
        throw new Xunit.Sdk.XunitException("Metadata traversal did not terminate.");
    }
}
