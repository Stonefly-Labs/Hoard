using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Application.Discovery;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
web.Logging.ClearProviders();
web.WebHost.UseUrls("http://127.0.0.1:0").PreferHostingUrls(true);
web.Services.AddAuthorization(options => options.AddPolicy("Hoard.Management.Read", policy => policy.RequireAssertion(_ => true)));
var builder = web.Services.AddHoard()
    .AddModule<Metadata>(Declaration("metadata", ModuleCategory.Metadata)).AddModuleLifecycle<Metadata, Passive>()
    .AddModule<Artifact>(Declaration("artifact", ModuleCategory.Artifact)).AddModuleLifecycle<Artifact, Passive>()
    .AddHoardDiscovery(new("public-source-consumer", "0.1.0", "partial"), new()
    { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true });
var result = builder.ValidateComposition(new()
{
    EnabledModuleIds = ["metadata", "artifact"],
    MetadataModuleId = "metadata",
    ArtifactModuleId = "artifact",
    RequiredCapabilities = []
}, new("0.1.0", "0.1.0"), new());
await using var lease = await builder.ComposeHoardModulesAsync(result.Composition!);
var app = await web.BuildHoardApplicationAsync(lease);
app.MapHoardDiscovery(lease);
await app.MapHoardModulesAsync(lease);
var source = lease.BindHoardDiscovery(app);
if (!source.Capture().Success || !ReferenceEquals(source, lease.BindHoardDiscovery(app)))
{ throw new InvalidOperationException("Public discovery binding failed."); }
Console.WriteLine("application-discovery-compatible");

static ModuleDescriptor Declaration(string id, ModuleCategory category) => new()
{
    Id = id,
    Category = category,
    Version = "0.1.0",
    Compatibility = new() { HostRange = "[0.1.0,0.2.0)", AbstractionsRange = "[0.1.0,0.2.0)", AllowPrereleaseHost = false, AllowPrereleaseAbstractions = false },
    Dependencies = [],
    Capabilities = [],
    Configuration = [],
    Endpoints = [],
    Health = [],
    Provenance = new() { Publisher = "Public API fixture", SupportStatus = ModuleSupportStatus.Fixture }
};
sealed class Metadata : IMetadataProvider;
sealed class Artifact : IArtifactProvider;
sealed class Passive : IHoardModule
{
    public void ConfigureServices(IServiceCollection services) { }
    public void MapEndpoints(HoardModuleEndpointBuilder routes) { }
    public ValueTask InitializeAsync(IServiceProvider services, CancellationToken token) => ValueTask.CompletedTask;
    public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token) => ValueTask.FromResult(new HoardModuleReadiness(true, []));
    public Task RunAsync(CancellationToken token) => Task.CompletedTask;
    public ValueTask StopAsync(CancellationToken token) => ValueTask.CompletedTask;
}
