using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public class LifecycleCoordinationTests
{
    [Fact]
    public void Deadline_is_absolute_and_inner_budget_never_expands_it()
    {
        var clock = new LifecycleTestTimeProvider();
        var deadline = new LifecycleDeadline(clock, TimeSpan.FromSeconds(2));
        Assert.Equal(TimeSpan.FromSeconds(2), deadline.Cap(TimeSpan.FromSeconds(30)));
        clock.Advance(TimeSpan.FromSeconds(1));
        Assert.Equal(TimeSpan.FromSeconds(1), deadline.Remaining);
        clock.Advance(TimeSpan.FromSeconds(2));
        Assert.Equal(TimeSpan.Zero, deadline.Remaining);
        Assert.Equal(TimeSpan.Zero, deadline.Cap(TimeSpan.FromSeconds(30)));
    }

    [Fact]
    public async Task Supervision_bounds_wait_not_execution_and_observes_late_work()
    {
        var clock = new LifecycleTestTimeProvider();
        var deadline = new LifecycleDeadline(clock, TimeSpan.FromSeconds(2));
        var callback = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var wait = deadline.WaitAsync(callback.Task, TimeSpan.FromSeconds(1), CancellationToken.None);
        clock.Advance(TimeSpan.FromSeconds(1));
        await Assert.ThrowsAsync<TimeoutException>(() => wait);
        Assert.False(callback.Task.IsCompleted);
        callback.SetResult();
        await callback.Task;
    }

    [Fact]
    public void Activity_retains_owner_until_actual_completion_and_ledger_enters_once()
    {
        var tracker = new HoardActivityTracker();
        using (tracker.Enter("module", HoardActivityKind.Phase))
        {
            Assert.Single(tracker.Snapshot());
        }
        Assert.Empty(tracker.Snapshot());
        var ledger = new ActivationLedger();
        ledger.Enter("module", HoardLifecyclePhase.Constructing);
        Assert.Throws<InvalidOperationException>(() => ledger.Enter("module", HoardLifecyclePhase.Constructing));
    }
}
