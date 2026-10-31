using Hoard.Testing.Conformance.Metadata;
using Xunit.Abstractions;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataDeadlineTests(ITestOutputHelper output)
{
    [Fact]
    public async Task MP19_Actual_writer_contention_consumes_the_original_budget_without_committing()
    {
        await using var fixture = await OpenAsync();
        await MetadataDeadlineAssertions.WriterBudgetAsync(fixture.Store,
            token => CommonWriterAsync(fixture, token), token => CommonSettlementAsync(fixture, token), default);
        ObserveOriginal(output, fixture, nameof(MetadataDeadlineTests));
    }

    [Fact]
    public async Task MP37_Incomplete_cleanup_reports_failure_and_keeps_activity_owned()
    {
        var fixture = await OpenAsync();
        await MetadataDeadlineAssertions.IncompleteCleanupAsync(fixture.Store, CommonObservations(fixture),
            () => CommonCounters(fixture), fixture.DisposeAsync, token => CommonSettlementAsync(fixture, token), default);
        ObserveOriginal(output, fixture, nameof(MetadataDeadlineTests));
    }

    [Fact]
    public async Task MP18_Cancellation_before_decision_is_definite_and_after_attempt_is_uncertain()
    {
        await using var fixture = await OpenAsync();
        await MetadataDeadlineAssertions.CancellationDecisionsAsync(fixture.Store, CommonObservations(fixture),
            token => CommonSettlementAsync(fixture, token), default);
        ObserveOriginal(output, fixture, nameof(MetadataDeadlineTests));
    }

    [Fact]
    public async Task MP19_Queue_capacity_and_held_work_deadlines_have_finite_owned_results()
    {
        await using var fixture = await OpenAsync();
        await MetadataDeadlineAssertions.QueueCapacityAsync(fixture.Store, CommonObservations(fixture),
            token => CommonSettlementAsync(fixture, token), default);
        ObserveOriginal(output, fixture, nameof(MetadataDeadlineTests));
    }

    [Fact]
    public async Task MP37_Disposal_owns_active_work_and_does_not_release_it_early()
    {
        var fixture = await OpenAsync();
        await MetadataDeadlineAssertions.DisposalOwnershipAsync(
            fixture.Store, CommonObservations(fixture), fixture.DisposeAsync, default);
        ObserveOriginal(output, fixture, nameof(MetadataDeadlineTests));
    }

    [Fact]
    public async Task MP18_Known_exception_types_after_commit_attempt_are_still_uncertain()
    {
        await using var fixture = await OpenAsync();
        await MetadataDeadlineAssertions.KnownExceptionsAsync(fixture.Store, CommonObservations(fixture), default);
        ObserveOriginal(output, fixture, nameof(MetadataDeadlineTests));
    }
}
