using System.Security.Cryptography;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Consumer;

public static class ArtifactConsumer
{
    public static async Task<string[]> CommonJourneyAsync(IArtifactStore store,
        IArtifactEvidenceValidator validator, IArtifactMaintenance maintenance,
        IArtifactCoordinationAuthority authority, ArtifactStoreIdentity identity)
    {
        await RoundTripAsync(store, validator, authority, identity);
        var bytes = "unchanged consumer mutation and maintenance journey"u8.ToArray();
        var digest = new ArtifactDigest(Convert.ToHexStringLower(SHA256.HashData(bytes)));
        var intent = new ArtifactWriteIntent(new ArtifactExpectations(1024,
            new ArtifactOption<ArtifactDigest>.Some(digest), new ArtifactOption<long>.Some(bytes.Length)));
        var ticket = Require(await store.ReserveWriteAsync(intent, new(), default));
        if (Require(await store.ReconcileAsync(ticket, new(), default)) is not ArtifactResolution.Pending pending
            || pending.Ticket != ticket)
        { throw new InvalidOperationException("Artifact consumer pending ticket mismatch."); }
        using var source = new BorrowedSource(bytes);
        var staged = Require(await store.StageAsync(ticket, source, new(), default));
        var renewed = Require(await store.RenewAsync(staged.Owner, new(), default));
        staged = new(renewed, staged.Identity, staged.VerifiedCompletion, staged.PrivateHandle);
        var published = Require(await store.CommitAsync(staged, new(), default));
        if (published.Outcome != ArtifactMutationOutcome.Published
            || Require(await store.ReconcileAsync(ticket, new(), default)) is not ArtifactResolution.Committed committed
            || committed.Receipt != published
            || Require(await store.CommitAsync(staged, new(), default)) != published)
        { throw new InvalidOperationException("Artifact consumer publication reconciliation mismatch."); }

        using var duplicateSource = new BorrowedSource(bytes);
        var duplicateTicket = Require(await store.ReserveWriteAsync(intent, new(), default));
        var duplicateStaged = Require(await store.StageAsync(duplicateTicket, duplicateSource, new(), default));
        var duplicate = Require(await store.CommitAsync(duplicateStaged, new(), default));
        if (duplicate.Outcome != ArtifactMutationOutcome.AlreadyPresentVerified
            || duplicate.Stamp != published.Stamp || duplicate.Ticket == published.Ticket)
        { throw new InvalidOperationException("Artifact consumer verified reuse mismatch."); }

        using var abandonedSource = new BorrowedSource(bytes);
        var abandonedTicket = Require(await store.ReserveWriteAsync(intent, new(), default));
        var abandoned = Require(await store.StageAsync(abandonedTicket, abandonedSource, new(), default));
        Require(await store.AbandonAsync(abandoned.Owner, new(), default));
        if (Require(await store.ReconcileAsync(abandonedTicket, new(), default))
            is not ArtifactResolution.NotCommitted notCommitted || notCommitted.Ticket != abandonedTicket)
        { throw new InvalidOperationException("Artifact consumer abandonment did not settle."); }
        Require(await maintenance.CleanupAsync(new(identity,
            [new ArtifactCleanupTarget.AbandonedStaging(abandoned.Owner)]), new(), default));
        var page = Require(await maintenance.ObserveAsync(
            new(identity, ArtifactRecoveryKind.Committed, pageSize: 1), new(), default));
        if (page.Observations.Length > 1 || page.Consistency != store.Capabilities.Enumeration)
        { throw new InvalidOperationException("Artifact consumer recovery page mismatch."); }
        await VerifyReadAsync(store, published.Stamp, bytes);
        ExpectFailure(await store.OpenReadAsync(new(digest, new ArtifactReadMode.Range(0, 1)), new(), default),
            ArtifactFailureCode.Unsupported);

        var deletionTicket = Require(await store.ReserveDeleteAsync(new(published.Stamp), new(), default));
        var removed = Require(await store.DeleteAsync(deletionTicket, new(), default));
        if (removed.Outcome != ArtifactMutationOutcome.Removed
            || Require(await store.DeleteAsync(deletionTicket, new(), default)) != removed
            || Require(await store.ReconcileAsync(deletionTicket, new(), default)) is not ArtifactResolution.Removed resolution
            || resolution.Receipt != removed)
        { throw new InvalidOperationException("Artifact consumer deletion reconciliation mismatch."); }
        ExpectFailure(await store.OpenReadAsync(new(digest), new(), default), ArtifactFailureCode.NotFound);
        var absentTicket = Require(await store.ReserveDeleteAsync(new(published.Stamp), new(), default));
        if (Require(await store.DeleteAsync(absentTicket, new(), default)).Outcome != ArtifactMutationOutcome.AlreadyAbsent)
        { throw new InvalidOperationException("Artifact consumer absence receipt mismatch."); }

        using var replacementSource = new BorrowedSource(bytes);
        var replacementTicket = Require(await store.ReserveWriteAsync(intent, new(), default));
        var replacementStaged = Require(await store.StageAsync(replacementTicket, replacementSource, new(), default));
        var replacement = Require(await store.CommitAsync(replacementStaged, new(), default));
        if (replacement.Stamp.Identity != published.Stamp.Identity || replacement.Stamp == published.Stamp)
        { throw new InvalidOperationException("Artifact consumer replacement incarnation mismatch."); }
        Require(await maintenance.CleanupAsync(new(identity,
            [new ArtifactCleanupTarget.RemovedIncarnation(published.Stamp)]), new(), default));
        await VerifyReadAsync(store, replacement.Stamp, bytes);
        if (new[] { source, duplicateSource, abandonedSource, replacementSource }
            .Any(input => !input.CanRead || !input.ReachedEof))
        { throw new InvalidOperationException("Artifact consumer borrowed source was disposed or not fully verified."); }

        return
        [
            nameof(IArtifactStore.ReserveWriteAsync), nameof(IArtifactStore.StageAsync),
            nameof(IArtifactStore.RenewAsync), nameof(IArtifactStore.CommitAsync),
            nameof(IArtifactStore.OpenReadAsync), nameof(IArtifactEvidenceValidator.ValidateAsync),
            nameof(IArtifactStore.ReconcileAsync), nameof(IArtifactStore.AbandonAsync),
            nameof(IArtifactStore.ReserveDeleteAsync), nameof(IArtifactStore.DeleteAsync),
            nameof(IArtifactMaintenance.ObserveAsync), nameof(IArtifactMaintenance.CleanupAsync),
            nameof(IArtifactReadSession.CopyToAsync), nameof(IArtifactReadSession.CloseAsync),
            nameof(IArtifactCoordinationAuthority.AcquireAsync), nameof(IArtifactCoordinationAuthority.RetainAsync)
        ];
    }

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
        await using var retained = Require(await authority.RetainAsync(protection, request, new(), default));
        await protection.DisposeAsync();
        if (Require(await validator.ValidateAsync(proof, retained, new(), default)) != receipt.Stamp)
        { throw new InvalidOperationException("Artifact consumer evidence mismatch."); }
        await using var read = Require(await store.OpenReadAsync(new(digest,
            expectedStamp: new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), default));
        using var destination = new MemoryStream();
        var completed = Require(await read.CopyToAsync(destination, new(), default));
        if (Require(await read.CloseAsync(new(), default)).State != ArtifactCleanupState.Released)
        { throw new InvalidOperationException("Artifact consumer read still owns resources."); }
        if (completed.Stamp != receipt.Stamp || completed.Length != bytes.Length
            || !destination.ToArray().AsSpan().SequenceEqual(bytes) || !destination.CanWrite
            || !source.CanRead || !source.ReachedEof)
        { throw new InvalidOperationException("Artifact consumer full read mismatch."); }
        return true;
    }

    private static async Task VerifyReadAsync(IArtifactStore store, ArtifactStamp stamp, byte[] bytes)
    {
        await using var read = Require(await store.OpenReadAsync(new(stamp.Identity.Digest,
            expectedStamp: new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), default));
        using var destination = new MemoryStream();
        var completion = Require(await read.CopyToAsync(destination, new(), default));
        if (Require(await read.CloseAsync(new(), default)).State != ArtifactCleanupState.Released)
        { throw new InvalidOperationException("Artifact consumer read still owns resources."); }
        if (completion.Stamp != stamp || completion.Length != bytes.Length || !destination.CanWrite
            || !destination.ToArray().AsSpan().SequenceEqual(bytes))
        { throw new InvalidOperationException("Artifact consumer protected read mismatch."); }
    }

    private static void ExpectFailure<T>(ArtifactResult<T> result, ArtifactFailureCode code) where T : notnull
    {
        if (result is not ArtifactResult<T>.Failure failure || failure.Code != code)
        { throw new InvalidOperationException("Artifact consumer expected rejection mismatch."); }
    }

    private static T Require<T>(ArtifactResult<T> result) where T : notnull
        => result is ArtifactResult<T>.Success success ? success.Value
            : throw new InvalidOperationException(result is ArtifactResult<T>.Failure failed
                ? $"Artifact consumer operation failed ({failed.Code})." : "Unknown artifact consumer result.");

    private sealed class BorrowedSource(byte[] bytes) : Stream
    {
        private int position;
        private bool disposed;
        public bool ReachedEof { get; private set; }
        public override bool CanRead => !disposed;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException();
        public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            ObjectDisposedException.ThrowIf(disposed, this);
            cancellationToken.ThrowIfCancellationRequested();
            var count = Math.Min(buffer.Length, bytes.Length - position);
            bytes.AsMemory(position, count).CopyTo(buffer);
            position += count;
            if (count == 0) { ReachedEof = true; }
            return ValueTask.FromResult(count);
        }
        protected override void Dispose(bool disposing) { disposed = true; base.Dispose(disposing); }
        public override void Flush() => throw new NotSupportedException();
        public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    }
}
