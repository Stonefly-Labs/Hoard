using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;

namespace Hoard.Metadata.Tests;

public sealed class MetadataValueTests
{
    [Fact]
    public void Canonical_text_preserves_exact_unicode_case_and_escapes_and_rejects_invalid_boundaries()
    {
        foreach (var value in new[] { "A", "a", "\u00e9", "e\u0301", "/a%2fb", new string('a', 1024) })
        {
            Assert.Equal(value, new CanonicalText(value).Value);
        }
        Assert.NotEqual(new CanonicalText("\u00e9"), new CanonicalText("e\u0301"));
        foreach (var value in new[] { "", "a\0", "a\n", "\ud800", "\udc00", new string('a', 1025) })
        {
            Assert.Throws<ArgumentException>(() => new CanonicalText(value));
        }
        Assert.Throws<ArgumentNullException>(() => new CanonicalText(null!));
        Assert.Equal("", new PublicLabel("").Value);
        Assert.Equal(512, new PublicLabel(new string('b', 512)).Value.Length);
        Assert.Throws<ArgumentException>(() => new PublicLabel(new string('b', 513)));
    }

    [Fact]
    public void Ids_revisions_digests_and_instants_reject_missing_or_lossy_values()
    {
        var guid = Guid.Parse("00112233-4455-6677-8899-aabbccddeeff");
        Assert.Equal(guid, new MetadataId(guid).Value);
        Assert.Throws<ArgumentException>(() => new MetadataId(Guid.Empty));
        Assert.Throws<ArgumentException>(() => new MetadataRevision(Guid.Empty));
        var bytes = Enumerable.Range(0, 32).Select(value => (byte)value).ToImmutableArray();
        Assert.Equal(Convert.ToHexStringLower(bytes.AsSpan()), new ArtifactDigest(bytes).Hex);
        Assert.Throws<ArgumentException>(() => new ArtifactDigest(ImmutableArray<byte>.Empty));
        Assert.Throws<ArgumentException>(() => new ArtifactDigest(default(ImmutableArray<byte>)));
        Assert.Equal(0, new MetadataInstant(0).UnixMilliseconds);
        Assert.Equal(253402300799999, new MetadataInstant(253402300799999).UnixMilliseconds);
        Assert.Throws<ArgumentException>(() => new MetadataInstant(-1));
        Assert.Throws<ArgumentException>(() => new MetadataInstant(253402300800000));
        Assert.Throws<ArgumentException>(() => new MetadataInstant(DateTimeOffset.UnixEpoch.AddTicks(1)));
        Assert.Throws<ArgumentException>(() => new MetadataInstant(DateTimeOffset.UnixEpoch.ToOffset(TimeSpan.FromHours(1))));
    }

    [Fact]
    public void Diagnostics_of_values_and_opaque_handles_never_echo_payloads()
    {
        const string canary = "synthetic-canary";
        Assert.DoesNotContain(canary, new CanonicalText(canary).ToString());
        Assert.DoesNotContain(canary, new PublicLabel(canary).ToString());
        Assert.DoesNotContain(canary, new MetadataArtifactEvidence(canary).ToString());
        Assert.DoesNotContain(canary, new MetadataContinuation(canary).ToString());
    }
}
