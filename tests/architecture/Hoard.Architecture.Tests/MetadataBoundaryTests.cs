using System.Text.Json;
using System.Xml.Linq;

namespace Hoard.Architecture.Tests;

public sealed class MetadataBoundaryTests
{
    [Fact]
    public void Native_only_packages_cannot_hide_managed_assets()
    {
        using var capture = InspectionInput.BeginIfRequested($"{typeof(MetadataBoundaryTests).FullName}.{nameof(Native_only_packages_cannot_hide_managed_assets)}");
        using var native = JsonDocument.Parse("""{"runtimeTargets":{"native/sqlite.dll":{"assetType":"native"}}}""");
        using var managed = JsonDocument.Parse("""{"runtimeTargets":{"lib/hidden.dll":{"assetType":"runtime"}}}""");
        using var compile = JsonDocument.Parse("""{"compile":{"lib/hidden.dll":{}}}""");
        Assert.True(InspectionEvidence.HasNoManagedAssets(native.RootElement));
        Assert.False(InspectionEvidence.HasNoManagedAssets(managed.RootElement));
        Assert.False(InspectionEvidence.HasNoManagedAssets(compile.RootElement));
        capture?.Complete();
    }

    [Fact]
    public void Package_groups_follow_actual_resolved_assets_not_a_guessed_framework()
    {
        using var capture = InspectionInput.BeginIfRequested($"{typeof(MetadataBoundaryTests).FullName}.{nameof(Package_groups_follow_actual_resolved_assets_not_a_guessed_framework)}");
        var groups = XElement.Parse("""
            <dependencies><group targetFramework="net8.0"/><group targetFramework=".NETStandard2.0"/>
            <group targetFramework="net6.0"/></dependencies>
            """).Elements().ToArray();
        using var standard = JsonDocument.Parse("""{"compile":{"lib/netstandard2.0/sdk.dll":{}}}""");
        using var six = JsonDocument.Parse("""{"compile":{"lib/net6.0/sdk.dll":{}}}""");
        using var foreign = JsonDocument.Parse("""{"compile":{"lib/net9.0/sdk.dll":{}}}""");
        Assert.Same(groups[1], DependencyGraphInspector.SelectedGroup(groups, standard.RootElement));
        Assert.Same(groups[2], DependencyGraphInspector.SelectedGroup(groups, six.RootElement));
        Assert.Throws<InspectionException>(() => DependencyGraphInspector.SelectedGroup(groups, foreign.RootElement));
        capture?.Complete();
    }

    [Fact]
    public void Pruned_dependency_needs_sdk_evidence_a_compatible_version_and_an_actual_framework_reference()
    {
        using var capture = InspectionInput.BeginIfRequested($"{typeof(MetadataBoundaryTests).FullName}.{nameof(Pruned_dependency_needs_sdk_evidence_a_compatible_version_and_an_actual_framework_reference)}");
        using var framework = JsonDocument.Parse("""{"packagesToPrune":{"System.Memory":"(,4.5.32767]"}}""");
        var node = new InspectionNode("System.Memory", BoundaryOwnership.Bcl, "", "", true);
        var dependency = XElement.Parse("""<dependency id="System.Memory" version="4.5.3"/>""");
        Assert.True(DependencyGraphInspector.ProvenFrameworkPruning(dependency, framework.RootElement, node));
        Assert.False(DependencyGraphInspector.ProvenFrameworkPruning(dependency, framework.RootElement, node with { IsFramework = false }));
        Assert.False(DependencyGraphInspector.ProvenFrameworkPruning(dependency, framework.RootElement, node with { Boundary = BoundaryOwnership.Sdk }));
        dependency.SetAttributeValue("version", "9.0.0");
        Assert.False(DependencyGraphInspector.ProvenFrameworkPruning(dependency, framework.RootElement, node));
        capture?.Complete();
    }

    [Fact]
    public void Prepared_metadata_packages_and_negative_contracts_preserve_boundaries_and_binary_surface()
    {
        using var capture = InspectionInput.BeginIfRequested($"{typeof(MetadataBoundaryTests).FullName}.{nameof(Prepared_metadata_packages_and_negative_contracts_preserve_boundaries_and_binary_surface)}");
        var path = Environment.GetEnvironmentVariable("HOARD_METADATA_BOUNDARIES");
        Assert.False(string.IsNullOrWhiteSpace(path), "Run validate-metadata.sh to prepare the actual metadata package graph.");
        using var document = JsonDocument.Parse(InspectionInput.ReadAllText(path!));
        var graphs = document.RootElement.GetProperty("graphs").EnumerateArray().ToArray();
        Assert.Equal(new[] { "platform", "sqlite", "memory", "host-adapters", "consumer", "crash-runner", "boundary-leak" }.Order(),
            graphs.Select(graph => graph.GetProperty("scanId").GetString()!).Order());
        foreach (var graph in graphs)
        {
            var violations = ArchitectureInspection.Inspect(graph);
            if (graph.GetProperty("scanId").GetString() == "boundary-leak")
            {
                Assert.Contains(violations, violation => violation.RuleId == "ARCH-004" && violation.Location.Contains("Driver", StringComparison.Ordinal));
                Assert.Contains(violations, violation => violation.RuleId == "ARCH-004" && violation.Path.Contains("IQueryable", StringComparison.Ordinal));
                Assert.Contains(violations, violation => violation.RuleId == "ARCH-004" && violation.Path.Contains("DbTransaction", StringComparison.Ordinal));
            }
            else { Assert.Empty(violations); }
        }
        using var oldAssembly = InspectionInput.ReadAssembly(document.RootElement.GetProperty("baselineAbstractions").GetString()!);
        using var currentAssembly = InspectionInput.ReadAssembly(document.RootElement.GetProperty("currentAbstractions").GetString()!);
        var actualTypes = PublicSurfaceInspector.Types(currentAssembly.MainModule).ToDictionary(type => type.FullName);
        foreach (var old in PublicSurfaceInspector.Types(oldAssembly.MainModule).Where(type => type.IsPublic || type.IsNestedPublic))
        {
            Assert.True(actualTypes.TryGetValue(old.FullName, out var current));
            Assert.Equal(old.BaseType?.FullName, current!.BaseType?.FullName);
            foreach (var method in old.Methods.Where(method => method.IsPublic || method.IsFamily))
            { Assert.Contains(current.Methods, candidate => candidate.FullName == method.FullName); }
            foreach (var property in old.Properties)
            { Assert.Contains(current.Properties, candidate => candidate.FullName == property.FullName); }
        }
        Assert.Empty(actualTypes["Hoard.Abstractions.Providers.IMetadataProvider"].Methods);
        capture?.Complete();
    }
}
