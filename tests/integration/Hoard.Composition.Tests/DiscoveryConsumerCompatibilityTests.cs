using System.Text.Json.Nodes;
using Hoard.Discovery.ReferenceConsumer;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryConsumerCompatibilityTests
{
    [Theory]
    [InlineData("schema")]
    [InlineData("missing")]
    [InlineData("duplicate-module")]
    [InlineData("duplicate-contribution")]
    [InlineData("unsafe")]
    [InlineData("type")]
    public async Task Incompatible_required_shapes_are_explicit_failures_not_empty_success(string defect)
    {
        var root = JsonNode.Parse(await DiscoveryPresentationTests.Body())!;
        var protocol = DiscoveryPresentationTests.Protocol(root);
        if (defect == "schema") { root["schemaVersion"] = 2; }
        if (defect == "missing") { protocol.Remove("compatibility"); }
        if (defect == "duplicate-module") { root["modules"]!.AsArray().Add(protocol.DeepClone()); }
        if (defect == "duplicate-contribution") { protocol["capabilities"]!.AsArray().Add(protocol["capabilities"]![0]!.DeepClone()); }
        if (defect == "unsafe") { protocol["id"] = "<unsafe>"; }
        if (defect == "type") { protocol["enabled"] = "yes"; }
        var result = DiscoveryJsonReader.Read(DiscoveryPresentationTests.Bytes(root));
        Assert.False(result.Compatible);
        Assert.Null(result.Observation);
        Assert.Equal("incompatible-discovery-response", result.Code);
    }

    [Fact]
    public async Task Additive_descriptions_are_ignored_and_unknown_operations_never_become_actions()
    {
        var root = JsonNode.Parse(await DiscoveryPresentationTests.Body())!;
        root["future-description"] = new JsonObject { ["unsafe-markup"] = "<script>inert</script>" };
        Assert.True(DiscoveryJsonReader.Read(DiscoveryPresentationTests.Bytes(root)).Compatible);
        DiscoveryPresentationTests.Protocol(root)["capabilities"]![0]!["operationId"] = "future-operation";
        var result = DiscoveryJsonReader.Read(DiscoveryPresentationTests.Bytes(root));
        Assert.True(result.Compatible);
        Assert.True(PresentationProjector.Project(result.Observation!, true, new HashSet<string> { "future-operation" })
            .Single(module => module.Id == "protocol").Actions.Single().Hidden);
    }

    [Theory]
    [InlineData("future-capability", "0.1.0")]
    [InlineData("inspect", "2.0.0")]
    public async Task A_known_operation_name_does_not_authorize_unknown_capability_semantics(string id, string version)
    {
        var root = JsonNode.Parse(await DiscoveryPresentationTests.Body())!;
        var capability = DiscoveryPresentationTests.Protocol(root)["capabilities"]![0]!;
        capability["id"] = id;
        capability["version"] = version;
        var parsed = DiscoveryJsonReader.Read(DiscoveryPresentationTests.Bytes(root));
        Assert.True(parsed.Compatible);
        var action = PresentationProjector.Project(parsed.Observation!, true, new HashSet<string> { "inspect" })
            .Single(module => module.Id == "protocol").Actions.Single();
        Assert.True(action.Hidden);
        Assert.False(action.Enabled);
    }

    [Theory]
    [InlineData("root")]
    [InlineData("module")]
    [InlineData("capability")]
    public async Task Omitted_unknown_reasons_cannot_leave_an_action_enabled(string scope)
    {
        var root = JsonNode.Parse(await DiscoveryPresentationTests.Body())!;
        var protocol = DiscoveryPresentationTests.Protocol(root);
        var owner = scope == "root" ? root : scope == "module" ? protocol : protocol["capabilities"]![0]!;
        owner["omittedReasonCount"] = 1;
        var parsed = DiscoveryJsonReader.Read(DiscoveryPresentationTests.Bytes(root));
        Assert.True(parsed.Compatible);
        Assert.False(PresentationProjector.Project(parsed.Observation!, true, new HashSet<string> { "inspect" })
            .Single(module => module.Id == "protocol").Actions.Single().Enabled);
    }

    [Theory]
    [InlineData("protocol", "unknown")]
    [InlineData("protocol", "future-phase")]
    [InlineData("metadata", "unknown")]
    [InlineData("metadata", "future-phase")]
    public async Task Unknown_owner_or_dependency_phases_preserve_inventory_but_never_enable_actions(string moduleId, string phase)
    {
        var root = JsonNode.Parse(await DiscoveryPresentationTests.Body())!;
        DiscoveryPresentationTests.Protocol(root)["capabilities"]![0]!["dependencies"] = new JsonArray("metadata");
        var current = DiscoveryJsonReader.Read(DiscoveryPresentationTests.Bytes(root));
        Assert.True(current.Compatible);
        Assert.Equal("assessing-readiness", DiscoveryPresentationTests.Module(root, moduleId)["lifecyclePhase"]!.GetValue<string>());
        Assert.True(PresentationProjector.Project(current.Observation!, true, new HashSet<string> { "inspect" })
            .Single(module => module.Id == "protocol").Actions.Single().Enabled);

        DiscoveryPresentationTests.Module(root, moduleId)["lifecyclePhase"] = phase;
        var changed = DiscoveryJsonReader.Read(DiscoveryPresentationTests.Bytes(root));
        Assert.True(changed.Compatible);
        Assert.Equal(current.Observation!.Modules.Select(module => module.Id), changed.Observation!.Modules.Select(module => module.Id));
        Assert.Equal("ready", changed.Observation.Modules.Single(module => module.Id == moduleId).Readiness);
        Assert.Equal("usable", changed.Observation.Modules.Single(module => module.Id == "protocol").Capabilities.Single().Availability);
        Assert.False(PresentationProjector.Project(changed.Observation, true, new HashSet<string> { "inspect" })
            .Single(module => module.Id == "protocol").Actions.Single().Enabled);
    }
}
