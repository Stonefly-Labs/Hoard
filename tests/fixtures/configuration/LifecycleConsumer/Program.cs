using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using Microsoft.Extensions.DependencyInjection;

var builder = new ServiceCollection().AddHoard()
    .AddModule<Metadata>(Declaration("metadata", ModuleCategory.Metadata))
    .AddModuleLifecycle<Metadata, Module>()
    .AddModule<Artifact>(Declaration("artifact", ModuleCategory.Artifact))
    .AddModuleLifecycle<Artifact, Module>();
var result = builder.ValidateComposition(new()
{
    EnabledModuleIds = ["metadata", "artifact"],
    MetadataModuleId = "metadata",
    ArtifactModuleId = "artifact",
    RequiredCapabilities = []
}, new("0.1.0", "0.1.0"), new());
if (result.Composition is null) { throw new InvalidOperationException("Fixture composition rejected."); }
await using var lease = await builder.ComposeHoardModulesAsync(result.Composition);
await lease.DisposeAsync();
if (lease.StopResult?.Complete != true) { throw new InvalidOperationException("Fixture cleanup incomplete."); }
Console.WriteLine("lifecycle-compatible");

static ModuleDescriptor Declaration(string id, ModuleCategory category) => new()
{
    Id = id,
    Category = category,
    Version = "0.1.0",
    Compatibility = new()
    {
        HostRange = "[0.1.0,0.2.0)", AbstractionsRange = "[0.1.0,0.2.0)",
        AllowPrereleaseHost = false, AllowPrereleaseAbstractions = false
    },
    Dependencies = [], Capabilities = [], Configuration = [], Endpoints = [], Health = [],
    Provenance = new() { Publisher = "Configuration fixtures", SupportStatus = ModuleSupportStatus.Fixture }
};

sealed class Metadata : IMetadataProvider;
sealed class Artifact : IArtifactProvider;
sealed class Module : IHoardModule
{
    public void ConfigureServices(IServiceCollection services) { }
    public void MapEndpoints(HoardModuleEndpointBuilder endpoints) { }
    public ValueTask InitializeAsync(IServiceProvider services, CancellationToken token) => ValueTask.CompletedTask;
    public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token) =>
        ValueTask.FromResult(new HoardModuleReadiness(true, []));
    public Task RunAsync(CancellationToken token) => Task.CompletedTask;
    public ValueTask StopAsync(CancellationToken token) => ValueTask.CompletedTask;
}
