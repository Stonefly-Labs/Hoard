using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting;

public sealed class HoardBuilder
{
    internal HoardBuilder(IServiceCollection services) => Services = services;

    public IServiceCollection Services { get; }
    internal object ConfigurationGate { get; } = new();
}
