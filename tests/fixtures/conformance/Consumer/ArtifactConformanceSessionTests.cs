using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Conformance.Bindings.Local;
using Hoard.Fixtures.Conformance.Bindings.ObjectSemantics;
using Hoard.Testing.Conformance.Artifacts;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Evidence;
using Xunit.Abstractions;
using RecordingDirectories = Hoard.Fixtures.Conformance.Consumer.LocalArtifactSessionTests.RecordingDirectories;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class ArtifactConformanceSessionTests(ITestOutputHelper output)
{
    [Theory]
    [InlineData("local", "receipt")]
    [InlineData("object", "receipt")]
    [InlineData("local", "read-open")]
    [InlineData("object", "read-open")]
    [InlineData("local", "verified-reconciliation")]
    [InlineData("object", "verified-reconciliation")]
    public async Task Observed_receipts_and_failed_callbacks_preserve_actual_resource_ownership(
        string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var limits = consumer == "read-open"
            ? new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, transferSlots: 1, waitingCalls: 0) : null;
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider, limits), context, default);
        var registrations = new Dictionary<ArtifactObservationPoint, IAsyncDisposable>();
        try
        {
            async ValueTask Observe(ArtifactObservationPoint point, Func<ValueTask> callback) =>
                registrations.Add(point, await session.Faults.ObserveBoundaryAsync(point, callback, default));
            async ValueTask Inject(ArtifactObservationPoint point, Func<ValueTask> callback) =>
                registrations.Add(point, await session.Faults.InjectObservationFailureAsync(point, callback, default));
            ValueTask Remove(ArtifactObservationPoint point) => registrations[point].DisposeAsync();
            async ValueTask LoseAcknowledgment() => registrations.Add(ArtifactObservationPoint.PublicationSelected,
                await session.Faults.InjectPublicationAcknowledgmentLossAsync(default));
            async ValueTask RemoveReconciliation()
            {
                await Remove(ArtifactObservationPoint.BeforeReconciliation);
                await Remove(ArtifactObservationPoint.ReconciliationVerified);
            }
            await (consumer switch
            {
                "receipt" => ArtifactObservationAssertions.ReceiptPersistedAsync(session.Store,
                    callback => Observe(ArtifactObservationPoint.ReceiptPersisted, callback),
                    () => Remove(ArtifactObservationPoint.ReceiptPersisted), default),
                "read-open" => ArtifactObservationAssertions.ReadOpenedFailureAsync(session.Store,
                    () => Inject(ArtifactObservationPoint.ReadOpened, () => ValueTask.CompletedTask),
                    () => Remove(ArtifactObservationPoint.ReadOpened), default),
                "verified-reconciliation" => ArtifactObservationAssertions.ReconciliationVerifiedAsync(session.Store,
                    LoseAcknowledgment, () => Remove(ArtifactObservationPoint.PublicationSelected),
                    callback => Observe(ArtifactObservationPoint.BeforeReconciliation, callback),
                    callback => Inject(ArtifactObservationPoint.ReconciliationVerified, callback),
                    RemoveReconciliation, default),
                _ => throw new ArgumentException("BindingInvalid")
            });
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            try { foreach (var registration in registrations.Values) { await registration.DisposeAsync(); } }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", ArtifactObservationPoint.ReadOpened)]
    [InlineData("object", ArtifactObservationPoint.ReadOpened)]
    [InlineData("local", ArtifactObservationPoint.ReconciliationVerified)]
    [InlineData("object", ArtifactObservationPoint.ReconciliationVerified)]
    public async Task Ordinary_errors_inside_owned_failure_callbacks_still_fault_actual_settlement(
        string provider, ArtifactObservationPoint point)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        var failure = new InvalidOperationException("InjectedObservationFailure");
        try
        {
            var ticket = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Value;
            using var source = new ArtifactPublicationAssertions.ShortSource("ordinary callback ownership"u8.ToArray());
            var staged = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Success>(
                await session.Store.StageAsync(ticket, source, new(), default)).Value;
            if (point == ArtifactObservationPoint.ReconciliationVerified)
            {
                await using var loss = await session.Faults.InjectPublicationAcknowledgmentLossAsync(default);
                Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                    await session.Store.CommitAsync(staged, new(), default)).Code);
            }
            else { Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Success>(
                await session.Store.CommitAsync(staged, new(), default)); }
            await using var injection = await session.Faults.InjectObservationFailureAsync(
                point, () => ValueTask.FromException(failure), default);
            if (point == ArtifactObservationPoint.ReadOpened)
            {
                Assert.Equal(ArtifactFailureCode.InternalFailure, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                    await session.Store.OpenReadAsync(new(staged.Identity.Digest), new(), default)).Code);
            }
            else
            {
                Assert.Equal(ArtifactFailureCode.InternalFailure, Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
                    await session.Store.ReconcileAsync(ticket, new(), default)).Code);
            }
            Assert.Equal(1, injection.ObservationCount);
            await session.Faults.AwaitSettlementAsync(default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await Assert.ThrowsAsync<InvalidOperationException>(() => session.DisposeAsync().AsTask()); }
        var settlement = Assert.Single(resources.Settlements).Value;
        Assert.True(settlement.IsFaulted);
        Assert.Contains(failure, settlement.Exception!.InnerExceptions);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "tickets")]
    [InlineData("object", "tickets")]
    [InlineData("local", "dependencies")]
    [InlineData("object", "dependencies")]
    [InlineData("local", "decisions")]
    [InlineData("object", "decisions")]
    [InlineData("local", "reclamation")]
    public async Task Observed_history_candidates_preserve_the_original_page_bounds(string provider, string kind)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var limits = new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1048576, committedIdentities: 128);
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider, limits), context, default);
        IAsyncDisposable? observation = null;
        try
        {
            async ValueTask Observe(Action<string, string> callback) =>
                observation = await session.Faults.ObserveHistoryCandidatesAsync(callback, default);
            await ArtifactHistoryAssertions.CandidateBoundsAsync(session.Store, kind, Observe, default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            try { if (observation is not null) { await observation.DisposeAsync(); } }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Observed_history_candidates_resume_after_an_owned_one_shot_failure(string provider)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        IAsyncDisposable? observation = null;
        IArtifactFaultRegistration? injection = null;
        try
        {
            async ValueTask Observe(Action<string, string> callback)
            {
                observation = await session.Faults.ObserveHistoryCandidatesAsync(callback, default);
                Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(
                    () => session.Faults.ObserveHistoryCandidatesAsync(callback, default).AsTask())).Message);
            }
            async ValueTask Inject()
            {
                injection = await session.Faults.InjectHistoryCandidateFailureAsync(default);
                Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(
                    () => session.Faults.InjectHistoryCandidateFailureAsync(default).AsTask())).Message);
            }
            await ArtifactHistoryAssertions.CandidateResumeAsync(session.Store, Observe, Inject, default);
            Assert.Equal(1, (injection ?? throw new InvalidOperationException("BindingInvalid")).ObservationCount);
            await injection.WaitForEntryAsync(default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            try
            {
                if (injection is not null) { await injection.DisposeAsync(); }
                if (observation is not null) { await observation.DisposeAsync(); }
            }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Ordinary_candidate_shaped_observer_errors_still_fault_actual_settlement(string provider)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        var failure = new InvalidOperationException("InjectedHistoryCandidateFailure");
        try
        {
            Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default));
            await using var injection = await session.Faults.InjectHistoryCandidateFailureAsync(default);
            await using var observation = await session.Faults.ObserveHistoryCandidatesAsync((_, _) => throw failure, default);
            Assert.Equal(ArtifactFailureCode.InternalFailure, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1)), new(), default)).Code);
            Assert.Equal(0, injection.ObservationCount);
            await session.Faults.AwaitSettlementAsync(default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await Assert.ThrowsAsync<InvalidOperationException>(() => session.DisposeAsync().AsTask()); }
        var settlement = Assert.Single(resources.Settlements).Value;
        Assert.True(settlement.IsFaulted);
        Assert.Contains(failure, settlement.Exception!.InnerExceptions);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "settled-replacement")]
    [InlineData("local", "reconciliation-history")]
    [InlineData("local", "cleanup-generation")]
    [InlineData("object", "settled-replacement")]
    [InlineData("object", "reconciliation-history")]
    [InlineData("object", "cleanup-generation")]
    public async Task Observed_reconciliation_and_cleanup_preserve_admitted_generation_ownership(
        string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var clock = new ControlledClock();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", clock,
            resources, new ConformanceEvidenceBuffer());
        var limits = consumer == "reconciliation-history"
            ? new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024, liveTickets: 1) : null;
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider, limits), context, default);
        IArtifactFaultRegistration? acknowledgment = null;
        IAsyncDisposable? observation = null;
        try
        {
            var point = consumer == "cleanup-generation" ? ArtifactObservationPoint.CleanupCandidate
                : provider == "local" ? ArtifactObservationPoint.BeforeReconciliation : ArtifactObservationPoint.DirectVerification;
            async ValueTask LoseAcknowledgment() =>
                acknowledgment = await session.Faults.InjectPublicationAcknowledgmentLossAsync(default);
            ValueTask RestoreAcknowledgment() =>
                (acknowledgment ?? throw new InvalidOperationException("BindingInvalid")).DisposeAsync();
            async ValueTask Observe(Func<ValueTask> callback) =>
                observation = await session.Faults.ObserveBoundaryAsync(point, callback, default);
            ValueTask Remove() => (observation ?? throw new InvalidOperationException("BindingInvalid")).DisposeAsync();
            await (consumer switch
            {
                "settled-replacement" => ArtifactRecoveryAssertions.SettledReceiptReplacementAsync(
                    session.Store, clock.SetUtc, LoseAcknowledgment, RestoreAcknowledgment, Observe, Remove, default),
                "reconciliation-history" => ArtifactRecoveryAssertions.AdmittedReconciliationHistoryAsync(
                    session.Store, clock.SetUtc, LoseAcknowledgment, RestoreAcknowledgment, Observe, Remove, default),
                "cleanup-generation" => ArtifactRecoveryAssertions.LateCleanupGenerationAsync(
                    session.Store, session.Maintenance, session.Identity, clock.Advance, Observe, Remove, default),
                _ => throw new ArgumentException("BindingInvalid")
            });
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            try
            {
                if (observation is not null) { await observation.DisposeAsync(); }
                if (acknowledgment is not null) { await acknowledgment.DisposeAsync(); }
            }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "delete-history")]
    [InlineData("local", "transfer-queue")]
    [InlineData("local", "released-shutdown")]
    [InlineData("object", "delete-history")]
    [InlineData("object", "transfer-queue")]
    [InlineData("object", "released-shutdown")]
    public async Task Observed_admitted_work_preserves_history_queue_and_shutdown_ownership(
        string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var clock = new ControlledClock();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", clock,
            resources, new ConformanceEvidenceBuffer());
        var limits = consumer switch
        {
            "delete-history" => new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, committedIdentities: 1),
            "transfer-queue" => new ArtifactLimits(artifactBytes: 1, stagingBytes: 3, transferSlots: 1, waitingCalls: 1),
            _ => null
        };
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider, limits), context, default);
        try
        {
            Task WhenIdle() => session.Faults.AwaitSettlementAsync(default).AsTask();
            var point = consumer switch
            {
                "delete-history" => ArtifactObservationPoint.DeleteRemoved,
                "transfer-queue" => ArtifactObservationPoint.TransferQueued,
                "released-shutdown" => ArtifactObservationPoint.OperationReleased,
                _ => throw new ArgumentException("BindingInvalid")
            };
            await ObserveAsync(session, point, observe => consumer switch
            {
                "delete-history" => ArtifactRecoveryAssertions.AdmittedDeleteHistoryAsync(
                    session.Store, session.Maintenance, session.Identity, clock.SetUtc, observe, default),
                "transfer-queue" => ArtifactBudgetAssertions.TransferQueueAsync(session.Store, observe, default),
                "released-shutdown" => ArtifactLifecycleAssertions.ReleasedBoundaryOwnershipAsync(
                    session.Store, observe, WhenIdle, () => session.Lifetime.StopAsync(new(TimeSpan.FromSeconds(5)), default),
                    default),
                _ => throw new ArgumentException("BindingInvalid")
            });
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "history")]
    [InlineData("local", "write-capacity")]
    [InlineData("local", "delete-capacity")]
    [InlineData("object", "history")]
    [InlineData("object", "write-capacity")]
    [InlineData("object", "delete-capacity")]
    public async Task Observed_clock_rollback_preserves_expiry_and_monotonic_ownership(string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var clock = new ControlledClock();
        var started = clock.GetTimestamp();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", clock,
            resources, new ConformanceEvidenceBuffer());
        var limits = consumer == "history" ? null
            : new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, liveTickets: 4);
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider, limits), context, default);
        try
        {
            await (consumer switch
            {
                "history" => ArtifactReconciliationAssertions.ExpiredHistoryRollbackAsync(
                    session.Store, session.Identity, clock.Advance, clock.SetUtc, default),
                "write-capacity" or "delete-capacity" => ArtifactHistoryAssertions.TicketExpiryCapacityAsync(
                    session.Store, session.Maintenance, session.Identity, clock.Advance,
                    clock.SetUtc, consumer == "delete-capacity", default),
                _ => throw new ArgumentException("BindingInvalid")
            });
            Assert.True(clock.GetTimestamp() > started);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "released-cancellation")]
    [InlineData("local", "successful-ticket")]
    [InlineData("local", "successful-read")]
    [InlineData("local", "unclaimed-ticket")]
    [InlineData("local", "unclaimed-read")]
    [InlineData("local", "expired-staging")]
    [InlineData("local", "progress-cancellation")]
    [InlineData("object", "released-cancellation")]
    [InlineData("object", "successful-ticket")]
    [InlineData("object", "successful-read")]
    [InlineData("object", "unclaimed-ticket")]
    [InlineData("object", "unclaimed-read")]
    [InlineData("object", "expired-staging")]
    [InlineData("object", "progress-cancellation")]
    public async Task Observed_handoff_and_progress_preserve_actual_result_ownership(string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var clock = new ControlledClock();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", clock,
            resources, new ConformanceEvidenceBuffer());
        var limits = consumer switch
        {
            "successful-ticket" or "successful-read" =>
                new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024, transferSlots: 1, waitingCalls: 0),
            "unclaimed-ticket" or "unclaimed-read" =>
                new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024, transferSlots: 1, waitingCalls: 0, liveTickets: 2),
            "expired-staging" => new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024),
            _ => null
        };
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider, limits), context, default);
        try
        {
            await using var barrier = new ArtifactConformanceBarrier("actual-result-handoff");
            IAsyncDisposable? registration = null;
            var point = consumer switch
            {
                "progress-cancellation" => ArtifactObservationPoint.CommitProgress,
                "unclaimed-ticket" or "unclaimed-read" or "expired-staging" => ArtifactObservationPoint.OperationCompleted,
                _ => ArtifactObservationPoint.OperationReleased
            };
            Func<Func<ValueTask>, ValueTask> observe = async callback =>
            {
                registration = await session.Faults.ObserveBoundaryAsync(point, callback, default);
            };
            ValueTask Remove() => (registration ?? throw new InvalidOperationException("BindingInvalid")).DisposeAsync();
            async ValueTask Block() => await observe(() => new(barrier.HoldAsync()));
            async ValueTask Release()
            {
                try { await Remove(); }
                finally { barrier.Release(); }
            }
            Task WhenIdle() => session.Faults.AwaitSettlementAsync(default).AsTask();
            Task WaitForBoundary() => barrier.Entered.WaitAsync(TimeSpan.FromSeconds(15));
            try
            {
                await (consumer switch
                {
                    "released-cancellation" => ArtifactHandoffAssertions.ReleasedCancellationAsync(
                        session.Store, observe, () => barrier.HoldAsync(), WaitForBoundary, Remove, barrier.Release, default),
                    "successful-ticket" or "successful-read" => ArtifactHandoffAssertions.SuccessfulResultAsync(
                        session.Store, consumer == "successful-read", observe, () => barrier.HoldAsync(),
                        WaitForBoundary, Remove, barrier.Release, default),
                    "unclaimed-ticket" or "unclaimed-read" => ArtifactHandoffAssertions.UnclaimedResultAsync(
                        session.Store, consumer == "unclaimed-read", Block, WaitForBoundary, Release, WhenIdle, default),
                    "expired-staging" => ArtifactHandoffAssertions.ExpiredStagingAsync(
                        session.Store, clock.Advance, Block, WaitForBoundary, Release, WhenIdle, default),
                    "progress-cancellation" => ArtifactOwnershipAssertions.ProgressRenewalCancellationAsync(
                        session.Store, clock.Advance, WhenIdle, observe, default),
                    _ => throw new ArgumentException("BindingInvalid")
                });
            }
            finally
            {
                barrier.Release();
                try { await session.Faults.AwaitSettlementAsync(default); }
                finally { if (registration is not null) { await registration.DisposeAsync(); } }
            }
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "authority-deadline")]
    [InlineData("local", "cancel-before")]
    [InlineData("local", "cancel-waiting")]
    [InlineData("local", "cap-crossing")]
    [InlineData("local", "cooperative-cancel")]
    [InlineData("local", "storage-failures")]
    [InlineData("local", "live-references")]
    [InlineData("local", "reclaimed-identities")]
    [InlineData("local", "reclaimed-incarnations")]
    [InlineData("object", "authority-deadline")]
    [InlineData("object", "cancel-before")]
    [InlineData("object", "cancel-waiting")]
    [InlineData("object", "cap-crossing")]
    [InlineData("object", "cooperative-cancel")]
    [InlineData("object", "storage-failures")]
    [InlineData("object", "live-references")]
    [InlineData("object", "reclaimed-identities")]
    public async Task Observed_budget_failures_and_references_preserve_actual_binding_guarantees(
        string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var clock = new ControlledClock();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", clock,
            resources, new ConformanceEvidenceBuffer());
        var limits = consumer switch
        {
            "cap-crossing" => new ArtifactLimits(10, 10, 1),
            "reclaimed-identities" or "reclaimed-incarnations" =>
                new ArtifactLimits(artifactBytes: 1024, stagingBytes: 4096, committedIdentities: 1),
            _ => null
        };
        long liveReferences = consumer == "live-references" ? 1 : 0;
        var referencesAvailable = true;
        var binding = Binding(provider, limits, (_, _) => ValueTask.FromResult(
            new ArtifactReferenceObservation(referencesAvailable, liveReferences, Guid.NewGuid())));
        var session = await ConformanceObservedArtifactSession.OpenAsync(binding, context, default);
        try
        {
            Task WhenIdle() => session.Faults.AwaitSettlementAsync(default).AsTask();
            void AdvanceTo(long timestamp) =>
                clock.Advance(DateTimeOffset.FromUnixTimeMilliseconds(timestamp) - clock.GetUtcNow());
            await (consumer switch
            {
                "authority-deadline" => ArtifactBudgetAssertions.AuthorityDeadlineAsync(
                    session.Store, session.Authority, session.Identity, default),
                "cancel-before" or "cancel-waiting" => ArtifactBudgetAssertions.CancelledCommitFencingAsync(
                    session.Store, session.Authority, session.Identity, WhenIdle, consumer == "cancel-before", default),
                "cap-crossing" => ArtifactBudgetAssertions.CapCrossingAsync(session.Store, default),
                "cooperative-cancel" => ArtifactBudgetAssertions.CooperativeCancellationAsync(session.Store, default),
                "storage-failures" => ArtifactFailureAssertions.StorageFailuresAsync(session.Store, default),
                "live-references" => ArtifactDeletionAssertions.LiveReferencesAsync(
                    session.Store, count => liveReferences = count, available => referencesAvailable = available, default),
                "reclaimed-identities" => ArtifactHistoryAssertions.ReclaimedIdentityExpiryAsync(
                    session.Store, session.Maintenance, session.Identity, AdvanceTo, default),
                "reclaimed-incarnations" => ArtifactHistoryAssertions.ReclaimedIncarnationBudgetAsync(
                    session.Store, AdvanceTo, default),
                _ => throw new ArgumentException("BindingInvalid")
            });
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "receipts")]
    [InlineData("local", "recovery-pages")]
    [InlineData("local", "sequential-recovery")]
    [InlineData("local", "changed-inventory")]
    [InlineData("local", "expiry-generation")]
    [InlineData("local", "ownerless-expiry")]
    [InlineData("local", "finalized-noncommit")]
    [InlineData("local", "finalized-mutations")]
    [InlineData("local", "idle-read")]
    [InlineData("local", "cooperative-inactivity")]
    [InlineData("local", "noncooperative-source")]
    [InlineData("local", "noncooperative-destination")]
    [InlineData("object", "receipts")]
    [InlineData("object", "recovery-pages")]
    [InlineData("object", "sequential-recovery")]
    [InlineData("object", "changed-inventory")]
    [InlineData("object", "expiry-generation")]
    [InlineData("object", "ownerless-expiry")]
    [InlineData("object", "finalized-noncommit")]
    [InlineData("object", "finalized-mutations")]
    [InlineData("object", "idle-read")]
    [InlineData("object", "cooperative-inactivity")]
    [InlineData("object", "noncooperative-source")]
    [InlineData("object", "noncooperative-destination")]
    public async Task Observed_recovery_evidence_and_expiry_preserve_actual_binding_guarantees(
        string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var clock = new ControlledClock();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", clock,
            resources, new ConformanceEvidenceBuffer());
        var limits = consumer == "ownerless-expiry" ? new ArtifactLimits(artifactBytes: 1, stagingBytes: 1) : null;
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider, limits), context, default);
        try
        {
            Task WhenIdle() => session.Faults.AwaitSettlementAsync(default).AsTask();
            await (consumer switch
            {
                "receipts" => ArtifactEvidenceAssertions.ExactCurrentReceiptsAsync(
                    session.Store, session.Validator, session.Authority, session.Identity, default),
                "recovery-pages" => ArtifactRecoveryAssertions.RecoveryPagesAsync(
                    session.Store, session.Maintenance, session.Identity, default),
                "sequential-recovery" => ArtifactRecoveryAssertions.SequentialRecoveryAsync(
                    session.Store, session.Maintenance, session.Identity, clock.Advance,
                    provider == "local" ? ArtifactEnumerationConsistency.Snapshot : ArtifactEnumerationConsistency.Incomplete,
                    default),
                "changed-inventory" => ArtifactRecoveryAssertions.ChangedInventoryAsync(
                    session.Store, session.Maintenance, session.Identity, default),
                "expiry-generation" => ArtifactRecoveryAssertions.ExpiryGenerationAsync(
                    session.Store, session.Maintenance, session.Identity, clock.Advance, default),
                "ownerless-expiry" => ArtifactRecoveryAssertions.OwnerlessExpiryAsync(session.Store, clock.Advance, default),
                "finalized-noncommit" => ArtifactRecoveryAssertions.FinalizedNoncommitAsync(
                    session.Store, session.Maintenance, session.Identity, clock.Advance, default),
                "finalized-mutations" => ArtifactReconciliationAssertions.FinalizedMutationExpiryAsync(
                    session.Store, clock.Advance, default),
                "idle-read" => ArtifactOwnershipAssertions.IdleReadExpiryAsync(session.Store, clock.Advance, default),
                "cooperative-inactivity" => ArtifactOwnershipAssertions.CooperativeInactivityAsync(
                    session.Store, WhenIdle, default),
                "noncooperative-source" => ArtifactOwnershipAssertions.NoncooperativeSourceAsync(session.Store, default),
                "noncooperative-destination" => ArtifactOwnershipAssertions.NoncooperativeDestinationAsync(session.Store, default),
                _ => throw new ArgumentException("BindingInvalid")
            });
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "completion")]
    [InlineData("local", "handle")]
    [InlineData("local", "renewed")]
    [InlineData("object", "completion")]
    [InlineData("object", "handle")]
    [InlineData("object", "renewed")]
    public async Task Observed_cancelled_descriptors_preserve_actual_current_ownership(string provider, string alteration)
    {
        await using var resources = new RecordingDirectories();
        var clock = new ControlledClock();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", clock,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        try
        {
            await ArtifactOwnershipAssertions.CancelledStagedDescriptorAsync(session.Store, clock.Advance,
                () => session.Faults.AwaitSettlementAsync(default).AsTask(), alteration, default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "read-bitflip")]
    [InlineData("local", "read-truncate")]
    [InlineData("local", "commit-progress")]
    [InlineData("local", "exact-payload")]
    [InlineData("object", "read-bitflip")]
    [InlineData("object", "read-truncate")]
    [InlineData("object", "commit-progress")]
    [InlineData("object", "exact-payload")]
    public async Task Observed_payload_and_progress_consumers_preserve_actual_binding_guarantees(
        string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var clock = new ControlledClock();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", clock,
            resources, new ConformanceEvidenceBuffer());
        var original = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        IArtifactConformanceSession current = original;
        var origins = new List<ConformanceSessionOrigin> { original.CaptureOrigin() };
        try
        {
            if (consumer == "commit-progress")
            {
                IAsyncDisposable? progress = null;
                try
                {
                    Func<Func<ValueTask>, ValueTask> observe = async callback =>
                    {
                        progress = await current.Faults.ObserveBoundaryAsync(
                            ArtifactObservationPoint.CommitProgress, callback, default);
                    };
                    await ArtifactRecoveryAssertions.ProgressingCommitAsync(current.Store, clock.Advance, observe, default);
                }
                finally
                {
                    try { await current.Faults.AwaitSettlementAsync(default); }
                    finally { if (progress is not null) { await progress.DisposeAsync(); } }
                }
            }
            else if (consumer == "exact-payload")
            {
                await ArtifactReadAssertions.ExactPayloadControlsAsync(current.Store,
                    current.Faults.CapturePayloadAsync, current.Faults.ReplacePayloadAsync,
                    current.Faults.RemovePayloadAsync, default);
                await ArtifactReadAssertions.PayloadControlsExcludeDeletionAsync(current.Store,
                    current.Faults.CapturePayloadAsync, current.Faults.ReplacePayloadAsync,
                    current.Faults.RemovePayloadAsync, () => current.Faults.WaitingAuthorityAdmissions,
                    (callback, token) => current.Faults.ObserveBoundaryAsync(
                        ArtifactObservationPoint.PayloadSelected, callback, token), default);
            }
            else
            {
                if (consumer is not ("read-bitflip" or "read-truncate")) { throw new ArgumentException("BindingInvalid"); }
                await ArtifactReadAssertions.DamagedReadAsync(
                    current.Store, current.Validator, current.Authority, current.Identity, consumer == "read-truncate",
                    (stamp, token) => current.Faults.CapturePayloadAsync(stamp, 1024, token),
                    async (stamp, truncate, token) =>
                    {
                        await current.Faults.ArmAsync(ConformanceFault.PayloadDamage, token);
                        var damaging = current.Faults.DamagePayloadAsync(stamp, truncate, token).AsTask();
                        try { await current.Faults.WaitForBoundaryAsync(ConformanceFault.PayloadDamage, token); }
                        finally
                        {
                            await current.Faults.ReleaseAsync(ConformanceFault.PayloadDamage, default);
                            await damaging;
                        }
                    }, current.Faults.ReplacePayloadAsync, default, null,
                    provider == "local" ? async token =>
                    {
                        current = await current.ReopenAsync(token);
                        var reopened = Assert.IsType<ConformanceObservedArtifactSession>(current).CaptureOrigin();
                        Assert.Equal(origins[0].SessionId, reopened.ParentSessionId);
                        origins.Add(reopened);
                        return current.Store;
                    }
                : null);
            }
            foreach (var origin in origins) { ConformanceSessionOriginOutput.Write(output, origin); }
        }
        finally { await current.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Ordinary_acknowledgment_shaped_observer_errors_still_fault_actual_settlement(string provider)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        var failure = new IOException("InjectedPublicationAcknowledgmentLoss");
        try
        {
            await using var observer = await session.Faults.ObserveBoundaryAsync(
                ArtifactObservationPoint.PublicationSelected, () => ValueTask.FromException(failure), default);
            var ticket = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Value;
            using var source = new ArtifactPublicationAssertions.ShortSource("unexpected acknowledgment error"u8.ToArray());
            var staged = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Success>(
                await session.Store.StageAsync(ticket, source, new(), default)).Value;
            Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await session.Store.CommitAsync(staged, new(), default)).Code);
            await session.Faults.AwaitSettlementAsync(default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await Assert.ThrowsAsync<InvalidOperationException>(() => session.DisposeAsync().AsTask()); }
        var settlement = Assert.Single(resources.Settlements).Value;
        Assert.True(settlement.IsFaulted);
        Assert.Contains(failure, settlement.Exception!.InnerExceptions);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "private-staging")]
    [InlineData("local", "concurrent-writers")]
    [InlineData("local", "lost-acknowledgment")]
    [InlineData("local", "visible-before-ack")]
    [InlineData("object", "private-staging")]
    [InlineData("object", "concurrent-writers")]
    [InlineData("object", "lost-acknowledgment")]
    [InlineData("object", "direct-availability")]
    public async Task Observed_boundary_consumers_preserve_actual_binding_guarantees(string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        try
        {
            await BoundaryConsumerAsync(session, consumer);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    private static async Task BoundaryConsumerAsync(IArtifactConformanceSession session, string consumer)
    {
        if (consumer == "concurrent-writers")
        {
            await ObserveAsync(session, ArtifactObservationPoint.PublicationAdmitted,
                install => ArtifactPublicationAssertions.ConcurrentEquivalentWritersAsync(session.Store, install, default));
            return;
        }
        if (consumer == "lost-acknowledgment")
        {
            await using var injection = await session.Faults.InjectPublicationAcknowledgmentLossAsync(default);
            await ArtifactReconciliationAssertions.LostAcknowledgmentAsync(
                session.Store, () => Assert.Equal(0, injection.ObservationCount), default);
            await injection.WaitForEntryAsync(default);
            Assert.Equal(1, injection.ObservationCount);
            await session.Faults.AwaitSettlementAsync(default);
            return;
        }
        var point = consumer switch
        {
            "private-staging" => ArtifactObservationPoint.StagePrefix,
            "visible-before-ack" => ArtifactObservationPoint.ReceiptPersisted,
            "direct-availability" => ArtifactObservationPoint.DirectVerification,
            _ => throw new ArgumentException("BindingInvalid")
        };
        await using var barrier = new ArtifactConformanceBarrier(consumer);
        await ObserveAsync(session, point, async install =>
        {
            void Block() => install(() => new(barrier.HoldAsync()));
            void Release()
            {
                install(static () => ValueTask.CompletedTask);
                barrier.Release();
            }
            if (consumer == "private-staging") { Block(); }
            try
            {
                await (consumer switch
                {
                    "private-staging" => ArtifactPublicationAssertions.PrivateStagingAsync(session.Store,
                        token => barrier.Entered.WaitAsync(token), Release, default),
                    "visible-before-ack" => ArtifactVisibilityAssertions.VisibleBeforeAcknowledgmentAsync(session.Store,
                        Block, token => barrier.Entered.WaitAsync(token), Release, default),
                    "direct-availability" => ArtifactVisibilityAssertions.DirectAvailabilityAsync(
                        session.Store, session.Maintenance, session.Identity,
                        Block, token => barrier.Entered.WaitAsync(token), Release, default),
                    _ => throw new ArgumentException("BindingInvalid")
                });
            }
            finally { Release(); }
        });
    }

    private static async Task ObserveAsync(IArtifactConformanceSession session, ArtifactObservationPoint point,
        Func<Action<Func<ValueTask>>, Task> assertion)
    {
        Func<ValueTask>? observer = null;
        await using var registration = await session.Faults.ObserveBoundaryAsync(point,
            () => (Volatile.Read(ref observer) ?? throw new InvalidOperationException("BindingInvalid"))(), default);
        try { await assertion(callback => Volatile.Write(ref observer, callback)); }
        finally { await session.Faults.AwaitSettlementAsync(default); }
    }

    [Theory]
    [InlineData("local", "destination-failure")]
    [InlineData("local", "exact-retry")]
    [InlineData("local", "staged-length")]
    [InlineData("local", "recreation")]
    [InlineData("local", "reader-exclusion")]
    [InlineData("object", "destination-failure")]
    [InlineData("object", "exact-retry")]
    [InlineData("object", "staged-length")]
    [InlineData("object", "recreation")]
    [InlineData("object", "reader-exclusion")]
    public async Task Observed_read_reconciliation_and_deletion_preserve_actual_binding_guarantees(
        string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        try
        {
            await (consumer switch
            {
                "destination-failure" => ArtifactReadAssertions.DestinationFailureAsync(
                    session.Store, "Synthetic borrowed destination failure", default),
                "exact-retry" => ArtifactReconciliationAssertions.AcknowledgedReceiptRetryAsync(session.Store, default),
                "staged-length" => ArtifactPublicationAssertions.ConflictingStagedLengthAsync(session.Store, default),
                "recreation" => ArtifactDeletionAssertions.ExactReceiptsAndRecreationAsync(
                    session.Store, session.Maintenance, session.Identity, default),
                "reader-exclusion" => ArtifactDeletionAssertions.HeldReaderExcludesDeletionAsync(session.Store, default),
                _ => throw new ArgumentException("BindingInvalid")
            });
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "empty")]
    [InlineData("local", "unknown-length")]
    [InlineData("local", "expectations")]
    [InlineData("local", "unsupported")]
    [InlineData("local", "duplicates")]
    [InlineData("object", "empty")]
    [InlineData("object", "unknown-length")]
    [InlineData("object", "expectations")]
    [InlineData("object", "unsupported")]
    [InlineData("object", "duplicates")]
    public async Task Observed_publication_consumers_preserve_actual_binding_guarantees(
        string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        try
        {
            await (consumer switch
            {
                "empty" => ArtifactPublicationAssertions.EmptyContentAndAbsenceAsync(session.Store, default),
                "unknown-length" => ArtifactPublicationAssertions.UnknownLengthAndRealEofAsync(session.Store, default),
                "expectations" => ArtifactPublicationAssertions.EveryExpectationAndEofAsync(session.Store, default),
                "unsupported" => ArtifactPublicationAssertions.UnsupportedChecksumAndRangeAsync(session.Store, default),
                "duplicates" => ArtifactPublicationAssertions.VerifiedDuplicatesAsync(session.Store, default),
                _ => throw new ArgumentException("BindingInvalid")
            });
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Releasing_native_work_does_not_block_an_independent_release_or_rearming(string provider)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        await using var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        await ArtifactBindingAssertions.ConcurrentReleaseAsync(session, default);
        ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
    }

    [Theory]
    [InlineData("local", ConformanceFault.PublicationBoundary)]
    [InlineData("local", ConformanceFault.DirectVisibility)]
    [InlineData("local", ConformanceFault.PayloadDamage)]
    [InlineData("local", ConformanceFault.Capacity)]
    [InlineData("local", ConformanceFault.NativeNonCooperation)]
    [InlineData("local", ConformanceFault.CleanupFailure)]
    [InlineData("local", ConformanceFault.GenerationBoundary)]
    [InlineData("local", ConformanceFault.ReceiptBoundary)]
    [InlineData("local", ConformanceFault.SourceNonCooperation)]
    [InlineData("local", ConformanceFault.SinkNonCooperation)]
    [InlineData("object", ConformanceFault.PublicationBoundary)]
    [InlineData("object", ConformanceFault.DirectVisibility)]
    [InlineData("object", ConformanceFault.PayloadDamage)]
    [InlineData("object", ConformanceFault.Capacity)]
    [InlineData("object", ConformanceFault.NativeNonCooperation)]
    [InlineData("object", ConformanceFault.CleanupFailure)]
    [InlineData("object", ConformanceFault.GenerationBoundary)]
    [InlineData("object", ConformanceFault.ReceiptBoundary)]
    [InlineData("object", ConformanceFault.SourceNonCooperation)]
    [InlineData("object", ConformanceFault.SinkNonCooperation)]
    public async Task Full_binding_controls_reach_actual_work_and_preserve_borrowed_ownership(
        string provider, ConformanceFault fault) =>
        await RunControlAsync(provider, fault, "full-artifact-binding");

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Missing_hooks_reject_before_dispatch_and_actual_binding_passes(string provider) =>
        await RunControlAsync(provider, ConformanceFault.PublicationBoundary, "QC-05");

    private async Task RunControlAsync(string provider, ConformanceFault fault, string caseId)
    {
        await using var resources = new RecordingDirectories();
        var clock = new ControlledClock();
        var context = new ConformanceRunContext(RunId(), caseId, clock,
            resources, new ConformanceEvidenceBuffer());
        var binding = Binding(provider);
        if (fault == ConformanceFault.PublicationBoundary)
        {
            await BindingAdmissionAssertions.ArtifactsAsync(binding.Declaration, context);
            Assert.Empty(resources.Settlements);
        }
        var session = await ConformanceObservedArtifactSession.OpenAsync(binding, context, default);
        try
        {
            await ArtifactBindingAssertions.ControlsAsync(session, fault, clock.Advance, default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", true)]
    [InlineData("object", false)]
    public async Task Observed_full_binding_reopens_actual_components_and_fences_stale_controls(
        string provider, bool retainsPublication)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var binding = Binding(provider);
        var original = await ConformanceObservedArtifactSession.OpenAsync(binding, context, default);
        var current = original;
        try
        {
            var receipt = await ArtifactCompositionAssertions.ConfiguredPublicationAsync(original.Store, default);
            var origin = original.CaptureOrigin();
            current = Assert.IsType<ConformanceObservedArtifactSession>(await original.ReopenAsync(default));
            var reopened = current.CaptureOrigin();
            Assert.Equal(origin.SessionId, reopened.ParentSessionId);
            Assert.NotEqual(origin.Components["store"].InstanceId, reopened.Components["store"].InstanceId);
            Assert.Equal(retainsPublication, original.Identity == current.Identity);
            await Assert.ThrowsAsync<InvalidOperationException>(() => original.Faults.ArmAsync(
                ConformanceFault.Capacity, default).AsTask());
            var result = await current.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default);
            if (retainsPublication)
            {
                await using var read = Assert.IsType<ArtifactResult<IArtifactReadSession>.Success>(result).Value;
                using var destination = new MemoryStream();
                Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Success>(
                    await read.CopyToAsync(destination, new(), default));
            }
            else { Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(result); }
            await original.DisposeAsync();
            await ArtifactCompositionAssertions.ConfiguredPublicationAsync(current.Store, default);
            ConformanceSessionOriginOutput.Write(output, origin);
            ConformanceSessionOriginOutput.Write(output, reopened);
        }
        finally { await current.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
    }

    private static Guid RunId()
    {
        if (!Guid.TryParseExact(Environment.GetEnvironmentVariable("HOARD_ORIGIN_RUN_ID"), "D", out var runId)
            || runId == Guid.Empty)
        { throw new InvalidOperationException("PrerequisiteMissing"); }
        return runId;
    }

    private static IArtifactConformanceBinding Binding(string provider, ArtifactLimits? limits = null,
        Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceObservation>>? references = null)
    {
        var variable = provider switch
        {
            "local" => "HOARD_ARTIFACT_LOCAL_PACKAGE_SHA256",
            "object" => "HOARD_ARTIFACT_OBJECT_PACKAGE_SHA256",
            _ => throw new ArgumentException("BindingInvalid")
        };
        var sha256 = Environment.GetEnvironmentVariable(variable)
            ?? throw new InvalidOperationException("PrerequisiteMissing");
        var options = new ArtifactAssertionOptions(limits, references: references ?? ((_, _) =>
            ValueTask.FromResult(new ArtifactReferenceObservation(true, 0, Guid.NewGuid()))));
        return provider == "local" ? new LocalBinding(sha256, options: options)
            : new ObjectSemanticsBinding(sha256, options: options);
    }

    private sealed class ControlledClock : TimeProvider
    {
        private long ticks = new DateTimeOffset(2026, 1, 1, 0, 0, 0, TimeSpan.Zero).Ticks;
        private long elapsedTicks;
        public override DateTimeOffset GetUtcNow() => new(Interlocked.Read(ref ticks), TimeSpan.Zero);
        public override long TimestampFrequency => TimeSpan.TicksPerSecond;
        public override long GetTimestamp() => Interlocked.Read(ref elapsedTicks);
        public void SetUtc(long milliseconds) =>
            Interlocked.Exchange(ref ticks, DateTimeOffset.FromUnixTimeMilliseconds(milliseconds).Ticks);
        public void Advance(TimeSpan amount)
        {
            ArgumentOutOfRangeException.ThrowIfNegative(amount.Ticks);
            Interlocked.Add(ref ticks, amount.Ticks);
            Interlocked.Add(ref elapsedTicks, amount.Ticks);
        }
    }
}
