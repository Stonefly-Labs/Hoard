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
        using var document = JsonDocument.Parse(stream);
        var root = document.RootElement;
        if (root.EnumerateObject().Count() != 3 || root.GetProperty("schemaVersion").GetInt32() != 1
            || root.GetProperty("catalogRevision").GetString() != Revision)
        { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
        var entries = ImmutableArray.CreateBuilder<ConformanceExpectedCase>();
        var keys = new HashSet<(string, string, string, string)>();
        foreach (var entry in root.GetProperty("entries").EnumerateArray())
        {
            if (entry.EnumerateObject().Count() != 7) { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
            var profile = ReadId(entry, "profileId");
            var binding = ReadId(entry, "bindingId");
            var matrix = ReadId(entry, "matrixId");
            var caseId = ReadId(entry, "caseId");
            if (!keys.Add((profile, binding, matrix, caseId))) { throw new InvalidOperationException("EvidenceIncomplete"); }
            var witnesses = ReadNames(entry, "witnesses");
            var controls = ReadNames(entry, "controls");
            var exclusion = entry.GetProperty("exclusion").GetString();
            if ((witnesses.Length + controls.Length == 0 && exclusion is null)
                || witnesses.Length + controls.Length > 128
                || exclusion is not (null or "non-durable fixture" or "simulation: no durable restart"))
            { throw new InvalidOperationException("EvidenceIncomplete"); }
            entries.Add(new(profile, binding, matrix, caseId, witnesses, controls, exclusion));
        }
        if (entries.GroupBy(entry => entry.ProfileId).Any(group => group.Count() > 10_000))
        { throw new InvalidOperationException("EvidenceIncomplete"); }
        return entries.ToImmutable();
    }

    private static string ReadId(JsonElement entry, string field)
        => ConformanceBindingDeclaration.Id(entry.GetProperty(field).GetString()
            ?? throw new InvalidOperationException("EvidenceSchemaInvalid"));

    private static ImmutableArray<string> ReadNames(JsonElement entry, string field)
    {
        var names = entry.GetProperty(field).EnumerateArray()
            .Select(value => value.GetString() ?? throw new InvalidOperationException("EvidenceSchemaInvalid"))
            .ToImmutableArray();
        if (names.Length > 128 || names.Any(name => name.Length is 0 or > 1024
                || name.Any(character => character is < ' ' or > '~'))
            || names.Distinct(StringComparer.Ordinal).Count() != names.Length)
        { throw new InvalidOperationException("EvidenceSchemaInvalid"); }
        return names;
    }
}
