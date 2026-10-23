using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactAuthorityTests
{
    private readonly ArtifactStoreIdentity store = new("fixture.artifact", Guid.NewGuid(), Guid.NewGuid());
    private readonly ArtifactDigest digest = new(new string('a', 64));
    private static readonly ArtifactCallOptions Options = new();

    private ArtifactProtectionRequest Request(ArtifactProtectionOperation operation = ArtifactProtectionOperation.Read)
        => new(Guid.NewGuid(), operation, store, digest,
            operation == ArtifactProtectionOperation.Deletion
                ? new ArtifactOption<ArtifactStamp>.Some(new ArtifactStamp(store, new ArtifactIdentity(digest, 1), Guid.NewGuid()))
                : new ArtifactOption<ArtifactStamp>.None());
    private static IArtifactProtectionGuard Guard(ArtifactResult<IArtifactProtectionGuard> result)
        => Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Success>(result).Value;

    [Fact]
    public async Task Shared_admission_retention_and_independent_disposal_use_one_recognized_handle()
    {
        var authority = new ArtifactCoordinationAuthority(store);
        var request = Request();
        var original = Guard(await authority.AcquireAsync(request, Options, default));
        var retained = Guard(await authority.RetainAsync(original, request, Options, default));
        Assert.Equal(original.Grant, retained.Grant);
        await original.DisposeAsync();
        Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
            await authority.RetainAsync(original, request, Options, default));
        var retainedAgain = Guard(await authority.RetainAsync(retained, request, Options, default));
        await retainedAgain.DisposeAsync();
        await retained.DisposeAsync();
    }

    [Fact]
    public async Task Copied_foreign_changed_scope_and_disposed_handles_never_authorize_retention()
    {
        var authority = new ArtifactCoordinationAuthority(store);
        var foreign = new ArtifactCoordinationAuthority(store);
        var request = Request();
        await using var guard = Guard(await authority.AcquireAsync(request, Options, default));
        await using var copied = new CopiedGuard(guard.Grant);
        foreach (var result in new[] {
            await authority.RetainAsync(copied, request, Options, default),
            await foreign.RetainAsync(guard, request, Options, default),
            await authority.RetainAsync(guard, Request(), Options, default) })
        { Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(result).Code); }
        var foreignRequest = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Read,
            new ArtifactStoreIdentity(store.ProviderModuleId, store.InstanceId, Guid.NewGuid()), digest);
        Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
            await authority.AcquireAsync(foreignRequest, Options, default));
    }

    [Fact]
    public async Task Held_same_operation_can_settle_after_expiry_without_reentrant_admission()
    {
        var clock = new ArtifactTestClock();
        var authority = new ArtifactCoordinationAuthority(store, clock);
        var request = Request();
        await using var guard = Guard(await authority.AcquireAsync(request, Options, default));
        clock.Advance(TimeSpan.FromMinutes(1));
        Assert.True(guard.Grant.AdmissionExpiry <= clock.GetUtcNow());
        await using var retained = Guard(await authority.RetainAsync(guard, request, Options, default));
        Assert.Equal(guard.Grant, retained.Grant);
        Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
            await authority.RetainAsync(guard, Request(), Options, default));
    }

    [Fact]
    public async Task Missing_reference_authority_denies_deletion_not_shared_reads()
    {
        var authority = new ArtifactCoordinationAuthority(store);
        await using var read = Guard(await authority.AcquireAsync(Request(), Options, default));
        var deletion = authority.AcquireAsync(Request(ArtifactProtectionOperation.Deletion),
            new ArtifactCallOptions(TimeSpan.FromMilliseconds(20)), default);
        var result = await deletion;
        Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(result);
    }

    [Fact]
    public async Task Queued_exclusive_admission_closes_new_shared_admission_and_retention_never_reenters()
    {
        var authority = new ArtifactCoordinationAuthority(store, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        var request = Request();
        var read = Guard(await authority.AcquireAsync(request, Options, default));
        var deletion = authority.AcquireAsync(Request(ArtifactProtectionOperation.Deletion), Options, default).AsTask();
        Assert.Equal(1, authority.WaitingAdmissions);
        var nextRead = authority.AcquireAsync(Request(), Options, default).AsTask();
        Assert.Equal(2, authority.WaitingAdmissions);
        var retention = Guard(await authority.RetainAsync(read, request, Options, default));
        await read.DisposeAsync();
        Assert.False(deletion.IsCompleted);
        await retention.DisposeAsync();
        var exclusive = Guard(await deletion);
        Assert.False(nextRead.IsCompleted);
        await exclusive.DisposeAsync();
        await using var admitted = Guard(await nextRead);
    }

    [Fact]
    public async Task Noncooperative_reference_query_retains_exclusion_blocks_admission_and_settles_before_release()
    {
        var pending = new TaskCompletionSource<ArtifactReferenceDecision>(TaskCreationOptions.RunContinuationsAsynchronously);
        var authority = new ArtifactCoordinationAuthority(store, references: (_, _) => new(pending.Task));
        var result = await authority.AcquireAsync(Request(ArtifactProtectionOperation.Deletion),
            new ArtifactCallOptions(TimeSpan.FromMilliseconds(20)), default);
        var failed = Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(result);
        Assert.Equal(ArtifactFailureCode.CleanupIncomplete, failed.Code);
        Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
        Assert.True(authority.HasRetainedWork);
        Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
            await authority.AcquireAsync(Request(), Options, default));
        pending.SetResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid()));
        Assert.True(await authority.DrainRetainedAsync(TimeSpan.FromSeconds(5)));
        Assert.False(authority.HasRetainedWork);
        await using var read = Guard(await authority.AcquireAsync(Request(), Options, default));
    }

    private sealed class CopiedGuard(ArtifactProtectionGrant grant) : IArtifactProtectionGuard
    {
        public ArtifactProtectionGrant Grant => grant;
        public ValueTask DisposeAsync() => ValueTask.CompletedTask;
    }
}
