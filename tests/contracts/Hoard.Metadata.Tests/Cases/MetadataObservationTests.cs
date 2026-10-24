using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataObservationTests
{
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
        var registry = Registry();
        await Commit(fixture, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        registry = await Read<MetadataRegistry>(fixture, registry.Selector);
        var ticket = await Ticket(fixture);
        var captured = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var observation = fixture.Controls.RegisterObserver("corruption.captured", () =>
        {
            captured.TrySetResult();
            return new(release.Task);
        });
        MetadataCorruptionRequest request =
            new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.NullLabel);
        var corrupting = CommonCorruptionAsync(fixture, request, default).AsTask();
        var updated = registry with { Label = new("intervening committed registry"), Revision = Revision() };
        try
        {
            await captured.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Success(await fixture.Store.CommitAsync(Batch(ticket,
                new MetadataMutation.PutRegistry(updated, new ExpectedRevision.Match(registry.Revision))), new(), default));
            updated = await Read<MetadataRegistry>(fixture, registry.Selector);
        }
        finally { release.TrySetResult(); }
        var error = await Record.ExceptionAsync(async () =>
        {
            await using var scope = await corrupting;
        });
        Assert.Equal<byte>(MetadataEncoding.Encode(updated),
            MetadataEncoding.Encode(await Read<MetadataRegistry>(fixture, registry.Selector)));
        Assert.IsType<MetadataResolution.Committed>(Success(await fixture.Store.ReconcileAsync(ticket, new(), default)));
        Assert.Equal("FaultControl.Conflict", Assert.IsType<InvalidOperationException>(error).Message);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Fixture_closure_admission_rejects_later_corruption_while_a_candidate_is_held(bool reopen)
    {
        await using var fixture = await OpenAsync();
        var registry = Registry();
        await Commit(fixture, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        registry = await Read<MetadataRegistry>(fixture, registry.Selector);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var observation = await CommonObservations(fixture)(MetadataObservationPoint.MutationApplied, () =>
        {
            entered.TrySetResult();
            return new(release.Task);
        }, default);
        var updated = registry with { Label = new("held registry"), Revision = Revision() };
        var committing = fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.PutRegistry(updated, new ExpectedRevision.Match(registry.Revision))), new(), default).AsTask();
        MetadataFixtureSession? transferred = null;
        Task? closing = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            closing = CloseAsync();
            var error = await Assert.ThrowsAsync<InvalidOperationException>(() => CommonCorruptionAsync(fixture,
                new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.NullLabel),
                default).AsTask().WaitAsync(TimeSpan.FromSeconds(1)));
            Assert.Equal("Metadata fixture closure has been admitted.", error.Message);
        }
        finally
        {
            release.TrySetResult();
            await committing;
            if (closing is not null) { await closing; }
            if (transferred is not null) { await transferred.DisposeAsync(); }
        }

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
        var registry = Registry();
        await Commit(fixture, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        var baseline = MetadataEncoding.Encode(await Read<MetadataRegistry>(fixture, registry.Selector));
        var request = new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.NullLabel);
        await using var scope = await CommonCorruptionAsync(fixture, request, default);
        var damaged = await scope.ObserveAsync(default);
        Assert.NotEqual(scope.Original, damaged);
        await Assert.ThrowsAsync<InvalidOperationException>(() => CommonCorruptionAsync(fixture, request, default).AsTask());
        await Assert.ThrowsAsync<InvalidOperationException>(() => fixture.ReopenAsync().AsTask());
        await Assert.ThrowsAsync<InvalidOperationException>(() => fixture.DisposeAsync().AsTask());
        Assert.Equal(damaged, await scope.ObserveAsync(default));
        await Task.WhenAll(scope.DisposeAsync().AsTask(), scope.DisposeAsync().AsTask());
        Assert.Equal<byte>(baseline, MetadataEncoding.Encode(await Read<MetadataRegistry>(fixture, registry.Selector)));
        await using var replacement = await CommonCorruptionAsync(fixture, request, default);
        await scope.DisposeAsync();
        Assert.Equal(damaged, await replacement.ObserveAsync(default));
        await Assert.ThrowsAsync<InvalidOperationException>(() => fixture.DisposeAsync().AsTask());
    }

    [Fact]
    public async Task Cancellation_after_payload_mutation_restores_before_releasing_ownership()
    {
        await using var fixture = await OpenAsync();
        var registry = Registry();
        await Commit(fixture, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        var baseline = MetadataEncoding.Encode(await Read<MetadataRegistry>(fixture, registry.Selector));
        using var cancelled = new CancellationTokenSource();
        var calls = 0;
        ValueTask Observe()
        {
            if (Interlocked.Increment(ref calls) == 1) { cancelled.Cancel(); }
            return ValueTask.CompletedTask;
        }
        await using var native = fixture.Controls.RegisterObserver("sqlite.persisted.changed", Observe);
        await using var managed = fixture.Controls.RegisterObserver("memory.persisted.changed", Observe);
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => CommonCorruptionAsync(fixture,
            new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.NullLabel), cancelled.Token).AsTask());
        Assert.Equal(2, calls);
        Assert.Equal<byte>(baseline, MetadataEncoding.Encode(await Read<MetadataRegistry>(fixture, registry.Selector)));
        await using var reopened = await fixture.ReopenAsync();
    }

    [Fact]
    public async Task Failed_payload_restoration_retains_a_recoverable_fixture_owner()
    {
        await using var fixture = await OpenAsync();
        var registry = Registry();
        await Commit(fixture, new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
        var baseline = MetadataEncoding.Encode(await Read<MetadataRegistry>(fixture, registry.Selector));
        var calls = 0;
        ValueTask Observe()
        {
            if (Interlocked.Increment(ref calls) <= 2)
            { throw new InvalidOperationException("Synthetic payload observation failure."); }
            return ValueTask.CompletedTask;
        }
        await using var native = fixture.Controls.RegisterObserver("sqlite.persisted.changed", Observe);
        await using var managed = fixture.Controls.RegisterObserver("memory.persisted.changed", Observe);
        await Assert.ThrowsAsync<InvalidOperationException>(() => CommonCorruptionAsync(fixture,
            new MetadataCorruptionRequest.Record(registry.Selector, MetadataRecordCorruption.NullLabel), default).AsTask());
        await Assert.ThrowsAsync<InvalidOperationException>(() => fixture.DisposeAsync().AsTask());
        await fixture.RestoreCorruptionsForTestAsync(default);
        Assert.Equal(3, calls);
        Assert.Equal<byte>(baseline, MetadataEncoding.Encode(await Read<MetadataRegistry>(fixture, registry.Selector)));
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
