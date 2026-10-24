using Hoard.Testing.Conformance.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataReconciliationTests
{
    [Fact]
    public async Task MP15_Corrupt_persisted_receipts_fail_reconciliation_and_replay_without_duplicate_effects()
    {
        await using var fixture = await OpenAsync();
        await MetadataReconciliationAssertions.CorruptReceiptsAsync(fixture.Store,
            (request, token) => CommonCorruptionAsync(fixture, request, token), default);
        CommonDiagnosticAssertions(fixture);
    }

    [Fact]
    public async Task MP15_Reconciliation_io_failure_preserves_the_unresolved_original_ticket()
    {
        await using var fixture = await OpenAsync();
        await MetadataReconciliationAssertions.IoFailureAsync(fixture.Store, CommonObservations(fixture), default);
    }

    [Fact]
    public async Task MP15_Reconciliation_without_exclusion_is_uncertain_not_a_noncommit_result()
    {
        await using var fixture = await OpenAsync();
        await MetadataReconciliationAssertions.WriterContentionAsync(fixture.Store,
            token => CommonWriterAsync(fixture, token), token => CommonSettlementAsync(fixture, token), default);
    }

    [Fact]
    public async Task MP14_Replay_returns_original_receipt_and_changed_payload_conflicts()
    {
        await using var fixture = await OpenAsync();
        await MetadataPublicationAssertions.ReplayWithoutReacquisitionAsync(fixture.Store, CommonAuthority(fixture), default);
    }

    [Fact]
    public async Task MP15_Lost_acknowledgment_reconciles_and_abandonment_fences_execution()
    {
        await using var fixture = await OpenAsync();
        await MetadataReconciliationAssertions.LostAcknowledgmentAndAbandonmentAsync(
            fixture.Store, CommonObservations(fixture), default);
    }

    [Fact]
    public async Task MP16_Distinct_contributions_sum_and_uncertain_retries_do_not_duplicate()
    {
        await using var fixture = await OpenAsync();
        await MetadataReconciliationAssertions.DistinctContributionsAsync(fixture.Store, CommonObservations(fixture), default);
    }

    [Fact]
    public async Task MP17_Exact_ticket_expiry_and_clock_rollback_cannot_revive_a_ticket()
    {
        var clock = new MetadataTestClock();
        await using var fixture = await OpenAsync(clock);
        await MetadataTimeAssertions.TicketExpiryAndRollbackAsync(fixture.Store, instant => clock.Set(instant.UnixMilliseconds), default);
    }
}
