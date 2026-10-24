namespace Hoard.Testing.Conformance.Metadata;

internal sealed class MetadataConformanceBarrier : IAsyncDisposable
{
    private readonly TaskCompletionSource entered = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly TaskCompletionSource released = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly TaskCompletionSource settled = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private int active;

    public Task WaitForEntryAsync(CancellationToken cancellationToken) =>
        entered.Task.WaitAsync(TimeSpan.FromSeconds(10), cancellationToken);

    public async ValueTask HoldAsync()
    {
        if (Interlocked.Exchange(ref active, 1) != 0) { throw new InvalidOperationException("BarrierAlreadyActive"); }
        entered.TrySetResult();
        try { await released.Task.WaitAsync(TimeSpan.FromSeconds(15)); }
        finally
        {
            Volatile.Write(ref active, 0);
            settled.TrySetResult();
        }
    }

    public void Release() => released.TrySetResult();

    public async ValueTask DisposeAsync()
    {
        Release();
        if (entered.Task.IsCompleted) { await settled.Task.WaitAsync(TimeSpan.FromSeconds(10)); }
    }
}
