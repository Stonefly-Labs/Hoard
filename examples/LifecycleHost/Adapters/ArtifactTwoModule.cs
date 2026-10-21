using Hoard.Fixtures.Lifecycle.Artifact.Two;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;

namespace LifecycleHost.Adapters;

public sealed class ArtifactTwoModule : IHoardModule, IHoardConfiguredModule
{
    public void ConfigureOptions(HoardModuleOptions options) { }
    private ArtifactTwoProvider? provider;
    public void ConfigureServices(IServiceCollection services) { }
    public void MapEndpoints(HoardModuleEndpointBuilder endpoints) { }
    public ValueTask InitializeAsync(IServiceProvider services, CancellationToken token)
    { provider = new(); provider.Acquire(); return ValueTask.CompletedTask; }
    public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token) =>
        ValueTask.FromResult(new HoardModuleReadiness(provider is not null, []));
    public Task RunAsync(CancellationToken token) => Task.CompletedTask;
    public ValueTask StopAsync(CancellationToken token)
    { provider?.Release(); provider = null; return ValueTask.CompletedTask; }
}
