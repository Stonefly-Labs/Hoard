using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactDeletionAssertions
{
    public static async Task ExactReceiptsAndRecreationAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        CancellationToken cancellationToken)
    {
        var bytes = "delete then recreate"u8.ToArray();
        using var first = new ShortSource(bytes);
        var original = await PublishAsync(store, first, new(1024), cancellationToken);
        var ticket = Success(await store.ReserveDeleteAsync(new(original.Stamp), new(), cancellationToken));
        var removed = Success(await store.DeleteAsync(ticket, new(), cancellationToken));
        Assert.Equal(ArtifactMutationOutcome.Removed, removed.Outcome);
        Assert.Equal(removed, Success(await store.DeleteAsync(ticket, new(), cancellationToken)));
        Assert.Equal(removed, Assert.IsType<ArtifactResolution.Removed>(
            Success(await store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt);
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(original.Stamp.Identity.Digest), new(), cancellationToken)).Code);
        var repeat = Success(await store.ReserveDeleteAsync(new(original.Stamp), new(), cancellationToken));
        Assert.Equal(ArtifactMutationOutcome.AlreadyAbsent,
            Success(await store.DeleteAsync(repeat, new(), cancellationToken)).Outcome);
        using var next = new ShortSource(bytes);
        var recreated = await PublishAsync(store, next, new(1024), cancellationToken);
        Assert.NotEqual(original.Stamp.Incarnation, recreated.Stamp.Incarnation);
        var stale = Success(await store.ReserveDeleteAsync(new(original.Stamp), new(), cancellationToken));
        Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.DeleteAsync(stale, new(), cancellationToken)).Code);
        var cleanup = new ArtifactCleanupRequest(identity, [new ArtifactCleanupTarget.RemovedIncarnation(original.Stamp)]);
        Success(await maintenance.CleanupAsync(cleanup, new(), cancellationToken));
        Assert.Equal(bytes, await ReadAsync(store, recreated.Stamp, cancellationToken));
    }

    public static async Task HeldReaderExcludesDeletionAsync(
        IArtifactStore store, CancellationToken cancellationToken)
    {
        var bytes = "reader exclusion"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        Task<ArtifactResult<ArtifactMutationReceipt>> deletion;
        await using (var reader = Success(await store.OpenReadAsync(
            new(receipt.Stamp.Identity.Digest), new(), cancellationToken)))
        {
            var ticket = Success(await store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
            deletion = store.DeleteAsync(ticket, new(), cancellationToken).AsTask();
            using var destination = new MemoryStream();
            Success(await reader.CopyToAsync(destination, new(), cancellationToken));
            Assert.False(deletion.IsCompleted);
            Assert.Equal(bytes, destination.ToArray());
        }
        Assert.Equal(ArtifactMutationOutcome.Removed, Success(await deletion).Outcome);
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)).Code);
    }
}
