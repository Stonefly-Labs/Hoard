using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Http;

namespace Hoard.Hosting.Routing;

public sealed class HoardModuleEndpointBuilder
{
    private readonly ModuleDescriptor declaration;
    private readonly HoardLifecycleCoordinator coordinator;
    private readonly List<HoardOwnedRoute> routes = [];
    private bool sealedBuilder;

    internal HoardModuleEndpointBuilder(ModuleDescriptor declaration, HoardLifecycleCoordinator coordinator)
    {
        this.declaration = declaration;
        this.coordinator = coordinator;
    }

    public void Map(string responsibilityId, string pattern, IEnumerable<string> methods, RequestDelegate handler)
    {
        ArgumentNullException.ThrowIfNull(responsibilityId);
        ArgumentNullException.ThrowIfNull(pattern);
        ArgumentNullException.ThrowIfNull(methods);
        ArgumentNullException.ThrowIfNull(handler);
        if (sealedBuilder || !declaration.Endpoints.Any(item => item.Id == responsibilityId))
        { throw coordinator.Error("UnsupportedRouteShape", declaration.Id, HoardLifecyclePhase.ComposingRoutes); }
        var route = HoardOwnedRoute.Create(declaration.Id, responsibilityId, pattern, methods, handler);
        if (route is null) { throw coordinator.Error("UnsupportedRouteShape", declaration.Id, HoardLifecyclePhase.ComposingRoutes); }
        routes.Add(route);
    }

    internal ImmutableArray<HoardOwnedRoute> Seal()
    {
        sealedBuilder = true;
        if (declaration.Endpoints.Any(item => !routes.Any(route => route.ResponsibilityId == item.Id)))
        { throw coordinator.Error("MissingEndpoint", declaration.Id, HoardLifecyclePhase.ComposingRoutes); }
        return routes.ToImmutableArray();
    }
}
