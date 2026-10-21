using System.Text.Json;

namespace Hoard.Architecture.Tests;

public sealed class ConfigurationBoundaryTests
{
    [Theory]
    [InlineData("Metadata", "Hosting", "ARCH-008")]
    [InlineData("Artifact", "Hosting", "ARCH-008")]
    [InlineData("Core", "Metadata", "ARCH-002")]
    [InlineData("Abstractions", "Hosting", "ARCH-001")]
    [InlineData("Protocol", "Hosting", null)]
    public void Configuration_does_not_expand_provider_dependency_directions(string source, string target, string? expected) =>
        Assert.Equal(expected, DependencyGraphInspector.Rule(Enum.Parse<BoundaryOwnership>(source),
            Enum.Parse<BoundaryOwnership>(target), 2, false));

    [Fact]
    public void Prepared_configuration_graphs_are_complete_and_permitted()
    {
        var path = Environment.GetEnvironmentVariable("HOARD_CONFIGURATION_EVIDENCE");
        Assert.False(string.IsNullOrWhiteSpace(path), "Run validate-configuration.sh to prepare actual packed configuration graphs.");
        using var document = JsonDocument.Parse(File.ReadAllText(path!));
        var graphs = document.RootElement.GetProperty("graphs").EnumerateArray().ToArray();
        string[] expected = ["platform", "Protocol.One", "Protocol.Two", "Metadata", "Artifact.One", "Artifact.Two",
            "Identity", "configured-baseline", "configured-custom", "old-provider", "lifecycle-consumer", "registration", "conversion-process"];
        Assert.Equal(expected.Order(), graphs.Select(graph => graph.GetProperty("scanId").GetString()!).Order());
        foreach (var graph in graphs) { Assert.Empty(ArchitectureInspection.Inspect(graph)); }
    }
}
