using Hoard.Abstractions.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataReconciliationTests
{
    [Fact]
    public async Task MP15_Reconciliation_io_failure_preserves_the_unresolved_original_ticket()
    {
        await using var fixture = await OpenAsync();
        var ticket = await Ticket(fixture);
        fixture.Controls.SetObserver("reconcile.before_decision", () => throw new IOException(MetadataTestData.Canary));
        var failure = Assert.IsType<MetadataResult<MetadataResolution>.Failure>(
            await fixture.Store.ReconcileAsync(ticket, new(), default));
        fixture.Controls.RemoveObserver("reconcile.before_decision");
        Assert.Equal(MetadataFailureCode.Uncertain, failure.Code);
        Assert.Equal(MetadataRetryDisposition.Reconcile, failure.Retry);
        Assert.Equal(ticket, Assert.IsType<MetadataOption<MetadataOperationTicket>.Some>(failure.Ticket).Value);
        Success(await fixture.Store.CommitAsync(Batch(ticket, new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent())), new(), default));
        await Read<MetadataRegistry>(fixture, Registry().Selector);
    }

    [Fact]
    public async Task MP15_Reconciliation_without_exclusion_is_uncertain_not_a_noncommit_result()
    {
        await using var fixture = await OpenAsync();
        var batch = Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        var receipt = Success(await fixture.Store.CommitAsync(batch, new(), default));
        using (await fixture.HoldWriterForTestAsync())
        {
            using var cancellation = new CancellationTokenSource();
            cancellation.Cancel();
            foreach (var token in new[] { CancellationToken.None, cancellation.Token })
            {
                var result = await fixture.Store.ReconcileAsync(batch.Ticket, new(TimeSpan.FromMilliseconds(50)), token);
                var failure = Assert.IsType<MetadataResult<MetadataResolution>.Failure>(result);
                Assert.Equal(MetadataFailureCode.Uncertain, failure.Code);
                Assert.Equal(MetadataRetryDisposition.Reconcile, failure.Retry);
                Assert.Equal(batch.Ticket, Assert.IsType<MetadataOption<MetadataOperationTicket>.Some>(failure.Ticket).Value);
                await fixture.WhenIdleAsync();
            }
        }
        Assert.Equal(receipt.CommitId, Assert.IsType<MetadataResolution.Committed>(
            Success(await fixture.Store.ReconcileAsync(batch.Ticket, new(), default))).Receipt.CommitId);
    }

    [Fact]
    public async Task MP14_Replay_returns_original_receipt_and_changed_payload_conflicts()
    {
        await using var fixture = await OpenAsync();
        var (_, package) = await Seed(fixture);
        var entry = Entry(package);
        var publication = Publish(fixture, entry);
        var batch = Batch(await Ticket(fixture), publication);
        var original = Success(await fixture.Store.CommitAsync(batch, new(), default));
        fixture.Authority.Revoke(publication.Evidence);
        var replay = Success(await fixture.Store.CommitAsync(Batch(batch.Ticket,
            publication with { Evidence = new("fresh-opaque-handle-not-acquired-on-replay") }), new(), default));
        Assert.Equal(original.CommitId, replay.CommitId);
        Assert.Equal(1, fixture.Authority.Acquisitions);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await fixture.Store.CommitAsync(Batch(batch.Ticket,
            publication with { Record = entry with { Length = 2048 } }), new(), default)));
        Assert.Equal(1, (await Read<MetadataArtifactState>(fixture, new MetadataSelector.Artifact(entry.Digest))).LiveReferences);
    }

    [Fact]
    public async Task MP15_Lost_acknowledgment_reconciles_and_abandonment_fences_execution()
    {
        await using var fixture = await OpenAsync();
        var batch = Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        fixture.Controls.SetObserver("M1", () => throw new InvalidOperationException("synthetic lost acknowledgment"));
        Assert.Equal(MetadataFailureCode.Uncertain, Failed(await fixture.Store.CommitAsync(batch, new(), default)));
        fixture.Controls.RemoveObserver("M1");
        var resolved = Assert.IsType<MetadataResolution.Committed>(Success(await fixture.Store.ReconcileAsync(batch.Ticket, new(), default)));
        Assert.Equal(resolved.Receipt.CommitId, Success(await fixture.Store.CommitAsync(batch, new(), default)).CommitId);
        var abandoned = await Ticket(fixture);
        Assert.IsType<MetadataResolution.NotCommitted>(Success(await fixture.Store.ReconcileAsync(abandoned, new(), default)));
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await fixture.Store.CommitAsync(Batch(abandoned,
            new MetadataMutation.PutRegistry(Registry(2), new ExpectedRevision.Absent())), new(), default)));
        await Missing(fixture, Registry(2).Selector);
    }

    [Fact]
    public async Task MP16_Distinct_contributions_sum_and_uncertain_retries_do_not_duplicate()
    {
        await using var fixture = await OpenAsync();
        var (registry, _) = await Seed(fixture);
        var key = Aggregate(registry);
        var batch = Batch(await Ticket(fixture), new MetadataMutation.AddAggregateContribution(key, Delta(3)));
        fixture.Controls.SetObserver("M1", () => throw new InvalidOperationException("synthetic lost acknowledgment"));
        Assert.Equal(MetadataFailureCode.Uncertain, Failed(await fixture.Store.CommitAsync(batch, new(), default)));
        fixture.Controls.RemoveObserver("M1");
        var original = Assert.IsType<MetadataResolution.Committed>(Success(await fixture.Store.ReconcileAsync(batch.Ticket, new(), default))).Receipt;
        Assert.Equal(original.CommitId, Success(await fixture.Store.CommitAsync(batch, new(), default)).CommitId);
        var tickets = await Task.WhenAll(Enumerable.Range(1, 8).Select(async _ => await Ticket(fixture)));
        var outcomes = await Task.WhenAll(tickets.Select(ticket => fixture.Store.CommitAsync(
            Batch(ticket, new MetadataMutation.AddAggregateContribution(key, Delta(2))), new(), default).AsTask()));
        Assert.All(outcomes, result => Success(result));
        Assert.Equal(19, (await Read<MetadataAccessAggregate>(fixture, new MetadataSelector.Aggregate(key))).Counters.Hits);
    }

    [Fact]
    public async Task MP17_Exact_ticket_expiry_and_clock_rollback_cannot_revive_a_ticket()
    {
        var clock = new MetadataTestClock();
        await using var fixture = await OpenAsync(clock);
        var batch = Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        Success(await fixture.Store.CommitAsync(batch, new(), default));
        Assert.IsType<MetadataResolution.Committed>(Success(await fixture.Store.ReconcileAsync(batch.Ticket, new(), default)));
        clock.Set(batch.Ticket.Expires.UnixMilliseconds);
        Assert.Equal(MetadataFailureCode.ReconciliationExpired, Failed(await fixture.Store.CommitAsync(batch, new(), default)));
        clock.Set(batch.Ticket.Issued.UnixMilliseconds);
        Assert.Equal(MetadataFailureCode.ReconciliationExpired, Failed(await fixture.Store.CommitAsync(batch, new(), default)));
        await Ticket(fixture);
        Assert.Equal(MetadataFailureCode.ReconciliationExpired, Failed(await fixture.Store.ReconcileAsync(batch.Ticket, new(), default)));
        var forged = batch.Ticket with { Epoch = Id(99) };
        Assert.Equal(MetadataFailureCode.ReconciliationExpired, Failed(await fixture.Store.CommitAsync(
            Batch(forged, new MetadataMutation.PutRegistry(Registry(2), new ExpectedRevision.Absent())), new(), default)));
        await Missing(fixture, Registry(2).Selector);
    }
}
