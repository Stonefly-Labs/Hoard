using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactFailureAssertions
{
    internal const string Canary = "synthetic-artifact-secret-canary";
    private const string OpaqueCanary = "synthetic-artifact-private-proof";

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
