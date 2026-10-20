namespace Hoard.Composition.Tests;

internal sealed class LifecycleTestTimeProvider : TimeProvider
{
    private readonly object gate = new();
    private readonly List<Timer> timers = [];
    private long ticks;

    public override long TimestampFrequency => TimeSpan.TicksPerSecond;
    public override long GetTimestamp() { lock (gate) { return ticks; } }
    public override DateTimeOffset GetUtcNow() => DateTimeOffset.UnixEpoch + TimeSpan.FromTicks(GetTimestamp());
    internal int PendingTimers { get { lock (gate) { return timers.Count(timer => timer.Due != long.MaxValue); } } }
    internal TimeSpan? NextDelay
    {
        get
        {
            lock (gate)
            {
                var next = timers.Where(timer => timer.Due != long.MaxValue).Select(timer => (long?)timer.Due).Min();
                return next is null ? null : TimeSpan.FromTicks(next.Value - ticks);
            }
        }
    }

    public void Advance(TimeSpan duration)
    {
        Timer[] due;
        lock (gate)
        {
            ticks += duration.Ticks;
            due = timers.Where(timer => timer.Due <= ticks).ToArray();
            foreach (var timer in due) { timer.Due = long.MaxValue; }
        }
        foreach (var timer in due) { timer.Fire(); }
    }

    public override ITimer CreateTimer(TimerCallback callback, object? state, TimeSpan dueTime, TimeSpan period)
    {
        var timer = new Timer(this, callback, state);
        lock (gate) { timers.Add(timer); }
        timer.Change(dueTime, period);
        return timer;
    }

    private sealed class Timer(LifecycleTestTimeProvider owner, TimerCallback callback, object? state) : ITimer
    {
        public long Due { get; set; } = long.MaxValue;
        public bool Change(TimeSpan dueTime, TimeSpan period)
        {
            lock (owner.gate)
            {
                Due = dueTime == Timeout.InfiniteTimeSpan ? long.MaxValue : owner.ticks + dueTime.Ticks;
            }
            return true;
        }
        public void Fire() => callback(state);
        public void Dispose() { lock (owner.gate) { owner.timers.Remove(this); } }
        public ValueTask DisposeAsync() { Dispose(); return ValueTask.CompletedTask; }
    }
}
