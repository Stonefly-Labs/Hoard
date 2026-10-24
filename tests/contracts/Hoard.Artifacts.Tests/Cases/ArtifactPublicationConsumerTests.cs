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

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Shared_receipt_retry_assertion_rejects_foreign_receipt_and_accepts_original_store(string provider)
    {
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            var mutation = new ForeignReconciledReceipt(driver.Store);
            await Assert.ThrowsAsync<Xunit.Sdk.EqualException>(() =>
                ArtifactReconciliationAssertions.AcknowledgedReceiptRetryAsync(mutation, default));
            Assert.Equal(1, mutation.ReconcileCalls);
            Assert.Equal(1, mutation.ForeignPublications);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            await ArtifactReconciliationAssertions.AcknowledgedReceiptRetryAsync(driver.Store, default);
        }
    }

    [Fact]
    public async Task Shared_visibility_assertion_rejects_premature_acknowledgment_and_accepts_original_store()
    {
        static async Task CheckAsync(IArtifactStore store, Action<Func<ValueTask>> observeAcknowledgment)
        {
            await using var boundary = new ArtifactTestBarrier("shared-receipt-before-acknowledgment");
            await ArtifactVisibilityAssertions.VisibleBeforeAcknowledgmentAsync(store,
                () => observeAcknowledgment(() => new(boundary.HoldAsync())),
                token => boundary.Entered.WaitAsync(token), boundary.Release, default);
        }

        await using (var driver = await ArtifactProviderDriver.CreateAsync("local"))
        {
            using var source = new ArtifactPublicationAssertions.ShortSource("actual premature acknowledgment control"u8.ToArray());
            var foreign = await ArtifactPublicationAssertions.PublishAsync(driver.Store, source, new(1024), default);
            var mutation = new PrematureAcknowledgment(driver.Store, foreign);
            await Assert.ThrowsAsync<Xunit.Sdk.FalseException>(() =>
                CheckAsync(mutation, observer => driver.LocalControls!.SetObserver("publish.receipted", observer)));
            Assert.Equal(1, mutation.CommitCalls);
            var actual = ArtifactPublicationTests.Success(await mutation.WaitForCommitAsync());
            Assert.NotEqual(foreign.Stamp, actual.Stamp);
            Assert.Equal(ArtifactMutationOutcome.Published, actual.Outcome);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync("local"))
        {
            await CheckAsync(driver.Store, observer => driver.LocalControls!.SetObserver("publish.receipted", observer));
        }
    }

    private sealed class PrematureAcknowledgment(IArtifactStore store, ArtifactMutationReceipt foreign) : ForwardingStore(store)
    {
        private Task<ArtifactResult<ArtifactMutationReceipt>>? actualCommit;
        public int CommitCalls { get; private set; }

        public override ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(
            ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct)
        {
            CommitCalls++;
            actualCommit = Store.CommitAsync(staged, options, ct).AsTask();
            return ValueTask.FromResult<ArtifactResult<ArtifactMutationReceipt>>(
                new ArtifactResult<ArtifactMutationReceipt>.Success(foreign));
        }

        public Task<ArtifactResult<ArtifactMutationReceipt>> WaitForCommitAsync() =>
            (actualCommit ?? throw new InvalidOperationException("Mutation requires an actual pending commit."))
            .WaitAsync(TimeSpan.FromSeconds(5));
    }

    private sealed class ForeignReconciledReceipt(IArtifactStore store) : ForwardingStore(store)
    {
        public int ReconcileCalls { get; private set; }
        public int ForeignPublications { get; private set; }

        public override async ValueTask<ArtifactResult<ArtifactResolution>> ReconcileAsync(
            ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct)
        {
            ReconcileCalls++;
            var original = Assert.IsType<ArtifactResolution.Committed>(
                ArtifactPublicationTests.Success(await Store.ReconcileAsync(ticket, options, ct)));
            using var source = new ArtifactPublicationAssertions.ShortSource("foreign actual reconciliation receipt"u8.ToArray());
            var foreign = await ArtifactPublicationAssertions.PublishAsync(Store, source, new(1024), ct);
            ForeignPublications++;
            Assert.NotEqual(original.Receipt, foreign);
            return new ArtifactResult<ArtifactResolution>.Success(new ArtifactResolution.Committed(foreign));
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
        public virtual ValueTask<ArtifactResult<ArtifactResolution>> ReconcileAsync(
            ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct) =>
            Store.ReconcileAsync(ticket, options, ct);
        public ValueTask<ArtifactResult<ArtifactCleanupReport>> AbandonAsync(
            ArtifactStagingOwner owner, ArtifactCallOptions options, CancellationToken ct) =>
            Store.AbandonAsync(owner, options, ct);
    }
}
