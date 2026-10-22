using Hoard.Abstractions.Metadata;

namespace Hoard.Abstractions.Storage;

public abstract record ArtifactReadMode : ArtifactDiagnostic
{
    private ArtifactReadMode() { }
    public sealed record Full : ArtifactReadMode;
    public sealed record Range : ArtifactReadMode
    {
        public Range(long offset, long count)
        {
            ArtifactValidation.Require(offset >= 0 && count > 0 && offset <= long.MaxValue - count);
            Offset = offset;
            Count = count;
        }
        public long Offset { get; }
        public long Count { get; }
    }
}

public sealed record ArtifactReadRequest : ArtifactDiagnostic
{
    public ArtifactReadRequest(ArtifactDigest digest, ArtifactReadMode? mode = null,
        ArtifactOption<ArtifactStamp>? expectedStamp = null)
    {
        ArgumentNullException.ThrowIfNull(digest);
        Digest = digest;
        Mode = mode ?? new ArtifactReadMode.Full();
        ExpectedStamp = expectedStamp ?? new ArtifactOption<ArtifactStamp>.None();
        ArtifactValidation.Require(ExpectedStamp is not ArtifactOption<ArtifactStamp>.Some stamp
            || stamp.Value.Identity.Digest == digest);
    }
    public ArtifactDigest Digest { get; }
    public ArtifactReadMode Mode { get; }
    public ArtifactOption<ArtifactStamp> ExpectedStamp { get; }
}

public sealed record ArtifactReadCompletion : ArtifactDiagnostic
{
    public ArtifactReadCompletion(ArtifactStamp stamp, ArtifactDigest digest, long length)
    {
        ArgumentNullException.ThrowIfNull(stamp);
        ArgumentNullException.ThrowIfNull(digest);
        ArtifactValidation.Require(stamp.Identity.Digest == digest && stamp.Identity.Length == length);
        Stamp = stamp;
        Digest = digest;
        Length = length;
    }
    public ArtifactStamp Stamp { get; }
    public ArtifactDigest Digest { get; }
    public long Length { get; }
}
