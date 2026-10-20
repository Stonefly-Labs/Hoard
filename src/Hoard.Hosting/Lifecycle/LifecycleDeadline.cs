namespace Hoard.Hosting.Lifecycle;

internal sealed class LifecycleDeadline(TimeProvider clock, TimeSpan budget)
{
    private readonly long started = clock.GetTimestamp();
    internal TimeSpan Remaining
    {
        get
        {
            var remaining = budget - clock.GetElapsedTime(started);
            return remaining > TimeSpan.Zero ? remaining : TimeSpan.Zero;
        }
    }
    internal TimeSpan Cap(TimeSpan inner) => inner < Remaining ? inner : Remaining;

    internal async Task WaitAsync(Task task, TimeSpan inner, CancellationToken token)
    {
        var callback = new LifecycleDeadline(clock, inner);
        while (true)
        {
            var remaining = Cap(callback.Remaining);
            if (remaining <= TimeSpan.Zero) { throw new TimeoutException(); }
            var slice = remaining > TimeSpan.FromMilliseconds(uint.MaxValue - 1)
                ? TimeSpan.FromMilliseconds(uint.MaxValue - 1) : remaining;
            try { await task.WaitAsync(slice, clock, token).ConfigureAwait(false); return; }
            catch (TimeoutException) when (slice < remaining && !task.IsCompleted) { }
        }
    }
}
