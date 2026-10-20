using System.Text.Json;
using System.Text.Json.Nodes;
using Hoard.Tests;

namespace Hoard.Architecture.Tests;

public class InspectionFailureTests
{
    [Theory]
    [InlineData("platform")]
    [InlineData("provider:Hoard.Fixtures.Protocol")]
    [InlineData("provider:Hoard.Fixtures.Metadata")]
    [InlineData("provider:Hoard.Fixtures.Artifact.One")]
    [InlineData("provider:Hoard.Fixtures.Artifact.Two")]
    [InlineData("provider:Hoard.Fixtures.Identity")]
    [InlineData("host:One")]
    [InlineData("host:Two")]
    public void Omitting_any_required_real_scan_is_an_error(string identity)
    {
        var graphs = JsonNode.Parse(FoundationEvidence.Load().GetProperty("realArchitecture").GetRawText())!.AsArray();
        graphs.Remove(graphs.Single(graph => graph!["scanId"]!.GetValue<string>() == identity));
        using var document = JsonDocument.Parse(graphs.ToJsonString());
        var error = Assert.Throws<InspectionException>(() => ArchitectureInspection.InspectRealGraphs(document.RootElement));
        Assert.Contains(identity, error.Message);
    }

    [Theory]
    [InlineData("assembly")]
    [InlineData("assets")]
    [InlineData("references")]
    [InlineData("ownership")]
    [InlineData("duplicate")]
    [InlineData("slices")]
    [InlineData("unresolved")]
    [InlineData("empty")]
    public void Incomplete_inputs_are_inspection_errors_not_clean_scans(string failure)
    {
        var graph = JsonNode.Parse(FoundationEvidence.Load().GetProperty("architecture").GetProperty("permitted").GetRawText())!;
        var projects = graph["projects"]!.AsArray();
        switch (failure)
        {
            case "assembly":
                projects[0]!["assembly"] = "/missing/foundation-input.dll";
                break;
            case "assets":
                projects[0]!["assets"] = "/missing/project.assets.json";
                break;
            case "references":
                projects[0]!["references"] = new JsonArray();
                break;
            case "ownership":
                graph["ownership"]!.AsObject().Remove("Metadata");
                break;
            case "duplicate":
                projects.Add(projects[0]!.DeepClone());
                break;
            case "slices":
                foreach (var project in projects)
                {
                    project!["sources"] = new JsonArray();
                }
                break;
            case "unresolved":
                projects[0]!["references"]![0]!["Identity"] = "/missing/System.Runtime.dll";
                break;
            case "empty":
                graph["projects"] = new JsonArray();
                break;
        }
        using var document = JsonDocument.Parse(graph.ToJsonString());
        var error = Assert.Throws<InspectionException>(() => ArchitectureInspection.Inspect(document.RootElement));
        Assert.StartsWith("INSPECTION:", error.Message);
    }
}
