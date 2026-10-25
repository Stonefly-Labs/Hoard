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
    [InlineData("memory", "upgrade")]
    [InlineData("memory", "upgrade-invalid")]
    [InlineData("memory", "upgrade-exclusive")]
    [InlineData("memory", "future-corrupt")]
    [InlineData("sqlite", "upgrade")]
    [InlineData("sqlite", "upgrade-invalid")]
    [InlineData("sqlite", "upgrade-exclusive")]
    [InlineData("sqlite", "future-corrupt")]
    public async Task Observed_schema_consumers_preserve_actual_reopen_lineage(string provider, string consumer)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-metadata-binding",
            new MetadataConformanceClock(new(1_800_000_000_000)), resources, new ConformanceEvidenceBuffer());
        var origins = new List<ConformanceSessionOrigin>();
        var observed = consumer == "future-corrupt"
            ? await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default)
            : await ConformanceObservedMetadataSession.OpenLegacyAsync(Binding(provider), context, default);
        await using var original = new OriginSession(observed, origins);
        origins.Add(observed.CaptureOrigin());
        if (consumer == "future-corrupt")
        {
            await using var corrupt = new OriginSession(
                await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default), origins);
            origins.Add(corrupt.CaptureOrigin());
            await MetadataSchemaAssertions.FutureAndCorruptAsync(original, corrupt, default);
        }
        else
        {
            await (consumer switch
            {
                "upgrade" => MetadataSchemaAssertions.UpgradeAsync(original, default),
                "upgrade-invalid" => MetadataSchemaAssertions.InvalidUpgradeAsync(original, default),
                "upgrade-exclusive" => MetadataSchemaAssertions.UpgradeExclusionAsync(original, default),
                _ => throw new ArgumentException("BindingInvalid")
            });
        }
        foreach (var origin in origins) { ConformanceSessionOriginOutput.Write(output, origin); }
    }

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
    [InlineData("memory", "bounds")]
    [InlineData("memory", "scopes")]
    [InlineData("memory", "page-kinds")]
    [InlineData("memory", "page-size")]
    [InlineData("memory", "page-datasets")]
    [InlineData("memory", "time-ticket")]
    [InlineData("memory", "time-lease")]
    [InlineData("memory", "cancel")]
    [InlineData("memory", "queue")]
    [InlineData("memory", "exceptions")]
    [InlineData("memory", "ledger")]
    [InlineData("memory", "diagnostics")]
    [InlineData("memory", "evidence")]
    [InlineData("memory", "publication-replay")]
    [InlineData("memory", "publication-orphan")]
    [InlineData("memory", "corrupt-groups")]
    [InlineData("memory", "corrupt-pages")]
    [InlineData("memory", "admission")]
    [InlineData("memory", "invalid-budget")]
    [InlineData("memory", "incomplete-cleanup")]
    [InlineData("memory", "disposal")]
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
    [InlineData("sqlite", "bounds")]
    [InlineData("sqlite", "scopes")]
    [InlineData("sqlite", "page-kinds")]
    [InlineData("sqlite", "page-size")]
    [InlineData("sqlite", "page-datasets")]
    [InlineData("sqlite", "time-ticket")]
    [InlineData("sqlite", "time-lease")]
    [InlineData("sqlite", "cancel")]
    [InlineData("sqlite", "queue")]
    [InlineData("sqlite", "exceptions")]
    [InlineData("sqlite", "ledger")]
    [InlineData("sqlite", "diagnostics")]
    [InlineData("sqlite", "evidence")]
    [InlineData("sqlite", "publication-replay")]
    [InlineData("sqlite", "publication-orphan")]
    [InlineData("sqlite", "corrupt-groups")]
    [InlineData("sqlite", "corrupt-pages")]
    [InlineData("sqlite", "admission")]
    [InlineData("sqlite", "invalid-budget")]
    [InlineData("sqlite", "incomplete-cleanup")]
    [InlineData("sqlite", "disposal")]
    public async Task Observed_factories_execute_unchanged_common_consumers_with_actual_origins(
        string provider, string consumer)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var clock = new MetadataConformanceClock(new(1_800_000_000_000));
        var context = new ConformanceRunContext(RunId(), "full-metadata-binding",
            clock, resources, new ConformanceEvidenceBuffer());
        await using var session = await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default);
        var origin = session.CaptureOrigin();
        if (consumer is not ("layout-empty" or "layout-partial" or "admission" or "invalid-budget"))
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
            "bounds" => MetadataBoundsAssertions.ExactBoundsAsync(session.Store, default),
            "scopes" => MetadataBoundsAssertions.ScopesAndIntervalsAsync(session.Store, default),
            "page-kinds" => MetadataPagingAssertions.AllQueryKindsAsync(session.Store, session.Authority, default),
            "page-size" => MetadataPagingAssertions.OversizedRequestsAndResultsAsync(
                session.Store, session.Authority, default),
            "page-datasets" => MetadataPagingAssertions.BoundedDatasetsAsync(session.Store, default),
            "time-ticket" => MetadataTimeAssertions.TicketExpiryAndRollbackAsync(session.Store, clock, default),
            "time-lease" => MetadataTimeAssertions.LeaseRollbackAsync(session.Store, clock, default),
            "cancel" => MetadataDeadlineAssertions.CancellationDecisionsAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, session.Faults.AwaitSettlementAsync, default),
            "queue" => MetadataDeadlineAssertions.QueueCapacityAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, session.Faults.AwaitSettlementAsync, default),
            "exceptions" => MetadataDeadlineAssertions.KnownExceptionsAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, default),
            "ledger" => MetadataFailureAssertions.LedgerCapacityAsync(session.Store, session.Faults.FillLedgerAsync, default),
            "diagnostics" => MetadataFailureAssertions.DiagnosticsAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, () => session.Faults.Counters, default),
            "evidence" => MetadataPublicationAssertions.MatchingEvidenceAsync(session.Store, session.Authority, default),
            "publication-replay" => MetadataPublicationAssertions.ReplayWithoutReacquisitionAsync(
                session.Store, session.Authority, default),
            "publication-orphan" => MetadataPublicationAssertions.OrphanNotRollbackAsync(
                session.Store, session.Authority, session.Faults.ObserveBoundaryAsync, default),
            "corrupt-groups" => MetadataCorruptionAssertions.AbsenceAndCorruptGroupsAsync(
                session.Store, session.Faults.CorruptRecordAsync, default),
            "corrupt-pages" => MetadataCorruptionAssertions.PageRecordsAsync(
                session.Store, session.Faults.CorruptAsync, session.Faults.CorruptRecordAsync, default),
            "admission" => MetadataAdmissionAssertions.ExplicitAdmissionAsync(
                session.Store, session.Schema, () => session.Faults.Counters, default),
            "invalid-budget" => MetadataAdmissionAssertions.InvalidBudgetsAsync(
                session.Store, session.Schema, () => session.Faults.Counters, session.Store.DisposeAsync, default),
            "incomplete-cleanup" => MetadataDeadlineAssertions.IncompleteCleanupAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, () => session.Faults.Counters,
                session.Store.DisposeAsync, session.Faults.AwaitSettlementAsync, default),
            "disposal" => MetadataDeadlineAssertions.DisposalOwnershipAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, session.Store.DisposeAsync, default),
            _ => throw new ArgumentException("BindingInvalid")
        });
        ConformanceSessionOriginOutput.Write(output, origin);
    }

    private sealed class OriginSession(
        ConformanceObservedMetadataSession session, List<ConformanceSessionOrigin> origins) : IMetadataConformanceSession
    {
        public IMetadataStore Store => session.Store;
        public IMetadataSchemaAdministration Schema => session.Schema;
        public IMetadataConformanceAuthority Authority => session.Authority;
        public IMetadataConformanceFaultDriver Faults => session.Faults;
        public ConformanceSessionOrigin CaptureOrigin() => session.CaptureOrigin();
        public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken cancellationToken) =>
            session.ObserveCleanupAsync(cancellationToken);
        public ValueTask DisposeAsync() => session.DisposeAsync();

        public async ValueTask<IMetadataConformanceSession> ReopenAsync(CancellationToken cancellationToken)
        {
            var reopened = await session.ReopenAsync(cancellationToken);
            var handedOff = false;
            try
            {
                var observed = Assert.IsType<ConformanceObservedMetadataSession>(reopened);
                var current = new OriginSession(observed, origins);
                origins.Add(observed.CaptureOrigin());
                handedOff = true;
                return current;
            }
            finally { if (!handedOff) { await reopened.DisposeAsync(); } }
        }
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
