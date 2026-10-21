using System.Diagnostics.Metrics;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;

namespace Hoard.Hosting.Discovery;

internal sealed class DiscoveryRawPeerStartupFilter(IDiscoveryExposureAdapter adapter, HoardDiscoveryOptions options) : IStartupFilter
{
    private static readonly Meter Meter = new("Hoard.Discovery");
    private static readonly Counter<long> Access = Meter.CreateCounter<long>("hoard.discovery.access");
    public Action<IApplicationBuilder> Configure(Action<IApplicationBuilder> next) => app =>
    {
        app.Use(nextRequest => async context =>
        {
            var headers = context.Request.Headers;
            context.Features.Set(new DiscoveryRawPeer(context.Connection.RemoteIpAddress, context.Request.IsHttps,
                headers.Keys.Any(key => key.Equals("Forwarded", StringComparison.OrdinalIgnoreCase)
                    || key.StartsWith("X-Forwarded-", StringComparison.OrdinalIgnoreCase)),
                headers["X-Forwarded-Proto"].Count == 1 ? headers["X-Forwarded-Proto"].ToString() : null));
            var discoveryPath = context.Request.Path.Value?.TrimEnd('/');
            if (string.Equals(discoveryPath, "/api/v1/discovery", StringComparison.OrdinalIgnoreCase)
                || string.Equals(discoveryPath, "/api/v1/discovery/openapi.json", StringComparison.OrdinalIgnoreCase))
            {
                context.Response.Headers.CacheControl = "no-store, private";
                context.Response.Headers.Pragma = "no-cache";
                context.Response.Headers.XContentTypeOptions = "nosniff";
                var failure = !adapter.Verified ? "invalid-protection"
                    : options.Exposure == HoardDiscoveryExposure.LocalLoopback && !adapter.Allows(context) ? "forbidden" : null;
                if (failure is not null)
                {
                    context.Response.StatusCode = failure == "forbidden" ? StatusCodes.Status403Forbidden : StatusCodes.Status503ServiceUnavailable;
                    context.Response.ContentType = "application/problem+json";
                    var reason = new DiscoveryReason(failure);
                    Access.Add(1, new("outcome", "failure"), new("reason", failure), new("phase", "exposure"));
                    await JsonSerializer.SerializeAsync(context.Response.Body, new
                    {
                        type = "about:blank",
                        title = "Discovery unavailable",
                        status = context.Response.StatusCode,
                        detail = reason.CorrectiveAction,
                        code = reason.Code,
                        phase = "exposure",
                        correlationId = Guid.NewGuid()
                    }, cancellationToken: context.RequestAborted).ConfigureAwait(false);
                    return;
                }
                try { await nextRequest(context).ConfigureAwait(false); }
                finally
                {
                    var code = context.RequestAborted.IsCancellationRequested ? "cancelled" : context.Response.StatusCode switch
                    { 200 => "none", 401 => "unauthenticated", 403 => "forbidden", 400 or 405 => "invalid-request", _ => "observation-unavailable" };
                    Access.Add(1, new("outcome", code == "none" ? "success" : "failure"), new("reason", code), new("phase", "authorization"));
                }
                return;
            }
            await nextRequest(context).ConfigureAwait(false);
        });
        next(app);
    };
}
