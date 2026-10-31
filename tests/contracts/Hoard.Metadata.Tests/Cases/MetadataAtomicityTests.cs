using Hoard.Testing.Conformance.Metadata;
using Xunit.Abstractions;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataAtomicityTests(ITestOutputHelper output)
{
    [Fact]
    public async Task MP09_Independent_engine_reads_cannot_see_an_uncommitted_candidate()
    {
        await using var fixture = await OpenAsync();
        await MetadataAtomicityAssertions.IndependentCandidateAsync(
            fixture.Store, CommonObservations(fixture), fixture.ObserveIndependentSnapshotAsync, default);
        ObserveOriginal(output, fixture, nameof(MetadataAtomicityTests));
    }

    [Fact]
    public async Task MP09_Each_faulted_candidate_is_invisible_and_success_is_complete()
    {
        await using var fixture = await OpenAsync();
        await MetadataAtomicityAssertions.FaultedCandidatesAsync(fixture.Store, CommonObservations(fixture), default);
        foreach (var diagnostic in fixture.Controls.Diagnostics)
        {
            MetadataTestData.AssertSanitized(diagnostic);
            Assert.DoesNotContain(MetadataReconciliationAssertions.CorruptionCanary, diagnostic);
        }
        ObserveOriginal(output, fixture, nameof(MetadataAtomicityTests));
    }

    [Fact]
    public async Task MP10_Grouped_reads_keep_one_root_while_independent_reads_can_straddle()
    {
        await using var fixture = await OpenAsync();
        await MetadataAtomicityAssertions.GroupedReadsAsync(fixture.Store, CommonObservations(fixture), default);
        ObserveOriginal(output, fixture, nameof(MetadataAtomicityTests));
    }

    [Fact]
    public async Task MP11_Competing_creates_have_one_winner()
    {
        await using var fixture = await OpenAsync();
        await MetadataConcurrencyAssertions.CompetingCreatesAsync(fixture.Store, default);
        ObserveOriginal(output, fixture, nameof(MetadataAtomicityTests));
    }

    [Fact]
    public async Task MP12_Revision_races_and_delete_recreate_are_fenced()
    {
        await using var fixture = await OpenAsync();
        await MetadataConcurrencyAssertions.RevisionRacesAsync(fixture.Store, default);
        ObserveOriginal(output, fixture, nameof(MetadataAtomicityTests));
    }
}
