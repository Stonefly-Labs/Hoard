namespace Hoard.Abstractions.Storage;

public interface IArtifactMaintenance
{
    ValueTask<ArtifactResult<ArtifactRecoveryPage>> ObserveAsync(
        ArtifactRecoveryQuery query, ArtifactMaintenanceOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactCleanupReport>> CleanupAsync(
        ArtifactCleanupRequest request, ArtifactMaintenanceOptions options, CancellationToken ct);
}
