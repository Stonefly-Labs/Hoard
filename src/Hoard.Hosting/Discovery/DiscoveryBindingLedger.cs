using System.Collections.Immutable;
using Hoard.Hosting.Routing;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting.Discovery;

internal sealed record DiscoverySealedBindings(bool ServicesSealed, bool RoutesSealed,
    ImmutableHashSet<string> Services, ImmutableHashSet<DiscoveryRouteBinding> Routes);

internal sealed class DiscoveryBindingLedger
{
    private readonly Dictionary<ServiceDescriptor, string> owners = new(ReferenceEqualityComparer.Instance);
    private DiscoverySealedBindings current = new(false, false, [], []);
    internal DiscoverySealedBindings Capture() => Volatile.Read(ref current);

    internal void Record(string owner, IServiceCollection services, ServiceDescriptor[] before)
    {
        var previous = new HashSet<ServiceDescriptor>(before, ReferenceEqualityComparer.Instance);
        foreach (var descriptor in services.Where(descriptor => !previous.Contains(descriptor)))
        { owners.TryAdd(descriptor, owner); }
    }

    internal void SealServices(FrozenDiscovery catalog, IServiceCollection services)
    {
        var valid = ImmutableHashSet.CreateBuilder<string>(StringComparer.Ordinal);
        foreach (var binding in catalog.Services)
        {
            var matches = services.Where(descriptor => descriptor.ServiceType == binding.ServiceType).Take(2).ToArray();
            if (matches.Length == 1 && !matches[0].IsKeyedService
                && owners.TryGetValue(matches[0], out var owner) && owner == binding.OwnerId)
            { valid.Add(binding.Id); }
        }
        Volatile.Write(ref current, current with { ServicesSealed = true, Services = valid.ToImmutable() });
    }

    internal void SealRoutes(IEnumerable<HoardOwnedRoute> routes) =>
        Volatile.Write(ref current, current with
        {
            RoutesSealed = true,
            Routes = routes.SelectMany(route => route.Methods.Select(method =>
                new DiscoveryRouteBinding(route.ModuleId, route.ResponsibilityId, method))).ToImmutableHashSet()
        });
}
