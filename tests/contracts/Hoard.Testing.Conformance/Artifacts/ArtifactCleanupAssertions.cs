using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public sealed class ArtifactCleanupAssertions
{
    private readonly IArtifactStore store;
    private readonly IArtifactMaintenance maintenance;
    private readonly ArtifactStoreIdentity identity;
    private readonly Func<bool> ready;
    private readonly Func<CancellationToken, ValueTask<string[]>> stagingFiles;

    public ArtifactCleanupAssertions(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Func<bool> ready, Func<string[]> stagingFiles) :
        this(store, maintenance, identity, ready, _ => ValueTask.FromResult(stagingFiles()))
    { }

    public ArtifactCleanupAssertions(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Func<bool> ready, Func<CancellationToken, ValueTask<string[]>> stagingFiles)
    {
        this.store = store;
        this.maintenance = maintenance;
        this.identity = identity;
        this.ready = ready;
        this.stagingFiles = stagingFiles;
    }

    public Task ReusedObjectAsync(
        Func<string[]> objectFiles, Action observeReadOnlyObjects, Action removeObserver,
        Action restoreObjects, CancellationToken cancellationToken) =>
        ReusedObjectAsync(_ => ValueTask.FromResult(objectFiles()),
            () => { observeReadOnlyObjects(); return ValueTask.CompletedTask; },
            () => { removeObserver(); return ValueTask.CompletedTask; },
            () => { restoreObjects(); return ValueTask.CompletedTask; }, cancellationToken);

    public async Task ReusedObjectAsync(
        Func<CancellationToken, ValueTask<string[]>> objectFiles,
        Func<ValueTask> observeReadOnlyObjects, Func<ValueTask> removeObserver,
        Func<ValueTask> restoreObjects, CancellationToken cancellationToken)
    {
        var bytes = "reused selected object stays immutable"u8.ToArray();
        using var control = new ShortSource(bytes);
        var committed = await PublishAsync(store, control, new(1024), cancellationToken);
        var selected = Assert.Single(await objectFiles(cancellationToken));
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource(bytes);
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        await observeReadOnlyObjects();
        try
        {
            var failed = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await store.CommitAsync(staged, new(), cancellationToken));
            Assert.Equal(ArtifactFailureCode.Uncertain, failed.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.False(ready());
            await removeObserver();
            var receipt = Assert.IsType<ArtifactResolution.Committed>(
                Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt;
            Assert.Equal(ArtifactMutationOutcome.AlreadyPresentVerified, receipt.Outcome);
            Assert.Equal(committed.Stamp, receipt.Stamp);
            Assert.Equal(2, (await objectFiles(cancellationToken)).Length);
            var row = Assert.Single(Success(await maintenance.ObserveAsync(
                new(identity, ArtifactRecoveryKind.Staging), new(), cancellationToken)).Observations);
            var owner = Assert.IsType<ArtifactOption<ArtifactStagingOwner>.Some>(row.Owner).Value;
            var request = new ArtifactCleanupRequest(identity, [new ArtifactCleanupTarget.AbandonedStaging(owner)]);
            Assert.Equal(ArtifactFailureCode.AccessDenied, Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(
                await maintenance.CleanupAsync(request, new(), cancellationToken)).Code);
            await restoreObjects();
            var reclaimed = Success(await maintenance.CleanupAsync(request, new(), cancellationToken));
            Assert.Equal(2 * bytes.Length, reclaimed.ReclaimedBytes);
            Assert.Equal(selected, Assert.Single(await objectFiles(cancellationToken)));
            Assert.Empty(await stagingFiles(cancellationToken));
            Assert.True(ready());
            Assert.Equal(receipt, Success(await store.CommitAsync(staged, new(), cancellationToken)));
            Assert.Equal(receipt, Assert.IsType<ArtifactResolution.Committed>(
                Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt);
            Assert.Equal(bytes, await ReadAsync(store, committed.Stamp, cancellationToken));
            Assert.False(source.WasDisposed);
            Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        }
        finally
        {
            await restoreObjects();
            await removeObserver();
        }
    }

    public Task UnselectedObjectAsync(
        bool duringAssembly, Func<string[]> objectFiles, Func<string, long> objectLength, Func<Task> whenIdle,
        Action<CancellationTokenSource> observeFailure, Action removeObserver, Action restoreObjects,
        Action cleanupFinally, CancellationToken cancellationToken) =>
        UnselectedObjectAsync(duringAssembly, _ => ValueTask.FromResult(objectFiles()),
            (id, _) => ValueTask.FromResult(objectLength(id)), whenIdle,
            cancellation => { observeFailure(cancellation); return ValueTask.CompletedTask; },
            () => { removeObserver(); return ValueTask.CompletedTask; },
            () => { restoreObjects(); return ValueTask.CompletedTask; },
            () => { cleanupFinally(); return ValueTask.CompletedTask; }, cancellationToken);

    public async Task UnselectedObjectAsync(
        bool duringAssembly, Func<CancellationToken, ValueTask<string[]>> objectFiles,
        Func<string, CancellationToken, ValueTask<long>> objectLength, Func<Task> whenIdle,
        Func<CancellationTokenSource, ValueTask> observeFailure, Func<ValueTask> removeObserver,
        Func<ValueTask> restoreObjects, Func<ValueTask> cleanupFinally, CancellationToken cancellationToken)
    {
        const int length = 512 * 1024;
        using var control = new ShortSource("selected payload must survive scratch cleanup"u8.ToArray());
        var committed = await PublishAsync(store, control, new(length), cancellationToken);
        var selected = Assert.Single(await objectFiles(cancellationToken));
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(length)), new(), cancellationToken));
        using var source = new ShortSource(new byte[length]);
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        using var cancellation = new CancellationTokenSource();
        await observeFailure(cancellation);
        try
        {
            var failed = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await store.CommitAsync(staged, new(), cancellation.Token));
            await whenIdle();
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.False(ready());
            Assert.False(source.WasDisposed);
            var residual = Assert.Single(await objectFiles(cancellationToken), path => path != selected);
            var residualBytes = await objectLength(residual, cancellationToken);
            Assert.InRange(residualBytes, 1, length);
            if (duringAssembly) { Assert.True(residualBytes < length); }
            else { Assert.Equal(length, residualBytes); }
            for (var attempt = 0; attempt < 3; attempt++)
            {
                Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                    await store.CommitAsync(staged, new(), cancellationToken)).Code);
                Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                    await store.ReserveWriteAsync(new(new ArtifactExpectations(length)), new(), cancellationToken)).Code);
                Assert.Equal(2, (await objectFiles(cancellationToken)).Length);
            }
            var page = Success(await maintenance.ObserveAsync(
                new(identity, ArtifactRecoveryKind.Staging), new(), cancellationToken));
            var row = Assert.Single(page.Observations);
            Assert.Equal(ArtifactObservationKind.AbandonedStaging, row.Kind);
            var owner = Assert.IsType<ArtifactOption<ArtifactStagingOwner>.Some>(row.Owner).Value;
            Assert.Equal(staged.Owner, owner);
            var request = new ArtifactCleanupRequest(identity, [new ArtifactCleanupTarget.AbandonedStaging(owner)]);
            for (var attempt = 0; attempt < 2; attempt++)
            {
                var retry = Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(
                    await maintenance.CleanupAsync(request, new(), cancellationToken));
                Assert.Equal(ArtifactFailureCode.AccessDenied, retry.Code);
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, retry.Cleanup);
            }
            await restoreObjects();
            await removeObserver();
            var reclaimed = Success(await maintenance.CleanupAsync(request, new(), cancellationToken));
            Assert.Equal(1, reclaimed.Completed);
            Assert.Equal(length + residualBytes, reclaimed.ReclaimedBytes);
            Assert.Equal(selected, Assert.Single(await objectFiles(cancellationToken)));
            Assert.Empty(await stagingFiles(cancellationToken));
            Assert.True(ready());
            Assert.IsType<ArtifactResolution.NotCommitted>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
            Assert.Equal("selected payload must survive scratch cleanup"u8.ToArray(), await ReadAsync(store, committed.Stamp, cancellationToken));
            using var replacement = new ShortSource("fresh selected object after cleanup"u8.ToArray());
            var fresh = await PublishAsync(store, replacement, new(length), cancellationToken);
            Assert.Equal(1, Success(await maintenance.CleanupAsync(request, new(), cancellationToken)).Conflicted);
            Assert.Equal("fresh selected object after cleanup"u8.ToArray(), await ReadAsync(store, fresh.Stamp, cancellationToken));
        }
        finally { await cleanupFinally(); }
    }

    public Task CommittedResidualAsync(
        Action blockPrefixCleanup, Action restorePrefixCleanup, CancellationToken cancellationToken) =>
        CommittedResidualAsync(() => { blockPrefixCleanup(); return ValueTask.CompletedTask; },
            () => { restorePrefixCleanup(); return ValueTask.CompletedTask; }, cancellationToken);

    public async Task CommittedResidualAsync(
        Func<ValueTask> blockPrefixCleanup, Func<ValueTask> restorePrefixCleanup, CancellationToken cancellationToken)
    {
        using var original = new ShortSource("committed bytes survive residual cleanup"u8.ToArray());
        var committed = await PublishAsync(store, original, new(1024), cancellationToken);
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var duplicate = new ShortSource("committed bytes survive residual cleanup"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, duplicate, new(), cancellationToken));
        await blockPrefixCleanup();
        try
        {
            var failed = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await store.CommitAsync(staged, new(), cancellationToken));
            Assert.Equal(ArtifactFailureCode.Uncertain, failed.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.False(ready());
            var receipt = Assert.IsType<ArtifactResolution.Committed>(
                Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt;
            Assert.Equal(committed.Stamp, receipt.Stamp);
            var page = Success(await maintenance.ObserveAsync(
                new(identity, ArtifactRecoveryKind.Staging), new(), cancellationToken));
            var row = Assert.Single(page.Observations);
            Assert.Equal(ArtifactObservationKind.AbandonedStaging, row.Kind);
            var owner = Assert.IsType<ArtifactOption<ArtifactStagingOwner>.Some>(row.Owner).Value;
            var request = new ArtifactCleanupRequest(identity, [new ArtifactCleanupTarget.AbandonedStaging(owner)]);
            Assert.Equal(ArtifactFailureCode.AccessDenied, Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(
                await maintenance.CleanupAsync(request, new(), cancellationToken)).Code);
            await restorePrefixCleanup();
            Assert.Equal(1, Success(await maintenance.CleanupAsync(request, new(), cancellationToken)).Completed);
            Assert.True(ready());
            Assert.Empty(await stagingFiles(cancellationToken));
            Assert.Equal(receipt, Success(await store.CommitAsync(staged, new(), cancellationToken)));
            Assert.Equal(receipt, Assert.IsType<ArtifactResolution.Committed>(
                Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt);
            Assert.Equal("committed bytes survive residual cleanup"u8.ToArray(), await ReadAsync(store, receipt.Stamp, cancellationToken));
            Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
            Assert.False(duplicate.WasDisposed);
        }
        finally { await restorePrefixCleanup(); }
    }

    public Task FailedPrefixAsync(
        Action denyPrefixCleanup, Action restorePrefixCleanup, CancellationToken cancellationToken) =>
        FailedPrefixAsync(() => { denyPrefixCleanup(); return ValueTask.CompletedTask; },
            () => { restorePrefixCleanup(); return ValueTask.CompletedTask; }, cancellationToken);

    public async Task FailedPrefixAsync(
        Func<ValueTask> denyPrefixCleanup, Func<ValueTask> restorePrefixCleanup, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("unreclaimed failed prefix"u8.ToArray());
        await denyPrefixCleanup();
        try
        {
            var failed = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await store.StageAsync(ticket, source, new(), cancellationToken));
            Assert.Equal(ArtifactFailureCode.AccessDenied, failed.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.False(ready());
            Assert.False(source.WasDisposed);
            Assert.True(source.BytesRead > 0);
            Assert.Single(await stagingFiles(cancellationToken));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken)).Code);
            var page = Success(await maintenance.ObserveAsync(
                new(identity, ArtifactRecoveryKind.Staging), new(), cancellationToken));
            var row = Assert.Single(page.Observations);
            Assert.Equal(ArtifactObservationKind.AbandonedStaging, row.Kind);
            var owner = Assert.IsType<ArtifactOption<ArtifactStagingOwner>.Some>(row.Owner).Value;
            var request = new ArtifactCleanupRequest(identity, [new ArtifactCleanupTarget.AbandonedStaging(owner)]);
            for (var attempt = 0; attempt < 2; attempt++)
            {
                var retry = Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(
                    await maintenance.CleanupAsync(request, new(), cancellationToken));
                Assert.Equal(ArtifactFailureCode.AccessDenied, retry.Code);
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, retry.Cleanup);
                Assert.False(ready());
            }
            await restorePrefixCleanup();
            var reclaimed = Success(await maintenance.CleanupAsync(request, new(), cancellationToken));
            Assert.Equal(1, reclaimed.Completed);
            Assert.True(reclaimed.ReclaimedBytes > 0);
            Assert.Empty(await stagingFiles(cancellationToken));
            Assert.True(ready());
            Assert.IsType<ArtifactResolution.NotCommitted>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
            using var replay = new ShortSource([1]);
            Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await store.StageAsync(ticket, replay, new(), cancellationToken));
            Assert.Equal(0, replay.BytesRead);
            var fresh = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
            using var replacement = new ShortSource("fresh owner after reclamation"u8.ToArray());
            var staged = Success(await store.StageAsync(fresh, replacement, new(), cancellationToken));
            Assert.Equal(1, Success(await maintenance.CleanupAsync(request, new(), cancellationToken)).Conflicted);
            Assert.IsType<ArtifactResult<ArtifactStagingOwner>.Failure>(await store.RenewAsync(owner, new(), cancellationToken));
            Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(await store.AbandonAsync(owner, new(), cancellationToken));
            var receipt = Success(await store.CommitAsync(staged, new(), cancellationToken));
            Assert.Equal("fresh owner after reclamation"u8.ToArray(), await ReadAsync(store, receipt.Stamp, cancellationToken));
        }
        finally { await restorePrefixCleanup(); }
    }

    public Task FailedPrefixStopAsync(
        ArtifactOperationTicket ticket, ShortSource source,
        Func<ArtifactCleanupOptions, ValueTask<ArtifactResult<ArtifactShutdown>>> stop,
        Action restorePrefixCleanup, CancellationToken cancellationToken) =>
        FailedPrefixStopAsync(ticket, source, stop,
            () => { restorePrefixCleanup(); return ValueTask.CompletedTask; }, cancellationToken);

    public async Task FailedPrefixStopAsync(
        ArtifactOperationTicket ticket, ShortSource source,
        Func<ArtifactCleanupOptions, ValueTask<ArtifactResult<ArtifactShutdown>>> stop,
        Func<ValueTask> restorePrefixCleanup, CancellationToken cancellationToken)
    {
        try
        {
            Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await store.StageAsync(ticket, source, new(), cancellationToken));
            for (var attempt = 0; attempt < 2; attempt++)
            {
                var failed = Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(await stop(new()));
                Assert.Equal(ArtifactFailureCode.CleanupIncomplete, failed.Code);
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
                Assert.Single(await stagingFiles(cancellationToken));
                Assert.False(source.WasDisposed);
            }
        }
        finally { await restorePrefixCleanup(); }
        Assert.Equal(ArtifactCleanupState.Released, Success(await stop(new())).State);
        Assert.Empty(await stagingFiles(cancellationToken));
    }

    public static async Task ReopenedAfterPrefixStopAsync(
        IArtifactStore reopened, Func<bool> reopenedReady, ArtifactOperationTicket ticket, CancellationToken cancellationToken)
    {
        Assert.True(reopenedReady());
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await reopened.ReconcileAsync(ticket, new(), cancellationToken)));
        Success(await reopened.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var replay = new ShortSource([1]);
        Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await reopened.StageAsync(ticket, replay, new(), cancellationToken));
        Assert.Equal(0, replay.BytesRead);
    }
}
