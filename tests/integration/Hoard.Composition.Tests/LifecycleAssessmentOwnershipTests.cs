using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public class LifecycleAssessmentOwnershipTests
{
    [Fact]
    public async Task Queued_readiness_is_owned_until_assessment_and_cleanup_have_settled()
    {
        LifecycleFixtures.Reset();
        using var clock = new AssessmentClock();
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        await using var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new(), clock).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        await app.StartAsync();
        await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));

        clock.Arm();
        var assessment = lease.Lifecycle.AssessReadinessAsync();
        Task<HoardStopResult>? stopping = null;
        try
        {
            await clock.Entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Contains(new HoardUnsafeActivity("composition", HoardActivityKind.Phase),
                lease.Coordinator.Activities.Snapshot());
            stopping = lease.Lifecycle.StopAsync();
            await LifecycleTestHarness.Until(() => lease.Lifecycle.Snapshot.Phase == HoardLifecyclePhase.Draining);
            Assert.False(stopping.IsCompleted);
            Assert.All(LifecycleFixtures.Controls.Values, control => Assert.DoesNotContain("stop", control.Calls));

            clock.Release();
            Assert.False((await assessment.WaitAsync(TimeSpan.FromSeconds(5))).StartupAdmission);
            var result = await stopping.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Empty(result.UnsafeActivities);
            Assert.All(result.Modules, module => Assert.Equal(HoardCleanupOutcome.Completed, module.Outcome));
            Assert.All(LifecycleFixtures.Controls.Values,
                control => Assert.Equal(1, control.Calls.Count(call => call == "stop")));
        }
        finally
        {
            clock.Release();
            await assessment.WaitAsync(TimeSpan.FromSeconds(5));
            if (stopping is not null) { await stopping.WaitAsync(TimeSpan.FromSeconds(5)); }
            await lease.Coordinator.Activities.WhenQuiescent.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    private sealed class AssessmentClock : TimeProvider, IDisposable
    {
        private readonly ManualResetEventSlim release = new();
        private int armed;
        internal TaskCompletionSource Entered { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        internal void Arm() => Interlocked.Exchange(ref armed, 1);
        internal void Release() => release.Set();
        public override long TimestampFrequency => System.TimestampFrequency;
        public override long GetTimestamp()
        {
            if (Interlocked.Exchange(ref armed, 0) != 0)
            {
                Entered.SetResult();
                if (!release.Wait(TimeSpan.FromSeconds(5))) { throw new TimeoutException("Assessment clock was not released."); }
            }
            return System.GetTimestamp();
        }
        public override ITimer CreateTimer(TimerCallback callback, object? state, TimeSpan dueTime, TimeSpan period) =>
            System.CreateTimer(callback, state, dueTime, period);
        public void Dispose() => release.Dispose();
    }
}
