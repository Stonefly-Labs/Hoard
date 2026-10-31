using System.Security.Cryptography;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;

namespace Hoard.Testing.Conformance.Artifacts;

public enum ArtifactCrashPoint { StagePrefix, StageVerified, PublicationSelected, DeleteRemoved, DeleteReclaimed }

public sealed record ArtifactCrashStamp(string Digest, long Length, Guid Incarnation)
{
    public static ArtifactCrashStamp From(ArtifactStamp stamp) => new(stamp.Identity.Digest.Hex, stamp.Identity.Length, stamp.Incarnation);
    public ArtifactStamp In(ArtifactStoreIdentity store) => new(store, new ArtifactIdentity(new ArtifactDigest(Digest), Length), Incarnation);
}

public sealed record ArtifactCrashStage(ArtifactStagingOwner Owner, string Digest, long Length, Guid Verification, string Handle)
{
    public static ArtifactCrashStage From(ArtifactStagedWrite staged) => new(staged.Owner, staged.Identity.Digest.Hex,
        staged.Identity.Length, staged.VerifiedCompletion, staged.PrivateHandle);
    public ArtifactStagedWrite ToStaged() => new(Owner, new ArtifactIdentity(new ArtifactDigest(Digest), Length), Verification, Handle);
    public override string ToString() => nameof(ArtifactCrashStage);
}

public sealed record ArtifactCrashState(Guid Run, string Barrier, ArtifactStoreIdentity Store,
    ArtifactOperationTicket ControlTicket, Guid ControlReceipt, ArtifactCrashStamp Control,
    ArtifactOperationTicket Ticket, string TargetDigest, long TargetLength,
    ArtifactCrashStamp? Target = null, Guid? AcknowledgedReceipt = null, ArtifactCrashStage? Stage = null,
    ArtifactStagingOwner? PriorOwner = null)
{
    public override string ToString() => nameof(ArtifactCrashState);
}

public sealed record ArtifactCrashReadback(
    bool OwnerFenced, bool Reconstructed, string Reclamation, string ContentSha256, long ContentLength,
    string ControlSha256, long ControlLength, ArtifactMutationReceipt Outcome);

public static class ArtifactCrashAssertions
{
    private static readonly byte[] ControlBytes = "acknowledged independent control before crash"u8.ToArray();
    private static readonly byte[] TargetBytes = Enumerable.Range(0, 1048576).Select(index => (byte)(index * 17 + 11)).ToArray();

    public static async Task CrashAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactStoreIdentity identity,
        string barrier, Guid run, Func<ArtifactCrashState, ValueTask> pause,
        Func<ArtifactCrashPoint, Func<ValueTask>, ValueTask<IAsyncDisposable>> observe,
        CancellationToken cancellationToken = default)
    {
        ValidateBoundary(barrier);
        ArgumentNullException.ThrowIfNull(pause);
        ArgumentNullException.ThrowIfNull(observe);
        cancellationToken.ThrowIfCancellationRequested();
        var control = await PublishAsync(store, ControlBytes, cancellationToken);
        var ticket = Need(await store.ReserveWriteAsync(new(new ArtifactExpectations(TargetBytes.Length)), new(), cancellationToken));
        var digest = Convert.ToHexStringLower(SHA256.HashData(TargetBytes));
        var state = new ArtifactCrashState(run, barrier, identity, control.Ticket, control.ReceiptId,
            ArtifactCrashStamp.From(control.Stamp), ticket, digest, TargetBytes.LongLength);

        async ValueTask PauseAsync()
        {
            if (barrier is "B0" or "B1")
            {
                var page = Need(await maintenance.ObserveAsync(new(identity, ArtifactRecoveryKind.Staging), new(), cancellationToken));
                var owner = page.Observations.Single(row => row.OperationId == ticket.Id).Owner;
                state = state with { PriorOwner = ((ArtifactOption<ArtifactStagingOwner>.Some)owner).Value };
            }
            else if (barrier == "B2")
            {
                var page = Need(await maintenance.ObserveAsync(new(identity, ArtifactRecoveryKind.Committed), new(), cancellationToken));
                var stamp = page.Observations.Single(row => row.OperationId == ticket.Id).Stamp;
                state = state with { Target = ArtifactCrashStamp.From(((ArtifactOption<ArtifactStamp>.Some)stamp).Value) };
            }
            await pause(state);
        }

        var point = barrier switch
        {
            "B0" => ArtifactCrashPoint.StagePrefix,
            "B1" => ArtifactCrashPoint.StageVerified,
            "B2" => ArtifactCrashPoint.PublicationSelected,
            "D0" => ArtifactCrashPoint.DeleteRemoved,
            "D1" => ArtifactCrashPoint.DeleteReclaimed,
            _ => (ArtifactCrashPoint?)null
        };
        await using var registration = point is null ? null : await observe(point.Value, PauseAsync);
        using var source = new MemoryStream(TargetBytes, writable: false);
        var staged = Need(await store.StageAsync(ticket, source, new(), cancellationToken));
        state = state with { Stage = ArtifactCrashStage.From(staged) };
        var publication = Need(await store.CommitAsync(staged, new(), cancellationToken));
        state = state with { Target = ArtifactCrashStamp.From(publication.Stamp), AcknowledgedReceipt = publication.ReceiptId };
        if (barrier == "B3") { await PauseAsync(); }
        else
        {
            var deletion = Need(await store.ReserveDeleteAsync(new(publication.Stamp), new(), cancellationToken));
            state = state with { Ticket = deletion, AcknowledgedReceipt = null };
            Need(await store.DeleteAsync(deletion, new(), cancellationToken));
        }
        throw new InvalidOperationException("Artifact crash child passed its required parent-kill boundary.");
    }

    public static async Task<ArtifactCrashReadback> RecoverAsync(
        IArtifactStore store, IArtifactMaintenance maintenance, ArtifactCrashState state, string barrier, Guid run,
        CancellationToken cancellationToken = default)
    {
        ValidateBoundary(barrier);
        cancellationToken.ThrowIfCancellationRequested();
        Require(state.Run == run && state.Barrier == barrier, "Artifact crash state belongs to another run.");
        var control = (ArtifactResolution.Committed)Need(await store.ReconcileAsync(state.ControlTicket, new(), cancellationToken));
        Require(control.Receipt.ReceiptId == state.ControlReceipt
            && control.Receipt.Stamp == state.Control.In(state.Store), "Acknowledged control receipt changed.");
        await VerifyReadAsync(store, control.Receipt.Stamp, ControlBytes, cancellationToken);
        var ownerFenced = false;
        var reconstructed = false;
        var reclamation = "NotApplicable";
        ArtifactMutationReceipt outcome;
        if (barrier is "B0" or "B1")
        {
            Require(Need(await store.ReconcileAsync(state.Ticket, new(), cancellationToken)) is ArtifactResolution.Pending,
                "A stage without decision intent must remain resumable.");
            var absent = await store.OpenReadAsync(new(new ArtifactDigest(state.TargetDigest)), new(), cancellationToken);
            Require(absent is ArtifactResult<IArtifactReadSession>.Failure { Code: ArtifactFailureCode.NotFound },
                "An incomplete stage became committed content.");
            var old = state.PriorOwner ?? throw new InvalidOperationException("Prior crash owner is missing.");
            Require(await store.RenewAsync(old, new(), cancellationToken) is ArtifactResult<ArtifactStagingOwner>.Failure,
                "Prior process ownership was renewed.");
            Require(await store.AbandonAsync(old, new(), cancellationToken) is ArtifactResult<ArtifactCleanupReport>.Failure,
                "Prior process ownership was allowed to abandon.");
            using var fresh = new MemoryStream(TargetBytes, writable: false);
            var staged = Need(await store.StageAsync(state.Ticket, fresh, new(), cancellationToken));
            Require(staged.Owner.Generation > old.Generation && staged.Owner.SessionId != old.SessionId,
                "Restart reused a staging generation.");
            var oldStaged = new ArtifactStagedWrite(old, staged.Identity, Guid.NewGuid(), old.OwnerId.ToString("N"));
            Require(await store.CommitAsync(oldStaged, new(), cancellationToken) is ArtifactResult<ArtifactMutationReceipt>.Failure,
                "An old generation was allowed to commit.");
            var cleanup = Need(await maintenance.CleanupAsync(new(state.Store,
                [new ArtifactCleanupTarget.AbandonedStaging(old)]), new(), cancellationToken));
            Require(cleanup.Conflicted == 1 && cleanup.ReclaimedBytes == 0, "Stale cleanup reclaimed new staging.");
            outcome = Need(await store.CommitAsync(staged, new(), cancellationToken));
            ownerFenced = true;
            reconstructed = true;
        }
        else if (barrier is "B2" or "B3")
        {
            var resolved = (ArtifactResolution.Committed)Need(await store.ReconcileAsync(state.Ticket, new(), cancellationToken));
            outcome = resolved.Receipt;
            Require(outcome.Stamp == state.Target!.In(state.Store), "Recovery selected another incarnation.");
            if (state.AcknowledgedReceipt is { } acknowledged)
            { Require(outcome.ReceiptId == acknowledged, "Acknowledged publication receipt changed."); }
            Require(Need(await store.CommitAsync(state.Stage!.ToStaged(), new(), cancellationToken)) == outcome,
                "Exact publication retry produced another receipt.");
        }
        else
        {
            outcome = ((ArtifactResolution.Removed)Need(await store.ReconcileAsync(state.Ticket, new(), cancellationToken))).Receipt;
            reclamation = outcome.Reclamation.ToString();
            Require(outcome.Stamp == state.Target!.In(state.Store), "Recovery removed another incarnation.");
            Require(outcome.Reclamation == (barrier == "D0" ? ArtifactReclamation.Pending : ArtifactReclamation.Reclaimed),
                "Durable reclamation progress was not reconciled.");
            var absent = await store.OpenReadAsync(new(outcome.Stamp.Identity.Digest), new(), cancellationToken);
            Require(absent is ArtifactResult<IArtifactReadSession>.Failure { Code: ArtifactFailureCode.NotFound },
                "Logical deletion was forgotten.");
            Require(Need(await store.DeleteAsync(state.Ticket, new(), cancellationToken)).ReceiptId == outcome.ReceiptId,
                "Exact deletion retry produced another receipt.");
            var recreated = await PublishAsync(store, TargetBytes, cancellationToken);
            Require(recreated.Stamp.Incarnation != outcome.Stamp.Incarnation, "Recreation reused the old incarnation.");
            Need(await maintenance.CleanupAsync(new(state.Store,
                [new ArtifactCleanupTarget.RemovedIncarnation(outcome.Stamp)]), new(), cancellationToken));
            Need(await store.DeleteAsync(state.Ticket, new(), cancellationToken));
            await VerifyReadAsync(store, recreated.Stamp, TargetBytes, cancellationToken);
            ownerFenced = true;
        }
        if (outcome.Visibility == ArtifactVisibility.Committed)
        { await VerifyReadAsync(store, outcome.Stamp, TargetBytes, cancellationToken); }
        var repeated = Need(await store.ReconcileAsync(state.Ticket, new(), cancellationToken));
        if (state.Stage is { } previous)
        {
            Require(await store.RenewAsync(previous.Owner, new(), cancellationToken) is ArtifactResult<ArtifactStagingOwner>.Failure,
                "A prior staging owner was revived after restart.");
            Require(await store.AbandonAsync(previous.Owner, new(), cancellationToken) is ArtifactResult<ArtifactCleanupReport>.Failure,
                "A prior staging owner was allowed to abandon after restart.");
            ownerFenced = true;
        }
        var inventory = Need(await maintenance.ObserveAsync(new(state.Store, ArtifactRecoveryKind.Committed), new(), cancellationToken));
        Require(inventory.Observations.Count(row => row.Stamp is ArtifactOption<ArtifactStamp>.Some stamp
            && stamp.Value.Identity.Digest.Hex == state.TargetDigest) == 1, "Recovery produced duplicate logical publication.");
        var repeatedReceipt = repeated switch
        {
            ArtifactResolution.Committed committed => committed.Receipt,
            ArtifactResolution.Removed removed => removed.Receipt,
            _ => throw new InvalidOperationException("Recovered ticket lost its decided outcome.")
        };
        Require(outcome.ReceiptId == repeatedReceipt.ReceiptId && outcome.Stamp == repeatedReceipt.Stamp
            && outcome.Outcome == repeatedReceipt.Outcome, "Recovered logical receipt was not stable.");
        return new(ownerFenced, reconstructed, reclamation,
            Convert.ToHexStringLower(SHA256.HashData(TargetBytes)), TargetBytes.LongLength,
            Convert.ToHexStringLower(SHA256.HashData(ControlBytes)), ControlBytes.LongLength, outcome);
    }

    private static async Task<ArtifactMutationReceipt> PublishAsync(
        IArtifactStore store, byte[] bytes, CancellationToken cancellationToken)
    {
        var ticket = Need(await store.ReserveWriteAsync(new(new ArtifactExpectations(bytes.Length)), new(), cancellationToken));
        using var source = new MemoryStream(bytes, writable: false);
        var stage = Need(await store.StageAsync(ticket, source, new(), cancellationToken));
        return Need(await store.CommitAsync(stage, new(), cancellationToken));
    }

    private static async Task VerifyReadAsync(
        IArtifactStore store, ArtifactStamp stamp, byte[] expected, CancellationToken cancellationToken)
    {
        await using var session = Need(await store.OpenReadAsync(new(stamp.Identity.Digest,
            expectedStamp: new ArtifactOption<ArtifactStamp>.Some(stamp)), new(), cancellationToken));
        using var destination = new MemoryStream();
        var complete = Need(await session.CopyToAsync(destination, new(), cancellationToken));
        Require(complete.Length == expected.Length && destination.ToArray().AsSpan().SequenceEqual(expected),
            "Recovered content readback did not match its acknowledged bytes.");
    }

    private static void ValidateBoundary(string barrier)
    {
        if (barrier is not ("B0" or "B1" or "B2" or "B3" or "D0" or "D1"))
        { throw new ArgumentException("Unknown artifact crash boundary."); }
    }

    private static T Need<T>(ArtifactResult<T> result) where T : notnull
        => result is ArtifactResult<T>.Success success ? success.Value
            : throw new InvalidOperationException(result is ArtifactResult<T>.Failure failure
                ? "Artifact crash operation failed: " + failure.Code : "Artifact crash operation failed.");
    private static void Require(bool condition, string message)
    { if (!condition) { throw new InvalidOperationException(message); } }
}
