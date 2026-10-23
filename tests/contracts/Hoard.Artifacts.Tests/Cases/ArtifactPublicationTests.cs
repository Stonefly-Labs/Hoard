using System.Security.Cryptography;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactPublicationTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Empty_content_and_true_absence_are_distinct(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var empty = new ArtifactDigest(Convert.ToHexStringLower(SHA256.HashData([])));
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await driver.Store.OpenReadAsync(new(empty), new(), default)).Code);
        using var source = new ShortSource([]);
        var receipt = await PublishAsync(driver, source, new(1));
        Assert.Equal(empty, receipt.Stamp.Identity.Digest);
        Assert.Equal(0, receipt.Stamp.Identity.Length);
        Assert.True(source.EofObserved);
        Assert.Empty(await ReadAsync(driver, receipt.Stamp));
        Assert.IsType<ArtifactResolution.Committed>(Success(
            await driver.Store.ReconcileAsync(receipt.Ticket, new(), default)));
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await driver.Store.OpenReadAsync(new(new ArtifactDigest(new string('a', 64))), new(), default)).Code);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Empty_unknown_length_and_positive_short_reads_require_real_eof(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        foreach (var bytes in new[] { Array.Empty<byte>(), "complete artifact bytes"u8.ToArray() })
        {
            using var source = new ShortSource(bytes);
            var receipt = await PublishAsync(driver, source, new(1024));
            Assert.True(source.EofObserved);
            Assert.False(source.WasDisposed);
            Assert.Equal(bytes.Length, receipt.Stamp.Identity.Length);
            Assert.Equal(new ArtifactDigest(Convert.ToHexStringLower(SHA256.HashData(bytes))), receipt.Stamp.Identity.Digest);
            Assert.Equal(bytes, await ReadAsync(driver, receipt.Stamp));
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Every_expectation_is_checked_and_declared_length_does_not_replace_eof(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var bytes = "all expectations are mandatory"u8.ToArray();
        var digest = new ArtifactDigest(Convert.ToHexStringLower(SHA256.HashData(bytes)));
        var checksum = SHA512.HashData(bytes);
        var matching = new ArtifactExpectations(1024, new ArtifactOption<ArtifactDigest>.Some(digest),
            new ArtifactOption<long>.Some(bytes.Length),
            new ArtifactOption<ArtifactChecksumExpectation>.Some(new("sha512", checksum)));
        using var good = new ShortSource(bytes);
        var receipt = await PublishAsync(driver, good, matching);
        Assert.True(good.EofObserved);
        foreach (var expectations in new[]
        {
            new ArtifactExpectations(1024, new ArtifactOption<ArtifactDigest>.Some(new ArtifactDigest(new string('0', 64)))),
            new ArtifactExpectations(1024, exactLength: new ArtifactOption<long>.Some(bytes.Length - 1)),
            new ArtifactExpectations(1024, exactLength: new ArtifactOption<long>.Some(bytes.Length + 1)),
            new ArtifactExpectations(1024, checksum: new ArtifactOption<ArtifactChecksumExpectation>.Some(new("sha512", new byte[64])))
        })
        {
            using var source = new ShortSource(bytes);
            var ticket = Success(await driver.Store.ReserveWriteAsync(new(expectations), new(), default));
            var result = await driver.Store.StageAsync(ticket, source, new(), default);
            Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(result);
            Assert.False(source.WasDisposed);
            Assert.Equal(bytes, await ReadAsync(driver, receipt.Stamp));
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Unsupported_checksum_and_range_reject_before_storage_or_stream_io(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        foreach (var (algorithm, size, code) in new[]
        {
            ("unknown", 1, ArtifactFailureCode.Unsupported),
            ("sha512", 63, ArtifactFailureCode.InvalidInput)
        })
        {
            var intent = new ArtifactWriteIntent(new ArtifactExpectations(1024,
                checksum: new ArtifactOption<ArtifactChecksumExpectation>.Some(new(algorithm, new byte[size]))));
            Assert.Equal(code, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await driver.Store.ReserveWriteAsync(intent, new(), default)).Code);
        }
        var digest = new ArtifactDigest(new string('a', 64));
        Assert.Equal(ArtifactFailureCode.Unsupported, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await driver.Store.OpenReadAsync(new(digest, new ArtifactReadMode.Range(0, 1)), new(), default)).Code);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Staging_is_private_until_complete_verified_commit(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var bytes = "no staged prefix is committed"u8.ToArray();
        var digest = new ArtifactDigest(Convert.ToHexStringLower(SHA256.HashData(bytes)));
        await using var barrier = new ArtifactTestBarrier("prefix");
        SetObserver(driver, "stage.prefix", "multipart.part", () => new(barrier.HoldAsync()));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource(bytes);
        var staging = driver.Store.StageAsync(ticket, source, new(), default).AsTask();
        await barrier.Entered;
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await driver.Store.OpenReadAsync(new(digest), new(), default)).Code);
        barrier.Release();
        var staged = Success(await staging);
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await driver.Store.OpenReadAsync(new(digest), new(), default)).Code);
        var receipt = Success(await driver.Store.CommitAsync(staged, new(), default));
        Assert.Equal(bytes, await ReadAsync(driver, receipt.Stamp));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Submitted_duplicates_are_fully_verified_and_keep_one_immutable_incarnation(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var bytes = "duplicate verification"u8.ToArray();
        using var first = new ShortSource(bytes);
        var original = await PublishAsync(driver, first, new(1024));
        using var duplicate = new ShortSource(bytes);
        var reused = await PublishAsync(driver, duplicate, new(1024));
        Assert.True(duplicate.EofObserved);
        Assert.Equal(bytes.Length, duplicate.BytesRead);
        Assert.Equal(ArtifactMutationOutcome.AlreadyPresentVerified, reused.Outcome);
        Assert.Equal(original.Stamp, reused.Stamp);
        Assert.NotEqual(original.ReceiptId, reused.ReceiptId);
        using var wrong = new ShortSource("wrong bytes"u8.ToArray());
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024,
            new ArtifactOption<ArtifactDigest>.Some(original.Stamp.Identity.Digest))), new(), default));
        Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await driver.Store.StageAsync(ticket, wrong, new(), default));
        Assert.Equal(bytes, await ReadAsync(driver, original.Stamp));
    }

    internal static T Success<T>(ArtifactResult<T> result) where T : notnull
        => Assert.IsType<ArtifactResult<T>.Success>(result).Value;

    internal static async Task<ArtifactMutationReceipt> PublishAsync(
        ArtifactProviderDriver driver, Stream source, ArtifactExpectations expectations)
    {
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(expectations), new(), default));
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        return Success(await driver.Store.CommitAsync(staged, new(), default));
    }

    internal static async Task<byte[]> ReadAsync(ArtifactProviderDriver driver, ArtifactStamp stamp)
    {
        await using var session = Success(await driver.Store.OpenReadAsync(
            new(stamp.Identity.Digest, expectedStamp: new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), default));
        using var destination = new MemoryStream();
        var completion = Success(await session.CopyToAsync(destination, new(), default));
        Assert.Equal(stamp, completion.Stamp);
        Assert.Equal(stamp.Identity.Length, completion.Length);
        return destination.ToArray();
    }

    internal static void SetObserver(ArtifactProviderDriver driver, string localPoint, string objectPoint, Func<ValueTask> observer)
    {
        if (driver.LocalControls is { } local) { local.SetObserver(localPoint, observer); }
        else { driver.ObjectControls!.SetObserver(objectPoint, observer); }
    }

    internal sealed class ShortSource(byte[] bytes) : Stream
    {
        private int position;
        public bool EofObserved { get; private set; }
        public bool WasDisposed { get; private set; }
        public int BytesRead => position;
        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException();
        public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var count = Math.Min(Math.Min(buffer.Length, 3), bytes.Length - position);
            bytes.AsMemory(position, count).CopyTo(buffer);
            position += count;
            EofObserved |= count == 0;
            return ValueTask.FromResult(count);
        }
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
        public override void Flush() => throw new NotSupportedException();
        public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    }
}
