namespace Hoard.Abstractions.Storage;

public interface IArtifactEvidenceValidator
{
    ValueTask<ArtifactResult<ArtifactStamp>> ValidateAsync(
        ArtifactCommitEvidence evidence, IArtifactProtectionGuard protection,
        ArtifactCallOptions options, CancellationToken ct);
}
