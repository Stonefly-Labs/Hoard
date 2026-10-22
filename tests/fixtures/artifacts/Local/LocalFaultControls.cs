using System.Collections.Concurrent;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed class LocalFaultControls
{
    private readonly ConcurrentDictionary<string, Func<ValueTask>> observers = new(StringComparer.Ordinal);
    private readonly ConcurrentQueue<string> observed = new();
    private static readonly HashSet<string> Points = new(StringComparer.Ordinal)
    {
        "initialize.before-root", "initialize.admitted", "stage.prefix", "stage.verified",
        "publish.admitted", "publish.before-decision", "publish.decided", "publish.receipted", "publish.progress",
        "read.opened", "read.copy", "delete.removed", "delete.reclaimed", "cleanup.candidate", "transfer.queued",
        "reconcile.before-resolution", "operation.released", "operation.completed", "operation.reclaim"
    };
    public string[] Observed => observed.ToArray();
    public Action? BeforeRecordWrite { get; set; }
    public Action<string, string>? BeforeHistoryCandidate { get; set; }
    public Func<ArtifactCapabilities, ArtifactCapabilities>? CapabilitiesForAdmission { get; set; }
    public string? InitializationFailure { get; private set; }
    internal void RecordInitializationFailure(Exception error)
        => InitializationFailure = error.GetType().Name + ":" + error.TargetSite?.Name;
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
