using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Composition.Tests;

public class LifecycleConcurrencyTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Stop_wins_over_initialization_or_readiness_and_cancelled_waiter_does_not_cancel_shared_start(bool readiness)
    {
        LifecycleFixtures.Reset();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        if (readiness)
        {
            LifecycleFixtures.For("artifact").Readiness = async token =>
            {
                entered.SetResult();
                await Task.Delay(Timeout.InfiniteTimeSpan, token);
                return new(true, []);
            };
        }
        else
        {
            LifecycleFixtures.For("artifact").Initialize = async token =>
        {
            entered.SetResult();
            await Task.Delay(Timeout.InfiniteTimeSpan, token);
        };
        }
        var web = LifecycleFixtures.WebBuilder();
        var builder = LifecycleFixtures.Registry(web.Services);
        var lease = await builder.ComposeHoardModulesAsync(builder.ValidateComposition(
            LifecycleFixtures.Selection(), LifecycleFixtures.Versions, new()).Composition!);
        var app = await web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        var first = lease.Lifecycle.StartAsync();
        using var cancelled = new CancellationTokenSource();
        var waiter = lease.Lifecycle.StartAsync(cancelled.Token);
        cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => waiter);
        await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
        Assert.False(first.IsCompleted);
        var results = await Task.WhenAll(Enumerable.Range(0, 8).Select(_ => lease.Lifecycle.StopAsync()));
        Assert.All(results, result => Assert.Same(results[0], result));
        Assert.False((await first).Ready);
        Assert.False(lease.Lifecycle.Snapshot.StartupAdmission);
        Assert.False((await lease.Lifecycle.StartAsync()).Ready);
        Assert.All(LifecycleFixtures.Controls.Values, control => Assert.Equal(1, control.Calls.Count(call => call == "stop")));
        await lease.DisposeAsync();
    }
}
