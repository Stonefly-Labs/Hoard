using System.Text.Json;

namespace Hoard.Architecture.Tests;

public class LifecycleBoundaryTests
{
    [Fact]
    public void Framework_roll_forward_is_not_a_package_identity_bypass()
    {
        var requested = Mono.Cecil.AssemblyNameReference.Parse("System.Runtime, Version=8.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a");
        var resolved = Mono.Cecil.AssemblyNameReference.Parse("System.Runtime, Version=10.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a");
        var framework = new InspectionNode("System.Runtime", BoundaryOwnership.Bcl, "", resolved.FullName, true);
        var externalHttp = new InspectionNode("External.Http", BoundaryOwnership.Http, "", resolved.FullName);
        Assert.True(DependencyGraphInspector.FrameworkCompatible(framework, requested, resolved));
        Assert.False(DependencyGraphInspector.FrameworkCompatible(externalHttp, requested, resolved));
        Assert.False(DependencyGraphInspector.FrameworkCompatible(framework, resolved, requested));
        requested.PublicKeyToken = [];
        Assert.False(DependencyGraphInspector.FrameworkCompatible(framework, requested, resolved));
    }

    [Theory]
    [InlineData("Hosting", "Http", false, null)]
    [InlineData("Hosting", "Versioning", false, null)]
    [InlineData("Metadata", "Http", false, "ARCH-008")]
    [InlineData("Artifact", "Hosting", false, "ARCH-008")]
    [InlineData("Core", "Versioning", false, "ARCH-002")]
    [InlineData("Protocol", "Versioning", false, "ARCH-008")]
    [InlineData("Protocol", "Versioning", true, null)]
    public void Only_approved_lifecycle_directions_are_permitted(
        string source, string target, bool viaHosting, string? rule) =>
        Assert.Equal(rule, DependencyGraphInspector.Rule(Enum.Parse<BoundaryOwnership>(source),
            Enum.Parse<BoundaryOwnership>(target), viaHosting ? 3 : 2, viaHosting));

    [Fact]
    public void Prepared_lifecycle_graphs_are_complete_and_permitted()
    {
        var path = Environment.GetEnvironmentVariable("HOARD_LIFECYCLE_EVIDENCE");
        Assert.False(string.IsNullOrWhiteSpace(path), "Run validate-lifecycle.sh to prepare LC-38 inputs.");
        using var document = JsonDocument.Parse(File.ReadAllText(path!));
        var graphs = document.RootElement.GetProperty("graphs").EnumerateArray().ToArray();
        string[] required = ["platform", "Protocol.One", "Protocol.Two", "Metadata", "Artifact.One", "Artifact.Two",
            "Identity", "baseline", "custom", "registration"];
        Assert.Equal(required.Order().ToArray(), graphs.Select(graph => graph.GetProperty("scanId").GetString()!).Order().ToArray());
        foreach (var graph in graphs) { Assert.Empty(ArchitectureInspection.Inspect(graph)); }
    }
}
