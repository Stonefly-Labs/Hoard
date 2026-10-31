using System.Collections.Concurrent;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Conformance.Bindings.Memory;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Metadata;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class MemoryBindingTests
{
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
        var resources = new RecordingResources();
        await using var session = await new MemoryBinding(new string('a', 64)).CreateSessionAsync(Context(resources), default);
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
    public async Task Typed_adapter_continuation_damage_preserves_exact_valid_resume(MetadataContinuationCorruption corruption)
    {
        await using var session = await new MemoryBinding(new string('a', 64))
            .CreateSessionAsync(Context(new RecordingResources()), default);
        Success(await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await MetadataPagingAssertions.MalformedContinuationFieldsAsync(
            session.Store, session.Faults.CorruptContinuationAsync, corruption, default);
    }

    [Theory]
    [InlineData("upgrade")]
    [InlineData("invalid-upgrade")]
    [InlineData("upgrade-contention")]
    public async Task Explicit_legacy_factory_executes_unchanged_schema_consumers(string consumer)
    {
        var resources = new RecordingResources();
        var context = Context(resources);
        var binding = new MemoryBinding(new string('a', 64));
        ConformanceBindingAdmission.Validate(binding.Declaration, ConformanceCategory.Metadata);
        await using (var legacy = await binding.CreateLegacySessionAsync(context, default))
        {
            await (consumer switch
            {
                "upgrade" => MetadataSchemaAssertions.UpgradeAsync(legacy, default),
                "invalid-upgrade" => MetadataSchemaAssertions.InvalidUpgradeAsync(legacy, default),
                "upgrade-contention" => MetadataSchemaAssertions.UpgradeExclusionAsync(legacy, default),
                _ => throw new ArgumentException("BindingInvalid")
            });
        }
        Assert.True(resources.Settlements.Count >= 2);
        Assert.All(resources.Settlements.Values, task => Assert.True(task.IsCompletedSuccessfully));
    }

    [Fact]
    public async Task Disposal_registers_actual_pending_work_and_never_claims_physical_release()
    {
        var resources = new RecordingResources();
        var session = await new MemoryBinding(new string('a', 64)).CreateSessionAsync(Context(resources), default);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var released = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Task? disposing = null;
        Task<MetadataResult<MetadataCommitReceipt>>? committing = null;
        await using var observation = await session.Faults.ObserveBoundaryAsync(
            MetadataObservationPoint.BeforeCommitDecision,
            () => { entered.TrySetResult(); return new(released.Task); }, default);
        try
        {
            Success(await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
            var ticket = Success(await session.Store.ReserveOperationAsync(new(), default));
            committing = session.Store.CommitAsync(new(ticket, [new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent())],
                new MetadataOption<MetadataLeaseGuard>.None()), new(TimeSpan.FromMilliseconds(200)), default).AsTask();
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(MetadataFailureCode.DeadlineExceeded,
                Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(await committing).Code);
            disposing = session.DisposeAsync().AsTask();
            var actual = Assert.Single(resources.Settlements).Value;
            Assert.False(actual.IsCompleted);
            Assert.False(disposing.IsCompleted);
            Assert.Equal(ConformanceOwnershipState.Settling, (await session.ObserveCleanupAsync(default)).State);
        }
        finally
        {
            released.TrySetResult();
            await Task.WhenAll(disposing ?? Task.CompletedTask, committing ?? Task.CompletedTask)
                .WaitAsync(TimeSpan.FromSeconds(10));
            await session.DisposeAsync();
        }
        var cleanup = await session.ObserveCleanupAsync(default);
        Assert.Equal(ConformanceOwnershipState.Settling, cleanup.State);
        Assert.Single(cleanup.ResourceIds);
        Assert.All(resources.Settlements.Values, task => Assert.True(task.IsCompletedSuccessfully));
    }

    [Fact]
    public async Task Independent_snapshot_observes_committed_state_while_a_read_is_held()
    {
        var resources = new RecordingResources();
        await using var session = await new MemoryBinding(new string('a', 64)).CreateSessionAsync(Context(resources), default);
        Success(await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var registry = Registry();
        var ticket = Success(await session.Store.ReserveOperationAsync(new(), default));
        Success(await session.Store.CommitAsync(new(ticket, [new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent())],
            new MetadataOption<MetadataLeaseGuard>.None()), new(), default));
        var query = new MetadataReadGroup([registry.Selector]);
        var expected = MetadataEncoding.Encode(Success(await session.Store.ReadAsync(query, new(), default)));
        await session.Faults.ArmAsync(ConformanceFault.IndependentSnapshot, default);
        var reading = session.Store.ReadAsync(query, new(TimeSpan.FromMilliseconds(100)), default).AsTask();
        Task? settling = null;
        try
        {
            await session.Faults.WaitForBoundaryAsync(ConformanceFault.IndependentSnapshot, default);
            Assert.Equal(MetadataFailureCode.DeadlineExceeded,
                Assert.IsType<MetadataResult<MetadataReadSnapshot>.Failure>(await reading).Code);
            var snapshot = Success(await session.Faults.ObserveIndependentSnapshotAsync(query, default));
            Assert.Equal<byte>(expected, MetadataEncoding.Encode(snapshot));
            settling = session.Faults.AwaitSettlementAsync(default).AsTask();
            Assert.False(settling.IsCompleted);
            var observation = await session.Faults.ObserveAsync(ConformanceFault.IndependentSnapshot, default);
            Assert.Equal(1, observation.ObservationCount);
            Assert.NotEmpty((await session.ObserveCleanupAsync(default)).ResourceIds);
        }
        finally
        {
            await session.Faults.ReleaseAsync(ConformanceFault.IndependentSnapshot, default);
            await reading;
            if (settling is not null) { await settling; }
            await session.Faults.AwaitSettlementAsync(default);
        }
    }

    private static ConformanceRunContext Context(RecordingResources resources) => new(
        Guid.NewGuid(), "arbitrary-case-not-a-setup-selector", new MetadataConformanceClock(new(1_800_000_000_000)),
        resources, new ConformanceEvidenceBuffer());

    private static MetadataRegistry Registry() => new()
    {
        Id = new(Guid.NewGuid()),
        Ecosystem = new("nuget"),
        Upstream = new("https://example.invalid/v3/"),
        Enabled = true,
        Label = new("synthetic"),
        PolicyId = new MetadataOption<MetadataId>.None(),
        Secret = new MetadataOption<MetadataSecretReference>.None(),
        Revision = new(Guid.NewGuid())
    };

    private static T Success<T>(MetadataResult<T> result) where T : notnull =>
        Assert.IsType<MetadataResult<T>.Success>(result).Value;

    // A unit observation double, not native root ownership or package-provenance evidence.
    private sealed class RecordingResources : IConformanceResourceAllocator
    {
        public ConcurrentDictionary<ConformanceOwnedDirectory, Task> Settlements { get; } = new();

        public ValueTask<ConformanceOwnedDirectory> AllocateDirectoryAsync(CancellationToken token)
        {
            token.ThrowIfCancellationRequested();
            return ValueTask.FromResult(new ConformanceOwnedDirectory(
                "unit-" + Guid.NewGuid().ToString("N"), Path.Combine(Path.GetTempPath(), "not-created-unit-resource")));
        }

        public ValueTask<ConformanceCleanupObservation> ReleaseAsync(ConformanceOwnedDirectory resource, CancellationToken token)
        {
            token.ThrowIfCancellationRequested();
            return ValueTask.FromResult(new ConformanceCleanupObservation(ConformanceOwnershipState.Settling, [resource.ResourceId]));
        }

        public async ValueTask<ConformanceCleanupObservation> ReleaseAsync(
            ConformanceOwnedDirectory resource, Task actualSettlement, CancellationToken token)
        {
            Assert.Same(actualSettlement, Settlements.GetOrAdd(resource, actualSettlement));
            try { await actualSettlement.WaitAsync(TimeSpan.FromSeconds(30), token); }
            catch (TimeoutException)
            {
                return new(ConformanceOwnershipState.Retained, [resource.ResourceId],
                    ConformanceDiagnosticCode.CleanupIncomplete);
            }
            return new(ConformanceOwnershipState.Settling, [resource.ResourceId]);
        }
    }
}
