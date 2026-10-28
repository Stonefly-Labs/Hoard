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
internal sealed class ContributorArtifactDataAttribute(string consumer) : DataAttribute
{
    public override IEnumerable<object[]> GetData(MethodInfo testMethod)
    {
        yield return [ContributorBindingFactory.BindingId, consumer];
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
    public async Task Observed_portable_consumers_preserve_actual_guarantees(string provider, string consumer)
    {
        Assert.Equal(ContributorBindingFactory.BindingId, provider);
        if (!Guid.TryParseExact(Environment.GetEnvironmentVariable("HOARD_ORIGIN_RUN_ID"), "D", out var runId)
            || runId == Guid.Empty)
        { throw new InvalidOperationException("PrerequisiteMissing"); }
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(runId, "contributor-artifact-component", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var limits = consumer == "cap-crossing" ? new ArtifactLimits(10, 10, 1) : null;
        long liveReferences = consumer == "live-references" ? 1 : 0;
        var referencesAvailable = true;
        var options = new ArtifactAssertionOptions(limits, (_, _) => ValueTask.FromResult(
            new ArtifactReferenceObservation(referencesAvailable, liveReferences, Guid.NewGuid())));
        var session = await ConformanceObservedArtifactSession.OpenAsync(
            ContributorBindingFactory.Create(options), context, default);
        try
        {
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
                _ => throw new ArgumentException("BindingInvalid")
            });
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }
}
#endif
