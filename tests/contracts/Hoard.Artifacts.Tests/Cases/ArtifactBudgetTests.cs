using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactBudgetTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cancellation_of_an_admitted_commit_cannot_fence_an_externally_renewed_owner(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("renewed owner survives older cancellation"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        await using var barrier = new ArtifactTestBarrier("renew-before-cancellation-settlement");
        SetObserver(driver, "publish.before-decision", "pointer.compare", () => new(barrier.HoldAsync()));
        using var cancellation = new CancellationTokenSource();
        var committing = driver.Store.CommitAsync(staged, new(), cancellation.Token).AsTask();
        ArtifactStagingOwner renewed;
        try
        {
            await barrier.Entered;
            clock.Advance(TimeSpan.FromSeconds(10));
            renewed = Success(await driver.Store.RenewAsync(staged.Owner, new(), default));
            cancellation.Cancel();
            Assert.Equal(ArtifactFailureCode.CancelledBeforeCommit,
                Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                    await committing.WaitAsync(TimeSpan.FromSeconds(2))).Code);
        }
        finally
        {
            if (driver.LocalControls is { } local) { local.RemoveObserver("publish.before-decision"); }
            else { driver.ObjectControls!.RemoveObserver("pointer.compare"); }
            barrier.Release();
        }
        await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.IsType<ArtifactResolution.Pending>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        var current = new ArtifactStagedWrite(renewed, staged.Identity, staged.VerifiedCompletion, staged.PrivateHandle);
        var receipt = Success(await driver.Store.CommitAsync(current, new(), default));
        Assert.Equal("renewed owner survives older cancellation"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cancellation_after_progress_renewal_fences_the_same_admitted_owner(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        var bytes = new byte[1048576];
        using var initial = new MemoryStream(bytes, writable: false);
        var original = await PublishAsync(driver, initial, new(2097152));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(2097152)), new(), default));
        using var duplicate = new MemoryStream(bytes, writable: false);
        var staged = Success(await driver.Store.StageAsync(ticket, duplicate, new(), default));
        using var cancellation = new CancellationTokenSource();
        var progress = 0;
        ValueTask Advance()
        {
            clock.Advance(TimeSpan.FromSeconds(11));
            if (Interlocked.Increment(ref progress) == 2) { cancellation.Cancel(); }
            return ValueTask.CompletedTask;
        }
        SetObserver(driver, "publish.progress", "object.commit-progress", Advance);
        Assert.Equal(ArtifactFailureCode.CancelledBeforeCommit,
            Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await driver.Store.CommitAsync(staged, new(), cancellation.Token)).Code);
        await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Equal(2, progress);
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        Assert.Equal(bytes, await ReadAsync(driver, original.Stamp));
    }

    [Theory]
    [InlineData("local", "renewed")]
    [InlineData("object", "renewed")]
    [InlineData("local", "completion")]
    [InlineData("object", "completion")]
    [InlineData("local", "handle")]
    [InlineData("object", "handle")]
    public async Task Cancelled_invalid_or_stale_commit_cannot_fence_the_current_verified_handle(
        string provider, string alteration)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("preserve current verified ownership"u8.ToArray());
        var original = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        var current = original;
        ArtifactStagedWrite invalid;
        if (alteration == "renewed")
        {
            clock.Advance(TimeSpan.FromSeconds(10));
            var renewed = Success(await driver.Store.RenewAsync(original.Owner, new(), default));
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
            await driver.Store.CommitAsync(invalid, new(), cancellation.Token));
        await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.IsType<ArtifactResolution.Pending>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        var receipt = Success(await driver.Store.CommitAsync(current, new(), default));
        Assert.Equal(ArtifactMutationOutcome.Published, receipt.Outcome);
        Assert.Equal("preserve current verified ownership"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("object", false)]
    [InlineData("local", true)]
    [InlineData("object", true)]
    public async Task Cancelled_commit_before_decision_fences_the_ticket_and_cannot_publish_on_retry(
        string provider, bool alreadyCancelled)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("cancelled publication is terminal"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        var stamp = new ArtifactStamp(driver.Identity, staged.Identity, Guid.NewGuid());
        var exclusion = Success(await driver.Authority.AcquireAsync(new(Guid.NewGuid(),
            ArtifactProtectionOperation.Deletion, driver.Identity, staged.Identity.Digest,
            new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), default));
        using var cancellation = new CancellationTokenSource();
        if (alreadyCancelled) { cancellation.Cancel(); }
        try
        {
            var failure = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await driver.Store.CommitAsync(staged, new(TimeSpan.FromMilliseconds(30)), cancellation.Token));
            Assert.Equal(alreadyCancelled ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded,
                failure.Code);
        }
        finally { await exclusion.DisposeAsync(); }
        await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await driver.Store.CommitAsync(staged, new(), default));
        var read = await Task.Factory.StartNew(() => driver.Store.OpenReadAsync(
            new(staged.Identity.Digest), new(), default).AsTask(), CancellationToken.None,
            TaskCreationOptions.LongRunning, TaskScheduler.Default).Unwrap();
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            read).Code);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Full_transfer_queue_rejects_without_input_io_and_capacity_returns_after_release(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new ArtifactLimits(artifactBytes: 1, stagingBytes: 3, transferSlots: 1, waitingCalls: 1));
        var tickets = new List<ArtifactOperationTicket>();
        for (var index = 0; index < 3; index++)
        { tickets.Add(Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default))); }
        var queued = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        ValueTask ObserveQueue() { queued.TrySetResult(); return ValueTask.CompletedTask; }
        if (driver.LocalControls is { } local) { local.SetObserver("transfer.queued", ObserveQueue); }
        else { driver.ObjectControls!.SetObserver("object.transfer-queued", ObserveQueue); }
        using var first = new PendingSource(cooperative: true);
        var active = driver.Store.StageAsync(tickets[0], first, new(), default).AsTask();
        await first.Entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
        using var second = new ShortSource([1]);
        var waiting = driver.Store.StageAsync(tickets[1], second, new(), default).AsTask();
        try
        {
            await queued.Task.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(0, second.BytesRead);
            using var rejected = new ShortSource([1]);
            Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await driver.Store.StageAsync(tickets[2], rejected, new(), default)).Code);
            Assert.Equal(0, rejected.BytesRead);
        }
        finally { first.Released.TrySetResult(0); }
        var completed = Success(await active);
        var unblocked = Success(await waiting);
        Success(await driver.Store.AbandonAsync(completed.Owner, new(), default));
        Success(await driver.Store.AbandonAsync(unblocked.Owner, new(), default));
        using var restored = new ShortSource([1]);
        Success(await driver.Store.StageAsync(tickets[2], restored, new(), default));
        Assert.Equal(1, restored.BytesRead);
    }

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
