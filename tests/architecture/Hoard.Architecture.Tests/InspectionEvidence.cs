using System.Text.Json;
using Mono.Cecil;

namespace Hoard.Architecture.Tests;

internal sealed record InspectionNode(string Id, BoundaryOwnership Boundary, string Assembly, string Identity);
internal sealed record DependencyEdge(string Source, string Target, string Kind, string Location);
internal sealed record ArchitectureViolation(string RuleId, string Source, string Target, string Location, string Path);
internal sealed class InspectionException(string message) : Exception($"INSPECTION: {message}");

internal sealed class InspectionEvidence : IDisposable
{
    internal Dictionary<string, InspectionNode> Nodes { get; } = new(StringComparer.OrdinalIgnoreCase);
    internal Dictionary<string, string> AssemblyOwners { get; } = new(StringComparer.OrdinalIgnoreCase);
    internal List<DependencyEdge> Edges { get; } = [];
    internal Dictionary<string, AssemblyDefinition> Assemblies { get; } = new(StringComparer.OrdinalIgnoreCase);
    internal Dictionary<string, List<string>> SliceRoots { get; } = new(StringComparer.OrdinalIgnoreCase);
    internal JsonElement Projects { get; }

    private InspectionEvidence(JsonElement input) => Projects = input.GetProperty("projects");

    internal static InspectionEvidence Load(JsonElement input)
    {
        var evidence = new InspectionEvidence(input);
        try
        {
            evidence.Read(input);
            return evidence;
        }
        catch
        {
            evidence.Dispose();
            throw;
        }
    }

    private void Read(JsonElement input)
    {
        if (Projects.GetArrayLength() == 0)
        {
            throw new InspectionException("Empty project inspection manifest.");
        }
        var ownership = input.GetProperty("ownership").Deserialize<Dictionary<string, string>>()!;
        foreach (var project in Projects.EnumerateArray())
        {
            var id = project.GetProperty("id").GetString()!;
            Add(id, Enum.Parse<BoundaryOwnership>(ownership[id]), project.GetProperty("assembly").GetString()!);
        }
        foreach (var project in Projects.EnumerateArray())
        {
            var references = project.GetProperty("references");
            if (references.GetArrayLength() == 0)
            {
                throw new InspectionException("Missing resolved framework/reference inputs.");
            }
            using var assets = JsonDocument.Parse(File.ReadAllText(project.GetProperty("assets").GetString()!));
            foreach (var reference in references.EnumerateArray())
            {
                var file = reference.GetProperty("Identity").GetString()!;
                var name = Path.GetFileNameWithoutExtension(file);
                if (!File.Exists(file))
                {
                    throw new InspectionException($"Missing resolved reference: {name}.");
                }
                if (AssemblyOwners.TryGetValue(name, out var known))
                {
                    using var resolved = AssemblyDefinition.ReadAssembly(file);
                    if (resolved.Name.FullName != Nodes[known].Identity)
                    {
                        throw new InspectionException($"Resolved assembly identity disagreement: {name}.");
                    }
                    continue;
                }
                var framework = reference.TryGetProperty("FrameworkReferenceName", out var f) ? f.GetString() : null;
                var package = reference.TryGetProperty("NuGetPackageId", out var p) ? p.GetString() : null;
                if (framework is "Microsoft.NETCore.App" or "Microsoft.AspNetCore.App"
                    && package == $"{framework}.Ref"
                    && assets.RootElement.GetProperty("project").GetProperty("frameworks").GetProperty("net10.0")
                        .GetProperty("frameworkReferences").TryGetProperty(framework, out _))
                {
                    Add(name, framework == "Microsoft.NETCore.App" ? BoundaryOwnership.Bcl : BoundaryOwnership.Http, file);
                }
                else if (package is not null && ownership.TryGetValue(package, out var owner))
                {
                    Add(package, Enum.Parse<BoundaryOwnership>(owner), file);
                }
                else
                {
                    throw new InspectionException($"Unknown non-framework ownership: {name}.");
                }
            }
        }
        foreach (var project in Projects.EnumerateArray())
        {
            var id = project.GetProperty("id").GetString()!;
            var roots = new List<string>();
            foreach (var source in project.GetProperty("sources").EnumerateArray())
            {
                var path = source.GetString()!;
                var normalized = path.Replace('\\', '/');
                var index = normalized.IndexOf("/Features/", StringComparison.Ordinal);
                if (index < 0)
                {
                    continue;
                }
                var suffix = Path.GetDirectoryName(normalized[(index + 1)..])!.Replace('/', '.');
                var text = File.ReadAllText(path);
                var match = System.Text.RegularExpressions.Regex.Match(text, @"namespace\s+([\w.]+)\s*[;{]");
                if (!match.Success || !match.Groups[1].Value.EndsWith("." + suffix, StringComparison.Ordinal))
                {
                    throw new InspectionException($"Slice folder/namespace disagreement: {Path.GetFileName(path)}.");
                }
                var root = match.Groups[1].Value;
                if (!roots.Contains(root))
                {
                    roots.Add(root);
                }
            }
            SliceRoots.Add(id, roots);
        }
    }

    private void Add(string id, BoundaryOwnership boundary, string path)
    {
        if (!File.Exists(path))
        {
            throw new InspectionException($"Missing assembly input: {Path.GetFileName(path)}.");
        }
        var assembly = AssemblyDefinition.ReadAssembly(path);
        var name = assembly.Name.Name;
        if (name != Path.GetFileNameWithoutExtension(path))
        {
            assembly.Dispose();
            throw new InspectionException($"Assembly identity mismatch: {id}.");
        }
        if (Nodes.TryGetValue(id, out var existing))
        {
            assembly.Dispose();
            if (existing.Boundary != boundary || existing.Identity != assembly.Name.FullName)
            {
                throw new InspectionException($"Conflicting ownership: {id}.");
            }
            return;
        }
        if (!AssemblyOwners.TryAdd(name, id))
        {
            assembly.Dispose();
            throw new InspectionException($"Duplicate assembly ownership: {name}.");
        }
        Nodes.Add(id, new(id, boundary, path, assembly.Name.FullName));
        Assemblies.Add(id, assembly);
    }

    internal string Owner(TypeReference type)
    {
        type = type.GetElementType();
        if (type is GenericParameter)
        {
            throw new InspectionException("Generic parameter has no assembly ownership.");
        }
        var name = type.Scope switch
        {
            AssemblyNameReference reference => reference.Name,
            ModuleDefinition module => module.Assembly.Name.Name,
            _ => throw new InspectionException($"Unresolved type scope: {type.FullName}.")
        };
        return AssemblyOwners.TryGetValue(name, out var owner)
            ? owner : throw new InspectionException($"Unresolved type assembly: {name}.");
    }

    public void Dispose()
    {
        foreach (var assembly in Assemblies.Values)
        {
            assembly.Dispose();
        }
    }
}
