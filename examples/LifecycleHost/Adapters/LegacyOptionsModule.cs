#if CONFIGURATION_LEGACY
using Hoard.Fixtures.Configuration.LegacyOptions;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;

namespace LifecycleHost.Adapters;

public sealed class LegacyOptionsModule : IHoardModule, IHoardConfiguredModule
{
    private HoardModuleOptions? options;
    private bool ready;
    public static int Accepted;
    public void ConfigureOptions(HoardModuleOptions values) => options = values;
    public void ConfigureServices(IServiceCollection services) { }
    public void MapEndpoints(HoardModuleEndpointBuilder endpoints) { }
    public ValueTask InitializeAsync(IServiceProvider services, CancellationToken token)
    {
        ready = new LegacyOptionsProvider().Accepts(options!.GetString("label"), options.GetSecret("credential").Reveal());
        if (ready) { Interlocked.Increment(ref Accepted); }
        return ValueTask.CompletedTask;
    }
    public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken token) => ValueTask.FromResult(new HoardModuleReadiness(ready, []));
    public Task RunAsync(CancellationToken token) => Task.CompletedTask;
    public ValueTask StopAsync(CancellationToken token) { ready = false; return ValueTask.CompletedTask; }
}
#endif
