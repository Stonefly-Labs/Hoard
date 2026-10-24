using System.Collections.Concurrent;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Conformance.Bindings.Sqlite;
using Hoard.Fixtures.Metadata.Sqlite;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Metadata;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class SqliteBindingTests
{
    [Theory]
    [InlineData("competing-creates")]
    [InlineData("revision-races")]
    [InlineData("exact-bounds")]
    [InlineData("scopes-and-intervals")]
    [InlineData("bounded-pages")]
    [InlineData("lease-fences")]
    [InlineData("registry-isolation")]
    [InlineData("authorization-isolation")]
    [InlineData("final-graph")]
    [InlineData("reference-replacement")]
    [InlineData("reference-aba")]
    [InlineData("telemetry-rollback")]
    [InlineData("all-page-queries")]
    [InlineData("oversized-pages")]
    [InlineData("canonical-identity")]
    [InlineData("ticket-expiry")]
    [InlineData("lease-rollback")]
    [InlineData("independent-candidate")]
    [InlineData("faulted-candidates")]
    [InlineData("grouped-root")]
    [InlineData("reconciliation-io")]
    [InlineData("lost-acknowledgment")]
    [InlineData("distinct-contributions")]
    [InlineData("reconciliation-writer")]
    [InlineData("cancellation-decision")]
    [InlineData("queue-capacity")]
    [InlineData("disposal-ownership")]
    [InlineData("known-exceptions")]
    [InlineData("matching-evidence")]
    [InlineData("orphan-not-rollback")]
    [InlineData("replay-without-reacquisition")]
    [InlineData("lease-overflow")]
    [InlineData("absence-and-corruption")]
    public async Task Compiled_logical_consumers_execute_through_the_independent_sqlite_binding(string consumer)
    {
        await using var resources = new RecordingDirectories();
        var context = Context(resources);
        var clock = Assert.IsType<MetadataConformanceClock>(context.Clock);
        await using var session = await new SqliteBinding(new string('a', 64)).CreateSessionAsync(context, default);
        Success(await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var store = session.Store;
        var authority = session.Authority;
        var faults = session.Faults;
        await (consumer switch
        {
            "competing-creates" => MetadataConcurrencyAssertions.CompetingCreatesAsync(store, default),
            "revision-races" => MetadataConcurrencyAssertions.RevisionRacesAsync(store, default),
            "exact-bounds" => MetadataBoundsAssertions.ExactBoundsAsync(store, default),
            "scopes-and-intervals" => MetadataBoundsAssertions.ScopesAndIntervalsAsync(store, default),
            "bounded-pages" => MetadataPagingAssertions.BoundedDatasetsAsync(store, default),
            "lease-fences" => MetadataLeaseAssertions.OwnerGenerationAndRevisionFencesAsync(store, default),
            "registry-isolation" => MetadataIdentityAssertions.RegistryIsolationAsync(store, authority, default),
            "authorization-isolation" => MetadataIdentityAssertions.AuthorizationPartitionIsolationAsync(store, authority, default),
            "final-graph" => MetadataEntityAssertions.FinalGraphDeletionAndDisabledRetentionAsync(store, authority, default),
            "reference-replacement" => MetadataReferenceAssertions.EntryReplacementAndRemovalAsync(store, authority, default),
            "reference-aba" => MetadataReferenceAssertions.ZeroReferenceAbaFencingAsync(store, authority, default),
            "telemetry-rollback" => MetadataReferenceAssertions.InvalidTelemetryRollsBackEntryAndReferencesAsync(store, authority, default),
            "all-page-queries" => MetadataPagingAssertions.AllQueryKindsAsync(store, authority, default),
            "oversized-pages" => MetadataPagingAssertions.OversizedRequestsAndResultsAsync(store, authority, default),
            "canonical-identity" => MetadataIdentityAssertions.CanonicalTextAndForbiddenValuesAsync(store, default),
            "ticket-expiry" => MetadataTimeAssertions.TicketExpiryAndRollbackAsync(store, clock, default),
            "lease-rollback" => MetadataTimeAssertions.LeaseRollbackAsync(store, clock, default),
            "independent-candidate" => MetadataAtomicityAssertions.IndependentCandidateAsync(
                store, faults.ObserveBoundaryAsync, faults.ObserveIndependentSnapshotAsync, default),
            "faulted-candidates" => MetadataAtomicityAssertions.FaultedCandidatesAsync(store, faults.ObserveBoundaryAsync, default),
            "grouped-root" => MetadataAtomicityAssertions.GroupedReadsAsync(store, faults.ObserveBoundaryAsync, default),
            "reconciliation-io" => MetadataReconciliationAssertions.IoFailureAsync(store, faults.ObserveBoundaryAsync, default),
            "lost-acknowledgment" => MetadataReconciliationAssertions.LostAcknowledgmentAndAbandonmentAsync(
                store, faults.ObserveBoundaryAsync, default),
            "distinct-contributions" => MetadataReconciliationAssertions.DistinctContributionsAsync(store, faults.ObserveBoundaryAsync, default),
            "reconciliation-writer" => MetadataReconciliationAssertions.WriterContentionAsync(
                store, faults.HoldWriterAsync, faults.AwaitSettlementAsync, default),
            "cancellation-decision" => MetadataDeadlineAssertions.CancellationDecisionsAsync(
                store, faults.ObserveBoundaryAsync, faults.AwaitSettlementAsync, default),
            "queue-capacity" => MetadataDeadlineAssertions.QueueCapacityAsync(
                store, faults.ObserveBoundaryAsync, faults.AwaitSettlementAsync, default),
            "disposal-ownership" => MetadataDeadlineAssertions.DisposalOwnershipAsync(
                store, faults.ObserveBoundaryAsync, session.DisposeAsync, default),
            "known-exceptions" => MetadataDeadlineAssertions.KnownExceptionsAsync(store, faults.ObserveBoundaryAsync, default),
            "matching-evidence" => MetadataPublicationAssertions.MatchingEvidenceAsync(store, authority, default),
            "orphan-not-rollback" => MetadataPublicationAssertions.OrphanNotRollbackAsync(store, authority, faults.ObserveBoundaryAsync, default),
            "replay-without-reacquisition" => MetadataPublicationAssertions.ReplayWithoutReacquisitionAsync(store, authority, default),
            "lease-overflow" => MetadataLeaseAssertions.GenerationOverflowAsync(store, faults.SetLeaseGenerationAsync, default),
            "absence-and-corruption" => MetadataCorruptionAssertions.AbsenceAndCorruptGroupsAsync(store, faults.CorruptRecordAsync, default),
            _ => throw new ArgumentException("BindingInvalid")
        });
    }

    [Theory]
    [InlineData("explicit-admission")]
    [InlineData("invalid-budgets")]
    public async Task Compiled_admission_consumers_execute_before_actual_schema_admission(string consumer)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await new SqliteBinding(new string('a', 64)).CreateSessionAsync(Context(resources), default);
        await (consumer switch
        {
            "explicit-admission" => MetadataAdmissionAssertions.ExplicitAdmissionAsync(
                session.Store, session.Schema, () => session.Faults.Counters, default),
            "invalid-budgets" => MetadataAdmissionAssertions.InvalidBudgetsAsync(
                session.Store, session.Schema, () => session.Faults.Counters, session.DisposeAsync, default),
            _ => throw new ArgumentException("BindingInvalid")
        });
    }

    [Theory]
    [InlineData(MetadataRecordCorruption.CacheAuthorization)]
    [InlineData(MetadataRecordCorruption.AggregateAuthorization)]
    [InlineData(MetadataRecordCorruption.AggregateStart)]
    [InlineData(MetadataRecordCorruption.AggregateEnd)]
    [InlineData(MetadataRecordCorruption.LeaseResource)]
    public async Task Compiled_query_dimension_consumers_check_raw_sqlite_damage_before_filtering(MetadataRecordCorruption corruption)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await new SqliteBinding(new string('a', 64)).CreateSessionAsync(Context(resources), default);
        Success(await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await MetadataCorruptionAssertions.QueryDimensionsAsync(
            session.Store, session.Authority, session.Faults.CorruptAsync, corruption, default);
    }

    [Theory]
    [InlineData(MetadataLeaseExpiryAction.Renew)]
    [InlineData(MetadataLeaseExpiryAction.Release)]
    [InlineData(MetadataLeaseExpiryAction.Guard)]
    public async Task Compiled_lease_expiry_consumer_rechecks_the_actual_sqlite_decision(MetadataLeaseExpiryAction action)
    {
        await using var resources = new RecordingDirectories();
        var context = Context(resources);
        await using var session = await new SqliteBinding(new string('a', 64)).CreateSessionAsync(context, default);
        Success(await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await MetadataLeaseAssertions.ExpiryAtDecisionAsync(session.Store,
            Assert.IsType<MetadataConformanceClock>(context.Clock), session.Faults.ObserveBoundaryAsync, action, default);
    }

    [Fact]
    public async Task Compiled_cursor_consumer_checks_actual_sqlite_foreign_epoch_and_live_resume()
    {
        await using var resources = new RecordingDirectories();
        var binding = new SqliteBinding(new string('a', 64));
        await using var session = await binding.CreateSessionAsync(Context(resources), default);
        await using var foreign = await binding.CreateSessionAsync(Context(resources), default);
        Success(await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        Success(await foreign.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await MetadataPagingAssertions.ContinuationScopeAndEpochAsync(session.Store, foreign.Store, default);
    }

    [Fact]
    public async Task Cancelled_reopen_preserves_the_original_root_and_genuine_pending_worker_for_disposal()
    {
        await using var resources = new RecordingDirectories();
        await using var session = await new SqliteBinding(new string('a', 64)).CreateSessionAsync(Context(resources), default);
        Success(await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var released = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var observation = await session.Faults.ObserveBoundaryAsync(
            MetadataObservationPoint.BeforeCommitDecision,
            () => { entered.TrySetResult(); return new(released.Task); }, default);
        var ticket = Success(await session.Store.ReserveOperationAsync(new(), default));
        var committing = session.Store.CommitAsync(new(ticket,
            [new MetadataMutation.AcquireLease(new("synthetic"), new(Guid.NewGuid()), 30)],
            new MetadataOption<MetadataLeaseGuard>.None()), new(), default).AsTask();
        Task? disposing = null;
        using var cancellation = new CancellationTokenSource();
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            var reopening = session.ReopenAsync(cancellation.Token).AsTask();
            Assert.Equal(MetadataFailureCode.Disposed,
                Assert.IsType<MetadataResult<MetadataOperationTicket>.Failure>(
                    await session.Store.ReserveOperationAsync(new(), default)).Code);
            cancellation.Cancel();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(async () => await reopening);
            Assert.Empty(resources.Settlements);
            Assert.Single(resources.Directories);
            disposing = session.DisposeAsync().AsTask();
            var actual = Assert.Single(resources.Settlements).Value;
            Assert.Same(Assert.IsType<SqliteMetadataStore>(session.Store).ObserveLifetimeSettlementForTest(), actual);
            Assert.False(actual.IsCompleted);
            Assert.False(disposing.IsCompleted);
        }
        finally
        {
            released.TrySetResult();
            await Task.WhenAll(committing, disposing ?? Task.CompletedTask).WaitAsync(TimeSpan.FromSeconds(10));
        }
    }

    [Theory]
    [InlineData("receipts")]
    [InlineData("record-pages")]
    [InlineData("capacity")]
    [InlineData("ledger")]
    [InlineData("writer")]
    [InlineData("diagnostics")]
    [InlineData("publication")]
    [InlineData("cleanup")]
    public async Task Typed_adapter_controls_execute_unchanged_common_consumers(string consumer)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await new SqliteBinding(new string('a', 64)).CreateSessionAsync(Context(resources), default);
        Success(await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await (consumer switch
        {
            "receipts" => MetadataReconciliationAssertions.CorruptReceiptsAsync(session.Store, session.Faults.CorruptAsync, default),
            "record-pages" => MetadataCorruptionAssertions.PageRecordsAsync(
                session.Store, session.Faults.CorruptAsync, session.Faults.CorruptRecordAsync, default),
            "capacity" => MetadataFailureAssertions.StorageCapacityAsync(session.Store,
                token => session.Faults.ArmAsync(ConformanceFault.Capacity, token), default),
            "ledger" => MetadataFailureAssertions.LedgerCapacityAsync(session.Store, session.Faults.FillLedgerAsync, default),
            "writer" => MetadataDeadlineAssertions.WriterBudgetAsync(
                session.Store, session.Faults.HoldWriterAsync, session.Faults.AwaitSettlementAsync, default),
            "diagnostics" => MetadataFailureAssertions.DiagnosticsAsync(
                session.Store, session.Faults.ObserveBoundaryAsync, () => session.Faults.Counters, default),
            "publication" => MetadataPublicationAssertions.ProtectionThroughSettlementAsync(
                session.Store, session.Authority, session.Faults.ObserveBoundaryAsync, session.Faults.AwaitSettlementAsync, default),
            "cleanup" => MetadataDeadlineAssertions.IncompleteCleanupAsync(session.Store,
                session.Faults.ObserveBoundaryAsync, () => session.Faults.Counters,
                session.DisposeAsync, session.Faults.AwaitSettlementAsync, default),
            _ => throw new ArgumentException("BindingInvalid")
        });
    }

    [Theory]
    [InlineData(MetadataContinuationCorruption.Null)]
    [InlineData(MetadataContinuationCorruption.Omitted)]
    [InlineData(MetadataContinuationCorruption.WrongType)]
    [InlineData(MetadataContinuationCorruption.Empty)]
    [InlineData(MetadataContinuationCorruption.OddHex)]
    [InlineData(MetadataContinuationCorruption.InvalidHex)]
    public async Task Typed_continuation_damage_preserves_exact_valid_resume(MetadataContinuationCorruption corruption)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await new SqliteBinding(new string('a', 64)).CreateSessionAsync(Context(resources), default);
        Success(await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await MetadataPagingAssertions.MalformedContinuationFieldsAsync(
            session.Store, session.Faults.CorruptContinuationAsync, corruption, default);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Unrecognized_layouts_reject_without_raw_state_repair(bool partial)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await new SqliteBinding(new string('a', 64)).CreateSessionAsync(Context(resources), default);
        await MetadataSchemaAssertions.UnrecognizedLayoutAsync(session, partial, default);
    }

    [Fact]
    public async Task Future_and_corrupt_schemas_reject_after_actual_same_database_reopen()
    {
        await using var resources = new RecordingDirectories();
        var binding = new SqliteBinding(new string('a', 64));
        await using var future = await binding.CreateSessionAsync(Context(resources), default);
        await using var corrupt = await binding.CreateSessionAsync(Context(resources), default);
        await MetadataSchemaAssertions.FutureAndCorruptAsync(future, corrupt, default);
    }

    [Fact]
    public async Task Reopen_transfers_one_directory_without_settling_it_under_an_old_worker()
    {
        await using var resources = new RecordingDirectories();
        var context = Context(resources);
        var binding = new SqliteBinding(new string('a', 64));
        ConformanceBindingAdmission.Validate(binding.Declaration, ConformanceCategory.Metadata);
        await using var original = await binding.CreateSessionAsync(context, default);
        var admission = Success(await original.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await MetadataEntityAssertions.RoundTripAndInvalidRelationshipsAsync(original.Store, original.Authority, default);
        var before = await original.Faults.ObserveStateAsync(default);
        await using var reopened = await original.ReopenAsync(default);
        Assert.Single(resources.Directories);
        Assert.Empty(resources.Settlements);
        Assert.True(Assert.IsType<SqliteMetadataStore>(original.Store).ObserveLifetimeSettlementForTest().IsCompletedSuccessfully);
        await original.DisposeAsync();
        Assert.Empty(resources.Settlements);
        Assert.Equal(before, await reopened.Faults.ObserveStateAsync(default));
        Assert.Equal(admission.Epoch, Success(await reopened.Schema.PrepareAsync(
            new MetadataSchemaRequest.InspectOnly(), new(), default)).Epoch);
        await reopened.DisposeAsync();
        Assert.Same(Assert.IsType<SqliteMetadataStore>(reopened.Store).ObserveLifetimeSettlementForTest(),
            Assert.Single(resources.Settlements).Value);
        Assert.Equal(ConformanceOwnershipState.Settling, (await reopened.ObserveCleanupAsync(default)).State);
        await Assert.ThrowsAsync<InvalidOperationException>(async () => await reopened.ReopenAsync(default));
    }

    [Theory]
    [InlineData("upgrade")]
    [InlineData("invalid-upgrade")]
    [InlineData("upgrade-contention")]
    public async Task Explicit_legacy_factory_executes_unchanged_schema_consumers_on_the_same_database(string consumer)
    {
        await using var resources = new RecordingDirectories();
        await using var legacy = await new SqliteBinding(new string('a', 64)).CreateLegacySessionAsync(Context(resources), default);
        await (consumer switch
        {
            "upgrade" => MetadataSchemaAssertions.UpgradeAsync(legacy, default),
            "invalid-upgrade" => MetadataSchemaAssertions.InvalidUpgradeAsync(legacy, default),
            "upgrade-contention" => MetadataSchemaAssertions.UpgradeExclusionAsync(legacy, default),
            _ => throw new ArgumentException("BindingInvalid")
        });
        Assert.Single(resources.Directories);
        Assert.Single(resources.Settlements);
        Assert.All(resources.Settlements.Values, task => Assert.True(task.IsCompletedSuccessfully));
    }

    private static ConformanceRunContext Context(RecordingDirectories resources) => new(
        Guid.NewGuid(), "arbitrary-case-not-a-setup-selector", new MetadataConformanceClock(new(1_800_000_000_000)),
        resources, new ConformanceEvidenceBuffer());

    private static T Success<T>(MetadataResult<T> result) where T : notnull =>
        Assert.IsType<MetadataResult<T>.Success>(result).Value;

    // Unit resource observations, not controller-authorized physical release.
    private sealed class RecordingDirectories : IConformanceResourceAllocator, IAsyncDisposable
    {
        public List<ConformanceOwnedDirectory> Directories { get; } = [];
        public ConcurrentDictionary<ConformanceOwnedDirectory, Task> Settlements { get; } = new();
        public ValueTask<ConformanceOwnedDirectory> AllocateDirectoryAsync(CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var directory = new ConformanceOwnedDirectory("unit-" + Guid.NewGuid().ToString("N"),
                Directory.CreateTempSubdirectory("hoard-sqlite-binding-").FullName);
            Directories.Add(directory);
            return ValueTask.FromResult(directory);
        }
        public ValueTask<ConformanceCleanupObservation> ReleaseAsync(
            ConformanceOwnedDirectory directory, CancellationToken cancellationToken) =>
            throw new InvalidOperationException("ActualSettlementRequired");
        public async ValueTask<ConformanceCleanupObservation> ReleaseAsync(
            ConformanceOwnedDirectory directory, Task actualSettlement, CancellationToken cancellationToken)
        {
            Assert.Same(actualSettlement, Settlements.GetOrAdd(directory, actualSettlement));
            try { await actualSettlement.WaitAsync(TimeSpan.FromSeconds(30), cancellationToken); }
            catch (TimeoutException)
            {
                return new(ConformanceOwnershipState.Retained, [directory.ResourceId],
                    ConformanceDiagnosticCode.CleanupIncomplete);
            }
            return new(ConformanceOwnershipState.Settling, [directory.ResourceId]);
        }
        public async ValueTask DisposeAsync()
        {
            Assert.Equal(Directories.Count, Settlements.Count);
            await Task.WhenAll(Settlements.Values).WaitAsync(TimeSpan.FromSeconds(10));
            foreach (var directory in Directories)
            {
                foreach (var capture in Directory.GetDirectories(directory.DirectoryPath))
                {
                    Assert.Equal(Path.Combine(directory.DirectoryPath, "metadata.db.captures"), capture);
                    foreach (var file in Directory.GetFiles(capture)) { File.Delete(file); }
                    Directory.Delete(capture);
                }
                foreach (var file in Directory.GetFiles(directory.DirectoryPath)) { File.Delete(file); }
                Directory.Delete(directory.DirectoryPath);
            }
        }
    }
}
