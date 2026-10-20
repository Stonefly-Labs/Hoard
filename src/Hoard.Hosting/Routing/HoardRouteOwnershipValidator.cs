using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using Microsoft.AspNetCore.Routing.Matching;
using Microsoft.AspNetCore.Routing.Patterns;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Primitives;

namespace Hoard.Hosting.Routing;

internal static class HoardRouteOwnershipValidator
{
    private sealed record Candidate(string Owner, RoutePattern Pattern, string[] Methods, decimal Precedence);

    internal static void Validate(WebApplication app, IEnumerable<HoardOwnedRoute> owned, HoardLifecycleCoordinator coordinator)
    {
        var candidates = owned.Select(route => new Candidate(route.ModuleId, route.Pattern, route.Methods.ToArray(), route.Precedence)).ToList();
        if (app.Services.GetServices<MatcherPolicy>().Any(policy => policy.GetType().Assembly != typeof(HttpMethodMatcherPolicy).Assembly))
        { throw coordinator.Error("UnsupportedRouteShape", "host", HoardLifecyclePhase.ComposingRoutes); }
        foreach (var source in ((IEndpointRouteBuilder)app).DataSources)
        {
            if (source is OwnedDataSource) { continue; }
            if (source.GetType().FullName != "Microsoft.AspNetCore.Routing.RouteEndpointDataSource")
            { throw coordinator.Error("UnsupportedRouteShape", "host", HoardLifecyclePhase.ComposingRoutes); }
            foreach (var endpoint in source.Endpoints)
            {
                if (endpoint is not RouteEndpoint { Order: 0 } route || !HoardOwnedRoute.Supported(route.RoutePattern)
                    || endpoint.Metadata.GetMetadata<IHttpMethodMetadata>() is not { HttpMethods.Count: > 0 } methods
                    || endpoint.Metadata.GetMetadata<IHostMetadata>() is not null
                    || endpoint.Metadata.GetMetadata<IDynamicEndpointMetadata>() is not null
                    || endpoint.Metadata.GetMetadata<ISuppressMatchingMetadata>() is { SuppressMatching: true })
                { throw coordinator.Error("UnsupportedRouteShape", "host", HoardLifecyclePhase.ComposingRoutes); }
                candidates.Add(new("host", route.RoutePattern, methods.HttpMethods.ToArray(), route.RoutePattern.InboundPrecedence));
            }
        }
        for (var first = 0; first < candidates.Count; first++)
        {
            for (var second = first + 1; second < candidates.Count; second++)
            {
                var left = candidates[first];
                var right = candidates[second];
                if (left.Methods.Intersect(right.Methods, StringComparer.OrdinalIgnoreCase).Any()
                    && Intersects(left.Pattern, right.Pattern) && left.Precedence == right.Precedence)
                { throw coordinator.Error("AmbiguousRoute", left.Owner, HoardLifecyclePhase.ComposingRoutes, path: [left.Owner, right.Owner]); }
            }
        }
    }

    private static bool Intersects(RoutePattern left, RoutePattern right) => left.PathSegments.Count == right.PathSegments.Count
        && left.PathSegments.Zip(right.PathSegments).All(pair =>
            pair.First.Parts[0] is not RoutePatternLiteralPart a || pair.Second.Parts[0] is not RoutePatternLiteralPart b
                || string.Equals(a.Content, b.Content, StringComparison.OrdinalIgnoreCase));

    internal static void Publish(WebApplication app, IEnumerable<HoardOwnedRoute> routes, HoardLifecycleCoordinator coordinator)
    {
        var endpoints = routes.Select(route => new RouteEndpoint(
            context => HoardModuleAdmissionMiddleware.DispatchAsync(context, route, coordinator),
            route.Pattern, 0, new EndpointMetadataCollection(new HttpMethodMetadata(route.Methods)), "Hoard owned module route")).ToArray();
        ((IEndpointRouteBuilder)app).DataSources.Add(new OwnedDataSource(endpoints));
    }

    private sealed class OwnedDataSource(Endpoint[] endpoints) : EndpointDataSource
    {
        public override IReadOnlyList<Endpoint> Endpoints => endpoints;
        public override IChangeToken GetChangeToken() => new CancellationChangeToken(CancellationToken.None);
    }
}
