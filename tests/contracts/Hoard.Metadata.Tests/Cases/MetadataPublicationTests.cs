using Hoard.Abstractions.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataPublicationTests
{
    [Fact]
    public async Task MP23_Publication_requires_committed_matching_authority_evidence()
    {
        await using var fixture = await OpenAsync();
        var (_, package) = await Seed(fixture);
        var entry = Entry(package);
        foreach (var evidence in new[]
        {
            new MetadataArtifactEvidence("forged-handle"),
            fixture.Authority.Register(Digest(2), entry.Length),
            fixture.Authority.Register(entry.Digest, entry.Length + 1)
        })
        {
            Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
                new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), evidence)), new(), default)));
            await Missing(fixture, entry.Selector);
            await Missing(fixture, new MetadataSelector.Artifact(entry.Digest));
            Assert.Equal(0, fixture.Authority.ActiveGuards);
        }
        var revoked = fixture.Authority.Register(entry.Digest, entry.Length);
        fixture.Authority.Revoke(revoked);
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), revoked)), new(), default)));
        await Commit(fixture, Publish(fixture, entry));
        Assert.Equal(1, (await Read<MetadataArtifactState>(fixture, new MetadataSelector.Artifact(entry.Digest))).LiveReferences);
    }

    [Fact]
    public async Task MP24_Entry_edges_replace_remove_and_compete_without_double_counts()
    {
        await using var fixture = await OpenAsync();
        var (_, package) = await Seed(fixture);
        var first = Entry(package);
        var second = Entry(package, target: "/second");
        await Commit(fixture, Publish(fixture, first), Publish(fixture, second));
        Assert.Equal(2, (await Read<MetadataArtifactState>(fixture, new MetadataSelector.Artifact(first.Digest))).LiveReferences);
        first = await Read<MetadataCacheEntry>(fixture, first.Selector);
        var replacement = first with { Digest = Digest(2) };
        var tickets = await Task.WhenAll(Enumerable.Range(0, 4).Select(async _ => await Ticket(fixture)));
        var outcomes = await Task.WhenAll(tickets.Select(ticket => fixture.Store.CommitAsync(Batch(ticket,
            Publish(fixture, replacement, new ExpectedRevision.Match(first.Revision))), new(), default).AsTask()));
        Assert.Single(outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Success>());
        Assert.Equal(3, outcomes.OfType<MetadataResult<MetadataCommitReceipt>.Failure>().Count(result => result.Code == MetadataFailureCode.Conflict));
        Assert.Equal(1, (await Read<MetadataArtifactState>(fixture, new MetadataSelector.Artifact(first.Digest))).LiveReferences);
        Assert.Equal(1, (await Read<MetadataArtifactState>(fixture, new MetadataSelector.Artifact(replacement.Digest))).LiveReferences);
        first = await Read<MetadataCacheEntry>(fixture, first.Selector);
        second = await Read<MetadataCacheEntry>(fixture, second.Selector);
        await Commit(fixture, new MetadataMutation.DeleteCacheEntry(first.Identity, first.Revision),
            new MetadataMutation.DeleteCacheEntry(second.Identity, second.Revision));
        Assert.Equal(0, (await Read<MetadataArtifactState>(fixture, new MetadataSelector.Artifact(first.Digest))).LiveReferences);
        Assert.Equal(0, (await Read<MetadataArtifactState>(fixture, new MetadataSelector.Artifact(second.Digest))).LiveReferences);
    }

    [Fact]
    public async Task MP25_Zero_reference_confirmation_is_invalidated_even_by_ABA()
    {
        await using var fixture = await OpenAsync();
        var (_, package) = await Seed(fixture);
        var entry = Entry(package);
        await Commit(fixture, Publish(fixture, entry));
        entry = await Read<MetadataCacheEntry>(fixture, entry.Selector);
        await Commit(fixture, new MetadataMutation.DeleteCacheEntry(entry.Identity, entry.Revision));
        var zero = await Read<MetadataArtifactState>(fixture, new MetadataSelector.Artifact(entry.Digest));
        await Commit(fixture, new MetadataMutation.ConfirmUnreferenced(entry.Digest, zero.Revision));
        await Commit(fixture, Publish(fixture, entry));
        entry = await Read<MetadataCacheEntry>(fixture, entry.Selector);
        await Commit(fixture, new MetadataMutation.DeleteCacheEntry(entry.Identity, entry.Revision));
        var again = await Read<MetadataArtifactState>(fixture, zero.Selector);
        Assert.NotEqual(zero.Revision, again.Revision);
        Assert.Equal(0, again.LiveReferences);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.ConfirmUnreferenced(entry.Digest, zero.Revision)), new(), default)));
        await Commit(fixture, new MetadataMutation.ConfirmUnreferenced(entry.Digest, again.Revision));
    }

    [Fact]
    public async Task MP26_Blob_commit_then_metadata_failure_is_an_orphan_not_a_blob_rollback()
    {
        await using var fixture = await OpenAsync();
        var (_, package) = await Seed(fixture);
        var entry = Entry(package);
        var committedBlob = fixture.Authority.Register(entry.Digest, entry.Length);
        fixture.Controls.SetObserver("mutation.applied", () => throw new InvalidOperationException("synthetic metadata failure"));
        Assert.Equal(MetadataFailureCode.InternalFailure, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), committedBlob)), new(), default)));
        fixture.Controls.RemoveObserver("mutation.applied");
        await Missing(fixture, entry.Selector);
        await Missing(fixture, new MetadataSelector.Artifact(entry.Digest));
        var artifact = Success(await fixture.Authority.AcquireAsync(committedBlob, new(), default));
        Assert.Equal(entry.Digest, artifact.Artifact.Digest);
        await artifact.DisposeAsync();
        Assert.Equal(0, fixture.Authority.ActiveGuards);
        await Commit(fixture, new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), committedBlob));
    }

    [Fact]
    public async Task MP27_Protection_survives_caller_timeout_through_owned_settlement()
    {
        await using var fixture = await OpenAsync();
        var (_, package) = await Seed(fixture);
        await using var barrier = new MetadataTestBarrier();
        var entry = Entry(package);
        var batch = Batch(await Ticket(fixture), Publish(fixture, entry));
        fixture.Controls.SetObserver("M1", () => new(barrier.HoldAsync()));
        var committing = fixture.Store.CommitAsync(batch, new(TimeSpan.FromMilliseconds(200)), default).AsTask();
        await barrier.Entered;
        Assert.Equal(1, fixture.Authority.ActiveGuards);
        Assert.Equal(MetadataFailureCode.Uncertain, Failed(await committing));
        Assert.Equal(1, fixture.Authority.ActiveGuards);
        Assert.Equal(MetadataFailureCode.Unavailable, Failed(await fixture.Store.ReserveOperationAsync(new(), default)));
        barrier.Release();
        await fixture.WhenIdleAsync();
        fixture.Controls.RemoveObserver("M1");
        Assert.Equal(0, fixture.Authority.ActiveGuards);
        Assert.IsType<MetadataResolution.Committed>(Success(await fixture.Store.ReconcileAsync(batch.Ticket, new(), default)));
        var acquisitions = fixture.Authority.Acquisitions;
        Success(await fixture.Store.CommitAsync(batch, new(), default));
        Assert.Equal(acquisitions, fixture.Authority.Acquisitions);
    }

    [Fact]
    public async Task MP31_Invalid_telemetry_rolls_back_its_declared_entry_and_reference_group()
    {
        await using var fixture = await OpenAsync();
        var (registry, package) = await Seed(fixture);
        var entry = Entry(package);
        var delta = Delta() with { Hits = -1 };
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await fixture.Store.CommitAsync(Batch(await Ticket(fixture),
            Publish(fixture, entry), new MetadataMutation.AddAggregateContribution(Aggregate(registry), delta)), new(), default)));
        await Missing(fixture, entry.Selector);
        await Missing(fixture, new MetadataSelector.Artifact(entry.Digest));
        await Commit(fixture, Publish(fixture, entry), new MetadataMutation.AddAggregateContribution(Aggregate(registry), Delta()));
        Assert.Equal(1, (await Read<MetadataArtifactState>(fixture, new MetadataSelector.Artifact(entry.Digest))).LiveReferences);
        Assert.Equal(1, (await Read<MetadataAccessAggregate>(fixture, new MetadataSelector.Aggregate(Aggregate(registry)))).Counters.Hits);
    }
}
