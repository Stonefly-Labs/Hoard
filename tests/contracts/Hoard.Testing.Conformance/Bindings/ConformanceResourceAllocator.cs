using System.Collections.Immutable;
using Hoard.Testing.Conformance.Diagnostics;

namespace Hoard.Testing.Conformance.Bindings;

/// <summary>
/// Allocates synthetic directories beneath a controller-owned private parent.
/// Physical cleanup and Released remain exclusively the controller's responsibility after child exit.
/// </summary>
public sealed class ConformanceResourceAllocator : IConformanceResourceAllocator, IDisposable
{
    private readonly object gate = new();
    private readonly string parent;
    private readonly OwnedDirectoryHandle parentHandle;
    private readonly TimeSpan cleanupBudget;
    private readonly Dictionary<ConformanceOwnedDirectory, Entry> entries = new(ReferenceEqualityComparer.Instance);
    private bool disposed;

    private ConformanceResourceAllocator(string parent, OwnedDirectoryHandle handle, TimeSpan cleanupBudget)
    {
        this.parent = parent;
        parentHandle = handle;
        this.cleanupBudget = cleanupBudget;
    }

    public static ConformanceResourceAllocator Open(string privateParent, string repositoryRoot,
        TimeSpan? cleanupBudget = null)
    {
        var budget = cleanupBudget ?? TimeSpan.FromSeconds(30);
        if (budget <= TimeSpan.Zero || budget > TimeSpan.FromSeconds(30))
        { throw new ArgumentOutOfRangeException(nameof(cleanupBudget), "OwnershipInvalid"); }
        var path = OwnedDirectoryHandle.Normalize(privateParent);
        var repository = OwnedDirectoryHandle.Normalize(repositoryRoot);
        if (path == repository || path.StartsWith(repository + Path.DirectorySeparatorChar, StringComparison.Ordinal))
        { throw new InvalidOperationException("OwnershipInvalid"); }
        var handle = OwnedDirectoryHandle.OpenPrivateParent(path);
        try
        {
            handle.Lock();
            handle.VerifyPath(path);
            if (Directory.EnumerateFileSystemEntries(path).Any())
            { throw new InvalidOperationException("OwnershipInvalid"); }
            handle.VerifyPath(path);
            return new(path, handle, budget);
        }
        catch (PlatformNotSupportedException) { handle.Dispose(); throw; }
        catch { handle.Dispose(); throw new InvalidOperationException("OwnershipInvalid"); }
    }

    public ValueTask<ConformanceOwnedDirectory> AllocateDirectoryAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        lock (gate)
        {
            ObjectDisposedException.ThrowIf(disposed, this);
            if (entries.Count >= 1024) { throw new InvalidOperationException("OwnershipInvalid"); }
            parentHandle.VerifyPath(parent);
            var name = "resource-" + Guid.NewGuid().ToString("N");
            var path = Path.Combine(parent, name);
            var lease = new ConformanceOwnedDirectory(name, path);
            var entry = new Entry(lease);
            entries.Add(lease, entry);
            try
            {
                entry.Handle = parentHandle.CreateChild(name);
                // Admission retains the descriptor even if the path was swapped during creation.
                Verify(entry);
            }
            catch
            {
                Record(entry, ConformanceOwnershipState.Retained, ConformanceDiagnosticCode.OwnershipInvalid);
                throw new InvalidOperationException("OwnershipInvalid");
            }
            return ValueTask.FromResult(lease);
        }
    }

    /// <summary>Immutable, path-free history; retries never remove an earlier retained observation.</summary>
    public ImmutableArray<ConformanceResourceEvent> ObserveLedger()
    {
        lock (gate)
        {
            return entries.Values.SelectMany(entry => entry.History).ToImmutableArray();
        }
    }

    public ValueTask<ConformanceCleanupObservation> ReleaseAsync(
        ConformanceOwnedDirectory resource, CancellationToken cancellationToken)
    {
        lock (gate)
        {
            var entry = Find(resource);
            Verify(entry);
            cancellationToken.ThrowIfCancellationRequested();
            if (entry.History[^1].Observation.State == ConformanceOwnershipState.Retained)
            { return ValueTask.FromResult(entry.History[^1].Observation); }
            return ValueTask.FromResult(Record(entry, ConformanceOwnershipState.Settling));
        }
    }

    /// <summary>
    /// Admits the real store/lifetime settlement task, not a dispose notification.
    /// Caller cancellation/timeout stops observation only and never cancels that task.
    /// A completed task still leaves the directory Settling for authoritative controller cleanup.
    /// </summary>
    public async ValueTask<ConformanceCleanupObservation> ReleaseAsync(
        ConformanceOwnedDirectory resource, Task actualSettlement, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(actualSettlement);
        Entry entry;
        lock (gate)
        {
            entry = Find(resource);
            Verify(entry);
            if (entry.Observing || entry.Attempts >= 3
                || (entry.Settlement is not null && !ReferenceEquals(entry.Settlement, actualSettlement)))
            { throw new InvalidOperationException("OwnershipInvalid"); }
            entry.Attempts++;
            if (entry.Settlement is null)
            {
                // Keep identity pins alive beyond a timed-out observer, until the actual work ends.
                _ = actualSettlement.ContinueWith(static (_, owner) => GC.KeepAlive(owner), this,
                    CancellationToken.None, TaskContinuationOptions.ExecuteSynchronously, TaskScheduler.Default);
            }
            entry.Settlement = actualSettlement;
            entry.Observing = true;
            Record(entry, ConformanceOwnershipState.Settling);
        }
        var reason = ConformanceDiagnosticCode.None;
        try
        {
            await actualSettlement.WaitAsync(cleanupBudget, TimeProvider.System, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception)
        {
            // Never persist task exceptions: provider messages may contain private paths or credentials.
            reason = ConformanceDiagnosticCode.CleanupIncomplete;
        }
        lock (gate)
        {
            entry.Observing = false;
            Verify(entry);
            return Record(entry, reason == ConformanceDiagnosticCode.None
                ? ConformanceOwnershipState.Settling : ConformanceOwnershipState.Retained, reason);
        }
    }

    /// <summary>Closes identity pins only after tracked work ends; does not release or delete resources.</summary>
    public void Dispose()
    {
        lock (gate)
        {
            if (disposed) { return; }
            if (entries.Values.Any(entry => entry.Observing || entry.Settlement is null || !entry.Settlement.IsCompleted))
            { throw new InvalidOperationException("CleanupIncomplete"); }
            foreach (var entry in entries.Values) { entry.Handle?.Dispose(); }
            parentHandle.Dispose();
            disposed = true;
        }
    }

    private Entry Find(ConformanceOwnedDirectory resource)
    {
        ObjectDisposedException.ThrowIf(disposed, this);
        if (resource is null || !entries.TryGetValue(resource, out var entry))
        { throw new InvalidOperationException("OwnershipInvalid"); }
        return entry;
    }

    private void Verify(Entry entry)
    {
        try
        {
            parentHandle.VerifyPath(parent);
            if (entry.Handle is null) { throw new InvalidOperationException("OwnershipInvalid"); }
            entry.Handle.VerifyPath(entry.Lease.DirectoryPath);
        }
        catch
        {
            Record(entry, ConformanceOwnershipState.Retained, ConformanceDiagnosticCode.OwnershipInvalid);
            throw new InvalidOperationException("OwnershipInvalid");
        }
    }

    private static ConformanceCleanupObservation Record(Entry entry, ConformanceOwnershipState state,
        ConformanceDiagnosticCode reason = ConformanceDiagnosticCode.None)
    {
        if (state == ConformanceOwnershipState.Retained && entry.History.Count > 0
            && entry.History[^1].Observation.State is ConformanceOwnershipState.Allocated or ConformanceOwnershipState.Active)
        { Record(entry, ConformanceOwnershipState.Settling); }
        var observation = new ConformanceCleanupObservation(state, [entry.Lease.ResourceId], reason);
        if (entry.History.Count == 0 || entry.History[^1].Observation.State != state
            || entry.History[^1].Observation.Reason != reason)
        {
            if (entry.History.Count >= 16) { throw new InvalidOperationException("OwnershipInvalid"); }
            entry.History.Add(new(entry.Lease.ResourceId, entry.History.Count, observation));
        }
        return observation;
    }

    private sealed class Entry
    {
        internal Entry(ConformanceOwnedDirectory lease)
        {
            Lease = lease;
            Record(this, ConformanceOwnershipState.Allocated);
            Record(this, ConformanceOwnershipState.Active);
        }
        internal ConformanceOwnedDirectory Lease { get; }
        internal OwnedDirectoryHandle? Handle { get; set; }
        internal List<ConformanceResourceEvent> History { get; } = [];
        internal Task? Settlement { get; set; }
        internal bool Observing { get; set; }
        internal int Attempts { get; set; }
    }
}

public sealed record ConformanceResourceEvent(
    string ResourceId, int Sequence, ConformanceCleanupObservation Observation);
