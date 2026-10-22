using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore
{
    private readonly object stateSync = new();
    private readonly object activitySync = new();
    private readonly ConcurrentDictionary<Guid, LocalOperation> operations = [];
    private readonly ConcurrentDictionary<Guid, byte> incompleteReadCloses = [];
    private readonly Dictionary<string, LocalDecision> decisions = new(StringComparer.Ordinal);
    private readonly SemaphoreSlim[] digestGates = Enumerable.Range(0, 64).Select(_ => new SemaphoreSlim(1, 1)).ToArray();
    private readonly Dictionary<Guid, Task> activities = [];
    private readonly HashSet<Guid> retained = [];
    private readonly HashSet<Guid> busyTickets = [];
    private readonly Dictionary<Guid, LocalDecision> removedContent = [];
    private readonly Dictionary<string, LocalContinuation> continuations = new(StringComparer.Ordinal);
    private long inventoryRevision;
    private readonly HashSet<LocalReadSession> readers = [];
    private ArtifactInitialization? configuration;
    private SemaphoreSlim? slots;
    private int waiters;
    private long reserved;
    private volatile bool stopping;
    private CancellationTokenSource shutdown = new();

    private ArtifactStoreIdentity StoreIdentity => configuration!.Store;
    private ArtifactLimits Limits => configuration!.Limits;
    private DateTimeOffset Now()
    {
        var now = time.GetUtcNow();
        if (now < ownership!.State.TimeFloor) { return ownership.State.TimeFloor; }
        ownership.AdvanceTime(now);
        return now;
    }

    private ArtifactOperationTicket Ticket(LocalOperation operation)
        => new(StoreIdentity, operation.Id, operation.Kind, operation.Issued, operation.Expires, operation.Fingerprint);
    private ArtifactStagingOwner Owner(LocalOperation operation)
        => new(Ticket(operation), operation.Session, operation.Owner, operation.Generation, operation.OwnerExpires);
    private ArtifactStagedWrite Staged(LocalOperation operation)
        => new(Owner(operation), operation.Content!.Stamp(StoreIdentity).Identity, operation.Verified, operation.Owner.ToString("N"));
    private string StagePath(LocalOperation operation) => ownership!.RecordPath("staging", operation.Owner.ToString("N"), ".part");
    private string PayloadPath(LocalContent content) => ownership!.RecordPath("data", content.Incarnation.ToString("N"), ".blob");
    private void Save(LocalOperation operation)
    {
        inventoryRevision = checked(inventoryRevision + 1);
        faults.BeforeRecordWrite?.Invoke();
        ownership!.WriteRecord("tickets", operation.Id.ToString("N"), operation);
    }
    private void Save(LocalDecision decision)
    {
        ownership!.WriteRecord("decisions", decision.Content.Digest, decision);
        decisions[decision.Content.Digest] = decision;
        inventoryRevision = checked(inventoryRevision + 1);
    }

    private LocalOperation Find(ArtifactOperationTicket ticket, ArtifactOperationKind? kind = null)
    {
        if (ticket.Store != StoreIdentity || !operations.TryGetValue(ticket.Id, out var operation)
            || Ticket(operation) != ticket || kind is { } required && operation.Kind != required)
        { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
        if (Now() >= operation.Expires)
        {
            ownership!.PersistTime();
            throw new LocalStateException(ArtifactFailureCode.ReconciliationExpired);
        }
        return operation;
    }

    private void CheckOwner(LocalOperation operation, ArtifactStagingOwner owner, bool requireVerified = false)
    {
        if (owner != Owner(operation) || operation.Session != ownership!.State.SessionId
            || Now() >= operation.OwnerExpires || operation.State != (requireVerified ? "verified" : "staging"))
        { throw new LocalStateException(ArtifactFailureCode.Conflict); }
    }

    private SemaphoreSlim DigestGate(string digest)
        => digestGates[Convert.ToByte(digest[..2], 16) % digestGates.Length];

    private bool IsBusy(Guid id) { lock (activitySync) { return busyTickets.Contains(id); } }
    public Task WhenIdleForQualificationAsync()
    { lock (activitySync) { return Task.WhenAll(activities.Values.ToArray()); } }

    private async Task<Slot> AdmitAsync(CancellationToken ct)
    {
        lock (stateSync)
        {
            if (slots!.Wait(0)) { return new Slot(slots); }
            if (waiters >= Limits.WaitingCalls) { throw new LocalStateException(ArtifactFailureCode.Capacity); }
            waiters++;
        }
        try
        {
            await faults.ObserveAsync("transfer.queued");
            await slots.WaitAsync(ct);
            return new Slot(slots);
        }
        finally { lock (stateSync) { waiters--; } }
    }

    private async ValueTask<ArtifactResult<T>> ExecuteAsync<T>(ArtifactPhase phase, TimeSpan budget,
        CancellationToken ct, Func<CancellationToken, Task<T>> work, ArtifactOperationTicket? ticket = null,
        Action? settled = null, Action? cancellationSettled = null)
        where T : notnull
    {
        ArgumentNullException.ThrowIfNull(work);
        var id = Guid.NewGuid();
        Task<ArtifactResult<T>> activity;
        var deadline = new CancellationTokenSource(budget, time);
        var cancellation = CancellationTokenSource.CreateLinkedTokenSource(ct, deadline.Token, shutdown.Token);
        var token = cancellation.Token;
        lock (activitySync)
        {
            if (!initialized || stopping || Volatile.Read(ref lifecycleActive) != 0 || retained.Count > 0 || !incompleteReadCloses.IsEmpty)
            {
                cancellation.Dispose();
                deadline.Dispose();
                settled?.Invoke();
                return Failed<T>(retained.Count > 0 || !incompleteReadCloses.IsEmpty ? ArtifactFailureCode.CleanupIncomplete : ArtifactFailureCode.Disposed,
                    phase, ticket, retained.Count > 0 || !incompleteReadCloses.IsEmpty);
            }
            if (activities.Count >= Limits.TransferSlots + Limits.WaitingCalls)
            {
                cancellation.Dispose();
                deadline.Dispose();
                settled?.Invoke();
                return Failed<T>(ArtifactFailureCode.Capacity, phase, ticket);
            }
            var mutation = ticket is not null && phase is ArtifactPhase.Stage or ArtifactPhase.Publication or ArtifactPhase.Delete;
            if (mutation && !busyTickets.Add(ticket!.Id))
            {
                cancellation.Dispose();
                deadline.Dispose();
                settled?.Invoke();
                return Failed<T>(ArtifactFailureCode.Conflict, phase, ticket);
            }
            activity = Task.Run(async () =>
            {
                try
                {
                    token.ThrowIfCancellationRequested();
                    return (ArtifactResult<T>)new ArtifactResult<T>.Success(await work(token));
                }
                catch (Exception error)
                {
                    var code = FailureCode(error, ct);
                    if (code is ArtifactFailureCode.CancelledBeforeCommit or ArtifactFailureCode.DeadlineExceeded)
                    {
                        try { cancellationSettled?.Invoke(); }
                        catch (Exception settlementError) { return Failed<T>(FailureCode(settlementError, ct), phase, ticket); }
                    }
                    if (code == ArtifactFailureCode.CancelledBeforeCommit && !ct.IsCancellationRequested && token.IsCancellationRequested)
                    { code = ArtifactFailureCode.DeadlineExceeded; }
                    return Failed<T>(code, phase, ticket);
                }
                finally
                {
                    lock (activitySync)
                    {
                        activities.Remove(id);
                        retained.Remove(id);
                        if (mutation) { busyTickets.Remove(ticket!.Id); }
                    }
                    cancellation.Dispose();
                    deadline.Dispose();
                    settled?.Invoke();
                }
            }, CancellationToken.None);
            activities.Add(id, activity);
        }
        try { return await activity.WaitAsync(token); }
        catch (OperationCanceledException)
        {
            lock (activitySync)
            {
                if (!activity.IsCompleted) { retained.Add(id); }
                return Failed<T>(ct.IsCancellationRequested ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded,
                    phase, ticket, !activity.IsCompleted);
            }
        }
    }

    private ArtifactResult<T> Failed<T>(ArtifactFailureCode code, ArtifactPhase phase,
        ArtifactOperationTicket? ticket = null, bool live = false) where T : notnull
    {
        if (code is not (ArtifactFailureCode.InvalidInput or ArtifactFailureCode.ReconciliationExpired)
            && ticket is not null && operations.TryGetValue(ticket.Id, out var operation) && Ticket(operation) == ticket
            && operation.State is "deciding" or "committed" or "removed" && phase is ArtifactPhase.Publication or ArtifactPhase.Delete)
        { code = ArtifactFailureCode.Uncertain; }
        return new ArtifactResult<T>.Failure(code, phase,
            code == ArtifactFailureCode.Uncertain ? ArtifactAction.ReconcileExactTicket : ArtifactAction.Reobserve,
            Guid.NewGuid(), ticket is null ? null : new ArtifactOption<ArtifactOperationTicket>.Some(ticket),
            live || code == ArtifactFailureCode.CleanupIncomplete ? ArtifactCleanupState.RetainedLiveOwnership : ArtifactCleanupState.Released);
    }

    private static ArtifactFailureCode FailureCode(Exception error, CancellationToken caller) => error switch
    {
        LocalStateException state => state.Code,
        OperationCanceledException => caller.IsCancellationRequested ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded,
        UnauthorizedAccessException => ArtifactFailureCode.AccessDenied,
        IOException io when (io.HResult & 0xffff) is 28 or 112 => ArtifactFailureCode.Capacity,
        IOException => ArtifactFailureCode.Unavailable,
        ArgumentException => ArtifactFailureCode.InvalidInput,
        _ => ArtifactFailureCode.InternalFailure
    };

    private static string Fingerprint(object value) => Convert.ToHexStringLower(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(value)));
    private sealed class Slot(SemaphoreSlim semaphore) : IDisposable
    {
        private int disposed;
        public void Dispose() { if (Interlocked.Exchange(ref disposed, 1) == 0) { semaphore.Release(); } }
    }
}
