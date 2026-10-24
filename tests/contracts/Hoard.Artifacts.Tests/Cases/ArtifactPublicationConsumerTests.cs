using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Artifacts;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactPublicationConsumerTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Shared_duplicate_assertion_rejects_substituted_source_and_accepts_original_store(string provider)
    {
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            var mutation = new SubstitutedDuplicateSource(driver.Store);
            var failure = await Assert.ThrowsAsync<Xunit.Sdk.TrueException>(() =>
                ArtifactPublicationAssertions.VerifiedDuplicatesAsync(mutation, default));
            Assert.Contains("Assert.True()", failure.Message);
            Assert.Equal(2, mutation.StageCalls);
            Assert.Equal(2, mutation.CommitCalls);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            await ArtifactPublicationAssertions.VerifiedDuplicatesAsync(driver.Store, default);
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Shared_conflicting_length_assertion_rejects_repaired_forgery_and_accepts_original_store(string provider)
    {
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            var mutation = new AcceptedConflictingLength(driver.Store);
            await Assert.ThrowsAsync<Xunit.Sdk.IsTypeException>(() =>
                ArtifactPublicationAssertions.ConflictingStagedLengthAsync(mutation, default));
            Assert.Equal(2, mutation.CommitCalls);
            Assert.Equal(1, mutation.RepairedClaims);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            await ArtifactPublicationAssertions.ConflictingStagedLengthAsync(driver.Store, default);
        }
    }

    private sealed class AcceptedConflictingLength(IArtifactStore store) : ForwardingStore(store)
    {
        private long? stagedLength;
        public int CommitCalls { get; private set; }
        public int RepairedClaims { get; private set; }

        public override async ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
            ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct)
        {
            var result = await Store.StageAsync(ticket, source, options, ct);
            if (result is ArtifactResult<ArtifactStagedWrite>.Success staged)
            { stagedLength = staged.Value.Identity.Length; }
            return result;
        }

        public override ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(
            ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct)
        {
            CommitCalls++;
            var length = stagedLength ?? throw new InvalidOperationException("Mutation requires actual staged bytes.");
            if (staged.Identity.Length != length) { RepairedClaims++; }
            var repaired = new ArtifactStagedWrite(staged.Owner, new(staged.Identity.Digest, length),
                staged.VerifiedCompletion, staged.PrivateHandle);
            return Store.CommitAsync(repaired, options, ct);
        }
    }

    private sealed class SubstitutedDuplicateSource(IArtifactStore store) : ForwardingStore(store)
    {
        private byte[]? original;
        public int StageCalls { get; private set; }
        public int CommitCalls { get; private set; }

        public override async ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
            ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct)
        {
            StageCalls++;
            if (original is null)
            {
                using var captured = new MemoryStream();
                await source.CopyToAsync(captured, ct);
                original = captured.ToArray();
            }
            using var substituted = new MemoryStream(original);
            return await Store.StageAsync(ticket, substituted, options, ct);
        }

        public override ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(
            ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct)
        {
            CommitCalls++;
            return Store.CommitAsync(staged, options, ct);
        }
    }

    private abstract class ForwardingStore(IArtifactStore store) : IArtifactStore
    {
        protected IArtifactStore Store { get; } = store;
        public ArtifactCapabilities Capabilities => Store.Capabilities;
        public virtual ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
            ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct) =>
            Store.StageAsync(ticket, source, options, ct);
        public virtual ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(
            ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct) =>
            Store.CommitAsync(staged, options, ct);

        public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(
            ArtifactWriteIntent intent, ArtifactCallOptions options, CancellationToken ct) =>
            Store.ReserveWriteAsync(intent, options, ct);
        public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveDeleteAsync(
            ArtifactDeleteIntent intent, ArtifactCallOptions options, CancellationToken ct) =>
            Store.ReserveDeleteAsync(intent, options, ct);
        public ValueTask<ArtifactResult<ArtifactStagingOwner>> RenewAsync(
            ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct) =>
            Store.RenewAsync(owner, options, ct);
        public ValueTask<ArtifactResult<IArtifactReadSession>> OpenReadAsync(
            ArtifactReadRequest request, ArtifactCallOptions options, CancellationToken ct) =>
            Store.OpenReadAsync(request, options, ct);
        public ValueTask<ArtifactResult<ArtifactMutationReceipt>> DeleteAsync(
            ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct) =>
            Store.DeleteAsync(ticket, options, ct);
        public ValueTask<ArtifactResult<ArtifactResolution>> ReconcileAsync(
            ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct) =>
            Store.ReconcileAsync(ticket, options, ct);
        public ValueTask<ArtifactResult<ArtifactCleanupReport>> AbandonAsync(
            ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct) =>
            Store.AbandonAsync(owner, options, ct);
    }
}
