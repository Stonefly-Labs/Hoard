using System.Text.Json;
using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using Hoard.Fixtures.Metadata.Hosting;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataHostIntegrationTests
{
    public sealed class ArtifactMarker : IArtifactProvider;
    public sealed class UnusedMarker : IMetadataProvider;
    public sealed class ArtifactModule : IHoardModule
    {
        public void ConfigureServices(IServiceCollection services) { }
        public void MapEndpoints(HoardModuleEndpointBuilder endpoints) { }
        public ValueTask InitializeAsync(IServiceProvider services, CancellationToken cancellationToken) => ValueTask.CompletedTask;
        public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken cancellationToken) => ValueTask.FromResult(new HoardModuleReadiness(true, []));
        public Task RunAsync(CancellationToken stoppingToken) => Task.CompletedTask;
        public ValueTask StopAsync(CancellationToken cancellationToken) => ValueTask.CompletedTask;
    }

    [Fact]
    public async Task MP46_Configured_selection_uses_existing_lifecycle_and_has_no_routes_or_fallback()
    {
        foreach (var createEmpty in new[] { true, false })
        {
            var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
            web.Logging.ClearProviders();
            web.WebHost.UseTestServer();
            var builder = web.Services.AddHoard().AddMetadataFixture();
            var registration = Assert.Single(builder.Services.Select(service => service.ImplementationInstance)
                .OfType<HoardModuleRegistration>());
            Assert.Equal("fixture.metadata", registration.Declaration.Id);
            Assert.Equal("0.1.0", registration.Declaration.Version);
            builder.AddMetadataFixture<UnusedMarker>("fixture.disabled");
            var disabledPath = Path.Combine(Path.GetTempPath(), "hoard-disabled-" + Guid.NewGuid().ToString("N") + ".db");
            builder.AddModule<ArtifactMarker>(new()
            {
                Id = "fixture.artifact",
                Category = ModuleCategory.Artifact,
                Version = "0.1.0",
                Compatibility = new()
                {
                    HostRange = "[0.1.0,0.2.0)",
                    AbstractionsRange = "[0.1.0,0.2.0)",
                    AllowPrereleaseHost = false,
                    AllowPrereleaseAbstractions = false
                },
                Dependencies = [],
                Capabilities = [],
                Configuration = [],
                Endpoints = [],
                Health = [],
                Provenance = new() { Publisher = "Hoard metadata acceptance", SupportStatus = ModuleSupportStatus.Fixture }
            }).AddModuleLifecycle<ArtifactMarker, ArtifactModule>();
            var defaults = JsonSerializer.Serialize(new
            {
                configurationVersion = 1,
                enabledModules = new[] { "fixture.metadata", "fixture.artifact" },
                metadataModule = "fixture.metadata",
                artifactModule = "fixture.artifact",
                identityModules = Array.Empty<string>(),
                requiredCapabilities = Array.Empty<string>(),
                modules = new Dictionary<string, object>
                {
                    ["fixture.metadata"] = new
                    {
                        optionsVersion = 1,
                        options = new { provider = Environment.GetEnvironmentVariable("HOARD_METADATA_PROVIDER"), createEmpty }
                    },
                    ["fixture.disabled"] = new
                    {
                        optionsVersion = 999,
                        options = new
                        {
                            provider = "invalid",
                            createEmpty = true,
                            databasePath = disabledPath
                        }
                    }
                }
            });
            await using var evaluation = await builder.EvaluateConfigurationAsync(new(defaults), new("0.1.0", "0.1.0"), new());
            Assert.Equal(HoardConfigurationOutcome.Validated, evaluation.Outcome);
            await using var lease = await builder.ComposeHoardModulesAsync(evaluation.Configuration!);
            var app = await web.BuildHoardApplicationAsync(lease);
            await app.MapHoardModulesAsync(lease);
            var module = app.Services.GetRequiredService<MetadataFixtureModule>();
            Assert.Single(app.Services.GetServices<MetadataFixtureModule>());
            Assert.False(File.Exists(disabledPath));
            Assert.Throws<InvalidOperationException>(() => module.Session);
            if (createEmpty)
            {
                await app.StartAsync();
                Assert.True(lease.Lifecycle.Snapshot.Ready);
                Assert.Equal(Environment.GetEnvironmentVariable("HOARD_METADATA_PROVIDER"), module.Session.Provider);
                await Seed(module.Session);
                using var response = await app.GetTestClient().GetAsync("/metadata-is-not-an-endpoint");
                Assert.Equal(System.Net.HttpStatusCode.NotFound, response.StatusCode);
                await using var barrier = new MetadataTestBarrier();
                module.Session.Controls.SetObserver("read.item", () => new(barrier.HoldAsync()));
                var reading = module.Session.Store.ReadAsync(new([Registry().Selector]),
                    new(TimeSpan.FromMilliseconds(100)), default).AsTask();
                await barrier.Entered;
                var stopping = app.StopHoardApplicationAsync(lease);
                try
                {
                    await module.AdmissionClosedForTest;
                    Assert.False((await module.CheckReadinessAsync(default)).Ready);
                    Assert.False(stopping.IsCompleted);
                    Assert.Equal(Hoard.Abstractions.Metadata.MetadataFailureCode.Disposed,
                        Failed(await module.Session.Store.ReserveOperationAsync(new(), default)));
                }
                finally { barrier.Release(); await reading; await stopping; }
            }
            else
            {
                await Assert.ThrowsAnyAsync<Exception>(() => app.StartAsync());
                Assert.False(lease.Lifecycle.Snapshot.Ready);
                Assert.IsType<Hoard.Abstractions.Metadata.MetadataResult<Hoard.Abstractions.Metadata.MetadataOperationTicket>.Failure>(
                    await module.Session.Store.ReserveOperationAsync(new(), default));
            }
            Assert.False(File.Exists(disabledPath));
        }
    }
}
