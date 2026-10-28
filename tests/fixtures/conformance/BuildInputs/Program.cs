using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;
using NuGet.Packaging;

namespace Hoard.Fixtures.Conformance.BuildInputs;

internal static partial class Program
{
    private const int MaxManifestBytes = 2 * 1024 * 1024;
    private const int MaxPackageBytes = 64 * 1024 * 1024;
    private const int MaxArchiveBytes = 256 * 1024 * 1024;

    private static int Main(string[] args)
    {
        try
        {
            Require(args.Length == 4 && args[0] == "content-hashes", "EvidenceSchemaInvalid");
            var root = Path.GetFullPath(args[1]);
            Require(Path.IsPathFullyQualified(args[1]) && root == args[1], "OwnershipInvalid");
            var requestPath = OwnedPath(root, args[2]);
            var requestBytes = Read(requestPath, MaxManifestBytes);
            Require(HashPattern().IsMatch(args[3]) && Hash(requestBytes) == args[3], "InputChanged");
            using var request = JsonDocument.Parse(requestBytes, new JsonDocumentOptions { MaxDepth = 16 });
            Keys(request.RootElement, "schemaVersion", "qualification", "assets", "cachePath", "outputPath");
            Require(request.RootElement.GetProperty("schemaVersion").GetInt32() == 1
                && request.RootElement.GetProperty("qualification").ValueKind == JsonValueKind.False,
                "EvidenceSchemaInvalid");
            var assets = request.RootElement.GetProperty("assets");
            Keys(assets, "path", "sha256");
            var assetsPath = OwnedPath(root, Text(assets, "path"));
            var assetsHash = Text(assets, "sha256");
            Require(HashPattern().IsMatch(assetsHash), "EvidenceSchemaInvalid");
            var assetsBytes = Read(assetsPath, MaxManifestBytes);
            Require(Hash(assetsBytes) == assetsHash, "InputChanged");
            _ = OwnedPath(root, Text(request.RootElement, "cachePath"));
            var outputPath = OwnedPath(root, Text(request.RootElement, "outputPath"));
            Require(!File.Exists(outputPath) && !Directory.Exists(outputPath), "OwnershipInvalid");
            using var graph = JsonDocument.Parse(assetsBytes, new JsonDocumentOptions { MaxDepth = 32 });
            Require(graph.RootElement.GetProperty("version").GetInt32() == 3, "EvidenceSchemaInvalid");
            var libraries = graph.RootElement.GetProperty("libraries");
            Require(libraries.ValueKind == JsonValueKind.Object, "EvidenceSchemaInvalid");
            var rows = new List<object>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            long total = 0;
            using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            foreach (var library in libraries.EnumerateObject())
            {
                cancellation.Token.ThrowIfCancellationRequested();
                if (Text(library.Value, "type") != "package")
                {
                    Require(Text(library.Value, "type") == "project", "EvidenceSchemaInvalid");
                    continue;
                }

                var prefix = Text(library.Value, "path");
                var parts = prefix.Split('/');
                Require(rows.Count < 1024 && parts.Length == 2 && parts.All(part => PackagePartPattern().IsMatch(part))
                    && seen.Add(prefix), "EvidenceSchemaInvalid");
                var relative = $"{Text(request.RootElement, "cachePath")}/{prefix}/{parts[0]}.{parts[1]}.nupkg";
                var path = OwnedPath(root, relative);
                var raw = Read(path, (int)Math.Min(MaxPackageBytes, MaxArchiveBytes - total));
                total += raw.Length;
                Require(total <= MaxArchiveBytes, "OutputLimitExceeded");
                using var stream = new MemoryStream(raw, writable: false);
                using var reader = new PackageArchiveReader(stream);
                var identity = reader.GetIdentity();
                Require(identity.Id.Equals(parts[0], StringComparison.OrdinalIgnoreCase)
                    && identity.Version.ToNormalizedString().Equals(parts[1], StringComparison.OrdinalIgnoreCase),
                    "InputChanged");
                var content = Convert.FromBase64String(reader.GetContentHash(cancellation.Token));
                Require(content.Length == 64, "EvidenceSchemaInvalid");
                rows.Add(new
                {
                    cachePath = prefix,
                    archiveSha256 = Hash(raw),
                    contentSha512 = Convert.ToHexStringLower(content)
                });
            }

            var bytes = JsonSerializer.SerializeToUtf8Bytes(new { schemaVersion = 1, qualification = false, packages = rows });
            Require(bytes.Length <= MaxManifestBytes, "OutputLimitExceeded");
            Require(Hash(Read(requestPath, MaxManifestBytes)) == args[3]
                && Hash(Read(assetsPath, MaxManifestBytes)) == assetsHash, "InputChanged");
            using (var output = new FileStream(outputPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                output.Write(bytes);
            }

            Console.WriteLine(JsonSerializer.Serialize(new { @event = "control", code = "None", value = rows.Count }));
            return 0;
        }
        catch (InputException error)
        {
            Console.WriteLine(JsonSerializer.Serialize(new { @event = "control", code = error.Message, value = 0 }));
            return 2;
        }
        catch (Exception)
        {
            Console.WriteLine("{\"event\":\"control\",\"code\":\"UnknownDiagnostic\",\"value\":0}");
            return 2;
        }
    }

    private static byte[] Read(string path, int limit)
    {
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        Require(stream.Length is > 0 && stream.Length <= limit, "OutputLimitExceeded");
        var bytes = new byte[(int)stream.Length];
        stream.ReadExactly(bytes);
        Require(stream.ReadByte() == -1, "InputChanged");
        return bytes;
    }

    private static string OwnedPath(string root, string relative)
    {
        Require(relative is { Length: > 0 and <= 512 } && relative.All(c => c is >= ' ' and <= '~')
            && !relative.Contains('\\') && !relative.Contains(':') && !Path.IsPathRooted(relative)
            && relative.Split('/').All(part => part is not ("" or "." or "..")), "OwnershipInvalid");
        var path = Path.GetFullPath(Path.Combine(root, relative));
        for (var current = path; current is not null; current = Path.GetDirectoryName(current))
        {
            Require((!File.Exists(current) && !Directory.Exists(current))
                || (File.GetAttributes(current) & FileAttributes.ReparsePoint) == 0, "OwnershipInvalid");
            Require(new FileInfo(current).LinkTarget is null, "OwnershipInvalid");
        }

        return path;
    }

    private static string Text(JsonElement value, string name)
    {
        var result = value.GetProperty(name).GetString();
        Require(result is not null && result.Length <= 1024, "EvidenceSchemaInvalid");
        return result!;
    }

    private static void Keys(JsonElement value, params string[] expected)
    {
        Require(value.ValueKind == JsonValueKind.Object, "EvidenceSchemaInvalid");
        var keys = value.EnumerateObject().Select(property => property.Name).ToArray();
        Require(keys.Length == expected.Length && keys.ToHashSet(StringComparer.Ordinal).SetEquals(expected),
            "EvidenceSchemaInvalid");
    }

    private static string Hash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    private static void Require(bool condition, string code)
    {
        if (!condition)
        {
            throw new InputException(code);
        }
    }

    private sealed class InputException(string code) : Exception(code);

    [GeneratedRegex(@"\A[0-9a-f]{64}\z")]
    private static partial Regex HashPattern();

    [GeneratedRegex(@"\A[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}\z")]
    private static partial Regex PackagePartPattern();
}
