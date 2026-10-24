using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Testing.Conformance.Artifacts;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactRecoveryTests
{
    [Fact]
    public async Task Stop_retains_unselected_object_ownership_and_retries_only_its_private_payload()
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync("object",
            limits: new(artifactBytes: 1024, stagingBytes: 1024));
        using var control = new ShortSource("selected control through stop"u8.ToArray());
        await PublishAsync(driver, control, new(1024));
        var objects = Path.Combine(Path.GetDirectoryName(driver.StagingDirectory)!, "objects");
        var selected = Assert.Single(Directory.GetFiles(objects));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("unselected assembly through stop"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        driver.ObjectControls!.SetObserver("pointer.compare", () =>
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix object proof required."); }
            File.SetUnixFileMode(objects, UnixFileMode.UserRead | UnixFileMode.UserExecute);
            return ValueTask.FromException(new IOException(ArtifactTestData.Canary));
        });
        try
        {
            Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await driver.Store.CommitAsync(staged, new(), default));
            for (var attempt = 0; attempt < 2; attempt++)
            {
                var stopped = Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                    await driver.StopAsync(new(TimeSpan.FromSeconds(1))));
                Assert.Equal(ArtifactFailureCode.CleanupIncomplete, stopped.Code);
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, stopped.Cleanup);
                Assert.Equal(2, Directory.GetFiles(objects).Length);
                Assert.False(source.WasDisposed);
            }
        }
        finally
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix object proof required."); }
            File.SetUnixFileMode(objects, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            driver.ObjectControls.RemoveObserver("pointer.compare");
        }
        Assert.Equal(ArtifactCleanupState.Released, Success(await driver.StopAsync(new())).State);
        Assert.Equal(selected, Assert.Single(Directory.GetFiles(objects)));
        Assert.Empty(Directory.GetFiles(driver.StagingDirectory));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Sequential_recovery_retires_consumed_cursors_without_starving_independent_scans(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        await ArtifactRecoveryAssertions.SequentialRecoveryAsync(
            driver.Store, driver.Maintenance, driver.Identity, clock.Advance,
            provider == "local" ? ArtifactEnumerationConsistency.Snapshot : ArtifactEnumerationConsistency.Incomplete,
            default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Admitted_reconciliation_preserves_the_settled_receipt_after_delete_and_recreate(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock,
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("settled receipt survives replacement"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        SetObserver(driver, "publish.decided", "pointer.selected",
            () => ValueTask.FromException(new IOException(ArtifactTestData.Canary)));
        Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.CommitAsync(staged, new(), default)).Code);
        if (driver.LocalControls is { } local) { local.RemoveObserver("publish.decided"); }
        else { driver.ObjectControls!.RemoveObserver("pointer.selected"); }
        await using var barrier = new ArtifactTestBarrier("settled-reconciliation-after-replacement");
        SetObserver(driver, "reconcile.before-resolution", "object.direct", () => new(barrier.HoldAsync()));
        var held = driver.Store.ReconcileAsync(ticket, new(), default).AsTask();
        ArtifactMutationReceipt settled;
        ArtifactMutationReceipt replacement;
        try
        {
            await barrier.Entered;
            if (driver.LocalControls is { } controls) { controls.RemoveObserver("reconcile.before-resolution"); }
            else { driver.ObjectControls!.RemoveObserver("object.direct"); }
            settled = Assert.IsType<ArtifactResolution.Committed>(
                Success(await driver.Store.ReconcileAsync(ticket, new(), default))).Receipt;
            var deletion = Success(await driver.Store.ReserveDeleteAsync(new(settled.Stamp), new(), default));
            Success(await driver.Store.DeleteAsync(deletion, new(), default));
            using var next = new ShortSource("settled receipt survives replacement"u8.ToArray());
            replacement = await PublishAsync(driver, next, new(1024));
            Assert.NotEqual(settled.Stamp, replacement.Stamp);
            clock.SetUtc(ticket.Expires.ToUnixTimeMilliseconds());
            Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        }
        finally { barrier.Release(); }
        Assert.Equal(settled, Assert.IsType<ArtifactResolution.Committed>(Success(await held)).Receipt);
        Assert.Equal("settled receipt survives replacement"u8.ToArray(), await ReadAsync(driver, replacement.Stamp));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Expired_reclaimed_history_remains_owned_until_the_admitted_delete_physically_settles(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock,
            new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, committedIdentities: 1),
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        using var source = new ShortSource("held deletion history"u8.ToArray());
        var original = await PublishAsync(driver, source, new(1024));
        var deletion = Success(await driver.Store.ReserveDeleteAsync(new(original.Stamp), new(), default));
        await using var barrier = new ArtifactTestBarrier("admitted-delete-retains-reclaimed-history");
        SetObserver(driver, "delete.removed", "pointer.tombstone", () => new(barrier.HoldAsync()));
        var held = driver.Store.DeleteAsync(deletion, new(), default).AsTask();
        try
        {
            await barrier.Entered;
            Success(await driver.Maintenance.CleanupAsync(new(driver.Identity,
                [new ArtifactCleanupTarget.RemovedIncarnation(original.Stamp)]), new(), default));
            clock.SetUtc(deletion.Expires.ToUnixTimeMilliseconds());
            var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
            using var next = new ShortSource("different digest awaiting settled history"u8.ToArray());
            var staged = Success(await driver.Store.StageAsync(ticket, next, new(), default));
            Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await driver.Store.CommitAsync(staged, new(), default)).Code);
        }
        finally { barrier.Release(); }
        Assert.Equal(ArtifactReclamation.Reclaimed, Success(await held).Reclamation);
        using var replacement = new ShortSource("different digest awaiting settled history"u8.ToArray());
        var current = await PublishAsync(driver, replacement, new(1024));
        Assert.Equal("different digest awaiting settled history"u8.ToArray(), await ReadAsync(driver, current.Stamp));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Expired_history_is_not_retired_beneath_an_admitted_reconciliation(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock,
            new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024, liveTickets: 1));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("retained reconciliation ownership"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        ValueTask LostAcknowledgment() => ValueTask.FromException(new IOException(ArtifactTestData.Canary));
        SetObserver(driver, "publish.decided", "pointer.selected", LostAcknowledgment);
        Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.CommitAsync(staged, new(), default)).Code);
        if (driver.LocalControls is { } local) { local.RemoveObserver("publish.decided"); }
        else { driver.ObjectControls!.RemoveObserver("pointer.selected"); }
        await using var barrier = new ArtifactTestBarrier("reconciliation-owns-expired-history");
        SetObserver(driver, "reconcile.before-resolution", "object.direct", () => new(barrier.HoldAsync()));
        var held = driver.Store.ReconcileAsync(ticket, new(), default).AsTask();
        ArtifactMutationReceipt settled;
        try
        {
            await barrier.Entered;
            if (driver.LocalControls is { } controls) { controls.RemoveObserver("reconcile.before-resolution"); }
            else { driver.ObjectControls!.RemoveObserver("object.direct"); }
            settled = Assert.IsType<ArtifactResolution.Committed>(
                Success(await driver.Store.ReconcileAsync(ticket, new(), default))).Receipt;
            clock.SetUtc(ticket.Expires.ToUnixTimeMilliseconds());
            Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Code);
        }
        finally { barrier.Release(); }
        Assert.Equal(settled, Assert.IsType<ArtifactResolution.Committed>(Success(await held)).Receipt);
        Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        Assert.Equal("retained reconciliation ownership"u8.ToArray(), await ReadAsync(driver, settled.Stamp));
    }

    [Fact]
    public async Task Local_reopen_preserves_committed_decisions_after_expired_ticket_retirement_and_clock_rollback()
    {
        using var root = new ArtifactTestRoot();
        var clock = new ArtifactTestClock();
        var identity = new ArtifactStoreIdentity("fixture.artifact.local", Guid.NewGuid(), Guid.NewGuid());
        var authority = new ArtifactCoordinationAuthority(identity, clock,
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        var limits = new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024, liveTickets: 1, committedIdentities: 1);
        var original = new LocalArtifactStore(root.Path, clock);
        Success(await original.InitializeAsync(new(ArtifactInitializationMode.CreateEmpty, identity, authority, limits), new(), default));
        ArtifactOperationTicket ticket;
        ArtifactMutationReceipt receipt;
        try
        {
            for (var index = 0; index < 105; index++)
            {
                var historical = Success(await original.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
                using var input = new ShortSource("repeated retired incarnation"u8.ToArray());
                var prepared = Success(await original.StageAsync(historical, input, new(), default));
                var incarnation = Success(await original.CommitAsync(prepared, new(), default));
                clock.SetUtc(historical.Expires.ToUnixTimeMilliseconds());
                var deletion = Success(await original.ReserveDeleteAsync(new(incarnation.Stamp), new(), default));
                Success(await original.DeleteAsync(deletion, new(), default));
                clock.SetUtc(deletion.Expires.ToUnixTimeMilliseconds());
            }
            ticket = Success(await original.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
            using var source = new ShortSource("persisted beyond ticket retention"u8.ToArray());
            var staged = Success(await original.StageAsync(ticket, source, new(), default));
            receipt = Success(await original.CommitAsync(staged, new(), default));
            clock.Advance(TimeSpan.FromHours(24));
            Success(await original.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        }
        finally { Success(await original.StopAsync(new(), default)); }
        clock.SetUtc(ticket.Issued.ToUnixTimeMilliseconds());
        var reopened = new LocalArtifactStore(root.Path, clock);
        try
        {
            Success(await reopened.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible, identity, authority, limits), new(), default));
            Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(await reopened.ReconcileAsync(ticket, new(), default));
            await using var read = Success(await reopened.OpenReadAsync(new(receipt.Stamp.Identity.Digest,
                expectedStamp: new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), default));
            using var destination = new MemoryStream();
            Success(await read.CopyToAsync(destination, new(), default));
            Assert.Equal("persisted beyond ticket retention"u8.ToArray(), destination.ToArray());
        }
        finally
        {
            var stopped = await reopened.StopAsync(new(), default);
            root.AllowCleanup = stopped is ArtifactResult<ArtifactShutdown>.Success;
            Assert.True(root.AllowCleanup);
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Late_cleanup_rechecks_the_exact_generation_after_replacement(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var first = new ShortSource("expired generation"u8.ToArray());
        var old = Success(await driver.Store.StageAsync(ticket, first, new(), default));
        clock.Advance(TimeSpan.FromSeconds(30));
        var request = new ArtifactCleanupRequest(driver.Identity, [new ArtifactCleanupTarget.AbandonedStaging(old.Owner)]);
        await using var barrier = new ArtifactTestBarrier("late-generation-cleanup");
        SetObserver(driver, "cleanup.candidate", "multipart.cleanup", () => new(barrier.HoldAsync()));
        var delayed = driver.Maintenance.CleanupAsync(request, new(), default).AsTask();
        ArtifactStagedWrite replacement;
        try
        {
            await barrier.Entered;
            if (driver.LocalControls is { } local) { local.RemoveObserver("cleanup.candidate"); }
            else { driver.ObjectControls!.RemoveObserver("multipart.cleanup"); }
            Assert.Equal(1, Success(await driver.Maintenance.CleanupAsync(request, new(), default)).Completed);
            using var second = new ShortSource("replacement generation"u8.ToArray());
            replacement = Success(await driver.Store.StageAsync(ticket, second, new(), default));
            Assert.True(replacement.Owner.Generation > old.Owner.Generation);
        }
        finally { barrier.Release(); }
        var result = Success(await delayed);
        Assert.Equal(1, result.Conflicted);
        Assert.Equal(0, result.ReclaimedBytes);
        var receipt = Success(await driver.Store.CommitAsync(replacement, new(), default));
        Assert.Equal("replacement generation"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Changed_inventory_rejects_old_continuations_and_fresh_pages_cover_every_current_identity(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactRecoveryAssertions.ChangedInventoryAsync(
            driver.Store, driver.Maintenance, driver.Identity, default);
    }

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
        await ArtifactRecoveryAssertions.OwnerlessExpiryAsync(driver.Store, clock.Advance, default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cleanup_cannot_reopen_a_finalized_noncommit(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        await ArtifactRecoveryAssertions.FinalizedNoncommitAsync(
            driver.Store, driver.Maintenance, driver.Identity, clock.Advance, default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Expiry_cleanup_and_restage_fence_the_old_generation(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        await ArtifactRecoveryAssertions.ExpiryGenerationAsync(
            driver.Store, driver.Maintenance, driver.Identity, clock.Advance, default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Recovery_pages_are_bounded_query_bound_and_not_deletion_authority(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactRecoveryAssertions.RecoveryPagesAsync(
            driver.Store, driver.Maintenance, driver.Identity, default);
    }
}
