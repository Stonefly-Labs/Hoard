namespace Hoard.Abstractions.Storage;

public interface IArtifactStore
{
    ArtifactCapabilities Capabilities { get; }
    ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(
        ArtifactWriteIntent intent, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveDeleteAsync(
        ArtifactDeleteIntent intent, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
        ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactStagingOwner>> RenewAsync(
        ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(
        ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<IArtifactReadSession>> OpenReadAsync(
        ArtifactReadRequest request, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactMutationReceipt>> DeleteAsync(
        ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactResolution>> ReconcileAsync(
        ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactCleanupReport>> AbandonAsync(
        ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct);
}
