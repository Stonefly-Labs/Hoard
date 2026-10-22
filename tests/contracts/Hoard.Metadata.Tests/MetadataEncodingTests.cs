using System.Collections.Immutable;
using System.Text;
using Hoard.Abstractions.Metadata;

namespace Hoard.Metadata.Tests;

public sealed class MetadataEncodingTests
{
    [Fact]
    public void Encoding_is_deterministic_and_GUID_keys_use_network_byte_order()
    {
        var id = new MetadataId(Guid.Parse("00112233-4455-6677-8899-aabbccddeeff"));
        var selector = new MetadataSelector.Registry(id);
        var group = new MetadataReadGroup([selector]);
        Assert.Equal(MetadataEncoding.Encode(group).AsSpan().ToArray(), MetadataEncoding.Encode(group).AsSpan().ToArray());
        Assert.Equal("0100112233445566778899aabbccddeeff", Convert.ToHexStringLower(MetadataEncoding.Key(selector).AsSpan()));
        Assert.Contains("00112233445566778899aabbccddeeff", Encoding.UTF8.GetString(MetadataEncoding.Encode(group).AsSpan()));
    }

    [Fact]
    public void Publication_fingerprint_excludes_only_renewable_evidence_not_logical_content_or_expectations()
    {
        var registry = new MetadataId(MetadataTestData.Id(1));
        var package = new MetadataPackageKey(registry, new("nuget"), new("package"));
        var entry = new MetadataCacheEntry
        {
            Identity = new(registry, package.Ecosystem, new("/package"), "GET", new("anonymous")),
            Package = package,
            Status = 200,
            Headers = new([]),
            Digest = new(new string('a', 64)),
            Length = 10,
            Created = new(1),
            Validated = new(2),
            FreshUntil = new(3),
            Revision = new(MetadataTestData.Id(2))
        };
        var ticket = new MetadataOperationTicket(new(MetadataTestData.Id(3)), new(MetadataTestData.Id(4)), new(0), new(86400000));
        MetadataMutationBatch Batch(MetadataCacheEntry record, string evidence, ExpectedRevision expected) =>
            new(ticket, [new MetadataMutation.PublishCacheEntry(record, expected, new(evidence))], new MetadataOption<MetadataLeaseGuard>.None());
        var first = Batch(entry, "first", new ExpectedRevision.Absent());
        var renewed = Batch(entry, "renewed", new ExpectedRevision.Absent());
        Assert.Equal(MetadataEncoding.Fingerprint(first).ToArray(), MetadataEncoding.Fingerprint(renewed).ToArray());
        Assert.NotEqual(MetadataEncoding.Encode(first).ToArray(), MetadataEncoding.Encode(renewed).ToArray());
        Assert.NotEqual(MetadataEncoding.Fingerprint(first).ToArray(),
            MetadataEncoding.Fingerprint(Batch(entry with { Length = 11 }, "first", new ExpectedRevision.Absent())).ToArray());
        Assert.NotEqual(MetadataEncoding.Fingerprint(first).ToArray(),
            MetadataEncoding.Fingerprint(Batch(entry, "first", new ExpectedRevision.Match(entry.Revision))).ToArray());
    }

    [Fact]
    public void Duplicate_targets_invalid_records_and_unguarded_options_do_not_encode()
    {
        var id = new MetadataId(MetadataTestData.Id(1));
        var ticket = new MetadataOperationTicket(id, new(MetadataTestData.Id(2)), new(0), new(86400000));
        var acquire = new MetadataMutation.AcquireLease(new("work"), id, 1);
        Assert.Throws<ArgumentException>(() => MetadataEncoding.Encode(
            new MetadataMutationBatch(ticket, [acquire, acquire], new MetadataOption<MetadataLeaseGuard>.None())));
        Assert.Throws<ArgumentException>(() => MetadataEncoding.Encode(
            new MetadataMutationBatch(ticket, [acquire], new MetadataOption<MetadataLeaseGuard>.Some(new(new("work"), id, 1)))));
        Assert.Throws<ArgumentException>(() => new MetadataHeader("set-cookie", "secret"));
        Assert.Throws<ArgumentException>(() => new MetadataHeader("etag", "x\r\nvalue"));
        Assert.Throws<ArgumentException>(() => new MetadataHeader("etag", new string('a', 513)));
        Assert.Equal(512, new MetadataHeader("etag", new string('a', 512)).Value.Length);
        Assert.Throws<ArgumentException>(() => new MetadataUpstream("https://user:password@example.invalid/"));
        Assert.Throws<ArgumentException>(() => new MetadataUpstream("https://example.invalid/?token=x"));
        Assert.Throws<ArgumentException>(() => new MetadataSecretReference(new string('a', 129), "file", "key"));
        Assert.Throws<ArgumentException>(() => new MetadataRequestIdentity(id, new("nuget"), new("/p"), "get", new("anonymous")));
        Assert.Throws<ArgumentException>(() => new MetadataHeaders(default(ImmutableArray<MetadataHeader>)));
    }
}
