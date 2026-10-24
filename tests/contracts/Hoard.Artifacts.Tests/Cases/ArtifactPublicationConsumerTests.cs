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

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Shared_history_resume_assertion_rejects_hidden_candidate_failure_and_accepts_original_store(string provider)
    {
        var observedCandidates = 0;
        Task CheckAsync(IArtifactStore store, ArtifactProviderDriver driver) =>
            ArtifactHistoryAssertions.CandidateResumeAsync(store,
                observe =>
                {
                    void Observed(string kind, string id)
                    {
                        if (kind == "tickets") { Interlocked.Increment(ref observedCandidates); }
                        observe(kind, id);
                    }
                    if (driver.LocalControls is { } local) { local.BeforeHistoryCandidate = Observed; }
                    else { driver.ObjectControls!.BeforeHistoryCandidate = Observed; }
                }, default);

        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            var mutation = new HiddenCandidateFailure(driver.Store);
            await Assert.ThrowsAsync<Xunit.Sdk.IsTypeException>(() => CheckAsync(mutation, driver));
            Assert.Equal(106, mutation.ReserveCalls);
            Assert.Equal(1, mutation.HiddenFailures);
            Assert.Equal(1, mutation.RetryCalls);
            Assert.True(observedCandidates > 0);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            await CheckAsync(driver.Store, driver);
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Shared_source_ownership_assertion_rejects_optimistic_cleanup_and_accepts_original_store(string provider)
    {
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            var mutation = new OptimisticSourceCleanup(driver.Store);
            await Assert.ThrowsAsync<Xunit.Sdk.EqualException>(() =>
                ArtifactOwnershipAssertions.NoncooperativeSourceAsync(mutation, default));
            await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
            Assert.Equal(1, mutation.StageCalls);
            Assert.Equal(1, mutation.ReportedReleased);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            await ArtifactOwnershipAssertions.NoncooperativeSourceAsync(driver.Store, default);
            await driver.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(2));
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Shared_cancelled_descriptor_assertion_rejects_abandoned_current_owner_and_accepts_original_store(string provider)
    {
        {
            var clock = new ArtifactTestClock();
            await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
            var mutation = new AbandonedCurrentOwner(driver.Store, driver.WhenIdleAsync);
            await Assert.ThrowsAsync<Xunit.Sdk.IsTypeException>(() =>
                ArtifactOwnershipAssertions.CancelledStagedDescriptorAsync(
                    mutation, clock.Advance, driver.WhenIdleAsync, "completion", default));
            Assert.Equal(1, mutation.StageCalls);
            Assert.Equal(1, mutation.CommitCalls);
            Assert.Equal(1, mutation.AbandonedOwners);
        }
        {
            var clock = new ArtifactTestClock();
            await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock);
            await ArtifactOwnershipAssertions.CancelledStagedDescriptorAsync(
                driver.Store, clock.Advance, driver.WhenIdleAsync, "completion", default);
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Shared_result_handoff_assertion_rejects_discarded_reservation_and_accepts_original_store(string provider)
    {
        static async Task CheckAsync(IArtifactStore store, ArtifactProviderDriver driver)
        {
            await using var released = new ArtifactTestBarrier("shared-successful-result-handoff");
            await ArtifactHandoffAssertions.SuccessfulResultAsync(store, false,
                observe =>
                {
                    if (driver.LocalControls is { } local) { local.SetObserver("operation.released", observe); }
                    else { driver.ObjectControls!.SetObserver("object.operation-released", observe); }
                }, released.HoldAsync, () => released.Entered,
                () =>
                {
                    driver.LocalControls?.RemoveObserver("operation.released");
                    driver.ObjectControls?.RemoveObserver("object.operation-released");
                }, released.Release, default);
        }

        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new(artifactBytes: 1024, stagingBytes: 1024, transferSlots: 1, waitingCalls: 0)))
        {
            var mutation = new DiscardedReservation(driver.Store);
            await Assert.ThrowsAsync<Xunit.Sdk.IsTypeException>(() => CheckAsync(mutation, driver));
            Assert.Equal(1, mutation.ReserveCalls);
            var ticket = mutation.DiscardedTicket
                ?? throw new InvalidOperationException("Mutation requires an actual discarded reservation.");
            using var source = new ArtifactPublicationAssertions.ShortSource("actual discarded reservation recovery"u8.ToArray());
            var staged = ArtifactPublicationTests.Success(await driver.Store.StageAsync(ticket, source, new(), default));
            var receipt = ArtifactPublicationTests.Success(await driver.Store.CommitAsync(staged, new(), default));
            Assert.Equal(ArtifactMutationOutcome.Published, receipt.Outcome);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new(artifactBytes: 1024, stagingBytes: 1024, transferSlots: 1, waitingCalls: 0)))
        {
            await CheckAsync(driver.Store, driver);
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Shared_cap_assertion_rejects_misclassified_limit_and_accepts_original_store(string provider)
    {
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider, limits: new ArtifactLimits(10, 10, 1)))
        {
            var mutation = new MisclassifiedLimit(driver.Store);
            await Assert.ThrowsAsync<Xunit.Sdk.EqualException>(() =>
                ArtifactBudgetAssertions.CapCrossingAsync(mutation, default));
            Assert.Equal(1, mutation.StageCalls);
            Assert.Equal(1, mutation.MisclassifiedFailures);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider, limits: new ArtifactLimits(10, 10, 1)))
        {
            await ArtifactBudgetAssertions.CapCrossingAsync(driver.Store, default);
        }
    }

    [Theory]
    [InlineData("local", "sqlite")]
    [InlineData("local", "memory")]
    [InlineData("object", "sqlite")]
    [InlineData("object", "memory")]
    public async Task Shared_metadata_reference_assertion_rejects_hidden_denial_and_accepts_original_stores(
        string provider, string metadataProvider)
    {
        using (var root = ArtifactMetadataIntegrationTests.PrivateRoot())
        {
            await using var session = await Hoard.Fixtures.Artifacts.HostAdapters.ArtifactMetadataFixtureSession
                .CreateForQualificationAsync(provider, metadataProvider, root.Path);
            var mutation = new HiddenReferenceDenial(session.Artifacts.Store);
            var assertions = new ArtifactMetadataIntegrationAssertions(mutation, session.Metadata,
                session.Artifacts.Identity, session.Artifacts.Authority, session.Publication.Encode);
            await Assert.ThrowsAsync<Xunit.Sdk.EqualException>(() => assertions.ActualReferencesAsync(default));
            Assert.Equal(1, mutation.DeleteCalls);
            Assert.Equal(1, mutation.HiddenDenials);
        }
        using (var root = ArtifactMetadataIntegrationTests.PrivateRoot())
        {
            await using var session = await Hoard.Fixtures.Artifacts.HostAdapters.ArtifactMetadataFixtureSession
                .CreateForQualificationAsync(provider, metadataProvider, root.Path);
            await new ArtifactMetadataIntegrationAssertions(session.Artifacts.Store, session.Metadata,
                session.Artifacts.Identity, session.Artifacts.Authority, session.Publication.Encode)
                .ActualReferencesAsync(default);
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Shared_storage_failure_assertion_rejects_misclassified_denial_and_accepts_original_store(string provider)
    {
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            var mutation = new MisclassifiedStorageFailure(driver.Store);
            await Assert.ThrowsAsync<Xunit.Sdk.EqualException>(() =>
                ArtifactFailureAssertions.StorageFailuresAsync(mutation, default));
            Assert.Equal(1, mutation.StageCalls);
            Assert.Equal(1, mutation.MisclassifiedFailures);
        }
        await using (var driver = await ArtifactProviderDriver.CreateAsync(provider))
        {
            await ArtifactFailureAssertions.StorageFailuresAsync(driver.Store, default);
        }
    }

    private sealed class MisclassifiedStorageFailure(IArtifactStore store) : ForwardingStore(store)
    {
        public int StageCalls { get; private set; }
        public int MisclassifiedFailures { get; private set; }

        public override async ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
            ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct)
        {
            StageCalls++;
            var result = await Store.StageAsync(ticket, source, options, ct);
            if (result is not ArtifactResult<ArtifactStagedWrite>.Failure { Code: ArtifactFailureCode.AccessDenied } failed)
            { throw new InvalidOperationException("Mutation requires an actual storage access-denied failure."); }
            MisclassifiedFailures++;
            return new ArtifactResult<ArtifactStagedWrite>.Failure(
                ArtifactFailureCode.Unavailable, failed.Phase, failed.Action, failed.CorrelationId, failed.Ticket, failed.Cleanup);
        }
    }

    private sealed class HiddenReferenceDenial(IArtifactStore store) : ForwardingStore(store)
    {
        public int DeleteCalls { get; private set; }
        public int HiddenDenials { get; private set; }

        public override async ValueTask<ArtifactResult<ArtifactMutationReceipt>> DeleteAsync(
            ArtifactOperationTicket ticket, ArtifactCallOptions options, CancellationToken ct)
        {
            DeleteCalls++;
            var result = await Store.DeleteAsync(ticket, options, ct);
            if (result is not ArtifactResult<ArtifactMutationReceipt>.Failure { Code: ArtifactFailureCode.Denied } failed)
            { throw new InvalidOperationException("Mutation requires actual live-reference deletion denial."); }
            HiddenDenials++;
            return new ArtifactResult<ArtifactMutationReceipt>.Failure(
                ArtifactFailureCode.Conflict, failed.Phase, failed.Action, failed.CorrelationId, failed.Ticket, failed.Cleanup);
        }
    }

    private sealed class MisclassifiedLimit(IArtifactStore store) : ForwardingStore(store)
    {
        public int StageCalls { get; private set; }
        public int MisclassifiedFailures { get; private set; }

        public override async ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
            ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct)
        {
            StageCalls++;
            var result = await Store.StageAsync(ticket, source, options, ct);
            if (result is not ArtifactResult<ArtifactStagedWrite>.Failure { Code: ArtifactFailureCode.LimitExceeded } failed)
            { throw new InvalidOperationException("Mutation requires an actual input-limit failure."); }
            MisclassifiedFailures++;
            return new ArtifactResult<ArtifactStagedWrite>.Failure(
                ArtifactFailureCode.Capacity, failed.Phase, failed.Action, failed.CorrelationId, failed.Ticket, failed.Cleanup);
        }
    }

    private sealed class DiscardedReservation(IArtifactStore store) : ForwardingStore(store)
    {
        public int ReserveCalls { get; private set; }
        public ArtifactOperationTicket? DiscardedTicket { get; private set; }

        public override async ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(
            ArtifactWriteIntent intent, ArtifactCallOptions options, CancellationToken ct)
        {
            ReserveCalls++;
            var result = await Store.ReserveWriteAsync(intent, options, ct);
            if (!ct.IsCancellationRequested || result is not ArtifactResult<ArtifactOperationTicket>.Success reserved)
            { throw new InvalidOperationException("Mutation requires an actual successful reservation after cancellation."); }
            DiscardedTicket = reserved.Value;
            return new ArtifactResult<ArtifactOperationTicket>.Failure(
                ArtifactFailureCode.CancelledBeforeCommit, ArtifactPhase.Reserve, ArtifactAction.None, Guid.NewGuid());
        }
    }

    private sealed class AbandonedCurrentOwner(IArtifactStore store, Func<Task> whenIdle) : ForwardingStore(store)
    {
        private ArtifactStagedWrite? current;
        public int StageCalls { get; private set; }
        public int CommitCalls { get; private set; }
        public int AbandonedOwners { get; private set; }

        public override async ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
            ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct)
        {
            StageCalls++;
            var result = await Store.StageAsync(ticket, source, options, ct);
            if (result is ArtifactResult<ArtifactStagedWrite>.Success staged) { current = staged.Value; }
            return result;
        }

        public override async ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(
            ArtifactStagedWrite staged, ArtifactTransferOptions options, CancellationToken ct)
        {
            CommitCalls++;
            var verified = current ?? throw new InvalidOperationException("Mutation requires actual verified staging.");
            if (!ct.IsCancellationRequested || staged.VerifiedCompletion == verified.VerifiedCompletion)
            { throw new InvalidOperationException("Mutation requires a cancelled altered completion claim."); }
            var result = await Store.CommitAsync(staged, options, ct);
            if (result is not ArtifactResult<ArtifactMutationReceipt>.Failure)
            { throw new InvalidOperationException("Mutation requires actual rejected commit."); }
            await whenIdle().WaitAsync(TimeSpan.FromSeconds(2));
            var abandoned = await Store.AbandonAsync(verified.Owner, new(), CancellationToken.None);
            if (abandoned is not ArtifactResult<ArtifactCleanupReport>.Success { Value.Completed: 1 })
            { throw new InvalidOperationException("Mutation requires actual current-owner abandonment."); }
            AbandonedOwners++;
            return result;
        }
    }

    private sealed class OptimisticSourceCleanup(IArtifactStore store) : ForwardingStore(store)
    {
        public int StageCalls { get; private set; }
        public int ReportedReleased { get; private set; }

        public override async ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(
            ArtifactOperationTicket ticket, Stream source, ArtifactTransferOptions options, CancellationToken ct)
        {
            StageCalls++;
            var result = await Store.StageAsync(ticket, source, options, ct);
            if (result is not ArtifactResult<ArtifactStagedWrite>.Failure
                { Code: ArtifactFailureCode.CancelledBeforeCommit, Cleanup: ArtifactCleanupState.RetainedLiveOwnership } failed)
            { throw new InvalidOperationException("Mutation requires actual retained source ownership."); }
            ReportedReleased++;
            return new ArtifactResult<ArtifactStagedWrite>.Failure(
                failed.Code, failed.Phase, failed.Action, failed.CorrelationId, failed.Ticket, ArtifactCleanupState.Released);
        }
    }

    private sealed class HiddenCandidateFailure(IArtifactStore store) : ForwardingStore(store)
    {
        public int ReserveCalls { get; private set; }
        public int HiddenFailures { get; private set; }
        public int RetryCalls { get; private set; }

        public override async ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(
            ArtifactWriteIntent intent, ArtifactCallOptions options, CancellationToken ct)
        {
            ReserveCalls++;
            var result = await Store.ReserveWriteAsync(intent, options, ct);
            if (result is ArtifactResult<ArtifactOperationTicket>.Failure { Code: ArtifactFailureCode.InternalFailure })
            {
                HiddenFailures++;
                RetryCalls++;
                return await Store.ReserveWriteAsync(intent, options, ct);
            }
            return result;
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

        public virtual ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(
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
        public virtual ValueTask<ArtifactResult<ArtifactMutationReceipt>> DeleteAsync(
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
