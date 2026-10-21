using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Hoard.Composition.Tests;

public class WorkerAdmissionTests
{
    [Fact]
    public async Task Held_worker_fault_notification_keeps_snapshot_and_stop_bounded_by_the_original_deadline()
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var fail = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var finished = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        LifecycleFixtures.For("artifact").Worker = async _ => { await fail.Task; throw new InvalidOperationException("seeded-secret"); };
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection(),
            LifecycleFixtures.Versions, new() { ShutdownTimeout = TimeSpan.FromMilliseconds(200) }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        using var notification = app.Services.GetRequiredService<IHostApplicationLifetime>().ApplicationStopping.Register(() =>
        {
            entered.SetResult();
            release.Task.GetAwaiter().GetResult();
            finished.SetResult();
        });
        Task<HoardLifecycleSnapshot>? snapshot = null;
        Task<HoardStopResult>? stopping = null;
        try
        {
            fail.SetResult();
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            snapshot = Task.Run(() => lease.Lifecycle.Snapshot);
            stopping = Task.Run(() => lease.Lifecycle.StopAsync());
            var state = await snapshot.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.False(state.Ready);
            Assert.False(state.StartupAdmission);
            await LifecycleTestHarness.Until(() => clock.NextDelay == TimeSpan.FromMilliseconds(200));
            clock.Advance(TimeSpan.FromMilliseconds(199));
            Assert.False(stopping.IsCompleted);
            clock.Advance(TimeSpan.FromMilliseconds(1));
            var result = await stopping.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(HoardRootDisposalOutcome.NotAttemptedUnsafe, result.RootDisposal);
            Assert.Contains(result.Diagnostics, item => item.RuleCode == "WorkerFailure" && !item.Cleanup);
            Assert.Contains(result.Diagnostics, item => item.RuleCode == "Timeout" && item.Cleanup);
            LifecycleFixtures.AssertSafe(result.Diagnostics);
        }
        finally
        {
            fail.TrySetResult();
            release.TrySetResult();
            await finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            if (snapshot is not null) { await snapshot.WaitAsync(TimeSpan.FromSeconds(5)); }
            if (stopping is not null) { await stopping.WaitAsync(TimeSpan.FromSeconds(5)); }
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            try { await lease.DisposeAsync(); }
            catch (HoardLifecycleException) when (lease.StopResult?.RootDisposal == HoardRootDisposalOutcome.NotAttemptedUnsafe) { }
        }
    }

    [Fact]
    public async Task Worker_is_admitted_once_after_complete_readiness_and_fault_closes_admission()
    {
        LifecycleFixtures.Reset();
        var initializing = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var ready = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var worker = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var fail = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        LifecycleFixtures.For("metadata").Initialize = async _ => { initializing.SetResult(); await ready.Task; };
        LifecycleFixtures.For("artifact").Worker = async _ => { worker.SetResult(); await fail.Task; throw new InvalidOperationException("seeded-secret"); };
        var web = LifecycleFixtures.WebBuilder();
        var resource = new LifecycleCleanupTests.DisposalProbe();
        web.Services.AddSingleton(_ => resource);
        var builder = LifecycleFixtures.Registry(web.Services);
        await using var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<LifecycleCleanupTests.DisposalProbe>();
        await app.MapHoardModulesAsync(lease);
        var notifications = 0;
        using var notification = app.Services.GetRequiredService<IHostApplicationLifetime>().ApplicationStopping.Register(() =>
            Interlocked.Increment(ref notifications));
        var start = app.StartAsync();
        try
        {
            await initializing.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.False(worker.Task.IsCompleted);
            Assert.False(lease.Lifecycle.Snapshot.StartupAdmission);
            Assert.Null(lease.Coordinator.TryAdmit("artifact"));
            ready.SetResult();
            await start.WaitAsync(TimeSpan.FromSeconds(5));
            await worker.Task.WaitAsync(TimeSpan.FromSeconds(5));
            fail.SetResult();
            await LifecycleTestHarness.Until(() => lease.Lifecycle.Snapshot.Diagnostics.Any(item => item.RuleCode == "WorkerFailure"));
            Assert.False(lease.Lifecycle.Snapshot.Ready);
            LifecycleFixtures.AssertSafe(lease.Lifecycle.Snapshot.Diagnostics);
            Assert.False(lease.Lifecycle.Snapshot.StartupAdmission);
            Assert.Equal(1, LifecycleFixtures.For("artifact").Calls.Count(item => item == "worker"));
            var result = await lease.Lifecycle.StopAsync();
            Assert.All(result.Modules, module => Assert.Equal(HoardCleanupOutcome.Completed, module.Outcome));
            await Task.WhenAll(Enumerable.Range(0, 4).Select(_ => lease.DisposeAsync().AsTask()));
            Assert.True(lease.StopResult!.Complete);
            Assert.Equal(1, notifications);
            Assert.Equal(1, resource.Disposals);
            Assert.All(LifecycleFixtures.Controls.Values, control => Assert.Equal(1, control.Calls.Count(item => item == "stop")));
        }
        finally { ready.TrySetResult(); fail.TrySetResult(); await start.WaitAsync(TimeSpan.FromSeconds(5)); }
    }

    [Fact]
    public async Task Independent_module_hosted_services_are_rejected()
    {
        LifecycleFixtures.Reset();
        LifecycleFixtures.For("artifact").Configure = services => services.AddSingleton<IHostedService, Bypass>();
        var builder = LifecycleFixtures.Registry();
        var result = builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!;
        var error = await Assert.ThrowsAsync<HoardLifecycleException>(() => builder.ComposeHoardModulesAsync(result));
        Assert.Contains(error.Diagnostics, item => item.RuleCode == "IndependentWorker");
        LifecycleFixtures.AssertSafe(error.Diagnostics);
    }

    private sealed class Bypass : IHostedService
    {
        public Task StartAsync(CancellationToken token) => Task.CompletedTask;
        public Task StopAsync(CancellationToken token) => Task.CompletedTask;
    }
}
