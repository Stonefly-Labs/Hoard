using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataPublicationTests
{
    [Fact]
    public async Task MP23_Publication_requires_committed_matching_authority_evidence()
    {
        await using var fixture = await OpenAsync();
        await MetadataPublicationAssertions.MatchingEvidenceAsync(fixture.Store, CommonAuthority(fixture), default);
    }

    [Fact]
    public async Task MP24_Entry_edges_replace_remove_and_compete_without_double_counts()
    {
        await using var fixture = await OpenAsync();
        await MetadataReferenceAssertions.EntryReplacementAndRemovalAsync(fixture.Store, CommonAuthority(fixture), default);
    }

    [Fact]
    public async Task MP25_Zero_reference_confirmation_is_invalidated_even_by_ABA()
    {
        await using var fixture = await OpenAsync();
        await MetadataReferenceAssertions.ZeroReferenceAbaFencingAsync(fixture.Store, CommonAuthority(fixture), default);
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
        await MetadataReferenceAssertions.InvalidTelemetryRollsBackEntryAndReferencesAsync(fixture.Store, CommonAuthority(fixture), default);
    }
}
