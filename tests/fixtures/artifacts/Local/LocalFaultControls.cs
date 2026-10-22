using System.Collections.Concurrent;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed class LocalFaultControls
{
    private readonly ConcurrentDictionary<string, Func<ValueTask>> observers = new(StringComparer.Ordinal);
    private readonly ConcurrentQueue<string> observed = new();
    private static readonly HashSet<string> Points = new(StringComparer.Ordinal)
    {
        "initialize.before-root", "initialize.admitted", "stage.prefix", "stage.verified",
        "publish.before-decision", "publish.decided", "publish.receipted",
        "read.opened", "read.copy", "delete.removed", "delete.reclaimed", "cleanup.candidate"
    };
    public string[] Observed => observed.ToArray();
    public void SetObserver(string point, Func<ValueTask> observer)
    {
        if (!Points.Contains(point) || observers.Count >= 16) { throw new ArgumentException("Invalid local fixture boundary."); }
        ArgumentNullException.ThrowIfNull(observer);
        observers[point] = observer;
    }
    public void RemoveObserver(string point) => observers.TryRemove(point, out _);
    internal ValueTask ObserveAsync(string point)
    {
        if (observed.Count < 100) { observed.Enqueue(point); }
        return observers.TryGetValue(point, out var observer) ? observer() : ValueTask.CompletedTask;
    }
}
