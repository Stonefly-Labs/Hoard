namespace Hoard.Abstractions.Metadata;

public interface IMetadataStore : IAsyncDisposable
{
    ValueTask<MetadataResult<MetadataOperationTicket>> ReserveOperationAsync(
        MetadataCallOptions options, CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataReadSnapshot>> ReadAsync(
        MetadataReadGroup request, MetadataCallOptions options, CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataPage>> ReadPageAsync(
        MetadataPageQuery request, MetadataCallOptions options, CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataCommitReceipt>> CommitAsync(
        MetadataMutationBatch request, MetadataCallOptions options, CancellationToken cancellationToken);
    ValueTask<MetadataResult<MetadataResolution>> ReconcileAsync(
        MetadataOperationTicket ticket, MetadataCallOptions options, CancellationToken cancellationToken);
}
