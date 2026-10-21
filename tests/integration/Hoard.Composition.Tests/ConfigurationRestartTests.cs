using System.Net;
using System.Text.Json.Nodes;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.TestHost;

namespace Hoard.Composition.Tests;

public sealed class ConfigurationRestartTests
{
    [Fact]
    public async Task Running_TestServer_keeps_fixed_inputs_and_fresh_restart_rereads_explicit_sources()
    {
        ConfiguredFixtures.Reset();
        await using var harness = new ConfigurationTestHarness();
        var target = harness.File("credential", "original\n");
        var file = harness.File("configuration.json", ConfigurationSecretTests.Document("file", target));
        var environment = new Dictionary<string, string> { ["HOARD_CONFIG"] = """{"modules":{"metadata":{"options":{"count":4}}}}""" };
        for (var run = 0; run < 2; run++)
        {
            var web = LifecycleFixtures.WebBuilder();
            var builder = ConfiguredFixtures.Registry(services: web.Services);
            await using var evaluated = await builder.EvaluateConfigurationAsync(new(ConfiguredFixtures.Defaults,
                explicitFile: file, environment: environment), LifecycleFixtures.Versions, new());
            Assert.Equal(HoardConfigurationOutcome.Validated, evaluated.Outcome);
            await using var lease = await builder.ComposeHoardModulesAsync(evaluated.Configuration!);
            var app = await web.BuildHoardApplicationAsync(lease);
            await app.MapHoardModulesAsync(lease);
            await app.StartAsync();
            Assert.True(lease.Lifecycle.Snapshot.Ready);
            using var client = app.GetTestClient();
            using var response = await client.GetAsync("/not-a-product-endpoint");
            Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
            var fixedOptions = ConfiguredFixtures.Delivered!;
            Assert.Equal(run == 0 ? "first" : "second", fixedOptions.GetString("label"));
            Assert.Equal(run == 0 ? "original" : "replacement", fixedOptions.GetSecret("credential").Reveal());
            Assert.Equal(run == 0 ? 4 : 5, fixedOptions.GetInteger("count"));
            if (run == 0)
            {
                var replacement = JsonNode.Parse(ConfigurationSecretTests.Document("file", target))!;
                replacement["modules"]!["metadata"]!["options"]!["label"] = "second";
                File.WriteAllText(file, replacement.ToJsonString());
                File.WriteAllText(target, "replacement");
                environment["HOARD_CONFIG"] = """{"modules":{"metadata":{"options":{"count":5}}}}""";
                Assert.Equal("first", fixedOptions.GetString("label"));
                Assert.Equal("original", fixedOptions.GetSecret("credential").Reveal());
                Assert.Equal(4, fixedOptions.GetInteger("count"));
            }
            await app.StopHoardApplicationAsync(lease);
            await lease.DisposeAsync();
            Assert.True(lease.StopResult!.Complete);
        }
        harness.AssertNoPayload(file, target);
    }

    [Fact]
    public async Task Invalid_restart_has_no_previous_value_reuse_and_explicit_fresh_recovery_is_required()
    {
        ConfiguredFixtures.Reset();
        var bad = JsonNode.Parse(ConfiguredFixtures.Defaults)!;
        bad["modules"]!["metadata"]!["options"]!["label"] = "";
        await using var failed = await ConfiguredFixtures.Evaluate(ConfiguredFixtures.Registry(), bad.ToJsonString());
        Assert.Equal(HoardConfigurationOutcome.Failed, failed.Outcome);
        Assert.Null(failed.Configuration);
        Assert.Empty(LifecycleFixtures.Controls);
        var recovery = ConfiguredFixtures.Registry();
        await using var valid = await ConfiguredFixtures.Evaluate(recovery);
        await using var lease = await recovery.ComposeHoardModulesAsync(valid.Configuration!);
        Assert.Equal("first", ConfiguredFixtures.Delivered!.GetString("label"));
    }
}
