using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Builder;

namespace Hoard.Composition.Tests;

public class LifecycleDeadlineTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Timed_out_startup_reports_eventual_fault_without_late_cleanup_or_admission(bool throwing)
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        LifecycleFixtures.For("artifact").Initialize = async token =>
        {
            entered.SetResult();
            await release.Task;
            if (throwing) { throw new InvalidOperationException("seeded-secret", new Exception("seeded-late-secret")); }
            token.ThrowIfCancellationRequested();
        };
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection(),
            LifecycleFixtures.Versions, new()
            {
                StartupTimeout = TimeSpan.FromSeconds(1),
                DrainTimeout = TimeSpan.FromSeconds(1)
            }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        var startup = lease.Lifecycle.StartAsync();
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await LifecycleTestHarness.Until(() => clock.NextDelay == TimeSpan.FromSeconds(1));
            clock.Advance(TimeSpan.FromSeconds(1));
            await LifecycleTestHarness.Until(() => lease.Lifecycle.Snapshot.Phase == HoardLifecyclePhase.Draining
                && clock.NextDelay == TimeSpan.FromSeconds(1));
            clock.Advance(TimeSpan.FromSeconds(1));
            var start = await startup.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.False(start.Ready);
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            var frozen = lease.StopResult;
            release.SetResult();
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            var snapshot = lease.Lifecycle.Snapshot;
            if (throwing)
            {
                var diagnostic = Assert.Single(snapshot.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
                Assert.Equal("artifact", diagnostic.ModuleId);
                Assert.Equal(HoardLifecyclePhase.Initializing, diagnostic.Phase);
                Assert.True(diagnostic.Cleanup);
                Assert.Equal(snapshot.CorrelationId, diagnostic.CorrelationId);
            }
            else { Assert.DoesNotContain(snapshot.Diagnostics, item => item.RuleCode == "LateCallbackFailure"); }
            LifecycleFixtures.AssertSafe(snapshot.Diagnostics);
            Assert.DoesNotContain(start.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
            Assert.DoesNotContain(frozen!.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            Assert.Same(frozen, lease.StopResult);
            Assert.False(snapshot.StartupAdmission);
            Assert.DoesNotContain("initialize", LifecycleFixtures.For("metadata").Calls);
            Assert.DoesNotContain("stop", LifecycleFixtures.For("artifact").Calls);
            Assert.Equal(1, LifecycleFixtures.For("metadata").Calls.Count(call => call == "stop"));
        }
        finally
        {
            release.TrySetResult();
            await startup.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public async Task Timeout_cancellation_reports_additional_fault_before_cleanup_publication(bool cleanup, bool throwing)
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var cancelled = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var independentEntered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var independentRelease = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var callbacks = 0;
        CancellationTokenRegistration registration = default;
        async Task Pending(CancellationToken token)
        {
            registration = token.Register(() =>
            {
                Interlocked.Increment(ref callbacks);
                cancelled.SetResult();
                if (throwing) { throw new InvalidOperationException("seeded-secret", new Exception("seeded-late-secret")); }
            });
            entered.SetResult();
            await release.Task;
        }
        if (cleanup) { LifecycleFixtures.For("metadata").Stop = Pending; }
        else
        {
            LifecycleFixtures.For("metadata").Readiness = async token => { await Pending(token); return new(true, []); };
        }
        LifecycleFixtures.For("artifact").Stop = async _ => { independentEntered.SetResult(); await independentRelease.Task; };
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection(),
            LifecycleFixtures.Versions, new()
            {
                ReadinessTimeout = TimeSpan.FromSeconds(1),
                ModuleCleanupTimeout = TimeSpan.FromSeconds(1)
            }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        if (cleanup) { await app.StartAsync(); }
        var startup = cleanup ? null : lease.Lifecycle.StartAsync();
        var stopping = cleanup ? lease.Lifecycle.StopAsync() : null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await LifecycleTestHarness.Until(() => clock.NextDelay == TimeSpan.FromSeconds(1));
            clock.Advance(TimeSpan.FromSeconds(1));
            await cancelled.Task.WaitAsync(TimeSpan.FromSeconds(5));
            registration.Dispose();
            release.SetResult();
            await independentEntered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await LifecycleTestHarness.Until(() => !lease.Coordinator.Activities.Snapshot().Any(activity => activity.ModuleId == "metadata"));
            var phase = cleanup ? HoardLifecyclePhase.CleaningUp : HoardLifecyclePhase.AssessingReadiness;
            var snapshot = lease.Lifecycle.Snapshot;
            Assert.Single(snapshot.Diagnostics, item => item.RuleCode == "Timeout" && item.ModuleId == "metadata"
                && item.Phase == phase && item.Cleanup == cleanup);
            if (throwing)
            {
                var diagnostic = Assert.Single(snapshot.Diagnostics, item => item.RuleCode == "CancellationFailure");
                Assert.Equal("metadata", diagnostic.ModuleId);
                Assert.Equal(phase, diagnostic.Phase);
                Assert.True(diagnostic.Cleanup);
                Assert.Equal(snapshot.CorrelationId, diagnostic.CorrelationId);
            }
            else { Assert.DoesNotContain(snapshot.Diagnostics, item => item.RuleCode == "CancellationFailure"); }
            LifecycleFixtures.AssertSafe(snapshot.Diagnostics);
            independentRelease.SetResult();
            if (startup is not null) { Assert.False((await startup.WaitAsync(TimeSpan.FromSeconds(5))).Ready); }
            var result = await (stopping ?? lease.Lifecycle.StopAsync()).WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(throwing ? 1 : 0, result.Diagnostics.Count(item => item.RuleCode == "CancellationFailure"));
            Assert.Contains(result.Modules, module => module.ModuleId == "metadata"
                && module.Outcome == (cleanup ? HoardCleanupOutcome.TimedOut : HoardCleanupOutcome.Completed));
            Assert.Contains(result.Modules, module => module.ModuleId == "artifact" && module.Outcome == HoardCleanupOutcome.Completed);
            Assert.Empty(result.UnsafeActivities);
            Assert.Same(result, await lease.Lifecycle.StopAsync());
            if (cleanup) { await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask()); }
            else { await lease.DisposeAsync(); }
            Assert.Equal(HoardRootDisposalOutcome.Completed, lease.StopResult!.RootDisposal);
            Assert.Equal(throwing ? 1 : 0, lease.StopResult.Diagnostics.Count(item => item.RuleCode == "CancellationFailure"));
            Assert.Equal(1, callbacks);
            Assert.All(LifecycleFixtures.Controls.Values, control => Assert.Equal(1, control.Calls.Count(call => call == "stop")));
            Assert.DoesNotContain("seeded-secret", System.Text.Json.JsonSerializer.Serialize(lease.StopResult));
        }
        finally
        {
            release.TrySetResult();
            independentRelease.TrySetResult();
            if (startup is not null) { await startup.WaitAsync(TimeSpan.FromSeconds(5)); }
            await (stopping ?? lease.Lifecycle.StopAsync()).WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
            registration.Dispose();
        }
    }

    [Fact]
    public async Task Long_budgets_propagate_callback_timeout_faults_and_rearm_timer_slices()
    {
        var clock = new LifecycleTestTimeProvider();
        var deadline = new LifecycleDeadline(clock, TimeSpan.FromDays(120));
        await Assert.ThrowsAsync<TimeoutException>(() => deadline.WaitAsync(
            Task.FromException(new TimeoutException("fixture")), TimeSpan.FromDays(110), CancellationToken.None));
        var work = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var wait = deadline.WaitAsync(work.Task, TimeSpan.FromDays(110), CancellationToken.None);
        clock.Advance(TimeSpan.FromMilliseconds(uint.MaxValue - 1));
        await LifecycleTestHarness.Until(() => clock.PendingTimers > 0);
        Assert.False(wait.IsCompleted);
        work.SetResult();
        await wait.WaitAsync(TimeSpan.FromSeconds(5));
    }

    [Fact]
    public async Task Readiness_timeout_returns_while_provider_cancellation_and_linked_disposal_are_blocked()
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var probe = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var cancelling = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        LifecycleFixtures.For("artifact").Readiness = async token =>
        {
            using var registration = token.Register(() =>
            {
                cancelling.TrySetResult();
                release.Task.GetAwaiter().GetResult();
            });
            probe.SetResult();
            await Task.Delay(Timeout.InfiniteTimeSpan, token);
            return new(true, []);
        };
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection(),
            LifecycleFixtures.Versions, new()
            {
                ReadinessTimeout = TimeSpan.FromSeconds(1),
                DrainTimeout = TimeSpan.FromSeconds(1)
            }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        var startup = lease.Lifecycle.StartAsync();
        try
        {
            await probe.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await LifecycleTestHarness.Until(() => clock.PendingTimers > 0);
            clock.Advance(TimeSpan.FromSeconds(1));
            await cancelling.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await LifecycleTestHarness.Until(() => clock.PendingTimers > 0);
            clock.Advance(TimeSpan.FromSeconds(1));
            Assert.False((await startup.WaitAsync(TimeSpan.FromSeconds(5))).Ready);
            await Assert.ThrowsAsync<HoardLifecycleException>(() => lease.DisposeAsync().AsTask());
            Assert.Equal(HoardRootDisposalOutcome.NotAttemptedUnsafe, lease.StopResult!.RootDisposal);
        }
        finally
        {
            release.TrySetResult();
            await startup.WaitAsync(TimeSpan.FromSeconds(5));
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    [Fact]
    public async Task Startup_pause_does_not_restart_the_absolute_deadline()
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection(),
            LifecycleFixtures.Versions, new() { StartupTimeout = TimeSpan.FromSeconds(2) }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        clock.Advance(TimeSpan.FromSeconds(3));
        Assert.False((await lease.Lifecycle.StartAsync()).Ready);
        Assert.DoesNotContain("initialize", LifecycleFixtures.For("artifact").Calls);
        Assert.Contains(lease.Lifecycle.Snapshot.Diagnostics, item => item.RuleCode == "Timeout");
        await lease.DisposeAsync();
    }

    [Fact]
    public async Task Aggregate_readiness_budget_is_not_multiplied_by_selected_modules()
    {
        LifecycleFixtures.Reset();
        var clock = new LifecycleTestTimeProvider();
        var firstEntered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var firstRelease = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var secondEntered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var secondRelease = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        LifecycleFixtures.For("artifact").Readiness = async _ => { firstEntered.SetResult(); await firstRelease.Task; return new(true, []); };
        LifecycleFixtures.For("metadata").Readiness = async token =>
        {
            secondEntered.SetResult();
            await secondRelease.Task.WaitAsync(token);
            return new(true, []);
        };
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(LifecycleFixtures.Selection(),
            LifecycleFixtures.Versions, new() { ReadinessTimeout = TimeSpan.FromSeconds(5) }, clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        var startup = lease.Lifecycle.StartAsync();
        try
        {
            await firstEntered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            clock.Advance(TimeSpan.FromSeconds(4));
            firstRelease.SetResult();
            await secondEntered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            clock.Advance(TimeSpan.FromSeconds(1));
            Assert.False((await startup.WaitAsync(TimeSpan.FromSeconds(5))).Ready);
        }
        finally
        {
            firstRelease.TrySetResult();
            secondRelease.TrySetResult();
            await startup.WaitAsync(TimeSpan.FromSeconds(5));
        }
        await lease.DisposeAsync();
    }
}
