#if HOARD_ARTIFACT_CONTRIBUTOR
using System.Reflection;
using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Evidence;
using Xunit.Abstractions;
using Xunit.Sdk;
using RecordingDirectories = Hoard.Fixtures.Conformance.Consumer.LocalArtifactSessionTests.RecordingDirectories;

namespace Hoard.Fixtures.Conformance.Consumer;

[AttributeUsage(AttributeTargets.Method, AllowMultiple = true)]
internal sealed class ContributorArtifactDataAttribute(params object[] arguments) : DataAttribute
{
    public override IEnumerable<object[]> GetData(MethodInfo testMethod)
    {
        if (arguments is ["direct-availability"]
            && ContributorBindingFactory.ExpectedEnumeration != ArtifactEnumerationConsistency.Incomplete)
        { yield break; }
        yield return [ContributorBindingFactory.BindingId, .. arguments];
    }
}

public sealed class ContributorArtifactSessionTests(ITestOutputHelper output)
{
    [Theory]
    [ContributorArtifactData("empty")]
    [ContributorArtifactData("unknown-length")]
    [ContributorArtifactData("expectations")]
    [ContributorArtifactData("unsupported")]
    [ContributorArtifactData("duplicates")]
    [ContributorArtifactData("destination-failure")]
    [ContributorArtifactData("exact-retry")]
    [ContributorArtifactData("staged-length")]
    [ContributorArtifactData("recreation")]
    [ContributorArtifactData("reader-exclusion")]
    [ContributorArtifactData("cap-crossing")]
    [ContributorArtifactData("storage-failures")]
    [ContributorArtifactData("live-references")]
    [ContributorArtifactData("private-staging")]
    [ContributorArtifactData("concurrent-writers")]
    [ContributorArtifactData("lost-acknowledgment")]
    [ContributorArtifactData("visible-before-ack")]
    [ContributorArtifactData("receipts")]
    [ContributorArtifactData("recovery-pages")]
    [ContributorArtifactData("changed-inventory")]
    [ContributorArtifactData("expiry-generation")]
    [ContributorArtifactData("ownerless-expiry")]
    [ContributorArtifactData("finalized-noncommit")]
    [ContributorArtifactData("finalized-mutations")]
    [ContributorArtifactData("idle-read")]
    [ContributorArtifactData("cooperative-inactivity")]
    [ContributorArtifactData("noncooperative-source")]
    [ContributorArtifactData("noncooperative-destination")]
    [ContributorArtifactData("authority-deadline")]
    [ContributorArtifactData("cancel-before")]
    [ContributorArtifactData("cancel-waiting")]
    [ContributorArtifactData("cooperative-cancel")]
    [ContributorArtifactData("reclaimed-identities")]
    [ContributorArtifactData("concurrent-release")]
    [ContributorArtifactData("sequential-recovery")]
    [ContributorArtifactData("direct-availability")]
    public async Task Observed_portable_consumers_preserve_actual_guarantees(string provider, string consumer)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories();
        var clock = new ArtifactConformanceSessionTests.ControlledClock();
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component", clock,
            resources, new ConformanceEvidenceBuffer());
        var limits = consumer switch
        {
            "cap-crossing" => new ArtifactLimits(10, 10, 1),
            "ownerless-expiry" => new ArtifactLimits(artifactBytes: 1, stagingBytes: 1),
            "reclaimed-identities" => new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, committedIdentities: 1),
            _ => null
        };
        long liveReferences = consumer == "live-references" ? 1 : 0;
        var referencesAvailable = true;
        var options = new ArtifactAssertionOptions(limits, (_, _) => ValueTask.FromResult(
            new ArtifactReferenceObservation(referencesAvailable, liveReferences, Guid.NewGuid())));
        var session = await ConformanceObservedArtifactSession.OpenAsync(
            ContributorBindingFactory.Create(options), context, default);
        try
        {
            AssertProfile(session);
            Task WhenIdle() => session.Faults.AwaitSettlementAsync(default).AsTask();
            void AdvanceTo(long timestamp) =>
                clock.Advance(DateTimeOffset.FromUnixTimeMilliseconds(timestamp) - clock.GetUtcNow());
            await (consumer switch
            {
                "empty" => ArtifactPublicationAssertions.EmptyContentAndAbsenceAsync(session.Store, default),
                "unknown-length" => ArtifactPublicationAssertions.UnknownLengthAndRealEofAsync(session.Store, default),
                "expectations" => ArtifactPublicationAssertions.EveryExpectationAndEofAsync(session.Store, default),
                "unsupported" => ArtifactPublicationAssertions.UnsupportedChecksumAndRangeAsync(session.Store, default),
                "duplicates" => ArtifactPublicationAssertions.VerifiedDuplicatesAsync(session.Store, default),
                "destination-failure" => ArtifactReadAssertions.DestinationFailureAsync(
                    session.Store, "Synthetic borrowed destination failure", default),
                "exact-retry" => ArtifactReconciliationAssertions.AcknowledgedReceiptRetryAsync(session.Store, default),
                "staged-length" => ArtifactPublicationAssertions.ConflictingStagedLengthAsync(session.Store, default),
                "recreation" => ArtifactDeletionAssertions.ExactReceiptsAndRecreationAsync(
                    session.Store, session.Maintenance, session.Identity, default),
                "reader-exclusion" => ArtifactDeletionAssertions.HeldReaderExcludesDeletionAsync(session.Store, default),
                "cap-crossing" => ArtifactBudgetAssertions.CapCrossingAsync(session.Store, default),
                "storage-failures" => ArtifactFailureAssertions.StorageFailuresAsync(session.Store, default),
                "live-references" => ArtifactDeletionAssertions.LiveReferencesAsync(
                    session.Store, count => liveReferences = count, available => referencesAvailable = available, default),
                "private-staging" or "concurrent-writers" or "lost-acknowledgment" or "visible-before-ack" or "direct-availability" =>
                    ArtifactConformanceSessionTests.BoundaryConsumerAsync(session, consumer),
                "receipts" => ArtifactEvidenceAssertions.ExactCurrentReceiptsAsync(
                    session.Store, session.Validator, session.Authority, session.Identity, default),
                "recovery-pages" => ArtifactRecoveryAssertions.RecoveryPagesAsync(
                    session.Store, session.Maintenance, session.Identity, default),
                "changed-inventory" => ArtifactRecoveryAssertions.ChangedInventoryAsync(
                    session.Store, session.Maintenance, session.Identity, default),
                "expiry-generation" => ArtifactRecoveryAssertions.ExpiryGenerationAsync(
                    session.Store, session.Maintenance, session.Identity, clock.Advance, default),
                "ownerless-expiry" => ArtifactRecoveryAssertions.OwnerlessExpiryAsync(session.Store, clock.Advance, default),
                "finalized-noncommit" => ArtifactRecoveryAssertions.FinalizedNoncommitAsync(
                    session.Store, session.Maintenance, session.Identity, clock.Advance, default),
                "finalized-mutations" => ArtifactReconciliationAssertions.FinalizedMutationExpiryAsync(
                    session.Store, clock.Advance, default),
                "idle-read" => ArtifactOwnershipAssertions.IdleReadExpiryAsync(session.Store, clock.Advance, default),
                "cooperative-inactivity" => ArtifactOwnershipAssertions.CooperativeInactivityAsync(
                    session.Store, WhenIdle, default),
                "noncooperative-source" => ArtifactOwnershipAssertions.NoncooperativeSourceAsync(session.Store, default),
                "noncooperative-destination" => ArtifactOwnershipAssertions.NoncooperativeDestinationAsync(session.Store, default),
                "authority-deadline" => ArtifactBudgetAssertions.AuthorityDeadlineAsync(
                    session.Store, session.Authority, session.Identity, default),
                "cancel-before" or "cancel-waiting" => ArtifactBudgetAssertions.CancelledCommitFencingAsync(
                    session.Store, session.Authority, session.Identity, WhenIdle, consumer == "cancel-before", default),
                "cooperative-cancel" => ArtifactBudgetAssertions.CooperativeCancellationAsync(session.Store, default),
                "reclaimed-identities" => ArtifactHistoryAssertions.ReclaimedIdentityExpiryAsync(
                    session.Store, session.Maintenance, session.Identity, AdvanceTo, default),
                "concurrent-release" => ArtifactBindingAssertions.ConcurrentReleaseAsync(session, default),
                "sequential-recovery" => ArtifactRecoveryAssertions.SequentialRecoveryAsync(
                    session.Store, session.Maintenance, session.Identity, clock.Advance,
                    ContributorBindingFactory.ExpectedEnumeration, default),
                _ => throw new ArgumentException("BindingInvalid")
            });
            AssertProfile(session);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [ContributorArtifactData(ConformanceFault.PublicationBoundary)]
    [ContributorArtifactData(ConformanceFault.DirectVisibility)]
    [ContributorArtifactData(ConformanceFault.PayloadDamage)]
    [ContributorArtifactData(ConformanceFault.Capacity)]
    [ContributorArtifactData(ConformanceFault.NativeNonCooperation)]
    [ContributorArtifactData(ConformanceFault.CleanupFailure)]
    [ContributorArtifactData(ConformanceFault.GenerationBoundary)]
    [ContributorArtifactData(ConformanceFault.ReceiptBoundary)]
    [ContributorArtifactData(ConformanceFault.SourceNonCooperation)]
    [ContributorArtifactData(ConformanceFault.SinkNonCooperation)]
    public async Task Observed_controls_reach_actual_work(string provider, ConformanceFault fault)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories();
        var clock = new ArtifactConformanceSessionTests.ControlledClock();
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component", clock,
            resources, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        if (fault == ConformanceFault.PublicationBoundary)
        {
            await BindingAdmissionAssertions.ArtifactsAsync(binding.Declaration, context);
            Assert.Empty(resources.Settlements);
        }
        var session = await ConformanceObservedArtifactSession.OpenAsync(binding, context, default);
        try
        {
            AssertProfile(session);
            await ArtifactBindingAssertions.ControlsAsync(session, fault, clock.Advance, default);
            AssertProfile(session);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    private static void AssertProfile(IArtifactConformanceSession session)
    {
        var actual = session.Store.Capabilities;
        Assert.Equal(ContributorBindingFactory.ExpectedDurability, actual.Durability);
        Assert.Equal(ContributorBindingFactory.ExpectedEnumeration, actual.Enumeration);
    }
}
#endif
