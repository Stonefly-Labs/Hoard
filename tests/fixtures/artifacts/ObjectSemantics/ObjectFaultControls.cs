using System.Collections.Concurrent;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

public sealed class ObjectFaultControls
{
    private readonly ConcurrentDictionary<string, Func<ValueTask>> callbacks = new(StringComparer.Ordinal);
    private readonly ConcurrentQueue<string> points = new();
    private static readonly HashSet<string> Supported = new(StringComparer.Ordinal)
    {
        "object.initialize", "object.admitted", "multipart.part", "multipart.complete",
        "object.publication-admitted", "pointer.compare", "pointer.selected", "object.direct", "object.list",
        "object.read", "pointer.tombstone", "object.reclaimed", "multipart.cleanup", "object.commit-progress", "object.transfer-queued",
        "object.operation-released", "object.operation-completed", "object.operation-reclaim",
        "object.receipted", "object.read-opened", "object.reconcile-before-resolution", "object.reconcile-verified",
        "object.payload-damage"
    };
    public string[] Observed => points.ToArray();
    public Action? BeforeObjectDelete { get; set; }
    public Action<string, string>? BeforeHistoryCandidate { get; set; }
    public Func<ArtifactCapabilities, ArtifactCapabilities>? CapabilitiesForAdmission { get; set; }
    public void SetObserver(string point, Func<ValueTask> callback)
    {
        if (!Supported.Contains(point)) { throw new ArgumentException("Invalid object fixture boundary."); }
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
