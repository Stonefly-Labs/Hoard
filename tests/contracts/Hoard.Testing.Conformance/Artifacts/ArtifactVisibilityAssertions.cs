using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactVisibilityAssertions
{
    public static async Task VisibleBeforeAcknowledgmentAsync(
        IArtifactStore store, Action blockAcknowledgment, Func<CancellationToken, Task> waitForAcknowledgment,
        Action releaseAcknowledgment, CancellationToken cancellationToken)
    {
        var bytes = "direct local publication before acknowledgment"u8.ToArray();
        using var source = new ShortSource(bytes);
        var ticket = Success(
            await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        blockAcknowledgment();
        var committing = store.CommitAsync(staged, new(), cancellationToken).AsTask();
        await waitForAcknowledgment(cancellationToken);
        try
        {
            Assert.False(committing.IsCompleted);
            await using var read = Success(await store.OpenReadAsync(
                new(staged.Identity.Digest), new(), cancellationToken));
            using var destination = new MemoryStream();
            Success(await read.CopyToAsync(destination, new(), cancellationToken));
            Assert.Equal(bytes, destination.ToArray());
        }
        finally { releaseAcknowledgment(); }
        var receipt = Success(await committing);
        Assert.Equal(bytes, await ReadAsync(store, receipt.Stamp, cancellationToken));
    }

    public static async Task IndependentListingAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Action blockListing, Func<CancellationToken, Task> waitForListing,
        Action releaseListing, CancellationToken cancellationToken)
    {
        blockListing();
        var observation = maintenance.ObserveAsync(
            new(identity, ArtifactRecoveryKind.Committed, 10), new(), cancellationToken).AsTask();
        try
        {
            await waitForListing(cancellationToken);
            using var source = new ShortSource("direct visibility does not depend on listing"u8.ToArray());
            var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
            Assert.Equal("direct visibility does not depend on listing"u8.ToArray(),
                await ReadAsync(store, receipt.Stamp, cancellationToken));
            Assert.False(observation.IsCompleted);
        }
        finally { releaseListing(); }
        var page = Success(await observation);
        Assert.Equal(ArtifactEnumerationConsistency.Incomplete, page.Consistency);
        Assert.Single(page.Observations);
    }

    public static async Task DirectAvailabilityAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Action blockDirect, Func<CancellationToken, Task> waitForDirect,
        Action releaseDirect, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("direct acknowledgment barrier"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        blockDirect();
        var committing = store.CommitAsync(staged, new(), cancellationToken).AsTask();
        try
        {
            await waitForDirect(cancellationToken);
            Assert.False(committing.IsCompleted);
            var listed = Success(await maintenance.ObserveAsync(
                new(identity, ArtifactRecoveryKind.Committed, 10), new(), cancellationToken));
            Assert.Equal(ArtifactEnumerationConsistency.Incomplete, listed.Consistency);
            Assert.Single(listed.Observations);
            Assert.False(committing.IsCompleted);
        }
        finally { releaseDirect(); }
        var receipt = Success(await committing);
        Assert.Equal("direct acknowledgment barrier"u8.ToArray(),
            await ReadAsync(store, receipt.Stamp, cancellationToken));
    }
}
