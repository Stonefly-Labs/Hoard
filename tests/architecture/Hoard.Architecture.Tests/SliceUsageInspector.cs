using Mono.Cecil;

namespace Hoard.Architecture.Tests;

internal static class SliceUsageInspector
{
    internal static List<ArchitectureViolation> Inspect(InspectionEvidence evidence)
    {
        var result = new List<ArchitectureViolation>();
        foreach (var project in evidence.Projects.EnumerateArray())
        {
            var source = project.GetProperty("id").GetString()!;
            var node = evidence.Nodes[source];
            if (node.Boundary is not (BoundaryOwnership.Application or BoundaryOwnership.Protocol))
            {
                continue;
            }
            foreach (var type in PublicSurfaceInspector.Types(evidence.Assemblies[source].MainModule))
            {
                var slice = Slice(evidence, source, type);
                Check(PublicSurfaceInspector.Expand(type.BaseType).Concat(PublicSurfaceInspector.Attributes(type))
                    .Concat(PublicSurfaceInspector.Constraints(type))
                    .Concat(type.Interfaces.SelectMany(i => PublicSurfaceInspector.Expand(i.InterfaceType)
                        .Concat(PublicSurfaceInspector.Attributes(i)))), type.FullName);
                foreach (var field in type.Fields)
                {
                    Check(PublicSurfaceInspector.Expand(field.FieldType).Concat(PublicSurfaceInspector.Attributes(field)), field.FullName);
                }
                foreach (var property in type.Properties)
                {
                    Check(PublicSurfaceInspector.Expand(property.PropertyType).Concat(PublicSurfaceInspector.Attributes(property)), property.FullName);
                }
                foreach (var item in type.Events)
                {
                    Check(PublicSurfaceInspector.Expand(item.EventType).Concat(PublicSurfaceInspector.Attributes(item)), item.FullName);
                }
                foreach (var method in type.Methods)
                {
                    Check(PublicSurfaceInspector.Signature(method), method.FullName);
                    if (!method.HasBody)
                    {
                        continue;
                    }
                    Check(method.Body.Variables.SelectMany(v => PublicSurfaceInspector.Expand(v.VariableType)), method.FullName);
                    foreach (var handler in method.Body.ExceptionHandlers)
                    {
                        Check(PublicSurfaceInspector.Expand(handler.CatchType), method.FullName);
                    }
                    foreach (var instruction in method.Body.Instructions)
                    {
                        Check(PublicSurfaceInspector.Operand(instruction.Operand), $"{method.FullName} IL_{instruction.Offset:x4}");
                    }
                }
                void Check(IEnumerable<TypeReference> references, string location)
                {
                    foreach (var reference in references)
                    {
                        var owner = evidence.Owner(reference);
                        var targetSlice = Slice(evidence, owner, reference);
                        if (slice is not null && targetSlice is not null && (source != owner || slice != targetSlice))
                        {
                            result.Add(new("ARCH-007", source, owner, location, $"{slice} -> {targetSlice}: {reference.FullName}"));
                        }
                        if (evidence.Nodes[owner].Boundary is BoundaryOwnership.Sdk or BoundaryOwnership.Metadata
                            or BoundaryOwnership.Artifact or BoundaryOwnership.Identity)
                        {
                            result.Add(new("ARCH-008", source, owner, location, $"{source} -> {reference.FullName} ({owner})"));
                        }
                    }
                }
            }
        }
        return result;
    }

    private static string? Slice(InspectionEvidence evidence, string owner, TypeReference type)
    {
        while (type.DeclaringType is not null)
        {
            type = type.DeclaringType;
        }
        var ns = type.Namespace;
        if (!ns.Contains(".Features.", StringComparison.Ordinal))
        {
            return null;
        }
        if (!evidence.SliceRoots.TryGetValue(owner, out var roots))
        {
            throw new InspectionException($"Unmapped external slice ownership: {type.FullName}.");
        }
        return roots.OrderByDescending(r => r.Length).FirstOrDefault(r => ns == r || ns.StartsWith(r + ".", StringComparison.Ordinal))
            ?? throw new InspectionException($"Unmapped slice namespace: {type.FullName}.");
    }
}
