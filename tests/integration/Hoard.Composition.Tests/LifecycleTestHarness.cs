using System.Collections.Concurrent;
using Microsoft.Extensions.Logging;

namespace Hoard.Composition.Tests;

internal sealed class LifecycleTestHarness : IAsyncDisposable, ILoggerProvider
{
    internal readonly ConcurrentQueue<string> Logs = new();
    public ILogger CreateLogger(string categoryName) => new CapturedLogger(Logs);
    void IDisposable.Dispose() { }
    private sealed class CapturedLogger(ConcurrentQueue<string> logs) : ILogger
    {
        public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;
        public bool IsEnabled(LogLevel level) => true;
        public void Log<TState>(LogLevel level, EventId id, TState state, Exception? error,
            Func<TState, Exception?, string> formatter) => logs.Enqueue(formatter(state, error) + error);
    }
    internal static async Task Until(Func<bool> predicate)
    {
        var deadline = System.Diagnostics.Stopwatch.StartNew();
        while (!predicate())
        {
            if (deadline.Elapsed > TimeSpan.FromSeconds(5)) { throw new TimeoutException("Fixture transition did not occur."); }
            await Task.Yield();
        }
    }
    private readonly ConcurrentQueue<(long Sequence, string Id, string Phase)> events = new();
    private readonly List<TaskCompletionSource> barriers = [];
    private readonly List<Task> pending = [];
    private long sequence;

    public void Record(string id, string phase) => events.Enqueue((Interlocked.Increment(ref sequence), id, phase));
    public (long Sequence, string Id, string Phase)[] Events => events.OrderBy(entry => entry.Sequence).ToArray();
    public TaskCompletionSource Barrier()
    {
        var barrier = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        barriers.Add(barrier);
        return barrier;
    }
    public void Observe(Task task) => pending.Add(task);
    public async ValueTask DisposeAsync()
    {
        foreach (var barrier in barriers) { barrier.TrySetResult(); }
        foreach (var task in pending)
        {
            try { await task.WaitAsync(TimeSpan.FromSeconds(5)); }
            catch (Exception error) when (error is not TimeoutException) { _ = error.GetType(); }
        }
    }
}
