using System.Collections.Immutable;
using System.Diagnostics;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Memory;

public sealed partial class MemoryMetadataStore : IMetadataStore, IMetadataSchemaAdministration
{
    private readonly IMetadataPublicationAuthority authority;
    private readonly TimeProvider clock;
    private readonly Func<string, ValueTask> observe;
    private readonly Action<string> diagnostic;
    private readonly SemaphoreSlim writer = new(1, 1);
    private readonly object activitiesLock = new();
    private readonly HashSet<MemoryActivity> activities = [];
    private MemoryState state;
    private int lateActivities;
    private bool admitted;
    private bool disposed;
    private MetadataRecoveryPoint? logicalAuthorization;
    private long authorizationChange;
    private TaskCompletionSource? idle;
    private readonly int applicationSchema;

    public MemoryMetadataStore(IMetadataPublicationAuthority publicationAuthority, TimeProvider timeProvider,
        Func<string, ValueTask> observer, Action<string> safeDiagnostic, int initialSchema = 0,
        int compatibleSchema = 2, MemoryFixtureImage? logicalImage = null)
    {
        ArgumentNullException.ThrowIfNull(publicationAuthority);
        ArgumentNullException.ThrowIfNull(timeProvider);
        ArgumentNullException.ThrowIfNull(observer);
        ArgumentNullException.ThrowIfNull(safeDiagnostic);
        if (initialSchema is < 0 or > 4) { throw new ArgumentException("Invalid synthetic schema state."); }
        if (compatibleSchema is not 1 and not 2) { throw new ArgumentException("Invalid synthetic application schema."); }
        authority = publicationAuthority;
        clock = timeProvider;
        observe = observer;
        diagnostic = safeDiagnostic;
        applicationSchema = compatibleSchema;
        state = logicalImage?.State ?? MemoryState.Empty(initialSchema);
    }

    public ValueTask<MetadataResult<MetadataOperationTicket>> ReserveOperationAsync(MetadataCallOptions options, CancellationToken cancellationToken) =>
        Dispatch(options?.EffectiveTimeout, TimeSpan.FromSeconds(30), cancellationToken, MetadataPhase.Reserve, null, true, ReserveCoreAsync);

    public ValueTask<MetadataResult<MetadataReadSnapshot>> ReadAsync(MetadataReadGroup request, MetadataCallOptions options, CancellationToken cancellationToken) =>
        Dispatch(options?.EffectiveTimeout, TimeSpan.FromSeconds(30), cancellationToken, MetadataPhase.Read, null, true,
            activity => ReadCoreAsync(request, activity));

    public ValueTask<MetadataResult<MetadataPage>> ReadPageAsync(MetadataPageQuery request, MetadataCallOptions options, CancellationToken cancellationToken) =>
        Dispatch(options?.EffectiveTimeout, TimeSpan.FromSeconds(30), cancellationToken, MetadataPhase.Page, null, true,
            activity => PageCoreAsync(request, activity));

    public ValueTask<MetadataResult<MetadataCommitReceipt>> CommitAsync(MetadataMutationBatch request, MetadataCallOptions options, CancellationToken cancellationToken) =>
        Dispatch(options?.EffectiveTimeout, TimeSpan.FromSeconds(30), cancellationToken, MetadataPhase.Commit, request?.Ticket, true,
            activity => CommitCoreAsync(request!, activity));

    public ValueTask<MetadataResult<MetadataResolution>> ReconcileAsync(MetadataOperationTicket ticket, MetadataCallOptions options, CancellationToken cancellationToken) =>
        Dispatch(options?.EffectiveTimeout, TimeSpan.FromSeconds(30), cancellationToken, MetadataPhase.Reconcile, ticket, true,
            activity => ReconcileCoreAsync(ticket, activity));

    public ValueTask<MetadataResult<MetadataSchemaInspection>> InspectAsync(MetadataAdministrationOptions options, CancellationToken cancellationToken) =>
        Dispatch(options?.EffectiveTimeout, TimeSpan.FromMinutes(2), cancellationToken, MetadataPhase.Schema, null, false, InspectCoreAsync);

    public ValueTask<MetadataResult<MetadataSchemaAdmission>> PrepareAsync(MetadataSchemaRequest request, MetadataAdministrationOptions options, CancellationToken cancellationToken) =>
        Dispatch(options?.EffectiveTimeout, TimeSpan.FromMinutes(2), cancellationToken, MetadataPhase.Schema, null, false,
            activity => PrepareCoreAsync(request, activity));

    private ValueTask<MetadataResult<T>> Dispatch<T>(TimeSpan? timeout, TimeSpan maximum, CancellationToken token,
        MetadataPhase phase, MetadataOperationTicket? ticket, bool requiresAdmission,
        Func<MemoryActivity, ValueTask<MetadataResult<T>>> action, bool independentRead = false) where T : notnull
    {
        if (timeout is null || timeout < TimeSpan.FromMilliseconds(1) || timeout > maximum)
        { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.InvalidInput, phase)); }
        MemoryActivity activity;
        Task<MetadataResult<T>> result;
        lock (activitiesLock)
        {
            if (disposed) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.Disposed, phase)); }
            if (lateActivities != 0 && !independentRead) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.Unavailable, phase, ticket)); }
            if (requiresAdmission && state.Schema == 4) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.CorruptState, phase)); }
            if (requiresAdmission && !admitted) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.IncompatibleSchema, phase)); }
            if (activities.Count >= 33) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.Capacity, phase, ticket)); }
            activity = new(timeout.Value, token);
            if (activities.Count == 0) { idle = new(TaskCreationOptions.RunContinuationsAsynchronously); }
            activities.Add(activity);
            result = Task.Run(async () =>
            {
                try
                {
                    activity.Check();
                    return await action(activity);
                }
                catch (MemoryContractFailure failure)
                { return Failure<T>(activity.Attempted ? MetadataFailureCode.Uncertain : failure.Code, phase, ticket); }
                catch (MemoryBudgetEnded)
                {
                    return Failure<T>(activity.Attempted ? MetadataFailureCode.Uncertain : token.IsCancellationRequested
                    ? MetadataFailureCode.CancelledBeforeCommit : MetadataFailureCode.DeadlineExceeded, phase, ticket);
                }
                catch (ArgumentException) { return Failure<T>(activity.Attempted ? MetadataFailureCode.Uncertain : MetadataFailureCode.InvalidInput, phase, ticket); }
                catch (OverflowException) { return Failure<T>(activity.Attempted ? MetadataFailureCode.Uncertain : MetadataFailureCode.Capacity, phase, ticket); }
                catch (IOException) { return Failure<T>(activity.Attempted ? MetadataFailureCode.Uncertain : MetadataFailureCode.Unavailable, phase, ticket); }
                catch (Exception)
                {
                    diagnostic("metadata.internal_failure");
                    return Failure<T>(activity.Attempted ? MetadataFailureCode.Uncertain : MetadataFailureCode.InternalFailure, phase, ticket);
                }
                finally
                {
                    lock (activitiesLock)
                    {
                        activities.Remove(activity);
                        if (activity.Late) { lateActivities--; }
                        if (activities.Count == 0) { idle?.TrySetResult(); }
                    }

                }
            });
            activity.Task = result;
        }
        return new(WaitAsync(result, activity, phase, ticket));
    }

    public Task WhenIdleAsync() => ObserveWorkSettlementForTest().WaitAsync(TimeSpan.FromSeconds(10));

    public Task ObserveWorkSettlementForTest()
    {
        lock (activitiesLock) { return idle?.Task ?? Task.CompletedTask; }
    }

    public MemoryFixtureImage CaptureLogicalImage()
    {
        lock (activitiesLock)
        {
            if (disposed || activities.Count != 0) { throw new InvalidOperationException("Logical image requires an idle fixture."); }
            return new(state);
        }
    }

    public MemoryFixtureImage CloseAndCaptureLogicalImageForTest()
    {
        lock (activitiesLock)
        {
            if (disposed || activities.Count != 0) { throw new InvalidOperationException("Logical reopen requires an idle fixture."); }
            disposed = true;
            admitted = false;
            return new(state);
        }
    }

    public ValueTask<MetadataResult<MetadataReadSnapshot>> ReadIndependentSnapshotForTestAsync(
        MetadataReadGroup request, CancellationToken cancellationToken) =>
        Dispatch(TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(30), cancellationToken, MetadataPhase.Read, null, true,
            activity => ReadCoreAsync(request, activity, false), independentRead: true);

    private async Task<MetadataResult<T>> WaitAsync<T>(Task<MetadataResult<T>> task, MemoryActivity activity,
        MetadataPhase phase, MetadataOperationTicket? ticket) where T : notnull
    {
        while (!task.IsCompleted)
        {
            if (activity.Ended)
            {
                activity.Abandon();
                lock (activitiesLock)
                {
                    if (activities.Contains(activity)) { activity.Late = true; lateActivities++; }
                }
                if (task.IsCompleted) { break; }
                return Failure<T>(activity.Attempted ? MetadataFailureCode.Uncertain :
                    activity.Cancelled ? MetadataFailureCode.CancelledBeforeCommit : MetadataFailureCode.DeadlineExceeded, phase, ticket);
            }
            await Task.WhenAny(task, Task.Delay(TimeSpan.FromMilliseconds(1)));
        }
        return await task;
    }

    private async ValueTask EnterWriterAsync(MemoryActivity activity)
    {
        while (!await writer.WaitAsync(0))
        {
            activity.Check();
            await Task.Delay(TimeSpan.FromMilliseconds(1));
        }
        try { activity.Check(); }
        catch { writer.Release(); throw; }
    }

    private static MetadataResult<T> Success<T>(T value) where T : notnull => new MetadataResult<T>.Success(value);
    private static MetadataResult<T> Failure<T>(MetadataFailureCode code, MetadataPhase phase, MetadataOperationTicket? ticket = null) where T : notnull
    {
        if (phase == MetadataPhase.Reconcile && ticket is not null
            && code is MetadataFailureCode.DeadlineExceeded or MetadataFailureCode.CancelledBeforeCommit
                or MetadataFailureCode.Unavailable or MetadataFailureCode.Capacity)
        { code = MetadataFailureCode.Uncertain; }
        return new MetadataResult<T>.Failure(code, phase, code switch
        {
            MetadataFailureCode.InvalidInput => MetadataRetryDisposition.CorrectInput,
            MetadataFailureCode.Uncertain => ticket is null ? MetadataRetryDisposition.OperatorRecovery : MetadataRetryDisposition.Reconcile,
            MetadataFailureCode.DeadlineExceeded or MetadataFailureCode.CancelledBeforeCommit =>
                phase == MetadataPhase.Schema ? MetadataRetryDisposition.OperatorRecovery : MetadataRetryDisposition.RetrySameTicket,
            MetadataFailureCode.CorruptState or MetadataFailureCode.IncompatibleSchema or MetadataFailureCode.InternalFailure => MetadataRetryDisposition.OperatorRecovery,
            _ => MetadataRetryDisposition.None
        }, new(Guid.NewGuid()), ticket is null ? new MetadataOption<MetadataOperationTicket>.None()
            : new MetadataOption<MetadataOperationTicket>.Some(ticket));
    }

    private async ValueTask<MetadataResult<MetadataReadSnapshot>> ReadCoreAsync(
        MetadataReadGroup request, MemoryActivity activity, bool observeItems = true)
    {
        _ = MetadataEncoding.Encode(request);
        var captured = Volatile.Read(ref state);
        if (captured.Schema == 4) { throw new MemoryContractFailure(MetadataFailureCode.CorruptState); }
        var result = ImmutableArray.CreateBuilder<MetadataReadItem>(request.Selectors.Length);
        foreach (var selector in request.Selectors)
        {
            activity.Check();
            result.Add(captured.Records.TryGetValue(selector, out var record)
                ? new MetadataReadItem.Found(record) : new MetadataReadItem.NotFound(selector));
            if (observeItems) { await observe("read.item"); }
        }
        var snapshot = new MetadataReadSnapshot(result.MoveToImmutable());
        _ = MetadataEncoding.Encode(snapshot);
        activity.Check();
        return Success(snapshot);
    }

    public async ValueTask DisposeAsync()
    {
        Task[] pending;
        lock (activitiesLock)
        {
            disposed = true;
            admitted = false;
            foreach (var activity in activities) { activity.Abandon(); }
            pending = activities.Select(activity => activity.Task!).ToArray();
        }
        try { await Task.WhenAll(pending).WaitAsync(TimeSpan.FromSeconds(30)); }
        catch (TimeoutException)
        {
            diagnostic("metadata.cleanup_incomplete");
            throw new InvalidOperationException("Memory metadata cleanup incomplete; live work remains owned.");
        }
    }

    private sealed class MemoryActivity(TimeSpan timeout, CancellationToken token)
    {
        private readonly long start = Stopwatch.GetTimestamp();
        private int decision;
        public Task? Task { get; set; }
        public bool Late { get; set; }
        public bool Cancelled => token.IsCancellationRequested;
        public bool Ended => Cancelled || Stopwatch.GetElapsedTime(start) >= timeout;
        public bool Attempted => Volatile.Read(ref decision) is 1 or 2;
        public TimeSpan Remaining => TimeSpan.FromTicks(Math.Max(0, (timeout - Stopwatch.GetElapsedTime(start)).Ticks));
        public void Abandon() => Interlocked.CompareExchange(ref decision, 3, 0);
        public void Check()
        {
            if (Ended || Volatile.Read(ref decision) == 3) { throw new MemoryBudgetEnded(); }
        }
        public void CommitDecision()
        {
            Check();
            if (Interlocked.CompareExchange(ref decision, 1, 0) != 0) { throw new MemoryBudgetEnded(); }
        }
        public void Committed() => Interlocked.Exchange(ref decision, 2);
    }
    private sealed class MemoryBudgetEnded : Exception;
}
