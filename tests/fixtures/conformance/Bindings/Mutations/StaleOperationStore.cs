using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Conformance.Bindings.Mutations;

internal sealed class StaleOperationStore(IMetadataStore inner, bool enabled) : IMetadataStore
{
    private MetadataResult<MetadataCommitReceipt>.Success? committed;
    public int Replays { get; private set; }

    public async ValueTask<MetadataResult<MetadataCommitReceipt>> CommitAsync(
        MetadataMutationBatch request, MetadataCallOptions options, CancellationToken cancellationToken)
    {
        if (enabled && committed is not null && request.Ticket == committed.Value.Ticket)
        {
            Replays++;
            return committed;
        }
        var result = await inner.CommitAsync(request, options, cancellationToken);
        if (result is MetadataResult<MetadataCommitReceipt>.Success success) { committed = success; }
        return result;
    }

    public ValueTask<MetadataResult<MetadataOperationTicket>> ReserveOperationAsync(
        MetadataCallOptions options, CancellationToken cancellationToken) =>
        inner.ReserveOperationAsync(options, cancellationToken);
    public ValueTask<MetadataResult<MetadataReadSnapshot>> ReadAsync(
        MetadataReadGroup request, MetadataCallOptions options, CancellationToken cancellationToken) =>
        inner.ReadAsync(request, options, cancellationToken);
    public ValueTask<MetadataResult<MetadataPage>> ReadPageAsync(
        MetadataPageQuery request, MetadataCallOptions options, CancellationToken cancellationToken) =>
        inner.ReadPageAsync(request, options, cancellationToken);
    public ValueTask<MetadataResult<MetadataResolution>> ReconcileAsync(
        MetadataOperationTicket ticket, MetadataCallOptions options, CancellationToken cancellationToken) =>
        inner.ReconcileAsync(ticket, options, cancellationToken);
    public ValueTask DisposeAsync() => inner.DisposeAsync();
}
