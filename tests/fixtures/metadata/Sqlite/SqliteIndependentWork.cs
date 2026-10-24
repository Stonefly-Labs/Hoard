using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Sqlite;

internal sealed partial class SqliteWorker
{
    private readonly HashSet<IndependentLease> independentLeases = [];
    private int independentCount;
    private int independentReads;
    private TaskCompletionSource? independentIdle;
    private TaskCompletionSource? independentReadsIdle;
    private bool independentCleanupFailed;

    public ValueTask<MetadataResult<T>> SubmitIndependent<T>(CancellationToken cancellationToken,
        Func<SqliteWorkBudget, ValueTask<MetadataResult<T>>> action) where T : notnull
    {
        var work = new Work<T>(new(TimeSpan.FromSeconds(5), cancellationToken),
            MetadataPhase.Read, null, action, diagnostic);
        lock (startLock)
        {
            if (closed != 0) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.Disposed, MetadataPhase.Read)); }
            if (independentCount >= 32) { return ValueTask.FromResult(Failure<T>(MetadataFailureCode.Capacity, MetadataPhase.Read)); }
            BeginIndependent(read: true);
            _ = Task.Run(async () =>
            {
                try { await work.ExecuteAsync(); }
                catch (Exception error)
                {
                    lock (startLock) { independentCleanupFailed = true; }
                    work.Completion.TrySetException(error);
                    _ = work.Completion.Task.Exception;
                }
                finally { EndIndependent(read: true); }
            });
        }
        return new(WaitAsync(work));
    }

    public async ValueTask<IAsyncDisposable> HoldIndependentAsync(
        Func<ValueTask<IDisposable>> acquire, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var lease = new IndependentLease(acquire);
        lock (startLock)
        {
            if (closed != 0 || independentCount >= 32) { throw new InvalidOperationException("OwnershipInvalid"); }
            BeginIndependent(read: false);
            independentLeases.Add(lease);
            lease.Work = Task.Run(async () =>
            {
                try { await lease.RunAsync(); }
                catch
                {
                    lock (startLock) { independentCleanupFailed = true; }
                    lease.CleanupFailed = true;
                }
                finally
                {
                    lock (startLock) { independentLeases.Remove(lease); }
                    EndIndependent(read: false);
                }
            });
        }
        try { return await lease.Ready.WaitAsync(TimeSpan.FromSeconds(5), cancellationToken); }
        catch
        {
            lease.Release();
            throw;
        }
    }

    private void BeginIndependent(bool read)
    {
        if (independentCount++ == 0) { independentIdle = new(TaskCreationOptions.RunContinuationsAsynchronously); }
        // A held writer is a lifetime resource, not an operation preventing ordinary idle.
        if (read && independentReads++ == 0) { independentReadsIdle = new(TaskCreationOptions.RunContinuationsAsynchronously); }
        owned ??= Task.Run(ProcessAsync);
    }

    private void EndIndependent(bool read)
    {
        lock (startLock)
        {
            if (read && --independentReads == 0) { independentReadsIdle?.TrySetResult(); }
            if (--independentCount == 0) { independentIdle?.TrySetResult(); }
        }
    }

    private sealed class IndependentLease(Func<ValueTask<IDisposable>> acquire) : IAsyncDisposable
    {
        private readonly TaskCompletionSource<IAsyncDisposable> ready = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private readonly TaskCompletionSource released = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public Task Work { get; set; } = Task.CompletedTask;
        public bool CleanupFailed { get; set; }
        public Task<IAsyncDisposable> Ready => ready.Task;
        public void Release() => released.TrySetResult();

        public async Task RunAsync()
        {
            IDisposable handle;
            try { handle = await acquire(); }
            catch (Exception error)
            {
                ready.TrySetException(error);
                _ = ready.Task.Exception;
                return;
            }
            using (handle)
            {
                ready.TrySetResult(this);
                await released.Task;
            }
        }

        public async ValueTask DisposeAsync()
        {
            Release();
            await Work;
            if (CleanupFailed) { throw new InvalidOperationException("CleanupIncomplete"); }
        }
    }
}
