using Hoard.Application.Discovery;
using Hoard.Hosting.Discovery;
using Microsoft.AspNetCore.Http;

namespace Hoard.Application.Features.Modules.GetDiscovery;

internal static class Endpoint
{
    internal const string Route = "/api/v1/discovery";
    internal static async Task HandleAsync(HttpContext context, IHoardDiscoverySource source, HoardDiscoveryOptions options)
    {
        if (context.Request.QueryString.HasValue)
        {
            await DiscoveryResponseWriter.ProblemAsync(context, 400, "invalid-request", "request",
                "Use the documented literal GET route without query parameters.", Route).ConfigureAwait(false);
            return;
        }
        var budget = new DiscoveryResponseWriter.Budget(options, context.RequestAborted);
        var captured = source.Capture(context.RequestAborted);
        if (!captured.Success)
        {
            var reason = captured.Failure!;
            if (reason.Code == "cancelled") { context.Abort(); return; }
            await DiscoveryResponseWriter.ProblemAsync(context, 503, reason.Code, "capture",
                reason.CorrectiveAction, Route).ConfigureAwait(false);
            return;
        }
        await DiscoveryResponseWriter.SendAsync(context, options, budget,
            () => Projector.Project(captured.Observation!, budget), Route).ConfigureAwait(false);
    }
}
