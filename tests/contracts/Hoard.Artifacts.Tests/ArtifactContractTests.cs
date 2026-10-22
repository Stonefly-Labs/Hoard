using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Providers;
using Hoard.Abstractions.Storage;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactContractTests
{
    private static ArtifactStoreIdentity Store() => new("fixture.artifact", Guid.NewGuid(), Guid.NewGuid());
    private static readonly ArtifactDigest Digest = new(new string('a', 64));
    private static ArtifactStamp Stamp() => new(Store(), new ArtifactIdentity(Digest, 1), Guid.NewGuid());
    private static ArtifactOperationTicket Ticket(ArtifactStoreIdentity store, ArtifactOperationKind kind)
        => new(store, Guid.NewGuid(), kind, DateTimeOffset.UnixEpoch, DateTimeOffset.UnixEpoch.AddHours(24), new string('a', 64));

    [Fact]
    public void Marker_and_historical_digest_remain_separate_from_operational_contracts()
    {
        Assert.Empty(typeof(IArtifactProvider).GetMethods());
        Assert.Equal([typeof(IHoardProvider)], typeof(IArtifactProvider).GetInterfaces());
        Assert.Equal("Hoard.Abstractions.Metadata", typeof(ArtifactDigest).Namespace);
        Assert.False(typeof(IArtifactStore).IsAssignableFrom(typeof(IArtifactProvider)));
        Assert.Equal(9, typeof(IArtifactStore).GetMethods().Count(method => !method.IsSpecialName));
        Assert.Equal(2, typeof(IArtifactCoordinationAuthority).GetMethods().Length);
        Assert.Empty(typeof(IArtifactStore).GetInterfaces());
        Assert.Empty(typeof(IArtifactMaintenance).GetInterfaces());
    }

    [Fact]
    public void Ranges_and_completion_reject_overflow_mismatched_digest_or_length()
    {
        Assert.Equal(long.MaxValue - 1, new ArtifactReadMode.Range(long.MaxValue - 1, 1).Offset);
        foreach (var (offset, count) in new[] { (-1L, 1L), (0L, 0L), (long.MaxValue, 1L), (1L, long.MaxValue) })
        { Assert.Throws<ArgumentException>(() => new ArtifactReadMode.Range(offset, count)); }
        var stamp = Stamp();
        Assert.NotNull(new ArtifactReadCompletion(stamp, Digest, 1));
        Assert.Throws<ArgumentException>(() => new ArtifactReadCompletion(stamp, Digest, 0));
        var different = new ArtifactDigest(new string('b', 64));
        Assert.Throws<ArgumentException>(() => new ArtifactReadRequest(different,
            expectedStamp: new ArtifactOption<ArtifactStamp>.Some(stamp)));
    }

    [Fact]
    public void Protection_requires_exact_matching_scope_and_positive_grant_identity()
    {
        var stamp = Stamp();
        var id = Guid.NewGuid();
        var request = new ArtifactProtectionRequest(id, ArtifactProtectionOperation.Read, stamp.Store, Digest);
        Assert.Equal(ArtifactProtectionMode.Shared, request.Mode);
        foreach (var operation in new[] { ArtifactProtectionOperation.Reference, ArtifactProtectionOperation.Deletion })
        {
            Assert.Throws<ArgumentException>(() => new ArtifactProtectionRequest(id, operation, stamp.Store, Digest));
            Assert.NotNull(new ArtifactProtectionRequest(id, operation, stamp.Store, Digest, new ArtifactOption<ArtifactStamp>.Some(stamp)));
        }
        Assert.Throws<ArgumentException>(() => new ArtifactProtectionRequest(id, ArtifactProtectionOperation.Read,
            Store(), Digest, new ArtifactOption<ArtifactStamp>.Some(stamp)));
        Assert.Throws<ArgumentException>(() => new ArtifactProtectionRequest(Guid.Empty, ArtifactProtectionOperation.Read, stamp.Store, Digest));
        Assert.Throws<ArgumentException>(() => new ArtifactProtectionGrant(id, request, 0, DateTimeOffset.UnixEpoch.AddMinutes(1)));
        Assert.Throws<ArgumentException>(() => new ArtifactProtectionGrant(Guid.Empty, request, 1, DateTimeOffset.UnixEpoch.AddMinutes(1)));
        Assert.NotNull(new ArtifactProtectionGrant(id, request, 1, DateTimeOffset.UnixEpoch.AddMinutes(1)));
    }

    [Fact]
    public void Receipts_cannot_mix_stores_kinds_visibility_evidence_or_resolution()
    {
        var stamp = Stamp();
        var ticket = Ticket(stamp.Store, ArtifactOperationKind.Write);
        var receiptId = Guid.NewGuid();
        var proof = new ArtifactCommitEvidence(stamp, ticket.Id, receiptId, "opaque", ArtifactPublicationOutcome.Published);
        var receipt = new ArtifactMutationReceipt(ticket, receiptId, ArtifactMutationOutcome.Published, stamp,
            ArtifactVisibility.Committed, ArtifactReclamation.NotApplicable, new ArtifactOption<ArtifactCommitEvidence>.Some(proof));
        Assert.Equal(receipt, new ArtifactResolution.Committed(receipt).Receipt);
        Assert.Throws<ArgumentException>(() => new ArtifactResolution.Removed(receipt));
        Assert.Throws<ArgumentException>(() => new ArtifactMutationReceipt(ticket, receiptId, ArtifactMutationOutcome.Published,
            stamp, ArtifactVisibility.Committed, ArtifactReclamation.NotApplicable));
        var delete = Ticket(stamp.Store, ArtifactOperationKind.Delete);
        var removed = new ArtifactMutationReceipt(delete, receiptId, ArtifactMutationOutcome.Removed, stamp,
            ArtifactVisibility.Removed, ArtifactReclamation.Pending);
        Assert.NotNull(new ArtifactResolution.Removed(removed));
        Assert.Throws<ArgumentException>(() => new ArtifactResolution.Committed(removed));
        Assert.Throws<ArgumentException>(() => new ArtifactResolution.AlreadyAbsent(removed));
        Assert.Throws<ArgumentException>(() => new ArtifactMutationReceipt(delete, receiptId, ArtifactMutationOutcome.Removed,
            Stamp(), ArtifactVisibility.Removed, ArtifactReclamation.Pending));
        Assert.Throws<ArgumentException>(() => new ArtifactMutationReceipt(ticket, receiptId, ArtifactMutationOutcome.Removed,
            stamp, ArtifactVisibility.Removed, ArtifactReclamation.Pending));
    }

    [Fact]
    public void Recovery_and_cleanup_are_bounded_immutable_exact_targets_not_absence_authority()
    {
        var stamp = Stamp();
        Assert.NotNull(new ArtifactRecoveryQuery(stamp.Store, ArtifactRecoveryKind.All, 100));
        foreach (var size in new[] { 0, 101 })
        { Assert.Throws<ArgumentException>(() => new ArtifactRecoveryQuery(stamp.Store, ArtifactRecoveryKind.All, size)); }
        Assert.Throws<ArgumentException>(() => new ArtifactRecoveryQuery(stamp.Store, ArtifactRecoveryKind.All,
            continuation: new ArtifactOption<string>.Some(new string('x', 4097))));
        var observation = new ArtifactRecoveryObservation(ArtifactObservationKind.Committed, Guid.NewGuid(),
            new ArtifactOption<ArtifactStamp>.Some(stamp));
        var inputs = new List<ArtifactRecoveryObservation> { observation };
        var page = new ArtifactRecoveryPage(inputs, ArtifactEnumerationConsistency.Incomplete);
        inputs.Clear();
        Assert.Single(page.Observations);
        Assert.Throws<ArgumentException>(() => new ArtifactRecoveryPage(Enumerable.Repeat(observation, 101), ArtifactEnumerationConsistency.Snapshot));
        Assert.Throws<ArgumentException>(() => new ArtifactRecoveryPage(default(ImmutableArray<ArtifactRecoveryObservation>), ArtifactEnumerationConsistency.Snapshot));
        Assert.Throws<ArgumentException>(() => new ArtifactRecoveryObservation(ArtifactObservationKind.Committed, Guid.NewGuid()));
        Assert.Throws<ArgumentException>(() => new ArtifactRecoveryObservation(ArtifactObservationKind.ActiveStaging, Guid.NewGuid()));
        ArtifactCleanupTarget target = new ArtifactCleanupTarget.RemovedIncarnation(stamp);
        Assert.NotNull(new ArtifactCleanupRequest(stamp.Store, [target]));
        Assert.Throws<ArgumentException>(() => new ArtifactCleanupRequest(Store(), [target]));
        Assert.Throws<ArgumentException>(() => new ArtifactCleanupRequest(stamp.Store, []));
        Assert.Throws<ArgumentException>(() => new ArtifactCleanupRequest(stamp.Store, Enumerable.Repeat(target, 101)));
        Assert.NotNull(new ArtifactCleanupReport(100, 0, 0, 0));
        Assert.Throws<ArgumentException>(() => new ArtifactCleanupReport(100, 1, 0, 0));
        Assert.Throws<ArgumentException>(() => new ArtifactCleanupReport(0, 0, 0, -1));
    }

    [Fact]
    public void Failures_shutdown_and_qualification_cannot_be_success_shaped()
    {
        var id = Guid.NewGuid();
        Assert.Throws<ArgumentNullException>(() => new ArtifactResult<ArtifactIdentity>.Success(null!));
        Assert.Throws<ArgumentException>(() => new ArtifactResult<ArtifactIdentity>.Failure(
            (ArtifactFailureCode)99, ArtifactPhase.Read, ArtifactAction.None, id));
        Assert.Throws<ArgumentException>(() => new ArtifactResult<ArtifactIdentity>.Failure(
            ArtifactFailureCode.Uncertain, ArtifactPhase.Publication, ArtifactAction.ReconcileExactTicket, id));
        Assert.Throws<ArgumentException>(() => new ArtifactResult<ArtifactIdentity>.Failure(
            ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, ArtifactAction.OperatorRecovery, id));
        Assert.NotNull(new ArtifactShutdown(ArtifactCleanupState.RetainedLiveOwnership, 1, 1, false));
        Assert.Throws<ArgumentException>(() => new ArtifactShutdown(ArtifactCleanupState.Released, 1, 0, false));
        Assert.Throws<ArgumentException>(() => new ArtifactShutdown(ArtifactCleanupState.Released, 0, 0, true));
        var capabilities = new ArtifactCapabilities(1, ArtifactDurability.SimulationOnly, ArtifactEnumerationConsistency.Incomplete, new ArtifactLimits());
        Assert.True(capabilities.MeetsBaseline);
        Assert.False(new ArtifactCapabilities(2, ArtifactDurability.SimulationOnly, ArtifactEnumerationConsistency.Incomplete, new ArtifactLimits()).MeetsBaseline);
        var cases = Enumerable.Range(1, 48).Select(number => $"AS-{number:D2}").ToArray();
        var hash = new string('a', 64);
        Assert.NotNull(new ArtifactQualificationRecord("fixture.artifact", "0.1.0", hash, hash, hash, hash, hash,
            capabilities, cases, [hash], ["AS-41", "AS-42", "AS-43", "AS-44"]));
        Assert.Throws<ArgumentException>(() => new ArtifactQualificationRecord("fixture.artifact", "0.1.0", hash, hash, hash, hash, hash,
            capabilities, cases.Take(47), [hash], []));
    }
}
