using Hoard.Abstractions.Storage;
using static Hoard.Testing.Conformance.Artifacts.ArtifactPublicationAssertions;

namespace Hoard.Testing.Conformance.Artifacts;

public sealed record ArtifactQuarantineReopen(
    IArtifactStoreLifetime Current, ArtifactStoreIdentity Identity, IArtifactCoordinationAuthority Authority,
    Func<(IArtifactStore Store, IArtifactStoreLifetime Lifetime)> Create);

public static class ArtifactEvidenceAssertions
{
    public static async Task FailedQuarantinePersistenceAsync(
        IArtifactStore store, IArtifactEvidenceValidator validator, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, IArtifactStoreLifetime lifetime, Func<bool> ready,
        Action capturePaths, Action damage, Action requirePermissionProof, Action denyPersistence,
        Action<byte[]> restorePayload, Action restorePermissions, CancellationToken cancellationToken,
        ArtifactQuarantineReopen? reopen)
    {
        var bytes = "quarantine survives denied decision persistence"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        capturePaths();
        damage();
        requirePermissionProof();
        try
        {
            denyPersistence();
            await using var guard = Success(await authority.AcquireAsync(new(Guid.NewGuid(),
                ArtifactProtectionOperation.Reference, identity, receipt.Stamp.Identity.Digest,
                new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), cancellationToken));
            var failed = Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await validator.ValidateAsync(proof, guard, new(), cancellationToken));
            Assert.Equal(ArtifactFailureCode.AccessDenied, failed.Code);
            restorePayload(bytes);
            Assert.False(ready());
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken));
            Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(
                await lifetime.StopAsync(new(TimeSpan.FromSeconds(1)), cancellationToken));
        }
        finally { restorePermissions(); }
        Success(await lifetime.StopAsync(new(), cancellationToken));
        Success(await lifetime.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible,
            identity, authority), new(), cancellationToken));
        await QuarantineIsPermanentAsync(store, receipt, bytes, cancellationToken, reopen);
    }

    public static Task ValidationFirstCorruptionAsync(
        IArtifactStore store, IArtifactEvidenceValidator validator, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, Action damage, Action<byte[]> restore,
        CancellationToken cancellationToken, ArtifactQuarantineReopen? reopen) =>
        ValidationFirstCorruptionAsync(store, validator, authority, identity,
            (_, _) => { damage(); return ValueTask.CompletedTask; },
            (_, bytes, _) => { restore(bytes.ToArray()); return ValueTask.CompletedTask; },
            cancellationToken, reopen);

    public static async Task ValidationFirstCorruptionAsync(
        IArtifactStore store, IArtifactEvidenceValidator validator, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, Func<ArtifactStamp, CancellationToken, ValueTask> damage,
        Func<ArtifactStamp, ReadOnlyMemory<byte>, CancellationToken, ValueTask> restore,
        CancellationToken cancellationToken, ArtifactQuarantineReopen? reopen,
        Func<CancellationToken, ValueTask<IArtifactStore>>? reopenAsync = null)
    {
        var bytes = "validation must quarantine this incarnation"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        var request = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Reference,
            identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        await using (var protection = Success(await authority.AcquireAsync(request, new(), cancellationToken)))
        {
            Assert.Equal(receipt.Stamp, Success(await validator.ValidateAsync(proof, protection, new(), cancellationToken)));
            await damage(receipt.Stamp, cancellationToken);
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await validator.ValidateAsync(proof, protection, new(), cancellationToken)).Code);
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)).Code);
            await restore(receipt.Stamp, bytes, cancellationToken);
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await validator.ValidateAsync(proof, protection, new(), cancellationToken)).Code);
        }
        if (reopenAsync is not null)
        {
            Assert.Null(reopen);
            await QuarantineAfterCompatibleReopenAsync(store, receipt, bytes, cancellationToken,
                async token => store = await reopenAsync(token));
        }
        else { await QuarantineIsPermanentAsync(store, receipt, bytes, cancellationToken, reopen); }
        var deletion = Success(await store.ReserveDeleteAsync(new(receipt.Stamp), new(), cancellationToken));
        Success(await store.DeleteAsync(deletion, new(), cancellationToken));
        using var replacementSource = new ShortSource(bytes);
        var replacement = await PublishAsync(store, replacementSource, new(1024), cancellationToken);
        Assert.NotEqual(receipt.Stamp.Incarnation, replacement.Stamp.Incarnation);
        Assert.Equal(receipt, Assert.IsType<ArtifactResolution.Committed>(
            Success(await store.ReconcileAsync(receipt.Ticket, new(), cancellationToken))).Receipt);
        Assert.Equal(bytes, await ReadAsync(store, replacement.Stamp, cancellationToken));
    }

    public static async Task ValidationAccessFailureAsync(
        IArtifactStore store, IArtifactEvidenceValidator validator, IArtifactCoordinationAuthority authority,
        ArtifactStoreIdentity identity, bool unavailable, Action prepare, Action deny, Action restore,
        CancellationToken cancellationToken)
    {
        var bytes = "permission failure is not corruption"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(store, source, new(1024), cancellationToken);
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        await using var guard = Success(await authority.AcquireAsync(new(Guid.NewGuid(),
            ArtifactProtectionOperation.Reference, identity, receipt.Stamp.Identity.Digest,
            new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), cancellationToken));
        prepare();
        try
        {
            deny();
            Assert.Equal(unavailable ? ArtifactFailureCode.Unavailable : ArtifactFailureCode.AccessDenied,
                Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await validator.ValidateAsync(proof, guard, new(), cancellationToken)).Code);
        }
        finally { restore(); }
        Assert.Equal(receipt.Stamp, Success(await validator.ValidateAsync(proof, guard, new(), cancellationToken)));
        Assert.Equal(bytes, await ReadAsync(store, receipt.Stamp, cancellationToken));
    }

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
        ArtifactQuarantineReopen? reopen)
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

    public static async Task QuarantineAfterCompatibleReopenAsync(
        IArtifactStore store, ArtifactMutationReceipt receipt, byte[] bytes, CancellationToken cancellationToken,
        Func<CancellationToken, ValueTask<IArtifactStore>> reopenAsync)
    {
        ArgumentNullException.ThrowIfNull(reopenAsync);
        await QuarantineIsPermanentAsync(store, receipt, bytes, cancellationToken, null);
        var reopened = await reopenAsync(cancellationToken);
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await reopened.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), cancellationToken)).Code);
    }

    private sealed class CopiedGuard(ArtifactProtectionGrant grant) : IArtifactProtectionGuard
    {
        public ArtifactProtectionGrant Grant => grant;
        public ValueTask DisposeAsync() => ValueTask.CompletedTask;
    }
}
