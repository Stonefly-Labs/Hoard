using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactReconciliationTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Finalized_mutation_retries_preserve_expiry_and_foreign_ticket_failures(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock,
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("expired mutations"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        var receipt = Success(await driver.Store.CommitAsync(staged, new(), default));
        var deletion = Success(await driver.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default));
        Success(await driver.Store.DeleteAsync(deletion, new(), default));
        var altered = new ArtifactOperationTicket(deletion.Store, deletion.Id, deletion.Kind,
            deletion.Issued, deletion.Expires, new string('a', 64));
        Assert.Equal(ArtifactFailureCode.InvalidInput, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.DeleteAsync(altered, new(), default)).Code);
        clock.Advance(TimeSpan.FromHours(24));
        Assert.Equal(ArtifactFailureCode.ReconciliationExpired, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.CommitAsync(staged, new(), default)).Code);
        Assert.Equal(ArtifactFailureCode.ReconciliationExpired, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.DeleteAsync(deletion, new(), default)).Code);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Acknowledged_commit_reconciles_and_retries_one_identical_receipt_without_new_source(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        using var source = new ShortSource("exact receipt retry"u8.ToArray());
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        var original = Success(await driver.Store.CommitAsync(staged, new(), default));
        var resolved = Assert.IsType<ArtifactResolution.Committed>(
            Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        Assert.Equal(original, resolved.Receipt);
        Assert.Equal(original, Success(await driver.Store.CommitAsync(staged, new(), default)));
        using var extraSource = new ShortSource("must not read decided input"u8.ToArray());
        Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await driver.Store.StageAsync(ticket, extraSource, new(), default)).Code);
        Assert.Equal(0, extraSource.BytesRead);
        var changedIntent = new ArtifactOperationTicket(ticket.Store, ticket.Id, ticket.Kind,
            ticket.Issued, ticket.Expires, new string('f', 64));
        Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(await driver.Store.ReconcileAsync(changedIntent, new(), default));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Lost_acknowledgment_never_becomes_rollback_or_another_publication(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        using var source = new ShortSource("lost publication acknowledgment"u8.ToArray());
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        SetObserver(driver, "publish.decided", "pointer.selected",
            () => ValueTask.FromException(new IOException(ArtifactTestData.Canary)));
        Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.CommitAsync(staged, new(), default)).Code);
        var resolved = Assert.IsType<ArtifactResolution.Committed>(
            Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        Assert.Equal(ArtifactMutationOutcome.Published, resolved.Receipt.Outcome);
        Assert.Equal("lost publication acknowledgment"u8.ToArray(), await ReadAsync(driver, resolved.Receipt.Stamp));
        Assert.Equal(resolved.Receipt, Success(await driver.Store.CommitAsync(staged, new(), default)));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Expired_history_cannot_be_revived_by_clock_rollback_or_foreign_epoch(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        using var source = new ShortSource("history expiry"u8.ToArray());
        var receipt = await PublishAsync(driver, source, new(1024));
        clock.Advance(TimeSpan.FromHours(24));
        Assert.Equal(ArtifactFailureCode.ReconciliationExpired, Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
            await driver.Store.ReconcileAsync(receipt.Ticket, new(), default)).Code);
        clock.SetUtc(receipt.Ticket.Issued.ToUnixTimeMilliseconds());
        Assert.Equal(ArtifactFailureCode.ReconciliationExpired, Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
            await driver.Store.ReconcileAsync(receipt.Ticket, new(), default)).Code);
        var foreign = new ArtifactOperationTicket(new ArtifactStoreIdentity(driver.Identity.ProviderModuleId,
            driver.Identity.InstanceId, Guid.NewGuid()), receipt.Ticket.Id, receipt.Ticket.Kind,
            receipt.Ticket.Issued, receipt.Ticket.Expires, receipt.Ticket.IntentFingerprint);
        Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(await driver.Store.ReconcileAsync(foreign, new(), default));
    }
}
