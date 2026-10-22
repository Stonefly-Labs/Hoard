using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

public sealed partial class ObjectArtifactStore : IArtifactStore, IArtifactEvidenceValidator, IArtifactMaintenance
{
    private ArtifactResult<T> Unimplemented<T>() where T : notnull
        => new ArtifactResult<T>.Failure(initialized ? ArtifactFailureCode.Unsupported : ArtifactFailureCode.Disposed,
            ArtifactPhase.Admission, ArtifactAction.OperatorRecovery, Guid.NewGuid());
    public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(ArtifactWriteIntent intent, ArtifactCallOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<ArtifactOperationTicket>());
    public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveDeleteAsync(ArtifactDeleteIntent intent, ArtifactCallOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<ArtifactOperationTicket>());
    public ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<ArtifactStagedWrite>());
    public ValueTask<ArtifactResult<ArtifactStagingOwner>> RenewAsync(ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<ArtifactStagingOwner>());
    public ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<ArtifactMutationReceipt>());
    public ValueTask<ArtifactResult<IArtifactReadSession>> OpenReadAsync(ArtifactReadRequest request, ArtifactCallOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<IArtifactReadSession>());
    public ValueTask<ArtifactResult<ArtifactMutationReceipt>> DeleteAsync(ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<ArtifactMutationReceipt>());
    public ValueTask<ArtifactResult<ArtifactResolution>> ReconcileAsync(ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<ArtifactResolution>());
    public ValueTask<ArtifactResult<ArtifactCleanupReport>> AbandonAsync(ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<ArtifactCleanupReport>());
    public ValueTask<ArtifactResult<ArtifactStamp>> ValidateAsync(ArtifactCommitEvidence evidence, IArtifactProtectionGuard protection, ArtifactCallOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<ArtifactStamp>());
    public ValueTask<ArtifactResult<ArtifactRecoveryPage>> ObserveAsync(ArtifactRecoveryQuery query, ArtifactMaintenanceOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<ArtifactRecoveryPage>());
    public ValueTask<ArtifactResult<ArtifactCleanupReport>> CleanupAsync(ArtifactCleanupRequest request, ArtifactMaintenanceOptions options, CancellationToken ct)
        => ValueTask.FromResult(Unimplemented<ArtifactCleanupReport>());
}
