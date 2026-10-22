using Hoard.Abstractions.Storage;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactPublicationRaceTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Equivalent_concurrent_writers_keep_one_stamp_and_distinct_receipts(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var bytes = "equivalent writers"u8.ToArray();
        using var first = new ShortSource(bytes);
        using var second = new ShortSource(bytes);
        var a = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var b = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staged = await Task.WhenAll(driver.Store.StageAsync(a, first, new(), default).AsTask(),
            driver.Store.StageAsync(b, second, new(), default).AsTask());
        var commits = await Task.WhenAll(staged.Select(value => driver.Store.CommitAsync(Success(value), new(), default).AsTask()));
        var receipts = commits.Select(Success).ToArray();
        Assert.True(first.EofObserved && second.EofObserved);
        Assert.Equal(receipts[0].Stamp, receipts[1].Stamp);
        Assert.NotEqual(receipts[0].ReceiptId, receipts[1].ReceiptId);
        Assert.Single(receipts, receipt => receipt.Outcome == ArtifactMutationOutcome.Published);
        Assert.Single(receipts, receipt => receipt.Outcome == ArtifactMutationOutcome.AlreadyPresentVerified);
        Assert.Equal(bytes, await ReadAsync(driver, receipts[0].Stamp));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Corrupt_existing_bytes_are_not_overwritten_or_reused(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var bytes = "preserve corrupt evidence"u8.ToArray();
        using var original = new ShortSource(bytes);
        var receipt = await PublishAsync(driver, original, new(1024));
        driver.DamageOnlyPayload(truncate: false);
        using var duplicate = new ShortSource(bytes);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staged = Success(await driver.Store.StageAsync(ticket, duplicate, new(), default));
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.CommitAsync(staged, new(), default)).Code);
        Assert.True(duplicate.EofObserved);
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Code);
    }
}
