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
    [MetadataBindingData(false, "capture")]
    [MetadataBindingData(true, "capture")]
    [MetadataBindingData(false, "cancel")]
    [MetadataBindingData(true, "cancel")]
    [MetadataBindingData(false, "restore")]
    [MetadataBindingData(true, "restore")]
    public async Task Observed_corruption_application_preserves_actual_commits_and_recoverable_ownership(
        string provider, bool operation, string consumer)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-metadata-binding",
            new MetadataConformanceClock(new(1_800_000_000_000)), resources, new ConformanceEvidenceBuffer());
        await using var session = await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default);
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
            await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var origin = session.CaptureOrigin();
        await (consumer switch
        {
            "capture" => MetadataCorruptionAssertions.CaptureConflictAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, session.Faults.CorruptAsync, operation, default),
            "cancel" => MetadataCorruptionAssertions.CancelledApplicationAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, session.Faults.CorruptAsync, operation, default),
            "restore" => MetadataCorruptionAssertions.FailedRestorationAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, session.Faults.CorruptAsync,
                session.Faults.RestoreCorruptionsAsync, () => session.DisposeAsync().AsTask(), operation, default),
            _ => throw new ArgumentException("BindingInvalid")
        });
        ConformanceSessionOriginOutput.Write(output, origin);
    }

    [Theory]
    [MetadataBindingData(false)]
    [MetadataBindingData(true)]
    public async Task Observed_corruption_closure_fences_later_scopes_while_actual_work_is_held(
        string provider, bool reopen)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-metadata-binding",
            new MetadataConformanceClock(new(1_800_000_000_000)), resources, new ConformanceEvidenceBuffer());
        var original = await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default);
        IMetadataConformanceSession current = original;
        try
        {
            Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
                await original.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
            var origin = original.CaptureOrigin();
            await MetadataCorruptionAssertions.ClosureAdmissionAsync(
                original.Store, original.Faults.ObserveBoundaryAsync, original.Faults.CorruptAsync,
                async () =>
                {
                    if (reopen) { current = await original.ReopenAsync(default); }
                    else { await original.DisposeAsync(); }
                }, default);
            ConformanceSessionOriginOutput.Write(output, origin);
            if (reopen)
            {
                var reopened = Assert.IsType<ConformanceObservedMetadataSession>(current).CaptureOrigin();
                Assert.Equal(origin.SessionId, reopened.ParentSessionId);
                ConformanceSessionOriginOutput.Write(output, reopened);
            }
        }
        finally { await current.DisposeAsync(); }
    }

    [Theory]
    [MetadataBindingData(false)]
    [MetadataBindingData(true)]
    public async Task Observed_corruption_scopes_preserve_actual_target_and_closure_ownership(
        string provider, bool operation)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-metadata-binding",
            new MetadataConformanceClock(new(1_800_000_000_000)), resources, new ConformanceEvidenceBuffer());
        await using var session = await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default);
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
            await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await MetadataCorruptionAssertions.ScopeOwnershipAsync(session.Store, session.Faults.CorruptAsync,
            async () => { await using var unexpected = await session.ReopenAsync(default); },
            () => session.DisposeAsync().AsTask(), operation, default);
        ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
    }

    [Theory]
    [MetadataBindingData(MetadataContinuationCorruption.Null)]
    [MetadataBindingData(MetadataContinuationCorruption.Omitted)]
    [MetadataBindingData(MetadataContinuationCorruption.WrongType)]
    [MetadataBindingData(MetadataContinuationCorruption.Empty)]
    [MetadataBindingData(MetadataContinuationCorruption.OddHex)]
    [MetadataBindingData(MetadataContinuationCorruption.InvalidHex)]
    public async Task Observed_continuation_corruption_preserves_actual_pages(
        string provider, MetadataContinuationCorruption corruption)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-metadata-binding",
            new MetadataConformanceClock(new(1_800_000_000_000)), resources, new ConformanceEvidenceBuffer());
        await using var session = await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default);
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
            await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var origin = session.CaptureOrigin();
        await MetadataPagingAssertions.MalformedContinuationFieldsAsync(
            session.Store, session.Faults.CorruptContinuationAsync, corruption, default);
        ConformanceSessionOriginOutput.Write(output, origin);
    }

    [Theory]
    [MetadataBindingData(MetadataRecordCorruption.CacheAuthorization)]
    [MetadataBindingData(MetadataRecordCorruption.AggregateAuthorization)]
    [MetadataBindingData(MetadataRecordCorruption.AggregateStart)]
    [MetadataBindingData(MetadataRecordCorruption.AggregateEnd)]
    [MetadataBindingData(MetadataRecordCorruption.LeaseResource)]
    public async Task Observed_query_corruption_preserves_actual_dimensions(
        string provider, MetadataRecordCorruption corruption)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-metadata-binding",
            new MetadataConformanceClock(new(1_800_000_000_000)), resources, new ConformanceEvidenceBuffer());
        await using var session = await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default);
        Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
            await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var origin = session.CaptureOrigin();
        await MetadataCorruptionAssertions.QueryDimensionsAsync(
            session.Store, session.Authority, session.Faults.CorruptAsync, corruption, default);
        ConformanceSessionOriginOutput.Write(output, origin);
    }

    [Theory]
    [MetadataBindingData]
    public async Task Observed_continuations_reject_foreign_actual_store_epochs(string provider)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-metadata-binding",
            new MetadataConformanceClock(new(1_800_000_000_000)), resources, new ConformanceEvidenceBuffer());
        await using var original = await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default);
        await using var foreign = await ConformanceObservedMetadataSession.OpenAsync(Binding(provider), context, default);
        foreach (var session in new[] { original, foreign })
        {
            Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
                await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        }
        var origin = original.CaptureOrigin();
        var foreignOrigin = foreign.CaptureOrigin();
        await MetadataPagingAssertions.ContinuationScopeAndEpochAsync(original.Store, foreign.Store, default);
        ConformanceSessionOriginOutput.Write(output, origin);
        ConformanceSessionOriginOutput.Write(output, foreignOrigin);
    }

    [Theory]
    [MetadataBindingData("upgrade")]
    [MetadataBindingData("upgrade-invalid")]
    [MetadataBindingData("upgrade-exclusive")]
    [MetadataBindingData("future-corrupt")]
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
    [MetadataBindingData]
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
    [MetadataBindingData("capacity")]
    [MetadataBindingData("writer")]
    [MetadataBindingData("publication")]
    [MetadataBindingData("entities")]
    [MetadataBindingData("graph")]
    [MetadataBindingData("independent")]
    [MetadataBindingData("atomic")]
    [MetadataBindingData("grouped")]
    [MetadataBindingData("lease-generation")]
    [MetadataBindingData("lease-fences")]
    [MetadataBindingData("lease-renew")]
    [MetadataBindingData("lease-release")]
    [MetadataBindingData("lease-guard")]
    [MetadataBindingData("text")]
    [MetadataBindingData("registry")]
    [MetadataBindingData("authorization")]
    [MetadataBindingData("references")]
    [MetadataBindingData("reference-aba")]
    [MetadataBindingData("telemetry")]
    [MetadataBindingData("create-race")]
    [MetadataBindingData("revision-race")]
    [MetadataBindingData("reconcile-writer")]
    [MetadataBindingData("reconcile-io")]
    [MetadataBindingData("reconcile-ack")]
    [MetadataBindingData("contributions")]
    [MetadataBindingData("receipts")]
    [MetadataBindingData("layout-empty")]
    [MetadataBindingData("layout-partial")]
    [MetadataBindingData("bounds")]
    [MetadataBindingData("scopes")]
    [MetadataBindingData("page-kinds")]
    [MetadataBindingData("page-size")]
    [MetadataBindingData("page-datasets")]
    [MetadataBindingData("time-ticket")]
    [MetadataBindingData("time-lease")]
    [MetadataBindingData("cancel")]
    [MetadataBindingData("queue")]
    [MetadataBindingData("exceptions")]
    [MetadataBindingData("ledger")]
    [MetadataBindingData("diagnostics")]
    [MetadataBindingData("evidence")]
    [MetadataBindingData("publication-replay")]
    [MetadataBindingData("publication-orphan")]
    [MetadataBindingData("corrupt-groups")]
    [MetadataBindingData("corrupt-pages")]
    [MetadataBindingData("admission")]
    [MetadataBindingData("invalid-budget")]
    [MetadataBindingData("incomplete-cleanup")]
    [MetadataBindingData("disposal")]
    public async Task Observed_factories_execute_unchanged_common_consumers_with_actual_origins(
        string provider, string consumer) =>
        await RunCommonConsumerAsync(provider, consumer, "full-metadata-binding");

    [Theory]
    [MetadataBindingData]
    public async Task Missing_hooks_reject_before_dispatch_and_actual_binding_passes(string provider) =>
        await RunCommonConsumerAsync(provider, "admission", "QC-05");

    private async Task RunCommonConsumerAsync(string provider, string consumer, string caseId)
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var clock = new MetadataConformanceClock(new(1_800_000_000_000));
        var context = new ConformanceRunContext(RunId(), caseId,
            clock, resources, new ConformanceEvidenceBuffer());
        var binding = Binding(provider);
        if (consumer == "admission")
        {
            await BindingAdmissionAssertions.MetadataAsync(binding.Declaration, context);
            Assert.Empty(resources.Settlements);
        }
        await using var session = await ConformanceObservedMetadataSession.OpenAsync(binding, context, default);
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
#if HOARD_METADATA_CONTRIBUTOR
        if (provider != ContributorBindingFactory.BindingId) { throw new ArgumentException("BindingInvalid"); }
        return ContributorBindingFactory.Create();
#else
        var variable = provider switch
        {
            "memory" => "HOARD_METADATA_MEMORY_PACKAGE_SHA256",
            "sqlite" => "HOARD_METADATA_SQLITE_PACKAGE_SHA256",
            _ => throw new ArgumentException("BindingInvalid")
        };
        var sha256 = Environment.GetEnvironmentVariable(variable)
            ?? throw new InvalidOperationException("PrerequisiteMissing");
        return provider == "memory" ? new MemoryBinding(sha256) : new SqliteBinding(sha256);
#endif
    }
}
