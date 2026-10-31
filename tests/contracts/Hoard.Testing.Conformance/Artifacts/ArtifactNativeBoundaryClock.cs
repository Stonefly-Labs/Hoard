namespace Hoard.Testing.Conformance.Artifacts;

public sealed class ArtifactNativeBoundaryClock(DateTimeOffset initial) : TimeProvider
{
    private readonly object gate = new();
    private readonly List<DeadlineTimer> timers = [];
    private long ticks;

    public override long TimestampFrequency => TimeSpan.TicksPerSecond;
    public override long GetTimestamp() { lock (gate) { return ticks; } }
    public override DateTimeOffset GetUtcNow() => initial + TimeSpan.FromTicks(GetTimestamp());

    public void Advance(TimeSpan duration)
    {
        ArgumentOutOfRangeException.ThrowIfNegative(duration.Ticks);
        DeadlineTimer[] due;
        lock (gate)
        {
            ticks = checked(ticks + duration.Ticks);
            due = timers.Where(timer => timer.Due <= ticks).ToArray();
            foreach (var timer in due) { timer.Due = long.MaxValue; }
        }
        foreach (var timer in due) { timer.Fire(); }
    }

    public override ITimer CreateTimer(TimerCallback callback, object? state, TimeSpan dueTime, TimeSpan period)
    {
        ArgumentNullException.ThrowIfNull(callback);
        var timer = new DeadlineTimer(this, callback, state);
        lock (gate)
        {
            timer.Change(dueTime, period);
            timers.Add(timer);
        }
        return timer;
    }

    private sealed class DeadlineTimer(ArtifactNativeBoundaryClock owner, TimerCallback callback, object? state) : ITimer
    {
        private bool disposed;
        public long Due { get; set; } = long.MaxValue;
        public bool Change(TimeSpan dueTime, TimeSpan period)
        {
            if (period != Timeout.InfiniteTimeSpan) { throw new ArgumentOutOfRangeException(nameof(period)); }
            if (dueTime < Timeout.InfiniteTimeSpan) { throw new ArgumentOutOfRangeException(nameof(dueTime)); }
            lock (owner.gate)
            {
                if (disposed) { return false; }
                Due = dueTime == Timeout.InfiniteTimeSpan ? long.MaxValue : checked(owner.ticks + dueTime.Ticks);
            }
            return true;
        }
        public void Fire() => callback(state);
        public void Dispose()
        {
            lock (owner.gate) { disposed = true; owner.timers.Remove(this); }
        }
        public ValueTask DisposeAsync() { Dispose(); return ValueTask.CompletedTask; }
    }
}
