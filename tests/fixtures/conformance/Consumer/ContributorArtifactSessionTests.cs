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
    [ContributorArtifactData("released-cancellation")]
    [ContributorArtifactData("successful-ticket")]
    [ContributorArtifactData("successful-read")]
    [ContributorArtifactData("unclaimed-ticket")]
    [ContributorArtifactData("unclaimed-read")]
    [ContributorArtifactData("expired-staging")]
    [ContributorArtifactData("progress-cancellation")]
    [ContributorArtifactData("rollback-history")]
    [ContributorArtifactData("rollback-write-capacity")]
    [ContributorArtifactData("rollback-delete-capacity")]
    [ContributorArtifactData("descriptor-completion")]
    [ContributorArtifactData("descriptor-handle")]
    [ContributorArtifactData("descriptor-renewed")]
    [ContributorArtifactData("candidate-tickets")]
    [ContributorArtifactData("candidate-dependencies")]
    [ContributorArtifactData("candidate-decisions")]
    [ContributorArtifactData("candidate-resume")]
    [ContributorArtifactData("receipt")]
    [ContributorArtifactData("read-open")]
    [ContributorArtifactData("verified-reconciliation")]
    [ContributorArtifactData("pending-reclamation")]
    [ContributorArtifactData("delete-history")]
    [ContributorArtifactData("transfer-queue")]
    [ContributorArtifactData("released-shutdown")]
    [ContributorArtifactData("committed-residual")]
    public async Task Observed_portable_consumers_preserve_actual_guarantees(string provider, string consumer)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories();
        var clock = new ArtifactConformanceSessionTests.ControlledClock();
        var started = clock.GetTimestamp();
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component", clock,
            resources, new ConformanceEvidenceBuffer());
        var limits = consumer switch
        {
            "cap-crossing" => new ArtifactLimits(10, 10, 1),
            "ownerless-expiry" => new ArtifactLimits(artifactBytes: 1, stagingBytes: 1),
            "reclaimed-identities" => new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, committedIdentities: 1),
            "successful-ticket" or "successful-read" =>
                new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024, transferSlots: 1, waitingCalls: 0),
            "unclaimed-ticket" or "unclaimed-read" =>
                new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024, transferSlots: 1, waitingCalls: 0, liveTickets: 2),
            "expired-staging" => new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024),
            "rollback-write-capacity" or "rollback-delete-capacity" =>
                new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, liveTickets: 4),
            "candidate-tickets" or "candidate-dependencies" or "candidate-decisions" =>
                new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1048576, committedIdentities: 128),
            "read-open" => new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, transferSlots: 1, waitingCalls: 0),
            "delete-history" => new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, committedIdentities: 1),
            "transfer-queue" => new ArtifactLimits(artifactBytes: 1, stagingBytes: 3, transferSlots: 1, waitingCalls: 1),
            "committed-residual" => new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024),
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
                "released-cancellation" or "successful-ticket" or "successful-read" or "unclaimed-ticket"
                    or "unclaimed-read" or "expired-staging" or "progress-cancellation" =>
                    ArtifactConformanceSessionTests.HandoffConsumerAsync(session, clock, consumer),
                "rollback-history" or "rollback-write-capacity" or "rollback-delete-capacity" =>
                    ArtifactConformanceSessionTests.ClockRollbackConsumerAsync(session, clock, consumer["rollback-".Length..]),
                "descriptor-completion" or "descriptor-handle" or "descriptor-renewed" =>
                    ArtifactOwnershipAssertions.CancelledStagedDescriptorAsync(
                        session.Store, clock.Advance, WhenIdle, consumer["descriptor-".Length..], default),
                "candidate-tickets" or "candidate-dependencies" or "candidate-decisions" =>
                    ArtifactConformanceSessionTests.CandidateBoundsConsumerAsync(session, consumer["candidate-".Length..]),
                "candidate-resume" => ArtifactConformanceSessionTests.CandidateResumeConsumerAsync(session),
                "receipt" or "read-open" or "verified-reconciliation" or "pending-reclamation" =>
                    ArtifactConformanceSessionTests.ReceiptOwnershipConsumerAsync(session, consumer),
                "delete-history" or "transfer-queue" or "released-shutdown" =>
                    ArtifactConformanceSessionTests.AdmittedOwnershipConsumerAsync(session, clock, consumer),
                "committed-residual" => ArtifactConformanceSessionTests.ResidualCleanupConsumerAsync(session),
                _ => throw new ArgumentException("BindingInvalid")
            });
            if (consumer is "rollback-history" or "rollback-write-capacity" or "rollback-delete-capacity")
            { Assert.True(clock.GetTimestamp() > started); }
            AssertProfile(session);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [ContributorArtifactData("read-bitflip")]
    [ContributorArtifactData("read-truncate")]
    [ContributorArtifactData("commit-progress")]
    [ContributorArtifactData("exact-payload")]
    public async Task Observed_payload_controls_preserve_actual_quarantine_and_declared_state(string provider, string consumer)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories();
        var clock = new ArtifactConformanceSessionTests.ControlledClock();
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component",
            clock, resources, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        await ArtifactConformanceSessionTests.PayloadConsumerAsync(binding, context, resources, output, clock, consumer,
            ContributorBindingFactory.ExpectedDurability == ArtifactDurability.LocalProcessCrash, AssertProfile);
    }

    [Theory]
    [ContributorArtifactData("open")]
    [ContributorArtifactData("publication")]
    [ContributorArtifactData("reconciliation")]
    public async Task Observed_payload_detection_preserves_actual_quarantine_and_declared_state(string provider, string detection)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component",
            TimeProvider.System, resources, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        await ArtifactConformanceSessionTests.DetectionQuarantineConsumerAsync(binding, context, resources, output,
            detection, ContributorBindingFactory.ExpectedDurability, AssertProfile);
    }

    [Theory]
    [ContributorArtifactData(false)]
    [ContributorArtifactData(true)]
    public async Task Observed_quarantine_validation_preserves_actual_restoration_and_declared_state(string provider, bool missing)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component",
            TimeProvider.System, resources, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        await ArtifactConformanceSessionTests.ValidationQuarantineConsumerAsync(binding, context, resources, output,
            missing, ContributorBindingFactory.ExpectedDurability == ArtifactDurability.LocalProcessCrash, AssertProfile);
    }

    [Theory]
    [ContributorArtifactData(false)]
    [ContributorArtifactData(true)]
    public async Task Observed_payload_prefix_cleanup_preserves_actual_ownership_and_declared_state(string provider, bool stop)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component",
            TimeProvider.System, resources, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(
            limits: new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024), references: (_, _) =>
                ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        await ArtifactConformanceSessionTests.PrefixCleanupConsumerAsync(binding, context, resources, output, stop,
            ContributorBindingFactory.ExpectedDurability == ArtifactDurability.LocalProcessCrash, AssertProfile);
    }

    [Theory]
    [ContributorArtifactData("scope", false)]
    [ContributorArtifactData("scope", true)]
    [ContributorArtifactData("validation", false)]
    [ContributorArtifactData("validation", true)]
    public async Task Observed_payload_access_preserves_actual_ownership_and_intact_content(
        string provider, string consumer, bool unavailable)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component",
            TimeProvider.System, resources, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        var session = await ConformanceObservedArtifactSession.OpenAsync(binding, context, default);
        try
        {
            AssertProfile(session);
            await (consumer switch
            {
                "scope" => ArtifactConformanceSessionTests.AccessScopeConsumerAsync(session, context, unavailable),
                "validation" => ArtifactConformanceSessionTests.ValidationAccessConsumerAsync(session, unavailable),
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

    [Theory]
    [ContributorArtifactData]
    public async Task Observed_reopen_preserves_actual_lineage_and_declared_state(string provider)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component",
            TimeProvider.System, resources, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        await ArtifactConformanceSessionTests.ReopenConsumerAsync(binding, context, resources, output,
            ContributorBindingFactory.ExpectedDurability == ArtifactDurability.LocalProcessCrash, AssertProfile);
    }

    [Theory]
    [ContributorArtifactData(ArtifactAdmissionProbe.Complete)]
    [ContributorArtifactData(ArtifactAdmissionProbe.Version)]
    [ContributorArtifactData(ArtifactAdmissionProbe.Publication)]
    [ContributorArtifactData(ArtifactAdmissionProbe.Deletion)]
    [ContributorArtifactData(ArtifactAdmissionProbe.Recovery)]
    [ContributorArtifactData(ArtifactAdmissionProbe.Fencing)]
    [ContributorArtifactData(ArtifactAdmissionProbe.Readers)]
    [ContributorArtifactData(ArtifactAdmissionProbe.Streaming)]
    [ContributorArtifactData(ArtifactAdmissionProbe.ForeignAuthority)]
    public async Task Observed_admission_preserves_actual_no_io_rejection(string provider, ArtifactAdmissionProbe probe)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component",
            TimeProvider.System, resources, new ConformanceEvidenceBuffer());
        var limits = probe == ArtifactAdmissionProbe.Complete
            ? new ArtifactLimits(artifactBytes: 1024, stagingBytes: 2048, transferSlots: 1, waitingCalls: 0)
            : new ArtifactLimits();
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(probe, limits, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        await ArtifactConformanceSessionTests.AdmissionConsumerAsync(binding, context, resources, output, probe, AssertProfile);
    }

    private static void AssertProfile(IArtifactConformanceSession session)
    {
        var actual = session.Store.Capabilities;
        Assert.Equal(ContributorBindingFactory.ExpectedDurability, actual.Durability);
        Assert.Equal(ContributorBindingFactory.ExpectedEnumeration, actual.Enumeration);
    }

    [Theory]
    [ContributorArtifactData(ArtifactObservationPoint.StagePrefix)]
    [ContributorArtifactData(ArtifactObservationPoint.BeforePublicationDecision)]
    [ContributorArtifactData(ArtifactObservationPoint.CommitProgress)]
    public async Task Observed_ordinary_cleanup_errors_preserve_actual_faulted_ownership(
        string provider, ArtifactObservationPoint point)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component",
            TimeProvider.System, resources, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        await ArtifactConformanceSessionTests.OrdinaryCleanupFailureConsumerAsync(binding, context, resources, output,
            point, AssertProfile);
    }

    [Theory]
    [ContributorArtifactData(ArtifactObservationPoint.ReadOpened)]
    [ContributorArtifactData(ArtifactObservationPoint.ReconciliationVerified)]
    [ContributorArtifactData(ArtifactObservationPoint.DeleteRemoved)]
    public async Task Observed_ordinary_failure_callbacks_preserve_actual_faulted_ownership(
        string provider, ArtifactObservationPoint point)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component",
            TimeProvider.System, resources, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        await ArtifactConformanceSessionTests.OrdinaryCallbackFailureConsumerAsync(binding, context, resources, output,
            point, AssertProfile);
    }

    [Theory]
    [ContributorArtifactData("candidate")]
    [ContributorArtifactData("acknowledgment")]
    public async Task Observed_ordinary_observer_errors_preserve_actual_faulted_ownership(string provider, string consumer)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var context = new ConformanceRunContext(ArtifactConformanceSessionTests.RunId(), "contributor-artifact-component",
            TimeProvider.System, resources, new ConformanceEvidenceBuffer());
        var binding = ContributorBindingFactory.Create(new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        await (consumer switch
        {
            "candidate" => ArtifactConformanceSessionTests.OrdinaryCandidateFailureConsumerAsync(
                binding, context, resources, output, AssertProfile),
            "acknowledgment" => ArtifactConformanceSessionTests.OrdinaryAcknowledgmentFailureConsumerAsync(
                binding, context, resources, output, AssertProfile),
            _ => throw new ArgumentException("BindingInvalid")
        });
    }
}
#endif
