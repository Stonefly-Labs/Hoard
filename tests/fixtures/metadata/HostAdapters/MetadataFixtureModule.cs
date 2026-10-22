using Hoard.Abstractions.Metadata;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Hoard.Hosting.Routing;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Fixtures.Metadata.Hosting;

public sealed class MetadataFixtureModule : IHoardModule, IHoardConfiguredModule, IAsyncDisposable
{
    private HoardModuleOptions? options;
    private MetadataFixtureSession? session;
    private volatile bool ready;
    private readonly object shutdownLock = new();
    private readonly TaskCompletionSource admissionClosed = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private Task? shutdown;
    public Task AdmissionClosedForTest => admissionClosed.Task.WaitAsync(TimeSpan.FromSeconds(10));
    public MetadataFixtureSession Session => session ?? throw new InvalidOperationException("Metadata fixture has not initialized.");
    public void ConfigureOptions(HoardModuleOptions value) => options = value;
    public void ConfigureServices(IServiceCollection services) => services.AddSingleton(this);
    public void MapEndpoints(HoardModuleEndpointBuilder endpoints) { }

    public async ValueTask InitializeAsync(IServiceProvider services, CancellationToken cancellationToken)
    {
        var configured = options ?? throw new InvalidOperationException("Metadata fixture owner options are required.");
        session = MetadataFixtureSession.Create(configured.GetString("provider"), TimeProvider.System,
            configured.Contains("databasepath") ? configured.GetString("databasepath") : null);
        var inspected = await session.Schema.InspectAsync(new(), cancellationToken);
        if (inspected is not MetadataResult<MetadataSchemaInspection>.Success inspection)
        { throw new InvalidOperationException("Metadata fixture schema inspection failed."); }
        MetadataSchemaRequest request = inspection.Value.State == MetadataSchemaState.Empty && configured.GetBoolean("createempty")
            ? new MetadataSchemaRequest.CreateIfEmpty() : new MetadataSchemaRequest.InspectOnly();
        var result = await session.Schema.PrepareAsync(request, new(), cancellationToken);
        ready = result is MetadataResult<MetadataSchemaAdmission>.Success;
        if (!ready) { throw new InvalidOperationException("Metadata fixture schema admission failed."); }
    }

    public ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken cancellationToken) =>
        ValueTask.FromResult(new HoardModuleReadiness(ready, []));
    public Task RunAsync(CancellationToken stoppingToken) => Task.CompletedTask;
    public ValueTask StopAsync(CancellationToken cancellationToken) => new(ShutdownAsync());
    public ValueTask DisposeAsync() => new(ShutdownAsync());
    private Task ShutdownAsync()
    {
        lock (shutdownLock) { ready = false; return shutdown ??= StopOwnedAsync(); }
    }
    private async Task StopOwnedAsync()
    {
        var stopping = session?.DisposeAsync().AsTask() ?? Task.CompletedTask;
        admissionClosed.TrySetResult();
        await stopping;
    }
}
