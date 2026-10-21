using System.Net;
using Hoard.Hosting.Discovery;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryExposureTests
{
    [Theory]
    [InlineData(null, false, false)]
    [InlineData("192.0.2.1", false, false)]
    [InlineData("127.0.0.1", true, false)]
    [InlineData("127.0.0.1", false, true)]
    public async Task Local_posture_policy_uses_the_raw_peer_not_rewritten_connection_state(string? peer, bool forwarded, bool allowed)
    {
        var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
        web.Logging.ClearProviders();
        await using var app = web.Build();
        var server = app.Services.GetRequiredService<IServer>();
        server.Features.Get<IServerAddressesFeature>()!.Addresses.Add("http://127.0.0.1:12345");
        var adapter = new KestrelDiscoveryExposureAdapter(server, new()
        { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true }, Options.Create(new ForwardedHeadersOptions()));
        var context = new DefaultHttpContext();
        context.Connection.RemoteIpAddress = IPAddress.Loopback;
        context.Features.Set(new DiscoveryRawPeer(peer is null ? null : IPAddress.Parse(peer), false, forwarded, null));
        Assert.Equal(allowed, adapter.Allows(context));
    }

    [Theory]
    [InlineData("127.0.0.1", "https", true, true)]
    [InlineData("192.0.2.1", "https", true, false)]
    [InlineData("127.0.0.1", "https,http", true, false)]
    [InlineData("127.0.0.1", "https", false, false)]
    public async Task Trusted_proxy_requires_known_immediate_peer_single_protocol_and_actual_forwarding_result(
        string peer, string protocol, bool resultingHttps, bool allowed)
    {
        var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
        web.Logging.ClearProviders();
        await using var app = web.Build();
        var server = app.Services.GetRequiredService<IServer>();
        server.Features.Get<IServerAddressesFeature>()!.Addresses.Add("http://127.0.0.1:12345");
        var proxy = new ForwardedHeadersOptions { ForwardLimit = 1, ForwardedHeaders = ForwardedHeaders.XForwardedProto };
        proxy.KnownProxies.Clear();
        proxy.KnownIPNetworks.Clear();
        proxy.KnownProxies.Add(IPAddress.Loopback);
        var adapter = new KestrelDiscoveryExposureAdapter(server, new()
        { Exposure = HoardDiscoveryExposure.SecuredNetwork, TrustedProxyTlsTermination = true }, Options.Create(proxy));
        var context = new DefaultHttpContext();
        context.Request.Scheme = resultingHttps ? "https" : "http";
        context.Features.Set(new DiscoveryRawPeer(IPAddress.Parse(peer), false, true, protocol));
        Assert.Equal(allowed, adapter.Allows(context));
    }
}
