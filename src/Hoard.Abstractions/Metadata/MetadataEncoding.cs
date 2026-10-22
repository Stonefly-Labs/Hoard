using System.Buffers.Binary;
using System.Collections.Immutable;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace Hoard.Abstractions.Metadata;

public static class MetadataEncoding
{
    public const int MaximumBytes = 1024 * 1024;
    private static readonly JsonSerializerOptions Options = new()
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        Converters = { new MetadataGuidConverter() }
    };

    public static ImmutableArray<byte> Encode(MetadataReadGroup value)
    {
        ArgumentNullException.ThrowIfNull(value);
        foreach (var selector in value.Selectors) { Validate(selector); }
        return EncodeValue(value);
    }

    public static ImmutableArray<byte> Encode(MetadataRecord value)
    {
        Validate(value);
        return EncodeValue(value);
    }

    public static ImmutableArray<byte> Encode(MetadataMutationBatch value)
    {
        Validate(value);
        return EncodeValue(value);
    }

    public static ImmutableArray<byte> Encode(MetadataPageQuery value)
    {
        Validate(value);
        return EncodeValue(value);
    }

    public static ImmutableArray<byte> Encode(MetadataReadSnapshot value)
    {
        ArgumentNullException.ThrowIfNull(value);
        MetadataValidation.Collection(value.Items, 1, 64);
        foreach (var item in value.Items)
        {
            switch (item)
            {
                case MetadataReadItem.Found found: Validate(found.Record); break;
                case MetadataReadItem.NotFound absent: Validate(absent.Selector); break;
                default: throw new ArgumentException("Invalid metadata read item.");
            }
        }
        return EncodeValue(value);
    }

    public static ImmutableArray<byte> Encode(MetadataPage value)
    {
        ArgumentNullException.ThrowIfNull(value);
        MetadataValidation.Collection(value.Records, 0, 100);
        ArgumentNullException.ThrowIfNull(value.Continuation);
        foreach (var record in value.Records) { Validate(record); }
        return EncodeValue(value);
    }

    public static ImmutableArray<byte> Encode(MetadataCommitReceipt value)
    {
        ArgumentNullException.ThrowIfNull(value);
        ValidateTicket(value.Ticket);
        ArgumentNullException.ThrowIfNull(value.CommitId);
        MetadataValidation.Collection(value.Revisions, 1, 64);
        MetadataValidation.Collection(value.References, 0, 128);
        var targets = new HashSet<MetadataSelector>();
        foreach (var item in value.Revisions)
        {
            ArgumentNullException.ThrowIfNull(item);
            Validate(item.Target);
            ArgumentNullException.ThrowIfNull(item.Revision);
            MetadataValidation.Require(targets.Add(item.Target));
        }
        var digests = new HashSet<ArtifactDigest>();
        foreach (var item in value.References)
        {
            ArgumentNullException.ThrowIfNull(item);
            MetadataValidation.Require(item is { Digest: not null, Revision: not null, LiveReferences: >= 0 } && digests.Add(item.Digest));
        }
        return EncodeValue(value);
    }

    public static ImmutableArray<byte> Fingerprint(MetadataMutationBatch value)
    {
        Validate(value);
        var node = JsonSerializer.SerializeToNode(value, Options)!;
        node.AsObject().Remove(nameof(MetadataMutationBatch.Ticket));
        foreach (var mutation in node[nameof(MetadataMutationBatch.Mutations)]!.AsArray())
        { mutation!.AsObject().Remove(nameof(MetadataMutation.PublishCacheEntry.Evidence)); }
        return SHA256.HashData(CanonicalBytes(node)).ToImmutableArray();
    }

    public static ImmutableArray<byte> Key(MetadataSelector value)
    {
        Validate(value);
        var key = new List<byte>(128);
        void Id(MetadataId id) => key.AddRange(id.Value.ToByteArray(bigEndian: true));
        void Text(string text)
        {
            foreach (var item in Encoding.UTF8.GetBytes(text))
            {
                key.Add(item);
                if (item == 0) { key.Add(255); }
            }
            key.Add(0);
            key.Add(0);
        }
        void Number(long number)
        {
            Span<byte> bytes = stackalloc byte[8];
            BinaryPrimitives.WriteInt64BigEndian(bytes, number);
            foreach (var item in bytes) { key.Add(item); }
        }
        switch (value)
        {
            case MetadataSelector.Registry registry:
                key.Add(1); Id(registry.Id); break;
            case MetadataSelector.Package package:
                key.Add(2); Id(package.Key.RegistryId); Text(package.Key.Ecosystem.Value); Text(package.Key.Name.Value); break;
            case MetadataSelector.Policy policy:
                key.Add(3); Id(policy.Id); break;
            case MetadataSelector.CacheEntry entry:
                key.Add(4); Id(entry.Identity.RegistryId); Text(entry.Identity.Ecosystem.Value);
                Text(entry.Identity.Target.Value); Text(entry.Identity.Method); Text(entry.Identity.AuthorizationPartition.Value); break;
            case MetadataSelector.Artifact artifact:
                key.Add(5); key.AddRange(Convert.FromHexString(artifact.Digest.Hex)); break;
            case MetadataSelector.Lease lease:
                key.Add(6); Text(lease.Resource.Value); break;
            case MetadataSelector.Aggregate aggregate:
                key.Add(7); Id(aggregate.Key.RegistryId); Text(aggregate.Key.AuthorizationPartition.Value);
                Number(aggregate.Key.Start.UnixMilliseconds); Number(aggregate.Key.End.UnixMilliseconds); break;
        }
        return key.ToImmutableArray();
    }

    public static MetadataSelector Target(MetadataMutation value) => value switch
    {
        MetadataMutation.PutRegistry put => put.Record.Selector,
        MetadataMutation.PutPackage put => put.Record.Selector,
        MetadataMutation.PutPolicy put => put.Record.Selector,
        MetadataMutation.DeleteRegistry delete => new MetadataSelector.Registry(delete.Id),
        MetadataMutation.DeletePackage delete => new MetadataSelector.Package(delete.Key),
        MetadataMutation.DeletePolicy delete => new MetadataSelector.Policy(delete.Id),
        MetadataMutation.PublishCacheEntry publish => publish.Record.Selector,
        MetadataMutation.DeleteCacheEntry delete => new MetadataSelector.CacheEntry(delete.Identity),
        MetadataMutation.AddAggregateContribution add => new MetadataSelector.Aggregate(add.Key),
        MetadataMutation.DeleteAggregate delete => new MetadataSelector.Aggregate(delete.Key),
        MetadataMutation.AcquireLease acquire => new MetadataSelector.Lease(acquire.Resource),
        MetadataMutation.RenewLease renew => new MetadataSelector.Lease(renew.Resource),
        MetadataMutation.ReleaseLease release => new MetadataSelector.Lease(release.Resource),
        MetadataMutation.ConfirmUnreferenced confirm => new MetadataSelector.Artifact(confirm.Digest),
        _ => throw new ArgumentException("Invalid metadata mutation.")
    };

    public static void Validate(MetadataSelector value)
    {
        switch (value)
        {
            case MetadataSelector.Registry { Id: not null }:
            case MetadataSelector.Policy { Id: not null }:
            case MetadataSelector.Artifact { Digest: not null }:
            case MetadataSelector.Lease { Resource: not null }: break;
            case MetadataSelector.Package package: ValidatePackageKey(package.Key); break;
            case MetadataSelector.CacheEntry { Identity: not null }: break;
            case MetadataSelector.Aggregate aggregate: ValidateAggregateKey(aggregate.Key); break;
            default: throw new ArgumentException("Invalid metadata selector.");
        }
    }

    public static void Validate(MetadataRecord value)
    {
        ArgumentNullException.ThrowIfNull(value);
        ArgumentNullException.ThrowIfNull(value.Revision);
        Validate(value.Selector);
        switch (value)
        {
            case MetadataRegistry registry:
                MetadataValidation.Require(registry.Ecosystem is not null && registry.Upstream is not null
                    && registry.PolicyId is not null && registry.Secret is not null && registry.Label is not null);
                break;
            case MetadataPackage package:
                ArgumentNullException.ThrowIfNull(package.Label); break;
            case MetadataPolicy policy:
                ValidateScope(policy.Scope);
                MetadataValidation.Require(policy.MetadataTtlMilliseconds is >= 0 and <= 31536000000
                    && policy.RetentionMilliseconds is >= 0 and <= 31536000000
                    && policy.StaleIfErrorMilliseconds is >= 0 and <= 31536000000
                    && policy.MaximumArtifactBytes >= 0);
                break;
            case MetadataCacheEntry entry:
                ValidatePackageKey(entry.Package);
                MetadataValidation.Require(entry.Status is >= 200 and <= 299 && entry.Headers is not null
                    && entry.Digest is not null && entry.Length >= 0 && entry.Created is not null
                    && entry.Validated is not null && entry.FreshUntil is not null
                    && entry.Created.UnixMilliseconds <= entry.Validated.UnixMilliseconds
                    && entry.Validated.UnixMilliseconds <= entry.FreshUntil.UnixMilliseconds
                    && entry.Package.RegistryId == entry.Identity.RegistryId
                    && entry.Package.Ecosystem == entry.Identity.Ecosystem);
                break;
            case MetadataArtifactState artifact:
                MetadataValidation.Require(artifact.Length >= 0 && artifact.LiveReferences >= 0); break;
            case MetadataWorkLease lease:
                MetadataValidation.Require(lease.Owner is not null && lease.Generation > 0
                    && lease.Acquired is not null && lease.Expires is not null
                    && lease.Acquired.UnixMilliseconds < lease.Expires.UnixMilliseconds);
                break;
            case MetadataAccessAggregate aggregate: Validate(aggregate.Counters); break;
            default: throw new ArgumentException("Invalid metadata record.");
        }
    }

    public static void Validate(MetadataAggregateDelta value)
    {
        ArgumentNullException.ThrowIfNull(value);
        MetadataValidation.Require(value.Hits >= 0 && value.Misses >= 0 && value.BytesServed >= 0
            && value.BytesFetched >= 0 && value.LatencyMilliseconds >= 0 && value.Samples >= 0);
    }

    public static void Validate(MetadataMutationBatch value)
    {
        ArgumentNullException.ThrowIfNull(value);
        ValidateTicket(value.Ticket);
        MetadataValidation.Collection(value.Mutations, 1, 64);
        ArgumentNullException.ThrowIfNull(value.LeaseGuard);
        var targets = new HashSet<string>(StringComparer.Ordinal);
        foreach (var mutation in value.Mutations)
        {
            var target = Target(mutation);
            MetadataValidation.Require(targets.Add(Convert.ToHexString(Key(target).AsSpan())));
            switch (mutation)
            {
                case MetadataMutation.PutRegistry put: Validate(put.Record); ValidateExpected(put.Expected); break;
                case MetadataMutation.PutPackage put: Validate(put.Record); ValidateExpected(put.Expected); break;
                case MetadataMutation.PutPolicy put: Validate(put.Record); ValidateExpected(put.Expected); break;
                case MetadataMutation.PublishCacheEntry publish:
                    Validate(publish.Record); ValidateExpected(publish.Expected);
                    ArgumentNullException.ThrowIfNull(publish.Evidence); break;
                case MetadataMutation.DeleteRegistry delete: ArgumentNullException.ThrowIfNull(delete.Revision); break;
                case MetadataMutation.DeletePackage delete: ArgumentNullException.ThrowIfNull(delete.Revision); break;
                case MetadataMutation.DeletePolicy delete: ArgumentNullException.ThrowIfNull(delete.Revision); break;
                case MetadataMutation.DeleteCacheEntry delete: ArgumentNullException.ThrowIfNull(delete.Revision); break;
                case MetadataMutation.DeleteAggregate delete: ArgumentNullException.ThrowIfNull(delete.Revision); break;
                case MetadataMutation.AddAggregateContribution add: Validate(add.Delta); break;
                case MetadataMutation.AcquireLease acquire:
                    MetadataValidation.Require(acquire.Owner is not null && acquire.TtlSeconds is >= 1 and <= 300); break;
                case MetadataMutation.RenewLease renew:
                    MetadataValidation.Require(renew.Owner is not null && renew.Revision is not null
                        && renew.Generation > 0 && renew.TtlSeconds is >= 1 and <= 300); break;
                case MetadataMutation.ReleaseLease release:
                    MetadataValidation.Require(release.Owner is not null && release.Revision is not null && release.Generation > 0); break;
                case MetadataMutation.ConfirmUnreferenced confirm: ArgumentNullException.ThrowIfNull(confirm.ReferenceRevision); break;
            }
            if (value.LeaseGuard is MetadataOption<MetadataLeaseGuard>.Some guard)
            {
                MetadataValidation.Require(guard.Value.Resource is not null && guard.Value.Owner is not null && guard.Value.Generation > 0
                    && target != new MetadataSelector.Lease(guard.Value.Resource));
            }
        }
    }

    public static void Validate(MetadataPageQuery value)
    {
        ArgumentNullException.ThrowIfNull(value);
        MetadataValidation.Require(value.PageSize is >= 1 and <= 100 && value.Continuation is not null);
        switch (value)
        {
            case MetadataPageQuery.Registries:
            case MetadataPageQuery.Artifacts: break;
            case MetadataPageQuery.Packages { RegistryId: not null }: break;
            case MetadataPageQuery.CacheEntries entries:
                MetadataValidation.Require(entries.RegistryId is not null && entries.AuthorizationPartition is not null && entries.Package is not null);
                if (entries.Package is MetadataOption<MetadataPackageKey>.Some package)
                {
                    ValidatePackageKey(package.Value);
                    MetadataValidation.Require(package.Value.RegistryId == entries.RegistryId);
                }
                break;
            case MetadataPageQuery.Policies policies: ValidateScope(policies.Scope); break;
            case MetadataPageQuery.Aggregates aggregate:
                ValidateAggregateKey(new(aggregate.RegistryId, aggregate.AuthorizationPartition, aggregate.Start, aggregate.End)); break;
            case MetadataPageQuery.Leases { ResourcePrefix: not null }: break;
            default: throw new ArgumentException("Invalid metadata page query.");
        }
    }

    public static void ValidateTicket(MetadataOperationTicket value)
    {
        ArgumentNullException.ThrowIfNull(value);
        MetadataValidation.Require(value.Epoch is not null && value.Id is not null && value.Issued is not null
            && value.Expires is not null && value.Expires.UnixMilliseconds - value.Issued.UnixMilliseconds == 86400000);
    }

    public static void Validate(MetadataSchemaRequest value)
    {
        ArgumentNullException.ThrowIfNull(value);
        if (value is not MetadataSchemaRequest.Upgrade upgrade) { return; }
        static void Version(string version) =>
            MetadataValidation.Require(version is { Length: >= 1 and <= 64 }
                && version.All(character => character is >= '!' and <= '~'));
        Version(upgrade.ExpectedCurrent);
        Version(upgrade.Target);
        ArgumentNullException.ThrowIfNull(upgrade.VerifiedRecoveryPoint);
        Version(upgrade.VerifiedRecoveryPoint.SchemaVersion);
    }

    private static void ValidateExpected(ExpectedRevision value) =>
        MetadataValidation.Require(value is ExpectedRevision.Absent or ExpectedRevision.Match { Revision: not null });

    private static void ValidatePackageKey(MetadataPackageKey value) =>
        MetadataValidation.Require(value is { RegistryId: not null, Ecosystem: not null, Name: not null });

    private static void ValidateAggregateKey(MetadataAggregateKey value) =>
        MetadataValidation.Require(value is { RegistryId: not null, AuthorizationPartition: not null, Start: not null, End: not null }
            && value.Start.UnixMilliseconds < value.End.UnixMilliseconds
            && value.End.UnixMilliseconds - value.Start.UnixMilliseconds <= 86400000);

    private static void ValidateScope(MetadataPolicyScope value) =>
        MetadataValidation.Require(value is MetadataPolicyScope.Global or MetadataPolicyScope.Registry { Id: not null });

    private static ImmutableArray<byte> EncodeValue<T>(T value)
    {
        var bytes = CanonicalBytes(JsonSerializer.SerializeToNode(value, Options)!);
        if (bytes.Length > MaximumBytes) { throw new ArgumentException("Metadata encoding exceeds one MiB."); }
        return bytes.ToImmutableArray();
    }

    private static byte[] CanonicalBytes(JsonNode node)
    {
        using var output = new MemoryStream();
        using (var writer = new Utf8JsonWriter(output)) { WriteCanonical(writer, node); }
        return output.ToArray();
    }

    private static void WriteCanonical(Utf8JsonWriter writer, JsonNode? node)
    {
        switch (node)
        {
            case JsonObject fields:
                writer.WriteStartObject();
                foreach (var field in fields.OrderBy(field => field.Key, StringComparer.Ordinal))
                {
                    writer.WritePropertyName(field.Key);
                    WriteCanonical(writer, field.Value);
                }
                writer.WriteEndObject(); break;
            case JsonArray items:
                writer.WriteStartArray();
                foreach (var item in items) { WriteCanonical(writer, item); }
                writer.WriteEndArray(); break;
            case null: writer.WriteNullValue(); break;
            default: node.WriteTo(writer); break;
        }
    }
}

internal sealed class MetadataGuidConverter : JsonConverter<Guid>
{
    public override Guid Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        var text = reader.GetString();
        if (text is null || text.Length != 32 || !Guid.TryParseExact(text, "N", out var value))
        { throw new JsonException("Invalid network-order metadata GUID."); }
        return value;
    }
    public override void Write(Utf8JsonWriter writer, Guid value, JsonSerializerOptions options) =>
        writer.WriteStringValue(Convert.ToHexStringLower(value.ToByteArray(bigEndian: true)));
}

internal sealed class MetadataOptionConverterFactory : JsonConverterFactory
{
    public override bool CanConvert(Type typeToConvert) =>
        typeToConvert.IsGenericType && typeToConvert.GetGenericTypeDefinition() == typeof(MetadataOption<>);

    public override JsonConverter CreateConverter(Type typeToConvert, JsonSerializerOptions options) =>
        (JsonConverter)Activator.CreateInstance(typeof(OptionConverter<>).MakeGenericType(typeToConvert.GetGenericArguments()), nonPublic: true)!;

    private sealed class OptionConverter<T> : JsonConverter<MetadataOption<T>> where T : notnull
    {
        public override MetadataOption<T> Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            using var document = JsonDocument.ParseValue(ref reader);
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty("kind", out var kind))
            { throw new JsonException("Invalid explicit metadata option."); }
            var fields = root.EnumerateObject().ToArray();
            return kind.GetString() switch
            {
                "none" when fields.Length == 1 => new MetadataOption<T>.None(),
                "some" when fields.Length == 2 && root.TryGetProperty("value", out var item) =>
                    new MetadataOption<T>.Some(item.Deserialize<T>(options) ?? throw new JsonException("Missing metadata option value.")),
                _ => throw new JsonException("Invalid explicit metadata option.")
            };
        }
        public override void Write(Utf8JsonWriter writer, MetadataOption<T> value, JsonSerializerOptions options)
        {
            writer.WriteStartObject();
            switch (value)
            {
                case MetadataOption<T>.None: writer.WriteString("kind", "none"); break;
                case MetadataOption<T>.Some some:
                    writer.WriteString("kind", "some");
                    writer.WritePropertyName("value");
                    JsonSerializer.Serialize(writer, some.Value, options);
                    break;
                default: throw new JsonException("Invalid explicit metadata option.");
            }
            writer.WriteEndObject();
        }
    }
}
