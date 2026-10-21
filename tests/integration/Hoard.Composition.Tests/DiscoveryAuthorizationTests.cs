using System.Net;
using System.Security.Claims;
using System.Text.Encodings.Web;
using Hoard.Application.Discovery;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryAuthorizationTests
{
    [Theory]
    [InlineData("", 401)]
    [InlineData("denied", 403)]
    [InlineData("read", 200)]
    public async Task Both_literal_routes_require_the_same_policy_without_disclosure(string identity, int status)
    {
        LifecycleFixtures.Reset();
        var executions = 0;
        LifecycleFixtures.For("protocol").Map = routes => routes.Map("inspect", "/fixture-inspect", ["GET"], async context =>
        {
            var authorization = context.RequestServices.GetRequiredService<IAuthorizationService>();
            if (!(await authorization.AuthorizeAsync(context.User, null, "fixture-execute")).Succeeded)
            {
                context.Response.StatusCode = 403;
                return;
            }
            Interlocked.Increment(ref executions);
            await context.Response.WriteAsync("fixture-operation");
        });
        var (app, lease) = await HttpFixture();
        await using (lease)
        {
            await app.StartAsync();
            using var client = app.GetTestClient();
            if (identity.Length != 0) { client.DefaultRequestHeaders.Add("X-Fixture-Identity", identity); }
            foreach (var path in new[] { "/api/v1/discovery", "/api/v1/discovery/openapi.json",
                "/api/v1/discovery/", "/api/v1/discovery/openapi.json/" })
            {
                using var response = await client.GetAsync(path);
                Assert.Equal(status, (int)response.StatusCode);
                Assert.Contains("no-store", response.Headers.CacheControl!.ToString());
                Assert.Equal("nosniff", Assert.Single(response.Headers.GetValues("X-Content-Type-Options")));
                if (status != 200) { Assert.DoesNotContain("discovery-fixture", await response.Content.ReadAsStringAsync()); }
            }
            if (identity == "read")
            {
                Assert.Equal("usable", DiscoveryFixtures.Capability(lease.Discovery!).Availability);
                Assert.Equal(0, executions);
                using var executed = await client.GetAsync("/fixture-inspect");
                Assert.Equal(HttpStatusCode.Forbidden, executed.StatusCode);
                Assert.Equal(0, executions);
                using var request = new HttpRequestMessage(HttpMethod.Get, "/fixture-inspect");
                request.Headers.Add("X-Fixture-Execute", "yes");
                using var permitted = await client.SendAsync(request);
                Assert.Equal(HttpStatusCode.OK, permitted.StatusCode);
                Assert.Equal(1, executions);
            }
        }
    }

    internal static async Task<(WebApplication App, HoardServiceComposition Lease)> HttpFixture(
        HoardDiscoveryCatalog? catalog = null, HoardDiscoveryOptions? options = null, Action<IServiceCollection>? configure = null)
    {
        var web = LifecycleFixtures.WebBuilder();
        web.Services.AddAuthentication("fixture").AddScheme<AuthenticationSchemeOptions, FixtureAuthentication>("fixture", _ => { });
        web.Services.AddAuthorization(authorization =>
        {
            authorization.AddPolicy("Hoard.Management.Read", policy => policy.RequireClaim("read", "yes"));
            authorization.AddPolicy("fixture-execute", policy => policy.RequireClaim("execute", "yes"));
        });
        web.Services.AddSingleton<IDiscoveryExposureAdapter, FixtureExposure>();
        configure?.Invoke(web.Services);
        var builder = DiscoveryFixtures.Registry(web.Services, catalog, options ?? new() { Exposure = HoardDiscoveryExposure.SecuredNetwork });
        var validation = builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new());
        var lease = await builder.ComposeHoardModulesAsync(validation.Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.MapHoardDiscovery(lease);
        await app.MapHoardModulesAsync(lease);
        return (app, lease);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Missing_policy_or_network_authentication_rejects_before_start(bool addPolicy)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var web = LifecycleFixtures.WebBuilder();
        web.Services.AddSingleton<IDiscoveryExposureAdapter, FixtureExposure>();
        web.Services.AddAuthorization(options =>
        {
            if (addPolicy) { options.AddPolicy("Hoard.Management.Read", policy => policy.RequireAssertion(_ => true)); }
        });
        var builder = DiscoveryFixtures.Registry(web.Services, options: new() { Exposure = HoardDiscoveryExposure.SecuredNetwork });
        await using var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!);
        await Assert.ThrowsAsync<HoardLifecycleException>(() => web.BuildHoardApplicationAsync(lease));
        Assert.False(lease.Lifecycle.Snapshot.StartupAdmission);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Multiple_authentication_schemes_need_defaults_or_explicit_read_policy_schemes(bool explicitScheme)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var web = LifecycleFixtures.WebBuilder();
        web.Services.AddAuthentication()
            .AddScheme<AuthenticationSchemeOptions, FixtureAuthentication>("first", _ => { })
            .AddScheme<AuthenticationSchemeOptions, FixtureAuthentication>("second", _ => { });
        web.Services.AddAuthorization(options => options.AddPolicy("Hoard.Management.Read", policy =>
        {
            policy.RequireClaim("read", "yes");
            if (explicitScheme) { policy.AddAuthenticationSchemes("first"); }
        }));
        web.Services.AddSingleton<IDiscoveryExposureAdapter, FixtureExposure>();
        var builder = DiscoveryFixtures.Registry(web.Services, options: new() { Exposure = HoardDiscoveryExposure.SecuredNetwork });
        await using var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!);
        if (!explicitScheme)
        {
            await Assert.ThrowsAsync<HoardLifecycleException>(() => web.BuildHoardApplicationAsync(lease));
            Assert.False(lease.Lifecycle.Snapshot.StartupAdmission);
            return;
        }
        var app = await web.BuildHoardApplicationAsync(lease);
        app.MapHoardDiscovery(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        using var client = app.GetTestClient();
        using var response = await client.GetAsync("/api/v1/discovery");
        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    private sealed class UnverifiedExposure : IDiscoveryExposureAdapter
    {
        public bool Verified => false;
        public bool Allows(HttpContext context) => false;
    }

    [Fact]
    public async Task Unverified_protection_returns_a_closed_503_without_inventory_for_both_routes()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var (app, lease) = await HttpFixture(configure: services =>
            services.AddSingleton<IDiscoveryExposureAdapter, UnverifiedExposure>());
        await using (lease)
        {
            await app.StartAsync();
            using var client = app.GetTestClient();
            foreach (var route in new[] { "/api/v1/discovery", "/api/v1/discovery/openapi.json" })
            {
                using var response = await client.GetAsync(route);
                Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
                var body = await response.Content.ReadAsStringAsync();
                Assert.Contains("invalid-protection", body);
                Assert.DoesNotContain("modules", body);
                Assert.Contains("no-store", response.Headers.CacheControl!.ToString());
            }
        }
    }

    internal sealed class FixtureExposure : IDiscoveryExposureAdapter
    {
        public bool Verified => true;
        public bool Allows(HttpContext context) => true;
    }

    internal sealed class FixtureAuthentication(IOptionsMonitor<AuthenticationSchemeOptions> options,
        ILoggerFactory logger, UrlEncoder encoder) : AuthenticationHandler<AuthenticationSchemeOptions>(options, logger, encoder)
    {
        protected override Task<AuthenticateResult> HandleAuthenticateAsync()
        {
            var identity = Request.Headers["X-Fixture-Identity"].ToString();
            if (identity.Length == 0) { return Task.FromResult(AuthenticateResult.NoResult()); }
            var claims = new List<Claim>();
            if (identity == "read") { claims.Add(new("read", "yes")); }
            if (Request.Headers["X-Fixture-Execute"] == "yes") { claims.Add(new("execute", "yes")); }
            return Task.FromResult(AuthenticateResult.Success(new(new ClaimsPrincipal(new ClaimsIdentity(claims, "fixture")), "fixture")));
        }
    }
}
