using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactOwnershipAssertions
{
    public static async Task SynchronousStorageHoldAsync(
        IArtifactAssertionSession session, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("actual synchronous storage ownership"u8.ToArray());
        var receipt = await PublishAsync(session.Store, source, new(1024), cancellationToken);
        var ticket = Success(await session.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
        var previous = await session.HoldSynchronousStorageAsync(cancellationToken);
        await previous.DisposeAsync();
        await using var hold = await session.HoldSynchronousStorageAsync(cancellationToken);
        await previous.DisposeAsync();
        var deleting = session.Store.DeleteAsync(
            ticket, new(TimeSpan.FromMilliseconds(100)), cancellationToken).AsTask();
        Task? workers = null;
        try
        {
            var entered = hold.WaitForEntryAsync(cancellationToken).AsTask();
            Assert.Same(entered, await Task.WhenAny(entered, deleting));
            await entered;
            var failed = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await deleting.WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.True(failed.Code is ArtifactFailureCode.DeadlineExceeded or ArtifactFailureCode.Uncertain);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            workers = session.ObserveWorkerSettlement();
            Assert.False(workers.IsCompleted);
            Assert.Equal(1, hold.ObservationCount);
            var rejected = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, rejected.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, rejected.Cleanup);
            var protection = await session.Authority.AcquireAsync(new(Guid.NewGuid(),
                ArtifactProtectionOperation.Read, session.Identity, receipt.Stamp.Identity.Digest,
                new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)),
                new(TimeSpan.FromMilliseconds(50)), cancellationToken);
            if (protection is ArtifactResult<IArtifactProtectionGuard>.Success unexpected)
            { await unexpected.Value.DisposeAsync(); }
            Assert.Equal(ArtifactFailureCode.DeadlineExceeded,
                Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(protection).Code);
            var stopped = Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                await session.Lifetime.StopAsync(new(TimeSpan.FromMilliseconds(50)), cancellationToken)
                    .AsTask().WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, stopped.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, stopped.Cleanup);
            Assert.False(workers.IsCompleted);
            Assert.False(session.Ready);
            Assert.Equal(1, hold.ObservationCount);
            Assert.False(source.WasDisposed);
            var mode = session.Store.Capabilities.Durability == ArtifactDurability.LocalProcessCrash
                ? ArtifactInitializationMode.ReopenCompatible : ArtifactInitializationMode.CreateEmpty;
            var competing = await session.ProbeCompetingInitializationAsync(mode, cancellationToken);
            Assert.Equal(ArtifactFailureCode.Unavailable,
                Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(competing.Admission).Code);
            Success(competing.Shutdown);
            Assert.True(session.ObserveInitialization().RootExists);
            Assert.False(workers.IsCompleted);
        }
        finally
        {
            hold.Release();
            await deleting.WaitAsync(TimeSpan.FromSeconds(10));
            if (workers is not null) { await workers; }
            await session.AwaitSettlementAsync(CancellationToken.None);
        }
        Assert.Equal(ArtifactCleanupState.Released, Success(
            await session.Lifetime.StopAsync(new(TimeSpan.FromSeconds(2)), CancellationToken.None)).State);
        Assert.False(source.WasDisposed);
    }

    public static async Task CooperativeInactivityAsync(
        IArtifactStore store, Func<Task> whenIdle, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var stalled = new PendingSource(cooperative: true);
        Assert.Equal(ArtifactFailureCode.DeadlineExceeded, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await store.StageAsync(ticket, stalled,
                new(TimeSpan.FromSeconds(2), TimeSpan.FromMilliseconds(20)), cancellationToken)
                .AsTask().WaitAsync(TimeSpan.FromSeconds(3))).Code);
        await whenIdle().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.False(stalled.WasDisposed);
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        using var source = new ShortSource("cooperative inactivity recovery"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        await using (var read = Success(await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)))
        {
            using var destination = new StalledDestination();
            Assert.Equal(ArtifactFailureCode.DeadlineExceeded, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await read.CopyToAsync(destination, new(TimeSpan.FromSeconds(2), TimeSpan.FromMilliseconds(20)), cancellationToken)
                    .AsTask().WaitAsync(TimeSpan.FromSeconds(3))).Code);
            Assert.True(destination.CanWrite);
            Success(await read.CloseAsync(new(), cancellationToken));
        }
        Assert.Equal("cooperative inactivity recovery"u8.ToArray(), await ReadAsync(store, receipt.Stamp, cancellationToken));
    }

    public static async Task IdleReadExpiryAsync(
        IArtifactStore store, Action<TimeSpan> advanceClock, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("idle read"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        await using var read = Success(await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken));
        advanceClock(TimeSpan.FromSeconds(30));
        using var destination = new MemoryStream();
        Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
            await read.CopyToAsync(destination, new(), cancellationToken)).Code);
        Assert.Equal(0, destination.Length);
        Success(await read.CloseAsync(new(), cancellationToken));
    }

    public static async Task NoncooperativeSourceAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        using var source = new PendingSource(cooperative: false);
        using var cancellation = new CancellationTokenSource();
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var work = store.StageAsync(ticket, source, new(), cancellation.Token).AsTask();
        try
        {
            await source.Entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
            cancellation.Cancel();
            var failed = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await work.WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.Equal(ArtifactFailureCode.CancelledBeforeCommit, failed.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.False(source.WasDisposed);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken)).Code);
        }
        finally { source.Released.TrySetResult(0); }
    }

    public static async Task NoncooperativeDestinationAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("live destination ownership"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        var session = Success(await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken));
        using var destination = new PendingDestination();
        using var cancellation = new CancellationTokenSource();
        var copy = session.CopyToAsync(destination, new(), cancellation.Token).AsTask();
        try
        {
            await destination.Entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
            cancellation.Cancel();
            var result = Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await copy.WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, result.Cleanup);
            var close = await session.CloseAsync(new(TimeSpan.FromMilliseconds(20)), cancellationToken);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(close).Code);
            Assert.False(destination.WasDisposed);
        }
        finally
        {
            destination.Released.TrySetResult();
            Success(await session.CloseAsync(new(), cancellationToken));
        }
    }

    public static async Task ExternalRenewalCancellationAsync(
        IArtifactStore store, Action<TimeSpan> advanceClock, Func<Task> whenIdle, Action blockDecision,
        Func<CancellationToken, Task> waitForDecision, Action releaseDecision, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("renewed owner survives older cancellation"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        blockDecision();
        using var cancellation = new CancellationTokenSource();
        var committing = store.CommitAsync(staged, new(), cancellation.Token).AsTask();
        ArtifactStagingOwner renewed;
        try
        {
            await waitForDecision(cancellationToken);
            advanceClock(TimeSpan.FromSeconds(10));
            renewed = Success(await store.RenewAsync(staged.Owner, new(), cancellationToken));
            cancellation.Cancel();
            Assert.Equal(ArtifactFailureCode.CancelledBeforeCommit,
                Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                    await committing.WaitAsync(TimeSpan.FromSeconds(2))).Code);
        }
        finally { releaseDecision(); }
        await whenIdle().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.IsType<ArtifactResolution.Pending>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        var current = new ArtifactStagedWrite(renewed, staged.Identity, staged.VerifiedCompletion, staged.PrivateHandle);
        var receipt = Success(await store.CommitAsync(current, new(), cancellationToken));
        Assert.Equal("renewed owner survives older cancellation"u8.ToArray(),
            await ReadAsync(store, receipt.Stamp, cancellationToken));
    }

    public static Task ProgressRenewalCancellationAsync(
        IArtifactStore store, Action<TimeSpan> advanceClock, Func<Task> whenIdle,
        Action<Func<ValueTask>> observeProgress, CancellationToken cancellationToken)
        => ProgressRenewalCancellationAsync(store, advanceClock, whenIdle,
            observer => { observeProgress(observer); return ValueTask.CompletedTask; }, cancellationToken);

    public static async Task ProgressRenewalCancellationAsync(
        IArtifactStore store, Action<TimeSpan> advanceClock, Func<Task> whenIdle,
        Func<Func<ValueTask>, ValueTask> observeProgress, CancellationToken cancellationToken)
    {
        var bytes = new byte[1048576];
        using var initial = new MemoryStream(bytes, writable: false);
        var original = await PublishAsync(store, initial, new(2097152), cancellationToken);
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(2097152)), new(), cancellationToken));
        using var duplicate = new MemoryStream(bytes, writable: false);
        var staged = Success(await store.StageAsync(ticket, duplicate, new(), cancellationToken));
        using var cancellation = new CancellationTokenSource();
        var progress = 0;
        ValueTask Advance()
        {
            advanceClock(TimeSpan.FromSeconds(11));
            if (Interlocked.Increment(ref progress) == 2) { cancellation.Cancel(); }
            return ValueTask.CompletedTask;
        }
        await observeProgress(Advance);
        Assert.Equal(ArtifactFailureCode.CancelledBeforeCommit,
            Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await store.CommitAsync(staged, new(), cancellation.Token)).Code);
        await whenIdle().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Equal(2, progress);
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        Assert.Equal(bytes, await ReadAsync(store, original.Stamp, cancellationToken));
    }

    public static async Task CancelledStagedDescriptorAsync(
        IArtifactStore store, Action<TimeSpan> advanceClock, Func<Task> whenIdle,
        string alteration, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("preserve current verified ownership"u8.ToArray());
        var original = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        var current = original;
        ArtifactStagedWrite invalid;
        if (alteration == "renewed")
        {
            advanceClock(TimeSpan.FromSeconds(10));
            var renewed = Success(await store.RenewAsync(original.Owner, new(), cancellationToken));
            current = new(renewed, original.Identity, original.VerifiedCompletion, original.PrivateHandle);
            invalid = original;
        }
        else
        {
            invalid = new(original.Owner, original.Identity,
                alteration == "completion" ? Guid.NewGuid() : original.VerifiedCompletion,
                alteration == "handle" ? original.PrivateHandle + "-forged" : original.PrivateHandle);
        }
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.CommitAsync(invalid, new(), cancellation.Token));
        await whenIdle().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.IsType<ArtifactResolution.Pending>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        var receipt = Success(await store.CommitAsync(current, new(), cancellationToken));
        Assert.Equal(ArtifactMutationOutcome.Published, receipt.Outcome);
        Assert.Equal("preserve current verified ownership"u8.ToArray(),
            await ReadAsync(store, receipt.Stamp, cancellationToken));
    }

    public class PendingSource(bool cooperative) : Stream
    {
        public TaskCompletionSource Entered { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource<int> Released { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public bool WasDisposed { get; private set; }
        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException();
        public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            Entered.TrySetResult();
            return new(cooperative ? Released.Task.WaitAsync(cancellationToken) : Released.Task);
        }
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
        public override void Flush() => throw new NotSupportedException();
        public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    }

    private sealed class StalledDestination : MemoryStream
    {
        public override ValueTask WriteAsync(ReadOnlyMemory<byte> buffer, CancellationToken cancellationToken = default)
            => new(Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken));
    }

    private sealed class PendingDestination : MemoryStream
    {
        public TaskCompletionSource Entered { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource Released { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public bool WasDisposed { get; private set; }
        public override ValueTask WriteAsync(ReadOnlyMemory<byte> buffer, CancellationToken cancellationToken = default)
        {
            Entered.TrySetResult();
            return new(Released.Task);
        }
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
    }
}
