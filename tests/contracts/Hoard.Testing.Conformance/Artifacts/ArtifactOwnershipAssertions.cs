using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactOwnershipAssertions
{
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
