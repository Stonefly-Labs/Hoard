using System.Security.Cryptography;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.ObjectSemantics;

public sealed partial class ObjectArtifactStore
{
    public ValueTask<ArtifactResult<IArtifactReadSession>> OpenReadAsync(
        ArtifactReadRequest request, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(options);
        return OwnedAsync<IArtifactReadSession>(ArtifactPhase.Read, options.Deadline, ct, async token =>
        {
            if (request.Mode is not ArtifactReadMode.Full) { throw new ObjectOperationException(ArtifactFailureCode.Unsupported); }
            if (request.ExpectedStamp is ArtifactOption<ArtifactStamp>.Some foreign && foreign.Value.Store != Identity)
            { throw new ObjectOperationException(ArtifactFailureCode.InvalidInput); }
            var lease = await EnterTransferAsync(token);
            IArtifactProtectionGuard? guard = null;
            FileStream? stream = null;
            try
            {
                var granted = await initializedWith!.Authority.AcquireAsync(new(Guid.NewGuid(),
                    ArtifactProtectionOperation.Read, Identity, request.Digest, request.ExpectedStamp), options, token);
                if (granted is not ArtifactResult<IArtifactProtectionGuard>.Success acquired)
                { throw new ObjectOperationException(granted is ArtifactResult<IArtifactProtectionGuard>.Failure denied ? denied.Code : ArtifactFailureCode.InternalFailure); }
                guard = acquired.Value;
                ObjectPointer pointer;
                lock (pointerSync)
                {
                    if (!pointers.TryGetValue(request.Digest.Hex, out var observed) || observed.Removed)
                    { throw new ObjectOperationException(ArtifactFailureCode.NotFound); }
                    pointer = observed;
                    if (pointer.Corrupt) { throw new ObjectOperationException(ArtifactFailureCode.CorruptContent); }
                    if (request.ExpectedStamp is ArtifactOption<ArtifactStamp>.Some exact && exact.Value != pointer.Stamp)
                    { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                }
                await faults.ObserveAsync("object.direct");
                stream = OpenCommittedObject(pointer, FileOptions.Asynchronous | FileOptions.SequentialScan);
                await faults.ObserveAsync("object.read-opened");
                token.ThrowIfCancellationRequested();
                var session = new ObjectReadSession(this, pointer, stream, guard, lease);
                lock (pointerSync)
                {
                    if (!pointers.TryGetValue(request.Digest.Hex, out var current)
                        || current.Removed || current.Stamp != pointer.Stamp || current.ObjectId != pointer.ObjectId)
                    { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                    if (current.Corrupt) { throw new ObjectOperationException(ArtifactFailureCode.CorruptContent); }
                    sessions.Add(session);
                }
                session.StartIdleExpiry();
                guard = null;
                stream = null;
                return session;
            }
            catch
            {
                if (stream is not null) { await stream.DisposeAsync(); }
                if (guard is not null) { await guard.DisposeAsync(); }
                lease.Dispose();
                throw;
            }
        }, undelivered: async session =>
        {
            if (await session.CloseAsync(new(), default) is not ArtifactResult<ArtifactShutdown>.Success)
            { throw new ObjectOperationException(ArtifactFailureCode.CleanupIncomplete); }
        });
    }

    private sealed class ObjectReadSession(ObjectArtifactStore owner, ObjectPointer pointer, FileStream file,
        IArtifactProtectionGuard guard, TransferLease lease) : IArtifactReadSession
    {
        private bool copyStarted;
        private readonly object sessionSync = new();
        private readonly Guid closeId = Guid.NewGuid();
        private bool released;
        private bool physicallyReleased;
        private Task? releaseTask;
        private TaskCompletionSource? settlement;
        private readonly long opened = owner.time.GetTimestamp();
        private readonly CancellationTokenSource idleCancellation = new();
        public ArtifactStamp Stamp => pointer.Stamp;
        public void StartIdleExpiry() => _ = ExpireIdleAsync();
        private async Task ExpireIdleAsync()
        {
            try { await Task.Delay(TimeSpan.FromSeconds(30), owner.time, idleCancellation.Token); }
            catch (OperationCanceledException) when (idleCancellation.IsCancellationRequested) { return; }
            lock (sessionSync)
            {
                if (copyStarted || released) { return; }
                released = true;
            }
            await CloseAsync(new(), default);
        }
        public ValueTask<ArtifactResult<ArtifactReadCompletion>> CopyToAsync(
            Stream destination, ArtifactTransferOptions options, CancellationToken ct)
        {
            ArgumentNullException.ThrowIfNull(destination);
            ArgumentNullException.ThrowIfNull(options);
            lock (sessionSync)
            {
                if (!released && owner.time.GetElapsedTime(opened) >= TimeSpan.FromSeconds(30))
                {
                    released = true;
                    _ = CloseAsync(new(), default);
                }
                if (released || copyStarted) { return ValueTask.FromResult(owner.Rejected<ArtifactReadCompletion>(ArtifactFailureCode.Conflict, ArtifactPhase.Read)); }
                idleCancellation.Cancel();
                copyStarted = true;
                settlement = new(TaskCreationOptions.RunContinuationsAsynchronously);
                return owner.OwnedAsync(ArtifactPhase.Read, options.Deadline, ct, async token =>
                {
                    if (!destination.CanWrite) { throw new ObjectOperationException(ArtifactFailureCode.InvalidInput); }
                    using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
                    var buffer = new byte[owner.Bounds.CopyBufferBytes];
                    long copied = 0;
                    while (true)
                    {
                        using var inactivity = CancellationTokenSource.CreateLinkedTokenSource(token);
                        inactivity.CancelAfter(options.Inactivity);
                        var count = await file.ReadAsync(buffer, inactivity.Token);
                        token.ThrowIfCancellationRequested();
                        if (count == 0) { break; }
                        if (count > Stamp.Identity.Length - copied) { return RejectCorruption(); }
                        await destination.WriteAsync(buffer.AsMemory(0, count), inactivity.Token);
                        token.ThrowIfCancellationRequested();
                        hash.AppendData(buffer, 0, count);
                        copied = checked(copied + count);
                        await owner.faults.ObserveAsync("object.read");
                    }
                    var digest = new ArtifactDigest(Convert.ToHexStringLower(hash.GetHashAndReset()));
                    if (copied != Stamp.Identity.Length || digest != Stamp.Identity.Digest) { return RejectCorruption(); }
                    return new ArtifactReadCompletion(Stamp, digest, copied);
                }, onSettled: () => settlement.TrySetResult());
            }
        }

        private ArtifactReadCompletion RejectCorruption()
        {
            throw owner.Quarantine(pointer);
        }

        public async ValueTask<ArtifactResult<ArtifactShutdown>> CloseAsync(ArtifactCleanupOptions options, CancellationToken ct)
        {
            ArgumentNullException.ThrowIfNull(options);
            Task release;
            lock (sessionSync)
            {
                released = true;
                idleCancellation.Cancel();
                var pending = settlement?.Task;
                release = releaseTask ??= Task.Run(async () =>
                {
                    if (pending is not null) { await pending; }
                    await file.DisposeAsync();
                    await guard.DisposeAsync();
                    lease.Dispose();
                    lock (owner.pointerSync) { owner.sessions.Remove(this); }
                    lock (sessionSync)
                    {
                        physicallyReleased = true;
                        owner.unfinishedReadCloses.TryRemove(closeId, out _);
                    }
                });
            }
            try { await release.WaitAsync(options.Deadline, ct); }
            catch (Exception)
            {
                lock (sessionSync)
                {
                    if (!physicallyReleased) { owner.unfinishedReadCloses.TryAdd(closeId, 0); }
                }
                return owner.Rejected<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, retainedOwnership: true);
            }
            return new ArtifactResult<ArtifactShutdown>.Success(new(ArtifactCleanupState.Released, 0, 0, false));
        }

        public async ValueTask DisposeAsync()
        {
            if (await CloseAsync(new(), default) is not ArtifactResult<ArtifactShutdown>.Success)
            { throw new InvalidOperationException("Artifact read retains unsettled resources."); }
        }
    }

    public ValueTask<ArtifactResult<ArtifactStamp>> ValidateAsync(ArtifactCommitEvidence evidence,
        IArtifactProtectionGuard protection, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(evidence);
        ArgumentNullException.ThrowIfNull(protection);
        ArgumentNullException.ThrowIfNull(options);
        return OwnedAsync(ArtifactPhase.Verify, options.Deadline, ct, async token =>
        {
            var scope = protection.Grant.Request;
            if (scope.Operation != ArtifactProtectionOperation.Reference || scope.Store != Identity
                || evidence.Stamp.Store != Identity || scope.Digest != evidence.Stamp.Identity.Digest
                || scope.Stamp is not ArtifactOption<ArtifactStamp>.Some exact || exact.Value != evidence.Stamp)
            { throw new ObjectOperationException(ArtifactFailureCode.Denied); }
            var recognized = await initializedWith!.Authority.RetainAsync(protection, scope, options, token);
            if (recognized is not ArtifactResult<IArtifactProtectionGuard>.Success held)
            { throw new ObjectOperationException(ArtifactFailureCode.Denied); }
            await using var retention = held.Value;
            ObjectPointer pointer;
            lock (pointerSync)
            {
                if (!uploads.TryGetValue(evidence.TicketId, out var upload)
                    || EffectiveNow() >= upload.Ticket.Expires || upload.Receipt?.Evidence is not ArtifactOption<ArtifactCommitEvidence>.Some proof
                    || proof.Value != evidence || !pointers.TryGetValue(scope.Digest.Hex, out var observed)
                    || observed.Removed || observed.Stamp != evidence.Stamp)
                { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                pointer = observed;
                if (pointer.Corrupt) { throw new ObjectOperationException(ArtifactFailureCode.CorruptContent); }
            }
            await faults.ObserveAsync("object.direct");
            using var direct = OpenCommittedObject(pointer);
            if (direct.Length != evidence.Stamp.Identity.Length) { throw Quarantine(pointer); }
            token.ThrowIfCancellationRequested();
            lock (pointerSync)
            {
                if (!pointers.TryGetValue(scope.Digest.Hex, out var current)
                    || current.Removed || current.Stamp != pointer.Stamp || current.ObjectId != pointer.ObjectId)
                { throw new ObjectOperationException(ArtifactFailureCode.Conflict); }
                if (current.Corrupt) { throw new ObjectOperationException(ArtifactFailureCode.CorruptContent); }
                return evidence.Stamp;
            }
        });
    }

    private ObjectOperationException Quarantine(ObjectPointer pointer)
    {
        lock (pointerSync)
        {
            if (pointers.TryGetValue(pointer.Stamp.Identity.Digest.Hex, out var current)
                && !current.Removed && !current.Corrupt
                && current.Stamp == pointer.Stamp && current.ObjectId == pointer.ObjectId)
            {
                pointers[pointer.Stamp.Identity.Digest.Hex] = current with { Corrupt = true };
                listingRevision = checked(listingRevision + 1);
            }
        }
        return new(ArtifactFailureCode.CorruptContent);
    }

    private FileStream OpenCommittedObject(ObjectPointer pointer, FileOptions options = FileOptions.None)
    {
        try { return new(ObjectPath(pointer.ObjectId), FileMode.Open, FileAccess.Read, FileShare.Read, 1, options); }
        catch (FileNotFoundException) { throw Quarantine(pointer); }
    }
}
