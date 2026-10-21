using Hoard.Hosting.Discovery;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryRaceTests
{
    private sealed class CaptureClock : TimeProvider
    {
        internal readonly ManualResetEventSlim Captured = new();
        internal readonly ManualResetEventSlim Release = new();
        internal int TargetThread;
        public override DateTimeOffset GetUtcNow()
        {
            if (Environment.CurrentManagedThreadId == Volatile.Read(ref TargetThread))
            {
                Captured.Set();
                if (!Release.Wait(TimeSpan.FromSeconds(5))) { throw new TimeoutException("Discovery capture barrier expired."); }
            }
            return DateTimeOffset.UtcNow;
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task A_captured_revision_stays_coherent_while_the_authority_changes_without_waiting_for_the_reader(bool reassess)
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var clock = new CaptureClock();
        using var capturedBarrier = clock.Captured;
        using var releaseBarrier = clock.Release;
        await using var harness = new DiscoveryTestHarness();
        var (app, lease) = await DiscoveryFixtures.Build(options: new()
        { Exposure = HoardDiscoveryExposure.LocalLoopback, DirectLocalNoProxy = true, TimeProvider = clock });
        await using (lease)
        {
            await app.StartAsync();
            var before = lease.Discovery!.Capture().Observation!;
            var read = Task.Run(() =>
            {
                Volatile.Write(ref clock.TargetThread, Environment.CurrentManagedThreadId);
                return lease.Discovery.Capture();
            });
            harness.Observe(read);
            try
            {
                Assert.True(clock.Captured.Wait(TimeSpan.FromSeconds(5)));
                if (reassess)
                {
                    LifecycleFixtures.For("protocol").Readiness = _ => Task.FromResult(new HoardModuleReadiness(false, []));
                    await lease.Lifecycle.AssessReadinessAsync().WaitAsync(TimeSpan.FromSeconds(5));
                }
                else { await lease.Lifecycle.StopAsync().WaitAsync(TimeSpan.FromSeconds(5)); }
            }
            finally { clock.Release.Set(); }
            var old = (await read).Observation!;
            Assert.Equal(before.Revision, old.Revision);
            Assert.Equal("running", old.Phase);
            Assert.True(old.StartupAdmission);
            Assert.Equal("usable", old.Modules.Single(module => module.Id == "protocol").Capabilities.Single().Availability);
            var after = lease.Discovery.Capture().Observation!;
            Assert.True(after.Revision > old.Revision);
            Assert.Equal(reassess ? "running" : "stopped", after.Phase);
            Assert.Equal(reassess, after.StartupAdmission);
            Assert.False(after.Ready);
            Assert.Equal("unavailable", after.Modules.Single(module => module.Id == "protocol").Capabilities.Single().Availability);
        }
    }
}
