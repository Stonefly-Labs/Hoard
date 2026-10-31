using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Testing.Conformance.Artifacts;
using Xunit.Abstractions;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactBudgetTests(ITestOutputHelper output)
{
    [Fact]
    public async Task Local_reclaimed_incarnations_remain_budgeted_until_expiry_without_removing_the_recreated_blob()
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync("local", clock,
            new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, committedIdentities: 1),
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactHistoryAssertions.ReclaimedIncarnationBudgetAsync(driver.Store, clock.SetUtc, default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Reclaimed_identity_history_has_a_finite_budget_and_expiry_restores_new_digest_admission(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock,
            new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, committedIdentities: 1),
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactHistoryAssertions.ReclaimedIdentityExpiryAsync(
            driver.Store, driver.Maintenance, driver.Identity, clock.SetUtc, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests));
    }

    [Theory]
    [InlineData("local", "tickets")]
    [InlineData("object", "tickets")]
    [InlineData("local", "dependencies")]
    [InlineData("object", "dependencies")]
    [InlineData("local", "decisions")]
    [InlineData("object", "decisions")]
    [InlineData("local", "reclamation")]
    public async Task History_maintenance_bounds_examined_candidates_even_when_none_can_be_retired(string provider, string kind)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1048576, committedIdentities: 128),
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactHistoryAssertions.CandidateBoundsAsync(driver.Store, kind,
            observe =>
            {
                if (driver.LocalControls is { } local) { local.BeforeHistoryCandidate = observe; }
                else { driver.ObjectControls!.BeforeHistoryCandidate = observe; }
            }, default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task History_candidate_pages_resume_past_ineligible_entries_and_preserve_a_faulted_candidate(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactHistoryAssertions.CandidateResumeAsync(driver.Store,
            observe =>
            {
                if (driver.LocalControls is { } local) { local.BeforeHistoryCandidate = observe; }
                else { driver.ObjectControls!.BeforeHistoryCandidate = observe; }
            }, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests));
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("object", false)]
    [InlineData("local", true)]
    [InlineData("object", true)]
    public async Task Expired_ticket_history_restores_write_and_delete_capacity_without_losing_committed_or_removed_identity(
        string provider, bool reserveDelete)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock,
            new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, liveTickets: 4),
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactHistoryAssertions.TicketExpiryCapacityAsync(driver.Store, driver.Maintenance,
            driver.Identity, clock.Advance, clock.SetUtc, reserveDelete, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests), parameter: $"reserveDelete: {reserveDelete}");
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Producer_and_consumer_inactivity_deadlines_release_cooperative_work_without_closing_borrowed_streams(
        string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactOwnershipAssertions.CooperativeInactivityAsync(driver.Store, driver.WhenIdleAsync, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cancellation_of_an_admitted_commit_cannot_fence_an_externally_renewed_owner(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        await using var barrier = new ArtifactTestBarrier("renew-before-cancellation-settlement");
        await ArtifactOwnershipAssertions.ExternalRenewalCancellationAsync(driver.Store, clock.Advance, driver.WhenIdleAsync,
            () => SetObserver(driver, "publish.before-decision", "pointer.compare", () => new(barrier.HoldAsync())),
            token => barrier.Entered.WaitAsync(token),
            () =>
            {
                if (driver.LocalControls is { } local) { local.RemoveObserver("publish.before-decision"); }
                else { driver.ObjectControls!.RemoveObserver("pointer.compare"); }
                barrier.Release();
            }, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cancellation_after_progress_renewal_fences_the_same_admitted_owner(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        await ArtifactOwnershipAssertions.ProgressRenewalCancellationAsync(driver.Store, clock.Advance, driver.WhenIdleAsync,
            observe => SetObserver(driver, "publish.progress", "object.commit-progress", observe), default);
    }

    [Theory]
    [InlineData("local", "renewed")]
    [InlineData("object", "renewed")]
    [InlineData("local", "completion")]
    [InlineData("object", "completion")]
    [InlineData("local", "handle")]
    [InlineData("object", "handle")]
    public async Task Cancelled_invalid_or_stale_commit_cannot_fence_the_current_verified_handle(
        string provider, string alteration)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        await ArtifactOwnershipAssertions.CancelledStagedDescriptorAsync(
            driver.Store, clock.Advance, driver.WhenIdleAsync, alteration, default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cancellation_after_resource_release_cannot_retain_an_already_settled_operation(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await using var released = new ArtifactTestBarrier("resources-released-task-not-completed");
        await ArtifactHandoffAssertions.ReleasedCancellationAsync(driver.Store,
            observe => SetObserver(driver, "operation.released", "object.operation-released", observe),
            released.HoldAsync, () => released.Entered,
            () =>
            {
                driver.LocalControls?.RemoveObserver("operation.released");
                driver.ObjectControls?.RemoveObserver("object.operation-released");
            }, released.Release, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests));
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("object", false)]
    [InlineData("local", true)]
    [InlineData("object", true)]
    public async Task Cancellation_at_result_handoff_cannot_discard_a_reserved_ticket_or_live_read(
        string provider, bool readSession)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new(artifactBytes: 1024, stagingBytes: 1024, transferSlots: 1, waitingCalls: 0),
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await using var released = new ArtifactTestBarrier("successful-result-before-task-completion");
        await ArtifactHandoffAssertions.SuccessfulResultAsync(driver.Store, readSession,
            observe => SetObserver(driver, "operation.released", "object.operation-released", observe),
            released.HoldAsync, () => released.Entered,
            () =>
            {
                driver.LocalControls?.RemoveObserver("operation.released");
                driver.ObjectControls?.RemoveObserver("object.operation-released");
            }, released.Release, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests), parameter: $"readSession: {readSession}");
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("object", false)]
    [InlineData("local", true)]
    [InlineData("object", true)]
    public async Task Cancellation_before_result_handoff_reclaims_the_unclaimed_ticket_or_read(
        string provider, bool readSession)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new(artifactBytes: 1024, stagingBytes: 1024, transferSlots: 1, waitingCalls: 0, liveTickets: 2),
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await using var produced = new ArtifactTestBarrier("successful-result-not-yet-handed-off");
        await ArtifactHandoffAssertions.UnclaimedResultAsync(driver.Store, readSession,
            () => SetObserver(driver, "operation.completed", "object.operation-completed", () => new(produced.HoldAsync())),
            () => produced.Entered,
            () =>
            {
                driver.LocalControls?.RemoveObserver("operation.completed");
                driver.ObjectControls?.RemoveObserver("object.operation-completed");
                produced.Release();
            }, driver.WhenIdleAsync, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests), parameter: $"readSession: {readSession}");
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Undelivered_verified_staging_is_reclaimed_after_ownership_expiry(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock,
            new(artifactBytes: 1024, stagingBytes: 1024));
        await using var produced = new ArtifactTestBarrier("verified-owner-expired-before-delivery");
        await ArtifactHandoffAssertions.ExpiredStagingAsync(driver.Store, clock.Advance,
            () => SetObserver(driver, "operation.completed", "object.operation-completed", () => new(produced.HoldAsync())),
            () => produced.Entered,
            () =>
            {
                driver.LocalControls?.RemoveObserver("operation.completed");
                driver.ObjectControls?.RemoveObserver("object.operation-completed");
                produced.Release();
            }, driver.WhenIdleAsync, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests));
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("object", false)]
    [InlineData("local", true)]
    [InlineData("object", true)]
    public async Task Failed_unclaimed_result_cleanup_blocks_admission_and_stop_until_exact_retry(
        string provider, bool readSession)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new(artifactBytes: 1024, stagingBytes: 1024, transferSlots: 1, waitingCalls: 0));
        await using var produced = new ArtifactTestBarrier("unclaimed-cleanup-failure");
        await ArtifactBudgetAssertions.UnclaimedCleanupFailureAsync(driver.Store, readSession,
            () => SetObserver(driver, "operation.completed", "object.operation-completed", () => new(produced.HoldAsync())),
            () => produced.Entered,
            () =>
            {
                driver.LocalControls?.RemoveObserver("operation.completed");
                driver.ObjectControls?.RemoveObserver("object.operation-completed");
                produced.Release();
            },
            observe => SetObserver(driver, "operation.reclaim", "object.operation-reclaim", observe),
            () =>
            {
                driver.LocalControls?.RemoveObserver("operation.reclaim");
                driver.ObjectControls?.RemoveObserver("object.operation-reclaim");
            }, driver.WhenIdleAsync, driver.StopAsync, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests), parameter: $"readSession: {readSession}");
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("object", false)]
    [InlineData("local", true)]
    [InlineData("object", true)]
    public async Task Cancelled_commit_before_decision_fences_the_ticket_and_cannot_publish_on_retry(
        string provider, bool alreadyCancelled)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactBudgetAssertions.CancelledCommitFencingAsync(
            driver.Store, driver.Authority, driver.Identity, driver.WhenIdleAsync, alreadyCancelled, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests), parameter: $"alreadyCancelled: {alreadyCancelled}");
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Full_transfer_queue_rejects_without_input_io_and_capacity_returns_after_release(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new ArtifactLimits(artifactBytes: 1, stagingBytes: 3, transferSlots: 1, waitingCalls: 1));
        await ArtifactBudgetAssertions.TransferQueueAsync(driver.Store,
            observe =>
            {
                if (driver.LocalControls is { } local) { local.SetObserver("transfer.queued", observe); }
                else { driver.ObjectControls!.SetObserver("object.transfer-queued", observe); }
            }, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cap_crossing_rejects_excess_before_append_and_capacity_recovers(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new ArtifactLimits(10, 10, 1));
        await ArtifactBudgetAssertions.CapCrossingAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Total_deadline_includes_shared_authority_contention_before_publication(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await ArtifactBudgetAssertions.AuthorityDeadlineAsync(driver.Store, driver.Authority, driver.Identity, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cooperative_cancellation_stops_input_without_disposing_borrowed_stream(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactBudgetAssertions.CooperativeCancellationAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactBudgetTests));
    }

    internal sealed class PendingSource(bool cooperative) : ArtifactOwnershipAssertions.PendingSource(cooperative);
}
