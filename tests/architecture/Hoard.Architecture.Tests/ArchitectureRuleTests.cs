using Hoard.Tests;

namespace Hoard.Architecture.Tests;

public class ArchitectureRuleTests
{
    [Theory]
    [InlineData("abstractions-sdk", "ARCH-001")]
    [InlineData("abstractions-http", "ARCH-001")]
    [InlineData("abstractions-unused-http", "ARCH-001")]
    [InlineData("core-unused-http", "ARCH-002")]
    [InlineData("core-unused", "ARCH-002")]
    [InlineData("core-transitive", "ARCH-003")]
    [InlineData("core-packed", "ARCH-003")]
    [InlineData("leak-direct", "ARCH-004")]
    [InlineData("leak-recursive", "ARCH-004")]
    [InlineData("bcl-query", "ARCH-004")]
    [InlineData("bcl-nested-query", "ARCH-004")]
    [InlineData("bcl-connection", "ARCH-004")]
    [InlineData("provider-unrelated", "ARCH-005")]
    [InlineData("provider-same-family", "ARCH-005")]
    [InlineData("slice-private", "ARCH-008")]
    [InlineData("slice-same-assembly", "ARCH-007")]
    [InlineData("slice-async", "ARCH-007")]
    [InlineData("slice-external", "ARCH-007")]
    public void Isolated_forbidden_input_is_rejected_by_its_intended_rule(string name, string rule)
    {
        var cases = FoundationEvidence.Load().GetProperty("architecture");
        var violations = ArchitectureInspection.Inspect(cases.GetProperty(name));
        var matches = violations.Where(v => v.RuleId == rule).ToArray();
        Assert.NotEmpty(matches);
        Assert.All(matches, violation =>
        {
            Assert.NotEmpty(violation.Source);
            Assert.NotEmpty(violation.Target);
            Assert.NotEmpty(violation.Location);
            Assert.NotEmpty(violation.Path);
        });
        if (rule == "ARCH-003")
        {
            Assert.Contains(matches, v => v.Path.Split(" -> ").Length >= 3);
        }
        if (name == "leak-recursive")
        {
            Assert.Contains(matches, v => v.Location.Contains("Models", StringComparison.Ordinal));
            Assert.Contains(matches, v => v.Path.Contains("IPrivateConstraint", StringComparison.Ordinal));
            Assert.Contains(matches, v => v.Path.Contains("PrivateAttribute", StringComparison.Ordinal));
            Assert.Contains(matches, v => v.Location.Contains("Changed", StringComparison.Ordinal));
        }
        if (name == "bcl-nested-query")
        {
            Assert.Contains(matches, v => v.Location.Contains("Queries", StringComparison.Ordinal));
        }
        if (name == "bcl-connection")
        {
            Assert.Contains(matches, v => v.Path.Contains("DbConnection", StringComparison.Ordinal));
            Assert.Contains(matches, v => v.Path.Contains("DbTransaction", StringComparison.Ordinal));
        }
        Assert.Empty(ArchitectureInspection.Inspect(cases.GetProperty("permitted")));
    }

    [Fact]
    public void Actual_platform_provider_packages_and_both_hosts_are_permitted()
    {
        Assert.Empty(ArchitectureInspection.InspectRealGraphs(FoundationEvidence.Load().GetProperty("realArchitecture")));
    }

    [Fact]
    public void Both_project_and_package_cycles_are_rejected()
    {
        var cycles = FoundationEvidence.Load().GetProperty("cycles");
        foreach (var name in new[] { "project", "package" })
        {
            var graph = cycles.GetProperty(name).EnumerateArray().Select(e =>
                new DependencyEdge(e[0].GetString()!, e[1].GetString()!, name, "graph.json")).ToArray();
            Assert.Contains(DependencyGraphInspector.Cycles(graph), v => v.RuleId == "ARCH-006");
            Assert.Empty(DependencyGraphInspector.Cycles(graph.Take(1).ToArray()));
        }
    }
}
