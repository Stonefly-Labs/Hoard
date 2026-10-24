using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public enum MetadataLeaseExpiryAction { Renew, Release, Guard }

public static class MetadataLeaseAssertions
{
    public static async Task GenerationOverflowAsync(
        IMetadataStore store,
        Func<CanonicalText, long, CancellationToken, ValueTask<MetadataResult<MetadataId>>> setGenerationAsync,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(setGenerationAsync);
        var resource = new CanonicalText("overflow-lease");
        await Commit(store, cancellationToken, new MetadataMutation.AcquireLease(resource, Id(3), 1));
        var lease = await Read<MetadataWorkLease>(store, new MetadataSelector.Lease(resource), cancellationToken);
        await Commit(store, cancellationToken, new MetadataMutation.ReleaseLease(resource, Id(3), lease.Generation, lease.Revision));
        Success(await setGenerationAsync(resource, long.MaxValue, cancellationToken));
        Assert.Equal(MetadataFailureCode.Capacity, Failed(await store.CommitAsync(
            Batch(await Ticket(store, cancellationToken),
                new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()),
                new MetadataMutation.AcquireLease(resource, Id(4), 1)), new(), cancellationToken)));
        await Missing(store, Registry().Selector, cancellationToken);
        var retained = await Read<MetadataWorkLease>(store, lease.Selector, cancellationToken);
        Assert.Equal(long.MaxValue, retained.Generation);
        Assert.IsType<MetadataOption<MetadataId>.None>(retained.Owner);
    }

    public static async Task ExpiryAtDecisionAsync(
        IMetadataStore store, MetadataConformanceClock clock, MetadataObservationControl observeAsync,
        MetadataLeaseExpiryAction action, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(clock);
        ArgumentNullException.ThrowIfNull(observeAsync);
        if (!Enum.IsDefined(action)) { throw new ArgumentException("BindingInvalid", nameof(action)); }
        var resource = new CanonicalText("maintenance");
        await Commit(store, cancellationToken, new MetadataMutation.AcquireLease(resource, Id(1), 1));
        var lease = await Read<MetadataWorkLease>(store, new MetadataSelector.Lease(resource), cancellationToken);
        clock.Set(new(lease.Expires.UnixMilliseconds - 1));
        var ticket = await Ticket(store, cancellationToken);
        MetadataMutation mutation = action switch
        {
            MetadataLeaseExpiryAction.Renew => new MetadataMutation.RenewLease(resource, Id(1), lease.Generation, lease.Revision, 1),
            MetadataLeaseExpiryAction.Release => new MetadataMutation.ReleaseLease(resource, Id(1), lease.Generation, lease.Revision),
            _ => new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent())
        };
        var batch = action == MetadataLeaseExpiryAction.Guard
            ? new MetadataMutationBatch(ticket, [mutation], new MetadataOption<MetadataLeaseGuard>.Some(new(resource, Id(1), lease.Generation)))
            : Batch(ticket, mutation);
        var observed = 0;
        await using (var observation = await observeAsync(MetadataObservationPoint.BeforeCommitDecision, () =>
        {
            Interlocked.Increment(ref observed);
            clock.Set(lease.Expires);
            return ValueTask.CompletedTask;
        }, cancellationToken))
        {
            Assert.Equal(MetadataFailureCode.Conflict, Failed(await store.CommitAsync(batch, new(), cancellationToken)));
            Assert.Equal(1, observed);
        }
        Assert.Equal(lease, await Read<MetadataWorkLease>(store, lease.Selector, cancellationToken));
        await Missing(store, Registry().Selector, cancellationToken);
        clock.Set(new(lease.Expires.UnixMilliseconds - 1));
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await store.CommitAsync(Batch(await Ticket(store, cancellationToken),
            new MetadataMutation.ReleaseLease(resource, Id(1), lease.Generation, lease.Revision)), new(), cancellationToken)));
        await Commit(store, cancellationToken, new MetadataMutation.AcquireLease(resource, Id(2), 1));
    }

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
