using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Artifacts;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;
using Xunit.Abstractions;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactNonCooperationTests(ITestOutputHelper output)
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Idle_read_expiry_fences_copy_without_touching_the_destination(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        await ArtifactOwnershipAssertions.IdleReadExpiryAsync(driver.Store, clock.Advance, default);
        driver.ObserveOriginal(output, nameof(ArtifactNonCooperationTests));
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
            await ArtifactLifecycleAssertions.ComposedShutdownAsync(session.Store, session.Authority, session.Identity,
                () => session.Authority.HasRetainedWork, session.DisposeAsync, default);
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
        await ArtifactLifecycleAssertions.ConcurrentCloseAsync(driver.Store, () => authority!.DelayRelease = true,
            () => authority!.Entered.Task, () => authority!.Released.TrySetResult(), default);
        driver.ObserveOriginal(output, nameof(ArtifactNonCooperationTests));
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
            mutation = ArtifactLifecycleAssertions.BoundedFailureAsync(driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)),
                new(TimeSpan.FromMilliseconds(100)), default).AsTask());
        }
        else
        {
            using var source = new ShortSource("stalled delete"u8.ToArray());
            var receipt = await PublishAsync(driver, source, new(1024));
            var deletion = Success(await driver.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default));
            driver.ObjectControls!.BeforeObjectDelete = StalledIo;
            mutation = ArtifactLifecycleAssertions.BoundedFailureAsync(
                driver.Store.DeleteAsync(deletion, new(TimeSpan.FromMilliseconds(100)), default).AsTask());
        }
        try
        {
            await ArtifactLifecycleAssertions.NativeBoundaryAsync(mutation,
                () => entered.Wait(TimeSpan.FromSeconds(2)), options => driver.StopAsync(options));
        }
        finally
        {
            release.Set();
            if (driver.LocalControls is { } localControls) { localControls.BeforeRecordWrite = null; }
            if (driver.ObjectControls is { } objects) { objects.BeforeObjectDelete = null; }
        }
        driver.ObserveOriginal(output, nameof(ArtifactNonCooperationTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Noncooperative_source_retains_bounded_ownership_and_blocks_admission_until_real_settlement(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactOwnershipAssertions.NoncooperativeSourceAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactNonCooperationTests));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Noncooperative_destination_cannot_release_live_read_protection_via_close_or_dispose(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactOwnershipAssertions.NoncooperativeDestinationAsync(driver.Store, default);
        driver.ObserveOriginal(output, nameof(ArtifactNonCooperationTests));
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
