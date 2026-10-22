using System.Text.Json;
using Mono.Cecil;

namespace Hoard.Architecture.Tests;

public sealed class ArtifactBoundaryTests
{
    [Fact]
    public void Prepared_artifact_packages_preserve_independence_and_existing_public_members()
    {
        var path = Environment.GetEnvironmentVariable("HOARD_ARTIFACT_BOUNDARIES");
        Assert.False(string.IsNullOrWhiteSpace(path), "Run validate-artifacts.sh --phase packages to prepare actual artifact package graphs.");
        using var document = JsonDocument.Parse(File.ReadAllText(path!));
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
            }
            else { Assert.Empty(violations); }
        }
        using var baseline = AssemblyDefinition.ReadAssembly(document.RootElement.GetProperty("baselineAbstractions").GetString()!);
        using var current = AssemblyDefinition.ReadAssembly(document.RootElement.GetProperty("currentAbstractions").GetString()!);
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
    }

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
