using System.Collections.Immutable;
using System.Text.Json;
using Hoard.Testing.Conformance.Catalog;

namespace Hoard.Conformance.Tests;

internal static class FrozenAgreement
{
    internal static ImmutableArray<ConformanceExpectedCase> Read(string profile)
    {
        using var stream = typeof(FrozenAgreement).Assembly.GetManifestResourceStream("Hoard.Conformance.FrozenInventory")
            ?? throw new InvalidOperationException("EvidenceIncomplete");
        using var document = JsonDocument.Parse(stream);
        return [.. document.RootElement.GetProperty("entries").EnumerateArray()
            .Where(entry => Text(entry, "profileId") == profile)
            .Select(entry => new ConformanceExpectedCase(
                Text(entry, "profileId"), Text(entry, "bindingId"), Text(entry, "matrixId"), Text(entry, "caseId"),
                Names(entry, "runtimeTests"), Names(entry, "orchestratorControls"),
                entry.GetProperty("exclusion").GetString()))];
    }

    internal static void AssertUnchanged(string profile, string binding)
    {
        var frozen = Read(profile).Where(entry => entry.BindingId == binding).OrderBy(entry => entry.CaseId).ToArray();
        var actual = ConformanceCatalog.Expand(profile).Where(entry => entry.BindingId == binding)
            .OrderBy(entry => entry.CaseId).ToArray();
        Assert.NotEmpty(frozen);
        Assert.Equal(frozen.Length, actual.Length);
        for (var index = 0; index < frozen.Length; index++)
        {
            Assert.Equal(frozen[index].ProfileId, actual[index].ProfileId);
            Assert.Equal(frozen[index].CaseId, actual[index].CaseId);
            Assert.Equal(frozen[index].MatrixId, actual[index].MatrixId);
            Assert.Equal(frozen[index].Exclusion, actual[index].Exclusion);
            Assert.Equal<string>(frozen[index].Witnesses, actual[index].Witnesses);
            Assert.Equal<string>(frozen[index].Controls, actual[index].Controls);
        }
    }

    internal static IEnumerable<(ConformanceExpectedCase Entry, string[] Witnesses)> ParameterizedGroups(
        string profile, string binding) =>
        Read(profile).Where(entry => entry.BindingId == binding && entry.Exclusion is null)
            .SelectMany(entry => entry.Witnesses.GroupBy(witness => witness.Split('(')[0], StringComparer.Ordinal)
                .Where(group => group.Any(witness => witness.Contains('(')))
                .Select(group => (entry, group.ToArray())));

    internal static void Select(RuntimeLoggerTests.OwnedInput owned, ConformanceExpectedCase entry,
        IReadOnlyList<string> witnesses)
    {
        Assert.Equal(owned.Input.Expected.Length, witnesses.Count);
        for (var index = 0; index < witnesses.Count; index++)
        {
            owned.Input.Expected[index] = owned.Input.Expected[index] with
            {
                TestIdentity = witnesses[index],
                FullyQualifiedName = witnesses[index].Split('(')[0],
                BindingId = entry.BindingId,
                MatrixId = entry.MatrixId,
                CaseId = entry.CaseId
            };
        }
        owned.RewriteManifest(JsonSerializer.Serialize(owned.Input, RuntimeLoggerTests.Json));
    }

    private static string Text(JsonElement entry, string property) =>
        entry.GetProperty(property).GetString() ?? throw new InvalidOperationException("EvidenceIncomplete");

    private static ImmutableArray<string> Names(JsonElement entry, string property) =>
        [.. entry.GetProperty(property).EnumerateArray().Select(value =>
            value.GetString() ?? throw new InvalidOperationException("EvidenceIncomplete"))];
}
