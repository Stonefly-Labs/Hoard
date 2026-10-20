using System.Security.Cryptography;
using System.Text.Json;
using Xunit;

namespace Hoard.Tests;

internal static class FoundationEvidence
{
    public static JsonElement Load()
    {
        var path = Environment.GetEnvironmentVariable("HOARD_FOUNDATION_EVIDENCE");
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
        {
            throw new InvalidOperationException(
                "Missing foundation build evidence. Run bash scripts/validate-foundation.sh; a solution build alone is insufficient.");
        }
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        return document.RootElement.Clone();
    }

    public static void AssertLocalPackageProvenance(string assetsPath)
    {
        var feed = Load().GetProperty("localFeed").GetString()!;
        using var document = JsonDocument.Parse(File.ReadAllText(assetsPath));
        var assets = document.RootElement;
        var cache = assets.GetProperty("packageFolders").EnumerateObject().Single().Name;
        var packages = assets.GetProperty("libraries").EnumerateObject().Where(l =>
            l.Value.GetProperty("type").GetString() == "package" && l.Name.StartsWith("Hoard.", StringComparison.Ordinal)).ToArray();
        Assert.NotEmpty(packages);
        foreach (var package in packages)
        {
            var directory = Path.Combine(cache, package.Value.GetProperty("path").GetString()!);
            using var metadata = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, ".nupkg.metadata")));
            Assert.Equal(Path.GetFullPath(feed), Path.GetFullPath(metadata.RootElement.GetProperty("source").GetString()!));
            var parts = package.Name.Split('/');
            var filename = $"{parts[0]}.{parts[1]}.nupkg";
            var expected = SHA512.HashData(File.ReadAllBytes(Path.Combine(feed, filename)));
            var actual = SHA512.HashData(File.ReadAllBytes(Path.Combine(directory, filename.ToLowerInvariant())));
            Assert.Equal(expected, actual);
        }
    }
}
