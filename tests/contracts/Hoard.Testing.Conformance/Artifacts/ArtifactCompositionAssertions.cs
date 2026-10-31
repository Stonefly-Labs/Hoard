using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactCompositionAssertions
{
    public static async Task<ArtifactMutationReceipt> ConfiguredPublicationAsync(
        IArtifactStore store, CancellationToken cancellationToken)
    {
        var bytes = "configured selected-store recovery"u8.ToArray();
        using var source = new ShortSource(bytes);
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        return Success(await store.CommitAsync(staged, new(), cancellationToken));
    }

    public static async Task CompatibleReopenAsync(
        IArtifactStore store, ArtifactStoreIdentity identity, ArtifactMutationReceipt old, CancellationToken cancellationToken)
    {
        var bytes = "configured selected-store recovery"u8.ToArray();
        Assert.Equal(old.Stamp.Store, identity);
        Assert.Equal(old, Assert.IsType<ArtifactResolution.Committed>(
            Success(await store.ReconcileAsync(old.Ticket, new(), cancellationToken))).Receipt);
        await using var read = Success(await store.OpenReadAsync(
            new(old.Stamp.Identity.Digest, expectedStamp: new ArtifactOption<ArtifactStamp>.Some(old.Stamp)), new(), cancellationToken));
        using var destination = new MemoryStream();
        Success(await read.CopyToAsync(destination, new(), cancellationToken));
        Assert.Equal(bytes, destination.ToArray());
    }

    public static async Task FreshEpochAsync(
        IArtifactStore store, ArtifactStoreIdentity identity, ArtifactMutationReceipt old, CancellationToken cancellationToken)
    {
        Assert.NotEqual(old.Stamp.Store.Epoch, identity.Epoch);
        Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
            await store.ReconcileAsync(old.Ticket, new(), cancellationToken));
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(old.Stamp.Identity.Digest), new(), cancellationToken)).Code);
    }
}
