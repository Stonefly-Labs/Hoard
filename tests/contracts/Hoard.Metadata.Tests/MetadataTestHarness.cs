namespace Hoard.Metadata.Tests;

internal static class MetadataTestData
{
    public const string Canary = "synthetic-metadata-secret-canary";
    public static Guid Id(int value) => new(value, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1);
    public static string Name(int value) => $"synthetic-package-{value:D4}";
    public static void AssertSanitized(string diagnostic) => Assert.DoesNotContain(Canary, diagnostic);
}

internal sealed class MetadataTestClock : TimeProvider
{
    private long milliseconds = 1_800_000_000_000;
    public override DateTimeOffset GetUtcNow() => DateTimeOffset.FromUnixTimeMilliseconds(Interlocked.Read(ref milliseconds));
    public void Set(long value) => Interlocked.Exchange(ref milliseconds, value);
    public void Advance(TimeSpan value) => Interlocked.Add(ref milliseconds, checked((long)value.TotalMilliseconds));
}

internal sealed class MetadataTestBarrier : IAsyncDisposable
{
    private readonly TaskCompletionSource entered = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly TaskCompletionSource released = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly TaskCompletionSource settled = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private int active;

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
