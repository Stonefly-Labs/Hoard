using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Testing.Conformance.Artifacts;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactDeletionTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Lost_delete_acknowledgment_preserves_pending_reclamation_until_actual_cleanup(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        using var source = new ShortSource("pending physical reclamation"u8.ToArray());
        var committed = await PublishAsync(driver, source, new(1024));
        var ticket = Success(await driver.Store.ReserveDeleteAsync(new(committed.Stamp), new(), default));
        ValueTask LostAck() => ValueTask.FromException(new IOException(ArtifactTestData.Canary));
        if (driver.LocalControls is { } local) { local.SetObserver("delete.removed", LostAck); }
        else { driver.ObjectControls!.SetObserver("pointer.tombstone", LostAck); }
        Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.DeleteAsync(ticket, new(), default)).Code);
        var pending = Assert.IsType<ArtifactResolution.Removed>(
            Success(await driver.Store.ReconcileAsync(ticket, new(), default))).Receipt;
        Assert.Equal(ArtifactReclamation.Pending, pending.Reclamation);
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await driver.Store.OpenReadAsync(new(committed.Stamp.Identity.Digest), new(), default)).Code);
        var cleaned = Success(await driver.Maintenance.CleanupAsync(new(driver.Identity,
            [new ArtifactCleanupTarget.RemovedIncarnation(committed.Stamp)]), new(), default));
        Assert.Equal(1, cleaned.Completed);
        Assert.Equal(committed.Stamp.Identity.Length, cleaned.ReclaimedBytes);
        var settled = Assert.IsType<ArtifactResolution.Removed>(
            Success(await driver.Store.ReconcileAsync(ticket, new(), default))).Receipt;
        Assert.Equal(pending.ReceiptId, settled.ReceiptId);
        Assert.Equal(pending.Stamp, settled.Stamp);
        Assert.Equal(pending.Outcome, settled.Outcome);
        Assert.Equal(ArtifactReclamation.Reclaimed, settled.Reclamation);
        Assert.Equal(settled, Success(await driver.Store.DeleteAsync(ticket, new(), default)));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Exact_delete_receipts_and_recreation_never_remove_the_new_incarnation(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactDeletionAssertions.ExactReceiptsAndRecreationAsync(
            driver.Store, driver.Maintenance, driver.Identity, default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Live_reference_or_unavailable_reference_authority_denies_removal(string provider)
    {
        var count = 1L;
        var available = true;
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(available, count, Guid.NewGuid())));
        using var source = new ShortSource("protected reference"u8.ToArray());
        var receipt = await PublishAsync(driver, source, new(1024));
        var ticket = Success(await driver.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default));
        Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.DeleteAsync(ticket, new(), default)).Code);
        count = 0;
        available = false;
        Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.DeleteAsync(ticket, new(), default)).Code);
        Assert.Equal("protected reference"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
        available = true;
        Assert.Equal(ArtifactMutationOutcome.Removed, Success(await driver.Store.DeleteAsync(ticket, new(), default)).Outcome);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task A_held_reader_finishes_before_exclusive_deletion_and_later_opens_cannot_enter(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactDeletionAssertions.HeldReaderExcludesDeletionAsync(driver.Store, default);
    }
}
