namespace Hoard.Artifacts.Tests;

internal static class ArtifactTestData
{
    public const string Canary = "synthetic-artifact-secret-canary";
    public const string OpaqueCanary = "synthetic-artifact-private-proof";
    public static void AssertSanitized(string diagnostic)
    {
        Assert.DoesNotContain(Canary, diagnostic);
        Assert.DoesNotContain(OpaqueCanary, diagnostic);
    }
}

internal sealed class ArtifactTestClock : TimeProvider
{
    private long milliseconds = 1_800_000_000_000;
    private long timestamp;

    public override DateTimeOffset GetUtcNow() => DateTimeOffset.FromUnixTimeMilliseconds(Interlocked.Read(ref milliseconds));
    public override long TimestampFrequency => 1000;
    public override long GetTimestamp() => Interlocked.Read(ref timestamp);
    public void SetUtc(long value) => Interlocked.Exchange(ref milliseconds, value);
    public void Advance(TimeSpan value)
    {
        var delta = checked((long)value.TotalMilliseconds);
        ArgumentOutOfRangeException.ThrowIfNegative(delta);
        Interlocked.Add(ref milliseconds, delta);
        Interlocked.Add(ref timestamp, delta);
    }
}

internal sealed class ArtifactTestBarrier(string name) : IAsyncDisposable
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

internal interface IArtifactProviderDriver : IAsyncDisposable
{
    string ProviderId { get; }
}
