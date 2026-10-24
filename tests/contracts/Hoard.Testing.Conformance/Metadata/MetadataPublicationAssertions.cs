using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Bindings;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataPublicationAssertions
{
    public static async Task MatchingEvidenceAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, CancellationToken cancellationToken)
    {
        var (_, package) = await Seed(store, cancellationToken);
        var entry = Entry(package);
        foreach (var evidence in new[] { new MetadataArtifactEvidence("forged-handle"),
            authority.Register(Digest(2), entry.Length), authority.Register(entry.Digest, entry.Length + 1) })
        {
            Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.CommitAsync(
                Batch(await Ticket(store, cancellationToken),
                    new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), evidence)), new(), cancellationToken)));
            await Missing(store, entry.Selector, cancellationToken);
            await Missing(store, new MetadataSelector.Artifact(entry.Digest), cancellationToken);
            Assert.Equal(0, authority.ActiveGuards);
        }
        var revoked = authority.Register(entry.Digest, entry.Length);
        authority.Revoke(revoked);
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.CommitAsync(
            Batch(await Ticket(store, cancellationToken),
                new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), revoked)), new(), cancellationToken)));
        await Missing(store, entry.Selector, cancellationToken);
        await Missing(store, new MetadataSelector.Artifact(entry.Digest), cancellationToken);
        await Commit(store, cancellationToken, Publish(authority, entry));
        Assert.Equal(1, (await Read<MetadataArtifactState>(
            store, new MetadataSelector.Artifact(entry.Digest), cancellationToken)).LiveReferences);
        Assert.Equal(0, authority.ActiveGuards);
    }

    public static async Task ReplayWithoutReacquisitionAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, CancellationToken cancellationToken)
    {
        var (_, package) = await Seed(store, cancellationToken);
        var entry = Entry(package);
        var publication = Publish(authority, entry);
        var batch = Batch(await Ticket(store, cancellationToken), publication);
        var original = Success(await store.CommitAsync(batch, new(), cancellationToken));
        authority.Revoke(publication.Evidence);
        var replay = Success(await store.CommitAsync(
            Batch(batch.Ticket, publication with { Evidence = new("fresh-opaque-handle-not-acquired-on-replay") }), new(), cancellationToken));
        Assert.Equal(original.CommitId, replay.CommitId);
        Assert.Equal(1, authority.Acquisitions);
        Assert.Equal(MetadataFailureCode.Conflict, Failed(await store.CommitAsync(
            Batch(batch.Ticket, publication with { Record = entry with { Length = 2048 } }), new(), cancellationToken)));
        Assert.Equal(1, (await Read<MetadataArtifactState>(
            store, new MetadataSelector.Artifact(entry.Digest), cancellationToken)).LiveReferences);
        Assert.Equal(0, authority.ActiveGuards);
    }

    public static async Task OrphanNotRollbackAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority,
        MetadataObservationControl observeAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        var (_, package) = await Seed(store, cancellationToken);
        var entry = Entry(package);
        var committed = authority.Register(entry.Digest, entry.Length);
        var observed = 0;
        await using (var observation = await observeAsync(MetadataObservationPoint.MutationApplied, () =>
        {
            Interlocked.Increment(ref observed);
            throw new InvalidOperationException(MetadataReconciliationAssertions.CorruptionCanary);
        }, cancellationToken))
        {
            Assert.Equal(MetadataFailureCode.InternalFailure, Failed(await store.CommitAsync(
                Batch(await Ticket(store, cancellationToken),
                    new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), committed)), new(), cancellationToken)));
            Assert.Equal(1, observed);
        }
        await Missing(store, entry.Selector, cancellationToken);
        await Missing(store, new MetadataSelector.Artifact(entry.Digest), cancellationToken);
        await using (var guard = Success(await authority.AcquireAsync(committed, new(), cancellationToken)))
        { Assert.Equal(entry.Digest, guard.Artifact.Digest); }
        Assert.Equal(0, authority.ActiveGuards);
        await Commit(store, cancellationToken,
            new MetadataMutation.PublishCacheEntry(entry, new ExpectedRevision.Absent(), committed));
    }

    public static async Task ProtectionThroughSettlementAsync(
        IMetadataStore store, IMetadataConformanceAuthority authority, MetadataObservationControl observeAsync,
        Func<CancellationToken, ValueTask> awaitSettlementAsync, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(observeAsync);
        ArgumentNullException.ThrowIfNull(awaitSettlementAsync);
        var (_, package) = await Seed(store, cancellationToken);
        await using var barrier = new MetadataConformanceBarrier();
        var entry = Entry(package);
        var batch = Batch(await Ticket(store, cancellationToken), Publish(authority, entry));
        await using (var observation = await observeAsync(
            MetadataObservationPoint.AfterCommitDecision, barrier.HoldAsync, cancellationToken))
        {
            var committing = store.CommitAsync(batch, new(TimeSpan.FromMilliseconds(200)), cancellationToken).AsTask();
            try
            {
                await barrier.WaitForEntryAsync(cancellationToken);
                Assert.Equal(1, authority.ActiveGuards);
                Assert.Equal(MetadataFailureCode.Uncertain, Failed(await committing));
                Assert.Equal(1, authority.ActiveGuards);
                Assert.Equal(MetadataFailureCode.Unavailable, Failed(await store.ReserveOperationAsync(new(), cancellationToken)));
            }
            finally
            {
                barrier.Release();
                await Task.WhenAll(committing, Settle());
            }
        }
        Assert.Equal(0, authority.ActiveGuards);
        Assert.IsType<MetadataResolution.Committed>(
            Success(await store.ReconcileAsync(batch.Ticket, new(), cancellationToken)));
        var acquisitions = authority.Acquisitions;
        Success(await store.CommitAsync(batch, new(), cancellationToken));
        Assert.Equal(acquisitions, authority.Acquisitions);

        async Task Settle() => await awaitSettlementAsync(CancellationToken.None);
    }
}
