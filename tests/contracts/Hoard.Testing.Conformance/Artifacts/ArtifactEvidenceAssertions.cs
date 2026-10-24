using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public sealed record ArtifactQuarantineReopen(
    IArtifactStoreLifetime Current, ArtifactStoreIdentity Identity, IArtifactCoordinationAuthority Authority,
    Func<(IArtifactStore Store, IArtifactStoreLifetime Lifetime)> Create);

public static class ArtifactEvidenceAssertions
{
    public static async Task ExactCurrentReceiptsAsync(
        IArtifactStore store, IArtifactEvidenceValidator validator, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, CancellationToken cancellationToken)
    {
        using var source = new ShortSource("attributable evidence"u8.ToArray());
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        var request = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Reference,
            identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        var protection = Success(await authority.AcquireAsync(request, new(), cancellationToken));
        try
        {
            Assert.Equal(receipt.Stamp, Success(await validator.ValidateAsync(proof, protection, new(), cancellationToken)));
            var wrong = new ArtifactCommitEvidence(proof.Stamp, proof.TicketId, Guid.NewGuid(), proof.ProofHandle, proof.Outcome);
            Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(await validator.ValidateAsync(wrong, protection, new(), cancellationToken));
            await using var copied = new CopiedGuard(protection.Grant);
            Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await validator.ValidateAsync(proof, copied, new(), cancellationToken)).Code);
            var foreignStamp = new ArtifactStamp(new ArtifactStoreIdentity(identity.ProviderModuleId,
                identity.InstanceId, Guid.NewGuid()), proof.Stamp.Identity, proof.Stamp.Incarnation);
            var foreign = new ArtifactCommitEvidence(foreignStamp, proof.TicketId, proof.ReceiptId, proof.ProofHandle, proof.Outcome);
            Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(await validator.ValidateAsync(foreign, protection, new(), cancellationToken));
        }
        finally { await protection.DisposeAsync(); }
        Assert.Equal(ArtifactFailureCode.Denied, Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
            await validator.ValidateAsync(proof, protection, new(), cancellationToken)).Code);
    }

    public static async Task QuarantineIsPermanentAsync(
        IArtifactStore store, ArtifactMutationReceipt receipt, byte[] bytes, CancellationToken cancellationToken,
        ArtifactQuarantineReopen? reopen = null)
    {
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)).Code);
        var ticket = Success(await store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), cancellationToken));
        using var duplicate = new ShortSource(bytes);
        var staged = Success(await store.StageAsync(ticket, duplicate, new(), cancellationToken));
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await store.CommitAsync(staged, new(), cancellationToken)).Code);
        Success(await store.AbandonAsync(staged.Owner, new(), cancellationToken));
        Assert.Equal(receipt, Assert.IsType<ArtifactResolution.Committed>(
            Success(await store.ReconcileAsync(receipt.Ticket, new(), cancellationToken))).Receipt);
        if (reopen is not null)
        {
            Success(await reopen.Current.StopAsync(new(), cancellationToken));
            var reopened = reopen.Create();
            try
            {
                Success(await reopened.Lifetime.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible,
                    reopen.Identity, reopen.Authority), new(), cancellationToken));
                Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                    await reopened.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)).Code);
            }
            finally { Success(await reopened.Lifetime.StopAsync(new(), cancellationToken)); }
            Success(await reopen.Current.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible,
                reopen.Identity, reopen.Authority), new(), cancellationToken));
        }
    }

    private sealed class CopiedGuard(ArtifactProtectionGrant grant) : IArtifactProtectionGuard
    {
        public ArtifactProtectionGrant Grant => grant;
        public ValueTask DisposeAsync() => ValueTask.CompletedTask;
    }
}
