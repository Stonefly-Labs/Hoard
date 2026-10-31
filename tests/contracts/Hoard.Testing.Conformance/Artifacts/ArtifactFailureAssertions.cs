using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactFailureAssertions
{
    internal const string Canary = "synthetic-artifact-secret-canary";
    private const string OpaqueCanary = "synthetic-artifact-private-proof";

    public static async Task ScopedUnclaimedCleanupAsync(
        IArtifactAssertionSession session, bool readSession, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("actual unclaimed cleanup ownership"u8.ToArray());
        var published = readSession ? await PublishAsync(session.Store, source, new(1024), cancellationToken) : null;
        using var cancellation = new CancellationTokenSource();
        await using var barrier = new ArtifactConformanceBarrier("unclaimed-cleanup");
        var injection = await session.InjectUnclaimedCleanupFailureAsync(cancellationToken);
        async Task CancelHandoffAsync<T>(ValueTask<ArtifactResult<T>> operation) where T : notnull
        {
            var pending = operation.AsTask();
            try
            {
                await barrier.Entered.WaitAsync(cancellationToken);
                cancellation.Cancel();
                Assert.IsType<ArtifactResult<T>.Failure>(await pending.WaitAsync(TimeSpan.FromSeconds(10)));
            }
            finally
            {
                cancellation.Cancel();
                barrier.Release();
                await pending.WaitAsync(TimeSpan.FromSeconds(10));
                await session.AwaitSettlementAsync(CancellationToken.None);
            }
        }
        try
        {
            await using var observation = await session.ObserveBoundaryAsync(
                ArtifactObservationPoint.OperationCompleted, () => new(barrier.HoldAsync()), cancellationToken);
            if (published is null)
            {
                await CancelHandoffAsync(session.Store.ReserveWriteAsync(
                    new(new ArtifactExpectations(1024)), new(), cancellation.Token));
            }
            else
            {
                await CancelHandoffAsync(session.Store.OpenReadAsync(
                    new(published.Stamp.Identity.Digest), new(), cancellation.Token));
            }
            Assert.Equal(1, injection.ObservationCount);
            Assert.False(session.Ready);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await session.Store.ReserveWriteAsync(
                    new(new ArtifactExpectations(1024)), new(), cancellationToken)).Code);
            var stopped = Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                await session.Lifetime.StopAsync(new(TimeSpan.FromSeconds(2)), cancellationToken));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, stopped.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, stopped.Cleanup);
            Assert.Equal(2, injection.ObservationCount);
        }
        finally
        {
            barrier.Release();
            await injection.DisposeAsync();
            Assert.Equal(ArtifactCleanupState.Released, Success(
                await session.Lifetime.StopAsync(new(TimeSpan.FromSeconds(2)), CancellationToken.None)).State);
            await session.AwaitSettlementAsync(CancellationToken.None);
        }
        Assert.False(source.WasDisposed);
    }

    public static async Task ScopedCapacityAsync(
        IArtifactAssertionSession session, CancellationToken cancellationToken)
    {
        var bytes = "publication after injected storage capacity failure"u8.ToArray();
        async Task FailStagingAsync()
        {
            var ticket = Success(await session.Store.ReserveWriteAsync(
                new(new ArtifactExpectations(1024)), new(), cancellationToken));
            using var source = new ShortSource(bytes);
            var failed = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await session.Store.StageAsync(ticket, source, new(), cancellationToken));
            Assert.Equal(ArtifactFailureCode.Capacity, failed.Code);
            AssertSanitized(failed.ToString());
            await session.AwaitSettlementAsync(cancellationToken);
            Assert.True(source.BytesRead > 0);
            Assert.False(source.WasDisposed);
            Assert.IsType<ArtifactResolution.NotCommitted>(Success(
                await session.Store.ReconcileAsync(ticket, new(), cancellationToken)));
        }

        var injection = await session.InjectCapacityFailureAsync(cancellationToken);
        try
        {
            await FailStagingAsync();
            await FailStagingAsync();
            Assert.Equal(2, injection.ObservationCount);
        }
        finally { await injection.DisposeAsync(); }
        await using (var replacement = await session.InjectCapacityFailureAsync(cancellationToken))
        {
            await injection.DisposeAsync();
            await FailStagingAsync();
            Assert.Equal(1, replacement.ObservationCount);
            Assert.Equal(2, injection.ObservationCount);
        }
        using var valid = new ShortSource(bytes);
        var committed = await PublishAsync(session.Store, valid, new(1024), cancellationToken);
        Assert.Equal(bytes, await ReadAsync(session.Store, committed.Stamp, cancellationToken));
        Assert.False(valid.WasDisposed);
        await session.AwaitSettlementAsync(cancellationToken);
        Assert.True(session.Ready);
    }

    public static async Task StorageFailuresAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        (Exception Error, ArtifactFailureCode Code)[] failures =
        [
            (new UnauthorizedAccessException(Canary), ArtifactFailureCode.AccessDenied),
            (new IOException(Canary, 28), ArtifactFailureCode.Capacity),
            (new IOException(Canary), ArtifactFailureCode.Unavailable),
            (new InvalidOperationException(Canary), ArtifactFailureCode.InternalFailure)
        ];
        foreach (var (error, code) in failures)
        {
            var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
            using var source = new FailingSource(error);
            var failed = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await store.StageAsync(ticket, source, new(), cancellationToken));
            Assert.Equal(code, failed.Code);
            AssertSanitized(failed.ToString());
            Assert.False(source.WasDisposed);
            Assert.IsType<ArtifactResolution.NotCommitted>(Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        }
        using var valid = new ShortSource("valid after failed private staging"u8.ToArray());
        var committed = await PublishAsync(store, valid, new(1024), cancellationToken);
        Assert.Equal("valid after failed private staging"u8.ToArray(), await ReadAsync(store, committed.Stamp, cancellationToken));
    }

    public static async Task UnexpectedFaultAsync(
        IArtifactStore store, Action injectFault, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("decision survives unexpected failure"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        injectFault();
        var failed = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.CommitAsync(staged, new(), cancellationToken));
        Assert.Equal(ArtifactFailureCode.Uncertain, failed.Code);
        Assert.Equal(ArtifactAction.ReconcileExactTicket, failed.Action);
        AssertSanitized(failed.ToString());
        var resolution = Assert.IsType<ArtifactResolution.Committed>(
            Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        Assert.Equal("decision survives unexpected failure"u8.ToArray(), await ReadAsync(store, resolution.Receipt.Stamp, cancellationToken));
        Assert.Equal(resolution.Receipt, Success(await store.CommitAsync(staged, new(), cancellationToken)));
    }

    private static void AssertSanitized(string diagnostic)
    {
        Assert.DoesNotContain(Canary, diagnostic);
        Assert.DoesNotContain(OpaqueCanary, diagnostic);
    }

    private sealed class FailingSource(Exception error) : MemoryStream
    {
        public bool WasDisposed { get; private set; }
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
            => ValueTask.FromException<int>(error);
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
    }
}
