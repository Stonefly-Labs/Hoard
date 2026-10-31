using System.Diagnostics;
using System.Threading.Channels;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Sqlite;

internal sealed class SqliteWorkBudget(TimeSpan timeout, CancellationToken cancellationToken)
{
    private readonly long started = Stopwatch.GetTimestamp();
    private int decision;
    public bool Cancelled => cancellationToken.IsCancellationRequested;
    public bool Expired => Stopwatch.GetElapsedTime(started) >= timeout;
    public bool Abandoned => Volatile.Read(ref decision) == 3;
    public bool Attempted => Volatile.Read(ref decision) is 1 or 2;
    public TimeSpan Remaining => TimeSpan.FromTicks(Math.Max(0, (timeout - Stopwatch.GetElapsedTime(started)).Ticks));
    public bool TryCommitDecision() => !Cancelled && !Expired && Interlocked.CompareExchange(ref decision, 1, 0) == 0;
    public void Committed() => Interlocked.Exchange(ref decision, 2);
    public void Abandon() => Interlocked.CompareExchange(ref decision, 3, 0);
    public void Check()
    {
        if (Cancelled || Expired || Abandoned) { throw new SqliteBudgetFailure(Cancelled); }
    }
}

internal sealed class SqliteBudgetFailure(bool cancelled) : Exception("Private metadata budget ended.")
{
    public bool Cancelled { get; } = cancelled;
}

internal sealed partial class SqliteWorker(Func<ValueTask> cleanup, Action<string> diagnostic)
{
    private readonly Channel<IWork> queue = Channel.CreateBounded<IWork>(new BoundedChannelOptions(32)
    { SingleReader = true, FullMode = BoundedChannelFullMode.Wait });
    private Task? owned;
    private int closed;
    private int late;
    private IWork? currentWork;
    private TaskCompletionSource? idle;
    private readonly object startLock = new();

    public ValueTask<MetadataResult<T>> Submit<T>(TimeSpan timeout, CancellationToken cancellationToken,
        MetadataPhase phase, MetadataOperationTicket? ticket, Func<SqliteWorkBudget, ValueTask<MetadataResult<T>>> action)
        where T : notnull
    {
        if (Volatile.Read(ref closed) != 0) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.Disposed, phase)); }
        if (Volatile.Read(ref late) != 0) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.Unavailable, phase, ticket)); }
        var work = new Work<T>(new(timeout, cancellationToken), phase, ticket, action, diagnostic);
        lock (startLock)
        {
            if (closed != 0) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.Disposed, phase)); }
            if (late != 0) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.Unavailable, phase, ticket)); }
            if (idle is null || idle.Task.IsCompleted) { idle = new(TaskCreationOptions.RunContinuationsAsynchronously); }
            owned ??= Task.Run(ProcessAsync);
            if (!queue.Writer.TryWrite(work)) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.Capacity, phase, ticket)); }
        }
        return new(WaitAsync(work));
    }

    private async Task<MetadataResult<T>> WaitAsync<T>(Work<T> work) where T : notnull
    {
        while (!work.Completion.Task.IsCompleted)
        {
            if (work.Budget.Cancelled || work.Budget.Expired)
            {
                work.Budget.Abandon();
                lock (startLock)
                {
                    if (ReferenceEquals(currentWork, work) && !work.Completion.Task.IsCompleted) { late = 1; }
                }
                if (work.Completion.Task.IsCompleted) { break; }
                return work.Budget.Attempted
                    ? Failure<T>(MetadataFailureCode.Uncertain, work.Phase, work.Ticket)
                    : Failure<T>(work.Budget.Cancelled ? MetadataFailureCode.CancelledBeforeCommit : MetadataFailureCode.DeadlineExceeded, work.Phase, work.Ticket);
            }
            await Task.WhenAny(work.Completion.Task, Task.Delay(TimeSpan.FromMilliseconds(1)));
        }
        return await work.Completion.Task;
    }

    private async Task ProcessAsync()
    {
        try
        {
            await foreach (var work in queue.Reader.ReadAllAsync())
            {
                if (Volatile.Read(ref closed) != 0) { work.Budget.Abandon(); }
                lock (startLock) { currentWork = work; }
                try { await work.ExecuteAsync(); }
                finally
                {
                    lock (startLock)
                    {
                        currentWork = null;
                        late = 0;
                        if (queue.Reader.Count == 0) { idle?.TrySetResult(); }
                    }
                }
            }

        }
        finally
        {
            Task independentSettlement;
            lock (startLock)
            {
                closed = 1;
                queue.Writer.TryComplete();
                foreach (var lease in independentLeases) { lease.Release(); }
                independentSettlement = independentIdle?.Task ?? Task.CompletedTask;
            }
            try { await independentSettlement; }
            finally { await cleanup(); }
            lock (startLock)
            {
                if (independentCleanupFailed) { throw new InvalidOperationException("CleanupIncomplete"); }
            }
        }
    }

    public Task WhenIdleAsync()
    {
        lock (startLock)
        {
            return Task.WhenAll(idle?.Task ?? Task.CompletedTask, independentReadsIdle?.Task ?? Task.CompletedTask)
                .WaitAsync(TimeSpan.FromSeconds(10));
        }
    }

    public Task ObserveLifetimeSettlementForTest()
    {
        lock (startLock) { return owned ?? Task.CompletedTask; }
    }

    public async ValueTask StopAsync()
    {
        Task? current;
        lock (startLock)
        {
            closed = 1;
            currentWork?.Budget.Abandon();
            foreach (var lease in independentLeases) { lease.Release(); }
            queue.Writer.TryComplete();
            current = owned;
        }
        if (current is null) { return; }
        try { await current.WaitAsync(TimeSpan.FromSeconds(30)); }
        catch (TimeoutException)
        {
            diagnostic("metadata.cleanup_incomplete");
            throw new InvalidOperationException("Metadata cleanup incomplete; live work remains owned.");
        }
    }

    internal static MetadataResult<T> Failure<T>(MetadataFailureCode code, MetadataPhase phase,
        MetadataOperationTicket? ticket = null) where T : notnull
    {
        if (phase == MetadataPhase.Reconcile && ticket is not null
            && code is MetadataFailureCode.DeadlineExceeded or MetadataFailureCode.CancelledBeforeCommit
                or MetadataFailureCode.Unavailable or MetadataFailureCode.Capacity)
        { code = MetadataFailureCode.Uncertain; }
        return new MetadataResult<T>.Failure(code, phase, code switch
        {
            MetadataFailureCode.InvalidInput => MetadataRetryDisposition.CorrectInput,
            MetadataFailureCode.Uncertain => ticket is null ? MetadataRetryDisposition.OperatorRecovery : MetadataRetryDisposition.Reconcile,
            MetadataFailureCode.CancelledBeforeCommit or MetadataFailureCode.DeadlineExceeded =>
                phase == MetadataPhase.Schema ? MetadataRetryDisposition.OperatorRecovery : MetadataRetryDisposition.RetrySameTicket,
            MetadataFailureCode.CorruptState or MetadataFailureCode.IncompatibleSchema or MetadataFailureCode.InternalFailure => MetadataRetryDisposition.OperatorRecovery,
            _ => MetadataRetryDisposition.None
        }, new(Guid.NewGuid()), ticket is null ? new MetadataOption<MetadataOperationTicket>.None()
            : new MetadataOption<MetadataOperationTicket>.Some(ticket));
    }

    private interface IWork
    {
        SqliteWorkBudget Budget { get; }
        ValueTask ExecuteAsync();
    }

    private sealed class Work<T>(SqliteWorkBudget budget, MetadataPhase phase, MetadataOperationTicket? ticket,
        Func<SqliteWorkBudget, ValueTask<MetadataResult<T>>> action, Action<string> diagnostic) : IWork where T : notnull
    {
        public SqliteWorkBudget Budget { get; } = budget;
        public MetadataPhase Phase { get; } = phase;
        public MetadataOperationTicket? Ticket { get; } = ticket;
        public int Started;
        public TaskCompletionSource<MetadataResult<T>> Completion { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        public async ValueTask ExecuteAsync()
        {
            Volatile.Write(ref Started, 1);
            MetadataResult<T> result;
            try { Budget.Check(); result = await action(Budget); }
            catch (SqliteBudgetFailure ended)
            {
                result = Failure<T>(Budget.Attempted ? MetadataFailureCode.Uncertain
                    : ended.Cancelled ? MetadataFailureCode.CancelledBeforeCommit : MetadataFailureCode.DeadlineExceeded, Phase, Ticket);
            }
            catch (ArgumentException) { result = Failure<T>(MetadataFailureCode.InvalidInput, Phase, Ticket); }
            catch (SqliteContractFailure rejection) { result = Failure<T>(rejection.Code, Phase, Ticket); }
            catch (OverflowException) { result = Failure<T>(MetadataFailureCode.Capacity, Phase, Ticket); }
            catch (SqliteNativeFailure error)
            {
                result = Failure<T>(Budget.Attempted ? MetadataFailureCode.Uncertain : error.Code switch
                {
                    5 or 6 => MetadataFailureCode.Unavailable,
                    7 or 13 => MetadataFailureCode.Capacity,
                    11 or 26 => MetadataFailureCode.CorruptState,
                    _ => MetadataFailureCode.Unavailable
                }, Phase, Ticket);
            }
            catch (Microsoft.Data.Sqlite.SqliteException error)
            {
                result = Failure<T>(error.SqliteErrorCode is 11 or 26 ? MetadataFailureCode.CorruptState : MetadataFailureCode.Unavailable, Phase, Ticket);
            }
            catch (IOException) { result = Failure<T>(MetadataFailureCode.Unavailable, Phase, Ticket); }
            catch (UnauthorizedAccessException) { result = Failure<T>(MetadataFailureCode.Unavailable, Phase, Ticket); }
            catch (System.Text.Json.JsonException)
            { result = Failure<T>(MetadataFailureCode.CorruptState, Phase, Ticket); }
            catch (Exception)
            {
                diagnostic("metadata.internal_failure");
                result = Failure<T>(Budget.Attempted ? MetadataFailureCode.Uncertain : MetadataFailureCode.InternalFailure, Phase, Ticket);
            }
            if (Budget.Attempted && result is MetadataResult<T>.Failure)
            { result = Failure<T>(MetadataFailureCode.Uncertain, Phase, Ticket); }
            Completion.TrySetResult(result);
        }
    }
}
