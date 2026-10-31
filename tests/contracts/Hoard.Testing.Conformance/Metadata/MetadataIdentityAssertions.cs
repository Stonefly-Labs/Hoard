using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataIdentityAssertions
{
    public static async Task CanonicalTextAndForbiddenValuesAsync(
        IMetadataStore store, CancellationToken cancellationToken)
    {
        var (registry, _) = await Seed(store, cancellationToken);
        var names = new[] { "Case", "case", "\u00e9", "e\u0301", "%2F", "/" };
        foreach (var name in names)
        { await Commit(store, cancellationToken, new MetadataMutation.PutPackage(Package(registry, name), new ExpectedRevision.Absent())); }
        foreach (var name in names)
        { Assert.Equal(name, (await Read<MetadataPackage>(store, Package(registry, name).Selector, cancellationToken)).Key.Name.Value); }
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.PutPackage(Package(registry, names[0]), new ExpectedRevision.Absent())), new(), cancellationToken)));
        Assert.Throws<ArgumentException>(() => new CanonicalText("\ud800"));
        var userInfo = new UriBuilder(Uri.UriSchemeHttps, "example.invalid")
        { UserName = "synthetic", Password = "synthetic" };
        Assert.Throws<ArgumentException>(() => new MetadataUpstream(userInfo.Uri.AbsoluteUri));
        userInfo.Path = "/private";
        Assert.Throws<ArgumentException>(() => new MetadataRequestIdentity(registry.Id, registry.Ecosystem,
            new(userInfo.Uri.AbsoluteUri), "GET", new("anonymous")));
        Assert.Throws<ArgumentException>(() => new MetadataHeader("authorization", "synthetic"));
        Assert.Throws<ArgumentException>(() => new MetadataHeader("etag", "bad\r\nvalue"));
        Assert.Throws<ArgumentException>(() => new MetadataSecretReference("owner", "resolver", new string('a', 129)));
    }

    public static async Task RegistryIsolationAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, CancellationToken cancellationToken)
    {
        var one = Registry();
        var two = Registry(2);
        var first = Package(one);
        var second = Package(two);
        await Commit(store, cancellationToken, new MetadataMutation.PutRegistry(one, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(two, new ExpectedRevision.Absent()),
            new MetadataMutation.PutPackage(first, new ExpectedRevision.Absent()),
            new MetadataMutation.PutPackage(second, new ExpectedRevision.Absent()));
        var entry = Entry(first);
        await Commit(store, cancellationToken, Publish(authority, entry));
        await Read<MetadataPackage>(store, first.Selector, cancellationToken);
        await Read<MetadataPackage>(store, second.Selector, cancellationToken);
        await Missing(store, Entry(second).Selector, cancellationToken);
        Assert.Single(await Traverse(store, new MetadataPageQuery.Packages(one.Id)
        { PageSize = 100, Continuation = None<MetadataContinuation>() }, cancellationToken));
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await store.CommitAsync(
            Batch(await Ticket(store, cancellationToken), new MetadataMutation.PutPackage(first, new ExpectedRevision.Absent())),
            new(), cancellationToken)));
    }

    public static async Task AuthorizationPartitionIsolationAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, CancellationToken cancellationToken)
    {
        var (_, package) = await Seed(store, cancellationToken);
        var anonymous = Entry(package);
        var authorized = Entry(package, "subject-opaque") with { Digest = Digest(2) };
        await Commit(store, cancellationToken, Publish(authority, anonymous), Publish(authority, authorized));
        Assert.Equal(anonymous.Digest, (await Read<MetadataCacheEntry>(store, anonymous.Selector, cancellationToken)).Digest);
        Assert.Equal(authorized.Digest, (await Read<MetadataCacheEntry>(store, authorized.Selector, cancellationToken)).Digest);
        await Missing(store, Entry(package, "different-subject").Selector, cancellationToken);
        var query = new MetadataPageQuery.CacheEntries(package.Key.RegistryId, new("anonymous"), None<MetadataPackageKey>())
        { PageSize = 100, Continuation = None<MetadataContinuation>() };
        Assert.Single(await Traverse(store, query, cancellationToken));
        Assert.Empty(await Traverse(store, query with { AuthorizationPartition = new("different-subject") }, cancellationToken));
    }
}
