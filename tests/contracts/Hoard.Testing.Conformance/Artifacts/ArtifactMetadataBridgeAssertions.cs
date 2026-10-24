using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Testing.Conformance.Artifacts;

public sealed class ArtifactMetadataBridgeAssertions(
    ArtifactStoreIdentity store, ArtifactCommitEvidence proof, IMetadataPublicationAuthority bridge,
    Func<ArtifactCommitEvidence, MetadataArtifactEvidence> encode)
{
    public async Task ExactEvidenceProtectionAsync(
        IArtifactCoordinationAuthority authority, Func<int> validatorCalls, Func<int> waitingAdmissions,
        CancellationToken cancellationToken)
    {
        var stamp = proof.Stamp;
        var result = await bridge.AcquireAsync(encode(proof), new(), cancellationToken);
        var guard = Assert.IsType<MetadataResult<IMetadataPublicationGuard>.Success>(result).Value;
        Assert.Equal(new MetadataCommittedArtifact(stamp.Identity.Digest, 1), guard.Artifact);
        Assert.Equal(1, validatorCalls());
        var deletion = authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Deletion, store,
            stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), cancellationToken).AsTask();
        Assert.Equal(1, waitingAdmissions());
        Assert.False(deletion.IsCompleted);
        await guard.DisposeAsync();
        await guard.DisposeAsync();
        await using var exclusive = Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Success>(await deletion).Value;
    }

    public async Task RejectInvalidEvidenceAsync(
        Func<int> validatorCalls, Action expireEvidence, Func<bool> hasRetainedWork, CancellationToken cancellationToken)
    {
        var stamp = proof.Stamp;
        Assert.IsType<MetadataResult<IMetadataPublicationGuard>.Failure>(
            await bridge.AcquireAsync(new MetadataArtifactEvidence("not-base64"), new(), cancellationToken));
        Assert.Equal(0, validatorCalls());
        var foreign = new ArtifactCommitEvidence(new ArtifactStamp(
            new ArtifactStoreIdentity(store.ProviderModuleId, store.InstanceId, Guid.NewGuid()), stamp.Identity, stamp.Incarnation),
            proof.TicketId, proof.ReceiptId, proof.ProofHandle, proof.Outcome);
        Assert.Throws<ArgumentException>(() => encode(foreign));
        var unknown = new ArtifactCommitEvidence(stamp, Guid.NewGuid(), proof.ReceiptId, "different", proof.Outcome);
        Assert.IsType<MetadataResult<IMetadataPublicationGuard>.Failure>(
            await bridge.AcquireAsync(encode(unknown), new(), cancellationToken));
        expireEvidence();
        Assert.IsType<MetadataResult<IMetadataPublicationGuard>.Failure>(
            await bridge.AcquireAsync(encode(proof), new(), cancellationToken));
        Assert.False(hasRetainedWork());
    }

    public async Task RejectMismatchedAuthorityAsync(CancellationToken cancellationToken)
    {
        Assert.IsType<MetadataResult<IMetadataPublicationGuard>.Failure>(
            await bridge.AcquireAsync(encode(proof), new(), cancellationToken));
    }

    public static void ReferenceProtection(IArtifactProtectionGuard guard, ArtifactCommitEvidence evidence)
    {
        Assert.Equal(ArtifactProtectionOperation.Reference, guard.Grant.Request.Operation);
        Assert.Equal(new ArtifactOption<ArtifactStamp>.Some(evidence.Stamp), guard.Grant.Request.Stamp);
    }
}
