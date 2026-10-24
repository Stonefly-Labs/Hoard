using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataObservationTests
{
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
