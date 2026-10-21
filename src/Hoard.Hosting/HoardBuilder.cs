using Hoard.Hosting.Discovery;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting;

public sealed class HoardBuilder
{
    internal HoardBuilder(IServiceCollection services) => Services = services;

    public IServiceCollection Services { get; }
    internal object ConfigurationGate { get; } = new();
    internal bool ConfigurationConsumed { get; set; }
    internal bool DiscoveryFrozen { get; set; }
    internal DiscoveryRegistration? DiscoveryRegistration { get; set; }
    internal HoardDiscoverySource? DiscoverySource { get; set; }
}
