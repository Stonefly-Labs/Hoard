using System.Text;
using System.Text.Json;
using Microsoft.Build.Evaluation;
using Microsoft.Build.Framework;
using static Hoard.Fixtures.Conformance.BuildInputs.Program;

namespace Hoard.Fixtures.Conformance.BuildInputs;

public sealed class ReadBindingInputs : Microsoft.Build.Utilities.Task
{
    [Required]
    public string OwnedRootBase64 { get; set; } = "";

    [Required]
    public string RequestPath { get; set; } = "";

    [Required]
    public string RequestSha256 { get; set; } = "";

    public override bool Execute()
    {
        try
        {
            WriteEvent("None", Capture());
            return true;
        }
        catch (InputException error)
        {
            WriteEvent(error.Message, 0);
            return false;
        }
        catch (Microsoft.Build.Exceptions.InvalidProjectFileException)
        {
            WriteEvent("BindingInvalid", 0);
            return false;
        }
        catch
        {
            WriteEvent("UnknownDiagnostic", 0);
            return false;
        }
    }

    private int Capture()
    {
        var root = new UTF8Encoding(false, true).GetString(Convert.FromBase64String(OwnedRootBase64));
        Require(Path.IsPathFullyQualified(root) && Path.GetFullPath(root) == root, "OwnershipInvalid");
        var requestPath = OwnedPath(root, RequestPath);
        var requestBytes = Read(requestPath, MaxManifestBytes);
        Require(HashPattern().IsMatch(RequestSha256) && Hash(requestBytes) == RequestSha256, "InputChanged");
        using var request = JsonDocument.Parse(requestBytes, new JsonDocumentOptions { MaxDepth = 16 });
        var value = request.RootElement;
        Keys(value, "schemaVersion", "qualification", "sourcePath", "project", "toolchainRoot", "sources", "outputPath");
        Require(value.GetProperty("schemaVersion").GetInt32() == 1
            && value.GetProperty("qualification").ValueKind == JsonValueKind.False, "EvidenceSchemaInvalid");
        var source = OwnedPath(root, Text(value, "sourcePath"));
        var project = Text(value, "project");
        Require(project.EndsWith(".csproj", StringComparison.Ordinal), "EvidenceSchemaInvalid");
        var projectPath = OwnedPath(source, project);
        var toolchain = Directory.GetParent(Path.GetDirectoryName(typeof(ProjectCollection).Assembly.Location)!)?.Parent;
        Require(toolchain is not null && Text(value, "toolchainRoot") == toolchain.FullName, "OwnershipInvalid");
        Require(!source.StartsWith(toolchain!.FullName + Path.DirectorySeparatorChar, StringComparison.Ordinal)
            && !toolchain.FullName.StartsWith(source + Path.DirectorySeparatorChar, StringComparison.Ordinal)
            && source != toolchain.FullName, "OwnershipInvalid");
        var outputPath = OwnedPath(root, Text(value, "outputPath"));
        Require(!File.Exists(outputPath) && !Directory.Exists(outputPath), "OwnershipInvalid");
        var expected = new Dictionary<string, string>(StringComparer.Ordinal);
        var expectedSources = value.GetProperty("sources");
        Require(expectedSources.ValueKind == JsonValueKind.Object, "EvidenceSchemaInvalid");
        foreach (var item in expectedSources.EnumerateObject())
        {
            _ = OwnedPath(source, item.Name);
            var hash = item.Value.GetString();
            Require(hash is not null && HashPattern().IsMatch(hash)
                && expected.Count < 4096 && expected.TryAdd(item.Name, hash), "EvidenceSchemaInvalid");
        }

        Require(expected.ContainsKey(project), "EvidenceIncomplete");
        var inputs = new SortedDictionary<string, string>(StringComparer.Ordinal);
        long total = 0;
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(30));

        void Add(string name)
        {
            cancellation.Token.ThrowIfCancellationRequested();
            var path = Path.GetFullPath(name);
            var owner = path.StartsWith(source + Path.DirectorySeparatorChar, StringComparison.Ordinal) ? source
                : path.StartsWith(toolchain.FullName + Path.DirectorySeparatorChar, StringComparison.Ordinal)
                    ? toolchain.FullName : null;
            Require(owner is not null, "OwnershipInvalid");
            var relative = path[(owner!.Length + 1)..].Replace(Path.DirectorySeparatorChar, '/');
            var identity = (owner == source ? "source/" : "toolchain/") + relative;
            if (owner == source)
            {
                Require(expected.ContainsKey(relative), "EvidenceIncomplete");
            }

            var bytes = Read(OwnedPath(owner, relative), (int)Math.Min(MaxPackageBytes, MaxArchiveBytes - total),
                allowEmpty: true);
            total += bytes.Length;
            var hash = Hash(bytes);
            Require(owner != source || expected[relative] == hash, "InputChanged");
            if (inputs.TryGetValue(identity, out var previous))
            {
                Require(previous == hash, "InputChanged");
            }
            else
            {
                Require(inputs.Count < 4096, "OutputLimitExceeded");
                inputs.Add(identity, hash);
            }
        }

        var pending = new Queue<string>();
        var visited = new HashSet<string>(StringComparer.Ordinal);
        var projects = new List<object>();
        pending.Enqueue(projectPath);
        using var collection = new ProjectCollection(new Dictionary<string, string>
        {
            ["Configuration"] = "Release",
            ["TargetFramework"] = "net10.0"
        });
        while (pending.TryDequeue(out var path))
        {
            if (!visited.Add(path))
            {
                continue;
            }

            Require(visited.Count <= 128, "OutputLimitExceeded");
            Add(path);
            var evaluated = collection.LoadProject(path);
            var packable = evaluated.GetPropertyValue("IsPackable");
            var packageId = evaluated.GetPropertyValue("PackageId");
            Require(bool.TryParse(packable, out var isPackable)
                && PackagePartPattern().IsMatch(packageId)
                && NuGet.Versioning.NuGetVersion.TryParse(evaluated.GetPropertyValue("PackageVersion"), out _),
                "BindingInvalid");
            projects.Add(new
            {
                Identity = Path.GetRelativePath(source, path).Replace(Path.DirectorySeparatorChar, '/'),
                PackageId = packageId,
                PackageVersion = NuGet.Versioning.NuGetVersion.Parse(
                    evaluated.GetPropertyValue("PackageVersion")).ToNormalizedString(),
                IsPackable = isPackable ? "true" : "false"
            });
            foreach (var import in evaluated.Imports)
            {
                Add(import.ImportedProject.FullPath);
            }

            foreach (var type in new[] { "Compile", "None", "Content", "EmbeddedResource", "AdditionalFiles", "AnalyzerConfigFiles" })
            {
                foreach (var item in evaluated.GetItems(type))
                {
                    Add(item.GetMetadataValue("FullPath"));
                }
            }

            foreach (var reference in evaluated.GetItems("ProjectReference"))
            {
                Require(pending.Count < 128, "OutputLimitExceeded");
                pending.Enqueue(reference.GetMetadataValue("FullPath"));
            }
        }

        foreach (var (identity, hash) in inputs)
        {
            cancellation.Token.ThrowIfCancellationRequested();
            var separator = identity.IndexOf('/');
            var owner = identity.StartsWith("source/", StringComparison.Ordinal) ? source : toolchain.FullName;
            var bytes = Read(OwnedPath(owner, identity[(separator + 1)..]),
                (int)Math.Min(MaxPackageBytes, MaxArchiveBytes - total), allowEmpty: true);
            total += bytes.Length;
            Require(Hash(bytes) == hash, "InputChanged");
        }

        var receipt = JsonSerializer.SerializeToUtf8Bytes(new
        {
            Items = new
            {
                _BindingInputs = inputs.Select(input => new
                {
                    Identity = input.Key,
                    Kind = input.Key.StartsWith("source/", StringComparison.Ordinal) ? "source" : "toolchain",
                    Sha256 = input.Value
                }).ToArray(),
                _BindingProjects = projects
            }
        });
        Require(receipt.Length <= MaxManifestBytes, "OutputLimitExceeded");
        Require(Hash(Read(requestPath, MaxManifestBytes)) == RequestSha256, "InputChanged");
        using var output = new FileStream(outputPath, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        output.Write(receipt);
        return inputs.Count;
    }

    private static void WriteEvent(string code, int value) =>
        Console.WriteLine(JsonSerializer.Serialize(new { @event = "control", code, value }));
}
