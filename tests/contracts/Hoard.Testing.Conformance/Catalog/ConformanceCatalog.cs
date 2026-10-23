using System.Collections.Immutable;
using System.Text.Json;
using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Testing.Conformance.Catalog;

public sealed record ConformanceExpectedCase(
    string ProfileId, string BindingId, string MatrixId, string CaseId,
    ImmutableArray<string> Witnesses, ImmutableArray<string> Controls, string? Exclusion);

public static class ConformanceCatalog
{
    public const string Revision = "f07-v1";
    private const int MaximumBytes = 16 * 1024 * 1024;
    private static readonly ImmutableArray<ConformanceExpectedCase> Cases = Load();
    public static ImmutableArray<ConformanceExpectedCase> Expand(string profile)
    {
        if (profile is not ("metadata" or "artifacts" or "composition" or "compatibility" or "harness"))
        { throw new ArgumentException("UnsupportedProfile"); }
        return [.. Cases.Where(entry => entry.ProfileId == profile)];
    }

    private static ImmutableArray<ConformanceExpectedCase> Load()
    {
        using var stream = typeof(ConformanceCatalog).Assembly.GetManifestResourceStream("Hoard.Conformance.Catalog")
            ?? throw new InvalidOperationException("EvidenceIncomplete");
        if (stream.Length > MaximumBytes) { throw new InvalidOperationException("OutputLimitExceeded"); }
        using var buffer = new MemoryStream();
        stream.CopyTo(buffer, 64 * 1024);
        return Parse(buffer.ToArray());
    }

    internal static ImmutableArray<ConformanceExpectedCase> Parse(ReadOnlyMemory<byte> data)
    {
        if (data.Length > MaximumBytes) { throw new InvalidOperationException("OutputLimitExceeded"); }
        JsonDocument document;
        try { document = JsonDocument.Parse(data); }
        catch (JsonException) { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
        using (document)
        {
            return ReadDocument(document.RootElement);
        }
    }

    private static ImmutableArray<ConformanceExpectedCase> ReadDocument(JsonElement root)
    {
        RequireFields(root, "schemaVersion", "catalogRevision", "entries");
        var schema = root.GetProperty("schemaVersion");
        if (schema.ValueKind != JsonValueKind.Number || !schema.TryGetInt32(out var revision) || revision != 1
            || ReadText(root.GetProperty("catalogRevision")) != Revision
            || root.GetProperty("entries").ValueKind != JsonValueKind.Array)
        { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
        if (root.GetProperty("entries").GetArrayLength() is 0 or > 50_000)
        { throw new InvalidOperationException("EvidenceIncomplete"); }
        var entries = ImmutableArray.CreateBuilder<ConformanceExpectedCase>();
        var keys = new HashSet<(string, string, string, string)>();
        var counts = new Dictionary<string, int>(StringComparer.Ordinal)
        { ["metadata"] = 0, ["artifacts"] = 0, ["composition"] = 0, ["compatibility"] = 0, ["harness"] = 0 };
        foreach (var entry in root.GetProperty("entries").EnumerateArray())
        {
            RequireFields(entry, "profileId", "bindingId", "matrixId", "caseId", "witnesses", "controls", "exclusion");
            var profile = ReadId(entry, "profileId");
            if (!counts.TryGetValue(profile, out var count))
            { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
            if (count >= 10_000) { throw new InvalidOperationException("EvidenceIncomplete"); }
            counts[profile] = count + 1;
            var binding = ReadId(entry, "bindingId");
            var matrix = ReadId(entry, "matrixId");
            var caseId = ReadId(entry, "caseId");
            if (!keys.Add((profile, binding, matrix, caseId))) { throw new InvalidOperationException("EvidenceIncomplete"); }
            var witnesses = ReadNames(entry, "witnesses");
            var controls = ReadNames(entry, "controls");
            var excluded = entry.GetProperty("exclusion");
            var exclusion = excluded.ValueKind == JsonValueKind.Null ? null : ReadText(excluded);
            if ((witnesses.Length + controls.Length == 0 && exclusion is null)
                || witnesses.Length + controls.Length > 128
                || exclusion is not (null or "non-durable fixture" or "simulation: no durable restart"))
            { throw new InvalidOperationException("EvidenceIncomplete"); }
            entries.Add(new(profile, binding, matrix, caseId, witnesses, controls, exclusion));
        }
        if (counts.Values.Any(count => count == 0))
        { throw new InvalidOperationException("EvidenceIncomplete"); }
        return entries.ToImmutable();
    }

    private static void RequireFields(JsonElement value, params string[] fields)
    {
        if (value.ValueKind != JsonValueKind.Object)
        { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
        var properties = value.EnumerateObject().Take(fields.Length + 1).ToArray();
        if (properties.Length != fields.Length
            || fields.Any(field => properties.Count(property => property.NameEquals(field)) != 1))
        { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
    }

    private static string ReadText(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.String)
        { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
        try { return value.GetString() ?? throw new InvalidOperationException("EvidenceSchemaInvalid"); }
        catch (InvalidOperationException) { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
    }

    private static string ReadId(JsonElement entry, string field)
    {
        try { return ConformanceBindingDeclaration.Id(ReadText(entry.GetProperty(field))); }
        catch (ArgumentException) { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
    }

    private static ImmutableArray<string> ReadNames(JsonElement entry, string field)
    {
        var array = entry.GetProperty(field);
        if (array.ValueKind != JsonValueKind.Array || array.GetArrayLength() > 128)
        { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
        var names = array.EnumerateArray().Select(ReadText).ToImmutableArray();
        if (names.Length > 128 || names.Any(name => name.Length is 0 or > 1024
                || name.Any(character => character is < ' ' or > '~'))
            || names.Distinct(StringComparer.Ordinal).Count() != names.Length)
        { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
        return names;
    }
}
