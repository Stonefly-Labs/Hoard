using System.Collections.Concurrent;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Conformance.Bindings.ObjectSemantics;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using RecordingDirectories = Hoard.Fixtures.Conformance.Consumer.LocalArtifactSessionTests.RecordingDirectories;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class ObjectArtifactSessionTests
{
    [Theory]
    [InlineData("publication")]
    [InlineData("expectations")]
    [InlineData("private-staging")]
    public async Task Owned_object_projection_executes_unchanged_common_consumers(string consumer)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await ObjectArtifactAssertionSessions.CreateAsync(Context(resources), default);
        Assert.True(session.Ready);
        await (consumer switch
        {
            "publication" => ArtifactPublicationAssertions.UnknownLengthAndRealEofAsync(session.Store, default),
            "expectations" => ArtifactPublicationAssertions.EveryExpectationAndEofAsync(session.Store, default),
            "private-staging" => PrivateStagingAsync(session),
            _ => throw new ArgumentException("BindingInvalid")
        });
    }

    private static async Task PrivateStagingAsync(IArtifactAssertionSession session)
    {
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var registration = await session.ObserveBoundaryAsync(ArtifactObservationPoint.StagePrefix,
            () => { entered.TrySetResult(); return new(release.Task); }, default);
        try
        {
            await ArtifactPublicationAssertions.PrivateStagingAsync(session.Store,
                token => entered.Task.WaitAsync(TimeSpan.FromSeconds(5), token), () => release.TrySetResult(), default);
        }
        finally { release.TrySetResult(); }
    }

    [Fact]
    public async Task All_typed_observations_register_together_and_stale_disposal_cannot_remove_a_replacement()
    {
        await using var resources = new RecordingDirectories();
        await using var session = await ObjectArtifactAssertionSessions.CreateAsync(Context(resources), default);
        var arrivals = new ConcurrentQueue<ArtifactObservationPoint>();
        var registrations = new List<IAsyncDisposable>();
        try
        {
            foreach (var point in Enum.GetValues<ArtifactObservationPoint>())
            {
                registrations.Add(await session.ObserveBoundaryAsync(point, () =>
                {
                    arrivals.Enqueue(point);
                    return ValueTask.CompletedTask;
                }, default));
            }
            await Assert.ThrowsAsync<InvalidOperationException>(() => session.ObserveBoundaryAsync(
                ArtifactObservationPoint.StageVerified, () => ValueTask.CompletedTask, default).AsTask());
            await ArtifactPublicationAssertions.UnknownLengthAndRealEofAsync(session.Store, default);
            Assert.Contains(ArtifactObservationPoint.StageVerified, arrivals);
            Assert.Contains(ArtifactObservationPoint.ReceiptPersisted, arrivals);
        }
        finally
        {
            foreach (var registration in registrations) { await registration.DisposeAsync(); }
        }
        var observed = arrivals.Count;
        await ArtifactPublicationAssertions.UnknownLengthAndRealEofAsync(session.Store, default);
        Assert.Equal(observed, arrivals.Count);
        var old = await session.ObserveBoundaryAsync(
            ArtifactObservationPoint.StageVerified, () => ValueTask.CompletedTask, default);
        await old.DisposeAsync();
        await using var current = await session.ObserveBoundaryAsync(ArtifactObservationPoint.StageVerified,
            () => { arrivals.Enqueue(ArtifactObservationPoint.StageVerified); return ValueTask.CompletedTask; }, default);
        await old.DisposeAsync();
        await ArtifactPublicationAssertions.UnknownLengthAndRealEofAsync(session.Store, default);
        Assert.True(arrivals.Count > observed);
    }

    [Fact]
    public async Task Object_restart_joins_old_authority_and_uses_fresh_epoch_authority_and_private_child()
    {
        await using var resources = new RecordingDirectories(useActualAllocator: true);
        var original = await ObjectArtifactAssertionSessions.CreateAsync(Context(resources), default);
        var current = original;
        var identity = original.Identity;
        var authority = original.Authority;
        var guard = Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Success>(
            await authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
                identity, new ArtifactDigest(new string('a', 64))), new(), default)).Value;
        try
        {
            var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(original.Store, default);
            var restarting = original.ReopenAsync(default).AsTask();
            Assert.False(restarting.IsCompleted);
            Assert.False(original.Ready);
            await guard.DisposeAsync();
            current = await restarting.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.NotSame(original.Store, current.Store);
            Assert.NotSame(authority, current.Authority);
            Assert.NotEqual(identity, current.Identity);
            Assert.Same(authority, original.Authority);
            Assert.Equal(identity, original.Identity);
            Assert.False(original.Ready);
            Assert.True(current.Ready);
            Assert.Equal(ArtifactDurability.SimulationOnly, current.Store.Capabilities.Durability);
            Assert.Equal(ArtifactFailureCode.Unavailable, Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
                await authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
                    identity, receipt.Stamp.Identity.Digest), new(), default)).Code);
            await ArtifactCompositionAssertions.FreshEpochAsync(current.Store, current.Identity, receipt, default);
            Assert.Equal(2, Directory.GetDirectories(Assert.Single(resources.Directories).DirectoryPath).Length);
            Assert.Empty(resources.Settlements);
            await original.DisposeAsync();
            Assert.True(current.Ready);
            await ArtifactPublicationAssertions.UnknownLengthAndRealEofAsync(current.Store, default);
        }
        finally
        {
            await guard.DisposeAsync();
            await current.DisposeAsync();
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.Equal(ConformanceOwnershipState.Settling, (await current.ObserveCleanupAsync(default)).State);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Released_callback_stays_owned_until_restart_or_final_settlement(bool restart)
    {
        await using var resources = new RecordingDirectories();
        var original = await ObjectArtifactAssertionSessions.CreateAsync(Context(resources), default);
        var current = original;
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var registration = await original.ObserveBoundaryAsync(ArtifactObservationPoint.OperationReleased,
            () => { entered.TrySetResult(); return new(release.Task); }, default);
        var reserving = original.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default).AsTask();
        Task<IArtifactAssertionSession>? reopening = null;
        Task? disposing = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.False(original.AwaitSettlementAsync(default).IsCompleted);
            if (restart) { reopening = original.ReopenAsync(default).AsTask(); }
            else
            {
                disposing = original.DisposeAsync().AsTask();
                await resources.Observing.Task.WaitAsync(TimeSpan.FromSeconds(5));
                Assert.False(Assert.Single(resources.Settlements).Value.IsCompleted);
            }
            Assert.False(reopening is { IsCompleted: true } || disposing is { IsCompleted: true });
        }
        finally
        {
            release.TrySetResult();
            await reserving;
            if (reopening is not null) { current = await reopening; }
            if (disposing is not null) { await disposing; }
            await current.DisposeAsync();
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
    }

    [Fact]
    public async Task Failed_replacement_keeps_the_original_as_cleanup_handle()
    {
        await using var resources = new RecordingDirectories();
        var original = await ObjectArtifactAssertionSessions.CreateAsync(Context(resources), default);
        var root = Assert.Single(resources.Directories).DirectoryPath;
        var moved = root + "-held";
        try
        {
            Directory.Move(root, moved);
            File.WriteAllText(root, "not a directory");
            Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(
                () => original.ReopenAsync(default).AsTask())).Message);
            Assert.False(original.Ready);
            Assert.Empty(resources.Settlements);
        }
        finally
        {
            File.Delete(root);
            Directory.Move(moved, root);
            await original.DisposeAsync();
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
    }

    [Fact]
    public async Task Failed_initialization_joins_actual_shutdown_without_erasing_foreign_content()
    {
        await using var resources = new RecordingDirectories(beforeAdmission: path =>
            File.WriteAllText(Path.Combine(RecordingDirectories.CreatePrivateDirectory(Path.Combine(path, "store")), "foreign"),
                "not an empty artifact root"));
        Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(() =>
            ObjectArtifactAssertionSessions.CreateAsync(Context(resources), default).AsTask())).Message);
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.True(File.Exists(Path.Combine(Assert.Single(resources.Directories).DirectoryPath, "store", "foreign")));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Observer_failure_before_or_during_cleanup_faults_the_same_actual_settlement(bool duringCleanup)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var session = await ObjectArtifactAssertionSessions.CreateAsync(Context(resources), default);
        var failure = new InvalidOperationException("controlled-observer-failure");
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var registration = await session.ObserveBoundaryAsync(
            ArtifactObservationPoint.OperationReleased, async () =>
            {
                entered.TrySetResult();
                await release.Task;
                throw failure;
            }, default);
        var reserving = session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default).AsTask();
        Task? disposing = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            if (duringCleanup)
            {
                disposing = session.DisposeAsync().AsTask();
                await resources.Observing.Task.WaitAsync(TimeSpan.FromSeconds(5));
                Assert.False(disposing.IsCompleted);
                Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                    await reserving.WaitAsync(TimeSpan.FromSeconds(5)));
            }
        }
        finally { release.TrySetResult(); }
        if (!duringCleanup) { Assert.Same(failure, await Record.ExceptionAsync(() => reserving)); }
        if (disposing is not null) { await Assert.ThrowsAsync<InvalidOperationException>(() => disposing); }
        await Assert.ThrowsAsync<InvalidOperationException>(() => session.DisposeAsync().AsTask());
        var actual = Assert.Single(resources.Settlements).Value;
        Assert.True(actual.IsFaulted);
        Assert.Contains(failure, actual.Exception!.InnerExceptions);
        await Assert.ThrowsAsync<InvalidOperationException>(() => session.DisposeAsync().AsTask());
        Assert.Same(actual, Assert.Single(resources.Settlements).Value);
    }

    [Fact]
    public async Task Retained_authority_and_concurrent_disposers_retry_the_same_settlement()
    {
        await using var resources = new RecordingDirectories(TimeSpan.FromMilliseconds(20));
        var session = await ObjectArtifactAssertionSessions.CreateAsync(Context(resources), default);
        var guard = Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Success>(
            await session.Authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
                session.Identity, new ArtifactDigest(new string('a', 64))), new(), default)).Value;
        var first = session.DisposeAsync().AsTask();
        var second = session.DisposeAsync().AsTask();
        try
        {
            Assert.Same(first, second);
            await resources.Retained.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.False(first.IsCompleted);
            Assert.False(Assert.Single(resources.Settlements).Value.IsCompleted);
        }
        finally { await guard.DisposeAsync(); }
        Assert.Equal("CleanupIncomplete", (await Assert.ThrowsAsync<InvalidOperationException>(() => first)).Message);
        await session.DisposeAsync();
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.Equal(ConformanceOwnershipState.Settling, (await session.ObserveCleanupAsync(default)).State);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Fact]
    public async Task Cancellation_while_joining_old_authority_does_not_admit_a_replacement()
    {
        await using var resources = new RecordingDirectories();
        var original = await ObjectArtifactAssertionSessions.CreateAsync(Context(resources), default);
        var guard = Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Success>(
            await original.Authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
                original.Identity, new ArtifactDigest(new string('a', 64))), new(), default)).Value;
        using var cancellation = new CancellationTokenSource();
        try
        {
            var restarting = original.ReopenAsync(cancellation.Token).AsTask();
            cancellation.Cancel();
            Assert.False(restarting.IsCompleted);
            await guard.DisposeAsync();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() => restarting);
            Assert.False(original.Ready);
            Assert.Single(Directory.GetDirectories(Assert.Single(resources.Directories).DirectoryPath));
            Assert.Empty(resources.Settlements);
        }
        finally
        {
            await guard.DisposeAsync();
            await original.DisposeAsync();
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Direct_stop_and_disposal_retries_reuse_the_pending_allocator_observation(bool actualAllocator)
    {
        await using var resources = new RecordingDirectories(useActualAllocator: actualAllocator);
        var session = await ObjectArtifactAssertionSessions.CreateAsync(Context(resources), default);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var registration = await session.ObserveBoundaryAsync(ArtifactObservationPoint.OperationReleased,
            () => { entered.TrySetResult(); return new(release.Task); }, default);
        var reserving = session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default).AsTask();
        Task<ArtifactResult<ArtifactShutdown>>? direct = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            direct = session.Lifetime.StopAsync(new(TimeSpan.FromSeconds(5)), default).AsTask();
            Assert.False(direct.IsCompleted);
            Assert.Equal("CleanupIncomplete", (await Assert.ThrowsAsync<InvalidOperationException>(
                () => session.DisposeAsync().AsTask())).Message);
            Assert.Equal("CleanupIncomplete", (await Assert.ThrowsAsync<InvalidOperationException>(
                () => session.DisposeAsync().AsTask())).Message);
            Assert.Equal(1, resources.ReleaseCalls);
            Assert.False(Assert.Single(resources.Settlements).Value.IsCompleted);
        }
        finally
        {
            release.TrySetResult();
            await reserving;
            if (direct is not null) { Assert.IsType<ArtifactResult<ArtifactShutdown>.Success>(await direct); }
            await session.DisposeAsync();
        }
        Assert.Single(resources.Observations);
    }

    [Fact]
    public async Task Cancellation_during_replacement_admission_retains_the_unpublished_generation()
    {
        await using var resources = new RecordingDirectories();
        var clock = new AdmissionClock();
        var context = new ConformanceRunContext(Guid.NewGuid(), "arbitrary-not-a-setup-selector",
            clock, resources, new ConformanceEvidenceBuffer());
        var original = await ObjectArtifactAssertionSessions.CreateAsync(context, default);
        var identity = original.Identity;
        var authority = original.Authority;
        var root = Assert.Single(resources.Directories).DirectoryPath;
        using var cancellation = new CancellationTokenSource();
        clock.OnUtcNow = () =>
        {
            if (Directory.GetDirectories(root).Length == 2) { cancellation.Cancel(); }
        };
        try
        {
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() => original.ReopenAsync(cancellation.Token).AsTask());
            Assert.True(cancellation.IsCancellationRequested);
            Assert.Equal(2, Directory.GetDirectories(root).Length);
            Assert.False(original.Ready);
            Assert.Equal(identity, original.Identity);
            Assert.Same(authority, original.Authority);
            Assert.Empty(resources.Settlements);
        }
        finally
        {
            clock.OnUtcNow = null;
            await original.DisposeAsync();
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
    }

    private sealed class AdmissionClock : TimeProvider
    {
        public Action? OnUtcNow { get; set; }
        public override DateTimeOffset GetUtcNow()
        {
            OnUtcNow?.Invoke();
            return TimeProvider.System.GetUtcNow();
        }
    }

    private static ConformanceRunContext Context(RecordingDirectories resources) => new(
        Guid.NewGuid(), "arbitrary-not-a-setup-selector", TimeProvider.System, resources, new ConformanceEvidenceBuffer());
}
