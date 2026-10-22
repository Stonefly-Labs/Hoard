using Hoard.Abstractions.Storage;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactVisibilityTests
{
    [Fact]
    public async Task Delayed_object_listing_does_not_block_direct_publication_or_establish_absence()
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync("object");
        await using var listing = new ArtifactTestBarrier("independent-listing");
        driver.ObjectControls!.SetObserver("object.list", () => new(listing.HoldAsync()));
        var observation = driver.Maintenance.ObserveAsync(
            new(driver.Identity, ArtifactRecoveryKind.Committed, 10), new(), default).AsTask();
        try
        {
            await listing.Entered;
            using var source = new ShortSource("direct visibility does not depend on listing"u8.ToArray());
            var receipt = await PublishAsync(driver, source, new(1024));
            Assert.Equal("direct visibility does not depend on listing"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
            Assert.False(observation.IsCompleted);
        }
        finally { listing.Release(); }
        var page = Success(await observation);
        Assert.Equal(ArtifactEnumerationConsistency.Incomplete, page.Consistency);
        Assert.Single(page.Observations);
    }

    [Fact]
    public async Task Object_commit_waits_for_direct_availability_while_listing_is_independently_observable()
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync("object");
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("direct acknowledgment barrier"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        await using var direct = new ArtifactTestBarrier("independent-direct");
        driver.ObjectControls!.SetObserver("object.direct", () => new(direct.HoldAsync()));
        var committing = driver.Store.CommitAsync(staged, new(), default).AsTask();
        try
        {
            await direct.Entered;
            Assert.False(committing.IsCompleted);
            var listed = Success(await driver.Maintenance.ObserveAsync(
                new(driver.Identity, ArtifactRecoveryKind.Committed, 10), new(), default));
            Assert.Equal(ArtifactEnumerationConsistency.Incomplete, listed.Consistency);
            Assert.Single(listed.Observations);
            Assert.False(committing.IsCompleted);
        }
        finally
        {
            driver.ObjectControls.RemoveObserver("object.direct");
            direct.Release();
        }
        var receipt = Success(await committing);
        Assert.Equal("direct acknowledgment barrier"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
    }
}
