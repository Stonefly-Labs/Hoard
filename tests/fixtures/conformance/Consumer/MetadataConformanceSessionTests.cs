using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Conformance.Bindings.Memory;
using Hoard.Fixtures.Conformance.Bindings.Sqlite;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Evidence;
using Hoard.Testing.Conformance.Metadata;
using Xunit.Abstractions;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class MetadataConformanceSessionTests(ITestOutputHelper output)
{
    [Theory]
    [InlineData("memory")]
    [InlineData("sqlite")]
    public async Task Observed_reopen_preserves_public_state_and_fences_stale_controls(string provider)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-metadata-binding",
            new MetadataConformanceClock(new(1_800_000_000_000)), resources, new ConformanceEvidenceBuffer());
        var original = await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default);
        IMetadataConformanceSession current = original;
        try
        {
            var origin = original.CaptureOrigin();
            current = await MetadataSchemaAssertions.CompatibleReopenAsync(original, default);
            var reopened = Assert.IsType<ConformanceObservedMetadataSession>(current).CaptureOrigin();
            Assert.Equal(origin.SessionId, reopened.ParentSessionId);
            Assert.NotEqual(origin.Components["store"].InstanceId, reopened.Components["store"].InstanceId);
            ConformanceSessionOriginOutput.Write(output, origin);
            ConformanceSessionOriginOutput.Write(output, reopened);
        }
        finally { await current.DisposeAsync(); }
        Assert.All(resources.Settlements.Values, task => Assert.True(task.IsCompletedSuccessfully));
    }

    [Theory]
    [InlineData("memory", "capacity")]
    [InlineData("memory", "writer")]
    [InlineData("memory", "publication")]
    [InlineData("memory", "entities")]
    [InlineData("memory", "graph")]
    [InlineData("memory", "independent")]
    [InlineData("memory", "atomic")]
    [InlineData("memory", "grouped")]
    [InlineData("memory", "lease-generation")]
    [InlineData("memory", "lease-fences")]
    [InlineData("memory", "lease-renew")]
    [InlineData("memory", "lease-release")]
    [InlineData("memory", "lease-guard")]
    [InlineData("memory", "text")]
    [InlineData("memory", "registry")]
    [InlineData("memory", "authorization")]
    [InlineData("memory", "references")]
    [InlineData("memory", "reference-aba")]
    [InlineData("memory", "telemetry")]
    [InlineData("memory", "create-race")]
    [InlineData("memory", "revision-race")]
    [InlineData("memory", "reconcile-writer")]
    [InlineData("memory", "reconcile-io")]
    [InlineData("memory", "reconcile-ack")]
    [InlineData("memory", "contributions")]
    [InlineData("memory", "receipts")]
    [InlineData("memory", "layout-empty")]
    [InlineData("memory", "layout-partial")]
    [InlineData("sqlite", "capacity")]
    [InlineData("sqlite", "writer")]
    [InlineData("sqlite", "publication")]
    [InlineData("sqlite", "entities")]
    [InlineData("sqlite", "graph")]
    [InlineData("sqlite", "independent")]
    [InlineData("sqlite", "atomic")]
    [InlineData("sqlite", "grouped")]
    [InlineData("sqlite", "lease-generation")]
    [InlineData("sqlite", "lease-fences")]
    [InlineData("sqlite", "lease-renew")]
    [InlineData("sqlite", "lease-release")]
    [InlineData("sqlite", "lease-guard")]
    [InlineData("sqlite", "text")]
    [InlineData("sqlite", "registry")]
    [InlineData("sqlite", "authorization")]
    [InlineData("sqlite", "references")]
    [InlineData("sqlite", "reference-aba")]
    [InlineData("sqlite", "telemetry")]
    [InlineData("sqlite", "create-race")]
    [InlineData("sqlite", "revision-race")]
    [InlineData("sqlite", "reconcile-writer")]
    [InlineData("sqlite", "reconcile-io")]
    [InlineData("sqlite", "reconcile-ack")]
    [InlineData("sqlite", "contributions")]
    [InlineData("sqlite", "receipts")]
    [InlineData("sqlite", "layout-empty")]
    [InlineData("sqlite", "layout-partial")]
    public async Task Observed_factories_execute_unchanged_common_consumers_with_actual_origins(
        string provider, string consumer)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var clock = new MetadataConformanceClock(new(1_800_000_000_000));
        var context = new ConformanceRunContext(RunId(), "full-metadata-binding",
            clock, resources, new ConformanceEvidenceBuffer());
        await using var session = await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default);
        if (consumer is not ("layout-empty" or "layout-partial"))
        {
            Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
                await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        }
        await (consumer switch
        {
            "capacity" => MetadataFailureAssertions.StorageCapacityAsync(session.Store,
                token => session.Faults.ArmAsync(ConformanceFault.Capacity, token), default),
            "writer" => MetadataDeadlineAssertions.WriterBudgetAsync(
                session.Store, session.Faults.HoldWriterAsync, session.Faults.AwaitSettlementAsync, default),
            "publication" => MetadataPublicationAssertions.ProtectionThroughSettlementAsync(
                session.Store, session.Authority, session.Faults.ObserveBoundaryAsync, session.Faults.AwaitSettlementAsync, default),
            "entities" => MetadataEntityAssertions.RoundTripAndInvalidRelationshipsAsync(
                session.Store, session.Authority, default),
            "graph" => MetadataEntityAssertions.FinalGraphDeletionAndDisabledRetentionAsync(
                session.Store, session.Authority, default),
            "independent" => MetadataAtomicityAssertions.IndependentCandidateAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, session.Faults.ObserveIndependentSnapshotAsync, default),
            "atomic" => MetadataAtomicityAssertions.FaultedCandidatesAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, default),
            "grouped" => MetadataAtomicityAssertions.GroupedReadsAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, default),
            "lease-generation" => MetadataLeaseAssertions.GenerationOverflowAsync(
                session.Store, session.Faults.SetLeaseGenerationAsync, default),
            "lease-fences" => MetadataLeaseAssertions.OwnerGenerationAndRevisionFencesAsync(session.Store, default),
            "lease-renew" => MetadataLeaseAssertions.ExpiryAtDecisionAsync(
                session.Store, clock, session.Faults.ObserveBoundaryAsync, MetadataLeaseExpiryAction.Renew, default),
            "lease-release" => MetadataLeaseAssertions.ExpiryAtDecisionAsync(
                session.Store, clock, session.Faults.ObserveBoundaryAsync, MetadataLeaseExpiryAction.Release, default),
            "lease-guard" => MetadataLeaseAssertions.ExpiryAtDecisionAsync(
                session.Store, clock, session.Faults.ObserveBoundaryAsync, MetadataLeaseExpiryAction.Guard, default),
            "text" => MetadataIdentityAssertions.CanonicalTextAndForbiddenValuesAsync(session.Store, default),
            "registry" => MetadataIdentityAssertions.RegistryIsolationAsync(session.Store, session.Authority, default),
            "authorization" => MetadataIdentityAssertions.AuthorizationPartitionIsolationAsync(
                session.Store, session.Authority, default),
            "references" => MetadataReferenceAssertions.EntryReplacementAndRemovalAsync(
                session.Store, session.Authority, default),
            "reference-aba" => MetadataReferenceAssertions.ZeroReferenceAbaFencingAsync(
                session.Store, session.Authority, default),
            "telemetry" => MetadataReferenceAssertions.InvalidTelemetryRollsBackEntryAndReferencesAsync(
                session.Store, session.Authority, default),
            "create-race" => MetadataConcurrencyAssertions.CompetingCreatesAsync(session.Store, default),
            "revision-race" => MetadataConcurrencyAssertions.RevisionRacesAsync(session.Store, default),
            "reconcile-writer" => MetadataReconciliationAssertions.WriterContentionAsync(
                session.Store, session.Faults.HoldWriterAsync, session.Faults.AwaitSettlementAsync, default),
            "reconcile-io" => MetadataReconciliationAssertions.IoFailureAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, default),
            "reconcile-ack" => MetadataReconciliationAssertions.LostAcknowledgmentAndAbandonmentAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, default),
            "contributions" => MetadataReconciliationAssertions.DistinctContributionsAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, default),
            "receipts" => MetadataReconciliationAssertions.CorruptReceiptsAsync(
                session.Store, session.Faults.CorruptAsync, default),
            "layout-empty" => MetadataSchemaAssertions.UnrecognizedLayoutAsync(session, false, default),
            "layout-partial" => MetadataSchemaAssertions.UnrecognizedLayoutAsync(session, true, default),
            _ => throw new ArgumentException("BindingInvalid")
        });
        ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
    }

    private static Guid RunId()
    {
        if (!Guid.TryParseExact(Environment.GetEnvironmentVariable("HOARD_ORIGIN_RUN_ID"), "D", out var runId)
            || runId == Guid.Empty)
        { throw new InvalidOperationException("PrerequisiteMissing"); }
        return runId;
    }

    private static IMetadataConformanceBinding Binding(string provider)
    {
        var variable = provider switch
        {
            "memory" => "HOARD_METADATA_MEMORY_PACKAGE_SHA256",
            "sqlite" => "HOARD_METADATA_SQLITE_PACKAGE_SHA256",
            _ => throw new ArgumentException("BindingInvalid")
        };
        var sha256 = Environment.GetEnvironmentVariable(variable)
            ?? throw new InvalidOperationException("PrerequisiteMissing");
        return provider == "memory" ? new MemoryBinding(sha256) : new SqliteBinding(sha256);
    }
}
