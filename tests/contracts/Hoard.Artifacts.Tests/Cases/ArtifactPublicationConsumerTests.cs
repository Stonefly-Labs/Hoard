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

    private sealed class SubstitutedDuplicateSource(IArtifactStore store) : IArtifactStore
    {
        private byte[]? original;
        public int StageCalls { get; private set; }
        public int CommitCalls { get; private set; }
        public ArtifactCapabilities Capabilities => store.Capabilities;

        public async ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
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
            return await store.StageAsync(ticket, substituted, options, ct);
        }

        public ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(
            ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct)
        {
            CommitCalls++;
            return store.CommitAsync(staged, options, ct);
        }

        public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(
            ArtifactWriteIntent intent, ArtifactCallOptions options, CancellationToken ct) =>
            store.ReserveWriteAsync(intent, options, ct);
        public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveDeleteAsync(
            ArtifactDeleteIntent intent, ArtifactCallOptions options, CancellationToken ct) =>
            store.ReserveDeleteAsync(intent, options, ct);
        public ValueTask<ArtifactResult<ArtifactStagingOwner>> RenewAsync(
            ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct) =>
            store.RenewAsync(owner, options, ct);
        public ValueTask<ArtifactResult<IArtifactReadSession>> OpenReadAsync(
            ArtifactReadRequest request, ArtifactCallOptions options, CancellationToken ct) =>
            store.OpenReadAsync(request, options, ct);
        public ValueTask<ArtifactResult<ArtifactMutationReceipt>> DeleteAsync(
            ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct) =>
            store.DeleteAsync(ticket, options, ct);
        public ValueTask<ArtifactResult<ArtifactResolution>> ReconcileAsync(
            ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct) =>
            store.ReconcileAsync(ticket, options, ct);
        public ValueTask<ArtifactResult<ArtifactCleanupReport>> AbandonAsync(
            ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct) =>
            store.AbandonAsync(owner, options, ct);
    }
}
