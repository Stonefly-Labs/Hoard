using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Hoard.Composition.Tests;

public class LifecycleOwnershipTests
{
    [Fact]
    public async Task Budget_expiry_between_framework_stop_and_root_dispatch_leaves_disposal_unattempted()
    {
        LifecycleFixtures.Reset();
        var clock = new InterPhaseClock();
        var resource = new LifecycleCleanupTests.DisposalProbe();
        var web = LifecycleFixtures.WebBuilder();
        web.Services.AddSingleton(_ => resource);
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection(),
            LifecycleFixtures.Versions, new() { ShutdownTimeout = TimeSpan.FromSeconds(2) }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<LifecycleCleanupTests.DisposalProbe>();
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        await app.StopHoardApplicationAsync(lease);
        clock.AdvanceAfterRead = TimeSpan.FromSeconds(2);
        await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
        await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
        Assert.Equal(HoardRootDisposalOutcome.NotAttemptedBudgetExhausted, lease.StopResult!.RootDisposal);
        Assert.Equal(0, resource.Disposals);
        var frozen = lease.StopResult;
        await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
        Assert.Same(frozen, lease.StopResult);
        Assert.Equal(0, resource.Disposals);
    }

    private sealed class InterPhaseClock : TimeProvider
    {
        private readonly LifecycleTestTimeProvider clock = new();
        internal TimeSpan AdvanceAfterRead;
        public override long TimestampFrequency => clock.TimestampFrequency;
        public override long GetTimestamp()
        {
            var timestamp = clock.GetTimestamp();
            var advance = AdvanceAfterRead;
            AdvanceAfterRead = TimeSpan.Zero;
            clock.Advance(advance);
            return timestamp;
        }
        public override ITimer CreateTimer(TimerCallback callback, object? state, TimeSpan dueTime, TimeSpan period) =>
            clock.CreateTimer(callback, state, dueTime, period);
    }

    [Theory]
    [InlineData(false, false, true, false)]
    [InlineData(false, true, true, false)]
    [InlineData(false, true, false, false)]
    [InlineData(true, false, true, false)]
    [InlineData(true, true, true, false)]
    [InlineData(true, true, false, false)]
    [InlineData(false, false, true, true)]
    [InlineData(true, false, true, true)]
    public async Task Framework_stop_and_root_disposal_report_faults_once_before_releasing_activity(bool root, bool held, bool throwing, bool timeout)
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var resource = new FaultingHostResource(root, held, throwing, timeout);
        var web = LifecycleFixtures.WebBuilder();
        web.Services.AddSingleton(_ => resource);
        if (!root) { web.Services.AddSingleton<IHostedService>(resource); }
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection(),
            LifecycleFixtures.Versions, new() { ShutdownTimeout = TimeSpan.FromSeconds(2) }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<FaultingHostResource>();
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        var disposal = lease.DisposeAsync().AsTask();
        try
        {
            await resource.Entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            if (held)
            {
                await LifecycleTestHarness.Until(() => clock.NextDelay == TimeSpan.FromSeconds(2));
                clock.Advance(TimeSpan.FromSeconds(2));
            }
            await Assert.ThrowsAsync<HoardLifecycleException>(() => disposal.WaitAsync(TimeSpan.FromSeconds(5)));
            var frozen = lease.StopResult;
            Assert.Equal(root ? held || timeout ? HoardRootDisposalOutcome.TimedOut : HoardRootDisposalOutcome.Failed
                : HoardRootDisposalOutcome.NotAttemptedUnsafe, frozen!.RootDisposal);
            if (held) { Assert.DoesNotContain(frozen.Diagnostics, item => item.RuleCode == "LateCallbackFailure"); }
            resource.Release.TrySetResult();
            await resource.Finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            var snapshot = lease.Lifecycle.Snapshot;
            var code = held ? "LateCallbackFailure" : timeout ? "Timeout" : root ? "RootDisposalFailure" : "HostStopFailure";
            if (throwing)
            {
                var diagnostic = Assert.Single(snapshot.Diagnostics, item => item.RuleCode == code);
                Assert.Equal("composition", diagnostic.ModuleId);
                Assert.Equal(root ? HoardLifecyclePhase.CleaningUp : HoardLifecyclePhase.Stopping, diagnostic.Phase);
                Assert.True(diagnostic.Cleanup);
                Assert.Equal(snapshot.CorrelationId, diagnostic.CorrelationId);
                Assert.Single(snapshot.Diagnostics, item => item.RuleCode is "LateCallbackFailure" or "RootDisposalFailure" or "HostStopFailure"
                    || timeout && item.RuleCode == "Timeout");
            }
            else { Assert.DoesNotContain(snapshot.Diagnostics, item => item.RuleCode == "LateCallbackFailure"); }
            LifecycleFixtures.AssertSafe(snapshot.Diagnostics);
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            Assert.Same(frozen, lease.StopResult);
            Assert.Equal(1, resource.Attempts);
            Assert.All(LifecycleFixtures.Controls.Values, control => Assert.Equal(1, control.Calls.Count(call => call == "stop")));
            if (held) { Assert.DoesNotContain(frozen.Diagnostics, item => item.RuleCode == "LateCallbackFailure"); }
        }
        finally
        {
            resource.Release.TrySetResult();
            await resource.Finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    private sealed class FaultingHostResource(bool root, bool held, bool throwing, bool timeout) : IHostedService, IAsyncDisposable
    {
        internal int Attempts;
        internal readonly TaskCompletionSource Entered = new(TaskCreationOptions.RunContinuationsAsynchronously);
        internal readonly TaskCompletionSource Release = new(TaskCreationOptions.RunContinuationsAsynchronously);
        internal readonly TaskCompletionSource Finished = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public Task StartAsync(CancellationToken token) => Task.CompletedTask;
        public Task StopAsync(CancellationToken token) => root ? Task.CompletedTask : InvokeAsync();
        public ValueTask DisposeAsync() => root ? new(InvokeAsync()) : ValueTask.CompletedTask;
        private async Task InvokeAsync()
        {
            Interlocked.Increment(ref Attempts);
            Entered.TrySetResult();
            try
            {
                if (held) { await Release.Task; }
                if (throwing)
                {
                    throw timeout ? new TimeoutException("root-secret")
                        : new InvalidOperationException("root-secret", new Exception("seeded-late-secret"));
                }
            }
            finally { Finished.TrySetResult(); }
        }
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public async Task Worker_fault_retains_all_resources_for_pending_host_notification_or_cancellation(bool cancellation, bool throwing)
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var fail = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var finished = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var web = LifecycleFixtures.WebBuilder();
        var resource = new LifecycleCleanupTests.DisposalProbe();
        web.Services.AddSingleton(_ => resource);
        var notifications = 0;
        var cancellations = 0;
        void Hold()
        {
            entered.SetResult();
            release.Task.GetAwaiter().GetResult();
            Assert.Equal(0, resource.Disposals);
            Assert.All(LifecycleFixtures.Controls.Values, control => Assert.DoesNotContain("stop", control.Calls));
            finished.SetResult();
            if (throwing) { throw new InvalidOperationException("seeded-late-secret"); }
        }
        CancellationTokenRegistration registration = default;
        LifecycleFixtures.For("artifact").Worker = async token =>
        {
            registration = token.Register(() => { Interlocked.Increment(ref cancellations); if (cancellation) { Hold(); } });
            await fail.Task;
            throw new InvalidOperationException("seeded-secret");
        };
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection(),
            LifecycleFixtures.Versions, new() { ShutdownTimeout = TimeSpan.FromSeconds(10), DrainTimeout = TimeSpan.FromSeconds(1) }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        app.Services.GetRequiredService<LifecycleCleanupTests.DisposalProbe>();
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        using var notification = app.Services.GetRequiredService<IHostApplicationLifetime>().ApplicationStopping.Register(() =>
        {
            Interlocked.Increment(ref notifications);
            if (!cancellation) { Hold(); }
        });
        Task<HoardStopResult>? stopping = null;
        try
        {
            fail.SetResult();
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            stopping = Task.Run(() => lease.Lifecycle.StopAsync());
            await LifecycleTestHarness.Until(() => clock.NextDelay == TimeSpan.FromSeconds(1));
            clock.Advance(TimeSpan.FromSeconds(1));
            var result = await stopping.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(TimeSpan.FromSeconds(9), lease.Coordinator.ShutdownDeadline!.Remaining);
            Assert.All(result.Modules, module => Assert.Equal(HoardCleanupOutcome.UnsafePendingCallback, module.Outcome));
            Assert.Contains(result.UnsafeActivities, activity => activity.ModuleId == "composition" && activity.Kind == HoardActivityKind.Phase);
            Assert.Equal(HoardRootDisposalOutcome.NotAttemptedUnsafe, result.RootDisposal);
            Assert.Single(result.Diagnostics, item => item.RuleCode == "WorkerFailure" && !item.Cleanup);
            Assert.Contains(result.Diagnostics, item => item.RuleCode == "UnsafePendingCallback" && item.Cleanup);
            Assert.DoesNotContain(result.Diagnostics, item => item.RuleCode == "CancellationFailure");
            LifecycleFixtures.AssertSafe(result.Diagnostics);
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            var frozen = lease.StopResult;
            Assert.Equal(HoardRootDisposalOutcome.NotAttemptedUnsafe, frozen!.RootDisposal);
            release.SetResult();
            await finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            var snapshot = lease.Lifecycle.Snapshot;
            if (throwing)
            {
                var diagnostic = Assert.Single(snapshot.Diagnostics, item => item.RuleCode == "CancellationFailure");
                Assert.Equal("composition", diagnostic.ModuleId);
                Assert.Equal(HoardLifecyclePhase.Stopping, diagnostic.Phase);
                Assert.True(diagnostic.Cleanup);
                Assert.Equal(snapshot.CorrelationId, diagnostic.CorrelationId);
            }
            else { Assert.DoesNotContain(snapshot.Diagnostics, item => item.RuleCode == "CancellationFailure"); }
            Assert.Single(snapshot.Diagnostics, item => item.RuleCode == "WorkerFailure" && !item.Cleanup);
            LifecycleFixtures.AssertSafe(snapshot.Diagnostics);
            Assert.DoesNotContain(frozen.Diagnostics, item => item.RuleCode == "CancellationFailure");
            Assert.Same(result, await lease.Lifecycle.StopAsync());
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            Assert.Same(frozen, lease.StopResult);
            Assert.Equal(1, notifications);
            Assert.Equal(1, cancellations);
            Assert.Equal(0, resource.Disposals);
            Assert.All(LifecycleFixtures.Controls.Values, control => Assert.DoesNotContain("stop", control.Calls));
        }
        finally
        {
            fail.TrySetResult();
            release.TrySetResult();
            await finished.Task.WaitAsync(TimeSpan.FromSeconds(5));
            if (stopping is not null) { await stopping.WaitAsync(TimeSpan.FromSeconds(5)); }
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            registration.Dispose();
        }
    }

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
