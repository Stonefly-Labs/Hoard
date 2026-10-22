using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.HostAdapters;

public sealed record ArtifactReferenceDecision(bool Available, long LiveReferences, Guid Revision);

public sealed class ArtifactCoordinationAuthority : IArtifactCoordinationAuthority
{
    private readonly ArtifactStoreIdentity store;
    private readonly TimeProvider clock;
    private readonly Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceDecision>>? references;
    private readonly object sync = new();
    private readonly Dictionary<string, Gate> gates = [];
    private readonly Dictionary<Guid, Holding> operations = [];
    private readonly Dictionary<Guid, Task> retainedWork = [];
    private readonly Guid instance = Guid.NewGuid();
    private DateTimeOffset timeFloor = DateTimeOffset.UnixEpoch;
    private long generation;
    private int waiting;

    public bool HasRetainedWork { get { lock (sync) { return retainedWork.Count > 0; } } }
    public int WaitingAdmissions { get { lock (sync) { return waiting; } } }

    public async ValueTask<bool> DrainRetainedAsync(TimeSpan timeout, CancellationToken ct = default)
    {
        Task[] pending;
        lock (sync) { pending = retainedWork.Values.ToArray(); }
        try
        {
            await Task.WhenAll(pending).WaitAsync(timeout, ct);
            return !HasRetainedWork;
        }
        catch (TimeoutException) { return false; }
        catch (OperationCanceledException) { return false; }
    }

    public ArtifactCoordinationAuthority(ArtifactStoreIdentity store, TimeProvider? clock = null,
        Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceDecision>>? references = null)
    {
        this.store = store ?? throw new ArgumentNullException(nameof(store));
        this.clock = clock ?? TimeProvider.System;
        this.references = references;
    }

    public async ValueTask<ArtifactResult<IArtifactProtectionGuard>> AcquireAsync(
        ArtifactProtectionRequest request, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(options);
        if (request.Store != store) { return Failure(ArtifactFailureCode.Denied); }
        if (ct.IsCancellationRequested) { return Failure(ArtifactFailureCode.CancelledBeforeCommit); }
        if (request.Mode == ArtifactProtectionMode.Exclusive && references is null)
        { return Failure(ArtifactFailureCode.Denied); }
        using var deadline = new CancellationTokenSource(options.Deadline, clock);
        using var linked = CancellationTokenSource.CreateLinkedTokenSource(ct, deadline.Token);
        Waiter waiter;
        lock (sync)
        {
            if (retainedWork.Count > 0) { return Failure(ArtifactFailureCode.CleanupIncomplete); }
            if (waiting >= 32 || operations.Count >= 100000 || generation == long.MaxValue)
            { return Failure(ArtifactFailureCode.Capacity); }
            if (operations.ContainsKey(request.OperationId)
                || gates.Values.Any(gate => gate.Pending.Any(entry => entry.Request.OperationId == request.OperationId)))
            { return Failure(ArtifactFailureCode.Denied); }
            var key = request.Digest.Hex;
            if (!gates.TryGetValue(key, out var gate)) { gates[key] = gate = new Gate(key); }
            waiter = new Waiter(request, gate);
            gate.Pending.Enqueue(waiter);
            waiting++;
            Pump(gate);
        }
        Guard? guard = null;
        try
        {
            guard = await waiter.Completion.Task.WaitAsync(linked.Token);
            if (request.Mode == ArtifactProtectionMode.Exclusive)
            {
                var stamp = ((ArtifactOption<ArtifactStamp>.Some)request.Stamp).Value;
                var query = references!(stamp, linked.Token).AsTask();
                ArtifactReferenceDecision observation;
                try { observation = await query.WaitAsync(linked.Token); }
                catch (OperationCanceledException) when (!query.IsCompleted)
                {
                    lock (sync)
                    {
                        retainedWork[request.OperationId] = Task.CompletedTask;
                        var settlement = SettleRetainedAsync(query, guard);
                        if (retainedWork.ContainsKey(request.OperationId)) { retainedWork[request.OperationId] = settlement; }
                    }
                    return Failure(ArtifactFailureCode.CleanupIncomplete);
                }
                if (!observation.Available || observation.LiveReferences != 0 || observation.Revision == Guid.Empty)
                {
                    await guard.DisposeAsync();
                    return Failure(ArtifactFailureCode.Denied);
                }
            }
            if (linked.IsCancellationRequested)
            {
                await guard.DisposeAsync();
                return Failure(ct.IsCancellationRequested
                    ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded);
            }
            lock (sync)
            {
                if (Now() >= guard.Grant.AdmissionExpiry)
                {
                    Release(guard);
                    return Failure(ArtifactFailureCode.DeadlineExceeded);
                }
            }
            return new ArtifactResult<IArtifactProtectionGuard>.Success(guard);
        }
        catch (OperationCanceledException)
        {
            lock (sync)
            {
                waiter.Cancelled = true;
                if (waiter.Issued is { } issued) { Release(issued); }
                Pump(waiter.Gate);
            }
            return Failure(ct.IsCancellationRequested
                ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded);
        }
        catch (Exception)
        {
            if (guard is not null) { await guard.DisposeAsync(); }
            return Failure(ArtifactFailureCode.Unavailable);
        }
    }

    public ValueTask<ArtifactResult<IArtifactProtectionGuard>> RetainAsync(
        IArtifactProtectionGuard protection, ArtifactProtectionRequest expected,
        ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(protection);
        ArgumentNullException.ThrowIfNull(expected);
        ArgumentNullException.ThrowIfNull(options);
        lock (sync)
        {
            if (ct.IsCancellationRequested)
            { return ValueTask.FromResult(Failure(ArtifactFailureCode.CancelledBeforeCommit)); }
            if (protection is not Guard guard || guard.Authority != this || guard.Disposed
                || guard.Holding.Request != expected || expected.Store != store
                || !operations.TryGetValue(expected.OperationId, out var holding)
                || !ReferenceEquals(holding, guard.Holding))
            { return ValueTask.FromResult(Failure(ArtifactFailureCode.Denied)); }
            if (holding.References == int.MaxValue)
            { return ValueTask.FromResult(Failure(ArtifactFailureCode.Capacity)); }
            holding.References++;
            return ValueTask.FromResult<ArtifactResult<IArtifactProtectionGuard>>(
                new ArtifactResult<IArtifactProtectionGuard>.Success(new Guard(this, holding)));
        }
    }

    private DateTimeOffset Now()
    {
        var current = clock.GetUtcNow();
        if (current > timeFloor) { timeFloor = current; }
        return timeFloor;
    }

    private void Pump(Gate gate)
    {
        while (gate.Pending.TryPeek(out var next))
        {
            if (next.Cancelled)
            {
                gate.Pending.Dequeue();
                waiting--;
                continue;
            }
            if (gate.Exclusive || next.Request.Mode == ArtifactProtectionMode.Exclusive && gate.Shared > 0) { break; }
            gate.Pending.Dequeue();
            waiting--;
            if (generation == long.MaxValue)
            {
                next.Completion.TrySetException(new InvalidOperationException("Artifact authority generation exhausted."));
                continue;
            }
            var grant = new ArtifactProtectionGrant(instance, next.Request, ++generation, Now().AddSeconds(30));
            var holding = new Holding(next.Request, grant, gate);
            operations.Add(next.Request.OperationId, holding);
            if (next.Request.Mode == ArtifactProtectionMode.Exclusive) { gate.Exclusive = true; }
            else { gate.Shared++; }
            next.Issued = new Guard(this, holding);
            next.Completion.TrySetResult(next.Issued);
            if (gate.Exclusive) { break; }
        }
        if (!gate.Exclusive && gate.Shared == 0 && gate.Pending.Count == 0) { gates.Remove(gate.Key); }
    }

    private void Release(Guard guard)
    {
        if (guard.Disposed) { return; }
        guard.Disposed = true;
        var holding = guard.Holding;
        if (--holding.References != 0) { return; }
        operations.Remove(holding.Request.OperationId);
        if (holding.Request.Mode == ArtifactProtectionMode.Exclusive) { holding.Gate.Exclusive = false; }
        else { holding.Gate.Shared--; }
        Pump(holding.Gate);
    }

    private static ArtifactResult<IArtifactProtectionGuard> Failure(ArtifactFailureCode code)
        => new ArtifactResult<IArtifactProtectionGuard>.Failure(code, ArtifactPhase.Admission,
            ArtifactAction.Reobserve, Guid.NewGuid(), cleanup: code == ArtifactFailureCode.CleanupIncomplete
                ? ArtifactCleanupState.RetainedLiveOwnership : ArtifactCleanupState.Released);

    private async Task SettleRetainedAsync(Task<ArtifactReferenceDecision> query, Guard guard)
    {
        try { await query; }
        catch (Exception) { /* A failed reference query never authorizes deletion. */ }
        finally
        {
            lock (sync)
            {
                Release(guard);
                retainedWork.Remove(guard.Holding.Request.OperationId);
            }
        }
    }

    private sealed class Gate(string key)
    {
        public string Key { get; } = key;
        public Queue<Waiter> Pending { get; } = [];
        public int Shared { get; set; }
        public bool Exclusive { get; set; }
    }

    private sealed class Waiter(ArtifactProtectionRequest request, Gate gate)
    {
        public ArtifactProtectionRequest Request { get; } = request;
        public Gate Gate { get; } = gate;
        public TaskCompletionSource<Guard> Completion { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public bool Cancelled { get; set; }
        public Guard? Issued { get; set; }
    }

    private sealed class Holding(ArtifactProtectionRequest request, ArtifactProtectionGrant grant, Gate gate)
    {
        public ArtifactProtectionRequest Request { get; } = request;
        public ArtifactProtectionGrant Grant { get; } = grant;
        public Gate Gate { get; } = gate;
        public int References { get; set; } = 1;
    }

    private sealed class Guard(ArtifactCoordinationAuthority authority, Holding holding) : IArtifactProtectionGuard
    {
        public ArtifactCoordinationAuthority Authority { get; } = authority;
        public Holding Holding { get; } = holding;
        public bool Disposed { get; set; }
        public ArtifactProtectionGrant Grant => Holding.Grant;
        public ValueTask DisposeAsync()
        {
            lock (Authority.sync) { Authority.Release(this); }
            return ValueTask.CompletedTask;
        }
    }
}
