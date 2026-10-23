using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactBudgetTests
{
    [Fact]
    public async Task Local_reclaimed_incarnations_remain_budgeted_until_expiry_without_removing_the_recreated_blob()
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync("local", clock,
            new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, committedIdentities: 1),
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        using var source = new ShortSource("reclaimed incarnation budget"u8.ToArray());
        var old = await PublishAsync(driver, source, new(1024));
        var deletion = Success(await driver.Store.ReserveDeleteAsync(new(old.Stamp), new(), default));
        Success(await driver.Store.DeleteAsync(deletion, new(), default));
        using var replacement = new ShortSource("reclaimed incarnation budget"u8.ToArray());
        var current = await PublishAsync(driver, replacement, new(1024));
        Assert.NotEqual(old.Stamp, current.Stamp);
        var blocked = Success(await driver.Store.ReserveDeleteAsync(new(current.Stamp), new(), default));
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.DeleteAsync(blocked, new(), default)).Code);
        Assert.Equal("reclaimed incarnation budget"u8.ToArray(), await ReadAsync(driver, current.Stamp));
        clock.SetUtc(blocked.Expires.ToUnixTimeMilliseconds());
        var fresh = Success(await driver.Store.ReserveDeleteAsync(new(current.Stamp), new(), default));
        Assert.Equal(ArtifactMutationOutcome.Removed, Success(await driver.Store.DeleteAsync(fresh, new(), default)).Outcome);
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
        using var source = new ShortSource("bounded retained identity history"u8.ToArray());
        var original = await PublishAsync(driver, source, new(1024));
        var deletion = Success(await driver.Store.ReserveDeleteAsync(new(original.Stamp), new(), default));
        var removed = Success(await driver.Store.DeleteAsync(deletion, new(), default));
        using var next = new ShortSource("new digest after retained history"u8.ToArray());
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staged = Success(await driver.Store.StageAsync(ticket, next, new(), default));
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.CommitAsync(staged, new(), default)).Code);
        Assert.Equal(removed, Success(await driver.Store.DeleteAsync(deletion, new(), default)));
        clock.SetUtc(ticket.Expires.ToUnixTimeMilliseconds());
        using var replacement = new ShortSource("new digest after retained history"u8.ToArray());
        var current = await PublishAsync(driver, replacement, new(1024));
        Assert.Equal("new digest after retained history"u8.ToArray(), await ReadAsync(driver, current.Stamp));
        Success(await driver.Maintenance.CleanupAsync(new(driver.Identity,
            [new ArtifactCleanupTarget.RemovedIncarnation(original.Stamp)]), new(), default));
        Assert.Equal("new digest after retained history"u8.ToArray(), await ReadAsync(driver, current.Stamp));
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
        for (var index = 0; index < 105; index++)
        {
            if (kind is "tickets" or "dependencies")
            { Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default)); }
            else
            {
                using var source = new ShortSource(BitConverter.GetBytes(index));
                var receipt = await PublishAsync(driver, source, new(1024));
                if (kind == "reclamation")
                {
                    var deletion = Success(await driver.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default));
                    Success(await driver.Store.DeleteAsync(deletion, new(), default));
                }
            }
        }
        var examined = 0;
        void Observe(string observed, string id)
        {
            if (observed == kind && Interlocked.Increment(ref examined) > 100)
            { throw new InvalidOperationException("History maintenance exceeded its candidate page."); }
        }
        if (driver.LocalControls is { } local) { local.BeforeHistoryCandidate = Observe; }
        else { driver.ObjectControls!.BeforeHistoryCandidate = Observe; }
        Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default));
        Assert.InRange(examined, 0, 100);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task History_candidate_pages_resume_past_ineligible_entries_and_preserve_a_faulted_candidate(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var original = new HashSet<string>();
        for (var index = 0; index < 105; index++)
        {
            var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default));
            original.Add(ticket.Id.ToString("N"));
        }
        var visited = new HashSet<string>();
        var examined = 0;
        var fail = true;
        void Observe(string kind, string id)
        {
            if (kind != "tickets") { return; }
            visited.Add(id);
            examined++;
            if (fail) { fail = false; throw new InvalidOperationException("Injected candidate failure."); }
        }
        if (driver.LocalControls is { } local) { local.BeforeHistoryCandidate = Observe; }
        else { driver.ObjectControls!.BeforeHistoryCandidate = Observe; }
        Assert.Equal(ArtifactFailureCode.InternalFailure, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default)).Code);
        visited.Clear();
        for (var page = 0; page < 2; page++)
        {
            examined = 0;
            Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default));
            Assert.InRange(examined, 1, 100);
        }
        Assert.True(original.IsSubsetOf(visited));
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
        using var source = new ShortSource("survives ticket retirement"u8.ToArray());
        var control = await PublishAsync(driver, source, new(1024));
        using var removedSource = new ShortSource("removed before ticket retirement"u8.ToArray());
        var old = await PublishAsync(driver, removedSource, new(1024));
        var deletion = Success(await driver.Store.ReserveDeleteAsync(new(old.Stamp), new(), default));
        Success(await driver.Store.DeleteAsync(deletion, new(), default));
        var reserved = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        clock.Advance(TimeSpan.FromHours(24) - TimeSpan.FromMilliseconds(1));
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Code);
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await driver.Store.ReserveDeleteAsync(new(control.Stamp), new(), default)).Code);
        clock.Advance(TimeSpan.FromMilliseconds(1));
        var replacement = Success(reserveDelete
            ? await driver.Store.ReserveDeleteAsync(new(control.Stamp), new(), default)
            : await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        Assert.Equal("survives ticket retirement"u8.ToArray(), await ReadAsync(driver, control.Stamp));
        var page = Success(await driver.Maintenance.ObserveAsync(
            new(driver.Identity, ArtifactRecoveryKind.Committed), new(), default));
        Assert.Equal(control.Stamp, Assert.IsType<ArtifactOption<ArtifactStamp>.Some>(Assert.Single(page.Observations).Stamp).Value);
        Success(await driver.Maintenance.CleanupAsync(new(driver.Identity,
            [new ArtifactCleanupTarget.RemovedIncarnation(old.Stamp)]), new(), default));
        foreach (var ticket in new[] { control.Ticket, old.Ticket, deletion, reserved })
        {
            Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
                await driver.Store.ReconcileAsync(ticket, new(), default));
        }
        clock.SetUtc(control.Ticket.Issued.ToUnixTimeMilliseconds());
        using var replay = new ShortSource([1]);
        Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await driver.Store.StageAsync(reserved, replay, new(), default));
        Assert.Equal(0, replay.BytesRead);
        if (reserveDelete)
        {
            Assert.Equal(ArtifactMutationOutcome.Removed,
                Success(await driver.Store.DeleteAsync(replacement, new(), default)).Outcome);
        }
        else
        {
            using var duplicate = new ShortSource("survives ticket retirement"u8.ToArray());
            var staged = Success(await driver.Store.StageAsync(replacement, duplicate, new(), default));
            Assert.Equal(control.Stamp, Success(await driver.Store.CommitAsync(staged, new(), default)).Stamp);
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Producer_and_consumer_inactivity_deadlines_release_cooperative_work_without_closing_borrowed_streams(
        string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var stalled = new PendingSource(cooperative: true);
        Assert.Equal(ArtifactFailureCode.DeadlineExceeded, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await driver.Store.StageAsync(ticket, stalled,
                new(TimeSpan.FromSeconds(2), TimeSpan.FromMilliseconds(20)), default)
                .AsTask().WaitAsync(TimeSpan.FromSeconds(3))).Code);
        await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.False(stalled.WasDisposed);
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        using var source = new ShortSource("cooperative inactivity recovery"u8.ToArray());
        var receipt = await PublishAsync(driver, source, new(1024));
        await using (var read = Success(await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)))
        {
            using var destination = new StalledDestination();
            Assert.Equal(ArtifactFailureCode.DeadlineExceeded, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await read.CopyToAsync(destination, new(TimeSpan.FromSeconds(2), TimeSpan.FromMilliseconds(20)), default)
                    .AsTask().WaitAsync(TimeSpan.FromSeconds(3))).Code);
            Assert.True(destination.CanWrite);
            Success(await read.CloseAsync(new(), default));
        }
        Assert.Equal("cooperative inactivity recovery"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
    }

    private sealed class StalledDestination : MemoryStream
    {
        public override ValueTask WriteAsync(ReadOnlyMemory<byte> buffer, CancellationToken cancellationToken = default)
            => new(Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cancellation_of_an_admitted_commit_cannot_fence_an_externally_renewed_owner(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("renewed owner survives older cancellation"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        await using var barrier = new ArtifactTestBarrier("renew-before-cancellation-settlement");
        SetObserver(driver, "publish.before-decision", "pointer.compare", () => new(barrier.HoldAsync()));
        using var cancellation = new CancellationTokenSource();
        var committing = driver.Store.CommitAsync(staged, new(), cancellation.Token).AsTask();
        ArtifactStagingOwner renewed;
        try
        {
            await barrier.Entered;
            clock.Advance(TimeSpan.FromSeconds(10));
            renewed = Success(await driver.Store.RenewAsync(staged.Owner, new(), default));
            cancellation.Cancel();
            Assert.Equal(ArtifactFailureCode.CancelledBeforeCommit,
                Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                    await committing.WaitAsync(TimeSpan.FromSeconds(2))).Code);
        }
        finally
        {
            if (driver.LocalControls is { } local) { local.RemoveObserver("publish.before-decision"); }
            else { driver.ObjectControls!.RemoveObserver("pointer.compare"); }
            barrier.Release();
        }
        await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.IsType<ArtifactResolution.Pending>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        var current = new ArtifactStagedWrite(renewed, staged.Identity, staged.VerifiedCompletion, staged.PrivateHandle);
        var receipt = Success(await driver.Store.CommitAsync(current, new(), default));
        Assert.Equal("renewed owner survives older cancellation"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cancellation_after_progress_renewal_fences_the_same_admitted_owner(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
        var bytes = new byte[1048576];
        using var initial = new MemoryStream(bytes, writable: false);
        var original = await PublishAsync(driver, initial, new(2097152));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(2097152)), new(), default));
        using var duplicate = new MemoryStream(bytes, writable: false);
        var staged = Success(await driver.Store.StageAsync(ticket, duplicate, new(), default));
        using var cancellation = new CancellationTokenSource();
        var progress = 0;
        ValueTask Advance()
        {
            clock.Advance(TimeSpan.FromSeconds(11));
            if (Interlocked.Increment(ref progress) == 2) { cancellation.Cancel(); }
            return ValueTask.CompletedTask;
        }
        SetObserver(driver, "publish.progress", "object.commit-progress", Advance);
        Assert.Equal(ArtifactFailureCode.CancelledBeforeCommit,
            Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await driver.Store.CommitAsync(staged, new(), cancellation.Token)).Code);
        await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Equal(2, progress);
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        Assert.Equal(bytes, await ReadAsync(driver, original.Stamp));
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
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("preserve current verified ownership"u8.ToArray());
        var original = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        var current = original;
        ArtifactStagedWrite invalid;
        if (alteration == "renewed")
        {
            clock.Advance(TimeSpan.FromSeconds(10));
            var renewed = Success(await driver.Store.RenewAsync(original.Owner, new(), default));
            current = new(renewed, original.Identity, original.VerifiedCompletion, original.PrivateHandle);
            invalid = original;
        }
        else
        {
            invalid = new(original.Owner, original.Identity,
                alteration == "completion" ? Guid.NewGuid() : original.VerifiedCompletion,
                alteration == "handle" ? original.PrivateHandle + "-forged" : original.PrivateHandle);
        }
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.CommitAsync(invalid, new(), cancellation.Token));
        await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.IsType<ArtifactResolution.Pending>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        var receipt = Success(await driver.Store.CommitAsync(current, new(), default));
        Assert.Equal(ArtifactMutationOutcome.Published, receipt.Outcome);
        Assert.Equal("preserve current verified ownership"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cancellation_after_resource_release_cannot_retain_an_already_settled_operation(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("released cancellation bookkeeping"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        var invalid = new ArtifactStagedWrite(staged.Owner, staged.Identity, Guid.NewGuid(), staged.PrivateHandle);
        using var cancellation = new CancellationTokenSource();
        await using var released = new ArtifactTestBarrier("resources-released-task-not-completed");
        async ValueTask Observe()
        {
            cancellation.Cancel();
            await released.HoldAsync();
        }
        SetObserver(driver, "operation.released", "object.operation-released", Observe);
        try
        {
            var attempt = driver.Store.CommitAsync(invalid, new(), cancellation.Token).AsTask();
            await released.Entered;
            driver.LocalControls?.RemoveObserver("operation.released");
            driver.ObjectControls?.RemoveObserver("object.operation-released");
            var result = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await attempt);
            Assert.Equal(ArtifactCleanupState.Released, result.Cleanup);
            Assert.IsType<ArtifactResolution.Pending>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        }
        finally { released.Release(); }
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
        using var source = new ShortSource("successful result ownership handoff"u8.ToArray());
        var published = readSession ? await PublishAsync(driver, source, new(1024)) : null;
        using var cancellation = new CancellationTokenSource();
        await using var released = new ArtifactTestBarrier("successful-result-before-task-completion");
        async ValueTask Observe()
        {
            cancellation.Cancel();
            await released.HoldAsync();
        }
        SetObserver(driver, "operation.released", "object.operation-released", Observe);
        try
        {
            if (published is null)
            {
                var reserving = driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellation.Token).AsTask();
                await released.Entered;
                RemoveObserver();
                var ticket = Success(await reserving);
                var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
                Success(await driver.Store.CommitAsync(staged, new(), default));
                Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
            }
            else
            {
                var opening = driver.Store.OpenReadAsync(new(published.Stamp.Identity.Digest), new(), cancellation.Token).AsTask();
                await released.Entered;
                RemoveObserver();
                await using var read = Success(await opening);
                using var destination = new MemoryStream();
                Success(await read.CopyToAsync(destination, new(), default));
                Assert.Equal("successful result ownership handoff"u8.ToArray(), destination.ToArray());
                Assert.Equal(ArtifactCleanupState.Released, Success(await read.CloseAsync(new(), default)).State);
                var deletion = Success(await driver.Store.ReserveDeleteAsync(new(published.Stamp), new(), default));
                Success(await driver.Store.DeleteAsync(deletion, new(), default));
            }
        }
        finally { RemoveObserver(); released.Release(); }

        void RemoveObserver()
        {
            driver.LocalControls?.RemoveObserver("operation.released");
            driver.ObjectControls?.RemoveObserver("object.operation-released");
        }
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
        using var source = new ShortSource("unclaimed result cleanup"u8.ToArray());
        var published = readSession ? await PublishAsync(driver, source, new(1024)) : null;
        using var cancellation = new CancellationTokenSource();
        await using var produced = new ArtifactTestBarrier("successful-result-not-yet-handed-off");
        SetObserver(driver, "operation.completed", "object.operation-completed", () => new(produced.HoldAsync()));
        try
        {
            if (published is null)
            {
                var reserving = driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellation.Token).AsTask();
                await produced.Entered;
                cancellation.Cancel();
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership,
                    Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(await reserving).Cleanup);
            }
            else
            {
                var opening = driver.Store.OpenReadAsync(new(published.Stamp.Identity.Digest), new(), cancellation.Token).AsTask();
                await produced.Entered;
                cancellation.Cancel();
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership,
                    Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(await opening).Cleanup);
            }
        }
        finally
        {
            driver.LocalControls?.RemoveObserver("operation.completed");
            driver.ObjectControls?.RemoveObserver("object.operation-completed");
            produced.Release();
        }
        await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        if (published is null)
        {
            Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        }
        else
        {
            var deletion = Success(await driver.Store.ReserveDeleteAsync(new(published.Stamp), new(), default));
            Success(await driver.Store.DeleteAsync(deletion, new(), default));
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Undelivered_verified_staging_is_reclaimed_after_ownership_expiry(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock,
            new(artifactBytes: 1024, stagingBytes: 1024));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("expired unclaimed staging"u8.ToArray());
        using var cancellation = new CancellationTokenSource();
        await using var produced = new ArtifactTestBarrier("verified-owner-expired-before-delivery");
        SetObserver(driver, "operation.completed", "object.operation-completed", () => new(produced.HoldAsync()));
        try
        {
            var staging = driver.Store.StageAsync(ticket, source, new(), cancellation.Token).AsTask();
            await produced.Entered;
            clock.Advance(TimeSpan.FromSeconds(31));
            cancellation.Cancel();
            Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await staging);
        }
        finally
        {
            driver.LocalControls?.RemoveObserver("operation.completed");
            driver.ObjectControls?.RemoveObserver("object.operation-completed");
            produced.Release();
        }
        await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
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
        using var source = new ShortSource("failed unclaimed cleanup"u8.ToArray());
        var published = readSession ? await PublishAsync(driver, source, new(1024)) : null;
        using var cancellation = new CancellationTokenSource();
        await using var produced = new ArtifactTestBarrier("unclaimed-cleanup-failure");
        SetObserver(driver, "operation.completed", "object.operation-completed", () => new(produced.HoldAsync()));
        SetObserver(driver, "operation.reclaim", "object.operation-reclaim",
            () => throw new IOException("synthetic unclaimed cleanup failure"));
        try
        {
            try
            {
                if (published is null)
                {
                    var reserving = driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellation.Token).AsTask();
                    await produced.Entered;
                    cancellation.Cancel();
                    Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(await reserving);
                }
                else
                {
                    var opening = driver.Store.OpenReadAsync(new(published.Stamp.Identity.Digest), new(), cancellation.Token).AsTask();
                    await produced.Entered;
                    cancellation.Cancel();
                    Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(await opening);
                }
            }
            finally
            {
                driver.LocalControls?.RemoveObserver("operation.completed");
                driver.ObjectControls?.RemoveObserver("object.operation-completed");
                produced.Release();
            }
            await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Code);
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                await driver.StopAsync(new())).Code);
        }
        finally
        {
            driver.LocalControls?.RemoveObserver("operation.reclaim");
            driver.ObjectControls?.RemoveObserver("object.operation-reclaim");
            Assert.Equal(ArtifactCleanupState.Released, Success(await driver.StopAsync(new())).State);
        }
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
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("cancelled publication is terminal"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        var stamp = new ArtifactStamp(driver.Identity, staged.Identity, Guid.NewGuid());
        var exclusion = Success(await driver.Authority.AcquireAsync(new(Guid.NewGuid(),
            ArtifactProtectionOperation.Deletion, driver.Identity, staged.Identity.Digest,
            new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), default));
        using var cancellation = new CancellationTokenSource();
        if (alreadyCancelled) { cancellation.Cancel(); }
        try
        {
            var failure = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await driver.Store.CommitAsync(staged, new(TimeSpan.FromMilliseconds(30)), cancellation.Token));
            Assert.Equal(alreadyCancelled ? ArtifactFailureCode.CancelledBeforeCommit : ArtifactFailureCode.DeadlineExceeded,
                failure.Code);
        }
        finally { await exclusion.DisposeAsync(); }
        await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.IsType<ArtifactResolution.NotCommitted>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await driver.Store.CommitAsync(staged, new(), default));
        var read = await Task.Factory.StartNew(() => driver.Store.OpenReadAsync(
            new(staged.Identity.Digest), new(), default).AsTask(), CancellationToken.None,
            TaskCreationOptions.LongRunning, TaskScheduler.Default).Unwrap();
        Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            read).Code);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Full_transfer_queue_rejects_without_input_io_and_capacity_returns_after_release(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new ArtifactLimits(artifactBytes: 1, stagingBytes: 3, transferSlots: 1, waitingCalls: 1));
        var tickets = new List<ArtifactOperationTicket>();
        for (var index = 0; index < 3; index++)
        { tickets.Add(Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default))); }
        var queued = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        ValueTask ObserveQueue() { queued.TrySetResult(); return ValueTask.CompletedTask; }
        if (driver.LocalControls is { } local) { local.SetObserver("transfer.queued", ObserveQueue); }
        else { driver.ObjectControls!.SetObserver("object.transfer-queued", ObserveQueue); }
        using var first = new PendingSource(cooperative: true);
        var active = driver.Store.StageAsync(tickets[0], first, new(), default).AsTask();
        await first.Entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
        using var second = new ShortSource([1]);
        var waiting = driver.Store.StageAsync(tickets[1], second, new(), default).AsTask();
        try
        {
            await queued.Task.WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(0, second.BytesRead);
            using var rejected = new ShortSource([1]);
            Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await driver.Store.StageAsync(tickets[2], rejected, new(), default)).Code);
            Assert.Equal(0, rejected.BytesRead);
        }
        finally { first.Released.TrySetResult(0); }
        var completed = Success(await active);
        var unblocked = Success(await waiting);
        Success(await driver.Store.AbandonAsync(completed.Owner, new(), default));
        Success(await driver.Store.AbandonAsync(unblocked.Owner, new(), default));
        using var restored = new ShortSource([1]);
        Success(await driver.Store.StageAsync(tickets[2], restored, new(), default));
        Assert.Equal(1, restored.BytesRead);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cap_crossing_rejects_excess_before_append_and_capacity_recovers(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new ArtifactLimits(10, 10, 1));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(10)), new(), default));
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default)).Code);
        using var source = new ShortSource("actual input is too large"u8.ToArray());
        Assert.Equal(ArtifactFailureCode.LimitExceeded, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await driver.Store.StageAsync(ticket, source, new(), default)).Code);
        Assert.False(source.WasDisposed);
        Assert.NotNull(Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(10)), new(), default)));
        Assert.Equal(ArtifactFailureCode.LimitExceeded, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(11)), new(), default)).Code);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Total_deadline_includes_shared_authority_contention_before_publication(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, references: (_, _) =>
            ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        using var source = new ShortSource("guard queue budget"u8.ToArray());
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        var stamp = new ArtifactStamp(driver.Identity, staged.Identity, Guid.NewGuid());
        await using var exclusion = Success(await driver.Authority.AcquireAsync(new(Guid.NewGuid(),
            ArtifactProtectionOperation.Deletion, driver.Identity, staged.Identity.Digest,
            new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), default));
        var result = await driver.Store.CommitAsync(staged,
            new ArtifactTransferOptions(TimeSpan.FromMilliseconds(30)), default).AsTask().WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Equal(ArtifactFailureCode.DeadlineExceeded, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(result).Code);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Cooperative_cancellation_stops_input_without_disposing_borrowed_stream(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        using var source = new PendingSource(cooperative: true);
        using var cancelled = new CancellationTokenSource();
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staging = driver.Store.StageAsync(ticket, source, new(), cancelled.Token).AsTask();
        await source.Entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
        cancelled.Cancel();
        var result = await staging.WaitAsync(TimeSpan.FromSeconds(2));
        Assert.Equal(ArtifactFailureCode.CancelledBeforeCommit, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(result).Code);
        Assert.False(source.WasDisposed);
    }

    internal sealed class PendingSource(bool cooperative) : Stream
    {
        public TaskCompletionSource Entered { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource<int> Released { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public bool WasDisposed { get; private set; }
        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException();
        public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            Entered.TrySetResult();
            return new(cooperative ? Released.Task.WaitAsync(cancellationToken) : Released.Task);
        }
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
        public override void Flush() => throw new NotSupportedException();
        public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    }
}
