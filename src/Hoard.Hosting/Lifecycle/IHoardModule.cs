using Hoard.Hosting.Routing;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting.Lifecycle;

public interface IHoardModule
{
    void ConfigureServices(IServiceCollection services);
    void MapEndpoints(HoardModuleEndpointBuilder endpoints);
    ValueTask InitializeAsync(IServiceProvider services, CancellationToken cancellationToken);
    ValueTask<HoardModuleReadiness> CheckReadinessAsync(CancellationToken cancellationToken);
    Task RunAsync(CancellationToken stoppingToken);
    ValueTask StopAsync(CancellationToken cancellationToken);
}
