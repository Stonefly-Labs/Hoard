using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public class LifecycleDeadlineTests
{
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
