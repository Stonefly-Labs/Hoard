namespace Hoard.Abstractions.Metadata;

public interface IMetadataPublicationAuthority
{
    ValueTask<MetadataResult<IMetadataPublicationGuard>> AcquireAsync(
        MetadataArtifactEvidence evidence, MetadataCallOptions options, CancellationToken cancellationToken);
}

public interface IMetadataPublicationGuard : IAsyncDisposable
{
    MetadataCommittedArtifact Artifact { get; }
}
