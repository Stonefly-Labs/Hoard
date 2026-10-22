using Hoard.Abstractions.Storage;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactReadVerificationTests
{
    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence(string provider, bool truncate)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        using var source = new ShortSource("detect stored corruption"u8.ToArray());
        var receipt = await PublishAsync(driver, source, new(1024));
        driver.DamageOnlyPayload(truncate);
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        await using (var session = Success(await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)))
        {
            using var destination = new MemoryStream();
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await session.CopyToAsync(destination, new(), default)).Code);
            Assert.True(destination.CanWrite);
        }
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Code);
        var scope = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Reference,
            driver.Identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        await using var guard = Success(await driver.Authority.AcquireAsync(scope, new(), default));
        Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(await driver.Validator.ValidateAsync(proof, guard, new(), default));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Destination_failure_and_second_copy_never_return_verified_completion_or_dispose_borrowed_streams(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        using var source = new ShortSource("borrowed streams"u8.ToArray());
        var receipt = await PublishAsync(driver, source, new(1024));
        await using var session = Success(await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default));
        using var destination = new FailingDestination();
        Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(await session.CopyToAsync(destination, new(), default));
        Assert.False(destination.WasDisposed);
        Assert.False(source.WasDisposed);
        Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(await session.CopyToAsync(Stream.Null, new(), default));
    }

    private sealed class FailingDestination : MemoryStream
    {
        public bool WasDisposed { get; private set; }
        public override ValueTask WriteAsync(ReadOnlyMemory<byte> buffer, CancellationToken cancellationToken = default)
            => ValueTask.FromException(new IOException(ArtifactTestData.Canary));
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
    }
}
