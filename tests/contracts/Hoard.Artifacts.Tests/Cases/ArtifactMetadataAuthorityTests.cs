using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactMetadataAuthorityTests
{
    [Fact]
    public async Task Bridge_binds_exact_evidence_and_keeps_recognized_shared_protection_until_metadata_settlement()
    {
        var store = new ArtifactStoreIdentity("fixture.artifact", Guid.NewGuid(), Guid.NewGuid());
        var stamp = new ArtifactStamp(store, new ArtifactIdentity(new ArtifactDigest(new string('a', 64)), 1), Guid.NewGuid());
        var proof = new ArtifactCommitEvidence(stamp, Guid.NewGuid(), Guid.NewGuid(), "opaque", ArtifactPublicationOutcome.Published);
        var authority = new ArtifactCoordinationAuthority(store, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        var validator = new CurrentValidator(authority, proof);
        var bridge = new ArtifactMetadataPublicationAuthority(store, validator, authority);
        var result = await bridge.AcquireAsync(bridge.Encode(proof), new(), default);
        var guard = Assert.IsType<MetadataResult<IMetadataPublicationGuard>.Success>(result).Value;
        Assert.Equal(new MetadataCommittedArtifact(stamp.Identity.Digest, 1), guard.Artifact);
        Assert.Equal(1, validator.Calls);
        var deletion = authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Deletion, store,
            stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), default).AsTask();
        Assert.Equal(1, authority.WaitingAdmissions);
        Assert.False(deletion.IsCompleted);
        await guard.DisposeAsync();
        await guard.DisposeAsync();
        await using var exclusive = Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Success>(await deletion).Value;
    }

    [Fact]
    public async Task Foreign_malformed_expired_and_unrecognized_evidence_cannot_publish_metadata_or_leak_a_guard()
    {
        var store = new ArtifactStoreIdentity("fixture.artifact", Guid.NewGuid(), Guid.NewGuid());
        var stamp = new ArtifactStamp(store, new ArtifactIdentity(new ArtifactDigest(new string('a', 64)), 0), Guid.NewGuid());
        var proof = new ArtifactCommitEvidence(stamp, Guid.NewGuid(), Guid.NewGuid(), "opaque", ArtifactPublicationOutcome.Published);
        var authority = new ArtifactCoordinationAuthority(store);
        var validator = new CurrentValidator(authority, proof);
        var bridge = new ArtifactMetadataPublicationAuthority(store, validator, authority);
        Assert.IsType<MetadataResult<IMetadataPublicationGuard>.Failure>(
            await bridge.AcquireAsync(new MetadataArtifactEvidence("not-base64"), new(), default));
        Assert.Equal(0, validator.Calls);
        var foreign = new ArtifactCommitEvidence(new ArtifactStamp(
            new ArtifactStoreIdentity(store.ProviderModuleId, store.InstanceId, Guid.NewGuid()), stamp.Identity, stamp.Incarnation),
            proof.TicketId, proof.ReceiptId, proof.ProofHandle, proof.Outcome);
        Assert.Throws<ArgumentException>(() => bridge.Encode(foreign));
        var unknown = new ArtifactCommitEvidence(stamp, Guid.NewGuid(), proof.ReceiptId, "different", proof.Outcome);
        Assert.IsType<MetadataResult<IMetadataPublicationGuard>.Failure>(
            await bridge.AcquireAsync(bridge.Encode(unknown), new(), default));
        validator.Expired = true;
        Assert.IsType<MetadataResult<IMetadataPublicationGuard>.Failure>(
            await bridge.AcquireAsync(bridge.Encode(proof), new(), default));
        Assert.False(authority.HasRetainedWork);
    }

    [Fact]
    public async Task Mismatched_authority_composition_cannot_substitute_field_equivalent_protection()
    {
        var store = new ArtifactStoreIdentity("fixture.artifact", Guid.NewGuid(), Guid.NewGuid());
        var stamp = new ArtifactStamp(store, new ArtifactIdentity(new ArtifactDigest(new string('a', 64)), 0), Guid.NewGuid());
        var proof = new ArtifactCommitEvidence(stamp, Guid.NewGuid(), Guid.NewGuid(), "opaque", ArtifactPublicationOutcome.Published);
        var actual = new ArtifactCoordinationAuthority(store);
        var other = new ArtifactCoordinationAuthority(store);
        var bridge = new ArtifactMetadataPublicationAuthority(store, new CurrentValidator(actual, proof), other);
        Assert.IsType<MetadataResult<IMetadataPublicationGuard>.Failure>(
            await bridge.AcquireAsync(bridge.Encode(proof), new(), default));
    }

    private sealed class CurrentValidator(IArtifactCoordinationAuthority authority, ArtifactCommitEvidence current)
        : IArtifactEvidenceValidator
    {
        public int Calls { get; private set; }
        public bool Expired { get; set; }
        public async ValueTask<ArtifactResult<ArtifactStamp>> ValidateAsync(ArtifactCommitEvidence evidence,
            IArtifactProtectionGuard protection, ArtifactCallOptions options, CancellationToken ct)
        {
            Calls++;
            var retained = await authority.RetainAsync(protection, protection.Grant.Request, options, ct);
            if (retained is not ArtifactResult<IArtifactProtectionGuard>.Success recognized)
            {
                return new ArtifactResult<ArtifactStamp>.Failure(
                    ArtifactFailureCode.Denied, ArtifactPhase.Publication, ArtifactAction.Reobserve, Guid.NewGuid());
            }
            await using var guard = recognized.Value;
            Assert.Equal(ArtifactProtectionOperation.Reference, guard.Grant.Request.Operation);
            Assert.Equal(new ArtifactOption<ArtifactStamp>.Some(evidence.Stamp), guard.Grant.Request.Stamp);
            return !Expired && evidence == current
                ? new ArtifactResult<ArtifactStamp>.Success(current.Stamp)
                : new ArtifactResult<ArtifactStamp>.Failure(ArtifactFailureCode.ReconciliationExpired,
                    ArtifactPhase.Publication, ArtifactAction.OperatorRecovery, Guid.NewGuid());
        }
    }
}
