using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public class SelectedStartupTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Shuffled_registration_preserves_actual_prerequisite_initialization_and_reverse_cleanup(bool reverse)
    {
        LifecycleFixtures.Reset();
        await using var events = new LifecycleTestHarness();
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services)
            .AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
            { Dependencies = [new() { ModuleId = "identity", VersionRange = "[0.1.0]", Optional = true, AllowPrerelease = false }] })
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>()
            .AddModule<LifecycleFixtures.IdentityProvider>(LifecycleFixtures.Declaration("identity", ModuleCategory.Identity))
            .AddModuleLifecycle<LifecycleFixtures.IdentityProvider, LifecycleFixtures.IdentityModule>();
        if (reverse)
        {
            var registrations = web.Services.Where(item => item.ImplementationInstance
                is HoardModuleRegistration or HoardModuleLifecycleRegistration).ToArray();
            foreach (var registration in registrations) { web.Services.Remove(registration); }
            foreach (var registration in registrations.Reverse()) { web.Services.Add(registration); }
        }
        foreach (var id in new[] { "artifact", "metadata", "identity", "protocol" })
        {
            LifecycleFixtures.For(id).Initialize = _ =>
            {
                if (id == "protocol") { Assert.Contains(events.Events, item => item.Id == "identity" && item.Phase == "initialized"); }
                events.Record(id, "initialized");
                return Task.CompletedTask;
            };
            LifecycleFixtures.For(id).Readiness = _ =>
            {
                Assert.Equal(4, events.Events.Count(item => item.Phase == "initialized"));
                return Task.FromResult(new HoardModuleReadiness(true, []));
            };
            LifecycleFixtures.For(id).Stop = _ =>
            {
                if (id == "identity") { Assert.Contains(events.Events, item => item.Id == "protocol" && item.Phase == "stopped"); }
                events.Record(id, "stopped");
                return Task.CompletedTask;
            };
        }
        var composition = builder.ValidateComposition(LifecycleFixtures.Selection("protocol", "identity"),
            LifecycleFixtures.Versions, new()).Composition!;
        await using var lease = await builder.ComposeHoardModulesAsync(composition);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        Assert.Equal(new[] { "artifact", "identity", "metadata", "protocol" },
            events.Events.Where(item => item.Phase == "initialized").Select(item => item.Id));
        await app.StopHoardApplicationAsync(lease);
        Assert.Equal(composition.ActivationOrder.Reverse(),
            events.Events.Where(item => item.Phase == "stopped").Select(item => item.Id));
    }

    [Theory]
    [InlineData("artifact")]
    [InlineData("metadata")]
    public async Task Initialization_failure_at_each_order_position_prevents_later_work_and_cleans_entered_adapters(string failure)
    {
        LifecycleFixtures.Reset();
        LifecycleFixtures.For(failure).Initialize = _ => throw new InvalidOperationException("fixture");
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        Assert.False((await lease.Lifecycle.StartAsync()).Ready);
        Assert.Equal(failure == "metadata", LifecycleFixtures.For("metadata").Calls.Contains("initialize"));
        Assert.All(LifecycleFixtures.Controls.Values, control =>
        {
            Assert.DoesNotContain("worker", control.Calls);
            Assert.Equal(1, control.Calls.Count(item => item == "stop"));
        });
    }

    [Fact]
    public async Task Endpoint_free_selected_modules_initialize_then_become_ready_once()
    {
        LifecycleFixtures.Reset();
        var workers = new[] { "artifact", "metadata" }.ToDictionary(id => id,
            _ => new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously));
        foreach (var (id, entered) in workers)
        {
            LifecycleFixtures.For(id).Worker = _ => { entered.SetResult(); return Task.CompletedTask; };
        }
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var validated = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!;
        await using var lease = await builder.ComposeHoardModulesAsync(validated);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        var lifecycle = app.Services.GetRequiredService<IHoardLifecycle>();
        Assert.False(lifecycle.Snapshot.Ready);
        await app.StartAsync();
        Assert.True(lifecycle.Snapshot.Ready);
        Assert.True((await lifecycle.StartAsync()).Ready);
        await Task.WhenAll(workers.Values.Select(entered => entered.Task)).WaitAsync(TimeSpan.FromSeconds(5));
        foreach (var id in new[] { "artifact", "metadata" })
        {
            Assert.Equal(new[] { "construct", "services", "map", "initialize", "readiness", "worker" },
                LifecycleFixtures.For(id).Calls.ToArray());
        }
        await app.StopHoardApplicationAsync(lease);
        Assert.False(lifecycle.Snapshot.Ready);
        await lease.DisposeAsync();
        Assert.True(lease.StopResult!.Complete);
        Assert.All(LifecycleFixtures.Controls.Values, control => Assert.Equal(1, control.Calls.Count(call => call == "stop")));
    }
}
