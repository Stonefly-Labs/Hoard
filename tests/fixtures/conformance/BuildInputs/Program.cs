using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
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
            Require(args.Length == 4 && args[0] is "content-hashes" or "pdb-documents", "EvidenceSchemaInvalid");
            var root = Path.GetFullPath(args[1]);
            Require(Path.IsPathFullyQualified(args[1]) && root == args[1], "OwnershipInvalid");
            var requestPath = OwnedPath(root, args[2]);
            var requestBytes = Read(requestPath, MaxManifestBytes);
            Require(HashPattern().IsMatch(args[3]) && Hash(requestBytes) == args[3], "InputChanged");
            using var request = JsonDocument.Parse(requestBytes, new JsonDocumentOptions { MaxDepth = 16 });
            if (args[0] == "pdb-documents")
            {
                var count = CaptureDocuments(root, request.RootElement, requestPath, args[3]);
                Console.WriteLine(JsonSerializer.Serialize(new { @event = "control", code = "None", value = count }));
                return 0;
            }

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

    private static int CaptureDocuments(string root, JsonElement request, string requestPath, string requestHash)
    {
        Keys(request, "schemaVersion", "qualification", "sourcePath", "generatedPath",
            "outputRoot", "project", "assembly", "pdb", "outputPath");
        Require(request.GetProperty("schemaVersion").GetInt32() == 1
            && request.GetProperty("qualification").ValueKind == JsonValueKind.False, "EvidenceSchemaInvalid");
        var source = OwnedPath(root, Text(request, "sourcePath"));
        var generated = OwnedPath(root, Text(request, "generatedPath"));
        Require(Directory.Exists(source) && Directory.Exists(generated) && source != generated
            && !source.StartsWith(generated + Path.DirectorySeparatorChar, StringComparison.Ordinal)
            && !generated.StartsWith(source + Path.DirectorySeparatorChar, StringComparison.Ordinal), "OwnershipInvalid");
        var project = Text(request, "project");
        Require(project.EndsWith(".csproj", StringComparison.Ordinal)
            && File.Exists(OwnedPath(source, project)), "OwnershipInvalid");
        var outputRoot = OwnedPath(root, Text(request, "outputRoot"));
        var outputPath = OwnedPath(root, Text(request, "outputPath"));
        Require(!File.Exists(outputPath) && !Directory.Exists(outputPath), "OwnershipInvalid");
        var assembly = request.GetProperty("assembly");
        var pdb = request.GetProperty("pdb");
        Keys(assembly, "path", "sha256");
        Keys(pdb, "path", "sha256");
        var assemblyName = Text(assembly, "path");
        var pdbName = Text(pdb, "path");
        var assemblyPath = OwnedPath(outputRoot, assemblyName);
        var pdbPath = OwnedPath(outputRoot, pdbName);
        Require(assemblyName.EndsWith(".dll", StringComparison.Ordinal)
            && pdbName == Path.ChangeExtension(assemblyName, ".pdb"), "EvidenceSchemaInvalid");
        var imageBytes = Read(assemblyPath, MaxPackageBytes);
        var pdbBytes = Read(pdbPath, MaxPackageBytes);
        Require(HashPattern().IsMatch(Text(assembly, "sha256")) && HashPattern().IsMatch(Text(pdb, "sha256")),
            "EvidenceSchemaInvalid");
        Require(Hash(imageBytes) == Text(assembly, "sha256") && Hash(pdbBytes) == Text(pdb, "sha256"), "InputChanged");
        using var imageStream = new MemoryStream(imageBytes, writable: false);
        using var image = new PEReader(imageStream);
        using var pdbStream = new MemoryStream(pdbBytes, writable: false);
        using var provider = MetadataReaderProvider.FromPortablePdbStream(pdbStream);
        var reader = provider.GetMetadataReader();
        var header = reader.DebugMetadataHeader;
        Require(header is not null, "ProofMismatch");
        var id = new BlobContentId(header!.Id);
        var entries = image.ReadDebugDirectory();
        var codeViews = entries.Where(entry => entry.Type == DebugDirectoryEntryType.CodeView).ToArray();
        var checksums = entries.Where(entry => entry.Type == DebugDirectoryEntryType.PdbChecksum).ToArray();
        Require(codeViews.Length == 1 && checksums.Length == 1, "ProofMismatch");
        var codeView = image.ReadCodeViewDebugDirectoryData(codeViews[0]);
        var checksum = image.ReadPdbChecksumDebugDirectoryData(checksums[0]);
        Require(codeViews[0].MinorVersion == 0x504d && codeView.Guid == id.Guid
            && codeViews[0].Stamp == id.Stamp && codeView.Age == 1, "ProofMismatch");
        var offset = header.IdStartOffset;
        Require(offset >= 0 && offset <= pdbBytes.Length - 20, "ProofMismatch");
        using var checksumHash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        checksumHash.AppendData(pdbBytes.AsSpan(0, offset));
        checksumHash.AppendData(new byte[20]);
        checksumHash.AppendData(pdbBytes.AsSpan(offset + 20));
        Require(checksum.AlgorithmName == "SHA256"
            && checksum.Checksum.AsSpan().SequenceEqual(checksumHash.GetHashAndReset()), "ProofMismatch");
        var documents = new SortedDictionary<string, string>(StringComparer.Ordinal);
        long total = imageBytes.Length + pdbBytes.Length;
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        foreach (var handle in reader.Documents)
        {
            cancellation.Token.ThrowIfCancellationRequested();
            var document = reader.GetDocument(handle);
            var name = reader.GetString(document.Name);
            Require(Path.IsPathFullyQualified(name), "OwnershipInvalid");
            var path = Path.GetFullPath(name);
            var owner = path.StartsWith(source + Path.DirectorySeparatorChar, StringComparison.Ordinal) ? source
                : path.StartsWith(generated + Path.DirectorySeparatorChar, StringComparison.Ordinal) ? generated : null;
            Require(owner is not null, "OwnershipInvalid");
            var relative = path[(owner!.Length + 1)..].Replace(Path.DirectorySeparatorChar, '/');
            var identity = (owner == source ? "source/" : "generated/") + relative;
            var hash = reader.GetBlobBytes(document.Hash);
            Require(reader.GetGuid(document.HashAlgorithm) == new Guid("8829d00f-11b8-4213-878b-770e8597ac16")
                && hash.Length == 32 && documents.Count < 4096
                && documents.TryAdd(identity, Convert.ToHexStringLower(hash)), "ProofMismatch");
            var bytes = Read(OwnedPath(owner, relative), (int)Math.Min(MaxPackageBytes, MaxArchiveBytes - total));
            total += bytes.Length;
            Require(Hash(bytes) == documents[identity], "InputChanged");
        }

        Require(documents.Count > 0, "EvidenceIncomplete");
        var receipt = JsonSerializer.SerializeToUtf8Bytes(new
        {
            schemaVersion = 1,
            qualification = false,
            project,
            assembly = new { path = assemblyName, sha256 = Hash(imageBytes) },
            pdb = new { path = pdbName, sha256 = Hash(pdbBytes) },
            documents
        });
        Require(receipt.Length <= MaxManifestBytes, "OutputLimitExceeded");
        Require(Hash(Read(requestPath, MaxManifestBytes)) == requestHash
            && Hash(Read(assemblyPath, MaxPackageBytes)) == Hash(imageBytes)
            && Hash(Read(pdbPath, MaxPackageBytes)) == Hash(pdbBytes), "InputChanged");
        using var output = new FileStream(outputPath, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        output.Write(receipt);
        return documents.Count;
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
