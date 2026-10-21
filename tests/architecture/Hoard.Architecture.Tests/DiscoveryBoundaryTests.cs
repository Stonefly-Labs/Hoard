using System.Text.Json;

namespace Hoard.Architecture.Tests;

public sealed class DiscoveryBoundaryTests
{
    [Fact]
    public void Prepared_discovery_graphs_preserve_approved_and_forbidden_directions()
    {
        var path = Environment.GetEnvironmentVariable("HOARD_DISCOVERY_EVIDENCE");
        Assert.False(string.IsNullOrWhiteSpace(path), "Run validate-discovery.sh to prepare real package and boundary evidence.");
        using var document = JsonDocument.Parse(File.ReadAllText(path!));
        var graphs = document.RootElement.GetProperty("graphs").EnumerateArray().ToArray();
        string[] expected = ["platform", "Protocol.One", "Protocol.Two", "Metadata", "Artifact.One", "Artifact.Two", "Identity",
            "baseline", "custom", "old-provider", "lifecycle-consumer", "configuration-consumer", "registration",
            "application-consumer", "nonweb-consumer", "permitted-application", "forbidden-provider", "cross-slice"];
        Assert.Equal(expected.Order(), graphs.Select(graph => graph.GetProperty("scanId").GetString()!).Order());
        foreach (var graph in graphs)
        {
            var violations = ArchitectureInspection.Inspect(graph);
            switch (graph.GetProperty("scanId").GetString())
            {
                case "forbidden-provider": Assert.Contains(violations, violation => violation.RuleId == "ARCH-008"); break;
                case "cross-slice": Assert.Contains(violations, violation => violation.RuleId == "ARCH-007"); break;
                default: Assert.Empty(violations); break;
            }
        }
    }
}
