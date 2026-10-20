using System.Text.Json;
using System.Xml.Linq;

namespace Hoard.Architecture.Tests;

internal static class DependencyGraphInspector
{
    internal static void Read(InspectionEvidence evidence)
    {
        foreach (var project in evidence.Projects.EnumerateArray())
        {
            var id = project.GetProperty("id").GetString()!;
            var path = project.GetProperty("project").GetString()!;
            var xml = XDocument.Load(path);
            var references = project.GetProperty("references").EnumerateArray().ToArray();
            foreach (var framework in xml.Descendants().Where(e => e.Name.LocalName == "FrameworkReference"))
            {
                var name = framework.Attribute("Include")?.Value;
                if (name is null || !references.Any(reference => reference.TryGetProperty("FrameworkReferenceName", out var f)
                    && f.GetString() == name))
                {
                    throw new InspectionException($"Unresolved declared framework reference: {id} -> {name}.");
                }
            }
            foreach (var reference in references.Where(r => r.TryGetProperty("FrameworkReferenceName", out _)))
            {
                var target = Path.GetFileNameWithoutExtension(reference.GetProperty("Identity").GetString()!);
                Edge(evidence, id, evidence.AssemblyOwners[target], "resolved framework", path);
            }
            foreach (var reference in xml.Descendants().Where(e => e.Name.LocalName is "ProjectReference" or "PackageReference"))
            {
                var target = reference.Attribute("Include")?.Value
                    ?? throw new InspectionException($"Missing declared reference identity: {id}.");
                if (reference.Name.LocalName == "ProjectReference")
                {
                    target = Path.GetFileNameWithoutExtension(target);
                }
                Edge(evidence, id, target, "declared", path);
            }
            var assetsPath = project.GetProperty("assets").GetString()!;
            using var assets = JsonDocument.Parse(File.ReadAllText(assetsPath));
            var identities = assets.RootElement.GetProperty("libraries").EnumerateObject().ToDictionary(
                library => library.Name.Split('/')[0],
                library => library.Value.GetProperty("type").GetString() == "project"
                    ? Path.GetFileNameWithoutExtension(library.Value.GetProperty("path").GetString()!)
                    : library.Name.Split('/')[0]);
            var targets = assets.RootElement.GetProperty("targets");
            if (targets.EnumerateObject().Count() != 1 || !targets.TryGetProperty("net10.0", out var targetFramework))
            {
                throw new InspectionException($"Missing/ambiguous exact net10.0 restore target: {id}.");
            }
            foreach (var library in targetFramework.EnumerateObject())
            {
                var source = identities[library.Name.Split('/')[0]];
                Require(evidence, source);
                var framework = assets.RootElement.GetProperty("project").GetProperty("frameworks").GetProperty("net10.0");
                if (framework.TryGetProperty("dependencies", out var direct) && direct.TryGetProperty(source, out _))
                {
                    Edge(evidence, id, source, "resolved direct", assetsPath);
                }
                if (library.Value.TryGetProperty("dependencies", out var dependencies))
                {
                    foreach (var dependency in dependencies.EnumerateObject())
                    {
                        Edge(evidence, source, identities[dependency.Name], "resolved transitive", assetsPath);
                    }
                }
                var details = assets.RootElement.GetProperty("libraries").GetProperty(library.Name);
                if (details.GetProperty("type").GetString() == "package")
                {
                    var folder = assets.RootElement.GetProperty("packageFolders").EnumerateObject().Single().Name;
                    var packagePath = Path.Combine(folder, details.GetProperty("path").GetString()!);
                    var nuspec = XDocument.Load(Directory.GetFiles(packagePath, "*.nuspec").Single());
                    var metadata = nuspec.Root!.Elements().Single(e => e.Name.LocalName == "metadata");
                    if (metadata.Elements().Single(e => e.Name.LocalName == "id").Value != source
                        || metadata.Elements().Single(e => e.Name.LocalName == "version").Value != library.Name.Split('/')[1])
                    {
                        throw new InspectionException($"Packed/resolved identity mismatch: {source}.");
                    }
                    var groups = metadata.Descendants().Where(e => e.Name.LocalName == "group").ToArray();
                    var group = groups.FirstOrDefault(g => g.Attribute("targetFramework")?.Value == "net10.0")
                        ?? groups.FirstOrDefault(g => g.Attribute("targetFramework")?.Value == "net8.0")
                        ?? groups.SingleOrDefault();
                    var packed = (group ?? metadata).Descendants().Where(e => e.Name.LocalName == "dependency")
                        .Select(e => e.Attribute("id")!.Value).Distinct().Order().ToArray();
                    var resolved = library.Value.TryGetProperty("dependencies", out var deps)
                        ? deps.EnumerateObject().Select(d => d.Name).Order().ToArray() : [];
                    if (!packed.SequenceEqual(resolved))
                    {
                        throw new InspectionException($"Packed/resolved dependency disagreement: {source}.");
                    }
                    foreach (var dependency in packed)
                    {
                        Edge(evidence, source, dependency, "packed nuspec", packagePath);
                    }
                    var packedFrameworks = metadata.Descendants().Where(e => e.Name.LocalName == "frameworkReference")
                        .Select(e => e.Attribute("name")!.Value).Distinct().Order().ToArray();
                    var resolvedFrameworks = library.Value.TryGetProperty("frameworkReferences", out var frameworks)
                        ? frameworks.EnumerateArray().Select(item => item.GetString()!).Order().ToArray() : [];
                    if (!packedFrameworks.SequenceEqual(resolvedFrameworks))
                    { throw new InspectionException($"Packed/resolved framework disagreement: {source}."); }
                }
            }
        }
        foreach (var pair in evidence.Assemblies.Where(a => !evidence.Nodes[a.Key].IsFramework))
        {
            foreach (var reference in pair.Value.MainModule.AssemblyReferences)
            {
                if (!evidence.AssemblyOwners.TryGetValue(reference.Name, out var owner)
                    || (evidence.Nodes[owner].Identity != reference.FullName
                        && !FrameworkCompatible(evidence.Nodes[owner], reference, evidence.Assemblies[owner].Name)))
                {
                    throw new InspectionException($"Unresolved compiled reference: {pair.Key} -> {reference.FullName}.");
                }
                Edge(evidence, pair.Key, owner, "compiled reference", evidence.Nodes[pair.Key].Assembly);
            }
        }
    }

    internal static bool FrameworkCompatible(InspectionNode node, Mono.Cecil.AssemblyNameReference requested,
        Mono.Cecil.AssemblyNameReference resolved) =>
        node.IsFramework && node.Boundary is BoundaryOwnership.Bcl or BoundaryOwnership.Http && requested.Name == resolved.Name
        && requested.Culture == resolved.Culture && requested.Version <= resolved.Version
        && requested.PublicKeyToken.SequenceEqual(resolved.PublicKeyToken);

    private static void Require(InspectionEvidence evidence, string id)
    {
        if (!evidence.Nodes.ContainsKey(id))
        {
            throw new InspectionException($"Unclassified dependency: {id}.");
        }
    }

    private static void Edge(InspectionEvidence evidence, string source, string target, string kind, string location)
    {
        Require(evidence, source);
        Require(evidence, target);
        if (source != target)
        {
            evidence.Edges.Add(new(source, target, kind, location));
        }
    }

    internal static List<ArchitectureViolation> Inspect(InspectionEvidence evidence)
    {
        var result = Cycles(evidence.Edges);
        foreach (var source in evidence.Nodes.Values.Where(n => !n.IsFramework))
        {
            var queue = new Queue<(string Id, string[] Path, bool ViaHosting)>();
            queue.Enqueue((source.Id, [source.Id], false));
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { source.Id };
            var seenViaHosting = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            while (queue.TryDequeue(out var current))
            {
                foreach (var edge in evidence.Edges.Where(e => e.Source == current.Id))
                {
                    var target = evidence.Nodes[edge.Target];
                    var viaHosting = current.ViaHosting || (source.Boundary is BoundaryOwnership.Identity or BoundaryOwnership.Protocol or BoundaryOwnership.Application
                        && current.Path.Length == 1 && target.Boundary == BoundaryOwnership.Hosting);
                    // A permitted Hosting path must not hide another route to the same dependency.
                    if (!(viaHosting ? seenViaHosting : seen).Add(edge.Target))
                    {
                        continue;
                    }
                    var path = current.Path.Append(edge.Target).ToArray();
                    var rule = Rule(source.Boundary, target.Boundary, path.Length, viaHosting);
                    if (rule is not null)
                    {
                        result.Add(new(rule, source.Id, target.Id, $"{edge.Kind}: {edge.Location}", string.Join(" -> ", path)));
                    }
                    queue.Enqueue((target.Id, path, viaHosting));
                }
            }
        }
        return result;
    }

    internal static string? Rule(BoundaryOwnership source, BoundaryOwnership target, int length, bool viaHosting)
    {
        if (target == BoundaryOwnership.Bcl)
        {
            return null;
        }
        return source switch
        {
            BoundaryOwnership.Abstractions => "ARCH-001",
            BoundaryOwnership.Core when target != BoundaryOwnership.Abstractions => length == 2 ? "ARCH-002" : "ARCH-003",
            BoundaryOwnership.Protocol or BoundaryOwnership.Metadata or BoundaryOwnership.Artifact or BoundaryOwnership.Identity
                when target is BoundaryOwnership.Protocol or BoundaryOwnership.Metadata or BoundaryOwnership.Artifact or BoundaryOwnership.Identity => "ARCH-005",
            BoundaryOwnership.Application or BoundaryOwnership.Protocol
                when target is not (BoundaryOwnership.Abstractions or BoundaryOwnership.Core or BoundaryOwnership.Hosting or BoundaryOwnership.Http)
                    && !(target == BoundaryOwnership.Versioning && viaHosting)
                    && !(target == BoundaryOwnership.Di && length > 2) => "ARCH-008",
            BoundaryOwnership.Hosting when target is not (BoundaryOwnership.Abstractions or BoundaryOwnership.Core or BoundaryOwnership.Di or BoundaryOwnership.Http or BoundaryOwnership.Versioning) => "ARCH-008",
            BoundaryOwnership.Metadata or BoundaryOwnership.Artifact
                when target is not (BoundaryOwnership.Abstractions or BoundaryOwnership.Sdk) => "ARCH-008",
            BoundaryOwnership.Identity when target is not (BoundaryOwnership.Abstractions or BoundaryOwnership.Hosting or BoundaryOwnership.Di or BoundaryOwnership.Sdk or BoundaryOwnership.Http)
                && !(target is BoundaryOwnership.Core or BoundaryOwnership.Versioning && viaHosting) => "ARCH-008",
            _ => null
        };
    }

    internal static List<ArchitectureViolation> Cycles(IReadOnlyCollection<DependencyEdge> edges)
    {
        var violations = new List<ArchitectureViolation>();
        var visited = new HashSet<string>();
        var stack = new List<string>();
        void Visit(string node)
        {
            var index = stack.IndexOf(node);
            if (index >= 0)
            {
                violations.Add(new("ARCH-006", stack[^1], node, "dependency graph", string.Join(" -> ", stack.Skip(index).Append(node))));
                return;
            }
            if (!visited.Add(node))
            {
                return;
            }
            stack.Add(node);
            foreach (var edge in edges.Where(e => e.Source == node))
            {
                Visit(edge.Target);
            }
            stack.RemoveAt(stack.Count - 1);
        }
        foreach (var node in edges.Select(e => e.Source).Distinct())
        {
            Visit(node);
        }
        return violations;
    }
}
