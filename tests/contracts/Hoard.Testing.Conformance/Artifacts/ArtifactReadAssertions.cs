using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactReadAssertions
{
    public static async Task DamagedReadAsync(
        IArtifactStore store, IArtifactEvidenceValidator validator, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, bool truncate, Func<ValueTask<byte[]>> capture,
        Func<bool, ValueTask> damage, Func<byte[], ValueTask> restore, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("detect stored corruption"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        var bytes = await capture();
        await damage(truncate);
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        await using (var session = Success(await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)))
        {
            using var destination = new MemoryStream();
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await session.CopyToAsync(destination, new(), cancellationToken)).Code);
            Assert.True(destination.CanWrite);
        }
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)).Code);
        var scope = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Reference,
            identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        await using var guard = Success(await authority.AcquireAsync(scope, new(), cancellationToken));
        Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(await validator.ValidateAsync(proof, guard, new(), cancellationToken));
        await restore(bytes);
        await guard.DisposeAsync();
        await ArtifactEvidenceAssertions.QuarantineIsPermanentAsync(store, receipt, bytes, cancellationToken);
    }

    public static async Task DestinationFailureAsync(
        IArtifactStore store, string failureMessage, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("borrowed streams"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        await using var session = Success(await store.OpenReadAsync(
            new(receipt.Stamp.Identity.Digest), new(), cancellationToken));
        using var destination = new FailingDestination(failureMessage);
        Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
            await session.CopyToAsync(destination, new(), cancellationToken));
        Assert.False(destination.WasDisposed);
        Assert.False(source.WasDisposed);
        Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
            await session.CopyToAsync(Stream.Null, new(), cancellationToken));
    }

    private sealed class FailingDestination(string failureMessage) : MemoryStream
    {
        public bool WasDisposed { get; private set; }
        public override ValueTask WriteAsync(ReadOnlyMemory<byte> buffer, CancellationToken cancellationToken = default) =>
            ValueTask.FromException(new IOException(failureMessage));
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
    }
}
