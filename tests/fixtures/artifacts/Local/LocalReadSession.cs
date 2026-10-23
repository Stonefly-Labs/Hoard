using System.Security.Cryptography;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Artifacts.Local;

public sealed partial class LocalArtifactStore
{
    public ValueTask<ArtifactResult<IArtifactReadSession>> OpenReadAsync(
        ArtifactReadRequest request, ArtifactCallOptions options, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(options);
        return ExecuteAsync<IArtifactReadSession>(ArtifactPhase.Read, options.Deadline, ct, async token =>
        {
            if (request.Mode is not ArtifactReadMode.Full) { throw new LocalStateException(ArtifactFailureCode.Unsupported); }
            if (request.ExpectedStamp is ArtifactOption<ArtifactStamp>.Some foreign && foreign.Value.Store != StoreIdentity)
            { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
            var slot = await AdmitAsync(token);
            IArtifactProtectionGuard? protection = null;
            FileStream? input = null;
            try
            {
                var admitted = await configuration!.Authority.AcquireAsync(new(Guid.NewGuid(), ArtifactProtectionOperation.Read,
                    StoreIdentity, request.Digest, request.ExpectedStamp), options, token);
                if (admitted is not ArtifactResult<IArtifactProtectionGuard>.Success acquired)
                { throw new LocalStateException(admitted is ArtifactResult<IArtifactProtectionGuard>.Failure failure ? failure.Code : ArtifactFailureCode.InternalFailure); }
                protection = acquired.Value;
                var gate = DigestGate(request.Digest.Hex);
                await gate.WaitAsync(token);
                LocalDecision decision;
                try
                {
                    lock (stateSync)
                    {
                        if (!decisions.TryGetValue(request.Digest.Hex, out var current) || current.Removed)
                        { throw new LocalStateException(ArtifactFailureCode.NotFound); }
                        decision = current;
                        if (decision.Corrupt) { throw new LocalStateException(ArtifactFailureCode.CorruptContent); }
                        if (request.ExpectedStamp is ArtifactOption<ArtifactStamp>.Some expected
                            && expected.Value != decision.Content.Stamp(StoreIdentity))
                        { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                    }
                    input = OpenCommittedPayload(decision.Content, FileOptions.Asynchronous | FileOptions.SequentialScan);
                }
                finally { gate.Release(); }
                await faults.ObserveAsync("read.opened");
                token.ThrowIfCancellationRequested();
                var session = new LocalReadSession(this, decision.Content.Stamp(StoreIdentity), input, protection, slot);
                lock (stateSync)
                {
                    if (!decisions.TryGetValue(request.Digest.Hex, out var current)
                        || current.Removed || current.Content != decision.Content)
                    { throw new LocalStateException(ArtifactFailureCode.Conflict); }
                    if (current.Corrupt) { throw new LocalStateException(ArtifactFailureCode.CorruptContent); }
                    readers.Add(session);
                }
                session.StartIdleExpiry();
                input = null;
                protection = null;
                return session;
            }
            catch
            {
                if (input is not null) { await input.DisposeAsync(); }
                if (protection is not null) { await protection.DisposeAsync(); }
                slot.Dispose();
                throw;
            }
        }, undelivered: async session =>
        {
            if (await session.CloseAsync(new(), default) is not ArtifactResult<ArtifactShutdown>.Success)
            { throw new LocalStateException(ArtifactFailureCode.CleanupIncomplete); }
        });
    }

    private sealed class LocalReadSession(LocalArtifactStore store, ArtifactStamp stamp, FileStream input,
        IArtifactProtectionGuard protection, Slot slot) : IArtifactReadSession
    {
        private int copied;
        private readonly object sessionSync = new();
        private readonly Guid closeId = Guid.NewGuid();
        private bool closed;
        private bool physicallyClosed;
        private Task? closing;
        private Task<ArtifactResult<ArtifactReadCompletion>>? copying;
        private TaskCompletionSource? copySettled;
        private readonly long opened = store.time.GetTimestamp();
        private readonly CancellationTokenSource idleCancellation = new();
        public ArtifactStamp Stamp { get; } = stamp;

        public void StartIdleExpiry() => _ = ExpireIdleAsync();

        private async Task ExpireIdleAsync()
        {
            try { await Task.Delay(TimeSpan.FromSeconds(30), store.time, idleCancellation.Token); }
            catch (OperationCanceledException) when (idleCancellation.IsCancellationRequested) { return; }
            lock (sessionSync)
            {
                if (copied != 0 || closed) { return; }
                closed = true;
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
                if (!closed && store.time.GetElapsedTime(opened) >= TimeSpan.FromSeconds(30))
                {
                    closed = true;
                    _ = CloseAsync(new(), default);
                }
                if (closed || Interlocked.CompareExchange(ref copied, 1, 0) != 0)
                { return ValueTask.FromResult(store.Failed<ArtifactReadCompletion>(ArtifactFailureCode.Conflict, ArtifactPhase.Read)); }
                idleCancellation.Cancel();
                copySettled = new(TaskCreationOptions.RunContinuationsAsynchronously);
                copying = store.ExecuteAsync(ArtifactPhase.Read, options.Deadline, ct, async token =>
                {
                    if (!destination.CanWrite) { throw new LocalStateException(ArtifactFailureCode.InvalidInput); }
                    using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
                    var buffer = new byte[store.Limits.CopyBufferBytes];
                    long length = 0;
                    while (true)
                    {
                        using var inactivity = CancellationTokenSource.CreateLinkedTokenSource(token);
                        inactivity.CancelAfter(options.Inactivity);
                        var count = await input.ReadAsync(buffer, inactivity.Token);
                        token.ThrowIfCancellationRequested();
                        if (count == 0) { break; }
                        if (count > Stamp.Identity.Length - length) { return Corrupt(); }
                        await destination.WriteAsync(buffer.AsMemory(0, count), inactivity.Token);
                        hash.AppendData(buffer, 0, count);
                        length = checked(length + count);
                        await store.faults.ObserveAsync("read.copy");
                    }
                    var digest = new ArtifactDigest(Convert.ToHexStringLower(hash.GetHashAndReset()));
                    if (length != Stamp.Identity.Length || digest != Stamp.Identity.Digest) { return Corrupt(); }
                    return new ArtifactReadCompletion(Stamp, digest, length);
                }, settled: () => copySettled.TrySetResult()).AsTask();
                return new(copying);
            }
        }

        private ArtifactReadCompletion Corrupt()
        {
            throw store.Quarantine(new(Stamp.Identity.Digest.Hex, Stamp.Identity.Length, Stamp.Incarnation));
        }

        public async ValueTask<ArtifactResult<ArtifactShutdown>> CloseAsync(ArtifactCleanupOptions options, CancellationToken ct)
        {
            ArgumentNullException.ThrowIfNull(options);
            Task close;
            lock (sessionSync)
            {
                closed = true;
                idleCancellation.Cancel();
                var live = copySettled?.Task;
                close = closing ??= Task.Run(async () =>
                {
                    if (live is not null) { await live; }
                    await input.DisposeAsync();
                    await protection.DisposeAsync();
                    slot.Dispose();
                    lock (store.stateSync) { store.readers.Remove(this); }
                    lock (sessionSync)
                    {
                        physicallyClosed = true;
                        store.incompleteReadCloses.TryRemove(closeId, out _);
                    }
                });
            }
            try { await close.WaitAsync(options.Deadline, ct); }
            catch (Exception)
            {
                lock (sessionSync)
                {
                    if (!physicallyClosed) { store.incompleteReadCloses.TryAdd(closeId, 0); }
                }
                return store.Failed<ArtifactShutdown>(ArtifactFailureCode.CleanupIncomplete, ArtifactPhase.Cleanup, live: true);
            }
            return new ArtifactResult<ArtifactShutdown>.Success(new(ArtifactCleanupState.Released, 0, 0, false));
        }

        public async ValueTask DisposeAsync()
        {
            if (await CloseAsync(new(), default) is not ArtifactResult<ArtifactShutdown>.Success)
            { throw new InvalidOperationException("Artifact read cleanup retains live ownership."); }
        }
    }
}
