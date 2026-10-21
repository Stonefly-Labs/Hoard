using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting.Discovery;

internal static class DiscoveryOwnership
{
    internal static IHoardDiscoverySource Bind(HoardServiceComposition lease, WebApplication application)
    {
        if (!ReferenceEquals(application, lease.Application)
            || lease.Discovery is not HoardDiscoverySource source || !ReferenceEquals(source.Lease, lease)
            || !ReferenceEquals(source.Registration, lease.Composition.Builder.DiscoveryRegistration)
            || !ReferenceEquals(application.Services.GetService<HoardServiceComposition>(), lease)
            || !ReferenceEquals(application.Services.GetService<IHoardDiscoverySource>(), source)
            || !ReferenceEquals(application.Services.GetService<HoardDiscoveryOptions>(), source.Registration.Options))
        { throw lease.Coordinator.Error("StaleComposition", "composition", HoardLifecyclePhase.ComposingRoutes); }
        return source;
    }
}
