using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactRecoveryAssertions
{
    public static async Task RetainedObjectStopAsync(
        IArtifactStore store, Func<ArtifactCleanupOptions, ValueTask<ArtifactResult<ArtifactShutdown>>> stop,
        Func<string[]> objectFiles, Func<string[]> stagingFiles, Action observeReadOnlyObjects,
        Action restoreObjects, CancellationToken cancellationToken)
    {
        using var control = new ShortSource("selected control through stop"u8.ToArray());
        await PublishAsync(store, control, new(1024), cancellationToken);
        var selected = Assert.Single(objectFiles());
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("unselected assembly through stop"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        observeReadOnlyObjects();
        try
        {
            Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await store.CommitAsync(staged, new(), cancellationToken));
            for (var attempt = 0; attempt < 2; attempt++)
            {
                var stopped = Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                    await stop(new(TimeSpan.FromSeconds(1))));
                Assert.Equal(ArtifactFailureCode.CleanupIncomplete, stopped.Code);
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, stopped.Cleanup);
                Assert.Equal(2, objectFiles().Length);
                Assert.False(source.WasDisposed);
            }
        }
        finally { restoreObjects(); }
        Assert.Equal(ArtifactCleanupState.Released, Success(await stop(new())).State);
        Assert.Equal(selected, Assert.Single(objectFiles()));
        Assert.Empty(stagingFiles());
    }

    public static Task CommittedDecisionRollbackAsync(
        IArtifactStore original, IArtifactStoreLifetime originalLifetime, ArtifactStoreIdentity identity,
        IArtifactCoordinationAuthority authority, ArtifactLimits limits, Action<long> setUtc,
        Action<TimeSpan> advanceClock, Func<(IArtifactStore Store, IArtifactStoreLifetime Lifetime)> createReopened,
        Action<bool> setCleanupAllowed, Func<bool> cleanupAllowed, CancellationToken cancellationToken) =>
        CommittedDecisionRollbackAsync(original, originalLifetime, identity, authority, limits, setUtc, advanceClock,
            async token =>
            {
                var reopened = createReopened();
                try
                {
                    Success(await reopened.Lifetime.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible,
                        identity, authority, limits), new(), token));
                    return reopened;
                }
                catch
                {
                    var stopped = await reopened.Lifetime.StopAsync(new(), token);
                    setCleanupAllowed(stopped is ArtifactResult<ArtifactShutdown>.Success);
                    Assert.True(cleanupAllowed());
                    throw;
                }
            }, setCleanupAllowed, cleanupAllowed, cancellationToken);

    public static async Task CommittedDecisionRollbackAsync(
        IArtifactStore original, IArtifactStoreLifetime originalLifetime, ArtifactStoreIdentity identity,
        IArtifactCoordinationAuthority authority, ArtifactLimits limits, Action<long> setUtc,
        Action<TimeSpan> advanceClock,
        Func<CancellationToken, ValueTask<(IArtifactStore Store, IArtifactStoreLifetime Lifetime)>> reopenAsync,
        Action<bool> setCleanupAllowed, Func<bool> cleanupAllowed, CancellationToken cancellationToken)
    {
        Success(await originalLifetime.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, identity, authority, limits), new(), cancellationToken));
        ArtifactOperationTicket ticket;
        ArtifactMutationReceipt receipt;
        try
        {
            for (var index = 0; index < 105; index++)
            {
                var historical = Success(await original.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
                using var input = new ShortSource("repeated retired incarnation"u8.ToArray());
                var prepared = Success(await original.StageAsync(historical, input, new(), cancellationToken));
                var incarnation = Success(await original.CommitAsync(prepared, new(), cancellationToken));
                setUtc(historical.Expires.ToUnixTimeMilliseconds());
                var deletion = Success(await original.ReserveDeleteAsync(new(incarnation.Stamp), new(), cancellationToken));
                Success(await original.DeleteAsync(deletion, new(), cancellationToken));
                setUtc(deletion.Expires.ToUnixTimeMilliseconds());
            }
            ticket = Success(await original.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
            using var source = new ShortSource("persisted beyond ticket retention"u8.ToArray());
            var staged = Success(await original.StageAsync(ticket, source, new(), cancellationToken));
            receipt = Success(await original.CommitAsync(staged, new(), cancellationToken));
            advanceClock(TimeSpan.FromHours(24));
            Success(await original.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        }
        finally { Success(await originalLifetime.StopAsync(new(), cancellationToken)); }
        setUtc(ticket.Issued.ToUnixTimeMilliseconds());
        var (reopened, reopenedLifetime) = await reopenAsync(cancellationToken);
        try
        {
            Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(await reopened.ReconcileAsync(ticket, new(), cancellationToken));
            await using var read = Success(await reopened.OpenReadAsync(new(receipt.Stamp.Identity.Digest,
                expectedStamp: new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), cancellationToken));
            using var destination = new MemoryStream();
            Success(await read.CopyToAsync(destination, new(), cancellationToken));
            Assert.Equal("persisted beyond ticket retention"u8.ToArray(), destination.ToArray());
        }
        finally
        {
            var stopped = await reopenedLifetime.StopAsync(new(), cancellationToken);
            setCleanupAllowed(stopped is ArtifactResult<ArtifactShutdown>.Success);
            Assert.True(cleanupAllowed());
        }
    }

    public static Task DurableReceiptReleaseAsync(
        IArtifactStore original, IArtifactStoreLifetime originalLifetime, ArtifactStoreIdentity identity,
        IArtifactCoordinationAuthority authority, ArtifactLimits limits,
        Action<Action> observeRecordWrite, Action removeRecordWrite,
        Func<(IArtifactStore Store, IArtifactStoreLifetime Lifetime)> createReopened,
        CancellationToken cancellationToken) =>
        DurableReceiptReleaseAsync(original, originalLifetime, identity, authority, limits,
            occurrence =>
            {
                var writes = 0;
                observeRecordWrite(() =>
                {
                    if (Interlocked.Increment(ref writes) == occurrence)
                    { throw new IOException("Interrupted reservation release."); }
                });
                return ValueTask.CompletedTask;
            }, () => { removeRecordWrite(); return ValueTask.CompletedTask; },
            async token =>
            {
                var reopened = createReopened();
                try
                {
                    Success(await reopened.Lifetime.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible,
                        identity, authority, limits), new(), token));
                    return reopened;
                }
                catch
                {
                    Success(await reopened.Lifetime.StopAsync(new(), token));
                    throw;
                }
            }, cancellationToken);

    public static async Task DurableReceiptReleaseAsync(
        IArtifactStore original, IArtifactStoreLifetime originalLifetime, ArtifactStoreIdentity identity,
        IArtifactCoordinationAuthority authority, ArtifactLimits limits,
        Func<int, ValueTask> injectRecordWriteFailure, Func<ValueTask> removeRecordWrite,
        Func<CancellationToken, ValueTask<(IArtifactStore Store, IArtifactStoreLifetime Lifetime)>> reopenAsync,
        CancellationToken cancellationToken)
    {
        Success(await originalLifetime.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, identity, authority, limits), new(), cancellationToken));
        var ticket = Success(await original.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("durable receipt before reservation release"u8.ToArray());
        var staged = Success(await original.StageAsync(ticket, source, new(), cancellationToken));
        await injectRecordWriteFailure(3);
        try
        {
            Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await original.CommitAsync(staged, new(), cancellationToken)).Code);
        }
        finally
        {
            await removeRecordWrite();
            Success(await originalLifetime.StopAsync(new(), cancellationToken));
        }
        var (reopened, reopenedLifetime) = await reopenAsync(cancellationToken);
        try
        {
            Assert.IsType<ArtifactResolution.Committed>(Success(await reopened.ReconcileAsync(ticket, new(), cancellationToken)));
            Success(await reopened.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        }
        finally { Success(await reopenedLifetime.StopAsync(new(), cancellationToken)); }
    }

    public static Task SettledReceiptReplacementAsync(
        IArtifactStore store, Action<long> setUtc, Action loseAcknowledgment, Action restoreAcknowledgment,
        Action<Func<ValueTask>> observeReconciliation, Action removeReconciliation,
        CancellationToken cancellationToken) =>
        SettledReceiptReplacementAsync(store, setUtc,
            () => { loseAcknowledgment(); return ValueTask.CompletedTask; },
            () => { restoreAcknowledgment(); return ValueTask.CompletedTask; },
            observer => { observeReconciliation(observer); return ValueTask.CompletedTask; },
            () => { removeReconciliation(); return ValueTask.CompletedTask; }, cancellationToken);

    public static async Task SettledReceiptReplacementAsync(
        IArtifactStore store, Action<long> setUtc, Func<ValueTask> loseAcknowledgment, Func<ValueTask> restoreAcknowledgment,
        Func<Func<ValueTask>, ValueTask> observeReconciliation, Func<ValueTask> removeReconciliation,
        CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("settled receipt survives replacement"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        await loseAcknowledgment();
        Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.CommitAsync(staged, new(), cancellationToken)).Code);
        await restoreAcknowledgment();
        await using var barrier = new ArtifactConformanceBarrier("settled-reconciliation-after-replacement");
        await observeReconciliation(() => new(barrier.HoldAsync()));
        var held = store.ReconcileAsync(ticket, new(), cancellationToken).AsTask();
        ArtifactMutationReceipt settled;
        ArtifactMutationReceipt replacement;
        try
        {
            await barrier.Entered;
            await removeReconciliation();
            settled = Assert.IsType<ArtifactResolution.Committed>(
                Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt;
            var deletion = Success(await store.ReserveDeleteAsync(new(settled.Stamp), new(), cancellationToken));
            Success(await store.DeleteAsync(deletion, new(), cancellationToken));
            using var next = new ShortSource("settled receipt survives replacement"u8.ToArray());
            replacement = await PublishAsync(store, next, new(1024), cancellationToken);
            Assert.NotEqual(settled.Stamp, replacement.Stamp);
            setUtc(ticket.Expires.ToUnixTimeMilliseconds());
            Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        }
        finally { barrier.Release(); }
        Assert.Equal(settled, Assert.IsType<ArtifactResolution.Committed>(Success(await held)).Receipt);
        Assert.Equal("settled receipt survives replacement"u8.ToArray(), await ReadAsync(store, replacement.Stamp, cancellationToken));
    }

    public static async Task AdmittedDeleteHistoryAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Action<long> setUtc, Action<Func<ValueTask>> observeDelete, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("held deletion history"u8.ToArray());
        var original = await PublishAsync(store, source, new(1024), cancellationToken);
        var deletion = Success(await store.ReserveDeleteAsync(new(original.Stamp), new(), cancellationToken));
        await using var barrier = new ArtifactConformanceBarrier("admitted-delete-retains-reclaimed-history");
        observeDelete(() => new(barrier.HoldAsync()));
        var held = store.DeleteAsync(deletion, new(), cancellationToken).AsTask();
        try
        {
            await barrier.Entered;
            Success(await maintenance.CleanupAsync(new(identity,
                [new ArtifactCleanupTarget.RemovedIncarnation(original.Stamp)]), new(), cancellationToken));
            setUtc(deletion.Expires.ToUnixTimeMilliseconds());
            var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
            using var next = new ShortSource("different digest awaiting settled history"u8.ToArray());
            var staged = Success(await store.StageAsync(ticket, next, new(), cancellationToken));
            Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await store.CommitAsync(staged, new(), cancellationToken)).Code);
        }
        finally { barrier.Release(); }
        Assert.Equal(ArtifactReclamation.Reclaimed, Success(await held).Reclamation);
        using var replacement = new ShortSource("different digest awaiting settled history"u8.ToArray());
        var current = await PublishAsync(store, replacement, new(1024), cancellationToken);
        Assert.Equal("different digest awaiting settled history"u8.ToArray(), await ReadAsync(store, current.Stamp, cancellationToken));
    }

    public static Task AdmittedReconciliationHistoryAsync(
        IArtifactStore store, Action<long> setUtc, Action loseAcknowledgment, Action restoreAcknowledgment,
        Action<Func<ValueTask>> observeReconciliation, Action removeReconciliation,
        CancellationToken cancellationToken) =>
        AdmittedReconciliationHistoryAsync(store, setUtc,
            () => { loseAcknowledgment(); return ValueTask.CompletedTask; },
            () => { restoreAcknowledgment(); return ValueTask.CompletedTask; },
            observer => { observeReconciliation(observer); return ValueTask.CompletedTask; },
            () => { removeReconciliation(); return ValueTask.CompletedTask; }, cancellationToken);

    public static async Task AdmittedReconciliationHistoryAsync(
        IArtifactStore store, Action<long> setUtc, Func<ValueTask> loseAcknowledgment, Func<ValueTask> restoreAcknowledgment,
        Func<Func<ValueTask>, ValueTask> observeReconciliation, Func<ValueTask> removeReconciliation,
        CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("retained reconciliation ownership"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        await loseAcknowledgment();
        Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.CommitAsync(staged, new(), cancellationToken)).Code);
        await restoreAcknowledgment();
        await using var barrier = new ArtifactConformanceBarrier("reconciliation-owns-expired-history");
        await observeReconciliation(() => new(barrier.HoldAsync()));
        var held = store.ReconcileAsync(ticket, new(), cancellationToken).AsTask();
        ArtifactMutationReceipt settled;
        try
        {
            await barrier.Entered;
            await removeReconciliation();
            settled = Assert.IsType<ArtifactResolution.Committed>(
                Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt;
            setUtc(ticket.Expires.ToUnixTimeMilliseconds());
            Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken)).Code);
        }
        finally { barrier.Release(); }
        Assert.Equal(settled, Assert.IsType<ArtifactResolution.Committed>(Success(await held)).Receipt);
        Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        Assert.Equal("retained reconciliation ownership"u8.ToArray(), await ReadAsync(store, settled.Stamp, cancellationToken));
    }

    public static Task LateCleanupGenerationAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Action<TimeSpan> advanceClock, Action<Func<ValueTask>> observeCleanup, Action removeCleanup,
        CancellationToken cancellationToken) =>
        LateCleanupGenerationAsync(store, maintenance, identity, advanceClock,
            observer => { observeCleanup(observer); return ValueTask.CompletedTask; },
            () => { removeCleanup(); return ValueTask.CompletedTask; }, cancellationToken);

    public static async Task LateCleanupGenerationAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Action<TimeSpan> advanceClock, Func<Func<ValueTask>, ValueTask> observeCleanup, Func<ValueTask> removeCleanup,
        CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var first = new ShortSource("expired generation"u8.ToArray());
        var old = Success(await store.StageAsync(ticket, first, new(), cancellationToken));
        advanceClock(TimeSpan.FromSeconds(30));
        var request = new ArtifactCleanupRequest(identity, [new ArtifactCleanupTarget.AbandonedStaging(old.Owner)]);
        await using var barrier = new ArtifactConformanceBarrier("late-generation-cleanup");
        await observeCleanup(() => new(barrier.HoldAsync()));
        var delayed = maintenance.CleanupAsync(request, new(), cancellationToken).AsTask();
        ArtifactStagedWrite replacement;
        try
        {
            await barrier.Entered;
            await removeCleanup();
            Assert.Equal(1, Success(await maintenance.CleanupAsync(request, new(), cancellationToken)).Completed);
            using var second = new ShortSource("replacement generation"u8.ToArray());
            replacement = Success(await store.StageAsync(ticket, second, new(), cancellationToken));
            Assert.True(replacement.Owner.Generation > old.Owner.Generation);
        }
        finally { barrier.Release(); }
        var result = Success(await delayed);
        Assert.Equal(1, result.Conflicted);
        Assert.Equal(0, result.ReclaimedBytes);
        var receipt = Success(await store.CommitAsync(replacement, new(), cancellationToken));
        Assert.Equal("replacement generation"u8.ToArray(), await ReadAsync(store, receipt.Stamp, cancellationToken));
    }

    public static Task ProgressingCommitAsync(
        IArtifactStore store, Action<TimeSpan> advanceClock, Action<Func<ValueTask>> observeProgress,
        CancellationToken cancellationToken) =>
        ProgressingCommitAsync(store, advanceClock, callback =>
        {
            observeProgress(callback);
            return ValueTask.CompletedTask;
        }, cancellationToken);

    public static async Task ProgressingCommitAsync(
        IArtifactStore store, Action<TimeSpan> advanceClock, Func<Func<ValueTask>, ValueTask> observeProgress,
        CancellationToken cancellationToken)
    {
        var bytes = new byte[1048576];
        using var first = new MemoryStream(bytes, writable: false);
        await PublishAsync(store, first, new(2097152), cancellationToken);
        using var duplicate = new MemoryStream(bytes, writable: false);
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(2097152)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, duplicate, new(), cancellationToken));
        var progress = 0;
        ValueTask Advance()
        {
            advanceClock(TimeSpan.FromSeconds(11));
            Interlocked.Increment(ref progress);
            return ValueTask.CompletedTask;
        }
        await observeProgress(Advance);
        var receipt = Success(await store.CommitAsync(staged, new(), cancellationToken));
        Assert.True(progress >= 4);
        Assert.Equal(ArtifactMutationOutcome.AlreadyPresentVerified, receipt.Outcome);
        Assert.Equal(receipt, Success(await store.CommitAsync(staged, new(), cancellationToken)));
    }

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
