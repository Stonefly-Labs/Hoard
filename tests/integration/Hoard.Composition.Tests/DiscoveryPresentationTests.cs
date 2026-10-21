using System.Text;
using System.Text.Json.Nodes;
using Hoard.Discovery.ReferenceConsumer;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.TestHost;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryPresentationTests
{
    internal static async Task<byte[]> Body()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var (app, lease) = await DiscoveryAuthorizationTests.HttpFixture();
        await using (lease)
        {
            await app.StartAsync();
            using var client = app.GetTestClient();
            client.DefaultRequestHeaders.Add("X-Fixture-Identity", "read");
            return await client.GetByteArrayAsync("/api/v1/discovery");
        }
    }
    internal static JsonObject Protocol(JsonNode root) =>
        root["modules"]!.AsArray().Single(module => module!["id"]!.GetValue<string>() == "protocol")!.AsObject();
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
}
