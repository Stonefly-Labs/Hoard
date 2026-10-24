using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Testing.Conformance.Artifacts;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactAuthorityOwnershipTests
{
    private readonly ArtifactStoreIdentity store = new("fixture.artifact", Guid.NewGuid(), Guid.NewGuid());

    [Fact]
    public async Task Shutdown_fence_joins_recognized_retained_and_queued_guards_before_reopen()
    {
        var authority = new ArtifactCoordinationAuthority(store, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await new ArtifactAuthorityAssertions(store).ShutdownHoldingsAsync(
            authority, authority.CloseAdmissionsAndObserveSettlementForQualificationAsync,
            authority.ReopenAdmissionsForQualification, () => authority.WaitingAdmissions, default);
    }

    [Fact]
    public async Task Shutdown_fence_joins_actual_noncooperating_reference_query_before_reopen()
    {
        var reference = new TaskCompletionSource<ArtifactReferenceDecision>(TaskCreationOptions.RunContinuationsAsynchronously);
        var authority = new ArtifactCoordinationAuthority(store, references: (_, _) => new(reference.Task));
        await new ArtifactAuthorityAssertions(store).ShutdownRetainedReferenceAsync(
            authority, authority.CloseAdmissionsAndObserveSettlementForQualificationAsync,
            authority.ReopenAdmissionsForQualification, () => authority.HasRetainedWork,
            () => reference.TrySetResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())), default);
    }

    [Fact]
    public async Task Shutdown_fence_observes_canceled_waiter_without_losing_the_current_guard()
    {
        var queries = 0;
        var authority = new ArtifactCoordinationAuthority(store, references: (_, _) =>
        {
            Interlocked.Increment(ref queries);
            return ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid()));
        });
        await new ArtifactAuthorityAssertions(store).ShutdownCanceledWaiterAsync(
            authority, authority.CloseAdmissionsAndObserveSettlementForQualificationAsync,
            () => authority.WaitingAdmissions, default);
        Assert.Equal(0, queries);
    }
}
