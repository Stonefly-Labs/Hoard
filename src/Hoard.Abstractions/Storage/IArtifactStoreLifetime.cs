namespace Hoard.Abstractions.Storage;

public interface IArtifactStoreLifetime
{
    ValueTask<ArtifactResult<ArtifactAdmission>> InitializeAsync(
        ArtifactInitialization request, ArtifactMaintenanceOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<ArtifactShutdown>> StopAsync(
        ArtifactCleanupOptions options, CancellationToken ct);
}
