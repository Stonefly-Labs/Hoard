using Hoard.Abstractions.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataLeaseTests
{
    [Fact]
    public async Task MP28_Generation_overflow_rejects_the_whole_group_and_preserves_tombstone()
    {
        await using var fixture = await OpenAsync();
        var resource = new CanonicalText("overflow-lease");
        await Commit(fixture, new MetadataMutation.AcquireLease(resource, Id(3), 1));
        var lease = await Read<MetadataWorkLease>(fixture, new MetadataSelector.Lease(resource));
        await Commit(fixture, new MetadataMutation.ReleaseLease(resource, Id(3), lease.Generation, lease.Revision));
        Success(await fixture.SetLeaseGenerationForTestAsync(resource, long.MaxValue));
        Assert.Equal(MetadataFailureCode.Capacity, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()),
            new MetadataMutation.AcquireLease(resource, Id(4), 1)), new(), default)));
        await Missing(fixture, Registry().Selector);
        var retained = await Read<MetadataWorkLease>(fixture, new MetadataSelector.Lease(resource));
        Assert.Equal(long.MaxValue, retained.Generation);
        Assert.IsType<MetadataOption<MetadataId>.None>(retained.Owner);
    }

    [Fact]
    public async Task MP28_Lease_owners_generations_and_revisions_are_fenced()
    {
        await using var fixture = await OpenAsync();
        var resource = new CanonicalText("maintenance");
        await Commit(fixture, new MetadataMutation.AcquireLease(resource, Id(1), 300));
        var lease = await Read<MetadataWorkLease>(fixture, new MetadataSelector.Lease(resource));
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.AcquireLease(resource, Id(2), 300)), new(), default)));
        await Commit(fixture, new MetadataMutation.RenewLease(resource, Id(1), lease.Generation, lease.Revision, 300));
        var renewed = await Read<MetadataWorkLease>(fixture, lease.Selector);
        Assert.NotEqual(lease.Revision, renewed.Revision);
        Assert.Equal(lease.Generation, renewed.Generation);
        await Commit(fixture, new MetadataMutation.ReleaseLease(resource, Id(1), renewed.Generation, renewed.Revision));
        await Commit(fixture, new MetadataMutation.AcquireLease(resource, Id(2), 300));
        var next = await Read<MetadataWorkLease>(fixture, lease.Selector);
        Assert.Equal(lease.Generation + 1, next.Generation);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.ReleaseLease(resource, Id(1), lease.Generation, lease.Revision)), new(), default)));
        Assert.Equal(next, await Read<MetadataWorkLease>(fixture, lease.Selector));
    }

    [Fact]
    public async Task MP29_Expiry_is_rechecked_at_the_final_decision_for_renew_release_and_guards()
    {
        foreach (var action in new[] { "renew", "release", "guard" })
        {
            var clock = new MetadataTestClock();
            await using var fixture = await OpenAsync(clock);
            var resource = new CanonicalText("maintenance");
            await Commit(fixture, new MetadataMutation.AcquireLease(resource, Id(1), 1));
            var lease = await Read<MetadataWorkLease>(fixture, new MetadataSelector.Lease(resource));
            clock.Set(lease.Expires.UnixMilliseconds - 1);
            var ticket = await Ticket(fixture);
            var mutation = action switch
            {
                "renew" => (MetadataMutation)new MetadataMutation.RenewLease(resource, Id(1), lease.Generation, lease.Revision, 1),
                "release" => new MetadataMutation.ReleaseLease(resource, Id(1), lease.Generation, lease.Revision),
                _ => new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent())
            };
            var batch = action == "guard" ? new MetadataMutationBatch(ticket, [mutation],
                new MetadataOption<MetadataLeaseGuard>.Some(new(resource, Id(1), lease.Generation))) : Batch(ticket, mutation);
            fixture.Controls.SetObserver("M0", () => { clock.Set(lease.Expires.UnixMilliseconds); return ValueTask.CompletedTask; });
            Assert.Equal(MetadataFailureCode.Conflict, Failed(await fixture.Store.CommitAsync(batch, new(), default)));
            fixture.Controls.RemoveObserver("M0");
            Assert.Equal(lease, await Read<MetadataWorkLease>(fixture, lease.Selector));
            await Missing(fixture, Registry().Selector);
            clock.Set(lease.Expires.UnixMilliseconds - 1);
            Assert.Equal(MetadataFailureCode.Conflict, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
                new MetadataMutation.ReleaseLease(resource, Id(1), lease.Generation, lease.Revision)), new(), default)));
            await Commit(fixture, new MetadataMutation.AcquireLease(resource, Id(2), 1));
        }
    }

    [Fact]
    public async Task MP30_Clock_rollback_does_not_undo_expiry_and_new_generation_is_retained()
    {
        var clock = new MetadataTestClock();
        await using var fixture = await OpenAsync(clock);
        var resource = new CanonicalText("maintenance");
        await Commit(fixture, new MetadataMutation.AcquireLease(resource, Id(1), 1));
        var first = await Read<MetadataWorkLease>(fixture, new MetadataSelector.Lease(resource));
        clock.Set(first.Expires.UnixMilliseconds);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.RenewLease(resource, Id(1), first.Generation, first.Revision, 1)), new(), default)));
        clock.Set(first.Acquired.UnixMilliseconds);
        await Commit(fixture, new MetadataMutation.AcquireLease(resource, Id(2), 1));
        var next = await Read<MetadataWorkLease>(fixture, first.Selector);
        Assert.Equal(first.Generation + 1, next.Generation);
        Assert.True(next.Acquired.UnixMilliseconds >= first.Expires.UnixMilliseconds);
        var invalid = new MetadataMutation.AcquireLease(new("different"), Id(3), 301);
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture), invalid), new(), default)));
        await Missing(fixture, new MetadataSelector.Lease(new("different")));
    }
}
