using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Testing.Conformance.Artifacts;

public sealed class ArtifactAuthorityAssertions(ArtifactStoreIdentity store)
{
    private readonly ArtifactDigest digest = new(new string('a', 64));
    private static readonly ArtifactCallOptions Options = new();

    private ArtifactProtectionRequest Request(ArtifactProtectionOperation operation = ArtifactProtectionOperation.Read)
        => new(Guid.NewGuid(), operation, store, digest,
            operation == ArtifactProtectionOperation.Deletion
                ? new ArtifactOption<ArtifactStamp>.Some(new ArtifactStamp(store, new ArtifactIdentity(digest, 1), Guid.NewGuid()))
                : new ArtifactOption<ArtifactStamp>.None());
    private static IArtifactProtectionGuard Guard(ArtifactResult<IArtifactProtectionGuard> result)
        => Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Success>(result).Value;

    public async Task SharedAdmissionAsync(IArtifactCoordinationAuthority authority, CancellationToken cancellationToken)
    {
        var request = Request();
        var original = Guard(await authority.AcquireAsync(request, Options, cancellationToken));
        var retained = Guard(await authority.RetainAsync(original, request, Options, cancellationToken));
        Assert.Equal(original.Grant, retained.Grant);
        await original.DisposeAsync();
        Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
            await authority.RetainAsync(original, request, Options, cancellationToken));
        var retainedAgain = Guard(await authority.RetainAsync(retained, request, Options, cancellationToken));
        await retainedAgain.DisposeAsync();
        await retained.DisposeAsync();
    }

    public async Task RejectCopiedHandlesAsync(
        IArtifactCoordinationAuthority authority, IArtifactCoordinationAuthority foreign, CancellationToken cancellationToken)
    {
        var request = Request();
        await using var guard = Guard(await authority.AcquireAsync(request, Options, cancellationToken));
        await using var copied = new CopiedGuard(guard.Grant);
        foreach (var result in new[] {
            await authority.RetainAsync(copied, request, Options, cancellationToken),
            await foreign.RetainAsync(guard, request, Options, cancellationToken),
            await authority.RetainAsync(guard, Request(), Options, cancellationToken) })
        { Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(result).Code); }
        var foreignRequest = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Read,
            new ArtifactStoreIdentity(store.ProviderModuleId, store.InstanceId, Guid.NewGuid()), digest);
        Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
            await authority.AcquireAsync(foreignRequest, Options, cancellationToken));
    }

    public async Task HeldAfterExpiryAsync(
        IArtifactCoordinationAuthority authority, Action<TimeSpan> advanceClock, Func<DateTimeOffset> utcNow,
        CancellationToken cancellationToken)
    {
        var request = Request();
        await using var guard = Guard(await authority.AcquireAsync(request, Options, cancellationToken));
        advanceClock(TimeSpan.FromMinutes(1));
        Assert.True(guard.Grant.AdmissionExpiry <= utcNow());
        await using var retained = Guard(await authority.RetainAsync(guard, request, Options, cancellationToken));
        Assert.Equal(guard.Grant, retained.Grant);
        Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
            await authority.RetainAsync(guard, Request(), Options, cancellationToken));
    }

    public async Task MissingReferencesAsync(IArtifactCoordinationAuthority authority, CancellationToken cancellationToken)
    {
        await using var read = Guard(await authority.AcquireAsync(Request(), Options, cancellationToken));
        var deletion = authority.AcquireAsync(Request(ArtifactProtectionOperation.Deletion),
            new ArtifactCallOptions(TimeSpan.FromMilliseconds(20)), cancellationToken);
        var result = await deletion;
        Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(result);
    }

    public async Task QueuedExclusiveAsync(
        IArtifactCoordinationAuthority authority, Func<int> waitingAdmissions, CancellationToken cancellationToken)
    {
        var request = Request();
        var read = Guard(await authority.AcquireAsync(request, Options, cancellationToken));
        var deletion = authority.AcquireAsync(Request(ArtifactProtectionOperation.Deletion), Options, cancellationToken).AsTask();
        Assert.Equal(1, waitingAdmissions());
        var nextRead = authority.AcquireAsync(Request(), Options, cancellationToken).AsTask();
        Assert.Equal(2, waitingAdmissions());
        var retention = Guard(await authority.RetainAsync(read, request, Options, cancellationToken));
        await read.DisposeAsync();
        Assert.False(deletion.IsCompleted);
        await retention.DisposeAsync();
        var exclusive = Guard(await deletion);
        Assert.False(nextRead.IsCompleted);
        await exclusive.DisposeAsync();
        await using var admitted = Guard(await nextRead);
    }

    public async Task RetainedReferenceAsync(
        IArtifactCoordinationAuthority authority, Func<bool> hasRetainedWork, Action completeReference,
        Func<TimeSpan, ValueTask<bool>> drainRetained, CancellationToken cancellationToken)
    {
        var result = await authority.AcquireAsync(Request(ArtifactProtectionOperation.Deletion),
            new ArtifactCallOptions(TimeSpan.FromMilliseconds(20)), cancellationToken);
        var failed = Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(result);
        Assert.Equal(ArtifactFailureCode.CleanupIncomplete, failed.Code);
        Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
        Assert.True(hasRetainedWork());
        Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
            await authority.AcquireAsync(Request(), Options, cancellationToken));
        completeReference();
        Assert.True(await drainRetained(TimeSpan.FromSeconds(5)));
        Assert.False(hasRetainedWork());
        await using var read = Guard(await authority.AcquireAsync(Request(), Options, cancellationToken));
    }

    private sealed class CopiedGuard(ArtifactProtectionGrant grant) : IArtifactProtectionGuard
    {
        public ArtifactProtectionGrant Grant => grant;
        public ValueTask DisposeAsync() => ValueTask.CompletedTask;
    }
}
