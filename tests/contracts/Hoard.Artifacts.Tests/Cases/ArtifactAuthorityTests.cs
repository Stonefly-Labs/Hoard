using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Testing.Conformance.Artifacts;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactAuthorityTests
{
    private readonly ArtifactStoreIdentity store = new("fixture.artifact", Guid.NewGuid(), Guid.NewGuid());

    [Fact]
    public async Task Shared_admission_retention_and_independent_disposal_use_one_recognized_handle()
    {
        var authority = new ArtifactCoordinationAuthority(store);
        await new ArtifactAuthorityAssertions(store).SharedAdmissionAsync(authority, default);
    }

    [Fact]
    public async Task Copied_foreign_changed_scope_and_disposed_handles_never_authorize_retention()
    {
        var authority = new ArtifactCoordinationAuthority(store);
        var foreign = new ArtifactCoordinationAuthority(store);
        await new ArtifactAuthorityAssertions(store).RejectCopiedHandlesAsync(authority, foreign, default);
    }

    [Fact]
    public async Task Held_same_operation_can_settle_after_expiry_without_reentrant_admission()
    {
        var clock = new ArtifactTestClock();
        var authority = new ArtifactCoordinationAuthority(store, clock);
        await new ArtifactAuthorityAssertions(store).HeldAfterExpiryAsync(
            authority, clock.Advance, clock.GetUtcNow, default);
    }

    [Fact]
    public async Task Missing_reference_authority_denies_deletion_not_shared_reads()
    {
        var authority = new ArtifactCoordinationAuthority(store);
        await new ArtifactAuthorityAssertions(store).MissingReferencesAsync(authority, default);
    }

    [Fact]
    public async Task Queued_exclusive_admission_closes_new_shared_admission_and_retention_never_reenters()
    {
        var authority = new ArtifactCoordinationAuthority(store, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        await new ArtifactAuthorityAssertions(store).QueuedExclusiveAsync(
            authority, () => authority.WaitingAdmissions, default);
    }

    [Fact]
    public async Task Noncooperative_reference_query_retains_exclusion_blocks_admission_and_settles_before_release()
    {
        var pending = new TaskCompletionSource<ArtifactReferenceDecision>(TaskCreationOptions.RunContinuationsAsynchronously);
        var authority = new ArtifactCoordinationAuthority(store, references: (_, _) => new(pending.Task));
        await new ArtifactAuthorityAssertions(store).RetainedReferenceAsync(authority, () => authority.HasRetainedWork,
            () => pending.SetResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())),
            timeout => authority.DrainRetainedAsync(timeout), default);
    }

    [Fact]
    public async Task Shared_authority_assertion_rejects_repaired_copied_handle_and_accepts_original_authority()
    {
        await using (var mutation = new RepairedCopiedHandle(new ArtifactCoordinationAuthority(store)))
        {
            await Assert.ThrowsAsync<Xunit.Sdk.IsTypeException>(() =>
                new ArtifactAuthorityAssertions(store).RejectCopiedHandlesAsync(
                    mutation, new ArtifactCoordinationAuthority(store), default));
            Assert.Equal(1, mutation.ActualCopiedDenials);
            Assert.Equal(1, mutation.RepairedRetentions);
        }
        await new ArtifactAuthorityAssertions(store).RejectCopiedHandlesAsync(
            new ArtifactCoordinationAuthority(store), new ArtifactCoordinationAuthority(store), default);
    }

    private sealed class RepairedCopiedHandle(IArtifactCoordinationAuthority inner)
        : IArtifactCoordinationAuthority, IAsyncDisposable
    {
        private IArtifactProtectionGuard? current;
        private readonly List<IArtifactProtectionGuard> retained = [];
        public int ActualCopiedDenials { get; private set; }
        public int RepairedRetentions => retained.Count;

        public async ValueTask<ArtifactResult<IArtifactProtectionGuard>> AcquireAsync(
            ArtifactProtectionRequest request, ArtifactCallOptions options, CancellationToken ct)
        {
            var result = await inner.AcquireAsync(request, options, ct);
            if (result is ArtifactResult<IArtifactProtectionGuard>.Success acquired) { current = acquired.Value; }
            return result;
        }

        public async ValueTask<ArtifactResult<IArtifactProtectionGuard>> RetainAsync(
            IArtifactProtectionGuard protection, ArtifactProtectionRequest expected, ArtifactCallOptions options, CancellationToken ct)
        {
            var result = await inner.RetainAsync(protection, expected, options, ct);
            if (current is { } original && !ReferenceEquals(protection, original) && protection.Grant == original.Grant)
            {
                if (result is not ArtifactResult<IArtifactProtectionGuard>.Failure { Code: ArtifactFailureCode.Denied })
                { throw new InvalidOperationException("Mutation requires actual copied-handle rejection."); }
                ActualCopiedDenials++;
                var repaired = await inner.RetainAsync(original, expected, options, ct);
                if (repaired is not ArtifactResult<IArtifactProtectionGuard>.Success recognized)
                { throw new InvalidOperationException("Mutation requires actual recognized retention."); }
                retained.Add(recognized.Value);
                return repaired;
            }
            return result;
        }

        public async ValueTask DisposeAsync()
        {
            foreach (var guard in retained) { await guard.DisposeAsync(); }
        }
    }
}
