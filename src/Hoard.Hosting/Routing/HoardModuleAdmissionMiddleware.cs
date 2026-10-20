using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Http;

namespace Hoard.Hosting.Routing;

internal static class HoardModuleAdmissionMiddleware
{
    internal static async Task DispatchAsync(HttpContext context, HoardOwnedRoute route, HoardLifecycleCoordinator coordinator)
    {
        var activity = coordinator.TryAdmit(route.ModuleId);
        if (activity is null)
        {
            context.Response.StatusCode = StatusCodes.Status503ServiceUnavailable;
            await context.Response.WriteAsync("Hoard module traffic is not admitted.").ConfigureAwait(false);
            return;
        }
        context.Response.OnCompleted(() => { activity.Dispose(); return Task.CompletedTask; });
        await route.Handler(context).ConfigureAwait(false);
    }
}
