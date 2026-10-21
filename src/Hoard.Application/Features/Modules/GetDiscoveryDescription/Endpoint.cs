using Hoard.Application.Discovery;
using Hoard.Hosting.Discovery;
using Microsoft.AspNetCore.Http;

namespace Hoard.Application.Features.Modules.GetDiscoveryDescription;

internal static class Endpoint
{
    internal const string Route = "/api/v1/discovery/openapi.json";
    private static readonly byte[] Description = Load();
    private static byte[] Load()
    {
        using var resource = typeof(Endpoint).Assembly.GetManifestResourceStream("Hoard.Application.Discovery.openapi.json")
            ?? throw new InvalidOperationException("The fixed discovery description is missing.");
        using var buffer = new MemoryStream();
        resource.CopyTo(buffer);
        if (buffer.Length > 4 * 1024 * 1024) { throw new InvalidOperationException("The fixed discovery description exceeds its bound."); }
        return buffer.ToArray();
    }

    internal static Task HandleAsync(HttpContext context, HoardDiscoveryOptions options) =>
        context.Request.QueryString.HasValue
            ? DiscoveryResponseWriter.ProblemAsync(context, 400, "invalid-request", "request",
                "Use the documented literal GET route without query parameters.", Route)
            : DiscoveryResponseWriter.SendAsync(context, options, new(options, context.RequestAborted), () => Description, Route, true);
}
