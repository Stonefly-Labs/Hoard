using System.Collections.Concurrent;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

public sealed class ObjectFaultControls
{
    private readonly ConcurrentDictionary<string, Func<ValueTask>> callbacks = new(StringComparer.Ordinal);
    private readonly ConcurrentQueue<string> points = new();
    private static readonly HashSet<string> Supported = new(StringComparer.Ordinal)
    {
        "object.initialize", "object.admitted", "multipart.part", "multipart.complete",
        "pointer.compare", "pointer.selected", "object.direct", "object.list",
        "object.read", "pointer.tombstone", "object.reclaimed", "multipart.cleanup"
    };
    public string[] Observed => points.ToArray();
    public void SetObserver(string point, Func<ValueTask> callback)
    {
        if (!Supported.Contains(point) || callbacks.Count >= 16) { throw new ArgumentException("Invalid object fixture boundary."); }
        ArgumentNullException.ThrowIfNull(callback);
        callbacks[point] = callback;
    }
    public void RemoveObserver(string point) => callbacks.TryRemove(point, out _);
    internal ValueTask ObserveAsync(string point)
    {
        if (points.Count < 100) { points.Enqueue(point); }
        return callbacks.TryGetValue(point, out var callback) ? callback() : ValueTask.CompletedTask;
    }
}
