using Hoard.Abstractions.Metadata;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataTimeAssertions
{
    public static Task TicketExpiryAndRollbackAsync(
        IMetadataStore store, MetadataConformanceClock clock, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(clock);
        return TicketExpiryAndRollbackAsync(store, clock.Set, cancellationToken);
    }

    public static async Task TicketExpiryAndRollbackAsync(
        IMetadataStore store, Action<MetadataInstant> setTime, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(setTime);
        var batch = Batch(await Ticket(store, cancellationToken), new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        Success(await store.CommitAsync(batch, new(), cancellationToken));
        Assert.IsType<MetadataResolution.Committed>(Success(await store.ReconcileAsync(batch.Ticket, new(), cancellationToken)));
        setTime(batch.Ticket.Expires);
        Assert.Equal(MetadataFailureCode.ReconciliationExpired, Failed(await store.CommitAsync(batch, new(), cancellationToken)));
        setTime(batch.Ticket.Issued);
        Assert.Equal(MetadataFailureCode.ReconciliationExpired, Failed(await store.CommitAsync(batch, new(), cancellationToken)));
        await Ticket(store, cancellationToken);
        Assert.Equal(MetadataFailureCode.ReconciliationExpired, Failed(await store.ReconcileAsync(batch.Ticket, new(), cancellationToken)));
        var forged = batch.Ticket with { Epoch = Id(99) };
        Assert.Equal(MetadataFailureCode.ReconciliationExpired, Failed(await store.CommitAsync(
            Batch(forged, new MetadataMutation.PutRegistry(Registry(2), new ExpectedRevision.Absent())), new(), cancellationToken)));
        await Missing(store, Registry(2).Selector, cancellationToken);
    }

    public static Task LeaseRollbackAsync(
        IMetadataStore store, MetadataConformanceClock clock, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(clock);
        return LeaseRollbackAsync(store, clock.Set, cancellationToken);
    }

    public static async Task LeaseRollbackAsync(
        IMetadataStore store, Action<MetadataInstant> setTime, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(setTime);
        var resource = new CanonicalText("maintenance");
        await Commit(store, cancellationToken, new MetadataMutation.AcquireLease(resource, Id(1), 1));
        var first = await Read<MetadataWorkLease>(store, new MetadataSelector.Lease(resource), cancellationToken);
        setTime(first.Expires);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.RenewLease(resource, Id(1), first.Generation, first.Revision, 1)), new(), cancellationToken)));
        setTime(first.Acquired);
        await Commit(store, cancellationToken, new MetadataMutation.AcquireLease(resource, Id(2), 1));
        var next = await Read<MetadataWorkLease>(store, first.Selector, cancellationToken);
        Assert.Equal(first.Generation + 1, next.Generation);
        Assert.True(next.Acquired.UnixMilliseconds >= first.Expires.UnixMilliseconds);
        var invalid = new MetadataMutation.AcquireLease(new("different"), Id(3), 301);
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.CommitAsync(
            Batch(await Ticket(store, cancellationToken), invalid), new(), cancellationToken)));
        await Missing(store, new MetadataSelector.Lease(new("different")), cancellationToken);
    }
}
