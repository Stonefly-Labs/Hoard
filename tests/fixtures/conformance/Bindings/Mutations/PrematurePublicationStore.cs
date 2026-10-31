using Hoard.Abstractions.Storage;

namespace Hoard.Fixtures.Conformance.Bindings.Mutations;

internal sealed class PrematurePublicationStore(IArtifactStore inner, bool enabled) : IArtifactStore, IAsyncDisposable
{
    private readonly List<IArtifactReadSession> reads = [];
    public int Publications { get; private set; }
    public ArtifactCapabilities Capabilities => inner.Capabilities;

    public async ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
        ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct)
    {
        var result = await inner.StageAsync(ticket, source, options, ct);
        if (enabled && result is ArtifactResult<ArtifactStagedWrite>.Success staged)
        {
            if (await inner.CommitAsync(staged.Value, options, ct) is not ArtifactResult<ArtifactMutationReceipt>.Success)
            { throw new InvalidOperationException("MutationSetupFailed"); }
            Publications++;
        }
        return result;
    }

    public async ValueTask<ArtifactResult<IArtifactReadSession>> OpenReadAsync(
        ArtifactReadRequest request, ArtifactCallOptions options, CancellationToken ct)
    {
        var result = await inner.OpenReadAsync(request, options, ct);
        if (result is ArtifactResult<IArtifactReadSession>.Success read) { reads.Add(read.Value); }
        return result;
    }

    public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(
        ArtifactWriteIntent intent, ArtifactCallOptions options, CancellationToken ct) =>
        inner.ReserveWriteAsync(intent, options, ct);
    public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveDeleteAsync(
        ArtifactDeleteIntent intent, ArtifactCallOptions options, CancellationToken ct) =>
        inner.ReserveDeleteAsync(intent, options, ct);
    public ValueTask<ArtifactResult<ArtifactStagingOwner>> RenewAsync(
        ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct) =>
        inner.RenewAsync(owner, options, ct);
    public ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(
        ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct) =>
        inner.CommitAsync(staged, options, ct);
    public ValueTask<ArtifactResult<ArtifactMutationReceipt>> DeleteAsync(
        ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct) =>
        inner.DeleteAsync(ticket, options, ct);
    public ValueTask<ArtifactResult<ArtifactResolution>> ReconcileAsync(
        ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct) =>
        inner.ReconcileAsync(ticket, options, ct);
    public ValueTask<ArtifactResult<ArtifactCleanupReport>> AbandonAsync(
        ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct) =>
        inner.AbandonAsync(owner, options, ct);

    public async ValueTask DisposeAsync()
    {
        foreach (var read in reads) { await read.DisposeAsync(); }
    }
}
