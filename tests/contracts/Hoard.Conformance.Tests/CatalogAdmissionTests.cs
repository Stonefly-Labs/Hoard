using System.Text;
using System.Text.Json.Nodes;
using Hoard.Testing.Conformance.Catalog;

namespace Hoard.Conformance.Tests;

public sealed class CatalogAdmissionTests
{
    [Theory]
    [InlineData("unknown-profile")]
    [InlineData("duplicate-field")]
    [InlineData("unknown-field")]
    [InlineData("missing-field")]
    [InlineData("non-string-witness")]
    [InlineData("malformed-unicode")]
    [InlineData("malformed-key")]
    public void Malformed_catalog_entries_fail_with_closed_diagnostics(string defect)
    {
        var root = Document();
        Assert.NotEmpty(ConformanceCatalog.Parse(Encoding.UTF8.GetBytes(root.ToJsonString())));
        var entry = root["entries"]![0]!;
        switch (defect)
        {
            case "unknown-profile": entry["profileId"] = "service"; break;
            case "unknown-field": entry["extra"] = "untrusted"; break;
            case "missing-field": entry.AsObject().Remove("matrixId"); break;
            case "non-string-witness": entry["witnesses"] = new JsonArray(1); break;
        }
        var data = root.ToJsonString();
        if (defect == "duplicate-field")
        {
            data = data.Replace("\"matrixId\":\"none\"", "\"profileId\":\"harness\"", StringComparison.Ordinal);
        }
        if (defect == "malformed-unicode")
        {
            data = data.Replace("\"control\"", "\"\\ud800\"", StringComparison.Ordinal);
        }
        if (defect == "malformed-key")
        {
            data = data.Replace("\"matrixId\"", "\"\\ud800\"", StringComparison.Ordinal);
        }
        var failure = Assert.Throws<InvalidOperationException>(() => ConformanceCatalog.Parse(Encoding.UTF8.GetBytes(data)));
        Assert.Equal("EvidenceSchemaInvalid", failure.Message);
    }

    [Fact]
    public void Oversized_catalogs_and_witness_collections_reject_without_partial_results()
    {
        var root = Document();
        root["entries"]![0]!["witnesses"] = new JsonArray(
            Enumerable.Range(0, 129).Select(index => JsonValue.Create("Tests.Check" + index)).ToArray());
        Assert.Throws<InvalidOperationException>(() => ConformanceCatalog.Parse(Encoding.UTF8.GetBytes(root.ToJsonString())));
        var oversized = Enumerable.Repeat((byte)' ', 16 * 1024 * 1024 + 1).ToArray();
        Encoding.UTF8.GetBytes(Document().ToJsonString()).CopyTo(oversized, 0);
        Assert.Throws<InvalidOperationException>(() => ConformanceCatalog.Parse(oversized));
    }

    [Fact]
    public void Missing_profiles_and_duplicate_keys_cannot_return_a_shortened_catalog()
    {
        var root = Document();
        root["entries"]!.AsArray().RemoveAt(0);
        Assert.Throws<InvalidOperationException>(() => ConformanceCatalog.Parse(Encoding.UTF8.GetBytes(root.ToJsonString())));
        root = Document();
        root["entries"]!.AsArray().Add(root["entries"]![0]!.DeepClone());
        Assert.Throws<InvalidOperationException>(() => ConformanceCatalog.Parse(Encoding.UTF8.GetBytes(root.ToJsonString())));
    }

    [Fact]
    public void Per_profile_result_overflow_rejects_even_when_other_profiles_are_complete()
    {
        var root = Document();
        var entries = root["entries"]!.AsArray();
        for (var index = 0; index < 10_000; index++)
        {
            var entry = entries[4]!.DeepClone();
            entry["caseId"] = "Case-" + index;
            entries.Add(entry);
        }
        Assert.Throws<InvalidOperationException>(() => ConformanceCatalog.Parse(Encoding.UTF8.GetBytes(root.ToJsonString())));
    }

    private static JsonObject Document() => new()
    {
        ["schemaVersion"] = 1,
        ["catalogRevision"] = "f07-v1",
        ["entries"] = new JsonArray(
            new[] { "metadata", "artifacts", "composition", "compatibility", "harness" }.Select(profile =>
                new JsonObject
                {
                    ["profileId"] = profile,
                    ["bindingId"] = "none",
                    ["matrixId"] = "none",
                    ["caseId"] = "QC-01",
                    ["witnesses"] = new JsonArray(),
                    ["controls"] = new JsonArray("control"),
                    ["exclusion"] = null,
                }).ToArray()),
    };
}
