namespace Hoard.Abstractions.Storage;

public interface IArtifactReadSession : IAsyncDisposable
{
    ArtifactStamp Stamp { get; }
    ValueTask<ArtifactResult<ArtifactReadCompletion>> CopyToAsync(
        Stream destination, ArtifactTransferOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactShutdown>> CloseAsync(
        ArtifactCleanupOptions options, CancellationToken ct);
}
