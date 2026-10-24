using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Artifacts;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactNonCooperationTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Idle_read_expiry_fences_copy_without_touching_the_destination(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        await ArtifactOwnershipAssertions.IdleReadExpiryAsync(driver.Store, clock.Advance, default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Composed_shutdown_cannot_release_store_while_authority_retains_a_reference_query(string provider)
    {
        using var root = new ArtifactTestRoot();
        var query = new TaskCompletionSource<Hoard.Fixtures.Artifacts.HostAdapters.ArtifactReferenceDecision>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var session = await Hoard.Fixtures.Artifacts.HostAdapters.ArtifactFixtureSession.CreateForQualificationAsync(
            provider, root.Path, (_, _) => new(query.Task));
        try
        {
            var ticket = Success(await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
            using var source = new ShortSource("authority shutdown"u8.ToArray());
            var staged = Success(await session.Store.StageAsync(ticket, source, new(), default));
            var receipt = Success(await session.Store.CommitAsync(staged, new(), default));
            var request = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Deletion,
                session.Identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
            Assert.IsType<ArtifactResult<IArtifactProtectionGuard>.Failure>(
                await session.Authority.AcquireAsync(request, new(TimeSpan.FromMilliseconds(20)), default));
            Assert.True(session.Authority.HasRetainedWork);
            await Assert.ThrowsAsync<InvalidOperationException>(() => session.DisposeAsync().AsTask());
            Assert.True(session.Authority.HasRetainedWork);
        }
        finally
        {
            query.TrySetResult(new(true, 0, Guid.NewGuid()));
            Assert.True(await session.Authority.DrainRetainedAsync(TimeSpan.FromSeconds(2)));
            await session.DisposeAsync();
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Concurrent_close_waits_for_the_same_physical_guard_release_and_fences_new_copy(string provider)
    {
        SlowReleaseAuthority? authority = null;
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            decorate: inner => authority = new(inner));
        using var source = new ShortSource("concurrent close"u8.ToArray());
        var receipt = await PublishAsync(driver, source, new(1024));
        authority!.DelayRelease = true;
        var session = Success(await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default));
        var close = session.CloseAsync(new(), default).AsTask();
        try
        {
            await authority.Entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
            var retry = await session.CloseAsync(new(TimeSpan.FromMilliseconds(20)), default);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(retry).Code);
            using var destination = new MemoryStream();
            Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await session.CopyToAsync(destination, new(), default)).Code);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default)).Code);
        }
        finally
        {
            authority.Released.TrySetResult();
            Success(await close);
            Success(await session.CloseAsync(new(), default));
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Deadline_and_stop_return_while_a_native_io_boundary_holds_provider_state(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            references: (_, _) => ValueTask.FromResult(new Hoard.Fixtures.Artifacts.HostAdapters.ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        using var entered = new ManualResetEventSlim();
        using var release = new ManualResetEventSlim();
        void StalledIo() { entered.Set(); release.Wait(); }
        Task mutation;
        if (driver.LocalControls is { } local)
        {
            local.BeforeRecordWrite = StalledIo;
            mutation = AssertBoundedFailure(driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)),
                new(TimeSpan.FromMilliseconds(100)), default).AsTask());
        }
        else
        {
            using var source = new ShortSource("stalled delete"u8.ToArray());
            var receipt = await PublishAsync(driver, source, new(1024));
            var deletion = Success(await driver.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default));
            driver.ObjectControls!.BeforeObjectDelete = StalledIo;
            mutation = AssertBoundedFailure(driver.Store.DeleteAsync(deletion, new(TimeSpan.FromMilliseconds(100)), default).AsTask());
        }
        try
        {
            Assert.True(await Task.Run(() => entered.Wait(TimeSpan.FromSeconds(2))));
            await mutation.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                await driver.StopAsync(new(TimeSpan.FromMilliseconds(20))).AsTask().WaitAsync(TimeSpan.FromSeconds(2))).Code);
        }
        finally
        {
            release.Set();
            if (driver.LocalControls is { } localControls) { localControls.BeforeRecordWrite = null; }
            if (driver.ObjectControls is { } objects) { objects.BeforeObjectDelete = null; }
        }

        static async Task AssertBoundedFailure<T>(Task<ArtifactResult<T>> task) where T : notnull
        {
            var failure = Assert.IsType<ArtifactResult<T>.Failure>(await task);
            Assert.True(failure.Code is ArtifactFailureCode.DeadlineExceeded or ArtifactFailureCode.Uncertain);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failure.Cleanup);
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Noncooperative_source_retains_bounded_ownership_and_blocks_admission_until_real_settlement(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactOwnershipAssertions.NoncooperativeSourceAsync(driver.Store, default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Noncooperative_destination_cannot_release_live_read_protection_via_close_or_dispose(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactOwnershipAssertions.NoncooperativeDestinationAsync(driver.Store, default);
    }

    private sealed class SlowReleaseAuthority(IArtifactCoordinationAuthority inner) : IArtifactCoordinationAuthority
    {
        public bool DelayRelease { get; set; }
        public TaskCompletionSource Entered { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource Released { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public async ValueTask<ArtifactResult<IArtifactProtectionGuard>> AcquireAsync(
            ArtifactProtectionRequest request, ArtifactCallOptions options, CancellationToken ct)
        {
            var result = await inner.AcquireAsync(request, options, ct);
            return DelayRelease && request.Operation == ArtifactProtectionOperation.Read
                && result is ArtifactResult<IArtifactProtectionGuard>.Success acquired
                ? new ArtifactResult<IArtifactProtectionGuard>.Success(new DelayedGuard(this, acquired.Value)) : result;
        }
        public ValueTask<ArtifactResult<IArtifactProtectionGuard>> RetainAsync(IArtifactProtectionGuard protection,
            ArtifactProtectionRequest expected, ArtifactCallOptions options, CancellationToken ct)
            => inner.RetainAsync(protection, expected, options, ct);
        private sealed class DelayedGuard(SlowReleaseAuthority owner, IArtifactProtectionGuard original) : IArtifactProtectionGuard
        {
            public ArtifactProtectionGrant Grant => original.Grant;
            public async ValueTask DisposeAsync()
            {
                owner.Entered.TrySetResult();
                await owner.Released.Task;
                await original.DisposeAsync();
            }
        }
    }
}
