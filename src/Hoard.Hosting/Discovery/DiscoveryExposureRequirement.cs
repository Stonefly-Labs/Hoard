using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;

namespace Hoard.Hosting.Discovery;

public sealed class DiscoveryExposureRequirement : IAuthorizationRequirement;

internal sealed class DiscoveryExposureHandler(IDiscoveryExposureAdapter adapter, HoardDiscoveryOptions options)
    : AuthorizationHandler<DiscoveryExposureRequirement>
{
    protected override Task HandleRequirementAsync(AuthorizationHandlerContext context, DiscoveryExposureRequirement requirement)
    {
        if (context.Resource is HttpContext http && adapter.Verified && adapter.Allows(http)
            && (options.Exposure == HoardDiscoveryExposure.LocalLoopback
                || context.User.Identities.Any(identity => identity.IsAuthenticated)))
        { context.Succeed(requirement); }
        return Task.CompletedTask;
    }
}
