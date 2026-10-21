using System.Diagnostics.Metrics;
using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Hoard.Hosting.Configuration.Conversion;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using Microsoft.Extensions.DependencyInjection;

if (args.Length != 3) { throw new InvalidOperationException("Explicit private conversion fixture inputs are required."); }
using var listener = new MeterListener();
listener.InstrumentPublished = (instrument, owner) =>
{
    if (instrument.Meter.Name == "Hoard.Configuration") { owner.EnableMeasurementEvents(instrument); }
};
listener.SetMeasurementEventCallback<long>((_, _, tags, _) =>
{
    foreach (var tag in tags)
    {
        if (tag.Key == "category" && tag.Value?.ToString() == args[2])
        {
            Console.WriteLine("barrier:" + args[2]);
            Console.Out.Flush();
            using var wait = new ManualResetEventSlim();
            wait.Wait();
        }
    }
});
listener.Start();
var builder = new ServiceCollection().AddHoard()
    .AddModule<MetadataProvider>(Descriptor("metadata", ModuleCategory.Metadata))
    .AddModuleLifecycle<MetadataProvider, NoopModule>()
    .AddModule<ArtifactProvider>(Descriptor("artifact", ModuleCategory.Artifact))
    .AddModuleLifecycle<ArtifactProvider, NoopModule>();
await using var preview = await builder.PreviewConfigurationConversionAsync(args[0], args[1], new("0.1.0", "0.1.0"), new());
if (preview.Session is null) { throw new InvalidOperationException("Conversion fixture preview failed."); }
preview.Session.Approve();
await using var applied = await builder.ApplyConfigurationConversionAsync(preview.Session);
if (applied.Outcome != HoardConfigurationApplyOutcome.Published) { throw new InvalidOperationException("Conversion fixture publication failed."); }

static ModuleDescriptor Descriptor(string id, ModuleCategory category) => new()
{
    Id = id,
    Category = category,
    Version = "0.1.0",
    Compatibility = new() { HostRange = "[0.1.0]", AbstractionsRange = "[0.1.0]", AllowPrereleaseHost = false, AllowPrereleaseAbstractions = false },
    Configuration = [],
    Dependencies = [],
    Capabilities = [],
    Endpoints = [],
    Health = [],
    Provenance = new() { Publisher = "Configuration fixtures", SupportStatus = ModuleSupportStatus.Fixture }
};
public sealed class MetadataProvider : IMetadataProvider;
public sealed class ArtifactProvider : IArtifactProvider;
public sealed class NoopModule : IHoardModule
{
    public NoopModule() => throw new InvalidOperationException("Conversion must never construct a module.");
    public void ConfigureServices(IServiceCollection services) { }
    public void MapEndpoints(HoardModuleEndpointBuilder endpoints) { }
    public ValueTask InitializeAsync(IServiceProvider services, CancellationToken token) => ValueTask.CompletedTask;
    public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token) => ValueTask.FromResult(new HoardModuleReadiness(true, []));
    public Task RunAsync(CancellationToken token) => Task.CompletedTask;
    public ValueTask StopAsync(CancellationToken token) => ValueTask.CompletedTask;
}
