using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactRecoveryAssertions
{
    public static async Task SequentialRecoveryAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Action<TimeSpan> advanceClock, ArtifactEnumerationConsistency expectedConsistency,
        CancellationToken cancellationToken)
    {
        for (var number = 0; number < 35; number++)
        {
            using var source = new ShortSource([(byte)number]);
            await PublishAsync(store, source, new(1024), cancellationToken);
        }
        var query = new ArtifactRecoveryQuery(identity, ArtifactRecoveryKind.Committed, 1);
        var pages = new ArtifactRecoveryPage[32];
        var seen = Enumerable.Range(0, 32).Select(_ => new HashSet<Guid>()).ToArray();
        for (var scan = 0; scan < pages.Length; scan++)
        {
            pages[scan] = Success(await maintenance.ObserveAsync(query, new(), cancellationToken));
            Assert.True(seen[scan].Add(Assert.Single(pages[scan].Observations).OperationId));
        }
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactRecoveryPage>.Failure>(
            await maintenance.ObserveAsync(query, new(), cancellationToken)).Code);
        var old = Assert.IsType<ArtifactOption<string>.Some>(pages[0].Continuation);
        Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactRecoveryPage>.Failure>(
            await maintenance.ObserveAsync(new(identity, ArtifactRecoveryKind.All, 1, old), new(), cancellationToken)).Code);
        Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactRecoveryPage>.Failure>(
            await maintenance.ObserveAsync(new(identity, ArtifactRecoveryKind.Committed, 2, old), new(), cancellationToken)).Code);
        for (var row = 1; row < 35; row++)
        {
            for (var scan = 0; scan < pages.Length; scan++)
            {
                pages[scan] = Success(await maintenance.ObserveAsync(
                    new(identity, ArtifactRecoveryKind.Committed, 1, pages[scan].Continuation), new(), cancellationToken));
                Assert.True(seen[scan].Add(Assert.Single(pages[scan].Observations).OperationId));
                Assert.Equal(expectedConsistency,
                    pages[scan].Consistency);
            }
            if (row == 1)
            {
                Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactRecoveryPage>.Failure>(
                    await maintenance.ObserveAsync(new(identity, ArtifactRecoveryKind.Committed, 1, old), new(), cancellationToken)).Code);
            }
        }
        for (var scan = 0; scan < pages.Length; scan++)
        {
            Assert.Equal(35, seen[scan].Count);
            Assert.IsType<ArtifactOption<string>.None>(pages[scan].Continuation);
            pages[scan] = Success(await maintenance.ObserveAsync(query, new(), cancellationToken));
        }
        advanceClock(TimeSpan.FromSeconds(30));
        Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactRecoveryPage>.Failure>(
            await maintenance.ObserveAsync(new(identity, ArtifactRecoveryKind.Committed, 1,
                pages[0].Continuation), new(), cancellationToken)).Code);
        Success(await maintenance.ObserveAsync(query, new(), cancellationToken));
    }

    public static async Task ChangedInventoryAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        CancellationToken cancellationToken)
    {
        for (var index = 0; index < 3; index++)
        {
            using var source = new ShortSource([(byte)index]);
            await PublishAsync(store, source, new(1024), cancellationToken);
        }
        var query = new ArtifactRecoveryQuery(identity, ArtifactRecoveryKind.Committed, 1);
        var first = Success(await maintenance.ObserveAsync(query, new(), cancellationToken));
        var old = Assert.IsType<ArtifactOption<string>.Some>(first.Continuation);
        using (var added = new ShortSource([3])) { await PublishAsync(store, added, new(1024), cancellationToken); }
        Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactRecoveryPage>.Failure>(
            await maintenance.ObserveAsync(new(identity, ArtifactRecoveryKind.Committed, 1, old),
                new(), cancellationToken)).Code);
        var stamps = new HashSet<ArtifactStamp>();
        ArtifactOption<string> next = new ArtifactOption<string>.None();
        do
        {
            var page = Success(await maintenance.ObserveAsync(
                new(identity, ArtifactRecoveryKind.Committed, 1, next), new(), cancellationToken));
            var row = Assert.Single(page.Observations);
            Assert.True(stamps.Add(Assert.IsType<ArtifactOption<ArtifactStamp>.Some>(row.Stamp).Value));
            next = page.Continuation;
        } while (next is ArtifactOption<string>.Some);
        Assert.Equal(4, stamps.Count);
        foreach (var stamp in stamps) { Assert.Single(await ReadAsync(store, stamp, cancellationToken)); }
    }

    public static async Task OwnerlessExpiryAsync(
        IArtifactStore store, Action<TimeSpan> advanceClock, CancellationToken cancellationToken)
    {
        var expired = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken));
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken)).Code);
        advanceClock(TimeSpan.FromHours(24));
        Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken));
        using var source = new ShortSource([1]);
        Assert.Equal(ArtifactFailureCode.ReconciliationExpired, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await store.StageAsync(expired, source, new(), cancellationToken)).Code);
        Assert.Equal(0, source.BytesRead);
    }

    public static async Task FinalizedNoncommitAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Action<TimeSpan> advanceClock, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("finalized abandonment"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        Success(await store.AbandonAsync(staged.Owner, new(), cancellationToken));
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        advanceClock(TimeSpan.FromSeconds(30));
        Success(await maintenance.CleanupAsync(new(identity,
            [new ArtifactCleanupTarget.AbandonedStaging(staged.Owner)]), new(), cancellationToken));
        using var replacement = new ShortSource("must not be read"u8.ToArray());
        Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await store.StageAsync(ticket, replacement, new(), cancellationToken));
        Assert.Equal(0, replacement.BytesRead);
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
    }

    public static async Task ExpiryGenerationAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Action<TimeSpan> advanceClock, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var first = new ShortSource("old generation"u8.ToArray());
        var old = Success(await store.StageAsync(ticket, first, new(), cancellationToken));
        advanceClock(TimeSpan.FromSeconds(30));
        Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactStagingOwner>.Failure>(
            await store.RenewAsync(old.Owner, new(), cancellationToken)).Code);
        var cleanup = new ArtifactCleanupRequest(identity, [new ArtifactCleanupTarget.AbandonedStaging(old.Owner)]);
        Assert.Equal(1, Success(await maintenance.CleanupAsync(cleanup, new(), cancellationToken)).Completed);
        using var second = new ShortSource("new generation"u8.ToArray());
        var current = Success(await store.StageAsync(ticket, second, new(), cancellationToken));
        Assert.True(current.Owner.Generation > old.Owner.Generation);
        Assert.Equal(1, Success(await maintenance.CleanupAsync(cleanup, new(), cancellationToken)).Conflicted);
        Assert.IsType<ArtifactResult<ArtifactStagingOwner>.Failure>(await store.RenewAsync(old.Owner, new(), cancellationToken));
        Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(await store.AbandonAsync(old.Owner, new(), cancellationToken));
        Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await store.CommitAsync(old, new(), cancellationToken));
        var receipt = Success(await store.CommitAsync(current, new(), cancellationToken));
        Assert.Equal("new generation"u8.ToArray(), await ReadAsync(store, receipt.Stamp, cancellationToken));
    }

    public static async Task RecoveryPagesAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        CancellationToken cancellationToken)
    {
        for (var number = 0; number < 3; number++)
        {
            using var source = new ShortSource([(byte)number]);
            await PublishAsync(store, source, new(1024), cancellationToken);
        }
        var query = new ArtifactRecoveryQuery(identity, ArtifactRecoveryKind.Committed, 1);
        var first = Success(await maintenance.ObserveAsync(query, new(), cancellationToken));
        Assert.Single(first.Observations);
        var continuation = Assert.IsType<ArtifactOption<string>.Some>(first.Continuation);
        var second = Success(await maintenance.ObserveAsync(new(identity,
            ArtifactRecoveryKind.Committed, 1, continuation), new(), cancellationToken));
        Assert.Single(second.Observations);
        Assert.NotEqual(first.Observations[0].OperationId, second.Observations[0].OperationId);
        Assert.IsType<ArtifactResult<ArtifactRecoveryPage>.Failure>(await maintenance.ObserveAsync(
            new(identity, ArtifactRecoveryKind.All, 1, continuation), new(), cancellationToken));
        var stamp = Assert.IsType<ArtifactOption<ArtifactStamp>.Some>(first.Observations[0].Stamp).Value;
        var unauthorizedCleanup = new ArtifactCleanupRequest(identity, [new ArtifactCleanupTarget.RemovedIncarnation(stamp)]);
        Assert.Equal(1, Success(await maintenance.CleanupAsync(unauthorizedCleanup, new(), cancellationToken)).Conflicted);
        Assert.Single(await ReadAsync(store, stamp, cancellationToken));
    }
}
