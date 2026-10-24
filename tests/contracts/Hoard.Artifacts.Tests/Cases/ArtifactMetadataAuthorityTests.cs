using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Testing.Conformance.Artifacts;

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
        await new ArtifactMetadataBridgeAssertions(store, proof, bridge, bridge.Encode)
            .ExactEvidenceProtectionAsync(authority, () => validator.Calls, () => authority.WaitingAdmissions, default);
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
        await new ArtifactMetadataBridgeAssertions(store, proof, bridge, bridge.Encode)
            .RejectInvalidEvidenceAsync(() => validator.Calls, () => validator.Expired = true,
                () => authority.HasRetainedWork, default);
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
        await new ArtifactMetadataBridgeAssertions(store, proof, bridge, bridge.Encode)
            .RejectMismatchedAuthorityAsync(default);
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
            ArtifactMetadataBridgeAssertions.ReferenceProtection(guard, evidence);
            return !Expired && evidence == current
                ? new ArtifactResult<ArtifactStamp>.Success(current.Stamp)
                : new ArtifactResult<ArtifactStamp>.Failure(ArtifactFailureCode.ReconciliationExpired,
                    ArtifactPhase.Publication, ArtifactAction.OperatorRecovery, Guid.NewGuid());
        }
    }
}
