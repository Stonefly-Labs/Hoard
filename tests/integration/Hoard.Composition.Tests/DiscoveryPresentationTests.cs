using System.Text;
using System.Text.Json.Nodes;
using Hoard.Discovery.ReferenceConsumer;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.TestHost;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryPresentationTests
{
    internal static async Task<byte[]> Body(HoardDiscoveryCatalog? catalog = null)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var (app, lease) = await DiscoveryAuthorizationTests.HttpFixture(catalog);
        await using (lease)
        {
            await app.StartAsync();
            using var client = app.GetTestClient();
            client.DefaultRequestHeaders.Add("X-Fixture-Identity", "read");
            return await client.GetByteArrayAsync("/api/v1/discovery");
        }
    }
    internal static JsonObject Module(JsonNode root, string id) =>
        root["modules"]!.AsArray().Single(module => module!["id"]!.GetValue<string>() == id)!.AsObject();
    internal static JsonObject Protocol(JsonNode root) => Module(root, "protocol");
    internal static byte[] Bytes(JsonNode root) => Encoding.UTF8.GetBytes(root.ToJsonString());

    [Theory]
    [InlineData("disabled")]
    [InlineData("initializing")]
    [InlineData("not-ready")]
    [InlineData("stopping")]
    [InlineData("stopped")]
    [InlineData("future-state")]
    public async Task Distinct_textual_states_and_safe_actions_are_projected_from_actual_JSON(string readiness)
    {
        var root = JsonNode.Parse(await Body())!;
        var protocol = Protocol(root);
        protocol["readiness"] = readiness;
        if (readiness == "disabled") { protocol["enabled"] = false; }
        var result = DiscoveryJsonReader.Read(Bytes(root));
        Assert.True(result.Compatible);
        var view = PresentationProjector.Project(result.Observation!, true, new HashSet<string> { "inspect" })
            .Single(module => module.Id == "protocol");
        Assert.False(Assert.Single(view.Actions).Enabled);
        Assert.Contains(view.ReadingOrder, line => line.Text == (readiness == "future-state" ? "Unknown/uninterpretable" : readiness));
        Assert.Equal(Enumerable.Range(1, view.ReadingOrder.Length), view.ReadingOrder.Select(line => line.Order));
        Assert.All(view.ReadingOrder, line => Assert.StartsWith("protocol:", line.Label));
        Assert.Contains(view.ReadingOrder, line => line.Text == PresentationText.Fixture);
    }

    [Fact]
    public async Task Unsupported_actions_hide_and_usable_operations_still_require_separate_permission()
    {
        var body = await Body();
        var parsed = DiscoveryJsonReader.Read(body);
        Assert.True(parsed.Compatible);
        var observation = parsed.Observation!;
        Assert.False(PresentationProjector.Project(observation, true, new HashSet<string>())
            .Single(module => module.Id == "protocol").Actions.Single().Enabled);
        Assert.True(PresentationProjector.Project(observation, true, new HashSet<string> { "inspect" })
            .Single(module => module.Id == "protocol").Actions.Single().Enabled);
        Assert.False(PresentationProjector.Project(observation, false, new HashSet<string> { "inspect" })
            .Single(module => module.Id == "protocol").Actions.Single().Enabled);
        Assert.Contains("Not included", PresentationProjector.Lookup(observation, "absent"), StringComparison.Ordinal);
        Assert.Contains("Inclusion unknown", PresentationProjector.Lookup(observation with { Completeness = "partial" }, "absent"), StringComparison.Ordinal);
        foreach (var support in new[] { "unsupported", "unverified" })
        {
            var root = JsonNode.Parse(body)!;
            Protocol(root)["capabilities"]![0]!["support"] = support;
            var changed = DiscoveryJsonReader.Read(Bytes(root));
            Assert.True(PresentationProjector.Project(changed.Observation!, true, new HashSet<string> { "inspect" })
                .Single(module => module.Id == "protocol").Actions.Single().Hidden);
        }
    }

    [Theory]
    [InlineData("protocol", "stopping")]
    [InlineData("protocol", "draining")]
    [InlineData("protocol", "cleaning-up")]
    [InlineData("protocol", "stopped")]
    [InlineData("metadata", "stopping")]
    [InlineData("metadata", "draining")]
    [InlineData("metadata", "cleaning-up")]
    [InlineData("metadata", "stopped")]
    public async Task Terminal_owner_or_dependency_phases_override_ready_usable_action_claims(string moduleId, string phase)
    {
        var root = JsonNode.Parse(await Body())!;
        Protocol(root)["capabilities"]![0]!["dependencies"] = new JsonArray("metadata");
        var current = DiscoveryJsonReader.Read(Bytes(root));
        Assert.True(current.Compatible);
        Assert.Equal("assessing-readiness", Module(root, moduleId)["lifecyclePhase"]!.GetValue<string>());
        Assert.True(PresentationProjector.Project(current.Observation!, true, new HashSet<string> { "inspect" })
            .Single(module => module.Id == "protocol").Actions.Single().Enabled);

        Module(root, moduleId)["lifecyclePhase"] = phase;
        var changed = DiscoveryJsonReader.Read(Bytes(root));
        Assert.True(changed.Compatible);
        Assert.Equal("ready", changed.Observation!.Modules.Single(module => module.Id == moduleId).Readiness);
        Assert.Equal("usable", changed.Observation.Modules.Single(module => module.Id == "protocol").Capabilities.Single().Availability);
        var views = PresentationProjector.Project(changed.Observation, true, new HashSet<string> { "inspect" });
        var action = views.Single(module => module.Id == "protocol").Actions.Single();
        Assert.False(action.Hidden);
        Assert.False(action.Enabled);
        Assert.False(string.IsNullOrWhiteSpace(action.Explanation));
        Assert.Contains(views.Single(module => module.Id == moduleId).ReadingOrder,
            line => line.Label == $"{moduleId}: authority phase" && line.Text == phase);
    }

    [Theory]
    [InlineData("supported")]
    [InlineData("unsupported")]
    [InlineData("unverified")]
    public async Task Support_state_and_fixture_scope_have_separate_contextual_semantic_lines(string support)
    {
        var catalog = DiscoveryFixtures.Catalog(support);
        catalog = catalog with
        {
            Contributions = [catalog.Contributions[0] with { EvidenceScope = "fixture", EvidenceIds = ["fixture-inspect"] }]
        };
        var parsed = DiscoveryJsonReader.Read(await Body(catalog));
        Assert.True(parsed.Compatible);
        var capability = parsed.Observation!.Modules.Single(module => module.Id == "protocol").Capabilities.Single();
        Assert.Equal(support, capability.Support);
        Assert.Equal("fixture", capability.EvidenceScope);
        var view = PresentationProjector.Project(parsed.Observation, true, new HashSet<string> { "inspect" })
            .Single(module => module.Id == "protocol");
        var state = Assert.Single(view.ReadingOrder, line => line.Label == "protocol: inspect support");
        Assert.Equal(support, state.Text);
        var scope = Assert.Single(view.ReadingOrder, line => line.Label == "protocol: inspect evidence scope");
        Assert.Equal(PresentationText.Fixture, scope.Text);
        var availability = Assert.Single(view.ReadingOrder, line => line.Label == "protocol: inspect availability");
        Assert.True(state.Order < scope.Order && scope.Order < availability.Order);
        Assert.Equal(Enumerable.Range(1, view.ReadingOrder.Length), view.ReadingOrder.Select(line => line.Order));
        Assert.All(view.ReadingOrder, line => Assert.StartsWith("protocol:", line.Label));
        var action = Assert.Single(view.Actions);
        Assert.Equal(support != "supported", action.Hidden);
        Assert.Equal(support == "supported", action.Enabled);
        if (support != "supported")
        {
            var reason = Assert.Single(capability.Reasons, reason => reason.Code == support);
            var guidance = Assert.Single(view.ReadingOrder, line => line.Label == $"protocol: inspect: {support}");
            Assert.Equal(reason.CorrectiveAction, guidance.Text);
            Assert.False(string.IsNullOrWhiteSpace(guidance.Text));
            Assert.True(availability.Order < guidance.Order);
        }
    }
}
