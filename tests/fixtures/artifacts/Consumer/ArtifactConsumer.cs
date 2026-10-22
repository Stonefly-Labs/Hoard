using System.Security.Cryptography;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Consumer;

public static class ArtifactConsumer
{
    public static async Task<bool> RoundTripAsync(IArtifactStore store, IArtifactEvidenceValidator validator,
        IArtifactCoordinationAuthority authority, ArtifactStoreIdentity identity)
    {
        var bytes = "unchanged package-only artifact consumer"u8.ToArray();
        var digest = new ArtifactDigest(Convert.ToHexStringLower(SHA256.HashData(bytes)));
        using var source = new BorrowedSource(bytes);
        var intent = new ArtifactWriteIntent(new ArtifactExpectations(1024,
            new ArtifactOption<ArtifactDigest>.Some(digest), new ArtifactOption<long>.Some(bytes.Length)));
        var ticket = Require(await store.ReserveWriteAsync(intent, new(), default));
        var staged = Require(await store.StageAsync(ticket, source, new(), default));
        var receipt = Require(await store.CommitAsync(staged, new(), default));
        var proof = receipt.Evidence is ArtifactOption<ArtifactCommitEvidence>.Some evidence
            ? evidence.Value : throw new InvalidOperationException("Artifact consumer received no verified evidence.");
        var request = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Reference,
            identity, digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        await using var protection = Require(await authority.AcquireAsync(request, new(), default));
        if (Require(await validator.ValidateAsync(proof, protection, new(), default)) != receipt.Stamp)
        { throw new InvalidOperationException("Artifact consumer evidence mismatch."); }
        await using var read = Require(await store.OpenReadAsync(new(digest,
            expectedStamp: new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), default));
        using var destination = new MemoryStream();
        var completed = Require(await read.CopyToAsync(destination, new(), default));
        if (completed.Stamp != receipt.Stamp || completed.Length != bytes.Length
            || !destination.ToArray().AsSpan().SequenceEqual(bytes) || !source.CanRead)
        { throw new InvalidOperationException("Artifact consumer full read mismatch."); }
        return true;
    }

    private static T Require<T>(ArtifactResult<T> result) where T : notnull
        => result is ArtifactResult<T>.Success success ? success.Value
            : throw new InvalidOperationException(result is ArtifactResult<T>.Failure failed
                ? $"Artifact consumer operation failed ({failed.Code})." : "Unknown artifact consumer result.");

    private sealed class BorrowedSource(byte[] bytes) : Stream
    {
        private int position;
        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException();
        public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var count = Math.Min(buffer.Length, bytes.Length - position);
            bytes.AsMemory(position, count).CopyTo(buffer);
            position += count;
            return ValueTask.FromResult(count);
        }
        public override void Flush() => throw new NotSupportedException();
        public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    }
}
