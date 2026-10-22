using Hoard.Abstractions.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataIdentityTests
{
    [Fact]
    public async Task MP02_Registry_identity_is_exact_and_isolated()
    {
        await using var fixture = await OpenAsync();
        var one = Registry();
        var two = Registry(2);
        var first = Package(one);
        var second = Package(two);
        await Commit(fixture, new MetadataMutation.PutRegistry(one, new ExpectedRevision.Absent()),
            new MetadataMutation.PutRegistry(two, new ExpectedRevision.Absent()),
            new MetadataMutation.PutPackage(first, new ExpectedRevision.Absent()),
            new MetadataMutation.PutPackage(second, new ExpectedRevision.Absent()));
        var entry = Entry(first);
        await Commit(fixture, Publish(fixture, entry));
        await Read<MetadataPackage>(fixture, first.Selector);
        await Read<MetadataPackage>(fixture, second.Selector);
        await Missing(fixture, Entry(second).Selector);
        Assert.Single(await Traverse(fixture, new MetadataPageQuery.Packages(one.Id) { PageSize = 100, Continuation = None<MetadataContinuation>() }));
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await fixture.Store.CommitAsync(
            Batch(await Ticket(fixture), new MetadataMutation.PutPackage(first, new ExpectedRevision.Absent())), new(), default)));
    }

    [Fact]
    public async Task MP03_Anonymous_and_authenticated_request_partitions_remain_separate()
    {
        await using var fixture = await OpenAsync();
        var (_, package) = await Seed(fixture);
        var anonymous = Entry(package);
        var authorized = Entry(package, "subject-opaque") with { Digest = Digest(2) };
        await Commit(fixture, Publish(fixture, anonymous), Publish(fixture, authorized));
        Assert.Equal(anonymous.Digest, (await Read<MetadataCacheEntry>(fixture, anonymous.Selector)).Digest);
        Assert.Equal(authorized.Digest, (await Read<MetadataCacheEntry>(fixture, authorized.Selector)).Digest);
        await Missing(fixture, Entry(package, "different-subject").Selector);
        var query = new MetadataPageQuery.CacheEntries(package.Key.RegistryId, new("anonymous"), None<MetadataPackageKey>())
        { PageSize = 100, Continuation = None<MetadataContinuation>() };
        Assert.Single(await Traverse(fixture, query));
        Assert.Empty(await Traverse(fixture, query with { AuthorizationPartition = new("different-subject") }));
    }

    [Fact]
    public async Task MP04_Canonical_text_is_not_normalized_and_forbidden_credentials_are_rejected()
    {
        await using var fixture = await OpenAsync();
        var (registry, _) = await Seed(fixture);
        var names = new[] { "Case", "case", "\u00e9", "e\u0301", "%2F", "/" };
        foreach (var name in names)
        { await Commit(fixture, new MetadataMutation.PutPackage(Package(registry, name), new ExpectedRevision.Absent())); }
        foreach (var name in names)
        { Assert.Equal(name, (await Read<MetadataPackage>(fixture, Package(registry, name).Selector)).Key.Name.Value); }
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.PutPackage(Package(registry, names[0]), new ExpectedRevision.Absent())), new(), default)));
        Assert.Throws<ArgumentException>(() => new CanonicalText("\ud800"));
        Assert.Throws<ArgumentException>(() => new MetadataUpstream("https://user:password@example.invalid"));
        Assert.Throws<ArgumentException>(() => new MetadataRequestIdentity(registry.Id, registry.Ecosystem,
            new("https://user:password@example.invalid/private"), "GET", new("anonymous")));
        Assert.Throws<ArgumentException>(() => new MetadataHeader("authorization", "synthetic"));
        Assert.Throws<ArgumentException>(() => new MetadataHeader("etag", "bad\r\nvalue"));
        Assert.Throws<ArgumentException>(() => new MetadataSecretReference("owner", "resolver", new string('a', 129)));
    }
}
