using Hoard.Application.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Builder;

namespace Discovery.PermittedApplication;

public static class Consumer
{
    public static WebApplication Map(WebApplication app, HoardServiceComposition composition) =>
        app.MapHoardDiscovery(composition);
}
