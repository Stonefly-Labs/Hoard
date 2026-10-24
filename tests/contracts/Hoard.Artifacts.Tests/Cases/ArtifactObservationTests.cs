using Hoard.Testing.Conformance.Artifacts;
using Hoard.Fixtures.Artifacts.HostAdapters;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactObservationTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Persisted_receipt_boundary_exposes_the_same_actual_reconciled_receipt(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactObservationAssertions.ReceiptPersistedAsync(driver.Store,
            observer => Set(driver, "publish.receipted", "object.receipted", observer),
            () => Remove(driver, "publish.receipted", "object.receipted"), default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Failed_opened_read_callback_reclaims_real_stream_guard_and_single_transfer_slot(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new(artifactBytes: 1024, stagingBytes: 4096, transferSlots: 1, waitingCalls: 0),
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactObservationAssertions.ReadOpenedFailureAsync(driver.Store,
            observer => Set(driver, "read.opened", "object.read-opened", observer),
            () => Remove(driver, "read.opened", "object.read-opened"), default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Verified_reconciliation_callback_failure_keeps_actual_uncertain_publication_recoverable(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactObservationAssertions.ReconciliationVerifiedAsync(driver.Store,
            observer => Set(driver, "publish.decided", "pointer.selected", observer),
            () => Remove(driver, "publish.decided", "pointer.selected"),
            observer => Set(driver, "reconcile.before-resolution", "object.reconcile-before-resolution", observer),
            observer => Set(driver, "reconcile.verified", "object.reconcile-verified", observer),
            () =>
            {
                Remove(driver, "reconcile.before-resolution", "object.reconcile-before-resolution");
                Remove(driver, "reconcile.verified", "object.reconcile-verified");
            }, default);
    }

    private static void Set(ArtifactProviderDriver driver, string local, string objects, Func<ValueTask> observer)
    {
        if (driver.LocalControls is { } controls) { controls.SetObserver(local, observer); }
        else { driver.ObjectControls!.SetObserver(objects, observer); }
    }

    private static void Remove(ArtifactProviderDriver driver, string local, string objects)
    {
        driver.LocalControls?.RemoveObserver(local);
        driver.ObjectControls?.RemoveObserver(objects);
    }
}
