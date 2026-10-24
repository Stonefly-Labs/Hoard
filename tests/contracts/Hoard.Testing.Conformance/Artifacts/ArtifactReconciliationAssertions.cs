using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public static class ArtifactReconciliationAssertions
{
    public static async Task FinalizedMutationExpiryAsync(
        IArtifactStore store, Action<TimeSpan> advanceClock, CancellationToken cancellationToken)
    {
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var source = new ShortSource("expired mutations"u8.ToArray());
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        var receipt = Success(await store.CommitAsync(staged, new(), cancellationToken));
        var deletion = Success(await store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
        Success(await store.DeleteAsync(deletion, new(), cancellationToken));
        var altered = new ArtifactOperationTicket(deletion.Store, deletion.Id, deletion.Kind,
            deletion.Issued, deletion.Expires, new string('a', 64));
        Assert.Equal(ArtifactFailureCode.InvalidInput, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.DeleteAsync(altered, new(), cancellationToken)).Code);
        advanceClock(TimeSpan.FromHours(24));
        Assert.Equal(ArtifactFailureCode.ReconciliationExpired, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.CommitAsync(staged, new(), cancellationToken)).Code);
        Assert.Equal(ArtifactFailureCode.ReconciliationExpired, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.DeleteAsync(deletion, new(), cancellationToken)).Code);
    }

    public static async Task AcknowledgedReceiptRetryAsync(IArtifactStore store, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("exact receipt retry"u8.ToArray());
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        var original = Success(await store.CommitAsync(staged, new(), cancellationToken));
        var resolved = Assert.IsType<ArtifactResolution.Committed>(
            Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        Assert.Equal(original, resolved.Receipt);
        Assert.Equal(original, Success(await store.CommitAsync(staged, new(), cancellationToken)));
        using var extraSource = new ShortSource("must not read decided input"u8.ToArray());
        Assert.Equal(ArtifactFailureCode.Conflict, Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
            await store.StageAsync(ticket, extraSource, new(), cancellationToken)).Code);
        Assert.Equal(0, extraSource.BytesRead);
        var changedIntent = new ArtifactOperationTicket(ticket.Store, ticket.Id, ticket.Kind,
            ticket.Issued, ticket.Expires, new string('f', 64));
        Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
            await store.ReconcileAsync(changedIntent, new(), cancellationToken));
    }

    public static async Task LostAcknowledgmentAsync(
        IArtifactStore store, Action loseAcknowledgment, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("lost publication acknowledgment"u8.ToArray());
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        var staged = Success(await store.StageAsync(ticket, source, new(), cancellationToken));
        loseAcknowledgment();
        Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.CommitAsync(staged, new(), cancellationToken)).Code);
        var resolved = Assert.IsType<ArtifactResolution.Committed>(
            Success(await store.ReconcileAsync(ticket, new(), cancellationToken)));
        Assert.Equal(ArtifactMutationOutcome.Published, resolved.Receipt.Outcome);
        Assert.Equal("lost publication acknowledgment"u8.ToArray(),
            await ReadAsync(store, resolved.Receipt.Stamp, cancellationToken));
        Assert.Equal(resolved.Receipt, Success(await store.CommitAsync(staged, new(), cancellationToken)));
    }

    public static async Task ExpiredHistoryRollbackAsync(
        IArtifactStore store, ArtifactStoreIdentity identity, Action<TimeSpan> advanceClock, Action<long> setUtc,
        CancellationToken cancellationToken)
    {
        using var source = new ShortSource("history expiry"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        advanceClock(TimeSpan.FromHours(24));
        Assert.Equal(ArtifactFailureCode.ReconciliationExpired, Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
            await store.ReconcileAsync(receipt.Ticket, new(), cancellationToken)).Code);
        setUtc(receipt.Ticket.Issued.ToUnixTimeMilliseconds());
        Assert.Equal(ArtifactFailureCode.ReconciliationExpired, Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
            await store.ReconcileAsync(receipt.Ticket, new(), cancellationToken)).Code);
        var foreign = new ArtifactOperationTicket(new ArtifactStoreIdentity(identity.ProviderModuleId,
            identity.InstanceId, Guid.NewGuid()), receipt.Ticket.Id, receipt.Ticket.Kind,
            receipt.Ticket.Issued, receipt.Ticket.Expires, receipt.Ticket.IntentFingerprint);
        Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
            await store.ReconcileAsync(foreign, new(), cancellationToken));
    }
}
