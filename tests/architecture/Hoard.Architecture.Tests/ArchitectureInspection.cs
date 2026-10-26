using System.Text.Json;

namespace Hoard.Architecture.Tests;

internal static class ArchitectureInspection
{
    internal static List<ArchitectureViolation> InspectRealGraphs(JsonElement graphs)
    {
        if (graphs.ValueKind != JsonValueKind.Array)
        {
            throw new InspectionException("Missing real scan collection.");
        }
        string[] required =
        [
            "platform", "provider:Hoard.Fixtures.Protocol", "provider:Hoard.Fixtures.Metadata",
            "provider:Hoard.Fixtures.Artifact.One", "provider:Hoard.Fixtures.Artifact.Two",
            "provider:Hoard.Fixtures.Identity", "host:One", "host:Two"
        ];
        var entries = graphs.EnumerateArray().ToArray();
        if (entries.Any(entry => entry.ValueKind != JsonValueKind.Object || !entry.TryGetProperty("scanId", out var id)
            || id.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(id.GetString())))
        {
            throw new InspectionException("Missing real scan identity.");
        }
        var actual = entries.Select(g => g.GetProperty("scanId").GetString()!).ToArray();
        var missing = required.Except(actual).ToArray();
        if (missing.Length != 0 || !required.Order().SequenceEqual(actual.Order()))
        {
            throw new InspectionException($"Incomplete/duplicate real scan coverage; missing: {string.Join(", ", missing)}.");
        }
        return entries.SelectMany(Inspect).ToList();
    }

    internal static List<ArchitectureViolation> Inspect(JsonElement input)
    {
        try
        {
            using var evidence = InspectionEvidence.Load(input);
            DependencyGraphInspector.Read(evidence);
            return DependencyGraphInspector.Inspect(evidence)
                .Concat(PublicSurfaceInspector.Inspect(evidence))
                .Concat(SliceUsageInspector.Inspect(evidence)).ToList();
        }
        catch (Exception error) when (error is IOException or JsonException or KeyNotFoundException
            or InvalidOperationException or ArgumentException or BadImageFormatException)
        {
            throw new InspectionException($"Incomplete or invalid build inputs ({error.GetType().Name}); regenerate the foundation evidence.");
        }
    }
}
