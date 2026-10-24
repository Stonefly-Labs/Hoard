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
        await MetadataPublicationAssertions.OrphanNotRollbackAsync(
            fixture.Store, CommonAuthority(fixture), CommonObservations(fixture), default);
    }

    [Fact]
    public async Task MP27_Protection_survives_caller_timeout_through_owned_settlement()
    {
        await using var fixture = await OpenAsync();
        await MetadataPublicationAssertions.ProtectionThroughSettlementAsync(
            fixture.Store, CommonAuthority(fixture), CommonObservations(fixture),
            cancellationToken => new(fixture.WhenIdleAsync().WaitAsync(cancellationToken)), default);
    }

    [Fact]
    public async Task MP31_Invalid_telemetry_rolls_back_its_declared_entry_and_reference_group()
    {
        await using var fixture = await OpenAsync();
        await MetadataReferenceAssertions.InvalidTelemetryRollsBackEntryAndReferencesAsync(fixture.Store, CommonAuthority(fixture), default);
    }
}
