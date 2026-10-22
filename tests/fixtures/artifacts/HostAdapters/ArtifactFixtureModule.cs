using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Fixtures.Artifacts.HostAdapters;

public sealed class ArtifactFixtureModule : IHoardModule, IHoardConfiguredModule, IAsyncDisposable
{
    private HoardModuleOptions? options;
    private ArtifactFixtureSession? session;
    private readonly object shutdownSync = new();
    private Task? shutdown;
    private volatile bool ready;

    public ArtifactFixtureSession Session => session
        ?? throw new InvalidOperationException("Artifact fixture has not initialized.");
    public void ConfigureOptions(HoardModuleOptions value) => options = value;
    public void ConfigureServices(IServiceCollection services) => services.AddSingleton(this);
    public void MapEndpoints(HoardModuleEndpointBuilder endpoints) { }

    public async ValueTask InitializeAsync(IServiceProvider services, CancellationToken cancellationToken)
    {
        var configured = options ?? throw new InvalidOperationException("Artifact fixture owner options are required.");
        cancellationToken.ThrowIfCancellationRequested();
        session = await ArtifactFixtureSession.CreateForQualificationAsync(
            configured.GetString("provider"), configured.GetString("root"), cancellationToken: cancellationToken);
        if (!session.Capabilities.MeetsBaseline)
        { throw new InvalidOperationException("Artifact fixture lacks mandatory guarantees; readiness is denied."); }
        ready = true;
    }

    public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken cancellationToken) =>
        ValueTask.FromResult(new HoardModuleReadiness(ready && session is { Ready: true }, []));
    public Task RunAsync(CancellationToken stoppingToken) => Task.CompletedTask;
    public ValueTask StopAsync(CancellationToken cancellationToken) => new(ShutdownAsync());
    public ValueTask DisposeAsync() => new(ShutdownAsync());

    private Task ShutdownAsync()
    {
        lock (shutdownSync)
        {
            ready = false;
            return shutdown ??= session?.DisposeAsync().AsTask() ?? Task.CompletedTask;
        }
    }
}
