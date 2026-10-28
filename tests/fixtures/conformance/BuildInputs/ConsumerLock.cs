using System.IO.Compression;
using System.Text.Json;
using System.Text.Json.Nodes;
using NuGet.Frameworks;
using NuGet.Packaging;
using NuGet.Versioning;

namespace Hoard.Fixtures.Conformance.BuildInputs;

internal static partial class Program
{
    private sealed record ConsumerArchive(string Id, NuGetVersion Version, string Path, string ArchiveHash,
        string ContentHash, IReadOnlyDictionary<string, VersionRange> Dependencies);

    private static int ComposeConsumerLock(string root, JsonElement request, string requestPath, string requestHash)
    {
        Keys(request, "schemaVersion", "qualification", "sourceLock", "adapter", "archives", "outputPath");
        Require(request.GetProperty("schemaVersion").GetInt32() == 1
            && request.GetProperty("qualification").ValueKind == JsonValueKind.False, "EvidenceSchemaInvalid");
        var source = request.GetProperty("sourceLock");
        var adapter = request.GetProperty("adapter");
        Keys(source, "path", "sha256");
        Keys(adapter, "packageId", "version");
        var sourcePath = OwnedPath(root, Text(source, "path"));
        var sourceHash = Text(source, "sha256");
        Require(HashPattern().IsMatch(sourceHash), "EvidenceSchemaInvalid");
        var sourceBytes = Read(sourcePath, MaxManifestBytes);
        Require(Hash(sourceBytes) == sourceHash, "InputChanged");
        var outputPath = OwnedPath(root, Text(request, "outputPath"));
        Require(!File.Exists(outputPath) && !Directory.Exists(outputPath), "OwnershipInvalid");
        using var sourceDocument = JsonDocument.Parse(sourceBytes, new JsonDocumentOptions { MaxDepth = 16 });
        Keys(sourceDocument.RootElement, "version", "dependencies");
        Require(sourceDocument.RootElement.GetProperty("version").GetInt32() is 1 or 2, "EvidenceSchemaInvalid");
        Keys(sourceDocument.RootElement.GetProperty("dependencies"), "net10.0");
        var original = sourceDocument.RootElement.GetProperty("dependencies").GetProperty("net10.0");
        Require(original.ValueKind == JsonValueKind.Object, "EvidenceSchemaInvalid");
        var lockDocument = JsonNode.Parse(sourceBytes)!.AsObject();
        var locked = lockDocument["dependencies"]!["net10.0"]!.AsObject();
        var candidates = request.GetProperty("archives");
        Require(candidates.ValueKind == JsonValueKind.Array && candidates.GetArrayLength() is > 0 and <= 1024,
            "EvidenceSchemaInvalid");
        var archives = new Dictionary<string, ConsumerArchive>(StringComparer.OrdinalIgnoreCase);
        var framework = NuGetFramework.ParseFolder("net10.0");
        var reducer = new FrameworkReducer();
        long total = 0;
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        foreach (var candidate in candidates.EnumerateArray())
        {
            cancellation.Token.ThrowIfCancellationRequested();
            Keys(candidate, "path", "sha256");
            var path = OwnedPath(root, Text(candidate, "path"));
            var expected = Text(candidate, "sha256");
            Require(HashPattern().IsMatch(expected), "EvidenceSchemaInvalid");
            var raw = Read(path, (int)Math.Min(MaxPackageBytes, MaxArchiveBytes - total));
            total += raw.Length;
            Require(Hash(raw) == expected, "InputChanged");
            using var stream = new MemoryStream(raw, writable: false);
            using (var zip = new ZipArchive(stream, ZipArchiveMode.Read, leaveOpen: true))
            {
                Require(zip.Entries.Count is > 0 and <= 4096, "OutputLimitExceeded");
                var nuspecs = zip.Entries.Where(entry => entry.FullName.EndsWith(".nuspec", StringComparison.OrdinalIgnoreCase)).ToArray();
                Require(nuspecs.Length == 1 && nuspecs[0].Length is > 0 and <= MaxManifestBytes,
                    "EvidenceSchemaInvalid");
            }
            stream.Position = 0;
            using var reader = new PackageArchiveReader(stream);
            var identity = reader.GetIdentity();
            Require(PackagePartPattern().IsMatch(identity.Id), "EvidenceSchemaInvalid");
            var groups = reader.NuspecReader.GetDependencyGroups().ToArray();
            Require(groups.Length <= 1024 && groups.Select(group => group.TargetFramework).Distinct().Count() == groups.Length,
                "EvidenceSchemaInvalid");
            var nearest = reducer.GetNearest(framework, groups.Select(group => group.TargetFramework));
            var dependencies = new SortedDictionary<string, VersionRange>(StringComparer.OrdinalIgnoreCase);
            foreach (var dependency in groups.Where(group => group.TargetFramework.Equals(nearest))
                .SelectMany(group => group.Packages))
            {
                Require(PackagePartPattern().IsMatch(dependency.Id) && dependency.VersionRange is not null
                    && dependencies.Count < 1024 && dependencies.TryAdd(dependency.Id, dependency.VersionRange),
                    "EvidenceSchemaInvalid");
            }
            var content = Convert.FromBase64String(reader.GetContentHash(cancellation.Token));
            Require(content.Length == 64 && archives.TryAdd(identity.Id, new(identity.Id, identity.Version, path,
                expected, Convert.ToHexStringLower(content), dependencies)), "ProofMismatch");
        }

        var names = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var entry in original.EnumerateObject())
        {
            Require(names.Count < 1024 && PackagePartPattern().IsMatch(entry.Name)
                && names.TryAdd(entry.Name, entry.Name) && entry.Value.ValueKind == JsonValueKind.Object,
                "EvidenceSchemaInvalid");
            var fields = entry.Value.EnumerateObject().Select(property => property.Name).ToArray();
            Require(fields.Length == fields.Distinct(StringComparer.Ordinal).Count()
                && fields.All(field => field is "type" or "requested" or "resolved" or "contentHash" or "dependencies")
                && new[] { "type", "resolved", "contentHash" }.All(field => fields.Contains(field)),
                "EvidenceSchemaInvalid");
            Require(Text(entry.Value, "type") is "Direct" or "Transitive" or "CentralTransitive",
                "EvidenceSchemaInvalid");
            Require(archives.TryGetValue(entry.Name, out var archive)
                && Text(entry.Value, "resolved").Equals(archive.Version.ToNormalizedString(), StringComparison.OrdinalIgnoreCase)
                && Text(entry.Value, "contentHash") == Convert.ToBase64String(Convert.FromHexString(archive.ContentHash)),
                "ProofMismatch");
            if (entry.Value.TryGetProperty("requested", out var requested))
            {
                Require(requested.ValueKind == JsonValueKind.String
                    && requested.GetString() is { Length: > 0 and <= 1024 } text
                    && VersionRange.TryParse(text, out var range)
                    && range.Satisfies(archive!.Version), "ProofMismatch");
            }
        }

        var visited = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var visiting = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        void Include(string id)
        {
            cancellation.Token.ThrowIfCancellationRequested();
            Require(archives.TryGetValue(id, out var archive), "EvidenceIncomplete");
            Require(!visiting.Contains(id), "ProofMismatch");
            if (!visited.Add(id)) { return; }
            visiting.Add(id);
            Require(visited.Count <= 1024, "OutputLimitExceeded");
            if (!names.TryGetValue(id, out var key))
            {
                key = archive!.Id;
                names.Add(id, key);
                var row = new JsonObject
                {
                    ["type"] = "Transitive",
                    ["resolved"] = archive.Version.ToNormalizedString(),
                    ["contentHash"] = Convert.ToBase64String(Convert.FromHexString(archive.ContentHash))
                };
                if (archive.Dependencies.Count > 0)
                {
                    var edges = new JsonObject();
                    foreach (var (dependency, range) in archive.Dependencies)
                    { edges.Add(dependency, range.ToNormalizedString()); }
                    row.Add("dependencies", edges);
                }
                locked.Add(key, row);
            }
            var declared = locked[key]!.AsObject()["dependencies"]?.AsObject() ?? new JsonObject();
            Require(declared.Count == archive!.Dependencies.Count
                && declared.All(edge => archive.Dependencies.Keys.Contains(edge.Key, StringComparer.OrdinalIgnoreCase)),
                "ProofMismatch");
            foreach (var (dependency, range) in archive.Dependencies)
            {
                Require(archives.TryGetValue(dependency, out var target) && range.Satisfies(target.Version),
                    "ProofMismatch");
                var edge = declared.Single(item => item.Key.Equals(dependency, StringComparison.OrdinalIgnoreCase));
                Require(edge.Value is JsonValue value && value.TryGetValue<string>(out var text)
                    && text.Length <= 1024 && VersionRange.TryParse(text, out var declaredRange)
                    && declaredRange.Satisfies(target!.Version), "ProofMismatch");
                Include(dependency);
            }
            visiting.Remove(id);
        }
        foreach (var id in names.Keys.ToArray()) { Include(id); }
        var adapterId = Text(adapter, "packageId");
        var adapterVersion = Text(adapter, "version");
        Require(PackagePartPattern().IsMatch(adapterId) && archives.TryGetValue(adapterId, out var selected)
            && adapterVersion.Equals(selected.Version.ToNormalizedString(), StringComparison.OrdinalIgnoreCase),
            "ProofMismatch");
        Include(adapterId);
        var adapterRow = locked[names[adapterId]]!.AsObject();
        adapterRow["type"] = "Direct";
        adapterRow["requested"] = $"[{adapterVersion}, {adapterVersion}]";
        var packages = visited.Select(id => archives[id]).OrderBy(archive => archive.Id, StringComparer.Ordinal).Select(archive => new
        {
            packageId = archive.Id,
            version = archive.Version.ToNormalizedString(),
            archiveSha256 = archive.ArchiveHash,
            nugetContentSha512 = archive.ContentHash
        }).ToArray();
        var receipt = JsonSerializer.SerializeToUtf8Bytes(new
        {
            schemaVersion = 1,
            qualification = false,
            sourceLockSha256 = sourceHash,
            packages,
            @lock = lockDocument
        });
        Require(receipt.Length <= MaxManifestBytes, "OutputLimitExceeded");
        foreach (var archive in archives.Values)
        {
            cancellation.Token.ThrowIfCancellationRequested();
            Require(Hash(Read(archive.Path, MaxPackageBytes)) == archive.ArchiveHash, "InputChanged");
        }
        Require(Hash(Read(sourcePath, MaxManifestBytes)) == sourceHash
            && Hash(Read(requestPath, MaxManifestBytes)) == requestHash, "InputChanged");
        using var output = new FileStream(outputPath, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        output.Write(receipt);
        return packages.Length;
    }
}
