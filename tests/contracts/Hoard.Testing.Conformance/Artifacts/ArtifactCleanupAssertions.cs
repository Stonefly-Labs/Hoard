using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public sealed class ArtifactCleanupAssertions(
    IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
    Func<bool> ready, Func<string[]> stagingFiles)
{
    public async Task CommittedResidualAsync(
        Action blockPrefixCleanup, Action restorePrefixCleanup, CancellationToken cancellationToken)
    {
        using var original = new ShortSource("committed bytes survive residual cleanup"u8.ToArray());
        var committed = await PublishAsync(store, original, new(1024), cancellationToken);
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var duplicate = new ShortSource("committed bytes survive residual cleanup"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, duplicate, new(), cancellationToken));
        blockPrefixCleanup();
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
            restorePrefixCleanup();
            Assert.Equal(1, Success(await maintenance.CleanupAsync(request, new(), cancellationToken)).Completed);
            Assert.True(ready());
            Assert.Empty(stagingFiles());
            Assert.Equal(receipt, Success(await store.CommitAsync(staged, new(), cancellationToken)));
            Assert.Equal(receipt, Assert.IsType<ArtifactResolution.Committed>(
                Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt);
            Assert.Equal("committed bytes survive residual cleanup"u8.ToArray(), await ReadAsync(store, receipt.Stamp, cancellationToken));
            Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
            Assert.False(duplicate.WasDisposed);
        }
        finally { restorePrefixCleanup(); }
    }

    public async Task FailedPrefixAsync(
        Action denyPrefixCleanup, Action restorePrefixCleanup, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("unreclaimed failed prefix"u8.ToArray());
        denyPrefixCleanup();
        try
        {
            var failed = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await store.StageAsync(ticket, source, new(), cancellationToken));
            Assert.Equal(ArtifactFailureCode.AccessDenied, failed.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.False(ready());
            Assert.False(source.WasDisposed);
            Assert.True(source.BytesRead > 0);
            Assert.Single(stagingFiles());
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
            restorePrefixCleanup();
            var reclaimed = Success(await maintenance.CleanupAsync(request, new(), cancellationToken));
            Assert.Equal(1, reclaimed.Completed);
            Assert.True(reclaimed.ReclaimedBytes > 0);
            Assert.Empty(stagingFiles());
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
        finally { restorePrefixCleanup(); }
    }

    public async Task FailedPrefixStopAsync(
        ArtifactOperationTicket ticket, ShortSource source,
        Func<ArtifactCleanupOptions, ValueTask<ArtifactResult<ArtifactShutdown>>> stop,
        Action restorePrefixCleanup, CancellationToken cancellationToken)
    {
        try
        {
            Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await store.StageAsync(ticket, source, new(), cancellationToken));
            for (var attempt = 0; attempt < 2; attempt++)
            {
                var failed = Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(await stop(new()));
                Assert.Equal(ArtifactFailureCode.CleanupIncomplete, failed.Code);
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
                Assert.Single(stagingFiles());
                Assert.False(source.WasDisposed);
            }
        }
        finally { restorePrefixCleanup(); }
        Assert.Equal(ArtifactCleanupState.Released, Success(await stop(new())).State);
        Assert.Empty(stagingFiles());
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
