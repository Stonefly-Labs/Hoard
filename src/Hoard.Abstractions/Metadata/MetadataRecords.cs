using System.Collections.Immutable;
using System.Text;
using System.Text.Json.Serialization;

namespace Hoard.Abstractions.Metadata;

public sealed record MetadataSecretReference : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataSecretReference(string ownerId, string resolverId, string key)
    {
        OwnerId = MetadataValidation.Text(ownerId, 1, 128);
        ResolverId = MetadataValidation.Text(resolverId, 1, 128);
        Key = MetadataValidation.Text(key, 1, 128);
    }
    public string OwnerId { get; }
    public string ResolverId { get; }
    public string Key { get; }
}

public sealed record MetadataUpstream : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataUpstream(string value)
    {
        MetadataValidation.Text(value, 1, 2048);
        MetadataValidation.Require(Uri.TryCreate(value, UriKind.Absolute, out var uri)
            && uri.Scheme is "http" or "https" && uri.UserInfo.Length == 0
            && uri.Query.Length == 0 && uri.Fragment.Length == 0 && uri.Host.Length > 0);
        Value = value;
    }
    public string Value { get; }
}

public sealed record MetadataPackageKey(MetadataId RegistryId, CanonicalText Ecosystem, CanonicalText Name) : MetadataDiagnostic;
public sealed record MetadataRequestIdentity : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataRequestIdentity(MetadataId registryId, CanonicalText ecosystem, CanonicalText target,
        string method, CanonicalText authorizationPartition)
    {
        ArgumentNullException.ThrowIfNull(registryId);
        ArgumentNullException.ThrowIfNull(ecosystem);
        ArgumentNullException.ThrowIfNull(target);
        ArgumentNullException.ThrowIfNull(authorizationPartition);
        ArgumentNullException.ThrowIfNull(method);
        MetadataValidation.Require(method.Length is >= 1 and <= 16
            && method.All(character => character is >= 'A' and <= 'Z' or >= '0' and <= '9'
                || "!#$%&'*+-.^_`|~".Contains(character, StringComparison.Ordinal)));
        MetadataValidation.Require(!Uri.TryCreate(target.Value, UriKind.Absolute, out var uri) || uri.UserInfo.Length == 0);
        RegistryId = registryId;
        Ecosystem = ecosystem;
        Target = target;
        Method = method;
        AuthorizationPartition = authorizationPartition;
    }
    public MetadataId RegistryId { get; }
    public CanonicalText Ecosystem { get; }
    public CanonicalText Target { get; }
    public string Method { get; }
    public CanonicalText AuthorizationPartition { get; }
}

[JsonPolymorphic(TypeDiscriminatorPropertyName = "$scope")]
[JsonDerivedType(typeof(MetadataPolicyScope.Global), "global")]
[JsonDerivedType(typeof(MetadataPolicyScope.Registry), "registry")]
public abstract record MetadataPolicyScope : MetadataDiagnostic
{
    private MetadataPolicyScope() { }
    public sealed record Global : MetadataPolicyScope;
    public sealed record Registry(MetadataId Id) : MetadataPolicyScope;
}

public sealed record MetadataAggregateKey(
    MetadataId RegistryId, CanonicalText AuthorizationPartition, MetadataInstant Start, MetadataInstant End) : MetadataDiagnostic;

public sealed record MetadataHeader : MetadataDiagnostic
{
    private static readonly string[] Allowed =
        ["content-type", "cache-control", "etag", "last-modified", "expires", "vary", "content-language"];
    [JsonConstructor]
    public MetadataHeader(string name, string value)
    {
        MetadataValidation.Require(Allowed.Contains(name, StringComparer.Ordinal));
        MetadataValidation.Text(value, 0, name == "etag" ? 512 : 8192);
        Name = name;
        Value = value;
    }
    public string Name { get; }
    public string Value { get; }
}

public sealed record MetadataHeaders : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataHeaders(ImmutableArray<MetadataHeader> values)
    {
        Values = MetadataValidation.Collection(values, 0, 32);
        var bytes = 0;
        foreach (var header in values)
        {
            ArgumentNullException.ThrowIfNull(header);
            bytes = checked(bytes + Encoding.UTF8.GetByteCount(header.Name) + Encoding.UTF8.GetByteCount(header.Value));
        }
        MetadataValidation.Require(bytes <= 8192);
    }
    public ImmutableArray<MetadataHeader> Values { get; }
}

[JsonPolymorphic(TypeDiscriminatorPropertyName = "$record")]
[JsonDerivedType(typeof(MetadataRegistry), "registry")]
[JsonDerivedType(typeof(MetadataPackage), "package")]
[JsonDerivedType(typeof(MetadataPolicy), "policy")]
[JsonDerivedType(typeof(MetadataCacheEntry), "entry")]
[JsonDerivedType(typeof(MetadataArtifactState), "artifact")]
[JsonDerivedType(typeof(MetadataWorkLease), "lease")]
[JsonDerivedType(typeof(MetadataAccessAggregate), "aggregate")]
public abstract record MetadataRecord : MetadataDiagnostic
{
    private protected MetadataRecord() { }
    public required MetadataRevision Revision { get; init; }
    [JsonIgnore]
    public abstract MetadataSelector Selector { get; }
}

public sealed record MetadataRegistry : MetadataRecord
{
    public required MetadataId Id { get; init; }
    public required CanonicalText Ecosystem { get; init; }
    public required MetadataUpstream Upstream { get; init; }
    public required bool Enabled { get; init; }
    public required MetadataOption<MetadataId> PolicyId { get; init; }
    public required MetadataOption<MetadataSecretReference> Secret { get; init; }
    public required PublicLabel Label { get; init; }
    public override MetadataSelector Selector => new MetadataSelector.Registry(Id);
}

public sealed record MetadataPackage : MetadataRecord
{
    public required MetadataPackageKey Key { get; init; }
    public required PublicLabel Label { get; init; }
    public override MetadataSelector Selector => new MetadataSelector.Package(Key);
}

public sealed record MetadataPolicy : MetadataRecord
{
    public required MetadataId Id { get; init; }
    public required MetadataPolicyScope Scope { get; init; }
    public required long MetadataTtlMilliseconds { get; init; }
    public required long RetentionMilliseconds { get; init; }
    public required long MaximumArtifactBytes { get; init; }
    public required bool Immutable { get; init; }
    public required long StaleIfErrorMilliseconds { get; init; }
    public override MetadataSelector Selector => new MetadataSelector.Policy(Id);
}

public sealed record MetadataCacheEntry : MetadataRecord
{
    public required MetadataRequestIdentity Identity { get; init; }
    public required MetadataPackageKey Package { get; init; }
    public required int Status { get; init; }
    public required MetadataHeaders Headers { get; init; }
    public required ArtifactDigest Digest { get; init; }
    public required long Length { get; init; }
    public required MetadataInstant Created { get; init; }
    public required MetadataInstant Validated { get; init; }
    public required MetadataInstant FreshUntil { get; init; }
    public override MetadataSelector Selector => new MetadataSelector.CacheEntry(Identity);
}

public sealed record MetadataArtifactState : MetadataRecord
{
    public required ArtifactDigest Digest { get; init; }
    public required long Length { get; init; }
    public required long LiveReferences { get; init; }
    public override MetadataSelector Selector => new MetadataSelector.Artifact(Digest);
}

public sealed record MetadataWorkLease : MetadataRecord
{
    public required CanonicalText Resource { get; init; }
    public required MetadataOption<MetadataId> Owner { get; init; }
    public required long Generation { get; init; }
    public required MetadataInstant Acquired { get; init; }
    public required MetadataInstant Expires { get; init; }
    public override MetadataSelector Selector => new MetadataSelector.Lease(Resource);
}

public sealed record MetadataAggregateDelta : MetadataDiagnostic
{
    public required long Hits { get; init; }
    public required long Misses { get; init; }
    public required long BytesServed { get; init; }
    public required long BytesFetched { get; init; }
    public required long LatencyMilliseconds { get; init; }
    public required long Samples { get; init; }
}

public sealed record MetadataAccessAggregate : MetadataRecord
{
    public required MetadataAggregateKey Key { get; init; }
    public required MetadataAggregateDelta Counters { get; init; }
    public override MetadataSelector Selector => new MetadataSelector.Aggregate(Key);
}
