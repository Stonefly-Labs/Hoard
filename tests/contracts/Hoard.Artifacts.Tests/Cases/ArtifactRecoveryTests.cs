using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactRecoveryTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Progressing_commit_renews_owner_across_the_original_ttl(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        var bytes = new byte[1048576];
        using var first = new MemoryStream(bytes, writable: false);
        await PublishAsync(driver, first, new(2097152));
        using var duplicate = new MemoryStream(bytes, writable: false);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(2097152)), new(), default));
        var staged = Success(await driver.Store.StageAsync(ticket, duplicate, new(), default));
        var progress = 0;
        ValueTask Advance()
        {
            clock.Advance(TimeSpan.FromSeconds(11));
            Interlocked.Increment(ref progress);
            return ValueTask.CompletedTask;
        }
        if (driver.LocalControls is { } local) { local.SetObserver("publish.progress", Advance); }
        else { driver.ObjectControls!.SetObserver("object.commit-progress", Advance); }
        var receipt = Success(await driver.Store.CommitAsync(staged, new(), default));
        Assert.True(progress >= 4);
        Assert.Equal(ArtifactMutationOutcome.AlreadyPresentVerified, receipt.Outcome);
        Assert.Equal(receipt, Success(await driver.Store.CommitAsync(staged, new(), default)));
    }

    [Fact]
    public async Task Reopen_finishes_staging_release_after_a_durable_commit_receipt()
    {
        using var root = new ArtifactTestRoot();
        var identity = new ArtifactStoreIdentity("fixture.artifact.local", Guid.NewGuid(), Guid.NewGuid());
        var authority = new ArtifactCoordinationAuthority(identity);
        var limits = new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024);
        var controls = new LocalFaultControls();
        var original = new LocalArtifactStore(root.Path, controls: controls);
        Success(await original.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, identity, authority, limits), new(), default));
        var ticket = Success(await original.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("durable receipt before reservation release"u8.ToArray());
        var staged = Success(await original.StageAsync(ticket, source, new(), default));
        var writes = 0;
        controls.BeforeRecordWrite = () =>
        {
            if (Interlocked.Increment(ref writes) == 3) { throw new IOException("Interrupted reservation release."); }
        };
        try
        {
            Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await original.CommitAsync(staged, new(), default)).Code);
        }
        finally
        {
            controls.BeforeRecordWrite = null;
            Success(await original.StopAsync(new(), default));
        }
        var reopened = new LocalArtifactStore(root.Path);
        try
        {
            Success(await reopened.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible, identity, authority, limits), new(), default));
            Assert.IsType<ArtifactResolution.Committed>(Success(await reopened.ReconcileAsync(ticket, new(), default)));
            Success(await reopened.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        }
        finally { Success(await reopened.StopAsync(new(), default)); }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Expired_ownerless_reservations_release_capacity_without_replaying_old_tickets(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock, new(artifactBytes: 1, stagingBytes: 1));
        var expired = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default));
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default)).Code);
        clock.Advance(TimeSpan.FromHours(24));
        Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default));
        using var source = new ShortSource([1]);
        Assert.Equal(ArtifactFailureCode.ReconciliationExpired, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await driver.Store.StageAsync(expired, source, new(), default)).Code);
        Assert.Equal(0, source.BytesRead);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cleanup_cannot_reopen_a_finalized_noncommit(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("finalized abandonment"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        Success(await driver.Store.AbandonAsync(staged.Owner, new(), default));
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        clock.Advance(TimeSpan.FromSeconds(30));
        Success(await driver.Maintenance.CleanupAsync(new(driver.Identity,
            [new ArtifactCleanupTarget.AbandonedStaging(staged.Owner)]), new(), default));
        using var replacement = new ShortSource("must not be read"u8.ToArray());
        Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await driver.Store.StageAsync(ticket, replacement, new(), default));
        Assert.Equal(0, replacement.BytesRead);
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Expiry_cleanup_and_restage_fence_the_old_generation(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var first = new ShortSource("old generation"u8.ToArray());
        var old = Success(await driver.Store.StageAsync(ticket, first, new(), default));
        clock.Advance(TimeSpan.FromSeconds(30));
        Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactStagingOwner>.Failure>(
            await driver.Store.RenewAsync(old.Owner, new(), default)).Code);
        var cleanup = new ArtifactCleanupRequest(driver.Identity, [new ArtifactCleanupTarget.AbandonedStaging(old.Owner)]);
        Assert.Equal(1, Success(await driver.Maintenance.CleanupAsync(cleanup, new(), default)).Completed);
        using var second = new ShortSource("new generation"u8.ToArray());
        var current = Success(await driver.Store.StageAsync(ticket, second, new(), default));
        Assert.True(current.Owner.Generation > old.Owner.Generation);
        Assert.Equal(1, Success(await driver.Maintenance.CleanupAsync(cleanup, new(), default)).Conflicted);
        Assert.IsType<ArtifactResult<ArtifactStagingOwner>.Failure>(await driver.Store.RenewAsync(old.Owner, new(), default));
        Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(await driver.Store.AbandonAsync(old.Owner, new(), default));
        Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await driver.Store.CommitAsync(old, new(), default));
        var receipt = Success(await driver.Store.CommitAsync(current, new(), default));
        Assert.Equal("new generation"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Recovery_pages_are_bounded_query_bound_and_not_deletion_authority(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        for (var number = 0; number < 3; number++)
        {
            using var source = new ShortSource([(byte)number]);
            await PublishAsync(driver, source, new(1024));
        }
        var query = new ArtifactRecoveryQuery(driver.Identity, ArtifactRecoveryKind.Committed, 1);
        var first = Success(await driver.Maintenance.ObserveAsync(query, new(), default));
        Assert.Single(first.Observations);
        var continuation = Assert.IsType<ArtifactOption<string>.Some>(first.Continuation);
        var second = Success(await driver.Maintenance.ObserveAsync(new(driver.Identity,
            ArtifactRecoveryKind.Committed, 1, continuation), new(), default));
        Assert.Single(second.Observations);
        Assert.NotEqual(first.Observations[0].OperationId, second.Observations[0].OperationId);
        Assert.IsType<ArtifactResult<ArtifactRecoveryPage>.Failure>(await driver.Maintenance.ObserveAsync(
            new(driver.Identity, ArtifactRecoveryKind.All, 1, continuation), new(), default));
        var stamp = Assert.IsType<ArtifactOption<ArtifactStamp>.Some>(first.Observations[0].Stamp).Value;
        var unauthorizedCleanup = new ArtifactCleanupRequest(driver.Identity, [new ArtifactCleanupTarget.RemovedIncarnation(stamp)]);
        Assert.Equal(1, Success(await driver.Maintenance.CleanupAsync(unauthorizedCleanup, new(), default)).Conflicted);
        Assert.Single(await ReadAsync(driver, stamp));
    }
}
