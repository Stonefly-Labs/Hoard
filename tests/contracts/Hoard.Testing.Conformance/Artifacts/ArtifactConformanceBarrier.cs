namespace Hoard.Testing.Conformance.Artifacts;

public class ArtifactConformanceBarrier(string name) : IAsyncDisposable
{
    private readonly TaskCompletionSource entered = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly TaskCompletionSource released = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly TaskCompletionSource settled = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private int active;

    public string Name { get; } = name;
    public Task Entered => entered.Task.WaitAsync(TimeSpan.FromSeconds(10));
    public bool IsActive => Volatile.Read(ref active) != 0;

    public async Task HoldAsync()
    {
        if (Interlocked.Exchange(ref active, 1) != 0) { throw new InvalidOperationException("Barrier already active."); }
        entered.TrySetResult();
        try { await released.Task.WaitAsync(TimeSpan.FromSeconds(20)); }
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
