using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Testing.Conformance.Artifacts;
using Xunit.Abstractions;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactReconciliationTests(ITestOutputHelper output)
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Finalized_mutation_retries_preserve_expiry_and_foreign_ticket_failures(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock,
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactReconciliationAssertions.FinalizedMutationExpiryAsync(driver.Store, clock.Advance, default);
        driver.ObserveOriginal(output, nameof(ArtifactReconciliationTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Acknowledged_commit_reconciles_and_retries_one_identical_receipt_without_new_source(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactReconciliationAssertions.AcknowledgedReceiptRetryAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactReconciliationTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Lost_acknowledgment_never_becomes_rollback_or_another_publication(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactReconciliationAssertions.LostAcknowledgmentAsync(driver.Store,
            () => SetObserver(driver, "publish.decided", "pointer.selected",
                () => ValueTask.FromException(new IOException(ArtifactTestData.Canary))), default);
        driver.ObserveOriginal(output, nameof(ArtifactReconciliationTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Expired_history_cannot_be_revived_by_clock_rollback_or_foreign_epoch(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        await ArtifactReconciliationAssertions.ExpiredHistoryRollbackAsync(
            driver.Store, driver.Identity, clock.Advance, clock.SetUtc, default);
        driver.ObserveOriginal(output, nameof(ArtifactReconciliationTests));
    }
}
