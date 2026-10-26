using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactReadAssertions
{
    public static async Task CommittedDetectionQuarantineAsync(
        IArtifactStore store, string detection, ArtifactDurability expectedDurability,
        Action removePayload, Action<byte[]> restoreRemovedPayload, Action observePublicationDecision,
        Action removePublicationObserver, Action damage, Action<byte[]> restorePayload, CancellationToken cancellationToken,
        ArtifactQuarantineReopen? reopen)
    {
        var bytes = "quarantine at each committed detection boundary"u8.ToArray();
        using var source = new ShortSource(bytes);
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        ArtifactMutationReceipt receipt;
        if (detection == "open")
        {
            receipt = Success(await store.CommitAsync(staged, new(), cancellationToken));
            removePayload();
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await store.OpenReadAsync(new(staged.Identity.Digest), new(), cancellationToken)).Code);
            restoreRemovedPayload(bytes);
        }
        else
        {
            observePublicationDecision();
            Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await store.CommitAsync(staged, new(), cancellationToken));
            removePublicationObserver();
            if (detection == "reconciliation")
            {
                damage();
                Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
                    await store.ReconcileAsync(ticket, new(), cancellationToken));
            }
            restorePayload(bytes);
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await store.OpenReadAsync(new(staged.Identity.Digest), new(), cancellationToken)).Code);
            if (detection == "reconciliation" || expectedDurability == ArtifactDurability.SimulationOnly)
            {
                Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
                    await store.ReconcileAsync(ticket, new(), cancellationToken));
                using var duplicate = new ShortSource(bytes);
                var retry = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
                var restaged = Success(await store.StageAsync(retry, duplicate, new(), cancellationToken));
                Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                    await store.CommitAsync(restaged, new(), cancellationToken)).Code);
                Success(await store.AbandonAsync(restaged.Owner, new(), cancellationToken));
                return;
            }
            receipt = Assert.IsType<ArtifactResolution.Committed>(
                Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt;
        }
        await ArtifactEvidenceAssertions.QuarantineIsPermanentAsync(store, receipt, bytes, cancellationToken, reopen);
    }

    public static async Task ReconciliationQuarantineRaceAsync(
        IArtifactStore store, Action loseAcknowledgment, Action restoreAcknowledgment, Action damage,
        Action observeCopy, Action observeReconciliation,
        Func<CancellationToken, Task> waitForCopy, Func<CancellationToken, Task> waitForReconciliation,
        Action releaseCopy, Action releaseReconciliation, Action<byte[]> restore, CancellationToken cancellationToken)
    {
        var bytes = "read detection wins before reconciliation settles"u8.ToArray();
        using var source = new ShortSource(bytes);
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        loseAcknowledgment();
        Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await store.CommitAsync(staged, new(), cancellationToken));
        restoreAcknowledgment();
        damage();
        await using var session = Success(await store.OpenReadAsync(new(staged.Identity.Digest), new(), cancellationToken));
        observeCopy();
        observeReconciliation();
        using var destination = new MemoryStream();
        var copying = session.CopyToAsync(destination, new(), cancellationToken).AsTask();
        Task<ArtifactResult<ArtifactResolution>>? reconciling = null;
        try
        {
            await waitForCopy(cancellationToken);
            restore(bytes);
            reconciling = store.ReconcileAsync(ticket, new(), cancellationToken).AsTask();
            await waitForReconciliation(cancellationToken);
            releaseCopy();
            Assert.Equal(ArtifactFailureCode.CorruptContent,
                Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(await copying).Code);
        }
        finally { releaseCopy(); releaseReconciliation(); }
        Assert.NotNull(reconciling);
        Assert.Equal(ArtifactFailureCode.CorruptContent,
            Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(await reconciling).Code);
        Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(await store.ReconcileAsync(ticket, new(), cancellationToken));
    }

    public static Task AdmittedOpenRechecksQuarantineAsync(
        IArtifactStore store, IArtifactEvidenceValidator validator, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, Action observeOpening, Func<CancellationToken, Task> waitForOpening,
        Action removeObserver, Action<byte[]> replacePayload, Action releaseOpening, CancellationToken cancellationToken) =>
        AdmittedOpenRechecksQuarantineAsync(store, validator, authority, identity,
            () => { observeOpening(); return ValueTask.CompletedTask; }, waitForOpening,
            () => { removeObserver(); return ValueTask.CompletedTask; },
            (_, bytes, _) => { replacePayload(bytes.ToArray()); return ValueTask.CompletedTask; },
            releaseOpening, cancellationToken);

    public static async Task AdmittedOpenRechecksQuarantineAsync(
        IArtifactStore store, IArtifactEvidenceValidator validator, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, Func<ValueTask> observeOpening, Func<CancellationToken, Task> waitForOpening,
        Func<ValueTask> removeObserver,
        Func<ArtifactStamp, ReadOnlyMemory<byte>, CancellationToken, ValueTask> replacePayload,
        Action releaseOpening, CancellationToken cancellationToken)
    {
        var bytes = "late open cannot bypass quarantine"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        await observeOpening();
        var opening = store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken).AsTask();
        try
        {
            await waitForOpening(cancellationToken);
            await removeObserver();
            await replacePayload(receipt.Stamp, bytes[..^1], cancellationToken);
            await using var guard = Success(await authority.AcquireAsync(new(Guid.NewGuid(),
                ArtifactProtectionOperation.Reference, identity, receipt.Stamp.Identity.Digest,
                new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), cancellationToken));
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await validator.ValidateAsync(proof, guard, new(), cancellationToken)).Code);
            await replacePayload(receipt.Stamp, bytes, cancellationToken);
        }
        finally { releaseOpening(); }
        var result = await opening;
        if (result is ArtifactResult<IArtifactReadSession>.Success leaked) { await leaked.Value.DisposeAsync(); }
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(result).Code);
    }

    public static async Task DamagedReadAsync(
        IArtifactStore store, IArtifactEvidenceValidator validator, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, bool truncate, Func<ArtifactStamp, CancellationToken, ValueTask<byte[]>> capture,
        Func<ArtifactStamp, bool, CancellationToken, ValueTask> damage,
        Func<ArtifactStamp, ReadOnlyMemory<byte>, CancellationToken, ValueTask> restore, CancellationToken cancellationToken,
        ArtifactQuarantineReopen? reopen, Func<CancellationToken, ValueTask<IArtifactStore>>? reopenAsync = null)
    {
        using var source = new ShortSource("detect stored corruption"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        var bytes = await capture(receipt.Stamp, cancellationToken);
        await damage(receipt.Stamp, truncate, cancellationToken);
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        await using (var session = Success(await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)))
        {
            using var destination = new MemoryStream();
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await session.CopyToAsync(destination, new(), cancellationToken)).Code);
            Assert.True(destination.CanWrite);
        }
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)).Code);
        var scope = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Reference,
            identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        await using var guard = Success(await authority.AcquireAsync(scope, new(), cancellationToken));
        Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(await validator.ValidateAsync(proof, guard, new(), cancellationToken));
        await restore(receipt.Stamp, bytes, cancellationToken);
        await guard.DisposeAsync();
        if (reopenAsync is not null)
        {
            Assert.Null(reopen);
            await ArtifactEvidenceAssertions.QuarantineAfterCompatibleReopenAsync(
                store, receipt, bytes, cancellationToken, reopenAsync);
        }
        else { await ArtifactEvidenceAssertions.QuarantineIsPermanentAsync(store, receipt, bytes, cancellationToken, reopen); }
    }

    public static async Task ExactPayloadControlsAsync(
        IArtifactStore store, Func<ArtifactStamp, int, CancellationToken, ValueTask<byte[]>> capture,
        Func<ArtifactStamp, ReadOnlyMemory<byte>, CancellationToken, ValueTask> replace,
        Func<ArtifactStamp, CancellationToken, ValueTask> remove, CancellationToken cancellationToken)
    {
        var bytes = "exact bounded payload"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        var controlBytes = "independent control"u8.ToArray();
        using var controlSource = new ShortSource(controlBytes);
        var control = await PublishAsync(store, controlSource, new(1024), cancellationToken);
        var copy = await capture(receipt.Stamp, 1024, cancellationToken);
        Assert.Equal(bytes, copy);
        copy[0] ^= 0xff;
        Assert.Equal(bytes, await capture(receipt.Stamp, 1024, cancellationToken));
        Assert.Equal("FaultControl.Capacity", (await Assert.ThrowsAsync<InvalidOperationException>(
            () => capture(receipt.Stamp, bytes.Length - 1, cancellationToken).AsTask())).Message);
        Assert.Equal("FaultControl.InvalidInput", (await Assert.ThrowsAsync<InvalidOperationException>(
            () => capture(receipt.Stamp, 65537, cancellationToken).AsTask())).Message);
        Assert.Equal("FaultControl.InvalidInput", (await Assert.ThrowsAsync<InvalidOperationException>(
            () => replace(receipt.Stamp, new byte[65537], cancellationToken).AsTask())).Message);
        var stale = new ArtifactStamp(receipt.Stamp.Store, receipt.Stamp.Identity, Guid.NewGuid());
        foreach (var action in new Func<Task>[]
        {
            () => capture(stale, 1024, cancellationToken).AsTask(),
            () => replace(stale, bytes, cancellationToken).AsTask(),
            () => remove(stale, cancellationToken).AsTask()
        })
        {
            Assert.Equal("FaultControl.Conflict", (await Assert.ThrowsAsync<InvalidOperationException>(action)).Message);
        }
        var changing = "changed"u8.ToArray();
        var replacing = replace(receipt.Stamp, changing, cancellationToken);
        changing[0] ^= 0xff;
        await replacing;
        Assert.Equal("changed"u8.ToArray(), await capture(receipt.Stamp, 1024, cancellationToken));
        Assert.Equal(controlBytes, await ReadAsync(store, control.Stamp, cancellationToken));
        await remove(receipt.Stamp, cancellationToken);
        await Assert.ThrowsAsync<InvalidOperationException>(() => capture(receipt.Stamp, 1024, cancellationToken).AsTask());
        await Assert.ThrowsAsync<InvalidOperationException>(() => remove(receipt.Stamp, cancellationToken).AsTask());
        await replace(receipt.Stamp, bytes, cancellationToken);
        await replace(receipt.Stamp, Array.Empty<byte>(), cancellationToken);
        Assert.Empty(await capture(receipt.Stamp, 0, cancellationToken));
        await replace(receipt.Stamp, bytes, cancellationToken);
        Assert.Equal(bytes, await ReadAsync(store, receipt.Stamp, cancellationToken));
        Assert.Equal(receipt, Assert.IsType<ArtifactResolution.Committed>(
            Success(await store.ReconcileAsync(receipt.Ticket, new(), cancellationToken))).Receipt);
        Assert.Equal(controlBytes, await ReadAsync(store, control.Stamp, cancellationToken));
        var deletion = Success(await store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
        Success(await store.DeleteAsync(deletion, new(), cancellationToken));
        using var replacementSource = new ShortSource(bytes);
        var replacement = await PublishAsync(store, replacementSource, new(1024), cancellationToken);
        Assert.NotEqual(receipt.Stamp, replacement.Stamp);
        foreach (var action in new Func<Task>[]
        {
            () => capture(receipt.Stamp, 1024, cancellationToken).AsTask(),
            () => replace(receipt.Stamp, bytes, cancellationToken).AsTask(),
            () => remove(receipt.Stamp, cancellationToken).AsTask()
        })
        {
            Assert.Equal("FaultControl.Conflict", (await Assert.ThrowsAsync<InvalidOperationException>(action)).Message);
        }
        Assert.Equal(bytes, await ReadAsync(store, replacement.Stamp, cancellationToken));
    }

    public static async Task PayloadControlsExcludeDeletionAsync(
        IArtifactStore store, Func<ArtifactStamp, int, CancellationToken, ValueTask<byte[]>> capture,
        Func<ArtifactStamp, ReadOnlyMemory<byte>, CancellationToken, ValueTask> replace,
        Func<ArtifactStamp, CancellationToken, ValueTask> remove, Func<int> waitingAdmissions,
        Func<Func<ValueTask>, CancellationToken, ValueTask<IAsyncDisposable>> observeSelected,
        CancellationToken cancellationToken)
    {
        for (var operation = 0; operation < 3; operation++)
        {
            var bytes = new byte[] { 41, 42, (byte)operation };
            using var source = new ShortSource(bytes);
            var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
            var ticket = Success(await store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
            await using var barrier = new ArtifactConformanceBarrier("payload-control-delete");
            await using var observation = await observeSelected(() => new(barrier.HoldAsync()), cancellationToken);
            using var budget = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            budget.CancelAfter(TimeSpan.FromSeconds(15));
            Task control = operation switch
            {
                0 => replace(receipt.Stamp, bytes, budget.Token).AsTask(),
                1 => capture(receipt.Stamp, 1024, budget.Token).AsTask(),
                _ => remove(receipt.Stamp, budget.Token).AsTask()
            };
            Task<ArtifactResult<ArtifactMutationReceipt>>? deleting = null;
            try
            {
                await barrier.Entered.WaitAsync(budget.Token);
                deleting = store.DeleteAsync(ticket, new(), budget.Token).AsTask();
                while (waitingAdmissions() == 0 && !deleting.IsCompleted)
                { await Task.Delay(1, budget.Token); }
                Assert.False(deleting.IsCompleted);
                Assert.Equal(1, waitingAdmissions());
            }
            finally
            {
                barrier.Release();
                try { await control; }
                finally { if (deleting is not null) { await deleting; } }
            }
            Assert.NotNull(deleting);
            var removed = Success(await deleting);
            Assert.Equal(ArtifactMutationOutcome.Removed, removed.Outcome);
            Assert.Equal(ArtifactReclamation.Reclaimed, removed.Reclamation);
            Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)).Code);
            Assert.Equal("FaultControl.Conflict", (await Assert.ThrowsAsync<InvalidOperationException>(
                () => replace(receipt.Stamp, bytes, cancellationToken).AsTask())).Message);
        }
    }

    public static async Task DestinationFailureAsync(
        IArtifactStore store, string failureMessage, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("borrowed streams"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        await using var session = Success(await store.OpenReadAsync(
            new(receipt.Stamp.Identity.Digest), new(), cancellationToken));
        using var destination = new FailingDestination(failureMessage);
        Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
            await session.CopyToAsync(destination, new(), cancellationToken));
        Assert.False(destination.WasDisposed);
        Assert.False(source.WasDisposed);
        Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
            await session.CopyToAsync(Stream.Null, new(), cancellationToken));
    }

    private sealed class FailingDestination(string failureMessage) : MemoryStream
    {
        public bool WasDisposed { get; private set; }
        public override ValueTask WriteAsync(ReadOnlyMemory<byte> buffer, CancellationToken cancellationToken = default) =>
            ValueTask.FromException(new IOException(failureMessage));
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
    }
}
