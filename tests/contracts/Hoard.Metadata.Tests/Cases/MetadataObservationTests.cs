using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataObservationTests
{
    [Fact]
    public async Task Original_schema_controls_preserve_cancelled_handoff_and_observe_real_state()
    {
        await using var fixture = await OpenAsync();
        var registry = Registry();
        await Commit(fixture, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        registry = await Read<MetadataRegistry>(fixture, registry.Selector);
        var projection = new OriginalMetadataSchemaSession(fixture);
        Assert.Same(fixture.Store, projection.Store);
        Assert.Same(fixture.Schema, projection.Schema);
        var before = await projection.ObserveStateAsync(default);
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => projection.ReopenAsync(cancelled.Token).AsTask());
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => projection.AuthorizeUpgradeAsync(cancelled.Token).AsTask());
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => projection.ObserveStateAsync(cancelled.Token).AsTask());
        Assert.Equal(before, await projection.ObserveStateAsync(default));
        Assert.Equal(registry, await Read<MetadataRegistry>(fixture, registry.Selector));
        await using (var corruption = await CommonCorruptionAsync(fixture,
            new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.NullLabel), default))
        {
            Assert.NotEqual(corruption.Original, await corruption.ObserveAsync(default));
        }
        Assert.Equal(registry, await Read<MetadataRegistry>(fixture, registry.Selector));
        Success(await projection.SetFutureSchemaAsync(default));
        Assert.NotEqual(before, await projection.ObserveStateAsync(default));
        await using var reopened = await projection.ReopenAsync(default);
        Assert.NotSame(fixture.Store, reopened.Store);
        Assert.Equal(MetadataFailureCode.Disposed, Failed(await fixture.Store.ReserveOperationAsync(new(), default)));
        Assert.Equal(MetadataSchemaState.Incompatible, Success(await reopened.Schema.InspectAsync(new(), default)).State);
    }

    [Fact]
    public async Task Original_diagnostic_fault_can_be_consumed_without_replacing_its_owner()
    {
        await using var fixture = await OpenAsync();
        var calls = 0;
        await using var owner = fixture.Controls.RegisterObserver("mutation.applied", () =>
        {
            calls++;
            throw new InvalidOperationException("Original diagnostic owner " + MetadataTestData.Canary);
        });
        await MetadataFailureAssertions.DiagnosticsAsync(
            fixture.Store, () => CommonCounters(fixture), MetadataTestData.Canary,
            MetadataTestData.AssertSanitized, default);
        Assert.Equal(1, calls);
        Assert.Single(fixture.Controls.Diagnostics);
        CommonDiagnosticAssertions(fixture);
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            fixture.Controls.ObserveAsync("mutation.applied").AsTask());
        Assert.Equal(2, calls);
    }

    [Fact]
    public async Task Corruption_capture_does_not_overwrite_an_intervening_committed_image()
    {
        await using var fixture = await OpenAsync();
        await MetadataCorruptionAssertions.CaptureConflictAsync(fixture.Store, CommonObservations(fixture),
            (request, token) => CommonCorruptionAsync(fixture, request, token), false, default);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Fixture_closure_admission_rejects_later_corruption_while_a_candidate_is_held(bool reopen)
    {
        await using var fixture = await OpenAsync();
        MetadataFixtureSession? transferred = null;
        try
        {
            await MetadataCorruptionAssertions.ClosureAdmissionAsync(fixture.Store, CommonObservations(fixture),
                (request, token) => CommonCorruptionAsync(fixture, request, token), CloseAsync, default);
        }
        finally { if (transferred is not null) { await transferred.DisposeAsync(); } }

        async Task CloseAsync()
        {
            if (reopen) { transferred = await fixture.ReopenAsync(); }
            else { await fixture.DisposeAsync(); }
        }
    }

    [Fact]
    public async Task Corruption_scope_rejects_overlapping_owners_and_restores_exact_payload()
    {
        await using var fixture = await OpenAsync();
        await MetadataCorruptionAssertions.ScopeOwnershipAsync(fixture.Store,
            (request, token) => CommonCorruptionAsync(fixture, request, token),
            async () => { await using var unexpected = await fixture.ReopenAsync(); },
            () => fixture.DisposeAsync().AsTask(), false, default);
    }

    [Fact]
    public async Task Cancellation_after_payload_mutation_restores_before_releasing_ownership()
    {
        await using var fixture = await OpenAsync();
        await MetadataCorruptionAssertions.CancelledApplicationAsync(fixture.Store, CommonObservations(fixture),
            (request, token) => CommonCorruptionAsync(fixture, request, token), false, default);
        await using var reopened = await fixture.ReopenAsync();
    }

    [Fact]
    public async Task Failed_payload_restoration_retains_a_recoverable_fixture_owner()
    {
        await using var fixture = await OpenAsync();
        await MetadataCorruptionAssertions.FailedRestorationAsync(fixture.Store, CommonObservations(fixture),
            (request, token) => CommonCorruptionAsync(fixture, request, token),
            fixture.RestoreCorruptionsForTestAsync, () => fixture.DisposeAsync().AsTask(), false, default);
    }

    [Fact]
    public async Task Typed_writer_cancellation_preserves_the_original_holder()
    {
        await using var fixture = await OpenAsync();
        var batch = Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        await using (var owner = await CommonWriterAsync(fixture, default))
        {
            using var cancelled = new CancellationTokenSource();
            cancelled.Cancel();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() => CommonWriterAsync(fixture, cancelled.Token).AsTask());
            Assert.Equal(MetadataFailureCode.DeadlineExceeded, Failed(await fixture.Store.CommitAsync(
                batch, new(TimeSpan.FromMilliseconds(50)), default)));
            await CommonSettlementAsync(fixture, default);
            await Missing(fixture, Registry().Selector);
        }
        Success(await fixture.Store.CommitAsync(batch, new(), default));
        await Read<MetadataRegistry>(fixture, Registry().Selector);
    }

    [Fact]
    public async Task Scoped_observation_rejects_duplicate_registration_without_replacing_the_owner()
    {
        var controls = new MetadataFixtureControls();
        var calls = 0;
        await using var registration = controls.RegisterObserver("M0", () => { calls++; return ValueTask.CompletedTask; });
        Assert.Throws<InvalidOperationException>(() => controls.RegisterObserver("M0", () => throw new InvalidOperationException()));
        await controls.ObserveAsync("M0");
        Assert.Equal(1, calls);
        await registration.DisposeAsync();
        await using var replacement = controls.RegisterObserver("M0", () => { calls += 10; return ValueTask.CompletedTask; });
        await registration.DisposeAsync();
        await controls.ObserveAsync("M0");
        Assert.Equal(11, calls);
    }

    [Fact]
    public async Task Scoped_disposal_does_not_remove_a_newer_legacy_observer()
    {
        var controls = new MetadataFixtureControls();
        var calls = 0;
        await using var registration = controls.RegisterObserver("M0", () => throw new InvalidOperationException());
        controls.SetObserver("M0", () => { calls++; return ValueTask.CompletedTask; });
        await registration.DisposeAsync();
        await controls.ObserveAsync("M0");
        Assert.Equal(1, calls);
    }

    [Fact]
    public async Task Scoped_disposal_unregisters_future_observation_without_settling_an_active_callback()
    {
        var controls = new MetadataFixtureControls();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var registration = controls.RegisterObserver("M0", () =>
        {
            entered.TrySetResult();
            return new(release.Task);
        });
        var observing = controls.ObserveAsync("M0").AsTask();
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            await registration.DisposeAsync();
            Assert.False(observing.IsCompleted);
            await controls.ObserveAsync("M0").AsTask().WaitAsync(TimeSpan.FromSeconds(5));
            Assert.False(observing.IsCompleted);
        }
        finally
        {
            release.TrySetResult();
            await observing.WaitAsync(TimeSpan.FromSeconds(5));
        }

    }

    [Fact]
    public async Task Typed_observation_rejects_cancelled_and_unknown_requests_without_leaking_registration()
    {
        await using var fixture = await OpenAsync();
        var observe = CommonObservations(fixture);
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            observe(MetadataObservationPoint.BeforeCommitDecision, () => ValueTask.CompletedTask, cancelled.Token).AsTask());
        await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() =>
            observe((MetadataObservationPoint)int.MaxValue, () => ValueTask.CompletedTask, default).AsTask());
        await using var registration = await observe(
            MetadataObservationPoint.BeforeCommitDecision, () => ValueTask.CompletedTask, default);
    }

    [Theory]
    [InlineData(MetadataObservationPoint.BeforeSchemaUpgrade)]
    [InlineData(MetadataObservationPoint.SchemaCandidatePrepared)]
    public async Task Typed_schema_upgrade_observation_runs_on_the_actual_provider_boundary(MetadataObservationPoint boundary)
    {
        var provider = Environment.GetEnvironmentVariable("HOARD_METADATA_PROVIDER")
            ?? throw new InvalidOperationException("Metadata acceptance requires an explicit provider.");
        await using var legacy = MetadataFixtureSession.Create(provider, new MetadataTestClock(),
            compatibleSchema: "fixture-sqlite-v1");
        Success(await legacy.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await using var current = await legacy.ReopenAsync();
        var point = await current.AuthorizeUpgradeAsync();
        var calls = 0;
        await using var registration = await CommonObservations(current)(
            boundary, () => { calls++; return ValueTask.CompletedTask; }, default);
        Success(await current.Schema.PrepareAsync(new MetadataSchemaRequest.Upgrade(
            point.SchemaVersion, point.SchemaVersion.Replace("-v1", "-v2", StringComparison.Ordinal), point), new(), default));
        Assert.Equal(1, calls);
    }
}
