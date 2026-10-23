using Hoard.Abstractions.Storage;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactVisibilityTests
{
    [Fact]
    public async Task Local_publication_is_directly_visible_before_acknowledgment()
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync("local");
        var bytes = "direct local publication before acknowledgment"u8.ToArray();
        using var source = new ArtifactPublicationTests.ShortSource(bytes);
        var ticket = ArtifactPublicationTests.Success(
            await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staged = ArtifactPublicationTests.Success(await driver.Store.StageAsync(ticket, source, new(), default));
        await using var boundary = new ArtifactTestBarrier("local-receipt-before-acknowledgment");
        driver.LocalControls!.SetObserver("publish.receipted", () => new(boundary.HoldAsync()));
        var committing = driver.Store.CommitAsync(staged, new(), default).AsTask();
        await boundary.Entered;
        try
        {
            Assert.False(committing.IsCompleted);
            await using var read = ArtifactPublicationTests.Success(await driver.Store.OpenReadAsync(
                new(staged.Identity.Digest), new(), default));
            using var destination = new MemoryStream();
            ArtifactPublicationTests.Success(await read.CopyToAsync(destination, new(), default));
            Assert.Equal(bytes, destination.ToArray());
        }
        finally { boundary.Release(); }
        var receipt = ArtifactPublicationTests.Success(await committing);
        Assert.Equal(bytes, await ArtifactPublicationTests.ReadAsync(driver, receipt.Stamp));
    }

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
