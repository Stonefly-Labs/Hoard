using Hoard.Abstractions.Metadata;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataLeaseAssertions
{
    public static async Task OwnerGenerationAndRevisionFencesAsync(IMetadataStore store, CancellationToken cancellationToken)
    {
        var resource = new CanonicalText("maintenance");
        await Commit(store, cancellationToken, new MetadataMutation.AcquireLease(resource, Id(1), 300));
        var lease = await Read<MetadataWorkLease>(store, new MetadataSelector.Lease(resource), cancellationToken);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.AcquireLease(resource, Id(2), 300)), new(), cancellationToken)));
        await Commit(store, cancellationToken, new MetadataMutation.RenewLease(resource, Id(1), lease.Generation, lease.Revision, 300));
        var renewed = await Read<MetadataWorkLease>(store, lease.Selector, cancellationToken);
        Assert.NotEqual(lease.Revision, renewed.Revision);
        Assert.Equal(lease.Generation, renewed.Generation);
        await Commit(store, cancellationToken, new MetadataMutation.ReleaseLease(resource, Id(1), renewed.Generation, renewed.Revision));
        await Commit(store, cancellationToken, new MetadataMutation.AcquireLease(resource, Id(2), 300));
        var next = await Read<MetadataWorkLease>(store, lease.Selector, cancellationToken);
        Assert.Equal(lease.Generation + 1, next.Generation);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.ReleaseLease(resource, Id(1), lease.Generation, lease.Revision)), new(), cancellationToken)));
        Assert.Equal(next, await Read<MetadataWorkLease>(store, lease.Selector, cancellationToken));
    }
}
