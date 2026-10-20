using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Hoard.Composition.Tests;

public class LifecycleOwnershipTests
{
    [Fact]
    public async Task Host_factory_failure_is_sanitized_and_cleans_every_returned_adapter()
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        web.Host.UseServiceProviderFactory(new FailedFactory());
        var builder = LifecycleFixtures.Registry(web.Services);
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var error = await Assert.ThrowsAsync<HoardLifecycleException>(() => web.BuildHoardApplicationAsync(lease));
        LifecycleFixtures.AssertSafe(error.Diagnostics);
        Assert.DoesNotContain("seeded-secret", error.ToString());
        Assert.All(LifecycleFixtures.Controls.Values, control =>
        {
            Assert.DoesNotContain("initialize", control.Calls);
            Assert.Equal(1, control.Calls.Count(item => item == "stop"));
        });
    }

    private sealed class FailedFactory : IServiceProviderFactory<IServiceCollection>
    {
        public IServiceCollection CreateBuilder(IServiceCollection services) => services;
        public IServiceProvider CreateServiceProvider(IServiceCollection services) => throw new InvalidOperationException("seeded-secret");
    }

    [Fact]
    public async Task Concurrent_framework_stop_and_owner_disposal_wait_for_stopped_notifications()
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        var resource = new LifecycleCleanupTests.DisposalProbe();
        web.Services.AddSingleton(_ => resource);
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<LifecycleCleanupTests.DisposalProbe>();
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        using var notification = app.Services.GetRequiredService<IHostApplicationLifetime>().ApplicationStopped.Register(() =>
        {
            entered.SetResult();
            release.Task.GetAwaiter().GetResult();
            Assert.Equal(0, resource.Disposals);
        });
        var stopping = app.StopHoardApplicationAsync(lease);
        Task? disposal = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            disposal = lease.DisposeAsync().AsTask();
            Assert.NotSame(disposal, await Task.WhenAny(disposal, Task.Delay(TimeSpan.FromMilliseconds(100))));
            Assert.Equal(0, resource.Disposals);
        }
        finally
        {
            release.TrySetResult();
            await stopping.WaitAsync(TimeSpan.FromSeconds(5));
            if (disposal is not null) { await disposal.WaitAsync(TimeSpan.FromSeconds(5)); }
            else { await lease.DisposeAsync(); }
        }
        Assert.Equal(1, resource.Disposals);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Root_disposal_failure_or_stall_is_explicit_safe_and_never_retried(bool stall)
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var resource = new RootProbe(stall);
        var web = LifecycleFixtures.WebBuilder();
        web.Services.AddSingleton(_ => resource);
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection(),
            LifecycleFixtures.Versions, new() { ShutdownTimeout = TimeSpan.FromSeconds(2) }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<RootProbe>();
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        await app.StopHoardApplicationAsync(lease);
        var disposal = lease.DisposeAsync().AsTask();
        try
        {
            await resource.Entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            if (stall)
            {
                await LifecycleTestHarness.Until(() => clock.PendingTimers > 0);
                clock.Advance(TimeSpan.FromSeconds(2));
            }
            var error = await Assert.ThrowsAsync<HoardLifecycleException>(() => disposal.WaitAsync(TimeSpan.FromSeconds(5)));
            LifecycleFixtures.AssertSafe(error.Diagnostics);
            Assert.DoesNotContain("root-secret", error.ToString());
            Assert.Equal(stall ? HoardRootDisposalOutcome.TimedOut : HoardRootDisposalOutcome.Failed, lease.StopResult!.RootDisposal);
            var frozen = lease.StopResult;
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            Assert.Equal(frozen, lease.StopResult);
            Assert.Equal(1, resource.Attempts);
        }
        finally
        {
            resource.Release.TrySetResult();
            await resource.Finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    private sealed class RootProbe(bool stall) : IAsyncDisposable
    {
        internal int Attempts;
        internal readonly TaskCompletionSource Entered = new(TaskCreationOptions.RunContinuationsAsynchronously);
        internal readonly TaskCompletionSource Release = new(TaskCreationOptions.RunContinuationsAsynchronously);
        internal readonly TaskCompletionSource Finished = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public async ValueTask DisposeAsync()
        {
            Interlocked.Increment(ref Attempts);
            Entered.TrySetResult();
            try
            {
                if (stall) { await Release.Task; }
                else { throw new InvalidOperationException("root-secret"); }
            }
            finally { Finished.TrySetResult(); }
        }
    }

    [Fact]
    public async Task External_lease_disposes_root_only_after_all_framework_hosted_services_stop()
    {
        LifecycleFixtures.Reset();
        var web = LifecycleFixtures.WebBuilder();
        var resource = new LifecycleCleanupTests.DisposalProbe();
        var hostOwned = new HostOwnedService(resource);
        web.Services.AddSingleton(_ => resource);
        web.Services.AddSingleton<IHostedService>(hostOwned);
        var builder = LifecycleFixtures.Registry(web.Services);
        await using var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<LifecycleCleanupTests.DisposalProbe>();
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        var modules = await lease.Lifecycle.StopAsync();
        Assert.Equal(HoardRootDisposalOutcome.NotAttemptedOwnerPending, modules.RootDisposal);
        Assert.Equal(0, resource.Disposals);
        await app.StopHoardApplicationAsync(lease);
        Assert.Equal(1, hostOwned.Stops);
        Assert.Equal(0, resource.Disposals);
        await Task.WhenAll(Enumerable.Range(0, 4).Select(_ => lease.DisposeAsync().AsTask()));
        Assert.Equal(1, resource.Disposals);
        Assert.True(lease.StopResult!.Complete);
    }

    [Theory]
    [InlineData("map-finalization", true)]
    [InlineData("build", true)]
    [InlineData("map-finalization", false)]
    [InlineData("build", false)]
    public async Task Synchronous_host_work_is_supervised_and_cancellation_or_timeout_cannot_publish_a_late_result(string target, bool cancel)
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var finished = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var web = LifecycleFixtures.WebBuilder();
        if (target == "build") { web.Host.UseServiceProviderFactory(new BlockedFactory(entered, release, finished)); }
        var builder = LifecycleFixtures.Registry(web.Services);
        var options = new HoardLifecycleOptions
        {
            DrainTimeout = TimeSpan.FromSeconds(1),
            ShutdownTimeout = TimeSpan.FromSeconds(10),
            StartupTimeout = TimeSpan.FromSeconds(2),
            ActivationCallbackTimeout = TimeSpan.FromSeconds(2)
        };
        var lease = await builder.ComposeHoardModulesAsync(
            builder.ValidateComposition(LifecycleFixtures.Selection(), LifecycleFixtures.Versions, options, clock).Composition!);
        using var cancellation = new CancellationTokenSource();
        Task operation;
        if (target == "build") { operation = web.BuildHoardApplicationAsync(lease, cancellation.Token); }
        else
        {
            var app = await web.BuildHoardApplicationAsync(lease);
            app.MapGet("/host", () => "fixture").Add(_ =>
            {
                entered.SetResult();
                release.Task.GetAwaiter().GetResult();
                finished.SetResult();
            });
            operation = app.MapHoardModulesAsync(lease, cancellation.Token);
        }
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            if (cancel) { cancellation.Cancel(); }
            else { clock.Advance(TimeSpan.FromSeconds(2)); }
            await LifecycleTestHarness.Until(() => lease.Lifecycle.Snapshot.Phase == HoardLifecyclePhase.Draining
                && clock.NextDelay == TimeSpan.FromSeconds(1));
            clock.Advance(TimeSpan.FromSeconds(1));
            await Assert.ThrowsAsync<HoardLifecycleException>(() => operation.WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.False(lease.Lifecycle.Snapshot.StartupAdmission);
            Assert.Contains(lease.Lifecycle.Snapshot.Diagnostics, item => item.RuleCode == (cancel ? "Cancelled" : "Timeout"));
            Assert.DoesNotContain("initialize", LifecycleFixtures.For("artifact").Calls);
            release.TrySetResult();
            await finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            Assert.Equal(HoardRootDisposalOutcome.NotAttemptedUnsafe, lease.StopResult!.RootDisposal);
        }
        finally
        {
            release.TrySetResult();
            await finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    private sealed class HostOwnedService(LifecycleCleanupTests.DisposalProbe resource) : IHostedService
    {
        internal int Stops;
        public Task StartAsync(CancellationToken token) => Task.CompletedTask;
        public Task StopAsync(CancellationToken token)
        {
            Assert.Equal(0, resource.Disposals);
            Interlocked.Increment(ref Stops);
            return Task.CompletedTask;
        }
    }

    private sealed class BlockedFactory(TaskCompletionSource entered, TaskCompletionSource release,
        TaskCompletionSource finished) : IServiceProviderFactory<IServiceCollection>
    {
        public IServiceCollection CreateBuilder(IServiceCollection services) => services;
        public IServiceProvider CreateServiceProvider(IServiceCollection services)
        {
            entered.SetResult();
            release.Task.GetAwaiter().GetResult();
            var result = new DefaultServiceProviderFactory().CreateServiceProvider(services);
            finished.SetResult();
            return result;
        }
    }
}
