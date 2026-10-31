using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Memory;

public static class MemoryPayloadDamage
{
    public static MemoryOperationTestImage Operation(
        MemoryOperationTestImage original, string shape, MetadataOperationTicket foreign, string canary)
    {
        if (shape == "fractional-state") { return original with { State = 1.5 }; }
        var payload = Object(original.Receipt ?? throw new ArgumentException("BindingInvalid"));
        var damaged = original;
        switch (shape)
        {
            case "null-target": payload["Revisions"]![0]!["Target"] = null; break;
            case "null-revision": payload["Revisions"]![0]!["Revision"] = null; break;
            case "missing-revisions":
                if (!payload.Remove("Revisions")) { throw new ArgumentException("BindingInvalid"); }
                break;
            case "oversized-revisions":
                payload["Revisions"] = new JsonArray(Enumerable.Range(0, 65)
                    .Select(_ => payload["Revisions"]![0]!.DeepClone()).ToArray());
                break;
            case "mismatched-ticket": payload["Ticket"] = JsonSerializer.SerializeToNode(foreign); break;
            case "short-fingerprint": damaged = damaged with { Fingerprint = new string('a', 62) }; break;
            case "missing-fingerprint": damaged = damaged with { Fingerprint = null }; break;
            case "invalid-fingerprint": damaged = damaged with { Fingerprint = new string('z', 64) }; break;
            case "reserved-receipt": damaged = damaged with { State = 0 }; break;
            case "abandoned-receipt": damaged = damaged with { State = 2 }; break;
            case "malformed" or "oversized-payload" or "missing-receipt": break;
            default: throw new ArgumentException("BindingInvalid");
        }
        return damaged with
        {
            Receipt = shape switch
            {
                "malformed" => "{" + canary,
                "oversized-payload" => new string(' ', MetadataEncoding.MaximumBytes) + original.Receipt,
                "missing-receipt" => null,
                _ => payload.ToJsonString()
            }
        };
    }

    public static string Record(string original, string shape, string canary)
    {
        var record = Object(original);
        switch (shape)
        {
            case "null-label": record["Label"] = null; break;
            case "oversized-label": record["Label"]!["Value"] = new string('x', 513) + canary; break;
            case "null-revision": record["Revision"] = null; break;
            case "wrong-key": record["Id"] = JsonSerializer.SerializeToNode(new MetadataId(Guid.NewGuid())); break;
            case "cache-auth": record["Identity"]!["AuthorizationPartition"] = null; break;
            case "aggregate-auth": record["Key"]!["AuthorizationPartition"] = null; break;
            case "aggregate-start": record["Key"]!["Start"] = null; break;
            case "aggregate-end": record["Key"]!["End"] = null; break;
            case "lease-resource": record["Resource"] = null; break;
            case "malformed": break;
            default: throw new ArgumentException("BindingInvalid");
        }
        return shape == "malformed" ? "{" + canary : record.ToJsonString();
    }

    public static MetadataContinuation Continuation(MetadataContinuation original, string field, string shape)
    {
        if (field is not ("Contract" or "Epoch" or "Query" or "Size" or "After"))
        { throw new ArgumentException("BindingInvalid"); }
        var cursor = Object(Convert.FromBase64String(original.Value));
        if (!cursor.ContainsKey(field)) { throw new ArgumentException("BindingInvalid"); }
        if (shape == "omitted") { cursor.Remove(field); }
        else
        {
            cursor[field] = shape switch
            {
                "null" => null,
                "wrong-type" => JsonValue.Create(42),
                "empty" => JsonValue.Create(""),
                "odd-hex" => JsonValue.Create("000"),
                "invalid-hex" => JsonValue.Create("zz"),
                _ => throw new ArgumentException("BindingInvalid")
            };
        }
        return new(Convert.ToBase64String(JsonSerializer.SerializeToUtf8Bytes(cursor)));
    }

    private static JsonObject Object(string value) =>
        JsonNode.Parse(value) as JsonObject ?? throw new ArgumentException("BindingInvalid");
    private static JsonObject Object(byte[] value) =>
        JsonNode.Parse(value) as JsonObject ?? throw new ArgumentException("BindingInvalid");
}
