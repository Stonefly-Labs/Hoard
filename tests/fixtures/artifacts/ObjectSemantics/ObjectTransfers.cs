using System.Collections.Concurrent;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

internal sealed class ObjectOperation(ArtifactOperationTicket ticket, ArtifactExpectations expectations)
{
    public ArtifactOperationTicket Ticket { get; } = ticket;
    public ArtifactExpectations Expectations { get; } = expectations;
    public ArtifactStagingOwner? Owner { get; set; }
    public ArtifactStagedWrite? Verified { get; set; }
    private ArtifactMutationReceipt? receipt;
    public ArtifactMutationReceipt? Receipt { get => Volatile.Read(ref receipt); set => Volatile.Write(ref receipt, value); }
    public List<Guid> Parts { get; } = [];
    public long Generation { get; set; }
    public bool Writing { get; set; }
    public bool Fenced { get; set; }
    private bool deciding;
    public bool Deciding { get => Volatile.Read(ref deciding); set => Volatile.Write(ref deciding, value); }
    public bool ReservationReleased { get; set; }
    public ObjectPointer? Selected { get; set; }
    public ArtifactMutationOutcome Outcome { get; set; }
    public Guid ReceiptId { get; set; }
    public string Proof { get; set; } = "";
    public ArtifactStamp? DeleteTarget { get; set; }
    public Guid? Assembly { get; set; }
    public long AssemblyBytes { get; set; }
}

internal sealed record ObjectPointer(ArtifactStamp Stamp, Guid ObjectId, long Version, Guid OperationId, DateTimeOffset HistoryUntil,
    bool Removed = false, bool Corrupt = false);
internal sealed class ObjectOperationException(ArtifactFailureCode code) : Exception
{
    public ArtifactFailureCode Code { get; } = code;
}

public sealed partial class ObjectArtifactStore
{
    private readonly object pointerSync = new();
    private readonly object workSync = new();
    private readonly ConcurrentDictionary<Guid, ObjectOperation> uploads = [];
    private readonly ConcurrentDictionary<Guid, byte> unfinishedReadCloses = [];
    private readonly ConcurrentDictionary<Guid, byte> failedMultipartCleanup = [];
    private readonly ConcurrentDictionary<Guid, byte> failedAssemblyCleanup = [];
    private readonly Dictionary<string, ObjectPointer> pointers = new(StringComparer.Ordinal);
    private readonly Dictionary<Guid, Task> ownedWork = [];
    private readonly HashSet<Guid> lateWork = [];
    private readonly Dictionary<Guid, Func<ValueTask>> incompleteHandoffs = [];
    private readonly Dictionary<Guid, Task> handoffRetries = [];
    private readonly HashSet<Guid> activeMutations = [];
    private readonly Dictionary<Guid, Guid> ticketReaders = [];
    private readonly Dictionary<Guid, ObjectPointer> retiredObjects = [];
    private readonly Dictionary<string, ObjectCursor> listingCursors = new(StringComparer.Ordinal);
    private long listingRevision;
    private readonly HashSet<ObjectReadSession> sessions = [];
    private ArtifactInitialization? initializedWith;
    private Guid processSession;
    private DateTimeOffset utcFloor = DateTimeOffset.UnixEpoch;
    private SemaphoreSlim? transferSlots;
    private CancellationTokenSource stopToken = new();
    private int queued;
    private long reservedBytes;
    private long assemblyBytes;
    private int assemblyCount;
    private volatile bool stopRequested;
    private string? bucketPath;

    private ArtifactStoreIdentity Identity => initializedWith!.Store;
    private ArtifactLimits Bounds => initializedWith!.Limits;
    private DateTimeOffset EffectiveNow()
    {
        var observed = time.GetUtcNow();
        if (observed > utcFloor) { utcFloor = observed; }
        return utcFloor;
    }

    private string ObjectPath(Guid id) => SafePath("objects", id);
    private string PartPath(Guid id) => SafePath("multipart", id);
    private string SafePath(string area, Guid id)
    {
        var parent = Path.Combine(bucketPath!, area);
        var file = Path.Combine(parent, id.ToString("N"));
        foreach (var entry in new FileSystemInfo[] { new DirectoryInfo(parent), new FileInfo(file) })
        {
            if (entry.LinkTarget is not null || entry.Exists && (entry.Attributes & FileAttributes.ReparsePoint) != 0)
            { throw new ObjectOperationException(ArtifactFailureCode.InvalidInput); }
        }
        return file;
    }

    private ObjectOperation Operation(ArtifactOperationTicket ticket)
    {
        if (ticket.Store != Identity || !uploads.TryGetValue(ticket.Id, out var operation) || operation.Ticket != ticket)
        { throw new ObjectOperationException(ArtifactFailureCode.InvalidInput); }
        if (EffectiveNow() >= ticket.Expires) { throw new ObjectOperationException(ArtifactFailureCode.ReconciliationExpired); }
        return operation;
    }

    private void CurrentOwner(ObjectOperation operation, ArtifactStagingOwner expected)
    {
        if (operation.Fenced || operation.Owner != expected || expected.SessionId != processSession
            || EffectiveNow() >= expected.Expires || operation.Receipt is not null)
        { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
    }

    private async Task<TransferLease> EnterTransferAsync(CancellationToken token)
    {
        lock (pointerSync)
        {
            if (transferSlots!.Wait(0)) { return new(transferSlots); }
            if (queued >= Bounds.WaitingCalls) { throw new ObjectOperationException(ArtifactFailureCode.Capacity); }
            queued++;
        }
        try
        {
            await faults.ObserveAsync("object.transfer-queued");
            await transferSlots.WaitAsync(token);
            return new(transferSlots);
        }
        finally { lock (pointerSync) { queued--; } }
    }

    private bool MutationActive(Guid ticket) { lock (workSync) { return activeMutations.Contains(ticket); } }
    private bool TicketObserved(Guid ticket) { lock (workSync) { return ticketReaders.ContainsValue(ticket); } }
    public Task WhenIdleForQualificationAsync()
    { lock (workSync) { return Task.WhenAll(ownedWork.Values.ToArray()); } }

    private async ValueTask ReclaimUndeliveredAsync<T>(Guid id, T value, Func<T, ValueTask> reclaim)
    {
        async ValueTask Cleanup()
        {
            await faults.ObserveAsync("object.operation-reclaim");
            await reclaim(value);
        }
        lock (workSync) { incompleteHandoffs.Add(id, Cleanup); }
        try { await Cleanup(); }
        catch (Exception) { throw new ObjectOperationException(ArtifactFailureCode.CleanupIncomplete); }
        lock (workSync) { incompleteHandoffs.Remove(id); }
    }

    private Task[] RetryUndeliveredCleanup()
    {
        lock (workSync)
        {
            foreach (var (id, cleanup) in incompleteHandoffs)
            {
                if (handoffRetries.ContainsKey(id)) { continue; }
                var retry = Task.Run(async () =>
                {
                    try
                    {
                        await cleanup();
                        lock (workSync) { incompleteHandoffs.Remove(id); }
                    }
                    finally { lock (workSync) { handoffRetries.Remove(id); } }
                });
                handoffRetries.Add(id, retry);
            }
            return handoffRetries.Values.ToArray();
        }
    }

    private async ValueTask<ArtifactResult<T>> OwnedAsync<T>(ArtifactPhase phase, TimeSpan timeout,
        CancellationToken caller, Func<CancellationToken, Task<T>> operation, ArtifactOperationTicket? ticket = null,
        Action? onSettled = null, Action? cancellationSettled = null, Func<T, ValueTask>? undelivered = null) where T : notnull
    {
        var id = Guid.NewGuid();
        var deadline = new CancellationTokenSource(timeout, time);
        var cancellation = CancellationTokenSource.CreateLinkedTokenSource(caller, deadline.Token, stopToken.Token);
        var token = cancellation.Token;
        ArtifactResult<T>? delivered = null;
        var abandoned = false;
        Task<ArtifactResult<T>> work;
        lock (workSync)
        {
            if (!initialized || stopRequested || Volatile.Read(ref lifetimeBusy) != 0 || lateWork.Count != 0
                || incompleteHandoffs.Count > 0 || !unfinishedReadCloses.IsEmpty
                || (!failedMultipartCleanup.IsEmpty || !failedAssemblyCleanup.IsEmpty)
                    && phase is not (ArtifactPhase.Maintenance or ArtifactPhase.Reconcile)
                || ownedWork.Count >= Bounds.TransferSlots + Bounds.WaitingCalls)
            {
                cancellation.Dispose();
                deadline.Dispose();
                onSettled?.Invoke();
                return Rejected<T>(lateWork.Count > 0 || incompleteHandoffs.Count > 0 || !unfinishedReadCloses.IsEmpty
                    || !failedMultipartCleanup.IsEmpty || !failedAssemblyCleanup.IsEmpty
                    ? ArtifactFailureCode.CleanupIncomplete
                    : initialized && !stopRequested ? ArtifactFailureCode.Capacity : ArtifactFailureCode.Disposed, phase, ticket);
            }
            var mutating = ticket is not null && phase is ArtifactPhase.Stage or ArtifactPhase.Publication or ArtifactPhase.Delete;
            if (mutating && !activeMutations.Add(ticket!.Id))
            {
                cancellation.Dispose();
                deadline.Dispose();
                onSettled?.Invoke();
                return Rejected<T>(ArtifactFailureCode.Conflict, phase, ticket);
            }
            if (ticket is not null) { ticketReaders.Add(id, ticket.Id); }
            work = Task.Run(async () =>
            {
                try
                {
                    token.ThrowIfCancellationRequested();
                    var value = await operation(token);
                    var transferred = false;
                    try
                    {
                        await faults.ObserveAsync("object.operation-completed");
                        lock (workSync)
                        {
                            if (!abandoned)
                            {
                                transferred = true;
                                return delivered = new ArtifactResult<T>.Success(value);
                            }
                        }
                        return Rejected<T>(caller.IsCancellationRequested ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded,
                            phase, ticket);
                    }
                    finally
                    {
                        if (!transferred && undelivered is not null)
                        {
                            await ReclaimUndeliveredAsync(id, value, undelivered);
                        }
                    }
                }
                catch (Exception error)
                {
                    var code = MapError(error, caller);
                    if (code is ArtifactFailureCode.CancelledBeforeCommit or ArtifactFailureCode.DeadlineExceeded)
                    {
                        try { cancellationSettled?.Invoke(); }
                        catch (Exception settlementError) { return Rejected<T>(MapError(settlementError, caller), phase, ticket); }
                    }
                    if (code == ArtifactFailureCode.CancelledBeforeCommit && !caller.IsCancellationRequested && token.IsCancellationRequested)
                    { code = ArtifactFailureCode.DeadlineExceeded; }
                    return Rejected<T>(code, phase, ticket);
                }
                finally
                {
                    lock (workSync)
                    {
                        ownedWork.Remove(id);
                        ticketReaders.Remove(id);
                        lateWork.Remove(id);
                        if (mutating) { activeMutations.Remove(ticket!.Id); }
                    }
                    await faults.ObserveAsync("object.operation-released");
                    cancellation.Dispose();
                    deadline.Dispose();
                    onSettled?.Invoke();
                }
            }, CancellationToken.None);
            ownedWork.Add(id, work);
        }
        try { return await work.WaitAsync(token); }
        catch (OperationCanceledException)
        {
            lock (workSync)
            {
                if (delivered is not null) { return delivered; }
                abandoned = true;
                var live = ownedWork.ContainsKey(id);
                if (live) { lateWork.Add(id); }
                return Rejected<T>(caller.IsCancellationRequested ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded,
                    phase, ticket, live);
            }
        }
    }

    private ArtifactResult<T> Rejected<T>(ArtifactFailureCode code, ArtifactPhase phase,
        ArtifactOperationTicket? ticket = null, bool retainedOwnership = false) where T : notnull
    {
        if (code is not (ArtifactFailureCode.InvalidInput or ArtifactFailureCode.ReconciliationExpired)
            && ticket is not null && uploads.TryGetValue(ticket.Id, out var upload) && upload.Ticket == ticket
            && (upload.Deciding || upload.Receipt is not null) && phase is ArtifactPhase.Publication or ArtifactPhase.Delete)
        { code = ArtifactFailureCode.Uncertain; }
        return new ArtifactResult<T>.Failure(code, phase,
            code == ArtifactFailureCode.Uncertain ? ArtifactAction.ReconcileExactTicket : ArtifactAction.Reobserve,
            Guid.NewGuid(), ticket is null ? null : new ArtifactOption<ArtifactOperationTicket>.Some(ticket),
            retainedOwnership || code == ArtifactFailureCode.CleanupIncomplete || !failedMultipartCleanup.IsEmpty || !failedAssemblyCleanup.IsEmpty
                ? ArtifactCleanupState.RetainedLiveOwnership : ArtifactCleanupState.Released);
    }

    private static ArtifactFailureCode MapError(Exception error, CancellationToken caller) => error switch
    {
        ObjectOperationException known => known.Code,
        OperationCanceledException => caller.IsCancellationRequested ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded,
        UnauthorizedAccessException => ArtifactFailureCode.AccessDenied,
        IOException io when (io.HResult & 0xffff) is 28 or 112 => ArtifactFailureCode.Capacity,
        IOException => ArtifactFailureCode.Unavailable,
        ArgumentException => ArtifactFailureCode.InvalidInput,
        _ => ArtifactFailureCode.InternalFailure
    };

    private sealed class TransferLease(SemaphoreSlim slots) : IDisposable
    {
        private int released;
        public void Dispose() { if (Interlocked.Exchange(ref released, 1) == 0) { slots.Release(); } }
    }
}
