using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactReadAssertions
{
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

    public static async Task AdmittedOpenRechecksQuarantineAsync(
        IArtifactStore store, IArtifactEvidenceValidator validator, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, Action observeOpening, Func<CancellationToken, Task> waitForOpening,
        Action removeObserver, Action<byte[]> replacePayload, Action releaseOpening, CancellationToken cancellationToken)
    {
        var bytes = "late open cannot bypass quarantine"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        observeOpening();
        var opening = store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken).AsTask();
        try
        {
            await waitForOpening(cancellationToken);
            removeObserver();
            replacePayload(bytes[..^1]);
            await using var guard = Success(await authority.AcquireAsync(new(Guid.NewGuid(),
                ArtifactProtectionOperation.Reference, identity, receipt.Stamp.Identity.Digest,
                new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), cancellationToken));
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await validator.ValidateAsync(proof, guard, new(), cancellationToken)).Code);
            replacePayload(bytes);
        }
        finally { releaseOpening(); }
        var result = await opening;
        if (result is ArtifactResult<IArtifactReadSession>.Success leaked) { await leaked.Value.DisposeAsync(); }
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(result).Code);
    }

    public static async Task DamagedReadAsync(
        IArtifactStore store, IArtifactEvidenceValidator validator, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, bool truncate, Func<ValueTask<byte[]>> capture,
        Func<bool, ValueTask> damage, Func<byte[], ValueTask> restore, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("detect stored corruption"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        var bytes = await capture();
        await damage(truncate);
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
        await restore(bytes);
        await guard.DisposeAsync();
        await ArtifactEvidenceAssertions.QuarantineIsPermanentAsync(store, receipt, bytes, cancellationToken);
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
