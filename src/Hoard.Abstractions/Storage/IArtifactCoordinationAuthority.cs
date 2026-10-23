namespace Hoard.Abstractions.Storage;

public interface IArtifactCoordinationAuthority
{
    ValueTask<ArtifactResult<IArtifactProtectionGuard>> AcquireAsync(
        ArtifactProtectionRequest request, ArtifactCallOptions options, CancellationToken ct);
    ValueTask<ArtifactResult<IArtifactProtectionGuard>> RetainAsync(
        IArtifactProtectionGuard protection, ArtifactProtectionRequest expected,
        ArtifactCallOptions options, CancellationToken ct);
}

public interface IArtifactProtectionGuard : IAsyncDisposable
{
    ArtifactProtectionGrant Grant { get; }
}
