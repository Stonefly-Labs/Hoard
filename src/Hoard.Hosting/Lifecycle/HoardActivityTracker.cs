using System.Collections.Immutable;

namespace Hoard.Hosting.Lifecycle;

internal sealed class HoardActivityTracker
{
    private readonly object gate = new();
    private readonly Dictionary<long, HoardUnsafeActivity> active = [];
    private long nextId;
    private TaskCompletionSource quiescent = Completed();

    private static TaskCompletionSource Completed()
    {
        var result = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        result.SetResult();
        return result;
    }

    internal IDisposable Enter(string owner, HoardActivityKind kind)
    {
        lock (gate)
        {
            if (active.Count == 0) { quiescent = new(TaskCreationOptions.RunContinuationsAsynchronously); }
            var id = ++nextId;
            active.Add(id, new(owner, kind));
            return new Lease(this, id);
        }
    }

    internal Task WhenQuiescent { get { lock (gate) { return quiescent.Task; } } }

    internal ImmutableArray<HoardUnsafeActivity> Snapshot()
    {
        lock (gate) { return active.Values.Distinct().ToImmutableArray(); }
    }

    private sealed class Lease(HoardActivityTracker tracker, long id) : IDisposable
    {
        public void Dispose()
        {
            lock (tracker.gate)
            {
                tracker.active.Remove(id);
                if (tracker.active.Count == 0) { tracker.quiescent.TrySetResult(); }
            }
        }
    }
}
