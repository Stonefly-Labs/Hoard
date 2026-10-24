using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactObservationAssertions
{
    public static async Task ReceiptPersistedAsync(
        IArtifactStore store, Action<Func<ValueTask>> observe, Action remove, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("observed publication"u8.ToArray());
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        observe(() => { entered.TrySetResult(); return new(release.Task); });
        var committing = store.CommitAsync(staged, new(), cancellationToken).AsTask();
        ArtifactMutationReceipt? persisted = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5), cancellationToken);
            Assert.False(committing.IsCompleted);
            persisted = Assert.IsType<ArtifactResolution.Committed>(
                Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt;
        }
        finally
        {
            remove();
            release.TrySetResult();
            Assert.Equal(persisted, Success(await committing));
        }
    }

    public static async Task ReadOpenedFailureAsync(
        IArtifactStore store, Action<Func<ValueTask>> observe, Action remove, CancellationToken cancellationToken)
    {
        var bytes = "observed resource opening"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        observe(() => throw new InvalidOperationException("controlled-read-open-failure"));
        try
        {
            Assert.Equal(ArtifactFailureCode.InternalFailure, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)).Code);
        }
        finally { remove(); }
        await using var read = Success(await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken));
        using var destination = new MemoryStream();
        Success(await read.CopyToAsync(destination, new(), cancellationToken));
        Assert.Equal(bytes, destination.ToArray());
        Assert.Equal(ArtifactCleanupState.Released, Success(await read.CloseAsync(new(), cancellationToken)).State);
        var deletion = Success(await store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
        var removed = await store.DeleteAsync(deletion, new(), cancellationToken);
        Assert.True(removed is ArtifactResult<ArtifactMutationReceipt>.Success,
            removed is ArtifactResult<ArtifactMutationReceipt>.Failure failure
                ? failure.Code.ToString() : "Unexpected deletion result.");
    }

    public static async Task ReconciliationVerifiedAsync(
        IArtifactStore store, Action<Func<ValueTask>> observeSelected, Action removeSelected,
        Action<Func<ValueTask>> observeBefore, Action<Func<ValueTask>> observeVerified, Action removeReconciliation,
        CancellationToken cancellationToken)
    {
        using var source = new ShortSource("observed reconciliation"u8.ToArray());
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        observeSelected(() => throw new InvalidOperationException("controlled-selected-failure"));
        try
        {
            Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await store.CommitAsync(staged, new(), cancellationToken)).Code);
        }
        finally { removeSelected(); }
        var before = 0;
        var verified = 0;
        observeBefore(() => { Interlocked.Increment(ref before); return ValueTask.CompletedTask; });
        observeVerified(() =>
        {
            Interlocked.Increment(ref verified);
            throw new InvalidOperationException("controlled-verified-failure");
        });
        try
        {
            Assert.Equal(ArtifactFailureCode.InternalFailure, Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
                await store.ReconcileAsync(ticket, new(), cancellationToken)).Code);
            Assert.Equal(1, before);
            Assert.Equal(1, verified);
        }
        finally { removeReconciliation(); }
        var recovered = Assert.IsType<ArtifactResolution.Committed>(
            Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt;
        Assert.Equal(ticket, recovered.Ticket);
        Assert.Equal(staged.Identity, recovered.Stamp.Identity);
    }
}
