using System.Net;
using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Hoard.Composition.Tests;

public class EnabledDisabledLifecycleTests
{
    [Fact]
    public async Task Live_concurrent_host_returns_503_until_complete_readiness_then_serves_and_blocks_after_stop()
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        web.Services.Configure<HostOptions>(options => options.ServicesStartConcurrently = true);
        var builder = LifecycleFixtures.Registry(web.Services)
            .AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
            { Endpoints = [new() { Id = "test", Description = "Fixture" }] })
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        LifecycleFixtures.For("metadata").Readiness = async _ => { entered.SetResult(); await release.Task; return new(true, []); };
        LifecycleFixtures.For("protocol").Map = routes =>
            routes.Map("test", "/fixture", ["GET"], context => context.Response.WriteAsync("fixture"));
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        var start = app.StartAsync();
        HttpClient? client = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await LifecycleTestHarness.Until(() =>
            {
                try { client = app.GetTestClient(); return true; }
                catch (InvalidOperationException) when (!start.IsCompleted) { return false; }
            });
            using var blocked = await client!.GetAsync("/fixture").WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(HttpStatusCode.ServiceUnavailable, blocked.StatusCode);
            Assert.DoesNotContain("worker", LifecycleFixtures.For("protocol").Calls);
            release.SetResult();
            await start.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal("fixture", await client.GetStringAsync("/fixture"));
            await lease.Lifecycle.StopAsync();
            using var stopped = await client.GetAsync("/fixture");
            Assert.Equal(HttpStatusCode.ServiceUnavailable, stopped.StatusCode);
        }
        finally
        {
            release.TrySetResult();
            await start.WaitAsync(TimeSpan.FromSeconds(5));
            client?.Dispose();
        }
        await app.StopHoardApplicationAsync(lease);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task Only_selected_ready_protocol_dispatches_owned_handler_and_worker(bool enabled)
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var declaration = LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        { Endpoints = [new() { Id = "test", Description = "Lifecycle only" }] };
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(declaration)
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        LifecycleFixtures.For("protocol").Map = routes => routes.Map("test", "/fixture", ["GET"],
            context => context.Response.WriteAsync("fixture"));
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection(enabled ? ["protocol"] : []), LifecycleFixtures.Versions, new()).Composition!;
        await using var lease = await builder.ComposeHoardModulesAsync(composition);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        using var client = app.GetTestClient();
        var response = await client.GetAsync("/fixture");
        Assert.Equal(enabled ? HttpStatusCode.OK : HttpStatusCode.NotFound, response.StatusCode);
        if (!enabled)
        {
            Assert.Equal(0, LifecycleFixtures.For("protocol").Constructors);
            Assert.Empty(LifecycleFixtures.For("protocol").Calls);
        }
        await app.StopHoardApplicationAsync(lease);
    }
}
