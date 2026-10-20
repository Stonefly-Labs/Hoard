using System.Text.Encodings.Web;
using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using Microsoft.AspNetCore.Routing.Matching;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Microsoft.Extensions.Primitives;

namespace Hoard.Composition.Tests;

public class OwnedRouteTests
{
    [Theory]
    [InlineData("undeclared")]
    [InlineData("missing")]
    [InlineData("order")]
    [InlineData("source")]
    [InlineData("policy")]
    public async Task Unsupported_host_matching_and_incomplete_owned_responsibilities_fail_explicitly(string kind)
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        if (kind == "policy") { web.Services.AddSingleton<MatcherPolicy, CustomPolicy>(); }
        var builder = LifecycleFixtures.Registry(web.Services)
            .AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
            { Endpoints = [new() { Id = "test", Description = "Fixture" }] })
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        LifecycleFixtures.For("protocol").Map = routes =>
        {
            if (kind != "missing") { routes.Map(kind == "undeclared" ? "unknown" : "test", "/fixture", ["GET"], _ => Task.CompletedTask); }
        };
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        if (kind == "order") { app.MapGet("/host", () => "fixture").WithOrder(1); }
        if (kind == "source") { ((IEndpointRouteBuilder)app).DataSources.Add(new CustomSource()); }
        var error = await Assert.ThrowsAsync<HoardLifecycleException>(() => app.MapHoardModulesAsync(lease));
        LifecycleFixtures.AssertSafe(error.Diagnostics);
        Assert.Contains(error.Diagnostics, item => item.RuleCode == (kind == "missing" ? "MissingEndpoint" : "UnsupportedRouteShape"));
        Assert.DoesNotContain("initialize", LifecycleFixtures.For("protocol").Calls);
    }

    private sealed class CustomPolicy : MatcherPolicy { public override int Order => 0; }
    private sealed class CustomSource : EndpointDataSource
    {
        public override IReadOnlyList<Endpoint> Endpoints => [];
        public override IChangeToken GetChangeToken() => new CancellationChangeToken(CancellationToken.None);
    }

    [Theory]
    [InlineData("/fixture/{id}", "/fixture/{name}", "GET", false)]
    [InlineData("/fixture/{id}", "/FIXTURE/{name}/", "GET", false)]
    [InlineData("/fixture/{id}", "/fixture/{name}", "POST", true)]
    [InlineData("/fixture/{id}", "/fixture/fixed", "GET", true)]
    [InlineData("/fixture/a", "/fixture/b", "GET", true)]
    [InlineData("/fixture/{id:int}", "/other", "GET", false)]
    [InlineData("/fixture/{id?}", "/other", "GET", false)]
    [InlineData("/fixture/{*path}", "/other", "GET", false)]
    [InlineData("/fixture/x{id}", "/other", "GET", false)]
    [InlineData("/fixture/{id=default}", "/other", "GET", false)]
    [InlineData("/fixture/{id}/{id}", "/other", "GET", false)]
    [InlineData("/fixture", "/fixture", "", false)]
    public async Task Owned_route_gate_rejects_ambiguity_or_unsupported_shape_before_start(
        string first, string second, string method, bool valid)
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        { Endpoints = [new() { Id = "test", Description = "Fixture route" }] })
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        LifecycleFixtures.For("protocol").Map = routes =>
        {
            routes.Map("test", first, ["GET"], _ => Task.CompletedTask);
            routes.Map("test", second, method.Length == 0 ? [] : [method], _ => Task.CompletedTask);
        };
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!;
        var lease = await builder.ComposeHoardModulesAsync(composition);
        var app = await web.BuildHoardApplicationAsync(lease);
        if (valid)
        {
            await app.MapHoardModulesAsync(lease);
            await app.StartAsync();
            await app.StopHoardApplicationAsync(lease);
        }
        else
        {
            var error = await Assert.ThrowsAsync<HoardLifecycleException>(() => app.MapHoardModulesAsync(lease));
            LifecycleFixtures.AssertSafe(error.Diagnostics);
            Assert.DoesNotContain("initialize", LifecycleFixtures.For("protocol").Calls);
        }
        await lease.DisposeAsync();
    }

    [Fact]
    public async Task Disjoint_unowned_host_route_is_preserved()
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.MapGet("/host", () => "host");
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        Assert.Equal("host", await app.GetTestClient().GetStringAsync("/host"));
        await app.StopHoardApplicationAsync(lease);
    }

    [Fact]
    public async Task Ambiguous_unowned_host_route_fails_before_initialization()
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        { Endpoints = [new() { Id = "test", Description = "Fixture" }] })
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        LifecycleFixtures.For("protocol").Map = routes =>
            routes.Map("test", "/fixture/{id}", ["GET"], _ => Task.CompletedTask);
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.MapGet("/fixture/{other}", () => "unowned");
        var error = await Assert.ThrowsAsync<HoardLifecycleException>(() => app.MapHoardModulesAsync(lease));
        Assert.Contains(error.Diagnostics, item => item.RuleCode == "AmbiguousRoute");
        LifecycleFixtures.AssertSafe(error.Diagnostics);
        Assert.DoesNotContain("initialize", LifecycleFixtures.For("protocol").Calls);
    }

    [Fact]
    public async Task Owned_handler_does_not_bypass_host_fallback_authorization_policy()
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        web.Services.AddAuthentication("fixture").AddScheme<AuthenticationSchemeOptions, NoIdentity>("fixture", _ => { });
        web.Services.AddAuthorization(options => options.FallbackPolicy =
            new AuthorizationPolicyBuilder().RequireAuthenticatedUser().Build());
        var builder = LifecycleFixtures.Registry(web.Services);
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        { Endpoints = [new() { Id = "test", Description = "Fixture" }] })
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        var calls = 0;
        LifecycleFixtures.For("protocol").Map = routes =>
            routes.Map("test", "/fixture", ["GET"], _ => { Interlocked.Increment(ref calls); return Task.CompletedTask; });
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.UseAuthentication();
        app.UseAuthorization();
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        using var response = await app.GetTestClient().GetAsync("/fixture");
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Equal(0, calls);
        await app.StopHoardApplicationAsync(lease);
    }

    private sealed class NoIdentity(IOptionsMonitor<AuthenticationSchemeOptions> options,
        ILoggerFactory logger, UrlEncoder encoder) : AuthenticationHandler<AuthenticationSchemeOptions>(options, logger, encoder)
    {
        protected override Task<AuthenticateResult> HandleAuthenticateAsync() => Task.FromResult(AuthenticateResult.NoResult());
    }
}
