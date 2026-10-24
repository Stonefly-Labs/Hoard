using System.Collections.Immutable;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;
using System.Text.Json.Serialization;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Memory;

internal sealed class MemoryStoredRecords
{
    internal static readonly JsonSerializerOptions Json = new()
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        MaxDepth = 32
    };

    private readonly ImmutableDictionary<MetadataSelector, string> payloads;

    private MemoryStoredRecords(ImmutableDictionary<MetadataSelector, string> payloads) => this.payloads = payloads;

    public static MemoryStoredRecords Empty { get; } = new(ImmutableDictionary<MetadataSelector, string>.Empty);
    internal IEnumerable<KeyValuePair<MetadataSelector, string>> Encoded => payloads;
    public IEnumerable<MetadataRecord> Values => payloads.Select(pair => Decode(pair.Key, pair.Value));
    public MetadataRecord this[MetadataSelector selector] => Decode(selector, payloads[selector]);
    public bool ContainsKey(MetadataSelector selector) => payloads.ContainsKey(selector);
    public bool TryGetValue(MetadataSelector selector, [NotNullWhen(true)] out MetadataRecord? record)
    {
        if (payloads.TryGetValue(selector, out var payload))
        {
            record = Decode(selector, payload);
            return true;
        }
        record = null;
        return false;
    }

    public MemoryStoredRecords SetItem(MetadataSelector selector, MetadataRecord record)
    {
        _ = MetadataEncoding.Encode(record);
        return new(payloads.SetItem(selector, JsonSerializer.Serialize<MetadataRecord>(record, Json)));
    }

    public MemoryStoredRecords Remove(MetadataSelector selector) => new(payloads.Remove(selector));
    internal string Payload(MetadataSelector selector) => payloads[selector];
    internal MemoryStoredRecords WithPayload(MetadataSelector selector, string payload)
    {
        if (!payloads.ContainsKey(selector)) { throw new ArgumentException("Missing synthetic record."); }
        return new(payloads.SetItem(selector, payload));
    }

    private static MetadataRecord Decode(MetadataSelector selector, string payload)
    {
        try
        {
            if (payload.Length > MetadataEncoding.MaximumBytes) { throw new MemoryContractFailure(MetadataFailureCode.CorruptState); }
            var record = JsonSerializer.Deserialize<MetadataRecord>(payload, Json)
                ?? throw new MemoryContractFailure(MetadataFailureCode.CorruptState);
            _ = MetadataEncoding.Encode(record);
            if (record.Selector != selector) { throw new MemoryContractFailure(MetadataFailureCode.CorruptState); }
            return record;
        }
        catch (JsonException) { throw new MemoryContractFailure(MetadataFailureCode.CorruptState); }
        catch (ArgumentException) { throw new MemoryContractFailure(MetadataFailureCode.CorruptState); }
        catch (OverflowException) { throw new MemoryContractFailure(MetadataFailureCode.CorruptState); }
    }
}
