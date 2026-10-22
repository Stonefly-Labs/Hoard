using System.Text.Json;
using Hoard.Abstractions.Providers;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Hosting;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactCompositionTests
{
    public sealed class DisabledArtifact : IArtifactProvider;

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Configured_selection_is_inert_until_start_and_missing_guarantees_block_readiness(string provider)
    {
        using var selected = new ArtifactTestRoot();
        using var disabled = new ArtifactTestRoot();
        var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
        web.Logging.ClearProviders();
        web.WebHost.UseTestServer();
        var builder = web.Services.AddHoard().AddArtifactFixture()
            .AddArtifactFixture<DisabledArtifact>("fixture.disabled").AddMetadataFixture();
        var defaults = JsonSerializer.Serialize(new
        {
            configurationVersion = 1,
            enabledModules = new[] { "fixture.artifact", "fixture.metadata" },
            artifactModule = "fixture.artifact",
            metadataModule = "fixture.metadata",
            identityModules = Array.Empty<string>(),
            requiredCapabilities = Array.Empty<string>(),
            modules = new Dictionary<string, object>
            {
                ["fixture.artifact"] = new { optionsVersion = 1, options = new { provider, root = selected.Path } },
                ["fixture.metadata"] = new { optionsVersion = 1, options = new { provider = "memory", createEmpty = true } },
                ["fixture.disabled"] = new { optionsVersion = 999, options = new { provider = "invalid", root = disabled.Path } }
            }
        });
        await using var evaluation = await builder.EvaluateConfigurationAsync(new(defaults), new("0.1.0", "0.1.0"), new());
        Assert.Equal(HoardConfigurationOutcome.Validated, evaluation.Outcome);
        await using var lease = await builder.ComposeHoardModulesAsync(evaluation.Configuration!);
        await using var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        var module = app.Services.GetRequiredService<ArtifactFixtureModule>();
        Assert.Single(app.Services.GetServices<ArtifactFixtureModule>());
        Assert.False(Directory.Exists(selected.Path));
        Assert.False(Directory.Exists(disabled.Path));
        Assert.Throws<InvalidOperationException>(() => module.Session);
        await Assert.ThrowsAnyAsync<Exception>(() => app.StartAsync());
        Assert.False(lease.Lifecycle.Snapshot.Ready);
        Assert.False((await module.CheckReadinessAsync(default)).Ready);
        Assert.False(module.Session.Capabilities.MeetsBaseline);
        Assert.Equal($"fixture.artifact.{provider}", module.Session.Identity.ProviderModuleId);
        Assert.False(Directory.Exists(disabled.Path));
    }
}
