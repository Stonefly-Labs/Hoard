using Hoard.Abstractions.Modules;
using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Composition.Tests;

public class LifecycleCleanupTests
{
    [Fact]
    public async Task Worker_fault_during_drain_is_reported_before_safe_resource_release()
    {
        LifecycleFixtures.Reset();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        LifecycleFixtures.For("artifact").Worker = async _ =>
        {
            entered.SetResult();
            await release.Task;
            throw new InvalidOperationException("seeded-secret");
        };
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
        var stopping = lease.Lifecycle.StopAsync();
        try
        {
            await LifecycleTestHarness.Until(() => lease.Lifecycle.Snapshot.Phase == HoardLifecyclePhase.Draining);
            release.SetResult();
            var result = await stopping.WaitAsync(TimeSpan.FromSeconds(5));
            var diagnostic = Assert.Single(result.Diagnostics);
            Assert.Equal("LateCallbackFailure", diagnostic.RuleCode);
            Assert.Equal("artifact", diagnostic.ModuleId);
            Assert.Equal(HoardLifecyclePhase.Running, diagnostic.Phase);
            Assert.True(diagnostic.Cleanup);
            Assert.Equal(lease.Lifecycle.Snapshot.CorrelationId, diagnostic.CorrelationId);
            LifecycleFixtures.AssertSafe(result.Diagnostics);
            Assert.All(result.Modules, module => Assert.Equal(HoardCleanupOutcome.Completed, module.Outcome));
            Assert.Empty(result.UnsafeActivities);
            await lease.DisposeAsync();
            Assert.True(lease.StopResult!.Complete);
            Assert.Equal(result.Diagnostics.ToArray(), lease.StopResult.Diagnostics.ToArray());
            Assert.All(LifecycleFixtures.Controls.Values, control => Assert.Equal(1, control.Calls.Count(call => call == "stop")));
        }
        finally
        {
            release.TrySetResult();
            await stopping.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Timed_out_cleanup_reports_eventual_fault_before_independent_cleanup_finishes(bool throwing)
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var independentEntered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var independentRelease = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        LifecycleFixtures.For("protocol").Stop = async token =>
        {
            entered.SetResult();
            await release.Task;
            if (throwing) { throw new InvalidOperationException("seeded-secret", new Exception("seeded-late-secret")); }
            token.ThrowIfCancellationRequested();
        };
        LifecycleFixtures.For("metadata").Stop = async _ => { independentEntered.SetResult(); await independentRelease.Task; };
        var web = LifecycleFixtures.WebBuilder();
        var root = new DisposalProbe();
        web.Services.AddSingleton(_ => root);
        var builder = LifecycleFixtures.Registry(web.Services);
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        { Dependencies = [new() { ModuleId = "artifact", VersionRange = "[0.1.0]", Optional = false, AllowPrerelease = false }] })
            .AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection("protocol"),
            LifecycleFixtures.Versions, new() { ModuleCleanupTimeout = TimeSpan.FromSeconds(1) }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<DisposalProbe>();
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        var stopping = lease.Lifecycle.StopAsync();
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await LifecycleTestHarness.Until(() => clock.NextDelay == TimeSpan.FromSeconds(1));
            clock.Advance(TimeSpan.FromSeconds(1));
            await independentEntered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            release.SetResult();
            await LifecycleTestHarness.Until(() => !lease.Coordinator.Activities.Snapshot().Any(item => item.ModuleId == "protocol"));
            Assert.False(stopping.IsCompleted);
            var snapshot = lease.Lifecycle.Snapshot;
            if (throwing)
            {
                var diagnostic = Assert.Single(snapshot.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
                Assert.Equal("protocol", diagnostic.ModuleId);
                Assert.Equal(HoardLifecyclePhase.CleaningUp, diagnostic.Phase);
                Assert.True(diagnostic.Cleanup);
                Assert.Equal(snapshot.CorrelationId, diagnostic.CorrelationId);
            }
            else { Assert.DoesNotContain(snapshot.Diagnostics, item => item.RuleCode == "LateCallbackFailure"); }
            LifecycleFixtures.AssertSafe(snapshot.Diagnostics);
            independentRelease.SetResult();
            var result = await stopping.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Contains(result.Modules, item => item.ModuleId == "protocol" && item.Outcome == HoardCleanupOutcome.TimedOut);
            Assert.All(result.Modules.Where(item => item.ModuleId != "protocol"), item => Assert.Equal(HoardCleanupOutcome.Completed, item.Outcome));
            Assert.Equal(throwing ? 1 : 0, result.Diagnostics.Count(item => item.RuleCode == "LateCallbackFailure"));
            Assert.Empty(result.UnsafeActivities);
            Assert.Same(result, await lease.Lifecycle.StopAsync());
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            Assert.Equal(HoardRootDisposalOutcome.Completed, lease.StopResult!.RootDisposal);
            Assert.Equal(1, root.Disposals);
            Assert.All(LifecycleFixtures.Controls.Values, control => Assert.Equal(1, control.Calls.Count(call => call == "stop")));
            LifecycleFixtures.AssertSafe(lease.StopResult.Diagnostics);
        }
        finally
        {
            release.TrySetResult();
            independentRelease.TrySetResult();
            await stopping.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Lifetime_cancellation_fault_is_reported_before_successful_resource_release(bool throwing)
    {
        LifecycleFixtures.Reset();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var callbacks = 0;
        CancellationTokenRegistration registration = default;
        LifecycleFixtures.For("artifact").Worker = async token =>
        {
            registration = token.Register(() =>
            {
                Interlocked.Increment(ref callbacks);
                if (throwing) { throw new InvalidOperationException("seeded-secret", new Exception("seeded-late-secret")); }
            });
            entered.SetResult();
            await Task.Delay(Timeout.InfiniteTimeSpan, token);
        };
        var web = LifecycleFixtures.WebBuilder();
        var resource = new DisposalProbe();
        web.Services.AddSingleton(_ => resource);
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<DisposalProbe>();
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            var result = await lease.Lifecycle.StopAsync().WaitAsync(TimeSpan.FromSeconds(5));
            Assert.All(result.Modules, module => Assert.Equal(HoardCleanupOutcome.Completed, module.Outcome));
            Assert.Empty(result.UnsafeActivities);
            Assert.Equal(HoardRootDisposalOutcome.NotAttemptedOwnerPending, result.RootDisposal);
            if (throwing)
            {
                var diagnostic = Assert.Single(result.Diagnostics);
                Assert.Equal("CancellationFailure", diagnostic.RuleCode);
                Assert.Equal("composition", diagnostic.ModuleId);
                Assert.Equal(HoardLifecyclePhase.Stopping, diagnostic.Phase);
                Assert.True(diagnostic.Cleanup);
                Assert.Equal(lease.Lifecycle.Snapshot.CorrelationId, diagnostic.CorrelationId);
                LifecycleFixtures.AssertSafe(result.Diagnostics);
            }
            else { Assert.Empty(result.Diagnostics); }
            await lease.DisposeAsync();
            Assert.True(lease.StopResult!.Complete);
            Assert.Equal(result.Diagnostics.ToArray(), lease.StopResult.Diagnostics.ToArray());
            Assert.Same(result, await lease.Lifecycle.StopAsync());
            await lease.DisposeAsync();
            Assert.Equal(1, callbacks);
            Assert.Equal(1, resource.Disposals);
            Assert.All(LifecycleFixtures.Controls.Values, control => Assert.Equal(1, control.Calls.Count(call => call == "stop")));
            Assert.DoesNotContain("seeded-secret", System.Text.Json.JsonSerializer.Serialize(lease.Lifecycle.Snapshot));
        }
        finally
        {
            await lease.DisposeAsync();
            registration.Dispose();
        }
    }

    [Theory]
    [InlineData("middleware", false)]
    [InlineData("middleware", true)]
    [InlineData("filter", false)]
    [InlineData("filter", true)]
    [InlineData("handler", false)]
    [InlineData("handler", true)]
    public async Task Response_completion_retains_owner_prerequisite_and_root_after_drain_expiry(string registration, bool handledError)
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var finished = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var web = LifecycleFixtures.WebBuilder();
        var root = new DisposalProbe();
        web.Services.AddSingleton(_ => root);
        var completions = 0;
        async Task CompleteAsync()
        {
            Interlocked.Increment(ref completions);
            entered.SetResult();
            await release.Task;
            finished.SetResult();
        }
        if (registration == "filter") { web.Services.AddSingleton<IStartupFilter>(new CompletionFilter(CompleteAsync)); }
        var builder = LifecycleFixtures.Registry(web.Services);
        builder.AddModule<LifecycleFixtures.ProtocolProvider>(LifecycleFixtures.Declaration("protocol", ModuleCategory.Protocol) with
        {
            Endpoints = [new() { Id = "test", Description = "Fixture" }],
            Dependencies = [new() { ModuleId = "artifact", VersionRange = "[0.1.0]", Optional = false, AllowPrerelease = false }]
        }).AddModuleLifecycle<LifecycleFixtures.ProtocolProvider, LifecycleFixtures.ProtocolModule>();
        LifecycleFixtures.For("protocol").Map = routes => routes.Map("test", "/fixture", ["GET"], context =>
        {
            if (registration == "handler") { context.Response.OnCompleted(CompleteAsync); }
            if (handledError) { throw new InvalidOperationException("Fixture handled failure."); }
            return context.Response.WriteAsync("Fixture response.");
        });
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection("protocol"), LifecycleFixtures.Versions,
            new() { DrainTimeout = TimeSpan.FromSeconds(1) }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<DisposalProbe>();
        app.Use(async (context, next) =>
        {
            if (registration == "middleware") { context.Response.OnCompleted(CompleteAsync); }
            try { await next(context); }
            catch (InvalidOperationException) { context.Response.StatusCode = 500; }
        });
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        using var client = app.GetTestClient();
        var response = client.GetAsync("/fixture");
        Task<HoardStopResult>? stop = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            stop = lease.Lifecycle.StopAsync();
            await LifecycleTestHarness.Until(() => clock.NextDelay == TimeSpan.FromSeconds(1)
                && !lease.Coordinator.Activities.Snapshot().Any(activity => activity.ModuleId == "composition"));
            clock.Advance(TimeSpan.FromSeconds(1));
            var result = await stop.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(TimeSpan.FromSeconds(29), lease.Coordinator.ShutdownDeadline!.Remaining);
            Assert.Contains(result.Modules, module => module.ModuleId == "protocol" && module.Outcome == HoardCleanupOutcome.UnsafePendingCallback);
            Assert.Contains(result.Modules, module => module.ModuleId == "artifact" && module.Outcome == HoardCleanupOutcome.UnsafePendingCallback);
            Assert.Contains(result.Modules, module => module.ModuleId == "metadata" && module.Outcome == HoardCleanupOutcome.Completed);
            Assert.Equal(new HoardUnsafeActivity("protocol", HoardActivityKind.Request), Assert.Single(result.UnsafeActivities));
            Assert.Equal(HoardRootDisposalOutcome.NotAttemptedUnsafe, result.RootDisposal);
            LifecycleFixtures.AssertSafe(result.Diagnostics);
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            var frozen = lease.StopResult;
            Assert.Equal(HoardRootDisposalOutcome.NotAttemptedUnsafe, frozen!.RootDisposal);
            release.TrySetResult();
            await finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Same(result, await lease.Lifecycle.StopAsync());
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            Assert.Same(frozen, lease.StopResult);
            Assert.Equal(0, root.Disposals);
            Assert.Equal(1, completions);
            Assert.DoesNotContain("stop", LifecycleFixtures.For("protocol").Calls);
            Assert.DoesNotContain("stop", LifecycleFixtures.For("artifact").Calls);
            Assert.Equal(1, LifecycleFixtures.For("metadata").Calls.Count(call => call == "stop"));
        }
        finally
        {
            release.TrySetResult();
            await finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            using var completedResponse = await response.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(handledError ? 500 : 200, (int)completedResponse.StatusCode);
            if (stop is not null) { await stop.WaitAsync(TimeSpan.FromSeconds(5)); }
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    internal sealed class CompletionFilter(Func<Task> complete) : IStartupFilter
    {
        public Action<IApplicationBuilder> Configure(Action<IApplicationBuilder> next) => app =>
        {
            app.Use(async (context, nextRequest) =>
            {
                context.Response.OnCompleted(complete);
                await nextRequest(context);
            });
            next(app);
        };
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public async Task Timed_out_cleanup_or_worker_retains_its_prerequisite_and_root_but_independent_cleanup_continues(bool worker, bool throwing)
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
            if (throwing) { throw new InvalidOperationException("seeded-late-secret"); }
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
            await LifecycleTestHarness.Until(() => clock.NextDelay == TimeSpan.FromSeconds(1)
                && !lease.Coordinator.Activities.Snapshot().Any(activity => activity.ModuleId == "composition"));
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
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            if (throwing)
            {
                var snapshot = lease.Lifecycle.Snapshot;
                var diagnostic = Assert.Single(snapshot.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
                Assert.Equal("protocol", diagnostic.ModuleId);
                Assert.Equal(worker ? HoardLifecyclePhase.Running : HoardLifecyclePhase.CleaningUp, diagnostic.Phase);
                Assert.True(diagnostic.Cleanup);
                Assert.Equal(snapshot.CorrelationId, diagnostic.CorrelationId);
                LifecycleFixtures.AssertSafe(snapshot.Diagnostics);
                Assert.DoesNotContain(result.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
            }
            else { Assert.DoesNotContain(lease.Lifecycle.Snapshot.Diagnostics, item => item.RuleCode == "LateCallbackFailure"); }
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

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Cleanup_exception_does_not_skip_other_modules_or_safe_root_disposal(bool timeout)
    {
        LifecycleFixtures.Reset();
        LifecycleFixtures.For("metadata").Stop = _ => throw (timeout ? new TimeoutException("seeded-secret") : new InvalidOperationException("seeded-secret"));
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        LifecycleFixtures.For("artifact").Stop = _ => LifecycleTestHarness.Until(() =>
            !lease.Coordinator.Activities.Snapshot().Any(item => item.ModuleId == "metadata"));
        var result = await lease.Lifecycle.StopAsync();
        LifecycleFixtures.AssertSafe(result.Diagnostics);
        Assert.Single(result.Diagnostics, item => item.RuleCode == (timeout ? "Timeout" : "CleanupFailure"));
        Assert.DoesNotContain(result.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
        Assert.Contains(result.Modules, item => item.ModuleId == "metadata"
            && item.Outcome == (timeout ? HoardCleanupOutcome.TimedOut : HoardCleanupOutcome.Failed));
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
