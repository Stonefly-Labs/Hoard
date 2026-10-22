using Mono.Cecil;

namespace Hoard.Architecture.Tests;

internal static class PublicSurfaceInspector
{
    private static readonly HashSet<string> ProhibitedContractTypes =
    [
        "System.Linq.IQueryable", "System.Linq.IQueryable`1",
        "System.Data.IDbConnection", "System.Data.IDbTransaction",
        "System.Data.Common.DbConnection", "System.Data.Common.DbTransaction"
    ];
    private static readonly HashSet<string> ProhibitedArtifactTypes =
    [
        "System.IServiceProvider",
        "System.IO.FileSystemInfo", "System.IO.FileInfo", "System.IO.DirectoryInfo",
        "System.IO.FileStream", "System.IO.FileSystemWatcher", "System.IO.DriveInfo",
        "Microsoft.Win32.SafeHandles.SafeFileHandle"
    ];

    private static bool Visible(TypeDefinition type) =>
        type.DeclaringType is null ? type.IsPublic
            : (type.IsNestedPublic || type.IsNestedFamily || type.IsNestedFamilyOrAssembly) && Visible(type.DeclaringType);

    private static bool Visible(MethodDefinition? method) =>
        method is not null && (method.IsPublic || method.IsFamily || method.IsFamilyOrAssembly);

    internal static IEnumerable<TypeDefinition> Types(ModuleDefinition module) => module.Types.SelectMany(Flatten);

    private static IEnumerable<TypeDefinition> Flatten(TypeDefinition type) =>
        new[] { type }.Concat(type.NestedTypes.SelectMany(Flatten));

    internal static IEnumerable<TypeReference> Expand(TypeReference? type)
    {
        if (type is null or GenericParameter)
        {
            yield break;
        }
        if (type is GenericInstanceType generic)
        {
            foreach (var argument in generic.GenericArguments.SelectMany(Expand))
            {
                yield return argument;
            }
        }
        if (type is IModifierType modifier)
        {
            foreach (var item in Expand(modifier.ModifierType))
            {
                yield return item;
            }
        }
        if (type is FunctionPointerType pointer)
        {
            foreach (var item in Expand(pointer.ReturnType).Concat(pointer.Parameters.SelectMany(p => Expand(p.ParameterType))))
            {
                yield return item;
            }
            yield break;
        }
        if (type is TypeSpecification specification)
        {
            foreach (var item in Expand(specification.ElementType))
            {
                yield return item;
            }
        }
        else
        {
            yield return type;
        }
    }

    private static IEnumerable<TypeReference> Argument(CustomAttributeArgument argument)
    {
        return Expand(argument.Type).Concat(argument.Value switch
        {
            TypeReference type => Expand(type),
            CustomAttributeArgument[] arguments => arguments.SelectMany(Argument),
            CustomAttributeArgument nested => Argument(nested),
            _ => []
        });
    }

    internal static IEnumerable<TypeReference> Attributes(ICustomAttributeProvider provider) =>
        provider.CustomAttributes.SelectMany(a => Expand(a.AttributeType)
            .Concat(a.ConstructorArguments.SelectMany(Argument))
            .Concat(a.Fields.SelectMany(f => Argument(f.Argument)))
            .Concat(a.Properties.SelectMany(p => Argument(p.Argument))));

    internal static IEnumerable<TypeReference> Constraints(IGenericParameterProvider provider) =>
        provider.GenericParameters.SelectMany(p => p.Constraints.SelectMany(c => Expand(c.ConstraintType).Concat(Attributes(c)))
            .Concat(Attributes(p)));

    internal static IEnumerable<TypeReference> Signature(MethodDefinition method) =>
        Expand(method.ReturnType).Concat(Attributes(method)).Concat(Attributes(method.MethodReturnType))
            .Concat(Constraints(method)).Concat(method.Parameters.SelectMany(p => Expand(p.ParameterType).Concat(Attributes(p))));

    internal static List<ArchitectureViolation> Inspect(InspectionEvidence evidence)
    {
        var result = new List<ArchitectureViolation>();
        foreach (var node in evidence.Nodes.Values.Where(n => n.Boundary is BoundaryOwnership.Abstractions
                     or BoundaryOwnership.Core or BoundaryOwnership.Hosting or BoundaryOwnership.Application or BoundaryOwnership.Protocol
                     or BoundaryOwnership.Metadata or BoundaryOwnership.Artifact or BoundaryOwnership.Identity))
        {
            var assembly = evidence.Assemblies[node.Id];
            Check(Attributes(assembly), "<assembly>");
            foreach (var type in Types(assembly.MainModule).Where(Visible))
            {
                Check(Expand(type.BaseType).Concat(type.Interfaces.SelectMany(i => Expand(i.InterfaceType).Concat(Attributes(i))))
                    .Concat(Attributes(type)).Concat(Constraints(type)), type.FullName);
                foreach (var field in type.Fields.Where(f => f.IsPublic || f.IsFamily || f.IsFamilyOrAssembly))
                {
                    Check(Expand(field.FieldType).Concat(Attributes(field)), field.FullName);
                }
                foreach (var method in type.Methods.Where(m => m.IsPublic || m.IsFamily || m.IsFamilyOrAssembly))
                {
                    Check(Signature(method), method.FullName);
                }
                foreach (var property in type.Properties.Where(p => Visible(p.GetMethod) || Visible(p.SetMethod)))
                {
                    Check(Expand(property.PropertyType).Concat(Attributes(property)), property.FullName);
                }
                foreach (var item in type.Events.Where(e => Visible(e.AddMethod) || Visible(e.RemoveMethod)))
                {
                    Check(Expand(item.EventType).Concat(Attributes(item)), item.FullName);
                }
            }
            void Check(IEnumerable<TypeReference> types, string location)
            {
                foreach (var type in types)
                {
                    var owner = evidence.Owner(type);
                    var target = evidence.Nodes[owner];
                    var prohibited = target.Boundary == BoundaryOwnership.Bcl
                        && (ProhibitedContractTypes.Contains(type.FullName)
                            || node.Boundary is BoundaryOwnership.Abstractions or BoundaryOwnership.Artifact
                            && ProhibitedArtifactTypes.Contains(type.FullName));
                    var allowed = !prohibited && (target.Boundary == BoundaryOwnership.Bcl || owner == node.Id
                        || (node.Boundary != BoundaryOwnership.Abstractions && target.Boundary == BoundaryOwnership.Abstractions)
                        || (node.Boundary is BoundaryOwnership.Hosting or BoundaryOwnership.Application or BoundaryOwnership.Protocol
                            && target.Boundary is BoundaryOwnership.Core or BoundaryOwnership.Hosting)
                        || (node.Boundary == BoundaryOwnership.Hosting && target.Boundary == BoundaryOwnership.Di));
                    allowed |= node.Boundary == BoundaryOwnership.Identity && target.Boundary == BoundaryOwnership.Hosting;
                    allowed |= !prohibited && target.Boundary == BoundaryOwnership.Http
                        && node.Boundary is BoundaryOwnership.Hosting or BoundaryOwnership.Application or BoundaryOwnership.Protocol or BoundaryOwnership.Identity;
                    if (!allowed)
                    {
                        result.Add(new("ARCH-004", node.Id, owner, location, $"{node.Id} -> {type.FullName} ({owner})"));
                    }
                }
            }
        }
        return result;
    }
}
