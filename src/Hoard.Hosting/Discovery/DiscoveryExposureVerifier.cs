using System.Net;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;

namespace Hoard.Hosting.Discovery;

internal interface IDiscoveryExposureAdapter
{
    bool Verified { get; }
    bool Allows(HttpContext context);
}

internal sealed record DiscoveryRawPeer(IPAddress? Address, bool Https, bool Forwarded, string? ForwardedProto);

internal sealed class KestrelDiscoveryExposureAdapter(IServer server, HoardDiscoveryOptions options,
    IOptions<ForwardedHeadersOptions> forwarding) : IDiscoveryExposureAdapter
{
    private bool ValidAddress(string address) => Uri.TryCreate(address, UriKind.Absolute, out var uri)
        && uri.Scheme is "http" or "https" && string.IsNullOrEmpty(uri.UserInfo)
        && (options.Exposure != HoardDiscoveryExposure.LocalLoopback || Loopback(uri.Host));

    internal static bool Loopback(string host) => host.Equals("localhost", StringComparison.OrdinalIgnoreCase)
        || IPAddress.TryParse(host.Trim('[', ']'), out var address) && IPAddress.IsLoopback(address);

    public bool Verified => server.GetType().Assembly == typeof(KestrelServer).Assembly
        && server.Features.Get<IServerAddressesFeature>() is { Addresses.Count: > 0 } addresses
        && addresses.Addresses.All(ValidAddress);

    public bool Allows(HttpContext context)
    {
        if (context.Features.Get<DiscoveryRawPeer>() is not { Address: { } peer } raw || !Verified) { return false; }
        var proxy = forwarding.Value;
        if (options.Exposure == HoardDiscoveryExposure.LocalLoopback)
        {
            return options.DirectLocalNoProxy && IPAddress.IsLoopback(peer) && !raw.Forwarded
                && proxy.ForwardedHeaders == ForwardedHeaders.None;
        }
        if (options.Exposure != HoardDiscoveryExposure.SecuredNetwork) { return false; }
        if (!raw.Forwarded) { return raw.Https; }
        return options.TrustedProxyTlsTermination && proxy.ForwardLimit == 1
            && proxy.ForwardedHeaders.HasFlag(ForwardedHeaders.XForwardedProto)
            && (proxy.KnownProxies.Contains(peer) || proxy.KnownIPNetworks.Any(network => network.Contains(peer)))
            && raw.ForwardedProto == "https" && context.Request.IsHttps;
    }

    internal void ValidateDeclared(WebApplicationBuilder builder, WebApplication app)
    {
        var proxy = forwarding.Value;
        var declared = builder.WebHost.GetSetting(WebHostDefaults.ServerUrlsKey)?
            .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries) ?? [];
        if (server.GetType().Assembly != typeof(KestrelServer).Assembly
            || declared.Length == 0 || declared.Any(address => !ValidAddress(address))
            || !string.Equals(builder.WebHost.GetSetting(WebHostDefaults.PreferHostingUrlsKey), "true", StringComparison.OrdinalIgnoreCase)
            || builder.WebHost.GetSetting("FORWARDEDHEADERS_ENABLED") is { Length: > 0 } enabled
                && !string.Equals(enabled, "false", StringComparison.OrdinalIgnoreCase))
        { throw new HoardDiscoverySetupException(); }
        if (options.Exposure == HoardDiscoveryExposure.LocalLoopback)
        {
            if (!options.DirectLocalNoProxy || options.TrustedProxyTlsTermination || proxy.ForwardedHeaders != ForwardedHeaders.None)
            { throw new HoardDiscoverySetupException(); }
        }
        else if (options.Exposure == HoardDiscoveryExposure.SecuredNetwork)
        {
            if (options.TrustedProxyTlsTermination)
            {
                if (proxy.ForwardLimit != 1 || !proxy.ForwardedHeaders.HasFlag(ForwardedHeaders.XForwardedProto)
                    || proxy.KnownProxies.Count + proxy.KnownIPNetworks.Count is 0 or > 32)
                { throw new HoardDiscoverySetupException(); }
            }
            else if (declared.Any(address => !address.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
                || proxy.ForwardedHeaders != ForwardedHeaders.None)
            { throw new HoardDiscoverySetupException(); }
        }
        else { throw new HoardDiscoverySetupException(); }
    }
}

internal static class DiscoveryExposureVerifier
{
    internal static async Task ValidateAsync(WebApplicationBuilder builder, WebApplication app, HoardDiscoveryOptions options)
    {
        var policyProvider = app.Services.GetService<IAuthorizationPolicyProvider>();
        if (options.Exposure == HoardDiscoveryExposure.Unconfigured || policyProvider is null)
        { throw new HoardDiscoverySetupException(); }
        var policy = await policyProvider.GetPolicyAsync(options.ManagementReadPolicy).ConfigureAwait(false);
        if (policy is null) { throw new HoardDiscoverySetupException(); }
        if (options.Exposure == HoardDiscoveryExposure.SecuredNetwork)
        {
            if (app.Services.GetService<IAuthenticationService>() is null
                || app.Services.GetService<IAuthenticationSchemeProvider>() is not { } schemes
                || !(await schemes.GetAllSchemesAsync().ConfigureAwait(false)).Any())
            { throw new HoardDiscoverySetupException(); }
            if (policy.AuthenticationSchemes.Count == 0)
            {
                if (await schemes.GetDefaultAuthenticateSchemeAsync().ConfigureAwait(false) is null
                    || await schemes.GetDefaultChallengeSchemeAsync().ConfigureAwait(false) is null
                    || await schemes.GetDefaultForbidSchemeAsync().ConfigureAwait(false) is null)
                { throw new HoardDiscoverySetupException(); }
            }
            foreach (var name in policy.AuthenticationSchemes)
            {
                if (await schemes.GetSchemeAsync(name).ConfigureAwait(false) is null)
                { throw new HoardDiscoverySetupException(); }
            }
        }
        if (app.Services.GetRequiredService<IDiscoveryExposureAdapter>() is KestrelDiscoveryExposureAdapter adapter)
        { adapter.ValidateDeclared(builder, app); }
    }
}
