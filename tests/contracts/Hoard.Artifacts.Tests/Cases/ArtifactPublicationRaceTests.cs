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
        var admitted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var arrivals = 0;
        ValueTask Hold()
        {
            if (Interlocked.Increment(ref arrivals) == 2) { admitted.TrySetResult(); }
            return new(release.Task);
        }
        SetObserver(driver, "publish.admitted", "object.publication-admitted", Hold);
        var committing = Task.WhenAll(staged.Select(value => driver.Store.CommitAsync(Success(value), new(), default).AsTask()));
        try
        {
            await admitted.Task.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.False(committing.IsCompleted);
        }
        finally { release.TrySetResult(); }
        var commits = await committing;
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
    public async Task Conflicting_staged_length_cannot_replace_valid_content_or_its_stamp(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var bytes = "valid content survives a conflicting claim"u8.ToArray();
        using var source = new ShortSource(bytes);
        var original = await PublishAsync(driver, source, new(1024));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var duplicate = new ShortSource(bytes);
        var staged = Success(await driver.Store.StageAsync(ticket, duplicate, new(), default));
        var conflicting = new ArtifactStagedWrite(staged.Owner,
            new(staged.Identity.Digest, staged.Identity.Length + 1), staged.VerifiedCompletion, staged.PrivateHandle);
        Assert.Equal(ArtifactFailureCode.InvalidInput, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.CommitAsync(conflicting, new(), default)).Code);
        var reused = Success(await driver.Store.CommitAsync(staged, new(), default));
        Assert.Equal(original.Stamp, reused.Stamp);
        Assert.Equal(ArtifactMutationOutcome.AlreadyPresentVerified, reused.Outcome);
        Assert.Equal(bytes, await ReadAsync(driver, original.Stamp));
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
