using System.Collections.Immutable;
using System.Text.Json;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.TestHost;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryDisclosureTests
{
    [Fact]
    public async Task Only_approved_literals_survive_and_owned_failures_keep_closed_safe_guidance()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        await using var harness = new DiscoveryTestHarness();
        var catalog = DiscoveryFixtures.Catalog() with
        {
            Publications = [new("protocol") { Publisher = "Approved fixture publisher" }]
        };
        var (app, lease) = await DiscoveryAuthorizationTests.HttpFixture(catalog);
        await using (lease)
        {
            await app.StartAsync();
            using var client = app.GetTestClient();
            client.DefaultRequestHeaders.Add("X-Fixture-Identity", "read");
            var observed = new List<string> { JsonSerializer.Serialize(lease.Discovery!.Capture()) };
            foreach (var path in new[] { "/api/v1/discovery", "/api/v1/discovery/openapi.json", "/api/v1/discovery?unknown=value" })
            { observed.Add(await client.GetStringAsync(path == "/api/v1/discovery?unknown=value" ? "/api/v1/discovery" : path)); }
            using var failure = await client.GetAsync("/api/v1/discovery?unknown=value");
            observed.Add(await failure.Content.ReadAsStringAsync());
            var all = string.Join("\n", observed.Concat(harness.Output).Concat(LifecycleFixtures.LogCapture.Logs));
            Assert.Contains("Approved fixture publisher", all);
            Assert.DoesNotContain(DiscoveryTestHarness.Secret, all);
            Assert.DoesNotContain(DiscoveryTestHarness.Locator, all);
            using var problem = JsonDocument.Parse(observed[^1]);
            Assert.Equal("request", problem.RootElement.GetProperty("phase").GetString());
            Assert.True(Guid.TryParse(problem.RootElement.GetProperty("correlationId").GetString(), out _));
            Assert.Contains("GET", problem.RootElement.GetProperty("detail").GetString(), StringComparison.Ordinal);
            harness.AssertNoPayload();
        }
    }

    [Fact]
    public async Task Raw_option_metadata_and_disabled_secret_locations_are_not_public_defaults()
    {
        ConfiguredFixtures.Reset();
        var builder = ConfiguredFixtures.Registry().AddHoardDiscovery(new("fixture", "0.1.0", "complete")
        {
            Publications = [new("metadata")
            {
                Publisher = "Approved",
                Options = [new("label") { Description = "Public label", PublicDefault = "Public default", AllowedValues = ["Public choice"] },
                    new("credential") { Description = "Private credential required when selected" }]
            }]
        }, new());
        await using var evaluation = await ConfiguredFixtures.Evaluate(builder);
        await using var lease = await builder.ComposeHoardModulesAsync(evaluation.Configuration!);
        var observation = lease.Discovery!.Capture().Observation!;
        var module = observation.Modules.Single(module => module.Id == "metadata");
        Assert.Equal("Public default", module.Options.Single(option => option.Id == "label").PublicDefault);
        Assert.Null(module.Options.Single(option => option.Id == "credential").PublicDefault);
        Assert.Null(module.Options.Single(option => option.Id == "credential").AllowedValues);
        Assert.DoesNotContain("\"first\"", JsonSerializer.Serialize(observation));
        Assert.Contains(module.Reasons, reason => reason.Code == "metadata-suppressed");
    }
}
