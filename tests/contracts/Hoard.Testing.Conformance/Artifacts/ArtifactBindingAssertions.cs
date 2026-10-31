using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactBindingAssertions
{
    public static async Task ConcurrentReleaseAsync(
        IArtifactConformanceSession session, CancellationToken cancellationToken)
    {
        const ConformanceFault publication = ConformanceFault.PublicationBoundary;
        const ConformanceFault native = ConformanceFault.NativeNonCooperation;
        using var source = new ShortSource("independently released actual work"u8.ToArray());
        var ticket = Success(await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await session.Store.StageAsync(ticket, source, new(), cancellationToken));
        await session.Faults.ArmAsync(publication, cancellationToken);
        var committing = session.Store.CommitAsync(staged, new(), cancellationToken).AsTask();
        Task? releasing = null;
        try
        {
            await session.Faults.WaitForBoundaryAsync(publication, cancellationToken);
            await session.Faults.ArmAsync(native, cancellationToken);
            releasing = session.Faults.ReleaseAsync(native, cancellationToken).AsTask();
            Assert.False(releasing.IsCompleted);
            var independent = session.Faults.ReleaseAsync(publication, cancellationToken).AsTask();
            Assert.Same(independent, await Task.WhenAny(independent, Task.Delay(TimeSpan.FromSeconds(2), cancellationToken)));
            await independent;
        }
        finally
        {
            await session.Faults.ReleaseAsync(publication, CancellationToken.None);
            await committing.WaitAsync(TimeSpan.FromSeconds(10));
            if (releasing is not null) { Assert.Null(await Record.ExceptionAsync(() => releasing)); }
            await session.Faults.AwaitSettlementAsync(CancellationToken.None);
        }
        Success(await committing);
        await session.Faults.ArmAsync(native, cancellationToken);
        await session.Faults.ReleaseAsync(native, cancellationToken);
        Assert.Equal("independently released actual work"u8.ToArray(),
            await ReadAsync(session.Store, Success(await committing).Stamp, cancellationToken));
        Assert.False(source.WasDisposed);
    }

    public static Task ControlsAsync(IArtifactConformanceSession session, ConformanceFault fault,
        Action<TimeSpan> advanceClock, CancellationToken cancellationToken) => fault switch
        {
            ConformanceFault.PublicationBoundary or ConformanceFault.DirectVisibility
                or ConformanceFault.ReceiptBoundary => PublicationAsync(session, fault, cancellationToken),
            ConformanceFault.GenerationBoundary => GenerationAsync(session, advanceClock, cancellationToken),
            ConformanceFault.PayloadDamage => DamageAsync(session, cancellationToken),
            ConformanceFault.Capacity => CapacityAsync(session, cancellationToken),
            ConformanceFault.CleanupFailure => CleanupAsync(session, cancellationToken),
            ConformanceFault.NativeNonCooperation => NativeAsync(session, advanceClock, cancellationToken),
            ConformanceFault.SourceNonCooperation => SourceAsync(session, cancellationToken),
            ConformanceFault.SinkNonCooperation => SinkAsync(session, cancellationToken),
            _ => throw new ArgumentException("BindingInvalid")
        };

    private static async Task ArmAsync(
        IArtifactConformanceSession session, ConformanceFault fault, CancellationToken cancellationToken)
    {
        await session.Faults.ArmAsync(fault, cancellationToken);
        Assert.Equal(0, (await session.Faults.ObserveAsync(fault, cancellationToken)).ObservationCount);
        using var waiting = new CancellationTokenSource();
        var entered = session.Faults.WaitForBoundaryAsync(fault, waiting.Token).AsTask();
        Assert.False(entered.IsCompleted);
        waiting.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => entered);
        await Assert.ThrowsAsync<InvalidOperationException>(() => session.Faults.ArmAsync(fault, cancellationToken).AsTask());
    }

    private static async Task ArrivedAsync(
        IArtifactConformanceSession session, ConformanceFault fault, Task operation, CancellationToken cancellationToken)
    {
        var entered = session.Faults.WaitForBoundaryAsync(fault, cancellationToken).AsTask();
        Assert.Same(entered, await Task.WhenAny(entered, operation));
        await entered;
        var observed = await session.Faults.ObserveAsync(fault, cancellationToken);
        Assert.Equal(1, observed.ObservationCount);
        Assert.NotEqual(ConformanceOwnershipState.Released, observed.Ownership);
    }

    private static async Task PublicationAsync(
        IArtifactConformanceSession session, ConformanceFault fault, CancellationToken cancellationToken)
    {
        var bytes = "full binding publication acknowledgement"u8.ToArray();
        using var source = new ShortSource(bytes);
        var ticket = Success(await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await session.Store.StageAsync(ticket, source, new(), cancellationToken));
        await ArmAsync(session, fault, cancellationToken);
        var committing = session.Store.CommitAsync(staged, new(), cancellationToken).AsTask();
        try
        {
            await ArrivedAsync(session, fault, committing, cancellationToken);
            Assert.False(committing.IsCompleted);
        }
        finally
        {
            await session.Faults.ReleaseAsync(fault, CancellationToken.None);
            await committing.WaitAsync(TimeSpan.FromSeconds(10));
            await session.Faults.AwaitSettlementAsync(CancellationToken.None);
        }
        var receipt = Success(await committing);
        Assert.Equal(receipt, Assert.IsType<ArtifactResolution.Committed>(Success(
            await session.Store.ReconcileAsync(ticket, new(), cancellationToken))).Receipt);
        Assert.Equal(bytes, await ReadAsync(session.Store, receipt.Stamp, cancellationToken));
        Assert.False(source.WasDisposed);
    }

    private static async Task GenerationAsync(
        IArtifactConformanceSession session, Action<TimeSpan> advanceClock, CancellationToken cancellationToken)
    {
        const ConformanceFault fault = ConformanceFault.GenerationBoundary;
        using var originalSource = new ShortSource("old generation"u8.ToArray());
        using var replacementSource = new ShortSource("new generation"u8.ToArray());
        var ticket = Success(await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var original = Success(await session.Store.StageAsync(ticket, originalSource, new(), cancellationToken));
        advanceClock(TimeSpan.FromSeconds(31));
        var cleanup = new ArtifactCleanupRequest(session.Identity, [new ArtifactCleanupTarget.AbandonedStaging(original.Owner)]);
        Assert.Equal(1, Success(await session.Maintenance.CleanupAsync(cleanup, new(), cancellationToken)).Completed);
        await ArmAsync(session, fault, cancellationToken);
        var staging = session.Store.StageAsync(ticket, replacementSource, new(), cancellationToken).AsTask();
        try
        {
            await ArrivedAsync(session, fault, staging, cancellationToken);
            Assert.False(staging.IsCompleted);
            Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await session.Store.CommitAsync(original, new(), cancellationToken)).Code);
        }
        finally
        {
            await session.Faults.ReleaseAsync(fault, CancellationToken.None);
            await staging.WaitAsync(TimeSpan.FromSeconds(10));
            await session.Faults.AwaitSettlementAsync(CancellationToken.None);
        }
        var replacement = Success(await staging);
        Assert.True(replacement.Owner.Generation > original.Owner.Generation);
        Assert.Equal(1, Success(await session.Maintenance.CleanupAsync(cleanup, new(), cancellationToken)).Conflicted);
        var receipt = Success(await session.Store.CommitAsync(replacement, new(), cancellationToken));
        Assert.Equal("new generation"u8.ToArray(), await ReadAsync(session.Store, receipt.Stamp, cancellationToken));
        Assert.False(originalSource.WasDisposed);
        Assert.False(replacementSource.WasDisposed);
    }

    private static async Task DamageAsync(IArtifactConformanceSession session, CancellationToken cancellationToken)
    {
        const ConformanceFault fault = ConformanceFault.PayloadDamage;
        using var first = new ShortSource("first explicitly targeted artifact"u8.ToArray());
        using var second = new ShortSource("second artifact must remain intact"u8.ToArray());
        var target = await PublishAsync(session.Store, first, new(1024), cancellationToken);
        var other = await PublishAsync(session.Store, second, new(1024), cancellationToken);
        await ArmAsync(session, fault, cancellationToken);
        var foreign = new ArtifactStamp(target.Stamp.Store, target.Stamp.Identity, Guid.NewGuid());
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            session.Faults.DamagePayloadAsync(foreign, false, cancellationToken).AsTask());
        Assert.Equal(0, (await session.Faults.ObserveAsync(fault, cancellationToken)).ObservationCount);
        Assert.Equal("first explicitly targeted artifact"u8.ToArray(),
            await ReadAsync(session.Store, target.Stamp, cancellationToken));
        try
        {
            await session.Faults.DamagePayloadAsync(target.Stamp, false, cancellationToken);
            await session.Faults.WaitForBoundaryAsync(fault, cancellationToken);
            Assert.Equal(1, (await session.Faults.ObserveAsync(fault, cancellationToken)).ObservationCount);
            Assert.Equal("second artifact must remain intact"u8.ToArray(),
                await ReadAsync(session.Store, other.Stamp, cancellationToken));
            await using var read = Success(await session.Store.OpenReadAsync(new(target.Stamp.Identity.Digest), new(), cancellationToken));
            using var destination = new MemoryStream();
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await read.CopyToAsync(destination, new(), cancellationToken)).Code);
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await session.Store.OpenReadAsync(new(target.Stamp.Identity.Digest), new(), cancellationToken)).Code);
        }
        finally { await session.Faults.ReleaseAsync(fault, CancellationToken.None); }
    }

    private static async Task CapacityAsync(IArtifactConformanceSession session, CancellationToken cancellationToken)
    {
        const ConformanceFault fault = ConformanceFault.Capacity;
        using var source = new ShortSource("real capacity prefix"u8.ToArray());
        var ticket = Success(await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        await ArmAsync(session, fault, cancellationToken);
        try
        {
            Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await session.Store.StageAsync(ticket, source, new(), cancellationToken)).Code);
            await session.Faults.WaitForBoundaryAsync(fault, cancellationToken);
            Assert.Equal(1, (await session.Faults.ObserveAsync(fault, cancellationToken)).ObservationCount);
            await session.Faults.AwaitSettlementAsync(cancellationToken);
            Assert.True(source.BytesRead > 0);
            Assert.False(source.WasDisposed);
            Assert.IsType<ArtifactResolution.NotCommitted>(Success(
                await session.Store.ReconcileAsync(ticket, new(), cancellationToken)));
        }
        finally { await session.Faults.ReleaseAsync(fault, CancellationToken.None); }
        await ArtifactCompositionAssertions.ConfiguredPublicationAsync(session.Store, cancellationToken);
    }

    private static async Task CleanupAsync(IArtifactConformanceSession session, CancellationToken cancellationToken)
    {
        const ConformanceFault fault = ConformanceFault.CleanupFailure;
        using var cancellation = new CancellationTokenSource();
        await using var barrier = new ArtifactConformanceBarrier("full-unclaimed-cleanup");
        await using var observation = await session.Faults.ObserveBoundaryAsync(
            ArtifactObservationPoint.OperationCompleted, () => new(barrier.HoldAsync()), cancellationToken);
        await ArmAsync(session, fault, cancellationToken);
        var reserving = session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellation.Token).AsTask();
        try
        {
            await barrier.Entered.WaitAsync(cancellationToken);
            cancellation.Cancel();
            Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await reserving.WaitAsync(TimeSpan.FromSeconds(10)));
            barrier.Release();
            await session.Faults.AwaitSettlementAsync(cancellationToken);
            await session.Faults.WaitForBoundaryAsync(fault, cancellationToken);
            Assert.Equal(1, (await session.Faults.ObserveAsync(fault, cancellationToken)).ObservationCount);
            var stopped = Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                await session.Lifetime.StopAsync(new(TimeSpan.FromSeconds(2)), cancellationToken));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, stopped.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, stopped.Cleanup);
            Assert.Equal(2, (await session.Faults.ObserveAsync(fault, cancellationToken)).ObservationCount);
        }
        finally
        {
            barrier.Release();
            cancellation.Cancel();
            await reserving.WaitAsync(TimeSpan.FromSeconds(10));
            await session.Faults.ReleaseAsync(fault, CancellationToken.None);
            Assert.Equal(ArtifactCleanupState.Released, Success(
                await session.Lifetime.StopAsync(new(TimeSpan.FromSeconds(2)), CancellationToken.None)).State);
            await session.Faults.AwaitSettlementAsync(CancellationToken.None);
        }
    }

    private static async Task NativeAsync(
        IArtifactConformanceSession session, Action<TimeSpan> advanceClock, CancellationToken cancellationToken)
    {
        const ConformanceFault fault = ConformanceFault.NativeNonCooperation;
        using var source = new ShortSource("full synchronous ownership"u8.ToArray());
        var receipt = await PublishAsync(session.Store, source, new(1024), cancellationToken);
        var ticket = Success(await session.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
        await ArmAsync(session, fault, cancellationToken);
        var deleting = session.Store.DeleteAsync(ticket, new(TimeSpan.FromMilliseconds(100)), cancellationToken).AsTask();
        try
        {
            await ArrivedAsync(session, fault, deleting, cancellationToken);
            advanceClock(TimeSpan.FromMilliseconds(100));
            var failed = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await deleting.WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.True(failed.Code is ArtifactFailureCode.DeadlineExceeded or ArtifactFailureCode.Uncertain);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                await session.Lifetime.StopAsync(new(TimeSpan.FromMilliseconds(50)), cancellationToken)).Code);
        }
        finally
        {
            await session.Faults.ReleaseAsync(fault, CancellationToken.None);
            await deleting.WaitAsync(TimeSpan.FromSeconds(10));
            await session.Faults.AwaitSettlementAsync(CancellationToken.None);
        }
        Assert.Equal(ArtifactCleanupState.Released, Success(
            await session.Lifetime.StopAsync(new(TimeSpan.FromSeconds(2)), cancellationToken)).State);
        Assert.False(source.WasDisposed);
    }

    private static async Task SourceAsync(IArtifactConformanceSession session, CancellationToken cancellationToken)
    {
        const ConformanceFault fault = ConformanceFault.SourceNonCooperation;
        var ticket = Success(await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        await ArmAsync(session, fault, cancellationToken);
        var source = session.Faults.BorrowedSource;
        using var cancellation = new CancellationTokenSource();
        var staging = session.Store.StageAsync(ticket, source.Stream, new(), cancellation.Token).AsTask();
        try
        {
            await ArrivedAsync(session, fault, staging, cancellationToken);
            cancellation.Cancel();
            var failed = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await staging.WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.Equal(ArtifactFailureCode.CancelledBeforeCommit, failed.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.False(source.WasDisposed);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken)).Code);
        }
        finally
        {
            await session.Faults.ReleaseAsync(fault, CancellationToken.None);
            await staging.WaitAsync(TimeSpan.FromSeconds(10));
            await session.Faults.AwaitSettlementAsync(CancellationToken.None);
        }
        Assert.False(source.WasDisposed);
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(
            await session.Store.ReconcileAsync(ticket, new(), cancellationToken)));
        await ArtifactCompositionAssertions.ConfiguredPublicationAsync(session.Store, cancellationToken);
    }

    private static async Task SinkAsync(IArtifactConformanceSession session, CancellationToken cancellationToken)
    {
        const ConformanceFault fault = ConformanceFault.SinkNonCooperation;
        using var source = new ShortSource("full borrowed destination"u8.ToArray());
        var receipt = await PublishAsync(session.Store, source, new(1024), cancellationToken);
        await using var read = Success(await session.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken));
        await ArmAsync(session, fault, cancellationToken);
        var destination = session.Faults.BorrowedDestination;
        using var cancellation = new CancellationTokenSource();
        var copying = read.CopyToAsync(destination.Stream, new(), cancellation.Token).AsTask();
        try
        {
            await ArrivedAsync(session, fault, copying, cancellationToken);
            cancellation.Cancel();
            var failed = Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await copying.WaitAsync(TimeSpan.FromSeconds(2)));
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                await read.CloseAsync(new(TimeSpan.FromMilliseconds(20)), cancellationToken)).Code);
            Assert.False(destination.WasDisposed);
        }
        finally
        {
            await session.Faults.ReleaseAsync(fault, CancellationToken.None);
            await copying.WaitAsync(TimeSpan.FromSeconds(10));
            await session.Faults.AwaitSettlementAsync(CancellationToken.None);
            Success(await read.CloseAsync(new(), CancellationToken.None));
        }
        Assert.False(destination.WasDisposed);
        Assert.Equal("full borrowed destination"u8.ToArray(),
            await ReadAsync(session.Store, receipt.Stamp, cancellationToken));
    }
}
