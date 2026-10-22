using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactDeletionTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Exact_delete_receipts_and_recreation_never_remove_the_new_incarnation(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        var bytes = "delete then recreate"u8.ToArray();
        using var first = new ShortSource(bytes);
        var original = await PublishAsync(driver, first, new(1024));
        var ticket = Success(await driver.Store.ReserveDeleteAsync(new(original.Stamp), new(), default));
        var removed = Success(await driver.Store.DeleteAsync(ticket, new(), default));
        Assert.Equal(ArtifactMutationOutcome.Removed, removed.Outcome);
        Assert.Equal(removed, Success(await driver.Store.DeleteAsync(ticket, new(), default)));
        Assert.Equal(removed, Assert.IsType<ArtifactResolution.Removed>(
            Success(await driver.Store.ReconcileAsync(ticket, new(), default))).Receipt);
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await driver.Store.OpenReadAsync(new(original.Stamp.Identity.Digest), new(), default)).Code);
        var repeat = Success(await driver.Store.ReserveDeleteAsync(new(original.Stamp), new(), default));
        Assert.Equal(ArtifactMutationOutcome.AlreadyAbsent, Success(await driver.Store.DeleteAsync(repeat, new(), default)).Outcome);
        using var next = new ShortSource(bytes);
        var recreated = await PublishAsync(driver, next, new(1024));
        Assert.NotEqual(original.Stamp.Incarnation, recreated.Stamp.Incarnation);
        var stale = Success(await driver.Store.ReserveDeleteAsync(new(original.Stamp), new(), default));
        Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.DeleteAsync(stale, new(), default)).Code);
        var cleanup = new ArtifactCleanupRequest(driver.Identity, [new ArtifactCleanupTarget.RemovedIncarnation(original.Stamp)]);
        Success(await driver.Maintenance.CleanupAsync(cleanup, new(), default));
        Assert.Equal(bytes, await ReadAsync(driver, recreated.Stamp));
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
        var bytes = "reader exclusion"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(driver, source, new(1024));
        var reader = Success(await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default));
        var ticket = Success(await driver.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default));
        var deletion = driver.Store.DeleteAsync(ticket, new(), default).AsTask();
        using var destination = new MemoryStream();
        Success(await reader.CopyToAsync(destination, new(), default));
        Assert.False(deletion.IsCompleted);
        Assert.Equal(bytes, destination.ToArray());
        await reader.DisposeAsync();
        Assert.Equal(ArtifactMutationOutcome.Removed, Success(await deletion).Outcome);
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Code);
    }
}
