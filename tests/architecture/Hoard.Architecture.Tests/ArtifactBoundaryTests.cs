using System.Text.Json;
using Mono.Cecil;

namespace Hoard.Architecture.Tests;

public sealed class ArtifactBoundaryTests
{
    [Fact]
    public void Prepared_artifact_packages_preserve_independence_and_existing_public_members()
    {
        using var capture = InspectionInput.BeginIfRequested($"{typeof(ArtifactBoundaryTests).FullName}.{nameof(Prepared_artifact_packages_preserve_independence_and_existing_public_members)}");
        var path = Environment.GetEnvironmentVariable("HOARD_ARTIFACT_BOUNDARIES");
        Assert.False(string.IsNullOrWhiteSpace(path), "Run validate-artifacts.sh --phase packages to prepare actual artifact package graphs.");
        using var document = JsonDocument.Parse(InspectionInput.ReadAllText(path!));
        var graphs = document.RootElement.GetProperty("graphs").EnumerateArray().ToArray();
        Assert.Equal(new[] { "platform", "local", "object", "host-adapters", "consumer", "crash-runner", "transfer-runner", "boundary-leak" }.Order(),
            graphs.Select(graph => graph.GetProperty("scanId").GetString()!).Order());
        foreach (var graph in graphs)
        {
            var violations = ArchitectureInspection.Inspect(graph);
            if (graph.GetProperty("scanId").GetString() == "boundary-leak")
            {
                Assert.Contains(violations, violation => violation.RuleId == "ARCH-004" && violation.Location.Contains("Provider", StringComparison.Ordinal));
                Assert.Contains(violations, violation => violation.RuleId == "ARCH-004" && violation.Location.Contains("Hosting", StringComparison.Ordinal));
                foreach (var member in new[] { "Sdk", "RawPath", "RawFile", "ServiceLocator" })
                {
                    Assert.Contains(violations, violation => violation.RuleId == "ARCH-004"
                        && violation.Location.Contains($"::{member}", StringComparison.Ordinal));
                }
                Assert.DoesNotContain(violations, violation =>
                    violation.Location.Contains("AllowedArtifactContract", StringComparison.Ordinal));
            }
            else { Assert.Empty(violations); }
        }
        using var baseline = InspectionInput.ReadAssembly(document.RootElement.GetProperty("baselineAbstractions").GetString()!);
        using var current = InspectionInput.ReadAssembly(document.RootElement.GetProperty("currentAbstractions").GetString()!);
        var types = PublicSurfaceInspector.Types(current.MainModule).ToDictionary(type => type.FullName);
        foreach (var old in PublicSurfaceInspector.Types(baseline.MainModule).Where(type => type.IsPublic || type.IsNestedPublic))
        {
            Assert.True(types.TryGetValue(old.FullName, out var actual));
            Assert.Equal(old.BaseType?.FullName, actual!.BaseType?.FullName);
            Assert.Equal(old.Attributes, actual.Attributes);
            foreach (var method in old.Methods.Where(method => method.IsPublic || method.IsFamily))
            { AssertMethodPreserved(method, actual); }
            foreach (var property in old.Properties)
            { Assert.Contains(actual.Properties, candidate => candidate.FullName == property.FullName); }
            foreach (var field in old.Fields.Where(field => field.IsPublic || field.IsFamily))
            { Assert.Contains(actual.Fields, candidate => candidate.FullName == field.FullName && candidate.Attributes == field.Attributes); }
            foreach (var contract in old.Interfaces)
            { Assert.Contains(actual.Interfaces, candidate => candidate.InterfaceType.FullName == contract.InterfaceType.FullName); }
        }
        Assert.Empty(types["Hoard.Abstractions.Providers.IArtifactProvider"].Methods);
        capture?.Complete();
    }

    [Fact]
    public void Prepared_artifact_consumer_bodies_are_provider_neutral_and_object_mechanisms_do_not_rename()
    {
        using var capture = InspectionInput.BeginIfRequested($"{typeof(ArtifactBoundaryTests).FullName}.{nameof(Prepared_artifact_consumer_bodies_are_provider_neutral_and_object_mechanisms_do_not_rename)}");
        var path = Environment.GetEnvironmentVariable("HOARD_ARTIFACT_BOUNDARIES");
        Assert.False(string.IsNullOrWhiteSpace(path), "Prepare actual artifact package graphs first.");
        using var document = JsonDocument.Parse(InspectionInput.ReadAllText(path!));
        var graphs = document.RootElement.GetProperty("graphs").EnumerateArray()
            .ToDictionary(graph => graph.GetProperty("scanId").GetString()!);
        using var consumer = InspectionEvidence.Load(graphs["consumer"]);
        Assert.Empty(ConsumerCouplings(consumer, "Consumer", "Hoard.Fixtures.Artifacts.Consumer.ArtifactConsumer"));
        using var negative = InspectionEvidence.Load(graphs["boundary-leak"]);
        Assert.Contains(ConsumerCouplings(negative, "BoundaryLeak",
            "Hoard.Fixtures.Artifacts.BoundaryLeak.HiddenProviderConsumer"),
            type => type.Contains("LocalArtifactStore", StringComparison.Ordinal));
        DependencyGraphInspector.Read(negative);
        negative.Nodes["BoundaryLeak"] = negative.Nodes["BoundaryLeak"] with { Boundary = BoundaryOwnership.Core };
        Assert.Contains(DependencyGraphInspector.Inspect(negative),
            violation => violation.RuleId == "ARCH-002" && violation.Source == "BoundaryLeak"
                && violation.Target == "Hoard.Fixtures.Artifacts.Local");

        using var local = InspectionEvidence.Load(graphs["local"]);
        using var objects = InspectionEvidence.Load(graphs["object"]);
        Assert.NotEmpty(RenameCalls(local.Assemblies["Local"]));
        Assert.Empty(RenameCalls(objects.Assemblies["ObjectSemantics"]));
        Assert.DoesNotContain(objects.Assemblies["ObjectSemantics"].MainModule.AssemblyReferences,
            reference => reference.Name == "Hoard.Fixtures.Artifacts.Local");
        capture?.Complete();
    }

    private static string[] ConsumerCouplings(InspectionEvidence evidence, string assembly, string root)
    {
        var types = PublicSurfaceInspector.Types(evidence.Assemblies[assembly].MainModule)
            .Where(type => type.FullName == root || type.FullName.StartsWith(root + "/", StringComparison.Ordinal)).ToArray();
        Assert.NotEmpty(types);
        return types.SelectMany(type => PublicSurfaceInspector.Expand(type.BaseType)
            .Concat(type.Interfaces.SelectMany(contract => PublicSurfaceInspector.Expand(contract.InterfaceType)))
            .Concat(type.Fields.SelectMany(field => PublicSurfaceInspector.Expand(field.FieldType)))
            .Concat(type.Methods.SelectMany(method => PublicSurfaceInspector.Signature(method)
                .Concat(method.HasBody
                    ? method.Body.Variables.SelectMany(variable => PublicSurfaceInspector.Expand(variable.VariableType))
                        .Concat(method.Body.ExceptionHandlers.SelectMany(handler => PublicSurfaceInspector.Expand(handler.CatchType)))
                        .Concat(method.Body.Instructions.SelectMany(instruction => PublicSurfaceInspector.Operand(instruction.Operand)))
                    : []))))
            .Where(type => evidence.Owner(type) != assembly
                && evidence.Nodes[evidence.Owner(type)].Boundary is not (BoundaryOwnership.Bcl or BoundaryOwnership.Abstractions))
            .Select(type => type.FullName).Distinct().ToArray();
    }

    private static MethodReference[] RenameCalls(AssemblyDefinition assembly)
        => PublicSurfaceInspector.Types(assembly.MainModule).SelectMany(type => type.Methods)
            .Where(method => method.HasBody).SelectMany(method => method.Body.Instructions)
            .Select(instruction => instruction.Operand).OfType<MethodReference>()
            .Where(method => method.DeclaringType.FullName is "System.IO.File" or "System.IO.Directory"
                && method.Name is "Move" or "Replace"
                || method.DeclaringType.FullName is "System.IO.FileInfo" or "System.IO.DirectoryInfo"
                && method.Name is "MoveTo" or "Replace").ToArray();

    [Fact]
    public void Identical_member_names_do_not_hide_accessibility_or_invocation_breaks()
    {
        using var module = ModuleDefinition.CreateModule("CompatibilityNegative", ModuleKind.Dll);
        var baseline = new TypeDefinition("Fixture", "Contract", TypeAttributes.Public, module.TypeSystem.Object);
        var current = new TypeDefinition("Fixture", "Contract", TypeAttributes.Public, module.TypeSystem.Object);
        var original = new MethodDefinition("Invoke", MethodAttributes.Public, module.TypeSystem.Void);
        baseline.Methods.Add(original);
        var replacement = new MethodDefinition("Invoke", MethodAttributes.Public, module.TypeSystem.Void);
        current.Methods.Add(replacement);
        AssertMethodPreserved(original, current);
        replacement.Attributes = MethodAttributes.Private;
        Assert.ThrowsAny<Xunit.Sdk.XunitException>(() => AssertMethodPreserved(original, current));
        replacement.Attributes = MethodAttributes.Public | MethodAttributes.Static;
        Assert.ThrowsAny<Xunit.Sdk.XunitException>(() => AssertMethodPreserved(original, current));
    }

    private static void AssertMethodPreserved(MethodDefinition original, TypeDefinition current)
        => Assert.Contains(current.Methods, candidate => candidate.FullName == original.FullName
            && candidate.Attributes == original.Attributes
            && candidate.ImplAttributes == original.ImplAttributes);
}
