using System.Net;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using Hoard.Application.Discovery;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryKestrelAdapterTests
{
    private sealed class ForwardingFilter : IStartupFilter
    {
        public Action<IApplicationBuilder> Configure(Action<IApplicationBuilder> next) => app =>
        { app.UseForwardedHeaders(); next(app); };
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Raw_peer_precedes_existing_forwarding_filters_regardless_of_opt_in_order(bool registerFirst)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
        web.Logging.ClearProviders();
        web.WebHost.UseUrls("http://127.0.0.1:0").PreferHostingUrls(true);
        web.Services.Configure<ForwardedHeadersOptions>(options =>
        {
            options.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
            options.ForwardLimit = 1;
            options.KnownProxies.Clear();
            options.KnownIPNetworks.Clear();
            options.KnownProxies.Add(IPAddress.Loopback);
        });
        web.Services.AddAuthentication("fixture").AddScheme<AuthenticationSchemeOptions, DiscoveryAuthorizationTests.FixtureAuthentication>("fixture", _ => { });
        web.Services.AddAuthorization(options => options.AddPolicy("Hoard.Management.Read", policy => policy.RequireClaim("read", "yes")));
        if (registerFirst) { web.Services.AddSingleton<IStartupFilter, ForwardingFilter>(); }
        var builder = DiscoveryFixtures.Registry(web.Services, options: new()
        { Exposure = HoardDiscoveryExposure.SecuredNetwork, TrustedProxyTlsTermination = true });
        if (!registerFirst) { web.Services.AddSingleton<IStartupFilter, ForwardingFilter>(); }
        await using var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.MapHoardDiscovery(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync().WaitAsync(TimeSpan.FromSeconds(5));
        var address = app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.Single();
        using var client = new HttpClient { BaseAddress = new(address), Timeout = TimeSpan.FromSeconds(5) };
        client.DefaultRequestHeaders.Add("X-Fixture-Identity", "read");
        client.DefaultRequestHeaders.Add("X-Forwarded-For", "192.0.2.1");
        client.DefaultRequestHeaders.Add("X-Forwarded-Proto", "https");
        using var response = await client.GetAsync("/api/v1/discovery");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Actual_loopback_binding_and_pinned_TLS_are_verified_without_a_public_listener(bool tls)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        using var key = RSA.Create(2048);
        var request = new CertificateRequest("CN=localhost", key, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        var alternative = new SubjectAlternativeNameBuilder();
        alternative.AddIpAddress(IPAddress.Loopback);
        request.CertificateExtensions.Add(alternative.Build());
        using var certificate = request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1), DateTimeOffset.UtcNow.AddMinutes(5));
        var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
        web.Logging.ClearProviders();
        web.WebHost.UseUrls($"{(tls ? "https" : "http")}://127.0.0.1:0").PreferHostingUrls(true);
        if (tls) { web.WebHost.ConfigureKestrel(server => server.ConfigureHttpsDefaults(https => https.ServerCertificate = certificate)); }
        web.Services.AddAuthentication("fixture").AddScheme<AuthenticationSchemeOptions, DiscoveryAuthorizationTests.FixtureAuthentication>("fixture", _ => { });
        web.Services.AddAuthorization(authorization => authorization.AddPolicy("Hoard.Management.Read",
            policy => { if (tls) { policy.RequireClaim("read", "yes"); } else { policy.RequireAssertion(_ => true); } }));
        var options = new HoardDiscoveryOptions
        { Exposure = tls ? HoardDiscoveryExposure.SecuredNetwork : HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = !tls };
        var builder = DiscoveryFixtures.Registry(web.Services, options: options);
        var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!);
        await using (lease)
        {
            var app = await web.BuildHoardApplicationAsync(lease);
            app.MapHoardDiscovery(lease);
            await app.MapHoardModulesAsync(lease);
            var adapter = app.Services.GetRequiredService<IDiscoveryExposureAdapter>();
            Assert.False(adapter.Verified);
            await app.StartAsync().WaitAsync(TimeSpan.FromSeconds(5));
            Assert.True(adapter.Verified);
            var address = Assert.Single(app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses);
            using var handler = new HttpClientHandler
            {
                ServerCertificateCustomValidationCallback = (_, actual, _, _) =>
                    actual is not null && actual.RawData.AsSpan().SequenceEqual(certificate.RawData)
            };
            using var client = new HttpClient(handler) { BaseAddress = new(address), Timeout = TimeSpan.FromSeconds(5) };
            if (tls) { client.DefaultRequestHeaders.Add("X-Fixture-Identity", "read"); }
            Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/api/v1/discovery")).StatusCode);
            Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/api/v1/discovery/openapi.json")).StatusCode);
            client.DefaultRequestHeaders.Add("X-Forwarded-Proto", "https");
            Assert.Equal(HttpStatusCode.Forbidden, (await client.GetAsync("/api/v1/discovery")).StatusCode);
        }
    }

    [Theory]
    [InlineData("http://0.0.0.0:0")]
    [InlineData("http://[::]:0")]
    [InlineData("http://192.0.2.1:0")]
    public async Task Known_invalid_local_bindings_reject_before_any_socket_is_opened(string binding)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var web = WebApplication.CreateBuilder(new WebApplicationOptions { Args = [] });
        web.Logging.ClearProviders();
        web.WebHost.UseUrls(binding).PreferHostingUrls(true);
        web.Services.AddAuthorization(authorization =>
            authorization.AddPolicy("Hoard.Management.Read", policy => policy.RequireAssertion(_ => true)));
        var builder = DiscoveryFixtures.Registry(web.Services, options: new()
        { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true });
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!);
        var error = await Assert.ThrowsAsync<HoardLifecycleException>(() => web.BuildHoardApplicationAsync(lease));
        Assert.DoesNotContain(binding, System.Text.Json.JsonSerializer.Serialize(error.Diagnostics));
        Assert.False(lease.Lifecycle.Snapshot.StartupAdmission);
    }
}
