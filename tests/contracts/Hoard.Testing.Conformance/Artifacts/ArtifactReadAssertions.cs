using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactReadAssertions
{
    public static async Task DestinationFailureAsync(
        IArtifactStore store, string failureMessage, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("borrowed streams"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        await using var session = Success(await store.OpenReadAsync(
            new(receipt.Stamp.Identity.Digest), new(), cancellationToken));
        using var destination = new FailingDestination(failureMessage);
        Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
            await session.CopyToAsync(destination, new(), cancellationToken));
        Assert.False(destination.WasDisposed);
        Assert.False(source.WasDisposed);
        Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
            await session.CopyToAsync(Stream.Null, new(), cancellationToken));
    }

    private sealed class FailingDestination(string failureMessage) : MemoryStream
    {
        public bool WasDisposed { get; private set; }
        public override ValueTask WriteAsync(ReadOnlyMemory<byte> buffer, CancellationToken cancellationToken = default) =>
            ValueTask.FromException(new IOException(failureMessage));
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
    }
}
