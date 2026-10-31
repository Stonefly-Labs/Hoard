using System.Text.Json;
using Hoard.Abstractions.Providers;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Hosting;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Evidence;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Xunit.Abstractions;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactCompositionTests(ITestOutputHelper output)
{
    public sealed class DisabledArtifact : IArtifactProvider;

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Configured_singleton_selection_recovers_and_restarts_explicitly(string provider)
    {
        using var first = new ArtifactTestRoot();
        using var replacement = new ArtifactTestRoot();
        using var disabled = new ArtifactTestRoot();
        ArtifactMutationReceipt? committed = null;
        ArtifactFixtureModule? previousModule = null;
        ConformanceOriginalObservation? previousObservation = null;
        for (var pass = 0; pass < 2; pass++)
        {
            var root = pass == 0 || provider == "local" ? first.Path : replacement.Path;
            var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
            web.Logging.ClearProviders();
            web.WebHost.UseTestServer();
            if (pass == 1 && provider == "local")
            {
                web.Services.AddSingleton(new ArtifactFixtureAdmissionProfile
                {
                    Mode = ArtifactInitializationMode.ReopenCompatible,
                    Store = committed!.Stamp.Store
                });
            }
            var builder = web.Services.AddHoard().AddArtifactFixture()
                .AddArtifactFixture<DisabledArtifact>("fixture.disabled").AddMetadataFixture();
            var defaults = Defaults(provider, root, disabled.Path);
            await using var evaluation = await builder.EvaluateConfigurationAsync(new(defaults), new("0.1.0", "0.1.0"), new());
            Assert.Equal(HoardConfigurationOutcome.Validated, evaluation.Outcome);
            await using var lease = await builder.ComposeHoardModulesAsync(evaluation.Configuration!);
            await using var app = await web.BuildHoardApplicationAsync(lease);
            await app.MapHoardModulesAsync(lease);
            var module = app.Services.GetRequiredService<ArtifactFixtureModule>();
            Assert.Single(app.Services.GetServices<ArtifactFixtureModule>());
            Assert.NotSame(previousModule, module);
            Assert.False((await module.CheckReadinessAsync(default)).Ready);
            await app.StartAsync();
            Assert.True(lease.Lifecycle.Snapshot.Ready);
            Assert.True((await module.CheckReadinessAsync(default)).Ready);
            Assert.True(module.Session.Capabilities.MeetsBaseline);
            Assert.Equal($"fixture.artifact.{provider}", module.Session.Identity.ProviderModuleId);
            var old = committed;
            if (old is null)
            {
                committed = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(module.Session.Store, default);
            }
            else if (provider == "local")
            {
                await ArtifactCompositionAssertions.CompatibleReopenAsync(
                    module.Session.Store, module.Session.Identity, old, default);
            }
            else
            {
                await ArtifactCompositionAssertions.FreshEpochAsync(
                    module.Session.Store, module.Session.Identity, old, default);
            }
            Assert.False(Directory.Exists(disabled.Path));
            await app.StopAsync();
            Assert.False((await module.CheckReadinessAsync(default)).Ready);
            Assert.False(module.Session.Ready);
            previousObservation = ArtifactProviderDriver.ObserveOriginalSession(output,
                nameof(ArtifactCompositionTests), provider, module.Session, module, previousObservation);
            previousModule = module;
        }
    }

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
        web.Services.AddSingleton(new ArtifactFixtureAdmissionProfile
        {
            CapabilitiesForAdmission = capabilities => new(1, capabilities.Durability, capabilities.Enumeration,
                capabilities.Limits, boundedStreaming: false)
        });
        var builder = web.Services.AddHoard().AddArtifactFixture()
            .AddArtifactFixture<DisabledArtifact>("fixture.disabled").AddMetadataFixture();
        var defaults = Defaults(provider, selected.Path, disabled.Path);
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
        Assert.Throws<InvalidOperationException>(() => module.Session);
        Assert.False(Directory.Exists(selected.Path));
        Assert.False(Directory.Exists(disabled.Path));
        ArtifactProviderDriver.ObserveOriginalOwner(output, nameof(ArtifactCompositionTests), module, provider: provider);
    }

    private static string Defaults(string provider, string root, string disabled) => JsonSerializer.Serialize(new
    {
        configurationVersion = 1,
        enabledModules = new[] { "fixture.artifact", "fixture.metadata" },
        artifactModule = "fixture.artifact",
        metadataModule = "fixture.metadata",
        identityModules = Array.Empty<string>(),
        requiredCapabilities = Array.Empty<string>(),
        modules = new Dictionary<string, object>
        {
            ["fixture.artifact"] = new { optionsVersion = 1, options = new { provider, root } },
            ["fixture.metadata"] = new { optionsVersion = 1, options = new { provider = "memory", createEmpty = true } },
            ["fixture.disabled"] = new { optionsVersion = 999, options = new { provider = "invalid", root = disabled } }
        }
    });
}
