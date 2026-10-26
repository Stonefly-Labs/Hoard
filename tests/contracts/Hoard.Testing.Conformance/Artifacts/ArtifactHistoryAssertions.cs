using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactHistoryAssertions
{
    public static async Task ReclaimedIncarnationBudgetAsync(
        IArtifactStore store, Action<long> setUtc, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("reclaimed incarnation budget"u8.ToArray());
        var old = await PublishAsync(store, source, new(1024), cancellationToken);
        var deletion = Success(await store.ReserveDeleteAsync(new(old.Stamp), new(), cancellationToken));
        Success(await store.DeleteAsync(deletion, new(), cancellationToken));
        using var replacement = new ShortSource("reclaimed incarnation budget"u8.ToArray());
        var current = await PublishAsync(store, replacement, new(1024), cancellationToken);
        Assert.NotEqual(old.Stamp, current.Stamp);
        var blocked = Success(await store.ReserveDeleteAsync(new(current.Stamp), new(), cancellationToken));
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.DeleteAsync(blocked, new(), cancellationToken)).Code);
        Assert.Equal("reclaimed incarnation budget"u8.ToArray(), await ReadAsync(store, current.Stamp, cancellationToken));
        setUtc(blocked.Expires.ToUnixTimeMilliseconds());
        var fresh = Success(await store.ReserveDeleteAsync(new(current.Stamp), new(), cancellationToken));
        Assert.Equal(ArtifactMutationOutcome.Removed,
            Success(await store.DeleteAsync(fresh, new(), cancellationToken)).Outcome);
    }

    public static async Task ReclaimedIdentityExpiryAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Action<long> setUtc, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("bounded retained identity history"u8.ToArray());
        var original = await PublishAsync(store, source, new(1024), cancellationToken);
        var deletion = Success(await store.ReserveDeleteAsync(new(original.Stamp), new(), cancellationToken));
        var removed = Success(await store.DeleteAsync(deletion, new(), cancellationToken));
        using var next = new ShortSource("new digest after retained history"u8.ToArray());
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, next, new(), cancellationToken));
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.CommitAsync(staged, new(), cancellationToken)).Code);
        Assert.Equal(removed, Success(await store.DeleteAsync(deletion, new(), cancellationToken)));
        setUtc(ticket.Expires.ToUnixTimeMilliseconds());
        using var replacement = new ShortSource("new digest after retained history"u8.ToArray());
        var current = await PublishAsync(store, replacement, new(1024), cancellationToken);
        Assert.Equal("new digest after retained history"u8.ToArray(), await ReadAsync(store, current.Stamp, cancellationToken));
        Success(await maintenance.CleanupAsync(new(identity,
            [new ArtifactCleanupTarget.RemovedIncarnation(original.Stamp)]), new(), cancellationToken));
        Assert.Equal("new digest after retained history"u8.ToArray(), await ReadAsync(store, current.Stamp, cancellationToken));
    }

    public static Task CandidateBoundsAsync(
        IArtifactStore store, string kind, Action<Action<string, string>> observeCandidate,
        CancellationToken cancellationToken) =>
        CandidateBoundsAsync(store, kind, observer =>
        {
            observeCandidate(observer);
            return ValueTask.CompletedTask;
        }, cancellationToken);

    public static async Task CandidateBoundsAsync(
        IArtifactStore store, string kind, Func<Action<string, string>, ValueTask> observeCandidate,
        CancellationToken cancellationToken)
    {
        for (var index = 0; index < 105; index++)
        {
            if (kind is "tickets" or "dependencies")
            { Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken)); }
            else
            {
                using var source = new ShortSource(BitConverter.GetBytes(index));
                var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
                if (kind == "reclamation")
                {
                    var deletion = Success(await store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
                    Success(await store.DeleteAsync(deletion, new(), cancellationToken));
                }
            }
        }
        var examined = 0;
        void Observe(string observed, string id)
        {
            if (observed == kind && Interlocked.Increment(ref examined) > 100)
            { throw new InvalidOperationException("History maintenance exceeded its candidate page."); }
        }
        await observeCandidate(Observe);
        Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken));
        Assert.InRange(examined, 0, 100);
    }

    public static Task CandidateResumeAsync(
        IArtifactStore store, Action<Action<string, string>> observeCandidate, CancellationToken cancellationToken)
    {
        var fail = true;
        return CandidateResumeAsync(store, observer =>
        {
            observeCandidate((kind, id) =>
            {
                observer(kind, id);
                if (kind == "tickets" && fail)
                { fail = false; throw new InvalidOperationException("Injected candidate failure."); }
            });
            return ValueTask.CompletedTask;
        }, () => ValueTask.CompletedTask, cancellationToken);
    }

    public static async Task CandidateResumeAsync(
        IArtifactStore store, Func<Action<string, string>, ValueTask> observeCandidate,
        Func<ValueTask> injectCandidateFailure, CancellationToken cancellationToken)
    {
        var original = new HashSet<string>();
        for (var index = 0; index < 105; index++)
        {
            var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken));
            original.Add(ticket.Id.ToString("N"));
        }
        var visited = new HashSet<string>();
        var examined = 0;
        void Observe(string kind, string id)
        {
            if (kind != "tickets") { return; }
            visited.Add(id);
            examined++;
        }
        await observeCandidate(Observe);
        await injectCandidateFailure();
        Assert.Equal(ArtifactFailureCode.InternalFailure, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken)).Code);
        visited.Clear();
        for (var page = 0; page < 2; page++)
        {
            examined = 0;
            Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), cancellationToken));
            Assert.InRange(examined, 1, 100);
        }
        Assert.True(original.IsSubsetOf(visited));
    }

    public static async Task TicketExpiryCapacityAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        Action<TimeSpan> advanceClock, Action<long> setUtc, bool reserveDelete, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("survives ticket retirement"u8.ToArray());
        var control = await PublishAsync(store, source, new(1024), cancellationToken);
        using var removedSource = new ShortSource("removed before ticket retirement"u8.ToArray());
        var old = await PublishAsync(store, removedSource, new(1024), cancellationToken);
        var deletion = Success(await store.ReserveDeleteAsync(new(old.Stamp), new(), cancellationToken));
        Success(await store.DeleteAsync(deletion, new(), cancellationToken));
        var reserved = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        advanceClock(TimeSpan.FromHours(24) - TimeSpan.FromMilliseconds(1));
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken)).Code);
        Assert.Equal(ArtifactFailureCode.Capacity, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
            await store.ReserveDeleteAsync(new(control.Stamp), new(), cancellationToken)).Code);
        advanceClock(TimeSpan.FromMilliseconds(1));
        var replacement = Success(reserveDelete
            ? await store.ReserveDeleteAsync(new(control.Stamp), new(), cancellationToken)
            : await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        Assert.Equal("survives ticket retirement"u8.ToArray(), await ReadAsync(store, control.Stamp, cancellationToken));
        var page = Success(await maintenance.ObserveAsync(
            new(identity, ArtifactRecoveryKind.Committed), new(), cancellationToken));
        Assert.Equal(control.Stamp, Assert.IsType<ArtifactOption<ArtifactStamp>.Some>(Assert.Single(page.Observations).Stamp).Value);
        Success(await maintenance.CleanupAsync(new(identity,
            [new ArtifactCleanupTarget.RemovedIncarnation(old.Stamp)]), new(), cancellationToken));
        foreach (var ticket in new[] { control.Ticket, old.Ticket, deletion, reserved })
        {
            Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
                await store.ReconcileAsync(ticket, new(), cancellationToken));
        }
        setUtc(control.Ticket.Issued.ToUnixTimeMilliseconds());
        using var replay = new ShortSource([1]);
        Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await store.StageAsync(reserved, replay, new(), cancellationToken));
        Assert.Equal(0, replay.BytesRead);
        if (reserveDelete)
        {
            Assert.Equal(ArtifactMutationOutcome.Removed,
                Success(await store.DeleteAsync(replacement, new(), cancellationToken)).Outcome);
        }
        else
        {
            using var duplicate = new ShortSource("survives ticket retirement"u8.ToArray());
            var staged = Success(await store.StageAsync(replacement, duplicate, new(), cancellationToken));
            Assert.Equal(control.Stamp, Success(await store.CommitAsync(staged, new(), cancellationToken)).Stamp);
        }
    }
}
