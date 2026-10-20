using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Hoard.Composition.Tests;

public class WorkerAdmissionTests
{
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
        var builder = LifecycleFixtures.Registry(web.Services);
        await using var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
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
