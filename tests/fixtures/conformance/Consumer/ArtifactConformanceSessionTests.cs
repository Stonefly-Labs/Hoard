using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Conformance.Bindings.Local;
using Hoard.Fixtures.Conformance.Bindings.ObjectSemantics;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Evidence;
using Xunit.Abstractions;
using RecordingDirectories = Hoard.Fixtures.Conformance.Consumer.LocalArtifactSessionTests.RecordingDirectories;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class ArtifactConformanceSessionTests(ITestOutputHelper output)
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Ordinary_acknowledgment_shaped_observer_errors_still_fault_actual_settlement(string provider)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        var failure = new IOException("InjectedPublicationAcknowledgmentLoss");
        try
        {
            await using var observer = await session.Faults.ObserveBoundaryAsync(
                ArtifactObservationPoint.PublicationSelected, () => ValueTask.FromException(failure), default);
            var ticket = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Value;
            using var source = new ArtifactPublicationAssertions.ShortSource("unexpected acknowledgment error"u8.ToArray());
            var staged = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Success>(
                await session.Store.StageAsync(ticket, source, new(), default)).Value;
            Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await session.Store.CommitAsync(staged, new(), default)).Code);
            await session.Faults.AwaitSettlementAsync(default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await Assert.ThrowsAsync<InvalidOperationException>(() => session.DisposeAsync().AsTask()); }
        var settlement = Assert.Single(resources.Settlements).Value;
        Assert.True(settlement.IsFaulted);
        Assert.Contains(failure, settlement.Exception!.InnerExceptions);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "private-staging")]
    [InlineData("local", "concurrent-writers")]
    [InlineData("local", "lost-acknowledgment")]
    [InlineData("local", "visible-before-ack")]
    [InlineData("object", "private-staging")]
    [InlineData("object", "concurrent-writers")]
    [InlineData("object", "lost-acknowledgment")]
    [InlineData("object", "direct-availability")]
    public async Task Observed_boundary_consumers_preserve_actual_binding_guarantees(string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        try
        {
            await BoundaryConsumerAsync(session, consumer);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    private static async Task BoundaryConsumerAsync(IArtifactConformanceSession session, string consumer)
    {
        if (consumer == "concurrent-writers")
        {
            await ObserveAsync(session, ArtifactObservationPoint.PublicationAdmitted,
                install => ArtifactPublicationAssertions.ConcurrentEquivalentWritersAsync(session.Store, install, default));
            return;
        }
        if (consumer == "lost-acknowledgment")
        {
            await using var injection = await session.Faults.InjectPublicationAcknowledgmentLossAsync(default);
            await ArtifactReconciliationAssertions.LostAcknowledgmentAsync(
                session.Store, () => Assert.Equal(0, injection.ObservationCount), default);
            await injection.WaitForEntryAsync(default);
            Assert.Equal(1, injection.ObservationCount);
            await session.Faults.AwaitSettlementAsync(default);
            return;
        }
        var point = consumer switch
        {
            "private-staging" => ArtifactObservationPoint.StagePrefix,
            "visible-before-ack" => ArtifactObservationPoint.ReceiptPersisted,
            "direct-availability" => ArtifactObservationPoint.DirectVerification,
            _ => throw new ArgumentException("BindingInvalid")
        };
        await using var barrier = new ArtifactConformanceBarrier(consumer);
        await ObserveAsync(session, point, async install =>
        {
            void Block() => install(() => new(barrier.HoldAsync()));
            void Release()
            {
                install(static () => ValueTask.CompletedTask);
                barrier.Release();
            }
            if (consumer == "private-staging") { Block(); }
            try
            {
                await (consumer switch
                {
                    "private-staging" => ArtifactPublicationAssertions.PrivateStagingAsync(session.Store,
                        token => barrier.Entered.WaitAsync(token), Release, default),
                    "visible-before-ack" => ArtifactVisibilityAssertions.VisibleBeforeAcknowledgmentAsync(session.Store,
                        Block, token => barrier.Entered.WaitAsync(token), Release, default),
                    "direct-availability" => ArtifactVisibilityAssertions.DirectAvailabilityAsync(
                        session.Store, session.Maintenance, session.Identity,
                        Block, token => barrier.Entered.WaitAsync(token), Release, default),
                    _ => throw new ArgumentException("BindingInvalid")
                });
            }
            finally { Release(); }
        });
    }

    private static async Task ObserveAsync(IArtifactConformanceSession session, ArtifactObservationPoint point,
        Func<Action<Func<ValueTask>>, Task> assertion)
    {
        Func<ValueTask>? observer = null;
        await using var registration = await session.Faults.ObserveBoundaryAsync(point,
            () => (Volatile.Read(ref observer) ?? throw new InvalidOperationException("BindingInvalid"))(), default);
        try { await assertion(callback => Volatile.Write(ref observer, callback)); }
        finally { await session.Faults.AwaitSettlementAsync(default); }
    }

    [Theory]
    [InlineData("local", "destination-failure")]
    [InlineData("local", "exact-retry")]
    [InlineData("local", "staged-length")]
    [InlineData("local", "recreation")]
    [InlineData("local", "reader-exclusion")]
    [InlineData("object", "destination-failure")]
    [InlineData("object", "exact-retry")]
    [InlineData("object", "staged-length")]
    [InlineData("object", "recreation")]
    [InlineData("object", "reader-exclusion")]
    public async Task Observed_read_reconciliation_and_deletion_preserve_actual_binding_guarantees(
        string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        try
        {
            await (consumer switch
            {
                "destination-failure" => ArtifactReadAssertions.DestinationFailureAsync(
                    session.Store, "Synthetic borrowed destination failure", default),
                "exact-retry" => ArtifactReconciliationAssertions.AcknowledgedReceiptRetryAsync(session.Store, default),
                "staged-length" => ArtifactPublicationAssertions.ConflictingStagedLengthAsync(session.Store, default),
                "recreation" => ArtifactDeletionAssertions.ExactReceiptsAndRecreationAsync(
                    session.Store, session.Maintenance, session.Identity, default),
                "reader-exclusion" => ArtifactDeletionAssertions.HeldReaderExcludesDeletionAsync(session.Store, default),
                _ => throw new ArgumentException("BindingInvalid")
            });
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "empty")]
    [InlineData("local", "unknown-length")]
    [InlineData("local", "expectations")]
    [InlineData("local", "unsupported")]
    [InlineData("local", "duplicates")]
    [InlineData("object", "empty")]
    [InlineData("object", "unknown-length")]
    [InlineData("object", "expectations")]
    [InlineData("object", "unsupported")]
    [InlineData("object", "duplicates")]
    public async Task Observed_publication_consumers_preserve_actual_binding_guarantees(
        string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        try
        {
            await (consumer switch
            {
                "empty" => ArtifactPublicationAssertions.EmptyContentAndAbsenceAsync(session.Store, default),
                "unknown-length" => ArtifactPublicationAssertions.UnknownLengthAndRealEofAsync(session.Store, default),
                "expectations" => ArtifactPublicationAssertions.EveryExpectationAndEofAsync(session.Store, default),
                "unsupported" => ArtifactPublicationAssertions.UnsupportedChecksumAndRangeAsync(session.Store, default),
                "duplicates" => ArtifactPublicationAssertions.VerifiedDuplicatesAsync(session.Store, default),
                _ => throw new ArgumentException("BindingInvalid")
            });
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Releasing_native_work_does_not_block_an_independent_release_or_rearming(string provider)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        await using var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        await ArtifactBindingAssertions.ConcurrentReleaseAsync(session, default);
        ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
    }

    [Theory]
    [InlineData("local", ConformanceFault.PublicationBoundary)]
    [InlineData("local", ConformanceFault.DirectVisibility)]
    [InlineData("local", ConformanceFault.PayloadDamage)]
    [InlineData("local", ConformanceFault.Capacity)]
    [InlineData("local", ConformanceFault.NativeNonCooperation)]
    [InlineData("local", ConformanceFault.CleanupFailure)]
    [InlineData("local", ConformanceFault.GenerationBoundary)]
    [InlineData("local", ConformanceFault.ReceiptBoundary)]
    [InlineData("local", ConformanceFault.SourceNonCooperation)]
    [InlineData("local", ConformanceFault.SinkNonCooperation)]
    [InlineData("object", ConformanceFault.PublicationBoundary)]
    [InlineData("object", ConformanceFault.DirectVisibility)]
    [InlineData("object", ConformanceFault.PayloadDamage)]
    [InlineData("object", ConformanceFault.Capacity)]
    [InlineData("object", ConformanceFault.NativeNonCooperation)]
    [InlineData("object", ConformanceFault.CleanupFailure)]
    [InlineData("object", ConformanceFault.GenerationBoundary)]
    [InlineData("object", ConformanceFault.ReceiptBoundary)]
    [InlineData("object", ConformanceFault.SourceNonCooperation)]
    [InlineData("object", ConformanceFault.SinkNonCooperation)]
    public async Task Full_binding_controls_reach_actual_work_and_preserve_borrowed_ownership(
        string provider, ConformanceFault fault) =>
        await RunControlAsync(provider, fault, "full-artifact-binding");

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Missing_hooks_reject_before_dispatch_and_actual_binding_passes(string provider) =>
        await RunControlAsync(provider, ConformanceFault.PublicationBoundary, "QC-05");

    private async Task RunControlAsync(string provider, ConformanceFault fault, string caseId)
    {
        await using var resources = new RecordingDirectories();
        var clock = new ControlledClock();
        var context = new ConformanceRunContext(RunId(), caseId, clock,
            resources, new ConformanceEvidenceBuffer());
        var binding = Binding(provider);
        if (fault == ConformanceFault.PublicationBoundary)
        {
            await BindingAdmissionAssertions.ArtifactsAsync(binding.Declaration, context);
            Assert.Empty(resources.Settlements);
        }
        var session = await ConformanceObservedArtifactSession.OpenAsync(binding, context, default);
        try
        {
            await ArtifactBindingAssertions.ControlsAsync(session, fault, clock.Advance, default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", true)]
    [InlineData("object", false)]
    public async Task Observed_full_binding_reopens_actual_components_and_fences_stale_controls(
        string provider, bool retainsPublication)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var binding = Binding(provider);
        var original = await ConformanceObservedArtifactSession.OpenAsync(binding, context, default);
        var current = original;
        try
        {
            var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(original.Store, default);
            var origin = original.CaptureOrigin();
            current = Assert.IsType<ConformanceObservedArtifactSession>(await original.ReopenAsync(default));
            var reopened = current.CaptureOrigin();
            Assert.Equal(origin.SessionId, reopened.ParentSessionId);
            Assert.NotEqual(origin.Components["store"].InstanceId, reopened.Components["store"].InstanceId);
            Assert.Equal(retainsPublication, original.Identity == current.Identity);
            await Assert.ThrowsAsync<InvalidOperationException>(() => original.Faults.ArmAsync(
                ConformanceFault.Capacity, default).AsTask());
            var result = await current.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default);
            if (retainsPublication)
            {
                await using var read = Assert.IsType<ArtifactResult<IArtifactReadSession>.Success>(result).Value;
                using var destination = new MemoryStream();
                Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Success>(
                    await read.CopyToAsync(destination, new(), default));
            }
            else { Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(result); }
            await original.DisposeAsync();
            await ArtifactCompositionAssertions.ConfiguredPublicationAsync(current.Store, default);
            ConformanceSessionOriginOutput.Write(output, origin);
            ConformanceSessionOriginOutput.Write(output, reopened);
        }
        finally { await current.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
    }

    private static Guid RunId()
    {
        if (!Guid.TryParseExact(Environment.GetEnvironmentVariable("HOARD_ORIGIN_RUN_ID"), "D", out var runId)
            || runId == Guid.Empty)
        { throw new InvalidOperationException("PrerequisiteMissing"); }
        return runId;
    }

    private static IArtifactConformanceBinding Binding(string provider)
    {
        var variable = provider switch
        {
            "local" => "HOARD_ARTIFACT_LOCAL_PACKAGE_SHA256",
            "object" => "HOARD_ARTIFACT_OBJECT_PACKAGE_SHA256",
            _ => throw new ArgumentException("BindingInvalid")
        };
        var sha256 = Environment.GetEnvironmentVariable(variable)
            ?? throw new InvalidOperationException("PrerequisiteMissing");
        var options = new ArtifactAssertionOptions(references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid())));
        return provider == "local" ? new LocalBinding(sha256, options: options)
            : new ObjectSemanticsBinding(sha256, options: options);
    }

    private sealed class ControlledClock : TimeProvider
    {
        private long ticks = new DateTimeOffset(2026, 1, 1, 0, 0, 0, TimeSpan.Zero).Ticks;
        public override DateTimeOffset GetUtcNow() => new(Interlocked.Read(ref ticks), TimeSpan.Zero);
        public void Advance(TimeSpan amount) => Interlocked.Add(ref ticks, amount.Ticks);
    }
}
