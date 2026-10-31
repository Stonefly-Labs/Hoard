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

internal interface IArtifactProviderDriver : IAsyncDisposable
{
    string ProviderId { get; }
}
