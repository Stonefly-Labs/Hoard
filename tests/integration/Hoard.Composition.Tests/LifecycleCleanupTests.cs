using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public class LifecycleCleanupTests
{
    [Fact]
    public async Task Throwing_handler_keeps_ownership_until_its_response_completion_callbacks_finish()
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var finished = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        {
            Endpoints = [new() { Id = "test", Description = "Fixture" }],
            Dependencies = [new() { ModuleId = "artifact", VersionRange = "[0.1.0]", Optional = false, AllowPrerelease = false }]
        }).AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        LifecycleFixtures.For("protocol").Map = routes => routes.Map("test", "/fixture", ["GET"], context =>
        {
            context.Response.OnCompleted(async () => { entered.SetResult(); await release.Task; finished.SetResult(); });
            throw new InvalidOperationException("Fixture handled failure.");
        });
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions,
            new() { DrainTimeout = TimeSpan.FromSeconds(1) }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Use(async (context, next) =>
        {
            try { await next(context); }
            catch (InvalidOperationException) { context.Response.StatusCode = 500; }
        });
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        using var client = app.GetTestClient();
        var response = client.GetAsync("/fixture");
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            var stop = lease.Lifecycle.StopAsync();
            await LifecycleTestHarness.Until(() => lease.Lifecycle.Snapshot.Phase == HoardLifecyclePhase.Draining && clock.PendingTimers > 0);
            clock.Advance(TimeSpan.FromSeconds(1));
            var result = await stop.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Contains(result.Modules, module => module.ModuleId == "protocol" && module.Outcome == HoardCleanupOutcome.UnsafePendingCallback);
            Assert.Contains(result.Modules, module => module.ModuleId == "artifact" && module.Outcome == HoardCleanupOutcome.UnsafePendingCallback);
            Assert.Contains(result.Modules, module => module.ModuleId == "metadata" && module.Outcome == HoardCleanupOutcome.Completed);
            release.TrySetResult();
            await finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Same(result, await lease.Lifecycle.StopAsync());
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
        }
        finally
        {
            release.TrySetResult();
            await finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            using var completedResponse = await response.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Timed_out_cleanup_or_worker_retains_its_prerequisite_and_root_but_independent_cleanup_continues(bool worker)
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var finished = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Func<CancellationToken, Task> pending = async _ =>
        {
            entered.SetResult();
            await release.Task;
            finished.SetResult();
            if (!worker) { throw new InvalidOperationException("seeded-late-secret"); }
        };
        if (worker) { LifecycleFixtures.For("protocol").Worker = pending; }
        else { LifecycleFixtures.For("protocol").Stop = pending; }
        var web = LifecycleFixtures.WebBuilder();
        var root = new DisposalProbe();
        web.Services.AddSingleton(_ => root);
        var builder = LifecycleFixtures.Registry(web.Services);
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        { Dependencies = [new() { ModuleId = "artifact", VersionRange = "[0.1.0]", Optional = false, AllowPrerelease = false }] })
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        var options = new HoardLifecycleOptions
        {
            ShutdownTimeout = TimeSpan.FromSeconds(10),
            DrainTimeout = TimeSpan.FromSeconds(1),
            ModuleCleanupTimeout = TimeSpan.FromSeconds(1)
        };
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions, options, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<DisposalProbe>();
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        if (worker) { await entered.Task.WaitAsync(TimeSpan.FromSeconds(5)); }
        var stopping = lease.Lifecycle.StopAsync();
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await LifecycleTestHarness.Until(() => clock.NextDelay == TimeSpan.FromSeconds(1));
            clock.Advance(TimeSpan.FromSeconds(1));
            var result = await stopping.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Contains(result.Modules, item => item.ModuleId == "protocol"
                && item.Outcome == (worker ? HoardCleanupOutcome.UnsafePendingCallback : HoardCleanupOutcome.TimedOut));
            Assert.Contains(result.Modules, item => item.ModuleId == "artifact" && item.Outcome == HoardCleanupOutcome.UnsafePendingCallback);
            Assert.Contains(result.Modules, item => item.ModuleId == "metadata" && item.Outcome == HoardCleanupOutcome.Completed);
            Assert.Equal(HoardRootDisposalOutcome.NotAttemptedUnsafe, result.RootDisposal);
            Assert.Equal(0, root.Disposals);
            Assert.DoesNotContain("stop", LifecycleFixtures.For("artifact").Calls);
            release.TrySetResult();
            await finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            if (!worker)
            {
                await LifecycleTestHarness.Until(() => lease.Lifecycle.Snapshot.Diagnostics.Any(item => item.RuleCode == "LateCallbackFailure"));
                Assert.DoesNotContain("seeded-late-secret", System.Text.Json.JsonSerializer.Serialize(lease.Lifecycle.Snapshot));
                Assert.DoesNotContain(result.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
            }
            Assert.Same(result, await lease.Lifecycle.StopAsync());
            Assert.Equal(worker ? 0 : 1, LifecycleFixtures.For("protocol").Calls.Count(item => item == "stop"));
            Assert.Equal(0, root.Disposals);
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
        }
        finally
        {
            release.TrySetResult();
            await finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    [Fact]
    public async Task Exhausted_outer_shutdown_budget_explicitly_omits_otherwise_safe_cleanup()
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        LifecycleFixtures.For("metadata").Stop = async _ => { entered.SetResult(); await release.Task; };
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection(),
            LifecycleFixtures.Versions, new() { ShutdownTimeout = TimeSpan.FromSeconds(1) }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        var stop = lease.Lifecycle.StopAsync();
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await LifecycleTestHarness.Until(() => clock.PendingTimers > 0);
            clock.Advance(TimeSpan.FromSeconds(1));
            var result = await stop.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Contains(result.Modules, item => item.ModuleId == "metadata" && item.Outcome == HoardCleanupOutcome.TimedOut);
            Assert.Contains(result.Modules, item => item.ModuleId == "artifact" && item.Outcome == HoardCleanupOutcome.NotAttemptedBudgetExhausted);
            Assert.DoesNotContain("stop", LifecycleFixtures.For("artifact").Calls);
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
        }
        finally
        {
            release.TrySetResult();
            await stop.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    [Fact]
    public async Task Cleanup_exception_does_not_skip_other_modules_or_safe_root_disposal()
    {
        LifecycleFixtures.Reset();
        LifecycleFixtures.For("metadata").Stop = _ => throw new InvalidOperationException("seeded-secret");
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        var result = await lease.Lifecycle.StopAsync();
        LifecycleFixtures.AssertSafe(result.Diagnostics);
        Assert.Contains(result.Modules, item => item.ModuleId == "metadata" && item.Outcome == HoardCleanupOutcome.Failed);
        Assert.Contains(result.Modules, item => item.ModuleId == "artifact" && item.Outcome == HoardCleanupOutcome.Completed);
        await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
        Assert.Equal(HoardRootDisposalOutcome.Completed, lease.StopResult!.RootDisposal);
        Assert.DoesNotContain("seeded-secret", System.Text.Json.JsonSerializer.Serialize(result));
        await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
    }

    internal sealed class DisposalProbe : IDisposable
    {
        internal int Disposals;
        public void Dispose() => Interlocked.Increment(ref Disposals);
    }
}
