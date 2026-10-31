using Hoard.Testing.Conformance.Artifacts;
using Xunit.Abstractions;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactVisibilityTests(ITestOutputHelper output)
{
    [Fact]
    public async Task Local_publication_is_directly_visible_before_acknowledgment()
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync("local");
        await using var boundary = new ArtifactTestBarrier("local-receipt-before-acknowledgment");
        await ArtifactVisibilityAssertions.VisibleBeforeAcknowledgmentAsync(driver.Store,
            () => driver.LocalControls!.SetObserver("publish.receipted", () => new(boundary.HoldAsync())),
            token => boundary.Entered.WaitAsync(token), boundary.Release, default);
        driver.ObserveOriginal(output, nameof(ArtifactVisibilityTests), providerParameter: false);
    }

    [Fact]
    public async Task Delayed_object_listing_does_not_block_direct_publication_or_establish_absence()
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync("object");
        await using var listing = new ArtifactTestBarrier("independent-listing");
        await ArtifactVisibilityAssertions.IndependentListingAsync(driver.Store, driver.Maintenance, driver.Identity,
            () => driver.ObjectControls!.SetObserver("object.list", () => new(listing.HoldAsync())),
            token => listing.Entered.WaitAsync(token), listing.Release, default);
        driver.ObserveOriginal(output, nameof(ArtifactVisibilityTests), providerParameter: false);
    }

    [Fact]
    public async Task Object_commit_waits_for_direct_availability_while_listing_is_independently_observable()
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync("object");
        await using var direct = new ArtifactTestBarrier("independent-direct");
        await ArtifactVisibilityAssertions.DirectAvailabilityAsync(driver.Store, driver.Maintenance, driver.Identity,
            () => driver.ObjectControls!.SetObserver("object.direct", () => new(direct.HoldAsync())),
            token => direct.Entered.WaitAsync(token),
            () =>
            {
                driver.ObjectControls!.RemoveObserver("object.direct");
                direct.Release();
            }, default);
        driver.ObserveOriginal(output, nameof(ArtifactVisibilityTests), providerParameter: false);
    }
}
