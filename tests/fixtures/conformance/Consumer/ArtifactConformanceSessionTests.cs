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
