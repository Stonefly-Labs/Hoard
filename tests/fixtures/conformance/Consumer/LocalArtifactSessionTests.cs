using System.Collections.Concurrent;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Conformance.Bindings.Local;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Evidence;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class LocalArtifactSessionTests
{
    [Fact]
    public async Task Recovery_binding_reopens_exact_owned_state_with_fresh_factory_and_authority()
    {
        await using var resources = new RecordingDirectories(useActualAllocator: true);
        var context = Context(resources);
        IArtifactRecoveryConformanceBinding binding = new LocalBinding(new string('0', 64));
        var original = await ConformanceObservedArtifactSession.OpenAsync(binding, context, default);
        ArtifactMutationReceipt receipt;
        ArtifactStoreIdentity identity;
        IArtifactCoordinationAuthority authority;
        ConformanceSessionOrigin sourceOrigin;
        try
        {
            identity = original.Identity;
            authority = original.Authority;
            sourceOrigin = original.CaptureOrigin();
            receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(original.Store, default);
            Assert.Equal("CleanupIncomplete", Assert.Throws<InvalidOperationException>(() =>
                resources.OpenRecovery(Assert.Single(resources.Directories))).Message);
        }
        finally { await original.DisposeAsync(); }
        var resource = Assert.Single(resources.Directories);
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.Equal("OwnershipInvalid", Assert.Throws<InvalidOperationException>(() =>
            resources.OpenRecovery(new(resource.ResourceId, resource.DirectoryPath))).Message);
        using var recoveryOwner = resources.OpenRecovery(resource);
        Assert.Equal("OwnershipInvalid", Assert.Throws<InvalidOperationException>(() =>
            resources.OpenRecovery(resource)).Message);
        var allocator = new RecoveryDirectories(recoveryOwner);
        var recoveryContext = new ConformanceRunContext(
            context.RunId, context.CaseId, context.Clock, allocator, context.Evidence);
        IArtifactRecoveryConformanceBinding fresh = new LocalBinding(new string('0', 64));
        Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<ArgumentException>(() =>
            ConformanceObservedArtifactRecoverySession.OpenAsync(fresh, recoveryContext,
                new("foreign.provider", identity.InstanceId, identity.Epoch),
                sourceOrigin.SessionId, new string('c', 64), default).AsTask())).Message);
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            ConformanceObservedArtifactRecoverySession.OpenAsync(fresh, recoveryContext, identity,
                sourceOrigin.SessionId, new string('c', 64), new CancellationToken(true)).AsTask());
        await Assert.ThrowsAsync<ArgumentException>(() =>
            ConformanceObservedArtifactRecoverySession.OpenAsync(
                fresh, recoveryContext, identity, Guid.Empty, new string('c', 64), default).AsTask());
        await Assert.ThrowsAsync<ArgumentException>(() =>
            ConformanceObservedArtifactRecoverySession.OpenAsync(
                fresh, recoveryContext, identity, sourceOrigin.SessionId, "invalid", default).AsTask());
        Assert.Equal(0, allocator.Allocations);
        var recovered = await ConformanceObservedArtifactRecoverySession.OpenAsync(
            fresh, recoveryContext, identity, sourceOrigin.SessionId, new string('c', 64), default);
        try
        {
            Assert.Equal(identity, recovered.Identity);
            Assert.NotSame(authority, recovered.Authority);
            Assert.NotSame(original.Store, recovered.Store);
            Assert.True(recovered.Faults.ObserveInitialization().Ready);
            await ArtifactCompositionAssertions.CompatibleReopenAsync(recovered.Store, identity, receipt, default);
            var origin = recovered.CaptureOrigin();
            using var packet = JsonDocument.Parse(ConformanceSessionOriginOutput.Serialize(origin));
            Assert.Equal("artifact-recovery", packet.RootElement.GetProperty("kind").GetString());
            Assert.Equal("recover", packet.RootElement.GetProperty("factoryOperation").GetString());
            Assert.Equal(sourceOrigin.SessionId, packet.RootElement.GetProperty("sourceSessionId").GetGuid());
            Assert.Equal(new string('c', 64), packet.RootElement.GetProperty("recoveryInputSha256").GetString());
            Assert.False(packet.RootElement.TryGetProperty("parentSessionId", out _));
            Assert.NotEqual(sourceOrigin.Components["factory"].InstanceId, origin.Components["factory"].InstanceId);
            Assert.Equal(sourceOrigin.DescriptorSha256, origin.DescriptorSha256);
            await using var liveReopen = await recovered.ReopenAsync(default);
            Assert.IsNotType<ConformanceObservedArtifactSession>(liveReopen);
            await ArtifactCompositionAssertions.CompatibleReopenAsync(liveReopen.Store, identity, receipt, default);
        }
        finally { await recovered.DisposeAsync(); }
        Assert.Equal(1, allocator.Allocations);
        await Assert.ThrowsAsync<InvalidOperationException>(() => allocator.AllocateDirectoryAsync(default).AsTask());
        var settlement = Assert.IsAssignableFrom<Task>(allocator.Settlement);
        Assert.True(settlement.IsCompletedSuccessfully);
        Assert.DoesNotContain(recoveryOwner.ObserveLedger(), item =>
            item.Observation.State is ConformanceOwnershipState.Released or ConformanceOwnershipState.Retained);
        recoveryOwner.Dispose();
        Assert.True(Directory.Exists(resource.DirectoryPath));
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
        using var rejectedOwner = resources.OpenRecovery(resource);
        var rejected = new RecoveryDirectories(rejectedOwner);
        var rejectedContext = new ConformanceRunContext(
            context.RunId, context.CaseId, context.Clock, rejected, context.Evidence);
        Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(() => fresh.ReopenSessionAsync(
            rejectedContext, new(identity.ProviderModuleId, identity.InstanceId, Guid.NewGuid()), default).AsTask())).Message);
        Assert.True(Assert.IsAssignableFrom<Task>(rejected.Settlement).IsCompletedSuccessfully);
    }

    private sealed class RecoveryDirectories(ConformanceResourceAllocator allocator)
        : IConformanceResourceAllocator
    {
        public int Allocations { get; private set; }
        public Task? Settlement { get; private set; }

        public async ValueTask<ConformanceOwnedDirectory> AllocateDirectoryAsync(CancellationToken cancellationToken)
        {
            var resource = await allocator.AllocateDirectoryAsync(cancellationToken);
            Allocations++;
            return resource;
        }

        public ValueTask<ConformanceCleanupObservation> ReleaseAsync(
            ConformanceOwnedDirectory owned, CancellationToken cancellationToken) =>
            throw new InvalidOperationException("Actual settlement required.");

        public async ValueTask<ConformanceCleanupObservation> ReleaseAsync(
            ConformanceOwnedDirectory owned, Task actualSettlement, CancellationToken cancellationToken)
        {
            Assert.Same(actualSettlement, Settlement ??= actualSettlement);
            return await allocator.ReleaseAsync(owned, actualSettlement, cancellationToken);
        }
    }

    [Fact]
    public async Task All_typed_observation_points_can_be_registered_together_and_removed_without_overwrite()
    {
        await using var resources = new RecordingDirectories();
        await using var session = await LocalArtifactAssertionSessions.CreateAsync(Context(resources), default);
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
    }

    [Theory]
    [InlineData("publication")]
    [InlineData("expectations")]
    [InlineData("private-staging")]
    public async Task Owned_local_projection_executes_unchanged_common_consumers(string consumer)
    {
        await using var resources = new RecordingDirectories();
        await using var session = await LocalArtifactAssertionSessions.CreateAsync(Context(resources), default);
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
    public async Task Scoped_observation_cannot_overwrite_a_live_registration_or_remove_its_replacement()
    {
        await using var resources = new RecordingDirectories();
        await using var session = await LocalArtifactAssertionSessions.CreateAsync(Context(resources), default);
        var old = await session.ObserveBoundaryAsync(ArtifactObservationPoint.StageVerified, () => ValueTask.CompletedTask, default);
        await Assert.ThrowsAsync<InvalidOperationException>(() => session.ObserveBoundaryAsync(
            ArtifactObservationPoint.StageVerified, () => ValueTask.CompletedTask, default).AsTask());
        await old.DisposeAsync();
        var arrivals = 0;
        await using var current = await session.ObserveBoundaryAsync(ArtifactObservationPoint.StageVerified,
            () => { Interlocked.Increment(ref arrivals); return ValueTask.CompletedTask; }, default);
        await old.DisposeAsync();
        await ArtifactPublicationAssertions.UnknownLengthAndRealEofAsync(session.Store, default);
        Assert.True(arrivals > 0);
    }

    [Fact]
    public async Task Local_reopen_keeps_identity_authority_content_and_allocation_without_stale_disposal()
    {
        await using var resources = new RecordingDirectories();
        var original = await LocalArtifactAssertionSessions.CreateAsync(Context(resources), default);
        var current = original;
        try
        {
            var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(original.Store, default);
            current = await original.ReopenAsync(default);
            Assert.NotSame(original.Store, current.Store);
            Assert.Same(original.Authority, current.Authority);
            Assert.Equal(original.Identity, current.Identity);
            Assert.False(original.Ready);
            Assert.True(current.Ready);
            Assert.Single(resources.Directories);
            Assert.Empty(resources.Settlements);
            await original.DisposeAsync();
            Assert.True(current.Ready);
            await ArtifactCompositionAssertions.CompatibleReopenAsync(current.Store, current.Identity, receipt, default);
        }
        finally { await current.DisposeAsync(); }
        Assert.All(resources.Settlements.Values, task => Assert.True(task.IsCompletedSuccessfully));
        Assert.Equal(ConformanceOwnershipState.Settling, (await current.ObserveCleanupAsync(default)).State);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Fact]
    public async Task Physical_store_stop_cannot_release_a_live_authority_guard_or_erase_retained_observation()
    {
        await using var resources = new RecordingDirectories(TimeSpan.FromMilliseconds(20));
        var session = await LocalArtifactAssertionSessions.CreateAsync(Context(resources), default);
        await using var guard = Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Success>(
            await session.Authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
                session.Identity, new ArtifactDigest(new string('a', 64))), new(), default)).Value;
        var disposing = session.DisposeAsync().AsTask();
        try
        {
            await resources.Retained.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.False(disposing.IsCompleted);
            Assert.False(Assert.Single(resources.Settlements).Value.IsCompleted);
            Assert.Equal(ConformanceOwnershipState.Retained, (await session.ObserveCleanupAsync(default)).State);
            Assert.Equal(ArtifactFailureCode.Unavailable, Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
                await session.Authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
                    session.Identity, new ArtifactDigest(new string('b', 64))), new(), default)).Code);
        }
        finally { await guard.DisposeAsync(); }
        Assert.Equal("CleanupIncomplete", (await Assert.ThrowsAsync<InvalidOperationException>(() => disposing)).Message);
        await session.DisposeAsync();
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.Equal(ConformanceOwnershipState.Settling, (await session.ObserveCleanupAsync(default)).State);
        Assert.Contains(resources.Observations, item => item.State == ConformanceOwnershipState.Retained);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Fact]
    public async Task Concurrent_disposers_join_one_attempt_and_the_same_actual_settlement()
    {
        await using var resources = new RecordingDirectories();
        var session = await LocalArtifactAssertionSessions.CreateAsync(Context(resources), default);
        await using var guard = Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Success>(
            await session.Authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
                session.Identity, new ArtifactDigest(new string('a', 64))), new(), default)).Value;
        var first = session.DisposeAsync().AsTask();
        var second = session.DisposeAsync().AsTask();
        try
        {
            Assert.Same(first, second);
            await resources.Observing.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.False(first.IsCompleted);
            Assert.False(Assert.Single(resources.Settlements).Value.IsCompleted);
        }
        finally { await guard.DisposeAsync(); }
        await Task.WhenAll(first, second);
        await session.DisposeAsync();
        Assert.Single(resources.Observations);
    }

    [Fact]
    public async Task Failed_initialization_retains_allocator_ownership_and_joins_actual_shutdown()
    {
        await using var resources = new RecordingDirectories(beforeAdmission: path =>
            File.WriteAllText(Path.Combine(RecordingDirectories.CreatePrivateDirectory(Path.Combine(path, "store")), "foreign"),
                "not an empty artifact root"));
        Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(() =>
            LocalArtifactAssertionSessions.CreateAsync(Context(resources), default).AsTask())).Message);
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.True(File.Exists(Path.Combine(Assert.Single(resources.Directories).DirectoryPath, "store", "foreign")));
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Released_boundary_stays_owned_through_actual_callback_and_reopen_or_disposal(bool reopen)
    {
        await using var resources = new RecordingDirectories();
        var original = await LocalArtifactAssertionSessions.CreateAsync(Context(resources), default);
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
            var actual = original.AwaitSettlementAsync(default).AsTask();
            Assert.False(actual.IsCompleted);
            if (reopen) { reopening = original.ReopenAsync(default).AsTask(); }
            else
            {
                disposing = original.DisposeAsync().AsTask();
                await resources.Observing.Task.WaitAsync(TimeSpan.FromSeconds(5));
                Assert.False(Assert.Single(resources.Settlements).Value.IsCompleted);
            }
            Assert.False(reopening is { IsCompleted: true } || disposing is { IsCompleted: true });
            release.TrySetResult();
            await actual;
            if (reopening is not null) { current = await reopening; }
            if (disposing is not null) { await disposing; }
        }
        finally
        {
            release.TrySetResult();
            await reserving;
            if (reopening is not null) { current = await reopening; }
            if (disposing is not null) { await disposing; }
            await current.DisposeAsync();
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Observer_failure_before_or_during_cleanup_remains_in_the_same_actual_settlement(bool duringCleanup)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var session = await LocalArtifactAssertionSessions.CreateAsync(Context(resources), default);
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
        Assert.All(resources.Observations, observation =>
        {
            Assert.Equal(ConformanceOwnershipState.Retained, observation.State);
            Assert.Equal(ConformanceDiagnosticCode.UnknownDiagnostic, observation.Reason);
        });
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Concurrent_direct_stop_and_disposal_retry_reuse_the_pending_allocator_observation(bool actualAllocator)
    {
        await using var resources = new RecordingDirectories(useActualAllocator: actualAllocator);
        var session = await LocalArtifactAssertionSessions.CreateAsync(Context(resources), default);
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
            if (direct is not null)
            { Assert.IsType<ArtifactResult<ArtifactShutdown>.Success>(await direct); }
            await session.DisposeAsync();
        }
        Assert.Single(resources.Observations);
    }

    private static ConformanceRunContext Context(RecordingDirectories resources) => new(
        Guid.NewGuid(), "arbitrary-not-a-setup-selector", TimeProvider.System, resources, new ConformanceEvidenceBuffer());

    // Records real fixture ownership; optional native allocation is not controller/category-origin proof.
    internal sealed class RecordingDirectories(
        TimeSpan? observationBudget = null, Action<string>? beforeAdmission = null, bool allowFailedSettlement = false,
        bool useActualAllocator = false)
        : IConformanceResourceAllocator, IAsyncDisposable
    {
        public List<ConformanceOwnedDirectory> Directories { get; } = [];
        public ConcurrentDictionary<ConformanceOwnedDirectory, Task> Settlements { get; } = new();
        public ConcurrentQueue<ConformanceCleanupObservation> Observations { get; } = new();
        public TaskCompletionSource Observing { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource Retained { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private int releaseCalls;
        private ConformanceResourceAllocator? allocator;
        private string? allocatorParent;
        public int ReleaseCalls => Volatile.Read(ref releaseCalls);

        internal ConformanceResourceAllocator OpenRecovery(ConformanceOwnedDirectory resource) =>
            (allocator ?? throw new InvalidOperationException("OwnershipInvalid")).OpenRecovery(resource);

        public async ValueTask<ConformanceOwnedDirectory> AllocateDirectoryAsync(CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var id = "local-unit-" + Guid.NewGuid().ToString("N");
            var parent = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Hoard",
                "conformance-local-unit");
            Directory.CreateDirectory(parent);
            ConformanceOwnedDirectory directory;
            if (useActualAllocator)
            {
                allocatorParent = CreatePrivateDirectory(Path.Combine(parent, id));
                allocator = ConformanceResourceAllocator.Open(allocatorParent, Environment.CurrentDirectory);
                directory = await allocator.AllocateDirectoryAsync(cancellationToken);
            }
            else { directory = new(id, CreatePrivateDirectory(Path.Combine(parent, id))); }
            Directories.Add(directory);
            beforeAdmission?.Invoke(directory.DirectoryPath);
            return directory;
        }

        public static string CreatePrivateDirectory(string path)
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("PrerequisiteMissing"); }
            Directory.CreateDirectory(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            return path;
        }

        public ValueTask<ConformanceCleanupObservation> ReleaseAsync(
            ConformanceOwnedDirectory resource, CancellationToken cancellationToken) =>
            throw new InvalidOperationException("Actual settlement required.");

        public async ValueTask<ConformanceCleanupObservation> ReleaseAsync(
            ConformanceOwnedDirectory resource, Task actualSettlement, CancellationToken cancellationToken)
        {
            Interlocked.Increment(ref releaseCalls);
            Assert.Same(actualSettlement, Settlements.GetOrAdd(resource, actualSettlement));
            Observing.TrySetResult();
            ConformanceCleanupObservation observation;
            if (allocator is not null)
            {
                observation = await allocator.ReleaseAsync(resource, actualSettlement, cancellationToken);
            }
            else
            {
                try
                {
                    await actualSettlement.WaitAsync(observationBudget ?? TimeSpan.FromSeconds(5), cancellationToken);
                    observation = new(ConformanceOwnershipState.Settling, [resource.ResourceId]);
                }
                catch (TimeoutException)
                {
                    observation = new(ConformanceOwnershipState.Retained, [resource.ResourceId],
                        ConformanceDiagnosticCode.CleanupIncomplete);
                }
                catch (Exception) when (actualSettlement.IsFaulted)
                {
                    observation = new(ConformanceOwnershipState.Retained, [resource.ResourceId],
                        ConformanceDiagnosticCode.UnknownDiagnostic);
                }
            }
            Observations.Enqueue(observation);
            if (observation.State == ConformanceOwnershipState.Retained) { Retained.TrySetResult(); }
            return observation;
        }

        public ValueTask DisposeAsync()
        {
            Assert.Equal(Directories.Count, Settlements.Count);
            Assert.All(Settlements.Values, task => Assert.True(
                task.IsCompletedSuccessfully || allowFailedSettlement && task.IsFaulted));
            if (allocator is not null)
            {
                Assert.DoesNotContain(allocator.ObserveLedger(), item =>
                    item.Observation.Reason == ConformanceDiagnosticCode.OwnershipInvalid
                    || item.Observation.State == ConformanceOwnershipState.Released);
                allocator.Dispose();
            }
            foreach (var directory in Directories) { Directory.Delete(directory.DirectoryPath, recursive: true); }
            if (allocatorParent is not null) { Directory.Delete(allocatorParent); }
            return ValueTask.CompletedTask;
        }
    }
}
