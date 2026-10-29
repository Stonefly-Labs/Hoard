using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Testing.Conformance.Artifacts;

public sealed record ArtifactTransferReadback(
    long Written, long Read, string SourceSha256, string SinkSha256, bool SourcePaced, bool SinkPaced);

public static class ArtifactTransferAssertions
{
    public static async Task WarmAsync(IArtifactStore store, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(store);
        using var source = new GeneratedArtifactSource(8388608);
        var ticket = Require(await store.ReserveWriteAsync(new(new ArtifactExpectations(8388608)), new(), cancellationToken));
        var staged = Require(await store.StageAsync(ticket, source, new(), cancellationToken));
        var receipt = Require(await store.CommitAsync(staged, new(), cancellationToken));
        await using var read = Require(await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken));
        using var sink = new ArtifactHashingSink();
        Require(await read.CopyToAsync(sink, new(), cancellationToken));
    }

    public static async Task<ArtifactTransferReadback> TransferAsync(
        IArtifactStore store, long size, string expectedSha256, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(store);
        if (size is not (268435456L or 4294967296L) || expectedSha256 is not { Length: 64 }
            || expectedSha256.Any(character => !char.IsAsciiHexDigitLower(character)))
        { throw new ArgumentException("EvidenceSchemaInvalid"); }
        var digest = new ArtifactDigest(expectedSha256);
        using var source = new GeneratedArtifactSource(size);
        var ticket = Require(await store.ReserveWriteAsync(new(new ArtifactExpectations(size,
            new ArtifactOption<ArtifactDigest>.Some(digest), new ArtifactOption<long>.Some(size))), new(), cancellationToken));
        var staged = Require(await store.StageAsync(ticket, source, new(), cancellationToken));
        var receipt = Require(await store.CommitAsync(staged, new(), cancellationToken));
        using var sink = new ArtifactHashingSink();
        await using (var read = Require(await store.OpenReadAsync(new(digest,
            expectedStamp: new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), cancellationToken)))
        {
            Require(await read.CopyToAsync(sink, new(), cancellationToken));
        }
        if (source.BytesRead != size || sink.BytesWritten != size || source.Digest != expectedSha256
            || sink.Digest != expectedSha256 || !source.Paced || !sink.Paced || staged.Identity.Length != size)
        { throw new InvalidOperationException("Artifact transfer did not verify actual paced byte counts."); }
        return new(source.BytesRead, sink.BytesWritten, source.Digest, sink.Digest, source.Paced, sink.Paced);
    }

    private static T Require<T>(ArtifactResult<T> result) where T : notnull
        => result is ArtifactResult<T>.Success success ? success.Value
            : throw new InvalidOperationException(result is ArtifactResult<T>.Failure failed
                ? $"Artifact transfer failed ({failed.Code})." : "Unknown artifact transfer result.");
}
