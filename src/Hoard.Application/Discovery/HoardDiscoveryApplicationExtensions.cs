using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Description = Hoard.Application.Features.Modules.GetDiscoveryDescription.Endpoint;
using Read = Hoard.Application.Features.Modules.GetDiscovery.Endpoint;

namespace Hoard.Application.Discovery;

public static class HoardDiscoveryApplicationExtensions
{
    public static WebApplication MapHoardDiscovery(this WebApplication application, HoardServiceComposition composition)
    {
        ArgumentNullException.ThrowIfNull(application);
        ArgumentNullException.ThrowIfNull(composition);
        var source = composition.BindHoardDiscovery(application);
        if (composition.Lifecycle.Snapshot.Phase != HoardLifecyclePhase.BuildingHost)
        { throw new HoardDiscoverySetupException(); }
        var options = application.Services.GetRequiredService<HoardDiscoveryOptions>();
        var exposure = new AuthorizationPolicyBuilder().AddRequirements(new DiscoveryExposureRequirement()).Build();
        application.MapMethods(Read.Route, ["GET"],
            (HttpContext context) => Read.HandleAsync(context, source, options))
            .RequireAuthorization(options.ManagementReadPolicy).RequireAuthorization(exposure);
        application.MapMethods(Description.Route, ["GET"],
            (HttpContext context) => Description.HandleAsync(context, options))
            .RequireAuthorization(options.ManagementReadPolicy).RequireAuthorization(exposure);
        return application;
    }
}
