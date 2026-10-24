using System.Security.Cryptography;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactPublicationAssertions
{
    public static async Task EmptyContentAndAbsenceAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        var empty = new ArtifactDigest(Convert.ToHexStringLower(SHA256.HashData([])));
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(empty), new(), cancellationToken)).Code);
        using var source = new ShortSource([]);
        var receipt = await PublishAsync(store, source, new(1), cancellationToken);
        Assert.Equal(empty, receipt.Stamp.Identity.Digest);
        Assert.Equal(0, receipt.Stamp.Identity.Length);
        Assert.True(source.EofObserved);
        Assert.Empty(await ReadAsync(store, receipt.Stamp, cancellationToken));
        Assert.IsType<ArtifactResolution.Committed>(Success(
            await store.ReconcileAsync(receipt.Ticket, new(), cancellationToken)));
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(new ArtifactDigest(new string('a', 64))), new(), cancellationToken)).Code);
    }

    public static async Task UnknownLengthAndRealEofAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        foreach (var bytes in new[] { Array.Empty<byte>(), "complete artifact bytes"u8.ToArray() })
        {
            using var source = new ShortSource(bytes);
            var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
            Assert.True(source.EofObserved);
            Assert.False(source.WasDisposed);
            Assert.Equal(bytes.Length, receipt.Stamp.Identity.Length);
            Assert.Equal(new ArtifactDigest(Convert.ToHexStringLower(SHA256.HashData(bytes))), receipt.Stamp.Identity.Digest);
            Assert.Equal(bytes, await ReadAsync(store, receipt.Stamp, cancellationToken));
        }
    }

    public static async Task EveryExpectationAndEofAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        var bytes = "all expectations are mandatory"u8.ToArray();
        var digest = new ArtifactDigest(Convert.ToHexStringLower(SHA256.HashData(bytes)));
        var checksum = SHA512.HashData(bytes);
        var matching = new ArtifactExpectations(1024, new ArtifactOption<ArtifactDigest>.Some(digest),
            new ArtifactOption<long>.Some(bytes.Length),
            new ArtifactOption<ArtifactChecksumExpectation>.Some(new("sha512", checksum)));
        using var good = new ShortSource(bytes);
        var receipt = await PublishAsync(store, good, matching, cancellationToken);
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
            var ticket = Success(await store.ReserveWriteAsync(new(expectations), new(), cancellationToken));
            var result = await store.StageAsync(ticket, source, new(), cancellationToken);
            Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(result);
            Assert.False(source.WasDisposed);
            Assert.Equal(bytes, await ReadAsync(store, receipt.Stamp, cancellationToken));
        }
    }

    public static async Task UnsupportedChecksumAndRangeAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        foreach (var (algorithm, size, code) in new[]
        {
            ("unknown", 1, ArtifactFailureCode.Unsupported),
            ("sha512", 63, ArtifactFailureCode.InvalidInput)
        })
        {
            var intent = new ArtifactWriteIntent(new ArtifactExpectations(1024,
                checksum: new ArtifactOption<ArtifactChecksumExpectation>.Some(new(algorithm, new byte[size]))));
            Assert.Equal(code, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await store.ReserveWriteAsync(intent, new(), cancellationToken)).Code);
        }
        var digest = new ArtifactDigest(new string('a', 64));
        Assert.Equal(ArtifactFailureCode.Unsupported, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(digest, new ArtifactReadMode.Range(0, 1)), new(), cancellationToken)).Code);
    }

    public static async Task VerifiedDuplicatesAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        var bytes = "duplicate verification"u8.ToArray();
        using var first = new ShortSource(bytes);
        var original = await PublishAsync(store, first, new(1024), cancellationToken);
        using var duplicate = new ShortSource(bytes);
        var reused = await PublishAsync(store, duplicate, new(1024), cancellationToken);
        Assert.True(duplicate.EofObserved);
        Assert.Equal(bytes.Length, duplicate.BytesRead);
        Assert.Equal(ArtifactMutationOutcome.AlreadyPresentVerified, reused.Outcome);
        Assert.Equal(original.Stamp, reused.Stamp);
        Assert.NotEqual(original.ReceiptId, reused.ReceiptId);
        using var wrong = new ShortSource("wrong bytes"u8.ToArray());
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024,
            new ArtifactOption<ArtifactDigest>.Some(original.Stamp.Identity.Digest))), new(), cancellationToken));
        Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await store.StageAsync(ticket, wrong, new(), cancellationToken));
        Assert.Equal(bytes, await ReadAsync(store, original.Stamp, cancellationToken));
    }

    public static async Task PrivateStagingAsync(
        IArtifactStore store, Func<CancellationToken, Task> waitForPrefix, Action releasePrefix,
        CancellationToken cancellationToken)
    {
        var bytes = "no staged prefix is committed"u8.ToArray();
        var digest = new ArtifactDigest(Convert.ToHexStringLower(SHA256.HashData(bytes)));
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource(bytes);
        var staging = store.StageAsync(ticket, source, new(), cancellationToken).AsTask();
        await waitForPrefix(cancellationToken);
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(digest), new(), cancellationToken)).Code);
        releasePrefix();
        var staged = Success(await staging);
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(digest), new(), cancellationToken)).Code);
        var receipt = Success(await store.CommitAsync(staged, new(), cancellationToken));
        Assert.Equal(bytes, await ReadAsync(store, receipt.Stamp, cancellationToken));
    }

    public static async Task ConcurrentEquivalentWritersAsync(
        IArtifactStore store, Action<Func<ValueTask>> observeAdmission, CancellationToken cancellationToken)
    {
        var bytes = "equivalent writers"u8.ToArray();
        using var first = new ShortSource(bytes);
        using var second = new ShortSource(bytes);
        var a = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var b = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = await Task.WhenAll(store.StageAsync(a, first, new(), cancellationToken).AsTask(),
            store.StageAsync(b, second, new(), cancellationToken).AsTask());
        var admitted = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var arrivals = 0;
        ValueTask Hold()
        {
            if (Interlocked.Increment(ref arrivals) == 2) { admitted.TrySetResult(); }
            return new(release.Task);
        }
        observeAdmission(Hold);
        var committing = Task.WhenAll(staged.Select(value => store.CommitAsync(Success(value), new(), cancellationToken).AsTask()));
        try
        {
            await admitted.Task.WaitAsync(TimeSpan.FromSeconds(2), cancellationToken);
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
        Assert.Equal(bytes, await ReadAsync(store, receipts[0].Stamp, cancellationToken));
    }

    public static async Task ConflictingStagedLengthAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        var bytes = "valid content survives a conflicting claim"u8.ToArray();
        using var source = new ShortSource(bytes);
        var original = await PublishAsync(store, source, new(1024), cancellationToken);
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var duplicate = new ShortSource(bytes);
        var staged = Success(await store.StageAsync(ticket, duplicate, new(), cancellationToken));
        var conflicting = new ArtifactStagedWrite(staged.Owner,
            new(staged.Identity.Digest, staged.Identity.Length + 1), staged.VerifiedCompletion, staged.PrivateHandle);
        Assert.Equal(ArtifactFailureCode.InvalidInput, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.CommitAsync(conflicting, new(), cancellationToken)).Code);
        var reused = Success(await store.CommitAsync(staged, new(), cancellationToken));
        Assert.Equal(original.Stamp, reused.Stamp);
        Assert.Equal(ArtifactMutationOutcome.AlreadyPresentVerified, reused.Outcome);
        Assert.Equal(bytes, await ReadAsync(store, original.Stamp, cancellationToken));
    }

    public static async Task CorruptExistingContentAsync(
        IArtifactStore store, Action damagePayload, Action<byte[]> restorePayload, CancellationToken cancellationToken)
    {
        var bytes = "preserve corrupt evidence"u8.ToArray();
        using var original = new ShortSource(bytes);
        var receipt = await PublishAsync(store, original, new(1024), cancellationToken);
        damagePayload();
        using var duplicate = new ShortSource(bytes);
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, duplicate, new(), cancellationToken));
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.CommitAsync(staged, new(), cancellationToken)).Code);
        Assert.True(duplicate.EofObserved);
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)).Code);
        restorePayload(bytes);
        Success(await store.AbandonAsync(staged.Owner, new(), cancellationToken));
        await ArtifactEvidenceAssertions.QuarantineIsPermanentAsync(store, receipt, bytes, cancellationToken);
    }

    public static async Task<ArtifactMutationReceipt> PublishAsync(
        IArtifactStore store, Stream source, ArtifactExpectations expectations, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(expectations), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        return Success(await store.CommitAsync(staged, new(), cancellationToken));
    }

    public static async Task<byte[]> ReadAsync(
        IArtifactStore store, ArtifactStamp stamp, CancellationToken cancellationToken)
    {
        await using var session = Success(await store.OpenReadAsync(
            new(stamp.Identity.Digest, expectedStamp: new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), cancellationToken));
        using var destination = new MemoryStream();
        var completion = Success(await session.CopyToAsync(destination, new(), cancellationToken));
        Assert.Equal(stamp, completion.Stamp);
        Assert.Equal(stamp.Identity.Length, completion.Length);
        return destination.ToArray();
    }

    internal static T Success<T>(ArtifactResult<T> result) where T : notnull =>
        Assert.IsType<ArtifactResult<T>.Success>(result).Value;

    public class ShortSource(byte[] bytes) : Stream
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
