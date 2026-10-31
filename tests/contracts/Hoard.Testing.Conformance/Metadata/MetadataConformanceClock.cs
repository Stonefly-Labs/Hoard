using Hoard.Abstractions.Metadata;

namespace Hoard.Testing.Conformance.Metadata;

public sealed class MetadataConformanceClock : TimeProvider
{
    private long milliseconds;

    public MetadataConformanceClock(MetadataInstant initial)
    {
        ArgumentNullException.ThrowIfNull(initial);
        milliseconds = initial.UnixMilliseconds;
    }

    public override DateTimeOffset GetUtcNow() =>
        DateTimeOffset.FromUnixTimeMilliseconds(Interlocked.Read(ref milliseconds));

    public void Set(MetadataInstant value)
    {
        ArgumentNullException.ThrowIfNull(value);
        Interlocked.Exchange(ref milliseconds, value.UnixMilliseconds);
    }
}
