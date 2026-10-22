using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactBudgetTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cap_crossing_rejects_excess_before_append_and_capacity_recovers(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new ArtifactLimits(10, 10, 1));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(10)), new(), default));
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default)).Code);
        using var source = new ShortSource("actual input is too large"u8.ToArray());
        Assert.Equal(ArtifactFailureCode.LimitExceeded, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await driver.Store.StageAsync(ticket, source, new(), default)).Code);
        Assert.False(source.WasDisposed);
        Assert.NotNull(Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(10)), new(), default)));
        Assert.Equal(ArtifactFailureCode.LimitExceeded, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(11)), new(), default)).Code);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Total_deadline_includes_shared_authority_contention_before_publication(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        using var source = new ShortSource("guard queue budget"u8.ToArray());
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        var stamp = new ArtifactStamp(driver.Identity, staged.Identity, Guid.NewGuid());
        await using var exclusion = Success(await driver.Authority.AcquireAsync(new(Guid.NewGuid(),
            ArtifactProtectionOperation.Deletion, driver.Identity, staged.Identity.Digest,
            new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), default));
        var result = await driver.Store.CommitAsync(staged,
            new ArtifactTransferOptions(TimeSpan.FromMilliseconds(30)), default).AsTask().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Equal(ArtifactFailureCode.DeadlineExceeded, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(result).Code);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cooperative_cancellation_stops_input_without_disposing_borrowed_stream(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        using var source = new PendingSource(cooperative: true);
        using var cancelled = new CancellationTokenSource();
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staging = driver.Store.StageAsync(ticket, source, new(), cancelled.Token).AsTask();
        await source.Entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
        cancelled.Cancel();
        var result = await staging.WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Equal(ArtifactFailureCode.CancelledBeforeCommit, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(result).Code);
        Assert.False(source.WasDisposed);
    }

    internal sealed class PendingSource(bool cooperative) : Stream
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
}
