using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataLeaseTests
{
    [Fact]
    public async Task Shared_clock_control_can_target_the_original_fixture_clock()
    {
        var clock = new MetadataTestClock();
        await using var fixture = await OpenAsync(clock);
        MetadataInstant? expiry = null;
        await MetadataTimeAssertions.TicketExpiryAndRollbackAsync(fixture.Store, instant =>
        {
            expiry ??= instant;
            clock.Set(instant.UnixMilliseconds);
        }, default);
        Assert.NotNull(expiry);
        Assert.True(clock.GetUtcNow().ToUnixTimeMilliseconds() < expiry.UnixMilliseconds);
        Assert.True((await Ticket(fixture)).Issued.UnixMilliseconds >= expiry.UnixMilliseconds);
    }

    [Fact]
    public async Task MP28_Generation_overflow_rejects_the_whole_group_and_preserves_tombstone()
    {
        await using var fixture = await OpenAsync();
        await MetadataLeaseAssertions.GenerationOverflowAsync(fixture.Store, (resource, generation, cancellationToken) =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            return fixture.SetLeaseGenerationForTestAsync(resource, generation);
        }, default);
    }

    [Fact]
    public async Task MP28_Lease_owners_generations_and_revisions_are_fenced()
    {
        await using var fixture = await OpenAsync();
        await MetadataLeaseAssertions.OwnerGenerationAndRevisionFencesAsync(fixture.Store, default);
    }

    [Fact]
    public async Task MP29_Expiry_is_rechecked_at_the_final_decision_for_renew_release_and_guards()
    {
        foreach (var action in new[] { MetadataLeaseExpiryAction.Renew, MetadataLeaseExpiryAction.Release, MetadataLeaseExpiryAction.Guard })
        {
            var clock = new MetadataTestClock();
            await using var fixture = await OpenAsync(clock);
            await MetadataLeaseAssertions.ExpiryAtDecisionAsync(
                fixture.Store, instant => clock.Set(instant.UnixMilliseconds), CommonObservations(fixture), action, default);
        }
    }

    [Fact]
    public async Task MP30_Clock_rollback_does_not_undo_expiry_and_new_generation_is_retained()
    {
        var clock = new MetadataTestClock();
        await using var fixture = await OpenAsync(clock);
        await MetadataTimeAssertions.LeaseRollbackAsync(fixture.Store, instant => clock.Set(instant.UnixMilliseconds), default);
    }
}
